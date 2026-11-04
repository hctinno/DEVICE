"""Official final-detector dialects. See SDK DETECTORS.md for page-level evidence.

The EmiReceiver device ID denotes the dedicated measurement role; FSW/X-Series
use spectrum-application final measurements, never the ordinary swept trace.
"""
import re
from datetime import datetime, timezone
from .core import InstrumentError, UnsupportedInstrument, fmt, scalar, close_enough, switch, number
from .detectors import DETECTORS, ReceiverLevel, RECEIVER_RANGES, validate_receiver


def family(model):
    if model.startswith('FSW'): return 'fsw-final-marker'
    if model.startswith('N'): return 'xseries-measure-at-marker'
    if model.startswith('ESU'): return 'esu-bargraph'
    if model == 'EPL1000': return 'epl-bargraph'
    raise UnsupportedInstrument('No extended detector dialect for ' + str(model))


def required_option(model):
    return 'K54' if model.startswith('FSW') else 'EMC' if model.startswith('N') else None


def verify_capability(model, capability, identity):
    option = required_option(model)
    if capability.get('dialect') != family(model) or capability.get('firmware_status') != 'site-validation-required':
        raise InstrumentError('Detector capability scope mismatch')
    if capability.get('required_option') != option or capability.get('firmware') != identity.firmware:
        raise InstrumentError('Detector capability identity mismatch')
    raw = capability.get('options_raw')
    if option:
        if not isinstance(raw, str): raise UnsupportedInstrument('Missing option response')
        tokens = {v.strip().strip('"').strip().upper() for v in raw.strip().strip('"').split(',')}
        if option not in tokens: raise UnsupportedInstrument('Required installed option not confirmed: ' + option)
    if model in {'N9000A', 'N9010A', 'N9020A', 'N9030A'}:
        match = re.fullmatch(r'A\.(\d+)\.(\d+)(?:\.\d+)?', identity.firmware.strip())
        if not match or int(match[1]) < 2:
            raise UnsupportedInstrument('X-Series A Measure-at-Marker requires documented A.02.00+ firmware format')


