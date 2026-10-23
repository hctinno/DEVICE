"""Repeatable virtual bench checks with separate observations and scenario truth.

These checks exercise a synthetic contract. They neither call an AI model nor
establish compliance, instrument accuracy, OEM support or physical RF behavior.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from uuid import uuid4

from .virtual_lab import VirtualLab


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def evaluate_virtual_observation(observation, minimum_dbm, maximum_dbm):
    """Classify only observable synthetic evidence, without scenario/fault names."""
    if not (_finite_number(minimum_dbm) and _finite_number(maximum_dbm)):
        raise ValueError('Diagnostic bounds must be finite numbers')
    if minimum_dbm > maximum_dbm:
        raise ValueError('Diagnostic minimum must not exceed maximum')
    if not isinstance(observation, dict):
        return 'invalid'
    if observation.get('synthetic') is not True or observation.get('hardware_verified') is not False:
        return 'invalid'
    status = observation.get('status')
    if status in ('pending', 'disconnected', 'no_data', 'invalid'):
        return status if observation.get('measurement') is None else 'invalid'
    if status != 'ok':
        return 'invalid'
    measurement = observation.get('measurement')
    if not isinstance(measurement, dict):
        return 'invalid'
    if measurement.get('synthetic') is not True or measurement.get('unit') != 'DBM':
        return 'invalid'
    for key in ('measurement_id', 'setup_revision'):
        value = measurement.get(key)
        if type(value) is not int or value < 1:
            return 'invalid'
    tick, completed = observation.get('tick'), measurement.get('completed_tick')
    if type(tick) is not int or type(completed) is not int or not 0 <= completed <= tick:
        return 'invalid'
    value = measurement.get('value')
    if not _finite_number(value):
        return 'invalid'
    if value < minimum_dbm:
        return 'below_range'
    if value > maximum_dbm:
        return 'above_range'
    return 'in_range'


class _Scenario:
    def __init__(self):
        self.lab = VirtualLab(seed=41, measurement_ticks=2, noise_db=0.0)
        self.events = []
        self.controls = []
        self.checks = []

    def act(self, action, **arguments):
        event = {'sequence': len(self.events) + 1, 'action': action, 'arguments': arguments}
        self.events.append(event)
        try:
            event['observation'] = getattr(self.lab, action)(**arguments)
        except Exception as exc:
            # The outer runner records a failed check and saves the attempted
            # command as evidence, instead of dropping a failed scenario.
            event['observation'] = {'status': 'exception', 'synthetic': True,
                                    'hardware_verified': False,
                                    'error': f'{type(exc).__name__}: {exc}'}
            raise
        return event['observation']

    def control(self, action, **arguments):
        # Hidden scenario setup is never added to operator observations.
        self.controls.append({'after_event': len(self.events), 'action': action, 'arguments': arguments})
        getattr(self.lab, action)(**arguments)

    def check(self, name, actual, expected):
        self.checks.append({'name': name, 'actual': actual, 'expected': expected,
                            'passed': type(actual) is type(expected) and actual == expected})

    def acquire(self, label):
        initialized = self.act('meter', command='INIT1:IMM')
        self.check(f'{label}_init', initialized['status'], 'ok')
        completion = self.act('meter', command='*OPC?')
        polls = 0
        while completion['status'] == 'pending' and polls < 3:
            self.act('advance', ticks=1)
            polls += 1
            completion = self.act('meter', command='*OPC?')
        observed = self.act('meter', command='FETC1?')
        return observed, completion, polls

    def assess_power(self, label, observed, completion, expected_class, expected_power):
        self.check(f'{label}_completion_status', completion.get('status'), 'ok')
        self.check(f'{label}_completion', completion.get('response'), '1')
        self.check(f'{label}_observation', evaluate_virtual_observation(observed, 6.9, 7.1), expected_class)
        power = observed.get('measurement', {}).get('value')
        self.check('power_dbm' if label == 'initial' else f'{label}_power_dbm', power, expected_power)


def _exercise(scenario, name):
    scenario.act('configure_dut', mode='g', channel=6, power_dbm=10.0)
    scenario.act('set_path', connected=True, loss_db=3.0)
    if name == 'silent_tx':
        scenario.control('inject_fault', name='tx_ignored', value=True)
    elif name == 'cable_open':
        scenario.control('set_path', connected=False, loss_db=3.0)
    elif name == 'thermal_drop':
        scenario.control('inject_fault', name='thermal_drop_db', value=6.0)
    elif name == 'measurement_stuck':
        scenario.control('inject_fault', name='measurement_stuck', value=True)
    elif name == 'transport_loss_recovery':
        scenario.control('inject_fault', name='meter_disconnected', value=True)
    acknowledgement = scenario.act('start_tx')
    scenario.check('tx_command_accepted', acknowledgement.get('accepted'), True)

    if name == 'transport_loss_recovery':
        disconnected = scenario.act('meter', command='INIT')
        scenario.check('lost_transport', evaluate_virtual_observation(disconnected, 6.9, 7.1), 'disconnected')
        scenario.act('advance', ticks=3)
        scenario.control('inject_fault', name='meter_disconnected', value=False)
        empty = scenario.act('meter', command='FETC?')
        scenario.check('lost_command_not_executed', evaluate_virtual_observation(empty, 6.9, 7.1), 'no_data')
        observed, completion, _ = scenario.acquire('recovered')
        scenario.assess_power('recovered', observed, completion, 'in_range', 7.0)
        return

    observed, completion, polls = scenario.acquire('initial')
    if name == 'measurement_stuck':
        scenario.check('initial_observation', evaluate_virtual_observation(observed, 6.9, 7.1), 'pending')
        scenario.check('poll_budget_exhausted', completion['status'] == 'pending' and polls == 3, True)
        scenario.check('abort_accepted', scenario.act('meter', command='ABOR')['status'], 'ok')
        empty = scenario.act('meter', command='FETC?')
        scenario.check('aborted_data_discarded', evaluate_virtual_observation(empty, 6.9, 7.1), 'no_data')
        scenario.control('inject_fault', name='measurement_stuck', value=False)
        observed, completion, _ = scenario.acquire('recovered')
        scenario.assess_power('recovered', observed, completion, 'in_range', 7.0)
        return

    # Independent literal expectations for the synthetic fixture, not values
    # derived from private DUT/meter state or a scenario's declared success.
    expected_class, expected_power = {
        'normal': ('in_range', 7.0),
        'silent_tx': ('below_range', -100.0),
        'cable_open': ('below_range', -100.0),
        'thermal_drop': ('below_range', 1.0),
    }[name]
    scenario.assess_power('initial', observed, completion, expected_class, expected_power)


def _save_json(root, relative_path, payload):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
    data = path.read_bytes()
    return {'path': relative_path, 'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def run_virtual_scenarios(output_dir):
    """Execute six checks and preserve a new evidence directory on every call."""
    run_id = str(uuid4())
    root = Path(output_dir).resolve() / run_id
    root.mkdir(parents=True, exist_ok=False)
    provenance = {'schema_version': 1, 'synthetic': True, 'hardware_verified': False,
                  'ai_model_called': False, 'verification_level': 'synthetic_contract_only',
                  'profile_id': VirtualLab.profile_id}
    files, results = [], []
    names = ['normal', 'silent_tx', 'cable_open', 'thermal_drop',
             'measurement_stuck', 'transport_loss_recovery']
    for index, name in enumerate(names, 1):
        scenario = _Scenario()
        try:
            _exercise(scenario, name)
        except Exception as exc:
            scenario.check('scenario_execution', f'{type(exc).__name__}: {exc}', 'completed')
        observations_path = f'observations/{index:02d}.json'
        assessment_path = f'assessments/{index:02d}.json'
        passed = bool(scenario.checks) and all(check['passed'] for check in scenario.checks)
        files.append(_save_json(root, observations_path, {
            **provenance, 'events': scenario.events,
        }))
        files.append(_save_json(root, assessment_path, {
            **provenance, 'scenario': name, 'passed': passed, 'seed': 41,
            'measurement_ticks': 2, 'noise_db': 0.0,
            'diagnostic_range_dbm': [6.9, 7.1], 'poll_limit': 3,
            'controls': scenario.controls, 'checks': scenario.checks,
        }))
        results.append({'scenario': name, 'passed': passed,
                        'failed_checks': sum(not check['passed'] for check in scenario.checks),
                        'observations': observations_path, 'assessment': assessment_path})
    passed_count = sum(result['passed'] for result in results)
    summary = {**provenance, 'run_id': run_id,
               'created_at': datetime.now(timezone(timedelta(hours=9))).isoformat(),
               'total_scenarios': len(results), 'passed': passed_count,
               'failed': len(results) - passed_count, 'scenarios': results,
               'manifest': 'manifest.json'}
    files.append(_save_json(root, 'summary.json', summary))
    _save_json(root, 'manifest.json', {**provenance, 'run_id': run_id, 'files': files})
    return {**summary, 'output_dir': str(root)}
