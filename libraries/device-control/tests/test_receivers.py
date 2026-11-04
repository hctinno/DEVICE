"""Native receiver parsers + all workflow adapters; never hardware or real RF."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from dgm_control import measurement_template, validate_measurement, detector_catalog, VirtualLab, Fault
from dgm_control.evaluation import Evaluation, evaluation_template
from dgm_control.receiver_measurement import acquire_grid, validate_trace
from dgm_control.receiver_peer import ReceiverPeer
from dgm_control.radio_run import run_radio
from dgm_control.virtual_recipe import run_virtual
from dgm_control.hardware_run import run_hardware, check_hardware
from test_radio_scan import quick, scan_hardware
from test_radios import hardware_peers, read
from test_hardware_run import QUICK, peers, profiles_fixture
from test_evaluation import commissioned_fixture


def receiver_profile(model='ESW44'):
    return {'schema_version': 1, 'device_id': 'EmiReceiver', 'mode': 'hardware',
            'config': {'driver': 'EmiReceiver', 'parameters': {'model': model, 'max_frequency_hz': 44e9},
                       'transport': {'kind': 'tcp', 'host': 'EmiReceiver.invalid', 'port': 5025, 'timeout': 5}}}


def commissioned_measurement(config):
    return deepcopy(config) | {'simulation_only': False, 'site_verified': True, 'evidence_notes': 'TEST NATIVE PEER ONLY'}


class ReceiverWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def trace(self, measurement):
        lab = VirtualLab(measurement_config=measurement)
        with lab.open('EmiReceiver') as receiver, receiver.active():
            return acquire_grid(receiver, measurement, lambda: None)

    def test_all_five_radios_all_three_detectors_correct_rank_and_save(self):
        for radio in ('wlan', 'bluetooth', 'cellular', 'nfc', 'uwb'):
            for detector in ('QP', 'LINEAR_AVER', 'CISPR_AVER'):
                with self.subTest(radio=radio, detector=detector), patch('socket.create_connection', side_effect=AssertionError('no physical I/O')):
                    plan = QUICK if radio == 'wlan' else quick(radio)
                    m = measurement_template(plan, detector)
                    e = evaluation_template(plan, m)
                    folder = self.root / (radio+detector)
                    result = run_virtual(folder, plan=plan, evaluation=e, measurement_config=m) if radio == 'wlan' else run_radio(
                        plan, 'simulation', folder, evaluation=e, measurement_config=m)
                    self.assertEqual(result['status'], 'completed', result)
                    self.assertEqual(result['assessment']['verdict'], 'PASS', result)
                    saved = read(folder/'result.json')
                    self.assertTrue(saved['measurement']['returned_to_sampled_peak'])
                    self.assertFalse(saved['physical_verified'])
                    samples = [json.loads(s) for s in (folder/'samples.jsonl').read_text().splitlines()]
                    for sample in samples:
                        trace = sample['trace']; validate_trace(trace, m)
                        self.assertEqual(trace['settings']['detector'], detector)
                        self.assertEqual(sample['evaluation']['bins'][0]['input_dbuv'], trace['values_dbuv'][0])
                    if radio != 'wlan':
                        state = read(folder/'simulation.json')['final_state']
                        self.assertFalse(state['source']['tx'])
                        self.assertEqual(state['route'], 'isolated')

    def test_real_adapter_path_all_radios_uses_receiver_native_protocol(self):
        import dgm_lab.registry as registry
        for radio in ('wlan', 'bluetooth', 'cellular', 'nfc', 'uwb'):
            plan, profiles, synthetic = (QUICK, profiles_fixture(), QUICK) if radio == 'wlan' else scan_hardware(radio)
            m = commissioned_measurement(measurement_template(synthetic, 'QP' if radio == 'nfc' else 'CISPR_AVER'))
            e = commissioned_fixture(evaluation_template(synthetic, m | {'simulation_only': True}))
            profiles['EmiReceiver'] = receiver_profile()
            with self.subTest(radio=radio), (peers() if radio == 'wlan' else hardware_peers(synthetic)) as (world, opened):
                state = world._world if radio == 'wlan' else world
                existing = registry.open_transport.side_effect
                def connect(config, log=None):
                    if config['host'] == 'EmiReceiver.invalid':
                        opened.append('EmiReceiver')
                        return ReceiverPeer(state, 'ESW44', log)
                    return existing(config, log)
                with patch('dgm_lab.registry.open_transport', side_effect=connect):
                    result = run_hardware(profiles, plan, self.root/radio, evaluation=e, measurement_config=m) if radio == 'wlan' else run_radio(
                        plan, 'hardware', self.root/radio, profiles=profiles, evaluation=e, measurement_config=m)
                self.assertEqual(result['status'], 'completed', result)
                self.assertEqual(result['assessment']['verdict'], 'PASS')
                self.assertIn('EmiReceiver', opened)
                self.assertFalse(result['physical_verified'])

    def test_partial_receiver_failure_keeps_point_log_and_stops_source(self):
        plan = quick('nfc'); m = measurement_template(plan, 'QP'); e = evaluation_template(plan, m)
        original = ReceiverPeer._write
        count = 0
        def fail_second(peer, command):
            nonlocal count
            original(peer, command)
            if command == 'TRAC? SINGLE':
                count += 1
                if count == 2: peer.reply = 'NaN'
        with patch.object(ReceiverPeer, '_write', fail_second):
            result = run_radio(plan, 'simulation', self.root/'partial', evaluation=e, measurement_config=m)
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')
        folder = self.root/'partial'
        self.assertFalse((folder/'result.json').exists())
        points = [json.loads(s) for s in (folder/'observations.jsonl').read_text().splitlines()]
        self.assertEqual(len([p for p in points if p['phase'] == 'receiver-point']), 1)
        self.assertFalse(read(folder/'simulation.json')['final_state']['source']['tx'])
        self.assertTrue(read(folder/'phone-log.json')['events'])

    def test_wrong_detector_after_measurement_fails_not_passes(self):
        m = measurement_template(QUICK, 'LINEAR_AVER'); e = evaluation_template(QUICK, m)
        with self.assertRaises(Exception):
            run_virtual(self.root/'wrong', plan=QUICK, measurement_config=m, evaluation=e,
                        fault=Fault('EmiReceiver', 'DET:REC?', 'malformed', 2))
        result = read(self.root/'wrong'/'failure.json')
        self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')
        self.assertFalse(result['final_simulated_state']['phone']['tx'])
        self.assertEqual(result['remaining_connections'], [])

    def test_cancellation_persists_partial_assessment_as_not_evaluated(self):
        plan = quick('bluetooth'); m = measurement_template(plan, 'CISPR_AVER')
        result = run_radio(plan, 'simulation', self.root/'cancel', fault='cancel-after-sample',
                           measurement_config=m, evaluation=evaluation_template(plan, m))
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['assessment']['samples'], 1)
        self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')

    def test_wlan_mid_grid_cancel_keeps_raw_point_and_cleans_up(self):
        m = measurement_template(QUICK, 'QP'); event = threading.Event()
        original = ReceiverPeer._write
        def cancel(peer, command):
            original(peer, command)
            if command == 'TRAC? SINGLE': event.set()
        with patch.object(ReceiverPeer, '_write', cancel), self.assertRaises(InterruptedError):
            run_virtual(self.root/'grid-cancel', plan=QUICK, measurement_config=m,
                        evaluation=evaluation_template(QUICK, m), cancelled=event)
        folder = self.root/'grid-cancel'
        self.assertEqual(len((folder/'receiver-points.jsonl').read_text().splitlines()), 1)
        result = read(folder/'failure.json')
        self.assertEqual(result['assessment']['verdict'], 'NOT_EVALUATED')
        self.assertFalse(result['final_simulated_state']['phone']['tx'])
        self.assertEqual(result['remaining_connections'], [])

    def test_nonuniform_grid_multiple_paths_rank_corrected_field(self):
        plan = quick('bluetooth')
        plan['scan']['rf_paths'].append('generator')
        plan['scan']['path_frequency_limits_hz']['generator'] = [0, 50e9]
        plan['scan']['simulation']['route_loss_db'] = {'dut': 0, 'generator': 20}
        m = measurement_template(plan, 'LINEAR_AVER')
        m['frequencies_hz'][1] = m['frequencies_hz'][0] + 12345
        e = evaluation_template(plan, m)
        for pol in e['paths']['generator'].values():
            for point in pol['cable_loss']['points']: point[1] = 40
        result = run_radio(plan, 'simulation', self.root/'paths', measurement_config=m, evaluation=e)
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(result['peak']['rf_path'], 'generator')
        saved = read(self.root/'paths/result.json')
        self.assertEqual(saved['measurement']['final_facility_readback']['rf_path'], 'isolated')
        self.assertTrue(result['assessment']['measurement_sha256'])

    def test_receiver_numerical_correction_maximum_and_worst_margin(self):
        m = measurement_template(QUICK, 'CISPR_AVER'); e = evaluation_template(QUICK, m)
        e['paths']['dut']['H']['antenna_factor']['points'][1][1] = 60
        e['criterion']['segments'][0].update(start_dbuv_m=70, stop_dbuv_m=150, interpolation='linear_hz')
        trace = self.trace(m)
        for i, value in enumerate((50, 40, 30)):
            from dgm_control.receiver_measurement import CONVERSION
            trace['receiver_points'][i].update(value=value, raw=str(value))
            trace['values_dbuv'][i] = value
            trace['values_dbm'][i] = value-CONVERSION
        engine = Evaluation(e, QUICK, simulated=True, measurement=m)
        row = dict(index=0, height_cm=100, angle_deg=0, polarization='H', trace=trace)
        engine.correct(row)
        summary = engine.summary(completed=True)
        self.assertEqual(summary['maximum_field']['bin'], 2)
        self.assertEqual(summary['maximum_field']['field_dbuv_m'], 93)
        self.assertEqual(summary['worst_margin']['bin'], 0)
        self.assertEqual(summary['verdict'], 'FAIL')

    def test_criterion_mismatch_and_schema_cannot_pass(self):
        m = measurement_template(QUICK, 'LINEAR_AVER')
        for change in ({'detector': 'QP'}, {'detector': 'AVER'}, {'detector': 'RMS'},
                       {'minimum_dwell_seconds': 2}, {'filter_type': 'NORM'}, {'rbw_hz': 9000}):
            e = evaluation_template(QUICK, m); e['criterion'].update(change)
            engine = Evaluation(e, QUICK, simulated=True, measurement=m)
            engine.correct(dict(index=0, height_cm=100, angle_deg=0, polarization='H', trace=self.trace(m)))
            self.assertEqual(engine.summary(completed=True)['verdict'], 'NOT_EVALUATED')
        with self.assertRaises(ValueError): Evaluation(evaluation_template(QUICK), QUICK, simulated=True, measurement=m)
        with self.assertRaises(ValueError): Evaluation(evaluation_template(QUICK, m), QUICK, simulated=True)

    def test_proof_tampering_grid_and_reuse_rejected(self):
        m = measurement_template(QUICK, 'QP')
        trace = self.trace(m)
        for mutate in (lambda t: t['receiver_points'][0]['readbacks']['after'].update({'DET:REC?': 'AVER'}),
                       lambda t: t['values_dbuv'].__setitem__(0, 99),
                       lambda t: t['receiver_points'][0]['identity'].update(model='ESR3'),
                       lambda t: t['receiver_points'].pop(), lambda t: t['frequencies_hz'].reverse()):
            altered = deepcopy(trace); mutate(altered)
            with self.assertRaises(Exception): validate_trace(altered, m)
        engine = Evaluation(evaluation_template(QUICK, m), QUICK, simulated=True, measurement=m)
        with self.assertRaises(ValueError): engine.bind(QUICK, True, m | {'detector': 'LINEAR_AVER'})

    def test_preflight_unknown_models_ranges_dwell_and_hardware_profile(self):
        m = measurement_template(QUICK, 'QP')
        for change in ({'model': 'EPL1000'}, {'model': 'UNREVIEWED'}, {'detector': 'AVER'}, {'dwell_seconds': .99},
                       {'frequencies_hz': [1e9, 2e9]}, {'frequencies_hz': [30e6, 30e6]}, {'filter_type': 'NORM'},
                       {'path_frequency_limits_hz': {'dut': [1, 2]}}):
            with self.assertRaises(Exception): validate_measurement(m | change, QUICK, simulated=True)
        profiles = profiles_fixture(); profiles['EmiReceiver'] = receiver_profile()
        real = commissioned_measurement(m)
        self.assertTrue(check_hardware(profiles, QUICK, real)['valid'])
        for key, value in (('model', 'ESR3'), ('max_frequency_hz', 1e6)):
            altered = deepcopy(profiles); altered['EmiReceiver']['config']['parameters'][key] = value
            with self.assertRaises(ValueError): check_hardware(altered, QUICK, real)
        altered = deepcopy(profiles); altered['EmiReceiver']['config']['transport']['timeout'] = 1
        with self.assertRaises(ValueError): check_hardware(altered, QUICK, real)
        with self.assertRaises(ValueError): check_hardware(profiles, QUICK, m)
        catalog = detector_catalog()['models']
        self.assertEqual(sum(r['status'] == 'implemented-uncommissioned' for r in catalog), 14)
        self.assertTrue(any(r['status'] == 'unconfirmed' for r in catalog))


if __name__ == '__main__': unittest.main()
