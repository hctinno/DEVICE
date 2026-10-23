"""Observation-only trusted-fixture runner; no providers, transport or replay.

Deadlines are cooperative. A RetryableTransportError is the caller's guarantee
that retrying still reaches the same live runtime and its request-ID ledger.
"""
import hashlib
import json
import math
import re
import threading
import time
from uuid import uuid4


_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_STATUSES = {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}
_TYPES = {'number', 'integer', 'boolean', 'string', 'object', 'array'}
_DEFAULTS = {'decisions': 64, 'logical_requests': 64, 'ticks': 32,
             'wall_seconds': 30, 'transport_retries': 2}
_PRIVATE = {'author', 'author_control', 'scenario_control', 'hidden', 'hidden_fault', 'hidden_faults',
            'fault', 'faults', 'truth', 'expected', 'expected_value', 'expected_values', 'expected_result',
            'seed', 'scenario', 'scenario_id', 'scenario_label', 'schedule', 'password', 'secret',
            'credential', 'credentials', 'source_path', 'file_path', 'decrypted_path', 'path',
            'serial', 'serial_number', 'simulation_parameters'}
_PROFILE_FIELDS = {'profile_id', 'model', 'manufacturer', 'role', 'ports', 'variant', 'evidence_refs',
                   'simulation_basis', 'capability_scope', 'profile_kind', 'classification',
                   'context', 'auxiliary'}
_CATALOG_FIELDS = {'schema_version', 'catalog_id', 'source_basis', 'title', 'scope', 'fixture'}
_MAX_JSON = 1024 * 1024
_MAX_EVENT = 512 * 1024
_MAX_EVENT_BYTES = 32 * 1024 * 1024
_MAX_EVENTS = 4096


class RetryableTransportError(Exception):
    """Only raise when the original live runtime and ID ledger remain reachable."""


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _copy(value, *, project=False, limit=_MAX_JSON):
    def walk(item, depth=0):
        if depth > 32:
            raise ValueError('json_depth')
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError('json_keys')
            return {key: walk(child, depth+1) for key, child in item.items()
                    if not project or key.lower() not in _PRIVATE}
        if type(item) is list:
            return [walk(child, depth+1) for child in item]
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        raise ValueError('json_value')
    result = walk(value)
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(encoded) > limit:
        raise ValueError('json_size')
    return json.loads(encoded)


def _identifier(value):
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError('identifier')
    return value


def _public_catalog(catalog):
    if type(catalog) is not dict or type(catalog.get('profiles')) is not list:
        raise ValueError('catalog')
    result = {key: value for key, value in catalog.items() if key in _CATALOG_FIELDS}
    result['profiles'] = []
    for profile in catalog['profiles']:
        if type(profile) is not dict:
            raise ValueError('profile')
        result['profiles'].append({key: value for key, value in profile.items() if key in _PROFILE_FIELDS})
    return _copy(result, project=True)


def _no_private(value):
    if type(value) is dict:
        return all(key.lower() not in _PRIVATE and _no_private(child) for key, child in value.items())
    if type(value) is list:
        return all(_no_private(child) for child in value)
    return True


def _typed(value, spec):
    kind = spec['type']
    valid = {'number': lambda: _finite(value), 'integer': lambda: type(value) is int,
             'boolean': lambda: type(value) is bool, 'string': lambda: type(value) is str and len(value) <= 4096,
             'object': lambda: type(value) is dict, 'array': lambda: type(value) is list}[kind]()
    if not valid:
        return False
    if 'enum' in spec and not any(type(value) is type(item) and value == item for item in spec['enum']):
        return False
    if kind in {'number', 'integer'}:
        if 'minimum' in spec and value < spec['minimum']:
            return False
        if 'maximum' in spec and value > spec['maximum']:
            return False
    return True


