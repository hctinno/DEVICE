"""Reviewed receiver subset. Limits here describe this implementation, not all instrument options."""
from dataclasses import dataclass
from .core import InstrumentError, UnsupportedInstrument, number, scalar, close_enough, switch

DETECTORS = {'POS': 'POS', 'QP': 'QPE', 'LINEAR_AVER': 'AVER', 'CISPR_AVER': 'CAV'}
RECEIVER_RANGES = {'ESW8': 8e9, 'ESW44': 44e9, 'ESR3': 3.6e9, 'ESR7': 7e9}
# Conservative reviewed workflow limits; not an instrument's installed RF option range.
EXTENDED_RANGES = {'EPL1000': 30e6, 'ESU8': 1e9, 'ESU40': 1e9,
                   'FSW50': 1e9, 'FSW67': 1e9, 'N9010A': 1e9, 'N9020A': 1e9,
                   'N9030A': 1e9, 'N9030B': 1e9, 'N9040B': 1e9}
RECEIVER_RANGES.update(EXTENDED_RANGES)
ALIASES = {'POS': 'POS', 'POSITIVE': 'POS', 'QPE': 'QP', 'QPEAK': 'QP',
           'AVER': 'LINEAR_AVER', 'AVERAGE': 'LINEAR_AVER', 'CAV': 'CISPR_AVER', 'CAVERAGE': 'CISPR_AVER'}


@dataclass(frozen=True)
class ReceiverLevel:
    value: float
    unit: str
    utc: str
    identity: object
    raw: str
    settings: dict
    readbacks: dict


def validate_receiver(model, max_hz, *, frequency_hz, rbw_hz, detector, dwell_seconds, attenuation_db):
    if model not in RECEIVER_RANGES:
        raise UnsupportedInstrument('Verified receiver-grid workflow not implemented for ' + str(model))
    if detector not in DETECTORS:
        raise ValueError('Use POS, QP, LINEAR_AVER or CISPR_AVER; ambiguous AVER/RMS is not accepted')
    number(frequency_hz, 'receiver frequency', 9000, min(max_hz, RECEIVER_RANGES[model]))
    if detector == 'QP' and frequency_hz > 1e9:
        raise ValueError('QP receiver-grid implementation is limited to <= 1 GHz')
    number(rbw_hz, 'CISPR RBW', 200, 1e6)
    if rbw_hz not in (200, 9000, 120000, 1000000): raise ValueError('Reviewed CISPR RBW required')
    number(dwell_seconds, 'dwell_seconds', 1 if detector == 'QP' else .02, 100)
    # Keep RF input protection unchanged. ESW disallows <=10 dB with protection enabled.
    number(attenuation_db, 'attenuation_db', 20, 70)
    if model in EXTENDED_RANGES:
        if model.startswith('FSW') and min(RECEIVER_RANGES[model], frequency_hz + rbw_hz) > max_hz:
            raise ValueError('FSW initial narrow sweep exceeds installed maximum frequency')
        # One second is a wrapper floor, not a guarantee for arbitrary pulse repetition rates.
        number(dwell_seconds, 'extended detector dwell', 1, 60)
        number(attenuation_db, 'extended detector attenuation', 20, 50)
        if attenuation_db % 10: raise ValueError('Extended detector attenuation uses 10 dB steps')
        expected_rbw = 200 if frequency_hz < 150e3 else 9000 if frequency_hz < 30e6 else 120000
        if rbw_hz != expected_rbw:
            raise ValueError('Extended workflow requires the CISPR band RBW: 200/9000/120000 Hz')


def verify_readbacks(values, settings, model=None):
    """Reject unknown tokens, multiple active detectors and any configuration drift."""
    if model in EXTENDED_RANGES:
        from .extended_detectors import verify_settings
        return verify_settings(model, values, settings)
    for key, query, tolerance in (('frequency_hz', 'FREQ:CENT?', .1), ('rbw_hz', 'BAND?', .1),
                                 ('dwell_seconds', 'SWE:TIME?', 1e-6), ('attenuation_db', 'INP:ATT?', .01)):
        close_enough(scalar(values[query]), settings[key], abs_tol=tolerance)
    if ALIASES.get(values['DET:REC?'].strip().upper()) != settings['detector']:
        raise InstrumentError('Receiver detector readback mismatch or multiple active detectors')
    if values['BAND:TYPE?'].strip().upper() != 'PULS':
        raise InstrumentError('Receiver requires CISPR 6 dB filter (PULS readback)')
    if values['CALC:UNIT:POW?'].strip().upper() != 'DBUV':
        raise InstrumentError('Receiver amplitude unit must be DBUV')
    for query in ('INIT1:CONT?', 'DISP:BARG:PHOL?', 'DISP:BARG:TCO?', 'BAND:AUTO?', 'INP:ATT:AUTO?'):
        if switch(values[query]): raise InstrumentError('Receiver state must be OFF: ' + query)


READBACK_QUERIES = ('FREQ:CENT?', 'BAND?', 'SWE:TIME?', 'INP:ATT?', 'DET:REC?', 'BAND:TYPE?',
                    'CALC:UNIT:POW?', 'INIT1:CONT?', 'DISP:BARG:PHOL?', 'DISP:BARG:TCO?',
                    'BAND:AUTO?', 'INP:ATT:AUTO?')
