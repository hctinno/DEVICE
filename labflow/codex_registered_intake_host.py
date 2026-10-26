"""Native operator entry for one registered synthetic Codex intake.

Authority comes from the fixed local operator source and existing delegation.
The host never creates a journal, baseline, permit, Store, or global budget.
"""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import sys
import uuid

from .codex_intake_once import preflight_codex_intake_once_inputs, run_codex_intake_once
from .intake_jobs import prepare_registered_synthetic_context
from .store import Store, StoreOpenError, canonical, identifier


__all__ = ['main']
_PREFIX = 'codex_registered_intake_host_'
_ANCHOR = 'root-continuation-anchor-20261026-v1.json'
_MODELS = ['gpt-6.1-sol', 'gpt-6-astra']
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_SHA = re.compile('[a-f0-9]{64}\\Z')
_EVENTS = {'baseline', 'permit', 'reserved', 'consumed', 'finished'}
_HELP = ('Usage: python -B -m labflow.codex_registered_intake_host '
         '--scenario-id ID --model gpt-6.1-sol|gpt-6-astra\n'
         'Fixed current-account operator control; one existing single-use permit.\n')


class _Failure(ValueError):
    pass


def _fail(code):
    raise _Failure(_PREFIX + code)


def _C(value):
    return canonical(value).encode('utf-8')


def _H(data):
    return hashlib.sha256(data).hexdigest()


def _keys(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        _fail('invalid_policy')


def _id(value):
    if type(value) is not str:
        _fail('invalid_policy')
    try:
        identifier(value)
    except ValueError:
        _fail('invalid_policy')


def _hash(value):
    if type(value) is not str or not _SHA.fullmatch(value):
        _fail('invalid_policy')


def _int(value, minimum=0, maximum=2**63-1):
    return type(value) is int and minimum <= value <= maximum


def _control_root():
    # Windows resolves the current token, not argv/LOCALAPPDATA/USERPROFILE.
    if os.name != 'nt':
        _fail('unsupported_platform')
    folder = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID('f1b32785-6fba-4fcf-9d55-7b8e7f157091').bytes_le)
    result = ctypes.c_void_p()
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    free = ctypes.WinDLL('ole32').CoTaskMemFree
    free.argtypes, free.restype = [ctypes.c_void_p], None
    shell.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    failure=None
    try:
        if shell.SHGetKnownFolderPath(ctypes.byref(folder), 0, None, ctypes.byref(result)) != 0 or not result.value:
            _fail('operator_unavailable')
        return Path(ctypes.wstring_at(result.value)) / 'DGMAutoLab' / 'codex-intake-host'
    except BaseException as error:
        failure=error
        raise
    finally:
        if result.value:
            try:free(result)
            except BaseException:
                if failure is None:raise


def _path(value, *, directory):
    if type(value) is str:
        value = Path(value)
    if type(value) is not type(Path()) or not value.is_absolute() or '..' in value.parts:
        _fail('invalid_path')
    if (not re.fullmatch('[A-Za-z]:', value.drive) or any(
            part in ('.', '..') or part.endswith((' ', '.')) or any(c in '<>:"|?*' or ord(c)<32 for c in part)
            for part in value.parts[1:])):
        _fail('invalid_path')
    for parent in reversed(value.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_file_attributes & 0x400:
            _fail('invalid_path')
    info = value.lstat()
    if (info.st_file_attributes & 0x400 or stat.S_ISLNK(info.st_mode) or
            (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)):
        _fail('invalid_path')
    return value, info


def _read(path, cap):
    path, before = _path(path, directory=False)
    if before.st_size > cap:
        _fail('input_limit')
    stream = path.open('rb')
    try:
        actual = os.fstat(stream.fileno())
        if (actual.st_dev, actual.st_ino, actual.st_size) != (before.st_dev, before.st_ino, before.st_size):
            _fail('source_changed')
        data = stream.read(cap+1)
    except BaseException:
        try:
            stream.close()
        except BaseException:
            pass
        raise
    else:
        stream.close()
    _, after = _path(path, directory=False)
    if (len(data) > cap or len(data) != before.st_size or
            (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) !=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)):
        _fail('source_changed')
    return data


