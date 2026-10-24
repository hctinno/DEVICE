"""Exact continuous-window maximum on a declared synthetic linear density."""
from bisect import bisect_right
from fractions import Fraction
import json
import math

from labflow.virtual_fleet.frequency_source import _validated
from labflow.virtual_fleet.frequency_psd import _log_display


_WIDTH = 3000
_MAX_CANDIDATES = 16384
_MAX_WORK_BITS = 8192
_MAX_PUBLIC_BITS = 4096
_MAX_RESULT_BYTES = 16384


def _numeric_error():
    raise ValueError('numeric_result_out_of_range')


def _checked(value):
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > _MAX_WORK_BITS:
        _numeric_error()
    return value


def _integer_text(value):
    if value == 0:
        return '0'
    sign = '-' if value < 0 else ''
    value = abs(value)
    parts = []
    while value:
        value, chunk = divmod(value, 10**9)
        parts.append(chunk)
    return sign + str(parts[-1]) + ''.join(f'{part:09d}' for part in reversed(parts[:-1]))


def _ratio(value):
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > _MAX_PUBLIC_BITS:
        _numeric_error()
    numerator, denominator = _integer_text(value.numerator), _integer_text(value.denominator)
    if len(numerator.lstrip('-')) > 1234 or len(denominator) > 1234:
        _numeric_error()
    return {'numerator': numerator, 'denominator': denominator}


def _finish(result):
    try:
        raw = json.dumps(result, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError):
        _numeric_error()
    if len(raw) > _MAX_RESULT_BYTES:
        _numeric_error()
    return result


class _Curve:
    def __init__(self, axis, density):
        self.axis, self.density = axis, density
        self.slopes, self.prefix = [], [Fraction(0)]
        for x0, x1, y0, y1 in zip(axis, axis[1:], density, density[1:]):
            width = _checked(x1 - x0)
            self.slopes.append(_checked(_checked(y1 - y0) / width))
            area = _checked(_checked(_checked(y0 + y1) * width) / 2)
            self.prefix.append(_checked(self.prefix[-1] + area))

    def _segment(self, point):
        if not self.axis[0] <= point <= self.axis[-1]:
            _numeric_error()
        return bisect_right(self.axis, point) - 1

    def value(self, point):
        index = self._segment(point)
        if index == len(self.axis) - 1:
            return self.density[-1]
        delta = _checked(point - self.axis[index])
        return _checked(self.density[index] + _checked(self.slopes[index] * delta))

    def primitive(self, point):
        index = self._segment(point)
        if index == len(self.axis) - 1:
            return self.prefix[-1]
        delta = _checked(point - self.axis[index])
        value = _checked(self.density[index] + _checked(self.slopes[index] * delta))
        local_area = _checked(_checked(_checked(self.density[index] + value) * delta) / 2)
        return _checked(self.prefix[index] + local_area)


def _candidates(curve, low, high):
    points = {low, high}
    for knot in curve.axis:
        for point in (knot, _checked(knot - _WIDTH)):
            if low <= point <= high:
                points.add(point)
                if len(points) > _MAX_CANDIDATES:
                    _numeric_error()
    ordered = sorted(points)
    derivative = [
        _checked(curve.value(_checked(point + _WIDTH)) - curve.value(point))
        for point in ordered
    ]
    # On each piece this continuous derivative is affine. Endpoint roots and
    # identically-zero plateaus are already represented by the breakpoints.
    candidates = set(points)
    for left, right, g0, g1 in zip(ordered, ordered[1:], derivative, derivative[1:]):
        if g0 < 0 < g1 or g1 < 0 < g0:
            fraction = _checked(g0 / _checked(g1 - g0))
            root = _checked(left - _checked(fraction * _checked(right - left)))
            if not left < root < right:
                _numeric_error()
            candidates.add(root)
            if len(candidates) > _MAX_CANDIDATES:
                _numeric_error()
    return sorted(candidates)


def find_source_psd_maximum(spec):
    """Find all legal 3 kHz window extrema; completeness covers this curve only."""
    try:
        snapshot, fingerprint, axis, density = _validated(spec)
    except ValueError as error:
        code = str(error)
        if code not in {'invalid_frequency_source', 'numeric_result_out_of_range'}:
            code = 'invalid_frequency_source'
        raise ValueError(code) from None
    for value in (*axis, *density):
        _checked(value)
    low, high = axis[0], _checked(axis[-1] - _WIDTH)
    result = {
        'schema_version': 1, 'kind': 'synthetic_source_psd_maximum',
        'algorithm_id': 'exact_continuous_3khz_density_max_v1',
        'source_id': snapshot['source_id'], 'declared_mode_id': snapshot['declared_mode_id'],
        'input_sha256': fingerprint, 'reference_plane': snapshot['reference_plane'],
        'time_basis': snapshot['time_basis'], 'power_method': snapshot['power_method'],
        'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
        'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
        'waveform_implemented': False, 'oem_mode_verified': False,
        'reference_bandwidth_hz': _WIDTH, 'status': 'incomplete',
        'reason_codes': ['source_support_shorter_than_reference_bandwidth'],
        'source_coverage': 'declared_density_support', 'max_search_complete': False,
        'search_domain': {'minimum_start_offset_hz': _ratio(low),
                          'maximum_start_offset_hz': _ratio(high), 'empty': high < low},
        'winning_interval': None, 'candidate_count': 0,
        'tie_break_policy': 'earliest_exact_start', 'exact_power_ratio': None,
        'power_mw': None, 'power_dbm': None, 'maximum_dbm': 8, 'margin_db': None,
        'conditional_comparison': None,
    }
    if high < low:
        return _finish(result)
    curve = _Curve(axis, density)
    candidates = _candidates(curve, low, high)
    if not candidates or len(candidates) > _MAX_CANDIDATES:
        _numeric_error()
    best_start = best_power = None
    for start in candidates:
        power = _checked(curve.primitive(_checked(start + _WIDTH)) - curve.primitive(start))
        if power <= 0:
            _numeric_error()
        # Sorted exact starts and strict replacement implement earliest ties.
        if best_power is None or power > best_power:
            best_start, best_power = start, power
    interval = {'start_offset_hz': _ratio(best_start),
                'stop_offset_hz': _ratio(_checked(best_start + _WIDTH))}
    power_ratio = _ratio(best_power)
    try:
        power_mw = float(best_power)
    except (OverflowError, ValueError):
        _numeric_error()
    if not math.isfinite(power_mw) or power_mw <= 0:
        _numeric_error()
    numerator, denominator = best_power.numerator, best_power.denominator
    comparison = 'meets' if numerator**5 <= 10000 * denominator**5 else 'above'
    try:
        power_dbm, margin_db = _log_display(numerator, denominator, comparison)
    except (ValueError, ArithmeticError):
        _numeric_error()
    result.update(
        status='complete', reason_codes=[], source_coverage='complete_declared_density_support',
        max_search_complete=True, winning_interval=interval, candidate_count=len(candidates),
        exact_power_ratio=power_ratio, power_mw=power_mw, power_dbm=power_dbm,
        margin_db=margin_db, conditional_comparison=comparison,
    )
    return _finish(result)
