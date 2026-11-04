"""Fault cases that can otherwise leave outputs on or label stale data as measured."""
import sys
import types
import unittest
from unittest.mock import Mock, patch
from test_control import fixture, Scripted
from dgm_lab import CmwLte, VectorNetworkAnalyzer, PowerSupply, InstrumentError
from dgm_lab.transport import VisaTransport, SerialTransport, CommunicationError
from dgm_rf.cmw_lte import LteRmcConfig


class FailureTests(unittest.TestCase):
    def test_cmw_failed_config_retains_cleanup_instance(self):
        io=fixture('CMW500','Rohde&Schwarz',**{'SYST:ERR?':['0','-222,"bad config"','0'],
                   'SOURce:LTE:SIGNaling2:CELL:STATe:ALL?':'OFF,ADJ'})
        d=CmwLte(io,site_profile_confirmed=True);d.identify()
        with self.assertRaises(InstrumentError): d.configure(LteRmcConfig(1,18000,20,100,instance=2))
        with self.assertRaises(InstrumentError): d.start()
        io.responses['SYST:ERR?']='0'
        d.stop()
        self.assertIn('SOURce:LTE:SIGNaling2:CELL:STATe OFF',io.events)
        self.assertNotIn('SOURce:LTE:SIGNaling2:CELL:STATe ON',io.events)

    def test_cmw_cannot_abandon_active_instance(self):
        io=fixture('CMW500','Rohde&Schwarz')
        d=CmwLte(io,site_profile_confirmed=True);d.identify()
        d.configure(LteRmcConfig(1,18000,20,100));d.active=True
        events=list(io.events)
        with self.assertRaisesRegex(InstrumentError,'Stop the current'):
            d.configure(LteRmcConfig(1,18000,20,100,instance=2))
        self.assertEqual(io.events,events)
        self.assertIn('SIGNaling1',d.plan['off_query'])

    def test_vna_no_calibration_never_enables_rf(self):
        io=fixture('ZNLE6','Rohde&Schwarz',**{
            'OUTP?':'0','SENS1:FREQ:STAR?':'1e9','SENS1:FREQ:STOP?':'2e9',
            'SENS1:SWE:POIN?':'2','SOUR1:POW?':'-20','SENS1:CORR:STAT?':'0'})
        d=VectorNetworkAnalyzer(io,model='ZNLE6',max_frequency_hz=6e9,max_power_dbm=-10);d.identify()
        with self.assertRaisesRegex(InstrumentError,'calibration'):
            d.acquire_s11(start_hz=1e9,stop_hz=2e9,points=2,if_bandwidth_hz=1000,power_dbm=-20)
        self.assertNotIn('OUTP ON',io.events)
        self.assertEqual(io.events.count('OUTP OFF'),2)

    def test_kikusui_delayed_status_does_not_resend_output(self):
        io=fixture('PWR2001ML','KIKUSUI',**{'OUTP?':['1','0']})
        d=PowerSupply(io,model='PWR2001ML',max_voltage=5,max_current=1);d.identify()
        d.stop()
        self.assertEqual(io.events.count('OUTP OFF'),1)
        self.assertEqual(io.events.count('OUTP?'),2)

    def test_visa_session_options_units_and_close(self):
        instrument=Mock();instrument.read.return_value='1\n'
        manager=Mock();manager.open_resource.return_value=instrument
        module=types.SimpleNamespace(ResourceManager=Mock(return_value=manager))
        with patch.dict(sys.modules,{'pyvisa':module}):
            with VisaTransport('GPIB0::13::INSTR',timeout=1.5,backend='@test',resource_options={'send_end':True}) as io:
                self.assertEqual(io.query('*OPC?'),'1')
                self.assertEqual(instrument.timeout,1500)
                self.assertEqual(instrument.read_termination,'\n')
            instrument.close.assert_called_once();manager.close.assert_called_once()
            manager.open_resource.assert_called_once_with('GPIB0::13::INSTR',send_end=True)

    def test_visa_partial_setup_closes_opened_resource(self):
        class Broken:
            close=Mock()
            @property
            def timeout(self): return 0
            @timeout.setter
            def timeout(self,value): raise RuntimeError('fixture VISA setup failure')
        instrument=Broken();manager=Mock();manager.open_resource.return_value=instrument
        with patch.dict(sys.modules,{'pyvisa':types.SimpleNamespace(ResourceManager=lambda:manager)}):
            with self.assertRaisesRegex(RuntimeError,'setup failure'):
                VisaTransport('USB0::1::2::TEST::INSTR')
        instrument.close.assert_called_once();manager.close.assert_called_once()

    def test_serial_explicit_settings_and_framing(self):
        port=Mock();port.write.return_value=7;port.read_until.return_value=b'OK\r\n'
        module=types.SimpleNamespace(Serial=Mock(return_value=port))
        with patch.dict(sys.modules,{'serial':module}):
            with SerialTransport('COM_TEST',baudrate=19200,parity='E',bytesize=7,stopbits=2,timeout=2) as io:
                self.assertEqual(io.query('TEST?'),'OK')
                port.write.assert_called_with(b'TEST?\r\n')
            module.Serial.assert_called_once_with(port='COM_TEST',baudrate=19200,parity='E',bytesize=7,stopbits=2,timeout=2,write_timeout=2)
            port.close.assert_called_once()

    def test_serial_truncated_reply_poisoned(self):
        port=Mock();port.write.return_value=7;port.read_until.return_value=b'PARTIAL'
        with patch.dict(sys.modules,{'serial':types.SimpleNamespace(Serial=lambda **kw:port)}):
            with SerialTransport('COM_TEST',baudrate=9600,parity='N',bytesize=8,stopbits=1) as io:
                with self.assertRaises(CommunicationError): io.query('TEST?')
                with self.assertRaises(CommunicationError): io.query('TEST?')
        port.write.assert_called_once()


if __name__=='__main__': unittest.main()