def _json(data):
    def pairs(items):
        value = {}
        for key, child in items:
            if key in value:
                _fail('invalid_policy')
            value[key] = child
        return value
    def constant(value):
        _fail('invalid_policy')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        pending, count = [(value,0)], 0
        while pending:
            item, depth = pending.pop();count += 1
            if depth > 24 or count > 50000 or type(item) is int and not -2**63 <= item <= 2**63-1:
                _fail('input_limit')
            if type(item) is dict:
                pending.extend((v,depth+1) for v in item.values())
            elif type(item) is list:
                pending.extend((v,depth+1) for v in item)
            elif type(item) is float and not math.isfinite(item):
                _fail('invalid_policy')
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError):
        _fail('invalid_policy')


def _anchor(value, root):
    _keys(value, 'schema_version kind recorded_at_kst state authority_source scope inherited_history admission trust_boundary '
          'new_model_processes original_receipt_or_customer_body_reads registration_created cumulative_journal_seeded new_budget_or_active_permit_issued')
    if (not _int(value['schema_version'],1,1) or value['kind'] != 'codex_intake_root_operator_continuation_anchor'
            or not _int(value['new_model_processes'],0,0) or not _int(value['original_receipt_or_customer_body_reads'],0,0)
            or any(value[k] is not False for k in ('registration_created','cumulative_journal_seeded','new_budget_or_active_permit_issued'))):
        _fail('invalid_policy')
    authority, scope, history, boundary = (value[k] for k in ('authority_source','scope','inherited_history','trust_boundary'))
    _keys(authority, 'kind instruction_reference authority_is_not_inferred_from_uploaded_documents_or_model_output')
    if (authority['kind'] != 'direct_human_instructions_to_this_root_thread' or
            type(authority['instruction_reference']) is not str or not authority['instruction_reference'].strip() or
            authority['authority_is_not_inferred_from_uploaded_documents_or_model_output'] is not True):
        _fail('invalid_policy')
    _keys(scope, 'action allowed_models maximum_attempts_per_once timeout_seconds_maximum automatic_retries '
          'scope_is_existing_delegation_not_new_global_budget customer_originals_or_decryption_external_transmission hardware_network_output_motion_submission')
    if (scope['action'] != 'one_registered_synthetic_intake_run' or scope['allowed_models'] != _MODELS or
            not _int(scope['maximum_attempts_per_once'],1,1) or not _int(scope['timeout_seconds_maximum'],60,60) or
            not _int(scope['automatic_retries'],0,0) or scope['scope_is_existing_delegation_not_new_global_budget'] is not True or
            scope['customer_originals_or_decryption_external_transmission'] is not False or scope['hardware_network_output_motion_submission'] is not False):
        _fail('invalid_policy')
    _keys(history, 'actual_codex_model_processes known_total_before_this_host unknown_usage_components usage_complete cost '
          'provenance_level source_rollup published_source')
    if (not _int(history['actual_codex_model_processes'],16) or history['known_total_before_this_host'] != history['actual_codex_model_processes'] or
            type(history['known_total_before_this_host']) is not int or history['usage_complete'] is not False or history['cost'] is not None or
            history['unknown_usage_components'] is not None or
            history['provenance_level'] != 'previous_verified_root_rollup_not_fresh_original_receipt_reaudit'):
        _fail('invalid_history')
    for name, fields in [('source_rollup','path bytes sha256'), ('published_source','commit path bytes sha256')]:
        item = history[name];_keys(item, fields);_hash(item['sha256'])
        if not _int(item['bytes'],1) or type(item['path']) is not str:
            _fail('invalid_history')
    _keys(boundary, 'operator_control_directory customer_input_argv_env_cannot_select_control_source native_operator_local_account_boundary '
          'protection_against_same_account_arbitrary_code_execution')
    if (boundary['operator_control_directory'] != str(root) or boundary['customer_input_argv_env_cannot_select_control_source'] is not True or
            boundary['native_operator_local_account_boundary'] is not True or boundary['protection_against_same_account_arbitrary_code_execution'] is not False):
        _fail('invalid_policy')
    admission = value['admission']
    _keys(admission, 'registered_input_root registration_manifest existing_store cumulative_journal reservation permitted_to_dispatch_now '
          'missing_registration_or_journal_is_not_run actual_global_call_cap global_cap_unknown_does_not_mean_unlimited '
          'exhausted_Vertex_ledger_is_separate_and_must_not_be_read_or_modified')
    if (any(admission[k] is not None for k in ('registered_input_root','registration_manifest','existing_store','cumulative_journal','reservation','actual_global_call_cap')) or
            admission['permitted_to_dispatch_now'] is not False or any(admission[k] is not True for k in (
                'missing_registration_or_journal_is_not_run','global_cap_unknown_does_not_mean_unlimited',
                'exhausted_Vertex_ledger_is_separate_and_must_not_be_read_or_modified'))):
        _fail('invalid_policy')


