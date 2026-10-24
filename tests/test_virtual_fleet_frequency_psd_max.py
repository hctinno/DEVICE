"""Continuous synthetic density maxima, independent integral/quadratic oracles."""
from contextlib import ExitStack
from copy import deepcopy
from decimal import Context, Decimal, Inexact, ROUND_FLOOR, getcontext, localcontext
from fractions import Fraction
import hashlib
import json
import math
import random
import unittest
from unittest.mock import patch

from labflow.virtual_fleet import frequency_psd_max as module
from labflow.virtual_fleet.frequency_source import _validated
from labflow.virtual_fleet.frequency_psd import _log_display


def source(offsets=None, densities=None, **changes):
    value = {
        'schema_version': 1, 'kind': 'synthetic_piecewise_density_source',
        'source_id': 'maximum-source-1', 'declared_mode_id': 'declared-mode-1',
        'synthetic': True, 'center_hz': 2450000000,
        'reference_plane': 'dut_output', 'time_basis': 'on_interval', 'power_method': 'on_mean',
        'interpolation': 'linear_mw_per_hz',
        'frequency_offsets_hz': [-5000, 0, 5000] if offsets is None else offsets,
        'density_mw_per_hz': [1 / 1024] * 3 if densities is None else densities,
    }
    value.update(changes)
    return value


