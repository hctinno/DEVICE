"""Basic swept spectrum and EMI single-frequency measurements; not a certification recipe."""
from dataclasses import dataclass
from datetime import datetime, timezone
from .core import Scpi, UnsupportedInstrument, InstrumentError, number, integer, fmt, scalar, close_enough

KEYSIGHT = ('Keysight Technologies', 'Agilent Technologies', 'Hewlett-Packard')
RS = ('Rohde&Schwarz', 'Rohde-Schwarz', 'Rohde & Schwarz')


@dataclass(frozen=True)
class Sweep:
    start_hz: float
    stop_hz: float
    rbw_hz: float
    vbw_hz: float
    reference_dbm: float
    attenuation_db: float
    points: int = 1001
    detector: str = 'POS'
    sweep_seconds: float = 1.0

    def validate(self, max_hz):
        number(self.start_hz, 'start_hz', 0, max_hz)
        number(self.stop_hz, 'stop_hz', 0, max_hz)
        if self.start_hz >= self.stop_hz:
            raise ValueError('stop_hz must exceed start_hz (zero span is a separate measurement)')
        number(self.rbw_hz, 'rbw_hz', 1, 1e8)
        number(self.vbw_hz, 'vbw_hz', 1, 1e8)
        number(self.reference_dbm, 'reference_dbm', -150, 40)
        number(self.attenuation_db, 'attenuation_db', 0, 70)
        number(self.sweep_seconds, 'sweep_seconds', 0.000001, 10000)
        integer(self.points, 'points', 101, 100001)
        if self.detector not in ('POS', 'NEG', 'SAMP', 'RMS', 'AVER'):
            raise ValueError('detector must be POS, NEG, SAMP, RMS or AVER')


@dataclass(frozen=True)
class Trace:
    frequencies_hz: tuple
    values_dbm: tuple
    utc: str
    identity: object
    settings: Sweep
    raw: str


