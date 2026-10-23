"""Trusted, observation-only RF fixture policy; no model or device calls."""
import json
import math
import re


_CONTEXT = {'schema_version', 'goal', 'catalog', 'topology', 'role_actions',
            'observations', 'last_receipt', 'remaining_budget'}
_PRIVATE = {'author', 'author_control', 'scenario_control', 'fault', 'hidden',
            'truth', 'expected', 'expected_values', 'seed', 'scenario', 'scenario_label',
            'schedule', 'password', 'credential', 'credentials', 'source_path',
            'file_path', 'decrypted_path', 'simulation_parameters'}
_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_STATUSES = {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}


class _Reject(Exception):
    def __init__(self, claim, reason):
        self.claim, self.reason = claim, reason


def _stop(claim, reason):
    return {'kind': 'stop', 'claim': claim, 'reason': reason}


def _execute(device, action):
    return {'kind': 'execute', 'device_id': device, 'action': action, 'parameters': {}}


def _integer(value):
    return type(value) is int and value >= 0


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _identifier(value):
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _json_tree(value, depth=0):
    if depth > 32:
        raise ValueError('JSON nesting limit')
    if type(value) is dict:
        if len(value) > 1024:
            raise ValueError('JSON map limit')
        for key, item in value.items():
            if type(key) is not str or key.lower() in _PRIVATE:
                raise ValueError('Nonpublic context')
            _json_tree(item, depth + 1)
    elif type(value) is list:
        if len(value) > 4096:
            raise ValueError('JSON list limit')
        for item in value:
            _json_tree(item, depth + 1)
    elif value is None or type(value) in (str, bool, int):
        return
    elif type(value) is not float or not math.isfinite(value):
        raise ValueError('Finite JSON required')


def _kind(declaration):
    return declaration.get('kind') if type(declaration) is dict else declaration


def _signal(value, source):
    if (type(value) is not dict or value.get('status') != 'ok'
            or value.get('valid') is not True or value.get('source_id') != source):
        raise ValueError('Invalid RF provenance')
    fields = ('frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle', 'crest_factor_db')
    if any(not _finite(value.get(name)) for name in fields):
        raise ValueError('Invalid RF number')
    if (value['frequency_hz'] <= 0 or value['bandwidth_hz'] <= 0
            or not 0 < value['duty_cycle'] <= 1 or value['crest_factor_db'] < 0
            or type(value.get('modulation')) is not str or not value['modulation']):
        raise ValueError('Invalid RF values')
    if (value['frequency_hz'] - value['bandwidth_hz'] / 2 < 0
            or not math.isfinite(value['frequency_hz'] + value['bandwidth_hz'] / 2)):
        raise ValueError('Invalid occupied RF band')
    return value


