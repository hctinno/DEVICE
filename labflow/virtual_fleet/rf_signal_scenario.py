"""Seven authored RF scenarios on the existing genuine Fleet, never hardware.

The operator sees public observations. A separate evaluator checks stored
evidence against literal synthetic expectations, before the publication gate.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from . import catalog as catalog_api, integration, journal, policies
from .harness import FleetHarness


_PREFIX = 'rf_signal_scenario_'
_CODES = frozenset(_PREFIX + x for x in (
    'invalid_request', 'unsupported_catalog', 'output_unavailable',
    'execution_incomplete', 'evidence_invalid', 'evidence_unavailable'))
_CATALOG_SHA = '6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff'
_ENGINE_SHA = '7816f87dcf8aa648d628935493f74dee3a54f993ba2bae87f9a1e102a8b4ccab'
_PARENTS = (
    '__init__.py', '__main__.py', 'catalog.py', 'core.py', 'evaluation.py',
    'facility.py', 'frequency_psd.py', 'frequency_psd_max.py',
    'frequency_source.py', 'harness.py', 'harness_check.py', 'instruments.py',
    'integration.py', 'journal.py', 'method_adapter.py', 'policies.py', 'rf.py',
    'spectrum_capture.py', 'spectrum_math.py')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_FLAGS = {
    'data_origin': 'authored_synthetic', 'execution_mode': 'synthetic_virtual_execution',
    'synthetic': True, 'hardware_verified': False, 'physical_verified': False,
    'ai_model_called': False, 'normative_compliance_verified': False,
    'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
    'waveform_implemented': False}
_BUDGETS = dict(decisions=64, logical_requests=64, ticks=32, wall_seconds=30,
                transport_retries=2)
_REPORT_KEYS = set('schema_version kind run_id runtime_instance_id synthetic hardware_verified '
                   'ai_model_called policy termination task_outcome cleanup usage evidence '
                   'unresolved_request_ids assessment'.split())
_ASSESSMENT_KEYS = set('status verdict evaluator_id evidence_refs summary_code'.split())
_AUTHOR_KEYS = set('schema_version kind scenario_id seed phases initial_context provenance oracle'.split())
_PROVENANCE_KEYS = set('runtime_origin catalog_sha256 topology_sha256 engine_sha256'.split())
_MANIFEST_KEYS = set('schema_version kind complete request catalog_sha256 topology_sha256 engine_sha256 files'.split())
_ARTIFACT_KEYS = set('path bytes sha256 visibility'.split())
_SELECTION = {
    'supply': ('power_supply', 'E3632A'), 'environment': ('temperature_chamber', 'SU-642'),
    'dut': ('dut', 'SM-A176U'), 'attenuator': ('attenuator', '8493C'),
    'switch_controller': ('rf_switch', 'FBSM-01B'), 'switch': ('rf_switch', 'OSP 120'),
    'coupler': ('coupler', '87300B'), 'sensor': ('power_sensor', 'N1921A'),
    'meter': ('power_meter', 'N1911A'), 'analyzer': ('signal_analyzer', 'N9030A'),
    'software': ('test_software', 'FCC WLAN Conducted')}
_LINKS = (
    ('supply', 'power', 'environment', 'power', 'power'),
    ('supply', 'power', 'dut', 'power', 'power'),
    ('supply', 'power', 'meter', 'power', 'power'),
    ('supply', 'power', 'analyzer', 'power', 'power'),
    ('environment', 'environment', 'dut', 'environment', 'environment'),
    ('dut', 'rf', 'attenuator', 'rf', 'rf'),
    ('attenuator', 'rf', 'switch', 'rf_1', 'rf'),
    ('switch_controller', 'control', 'switch', 'control', 'control'),
    ('switch', 'rf', 'coupler', 'rf', 'rf'),
    ('coupler', 'rf', 'analyzer', 'rf', 'rf'),
    ('coupler', 'coupled', 'sensor', 'rf', 'rf'),
    ('sensor', 'measurement', 'meter', 'sensor', 'measurement'),
    ('meter', 'measurement', 'software', 'measurement', 'measurement'))
_SCENARIO_ROWS = {
    'pulsed_on_mean': (2450000000.0, .25, 3.0, 'OFDM', True, 2450000000.0, 'on_average'),
    'pulsed_time_mean': (2450000000.0, .25, 3.0, 'OFDM', True, 2450000000.0, 'time_average'),
    'pulsed_peak': (2450000000.0, .25, 3.0, 'OFDM', True, 2450000000.0, 'peak'),
    'cw_peak': (2450000000.0, 1.0, 0.0, 'CW', True, 2450000000.0, 'peak'),
    'shifted_frequency': (2460000000.0, .25, 3.0, 'OFDM', True, 2460000000.0, 'on_average'),
    'sensor_uncalibrated': (2450000000.0, .25, 3.0, 'OFDM', False, 2450000000.0, 'on_average'),
    'meter_frequency_conflict': (2450000000.0, .25, 3.0, 'OFDM', True, 2460000000.0, 'on_average')}
# Independently fixed expectations, never computed by the RF engine/evaluator.
_ORACLE_ROWS = {
    'pulsed_on_mean': ('measured', None, -18.0, -18.0, 'on_average'),
    'pulsed_time_mean': ('measured', None, -18.0, -24.020599913279625, 'time_average'),
    'pulsed_peak': ('measured', None, -18.0, -15.0, 'peak'),
    'cw_peak': ('measured', None, -18.0, -18.0, 'peak'),
    'shifted_frequency': ('measured', None, -18.0, -18.0, 'on_average'),
    'sensor_uncalibrated': ('sensor_blocked', 'calibration_unavailable', None, None, None),
    'meter_frequency_conflict': ('meter_blocked', 'sensor_frequency_setting_conflict', -18.0, None, None)}


class RfSignalScenarioError(ValueError):
    """Only a fixed, sanitized code crosses the host boundary."""
    def __init__(self, code):
        self.code = code if code in _CODES else _PREFIX + 'evidence_invalid'
        super().__init__(self.code)


def _error(suffix):
    return RfSignalScenarioError(_PREFIX + suffix)


def _require(condition):
    if not condition:
        raise _error('evidence_invalid')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _snapshot(value, *, limit, depth, nodes, string_limit=16384):
    """Bound before serialization; preserve plain JSON native types and arrays."""
    remaining = nodes
    def walk(item, level):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or level > depth:
            raise ValueError('budget')
        if type(item) is dict:
            result = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError('key')
                remaining -= 1
                if remaining < 0 or len(key) > string_limit:
                    raise ValueError('key budget')
                key.encode('utf-8')
                result[key] = walk(child, level + 1)
            return result
        if type(item) is list:
            return [walk(child, level + 1) for child in item]
        if type(item) is str:
            if len(item) > string_limit:
                raise ValueError('string budget')
            item.encode('utf-8')
            return item
        if item is None or type(item) is bool:
            return item
        if type(item) is int and item.bit_length() <= 4096:
            return item
        if type(item) is float and math.isfinite(item):
            return item
        raise ValueError('plain finite JSON')
    copied = walk(value, 0)
    if len(_canonical(copied)) > limit:
        raise ValueError('bytes')
    return copied


def _request(value):
    try:
        req = _snapshot(value, limit=1024, depth=4, nodes=32)
        if (type(req) is not dict or set(req) != {'schema_version', 'scenario_id', 'seed'}
                or type(req['schema_version']) is not int or req['schema_version'] != 1
                or type(req['scenario_id']) is not str or req['scenario_id'] not in _SCENARIO_ROWS
                or type(req['seed']) is not int or not 0 <= req['seed'] <= 2147483647):
            raise ValueError('request')
        return req
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError):
        raise _error('invalid_request') from None


def _catalog(value):
    try:
        data = _snapshot(value, limit=1048576, depth=8, nodes=8192, string_limit=1024)
        data = catalog_api.validate_catalog(data)
        if _sha(_canonical(data)) != _CATALOG_SHA:
            raise ValueError('catalog fingerprint')
        return data
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        raise _error('unsupported_catalog') from None


def describe_rf_signal_scenario(scenario_id):
    if type(scenario_id) is not str or scenario_id not in _SCENARIO_ROWS:
        raise _error('invalid_request') from None
    frequency, duty, crest, modulation, calibration, meter_hz, mode = _SCENARIO_ROWS[scenario_id]
    return {
        'source_signal': {'frequency_hz': frequency, 'power_dbm': 12.5,
                          'bandwidth_hz': 20000000.0, 'duty_cycle': duty,
                          'crest_factor_db': crest, 'modulation': modulation},
        'sensor': {'calibration_valid': calibration, 'acquisition_policy': 'triggered'},
        'meter': {'frequency_hz': meter_hz, 'measurement_mode': mode, 'unit': 'dBm'},
        'reference_plane': 'sensor_input', 'basis': 'declared_synthetic_policy'}


def _oracle(scenario_id):
    outcome, reason, sensor, meter, quantity = _ORACLE_ROWS[scenario_id]
    return dict(expected_outcome=outcome, expected_reason=reason, sensor_dbm=sensor,
                meter_dbm=meter, meter_quantity=quantity, tolerance_db=1e-9)


def _engine():
    digest = hashlib.sha256()
    for name in _PARENTS:
        data = (Path(__file__).parent / name).read_bytes().replace(b'\r\n', b'\n')
        digest.update(name.encode('utf-8') + b'\0' + data + b'\0')
    _require(digest.hexdigest() == _ENGINE_SHA)
    return digest.hexdigest()


def _topology_witness(catalog):
    """Static expected public wiring, for validation only, no device construction."""
    nodes, used = [], set()
    for identity, (role, model) in _SELECTION.items():
        matches = sorted((p for p in catalog['profiles'] if p['role'] == role and p['model'] == model),
                         key=lambda p: p['profile_id'])
        _require(bool(matches))
        profile_id = matches[0]['profile_id']
        nodes.append({'id': identity, 'profile_id': profile_id})
        used.add(profile_id)
    nodes.extend({'id': 'inventory:' + p['profile_id'], 'profile_id': p['profile_id']}
                 for p in catalog['profiles'] if p['profile_id'] not in used)
    return {'devices': nodes, 'connections': [
        {'source': {'device_id': src, 'port': out}, 'target': {'device_id': dst, 'port': port},
         'kind': kind} for src, out, dst, port, kind in _LINKS]}


def _assessment(status='not_assessed', verdict=None, code=None, refs=()):
    return dict(status=status, verdict=verdict,
                evaluator_id=None if status == 'not_assessed' else 'rf_signal_scenario_v1',
                evidence_refs=list(dict.fromkeys(refs)), summary_code=code)


def _record(scenario_id, status, *, declared=None, report=None, assessment=None,
            artifacts=(), error=None):
    value = dict(schema_version=1, kind='virtual_rf_signal_scenario', scenario_id=scenario_id,
                 status=status, declared_setup=declared, report=report,
                 assessment=assessment if assessment is not None else _assessment(),
                 artifacts=list(artifacts), error_code=error, verification=dict(_FLAGS))
    return _snapshot(value, limit=327680, depth=20, nodes=16384)


def _write_new(path, value, *, limit):
    data = _canonical(value) + b'\n'
    _require(len(data) <= limit)
    with path.open('xb') as stream:
        if stream.write(data) != len(data):
            raise OSError('short evidence write')
        stream.flush()


def _read_bytes(path, limit):
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    _require(len(data) <= limit)
    return data


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _read_json(path, limit):
    raw = _read_bytes(path, limit)
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
        return _snapshot(value, limit=limit, depth=24, nodes=100000)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise _error('evidence_invalid') from None


def _artifact(output, relative, visibility='operator'):
    limit = {'public-result.json': 327680, 'private/author.json': 1048576,
             'operator/events.jsonl': 33554432}[relative]
    data = _read_bytes(output / relative, limit)
    return dict(path=relative, bytes=len(data), sha256=_sha(data), visibility=visibility)


def _execute(device, action):
    return dict(kind='execute', device_id=device, action=action, parameters={})


class _MeterPolicy:
    """Continue the public sensor policy in the same harness, with no oracle."""
    policy_id = 'rf_signal_scenario_v1'

    def __init__(self):
        self._sensor = policies.RFSensorFixturePolicy()
        self._phase = 'sensor'

    def __call__(self, context):
        if self._phase == 'sensor':
            child = self._sensor(context)
            if child.get('kind') != 'stop' or child.get('claim') != 'completed':
                return child
            self._phase = 'meter'
            return _execute('meter', 'acquire')
        node = context['observations']['devices']['meter']
        if node['status'] in {'invalid', 'unsupported', 'error', 'disconnected'}:
            return dict(kind='stop', claim='blocked', reason='meter_not_ready')
        sample = node['values']['outputs'].get('measurement')
        if sample is None or node['status'] == 'pending':
            return dict(kind='advance', ticks=1)
        if self._phase == 'meter':
            self._phase = 'fetch'
            return _execute('meter', 'fetch')
        last = context['last_receipt']
        if (last is None or last.get('device_id') != 'meter' or last.get('status') != 'ok'
                or sample.get('valid') is not True):
            return dict(kind='stop', claim='blocked', reason='meter_not_ready')
        return dict(kind='stop', claim='completed', reason='fresh_meter_observed')


def _natural(value):
    return type(value) is int and value >= 0


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _keys(value, fields):
    _require(type(value) is dict and set(value) == set(fields))


def _same(left, right):
    _require(_canonical(left) == _canonical(right))


def _validate_report(report):
    value = _snapshot(report, limit=262144, depth=16, nodes=8192)
    _keys(value, _REPORT_KEYS)
    _same({k: value[k] for k in ('schema_version', 'kind', 'synthetic', 'hardware_verified',
                                'ai_model_called', 'task_outcome')},
          dict(schema_version=1, kind='virtual_fleet_harness_result', synthetic=True,
               hardware_verified=False, ai_model_called=False, task_outcome='not_assessed'))
    for key in ('run_id', 'runtime_instance_id'):
        _require(type(value[key]) is str and _ID.fullmatch(value[key]) is not None)
    _same(value['policy'], {'kind': 'fixture', 'id': 'rf_signal_scenario_v1'})
    _keys(value['termination'], ('reason', 'policy_claim'))
    _require(value['termination']['reason'] in {
        'policy_stop', 'supervisor_stop', 'decision_budget', 'request_budget', 'tick_budget',
        'wall_deadline', 'policy_error', 'invalid_proposal', 'runtime_error',
        'runtime_mutation_uncertain', 'evidence_error'})
    _require(value['termination']['policy_claim'] in {None, 'completed', 'blocked', 'failed', 'unsupported'})
    _same(value['cleanup'], {'status': 'not_assessed', 'evidence_refs': []})
    _same(value['assessment'], _assessment())
    _keys(value['evidence'], ('measurement_refs', 'operator_transcript_ref'))
    _require(type(value['evidence']['measurement_refs']) is list)
    _require(value['evidence']['operator_transcript_ref'] == 'artifact:operator_events')
    _keys(value['usage'], ('decisions', 'logical_requests', 'transport_retries',
                           'tick_delta', 'reserved_ticks', 'elapsed_ms'))
    for key, number in value['usage'].items():
        _require(_finite(number) and number >= 0 if key == 'elapsed_ms' else _natural(number))
    _require(value['usage']['decisions'] <= 64 and value['usage']['logical_requests'] <= 64
             and value['usage']['tick_delta'] <= 32 and value['usage']['transport_retries'] <= 2)
    unresolved = value['unresolved_request_ids']
    _require(type(unresolved) is list and all(type(x) is str and _ID.fullmatch(x) for x in unresolved)
             and len(set(unresolved)) == len(unresolved))
    return value


def _binding(catalog):
    topology = _topology_witness(catalog)
    profiles = {p['profile_id']: p for p in catalog['profiles']}
    identities = {node['id']: profiles[node['profile_id']] for node in topology['devices']}
    return topology, identities


def _envelope(value, *, tick=None, revision=None, identity=None, identities=None):
    _require(type(value) is dict and value.get('synthetic') is True
             and value.get('hardware_verified') is False
             and _natural(value.get('tick')) and _natural(value.get('setup_revision'))
             and value.get('status') in {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}
             and type(value.get('values')) is dict)
    if tick is not None:
        _require(value['tick'] == tick and value['setup_revision'] == revision)
    if identity is not None:
        profile = identities[identity]
        _require(value.get('device_id') == identity and value.get('profile_id') == profile['profile_id']
                 and value.get('role') == profile['role'])
    outputs = value['values'].get('outputs', {})
    _require(type(outputs) is dict and all(type(v) is dict for v in outputs.values()))


def _meter_context(values, meter, revision=None):
    """Bind the declared meter settings to its public configuration context."""
    configuration = values.get('configuration')
    expected = dict(meter, trigger_source='immediate', window=1)
    _same(configuration, expected)
    current = values.get('configuration_revision')
    _require(_natural(current) and (revision is None or current == revision))
    return current


def _setup_receipt_accepted(receipt, index, declared):
    values = receipt['values']
    if index == 3:
        try:
            _meter_context(values, declared['meter'])
        except RfSignalScenarioError:
            return False
    elif values.get('configured') is not True:
        return False
    if receipt['status'] in {'ok', 'pending'}:
        return True
    # Same meter configuration preserves the old invalidated acquisition state.
    # This is configuration evidence only, never an accepted measurement.
    if (index == 3 and receipt.get('device_id') == 'meter' and receipt['status'] == 'invalid'
            and receipt.get('setup_changed') is False
            and values.get('reason') == 'configuration_changed' and values.get('outputs') == {}):
        configuration = values.get('configuration')
        return (type(configuration) is dict and all(
            _canonical(configuration.get(key)) == _canonical(value)
            for key, value in declared['meter'].items()))
    return False


def _validate_author(author, request, provenance, identities):
    _keys(author, _AUTHOR_KEYS)
    _same({k: author[k] for k in ('schema_version', 'kind', 'scenario_id', 'seed')},
          dict(schema_version=1, kind='private_rf_signal_scenario_author',
               scenario_id=request['scenario_id'], seed=request['seed']))
    _same(author['oracle'], _oracle(request['scenario_id']))
    _same(author['provenance'], provenance)
    _keys(author['phases'], ('bootstrap', 'scenario_setup'))
    bootstrap, setup = author['phases']['bootstrap'], author['phases']['scenario_setup']
    _require(type(bootstrap) is list and len(bootstrap) == 23
             and type(setup) is list and len(setup) == 4)
    bootstrap_nodes = ('supply', 'supply', 'supply', 'environment', 'environment', 'dut',
                       'attenuator', 'switch_controller', 'switch_controller', 'switch',
                       'switch', 'coupler', 'sensor', 'meter', 'analyzer', None,
                       'dut', None, 'meter', 'analyzer', None, 'meter', 'analyzer')
    previous = (0, 0)
    declared = describe_rf_signal_scenario(request['scenario_id'])
    for index, (receipt, identity) in enumerate(zip(
            bootstrap + setup, bootstrap_nodes + ('dut', 'dut', 'sensor', 'meter'))):
        _envelope(receipt, identity=identity, identities=identities)
        _require(receipt['status'] in {'ok', 'pending'} if index < 23
                 else _setup_receipt_accepted(receipt, index - 23, declared))
        clock = (receipt['tick'], receipt['setup_revision'])
        _require(all(a >= b for a, b in zip(clock, previous)))
        previous = clock
    _keys(author['initial_context'], ('tick', 'setup_revision'))
    _same(author['initial_context'], dict(tick=setup[-1]['tick'],
                                         setup_revision=setup[-1]['setup_revision']))
    bootstrap_meter = bootstrap[13]['values']
    old_revision = _meter_context(
        bootstrap_meter, describe_rf_signal_scenario('pulsed_time_mean')['meter'])
    for receipt, identity in zip(bootstrap, bootstrap_nodes):
        if identity == 'meter':
            _meter_context(receipt['values'], describe_rf_signal_scenario('pulsed_time_mean')['meter'],
                           old_revision)
            sample = receipt['values']['outputs'].get('measurement')
            if sample is not None:
                _require(sample.get('configuration_revision') == old_revision)
    changed = setup[-1].get('setup_changed')
    _require(type(changed) is bool)
    _require(changed == (_canonical(bootstrap_meter['configuration']) !=
                         _canonical(setup[-1]['values']['configuration'])))
    _meter_context(setup[-1]['values'], declared['meter'], old_revision + int(changed))
    return author['initial_context']


def _rf_packet(packet, declared, identity, *, power):
    _keys(packet, set(declared) | {'status', 'valid', 'source_id'})
    _require(packet['status'] == 'ok' and packet['valid'] is True
             and packet['source_id'] == identity)
    for key, value in declared.items():
        _require(_finite(packet[key]) if key != 'modulation' else type(packet[key]) is str)
        if key != 'power_dbm':
            _require(packet[key] == value)
    _require(_finite(packet['power_dbm']))
    return abs(packet['power_dbm'] - power) <= 1e-9


def _sensor_packet(sample, declared, observed, acquisition, initial):
    _keys(sample, ('status', 'valid', 'value', 'unit', 'frequency_hz', 'power_dbm',
                   'duty_cycle', 'crest_factor_db', 'acquisition_tick',
                   'acquisition_setup_revision', 'source_id'))
    _require(sample['status'] == 'ok' and sample['valid'] is True
             and sample['unit'] == 'dBm' and sample['source_id'] == 'sensor')
    for key in ('value', 'power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db'):
        _require(_finite(sample[key]))
    _require(sample['value'] == sample['power_dbm'])
    for key in ('frequency_hz', 'duty_cycle', 'crest_factor_db'):
        _require(sample[key] == declared[key])
    _require(_natural(sample['acquisition_tick']) and acquisition is not None
             and acquisition['tick'] < sample['acquisition_tick'] <= observed['tick']
             and sample['acquisition_tick'] > initial['tick']
             and sample['acquisition_setup_revision'] == observed['setup_revision']
             and acquisition['setup_revision'] == observed['setup_revision'])
    return abs(sample['value'] - (-18.0)) <= 1e-9


def _meter_packet(sample, declared, observed, sensor, acquisition):
    _keys(sample, ('status', 'valid', 'source_id', 'input_source_id', 'acquisition_tick',
                   'acquisition_setup_revision', 'configuration_revision', 'simulation_basis',
                   'value', 'unit', 'quantity', 'frequency_hz', 'duty_cycle', 'crest_factor_db', 'window'))
    _require(sample['status'] == 'ok' and sample['valid'] is True
             and sample['source_id'] == 'meter' and sample['input_source_id'] == 'sensor'
             and sample['unit'] == 'dBm' and sample['quantity'] == declared['meter']['measurement_mode']
             and sample['simulation_basis'] == 'declared_synthetic_policy' and sample['window'] == 1)
    _require(_natural(sample['configuration_revision']) and _finite(sample['value']))
    _require(sample['configuration_revision'] ==
             observed['devices']['meter']['values']['configuration_revision'])
    for key in ('frequency_hz', 'duty_cycle', 'crest_factor_db'):
        _require(sample[key] == sensor[key])
    _require(_natural(sample['acquisition_tick']) and acquisition is not None
             and max(acquisition['tick'], sensor['acquisition_tick']) < sample['acquisition_tick'] <= observed['tick']
             and sample['acquisition_setup_revision'] == observed['setup_revision']
             and acquisition['setup_revision'] == observed['setup_revision']
             and sample['configuration_revision'] == acquisition['values']['configuration_revision']
             and sample['frequency_hz'] == declared['meter']['frequency_hz'])


def _evaluate_events(request, declared, report, stored, author, catalog):
    topology, identities = _binding(catalog)
    provenance = dict(runtime_origin='preinitialized', catalog_sha256=_CATALOG_SHA,
                      topology_sha256=_sha(_canonical(topology)), engine_sha256=_engine())
    initial = _validate_author(author, request, provenance, identities)
    meter_revision = author['phases']['scenario_setup'][-1]['values']['configuration_revision']
    _same(stored['header']['provenance'], provenance)
    _require(stored['complete'] is True and stored['unresolved_request_ids'] == []
             and report['unresolved_request_ids'] == [] and report['usage']['reserved_ticks'] == 0
             and stored['header']['run_id'] == report['run_id']
             and stored['header']['runtime_instance_id'] == report['runtime_instance_id'])
    events = stored['events']
    _require(bool(events))
    intents, receipted, caused = {}, {}, set()
    acquisitions, reads = {}, {}
    last, last_event, proposal = None, None, None
    decisions = retries = 0
    match = True
    for event in events:
        kind, payload = event['type'], event['payload']
        if kind == 'policy_decision':
            decisions += 1
            proposal = payload['proposal']
        elif kind == 'intent':
            _require(last is not None)
            rid, operation, body = payload['request_id'], payload['operation'], payload['body']
            _require(rid not in intents and payload['logical_request'] == len(intents) + 1)
            expected_proposal = dict(kind=operation, **body)
            _same(proposal, expected_proposal)
            if operation == 'execute':
                _require(body['device_id'] in {'dut', 'sensor', 'meter'}
                         and body['action'] in {'start', 'acquire', 'read', 'fetch'}
                         and body['parameters'] == {})
                _require((body['device_id'], body['action']) in {
                    ('dut', 'start'), ('sensor', 'acquire'), ('sensor', 'read'),
                    ('meter', 'acquire'), ('meter', 'fetch')})
            intents[rid] = dict(payload, before_tick=last['tick'], before_revision=last['setup_revision'])
        elif kind == 'receipt':
            rid, receipt = payload['request_id'], payload['result']
            _require(rid in intents and rid not in receipted)
            intent = intents[rid]
            body = intent['body']
            identity = body.get('device_id')
            _envelope(receipt, identity=identity, identities=identities)
            if identity == 'meter':
                _meter_context(receipt['values'], declared['meter'], meter_revision)
            elif identity in {'dut', 'sensor'}:
                _require(receipt['values'].get('configured') is True)
            changed = receipt.get('setup_changed', False)
            _require(type(changed) is bool)
            _require(receipt['setup_revision'] == intent['before_revision'] + int(changed))
            _require(receipt['tick'] == intent['before_tick'] + int(intent['operation'] == 'advance'))
            if identity is None:
                _require(receipt['status'] == 'ok' and receipt['values'].get('advanced_ticks') == 1)
            elif receipt['status'] in {'ok', 'pending'}:
                if body['action'] == 'acquire':
                    _require(identity not in acquisitions)
                    acquisitions[identity] = receipt
                elif body['action'] in {'read', 'fetch'}:
                    _require(identity in acquisitions)
                    reads[identity] = receipt
            receipted[rid] = receipt
        elif kind == 'transport_retry':
            retries += 1
        elif kind == 'observation':
            observed = payload['observation']
            _keys(observed, ('tick', 'setup_revision', 'synthetic', 'hardware_verified', 'devices'))
            _require(_natural(observed['tick']) and _natural(observed['setup_revision'])
                     and observed['synthetic'] is True and observed['hardware_verified'] is False)
            _require(set(observed['devices']) == set(identities))
            for identity, node in observed['devices'].items():
                _envelope(node, tick=observed['tick'], revision=observed['setup_revision'],
                          identity=identity, identities=identities)
                if identity == 'meter':
                    _meter_context(node['values'], declared['meter'], meter_revision)
                elif identity in {'dut', 'sensor'}:
                    _require(node['values'].get('configured') is True)
            if last is None:
                _same(dict(tick=observed['tick'], setup_revision=observed['setup_revision']), initial)
                _require('cause_request_id' not in payload)
            else:
                rid = payload.get('cause_request_id')
                _require(rid in receipted and rid not in caused
                         and observed['tick'] == receipted[rid]['tick']
                         and observed['setup_revision'] == receipted[rid]['setup_revision'])
                caused.add(rid)
                _require(observed['tick'] >= last['tick']
                         and observed['setup_revision'] >= last['setup_revision'])
                body = intents[rid]['body']
                if intents[rid]['operation'] == 'execute' and body['action'] in {'read', 'fetch'}:
                    _same(receipted[rid]['values']['outputs'],
                          observed['devices'][body['device_id']]['values']['outputs'])
            devices = observed['devices']
            for identity, port, expected_power in (('dut', 'rf', 12.5), ('coupler', 'coupled', -18.0)):
                packet = devices[identity]['values']['outputs'].get(port)
                if packet is not None:
                    _require(devices[identity]['status'] == 'ok')
                    match &= _rf_packet(packet, declared['source_signal'], identity, power=expected_power)
            sensor = devices['sensor']['values']['outputs'].get('measurement')
            if sensor is not None:
                _require(devices['sensor']['status'] == 'ok')
                match &= _sensor_packet(sensor, declared['source_signal'], observed,
                                        acquisitions.get('sensor'), initial)
                coupled = devices['coupler']['values']['outputs'].get('coupled')
                _require(coupled is not None and sensor['value'] == coupled['power_dbm'])
            meter = devices['meter']['values']['outputs'].get('measurement')
            if meter is not None:
                _require(devices['meter']['status'] == 'ok')
                _require(sensor is not None)
                _meter_packet(meter, declared, observed, sensor, acquisitions.get('meter'))
            last, last_event = observed, event['event_id']
        elif kind == 'error':
            raise _error('evidence_invalid')
    _require(last is not None and set(intents) == set(receipted) == caused)
    _require(report['usage']['logical_requests'] == len(intents)
             and report['usage']['decisions'] == decisions
             and report['usage']['transport_retries'] == retries
             and report['usage']['tick_delta'] == last['tick'] - initial['tick'])
    _require(type(proposal) is dict and proposal.get('kind') == 'stop'
             and report['termination']['reason'] == 'policy_stop'
             and report['termination']['policy_claim'] == proposal.get('claim'))
    event_ids = {e['event_id'] for e in events if e['type'] == 'observation'}
    _require(set(report['evidence']['measurement_refs']) <= event_ids)
    final = last['devices']
    sensor = final['sensor']['values']['outputs'].get('measurement')
    meter = final['meter']['values']['outputs'].get('measurement')
    _require(final['dut']['status'] == final['coupler']['status'] == 'ok'
             and final['dut']['values']['outputs'].get('rf') is not None
             and final['coupler']['values']['outputs'].get('coupled') is not None)
    oracle = _oracle(request['scenario_id'])
    if oracle['expected_outcome'] == 'sensor_blocked':
        good = (report['termination']['policy_claim'] == 'blocked' and sensor is None and meter is None
                and 'sensor' not in acquisitions and 'meter' not in acquisitions
                and final['sensor']['values'].get('reason') == 'calibration_unavailable'
                and proposal.get('reason') == 'sensor_not_ready')
        code = 'expected_sensor_blocked'
    elif oracle['expected_outcome'] == 'meter_blocked':
        bad_acquire = [receipted[rid] for rid, intent in intents.items()
                       if intent['operation'] == 'execute' and intent['body'] ==
                       dict(device_id='meter', action='acquire', parameters={})]
        good = (report['termination']['policy_claim'] == 'blocked' and sensor is not None and meter is None
                and 'sensor' in reads and 'meter' not in reads and len(bad_acquire) == 1
                and bad_acquire[0]['status'] == 'invalid'
                and bad_acquire[0]['values'].get('reason') == 'sensor_frequency_setting_conflict'
                and final['meter']['values'].get('reason') == 'sensor_frequency_setting_conflict')
        code = 'expected_meter_frequency_conflict'
    else:
        good = (report['termination']['policy_claim'] == 'completed'
                and sensor is not None and meter is not None
                and 'sensor' in reads and 'meter' in reads
                and reads['sensor']['tick'] >= sensor['acquisition_tick']
                and reads['meter']['tick'] >= meter['acquisition_tick']
                and final['sensor']['status'] == final['meter']['status'] == 'ok')
        if meter is not None:
            good &= abs(meter['value'] - oracle['meter_dbm']) <= 1e-9
        code = 'observed_signal_satisfied'
    passed = bool(good and match)
    return _assessment('completed', 'pass' if passed else 'fail',
                       code if passed else 'scenario_expectation_mismatch', [last_event])


def evaluate_rf_signal_scenario(request, declared_setup, report, output_dir):
    """Read actual evidence; never construct or call a virtual RF runtime."""
    try:
        req = _request(request)
        _same(declared_setup, describe_rf_signal_scenario(req['scenario_id']))
        valid_report = _validate_report(report)
        output = Path(output_dir)
        author = _read_json(output / 'private/author.json', 1048576)
        path = output / 'operator/events.jsonl'
        before = _read_bytes(path, 33554432)
        stored = journal.read_operator_journal(path)
        _require(before == _read_bytes(path, 33554432)
                 and stored['integrity']['file_sha256'] == _sha(before))
        raw_catalog = catalog_api.load_catalog(Path(__file__).resolve().parents[2] /
                                               'virtual_profiles/sm_a176u_unlicensed.json')
        catalog = _catalog(raw_catalog)
        return _evaluate_events(req, declared_setup, valid_report, stored, author, catalog)
    except (OSError, journal.JournalStorageError):
        raise _error('evidence_unavailable') from None
    except (RfSignalScenarioError, ValueError, TypeError, KeyError, IndexError,
            RecursionError, OverflowError, UnicodeError):
        return _assessment('failed', None, 'operator_evidence_invalid')


def _publication_gate(output, request, provenance, outer, rows):
    manifest = _read_json(output / 'private-manifest.json', 65536)
    _keys(manifest, _MANIFEST_KEYS)
    _same(manifest, dict(schema_version=1, kind='private_rf_signal_scenario_manifest',
                         complete=True, request=request,
                         catalog_sha256=provenance['catalog_sha256'],
                         topology_sha256=provenance['topology_sha256'],
                         engine_sha256=provenance['engine_sha256'], files=rows))
    _require(len(rows) == 3 and {r['path'] for r in rows} ==
             {'public-result.json', 'operator/events.jsonl', 'private/author.json'})
    for row in rows:
        _keys(row, _ARTIFACT_KEYS)
        _same(_artifact(output, row['path'], row['visibility']), row)
    _same(_read_json(output / 'public-result.json', 327680), outer)


def run_rf_signal_scenario(catalog, request, output_dir, *, run_id, runtime_instance_id):
    """Run one bounded, new synthetic attempt and preserve all failed evidence."""
    scenario_id = None
    try:
        req = _request(request)
        scenario_id = req['scenario_id']
        if any(type(x) is not str or _ID.fullmatch(x) is None for x in (run_id, runtime_instance_id)):
            scenario_id = None
            raise _error('invalid_request')
        valid_catalog = _catalog(catalog)
    except RfSignalScenarioError as error:
        return _record(scenario_id, 'rejected', error=error.code)
    try:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError, TypeError):
        return _record(scenario_id, 'rejected', error=_PREFIX + 'output_unavailable')
    declared = describe_rf_signal_scenario(scenario_id)
    report = None
    writer = None
    bootstrap, setup, initial = None, [], None
    provenance = dict(runtime_origin='preinitialized', catalog_sha256=_CATALOG_SHA,
                      topology_sha256=None, engine_sha256=None)
    author_attempted = False
    phase, dispatched = 'bootstrap', None
    failure_code = _PREFIX + 'execution_incomplete'
    try:
        engine = _engine()
        provenance['engine_sha256'] = engine
        provenance['topology_sha256'] = _sha(_canonical(_topology_witness(valid_catalog)))
        fleet, topology, bootstrap = integration.create_conducted_example(valid_catalog, seed=req['seed'])
        dispatched = True
        _same(topology, _topology_witness(valid_catalog))
        phase = 'setup'
        for i, (device, parameters, action) in enumerate((
                ('dut', {}, 'stop'), ('dut', declared['source_signal'], 'configure'),
                ('sensor', declared['sensor'], 'configure'), ('meter', declared['meter'], 'configure'))):
            receipt = fleet.execute('scenario:setup:' + str(i), device, action, deepcopy(parameters))
            setup.append(receipt)
            if not _setup_receipt_accepted(receipt, i, declared):
                raise _error('execution_incomplete')
        observed = fleet.observations()
        initial = dict(tick=observed['tick'], setup_revision=observed['setup_revision'])
        provenance = dict(runtime_origin='preinitialized', catalog_sha256=_CATALOG_SHA,
                          topology_sha256=_sha(_canonical(topology)), engine_sha256=engine)
        phase = 'harness'
        failure_code = _PREFIX + 'evidence_unavailable'
        (output / 'operator').mkdir()
        writer = journal.OperatorJournal(output / 'operator/events.jsonl', run_id=run_id,
                                         runtime_instance_id=runtime_instance_id, provenance=provenance)
        harness = FleetHarness(
            fleet, _MeterPolicy(), goal=dict(kind='acquire_fresh_rf_sensor', dut_id='dut',
                                             sensor_id='sensor', minimum_acquisition_tick=initial['tick'] + 1),
            catalog=valid_catalog, topology=topology, role_actions=fleet.role_actions,
            budgets=dict(_BUDGETS), event_sink=writer, run_id=run_id,
            runtime_instance_id=runtime_instance_id)
        failure_code = _PREFIX + 'execution_incomplete'
        report = _validate_report(harness.run())
        phase = 'journal_close'
        failure_code = _PREFIX + 'evidence_unavailable'
        closing, writer = writer, None
        closing.close()
        phase = 'artifact_write'
        (output / 'private').mkdir()
        author = dict(schema_version=1, kind='private_rf_signal_scenario_author',
                      scenario_id=scenario_id, seed=req['seed'],
                      phases=dict(bootstrap=bootstrap, scenario_setup=setup),
                      initial_context=initial, provenance=provenance, oracle=_oracle(scenario_id))
        author_attempted = True
        _write_new(output / 'private/author.json', author, limit=1048576)
        if (report['unresolved_request_ids'] or report['usage']['reserved_ticks']
                or report['termination']['reason'] != 'policy_stop'):
            phase = 'harness'
            raise _error('execution_incomplete')
        phase = 'evaluation'
        evaluated_rows = [_artifact(output, 'operator/events.jsonl'),
                          _artifact(output, 'private/author.json', 'evaluator_private')]
        assessment = evaluate_rf_signal_scenario(req, declared, report, output)
        if assessment['status'] != 'completed':
            raise _error('evidence_invalid')
        for row in evaluated_rows:
            _same(_artifact(output, row['path'], row['visibility']), row)
        phase = 'artifact_write'
        outer = _record(scenario_id, 'executed', declared=declared, report=report,
                        assessment=assessment, artifacts=[evaluated_rows[0]])
        _write_new(output / 'public-result.json', outer, limit=327680)
        rows = [_artifact(output, 'public-result.json'), *evaluated_rows]
        manifest = dict(schema_version=1, kind='private_rf_signal_scenario_manifest',
                        complete=True, request=req, catalog_sha256=_CATALOG_SHA,
                        topology_sha256=provenance['topology_sha256'], engine_sha256=engine, files=rows)
        _write_new(output / 'private-manifest.json', manifest, limit=65536)
        _publication_gate(output, req, provenance, outer, rows)
        return outer
    except RfSignalScenarioError as error:
        failure_code = error.code
    except OSError:
        if phase not in {'bootstrap', 'setup'}:
            failure_code = _PREFIX + 'evidence_unavailable'
    except Exception:
        pass
    finally:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
    if not author_attempted:
        # Keep known receipts on early failure. A failed writer is never retried.
        try:
            (output / 'private').mkdir(exist_ok=True)
            author_attempted = True
            _write_new(output / 'private/author.json',
                       dict(schema_version=1, kind='private_rf_signal_scenario_author',
                            scenario_id=scenario_id, seed=req['seed'],
                            phases=dict(bootstrap=bootstrap, scenario_setup=setup),
                            initial_context=initial, provenance=provenance, oracle=_oracle(scenario_id)),
                       limit=1048576)
        except Exception:
            pass
    failure = dict(schema_version=1, kind='rf_signal_scenario_failure', scenario_id=scenario_id,
                   error_code=failure_code, phase=phase, dispatched=dispatched)
    try:
        _write_new(output / 'failure.json', failure, limit=65536)
    except Exception:
        pass
    return _record(scenario_id, 'failed', declared=declared, report=report, error=failure_code)
