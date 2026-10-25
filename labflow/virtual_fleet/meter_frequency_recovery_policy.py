"""Observation-only, explicitly delegated single-frequency virtual meter recovery."""
import json

from .policies import (RFSensorFixturePolicy, _finite, _identifier, _integer,
                       _json_tree, _kind, _signal)


_CONTEXT = {'schema_version', 'goal', 'catalog', 'topology', 'role_actions',
            'observations', 'last_receipt', 'remaining_budget'}
_STATUSES = {'ok', 'pending', 'invalid', 'unsupported', 'error', 'disconnected'}
_SENSOR_FIELDS = ('value', 'power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db',
                  'unit', 'source_id', 'acquisition_tick', 'acquisition_setup_revision')
_METER_FIELDS = ('value', 'unit', 'quantity', 'source_id', 'input_source_id',
                 'acquisition_tick', 'acquisition_setup_revision', 'configuration_revision',
                 'simulation_basis', 'frequency_hz', 'duty_cycle', 'crest_factor_db', 'window')


class _Reject(Exception):
    def __init__(self, claim, reason):
        self.claim, self.reason = claim, reason


def _require(condition):
    if not condition:
        raise ValueError('Invalid public context')


def _stop(claim, reason):
    return {'kind': 'stop', 'claim': claim, 'reason': reason}


