"""Pure math for explicitly synthetic frequency and declared-band inputs."""

import hashlib
import json
import math
import re
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction


_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_TRACE_CONSTANTS = {
    'schema_version': 1, 'kind': 'synthetic_frequency_spectrum', 'synthetic': True,
    'axis_domain': 'frequency_offset_hz', 'sample_unit': 'dB',
    'amplitude_basis': 'relative_to_peak',
    'selection_policy': 'unique_peak_single_lobe_linear_db',
}
_TRACE_FIELDS = set(_TRACE_CONSTANTS) | {'capture_id', 'frequency_offsets_hz', 'relative_levels_db'}
_MINIMUM_BANDWIDTH_HZ = 500000
_THRESHOLD_DB = -6
_PSD_CONSTANTS = {
    'schema_version': 1, 'kind': 'synthetic_psd_input', 'synthetic': True,
    'reference_plane': 'dut_output', 'time_basis': 'on_interval',
    'path_correction_state': 'already_applied',
}
_PSD_FIELDS = set(_PSD_CONSTANTS) | {'capture_id', 'input_basis', 'output_power_method', 'psd_power_method'}
_PSD_VALUE_FIELDS = {'band_power_3khz': 'power_dbm', 'flat_density_mw_per_hz': 'density_mw_per_hz'}
_METHODS = {'on_mean', 'peak'}
_REFERENCE_BANDWIDTH_HZ = 3000
_MAXIMUM_DBM = 8


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _record(value, fields, constants, code):
    if type(value) is not dict or set(value) != fields:
        raise ValueError(code)
    if any(type(value[key]) is not type(expected) or value[key] != expected
           for key, expected in constants.items()):
        raise ValueError(code)
    capture = value['capture_id']
    if type(capture) is not str or not _ID.fullmatch(capture):
        raise ValueError(code)


def _identity(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                     separators=(',', ':')).encode('utf-8')
    return {
        'schema_version': 1, 'capture_id': value['capture_id'],
        'input_sha256': hashlib.sha256(raw).hexdigest(), 'synthetic': True,
        'hardware_verified': False, 'ai_model_called': False,
        'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
    }


def _numeric_result(value):
    if not _finite(value):
        raise ValueError('numeric_result_out_of_range')
    return value


def _crossing(inside_x, inside_y, outside_x, outside_y):
    # Fraction preserves the exact values of both Python ints and input floats.
    inside, outside = Fraction(inside_x), Fraction(outside_x)
    fraction = ((Fraction(inside_y) - _THRESHOLD_DB)
                / (Fraction(inside_y) - Fraction(outside_y)))
    return inside + (outside - inside) * fraction


def _fraction_float(value):
    try:
        return _numeric_result(float(value))
    except (OverflowError, ValueError):
        raise ValueError('numeric_result_out_of_range') from None


def _bandwidth_values(left, right, exact_left, exact_right):
    exact_width = exact_right - exact_left
    width = _fraction_float(exact_width)
    displayed_difference = Fraction(right) - Fraction(left)
    displayed_width = _fraction_float(displayed_difference)
    meets = exact_width >= _MINIMUM_BANDWIDTH_HZ
    # A one-ULP bound concerns representation only. The boundary comparison
    # always uses exact_width, with no allowed excess or regulatory tolerance.
    if (width <= 0 or displayed_difference <= 0
            or abs(displayed_difference - exact_width) > Fraction(math.ulp(width))
            or (displayed_difference >= _MINIMUM_BANDWIDTH_HZ) != meets
            or (displayed_width >= _MINIMUM_BANDWIDTH_HZ) != meets
            or (Fraction(width) >= _MINIMUM_BANDWIDTH_HZ) != meets):
        raise ValueError('numeric_result_out_of_range')
    return width, _fraction_float(exact_width - _MINIMUM_BANDWIDTH_HZ), 'meets' if meets else 'below'


def _density_log_values(exact_power):
    # Every divide/log10/product/subtraction is enclosed by adjacent Decimal
    # values. Agreeing bounds certify both the comparison and displayed floats.
    for precision in (80, 160, 320, 640, 1280):
        fixed = Context(prec=precision, rounding=ROUND_HALF_EVEN,
                        Emin=-999999, Emax=999999, traps=[])
        with localcontext(fixed):
            power = Decimal(exact_power.numerator) / Decimal(exact_power.denominator)
            lower = (power.next_minus().log10().next_minus() * 10).next_minus()
            upper = (power.next_plus().log10().next_plus() * 10).next_plus()
            maximum = Decimal(_MAXIMUM_DBM)
            if upper <= maximum:
                comparison = 'meets'
            elif lower > maximum:
                comparison = 'above'
            else:
                continue
            low_margin = (maximum - upper).next_minus()
            high_margin = (maximum - lower).next_plus()
            dbm, margin = float(lower), float(low_margin)
            if dbm == float(upper) and margin == float(high_margin):
                return _numeric_result(dbm), _numeric_result(margin), comparison
    raise ValueError('numeric_result_out_of_range')


