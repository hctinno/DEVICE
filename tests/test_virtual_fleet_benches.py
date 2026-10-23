"""Six public-catalog DAGs exercise declared synthetic roles, never hardware.

Catalog metadata is copied intact; only explicit synthetic policies are added.
Nominal fixed attenuations (3/10/20 dB) are preserved. Other numbers, including
the DUT's 1 MHz CW emission, are authored fixtures, not smartphone capabilities.
Motion is independent of RF: geometry/field coupling, AC emissions accuracy,
Bluetooth decoding, regulatory DFS waveforms, physical calibration, VNA phase,
manufacturer SCPI, real-model accuracy and field operation remain unvalidated.
Only unconnected ports are absent; connected invalid outputs must block results.
"""
import copy
import math
from pathlib import Path
import unittest

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example, create_fleet

CATALOG = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'


class FleetBenchTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(CATALOG)
        self.original = copy.deepcopy(self.catalog)
        self.sequence = 0

    def tearDown(self):
        self.assertEqual(self.catalog, self.original)

    def request_id(self):
        self.sequence += 1
        return f'bench:{self.sequence}'

    def command(self, device, action, expected=('ok', 'pending'), **parameters):
        result = self.fleet.execute(self.request_id(), device, action, parameters)
        self.assertIn(result['status'], expected, (device, action, result))
        return result

    def advance(self, ticks):
        self.assertEqual(self.fleet.advance(self.request_id(), ticks)['status'], 'ok')

    def observed(self, device):
        return self.fleet.observations()['devices'][device]

    def output(self, device, port):
        return self.observed(device)['values']['outputs'][port]

    def measure(self, device, port='measurement', action='acquire'):
        self.command(device, action, expected=('pending',))
        self.advance(2)
        self.command(device, 'fetch', expected=('ok',))
        packet = self.output(device, port)
        self.assertTrue(packet['valid'])
        self.assertEqual(packet['acquisition_setup_revision'], self.fleet.observations()['setup_revision'])
        self.assertTrue(self.observed(device)['synthetic'])
        self.assertFalse(self.observed(device)['hardware_verified'])
        return packet

    def bench(self, devices, links, *, dut=True, policies=None):
        catalog = copy.deepcopy(self.catalog)
        specs = {'supply': ('power_supply', 'E3632A')}
        if dut:
            specs.update(environment=('temperature_chamber', 'SU-642'), dut=('dut', 'SM-A176U'))
        specs.update(devices)
        self.profiles = {}
        for name, (role, model, *function) in specs.items():
            profile = next(p for p in catalog['profiles'] if p['role'] == role and p['model'] == model
                           and (not function or p['simulation_parameters'].get('function') == function[0]))
            if role in {'temperature_chamber', 'position_controller', 'turntable', 'antenna_mast'}:
                profile['simulation_parameters']['requires_power'] = True
            profile['simulation_parameters'].update((policies or {}).get(name, {}))
            self.profiles[name] = profile
        links = list(links)
        if dut:
            links.append(('environment', 'environment', 'dut', 'environment'))
        for name, profile in self.profiles.items():
            if 'power' in profile['ports']['inputs'] and not any(dst == name and port == 'power' for _, _, dst, port in links):
                links.append(('supply', 'power', name, 'power'))
        topology = {'devices': [{'id': name, 'profile_id': p['profile_id']} for name, p in self.profiles.items()],
                    'connections': [{'source': {'device_id': src, 'port': out}, 'target': {'device_id': dst, 'port': inp},
                                     'kind': self.profiles[src]['ports']['outputs'][out]} for src, out, dst, inp in links]}
        self.fleet = create_fleet(catalog, topology, seed=31)
        self.command('supply', 'configure', voltage_v=5, current_limit_a=1)
        self.command('supply', 'set_load', resistance_ohm=50)
        self.command('supply', 'output', enabled=True)
        if dut:
            self.command('environment', 'configure', temperature_c=23, humidity_percent=45)
            self.command('environment', 'start')
            self.advance(8)

    def start_dut(self, frequency=2.45e9, power=8, bandwidth=1e6, modulation='CW'):
        self.command('dut', 'configure', frequency_hz=frequency, power_dbm=power,
                     bandwidth_hz=bandwidth, duty_cycle=1, modulation=modulation, crest_factor_db=0)
        self.command('dut', 'start')
        self.advance(2)

    def test_radiated_role_path_and_independent_position_motion(self):
        self.bench({'filter': ('filter', 'WRCJV2400/2483.5-2370/2520-60/12SS'),
                    'antenna': ('antenna', 'VULB 9168'), 'analyzer': ('signal_analyzer', 'N9030A'),
                    'controller': ('position_controller', 'CO3000'), 'table': ('turntable', 'DS2000-S'),
                    'mast': ('antenna_mast', 'MA4640')},
                   [('dut', 'rf', 'filter', 'rf'), ('filter', 'rf', 'antenna', 'rf'),
                    ('antenna', 'rf', 'analyzer', 'rf'), ('controller', 'control', 'table', 'control')],
                   policies={'table': {'requires_control': True}})
        self.command('filter', 'configure', loss_db=1.5, band_min_hz=2.4e9, band_max_hz=2.4835e9)
        self.command('antenna', 'configure', gain_db=3, loss_db=.5)
        self.command('analyzer', 'configure', frequency_hz=2.45e9, measurement='power', detector='rms')
        for device, speed in [('controller', 30), ('table', 30), ('mast', .5)]:
            self.command(device, 'configure', speed_per_tick=speed)
        self.start_dut()
        self.command('controller', 'move', position=90)
        self.command('mast', 'move', position=2)
        self.advance(1)
        self.assertEqual(self.output('table', 'position')['position'], 30)
        self.assertEqual(self.output('mast', 'position')['position'], 1.5)
        self.advance(2)
        for device, position, unit in [('table', 90, 'deg'), ('mast', 2, 'm')]:
            self.assertEqual(self.output(device, 'position'),
                             {'valid': True, 'position': position, 'unit': unit, 'moving': False, 'source_id': device})
        measurement = self.measure('analyzer')
        self.assertAlmostEqual(measurement['value'], 8 - 1.5 + 3 - .5)
        self.assertEqual(measurement['unit'], 'dBm')
        self.start_dut(frequency=2.6e9)
        self.assertEqual(self.observed('filter')['values']['reason'], 'out_of_band')
        rejected = self.command('analyzer', 'acquire', expected=('invalid',))
        self.assertNotIn('measurement', rejected['values']['outputs'])

    def test_ac_role_cw_lisn_receiver_units_and_missing_power(self):
        self.bench({'lisn': ('lisn', 'ENV216'), 'receiver': ('emi_receiver', 'ESR')},
                   [('dut', 'rf', 'lisn', 'rf'), ('lisn', 'rf', 'receiver', 'rf'),
                    ('lisn', 'power', 'receiver', 'power')])
        self.command('lisn', 'configure', loss_db=2)
        self.command('receiver', 'configure', frequency_hz=1e6, bandwidth_hz=1e4, rbw_hz=1000,
                     measurement='power', detector='rms', impedance_ohm=50)
        self.start_dut(frequency=1e6, power=-30, bandwidth=1e4)
        power = self.measure('receiver')
        self.assertEqual((power['unit'], power['value']), ('dBm', -32))
        self.command('receiver', 'configure', measurement='voltage')
        voltage = self.measure('receiver')
        self.assertEqual(voltage['unit'], 'dBuV')
        self.assertAlmostEqual(voltage['value'], -32 + 90 + 10 * math.log10(50))
        self.command('supply', 'output', enabled=False)
        self.assertNotIn('rf', self.observed('lisn')['values']['outputs'])
        rejected = self.command('receiver', 'fetch', expected=('invalid',))
        self.assertNotIn('measurement', rejected['values']['outputs'])

    def test_pxi_generator_to_analyzer_preserves_pulse_and_threshold_detection(self):
        self.bench({'generator': ('dfs_system', 'PXI', 'generator'), 'analyzer': ('dfs_system', 'PXI', 'analyzer')},
                   [('generator', 'rf', 'analyzer', 'rf')], dut=False)
        self.command('generator', 'configure', frequency_hz=5.5e9, bandwidth_hz=1e6, power_dbm=-20,
                     pulse_width_s=2e-6, pulse_repetition_hz=500)
        self.command('analyzer', 'configure', frequency_hz=5.5e9, detection_threshold_dbm=-30)
        self.command('generator', 'acquire', expected=('unsupported',))
        self.command('analyzer', 'start_tx', expected=('unsupported',))
        self.command('generator', 'start_tx')
        pulse = self.output('generator', 'rf')
        self.assertEqual((pulse['modulation'], pulse['pulse_width_s'], pulse['pulse_repetition_hz']), ('pulse', 2e-6, 500))
        self.assertAlmostEqual(pulse['duty_cycle'], .001)
        detected = self.measure('analyzer')
        self.assertTrue(detected['detected'])
        self.assertEqual(detected['detection_policy'], 'synthetic_pulse_and_threshold')
        self.assertEqual(detected['input_source_id'], 'generator')
        self.command('analyzer', 'configure', detection_threshold_dbm=-10)
        self.assertFalse(self.measure('analyzer')['detected'])

    def test_dut_cbt_link_uses_environment_power_and_synthetic_metrics(self):
        self.bench({'tester': ('bluetooth_tester', 'CBT')}, [('dut', 'rf', 'tester', 'rf')])
        self.command('tester', 'configure', frequency_hz=2.45e9, bandwidth_hz=1e6,
                     offered_rate_mbps=2, noise_figure_db=6, minimum_snr_db=3)
        self.command('tester', 'acquire', expected=('invalid',))
        self.start_dut(power=-60, modulation='synthetic-BT')
        metric = self.measure('tester')
        self.assertEqual((metric['unit'], metric['value'], metric['quantity']), ('dBm', -60, 'received_power'))
        self.assertAlmostEqual(metric['snr_db'], -60 - (-174 + 10 * math.log10(1e6) + 6))
        self.assertTrue(metric['associated'])
        self.assertEqual(metric['throughput_mbps'], 2)
        self.assertGreater(metric['bit_error_ratio'], 0)
        self.assertLess(metric['bit_error_ratio'], .5)
        self.assertEqual(metric['simulation_basis'], 'declared_synthetic_policy')
        self.assertEqual(metric['input_source_id'], 'dut')
        self.fleet.author_control(self.request_id(), 'environment', 'communication_loss', True)
        self.assertNotIn('rf', self.observed('dut')['values']['outputs'])
        self.assertNotIn('measurement', self.command('tester', 'fetch', expected=('invalid',))['values']['outputs'])

    def test_auxiliary_cable_single_point_reference_test_keeps_nominal_loss(self):
        self.bench({'splitter': ('splitter', '11667B'), 'attenuator': ('attenuator', '8493C'),
                    'vna': ('network_analyzer', 'HP8753D')},
                   [('dut', 'rf', 'splitter', 'rf'), ('splitter', 'rf_1', 'vna', 'reference'),
                    ('splitter', 'rf_2', 'attenuator', 'rf'), ('attenuator', 'rf', 'vna', 'test')],
                   policies={'vna': {'calibration_valid': True}})
        self.command('splitter', 'configure', ways=2, loss_db=.75)
        self.command('attenuator', 'configure', attenuation_db=10)
        self.command('vna', 'configure', start_hz=2.45e9, stop_hz=2.45e9, points=1)
        self.start_dut()
        measurement = self.measure('vna')
        self.assertEqual((measurement['unit'], measurement['quantity']), ('dB', 's21_magnitude'))
        self.assertEqual(measurement['value'], [-10])
        self.assertEqual(measurement['loss_db'], [10])
        self.assertEqual(measurement['s21_magnitude_db'], [-10])
        self.assertFalse(measurement['phase_supported'])
        self.command('attenuator', 'configure', expected=('unsupported',), attenuation_db=20)
        self.assertEqual(self.measure('vna')['value'], [-10])
        fixed = {p['model']: p['simulation_parameters']['attenuation_db'] for p in self.catalog['profiles']
                 if p['role'] == 'attenuator' and p['simulation_parameters'].get('attenuator_mode') == 'fixed'}
        self.assertEqual(fixed, {'18B-03': 3, '18N-20dB': 20, '8493C': 10})
        self.fleet.author_control(self.request_id(), 'attenuator', 'no_output', True)
        self.assertTrue(self.output('splitter', 'rf_1')['valid'])
        self.assertNotIn('measurement', self.command('vna', 'acquire', expected=('invalid',))['values']['outputs'])

    def test_connected_meter_criterion_requires_new_current_unit_traced_acquisition(self):
        self.fleet, _, _ = create_conducted_example(copy.deepcopy(self.catalog), seed=31)
        previous = self.output('meter', 'measurement')
        criterion = {'id': 'synthetic-power-limit', 'unit': 'dBm', 'quantity': 'time_average', 'operator': '<=', 'limit': -20}
        self.command('software', 'configure', criteria=[criterion])
        self.assertNotIn('measurement', self.observed('meter')['values']['outputs'])
        self.command('software', 'run', expected=('invalid',))
        self.advance(2)
        current = self.measure('meter')
        self.assertGreater(current['acquisition_tick'], previous['acquisition_tick'])
        verdict = self.measure('software', 'data', 'run')
        self.assertEqual((verdict['verdict'], verdict['criteria_count']), ('pass', 1))
        self.assertFalse(verdict['authorized_for_issue'])
        result = verdict['results'][0]
        for key in ('source_id', 'acquisition_tick', 'acquisition_setup_revision', 'unit', 'quantity', 'value'):
            self.assertEqual(result[key], current[key])
        self.assertEqual((result['operator'], result['limit'], result['passed']), ('<=', -20, True))


if __name__ == '__main__':
    unittest.main()
