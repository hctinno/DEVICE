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


    def plan_source(self,**changes):
        source=dict(frequency_hz=2.412e9,power_dbm=11.0,bandwidth_hz=10e6,
                    duty_cycle=.5,modulation='OFDM',crest_factor_db=4.0)
        source.update(changes)
        return source

    def test_source_reaches_one_factory_and_same_detached_followup_setup(self):
        from unittest.mock import patch
        from labflow.virtual_fleet import evaluation
        from labflow.virtual_fleet.core import VirtualFleet
        source=self.plan_source();original=deepcopy(source);factory_args=[];dut_args=[];fleets=[]
        factory=evaluation.create_conducted_example;execute=VirtualFleet.execute
        def create(catalog,**kw):
            factory_args.append(kw);result=factory(catalog,**kw);fleets.append(result[0]);return result
        def command(fleet,request,device,action,parameters=None):
            if device=='dut' and action=='configure':dut_args.append(parameters)
            return execute(fleet,request,device,action,parameters)
        try:
            with patch.object(evaluation,'create_conducted_example',create),patch.object(VirtualFleet,'execute',command):
                trial=prepare_sensor_trial(self.catalog,power_dbm=source['power_dbm'],source_settings=source)
        except TypeError as error:self.fail('source_settings optional keyword unavailable: '+str(error))
        self.assertEqual(len(factory_args),1);self.assertEqual(len(fleets),1)
        sent=factory_args[0]['source_settings']
        self.assertIsNot(sent,source);self.assertEqual(sent,original)
        self.assertEqual(dut_args,[original,original]);self.assertIs(dut_args[-1],sent)
        self.assertIs(trial._fleet,fleets[0]);self.assertEqual(source,original)
        source['frequency_hz']=2.45e9;source['power_dbm']=12.5
        result,events=self.evidence(trial)
        self.assertEqual(evaluate_sensor_run(trial,result,events)['verdict'],'pass')

    def test_plan_power_path_and_signal_metadata_reach_evaluator(self):
        for power in (-4.0,11.0,14.0):
            source=self.plan_source(power_dbm=power)
            trial=prepare_sensor_trial(self.catalog,power_dbm=power,source_settings=source)
            result,events=self.evidence(trial)
            observed=trial.runtime.observations()['devices']
            measurement=observed['sensor']['values']['outputs']['measurement']
            coupled=observed['coupler']['values']['outputs']['coupled']
            self.assertAlmostEqual(measurement['value'],power-10-.5-20,places=9)
            self.assertAlmostEqual(coupled['power_dbm'],power-30.5,places=9)
            self.assertEqual(measurement['frequency_hz'],source['frequency_hz'])
            self.assertEqual(measurement['duty_cycle'],source['duty_cycle'])
            self.assertEqual(measurement['crest_factor_db'],source['crest_factor_db'])
            self.assertEqual(coupled['bandwidth_hz'],source['bandwidth_hz'])
            grade=evaluate_sensor_run(trial,result,events)
            self.assertEqual((grade['status'],grade['verdict'],grade['evaluator_id']),
                             ('completed','pass','rf_sensor_fixture_v1'))
            self.assertNotIn('expected_sensor_dbm',json.dumps(grade))

    def test_power_mismatch_and_nonfinite_reject_before_factory_both_entries(self):
        from unittest.mock import patch
        from labflow.virtual_fleet import evaluation
        source=self.plan_source()
        cases=[(12.5,source),(True,source),(float('nan'),source),(float('inf'),source),
               (10**400,source),(11.0,{**source,'power_dbm':True}),
               (11.0,{**source,'power_dbm':float('nan')}),(11.0,{k:v for k,v in source.items() if k!='power_dbm'})]
        with patch.object(evaluation,'create_conducted_example',side_effect=AssertionError('no factory on power mismatch')):
            with self.assertRaises(ValueError):prepare_sensor_trial(self.catalog,source_settings=source)
            for index,(power,supplied) in enumerate(cases):
                for constructor in (prepare_sensor_trial,evaluation.SensorTrial):
                    with self.subTest(index=index,entry=constructor.__name__),self.assertRaises(ValueError):
                        constructor(self.catalog,condition='normal',seed=0,power_dbm=power,source_settings=supplied)

    def test_matching_numeric_power_and_factory_owns_range_validation(self):
        from unittest.mock import patch
        from labflow.virtual_fleet import evaluation,integration
        source=self.plan_source(power_dbm=11)
        trial=evaluation.SensorTrial(self.catalog,condition='normal',seed=3,power_dbm=11.0,source_settings=source)
        result,events=self.evidence(trial)
        self.assertEqual(evaluate_sensor_run(trial,result,events)['verdict'],'pass')
        invalid=[{**source,'frequency_hz':True},{**source,'duty_cycle':0},
                 {**source,'bandwidth_hz':float('inf')},{**source,'extra':0},
                 {k:v for k,v in source.items() if k!='bandwidth_hz'}]
        for index,supplied in enumerate(invalid):
            with self.subTest(index=index),patch.object(evaluation,'create_conducted_example',wraps=integration.create_conducted_example) as factory,patch.object(
                    integration,'create_fleet',side_effect=AssertionError('factory must reject before fleet')):
                with self.assertRaises(ValueError):
                    prepare_sensor_trial(self.catalog,power_dbm=11,source_settings=supplied)
                self.assertEqual(factory.call_count,1)

    def test_none_preserves_legacy_observation_goal_and_author_contract(self):
        from unittest.mock import patch
        from labflow.virtual_fleet import evaluation
        original=deepcopy(self.catalog)
        for power in (-4,12.5,17):
            implicit=prepare_sensor_trial(self.catalog,power_dbm=power,seed=7)
            with patch.object(evaluation,'create_conducted_example',wraps=evaluation.create_conducted_example) as factory:
                explicit=prepare_sensor_trial(self.catalog,power_dbm=power,seed=7,source_settings=None)
            self.assertEqual(factory.call_args.kwargs,{'seed':7})
            self.assertEqual(implicit.runtime.observations(),explicit.runtime.observations())
            self.assertEqual(implicit.goal,explicit.goal)
            self.assertEqual(implicit.author_record(),explicit.author_record())
            self.assertNotIn('source_settings',explicit.author_record())
            result,events=self.evidence(explicit)
            self.assertEqual(evaluate_sensor_run(explicit,result,events)['verdict'],'pass')
        self.assertEqual(self.catalog,original)

    def test_plan_disconnect_recovery_and_failed_recovery_preserve_schedule(self):
        source=self.plan_source();before=deepcopy(source)
        persistent=prepare_sensor_trial(self.catalog,condition='persistent_disconnect',
                                        power_dbm=11,source_settings=source)
        result,events=self.evidence(persistent,wait=8,measure=False)
        self.assertEqual(evaluate_sensor_run(persistent,result,events)['verdict'],'pass')
        restored=prepare_sensor_trial(self.catalog,condition='restored_disconnect',power_dbm=11,source_settings=source)
        result,events=self.evidence(restored,wait=4)
        self.assertEqual(evaluate_sensor_run(restored,result,events)['verdict'],'pass')
        author=restored.author_record()
        self.assertEqual(author['release_tick'],author['start_tick']+4)
        failed=prepare_sensor_trial(self.catalog,condition='restored_disconnect',power_dbm=11,source_settings=source)
        result,events=self.evidence(failed)
        self.assertEqual(evaluate_sensor_run(failed,result,events)['verdict'],'fail')
        self.assertEqual(source,before)

    def test_plan_stale_and_changed_signal_metadata_cannot_rebind_oracle(self):
        source=self.plan_source(duty_cycle=1.0,crest_factor_db=0)
        trial=prepare_sensor_trial(self.catalog,power_dbm=11,source_settings=source)
        result,events=self.evidence(trial)
        self.assertEqual(evaluate_sensor_run(trial,result,events)['verdict'],'pass')
        stale,old_events=self.evidence(trial,measure=False,prefix='second',run_id='second-run')
        stale['termination']={'reason':'policy_stop','policy_claim':'completed'}
        self.assertEqual(evaluate_sensor_run(trial,stale,old_events)['verdict'],'fail')
        for device,port,key,value in [('coupler','coupled','bandwidth_hz',20e6),
                ('coupler','coupled','frequency_hz',2.45e9),('coupler','coupled','modulation','CW'),
                ('sensor','measurement','duty_cycle',True),('sensor','measurement','crest_factor_db',False),
                ('sensor','measurement','frequency_hz',2.45e9)]:
            altered=deepcopy(events)
            for event in altered:
                if event['type']=='observation':
                    packet=event['payload']['observation']['devices'][device]['values']['outputs'].get(port)
                    if packet:packet[key]=value
            with self.subTest(device=device,key=key):
                self.assertEqual(evaluate_sensor_run(trial,result,altered)['verdict'],'fail')

    def test_plan_public_context_excludes_private_source_oracle_and_author(self):
        from labflow.virtual_fleet.harness import FleetHarness
        from labflow.virtual_fleet.integration import get_role_actions
        source=self.plan_source();trial=prepare_sensor_trial(self.catalog,power_dbm=11,source_settings=source)
        contexts=[]
        def policy(context):
            contexts.append(deepcopy(context))
            return {'kind':'stop','claim':'blocked','reason':'public-context inspection only'}
        harness=FleetHarness(trial.runtime,policy,goal=trial.goal,catalog=trial.catalog,topology=trial.topology,
                             role_actions=get_role_actions(),runtime_instance_id=trial.runtime_instance_id)
        harness.run()
        self.assertEqual(len(contexts),1)
        self.assertEqual(set(contexts[0]),{'schema_version','goal','catalog','topology','role_actions','observations','last_receipt','remaining_budget'})
        forbidden={'source_settings','_source_settings','expected_sensor_dbm','condition','seed','author_events'}
        def check(value):
            if isinstance(value,dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for child in value.values():check(child)
            elif isinstance(value,list):
                for child in value:check(child)
        check(contexts[0])
        self.assertEqual(set(trial.goal),{'kind','dut_id','sensor_id','minimum_acquisition_tick'})
        self.assertFalse(hasattr(trial.runtime,'author_control'))


if __name__ == '__main__':
    unittest.main()
