"""Assess supplied one-action evidence in memory; never grade the sensor task."""
import hashlib
import json
import math
import re

from .model_operator_boundary import ModelOperatorBoundaryError, decode_operator_response

__all__ = ['assess_codex_one_action_effects', 'CodexOneActionAssessmentError']

_PREFIX = 'codex_one_action_assessment_'
_ERRORS = {'invalid_input', 'limit_exceeded', 'internal_error'}
_CONTROL = (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)
_PACKET = 'host_result context8 prompt response_bytes harness_report harness_events before after dispatch_receipt'.split()
_CHECKS = 'input_binding wire_scope same_run_evidence single_action effect_receipt error_and_cleanup'.split()
_VERIFY = 'input_values_unchanged supplied_graph_consistent root_authority_verified runtime_authenticity_verified storage_integrity_verified actual_wall_time_verified model_quality_verified hardware_verified physical_cleanup_verified task_goal_verified'.split()
_REASONS = 'unsupported_protocol task_evaluator_inapplicable evidence_missing execution_unresolved caller_refusal_only binding_mismatch wire_scope_mismatch wire_evidence_missing receipt_observation_mismatch host_summary_mismatch single_action_violation reported_budget_violation first_error_mismatch cleanup_unverified effect_observed command_rejected_observed command_pending_observed stop_not_completion host_error_before_dispatch supplied_provenance_only'.split()
_HOST_CODES = 'invalid_input delegation_denied unsupported_source capture_failed budget_exhausted cancelled timeout retention_failed runtime_rejected runtime_uncertain cleanup_failed internal_error'.split()
_CLI_CODES = 'invalid_input limit_exceeded unsupported_client evidence_error spawn_failed timeout stream_invalid process_failed final_mismatch cleanup_failed internal_error'.split()
_BOUNDARY_CODES = 'invalid_input invalid_prompt response_invalid response_binding_mismatch response_producer_mismatch proposal_invalid limit_exceeded internal_error'.split()
_CALLER_CODES = ({'operator_virtual_one_action_' + x for x in _HOST_CODES}
                 | {'codex_cli_response_' + x for x in _CLI_CODES}
                 | {'model_operator_boundary_' + x for x in _BOUNDARY_CODES})
_LIMITS = dict(max_input_bytes=8388608, max_output_bytes=65536,
    max_host_result_bytes=262144, max_context_or_observation_bytes=1048576,
    max_prompt_bytes=262144, max_report_bytes=262144, max_response_bytes=65536,
    max_dispatch_receipt_bytes=65536, max_events=16, max_event_bytes=524288,
    max_events_bytes=2097152, max_depth=32, max_nodes=200000,
    min_integer=-9223372036854775808, max_integer=9223372036854775807)
_CAPS = dict(host_result=262144, context8=1048576, prompt=262144,
    response_bytes=65536, harness_report=262144, harness_events=2097152,
    before=1048576, after=1048576, dispatch_receipt=65536, caller_error_code=256)
_BUDGET = dict(decisions=1, logical_requests=1, ticks=1, wall_seconds=30, transport_retries=0)
_BINDING = 'run_id runtime_instance_id decision_id model_request_id context_sha256 request_sha256'.split()
_OBS = 'tick setup_revision synthetic hardware_verified devices'.split()
_BASE = set('status values tick setup_revision synthetic hardware_verified'.split())
_NODE = {'device_id', 'profile_id', 'role'}
_STATUS = {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}
_EVENT_TYPES = {'observation', 'policy_decision', 'intent', 'receipt', 'termination', 'error', 'transport_retry'}
_HARNESS_ERRORS = set('clock_error deadline_elapsed observation_error observation_invalid observation_evidence_error intent_evidence_error transport_retry_exhausted retry_evidence_error runtime_call_error receipt_invalid receipt_evidence_error policy_call_error proposal_invalid decision_evidence_error harness_contract_error'.split())
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
_SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_ESCAPE = re.compile(r'["\\\x00-\x1f]')
_FILES = dict(context8='context8.json', context7='public-context7.json', binding='binding.json',
    prompt='prompt.json', before='before.json', after='after.json', wire='wire.json',
    harness_report='harness-report.json', harness_events='harness-events.json', dispatch_receipt='dispatch-receipt.json')
_PRODUCER_FILES = dict(prompt='request.json', response_schema='response-schema.json', invocation='invocation.json',
    version_stdout='version.stdout', version_stderr='version.stderr', stdout_jsonl='stdout.jsonl',
    stderr='stderr.bin', final_text='final-text.bin', last_message='last-message.bin')


class CodexOneActionAssessmentError(ValueError):
    """A fixed code only; no input values, paths or underlying exception text."""
    def __init__(self, code):
        suffix = code.removeprefix(_PREFIX) if type(code) is str else 'invalid_input'
        self.code = _PREFIX + (suffix if suffix in _ERRORS else 'invalid_input')
        super().__init__(self.code)


class _Fault(Exception):
    def __init__(self, code='invalid_input'):
        self.code = code


def _fail(code='invalid_input'):
    raise _Fault(code)


def _fixed(code):
    try:
        raise CodexOneActionAssessmentError(code) from None
    except CodexOneActionAssessmentError as error:
        error.__cause__ = error.__context__ = None
        raise


def _C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def _H(data):
    return hashlib.sha256(data).hexdigest()


def _keys(value, names):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value) != set(names):
        _fail()


def _type(value, kind):
    if type(value) is not kind:
        _fail()


