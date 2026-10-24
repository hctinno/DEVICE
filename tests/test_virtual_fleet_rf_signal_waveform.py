"""054 contract tests: independent literal/Decimal expectations, no RF runner."""
import ast
import builtins
from contextlib import ExitStack
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import importlib
import importlib.util
from io import StringIO
import json
import math
import os
from pathlib import Path
import random
import socket
import sqlite3
import subprocess
import sys
import tracemalloc
import unittest
from unittest import mock

wave = (importlib.import_module('labflow.virtual_fleet.rf_signal_waveform')
        if importlib.util.find_spec('labflow.virtual_fleet.rf_signal_waveform') else None)
FLAGS = dict(data_origin='authored_synthetic', synthetic=True, hardware_verified=False,
             physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
             method_approval='not_assessed', regulatory_scope_complete=False,
             model_scope='normalized_baseband_sample_math_v1')
PACKET_KEYS = set('schema_version kind grid sample_unit samples verification execution_authorized rerun_authorized'.split())
ANALYSIS_KEYS = set('schema_version kind grid input_sha256 metrics verification execution_authorized rerun_authorized'.split())
METRIC_KEYS = set('window_seconds observed_on_samples observed_duty_cycle time_mean_mw on_mean_mw peak_mw '
                  'energy_mw_s time_mean_dbm on_mean_dbm peak_dbm'.split())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def cw(**updates):
    value = dict(schema_version=1, signal_kind='cw', sample_rate_hz=8, sample_count=8, on_power_dbm=0, pulse=None)
    value.update(updates)
    return value


def pulse(*, period=4, on=1, start=0, **updates):
    return cw(signal_kind='rectangular_pulse', pulse=dict(period_samples=period, on_samples=on,
                                                        start_sample_in_period=start), **updates)


def packet(samples, *, fs=8):
    return dict(schema_version=1, kind='synthetic_rf_baseband_envelope',
                grid=dict(sample_rate_hz=fs, sample_count=len(samples), t0_seconds=0,
                          interpolation='zero_order_hold'), sample_unit='sqrt_mW', samples=deepcopy(samples),
                verification=deepcopy(FLAGS), execution_authorized=False, rerun_authorized=False)


class RfSignalWaveformGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(wave, '054 module is absent')

    def error(self, suffix, function, *args, **kwargs):
        with self.assertRaises(wave.RfSignalWaveformError) as raised:
            function(*args, **kwargs)
        code = 'rf_signal_waveform_' + suffix
        self.assertEqual((raised.exception.code, str(raised.exception)), (code, code))
        self.assertNotIn('PRIVATE', str(raised.exception))

    def generate(self, spec=None, seed=0):
        result = wave.generate_rf_baseband_envelope(cw() if spec is None else spec, seed=seed)
        self.assertIs(type(result), dict)
        return result

    def test_public_functions_two_and_fixed_error_codes_three(self):
        self.assertTrue(callable(wave.generate_rf_baseband_envelope))
        self.assertTrue(callable(wave.analyze_rf_baseband_envelope))
        for suffix in ('invalid_argument', 'budget_exceeded', 'numeric_unavailable'):
            code = 'rf_signal_waveform_' + suffix
            error = wave.RfSignalWaveformError(code)
            self.assertTrue(hasattr(error, 'code'))
            self.assertEqual((error.code, str(error)), (code, code))
        for value in ('PRIVATE path/seed', None, True, 7, [], {}):
            error = wave.RfSignalWaveformError(value)
            self.assertTrue(hasattr(error, 'code'))
            self.assertEqual((error.code, str(error)), ('rf_signal_waveform_invalid_argument',) * 2)

    def test_cw_four_phases_seed_alias_and_no_global_rng_changes(self):
        state = random.getstate()
        expected = ([1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0])
        for seed, pair in enumerate(expected):
            first = self.generate(seed=seed)
            self.assertEqual(first['samples'], [pair] * 8)
            self.assertEqual(first, self.generate(seed=seed))
            self.assertEqual(first, self.generate(seed=seed + 4))
        self.assertEqual(random.getstate(), state)

    def test_rectangular_gate_halfopen_boundaries_wrap_partial_and_all_off(self):
        cases = [(pulse(), [1, 0, 0, 0, 1, 0, 0, 0]),
                 (pulse(start=3, sample_count=6), [0, 1, 0, 0, 0, 1]),
                 (pulse(on=3, start=2, sample_count=5), [1, 0, 1, 1, 1]),
                 (pulse(start=1, sample_count=3), [0, 0, 0]),
                 (pulse(period=1, on=1, sample_count=1), [1]),
                 (pulse(period=4, on=4, sample_count=1), [1])]
        for spec, expected in cases:
            value = self.generate(spec)
            self.assertEqual(value['samples'], [[float(on), 0.0] for on in expected])
            self.assertEqual(value['grid'], dict(sample_rate_hz=8, sample_count=len(expected),
                                                t0_seconds=0, interpolation='zero_order_hold'))

    def test_strict_plain_request_shape_enum_and_subclasses_without_callbacks(self):
        class Text(str):
            def __eq__(self, other): raise AssertionError('callback')
            def __str__(self): raise AssertionError('callback')
            __hash__ = str.__hash__
        class Mapping(dict):
            def __iter__(self): raise AssertionError('callback')
        values = [None, [], Mapping(cw()), {}, dict(cw(), extra='PRIVATE'), dict(cw(), schema_version=True),
                  dict(cw(), schema_version=1.0), dict(cw(), schema_version=2),
                  dict(cw(), signal_kind='OFDM'), dict(cw(), signal_kind=Text('cw')),
                  dict(cw(), pulse={}), dict(pulse(), pulse=None), {Text('schema_version'): 1}]
        missing = cw(); del missing['pulse']; values.append(missing)
        for value in values:
            self.error('invalid_argument', wave.generate_rf_baseband_envelope, value, seed=0)

    def test_strict_request_numeric_bounds_and_budget_before_generation(self):
        for field, values in [('sample_rate_hz', (0, 1_000_000_001, 1.0, True, '8', None)),
                              ('sample_count', (0, -1, 1.0, False)),
                              ('on_power_dbm', (-120.0001, 60.0001, math.nan, math.inf, -math.inf, True, '0', None))]:
            for value in values:
                self.error('invalid_argument', wave.generate_rf_baseband_envelope, cw(**{field: value}), seed=0)
        for seed in (-1, 2**31, False, 0.0, '0', None):
            self.error('invalid_argument', wave.generate_rf_baseband_envelope, cw(), seed=seed)
        for spec in (cw(sample_count=4097), cw(sample_count=1 << 32768), pulse(period=4097)):
            with mock.patch.object(math, 'sqrt', side_effect=AssertionError('must reject before generation')) as sqrt:
                self.error('budget_exceeded', wave.generate_rf_baseband_envelope, spec, seed=0)
            sqrt.assert_not_called()
        for spec in (pulse(period=0), pulse(on=0), pulse(on=5), pulse(start=-1), pulse(start=4)):
            self.error('invalid_argument', wave.generate_rf_baseband_envelope, spec, seed=0)
        for spec in (cw(sample_rate_hz=1, sample_count=1, on_power_dbm=-120),
                     pulse(period=4096, on=4096, sample_count=4096, sample_rate_hz=1_000_000_000, on_power_dbm=60)):
            self.assertLessEqual(len(encoded(self.generate(spec, seed=2**31-1))), 1_048_576)

    def test_generated_packet_exact_shape_metadata_units_input_and_result_freshness(self):
        spec = pulse(); before = deepcopy(spec)
        first, second = self.generate(spec), self.generate(spec)
        self.assertEqual(set(first), PACKET_KEYS)
        self.assertEqual((first['schema_version'], first['kind'], first['sample_unit']),
                         (1, 'synthetic_rf_baseband_envelope', 'sqrt_mW'))
        self.assertEqual(first['verification'], FLAGS)
        self.assertIs(first['execution_authorized'], False); self.assertIs(first['rerun_authorized'], False)
        self.assertEqual(len({id(pair) for pair in first['samples']}), 8)
        self.assertEqual(spec, before)
        for key in ('seed', 'spec', 'expected', 'oracle', 'author', 'waveform_implemented'):
            self.assertNotIn(key, first); self.assertNotIn(key, first['verification'])
        self.assertEqual(first, second)
        first['samples'][0][0] = 99; first['grid']['sample_count'] = 99
        first['verification']['hardware_verified'] = True
        self.assertEqual(second, self.generate(spec)); self.assertEqual(spec, before)

    def test_scalar_power_extremes_and_fractional_dBm_match_independent_Decimal(self):
        for dbm in (-120, -60.75, 0, 12.5, 60):
            value = self.generate(cw(on_power_dbm=dbm, sample_count=1), seed=3)
            with localcontext() as context:
                context.prec = 80
                expected = float(Decimal(10) ** (Decimal(str(dbm)) / Decimal(10)))
            i, q = value['samples'][0]
            observed = i * i + q * q
            self.assertTrue(math.isclose(observed, expected, rel_tol=1e-12, abs_tol=0))
            self.assertGreaterEqual(observed, float.fromhex('0x1p-1022'))


class RfSignalWaveformAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(wave, '054 module is absent')

    def analyze(self, value):
        result = wave.analyze_rf_baseband_envelope(value)
        self.assertIs(type(result), dict)
        return result

    def error(self, suffix, value):
        with self.assertRaises(wave.RfSignalWaveformError) as raised:
            wave.analyze_rf_baseband_envelope(value)
        self.assertEqual((raised.exception.code, str(raised.exception)), ('rf_signal_waveform_' + suffix,) * 2)
        self.assertNotIn('PRIVATE', str(raised.exception))

    def assert_number(self, observed, expected, *, db=False):
        if expected is None:
            self.assertIsNone(observed)
        elif expected == 0:
            self.assertEqual(observed, 0)
        elif db:
            self.assertTrue(math.isclose(observed, float(expected), rel_tol=0, abs_tol=1e-9), (observed, expected))
        else:
            self.assertTrue(math.isclose(observed, float(expected), rel_tol=1e-12, abs_tol=0), (observed, expected))

    def assert_independent_metrics(self, result, samples, fs):
        # Independent arbitrary precision algebra on caller-owned literal I/Q.
        with localcontext() as context:
            context.prec = 80
            powers = [(Decimal.from_float(i) if type(i) is float else Decimal(i)) ** 2
                      + (Decimal.from_float(q) if type(q) is float else Decimal(q)) ** 2 for i, q in samples]
            total, count, on = sum(powers), len(samples), sum(value > 0 for value in powers)
            means = dict(time_mean_mw=total / count, on_mean_mw=total / on if on else None, peak_mw=max(powers))
            expected = dict(window_seconds=Decimal(count) / fs, observed_on_samples=on,
                            observed_duty_cycle=Decimal(on) / count, energy_mw_s=total / fs, **means)
            expected.update({key.replace('_mw', '_dbm'): 10 * value.log10() if value else None
                             for key, value in means.items()})
            self.assertEqual(set(result['metrics']), METRIC_KEYS)
            for key, value in expected.items():
                self.assert_number(result['metrics'][key], value, db=key.endswith('_dbm'))
            self.assertIs(type(result['metrics']['observed_on_samples']), int)

    def test_independent_literal_IQ_energy_and_Decimal_Fraction_expectations(self):
        value = packet([[3, 4], [0, 0], [0, -2], [-1, 0]], fs=8)
        result = self.analyze(value)
        self.assertEqual(set(result), ANALYSIS_KEYS)
        self.assertEqual(result['kind'], 'synthetic_rf_baseband_analysis')
        self.assertEqual(result['schema_version'], 1); self.assertEqual(result['grid'], value['grid'])
        self.assertEqual(result['verification'], FLAGS)
        self.assertIs(result['execution_authorized'], False); self.assertIs(result['rerun_authorized'], False)
        self.assert_independent_metrics(result, value['samples'], 8)
        for key, expected in dict(window_seconds=Fraction(1, 2), observed_on_samples=3,
                                  observed_duty_cycle=Fraction(3, 4), time_mean_mw=Fraction(15, 2),
                                  on_mean_mw=10, peak_mw=25, energy_mw_s=Fraction(15, 4)).items():
            self.assertEqual(result['metrics'][key], expected)

    def test_N1_interval_has_nonzero_duration_and_energy(self):
        result = self.analyze(packet([[1, 0]], fs=8))
        self.assertEqual((result['metrics']['window_seconds'], result['metrics']['energy_mw_s']), (0.125, 0.125))
        self.assert_independent_metrics(result, [[1, 0]], 8)

    def test_zero_window_and_negative_zero_have_exact_zero_and_undefined_null(self):
        value = packet([[0.0, -0.0], [0, 0], [-0.0, 0]], fs=1_000_000_000)
        result = self.analyze(value)
        self.assert_independent_metrics(result, value['samples'], 1_000_000_000)
        for field in ('on_mean_mw', 'on_mean_dbm', 'time_mean_dbm', 'peak_dbm'):
            self.assertIsNone(result['metrics'][field])
        for field in ('time_mean_mw', 'energy_mw_s', 'observed_duty_cycle', 'observed_on_samples', 'peak_mw'):
            self.assertEqual(result['metrics'][field], 0)

    def test_I1_both_positive_subnormal_power_and_energy_only_are_rejected(self):
        for i, fs in ((2e-162, 1), (3e-154, 1_000_000_000)):
            self.error('numeric_unavailable', packet([[i, 0]], fs=fs))

    def test_nonzero_pair_rounded_to_zero_and_subnormal_time_mean_are_rejected(self):
        self.error('numeric_unavailable', packet([[1e-200, 0]], fs=1))
        self.error('numeric_unavailable', packet([[float.fromhex('0x1p-511'), 0], [0, 0]], fs=1))

    def test_exact_minimum_normal_power_and_energy_boundary_is_accepted(self):
        minimum = float.fromhex('0x1p-1022')
        value = packet([[float.fromhex('0x1p-511'), 0]], fs=1)
        result = self.analyze(value)
        for field in ('time_mean_mw', 'on_mean_mw', 'peak_mw', 'energy_mw_s'):
            self.assertEqual(result['metrics'][field], minimum)
        self.assert_independent_metrics(result, value['samples'], 1)
        larger = packet([[float.fromhex('0x1p-510'), 0]], fs=4)
        self.assertEqual(self.analyze(larger)['metrics']['energy_mw_s'], minimum)
        larger['grid']['sample_rate_hz'] = 5
        self.error('numeric_unavailable', larger)

    def test_subnormal_component_with_normal_computed_power_is_accepted(self):
        value = packet([[float.fromhex('0x0.0000000000001p-1022'), 1]], fs=1)
        result = self.analyze(value)
        self.assert_independent_metrics(result, value['samples'], 1)
        self.assertEqual((result['metrics']['peak_mw'], result['metrics']['energy_mw_s']), (1, 1))

    def test_unknown_top_grid_verification_metadata_and_authority_fail_closed(self):
        values = [None, [], {}, dict(packet([[1, 0]]), extra='PRIVATE'),
                  dict(packet([[1, 0]]), schema_version=True), dict(packet([[1, 0]]), schema_version=2),
                  dict(packet([[1, 0]]), kind='unknown'), dict(packet([[1, 0]]), sample_unit='V'),
                  dict(packet([[1, 0]]), execution_authorized=0), dict(packet([[1, 0]]), rerun_authorized=True)]
        missing = packet([[1, 0]]); del missing['verification']; values.append(missing)
        for key, bad in [('sample_rate_hz', 0), ('sample_rate_hz', 1.0), ('sample_count', 0),
                         ('sample_count', True), ('t0_seconds', 0.0), ('interpolation', 'linear')]:
            value = packet([[1, 0]]); value['grid'][key] = bad; values.append(value)
        for bad in (None, [], {}, dict(FLAGS, seed=7), dict(FLAGS, hardware_verified=0),
                    dict(FLAGS, model_scope='actual_hardware'), dict(FLAGS, waveform_implemented=True)):
            values.append(dict(packet([[1, 0]]), verification=bad))
        for value in values: self.error('invalid_argument', value)

    def test_plain_sample_shapes_numeric_bounds_and_no_callbacks(self):
        class Row(list):
            def __iter__(self): raise AssertionError('callback')
        class Number(float):
            def __float__(self): raise AssertionError('callback')
            def __mul__(self, other): raise AssertionError('callback')
        invalid = (None, (), [[1]], [[1, 0, 0]], [[True, 0]], [['1', 0]], [[math.nan, 0]],
                   [[math.inf, 0]], [[1000.001, 0]], [[1000, 1]], [Row([1, 0])], [[Number(1), 0]])
        for rows in invalid:
            value = packet([[1, 0]]); value['samples'] = rows
            self.error('invalid_argument', value)
        self.error('invalid_argument', packet([[1, 0], [0, 0]], fs=1) | {'grid': packet([[1, 0]])['grid']})

    def test_oversized_count_or_samples_rejected_before_copy_or_serialization(self):
        first = packet([[1, 0]]); first['grid']['sample_count'] = 1 << 32768
        second = packet([[1, 0]]); second['grid']['sample_count'] = 4096; second['samples'] = [object()] * 4097
        for value in (first, second):
            with mock.patch.object(json, 'dumps', side_effect=AssertionError('must reject before serialization')) as dumped:
                self.error('budget_exceeded', value)
            dumped.assert_not_called()

    def test_original_number_types_negative_zero_order_hash_and_fresh_results(self):
        value = packet([[1, -0.0], [0, 2.0]], fs=3); before = deepcopy(value)
        first, second = self.analyze(value), self.analyze(value)
        self.assertEqual(first['input_sha256'], hashlib.sha256(encoded(value)).hexdigest())
        self.assertEqual(value, before); self.assertEqual(first, second)
        changed_type = deepcopy(value); changed_type['samples'][0][0] = 1.0
        changed_order = deepcopy(value); changed_order['samples'].reverse()
        self.assertNotEqual(self.analyze(changed_type)['input_sha256'], first['input_sha256'])
        self.assertNotEqual(self.analyze(changed_order)['input_sha256'], first['input_sha256'])
        first['grid']['sample_rate_hz'] = 99; first['verification']['synthetic'] = False
        self.assertEqual(second, self.analyze(value)); self.assertEqual(value, before)

    def test_rotation_sign_and_sample_rate_scaling_preserve_power_relations(self):
        original = packet([[3, 4], [-1, 0], [0, 0]], fs=3)
        rotated = packet([[-4, 3], [0, -1], [0, 0]], fs=3)
        first, second = self.analyze(original), self.analyze(rotated)
        self.assertEqual(first['metrics'], second['metrics'])
        self.assertNotEqual(first['input_sha256'], second['input_sha256'])
        doubled = deepcopy(original); doubled['grid']['sample_rate_hz'] *= 2
        third = self.analyze(doubled)
        for key, value in first['metrics'].items():
            self.assertEqual(third['metrics'][key], value / 2 if key in ('energy_mw_s', 'window_seconds') else value)

    def test_generator_analysis_counts_match_independent_closed_form_and_Decimal(self):
        for period in (1, 2, 4, 7, 16):
            for on in sorted({1, max(1, period // 2), period}):
                for start in sorted({0, period - 1}):
                    for count in sorted({1, period, period + 1, 2 * period + 3}):
                        spec = pulse(period=period, on=on, start=start, sample_count=count, sample_rate_hz=13)
                        generated = wave.generate_rf_baseband_envelope(spec, seed=7)
                        result = self.analyze(generated)
                        f = lambda x: (x // period) * on + min(x % period, on)
                        expected = f(start + count) - f(start)
                        metrics = result['metrics']
                        self.assertEqual(metrics['observed_on_samples'], expected)
                        for key, target in dict(observed_duty_cycle=Fraction(expected, count),
                                                time_mean_mw=Fraction(expected, count),
                                                energy_mw_s=Fraction(expected, 13),
                                                peak_mw=1 if expected else 0, on_mean_mw=1 if expected else None).items():
                            self.assert_number(metrics[key], target)
        for dbm in (-120, -60.75, 7.25, 60):
            spec = pulse(period=7, on=3, start=6, sample_count=15, sample_rate_hz=13, on_power_dbm=dbm)
            result = self.analyze(wave.generate_rf_baseband_envelope(spec, seed=2))
            with localcontext() as context:
                context.prec = 80
                p = Decimal(10) ** (Decimal(str(dbm)) / Decimal(10))
                f = lambda x: (x // 7) * 3 + min(x % 7, 3)
                expected = f(6 + 15) - f(6)
                for key, target in dict(time_mean_mw=p * expected / 15, on_mean_mw=p,
                                       peak_mw=p, energy_mw_s=p * expected / 13).items():
                    self.assert_number(result['metrics'][key], target)

    def test_analysis_does_not_call_generator_or_use_a_previous_generated_result(self):
        value = packet([[0.6, 0.8], [0, 0]], fs=5)
        with mock.patch.object(wave, 'generate_rf_baseband_envelope', side_effect=AssertionError('generator forbidden')) as generate:
            result = self.analyze(value)
        generate.assert_not_called()
        self.assert_independent_metrics(result, value['samples'], 5)


class RfSignalWaveformSafetyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(wave)

    def assert_error(self, suffix, call):
        with self.assertRaises(wave.RfSignalWaveformError) as raised: call()
        self.assertEqual((raised.exception.code, str(raised.exception)), ('rf_signal_waveform_' + suffix,) * 2)
        self.assertNotIn('PRIVATE', str(raised.exception))

    def test_API_calls_have_no_data_IO_runtime_imports_or_stream_mutation(self):
        class Stream(StringIO):
            def write(self, value): raise AssertionError('caller stream write')
            def reconfigure(self, **kwargs): raise AssertionError('caller reconfigure')
        out, err = Stream(), Stream()
        source = packet([[3, 4], [0, 0]], fs=8)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, 'stdout', out))
            stack.enter_context(mock.patch.object(sys, 'stderr', err))
            forbidden = [stack.enter_context(mock.patch.object(obj, method, side_effect=AssertionError('forbidden IO')))
                         for obj, method in [(builtins, 'open'), (builtins, '__import__'), (Path, 'open'),
                                             (Path, 'read_bytes'), (os, 'open'), (socket, 'socket'),
                                             (sqlite3, 'connect'), (subprocess, 'Popen')]]
            generated = wave.generate_rf_baseband_envelope(pulse(), seed=7)
            result = wave.analyze_rf_baseband_envelope(source)
            for call in forbidden: call.assert_not_called()
            self.assertIs(sys.stdout, out); self.assertIs(sys.stderr, err)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertFalse(out.closed); self.assertFalse(err.closed)
        self.assertEqual((generated['samples'][0], result['metrics']['energy_mw_s']), ([0.0, -1.0], 3.125))

    def test_maximum_grid_and_independent_IQ_stay_within_budget_and_normal_power(self):
        source = packet([[600, 800], [-600, -800]] * 2048, fs=1_000_000_000)
        before = encoded(source)
        result = wave.analyze_rf_baseband_envelope(source)
        self.assertEqual((result['metrics']['observed_on_samples'], result['metrics']['peak_mw'],
                          result['metrics']['time_mean_mw']), (4096, 1_000_000, 1_000_000))
        self.assertTrue(math.isclose(result['metrics']['energy_mw_s'], 4.096, rel_tol=1e-12, abs_tol=0))
        generated = wave.generate_rf_baseband_envelope(cw(sample_count=4096, on_power_dbm=60), seed=0)
        self.assertEqual(generated['samples'], [[1000.0, 0.0]] * 4096)
        self.assertLessEqual(len(encoded(source)), 1_048_576)
        self.assertLessEqual(len(encoded(generated)), 1_048_576)
        self.assertLessEqual(len(encoded(result)), 1_048_576)
        self.assertEqual(encoded(source), before)

    def test_serializer_faults_and_oversized_bytes_are_fixed_errors_without_clipping(self):
        source = packet([[1, 0]])
        calls = (lambda: wave.generate_rf_baseband_envelope(cw(), seed=0),
                 lambda: wave.analyze_rf_baseband_envelope(source))
        for call in calls:
            with mock.patch.object(json, 'dumps', return_value=' ' * 1_048_577):
                self.assert_error('budget_exceeded', call)
            with mock.patch.object(json, 'dumps', side_effect=OSError('PRIVATE serializer/path/seed')):
                self.assert_error('numeric_unavailable', call)

    def test_public_packet_hash_once_and_no_hashing_generator_recipe_or_source(self):
        source = packet([[1, -0.0], [0, 2.0]], fs=3)
        expected = encoded(source); original = hashlib.sha256
        with mock.patch.object(hashlib, 'sha256', wraps=original) as hashed:
            wave.generate_rf_baseband_envelope(cw(), seed=7)
            hashed.assert_not_called()
            result = wave.analyze_rf_baseband_envelope(source)
        hashed.assert_called_once_with(expected)
        self.assertEqual(result['input_sha256'], original(expected).hexdigest())
        with mock.patch.object(hashlib, 'sha256', side_effect=OSError('PRIVATE hash')):
            self.assert_error('numeric_unavailable', lambda: wave.analyze_rf_baseband_envelope(source))

    def test_calculation_failures_sanitized_and_KI_propagates_without_changing_input(self):
        request, source = pulse(), packet([[1, 0]])
        request_before, source_before = deepcopy(request), deepcopy(source)
        for function, target in ((lambda: wave.generate_rf_baseband_envelope(request, seed=7), 'sqrt'),
                                 (lambda: wave.analyze_rf_baseband_envelope(source), 'fsum')):
            with mock.patch.object(math, target, side_effect=ValueError('PRIVATE math/source')):
                self.assert_error('numeric_unavailable', function)
            with mock.patch.object(math, target, side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt): function()
        self.assertEqual(request, request_before); self.assertEqual(source, source_before)

    def test_hostile_plain_type_subclasses_are_rejected_without_callbacks(self):
        class Integer(int):
            def __index__(self): raise AssertionError('callback')
            def __int__(self): raise AssertionError('callback')
            def __mod__(self, value): raise AssertionError('callback')
        class Text(str):
            def __eq__(self, value): raise AssertionError('callback')
            def __str__(self): raise AssertionError('callback')
            __hash__ = str.__hash__
        class Mapping(dict):
            def __iter__(self): raise AssertionError('callback')
        class Rows(list):
            def __len__(self): raise AssertionError('callback')
        calls = [lambda: wave.generate_rf_baseband_envelope(cw(), seed=Integer(1)),
                 lambda: wave.generate_rf_baseband_envelope(cw(sample_count=Integer(1)), seed=0),
                 lambda: wave.generate_rf_baseband_envelope(cw(on_power_dbm=Integer(1)), seed=0),
                 lambda: wave.generate_rf_baseband_envelope(pulse(period=Integer(4)), seed=0),
                 lambda: wave.analyze_rf_baseband_envelope(Mapping(packet([[1, 0]])))]
        for key, bad in [('kind', Text('synthetic_rf_baseband_envelope')), ('samples', Rows([[1, 0]]))]:
            value = packet([[1, 0]]); value[key] = bad
            calls.append(lambda value=value: wave.analyze_rf_baseband_envelope(value))
        for call in calls: self.assert_error('invalid_argument', call)
        error = wave.RfSignalWaveformError(Text('PRIVATE'))
        self.assertEqual((error.code, str(error)), ('rf_signal_waveform_invalid_argument',) * 2)

    def test_fixed_metadata_cannot_be_relabelled_as_hardware_or_expected_or_seed(self):
        for field in FLAGS:
            value = packet([[1, 0]])
            value['verification'][field] = True if type(FLAGS[field]) is str else not FLAGS[field]
            self.assert_error('invalid_argument', lambda value=value: wave.analyze_rf_baseband_envelope(value))
        for field in ('seed', 'author', 'oracle', 'expected', 'private_path'):
            value = packet([[1, 0]]); value[field] = 'PRIVATE'
            self.assert_error('invalid_argument', lambda value=value: wave.analyze_rf_baseband_envelope(value))

    def test_module_has_only_approved_imports_and_two_public_functions(self):
        tree = ast.parse(Path(wave.__file__).read_text(encoding='utf-8'))
        imports = [name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names]
        self.assertEqual(set(imports), {'math', 'json', 'hashlib'})
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))
        self.assertEqual([node.name for node in tree.body if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')],
                         ['generate_rf_baseband_envelope', 'analyze_rf_baseband_envelope'])
        self.assertEqual([node.name for node in tree.body if isinstance(node, ast.ClassDef)], ['RfSignalWaveformError'])
        forbidden = {'open', 'exec', 'eval', '__import__', 'compile'}
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden
                             for node in ast.walk(tree)))
        with self.assertRaises(TypeError): wave.generate_rf_baseband_envelope(cw())
        with self.assertRaises(TypeError): wave.generate_rf_baseband_envelope(cw(), 0)

    def test_oversized_exact_record_refusal_does_not_copy_a_large_keyset(self):
        value = {'extra_' + str(index): None for index in range(100_000)}
        tracemalloc.start()
        try:
            self.assert_error('invalid_argument', lambda: wave.generate_rf_baseband_envelope(value, seed=0))
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 128 * 1024, 'exact shape refusal allocated proportional to caller metadata: ' + str(peak))


if __name__ == '__main__':
    unittest.main()
