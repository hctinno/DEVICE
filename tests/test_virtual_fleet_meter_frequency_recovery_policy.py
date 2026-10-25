"""Owner-authored synthetic cases, separate from the independent sealed oracle."""
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import unittest

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.harness import FleetHarness, RetryableTransportError
from labflow.virtual_fleet.integration import create_conducted_example, get_role_actions

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'labflow.virtual_fleet.meter_frequency_recovery_policy'


def bench(*, frequency=2.46e9, calibration=True, disconnected=False, meter_fault=None):
    catalog = load_catalog(ROOT / 'virtual_profiles/sm_a176u_unlicensed.json')
    fleet, topology, bootstrap = create_conducted_example(catalog, seed=19)
    preparation = []
    for device, action, parameters in (
        ('dut', 'stop', {}),
        ('dut', 'configure', {'frequency_hz': 2.44e9, 'power_dbm': 9.0,
                             'bandwidth_hz': 10e6, 'duty_cycle': .4,
                             'modulation': 'owner_synthetic', 'crest_factor_db': 4.5}),
        ('sensor', 'configure', {'calibration_valid': calibration,
                                 'acquisition_policy': 'triggered'}),
        ('meter', 'configure', {'frequency_hz': frequency, 'measurement_mode': 'on_average',
                                'unit': 'dBm', 'window': 1, 'trigger_source': 'immediate'}),
    ):
        receipt = fleet.execute('owner:prepare:' + str(len(preparation)), device, action, parameters)
        if receipt['status'] not in {'ok', 'pending'}:
            raise AssertionError(receipt)
        preparation.append(receipt)
    if disconnected:
        preparation.append(fleet.author_control('owner:disconnect', 'sensor', 'disconnect', True))
    if meter_fault is not None:
        preparation.append(fleet.author_control('owner:meter-fault', 'meter', meter_fault, True))
    initial = fleet.observations()
    goal = {'kind': 'acquire_fresh_rf_sensor_meter', 'dut_id': 'dut', 'sensor_id': 'sensor',
            'meter_id': 'meter', 'minimum_acquisition_tick': initial['tick'] + 1,
            'allow_meter_frequency_reconfigure': True}
    return fleet, catalog, topology, goal, bootstrap + preparation


def run_case(policy_type, *, allow=True, frequency=2.46e9, calibration=True,
             disconnected=False, budgets=None, boundary=None, meter_fault=None, event_sink=None):
    fleet, catalog, topology, goal, setup = bench(
        frequency=frequency, calibration=calibration, disconnected=disconnected, meter_fault=meter_fault)
    goal['allow_meter_frequency_reconfigure'] = allow
    contexts, proposals, events = [], [], []
    candidate = policy_type()

    class Recorder:
        policy_id = candidate.policy_id

        def __call__(self, context):
            contexts.append(deepcopy(context))
            before = deepcopy(context)
            result = candidate(context)
            if context != before:
                raise AssertionError('policy mutated public input')
            proposals.append(deepcopy(result))
            return result

    def sink(event):
        events.append(event)
        if event_sink is not None:
            event_sink(event)

    runtime = fleet if boundary is None else boundary(fleet)
    runner = FleetHarness(runtime, Recorder(), goal=goal, catalog=catalog, topology=topology,
                          role_actions=get_role_actions(), budgets=budgets, event_sink=sink,
                          run_id='owner:meter', runtime_instance_id='owner:live-runtime')
    report = runner.run()
    return {'fleet': fleet, 'runtime': runtime, 'candidate': candidate, 'report': report,
            'events': events, 'contexts': contexts, 'proposals': proposals, 'setup': setup}


def intents(case, device=None, action=None):
    return [e for e in case['events'] if e['type'] == 'intent'
            and (device is None or e['payload']['body'].get('device_id') == device)
            and (action is None or e['payload']['body'].get('action') == action)]


def receipt_for(case, intent):
    return next(e['payload']['result'] for e in case['events'] if e['type'] == 'receipt'
                and e['payload']['request_id'] == intent['payload']['request_id'])


