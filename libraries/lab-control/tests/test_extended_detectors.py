"""Independent manual-derived reply fixtures; no real hardware or shared peer builder."""
import unittest
from dgm_lab.analyzers import EmiReceiver
from dgm_lab.core import InstrumentError
from dgm_lab.detectors import EXTENDED_RANGES, DETECTORS
from test_control import fixture

ARGS = dict(frequency_hz=13.56e6, rbw_hz=9000, detector='QP', dwell_seconds=1, attenuation_db=20)


def replies(model, detector='QP'):
    if model.startswith('FSW'):
        return {'*OPT?': 'B10,K54', 'FREQ:STAR?': '13551000', 'FREQ:STOP?': '13569000',
                'BAND:RES?': '9000', 'INP:ATT?': '20', 'BAND:TYPE?': 'PULS', 'CALC:UNIT:POW?': 'DBUV',
                'INIT:CONT?': '0', 'BAND:RES:AUTO?': '0', 'INP:ATT:AUTO?': '0',
                'CALC:MARK1:X?': '13560000', 'CALC:MARK1?': '1', 'CALC:MARK1:TRAC?': '1',
                'CALC:MARK:FUNC:FME:STAT?': '1', 'CALC:MARK:FUNC:FME:PEAK:AUTO?': '0',
                'CALC:MARK:FUNC:FME:DWEL?': '1', 'CALC:MARK1:FUNC:FME:DET?': DETECTORS[detector],
                'SWE:POIN?': '1001', 'TRIG:SOUR?': 'IMM', 'CALC:MARK1:FUNC:FME:RES?': '36.5',
                'BAND:VID:AUTO?': '0', 'BAND:VID?': '90000', 'SWE:TIME?': '0.1'}
    if model.startswith('N'):
        return {'*OPT?': '"550,EMC"', 'FREQ:CENT?': '13560000', 'FREQ:SPAN?': '0',
                'BAND:RES?': '9000', 'POW:ATT?': '20', 'CALC:MAM:DET1:DWEL?': '1',
                'CALC:MAM:DET1?': 'EAV' if detector == 'CISPR_AVER' else DETECTORS[detector],
                'CALC:MAM:DET2?': 'OFF', 'CALC:MAM:DET3?': 'OFF', 'CALC:MAM:COUP?': '0',
                'CALC:MARK1:MODE?': 'POS', 'EMC:STAN?': 'CISP', 'UNIT:POW?': 'DBUV',
                'AVER:TYPE?': 'SCAL', 'AVER:TYPE:AUTO?': '0', 'SWE:TYPE?': 'SWE',
                'SWE:TYPE:AUTO?': '0', 'INIT:CONT?': '0', 'BAND:RES:AUTO?': '0',
                'POW:ATT:AUTO?': '0', 'TRIG:SOUR?': 'IMM', 'CALC:MARK1:FUNC:MAM?': '36.5,-999,-999,13560000',
                'BAND:VID:AUTO?': '0', 'BAND:VID?': '90000'}
    r = {'FREQ:CENT?': '13560000', 'BAND?': '9000', 'SWE:TIME?': '1', 'INP:ATT?': '20',
         'DET:REC?': DETECTORS[detector], 'BAND:TYPE?': 'PULS', 'CALC:UNIT:POW?': 'DBUV',
         'INIT1:CONT?': '0', 'DISP:BARG:PHOL?': '0', 'BAND:AUTO?': '0', 'INP:ATT:AUTO?': '0', 'TRAC? SINGLE': '36.5'}
    if model == 'EPL1000': r['DISP:BARG:TCO?'] = '0'
    return r


def driver_for(model, detector='QP', changes=None, firmware='A.02.00'):
    manufacturer = 'Keysight Technologies' if model.startswith('N') else 'Rohde&Schwarz'
    data = replies(model, detector)
    data.update({'*IDN?': f'{manufacturer},{model},TEST,{firmware}'})
    data.update(changes or {})
    io = fixture(model, manufacturer, **data)
    driver = EmiReceiver(io, model=model, max_frequency_hz=EXTENDED_RANGES[model])
    driver.identify()
    return driver, io


