"""Bind a declared frequency fixture to a current scalar observation context."""

from copy import deepcopy
import hashlib
import json
import math
import re

from .spectrum_math import analyze_6db_bandwidth


_LIMIT = 4 * 1024 * 1024
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_CONTEXT = set('run_id runtime_instance_id source_id profile_id minimum_acquisition_tick'.split())
_CAPTURE = set('schema_version kind capture_id synthetic capture_origin run_id runtime_instance_id source_id '
               'profile_id acquisition_tick acquisition_setup_revision observation_event_id observation_sha256 '
               'trace_sha256 trace'.split())
_EVENT = set('schema_version kind event_id run_id runtime_instance_id sequence type payload'.split())
_OBSERVATION = set('tick setup_revision synthetic hardware_verified devices'.split())
_NODE = set('status values tick setup_revision synthetic hardware_verified device_id profile_id role'.split())
_STATUSES = {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}
_TRACE_FIXED = {'schema_version': 1, 'kind': 'synthetic_frequency_spectrum', 'synthetic': True,
                'axis_domain': 'frequency_offset_hz', 'sample_unit': 'dB',
                'amplitude_basis': 'relative_to_peak', 'selection_policy': 'unique_peak_single_lobe_linear_db'}
_TRACE = set(_TRACE_FIXED) | {'capture_id', 'frequency_offsets_hz', 'relative_levels_db'}
_BW = set('schema_version kind capture_id input_sha256 algorithm_id status reason_codes left_offset_hz '
          'right_offset_hz bandwidth_hz minimum_bandwidth_hz margin_hz conditional_comparison synthetic '
          'hardware_verified ai_model_called method_approval regulatory_scope_complete'.split())
_REASONS = ['non_unique_peak', 'disconnected_lobes', 'threshold_plateau',
            'left_crossing_missing', 'right_crossing_missing']
_FLAGS = {'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
          'method_approval': 'not_assessed', 'regulatory_scope_complete': False}


def _require(condition):
    if not condition:
        raise ValueError('invalid_bandwidth_capture')


def _keys(value, expected):
    _require(type(value) is dict and set(value) == expected)


def _fixed(value, expected):
    _require(type(value) is type(expected) and value == expected)


def _identifier(value):
    _require(type(value) is str and _ID.fullmatch(value) is not None)


def _natural(value):
    _require(type(value) is int and value >= 0)


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _snapshot(value):
    def walk(item, depth=0):
        _require(depth <= 32)
        if type(item) is dict:
            _require(all(type(key) is str for key in item))
            return {key: walk(child, depth + 1) for key, child in item.items()}
        if type(item) is list:
            return [walk(child, depth + 1) for child in item]
        if item is None or type(item) in (str, bool, int):
            return item
        _require(type(item) is float and math.isfinite(item))
        return item
    try:
        raw = _canonical(walk(value))
        _require(len(raw) <= _LIMIT)
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError('invalid_bandwidth_capture') from None


def _trace(trace, capture):
    _keys(trace, _TRACE)
    for key, expected in _TRACE_FIXED.items():
        _fixed(trace[key], expected)
    _identifier(trace['capture_id'])
    _require(trace['capture_id'] == capture['capture_id'])
    axis, levels = trace['frequency_offsets_hz'], trace['relative_levels_db']
    _require(type(axis) is list and type(levels) is list and 3 <= len(axis) <= 65536
             and len(axis) == len(levels) and all(_finite(value) for value in axis)
             and all(_finite(value) for value in levels)
             and all(left < right for left, right in zip(axis, axis[1:])) and max(levels) == 0)
    _require(_hash(trace) == capture['trace_sha256'])


def _observation(event, context):
    _keys(event, _EVENT)
    for key, expected in {'schema_version': 1, 'kind': 'operator_event', 'type': 'observation'}.items():
        _fixed(event[key], expected)
    _natural(event['sequence'])
    _require(event['sequence'] > 0 and event['event_id'] == 'event:' + str(event['sequence']))
    for key in ['event_id', 'run_id', 'runtime_instance_id']:
        _identifier(event[key])
    _require(event['run_id'] == context['run_id'] and event['runtime_instance_id'] == context['runtime_instance_id'])
    payload = event['payload']
    _require(type(payload) is dict and {'observation'} <= set(payload)
             and set(payload) <= {'observation', 'cause_request_id'})
    if 'cause_request_id' in payload:
        _identifier(payload['cause_request_id'])
    observation = payload['observation']
    _keys(observation, _OBSERVATION)
    _natural(observation['tick']); _natural(observation['setup_revision'])
    _fixed(observation['synthetic'], True); _fixed(observation['hardware_verified'], False)
    devices = observation['devices']
    _require(type(devices) is dict and context['source_id'] in devices)
    for identity, node in devices.items():
        _identifier(identity)
        _require(type(node) is dict and _NODE <= set(node) and set(node) <= _NODE | {'state', 'setup_changed'})
        _identifier(node['profile_id']); _identifier(node['role'])
        _require(node['device_id'] == identity and type(node['status']) is str and node['status'] in _STATUSES
                 and type(node['values']) is dict)
        _natural(node['tick']); _natural(node['setup_revision'])
        _require(node['tick'] == observation['tick'] and node['setup_revision'] == observation['setup_revision'])
        _fixed(node['synthetic'], True); _fixed(node['hardware_verified'], False)
    return observation, devices[context['source_id']]


