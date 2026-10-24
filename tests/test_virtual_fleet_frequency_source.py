from contextlib import ExitStack
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib
import importlib.util
import json
import math
import unittest
from unittest.mock import patch

from labflow.virtual_fleet.spectrum_math import analyze_6db_bandwidth


def source(offsets=None, densities=None, **changes):
    value = {'schema_version': 1, 'kind': 'synthetic_piecewise_density_source',
        'source_id': 'frequency-source-1', 'declared_mode_id': 'declared-mode-1', 'synthetic': True,
        'center_hz': 2450000000, 'reference_plane': 'dut_output', 'time_basis': 'on_interval',
        'power_method': 'on_mean', 'interpolation': 'linear_mw_per_hz',
        'frequency_offsets_hz': [-5000, 0, 5000] if offsets is None else offsets,
        'density_mw_per_hz': [0.25, 1.0, 0.25] if densities is None else densities}
    value.update(changes)
    return value


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def exact_ratio(result):
    ratio = result['exact_power_ratio']
    return Fraction(int(ratio['numerator']), int(ratio['denominator']))


def antiderivative_oracle(spec, start, stop):
    """Independent slope/intercept integration rather than endpoint trapezoids."""
    axis = [Fraction(x) for x in spec['frequency_offsets_hz']]
    density = [Fraction(y) for y in spec['density_mw_per_hz']]
    start, stop = Fraction(start), Fraction(stop)
    total = Fraction(0)
    for x0, x1, y0, y1 in zip(axis, axis[1:], density, density[1:]):
        low, high = max(start, x0), min(stop, x1)
        if high <= low:
            continue
        slope = (y1 - y0) / (x1 - x0)
        intercept = y0 - slope * x0
        total += slope * (high * high - low * low) / 2 + intercept * (high - low)
    return total


class FrequencySourceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_fleet.frequency_source'),
                             'the declared density source APIs are not implemented')
        self.module = importlib.import_module('labflow.virtual_fleet.frequency_source')
        self.assertTrue(callable(getattr(self.module, 'generate_frequency_source', None)))
        self.assertTrue(callable(getattr(self.module, 'integrate_source_3khz', None)))

    def generate(self, spec):
        return self.module.generate_frequency_source(spec)

    def integrate(self, spec, start=0):
        return self.module.integrate_source_3khz(spec, start_offset_hz=start)

    def assert_flags(self, result, spec):
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['source_id'], spec['source_id'])
        self.assertEqual(result['declared_mode_id'], spec['declared_mode_id'])
        self.assertEqual(result['input_sha256'], sha(spec))
        self.assertEqual(result['reference_plane'], 'dut_output')
        self.assertEqual(result['time_basis'], 'on_interval')
        self.assertEqual(result['power_method'], spec['power_method'])
        for key, value in {'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
            'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
            'waveform_implemented': False, 'oem_mode_verified': False}.items():
            self.assertIs(result[key], value) if type(value) is bool else self.assertEqual(result[key], value)
        json.dumps(result, allow_nan=False)

    def assert_rejected(self, values):
        for index, spec in enumerate(values):
            for function in [self.generate, self.integrate]:
                with self.subTest(index=index, function=function.__name__):
                    with self.assertRaises(ValueError) as caught:
                        function(spec)
                    self.assertNotIn('CANARY_PRIVATE', str(caught.exception))

    def test_generate_has_exact_public_source_and_existing_trace_contracts(self):
        spec = source([-1000000, 0, 1000000], [0.1, 1, 0.1])
        result = self.generate(spec)
        self.assertEqual(set(result), set('schema_version kind source_id declared_mode_id input_sha256 center_hz '
            'reference_plane time_basis power_method density_interpolation trace_projection trace synthetic '
            'hardware_verified ai_model_called method_approval regulatory_scope_complete waveform_implemented '
            'oem_mode_verified'.split()))
        self.assert_flags(result, spec)
        self.assertEqual(result['kind'], 'synthetic_frequency_source')
        self.assertEqual(result['density_interpolation'], 'linear_mw_per_hz')
        self.assertEqual(result['trace_projection'], 'knot_samples_linear_db')
        self.assertEqual(result['center_hz'], spec['center_hz'])
        trace = result['trace']
        self.assertEqual(set(trace), set('schema_version kind capture_id synthetic axis_domain sample_unit '
            'amplitude_basis selection_policy frequency_offsets_hz relative_levels_db'.split()))
        self.assertEqual(trace['capture_id'], 'fs:' + sha(spec))
        self.assertEqual(trace['kind'], 'synthetic_frequency_spectrum')
        self.assertEqual(trace['axis_domain'], 'frequency_offset_hz')
        self.assertEqual(trace['sample_unit'], 'dB')
        self.assertEqual(trace['amplitude_basis'], 'relative_to_peak')
        self.assertEqual(trace['selection_policy'], 'unique_peak_single_lobe_linear_db')
        self.assertEqual(trace['frequency_offsets_hz'], [-1000000, 0, 1000000])
        self.assertEqual(trace['relative_levels_db'], [-10, 0, -10])

    def test_integral_exact_contract_and_binary_flat_density(self):
        spec = source([-3000, 0, 6000], [1 / 1024] * 3)
        result = self.integrate(spec, -1000)
        self.assertEqual(set(result), set('schema_version kind source_id declared_mode_id input_sha256 '
            'start_offset_hz stop_offset_hz reference_bandwidth_hz reference_plane time_basis power_method '
            'power_mw exact_power_ratio source_coverage max_search_complete synthetic hardware_verified '
            'ai_model_called method_approval regulatory_scope_complete waveform_implemented oem_mode_verified'.split()))
        self.assert_flags(result, spec)
        self.assertEqual(result['kind'], 'synthetic_integrated_band_power')
        self.assertEqual(result['start_offset_hz'], -1000)
        self.assertEqual(result['stop_offset_hz'], 2000)
        self.assertEqual(result['reference_bandwidth_hz'], 3000)
        self.assertEqual(result['power_mw'], 2.9296875)
        self.assertEqual(result['exact_power_ratio'], {'numerator': '375', 'denominator': '128'})
        self.assertEqual(result['source_coverage'], 'single_declared_band')
        self.assertIs(result['max_search_complete'], False)

    def test_piecewise_triangle_clips_both_segments_with_exact_area(self):
        spec = source([-2000, 0, 2000], [0.25, 1, 0.25])
        result = self.integrate(spec, -1500)
        self.assertEqual(exact_ratio(result), Fraction(8625, 4))
        self.assertEqual(result['power_mw'], 2156.25)
        self.assertEqual(exact_ratio(result), antiderivative_oracle(spec, -1500, 1500))

    def test_asymmetric_profile_crosses_multiple_knots(self):
        spec = source([-5000, 0, 1000, 5000], [0.5, 1, 2, 0.25])
        result = self.integrate(spec, -1000)
        self.assertEqual(exact_ratio(result), Fraction(16925, 4))
        self.assertEqual(result['power_mw'], 4231.25)
        self.assertEqual(exact_ratio(result), antiderivative_oracle(spec, -1000, 2000))

    def test_float_inputs_are_integrated_as_their_exact_values_and_ratio_is_reduced(self):
        spec = source([-4000.5, -0.25, 5000.75], [0.001, 0.003, 0.002])
        result = self.integrate(spec, -123.5)
        expected = antiderivative_oracle(spec, -123.5, Fraction(-123.5) + 3000)
        self.assertEqual(exact_ratio(result), expected)
        self.assertEqual(result['power_mw'], float(expected))
        self.assertEqual(math.gcd(int(result['exact_power_ratio']['numerator']), int(result['exact_power_ratio']['denominator'])), 1)
        for value in result['exact_power_ratio'].values():
            self.assertRegex(value, r'^[1-9][0-9]*$')

    def test_domain_endpoints_are_included_but_any_clipping_is_refused(self):
        spec = source([-1500, 0, 1500], [0.5, 1, 0.5])
        self.assertEqual(exact_ratio(self.integrate(spec, -1500)), Fraction(2250))
        for start in [-1501, -1499, math.nextafter(-1500, -math.inf), math.nextafter(-1500, math.inf)]:
            with self.subTest(start=start), self.assertRaises(ValueError):
                self.integrate(spec, start)
        zero_based = source([0, 1500, 3000], [1, 1, 1])
        for start in [math.ulp(0.0), -math.ulp(0.0)]:
            with self.subTest(start=start), self.assertRaises(ValueError):
                self.integrate(zero_based, start)

    def test_adjacent_three_khz_intervals_are_additive_over_their_union(self):
        spec = source([0, 2000, 4000, 8000], [0.5, 1, 2, 0.25])
        combined = exact_ratio(self.integrate(spec, 0)) + exact_ratio(self.integrate(spec, 3000))
        self.assertEqual(combined, antiderivative_oracle(spec, 0, 6000))

    def test_splitting_linear_segments_does_not_change_the_integral(self):
        original = source([-3000, 0, 6000], [0.5, 1, 2])
        split = source([-3000, -1500, 0, 3000, 6000], [0.5, 0.75, 1, 1.5, 2])
        self.assertEqual(exact_ratio(self.integrate(original, -1000)), exact_ratio(self.integrate(split, -1000)))
        self.assertNotEqual(self.integrate(original)['input_sha256'], self.integrate(split)['input_sha256'])

    def test_density_scaling_changes_exact_power_but_not_relative_db_profile(self):
        original = source(); scaled = deepcopy(original)
        scaled['density_mw_per_hz'] = [value * 2 for value in original['density_mw_per_hz']]
        self.assertEqual(exact_ratio(self.integrate(scaled)), 2 * exact_ratio(self.integrate(original)))
        self.assertEqual(self.generate(original)['trace']['relative_levels_db'], self.generate(scaled)['trace']['relative_levels_db'])

    def test_frequency_translation_preserves_integral_without_converting_integer_offsets(self):
        original = source([-5000, 0, 5000], [0.25, 1, 0.25]); shifted = deepcopy(original)
        shift = 10 ** 20
        shifted['frequency_offsets_hz'] = [value + shift for value in original['frequency_offsets_hz']]
        result = self.integrate(shifted, shift)
        self.assertIs(type(result['start_offset_hz']), int)
        self.assertIs(type(result['stop_offset_hz']), int)
        self.assertEqual(result['stop_offset_hz'] - result['start_offset_hz'], 3000)
        self.assertEqual(exact_ratio(result), exact_ratio(self.integrate(original, 0)))

    def test_float_endpoints_that_collapse_or_distort_three_khz_are_rejected(self):
        spec = source([10 ** 20 - 10000, 10 ** 20, 10 ** 20 + 10000], [1, 1, 1])
        with self.assertRaises(ValueError) as caught:
            self.integrate(spec, 1e20)
        self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')
        large = 2 ** 63
        spec = source([large - 10000, large, large + 10000], [1, 1, 1])
        with self.assertRaises(ValueError) as caught:
            self.integrate(spec, float(large))
        self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')

    def test_start_float_is_preserved_and_tiny_display_rounding_does_not_change_exact_ratio(self):
        spec = source([-1, 1500, 4000], [0.5, 1, 2])
        start = math.ulp(0.0)
        result = self.integrate(spec, start)
        self.assertIs(type(result['start_offset_hz']), float)
        self.assertEqual(result['start_offset_hz'], start)
        self.assertEqual(result['stop_offset_hz'], 3000.0)
        self.assertEqual(exact_ratio(result), antiderivative_oracle(spec, Fraction(start), Fraction(start) + 3000))

    def test_positive_subnormal_density_integrates_without_a_zero_floor(self):
        minimum = math.ulp(0.0)
        spec = source(densities=[minimum] * 3)
        result = self.integrate(spec)
        self.assertGreater(result['power_mw'], 0)
        self.assertEqual(exact_ratio(result), Fraction(minimum) * 3000)

    def test_density_ratio_that_underflows_as_a_float_still_has_finite_db(self):
        spec = source(densities=[math.ulp(0.0), 1.0, 1e308])
        result = self.generate(spec)
        levels = result['trace']['relative_levels_db']
        self.assertLess(levels[0], -6000)
        self.assertEqual(levels[-1], 0)
        self.assertTrue(all(math.isfinite(value) for value in levels))

    def test_near_maximum_integer_densities_do_not_create_a_false_zero_peak(self):
        maximum = 10 ** 308
        result = self.generate(source(densities=[maximum - 1, maximum, maximum - 1]))
        levels = result['trace']['relative_levels_db']
        self.assertLess(levels[0], 0)
        self.assertEqual(levels[1], 0)
        self.assertEqual(levels[0], levels[2])

    def test_distinct_densities_that_merge_in_display_db_are_refused(self):
        spec = source(densities=[1e-300, math.nextafter(1e-300, math.inf), 1.0])
        with self.assertRaises(ValueError) as caught:
            self.generate(spec)
        self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')
        repeated = self.generate(source(densities=[1e-300, 1e-300, 1.0]))
        self.assertEqual(repeated['trace']['relative_levels_db'], [-3000, -3000, 0])

    def test_generate_does_not_run_bw_and_consumer_uses_db_knot_projection(self):
        spec = source([-1000000, 0, 1000000], [0.1, 1, 0.1])
        with patch('labflow.virtual_fleet.spectrum_math.analyze_6db_bandwidth', side_effect=AssertionError('BW is a caller choice')) as bw_call:
            generated = self.generate(spec)
        self.assertEqual(bw_call.call_count, 0)
        result = analyze_6db_bandwidth(generated['trace'])
        self.assertEqual(result['left_offset_hz'], -600000)
        self.assertEqual(result['right_offset_hz'], 600000)
        self.assertEqual(result['bandwidth_hz'], 1200000)
        # At +600 kHz the linear-density function is 0.46, not the -6 dB density.
        self.assertAlmostEqual(0.1 + (1 - 0.1) * 0.4, 0.46)
        self.assertGreater(10 * math.log10(0.46), -6)

    def test_multiple_maxima_and_clipped_profiles_remain_incomplete_in_bw_consumer(self):
        for densities, reasons in [([1, 1, 1], ['non_unique_peak']),
                                   ([0.5, 1, 0.5], ['left_crossing_missing', 'right_crossing_missing'])]:
            generated = self.generate(source([-1000000, 0, 1000000], densities))
            bw = analyze_6db_bandwidth(generated['trace'])
            self.assertEqual(bw['status'], 'incomplete')
            self.assertEqual(bw['reason_codes'], reasons)
            self.assertIsNone(bw['bandwidth_hz'])

    def test_mode_id_and_power_method_do_not_infer_waveform_or_scale_density(self):
        base = source(); changed = source(declared_mode_id='mode-HT20-example', power_method='peak')
        original, modified = self.generate(base), self.generate(changed)
        self.assertEqual(original['trace']['relative_levels_db'], modified['trace']['relative_levels_db'])
        self.assertEqual(exact_ratio(self.integrate(base)), exact_ratio(self.integrate(changed)))
        self.assertNotEqual(original['input_sha256'], modified['input_sha256'])
        self.assertIs(modified['waveform_implemented'], False)
        self.assertIs(modified['oem_mode_verified'], False)

    def test_exact_keys_ids_units_origin_and_supported_methods_are_required(self):
        changes = [{'schema_version': True}, {'schema_version': 1.0}, {'kind': 'measured_spectrum'},
            {'synthetic': False}, {'synthetic': 1}, {'source_id': '../CANARY_PRIVATE'},
            {'declared_mode_id': '한글'}, {'declared_mode_id': 'A' * 129}, {'center_hz': True},
            {'reference_plane': 'sensor_input'}, {'time_basis': 'cycle'}, {'power_method': 'on_average'},
            {'interpolation': 'linear_db'}, {'nominal_bandwidth_hz': 20000000},
            {'NSS': 1}, {'current_firmware': 'CANARY_PRIVATE'}, {'source_path': 'CANARY_PRIVATE'}]
        values = [source(**change) for change in changes]
        for key in source():
            value = source(); del value[key]; values.append(value)
        self.assert_rejected(values + [None, [], 'CANARY_PRIVATE', 1])
        valid = source(source_id='A' * 128, declared_mode_id='B' * 128)
        self.assertEqual(self.generate(valid)['source_id'], 'A' * 128)

    def test_axes_densities_and_lengths_are_strict_without_sorting_or_floor(self):
        values = [source([0, 0, 1]), source([0, 2, 1]), source([0, 1], [1, 1]),
            source([0, 1, 2, 3]), source((0, 1, 2)), source(densities=(1, 1, 1)),
            source(densities=[1, 0, 1]), source(densities=[1, -1, 1])]
        for bad in [True, 'CANARY_PRIVATE', None, math.nan, math.inf, -math.inf, 10 ** 1000]:
            values.extend([source([-1, bad, 1]), source(densities=[1, bad, 1]), source(center_hz=bad)])
        self.assert_rejected(values)

    def test_center_and_every_absolute_knot_must_be_positive_and_finite(self):
        self.assert_rejected([source(center_hz=0), source(center_hz=-1),
            source([-1000, 0, 1000], center_hz=1000), source([-1001, 0, 1000], center_hz=1000),
            source([-1e307, 0, 1e308], center_hz=1e308)])

    def test_point_limit_accepts_4096_and_rejects_4097(self):
        spec = source(list(range(4096)), [0.25] * 4096)
        self.assertEqual(len(self.generate(spec)['trace']['frequency_offsets_hz']), 4096)
        self.assertEqual(exact_ratio(self.integrate(spec)), Fraction(750))
        self.assert_rejected([source(list(range(4097)), [0.25] * 4097)])

    def test_bad_start_types_and_nonfinite_are_refused_without_private_error_text(self):
        for start in [True, None, 'CANARY_PRIVATE', [], math.nan, math.inf, -math.inf, 10 ** 1000]:
            with self.subTest(start_type=type(start).__name__), self.assertRaises(ValueError) as caught:
                self.integrate(source(), start)
            self.assertNotIn('CANARY_PRIVATE', str(caught.exception))

    def test_integrated_power_overflow_is_numeric_error_without_changing_the_density(self):
        spec = source(densities=[1e308] * 3); before = deepcopy(spec)
        with self.assertRaises(ValueError) as caught:
            self.integrate(spec)
        self.assertEqual(str(caught.exception), 'numeric_result_out_of_range')
        self.assertEqual(spec, before)

    def test_json_size_depth_cycles_nonstring_keys_and_invalid_unicode_are_refused(self):
        huge = source(); huge['extra'] = 'x' * (4 * 1024 * 1024)
        bad_key = source(); bad_key[1] = 'CANARY_PRIVATE'
        cycle = source(); cycle['cycle'] = cycle
        deep = source(); value = None
        for _ in range(40): value = [value]
        deep['deep'] = value
        self.assert_rejected([huge, bad_key, cycle, deep, source(declared_mode_id='\ud800')])

    def test_input_and_output_are_independent_and_hash_preserves_json_number_representation(self):
        spec = source(); before = deepcopy(spec); first = self.generate(spec); integral = self.integrate(spec)
        self.assertEqual(spec, before)
        first['trace']['frequency_offsets_hz'][0] = -1
        first['trace']['relative_levels_db'][0] = 123
        integral['exact_power_ratio']['numerator'] = '1'
        self.assertEqual(spec, before)
        self.assertEqual(self.generate(spec)['trace']['frequency_offsets_hz'], before['frequency_offsets_hz'])
        self.assertNotEqual(self.integrate(spec)['exact_power_ratio'], integral['exact_power_ratio'])
        reversed_keys = dict(reversed(list(spec.items())))
        self.assertEqual(self.generate(reversed_keys)['input_sha256'], sha(before))
        changed = deepcopy(spec); changed['center_hz'] = float(changed['center_hz'])
        self.assertNotEqual(self.generate(changed)['input_sha256'], sha(before))

    def test_decimal_precision_rounding_traps_and_flags_are_preserved(self):
        from decimal import Inexact, ROUND_DOWN, localcontext
        with localcontext() as caller:
            caller.prec = 5; caller.rounding = ROUND_DOWN
            caller.traps[Inexact] = True; caller.flags[Inexact] = True
            flags = dict(caller.flags)
            result = self.generate(source())
            self.assertEqual(result['trace']['relative_levels_db'], [-6.020599913279624, 0, -6.020599913279624])
            self.integrate(source())
            self.assertEqual(caller.prec, 5)
            self.assertEqual(caller.rounding, ROUND_DOWN)
            self.assertIs(caller.traps[Inexact], True)
            self.assertEqual(caller.flags, flags)

    def test_api_calls_need_no_file_db_clock_random_network_or_runtime(self):
        import pathlib
        import random
        import socket
        import sqlite3
        import time
        with ExitStack() as stack:
            for operation in ['builtins.open', 'pathlib.Path.open', 'socket.socket', 'sqlite3.connect',
                              'time.time', 'time.monotonic', 'random.random', 'random.Random']:
                stack.enter_context(patch(operation, side_effect=AssertionError('unexpected side effect')))
            spec = source()
            self.assertEqual(self.generate(spec)['trace']['relative_levels_db'][1], 0)
            self.assertGreater(self.integrate(spec)['power_mw'], 0)


if __name__ == '__main__':
    unittest.main()
