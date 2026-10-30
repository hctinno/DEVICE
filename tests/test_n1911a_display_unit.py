"""Display conversion on genuine synthetic Fleet/engine state; no hardware I/O."""
from decimal import Decimal, localcontext
from pathlib import Path
import unittest

from labflow.n1911a_virtual_session import N1911AVirtualSession
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example
from labflow.virtual_fleet.instruments import DEVICE_FACTORIES


CATALOG = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'


def watts(dbm):
    with localcontext() as context:
        context.prec = 50
        return float(Decimal(10) ** ((Decimal(str(dbm)) - Decimal(30)) / Decimal(10)))


def bench():
    # Independent declared path: 11 dBm - 10 dB - .5 dB - 20 dB = -19.5 dBm.
    fleet, _, _ = create_conducted_example(load_catalog(CATALOG), seed=4, source_settings={
        'frequency_hz': 2.45e9, 'power_dbm': 11, 'bandwidth_hz': 20e6,
        'duty_cycle': 1, 'modulation': 'CW', 'crest_factor_db': 0})
    return fleet, N1911AVirtualSession(fleet, device_id='meter')


def meter(power, *, unit='dBm', noise=0, maximum=30, mode='on_average', duty=1):
    device = DEVICE_FACTORIES['power_meter']({'profile_id': 'synthetic-meter',
        'role': 'power_meter', 'simulation_parameters': {
            'noise_db': noise, 'maximum_input_dbm': maximum}}, 29)
    ports = {'power': {'valid': True, 'enabled': True, 'voltage_v': 12}, 'sensor': {
        'valid': True, 'status': 'ok', 'unit': 'dBm', 'value': power, 'power_dbm': power,
        'frequency_hz': 2.45e9, 'duty_cycle': duty, 'crest_factor_db': 0,
        'source_id': 'synthetic-sensor', 'acquisition_tick': 0, 'acquisition_setup_revision': 0}}
    device.perform('configure', {'unit': unit, 'measurement_mode': mode},
                   tick=0, setup_revision=0, inputs=ports)
    device.perform('acquire', {}, tick=0, setup_revision=0, inputs=ports)
    device.advance(tick=2, setup_revision=0, inputs=ports)
    return device, ports


def output(response):
    return response['values']['outputs']['measurement']


