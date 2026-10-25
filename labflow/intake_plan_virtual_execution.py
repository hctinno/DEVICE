"""Bind a revalidated synthetic intake plan to one public Codex virtual loop."""
import hashlib
import math
from pathlib import Path
import re

from .intake_conducted_twin_plan import build_conducted_twin_plan_input
from .store import canonical
from .virtual_fleet.codex_virtual_loop import (
    CodexVirtualLoopError, run_codex_virtual_loop as _run_loop)

__all__ = ['run_intake_plan_virtual_execution', 'IntakePlanVirtualExecutionError']

_PREFIX = 'intake_plan_virtual_execution_'
_CODES = {_PREFIX + x for x in ('invalid_input', 'invalid_plan', 'binding_mismatch',
    'non_synthetic', 'unsupported_method', 'plan_validation_failed', 'invalid_loop_result', 'execution_failed')}
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_BINDING = 'intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256'.split()
_PLAN = set('schema_version method_id method_version metric reference_plane source_settings basis_refs numeric_limit_dbm uncertainty_db assessment'.split())
_LOOP = set('schema_version kind run_id status failure declaration budget steps termination evidence_assessment execution cleanup artifacts verification'.split())


def _known_code(code):
    return type(code) is str and (code in _CODES or CodexVirtualLoopError(code).code == code)


class IntakePlanVirtualExecutionError(RuntimeError):
    """A fixed code and detached receipt; no native exception text is published."""
    def __init__(self, code, receipt=None):
        self.code = code if _known_code(code) else _PREFIX + 'invalid_input'
        self.receipt = receipt
        super().__init__(self.code)


class _Blocked(Exception):
    def __init__(self, code, stage):
        self.code, self.stage = _PREFIX + code, stage


def _block(code, stage='input'):
    raise _Blocked(code, stage)


def _C(value):
    return canonical(value).encode('utf-8')


def _H(value):
    return hashlib.sha256(_C(value)).hexdigest()