def analyze_6db_bandwidth(trace):
    """Find one unique-peak lobe's -6 dB crossings; never extrapolate."""
    _record(trace, _TRACE_FIELDS, _TRACE_CONSTANTS, 'invalid_spectrum_input')
    axis, levels = trace['frequency_offsets_hz'], trace['relative_levels_db']
    if (type(axis) is not list or type(levels) is not list
            or not 3 <= len(axis) <= 65536 or len(axis) != len(levels)
            or not all(_finite(value) for value in axis)
            or not all(_finite(value) for value in levels)
            or any(left >= right for left, right in zip(axis, axis[1:]))
            or max(levels) != 0):
        raise ValueError('invalid_spectrum_input')

    reasons = []
    if levels.count(0) != 1:
        reasons.append('non_unique_peak')
    above = [value >= _THRESHOLD_DB for value in levels]
    components = sum(value and (index == 0 or not above[index - 1])
                     for index, value in enumerate(above))
    if components != 1:
        reasons.append('disconnected_lobes')
    if any(left == right == _THRESHOLD_DB for left, right in zip(levels, levels[1:])):
        reasons.append('threshold_plateau')

    result = {
        **_identity(trace), 'kind': 'synthetic_bandwidth_result',
        'algorithm_id': 'peak6_linear_db_v1', 'status': 'incomplete', 'reason_codes': reasons,
        'left_offset_hz': None, 'right_offset_hz': None, 'bandwidth_hz': None,
        'minimum_bandwidth_hz': _MINIMUM_BANDWIDTH_HZ, 'margin_hz': None,
        'conditional_comparison': None,
    }
    if reasons:
        return result

    left = above.index(True)
    right = len(above) - 1 - above[::-1].index(True)
    if left == 0 and levels[left] != _THRESHOLD_DB:
        reasons.append('left_crossing_missing')
    if right == len(axis) - 1 and levels[right] != _THRESHOLD_DB:
        reasons.append('right_crossing_missing')
    if reasons:
        return result
    exact_left = (Fraction(axis[left]) if levels[left] == _THRESHOLD_DB else
                  _crossing(axis[left], levels[left], axis[left - 1], levels[left - 1]))
    exact_right = (Fraction(axis[right]) if levels[right] == _THRESHOLD_DB else
                   _crossing(axis[right], levels[right], axis[right + 1], levels[right + 1]))
    left_hz = axis[left] if levels[left] == _THRESHOLD_DB else _fraction_float(exact_left)
    right_hz = axis[right] if levels[right] == _THRESHOLD_DB else _fraction_float(exact_right)
    bandwidth, margin, comparison = _bandwidth_values(left_hz, right_hz, exact_left, exact_right)
    result.update(status='complete', left_offset_hz=left_hz, right_offset_hz=right_hz,
                  bandwidth_hz=bandwidth, margin_hz=margin, conditional_comparison=comparison)
    return result


def analyze_psd_band(sample):
    """Compare one declared synthetic 3 kHz band; perform no maximum search."""
    if type(sample) is not dict:
        raise ValueError('invalid_psd_input')
    basis = sample.get('input_basis')
    if type(basis) is not str or basis not in _PSD_VALUE_FIELDS:
        raise ValueError('invalid_psd_input')
    value_field = _PSD_VALUE_FIELDS[basis]
    _record(sample, _PSD_FIELDS | {value_field}, _PSD_CONSTANTS, 'invalid_psd_input')
    output_method, psd_method = sample['output_power_method'], sample['psd_power_method']
    if (type(output_method) is not str or output_method not in _METHODS
            or type(psd_method) is not str or psd_method != output_method):
        raise ValueError('invalid_psd_input')
    value = sample[value_field]
    if not _finite(value):
        raise ValueError('invalid_psd_input')
    if basis == 'band_power_3khz':
        if not -300 <= value <= 100:
            raise ValueError('invalid_psd_input')
        power_dbm = float(value)
        power_mw = _numeric_result(10 ** (power_dbm / 10))
        margin = _fraction_float(Fraction(_MAXIMUM_DBM) - Fraction(value))
        comparison = 'meets' if value <= _MAXIMUM_DBM else 'above'
    else:
        if value <= 0:
            raise ValueError('invalid_psd_input')
        exact_power = Fraction(value) * _REFERENCE_BANDWIDTH_HZ
        power_mw = _fraction_float(exact_power)
        if power_mw <= 0:
            raise ValueError('numeric_result_out_of_range')
        power_dbm, margin, comparison = _density_log_values(exact_power)
    return {
        **_identity(sample), 'kind': 'synthetic_psd_band_result',
        'algorithm_id': 'declared_3khz_power_v1', 'input_basis': basis,
        'power_dbm': power_dbm, 'power_mw': power_mw,
        'reference_bandwidth_hz': _REFERENCE_BANDWIDTH_HZ, 'maximum_dbm': _MAXIMUM_DBM,
        'margin_db': margin, 'conditional_comparison': comparison,
        'source_coverage': 'single_declared_band', 'max_search_complete': False,
    }