def _registration(root, config, scenario):
    data = _read(root/'registered-intake-v1.json',256*1024)
    if _H(data) != config['registration_sha256']:
        _fail('registration_changed')
    manifest = _json(data)
    _keys(manifest, 'schema_version kind scenario_id synthetic registered_intake')
    if (not _int(manifest['schema_version'],1,1) or manifest['kind'] != 'codex_registered_synthetic_intake'
            or manifest['scenario_id'] != scenario or manifest['synthetic'] is not True):
        _fail('registration_mismatch')
    selection = manifest['registered_intake']
    _keys(selection, 'source_id intake_id revision job_id revision_fingerprint files')
    for key in ('source_id','intake_id','job_id'):
        _id(selection[key])
    _hash(selection['revision_fingerprint'])
    files = selection['files']
    if not _int(selection['revision'],1) or type(files) is not list or not 1 <= len(files) <= 1000:
        _fail('registration_mismatch')
    names, total = set(), 0
    for item in files:
        _keys(item, 'path sha256 bytes');_hash(item['sha256'])
        name = item['path']
        if (type(name) is not str or not name or '\\' in name or PurePosixPath(name).is_absolute()
                or any(part in ('','.','..') for part in name.split('/')) or not _int(item['bytes'],0,32*1024*1024)):
            _fail('registration_mismatch')
        if name.casefold() in names:
            _fail('registration_mismatch')
        names.add(name.casefold());total += item['bytes']
    if total > 128*1024*1024 or _H(_C(files)) != selection['revision_fingerprint']:
        _fail('registration_mismatch')
    original, _ = _path(config['registered_input_root'], directory=True)
    observed, pending, directories = set(), [original], 0
    while pending:
        directory = pending.pop();directories += 1
        if directories > 1000:
            _fail('input_limit')
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path);info = path.lstat()
                if info.st_file_attributes & 0x400 or stat.S_ISLNK(info.st_mode):
                    _fail('invalid_path')
                if stat.S_ISDIR(info.st_mode):
                    if len(path.relative_to(original).parts) > 32:
                        _fail('input_limit')
                    pending.append(path)
                else:
                    observed.add(path.relative_to(original).as_posix().casefold())
                    if len(observed)>1000 or not stat.S_ISREG(info.st_mode):
                        _fail('input_limit')
    if observed != names:
        _fail('registration_changed')
    for item in files:
        payload = _read(original/item['path'],32*1024*1024)
        if len(payload) != item['bytes'] or _H(payload) != item['sha256']:
            _fail('registration_changed')
    return selection


def _expiry(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value, re.ASCII):
        _fail('invalid_policy')
    try:
        deadline = datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        _fail('invalid_policy')
    if datetime.now(timezone.utc) >= deadline:
        _fail('permit_expired')


def _permit_shape(value):
    _keys(value, 'schema_version kind journal_id permit_id anchor_sha256 scenario_id requested_model registration_sha256 '
          'store_root worker_id producer_name maximum_model_processes timeout_seconds automatic_retries expires_at')
    for key in ('journal_id','permit_id','scenario_id','worker_id'):
        _id(value[key])
    for key in ('anchor_sha256','registration_sha256'):
        _hash(value[key])
    if (not _int(value['schema_version'],1,1) or value['kind']!='codex_intake_single_use_permit' or
            value['requested_model'] not in _MODELS or not _int(value['maximum_model_processes'],1,1) or
            not _int(value['automatic_retries'],0,0) or type(value['timeout_seconds']) not in (int,float) or
            not 0<value['timeout_seconds']<=60 or not math.isfinite(value['timeout_seconds']) or
            type(value['store_root']) is not str or type(value['producer_name']) is not str or
            not value['producer_name'].strip() or len(value['producer_name'])>200 or type(value['expires_at']) is not str):
        _fail('invalid_policy')


def _pin(value, raw):
    _keys(value,'bytes sha256');_hash(value['sha256'])
    if not _int(value['bytes'],0,65536) or value['bytes']!=len(raw) or value['sha256']!=_H(raw):
        _fail('partial_evidence')


