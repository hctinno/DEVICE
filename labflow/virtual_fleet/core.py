"""Factory-injected virtual DAG runtime; never opens a transport or file."""

import hashlib
import json
import math
import re
import threading
from collections import deque


STATUSES = frozenset({'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'})
PORT_KINDS = frozenset({'rf', 'power', 'environment', 'position', 'control', 'measurement', 'data'})
PARAMETER_TYPES = frozenset({'number', 'integer', 'boolean', 'string', 'object', 'array'})
MAX_JSON_BYTES = 1024 * 1024
MAX_DEVICE_RESULT_BYTES = 256 * 1024
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_REQUESTS = 5000
MAX_HISTORY = 10000
MAX_DEVICES = 256
MAX_PROFILES = 512
MAX_CONNECTIONS = 4096
MAX_ADVANCE_TICKS = 10000
_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')


def _json_copy(value):
    def validate(item, depth=0):
        if depth > 64:
            raise ValueError('JSON nesting limit exceeded')
        if item is None or type(item) in (bool, str, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                validate(child, depth + 1)
            return
        if type(item) is dict and all(isinstance(key, str) for key in item):
            for child in item.values():
                validate(child, depth + 1)
            return
        raise ValueError('a finite JSON tree with string keys is required')
    validate(value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        if len(encoded.encode('utf-8')) > MAX_JSON_BYTES:
            raise ValueError('JSON value exceeds the virtual runtime limit')
        return json.loads(encoded)
    except (TypeError, OverflowError, RecursionError) as exc:
        raise ValueError('a finite JSON value is required') from exc


def _identifier(value, label):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f'invalid {label}')
    return value


def _same_content(value):
    """JSON numeric equality, keeping booleans separate from numeric values."""
    if isinstance(value, list):
        return [_same_content(item) for item in value]
    if isinstance(value, dict):
        return {key: _same_content(item) for key, item in value.items()}
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _fingerprint(value):
    return json.dumps(_same_content(value), sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':'))


def _ports(profile):
    ports = profile.get('ports', {})
    if not isinstance(ports, dict) or set(ports) - {'inputs', 'outputs'}:
        raise ValueError('ports must contain inputs and outputs maps')
    result = {}
    for direction in ('inputs', 'outputs'):
        declarations = ports.get(direction, {})
        if not isinstance(declarations, dict) or len(declarations) > 64:
            raise ValueError('invalid port map')
        result[direction] = {}
        for name, declaration in declarations.items():
            _identifier(name, 'port name')
            kind = declaration.get('kind') if isinstance(declaration, dict) else declaration
            if not isinstance(kind, str) or kind not in PORT_KINDS:
                raise ValueError('unsupported port kind')
            result[direction][name] = kind
    return result


def _validate_actions(role_actions, roles):
    if not isinstance(role_actions, dict):
        raise ValueError('role_actions must be a map')
    for role in roles:
        actions = role_actions.get(role)
        if not isinstance(actions, dict) or not actions:
            raise ValueError('each instantiated role needs action declarations')
        for action, declaration in actions.items():
            _identifier(action, 'action')
            if not isinstance(declaration, dict):
                raise ValueError('action metadata must be a map')
            parameters = declaration.get('parameters', {})
            if not isinstance(parameters, dict):
                raise ValueError('action parameters must be a map')
            for name, spec in parameters.items():
                _identifier(name, 'parameter')
                if not isinstance(spec, dict) or not isinstance(spec.get('type'), str) or spec['type'] not in PARAMETER_TYPES:
                    raise ValueError('invalid parameter type declaration')
                if 'required' in spec and not isinstance(spec['required'], bool):
                    raise ValueError('required must be boolean')


