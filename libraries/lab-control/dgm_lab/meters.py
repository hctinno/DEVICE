"""Power-meter measurements are scoped to specified window/channel and units."""
from .core import Scpi, UnsupportedInstrument, InstrumentError, number, integer, fmt, scalar, close_enough
from .analyzers import KEYSIGHT, RS
from .model_scope import extra_models, frequency_scope


class PSeriesPowerMeter(Scpi):
    source_id = 'keysight-power'

    def __init__(self, transport, *, model):
        if model not in ('N1911A', 'N1912A'):
            raise UnsupportedInstrument(f'P-Series driver does not support {model}')
        super().__init__(transport, model=model, manufacturers=KEYSIGHT)
        self.channels = 1 if model=='N1911A' else 2
        self.configured_channel = None

    def configure_average(self, *, frequency_hz, channel=1):
        number(frequency_hz, 'sensor correction frequency', 1, 1e12)
        integer(channel, 'channel', 1, self.channels)
        self.configured_channel = None
        # Window 1 routes explicitly to the selected input. Never infer A/B from a window number.
        with self.io.transaction():
            self.apply([f'INIT{channel}:CONT OFF',
                        f'CONF1:POW:AC DEF,DEF,(@{channel})',
                        f'SENS{channel}:FREQ {fmt(frequency_hz)}',
                        'UNIT1:POW DBM', f'TRIG{channel}:SOUR IMM'])
            close_enough(scalar(self.io.query(f'SENS{channel}:FREQ?')), frequency_hz, abs_tol=0.1)
            if self.io.query('UNIT1:POW?').strip().upper() != 'DBM':
                raise InstrumentError('Power unit is not dBm')
            self.errors()
            self.configured_channel = channel

    def read_power(self):
        if self.configured_channel is None:
            raise InstrumentError('configure_average() must succeed first')
        return self.measure('READ1?', 'dBm')

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('ABOR')
            for channel in range(1, self.channels+1):
                self.io.write(f'INIT{channel}:CONT OFF')
            self.opc()
            self.errors()


class UsbPowerSensor(Scpi):
    MODELS = {'U2000A': 'keysight-u2000', 'NRP8S': 'rs-nrps', 'NRP18S': 'rs-nrps', 'NRP18A': 'rs-nrpa'}
    MODELS.update(extra_models('UsbPowerSensor'))

    def __init__(self, transport, *, model):
        if model not in self.MODELS:
            raise UnsupportedInstrument(f'No reviewed sensor dialect for {model}')
        super().__init__(transport, model=model, manufacturers=KEYSIGHT if model.startswith('U200') else RS)
        self.source_id = self.MODELS[model]
        self.configured = False

    def configure_average(self, *, frequency_hz):
        number(frequency_hz, 'sensor correction frequency', 1, 1e12)
        frequency_scope('UsbPowerSensor', self.expected_model, frequency_hz)
        self.configured = False
        if self.expected_model.startswith('U200'):
            commands = ['ABOR', 'CONF', 'SENS:DET:FUNC AVER', 'INIT:CONT OFF', 'UNIT:POW DBM']
        else:
            commands = ['ABOR', 'INIT:CONT OFF', 'SENS:FUNC "POW:AVG"', 'CALC:FEED "POW:AVER"',
                        'UNIT:POW W', 'FORM:DATA ASC', 'BUFF:STAT OFF', 'TRIG:COUN 1']
        with self.io.transaction():
            self.apply(commands + [f'SENS:FREQ {fmt(frequency_hz)}', 'TRIG:SOUR IMM'])
            close_enough(scalar(self.io.query('SENS:FREQ?')), frequency_hz, abs_tol=0.1)
            expected_unit = 'DBM' if self.expected_model.startswith('U200') else 'W'
            if self.io.query('UNIT:POW?').strip().upper() != expected_unit:
                raise InstrumentError('Power sensor unit readback mismatch')
            self.errors()
            self.configured = True

    def read_power(self):
        if not self.configured:
            raise InstrumentError('configure_average() must succeed first')
        with self.io.transaction():
            if self.expected_model.startswith('U200'):
                return self.measure('READ?', 'dBm')
            self.io.write('INIT')
            self.opc()
            return self.measure('FETC?', 'W')

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('ABOR')
            self.io.write('INIT:CONT OFF')
            self.opc()
            self.errors()
