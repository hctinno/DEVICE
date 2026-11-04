"""Strict synthetic SCPI peer for standalone equipment, not measurement physics.

Command grammar is a fixed whitelist independent of recipe/driver code. Unsupported
queries/writes fail; a configured power source changes output only on OUTP ON.
"""
from dgm_lab.transport import Transport
from dgm_lab.core import InstrumentError, scalar
import re


SIMULATED_DRIVERS = {'SpectrumAnalyzer','EmiReceiver','SignalGenerator','PowerSupply','UsbPowerSensor','DigitalMultimeter'}


class EquipmentPeer(Transport):
    def __init__(self, driver, model, *, log=None):
        super().__init__('simulation://' + driver + '/' + model, timeout=120, log=log)
        self.driver, self.model, self.reply = driver, model, None
        self.state = {'OUTP':'0', 'SAMP:COUN':'1', 'TRIG:COUN':'1'}
        self.output = False
        self.measurements = 0

    def _write(self, command):
        self.reply = None
        if command == '*IDN?':
            maker = 'Keysight Technologies' if re.match(r'^[NE]\d|^U200|^344|^6674A$',self.model) else 'Rohde&Schwarz'
            if self.model == 'PWR2001ML': maker = 'KIKUSUI'
            self.reply = f'{maker},{self.model},SIMULATION-ONLY,SIMULATED'
        elif command == '*OPC?': self.reply = '1'
        elif command == 'SYST:ERR?': self.reply = '0,"No error"'
        elif command == '*OPT?': self.reply = 'K54' if self.model.startswith('FSW') else 'EMC'
        elif command == 'CONF?': self.reply = self.state['CONF']
        elif command in {'READ?','FETC?','MEAS:VOLT?','MEAS:CURR?'}:
            self.measurements += 1
            if self.driver == 'DigitalMultimeter':
                self.reply = '99.5' if self.state['CONF'].startswith('"RES ') else '0.05'
            elif self.driver == 'PowerSupply':
                self.reply = self.state.get('VOLT' if command == 'MEAS:VOLT?' else 'CURR','0') if self.output else '0'
            else: self.reply = '-30' if self.model.startswith('U200') else '0.000001'
        elif command == 'TRAC:DATA? TRACE1':
            self.measurements += 1
            self.reply = ','.join('-60' for _ in range(int(float(self.state['SWE:POIN']))))
        elif command.endswith('?'):
            key = command[:-1]
            if key not in self.state: raise InstrumentError('Unsupported equipment query: ' + command)
            self.reply = self.state[key]
        elif command in {'ABOR','INIT','INIT:IMM','CONF:SAN','CONF'}: pass
        elif command.startswith(('CONF:VOLT:DC ','CONF:VOLT:AC ','CONF:RES ')):
            key, value = command.split(' ',1)
            scalar(value)
            function = {'CONF:VOLT:DC':'VOLT','CONF:VOLT:AC':'VOLT:AC','CONF:RES':'RES'}[key]
            self.state['CONF'] = f'"{function} {value},1e-6"'
        else:
            key, sep, value = command.partition(' ')
            numeric = {'FREQ:STAR','FREQ:STOP','BAND:RES','BAND:VID','POW:ATT','INP:ATT','DISP:WIND:TRAC:Y:RLEV',
                       'SWE:POIN','SWE:TIME','SOUR:FREQ:CW','SOUR:POW','VOLT','CURR','SENS:FREQ','SAMP:COUN','TRIG:COUN'}
            enums = {'INST:SEL':{'SA','SAN'}, 'INIT:CONT':{'OFF'}, 'FORM:DATA':{'ASC'},
                     'CALC:UNIT:POW':{'DBM'}, 'UNIT:POW':{'DBM','W'},
                     'BAND:RES:AUTO':{'OFF'}, 'BAND:VID:AUTO':{'OFF'}, 'POW:ATT:AUTO':{'OFF'}, 'INP:ATT:AUTO':{'OFF'},
                     'SWE:TIME:AUTO':{'OFF'}, 'DET':{'POS','NEG','SAMP','RMS','AVER'},
                     'TRAC1:TYPE':{'WRIT'}, 'TRAC1:MODE':{'WRIT'}, 'DISP:WIND:TRAC1:MODE':{'WRIT'},
                     'TRIG:SOUR':{'IMM'}, 'TRAC1:UPD':{'ON'}, 'TRAC1:DISP':{'ON'}, 'AVER:TYPE':{'RMS'},
                     'AVER':{'OFF'}, 'DISP:WIND:TRAC:X:SPAC':{'LIN'}, 'OUTP':{'ON','OFF'}, 'OUTP:MOD':{'OFF'},
                     'SOUR:MOD:ALL:STAT':{'OFF'}, 'SOUR:FREQ:MODE':{'CW'}, 'SOUR:POW:MODE':{'FIX'},
                     'VOLT:RANG':{'P8V','P20V','P35V','P60V','P15V','P30V'}, 'SENS:DET:FUNC':{'AVER'},
                     'SENS:FUNC':{'"POW:AVG"'}, 'CALC:FEED':{'"POW:AVER"'}, 'BUFF:STAT':{'OFF'}}
            if key in numeric and sep:
                token = value[:-3] if value.endswith('DBM') else value
                scalar(token)
                self.state[key] = token
            elif key in enums and value in enums[key]:
                self.state[key] = {'ON':'1','OFF':'0'}.get(value,value)
                if key == 'OUTP': self.output = value == 'ON'
            else: raise InstrumentError('Unsupported equipment command: ' + command)

    def _read(self):
        if self.reply is None: raise InstrumentError('No equipment response pending')
        return self.reply

    def _close(self): pass
