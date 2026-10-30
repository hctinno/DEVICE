"""Stateful synthetic instrument roles. No transport, SDK, hardware or SCPI.

Numbers derive from input signals and declared virtual policies. Model names
are metadata, never evidence of installed firmware, options or RF accuracy.
"""
import bisect
import copy
import hashlib
import json
import math
import random


_KINDS = {'number': (int, float), 'integer': (int,), 'boolean': (bool,),
          'string': (str,), 'object': (dict,), 'array': (list,)}
_MEASUREMENT = {'power_meter', 'signal_analyzer', 'emi_receiver', 'communication_tester',
                'bluetooth_tester', 'wireless_ap', 'dfs_system', 'network_test_station',
                'test_software', 'network_analyzer'}
_TRANSMIT = {'signal_generator', 'communication_tester', 'bluetooth_tester', 'wireless_ap', 'dfs_system'}
_CALIBRATION = {'power_meter', 'signal_analyzer', 'emi_receiver', 'network_analyzer'}


def _ports(inputs, outputs):
    return {'inputs': dict(inputs), 'outputs': dict(outputs)}


ROLE_PORTS = {
    'power_meter': _ports([('sensor', 'measurement'), ('power', 'power')], [('measurement', 'measurement')]),
    'signal_analyzer': _ports([('rf', 'rf'), ('power', 'power')], [('measurement', 'measurement')]),
    'emi_receiver': _ports([('rf', 'rf'), ('power', 'power')], [('measurement', 'measurement')]),
    'signal_generator': _ports([('power', 'power')], [('rf', 'rf')]),
    'communication_tester': _ports([('rf', 'rf'), ('power', 'power')], [('rf', 'rf'), ('measurement', 'measurement'), ('data', 'data')]),
    'bluetooth_tester': _ports([('rf', 'rf'), ('power', 'power')], [('rf', 'rf'), ('measurement', 'measurement'), ('data', 'data')]),
    'wireless_ap': _ports([('rf', 'rf'), ('power', 'power')], [('rf', 'rf'), ('measurement', 'measurement'), ('data', 'data')]),
    'dfs_system': _ports([('rf', 'rf'), ('power', 'power')], [('rf', 'rf'), ('measurement', 'measurement')]),
    'network_test_station': _ports([('rf', 'rf'), ('data', 'data'), ('power', 'power')], [('measurement', 'measurement'), ('data', 'data')]),
    'test_software': _ports([('measurement', 'measurement'), ('data', 'data')], [('control', 'control'), ('data', 'data')]),
    'network_analyzer': _ports([('reference', 'rf'), ('test', 'rf'), ('path', 'data'), ('power', 'power')], [('measurement', 'measurement')]),
}


def _parameter(kind, unit='', required=False):
    return {'type': kind, 'required': required, 'unit': unit}


_FIELDS = {
    'frequency_hz': _parameter('number', 'Hz'), 'bandwidth_hz': _parameter('number', 'Hz'),
    'rbw_hz': _parameter('number', 'Hz'), 'normalization_hz': _parameter('number', 'Hz'),
    'measurement': _parameter('string'), 'measurement_mode': _parameter('string'),
    'detector': _parameter('string'), 'unit': _parameter('string'), 'window': _parameter('integer'),
    'trigger_source': _parameter('string'), 'impedance_ohm': _parameter('number', 'ohm'),
    'antenna_factor_db_per_m': _parameter('number', 'dB/m'),
    'power_dbm': _parameter('number', 'dBm'), 'duty_cycle': _parameter('number', 'ratio'),
    'crest_factor_db': _parameter('number', 'dB'), 'modulation': _parameter('string'),
    'offered_rate_mbps': _parameter('number', 'Mbit/s'), 'noise_figure_db': _parameter('number', 'dB'),
    'minimum_snr_db': _parameter('number', 'dB'), 'ssid': _parameter('string'),
    'detection_threshold_dbm': _parameter('number', 'dBm'), 'pulse_width_s': _parameter('number', 's'),
    'pulse_repetition_hz': _parameter('number', 'Hz'),
    'start_hz': _parameter('number', 'Hz'), 'stop_hz': _parameter('number', 'Hz'), 'points': _parameter('integer'),
    'criteria': _parameter('array'),
}
_DEFAULTS = {'frequency_hz': None, 'bandwidth_hz': 20e6, 'rbw_hz': 100e3,
             'normalization_hz': 1.0, 'measurement': 'power', 'measurement_mode': 'on_average',
             'detector': 'rms', 'unit': 'dBm', 'window': 1, 'trigger_source': 'immediate',
             'impedance_ohm': 50.0, 'antenna_factor_db_per_m': None,
             'power_dbm': 0.0, 'duty_cycle': 1.0, 'crest_factor_db': 0.0, 'modulation': 'CW',
             'offered_rate_mbps': 54.0, 'noise_figure_db': 6.0, 'minimum_snr_db': 3.0,
             'ssid': 'synthetic-ap', 'detection_threshold_dbm': -60.0,
             'pulse_width_s': 1e-6, 'pulse_repetition_hz': 1000.0,
             'start_hz': None, 'stop_hz': None, 'points': 101, 'criteria': []}
