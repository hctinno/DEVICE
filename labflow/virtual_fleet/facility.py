"""Synthetic facilities, motion and auxiliary inspection; no vendor transport."""

import copy
import math
from collections import deque


def _parameter(kind, unit=None):
    value = {'type': kind, 'required': True}
    if unit:
        value['unit'] = unit
    return value


def _action(parameters=None, completion='immediate'):
    return {'parameters': parameters or {}, 'completion': completion}


_COMMON = {'reset': _action(completion='stops output/operation; active causes remain'),
           'read_errors': _action(completion='pop one FIFO error; zero means queue empty')}
_MOTION_ACTIONS = dict(_COMMON, **{
    'configure': _action({'speed_per_tick': _parameter('number', 'position unit/tick')}),
    'move': _action({'position': _parameter('number', 'profile position_unit')}, 'pending until position reached'),
    'home': _action(completion='pending until declared minimum reached'),
    'stop': _action(completion='stop at current position'),
    'clear_trip': _action(completion='only succeeds after active cause is removed'),
})
ROLE_ACTIONS = {
    'power_supply': dict(_COMMON, **{
        'configure': _action({'voltage_v': _parameter('number', 'V'), 'current_limit_a': _parameter('number', 'A')}),
        'set_load': _action({'resistance_ohm': _parameter('number', 'ohm')}),
        'output': _action({'enabled': _parameter('boolean')}),
        'measure': _action(completion='valid only with enabled healthy output'),
        'clear_trip': _action(completion='only succeeds after active cause is removed'),
    }),
    'temperature_chamber': dict(_COMMON, **{
        'configure': _action({'temperature_c': _parameter('number', 'C'), 'humidity_percent': _parameter('number', '%')}),
        'start': _action(completion='pending until target and stable dwell reached'),
        'stop': _action(completion='cancel stability wait'),
        'wait_stable': _action(completion='pending/ok reflect stability, not metrological certification'),
        'sample': _action(completion='pending while unstable; no reading when sensor unavailable'),
    }),
    'position_controller': copy.deepcopy(_MOTION_ACTIONS),
    'antenna_mast': copy.deepcopy(_MOTION_ACTIONS),
    'turntable': copy.deepcopy(_MOTION_ACTIONS),
    'inspection_microscope': dict(_COMMON, **{
        'configure': _action({'magnification': _parameter('number', 'x'), 'focus_um': _parameter('number', 'um'),
                              'illumination_percent': _parameter('number', '%')}),
        'load_sample': _action({'sample_id': _parameter('string'), 'feature_size_um': _parameter('number', 'um'),
                               'surface_contrast': _parameter('number', '0..1')}),
        'acquire': _action(completion='pending; synthetic feature only, no image classification'),
        'fetch': _action(completion='returns current-revision acquisition or explicit invalid/error'),
        'abort': _action(completion='cancel active acquisition and discard result'),
    }),
}

ROLE_PORTS = {
    'power_supply': {'inputs': {}, 'outputs': {'power': 'power'}},
    'temperature_chamber': {'inputs': {'power': 'power'}, 'outputs': {'environment': 'environment'}},
    'position_controller': {'inputs': {'power': 'power', 'control': 'control'},
                            'outputs': {'position': 'position', 'control': 'control'}},
    'antenna_mast': {'inputs': {'power': 'power', 'control': 'control'}, 'outputs': {'position': 'position'}},
    'turntable': {'inputs': {'power': 'power', 'control': 'control'}, 'outputs': {'position': 'position'}},
    'inspection_microscope': {'inputs': {'power': 'power', 'sample': 'data'}, 'outputs': {'data': 'data'}},
}


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _number(policy, name, default, minimum=None, maximum=None, positive=False):
    value = policy.get(name, default)
    if not _finite(value) or (positive and value <= 0):
        raise ValueError(f'invalid synthetic policy: {name}')
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError(f'synthetic policy out of range: {name}')
    return float(value)


def _integer(policy, name, default, minimum=1):
    value = policy.get(name, default)
    if type(value) is not int or not minimum <= value <= 10000:
        raise ValueError(f'invalid synthetic tick policy: {name}')
    return value


