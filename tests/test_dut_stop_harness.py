"""Existing in-memory fixture -> separate stop; labelled faults stay distinct."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import dut_stop_harness as boundary
from labflow.virtual_fleet.core import VirtualFleet
from labflow.virtual_fleet import rf


KEYS = {'schema_version','kind','execution_mode','synthetic','hardware_verified','physical_model_verified',
    'model_execution_verified','oem_support_status','run_id','runtime_instance_id','device_id','profile_id',
    'status','reason_code','harness_dispatch','harness_result','harness_error','events_error','dut_stop_request_id',
    'stop_dispatch','dut_stop_receipt','dut_stop_error','record_error','receipt_scope','current_stop_authority'}
SECRET = 'PRIVATE_016_AUTHOR_CANARY'


def fleet_fixture():
    profiles = []
    for role,parameters in [('dut',{'requires_power':False,'requires_environment':False,'frequency_hz':1e9,
                'power_dbm':7,'bandwidth_hz':1e6,'duty_cycle':.5,'modulation':'QPSK','crest_factor_db':3}),
            ('power_sensor',{'calibration_valid':True,'acquisition_ticks':1})]:
        profiles.append({'profile_id':'fixture-'+role,'role':role,'model':'SYNTHETIC-'+role,
            'ports':copy.deepcopy(rf.ROLE_PORTS[role]),'simulation_parameters':parameters})
    topology = {'devices':[{'id':'dut','profile_id':'fixture-dut'},{'id':'sensor','profile_id':'fixture-power_sensor'}],
        'connections':[{'source':{'device_id':'dut','port':'rf'},'target':{'device_id':'sensor','port':'rf'},'kind':'rf'}]}
    fleet = VirtualFleet({'profiles':profiles},topology,factories=rf.DEVICE_FACTORIES,role_actions=rf.ROLE_ACTIONS,seed=13)
    fleet.execute('setup:start','dut','start',{})
    fleet.advance('setup:tick',1)
    return fleet


def configs(fleet,**budgets):
    return {'goal':{'kind':'acquire_fresh_rf_sensor','dut_id':'dut','sensor_id':'sensor',
                   'minimum_acquisition_tick':fleet.observations()['tick']+1},
        'catalog':fleet.catalog,'topology':fleet.topology,'role_actions':fleet.role_actions,
        'run_id':'fixture-run','runtime_instance_id':'fixture-instance',**({'budgets':budgets} if budgets else {})}


class DutStopHarnessTests(unittest.TestCase):
    def setUp(self):
        self.fleet = fleet_fixture()

    def subject(self,*,fleet=None,harness_config=None,stop_config=None,**stop):
        fleet = self.fleet if fleet is None else fleet
        return boundary.SyntheticDutStopHarnessRun(fleet,'dut',harness_config=configs(fleet) if harness_config is None else harness_config,
            stop_config=stop_config if stop_config is not None else {'transport_family':'ADB','available':True,
                'authorized':True,'model_fw_matches':True,**stop})

    def check_result(self,result,status='recorded'):
        self.assertEqual(set(result),KEYS)
        self.assertEqual(result['status'],status)
        self.assertEqual((result['schema_version'],result['kind'],result['execution_mode']),
            (1,'synthetic_dut_stop_harness_result','virtual_fleet_fixture_then_dut_stop'))
        self.assertIs(result['synthetic'],True)
        for key in ('hardware_verified','physical_model_verified','model_execution_verified','current_stop_authority'):
            self.assertIs(result[key],False)
        self.assertEqual(result['receipt_scope'],'historical_observation')
        self.assertEqual(result['oem_support_status'],'not_assessed')
        self.assertNotIn(SECRET,json.dumps(result))

    def test_constructor_has_no_commands_and_empty_queries(self):
        before = self.fleet.history()
        subject = self.subject()
        self.assertEqual(self.fleet.history(),before)
        self.assertIsNone(subject.result())
        self.assertIsNone(subject.author_record())
        self.assertEqual(subject.events(),[])
        self.assertIs(subject._harness._runtime,self.fleet)
        self.assertIs(subject._adapter._fleet,self.fleet)

    def test_real_fixture_terminal_is_preserved_before_separate_stop(self):
        subject = self.subject()
        result = subject.run()
        self.check_result(result)
        self.assertEqual(result['reason_code'],'children_recorded')
        self.assertEqual(result['harness_result']['termination'],{'reason':'policy_stop','policy_claim':'completed'})
        self.assertEqual(result['harness_result']['cleanup'],{'status':'not_assessed','evidence_refs':[]})
        self.assertEqual(result['harness_result']['task_outcome'],'not_assessed')
        self.assertEqual(result['harness_result'],subject._harness.result())
        self.assertEqual(subject.events(),subject._harness.events())
        observations = [event['payload']['observation'] for event in subject.events() if event['type']=='observation']
        self.assertEqual(observations[-1]['devices']['dut']['values']['state'],'transmitting')
        receipt = result['dut_stop_receipt']
        self.assertEqual(receipt['status'],'confirmed_synthetic')
        self.assertEqual([event['action'] for event in receipt['commands']],['stop','read'])
        self.assertEqual(self.fleet.observations()['devices']['dut']['values']['state'],'idle')
        self.assertEqual((result['harness_dispatch'],result['stop_dispatch']),('returned','returned'))

    def test_original_budget_termination_and_followup_stop_remain_separate(self):
        for budgets,reason in [({'decisions':1},'decision_budget'),({'logical_requests':1},'request_budget'),({'ticks':1},'tick_budget')]:
            with self.subTest(budgets=budgets):
                fleet = fleet_fixture(); config=configs(fleet,**budgets)
                config['goal']['minimum_acquisition_tick']=fleet.observations()['tick']+20
                subject = self.subject(fleet=fleet,harness_config=config)
                result=subject.run();self.check_result(result)
                self.assertEqual(result['harness_result']['termination']['reason'],reason)
                self.assertEqual(result['harness_result']['cleanup']['status'],'not_assessed')
                self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_stop_gates_do_not_prevent_fixture_or_promote_cleanup(self):
        for gate,reason in [('available','transport_unavailable'),('authorized','permission_denied'),('model_fw_matches','model_firmware_mismatch')]:
            with self.subTest(gate=gate):
                fleet=fleet_fixture();subject=self.subject(fleet=fleet,**{gate:False})
                result=subject.run();self.check_result(result)
                self.assertEqual(result['harness_result']['termination']['policy_claim'],'completed')
                self.assertEqual(result['dut_stop_receipt']['status'],'blocked')
                self.assertEqual(result['dut_stop_receipt']['reason_code'],reason)
                self.assertEqual(result['dut_stop_receipt']['commands'],[])
                self.assertEqual(fleet.observations()['devices']['dut']['values']['state'],'transmitting')

    def test_all_families_remain_explicit_synthetic_declarations(self):
        for family in ['ADB','OEM','GUI','AT','DIAG']:
            with self.subTest(family=family):
                subject=self.subject(fleet=fleet_fixture(),transport_family=family)
                result=subject.run();self.check_result(result)
                self.assertEqual(result['dut_stop_receipt']['transport_family'],family)
                self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_uncertain_stop_scenarios_preserve_independent_harness_claim(self):
        for scenario in ['disconnected','timeout_before','timeout_after_stop','partial_delivery','ack_only','no_effect','stale_read','wrong_context']:
            with self.subTest(scenario=scenario):
                subject=self.subject(fleet=fleet_fixture(),scenario=scenario)
                result=subject.run();self.check_result(result)
                self.assertEqual(result['harness_result']['termination']['policy_claim'],'completed')
                self.assertEqual(result['dut_stop_receipt']['status'],'unconfirmed')
                self.assertLessEqual(len(result['dut_stop_receipt']['commands']),2)
                self.assertNotIn('scenario',json.dumps(result))

    def test_same_object_replay_is_detached_history_even_after_restart_of_dut(self):
        subject=self.subject();result=subject.run()
        self.fleet.execute('later:start','dut','start',{});self.fleet.advance('later:tick',1)
        history=self.fleet.history();result['harness_result']['cleanup']['status']='caller mutation'
        self.assertEqual(subject.run(),subject.result())
        self.assertEqual(subject.result()['harness_result']['cleanup']['status'],'not_assessed')
        subject.events().clear();self.assertTrue(subject.events())
        author=subject.author_record();author['stop_configuration']['available']=False
        self.assertTrue(subject.author_record()['stop_configuration']['available'])
        self.assertEqual(self.fleet.history(),history)
        self.assertEqual(self.fleet.observations()['devices']['dut']['values']['state'],'transmitting')

    def test_concurrent_run_has_one_fixture_and_one_stop_read_pair(self):
        subject=self.subject();before=len(self.fleet.history())
        with ThreadPoolExecutor(max_workers=8) as pool: values=list(pool.map(lambda _:subject.run(),range(16)))
        self.assertTrue(all(value==values[0] for value in values))
        delta=self.fleet.history()[before:]
        self.assertEqual(sum(event.get('action')=='stop' and event.get('device_id')=='dut' for event in delta),1)
        self.assertEqual(sum(event.get('action')=='acquire' for event in delta),1)

    def test_stable_id_uses_two_ids_and_separate_namespace(self):
        subject=self.subject();result=subject.run()
        expected='dut-stop-harness:'+hashlib.sha256(json.dumps(['fixture-run','fixture-instance'],separators=(',',':')).encode()).hexdigest()
        self.assertEqual(result['dut_stop_request_id'],expected)
        self.assertEqual(result['dut_stop_receipt']['request_id'],expected)
        self.assertFalse(expected.startswith('request:'))
        fleet=fleet_fixture();config=configs(fleet);config['run_id']='fixture';config['runtime_instance_id']='run-fixture-instance'
        self.assertNotEqual(self.subject(fleet=fleet,harness_config=config).run()['dut_stop_request_id'],expected)

    def test_config_shape_budgets_ids_and_callbacks_are_rejected_before_commands(self):
        original=configs(self.fleet)
        cases=[[],{}, {**original,'runtime':self.fleet},{**original,'policy':lambda value:None},
            {**original,'budgets':{'decisions':True}},{**original,'budgets':{'ticks':0}},
            {**original,'budgets':None},
            {**original,'budgets':{'wall_seconds':float('nan')}},{**original,'budgets':{'unknown':1}},
            {**original,'run_id':'bad id'},{**original,'runtime_instance_id':None}]
        before=self.fleet.history()
        for config in cases:
            with self.subTest(config_keys=list(config) if type(config) is dict else None):
                with self.assertRaisesRegex(ValueError,'^dut_stop_harness_configuration_invalid$'): self.subject(harness_config=config)
        self.assertEqual(self.fleet.history(),before)

    def test_stop_config_is_exact_and_never_accepts_transport_or_callback(self):
        good={'transport_family':'ADB','available':True,'authorized':True,'model_fw_matches':True}
        for config in [{},{**good,'transport':object()},{**good,'callback':lambda:None},{**good,'authorized':1},{**good,'transport_family':'HID'}]:
            with self.subTest(keys=list(config)):
                with self.assertRaisesRegex(ValueError,'^dut_stop_harness_stop_configuration_invalid$'): self.subject(stop_config=config)

    def test_goal_must_bind_same_dut_distinct_power_sensor_and_exact_types(self):
        for change in [{'dut_id':'other'},{'sensor_id':'dut'},{'sensor_id':'missing'},{'minimum_acquisition_tick':True},
                       {'minimum_acquisition_tick':-1},{'kind':'any-goal'},{'extra':SECRET}]:
            with self.subTest(change=change):
                config=configs(self.fleet);config['goal'].update(change)
                with self.assertRaisesRegex(ValueError,'^dut_stop_harness_(configuration|binding)_invalid$'): self.subject(harness_config=config)

    def test_host_catalog_topology_and_action_metadata_must_match(self):
        for field in ['catalog','topology','role_actions']:
            with self.subTest(field=field):
                config=configs(self.fleet)
                if field=='catalog':config[field]['profiles'][0]['model']='other'
                elif field=='topology':config[field]['connections']=[]
                else:config[field]['dut'].pop('start')
                with self.assertRaisesRegex(ValueError,'^dut_stop_harness_binding_invalid$'): self.subject(harness_config=config)

    def test_input_mutation_and_private_truth_do_not_reach_fixture_context(self):
        config=configs(self.fleet);config['catalog']['profiles'][0]['simulation_parameters']['scenario']=SECRET
        subject=self.subject(harness_config=config,scenario='ack_only')
        config['goal']['dut_id']='caller mutation';config['topology']['devices'].clear()
        result=subject.run();self.check_result(result)
        self.assertNotIn(SECRET,json.dumps(subject.events()))
        self.assertNotIn(SECRET,json.dumps(subject._harness._catalog))
        self.assertNotIn('scenario',json.dumps(subject._harness._goal))
        self.assertEqual(subject.author_record()['stop_configuration']['scenario'],'ack_only')

    def test_exact_fleet_and_transitive_helpers_are_checked_without_callback(self):
        class Duck:
            def observations(self):raise AssertionError('must not call')
        with self.assertRaisesRegex(ValueError,'^dut_stop_harness_fleet_invalid$'):
            boundary.SyntheticDutStopHarnessRun(Duck(),'dut',harness_config=configs(self.fleet),stop_config={})
        calls=[];self.fleet._request=lambda *args,**kwargs:calls.append('request')
        with self.assertRaisesRegex(ValueError,'^dut_stop_harness_fleet_invalid$'):self.subject()
        self.assertEqual(calls,[])

    def test_binding_change_after_constructor_is_recorded_without_dispatch(self):
        subject=self.subject();before=self.fleet.history()
        self.fleet._topology['connections']=[]
        result=subject.run();self.check_result(result,'partial')
        self.assertEqual(result['record_error'],'child_binding_changed')
        self.assertEqual((result['harness_dispatch'],result['stop_dispatch']),('not_started','not_sent'))
        self.assertEqual(self.fleet.history(),before)
        self.assertEqual(subject.run(),result)

    def test_failure_after_terminal_keeps_original_harness_and_still_stops(self):
        subject=self.subject();actual=subject._invoke_harness
        def failure():actual();raise RuntimeError(SECRET)
        with patch.object(subject,'_invoke_harness',side_effect=failure):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['harness_error'],'harness_execution_error')
        self.assertEqual(result['harness_dispatch'],'unknown')
        self.assertEqual(result['harness_result'],subject._harness.result())
        self.assertEqual(subject.events(),subject._harness.events())
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_partial_harness_failure_keeps_prior_intent_receipt_and_stop(self):
        subject=self.subject()
        def failure():subject._harness.step();raise RuntimeError(SECRET)
        with patch.object(subject,'_invoke_harness',side_effect=failure):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['harness_error'],'harness_execution_error')
        self.assertIsNone(result['harness_result'])
        self.assertTrue(any(event['type']=='intent' for event in subject.events()))
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')
        history=self.fleet.history();self.assertEqual(subject.run(),result);self.assertEqual(self.fleet.history(),history)

    def test_events_getter_failure_preserves_already_owned_events(self):
        subject=self.subject()
        with patch.object(subject,'_read_harness_events',side_effect=RuntimeError(SECRET)):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['events_error'],'harness_events_error')
        self.assertEqual(subject.events(),subject._harness.events())
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_adapter_exception_before_or_after_actual_dispatch_remains_unknown(self):
        for after in [False,True]:
            with self.subTest(after=after):
                fleet=fleet_fixture();subject=self.subject(fleet=fleet);actual=subject._invoke_stop
                def failure():
                    if after:actual()
                    raise RuntimeError(SECRET)
                with patch.object(subject,'_invoke_stop',side_effect=failure):result=subject.run()
                self.check_result(result,'partial')
                self.assertEqual(result['dut_stop_error'],'dut_stop_execution_error')
                self.assertEqual(result['stop_dispatch'],'unknown')
                self.assertIsNone(result['dut_stop_receipt'])
                self.assertEqual(fleet.observations()['devices']['dut']['values']['state'],'idle' if after else 'transmitting')
                history=fleet.history();self.assertEqual(subject.run(),result);self.assertEqual(fleet.history(),history)
                if after:self.assertIsNotNone(subject.author_record()['dut_stop_author'])

    def test_invalid_harness_return_is_private_and_does_not_suppress_stop(self):
        subject=self.subject();actual=subject._invoke_harness
        def invalid():value=actual();value['author']=SECRET;return value
        with patch.object(subject,'_invoke_harness',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['harness_error'],'harness_result_invalid')
        self.assertIsNone(result['harness_result'])
        self.assertIn(SECRET,json.dumps(subject.author_record()['harness_return']))
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_well_shaped_substituted_harness_claim_is_rejected(self):
        subject=self.subject();actual=subject._invoke_harness
        def invalid():value=actual();value['termination']['policy_claim']='failed';return value
        with patch.object(subject,'_invoke_harness',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['harness_error'],'harness_result_invalid')
        self.assertIsNone(result['harness_result'])
        self.assertEqual(subject._harness.result()['termination']['policy_claim'],'completed')
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_invalid_stop_return_is_private_with_original_harness_kept(self):
        for field,value in [('profile_id','wrong'),('request_id','other'),('hardware_verified',True),('current_stop_authority',True),('author',SECRET)]:
            with self.subTest(field=field):
                subject=self.subject(fleet=fleet_fixture());actual=subject._invoke_stop
                def invalid():result=actual();result[field]=value;return result
                with patch.object(subject,'_invoke_stop',side_effect=invalid):result=subject.run()
                self.check_result(result,'partial')
                self.assertEqual(result['dut_stop_error'],'dut_stop_receipt_invalid')
                self.assertEqual(result['stop_dispatch'],'returned')
                self.assertIsNone(result['dut_stop_receipt'])
                self.assertIsNotNone(result['harness_result'])
                self.assertIsNotNone(subject.author_record()['dut_stop_return'])

    def test_well_shaped_stop_context_substitution_is_rejected(self):
        subject=self.subject();actual=subject._invoke_stop
        def invalid():
            value=actual();value['request_context']['setup_revision']+=1;return value
        with patch.object(subject,'_invoke_stop',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['dut_stop_error'],'dut_stop_receipt_invalid')
        self.assertIsNone(result['dut_stop_receipt'])
        self.assertIsNotNone(subject.author_record()['dut_stop_author'])

    def test_private_dut_identity_drift_is_refused_before_fixture_commands(self):
        subject=self.subject();before=self.fleet.history()
        self.fleet._devices['dut'].profile_id='other-profile'
        result=subject.run();self.check_result(result,'partial')
        self.assertEqual(result['record_error'],'child_binding_changed')
        self.assertEqual(self.fleet.history(),before)

    def test_replaced_child_policy_is_refused_before_its_callback(self):
        subject=self.subject();calls=[]
        subject._harness._policy=lambda context:calls.append(context)
        before=self.fleet.history();result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['record_error'],'child_binding_changed')
        self.assertEqual(calls,[]);self.assertEqual(self.fleet.history(),before)

    def test_parent_result_wrapper_failure_keeps_children_and_replay(self):
        subject=self.subject();actual=subject._compose_result
        def invalid():result=actual();result['invalid_wrapper_fixture']=object();return result
        with patch.object(subject,'_compose_result',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['record_error'],'wrapper_record_error')
        self.assertEqual(result['harness_result'],subject._harness.result())
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')
        self.assertEqual(subject.events(),subject._harness.events())
        history=self.fleet.history();self.assertEqual(subject.run(),result);self.assertEqual(self.fleet.history(),history)

    def test_parent_author_wrapper_failure_keeps_children_and_replay(self):
        subject=self.subject();actual=subject._compose_author
        def invalid():result=actual();result['invalid_wrapper_fixture']=object();return result
        with patch.object(subject,'_compose_author',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['record_error'],'wrapper_record_error')
        author=subject.author_record()
        self.assertEqual(author['diagnostic_error'],'wrapper_record_error')
        self.assertIsNotNone(author['dut_stop_author'])
        self.assertEqual(author['harness_events'],subject.events())
        self.assertEqual(author['result'],result)
        history=self.fleet.history();self.assertEqual(subject.run(),result);self.assertEqual(self.fleet.history(),history)

    def test_child_event_depth32_is_not_rejected_by_parent_list_or_author(self):
        subject=self.subject();actual=subject._read_harness_events
        def nested():
            values=actual();child='LABELLED_STORAGE_LEAF'
            for _ in range(26):child={'child':child}
            values[0]['payload']['observation']['devices']['dut']['values']['storage_fixture']=child
            return values
        with patch.object(subject,'_read_harness_events',side_effect=nested):result=subject.run()
        self.check_result(result)
        self.assertIn('LABELLED_STORAGE_LEAF',json.dumps(subject.events()))
        self.assertEqual(subject.author_record()['harness_events'],subject.events())

    def test_invalid_event_is_private_without_erasing_other_child_events(self):
        subject=self.subject();actual=subject._read_harness_events
        def invalid():values=actual();values[1]['payload']['author']=SECRET;return values
        with patch.object(subject,'_read_harness_events',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['events_error'],'harness_events_invalid')
        self.assertNotIn(SECRET,json.dumps(subject.events()))
        self.assertIn(SECRET,json.dumps(subject.author_record()['harness_events']))
        self.assertTrue(subject.events())
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_unserializable_event_keeps_valid_prior_and_later_records(self):
        subject=self.subject();actual=subject._read_harness_events
        def invalid():values=actual();values[1]['payload']['storage_fixture']=object();return values
        with patch.object(subject,'_read_harness_events',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['events_error'],'harness_events_invalid')
        self.assertEqual(subject.events()[0]['sequence'],1)
        self.assertEqual(subject.events()[-1]['type'],'termination')
        self.assertNotIn(2,[event['sequence'] for event in subject.events()])
        self.assertEqual(result['dut_stop_receipt']['status'],'confirmed_synthetic')

    def test_missing_event_payload_is_refused_without_losing_later_events(self):
        subject=self.subject();actual=subject._read_harness_events
        def invalid():values=actual();values[1]['payload']={};return values
        with patch.object(subject,'_read_harness_events',side_effect=invalid):result=subject.run()
        self.check_result(result,'partial')
        self.assertEqual(result['events_error'],'harness_events_invalid')
        self.assertEqual(subject.events()[-1]['type'],'termination')
        self.assertNotIn(2,[event['sequence'] for event in subject.events()])

    def test_maximum_child_component_storage_budgets_fit_parent_wrappers(self):
        """Serialization-only size/depth fixtures; not semantic child results."""
        subject=self.subject()
        def sized(limit,depth):
            nested='LABELLED_STORAGE_LEAF'
            for _ in range(depth-1):nested={'child':nested}
            value={'nested':nested,'storage_padding':''}
            value['storage_padding']='x'*(limit-len(boundary._fingerprint(value).encode('utf-8')))
            self.assertEqual(len(boundary._fingerprint(value).encode('utf-8')),limit)
            return value
        harness=sized(256*1024,32);receipt=sized(96*1024,32)
        result=subject._core_result();result.update(harness_result=harness,dut_stop_receipt=receipt)
        stored=boundary._copy(result,384*1024,max_depth=36)
        self.assertEqual(stored['harness_result'],harness)
        author=subject._core_author();author.update(harness_configuration={key:sized(1024*1024,32) for key in ('goal','catalog','topology','role_actions')},
            harness_return=harness,dut_stop_return=receipt,dut_stop_author=sized(256*1024,36),
            harness_events=[sized(512*1024,32)]*64,result=stored)
        copied=boundary._copy(author,38*1024*1024,max_depth=40)
        size=len(boundary._fingerprint(copied).encode('utf-8'))
        self.assertGreater(size,36*1024*1024)
        self.assertLessEqual(size,38*1024*1024)
        self.assertEqual(copied['harness_events'][-1],author['harness_events'][-1])
        self.assertEqual(copied['dut_stop_author'],author['dut_stop_author'])

    def test_api_does_not_open_file_socket_process_sdk_or_external_accounts(self):
        subject=self.subject()
        with patch.object(Path,'open') as files,patch('builtins.open') as opens,patch('os.open') as osopen, \
             patch.object(socket,'socket') as sockets,patch.object(subprocess,'Popen') as processes:
            result=subject.run();subject.result();subject.events();subject.author_record();subject.run()
        self.check_result(result)
        for mock in [files,opens,osopen,sockets,processes]:mock.assert_not_called()


if __name__=='__main__':unittest.main()
