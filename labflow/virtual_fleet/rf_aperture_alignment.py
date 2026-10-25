"""Pure declared boxcar/ZOH aperture projection; no runtime or device I/O."""
from fractions import Fraction
import hashlib
import json
import math
import re


_PREFIX = 'rf_aperture_alignment_'
_CODES = frozenset(_PREFIX + x for x in ('invalid_argument', 'budget_exceeded', 'numeric_unavailable'))
_MAX_BODY = 1048576
_MAX_BITS = 4096
_MIN_NORMAL = float.fromhex('0x1p-1022')
_MIN_EXACT = Fraction(1, 2**1022)
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
_INPUT_FLAGS = dict(data_origin='authored_synthetic', synthetic=True, hardware_verified=False,
                    physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
                    method_approval='not_assessed', regulatory_scope_complete=False,
                    model_scope='normalized_baseband_sample_math_v1')
_OUTPUT_FLAGS = dict(_INPUT_FLAGS, model_scope='declared_rf_aperture_boxcar_zoh_v1',
                     runtime_alignment_verified=False)


class RfApertureAlignmentError(ValueError):
    """Known public failures carry a fixed code only."""

    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + 'invalid_argument'
        super().__init__(self.code)


def _fail(suffix):
    raise RfApertureAlignmentError(_PREFIX + suffix) from None


def _require(condition, suffix='invalid_argument'):
    if not condition:
        _fail(suffix)


def _record(value, fields):
    _require(type(value) is dict and len(value) == len(fields) and all(type(k) is str for k in value) and set(value) == set(fields))


def _fixed(value, expected):
    _require(type(value) is type(expected) and value == expected)


def _integer(value, low, high, *, budget=False):
    _require(type(value) is int and value >= low)
    if value > high:
        _fail('budget_exceeded' if budget else 'invalid_argument')
    return value


def _number(value, low, high):
    _require(type(value) in (int, float) and low <= value <= high)
    _require(math.isfinite(value))
    return value


def _body(value, limit):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    _require(len(raw) <= limit, 'budget_exceeded')
    return raw


def _packet(value):
    _record(value, ('schema_version', 'kind', 'grid', 'sample_unit', 'samples',
                    'verification', 'execution_authorized', 'rerun_authorized'))
    for key, expected in (('schema_version', 1), ('kind', 'synthetic_rf_baseband_envelope'),
                          ('sample_unit', 'sqrt_mW'), ('execution_authorized', False),
                          ('rerun_authorized', False)):
        _fixed(value[key], expected)
    grid = value['grid']
    _record(grid, ('sample_rate_hz', 'sample_count', 't0_seconds', 'interpolation'))
    _integer(grid['sample_rate_hz'], 1, 1000000000)
    count = _integer(grid['sample_count'], 1, 4096, budget=True)
    _fixed(grid['t0_seconds'], 0)
    _fixed(grid['interpolation'], 'zero_order_hold')
    flags = value['verification']
    _record(flags, _INPUT_FLAGS)
    for key, expected in _INPUT_FLAGS.items():
        _fixed(flags[key], expected)
    rows = value['samples']
    _require(type(rows) is list)
    _require(len(rows) <= 4096, 'budget_exceeded')
    _require(len(rows) == count)
    samples = []
    for row in rows:
        _require(type(row) is list and len(row) == 2)
        samples.append([_number(row[0], -1000, 1000), _number(row[1], -1000, 1000)])
    snapshot = dict(schema_version=1, kind=value['kind'], grid=dict(grid),
                    sample_unit=value['sample_unit'], samples=samples, verification=dict(flags),
                    execution_authorized=False, rerun_authorized=False)
    return snapshot, _body(snapshot, _MAX_BODY)


def _request(value):
    _record(value, ('schema_version', 'timebase', 'aperture', 'reference_planes', 'path_loss_db'))
    _fixed(value['schema_version'], 1)
    timebase = value['timebase']
    _record(timebase, ('id', 'origin_tick', 'tick_seconds'))
    _require(type(timebase['id']) is str and _ID.fullmatch(timebase['id']) is not None)
    origin = _integer(timebase['origin_tick'], 0, 2**63 - 1, budget=True)
    ratio = timebase['tick_seconds']
    _record(ratio, ('numerator', 'denominator'))
    numerator = _integer(ratio['numerator'], 1, 1000000000, budget=True)
    denominator = _integer(ratio['denominator'], 1, 1000000000, budget=True)
    _require(math.gcd(numerator, denominator) == 1)
    aperture = value['aperture']
    _record(aperture, ('start_tick', 'stop_tick', 'kernel'))
    start = _integer(aperture['start_tick'], 0, 2**63 - 1, budget=True)
    stop = _integer(aperture['stop_tick'], 0, 2**63 - 1, budget=True)
    _fixed(aperture['kernel'], 'boxcar')
    _require(origin <= start < stop)
    planes = value['reference_planes']
    _record(planes, ('input', 'output'))
    _fixed(planes['input'], 'declared_dut_output')
    _fixed(planes['output'], 'declared_sensor_input')
    loss = _number(value['path_loss_db'], 0, 120)
    snapshot = dict(schema_version=1,
                    timebase=dict(id=timebase['id'], origin_tick=origin, tick_seconds=dict(ratio)),
                    aperture=dict(aperture), reference_planes=dict(planes), path_loss_db=loss)
    return snapshot, _body(snapshot, 4096)


def _bounded(integer):
    _require(integer.bit_length() <= _MAX_BITS, 'budget_exceeded')
    return integer