def _boolean(policy, name, default=False):
    value = policy.get(name, default)
    if type(value) is not bool:
        raise ValueError(f'invalid synthetic boolean policy: {name}')
    return value


class _Facility:
    faults = frozenset({'communication_loss'})
    policy_names = frozenset()
    permitted_roles = frozenset()

    def __init__(self, profile, seed):
        self.profile = copy.deepcopy(profile)
        self.role = profile['role']
        if self.role not in self.permitted_roles:
            raise ValueError('unsupported facility role')
        self.policy = copy.deepcopy(profile.get('simulation_parameters', {}))
        if not isinstance(self.policy, dict):
            raise ValueError('simulation_parameters must be a map')
        if set(self.policy) - (self.policy_names | {'requires_power'}):
            raise ValueError('unsupported synthetic facility policy')
        declared_ports = profile.get('ports', {})
        if not isinstance(declared_ports, dict) or set(declared_ports) - {'inputs', 'outputs'}:
            raise ValueError('unsupported facility ports')
        for direction in ('inputs', 'outputs'):
            declarations = declared_ports.get(direction, {})
            if not isinstance(declarations, dict):
                raise ValueError('facility ports must be maps')
            for name, declaration in declarations.items():
                kind = declaration.get('kind') if isinstance(declaration, dict) else declaration
                if ROLE_PORTS[self.role][direction].get(name) != kind:
                    raise ValueError('unsupported facility port name or kind')
        self._faults = dict.fromkeys(self.faults, False)
        self._errors = deque(maxlen=64)
        self._last_tick = 0
        self._revision = 0
        self._inputs = {}
        self._communication_down = False
        self._requires_power = _boolean(self.policy, 'requires_power')
        if self.role == 'power_supply' and self._requires_power:
            raise ValueError('upstream power supply modelling is unsupported')
        ports = profile.get('ports', {}).get('outputs', {})
        self._output_names = set(ports)

    def _error(self, code, message):
        item = {'code': code, 'message': message}
        if not self._errors or self._errors[-1] != item:
            if len(self._errors) == 64:
                self._errors[-1] = {'code': 'E199', 'message': 'Additional errors were suppressed'}
            else:
                self._errors.append(item)

    def _response(self, status='ok', values=None, changed=False):
        return {'status': status, 'values': values or {}, 'setup_changed': changed}

    def _invalid(self, reason):
        self._error('E101', reason)
        return self._response('invalid', {'reason': reason})

    def _ports(self, values):
        return {name: value for name, value in values.items() if name in self._output_names}

    def _power_ready(self):
        if not self._requires_power:
            return True
        power = self._inputs.get('power', {})
        return (isinstance(power, dict) and power.get('valid') is True and power.get('enabled') is True
                and _finite(power.get('voltage_v')) and power['voltage_v'] > 0)

    def author_control(self, fault, value):
        if fault not in self._faults or type(value) is not bool:
            raise ValueError('unsupported author control or invalid value')
        self._faults[fault] = value

    def _valid_parameters(self, action, parameters):
        if not isinstance(parameters, dict):
            return False
        specs = ROLE_ACTIONS[self.role][action]['parameters']
        if set(parameters) != set(specs):
            return False
        for key, spec in specs.items():
            value = parameters[key]
            if spec['type'] == 'number' and not _finite(value):
                return False
            if spec['type'] == 'boolean' and type(value) is not bool:
                return False
            if spec['type'] == 'string' and (not isinstance(value, str) or not value or len(value) > 128):
                return False
        return True

    def perform(self, action, parameters, *, tick, setup_revision, inputs):
        if action not in ROLE_ACTIONS[self.role]:
            return self._response('unsupported', {'reason': 'unsupported_action'})
        if not self._valid_parameters(action, parameters):
            return self._invalid('invalid_parameters')
        self.advance(tick=tick, setup_revision=setup_revision, inputs=inputs)
        if self._faults['communication_loss']:
            return self._response('disconnected', {'reason': 'device_unavailable'})
        if action == 'read_errors':
            return self._response(values={'error': self._errors.popleft() if self._errors else {'code': '0', 'message': 'No error'}})
        if action == 'reset':
            self._reset()
            self._sync()
            return self._response('error' if self._status() == 'error' else 'ok',
                                  {'state': self._state(), 'ready': self._status() in {'ok', 'pending'}}, True)
        return self._perform(action, parameters)

    def advance(self, *, tick, setup_revision, inputs):
        if type(tick) is not int or tick < self._last_tick or tick - self._last_tick > 10000:
            raise ValueError('invalid virtual tick')
        if type(setup_revision) is not int or setup_revision < 0 or not isinstance(inputs, dict):
            raise ValueError('invalid virtual context')
        self._inputs, self._revision = copy.deepcopy(inputs), setup_revision
        if self._faults['communication_loss']:
            if not self._communication_down:
                self._halt()
                self._error('E102', 'Device communication unavailable')
            self._communication_down = True
            self._last_tick = tick
            return
        self._communication_down = False
        self._sync()
        while self._last_tick < tick:
            self._last_tick += 1
            self._step()
            self._sync()

    def observation(self, *, tick, setup_revision):
        if self._faults['communication_loss']:
            return {'status': 'disconnected', 'state': 'unavailable', 'values': {'outputs': {}}}
        return {'status': self._status(), 'state': self._state(), 'values': self._values()}

    def _sync(self):
        pass

    def _step(self):
        pass


