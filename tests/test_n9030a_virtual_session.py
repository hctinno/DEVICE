"""N9030A documented SCPI subset against a real in-memory VirtualFleet."""
from decimal import Decimal, localcontext
import importlib
import unittest
from pathlib import Path

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example


CATALOG = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'


def expected_input_dbm(source_power):
    # Independent declared path: attenuator, switch, coupler. No vendor RF claim.
    with localcontext() as context:
        context.prec = 50
        return Decimal(source_power) - Decimal('10') - Decimal('.5') - Decimal('1.25')


class N9030AVirtualSessionTests(unittest.TestCase):
    def setUp(self):
        self.api = importlib.import_module('labflow.n9030a_virtual_session')
        self.catalog = load_catalog(CATALOG)
        self.fleet, _, _ = create_conducted_example(self.catalog, seed=13)
        self.session = self.api.N9030AVirtualSession(self.fleet, device_id='analyzer')

    def command(self, text):
        return self.session.command(text)

    def test_exact_model_role_and_synthetic_identity(self):
        before = self.fleet.history()
        reply = self.command('*IDN?')
        self.assertEqual(reply['status'], 'ok')
        self.assertIn('DGM Virtual,N9030A,SYNTHETIC', reply['response'])
        self.assertTrue(reply['synthetic'])
        self.assertFalse(reply['hardware_verified'])
        self.assertEqual(reply['profile_id'], 'n9030a-49f214c7ff')
        self.assertEqual(self.fleet.history(), before)
        with self.assertRaises(ValueError):
            self.api.N9030AVirtualSession(self.fleet, device_id='meter')
        with self.assertRaises(ValueError):
            self.api.N9030AVirtualSession(self.fleet, device_id='missing')

    def test_center_span_rbw_and_detector_use_only_fleet_configuration(self):
        checks = [
            ('SENS:FREQ:CENT 2450 MHz', 'FREQUENCY:CENTER?', 'frequency_hz', 2.45e9),
            (':FREQ:SPAN 22MHz', ':SENS:FREQ:SPAN?', 'bandwidth_hz', 22e6),
            ('BAND:RES 30 KHZ', 'SENS:BWID?', 'rbw_hz', 30e3),
        ]
        for setter, getter, key, value in checks:
            with self.subTest(key=key):
                result = self.command(setter)
                self.assertEqual(result['status'], 'ok')
                self.assertEqual(result['fleet_receipt']['values']['configuration'][key], value)
                self.assertEqual(float(self.command(getter)['response']), value)
        self.assertEqual(self.command('DET:FUNC RMS')['fleet_receipt']['values']['configuration']['detector'], 'rms')
        self.assertEqual(self.command('SENS:DET?')['response'], 'AVER')
        self.assertEqual(self.command('DET POS')['fleet_receipt']['values']['configuration']['detector'], 'peak')
        self.assertEqual(self.command('DET:FUNC?')['response'], 'POS')
        self.assertEqual(self.fleet.observations()['devices']['analyzer']['values']['configuration']['detector'], 'peak')
        self.assertEqual(self.command('INIT:IMM')['status'], 'pending')
        self.session.advance(2)
        peak = self.session.fetch_current_scalar()
        self.assertEqual(peak['measurement']['quantity'], 'peak')
        self.assertAlmostEqual(peak['measurement']['value'],
                               float(expected_input_dbm('12.5') + Decimal('3')), places=12)

    def test_center_and_span_both_reject_negative_synthetic_window_atomically(self):
        initial = self.fleet.observations()['devices']['analyzer']
        scalar = self.session.fetch_current_scalar()['measurement']
        for text in ('FREQ:CENT 1 HZ', 'FREQ:SPAN 5 GHZ'):
            with self.subTest(text=text):
                history = self.fleet.history()
                reply = self.command(text)
                self.assertEqual(reply['status'], 'invalid')
                self.assertEqual(reply['code'], 'span_outside_synthetic_window')
                self.assertEqual(self.fleet.history(), history)
                self.assertEqual(self.fleet.observations()['devices']['analyzer'], initial)
                self.assertEqual(self.session.fetch_current_scalar()['measurement'], scalar)

    def test_fetch_current_scalar_uses_fleet_receipt_and_independent_decimal_relation(self):
        first = self.session.fetch_current_scalar()
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(first['measurement'], first['fleet_receipt']['values']['outputs']['measurement'])
        self.assertEqual(first['measurement'], first['observation']['values']['outputs']['measurement'])
        self.assertEqual(first['measurement']['unit'], 'dBm')
        self.assertEqual(first['measurement']['quantity'], 'on_average')
        self.assertEqual(first['measurement']['input_source_id'], 'coupler')
        self.assertEqual(first['measurement']['acquisition_setup_revision'], first['setup_revision'])
        self.assertAlmostEqual(first['measurement']['value'], float(expected_input_dbm('12.5')), places=12)
        self.assertEqual(float(first['response']), first['measurement']['value'])
        self.assertEqual(self.session.fetch_current_scalar()['measurement'], first['measurement'])
        new_source = {'frequency_hz': 2.45e9, 'power_dbm': 15.5,
                      'bandwidth_hz': 20e6, 'duty_cycle': .25,
                      'modulation': 'OFDM', 'crest_factor_db': 3}
        self.assertEqual(self.fleet.execute('test:power3', 'dut', 'configure', new_source)['status'], 'ok')
        self.assertNotEqual(self.session.fetch_current_scalar()['status'], 'ok')
        self.assertEqual(self.fleet.execute('test:restart', 'dut', 'start')['status'], 'pending')
        self.fleet.advance('test:restart-ticks', 3)
        self.assertEqual(self.command('INIT:IMM')['status'], 'pending')
        self.session.advance(2)
        second = self.session.fetch_current_scalar()
        self.assertEqual(second['status'], 'ok')
        self.assertAlmostEqual(second['measurement']['value'] - first['measurement']['value'],
                               float(expected_input_dbm('15.5') - expected_input_dbm('12.5')), places=12)

    def test_pending_opc_abort_and_external_path_stop_invalidate_fetch(self):
        self.assertEqual(self.command('INITIATE:IMMEDIATE')['status'], 'pending')
        self.assertEqual(self.command('*OPC?')['status'], 'pending')
        self.assertEqual(self.session.fetch_current_scalar()['status'], 'pending')
        self.assertEqual(self.command('ABOR')['fleet_receipt']['values']['state'], 'aborted')
        self.assertEqual(self.command('*OPC?')['response'], '1')
        self.assertNotEqual(self.session.fetch_current_scalar()['status'], 'ok')
        self.command('INIT:IMM')
        self.session.advance(2)
        before_path = self.session.fetch_current_scalar()
        self.assertEqual(before_path['status'], 'ok')
        self.assertEqual(self.fleet.execute('test:path', 'switch', 'configure',
                                            {'loss_db': 1.5})['status'], 'ok')
        self.assertNotEqual(self.session.fetch_current_scalar()['status'], 'ok')
        self.command('INIT:IMM')
        self.session.advance(2)
        after_path = self.session.fetch_current_scalar()
        self.assertEqual(after_path['status'], 'ok')
        self.assertAlmostEqual(after_path['measurement']['value'] - before_path['measurement']['value'], -1, places=12)
        self.fleet.execute('test:stop', 'dut', 'stop')
        self.assertNotEqual(self.session.fetch_current_scalar()['status'], 'ok')

    def test_error_is_structured_and_consumed_from_same_fleet(self):
        self.assertEqual(self.command('SYST:ERR?')['error']['reason'], None)
        self.fleet.author_control('test:fault', 'analyzer', 'invalid_calibration', True)
        self.assertEqual(self.command('INIT:IMM')['status'], 'invalid')
        result = self.command('SYST:ERR:NEXT?')
        self.assertEqual(result['error']['reason'], 'calibration_not_valid')
        self.assertIsNone(result['error']['vendor_number'])
        self.assertEqual(result['fleet_receipt']['device_id'], 'analyzer')
        self.assertIsNone(self.command('SYST:ERR?')['error']['reason'])

    def test_external_fleet_quantity_and_detector_are_not_reinterpreted(self):
        self.assertEqual(self.fleet.execute('test:psd', 'analyzer', 'configure',
                                            {'measurement': 'psd'})['status'], 'ok')
        self.command('INIT:IMM')
        self.session.advance(2)
        self.assertEqual(self.session.fetch_current_scalar()['code'],
                         'measurement_not_current_or_outside_scalar_subset')
        self.assertEqual(self.fleet.execute('test:detector', 'analyzer', 'configure',
                                            {'detector': 'quasi_peak'})['status'], 'ok')
        self.assertEqual(self.command('DET?')['code'], 'detector_outside_scalar_subset')

    def test_rejects_unsupported_vendor_result_and_bad_inputs_without_mutation(self):
        before = self.fleet.history()
        for text in ('FETC:CHP:CHP?', 'FETCh:CHPower1?', 'TRAC? TRACE1',
                     'FREQ:CENT 5 V', 'FREQ:SPAN 0 HZ', 'DET QPE',
                     'SENS:DET:TRAC1 POS', 'FREQ:CENT 1GHZ;*IDN?', 'FREQ:CENT 1GHz\n'):
            with self.subTest(text=text):
                self.assertIn(self.command(text)['status'], ('unsupported', 'invalid'))
        self.assertEqual(self.fleet.history(), before)


if __name__ == '__main__':
    unittest.main()
