"""Synthetic steady envelope, NOT QP/CISPR weighting physics. Runs the native driver."""
from dgm_lab.core import InstrumentError
from dgm_lab.transport import Transport
from .receiver_measurement import CONVERSION


class ReceiverPeer(Transport):
    NUMBERS = {'FREQ:CENT', 'BAND', 'INP:ATT', 'SWE:TIME'}
    ENUMS = {'INST:SEL': {'REC'}, 'INIT1:CONT': {'OFF'}, 'FORM': {'ASC'},
             'CALC:UNIT:POW': {'DBUV'}, 'DISP:BARG:TCO': {'OFF'}, 'DISP:BARG:PHOL': {'OFF'},
             'DET:REC': {'POS', 'QPE', 'AVER', 'CAV'}, 'BAND:TYPE': {'CISPR'},
             'BAND:AUTO': {'OFF'}, 'INP:ATT:AUTO': {'OFF'}}

    def __init__(self, world, model, log=None):
        super().__init__('simulation://EmiReceiver', timeout=120, log=log)
        self.world, self.model = world, model
        self.settings, self.reply, self.result = {}, None, None
        self.options = 'K54' if model.startswith('FSW') else 'EMC' if model.startswith('N') else ''
        self.firmware = 'A.02.00' if model.startswith('N') and model.endswith('A') else 'SIMULATED'
        self.numbers = self.NUMBERS | {'FREQ:STAR', 'FREQ:STOP', 'FREQ:SPAN', 'BAND:RES', 'BAND:VID', 'POW:ATT',
                                      'SWE:POIN', 'CALC:MARK1:TRAC', 'CALC:MARK1:X',
                                      'CALC:MARK:FUNC:FME:DWEL', 'CALC:MAM:DET1:DWEL'}
        self.enums = {**self.ENUMS, 'INST:SEL': {'REC', 'SAN', 'SA'}, 'BAND:TYPE': {'CISPR', 'CISP', 'PULS'},
                      'INIT:CONT': {'OFF'}, 'FORM:DATA': {'ASC'}, 'UNIT:POW': {'DBUV'},
                      'CALC:MARK:FUNC:FME:STAT': {'ON', 'OFF'}, 'CALC:MARK:FUNC:FME:PEAK:AUTO': {'OFF'},
                      'BAND:RES:AUTO': {'OFF'}, 'BAND:VID:AUTO': {'OFF'}, 'SWE:TIME:AUTO': {'ON'}, 'TRIG:SOUR': {'IMM'},
                      'DISP:WIND:TRAC1:MODE': {'WRIT'}, 'DET1': {'POS'}, 'CALC:MARK1': {'ON'},
                      'CALC:MARK1:FUNC:FME:DET': {'POS', 'QPE', 'AVER', 'CAV'}, 'SWE:TYPE:AUTO': {'OFF'},
                      'SWE:TYPE': {'SWE'}, 'EMC:STAN': {'CISP'}, 'POW:ATT:AUTO': {'OFF'},
                      'AVER:TYPE:AUTO': {'OFF'}, 'AVER:TYPE': {'SCAL'}, 'CALC:MARK1:MODE': {'POS'},
                      'CALC:MAM:COUP': {'OFF'}, 'CALC:MAM:DET2': {'OFF'}, 'CALC:MAM:DET3': {'OFF'},
                      'CALC:MAM:DET1': {'POS', 'QPE', 'AVER', 'EAV'}}

    def measure(self):
        if self.model.startswith('FSW'):
            required = {'CALC:MARK1:X', 'CALC:MARK1:FUNC:FME:DET', 'CALC:MARK:FUNC:FME:DWEL',
                        'CALC:MARK:FUNC:FME:STAT', 'CALC:MARK:FUNC:FME:PEAK:AUTO', 'BAND:RES'}
            f = self.settings.get('CALC:MARK1:X')
        elif self.model.startswith('N'):
            required = {'FREQ:CENT', 'FREQ:SPAN', 'CALC:MAM:DET1', 'CALC:MAM:DET2', 'CALC:MAM:DET3',
                        'CALC:MAM:DET1:DWEL', 'CALC:MAM:COUP', 'EMC:STAN', 'AVER:TYPE', 'BAND:RES'}
            f = self.settings.get('FREQ:CENT')
        else:
            required = self.NUMBERS | set(self.ENUMS)
            if self.model.startswith('ESU'): required = required - {'DISP:BARG:TCO'}
            f = self.settings.get('FREQ:CENT')
        if not required <= set(self.settings): raise InstrumentError('Incomplete receiver setup')
        rbw = self.settings.get('BAND:RES', self.settings.get('BAND'))
        self.result = format(self.world.power(f, rbw)+CONVERSION, '.12g')
        self.world.observation('EmiReceiver', self.settings, {'dbuv': float(self.result), 'detector_physics_simulated': False})

    def _write(self, command):
        with self.world.lock:
            fault = self.world.fault('EmiReceiver', command)
            self.reply = None
            if fault == 'reject': raise InstrumentError('Injected receiver rejection')
            if fault == 'malformed':
                self.reply = 'malformed'
                return
            if command == '*IDN?':
                self.reply = ('Keysight Technologies,' if self.model.startswith('N') else 'Rohde&Schwarz,') + self.model + ',SIMULATION,' + self.firmware
            elif command == '*OPT?': self.reply = self.options
            elif command == 'SWE:TIME?' and self.model.startswith('FSW'): self.reply = '0.1'
            elif command == '*OPC?': self.reply = '1'
            elif command == 'SYST:ERR?': self.reply = '0,"No error"'
            elif command == 'ABOR': self.result = None
            elif command in {'INIT1:IMM', 'INIT:IMM'}: self.measure()
            elif command in {'CALC:MARK:AOFF', 'CONF:SAN'}: pass
            elif command == 'CALC:MARK1:FUNC:MAM?':
                self.measure()
                self.reply = self.result + ',-999,-999,' + str(self.settings['FREQ:CENT'])
            elif command == 'CALC:MARK1:FUNC:FME:RES?' and self.result is not None: self.reply = self.result
            elif command == 'TRAC? SINGLE' and self.result is not None: self.reply = self.result
            elif command.endswith('?') and command[:-1] in self.settings:
                value = self.settings[command[:-1]]
                self.reply = 'PULS' if command == 'BAND:TYPE?' else str(value)
            else:
                key, _, value = command.partition(' ')
                if key in self.numbers: self.settings[key] = float(value)
                elif key in self.enums and value in self.enums[key]: self.settings[key] = value
                else: raise InstrumentError('Unmodeled receiver command: ' + command)

    def _read(self):
        if self.reply is None: raise InstrumentError('Receiver read without query')
        result, self.reply = self.reply, None
        return result

    def _close(self): pass
