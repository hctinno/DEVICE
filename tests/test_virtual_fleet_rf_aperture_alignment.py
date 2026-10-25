"""Owner-authored inputs; independent sealed packets/expectations are never read."""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import importlib
import importlib.util
import json
import math
import unittest
from unittest.mock import patch

MODULE = 'labflow.virtual_fleet.rf_aperture_alignment'
PREFIX = 'rf_aperture_alignment_'
FLAGS = dict(data_origin='authored_synthetic', synthetic=True, hardware_verified=False,
             physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
             method_approval='not_assessed', regulatory_scope_complete=False,
             model_scope='normalized_baseband_sample_math_v1')
ORIGIN = 2**60
UNSET = object()


def packet(rows=None, fs=5):
    rows = [[1, 0], [0, 2], [0, 0], [3, 0], [0, 0]] if rows is None else rows
    return dict(schema_version=1, kind='synthetic_rf_baseband_envelope',
                grid=dict(sample_rate_hz=fs, sample_count=len(rows), t0_seconds=0,
                          interpolation='zero_order_hold'),
                sample_unit='sqrt_mW', samples=deepcopy(rows), verification=dict(FLAGS),
                execution_authorized=False, rerun_authorized=False)


def request(*, origin=ORIGIN, numerator=1, denominator=20, start=1, stop=13, loss=20):
    return dict(schema_version=1,
                timebase=dict(id='owner:aperture-clock', origin_tick=origin,
                              tick_seconds=dict(numerator=numerator, denominator=denominator)),
                aperture=dict(start_tick=origin + start, stop_tick=origin + stop, kernel='boxcar'),
                reference_planes=dict(input='declared_dut_output', output='declared_sensor_input'),
                path_loss_db=loss)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def dbm_of_fraction(value):
    with localcontext() as context:
        context.prec = 80
        number = Decimal(value.numerator) / Decimal(value.denominator)
        return float(Decimal(10) * number.ln() / Decimal(10).ln())


class ApertureAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), 'new pure aperture API is absent')
        self.module = importlib.import_module(MODULE)
        self.api = self.module.project_declared_rf_aperture
        self.Error = self.module.RfApertureAlignmentError

    def rejects(self, p=UNSET, r=UNSET, code='invalid_argument'):
        p = packet() if p is UNSET else p
        r = request() if r is UNSET else r
        with self.assertRaises(self.Error) as caught:
            self.api(p, r)
        self.assertEqual(caught.exception.code, PREFIX + code)
        self.assertEqual(str(caught.exception), PREFIX + code)
        self.assertEqual(caught.exception.args, (PREFIX + code,))
        return caught.exception

    def test_partial_overlap_hand_fraction_and_decimal_at_two_reference_planes(self):
        p, r = packet(), request()
        result = self.api(p, r)
        # [1/20,13/20): weights3/20,1/5,1/5,1/20; powers1,4,0,9.
        # E=7/5; T=3/5; Ton=2/5. Loss20dB scales sensor power by1/100.
        self.assertEqual(result['interval'], {
            'start_seconds': {'numerator': 1, 'denominator': 20},
            'stop_seconds': {'numerator': 13, 'denominator': 20},
            'duration_seconds': {'numerator': 3, 'denominator': 5},
            'on_duration_seconds': {'numerator': 2, 'denominator': 5},
            'observed_duty_cycle': 2/3,
            'overlaps': [
                {'sample_index': 0, 'seconds': {'numerator': 3, 'denominator': 20}},
                {'sample_index': 1, 'seconds': {'numerator': 1, 'denominator': 5}},
                {'sample_index': 2, 'seconds': {'numerator': 1, 'denominator': 5}},
                {'sample_index': 3, 'seconds': {'numerator': 1, 'denominator': 20}},
            ]})
        for plane, values in (
            ('source', {'time_mean_mw': Fraction(7, 3), 'on_mean_mw': Fraction(7, 2),
                        'peak_mw': Fraction(9), 'energy_mw_s': Fraction(7, 5)}),
            ('sensor_input', {'time_mean_mw': Fraction(7, 300), 'on_mean_mw': Fraction(7, 200),
                              'peak_mw': Fraction(9, 100), 'energy_mw_s': Fraction(7, 500)}),
        ):
            for key, expected in values.items():
                self.assertTrue(math.isclose(result['metrics'][plane][key], float(expected),
                                             rel_tol=1e-12, abs_tol=0), (plane, key))
            for stem in ('time_mean', 'on_mean', 'peak'):
                self.assertAlmostEqual(result['metrics'][plane][stem + '_dbm'],
                                       dbm_of_fraction(values[stem + '_mw']), delta=1e-9)
        self.assertEqual(result['binding']['packet_sha256'], hashlib.sha256(canonical(p)).hexdigest())
        self.assertEqual(result['binding']['request_sha256'], hashlib.sha256(canonical(r)).hexdigest())
        self.assertEqual(result['binding']['source_grid'], p['grid'])
        self.assertEqual(result['binding']['request'], r)

    def test_exact_return_shapes_plain_json_and_non_authorizing_flags(self):
        result = self.api(packet(), request())
        self.assertEqual(set(result), set('schema_version kind binding interval metrics verification execution_authorized rerun_authorized'.split()))
        self.assertEqual(result['kind'], 'declared_rf_aperture_projection')
        self.assertEqual(len(result['binding']), 4)
        self.assertEqual(len(result['interval']), 6)
        self.assertEqual(set(result['metrics']), {'source', 'sensor_input'})
        self.assertTrue(all(len(v) == 7 for v in result['metrics'].values()))
        self.assertEqual(len(result['verification']), 10)
        self.assertIs(result['verification']['runtime_alignment_verified'], False)
        self.assertIs(result['verification']['hardware_verified'], False)
        self.assertIs(result['execution_authorized'], False)
        self.assertIs(result['rerun_authorized'], False)
        self.assertLessEqual(len(canonical(result)), 1048576)
        json.loads(canonical(result))

    def test_off_only_window_returns_exact_zero_and_null_without_log_zero(self):
        p = packet([[1, 0], [0, 0], [2, 0]], fs=3)
        r = request(numerator=1, denominator=6, start=2, stop=4)
        with patch.object(self.module.math, 'log10', side_effect=AssertionError('log zero')):
            result = self.api(p, r)
        self.assertEqual(result['interval']['on_duration_seconds'], {'numerator': 0, 'denominator': 1})
        self.assertEqual(result['interval']['observed_duty_cycle'], 0.0)
        for values in result['metrics'].values():
            self.assertEqual(values, dict(time_mean_mw=0.0, on_mean_mw=None, peak_mw=0.0,
                                          energy_mw_s=0.0, time_mean_dbm=None,
                                          on_mean_dbm=None, peak_dbm=None))

    def test_n1_and_exact_right_endpoint_are_covered(self):
        result = self.api(packet([[2, 0]], fs=7),
                          request(numerator=1, denominator=7, start=0, stop=1, loss=0))
        self.assertEqual(result['interval']['duration_seconds'], {'numerator': 1, 'denominator': 7})
        self.assertEqual(result['metrics']['source']['time_mean_mw'], 4.0)
        self.assertTrue(math.isclose(result['metrics']['source']['energy_mw_s'], 4/7, rel_tol=1e-12))
        self.assertEqual(result['metrics']['source'], result['metrics']['sensor_input'])

    def test_window_does_not_repeat_pad_or_clip_original_packet(self):
        for start, stop in ((-1, 1), (0, 0), (4, 3), (0, 21), (21, 22)):
            with self.subTest(start=start, stop=stop):
                self.rejects(r=request(start=start, stop=stop))
        r = request(origin=0)
        r['aperture']['start_tick'] = -1
        self.rejects(r=r)

    def test_large_origin_keeps_nearby_ticks_and_time_unit_reexpression(self):
        a = request(origin=2**63 - 30)
        b = request(origin=0, denominator=40, start=2, stop=26)
        first, second = self.api(packet(), a), self.api(packet(), b)
        self.assertEqual(first['interval'], second['interval'])
        self.assertEqual(first['metrics'], second['metrics'])
        self.assertNotEqual(first['binding']['request_sha256'], second['binding']['request_sha256'])

    def test_halving_seconds_with_doubled_fs_halves_energy_not_mean_or_duty(self):
        first = self.api(packet(), request())
        second = self.api(packet(fs=10), request(denominator=40))
        for plane in ('source', 'sensor_input'):
            self.assertEqual(first['metrics'][plane]['time_mean_mw'], second['metrics'][plane]['time_mean_mw'])
            self.assertEqual(first['metrics'][plane]['peak_mw'], second['metrics'][plane]['peak_mw'])
        self.assertAlmostEqual(second['metrics']['source']['energy_mw_s'], .7, delta=1e-12)
        self.assertEqual(second['interval']['duration_seconds'], {'numerator': 3, 'denominator': 10})
        self.assertEqual(second['interval']['observed_duty_cycle'], 2/3)

    def test_missing_extra_and_wrong_nested_keys_are_invalid(self):
        for field in packet():
            p = packet()
            p.pop(field)
            with self.subTest(packet_missing=field):
                self.rejects(p=p)
        for field in request():
            r = request()
            r.pop(field)
            with self.subTest(request_missing=field):
                self.rejects(r=r)
        for parent, key in (('grid', 'duty'), ('verification', 'author')):
            p = packet()
            p[parent][key] = 'CANARY'
            self.rejects(p=p)
        for parent in ('timebase', 'aperture', 'reference_planes'):
            r = request()
            r[parent]['unexpected'] = 'CANARY'
            self.rejects(r=r)

    def test_constants_flags_and_normalization_are_not_inferred(self):
        for key, value in (('kind', 'cw'), ('schema_version', True), ('sample_unit', 'V'),
                           ('execution_authorized', 0), ('rerun_authorized', True)):
            p = packet()
            p[key] = value
            self.rejects(p=p)
        for key, value in (('t0_seconds', 0.0), ('interpolation', 'linear'),
                           ('sample_rate_hz', True), ('sample_rate_hz', 1000000001),
                           ('sample_count', True)):
            p = packet()
            p['grid'][key] = value
            self.rejects(p=p)
        for key in FLAGS:
            p = packet()
            p['verification'][key] = 1 if type(FLAGS[key]) is bool else 'CANARY'
            self.rejects(p=p)

    def test_plain_types_reject_subclasses_objects_cycles_and_tuple_rows(self):
        class Mapping(dict):
            pass
        class Number(int):
            pass
        class Floating(float):
            pass
        class Text(str):
            pass
        class Sequence(list):
            pass
        for p in (Mapping(packet()), object(), [], None):
            self.rejects(p=p)
        for changed in (Number(1), Floating(1.0), True, object(), 10**10000):
            p = packet()
            p['samples'][0][0] = changed
            self.rejects(p=p)
        p = packet()
        p['samples'] = Sequence(p['samples'])
        self.rejects(p=p)
        p = packet()
        p['samples'][0] = (1, 0)
        self.rejects(p=p)
        r = request()
        r['timebase']['id'] = Text('owner')
        self.rejects(r=r)
        p = packet()
        p['samples'][0] = p['samples']
        self.rejects(p=p)

    def test_iq_domain_nonfinite_and_combined_power_ceiling(self):
        for value in (float('nan'), float('inf'), -float('inf'), 1001, -1001, '1'):
            p = packet()
            p['samples'][0][0] = value
            self.rejects(p=p)
        self.rejects(p=packet([[1000, 1000]], fs=1),
                     r=request(numerator=1, denominator=1, start=0, stop=1))

    def test_request_rational_clock_identity_planes_and_loss_are_explicit(self):
        for field, bad in (('id', ''), ('id', 'x\n'), ('id', 'a'*129), ('origin_tick', True),
                            ('origin_tick', -1), ('tick_seconds', {'numerator': 2, 'denominator': 40})):
            r = request()
            r['timebase'][field] = bad
            self.rejects(r=r)
        for value in (0, -1, True, 1.0):
            r = request()
            r['timebase']['tick_seconds']['denominator'] = value
            self.rejects(r=r)
        for loss in (-1, 121, True, float('inf')):
            self.rejects(r=request(loss=loss))
        r = request()
        r['reference_planes']['input'] = 'sensor_input'
        self.rejects(r=r)
        r = request()
        r['aperture']['kernel'] = 'hann'
        self.rejects(r=r)

    def test_sample_ratio_and_tick_upper_budgets_have_fixed_codes(self):
        p = packet()
        p['grid']['sample_count'] = 4097
        self.rejects(p=p, code='budget_exceeded')
        p = packet([[0, 0]]*4097)
        self.rejects(p=p, code='budget_exceeded')
        for location, field in (('timebase', 'origin_tick'), ('aperture', 'start_tick'),
                                ('aperture', 'stop_tick')):
            r = request()
            r[location][field] = 2**63
            self.rejects(r=r, code='budget_exceeded')
        for name in ('numerator', 'denominator'):
            r = request()
            r['timebase']['tick_seconds'][name] = 10**10000
            self.rejects(r=r, code='budget_exceeded')

    def test_maximal_count_and_clock_ratio_endpoints_are_supported(self):
        p = packet([[1, 0]]*4096, fs=1)
        r = request(origin=0, numerator=1, denominator=1, start=0, stop=4096, loss=0)
        result = self.api(p, r)
        self.assertEqual(len(result['interval']['overlaps']), 4096)
        self.assertEqual(result['metrics']['source']['energy_mw_s'], 4096.0)
        self.assertEqual(result['metrics']['source']['time_mean_mw'], 1.0)
        result = self.api(packet([[1, 0]], fs=1000000000),
                          request(origin=0, denominator=1000000000, start=0, stop=1, loss=120))
        self.assertTrue(math.isclose(result['metrics']['sensor_input']['energy_mw_s'],
                                     1e-21, rel_tol=1e-12))

    def test_minimum_normal_and_subnormal_weighted_terms_can_sum_to_normal(self):
        amplitude = float.fromhex('0x1p-511')
        m = float.fromhex('0x1p-1022')
        first = self.api(packet([[amplitude, 0]], fs=1),
                         request(numerator=1, denominator=1, start=0, stop=1, loss=0))
        self.assertEqual(first['metrics']['source']['time_mean_mw'], m)
        self.assertEqual(first['metrics']['source']['energy_mw_s'], m)
        # Each E term is m/2, below normal; the exact sum m must survive.
        second = self.api(packet([[amplitude, 0], [amplitude, 0]], fs=2),
                          request(numerator=1, denominator=2, start=0, stop=2, loss=0))
        self.assertEqual(second['metrics']['source']['energy_mw_s'], m)

    def test_exact_below_normal_rejects_despite_parent_rounded_acceptance(self):
        amplitude = float.fromhex('0x1p-511')
        below = float.fromhex('0x1.fffffffffffffp-512')
        m = Fraction(1, 2**1022)
        ulp = Fraction(1, 2**1074)
        # Squared first row rounds to2m-ulp; second is m; third is0.
        # Exact mean=(3m-ulp)/3<m. Parent fsum rounds total to3m.
        self.assertLess((3*m-ulp)/3, m)
        p = packet([[amplitude, below], [amplitude, 0], [0, 0]], fs=1)
        r = request(numerator=1, denominator=1, start=0, stop=3, loss=0)
        self.rejects(p=p, r=r, code='numeric_unavailable')
        # Separate legacy characterization, not the new API's expected-value oracle.
        from labflow.virtual_fleet.rf_signal_waveform import analyze_rf_baseband_envelope
        legacy = analyze_rf_baseband_envelope(p)
        self.assertEqual(legacy['metrics']['time_mean_mw'], float(m))

    def test_numeric_failure_outside_aperture_is_not_skipped(self):
        p = packet([[1, 0], [1e-200, 0]], fs=2)
        self.rejects(p=p, r=request(numerator=1, denominator=2, start=0, stop=1),
                     code='numeric_unavailable')
        amplitude = float.fromhex('0x1p-511')
        p = packet([[0, 0], [amplitude, 0]], fs=2)
        self.rejects(p=p, r=request(numerator=1, denominator=2, start=0, stop=1, loss=10),
                     code='numeric_unavailable')

    def test_power_and_aggregate_underflow_are_numeric_not_zero(self):
        p = packet([[1e-200, 0]], fs=1)
        self.rejects(p=p, r=request(numerator=1, denominator=1, start=0, stop=1),
                     code='numeric_unavailable')
        p = packet([[float.fromhex('0x1p-511'), 0]], fs=2)
        self.rejects(p=p, r=request(numerator=1, denominator=2, start=0, stop=1, loss=0),
                     code='numeric_unavailable')
        result = self.api(packet([[1, 1e-200]], fs=1),
                          request(numerator=1, denominator=1, start=0, stop=1, loss=0))
        self.assertEqual(result['metrics']['source']['time_mean_mw'], 1.0)

    def test_first_known_error_order_packet_request_coverage_then_numeric(self):
        p = packet([[1e-200, 0]], fs=1)
        r = request()
        r['timebase']['tick_seconds']['denominator'] = 0
        self.rejects(p=p, r=r)
        self.rejects(p=p, r=request(start=0, stop=21))
        p['kind'] = 'CANARY'
        r['timebase']['tick_seconds']['denominator'] = 10**10000
        self.rejects(p=p, r=r)

    def test_binding_representation_key_order_and_original_grid_are_preserved(self):
        p, r = packet(), request()
        first = self.api(p, r)
        reordered = dict(reversed(list(p.items())))
        second = self.api(reordered, dict(reversed(list(r.items()))))
        self.assertEqual(first, second)
        p['samples'][0][0] = 1.0
        third = self.api(p, r)
        self.assertEqual(first['metrics'], third['metrics'])
        self.assertNotEqual(first['binding']['packet_sha256'], third['binding']['packet_sha256'])
        self.assertEqual(first['binding']['source_grid']['sample_count'], 5)

    def test_inputs_and_detached_results_do_not_alias_on_success_or_error(self):
        p, r = packet(), request()
        old_p, old_r = deepcopy(p), deepcopy(r)
        result = self.api(p, r)
        self.assertEqual((p, r), (old_p, old_r))
        result['binding']['request']['timebase']['id'] = 'CANARY'
        result['binding']['source_grid']['sample_count'] = 1
        result['interval']['overlaps'].clear()
        self.assertEqual((p, r), (old_p, old_r))
        self.assertEqual(self.api(p, r)['binding']['source_grid']['sample_count'], 5)
        r['aperture']['stop_tick'] = r['aperture']['start_tick']
        before = deepcopy(r)
        self.rejects(p=p, r=r)
        self.assertEqual(r, before)

    def test_unexpected_control_exception_propagates_the_original_object(self):
        for error in (KeyboardInterrupt('CANARY'), SystemExit(7), GeneratorExit(), RuntimeError('CANARY')):
            with self.subTest(error=type(error).__name__):
                with patch.object(self.module.math, 'log10', side_effect=error):
                    with self.assertRaises(type(error)) as caught:
                        self.api(packet(), request())
                self.assertIs(caught.exception, error)

    def test_api_body_does_no_file_db_network_clock_rng_or_parent_calls(self):
        from labflow.virtual_fleet import rf_signal_waveform as old_waveform
        with patch.object(old_waveform, 'generate_rf_baseband_envelope',
                          side_effect=AssertionError('old generator')), \
             patch.object(old_waveform, 'analyze_rf_baseband_envelope',
                          side_effect=AssertionError('old analyzer')), \
             patch('builtins.open', side_effect=AssertionError('file I/O')), \
             patch('socket.socket', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('DB')), \
             patch('time.time', side_effect=AssertionError('clock')), \
             patch('random.random', side_effect=AssertionError('RNG')):
            result = self.api(packet(), request())
        self.assertIs(result['verification']['runtime_alignment_verified'], False)

    def test_legacy_full_window_compatibility_only_in_common_numeric_domain(self):
        from labflow.virtual_fleet.rf_signal_waveform import analyze_rf_baseband_envelope
        p = packet()
        result = self.api(p, request(numerator=1, denominator=5, start=0, stop=5, loss=0))
        old = analyze_rf_baseband_envelope(p)
        # Own literal full window: energy14/5, T1, Ton3/5, time mean14/5.
        self.assertAlmostEqual(result['metrics']['source']['time_mean_mw'], 14/5, delta=1e-12)
        for key in result['metrics']['source']:
            self.assertEqual(result['metrics']['source'][key], old['metrics'][key])


if __name__ == '__main__':
    unittest.main()