def _history(con, anchor, config, root):
    if [tuple(row[1:3]) for row in con.execute('PRAGMA table_info(codex_intake_history)')] != [
            ('seq','INTEGER'),('kind','TEXT'),('permit_id','TEXT'),('payload','TEXT')]:
        _fail('invalid_history')
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' LIMIT 1").fetchone():
        _fail('invalid_history')
    rows = con.execute('SELECT seq,kind,permit_id,payload FROM codex_intake_history ORDER BY seq LIMIT 4097').fetchall()
    if not 1 <= len(rows) <= 4096:
        _fail('invalid_history')
    events, byte_count = {}, 0
    for number, (seq, kind, permit_id, text) in enumerate(rows,1):
        if seq != number or kind not in _EVENTS or type(text) is not str:
            _fail('invalid_history')
        data = text.encode('utf-8');byte_count += len(data)
        if len(data)>65536 or byte_count>32*1024*1024:
            _fail('input_limit')
        value = _json(data)
        if _C(value) != data or (kind,permit_id) in events:
            _fail('invalid_history')
        if kind == 'baseline':
            if seq != 1 or permit_id is not None:
                _fail('invalid_history')
            _keys(value, 'schema_version kind journal_id anchor_sha256 inherited_history')
            if (not _int(value['schema_version'],1,1) or value['kind'] != 'codex_intake_continuation_baseline' or
                    value['journal_id'] != config['journal_id'] or value['anchor_sha256'] != config['anchor_sha256'] or
                    _C(value['inherited_history']) != _C(anchor['inherited_history'])):
                _fail('invalid_history')
        else:
            _id(permit_id)
            if not ('baseline',None) in events or value.get('permit_id') != permit_id:
                _fail('invalid_history')
            previous = {'reserved':'permit','consumed':'reserved','finished':'consumed'}.get(kind)
            if previous and (previous,permit_id) not in events:
                _fail('invalid_history')
            if kind=='permit':
                _permit_shape(value)
                if value['journal_id']!=config['journal_id'] or value['anchor_sha256']!=config['anchor_sha256']:
                    _fail('invalid_history')
            elif kind=='reserved':
                _keys(value,'permit_id context_sha256 registration_sha256 store_root requested_model reserved_model_attempts')
                _hash(value['context_sha256'])
                parent=events['permit',permit_id]
                if (any(value[k]!=parent[k] for k in ('registration_sha256','store_root','requested_model')) or
                        not _int(value['reserved_model_attempts'],1,1)):
                    _fail('invalid_history')
            elif kind=='consumed':
                _keys(value,'permit_id reservation_sha256')
                if value['reservation_sha256']!=_H(_C(events['reserved',permit_id])):
                    _fail('invalid_history')
            elif kind=='finished':
                _keys(value,'permit_id status local_model_processes cleanup_confirmed producer_receipt caller_receipt once errors')
                if (value['status'] not in ('completed','failed','unknown') or
                        value['local_model_processes'] is not None and not _int(value['local_model_processes'],0,1) or
                        type(value['cleanup_confirmed']) is not bool or type(value['errors']) is not list or len(value['errors'])>4):
                    _fail('invalid_history')
                once=value['once']
                if once is not None:
                    _keys(once,'schema_version kind status phase job binding attempts strict_decode assessment errors')
                    _keys(once['attempts'],'producer_invocations version_process_attempts model_process_attempts automatic_retries')
                    if (not _int(once['schema_version'],1,1) or once['kind']!='codex_intake_once_receipt' or
                            once['status'] not in ('completed','idle','failed','unknown') or
                            not _int(once['attempts']['producer_invocations'],0,1) or not _int(once['attempts']['automatic_retries'],0,0)):
                        _fail('invalid_history')
                    for key in ('version_process_attempts','model_process_attempts'):
                        if once['attempts'][key] is not None and not _int(once['attempts'][key],0,1):
                            _fail('invalid_history')
                if value['status']=='completed' and (once is None or once['status']!='completed' or
                        once['strict_decode']!='accepted' or value['local_model_processes']!=1 or
                        value['cleanup_confirmed'] is not True or value['producer_receipt'] is None or value['caller_receipt'] is None):
                    _fail('partial_evidence')
                evidence=root/'runs'/permit_id
                for key,name in [('producer_receipt','exchange/receipt.json'),('caller_receipt','caller-receipt.json')]:
                    if value[key] is not None:
                        raw=_read(evidence/name,65536);_pin(value[key],raw)
                        if key=='caller_receipt' and (once is None or raw!=_C(once)):
                            _fail('partial_evidence')
                if value['local_model_processes']==1 and value['producer_receipt'] is None:
                    _fail('partial_evidence')
                if value['status']!='unknown' and (value['caller_receipt'] is None or not value['cleanup_confirmed']):
                    _fail('partial_evidence')
        events[kind,permit_id] = value
    inherited = anchor['inherited_history']['actual_codex_model_processes']
    finished = [v for (kind,_),v in events.items() if kind == 'finished']
    for value in finished:
        actual = value.get('local_model_processes')
        if actual is not None and not _int(actual,0,1) or value.get('status') not in ('completed','failed','unknown'):
            _fail('invalid_history')
    unknown = sum(v['local_model_processes'] is None for v in finished)
    pending = {permit for (kind,permit) in events if kind in ('reserved','consumed') and ('finished',permit) not in events}
    unsettled = pending | {permit for (kind,permit),value in events.items() if kind=='finished' and
        (value['local_model_processes'] is None or value['status']=='unknown' or value.get('cleanup_confirmed') is not True)}
    known = inherited + sum(v['local_model_processes'] or 0 for v in finished)
    summary = dict(inherited_model_processes=inherited,known_total_model_processes=known,
        actual_total_model_processes=known if not unknown and not pending else None,
        unknown_finished_process_counts=unknown,pending_permits=len(pending),
        reserved_single_use_permits=sum(k=='reserved' for k,_ in events),
        consumed_single_use_permits=sum(k=='consumed' for k,_ in events),
        usage_complete=False,unknown_usage_components=anchor['inherited_history']['unknown_usage_components'],cost=None)
    return events, summary, unsettled


