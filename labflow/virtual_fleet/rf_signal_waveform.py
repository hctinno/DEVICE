"""Bounded normalized I/Q envelopes; no RF runner or hardware."""
import hashlib
import json
import math


_PREFIX = 'rf_signal_waveform_'
_CODES = frozenset(_PREFIX + suffix for suffix in ('invalid_argument', 'budget_exceeded', 'numeric_unavailable'))
_REQUEST = frozenset('schema_version signal_kind sample_rate_hz sample_count on_power_dbm pulse'.split())
_PULSE = frozenset('period_samples on_samples start_sample_in_period'.split())
_PACKET = frozenset('schema_version kind grid sample_unit samples verification execution_authorized rerun_authorized'.split())
_GRID = frozenset('sample_rate_hz sample_count t0_seconds interpolation'.split())
_FLAGS = dict(data_origin='authored_synthetic', synthetic=True, hardware_verified=False,
              physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
              method_approval='not_assessed', regulatory_scope_complete=False,
              model_scope='normalized_baseband_sample_math_v1')
_MIN_NORMAL = float.fromhex('0x1p-1022')


class RfSignalWaveformError(ValueError):
    """A fixed full code, never caller data or supplier exception text."""
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + 'invalid_argument'
        super().__init__(self.code)


def _fail(suffix):
    raise RfSignalWaveformError(_PREFIX + suffix) from None


def _record(value, fields, constants=None):
    if (type(value) is not dict or len(value) != len(fields) or any(type(key) is not str for key in value)
            or set(value) != fields):
        _fail('invalid_argument')
    for key, expected in (constants or {}).items():
        if type(value[key]) is not type(expected) or value[key] != expected:
            _fail('invalid_argument')


def _integer(value, low, high, *, budget=False):
    if type(value) is not int or value < low:
        _fail('invalid_argument')
    if value > high:
        _fail('budget_exceeded' if budget else 'invalid_argument')
    return value


def _number(value, low, high):
    if type(value) not in (int, float) or not low <= value <= high:
        _fail('invalid_argument')
    return value


def _numeric(value, *, positive=False):
    if (not math.isfinite(value) or value < 0 or (positive and value == 0)
            or 0 < value < _MIN_NORMAL):
        _fail('numeric_unavailable')
    return value


def _bytes(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > 1_048_576:
        _fail('budget_exceeded')
    return raw


def _grid(fs, count):
    return dict(sample_rate_hz=fs, sample_count=count, t0_seconds=0, interpolation='zero_order_hold')


def generate_rf_baseband_envelope(spec, *, seed) -> dict:
    """Generate only constant-phase CW or rectangular sample-and-hold pulses."""
    try:
        _record(spec, _REQUEST, {'schema_version': 1})
        kind = spec['signal_kind']
        if type(kind) is not str or kind not in ('cw', 'rectangular_pulse'):
            _fail('invalid_argument')
        fs = _integer(spec['sample_rate_hz'], 1, 1_000_000_000)
        count = _integer(spec['sample_count'], 1, 4096, budget=True)
        power = _number(spec['on_power_dbm'], -120, 60)
        _integer(seed, 0, 2_147_483_647)
        period, on, start = 1, 1, 0
        if kind == 'cw':
            if spec['pulse'] is not None:
                _fail('invalid_argument')
        else:
            pulse = spec['pulse']
            _record(pulse, _PULSE)
            period = _integer(pulse['period_samples'], 1, 4096, budget=True)
            on = _integer(pulse['on_samples'], 1, period)
            start = _integer(pulse['start_sample_in_period'], 0, period - 1)
        amplitude = math.sqrt(_numeric(10 ** (power / 10), positive=True))
        _numeric(amplitude * amplitude, positive=True)
        i, q = ((amplitude, 0.0), (0.0, amplitude), (-amplitude, 0.0), (0.0, -amplitude))[seed % 4]
        samples = [[i, q] if (n + start) % period < on else [0.0, 0.0] for n in range(count)]
        result = dict(schema_version=1, kind='synthetic_rf_baseband_envelope', grid=_grid(fs, count),
                      sample_unit='sqrt_mW', samples=samples, verification=dict(_FLAGS),
                      execution_authorized=False, rerun_authorized=False)
        _bytes(result)
        return result
    except RfSignalWaveformError:
        raise
    except Exception:
        _fail('numeric_unavailable')


def analyze_rf_baseband_envelope(packet) -> dict:
    """Analyze copied public I/Q only, without generating or judging a waveform."""
    try:
        _record(packet, _PACKET, dict(schema_version=1, kind='synthetic_rf_baseband_envelope',
                                     sample_unit='sqrt_mW', execution_authorized=False, rerun_authorized=False))
        grid = packet['grid']
        _record(grid, _GRID, dict(t0_seconds=0, interpolation='zero_order_hold'))
        fs = _integer(grid['sample_rate_hz'], 1, 1_000_000_000)
        count = _integer(grid['sample_count'], 1, 4096, budget=True)
        _record(packet['verification'], set(_FLAGS), _FLAGS)
        rows = packet['samples']
        if type(rows) is not list:
            _fail('invalid_argument')
        if len(rows) > 4096:
            _fail('budget_exceeded')
        if len(rows) != count:
            _fail('invalid_argument')
        samples = []
        for row in rows:
            if type(row) is not list or len(row) != 2:
                _fail('invalid_argument')
            samples.append([_number(row[0], -1000, 1000), _number(row[1], -1000, 1000)])
        snapshot = dict(schema_version=1, kind='synthetic_rf_baseband_envelope', grid=_grid(fs, count),
                        sample_unit='sqrt_mW', samples=samples, verification=dict(_FLAGS),
                        execution_authorized=False, rerun_authorized=False)
        raw = _bytes(snapshot)
        powers = []
        for i, q in samples:
            power = float(i) * float(i) + float(q) * float(q)
            if power > 1_000_000:
                _fail('invalid_argument')
            powers.append(_numeric(power, positive=i != 0 or q != 0))
        on = sum(value > 0 for value in powers)
        present = on > 0
        total = _numeric(math.fsum(powers), positive=present)
        time_mean = _numeric(total / count, positive=present)
        on_mean = _numeric(total / on, positive=True) if present else None
        peak = _numeric(max(powers), positive=present)
        energy = _numeric(total / fs, positive=present)
        metrics = dict(window_seconds=_numeric(count / fs, positive=True), observed_on_samples=on,
                       observed_duty_cycle=_numeric(on / count, positive=present),
                       time_mean_mw=time_mean, on_mean_mw=on_mean, peak_mw=peak, energy_mw_s=energy,
                       time_mean_dbm=_dbm(time_mean), on_mean_dbm=_dbm(on_mean), peak_dbm=_dbm(peak))
        result = dict(schema_version=1, kind='synthetic_rf_baseband_analysis', grid=_grid(fs, count),
                      input_sha256=hashlib.sha256(raw).hexdigest(), metrics=metrics,
                      verification=dict(_FLAGS), execution_authorized=False, rerun_authorized=False)
        _bytes(result)
        return result
    except RfSignalWaveformError:
        raise
    except Exception:
        _fail('numeric_unavailable')


def _dbm(power):
    if power is None or power == 0:
        return None
    value = 10 * math.log10(power)
    if not math.isfinite(value):
        _fail('numeric_unavailable')
    return value
