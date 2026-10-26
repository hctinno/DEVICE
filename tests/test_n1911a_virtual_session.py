"""Genuine existing VirtualFleet execution; no SCPI transport or physical RF."""
from decimal import Decimal, localcontext
import importlib
import importlib.util
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example, create_fleet, inventory_topology

CATALOG = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'


def expected_dbm(power='12.5', coupling='20'):
    # Independent declared coupled path, time average duty=1/4; no session math.
    with localcontext() as context:
        context.prec = 50
        return Decimal(power) - Decimal('10') - Decimal('.5') - Decimal(coupling) + Decimal(10) * Decimal('.25').log10()


class N1911ASessionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.n1911a_virtual_session'),
                             'N1911A Fleet SCPI session is missing')
        self.api = importlib.import_module('labflow.n1911a_virtual_session')
        self.catalog = load_catalog(CATALOG)
        self.fleet, self.topology, _ = create_conducted_example(self.catalog, seed=4)
        self.session = self.api.N1911AVirtualSession(self.fleet, device_id='meter')

    def command(self, text):
        return self.session.command(text)

    def fresh(self, window=1):
        self.assertEqual(self.command('INIT1')['status'], 'pending')
        self.session.advance(2)
        return self.command(f'FETC{window}?')

    def test_synthetic_identity_binds_exact_existing_catalog_device(self):
        before = self.fleet.history()
        reply = self.command('*IDN?')
        self.assertEqual(reply['status'], 'ok')
        self.assertEqual(reply['response'], 'DGM Virtual,N1911A,SYNTHETIC,SIM-1')
        self.assertEqual(reply['model'], 'N1911A')
        self.assertEqual(reply['profile_id'], 'n1911a-7e6c83fb30')
        self.assertTrue(reply['synthetic'])
        self.assertFalse(reply['hardware_verified'])
        self.assertEqual(reply['firmware_support'], 'not_assessed')
        self.assertEqual(reply['calibration_support'], 'not_assessed')
        self.assertEqual(self.fleet.history(), before)

    def test_normal_fetch_decimal_path_and_lineage_are_original_fleet_values(self):
        reply = self.command('FETCh1:SCALar:POWer:AC?')
        self.assertEqual(reply['status'], 'ok')
        self.assertAlmostEqual(reply['measurement']['value'], float(expected_dbm()), places=12)
        self.assertEqual(reply['measurement'], reply['fleet_receipt']['values']['outputs']['measurement'])
        self.assertEqual(reply['measurement'], reply['observation']['values']['outputs']['measurement'])
        self.assertEqual(reply['measurement']['input_source_id'], 'sensor')
        self.assertEqual(reply['measurement']['source_id'], 'meter')
        self.assertEqual(reply['measurement']['acquisition_setup_revision'], reply['setup_revision'])
        self.assertEqual(float(reply['response']), float(f"{float(expected_dbm()):+.9E}"))
        self.assertEqual(reply['fleet_receipt']['device_id'], 'meter')

    def test_fetch_never_reacquires_resamples_or_advances_clock(self):
        start = len(self.fleet.history())
        first = self.command('FETC?')
        for text in ('FETCH1?', ':FETC1:POW:AC?', 'FETCH:SCALAR?'):
            again = self.command(text)
            self.assertEqual(again['measurement'], first['measurement'])
            self.assertEqual(again['tick'], first['tick'])
        rows = self.fleet.history()[start:]
        self.assertEqual([row['action'] for row in rows], ['fetch'] * 4)

    def test_imm_pending_and_opc_need_only_explicit_clock(self):
        tick = self.fleet.observations()['tick']
        started = self.command('INITiate1:IMMediate')
        self.assertEqual(started['status'], 'pending')
        for _ in range(3):
            self.assertEqual(self.command('*OPC?')['status'], 'pending')
            pending = self.command('FETCH?')
            self.assertEqual(pending['status'], 'pending')
            self.assertIsNone(pending['response'])
            self.assertIsNone(pending['measurement'])
        self.assertEqual(self.fleet.observations()['tick'], tick)
        self.session.advance(1)
        self.assertEqual(self.command('*OPC?')['status'], 'pending')
        advanced = self.session.advance(1)
        self.assertEqual(advanced['fleet_receipt']['values']['advanced_ticks'], 1)
        self.assertEqual(self.command('*OPC?')['response'], '1')
        self.assertEqual(self.command('FETCH?')['measurement']['acquisition_tick'], tick + 2)

    def test_watts_come_from_fleet_after_explicit_unit_change(self):
        self.assertEqual(self.command('UNIT1:POW?')['response'], 'DBM')
        changed = self.command('UNIT1:POWer W')
        self.assertEqual(changed['fleet_receipt']['values']['configuration']['unit'], 'W')
        self.assertEqual(self.command('UNIT:POWER?')['response'], 'W')
        self.assertIsNone(self.command('FETCH?')['response'])
        self.session.advance(2)  # Existing upstream sensor must settle at the new setup revision.
        reply = self.fresh()
        with localcontext() as context:
            context.prec = 50
            watts = Decimal(10) ** ((expected_dbm() - Decimal(30)) / Decimal(10))
        self.assertEqual(reply['measurement']['unit'], 'W')
        self.assertAlmostEqual(reply['measurement']['value'], float(watts), places=16)
        self.assertEqual(reply['measurement']['value'], reply['fleet_receipt']['values']['outputs']['measurement']['value'])

    def test_bus_wait_and_documented_star_trigger_reuse_actual_actions(self):
        self.command('TRIGger:SEQuence1:SOURce BUS')
        self.assertEqual(self.command('TRIG1:SOUR?')['response'], 'BUS')
        self.session.advance(2)
        self.assertEqual(self.command('INIT')['observation']['values']['state'], 'trigger_wait')
        self.session.advance(1)
        self.assertEqual(self.command('*OPC?')['status'], 'pending')
        triggered = self.command('*TRG')
        self.assertEqual(triggered['fleet_receipt']['values']['state'], 'acquiring')
        self.assertEqual(triggered['status'], 'pending')
        self.session.advance(2)
        self.assertEqual(self.command('*OPC?')['response'], '1')
        self.assertAlmostEqual(self.command('FETCH?')['measurement']['value'], float(expected_dbm()), places=12)
        self.assertIn('trigger', [row.get('action') for row in self.fleet.history()])

    def test_abort_cancels_actual_pending_and_preserves_trigger_settings(self):
        self.command('TRIG1:SOUR BUS')
        self.session.advance(2)
        self.command('INIT1')
        aborted = self.command('ABORt1')
        self.assertEqual(aborted['fleet_receipt']['values']['state'], 'aborted')
        self.assertEqual(self.command('TRIG:SOUR?')['response'], 'BUS')
        self.assertEqual(self.command('*OPC?')['response'], '1')
        reply = self.command('FETCH?')
        self.assertEqual(reply['status'], 'invalid')
        self.assertIsNone(reply['response'])
        self.assertIsNone(reply['measurement'])

    def test_window_mismatch_never_fetches_old_or_independent_window_data(self):
        with patch.object(self.fleet, 'execute', wraps=self.fleet.execute) as execute:
            for text in ('FETC2?', 'UNIT2:POW?', 'UNIT2:POW W'):
                reply = self.command(text)
                self.assertEqual(reply['status'], 'unsupported')
                self.assertEqual(reply['code'], 'window_not_current')
                self.assertIsNone(reply['response'])
                self.assertIsNone(reply['measurement'])
            execute.assert_not_called()
        self.fleet.execute('test:select-window', 'meter', 'configure', {'window': 4})
        self.session.advance(2)
        self.assertEqual(self.command('UNIT4:POW?')['response'], 'DBM')
        reply = self.fresh(window=4)
        self.assertEqual(reply['measurement']['window'], 4)
        self.assertEqual(self.command('FETCH1?')['code'], 'window_not_current')

    def test_source_change_invalidates_pending_then_fresh_value_tracks_three_db(self):
        first = self.command('FETCH?')['measurement']
        self.command('INIT1')
        changed = self.fleet.execute('test:source-change', 'dut', 'configure',
            {'frequency_hz': 2.45e9, 'power_dbm': 15.5, 'bandwidth_hz': 20e6,
             'duty_cycle': .25, 'modulation': 'OFDM', 'crest_factor_db': 3})
        self.assertEqual(changed['status'], 'ok')
        invalid = self.command('FETCH?')
        self.assertEqual(invalid['status'], 'invalid')
        self.assertIsNone(invalid['measurement'])
        self.fleet.execute('test:restart', 'dut', 'start')
        self.session.advance(3)
        fresh = self.fresh()['measurement']
        self.assertAlmostEqual(fresh['value'], float(expected_dbm('15.5')), places=12)
        self.assertAlmostEqual(fresh['value'] - first['value'], 3, places=12)
        self.assertGreater(fresh['acquisition_setup_revision'], first['acquisition_setup_revision'])

    def test_path_plus_three_db_lowers_same_meter_raw_three_db(self):
        first = self.command('FETCH?')['measurement']
        changed = self.fleet.execute('test:coupler-change', 'coupler', 'configure',
                                     {'through_loss_db': 1.25, 'coupling_db': 23})
        self.assertEqual(changed['status'], 'ok')
        self.assertIsNone(self.command('FETCH?')['measurement'])
        self.session.advance(3)
        fresh = self.fresh()['measurement']
        self.assertAlmostEqual(fresh['value'], float(expected_dbm(coupling='23')), places=12)
        self.assertAlmostEqual(fresh['value'] - first['value'], -3, places=12)

    def test_stop_and_route_loss_invalidate_cached_measurement_without_numeric_zero(self):
        for device, action, parameters in [('dut', 'stop', {}), ('switch', 'select_path', {'input_port': 'rf_2'})]:
            with self.subTest(device=device):
                fleet, _, _ = create_conducted_example(self.catalog)
                session = self.api.N1911AVirtualSession(fleet, device_id='meter')
                self.assertEqual(session.command('FETCH?')['status'], 'ok')
                fleet.execute('test:loss', device, action, parameters)
                reply = session.command('FETCH?')
                self.assertEqual(reply['status'], 'invalid')
                self.assertIsNone(reply['response'])
                self.assertIsNone(reply['measurement'])
                self.assertEqual(session.command('*OPC?')['response'], '1')

    def test_error_query_consumes_existing_fifo_without_invented_vendor_numbers(self):
        self.command('*TRG')  # Fleet queues not_armed_for_bus_trigger.
        self.command('FETCH?')  # Fleet queues no_current_measurement after invalidation.
        first, second, empty = [self.command('SYSTem:ERRor?') for _ in range(3)]
        self.assertEqual(first['error']['reason'], 'not_armed_for_bus_trigger')
        self.assertEqual(second['error']['reason'], 'no_current_measurement')
        for reply in (first, second):
            self.assertEqual(reply['error']['source'], 'existing_virtual_fleet')
            self.assertIsNone(reply['error']['vendor_number'])
            self.assertIsNone(reply['response'])
            self.assertEqual(reply['error']['reason'], reply['fleet_receipt']['values']['error'])
        self.assertEqual(empty['response'], '+0,"No error"')

    def test_invalid_commands_do_not_dispatch_or_become_fifo_vendor_errors(self):
        invalid = [None, [], '', 'x' * 257, 'FETCH?\n', '*IDN?;FETCH?', 'FETCH?\r', 'ＦＥＴＣ?',
            'UNIT1:POW 0', 'UNIT5:POW W', 'UNIT2:POW MW', 'INIT2', 'ABOR2', 'TRIG2:SOUR BUS',
            'TRIG1:SOUR EXT', 'INIT1:CONT ON', 'CAL:ALL', '*RST', 'FORM:DATA REAL',
            'FETC1:POW:AC? DEF', 'FETC1:SCAL:POW?', 'MEAS?', 'SYST:ERR? extra']
        with patch.object(self.fleet, 'execute', wraps=self.fleet.execute) as execute:
            for text in invalid:
                with self.subTest(text=text):
                    reply = self.command(text)
                    self.assertIn(reply['status'], ('invalid', 'unsupported'))
                    self.assertIsNone(reply['response'])
                    self.assertIsNone(reply['measurement'])
                    self.assertEqual(reply['error_source'], 'session_parser')
            execute.assert_not_called()
        self.assertEqual(self.command('SYST:ERR?')['response'], '+0,"No error"')

    def test_model_role_and_device_id_must_be_explicit_and_exact(self):
        for fleet, identity in [(None, 'meter'), (object(), 'meter'), (self.fleet, None),
                                (self.fleet, ''), (self.fleet, 'missing'), (self.fleet, 'sensor')]:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.api.N1911AVirtualSession(fleet, device_id=identity)
        other_catalog = load_catalog(CATALOG)
        other_meter = next(p for p in other_catalog['profiles'] if p['role'] == 'power_meter')
        other_meter['model'] = 'N1914A'  # Authored negative profile, not catalog support.
        other_fleet = create_fleet(other_catalog, inventory_topology(other_catalog))
        with self.assertRaises(ValueError):
            self.api.N1911AVirtualSession(other_fleet, device_id=other_meter['profile_id'])
        sensor = next(p for p in self.catalog['profiles'] if p['role'] == 'power_sensor')
        sensor['model'] = 'N1911A'  # Same model label with wrong role must still fail.
        wrong_role = create_fleet(self.catalog, inventory_topology(self.catalog))
        with self.assertRaises(ValueError):
            self.api.N1911AVirtualSession(wrong_role, device_id=sensor['profile_id'])

    def test_disconnection_and_calibration_failure_are_not_valid_fetches(self):
        self.fleet.author_control('test:calibration', 'meter', 'invalid_calibration', True)
        reply = self.command('FETCH?')
        self.assertEqual(reply['status'], 'invalid')
        self.assertIsNone(reply['measurement'])
        self.assertEqual(self.command('*OPC?')['response'], '1')
        self.fleet.author_control('test:disconnect', 'meter', 'disconnected', True)
        for text in ('FETCH?', '*IDN?', '*OPC?'):
            reply = self.command(text)
            self.assertEqual(reply['status'], 'disconnected')
            self.assertIsNone(reply['response'])

    def test_session_execution_opens_no_process_or_socket_and_bad_ticks_do_not_advance(self):
        tick = self.fleet.observations()['tick']
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('no process')), \
                patch.object(socket, 'socket', side_effect=AssertionError('no socket')):
            self.command('*IDN?')
            self.command('INIT1')
            self.session.advance(2)
            self.assertEqual(self.command('FETCH?')['status'], 'ok')
        current = self.fleet.observations()['tick']
        self.assertEqual(current, tick + 2)
        for ticks in (True, 0, -1, 1.5, 10001):
            with self.assertRaises(ValueError):
                self.session.advance(ticks)
        self.assertEqual(self.fleet.observations()['tick'], current)

    def test_unsourced_colon_prefix_on_common_commands_is_outside_subset(self):
        with patch.object(self.fleet, 'execute', wraps=self.fleet.execute) as execute:
            for text in (':*IDN?', ':*OPC?', ':*TRG'):
                with self.subTest(text=text):
                    reply = self.command(text)
                    self.assertEqual(reply['status'], 'unsupported')
                    self.assertIsNone(reply['response'])
                    self.assertEqual(reply['error_source'], 'session_parser')
            execute.assert_not_called()

    def test_incomplete_error_query_receipt_cannot_report_ok(self):
        provided = self.fleet.observations()['devices']['meter']
        with patch.object(self.fleet, 'execute', return_value=provided):
            reply = self.command('SYST:ERR?')
        self.assertEqual(reply['status'], 'invalid')
        self.assertEqual(reply['code'], 'fleet_error_query_unavailable')
        self.assertIsNone(reply['response'])

    def test_bus_timeout_is_completed_operation_without_valid_measurement(self):
        self.command('TRIG1:SOUR BUS')
        self.session.advance(2)
        self.command('INIT1')
        self.session.advance(100)
        opc = self.command('*OPC?')
        self.assertEqual(opc['response'], '1')
        self.assertEqual(opc['observation']['values']['reason'], 'acquisition_timeout')
        self.assertIsNone(self.command('FETCH?')['measurement'])
        self.assertEqual(self.command('SYST:ERR?')['error']['reason'], 'acquisition_timeout')


if __name__ == '__main__':
    unittest.main()