def _permit(events, config, scenario, model):
    permit = events.get(('permit',config['permit_id']))
    _permit_shape(permit)
    if (not _int(permit['schema_version'],1,1) or permit['kind'] != 'codex_intake_single_use_permit' or
            any(permit[k] != config[k] for k in ('journal_id','permit_id','anchor_sha256','registration_sha256','store_root')) or
            permit['scenario_id'] != scenario or permit['requested_model'] != model or
            not _int(permit['maximum_model_processes'],1,1) or not _int(permit['automatic_retries'],0,0) or
            type(permit['timeout_seconds']) not in (int,float) or not 0<permit['timeout_seconds']<=60 or not math.isfinite(permit['timeout_seconds'])):
        _fail('permit_mismatch')
    _id(permit['worker_id'])
    if type(permit['producer_name']) is not str or not permit['producer_name'].strip() or len(permit['producer_name'])>200:
        _fail('invalid_policy')
    _expiry(permit['expires_at'])
    if any((kind,config['permit_id']) in events for kind in ('reserved','consumed','finished')):
        _fail('permit_used')
    return permit


def _append(con, kind, permit_id, body):
    data = _C(body)
    if len(data)>65536:
        _fail('input_limit')
    con.execute('INSERT INTO codex_intake_history(kind,permit_id,payload) VALUES(?,?,?)',(kind,permit_id,data.decode('utf-8')))


def _active_guard(path, data):
    # Durable crash/late-close guard, not a budget or a reusable authorization.
    stream=path.open('xb')
    try:
        if stream.write(data)!=len(data):raise OSError()
        stream.flush();os.fsync(stream.fileno())
    except BaseException:
        try:stream.close()
        except BaseException:pass
        raise
    else:stream.close()
    return _path(path,directory=False)[1]


def _dedicated(store, job_id):
    with store.connection() as con:
        rows = con.execute("SELECT job_id FROM intake_jobs WHERE state IN ('queued','running') ORDER BY job_id LIMIT 2").fetchall()
    if [row[0] for row in rows] != [job_id]:
        _fail('store_not_dedicated')


