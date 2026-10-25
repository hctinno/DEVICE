"""Authored RF fixtures and independent public-evidence grading, never hardware.

Only the host/evaluator receives SensorTrial. A policy receives detached public
JSON through FleetHarness, never this object, its seed, schedule or oracle.
"""
from copy import deepcopy
import json
import math
import re
import uuid

from .integration import create_conducted_example
from .core import STATUSES


CONDITIONS = ('normal', 'persistent_disconnect', 'restored_disconnect')
_BOUNDED = {'decision_budget', 'request_budget', 'tick_budget', 'wall_deadline'}
_EVENT_TYPES = {'policy_decision', 'intent', 'receipt', 'observation', 'transport_retry', 'error', 'termination'}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _natural(value):
    return type(value) is int and value >= 0


def _source_declaration(power_dbm, source_settings):
    if source_settings is None:
        return None
    if (type(source_settings) is not dict or any(type(key) is not str for key in source_settings)
            or 'power_dbm' not in source_settings):
        raise ValueError('Invalid synthetic source declaration')
    try:
        matches = (_number(power_dbm) and _number(source_settings['power_dbm'])
                   and power_dbm == source_settings['power_dbm'])
    except OverflowError:
        matches = False
    if not matches:
        raise ValueError('Synthetic source power must match finite power_dbm')
    # Full exact6/native/range validation belongs to the existing bench factory.
    return dict(source_settings)


class _OperatorRuntime:
    """Narrow, trusted host facade. It is never supplied to policy context."""
    def __init__(self, trial):
        self.__trial = trial

    def execute(self, request_id, device_id, action, parameters=None):
        return self.__trial._fleet.execute(request_id, device_id, action, parameters)

    def advance(self, request_id, ticks=1):
        receipt = self.__trial._fleet.advance(request_id, ticks)
        self.__trial._after_tick()
        return receipt

    def observations(self):
        return self.__trial._fleet.observations()

    def coverage(self):
        return self.__trial._fleet.coverage()


class SensorTrial:
    """Private authored trial; public goal and operator facade are separate."""
    def __init__(self, catalog, *, condition, seed, power_dbm, source_settings=None):
        source = _source_declaration(power_dbm, source_settings)
        if source is not None and (condition not in CONDITIONS or type(seed) is not int):
            raise ValueError('Invalid synthetic author setup')
        self.catalog = deepcopy(catalog)
        options = {} if source is None else {'source_settings': source}
        self._fleet, self.topology, bootstrap = create_conducted_example(catalog, seed=seed, **options)
        self._source_settings = source
        self.runtime_instance_id = uuid.uuid4().hex
        self._condition, self._seed = condition, seed
        self._power_dbm = float(power_dbm)
        self._author_events = []
        self._release_tick = None
        self._expected_sensor_dbm = float(power_dbm) - 10 - .5 - 20
        dut_settings = ({'frequency_hz': 2.45e9, 'power_dbm': power_dbm,
                         'bandwidth_hz': 20e6, 'duty_cycle': .25,
                         'modulation': 'OFDM', 'crest_factor_db': 3} if source is None else source)
        setup = [('dut', 'configure', dut_settings),
                 ('sensor', 'configure', {'calibration_valid': True, 'acquisition_policy': 'triggered'}),
                 ('dut', 'stop', {})]
        self._setup_receipts = []
        for i, (device, action, parameters) in enumerate(setup):
            result = self._fleet.execute(f'fixture:setup:{i}', device, action, parameters)
            if result['status'] not in {'ok', 'pending'}:
                raise ValueError('Synthetic trial setup failed')
            self._setup_receipts.append(result)
        initial = self._fleet.observations()
        self._start_tick = initial['tick']
        self._goal = {'kind': 'acquire_fresh_rf_sensor', 'dut_id': 'dut',
                      'sensor_id': 'sensor', 'minimum_acquisition_tick': self._start_tick + 1}
        self._bootstrap_receipts = bootstrap
        self._profile_ids = {node['id']: node['profile_id'] for node in self.topology['devices']}
        roles = {profile['profile_id']: profile['role'] for profile in self.catalog['profiles']}
        self._roles = {node: roles[profile] for node, profile in self._profile_ids.items()}
        if condition != 'normal':
            self._author_change(True)
        self.runtime = _OperatorRuntime(self)

    @property
    def goal(self):
        return deepcopy(self._goal)

    def _author_change(self, value):
        event_id = 'author:' + uuid.uuid4().hex
        result = self._fleet.author_control(event_id, 'dut', 'disconnect', value)
        if result['status'] not in {'ok', 'disconnected'}:
            raise ValueError('Synthetic author transition failed')
        self._author_events.append({'request_id': event_id, 'device_id': 'dut',
                                    'fault': 'disconnect', 'value': value,
                                    'tick': result['tick'], 'setup_revision': result['setup_revision']})

    def _after_tick(self):
        tick = self._fleet.observations()['tick']
        if (self._condition == 'restored_disconnect' and self._release_tick is None
                and tick >= self._start_tick + 4):
            self._author_change(False)
            self._release_tick = tick

    def author_record(self):
        return deepcopy({'schema_version': 1, 'kind': 'private_synthetic_author_record',
                         'synthetic': True, 'hardware_verified': False,
                         'condition': self._condition, 'seed': self._seed,
                         'start_tick': self._start_tick, 'release_tick': self._release_tick,
                         'expected_sensor_dbm': self._expected_sensor_dbm,
                         'comparison_tolerance_db': 1e-9,
                         'basis': 'declared_synthetic_policy',
                         'runtime_origin': 'preinitialized', 'resumable': False,
                         'bootstrap_receipts': self._bootstrap_receipts,
                         'setup_receipts': self._setup_receipts,
                         'author_events': self._author_events})