class SpectrumAnalyzer(Scpi):
    """X-Series A/B, FSW and legacy ESU/ESCI spectrum applications only."""
    MODELS = {
        'N9010A': ('keysight-xsa-a', 'keysight'), 'N9030A': ('keysight-xsa-a', 'keysight'),
        'N9020A': ('keysight-xsa-a', 'keysight'),
        'N9030B': ('keysight-xsa-b', 'keysight'), 'N9040B': ('keysight-xsa-b', 'keysight'),
        'E4440A': ('keysight-psa', 'psa'),
        'FSW50': ('rs-fsw', 'rs'), 'ESU8': ('rs-esu', 'legacy-rs'),
        'FSW67': ('rs-fsw', 'rs'), 'FSV40': ('rs-fsv', 'legacy-rs'),
        'ESU40': ('rs-esu', 'legacy-rs'), 'ESCI7': ('rs-esci', 'legacy-rs'),
    }

    def __init__(self, transport, *, model, max_frequency_hz):
        if model not in self.MODELS:
            raise UnsupportedInstrument(f'No reviewed spectrum dialect for {model}')
        self.source_id, self.dialect = self.MODELS[model]
        self.max_hz = number(max_frequency_hz, 'installed maximum frequency', 1, 1e12)
        super().__init__(transport, model=model, manufacturers=KEYSIGHT if self.dialect in ('keysight','psa') else RS)

    def acquire(self, config: Sweep):
        config.validate(self.max_hz)  # validate ALL values before even checking error queues
        self.ready()
        if config.sweep_seconds >= self.io.timeout:
            raise ValueError('Transport timeout must exceed sweep duration plus settling margin')
        key = self.dialect in ('keysight','psa')
        if self.dialect=='psa' and config.detector not in ('POS','NEG','SAMP'):
            raise ValueError('PSA wrapper currently supports POS/NEG/SAMP detectors only')
        commands = ['ABOR', 'INST:SEL SA' if key else 'INST:SEL SAN', 'INIT:CONT OFF',
                    'FORM:DATA ASC', 'CALC:UNIT:POW DBM' if self.dialect=='legacy-rs' else 'UNIT:POW DBM',
                    f'FREQ:STAR {fmt(config.start_hz)}', f'FREQ:STOP {fmt(config.stop_hz)}',
                    'BAND:RES:AUTO OFF', f'BAND:RES {fmt(config.rbw_hz)}',
                    'BAND:VID:AUTO OFF', f'BAND:VID {fmt(config.vbw_hz)}',
                    'POW:ATT:AUTO OFF' if key else 'INP:ATT:AUTO OFF',
                    f'{"POW:ATT" if key else "INP:ATT"} {fmt(config.attenuation_db)}',
                    f'DISP:WIND:TRAC:Y:RLEV {fmt(config.reference_dbm)}',
                    f'SWE:POIN {config.points}', 'SWE:TIME:AUTO OFF',
                    f'SWE:TIME {fmt(config.sweep_seconds)}',
                    f'DET {"AVER" if key and config.detector=="RMS" else config.detector}',
                    ('TRAC1:MODE WRIT' if self.dialect=='psa' else 'TRAC1:TYPE WRIT') if key else 'DISP:WIND:TRAC1:MODE WRIT',
                    'TRIG:SOUR IMM']
        if self.dialect=='keysight':
            # Select the swept-spectrum measurement, not a restored ACP/OBW measurement.
            commands.insert(2, 'CONF:SAN')
            commands += ['TRAC1:UPD ON', 'TRAC1:DISP ON']
            if config.detector in ('AVER','RMS'):
                commands += ['AVER:TYPE RMS']
        if self.dialect=='psa':
            commands += ['AVER OFF']
        else:
            commands += ['DISP:WIND:TRAC:X:SPAC LIN']
        with self.io.transaction():
            self.apply(commands)
            for query, requested, tol in [('FREQ:STAR?', config.start_hz, 0.1),
                                           ('FREQ:STOP?', config.stop_hz, 0.1),
                                           ('BAND:RES?', config.rbw_hz, 0.1),
                                           ('BAND:VID?', config.vbw_hz, 0.1),
                                           ('SWE:POIN?', config.points, 0),
                                           ('SWE:TIME?', config.sweep_seconds, 1e-6)]:
                close_enough(scalar(self.io.query(query)), requested, abs_tol=tol)
            close_enough(scalar(self.io.query('POW:ATT?' if key else 'INP:ATT?')), config.attenuation_db, abs_tol=0.01)
            close_enough(scalar(self.io.query('DISP:WIND:TRAC:Y:RLEV?')), config.reference_dbm, abs_tol=0.01)
            units_query = 'CALC:UNIT:POW?' if self.dialect=='legacy-rs' else 'UNIT:POW?'
            if self.io.query(units_query).upper() != 'DBM':
                raise InstrumentError('Analyzer amplitude units are not dBm')
            self.io.write('INIT:IMM')
            self.opc()
            raw = self.io.query('TRAC:DATA? TRACE1')
            values = tuple(scalar(v) for v in raw.split(','))
            self.errors()
            if len(values) != config.points:
                raise InstrumentError(f'Trace count {len(values)} != requested {config.points}')
            step = (config.stop_hz-config.start_hz)/(config.points-1)
            return Trace(tuple(config.start_hz+i*step for i in range(config.points)), values,
                         datetime.now(timezone.utc).isoformat(), self.identity, config, raw)

    def stop(self):
        self.ready()
        # ABOR must be issued even if an old error is pending.
        with self.io.transaction():
            self.io.write('ABOR')
            self.io.write('INIT:CONT OFF')
            self.opc()
            self.errors()


