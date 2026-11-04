"""Extended detector acquisition through the actual workflow/driver boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dgm_control import measurement_template, VirtualLab, detector_catalog
from dgm_control.evaluation import evaluation_template
from dgm_control.receiver_measurement import acquire_grid, validate_trace, require_dedicated_receiver
from dgm_control.receiver_peer import ReceiverPeer
from dgm_control.radio_run import run_radio
from dgm_control.virtual_recipe import run_virtual
from dgm_control.hardware_run import run_hardware
from dgm_lab.detectors import EXTENDED_RANGES
from test_receivers import receiver_profile, commissioned_measurement
from test_hardware_run import QUICK, profiles_fixture, peers
from test_radio_scan import quick, scan_hardware
from test_radios import hardware_peers, read
from test_evaluation import commissioned_fixture

MODELS = ('EPL1000', 'ESU8', 'FSW50', 'N9030B')


class ExtendedReceiverWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_each_family_each_radio_correction_ranking_and_saved_proof(self):
        for i, model in enumerate(MODELS):
            for j, radio in enumerate(('wlan', 'bluetooth', 'cellular', 'nfc', 'uwb')):
                detector = ('QP', 'LINEAR_AVER', 'CISPR_AVER')[(i+j) % 3]
                with self.subTest(model=model, radio=radio), patch('socket.create_connection', side_effect=AssertionError('no real I/O')):
                    plan = QUICK if radio == 'wlan' else quick(radio)
                    m = measurement_template(plan, detector, model)
                    e = evaluation_template(plan, m)
                    folder = self.root/(model+radio)
                    result = run_virtual(folder, plan=plan, measurement_config=m, evaluation=e) if radio == 'wlan' else run_radio(
                        plan, 'simulation', folder, measurement_config=m, evaluation=e)
                    self.assertEqual(result['status'], 'completed', result)
                    self.assertEqual(result['assessment']['verdict'], 'PASS', result)
                    self.assertTrue(read(folder/'result.json')['measurement']['returned_to_sampled_peak'])
                    self.assertFalse(read(folder/'result.json')['physical_verified'])
                    for sample in map(json.loads, (folder/'samples.jsonl').read_text().splitlines()):
                        validate_trace(sample['trace'], m)
                        self.assertEqual(sample['evaluation']['bins'][0]['input_dbuv'], sample['trace']['values_dbuv'][0])
                        self.assertIn('capability', sample['trace']['receiver_points'][0]['readbacks'])

    def test_all_ten_models_all_detectors_share_grid_proof_contract(self):
        for model in EXTENDED_RANGES:
            for detector in ('POS', 'QP', 'LINEAR_AVER', 'CISPR_AVER'):
                m = measurement_template(QUICK, detector, model)
                with self.subTest(model=model, detector=detector), VirtualLab(measurement_config=m).open('EmiReceiver') as session, session.active():
                    trace = acquire_grid(session, m, lambda: None)
                    validate_trace(trace, m)
                    changed = deepcopy(trace)
                    changed['receiver_points'][0]['readbacks']['capability']['firmware'] = 'MISMATCH'
                    with self.assertRaises(Exception): validate_trace(changed, m)

    def test_hardware_adapter_uses_dedicated_native_role_for_all_families(self):
        import dgm_lab.registry as registry
        for model, radio in zip(MODELS + ('N9010A',), ('wlan', 'bluetooth', 'cellular', 'nfc', 'uwb')):
            plan, profiles, synthetic = (QUICK, profiles_fixture(), QUICK) if radio == 'wlan' else scan_hardware(radio)
            m = commissioned_measurement(measurement_template(synthetic, 'QP', model))
            e = commissioned_fixture(evaluation_template(synthetic, m | {'simulation_only': True}))
            profiles['EmiReceiver'] = receiver_profile(model)
            with self.subTest(model=model, radio=radio), (peers() if radio == 'wlan' else hardware_peers(synthetic)) as (world, opened):
                state = world._world if radio == 'wlan' else world
                original = registry.open_transport.side_effect
                def connect(config, log=None):
                    if config.get('host') == 'EmiReceiver.invalid':
                        opened.append('EmiReceiver')
                        return ReceiverPeer(state, model, log)
                    return original(config, log)
                with patch('dgm_lab.registry.open_transport', side_effect=connect):
                    result = run_hardware(profiles, plan, self.root/radio, measurement_config=m, evaluation=e) if radio == 'wlan' else run_radio(
                        plan, 'hardware', self.root/radio, profiles=profiles, measurement_config=m, evaluation=e)
                self.assertEqual(result['status'], 'completed', result)
                self.assertEqual(result['assessment']['verdict'], 'PASS')
                self.assertIn('EmiReceiver', opened)

    def test_partial_final_result_failure_and_cancel_keep_logs_not_verdict(self):
        for model, query in [('FSW50', 'CALC:MARK1:FUNC:FME:RES?'), ('N9030B', 'CALC:MARK1:FUNC:MAM?')]:
            plan = quick('bluetooth'); m = measurement_template(plan, 'QP', model)
            original = ReceiverPeer._write
            calls = 0
            def fail(peer, command):
                nonlocal calls
                original(peer, command)
                if command == query:
                    calls += 1
                    if calls == 2: peer.reply = '-999,-999,-999,30010000' if model.startswith('N') else 'NaN'
            with patch.object(ReceiverPeer, '_write', fail):
                folder = self.root/model
                result = run_radio(plan, 'simulation', folder, measurement_config=m, evaluation=evaluation_template(plan, m))
            self.assertEqual(result['status'], 'failed', result)
            self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')
            points = list(map(json.loads, (folder/'observations.jsonl').read_text().splitlines()))
            self.assertEqual(sum(p['phase'] == 'receiver-point' for p in points), 1)
            self.assertTrue(read(folder/'phone-log.json')['events'])
            self.assertFalse(read(folder/'simulation.json')['final_state']['source']['tx'])
            result = run_radio(plan, 'simulation', self.root/(model+'cancel'), measurement_config=m,
                               evaluation=evaluation_template(plan, m), fault='cancel-after-sample')
            self.assertEqual(result['status'], 'cancelled')
            self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')

    def test_missing_option_is_logged_and_never_assessed(self):
        plan = quick('nfc'); m = measurement_template(plan, 'QP', 'N9030B')
        original = ReceiverPeer._write
        def no_option(peer, command):
            original(peer, command)
            if command == '*OPT?': peer.reply = '550'
        with patch.object(ReceiverPeer, '_write', no_option):
            result = run_radio(plan, 'simulation', self.root/'missing', measurement_config=m, evaluation=evaluation_template(plan, m))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')
        self.assertIn('EMC', json.dumps(result))

    def test_duplicate_endpoint_rejected_and_catalog_exposes_role_models(self):
        profiles = profiles_fixture(); profiles['EmiReceiver'] = receiver_profile('N9030B')
        for kind, fields in [('tcp', {'host': 'example.invalid', 'port': 5025}), ('visa', {'resource': 'GPIB0::18::INSTR'})]:
            for name in ('EmiReceiver', 'SpectrumAnalyzer'):
                profiles[name]['config']['transport'] = dict(kind=kind, **fields)
            with self.assertRaises(ValueError): require_dedicated_receiver(profiles)
        rows = {r['model']: r for r in detector_catalog()['models'] if r['device_id'] == 'EmiReceiver'}
        self.assertEqual(rows['EPL1000']['maximum_hz'], 30e6)
        self.assertEqual(rows['FSW50']['required_option'], 'K54')
        self.assertEqual(rows['N9030B']['required_option'], 'EMC')
        for row in detector_catalog()['models']:
            if row['status'] == 'separate-final-detector-role':
                self.assertIn('Use EmiReceiver role', row['reason'])
