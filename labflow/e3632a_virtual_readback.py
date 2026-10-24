"""One bounded public snapshot and optional measurement of a built-in virtual supply."""
import copy
import hashlib
import itertools
import json
import math
import random
import re
import threading
from collections import deque
from types import FunctionType

from labflow.virtual_fleet import core, facility, instruments, rf


_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_PROFILES = {
    'e3632a-ba5f7c3ee5': ('Agilent', '2279d6849e73189424a732b918dd295836d79f0c0f8c87b7e8dfed5e1899efab'),
    'e3632a-ebca10ffe2': ('H.P', '1a5cef4d5e89f3624858ef66322fcfd437a8fa71ac28b2ce81219caf59e44d99'),
}
_SNAPSHOT_BYTES, _SNAPSHOT_DEPTH = 256 * 1024, 32
_PACKET_BYTES, _PACKET_DEPTH = 16 * 1024, 16
_RECEIPT_BYTES, _RECEIPT_DEPTH = 16 * 1024, 16
_AUTHOR_BYTES, _AUTHOR_DEPTH = 64 * 1024, 24
_NAMESPACES = itertools.count(1)
_RLOCK_TYPE = type(threading.RLock())
_DUMPS, _LOADS, _FINITE, _HASH = json.dumps, json.loads, math.isfinite, hashlib.sha256
_ELECTRICAL = frozenset({'voltage_v', 'current_a', 'mode', 'acquisition_tick', 'acquisition_revision'})
_ENVELOPE = frozenset({'status', 'values', 'tick', 'setup_revision', 'synthetic',
                       'hardware_verified', 'device_id', 'profile_id', 'role'})
_VERIFICATION = {
    'synthetic': True, 'hardware_verified': False, 'ai_verified': False,
    'vendor_binary_executed': False, 'output_off_verified': False,
    'rf_off_verified': False, 'safe_state_verified': False,
    'model_limits': 'not_assessed', 'calibration': 'not_assessed',
    'oem_support': 'not_assessed', 'firmware_options': 'not_assessed',
    'physical_model': 'not_assessed',
}


class _Invalid(Exception):
    pass


class _Budget(_Invalid):
    pass


class _Stop(Exception):
    def __init__(self, reason):
        self.reason = reason


def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _walk(value, depth_limit, *, typed=False, remaining=None, depth=0):
    """Inspect exact data types before serialization; never call object hooks."""
    if remaining is None:
        remaining = [200000 if typed else 100000]
    remaining[0] -= 1
    if depth > depth_limit or remaining[0] < 0:
        raise _Budget
    kind = type(value)
    if value is None or kind is bool:
        return
    if kind is str:
        if len(value) > 1024 * 1024:
            raise _Budget
        return
    if kind is int:
        if value.bit_length() > 4096:
            raise _Budget
        return
    if kind is float and _FINITE(value):
        return
    if kind is dict:
        if len(value) > remaining[0]:
            raise _Budget
        for key, child in value.items():
            if not typed and type(key) is not str:
                raise _Invalid
            _walk(key, depth_limit, typed=typed, remaining=remaining, depth=depth + 1)
            _walk(child, depth_limit, typed=typed, remaining=remaining, depth=depth + 1)
        return
    sequences = (list, tuple, set, frozenset, deque) if typed else (list,)
    if kind in sequences:
        if len(value) > remaining[0]:
            raise _Budget
        for child in value:
            _walk(child, depth_limit, typed=typed, remaining=remaining, depth=depth + 1)
        return
    if typed and kind is random.Random:
        _walk(vars(value), depth_limit, typed=True, remaining=remaining, depth=depth + 1)
        return
    raise _Invalid


