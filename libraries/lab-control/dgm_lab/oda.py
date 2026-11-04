"""ODA EX family, serial-bound EX60-40 profile. Manufacturer PDF pp.73-85.

Three-field IDN is a FAMILY identity, not proof of the installed model.
No *OPC?, reset, factory commands, protection clearing or RS485 addressing.
"""
from .core import (Identity, InstrumentError, UnsupportedInstrument, Scpi,
                   number, scalar, switch, normalized, fmt, close_enough, managed_run)


class OdaEx:
    source_id = 'oda-ex'

    def __init__(self, transport, *, model='EX60-40', expected_serial='', expected_firmware='',
                 max_voltage=0, max_current=0, installed_model_confirmed=False):
        if model != 'EX60-40' or installed_model_confirmed is not True:
            raise UnsupportedInstrument('Confirm EX60-40 nameplate, firmware/protocol and serial binding')
        if not isinstance(expected_serial, str) or not expected_serial.strip() or not isinstance(expected_firmware, str) or not expected_firmware.strip():
            raise ValueError('expected_serial and expected_firmware must be commissioned values')
        self.max_voltage = number(max_voltage, 'site max_voltage', 0.01, 60)
        self.max_current = number(max_current, 'site max_current', 0.01, 40)
        self.expected_serial = expected_serial
        self.expected_firmware = expected_firmware
        self.io = transport
        self.identity = None
        self.plan = None

    def identify(self):
        self.identity = None
        self.plan = None
        with self.io.transaction():
            raw = self.io.query('*IDN?')
            parts = [p.strip() for p in raw.split(',')]
            if len(parts) != 3 or normalized(parts[0]) != 'ODATECHNOLOGIES' or parts[1] != 'EX-Series':
                raise UnsupportedInstrument(f'Expected three-field ODA EX identity: {raw!r}')
            serial = self.io.query('*SN?').strip()
            if serial != self.expected_serial or parts[2] != self.expected_firmware:
                raise UnsupportedInstrument('ODA serial/firmware differs from commissioned profile')
            self.identity = Identity(parts[0], parts[1], serial, parts[2], raw)
            return self.identity

    def ready(self):
        if self.identity is None:
            raise UnsupportedInstrument('Identify serial-bound ODA EX first')

    def errors(self):
        Scpi.errors(self, limit=11)  # ten-entry queue, no *CLS

    def _trips(self):
        if switch(self.io.query('VOLT:OVP:TRIP?')) or switch(self.io.query('CURR:OCP:TRIP?')):
            raise InstrumentError('ODA protection tripped; no automatic clearing')

    def _readback(self, voltage, current):
        close_enough(scalar(self.io.query('VOLT?')), voltage, abs_tol=0.005)
        close_enough(scalar(self.io.query('CURR?')), current, abs_tol=0.005)

    def configure(self, *, voltage, current):
        """Set V/A with output OFF; conservative 0.01 V/A grid, site limits <=60 V/40 A."""
        self.plan = None
        number(voltage, 'voltage', 0, self.max_voltage)
        number(current, 'current', 0, self.max_current)
        for value in (voltage, current):
            close_enough(value * 100, round(value * 100), abs_tol=1e-6)
        command = f'APPL {fmt(voltage)},{fmt(current)}'
        self.ready()
        with self.io.transaction():
            self.errors()
            if switch(self.io.query('OUTP?')):
                raise InstrumentError('ODA output must be OFF before configure')
            self._trips()
            for value, stem in ((voltage, 'VOLT'), (current, 'CURR')):
                lower = scalar(self.io.query(stem + (':UVL?' if stem == 'VOLT' else ':UCL?')))
                upper = scalar(self.io.query(stem + (':OVL?' if stem == 'VOLT' else ':OCL?')))
                if not lower <= value <= upper:
                    raise InstrumentError(f'{stem} request outside installed limits {lower}..{upper}')
            self.io.write(command)
            self._readback(voltage, current)
            self.errors()
            self.plan = (voltage, current)

    def start(self):
        self.ready()
        if self.plan is None:
            raise InstrumentError('configure() must succeed before output ON')
        with self.io.transaction():
            self.errors()
            self._trips()
            self._readback(*self.plan)
            if switch(self.io.query('OUTP?')):
                raise InstrumentError('ODA output already ON; ownership unclear')
            self.io.write('OUTP ON')
            if not switch(self.io.query('OUTP?')):
                raise InstrumentError('ODA output ON readback failed')
            self._trips()
            self.errors()

    def read_voltage(self):
        return Scpi.measure(self, 'MEAS:VOLT?', 'V')

    def read_current(self):
        return Scpi.measure(self, 'MEAS:CURR?', 'A')

    def stop(self):
        self.ready()
        self.plan = None
        with self.io.transaction():
            self.io.write('OUTP OFF')
            if switch(self.io.query('OUTP?')):
                raise InstrumentError('ODA output OFF not confirmed')
            self.errors()

    def powering(self):
        return managed_run(self.start, self.stop)
