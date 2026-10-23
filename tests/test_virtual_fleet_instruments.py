"""Synthetic role/state tests. No customer records, equipment I/O or network."""
import copy
import json
import math
import unittest

from labflow.virtual_fleet.instruments import DEVICE_FACTORIES, ROLE_ACTIONS, ROLE_PORTS


ROLES = {'power_meter', 'signal_analyzer', 'emi_receiver', 'signal_generator',
         'communication_tester', 'bluetooth_tester', 'wireless_ap', 'dfs_system',
         'network_test_station', 'test_software', 'network_analyzer'}


def rf(power=10.0, **changes):
    result = {'frequency_hz': 2.45e9, 'power_dbm': power, 'bandwidth_hz': 2e6,
              'duty_cycle': 0.25, 'crest_factor_db': 4.0, 'modulation': 'synthetic_qpsk',
              'source_id': 'synthetic-source'}
    result.update(changes)
    return result


def sensor(power=10.0, **changes):
    result = {'status': 'ok', 'valid': True, 'value': power, 'unit': 'dBm',
              'frequency_hz': 2.45e9, 'power_dbm': power, 'duty_cycle': 0.25,
              'crest_factor_db': 4.0, 'source_id': 'synthetic-sensor',
              'acquisition_tick': 0, 'acquisition_setup_revision': 0}
    result.update(changes)
    return result


def inputs(**changes):
    result = {'power': {'enabled': True, 'valid': True, 'voltage_v': 12.0},
              'rf': rf(), 'sensor': sensor()}
    result.update(changes)
    return result


def make(role, **simulation):
    profile = {'profile_id': 'synthetic-' + role, 'model': 'SYNTHETIC', 'manufacturer': 'TEST',
               'role': role, 'ports': copy.deepcopy(ROLE_PORTS[role]), 'simulation_parameters': simulation}
    return DEVICE_FACTORIES[role](profile, 123)


def call(device, action, parameters=None, *, tick=0, revision=0, ports=None):
    return device.perform(action, parameters or {}, tick=tick, setup_revision=revision,
                          inputs=inputs() if ports is None else ports)


def advance(device, tick=2, revision=0, ports=None):
    device.advance(tick=tick, setup_revision=revision, inputs=inputs() if ports is None else ports)
    return device.observation(tick=tick, setup_revision=revision)


def packet(response, port='measurement'):
    return response['values']['outputs'][port]