class EmiReceiver(Scpi):
    """ESW/ESR receiver bargraph; single detector avoids model-specific result order.

    Takes individual conducted/radiated amplitude readings. Antenna factor, cable loss,
    LISN, height/azimuth search and regulatory verdict are separate site responsibilities.
    """
    MODELS = {'ESW8': 'rs-esw', 'ESW44': 'rs-esw', 'ESR3': 'rs-esr', 'ESR7': 'rs-esr', 'EPL1000': 'rs-epl'}

    def __init__(self, transport, *, model, max_frequency_hz):
        if model not in self.MODELS:
            raise UnsupportedInstrument(f'No reviewed receiver dialect for {model}')
        super().__init__(transport, model=model, manufacturers=RS)
        self.source_id = self.MODELS[model]
        self.max_hz = number(max_frequency_hz, 'installed maximum frequency', 1, 1e12)

    def read_level(self, *, frequency_hz, rbw_hz, detector, dwell_seconds, attenuation_db):
        number(frequency_hz, 'frequency_hz', 1, self.max_hz)
        number(rbw_hz, 'rbw_hz', 1, 1e7)
        number(dwell_seconds, 'dwell_seconds', 0.001, 100)
        number(attenuation_db, 'attenuation_db', 0, 70)
        if detector not in ('POS', 'NEG', 'QPE', 'AVER', 'RMS', 'CAV', 'CRMS'):
            raise ValueError('Unsupported bargraph detector')
        if dwell_seconds >= self.io.timeout:
            raise ValueError('timeout must exceed dwell duration')
        with self.io.transaction():
            self.apply(['ABOR', 'INST:SEL REC', 'INIT1:CONT OFF', 'FORM ASC',
                        'CALC:UNIT:POW DBUV', f'FREQ:CENT {fmt(frequency_hz)}',
                        'BAND:AUTO OFF', f'BAND {fmt(rbw_hz)}',
                        'INP:ATT:AUTO OFF', f'INP:ATT {fmt(attenuation_db)}',
                        f'DET:REC {detector}', f'SWE:TIME {fmt(dwell_seconds)}'])
            close_enough(scalar(self.io.query('FREQ:CENT?')), frequency_hz, abs_tol=0.1)
            close_enough(scalar(self.io.query('BAND?')), rbw_hz, abs_tol=0.1)
            self.io.write('INIT1:IMM')
            self.opc()
            return self.measure('TRAC? SINGLE', 'dBuV')

    def read_verified_level(self, *, frequency_hz, rbw_hz, detector, dwell_seconds, attenuation_db):
        """Single bargraph, explicit CISPR filter and before/after configuration proof.

        ESW manual ed.18 pp.473-485,557-562; ESR ed.13 pp.607-615,637-640.
        External corrections must be disabled and RF input/path commissioned on site.
        Call within managed_run/DeviceSession.active so abort is attempted on any failure.
        """
        from .detectors import DETECTORS, ReceiverLevel, validate_receiver, verify_readbacks, READBACK_QUERIES
        settings = dict(frequency_hz=frequency_hz, rbw_hz=rbw_hz, detector=detector,
                        dwell_seconds=dwell_seconds, attenuation_db=attenuation_db, filter_type='CISPR')
        validate_receiver(self.expected_model, self.max_hz, **{k: v for k, v in settings.items() if k != 'filter_type'})
        if dwell_seconds >= self.io.timeout: raise ValueError('timeout must exceed dwell duration plus margin')
        self.ready()
        with self.io.transaction():
            self.apply(['ABOR', 'INST:SEL REC', 'INIT1:CONT OFF', 'FORM ASC',
                        'CALC:UNIT:POW DBUV', 'DISP:BARG:TCO OFF', 'DISP:BARG:PHOL OFF',
                        f'FREQ:CENT {fmt(frequency_hz)}', f'DET:REC {DETECTORS[detector]}',
                        'BAND:TYPE CISPR', 'BAND:AUTO OFF', f'BAND {fmt(rbw_hz)}',
                        'INP:ATT:AUTO OFF', f'INP:ATT {fmt(attenuation_db)}', f'SWE:TIME {fmt(dwell_seconds)}'])
            before = {q: self.io.query(q) for q in READBACK_QUERIES}
            verify_readbacks(before, settings)
            self.errors()
            self.io.write('INIT1:IMM')
            self.opc()
            result = self.measure('TRAC? SINGLE', 'dBuV')  # scalar rejects multiple bargraphs and overrange
            after = {q: self.io.query(q) for q in READBACK_QUERIES}
            verify_readbacks(after, settings)
            self.errors()
            return ReceiverLevel(result.value, result.unit, result.utc, result.identity, result.raw,
                                 settings, dict(before=before, after=after))

    def stop(self):
        self.ready()
        with self.io.transaction():
            self.io.write('ABOR')
            self.io.write('INIT1:CONT OFF')
            self.opc()
            self.errors()
