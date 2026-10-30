"""One explicitly delegated synthetic intake; fixture worker remains unchanged.

The host owns the borrowed Store, approval, cumulative budget and private root.
There is no import-time run, CLI entry point, polling, provider hook or retry.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

from .codex_cli_response import CodexCliResponseError, produce_codex_cli_response, _client_versions_match
from .intake_jobs import claim_job, complete_job, fail_job
from .intake_model_boundary import (
    build_analysis_prompt, build_analysis_response_schema, decode_analysis_response,
)
from .store import Store, canonical, identifier


_PREFIX = 'codex_intake_once_'
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_PUBLIC = ('job_id', 'intake_id', 'revision', 'synthetic', 'documents',
           'analysis_context_id', 'analysis_contract', 'instructions')
_MODELS = ('gpt-6.1-sol', 'gpt-6-astra')
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_EXCHANGE = re.compile(r'codex-cli-exchange:[a-f0-9]{32}\Z')
_BOUNDARY_CODES = {'analysis_context_invalid', 'analysis_context_limit', 'analysis_producer_invalid',
                   'analysis_response_invalid', 'analysis_response_limit'}
_D2_CODES = {'codex_cli_response_' + code for code in (
    'invalid_input', 'limit_exceeded', 'unsupported_client', 'evidence_error', 'spawn_failed',
    'timeout', 'stream_invalid', 'process_failed', 'final_mismatch', 'cleanup_failed', 'internal_error')}
_LAYOUT = dict(prompt='request.json', response_schema='response-schema.json', invocation='invocation.json',
               version_stdout='version.stdout', version_stderr='version.stderr', stdout_jsonl='stdout.jsonl',
               stderr='stderr.bin', final_text='final-text.bin', last_message='last-message.bin')
_RECEIPT_KEYS = set('schema_version kind exchange_ref status failure bindings client model attempts lifecycle '
                    'usage cost timing controls cleanup artifacts limits verification'.split())


class _Failure(Exception):
    def __init__(self, suffix):
        self.code = _PREFIX + suffix


def _fail(suffix):
    raise _Failure(suffix)


def _C(value):
    return canonical(value).encode('utf-8')


def _H(value):
    return hashlib.sha256(value).hexdigest()


def _integer(value, expected=None):
    return type(value) is int and (value == expected if expected is not None else 0 <= value <= 2**63 - 1)


def _reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _path(path, *, directory):
    if type(path) is not type(Path()) or not path.is_absolute() or '..' in path.parts:
        _fail('invalid_input')
    for parent in reversed(path.parents):
        info = parent.lstat()
        if _reparse(info) or not stat.S_ISDIR(info.st_mode):
            _fail('invalid_input')
    info = path.lstat()
    if _reparse(info) or (not stat.S_ISDIR(info.st_mode) if directory else
                          not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        _fail('invalid_input')
    return info


def _write_new(path, value):
    payload = _C(value)
    if len(payload) > 65536:
        _fail('evidence_error')
    stream = path.open('xb')
    try:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    except BaseException:
        try:
            stream.close()
        except BaseException:
            pass
        raise
    else:
        stream.close()


def _read(path, limit):
    before = _path(path, directory=False)
    if before.st_size > limit:
        _fail('receipt_binding_mismatch')
    stream = path.open('rb')
    try:
        actual = os.fstat(stream.fileno())
        if (actual.st_dev, actual.st_ino) != (before.st_dev, before.st_ino):
            _fail('receipt_binding_mismatch')
        payload = stream.read(limit + 1)
    except BaseException:
        try:
            stream.close()
        except BaseException:
            pass
        raise
    else:
        stream.close()
    after = path.lstat()
    if (len(payload) > limit or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        _fail('receipt_binding_mismatch')
    return payload


def _receipt_snapshot(value):
    if type(value) is not dict:
        _fail('receipt_binding_mismatch')
    try:
        data = _C(value)
        if len(data) > 65536:
            _fail('receipt_binding_mismatch')
        stack = [(value, 0)]
        count = 0
        while stack:
            item, depth = stack.pop()
            count += 1
            if depth > 32 or count > 200000:
                _fail('receipt_binding_mismatch')
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    _fail('receipt_binding_mismatch')
                stack.extend((child, depth + 1) for child in item.values())
            elif type(item) is list:
                stack.extend((child, depth + 1) for child in item)
            elif type(item) is int:
                if not -2**63 <= item <= 2**63 - 1:
                    _fail('receipt_binding_mismatch')
            elif type(item) is float:
                if not math.isfinite(item):
                    _fail('receipt_binding_mismatch')
            elif item is not None and type(item) not in (str, bool):
                _fail('receipt_binding_mismatch')
        return json.loads(data), data
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        _fail('receipt_binding_mismatch')


def _observe_attempts(record, receipt):
    attempts = receipt.get('attempts') if type(receipt) is dict else None
    for key in ('version_process_attempts', 'model_process_attempts'):
        value = attempts.get(key) if type(attempts) is dict else None
        record['attempts'][key] = value if type(value) is int and value in (0, 1) else None


def _verify(response, receipt, prompt, schema, declaration, model, directory):
    value, encoded = _receipt_snapshot(receipt)
    try:
        if (type(response) is not bytes or len(response) > 2097152 or set(value) != _RECEIPT_KEYS or
                not _integer(value['schema_version'], 1) or value['kind'] != 'codex_cli_response_receipt' or
                value['status'] != 'complete' or value['failure'] is not None or
                type(value['exchange_ref']) is not str or not _EXCHANGE.fullmatch(value['exchange_ref'])):
            _fail('receipt_binding_mismatch')
        bindings, attempts = value['bindings'], value['attempts']
        if (bindings['prompt_sha256'] != _H(prompt) or bindings['schema_sha256'] != _H(schema) or
                _C(bindings['producer_declaration']) != _C(declaration) or
                not _integer(attempts['version_process_attempts'], 1) or
                not _integer(attempts['model_process_attempts'], 1) or not _integer(attempts['application_retries'], 0) or
                value['model']['requested'] != model or value['model']['resolved'] is not None or
                value['model']['remote_request_id'] is not None or type(value['model']['cli_thread_id']) is not str or
                not value['model']['cli_thread_id'] or
                not _client_versions_match(value['client']['supported_version'], value['client']['observed_version'])):
            _fail('receipt_binding_mismatch')
        life, cleanup, observed = value['lifecycle'], value['cleanup'], value['controls']['observed']
        if (any(not _integer(life[key], 1) for key in ('thread_started', 'turn_started', 'turn_completed', 'agent_messages')) or
                not _integer(life['exit_code'], 0) or not _integer(life['tool_items'], 0) or
                any(life[key] is not True for key in ('model_process_started', 'stdout_eof', 'stderr_eof')) or
                any(cleanup[key] is not True for key in ('version_child_reaped', 'model_child_reaped', 'readers_joined', 'pipes_closed', 'artifacts_closed')) or
                cleanup['secondary_errors'] != [] or
                any(observed[key] is not True for key in ('argv_submitted', 'argv_exit0', 'empty_cwd_at_spawn')) or
                not _integer(observed['tool_items'], 0) or value['verification']['wire_complete'] is not True or
                any(value['verification'][key] is not False for key in ('remote_identity_verified', 'semantic_quality_verified',
                    'external_data_authority_verified', 'storage_authenticity_verified'))):
            _fail('receipt_binding_mismatch')
        artifacts = value['artifacts']
        if type(artifacts) is not dict or set(artifacts) != set(_LAYOUT):
            _fail('receipt_binding_mismatch')
        for key, name in _LAYOUT.items():
            item = artifacts[key]
            if (type(item) is not dict or item['path'] != name or not _integer(item['bytes']) or
                    type(item['sha256']) is not str or not _HASH.fullmatch(item['sha256']) or
                    item['present'] is not True or item['complete'] is not True or
                    item['overflow'] is not False or item['extent'] != 'whole_file'):
                _fail('receipt_binding_mismatch')
        if bindings['invocation_sha256'] != artifacts['invocation']['sha256']:
            _fail('receipt_binding_mismatch')
        for key, payload, cap in (('prompt', prompt, 262144), ('response_schema', schema, 65536),
                                  ('final_text', response, 2097152), ('last_message', response, 2097152)):
            item = artifacts[key]
            if item['bytes'] != len(payload) or item['sha256'] != _H(payload) or _read(directory / _LAYOUT[key], cap) != payload:
                _fail('receipt_binding_mismatch')
        if _read(directory / 'receipt.json', 65536) != encoded:
            _fail('receipt_binding_mismatch')
        return value, _H(encoded)
    except (_Failure, KeyError, TypeError, ValueError, OSError, RecursionError):
        _fail('receipt_binding_mismatch')


def _error(record, code, *, secondary=False):
    item = dict(phase=record['phase'], code=code, secondary=secondary)
    if len(record['errors']) < 4 and item not in record['errors']:
        record['errors'].append(item)


def _code(error, phase):
    if isinstance(error, _Failure):
        return error.code
    if isinstance(error, CodexCliResponseError) and error.code in _D2_CODES:
        return error.code
    if isinstance(error, ValueError) and type(error.args[0] if error.args else None) is str and error.args[0] in _BOUNDARY_CODES:
        return error.args[0]
    if phase == 'complete':
        return _PREFIX + 'completion_unknown'
    if isinstance(error, OSError) and phase in ('validation', 'finalize'):
        return _PREFIX + 'evidence_error'
    return _PREFIX + 'internal_error'


def _finalize(record, root, intent_started):
    if intent_started:
        try:
            _write_new(root / 'caller-receipt.json', record)
        except _CONTROL:
            raise
        except Exception:
            record['status'], record['phase'] = 'unknown', 'finalize'
            _error(record, _PREFIX + 'evidence_error', secondary=bool(record['errors']))
    return record


def preflight_codex_intake_once_inputs(approved_context, *, producer_name) -> dict:
    """Pure request snapshot/quality/byte checks; no state or execution authority.

    A validated result is still subject to host approval, budget and a fresh
    public claim. Unread or partial documents remain data in the generic G3
    path, but are outside this first execution scope. Never repair them here.
    """
    result = dict(schema_version=1, kind='codex_intake_once_preflight', status='blocked',
                  context=None, prompt=None, response_schema=None, pins=None,
                  failure=None, execution_authority=False)
    try:
        if (type(approved_context) is not dict or any(type(key) is not str for key in approved_context) or
                set(approved_context) != set(_PUBLIC) or approved_context.get('synthetic') is not True):
            _fail('invalid_input')
        prompt = build_analysis_prompt(approved_context, producer_name=producer_name)
        context = json.loads(prompt['messages'][1]['content'])
        for document in context['documents']:
            if document.get('format') == 'pdf':
                pages = document['pages']
                if (document['parse_status'] != 'ok' or document['complete'] is not True or document['issues'] or
                        type(document['total_pages']) is not int or document['total_pages'] < 1 or
                        document['total_pages'] != document['processed_pages'] or document['total_pages'] != len(pages) or
                        any(page['page_number'] != number or page['status'] != 'ok' or not page['text'].strip()
                            for number, page in enumerate(pages, 1))):
                    _fail('unsupported_schema')
            elif (document.get('format', 'text') != 'text' or document['parse_status'] != 'text' or
                  not (document['text'] or '').strip() or
                  document.get('extraction_status', 'ok') != 'ok' or document.get('issues', [])):
                _fail('unsupported_schema')
        schema = build_analysis_response_schema(producer_name=producer_name, context=context)
        prompt_bytes, schema_bytes = _C(prompt), _C(schema)
        if len(prompt_bytes) > 262144 or len(schema_bytes) > 65536:
            _fail('invalid_input')
        result.update(status='validated', context=context, prompt=prompt, response_schema=schema,
                      pins=dict(context_sha256=_H(_C(context)), prompt_sha256=_H(prompt_bytes),
                                schema_sha256=_H(schema_bytes)))
    except _CONTROL:
        raise
    except Exception as error:
        result['failure'] = _code(error, 'validation')
    return result


def _request_inputs(context, producer_name):
    prepared = preflight_codex_intake_once_inputs(context, producer_name=producer_name)
    if prepared['status'] != 'validated':
        code = prepared['failure']
        if code in _BOUNDARY_CODES:
            raise ValueError(code)
        raise _Failure(code[len(_PREFIX):])
    return prepared


def run_codex_intake_once(store, approved_context, *, worker_id, producer_name,
                         executable, requested_model, evidence_root, authorization_ref,
                         timeout_seconds=60.0) -> dict:
    """Claim at most one synthetic job; concrete D2 once, strict, existing completion.

    Host approval/budget and Store.close remain caller responsibilities. Never
    attach this manual function to fixture workers or an automatic retry loop.
    """
    record = dict(schema_version=1, kind='codex_intake_once_receipt', status='failed', phase='validation',
                  job=None, binding=None, attempts=dict(producer_invocations=0, version_process_attempts=0,
                                                       model_process_attempts=0, automatic_retries=0),
                  strict_decode='not_run', assessment=dict(status='not_assessed', verdict=None,
                      reason_code='manual_intake_admission_only'), errors=[])
    lease = None
    intent_started = False
    claim_entered = False
    completion_entered = False
    try:
        if (type(store) is not Store or type(worker_id) is not str or type(authorization_ref) is not str or
                type(requested_model) is not str or requested_model not in _MODELS or
                type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 60 or not math.isfinite(timeout_seconds)):
            _fail('invalid_input')
        try:
            identifier(worker_id)
            identifier(authorization_ref)
            _path(executable, directory=False)
            _path(evidence_root, directory=True)
            if executable.name.lower() != 'codex.exe' or any(evidence_root.iterdir()):
                _fail('invalid_input')
        except (OSError, ValueError, TypeError):
            _fail('invalid_input')
        approved = _request_inputs(approved_context, producer_name)
        expected, context = approved['prompt'], approved['context']
        schema = _C(approved['response_schema'])
        intent_started = True
        _write_new(evidence_root / 'attempt-intent.json', dict(kind='codex_intake_once_intent', authorization_ref=authorization_ref,
                    approved_context_sha256=_H(_C(context)), requested_model=requested_model, producer_name=producer_name))
        record['phase'] = 'claim'
        claim_entered = True
        claim = claim_job(store, worker_id, synthetic_only=True, lease_seconds=3600)
        if claim is None:
            record['status'] = 'idle'
        else:
            if (type(claim) is not dict or type(claim.get('token')) is not str or not claim['token'] or
                    any(type(claim.get(key)) is not str or not claim[key] for key in ('job_id', 'intake_id')) or
                    not _integer(claim.get('revision')) or claim['revision'] < 1 or
                    not _integer(claim.get('attempt')) or claim['attempt'] < 1):
                _fail('internal_error')
            try:
                identifier(claim['job_id'])
                identifier(claim['intake_id'])
            except ValueError:
                _fail('internal_error')
            lease = (claim['job_id'], claim['token'])
            record['job'] = {key: claim[key] for key in ('job_id', 'intake_id', 'revision', 'attempt')}
            record['phase'] = 'scope'
            public = {key: claim[key] for key in _PUBLIC}
            prepared = _request_inputs(public, producer_name)
            fresh, fresh_context = prepared['prompt'], prepared['context']
            if (_C(fresh_context) != _C(context) or _C(fresh) != _C(expected) or
                    _C(prepared['response_schema']) != schema or prepared['pins'] != approved['pins']):
                _fail('scope_mismatch')
            prompt = _C(fresh)
            record['binding'] = dict(authorization_ref=authorization_ref, context_sha256=_H(_C(fresh_context)),
                prompt_sha256=_H(prompt), schema_sha256=_H(schema), response_sha256=None,
                producer_declaration=json.loads(_C(fresh['expected_producer'])), requested_model=requested_model,
                exchange_ref=None, producer_receipt_sha256=None)
            record['phase'] = 'producer'
            record['attempts'].update(producer_invocations=1, version_process_attempts=None, model_process_attempts=None)
            try:
                result = produce_codex_cli_response(prompt, schema, executable=executable,
                    requested_model=requested_model, evidence_dir=evidence_root / 'exchange', timeout_seconds=timeout_seconds)
            except CodexCliResponseError as error:
                _observe_attempts(record, error.receipt)
                raise
            record['phase'] = 'receipt'
            if type(result) is not tuple or len(result) != 2:
                _fail('receipt_binding_mismatch')
            response, receipt = result
            _observe_attempts(record, receipt)
            receipt, receipt_sha = _verify(response, receipt, prompt, schema, fresh['expected_producer'],
                                            requested_model, evidence_root / 'exchange')
            record['binding'].update(response_sha256=_H(response), exchange_ref=receipt['exchange_ref'], producer_receipt_sha256=receipt_sha)
            record['phase'] = 'decode'
            try:
                analysis = decode_analysis_response(response, fresh_context, producer_name=producer_name)
            except _CONTROL:
                raise
            except Exception:
                record['strict_decode'] = 'rejected'
                raise
            record['strict_decode'] = 'accepted'
            try:
                _write_new(evidence_root / 'job-binding.json', dict(kind='codex_intake_job_binding', job=record['job'], binding=record['binding']))
            except _CONTROL:
                raise
            except Exception:
                _fail('evidence_error')
            record['phase'] = 'complete'
            completion_entered = True
            complete_job(store, lease[0], lease[1], analysis)
            record['status'], record['phase'] = 'completed', 'finalize'
    except _CONTROL:
        record['status'] = 'unknown'
        _error(record, _PREFIX + 'internal_error')
        try:
            _finalize(record, evidence_root, intent_started)
        except BaseException:
            pass
        raise
    except Exception as error:
        _error(record, _code(error, record['phase']))
        record['status'] = 'unknown' if completion_entered or claim_entered and lease is None else 'failed'
        if lease is not None and not completion_entered:
            try:
                fail_job(store, lease[0], lease[1])
            except _CONTROL:
                record['status'] = 'unknown'
                _error(record, _PREFIX + 'job_finalize_failed', secondary=True)
                try:
                    _finalize(record, evidence_root, intent_started)
                except BaseException:
                    pass
                raise
            except Exception:
                record['status'] = 'unknown'
                _error(record, _PREFIX + 'job_finalize_failed', secondary=True)
    return _finalize(record, evidence_root, intent_started)
