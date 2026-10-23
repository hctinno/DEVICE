"""Pure virtual RF roles. Values are explicit simulation policies, not hardware.

The caller owns the trusted clock, setup revision, topology and provenance.
No network, DUT software, instrument protocol or customer artifact is executed.
"""
import copy
import json
import math


ROLE_PORTS = {
    'dut': {'inputs': {'power': 'power', 'environment': 'environment', 'control': 'control'}, 'outputs': {'rf': 'rf'}},
    'power_sensor': {'inputs': {'rf': 'rf'}, 'outputs': {'measurement': 'measurement'}},
    'attenuator': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf'}},
    'coupler': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf', 'coupled': 'rf'}},
    'splitter': {'inputs': {'rf': 'rf'}, 'outputs': {'rf_1': 'rf', 'rf_2': 'rf'}},
    'antenna': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf'}},
    'amplifier': {'inputs': {'rf': 'rf', 'power': 'power'}, 'outputs': {'rf': 'rf'}},
    'filter': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf'}},
    'rf_switch': {'inputs': {'rf_1': 'rf', 'rf_2': 'rf', 'control': 'control'}, 'outputs': {'rf': 'rf'}},
    'lisn': {'inputs': {'rf': 'rf', 'power': 'power'}, 'outputs': {'rf': 'rf', 'power': 'power'}},
}
ROLE_PORT_VARIANTS = {
    'rf_switch.controller_only': {'inputs': {'control': 'control'}, 'outputs': {'control': 'control'}},
    'splitter.four_way': {'inputs': {'rf': 'rf'}, 'outputs': {f'rf_{i}': 'rf' for i in range(1, 5)}},
}


def _parameter(kind, unit='', required=False):
    return {'type': kind, 'required': required, 'unit': unit}


_N = lambda unit='', required=False: _parameter('number', unit, required)
_COMMON_CONFIG = {'enabled': _parameter('boolean'), 'band_min_hz': _N('Hz'), 'band_max_hz': _N('Hz'),
                  'max_input_dbm': _N('dBm'), 'max_output_dbm': _N('dBm')}
_CONFIG = {
    'dut': {'frequency_hz': _N('Hz', True), 'power_dbm': _N('dBm', True),
            'bandwidth_hz': _N('Hz', True), 'duty_cycle': _N('ratio', True),
            'modulation': _parameter('string', required=True), 'crest_factor_db': _N('dB'),
            'startup_ticks': _parameter('integer', 'tick')},
    'power_sensor': {'calibration_valid': _parameter('boolean', required=True),
                     'expected_model': _parameter('string'), 'acquisition_ticks': _parameter('integer', 'tick'),
                     'acquisition_policy': _parameter('string')},
    'attenuator': {'attenuation_db': _N('dB', True), 'steps_db': _parameter('array', 'dB'),
                   'loss_table': _parameter('array')},
    'coupler': {'through_loss_db': _N('dB', True), 'coupling_db': _N('dB', True)},
    'splitter': {'ways': _parameter('integer', required=True), 'loss_db': _N('dB'), 'loss_table': _parameter('array')},
    'antenna': {'gain_db': _N('dB', True), 'loss_db': _N('dB'), 'loss_table': _parameter('array')},
    'amplifier': {'gain_db': _N('dB'), 'gain_table': _parameter('array')},
    'filter': {'loss_db': _N('dB'), 'loss_table': _parameter('array'), 'band_min_hz': _N('Hz', True), 'band_max_hz': _N('Hz', True)},
    'rf_switch': {'loss_db': _N('dB'), 'loss_table': _parameter('array'), 'settling_ticks': _parameter('integer', 'tick'),
                   'routes': _parameter('array')},
    'lisn': {'loss_db': _N('dB'), 'loss_table': _parameter('array')},
}
ROLE_ACTIONS = {
    role: {'configure': {'parameters': {**copy.deepcopy(_COMMON_CONFIG), **copy.deepcopy(fields)}, 'completion': 'configuration_committed'},
           'read': {'parameters': {}, 'completion': 'current_observation'},
           'reset': {'parameters': {}, 'completion': 'configuration_retained_activity_cleared'}}
    for role, fields in _CONFIG.items()
}
for _role in ROLE_ACTIONS:
    if _role != 'dut':
        ROLE_ACTIONS[_role]['enable'] = {'parameters': {'enabled': _parameter('boolean', required=True)}, 'completion': 'output_gate_changed'}
