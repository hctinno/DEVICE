import json
import math
import socketserver
import threading
import time
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT.parent/'samsung-rf'))
from dgm_lab import *
from dgm_lab.core import Scpi, scalar, switch
from dgm_lab.transport import Transport
from dgm_lab.registry import connect
from dgm_lab.phone import measure_during_phone_tx, latest_phone_support


class Scripted(Transport):
    """Strict response fixture. Unknown queries fail instead of returning success."""
    def __init__(self, responses, timeout=30):
        super().__init__('fixture://manual',timeout)
        self.responses=dict(responses)
        self.events=[]
        self.command=None

    def _write(self,command):
        self.command=command;self.events.append(command)

    def _read(self):
        value=self.responses[self.command]
        if isinstance(value,list):
            value=value.pop(0)
        if isinstance(value,BaseException):
            raise value
        return value

    def _close(self): pass


def fixture(model, maker='Keysight Technologies', **responses):
    base={'*IDN?':f'{maker},{model},SIMULATED,fixture-1', '*OPC?':'1', 'SYST:ERR?':'0,"No error"'}
    base.update(responses)
    return Scripted(base)


def source_fixture(model='N5182B'):
    maker='Keysight Technologies' if model.startswith(('N','E')) else 'Rohde&Schwarz'
    io=fixture(model,maker,**{'OUTP?':['0','1','0'], 'SOUR:FREQ:CW?':'2.412E9','SOUR:POW?':'-20'})
    driver=SignalGenerator(io,model=model,max_frequency_hz=6e9,max_power_dbm=-10)
    driver.identify()
    return io,driver


class ValidationTests(unittest.TestCase):
    def test_wrong_model_or_manufacturer_never_writes(self):
        for response in ('Keysight Technologies,N9030A,S,F','Other,N9030B,S,F','invalid'):
            io=Scripted({'*IDN?':response})
            device=SpectrumAnalyzer(io,model='N9030B',max_frequency_hz=26.5e9)
            with self.assertRaises(UnsupportedInstrument): device.identify()
            self.assertEqual(io.events,['*IDN?'])

    def test_unidentified_output_blocked(self):
        io=fixture('N5182B')
        source=SignalGenerator(io,model='N5182B',max_frequency_hz=6e9,max_power_dbm=-10)
        with self.assertRaises(UnsupportedInstrument): source.configure_cw(frequency_hz=1e9,power_dbm=-30)
        self.assertEqual(io.events,[])

    def test_unsupported_model_before_open(self):
        with self.assertRaises(UnsupportedInstrument):
            with connect({'driver':'SignalGenerator','parameters':dict(model='CMX500',max_frequency_hz=6e9,max_power_dbm=0)}): pass

    def test_numeric_sentinels_are_not_measurements(self):
        for raw in ('NaN','inf','-inf','9.91E37','-9.9E37','OVER','1,2',''):
            with self.subTest(raw=raw),self.assertRaises(InstrumentError): scalar(raw)
        self.assertEqual(scalar('-1.234E-3'),-.001234)

    def test_unknown_switch_not_truthy(self):
        with self.assertRaises(InstrumentError): switch('2')
        self.assertFalse(switch('OFF'))

    def test_invalid_config_has_zero_io(self):
        io,driver=source_fixture()
        baseline=list(io.events)
        for kwargs in (dict(frequency_hz=True,power_dbm=-20),dict(frequency_hz=6e9+1,power_dbm=-20),
                       dict(frequency_hz=1e9,power_dbm=math.nan),dict(frequency_hz=1e9,power_dbm=0)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError): driver.configure_cw(**kwargs)
        self.assertEqual(io.events,baseline)

    def test_sweep_invalid_values_before_io(self):
        c=Sweep(1e9,2e9,1e6,3e6,-10,10)
        io=fixture('N9030B');d=SpectrumAnalyzer(io,model='N9030B',max_frequency_hz=3e9)
        for invalid in (replace(c,points=True),replace(c,rbw_hz=math.inf),replace(c,start_hz=2e9),replace(c,detector='POS;*RST')):
            with self.assertRaises(ValueError): d.acquire(invalid)
        self.assertEqual(io.events,[])

    def test_error_queue_preserved_and_bounded(self):
        io=fixture('N5182B',**{'SYST:ERR?':['-222,"range"','0,"No error"']})
        d=Scpi(io,model='N5182B',manufacturers=['Keysight Technologies']);d.identify()
        with self.assertRaisesRegex(InstrumentError,'-222'): d.apply(['OUTP ON'])
        self.assertNotIn('OUTP ON',io.events)
        io.responses['SYST:ERR?']='-200,"persistent"'
        with self.assertRaisesRegex(InstrumentError,'did not clear'): d.errors(limit=2)

    def test_query_or_line_in_write_rejected(self):
        io=Scripted({})
        for command in ('*IDN?','FREQ 1\nOUTP ON','FREQ 1\r',''):
            with self.assertRaises(ValueError): io.write(command)
        self.assertEqual(io.events,[])

    def test_timeout_poison_no_retry(self):
        io=Scripted({'READ?':TimeoutError('fixture timeout')})
        with self.assertRaises(TimeoutError): io.query('READ?')
        with self.assertRaises(CommunicationError): io.query('READ?')
        self.assertEqual(io.events,['READ?'])

    def test_reidentify_invalidates_config(self):
        io,d=source_fixture();d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
        d.identify()
        with self.assertRaises(InstrumentError): d.start()


