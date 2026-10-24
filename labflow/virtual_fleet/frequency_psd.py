"""Exact-ratio comparison of one declared synthetic 3 kHz source band."""
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import json
import math
import re

from labflow.virtual_fleet.frequency_source import integrate_source_3khz


_FIXED = {
    'schema_version': 1, 'kind': 'synthetic_integrated_band_power',
    'reference_bandwidth_hz': 3000, 'reference_plane': 'dut_output',
    'time_basis': 'on_interval', 'source_coverage': 'single_declared_band',
    'max_search_complete': False, 'synthetic': True, 'hardware_verified': False,
    'ai_model_called': False, 'method_approval': 'not_assessed',
    'regulatory_scope_complete': False, 'waveform_implemented': False,
    'oem_mode_verified': False,
}
_FIELDS = set(_FIXED) | {
    'source_id', 'declared_mode_id', 'input_sha256', 'start_offset_hz',
    'stop_offset_hz', 'power_method', 'power_mw', 'exact_power_ratio',
}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_MAX_RATIO_DIGITS = 1234
_MAX_RATIO_BITS = 4096
_MAX_BAND_BYTES = 16384


def _require(condition):
    if not condition:
        raise ValueError('invalid_integrated_power')


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _integer(text):
    _require(type(text) is str)
    if len(text) > _MAX_RATIO_DIGITS:
        raise ValueError('numeric_result_out_of_range')
    _require(re.fullmatch(r'[1-9][0-9]*', text) is not None)
    # Small chunks avoid dependence on the host's decimal-int conversion limit.
    value = 0
    for offset in range(0, len(text), 9):
        chunk = text[offset:offset + 9]
        value = value * 10**len(chunk) + int(chunk)
        if value.bit_length() > _MAX_RATIO_BITS:
            raise ValueError('numeric_result_out_of_range')
    return value


def _band_snapshot(band):
    _require(type(band) is dict and set(band) == _FIELDS)
    for key, expected in _FIXED.items():
        _require(type(band[key]) is type(expected) and band[key] == expected)
    for key in ('source_id', 'declared_mode_id'):
        _require(type(band[key]) is str and _ID.fullmatch(band[key]) is not None)
    _require(type(band['input_sha256']) is str
             and re.fullmatch(r'[0-9a-f]{64}', band['input_sha256']) is not None)
    _require(type(band['power_method']) is str and band['power_method'] in ('on_mean', 'peak'))
    _require(_finite(band['start_offset_hz']) and _finite(band['stop_offset_hz'])
             and type(band['start_offset_hz']) is type(band['stop_offset_hz']))
    width = Fraction(band['stop_offset_hz']) - Fraction(band['start_offset_hz'])
    _require(width > 0 and abs(width - 3000) <= Fraction(math.ulp(3000.0)))
    _require(type(band['power_mw']) is float and math.isfinite(band['power_mw'])
             and band['power_mw'] > 0)
    ratio = band['exact_power_ratio']
    _require(type(ratio) is dict and set(ratio) == {'numerator', 'denominator'})
    numerator, denominator = _integer(ratio['numerator']), _integer(ratio['denominator'])
    _require(math.gcd(numerator, denominator) == 1)
    try:
        display = float(Fraction(numerator, denominator))
    except (OverflowError, ValueError):
        raise ValueError('numeric_result_out_of_range') from None
    if not math.isfinite(display) or display <= 0:
        raise ValueError('numeric_result_out_of_range')
    _require(display == band['power_mw'])
    try:
        raw = json.dumps(band, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                         allow_nan=False).encode('utf-8')
        _require(len(raw) <= _MAX_BAND_BYTES)
        return json.loads(raw), numerator, denominator
    except (TypeError, ValueError, OverflowError, UnicodeError):
        raise ValueError('invalid_integrated_power') from None


def _log_display(numerator, denominator, comparison):
    if numerator == denominator:
        return 0.0, 8.0
    for precision in (80, 160, 320, 640, 1280):
        fixed = Context(prec=precision, rounding=ROUND_HALF_EVEN, Emin=-999999,
                        Emax=999999, clamp=0, flags=[], traps=[])
        with localcontext(fixed):
            power = Decimal(numerator) / Decimal(denominator)
            lower = (power.next_minus().log10().next_minus() * 10).next_minus()
            upper = (power.next_plus().log10().next_plus() * 10).next_plus()
            lower_margin = (Decimal(8) - upper).next_minus()
            upper_margin = (Decimal(8) - lower).next_plus()
            dbm, margin = float(lower), float(lower_margin)
            if dbm != float(upper) or margin != float(upper_margin):
                continue
            if (not math.isfinite(dbm) or not math.isfinite(margin)
                    or dbm == 0 or margin == 0
                    or (dbm > 0) != (numerator > denominator)
                    or (margin > 0) != (comparison == 'meets')):
                raise ValueError('numeric_result_out_of_range')
            return dbm, margin
    raise ValueError('numeric_result_out_of_range')


def analyze_source_psd(spec, *, start_offset_hz):
    """Use the source's exact integral; no maximum search or physical approval."""
    try:
        integrated = integrate_source_3khz(spec, start_offset_hz=start_offset_hz)
    except ValueError as error:
        code = str(error)
        if code not in {'invalid_frequency_source', 'invalid_frequency_interval',
                        'numeric_result_out_of_range'}:
            code = 'invalid_integrated_power'
        raise ValueError(code) from None
    band, numerator, denominator = _band_snapshot(integrated)
    # 10*log10(a/b) <= 8 iff a**5 <= 10**4 * b**5; no display or epsilon.
    comparison = 'meets' if numerator**5 <= 10000 * denominator**5 else 'above'
    power_dbm, margin_db = _log_display(numerator, denominator, comparison)
    return {
        **band, 'kind': 'synthetic_source_psd_band_result',
        'algorithm_id': 'exact_source_3khz_psd_v1',
        'input_basis': 'exact_integrated_power_ratio',
        'comparison_basis': 'exact_integer_fifth_power',
        'power_dbm': power_dbm, 'maximum_dbm': 8,
        'margin_db': margin_db, 'conditional_comparison': comparison,
    }
