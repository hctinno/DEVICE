"""Bounded fixture harness contracts using only synthetic test doubles."""
import copy
import json
import unittest
from unittest.mock import patch

from labflow.virtual_fleet.harness import FleetHarness, RetryableTransportError


SECRET = 'PRIVATE_EXCEPTION_CANARY'
CATALOG = {'schema_version': 1, 'catalog_id': 'synthetic', 'profiles': [
    {'profile_id': 'sensor-policy', 'model': 'SYNTHETIC', 'manufacturer': 'TEST',
     'role': 'power_sensor', 'ports': {'inputs': {}, 'outputs': {'measurement': 'measurement'}},
     'simulation_parameters': {'seed': SECRET}, 'evidence_refs': []}]}
TOPOLOGY = {'devices': [{'id': 'sensor', 'profile_id': 'sensor-policy'}], 'connections': []}
ACTIONS = {'power_sensor': {
    'acquire': {'parameters': {}, 'completion': 'pending'},
    'read': {'parameters': {}, 'completion': 'cached'},
    'configure': {'parameters': {'gain_db': {'type': 'number', 'required': True, 'unit': 'dB'}}, 'completion': 'immediate'}}}
GOAL = {'kind': 'acquire_fresh_rf_sensor', 'sensor_id': 'sensor', 'minimum_acquisition_tick': 1}


def execute(action='acquire', parameters=None):
    return {'kind': 'execute', 'device_id': 'sensor', 'action': action, 'parameters': parameters or {}}


def advance():
    return {'kind': 'advance', 'ticks': 1}


def stop(claim='completed'):
    return {'kind': 'stop', 'claim': claim, 'reason': 'observed_evidence'}


class Clock:
    def __init__(self):
        self.time = 0.0

    def __call__(self):
        return self.time


class Policy:
    policy_id = 'synthetic_policy'

    def __init__(self, *proposals):
        self.proposals = list(proposals)
        self.contexts = []

    def __call__(self, context):
        self.contexts.append(copy.deepcopy(context))
        return copy.deepcopy(self.proposals.pop(0) if self.proposals else stop('blocked'))


class Runtime:
    def __init__(self):
        self.tick, self.revision = 10, 2
        self.requests, self.attempts = {}, []
        self.mutations = 0
        self.due = None
        self.lost = None
        self.observe_count = 0
        self.status = None

    def envelope(self, status, values=None):
        return {'status': status, 'values': values or {}, 'tick': self.tick,
                'setup_revision': self.revision, 'synthetic': True, 'hardware_verified': False,
                'device_id': 'sensor', 'profile_id': 'sensor-policy', 'role': 'power_sensor'}

    def dispatch(self, request_id, body, operation):
        self.attempts.append((request_id, copy.deepcopy(body)))
        if request_id in self.requests:
            old, reply = self.requests[request_id]
            if old != body:
                raise ValueError(SECRET)
            return copy.deepcopy(reply)
        self.mutations += 1
        if operation == 'advance':
            self.tick += body['ticks']
            reply = self.envelope('ok', {'advanced_ticks': 1})
        else:
            if body['action'] == 'acquire':
                self.due = self.tick+2
                reply = self.envelope('pending')
            elif body['action'] == 'configure':
                self.revision += 1
                reply = self.envelope('ok')
            else:
                reply = self.envelope(self.status or 'ok')
        self.requests[request_id] = (copy.deepcopy(body), copy.deepcopy(reply))
        if self.lost == operation:
            self.lost = None
            raise RetryableTransportError(SECRET)
        return reply

    def execute(self, request_id, device_id, action, parameters):
        return self.dispatch(request_id, {'device_id': device_id, 'action': action,
                                          'parameters': parameters}, 'execute')

    def advance(self, request_id, ticks):
        return self.dispatch(request_id, {'ticks': ticks}, 'advance')

    def observations(self):
        self.observe_count += 1
        outputs = {}
        if self.due is not None and self.tick >= self.due:
            outputs['measurement'] = {'status': 'ok', 'valid': True, 'source_id': 'sensor',
                'unit': 'dBm', 'value': 7.25, 'acquisition_tick': self.tick,
                'acquisition_setup_revision': self.revision}
        observed = self.envelope(self.status or 'ok', {'outputs': outputs})
        return {'tick': self.tick, 'setup_revision': self.revision, 'synthetic': True,
                'hardware_verified': False, 'devices': {'sensor': observed}}