class DriverTests(unittest.TestCase):
    def test_hp_native_identity_and_triggered_measurement(self):
        status='000000110010001A0010000001'
        self.assertEqual(len(status),26)
        io=Scripted({'*IDN?':'HEWLETT-PACKARD,437B,1.5','ERR?':'000','SM':status,'TR2':'-2.0000E+01'})
        d=Hp437B(io);d.identify();d.configure(frequency_hz=300e6,sensor_table=1)
        self.assertEqual(d.read_power().value,-20);d.stop()
        self.assertIn('FR300000000HZ',io.events)
        self.assertNotIn('SYST:ERR?',io.events)

    def test_all_rf_sources_on_off(self):
        for model in SignalGenerator.MODELS:
            with self.subTest(model=model):
                io,d=source_fixture(model)
                d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
                with d.emitting(): pass
                self.assertLess(io.events.index('OUTP OFF'),io.events.index('SOUR:FREQ:CW 2412000000'))
                self.assertIn('OUTP ON',io.events)
                self.assertEqual([x for x in io.events if x=='OUTP OFF'],['OUTP OFF','OUTP OFF'])
                self.assertNotIn('*RST',io.events)

    def test_exception_and_ctrl_c_stop_rf(self):
        for exc in (ValueError('measurement failed'),KeyboardInterrupt()):
            io,d=source_fixture();d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
            with self.assertRaises(type(exc)):
                with d.emitting(): raise exc
            self.assertEqual(io.events[-4:],['OUTP OFF','*OPC?','OUTP?','SYST:ERR?'])

    def test_start_partial_failure_still_stops(self):
        io,d=source_fixture();d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
        io.responses['OUTP?']=['0','0']
        with self.assertRaisesRegex(InstrumentError,'ON readback'):
            with d.emitting(): self.fail('should not enter')
        self.assertEqual(io.events.count('OUTP OFF'),2)

    def test_original_error_and_off_failure_both_preserved(self):
        io,d=source_fixture();d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
        io.responses['OUTP?']=['1','1']
        with self.assertRaises(BaseExceptionGroup) as caught:
            with d.emitting(): raise ValueError('original acquisition failure')
        self.assertIn('original acquisition failure',str(caught.exception.exceptions[0]))
        self.assertIn('RF OFF',str(caught.exception.exceptions[1]))

    def test_readback_mismatch_blocks_on(self):
        io,d=source_fixture();io.responses['SOUR:FREQ:CW?']='1e9'
        with self.assertRaisesRegex(InstrumentError,'mismatch'): d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
        with self.assertRaises(InstrumentError): d.start()
        self.assertNotIn('OUTP ON',io.events)

    def test_supplies_voltage_current_and_off(self):
        for model in PowerSupply.MODELS:
            maker='KIKUSUI' if model=='PWR2001ML' else 'Agilent Technologies'
            io=fixture(model,maker,**{'OUTP?':['0','1','0'],'VOLT?':'4.2','CURR?':'1.2','MEAS:VOLT?':'4.199','MEAS:CURR?':'0.4'})
            d=PowerSupply(io,model=model,max_voltage=5,max_current=2);d.identify()
            d.configure(voltage=4.2,current_limit=1.2,range_name={'E3640A':'P8V','E3632A':'P15V'}.get(model))
            with d.powering():
                self.assertEqual(d.read_voltage().unit,'V');self.assertEqual(d.read_current().value,.4)
            self.assertNotIn('*RST',io.events)

    def test_supply_range_limits_before_io(self):
        io=fixture('E3640A');d=PowerSupply(io,model='E3640A',max_voltage=30,max_current=5)
        with self.assertRaises(ValueError): d.configure(voltage=20,current_limit=3,range_name='P20V')
        self.assertEqual(io.events,[])

    def test_pseries_channel_route_and_power(self):
        io=fixture('N1912A',**{'SENS2:FREQ?':'6e9','UNIT1:POW?':'DBM','READ1?':'-23.75'})
        d=PSeriesPowerMeter(io,model='N1912A');d.identify();d.configure_average(frequency_hz=6e9,channel=2)
        self.assertEqual(d.read_power().value,-23.75)
        self.assertIn('CONF1:POW:AC DEF,DEF,(@2)',io.events)
        d.stop()

    def test_pseries_channel_two_not_on_single_input_model(self):
        io=fixture('N1911A');d=PSeriesPowerMeter(io,model='N1911A')
        with self.assertRaises(ValueError): d.configure_average(frequency_hz=1e9,channel=2)
        self.assertEqual(io.events,[])

    def test_usb_sensor_units_and_measurement(self):
        for model in UsbPowerSensor.MODELS:
            key=model=='U2000A'
            io=fixture(model,'Agilent Technologies' if key else 'Rohde&Schwarz',
                       **{'SENS:FREQ?':'2.4e9','READ?':'-20','FETC?':'1e-5','UNIT:POW?':'DBM' if key else 'W'})
            d=UsbPowerSensor(io,model=model);d.identify();d.configure_average(frequency_hz=2.4e9)
            result=d.read_power()
            self.assertEqual(result.unit,'dBm' if key else 'W')
            d.stop()
            if key:
                self.assertLess(io.events.index('SENS:DET:FUNC AVER'),io.events.index('INIT:CONT OFF'))

    def test_all_spectrum_dialects_return_new_trace(self):
        config=Sweep(1e9,2e9,1e6,3e6,-10,10,101,'POS',.01)
        for model,(_,dialect) in SpectrumAnalyzer.MODELS.items():
            with self.subTest(model=model):
                io=fixture(model,'Keysight Technologies' if dialect in ('keysight','psa') else 'Rohde&Schwarz',**{
                    'FREQ:STAR?':'1e9','FREQ:STOP?':'2e9','BAND:RES?':'1e6','BAND:VID?':'3e6',
                    'SWE:POIN?':'101','SWE:TIME?':'.01','POW:ATT?':'10','INP:ATT?':'10',
                    'DISP:WIND:TRAC:Y:RLEV?':'-10','UNIT:POW?':'DBM','CALC:UNIT:POW?':'DBM',
                    'TRAC:DATA? TRACE1':','.join(['-40']*101)})
                d=SpectrumAnalyzer(io,model=model,max_frequency_hz=3e9);d.identify()
                result=d.acquire(config)
                self.assertEqual(result.frequencies_hz[-1],2e9);self.assertEqual(len(result.values_dbm),101)
                self.assertLess(io.events.index('INIT:IMM'),io.events.index('TRAC:DATA? TRACE1'))
                io.responses['TRAC:DATA? TRACE1']='-40,-50'
                with self.assertRaisesRegex(InstrumentError,'count'): d.acquire(config)

    def test_receiver_single_detector_returns_dbuv(self):
        for model in EmiReceiver.MODELS:
            io=fixture(model,'Rohde&Schwarz',**{'FREQ:CENT?':'1e6','BAND?':'9000','TRAC? SINGLE':'36.5'})
            d=EmiReceiver(io,model=model,max_frequency_hz=3e9);d.identify()
            value=d.read_level(frequency_hz=1e6,rbw_hz=9000,detector='QPE',dwell_seconds=1,attenuation_db=10)
            self.assertEqual(value.unit,'dBuV');self.assertEqual(value.value,36.5);d.stop()

    def test_conditional_controller_requires_site_confirmation(self):
        with self.assertRaises(UnsupportedInstrument): Thermotron8800(None,channel=1,minimum=-40,maximum=85,acknowledgement=False)
        with self.assertRaises(UnsupportedInstrument): EspecController(None,expected_rom='P300',minimum_c=-40,maximum_c=85)

    def test_thermotron_ack_modes_and_stop(self):
        for acknowledgement in (True,False):
            io=Scripted({'IDEN?':'8800 CHAMBER CONTROLLER','IERR?':'0',
                         'RUNM':'0','STOP':'0','SETP1,25':'0','STAT?':['16','16','0'],
                         'SETP1?':'25.0','PVAR1?':'24.8'})
            d=Thermotron8800(io,channel=1,minimum=-40,maximum=85,acknowledgement=acknowledgement,installed_controller_confirmed=True)
            d.identify()
            with d.running(): d.setpoint(25);self.assertEqual(d.read_process(),24.8)
            self.assertIn('STOP',io.events)

    def test_espec_setpoint_start_standby_and_error(self):
        io=Scripted({'ROM?':'P300 fixture','MODE,STANDBY':'OK','MODE?':['STANDBY','CONSTANT','STANDBY'],
                     'TEMP?':['24,20,100,-40','24,25,100,-40'],'TEMP, S25.0':'OK','MODE,CONSTANT':'OK'})
        d=EspecController(io,expected_rom='P300 fixture',minimum_c=-30,maximum_c=80,installed_controller_confirmed=True)
        d.identify();d.configure(temperature_c=25)
        with d.running(): pass
        io.responses['TEMP?']='NA:DATA ERROR'
        with self.assertRaisesRegex(InstrumentError,'DATA ERROR'): d.temperature()

    def test_cmw_state_sequence_and_stop(self):
        from dgm_rf.cmw_lte import LteRmcConfig
        io=fixture('CMW500','Rohde&Schwarz',**{
            'SOURce:LTE:SIGNaling1:CELL:STATe:ALL?':['ON,ADJ','OFF,ADJ'],
            'FETCh:LTE:SIGNaling1:PSWitched:STATe?':['ATT','CEST']})
        d=CmwLte(io,site_profile_confirmed=True);d.identify()
        d.configure(LteRmcConfig(1,18000,20,100))
        with d.connected(timeout=1): pass
        self.assertIn('CALL:LTE:SIGNaling1:PSWitched:ACTion DISConnect',io.events)
        self.assertEqual(io.events[-2:],[d.plan['off_query'],'SYST:ERR?'])

    def test_cmw_cancel_before_attach_runs_cleanup(self):
        from dgm_rf.cmw_lte import LteRmcConfig
        io=fixture('CMW500','Rohde&Schwarz',**{'SOURce:LTE:SIGNaling1:CELL:STATe:ALL?':'OFF,ADJ'})
        d=CmwLte(io,site_profile_confirmed=True);d.identify();d.configure(LteRmcConfig(1,18000,20,100))
        cancelled=threading.Event();cancelled.set()
        with self.assertRaises(InterruptedError):
            with d.connected(timeout=1,cancelled=cancelled): pass
        self.assertIn(d.plan['cleanup'][1],io.events)

    def test_vna_both_dialects_complex_data_and_off(self):
        for model in ('ZNLE6','ZNB8-2Port','ZNB8-4Port','ZNB20-2Port','ZNB20-4Port','Planar R140'):
            cmt=model=='Planar R140'
            io=fixture(model,'Copper Mountain Technologies' if cmt else 'Rohde&Schwarz',**{
                'OUTP?':['0','0'],'SENS1:FREQ:STAR?':'1e9','SENS1:FREQ:STOP?':'2e9','SENS1:SWE:POIN?':'2',
                'SOUR1:POW?':'-20','SENS1:CORR:STAT?':'1',
                'CALC1:DATA:SDAT?' if cmt else 'CALC1:DATA? SDAT':'0.1,0.2,0.3,0.4',
                'SENS1:FREQ:DATA?' if cmt else 'CALC1:DATA:STIM?':'1e9,2e9'})
            d=VectorNetworkAnalyzer(io,model=model,max_frequency_hz=3e9,max_power_dbm=-10);d.identify()
            result=d.acquire_s11(start_hz=1e9,stop_hz=2e9,points=2,if_bandwidth_hz=1000,power_dbm=-20)
            self.assertEqual(result.s11,(.1+.2j,.3+.4j));self.assertEqual(io.events.count('OUTP OFF'),2)

    def test_phone_cleanup_wraps_measurement_failure(self):
        from dgm_rf import Controller, Profile, ScriptedTransport, WlanTxConfig
        profile=Profile.load(ROOT.parent/'samsung-rf/profiles/simulation.json')
        phone=Controller(ScriptedTransport(),profile)
        config=WlanTxConfig(band=3,bandwidth=9,channel_argument=17,rate=15,antenna=1,gi=5,encoding=1,power='0.0',burst=1000,payload=1000)
        with self.assertRaisesRegex(ValueError,'measurement failed'):
            measure_during_phone_tx(phone=phone,config=config,acquire=lambda:(_ for _ in ()).throw(ValueError('measurement failed')))
        self.assertFalse(latest_phone_support('SM-F971U')['direct_tx_supported'])


