"""Small, immutable public projection of one caller supplied virtual operator attempt.

The constructor accepts trusted in-memory receipts. It never locates files, starts a
model, grants execution authority, or publishes the receipts themselves.
"""
import hashlib
import json
import re

from .store import canonical

_SHA = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,149}\Z', re.ASCII)
_MODEL = re.compile(r'[a-z0-9][a-z0-9.-]{0,63}\Z', re.ASCII)
_PINS = {'evaluation', 'execution', 'finalizer', 'finished', 'handoff'}
_BINDING = {'intake_id', 'revision', 'analysis_context_id', 'context_sha256',
            'analysis_sha256', 'plan_sha256', 'plan_input_sha256', 'run_id',
            'runtime_instance_id'}
_PLAN_BINDING = _BINDING - {'plan_input_sha256', 'run_id', 'runtime_instance_id'}


class OperatorAttemptViewError(ValueError):
    pass


def _need(condition):
    if not condition:
        raise OperatorAttemptViewError('operator_attempt_invalid')


def _sha(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _same(left, right):
    return canonical(left) == canonical(right)


def _digest(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def _binding(value):
    _need(type(value) is dict and set(value) == _BINDING)
    _need(type(value['intake_id']) is str and _ID.fullmatch(value['intake_id']) is not None)
    _need(type(value['revision']) is int and 1 <= value['revision'] <= 2**53 - 1)
    _need(all(_digest(value[k]) for k in ('analysis_context_id', 'context_sha256',
                                        'analysis_sha256', 'plan_sha256', 'plan_input_sha256')))
    _need(all(type(value[k]) is str and _ID.fullmatch(value[k]) for k in ('run_id', 'runtime_instance_id')))


def _source(record, kind):
    _need(type(record) is dict and record.get('kind') == kind)


def prepare_operator_attempt(provided):
    """Return only validated, detached UTF-8 JSON bytes for one held attempt."""
    try:
        _need(type(provided) is dict and set(provided) == _PINS | {'source_pins'})
        e, x, f, z, h = (provided[k] for k in ('evaluation', 'execution', 'finalizer', 'finished', 'handoff'))
        pins = provided['source_pins']
        _need(type(pins) is dict and set(pins) == _PINS and all(_digest(v) for v in pins.values()))
        _source(e, 'actual_ai_01_continuation_independent_evaluation')
        _source(x, 'intake_plan_virtual_execution_result')
        _source(f, 'conducted_execution_result_finalizer')
        _source(z, 'same_case_manual_continuation_finished')
        _source(h, 'codex_conducted_workflow_current_handoff')
        b = e['binding']['execution']; _binding(b)
        _need(_same(x['binding'], b) and x['loop']['run_id'] == b['run_id']
              and x['loop']['status'] == x['status'])
        _need(_same(f['execution_receipt'], x) and f['status'] == 'held' and f['result'] is None
              and f['artifact'] is None and f['measurement_selection']['status'] == 'blocked')
        _need(z['status'] == 'failed' and z['execution_receipt']['sha256'] == pins['execution']
              and z['finalizer_receipt']['sha256'] == pins['finalizer'])
        _need(h['execution_receipt']['sha256'] == pins['execution']
              and h['finalizer_receipt']['sha256'] == pins['finalizer'])
        current = h['current_facts_plan']; context = current['context']; analysis = current['analysis']
        plan_input = current['facts_plan']['plan_input']; plan_binding = plan_input['binding']
        method = {key: plan_input['plan'][key] for key in
                  ('method_id', 'method_version', 'metric', 'reference_plane')}
        _need(current['facts_plan']['status'] == 'ready_for_simulation'
              and _same(x['plan_input'], plan_input)
              and type(plan_binding) is dict and set(plan_binding) == _PLAN_BINDING
              and _same(plan_binding, {k: b[k] for k in _PLAN_BINDING})
              and method['method_id'] == 'conducted_synthetic'
              and type(method['method_version']) is int and method['method_version'] == 1
              and method['metric'] in ('on', 'time', 'peak')
              and method['reference_plane'] == 'source_output'
              and context['intake_id'] == b['intake_id']
              and _integer(context['revision'], b['revision'], b['revision'])
              and context['analysis_context_id'] == b['analysis_context_id']
              and type(context['job_id']) is str and _ID.fullmatch(context['job_id']) is not None
              and _sha(context) == b['context_sha256'] and _sha(analysis) == b['analysis_sha256']
              and _sha(plan_input['plan']) == b['plan_sha256']
              and _sha(plan_input) == b['plan_input_sha256'])
        _need(e['root_observation']['execution_status'] == 'bounded'
              and e['root_observation']['finalization_status'] == 'held'
              and e['root_observation']['finished_status'] == 'failed'
              and e['root_observation']['hardware_verified'] is False
              and e['root_observation']['origin_authenticated'] is False
              and e['root_observation']['remote_model_identity_verified'] is False)
        _need(x['status'] == 'bounded' and x['execution']['mode'] == 'synthetic_only'
              and x['execution']['origin_declaration'] == 'actual_cli'
              and x['execution']['origin_authenticated'] is False
              and x['execution']['hardware_verified'] is False
              and x['loop']['termination']['reason'] == 'decision_budget'
              and e['journal']['run_id'] == b['run_id']
              and e['journal']['runtime_instance_id'] == b['runtime_instance_id']
              and e['journal']['terminal_reason'] == 'decision_budget'
              and _integer(e['journal']['explicit_stop_decision_count'], 0, 0)
              and e['journal']['final_virtual_dut_state'] == 'transmitting')
        reasons = f['measurement_selection']['reasons']
        _need(type(reasons) is list and len(reasons) == 1
              and type(reasons[0]) is dict and set(reasons[0]) == {'code', 'field', 'detail'}
              and reasons[0] == dict(code='execution_incomplete', field='journal/report', detail=None))
        _need(f['failure'] == dict(code='conducted_execution_result_finalizer_measurement_selection_blocked',
                                  stage='selection')
              and e['finalization']['status'] == 'held' and e['finalization']['result'] is None
              and e['finalization']['artifact'] is None
              and _integer(e['finalization']['measurement_builder_calls'], 0, 0)
              and e['finalization']['persistent_DRAFT_evidence'] is False
              and e['finalization']['failure'] == f['failure']
              and e['finalization']['measurement_selection_status'] == f['measurement_selection']['status']
              and e['finalization']['measurement_selection_reasons'] == reasons)
        calls = e['model_calls']; steps = x['loop']['steps']
        count = z['local_model_processes']
        _need(_integer(count, 1, 8) and len(calls) == len(steps) == count
              and _integer(x['execution']['producer_calls_started'], count, count))
        loop_budget = x['loop']['budget']
        _need(all(_integer(loop_budget[key], count, count) for key in
                  ('producer_calls_started', 'model_process_attempts',
                   'version_process_attempts', 'reserved_model_calls'))
              and _integer(loop_budget['harness_usage']['decisions'], count, count)
              and _integer(loop_budget['limits']['model_calls'], count, count))
        requested = calls[0]['requested_model']
        _need(type(requested) is str and _MODEL.fullmatch(requested) is not None)
        public_steps = []
        for index, (call, step) in enumerate(zip(calls, steps), 1):
            proposal = call['proposal']; wire = step['wire']['proposal']
            _need(type(proposal) is dict and type(wire) is dict and proposal == wire
                  and _integer(call['index'], index, index) and _integer(step['index'], index, index)
                  and step['binding']['run_id'] == b['run_id']
                  and step['binding']['runtime_instance_id'] == b['runtime_instance_id']
                  and call['requested_model'] == requested and call['remote_resolved_model'] is None
                  and _integer(call['cli_tool_items'], 0, 0)
                  and _integer(call['confirmed_dispatch_receipts'], 1, 1)
                  and _integer(step['dispatch']['confirmed_receipts'], 1, 1)
                  and call['receipt_status'] == step['dispatch']['receipt_status']
                  and call['receipt_status'] in ('ok', 'pending')
                  and step['dispatch']['effect'] in ('changed', 'unchanged'))
            receipt = step['producer']['receipt']
            _need(receipt['status'] == call['producer_status'] == 'complete'
                  and _integer(receipt['lifecycle']['tool_items'], 0, 0)
                  and _integer(receipt['lifecycle']['agent_messages'], 1, 1)
                  and _integer(call['agent_messages'], 1, 1)
                  and _integer(receipt['lifecycle']['exit_code'], 0, 0)
                  and _integer(call['cli_exit_code'], 0, 0)
                  and _integer(receipt['attempts']['model_process_attempts'], 1, 1)
                  and _integer(receipt['attempts']['version_process_attempts'], 1, 1)
                  and receipt['model']['requested'] == requested
                  and receipt['model']['resolved'] is None)
            if proposal.get('kind') == 'advance':
                _need(set(proposal) == {'kind', 'ticks'}
                      and _integer(proposal['ticks'], 1, 8) and _integer(wire['ticks'], 1, 8))
                action = 'advance'
            else:
                _need(set(proposal) == {'kind', 'device_id', 'action', 'parameters'}
                      and proposal['kind'] == 'execute' and proposal['parameters'] == {}
                      and (proposal['device_id'], proposal['action']) in
                          {('dut', 'start'), ('sensor', 'acquire'), ('sensor', 'read')})
                action = proposal['device_id'] + '.' + proposal['action']
            before = step.get('before', {}); after = step.get('after', {})
            _need(type(before) is dict and type(after) is dict
                  and type(call['before_tick']) is int and type(call['after_tick']) is int
                  and 0 <= call['before_tick'] <= call['after_tick'] <= 100000
                  and _integer(before.get('tick', call['before_tick']), call['before_tick'], call['before_tick'])
                  and _integer(after.get('tick', call['after_tick']), call['after_tick'], call['after_tick']))
            public_steps.append(dict(index=index, action=action, before_tick=call['before_tick'],
                                     after_tick=call['after_tick'], receipt_status=call['receipt_status'],
                                     effect=step['dispatch']['effect'], cli_tool_items=0))
        budget = e['budget_and_usage']
        _need(_integer(budget['cumulative_model_processes'], count, 2**53 - 1)
              and _integer(budget['maximum_cumulative_model_processes'], count, 2**53 - 1)
              and _integer(budget['remaining_model_processes'], 0, 0)
              and budget['cumulative_model_processes'] == budget['maximum_cumulative_model_processes']
              and budget['cost'] is None)
        output = dict(schema_version=1, kind='operator_attempt_view', status=x['status'],
                      finalization=f['status'], storage='not_created',
                      termination_reason=x['loop']['termination']['reason'],
                      hold_reason=reasons[0]['code'], hold_reasons=[reasons[0].copy()],
                      virtual_dut_final_state=e['journal']['final_virtual_dut_state'],
                      source_kind='provided_actual_cli_record', declared_mode='synthetic_only',
                      binding={**b, 'job_id': context['job_id']},
                      method=method,
                      model=dict(requested_model=requested, remote_resolved_model=None,
                                 process_count=count, cli_tool_items=0, cumulative_processes=budget['cumulative_model_processes'],
                                 remaining_processes=0, token_usage=None, cost=None),
                      steps=public_steps,
                      verification=dict(origin_authenticated=False, remote_identity_verified=False,
                                        hardware_verified=False, execution_authority=False,
                                        result_created=False, draft_created=False),
                      evidence={key: pins[key] for key in sorted(_PINS)})
        raw = json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        _need(len(raw) <= 16384)
        return raw
    except (OperatorAttemptViewError, KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise OperatorAttemptViewError('operator_attempt_invalid') from None


def check_current_binding(prepared, observed):
    """Reject every changed current read; never substitute retained success."""
    try:
        _need(type(prepared) is dict and prepared.get('kind') == 'operator_attempt_view')
        _need(type(observed) is dict and observed['status'] == 'available'
              and observed['recheck']['status'] == 'unchanged')
        value = observed['current']; context = value['context']; analysis = value['analysis']
        facts = value['facts_plan']; plan_input = facts['plan_input']; b = prepared['binding']
        _need(facts['status'] == 'ready_for_simulation'
              and context['intake_id'] == b['intake_id'] and context['job_id'] == b['job_id']
              and _integer(context['revision'], b['revision'], b['revision'])
              and context['analysis_context_id'] == b['analysis_context_id']
              and _sha(context) == b['context_sha256'] and _sha(analysis) == b['analysis_sha256']
              and _sha(plan_input['plan']) == b['plan_sha256']
              and _sha(plan_input) == b['plan_input_sha256']
              and type(plan_input['binding']) is dict and set(plan_input['binding']) == _PLAN_BINDING
              and _same(plan_input['binding'], {k: b[k] for k in _PLAN_BINDING}))
        return None
    except (OperatorAttemptViewError, KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise OperatorAttemptViewError('operator_attempt_binding_mismatch') from None