ROLE_ACTIONS['attenuator']['set_attenuation'] = {'parameters': {'attenuation_db': _N('dB', True)}, 'completion': 'declared_step_selected'}
ROLE_ACTIONS['rf_switch']['select_path'] = {'parameters': {'input_port': _parameter('string', required=True)}, 'completion': 'pending_until_virtual_settling_tick'}
ROLE_ACTIONS['dut'].update(start={'parameters': {}, 'completion': 'pending_until_startup_tick'},
                           stop={'parameters': {}, 'completion': 'rf_output_stopped'})
ROLE_ACTIONS['power_sensor']['acquire'] = {'parameters': {}, 'completion': 'pending_until_acquisition_tick'}


class _Issue(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


def _number(value, *, positive=False, nonnegative=False):
    if type(value) not in {int, float}:
        raise ValueError('Expected a finite number')
    try:
        value = float(value)
    except OverflowError:
        raise ValueError('Expected a representable finite number') from None
    if not math.isfinite(value):
        raise ValueError('Expected a finite number')
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError('Number outside policy range')
    return float(value)


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError('Expected bounded nonempty text')
    return value


def _rf_signal(value, allow_cw_zero=False):
    if not isinstance(value, dict) or value.get('valid') is not True or value.get('status', 'ok') != 'ok':
        raise _Issue('invalid', 'invalid_rf_input')
    try:
        signal = {'status': 'ok', 'valid': True,
                  'frequency_hz': _number(value.get('frequency_hz'), positive=True),
                  'power_dbm': _number(value.get('power_dbm')),
                  'bandwidth_hz': _number(value.get('bandwidth_hz'), positive=True),
                  'duty_cycle': _number(value.get('duty_cycle'), positive=True),
                  'modulation': _text(value.get('modulation')), 'source_id': _text(value.get('source_id'))}
        crest = value.get('crest_factor_db')
        if crest is None and signal['modulation'].upper() == 'CW' and allow_cw_zero:
            crest = 0
        signal['crest_factor_db'] = _number(crest, nonnegative=True)
        low = signal['frequency_hz'] - signal['bandwidth_hz'] / 2
        high = signal['frequency_hz'] + signal['bandwidth_hz'] / 2
        if signal['duty_cycle'] > 1 or low < 0 or not math.isfinite(high):
            raise ValueError('Invalid RF duty/bandwidth')
        return signal
    except (ValueError, TypeError):
        raise _Issue('invalid', 'invalid_rf_input') from None


def _power(value, settings):
    if not isinstance(value, dict):
        raise _Issue('disconnected', 'power_unavailable')
    try:
        voltage = _number(value.get('voltage_v'), positive=True)
        if value.get('enabled') is not True or value.get('valid') is not True:
            raise ValueError('Power is not enabled/valid')
        if voltage < settings.get('voltage_min_v', 0) or voltage > settings.get('voltage_max_v', math.inf):
            raise ValueError('Voltage outside declared policy')
        return {'enabled': True, 'valid': True, 'voltage_v': voltage}
    except (ValueError, TypeError):
        raise _Issue('invalid', 'invalid_power_input') from None


def _environment(value, settings):
    if not isinstance(value,dict): raise _Issue('disconnected','environment_unavailable')
    try:
        temperature=_number(value.get('temperature_c'))
        humidity=_number(value.get('humidity_percent'),nonnegative=True)
        if value.get('valid') is not True or type(value.get('stable')) is not bool or humidity>100:
            raise ValueError('Invalid environment observation')
        if temperature<settings.get('temperature_min_c',-math.inf) or temperature>settings.get('temperature_max_c',math.inf):
            raise ValueError('Environment outside declared temperature interval')
    except (ValueError,TypeError):
        raise _Issue('invalid','invalid_environment_input') from None
    if not value['stable']: raise _Issue('pending','environment_not_stable')


def _table(value, quantity):
    if not isinstance(value, list) or not 1 <= len(value) <= 1000:
        raise ValueError('Invalid correction table')
    previous = -1
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {'frequency_hz', quantity}:
            raise ValueError('Invalid correction entry')
        frequency = _number(entry['frequency_hz'], positive=True)
        _number(entry[quantity], nonnegative=quantity == 'loss_db')
        if frequency <= previous:
            raise ValueError('Correction frequencies must increase')
        previous = frequency


def _at(settings, scalar, table, frequency):
    curve = settings.get(table)
    if curve is None:
        if scalar not in settings:
            raise _Issue('invalid', 'correction_policy_missing')
        return settings[scalar]
    quantity = 'gain_db' if table == 'gain_table' else 'loss_db'
    if not curve[0]['frequency_hz'] <= frequency <= curve[-1]['frequency_hz']:
        raise _Issue('invalid', 'correction_outside_declared_table')
    for entry in curve:
        if frequency == entry['frequency_hz']:
            return entry[quantity]
    for left, right in zip(curve, curve[1:]):
        if left['frequency_hz'] < frequency < right['frequency_hz']:
            ratio = (frequency-left['frequency_hz'])/(right['frequency_hz']-left['frequency_hz'])
            return left[quantity] + ratio*(right[quantity]-left[quantity])
    raise _Issue('invalid', 'correction_unavailable')


class RFDevice:
    def __init__(self, profile, seed):
        if not isinstance(profile, dict) or profile.get('role') not in ROLE_PORTS or type(seed) is not int:
            raise ValueError('Unsupported RF profile/seed')
        self.role, self.profile_id = profile['role'], _text(profile.get('profile_id'))
        self.model = _text(profile.get('model'))
        self.ports = copy.deepcopy(profile.get('ports', ROLE_PORTS[self.role]))
        self.settings = {'enabled': True, 'requires_power': self.role in {'dut','amplifier','lisn'},
                         'requires_environment': self.role == 'dut', 'requires_control': False,
                         'controller_only': False, 'control_selects_route': False, 'attenuator_mode': 'fixed', 'startup_ticks': 1,
                         'settling_ticks': 1, 'acquisition_ticks': 1, 'acquisition_policy': 'triggered',
                         'calibration_valid': False, 'expected_model': self.model, 'assume_cw_crest_zero': False}
        parameters = profile.get('simulation_parameters', {})
        if not isinstance(parameters, dict):
            raise ValueError('Invalid simulation parameters')
        initial_only = {'requires_power','requires_environment','requires_control','controller_only','control_selects_route','attenuator_mode',
                        'voltage_min_v','voltage_max_v','temperature_min_c','temperature_max_c','assume_cw_crest_zero'}
        if set(parameters) - set(_CONFIG[self.role]) - set(_COMMON_CONFIG) - initial_only:
            raise ValueError('Unsupported simulation parameter')
        self.settings.update(copy.deepcopy(parameters))
        self._validate_ports()
        self._validate_configuration(self.settings, required=False)
        self.configured = False
        if parameters:
            try:
                self._validate_configuration(self.settings)
                self.configured = True
            except ValueError:
                pass
        self._faults = {}
        self._route = self._pending_route = None
        self._due_tick = None
        self._transmitting = False
        self._requested_tx = False
        self._acquisition = self._measurement = None
        self._measurement_fingerprint = None
        self._last_revision = -1
        self._publish('invalid', 'unconfigured', reason='configuration_required')

    def _validate_ports(self):
        if not isinstance(self.ports, dict) or set(self.ports) != {'inputs','outputs'}:
            raise ValueError('Invalid RF port maps')
        ins, outs = self.ports['inputs'], self.ports['outputs']
        if not all(isinstance(group, dict) for group in (ins, outs)):
            raise ValueError('Invalid RF port map')
        if self.role == 'splitter':
            count = len(outs)
            if count not in {2,4} or outs != {f'rf_{i}':'rf' for i in range(1,count+1)} or ins != {'rf':'rf'}:
                raise ValueError('Unsupported splitter ports')
            self.settings.setdefault('ways', count)
        elif self.role == 'rf_switch':
            if self.settings['controller_only']:
                if ins not in ({}, {'control':'control'}) or outs != {'control':'control'}:
                    raise ValueError('Controller-only profile cannot carry RF')
            else:
                routes = {name:kind for name,kind in ins.items() if name != 'control'}
                if (not routes or len(routes)>16 or any(not name.startswith('rf_') or kind!='rf' for name,kind in routes.items())
                        or 'control' in ins and ins['control']!='control' or outs != {'rf':'rf'}):
                    raise ValueError('Unsupported RF matrix ports')
            if self.settings['control_selects_route'] and (self.settings['controller_only'] or ins.get('control')!='control'):
                raise ValueError('Controller-driven RF matrix requires a declared control input')
        elif self.ports != ROLE_PORTS[self.role]:
            raise ValueError('Unsupported role ports')

    def _validate_configuration(self, settings, required=True):
        for name in ('enabled','requires_power','requires_environment','requires_control','controller_only','control_selects_route','calibration_valid','assume_cw_crest_zero'):
            if type(settings[name]) is not bool:
                raise ValueError('Expected boolean policy')
        for name in ('startup_ticks','settling_ticks','acquisition_ticks'):
            if type(settings[name]) is not int or not 1 <= settings[name] <= 1000000:
                raise ValueError('Invalid virtual duration')
        for key in ('loss_db','attenuation_db','through_loss_db','coupling_db'):
            if key in settings: _number(settings[key], nonnegative=True)
        for key in ('gain_db','max_input_dbm','max_output_dbm','temperature_min_c','temperature_max_c'):
            if key in settings: _number(settings[key])
        for key in ('band_min_hz','band_max_hz','voltage_min_v','voltage_max_v'):
            if key in settings: _number(settings[key], positive=True)
        if 'band_min_hz' in settings and 'band_max_hz' in settings and settings['band_min_hz'] >= settings['band_max_hz']:
            raise ValueError('Invalid frequency interval')
        if settings.get('voltage_min_v',0)>settings.get('voltage_max_v',math.inf): raise ValueError('Invalid voltage interval')
        if settings.get('temperature_min_c',-math.inf)>settings.get('temperature_max_c',math.inf): raise ValueError('Invalid temperature interval')
        _text(settings['expected_model'])
        if settings['acquisition_policy'] not in {'triggered','continuous'}: raise ValueError('Unknown acquisition policy')
        for table, quantity in (('loss_table','loss_db'),('gain_table','gain_db')):
            if table in settings: _table(settings[table], quantity)
        if settings['attenuator_mode'] not in {'fixed','step'}:
            raise ValueError('Unknown attenuator mode')
        if 'steps_db' in settings:
            steps = settings['steps_db']
            if not isinstance(steps,list) or not steps or len(steps)>1000:
                raise ValueError('Missing synthetic step policy')
            for step in steps: _number(step, nonnegative=True)
            if sorted(set(steps)) != steps: raise ValueError('Invalid synthetic step policy')
        if 'routes' in settings:
            routes=settings['routes']
            if not isinstance(routes,list) or not routes or len(routes)>16 or len(set(routes))!=len(routes):
                raise ValueError('Invalid controller routes')
            for route in routes: _text(route)
        if not required: return
        if self.role=='attenuator':
            _number(settings.get('attenuation_db'), nonnegative=True)
            if settings['attenuator_mode']=='step':
                if settings.get('attenuation_db') not in settings.get('steps_db',[]) or 'loss_table' in settings:
                    raise ValueError('Step policy missing or unsupported combined curve')
        elif self.role=='coupler':
            a=_number(settings.get('through_loss_db'),nonnegative=True)
            b=_number(settings.get('coupling_db'),nonnegative=True)
            if 10**(-a/10)+10**(-b/10)>1+1e-12:
                raise ValueError('Coupler policy would create RF power')
        elif self.role=='amplifier':
            if 'gain_db' not in settings and 'gain_table' not in settings: raise ValueError('Gain policy missing')
        elif self.role in {'splitter','antenna','filter','lisn','rf_switch'} and not (self.role=='rf_switch' and settings['controller_only']):
            if 'loss_db' not in settings and 'loss_table' not in settings: raise ValueError('Loss policy missing')
            if self.role=='splitter' and (type(settings.get('ways')) is not int or settings['ways']!=len(self.ports['outputs'])):
                raise ValueError('Splitter ways disagree with declared ports')
            if self.role=='antenna': _number(settings.get('gain_db'))
            if self.role=='filter' and not {'band_min_hz','band_max_hz'}<=set(settings): raise ValueError('Filter band missing')
        elif self.role=='dut':
            for name in ('frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation'):
                if name not in settings: raise ValueError('DUT configuration missing')
            try:
                _rf_signal({**settings,'valid':True,'status':'ok','source_id':self.profile_id},settings['assume_cw_crest_zero'])
            except _Issue:
                raise ValueError('Invalid DUT signal policy') from None

    def _publish(self, status, state, *, outputs=None, reason=None, **values):
        self._cached = {'status': status, 'values': {'state': state, 'outputs': outputs or {},
                                                   'configured': self.configured, **values}}
        if reason is not None: self._cached['values']['reason'] = reason

    def _response(self, status=None, changed=False):
        return {**copy.deepcopy(self._cached), 'status': status or self._cached['status'], 'setup_changed': changed}

    def _parameters(self, action, parameters):
        schema=ROLE_ACTIONS[self.role].get(action)
        if schema is None: raise _Issue('unsupported','unsupported_action')
        if not isinstance(parameters,dict) or set(parameters)-set(schema['parameters']): raise _Issue('invalid','invalid_parameters')
        for name,rule in schema['parameters'].items():
            if name not in parameters:
                if rule['required']: raise _Issue('invalid','missing_parameter')
                continue
            value=parameters[name]; kind=rule['type']
            valid=(kind=='number' and type(value) in {int,float} and math.isfinite(value) or
                   kind=='integer' and type(value) is int or kind=='boolean' and type(value) is bool or
                   kind=='string' and isinstance(value,str) and bool(value.strip()) or kind=='array' and isinstance(value,list))
            if not valid: raise _Issue('invalid','invalid_parameter_type')

    def _clear_activity(self):
        self._requested_tx=False; self._transmitting=False; self._due_tick=None; self._pending_route=None
        self._acquisition=None; self._measurement=None; self._measurement_fingerprint=None

    def perform(self, action, parameters, *, tick, setup_revision, inputs):
        try:
            if type(tick) is not int or tick<0 or type(setup_revision) is not int or setup_revision<0 or not isinstance(inputs,dict):
                raise _Issue('invalid','invalid_clock_or_context')
            self._parameters(action,parameters)
            if self._faults.get('disconnect'): raise _Issue('disconnected','device_unavailable')
            if action=='configure':
                candidate={**self.settings,**copy.deepcopy(parameters)}
                self._validate_configuration(candidate)
                if self.configured and self.role=='attenuator' and self.settings['attenuator_mode']=='fixed' and candidate.get('attenuation_db')!=self.settings.get('attenuation_db'):
                    raise _Issue('unsupported','fixed_attenuation_cannot_change')
                changed=not self.configured or candidate!=self.settings
                if changed:
                    self.settings=candidate; self.configured=True; self._clear_activity()
                    if self.role=='rf_switch' and self._route not in self._routes():
                        self._route=None
                    self._publish('ok','configured')
                return self._response('ok',changed)
            if action=='reset':
                self._clear_activity(); self._route=None
                self._publish('ok','configured' if self.configured else 'unconfigured')
                return self._response('ok',True)
            if action=='enable':
                changed=self.settings['enabled']!=parameters['enabled']; self.settings['enabled']=parameters['enabled']
                if changed:
                    self._clear_activity(); self._publish('ok','configured' if self.configured else 'unconfigured')
                return self._response('ok',changed)
            if action=='read':
                self.advance(tick=tick,setup_revision=setup_revision,inputs=inputs)
                return self._response()
            if action=='stop':
                changed=self._requested_tx or self._transmitting or self._due_tick is not None
                self._clear_activity(); self._publish('ok','configured' if self.configured else 'unconfigured')
                return self._response('ok',changed)
            if not self.configured: raise _Issue('invalid','configuration_required')
            if action=='start':
                if not self.settings['enabled']: raise _Issue('invalid','output_disabled')
                if self._requested_tx:
                    self.advance(tick=tick,setup_revision=setup_revision,inputs=inputs)
                    return self._response()
                try:
                    self._dut_prerequisites(inputs)
                except _Issue as error:
                    if error.status!='pending': raise
                    self._requested_tx=True; self._due_tick=None
                    self._publish('pending','waiting',reason=error.reason)
                    return self._response('pending',True)
                self._requested_tx=True; self._due_tick=tick+self.settings['startup_ticks']
                self._publish('pending','arming'); return self._response('pending',True)
            if action=='acquire':
                signal=self._sensor_signal(inputs)
                self._measurement=None; self._measurement_fingerprint=None
                self._begin_sensor(signal,tick,setup_revision)
                self._publish('pending','acquiring'); return self._response('pending')
            if action=='set_attenuation':
                if self.settings['attenuator_mode']!='step': raise _Issue('unsupported','fixed_attenuation_cannot_change')
                value=parameters['attenuation_db']
                if value not in self.settings['steps_db']: raise _Issue('invalid','undeclared_attenuation_step')
                changed=value!=self.settings['attenuation_db']; self.settings['attenuation_db']=value
                self._publish('ok','configured'); return self._response('ok',changed)
            if action=='select_path':
                route=parameters['input_port']
                if route not in self._routes(): raise _Issue('invalid','undeclared_route')
                if route==self._pending_route: return self._response('pending')
                if route==self._route and self._pending_route is None: return self._response('ok')
                self._pending_route=route; self._due_tick=tick+self.settings['settling_ticks']
                self._publish('pending','settling'); return self._response('pending',True)
            raise _Issue('unsupported','role_action_not_implemented')
        except _Issue as error:
            return {'status':error.status,'values':{'state':self._cached['values']['state'],'outputs':{},'reason':error.reason},'setup_changed':False}
        except (ValueError,TypeError,KeyError,OverflowError):
            return {'status':'invalid','values':{'state':self._cached['values']['state'],'outputs':{},'reason':'invalid_configuration'},'setup_changed':False}

    def _routes(self):
        if self.settings['controller_only']: return self.settings.get('routes',['rf_1','rf_2'])
        return [name for name,kind in self.ports['inputs'].items() if kind=='rf']

    def _control(self, inputs):
        if 'control' not in inputs and not self.settings['requires_control']: return
        value=inputs.get('control')
        if not isinstance(value,dict): raise _Issue('disconnected','control_unavailable')
        if value.get('valid') is not True or value.get('enabled') is not True: raise _Issue('invalid','invalid_control_input')

    def _input(self, inputs, port='rf'):
        if port not in inputs: raise _Issue('disconnected','rf_input_unavailable')
        signal=_rf_signal(inputs[port],self.settings['assume_cw_crest_zero'])
        low=signal['frequency_hz']-signal['bandwidth_hz']/2; high=signal['frequency_hz']+signal['bandwidth_hz']/2
        if low<self.settings.get('band_min_hz',0) or high>self.settings.get('band_max_hz',math.inf): raise _Issue('invalid','out_of_band')
        if signal['power_dbm']>self.settings.get('max_input_dbm',math.inf): raise _Issue('error','input_overload')
        return signal

    def _shift(self, signal, delta):
        value=signal['power_dbm']+delta
        if not math.isfinite(value) or value>self.settings.get('max_output_dbm',math.inf): raise _Issue('error','output_overload')
        return {**signal,'power_dbm':value}

    def _dut_prerequisites(self, inputs):
        if self.settings['requires_power']: _power(inputs.get('power'),self.settings)
        self._control(inputs)
        if self.settings['requires_environment']: _environment(inputs.get('environment'),self.settings)

    def _dut(self, inputs, tick):
        self._dut_prerequisites(inputs)
        if self._due_tick is None: self._due_tick=tick+self.settings['startup_ticks']
        if tick<self._due_tick: raise _Issue('pending','transmitter_starting')
        signal=_rf_signal({**self.settings,'valid':True,'status':'ok','source_id':self.profile_id},self.settings['assume_cw_crest_zero'])
        # Check the configured signal interval, never infer a manufacturer band.
        low=signal['frequency_hz']-signal['bandwidth_hz']/2; high=signal['frequency_hz']+signal['bandwidth_hz']/2
        if low<self.settings.get('band_min_hz',0) or high>self.settings.get('band_max_hz',math.inf): raise _Issue('invalid','out_of_band')
        if signal['power_dbm']>self.settings.get('max_output_dbm',math.inf): raise _Issue('error','output_overload')
        self._transmitting=True
        return {'rf':signal}

    def _sensor_signal(self, inputs):
        if not self.settings['calibration_valid']: raise _Issue('invalid','calibration_unavailable')
        if self.settings['expected_model']!=self.model or self._faults.get('model_mismatch') or self._faults.get('measurement_invalid'):
            raise _Issue('invalid','measurement_not_valid')
        return self._input(inputs)

    def _begin_sensor(self, signal, tick, revision):
        self._acquisition={'due_tick':tick+self.settings['acquisition_ticks'],'revision':revision,
                           'fingerprint':json.dumps(signal,sort_keys=True),'signal':copy.deepcopy(signal)}

    def _sensor(self, inputs, tick, revision):
        signal=self._sensor_signal(inputs)
        fingerprint=json.dumps(signal,sort_keys=True)
        continuous=self.settings['acquisition_policy']=='continuous'
        if self._acquisition is not None:
            capture=self._acquisition
            if capture['revision']!=revision or capture['fingerprint']!=fingerprint:
                self._acquisition=None; self._measurement=None; self._measurement_fingerprint=None
                if continuous:
                    self._begin_sensor(signal,tick,revision)
                    self._publish('pending','acquiring'); return
                raise _Issue('invalid','acquisition_context_changed')
            if tick>=capture['due_tick']:
                self._measurement={'status':'ok','valid':True,'value':signal['power_dbm'],'unit':'dBm',
                                   'frequency_hz':signal['frequency_hz'],'power_dbm':signal['power_dbm'],
                                   'duty_cycle':signal['duty_cycle'],'crest_factor_db':signal['crest_factor_db'],
                                   'acquisition_tick':tick,'acquisition_setup_revision':revision,'source_id':self.profile_id}
                self._measurement_fingerprint=fingerprint; self._acquisition=None
                if continuous: self._begin_sensor(signal,tick,revision)
            elif self._measurement is None:
                self._publish('pending','acquiring'); return
        if self._measurement is not None:
            if self._measurement['acquisition_setup_revision']!=revision or self._measurement_fingerprint!=fingerprint:
                self._measurement=None; self._measurement_fingerprint=None
                if continuous:
                    self._begin_sensor(signal,tick,revision)
                    self._publish('pending','acquiring'); return
                raise _Issue('invalid','acquisition_context_changed')
            self._publish('ok','sampling' if continuous else 'complete',outputs={'measurement':copy.deepcopy(self._measurement)})
            return
        if continuous:
            self._begin_sensor(signal,tick,revision); self._publish('pending','acquiring'); return
        raise _Issue('invalid','acquisition_required')

    def _path(self, inputs, tick):
        if self.role=='rf_switch':
            self._control(inputs)
            if self.settings['control_selects_route']:
                control=inputs.get('control')
                if not isinstance(control,dict): raise _Issue('disconnected','control_unavailable')
                selected=control.get('selected_input')
                if selected not in self._routes(): raise _Issue('invalid','undeclared_control_route')
                if selected==self._route:
                    self._pending_route=None; self._due_tick=None
                elif selected!=self._pending_route:
                    self._pending_route=selected; self._due_tick=tick+self.settings['settling_ticks']
            if self._pending_route is not None:
                if tick<self._due_tick or self._faults.get('stuck'): raise _Issue('pending','settling')
                self._route=self._pending_route; self._pending_route=None; self._due_tick=None
            if self._route is None: raise _Issue('invalid','route_not_selected')
            if self.settings['controller_only']:
                return {'control':{'status':'ok','valid':True,'enabled':True,'selected_input':self._route,'source_id':self.profile_id}}
            signal=self._input(inputs,self._route)
        else:
            if self.settings['requires_power']: _power(inputs.get('power'),self.settings)
            signal=self._input(inputs)
        frequency=signal['frequency_hz']
        if self.role=='amplifier':
            return {'rf':self._shift(signal,_at(self.settings,'gain_db','gain_table',frequency))}
        if self.role=='coupler':
            return {'rf':self._shift(signal,-self.settings['through_loss_db']),
                    'coupled':self._shift(signal,-self.settings['coupling_db'])}
        key='attenuation_db' if self.role=='attenuator' else 'loss_db'
        loss=_at(self.settings,key,'loss_table',frequency)
        if self.role=='splitter':
            return {name:self._shift(signal,-loss-10*math.log10(self.settings['ways'])) for name in self.ports['outputs']}
        result={'rf':self._shift(signal,(self.settings['gain_db'] if self.role=='antenna' else 0)-loss)}
        if self.role=='lisn': result['power']=_power(inputs.get('power'),self.settings)
        return result

    def advance(self, *, tick, setup_revision, inputs):
        if type(tick) is not int or tick<0 or type(setup_revision) is not int or setup_revision<0 or not isinstance(inputs,dict):
            raise ValueError('Invalid trusted RF clock/context')
        self._last_revision=setup_revision
        try:
            if self._faults.get('disconnect'): raise _Issue('disconnected','device_unavailable')
            if self._faults.get('fault'): raise _Issue('error','device_unavailable')
            if not self.configured: raise _Issue('invalid','configuration_required')
            if not self.settings['enabled']: raise _Issue('invalid','output_disabled')
            if self._faults.get('no_output'): raise _Issue('invalid','signal_unavailable')
            if self.role=='dut':
                if not self._requested_tx:
                    self._publish('ok','idle'); return
                outputs=self._dut(inputs,tick)
            elif self.role=='power_sensor':
                self._sensor(inputs,tick,setup_revision); return
            else:
                outputs=self._path(inputs,tick)
            self._publish('ok','transmitting' if self.role=='dut' else 'active',outputs=outputs,
                          controller_only=self.settings['controller_only'] if self.role=='rf_switch' else False)
        except _Issue as error:
            if self.role=='dut':
                self._transmitting=False
                if error.status=='pending' and error.reason=='environment_not_stable': self._due_tick=None
                elif error.status!='pending': self._clear_activity()
            if self.role=='power_sensor' and error.status!='pending':
                self._acquisition=None; self._measurement=None; self._measurement_fingerprint=None
            self._publish(error.status,'settling' if error.status=='pending' else 'unavailable',reason=error.reason)

    def observation(self, *, tick, setup_revision):
        if type(tick) is not int or tick<0 or type(setup_revision) is not int or setup_revision<0:
            raise ValueError('Invalid trusted RF clock/context')
        result=copy.deepcopy(self._cached)
        if self._last_revision!=setup_revision and result['values']['outputs']:
            result['status']='invalid'; result['values'].update(outputs={},reason='setup_revision_changed')
        return result

    def author_control(self, fault, value):
        allowed={'disconnect','fault','no_output'}
        if self.role=='rf_switch': allowed.add('stuck')
        if self.role=='power_sensor': allowed.update({'measurement_invalid','model_mismatch'})
        if fault not in allowed or type(value) is not bool: raise ValueError('Unsupported author control')
        self._faults[fault]=value
        if value:
            if fault=='stuck':
                self._publish('pending' if self._pending_route is not None else 'invalid','settling',reason='device_unavailable')
            else:
                self._clear_activity()
                self._publish('disconnected' if fault=='disconnect' else 'invalid','unavailable',reason='device_unavailable')
        else:
            self._publish('invalid','awaiting_fresh_observation',reason='fresh_observation_required')


def _factory(role):
    def create(profile, seed):
        if profile.get('role')!=role: raise ValueError('Factory role mismatch')
        return RFDevice(profile,seed)
    return create


DEVICE_FACTORIES = {role:_factory(role) for role in ROLE_PORTS}
