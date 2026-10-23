import copy
import math
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch


class SampleDevice:
    def __init__(self, profile, seed):
        self.profile = profile
        self.seed = seed
        self.value = 1
        self.calls = 0
        self.inputs = {}
        self.last_revision = 0
        self.ready_at = None
        self.acquired_revision = None
        self.result = None
        self.offline = False

    def perform(self, action, parameters, *, tick, setup_revision, inputs):
        self.calls += 1
        if action == 'set':
            self.value = parameters['value']
            return {'status': 'ok', 'values': {}, 'setup_changed': True}
        if action == 'start':
            self.ready_at = tick + 2
            self.acquired_revision = setup_revision
            self.result = None
            return {'status': 'pending', 'values': {}, 'setup_changed': False}
        return {'status': 'ok', 'values': {'seed_sample': self.seed}, 'setup_changed': False}

    def advance(self, *, tick, setup_revision, inputs):
        self.inputs = copy.deepcopy(inputs)
        self.last_revision = setup_revision
        if self.acquired_revision != setup_revision:
            self.result = None
        elif self.ready_at is not None and tick >= self.ready_at:
            self.result = self.value

    def observation(self, *, tick, setup_revision):
        if self.offline:
            return {'status': 'disconnected', 'values': {'outputs': {'out': {'value': self.value}}}}
        return {
            'status': 'ok', 'state': 'ready',
            'values': {'outputs': {'out': {'value': self.value}}, 'inputs': self.inputs,
                       'result': self.result, 'acquisition_revision': self.acquired_revision},
            'synthetic': False, 'hardware_verified': True, 'tick': -1,
            'profile_id': 'forged', 'fault': 'private-author-secret',
        }

    def author_control(self, fault, value):
        if fault != 'private-author-secret' or not isinstance(value, bool):
            raise ValueError('unknown author control')
        self.offline = value


ACTIONS = {'sample': {
    'set': {'parameters': {'value': {'type': 'number', 'required': True}}, 'completion': 'immediate'},
    'start': {'parameters': {}, 'completion': 'two ticks'},
    'read': {'parameters': {}, 'completion': 'immediate'},
}}


def catalog():
    return {'profiles': [{
        'profile_id': 'synthetic-sample', 'role': 'sample', 'model': 'Synthetic fixture',
        'manufacturer': 'Simulation', 'variant': '', 'evidence_refs': [],
        'simulation_basis': 'synthetic acceptance fixture', 'capability_scope': 'test',
        'ports': {'inputs': {'in': 'data'}, 'outputs': {'out': 'data'}},
    }]}


def topology():
    return {'devices': [{'id': 'a', 'profile_id': 'synthetic-sample'},
                        {'id': 'b', 'profile_id': 'synthetic-sample'}],
            'connections': [{'source': {'device_id': 'a', 'port': 'out'},
                             'target': {'device_id': 'b', 'port': 'in'}, 'kind': 'data'}]}