class RefusedConfigure:
    """Boundary double: refuse configure without changing the real synthetic fleet."""
    def __init__(self, fleet):
        self.fleet = fleet

    def execute(self, request_id, device, action, parameters):
        if device == 'meter' and action == 'configure':
            result = self.fleet.observations()['devices']['meter']
            result['status'] = 'invalid'
            result['values']['reason'] = 'synthetic_config_rejected'
            return result
        return self.fleet.execute(request_id, device, action, parameters)

    def advance(self, request_id, ticks):
        return self.fleet.advance(request_id, ticks)

    def observations(self):
        return self.fleet.observations()


class LostConfigureReply(RefusedConfigure):
    """Real runtime commits once; its original ledger answers the same-ID retry."""
    def __init__(self, fleet):
        super().__init__(fleet)
        self.lost = False
        self.configure_calls = []

    def execute(self, request_id, device, action, parameters):
        result = self.fleet.execute(request_id, device, action, parameters)
        if device == 'meter' and action == 'configure':
            self.configure_calls.append((request_id, deepcopy(parameters)))
            if not self.lost:
                self.lost = True
                raise RetryableTransportError()
        return result


class MeterRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), 'new public recovery API is absent')
        self.Policy = importlib.import_module(MODULE).RFMeterFrequencyRecoveryPolicy

    def assert_completed(self, case):
        self.assertEqual(case['report']['termination'],
                         {'reason': 'policy_stop', 'policy_claim': 'completed'})

    def test_public_api_requires_explicit_goal_and_no_private_constructor_input(self):
        policy = self.Policy()
        self.assertEqual(policy.policy_id, 'rf_meter_frequency_recovery_v1')
        with self.assertRaises(TypeError):
            self.Policy(seed=19)
        context = run_case(self.Policy)['contexts'][0]
        for missing in ('meter_id', 'allow_meter_frequency_reconfigure'):
            changed = deepcopy(context)
            changed['goal'].pop(missing)
            self.assertEqual(self.Policy()(changed)['claim'], 'failed')

    def test_authorized_conflict_causes_one_frequency_only_correction_then_fresh_both(self):
        case = run_case(self.Policy)
        self.assert_completed(case)
        corrections = intents(case, 'meter', 'configure')
        self.assertEqual(len(corrections), 1)
        configure = corrections[0]
        self.assertEqual(configure['payload']['body']['parameters'], {'frequency_hz': 2440000000.0})
        acquisitions = intents(case, 'meter', 'acquire')
        self.assertEqual(len(acquisitions), 2)
        first = receipt_for(case, acquisitions[0])
        self.assertEqual(first['status'], 'invalid')
        self.assertEqual(first['values']['reason'], 'sensor_frequency_setting_conflict')
        self.assertEqual(first['values']['outputs'], {})
        acknowledged = receipt_for(case, configure)
        self.assertEqual(acknowledged['status'], 'ok')
        self.assertGreater(acknowledged['setup_revision'], first['setup_revision'])
        self.assertEqual(acknowledged['values']['configuration_revision'],
                         first['values']['configuration_revision'] + 1)
        before = deepcopy(first['values']['configuration'])
        before['frequency_hz'] = 2440000000.0
        self.assertEqual(acknowledged['values']['configuration'], before)
        seq = [(e['payload']['body'].get('device_id'), e['payload']['body'].get('action'))
               for e in intents(case)]
        at = seq.index(('meter', 'configure'))
        self.assertEqual([x for x in seq[at + 1:] if x[0] in {'sensor', 'meter'}],
                         [('sensor', 'acquire'), ('sensor', 'read'),
                          ('meter', 'acquire'), ('meter', 'fetch')])
        final = case['contexts'][-1]['observations']
        sensor = final['devices']['sensor']['values']['outputs']['measurement']
        meter = final['devices']['meter']['values']['outputs']['measurement']
        # Hand arithmetic: 9 - 10 - 0.5 - 20 = -21.5 dBm (coupled branch).
        self.assertAlmostEqual(sensor['power_dbm'], -21.5, delta=1e-9)
        self.assertAlmostEqual(meter['value'], -21.5, delta=1e-9)
        self.assertGreater(sensor['acquisition_tick'], acknowledged['tick'])
        self.assertGreater(meter['acquisition_tick'], sensor['acquisition_tick'])
        self.assertEqual(meter['acquisition_setup_revision'], final['setup_revision'])
        self.assertEqual(meter['source_id'], 'meter')
        self.assertEqual(meter['input_source_id'], 'sensor')
        self.assertEqual(meter['quantity'], 'on_average')
        self.assertEqual(meter['unit'], 'dBm')
        ids = [e['payload']['request_id'] for e in intents(case)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(intents(case, 'sensor', 'acquire')), 2)
        self.assertEqual(len(intents(case, 'sensor', 'read')), 2)

    def test_already_matched_or_one_hz_tolerance_uses_no_configure(self):
        for frequency in (2440000000.0, 2440000001.0):
            with self.subTest(frequency=frequency):
                case = run_case(self.Policy, frequency=frequency)
                self.assert_completed(case)
                self.assertEqual(intents(case, 'meter', 'configure'), [])
                self.assertEqual(len(intents(case, 'meter', 'acquire')), 1)
                self.assertEqual(len(intents(case, 'meter', 'fetch')), 1)

    def test_no_grant_blocks_fresh_conflict_without_configure(self):
        case = run_case(self.Policy, allow=False)
        self.assertEqual(case['report']['termination']['policy_claim'], 'blocked')
        self.assertEqual(intents(case, 'meter', 'configure'), [])
        self.assertEqual(len(intents(case, 'meter', 'acquire')), 1)
        self.assertEqual(intents(case, 'meter', 'fetch'), [])

    def test_refused_configure_is_not_retried_or_completed(self):
        case = run_case(self.Policy, boundary=RefusedConfigure)
        self.assertEqual(case['report']['termination']['policy_claim'], 'blocked')
        self.assertEqual(len(intents(case, 'meter', 'configure')), 1)
        self.assertEqual(len(intents(case, 'meter', 'acquire')), 1)

    def test_lost_ack_uses_harness_same_id_body_retry_one_logical_configure(self):
        case = run_case(self.Policy, boundary=LostConfigureReply)
        self.assert_completed(case)
        self.assertEqual(len(intents(case, 'meter', 'configure')), 1)
        self.assertEqual(case['report']['usage']['transport_retries'], 1)
        calls = case['runtime'].configure_calls
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        correction = receipt_for(case, intents(case, 'meter', 'configure')[0])
        self.assertEqual(correction['values']['configuration_revision'],
                         case['setup'][-1]['values']['configuration_revision'] + 1)

    def test_uncalibrated_sensor_blocks_without_recovery_commands(self):
        case = run_case(self.Policy, calibration=False)
        self.assertEqual(case['report']['termination']['policy_claim'], 'blocked')
        self.assertEqual(intents(case, 'meter', 'configure'), [])
        self.assertEqual(intents(case, 'sensor', 'configure'), [])

    def test_persistent_disconnect_is_bounded_without_clear_fault_or_success(self):
        case = run_case(self.Policy, disconnected=True, budgets={'ticks': 6})
        self.assertEqual(case['report']['termination']['reason'], 'tick_budget')
        self.assertIsNone(case['report']['termination']['policy_claim'])
        self.assertEqual(intents(case, 'meter', 'configure'), [])

    def test_report_and_event_contracts_do_not_grade_fixture_claim_or_cleanup(self):
        case = run_case(self.Policy)
        report = case['report']
        self.assertEqual(len(report), 15)
        self.assertTrue(report['synthetic'])
        self.assertFalse(report['hardware_verified'])
        self.assertFalse(report['ai_model_called'])
        self.assertEqual(report['policy'], {'kind': 'fixture', 'id': 'rf_meter_frequency_recovery_v1'})
        self.assertEqual(report['task_outcome'], 'not_assessed')
        self.assertEqual(report['assessment']['status'], 'not_assessed')
        self.assertEqual(report['cleanup']['status'], 'not_assessed')
        self.assertTrue(all(len(c) == 8 and len(c['goal']) == 6 for c in case['contexts']))
        self.assertEqual(report['unresolved_request_ids'], [])
        self.assertTrue(all(len(e) == 8 for e in case['events']))
        # A terminated instance stays terminal and never emits a new device command.
        again = case['candidate'](deepcopy(case['contexts'][-1]))
        self.assertEqual(again['kind'], 'stop')

    def replay_changed(self, change, *, phase='fetch'):
        case = run_case(self.Policy)
        if phase == 'fetch':
            index = next(i + 1 for i, p in enumerate(case['proposals'])
                         if p.get('action') == 'fetch')
        elif phase == 'configure':
            index = next(i + 1 for i, p in enumerate(case['proposals'])
                         if p.get('action') == 'configure')
        elif phase == 'conflict':
            index = next(i + 1 for i, p in enumerate(case['proposals'])
                         if p.get('device_id') == 'meter' and p.get('action') == 'acquire')
        policy = self.Policy()
        for c in case['contexts'][:index]:
            policy(deepcopy(c))
        changed = deepcopy(case['contexts'][index])
        change(changed)
        proposal = policy(changed)
        self.assertEqual(proposal['kind'], 'stop')
        self.assertNotEqual(proposal['claim'], 'completed')
        self.assertNotIn('CANARY', json.dumps(proposal))
        return proposal

    def test_meter_sample_provenance_units_window_and_numbers_are_bound(self):
        for field, value in (
            ('source_id', 'CANARY'), ('input_source_id', 'dut'), ('unit', 'W'),
            ('quantity', 'time_average'), ('window', 2), ('configuration_revision', 0),
            ('acquisition_setup_revision', 0), ('acquisition_tick', 9999),
            ('simulation_basis', 'CANARY'), ('value', -27.0), ('frequency_hz', 2450000000.0),
            ('duty_cycle', True), ('crest_factor_db', float('inf')), ('value', 10**400),
        ):
            with self.subTest(field=field, value=value):
                self.replay_changed(lambda c: c['observations']['devices']['meter']['values']
                                    ['outputs']['measurement'].__setitem__(field, value))

    def test_missing_or_wrong_fetch_receipt_cannot_complete(self):
        for transform in (
            lambda c: c.__setitem__('last_receipt', None),
            lambda c: c['last_receipt'].__setitem__('device_id', 'sensor'),
            lambda c: c['last_receipt']['values']['outputs'].clear(),
            lambda c: c['last_receipt'].__setitem__('status', 'invalid'),
        ):
            with self.subTest(transform=transform):
                self.replay_changed(transform)

    def test_binding_or_clock_changes_are_rejected(self):
        for transform in (
            lambda c: c['goal'].__setitem__('allow_meter_frequency_reconfigure', False),
            lambda c: c['catalog']['profiles'][0].__setitem__('model', 'CANARY'),
            lambda c: c['topology'].__setitem__('connections', []),
            lambda c: c['role_actions']['power_meter'].pop('fetch'),
            lambda c: c['observations'].__setitem__('tick', 0),
        ):
            with self.subTest(transform=transform):
                self.assertEqual(self.replay_changed(transform)['claim'], 'failed')

    def test_configure_ack_requires_revision_change_and_frequency_only_settings(self):
        for transform in (
            lambda c: c.__setitem__('last_receipt', None),
            lambda c: c['observations']['devices']['meter']['values']['configuration']
                .__setitem__('unit', 'W'),
            lambda c: c['last_receipt']['values'].__setitem__('configuration_revision', 0),
            lambda c: c['last_receipt'].__setitem__('setup_changed', False),
        ):
            with self.subTest(transform=transform):
                self.replay_changed(transform, phase='configure')

    def test_cached_conflict_or_unsupported_metadata_never_grants_configure(self):
        initial = run_case(self.Policy)['contexts'][0]
        initial['observations']['devices']['meter']['values']['reason'] = 'sensor_frequency_setting_conflict'
        proposal = self.Policy()(deepcopy(initial))
        self.assertNotEqual(proposal.get('action'), 'configure')
        for transform in (
            lambda c: c['role_actions']['power_meter'].pop('configure'),
            lambda c: c['role_actions']['power_meter']['configure']['parameters'].pop('frequency_hz'),
            lambda c: c['observations']['devices']['meter']['values']['configuration']
                .__setitem__('measurement_mode', 'peak'),
            lambda c: c['topology'].__setitem__('connections', [e for e in c['topology']['connections']
                if e['target'] != {'device_id': 'meter', 'port': 'sensor'}]),
        ):
            with self.subTest(transform=transform):
                value = deepcopy(initial)
                transform(value)
                result = self.Policy()(value)
                self.assertEqual(result['kind'], 'stop')
                self.assertNotEqual(result['claim'], 'completed')
                self.assertNotEqual(result.get('action'), 'configure')

    def test_conflict_receipt_configuration_must_match_current_meter(self):
        for transform in (
            lambda c: c['last_receipt']['values']['configuration'].__setitem__('frequency_hz', 2440000000.0),
            lambda c: c['last_receipt']['values'].__setitem__('configuration_revision', 0),
            lambda c: c['last_receipt']['values'].pop('configuration'),
        ):
            with self.subTest(transform=transform):
                self.assertEqual(self.replay_changed(transform, phase='conflict')['claim'], 'failed')

    def test_current_failed_meter_calibration_cannot_complete(self):
        self.replay_changed(lambda c: c['observations']['devices']['meter']['values']
                            .__setitem__('calibration_state', 'verification_failed'))

    def test_meter_acquisition_must_follow_own_intent_and_sensor_capture(self):
        case = run_case(self.Policy)
        own = next(c['observations']['tick'] for c, p in zip(case['contexts'], case['proposals'])
                   if p.get('device_id') == 'meter' and p.get('action') == 'acquire'
                   and c['observations']['setup_revision'] == case['contexts'][-1]['observations']['setup_revision'])
        sensor_tick = case['contexts'][-1]['observations']['devices']['sensor']['values']['outputs']['measurement']['acquisition_tick']
        for tick in (own, sensor_tick):
            self.replay_changed(lambda c: c['observations']['devices']['meter']['values']
                                ['outputs']['measurement'].__setitem__('acquisition_tick', tick))

    def test_malformed_goal_json_envelopes_and_unknown_receipt_never_dispatch(self):
        initial = run_case(self.Policy)['contexts'][0]
        changes = (
            lambda c: c['goal'].__setitem__('allow_meter_frequency_reconfigure', 1),
            lambda c: c['goal'].__setitem__('minimum_acquisition_tick', True),
            lambda c: c['goal'].__setitem__('meter_id', 'sensor'),
            lambda c: c['goal'].__setitem__('extra', 1),
            lambda c: c.__setitem__('remaining_budget', []),
            lambda c: c['observations'].__setitem__('synthetic', False),
            lambda c: c['observations']['devices']['meter'].__setitem__('profile_id', 'CANARY'),
            lambda c: c['observations']['devices']['meter'].__setitem__('tick', True),
            lambda c: c.__setitem__('last_receipt', object()),
            lambda c: c['remaining_budget'].__setitem__('seed', 'CANARY'),
        )
        for change in changes:
            with self.subTest(change=change):
                context = deepcopy(initial)
                change(context)
                self.assertEqual(self.Policy()(context), {'kind': 'stop', 'claim': 'failed',
                                                         'reason': 'invalid_public_context'})
        self.replay_changed(lambda c: c['last_receipt'].__setitem__('status', 'CANARY'), phase='configure')

    def test_changed_sensor_target_never_retunes_a_second_time(self):
        self.replay_changed(lambda c: c['observations']['devices']['sensor']['values']
                            ['outputs']['measurement'].__setitem__('frequency_hz', 2450000000.0))

    def test_mutating_returned_proposal_does_not_change_correction_state(self):
        case = run_case(self.Policy)
        at = next(i for i, p in enumerate(case['proposals']) if p.get('action') == 'configure')
        policy = self.Policy()
        for c in case['contexts'][:at]:
            policy(deepcopy(c))
        proposal = policy(deepcopy(case['contexts'][at]))
        proposal['parameters']['frequency_hz'] = 1
        for c in case['contexts'][at + 1:]:
            proposal = policy(deepcopy(c))
        self.assertEqual(proposal['claim'], 'completed')

    def test_meter_numeric_tolerance_accepts_small_roundoff_but_rejects_larger_error(self):
        case = run_case(self.Policy, frequency=2.44e9)
        for delta, claim in ((5e-10, 'completed'), (2e-9, 'failed')):
            policy = self.Policy()
            result = None
            for c in deepcopy(case['contexts']):
                for node in (c['observations']['devices']['meter'], c['last_receipt']):
                    if node and node.get('device_id') == 'meter':
                        sample = node.get('values', {}).get('outputs', {}).get('measurement')
                        if sample:
                            sample['value'] += delta
                result = policy(c)
                if result['kind'] == 'stop':
                    break
            self.assertEqual(result['claim'], claim)

    def test_real_base_exception_reaches_harness_redacted_policy_error(self):
        from unittest.mock import patch
        with patch('labflow.virtual_fleet.meter_frequency_recovery_policy.RFSensorFixturePolicy.__call__',
                   side_effect=KeyboardInterrupt('CANARY')):
            case = run_case(self.Policy)
        self.assertEqual(case['report']['termination']['reason'], 'policy_error')
        self.assertIsNone(case['report']['termination']['policy_claim'])
        self.assertNotIn('CANARY', json.dumps(case['events']))

    def test_boolean_aliases_in_read_or_conflict_receipt_are_not_measurement_evidence(self):
        case = run_case(self.Policy)
        index = next(i + 1 for i, p in enumerate(case['proposals']) if p.get('action') == 'read')
        policy = self.Policy()
        for c in case['contexts'][:index]:
            policy(deepcopy(c))
        context = deepcopy(case['contexts'][index])
        context['last_receipt']['values']['outputs']['measurement']['valid'] = 1
        with self.subTest(boundary='sensor_read'):
            self.assertEqual(policy(context)['kind'], 'stop')
        self.replay_changed(lambda c: c['last_receipt']['values']['configuration']
                            .__setitem__('window', True), phase='conflict')

    def test_meter_calibration_failure_and_stuck_measurement_do_not_complete(self):
        failed = run_case(self.Policy, meter_fault='invalid_calibration')
        self.assertEqual(failed['report']['termination']['policy_claim'], 'blocked')
        self.assertEqual(intents(failed, 'meter', 'configure'), [])
        stuck = run_case(self.Policy, meter_fault='stuck', budgets={'ticks': 10})
        self.assertEqual(stuck['report']['termination']['reason'], 'tick_budget')
        self.assertIsNone(stuck['report']['termination']['policy_claim'])
        self.assertEqual(len(intents(stuck, 'meter', 'configure')), 1)

    def test_unacknowledged_correction_exhausts_retry_with_original_unresolved_intent(self):
        class NeverAcknowledged(LostConfigureReply):
            def execute(self, request_id, device, action, parameters):
                result = super().execute(request_id, device, action, parameters)
                if device == 'meter' and action == 'configure':
                    raise RetryableTransportError()
                return result
        case = run_case(self.Policy, boundary=NeverAcknowledged)
        self.assertEqual(case['report']['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertIsNone(case['report']['termination']['policy_claim'])
        correction = intents(case, 'meter', 'configure')
        self.assertEqual(len(correction), 1)
        self.assertEqual(case['report']['unresolved_request_ids'], [correction[0]['payload']['request_id']])
        self.assertEqual(case['report']['usage']['transport_retries'], 2)
        self.assertEqual(len(case['runtime'].configure_calls), 3)


    def test_current_dut_must_still_supply_valid_rf_at_completion(self):
        for change in (
            lambda c: c['observations']['devices']['dut'].__setitem__('status', 'disconnected'),
            lambda c: c['observations']['devices']['dut']['values']['outputs'].clear(),
            lambda c: c['observations']['devices']['dut']['values']['outputs']['rf'].__setitem__('valid', False),
        ):
            with self.subTest(change=change):
                self.replay_changed(change)


if __name__ == '__main__':
    unittest.main()