@contextmanager
def tcp_server(responder):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            while True:
                try:
                    line=self.rfile.readline()
                except (ConnectionResetError,ConnectionAbortedError):
                    return
                if not line:
                    return
                response=responder(line.decode().strip())
                if response is None: return
                chunks=response if isinstance(response,list) else [response]
                for chunk in chunks:
                    if isinstance(chunk,float): time.sleep(chunk)
                    else:
                        try: self.wfile.write(chunk);self.wfile.flush()
                        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError): return
    server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler)
    server.daemon_threads=True
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try: yield server.server_address
    finally: server.shutdown();server.server_close();worker.join(timeout=2)


class SocketTests(unittest.TestCase):
    def test_fragmented_socket_real_driver_rf_cycle(self):
        state={'out':False,'frequency':None,'power':None};traffic=[]
        def respond(command):
            traffic.append(command)
            if command=='*IDN?': return [b'Keysight Tech',.005,b'nologies,N5182B,SIMULATED,1\n']
            if command=='SYST:ERR?': return b'0,"No error"\n'
            if command=='*OPC?': return b'1\n'
            if command=='OUTP?': return b'1\n' if state['out'] else b'0\n'
            if command=='SOUR:FREQ:CW?': return f"{state['frequency']}\n".encode()
            if command=='SOUR:POW?': return f"{state['power']}\n".encode()
            if command.startswith('OUTP '): state['out']=command.endswith(' ON')
            elif command.startswith('SOUR:FREQ:CW '): state['frequency']=float(command.split()[1])
            elif command.startswith('SOUR:POW '): state['power']=float(command.split()[1].replace('DBM',''))
            return []
        with tcp_server(respond) as address:
            with SocketTransport(*address,timeout=1) as io:
                d=SignalGenerator(io,model='N5182B',max_frequency_hz=6e9,max_power_dbm=-10)
                d.identify();d.configure_cw(frequency_hz=2.412e9,power_dbm=-20)
                with self.assertRaises(ValueError):
                    with d.emitting():
                        self.assertTrue(state['out']);raise ValueError('callback failure')
                self.assertFalse(state['out'])
        self.assertNotIn('*RST',traffic)

    def test_timeout_late_response_cannot_be_reused(self):
        with tcp_server(lambda command:[.15,b'1\n']) as address:
            with SocketTransport(*address,timeout=.04) as io:
                with self.assertRaises(TimeoutError): io.query('*OPC?')
                with self.assertRaises(CommunicationError): io.query('*IDN?')

    def test_disconnect_incomplete_response(self):
        with tcp_server(lambda command:None) as address:
            with SocketTransport(*address,timeout=.2) as io:
                with self.assertRaises(CommunicationError): io.query('*IDN?')

    def test_oversized_response_rejected(self):
        with tcp_server(lambda command:b'a'*100+b'\n') as address:
            with SocketTransport(*address,timeout=.2,max_bytes=16) as io:
                with self.assertRaisesRegex(CommunicationError,'max_bytes'): io.query('*IDN?')

    def test_cr_termination_for_controller(self):
        with tcp_server(lambda command:b'8800 CHAMBER CONTROLLER\r') as address:
            # Server reads LF; direct test uses LF write/CR response to isolate parser.
            with SocketTransport(*address,timeout=.2,termination=b'\r') as io:
                io._write=lambda command:io.socket.sendall(command.encode()+b'\n')
                self.assertEqual(io.query('IDEN?'),'8800 CHAMBER CONTROLLER')


if __name__=='__main__': unittest.main()