class N1911ADisplayUnitTests(unittest.TestCase):
    def test_completed_fetch_conversion_is_shared_and_preserves_original_lineage(self):
        fleet, session = bench()
        other = N1911AVirtualSession(fleet, device_id='meter')
        original = session.command('FETCH?')
        self.assertEqual(original['measurement']['value'], -19.5)
        before = fleet.observations()
        start = len(fleet.history())
        changed = session.command('UNIT:POW W')
        self.assertEqual(changed['status'], 'ok')
        self.assertEqual(changed['setup_revision'], before['setup_revision'])
        self.assertEqual(other.command('UNIT:POW?')['response'], 'W')
        converted = other.command('FETCH?')
        self.assertEqual(converted['status'], 'ok')
        current = converted['measurement']
        self.assertEqual(current['unit'], 'W')
        self.assertAlmostEqual(current['value'], watts('-19.5'), delta=1e-19)
        for key in original['measurement']:
            if key not in ('value', 'unit'):
                self.assertEqual(current[key], original['measurement'][key], key)
        self.assertEqual(current['acquisition_value'], -19.5)
        self.assertEqual(current['acquisition_unit'], 'dBm')
        self.assertEqual(current, converted['fleet_receipt']['values']['outputs']['measurement'])
        self.assertEqual(current, converted['observation']['values']['outputs']['measurement'])
        self.assertEqual(fleet.observations()['tick'], before['tick'])
        self.assertEqual(fleet.observations()['devices']['sensor'], before['devices']['sensor'])
        self.assertEqual(fleet.observations()['devices']['dut'], before['devices']['dut'])
        self.assertEqual([row.get('action') for row in fleet.history()[start:]],
                         ['set_display_unit', 'fetch'])
        other.command('UNIT:POW DBM')
        self.assertEqual(session.command('FETCH?')['measurement'], original['measurement'])

    def test_decimal_zero_and_negative_conversion_roundtrips_from_one_acquisition(self):
        for power in (0, -19.5):
            for first_unit in ('dBm', 'W', 'mW'):
                with self.subTest(power=power, first_unit=first_unit):
                    device, ports = meter(power, unit=first_unit)
                    first = output(device.observation(tick=2, setup_revision=0))
                    for unit in ('W', 'dBm', 'W', 'dBm'):
                        reply = device.perform('set_display_unit', {'unit': unit}, tick=2,
                                               setup_revision=0, inputs=ports)
                        self.assertEqual(reply['status'], 'ok')
                        self.assertFalse(reply['setup_changed'])
                        value = output(reply)
                        self.assertEqual(value['unit'], unit)
                        self.assertAlmostEqual(value['value'], watts(power) if unit == 'W' else power,
                                               delta=1e-19 if unit == 'W' else 1e-13)
                        self.assertEqual(value['acquisition_value'], power)
                        self.assertEqual(value['acquisition_tick'], first['acquisition_tick'])
                        self.assertEqual(value['configuration_revision'], first['configuration_revision'])

    def test_display_changes_do_not_resample_noise_or_consume_next_sample(self):
        device, ports = meter(-19.5, noise=.4)
        control, control_ports = meter(-19.5, noise=.4)
        first = output(device.observation(tick=2, setup_revision=0))
        device.perform('set_display_unit', {'unit': 'W'}, tick=2, setup_revision=0, inputs=ports)
        converted = output(device.observation(tick=2, setup_revision=0))
        self.assertAlmostEqual(converted['value'], watts(first['value']), delta=1e-19)
        device.perform('set_display_unit', {'unit': 'dBm'}, tick=2, setup_revision=0, inputs=ports)
        self.assertEqual(output(device.observation(tick=2, setup_revision=0)), first)
        for target, source in ((device, ports), (control, control_ports)):
            target.perform('acquire', {}, tick=2, setup_revision=0, inputs=source)
            target.advance(tick=4, setup_revision=0, inputs=source)
        self.assertEqual(output(device.observation(tick=4, setup_revision=0)),
                         output(control.observation(tick=4, setup_revision=0)))

    def test_pending_and_bus_wait_unit_changes_preserve_original_deadline(self):
        for bus in (False, True):
            with self.subTest(bus=bus):
                fleet, session = bench()
                if bus:
                    session.command('TRIG:SOUR BUS')
                    session.advance(2)
                session.command('INIT')
                if bus:
                    changed = session.command('UNIT:POW W')
                    self.assertEqual(changed['observation']['values']['state'], 'trigger_wait')
                    self.assertEqual(session.command('*TRG')['status'], 'pending')
                started = fleet.observations()
                session.advance(1)
                sensor_before = fleet.observations()['devices']['sensor']
                if bus:
                    self.assertEqual(session.command('UNIT:POW DBM')['status'], 'pending')
                changed = session.command('UNIT:POW W')
                self.assertEqual(changed['status'], 'pending')
                self.assertEqual(changed['setup_revision'], started['setup_revision'])
                self.assertEqual(changed['observation']['values']['state'], 'acquiring')
                self.assertEqual(fleet.observations()['devices']['sensor'], sensor_before)
                self.assertIsNone(session.command('FETCH?')['measurement'])
                session.advance(1)
                result = session.command('FETCH?')
                self.assertEqual(result['status'], 'ok')
                self.assertEqual(result['measurement']['acquisition_tick'], started['tick'] + 2)
                self.assertEqual(result['measurement']['unit'], 'W')

    def test_display_change_cannot_repair_stale_stop_route_abort_or_disconnection(self):
        for failure in ('stale', 'stop', 'route', 'abort', 'disconnected'):
            with self.subTest(failure=failure):
                fleet, session = bench()
                if failure == 'stale':
                    fleet.execute('test:stale', 'meter', 'configure', {'frequency_hz': 2.46e9})
                elif failure == 'stop':
                    fleet.execute('test:stop', 'dut', 'stop')
                elif failure == 'route':
                    fleet.execute('test:route', 'switch', 'select_path', {'input_port': 'rf_2'})
                elif failure == 'abort':
                    session.command('ABOR')
                else:
                    fleet.author_control('test:disconnect', 'meter', 'disconnected', True)
                before = fleet.observations()
                session.command('UNIT:POW W')
                result = session.command('FETCH?')
                self.assertIn(result['status'], ('invalid', 'disconnected'))
                self.assertIsNone(result['measurement'])
                self.assertIsNone(result['response'])
                self.assertEqual(fleet.observations()['tick'], before['tick'])
                self.assertEqual(fleet.observations()['setup_revision'], before['setup_revision'])

    def test_general_configure_unit_still_invalidates_and_increments_setup(self):
        fleet, session = bench()
        before = fleet.observations()
        fleet.execute('test:general-unit', 'meter', 'configure', {'unit': 'W'})
        after = fleet.observations()
        self.assertEqual(after['setup_revision'], before['setup_revision'] + 1)
        self.assertEqual(after['devices']['meter']['values']['configuration_revision'],
                         before['devices']['meter']['values']['configuration_revision'] + 1)
        self.assertIsNone(session.command('FETCH?')['measurement'])
        session.command('UNIT:POW DBM')
        self.assertIsNone(session.command('FETCH?')['measurement'])

    def test_presentation_action_rejects_extra_scope_and_bad_units_without_losing_data(self):
        device, ports = meter(-19.5)
        before = output(device.observation(tick=2, setup_revision=0))
        for parameters in ({'unit': 'mW'}, {'unit': 'DBM'}, {}, {'unit': 'W', 'window': 2},
                           {'unit': 'W', 'measurement_mode': 'peak'}):
            with self.subTest(parameters=parameters):
                reply = device.perform('set_display_unit', parameters, tick=2,
                                       setup_revision=0, inputs=ports)
                self.assertEqual(reply['status'], 'error')
                self.assertFalse(reply['setup_changed'])
                self.assertEqual(output(device.observation(tick=2, setup_revision=0)), before)


