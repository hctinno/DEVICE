"""HP 437B native programming language (NOT SYST:ERR?/READ? SCPI).

Manual pages were visually reviewed: PDF 61,63,64,70-72,95,133-135.
"""
from datetime import datetime, timezone
from .core import Identity, Measurement, InstrumentError, UnsupportedInstrument, integer, number, scalar, fmt


class Hp437B:
    source_id='hp-437b'

    def __init__(self,transport):
        self.io=transport
        self.identity=None
        self.configured=False

    def identify(self):
        self.identity=None;self.configured=False
        raw=self.io.query('*IDN?')
        parts=[s.strip() for s in raw.split(',')]
        if len(parts)!=3 or parts[0].upper()!='HEWLETT-PACKARD' or parts[1].upper()!='437B':
            raise UnsupportedInstrument(f'Expected native HP 437B three-field identity: {raw!r}')
        self.identity=Identity(parts[0],parts[1],'',parts[2],raw)
        return self.identity

    def _ready(self):
        if self.identity is None:
            raise UnsupportedInstrument('Identify HP 437B first')

    def _error(self):
        raw=self.io.query('ERR?')
        try: code=int(raw)
        except ValueError as exc: raise InstrumentError(f'Invalid HP error response: {raw!r}') from exc
        if code: raise InstrumentError(f'HP 437B error {code}')

    def configure(self,*,frequency_hz,sensor_table):
        number(frequency_hz,'frequency_hz',100000,999.9999e9)
        integer(sensor_table,'verified sensor calibration table',0,9)
        if frequency_hz%100000:
            raise ValueError('HP 437B correction frequency resolution is 100 kHz')
        self._ready();self.configured=False
        with self.io.transaction():
            self._error()
            for cmd in ('TR0',f'SE{sensor_table}EN',f'FR{fmt(frequency_hz)}HZ','LG','RL0','OF0','DC0'):
                self.io.write(cmd)
            self._error()
            self.configured=True

    def read_power(self):
        self._ready()
        if not self.configured: raise InstrumentError('configure() must succeed first')
        with self.io.transaction():
            # TR2 both starts a settled reading and produces a result when addressed to talk.
            raw=self.io.query('TR2')
            value=scalar(raw)
            status=self.io.query('SM')
            if len(status)!=26 or not status[:4].isdigit():
                raise InstrumentError(f'Invalid 26-character HP status: {status!r}')
            if status[:4]!='0000': raise InstrumentError(f'HP measurement/entry error: {status[:4]}')
            if status[25]!='1' or status[17]!='0':
                raise InstrumentError('HP reading is not absolute dBm')
            self._error()
            return Measurement(value,'dBm',datetime.now(timezone.utc).isoformat(),self.identity,raw)

    def stop(self):
        self._ready()
        with self.io.transaction():
            self.io.write('TR0')
            self._error()
        # Status message is only refreshed by a measurement; do not claim fresh stop readback.
