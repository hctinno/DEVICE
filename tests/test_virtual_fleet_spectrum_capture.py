from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.harness import FleetHarness
from labflow.virtual_fleet.integration import create_conducted_example, get_role_actions
from labflow.virtual_fleet.spectrum_math import analyze_6db_bandwidth


LIMIT = 4 * 1024 * 1024
MISSING = object()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def declared_trace(offsets=None, levels=None):
    return {'schema_version': 1, 'kind': 'synthetic_frequency_spectrum', 'capture_id': 'declared-1',
            'synthetic': True, 'axis_domain': 'frequency_offset_hz', 'sample_unit': 'dB',
            'amplitude_basis': 'relative_to_peak', 'selection_policy': 'unique_peak_single_lobe_linear_db',
            'frequency_offsets_hz': [-250000, 0, 250000] if offsets is None else offsets,
            'relative_levels_db': [-6, 0, -6] if levels is None else levels}


def real_fixture(detector='rms'):
    catalog = load_catalog(Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json')
    fleet, topology, bootstrap = create_conducted_example(catalog)
    if detector != 'rms':
        configured = fleet.execute('capture:detector', 'analyzer', 'configure', {'detector': detector})
        assert configured['status'] == 'ok'
    initial_tick = fleet.observations()['tick']
    steps = iter([
        {'kind': 'execute', 'device_id': 'analyzer', 'action': 'acquire', 'parameters': {}},
        {'kind': 'advance', 'ticks': 1}, {'kind': 'advance', 'ticks': 1},
        {'kind': 'execute', 'device_id': 'analyzer', 'action': 'fetch', 'parameters': {}},
        {'kind': 'stop', 'claim': 'completed', 'reason': 'current_context_ready'},
    ])
    harness = FleetHarness(fleet, lambda view: next(steps), goal={'kind': 'declared_capture_context'},
        catalog=catalog, topology=topology, role_actions=get_role_actions(),
        run_id='capture-run', runtime_instance_id='capture-instance')
    report = harness.run()
    assert report['termination'] == {'reason': 'policy_stop', 'policy_claim': 'completed'}
    event = [item for item in harness.events() if item['type'] == 'observation'][-1]
    packet = event['payload']['observation']['devices']['analyzer']['values']['outputs']['measurement']
    profile = next(node['profile_id'] for node in topology['devices'] if node['id'] == 'analyzer')
    context = {'run_id': 'capture-run', 'runtime_instance_id': 'capture-instance',
               'source_id': 'analyzer', 'profile_id': profile, 'minimum_acquisition_tick': initial_tick + 1}
    trace = declared_trace()
    capture = {'schema_version': 1, 'kind': 'synthetic_frequency_capture', 'capture_id': trace['capture_id'],
               'synthetic': True, 'capture_origin': 'declared_frequency_fixture',
               'run_id': context['run_id'], 'runtime_instance_id': context['runtime_instance_id'],
               'source_id': context['source_id'], 'profile_id': profile,
               'acquisition_tick': packet['acquisition_tick'],
               'acquisition_setup_revision': packet['acquisition_setup_revision'],
               'observation_event_id': event['event_id'], 'observation_sha256': sha(event),
               'trace_sha256': sha(trace), 'trace': trace}
    return capture, event, context, fleet, report


class SpectrumCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = real_fixture()

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_fleet.spectrum_capture'),
                             'the read-only capture context bridge is not implemented')
        self.module = importlib.import_module('labflow.virtual_fleet.spectrum_capture')
        self.capture, self.event, self.context = deepcopy(self.fixture[:3])

    def run_capture(self, capture=MISSING, event=MISSING, context=MISSING):
        return self.module.analyze_current_bandwidth_capture(
            self.capture if capture is MISSING else capture,
            self.event if event is MISSING else event,
            context=self.context if context is MISSING else context)

    def rehash(self):
        self.capture['observation_sha256'] = sha(self.event)
        self.capture['trace_sha256'] = sha(self.capture['trace'])

    def node(self):
        return self.event['payload']['observation']['devices']['analyzer']

    def packet(self):
        return self.node()['values']['outputs']['measurement']

    def assert_rejected_before_math(self, capture=MISSING, event=MISSING, context=MISSING):
        with patch.object(self.module, 'analyze_6db_bandwidth', side_effect=AssertionError('math must not run')) as math_call:
            with self.assertRaises(ValueError) as caught:
                self.run_capture(capture, event, context)
        self.assertEqual(math_call.call_count, 0)
        self.assertNotIn('CANARY_PRIVATE', str(caught.exception))

    def test_actual_fleet_acquire_advance_fetch_event_has_exact_bound_result(self):
        with patch.object(self.module, 'analyze_6db_bandwidth', wraps=analyze_6db_bandwidth) as math_call:
            result = self.run_capture()
        self.assertEqual(math_call.call_count, 1)
        self.assertEqual(set(result), set('schema_version kind binding bandwidth_result synthetic hardware_verified '
            'ai_model_called method_approval regulatory_scope_complete'.split()))
        expected = {'capture_id': 'declared-1', 'run_id': 'capture-run', 'runtime_instance_id': 'capture-instance',
            'source_id': 'analyzer', 'profile_id': self.context['profile_id'], 'role': 'signal_analyzer',
            'acquisition_tick': 15, 'acquisition_setup_revision': 15, 'configuration_revision': 1,
            'observation_event_id': 'event:17', 'current_tick': 15, 'current_setup_revision': 15,
            'observation_sha256': sha(self.event), 'trace_sha256': sha(self.capture['trace']),
            'capture_sha256': sha(self.capture), 'trace_origin': 'declared_frequency_fixture',
            'binding_scope': 'current_observation_context', 'rf_trace_observed': False}
        self.assertEqual(result['binding'], expected)
        self.assertEqual(result['kind'], 'synthetic_bandwidth_capture_result')
        self.assertEqual(result['schema_version'], 1)
        self.assertIs(result['synthetic'], True)
        self.assertIs(result['hardware_verified'], False)
        self.assertIs(result['ai_model_called'], False)
        self.assertEqual(result['method_approval'], 'not_assessed')
        self.assertIs(result['regulatory_scope_complete'], False)
        bw = result['bandwidth_result']
        self.assertEqual(bw['bandwidth_hz'], 500000)
        self.assertEqual(bw['margin_hz'], 0)
        self.assertEqual(bw['conditional_comparison'], 'meets')
        self.assertEqual(bw['input_sha256'], expected['trace_sha256'])
        self.assertEqual(self.fixture[4]['task_outcome'], 'not_assessed')
        json.dumps(result, allow_nan=False)

    def test_real_peak_acquisition_context_is_supported(self):
        capture, event, context, fleet, report = real_fixture(detector='peak')
        self.assertEqual(event['payload']['observation']['devices']['analyzer']['values']['outputs']['measurement']['quantity'], 'peak')
        self.assertEqual(self.run_capture(capture, event, context)['bandwidth_result']['bandwidth_hz'], 500000)

    def test_public_ids_accept_128_characters_and_observation_cause_is_optional(self):
        self.capture['capture_id'] = self.capture['trace']['capture_id'] = 'A' * 128
        self.capture['run_id'] = self.event['run_id'] = self.context['run_id'] = 'R' * 128
        self.capture['runtime_instance_id'] = self.event['runtime_instance_id'] = self.context['runtime_instance_id'] = 'I' * 128
        del self.event['payload']['cause_request_id']
        self.rehash()
        self.assertEqual(self.run_capture()['binding']['capture_id'], 'A' * 128)

    def test_valid_context_keeps_clipped_multiple_peak_lobe_and_plateau_incomplete(self):
        cases = [(declared_trace(levels=[-3, 0, -8]), ['left_crossing_missing']),
                 (declared_trace([-2, -1, 0, 1, 2], [-10, 0, -3, 0, -10]), ['non_unique_peak']),
                 (declared_trace([-2, -1, 0, 1, 2], [-8, -5, -8, 0, -8]), ['disconnected_lobes']),
                 (declared_trace([-2, -1, 0, 1, 2], [-6, -6, 0, -6, -8]), ['threshold_plateau'])]
        for trace, reasons in cases:
            with self.subTest(reasons=reasons):
                capture = deepcopy(self.capture); capture.update(trace=trace, trace_sha256=sha(trace))
                with patch.object(self.module, 'analyze_6db_bandwidth', wraps=analyze_6db_bandwidth) as math_call:
                    result = self.run_capture(capture)['bandwidth_result']
                self.assertEqual(math_call.call_count, 1)
                self.assertEqual(result['status'], 'incomplete')
                self.assertEqual(result['reason_codes'], reasons)
                for key in ['left_offset_hz', 'right_offset_hz', 'bandwidth_hz', 'margin_hz', 'conditional_comparison']:
                    self.assertIsNone(result[key])

    def test_host_expectations_are_not_inferred_from_matching_forged_capture_and_event(self):
        for key in ['run_id', 'runtime_instance_id', 'source_id', 'profile_id']:
            with self.subTest(key=key):
                capture, event = deepcopy((self.capture, self.event))
                capture[key] = 'another-valid-id'
                if key in ['run_id', 'runtime_instance_id']:
                    event[key] = capture[key]
                else:
                    event['payload']['observation']['devices']['analyzer'][
                        'device_id' if key == 'source_id' else 'profile_id'] = capture[key]
                capture['observation_sha256'] = sha(event)
                self.assert_rejected_before_math(capture, event)

    def test_wrong_capture_event_or_trace_hash_is_rejected_before_math(self):
        for key in ['observation_sha256', 'trace_sha256', 'observation_event_id']:
            capture = deepcopy(self.capture); capture[key] = 'a' * 64 if 'sha256' in key else 'event:1'
            self.assert_rejected_before_math(capture)
        capture = deepcopy(self.capture); capture['trace']['relative_levels_db'][0] = -7
        self.assert_rejected_before_math(capture)

    def test_capture_context_keys_types_flags_origin_and_public_identifiers_are_exact(self):
        for change in [{'schema_version': True}, {'schema_version': 1.0}, {'synthetic': 1}, {'synthetic': False},
                       {'kind': 'observed_rf_trace'}, {'capture_origin': 'time_envelope'},
                       {'capture_id': '../CANARY_PRIVATE'}, {'capture_id': '한글'}, {'source_id': True},
                       {'profile_id': 'A' * 129}, {'authorControl': {'seed': 'CANARY_PRIVATE'}},
                       {'run_id': []}, {'trace_sha256': 'A' * 64}, {'acquisition_tick': True}]:
            capture = deepcopy(self.capture); capture.update(change); self.assert_rejected_before_math(capture)
        for change in [{'minimum_acquisition_tick': True}, {'minimum_acquisition_tick': -1},
                       {'run_id': ''}, {'source_id': []}, {'case_id': 'CANARY_PRIVATE'}]:
            context = deepcopy(self.context); context.update(change); self.assert_rejected_before_math(context=context)
        for key in list(self.capture):
            capture = deepcopy(self.capture); del capture[key]; self.assert_rejected_before_math(capture)
        for key in list(self.context):
            context = deepcopy(self.context); del context[key]; self.assert_rejected_before_math(context=context)

    def test_top_level_non_objects_are_rejected_before_math(self):
        for value in [None, [], 'CANARY_PRIVATE', True]:
            self.assert_rejected_before_math(capture=value)
            self.assert_rejected_before_math(event=value)
            self.assert_rejected_before_math(context=value)

    def test_event_schema_sequence_type_payload_and_ids_are_exact(self):
        for change in [{'schema_version': True}, {'kind': 'receipt'}, {'type': 'receipt'}, {'sequence': True},
                       {'sequence': 0}, {'sequence': 99}, {'event_id': 'event:999'}, {'synthetic': True}, {'payload': []}]:
            event = deepcopy(self.event); event.update(change)
            capture = deepcopy(self.capture); capture['observation_sha256'] = sha(event)
            self.assert_rejected_before_math(capture, event)
        event = deepcopy(self.event); event['payload']['extra'] = 'CANARY_PRIVATE'
        capture = deepcopy(self.capture); capture['observation_sha256'] = sha(event)
        self.assert_rejected_before_math(capture, event)

    def test_current_core_and_node_clocks_flags_and_shape_must_match(self):
        for layer, key, value in [('observation', 'tick', True), ('observation', 'setup_revision', -1),
                ('observation', 'synthetic', False), ('observation', 'hardware_verified', True),
                ('node', 'tick', 14), ('node', 'setup_revision', 14), ('node', 'synthetic', 1),
                ('node', 'hardware_verified', 0), ('node', 'role', 'power_sensor'),
                ('node', 'status', 'pending'), ('node', 'status', 'disconnected')]:
            with self.subTest(layer=layer, key=key):
                event = deepcopy(self.event); observation = event['payload']['observation']
                selected = observation if layer == 'observation' else observation['devices']['analyzer']
                selected[key] = value
                capture = deepcopy(self.capture); capture['observation_sha256'] = sha(event)
                self.assert_rejected_before_math(capture, event)

    def test_scalar_measurement_is_valid_current_dbm_from_the_selected_source(self):
        for key, value in [('status', 'invalid'), ('valid', 1), ('valid', False), ('source_id', 'sensor'),
                           ('unit', 'dBm/Hz'), ('quantity', 'time_average'), ('value', True),
                           ('value', ['CANARY_PRIVATE']), ('value', 'CANARY_PRIVATE')]:
            event = deepcopy(self.event)
            event['payload']['observation']['devices']['analyzer']['values']['outputs']['measurement'][key] = value
            capture = deepcopy(self.capture); capture['observation_sha256'] = sha(event)
            self.assert_rejected_before_math(capture, event)

    def test_stale_future_and_capture_acquisition_mismatch_are_rejected(self):
        for field, value in [('acquisition_tick', 13), ('acquisition_tick', 16), ('acquisition_tick', True),
                              ('acquisition_setup_revision', 14), ('acquisition_setup_revision', True)]:
            event = deepcopy(self.event)
            event['payload']['observation']['devices']['analyzer']['values']['outputs']['measurement'][field] = value
            capture = deepcopy(self.capture); capture[field] = value; capture['observation_sha256'] = sha(event)
            self.assert_rejected_before_math(capture, event)
        capture = deepcopy(self.capture); capture['acquisition_tick'] -= 1
        self.assert_rejected_before_math(capture)

    def test_configuration_drift_pending_completion_or_missing_measurement_is_rejected(self):
        for key, value in [('configuration_revision', 2), ('configuration_revision', True),
                           ('operation_complete', False), ('operation_complete', 1), ('outputs', {})]:
            event = deepcopy(self.event)
            event['payload']['observation']['devices']['analyzer']['values'][key] = value
            capture = deepcopy(self.capture); capture['observation_sha256'] = sha(event)
            self.assert_rejected_before_math(capture, event)

    def test_trace_must_be_explicit_frequency_input_and_validated_before_math(self):
        changes = [{'axis_domain': 'time_s'}, {'sample_unit': 'dBm'}, {'frequency_offsets_hz': [0, 0, 1]},
                   {'frequency_offsets_hz': [0, 1], 'relative_levels_db': [-6, 0]},
                   {'relative_levels_db': [-6, True, -6]}, {'relative_levels_db': [-7, -1, -7]},
                   {'capture_id': 'different'}, {'nominal_bandwidth_hz': 20e6}]
        for change in changes:
            capture = deepcopy(self.capture); capture['trace'].update(change); capture['trace_sha256'] = sha(capture['trace'])
            self.assert_rejected_before_math(capture)

    def test_unsupported_nonfinite_non_utf8_cyclic_and_deep_json_are_sanitized(self):
        values = []
        for bad in [math.nan, math.inf, -math.inf, '\ud800', object()]:
            event = deepcopy(self.event); event['payload']['observation']['devices']['analyzer']['values']['reason'] = bad
            values.append(event)
        event = deepcopy(self.event); event[1] = 'CANARY_PRIVATE'; values.append(event)
        event = deepcopy(self.event); event['cycle'] = event; values.append(event)
        event = deepcopy(self.event); deep = None
        for _ in range(40): deep = [deep]
        event['deep'] = deep; values.append(event)
        for event in values:
            self.assert_rejected_before_math(event=event)

    def test_current_event_exactly_four_mib_is_allowed_and_one_byte_more_is_rejected(self):
        event = deepcopy(self.event)
        values = event['payload']['observation']['devices']['analyzer']['values']
        values['reason'] = ''
        values['reason'] = 'x' * (LIMIT - len(canonical(event)))
        self.assertEqual(len(canonical(event)), LIMIT)
        capture = deepcopy(self.capture); capture['observation_sha256'] = sha(event)
        self.assertEqual(self.run_capture(capture, event)['bandwidth_result']['bandwidth_hz'], 500000)
        values['reason'] += 'x'; capture['observation_sha256'] = sha(event)
        self.assert_rejected_before_math(capture, event)

    def test_capture_over_four_mib_is_rejected_even_when_its_trace_is_structurally_valid(self):
        trace = declared_trace(list(range(10 ** 100, 10 ** 100 + 65536)), [-12] * 65536)
        trace['relative_levels_db'][32767:32770] = [-6, 0, -6]
        capture = deepcopy(self.capture); capture.update(trace=trace, trace_sha256=sha(trace))
        self.assertGreater(len(canonical(capture)), LIMIT)
        self.assert_rejected_before_math(capture)

    def test_input_snapshots_remain_consistent_if_caller_mutates_originals_during_math(self):
        originals = deepcopy((self.capture, self.event, self.context)); expected_hash = sha(self.capture)
        def mutate_then_calculate(trace):
            self.capture['source_id'] = 'CANARY_PRIVATE'
            self.event.clear(); self.context.clear()
            return analyze_6db_bandwidth(trace)
        with patch.object(self.module, 'analyze_6db_bandwidth', side_effect=mutate_then_calculate):
            result = self.run_capture()
        self.assertEqual(result['binding']['source_id'], 'analyzer')
        self.assertEqual(result['binding']['capture_sha256'], expected_hash)
        self.assertNotIn('CANARY_PRIVATE', json.dumps(result))
        capture, event, context = originals
        before = deepcopy(originals); self.run_capture(capture, event, context)
        self.assertEqual((capture, event, context), before)

    def test_output_does_not_alias_inputs_the_calculator_or_future_results(self):
        calculated = analyze_6db_bandwidth(self.capture['trace']); before = deepcopy(calculated)
        with patch.object(self.module, 'analyze_6db_bandwidth', return_value=calculated):
            first = self.run_capture(); first['bandwidth_result']['reason_codes'].append('caller-change')
            first['binding']['source_id'] = 'caller-change'
            self.assertEqual(calculated, before)
            self.assertEqual(self.run_capture()['bandwidth_result']['reason_codes'], [])

    def test_bridge_calls_no_file_database_network_clock_or_runtime_operations(self):
        import pathlib
        import socket
        import sqlite3
        import time
        fleet = self.fixture[3]; before = fleet.observations()
        with ExitStack() as stack:
            for name in ['builtins.open', 'pathlib.Path.open', 'socket.socket', 'sqlite3.connect', 'time.time', 'time.monotonic']:
                stack.enter_context(patch(name, side_effect=AssertionError('unexpected side effect')))
            for name in ['execute', 'advance', 'observations']:
                stack.enter_context(patch.object(fleet, name, side_effect=AssertionError('runtime operation')))
            self.assertEqual(self.run_capture()['binding']['source_id'], 'analyzer')
        self.assertEqual(fleet.observations(), before)

    def test_returned_math_schema_cannot_smuggle_private_nested_values_or_wrong_binding(self):
        original = analyze_6db_bandwidth(self.capture['trace'])
        for change in [{'left_offset_hz': {'authorControl': 'CANARY_PRIVATE'}},
                       {'capture_id': 'another'}, {'input_sha256': 'a' * 64},
                       {'authorControl': 'CANARY_PRIVATE'}, {'synthetic': False}]:
            value = deepcopy(original); value.update(change)
            with patch.object(self.module, 'analyze_6db_bandwidth', return_value=value) as math_call:
                with self.assertRaises(ValueError) as caught:
                    self.run_capture()
            self.assertEqual(math_call.call_count, 1)
            self.assertNotIn('CANARY_PRIVATE', str(caught.exception))

    def test_calculation_failure_is_not_retried_and_private_exception_is_sanitized(self):
        for error in [ValueError('CANARY_PRIVATE'), RuntimeError('CANARY_PRIVATE'), ValueError('numeric_result_out_of_range')]:
            with patch.object(self.module, 'analyze_6db_bandwidth', side_effect=error) as math_call:
                with self.assertRaises(ValueError) as caught:
                    self.run_capture()
            self.assertEqual(math_call.call_count, 1)
            self.assertNotIn('CANARY_PRIVATE', str(caught.exception))
            if error.args == ('numeric_result_out_of_range',):
                self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')

    def test_scalar_zero_and_different_nominal_bandwidth_do_not_change_the_declared_trace(self):
        self.packet()['value'] = 0.0
        self.node()['values']['configuration']['bandwidth_hz'] = 1
        self.node()['values']['reason'] = 'CANARY_PRIVATE'
        self.rehash()
        result = self.run_capture()
        self.assertEqual(result['bandwidth_result']['bandwidth_hz'], 500000)
        text = json.dumps(result)
        for forbidden in ['CANARY_PRIVATE', 'frequency_offsets_hz', 'relative_levels_db', 'measurement', 'configuration']:
            self.assertNotIn('"' + forbidden + '"', text)


if __name__ == '__main__':
    unittest.main()