def contract(model, s):
    """Commands and exact expected queries; no arbitrary caller SCPI accepted."""
    f, rbw, dwell, att = (s[k] for k in ('frequency_hz', 'rbw_hz', 'dwell_seconds', 'attenuation_db'))
    kind = family(model)
    common = {'FREQ:CENT?': f}
    if kind.endswith('bargraph'):
        commands = ['INST:SEL REC', 'INIT1:CONT OFF', 'FORM ASC', 'CALC:UNIT:POW DBUV',
                    'DISP:BARG:PHOL OFF', f'FREQ:CENT {fmt(f)}', f'DET:REC {DETECTORS[s["detector"]]}',
                    'BAND:TYPE PULS' if kind == 'esu-bargraph' else 'BAND:TYPE CISPR',
                    'BAND:AUTO OFF', f'BAND {fmt(rbw)}', 'INP:ATT:AUTO OFF',
                    f'INP:ATT {fmt(att)}', f'SWE:TIME {fmt(dwell)}']
        expected = {**common, 'BAND?': rbw, 'SWE:TIME?': dwell, 'INP:ATT?': att,
                    'DET:REC?': DETECTORS[s['detector']], 'BAND:TYPE?': 'PULS',
                    'CALC:UNIT:POW?': 'DBUV', 'INIT1:CONT?': False, 'DISP:BARG:PHOL?': False,
                    'BAND:AUTO?': False, 'INP:ATT:AUTO?': False}
        if kind == 'epl-bargraph':
            commands.insert(4, 'DISP:BARG:TCO OFF')
            expected['DISP:BARG:TCO?'] = False
        return commands, expected, 'INIT1:IMM', 'TRAC? SINGLE'
    if kind == 'fsw-final-marker':
        # A narrow nonzero span keeps marker X in Hz and RBW/point spacing sufficient.
        low, high = max(0, f-rbw), min(RECEIVER_RANGES[model], f+rbw)
        commands = ['INST:SEL SAN', 'INIT:CONT OFF', 'FORM ASC', 'CALC:UNIT:POW DBUV',
                    'CALC:MARK:AOFF', 'CALC:MARK:FUNC:FME:STAT ON',
                    'CALC:MARK:FUNC:FME:PEAK:AUTO OFF',
                    f'FREQ:STAR {fmt(low)}', f'FREQ:STOP {fmt(high)}',
                    'BAND:TYPE CISP', 'BAND:RES:AUTO OFF', f'BAND:RES {fmt(rbw)}',
                    'BAND:VID:AUTO OFF', f'BAND:VID {fmt(10*rbw)}',
                    'INP:ATT:AUTO OFF', f'INP:ATT {fmt(att)}', 'SWE:POIN 1001',
                    'SWE:TIME:AUTO ON', 'TRIG:SOUR IMM', 'DISP:WIND:TRAC1:MODE WRIT',
                    'DET1 POS', 'CALC:MARK1 ON', 'CALC:MARK1:TRAC 1',
                    f'CALC:MARK1:X {fmt(f)}', f'CALC:MARK:FUNC:FME:DWEL {fmt(dwell)}',
                    f'CALC:MARK1:FUNC:FME:DET {DETECTORS[s["detector"]]}']
        expected = {'FREQ:STAR?': low, 'FREQ:STOP?': high, 'BAND:RES?': rbw, 'INP:ATT?': att,
                    'BAND:TYPE?': 'PULS', 'CALC:UNIT:POW?': 'DBUV', 'INIT:CONT?': False,
                    'BAND:RES:AUTO?': False, 'INP:ATT:AUTO?': False,
                    'CALC:MARK1:X?': f, 'CALC:MARK1?': True, 'CALC:MARK1:TRAC?': 1,
                    'CALC:MARK:FUNC:FME:STAT?': True, 'CALC:MARK:FUNC:FME:PEAK:AUTO?': False,
                    'CALC:MARK:FUNC:FME:DWEL?': dwell,
                    'CALC:MARK1:FUNC:FME:DET?': DETECTORS[s['detector']],
                    'SWE:POIN?': 1001, 'TRIG:SOUR?': 'IMM', 'SWE:TIME?': None,
                    'BAND:VID:AUTO?': False, 'BAND:VID?': 10*rbw}
        return commands, expected, 'INIT:IMM', 'CALC:MARK1:FUNC:FME:RES?'
    wire = {'POS': 'POS', 'QP': 'QPE', 'LINEAR_AVER': 'AVER', 'CISPR_AVER': 'EAV'}[s['detector']]
    # Zero span prevents the firmware's automatic marker zoom from moving the frequency.
    commands = ['INST:SEL SA', 'CONF:SAN', 'INIT:CONT OFF', 'FORM:DATA ASC', 'UNIT:POW DBUV',
                f'FREQ:CENT {fmt(f)}', 'FREQ:SPAN 0', 'SWE:TYPE:AUTO OFF', 'SWE:TYPE SWE',
                'EMC:STAN CISP', 'BAND:RES:AUTO OFF', f'BAND:RES {fmt(rbw)}',
                'BAND:VID:AUTO OFF', f'BAND:VID {fmt(10*rbw)}',
                'POW:ATT:AUTO OFF', f'POW:ATT {fmt(att)}', 'AVER:TYPE:AUTO OFF', 'AVER:TYPE SCAL',
                'CALC:MARK1:MODE POS', 'CALC:MAM:COUP OFF', 'CALC:MAM:DET2 OFF', 'CALC:MAM:DET3 OFF',
                f'CALC:MAM:DET1 {wire}', f'CALC:MAM:DET1:DWEL {fmt(dwell)}', 'TRIG:SOUR IMM']
    expected = {**common, 'FREQ:SPAN?': 0, 'BAND:RES?': rbw, 'POW:ATT?': att,
                'CALC:MAM:DET1:DWEL?': dwell, 'CALC:MAM:DET1?': wire,
                'CALC:MAM:DET2?': 'OFF', 'CALC:MAM:DET3?': 'OFF', 'CALC:MAM:COUP?': False,
                'CALC:MARK1:MODE?': 'POS', 'EMC:STAN?': 'CISP', 'UNIT:POW?': 'DBUV',
                'AVER:TYPE?': 'SCAL', 'AVER:TYPE:AUTO?': False, 'SWE:TYPE?': 'SWE',
                'SWE:TYPE:AUTO?': False, 'INIT:CONT?': False, 'BAND:RES:AUTO?': False,
                'POW:ATT:AUTO?': False, 'TRIG:SOUR?': 'IMM',
                'BAND:VID:AUTO?': False, 'BAND:VID?': 10*rbw}
    return commands, expected, None, 'CALC:MARK1:FUNC:MAM?'