def _observation(once, evidence, entered):
    if not entered:
        return 0, None, True, None
    caller_pin=None
    try:
        caller=_read(evidence/'caller-receipt.json',65536)
        if caller==_C(once):caller_pin=dict(bytes=len(caller),sha256=_H(caller))
    except _CONTROL:raise
    except Exception:pass
    if type(once) is dict and once.get('attempts',{}).get('producer_invocations') == 0:
        return 0, None, caller_pin is not None, caller_pin
    if type(once) is not dict or type(once.get('binding')) is not dict:
        return None, None, False, caller_pin
    try:
        raw = _read(evidence/'exchange'/'receipt.json',65536)
        receipt = _json(raw);binding = once['binding']
        if (receipt['kind'] != 'codex_cli_response_receipt' or receipt['model']['requested'] != binding['requested_model'] or
                any(receipt['bindings'][key] != binding[key] for key in ('prompt_sha256','schema_sha256')) or
                receipt['attempts']['model_process_attempts'] != once['attempts']['model_process_attempts'] or
                type(receipt['lifecycle']['model_process_started']) is not bool):
            return None, None, False, caller_pin
        actual = int(receipt['lifecycle']['model_process_started'])
        if actual and not _int(receipt['attempts']['model_process_attempts'],1,1):
            return None, None, False, caller_pin
        cleanup = all(receipt['cleanup'][key] is True for key in
                      ('version_child_reaped','model_child_reaped','readers_joined','pipes_closed','artifacts_closed'))
        if binding.get('producer_receipt_sha256') is not None and _H(raw) != binding['producer_receipt_sha256']:
            return None, None, False, caller_pin
        return actual, dict(bytes=len(raw),sha256=_H(raw)), cleanup and caller_pin is not None, caller_pin
    except _CONTROL:
        raise
    except Exception:
        return None, None, False, caller_pin


