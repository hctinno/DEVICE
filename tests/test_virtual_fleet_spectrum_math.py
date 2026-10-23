from copy import deepcopy
from contextlib import ExitStack
import hashlib
import importlib
import importlib.util
import json
import math
import unittest
from unittest.mock import patch


def trace(offsets=None, levels=None, **changes):
    value = {
        'schema_version': 1, 'kind': 'synthetic_frequency_spectrum', 'capture_id': 'capture-1',
        'synthetic': True, 'axis_domain': 'frequency_offset_hz', 'sample_unit': 'dB',
        'amplitude_basis': 'relative_to_peak',
        'selection_policy': 'unique_peak_single_lobe_linear_db',
        'frequency_offsets_hz': [-250000, 0, 250000] if offsets is None else offsets,
        'relative_levels_db': [-6, 0, -6] if levels is None else levels,
    }
    value.update(changes)
    return value


def input_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                     separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def psd_sample(**changes):
    value = {
        'schema_version': 1, 'kind': 'synthetic_psd_input', 'capture_id': 'band-1',
        'synthetic': True, 'reference_plane': 'dut_output', 'time_basis': 'on_interval',
        'output_power_method': 'on_mean', 'psd_power_method': 'on_mean',
        'path_correction_state': 'already_applied', 'input_basis': 'band_power_3khz', 'power_dbm': 0,
    }
    value.update(changes)
    return value


def density_sample(value, **changes):
    source = psd_sample(input_basis='flat_density_mw_per_hz', **changes)
    del source['power_dbm']
    source['density_mw_per_hz'] = value
    return source


class MathTestCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_fleet.spectrum_math'),
                             'the pure synthetic spectrum API has not been implemented')
        self.module = importlib.import_module('labflow.virtual_fleet.spectrum_math')

    def assert_public(self, result, source):
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['capture_id'], source['capture_id'])
        self.assertEqual(result['input_sha256'], input_hash(source))
        self.assertIs(result['synthetic'], True)
        self.assertIs(result['hardware_verified'], False)
        self.assertIs(result['ai_model_called'], False)
        self.assertEqual(result['method_approval'], 'not_assessed')
        self.assertIs(result['regulatory_scope_complete'], False)
        json.dumps(result, allow_nan=False)

    def assert_rejected(self, function, values):
        for index, value in enumerate(values):
            with self.subTest(index=index):
                with self.assertRaises(ValueError) as caught:
                    function(value)
                self.assertNotIn('CANARY_PRIVATE', str(caught.exception))