def unpack(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def integral(spec, start):
    """Independent slope/intercept primitive over every crossed segment."""
    start = Fraction(start)
    stop = start + 3000
    axis = list(map(Fraction, spec['frequency_offsets_hz']))
    density = list(map(Fraction, spec['density_mw_per_hz']))
    result = Fraction(0)
    for x0, x1, y0, y1 in zip(axis, axis[1:], density, density[1:]):
        lo, hi = max(start, x0), min(stop, x1)
        if lo >= hi:
            continue
        slope = (y1 - y0) / (x1 - x0)
        intercept = y0 - slope * x0
        result += slope * (hi**2 - lo**2) / 2 + intercept * (hi - lo)
    return result


def quadratic_oracle(spec):
    """Fit each exact integral quadratic at three points; do not use f(t+W)-f(t)."""
    axis = list(map(Fraction, spec['frequency_offsets_hz']))
    lo, hi = axis[0], axis[-1] - 3000
    if hi < lo:
        return None
    split = sorted({lo, hi} | {p for x in axis for p in (x, x - 3000) if lo <= p <= hi})
    candidates = set(split)
    for a, b in zip(split, split[1:]):
        left, middle, right = [integral(spec, p) for p in (a, (a + b) / 2, b)]
        quadratic = 2 * (left + right - 2 * middle)
        linear = right - left - quadratic
        if quadratic:
            position = -linear / (2 * quadratic)
            if 0 < position < 1:
                candidates.add(a + (b - a) * position)
    start = min(candidates, key=lambda t: (-integral(spec, t), t))
    return start, integral(spec, start), len(candidates)


def log_oracle(power):
    with localcontext(Context(prec=500, traps=[])):
        value = 10 * (Decimal(power.numerator).log10() - Decimal(power.denominator).log10())
        return float(value), float(8 - value)


def context_state(context):
    return (context.prec, context.rounding, context.Emin, context.Emax, context.clamp,
            context.capitals, dict(context.traps), dict(context.flags))


class FrequencyPSDMaximumTests(unittest.TestCase):
    def find(self, spec):
        return module.find_source_psd_maximum(spec)

    def assert_contract(self, result, spec):
        self.assertEqual(set(result), set('schema_version kind algorithm_id source_id declared_mode_id '
            'input_sha256 reference_plane time_basis power_method synthetic hardware_verified ai_model_called '
            'method_approval regulatory_scope_complete waveform_implemented oem_mode_verified reference_bandwidth_hz '
            'status reason_codes source_coverage max_search_complete search_domain winning_interval candidate_count '
            'tie_break_policy exact_power_ratio power_mw power_dbm maximum_dbm margin_db conditional_comparison'.split()))
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['kind'], 'synthetic_source_psd_maximum')
        self.assertEqual(result['algorithm_id'], 'exact_continuous_3khz_density_max_v1')
        self.assertEqual(result['tie_break_policy'], 'earliest_exact_start')
        self.assertEqual(result['source_id'], spec['source_id'])
        self.assertEqual(result['declared_mode_id'], spec['declared_mode_id'])
        expected = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'),
            ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
        self.assertEqual(result['input_sha256'], expected)
        self.assertEqual(result['reference_plane'], 'dut_output')
        self.assertEqual(result['time_basis'], 'on_interval')
        self.assertEqual(result['power_method'], spec['power_method'])
        self.assertEqual(result['reference_bandwidth_hz'], 3000)
        self.assertEqual(result['maximum_dbm'], 8)
        for key, expected in {
            'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
            'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
            'waveform_implemented': False, 'oem_mode_verified': False,
        }.items():
            self.assertIs(result[key], expected) if type(expected) is bool else self.assertEqual(result[key], expected)
        domain = result['search_domain']
        self.assertEqual(set(domain), {'minimum_start_offset_hz', 'maximum_start_offset_hz', 'empty'})
        self.assertEqual(unpack(domain['minimum_start_offset_hz']), Fraction(spec['frequency_offsets_hz'][0]))
        self.assertEqual(unpack(domain['maximum_start_offset_hz']), Fraction(spec['frequency_offsets_hz'][-1]) - 3000)
        raw = json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
        self.assertLessEqual(len(raw), 16384)
        self.assertIs(type(result['candidate_count']), int)
        if result['status'] == 'complete':
            self.assertIs(result['max_search_complete'], True)
            self.assertIs(domain['empty'], False)
            self.assertEqual(result['source_coverage'], 'complete_declared_density_support')
            self.assertEqual(result['reason_codes'], [])
            self.assertGreaterEqual(result['candidate_count'], 1)
            self.assertLessEqual(result['candidate_count'], 16384)
            interval = result['winning_interval']
            self.assertEqual(set(interval), {'start_offset_hz', 'stop_offset_hz'})
            start, stop = unpack(interval['start_offset_hz']), unpack(interval['stop_offset_hz'])
            self.assertEqual(stop - start, 3000)
            self.assertGreaterEqual(start, unpack(domain['minimum_start_offset_hz']))
            self.assertLessEqual(start, unpack(domain['maximum_start_offset_hz']))
            power = unpack(result['exact_power_ratio'])
            self.assertGreater(power, 0)
            self.assertEqual(power, integral(spec, start))
            self.assertEqual(result['power_mw'], float(power))
            self.assertEqual(result['conditional_comparison'], 'meets' if power**5 <= 10000 else 'above')
            self.assertEqual((result['power_dbm'], result['margin_db']), log_oracle(power))
        else:
            self.assertEqual(result['status'], 'incomplete')
            self.assertIs(result['max_search_complete'], False)
            self.assertIs(domain['empty'], True)
            self.assertEqual(result['source_coverage'], 'declared_density_support')
            self.assertEqual(result['reason_codes'], ['source_support_shorter_than_reference_bandwidth'])
            self.assertEqual(result['candidate_count'], 0)
            for key in ('winning_interval', 'exact_power_ratio', 'power_mw', 'power_dbm',
                        'margin_db', 'conditional_comparison'):
                self.assertIsNone(result[key], key)

    def test_flat_all_windows_tie_and_earliest_exact_start_wins(self):
        spec = source()
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), -5000)
        self.assertEqual(unpack(result['exact_power_ratio']), Fraction(375, 128))
        self.assertEqual(result['candidate_count'], 4)

    def test_support_exactly_three_kilohertz_has_one_candidate(self):
        spec = source([0, 1000, 3000], [1, 2, 1])
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), 0)
        self.assertEqual(unpack(result['exact_power_ratio']), 4500)

    def test_short_support_is_incomplete_not_zero_or_an_invented_comparison(self):
        for offsets in ([0, 1000, 2999], [0, math.ulp(0.0), 1]):
            spec = source(offsets, [1, 1, 1])
            result = self.find(spec)
            self.assert_contract(result, spec)
            self.assertLess(unpack(result['search_domain']['maximum_start_offset_hz']),
                            unpack(result['search_domain']['minimum_start_offset_hz']))

    def test_strictly_increasing_and_decreasing_curves_win_at_domain_ends(self):
        for densities, expected_start in (([1, 2, 3], 2000), ([3, 2, 1], -5000)):
            spec = source(densities=densities)
            result = self.find(spec)
            self.assert_contract(result, spec)
            self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), expected_start)
            self.assertEqual(unpack(result['exact_power_ratio']), 8100)

    def test_symmetric_triangle_stationary_window_is_centered_at_peak(self):
        spec = source(densities=[0.25, 1, 0.25])
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), -1500)
        self.assertEqual(unpack(result['exact_power_ratio']), Fraction(5325, 2))

    def test_asymmetric_stationary_endpoint_is_nonbinary_rational(self):
        spec = source([-4000, 0, 6000], [0.25, 1, 0.5])
        result = self.find(spec)
        self.assert_contract(result, spec)
        start = unpack(result['winning_interval']['start_offset_hz'])
        self.assertEqual(start, Fraction(-12000, 13))
        self.assertEqual(unpack(result['winning_interval']['stop_offset_hz']), Fraction(27000, 13))
        self.assertNotEqual(Fraction(float(start)), start)
        self.assertGreater(unpack(result['exact_power_ratio']), integral(spec, float(start)))
        grid = [Fraction(i) for i in range(-4000, 3001, 500)]
        self.assertGreater(unpack(result['exact_power_ratio']), max(integral(spec, t) for t in grid))

    def test_knot_breakpoint_can_be_the_exact_global_maximum(self):
        spec = source([0, 1000, 3000, 4000, 6000], [1, 4, 2, 4, 1])
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), 1000)
        self.assertEqual(unpack(result['exact_power_ratio']), 9000)

    def test_separated_equal_lobes_choose_earliest_stationary_maximum(self):
        spec = source([-10000, -5000, 0, 5000, 10000], [0.25, 1, 0.25, 1, 0.25])
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), -6500)
        self.assertEqual(unpack(result['exact_power_ratio']), integral(spec, 3500))

    def test_flat_top_plateau_chooses_first_fully_inside_window(self):
        spec = source([-10000, -5000, 0, 5000, 10000], [0.25, 1, 1, 1, 0.25])
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), -5000)
        self.assertEqual(unpack(result['exact_power_ratio']), 3000)

    def test_random_piecewise_curves_match_independent_three_point_quadratic_oracle(self):
        generator = random.Random(14317)
        for index in range(32):
            offsets = [0, *sorted(generator.sample(range(1, 12000), 5)), 12000]
            densities = [generator.randrange(1, 17) / 4096 for _ in offsets]
            spec = source(offsets, densities, power_method='peak' if index % 2 else 'on_mean')
            with self.subTest(index=index):
                expected_start, expected_power, expected_count = quadratic_oracle(spec)
                result = self.find(spec)
                self.assert_contract(result, spec)
                self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), expected_start)
                self.assertEqual(unpack(result['exact_power_ratio']), expected_power)
                self.assertEqual(result['candidate_count'], expected_count)

    def test_density_scaling_and_translation_preserve_exact_stationary_position(self):
        spec = source([-4000, 0, 6000], [0.25, 1, 0.5])
        original = self.find(spec)
        scaled = deepcopy(spec); scaled['density_mw_per_hz'] = [x * 2 for x in spec['density_mw_per_hz']]
        doubled = self.find(scaled)
        self.assertEqual(doubled['winning_interval'], original['winning_interval'])
        self.assertEqual(unpack(doubled['exact_power_ratio']), 2 * unpack(original['exact_power_ratio']))
        shifted = deepcopy(spec)
        shifted['frequency_offsets_hz'] = [x + 10**200 for x in spec['frequency_offsets_hz']]
        translated = self.find(shifted)
        self.assert_contract(translated, shifted)
        start = unpack(translated['winning_interval']['start_offset_hz'])
        stop = unpack(translated['winning_interval']['stop_offset_hz'])
        self.assertEqual(start, 10**200 - Fraction(12000, 13))
        self.assertEqual(unpack(translated['exact_power_ratio']), unpack(original['exact_power_ratio']))
        self.assertEqual(float(start), float(stop))

    def test_large_float_knots_may_need_nonrepresentable_integer_window_endpoints(self):
        center = 1e20
        spacing = int(math.ulp(center))
        spec = source([center - spacing, center, center + spacing], [0.25, 1, 0.25])
        result = self.find(spec)
        self.assert_contract(result, spec)
        interval = result['winning_interval']
        start, stop = unpack(interval['start_offset_hz']), unpack(interval['stop_offset_hz'])
        self.assertEqual(start, Fraction(center) - 1500)
        self.assertEqual(stop, Fraction(center) + 1500)
        self.assertEqual(float(start), float(stop))

    def test_huge_prefix_integrals_do_not_overflow_or_cancel_exact_window_power(self):
        spec = source([0, 10**300, 2 * 10**300], [1e100] * 3)
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), 0)
        self.assertEqual(unpack(result['exact_power_ratio']), Fraction(1e100) * 3000)

    def test_display_eight_does_not_choose_comparison_or_margin(self):
        high = 0.002103191148267311
        for density, comparison in ((math.nextafter(high, -math.inf), 'meets'), (high, 'above')):
            spec = source(densities=[density] * 3)
            result = self.find(spec)
            self.assert_contract(result, spec)
            self.assertEqual(result['power_dbm'], 8.0)
            self.assertEqual(result['conditional_comparison'], comparison)
            self.assertNotEqual(result['margin_db'], 8 - result['power_dbm'])

    def test_exact_one_milliwatt_keeps_true_zero_dbm(self):
        spec = source([0, 1, 3000], [2193 / 4096, 1 / 4096, 1 / 4096])
        result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(result['power_dbm'], 0.0)
        self.assertEqual(result['margin_db'], 8.0)

    def test_minimum_density_and_large_finite_power_have_finite_stable_displays(self):
        for density in (math.ulp(0.0), 1e304):
            spec = source(densities=[density] * 3)
            result = self.find(spec)
            self.assert_contract(result, spec)
            self.assertTrue(math.isfinite(result['power_dbm']))
        with self.assertRaisesRegex(ValueError, '^numeric_result_out_of_range$'):
            self.find(source(densities=[1e305] * 3))

    def test_maximum_source_knot_count_is_supported_without_repeated_full_integration(self):
        spec = source(list(range(4096)), [1 / 1024] * 4096)
        with patch('labflow.virtual_fleet.frequency_source.integrate_source_3khz', side_effect=AssertionError('reintegrated')), \
             patch('labflow.virtual_fleet.frequency_psd.analyze_source_psd', side_effect=AssertionError('float interval')):
            result = self.find(spec)
        self.assert_contract(result, spec)
        self.assertEqual(unpack(result['winning_interval']['start_offset_hz']), 0)
        self.assertEqual(result['candidate_count'], 1096)

    def test_validates_once_and_only_displays_the_winner(self):
        spec = source([-4000, 0, 6000], [0.25, 1, 0.5])
        with patch.object(module, '_validated', wraps=_validated) as validate, \
             patch.object(module, '_log_display', wraps=_log_display) as display:
            self.find(spec)
            validate.assert_called_once_with(spec)
            self.assertEqual(display.call_count, 1)
        with patch.object(module, '_log_display', side_effect=AssertionError('incomplete display')):
            self.assertEqual(self.find(source([0, 100, 200]))['status'], 'incomplete')

    def test_input_hash_and_all_nested_returned_ratios_are_detached(self):
        spec = source()
        before = deepcopy(spec)
        first = self.find(spec)
        expected = deepcopy(first)
        first['winning_interval']['start_offset_hz']['numerator'] = '123'
        self.assertEqual(first['search_domain']['minimum_start_offset_hz'],
                         expected['search_domain']['minimum_start_offset_hz'])
        first['search_domain']['maximum_start_offset_hz']['denominator'] = '9'
        first['reason_codes'].append('changed')
        first['exact_power_ratio']['numerator'] = '1'
        self.assertEqual(spec, before)
        self.assertEqual(self.find(spec), expected)
        spec['density_mw_per_hz'][1] *= 2
        self.assertNotEqual(self.find(spec)['input_sha256'], expected['input_sha256'])

    def test_decimal_precision_traps_flags_and_rounding_are_preserved(self):
        with localcontext() as context:
            context.prec, context.rounding, context.Emin, context.Emax = 2, ROUND_FLOOR, -9, 9
            context.clamp, context.capitals = 1, 0
            for signal in context.traps:
                context.traps[signal] = True
            context.flags[Inexact] = True
            before = context_state(context)
            self.assertEqual(self.find(source(densities=[0.002103191148267311] * 3))['conditional_comparison'], 'above')
            self.assertEqual(context_state(getcontext()), before)
            with self.assertRaisesRegex(ValueError, '^numeric_result_out_of_range$'):
                self.find(source(densities=[1e305] * 3))
            self.assertEqual(context_state(getcontext()), before)

    def test_invalid_source_json_numeric_and_knot_limits_remain_fixed_errors(self):
        values = [None, [], {}, source(schema_version=True), source(power_method='cycle_mean'),
            source(densities=[0, 1, 1]), source(densities=[math.nan] * 3),
            source(densities=[math.inf] * 3), source(densities=[True] * 3),
            source(offsets=[0, 0, 6000]), source(source_id='PRIVATE_CANARY/secret'),
            source(unused='PRIVATE_CANARY' + 'x' * (4 * 1024 * 1024)),
            source(list(range(4097)), [1] * 4097)]
        for i, spec in enumerate(values):
            with self.subTest(index=i):
                with self.assertRaisesRegex(ValueError, '^invalid_frequency_source$') as caught:
                    self.find(spec)
                self.assertNotIn('PRIVATE_CANARY', str(caught.exception))

    def test_candidate_work_public_integer_and_output_budgets_fail_closed(self):
        # Lower private budgets in unit tests, not an API setting or source claim.
        for name, value in (('_MAX_CANDIDATES', 3), ('_MAX_WORK_BITS', 4),
                            ('_MAX_PUBLIC_BITS', 4), ('_MAX_RESULT_BYTES', 20)):
            with self.subTest(budget=name), patch.object(module, name, value):
                with self.assertRaisesRegex(ValueError, '^numeric_result_out_of_range$'):
                    self.find(source())

    def test_source_and_numeric_errors_never_publish_private_exception_text(self):
        with patch.object(module, '_validated', side_effect=ValueError('PRIVATE_CANARY')):
            with self.assertRaisesRegex(ValueError, '^invalid_frequency_source$'):
                self.find(source())
        with patch.object(module, '_log_display', side_effect=ValueError('PRIVATE_CANARY')):
            with self.assertRaisesRegex(ValueError, '^numeric_result_out_of_range$'):
                self.find(source())

    def test_no_io_device_clock_or_single_band_fallback(self):
        with ExitStack() as stack:
            for target in ('builtins.open', 'pathlib.Path.open', 'sqlite3.connect', 'socket.create_connection',
                           'subprocess.run', 'subprocess.Popen', 'time.time',
                           'labflow.virtual_fleet.frequency_source.integrate_source_3khz',
                           'labflow.virtual_fleet.frequency_psd.analyze_source_psd',
                           'labflow.virtual_fleet.frequency_source.generate_frequency_source'):
                stack.enter_context(patch(target, side_effect=AssertionError('unexpected I/O or fallback')))
            self.assertEqual(self.find(source())['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