def _parameters_valid(parameters, declaration):
    specs = declaration.get('parameters', {})
    if set(parameters) - set(specs):
        return False
    def finite(v):
        try:
            return type(v) in (int, float) and math.isfinite(v)
        except OverflowError:
            return False
    types = {'integer': lambda v: type(v) is int,
             'number': finite,
             'boolean': lambda v: type(v) is bool,
             'string': lambda v: isinstance(v, str),
             'object': lambda v: isinstance(v, dict),
             'array': lambda v: isinstance(v, list)}
    for name, spec in specs.items():
        if name not in parameters:
            if spec.get('required', False):
                return False
        elif not types[spec['type']](parameters[name]):
            return False
    return True


class VirtualFleet:
    """An in-memory synthetic runtime with isolated operator/author request IDs.

    Device implementations are trusted pure Python objects. An invalid result or
    unexpected device exception quarantines the node until runtime reconstruction.
    """

    def __init__(self, catalog, topology, *, factories, role_actions, seed=0):
        if type(seed) is not int or not 0 <= seed < 2 ** 64:
            raise ValueError('seed must be an unsigned 64-bit integer')
        self._catalog, self._topology = _json_copy(catalog), _json_copy(topology)
        self._role_actions = _json_copy(role_actions)
        if not isinstance(self._catalog, dict) or not isinstance(self._topology, dict):
            raise ValueError('catalog and topology must be maps')
        if not isinstance(factories, dict):
            raise ValueError('factories must be a map')
        profiles = self._catalog.get('profiles')
        nodes = self._topology.get('devices')
        connections = self._topology.get('connections', [])
        if not isinstance(profiles, list) or not 1 <= len(profiles) <= MAX_PROFILES:
            raise ValueError('catalog requires a bounded nonempty profiles list')
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_DEVICES:
            raise ValueError('topology requires a bounded nonempty devices list')
        if not isinstance(connections, list) or len(connections) > MAX_CONNECTIONS:
            raise ValueError('invalid connections list')
        self._profiles, self._profile_ports = {}, {}
        for profile in profiles:
            if not isinstance(profile, dict):
                raise ValueError('profile must be a map')
            profile_id = _identifier(profile.get('profile_id'), 'profile ID')
            role = _identifier(profile.get('role'), 'role')
            if profile_id in self._profiles:
                raise ValueError('duplicate profile ID')
            if role not in factories or not callable(factories[role]):
                raise ValueError('unsupported role')
            self._profiles[profile_id] = profile
            self._profile_ports[profile_id] = _ports(profile)
        _validate_actions(self._role_actions, {p['role'] for p in profiles})
        self._nodes = {}
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError('device must be a map')
            device_id = _identifier(node.get('id'), 'device ID')
            if device_id in self._nodes:
                raise ValueError('duplicate device ID')
            _identifier(node.get('profile_id'), 'profile ID')
            if node['profile_id'] not in self._profiles:
                raise ValueError('unknown profile')
            self._nodes[device_id] = node
        self._incoming = {name: [] for name in self._nodes}
        successors = {name: set() for name in self._nodes}
        indegree = dict.fromkeys(self._nodes, 0)
        targets = set()
        for connection in connections:
            if not isinstance(connection, dict) or set(connection) != {'source', 'target', 'kind'}:
                raise ValueError('connection requires source, target and kind')
            endpoints = []
            for endpoint, direction in [('source', 'outputs'), ('target', 'inputs')]:
                value = connection[endpoint]
                if not isinstance(value, dict) or set(value) != {'device_id', 'port'}:
                    raise ValueError('invalid connection endpoint')
                name, port = value['device_id'], value['port']
                _identifier(name, 'connected device ID')
                _identifier(port, 'connected port')
                if name not in self._nodes:
                    raise ValueError('unknown connected device')
                ports = self._profile_ports[self._nodes[name]['profile_id']][direction]
                if port not in ports or ports[port] != connection['kind']:
                    raise ValueError('unknown or mismatched connection port')
                endpoints.append((name, port))
            (source, source_port), (target, target_port) = endpoints
            if (target, target_port) in targets:
                raise ValueError('multiple sources to one input are unsupported')
            targets.add((target, target_port))
            self._incoming[target].append((source, source_port, target_port))
            if target not in successors[source]:
                successors[source].add(target)
                indegree[target] += 1
        ready = deque(sorted(name for name, degree in indegree.items() if not degree))
        self._order = []
        while ready:
            name = ready.popleft()
            self._order.append(name)
            for target in sorted(successors[name]):
                indegree[target] -= 1
                if not indegree[target]:
                    ready.append(target)
        if len(self._order) != len(self._nodes):
            raise ValueError('connection cycles are unsupported')
        self._devices = {}
        for name in self._order:
            profile = self._profiles[self._nodes[name]['profile_id']]
            derived_seed = int.from_bytes(hashlib.sha256(f'{seed}:{name}'.encode()).digest()[:8], 'big')
            device = factories[profile['role']](_json_copy(profile), derived_seed)
            for method in ('perform', 'advance', 'observation', 'author_control'):
                if not callable(getattr(device, method, None)):
                    raise ValueError('device does not implement the fixed interface')
            self._devices[name] = device
        self._lock = threading.RLock()
        self._tick = self._revision = 0
        self._requests = {}
        self._ledger_bytes = {'operator': 0, 'author': 0}
        self._history = deque(maxlen=MAX_HISTORY)
        self._snapshots = {}
        self._quarantined = set()
        self._exercised = {name: set() for name in self._nodes}
        self._status_counts = {name: {} for name in self._nodes}
        self._propagate()

    @property
    def catalog(self):
        return _json_copy(self._catalog)

    @property
    def topology(self):
        return _json_copy(self._topology)

    @property
    def role_actions(self):
        return _json_copy(self._role_actions)

    def _envelope(self, result, device_id=None):
        envelope = {'status': result['status'], 'values': _json_copy(result['values']),
                    'tick': self._tick, 'setup_revision': self._revision,
                    'synthetic': True, 'hardware_verified': False}
        for key in ('state', 'setup_changed'):
            if key in result:
                envelope[key] = _json_copy(result[key])
        if device_id is not None:
            profile = self._profiles[self._nodes[device_id]['profile_id']]
            envelope.update(device_id=device_id, profile_id=profile['profile_id'], role=profile['role'])
        return envelope

    def _check_result(self, raw, name, *, perform=False):
        result = _json_copy(raw)
        if len(json.dumps(result, ensure_ascii=False).encode('utf-8')) > MAX_DEVICE_RESULT_BYTES:
            raise ValueError('device result exceeds the contract limit')
        if not isinstance(result, dict) or not isinstance(result.get('status'), str) or result['status'] not in STATUSES:
            raise ValueError('invalid device status')
        if not isinstance(result.get('values'), dict):
            raise ValueError('device values must be a map')
        if perform and type(result.get('setup_changed')) is not bool:
            raise ValueError('perform requires boolean setup_changed')
        outputs = result['values'].get('outputs', {})
        declared = self._profile_ports[self._nodes[name]['profile_id']]['outputs']
        if not isinstance(outputs, dict) or set(outputs) - set(declared):
            raise ValueError('undeclared device output')
        for port, value in outputs.items():
            if not isinstance(value, dict):
                raise ValueError('port output must be an object')
            value['source_id'] = name
            if declared[port] == 'rf' and value.get('valid', True):
                numeric = ('frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle')
                if any(type(value.get(field)) not in (int, float) for field in numeric):
                    raise ValueError('RF signal requires finite explicit units')
                if value['frequency_hz'] <= 0 or value['bandwidth_hz'] <= 0:
                    raise ValueError('RF frequency and bandwidth must be positive')
                if not 0 < value['duty_cycle'] <= 1 or not isinstance(value.get('modulation'), str) or not value['modulation']:
                    raise ValueError('invalid RF duty cycle or modulation')
        return result

    def _inputs(self, name):
        result = {}
        for source, source_port, target_port in self._incoming[name]:
            upstream = self._snapshots.get(source, {'status': 'invalid', 'values': {}})
            value = upstream['values'].get('outputs', {}).get(source_port)
            if value is None:
                result[target_port] = {'valid': False, 'upstream_status': upstream['status'],
                                       'reason': 'output_unavailable', 'source_id': source}
                continue
            result[target_port] = _json_copy(value)
            if upstream['status'] != 'ok' and not (upstream['status'] == 'pending' and value.get('valid') is True):
                result[target_port].update(valid=False, upstream_status=upstream['status'])
        return result

    def _failed(self):
        return {'status': 'error', 'state': 'unavailable',
                'values': {'reason': 'device_contract_error', 'outputs': {}}}

    def _propagate(self):
        for _ in range(len(self._order) + 1):
            before = len(self._quarantined)
            for name in self._order:
                if name in self._quarantined:
                    self._snapshots[name] = self._failed()
                    continue
                device = self._devices[name]
                try:
                    device.advance(tick=self._tick, setup_revision=self._revision, inputs=self._inputs(name))
                    raw = device.observation(tick=self._tick, setup_revision=self._revision)
                    self._snapshots[name] = self._check_result(raw, name)
                except Exception:
                    self._quarantined.add(name)
                    self._snapshots[name] = self._failed()
            if len(self._quarantined) == before:
                break
            self._revision += 1

    def _request(self, namespace, request_id, content):
        _identifier(request_id, 'request ID')
        key = (namespace, request_id)
        fingerprint = _fingerprint(content)
        if key in self._requests:
            previous, response = self._requests[key]
            if previous != fingerprint:
                if namespace == 'operator':
                    self._history.append({'request_id': request_id, 'tick': self._tick, 'outcome': 'conflict'})
                raise ValueError('request ID conflicts with an earlier request')
            if namespace == 'operator':
                self._history.append({'request_id': request_id, 'tick': self._tick, 'outcome': 'duplicate'})
            return key, fingerprint, _json_copy(response)
        if sum(stored_namespace == namespace for stored_namespace, _ in self._requests) >= MAX_REQUESTS:
            raise ValueError('virtual request ledger is full; construct a new runtime')
        if self._ledger_bytes[namespace] + len(fingerprint.encode('utf-8')) + MAX_JSON_BYTES > MAX_LEDGER_BYTES:
            raise ValueError('virtual request byte budget is full; construct a new runtime')
        return key, fingerprint, None

    def _remember(self, key, fingerprint, response, event=None):
        stored = _json_copy(response)
        self._requests[key] = (fingerprint, stored)
        self._ledger_bytes[key[0]] += len(fingerprint.encode('utf-8')) + len(json.dumps(stored, ensure_ascii=False).encode('utf-8'))
        if event is not None:
            self._history.append(_json_copy(event))
        return _json_copy(response)

    def execute(self, request_id, device_id, action, parameters=None):
        with self._lock:
            parameters = {} if parameters is None else _json_copy(parameters)
            if not isinstance(parameters, dict):
                raise ValueError('parameters must be a JSON object')
            _identifier(device_id, 'device ID')
            _identifier(action, 'action')
            key, fingerprint, cached = self._request('operator', request_id,
                                                    ['execute', device_id, action, parameters])
            if cached is not None:
                return cached
            result = {'status': 'invalid', 'values': {'reason': 'unknown_device'}, 'setup_changed': False}
            if device_id in self._nodes:
                role = self._profiles[self._nodes[device_id]['profile_id']]['role']
                declaration = self._role_actions[role].get(action)
                if declaration is None:
                    result = {'status': 'unsupported', 'values': {'reason': 'unsupported_action'}, 'setup_changed': False}
                elif not _parameters_valid(parameters, declaration):
                    result = {'status': 'invalid', 'values': {'reason': 'invalid_parameters'}, 'setup_changed': False}
                elif device_id in self._quarantined:
                    result = dict(self._failed(), setup_changed=False)
                else:
                    try:
                        raw = self._devices[device_id].perform(action, _json_copy(parameters), tick=self._tick,
                                                               setup_revision=self._revision, inputs=self._inputs(device_id))
                        result = self._check_result(raw, device_id, perform=True)
                    except Exception:
                        self._quarantined.add(device_id)
                        result = dict(self._failed(), setup_changed=True)
                    self._exercised[device_id].add(action)
            if result['setup_changed']:
                self._revision += 1
            action_revision = self._revision
            self._propagate()
            if device_id in self._quarantined:
                result = dict(self._failed(), setup_changed=result['setup_changed'])
            elif self._revision != action_revision and result['status'] in {'ok', 'pending'}:
                result = {'status': 'invalid', 'values': {'reason': 'setup_changed_during_action'},
                          'setup_changed': result['setup_changed']}
            if device_id in self._nodes:
                counts = self._status_counts[device_id]
                counts[result['status']] = counts.get(result['status'], 0) + 1
            response = self._envelope(result, device_id if device_id in self._nodes else None)
            event = {'request_id': request_id, 'kind': 'execute', 'device_id': device_id,
                     'action': action, 'tick': self._tick, 'status': result['status'], 'outcome': 'executed'}
            return self._remember(key, fingerprint, response, event)

    def advance(self, request_id, ticks=1):
        with self._lock:
            if type(ticks) is not int or not 1 <= ticks <= MAX_ADVANCE_TICKS:
                raise ValueError('ticks must be an integer from 1 to 10000')
            key, fingerprint, cached = self._request('operator', request_id, ['advance', ticks])
            if cached is not None:
                return cached
            for _ in range(ticks):
                self._tick += 1
                self._propagate()
            response = self._envelope({'status': 'ok', 'values': {'advanced_ticks': ticks}})
            return self._remember(key, fingerprint, response,
                                  {'request_id': request_id, 'kind': 'advance', 'tick': self._tick,
                                   'ticks': ticks, 'status': 'ok', 'outcome': 'executed'})

    def author_control(self, request_id, device_id, fault, value):
        with self._lock:
            _identifier(device_id, 'device ID')
            _identifier(fault, 'author control')
            value = _json_copy(value)
            key, fingerprint, cached = self._request('author', request_id, [device_id, fault, value])
            if cached is not None:
                return cached
            if device_id not in self._nodes:
                raise ValueError('unknown device')
            if device_id in self._quarantined:
                raise ValueError('unavailable device requires runtime reconstruction')
            result = {'status': 'ok', 'values': {}}
            try:
                self._devices[device_id].author_control(fault, value)
            except Exception:
                self._quarantined.add(device_id)
                result = self._failed()
            self._revision += 1
            self._propagate()
            if device_id in self._quarantined:
                result = self._failed()
            response = self._envelope(result)
            return self._remember(key, fingerprint, response)

    def observations(self):
        with self._lock:
            return {'tick': self._tick, 'setup_revision': self._revision,
                    'synthetic': True, 'hardware_verified': False,
                    'devices': {name: self._envelope(self._snapshots[name], name) for name in self._order}}

    def history(self):
        with self._lock:
            return _json_copy(list(self._history))

    def coverage(self):
        with self._lock:
            devices = {}
            for name in self._order:
                profile = self._profiles[self._nodes[name]['profile_id']]
                role = profile['role']
                devices[name] = {
                    'profile_id': profile['profile_id'], 'role': role,
                    'supported_actions': sorted(self._role_actions[role]),
                    'action_definitions': _json_copy(self._role_actions[role]),
                    'exercised_actions': sorted(self._exercised[name]),
                    'status_counts': dict(self._status_counts[name]),
                    'scenario_validation': 'not_assessed',
                    'available': name not in self._quarantined,
                }
            return {'synthetic': True, 'hardware_verified': False, 'devices': devices,
                    'catalog_profiles': len(self._profiles), 'instantiated_devices': len(self._nodes),
                    'uninstantiated_profiles': sorted(set(self._profiles) - {n['profile_id'] for n in self._nodes.values()}),
                    'validation_scope': 'execution counters; scenario acceptance and physical accuracy unverified'}
