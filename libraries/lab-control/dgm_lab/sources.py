"""RF CW generators and DC supplies. Site limits are required, not inferred from reports."""
import time
from .core import Scpi, UnsupportedInstrument, InstrumentError, number, fmt, scalar, switch, close_enough, managed_run
from .analyzers import KEYSIGHT, RS


class SignalGenerator(Scpi):
    MODELS = {'N5181A': 'keysight-mxg-a', 'N5182B': 'keysight-mxg-b', 'SMB100A': 'rs-smb100a',
              'SMB100B': 'rs-smb100b', 'SMW200A': 'rs-smw200a'}

    def __init__(self, transport, *, model, max_frequency_hz, max_power_dbm):
        if model not in self.MODELS:
            raise UnsupportedInstrument(f'No reviewed RF source dialect for {model}')
        super().__init__(transport, model=model, manufacturers=KEYSIGHT if model.startswith('N') else RS)
        self.source_id = self.MODELS[model]
        self.max_hz = number(max_frequency_hz, 'installed maximum frequency', 1, 1e12)
        self.max_dbm = number(max_power_dbm, 'site maximum power', -140, 40)
        self.configured = False

    def configure_cw(self, *, frequency_hz, power_dbm):
        number(frequency_hz, 'frequency_hz', 1, self.max_hz)
        number(power_dbm, 'power_dbm', -140, self.max_dbm)
        self.ready()
        self.configured = False
        with self.io.transaction():
            self.stop()
            # RF path 1 only. Disables modulation, selects fixed frequency AND power.
            modulation_off = 'OUTP:MOD OFF' if self.expected_model.startswith('N') else 'SOUR:MOD:ALL:STAT OFF'
            self.apply([modulation_off, 'SOUR:FREQ:MODE CW', 'SOUR:POW:MODE FIX',
                        f'SOUR:FREQ:CW {fmt(frequency_hz)}', f'SOUR:POW {fmt(power_dbm)}DBM'])
            close_enough(scalar(self.io.query('SOUR:FREQ:CW?')), frequency_hz, abs_tol=0.1)
            close_enough(scalar(self.io.query('SOUR:POW?')), power_dbm, abs_tol=0.01)
            self.errors()
            self.configured = True

    def start(self):
        self.ready()
        if not self.configured:
            raise InstrumentError('configure_cw() and readbacks must succeed before RF ON')
        with self.io.transaction():
            self.apply(['OUTP ON'])
            if not switch(self.io.query('OUTP?')):
                raise InstrumentError('RF ON readback failed')

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('OUTP OFF')
            self.opc()
            if switch(self.io.query('OUTP?')):
                raise InstrumentError('RF OFF readback failed; output state UNKNOWN')
            self.errors()

    def emitting(self):
        return managed_run(self.start, self.stop)


class PowerSupply(Scpi):
    MODELS = {'PWR2001ML': 'kikusui-pwr', 'E3640A': 'keysight-e3640'}

    def __init__(self, transport, *, model, max_voltage, max_current):
        if model not in self.MODELS:
            raise UnsupportedInstrument(f'No reviewed supply dialect for {model}')
        super().__init__(transport, model=model, manufacturers=('KIKUSUI', 'KIKUSUI ELECTRONICS CORP.') if model=='PWR2001ML' else KEYSIGHT)
        self.source_id = self.MODELS[model]
        self.max_v = number(max_voltage, 'site voltage limit', 0.001, 1000)
        self.max_a = number(max_current, 'site current limit', 0.001, 1000)
        self.configured = False

    def configure(self, *, voltage, current_limit, range_name=None):
        number(voltage, 'voltage', 0, self.max_v)
        number(current_limit, 'current_limit', 0, self.max_a)
        if self.expected_model == 'E3640A':
            if range_name not in ('P8V', 'P20V'):
                raise ValueError('E3640A requires explicit P8V or P20V range')
            vmax, imax = (8, 3) if range_name=='P8V' else (20, 1.5)
            number(voltage, 'selected range voltage', 0, vmax)
            number(current_limit, 'selected range current', 0, imax)
        elif range_name is not None:
            raise ValueError('range_name only applies to E3640A')
        self.ready()
        self.configured = False
        with self.io.transaction():
            self.stop()
            commands = [f'VOLT:RANG {range_name}'] if range_name else []
            self.apply(commands + [f'CURR {fmt(current_limit)}', f'VOLT {fmt(voltage)}'])
            close_enough(scalar(self.io.query('VOLT?')), voltage, abs_tol=0.005)
            close_enough(scalar(self.io.query('CURR?')), current_limit, abs_tol=0.001)
            self.errors()
            self.configured = True

    def start(self):
        self.ready()
        if not self.configured:
            raise InstrumentError('configure() and readbacks must succeed before output ON')
        with self.io.transaction():
            self.apply(['OUTP ON'])
            self._wait_output(True)

    def _wait_output(self, expected):
        # PWR-01 status sampling can lag by 50 ms. Bound the wait; do not resend OUTP.
        deadline = time.monotonic() + (0.5 if self.expected_model == 'PWR2001ML' else 0)
        while True:
            if switch(self.io.query('OUTP?')) == expected:
                return
            if time.monotonic() >= deadline:
                raise InstrumentError(f'Output {"ON" if expected else "OFF"} readback failed; output state UNKNOWN')
            time.sleep(0.05)

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('OUTP OFF')
            self.opc()
            self._wait_output(False)
            self.errors()

    def read_voltage(self):
        return self.measure('MEAS:VOLT?', 'V')

    def read_current(self):
        return self.measure('MEAS:CURR?', 'A')

    def powering(self):
        return managed_run(self.start, self.stop)
