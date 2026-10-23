"""Append-only public operator evidence, with no runtime resume or replay."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import unicodedata


MAX_LINE_BYTES = 512 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 4096
MAX_DEPTH = 32
_ZERO_HASH = '0' * 64
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_PATH = re.compile(r'(?:[A-Za-z]:[\\/]|\\\\|file://|^/)', re.IGNORECASE)
_EVENT_KEYS = {'schema_version', 'kind', 'event_id', 'run_id', 'runtime_instance_id', 'sequence', 'type', 'payload'}
_TYPES = {'policy_decision', 'intent', 'receipt', 'observation', 'transport_retry', 'error', 'termination'}
_PRIVATE_WORDS = {'author', 'fault', 'seed', 'truth', 'expected', 'password', 'secret', 'private',
                  'hidden', 'credential', 'credentials', 'path', 'paths', 'oracle', 'scenario',
                  'schedule', 'traceback', 'token'}
_PRIVATE_COMPACT = {'authorcontrol', 'randomseed', 'hiddenfault', 'sourcepath', 'filepath', 'decryptedpath',
                    'privatepath', 'expectedvalues', 'expectedresult', 'apikey', 'accesstoken'}
_PROVENANCE_FLAGS = {'synthetic': True, 'hardware_verified': False, 'ai_model_called': False, 'resumable': False}


class JournalValidationError(ValueError):
    """Invalid public event or provenance; no bytes were appended."""


class JournalIntegrityError(JournalValidationError):
    """Stored evidence is invalid; the reader leaves its bytes untouched."""


class JournalStorageError(OSError):
    """Storage is unavailable or uncertain; no more writes are permitted."""


def _identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise JournalValidationError('invalid_identifier')
    return value


def _private_key(key):
    normalized = unicodedata.normalize('NFKC', key)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Cf')
    separated = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', normalized).lower()
    words = set(re.findall(r'[a-z0-9]+', separated))
    compact = ''.join(re.findall(r'[a-z0-9]+', separated))
    return (bool(words & _PRIVATE_WORDS) or compact in _PRIVATE_COMPACT or
            any(word in normalized for word in ('암호', '비밀번호', '작성자', '정답', '고장', '시드', '경로', '비공개')))


def _public_copy(value, depth=0):
    if depth > MAX_DEPTH:
        raise JournalValidationError('json_nesting_limit')
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is str:
        try:
            if len(value.encode('utf-8')) > MAX_LINE_BYTES:
                raise JournalValidationError('string_size_limit')
        except UnicodeError:
            raise JournalValidationError('invalid_utf8') from None
        if _PATH.search(value):
            raise JournalValidationError('filesystem_path_forbidden')
        return value
    if type(value) is list:
        return [_public_copy(item, depth + 1) for item in value]
    if type(value) is dict:
        result = {}
        for key, item in value.items():
            if type(key) is not str or _private_key(key):
                raise JournalValidationError('private_or_invalid_key')
            _public_copy(key, depth + 1)
            if key in _PROVENANCE_FLAGS and item is not _PROVENANCE_FLAGS[key]:
                raise JournalValidationError('invalid_synthetic_provenance')
            if key == 'sha256' or key.endswith('_sha256'):
                if not isinstance(item, str) or not _HASH.fullmatch(item):
                    raise JournalValidationError('invalid_sha256')
            result[key] = _public_copy(item, depth + 1)
        return result
    raise JournalValidationError('finite_json_required')


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise JournalValidationError('invalid_canonical_json') from None


def _provenance(value):
    result = _public_copy(value)
    required = {'runtime_origin', 'catalog_sha256', 'topology_sha256', 'engine_sha256'}
    if not isinstance(result, dict) or not required <= set(result) or result['runtime_origin'] != 'preinitialized':
        raise JournalValidationError('invalid_preinitialized_provenance')
    return result


def _header(run_id, runtime_instance_id, provenance):
    return {'schema_version': 1, 'kind': 'operator_journal', 'run_id': _identifier(run_id),
            'runtime_instance_id': _identifier(runtime_instance_id), 'provenance': _provenance(provenance),
            **_PROVENANCE_FLAGS}


def _record(record_type, payload, previous):
    result = {'record_type': record_type, record_type: payload, 'previous_sha256': previous}
    result['sha256'] = hashlib.sha256(_canonical(result)).hexdigest()
    line = _canonical(result) + b'\n'
    if len(line) > MAX_LINE_BYTES:
        raise JournalValidationError('journal_line_limit')
    return result, line


class _EventState:
    def __init__(self, header):
        self.run_id, self.instance = header['run_id'], header['runtime_instance_id']
        self.sequence = self.logical_requests = 0
        self.event_ids, self.request_ids = set(), set()
        self.pending, self.retries = {}, {}
        self.terminated = False

    def validate(self, event):
        event = _public_copy(event)
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise JournalValidationError('invalid_event_envelope')
        if self.terminated:
            raise JournalValidationError('event_after_termination')
        if self.sequence >= MAX_EVENTS:
            raise JournalValidationError('journal_event_limit')
        if type(event['schema_version']) is not int or event['schema_version'] != 1 or event['kind'] != 'operator_event':
            raise JournalValidationError('invalid_event_schema')
        _identifier(event['event_id'])
        if event['event_id'] in self.event_ids:
            raise JournalValidationError('duplicate_event_id')
        if event['run_id'] != self.run_id or event['runtime_instance_id'] != self.instance:
            raise JournalValidationError('event_instance_mismatch')
        if type(event['sequence']) is not int or event['sequence'] != self.sequence + 1:
            raise JournalValidationError('event_sequence_mismatch')
        kind, payload = event['type'], event['payload']
        if not isinstance(kind, str) or kind not in _TYPES or not isinstance(payload, dict):
            raise JournalValidationError('invalid_event_type_or_payload')
        if kind == 'intent':
            if set(payload) != {'request_id', 'operation', 'body', 'logical_request'}:
                raise JournalValidationError('invalid_intent_payload')
            _identifier(payload['request_id'])
            if payload['request_id'] in self.request_ids:
                raise JournalValidationError('duplicate_intent_id')
            if type(payload['logical_request']) is not int or payload['logical_request'] != self.logical_requests + 1:
                raise JournalValidationError('invalid_logical_request')
            body = payload['body']
            if not isinstance(body, dict):
                raise JournalValidationError('invalid_intent_body')
            if payload['operation'] == 'execute':
                if set(body) != {'device_id', 'action', 'parameters'} or not isinstance(body['parameters'], dict):
                    raise JournalValidationError('invalid_execute_body')
                _identifier(body['device_id']); _identifier(body['action'])
            elif payload['operation'] == 'advance':
                if set(body) != {'ticks'} or type(body['ticks']) is not int or body['ticks'] != 1:
                    raise JournalValidationError('invalid_advance_body')
            else:
                raise JournalValidationError('invalid_intent_operation')
        elif kind == 'receipt':
            if set(payload) != {'request_id', 'result'} or not isinstance(payload['result'], dict):
                raise JournalValidationError('invalid_receipt_payload')
            if _identifier(payload['request_id']) not in self.pending:
                raise JournalValidationError('receipt_without_pending_intent')
        elif kind == 'transport_retry':
            if set(payload) != {'request_id', 'retry'} or _identifier(payload['request_id']) not in self.pending:
                raise JournalValidationError('retry_without_pending_intent')
            if type(payload['retry']) is not int or payload['retry'] != self.retries.get(payload['request_id'], 0) + 1:
                raise JournalValidationError('invalid_retry_number')
        elif kind == 'observation':
            if not {'observation'} <= set(payload) <= {'observation', 'cause_request_id'} or not isinstance(payload['observation'], dict):
                raise JournalValidationError('invalid_observation_payload')
            if 'cause_request_id' in payload and _identifier(payload['cause_request_id']) not in self.request_ids:
                raise JournalValidationError('observation_without_intent')
        elif kind == 'policy_decision':
            if 'proposal' not in payload:
                raise JournalValidationError('missing_policy_proposal')
        elif kind == 'error':
            if 'code' not in payload:
                raise JournalValidationError('missing_public_error_code')
            _identifier(payload['code'])
        elif kind == 'termination':
            if payload.get('code') != 'run_terminated' or not isinstance(payload.get('unresolved_request_ids'), list):
                raise JournalValidationError('invalid_termination_marker')
            ids = payload['unresolved_request_ids']
            if any(_identifier(value) not in self.request_ids for value in ids) or len(set(ids)) != len(ids):
                raise JournalValidationError('invalid_termination_request_ids')
        return event

    def apply(self, event):
        self.sequence += 1
        self.event_ids.add(event['event_id'])
        kind, payload = event['type'], event['payload']
        if kind == 'intent':
            request_id = payload['request_id']
            self.request_ids.add(request_id)
            self.pending[request_id] = None
            self.logical_requests += 1
        elif kind == 'receipt':
            del self.pending[payload['request_id']]
        elif kind == 'transport_retry':
            self.retries[payload['request_id']] = payload['retry']
        elif kind == 'termination':
            self.terminated = True


class OperatorJournal:
    """New-file-only, fsynced event_sink. A write failure ends this writer."""

    def __init__(self, path, *, run_id, runtime_instance_id, provenance):
        header = _header(run_id, runtime_instance_id, provenance)
        record, line = _record('header', header, _ZERO_HASH)
        if len(line) > MAX_FILE_BYTES:
            raise JournalValidationError('journal_file_limit')
        self._lock = threading.RLock()
        self._state = _EventState(header)
        self._failed = self._closed = False
        self._bytes = 0
        self._previous = _ZERO_HASH
        self._stream = None
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND | getattr(os, 'O_BINARY', 0)
        try:
            fd = os.open(Path(path), flags, 0o600)
        except FileExistsError:
            raise FileExistsError('operator journal already exists') from None
        except OSError:
            raise JournalStorageError('cannot create operator journal') from None
        try:
            self._stream = os.fdopen(fd, 'wb')
        except Exception:
            os.close(fd)
            raise JournalStorageError('cannot open operator journal stream') from None
        try:
            self._append(record, line)
        except BaseException:
            try:
                self.close()
            except JournalStorageError:
                pass
            raise

    def _append(self, record, line):
        if self._bytes + len(line) > MAX_FILE_BYTES:
            raise JournalValidationError('journal_file_limit')
        try:
            if self._stream.write(line) != len(line):
                raise OSError('short write')
            self._stream.flush()
            os.fsync(self._stream.fileno())
        except Exception:
            self._failed = True
            try:
                self.close()
            except JournalStorageError:
                pass
            raise JournalStorageError('operator journal write uncertain; writer is unusable') from None
        self._bytes += len(line)
        self._previous = record['sha256']

    def __call__(self, event):
        with self._lock:
            if self._closed or self._failed:
                raise JournalStorageError('operator journal is closed or uncertain')
            event = self._state.validate(event)
            record, line = _record('event', event, self._previous)
            self._append(record, line)
            self._state.apply(event)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                fd = self._stream.fileno()
            except Exception:
                fd = None
            try:
                self._stream.close()
            except Exception:
                self._failed = True
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                raise JournalStorageError('operator journal close uncertain') from None

    def __enter__(self):
        with self._lock:
            if self._closed or self._failed:
                raise JournalStorageError('operator journal is closed or uncertain')
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.close()
        except JournalStorageError:
            if exc_type is None:
                raise
        return False


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JournalIntegrityError('duplicate_json_key')
        result[key] = value
    return result


def _constant(value):
    raise JournalIntegrityError('nonfinite_json_number')


def _read_record(line, previous, record_type):
    if not line.endswith(b'\n') or len(line) > MAX_LINE_BYTES:
        raise JournalIntegrityError('partial_or_oversized_line')
    try:
        record = json.loads(line.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
        if not isinstance(record, dict) or set(record) != {'record_type', record_type, 'previous_sha256', 'sha256'}:
            raise JournalIntegrityError('invalid_record_schema')
        if record['record_type'] != record_type or record['previous_sha256'] != previous:
            raise JournalIntegrityError('invalid_hash_chain')
        if not isinstance(record['sha256'], str) or not _HASH.fullmatch(record['sha256']):
            raise JournalIntegrityError('invalid_record_hash')
        unsigned = {key: value for key, value in record.items() if key != 'sha256'}
        if hashlib.sha256(_canonical(unsigned)).hexdigest() != record['sha256']:
            raise JournalIntegrityError('record_checksum_mismatch')
        if _canonical(record) + b'\n' != line:
            raise JournalIntegrityError('noncanonical_json_line')
        return record
    except JournalIntegrityError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise JournalIntegrityError('invalid_json_record') from None


def read_operator_journal(path):
    """Verify stored evidence without modifying it or constructing any runtime."""
    previous, total = _ZERO_HASH, 0
    file_hash = hashlib.sha256()
    header = state = None
    events = []
    try:
        with Path(path).open('rb') as stream:
            if os.fstat(stream.fileno()).st_size > MAX_FILE_BYTES:
                raise JournalIntegrityError('journal_file_limit')
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                total += len(line)
                if total > MAX_FILE_BYTES:
                    raise JournalIntegrityError('journal_file_limit')
                record_type = 'header' if header is None else 'event'
                record = _read_record(line, previous, record_type)
                if header is None:
                    actual = record['header']
                    try:
                        expected = _header(actual['run_id'], actual['runtime_instance_id'], actual['provenance'])
                    except (KeyError, TypeError, JournalValidationError):
                        raise JournalIntegrityError('invalid_journal_header') from None
                    if _canonical(actual) != _canonical(expected):
                        raise JournalIntegrityError('invalid_journal_header')
                    header, state = expected, _EventState(expected)
                else:
                    try:
                        event = state.validate(record['event'])
                    except JournalValidationError:
                        raise JournalIntegrityError('invalid_stored_event') from None
                    state.apply(event)
                    events.append(event)
                previous = record['sha256']
                file_hash.update(line)
    except OSError:
        raise JournalStorageError('cannot read operator journal') from None
    if header is None:
        raise JournalIntegrityError('missing_journal_header')
    return {'schema_version': 1, 'kind': 'operator_journal_read', 'header': header, 'events': events,
            'integrity': {'status': 'verified', 'algorithm': 'sha256', 'head_sha256': previous,
                          'file_sha256': file_hash.hexdigest(), 'event_count': len(events)},
            'complete': state.terminated and not state.pending,
            'unresolved_request_ids': list(state.pending), 'resumable': False}
