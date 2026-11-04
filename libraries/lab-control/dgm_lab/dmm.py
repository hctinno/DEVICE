"""Truevolt DC/AC voltage and 2-wire resistance; conservative bench wrapper.

Official guide 9018-03876 pp.201-202,239-241,246,248,341-352,370,374-382.
CONF resets per-function math/null per p.239. No current, mains or scanning API.
"""
from .core import Scpi, UnsupportedInstrument, InstrumentError, Measurement, number, scalar, fmt, close_enough
from .analyzers import KEYSIGHT
from .model_scope import extra_models
from datetime import datetime, timezone


class DigitalMultimeter(Scpi):
    MODELS = extra_models('DigitalMultimeter')

    def __init__(self, transport, *, model, max_voltage):
        if model not in self.MODELS: raise UnsupportedInstrument('Unreviewed Truevolt model')
        super().__init__(transport, model=model, manufacturers=KEYSIGHT)
        self.source_id = self.MODELS[model]
        self.max_voltage = number(max_voltage, 'site voltage limit', .1, 10)
        self.configured = False

    def configure(self, *, function, range_value):
        ranges = {'DCV': (.1,1,10), 'ACV': (.1,1,10), 'RES2W': (100,1000,10000,100000,1000000)}
        if function not in ranges or type(range_value) not in (int,float) or range_value not in ranges[function]:
            raise ValueError('Explicit DCV/ACV/RES2W and reviewed fixed range required')
        if function != 'RES2W': number(range_value, 'voltage range', .1, self.max_voltage)
        self.ready()
        self.configured = False
        self.function, self.range_value = function, range_value
        self.mnemonic = {'DCV':'VOLT:DC', 'ACV':'VOLT:AC', 'RES2W':'RES'}[function]
        with self.io.transaction():
            self.stop()
            self.apply([f'CONF:{self.mnemonic} {fmt(range_value)}', 'TRIG:SOUR IMM', 'SAMP:COUN 1', 'TRIG:COUN 1'])
            self._verify()
            self.errors()
            self.configured = True

    def _verify(self):
        conf = self.io.query('CONF?').strip().strip('"')
        try:
            function, values = conf.split(None,1)
            value, resolution = map(scalar, values.split(','))
        except (ValueError, TypeError) as exc:
            raise InstrumentError('Malformed DMM configuration evidence') from exc
        wanted = {'DCV':'VOLT', 'ACV':'VOLT:AC', 'RES2W':'RES'}[self.function]
        if function != wanted or resolution <= 0: raise InstrumentError('DMM function/resolution mismatch')
        close_enough(value, self.range_value)
        for q in ('SAMP:COUN?', 'TRIG:COUN?'):
            close_enough(scalar(self.io.query(q)), 1)
        if self.io.query('TRIG:SOUR?').strip().upper() != 'IMM': raise InstrumentError('DMM trigger mismatch')
        return conf

    def read(self):
        if not self.configured: raise InstrumentError('configure must succeed before measurement')
        with self.io.transaction():
            self.errors()
            self._verify()
            raw = self.io.query('READ?')
            value = scalar(raw)
            self._verify()
            self.errors()
            return Measurement(value, 'Ohm' if self.function == 'RES2W' else 'V',
                               datetime.now(timezone.utc).isoformat(), self.identity, raw)

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('ABOR')
            self.opc()
            self.errors()