def _fraction(numerator, denominator=1):
    return Fraction(_bounded(numerator), _bounded(denominator))


def _add(left, right):
    a = _bounded(left.numerator * right.denominator)
    b = _bounded(right.numerator * left.denominator)
    return _fraction(_bounded(a + b), _bounded(left.denominator * right.denominator))


def _multiply(left, right):
    return _fraction(_bounded(left.numerator * right.numerator),
                     _bounded(left.denominator * right.denominator))


def _divide(left, right):
    return _multiply(left, _fraction(right.denominator, right.numerator))


def _as_float(value):
    _require(value >= 0, 'numeric_unavailable')
    if value == 0:
        return 0.0
    _require(value >= _MIN_EXACT, 'numeric_unavailable')
    try:
        result = float(value)
    except OverflowError:
        _fail('numeric_unavailable')
    _require(math.isfinite(result) and result >= _MIN_NORMAL, 'numeric_unavailable')
    return result


def _ratio(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


def _window(packet, request):
    clock = request['timebase']
    step = _fraction(clock['tick_seconds']['numerator'], clock['tick_seconds']['denominator'])
    aperture = request['aperture']
    start = _multiply(_fraction(aperture['start_tick'] - clock['origin_tick']), step)
    stop = _multiply(_fraction(aperture['stop_tick'] - clock['origin_tick']), step)
    fs, count = packet['grid']['sample_rate_hz'], packet['grid']['sample_count']
    _require(0 <= start < stop <= _fraction(count, fs))
    duration = _add(stop, -start)
    overlaps = []
    for index in range(count):
        left = max(start, _fraction(index, fs))
        right = min(stop, _fraction(index + 1, fs))
        if right > left:
            overlaps.append((index, _add(right, -left)))
    return start, stop, duration, overlaps


def _powers(samples, loss):
    try:
        gain = 10.0 ** (-float(loss) / 10.0)
    except OverflowError:
        _fail('numeric_unavailable')
    _require(math.isfinite(gain) and gain > 0, 'numeric_unavailable')
    source, sensor = [], []
    for i, q in samples:
        power = float(i) * float(i) + float(q) * float(q)
        _require(power <= 1000000)
        _require(math.isfinite(power) and power >= 0, 'numeric_unavailable')
        _require(power != 0 or (i == 0 and q == 0), 'numeric_unavailable')
        _require(power == 0 or power >= _MIN_NORMAL, 'numeric_unavailable')
        attenuated = power * gain
        _require(math.isfinite(attenuated), 'numeric_unavailable')
        _require(power == 0 or attenuated >= _MIN_NORMAL, 'numeric_unavailable')
        source.append(_fraction(*power.as_integer_ratio()))
        sensor.append(_fraction(*attenuated.as_integer_ratio()))
    return source, sensor


def _dbm(power):
    if power is None or power == 0:
        return None
    result = 10 * math.log10(power)
    _require(math.isfinite(result), 'numeric_unavailable')
    return result


def _metrics(powers, overlaps, duration, on_duration):
    energy, peak = _fraction(0), _fraction(0)
    for index, weight in overlaps:
        energy = _add(energy, _multiply(powers[index], weight))
        peak = max(peak, powers[index])
    values = dict(time_mean_mw=_as_float(_divide(energy, duration)),
                  on_mean_mw=_as_float(_divide(energy, on_duration)) if on_duration else None,
                  peak_mw=_as_float(peak), energy_mw_s=_as_float(energy))
    for stem in ('time_mean', 'on_mean', 'peak'):
        values[stem + '_dbm'] = _dbm(values[stem + '_mw'])
    return values


def project_declared_rf_aperture(packet, request) -> dict:
    """Project a caller-declared window only; never verify live acquisition.

    Validation order: packet, request, exact coverage, all-row numeric checks,
    source then sensor aggregates, and detached result/body budget.
    Unexpected BaseException objects propagate without cleanup or retries.
    """
    source_packet, packet_body = _packet(packet)
    declaration, request_body = _request(request)
    start, stop, duration, overlaps = _window(source_packet, declaration)
    source, sensor = _powers(source_packet['samples'], declaration['path_loss_db'])
    on_duration = _fraction(0)
    for index, weight in overlaps:
        if source[index] > 0:
            on_duration = _add(on_duration, weight)
    source_metrics = _metrics(source, overlaps, duration, on_duration)
    sensor_metrics = _metrics(sensor, overlaps, duration, on_duration)
    _as_float(duration)
    _as_float(on_duration)
    duty = _as_float(_divide(on_duration, duration))
    result = dict(
        schema_version=1, kind='declared_rf_aperture_projection',
        binding=dict(packet_sha256=hashlib.sha256(packet_body).hexdigest(),
                     request_sha256=hashlib.sha256(request_body).hexdigest(),
                     source_grid=dict(source_packet['grid']), request=declaration),
        interval=dict(start_seconds=_ratio(start), stop_seconds=_ratio(stop),
                      duration_seconds=_ratio(duration), on_duration_seconds=_ratio(on_duration),
                      observed_duty_cycle=duty,
                      overlaps=[dict(sample_index=index, seconds=_ratio(weight))
                                for index, weight in overlaps]),
        metrics=dict(source=source_metrics, sensor_input=sensor_metrics),
        verification=dict(_OUTPUT_FLAGS), execution_authorized=False, rerun_authorized=False)
    _body(result, _MAX_BODY)
    return result