class DisplayNumericBoundaryTests(unittest.TestCase):
    def test_large_finite_watts_uses_final_exponent_and_keeps_acquisition(self):
        with localcontext() as context:
            context.prec = 70
            expected = float(Decimal(10) ** Decimal(306))
        for first_unit in ('dBm', 'W'):
            with self.subTest(first_unit=first_unit):
                device, ports = meter(3090, unit=first_unit, maximum=4000)
                before = device.observation(tick=2, setup_revision=0)
                self.assertEqual(before['status'], 'ok')
                changed = device.perform('set_display_unit', {'unit': 'W'}, tick=2,
                                         setup_revision=0, inputs=ports)
                self.assertEqual(changed['status'], 'ok')
                self.assertFalse(changed['setup_changed'])
                result = output(changed)
                self.assertEqual(result['value'], expected)
                self.assertEqual(result['acquisition_value'], 3090)
                self.assertEqual(result['acquisition_tick'], 2)
                self.assertEqual(result['configuration_revision'],
                                 output(before)['configuration_revision'])
                reverted = device.perform('set_display_unit', {'unit': 'dBm'}, tick=2,
                                          setup_revision=0, inputs=ports)
                self.assertEqual(output(reverted)['value'], 3090)
                self.assertEqual(output(device.perform('fetch', {}, tick=2,
                    setup_revision=0, inputs=ports)), output(reverted))

    def test_unrepresentable_watts_rejects_setter_without_partial_state_change(self):
        cases = [({'power': 4000, 'maximum': 4000}, 'display_value_overflow'),
                 ({'power': -300, 'mode': 'time_average', 'duty': 1e-300},
                  'display_value_underflow')]
        for settings, reason in cases:
            with self.subTest(reason=reason):
                device, ports = meter(**settings)
                before = device.observation(tick=2, setup_revision=0)
                changed = device.perform('set_display_unit', {'unit': 'W'}, tick=2,
                                         setup_revision=0, inputs=ports)
                self.assertEqual(changed['status'], 'error')
                self.assertEqual(changed['values']['reason'], reason)
                self.assertFalse(changed['setup_changed'])
                self.assertEqual(changed['values']['configuration'], before['values']['configuration'])
                self.assertEqual(device.observation(tick=2, setup_revision=0), before)
                self.assertEqual(output(device.perform('fetch', {}, tick=2,
                    setup_revision=0, inputs=ports)), output(before))

    def test_watts_acquisition_overflow_and_underflow_are_structured_invalid_not_zero(self):
        cases = [({'power': 4000, 'maximum': 4000}, 'display_value_overflow'),
                 ({'power': -300, 'mode': 'time_average', 'duty': 1e-300},
                  'display_value_underflow')]
        for settings, reason in cases:
            with self.subTest(reason=reason):
                device, ports = meter(unit='W', **settings)
                observed = device.observation(tick=2, setup_revision=0)
                self.assertEqual(observed['status'], 'invalid')
                self.assertEqual(observed['values']['reason'], reason)
                self.assertTrue(observed['values']['operation_complete'])
                self.assertNotIn('measurement', observed['values']['outputs'])
                recovered_unit = device.perform('set_display_unit', {'unit': 'dBm'}, tick=2,
                                                setup_revision=0, inputs=ports)
                self.assertNotIn('measurement', recovered_unit['values']['outputs'])


if __name__ == '__main__':
    unittest.main()