def verify_settings(model, values, settings):
    _, expected, _, _ = contract(model, settings)
    if set(values) != set(expected): raise InstrumentError('Incomplete detector readback evidence')
    for query, wanted in expected.items():
        value = values[query]
        if wanted is None:
            number(scalar(value), 'automatic initial sweep duration', 1e-6, 10000)
        elif isinstance(wanted, bool):
            if switch(value) != wanted: raise InstrumentError('Detector state mismatch: ' + query)
        elif isinstance(wanted, (int, float)):
            close_enough(scalar(value), wanted, abs_tol=1e-6 if 'DWEL' in query or 'TIME' in query else .01)
        elif value.strip().upper() != wanted:
            raise InstrumentError('Detector setting mismatch: ' + query)


def parse_result(model, raw, settings):
    if family(model) != 'xseries-measure-at-marker': return scalar(raw)
    fields = raw.split(',')
    if len(fields) != 4: raise InstrumentError('Measure-at-Marker must return four fields')
    level, off2, off3, frequency = map(scalar, fields)
    if level == -999 or (off2, off3) != (-999, -999):
        raise InstrumentError('Measure-at-Marker missing result or unexpected active detector')
    close_enough(frequency, settings['frequency_hz'], abs_tol=.01)
    return level


def read_level(driver, **args):
    model = driver.expected_model
    validate_receiver(model, driver.max_hz, **args)
    if args['dwell_seconds'] >= driver.io.timeout: raise ValueError('timeout must exceed dwell duration plus settling margin')
    driver.ready()
    settings = dict(args, filter_type='CISPR')
    commands, expected, start, result_query = contract(model, settings)
    with driver.io.transaction():
        capability = dict(required_option=required_option(model), firmware=driver.identity.firmware,
                          firmware_status='site-validation-required', dialect=family(model),
                          options_raw=driver.io.query('*OPT?') if required_option(model) else None)
        verify_capability(model, capability, driver.identity)
        driver.errors()
        driver.io.write('ABOR')
        driver.opc()
        driver.apply(commands)
        before = {q: driver.io.query(q) for q in expected}
        verify_settings(model, before, settings)
        if model.startswith('FSW') and scalar(before['SWE:TIME?']) + args['dwell_seconds'] >= driver.io.timeout:
            raise ValueError('timeout must exceed FSW initial sweep plus final dwell and settling margin')
        driver.errors()
        if start:
            driver.io.write(start)
            driver.opc()
        raw = driver.io.query(result_query)
        value = parse_result(model, raw, settings)
        driver.errors()
        after = {q: driver.io.query(q) for q in expected}
        verify_settings(model, after, settings)
        if model.startswith('FSW'):
            close_enough(scalar(after['SWE:TIME?']), scalar(before['SWE:TIME?']))
        driver.errors()
        return ReceiverLevel(value, 'dBuV', datetime.now(timezone.utc).isoformat(), driver.identity,
                             raw, settings, dict(before=before, after=after, capability=capability))
