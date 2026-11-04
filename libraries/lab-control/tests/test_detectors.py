"""Manufacturer-dialect contract tests. Scripted transport, no physical instruments."""
from copy import deepcopy
import unittest
from dgm_lab.analyzers import EmiReceiver
from dgm_lab.core import InstrumentError
from dgm_lab.detectors import DETECTORS, RECEIVER_RANGES
from test_control import fixture


class ReceiverDetectorTests(unittest.TestCase):
    def setup_driver(self, model='ESW44', detector='QP', changes=None):
        replies = {'FREQ:CENT?': '13560000', 'BAND?': '9000', 'DET:REC?': DETECTORS[detector],
                   'SWE:TIME?': '1', 'INP:ATT?': '20', 'BAND:TYPE?': 'PULS', 'CALC:UNIT:POW?': 'DBUV',
                   'INIT1:CONT?': '0', 'DISP:BARG:PHOL?': '0', 'DISP:BARG:TCO?': '0',
                   'BAND:AUTO?': '0', 'INP:ATT:AUTO?': '0', 'TRAC? SINGLE': '36.5'}
        replies.update(changes or {})
        io = fixture(model, 'Rohde&Schwarz', **replies)
        driver = EmiReceiver(io, model=model, max_frequency_hz=44e9)
        driver.identify()
        return driver, io

    def arguments(self, detector='QP'):
        return dict(frequency_hz=13.56e6, rbw_hz=9000, detector=detector, dwell_seconds=1, attenuation_db=20)

    def test_all_verified_models_and_detectors_use_single_bargraph_and_proof(self):
        from dgm_lab.capabilities import capabilities
        self.assertEqual(set(capabilities('EmiReceiver')[0]['operation_models']['read_verified_level']), set(RECEIVER_RANGES))
        for model in RECEIVER_RANGES:
            for detector, wire in DETECTORS.items():
                with self.subTest(model=model, detector=detector):
                    driver, io = self.setup_driver(model, detector)
                    result = driver.read_verified_level(**self.arguments(detector))
                    self.assertEqual((result.value, result.unit), (36.5, 'dBuV'))
                    self.assertEqual(result.readbacks['before'], result.readbacks['after'])
                    self.assertIn('DET:REC '+wire, io.events)
                    self.assertLess(io.events.index('BAND:TYPE CISPR'), io.events.index('BAND 9000'))
                    self.assertEqual(io.events.count('DET:REC?'), 2)
                    self.assertLess(io.events.index('INIT1:IMM'), io.events.index('TRAC? SINGLE'))
                    self.assertNotIn('INP:ATT:PROT OFF', io.events)
                    driver.stop()
                    self.assertIn('ABOR', io.events[-5:])

    def test_readback_mismatch_before_and_after_never_returns_measurement(self):
        wrong = {'FREQ:CENT?': '1', 'BAND?': '120000', 'DET:REC?': 'AVER', 'SWE:TIME?': '.1',
                 'INP:ATT?': '0', 'BAND:TYPE?': 'NORM', 'CALC:UNIT:POW?': 'DBM',
                 'INIT1:CONT?': '1', 'DISP:BARG:PHOL?': '1', 'DISP:BARG:TCO?': '1',
                 'BAND:AUTO?': '1', 'INP:ATT:AUTO?': '1'}
        for query, value in wrong.items():
            for after in (False, True):
                with self.subTest(query=query, after=after):
                    driver, io = self.setup_driver()
                    old = io.responses[query]
                    io.responses[query] = [old, value] if after else value
                    with self.assertRaises(InstrumentError): driver.read_verified_level(**self.arguments())

    def test_multi_detector_unknown_and_nonfinite_results_rejected(self):
        for changes in ({'DET:REC?': 'QPE,AVER'}, {'DET:REC?': 'UNKNOWN'}, {'TRAC? SINGLE': '36.5,37'},
                        {'TRAC? SINGLE': 'NaN'}, {'TRAC? SINGLE': '9.9e37'}, {'BAND:AUTO?': 'UNKNOWN'}):
            driver, io = self.setup_driver(changes=changes)
            with self.assertRaises(InstrumentError): driver.read_verified_level(**self.arguments())

    def test_unsupported_limits_fail_without_command_writes(self):
        for changes in ({'detector': 'AVER'}, {'detector': 'RMS'}, {'frequency_hz': 1.001e9},
                        {'dwell_seconds': .99}, {'rbw_hz': 1000}, {'attenuation_db': 10},
                        {'dwell_seconds': float('nan')}, {'frequency_hz': 8000}):
            driver, io = self.setup_driver()
            before = deepcopy(io.events)
            with self.assertRaises(ValueError): driver.read_verified_level(**(self.arguments() | changes))
            self.assertEqual(io.events, before)
        driver, io = self.setup_driver('EPL1000')
        with self.assertRaises(InstrumentError): driver.read_verified_level(**self.arguments())


if __name__ == '__main__': unittest.main()
