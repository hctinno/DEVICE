"""Finalize pinned, already executed synthetic evidence without rerunning it."""
import hashlib
import json
import math
from pathlib import Path
import re

from . import control_packet_prepare as _native
from .intake_plan_virtual_execution import IntakePlanVirtualExecutionError
from .store import canonical
from .virtual_fleet.journal import read_operator_journal as _read_journal
from .virtual_fleet.conducted_twin_result import build_conducted_twin_result as _build_result
from .virtual_fleet.conducted_result_artifact import (
    ConductedResultArtifactError, write_conducted_result_artifact as _write_result)

__all__ = ['finalize_conducted_execution_result', 'ConductedExecutionResultFinalizerError']

_PREFIX = 'conducted_execution_result_finalizer_'
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_BINDING = set('intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256'.split())
_TOP = set('schema_version kind status failure binding plan_input loop execution artifacts verification'.split())
_LOOP = set('schema_version kind run_id status failure declaration budget steps termination evidence_assessment execution cleanup artifacts verification'.split())
_FILES = {
    'request': ('caller-request.json', 262144),
    'setup_snapshot': ('setup-snapshot.json', 1048576),
    'operator_journal': ('operator-journal.jsonl', 9437184),
    'legacy_report': ('legacy-harness-report.json', 262144),
    'legacy_events': ('legacy-harness-events.json', 8388608),
}


class ConductedExecutionResultFinalizerError(RuntimeError):
    """Fixed failure and detached preservation receipt; no exception text."""
    def __init__(self, code, stage, receipt):
        self.code, self.stage, self.receipt = code, stage, receipt
        super().__init__(code)


class _Reject(Exception):
    def __init__(self, suffix):
        self.code = _PREFIX + suffix


def _reject(suffix):
    raise _Reject(suffix)


def _C(value):
    return canonical(value).encode('utf-8')


def _H(raw):
    return hashlib.sha256(raw).hexdigest()


def _snapshot(value, limit=262144):
    ancestors = set()
    nodes = used = 0
    def walk(item, depth=0):
        nonlocal nodes, used
        nodes += 1
        if depth > 32 or nodes > 1000000:
            _reject('input_invalid')
        kind = type(item)
        if item is None or kind in (bool,int):
            used += len(str(item))
            result = item
        elif kind is float and math.isfinite(item):
            used += 24
            result = item
        elif kind is str:
            used += len(item.encode('utf-8')) + 2
            result = item
        elif kind in (dict,list) and id(item) not in ancestors:
            ancestors.add(id(item))
            try:
                if kind is list:
                    result = [walk(child,depth+1) for child in item]
                else:
                    result = {}
                    for key,child in item.items():
                        if type(key) is not str:
                            _reject('input_invalid')
                        walk(key,depth+1)
                        result[key] = walk(child,depth+1)
            finally:
                ancestors.remove(id(item))
        else:
            _reject('input_invalid')
        if used > limit:
            _reject('input_invalid')
        return result
    try:
        result = walk(value)
        if len(_C(result)) > limit:
            _reject('input_invalid')
        return result
    except (ValueError,UnicodeError,OverflowError,RecursionError):
        _reject('input_invalid')


def _note(receipt, item):
    if receipt['failure'] is None:
        receipt['failure'] = item
    else:
        receipt['secondary_errors'].append(item)


def _same(left, right):
    if _C(left) != _C(right):
        _reject('binding_mismatch')


def _adapter(value, expected_sha, receipt):
    value = _snapshot(value)
    receipt['execution_receipt'] = value
    if type(expected_sha) is not str or not _SHA.fullmatch(expected_sha):
        _reject('input_invalid')
    if _H(_C(value)) != expected_sha:
        _reject('execution_hash_mismatch')
    if (type(value) is not dict or set(value) != _TOP or type(value['schema_version']) is not int
            or value['schema_version'] != 1 or value['kind'] != 'intake_plan_virtual_execution_result'):
        _reject('input_invalid')
    if value['failure'] is not None:
        failure = value['failure']
        if (type(failure) is not dict or set(failure) != {'code','stage'}
                or type(failure['code']) is not str or type(failure['stage']) is not str
                or IntakePlanVirtualExecutionError(failure['code']).code != failure['code']):
            _reject('input_invalid')
        _note(receipt, failure)
    plan, loop, binding = value['plan_input'], value['loop'], value['binding']
    if type(plan) is not dict or type(loop) is not dict or type(binding) is not dict:
        _reject('unbound_execution')
    if (set(loop) != _LOOP or type(loop['schema_version']) is not int or loop['schema_version'] != 1
            or loop['kind'] != 'codex_virtual_loop_result' or loop['status'] not in ('stopped','bounded','failed')
            or type(loop['execution']) is not dict or loop['execution'].get('synthetic') is not True
            or type(value['execution']) is not dict or value['execution'].get('mode') != 'synthetic_only'):
        _reject('unbound_execution')
    if (type(plan.get('binding')) is not dict or set(plan['binding']) != _BINDING
            or set(binding) != _BINDING | {'plan_input_sha256','run_id','runtime_instance_id'}
            or type(loop.get('execution')) is not dict or type(loop.get('artifacts')) is not dict):
        _reject('binding_mismatch')
    _same({key:binding[key] for key in _BINDING},plan['binding'])
    _same(binding['plan_input_sha256'],_H(_C(plan)))
    _same(value['artifacts']['loop'],loop['artifacts'])
    _same(value['status'],loop['status'])
    _same(value['failure'],loop['failure'])
    run, runtime = loop['run_id'], loop['execution']['runtime_instance_id']
    _same((binding['run_id'],binding['runtime_instance_id']),(run,runtime))
    if (type(run) is not str or not run or len(run)>200
            or type(runtime) is not str or not runtime or len(runtime)>200):
        _reject('unbound_execution')
    return plan, loop, run, runtime