class BandwidthMathTests(MathTestCase):
    def test_exact_half_megahertz_boundary_has_exact_public_contract(self):
        source = trace()
        result = self.module.analyze_6db_bandwidth(source)
        self.assertEqual(set(result), set('schema_version kind capture_id input_sha256 algorithm_id status '
            'reason_codes left_offset_hz right_offset_hz bandwidth_hz minimum_bandwidth_hz margin_hz '
            'conditional_comparison synthetic hardware_verified ai_model_called method_approval '
            'regulatory_scope_complete'.split()))
        self.assert_public(result, source)
        self.assertEqual(result['kind'], 'synthetic_bandwidth_result')
        self.assertEqual(result['algorithm_id'], 'peak6_linear_db_v1')
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['reason_codes'], [])
        self.assertEqual(result['left_offset_hz'], -250000)
        self.assertEqual(result['right_offset_hz'], 250000)
        self.assertEqual(result['bandwidth_hz'], 500000)
        self.assertEqual(result['minimum_bandwidth_hz'], 500000)
        self.assertEqual(result['margin_hz'], 0)
        self.assertEqual(result['conditional_comparison'], 'meets')

    def test_width_below_and_above_declared_boundary(self):
        for half, width, margin, comparison in [(249999.5, 499999, -1, 'below'),
                                                 (300000, 600000, 100000, 'meets')]:
            with self.subTest(half=half):
                result = self.module.analyze_6db_bandwidth(trace([-half, 0, half]))
                self.assertEqual(result['bandwidth_hz'], width)
                self.assertEqual(result['margin_hz'], margin)
                self.assertEqual(result['conditional_comparison'], comparison)

    def test_irregular_bins_use_linear_db_interpolation(self):
        source = trace([-1000000, -100000, 0, 300000, 1000000], [-10, -4, 0, -3, -9])
        result = self.module.analyze_6db_bandwidth(source)
        self.assertAlmostEqual(result['left_offset_hz'], -400000)
        self.assertAlmostEqual(result['right_offset_hz'], 650000)
        self.assertAlmostEqual(result['bandwidth_hz'], 1050000)
        self.assertAlmostEqual(result['margin_hz'], 550000)

    def test_exact_threshold_points_inside_trace_are_not_interpolated_again(self):
        result = self.module.analyze_6db_bandwidth(
            trace([-1000000, -250000, 0, 250000, 1000000], [-50, -6, 0, -6, -50]))
        self.assertEqual(result['left_offset_hz'], -250000)
        self.assertEqual(result['right_offset_hz'], 250000)
        self.assertEqual(result['bandwidth_hz'], 500000)

    def test_missing_left_right_or_both_crossings_remain_incomplete(self):
        for levels, reasons in [([-3, 0, -8], ['left_crossing_missing']),
                                ([-8, 0, -3], ['right_crossing_missing']),
                                ([-3, 0, -3], ['left_crossing_missing', 'right_crossing_missing'])]:
            with self.subTest(reasons=reasons):
                source = trace(levels=levels)
                self.assert_incomplete(source, reasons)

    def assert_incomplete(self, source, reasons):
        result = self.module.analyze_6db_bandwidth(source)
        self.assert_public(result, source)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['reason_codes'], reasons)
        for field in ['left_offset_hz', 'right_offset_hz', 'bandwidth_hz', 'margin_hz',
                      'conditional_comparison']:
            self.assertIsNone(result[field], field)

    def test_equal_global_peaks_remain_incomplete(self):
        self.assert_incomplete(trace([-2, -1, 0, 1, 2], [-10, 0, -3, 0, -10]), ['non_unique_peak'])

    def test_separate_threshold_lobe_is_not_silently_selected_or_merged(self):
        self.assert_incomplete(trace([-2, -1, 0, 1, 2], [-8, -5, -8, 0, -8]), ['disconnected_lobes'])

    def test_two_adjacent_threshold_samples_are_an_ambiguous_plateau(self):
        self.assert_incomplete(trace([-3, -2, -1, 0, 1, 2, 3], [-10, -6, -6, 0, -6, -8, -10]),
                               ['threshold_plateau'])

    def test_ambiguity_reasons_have_fixed_order_without_selecting_crossings(self):
        self.assert_incomplete(trace([-3, -2, -1, 0, 1, 2, 3], [0, -6, -6, -8, 0, -8, -10]),
                               ['non_unique_peak', 'disconnected_lobes', 'threshold_plateau'])

    def test_time_axis_unknown_units_wrong_basis_and_extra_private_fields_are_rejected(self):
        changes = [{'schema_version': True}, {'schema_version': 1.0}, {'kind': 'time_envelope'},
                   {'synthetic': False}, {'synthetic': 1}, {'axis_domain': 'time_s'},
                   {'sample_unit': 'dBm'}, {'sample_unit': 'W'}, {'amplitude_basis': 'absolute'},
                   {'selection_policy': 'largest_lobe'}, {'source_path': 'CANARY_PRIVATE'},
                   {'capture_id': '../CANARY_PRIVATE'}, {'capture_id': '한글'}, {'capture_id': 'x' * 129}]
        values = [trace(**change) for change in changes]
        missing = trace(); del missing['sample_unit']; values.append(missing)
        self.assert_rejected(self.module.analyze_6db_bandwidth, values + [None, [], 'CANARY_PRIVATE', 1])

    def test_axis_must_already_be_strictly_increasing_with_matching_array_lengths(self):
        values = [trace([1, 0, 2]), trace([0, 0, 1]), trace([0, 1]), trace([0, 1, 2, 3]),
                  trace((0, 1, 2)), trace([0, 1, 2], [-6, 0]), trace([0, 1, 2], (-6, 0, -6))]
        self.assert_rejected(self.module.analyze_6db_bandwidth, values)

    def test_non_numeric_boolean_nonfinite_and_unrepresentable_inputs_are_rejected(self):
        values = []
        for bad in [True, False, 'CANARY_PRIVATE', {}, [], None, math.nan, math.inf, -math.inf, 10 ** 1000]:
            values.extend([trace([-1, bad, 1]), trace(levels=[-6, 0, bad])])
        values.extend([trace(levels=[-6, 1, -6]), trace(levels=[-7, -1, -7])])
        self.assert_rejected(self.module.analyze_6db_bandwidth, values)

    def test_size_limit_accepts_65536_samples_and_rejects_an_extra_bin(self):
        offsets = list(range(65536)); levels = [-12] * 65536
        levels[32767:32770] = [-6, 0, -6]
        result = self.module.analyze_6db_bandwidth(trace(offsets, levels))
        self.assertEqual(result['bandwidth_hz'], 2)
        self.assert_rejected(self.module.analyze_6db_bandwidth,
                             [trace(offsets + [65536], levels + [-12])])

    def test_large_intermediate_axis_span_does_not_overflow_a_finite_result(self):
        result = self.module.analyze_6db_bandwidth(trace([-1e308, -9e307, 1e308], [-12, 0, -12]))
        self.assertTrue(math.isclose(result['left_offset_hz'], -9.5e307))
        self.assertTrue(math.isclose(result['right_offset_hz'], 5e306))
        self.assertTrue(math.isclose(result['bandwidth_hz'], 1e308))
        json.dumps(result, allow_nan=False)

    def test_width_overflow_and_unrepresentable_positive_width_are_sanitized_errors(self):
        self.assert_rejected(self.module.analyze_6db_bandwidth,
            [trace([-1e308, 0, 1e308]), trace([1e308, 1.1e308, 1.2e308], [-1e308, 0, -1e308])])

    def test_large_absolute_axes_reject_unreliable_crossing_precision(self):
        for level in [-25.17, -25.16]:
            with self.subTest(level=level):
                source = trace([1e20 - 1048576, 1e20, 1e20 + 1048576], [level, 0, level])
                with self.assertRaises(ValueError) as caught:
                    self.module.analyze_6db_bandwidth(source)
                self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')

    def test_exact_interpolation_on_both_sides_and_at_boundary_without_cancellation(self):
        for level, width, comparison in [(-25.17, 499917.0441001192, 'below'),
                                         (-25.16, 500115.7392686804, 'meets')]:
            with self.subTest(level=level):
                result = self.module.analyze_6db_bandwidth(trace([-1048576, 0, 1048576], [level, 0, level]))
                self.assertAlmostEqual(result['bandwidth_hz'], width, places=6)
                self.assertEqual(result['conditional_comparison'], comparison)
        exact = self.module.analyze_6db_bandwidth(trace([-500000, 0, 500000], [-12, 0, -12]))
        self.assertEqual(exact['bandwidth_hz'], 500000)
        self.assertEqual(exact['margin_hz'], 0)
        self.assertEqual(exact['conditional_comparison'], 'meets')

    def test_below_boundary_width_rounding_up_to_limit_is_a_representation_error(self):
        source = trace([-20000, 0, 980000], [math.nextafter(-12, -math.inf), 0, -12])
        with self.assertRaises(ValueError) as caught:
            self.module.analyze_6db_bandwidth(source)
        self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')

    def test_input_hash_tracks_declared_values_and_inputs_and_results_are_independent(self):
        source = trace(capture_id='A' * 128); before = deepcopy(source)
        first = self.module.analyze_6db_bandwidth(source)
        self.assertEqual(source, before)
        first['reason_codes'].append('caller-change')
        second = self.module.analyze_6db_bandwidth(source)
        self.assertEqual(second['reason_codes'], [])
        self.assertEqual(second['input_sha256'], input_hash(before))
        changed = deepcopy(source); changed['relative_levels_db'][0] = -7
        self.assertNotEqual(self.module.analyze_6db_bandwidth(changed)['input_sha256'], second['input_sha256'])


