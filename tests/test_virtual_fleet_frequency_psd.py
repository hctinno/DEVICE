"""Exact synthetic band PSD; independent antiderivative and logarithm oracles."""
from contextlib import ExitStack
from copy import deepcopy
from decimal import Context, Decimal, Inexact, ROUND_FLOOR, getcontext, localcontext
from fractions import Fraction
import hashlib
import json
import math
import unittest
from unittest.mock import patch

from labflow.virtual_fleet import frequency_psd
from labflow.virtual_fleet.frequency_source import integrate_source_3khz


def source(offsets=None, densities=None, **changes):
    value = {
        'schema_version': 1, 'kind': 'synthetic_piecewise_density_source',
        'source_id': 'psd-source-1', 'declared_mode_id': 'declared-mode-1',
        'synthetic': True, 'center_hz': 2450000000,
        'reference_plane': 'dut_output', 'time_basis': 'on_interval',
        'power_method': 'on_mean', 'interpolation': 'linear_mw_per_hz',
        'frequency_offsets_hz': [-5000, 0, 5000] if offsets is None else offsets,
        'density_mw_per_hz': [1 / 1024] * 3 if densities is None else densities,
    }
    value.update(changes)
    return value


def ratio(result):
    r = result['exact_power_ratio']
    return Fraction(int(r['numerator']), int(r['denominator']))


def antiderivative(spec, start):
    """Use slope/intercept primitives, independent of source trapezoids."""
    total = Fraction(0)
    axis = list(map(Fraction, spec['frequency_offsets_hz']))
    density = list(map(Fraction, spec['density_mw_per_hz']))
    for x0, x1, y0, y1 in zip(axis, axis[1:], density, density[1:]):
        low, high = max(Fraction(start), x0), min(Fraction(start) + 3000, x1)
        if low >= high:
            continue
        slope = (y1 - y0) / (x1 - x0)
        intercept = y0 - slope * x0
        total += slope * (high**2 - low**2) / 2 + intercept * (high - low)
    return total


def logarithm_oracle(power):
    # Log numerator - log denominator avoids the implementation's ratio/log path.
    with localcontext(Context(prec=500, traps=[])):
        dbm = 10 * (Decimal(power.numerator).log10() - Decimal(power.denominator).log10())
        return float(dbm), float(8 - dbm)


def context_state(ctx):
    return (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals, ctx.clamp,
            dict(ctx.traps), dict(ctx.flags))


