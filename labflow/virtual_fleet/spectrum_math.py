"""Pure math for explicitly synthetic frequency and declared-band inputs."""

import hashlib
import json
import math
import re


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
    if inside_y == _THRESHOLD_DB:
        return inside_x
    # Measure from the inside sample: subtracting nearly equal huge levels
    # or forming an outside-to-inside axis span would lose/overflow a crossing.
    fraction = (inside_y - _THRESHOLD_DB) / (inside_y - outside_y)
    try:
        crossing = math.fsum((inside_x * (1 - fraction), outside_x * fraction))
    except (OverflowError, ValueError):
        raise ValueError('numeric_result_out_of_range') from None
    _numeric_result(crossing)
    if not min(inside_x, outside_x) <= crossing <= max(inside_x, outside_x):
        raise ValueError('numeric_result_out_of_range')
    return crossing


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
    left_hz = (axis[left] if levels[left] == _THRESHOLD_DB else
               _crossing(axis[left], levels[left], axis[left - 1], levels[left - 1]))
    right_hz = (axis[right] if levels[right] == _THRESHOLD_DB else
                _crossing(axis[right], levels[right], axis[right + 1], levels[right + 1]))
    bandwidth = _numeric_result(right_hz - left_hz)
    if bandwidth <= 0:
        raise ValueError('numeric_result_out_of_range')
    result.update(status='complete', left_offset_hz=left_hz, right_offset_hz=right_hz,
                  bandwidth_hz=bandwidth, margin_hz=_numeric_result(bandwidth - _MINIMUM_BANDWIDTH_HZ),
                  conditional_comparison='meets' if bandwidth >= _MINIMUM_BANDWIDTH_HZ else 'below')
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
    else:
        if value <= 0:
            raise ValueError('invalid_psd_input')
        power_mw = _numeric_result(value * _REFERENCE_BANDWIDTH_HZ)
        if power_mw <= 0:
            raise ValueError('numeric_result_out_of_range')
        power_dbm = _numeric_result(10 * math.log10(power_mw))
    return {
        **_identity(sample), 'kind': 'synthetic_psd_band_result',
        'algorithm_id': 'declared_3khz_power_v1', 'input_basis': basis,
        'power_dbm': power_dbm, 'power_mw': power_mw,
        'reference_bandwidth_hz': _REFERENCE_BANDWIDTH_HZ, 'maximum_dbm': _MAXIMUM_DBM,
        'margin_db': _numeric_result(_MAXIMUM_DBM - power_dbm),
        'conditional_comparison': 'meets' if power_dbm <= _MAXIMUM_DBM else 'above',
        'source_coverage': 'single_declared_band', 'max_search_complete': False,
    }