class PowerSupply(_Facility):
    faults = _Facility.faults | {'overcurrent', 'output_failure'}
    permitted_roles = frozenset({'power_supply'})
    policy_names = frozenset({'voltage_min_v', 'voltage_max_v', 'current_max_a', 'initial_voltage_v',
                              'initial_current_limit_a', 'load_resistance_ohm'})

    def __init__(self, profile, seed):
        super().__init__(profile, seed)
        p = self.policy
        self.minimum = _number(p, 'voltage_min_v', 0, minimum=0)
        self.maximum = _number(p, 'voltage_max_v', 60, minimum=self.minimum)
        self.current_max = _number(p, 'current_max_a', 10, positive=True)
        self.voltage = _number(p, 'initial_voltage_v', 0, minimum=self.minimum, maximum=self.maximum)
        self.current_limit = _number(p, 'initial_current_limit_a', 1, minimum=0, maximum=self.current_max)
        self.resistance = _number(p, 'load_resistance_ohm', 100, positive=True)
        self.enabled = self.trip = False

    def _sync(self):
        if self._faults['overcurrent'] or self._faults['output_failure']:
            self._halt()
            self._error('P101', 'Output protection active')

    def _halt(self):
        self.enabled, self.trip = False, True

    def _reset(self):
        self.enabled = False
        self.trip = any(self._faults.values())

    def _status(self):
        return 'error' if self.trip else 'ok'

    def _state(self):
        return 'protected' if self.trip else 'enabled' if self.enabled else 'off'

    def _electrical(self):
        current = min(self.voltage / self.resistance, self.current_limit)
        voltage = current * self.resistance
        return {'voltage_v': voltage, 'current_a': current,
                'acquisition_tick': self._last_tick, 'acquisition_revision': self._revision,
                'mode': 'constant_current' if self.voltage / self.resistance > self.current_limit else 'constant_voltage'}

    def _values(self):
        output = {'enabled': self.enabled, 'valid': self.enabled and not self.trip}
        if output['valid']:
            output.update(self._electrical())
        else:
            output.update(voltage_v=0., current_a=0.)
        return {'voltage_setpoint_v': self.voltage, 'current_limit_a': self.current_limit,
                'outputs': self._ports({'power': output})}

    def _perform(self, action, parameters):
        if action == 'configure':
            voltage, current = parameters['voltage_v'], parameters['current_limit_a']
            if not self.minimum <= voltage <= self.maximum or not 0 <= current <= self.current_max:
                return self._invalid('setpoint_out_of_range')
            changed = (voltage, current) != (self.voltage, self.current_limit)
            self.voltage, self.current_limit = float(voltage), float(current)
            return self._response(changed=changed)
        if action == 'set_load':
            resistance = parameters['resistance_ohm']
            if resistance <= 0:
                return self._invalid('load_must_be_positive')
            changed = self.resistance != resistance
            self.resistance = float(resistance)
            return self._response(changed=changed)
        if action == 'clear_trip':
            if any(self._faults.values()):
                return self._response('error', {'reason': 'condition_active'})
            changed, self.trip = self.trip, False
            return self._response(changed=changed)
        if action == 'output':
            enabled = parameters['enabled']
            if enabled and self.trip:
                return self._response('error', {'reason': 'protection_requires_recovery'})
            changed, self.enabled = enabled != self.enabled, enabled
            return self._response(changed=changed)
        if action == 'measure':
            if self.trip:
                return self._response('error', {'reason': 'output_unavailable'})
            if not self.enabled:
                return self._response('invalid', {'reason': 'output_disabled'})
            return self._response(values=self._electrical())
        return self._response('unsupported')