class RFMeterFrequencyRecoveryPolicy:
    """One instance per live harness run; the harness owns transport and IDs.

    A configuration ACK cannot complete this policy. Both instruments must be
    acquired again, and the final fetch must confirm the current observation.
    """

    policy_id = 'rf_meter_frequency_recovery_v1'

    def __init__(self):
        self._binding = self._clock = self._terminal = None
        self._configuration = self._configuration_revision = None
        self._pending = self._sensor_signature = self._acquire = self._fetch = None
        self._sensor = RFSensorFixturePolicy()
        self._phase = 'sensor'
        self._minimum = None
        self._attempted = False
        self._target = None

    def __call__(self, context):
        if self._terminal is not None:
            return dict(self._terminal)
        try:
            goal, observed, profiles, nodes, upstream = self._context(context)
            meter = self._node(observed, goal['meter_id'], profiles, nodes)
            configuration, revision = self._settings(meter)
            previous, receipt = self._receipt(context, observed, profiles, nodes)
            configuring = previous is not None and previous[2] == 'configure'
            if configuring:
                proposal = self._configured(goal, observed, meter, receipt, configuration, revision)
            else:
                if self._configuration is None:
                    self._configuration = dict(configuration)
                    self._configuration_revision = revision
                if configuration != self._configuration or revision != self._configuration_revision:
                    raise _Reject('failed', 'meter_context_changed')
                if self._phase == 'sensor':
                    proposal = self._sensor_step(context, goal, observed, profiles, nodes, upstream)
                else:
                    proposal = self._meter_step(goal, observed, meter, previous, receipt,
                                                profiles, nodes, upstream)
            if proposal['kind'] == 'stop':
                self._terminal = dict(proposal)
            else:
                self._pending = (proposal['kind'], proposal.get('device_id'),
                                 proposal.get('action'), observed['tick'], observed['setup_revision'])
            return proposal
        except _Reject as error:
            self._terminal = _stop(error.claim, error.reason)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
            self._terminal = _stop('failed', 'invalid_public_context')
        return dict(self._terminal)

    def _context(self, context):
        _json_tree(context)
        _require(len(json.dumps(context, ensure_ascii=False, allow_nan=False).encode('utf-8')) <= 1024 * 1024)
        _require(type(context) is dict and set(context) == _CONTEXT
                 and type(context['schema_version']) is int and context['schema_version'] == 1)
        _require(all(type(context[n]) is dict for n in
                     ('catalog', 'topology', 'role_actions', 'remaining_budget')))
        goal = context['goal']
        _require(type(goal) is dict and set(goal) == {
            'kind', 'dut_id', 'sensor_id', 'meter_id', 'minimum_acquisition_tick',
            'allow_meter_frequency_reconfigure'})
        ids = [goal[n] for n in ('dut_id', 'sensor_id', 'meter_id')]
        _require(goal['kind'] == 'acquire_fresh_rf_sensor_meter'
                 and all(_identifier(i) for i in ids) and len(set(ids)) == 3
                 and _integer(goal['minimum_acquisition_tick'])
                 and type(goal['allow_meter_frequency_reconfigure']) is bool)
        observed = context['observations']
        _require(type(observed) is dict and observed.get('synthetic') is True
                 and observed.get('hardware_verified') is False
                 and _integer(observed.get('tick')) and _integer(observed.get('setup_revision'))
                 and type(observed.get('devices')) is dict)
        clock = (observed['tick'], observed['setup_revision'])
        _require(self._clock is None or all(new >= old for new, old in zip(clock, self._clock)))
        binding = json.dumps({n: context[n] for n in ('goal', 'catalog', 'topology', 'role_actions')},
                             sort_keys=True, ensure_ascii=False, allow_nan=False)
        _require(self._binding is None or binding == self._binding)
        profiles, nodes, upstream = self._metadata(context, goal)
        for identity in ids:
            self._node(observed, identity, profiles, nodes)
        self._binding, self._clock = binding, clock
        if self._minimum is None:
            self._minimum = goal['minimum_acquisition_tick']
        return goal, observed, profiles, nodes, upstream

    def _metadata(self, context, goal):
        profiles, nodes = {}, {}
        _require(type(context['catalog'].get('profiles')) is list)
        for p in context['catalog']['profiles']:
            _require(type(p) is dict and _identifier(p.get('profile_id'))
                     and p['profile_id'] not in profiles)
            profiles[p['profile_id']] = p
        topology = context['topology']
        _require(type(topology.get('devices')) is list and type(topology.get('connections')) is list)
        for node in topology['devices']:
            _require(type(node) is dict and _identifier(node.get('id')) and node['id'] not in nodes
                     and node.get('profile_id') in profiles)
            nodes[node['id']] = node['profile_id']
        for key, role, actions in (
            ('dut_id', 'dut', ('start',)), ('sensor_id', 'power_sensor', ('acquire', 'read')),
            ('meter_id', 'power_meter', ('acquire', 'fetch', 'configure')),
        ):
            identity = goal[key]
            if identity not in nodes or profiles[nodes[identity]]['role'] != role:
                raise _Reject('unsupported', 'unsupported_fixture')
            declared = context['role_actions'].get(role, {})
            _require(type(declared) is dict)
            for action in actions:
                if action not in declared:
                    raise _Reject('unsupported', 'unsupported_fixture')
                declaration = declared[action]
                _require(type(declaration) is dict and type(declaration.get('parameters', {})) is dict)
                parameters = declaration.get('parameters', {})
                for name, rule in parameters.items():
                    _require(type(rule) is dict and type(rule.get('required', False)) is bool)
                    if rule.get('required', False) and not (action == 'configure' and name == 'frequency_hz'):
                        raise _Reject('unsupported', 'unsupported_fixture')
                if action == 'configure':
                    if parameters.get('frequency_hz', {}).get('type') != 'number':
                        raise _Reject('unsupported', 'unsupported_fixture')
        incoming, adjacency = {}, {name: set() for name in nodes}
        for edge in topology['connections']:
            source, target = edge['source'], edge['target']
            source_id, target_id = source['device_id'], target['device_id']
            _require(source_id in nodes and target_id in nodes)
            out = profiles[nodes[source_id]]['ports']['outputs'][source['port']]
            into = profiles[nodes[target_id]]['ports']['inputs'][target['port']]
            _require(_kind(out) == edge['kind'] == _kind(into))
            key = (target_id, target['port'])
            _require(key not in incoming)
            incoming[key] = (source_id, source['port'], edge['kind'])
            if edge['kind'] == 'rf':
                adjacency[source_id].add(target_id)
        reached, waiting = set(), [goal['dut_id']]
        while waiting:
            name = waiting.pop()
            if name not in reached:
                reached.add(name)
                waiting.extend(adjacency[name] - reached)
        upstream = incoming.get((goal['sensor_id'], 'rf'))
        if (goal['sensor_id'] not in reached or upstream is None or upstream[2] != 'rf'
                or incoming.get((goal['meter_id'], 'sensor')) !=
                (goal['sensor_id'], 'measurement', 'measurement')):
            raise _Reject('unsupported', 'unsupported_rf_path')
        return profiles, nodes, upstream

    def _node(self, observed, identity, profiles, nodes):
        node = observed['devices'][identity]
        _require(type(node) is dict and node.get('device_id') == identity
                 and node.get('profile_id') == nodes[identity]
                 and node.get('role') == profiles[nodes[identity]]['role']
                 and type(node.get('tick')) is int and node['tick'] == observed['tick']
                 and type(node.get('setup_revision')) is int
                 and node['setup_revision'] == observed['setup_revision']
                 and node.get('synthetic') is True and node.get('hardware_verified') is False
                 and node.get('status') in _STATUSES and type(node.get('values')) is dict
                 and type(node['values'].get('outputs')) is dict)
        return node

    def _settings(self, meter):
        configuration = meter['values'].get('configuration')
        revision = meter['values'].get('configuration_revision')
        _require(type(configuration) is dict and _integer(revision))
        if (configuration.get('measurement_mode') != 'on_average' or configuration.get('unit') != 'dBm'
                or type(configuration.get('window')) is not int or configuration['window'] != 1
                or configuration.get('trigger_source') != 'immediate'):
            raise _Reject('unsupported', 'unsupported_meter_configuration')
        _require(_finite(configuration.get('frequency_hz')) and configuration['frequency_hz'] > 0)
        return configuration, revision

    def _receipt(self, context, observed, profiles, nodes):
        previous, self._pending = self._pending, None
        receipt = context['last_receipt']
        if previous is None:
            return previous, receipt
        operation, identity, action, tick, revision = previous
        _require(type(receipt) is dict and receipt.get('status') in _STATUSES
                 and type(receipt.get('values')) is dict
                 and receipt.get('synthetic') is True and receipt.get('hardware_verified') is False
                 and type(receipt.get('tick')) is int and receipt['tick'] == observed['tick']
                 and receipt['tick'] == tick + int(operation == 'advance')
                 and type(receipt.get('setup_revision')) is int
                 and receipt['setup_revision'] == observed['setup_revision']
                 and receipt['setup_revision'] >= revision)
        if operation == 'advance':
            _require(receipt['status'] == 'ok' and type(receipt['values'].get('advanced_ticks')) is int
                     and receipt['values']['advanced_ticks'] == 1)
        else:
            _require(receipt.get('device_id') == identity and receipt.get('profile_id') == nodes[identity]
                     and receipt.get('role') == profiles[nodes[identity]]['role'])
            if profiles[nodes[identity]]['role'] == 'power_meter' and (
                    receipt['status'] in {'ok', 'pending'}
                    or receipt['values'].get('reason') == 'sensor_frequency_setting_conflict'):
                current = observed['devices'][identity]['values']
                received_configuration = receipt['values'].get('configuration')
                _require(type(received_configuration) is dict
                         and type(received_configuration.get('window')) is int
                         and _finite(received_configuration.get('frequency_hz'))
                         and received_configuration == current['configuration']
                         and type(receipt['values'].get('configuration_revision')) is int
                         and receipt['values']['configuration_revision'] == current['configuration_revision'])
            if action == 'read':
                sensor = observed['devices'][identity]['values']['outputs'].get('measurement')
                received = receipt['values'].get('outputs', {}).get('measurement')
                _require(receipt['status'] == 'ok' and sensor is not None and type(received) is dict
                         and received.get('status') == 'ok' and received.get('valid') is True
                         and _integer(received.get('acquisition_tick'))
                         and _integer(received.get('acquisition_setup_revision'))
                         and all(_finite(received.get(n)) for n in
                                 ('value', 'power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db'))
                         and received == sensor)
        return previous, receipt

    def _configured(self, goal, observed, meter, receipt, configuration, revision):
        if receipt['status'] != 'ok':
            return _stop('blocked', 'meter_configuration_failed')
        expected = dict(self._configuration, frequency_hz=self._target)
        _require(self._attempted and receipt.get('setup_changed') is True
                 and receipt['setup_revision'] > self._acquire[1]
                 and configuration == expected and revision == self._configuration_revision + 1
                 and receipt['values'].get('configuration') == configuration
                 and receipt['values'].get('configuration_revision') == revision
                 and not receipt['values'].get('outputs') and not meter['values']['outputs'])
        self._configuration, self._configuration_revision = dict(configuration), revision
        self._sensor = RFSensorFixturePolicy()
        self._minimum = max(goal['minimum_acquisition_tick'], receipt['tick'] + 1)
        self._sensor_signature = self._acquire = self._fetch = None
        self._phase = 'sensor'
        # The new child sees the same runtime only on the next decision.
        return {'kind': 'advance', 'ticks': 1}

    def _sensor_current(self, goal, observed, profiles, nodes, upstream):
        dut = self._node(observed, goal['dut_id'], profiles, nodes)
        _require(dut['status'] == 'ok' and dut['values'].get('configured') is True)
        dut_signal = _signal(dut['values']['outputs'].get('rf'), goal['dut_id'])
        sensor = self._node(observed, goal['sensor_id'], profiles, nodes)
        sample = sensor['values']['outputs'].get('measurement')
        _require(sensor['status'] == 'ok' and type(sample) is dict and sample.get('status') == 'ok'
                 and sample.get('valid') is True and sample.get('unit') == 'dBm'
                 and sample.get('source_id') == goal['sensor_id']
                 and _integer(sample.get('acquisition_tick')) and sample['acquisition_tick'] <= observed['tick']
                 and sample['acquisition_tick'] >= self._minimum
                 and type(sample.get('acquisition_setup_revision')) is int
                 and sample['acquisition_setup_revision'] == observed['setup_revision'])
        for field in ('value', 'power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db'):
            _require(_finite(sample.get(field)))
        _require(sample['value'] == sample['power_dbm'] and sample['frequency_hz'] > 0
                 and 0 < sample['duty_cycle'] <= 1 and sample['crest_factor_db'] >= 0)
        source = self._node(observed, upstream[0], profiles, nodes)
        _require(source['status'] == 'ok')
        signal = _signal(source['values']['outputs'].get(upstream[1]), upstream[0])
        _require(all(sample[n] == signal[n] for n in
                     ('power_dbm', 'frequency_hz', 'duty_cycle', 'crest_factor_db')))
        _require(all(sample[n] == dut_signal[n] for n in ('frequency_hz', 'duty_cycle', 'crest_factor_db')))
        if self._target is not None and sample['frequency_hz'] != self._target:
            raise _Reject('failed', 'meter_context_changed')
        return sample

    def _sensor_step(self, context, goal, observed, profiles, nodes, upstream):
        child_context = dict(context, goal={
            'kind': 'acquire_fresh_rf_sensor', 'dut_id': goal['dut_id'], 'sensor_id': goal['sensor_id'],
            'minimum_acquisition_tick': self._minimum})
        proposal = self._sensor(child_context)
        if proposal['kind'] != 'stop' or proposal['claim'] != 'completed':
            return proposal
        sample = self._sensor_current(goal, observed, profiles, nodes, upstream)
        self._sensor_signature = tuple(sample[n] for n in _SENSOR_FIELDS)
        self._phase = 'meter'
        self._acquire = (observed['tick'], observed['setup_revision'])
        return self._execute(goal['meter_id'], 'acquire')

    def _meter_sample(self, sample, goal, observed, sensor):
        _require(type(sample) is dict and sample.get('status') == 'ok' and sample.get('valid') is True
                 and sample.get('source_id') == goal['meter_id'] and sample.get('input_source_id') == goal['sensor_id']
                 and sample.get('unit') == 'dBm' and sample.get('quantity') == 'on_average'
                 and sample.get('simulation_basis') == 'declared_synthetic_policy'
                 and type(sample.get('window')) is int and sample['window'] == 1
                 and type(sample.get('configuration_revision')) is int
                 and sample['configuration_revision'] == self._configuration_revision
                 and type(sample.get('acquisition_setup_revision')) is int
                 and sample['acquisition_setup_revision'] == observed['setup_revision'] == self._acquire[1]
                 and _integer(sample.get('acquisition_tick'))
                 and max(self._acquire[0], sensor['acquisition_tick']) < sample['acquisition_tick'] <= observed['tick'])
        _require(all(_finite(sample.get(n)) for n in
                     ('value', 'frequency_hz', 'duty_cycle', 'crest_factor_db')))
        _require(abs(sample['value'] - sensor['power_dbm']) <= 1e-9
                 and all(sample[n] == sensor[n] for n in ('frequency_hz', 'duty_cycle', 'crest_factor_db'))
                 and abs(self._configuration['frequency_hz'] - sensor['frequency_hz']) <= 1)
        return tuple(sample[n] for n in _METER_FIELDS)

    def _meter_step(self, goal, observed, meter, previous, receipt, profiles, nodes, upstream):
        sensor = self._sensor_current(goal, observed, profiles, nodes, upstream)
        _require(tuple(sensor[n] for n in _SENSOR_FIELDS) == self._sensor_signature)
        if meter['values'].get('calibration_state') != 'valid':
            return _stop('blocked', 'meter_not_ready')
        acquired = previous is not None and previous[1:3] == (goal['meter_id'], 'acquire')
        if acquired and receipt['status'] == 'invalid' and meter['status'] == 'invalid':
            if (receipt['values'].get('reason') == 'sensor_frequency_setting_conflict'
                    and meter['values'].get('reason') == 'sensor_frequency_setting_conflict'):
                _require(not receipt['values'].get('outputs') and not meter['values']['outputs']
                         and abs(self._configuration['frequency_hz'] - sensor['frequency_hz']) > 1)
                if not goal['allow_meter_frequency_reconfigure']:
                    return _stop('blocked', 'meter_frequency_reconfigure_not_allowed')
                if self._attempted:
                    return _stop('blocked', 'meter_frequency_recovery_exhausted')
                self._attempted, self._target = True, sensor['frequency_hz']
                self._phase = 'configure'
                return self._execute(goal['meter_id'], 'configure', {'frequency_hz': self._target})
        if acquired and receipt['status'] not in {'ok', 'pending'}:
            return _stop('blocked', 'meter_not_ready')
        sample = meter['values']['outputs'].get('measurement')
        if meter['status'] == 'pending' and self._fetch is None:
            _require(sample is None)
            return {'kind': 'advance', 'ticks': 1}
        if meter['status'] != 'ok':
            return _stop('blocked', 'meter_not_ready')
        signature = self._meter_sample(sample, goal, observed, sensor)
        if self._fetch is None:
            self._fetch = signature
            return self._execute(goal['meter_id'], 'fetch')
        _require(previous is not None and previous[1:3] == (goal['meter_id'], 'fetch')
                 and receipt['status'] == 'ok'
                 and receipt['values'].get('configuration') == self._configuration
                 and receipt['values'].get('configuration_revision') == self._configuration_revision
                 and self._meter_sample(receipt['values'].get('outputs', {}).get('measurement'),
                                        goal, observed, sensor) == signature == self._fetch)
        return _stop('completed', 'fresh_sensor_meter_measurement_observed')

    @staticmethod
    def _execute(identity, action, parameters=None):
        return {'kind': 'execute', 'device_id': identity, 'action': action,
                'parameters': {} if parameters is None else parameters}