def prepare_sensor_trial(catalog, *, condition='normal', seed=0, power_dbm=12.5, source_settings=None):
    """Host-only factory; original catalog and source files are never modified."""
    if (condition not in CONDITIONS or type(seed) is not int
            or (source_settings is None and not _number(power_dbm))):
        raise ValueError('Invalid synthetic author setup')
    options = {} if source_settings is None else {'source_settings': source_settings}
    return SensorTrial(catalog, condition=condition, seed=seed, power_dbm=power_dbm, **options)


def _assessment(status, verdict, code, refs=()):
    return {'status': status, 'verdict': verdict, 'evaluator_id': 'rf_sensor_fixture_v1',
            'evidence_refs': list(dict.fromkeys(refs)), 'summary_code': code}


def _validated_events(trial, result, events):
    # No repr/default encoder: arbitrary objects and raw exceptions stay private.
    if not isinstance(result, dict) or not isinstance(events, list) or len(events) > 4096:
        raise ValueError('invalid_evidence')
    encoded = json.dumps([result, events], ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(encoded) > 32 * 1024 * 1024:
        raise ValueError('evidence_too_large')
    if (result.get('kind') != 'virtual_fleet_harness_result' or result.get('schema_version') != 1
            or result.get('synthetic') is not True or result.get('hardware_verified') is not False
            or result.get('ai_model_called') is not False
            or result.get('runtime_instance_id') != trial.runtime_instance_id
            or not isinstance(result.get('run_id'), str) or not _ID.fullmatch(result['run_id'])
            or not isinstance(result.get('termination'), dict)
            or not isinstance(result.get('unresolved_request_ids'), list)
            or any(not isinstance(value, str) or not _ID.fullmatch(value)
                   for value in result['unresolved_request_ids'])):
        raise ValueError('invalid_result')
    for i, event in enumerate(events, 1):
        if (not isinstance(event, dict) or event.get('schema_version') != 1
                or event.get('kind') != 'operator_event' or type(event.get('sequence')) is not int
                or event['sequence'] != i or not isinstance(event.get('type'), str)
                or event['type'] not in _EVENT_TYPES
                or event.get('event_id') != f'event:{i}' or event.get('run_id') != result['run_id']
                or event.get('runtime_instance_id') != trial.runtime_instance_id
                or not isinstance(event.get('payload'), dict)):
            raise ValueError('invalid_event')
    return deepcopy(events)


def _validate_observation(trial, observation):
    if (not isinstance(observation, dict) or observation.get('synthetic') is not True
            or observation.get('hardware_verified') is not False
            or not _natural(observation.get('tick')) or not _natural(observation.get('setup_revision'))
            or not isinstance(observation.get('devices'), dict)
            or set(observation['devices']) != set(trial._profile_ids)):
        raise ValueError('invalid_observation')
    for identity, node in observation['devices'].items():
        if (not isinstance(node, dict) or node.get('device_id') != identity
                or node.get('profile_id') != trial._profile_ids[identity]
                or node.get('role') != trial._roles[identity]
                or node.get('synthetic') is not True or node.get('hardware_verified') is not False
                or node.get('tick') != observation['tick']
                or node.get('setup_revision') != observation['setup_revision']
                or not isinstance(node.get('status'), str) or node['status'] not in STATUSES
                or not isinstance(node.get('values'), dict)
                or not isinstance(node['values'].get('outputs', {}), dict)
                or any(not isinstance(packet, dict) for packet in node['values'].get('outputs', {}).values())):
            raise ValueError('invalid_device_observation')


def _validate_receipt(trial, receipt, intent):
    if (not isinstance(receipt, dict) or receipt.get('synthetic') is not True
            or receipt.get('hardware_verified') is not False
            or not _natural(receipt.get('tick')) or not _natural(receipt.get('setup_revision'))
            or not isinstance(receipt.get('status'), str) or receipt['status'] not in STATUSES
            or not isinstance(receipt.get('values'), dict)):
        raise ValueError('invalid_receipt')
    if intent['operation'] == 'execute':
        identity = intent['body']['device_id']
        if (receipt.get('device_id') != identity or receipt.get('profile_id') != trial._profile_ids[identity]
                or receipt.get('role') != trial._roles[identity]
                or receipt['tick'] != intent['before_tick']
                or receipt['setup_revision'] < intent['before_revision']):
            raise ValueError('receipt_identity_or_time')
    elif receipt['tick'] != intent['before_tick'] + intent['body']['ticks']:
        raise ValueError('cached_advance_receipt')


def _valid_measurement(trial, observation, acquisition, baseline_tick):
    if (observation.get('synthetic') is not True or observation.get('hardware_verified') is not False
            or not _natural(observation.get('tick')) or not _natural(observation.get('setup_revision'))):
        return False
    tick, revision = observation['tick'], observation['setup_revision']
    devices = observation.get('devices', {})
    sensor = devices.get('sensor', {})
    if (sensor.get('device_id') != 'sensor' or sensor.get('profile_id') != trial._profile_ids['sensor']
            or sensor.get('role') != 'power_sensor' or sensor.get('status') != 'ok'
            or sensor.get('synthetic') is not True or sensor.get('hardware_verified') is not False
            or sensor.get('tick') != tick or sensor.get('setup_revision') != revision):
        return False
    measurement = sensor.get('values', {}).get('outputs', {}).get('measurement', {})
    coupled = devices.get('coupler', {}).get('values', {}).get('outputs', {}).get('coupled', {})
    if (measurement.get('valid') is not True or measurement.get('status') != 'ok'
            or measurement.get('source_id') != 'sensor' or measurement.get('unit') != 'dBm'
            or not _number(measurement.get('value')) or not _number(measurement.get('power_dbm'))
            or not _natural(measurement.get('acquisition_tick'))
            or measurement.get('acquisition_setup_revision') != revision
            or not max(trial._goal['minimum_acquisition_tick'], baseline_tick + 1) <= measurement['acquisition_tick'] <= tick
            or acquisition is None or acquisition.get('setup_revision') != revision
            or measurement['acquisition_tick'] <= acquisition.get('tick', tick)
            or coupled.get('source_id') != 'coupler' or coupled.get('valid') is not True
            or not _number(coupled.get('power_dbm'))):
        return False
    if trial._condition == 'restored_disconnect' and (
            trial._release_tick is None or measurement['acquisition_tick'] <= trial._release_tick):
        return False
    expected = trial._expected_sensor_dbm
    source = trial._source_settings
    if source is None:
        frequency, duty, crest = 2.45e9, .25, 3
    else:
        # The accepted host declaration is private, not an oracle learned from events.
        numeric = ('frequency_hz', 'bandwidth_hz', 'duty_cycle', 'crest_factor_db')
        if (any(not _number(coupled.get(key)) or coupled[key] != source[key] for key in numeric)
                or type(coupled.get('modulation')) is not str
                or coupled['modulation'] != source['modulation']
                or any(not _number(measurement.get(key))
                       for key in ('frequency_hz', 'duty_cycle', 'crest_factor_db'))):
            return False
        frequency, duty, crest = source['frequency_hz'], source['duty_cycle'], source['crest_factor_db']
    return (abs(measurement['value'] - expected) <= 1e-9
            and abs(measurement['power_dbm'] - expected) <= 1e-9
            and abs(coupled['power_dbm'] - expected) <= 1e-9
            and measurement.get('frequency_hz') == frequency
            and measurement.get('duty_cycle') == duty and measurement.get('crest_factor_db') == crest)


def evaluate_sensor_run(trial, result, events):
    """Grade snapshots, never ACK alone, and return no hidden oracle values."""
    try:
        events = _validated_events(trial, result, events)
        intents, receipted = {}, set()
        acquisition, last_snapshot, baseline_tick = None, None, None
        valid_refs, observation_refs, disconnected_refs = [], [], []
        for event in events:
            payload = event['payload']
            if event['type'] == 'intent':
                request_id, operation, body = payload['request_id'], payload['operation'], payload['body']
                if (not isinstance(request_id, str) or not _ID.fullmatch(request_id)
                        or request_id in intents or type(payload.get('logical_request')) is not int
                        or payload['logical_request'] != len(intents) + 1 or last_snapshot is None
                        or operation not in {'execute', 'advance'} or not isinstance(body, dict)):
                    raise ValueError('invalid_intent')
                if operation == 'execute':
                    if (set(body) != {'device_id', 'action', 'parameters'}
                            or body['device_id'] not in trial._profile_ids
                            or not isinstance(body['action'], str) or not isinstance(body['parameters'], dict)):
                        raise ValueError('invalid_execute_intent')
                elif set(body) != {'ticks'} or type(body['ticks']) is not int or body['ticks'] != 1:
                    raise ValueError('invalid_advance_intent')
                intents[request_id] = {**payload, 'before_tick': last_snapshot['tick'],
                                       'before_revision': last_snapshot['setup_revision']}
            elif event['type'] == 'receipt':
                request_id = payload['request_id']
                if request_id not in intents or request_id in receipted:
                    raise ValueError('receipt_without_unique_intent')
                intent = intents[request_id]
                body, receipt = intent.get('body', {}), payload['result']
                _validate_receipt(trial, receipt, intent)
                receipted.add(request_id)
                if (intent.get('operation') == 'execute' and body.get('device_id') == 'sensor'
                        and body.get('action') == 'acquire' and receipt.get('status') in {'ok', 'pending'}):
                    acquisition = receipt if receipt['setup_revision'] == intent['before_revision'] else None
            elif event['type'] == 'observation':
                observation = payload['observation']
                _validate_observation(trial, observation)
                if last_snapshot is not None and (observation['tick'] < last_snapshot['tick']
                                                  or observation['setup_revision'] < last_snapshot['setup_revision']):
                    raise ValueError('observation_clock_regression')
                if baseline_tick is None:
                    baseline_tick = observation['tick']
                last_snapshot = observation
                observation_refs.append(event['event_id'])
                dut, sensor = observation['devices']['dut'], observation['devices']['sensor']
                if (dut['status'] == 'disconnected' and not dut['values'].get('outputs')
                        and sensor['status'] in {'invalid', 'disconnected', 'error'}
                        and 'measurement' not in sensor['values'].get('outputs', {})):
                    disconnected_refs.append(event['event_id'])
                if _valid_measurement(trial, observation, acquisition, baseline_tick):
                    valid_refs.append(event['event_id'])
        termination = result.get('termination', {})
        completed = termination.get('reason') == 'policy_stop' and termination.get('policy_claim') == 'completed'
        if result.get('unresolved_request_ids') or set(intents) - receipted:
            return _assessment('completed', 'fail', 'execution_unresolved', observation_refs[-1:])
        if trial._condition == 'persistent_disconnect':
            bounded = termination.get('reason') in _BOUNDED or (
                termination.get('reason') == 'policy_stop' and termination.get('policy_claim') in {'blocked', 'failed'})
            passed = (bounded and not completed and not valid_refs and bool(observation_refs)
                      and len(disconnected_refs) == len(observation_refs))
            return _assessment('completed', 'pass' if passed else 'fail',
                               'bounded_noncompletion_confirmed' if passed else 'noncompletion_not_verified',
                               observation_refs[-1:])
        passed = completed and bool(valid_refs)
        return _assessment('completed', 'pass' if passed else 'fail',
                           'observed_goal_satisfied' if passed else 'fresh_measurement_not_verified', valid_refs)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return _assessment('failed', None, 'operator_evidence_invalid')
