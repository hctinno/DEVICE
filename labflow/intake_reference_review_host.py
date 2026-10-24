"""Bounded preparations borrowed by an already authenticated reference host.

This module owns memory admission, never authentication, source concurrency or
Store lifetime. The trusted host supplies the same RLock used by its supervisor.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import sys
import threading
from time import monotonic as _clock

from .store import Store, StoreOpenError


_MIB = 1024 * 1024
_HANDLE_RESERVATION = 21 * _MIB  # parent20MiB plus bounded metadata allowance
_RETAINED_LIMIT = 63 * _MIB
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z', re.ASCII)
_SHA = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
_LOCK_TYPE = type(threading.RLock())
_TOKEN = object()
_PREFIX = 'intake_reference_review_host_'
_ERRORS = {'unconfigured': 503, 'invalid_request': 400, 'input_limit': 413,
           'access_denied': 403, 'review_input_unavailable': 503,
           'prepared_unavailable': 410, 'request_conflict': 409, 'unavailable': 503}
# Exact public classes and enumerated codes only. Looking up already loaded
# modules avoids importing042 on a disabled/default host path.
_PARENT_ERRORS = {
    ('labflow.store', 'StoreOpenError'): ('store_open_', frozenset((
        'invalid_argument', 'path_invalid', 'unavailable', 'schema_mismatch',
        'input_changed', 'integrity_invalid', 'closed', 'backend_unavailable', 'mode_unsupported'))),
    ('labflow.intake_reference_review', 'IntakeReferenceReviewError'): ('intake_reference_review_', frozenset((
        'invalid_argument', 'store_invalid', 'access_denied', 'prepared_invalid',
        'review_state_changed', 'parent_invalid', 'input_limit', 'unavailable'))),
    ('labflow.intake_reference_ledger', 'IntakeReferenceLedgerError'): ('intake_reference_ledger_', frozenset((
        'invalid_argument', 'store_invalid', 'intake_not_found', 'input_limit', 'parent_invalid',
        'origin_invalid', 'schema_mismatch', 'request_conflict', 'integrity_invalid', 'storage_error'))),
    ('labflow.intake_reference_snapshot', 'IntakeReferenceStateError'): ('intake_reference_state_', frozenset((
        'invalid_argument', 'store_invalid', 'transaction_required', 'intake_not_found', 'input_limit',
        'source_integrity_invalid', 'projection_inconsistent', 'delegation_invalid', 'storage_error'))),
    ('labflow.intake_case_references', 'IntakeCaseReferencesError'): ('intake_case_references_', frozenset((
        'catalog_invalid', 'snapshot_invalid', 'context_invalid', 'response_invalid', 'producer_invalid', 'source_error', 'limit_exceeded'))),
    ('labflow.fcc_case_review', 'FccCaseReviewError'): ('fcc_case_review_', frozenset((
        'catalog_invalid', 'query_invalid', 'selection_invalid', 'source_invalid', 'source_error', 'limit_exceeded',
        'context_invalid', 'context_mismatch', 'producer_invalid', 'response_invalid', 'reference_invalid'))),
}
_REASONS = frozenset(('analysis_not_ready', 'profile_changed', 'delegation_missing', 'intake_deferred',
    'delegation_evidence_missing', 'required_questions_open', 'unread_documents', 'source_provenance_unconfirmed', 'preparation_not_ready'))
_STATUSES = frozenset(('current_at_append', 'historical_provided', 'preparation_unverified', 'head_conflict', 'reference_unbound'))
_PREVIEW = frozenset(('schema_version', 'kind', 'intake_id', 'preparation_id', 'observation',
    'preparation_ready', 'reason_codes', 'review_status', 'selection', 'source_modes', 'verification'))
_REGISTRATION = frozenset(('schema_version', 'kind', 'request_id', 'record_id', 'seq', 'stored',
    'replayed', 'binding_status', 'append_observation', 'verification'))
_APPEND_REQUEST = frozenset(('schema_version', 'handle_id', 'intake_id', 'request_id',
    'preparation_id', 'expected_snapshot_id', 'expected_head_record_id'))


class IntakeReferenceReviewHostError(ValueError):
    """Fixed code/status without source values or exception chaining."""
    def __init__(self, code='unavailable', status=None):
        suffix = code.removeprefix(_PREFIX) if type(code) is str else 'unavailable'
        suffix = suffix if suffix in _ERRORS else 'unavailable'
        self.code = _PREFIX + suffix
        self.status = 429 if suffix == 'unavailable' and type(status) is int and status == 429 else _ERRORS[suffix]
        super().__init__(self.code)


def _fail(suffix='invalid_request', status=None):
    raise IntakeReferenceReviewHostError(suffix, status)


def _public(function):
    @wraps(function)
    def call(*args, **kwargs):
        failure = IntakeReferenceReviewHostError('unavailable')
        try:
            return function(*args, **kwargs)
        except IntakeReferenceReviewHostError as error:
            if type(error) is IntakeReferenceReviewHostError:
                failure = IntakeReferenceReviewHostError(error.code, error.status)
        except Exception as error:
            for (module_name, name), (prefix, suffixes) in _PARENT_ERRORS.items():
                module = sys.modules.get(module_name)
                cls = vars(module).get(name) if module is not None else None
                if type(error) is cls:
                    code = getattr(error, 'code', None)
                    if type(code) is str and code in {prefix + suffix for suffix in suffixes}:
                        failure = cls(code)
                    break
        # Also clear context when the *caller* is handling an unrelated exception.
        try:
            raise failure from None
        except ValueError as sanitized:
            sanitized.__context__ = sanitized.__cause__ = None
            raise
    return call


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _copy(value, limit, depth_limit, node_limit, code='invalid_request'):
    size = nodes = 0

    def consume(amount):
        nonlocal size
        size += amount
        if size > limit:
            _fail('input_limit')

    def count():
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            _fail('input_limit')

    def scalar(item):
        if type(item) is str and len(item) > limit - size:
            _fail('input_limit')
        try:
            raw = _encoded(item)
        except (ValueError, UnicodeError, OverflowError):
            _fail(code)
        consume(len(raw))
        return item

    def walk(item, depth=0):
        count()
        if depth > depth_limit:
            _fail('input_limit')
        if type(item) is dict:
            consume(2)
            result = {}
            for index, (key, child) in enumerate(item.items()):
                if type(key) is not str:
                    _fail(code)
                count()
                scalar(key)
                consume(1 + bool(index))
                result[key] = walk(child, depth + 1)
            return result
        if type(item) is list:
            consume(2)
            result = []
            for index, child in enumerate(item):
                if index:
                    consume(1)
                result.append(walk(child, depth + 1))
            return result
        if item is None or type(item) in (str, int, bool):
            return scalar(item)
        if type(item) is float and math.isfinite(item):
            return scalar(item)
        _fail(code)
    return walk(value)


def _keys(value, fields, code='invalid_request'):
    if type(value) is not dict or set(value) != set(fields):
        _fail(code)


def _id(value, maximum=150, code='invalid_request'):
    if type(value) is not str or len(value) > maximum or not _ID.fullmatch(value):
        _fail(code)


def _sha(value, nullable=False, code='invalid_request'):
    if value is None and nullable:
        return
    if type(value) is not str or not _SHA.fullmatch(value):
        _fail(code)


def _integer(value, minimum=1, maximum=2**63-1, code='unavailable'):
    if type(value) is not int or not minimum <= value <= maximum:
        _fail(code)


def _boolean(value):
    if type(value) is not bool:
        _fail('unavailable')


def _choice(value, choices, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or value not in choices:
        _fail('unavailable')


def _flags(value, true, false, optional=()):
    _keys(value, set(true) | set(false) | set(optional), 'unavailable')
    for child in value.values():
        _boolean(child)
    if any(value[key] is not True for key in true) or any(value[key] is not False for key in false):
        _fail('unavailable')


def _time(value):
    if type(value) is not str or len(value) > 128:
        _fail('unavailable')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        _fail('unavailable')
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        _fail('unavailable')


def _preview(value, intake_id):
    value = _copy(value, 32*1024, 12, 4096, 'unavailable')
    _keys(value, _PREVIEW, 'unavailable')
    _integer(value['schema_version'], maximum=1)
    if value['kind'] != 'intake_reference_review_preview' or value['intake_id'] != intake_id:
        _fail('unavailable')
    _id(value['intake_id'], code='unavailable')
    _sha(value['preparation_id'], code='unavailable')
    observation = value['observation']
    _keys(observation, ('kind', 'snapshot_id', 'head_record_id', 'observed_at'), 'unavailable')
    if observation['kind'] != 'paired_public_reads':
        _fail('unavailable')
    _sha(observation['snapshot_id'], code='unavailable')
    _sha(observation['head_record_id'], True, 'unavailable')
    _time(observation['observed_at'])
    _boolean(value['preparation_ready'])
    reasons = value['reason_codes']
    if type(reasons) is not list or len(reasons) > len(_REASONS):
        _fail('unavailable')
    for reason in reasons:
        _choice(reason, _REASONS)
    if reasons != sorted(set(reasons)) or value['preparation_ready'] is not (not reasons):
        _fail('unavailable')
    _choice(value['review_status'], ('bound', 'insufficient_evidence'))
    selection = value['selection']
    _keys(selection, ('context_id', 'corpus_id', 'requested_case_ids', 'status', 'accepted_reference_count', 'receipt_id'), 'unavailable')
    _sha(selection['context_id'], True, 'unavailable')
    if selection['corpus_id'] is not None:
        _id(selection['corpus_id'], 128, 'unavailable')
    ids = selection['requested_case_ids']
    if type(ids) is not list or len(ids) > 16:
        _fail('unavailable')
    for item in ids:
        _id(item, 128, 'unavailable')
    if len(ids) != len(set(ids)):
        _fail('unavailable')
    _choice(selection['status'], ('selected', 'no_candidate', 'unknown'))
    _integer(selection['accepted_reference_count'], 0, 256)
    _sha(selection['receipt_id'], code='unavailable')
    modes = value['source_modes']
    _keys(modes, ('intake_revision_synthetic', 'catalog_synthetic', 'intake_provenance_status'), 'unavailable')
    _boolean(modes['intake_revision_synthetic'])
    if modes['catalog_synthetic'] is not None:
        _boolean(modes['catalog_synthetic'])
    _choice(modes['intake_provenance_status'], ('confirmed', 'unconfirmed'))
    _flags(value['verification'], ('reference_receipt_validated', 'retained_snapshot_observed'),
           ('reference_source_currentness_verified', 'operational_authority_granted', 'model_execution_verified', 'evaluation_executed'))
    return value


def _registration(value, request):
    value = _copy(value, 2*_MIB, 20, 200000, 'unavailable')
    _keys(value, _REGISTRATION, 'unavailable')
    _integer(value['schema_version'], maximum=1)
    if value['kind'] != 'intake_reference_registration' or value['request_id'] != request['request_id'] or value['stored'] is not True:
        _fail('unavailable')
    _sha(value['record_id'], code='unavailable')
    _integer(value['seq'])
    _boolean(value['replayed'])
    _choice(value['binding_status'], _STATUSES)
    observation = value['append_observation']
    _keys(observation, ('expected_snapshot_id', 'captured_snapshot_id', 'head_before_record_id',
        'head_after_record_id', 'head_advanced', 'preparation_ready', 'observed_at'), 'unavailable')
    _sha(observation['expected_snapshot_id'], code='unavailable')
    for key in ('captured_snapshot_id', 'head_before_record_id', 'head_after_record_id'):
        _sha(observation[key], True, 'unavailable')
    _boolean(observation['head_advanced'])
    _boolean(observation['preparation_ready'])
    _time(observation['observed_at'])
    if observation['expected_snapshot_id'] != request['expected_snapshot_id']:
        _fail('unavailable')
    if observation['head_advanced'] is not (value['binding_status'] == 'current_at_append'):
        _fail('unavailable')
    if observation['head_advanced']:
        if observation['captured_snapshot_id'] != observation['expected_snapshot_id'] or observation['head_after_record_id'] != value['record_id']:
            _fail('unavailable')
    elif observation['head_after_record_id'] != observation['head_before_record_id']:
        _fail('unavailable')
    _flags(value['verification'], ('record_hash_verified', 'parent_revalidated_at_append', 'origin_revalidated_at_append'),
           ('operational_authority_granted', 'model_execution_verified', 'evaluation_executed', 'independent_evaluation_approved'),
           ('mutable_state_verified_at_append',))
    return value


def _scope(value):
    if type(value) is str and value == 'workspace':
        return value
    if type(value) is not tuple:
        _fail()
    if len(value) > 100:
        _fail('input_limit')
    for item in value:
        _id(item)
    if len(value) != len(set(value)):
        _fail()
    return value


def _permits(scope, intake_id):
    return scope == 'workspace' or intake_id in scope


def _inputs(values):
    if type(values) is not tuple:
        _fail()
    if len(values) > 100:
        _fail('input_limit')
    result = {}
    total = 2  # canonical list brackets; no aggregate node limit
    for index, item in enumerate(values):
        _keys(item, ('intake_id', 'case_context', 'validated_response', 'producer_name'))
        intake_id, producer = item['intake_id'], item['producer_name']
        _id(intake_id)
        _id(producer)
        if intake_id in result:
            _fail()
        context = _copy(item['case_context'], 8*_MIB, 24, 200000)
        response = _copy(item['validated_response'], 320*1024, 16, 60000)
        for value, kind in ((context, 'fcc_case_review_context'), (response, 'validated_fcc_case_review')):
            if type(value) is not dict or type(value.get('schema_version')) is not int or value['schema_version'] != 1 or value.get('kind') != kind:
                _fail()
        detached = dict(intake_id=intake_id, producer_name=producer, case_context=context, validated_response=response)
        total += len(_encoded(detached)) + bool(index)
        if total > 32*_MIB:
            _fail('input_limit')
        context_raw, response_raw = _encoded(context), _encoded(response)
        input_id = hashlib.sha256(_encoded({'schema_version': 1, 'intake_id': intake_id,
            'case_context_sha256': hashlib.sha256(context_raw).hexdigest(),
            'validated_response_sha256': hashlib.sha256(response_raw).hexdigest(), 'producer_name': producer})).hexdigest()
        result[intake_id] = (input_id, context_raw, response_raw, producer)
    return result


def _identity(store):
    if type(store) is not Store or not isinstance(getattr(store, 'root', None), Path) or not isinstance(getattr(store, 'db', None), Path):
        _fail()
    # Public non-owning liveness check: no __exit__, connection or private043 data.
    Store.__enter__(store)
    path = store.db.resolve(strict=True)
    if not path.is_file():
        _fail('unavailable')
    stat = path.stat()
    return str(store.root.resolve()), str(path), stat.st_dev, stat.st_ino


@dataclass(slots=True, repr=False)
class _Entry:
    binding: tuple
    intake_id: str
    input_id: str
    handle_id: str
    request_id: str
    deadline: float
    state: str = 'preparing'
    active: bool = True
    retire_pending: bool = False
    prepared: object = None
    request: object = None


class ReferenceReviewActions:
    """Process-local finite preparations; construction is through the factory."""
    __slots__ = ('_store', '_catalog', '_identity', '_epochs', '_lock', '_read', '_write',
                 '_inputs', '_parents', '_entries', '_pending', '_active', '_closing', '_closed')

    def __init__(self, token=None, *, store=None, catalog=None, identity=None, epochs=None,
                 lock=None, read=(), write=(), inputs=None, parents=None):
        if token is not _TOKEN:
            _fail()
        self._store, self._catalog, self._identity = store, catalog, identity
        self._epochs, self._lock, self._read, self._write = epochs, lock, read, write
        self._inputs, self._parents = inputs, parents
        self._entries, self._pending = {}, {}
        self._active, self._closing, self._closed = 0, False, False

    def __repr__(self):
        return '<ReferenceReviewActions>'

    def __reduce_ex__(self, protocol):
        _fail()

    def _binding(self, value):
        if value is None:
            _fail('access_denied')
        value = _copy(value, 16384, 8, 256)
        _keys(value, ('host_epoch', 'session_id', 'scope_epoch'))
        for item in value.values():
            _sha(item)
        if (value['host_epoch'], value['scope_epoch']) != self._epochs:
            _fail('access_denied')
        return value['host_epoch'], value['session_id'], value['scope_epoch']

    def _admit(self, intake_id, *, append=False):
        if self._closing:
            _fail('unavailable')
        if self._store is None or self._catalog is None or not self._inputs:
            _fail('unconfigured')
        if not _permits(self._read, intake_id) or append and not _permits(self._write, intake_id):
            _fail('access_denied')
        if intake_id not in self._inputs:
            _fail('review_input_unavailable')

    def _check_origin(self):
        if _identity(self._store) != self._identity:
            _fail('request_conflict')

    def _purge(self, now):
        for table in (self._entries, self._pending):
            for handle_id, entry in tuple(table.items()):
                if now >= entry.deadline:
                    entry.retire_pending = True
                if entry.retire_pending and not entry.active:
                    entry.state = 'retired'
                    del table[handle_id]

    def _entry(self, binding, handle_id, intake_id):
        entry = self._entries.get(handle_id)
        if entry is None or entry.retire_pending:
            _fail('prepared_unavailable')
        if entry.binding != binding:
            _fail('access_denied')
        if entry.intake_id != intake_id:
            _fail('request_conflict')
        return entry

    def _new_ids(self):
        occupied = {entry.request_id for entry in (*self._entries.values(), *self._pending.values())}
        for _ in range(8):
            handle, request = secrets.token_hex(32), 'REF-' + secrets.token_hex(32)
            if handle not in self._entries and handle not in self._pending and request not in occupied:
                return handle, request
        _fail('unavailable')

    @_public
    def capabilities(self, session_binding, intake_id):
        _id(intake_id)
        closed = {'prepare_allowed': False, 'append_allowed': False, 'review_input_id': None}
        if session_binding is None:
            return closed
        self._binding(session_binding)
        with self._lock:
            if self._closing or self._store is None or self._catalog is None or not _permits(self._read, intake_id):
                return closed
            source = self._inputs.get(intake_id)
            if source is None:
                return closed
            return {'prepare_allowed': True, 'append_allowed': _permits(self._write, intake_id), 'review_input_id': source[0]}

    @_public
    def prepare(self, session_binding, intake_id, request):
        _id(intake_id)
        binding = self._binding(session_binding)
        with self._lock:
            self._admit(intake_id)
        request = _copy(request, 16384, 8, 256)
        _keys(request, ('schema_version', 'review_input_id', 'replace_handle_id'))
        _integer(request['schema_version'], maximum=1, code='invalid_request')
        _sha(request['review_input_id'])
        _sha(request['replace_handle_id'], True)
        self._check_origin()
        old = None
        with self._lock:
            self._admit(intake_id)
            source = self._inputs[intake_id]
            if request['review_input_id'] != source[0]:
                _fail('request_conflict')
            now = _clock()
            self._purge(now)
            if request['replace_handle_id'] is not None:
                old = self._entry(binding, request['replace_handle_id'], intake_id)
                if old.state in ('appending', 'uncertain'):
                    _fail('request_conflict')
                if old.active:
                    _fail('unavailable', 429)
            elif (len(self._entries) + 1) * _HANDLE_RESERVATION > _RETAINED_LIMIT or sum(e.binding == binding for e in self._entries.values()) >= 2:
                _fail('unavailable')
            handle_id, request_id = self._new_ids()
            candidate = _Entry(binding, intake_id, source[0], handle_id, request_id, now + 900)
            if old is None:
                self._entries[handle_id] = candidate
                old_state = None
            else:
                old_state = old.state
                old.state, old.active = 'replacing', True
                self._pending[handle_id] = candidate
            self._active += 1
        published = False
        try:
            prepared, preview = self._parents[0](self._store, self._catalog, intake_id,
                case_context=json.loads(source[1]), validated_response=json.loads(source[2]),
                producer_name=source[3], allow_retained_reads=True)
            if type(prepared) is not self._parents[2]:
                _fail('unavailable')
            preview = _preview(preview, intake_id)
            self._check_origin()
            original = {'schema_version': 1, 'intake_id': intake_id, 'request_id': request_id,
                'preparation_id': preview['preparation_id'], 'expected_snapshot_id': preview['observation']['snapshot_id'],
                'expected_head_record_id': preview['observation']['head_record_id']}
            envelope = _copy({'schema_version': 1, 'kind': 'intake_reference_preparation_handle',
                'handle_id': handle_id, 'append_request_id': request_id, 'expires_in_seconds': 1, 'preview': preview},
                64*1024, 16, 10000, 'unavailable')
            with self._lock:
                now = _clock()
                if self._closing:
                    _fail('unavailable')
                if candidate.retire_pending or now >= candidate.deadline or old is not None and (old.retire_pending or now >= old.deadline):
                    _fail('prepared_unavailable')
                candidate.prepared, candidate.request, candidate.state = prepared, original, 'ready'
                if old is not None:
                    old.state = 'retired'
                    del self._entries[old.handle_id]
                    self._pending.pop(handle_id)
                    self._entries[handle_id] = candidate
                envelope['expires_in_seconds'] = min(900, math.ceil(candidate.deadline - now))
                published = True
                return envelope
        finally:
            with self._lock:
                self._active -= 1
                candidate.active = False
                self._pending.pop(handle_id, None)
                if not published:
                    self._entries.pop(handle_id, None)
                if old is not None:
                    old.active = False
                    if not published:
                        if not old.retire_pending and not self._closing and _clock() < old.deadline:
                            old.state = old_state
                        else:
                            self._entries.pop(old.handle_id, None)
                self._purge(_clock())

    @_public
    def append(self, session_binding, intake_id, request):
        _id(intake_id)
        binding = self._binding(session_binding)
        with self._lock:
            self._admit(intake_id, append=True)
        request = _copy(request, 16384, 8, 256)
        _keys(request, _APPEND_REQUEST)
        _integer(request['schema_version'], maximum=1, code='invalid_request')
        for key in ('handle_id', 'preparation_id', 'expected_snapshot_id'):
            _sha(request[key])
        _sha(request['expected_head_record_id'], True)
        for key in ('intake_id', 'request_id'):
            _id(request[key])
        self._check_origin()
        with self._lock:
            self._admit(intake_id, append=True)
            self._purge(_clock())
            entry = self._entry(binding, request['handle_id'], intake_id)
            if entry.active:
                _fail('unavailable', 429)
            original = {key: value for key, value in request.items() if key != 'handle_id'}
            if original != entry.request:
                _fail('request_conflict')
            prior = entry.state
            entry.state, entry.active = 'appending', True
            self._active += 1
        dispatched = False
        succeeded = False
        try:
            dispatched = True
            result = self._parents[1](self._store, self._catalog, entry.prepared, dict(entry.request),
                allow_retained_reads=True, allow_append=True)
            result = _registration(result, entry.request)
            succeeded = True
            return result
        finally:
            with self._lock:
                entry.state = 'recorded' if succeeded else 'uncertain' if dispatched else prior
                entry.active = False
                self._active -= 1
                self._purge(_clock())

    @_public
    def discard_session(self, session_binding):
        binding = self._binding(session_binding)
        with self._lock:
            for table in (self._entries, self._pending):
                for entry in tuple(table.values()):
                    if entry.binding == binding:
                        entry.retire_pending = True
            self._purge(_clock())

    @_public
    def close(self):
        with self._lock:
            if self._closed:
                return None
            self._closing = True
            for table in (self._entries, self._pending):
                for entry in table.values():
                    entry.retire_pending = True
            if self._active:
                _fail('unavailable')
            self._entries.clear()
            self._pending.clear()
            self._inputs.clear()
            self._parents = self._store = self._catalog = self._identity = None
            self._closed = True


@_public
def create_reference_review_actions(store, catalog, *, host_epoch, scope_epoch,
                                  runtime_lock, read_scope=(), append_scope=(), review_inputs=()):
    """Capture trusted fixed inputs and official parents without source/DB I/O."""
    _sha(host_epoch)
    _sha(scope_epoch)
    if type(runtime_lock) is not _LOCK_TYPE:
        _fail()
    read, write = _scope(read_scope), _scope(append_scope)
    inputs = _inputs(review_inputs)
    if store is not None and type(store) is not Store:
        _fail()
    if catalog is not None:
        from .fcc_report_cases import FccReportCaseCatalog
        if type(catalog) is not FccReportCaseCatalog:
            _fail()
    if inputs and (store is None or catalog is None):
        _fail()
    identity = None
    parents = None
    if store is not None and catalog is not None and inputs:
        identity = _identity(store)
        if read:
            from .intake_reference_review import prepare_reference_review, append_reference_review, PreparedReferenceReview
            parents = (prepare_reference_review, append_reference_review, PreparedReferenceReview)
    return ReferenceReviewActions(_TOKEN, store=store, catalog=catalog, identity=identity,
        epochs=(host_epoch, scope_epoch), lock=runtime_lock, read=read, write=write, inputs=inputs, parents=parents)
