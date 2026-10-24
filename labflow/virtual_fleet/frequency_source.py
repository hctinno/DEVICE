"""Explicit synthetic linear density curves and exact single-band integration."""

from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import hashlib
import json
import math
import re


_LIMIT = 4 * 1024 * 1024
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_FIXED = {'schema_version': 1, 'kind': 'synthetic_piecewise_density_source', 'synthetic': True,
          'reference_plane': 'dut_output', 'time_basis': 'on_interval', 'interpolation': 'linear_mw_per_hz'}
_FIELDS = set(_FIXED) | {'source_id', 'declared_mode_id', 'center_hz', 'power_method',
                         'frequency_offsets_hz', 'density_mw_per_hz'}
_FLAGS = {'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
          'method_approval': 'not_assessed', 'regulatory_scope_complete': False,
          'waveform_implemented': False, 'oem_mode_verified': False}


def _invalid(condition):
    if not condition:
        raise ValueError('invalid_frequency_source')


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _snapshot(value):
    def walk(item, depth=0):
        _invalid(depth <= 32)
        if type(item) is dict:
            _invalid(all(type(key) is str for key in item))
            return {key: walk(child, depth + 1) for key, child in item.items()}
        if type(item) is list:
            return [walk(child, depth + 1) for child in item]
        if item is None or type(item) in (str, bool, int):
            return item
        _invalid(type(item) is float and math.isfinite(item))
        return item
    try:
        raw = json.dumps(walk(value), ensure_ascii=False, sort_keys=True, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
        _invalid(len(raw) <= _LIMIT)
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError('invalid_frequency_source') from None


def _positive_float(value):
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError('numeric_result_out_of_range') from None
    if not math.isfinite(result) or result <= 0:
        raise ValueError('numeric_result_out_of_range')
    return result


def _validated(value):
    spec, fingerprint = _snapshot(value)
    _invalid(type(spec) is dict and set(spec) == _FIELDS)
    for key, expected in _FIXED.items():
        _invalid(type(spec[key]) is type(expected) and spec[key] == expected)
    for key in ['source_id', 'declared_mode_id']:
        _invalid(type(spec[key]) is str and _ID.fullmatch(spec[key]) is not None)
    _invalid(type(spec['power_method']) is str and spec['power_method'] in {'on_mean', 'peak'})
    _invalid(_finite(spec['center_hz']) and spec['center_hz'] > 0)
    offsets, densities = spec['frequency_offsets_hz'], spec['density_mw_per_hz']
    _invalid(type(offsets) is list and type(densities) is list and 3 <= len(offsets) <= 4096
             and len(offsets) == len(densities) and all(_finite(value) for value in offsets)
             and all(_finite(value) and value > 0 for value in densities)
             and all(left < right for left, right in zip(offsets, offsets[1:])))
    axis = [Fraction(value) for value in offsets]
    density = [Fraction(value) for value in densities]
    center = Fraction(spec['center_hz'])
    for offset in axis:
        absolute = center + offset
        _invalid(absolute > 0)
        _positive_float(absolute)
    return spec, fingerprint, axis, density


def _headers(spec, fingerprint):
    return {'schema_version': 1, 'source_id': spec['source_id'], 'declared_mode_id': spec['declared_mode_id'],
            'input_sha256': fingerprint, 'reference_plane': spec['reference_plane'],
            'time_basis': spec['time_basis'], 'power_method': spec['power_method'], **_FLAGS}


def _relative_db(ratio):
    if ratio == 1:
        return 0.0
    for precision in (80, 160, 320, 640, 1280):
        fixed = Context(prec=precision, rounding=ROUND_HALF_EVEN, Emin=-999999,
                        Emax=999999, clamp=0, flags=[], traps=[])
        with localcontext(fixed):
            value = Decimal(ratio.numerator) / Decimal(ratio.denominator)
            lower = (value.next_minus().log10().next_minus() * 10).next_minus()
            upper = (value.next_plus().log10().next_plus() * 10).next_plus()
            if upper >= 0:
                continue
            left, right = float(lower), float(upper)
            if left == right and math.isfinite(left) and left < 0:
                return left
    raise ValueError('numeric_result_out_of_range')


def generate_frequency_source(spec):
    """Project declared density knots into relative dB samples, without BW analysis."""
    spec, fingerprint, _, density = _validated(spec)
    maximum = max(density)
    cache, displayed, levels = {}, {}, []
    for value in density:
        if value not in cache:
            level = _relative_db(value / maximum)
            if level in displayed and displayed[level] != value:
                raise ValueError('numeric_result_out_of_range')
            cache[value], displayed[level] = level, value
        levels.append(cache[value])
    trace = {'schema_version': 1, 'kind': 'synthetic_frequency_spectrum',
             'capture_id': 'fs:' + fingerprint, 'synthetic': True,
             'axis_domain': 'frequency_offset_hz', 'sample_unit': 'dB',
             'amplitude_basis': 'relative_to_peak', 'selection_policy': 'unique_peak_single_lobe_linear_db',
             'frequency_offsets_hz': list(spec['frequency_offsets_hz']), 'relative_levels_db': levels}
    return {**_headers(spec, fingerprint), 'kind': 'synthetic_frequency_source',
            'center_hz': spec['center_hz'], 'density_interpolation': 'linear_mw_per_hz',
            'trace_projection': 'knot_samples_linear_db', 'trace': trace}


def integrate_source_3khz(spec, *, start_offset_hz):
    """Integrate exactly one fully covered 3000 Hz band of the density function."""
    spec, fingerprint, axis, density = _validated(spec)
    if not _finite(start_offset_hz):
        raise ValueError('invalid_frequency_interval')
    start = Fraction(start_offset_hz)
    stop = start + 3000
    if start < axis[0] or stop > axis[-1]:
        raise ValueError('invalid_frequency_interval')
    if type(start_offset_hz) is int:
        public_stop = start_offset_hz + 3000
    else:
        try:
            public_stop = float(stop)
        except (OverflowError, ValueError):
            raise ValueError('numeric_result_out_of_range') from None
        if not math.isfinite(public_stop):
            raise ValueError('numeric_result_out_of_range')
    public_width = Fraction(public_stop) - Fraction(start_offset_hz)
    if public_width <= 0 or abs(public_width - 3000) > Fraction(math.ulp(3000.0)):
        raise ValueError('numeric_result_out_of_range')

    power = Fraction(0)
    for x0, x1, y0, y1 in zip(axis, axis[1:], density, density[1:]):
        low, high = max(start, x0), min(stop, x1)
        if high <= low:
            continue
        low_density = y0 + (y1 - y0) * (low - x0) / (x1 - x0)
        high_density = y0 + (y1 - y0) * (high - x0) / (x1 - x0)
        power += (low_density + high_density) * (high - low) / 2
    power_mw = _positive_float(power)
    try:
        ratio = {'numerator': str(power.numerator), 'denominator': str(power.denominator)}
    except ValueError:
        raise ValueError('numeric_result_out_of_range') from None
    return {**_headers(spec, fingerprint), 'kind': 'synthetic_integrated_band_power',
            'start_offset_hz': start_offset_hz, 'stop_offset_hz': public_stop,
            'reference_bandwidth_hz': 3000, 'power_mw': power_mw, 'exact_power_ratio': ratio,
            'source_coverage': 'single_declared_band', 'max_search_complete': False}