class ExtendedDetectorTests(unittest.TestCase):
    def test_ten_models_four_detectors_native_start_result_stop(self):
        for model in EXTENDED_RANGES:
            for detector in DETECTORS:
                with self.subTest(model=model, detector=detector):
                    driver, io = driver_for(model, detector)
                    result = driver.read_verified_level(**(ARGS | {'detector': detector}))
                    self.assertEqual(result.value, 36.5)
                    self.assertEqual(result.unit, 'dBuV')
                    self.assertEqual(result.readbacks['before'], result.readbacks['after'])
                    self.assertEqual(result.readbacks['capability']['firmware'], 'A.02.00')
                    if model.startswith('FSW'):
                        self.assertIn('CALC:MARK1:FUNC:FME:DET '+DETECTORS[detector], io.events)
                        self.assertLess(io.events.index('INIT:IMM'), io.events.index('CALC:MARK1:FUNC:FME:RES?'))
                        self.assertNotIn('TRAC:DATA? TRACE1', io.events)
                    elif model.startswith('N'):
                        self.assertIn('AVER:TYPE SCAL', io.events)
                        self.assertIn('FREQ:SPAN 0', io.events)
                        self.assertIn('CALC:MAM:COUP OFF', io.events)
                        self.assertNotIn('INIT:IMM', io.events)
                    else:
                        self.assertLess(io.events.index('INIT1:IMM'), io.events.index('TRAC? SINGLE'))
                        if model.startswith('ESU'):
                            self.assertIn('BAND:TYPE PULS', io.events)
                            self.assertNotIn('DISP:BARG:TCO OFF', io.events)
                    driver.stop()
                    self.assertIn('ABOR', io.events[-7:])

    def test_every_before_and_after_setting_is_required(self):
        for model in ('EPL1000', 'ESU8', 'FSW50', 'N9030B'):
            driver, _ = driver_for(model)
            reference = driver.read_verified_level(**ARGS).readbacks['before']
            for query in reference:
                for after in (False, True):
                    with self.subTest(model=model, query=query, after=after):
                        bad = [reference[query], 'UNKNOWN'] if after else 'UNKNOWN'
                        driver, io = driver_for(model, changes={query: bad})
                        with self.assertRaises(InstrumentError): driver.read_verified_level(**ARGS)

    def test_missing_options_and_unreviewed_a_firmware_reject_before_configuration(self):
        for model, changes, firmware in [('FSW50', {'*OPT?': 'K540'}, 'TEST'), ('N9030B', {'*OPT?': 'N6141A'}, 'TEST'),
                                        ('N9030B', {'*OPT?': ''}, 'TEST'), ('N9010A', {}, 'A.01.99'),
                                        ('N9010A', {}, 'UNKNOWN')]:
            driver, io = driver_for(model, changes=changes, firmware=firmware)
            with self.assertRaises(InstrumentError): driver.read_verified_level(**ARGS)
            self.assertEqual(io.events, ['*IDN?', '*OPT?'])

    def test_measure_at_marker_array_errors_never_become_scalar_success(self):
        for raw in ('-999,-999,-999,13560000', '36.5,12,-999,13560000', '36.5,-999,-999,13560001',
                    '36.5', 'NaN,-999,-999,13560000', '9.9e37,-999,-999,13560000'):
            driver, io = driver_for('N9030B', changes={'CALC:MARK1:FUNC:MAM?': raw})
            with self.assertRaises(InstrumentError): driver.read_verified_level(**ARGS)

    def test_fsw_initial_sweep_budget_and_drift_are_rejected(self):
        driver, io = driver_for('FSW50')
        driver.max_hz = ARGS['frequency_hz']
        with self.assertRaisesRegex(ValueError, 'initial narrow sweep'): driver.read_verified_level(**ARGS)
        self.assertEqual(io.events, ['*IDN?'])
        driver, io = driver_for('FSW50', changes={'SWE:TIME?': '30'})
        with self.assertRaises(ValueError): driver.read_verified_level(**ARGS)
        self.assertNotIn('INIT:IMM', io.events)
        driver, io = driver_for('FSW50', changes={'SWE:TIME?': ['0.1', '0.2']})
        with self.assertRaises(InstrumentError): driver.read_verified_level(**ARGS)

    def test_limits_are_checked_without_io_and_legacy_method_is_blocked(self):
        for model in EXTENDED_RANGES:
            for changes in ({'frequency_hz': EXTENDED_RANGES[model]+1}, {'rbw_hz': 120000},
                            {'dwell_seconds': .1}, {'dwell_seconds': 61}, {'attenuation_db': 55}):
                driver, io = driver_for(model)
                with self.assertRaises(ValueError): driver.read_verified_level(**(ARGS | changes))
                self.assertEqual(io.events, ['*IDN?'])
        driver, io = driver_for('N9030B')
        with self.assertRaises(InstrumentError): driver.read_level(**ARGS)