class TemperatureChamber(_Facility):
    faults = _Facility.faults | {'stuck', 'sensor_failure'}
    permitted_roles = frozenset({'temperature_chamber'})
    policy_names = frozenset({'temperature_min_c', 'temperature_max_c', 'humidity_min_percent', 'humidity_max_percent',
                              'initial_temperature_c', 'initial_humidity_percent', 'temperature_rate_c_per_tick',
                              'humidity_rate_percent_per_tick', 'temperature_tolerance_c', 'humidity_tolerance_percent',
                              'stable_ticks', 'timeout_ticks'})

    def __init__(self, profile, seed):
        super().__init__(profile, seed)
        p = self.policy
        self.temp_min = _number(p, 'temperature_min_c', -40)
        self.temp_max = _number(p, 'temperature_max_c', 85, minimum=self.temp_min)
        self.humidity_min = _number(p, 'humidity_min_percent', 0, minimum=0, maximum=100)
        self.humidity_max = _number(p, 'humidity_max_percent', 100, minimum=self.humidity_min, maximum=100)
        self.temperature = _number(p, 'initial_temperature_c', 20, minimum=self.temp_min, maximum=self.temp_max)
        self.humidity = _number(p, 'initial_humidity_percent', 50, minimum=self.humidity_min, maximum=self.humidity_max)
        self.temp_rate = _number(p, 'temperature_rate_c_per_tick', 2, positive=True)
        self.humidity_rate = _number(p, 'humidity_rate_percent_per_tick', 5, positive=True)
        self.temp_tolerance = _number(p, 'temperature_tolerance_c', .25, minimum=0)
        self.humidity_tolerance = _number(p, 'humidity_tolerance_percent', .5, minimum=0)
        self.stable_ticks = _integer(p, 'stable_ticks', 2)
        self.timeout_ticks = _integer(p, 'timeout_ticks', 100)
        self.target_temperature, self.target_humidity = self.temperature, self.humidity
        self.running = self.failed = False
        self._dwell = self._started = 0

    def _halt(self):
        self.running, self.failed, self._dwell = False, True, 0

    def _reset(self):
        self.running = self.failed = False
        self._dwell = 0

    def _sync(self):
        if self._faults['sensor_failure']:
            self._halt()
            self._error('T101', 'Environmental reading unavailable')
        if not self._power_ready():
            self.running, self._dwell = False, 0

    def _state(self):
        if self.failed:
            return 'unavailable'
        if not self._power_ready():
            return 'unpowered'
        if not self.running:
            return 'idle'
        return 'stable' if self._dwell >= self.stable_ticks else 'conditioning'

    def _status(self):
        if self.failed:
            return 'error'
        if not self._power_ready() or not self.running:
            return 'invalid'
        return 'ok' if self._dwell >= self.stable_ticks else 'pending'

    def _step(self):
        if not self.running or self.failed or not self._power_ready():
            return
        if not self._faults['stuck']:
            self.temperature += max(-self.temp_rate, min(self.temp_rate, self.target_temperature - self.temperature))
            self.humidity += max(-self.humidity_rate, min(self.humidity_rate, self.target_humidity - self.humidity))
        reached = (abs(self.temperature - self.target_temperature) <= self.temp_tolerance and
                   abs(self.humidity - self.target_humidity) <= self.humidity_tolerance)
        self._dwell = self._dwell + 1 if reached else 0
        if self._dwell < self.stable_ticks and self._last_tick - self._started >= self.timeout_ticks:
            self._halt()
            self._error('T102', 'Conditioning time limit reached')

    def _values(self):
        if self._faults['sensor_failure']:
            return {'outputs': {}, 'reason': 'reading_unavailable'}
        stable = self._status() == 'ok'
        environment = {'valid': stable, 'stable': stable, 'temperature_c': self.temperature,
                       'humidity_percent': self.humidity}
        return {'temperature_c': self.temperature, 'humidity_percent': self.humidity,
                'target_temperature_c': self.target_temperature, 'target_humidity_percent': self.target_humidity,
                'stable_ticks': self._dwell, 'required_stable_ticks': self.stable_ticks,
                'outputs': self._ports({'environment': environment})}

    def _perform(self, action, parameters):
        if action == 'configure':
            temp, humidity = parameters['temperature_c'], parameters['humidity_percent']
            if not self.temp_min <= temp <= self.temp_max or not self.humidity_min <= humidity <= self.humidity_max:
                return self._invalid('setpoint_out_of_range')
            changed = (temp, humidity) != (self.target_temperature, self.target_humidity)
            self.target_temperature, self.target_humidity = float(temp), float(humidity)
            if changed:
                self._dwell, self._started = 0, self._last_tick
            return self._response(changed=changed)
        if action == 'stop':
            changed, self.running, self._dwell = self.running, False, 0
            return self._response(changed=changed)
        if action == 'start':
            if not self._power_ready():
                return self._invalid('required_power_unavailable')
            if self.failed:
                return self._response('error', {'reason': 'recovery_required'})
            changed = not self.running
            if changed:
                self._started, self._dwell = self._last_tick, 0
            self.running = True
            return self._response(self._status(), changed=changed)
        if action in {'sample', 'wait_stable'}:
            values = self._values() if action == 'sample' else {'state': self._state()}
            return self._response(self._status(), values)
        return self._response('unsupported')