class PSDMathTests(MathTestCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(callable(getattr(self.module, 'analyze_psd_band', None)),
                        'the declared 3 kHz PSD API has not been implemented')

    def test_zero_dbm_is_one_milliwatt_with_exact_public_contract(self):
        source = psd_sample()
        result = self.module.analyze_psd_band(source)
        self.assertEqual(set(result), set('schema_version kind capture_id input_sha256 algorithm_id input_basis '
            'power_dbm power_mw reference_bandwidth_hz maximum_dbm margin_db conditional_comparison '
            'source_coverage max_search_complete synthetic hardware_verified ai_model_called method_approval '
            'regulatory_scope_complete'.split()))
        self.assert_public(result, source)
        self.assertEqual(result['kind'], 'synthetic_psd_band_result')
        self.assertEqual(result['algorithm_id'], 'declared_3khz_power_v1')
        self.assertEqual(result['input_basis'], 'band_power_3khz')
        self.assertEqual(result['power_dbm'], 0)
        self.assertEqual(result['power_mw'], 1)
        self.assertEqual(result['reference_bandwidth_hz'], 3000)
        self.assertEqual(result['maximum_dbm'], 8)
        self.assertEqual(result['margin_db'], 8)
        self.assertEqual(result['conditional_comparison'], 'meets')
        self.assertEqual(result['source_coverage'], 'single_declared_band')
        self.assertIs(result['max_search_complete'], False)

    def test_eight_dbm_and_the_next_larger_float_have_different_conditional_results(self):
        exact = self.module.analyze_psd_band(psd_sample(power_dbm=8))
        self.assertAlmostEqual(exact['power_mw'], 6.309573444801933)
        self.assertEqual(exact['margin_db'], 0)
        self.assertEqual(exact['conditional_comparison'], 'meets')
        above = self.module.analyze_psd_band(psd_sample(power_dbm=math.nextafter(8, math.inf)))
        self.assertLess(above['margin_db'], 0)
        self.assertEqual(above['conditional_comparison'], 'above')

    def test_band_power_range_endpoints_keep_negative_power_and_finite_results(self):
        for power, mw, margin, comparison in [(-300, 1e-30, 308, 'meets'), (100, 1e10, -92, 'above')]:
            with self.subTest(power=power):
                source = psd_sample(power_dbm=power)
                result = self.module.analyze_psd_band(source)
                self.assert_public(result, source)
                self.assertEqual(result['power_dbm'], power)
                self.assertEqual(result['power_mw'], mw)
                self.assertEqual(result['margin_db'], margin)
                self.assertEqual(result['conditional_comparison'], comparison)

    def test_matching_on_mean_or_peak_methods_are_supported(self):
        for method in ['on_mean', 'peak']:
            source = psd_sample(output_power_method=method, psd_power_method=method)
            self.assertEqual(self.module.analyze_psd_band(source)['power_mw'], 1)

    def test_flat_density_is_integrated_over_three_kilohertz(self):
        source = density_sample(0.002)
        result = self.module.analyze_psd_band(source)
        self.assert_public(result, source)
        self.assertEqual(result['input_basis'], 'flat_density_mw_per_hz')
        self.assertEqual(result['power_mw'], 6)
        self.assertAlmostEqual(result['power_dbm'], 7.781512503836437)
        self.assertAlmostEqual(result['margin_db'], 0.218487496163563)
        self.assertEqual(result['conditional_comparison'], 'meets')

    def test_flat_density_above_declared_limit_is_not_reported_as_band_search_complete(self):
        result = self.module.analyze_psd_band(density_sample(0.01))
        self.assertEqual(result['power_mw'], 30)
        self.assertAlmostEqual(result['power_dbm'], 14.771212547196624)
        self.assertEqual(result['conditional_comparison'], 'above')
        self.assertLess(result['margin_db'], 0)
        self.assertIs(result['max_search_complete'], False)

    def test_smallest_positive_density_is_not_mistaken_for_absence_or_band_dbm_range(self):
        source = density_sample(math.ulp(0.0))
        result = self.module.analyze_psd_band(source)
        self.assert_public(result, source)
        self.assertGreater(result['power_mw'], 0)
        self.assertLess(result['power_dbm'], -300)
        self.assertTrue(math.isfinite(result['power_dbm']))

    def test_density_integral_overflow_has_a_sanitized_numeric_error(self):
        with self.assertRaises(ValueError) as caught:
            self.module.analyze_psd_band(density_sample(1e308))
        self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')

    def test_density_rounded_to_eight_dbm_keeps_its_true_above_comparison(self):
        result = self.module.analyze_psd_band(density_sample(0.002103191148267311))
        self.assertEqual(result['power_dbm'], 8.0)
        self.assertEqual(result['conditional_comparison'], 'above')
        self.assertLess(result['margin_db'], 0)
        self.assertAlmostEqual(result['margin_db'], -5.622003640353109e-16, delta=1e-29)

    def test_adjacent_density_values_keep_signed_unrounded_margins(self):
        middle = 0.002103191148267311
        for density, comparison, sign in [(math.nextafter(middle, -math.inf), 'meets', 1),
                                          (math.nextafter(middle, math.inf), 'above', -1)]:
            with self.subTest(density=density):
                result = self.module.analyze_psd_band(density_sample(density))
                self.assertEqual(result['conditional_comparison'], comparison)
                self.assertGreater(sign * result['margin_db'], 0)
        for power, comparison, sign in [(math.nextafter(8, -math.inf), 'meets', 1),
                                        (math.nextafter(8, math.inf), 'above', -1)]:
            result = self.module.analyze_psd_band(psd_sample(power_dbm=power))
            self.assertEqual(result['conditional_comparison'], comparison)
            self.assertGreater(sign * result['margin_db'], 0)
        exact = self.module.analyze_psd_band(psd_sample(power_dbm=8))
        self.assertEqual(exact['conditional_comparison'], 'meets')
        self.assertEqual(exact['margin_db'], 0)

    def test_invalid_power_density_boolean_nonfinite_and_out_of_range_are_rejected(self):
        bad = [True, False, 'CANARY_PRIVATE', {}, [], None, math.nan, math.inf, -math.inf, 10 ** 1000]
        values = [psd_sample(power_dbm=value) for value in bad + [-300.1, 100.1]]
        values += [density_sample(value) for value in bad + [0, -1]]
        self.assert_rejected(self.module.analyze_psd_band, values)

    def test_method_mismatch_cycle_unknown_plane_or_unapplied_correction_is_rejected(self):
        changes = [{'output_power_method': 'peak'}, {'psd_power_method': 'peak'},
                   {'output_power_method': 'cycle_mean', 'psd_power_method': 'cycle_mean'},
                   {'output_power_method': None}, {'psd_power_method': ['CANARY_PRIVATE']},
                   {'time_basis': 'cycle'}, {'time_basis': 'unknown'},
                   {'reference_plane': 'sensor_input'}, {'path_correction_state': 'unapplied'}]
        self.assert_rejected(self.module.analyze_psd_band, [psd_sample(**change) for change in changes])

    def test_rbw_enbw_duty_spectrum_and_extra_correction_fields_are_not_guessed(self):
        fields = ['rbw_hz', 'enbw_hz', 'duty_cycle', 'duty_correction_db', 'attenuation_db',
                  'spectrum', 'overlapping_bins', 'source_path']
        self.assert_rejected(self.module.analyze_psd_band,
                             [psd_sample(**{name: 'CANARY_PRIVATE'}) for name in fields])

    def test_schema_basis_and_value_key_must_match_exactly(self):
        values = [psd_sample(schema_version=True), psd_sample(schema_version=1.0),
                  psd_sample(kind='real_psd'), psd_sample(synthetic=False), psd_sample(synthetic=1),
                  psd_sample(input_basis='sa_amplitude_rbw'), psd_sample(input_basis=['CANARY_PRIVATE']),
                  psd_sample(density_mw_per_hz=0.001), psd_sample(input_basis='flat_density_mw_per_hz')]
        for field in ['time_basis', 'reference_plane', 'power_dbm', 'psd_power_method']:
            source = psd_sample(); del source[field]; values.append(source)
        self.assert_rejected(self.module.analyze_psd_band, values + [None, [], 'CANARY_PRIVATE', 1])

    def test_capture_id_and_hash_are_public_bounded_immutable_and_input_specific(self):
        source = psd_sample(capture_id='A' * 128); before = deepcopy(source)
        result = self.module.analyze_psd_band(source)
        self.assertEqual(source, before)
        self.assert_public(result, source)
        changed = psd_sample(capture_id='A' * 128, power_dbm=1)
        self.assertNotEqual(result['input_sha256'], self.module.analyze_psd_band(changed)['input_sha256'])
        self.assert_rejected(self.module.analyze_psd_band,
            [psd_sample(capture_id=value) for value in ['', ' ', '../CANARY_PRIVATE', '한글', 'A' * 129, True]])


class PureMathTests(MathTestCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(callable(getattr(self.module, 'analyze_psd_band', None)),
                        'both pure APIs are required for side-effect and identity checks')

    def test_calculations_need_no_file_database_network_or_clock_and_are_repeatable(self):
        import pathlib
        import socket
        import sqlite3
        import time
        sources = [trace(), psd_sample(), density_sample(0.002)]
        before = deepcopy(sources)
        with ExitStack() as stack:
            for operation in ['builtins.open', 'pathlib.Path.open', 'socket.socket',
                              'sqlite3.connect', 'time.time', 'time.monotonic']:
                stack.enter_context(patch(operation, side_effect=AssertionError('unexpected side effect')))
            results = [self.module.analyze_6db_bandwidth(sources[0]),
                       self.module.analyze_psd_band(sources[1]), self.module.analyze_psd_band(sources[2])]
            self.assertEqual(results, [self.module.analyze_6db_bandwidth(sources[0]),
                self.module.analyze_psd_band(sources[1]), self.module.analyze_psd_band(sources[2])])
        self.assertEqual(sources, before)

    def test_hash_ignores_object_key_order_but_preserves_declared_json_number_representation(self):
        for source, function in [(trace(), self.module.analyze_6db_bandwidth),
                                 (psd_sample(), self.module.analyze_psd_band)]:
            reverse = dict(reversed(list(source.items())))
            self.assertEqual(function(source)['input_sha256'], function(reverse)['input_sha256'])
            changed = deepcopy(source)
            if 'power_dbm' in changed:
                changed['power_dbm'] = 0.0
            else:
                changed['frequency_offsets_hz'][1] = 0.0
            self.assertNotEqual(function(source)['input_sha256'], function(changed)['input_sha256'])

    def test_precision_does_not_depend_on_or_modify_the_callers_decimal_context(self):
        from decimal import Inexact, ROUND_DOWN, localcontext
        with localcontext() as caller:
            caller.prec = 5
            caller.rounding = ROUND_DOWN
            caller.traps[Inexact] = True
            result = self.module.analyze_psd_band(density_sample(0.002103191148267311))
            self.assertEqual(result['conditional_comparison'], 'above')
            self.assertLess(result['margin_db'], 0)
            self.assertEqual(caller.prec, 5)
            self.assertEqual(caller.rounding, ROUND_DOWN)
            self.assertIs(caller.traps[Inexact], True)


if __name__ == '__main__':
    unittest.main()