class FleetInstrumentTests(unittest.TestCase):
    def test_role_factories_and_declarations_cover_every_assigned_role(self):
        self.assertEqual(set(DEVICE_FACTORIES), ROLES)
        self.assertEqual(set(ROLE_ACTIONS), ROLES)
        self.assertEqual(set(ROLE_PORTS), ROLES)
        for role in ROLES:
            with self.subTest(role=role):
                device = make(role)
                observed = device.observation(tick=0, setup_revision=0)
                self.assertIn(observed['status'], {'ok', 'invalid'})
                self.assertEqual(observed['values']['state'], 'idle')
                self.assertIn('configure', ROLE_ACTIONS[role])
                json.dumps(observed, allow_nan=False)

    def test_power_meter_on_time_average_and_peak_apply_each_factor_once(self):
        for mode, expected in [('on_average', 10.0), ('time_average', 3.979400086720376), ('peak', 14.0)]:
            with self.subTest(mode=mode):
                device = make('power_meter')
                self.assertEqual(call(device, 'configure', {'measurement_mode': mode})['status'], 'ok')
                self.assertEqual(call(device, 'acquire')['status'], 'pending')
                result = packet(advance(device))
                self.assertAlmostEqual(result['value'], expected, places=10)
                self.assertEqual(result['unit'], 'dBm')
                self.assertEqual(result['quantity'], mode)

    def test_meter_watts_conversion_and_missing_sensor_never_make_zero_measurement(self):
        device = make('power_meter')
        call(device, 'configure', {'measurement_mode': 'on_average', 'unit': 'W'})
        call(device, 'acquire')
        self.assertAlmostEqual(packet(advance(device))['value'], 0.01)
        empty = make('power_meter')
        response = call(empty, 'acquire', ports={'power': inputs()['power']})
        self.assertEqual(response['status'], 'invalid')
        self.assertNotIn('measurement', response['values']['outputs'])

    def test_sensor_validity_units_model_revision_and_quantity_are_fenced(self):
        for change in [{'valid': False}, {'unit': 'mW'}, {'power_dbm': 9.0},
                       {'acquisition_setup_revision': 3}, {'acquisition_tick': 10},
                       {'source_id': ''}, {'duty_cycle': 0}, {'value': float('nan')}]:
            with self.subTest(change=change):
                device = make('power_meter')
                response = call(device, 'acquire', ports=inputs(sensor=sensor(**change)))
                self.assertEqual(response['status'], 'invalid')
                self.assertNotIn('measurement', response['values']['outputs'])

    def test_power_failure_and_overload_preserve_no_valid_output(self):
        for ports in [inputs(power={'valid': True, 'enabled': False, 'voltage_v': 12}),
                      inputs(power={'valid': False, 'enabled': True, 'voltage_v': 12}),
                      {'rf': rf()}, inputs(rf=rf(power=60))]:
            device = make('signal_analyzer')
            call(device, 'configure', {'frequency_hz': 2.45e9})
            result = call(device, 'acquire', ports=ports)
            self.assertIn(result['status'], {'invalid', 'error'})
            self.assertNotIn('measurement', result['values']['outputs'])

    def test_pending_trigger_timeout_abort_and_recovery_are_distinct(self):
        device = make('power_meter', operation_timeout_ticks=5)
        call(device, 'configure', {'trigger_source': 'bus'})
        self.assertEqual(call(device, 'acquire')['values']['state'], 'trigger_wait')
        self.assertEqual(advance(device, 2)['status'], 'pending')
        self.assertEqual(call(device, 'fetch', tick=2)['status'], 'pending')
        self.assertEqual(call(device, 'trigger', tick=2)['status'], 'pending')
        self.assertEqual(advance(device, 4)['status'], 'ok')
        self.assertEqual(call(device, 'abort', tick=4)['values']['state'], 'aborted')
        call(device, 'acquire', tick=4)
        self.assertEqual(advance(device, 10)['status'], 'error')
        self.assertNotIn('measurement', device.observation(tick=10, setup_revision=0)['values']['outputs'])
        self.assertEqual(call(device, 'recover', tick=10)['status'], 'ok')

    def test_measurement_stuck_disconnect_and_recover_do_not_leak_fault_names(self):
        device = make('signal_analyzer', operation_timeout_ticks=4)
        call(device, 'configure', {'frequency_hz': 2.45e9})
        device.author_control('stuck', True)
        call(device, 'acquire')
        self.assertEqual(advance(device, 2)['status'], 'pending')
        self.assertEqual(advance(device, 5)['status'], 'error')
        device.author_control('stuck', False)
        call(device, 'recover', tick=5)
        device.author_control('disconnected', True)
        self.assertEqual(call(device, 'acquire', tick=5)['status'], 'disconnected')
        self.assertNotIn('fault', json.dumps(device.observation(tick=5, setup_revision=0)))
        device.author_control('disconnected', False)
        call(device, 'recover', tick=5)
        call(device, 'acquire', tick=5)
        self.assertEqual(advance(device, 7)['status'], 'ok')

    def test_revision_and_changing_input_invalidate_pending_or_cached_results(self):
        for stale in ['revision', 'input']:
            device = make('signal_analyzer')
            call(device, 'configure', {'frequency_hz': 2.45e9})
            call(device, 'acquire')
            result = advance(device, 2, revision=1 if stale == 'revision' else 0,
                             ports=inputs(rf=rf(9)) if stale == 'input' else inputs())
            self.assertEqual(result['status'], 'invalid')
            self.assertNotIn('measurement', result['values']['outputs'])
        device = make('power_meter')
        call(device, 'acquire')
        advance(device)
        self.assertEqual(device.observation(tick=3, setup_revision=1)['status'], 'invalid')

    def test_cached_fetch_is_stable_and_seeded_noise_reproduces(self):
        results = []
        for _ in range(2):
            device = make('power_meter', noise_db=0.1)
            call(device, 'acquire')
            first = packet(advance(device))
            self.assertEqual(packet(call(device, 'fetch', tick=3)), first)
            self.assertEqual(packet(call(device, 'fetch', tick=4)), first)
            results.append(first)
        self.assertEqual(results[0], results[1])

    def test_bad_configuration_and_unsupported_action_do_not_mutate_configuration(self):
        device = make('signal_analyzer')
        call(device, 'configure', {'frequency_hz': 2.45e9})
        before = device.observation(tick=0, setup_revision=0)['values']['configuration']
        for parameters in [{'frequency_hz': True}, {'frequency_hz': float('inf')},
                           {'bandwidth_hz': -1}, {'unknown': 1}, {'detector': 'invented'}]:
            self.assertEqual(call(device, 'configure', parameters)['status'], 'error')
            self.assertEqual(device.observation(tick=0, setup_revision=0)['values']['configuration'], before)
        self.assertEqual(call(device, 'UNREVIEWED:SCPI?')['status'], 'unsupported')

    def test_analyzer_psd_and_receiver_voltage_derive_from_rf_and_explicit_units(self):
        analyzer = make('signal_analyzer')
        call(analyzer, 'configure', {'frequency_hz': 2.45e9, 'measurement': 'psd', 'rbw_hz': 10000.0})
        call(analyzer, 'acquire')
        result = packet(advance(analyzer))
        self.assertAlmostEqual(result['value'], -53.01029995663981)
        self.assertEqual(result['unit'], 'dBm/Hz')
        self.assertEqual(result['rbw_hz'], 10000)
        receiver = make('emi_receiver')
        call(receiver, 'configure', {'frequency_hz': 2.45e9, 'measurement': 'voltage', 'impedance_ohm': 50.0})
        call(receiver, 'acquire')
        self.assertAlmostEqual(packet(advance(receiver))['value'], 116.98970004336019)
        self.assertEqual(packet(call(receiver, 'fetch', tick=2))['unit'], 'dBuV')

    def test_cw_only_missing_crest_policy_and_field_strength_requirements(self):
        meter = make('power_meter')
        call(meter, 'configure', {'measurement_mode': 'peak'})
        missing = sensor()
        del missing['crest_factor_db']
        self.assertEqual(call(meter, 'acquire', ports=inputs(sensor=missing))['status'], 'invalid')
        analyzer = make('signal_analyzer')
        call(analyzer, 'configure', {'frequency_hz': 2.45e9, 'measurement_mode': 'peak'})
        continuous = rf(modulation='CW', duty_cycle=1)
        del continuous['crest_factor_db']
        call(analyzer, 'acquire', ports=inputs(rf=continuous))
        self.assertAlmostEqual(packet(advance(analyzer, ports=inputs(rf=continuous)))['value'], 10)
        receiver = make('emi_receiver')
        call(receiver, 'configure', {'frequency_hz': 2.45e9, 'measurement': 'field_strength'})
        self.assertEqual(call(receiver, 'acquire')['status'], 'invalid')

    def test_generator_emits_configured_signal_only_with_valid_power(self):
        device = make('signal_generator')
        self.assertEqual(call(device, 'start_tx')['status'], 'invalid')
        configured = call(device, 'configure', {'frequency_hz': 2.45e9, 'power_dbm': 5.0,
                          'bandwidth_hz': 1e6, 'duty_cycle': 0.5, 'crest_factor_db': 2.0, 'modulation': 'test'})
        self.assertTrue(configured['setup_changed'])
        emitted = packet(call(device, 'start_tx'), 'rf')
        self.assertEqual(emitted['power_dbm'], 5)
        self.assertEqual(emitted['duty_cycle'], 0.5)
        self.assertNotIn('rf', call(device, 'stop_tx')['values']['outputs'])

    def test_communication_roles_link_metrics_change_with_received_signal(self):
        for role in ['communication_tester', 'bluetooth_tester', 'wireless_ap', 'network_test_station']:
            values = []
            for power in [-75.0, -95.0]:
                device = make(role)
                ports = inputs(rf=rf(power), data={'valid': True, 'offered_rate_mbps': 100.0})
                call(device, 'configure', {'frequency_hz': 2.45e9, 'offered_rate_mbps': 100.0}, ports=ports)
                call(device, 'acquire', ports=ports)
                observed = advance(device, ports=ports)
                self.assertEqual(observed['status'], 'ok')
                values.append(packet(observed, 'data')['throughput_mbps'])
            self.assertGreater(values[0], values[1], role)

    def test_dfs_detection_checks_pulse_metadata_and_variant(self):
        device = make('dfs_system', function='analyzer')
        call(device, 'configure', {'frequency_hz': 2.45e9, 'detection_threshold_dbm': -60.0})
        self.assertEqual(call(device, 'start_tx')['status'], 'unsupported')
        pulse = rf(-40, modulation='pulse', duty_cycle=0.001, crest_factor_db=0,
                   pulse_width_s=1e-6, pulse_repetition_hz=1000)
        call(device, 'acquire', ports=inputs(rf=pulse))
        self.assertTrue(packet(advance(device, ports=inputs(rf=pulse)))['detected'])
        generator = make('dfs_system', function='generator')
        call(generator, 'configure', {'frequency_hz': 2.45e9, 'power_dbm': -40,
                                      'pulse_width_s': 1e-6, 'pulse_repetition_hz': 1000})
        self.assertAlmostEqual(packet(call(generator, 'start_tx'), 'rf')['duty_cycle'], 0.001)

    def test_software_requires_criteria_and_does_not_turn_fail_into_device_error(self):
        criteria = [{'id': 'synthetic-check', 'unit': 'dBm', 'quantity': 'on_average', 'operator': '<=', 'limit': 12.0}]
        for value, verdict in [(10.0, 'pass'), (14.0, 'fail')]:
            device = make('test_software')
            call(device, 'configure', {'criteria': criteria})
            measurement = sensor(value, quantity='on_average')
            ports = {'measurement': measurement}
            call(device, 'run', ports=ports)
            result = advance(device, ports=ports)
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(packet(result, 'data')['verdict'], verdict)
        empty = make('test_software')
        self.assertEqual(call(empty, 'run', ports={'measurement': sensor()})['status'], 'invalid')
        mismatched = make('test_software')
        call(mismatched, 'configure', {'criteria': criteria})
        self.assertEqual(call(mismatched, 'run', ports={'measurement': sensor(unit='W')})['status'], 'invalid')

    def test_pseries_windows_are_not_physical_sensor_ports_and_calibration_is_distinct(self):
        self.assertEqual(set(ROLE_PORTS['power_meter']['inputs']), {'sensor', 'power'})
        meter = make('power_meter')
        call(meter, 'configure', {'window': 4})
        call(meter, 'acquire')
        self.assertEqual(packet(advance(meter))['window'], 4)
        call(meter, 'calibrate', tick=2)
        completed = advance(meter, tick=4)
        self.assertTrue(completed['values']['operation_complete'])
        self.assertEqual(completed['values']['calibration_state'], 'verification_required')
        self.assertEqual(call(meter, 'acquire', tick=4)['status'], 'invalid')
        verified = call(meter, 'verify_calibration', {'reference_dbm': 10.0, 'tolerance_db': 0.05}, tick=4)
        self.assertEqual(verified['values']['calibration_state'], 'valid')

    def test_network_analyzer_sweep_interpolates_explicit_path_and_requires_calibration(self):
        device = make('network_analyzer')
        call(device, 'configure', {'start_hz': 1e9, 'stop_hz': 3e9, 'points': 3})
        path = {'valid': True, 'frequency_loss_db': [[1e9, 1.0], [3e9, 3.0]], 'source_id': 'synthetic-cable'}
        ports = {'power': inputs()['power'], 'path': path}
        self.assertEqual(call(device, 'acquire', ports=ports)['status'], 'invalid')
        standard = {'valid': True, 'calibration_standard': True,
                    'frequency_loss_db': [[1e9, 0.0], [3e9, 0.0]], 'source_id': 'synthetic-thru'}
        call(device, 'calibrate', {'standard_loss_db': 0.0}, ports={**ports, 'path': standard})
        advance(device, ports={**ports, 'path': standard})
        call(device, 'acquire', tick=2, ports=ports)
        measured = packet(advance(device, tick=4, ports=ports))
        self.assertEqual(measured['frequencies_hz'], [1e9, 2e9, 3e9])
        self.assertEqual(measured['s21_magnitude_db'], [-1.0, -2.0, -3.0])
        self.assertEqual(measured['loss_db'], [1.0, 2.0, 3.0])
        device.author_control('invalid_calibration', True)
        self.assertEqual(call(device, 'acquire', tick=4, ports=ports)['status'], 'invalid')

    def test_network_analyzer_rejects_uncovered_sweep_and_mismatched_rf_pair(self):
        device = make('network_analyzer', calibration_valid=True)
        call(device, 'configure', {'start_hz': 1e9, 'stop_hz': 3e9, 'points': 3})
        bad = inputs(path={'valid': True, 'frequency_loss_db': [[2e9, 1.0], [3e9, 2.0]], 'source_id': 'cable'})
        self.assertEqual(call(device, 'acquire', ports=bad)['status'], 'invalid')
        one = make('network_analyzer', calibration_valid=True)
        call(one, 'configure', {'start_hz': 2.45e9, 'stop_hz': 2.45e9, 'points': 1})
        self.assertEqual(call(one, 'acquire', ports=inputs(reference=rf(), test=rf(frequency_hz=2.46e9)))['status'], 'invalid')

    def test_connected_unavailable_markers_never_fall_back_to_zero_or_other_ports(self):
        marker = {'valid': False, 'reason': 'output_unavailable', 'source_id': 'upstream', 'upstream_status': 'ok'}
        cases = [('power_meter', 'sensor'), ('signal_analyzer', 'rf'), ('emi_receiver', 'power'),
                 ('network_test_station', 'data')]
        for role, port in cases:
            with self.subTest(role=role, port=port):
                device = make(role)
                if role != 'power_meter':
                    call(device, 'configure', {'frequency_hz': 2.45e9})
                response = call(device, 'acquire', ports=inputs(**{port: marker}))
                self.assertEqual(response['status'], 'invalid')
                self.assertEqual(response['values']['outputs'], {})
        vna = make('network_analyzer', calibration_valid=True)
        call(vna, 'configure', {'start_hz': 2.45e9, 'stop_hz': 2.45e9, 'points': 1})
        response = call(vna, 'acquire', ports=inputs(path=marker, reference=rf(), test=rf(8)))
        self.assertEqual(response['status'], 'invalid')
        self.assertEqual(response['values']['outputs'], {})

    def test_cached_measurement_loses_validity_when_current_input_or_power_disappears(self):
        for change in [inputs(sensor={'valid': False, 'reason': 'output_unavailable'}),
                       inputs(sensor=sensor(9)), inputs(power={'valid': False})]:
            meter = make('power_meter')
            call(meter, 'acquire')
            advance(meter)
            result = advance(meter, tick=3, ports=change)
            self.assertEqual(result['status'], 'invalid')
            self.assertNotIn('measurement', result['values']['outputs'])

    def test_author_invalid_calibration_and_missing_output_invalidate_visible_result(self):
        for fault in ['invalid_calibration', 'sensor_mismatch', 'drop_output']:
            with self.subTest(fault=fault):
                meter = make('power_meter')
                call(meter, 'acquire')
                advance(meter)
                meter.author_control(fault, True)
                response = meter.observation(tick=2, setup_revision=0)
                self.assertNotIn('measurement', response['values']['outputs'])
                self.assertNotIn(fault, json.dumps(response))

    def test_quasi_peak_requires_crest_and_detector_peak_obeys_input_limit(self):
        for detector, signal in [('quasi_peak', rf(crest_factor_db=None)),
                                 ('peak', rf(29, crest_factor_db=3))]:
            receiver = make('emi_receiver')
            call(receiver, 'configure', {'frequency_hz': 2.45e9, 'detector': detector})
            call(receiver, 'acquire', ports=inputs(rf=signal))
            response = advance(receiver, ports=inputs(rf=signal))
            self.assertEqual(response['status'], 'invalid')
            self.assertNotIn('measurement', response['values']['outputs'])
        meter = make('power_meter')
        call(meter, 'configure', {'measurement_mode': 'time_average'})
        self.assertEqual(call(meter, 'acquire', ports=inputs(sensor=sensor(40, duty_cycle=0.001)))['status'], 'invalid')

    def test_internal_calibration_completion_needs_no_external_reference_input(self):
        meter = make('power_meter', calibration_valid=False)
        power_only = {'power': inputs()['power']}
        self.assertEqual(call(meter, 'calibrate', ports=power_only)['status'], 'pending')
        completed = advance(meter, ports=power_only)
        self.assertTrue(completed['values']['operation_complete'])
        self.assertEqual(completed['values']['calibration_state'], 'verification_required')
        self.assertEqual(call(meter, 'acquire', tick=2)['status'], 'invalid')

    def test_abort_calibration_and_vna_reset_require_new_verification(self):
        meter = make('power_meter')
        call(meter, 'calibrate')
        response = call(meter, 'abort')
        self.assertEqual(response['values']['calibration_state'], 'verification_required')
        vna = make('network_analyzer', calibration_valid=True)
        call(vna, 'configure', {'start_hz': 2.45e9, 'stop_hz': 2.45e9, 'points': 1})
        call(vna, 'reset')
        call(vna, 'configure', {'start_hz': 2.45e9, 'stop_hz': 2.45e9, 'points': 1})
        response = call(vna, 'acquire', ports=inputs(reference=rf(), test=rf(8)))
        self.assertEqual(response['status'], 'invalid')

    def test_malformed_software_batch_and_quantity_rule_are_rejected_without_exception(self):
        software = make('test_software')
        self.assertEqual(call(software, 'configure', {'criteria': [{'id': 'one', 'unit': 'dBm',
                          'quantity': [], 'operator': '<=', 'limit': 12}]})['status'], 'error')
        call(software, 'configure', {'criteria': [
            {'id': 'one', 'unit': 'dBm', 'operator': '<=', 'limit': 12},
            {'id': 'two', 'unit': 'dBm', 'operator': '<=', 'limit': 12}]})
        response = call(software, 'run', ports={'data': {'valid': True, 'measurements': []}})
        self.assertEqual(response['status'], 'invalid')
        self.assertEqual(response['values']['outputs'], {})

    def test_profile_policy_types_and_unknown_dfs_function_are_rejected(self):
        for policy in [{'calibration_valid': 'false'}, {'power_required': 'false'},
                       {'accepted_sensor_ids': 'sensor'}, {'accepted_sensor_ids': [1]},
                       {'function': 'unverified-mode'}, {'function': []}, {'unreviewed_policy': True}]:
            with self.subTest(policy=policy):
                with self.assertRaises(ValueError):
                    make('dfs_system' if 'function' in policy else 'power_meter', **policy)

    def test_boolean_sensor_revision_and_unbounded_crest_are_not_numeric_evidence(self):
        for change in [{'acquisition_setup_revision': False}, {'crest_factor_db': 1e100}]:
            device = make('power_meter')
            self.assertEqual(call(device, 'acquire', ports=inputs(sensor=sensor(**change)))['status'], 'invalid')

    def test_rf_stays_explicitly_valid_during_parallel_link_measurement(self):
        ap = make('wireless_ap')
        call(ap, 'configure', {'frequency_hz': 2.45e9})
        call(ap, 'start_tx')
        response = call(ap, 'acquire')
        self.assertEqual(response['status'], 'pending')
        self.assertIs(packet(response, 'rf').get('valid'), True)
        self.assertEqual(packet(response, 'rf')['status'], 'ok')

    def test_power_loss_stops_tx_and_recover_requires_explicit_restart(self):
        generator = make('signal_generator')
        call(generator, 'configure', {'frequency_hz': 2.45e9})
        call(generator, 'start_tx')
        failed = advance(generator, 1, ports={'power': {'valid': False}})
        self.assertEqual(failed['status'], 'invalid')
        self.assertEqual(failed['values']['outputs'], {})
        recovered = call(generator, 'recover', tick=1)
        self.assertNotIn('rf', recovered['values']['outputs'])
        self.assertIn('rf', call(generator, 'start_tx', tick=1)['values']['outputs'])

    def test_error_fifo_survives_reset_and_measurement_windows_reject_old_results(self):
        meter = make('power_meter')
        call(meter, 'configure', {'window': 5})
        call(meter, 'reset')
        self.assertEqual(call(meter, 'read_error')['values']['error'], 'measurement_window_out_of_scope')
        self.assertIsNone(call(meter, 'read_error')['values']['error'])
        call(meter, 'acquire')
        advance(meter)
        call(meter, 'configure', {'window': 2}, tick=2)
        response = call(meter, 'fetch', {'window': 1}, tick=2)
        self.assertEqual(response['status'], 'invalid')
        self.assertNotIn('measurement', response['values']['outputs'])

    def test_dfs_invalid_pulse_metadata_and_signal_tuning_mismatch_are_not_success(self):
        dfs = make('dfs_system', function='analyzer')
        call(dfs, 'configure', {'frequency_hz': 2.45e9})
        pulse = rf(-40, modulation='pulse', duty_cycle=0.5, pulse_width_s=1e-6, pulse_repetition_hz=1000)
        self.assertEqual(call(dfs, 'acquire', ports=inputs(rf=pulse))['status'], 'invalid')
        analyzer = make('signal_analyzer')
        call(analyzer, 'configure', {'frequency_hz': 2.45e9, 'bandwidth_hz': 1e6})
        self.assertEqual(call(analyzer, 'acquire', ports=inputs(rf=rf(frequency_hz=3e9)))['status'], 'invalid')

    def test_vna_single_point_ratio_and_software_multiple_criteria_retain_sources(self):
        vna = make('network_analyzer', calibration_valid=True)
        call(vna, 'configure', {'start_hz': 2.45e9, 'stop_hz': 2.45e9, 'points': 1})
        paired = inputs(reference=rf(10), test=rf(7))
        call(vna, 'acquire', ports=paired)
        self.assertEqual(packet(advance(vna, ports=paired))['s21_magnitude_db'], [-3.0])
        software = make('test_software')
        rules = [{'id': 'one', 'unit': 'dBm', 'operator': '<=', 'limit': 12},
                 {'id': 'two', 'unit': 'dBm', 'operator': '>=', 'limit': 5}]
        call(software, 'configure', {'criteria': rules})
        ports = {'data': {'valid': True, 'measurements': {'one': sensor(10), 'two': sensor(4)}}}
        call(software, 'run', ports=ports)
        result = packet(advance(software, ports=ports), 'data')
        self.assertEqual(result['verdict'], 'fail')
        self.assertEqual([r['passed'] for r in result['results']], [True, False])
        self.assertEqual([r['source_id'] for r in result['results']], ['synthetic-sensor'] * 2)

    def test_declared_limits_keep_sweep_and_rules_inside_runtime_result_budget(self):
        vna = make('network_analyzer', calibration_valid=True)
        self.assertEqual(call(vna, 'configure', {'points': 2049})['status'], 'error')
        call(vna, 'configure', {'start_hz': 1.23456789e9, 'stop_hz': 3.98765432e9, 'points': 2048})
        ports = inputs(path={'valid': True, 'source_id': 'synthetic-curve',
                            'frequency_loss_db': [[1.23456789e9, 1.0123456789], [3.98765432e9, 3.987654321]]})
        call(vna, 'acquire', ports=ports)
        result = advance(vna, ports=ports)
        self.assertEqual(result['status'], 'ok')
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False).encode('utf-8')), 256*1024)
        software = make('test_software')
        rules = [{'id': str(index), 'unit': 'dBm', 'operator': '<=', 'limit': 12} for index in range(129)]
        self.assertEqual(call(software, 'configure', {'criteria': rules})['status'], 'error')

    def test_transmitter_rejects_empty_metadata_before_emitting_invalid_rf(self):
        for role, parameter in [('signal_generator', 'modulation'), ('wireless_ap', 'ssid')]:
            transmitter = make(role)
            self.assertEqual(call(transmitter, 'configure', {parameter: ''})['status'], 'error')

    def test_author_controls_reject_role_inapplicable_faults(self):
        for role, fault in [('signal_generator', 'stuck'), ('wireless_ap', 'invalid_calibration'),
                            ('signal_analyzer', 'sensor_mismatch'), ('test_software', 'gain_error_db')]:
            with self.subTest(role=role, fault=fault):
                with self.assertRaises(ValueError):
                    make(role).author_control(fault, True if fault != 'gain_error_db' else 1.0)

    def test_nested_criterion_operator_types_are_explicit_errors(self):
        for operator in [[], {}, None, True]:
            software = make('test_software')
            response = call(software, 'configure', {'criteria': [
                {'id': 'one', 'unit': 'dBm', 'operator': operator, 'limit': 12}]})
            self.assertEqual(response['status'], 'error')
            self.assertEqual(response['values']['configuration']['criteria'], [])

    def test_meter_explicit_frequency_setting_must_match_sensor_frequency(self):
        meter = make('power_meter')
        call(meter, 'configure', {'frequency_hz': 2.45e9})
        response = call(meter, 'acquire', ports=inputs(sensor=sensor(frequency_hz=3e9)))
        self.assertEqual(response['status'], 'invalid')
        self.assertEqual(response['values']['outputs'], {})


if __name__ == '__main__':
    unittest.main()