class PositionDevice(_Facility):
    faults = _Facility.faults | {'jammed', 'interlock_open', 'limit_switch'}
    permitted_roles = frozenset({'position_controller', 'antenna_mast', 'turntable'})
    policy_names = frozenset({'position_unit', 'position_min', 'position_max', 'initial_position',
                              'speed_max_per_tick', 'speed_per_tick', 'timeout_ticks', 'requires_control'})

    def __init__(self, profile, seed):
        super().__init__(profile, seed)
        p = self.policy
        mast = self.role == 'antenna_mast'
        self.unit = p.get('position_unit', 'm' if mast else 'deg')
        if self.unit not in {'m', 'mm', 'deg'}:
            raise ValueError('unsupported synthetic position unit')
        self.minimum = _number(p, 'position_min', 1 if mast else 0)
        self.maximum = _number(p, 'position_max', 4 if self.unit == 'm' else 360, minimum=self.minimum)
        self.position = _number(p, 'initial_position', self.minimum, minimum=self.minimum, maximum=self.maximum)
        self.speed_max = _number(p, 'speed_max_per_tick', 1 if self.unit == 'm' else 360, positive=True)
        self.speed = _number(p, 'speed_per_tick', .25 if self.unit == 'm' else 30, positive=True, maximum=self.speed_max)
        self.timeout_ticks = _integer(p, 'timeout_ticks', 100)
        self.requires_control = _boolean(p, 'requires_control')
        self.target = self.position
        self.moving = self.trip = self._command_enabled = False
        self._started = self._generation = 0
        self._seen_command = None
        self._control_ready = not self.requires_control

    def _halt(self):
        self.moving, self.trip, self._command_enabled = False, True, False
        self.target = self.position

    def _reset(self):
        self.moving = self.trip = self._command_enabled = False
        self.target = self.position
        self._generation += 1

    def _active_cause(self):
        return any(self._faults.values()) or not self._power_ready()

    def _sync(self):
        if self._faults['interlock_open'] or self._faults['limit_switch']:
            self._halt()
            self._error('M101', 'Motion safety condition active')
        if not self._power_ready():
            if self.moving:
                self._halt()
            self._command_enabled = False
        control = self._inputs.get('control')
        if control is None:
            self._control_ready = not self.requires_control
        else:
            command_valid = (isinstance(control, dict) and control.get('valid') is True and
                             type(control.get('enabled')) is bool and control.get('unit') == self.unit and
                             _finite(control.get('target_position')) and
                             self.minimum <= control['target_position'] <= self.maximum and
                             type(control.get('generation')) is int)
            self._control_ready = command_valid and control['enabled']
            if command_valid:
                key = (control.get('source_id'), control['generation'])
                if key != self._seen_command:
                    self._seen_command = key
                    if not control['enabled']:
                        self.moving = self._command_enabled = False
                        self.target = self.position
                        self._generation += 1
                    elif not self.trip and self._power_ready():
                        self._move(control['target_position'])
            elif self.moving:
                self._halt()
        if self.requires_control and not self._control_ready and self.moving:
            self._halt()

    def _state(self):
        if self.trip:
            return 'interrupted'
        if not self._power_ready():
            return 'unpowered'
        if not self._control_ready:
            return 'awaiting_control'
        return 'moving' if self.moving else 'idle'

    def _status(self):
        if self.trip:
            return 'error'
        if not self._power_ready() or not self._control_ready:
            return 'invalid'
        return 'pending' if self.moving else 'ok'

    def _move(self, target):
        self.target, self._started = float(target), self._last_tick
        self.moving = self.position != self.target
        self._command_enabled = True
        self._generation += 1

    def _step(self):
        if not self.moving or self.trip:
            return
        if not self._faults['jammed']:
            self.position += max(-self.speed, min(self.speed, self.target - self.position))
        self.moving = abs(self.position - self.target) > 1e-12
        if not self.moving:
            self.position = self.target
        elif self._last_tick - self._started >= self.timeout_ticks:
            self._halt()
            self._error('M102', 'Motion time limit reached')

    def _values(self):
        valid = self._status() in {'ok', 'pending'}
        outputs = {'position': {'valid': valid, 'position': self.position, 'unit': self.unit,
                                'moving': self.moving},
                   'control': {'valid': valid, 'enabled': self._command_enabled and valid,
                               'target_position': self.target, 'unit': self.unit, 'generation': self._generation}}
        return {'position': self.position, 'target_position': self.target, 'unit': self.unit,
                'speed_per_tick': self.speed, 'moving': self.moving, 'safety_ready': not self.trip,
                'outputs': self._ports(outputs)}

    def _perform(self, action, parameters):
        if action == 'configure':
            speed = parameters['speed_per_tick']
            if not 0 < speed <= self.speed_max:
                return self._invalid('speed_out_of_range')
            changed, self.speed = speed != self.speed, float(speed)
            return self._response(changed=changed)
        if action == 'stop':
            changed = self.moving or self._command_enabled
            self.moving = self._command_enabled = False
            self.target = self.position
            self._generation += 1
            return self._response(changed=changed)
        if action == 'clear_trip':
            if self._active_cause():
                return self._response('error', {'reason': 'condition_active'})
            changed, self.trip = self.trip, False
            return self._response(changed=changed)
        if action in {'move', 'home'}:
            target = parameters['position'] if action == 'move' else self.minimum
            if not self.minimum <= target <= self.maximum:
                return self._invalid('position_out_of_range')
            if self.trip:
                return self._response('error', {'reason': 'recovery_required'})
            if not self._power_ready() or self.requires_control and not self._control_ready:
                return self._invalid('required_input_unavailable')
            self._move(target)
            return self._response(self._status(), changed=True)
        return self._response('unsupported')