def _number(value, *, integer=False, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in ((int,) if integer else (int, float)):
        _fail()


def _identity(value):
    if type(value) is not str or not _ID.fullmatch(value):
        _fail()


def _hash(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not _SHA.fullmatch(value):
        _fail()


def _snapshot(packet, caller):
    """Bound native values before serialization; aliases consume nodes again."""
    _keys(packet, _PACKET)
    if caller is not None and (type(caller) is not str or caller not in _CALLER_CODES):
        _fail()
    nodes = 0
    total = 0
    active = set()

    def clone(value, cap):
        used = 0

        def consume(size):
            nonlocal used
            used += size
            if used > cap:
                _fail('limit_exceeded')

        def walk(item, depth):
            nonlocal nodes
            nodes += 1
            if nodes > _LIMITS['max_nodes'] or depth > _LIMITS['max_depth']:
                _fail('limit_exceeded')
            kind = type(item)
            if item is None:
                consume(4)
                return None
            if kind is bool:
                consume(4 if item else 5)
                return item
            if kind is int:
                if not _LIMITS['min_integer'] <= item <= _LIMITS['max_integer']:
                    _fail('limit_exceeded')
                consume(len(str(item)))
                return item
            if kind is float:
                if not math.isfinite(item):
                    _fail()
                consume(len(json.dumps(item, allow_nan=False)))
                return item
            if kind is str:
                if len(item) + 2 > cap - used:
                    _fail('limit_exceeded')
                consume(2)
                for start in range(0, len(item), 16384):
                    part = item[start:start + 16384]
                    try:
                        size = len(part.encode('utf-8'))
                    except UnicodeError:
                        _fail()
                    size += sum(1 if m[0] in '"\\\b\f\n\r\t' else 5 for m in _ESCAPE.finditer(part))
                    consume(size)
                return item
            if kind not in (dict, list) or id(item) in active:
                _fail()
            active.add(id(item))
            consume(2)
            try:
                if kind is dict:
                    result = {}
                    for i, (key, child) in enumerate(item.items()):
                        _type(key, str)
                        if i:
                            consume(1)
                        result[walk(key, depth + 1)] = walk(child, depth + 1)
                        consume(1)
                    return result
                result = []
                for i, child in enumerate(item):
                    if i:
                        consume(1)
                    result.append(walk(child, depth + 1))
                return result
            finally:
                active.remove(id(item))

        return walk(value, 0)

    result = {}
    components = {}
    for name in [*_PACKET, 'caller_error_code']:
        value = caller if name == 'caller_error_code' else packet[name]
        if value is None:
            result[name] = None
            components[name] = dict(present=False, bytes=0, sha256=None)
            continue
        if name == 'response_bytes':
            _type(value, bytes)
            if len(value) > _CAPS[name]:
                _fail('limit_exceeded')
            saved, raw = value, value
        else:
            if name == 'harness_events' and type(value) is list and len(value) > 16:
                _fail('limit_exceeded')
            saved = clone(value, _CAPS[name])
            raw = _C(saved)
            if name == 'harness_events' and type(saved) is list:
                if any(len(_C(e)) > 524288 for e in saved):
                    _fail('limit_exceeded')
        total += len(raw)
        if total > 8388608:
            _fail('limit_exceeded')
        result[name] = saved
        components[name] = dict(present=True, bytes=len(raw), sha256=_H(raw))
    result.pop('caller_error_code')
    return result, components


def _binding(value):
    _keys(value, _BINDING)
    for key in _BINDING[:4]:
        _identity(value[key])
    for key in _BINDING[4:]:
        _hash(value[key])


def _descriptor(value):
    _keys(value, 'path present bytes sha256 complete overflow extent'.split())
    for key in ('path', 'extent'):
        _type(value[key], str)
    for key in ('present', 'complete', 'overflow'):
        _type(value[key], bool)
    _number(value['bytes'], integer=True)
    _hash(value['sha256'], nullable=True)


def _envelope(value, *, node=False):
    if type(value) is not dict or not _BASE <= set(value):
        _fail()
    allowed = _BASE | _NODE | {'setup_changed', 'state'}
    if set(value) - allowed or (node and not _NODE <= set(value)):
        _fail()
    for key in ('tick', 'setup_revision'):
        _number(value[key], integer=True)
    for key in ('synthetic', 'hardware_verified', 'setup_changed'):
        if key in value:
            _type(value[key], bool)
    for key in ('status', *(_NODE & set(value))):
        _type(value[key], str)
    if 'state' in value:
        _type(value['state'], str)
    _type(value['values'], dict)


def _observation(value):
    _keys(value, _OBS)
    for key in ('tick', 'setup_revision'):
        _number(value[key], integer=True)
    for key in ('synthetic', 'hardware_verified'):
        _type(value[key], bool)
    _type(value['devices'], dict)
    for identity, node in value['devices'].items():
        _identity(identity)
        _envelope(node, node=True)


def _failure(value):
    _keys(value, ('code', 'stage'))
    if type(value['code']) is not str or value['code'] not in _CALLER_CODES:
        _fail()
    _identity(value['stage'])


def _proposal(value):
    _type(value, dict)
    _type(value.get('kind'), str)
    if value['kind'] == 'execute':
        _keys(value, ('kind', 'device_id', 'action', 'parameters'))
        _identity(value['device_id']); _identity(value['action']); _type(value['parameters'], dict)
    elif value['kind'] == 'advance':
        _keys(value, ('kind', 'ticks')); _number(value['ticks'], integer=True)
    elif value['kind'] == 'stop':
        _keys(value, ('kind', 'claim', 'reason'))
        _type(value['claim'], str); _type(value['reason'], str)


def _wire(value):
    _keys(value, ('schema_version', 'kind', 'request_sha256', 'producer', 'proposal'))
    _number(value['schema_version'], integer=True); _type(value['kind'], str); _hash(value['request_sha256'])
    _keys(value['producer'], ('kind', 'name'))
    for v in value['producer'].values():
        _type(v, str)
    _proposal(value['proposal'])


def _producer(value):
    _keys(value, 'schema_version kind exchange_ref status failure bindings client model attempts lifecycle usage cost timing controls cleanup artifacts limits verification'.split())
    for key in 'bindings client model attempts lifecycle cost timing controls cleanup artifacts limits verification'.split():
        _type(value[key], dict)
    _keys(value['bindings'], 'prompt_sha256 schema_sha256 invocation_sha256 producer_declaration'.split())
    for key in ('prompt_sha256', 'schema_sha256', 'invocation_sha256'):
        _hash(value['bindings'][key])
    _keys(value['model'], 'requested resolved cli_thread_id remote_request_id'.split())
    for k, v in value['model'].items():
        if v is not None or k == 'requested':
            _type(v, str)
    _keys(value['client'], 'name supported_version observed_version binary_content_sha256'.split())
    for k in ('name', 'supported_version', 'observed_version'):
        if value['client'][k] is not None:
            _type(value['client'][k], str)
    _hash(value['client']['binary_content_sha256'], nullable=True)
    _keys(value['attempts'], 'version_process_attempts model_process_attempts application_retries internal_network_requests internal_network_retries'.split())
    _keys(value['timing'], ('timeout_seconds', 'local_elapsed_seconds'))
    for v in value['timing'].values():
        _number(v)
    for v in value['attempts'].values():
        _number(v, integer=True, nullable=True)
    _keys(value['lifecycle'], 'model_process_started exit_code thread_started turn_started turn_completed agent_messages reasoning_items tool_items stdout_eof stderr_eof'.split())
    for k, v in value['lifecycle'].items():
        if k in {'model_process_started', 'stdout_eof', 'stderr_eof'}:
            if v is not None:
                _type(v, bool)
        else:
            _number(v, integer=True, nullable=True)
    if value['usage'] is not None:
        _keys(value['usage'], 'input_tokens cached_input_tokens cache_write_input_tokens output_tokens reasoning_output_tokens'.split())
        for v in value['usage'].values():
            _number(v, integer=True, nullable=True)
    _keys(value['cost'], 'kind amount currency price_version'.split())
    _type(value['cost']['kind'], str); _number(value['cost']['amount'], nullable=True)
    for k in ('currency', 'price_version'):
        if value['cost'][k] is not None:
            _type(value['cost'][k], str)
    _keys(value['controls'], 'requested documented observed unknown'.split())
    for k in ('requested', 'documented', 'observed'):
        _type(value['controls'][k], dict)
    _keys(value['controls']['requested'], 'ignore_user_config ignore_rules sandbox ephemeral empty_cwd model_local_attempt_cap automatic_retries'.split())
    for k, v in value['controls']['requested'].items():
        if k in {'model_local_attempt_cap', 'automatic_retries'}:
            _number(v, integer=True)
        else:
            _type(v, str if k == 'sandbox' else bool)
    _keys(value['controls']['documented'], 'ignore_user_config ignore_rules sandbox ephemeral'.split())
    for v in value['controls']['documented'].values():
        _type(v, str)
    _keys(value['controls']['observed'], 'argv_submitted argv_exit0 empty_cwd_at_spawn tool_items'.split())
    for k, v in value['controls']['observed'].items():
        if v is not None:
            _type(v, int if k == 'tool_items' else bool)
    _type(value['controls']['unknown'], list)
    for v in value['controls']['unknown']:
        _identity(v)
    _keys(value['cleanup'], 'version_child_reaped model_child_reaped readers_joined pipes_closed artifacts_closed descendants_reaped remote_cancelled secondary_errors'.split())
    for k, v in value['cleanup'].items():
        if k == 'secondary_errors':
            _type(v, list)
            for code in v:
                _identity(code)
        elif v is not None:
            _type(v, bool)
    _keys(value['verification'], 'wire_complete remote_identity_verified semantic_quality_verified external_data_authority_verified storage_authenticity_verified'.split())
    for v in value['verification'].values():
        _type(v, bool)
    for v in value['limits'].values():
        _number(v)
    if value['failure'] is not None:
        _keys(value['failure'], ('code', 'phase'))
        if type(value['failure']['code']) is not str or value['failure']['code'] not in {'codex_cli_response_' + x for x in _CLI_CODES}:
            _fail()
        _identity(value['failure']['phase'])
    _keys(value['artifacts'], _PRODUCER_FILES)
    for d in value['artifacts'].values():
        _descriptor(d)
    for key in ('schema_version',):
        _number(value[key], integer=True)
    for key in ('kind', 'exchange_ref', 'status'):
        _type(value[key], str)


def _shapes(p):
    h = p['host_result']
    if h is not None:
        _keys(h, 'schema_version kind run_id status failure declaration budget step cancellation cleanup execution verification'.split())
        _number(h['schema_version'], integer=True)
        for key in ('kind', 'status'):
            _type(h[key], str)
        _identity(h['run_id'])
        if h['failure'] is not None:
            _failure(h['failure'])
        _keys(h['declaration'], 'scenario requested_model producer_name catalog_sha256 schema_sha256 virtual_dispatch_authorized scope'.split())
        for key in ('scenario', 'requested_model', 'producer_name', 'scope'):
            _type(h['declaration'][key], str)
        for key in ('catalog_sha256', 'schema_sha256'):
            _hash(h['declaration'][key])
        _type(h['declaration']['virtual_dispatch_authorized'], bool)
        b = h['budget']
        _keys(b, 'limits reserved_model_calls producer_calls_started version_process_attempts model_process_attempts elapsed_seconds reservation_refunded application_retries new_budget_granted'.split())
        _keys(b['limits'], 'model_calls wall_seconds producer_cleanup_allowance_seconds harness_budgets'.split())
        _keys(b['limits']['harness_budgets'], _BUDGET)
        for k in ('reserved_model_calls', 'producer_calls_started', 'version_process_attempts', 'model_process_attempts', 'application_retries'):
            _number(b[k], integer=True, nullable=k in {'version_process_attempts', 'model_process_attempts'})
        for k in ('reservation_refunded', 'new_budget_granted'):
            _type(b[k], bool)
        _number(b['elapsed_seconds'])
        for k in ('wall_seconds', 'producer_cleanup_allowance_seconds'):
            _number(b['limits'][k])
        _number(b['limits']['model_calls'], integer=True)
        for k, v in b['limits']['harness_budgets'].items():
            _number(v, integer=k != 'wall_seconds')
        s = h['step']
        _keys(s, 'stage binding before after transport wire dispatch harness artifacts failure'.split())
        _identity(s['stage'])
        if s['binding'] is not None:
            _binding(s['binding'])
        for k in ('before', 'after'):
            if s[k] is not None:
                _keys(s[k], 'tick setup_revision device_count sha256 present'.split())
                for n in ('tick', 'setup_revision', 'device_count'):
                    _number(s[k][n], integer=True)
                _type(s[k]['present'], bool)
                _hash(s[k]['sha256'])
        _keys(s['dispatch'], 'intent_seen request_id operation reserved_logical_requests confirmed_receipts runtime_call_attempts receipt_status effect'.split())
        _type(s['dispatch']['intent_seen'], bool)
        for k in ('reserved_logical_requests', 'confirmed_receipts', 'runtime_call_attempts'):
            _number(s['dispatch'][k], integer=True, nullable=k == 'runtime_call_attempts')
        for k in ('request_id', 'operation', 'receipt_status', 'effect'):
            if s['dispatch'][k] is not None:
                _type(s['dispatch'][k], str)
        if s['failure'] is not None:
            _failure(s['failure'])
        if s['wire'] is not None:
            _wire(s['wire'])
        if s['harness'] is not None:
            _keys(s['harness'], 'termination unresolved_request_ids legacy_ai_model_called'.split())
            _type(s['harness']['legacy_ai_model_called'], bool)
        _keys(s['artifacts'], _FILES)
        for d in s['artifacts'].values():
            _descriptor(d)
        if s['transport'] is not None:
            _keys(s['transport'], ('exchange_ref', 'receipt', 'receipt_sha256'))
            _type(s['transport']['exchange_ref'], str)
            _hash(s['transport']['receipt_sha256'], nullable=True)
            _producer(s['transport']['receipt'])
        _keys(h['cancellation'], 'requested scope observed_stage remote_cancel_verified'.split())
        _keys(h['cleanup'], 'supervisor_stop_requested terminal_report_observed host_artifacts_closed virtual_outputs_disabled remote_cancel_verified secondary_errors'.split())
        for k in ('requested', 'remote_cancel_verified'):
            _type(h['cancellation'][k], bool)
        _type(h['cancellation']['scope'], str)
        if h['cancellation']['observed_stage'] is not None:
            _identity(h['cancellation']['observed_stage'])
        for k in ('supervisor_stop_requested', 'terminal_report_observed', 'remote_cancel_verified'):
            _type(h['cleanup'][k], bool)
        for k in ('host_artifacts_closed', 'virtual_outputs_disabled'):
            if h['cleanup'][k] is not None:
                _type(h['cleanup'][k], bool)
        _type(h['cleanup']['secondary_errors'], list)
        for code in h['cleanup']['secondary_errors']:
            _identity(code)
        _keys(h['execution'], 'mode synthetic model_proposal_dispatches task_assessment_status task_score closed_loop_complete hardware_verified physical_cleanup_verified'.split())
        _number(h['execution']['model_proposal_dispatches'], integer=True, nullable=True)
        _number(h['execution']['task_score'], nullable=True)
        for k in ('synthetic', 'closed_loop_complete', 'hardware_verified', 'physical_cleanup_verified'):
            _type(h['execution'][k], bool)
        for k in ('mode', 'task_assessment_status'):
            _type(h['execution'][k], str)
        _keys(h['verification'], 'wire_accepted dispatch_trace_complete source_inputs_unchanged remote_identity_verified semantic_quality_verified hardware_verified'.split())
        for v in h['verification'].values():
            _type(v, bool)
    c = p['context8']
    if c is not None:
        _keys(c, 'schema_version goal catalog topology role_actions observations last_receipt remaining_budget'.split())
        _number(c['schema_version'], integer=True)
        for k in ('goal', 'catalog', 'topology', 'role_actions'):
            _type(c[k], dict)
        _keys(c['remaining_budget'], _BUDGET)
        for k, v in c['remaining_budget'].items():
            _number(v, integer=k != 'wall_seconds')
        _observation(c['observations'])
        if c['last_receipt'] is not None:
            _envelope(c['last_receipt'])
    prompt = p['prompt']
    if prompt is not None:
        _keys(prompt, 'schema_version kind binding expected_producer messages'.split())
        _number(prompt['schema_version'], integer=True)
        _type(prompt['kind'], str)
        _binding(prompt['binding'])
        _keys(prompt['expected_producer'], ('kind', 'name'))
        for v in prompt['expected_producer'].values():
            _type(v, str)
        _type(prompt['messages'], list)
        for message in prompt['messages']:
            _keys(message, ('role', 'content'))
            for v in message.values():
                _type(v, str)
    report = p['harness_report']
    if report is not None:
        _keys(report, 'schema_version kind run_id runtime_instance_id synthetic hardware_verified ai_model_called policy termination task_outcome cleanup usage evidence unresolved_request_ids assessment'.split())
        _number(report['schema_version'], integer=True)
        for k in ('run_id', 'runtime_instance_id'):
            _identity(report[k])
        for k in ('synthetic', 'hardware_verified', 'ai_model_called'):
            _type(report[k], bool)
        _keys(report['policy'], ('kind', 'id'))
        for v in report['policy'].values():
            _type(v, str)
        _keys(report['termination'], ('reason', 'policy_claim'))
        for k in ('kind', 'task_outcome'):
            _type(report[k], str)
        _type(report['termination']['reason'], str)
        if report['termination']['policy_claim'] is not None:
            _type(report['termination']['policy_claim'], str)
        _keys(report['assessment'], 'status verdict evaluator_id evidence_refs summary_code'.split())
        _keys(report['cleanup'], ('status', 'evidence_refs'))
        _keys(report['evidence'], ('measurement_refs', 'operator_transcript_ref'))
        _keys(report['usage'], 'decisions logical_requests transport_retries tick_delta reserved_ticks elapsed_ms'.split())
        for k, v in report['usage'].items():
            _number(v, integer=k != 'elapsed_ms')
        _type(report['unresolved_request_ids'], list)
        for v in report['unresolved_request_ids']:
            _identity(v)
        for refs in (report['assessment']['evidence_refs'], report['cleanup']['evidence_refs'], report['evidence']['measurement_refs']):
            _type(refs, list)
            for ref in refs:
                _identity(ref)
    events = p['harness_events']
    if events is not None:
        _type(events, list)
        for event in events:
            _keys(event, 'schema_version kind event_id run_id runtime_instance_id sequence type payload'.split())
            for k in ('schema_version', 'sequence'):
                _number(event[k], integer=True)
            for k in ('event_id', 'run_id', 'runtime_instance_id'):
                _identity(event[k])
            _type(event['kind'], str)
            _type(event['type'], str)
            _type(event['payload'], dict)
            body, kind = event['payload'], event['type']
            if kind == 'observation':
                if set(body) not in ({'observation'}, {'observation', 'cause_request_id'}):
                    _fail()
                _observation(body['observation'])
                if 'cause_request_id' in body:
                    _identity(body['cause_request_id'])
            elif kind == 'policy_decision':
                _keys(body, ('proposal',)); _proposal(body['proposal'])
            elif kind == 'intent':
                _keys(body, ('request_id', 'operation', 'body', 'logical_request'))
                _identity(body['request_id']); _type(body['operation'], str)
                _type(body['body'], dict); _number(body['logical_request'], integer=True)
                if body['operation'] in {'execute', 'advance'}:
                    _proposal(dict(kind=body['operation'], **body['body']))
            elif kind == 'receipt':
                _keys(body, ('request_id', 'result')); _identity(body['request_id']); _envelope(body['result'])
            elif kind == 'termination':
                _keys(body, ('code', 'unresolved_request_ids')); _type(body['code'], str)
                _type(body['unresolved_request_ids'], list)
                for v in body['unresolved_request_ids']:
                    _identity(v)
            elif kind == 'error':
                _keys(body, ('code',)); _type(body['code'], str)
            elif kind == 'transport_retry':
                _keys(body, ('request_id', 'retry')); _identity(body['request_id']); _number(body['retry'], integer=True)
    for k in ('before', 'after'):
        if p[k] is not None:
            _observation(p[k])
    if p['dispatch_receipt'] is not None:
        _envelope(p['dispatch_receipt'])


class _Assessment:
    def __init__(self, packet, caller, components):
        self.p, self.caller = packet, caller
        self.h, self.c, self.prompt = packet['host_result'], packet['context8'], packet['prompt']
        self.report, self.events = packet['harness_report'], packet['harness_events']
        self.checks = dict.fromkeys(_CHECKS, 'unverified')
        self.reasons = {'task_evaluator_inapplicable', 'supplied_provenance_only', 'cleanup_unverified'}
        self.missing = False
        self.unsupported = False
        self.effect, self.command = 'unknown', 'unknown'
        self.core = None
        self.wire = None
        self.complete = False
        self.binding = (self.h['step']['binding'] if self.h else None) or (self.prompt['binding'] if self.prompt else None)
        self.first = (dict(self.h['failure'], source='host_result') if self.h and self.h['failure']
                      else dict(code=caller, stage=None, source='caller') if caller else None)
        self.components = components

    def bad(self, check, reason):
        self.checks[check] = 'contradicted'
        self.reasons.add(reason)

    def lack(self, reason='evidence_missing'):
        self.missing = True
        self.reasons.add(reason)

    def good(self, check):
        if self.checks[check] != 'contradicted':
            self.checks[check] = 'supported'

    def compare(self, check, actual, expected, reason='binding_mismatch'):
        if _C(actual) != _C(expected):
            self.bad(check, reason)

    def protocol(self):
        h, c, r, prompt = self.h, self.c, self.report, self.prompt
        if prompt:
            try:
                def pairs(items):
                    result = {}
                    for k, v in items:
                        if k in result:
                            raise ValueError()
                        result[k] = v
                    return result
                if len(prompt['messages']) != 2 or prompt['messages'][1]['role'] != 'user':
                    raise ValueError()
                user = json.loads(prompt['messages'][1]['content'], object_pairs_hook=pairs,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                _keys(user, ('request', 'request_sha256'))
                core = user['request']
                _keys(core, 'schema_version kind binding expected_producer user_input'.split())
                _keys(core['binding'], _BINDING[:-1])
                _keys(core['expected_producer'], ('kind', 'name'))
                _keys(core['user_input'], ('public_context', 'delegation'))
                context = core['user_input']['public_context']
                _keys(context, 'schema_version goal catalog topology role_actions observations last_receipt'.split())
                _type(context['goal'], dict); _type(context['goal'].get('kind'), str)
                if context['goal']['kind'] != 'acquire_fresh_rf_sensor':
                    self.unsupported = True
                self.core = core
                if user.get('request_sha256') != _H(_C(core)):
                    self.bad('input_binding', 'binding_mismatch')
            except (_Fault, ValueError, KeyError, TypeError, RecursionError, UnicodeError):
                self.core = None
                self.bad('wire_scope', 'wire_scope_mismatch')
        if h and h['kind'] != 'codex_virtual_one_action_result':
            self.unsupported = True
        if c and c['goal'].get('kind') != 'acquire_fresh_rf_sensor':
            self.unsupported = True
        if r and (r['kind'] != 'virtual_fleet_harness_result'
                  or r['policy'] != dict(kind='fixture', id='codex_virtual_one_action')
                  or r['ai_model_called'] is not False or r['task_outcome'] != 'not_assessed'
                  or r['assessment'] != dict(status='not_assessed', verdict=None, evaluator_id=None, evidence_refs=[], summary_code=None)
                  or r['cleanup'] != dict(status='not_assessed', evidence_refs=[])):
            self.unsupported = True

    def inputs(self):
        h, c, prompt, binding = self.h, self.c, self.prompt, self.binding
        if not all(x is not None for x in (h, c, prompt, binding, self.p['before'])):
            self.lack()
        else:
            self.good('input_binding')
        if h:
            self.compare('input_binding', h['schema_version'], 1)
            d = h['declaration']
            if (d['scope'] != 'rf_sensor_proposal_v1' or d['producer_name'] != 'dgm-virtual-operator-v1'
                    or d['scenario'] not in {'normal', 'restored_disconnect'}
                    or d['requested_model'] not in {'gpt-6.1-sol', 'gpt-6-astra'}
                    or d['virtual_dispatch_authorized'] is not True):
                self.bad('input_binding', 'host_summary_mismatch')
            b = h['budget']
            if b['limits'] != dict(model_calls=8, wall_seconds=60,
                    producer_cleanup_allowance_seconds=6, harness_budgets=_BUDGET):
                self.bad('single_action', 'reported_budget_violation')
            if (any(b[k] not in (0, 1) for k in ('reserved_model_calls', 'producer_calls_started'))
                    or any(b[k] is not None and b[k] not in (0, 1) for k in ('version_process_attempts', 'model_process_attempts'))
                    or b['application_retries'] != 0 or b['reservation_refunded'] is not False
                    or b['new_budget_granted'] is not False or not 0 <= b['elapsed_seconds'] <= 60
                    or b['producer_calls_started'] > b['reserved_model_calls']):
                self.bad('single_action', 'reported_budget_violation')
            e = h['execution']
            dispatch = h['step']['dispatch']
            counts = [e['model_proposal_dispatches'], dispatch['reserved_logical_requests'],
                      dispatch['confirmed_receipts'], dispatch['runtime_call_attempts']]
            if any(v is not None and v not in (0, 1) for v in counts):
                self.bad('single_action', 'single_action_violation')
            if (e['mode'] != 'virtual_one_action' or e['synthetic'] is not True or e['task_assessment_status'] != 'not_executed'
                    or e['task_score'] is not None or any(e[k] is not False for k in ('closed_loop_complete', 'hardware_verified', 'physical_cleanup_verified'))
                    or any(h['verification'][k] is not False for k in ('remote_identity_verified', 'semantic_quality_verified', 'hardware_verified'))):
                self.bad('input_binding', 'host_summary_mismatch')
            if h['step']['binding']:
                self.compare('input_binding', h['run_id'], h['step']['binding']['run_id'])
        if binding and prompt:
            self.compare('input_binding', binding, prompt['binding'])
        if c:
            remaining = c['remaining_budget']
            if (any(remaining[k] != v for k, v in dict(decisions=0, logical_requests=1, ticks=1, transport_retries=0).items())
                    or not 0 <= remaining['wall_seconds'] <= 30):
                self.bad('single_action', 'reported_budget_violation')
            if c['schema_version'] != 1 or c['last_receipt'] is not None:
                self.bad('input_binding', 'binding_mismatch')
            context7 = {k: v for k, v in c.items() if k != 'remaining_budget'}
            if binding:
                self.compare('input_binding', binding['context_sha256'], _H(_C(context7)))
            if self.core:
                self.compare('input_binding', self.core['user_input'].get('public_context'), context7)
                declared = self.core['user_input'].get('delegation')
                if declared != dict(scope='rf_sensor_proposal_v1', harness_budgets=_BUDGET, outer_limits=dict(wall_seconds=60, model_calls=8)):
                    self.bad('single_action', 'reported_budget_violation')
            if self.p['before']:
                self.compare('same_run_evidence', self.p['before'], c['observations'])
        if self.core and binding:
            self.compare('input_binding', self.core.get('binding'), {k: v for k, v in binding.items() if k != 'request_sha256'})
            self.compare('input_binding', _H(_C(self.core)), binding['request_sha256'])

    def observations(self):
        c = self.c
        if c is None:
            self.lack()
            return
        profiles = c['catalog'].get('profiles')
        nodes = c['topology'].get('devices')
        if type(profiles) is not list or type(nodes) is not list:
            _fail()
        if any(type(x) is not dict for x in profiles + nodes):
            _fail()
        for profile in profiles:
            _identity(profile.get('profile_id')); _type(profile.get('role'), str)
        for node in nodes:
            _keys(node, ('id', 'profile_id'))
            _identity(node['id']); _identity(node['profile_id'])
        profile_map = {x.get('profile_id'): x for x in profiles if type(x.get('profile_id')) is str}
        devices = {}
        for node in nodes:
            identity = node.get('id')
            profile = profile_map.get(node.get('profile_id'))
            if type(identity) is str and profile is not None:
                devices[identity] = dict(device_id=identity, profile_id=node['profile_id'], role=profile.get('role'))
        if len(profiles) != 64 or len(profile_map) != 64 or len(nodes) != 64 or len(devices) != 64:
            self.bad('same_run_evidence', 'binding_mismatch')
        values = [c['observations'], self.p['before'], self.p['after']]
        values += [e['payload']['observation'] for e in self.events or [] if e['type'] == 'observation']
        for obs in values:
            if obs is None:
                continue
            if (obs['synthetic'] is not True or obs['hardware_verified'] is not False
                    or obs['tick'] < 0 or obs['setup_revision'] < 0 or len(obs['devices']) != 64 or set(obs['devices']) != set(devices)):
                self.bad('same_run_evidence', 'binding_mismatch')
            for identity, node in obs['devices'].items():
                expected = devices.get(identity)
                if (expected is None or any(node.get(k) != expected.get(k) for k in _NODE)
                        or node['tick'] != obs['tick'] or node['setup_revision'] != obs['setup_revision']
                        or node['synthetic'] is not True or node['hardware_verified'] is not False or node['status'] not in _STATUS):
                    self.bad('same_run_evidence', 'binding_mismatch')
        goal = c['goal']
        _keys(goal, ('kind', 'dut_id', 'sensor_id', 'minimum_acquisition_tick'))
        _number(goal['minimum_acquisition_tick'], integer=True)
        for k, role in (('dut_id', 'dut'), ('sensor_id', 'power_sensor')):
            _identity(goal[k])
            device = devices.get(goal[k])
            if device is None or device.get('role') != role:
                self.bad('same_run_evidence', 'binding_mismatch')

    def wire_scope(self):
        h = self.h
        if h is None:
            self.lack('wire_evidence_missing')
            return
        wire = h['step']['wire']
        accepted = h['verification']['wire_accepted']
        if accepted or wire is not None:
            if accepted is not True or wire is None:
                self.bad('wire_scope', 'host_summary_mismatch')
            if self.prompt is None or self.p['response_bytes'] is None:
                self.lack('wire_evidence_missing')
                return
            try:
                decoded = decode_operator_response(self.p['response_bytes'], self.prompt)
            except ModelOperatorBoundaryError:
                self.bad('wire_scope', 'wire_scope_mismatch')
                return
            self.compare('wire_scope', decoded, wire, 'wire_scope_mismatch')
            self.wire = decoded
            proposal = decoded['proposal']
            goal = self.c['goal'] if self.c else self.core['user_input']['public_context']['goal'] if self.core else None
            allowed = (proposal['kind'] == 'stop' or proposal == dict(kind='advance', ticks=1)
                or goal is not None and proposal['kind'] == 'execute' and proposal.get('parameters') == {}
                and ((proposal.get('device_id') == goal['dut_id'] and proposal.get('action') == 'start')
                     or (proposal.get('device_id') == goal['sensor_id'] and proposal.get('action') in {'acquire', 'read'})))
            if not allowed:
                self.bad('wire_scope', 'wire_scope_mismatch')
            else:
                self.good('wire_scope')
        elif not h['failure']:
            self.lack('wire_evidence_missing')

    def artifact(self, desc, body, check, path):
        if desc['path'] != path or desc['bytes'] < 0:
            self.bad(check, 'host_summary_mismatch')
        if not desc['present'] or not desc['complete'] or desc['overflow'] or desc['extent'] != 'whole_file':
            self.lack()
            return
        if body is None:
            self.lack()
        elif desc['bytes'] != len(body) or desc['sha256'] != _H(body):
            self.bad(check, 'host_summary_mismatch')

    def artifacts(self):
        h = self.h
        if h is None:
            return
        s = h['step']
        for name, path in _FILES.items():
            if name in self.p:
                value = self.p[name]
            elif name == 'context7':
                value = {k: v for k, v in self.c.items() if k != 'remaining_budget'} if self.c else None
            elif name == 'wire':
                value = s['wire']
            else:
                value = dict(binding=s['binding'], delegation=self.core['user_input']['delegation'],
                    remaining_budget=self.c['remaining_budget'], catalog_sha256=h['declaration']['catalog_sha256'],
                    schema_sha256=h['declaration']['schema_sha256']) if self.core and self.c and s['binding'] else None
            d = s['artifacts'][name]
            # An original pre-dispatch failure can legitimately have no after/wire/receipt.
            if not d['present'] and value is None and (name in {'after', 'wire', 'dispatch_receipt'}):
                continue
            if value is None:
                if d['present']:
                    self.lack()
                continue
            self.artifact(d, _C(value), 'effect_receipt' if name in {'before', 'after', 'dispatch_receipt'} else 'same_run_evidence', path)
        for name in ('before', 'after'):
            value, summary = self.p[name], s[name]
            if value is not None and summary is not None:
                self.compare('effect_receipt', summary, dict(tick=value['tick'], setup_revision=value['setup_revision'],
                    device_count=len(value['devices']), sha256=_H(_C(value)), present=True), 'host_summary_mismatch')
            elif value is not None or summary is not None:
                self.lack()
        t = s['transport']
        if t is None:
            if h['verification']['wire_accepted']:
                self.lack('wire_evidence_missing')
            return
        r = t['receipt']
        if r['failure'] is not None and h['failure'] is not None:
            self.compare('error_and_cleanup', r['failure']['code'], h['failure']['code'], 'first_error_mismatch')
        for actual, expected in ((t['exchange_ref'], r['exchange_ref']),
                (r['bindings']['schema_sha256'], h['declaration']['schema_sha256']),
                (r['model']['requested'], h['declaration']['requested_model']),
                (r['bindings']['producer_declaration'], dict(kind='model', name=h['declaration']['producer_name']))):
            self.compare('input_binding', actual, expected)
        if self.prompt:
            self.compare('input_binding', r['bindings']['prompt_sha256'], _H(_C(self.prompt)))
            self.artifact(r['artifacts']['prompt'], _C(self.prompt), 'input_binding', 'request.json')
        if t['receipt_sha256'] is not None:
            self.compare('input_binding', t['receipt_sha256'], _H(_C(r)))
        elif h['verification']['wire_accepted']:
            self.lack('wire_evidence_missing')
        for name in ('final_text', 'last_message'):
            if self.p['response_bytes'] is not None:
                self.artifact(r['artifacts'][name], self.p['response_bytes'], 'wire_scope', _PRODUCER_FILES[name])
            elif h['verification']['wire_accepted']:
                self.lack('wire_evidence_missing')
        if h['verification']['wire_accepted'] and (r['schema_version'] != 1 or r['kind'] != 'codex_cli_response_receipt'
                or r['status'] != 'complete' or r['failure'] is not None or r['verification'].get('wire_complete') is not True):
            self.bad('wire_scope', 'wire_scope_mismatch')
        for key in ('remote_identity_verified', 'semantic_quality_verified', 'external_data_authority_verified', 'storage_authenticity_verified'):
            if r['verification'].get(key) is not False:
                self.bad('input_binding', 'host_summary_mismatch')
        for key in ('version_process_attempts', 'model_process_attempts'):
            if r['attempts'][key] not in (0, 1, None):
                self.bad('single_action', 'reported_budget_violation')
            if r['attempts'][key] is not None and h['budget'][key] is not None:
                self.compare('single_action', r['attempts'][key], h['budget'][key], 'host_summary_mismatch')
        timing = r['timing']
        if (r['attempts']['application_retries'] != 0 or not 0 < timing['timeout_seconds'] <= 60
                or not 0 <= timing['local_elapsed_seconds'] <= 60):
            self.bad('single_action', 'reported_budget_violation')

    def graph(self):
        events, report, binding = self.events, self.report, self.binding
        if events is None:
            self.lack()
            return
        seen = set()
        for index, event in enumerate(events, 1):
            if event['event_id'] in seen or event['sequence'] != index or event['type'] not in _EVENT_TYPES:
                self.bad('same_run_evidence', 'binding_mismatch')
            seen.add(event['event_id'])
            if event['schema_version'] != 1 or event['kind'] != 'operator_event':
                self.bad('same_run_evidence', 'binding_mismatch')
            if binding:
                for k in ('run_id', 'runtime_instance_id'):
                    self.compare('same_run_evidence', event[k], binding[k])
        groups = {kind: [e for e in events if e['type'] == kind] for kind in _EVENT_TYPES}
        intents, receipts, decisions, terminals = (groups[k] for k in ('intent', 'receipt', 'policy_decision', 'termination'))
        if max(len(intents), len(receipts), len(decisions)) > 1 or groups['transport_retry']:
            self.bad('single_action', 'single_action_violation')
        if len(terminals) > 1 or terminals and terminals[-1] is not events[-1]:
            self.bad('single_action', 'single_action_violation')
        self.complete = bool(events and len(terminals) == 1 and terminals[0] is events[-1])
        if not self.complete or report is None:
            self.lack('execution_unresolved')
        else:
            self.good('same_run_evidence')
            self.good('single_action')
        if report:
            if binding:
                for key in ('run_id', 'runtime_instance_id'):
                    self.compare('same_run_evidence', report[key], binding[key])
            if report['schema_version'] != 1 or report['synthetic'] is not True or report['hardware_verified'] is not False:
                self.bad('same_run_evidence', 'binding_mismatch')
            for refs in (report['evidence']['measurement_refs'], report['cleanup']['evidence_refs'], report['assessment']['evidence_refs']):
                if any(ref not in seen for ref in refs):
                    self.bad('same_run_evidence', 'binding_mismatch')
            if report['evidence']['operator_transcript_ref'] != 'artifact:operator_events':
                self.bad('same_run_evidence', 'binding_mismatch')
            u = report['usage']
            if (any(not 0 <= u[k] <= 1 for k in ('decisions', 'logical_requests', 'tick_delta', 'reserved_ticks'))
                    or u['transport_retries'] != 0 or not 0 <= u['elapsed_ms'] <= 30000):
                self.bad('single_action', 'reported_budget_violation')
            if self.complete:
                # A failed charged policy call emits an error, rather than a policy_decision.
                charged = len(decisions) + int(not decisions and bool(groups['error']))
                for actual, expected in ((u['decisions'], charged), (u['logical_requests'], len(intents))):
                    self.compare('single_action', actual, expected, 'host_summary_mismatch')
                self.compare('same_run_evidence', terminals[0]['payload']['unresolved_request_ids'], report['unresolved_request_ids'])
                if terminals[0]['payload']['code'] != 'run_terminated':
                    self.bad('same_run_evidence', 'binding_mismatch')
            elif u['logical_requests'] < len(intents) or u['decisions'] < len(decisions):
                self.bad('single_action', 'host_summary_mismatch')
            if report['unresolved_request_ids']:
                self.lack('execution_unresolved')
        if self.wire and decisions:
            self.compare('wire_scope', decisions[0]['payload']['proposal'], self.wire['proposal'], 'wire_scope_mismatch')
        obs = groups['observation']
        if self.p['before'] is not None and obs:
            self.compare('same_run_evidence', obs[0]['payload'], dict(observation=self.p['before']))
        elif not obs:
            self.lack()
        if intents:
            intent = intents[0]['payload']
            if intent['logical_request'] != 1:
                self.bad('single_action', 'single_action_violation')
            if self.wire:
                proposal = self.wire['proposal']
                self.compare('wire_scope', dict(kind=intent['operation'], **intent['body']), proposal, 'wire_scope_mismatch')
            else:
                self.lack('wire_evidence_missing')
            if receipts:
                self.compare('effect_receipt', receipts[0]['payload']['request_id'], intent['request_id'], 'receipt_observation_mismatch')
                if receipts[0]['sequence'] <= intents[0]['sequence']:
                    self.bad('effect_receipt', 'receipt_observation_mismatch')
            if len(obs) > 1:
                self.compare('effect_receipt', obs[-1]['payload'].get('cause_request_id'), intent['request_id'], 'receipt_observation_mismatch')
                if receipts and obs[-1]['sequence'] <= receipts[0]['sequence']:
                    self.bad('effect_receipt', 'receipt_observation_mismatch')
            if decisions and decisions[0]['sequence'] >= intents[0]['sequence']:
                self.bad('single_action', 'single_action_violation')
            self.action(intents, receipts, decisions, obs)
        elif receipts or any('cause_request_id' in e['payload'] for e in obs):
            self.bad('single_action', 'single_action_violation')
        else:
            self.no_dispatch(decisions, groups['error'])

    def action(self, intents, receipts, decisions, observations):
        p, h, r = self.p, self.h, self.report
        if not (self.complete and r is not None and h is not None and self.wire is not None
                and len(intents) == len(receipts) == len(decisions) == 1 and len(observations) == 2
                and p['before'] is not None and p['after'] is not None and p['dispatch_receipt'] is not None
                and not r['unresolved_request_ids']):
            self.lack('execution_unresolved')
            return
        intent, receipt = intents[0]['payload'], receipts[0]['payload']['result']
        before, after = p['before'], p['after']
        self.compare('effect_receipt', p['dispatch_receipt'], receipt, 'receipt_observation_mismatch')
        self.compare('effect_receipt', observations[-1]['payload']['observation'], after, 'receipt_observation_mismatch')
        operation = intent['operation']
        if (operation not in {'execute', 'advance'} or receipt['status'] not in _STATUS
                or receipt['synthetic'] is not True or receipt['hardware_verified'] is not False
                or after['tick'] != before['tick'] + int(operation == 'advance')
                or receipt['tick'] != after['tick'] or receipt['setup_revision'] < before['setup_revision']
                or after['setup_revision'] < receipt['setup_revision']):
            self.bad('effect_receipt', 'receipt_observation_mismatch')
        if operation == 'execute':
            target = before['devices'].get(intent['body'].get('device_id'))
            if target is None or any(receipt.get(k) != target.get(k) for k in _NODE):
                self.bad('effect_receipt', 'receipt_observation_mismatch')
        elif receipt['status'] != 'ok' or receipt['values'].get('advanced_ticks') != 1 or type(receipt['values'].get('advanced_ticks')) is not int:
            self.bad('effect_receipt', 'receipt_observation_mismatch')
        effect = 'unchanged' if _C(before) == _C(after) else 'changed'
        self.compare('effect_receipt', h['step']['dispatch'], dict(intent_seen=True, request_id=intent['request_id'],
            operation=operation, reserved_logical_requests=1, confirmed_receipts=1, runtime_call_attempts=1,
            receipt_status=receipt['status'], effect=effect), 'host_summary_mismatch')
        self.compare('single_action', h['execution']['model_proposal_dispatches'], 1, 'host_summary_mismatch')
        self.compare('single_action', r['usage']['tick_delta'], after['tick'] - before['tick'], 'host_summary_mismatch')
        if r['usage']['reserved_ticks'] != 0 or r['termination'] != dict(reason='supervisor_stop', policy_claim=None):
            self.bad('single_action', 'host_summary_mismatch')
        self.good('effect_receipt')
        self.effect = effect
        self.command = 'accepted' if receipt['status'] == 'ok' else 'pending' if receipt['status'] == 'pending' else 'rejected'
        self.reasons.add('effect_observed')
        if self.command == 'pending':
            self.reasons.add('command_pending_observed')
        if self.command == 'rejected':
            self.reasons.add('command_rejected_observed')
            if not h['failure'] or h['failure'] != dict(code='operator_virtual_one_action_runtime_rejected', stage='dispatch'):
                self.bad('error_and_cleanup', 'first_error_mismatch')

    def no_dispatch(self, decisions, errors):
        h, report = self.h, self.report
        if not h or not report or not self.complete or report['unresolved_request_ids']:
            self.lack('execution_unresolved')
            return
        valid = False
        if self.wire and self.wire['proposal']['kind'] == 'stop':
            self.compare('wire_scope', report['termination'], dict(reason='policy_stop', policy_claim=self.wire['proposal']['claim']), 'wire_scope_mismatch')
            if len(decisions) != 1:
                self.bad('single_action', 'single_action_violation')
            if self.p['after'] is None or self.p['before'] is None:
                self.lack()
            else:
                self.compare('effect_receipt', self.p['after'], self.p['before'], 'receipt_observation_mismatch')
            self.reasons.add('stop_not_completion')
            valid = True
        elif h['failure'] and not h['verification']['wire_accepted'] and h['step']['wire'] is None:
            if report['termination']['reason'] not in {'policy_error', 'invalid_proposal', 'runtime_error', 'supervisor_stop', 'wall_deadline', 'evidence_error'}:
                self.bad('error_and_cleanup', 'first_error_mismatch')
            if decisions:
                self.bad('wire_scope', 'wire_scope_mismatch')
            if self.p['dispatch_receipt'] is not None:
                self.bad('effect_receipt', 'receipt_observation_mismatch')
            self.good('wire_scope')
            self.reasons.add('host_error_before_dispatch')
            valid = True
        if not valid:
            self.lack('execution_unresolved')
            return
        d = h['step']['dispatch']
        self.compare('single_action', d, dict(intent_seen=False, request_id=None, operation=None,
            reserved_logical_requests=0, confirmed_receipts=0, runtime_call_attempts=0, receipt_status=None, effect='not_applicable'), 'host_summary_mismatch')
        self.compare('single_action', h['execution']['model_proposal_dispatches'], 0, 'host_summary_mismatch')
        if report['usage']['logical_requests'] or report['usage']['tick_delta'] or report['usage']['reserved_ticks']:
            self.bad('single_action', 'host_summary_mismatch')
        self.good('effect_receipt')
        self.effect, self.command = 'not_applicable', 'not_dispatched'

    def errors(self, groups):
        h, report = self.h, self.report
        if h is None:
            return
        failure = h['failure']
        expected_status = ('rejected' if failure and failure['code'] == 'operator_virtual_one_action_runtime_rejected'
            else 'failed' if failure else 'stopped' if self.wire and self.wire['proposal']['kind'] == 'stop' else 'observed')
        self.compare('error_and_cleanup', h['status'], expected_status, 'host_summary_mismatch')
        if any(e['payload']['code'] not in _HARNESS_ERRORS for e in groups['error']):
            self.bad('error_and_cleanup', 'first_error_mismatch')
        if groups['error'] and failure is None:
            self.bad('error_and_cleanup', 'first_error_mismatch')
        self.compare('error_and_cleanup', h['step']['failure'], failure, 'first_error_mismatch')
        if failure:
            if self.caller is not None and self.caller != failure['code']:
                self.bad('error_and_cleanup', 'first_error_mismatch')
            self.compare('error_and_cleanup', h['step']['stage'], failure['stage'], 'first_error_mismatch')
            if failure['code'] == 'operator_virtual_one_action_runtime_rejected' and groups['receipt']:
                if groups['receipt'][0]['payload']['result']['status'] in {'ok', 'pending'}:
                    self.bad('error_and_cleanup', 'first_error_mismatch')
        elif self.caller is not None:
            self.bad('error_and_cleanup', 'first_error_mismatch')
        if report and h['step']['harness']:
            self.compare('error_and_cleanup', h['step']['harness'], dict(termination=report['termination'],
                unresolved_request_ids=report['unresolved_request_ids'], legacy_ai_model_called=False), 'host_summary_mismatch')
        if (h['cleanup']['remote_cancel_verified'] is not False or h['cancellation']['remote_cancel_verified'] is not False
                or h['cleanup']['virtual_outputs_disabled'] is not None):
            self.bad('error_and_cleanup', 'host_summary_mismatch')
        if self.complete and report:
            if h['cleanup']['terminal_report_observed'] is not True:
                self.bad('error_and_cleanup', 'host_summary_mismatch')
            self.good('error_and_cleanup')
        else:
            self.lack()

    def result(self):
        self.protocol()
        if not self.unsupported:
            self.inputs()
            self.observations()
            self.wire_scope()
            self.artifacts()
            self.graph()
            self.errors({kind: [e for e in self.events or [] if e['type'] == kind] for kind in _EVENT_TYPES})
        if self.unsupported:
            status, verdict = 'unsupported', None
            self.reasons.add('unsupported_protocol')
        elif 'contradicted' in self.checks.values():
            status, verdict = 'assessed', 'contradictory'
        elif self.missing or 'unverified' in self.checks.values():
            status, verdict = 'inconclusive', 'insufficient'
            self.reasons.add('evidence_missing')
        else:
            status, verdict = 'assessed', 'consistent'
        if verdict != 'consistent':
            self.effect = self.command = 'unknown'
        if self.h is None and self.caller is not None:
            self.reasons.add('caller_refusal_only')
        refs = ['component:' + key for key in _PACKET if self.p[key] is not None]
        if self.caller is not None:
            refs.append('component:caller_error_code')
        refs += [e['event_id'] for e in self.events or [] if e['event_id'] not in refs]
        verification = dict.fromkeys(_VERIFY, False)
        verification.update(input_values_unchanged=True, supplied_graph_consistent=verdict == 'consistent')
        return dict(schema_version=1, kind='codex_one_action_effect_assessment', status=status, verdict=verdict,
            bindings=dict(operator_binding=self.binding, input_sha256=_H(_C(dict(schema_version=1,
                kind='codex_one_action_assessment_inputs', components=self.components))), components=self.components),
            observed_effect=self.effect, command_outcome=self.command, first_error=self.first,
            task_assessment=dict(status='not_evaluated', verdict=None, score=None, evaluator_called=False),
            checks=self.checks, evidence_refs=list(dict.fromkeys(refs))[:32], verification=verification,
            reason_codes=[r for r in _REASONS if r in self.reasons], limits=dict(_LIMITS))


def assess_codex_one_action_effects(packet: dict, *, caller_error_code: str | None = None) -> dict:
    """Return detached effect/command evidence; None denotes explicitly missing data."""
    code = None
    try:
        saved, before = _snapshot(packet, caller_error_code)
        _shapes(saved)
        result = _Assessment(saved, caller_error_code, before).result()
        try:
            _, after = _snapshot(packet, caller_error_code)
        except _CONTROL:
            raise
        except Exception:
            _fail('internal_error')
        if before != after:
            _fail('internal_error')
        raw = _C(result)
        if len(raw) > _LIMITS['max_output_bytes']:
            _fail('limit_exceeded')
        return json.loads(raw)
    except _CONTROL:
        raise
    except _Fault as error:
        code = error.code
    except Exception:
        code = 'internal_error'
    _fixed(code)
