import importlib.util
import hashlib
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class VirtualLabTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_lab'), 'virtual lab not implemented')
        from labflow.virtual_lab import VirtualLab
        self.lab_type = VirtualLab
        self.lab = self.connected_lab()

    def connected_lab(self, **kwargs):
        lab = self.lab_type(**kwargs)
        lab.configure_dut('g', 6, 10.0)
        lab.set_path(True, 3.0)
        lab.start_tx()
        return lab

    def acquire(self, lab=None):
        lab = lab or self.lab
        self.assertEqual(lab.meter('INIT1:IMM')['status'], 'ok')
        lab.advance(2)
        return lab.meter('FETC1?')

    def test_measurement_waits_for_completion_and_converts_cached_power(self):
        self.assertEqual(self.lab.meter('FETC?')['status'], 'no_data')
        self.lab.meter('INIT')
        self.assertEqual(self.lab.meter('*OPC?')['status'], 'pending')
        self.lab.advance(1)
        self.assertEqual(self.lab.meter('FETC?')['status'], 'pending')
        self.lab.advance(1)
        self.assertEqual(self.lab.meter('*OPC?')['response'], '1')
        dbm = self.lab.meter('FETC?')
        self.assertEqual(dbm['measurement']['value'], 7.0)
        self.assertTrue(dbm['synthetic'])
        self.lab.meter('UNIT1:POW W')
        watts = self.lab.meter('FETCH1:SCALAR:POWER:AC?')
        self.assertAlmostEqual(watts['measurement']['value'], 0.005011872336272725)
        self.assertEqual(watts['measurement']['measurement_id'], dbm['measurement']['measurement_id'])
        self.assertEqual(self.lab.meter('UNIT:POW?')['response'], 'W')

    def test_fetch_does_not_trigger_or_resample_noise(self):
        lab = self.connected_lab(seed=41, noise_db=0.1)
        first = self.acquire(lab)
        lab.advance(100)
        again = lab.meter('FETC?')
        self.assertEqual(first['measurement'], again['measurement'])
        second = self.acquire(lab)
        self.assertNotEqual(first['measurement']['measurement_id'], second['measurement']['measurement_id'])
        self.assertNotEqual(first['measurement']['value'], second['measurement']['value'])
        twin = self.connected_lab(seed=41, noise_db=0.1)
        self.assertEqual(first['measurement']['value'], self.acquire(twin)['measurement']['value'])
        self.assertEqual(second['measurement']['value'], self.acquire(twin)['measurement']['value'])

    def test_bus_trigger_and_duplicate_init_preserve_fifo_errors_on_reset(self):
        self.assertEqual(self.lab.meter('*TRG')['error_number'], -211)
        self.lab.meter('TRIG:SEQ1:SOUR BUS')
        self.lab.meter('INIT')
        self.lab.advance(20)
        self.assertEqual(self.lab.meter('*OPC?')['status'], 'pending')
        self.assertEqual(self.lab.meter('INIT')['error_number'], -213)
        self.lab.meter('*TRG')
        self.lab.advance(2)
        self.assertEqual(self.lab.meter('FETC?')['measurement']['value'], 7.0)
        self.lab.meter('*RST')
        self.assertEqual(self.lab.meter('SYST:ERR?')['error_number'], -211)
        self.assertEqual(self.lab.meter('SYSTEM:ERROR?')['error_number'], -213)
        self.assertEqual(self.lab.meter('SYST:ERR?')['error_number'], 0)
        self.assertEqual(self.lab.meter('TRIG:SOUR?')['response'], 'IMM')
        self.assertEqual(self.lab.meter('FETC?')['status'], 'no_data')

    def test_abort_cancels_pending_and_does_not_change_trigger_source(self):
        self.lab.meter('TRIG:SOUR BUS')
        self.lab.meter('INIT')
        self.lab.meter('ABORT1')
        self.lab.advance(100)
        self.assertEqual(self.lab.meter('FETC?')['status'], 'no_data')
        self.assertEqual(self.lab.meter('TRIG:SOUR?')['response'], 'BUS')
        self.assertEqual(self.lab.meter('*OPC?')['response'], '1')

    def test_error_overflow_and_clear_do_not_abort_measurement(self):
        self.lab.meter('INIT')
        for _ in range(33):
            self.lab.meter('INIT')
        for _ in range(29):
            self.assertEqual(self.lab.meter('SYST:ERR?')['error_number'], -213)
        self.assertEqual(self.lab.meter('SYST:ERR?')['error_number'], -350)
        self.assertEqual(self.lab.meter('SYST:ERR?')['error_number'], 0)
        self.lab.meter('INIT')
        self.lab.meter('*CLS')
        self.assertEqual(self.lab.meter('SYST:ERR?')['error_number'], 0)
        self.lab.advance(2)
        self.assertEqual(self.lab.meter('FETC?')['measurement']['value'], 7.0)

    def test_tx_ack_does_not_prove_rf_emission(self):
        self.lab.stop_tx()
        self.lab.inject_fault('tx_ignored', True)
        self.assertTrue(self.lab.start_tx()['accepted'])
        result = self.acquire()
        self.assertEqual(result['measurement']['value'], -100.0)
        self.assertNotIn('tx_ignored', str(result))

    def test_path_open_and_thermal_drop_change_observed_power(self):
        self.lab.set_path(False, 3.0)
        self.assertEqual(self.acquire()['measurement']['value'], -100.0)
        self.lab.set_path(True, 3.0)
        self.lab.inject_fault('thermal_drop_db', 6.0)
        self.assertEqual(self.acquire()['measurement']['value'], 1.0)

    def test_changed_configuration_invalidates_pending_and_cached_measurements(self):
        self.lab.meter('INIT')
        self.lab.set_path(True, 5.0)
        self.lab.advance(2)
        self.assertEqual(self.lab.meter('FETC?')['status'], 'invalid')
        self.assertEqual(self.acquire()['measurement']['value'], 5.0)
        self.lab.configure_dut('n', 6, 10.0)
        self.assertEqual(self.lab.meter('FETC?')['status'], 'invalid')

    def test_stuck_measurement_can_be_aborted_and_recovered(self):
        self.lab.inject_fault('measurement_stuck', True)
        self.lab.meter('INIT')
        self.lab.advance(1000)
        self.assertEqual(self.lab.meter('*OPC?')['status'], 'pending')
        self.lab.meter('ABOR')
        self.lab.inject_fault('measurement_stuck', False)
        self.assertEqual(self.acquire()['measurement']['value'], 7.0)

    def test_transport_loss_does_not_execute_commands(self):
        self.lab.inject_fault('meter_disconnected', True)
        self.assertEqual(self.lab.meter('INIT')['status'], 'disconnected')
        self.lab.advance(10)
        self.lab.inject_fault('meter_disconnected', False)
        self.assertEqual(self.lab.meter('FETC?')['status'], 'no_data')
        self.assertEqual(self.acquire()['measurement']['value'], 7.0)

    def test_unsupported_operations_do_not_masquerade_as_vendor_success(self):
        for command in ['INIT1?', 'INIT2', 'FORM REAL', 'FORM:BORD NORM', 'TRIG:SOUR EXT',
                        'UNIT1:POW 15', '*RST;INIT', 'INIT:CONT ON', 'TRAC:DATA?', 'INIT\n*TRG']:
            with self.subTest(command=command):
                result = self.lab.meter(command)
                self.assertEqual(result['status'], 'unsupported')
                self.assertIsNone(result['response'])
        self.assertEqual(self.lab.meter('FETC?')['status'], 'no_data')
        self.assertIn('SIM', self.lab.meter('*IDN?')['response'])

    def test_numeric_and_boolean_validation_happens_before_state_change(self):
        for value in [True, float('nan'), float('inf'), -31, 31, '10', 10**400]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.lab.configure_dut('g', 6, value)
        for connected, loss in [(1, 3), (True, -1), (True, float('nan'))]:
            with self.assertRaises(ValueError):
                self.lab.set_path(connected, loss)
        for ticks in [True, -1, 1.5, 10001]:
            with self.assertRaises(ValueError):
                self.lab.advance(ticks)
        with self.assertRaises(ValueError):
            self.lab.inject_fault('unknown', True)
        with self.assertRaises(ValueError):
            self.lab.inject_fault('tx_ignored', 'false')
        self.assertEqual(self.acquire()['measurement']['value'], 7.0)


class VirtualScenarioTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_scenarios'),
                             'virtual scenario runner not implemented')
        from labflow.virtual_scenarios import evaluate_virtual_observation, run_virtual_scenarios
        self.assess = evaluate_virtual_observation
        self.run_scenarios = run_virtual_scenarios

    def observation(self, value=7.0):
        return {'status': 'ok', 'synthetic': True, 'hardware_verified': False, 'tick': 2,
                'measurement': {'value': value, 'unit': 'DBM', 'synthetic': True,
                                'measurement_id': 1, 'setup_revision': 3, 'completed_tick': 2}}

    def test_assessment_uses_observed_values_and_provenance(self):
        for value, expected in [(7, 'in_range'), (6.9, 'in_range'), (7.1, 'in_range'),
                                (-100, 'below_range'), (1, 'below_range'), (15, 'above_range')]:
            with self.subTest(value=value):
                self.assertEqual(self.assess(self.observation(value), 6.9, 7.1), expected)
        for key, value in [('synthetic', False), ('synthetic', 1), ('hardware_verified', True)]:
            observation = self.observation()
            observation[key] = value
            self.assertEqual(self.assess(observation, 6.9, 7.1), 'invalid')
        for status in ['pending', 'disconnected', 'no_data', 'invalid']:
            self.assertEqual(self.assess({'status': status, 'synthetic': True,
                                         'hardware_verified': False}, 6.9, 7.1), status)

    def test_malformed_measurements_and_ranges_cannot_pass(self):
        for key, value in [('value', float('nan')), ('value', float('inf')), ('value', 10**400), ('value', True),
                           ('value', '7'), ('unit', 'W'), ('synthetic', False),
                           ('measurement_id', 0), ('setup_revision', True), ('completed_tick', 3)]:
            observation = self.observation()
            observation['measurement'][key] = value
            with self.subTest(key=key, value=value):
                self.assertEqual(self.assess(observation, 6.9, 7.1), 'invalid')
        for observation in [None, {}, {'status': 'ok'}, self.observation() | {'measurement': None}]:
            self.assertEqual(self.assess(observation, 6.9, 7.1), 'invalid')
        for limits in [(8, 7), (True, 7), (float('nan'), 7), (7, float('inf')), (7, 10**400)]:
            with self.assertRaises(ValueError):
                self.assess(self.observation(), *limits)

    def read_assessments(self, result):
        root = Path(result['output_dir'])
        return {item['scenario']: json.loads((root / item['assessment']).read_text(encoding='utf-8'))
                for item in result['scenarios']}

    def test_six_scenarios_preserve_observations_and_recovery_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_scenarios(Path(temp) / '가상 시험 결과')
            self.assertEqual((result['total_scenarios'], result['passed'], result['failed']), (6, 6, 0))
            self.assertTrue(result['synthetic'])
            self.assertFalse(result['hardware_verified'])
            self.assertFalse(result['ai_model_called'])
            assessments = self.read_assessments(result)
            for name, value in [('normal', 7.0), ('silent_tx', -100.0), ('cable_open', -100.0),
                                ('thermal_drop', 1.0)]:
                check = next(check for check in assessments[name]['checks'] if check['name'] == 'power_dbm')
                self.assertEqual(check['actual'], value)
            stuck = assessments['measurement_stuck']
            self.assertTrue(any(check['name'] == 'poll_budget_exhausted' and check['actual'] is True
                                for check in stuck['checks']))
            for name in ['measurement_stuck', 'transport_loss_recovery']:
                self.assertTrue(any(check['name'] == 'recovered_observation' and check['actual'] == 'in_range'
                                    for check in assessments[name]['checks']))
            root = Path(result['output_dir'])
            for item in result['scenarios']:
                trace = json.loads((root / item['observations']).read_text(encoding='utf-8'))
                self.assertNotIn('scenario', trace)
                self.assertNotIn('controls', trace)
                self.assertNotIn('expected', trace)
                self.assertTrue(trace['events'])
                self.assertTrue(all(event['action'] != 'inject_fault' for event in trace['events']))
                self.assertTrue(all(event['observation']['synthetic'] is True for event in trace['events']))

    def test_manifest_verifies_all_artifacts_and_repeated_runs_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            first = self.run_scenarios(temp)
            root = Path(first['output_dir'])
            before = {path.relative_to(root).as_posix(): path.read_bytes()
                      for path in root.rglob('*') if path.is_file()}
            second = self.run_scenarios(temp)
            self.assertNotEqual(first['output_dir'], second['output_dir'])
            self.assertEqual(before, {path.relative_to(root).as_posix(): path.read_bytes()
                                      for path in root.rglob('*') if path.is_file()})
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual({entry['path'] for entry in manifest['files']}, set(before) - {'manifest.json'})
            for entry in manifest['files']:
                payload = (root / entry['path']).read_bytes()
                self.assertEqual(len(payload), entry['size_bytes'])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry['sha256'])
            self.assertEqual(self.read_assessments(first), self.read_assessments(second))

    def test_broken_simulator_produces_failed_assessments_instead_of_named_success(self):
        from labflow.virtual_lab import VirtualLab

        class NoFaultsLab(VirtualLab):
            def inject_fault(self, name, value):
                pass

        with tempfile.TemporaryDirectory() as temp, patch('labflow.virtual_scenarios.VirtualLab', NoFaultsLab):
            result = self.run_scenarios(temp)
            assessments = self.read_assessments(result)
            self.assertGreaterEqual(result['failed'], 4)
            for name in ['silent_tx', 'thermal_drop', 'measurement_stuck', 'transport_loss_recovery']:
                self.assertFalse(assessments[name]['passed'])
                self.assertTrue(any(not check['passed'] for check in assessments[name]['checks']))

    def test_unexpected_simulator_failure_is_retained_and_fails_the_run(self):
        from labflow.virtual_lab import VirtualLab

        class BrokenMeter(VirtualLab):
            def meter(self, command):
                raise RuntimeError('deliberate test failure')

        with tempfile.TemporaryDirectory() as temp, patch('labflow.virtual_scenarios.VirtualLab', BrokenMeter):
            result = self.run_scenarios(temp)
            self.assertEqual(result['failed'], 6)
            for item in result['scenarios']:
                content = (Path(result['output_dir']) / item['observations']).read_text(encoding='utf-8')
                self.assertIn('deliberate test failure', content)

    def test_pending_completion_cannot_pass_with_a_stale_response_string(self):
        from labflow.virtual_lab import VirtualLab

        class ContradictoryCompletion(VirtualLab):
            def meter(self, command):
                result = super().meter(command)
                if command == '*OPC?' and result['status'] == 'ok':
                    result['status'] = 'pending'
                return result

        with tempfile.TemporaryDirectory() as temp, \
             patch('labflow.virtual_scenarios.VirtualLab', ContradictoryCompletion):
            result = self.run_scenarios(temp)
            self.assertFalse(self.read_assessments(result)['normal']['passed'])

    def test_cli_runs_in_non_ascii_path_and_reports_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, '-m', 'labflow', '--workspace', str(Path(temp) / '상태'),
                 'virtual-check', '--out', str(Path(temp) / '가상 시험')],
                capture_output=True, encoding='utf-8', cwd=Path(__file__).resolve().parents[1], timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual((summary['passed'], summary['failed']), (6, 0))
            self.assertTrue((Path(summary['output_dir']) / summary['manifest']).is_file())
            self.assertFalse((Path(temp) / '상태').exists())

    def test_cli_returns_nonzero_for_failed_scenario_checks(self):
        from labflow.__main__ import main
        with tempfile.TemporaryDirectory() as temp, \
             patch('sys.argv', ['labflow', '--workspace', temp, 'virtual-check', '--out', temp]), \
             patch('labflow.virtual_scenarios.run_virtual_scenarios', return_value={'failed': 1}), \
             patch('sys.stdout', new_callable=StringIO) as stdout:
            self.assertEqual(main(), 1)
            self.assertEqual(json.loads(stdout.getvalue()), {'failed': 1})


if __name__ == '__main__':
    unittest.main()
