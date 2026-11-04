"""S11 acquisition for ZNLE6 / RVNA R140; calibration remains an explicit site input."""
from dataclasses import dataclass
from datetime import datetime, timezone
from .core import Scpi, UnsupportedInstrument, InstrumentError, number, integer, fmt, scalar, switch, close_enough, managed_run
from .analyzers import RS


@dataclass(frozen=True)
class NetworkTrace:
    frequencies_hz: tuple
    s11: tuple
    correction_enabled: bool
    utc: str
    identity: object
    raw: str


class VectorNetworkAnalyzer(Scpi):
    def __init__(self, transport, *, model, max_frequency_hz, max_power_dbm):
        if model not in ('ZNLE6', 'Planar R140'):
            raise UnsupportedInstrument(f'No reviewed VNA dialect for {model}')
        super().__init__(transport, model=model, manufacturers=RS if model=='ZNLE6' else ('Copper Mountain Technologies',))
        self.source_id = 'rs-znle' if model=='ZNLE6' else 'cmt-rvna'
        self.max_hz = number(max_frequency_hz, 'installed maximum frequency', 1, 1e12)
        self.max_dbm = number(max_power_dbm, 'site maximum power', -100, 30)

    def acquire_s11(self, *, start_hz, stop_hz, points, if_bandwidth_hz, power_dbm,
                    require_correction=True):
        number(start_hz, 'start_hz', 1, self.max_hz)
        number(stop_hz, 'stop_hz', start_hz, self.max_hz)
        if start_hz == stop_hz:
            raise ValueError('Frequency sweep must have nonzero span')
        integer(points, 'points', 2, 100001)
        number(if_bandwidth_hz, 'if_bandwidth_hz', 1, 1e6)
        number(power_dbm, 'power_dbm', -100, self.max_dbm)
        if type(require_correction) is not bool:
            raise ValueError('require_correction must be boolean')
        self.ready()
        cmt = self.expected_model == 'Planar R140'
        with self.io.transaction():
            with managed_run(lambda: None, self.stop):
                self.stop()
                trace_commands = ['CALC1:PAR1:DEF S11', 'CALC1:PAR1:SEL'] if cmt else [
                    "CALC1:PAR:SDEF 'DGM_S11','S11'", "CALC1:PAR:SEL 'DGM_S11'"]
                self.apply(trace_commands + [
                    'FORM:DATA ASC', 'SENS1:SWE:TYPE LIN',
                    f'SENS1:FREQ:STAR {fmt(start_hz)}', f'SENS1:FREQ:STOP {fmt(stop_hz)}',
                    f'SENS1:SWE:POIN {points}', f'SENS1:BAND {fmt(if_bandwidth_hz)}',
                    f'SOUR1:POW {fmt(power_dbm)}',
                    'TRIG:SOUR BUS' if cmt else 'TRIG1:SEQ:SOUR IMM',
                    'INIT1:CONT ON' if cmt else 'INIT1:CONT OFF'])
                for query, value in [('SENS1:FREQ:STAR?', start_hz), ('SENS1:FREQ:STOP?', stop_hz),
                                     ('SENS1:SWE:POIN?', points), ('SOUR1:POW?', power_dbm)]:
                    close_enough(scalar(self.io.query(query)), value, abs_tol=0.001)
                correction = switch(self.io.query('SENS1:CORR:STAT?'))
                if require_correction and not correction:
                    raise InstrumentError('Load and verify a suitable calibration before acquisition')
                self.apply(['OUTP ON'])
                self.io.write('TRIG:SING' if cmt else 'INIT1:IMM')
                self.opc()
                raw = self.io.query('CALC1:DATA:SDAT?' if cmt else 'CALC1:DATA? SDAT')
                values = [scalar(v) for v in raw.split(',')]
                frequencies = tuple(scalar(v) for v in self.io.query('SENS1:FREQ:DATA?' if cmt else 'CALC1:DATA:STIM?').split(','))
                self.errors()
                if len(values) != 2*points or len(frequencies) != points:
                    raise InstrumentError('VNA frequency/data length mismatch')
                if any(a >= b for a, b in zip(frequencies, frequencies[1:])):
                    raise InstrumentError('VNA frequency axis is not strictly increasing')
                close_enough(frequencies[0], start_hz, abs_tol=0.1)
                close_enough(frequencies[-1], stop_hz, abs_tol=0.1)
                return NetworkTrace(frequencies, tuple(complex(values[i], values[i+1]) for i in range(0,len(values),2)),
                                    correction, datetime.now(timezone.utc).isoformat(), self.identity, raw)

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('OUTP OFF')
            self.io.write('INIT1:CONT OFF')
            self.opc()
            if switch(self.io.query('OUTP?')):
                raise InstrumentError('VNA RF OFF not confirmed')
            self.errors()