class InspectionMicroscope(_Facility):
    """Auxiliary synthetic feature acquisition, never an image-based pass verdict."""

    faults = _Facility.faults | {'optics_failure', 'acquisition_stall'}
    permitted_roles = frozenset({'inspection_microscope'})
    policy_names = frozenset({'magnification_min', 'magnification_max', 'focus_min_um', 'focus_max_um',
                              'initial_magnification', 'initial_focus_um', 'initial_illumination_percent',
                              'sample_plane_um', 'focus_width_um', 'minimum_quality', 'acquisition_ticks',
                              'timeout_ticks', 'requires_sample'})

    def __init__(self, profile, seed):
        super().__init__(profile, seed)
        p = self.policy
        self.magnification_min = _number(p, 'magnification_min', 1, positive=True)
        self.magnification_max = _number(p, 'magnification_max', 200, minimum=self.magnification_min)
        self.focus_min = _number(p, 'focus_min_um', 0)
        self.focus_max = _number(p, 'focus_max_um', 1000, minimum=self.focus_min)
        self.magnification = _number(p, 'initial_magnification', 10, minimum=self.magnification_min, maximum=self.magnification_max)
        self.focus = _number(p, 'initial_focus_um', 100, minimum=self.focus_min, maximum=self.focus_max)
        self.illumination = _number(p, 'initial_illumination_percent', 50, minimum=0, maximum=100)
        self.sample_plane = _number(p, 'sample_plane_um', 100, minimum=self.focus_min, maximum=self.focus_max)
        self.focus_width = _number(p, 'focus_width_um', 20, positive=True)
        self.minimum_quality = _number(p, 'minimum_quality', .25, minimum=0, maximum=1)
        self.acquisition_ticks = _integer(p, 'acquisition_ticks', 2)
        self.timeout_ticks = _integer(p, 'timeout_ticks', 10)
        self.requires_sample = _boolean(p, 'requires_sample')
        self._source_sample = None
        self._sample_ready = False
        self.sample = self.result = None
        self._acquired_revision = self._started = self._ready_tick = None
        self.active = self.failed = False
        self.invalid_reason = 'no_acquisition'

    def _halt(self):
        self.active, self.failed, self.result = False, True, None
        self.invalid_reason = 'operation_interrupted'

    def _reset(self):
        self.active = self.failed = False
        self.result = self._acquired_revision = None
        self.invalid_reason = 'no_acquisition'

    def _sync(self):
        if self._faults['optics_failure']:
            self._halt()
            self._error('I101', 'Optical reading unavailable')
        if not self._power_ready():
            if self.active:
                self._halt()
            self.result = None
        sample = self._inputs.get('sample')
        self._sample_ready = not self.requires_sample and self.sample is not None
        if sample is not None:
            self._sample_ready = (isinstance(sample, dict) and sample.get('valid') is True and
                                  isinstance(sample.get('sample_id'), str) and 0 < len(sample['sample_id']) <= 128 and
                                  _finite(sample.get('feature_size_um')) and sample['feature_size_um'] > 0 and
                                  _finite(sample.get('surface_contrast')) and 0 <= sample['surface_contrast'] <= 1)
            if self._sample_ready:
                selected = {key: sample[key] for key in ('sample_id', 'feature_size_um', 'surface_contrast')}
                if selected != self._source_sample:
                    self._source_sample = copy.deepcopy(selected)
                    self.active, self.result = False, None
                    self.invalid_reason = 'sample_changed'
                self.sample = selected
        if not self._sample_ready:
            self.active, self.result = False, None
            self.invalid_reason = 'sample_unavailable'
        if self._acquired_revision is not None and self._revision != self._acquired_revision:
            self.active, self.result = False, None
            self.invalid_reason = 'setup_changed'

    def _state(self):
        if self.failed:
            return 'unavailable'
        if self.active:
            return 'acquiring'
        return 'complete' if self.result is not None else 'idle'

    def _status(self):
        if self.failed:
            return 'error'
        if not self._power_ready() or not self._sample_ready:
            return 'invalid'
        if self.active:
            return 'pending'
        return 'ok' if self.result is not None else 'invalid'

    def _step(self):
        if not self.active:
            return
        if self._faults['acquisition_stall']:
            if self._last_tick - self._started >= self.timeout_ticks:
                self._halt()
                self._error('I102', 'Acquisition time limit reached')
            return
        if self._last_tick < self._ready_tick:
            return
        focus_score = max(0., 1. - abs(self.focus - self.sample_plane) / self.focus_width)
        illumination_score = max(0., 1. - abs(self.illumination - 50.) / 50.)
        quality = focus_score * illumination_score * self.sample['surface_contrast']
        self.active = False
        if quality < self.minimum_quality:
            self.invalid_reason = 'insufficient_observation_quality'
            self._error('I103', 'Observation quality below synthetic policy')
            return
        image_size = self.sample['feature_size_um'] * self.magnification
        if not _finite(image_size):
            self.invalid_reason = 'synthetic_calculation_out_of_range'
            self._error('I104', 'Synthetic feature calculation outside numeric range')
            return
        self.result = {'valid': True, 'feature_size_um': self.sample['feature_size_um'], 'quality': quality,
                       'magnification': self.magnification, 'image_feature_size_um': image_size,
                       'unit': 'um', 'acquisition_tick': self._last_tick, 'acquisition_revision': self._acquired_revision,
                       'synthetic_sample': True}

    def _values(self):
        values = {'scope': 'auxiliary cable validation', 'image_interpretation': 'not_performed',
                  'synthetic_sample': True, 'magnification': self.magnification, 'focus_um': self.focus,
                  'illumination_percent': self.illumination, 'outputs': {}}
        if self.result is not None:
            values['measurement'] = copy.deepcopy(self.result)
            values['outputs'] = self._ports({'data': copy.deepcopy(self.result)})
        else:
            values['reason'] = self.invalid_reason
        return values

    def _perform(self, action, parameters):
        if action == 'configure':
            magnification, focus, illumination = (parameters['magnification'], parameters['focus_um'], parameters['illumination_percent'])
            if not self.magnification_min <= magnification <= self.magnification_max or not self.focus_min <= focus <= self.focus_max or not 0 <= illumination <= 100:
                return self._invalid('optical_setting_out_of_range')
            changed = (magnification, focus, illumination) != (self.magnification, self.focus, self.illumination)
            self.magnification, self.focus, self.illumination = float(magnification), float(focus), float(illumination)
            if changed:
                self.active, self.result = False, None
                self.invalid_reason = 'setup_changed'
            return self._response(changed=changed)
        if action == 'load_sample':
            if self.requires_sample or 'sample' in self._inputs:
                return self._invalid('sample_input_authoritative')
            if parameters['feature_size_um'] <= 0 or not 0 <= parameters['surface_contrast'] <= 1:
                return self._invalid('invalid_synthetic_sample')
            self.sample = copy.deepcopy(parameters)
            self._sample_ready = not self.requires_sample
            self.active, self.result = False, None
            self.invalid_reason = 'sample_changed'
            return self._response(changed=True)
        if action == 'abort':
            changed = self.active or self.result is not None
            self.active, self.result = False, None
            self.invalid_reason = 'cancelled'
            return self._response(changed=changed)
        if action == 'acquire':
            if self.failed:
                return self._response('error', {'reason': 'recovery_required'})
            if not self._power_ready() or not self._sample_ready or self.illumination <= 0:
                return self._invalid('acquisition_prerequisite_missing')
            if self.active:
                return self._response('pending', {'reason': 'already_acquiring'})
            self.result = None
            self.active, self._started = True, self._last_tick
            self._ready_tick = self._last_tick + self.acquisition_ticks
            self._acquired_revision = self._revision
            return self._response('pending')
        if action == 'fetch':
            return self._response(self._status(), self._values())
        return self._response('unsupported')


DEVICE_FACTORIES = {
    'power_supply': PowerSupply,
    'temperature_chamber': TemperatureChamber,
    'position_controller': PositionDevice,
    'antenna_mast': PositionDevice,
    'turntable': PositionDevice,
    'inspection_microscope': InspectionMicroscope,
}