def _run(scenario, model):
    record = dict(schema_version=1,kind='codex_registered_intake_host_receipt',status='not_run',phase='operator',
        scenario_id=scenario,requested_model=model,history=None,reservation=None,once=None,errors=[],
        verification=dict(operator_scope='not_validated',execution_scope='one_registered_synthetic_intake',measurement='not_assessed'))
    store = con = guard = control = first_error = None
    attempted = entered = consumed = False
    root = config = anchor = evidence = None
    active_path = active_info = active_bytes = None
    def error(exc, phase):
        nonlocal control, first_error
        if first_error is None:
            first_error = exc
        if isinstance(exc,_CONTROL) and control is None:
            control = exc
        code = str(exc) if type(exc) is _Failure else exc.code if isinstance(exc,StoreOpenError) else _PREFIX+(
            'journal_busy' if isinstance(exc,sqlite3.OperationalError) and 'locked' in str(exc) else 'interrupted' if isinstance(exc,_CONTROL) else 'internal_error')
        if len(record['errors'])<4:
            record['errors'].append(dict(phase=phase,code=code))
        record['status'] = 'unknown' if attempted or entered else 'not_run'
    try:
        root, _ = _path(_control_root(),directory=True)
        active_path=root/'active-run.json'
        try:active_path.lstat()
        except FileNotFoundError:pass
        else:_fail('history_unsettled')
        anchor_bytes = _read(root/_ANCHOR,65536);anchor = _json(anchor_bytes);_anchor(anchor,root)
        config_bytes = _read(root/'operator-control-v1.json',16384);config = _json(config_bytes)
        _keys(config, 'schema_version kind anchor_sha256 journal_id permit_id registration_sha256 registered_input_root store_root executable')
        if not _int(config['schema_version'],1,1) or config['kind'] != 'codex_registered_intake_operator_control' or config['anchor_sha256'] != _H(anchor_bytes):
            _fail('invalid_policy')
        for key in ('journal_id','permit_id'):
            _id(config[key])
        _hash(config['registration_sha256'])
        original,_ = _path(config['registered_input_root'],directory=True)
        store_root,_ = _path(config['store_root'],directory=True)
        executable,_ = _path(config['executable'],directory=False)
        if executable.name.lower() != 'codex.exe' or any(a==b or a.is_relative_to(b) or b.is_relative_to(a)
                for a,b in ((root,original),(root,store_root),(original,store_root))):
            _fail('invalid_path')
        evidence,_ = _path(root/'runs'/config['permit_id'],directory=True)
        if any(evidence.iterdir()):
            _fail('evidence_not_empty')
        record['phase']='registration'
        selection = _registration(root,config,scenario)
        record['phase']='history'
        journal, before = _path(root/'continuation.sqlite3',directory=False)
        if before.st_size>32*1024*1024:
            _fail('input_limit')
        guard=journal.open('rb')
        con=sqlite3.connect(journal.as_uri()+'?mode=rw',uri=True,timeout=0,isolation_level=None)
        con.execute('PRAGMA trusted_schema=OFF')
        _,after=_path(journal,directory=False)
        if (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino) or os.fstat(guard.fileno()).st_ino!=before.st_ino:
            _fail('source_changed')
        con.execute('BEGIN IMMEDIATE')
        events,record['history'],unsettled = _history(con,anchor,config,root)
        if unsettled:
            _fail('history_unsettled')
        permit = _permit(events,config,scenario,model)
        record['verification']['operator_scope']='native_operator_control'
        record['phase']='preclaim'
        store=Store.open_existing(str(store_root))
        _dedicated(store,selection['job_id'])
        context=prepare_registered_synthetic_context(store,selection,producer_name=permit['producer_name'])
        _dedicated(store,selection['job_id'])
        _registration(root,config,scenario)
        if _read(root/_ANCHOR,65536)!=anchor_bytes or _read(root/'operator-control-v1.json',16384)!=config_bytes:
            _fail('source_changed')
        _expiry(permit['expires_at'])
        prepared=preflight_codex_intake_once_inputs(context,producer_name=permit['producer_name'])
        _keys(prepared,'schema_version kind status context prompt response_schema pins failure execution_authority')
        if (not _int(prepared['schema_version'],1,1) or prepared['kind']!='codex_intake_once_preflight' or
                prepared['execution_authority'] is not False):
            _fail('invalid_policy')
        if prepared['status']!='validated':
            _fail('input_limit' if prepared['failure'] in ('analysis_context_limit','codex_intake_once_invalid_input') else 'unsupported_schema')
        if prepared['failure'] is not None:
            _fail('invalid_policy')
        prompt_bytes,schema_bytes=_C(prepared['prompt']),_C(prepared['response_schema'])
        if len(prompt_bytes)>262144 or len(schema_bytes)>65536:
            _fail('input_limit')
        _keys(prepared['pins'],'context_sha256 prompt_sha256 schema_sha256')
        if (_C(prepared['context'])!=_C(context) or prepared['pins']!=dict(
                context_sha256=_H(_C(context)),prompt_sha256=_H(prompt_bytes),schema_sha256=_H(schema_bytes))):
            _fail('source_changed')
        context=prepared['context']
        record['phase']='reserve'
        reserved=dict(permit_id=config['permit_id'],context_sha256=_H(_C(context)),registration_sha256=config['registration_sha256'],
            store_root=str(store_root),requested_model=model,reserved_model_attempts=1)
        record['history']=None
        attempted=True
        active_bytes=_C(reserved)
        active_info=_active_guard(active_path,active_bytes)
        _append(con,'reserved',config['permit_id'],reserved);con.commit()
        record['reservation']=dict(permit_id=config['permit_id'],state='reserved',context_sha256=reserved['context_sha256'],
                                    reservation_sha256=_H(_C(reserved)))
        record['phase']='consume'
        con.execute('BEGIN IMMEDIATE')
        events,_,unsettled=_history(con,anchor,config,root)
        if unsettled!={config['permit_id']} or events.get(('reserved',config['permit_id']))!=reserved or ('consumed',config['permit_id']) in events:
            _fail('history_unsettled')
        _expiry(permit['expires_at'])
        _append(con,'consumed',config['permit_id'],dict(permit_id=config['permit_id'],reservation_sha256=_H(_C(reserved))))
        con.commit();consumed=True;record['reservation']['state']='consumed'
        record['phase']='once';entered=True
        record['once']=run_codex_intake_once(store,context,worker_id=permit['worker_id'],producer_name=permit['producer_name'],
            executable=executable,requested_model=model,evidence_root=evidence,authorization_ref=config['permit_id'],
            timeout_seconds=permit['timeout_seconds'])
        record['status']='completed' if record['once']['status']=='completed' else 'unknown' if record['once']['status']=='unknown' else 'failed'
    except BaseException as exc:
        error(exc,record['phase'])
    finally:
        if store is not None:
            try:store.close()
            except BaseException as exc:error(exc,'store_close')
        if con is not None:
            transaction_settled=finish_mutation_attempted=finish_committed=False
            try:
                if con.in_transaction:con.rollback()
                transaction_settled=not con.in_transaction
                if attempted:
                    actual,receipt_pin,cleanup,caller_pin=_observation(record['once'],evidence,entered)
                    if not consumed or not cleanup or actual is None:
                        record['status']='unknown'
                    con.execute('BEGIN IMMEDIATE')
                    events,record['history'],_=_history(con,anchor,config,root)
                    if not consumed or ('consumed',config['permit_id']) not in events or ('finished',config['permit_id']) in events:
                        _fail('history_unsettled')
                    finished=dict(permit_id=config['permit_id'],status=record['status'],local_model_processes=actual,
                        cleanup_confirmed=cleanup,producer_receipt=receipt_pin,caller_receipt=caller_pin,once=record['once'],errors=record['errors'].copy())
                    record['history']=None
                    finish_mutation_attempted=True
                    _append(con,'finished',config['permit_id'],finished);con.commit()
                    finish_committed=True
                    _,record['history'],_=_history(con,anchor,config,root)
                    record['reservation']['state']='finished'
                    record['phase']='finished'
            except BaseException as exc:
                error(exc,'finish')
                if not transaction_settled:record['history']=None
                elif finish_mutation_attempted and not finish_committed and control is None:
                    try:
                        if con.in_transaction:con.rollback()
                        if not con.in_transaction:
                            _,record['history'],_=_history(con,anchor,config,root)
                    except BaseException as refresh_error:error(refresh_error,'history_refresh')
            finally:
                try:con.close()
                except BaseException as exc:error(exc,'journal_close')
        if guard is not None:
            try:guard.close()
            except BaseException as exc:error(exc,'journal_guard_close')
        if (active_info is not None and control is None and not record['errors'] and
                record['status'] in ('completed','failed') and record['reservation']['state']=='finished'):
            try:
                _,info=_path(active_path,directory=False)
                if (info.st_dev,info.st_ino)!=(active_info.st_dev,active_info.st_ino) or _read(active_path,65536)!=active_bytes:
                    _fail('source_changed')
                active_path.unlink()
            except BaseException as exc:
                error(exc,'active_guard_close')
                # If unlink completed before an observed control, restore a guard
                # without overwriting anything. Original journal evidence remains.
                try:_active_guard(active_path,active_bytes)
                except BaseException:pass
    if isinstance(first_error,_CONTROL):
        raise first_error
    return record