class RFSensorFixturePolicy:
    """One instance per run. Only detached public JSON is accepted.

    A fresh acquisition proposed by this instance and a subsequent read must
    precede completion. Receipts never substitute for the current observation.
    The harness owns request IDs, budgets and trusted snapshot delivery.
    """

    policy_id = 'rf_sensor_v1'

    def __init__(self):
        self._binding = None
        self._clock = None
        self._acquire = None
        self._read = None

    def __call__(self, context):
        try:
            _json_tree(context)
            encoded = json.dumps(context, ensure_ascii=False, allow_nan=False, sort_keys=True)
            if len(encoded.encode('utf-8')) > 1024 * 1024:
                raise ValueError('Context size limit')
            if type(context) is not dict or set(context) != _CONTEXT or type(context['schema_version']) is not int or context['schema_version'] != 1:
                raise ValueError('Invalid context schema')
            if any(type(context[name]) is not dict for name in ('catalog', 'topology', 'role_actions', 'remaining_budget')):
                raise ValueError('Invalid context maps')
            goal = context['goal']
            if (type(goal) is not dict or set(goal) != {'kind', 'dut_id', 'sensor_id', 'minimum_acquisition_tick'}
                    or goal['kind'] != 'acquire_fresh_rf_sensor' or not _identifier(goal['dut_id'])
                    or not _identifier(goal['sensor_id']) or goal['dut_id'] == goal['sensor_id']
                    or not _integer(goal['minimum_acquisition_tick'])):
                raise ValueError('Invalid goal')
            observed = context['observations']
            if (type(observed) is not dict or observed.get('synthetic') is not True
                    or observed.get('hardware_verified') is not False
                    or not _integer(observed.get('tick')) or not _integer(observed.get('setup_revision'))):
                raise ValueError('Invalid snapshot')
            clock = (observed['tick'], observed['setup_revision'])
            if self._clock is not None and any(new < old for new, old in zip(clock, self._clock)):
                raise ValueError('Snapshot went backwards')
            binding = json.dumps({name: context[name] for name in ('goal', 'catalog', 'topology', 'role_actions')},
                                 sort_keys=True, ensure_ascii=False, allow_nan=False)
            if self._binding is not None and binding != self._binding:
                raise ValueError('Public contract changed')
            profiles, nodes, incoming = self._metadata(context)
            dut_id, sensor_id = goal['dut_id'], goal['sensor_id']
            dut = self._node(observed, dut_id, profiles, nodes)
            sensor = self._node(observed, sensor_id, profiles, nodes)
            self._binding, self._clock = binding, clock
            if self._acquire is not None and self._acquire[1] != clock[1]:
                self._acquire = self._read = None
            return self._decide(goal, observed, dut, sensor, profiles, nodes, incoming)
        except _Reject as error:
            return _stop(error.claim, error.reason)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
            return _stop('failed', 'invalid_public_context')

    def _metadata(self, context):
        profiles, nodes = {}, {}
        for profile in context['catalog']['profiles']:
            identity = profile['profile_id']
            if not _identifier(identity) or identity in profiles:
                raise ValueError('Invalid profile identity')
            profiles[identity] = profile
        topology = context['topology']
        for node in topology['devices']:
            identity = node['id']
            if not _identifier(identity) or identity in nodes or node['profile_id'] not in profiles:
                raise ValueError('Invalid topology identity')
            nodes[identity] = node['profile_id']
        goal = context['goal']
        for identity, role, required in ((goal['dut_id'], 'dut', ('start',)),
                                         (goal['sensor_id'], 'power_sensor', ('acquire', 'read'))):
            if identity not in nodes or profiles[nodes[identity]]['role'] != role:
                raise _Reject('unsupported', 'unsupported_fixture')
            actions = context['role_actions'].get(role, {})
            if type(actions) is not dict:
                raise ValueError('Invalid role actions')
            for action in required:
                if action not in actions:
                    raise _Reject('unsupported', 'unsupported_fixture')
                declaration = actions[action]
                if type(declaration) is not dict or type(declaration.get('parameters', {})) is not dict:
                    raise ValueError('Invalid action declaration')
                rules = declaration.get('parameters', {}).values()
                if any(type(rule) is not dict or type(rule.get('required', False)) is not bool for rule in rules):
                    raise ValueError('Invalid action parameters')
                if any(rule.get('required', False) for rule in rules):
                    raise _Reject('unsupported', 'unsupported_fixture')
        incoming, adjacency = {}, {name: set() for name in nodes}
        targets = set()
        for edge in topology['connections']:
            source, target = edge['source'], edge['target']
            source_id, target_id = source['device_id'], target['device_id']
            if source_id not in nodes or target_id not in nodes:
                raise ValueError('Unknown connected node')
            source_ports = profiles[nodes[source_id]]['ports']['outputs']
            target_ports = profiles[nodes[target_id]]['ports']['inputs']
            if (_kind(source_ports[source['port']]) != edge['kind']
                    or _kind(target_ports[target['port']]) != edge['kind']):
                raise ValueError('Port kind mismatch')
            key = (target_id, target['port'])
            if key in targets:
                raise ValueError('Duplicate input source')
            targets.add(key)
            if edge['kind'] == 'rf':
                incoming[key] = (source_id, source['port'])
                adjacency[source_id].add(target_id)
        reachable, waiting = set(), [goal['dut_id']]
        while waiting:
            name = waiting.pop()
            if name not in reachable:
                reachable.add(name); waiting.extend(adjacency[name] - reachable)
        if goal['sensor_id'] not in reachable or (goal['sensor_id'], 'rf') not in incoming:
            raise _Reject('unsupported', 'unsupported_rf_path')
        return profiles, nodes, incoming

    def _node(self, observed, identity, profiles, nodes):
        node = observed['devices'][identity]
        if (type(node) is not dict or node.get('device_id') != identity or node.get('profile_id') != nodes[identity]
                or node.get('role') != profiles[nodes[identity]]['role']
                or node.get('tick') != observed['tick'] or type(node.get('tick')) is not int
                or node.get('setup_revision') != observed['setup_revision'] or type(node.get('setup_revision')) is not int
                or node.get('synthetic') is not True or node.get('hardware_verified') is not False
                or node.get('status') not in _STATUSES or type(node.get('values')) is not dict
                or type(node['values'].get('outputs')) is not dict):
            raise ValueError('Inconsistent node snapshot')
        return node

    def _wait(self):
        self._acquire = self._read = None
        return {'kind': 'advance', 'ticks': 1}

    def _decide(self, goal, observed, dut, sensor, profiles, nodes, incoming):
        dut_id, sensor_id = goal['dut_id'], goal['sensor_id']
        if dut['values'].get('configured') is not True or sensor['values'].get('configured') is not True:
            return _stop('blocked', 'fixture_configuration_required')
        if dut['status'] in {'disconnected', 'error', 'invalid', 'pending'}:
            return self._wait()
        if dut['status'] != 'ok':
            return _stop('unsupported', 'unsupported_dut_state')
        output = dut['values']['outputs'].get('rf')
        if output is None:
            self._acquire = self._read = None
            if dut['values'].get('state') in {'idle', 'configured'}:
                return _execute(dut_id, 'start')
            return {'kind': 'advance', 'ticks': 1}
        _signal(output, dut_id)
        source_id, source_port = incoming[(sensor_id, 'rf')]
        upstream = self._node(observed, source_id, profiles, nodes)
        source = upstream['values']['outputs'].get(source_port)
        if upstream['status'] != 'ok' or source is None:
            return self._wait()
        source = _signal(source, source_id)
        if sensor['status'] in {'disconnected', 'error'}:
            return self._wait()
        if sensor['status'] == 'unsupported':
            return _stop('unsupported', 'unsupported_sensor_state')
        if sensor['values'].get('reason') in {'calibration_unavailable', 'measurement_not_valid', 'output_disabled'}:
            return _stop('blocked', 'sensor_not_ready')
        if sensor['status'] == 'pending':
            return {'kind': 'advance', 'ticks': 1}
        sample = sensor['values']['outputs'].get('measurement')
        if sample is not None:
            if sensor['status'] != 'ok':
                raise ValueError('Measurement in invalid state')
            self._measurement(sample, source, observed, sensor_id)
            fresh = (sample['acquisition_tick'] >= goal['minimum_acquisition_tick']
                     and self._acquire is not None and sample['acquisition_tick'] > self._acquire[0])
            if fresh:
                signature = tuple(sample[name] for name in
                                  ('value', 'power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db',
                                   'unit', 'source_id', 'acquisition_tick', 'acquisition_setup_revision'))
                if self._read == signature:
                    return _stop('completed', 'fresh_measurement_observed')
                if self._read is not None:
                    raise ValueError('Measurement changed during read')
                self._read = signature
                return _execute(sensor_id, 'read')
        if observed['tick'] + 1 < goal['minimum_acquisition_tick']:
            return {'kind': 'advance', 'ticks': 1}
        self._acquire = (observed['tick'], observed['setup_revision'])
        self._read = None
        return _execute(sensor_id, 'acquire')

    def _measurement(self, sample, source, observed, sensor_id):
        if (type(sample) is not dict or sample.get('status') != 'ok' or sample.get('valid') is not True
                or sample.get('source_id') != sensor_id or sample.get('unit') != 'dBm'
                or not _integer(sample.get('acquisition_tick')) or sample['acquisition_tick'] > observed['tick']
                or type(sample.get('acquisition_setup_revision')) is not int
                or sample['acquisition_setup_revision'] != observed['setup_revision']):
            raise ValueError('Invalid measurement provenance')
        for name in ('value', 'power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db'):
            if not _finite(sample.get(name)):
                raise ValueError('Invalid measurement number')
        if sample['value'] != sample['power_dbm'] or sample['value'] != source['power_dbm']:
            raise ValueError('Measurement is not the observed ON mean')
        if any(sample[name] != source[name] for name in ('frequency_hz', 'duty_cycle', 'crest_factor_db')):
            raise ValueError('Measurement and input disagree')