_CONFIG = {
    'power_meter': ['frequency_hz', 'measurement_mode', 'unit', 'window', 'trigger_source'],
    'signal_analyzer': ['frequency_hz', 'bandwidth_hz', 'rbw_hz', 'normalization_hz', 'measurement', 'measurement_mode', 'detector'],
    'emi_receiver': ['frequency_hz', 'bandwidth_hz', 'rbw_hz', 'measurement', 'measurement_mode', 'detector', 'impedance_ohm', 'antenna_factor_db_per_m'],
    'signal_generator': ['frequency_hz', 'bandwidth_hz', 'power_dbm', 'duty_cycle', 'crest_factor_db', 'modulation'],
    'communication_tester': ['frequency_hz', 'bandwidth_hz', 'power_dbm', 'duty_cycle', 'crest_factor_db', 'modulation', 'offered_rate_mbps', 'noise_figure_db', 'minimum_snr_db'],
    'bluetooth_tester': ['frequency_hz', 'bandwidth_hz', 'power_dbm', 'duty_cycle', 'crest_factor_db', 'modulation', 'offered_rate_mbps', 'noise_figure_db', 'minimum_snr_db'],
    'wireless_ap': ['frequency_hz', 'bandwidth_hz', 'power_dbm', 'duty_cycle', 'crest_factor_db', 'modulation', 'offered_rate_mbps', 'noise_figure_db', 'minimum_snr_db', 'ssid'],
    'dfs_system': ['frequency_hz', 'bandwidth_hz', 'power_dbm', 'detection_threshold_dbm', 'pulse_width_s', 'pulse_repetition_hz'],
    'network_test_station': ['frequency_hz', 'bandwidth_hz', 'offered_rate_mbps', 'noise_figure_db', 'minimum_snr_db'],
    'test_software': ['criteria'],
    'network_analyzer': ['start_hz', 'stop_hz', 'points'],
}


def _actions(role):
    actions = {'configure': {'parameters': {k: copy.deepcopy(_FIELDS[k]) for k in _CONFIG[role]},
                             'completion': 'validated settings; invalidates earlier acquisitions'},
               'reset': {'parameters': {}, 'completion': 'idle; error FIFO preserved'},
               'recover': {'parameters': {}, 'completion': 'idle after observed communication/power error clears'},
               'read_error': {'parameters': {}, 'completion': 'remove one observed error from FIFO'},
               'abort': {'parameters': {}, 'completion': 'cancel pending operation and invalidate result'}}
    if role in _MEASUREMENT:
        actions.update(acquire={'parameters': {}, 'completion': 'pending until explicit virtual ticks finish'},
                       fetch={'parameters': {}, 'completion': 'cached current-revision result; no implicit acquisition'})
    if role in _TRANSMIT:
        actions.update(start_tx={'parameters': {}, 'completion': 'emit declared synthetic RF when powered'},
                       stop_tx={'parameters': {}, 'completion': 'remove RF output'})
    if role in _CALIBRATION:
        actions['calibrate'] = {'parameters': {'standard_loss_db': _parameter('number', 'dB')}
                                if role == 'network_analyzer' else {},
                                'completion': 'pending; completion and calibration validity are distinct'}
        if role != 'network_analyzer':
            actions['verify_calibration'] = {'parameters': {'reference_dbm': _parameter('number', 'dBm', True),
                                                           'tolerance_db': _parameter('number', 'dB', True)},
                                              'completion': 'compare a known synthetic reference, not an OPC flag'}
    if role == 'power_meter':
        actions['trigger'] = {'parameters': {}, 'completion': 'start an armed BUS acquisition'}
        actions['fetch']['parameters'] = {'window': _parameter('integer')}
        actions['set_display_unit'] = {
            'parameters': {'unit': _parameter('string', required=True)},
            'completion': 'dBm/W presentation only; preserves acquisition and setup revision'}
    if role == 'test_software':
        actions['run'] = copy.deepcopy(actions['acquire'])
    return actions


ROLE_ACTIONS = {role: _actions(role) for role in ROLE_PORTS}


class _InputError(ValueError):
    pass


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _number(value, *, positive=False):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise _InputError('nonfinite_or_non_numeric')
    if positive and value <= 0:
        raise _InputError('nonpositive_quantity')
    return float(value)


def _identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > 200:
        raise _InputError('source_identity_missing')
    return value


def _interpolate(points, frequency):
    if frequency < points[0][0] or frequency > points[-1][0]:
        raise _InputError('path_frequency_not_covered')
    index = bisect.bisect_left([p[0] for p in points], frequency)
    if index < len(points) and points[index][0] == frequency:
        return points[index][1]
    first, last = points[index-1], points[index]
    return first[1] + (last[1] - first[1]) * (frequency - first[0]) / (last[0] - first[0])


def _power_in_unit(power_dbm, unit):
    if unit == 'dBm':
        return power_dbm
    # Apply the W scale in the exponent: a finite final value must not overflow
    # merely because the intermediate mW value exceeds the float range.
    try:
        value = 10.0**((power_dbm - (30 if unit == 'W' else 0))/10)
    except OverflowError:
        raise _InputError('display_value_overflow') from None
    if not math.isfinite(value):
        raise _InputError('display_value_overflow')
    if value == 0:
        raise _InputError('display_value_underflow')
    return value


