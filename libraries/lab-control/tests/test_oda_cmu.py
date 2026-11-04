import unittest
from test_control import Scripted
from dgm_lab import OdaEx, Cmu200Cw, InstrumentError, UnsupportedInstrument


def oda():
    io = Scripted({'*IDN?':'ODA Technologies,EX-Series,1.3-1.3-1.2', '*SN?':'FIXTURE',
                   'SYST:ERR?':'0,"No error"', 'OUTP?':['0','0','1','0'],
                   'VOLT:OVP:TRIP?':'0', 'CURR:OCP:TRIP?':'0',
                   'VOLT:UVL?':'0', 'VOLT:OVL?':'60', 'CURR:UCL?':'0', 'CURR:OCL?':'40',
                   'VOLT?':'5.00', 'CURR?':'1.00', 'MEAS:VOLT?':'4.99', 'MEAS:CURR?':'0.8'})
    dev = OdaEx(io, expected_serial='FIXTURE', expected_firmware='1.3-1.3-1.2',
                max_voltage=5, max_current=1, installed_model_confirmed=True)
    return io, dev


def cmu():
    io = Scripted({'0;*IDN?':'Rohde&Schwarz,CMU200,FIXTURE,5.21',
                   '0;SYST:REM:ADDR:SEC? 7':'"RF_NSig"', '0;SYST:ERR?':'0,"No error"',
                   '7;FETC:RFG:TX:STAT?':['OFF','OFF','RUN','OFF'], '7;*OPC?':'1',
                   '7;OUTP:TX?':'RF2', '7;SOUR:CORR:LOSS:OUTP2:TX?':'0',
                   '7;SOUR:RFG:TX:FREQ?':'2412000000', '7;SOUR:RFG:TX:LEV?':'-30',
                   '7;SOUR:RFG:MOD?':'OFF', '7;SOUR:RFG:FHOP:STAT?':'0', '7;SOUR:RFG:PULS:STAT?':'0'})
    dev = Cmu200Cw(io, secondary_address=7, output_port=2, max_frequency_hz=2.7e9,
                   max_power_dbm=-20, expected_firmware='5.21', site_profile_confirmed=True)
    return io, dev


class OdaTests(unittest.TestCase):
    def test_cycle_no_opc_and_measurement_units(self):
        io, dev = oda(); dev.identify(); dev.configure(voltage=5, current=1)
        with dev.powering():
            self.assertEqual(dev.read_voltage().unit, 'V')
            self.assertEqual(dev.read_current().value, 0.8)
        self.assertIn('APPL 5,1', io.events)
        self.assertIn('OUTP OFF', io.events)
        self.assertNotIn('*OPC?', io.events)
        self.assertIsNone(dev.plan)

    def test_family_identity_does_not_replace_serial_binding(self):
        io, dev = oda(); io.responses['*SN?'] = 'ANOTHER'
        with self.assertRaises(UnsupportedInstrument): dev.identify()
        self.assertIsNone(dev.identity)
        self.assertTrue(all('?' in c for c in io.events))

    def test_site_and_installed_limits(self):
        io, dev = oda(); dev.identify()
        with self.assertRaises(ValueError): dev.configure(voltage=6, current=1)
        io.responses['VOLT:OVL?'] = '4'
        with self.assertRaises(InstrumentError): dev.configure(voltage=5, current=1)
        self.assertFalse(any(c.startswith('APPL ') for c in io.events))

    def test_existing_output_or_trip_blocks_configure(self):
        for key in ('OUTP?', 'VOLT:OVP:TRIP?', 'CURR:OCP:TRIP?'):
            io, dev = oda(); dev.identify(); io.responses[key] = '1'
            with self.assertRaises(InstrumentError): dev.configure(voltage=5, current=1)
            self.assertFalse(any(c.startswith('APPL ') for c in io.events))

    def test_readback_failure_never_enables(self):
        io, dev = oda(); dev.identify(); io.responses['VOLT?'] = '4.9'
        with self.assertRaises(InstrumentError): dev.configure(voltage=5, current=1)
        with self.assertRaises(InstrumentError): dev.start()
        self.assertNotIn('OUTP ON', io.events)

    def test_start_failure_still_stops(self):
        io, dev = oda(); dev.identify(); dev.configure(voltage=5, current=1)
        io.responses['OUTP?'] = ['0','0','0']
        with self.assertRaises(InstrumentError):
            with dev.powering(): self.fail('must not yield')
        self.assertIn('OUTP OFF', io.events)

    def test_cleanup_error_preserves_primary(self):
        io, dev = oda(); dev.identify(); dev.configure(voltage=5, current=1)
        io.responses['OUTP?'] = ['0','1','1']
        with self.assertRaises(ExceptionGroup) as caught:
            with dev.powering(): raise ValueError('measurement failed')
        self.assertEqual(len(caught.exception.exceptions), 2)


