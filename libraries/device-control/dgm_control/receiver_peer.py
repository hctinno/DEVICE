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

    def _write(self, command):
        with self.world.lock:
            fault = self.world.fault('EmiReceiver', command)
            self.reply = None
            if fault == 'reject': raise InstrumentError('Injected receiver rejection')
            if fault == 'malformed':
                self.reply = 'malformed'
                return
            if command == '*IDN?': self.reply = 'Rohde&Schwarz,' + self.model + ',SIMULATION,0'
            elif command == '*OPC?': self.reply = '1'
            elif command == 'SYST:ERR?': self.reply = '0,"No error"'
            elif command == 'ABOR': self.result = None
            elif command == 'INIT1:IMM':
                if not (self.NUMBERS | set(self.ENUMS)) <= set(self.settings): raise InstrumentError('Incomplete receiver setup')
                self.result = format(self.world.power(self.settings['FREQ:CENT'], self.settings['BAND'])+CONVERSION, '.12g')
                self.world.observation('EmiReceiver', self.settings, {'dbuv': float(self.result), 'detector_physics_simulated': False})
            elif command == 'TRAC? SINGLE' and self.result is not None: self.reply = self.result
            elif command.endswith('?') and command[:-1] in self.settings:
                value = self.settings[command[:-1]]
                self.reply = 'PULS' if command == 'BAND:TYPE?' else str(value)
            else:
                key, _, value = command.partition(' ')
                if key in self.NUMBERS: self.settings[key] = float(value)
                elif key in self.ENUMS and value in self.ENUMS[key]: self.settings[key] = value
                else: raise InstrumentError('Unmodeled receiver command: ' + command)

    def _read(self):
        if self.reply is None: raise InstrumentError('Receiver read without query')
        result, self.reply = self.reply, None
        return result

    def _close(self): pass