class VirtualFleetCoreTests(unittest.TestCase):
    def setUp(self):
        from labflow.virtual_fleet.core import VirtualFleet
        self.kind = VirtualFleet

    def fleet(self, **kwargs):
        return self.kind(kwargs.pop('catalog', catalog()), kwargs.pop('topology', topology()),
                         factories=kwargs.pop('factories', {'sample': SampleDevice}),
                         role_actions=kwargs.pop('role_actions', ACTIONS), **kwargs)

    def test_dag_propagates_current_outputs_and_trusted_provenance(self):
        fleet = self.fleet()
        response = fleet.execute('configure', 'a', 'set', {'value': 7})
        self.assertEqual(response['setup_revision'], 1)
        observations = fleet.observations()
        self.assertEqual(observations['devices']['b']['values']['inputs']['in']['value'], 7)
        self.assertEqual(observations['devices']['b']['values']['inputs']['in']['source_id'], 'a')
        row = observations['devices']['a']
        self.assertTrue(row['synthetic'])
        self.assertFalse(row['hardware_verified'])
        self.assertEqual(row['profile_id'], 'synthetic-sample')
        self.assertEqual(row['tick'], 0)
        self.assertNotIn('fault', row)

    def test_duplicate_is_exact_and_copy_isolation_including_cached_reply(self):
        fleet = self.fleet()
        first = fleet.execute('configure', 'a', 'set', {'value': 4})
        fleet.advance('clock', 3)
        retry = fleet.execute('configure', 'a', 'set', {'value': 4.0})
        self.assertEqual(first, retry)
        retry['values']['mutated'] = True
        self.assertNotIn('mutated', fleet.execute('configure', 'a', 'set', {'value': 4})['values'])
        self.assertEqual(fleet.observations()['setup_revision'], 1)
        self.assertEqual(fleet.history()[-1]['outcome'], 'duplicate')

    def test_request_conflicts_include_device_action_parameters_and_kind(self):
        variants = [('a', 'set', {'value': 9}), ('b', 'set', {'value': 3}), ('a', 'read', {})]
        for device, action, params in variants:
            fleet = self.fleet()
            fleet.execute('id', 'a', 'set', {'value': 3})
            with self.assertRaises(ValueError):
                fleet.execute('id', device, action, params)
        fleet = self.fleet()
        fleet.execute('same', 'a', 'read')
        with self.assertRaises(ValueError):
            fleet.advance('same', 1)

    def test_author_namespace_is_separate_and_secret_is_not_in_public_views(self):
        fleet = self.fleet()
        fleet.execute('same-id', 'a', 'read')
        reply = fleet.author_control('same-id', 'a', 'private-author-secret', True)
        self.assertEqual(reply['status'], 'ok')
        self.assertEqual(fleet.observations()['devices']['a']['status'], 'disconnected')
        public = repr([fleet.observations(), fleet.coverage(), fleet.history(), reply])
        self.assertNotIn('private-author-secret', public)
        self.assertNotIn('author_control', repr(fleet.history()))
        with self.assertRaises(ValueError):
            fleet.author_control('same-id', 'a', 'private-author-secret', False)

    def test_invalid_upstream_is_marked_invalid_instead_of_a_healthy_value(self):
        fleet = self.fleet()
        fleet.author_control('offline', 'a', 'private-author-secret', True)
        data = fleet.observations()['devices']['b']['values']['inputs']['in']
        self.assertIs(data['valid'], False)
        self.assertEqual(data['upstream_status'], 'disconnected')

    def test_virtual_ticks_and_revision_invalidate_completed_and_pending_results(self):
        fleet = self.fleet()
        fleet.execute('start', 'b', 'start')
        fleet.advance('one', 1)
        self.assertIsNone(fleet.observations()['devices']['b']['values']['result'])
        fleet.advance('two', 1)
        self.assertEqual(fleet.observations()['devices']['b']['values']['result'], 1)
        fleet.execute('change', 'a', 'set', {'value': 8})
        self.assertIsNone(fleet.observations()['devices']['b']['values']['result'])
        fleet.execute('restart', 'b', 'start')
        fleet.execute('another-change', 'a', 'set', {'value': 9})
        fleet.advance('finish', 3)
        self.assertIsNone(fleet.observations()['devices']['b']['values']['result'])

    def test_reproducible_seed_order_and_input_copy(self):
        a, b = self.fleet(seed=42), self.fleet(seed=42)
        for fleet in [a, b]:
            fleet.execute('set', 'a', 'set', {'value': 12})
            fleet.advance('clock', 2)
        self.assertEqual(a.observations(), b.observations())
        self.assertEqual(a.execute('read-a', 'a', 'read'), b.execute('read-a', 'a', 'read'))
        obs = a.observations()
        obs['devices']['a']['values']['outputs']['out']['value'] = -100
        self.assertEqual(a.observations()['devices']['a']['values']['outputs']['out']['value'], 12)

    def test_unknown_action_and_bad_parameters_are_explicit_and_recorded(self):
        fleet = self.fleet()
        self.assertEqual(fleet.execute('unknown', 'a', 'missing')['status'], 'unsupported')
        for index, args in enumerate([{}, {'value': True}, {'value': '3'}, {'value': 2, 'extra': 1}]):
            self.assertEqual(fleet.execute(f'bad-{index}', 'a', 'set', args)['status'], 'invalid')
        self.assertEqual(fleet.observations()['setup_revision'], 0)
        self.assertEqual(fleet.execute('unknown-device', 'none', 'read')['status'], 'invalid')

    def test_invalid_json_request_ids_ticks_and_seed_are_rejected(self):
        fleet = self.fleet()
        for value in [math.inf, math.nan, float('-inf')]:
            with self.assertRaises(ValueError):
                fleet.execute('bad', 'a', 'set', {'value': value})
        for value in [None, '', True, [], 'x' * 129]:
            with self.assertRaises(ValueError):
                fleet.execute(value, 'a', 'read')
        for ticks in [0, -1, True, 1.5, 10001]:
            with self.assertRaises(ValueError):
                fleet.advance('clock', ticks)
        with self.assertRaises(ValueError):
            self.fleet(seed=True)

    def test_profile_device_role_port_and_graph_validation_precedes_factory(self):
        cases = []
        c, t = catalog(), topology(); c['profiles'].append(copy.deepcopy(c['profiles'][0])); cases.append((c, t))
        c, t = catalog(), topology(); t['devices'].append(copy.deepcopy(t['devices'][0])); cases.append((c, t))
        c, t = catalog(), topology(); t['devices'][0]['profile_id'] = 'unknown'; cases.append((c, t))
        c, t = catalog(), topology(); c['profiles'][0]['role'] = 'unknown'; cases.append((c, t))
        c, t = catalog(), topology(); t['connections'][0]['source']['port'] = 'bad'; cases.append((c, t))
        c, t = catalog(), topology(); t['connections'][0]['kind'] = 'rf'; cases.append((c, t))
        c, t = catalog(), topology(); t['connections'].append(copy.deepcopy(t['connections'][0])); cases.append((c, t))
        c, t = catalog(), topology(); t['connections'].append({'source': {'device_id': 'b', 'port': 'out'}, 'target': {'device_id': 'a', 'port': 'in'}, 'kind': 'data'}); cases.append((c, t))
        c, t = catalog(), topology(); c['profiles'][0]['ports']['outputs']['out'] = 'unknown-kind'; cases.append((c, t))
        calls = []
        def factory(profile, seed):
            calls.append(profile)
            return SampleDevice(profile, seed)
        for c, t in cases:
            with self.assertRaises(ValueError):
                self.fleet(catalog=c, topology=t, factories={'sample': factory})
        self.assertEqual(calls, [])

    def test_catalog_topology_and_action_declarations_are_copy_isolated(self):
        c, t, actions = catalog(), topology(), copy.deepcopy(ACTIONS)
        fleet = self.fleet(catalog=c, topology=t, role_actions=actions)
        c['profiles'][0]['role'] = 'mutated'
        t['connections'].clear()
        actions['sample'].clear()
        self.assertEqual(fleet.execute('set', 'a', 'set', {'value': 5})['status'], 'ok')
        self.assertEqual(fleet.observations()['devices']['b']['values']['inputs']['in']['value'], 5)
        self.assertEqual(fleet.catalog['profiles'][0]['role'], 'sample')

    def test_contract_failure_is_not_a_numeric_or_successful_result(self):
        class Broken(SampleDevice):
            def perform(self, *args, **kwargs):
                return {'status': 'ok', 'values': {'reading': float('nan')}, 'setup_changed': False}
        fleet = self.fleet(factories={'sample': Broken})
        result = fleet.execute('broken', 'a', 'read')
        self.assertEqual(result['status'], 'error')
        self.assertNotIn('nan', repr(result).lower())
        self.assertEqual(fleet.observations()['devices']['a']['status'], 'error')
        self.assertEqual(fleet.observations()['devices']['b']['values']['inputs'].get('in', {}).get('valid'), False)

    def test_coverage_distinguishes_supported_exercised_and_unverified(self):
        fleet = self.fleet()
        fleet.execute('set', 'a', 'set', {'value': 5})
        coverage = fleet.coverage()
        self.assertEqual(coverage['devices']['a']['supported_actions'], ['read', 'set', 'start'])
        self.assertEqual(coverage['devices']['a']['exercised_actions'], ['set'])
        self.assertFalse(coverage['hardware_verified'])
        self.assertEqual(coverage['devices']['a']['scenario_validation'], 'not_assessed')

    def test_author_request_capacity_does_not_reduce_operator_capacity(self):
        with patch('labflow.virtual_fleet.core.MAX_REQUESTS', 2):
            fleet = self.fleet()
            fleet.author_control('hidden-1', 'a', 'private-author-secret', True)
            fleet.author_control('hidden-2', 'a', 'private-author-secret', False)
            self.assertEqual(fleet.execute('operator-1', 'a', 'read')['status'], 'ok')
            self.assertEqual(fleet.execute('operator-2', 'a', 'read')['status'], 'ok')
            with self.assertRaises(ValueError):
                fleet.execute('operator-3', 'a', 'read')

    def test_concurrent_retries_apply_once_and_keep_first_reply(self):
        fleet = self.fleet()
        with ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(lambda _: fleet.execute('shared', 'a', 'set', {'value': 9}), range(32)))
        self.assertTrue(all(reply == replies[0] for reply in replies))
        self.assertEqual(fleet.observations()['setup_revision'], 1)

    def test_non_json_objects_and_extreme_numeric_parameters_fail_without_progress(self):
        fleet = self.fleet()
        for index, value in enumerate([{1: 2}, {'value': (1, 2)}, {'value': 10 ** 1000}]):
            try:
                result = fleet.execute(f'invalid-{index}', 'a', 'set', value)
            except ValueError:
                continue
            self.assertEqual(result['status'], 'invalid')
        self.assertEqual(fleet.observations()['setup_revision'], 0)

    def test_malformed_graph_and_action_type_errors_are_value_errors(self):
        for field, value in [('device_id', []), ('port', {})]:
            t = topology(); t['connections'][0]['source'][field] = value
            with self.assertRaises(ValueError):
                self.fleet(topology=t)
        c = catalog(); c['profiles'][0]['ports']['outputs']['out'] = []
        with self.assertRaises(ValueError):
            self.fleet(catalog=c)
        actions = copy.deepcopy(ACTIONS); actions['sample']['set']['parameters']['value']['type'] = []
        with self.assertRaises(ValueError):
            self.fleet(role_actions=actions)

    def test_device_that_breaks_observation_after_action_cannot_return_success(self):
        class BreakOnChange(SampleDevice):
            def observation(self, **kwargs):
                if self.value != 1:
                    raise RuntimeError('sensitive implementation detail')
                return super().observation(**kwargs)
        fleet = self.fleet(factories={'sample': BreakOnChange})
        reply = fleet.execute('configure', 'a', 'set', {'value': 5})
        self.assertEqual(reply['status'], 'error')
        self.assertNotIn('sensitive implementation detail', repr([reply, fleet.history(), fleet.observations()]))

    def test_oversize_device_reply_and_missing_rf_units_are_not_accepted(self):
        class Oversized(SampleDevice):
            def perform(self, *args, **kwargs):
                return {'status': 'ok', 'values': {'body': 'x' * (1024 * 1024 - 100)}, 'setup_changed': False}
        fleet = self.fleet(factories={'sample': Oversized})
        self.assertEqual(fleet.execute('oversized', 'a', 'read')['status'], 'error')
        c, t = catalog(), topology()
        c['profiles'][0]['ports'] = {'inputs': {'in': 'rf'}, 'outputs': {'out': 'rf'}}
        t['connections'][0]['kind'] = 'rf'
        fleet = self.fleet(catalog=c, topology=t)
        self.assertEqual(fleet.observations()['devices']['a']['status'], 'error')

    def test_connected_empty_output_is_distinct_from_an_unconnected_input(self):
        class EmptySource(SampleDevice):
            def observation(self, **kwargs):
                result = super().observation(**kwargs)
                result['values']['outputs'] = {}
                return result
        fleet = self.fleet(factories={'sample': EmptySource})
        rows = fleet.observations()['devices']
        self.assertNotIn('in', rows['a']['values']['inputs'])
        marker = rows['b']['values']['inputs']['in']
        self.assertFalse(marker['valid'])
        self.assertEqual(marker['reason'], 'output_unavailable')
        self.assertEqual(marker['source_id'], 'a')

    def test_author_exception_after_mutation_quarantines_invalidates_and_caches_redacted_receipt(self):
        for exception_type in [RuntimeError, ValueError]:
            calls = []
            class BadAuthor(SampleDevice):
                def author_control(self, fault, value):
                    calls.append(1)
                    self.value = 99
                    raise exception_type('sensitive author implementation detail')
            fleet = self.fleet(factories={'sample': BadAuthor})
            fleet.execute('start-a', 'a', 'start')
            fleet.execute('start-b', 'b', 'start')
            fleet.advance('acquired', 2)
            self.assertEqual(fleet.observations()['devices']['a']['values']['result'], 1)
            receipt = fleet.author_control('hidden', 'a', 'private-author-secret', True)
            self.assertEqual(receipt['status'], 'error')
            rows = fleet.observations()['devices']
            self.assertEqual(rows['a']['status'], 'error')
            self.assertFalse(fleet.coverage()['devices']['a']['available'])
            self.assertIsNone(rows['b']['values']['result'])
            self.assertFalse(rows['b']['values']['inputs']['in']['valid'])
            revision = fleet.observations()['setup_revision']
            self.assertGreater(revision, 0)
            fleet.advance('later', 1)
            self.assertEqual(fleet.author_control('hidden', 'a', 'private-author-secret', True), receipt)
            self.assertEqual(fleet.observations()['setup_revision'], revision)
            self.assertEqual(len(calls), 1)
            self.assertEqual(fleet.execute('read-unavailable', 'a', 'read')['status'], 'error')
            public = repr([receipt, fleet.observations(), fleet.coverage(), fleet.history()])
            self.assertNotIn('sensitive author implementation detail', public)
            self.assertNotIn('private-author-secret', public)

    def test_propagation_revision_change_cannot_relabel_and_cache_an_old_valid_measurement(self):
        from labflow.virtual_fleet.facility import DEVICE_FACTORIES, ROLE_ACTIONS
        failure = {'armed': False}
        class FailElsewhere(SampleDevice):
            def observation(self, **kwargs):
                if failure['armed']:
                    failure['armed'] = False
                    raise RuntimeError('sensitive other-node failure')
                return super().observation(**kwargs)
        c = catalog()
        c['profiles'].append({'profile_id': 'synthetic-microscope', 'role': 'inspection_microscope',
                              'ports': {'inputs': {}, 'outputs': {'data': 'data'}}, 'simulation_parameters': {}})
        t = {'devices': [{'id': 'a-inspection', 'profile_id': 'synthetic-microscope'},
                         {'id': 'z-other', 'profile_id': 'synthetic-sample'}], 'connections': []}
        factories = dict(DEVICE_FACTORIES, sample=FailElsewhere)
        actions = dict(ROLE_ACTIONS, **ACTIONS)
        fleet = self.fleet(catalog=c, topology=t, factories=factories, role_actions=actions)
        loaded = fleet.execute('sample', 'a-inspection', 'load_sample',
                               {'sample_id': 'synthetic', 'feature_size_um': 11, 'surface_contrast': .9})
        self.assertEqual(loaded['status'], 'ok')
        fleet.execute('acquire', 'a-inspection', 'acquire')
        fleet.advance('complete', 2)
        previous = fleet.observations()['devices']['a-inspection']['values']['measurement']
        self.assertTrue(previous['valid'])
        failure['armed'] = True
        reply = fleet.execute('fetch-race', 'a-inspection', 'fetch')
        self.assertEqual(fleet.observations()['devices']['a-inspection']['status'], 'invalid')
        self.assertEqual(reply['status'], 'invalid')
        self.assertNotIn('measurement', reply['values'])
        self.assertEqual(reply['values']['reason'], 'setup_changed_during_action')
        self.assertGreater(reply['setup_revision'], previous['acquisition_revision'])
        fleet.advance('later', 1)
        self.assertEqual(fleet.execute('fetch-race', 'a-inspection', 'fetch'), reply)


if __name__ == '__main__':
    unittest.main()