class _Instrument:
    def __init__(self, profile, seed):
        if not isinstance(profile, dict) or profile.get('role') not in ROLE_PORTS:
            raise ValueError('Unsupported role profile')
        _json(profile)
        if type(seed) is not int:
            raise ValueError('seed must be an integer')
        self.profile = copy.deepcopy(profile)
        self.role = profile['role']
        self.profile_id = _identifier(profile.get('profile_id'))
        self._policy = copy.deepcopy(profile.get('simulation_parameters', {}))
        if not isinstance(self._policy, dict):
            raise ValueError('simulation_parameters must be an object')
        allowed = {'measurement_ticks', 'operation_timeout_ticks', 'noise_db', 'frequency_min_hz',
                   'frequency_max_hz', 'maximum_input_dbm', 'power_required', 'calibration_valid'}
        if self.role == 'power_meter':
            allowed.add('accepted_sensor_ids')
        if self.role == 'dfs_system':
            allowed.add('function')
        if set(self._policy) - allowed:
            raise ValueError('Unsupported synthetic instrument policy')
        for name in ('calibration_valid', 'power_required'):
            if name in self._policy and type(self._policy[name]) is not bool:
                raise ValueError('Boolean simulation policy required')
        if 'accepted_sensor_ids' in self._policy:
            identities = self._policy['accepted_sensor_ids']
            if not isinstance(identities, list) or len(identities) > 1000:
                raise ValueError('Invalid accepted sensor identities')
            for identity in identities:
                _identifier(identity)
        function = self._policy.get('function', 'combined')
        if self.role == 'dfs_system' and (not isinstance(function, str) or function not in {'analyzer', 'generator', 'combined'}):
            raise ValueError('Unsupported synthetic DFS function')
        self._latency = self._policy.get('measurement_ticks', 2)
        self._timeout = self._policy.get('operation_timeout_ticks', 100)
        if (type(self._latency) is not int or type(self._timeout) is not int
                or not 1 <= self._latency <= self._timeout <= 1000000):
            raise ValueError('Invalid virtual timing policy')
        self._noise = _number(self._policy.get('noise_db', 0))
        if not 0 <= self._noise <= 100:
            raise ValueError('Invalid noise policy')
        self._minimum_hz = _number(self._policy.get('frequency_min_hz', 1), positive=True)
        self._maximum_hz = _number(self._policy.get('frequency_max_hz', 100e9), positive=True)
        if self._maximum_hz <= self._minimum_hz:
            raise ValueError('Invalid frequency range')
        self._max_power = _number(self._policy.get('maximum_input_dbm', 30))
        self._rng = random.Random(seed ^ int(hashlib.sha256(self.profile_id.encode()).hexdigest()[:16], 16))
        self._faults = {'disconnected': False, 'stuck': False, 'invalid_calibration': False,
                        'sensor_mismatch': False, 'drop_output': False, 'gain_error_db': 0.0}
        self._errors = []
        self._windows = {}
        self._tick = 0
        self._configuration_revision = 0
        self._configured = False
        self._inputs = {}
        self._calibration_valid = bool(self._policy.get('calibration_valid', self.role != 'network_analyzer'))
        self._calibration_state = 'valid' if self._calibration_valid else 'verification_required'
        self._cfg = self._defaults()
        self._state, self._reason = 'idle', None
        self._pending, self._result = None, None
        self._result_signature = None
        self._transmitting = False

    def _defaults(self):
        result = {key: copy.deepcopy(_DEFAULTS[key]) for key in _CONFIG[self.role]}
        if self.role == 'emi_receiver':
            result['measurement'] = 'voltage'
        return result

    def _context(self, tick, revision, inputs=None):
        if type(tick) is not int or type(revision) is not int or tick < self._tick or revision < 0:
            raise ValueError('Invalid or reversed virtual clock/revision')
        if inputs is not None:
            if not isinstance(inputs, dict):
                raise _InputError('invalid_input_ports')
            try:
                _json(inputs)
            except (TypeError, ValueError):
                raise _InputError('invalid_input_json') from None
            self._inputs = copy.deepcopy(inputs)
        self._tick = tick

    def _queue(self, reason):
        if len(self._errors) >= 30:
            self._errors[-1] = 'error_queue_overflow'
        else:
            self._errors.append(reason)

    def _invalidate(self, reason, state='invalid'):
        if self._pending is not None and self._pending['calibrating']:
            self._calibration_valid, self._calibration_state = False, 'verification_required'
        self._state, self._reason = state, reason
        self._pending, self._result = None, None
        self._result_signature = None

    def _power(self):
        if self._faults['disconnected']:
            raise _InputError('communication_unavailable')
        if self.role == 'test_software' or self._policy.get('power_required', True) is False:
            return
        power = self._inputs.get('power')
        if not isinstance(power, dict) or power.get('valid') is not True or power.get('enabled') is not True:
            raise _InputError('power_unavailable')
        _number(power.get('voltage_v'), positive=True)

    def _frequency(self, frequency):
        value = _number(frequency, positive=True)
        if not self._minimum_hz <= value <= self._maximum_hz:
            raise _InputError('frequency_out_of_scope')
        return value

    def _rf(self, port='rf', *, require_center=True):
        signal = self._inputs.get(port)
        if not isinstance(signal, dict) or signal.get('valid', True) is not True or signal.get('status', 'ok') != 'ok':
            raise _InputError('rf_unavailable')
        frequency = self._frequency(signal.get('frequency_hz'))
        power = _number(signal.get('power_dbm'))
        bandwidth = _number(signal.get('bandwidth_hz'), positive=True)
        duty = _number(signal.get('duty_cycle'), positive=True)
        if duty > 1 or power > self._max_power or power < -300:
            raise _InputError('rf_overload_or_invalid_duty')
        modulation = _identifier(signal.get('modulation'))
        crest = signal.get('crest_factor_db')
        if crest is None and modulation.upper() == 'CW':
            crest = 0.0  # Explicit virtual missing-crest policy: CW only.
        if crest is not None:
            crest = _number(crest)
            if crest < 0 or crest > 100:
                raise _InputError('invalid_crest_factor')
        center = self._cfg.get('frequency_hz')
        if require_center and center is not None and abs(frequency - center) > self._cfg.get('bandwidth_hz', 1) / 2:
            raise _InputError('frequency_outside_capture')
        return {'frequency_hz': frequency, 'power_dbm': power, 'bandwidth_hz': bandwidth,
                'duty_cycle': duty, 'crest_factor_db': crest, 'modulation': modulation,
                'source_id': _identifier(signal.get('source_id')),
                **{k: signal[k] for k in ('pulse_width_s', 'pulse_repetition_hz') if k in signal}}

    def _sensor(self, revision):
        signal = self._inputs.get('sensor')
        if (not isinstance(signal, dict) or signal.get('status') != 'ok' or signal.get('valid') is not True
                or signal.get('unit') != 'dBm' or self._faults['sensor_mismatch']):
            raise _InputError('sensor_invalid_or_incompatible')
        value, power = _number(signal.get('value')), _number(signal.get('power_dbm'))
        if value != power or power < -300 or power > self._max_power:
            raise _InputError('sensor_quantity_conflict')
        if (type(signal.get('acquisition_tick')) is not int or not 0 <= signal['acquisition_tick'] <= self._tick
                or type(signal.get('acquisition_setup_revision')) is not int
                or signal['acquisition_setup_revision'] != revision):
            raise _InputError('sensor_acquisition_stale')
        identity = _identifier(signal.get('source_id'))
        accepted = self._policy.get('accepted_sensor_ids')
        if accepted is not None and identity not in accepted:
            raise _InputError('sensor_invalid_or_incompatible')
        duty = _number(signal.get('duty_cycle'), positive=True)
        if duty > 1:
            raise _InputError('invalid_duty_cycle')
        crest = signal.get('crest_factor_db')
        if crest is not None:
            crest = _number(crest)
            if not 0 <= crest <= 100:
                raise _InputError('invalid_crest_factor')
        return {'frequency_hz': self._frequency(signal.get('frequency_hz')), 'power_dbm': power,
                'duty_cycle': duty, 'crest_factor_db': crest, 'source_id': identity}

    def _mode_power(self, signal):
        mode = self._cfg.get('measurement_mode', 'on_average')
        power = signal['power_dbm']
        if mode == 'time_average':
            power += 10 * math.log10(signal['duty_cycle'])
        elif mode == 'peak':
            if signal.get('crest_factor_db') is None:
                raise _InputError('peak_quantity_missing')
            power += signal['crest_factor_db']
        if power > self._max_power:
            raise _InputError('input_overload')
        return power

    def _validate_settings(self, config):
        if len(_json(config).encode('utf-8')) > 32768:
            raise _InputError('configuration_byte_limit')
        for key in ('modulation', 'ssid'):
            if key in config:
                _identifier(config[key])
        for key in ['frequency_hz', 'start_hz', 'stop_hz']:
            if config.get(key) is not None:
                self._frequency(config[key])
        for key in ['bandwidth_hz', 'rbw_hz', 'normalization_hz', 'impedance_ohm', 'offered_rate_mbps', 'pulse_width_s', 'pulse_repetition_hz']:
            if key in config:
                _number(config[key], positive=True)
        for key in ['power_dbm', 'noise_figure_db', 'minimum_snr_db', 'detection_threshold_dbm']:
            if key in config:
                _number(config[key])
        if 'duty_cycle' in config and not 0 < config['duty_cycle'] <= 1:
            raise _InputError('invalid_duty_cycle')
        if config.get('measurement_mode', 'on_average') not in {'on_average', 'time_average', 'peak'}:
            raise _InputError('unsupported_measurement_mode')
        if config.get('detector', 'rms') not in {'rms', 'peak', 'quasi_peak'}:
            raise _InputError('unsupported_detector')
        measurements = {'power', 'psd', 'voltage'}
        if self.role == 'emi_receiver':
            measurements.add('field_strength')
        if config.get('measurement', 'power') not in measurements:
            raise _InputError('unsupported_measurement')
        if config.get('unit', 'dBm') not in {'dBm', 'W', 'mW'}:
            raise _InputError('unsupported_unit')
        if config.get('window', 1) not in {1, 2, 3, 4}:
            raise _InputError('measurement_window_out_of_scope')
        if config.get('trigger_source', 'immediate') not in {'immediate', 'bus'}:
            raise _InputError('unsupported_trigger_source')
        if 'crest_factor_db' in config and (config['crest_factor_db'] < 0 or config['crest_factor_db'] > 100):
            raise _InputError('invalid_crest_factor')
        if 'antenna_factor_db_per_m' in config and config['antenna_factor_db_per_m'] is not None:
            _number(config['antenna_factor_db_per_m'])
        if 'pulse_width_s' in config and config['pulse_width_s'] * config['pulse_repetition_hz'] > 1:
            raise _InputError('pulse_duty_out_of_range')
        if 'points' in config:
            if type(config['points']) is not int or not 1 <= config['points'] <= 2048:
                raise _InputError('sweep_point_limit')
            if config['start_hz'] is not None and config['stop_hz'] is not None:
                if config['stop_hz'] < config['start_hz'] or (config['points'] > 1 and config['stop_hz'] == config['start_hz']):
                    raise _InputError('invalid_sweep_range')
        if 'criteria' in config:
            if not isinstance(config['criteria'], list) or len(config['criteria']) > 128:
                raise _InputError('invalid_criteria')
            seen = set()
            for rule in config['criteria']:
                if (not isinstance(rule, dict) or set(rule) - {'id', 'unit', 'quantity', 'operator', 'limit'}
                        or not {'id', 'unit', 'operator', 'limit'} <= set(rule)):
                    raise _InputError('invalid_criterion')
                if (_identifier(rule['id']) in seen or not isinstance(rule['operator'], str)
                        or rule['operator'] not in {'<=', '<', '>=', '>', '=='}):
                    raise _InputError('invalid_criterion')
                seen.add(rule['id'])
                _identifier(rule['unit'])
                if 'quantity' in rule:
                    _identifier(rule['quantity'])
                _number(rule['limit'])

    def _parameters(self, action, parameters):
        schema = ROLE_ACTIONS[self.role][action]['parameters']
        if not isinstance(parameters, dict) or set(parameters) - set(schema):
            raise _InputError('unsupported_parameters')
        for name, spec in schema.items():
            if name not in parameters:
                if spec['required']:
                    raise _InputError('missing_parameter')
                continue
            value = parameters[name]
            kind = spec['type']
            if not isinstance(value, _KINDS[kind]) or (kind in {'number', 'integer'} and isinstance(value, bool)):
                raise _InputError('invalid_parameter_type')
            if kind == 'number':
                _number(value)
        try:
            _json(parameters)
        except (TypeError, ValueError):
            raise _InputError('invalid_parameter_json') from None

    def _software_inputs(self, revision):
        rules = self._cfg['criteria']
        if not rules:
            raise _InputError('criteria_missing')
        data = self._inputs.get('data', {})
        batch = data.get('measurements', {}) if isinstance(data, dict) and data.get('valid') is True else {}
        if not isinstance(batch, dict):
            raise _InputError('invalid_measurement_batch')
        if len(rules) == 1 and 'measurement' in self._inputs:
            batch = {rules[0]['id']: self._inputs['measurement']}
        selected = {}
        for rule in rules:
            item = batch.get(rule['id'])
            if (not isinstance(item, dict) or item.get('valid') is not True or item.get('status') != 'ok'
                    or item.get('unit') != rule['unit'] or (rule.get('quantity') and item.get('quantity') != rule['quantity'])):
                raise _InputError('measurement_missing_or_unit_conflict')
            if (type(item.get('acquisition_setup_revision')) is not int or item['acquisition_setup_revision'] != revision
                    or type(item.get('acquisition_tick')) is not int
                    or not 0 <= item['acquisition_tick'] <= self._tick):
                raise _InputError('measurement_stale')
            selected[rule['id']] = {'value': _number(item.get('value')), 'unit': item['unit'],
                                    'quantity': item.get('quantity'), 'source_id': _identifier(item.get('source_id')),
                                    'acquisition_tick': item['acquisition_tick'],
                                    'acquisition_setup_revision': item['acquisition_setup_revision']}
        return selected

    def _vna_inputs(self, calibrating=False):
        start, stop, points = (self._cfg[key] for key in ('start_hz', 'stop_hz', 'points'))
        if start is None or stop is None:
            raise _InputError('sweep_not_configured')
        frequencies = [start] if points == 1 else [start + (stop-start) * i/(points-1) for i in range(points)]
        path = self._inputs.get('path')
        if 'path' in self._inputs and (not isinstance(path, dict) or path.get('valid') is not True):
            raise _InputError('path_unavailable')
        if isinstance(path, dict) and path.get('valid') is True:
            curve = path.get('frequency_loss_db')
            if not isinstance(curve, list) or not 1 <= len(curve) <= 4096:
                raise _InputError('path_curve_missing')
            parsed = []
            for pair in curve:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise _InputError('invalid_path_curve')
                parsed.append([self._frequency(pair[0]), _number(pair[1])])
            if any(b[0] <= a[0] for a, b in zip(parsed, parsed[1:])):
                raise _InputError('unordered_path_curve')
            if calibrating and path.get('calibration_standard') is not True:
                raise _InputError('known_calibration_standard_required')
            losses = [_interpolate(parsed, frequency) for frequency in frequencies]
            return {'frequencies_hz': frequencies, 'loss_db': losses,
                    'source_id': _identifier(path.get('source_id')), 'calibration_standard': calibrating}
        if points != 1 or calibrating:
            raise _InputError('sweep_path_not_provided')
        reference = self._rf('reference', require_center=False)
        test = self._rf('test', require_center=False)
        if abs(reference['frequency_hz'] - test['frequency_hz']) > 1 or abs(start-reference['frequency_hz']) > 1:
            raise _InputError('reference_test_frequency_conflict')
        return {'frequencies_hz': frequencies, 'loss_db': [reference['power_dbm'] - test['power_dbm']],
                'source_id': test['source_id'], 'reference_source_id': reference['source_id']}

    def _prepare(self, revision, *, calibrating=False):
        self._power()
        if calibrating and self.role != 'network_analyzer':
            return {'calibration_policy': 'synthetic_internal_routine'}
        if self.role in _CALIBRATION and not calibrating and (not self._calibration_valid or self._faults['invalid_calibration']):
            raise _InputError('calibration_not_valid')
        if self.role == 'power_meter':
            source = self._sensor(revision)
            if self._cfg['frequency_hz'] is not None and abs(source['frequency_hz'] - self._cfg['frequency_hz']) > 1:
                raise _InputError('sensor_frequency_setting_conflict')
            if not calibrating:
                self._mode_power(source)
            return source
        if self.role == 'network_analyzer':
            return self._vna_inputs(calibrating)
        if self.role == 'test_software':
            return self._software_inputs(revision)
        if self._cfg.get('frequency_hz') is None:
            raise _InputError('frequency_not_configured')
        source = self._rf()
        self._mode_power(source)
        if self.role in {'signal_analyzer', 'emi_receiver'} and self._cfg['detector'] in {'peak', 'quasi_peak'}:
            if source.get('crest_factor_db') is None:
                raise _InputError('peak_quantity_missing')
            if source['power_dbm'] + source['crest_factor_db'] > self._max_power:
                raise _InputError('input_overload')
        if self.role == 'emi_receiver' and self._cfg['measurement'] == 'field_strength' and self._cfg['antenna_factor_db_per_m'] is None:
            raise _InputError('antenna_factor_missing')
        if self.role == 'network_test_station':
            data = self._inputs.get('data')
            if not isinstance(data, dict) or data.get('valid') is not True:
                raise _InputError('traffic_data_missing')
            source['offered_rate_mbps'] = _number(data.get('offered_rate_mbps'), positive=True)
        if self.role == 'dfs_system' and source['modulation'].lower() == 'pulse':
            width = _number(source.get('pulse_width_s'), positive=True)
            repetition = _number(source.get('pulse_repetition_hz'), positive=True)
            if width * repetition > 1 or not math.isclose(source['duty_cycle'], width*repetition, rel_tol=1e-8):
                raise _InputError('pulse_metadata_conflict')
        return source

    def _measurement(self, source, revision, tick):
        base = {'status': 'ok', 'valid': True, 'source_id': self.profile_id,
                'input_source_id': source.get('source_id'), 'acquisition_tick': tick,
                'acquisition_setup_revision': revision, 'configuration_revision': self._configuration_revision,
                'simulation_basis': 'declared_synthetic_policy'}
        bias = self._faults['gain_error_db'] + self._rng.uniform(-self._noise, self._noise)
        if self.role == 'network_analyzer':
            loss = [v-bias for v in source['loss_db']]
            return {**base, 'unit': 'dB', 'quantity': 's21_magnitude', 'value': [-v for v in loss],
                    'frequencies_hz': source['frequencies_hz'], 's21_magnitude_db': [-v for v in loss],
                    'loss_db': loss, 'phase_supported': False}
        if self.role == 'test_software':
            results = []
            for rule in self._cfg['criteria']:
                value, limit = source[rule['id']]['value'], rule['limit']
                passed = {'<=': value <= limit, '<': value < limit, '>=': value >= limit,
                          '>': value > limit, '==': value == limit}[rule['operator']]
                results.append({'id': rule['id'], **source[rule['id']], 'operator': rule['operator'],
                                'limit': limit, 'passed': passed})
            return {**base, 'quantity': 'test_results', 'verdict': 'pass' if all(r['passed'] for r in results) else 'fail',
                    'results': results, 'criteria_count': len(results), 'authorized_for_issue': False}
        power = self._mode_power(source) + bias
        if self.role in {'communication_tester', 'bluetooth_tester', 'wireless_ap', 'network_test_station'}:
            noise_floor = -174 + 10*math.log10(source['bandwidth_hz']) + self._cfg['noise_figure_db']
            snr = power-noise_floor
            offered = source.get('offered_rate_mbps', self._cfg['offered_rate_mbps'])
            capacity = source['bandwidth_hz'] * math.log2(1 + 10**(min(snr, 100)/10)) / 1e6
            associated = snr >= self._cfg['minimum_snr_db']
            return {**base, 'unit': 'dBm', 'quantity': 'received_power', 'value': power,
                    'snr_db': snr, 'associated': associated,
                    'throughput_mbps': min(offered, capacity) if associated else 0.0,
                    'bit_error_ratio': min(0.5, 0.5*math.exp(-max(snr, 0)/4)),
                    'frequency_hz': source['frequency_hz'],
                    **({'ssid': self._cfg['ssid']} if self.role == 'wireless_ap' else {})}
        if self.role == 'dfs_system':
            detected = source['modulation'].lower() == 'pulse' and power >= self._cfg['detection_threshold_dbm']
            return {**base, 'unit': 'dBm', 'quantity': 'radar_received_power', 'value': power,
                    'detected': detected, 'frequency_hz': source['frequency_hz'],
                    'detection_policy': 'synthetic_pulse_and_threshold'}
        quantity, unit = self._cfg.get('measurement_mode', 'on_average'), self._cfg.get('unit', 'dBm')
        extras = {'frequency_hz': source['frequency_hz'], 'duty_cycle': source['duty_cycle'],
                  'crest_factor_db': source.get('crest_factor_db')}
        if self.role == 'power_meter':
            # Keep one canonical acquired value, including the one noise sample.
            # Display projection must never call _measurement again.
            _power_in_unit(power, unit)  # Fail through advance's structured error path.
            unit = 'dBm'
            extras['window'] = self._cfg['window']
        elif self.role in {'signal_analyzer', 'emi_receiver'}:
            detector = self._cfg['detector']
            if detector == 'peak':
                if source.get('crest_factor_db') is None:
                    raise _InputError('peak_quantity_missing')
                power = source['power_dbm'] + source['crest_factor_db'] + bias
                quantity = 'peak'
            elif detector == 'quasi_peak':
                average = source['power_dbm'] + 10*math.log10(source['duty_cycle'])
                peak = source['power_dbm'] + source['crest_factor_db']
                weight = 1-math.exp(-self._latency/2)
                power = average + (peak-average)*weight + bias
                quantity = 'synthetic_quasi_peak_envelope'
            measurement = self._cfg['measurement']
            if measurement == 'psd':
                density = power - 10*math.log10(source['bandwidth_hz'])
                extras.update(rbw_hz=self._cfg['rbw_hz'],
                              normalization_hz=self._cfg.get('normalization_hz', 1.0),
                              rbw_band_power_dbm=power+10*math.log10(min(self._cfg['rbw_hz'], source['bandwidth_hz'])/source['bandwidth_hz']),
                              normalized_band_power_dbm=density+10*math.log10(self._cfg.get('normalization_hz', 1.0)),
                              spectrum_policy='uniform_power_across_declared_bandwidth')
                power, unit, quantity = density, 'dBm/Hz', 'spectral_density'
            elif measurement in {'voltage', 'field_strength'}:
                power += 90 + 10*math.log10(self._cfg.get('impedance_ohm', 50))
                unit, quantity = 'dBuV', 'receiver_voltage'
                if measurement == 'field_strength':
                    power += self._cfg['antenna_factor_db_per_m']
                    unit, quantity = 'dBuV/m', 'field_strength'
            extras['detector'] = detector
        return {**base, 'value': power, 'unit': unit, 'quantity': quantity, **extras}

    def _display_measurement(self):
        result = copy.deepcopy(self._result)
        if self.role == 'power_meter':
            result['acquisition_value'] = result['value']
            result['acquisition_unit'] = result['unit']
            unit = self._cfg['unit']
            result.update(value=_power_in_unit(result['value'], unit), unit=unit)
        return result

    def _rf_output(self):
        self._power()
        frequency = self._cfg.get('frequency_hz')
        if frequency is None:
            raise _InputError('frequency_not_configured')
        power = _number(self._cfg.get('power_dbm', 0))
        if power > self._max_power or power < -300:
            raise _InputError('rf_output_out_of_scope')
        if self.role == 'dfs_system':
            width, repetition = self._cfg['pulse_width_s'], self._cfg['pulse_repetition_hz']
            return {'status': 'ok', 'valid': True, 'frequency_hz': frequency, 'power_dbm': power, 'bandwidth_hz': self._cfg['bandwidth_hz'],
                    'duty_cycle': width*repetition, 'crest_factor_db': 0.0, 'modulation': 'pulse',
                    'pulse_width_s': width, 'pulse_repetition_hz': repetition, 'source_id': self.profile_id}
        return {key: self._cfg[key] for key in ('frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle', 'crest_factor_db', 'modulation')} | {
            'source_id': self.profile_id, 'status': 'ok', 'valid': True,
            **({'ssid': self._cfg['ssid']} if self.role == 'wireless_ap' else {})}

    def _response(self, revision, *, changed=False, status=None, extra=None):
        visible_state = self._state
        if self._faults['disconnected']:
            visible_state, status = 'disconnected', 'disconnected'
        elif self._result is not None and (self._result['acquisition_setup_revision'] != revision
                                           or self._result['configuration_revision'] != self._configuration_revision):
            self._invalidate('configuration_changed')
            visible_state = self._state
        elif self._result is not None:
            try:
                if _json(self._prepare(revision)) != self._result_signature:
                    raise _InputError('input_changed_since_acquisition')
            except _InputError as error:
                self._invalidate(str(error))
                visible_state = self._state
        if status is None:
            status = 'pending' if self._pending else visible_state if visible_state in {'invalid', 'error', 'disconnected'} else 'ok'
        outputs = {}
        if status not in {'invalid', 'error', 'disconnected'} and not self._faults['drop_output']:
            if self._transmitting and not self._faults['drop_output']:
                try:
                    outputs['rf'] = self._rf_output()
                except _InputError:
                    pass
            if self._result is not None and self._pending is None:
                if self.role == 'test_software':
                    outputs['data'] = copy.deepcopy(self._result)
                    outputs['control'] = {'valid': True, 'requested_state': 'complete', 'verdict': self._result['verdict']}
                else:
                    outputs['measurement'] = self._display_measurement()
                    if 'data' in ROLE_PORTS[self.role]['outputs']:
                        outputs['data'] = copy.deepcopy(self._result)
        values = {'state': visible_state, 'reason': self._reason, 'configuration': copy.deepcopy(self._cfg),
                  'configuration_revision': self._configuration_revision, 'operation_complete': self._pending is None,
                  'outputs': outputs, 'calibration_state': self._calibration_state,
                  'simulation_policy': 'declared_synthetic_role_model'}
        if extra:
            values.update(extra)
        return {'status': status, 'values': values, 'setup_changed': changed}

    def perform(self, action, parameters, *, tick, setup_revision, inputs):
        try:
            self._context(tick, setup_revision, inputs)
        except _InputError as error:
            self._invalidate(str(error))
            return self._response(setup_revision)
        if action not in ROLE_ACTIONS[self.role]:
            return self._response(setup_revision, status='unsupported', extra={'reason': 'unsupported_action'})
        try:
            self._parameters(action, parameters)
            if self._faults['disconnected'] and action not in {'read_error', 'abort', 'reset'}:
                raise _InputError('communication_unavailable')
            if action == 'set_display_unit':
                if parameters['unit'] not in {'dBm', 'W'}:
                    raise _InputError('unsupported_display_unit')
                if self._result is not None:
                    _power_in_unit(self._result['value'], parameters['unit'])
                self._cfg['unit'] = parameters['unit']
                return self._response(setup_revision)
            if action == 'configure':
                candidate = copy.deepcopy(self._cfg)
                candidate.update(parameters)
                self._validate_settings(candidate)
                changed = candidate != self._cfg
                if changed:
                    if self.role == 'network_analyzer' and self._configured:
                        self._calibration_valid, self._calibration_state = False, 'verification_required'
                    self._cfg = candidate
                    self._configuration_revision += 1
                    self._invalidate('settings_changed', 'idle')
                    self._configured = True
                return self._response(setup_revision, changed=changed)
            if action == 'read_error':
                return self._response(setup_revision, extra={'error': self._errors.pop(0) if self._errors else None})
            if action in {'reset', 'abort', 'recover'}:
                if action == 'recover':
                    self._power()
                self._transmitting = False
                self._invalidate(None, 'aborted' if action == 'abort' else 'idle')
                if action == 'reset':
                    self._cfg = self._defaults()
                    self._configuration_revision += 1
                    self._configured = False
                    self._windows.clear()
                    if self.role == 'network_analyzer':
                        self._calibration_valid, self._calibration_state = False, 'verification_required'
                return self._response(setup_revision, changed=action == 'reset')
            if action in {'start_tx', 'stop_tx'}:
                if self.role == 'dfs_system' and self._policy.get('function') == 'analyzer':
                    return self._response(setup_revision, status='unsupported')
                if action == 'start_tx':
                    self._rf_output()
                changed = self._transmitting != (action == 'start_tx')
                if changed:
                    self._invalidate(None)
                    self._transmitting = action == 'start_tx'
                    self._state = 'transmitting' if self._transmitting else 'idle'
                return self._response(setup_revision, changed=changed)
            if action == 'fetch':
                if self._pending:
                    return self._response(setup_revision)
                window = parameters.get('window', self._cfg.get('window', 1))
                if window not in {1, 2, 3, 4}:
                    raise _InputError('measurement_window_out_of_scope')
                if self.role == 'power_meter' and window != self._cfg['window']:
                    previous = self._windows.get(window)
                    if previous is None or previous['configuration_revision'] != self._configuration_revision:
                        raise _InputError('window_data_not_current')
                    self._result = copy.deepcopy(previous)
                if self._result is None:
                    raise _InputError('no_current_measurement')
                return self._response(setup_revision)
            if action == 'trigger':
                if self._state != 'trigger_wait' or self._pending is None:
                    raise _InputError('not_armed_for_bus_trigger')
                self._pending['due_tick'] = tick+self._latency
                self._state = 'acquiring'
                return self._response(setup_revision)
            if action == 'verify_calibration':
                if self._pending:
                    raise _InputError('operation_in_progress')
                self._power()
                source = self._sensor(setup_revision) if self.role == 'power_meter' else self._rf()
                tolerance = _number(parameters['tolerance_db'], positive=True)
                deviation = source['power_dbm'] + self._faults['gain_error_db'] - parameters['reference_dbm']
                self._calibration_valid = abs(deviation) <= tolerance and not self._faults['invalid_calibration']
                self._calibration_state = 'valid' if self._calibration_valid else 'verification_failed'
                self._invalidate(None if self._calibration_valid else 'reference_check_failed', 'idle' if self._calibration_valid else 'invalid')
                return self._response(setup_revision, extra={'reference_deviation_db': deviation})
            if action in {'acquire', 'run', 'calibrate'}:
                if self._pending:
                    return self._response(setup_revision, status='error', extra={'reason': 'operation_in_progress'})
                if self.role == 'dfs_system' and self._policy.get('function') == 'generator' and action != 'calibrate':
                    return self._response(setup_revision, status='unsupported')
                calibrating = action == 'calibrate'
                source = self._prepare(setup_revision, calibrating=calibrating)
                self._pending = {'start_tick': tick, 'due_tick': tick+self._latency, 'revision': setup_revision,
                                 'source': source, 'signature': _json(source), 'calibrating': calibrating,
                                 'parameters': copy.deepcopy(parameters), 'blocked': self._faults['stuck']}
                self._result = None
                if calibrating:
                    self._calibration_valid, self._calibration_state = False, 'pending'
                trigger_wait = not calibrating and self._cfg.get('trigger_source') == 'bus'
                self._state, self._reason = 'trigger_wait' if trigger_wait else 'calibrating' if calibrating else 'acquiring', None
                return self._response(setup_revision)
        except _InputError as error:
            reason = str(error)
            self._queue(reason)
            if action in {'configure', 'set_display_unit'}:
                return self._response(setup_revision, status='error', extra={'reason': reason})
            self._invalidate(reason, 'disconnected' if reason == 'communication_unavailable' else 'invalid')
            return self._response(setup_revision)
        return self._response(setup_revision, status='unsupported')

    def advance(self, *, tick, setup_revision, inputs):
        try:
            self._context(tick, setup_revision, inputs)
            if self._transmitting:
                self._power()
            pending = self._pending
            if pending is None:
                return
            if pending['revision'] != setup_revision:
                raise _InputError('configuration_changed_during_acquisition')
            source = self._prepare(setup_revision, calibrating=pending['calibrating'])
            if _json(source) != pending['signature']:
                raise _InputError('input_changed_during_acquisition')
            waiting = self._state == 'trigger_wait' or self._faults['stuck']
            pending['blocked'] = pending['blocked'] or waiting
            if (waiting or pending['blocked']) and tick-pending['start_tick'] >= self._timeout:
                self._queue('acquisition_timeout')
                self._invalidate('acquisition_timeout', 'error')
                return
            if waiting or tick < pending['due_tick']:
                return
            self._pending = None
            if pending['calibrating']:
                if self.role == 'network_analyzer':
                    standard = pending['parameters'].get('standard_loss_db', 0.0)
                    deviation = max(abs(loss-standard-self._faults['gain_error_db']) for loss in source['loss_db'])
                    self._calibration_valid = deviation <= 0.05 and not self._faults['invalid_calibration']
                    self._calibration_state = 'valid' if self._calibration_valid else 'verification_failed'
                    self._state = 'idle' if self._calibration_valid else 'invalid'
                    self._reason = None if self._calibration_valid else 'calibration_reference_failed'
                else:
                    self._calibration_valid, self._calibration_state = False, 'verification_required'
                    self._state, self._reason = 'idle', None
            else:
                self._result = self._measurement(source, setup_revision, tick)
                self._result_signature = _json(source)
                _json(self._result)
                if self.role == 'power_meter':
                    self._windows[self._cfg['window']] = copy.deepcopy(self._result)
                self._state, self._reason = 'complete', None
        except _InputError as error:
            self._queue(str(error))
            self._transmitting = False
            self._invalidate(str(error), 'disconnected' if str(error) == 'communication_unavailable' else 'invalid')

    def observation(self, *, tick, setup_revision):
        self._context(tick, setup_revision)
        response = self._response(setup_revision)
        response.pop('setup_changed')
        return response

    def author_control(self, fault, value):
        supported = {'disconnected', 'drop_output'}
        if self.role in _MEASUREMENT:
            supported.add('stuck')
            if self.role != 'test_software':
                supported.add('gain_error_db')
        if self.role in _CALIBRATION:
            supported.add('invalid_calibration')
        if self.role == 'power_meter':
            supported.add('sensor_mismatch')
        if fault not in supported:
            raise ValueError('Unsupported author control')
        if fault == 'gain_error_db':
            value = _number(value)
            if abs(value) > 100:
                raise ValueError('Author offset out of bounds')
        elif type(value) is not bool:
            raise ValueError('Author switch must be boolean')
        self._faults[fault] = value
        if fault == 'invalid_calibration' and value:
            self._calibration_valid, self._calibration_state = False, 'verification_required'
        if fault == 'disconnected' and value:
            self._transmitting = False
            self._invalidate('communication_unavailable', 'disconnected')


def _factory(role):
    def create(profile, seed):
        if not isinstance(profile, dict) or profile.get('role') != role:
            raise ValueError('Factory role mismatch')
        return _Instrument(profile, seed)
    return create


DEVICE_FACTORIES = {role: _factory(role) for role in ROLE_PORTS}