def _measurement(node, observation, capture, context):
    _require(node['profile_id'] == context['profile_id'] and node['role'] == 'signal_analyzer' and node['status'] == 'ok')
    values = node['values']
    _fixed(values.get('operation_complete'), True)
    _natural(values.get('configuration_revision'))
    outputs = values.get('outputs')
    _require(type(outputs) is dict and type(outputs.get('measurement')) is dict)
    packet = outputs['measurement']
    _require(packet.get('status') == 'ok' and packet.get('valid') is True
             and packet.get('source_id') == context['source_id'] and packet.get('unit') == 'dBm'
             and type(packet.get('quantity')) is str and packet['quantity'] in {'on_average', 'peak'}
             and _finite(packet.get('value')))
    for field in ['acquisition_tick', 'acquisition_setup_revision', 'configuration_revision']:
        _natural(packet.get(field))
    _require(context['minimum_acquisition_tick'] <= packet['acquisition_tick'] <= observation['tick']
             and packet['acquisition_setup_revision'] == observation['setup_revision']
             and packet['configuration_revision'] == values['configuration_revision']
             and capture['acquisition_tick'] == packet['acquisition_tick']
             and capture['acquisition_setup_revision'] == packet['acquisition_setup_revision'])
    return packet


def _bandwidth_result(value, capture):
    result, _ = _snapshot(value)
    _keys(result, _BW)
    expected = {**_FLAGS, 'schema_version': 1, 'kind': 'synthetic_bandwidth_result',
                'algorithm_id': 'peak6_linear_db_v1', 'minimum_bandwidth_hz': 500000,
                'capture_id': capture['capture_id'], 'input_sha256': capture['trace_sha256']}
    for key, constant in expected.items():
        _fixed(result[key], constant)
    reasons = result['reason_codes']
    _require(type(reasons) is list and all(type(reason) is str and reason in _REASONS for reason in reasons)
             and reasons == [reason for reason in _REASONS if reason in reasons])
    numeric = ['left_offset_hz', 'right_offset_hz', 'bandwidth_hz', 'margin_hz']
    if result['status'] == 'complete':
        _require(not reasons and all(_finite(result[key]) for key in numeric)
                 and result['right_offset_hz'] > result['left_offset_hz'] and result['bandwidth_hz'] > 0
                 and type(result['conditional_comparison']) is str and result['conditional_comparison'] in {'meets', 'below'})
    else:
        _fixed(result['status'], 'incomplete')
        _require(bool(reasons) and all(result[key] is None for key in numeric + ['conditional_comparison']))
    return result


def analyze_current_bandwidth_capture(capture, current_event, *, context):
    """Validate current scalar context before one separate declared-trace calculation."""
    capture, capture_hash = _snapshot(capture)
    event, observation_hash = _snapshot(current_event)
    context, _ = _snapshot(context)
    _keys(context, _CONTEXT)
    for key in ['run_id', 'runtime_instance_id', 'source_id', 'profile_id']:
        _identifier(context[key])
    _natural(context['minimum_acquisition_tick'])
    _keys(capture, _CAPTURE)
    for key, expected in {'schema_version': 1, 'kind': 'synthetic_frequency_capture', 'synthetic': True,
                          'capture_origin': 'declared_frequency_fixture'}.items():
        _fixed(capture[key], expected)
    for key in ['capture_id', 'run_id', 'runtime_instance_id', 'source_id', 'profile_id', 'observation_event_id']:
        _identifier(capture[key])
    for key in ['run_id', 'runtime_instance_id', 'source_id', 'profile_id']:
        _require(capture[key] == context[key])
    for key in ['observation_sha256', 'trace_sha256']:
        _require(type(capture[key]) is str and _HASH.fullmatch(capture[key]) is not None)
    _natural(capture['acquisition_tick']); _natural(capture['acquisition_setup_revision'])
    observation, node = _observation(event, context)
    _require(capture['observation_event_id'] == event['event_id'] and capture['observation_sha256'] == observation_hash)
    packet = _measurement(node, observation, capture, context)
    _trace(capture['trace'], capture)
    try:
        calculated = analyze_6db_bandwidth(deepcopy(capture['trace']))
    except Exception as error:
        code = error.args[0] if type(error) is ValueError and len(error.args) == 1 else None
        safe = code if type(code) is str and code in {'invalid_spectrum_input', 'numeric_result_out_of_range'} else 'bandwidth_analysis_failed'
        raise ValueError(safe) from None
    try:
        bandwidth = _bandwidth_result(calculated, capture)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError('invalid_bandwidth_analysis') from None
    binding = {key: capture[key] for key in ['capture_id', 'run_id', 'runtime_instance_id', 'source_id', 'profile_id',
                                             'acquisition_tick', 'acquisition_setup_revision', 'observation_event_id',
                                             'observation_sha256', 'trace_sha256']}
    binding.update(role='signal_analyzer', configuration_revision=packet['configuration_revision'],
                   current_tick=observation['tick'], current_setup_revision=observation['setup_revision'],
                   capture_sha256=capture_hash, trace_origin='declared_frequency_fixture',
                   binding_scope='current_observation_context', rf_trace_observed=False)
    return {'schema_version': 1, 'kind': 'synthetic_bandwidth_capture_result',
            'binding': binding, 'bandwidth_result': bandwidth, **_FLAGS}
