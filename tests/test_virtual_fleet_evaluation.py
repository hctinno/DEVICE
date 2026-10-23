"""Independent grading of public evidence from authored synthetic RF trials."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.evaluation import prepare_sensor_trial, evaluate_sensor_run


CATALOG = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'


class SensorEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(CATALOG)

    def evidence(self, trial, *, wait=0, measure=True, finish_stop=False,
                 prefix='public', run_id='opaque-run'):
        events = []
        request = 0

        def emit(kind, payload):
            sequence = len(events) + 1
            events.append({'schema_version': 1, 'kind': 'operator_event',
                           'event_id': f'event:{sequence}', 'run_id': run_id,
                           'runtime_instance_id': trial.runtime_instance_id,
                           'sequence': sequence, 'type': kind, 'payload': deepcopy(payload)})

        def observe(cause=None):
            payload = {'observation': trial.runtime.observations()}
            if cause:
                payload['cause_request_id'] = cause
            emit('observation', payload)

        def command(operation, **body):
            nonlocal request
            request += 1
            request_id = f'{prefix}:{request}'
            emit('intent', {'request_id': request_id, 'operation': operation,
                            'body': body, 'logical_request': request})
            if operation == 'advance':
                receipt = trial.runtime.advance(request_id, body['ticks'])
            else:
                receipt = trial.runtime.execute(request_id, body['device_id'], body['action'], body['parameters'])
            emit('receipt', {'request_id': request_id, 'result': receipt})
            observe(request_id)
            return receipt

        observe()
        for _ in range(wait):
            command('advance', ticks=1)
        if measure:
            command('execute', device_id='dut', action='start', parameters={})
            for _ in range(2):
                command('advance', ticks=1)
            command('execute', device_id='sensor', action='acquire', parameters={})
            command('advance', ticks=1)
            command('execute', device_id='sensor', action='read', parameters={})
        if finish_stop:
            command('execute', device_id='dut', action='stop', parameters={})
        result = {'schema_version': 1, 'kind': 'virtual_fleet_harness_result',
                  'run_id': run_id, 'runtime_instance_id': trial.runtime_instance_id,
                  'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
                  'policy': {'kind': 'fixture', 'id': 'rf_sensor_v1'},
                  'termination': {'reason': 'policy_stop' if measure else 'tick_budget',
                                  'policy_claim': 'completed' if measure else None},
                  'task_outcome': 'not_assessed', 'cleanup': {'status': 'not_assessed', 'evidence_refs': []},
                  'usage': {'decisions': request + 1, 'logical_requests': request,
                            'transport_retries': 0, 'tick_delta': wait + (3 if measure else 0),
                            'reserved_ticks': wait + (3 if measure else 0), 'elapsed_ms': 1},
                  'evidence': {'measurement_refs': [], 'operator_transcript_ref': 'artifact:operator_events'},
                  'unresolved_request_ids': [],
                  'assessment': {'status': 'not_assessed', 'verdict': None, 'evaluator_id': None,
                                 'evidence_refs': [], 'summary_code': None}}
        return result, events

    def test_trials_share_public_goal_and_leave_catalog_unchanged(self):
        original = deepcopy(self.catalog)
        trials = [prepare_sensor_trial(self.catalog, condition=condition, seed=29)
                  for condition in ('normal', 'persistent_disconnect', 'restored_disconnect')]
        self.assertEqual(trials[0].goal, trials[1].goal)
        self.assertEqual(trials[1].goal, trials[2].goal)
        self.assertEqual(self.catalog, original)
        for trial in trials:
            self.assertFalse(hasattr(trial.runtime, 'author_control'))
            public = json.dumps(trial.runtime.observations())
            for hidden in ('persistent_disconnect', 'restored_disconnect', 'expected_sensor_dbm', 'author_event'):
                self.assertNotIn(hidden, public)
            self.assertEqual(trial.author_record()['seed'], 29)

    def test_normal_measurement_is_graded_from_fresh_observation(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        assessment = evaluate_sensor_run(trial, result, events)
        self.assertEqual((assessment['status'], assessment['verdict']), ('completed', 'pass'))
        refs = {event['event_id'] for event in events}
        self.assertTrue(assessment['evidence_refs'])
        self.assertLessEqual(set(assessment['evidence_refs']), refs)
        self.assertNotIn('expected_sensor_dbm', json.dumps(assessment))

    def test_persistent_disconnect_passes_only_as_bounded_noncompletion(self):
        trial = prepare_sensor_trial(self.catalog, condition='persistent_disconnect')
        result, events = self.evidence(trial, wait=8, measure=False)
        self.assertEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')
        result['termination'] = {'reason': 'policy_stop', 'policy_claim': 'completed'}
        self.assertNotEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')

    def test_recovery_requires_release_and_fresh_later_acquisition(self):
        trial = prepare_sensor_trial(self.catalog, condition='restored_disconnect')
        result, events = self.evidence(trial, wait=4)
        self.assertEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')
        author = trial.author_record()
        self.assertEqual(author['release_tick'], author['start_tick'] + 4)
        acquisition_ticks = [event['payload']['observation']['devices']['sensor']['values']['outputs']['measurement']['acquisition_tick']
                             for event in events if event['type'] == 'observation'
                             and 'measurement' in event['payload']['observation']['devices']['sensor']['values']['outputs']]
        self.assertTrue(all(tick > author['release_tick'] for tick in acquisition_ticks))

    def test_release_does_not_repeat_on_duplicate_advance(self):
        trial = prepare_sensor_trial(self.catalog, condition='restored_disconnect')
        for i in range(4):
            trial.runtime.advance(f'public:{i}', 1)
        original = trial.author_record()
        trial.runtime.advance('public:3', 1)
        self.assertEqual(trial.author_record(), original)

    def test_ack_or_old_receipt_alone_cannot_complete_measurement(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        events = [event for event in events if event['type'] != 'observation']
        for i, event in enumerate(events, 1):
            event.update(sequence=i, event_id=f'event:{i}')
        self.assertNotEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')

    def test_wrong_unit_source_revision_tick_or_value_never_passes(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        changes = [('unit', 'W'), ('source_id', 'dut'), ('value', 123),
                   ('acquisition_setup_revision', 0), ('acquisition_tick', 0)]
        for key, value in changes:
            tampered = deepcopy(events)
            for event in tampered:
                if event['type'] == 'observation':
                    measurement = event['payload']['observation']['devices']['sensor']['values']['outputs'].get('measurement')
                    if measurement:
                        measurement[key] = value
            with self.subTest(key=key):
                self.assertEqual(evaluate_sensor_run(trial, result, tampered)['verdict'], 'fail')

    def test_historical_valid_measurement_survives_later_stop_revision(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial, finish_stop=True)
        self.assertNotIn('measurement', trial.runtime.observations()['devices']['sensor']['values']['outputs'])
        self.assertEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')

    def test_independent_authored_input_changes_oracle(self):
        for power in (-4, 12.5, 17):
            trial = prepare_sensor_trial(self.catalog, power_dbm=power)
            result, events = self.evidence(trial)
            self.assertAlmostEqual(trial.author_record()['expected_sensor_dbm'], power - 30.5)
            self.assertEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')

    def test_mixed_run_or_instance_and_bad_sequence_are_refused(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        for key, value in [('run_id', 'other'), ('runtime_instance_id', 'other'), ('sequence', 999)]:
            tampered = deepcopy(events)
            tampered[-1][key] = value
            with self.subTest(key=key):
                assessment = evaluate_sensor_run(trial, result, tampered)
                self.assertEqual(assessment['status'], 'failed')
                self.assertIsNone(assessment['verdict'])

    def test_uncertain_or_unresolved_request_is_not_successful_detection(self):
        trial = prepare_sensor_trial(self.catalog, condition='persistent_disconnect')
        result, events = self.evidence(trial, wait=5, measure=False)
        result['termination']['reason'] = 'runtime_mutation_uncertain'
        result['unresolved_request_ids'] = ['public:unresolved']
        self.assertEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'fail')

    def test_non_json_evidence_is_failed_without_echoing_private_text(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        events[-1]['payload']['private-canary'] = object()
        assessment = evaluate_sensor_run(trial, result, events)
        self.assertEqual(assessment['status'], 'failed')
        self.assertNotIn('private-canary', json.dumps(assessment))

    def test_invalid_author_setup_is_rejected(self):
        for kwargs in ({'condition': 'unknown'}, {'seed': True}, {'power_dbm': float('nan')}, {'power_dbm': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                prepare_sensor_trial(self.catalog, **kwargs)

    def test_malformed_nested_json_is_failed_without_raising(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        for case in ('termination', 'observation', 'devices'):
            bad_result, bad_events = deepcopy(result), deepcopy(events)
            if case == 'termination':
                bad_result['termination'] = []
            elif case == 'observation':
                bad_events[0]['payload']['observation'] = None
            else:
                bad_events[0]['payload']['observation']['devices'] = []
            with self.subTest(case=case):
                assessment = evaluate_sensor_run(trial, bad_result, bad_events)
                self.assertEqual((assessment['status'], assessment['verdict']), ('failed', None))

    def test_empty_or_non_disconnected_observation_cannot_prove_failure_detection(self):
        trial = prepare_sensor_trial(self.catalog, condition='persistent_disconnect')
        result, events = self.evidence(trial, wait=4, measure=False)
        for case in ('empty', 'not_disconnected'):
            tampered = deepcopy(events)
            for event in tampered:
                if event['type'] == 'observation':
                    if case == 'empty':
                        event['payload']['observation'] = {}
                    else:
                        event['payload']['observation']['devices']['dut']['status'] = 'ok'
            with self.subTest(case=case):
                self.assertNotEqual(evaluate_sensor_run(trial, result, tampered)['verdict'], 'pass')

    def test_acquire_receipt_identity_and_provenance_must_match(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        for key, value in [('device_id', 'dut'), ('profile_id', 'other'),
                           ('role', 'dut'), ('synthetic', False), ('hardware_verified', True)]:
            tampered = deepcopy(events)
            intents = {event['payload']['request_id']: event['payload'] for event in tampered
                       if event['type'] == 'intent'}
            for event in tampered:
                if event['type'] == 'receipt' and intents[event['payload']['request_id']]['body'].get('action') == 'acquire':
                    event['payload']['result'][key] = value
            with self.subTest(key=key):
                self.assertNotEqual(evaluate_sensor_run(trial, result, tampered)['verdict'], 'pass')

    def test_different_logical_operations_cannot_share_request_id(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        for event in events:
            payload = event['payload']
            for key in ('request_id', 'cause_request_id'):
                if key in payload:
                    payload[key] = 'same-id'
        self.assertEqual(evaluate_sensor_run(trial, result, events)['status'], 'failed')

    def test_transcript_unresolved_intent_is_checked_independently_of_result(self):
        trial = prepare_sensor_trial(self.catalog)
        result, events = self.evidence(trial)
        last = deepcopy(events[-1])
        last.update(sequence=len(events) + 1, event_id=f'event:{len(events) + 1}', type='intent')
        last['payload'] = {'request_id': 'new-unresolved', 'operation': 'execute', 'logical_request': 7,
                           'body': {'device_id': 'sensor', 'action': 'acquire', 'parameters': {}}}
        events.append(last)
        self.assertFalse(result['unresolved_request_ids'])
        self.assertEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'fail')

    def test_real_cached_acquire_from_previous_run_is_not_a_new_acquisition(self):
        trial = prepare_sensor_trial(self.catalog)
        result, first = self.evidence(trial)
        original = next(event['payload'] for event in first if event['type'] == 'intent'
                        and event['payload']['body'].get('action') == 'acquire')
        initial = trial.runtime.observations()
        cached = trial.runtime.execute(original['request_id'], 'sensor', 'acquire', {})
        self.assertLess(cached['tick'], initial['tick'])
        templates = [('observation', {'observation': initial}),
                     ('intent', {**original, 'logical_request': 1}),
                     ('receipt', {'request_id': original['request_id'], 'result': cached}),
                     ('observation', {'observation': trial.runtime.observations(),
                                      'cause_request_id': original['request_id']})]
        events = [{'schema_version': 1, 'kind': 'operator_event', 'event_id': f'event:{i}',
                   'run_id': 'second-run', 'runtime_instance_id': trial.runtime_instance_id,
                   'sequence': i, 'type': kind, 'payload': payload}
                  for i, (kind, payload) in enumerate(templates, 1)]
        result['run_id'] = 'second-run'
        self.assertNotEqual(evaluate_sensor_run(trial, result, events)['verdict'], 'pass')
        fresh_result, fresh_events = self.evidence(trial, prefix='second', run_id='second-run')
        self.assertEqual(evaluate_sensor_run(trial, fresh_result, fresh_events)['verdict'], 'pass')

    def test_facade_reports_coverage_without_exposing_author_commands(self):
        trial = prepare_sensor_trial(self.catalog)
        self.assertEqual(trial.runtime.coverage()['catalog_profiles'], 64)
        self.assertFalse(hasattr(trial.runtime, 'author_control'))


if __name__ == '__main__':
    unittest.main()