class CmuTests(unittest.TestCase):
    def test_cw_cycle_all_commands_addressed(self):
        io, dev = cmu(); dev.identify(); dev.configure(frequency_hz=2412e6, power_dbm=-30)
        with dev.emitting(): pass
        self.assertIn('7;INIT:RFG:TX', io.events)
        self.assertIn('7;ABOR:RFG:TX', io.events)
        self.assertTrue(all(c.startswith(('0;','7;')) for c in io.events))
        self.assertFalse(any('ADDR:SEC ' in c or '*RST' in c for c in io.events))

    def test_wrong_mapping_and_firmware_block(self):
        for key, value in [('0;SYST:REM:ADDR:SEC? 7','"Bluetooth_Sig"'),
                           ('0;*IDN?','Rohde&Schwarz,CMU200,FIXTURE,4.00')]:
            io, dev = cmu(); io.responses[key] = value
            with self.assertRaises(UnsupportedInstrument): dev.identify()
            self.assertIsNone(dev.identity)
            self.assertTrue(all('?' in c for c in io.events))

    def test_port_and_power_limits_prevent_io(self):
        io, dev = cmu(); dev.identify(); before = list(io.events)
        for kwargs in [dict(frequency_hz=6e9,power_dbm=-30),dict(frequency_hz=1e9,power_dbm=0)]:
            with self.assertRaises(ValueError): dev.configure(**kwargs)
        self.assertEqual(io.events, before)

    def test_settings_drift_rejects_start(self):
        for key, value in [('7;OUTP:TX?','RF3'), ('7;SOUR:CORR:LOSS:OUTP2:TX?','3'),
                           ('7;SOUR:RFG:MOD?','AM'), ('7;SOUR:RFG:FHOP:STAT?','1')]:
            io, dev = cmu(); dev.identify(); dev.configure(frequency_hz=2412e6,power_dbm=-30)
            io.responses[key] = value
            with self.assertRaises(InstrumentError): dev.start()
            self.assertNotIn('7;INIT:RFG:TX', io.events)

    def test_failed_start_aborts(self):
        io, dev = cmu(); dev.identify(); dev.configure(frequency_hz=2412e6,power_dbm=-30)
        io.responses['7;FETC:RFG:TX:STAT?'] = ['OFF','ERR','OFF']
        with self.assertRaises(InstrumentError):
            with dev.emitting(): self.fail('must not yield')
        self.assertIn('7;ABOR:RFG:TX', io.events)

    def test_default_profiles_block_before_transport(self):
        for cls in (OdaEx, Cmu200Cw):
            with self.assertRaises(UnsupportedInstrument): cls(None)

    def test_invalid_reconfigure_invalidates_previous_start_plan(self):
        for factory, good, bad in ((oda,dict(voltage=5,current=1),dict(voltage=999,current=1)),
                                  (cmu,dict(frequency_hz=2412e6,power_dbm=-30),dict(frequency_hz=6e9,power_dbm=-30))):
            io, dev = factory(); dev.identify(); dev.configure(**good)
            before = list(io.events)
            with self.assertRaises(ValueError): dev.configure(**bad)
            with self.assertRaises(InstrumentError): dev.start()
            self.assertEqual(io.events,before)


if __name__ == '__main__': unittest.main()
