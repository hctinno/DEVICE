"""CMU200 RF_NSig CW generator ONLY. Not UE/cellular/Bluetooth signalling.

1100.4903.12 E-3, PDF 253,316,348-352,359. Logical address prefix on every
transaction; never remaps secondary addresses. Remote entry can disturb calls.
"""
from .core import (Scpi, InstrumentError, UnsupportedInstrument, integer, number,
                   scalar, switch, fmt, close_enough, managed_run)


class _Addressed:
    def __init__(self, io, address):
        self.io, self.address = io, address

    def query(self, command):
        return self.io.query(f'{self.address};{command}')

    def write(self, command):
        return self.io.write(f'{self.address};{command}')

    def transaction(self):
        return self.io.transaction()


class Cmu200Cw:
    source_id = 'rs-cmu-base'

    def __init__(self, transport, *, secondary_address=0, output_port=0,
                 max_frequency_hz=0, max_power_dbm=None, expected_firmware='',
                 site_profile_confirmed=False):
        if site_profile_confirmed is not True:
            raise UnsupportedInstrument('Confirm CMU200 RF_NSig mapping, firmware, other generators OFF and remote-entry effects')
        self.address = integer(secondary_address, 'secondary_address', 1, 29)
        self.port = integer(output_port, 'output_port', 1, 3)
        self.max_frequency = number(max_frequency_hz, 'max_frequency_hz', 100000, 2.7e9)
        self.minimum_power, maximum = {1: (-137, -27), 2: (-137, -10), 3: (-90, 13)}[self.port]
        self.max_power = number(max_power_dbm, 'max_power_dbm', self.minimum_power, maximum)
        if not isinstance(expected_firmware, str) or not expected_firmware.strip():
            raise ValueError('expected_firmware required; verify logical addressing support (base >=1.20)')
        self.expected_firmware = expected_firmware
        self.io, self.identity, self.plan = transport, None, None

    def identify(self):
        self.identity = None
        self.plan = None
        with self.io.transaction():
            base = Scpi(_Addressed(self.io, 0), model='CMU200', manufacturers=('Rohde&Schwarz',))
            identity = base.identify()
            if identity.firmware != self.expected_firmware:
                raise UnsupportedInstrument('CMU firmware differs from commissioned profile')
            group = self.io.query(f'0;SYST:REM:ADDR:SEC? {self.address}').strip().strip('"')
            if group != 'RF_NSig':
                raise UnsupportedInstrument(f'Secondary {self.address} maps to {group!r}, not RF_NSig')
            self.identity = identity
            return identity

    def _ready(self):
        if self.identity is None:
            raise UnsupportedInstrument('Identify CMU200 and verify RF_NSig mapping first')

    def _query(self, command):
        return self.io.query(f'{self.address};{command}')

    def _write(self, command):
        self.io.write(f'{self.address};{command}')

    def _errors(self):
        Scpi(_Addressed(self.io, 0), model='CMU200', manufacturers=('Rohde&Schwarz',)).errors()

    def status(self):
        self._ready()
        value = self._query('FETC:RFG:TX:STAT?').strip()
        if value not in ('OFF', 'RUN', 'ERR'):
            raise InstrumentError(f'Unknown CMU generator status {value!r}')
        return value

    def _verify_settings(self, frequency_hz, power_dbm):
        if self._query('OUTP:TX?').strip() != f'RF{self.port}':
            raise InstrumentError('CMU output route mismatch')
        close_enough(scalar(self._query(f'SOUR:CORR:LOSS:OUTP{self.port}:TX?')), 0)
        close_enough(scalar(self._query('SOUR:RFG:TX:FREQ?')), frequency_hz, abs_tol=0.05)
        close_enough(scalar(self._query('SOUR:RFG:TX:LEV?')), power_dbm, abs_tol=0.05)
        if self._query('SOUR:RFG:MOD?').strip() != 'OFF':
            raise InstrumentError('CMU modulation not OFF')
        for suffix in ('FHOP:STAT?', 'PULS:STAT?'):
            if switch(self._query('SOUR:RFG:' + suffix)):
                raise InstrumentError('CMU hopping/ramping not OFF')

    def configure(self, *, frequency_hz, power_dbm):
        """CW 100 kHz..site max <=2.7 GHz, port-specific dBm, zero internal loss correction."""
        self.plan = None
        number(frequency_hz, 'frequency_hz', 100000, self.max_frequency)
        number(power_dbm, 'power_dbm', self.minimum_power, self.max_power)
        close_enough(frequency_hz * 10, round(frequency_hz * 10), abs_tol=1e-5)
        close_enough(power_dbm * 10, round(power_dbm * 10), abs_tol=1e-7)
        self._ready()
        with self.io.transaction():
            self._errors()
            if self.status() != 'OFF':
                raise InstrumentError('CMU TX generator must be OFF before configure')
            for command in (f'OUTP:TX RF{self.port}', f'SOUR:CORR:LOSS:OUTP{self.port}:TX 0',
                            'SOUR:RFG:MOD OFF', 'SOUR:RFG:FHOP:STAT OFF', 'SOUR:RFG:PULS:STAT OFF',
                            f'SOUR:RFG:TX:FREQ {fmt(frequency_hz)}', f'SOUR:RFG:TX:LEV {fmt(power_dbm)}'):
                self._write(command)
            if self._query('*OPC?') != '1':
                raise InstrumentError('CMU configuration completion failed')
            self._verify_settings(frequency_hz, power_dbm)
            self._errors()
            self.plan = (frequency_hz, power_dbm)

    def start(self):
        self._ready()
        if self.plan is None:
            raise InstrumentError('configure() must succeed before CMU TX start')
        with self.io.transaction():
            self._errors()
            if self.status() != 'OFF':
                raise InstrumentError('CMU TX already active or error')
            self._verify_settings(*self.plan)
            self._write('INIT:RFG:TX')
            if self._query('*OPC?') != '1' or self.status() != 'RUN':
                raise InstrumentError('CMU TX RUN not confirmed')
            self._errors()

    def stop(self):
        self._ready()
        self.plan = None
        with self.io.transaction():
            self._write('ABOR:RFG:TX')
            if self._query('*OPC?') != '1' or self.status() != 'OFF':
                raise InstrumentError('CMU TX OFF not confirmed')
            self._errors()

    def emitting(self):
        return managed_run(self.start, self.stop)