def main(argv=None) -> int:
    """Explicit native operator invocation; no authority/Store/provider injection."""
    args=sys.argv[1:] if argv is None else argv
    if type(args) in (list,tuple) and args==['--help']:
        try:sys.stdout.write(_HELP);sys.stdout.flush();return 0
        except _CONTROL:raise
        except Exception:return 5
    values={}
    if type(args) in (list,tuple) and len(args)==4 and all(type(v) is str for v in args):
        for option,value in zip(args[::2],args[1::2]):
            if option in ('--scenario-id','--model') and option not in values:values[option]=value
    try:
        if set(values)!={'--scenario-id','--model'} or values['--model'] not in _MODELS:
            raise ValueError()
        identifier(values['--scenario-id'])
    except ValueError:
        result=dict(schema_version=1,kind='codex_registered_intake_host_error',status='not_run',phase='arguments',code=_PREFIX+'invalid_arguments')
        status,stream=2,sys.stderr
    else:
        result=_run(values['--scenario-id'],values['--model'])
        status={'completed':0,'not_run':3,'failed':4,'unknown':5}[result['status']]
        stream=sys.stdout if status==0 else sys.stderr
    try:
        payload=canonical(result)+'\n'
        if len(payload.encode('utf-8'))>69632 or stream.write(payload)!=len(payload):return 5
        stream.flush()
    except _CONTROL:raise
    except Exception:return 5
    return status


def _process_main():
    """Own process streams only; avoid an interpreter retry after broken output."""
    control_status,status=None,5
    try:
        for stream in (sys.stdout,sys.stderr):
            stream.reconfigure(encoding='utf-8',errors='strict',newline='\n')
        status=main()
    except KeyboardInterrupt:
        control_status,status=130,130
    except (SystemExit,GeneratorExit,MemoryError):
        control_status,status=5,5
    except Exception:
        status=5
    for stream in (sys.stdout,sys.stderr):
        try:stream.flush()
        except _CONTROL as error:
            if control_status is None:control_status=130 if isinstance(error,KeyboardInterrupt) else 5
            os._exit(control_status)
        except Exception:
            os._exit(5 if control_status is None else control_status)
    return status


if __name__=='__main__':
    raise SystemExit(_process_main())