class FleetHarness:
    """One owner, one live runtime, detached JSON policy input and evidence.

    The fixture is trusted Python, not a security sandbox. No automatic cleanup,
    durable resume, independent grading or hard cancellation is performed here.
    """

    def __init__(self, runtime, policy, *, goal, catalog, topology, role_actions,
                 budgets=None, event_sink=None, run_id=None, runtime_instance_id=None, clock=None):
        if not callable(policy) or any(not callable(getattr(runtime, name, None))
                                       for name in ('execute', 'advance', 'observations')):
            raise ValueError('runtime_or_policy')
        if event_sink is not None and not callable(event_sink):
            raise ValueError('event_sink')
        if clock is not None and not callable(clock):
            raise ValueError('clock')
        self._runtime, self._policy = runtime, policy
        self._sink, self._clock = event_sink, clock or time.monotonic
        self._run_id = _identifier(str(uuid4()) if run_id is None else run_id)
        self._instance_id = _identifier(str(uuid4()) if runtime_instance_id is None else runtime_instance_id)
        self._goal = _copy(goal, project=True)
        self._catalog = _public_catalog(catalog)
        self._topology = _copy(topology, project=True)
        self._actions = _copy(role_actions, project=True)
        if type(self._goal) is not dict or type(self._topology) is not dict or type(self._actions) is not dict:
            raise ValueError('metadata')
        self._profiles, self._devices = {}, {}
        for profile in self._catalog['profiles']:
            identity = _identifier(profile.get('profile_id'))
            if identity in self._profiles or type(profile.get('role')) is not str:
                raise ValueError('profile')
            self._profiles[identity] = profile
        if type(self._topology.get('devices')) is not list:
            raise ValueError('topology')
        for node in self._topology['devices']:
            if type(node) is not dict:
                raise ValueError('device')
            identity = _identifier(node.get('id'))
            if identity in self._devices or node.get('profile_id') not in self._profiles:
                raise ValueError('device')
            self._devices[identity] = self._profiles[node['profile_id']]
        for profile in self._devices.values():
            actions = self._actions.get(profile['role'])
            if type(actions) is not dict or not actions:
                raise ValueError('actions')
            for action, declaration in actions.items():
                _identifier(action)
                if type(declaration) is not dict or type(declaration.get('parameters')) is not dict:
                    raise ValueError('action')
                for name, spec in declaration['parameters'].items():
                    _identifier(name)
                    if (type(spec) is not dict or type(spec.get('type')) is not str or spec['type'] not in _TYPES
                            or type(spec.get('required', False)) is not bool):
                        raise ValueError('parameter')
        limits = {} if budgets is None else _copy(budgets)
        if type(limits) is not dict or set(limits) - set(_DEFAULTS):
            raise ValueError('budgets')
        self._limits = {**_DEFAULTS, **limits}
        for name, value in self._limits.items():
            if name == 'wall_seconds':
                if not _finite(value) or value <= 0:
                    raise ValueError('wall_budget')
            elif type(value) is not int or value < (0 if name == 'transport_retries' else 1):
                raise ValueError('budget')
        try:
            policy_id = getattr(policy, 'policy_id', 'fixture')
        except BaseException:
            policy_id = 'fixture'
        self._policy_id = policy_id if type(policy_id) is str and _IDENTIFIER.fullmatch(policy_id) else 'fixture'
        self._events, self._measurement_refs = [], []
        self._event_bytes, self._sink_failed = 0, False
        self._last_observation, self._last_receipt = None, None
        self._start, self._now, self._initial_tick = None, None, None
        self._usage = {'decisions': 0, 'logical_requests': 0, 'transport_retries': 0,
                       'tick_delta': 0, 'reserved_ticks': 0, 'elapsed_ms': 0}
        self._unresolved = set()
        self._dispatched = False
        self._result = None
        self._stop_requested = threading.Event()
        self._step_lock = threading.Lock()
        self._id_prefix = hashlib.sha256((self._run_id+'\0'+self._instance_id).encode()).hexdigest()[:20]

    def stop(self):
        """Request a stop at the next decision/call boundary; no device cleanup."""
        self._stop_requested.set()

    def events(self):
        # Each accepted event already owns its depth/size budget. Wrapping all
        # events in one JSON tree must not reduce that permitted depth by one.
        return [_copy(event, limit=_MAX_EVENT) for event in list(self._events)]

    def result(self):
        return None if self._result is None else _copy(self._result, limit=256*1024)

    def _time(self):
        value = self._clock()
        if not _finite(value) or (self._now is not None and value < self._now):
            raise ValueError('clock')
        now = float(value)
        start = now if self._start is None else self._start
        elapsed = (now-start)*1000
        if not math.isfinite(elapsed):
            raise ValueError('clock_range')
        self._now, self._start = now, start
        self._usage['elapsed_ms'] = max(0.0, elapsed)
        return now-start >= self._limits['wall_seconds']

    def _record(self, kind, payload):
        if self._sink_failed:
            return None
        event = {'schema_version': 1, 'kind': 'operator_event', 'event_id': 'event:'+str(len(self._events)+1),
                 'run_id': self._run_id, 'runtime_instance_id': self._instance_id,
                 'sequence': len(self._events)+1, 'type': kind, 'payload': payload}
        try:
            event = _copy(event, limit=_MAX_EVENT)
            size = len(json.dumps(event, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
            if len(self._events) >= _MAX_EVENTS or self._event_bytes+size > _MAX_EVENT_BYTES:
                raise ValueError('event_limit')
            if self._sink is not None:
                self._sink(_copy(event, limit=_MAX_EVENT))
        except BaseException:
            self._sink_failed = True
            return None
        self._events.append(event)
        self._event_bytes += size
        return event

    def _finish(self, reason, *, claim=None, code=None):
        if self._result is not None:
            return
        if code is not None:
            self._record('error', {'code': code})
        termination = {'reason': reason, 'policy_claim': claim if reason == 'policy_stop' else None}
        if not self._record('termination', {'code': 'run_terminated', 'unresolved_request_ids': sorted(self._unresolved)}):
            if reason not in {'evidence_error', 'runtime_mutation_uncertain'}:
                reason = 'runtime_mutation_uncertain' if self._dispatched else 'evidence_error'
                termination = {'reason': reason, 'policy_claim': None}
        try:
            expired = self._time()
        except BaseException:
            if reason == 'policy_stop':
                termination = {'reason': 'runtime_error', 'policy_claim': None}
        else:
            if expired and reason == 'policy_stop':
                termination = {'reason': 'wall_deadline', 'policy_claim': None}
        self._result = {
            'schema_version': 1, 'kind': 'virtual_fleet_harness_result', 'run_id': self._run_id,
            'runtime_instance_id': self._instance_id, 'synthetic': True, 'hardware_verified': False,
            'ai_model_called': False, 'policy': {'kind': 'fixture', 'id': self._policy_id},
            'termination': termination, 'task_outcome': 'not_assessed',
            'cleanup': {'status': 'not_assessed', 'evidence_refs': []}, 'usage': dict(self._usage),
            'evidence': {'measurement_refs': list(self._measurement_refs),
                         'operator_transcript_ref': 'artifact:operator_events'},
            'unresolved_request_ids': sorted(self._unresolved),
            'assessment': {'status': 'not_assessed', 'verdict': None, 'evaluator_id': None,
                           'evidence_refs': [], 'summary_code': None}}

    def _boundary(self, *, mutation=False):
        if self._stop_requested.is_set():
            self._finish('runtime_mutation_uncertain' if mutation and self._unresolved else 'supervisor_stop')
            return False
        try:
            expired = self._time()
        except BaseException:
            self._finish('runtime_mutation_uncertain' if mutation else 'runtime_error', code='clock_error')
            return False
        if expired:
            self._finish('runtime_mutation_uncertain' if mutation else 'wall_deadline', code='deadline_elapsed')
            return False
        return True

    def _envelope(self, value):
        if (type(value) is not dict or type(value.get('status')) is not str or value['status'] not in _STATUSES
                or type(value.get('values')) is not dict or value.get('synthetic') is not True
                or value.get('hardware_verified') is not False
                or type(value.get('tick')) is not int or value['tick'] < 0
                or type(value.get('setup_revision')) is not int or value['setup_revision'] < 0):
            raise ValueError('runtime_envelope')
        outputs = value['values'].get('outputs', {})
        if type(outputs) is not dict or any(type(packet) is not dict for packet in outputs.values()):
            raise ValueError('runtime_outputs')

    def _observe(self, *, cause=None, expected_tick=None, minimum_revision=None):
        try:
            raw = self._runtime.observations()
        except BaseException:
            self._finish('runtime_mutation_uncertain' if cause else 'runtime_error', code='observation_error')
            return None
        if not self._boundary(mutation=cause is not None):
            return None
        try:
            observation = _copy(raw, project=True)
            if (type(observation) is not dict or observation.get('synthetic') is not True
                    or observation.get('hardware_verified') is not False
                    or type(observation.get('tick')) is not int or observation['tick'] < 0
                    or type(observation.get('setup_revision')) is not int or observation['setup_revision'] < 0
                    or type(observation.get('devices')) is not dict
                    or set(observation['devices']) != set(self._devices)):
                raise ValueError('observations')
            for identity, value in observation['devices'].items():
                self._envelope(value)
                profile = self._devices[identity]
                if (value.get('device_id') != identity or value.get('profile_id') != profile['profile_id']
                        or value.get('role') != profile['role'] or value['tick'] != observation['tick']
                        or value['setup_revision'] != observation['setup_revision']):
                    raise ValueError('device_binding')
            if self._initial_tick is None:
                self._initial_tick = observation['tick']
            if observation['tick'] < self._initial_tick+self._usage['tick_delta']:
                raise ValueError('clock_reversed')
            if expected_tick is not None and observation['tick'] != expected_tick:
                raise ValueError('unexpected_observation_tick')
            if observation['tick']-self._initial_tick > self._limits['ticks']:
                raise ValueError('observation_tick_budget')
            if minimum_revision is not None and observation['setup_revision'] < minimum_revision:
                raise ValueError('observation_revision')
        except BaseException:
            self._finish('runtime_mutation_uncertain' if cause else 'runtime_error', code='observation_invalid')
            return None
        return observation

    def _read_observation(self):
        observation = self._observe()
        return observation is not None and self._record_observation(observation)

    def _record_observation(self, observation, *, cause=None):
        payload = {'observation': observation}
        if cause is not None:
            payload['cause_request_id'] = cause
        event = self._record('observation', payload)
        if event is None:
            self._finish('runtime_mutation_uncertain' if cause else 'evidence_error', code='observation_evidence_error')
            return False
        self._last_observation = observation
        self._usage['tick_delta'] = observation['tick']-self._initial_tick
        if self._has_measurement(observation):
            self._measurement_refs.append(event['event_id'])
        return self._boundary()

    @staticmethod
    def _has_measurement(observation):
        for identity, device in observation['devices'].items():
            if device['status'] != 'ok':
                continue
            packet = device['values'].get('outputs', {}).get('measurement')
            if (type(packet) is dict and packet.get('status') == 'ok' and packet.get('valid') is True
                    and packet.get('source_id') == identity and type(packet.get('unit')) is str and packet['unit']
                    and _finite(packet.get('value')) and type(packet.get('acquisition_tick')) is int
                    and 0 <= packet['acquisition_tick'] <= observation['tick']
                    and type(packet.get('acquisition_setup_revision')) is int
                    and packet['acquisition_setup_revision'] == observation['setup_revision']):
                return True
        return False

    def _remaining(self):
        return {'decisions': max(0, self._limits['decisions']-self._usage['decisions']),
                'logical_requests': max(0, self._limits['logical_requests']-self._usage['logical_requests']),
                'ticks': max(0, self._limits['ticks']-self._usage['tick_delta']-self._usage['reserved_ticks']),
                'wall_seconds': max(0.0, self._limits['wall_seconds']-self._usage['elapsed_ms']/1000),
                'transport_retries': max(0, self._limits['transport_retries']-self._usage['transport_retries'])}

    def _proposal(self, raw):
        proposal = _copy(raw, limit=64*1024)
        if type(proposal) is not dict or not _no_private(proposal):
            raise ValueError('proposal')
        kind = proposal.get('kind')
        if kind == 'stop':
            if (set(proposal) != {'kind', 'claim', 'reason'} or type(proposal['claim']) is not str
                    or proposal['claim'] not in {'completed', 'blocked', 'unsupported', 'failed'}
                    or type(proposal['reason']) is not str or not proposal['reason'].strip()
                    or len(proposal['reason']) > 4096):
                raise ValueError('stop')
        elif kind == 'advance':
            if set(proposal) != {'kind', 'ticks'} or type(proposal['ticks']) is not int or proposal['ticks'] != 1:
                raise ValueError('advance')
        elif kind == 'execute':
            if (set(proposal) != {'kind', 'device_id', 'action', 'parameters'}
                    or type(proposal['device_id']) is not str or proposal['device_id'] not in self._devices
                    or type(proposal['action']) is not str or type(proposal['parameters']) is not dict):
                raise ValueError('execute')
            role = self._devices[proposal['device_id']]['role']
            declaration = self._actions[role].get(proposal['action'])
            if declaration is None:
                raise ValueError('action')
            specs, parameters = declaration['parameters'], proposal['parameters']
            if set(parameters)-set(specs):
                raise ValueError('parameters')
            for name, spec in specs.items():
                if name not in parameters:
                    if spec.get('required', False):
                        raise ValueError('required')
                elif not _typed(parameters[name], spec):
                    raise ValueError('parameter_type')
        else:
            raise ValueError('proposal_kind')
        return proposal

    def _dispatch(self, proposal):
        if self._usage['logical_requests'] >= self._limits['logical_requests']:
            self._finish('request_budget')
            return
        operation = proposal['kind']
        if operation == 'advance' and self._remaining()['ticks'] < 1:
            self._finish('tick_budget')
            return
        logical = self._usage['logical_requests']+1
        expected_tick = self._last_observation['tick']+int(operation == 'advance')
        request_id = 'request:'+self._id_prefix+':'+str(logical)
        body = {key: value for key, value in proposal.items() if key != 'kind'}
        if not self._record('intent', {'request_id': request_id, 'operation': operation,
                                     'body': body, 'logical_request': logical}):
            self._finish('evidence_error', code='intent_evidence_error')
            return
        self._usage['logical_requests'] = logical
        self._unresolved.add(request_id)
        if operation == 'advance':
            self._usage['reserved_ticks'] += 1
        if not self._boundary():
            return
        retry = 0
        while True:
            try:
                self._dispatched = True
                if operation == 'advance':
                    raw = self._runtime.advance(request_id, body['ticks'])
                else:
                    raw = self._runtime.execute(request_id, body['device_id'], body['action'], _copy(body['parameters']))
            except RetryableTransportError:
                if not self._boundary(mutation=True):
                    return
                if self._usage['transport_retries'] >= self._limits['transport_retries']:
                    self._finish('runtime_mutation_uncertain', code='transport_retry_exhausted')
                    return
                retry += 1
                if not self._record('transport_retry', {'request_id': request_id, 'retry': retry}):
                    self._finish('runtime_mutation_uncertain', code='retry_evidence_error')
                    return
                self._usage['transport_retries'] += 1
                if not self._boundary(mutation=True):
                    return
                continue
            except BaseException:
                self._finish('runtime_mutation_uncertain', code='runtime_call_error')
                return
            break
        if not self._boundary(mutation=True):
            return
        try:
            receipt = _copy(raw, project=True)
            self._envelope(receipt)
            if (receipt['tick'] != expected_tick or receipt['tick']-self._initial_tick > self._limits['ticks']
                    or receipt['setup_revision'] < self._last_observation['setup_revision']):
                raise ValueError('receipt_clock')
            if operation == 'execute':
                profile = self._devices[body['device_id']]
                if (receipt.get('device_id') != body['device_id'] or receipt.get('profile_id') != profile['profile_id']
                        or receipt.get('role') != profile['role']):
                    raise ValueError('receipt_device_binding')
            elif (receipt['status'] != 'ok' or type(receipt['values'].get('advanced_ticks')) is not int
                  or receipt['values']['advanced_ticks'] != 1):
                raise ValueError('receipt_advance')
        except BaseException:
            self._finish('runtime_mutation_uncertain', code='receipt_invalid')
            return
        observation = self._observe(cause=request_id, expected_tick=expected_tick,
                                    minimum_revision=receipt['setup_revision'])
        if observation is None:
            return
        if not self._record('receipt', {'request_id': request_id, 'result': receipt}):
            self._finish('runtime_mutation_uncertain', code='receipt_evidence_error')
            return
        self._unresolved.remove(request_id)
        self._last_receipt = receipt
        if operation == 'advance':
            self._usage['reserved_ticks'] -= 1
        self._usage['tick_delta'] = receipt['tick']-self._initial_tick
        if not self._boundary(mutation=True):
            return
        self._record_observation(observation, cause=request_id)

    def _state(self):
        return _copy({'state': 'terminated' if self._result is not None else 'running',
                      'run_id': self._run_id, 'runtime_instance_id': self._instance_id,
                      'usage': dict(self._usage), 'termination': None if self._result is None else self._result['termination'],
                      'result': self._result}, limit=_MAX_JSON)

    def step(self):
        """Make at most one policy decision. Never dispatch after a terminal state."""
        if not self._step_lock.acquire(blocking=False):
            raise RuntimeError('step_already_running')
        try:
            if self._result is not None or not self._boundary():
                return self._state()
            if self._usage['decisions'] >= self._limits['decisions']:
                self._finish('decision_budget')
                return self._state()
            if self._last_observation is None and not self._read_observation():
                return self._state()
            self._usage['decisions'] += 1
            context = _copy({'schema_version': 1, 'goal': self._goal, 'catalog': self._catalog,
                             'topology': self._topology, 'role_actions': self._actions,
                             'observations': self._last_observation, 'last_receipt': self._last_receipt,
                             'remaining_budget': self._remaining()})
            try:
                raw = self._policy(context)
            except BaseException:
                self._finish('policy_error', code='policy_call_error')
                return self._state()
            if not self._boundary():
                return self._state()
            try:
                proposal = self._proposal(raw)
            except BaseException:
                self._finish('invalid_proposal', code='proposal_invalid')
                return self._state()
            if not self._record('policy_decision', {'proposal': proposal}):
                self._finish('evidence_error', code='decision_evidence_error')
            elif not self._boundary():
                pass
            elif proposal['kind'] == 'stop':
                self._finish('policy_stop', claim=proposal['claim'])
            else:
                self._dispatch(proposal)
            if self._result is None:
                self._boundary()
            return self._state()
        except BaseException:
            self._finish('runtime_mutation_uncertain' if self._unresolved else 'runtime_error', code='harness_contract_error')
            return self._state()
        finally:
            self._step_lock.release()

    def run(self):
        """Run a trusted fixture until bounded termination; never grade its claim."""
        while self._result is None:
            self.step()
        return self.result()