def harness(policy=None, runtime=None, **kwargs):
    return FleetHarness(runtime or Runtime(), policy or Policy(stop()), goal=GOAL,
                        catalog=CATALOG, topology=TOPOLOGY, role_actions=ACTIONS,
                        run_id='synthetic-run', runtime_instance_id='synthetic-instance', **kwargs)


class FleetHarnessTests(unittest.TestCase):
    def test_normal_flow_has_fixed_context_events_and_independent_unassessed_result(self):
        policy = Policy(execute(), advance(), advance(), execute('read'), stop())
        runtime = Runtime()
        subject = harness(policy, runtime)
        self.assertIsNone(subject.result())
        result = subject.run()
        self.assertEqual(result['termination'], {'reason': 'policy_stop', 'policy_claim': 'completed'})
        self.assertEqual(result['policy'], {'kind': 'fixture', 'id': 'synthetic_policy'})
        self.assertEqual(result['task_outcome'], 'not_assessed')
        self.assertEqual(result['cleanup'], {'status': 'not_assessed', 'evidence_refs': []})
        self.assertEqual(result['assessment'], {'status': 'not_assessed', 'verdict': None,
                         'evaluator_id': None, 'evidence_refs': [], 'summary_code': None})
        self.assertEqual(result['usage']['decisions'], 5)
        self.assertEqual(result['usage']['logical_requests'], 4)
        self.assertEqual(result['usage']['tick_delta'], 2)
        self.assertTrue(result['evidence']['measurement_refs'])
        self.assertEqual(result['unresolved_request_ids'], [])
        self.assertEqual(set(policy.contexts[0]), {'schema_version', 'goal', 'catalog', 'topology',
                         'role_actions', 'observations', 'last_receipt', 'remaining_budget'})
        self.assertNotIn('simulation_parameters', json.dumps(policy.contexts))
        self.assertNotIn(SECRET, json.dumps(subject.events()))
        self.assertEqual([e['sequence'] for e in subject.events()], list(range(1, len(subject.events())+1)))
        self.assertEqual([e['event_id'] for e in subject.events()], ['event:'+str(i) for i in range(1, len(subject.events())+1)])
        self.assertEqual(subject.events()[0]['type'], 'observation')
        self.assertEqual(subject.events()[-1]['type'], 'termination')
        self.assertTrue(result['synthetic'])
        self.assertFalse(result['hardware_verified'])
        self.assertFalse(result['ai_model_called'])

    def test_step_stop_and_terminated_access_are_idempotent_and_detached(self):
        subject = harness(Policy(advance(), stop()))
        state = subject.step()
        self.assertEqual(state['state'], 'running')
        self.assertIsNone(state['result'])
        result = subject.run()
        count = len(subject.events())
        result['usage']['decisions'] = 999
        subject.events().clear()
        self.assertEqual(subject.step()['state'], 'terminated')
        self.assertEqual(subject.result()['usage']['decisions'], 2)
        self.assertEqual(len(subject.events()), count)
        self.assertIsNone(subject.stop())

    def test_supervisor_stop_before_policy_or_inside_policy_prevents_dispatch(self):
        runtime = Runtime()
        policy = Policy(execute())
        subject = harness(policy, runtime)
        subject.stop()
        self.assertEqual(subject.run()['termination']['reason'], 'supervisor_stop')
        self.assertEqual(policy.contexts, [])
        self.assertEqual(runtime.mutations, 0)
        def stopping(context):
            other.stop()
            return execute()
        other = harness(stopping, runtime)
        self.assertEqual(other.run()['termination']['reason'], 'supervisor_stop')
        self.assertEqual(runtime.mutations, 0)

    def test_policy_context_and_sink_mutation_cannot_change_subsequent_state(self):
        seen = []
        def policy(context):
            seen.append(copy.deepcopy(context))
            context['observations']['tick'] = 999
            context['catalog']['profiles'].clear()
            context['role_actions'].clear()
            return advance() if len(seen) == 1 else stop()
        def sink(event):
            event.clear()
        subject = harness(policy, event_sink=sink)
        subject.run()
        self.assertEqual(seen[1]['observations']['tick'], 11)
        self.assertEqual(len(seen[1]['catalog']['profiles']), 1)
        self.assertTrue(subject.events()[0]['payload'])

    def test_invalid_proposals_never_dispatch_and_are_charged_one_decision(self):
        proposals = [None, [], {'kind': 'advance', 'ticks': 2}, {'kind': 'advance', 'ticks': True},
                     {**execute(), 'request_id': 'forged'}, execute('author_control'),
                     {**execute(), 'device_id': 'unknown'}, execute('configure', {'gain_db': True}),
                     execute('configure', {'gain_db': float('nan')}), execute('configure'),
                     {'kind': 'stop', 'claim': 'PASS', 'reason': 'invented'},
                     {'kind': 'stop', 'claim': 'completed', 'reason': 'x', 'seed': SECRET},
                     execute('configure', {'gain_db': 2, 'unknown': 3})]
        for proposal in proposals:
            with self.subTest(proposal=proposal):
                runtime = Runtime()
                subject = harness(Policy(proposal), runtime)
                result = subject.run()
                self.assertEqual(result['termination']['reason'], 'invalid_proposal')
                self.assertEqual(result['usage']['decisions'], 1)
                self.assertEqual(runtime.mutations, 0)
                self.assertNotIn(SECRET, json.dumps(subject.events()))

    def test_decision_request_and_tick_budgets_allow_stop_but_no_excess_mutation(self):
        for budgets, proposals, reason, mutations in [
            ({'decisions': 1}, [advance(), advance()], 'decision_budget', 1),
            ({'logical_requests': 1}, [execute(), execute()], 'request_budget', 1),
            ({'ticks': 1}, [advance(), advance()], 'tick_budget', 1)]:
            with self.subTest(reason=reason):
                runtime = Runtime()
                result = harness(Policy(*proposals), runtime, budgets=budgets).run()
                self.assertEqual(result['termination']['reason'], reason)
                self.assertEqual(runtime.mutations, mutations)
        result = harness(Policy(advance(), stop()), budgets={'ticks': 1, 'logical_requests': 1}).run()
        self.assertEqual(result['termination']['reason'], 'policy_stop')

    def test_retry_lost_execute_and_advance_uses_same_id_and_body_once(self):
        for operation, proposal in [('execute', execute()), ('advance', advance())]:
            with self.subTest(operation=operation):
                runtime = Runtime()
                runtime.lost = operation
                subject = harness(Policy(proposal, stop()), runtime)
                result = subject.run()
                self.assertEqual(result['termination']['reason'], 'policy_stop')
                self.assertEqual(runtime.mutations, 1)
                self.assertEqual(runtime.attempts[0], runtime.attempts[1])
                self.assertEqual(result['usage']['logical_requests'], 1)
                self.assertEqual(result['usage']['transport_retries'], 1)
                self.assertEqual(result['usage']['tick_delta'], int(operation == 'advance'))
                self.assertEqual(result['usage']['reserved_ticks'], 0)
                retries = [e for e in subject.events() if e['type'] == 'transport_retry']
                self.assertEqual(retries[0]['payload']['retry'], 1)

    def test_retry_exhaustion_preserves_one_unresolved_intent_and_tick_reservation(self):
        runtime = Runtime()
        with patch.object(runtime, 'advance', side_effect=RetryableTransportError(SECRET)) as dispatch:
            subject = harness(Policy(advance()), runtime)
            result = subject.run()
        self.assertEqual(dispatch.call_count, 3)
        self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(result['usage']['transport_retries'], 2)
        self.assertEqual(result['usage']['reserved_ticks'], 1)
        self.assertEqual(len(result['unresolved_request_ids']), 1)
        self.assertNotIn(SECRET, json.dumps(result)+json.dumps(subject.events()))

    def test_known_invalid_unsupported_error_or_disconnected_are_not_transport_retries(self):
        for status in ['invalid', 'unsupported', 'error', 'disconnected']:
            runtime = Runtime()
            runtime.status = status
            policy = Policy(execute('read'), stop('blocked'))
            result = harness(policy, runtime).run()
            self.assertEqual(result['termination']['reason'], 'policy_stop')
            self.assertEqual(policy.contexts[-1]['last_receipt']['status'], status)
            self.assertEqual(result['usage']['transport_retries'], 0)

    def test_policy_and_initial_runtime_exceptions_are_redacted(self):
        def broken(context):
            raise RuntimeError(SECRET)
        subject = harness(broken)
        self.assertEqual(subject.run()['termination']['reason'], 'policy_error')
        self.assertNotIn(SECRET, json.dumps(subject.events())+json.dumps(subject.result()))
        runtime = Runtime()
        with patch.object(runtime, 'observations', side_effect=RuntimeError(SECRET)):
            subject = harness(runtime=runtime)
            self.assertEqual(subject.run()['termination']['reason'], 'runtime_error')
        self.assertEqual(subject.result()['unresolved_request_ids'], [])

    def test_raw_dispatch_exception_is_uncertain_and_never_retried(self):
        runtime = Runtime()
        with patch.object(runtime, 'execute', side_effect=RuntimeError(SECRET)) as dispatch:
            subject = harness(Policy(execute()), runtime)
            result = subject.run()
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(len(result['unresolved_request_ids']), 1)
        self.assertNotIn(SECRET, json.dumps(subject.events())+json.dumps(result))

    def test_intent_sink_must_finish_before_dispatch_and_failure_prevents_it(self):
        runtime = Runtime()
        accepted = []
        def sink(event):
            if event['type'] == 'intent':
                self.assertEqual(runtime.mutations, 0)
                raise OSError(SECRET)
            accepted.append(event)
        subject = harness(Policy(execute()), runtime, event_sink=sink)
        result = subject.run()
        self.assertEqual(result['termination']['reason'], 'evidence_error')
        self.assertEqual(runtime.mutations, 0)
        self.assertEqual(result['unresolved_request_ids'], [])
        self.assertFalse(any(e['type'] == 'intent' for e in subject.events()))

    def test_postdispatch_receipt_sink_failure_is_uncertain_and_does_not_repeat_mutation(self):
        runtime = Runtime()
        def sink(event):
            if event['type'] == 'receipt':
                raise OSError(SECRET)
        subject = harness(Policy(advance()), runtime, event_sink=sink)
        result = subject.run()
        self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(runtime.mutations, 1)
        self.assertEqual(len(result['unresolved_request_ids']), 1)
        self.assertEqual(result['usage']['reserved_ticks'], 1)
        self.assertNotIn(SECRET, json.dumps(subject.events())+json.dumps(result))

    def test_initial_sink_failure_and_termination_failure_are_evidence_errors(self):
        for kind in ['observation', 'termination']:
            def sink(event):
                if event['type'] == kind:
                    raise OSError(SECRET)
            subject = harness(Policy(stop()), event_sink=sink)
            self.assertEqual(subject.run()['termination']['reason'], 'evidence_error')

    def test_late_policy_and_initial_observation_return_wall_deadline(self):
        clock = Clock()
        def late(context):
            clock.time = 30
            return execute()
        runtime = Runtime()
        result = harness(late, runtime, clock=clock).run()
        self.assertEqual(result['termination']['reason'], 'wall_deadline')
        self.assertEqual(runtime.mutations, 0)
        clock.time = 0
        original = runtime.observations
        def observe():
            clock.time = 30
            return original()
        with patch.object(runtime, 'observations', side_effect=observe):
            self.assertEqual(harness(runtime=runtime, clock=clock).run()['termination']['reason'], 'wall_deadline')

    def test_late_mutation_response_is_uncertain_without_late_success_receipt(self):
        runtime, clock = Runtime(), Clock()
        original = runtime.advance
        def late(request_id, ticks):
            result = original(request_id, ticks)
            clock.time = 30
            return result
        with patch.object(runtime, 'advance', side_effect=late):
            subject = harness(Policy(advance(), stop()), runtime, clock=clock)
            result = subject.run()
        self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(result['usage']['reserved_ticks'], 1)
        self.assertFalse(any(e['type'] == 'receipt' for e in subject.events()))

    def test_constructor_rejects_invalid_budgets_and_identifiers(self):
        for budgets in [{'decisions': 0}, {'decisions': True}, {'ticks': 1.5},
                        {'wall_seconds': float('inf')}, {'wall_seconds': 0},
                        {'transport_retries': -1}, {'unknown': 1}]:
            with self.subTest(budgets=budgets), self.assertRaises(ValueError):
                harness(budgets=budgets)
        for bad in ['', '../path', 'x'*129, '한글']:
            with self.subTest(run_id=bad), self.assertRaises(ValueError):
                FleetHarness(Runtime(), Policy(stop()), goal=GOAL, catalog=CATALOG,
                             topology=TOPOLOGY, role_actions=ACTIONS, run_id=bad)

    def test_no_automatic_cleanup_or_grade_from_completed_claim(self):
        runtime = Runtime()
        subject = harness(Policy(stop()), runtime)
        result = subject.run()
        self.assertEqual(runtime.mutations, 0)
        self.assertEqual(result['evidence']['measurement_refs'], [])
        self.assertEqual(result['assessment']['status'], 'not_assessed')
        self.assertEqual(result['cleanup']['status'], 'not_assessed')

    def test_retry_budget_is_shared_across_the_entire_run(self):
        runtime = Runtime()
        runtime.lost = 'execute'
        count = 0
        def policy(context):
            nonlocal count
            count += 1
            if count == 1:
                return execute()
            runtime.lost = 'advance'
            return advance()
        result = harness(policy, runtime, budgets={'transport_retries': 1}).run()
        self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(result['usage']['transport_retries'], 1)
        self.assertEqual(result['usage']['logical_requests'], 2)
        self.assertEqual(len(runtime.attempts), 3)
        self.assertEqual(len(result['unresolved_request_ids']), 1)

    def test_zero_retry_budget_never_resends_unacknowledged_advance(self):
        runtime = Runtime()
        runtime.lost = 'advance'
        result = harness(Policy(advance()), runtime, budgets={'transport_retries': 0}).run()
        self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(len(runtime.attempts), 1)
        self.assertEqual(result['usage']['reserved_ticks'], 1)

    def test_invalid_receipt_after_dispatch_is_uncertain(self):
        for reply in [None, {'status': 'ok'}, Runtime().envelope('invented'),
                      Runtime().envelope('ok', {'value': float('inf')})]:
            runtime = Runtime()
            with patch.object(runtime, 'execute', return_value=reply):
                subject = harness(Policy(execute()), runtime)
                self.assertEqual(subject.run()['termination']['reason'], 'runtime_mutation_uncertain')
                self.assertEqual(len(subject.result()['unresolved_request_ids']), 1)

    def test_current_observation_binding_and_provenance_are_required(self):
        for mutation in ['provenance', 'profile', 'revision', 'tick', 'device']:
            with self.subTest(mutation=mutation):
                runtime = Runtime()
                observed = runtime.observations()
                if mutation == 'provenance':
                    observed['hardware_verified'] = True
                elif mutation == 'profile':
                    observed['devices']['sensor']['profile_id'] = 'other'
                elif mutation == 'revision':
                    observed['devices']['sensor']['setup_revision'] += 1
                elif mutation == 'tick':
                    observed['devices']['sensor']['tick'] += 1
                else:
                    observed['devices'].clear()
                with patch.object(runtime, 'observations', return_value=observed):
                    self.assertEqual(harness(runtime=runtime).run()['termination']['reason'], 'runtime_error')

    def test_private_catalog_goal_and_observation_fields_never_reach_policy_or_events(self):
        runtime = Runtime()
        original = runtime.observations
        def observed():
            value = original()
            value['author'] = {'seed': SECRET}
            value['devices']['sensor']['values']['truth'] = SECRET
            return value
        policy = Policy(stop())
        with patch.object(runtime, 'observations', side_effect=observed):
            subject = FleetHarness(runtime, policy, goal={**GOAL, 'seed': SECRET}, catalog=CATALOG,
                                   topology={**TOPOLOGY, 'schedule': SECRET}, role_actions=ACTIONS)
            subject.run()
        self.assertNotIn(SECRET, json.dumps(policy.contexts)+json.dumps(subject.events())+json.dumps(subject.result()))

    def test_observation_or_sink_failure_tracks_receipt_acceptance_and_stops_uncertain(self):
        for failure in ['read', 'sink']:
            runtime = Runtime()
            original = runtime.observations
            def observed():
                if failure == 'read' and runtime.mutations:
                    raise RuntimeError(SECRET)
                return original()
            def sink(event):
                if failure == 'sink' and event['type'] == 'observation' and runtime.mutations:
                    raise OSError(SECRET)
            with patch.object(runtime, 'observations', side_effect=observed):
                subject = harness(Policy(advance()), runtime, event_sink=sink)
                result = subject.run()
            self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
            self.assertEqual(len(result['unresolved_request_ids']), int(failure == 'read'))
            self.assertEqual(result['usage']['reserved_ticks'], int(failure == 'read'))
            self.assertEqual(sum(e['type'] == 'receipt' for e in subject.events()), int(failure == 'sink'))

    def test_deadline_after_intent_and_during_retry_does_not_dispatch_again(self):
        for during_retry in [False, True]:
            runtime, clock = Runtime(), Clock()
            runtime.lost = 'advance' if during_retry else None
            def sink(event):
                if event['type'] == ('transport_retry' if during_retry else 'intent'):
                    clock.time = 30
            subject = harness(Policy(advance()), runtime, clock=clock, event_sink=sink)
            result = subject.run()
            self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain' if during_retry else 'wall_deadline')
            self.assertEqual(runtime.mutations, int(during_retry))
            self.assertEqual(len(result['unresolved_request_ids']), 1)

    def test_event_limit_pre_and_post_intent_never_claims_completion(self):
        for limit, reason, mutations in [(2, 'evidence_error', 0), (3, 'runtime_mutation_uncertain', 1)]:
            runtime = Runtime()
            with patch('labflow.virtual_fleet.harness._MAX_EVENTS', limit):
                subject = harness(Policy(advance()), runtime)
                result = subject.run()
            self.assertEqual(result['termination']['reason'], reason)
            self.assertEqual(runtime.mutations, mutations)
            self.assertEqual(len(subject.events()), limit)

    def test_measurement_references_require_finite_current_source_quantity(self):
        mutations = [{'valid': False}, {'source_id': 'other'}, {'unit': ''},
                     {'acquisition_setup_revision': 0}, {'acquisition_tick': 999}, {'value': True}]
        for change in mutations:
            runtime = Runtime()
            runtime.due = 0
            observed = runtime.observations()
            observed['devices']['sensor']['values']['outputs']['measurement'].update(change)
            with patch.object(runtime, 'observations', return_value=observed):
                result = harness(runtime=runtime).run()
            self.assertEqual(result['evidence']['measurement_refs'], [])

    def test_constructor_and_input_mutation_do_not_change_captured_contract(self):
        catalog, topology, actions, goal = (copy.deepcopy(item) for item in (CATALOG, TOPOLOGY, ACTIONS, GOAL))
        policy = Policy(stop())
        subject = FleetHarness(Runtime(), policy, goal=goal, catalog=catalog, topology=topology, role_actions=actions)
        catalog['profiles'].clear()
        topology['devices'].clear()
        actions.clear()
        goal.clear()
        subject.run()
        self.assertEqual(len(policy.contexts[0]['catalog']['profiles']), 1)
        self.assertEqual(policy.contexts[0]['goal'], GOAL)

    def test_clock_errors_are_finite_redacted_results(self):
        for value in [float('nan'), float('inf'), 'bad']:
            subject = harness(clock=lambda: value)
            self.assertEqual(subject.run()['termination']['reason'], 'runtime_error')
            json.dumps(subject.result(), allow_nan=False)
        clock = Clock()
        def late(context):
            clock.time = 1e308
            return stop()
        subject = harness(late, clock=clock)
        self.assertEqual(subject.run()['termination']['reason'], 'runtime_error')
        json.dumps(subject.result(), allow_nan=False)

    def test_late_termination_evidence_cannot_return_policy_completion(self):
        clock = Clock()
        def sink(event):
            if event['type'] == 'termination':
                clock.time = 30
        result = harness(Policy(stop()), clock=clock, event_sink=sink).run()
        self.assertEqual(result['termination']['reason'], 'wall_deadline')
        self.assertIsNone(result['termination']['policy_claim'])

    def test_real_fleet_generator_sensor_records_current_synthetic_measurement(self):
        from labflow.virtual_fleet.core import VirtualFleet
        from labflow.virtual_fleet import instruments, rf
        catalog = {'profiles': [
            {'profile_id': 'generator-policy', 'model': 'SYNTHETIC', 'manufacturer': 'TEST',
             'role': 'signal_generator', 'ports': instruments.ROLE_PORTS['signal_generator'],
             'simulation_parameters': {'power_required': False}},
            {'profile_id': 'sensor-policy', 'model': 'SYNTHETIC', 'manufacturer': 'TEST',
             'role': 'power_sensor', 'ports': rf.ROLE_PORTS['power_sensor'],
             'simulation_parameters': {'calibration_valid': True, 'acquisition_policy': 'triggered'}}]}
        topology = {'devices': [{'id': 'generator', 'profile_id': 'generator-policy'},
                                {'id': 'sensor', 'profile_id': 'sensor-policy'}],
                    'connections': [{'source': {'device_id': 'generator', 'port': 'rf'},
                                     'target': {'device_id': 'sensor', 'port': 'rf'}, 'kind': 'rf'}]}
        actions = instruments.ROLE_ACTIONS | rf.ROLE_ACTIONS
        runtime = VirtualFleet(catalog, topology, factories=instruments.DEVICE_FACTORIES | rf.DEVICE_FACTORIES,
                               role_actions=actions)
        policy = Policy(
            {'kind': 'execute', 'device_id': 'generator', 'action': 'configure',
             'parameters': {'frequency_hz': 2.45e9, 'power_dbm': 7.25, 'bandwidth_hz': 2e6}},
            {'kind': 'execute', 'device_id': 'generator', 'action': 'start_tx', 'parameters': {}},
            execute(), advance(), advance(), execute('read'), stop())
        subject = FleetHarness(runtime, policy, goal=GOAL, catalog=catalog, topology=topology, role_actions=actions)
        result = subject.run()
        self.assertEqual(result['termination']['reason'], 'policy_stop')
        measurements = [event for event in subject.events() if event['event_id'] in result['evidence']['measurement_refs']]
        self.assertTrue(measurements)
        snapshot = measurements[-1]['payload']['observation']
        measured = snapshot['devices']['sensor']['values']['outputs']['measurement']
        self.assertEqual(measured['source_id'], 'sensor')
        self.assertEqual(measured['unit'], 'dBm')
        self.assertEqual(measured['value'], 7.25)
        self.assertEqual(measured['acquisition_setup_revision'], snapshot['setup_revision'])
        self.assertNotIn('simulation_parameters', json.dumps(policy.contexts))

    def test_real_fleet_contract_quarantine_is_known_error_not_retry_or_completed_grade(self):
        from labflow.virtual_fleet.core import VirtualFleet
        class BrokenDevice:
            def advance(self, **kwargs):
                return None
            def observation(self, *, tick, setup_revision):
                return {'status': 'ok', 'values': {'outputs': {}}}
            def perform(self, *args, **kwargs):
                raise RuntimeError(SECRET)
            def author_control(self, *args):
                raise AssertionError('not an operator capability')
        runtime = VirtualFleet(CATALOG, TOPOLOGY, factories={'power_sensor': lambda profile, seed: BrokenDevice()},
                               role_actions=ACTIONS)
        policy = Policy(execute(), stop('failed'))
        subject = harness(policy, runtime)
        result = subject.run()
        self.assertEqual(policy.contexts[-1]['last_receipt']['status'], 'error')
        self.assertEqual(result['termination']['policy_claim'], 'failed')
        self.assertEqual(result['usage']['transport_retries'], 0)
        self.assertEqual(result['assessment']['status'], 'not_assessed')
        self.assertNotIn(SECRET, json.dumps(subject.events()))

    def test_supervisor_stop_during_unacknowledged_mutation_is_uncertain(self):
        for lost in [False, True]:
            runtime = Runtime()
            original = runtime.advance
            def dispatch(request_id, ticks):
                result = original(request_id, ticks)
                subject.stop()
                if lost:
                    raise RetryableTransportError(SECRET)
                return result
            subject = harness(Policy(advance()), runtime)
            with patch.object(runtime, 'advance', side_effect=dispatch):
                result = subject.run()
            self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
            self.assertEqual(len(result['unresolved_request_ids']), 1)
            self.assertEqual(len(runtime.attempts), 1)

    def test_retry_body_and_last_receipt_are_detached_from_runtime_and_policy(self):
        runtime = Runtime()
        original = runtime.execute
        received = []
        def dispatch(request_id, device_id, action, parameters):
            received.append(copy.deepcopy(parameters))
            if len(received) == 1:
                parameters['gain_db'] = 999
                raise RetryableTransportError(SECRET)
            return original(request_id, device_id, action, parameters)
        calls = 0
        def policy(context):
            nonlocal calls
            calls += 1
            if calls == 1:
                return execute('configure', {'gain_db': 2.5})
            context['last_receipt']['status'] = 'corrupted'
            return stop()
        with patch.object(runtime, 'execute', side_effect=dispatch):
            subject = harness(policy, runtime)
            self.assertEqual(subject.run()['termination']['reason'], 'policy_stop')
        self.assertEqual(received, [{'gain_db': 2.5}, {'gain_db': 2.5}])
        receipt = next(event['payload']['result'] for event in subject.events() if event['type'] == 'receipt')
        self.assertEqual(receipt['status'], 'ok')

    def test_oversize_and_unserializable_proposals_are_rejected_before_intent(self):
        for proposal in [execute('configure', {'gain_db': 'x'*(2*1024*1024)}),
                         execute('configure', {'gain_db': object()}),
                         {'kind': 'stop', 'claim': 'completed', 'reason': '\ud800'}]:
            runtime = Runtime()
            subject = harness(Policy(proposal), runtime)
            self.assertEqual(subject.run()['termination']['reason'], 'invalid_proposal')
            self.assertEqual(runtime.mutations, 0)
            self.assertFalse(any(event['type'] == 'intent' for event in subject.events()))

    def test_malformed_outputs_after_dispatch_preserve_uncertain_request(self):
        for outputs in [None, [], 'invalid']:
            with self.subTest(outputs=outputs):
                runtime = Runtime()
                original = runtime.observations
                def observed():
                    value = original()
                    if runtime.mutations:
                        value['devices']['sensor']['values']['outputs'] = outputs
                    return value
                policy = Policy(execute('read'), execute('read'), stop())
                with patch.object(runtime, 'observations', side_effect=observed):
                    subject = harness(policy, runtime)
                    result = subject.run()
                self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
                self.assertEqual(len(result['unresolved_request_ids']), 1)
                self.assertEqual(runtime.mutations, 1)
                self.assertEqual(len(policy.contexts), 1)
                self.assertFalse(any(event['type'] == 'receipt' for event in subject.events()))

    def test_execute_receipt_must_match_all_request_target_identifiers(self):
        for key in ['device_id', 'profile_id', 'role']:
            for missing in [False, True]:
                with self.subTest(key=key, missing=missing):
                    runtime = Runtime()
                    original = runtime.execute
                    def dispatch(*args):
                        reply = original(*args)
                        if missing:
                            del reply[key]
                        else:
                            reply[key] = 'different-target'
                        return reply
                    policy = Policy(execute('read'), stop())
                    with patch.object(runtime, 'execute', side_effect=dispatch):
                        subject = harness(policy, runtime)
                        result = subject.run()
                    self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
                    self.assertEqual(len(result['unresolved_request_ids']), 1)
                    self.assertEqual(runtime.mutations, 1)
                    self.assertEqual(len(policy.contexts), 1)

    def test_receipt_and_observation_tick_must_equal_the_single_reserved_operation(self):
        cases = [('advance_receipt', 0), ('advance_receipt', 33),
                 ('advance_observation', 0), ('advance_observation', 33),
                 ('execute_receipt', 1), ('execute_observation', 1)]
        for stage, extra in cases:
            with self.subTest(stage=stage, extra=extra):
                runtime = Runtime()
                initial_tick = runtime.tick
                original_execute, original_advance, original_observe = runtime.execute, runtime.advance, runtime.observations
                def dispatch_execute(*args):
                    reply = original_execute(*args)
                    if stage == 'execute_receipt':
                        runtime.tick += extra
                        reply['tick'] = runtime.tick
                    return reply
                def dispatch_advance(*args):
                    reply = original_advance(*args)
                    if stage == 'advance_receipt':
                        runtime.tick = initial_tick+extra
                        reply['tick'] = runtime.tick
                        reply['values']['advanced_ticks'] = extra
                    return reply
                def observed():
                    value = original_observe()
                    if runtime.mutations and stage.endswith('observation'):
                        value['tick'] = initial_tick+extra
                        value['devices']['sensor']['tick'] = value['tick']
                    return value
                policy = Policy(advance() if stage.startswith('advance') else execute('read'), execute('read'), stop())
                with patch.object(runtime, 'execute', side_effect=dispatch_execute), \
                     patch.object(runtime, 'advance', side_effect=dispatch_advance), \
                     patch.object(runtime, 'observations', side_effect=observed):
                    subject = harness(policy, runtime, budgets={'ticks': 1})
                    result = subject.run()
                self.assertEqual(result['termination']['reason'], 'runtime_mutation_uncertain')
                self.assertEqual(len(result['unresolved_request_ids']), 1)
                self.assertEqual(result['usage']['tick_delta'], 0)
                self.assertEqual(runtime.mutations, 1)
                self.assertEqual(len(policy.contexts), 1)

    def test_accepted_event_depth_remains_readable_as_detached_event_list(self):
        for depth in range(24, 33):
            runtime = Runtime()
            observed = runtime.observations()
            nested = 1
            for _ in range(depth):
                nested = {'detail': nested}
            observed['detail'] = nested
            with patch.object(runtime, 'observations', return_value=observed):
                subject = harness(runtime=runtime)
                subject.run()
            events = subject.events()
            json.dumps(events, allow_nan=False)
            if events:
                events[0].clear()
                self.assertTrue(subject.events()[0])


if __name__ == '__main__':
    unittest.main()