def _snapshot(value, *, limit=8388608, depth_limit=32, node_limit=100000):
    ancestors = set()
    nodes = 0
    def walk(item, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > depth_limit or nodes > node_limit:
            _block('invalid_input')
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        if type(item) not in (dict, list) or id(item) in ancestors:
            _block('invalid_input')
        ancestors.add(id(item))
        try:
            if type(item) is list:
                return [walk(child, depth + 1) for child in item]
            if any(type(key) is not str for key in item):
                _block('invalid_input')
            return {key: walk(child, depth + 1) for key, child in item.items()}
        finally:
            ancestors.remove(id(item))
    result = walk(value)
    if len(_C(result)) > limit:
        _block('invalid_input')
    return result


def _result(origin):
    return dict(schema_version=1, kind='intake_plan_virtual_execution_result', status='blocked', failure=None,
        binding={key: None for key in _BINDING + ['plan_input_sha256', 'run_id', 'runtime_instance_id']},
        plan_input=None, loop=None,
        execution=dict(mode='synthetic_only', loop_entered=False, trial_factory_calls=0,
            producer_calls_started=0,
            origin_declaration=origin if type(origin) is str and origin in ('mock_subprocess', 'actual_cli') else None,
            origin_authenticated=False, ai_model_called=None, intake_native_host_connected=False,
            hardware_verified=False),
        artifacts=dict(loop=None, outer_receipt_retained=False),
        verification=dict(original_plan_c1_verified=False, context_binding_verified=False,
            ready_plan_revalidated=False, source_bytes_reopened=False, current_store_revision_observed=False,
            execution_authority_verified=False, full_task_verified=False, setup_journal_connected=False,
            quantity_basis_verified=False))


def _receipt(value):
    return _snapshot(value, limit=16777216, depth_limit=64, node_limit=200000)


def _raise(code, result):
    receipt = _receipt(result)
    try:
        raise IntakePlanVirtualExecutionError(code, receipt) from None
    except IntakePlanVirtualExecutionError as error:
        error.__cause__ = error.__context__ = None
        raise


def _validate(context, analysis, plan_input, revision, context_sha, plan_sha, origin, result):
    context, analysis, supplied = _snapshot([context, analysis, plan_input])
    result['plan_input'] = supplied
    if (type(revision) is not int or revision < 1 or type(context_sha) is not str
            or not _SHA.fullmatch(context_sha) or type(plan_sha) is not str or not _SHA.fullmatch(plan_sha)
            or type(origin) is not str or origin not in {'mock_subprocess', 'actual_cli'}):
        _block('invalid_input')
    if type(supplied) is not dict:
        _block('invalid_plan')
    result['binding']['plan_input_sha256'] = _H(supplied)
    if result['binding']['plan_input_sha256'] != plan_sha:
        _block('binding_mismatch', 'binding')
    result['verification']['original_plan_c1_verified'] = True
    if (set(supplied) != set('schema_version kind status binding intake plan gaps verification'.split())
            or type(supplied['schema_version']) is not int or supplied['schema_version'] != 1
            or supplied['kind'] != 'intake_conducted_twin_plan_input'
            or type(supplied['binding']) is not dict or set(supplied['binding']) != set(_BINDING)):
        _block('invalid_plan')
    binding = supplied['binding']
    result['binding'].update(binding)
    if supplied['status'] == 'blocked':
        return None
    if supplied['status'] != 'ready_for_simulation':
        _block('invalid_plan')
    if type(context) is not dict or type(analysis) is not dict:
        _block('invalid_input')
    if context.get('synthetic') is not True:
        _block('non_synthetic', 'binding')
    plan = supplied['plan']
    if type(plan) is not dict or set(plan) != _PLAN:
        _block('invalid_plan')
    if (type(context.get('revision')) is not int or type(binding['revision']) is not int
            or context['revision'] != revision or binding['revision'] != revision
            or _H(context) != context_sha or binding['context_sha256'] != context_sha
            or binding['analysis_sha256'] != _H(analysis) or binding['plan_sha256'] != _H(plan)
            or any(type(binding[key]) is not str or binding[key] != context.get(key)
                   for key in ('intake_id', 'analysis_context_id'))):
        _block('binding_mismatch', 'binding')
    result['verification']['context_binding_verified'] = True
    method = {key: plan[key] for key in ('method_id', 'method_version', 'metric', 'reference_plane')}
    if (method['method_id'] != 'conducted_synthetic' or type(method['method_version']) is not int
            or method['method_version'] != 1 or method['metric'] not in ('on', 'time', 'peak')
            or method['reference_plane'] != 'source_output'):
        _block('unsupported_method', 'plan')
    rebuilt = build_conducted_twin_plan_input(context, analysis,
        expected_revision=revision, expected_context_sha256=context_sha,
        source_settings=plan['source_settings'], basis=plan['basis_refs'], method=method)
    if rebuilt['status'] != 'ready_for_simulation' or _C(rebuilt) != _C(supplied):
        _block('plan_validation_failed', 'plan')
    result['verification']['ready_plan_revalidated'] = True
    return plan['source_settings']


def _attach(result, value):
    captured = _snapshot(value, limit=262144, depth_limit=64)
    if (type(captured) is not dict or set(captured) != _LOOP
            or type(captured['schema_version']) is not int or captured['schema_version'] != 1
            or captured['kind'] != 'codex_virtual_loop_result'
            or captured['status'] not in ('stopped', 'bounded', 'failed')
            or type(captured['execution']) is not dict or type(captured['budget']) is not dict
            or type(captured['run_id']) is not str
            or type(captured['artifacts']) is not dict
            or 'runtime_instance_id' not in captured['execution']):
        _block('invalid_loop_result', 'capture')
    if captured['status'] == 'failed':
        failure = captured['failure']
        if (type(failure) is not dict or set(failure) != {'code', 'stage'}
                or not _known_code(failure['code']) or type(failure['stage']) is not str):
            _block('invalid_loop_result', 'capture')
    elif captured['failure'] is not None:
        _block('invalid_loop_result', 'capture')
    result['loop'] = captured
    result['artifacts']['loop'] = _snapshot(captured['artifacts'])
    result['binding']['run_id'] = captured['run_id']
    runtime_id = captured['execution']['runtime_instance_id']
    result['binding']['runtime_instance_id'] = runtime_id
    result['execution']['trial_factory_calls'] = 1 if type(runtime_id) is str and runtime_id else None
    count = captured['budget'].get('producer_calls_started')
    result['execution']['producer_calls_started'] = count if type(count) is int and 0 <= count <= 8 else None
    result['status'] = captured['status']
    result['failure'] = captured['failure']


def run_intake_plan_virtual_execution(context, analysis, plan_input, *, expected_revision,
        expected_context_sha256, expected_plan_input_sha256, catalog_path: Path, catalog_sha256: str,
        response_schema_bytes: bytes, executable: Path, requested_model: str, scenario: str,
        evidence_dir: Path, execution_origin: str, cancel_event=None) -> dict:
    """Revalidate caller snapshots then enter one delegated synthetic loop; never grant authority."""
    result = _result(execution_origin)
    try:
        source = _validate(context, analysis, plan_input, expected_revision, expected_context_sha256,
                           expected_plan_input_sha256, execution_origin, result)
    except _CONTROL:
        raise
    except _Blocked as error:
        result['failure'] = dict(code=error.code, stage=error.stage)
        return _receipt(result)
    except Exception:
        result['failure'] = dict(code=_PREFIX+'invalid_input', stage='input')
        return _receipt(result)
    if source is None:
        return _receipt(result)
    result['execution'].update(loop_entered=True, trial_factory_calls=None, producer_calls_started=None)
    try:
        original = _run_loop(catalog_path=catalog_path, catalog_sha256=catalog_sha256,
            response_schema_bytes=response_schema_bytes, executable=executable, requested_model=requested_model,
            scenario=scenario, evidence_dir=evidence_dir, execution_origin=execution_origin,
            cancel_event=cancel_event, source_settings=source)
    except _CONTROL:
        raise
    except CodexVirtualLoopError as error:
        if error.receipt is not None:
            try:
                _attach(result, error.receipt)
            except _CONTROL:
                raise
            except Exception:
                pass  # An unavailable partial receipt cannot replace the parent's first error.
        result['status'] = 'failed'
        if result['failure'] is None:
            result['failure'] = dict(code=error.code, stage='execute')
        _raise(error.code, result)
    except Exception:
        result['status'] = 'failed'
        result['failure'] = dict(code=_PREFIX+'execution_failed', stage='execute')
        _raise(result['failure']['code'], result)
    try:
        _attach(result, original)
    except _CONTROL:
        raise
    except Exception:
        result['status'] = 'failed'
        result['failure'] = dict(code=_PREFIX+'invalid_loop_result', stage='capture')
        _raise(result['failure']['code'], result)
    if result['status'] == 'failed':
        _raise(result['failure']['code'], result)
    return _receipt(result)