class FrequencyPSDTests(unittest.TestCase):
    def analyze(self, spec, start=0):
        return frequency_psd.analyze_source_psd(spec, start_offset_hz=start)

    def assert_contract(self, result, spec):
        self.assertEqual(set(result), set('schema_version kind source_id declared_mode_id '
            'input_sha256 start_offset_hz stop_offset_hz reference_bandwidth_hz reference_plane '
            'time_basis power_method power_mw exact_power_ratio source_coverage max_search_complete '
            'synthetic hardware_verified ai_model_called method_approval regulatory_scope_complete '
            'waveform_implemented oem_mode_verified algorithm_id input_basis comparison_basis '
            'power_dbm maximum_dbm margin_db conditional_comparison'.split()))
        self.assertEqual(result['kind'], 'synthetic_source_psd_band_result')
        self.assertEqual(result['algorithm_id'], 'exact_source_3khz_psd_v1')
        self.assertEqual(result['input_basis'], 'exact_integrated_power_ratio')
        self.assertEqual(result['comparison_basis'], 'exact_integer_fifth_power')
        self.assertEqual(result['source_id'], spec['source_id'])
        self.assertEqual(result['declared_mode_id'], spec['declared_mode_id'])
        expected_hash = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'),
            ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
        self.assertEqual(result['input_sha256'], expected_hash)
        self.assertEqual(result['reference_plane'], 'dut_output')
        self.assertEqual(result['time_basis'], 'on_interval')
        self.assertEqual(result['power_method'], spec['power_method'])
        self.assertEqual(result['reference_bandwidth_hz'], 3000)
        self.assertEqual(result['maximum_dbm'], 8)
        self.assertEqual(result['source_coverage'], 'single_declared_band')
        for key, expected in {
            'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
            'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
            'waveform_implemented': False, 'oem_mode_verified': False, 'max_search_complete': False,
        }.items():
            self.assertIs(result[key], expected) if type(expected) is bool else self.assertEqual(result[key], expected)
        power = ratio(result)
        self.assertEqual(result['conditional_comparison'], 'meets' if power**5 <= 10000 else 'above')
        self.assertEqual(result['power_mw'], float(power))
        self.assertTrue(math.isfinite(result['power_dbm']))
        self.assertTrue(math.isfinite(result['margin_db']))
        json.dumps(result, allow_nan=False)

    def patched_power(self, power):
        band = integrate_source_3khz(source(), start_offset_hz=0)
        band['exact_power_ratio'] = {
            'numerator': str(power.numerator), 'denominator': str(power.denominator)}
        try:
            band['power_mw'] = float(power)
        except OverflowError:
            band['power_mw'] = 1.0
        return band

    def rejected_band(self, band, code='invalid_integrated_power'):
        with patch.object(frequency_psd, 'integrate_source_3khz', return_value=band):
            with self.assertRaisesRegex(ValueError, '^' + code + '$') as caught:
                self.analyze(source())
        self.assertNotIn('PRIVATE_CANARY', str(caught.exception))

    def test_exact_public_contract_preserves_original_integrated_metadata(self):
        spec = source()
        band = integrate_source_3khz(spec, start_offset_hz=-1000)
        result = self.analyze(spec, -1000)
        self.assert_contract(result, spec)
        for key, value in band.items():
            if key != 'kind':
                self.assertEqual(result[key], value, key)
        self.assertEqual(result['exact_power_ratio'], {'numerator': '375', 'denominator': '128'})

    def test_flat_slopes_knots_and_asymmetry_match_independent_integrals(self):
        cases = [
            ([-5000, 0, 5000], [1 / 1024] * 3, -5000),
            ([-5000, 0, 5000], [1 / 1024] * 3, 2000),
            ([-5000, 0, 5000], [0.0001, 0.001, 0.0001], -1500),
            ([-5000, 0, 5000], [0.0001, 0.004, 0.0004], -800),
            ([-4000, -1500, -100, 300, 5000], [0.001, 0.003, 0.0005, 0.0007, 0.001], -1600),
            ([-4000, -1500, -100, 300, 5000], [0.003, 0.0001, 0.005, 0.0002, 0.003], 10.5),
        ]
        for offsets, densities, start in cases:
            for method in ('on_mean', 'peak'):
                with self.subTest(start=start, method=method):
                    spec = source(offsets, densities, power_method=method)
                    result = self.analyze(spec, start)
                    exact = antiderivative(spec, start)
                    self.assertEqual(ratio(result), exact)
                    self.assertEqual((result['power_dbm'], result['margin_db']), logarithm_oracle(exact))
                    self.assert_contract(result, spec)

    def test_density_scaling_and_frequency_translation_preserve_expected_power(self):
        spec = source([-5000, 0, 5000], [0.0001, 0.004, 0.0004])
        original = self.analyze(spec, -1500)
        scaled = deepcopy(spec)
        scaled['density_mw_per_hz'] = [x * 2 for x in spec['density_mw_per_hz']]
        result = self.analyze(scaled, -1500)
        self.assertEqual(ratio(result), 2 * ratio(original))
        translated = deepcopy(spec)
        translated['center_hz'] += 1000000
        translated['frequency_offsets_hz'] = [x - 1000000 for x in spec['frequency_offsets_hz']]
        shifted = self.analyze(translated, -1001500)
        for field in ('power_mw', 'exact_power_ratio', 'power_dbm', 'margin_db', 'conditional_comparison'):
            self.assertEqual(shifted[field], original[field])
        self.assertNotEqual(shifted['input_sha256'], original['input_sha256'])

    def test_actual_density_neighbors_both_display_eight_but_compare_differently(self):
        high = 0.002103191148267311
        low = math.nextafter(high, -math.inf)
        for density, comparison in ((low, 'meets'), (high, 'above')):
            spec = source(densities=[density] * 3)
            result = self.analyze(spec)
            self.assert_contract(result, spec)
            self.assertEqual(result['power_dbm'], 8.0)
            self.assertEqual(result['conditional_comparison'], comparison)
            self.assertNotEqual(result['margin_db'], 8 - result['power_dbm'])
            self.assertEqual(result['margin_db'] > 0, comparison == 'meets')
            self.assertEqual((result['power_dbm'], result['margin_db']), logarithm_oracle(ratio(result)))

    def test_same_float_power_and_eight_display_cannot_decide_exact_comparison(self):
        # A unit-only injected source result; not claimed as actual source output.
        with localcontext(Context(prec=250, traps=[])):
            scale = 10**100
            floor = int((Decimal(10) ** (Decimal(4) / 5)) * scale)
        powers = [Fraction(floor, scale), Fraction(floor + 1, scale)]
        results = []
        for power in powers:
            band = self.patched_power(power)
            with patch.object(frequency_psd, 'integrate_source_3khz', return_value=band):
                results.append(self.analyze(source()))
            self.assertEqual((results[-1]['power_dbm'], results[-1]['margin_db']), logarithm_oracle(power))
        self.assertEqual(results[0]['power_mw'], results[1]['power_mw'])
        self.assertEqual([x['power_dbm'] for x in results], [8.0, 8.0])
        self.assertEqual([x['conditional_comparison'] for x in results], ['meets', 'above'])
        self.assertGreater(results[0]['margin_db'], 0)
        self.assertLess(results[1]['margin_db'], 0)

    def test_exact_one_milliwatt_has_true_zero_dbm(self):
        spec = source([0, 1, 3000], [2193 / 4096, 1 / 4096, 1 / 4096])
        result = self.analyze(spec)
        self.assertEqual(ratio(result), 1)
        self.assertEqual(result['power_dbm'], 0.0)
        self.assertEqual(math.copysign(1, result['power_dbm']), 1)
        self.assertEqual(result['margin_db'], 8.0)
        self.assert_contract(result, spec)

    def test_minimum_positive_density_and_large_finite_power_have_finite_logs(self):
        for density in (math.ulp(0.0), 1e304):
            spec = source(densities=[density] * 3)
            result = self.analyze(spec)
            self.assert_contract(result, spec)
            self.assertEqual((result['power_dbm'], result['margin_db']),
                             logarithm_oracle(antiderivative(spec, 0)))

    def test_float_power_overflow_is_not_a_completed_result(self):
        with self.assertRaisesRegex(ValueError, '^numeric_result_out_of_range$'):
            self.analyze(source(densities=[1e305] * 3))

    def test_whole_interval_inclusion_and_endpoint_types_follow_existing_source(self):
        spec = source([0, 3000, 6000], [1 / 1024] * 3)
        for start in (0, 3000, 0.0, 0.5):
            result = self.analyze(spec, start)
            self.assertIs(type(result['start_offset_hz']), type(start))
            self.assertIs(type(result['stop_offset_hz']), type(start))
            self.assertEqual(result['stop_offset_hz'], start + 3000)
            self.assertEqual(result['input_sha256'], self.analyze(spec)['input_sha256'])
        for start in (-math.ulp(0.0), math.nextafter(3000.0, math.inf), 3001):
            with self.assertRaisesRegex(ValueError, '^invalid_frequency_interval$'):
                self.analyze(spec, start)

    def test_large_integer_endpoints_are_preserved_without_float_downcast(self):
        start = 10**200
        spec = source([start - 1, start + 1, start + 3001], [1 / 1024] * 3)
        result = self.analyze(spec, start)
        self.assertEqual(result['start_offset_hz'], start)
        self.assertEqual(result['stop_offset_hz'], start + 3000)
        self.assert_contract(result, spec)

    def test_inherited_source_and_interval_errors_are_sanitized(self):
        invalid = [None, [], {}, source(schema_version=True), source(power_method='average'),
            source(densities=[0, 1, 1]), source(densities=[math.nan] * 3),
            source(densities=[True] * 3), source(offsets=[0, 0, 3000]),
            source(source_id='PRIVATE_CANARY/secret'), source(unused='PRIVATE_CANARY'),
            source(density_mw_per_hz=[1 / 1024] * 4097, frequency_offsets_hz=list(range(4097)))]
        for spec in invalid:
            with self.subTest(kind=type(spec).__name__):
                with self.assertRaisesRegex(ValueError, '^invalid_frequency_source$') as caught:
                    self.analyze(spec)
                self.assertNotIn('PRIVATE_CANARY', str(caught.exception))
        for start in (True, '0', Decimal(0), math.inf, math.nan):
            with self.assertRaisesRegex(ValueError, '^invalid_frequency_interval$'):
                self.analyze(source(), start)

    def test_inherited_json_size_and_depth_limits(self):
        oversized = source(unused='PRIVATE_CANARY' + 'x' * (4 * 1024 * 1024))
        deep = None
        for _ in range(33):
            deep = [deep]
        for spec in (oversized, source(unused=deep)):
            with self.assertRaisesRegex(ValueError, '^invalid_frequency_source$'):
                self.analyze(spec)

    def test_source_maximum_knots_are_supported(self):
        spec = source(list(range(4096)), [1 / 1024] * 4096)
        result = self.analyze(spec, 500)
        self.assertEqual(ratio(result), Fraction(375, 128))
        self.assert_contract(result, spec)

    def test_source_input_hash_and_output_aliases_remain_independent(self):
        spec = source()
        original = deepcopy(spec)
        first = self.analyze(spec)
        expected = deepcopy(first)
        first['exact_power_ratio']['numerator'] = '1'
        first['source_id'] = 'changed'
        self.assertEqual(spec, original)
        self.assertEqual(self.analyze(spec), expected)
        spec['density_mw_per_hz'][0] *= 2
        changed = self.analyze(spec, -2000)
        self.assertNotEqual(changed['input_sha256'], expected['input_sha256'])
        self.assertEqual(expected['source_id'], original['source_id'])

    def test_callee_result_and_return_value_are_detached(self):
        spec = source()
        band = integrate_source_3khz(spec, start_offset_hz=0)
        original = deepcopy(band)
        with patch.object(frequency_psd, 'integrate_source_3khz', return_value=band):
            result = self.analyze(spec)
        self.assertEqual(band, original)
        band['exact_power_ratio']['numerator'] = 'PRIVATE_CANARY'
        self.assertNotIn('PRIVATE_CANARY', json.dumps(result))
        result['exact_power_ratio']['denominator'] = '1'
        self.assertEqual(original['exact_power_ratio']['denominator'], '128')

    def test_callee_called_once_and_existing_psd_or_source_generation_not_used(self):
        with patch.object(frequency_psd, 'integrate_source_3khz', wraps=integrate_source_3khz) as integrate, \
             patch('labflow.virtual_fleet.frequency_source.generate_frequency_source', side_effect=AssertionError), \
             patch('labflow.virtual_fleet.spectrum_math.analyze_psd_band', side_effect=AssertionError):
            spec = source()
            self.analyze(spec, -1000)
            integrate.assert_called_once_with(spec, start_offset_hz=-1000)

    def test_malformed_ratio_is_not_silently_normalized(self):
        for value in (None, [], {}, {'numerator': '1'}, {'numerator': '1', 'denominator': '1', 'extra': 'PRIVATE_CANARY'},
            {'numerator': True, 'denominator': '1'}, {'numerator': '0', 'denominator': '1'},
            {'numerator': '-1', 'denominator': '1'}, {'numerator': '+1', 'denominator': '1'},
            {'numerator': '01', 'denominator': '1'}, {'numerator': '1', 'denominator': '0'},
            {'numerator': '1', 'denominator': '01'}, {'numerator': '１', 'denominator': '1'},
            {'numerator': '2', 'denominator': '2'}):
            band = integrate_source_3khz(source(), start_offset_hz=0)
            band['exact_power_ratio'] = value
            self.rejected_band(band)

    def test_ratio_digit_and_bit_limits_are_checked_before_fifth_power(self):
        for value in ('9' * 1235, str(1 << 4096), '9' * 1234):
            for field in ('numerator', 'denominator'):
                band = integrate_source_3khz(source(), start_offset_hz=0)
                band['exact_power_ratio'][field] = value
                self.rejected_band(band, 'numeric_result_out_of_range')

    def test_bad_integrated_metadata_and_private_keys_are_not_published(self):
        band = integrate_source_3khz(source(), start_offset_hz=0)
        cases = [None, [], {'PRIVATE_CANARY': True}]
        for field, value in [
            ('unused', 'PRIVATE_CANARY'), ('kind', 'other'), ('schema_version', True),
            ('reference_plane', 'antenna'), ('time_basis', 'duty_cycle'),
            ('power_method', 'average'), ('hardware_verified', True), ('synthetic', False),
            ('ai_model_called', True), ('waveform_implemented', True), ('oem_mode_verified', True),
            ('method_approval', 'approved'), ('regulatory_scope_complete', True),
            ('max_search_complete', True), ('source_coverage', 'all_bands'),
            ('input_sha256', 'PRIVATE_CANARY'), ('source_id', '../PRIVATE_CANARY'),
            ('declared_mode_id', []), ('reference_bandwidth_hz', 3000.0),
            ('start_offset_hz', True), ('stop_offset_hz', 2999),
            ('start_offset_hz', 0.0), ('stop_offset_hz', 3000.0),
            ('power_mw', math.nan), ('power_mw', math.inf), ('power_mw', True),
            ('power_mw', 0), ('power_mw', 3.0),
        ]:
            changed = deepcopy(band)
            changed[field] = value
            cases.append(changed)
        for i, item in enumerate(cases):
            with self.subTest(case=i):
                self.rejected_band(item)

    def test_unrepresentable_exact_power_is_not_substituted_with_float_display(self):
        for power in (Fraction(1, 10**400), Fraction(10**400)):
            band = self.patched_power(power)
            band['power_mw'] = 1.0
            self.rejected_band(band, 'numeric_result_out_of_range')

    def test_nonzero_log_or_margin_underflow_is_rejected_instead_of_zero(self):
        scale = 10**400
        near_one = Fraction(scale + 1, scale)
        with localcontext(Context(prec=600, traps=[])):
            floor = int(Decimal(10) ** (Decimal(4) / 5) * scale)
        for power in (near_one, Fraction(floor, scale), Fraction(floor + 1, scale)):
            self.rejected_band(self.patched_power(power), 'numeric_result_out_of_range')

    def test_decimal_precision_rounding_traps_and_flags_are_preserved(self):
        with localcontext() as ctx:
            ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax = 2, ROUND_FLOOR, -9, 9
            ctx.capitals, ctx.clamp = 0, 1
            for signal in ctx.traps:
                ctx.traps[signal] = True
            ctx.flags[Inexact] = True
            before = context_state(ctx)
            result = self.analyze(source(densities=[0.002103191148267311] * 3))
            self.assertEqual(result['conditional_comparison'], 'above')
            self.assertEqual(context_state(getcontext()), before)
            with self.assertRaisesRegex(ValueError, '^numeric_result_out_of_range$'):
                self.analyze(source(densities=[1e305] * 3))
            self.assertEqual(context_state(getcontext()), before)

    def test_unknown_callee_valueerror_is_sanitized(self):
        with patch.object(frequency_psd, 'integrate_source_3khz',
                          side_effect=ValueError('PRIVATE_CANARY/secret')):
            with self.assertRaisesRegex(ValueError, '^invalid_integrated_power$'):
                self.analyze(source())

    def test_calculation_performs_no_io_or_existing_lab_operations(self):
        with ExitStack() as stack:
            for name in ('builtins.open', 'socket.create_connection',
                         'labflow.virtual_lab.VirtualLab.meter', 'labflow.virtual_lab.VirtualLab.advance'):
                stack.enter_context(patch(name, side_effect=AssertionError('unexpected I/O')))
            self.assertEqual(self.analyze(source())['conditional_comparison'], 'meets')


if __name__ == '__main__':
    unittest.main()