def _pack(value, max_bytes, max_depth):
    _walk(value, max_depth)
    try:
        data = _DUMPS(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        raise _Invalid from None
    if len(data) > max_bytes:
        raise _Budget
    return data


def _packet(value, max_bytes, max_depth):
    return _LOADS(_pack(value, max_bytes, max_depth))


def _constant(value):
    """Stable, typed signature for built-in module data, never arbitrary objects."""
    _walk(value, 48, typed=True)
    def convert(item):
        kind = type(item)
        if kind is dict:
            return ('dict', tuple(sorted((convert(k), convert(v)) for k, v in item.items())))
        if kind in (list, tuple, deque):
            return (kind.__name__, tuple(convert(v) for v in item))
        if kind in (set, frozenset):
            return (kind.__name__, tuple(sorted(convert(v) for v in item)))
        return (kind.__name__, item)
    return convert(value)


# execute('measure') propagates every node, so its complete built-in role path
# is checked, not merely the selected supply. Capture code as well as identity.
_MODULES = (core, facility, instruments, rf)
_MODULE_BINDINGS = {
    module: {k: v for k, v in vars(module).items() if not k.startswith('__')}
    for module in _MODULES
}
_CLASSES = (core.VirtualFleet, facility._Facility, facility.PowerSupply,
            facility.TemperatureChamber, facility.PositionDevice, facility.InspectionMicroscope,
            rf.RFDevice, rf._Issue, instruments._Instrument, instruments._InputError, random.Random)
_CLASS_BINDINGS = {cls: dict(vars(cls)) for cls in _CLASSES}
_FUNCTIONS = []
for _bindings in (*_MODULE_BINDINGS.values(), *_CLASS_BINDINGS.values()):
    for _member in _bindings.values():
        if type(_member) is property:
            _member = _member.fget
        if type(_member) is FunctionType and all(_member is not f[0] for f in _FUNCTIONS):
            _FUNCTIONS.append((_member, _member.__code__, _constant(_member.__defaults__),
                               _constant(_member.__kwdefaults__)))
_CONSTANTS = []
for _module, _bindings in _MODULE_BINDINGS.items():
    for _name, _member in _bindings.items():
        try:
            _signature = _constant(_member)
        except _Invalid:
            continue
        _CONSTANTS.append((_module, _name, _signature))
_LIBRARY = ((copy, 'deepcopy', copy.deepcopy), (json, 'dumps', json.dumps),
            (json, 'loads', json.loads), (hashlib, 'sha256', hashlib.sha256),
            (instruments.bisect, 'bisect_left', instruments.bisect.bisect_left),
            (random, 'Random', random.Random)) + tuple(
                (math, name, getattr(math, name))
                for name in ('isfinite', 'isclose', 'exp', 'log10', 'log2'))
for _module, _name, _member in _LIBRARY:
    if type(_member) is FunctionType and all(_member is not f[0] for f in _FUNCTIONS):
        _FUNCTIONS.append((_member, _member.__code__, _constant(_member.__defaults__),
                           _constant(_member.__kwdefaults__)))
_ACTIONS = {**copy.deepcopy(facility.ROLE_ACTIONS), **copy.deepcopy(rf.ROLE_ACTIONS),
            **copy.deepcopy(instruments.ROLE_ACTIONS)}
_ROLE_TYPES = {role: facility.DEVICE_FACTORIES[role] for role in facility.ROLE_ACTIONS}
_ROLE_TYPES.update(dict.fromkeys(rf.ROLE_ACTIONS, rf.RFDevice))
_ROLE_TYPES.update(dict.fromkeys(instruments.ROLE_ACTIONS, instruments._Instrument))


def _native_path():
    if any(getattr(module, name) is not function for module, name, function in _LIBRARY):
        return False
    for module, saved in _MODULE_BINDINGS.items():
        current = {k: v for k, v in vars(module).items() if not k.startswith('__')}
        if current.keys() != saved.keys() or any(current[k] is not v for k, v in saved.items()):
            return False
    for cls, saved in _CLASS_BINDINGS.items():
        current = vars(cls)
        if current.keys() != saved.keys() or any(current[k] is not v for k, v in saved.items()):
            return False
    for function, code, defaults, kwdefaults in _FUNCTIONS:
        if (function.__code__ is not code or _constant(function.__defaults__) != defaults
                or _constant(function.__kwdefaults__) != kwdefaults):
            return False
    return all(_constant(vars(module)[name]) == signature for module, name, signature in _CONSTANTS)


def _runtime_path(fleet):
    if not _native_path() or type(fleet) is not core.VirtualFleet:
        return False
    state = vars(fleet)
    if type(state.get('_lock')) is not _RLOCK_TYPE or type(state.get('_devices')) is not dict:
        return False
    remaining = [200000]
    for key, value in state.items():
        if key not in ('_lock', '_devices'):
            _walk(value, 48, typed=True, remaining=remaining)
    devices = state['_devices']
    if devices.keys() != state['_nodes'].keys() or set(state['_order']) != devices.keys():
        return False
    for name, device in devices.items():
        node = state['_nodes'][name]
        profile = state['_profiles'][node['profile_id']]
        role = profile['role']
        if (type(device) is not _ROLE_TYPES.get(role)
                or _constant(state['_role_actions'].get(role)) != _constant(_ACTIONS[role])):
            return False
        _walk(vars(device), 48, typed=True, remaining=remaining)
        if device.role != role:
            return False
        if type(device) in (rf.RFDevice, instruments._Instrument) and device.profile_id != profile['profile_id']:
            return False
    return True


def _profile_hash(value):
    return _HASH(_pack(value, _PACKET_BYTES, _PACKET_DEPTH)).hexdigest()


def _binding(fleet, device_id, profile_id=None, device=None):
    state = vars(fleet)
    node = state['_nodes'].get(device_id)
    if type(node) is not dict or node.get('id') != device_id:
        return None
    bound = node.get('profile_id')
    if type(bound) is not str or bound not in _PROFILES or (profile_id is not None and bound != profile_id):
        return None
    profile = state['_profiles'].get(bound)
    target = state['_devices'].get(device_id)
    if device is not None and target is not device:
        return None
    if _profile_hash(profile) != _PROFILES[bound][1]:
        return None
    if type(target) is not facility.PowerSupply:
        return None
    if (_profile_hash(target.profile) != _PROFILES[bound][1] or target.policy != {}
            or any(type(v) is not float for v in (target.minimum, target.maximum, target.current_max))
            or (target.minimum, target.maximum, target.current_max) != (0., 60., 10.)
            or target._output_names != {'power'}
            or state['_profile_ports'].get(bound) != {'inputs': {}, 'outputs': {'power': 'power'}}):
        return None
    return bound


def _context(value):
    if (type(value) is not dict or any(type(value.get(k)) is not int
            or not 0 <= value[k] < 2 ** 63 for k in ('tick', 'setup_revision'))):
        raise _Invalid
    return {k: value[k] for k in ('tick', 'setup_revision')}


def _number(value):
    if type(value) not in (int, float) or not _FINITE(value) or value < 0:
        raise _Invalid


def _envelope(packet, device_id, profile_id, context):
    if (type(packet) is not dict or not _ENVELOPE <= packet.keys()
            or packet['synthetic'] is not True or packet['hardware_verified'] is not False
            or type(packet['device_id']) is not str or packet['device_id'] != device_id
            or type(packet['profile_id']) is not str or packet['profile_id'] != profile_id
            or type(packet['role']) is not str or packet['role'] != 'power_supply'
            or type(packet['status']) is not str or packet['status'] not in core.STATUSES
            or type(packet['values']) is not dict):
        raise _Invalid
    if _context(packet) != context:
        raise _Stop('context_mismatch')


def _electrical(value, context):
    if type(value) is not dict or value.keys() != _ELECTRICAL:
        raise _Invalid
    _number(value['voltage_v'])
    _number(value['current_a'])
    if type(value['mode']) is not str or value['mode'] not in ('constant_voltage', 'constant_current'):
        raise _Invalid
    for key, expected in (('acquisition_tick', context['tick']),
                          ('acquisition_revision', context['setup_revision'])):
        if type(value[key]) is not int or value[key] != expected:
            raise _Stop('context_mismatch')
    return dict(value)


def _validate_observation(snapshot, device_id, profile_id, initial_context):
    if (type(snapshot) is not dict or snapshot.keys() !=
            {'tick', 'setup_revision', 'synthetic', 'hardware_verified', 'devices'}
            or snapshot['synthetic'] is not True or snapshot['hardware_verified'] is not False
            or type(snapshot['devices']) is not dict or device_id not in snapshot['devices']):
        raise _Invalid
    context = _context(snapshot)
    if context != initial_context:
        raise _Stop('context_mismatch')
    packet = snapshot['devices'][device_id]
    _envelope(packet, device_id, profile_id, context)
    if packet.keys() != _ENVELOPE | {'state'} or type(packet['state']) is not str:
        raise _Invalid
    values, state, status = packet['values'], packet['state'], packet['status']
    result = {'configured': None, 'output': None, 'electrical': None, 'context': context, 'reason': None}
    if status == 'disconnected' and state == 'unavailable' and values == {'outputs': {}}:
        result['reason'] = 'device_unavailable'
        return result
    if (status == 'error' and state == 'unavailable'
            and values == {'reason': 'device_contract_error', 'outputs': {}}):
        result['reason'] = 'observation_unavailable'
        return result
    if values.keys() != {'voltage_setpoint_v', 'current_limit_a', 'outputs'}:
        raise _Invalid
    _number(values['voltage_setpoint_v'])
    _number(values['current_limit_a'])
    outputs = values['outputs']
    if type(outputs) is not dict or outputs.keys() != {'power'} or type(outputs['power']) is not dict:
        raise _Invalid
    power = outputs['power']
    if (type(power.get('enabled')) is not bool or type(power.get('valid')) is not bool
            or type(power.get('source_id')) is not str or power['source_id'] != device_id):
        raise _Invalid
    if status == 'ok' and state == 'enabled' and power['enabled'] and power['valid']:
        if power.keys() != _ELECTRICAL | {'enabled', 'valid', 'source_id'}:
            raise _Invalid
        result['electrical'] = _electrical({k: power[k] for k in _ELECTRICAL}, context)
    elif ((status, state) in (('ok', 'off'), ('error', 'protected'))
          and not power['enabled'] and not power['valid']):
        if power.keys() != {'enabled', 'valid', 'source_id', 'voltage_v', 'current_a'}:
            raise _Invalid
        for key in ('voltage_v', 'current_a'):
            _number(power[key])
            if power[key] != 0:
                raise _Invalid
        result['reason'] = 'output_disabled' if state == 'off' else 'output_protected'
    else:
        raise _Invalid
    result['configured'] = {k: values[k] for k in ('voltage_setpoint_v', 'current_limit_a')}
    result['output'] = {'enabled': power['enabled'], 'valid': power['valid'], 'state': state}
    return result


def _validate_measurement(packet, device_id, profile_id, context):
    _envelope(packet, device_id, profile_id, context)
    if packet.get('setup_changed') is not False:
        raise _Stop('context_mismatch')
    if packet['status'] != 'ok':
        if packet.keys() not in (_ENVELOPE | {'setup_changed'}, _ENVELOPE | {'setup_changed', 'state'}):
            raise _Invalid
        allowed = ({'reason': 'output_unavailable'}, {'reason': 'output_disabled'},
                   {'reason': 'device_unavailable'}, {'reason': 'setup_changed_during_action'},
                   {'reason': 'device_contract_error', 'outputs': {}})
        if packet['values'] not in allowed or ('state' in packet and packet['state'] != 'unavailable'):
            raise _Invalid
        raise _Stop('measurement_unavailable')
    if packet.keys() != _ENVELOPE | {'setup_changed'}:
        raise _Invalid
    return _electrical(packet['values'], context)


def _seal(receipt, author):
    return (_pack(receipt, _RECEIPT_BYTES, _RECEIPT_DEPTH),
            _pack(author, _AUTHOR_BYTES, _AUTHOR_DEPTH))


class E3632AVirtualReadback:
    """Bounded historical synthetic receipts; never enables, advances, or recovers."""

    def __init__(self, fleet, device_id):
        if type(fleet) is not core.VirtualFleet:
            raise ValueError('invalid_virtual_fleet')
        if not _identifier(device_id):
            raise ValueError('invalid_device_id')
        code, locked = None, False
        try:
            if not _native_path() or type(vars(fleet).get('_lock')) is not _RLOCK_TYPE:
                code = 'unsafe_callpath'
            else:
                fleet_lock = fleet._lock
                locked = fleet_lock.acquire(blocking=False)
                if not locked:
                    code = 'readback_busy'
                elif not _runtime_path(fleet):
                    code = 'unsafe_callpath'
                elif (profile_id := _binding(fleet, device_id)) is None:
                    code = 'unsupported_supply_profile'
                else:
                    self._device, self._fleet_lock = fleet._devices[device_id], fleet_lock
        except Exception:
            code = 'unsafe_callpath'
        finally:
            if locked:
                fleet_lock.release()
        if code is not None:
            raise ValueError(code)
        self._fleet, self._device_id, self._profile_id = fleet, device_id, profile_id
        self._lock, self._entries = threading.Lock(), {}
        self._namespace = next(_NAMESPACES)

    def _base(self, request_id):
        return {
            'schema_version': 1, 'kind': 'e3632a_virtual_readback', 'request_id': request_id,
            'device_id': self._device_id, 'profile_id': self._profile_id,
            'manufacturer_as_recorded': _PROFILES[self._profile_id][0], 'model': 'E3632A',
            'profile_sha256': _PROFILES[self._profile_id][1], 'status': 'unconfirmed',
            'reason_codes': [], 'configured': None, 'output': None, 'measurement': None,
            'initial_context': None, 'observation_context': None, 'measurement_context': None,
            'observation_reads': 0, 'observation_method': 'fleet.observations', 'commands': [],
            'simulation_basis': 'existing_role_domain_model', 'observation_scope': 'historical_observation',
            'current_authority': False, 'verification': dict(_VERIFICATION),
            'role_policy_defaults': {'voltage_max_v': 60, 'current_max_a': 10,
                                    'scope': 'generic_role_policy_not_model_ratings'},
            'resumable': False,
        }

    def _gate(self):
        try:
            if not _native_path():
                return 'unsafe_callpath'
            if self._fleet._lock is not self._fleet_lock:
                return 'unsafe_callpath'
            if not _runtime_path(self._fleet):
                return 'unsafe_callpath'
            if _binding(self._fleet, self._device_id, self._profile_id, self._device) is None:
                return 'binding_changed'
        except Exception:
            return 'unsafe_callpath'
        return None

    def _observe(self, entry):
        receipt = entry['receipt']
        reason = self._gate()
        if reason:
            raise _Stop(reason)
        try:
            receipt['initial_context'] = _context({'tick': self._fleet._tick,
                                                   'setup_revision': self._fleet._revision})
        except _Invalid:
            raise _Stop('context_mismatch') from None
        frame = {'method': 'fleet.observations', 'attempted': True, 'packet': None, 'error': None}
        receipt['observation_reads'] = 1
        entry['observations'].append(frame)
        try:
            raw = self._fleet.observations()
        except Exception:
            frame['error'] = 'observation_exception'
            raise _Stop(frame['error']) from None
        try:
            snapshot = _packet(raw, _SNAPSHOT_BYTES, _SNAPSHOT_DEPTH)
            selected = snapshot.get('devices', {}).get(self._device_id) if type(snapshot) is dict else None
            frame['packet'] = _packet(selected, _PACKET_BYTES, _PACKET_DEPTH)
        except _Budget:
            frame['error'] = 'observation_budget_exceeded'
            raise _Stop(frame['error']) from None
        except Exception:
            frame['error'] = 'observation_packet_invalid'
            raise _Stop(frame['error']) from None
        try:
            observed = _validate_observation(snapshot, self._device_id, self._profile_id,
                                             receipt['initial_context'])
        except _Stop as stop:
            frame['error'] = stop.reason
            raise
        except Exception:
            frame['error'] = 'observation_packet_invalid'
            raise _Stop(frame['error']) from None
        receipt['observation_context'] = observed['context']
        receipt['configured'], receipt['output'] = observed['configured'], observed['output']
        if observed['reason']:
            frame['error'] = observed['reason']
            raise _Stop(observed['reason'])
        reason = self._gate()
        if reason:
            raise _Stop(reason)
        if _context({'tick': self._fleet._tick, 'setup_revision': self._fleet._revision}) != observed['context']:
            raise _Stop('context_mismatch')
        child_id = 'e3632a:' + str(self._namespace) + ':' + _HASH(
            receipt['request_id'].encode('ascii')).hexdigest()
        command = {'request_id': child_id, 'device_id': self._device_id, 'action': 'measure',
                   'parameters': {}, 'attempted': True}
        # Set before dispatch. Exceptions cannot prove whether perform ran.
        receipt['commands'].append(command)
        command_frame = dict(command, packet=None, error=None)
        entry['commands'].append(command_frame)
        try:
            raw = self._fleet.execute(child_id, self._device_id, 'measure', {})
        except Exception:
            command_frame['error'] = 'measure_exception'
            raise _Stop(command_frame['error']) from None
        try:
            packet = _packet(raw, _PACKET_BYTES, _PACKET_DEPTH)
            command_frame['packet'] = packet
        except _Budget:
            command_frame['error'] = 'measurement_budget_exceeded'
            raise _Stop(command_frame['error']) from None
        except Exception:
            command_frame['error'] = 'measurement_packet_invalid'
            raise _Stop(command_frame['error']) from None
        try:
            measurement = _validate_measurement(packet, self._device_id, self._profile_id, observed['context'])
            receipt['measurement_context'] = _context(packet)
            if (_context({'tick': self._fleet._tick, 'setup_revision': self._fleet._revision})
                    != observed['context']):
                raise _Stop('context_mismatch')
            if measurement != observed['electrical']:
                raise _Stop('measurement_mismatch')
        except _Stop as stop:
            command_frame['error'] = stop.reason
            raise
        except Exception:
            command_frame['error'] = 'measurement_packet_invalid'
            raise _Stop(command_frame['error']) from None
        receipt['measurement'], receipt['status'] = measurement, 'observed_synthetic'

    def _finish(self, entry):
        receipt = entry['receipt']
        author = {'schema_version': 1, 'kind': 'e3632a_virtual_readback_author',
                  'request_id': receipt['request_id'], 'scope': 'trusted_author_only',
                  'operator_receipt': receipt, 'observation_frames': entry['observations'],
                  'command_frames': entry['commands'], 'diagnostics': list(receipt['reason_codes'])}
        try:
            encoded = _seal(receipt, author)
        except Exception:
            # Preserve the actual call prefix and retained original frames. No retry.
            receipt['status'], receipt['measurement'] = 'unconfirmed', None
            receipt['reason_codes'] = ['preservation_failed']
            author['diagnostics'] = ['preservation_failed']
            try:
                encoded = (_pack(receipt, _RECEIPT_BYTES, _RECEIPT_DEPTH),
                           _pack(author, _AUTHOR_BYTES, _AUTHOR_DEPTH))
            except Exception:
                # A bounded failure record still retains attempts, never a not-sent claim.
                receipt['configured'] = receipt['output'] = None
                for frame in (*entry['observations'], *entry['commands']):
                    frame['packet'], frame['error'] = None, 'preservation_failed'
                encoded = (_pack(receipt, _RECEIPT_BYTES, _RECEIPT_DEPTH),
                           _pack(author, _AUTHOR_BYTES, _AUTHOR_DEPTH))
        entry['encoded'] = encoded

    def observe(self, request_id):
        if not _identifier(request_id):
            raise ValueError('invalid_request_id')
        if not self._lock.acquire(blocking=False):
            raise ValueError('readback_busy')
        entry = None
        fleet_locked = False
        try:
            if request_id in self._entries:
                return _LOADS(self._entries[request_id]['encoded'][0])
            if len(self._entries) >= 128:
                raise ValueError('receipt_limit_reached')
            fleet_locked = self._fleet_lock.acquire(blocking=False)
            if not fleet_locked:
                raise ValueError('readback_busy')
            entry = {'receipt': self._base(request_id), 'observations': [], 'commands': []}
            # Reserve before either call; a failed first call is also historical.
            self._entries[request_id] = entry
            try:
                self._observe(entry)
            except _Stop as stop:
                entry['receipt']['reason_codes'] = [stop.reason]
            except Exception:
                entry['receipt']['reason_codes'] = ['preservation_failed']
            finally:
                if entry['receipt']['status'] != 'observed_synthetic':
                    entry['receipt']['measurement'] = None
                if not entry['receipt']['reason_codes'] and entry['receipt']['status'] == 'unconfirmed':
                    entry['receipt']['reason_codes'] = ['preservation_failed']
                self._finish(entry)
            return _LOADS(entry['encoded'][0])
        finally:
            if fleet_locked:
                self._fleet_lock.release()
            self._lock.release()

    def author_record(self, request_id):
        if not _identifier(request_id):
            raise ValueError('invalid_request_id')
        if not self._lock.acquire(blocking=False):
            raise ValueError('readback_busy')
        try:
            if request_id not in self._entries:
                raise ValueError('readback_record_not_found')
            return _LOADS(self._entries[request_id]['encoded'][1])
        finally:
            self._lock.release()