def _json(raw):
    def pairs(rows):
        result = {}
        for key,value in rows:
            if key in result:
                _reject('evidence_json_invalid')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: _reject('evidence_json_invalid'))
        return _snapshot(value,limit=33554432)
    except (ValueError,UnicodeError,RecursionError):
        _reject('evidence_json_invalid')


def _read_inputs(evidence_dir, artifacts, receipt):
    if type(evidence_dir) not in (str,Path):
        # Concrete platform Path types are native too; arbitrary __fspath__ hooks are not.
        if type(evidence_dir) is not type(Path()):
            _reject('input_invalid')
    backend = None
    error = None
    result = None
    try:
        try:
            backend = _native._WindowsIO()
        except NotImplementedError:
            _reject('unsupported_platform')
        root = _native._local_path(evidence_dir)
        tree = _native._Tree(root,backend)
        values, stamps = {}, {}
        total = 0
        for key,(leaf,limit) in _FILES.items():
            meta = artifacts.get(key)
            if (type(meta) is not dict or set(meta) != {'path','present','bytes','sha256','complete','overflow','extent'}
                    or meta['path'] != leaf or type(meta['present']) is not bool
                    or type(meta['complete']) is not bool or type(meta['overflow']) is not bool):
                _reject('artifact_descriptor_invalid')
            if not meta['present']:
                _reject('evidence_missing')
            if (type(meta['bytes']) is not int or not 0<=meta['bytes']<=limit
                    or type(meta['sha256']) is not str or not _SHA.fullmatch(meta['sha256'])
                    or meta['overflow'] or meta['extent'] != ('whole_file' if meta['complete'] else 'prefix')):
                _reject('artifact_descriptor_invalid')
            if not meta['complete'] and key != 'operator_journal':
                _reject('artifact_incomplete')
            path = root/leaf
            info = tree.file_stat(path)
            if info.st_size != meta['bytes']:
                _reject('artifact_hash_mismatch')
            descriptor = backend.open_read(path,pin=True)
            stamp = _native._stamp(info)
            if _native._stamp(backend.info(descriptor,directory=False)) != stamp:
                _reject('evidence_changed')
            raw = _native._read_descriptor(descriptor,limit,'packet_prepare_verification_failed')
            total += len(raw)
            if total > 33554432:
                _reject('input_invalid')
            if len(raw) != meta['bytes'] or _H(raw) != meta['sha256']:
                _reject('artifact_hash_mismatch')
            stamps[path] = (descriptor,stamp)
            receipt['input_files'][key] = dict(path=leaf,bytes=len(raw),sha256=_H(raw),complete=meta['complete'])
            values[key] = raw if key=='operator_journal' else _json(raw)
        journal = _read_journal(root/_FILES['operator_journal'][0])
        _same(journal['integrity']['file_sha256'],_H(values['operator_journal']))
        for path,(descriptor,stamp) in stamps.items():
            if (_native._stamp(backend.info(descriptor,directory=False)) != stamp
                    or _native._stamp(tree.file_stat(path)) != stamp):
                _reject('evidence_changed')
        for path,identity in tree.directories.items():
            if _native._identity(backend.info(backend.directory(path),directory=True)) != identity:
                _reject('evidence_changed')
        result = values,journal
    except BaseException as observed:
        error = observed
    finally:
        if backend is not None:
            try:
                backend.close()
            except BaseException as close_error:
                if error is None or isinstance(close_error,_CONTROL) and not isinstance(error,_CONTROL):
                    error = close_error if isinstance(close_error,_CONTROL) else _Reject('evidence_close_failed')
                else:
                    receipt['secondary_errors'].append(dict(code=_PREFIX+'evidence_close_failed',stage='read'))
    if error is not None:
        raise error
    return result


