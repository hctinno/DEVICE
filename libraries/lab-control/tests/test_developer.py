import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_control import ROOT
from dgm_lab.registry import DRIVERS
from dgm_lab.capabilities import capabilities, validate_profile
from dgm_lab.demo import run_demo
from dgm_lab import InstrumentError


class DeveloperTests(unittest.TestCase):
    def test_all_drivers_have_actual_operations_and_profiles(self):
        rows = capabilities()
        self.assertEqual({r['driver'] for r in rows}, set(DRIVERS))
        for row in rows:
            self.assertFalse(row['physical_verified'])
            self.assertTrue((ROOT/row['profile_path']).exists())
            for method in row['methods']:
                self.assertTrue(callable(getattr(DRIVERS[row['driver']], method)))

    def test_profile_validation_opens_nothing(self):
        profile = dict(driver='OdaEx',parameters=dict(expected_serial='LOCAL',expected_firmware='LOCAL',
                       max_voltage=5,max_current=1,installed_model_confirmed=True),
                       transport=dict(kind='serial',port='COM5',baudrate=9600,parity='N',bytesize=8,stopbits=1,termination='\n'))
        with patch('dgm_lab.registry.open_transport',side_effect=AssertionError('must not connect')):
            result = validate_profile(profile)
        self.assertTrue(result['offline_valid'])
        self.assertFalse(result['connection_attempted'])
        self.assertFalse(result['physical_verified'])

    def test_templates_and_bad_transport_rejected_offline(self):
        for name in ('oda-ex','cmu200-cw'):
            with self.assertRaises((ValueError,RuntimeError)):
                validate_profile(json.loads((ROOT/f'profiles/{name}.template.json').read_text()))
        profile = dict(driver='SpectrumAnalyzer',parameters=dict(model='N9030B',max_frequency_hz=3e9),
                       transport=dict(kind='tcp',host='127.0.0.1',port=0))
        with self.assertRaises(ValueError): validate_profile(profile)

    def test_cmu_tcp_not_promoted_from_network_card(self):
        profile = dict(driver='Cmu200Cw',parameters=dict(secondary_address=7,output_port=2,max_frequency_hz=2.7e9,
                       max_power_dbm=-20,expected_firmware='5.21',site_profile_confirmed=True),
                       transport=dict(kind='tcp',host='127.0.0.1',port=5025))
        with self.assertRaises(ValueError): validate_profile(profile)
        from dgm_lab.registry import connect
        with patch('dgm_lab.registry.open_transport',side_effect=AssertionError('must not connect')):
            with self.assertRaises(ValueError):
                with connect(profile): pass
        profile['transport'] = dict(kind='visa',resource='GPIB0::20::7::INSTR')
        with self.assertRaises(ValueError): validate_profile(profile)
        profile['transport']['resource'] = 'GPIB0::20::INSTR'
        self.assertTrue(validate_profile(profile)['offline_valid'])

    def test_simulated_success_and_failure_export_cleanup_evidence(self):
        for failed in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)/'run'
                with patch('socket.create_connection',side_effect=AssertionError('demo must not open hardware')):
                    if failed:
                        with self.assertRaises(InstrumentError): run_demo(path,inject_failure=True)
                    else: run_demo(path)
                result = json.loads((path/('failure.json' if failed else 'result.json')).read_text())
                self.assertTrue(result['simulated_output_off'])
                self.assertEqual(result['status'],'failed' if failed else 'completed')
                self.assertEqual(len(result['measurements']),0 if failed else 2)
                self.assertEqual((path/'result.json').exists(),not failed)
                events = [json.loads(line) for line in (path/'traffic.jsonl').read_text().splitlines()]
                self.assertIn('OUTP OFF',[r['payload'] for r in events if r['direction']=='tx'])
                with self.assertRaises(FileExistsError): run_demo(path)

    def test_open_source_pins_and_no_license_reuse(self):
        rows = json.loads((ROOT/'research/open-source-review.json').read_text())
        for row in rows:
            self.assertRegex(row['commit'],r'^[0-9a-f]{40}$')
            if row['license']=='NOASSERTION':
                self.assertEqual(row['decision'],'no_code_reuse_no_runtime_driver')


if __name__ == '__main__': unittest.main()
