"""Independent manual-response fixtures, not the SDK's synthetic equipment peer."""
import unittest
from dgm_lab import SpectrumAnalyzer, EmiReceiver, SignalGenerator, PowerSupply, UsbPowerSensor, DigitalMultimeter, Sweep
from dgm_lab.core import InstrumentError
from dgm_lab.model_scope import extra_models, SUPPLY_RANGES
from test_control import fixture


class ExpandedModelTests(unittest.TestCase):
    def test_all_added_spectrum_models_acquire_and_abort(self):
        for model in extra_models('SpectrumAnalyzer'):
            maker = 'Keysight Technologies' if model.startswith('N') else 'Rohde&Schwarz'
            io = fixture(model,maker,**{'FREQ:STAR?':'100e6','FREQ:STOP?':'101e6','BAND:RES?':'100000','BAND:VID?':'300000',
                'SWE:POIN?':'101','SWE:TIME?':'.1','POW:ATT?':'20','INP:ATT?':'20',
                'DISP:WIND:TRAC:Y:RLEV?':'0','UNIT:POW?':'DBM','CALC:UNIT:POW?':'DBM',
                'TRAC:DATA? TRACE1':','.join(['-45']*101)})
            d = SpectrumAnalyzer(io,model=model,max_frequency_hz=1e9)
            d.identify()
            trace = d.acquire(Sweep(100e6,101e6,100000,300000,0,20,101,'POS',.1))
            self.assertEqual((len(trace.values_dbm),trace.values_dbm[0]),(101,-45))
            d.stop()
            self.assertIn('ABOR',io.events[-4:])

    def test_all_added_sources_configure_and_verify_on_off(self):
        for model in extra_models('SignalGenerator'):
            io=fixture(model,**{'OUTP?':['0','1','0'],'SOUR:FREQ:CW?':'100e6','SOUR:POW?':'-30'})
            d=SignalGenerator(io,model=model,max_frequency_hz=1e9,max_power_dbm=-20)
            d.identify(); d.configure_cw(frequency_hz=100e6,power_dbm=-30)
            with d.emitting(): pass
            self.assertEqual(io.events.count('OUTP OFF'),2)
            self.assertIn('SOUR:FREQ:CW 100000000',io.events)

    def test_all_added_sensors_preserve_watts_or_dbm(self):
        for model in extra_models('UsbPowerSensor'):
            key=model.startswith('U200')
            io=fixture(model,'Keysight Technologies' if key else 'Rohde&Schwarz',
                       **{'SENS:FREQ?':'100e6','UNIT:POW?':'DBM' if key else 'W','READ?':'-30','FETC?':'1e-6'})
            d=UsbPowerSensor(io,model=model); d.identify(); d.configure_average(frequency_hz=100e6)
            result=d.read_power(); d.stop()
            self.assertEqual(result.unit,'dBm' if key else 'W')
            self.assertEqual(result.value,-30 if key else 1e-6)

    def test_all_supply_ranges_and_pre_io_rated_limits(self):
        for model in extra_models('PowerSupply'):
            for range_name in SUPPLY_RANGES[model]:
                io=fixture(model,**{'OUTP?':['0','1','0'],'VOLT?':'1','CURR?':'.05','VOLT:RANG?':range_name})
                d=PowerSupply(io,model=model,max_voltage=5,max_current=.1); d.identify()
                d.configure(voltage=1,current_limit=.05,range_name=range_name)
                with d.powering(): pass
                self.assertIn('VOLT:RANG '+range_name,io.events)
            io=fixture(model)
            d=PowerSupply(io,model=model,max_voltage=5,max_current=.1)
            with self.assertRaises(ValueError): d.configure(voltage=6,current_limit=.05,range_name=range_name)
            self.assertEqual(io.events,[])
        with self.assertRaises(ValueError): PowerSupply(None,model='E3641A',max_voltage=61,max_current=.1)

    def test_all_dmm_models_all_functions_and_drift(self):
        for model in extra_models('DigitalMultimeter'):
            for function,mnemonic,range_value,raw in [('DCV','VOLT',10,'4.1'),('ACV','VOLT:AC',1,'.2'),('RES2W','RES',1000,'499')]:
                replies={'CONF?':f'"{mnemonic} {range_value},1e-6"','SAMP:COUN?':'1','TRIG:COUN?':'1','TRIG:SOUR?':'IMM','READ?':raw}
                io=fixture(model,**replies)
                d=DigitalMultimeter(io,model=model,max_voltage=10); d.identify()
                d.configure(function=function,range_value=range_value)
                self.assertEqual(d.read().value,float(raw))
                io.responses['CONF?']='"CURR .1,1e-6"'
                with self.assertRaises(InstrumentError): d.read()
                d.stop()

    def test_dmm_bad_range_nonfinite_and_multireading_rejected(self):
        io=fixture('34461A'); d=DigitalMultimeter(io,model='34461A',max_voltage=10)
        for kwargs in [dict(function='DCV',range_value=100),dict(function='CURR',range_value=1),dict(function='RES2W',range_value=True)]:
            with self.assertRaises(ValueError): d.configure(**kwargs)
        self.assertEqual(io.events,[])
        for raw in ('nan','9.9E37','1,2'):
            io=fixture('34461A',**{'CONF?':'"VOLT 10,1e-6"','SAMP:COUN?':'1','TRIG:COUN?':'1','TRIG:SOUR?':'IMM','READ?':raw})
            d=DigitalMultimeter(io,model='34461A',max_voltage=10);d.identify();d.configure(function='DCV',range_value=10)
            with self.assertRaises(InstrumentError): d.read()

    def test_expansion_frequency_limit_rejects_before_io(self):
        from dgm_lab.model_scope import model_rows
        from dgm_lab.registry import DRIVERS
        from dgm_lab.core import UnsupportedInstrument
        for row in model_rows():
            name,model=row['driver'],row['model']
            parameters={'model':model}
            if name in {'SpectrumAnalyzer','EmiReceiver','SignalGenerator'}: parameters['max_frequency_hz']=1e9
            if name=='SignalGenerator': parameters['max_power_dbm']=-20
            if name=='PowerSupply': parameters.update(max_voltage=5,max_current=.1)
            if name=='DigitalMultimeter': parameters['max_voltage']=10
            io=fixture('WRONG-MODEL','Keysight Technologies' if row['source_id'].startswith('keysight') else 'Rohde&Schwarz')
            d=DRIVERS[name](io,**parameters)
            with self.assertRaises(UnsupportedInstrument): d.identify()
            self.assertEqual(io.events,['*IDN?'])
        for name,cls in [('SignalGenerator',SignalGenerator),('SpectrumAnalyzer',SpectrumAnalyzer),('UsbPowerSensor',UsbPowerSensor)]:
            for model in extra_models(name):
                io=fixture(model)
                d=cls(io,model=model,**({'max_frequency_hz':100e9,'max_power_dbm':0} if name=='SignalGenerator' else {'max_frequency_hz':100e9} if name=='SpectrumAnalyzer' else {}))
                with self.assertRaises(ValueError):
                    if name=='SignalGenerator': d.configure_cw(frequency_hz=6e9,power_dbm=-30)
                    elif name=='UsbPowerSensor': d.configure_average(frequency_hz=6e9)
                    else: d.acquire(Sweep(5e9,6e9,100000,300000,0,20,101,'POS',.1))
                self.assertEqual(io.events,[])

    def test_nrp_50mhz_lower_boundary_rejects_before_io(self):
        for model in extra_models('UsbPowerSensor'):
            if not model.startswith(('NRP40','NRP50','NRP67','NRP90')): continue
            io=fixture(model,'Rohde&Schwarz');d=UsbPowerSensor(io,model=model)
            for frequency in (10e6,49_999_999):
                with self.assertRaises(ValueError): d.configure_average(frequency_hz=frequency)
            self.assertEqual(io.events,[])