def _bind(plan, loop, run, runtime, values, journal):
    request, report = values['request'],values['legacy_report']
    host = loop['execution']['host_evidence']
    header = journal['header']; provenance = header['provenance']
    for obj in (request,report,header):
        _same(obj['run_id'],run)
    _same((report['runtime_instance_id'],header['runtime_instance_id']),(runtime,runtime))
    _same(request['declaration'],loop['declaration'])
    _same(request['limits'],loop['budget']['limits'])
    _same(request['execution']['plan_binding'],plan['binding'])
    _same(request['execution']['source_settings'],plan['plan']['source_settings'])
    _same(host['plan_binding'],plan['binding'])
    _same(provenance['plan_binding'],plan['binding'])
    _same((host['setup_sha256'],provenance['setup_sha256']),(_H(_C(values['setup_snapshot'])),)*2)
    _same((host['topology_sha256'],provenance['topology_sha256']),(_H(_C(provenance['topology'])),)*2)
    _same(provenance['catalog_sha256'],loop['declaration']['catalog_sha256'])
    _same(provenance['source_pins'],request['source_pins'])
    _same(provenance['engine_sha256'],_H(_C(request['source_pins'])))
    _same(provenance['engine_fingerprint_kind'],'sha256_canonical_host_source_pins_v1')
    _same((host['recording_mode'],provenance['recording_mode']),('post_run_from_retained_events',)*2)
    quantity = request['execution'].get('quantity')
    _same(host['quantity'],quantity)
    if quantity is None:
        if 'quantity' in provenance:
            _reject('binding_mismatch')
    else:
        _same(provenance['quantity'],quantity)
    _same(host['journal_file_sha256'],journal['integrity']['file_sha256'])
    _same(host['journal_head_sha256'],journal['integrity']['head_sha256'])
    _same(host['journal_complete'],journal['complete'])
    _same(values['legacy_events'],journal['events'])


def finalize_conducted_execution_result(execution_receipt, *, expected_execution_sha256,
        evidence_dir, measurement_ref=None, workspace_root, artifact_name):
    """Pin fixed same-run evidence, call genuine builder, and store its unchanged DTO."""
    receipt = dict(schema_version=1,kind='conducted_execution_result_finalizer',status='held',
        execution_receipt=None,input_files={},result=None,artifact=None,failure=None,secondary_errors=[],
        verification=dict(evidence_snapshot_verified=False,recording_mode=None,origin_authenticated=False,
            ai_model_called=None,execution_rerun=False,source_bytes_reopened=False,hardware_verified=False,
            physical_verified=False,full_task_verified=False,method_approval='not_assessed'),execution_authority=False)
    stage = 'input'
    try:
        plan,loop,run,runtime = _adapter(execution_receipt,expected_execution_sha256,receipt)
        if measurement_ref is not None and (type(measurement_ref) is not str or len(measurement_ref)>200):
            _reject('input_invalid')
        stage = 'read'
        values,journal = _read_inputs(evidence_dir,loop['artifacts'],receipt)
        stage = 'binding'
        _bind(plan,loop,run,runtime,values,journal)
        receipt['verification'].update(evidence_snapshot_verified=True,recording_mode='post_run_from_retained_events')
        stage = 'builder'
        result = _build_result(plan,values['setup_snapshot'],journal,values['legacy_report'],measurement_ref=measurement_ref)
        receipt['result'] = result
        if result['failure'] is not None:
            _note(receipt,result['failure'])
        stage = 'writer'
        receipt['artifact'] = _write_result(result,workspace_root=workspace_root,artifact_name=artifact_name,
            expected_result_sha256=_H(_C(result)),run_id=run,runtime_instance_id=runtime)
        receipt['status'] = 'stored'
        return receipt
    except _CONTROL:
        raise
    except Exception as error:
        if isinstance(error,ConductedResultArtifactError):
            item = dict(code=error.code,stage=stage,phase=error.phase,publication_attempted=error.publication_attempted)
            code = _PREFIX+'storage_failed'
        else:
            code = error.code if isinstance(error,_Reject) else _PREFIX+{
                'input':'input_invalid','read':'evidence_read_failed','binding':'binding_mismatch',
                'builder':'builder_failed','writer':'storage_failed'}[stage]
            item = dict(code=code,stage=stage)
        _note(receipt,item)
        raise ConductedExecutionResultFinalizerError(code,stage,receipt) from None
