"""Synthetic stop boundary over existing exact Fleet; never uses a real DUT."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import dut_stop_simulation as stop_boundary
from labflow.virtual_fleet.core import VirtualFleet
from labflow.virtual_fleet import rf


KEYS = {'schema_version','kind','execution_mode','synthetic','hardware_verified','physical_model_verified',
    'model_execution_verified','oem_support_status','request_id','transport_family','device_id','profile_id',
    'request_context','status','reason_code','acknowledgement','stop_response','read_observation','commands',
    'receipt_scope','current_stop_authority','observation_context'}


def fleet_fixture(*,start=True):
    profile = {'profile_id':'fixture-dut','role':'dut','model':'SYNTHETIC-DUT',
        'ports':copy.deepcopy(rf.ROLE_PORTS['dut']),
        'simulation_parameters':{'requires_power':False,'requires_environment':False,'frequency_hz':1e9,
            'power_dbm':7,'bandwidth_hz':1e6,'duty_cycle':.5,'modulation':'QPSK','crest_factor_db':3}}
    fleet = VirtualFleet({'profiles':[profile]}, {'devices':[{'id':'dut','profile_id':'fixture-dut'}],'connections':[]},
        factories=rf.DEVICE_FACTORIES,role_actions=rf.ROLE_ACTIONS,seed=13)
    if start:
        fleet.execute('setup:start','dut','start',{})
        fleet.advance('setup:clock',1)
    return fleet


class DutStopTests(unittest.TestCase):
    def setUp(self):
        self.fleet = fleet_fixture()

    def adapter(self,**kwargs):
        return stop_boundary.SyntheticDutStopAdapter(kwargs.pop('fleet',self.fleet),kwargs.pop('dut_id','dut'),
            transport_family=kwargs.pop('transport_family','ADB'),available=kwargs.pop('available',True),
            authorized=kwargs.pop('authorized',True),model_fw_matches=kwargs.pop('model_fw_matches',True),**kwargs)

    def assert_receipt(self,value,status):
        self.assertEqual(set(value),KEYS)
        self.assertEqual(value['status'],status)
        self.assertEqual((value['schema_version'],value['kind'],value['execution_mode']),
                         (1,'synthetic_dut_stop_receipt','virtual_fleet_dut_stop'))
        self.assertIs(value['synthetic'],True)
        for key in ('hardware_verified','physical_model_verified','model_execution_verified','current_stop_authority'):
            self.assertIs(value[key],False)
        self.assertEqual(value['oem_support_status'],'not_assessed')
        self.assertEqual(value['receipt_scope'],'historical_observation')
        self.assertEqual(set(value['acknowledgement']),{'received','completion','origin'})
        def keys(item):
            if type(item) is dict:
                for key,child in item.items():
                    self.assertNotIn(key,{'scenario','author','fault','truth','secret','available','authorized','model_fw_matches'})
                    keys(child)
            elif type(item) is list:
                for child in item: keys(child)
        keys(value)

    def test_normal_executes_existing_stop_and_same_dut_read(self):
        before = self.fleet.observations()
        self.assertEqual(before['devices']['dut']['values']['state'],'transmitting')
        history = len(self.fleet.history())
        adapter = self.adapter()
        self.assertEqual(len(self.fleet.history()),history)
        result = adapter.stop('request:normal')
        self.assert_receipt(result,'confirmed_synthetic')
        self.assertEqual(result['reason_code'],'observed_stopped')
        self.assertEqual(result['request_context'],{'tick':before['tick'],'setup_revision':before['setup_revision']})
        self.assertEqual(result['read_observation']['values']['state'],'idle')
        self.assertEqual(result['read_observation']['values']['outputs'],{})
        self.assertEqual(result['stop_response']['device_id'],result['read_observation']['device_id'])
        self.assertEqual([item['action'] for item in result['commands']],['stop','read'])
        self.assertEqual([item['action'] for item in self.fleet.history()[history:]],['stop','read'])

    def test_adb_and_oem_availability_do_not_select_a_fallback(self):
        for selected in ('ADB','OEM'):
            fleet = fleet_fixture()
            alternate = 'OEM' if selected=='ADB' else 'ADB'
            blocked = self.adapter(fleet=fleet,transport_family=alternate,available=False)
            before = len(fleet.history())
            result = blocked.stop('unavailable')
            self.assert_receipt(result,'blocked')
            self.assertEqual(result['transport_family'],alternate)
            self.assertEqual(len(fleet.history()),before)
            allowed = self.adapter(fleet=fleet,transport_family=selected)
            result = allowed.stop('selected')
            self.assert_receipt(result,'confirmed_synthetic')
            self.assertEqual(result['transport_family'],selected)
            self.assertEqual(len(fleet.history())-before,2)

    def test_gui_at_and_diag_remain_distinct_explicit_families(self):
        for family in ('GUI','AT','DIAG'):
            result = self.adapter(fleet=fleet_fixture(),transport_family=family).stop('family')
            self.assert_receipt(result,'confirmed_synthetic')
            self.assertEqual(result['transport_family'],family)

    def test_each_access_gate_blocks_all_dut_commands(self):
        for changes,reason in (({'available':False},'transport_unavailable'),
                ({'authorized':False},'permission_denied'),({'model_fw_matches':False},'model_firmware_mismatch')):
            before = self.fleet.observations()
            history = self.fleet.history()
            result = self.adapter(**changes).stop(reason)
            self.assert_receipt(result,'blocked')
            self.assertEqual(result['reason_code'],reason)
            self.assertEqual(result['commands'],[])
            self.assertEqual(self.fleet.history(),history)
            self.assertEqual(self.fleet.observations(),before)

    def test_invalid_family_and_nonbool_author_gates_are_rejected(self):
        for family in ('AUTO','USB','HID','iOS','firmware','adb',None):
            with self.assertRaisesRegex(ValueError,'^dut_stop_configuration_invalid$'):
                self.adapter(transport_family=family)
        for name in ('available','authorized','model_fw_matches'):
            for value in (0,1,None,'true'):
                with self.assertRaisesRegex(ValueError,'^dut_stop_configuration_invalid$'):
                    self.adapter(**{name:value})

    def test_duck_subclass_and_non_dut_objects_are_refused_without_execution(self):
        class Duck:
            def __getattr__(self,name): raise AssertionError('duck was invoked')
        class Derived(VirtualFleet): pass
        for fleet in (Duck(),object.__new__(Derived)):
            with self.assertRaisesRegex(ValueError,'^dut_stop_fleet_invalid$'): self.adapter(fleet=fleet)
        with self.assertRaisesRegex(ValueError,'^dut_stop_device_invalid$'): self.adapter(dut_id='missing')
        fleet = fleet_fixture()
        fleet._devices['dut'].perform = lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('injected IO'))
        with self.assertRaisesRegex(ValueError,'^dut_stop_fleet_invalid$'): self.adapter(fleet=fleet)

    def test_disconnection_and_timeout_before_send_do_not_stop(self):
        for scenario,reason in (('disconnected','transport_disconnected'),('timeout_before','deadline_exceeded')):
            history = self.fleet.history()
            result = self.adapter(scenario=scenario).stop('failure:'+scenario)
            self.assert_receipt(result,'unconfirmed')
            self.assertEqual(result['reason_code'],reason)
            self.assertEqual(result['commands'],[])
            self.assertEqual(self.fleet.history(),history)
            self.assertEqual(self.fleet.observations()['devices']['dut']['values']['state'],'transmitting')

    def test_timeout_after_actual_stop_keeps_unknown_ack_and_no_retry(self):
        adapter = self.adapter(scenario='timeout_after_stop')
        result = adapter.stop('timeout')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'deadline_exceeded')
        self.assertFalse(result['acknowledgement']['received'])
        self.assertIsNone(result['stop_response'])
        self.assertIsNone(result['read_observation'])
        self.assertEqual([value['action'] for value in result['commands']],['stop'])
        self.assertEqual(self.fleet.observations()['devices']['dut']['values']['state'],'idle')
        self.assertIsNotNone(adapter.author_record('timeout')['exchanges'][0]['raw_response'])
        history = self.fleet.history()
        self.assertEqual(adapter.stop('timeout'),result)
        self.assertEqual(self.fleet.history(),history)

    def test_partial_and_no_effect_use_real_current_read_without_second_state_engine(self):
        for scenario,reason in (('partial_delivery','partial_acknowledgement'),('no_effect','stop_not_observed')):
            result = self.adapter(scenario=scenario).stop(scenario)
            self.assert_receipt(result,'unconfirmed')
            self.assertEqual(result['reason_code'],reason)
            self.assertEqual(result['acknowledgement']['origin'],'synthetic_delivery')
            self.assertEqual([value['action'] for value in result['commands']],['read'])
            self.assertIsNone(result['stop_response'])
            self.assertEqual(result['read_observation']['values']['state'],'transmitting')

    def test_ack_only_never_confirms_without_separate_read(self):
        result = self.adapter(scenario='ack_only').stop('ack')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'observation_missing')
        self.assertTrue(result['acknowledgement']['received'])
        self.assertIsNotNone(result['stop_response'])
        self.assertIsNone(result['read_observation'])
        self.assertEqual(len(result['commands']),1)

    def test_stale_and_wrong_context_preserve_private_raw_packets(self):
        for scenario in ('stale_read','wrong_context'):
            adapter = self.adapter(fleet=fleet_fixture(),scenario=scenario)
            result = adapter.stop('context')
            self.assert_receipt(result,'unconfirmed')
            self.assertEqual(result['reason_code'],'context_mismatch')
            self.assertIsNone(result['read_observation'])
            author = adapter.author_record('context')
            self.assertEqual(author['configuration']['scenario'],scenario)
            read = author['exchanges'][-1]
            self.assertEqual(read['raw_response']['values']['state'],'idle')
            self.assertNotEqual(read['raw_response'],read['received_response'])

    def test_same_id_is_detached_history_even_after_dut_restarts(self):
        adapter = self.adapter()
        original = adapter.stop('same')
        expected = copy.deepcopy(original)
        original['read_observation']['values']['state'] = 'caller mutation'
        self.fleet.execute('restart','dut','start',{})
        self.fleet.advance('restart-clock',1)
        history = self.fleet.history()
        replay = adapter.stop('same')
        self.assertEqual(replay,expected)
        self.assertEqual(self.fleet.history(),history)
        self.assertEqual(self.fleet.observations()['devices']['dut']['values']['state'],'transmitting')
        self.assertFalse(replay['current_stop_authority'])

    def test_cache_is_bounded_without_eviction_and_existing_ids_replay(self):
        adapter = self.adapter(available=False)
        first = adapter.stop('id0')
        for index in range(1,128): adapter.stop('id'+str(index))
        history = self.fleet.history()
        with self.assertRaisesRegex(ValueError,'^dut_stop_cache_full$'): adapter.stop('overflow')
        self.assertEqual(adapter.stop('id0'),first)
        self.assertEqual(self.fleet.history(),history)

    def test_concurrent_same_request_has_one_stop_read_pair(self):
        adapter = self.adapter()
        before = len(self.fleet.history())
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _:adapter.stop('same'),range(16)))
        self.assertTrue(all(result==results[0] for result in results))
        self.assertEqual([event['action'] for event in self.fleet.history()[before:]],['stop','read'])

    def test_invalid_and_unknown_ids_do_not_issue_commands(self):
        adapter = self.adapter()
        history = self.fleet.history()
        for value in ('','한글','x'*129,'with space',True,None):
            with self.assertRaisesRegex(ValueError,'^dut_stop_request_invalid$'): adapter.stop(value)
        with self.assertRaisesRegex(ValueError,'^dut_stop_request_unknown$'): adapter.author_record('unknown')
        self.assertEqual(self.fleet.history(),history)

    def test_author_record_is_detached_and_hidden_from_operator(self):
        adapter = self.adapter(scenario='partial_delivery')
        result = adapter.stop('author')
        author = adapter.author_record('author')
        author['configuration']['scenario'] = 'mutated'
        author['receipt']['status'] = 'mutated'
        self.assertEqual(adapter.author_record('author')['configuration']['scenario'],'partial_delivery')
        self.assertEqual(adapter.stop('author'),result)
        self.assertNotIn('partial_delivery',json.dumps(result))

    def test_response_context_and_synthetic_type_attacks_are_never_confirmed(self):
        attacks = {'tick':99,'setup_revision':99,'device_id':'other','profile_id':'other',
                   'role':'power_sensor','synthetic':1,'hardware_verified':0}
        for field,value in attacks.items():
            with self.subTest(field=field):
                adapter = self.adapter(fleet=fleet_fixture())
                actual = adapter._command
                def command(request_id,action):
                    response = actual(request_id,action)
                    if action=='read': response[field]=value
                    return response
                with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('tampered')
                self.assert_receipt(result,'unconfirmed')
                self.assertIsNone(result['read_observation'])

    def test_unknown_response_fields_never_leak_hidden_answers(self):
        adapter = self.adapter()
        actual = adapter._command
        def command(request_id,action):
            response = actual(request_id,action)
            if action=='read': response['values']['secret']='PRIVATE_AUTHOR_ANSWER'
            return response
        with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('secret')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'invalid_response')
        self.assertNotIn('PRIVATE_AUTHOR_ANSWER',json.dumps(result))
        self.assertIn('PRIVATE_AUTHOR_ANSWER',json.dumps(adapter.author_record('secret')))

    def test_stop_ack_cannot_add_reason_or_claim_remaining_rf_output(self):
        for inject in ('reason','rf'):
            adapter = self.adapter(fleet=fleet_fixture())
            signal = copy.deepcopy(adapter._fleet.observations()['devices']['dut']['values']['outputs']['rf'])
            actual = adapter._command
            def command(request_id,action):
                response = actual(request_id,action)
                if action=='stop':
                    if inject=='reason': response['values']['reason']='PRIVATE_STOP_ANSWER'
                    else: response['values']['outputs']={'rf':signal}
                return response
            with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('bad-ack')
            with self.subTest(inject=inject):
                self.assert_receipt(result,'unconfirmed')
                self.assertEqual(result['reason_code'],'invalid_response')
                self.assertNotIn('PRIVATE_STOP_ANSWER',json.dumps(result))

    def test_failed_virtual_reason_is_private_diagnostic_not_operator_payload(self):
        self.fleet.author_control('author-offline','dut','disconnect',True)
        adapter = self.adapter()
        actual = adapter._command
        def command(request_id,action):
            response = actual(request_id,action)
            response['values']['reason']='PRIVATE_FAILURE_ANSWER'
            return response
        with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('failed-reason')
        self.assert_receipt(result,'unconfirmed')
        self.assertNotIn('PRIVATE_FAILURE_ANSWER',json.dumps(result))
        self.assertIn('PRIVATE_FAILURE_ANSWER',json.dumps(adapter.author_record('failed-reason')))

    def test_author_configuration_change_during_stop_stays_unconfirmed(self):
        adapter = self.adapter()
        actual = adapter._command
        def command(request_id,action):
            response = actual(request_id,action)
            if action=='stop': adapter._config=replace(adapter._config,transport_family='OEM')
            return response
        with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('changed')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'configuration_changed')
        self.assertEqual(result['transport_family'],'ADB')
        self.assertEqual([value['action'] for value in result['commands']],['stop'])

    def test_malformed_configuration_change_is_sanitized_and_cached(self):
        for during in (False,True):
            adapter = self.adapter(fleet=fleet_fixture())
            actual = adapter._command
            def command(request_id,action):
                response = actual(request_id,action)
                adapter._config=replace(adapter._config,scenario=float('nan'))
                return response
            if not during: adapter._config=replace(adapter._config,scenario=object())
            with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('malformed')
            self.assert_receipt(result,'unconfirmed')
            self.assertEqual(result['reason_code'],'configuration_changed')
            self.assertEqual(len(result['commands']),1 if during else 0)
            self.assertEqual(adapter.stop('malformed'),result)

    def test_external_setup_change_after_stop_is_not_current_confirmation(self):
        adapter = self.adapter()
        actual = adapter._command
        def command(request_id,action):
            response = actual(request_id,action)
            if action=='stop': self.fleet.execute('external-start','dut','start',{})
            return response
        with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('changed')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'context_mismatch')
        self.assertEqual([value['action'] for value in result['commands']],['stop'])

    def test_unknown_post_stop_exception_is_cached_without_resend(self):
        adapter = self.adapter()
        actual = adapter._command
        def command(request_id,action):
            actual(request_id,action)
            raise RuntimeError('PRIVATE_POST_STOP_EXCEPTION')
        with patch.object(adapter,'_command',side_effect=command): result = adapter.stop('uncertain')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'runtime_error')
        self.assertEqual(result['acknowledgement'],{'received':False,'completion':'unknown','origin':'none'})
        self.assertNotIn('PRIVATE_POST_STOP_EXCEPTION',json.dumps(result))
        history = self.fleet.history()
        self.assertEqual(adapter.stop('uncertain'),result)
        self.assertEqual(self.fleet.history(),history)

    def test_legal_nested_packet_keeps_original_context_and_private_diagnostic(self):
        for levels in (26,28,29,30):
            with self.subTest(levels=levels):
                fleet = fleet_fixture()
                adapter = self.adapter(fleet=fleet)
                before = fleet.observations()
                actual = adapter._command
                nested = 'PRIVATE_NESTED_PACKET'
                for _ in range(levels): nested={'child':nested}
                def command(request_id,action):
                    response = actual(request_id,action)
                    if action=='stop': response['values']['unknown_nested']=nested
                    return response
                with patch.object(adapter,'_command',side_effect=command): result=adapter.stop('nested')
                self.assert_receipt(result,'unconfirmed')
                self.assertEqual(result['reason_code'],'invalid_response')
                self.assertEqual(result['request_context'],{'tick':before['tick'],'setup_revision':before['setup_revision']})
                self.assertEqual([value['action'] for value in result['commands']],['stop'])
                self.assertEqual(result['acknowledgement']['completion'],'unknown')
                self.assertEqual(fleet.observations()['devices']['dut']['values']['state'],'idle')
                author = adapter.author_record('nested')
                self.assertEqual(author['exchanges'][0]['raw_response']['values']['unknown_nested'],nested)
                self.assertEqual(author['exchanges'][0]['received_response']['values']['unknown_nested'],nested)
                self.assertEqual(author['receipt'],result)
                history = fleet.history()
                self.assertEqual(adapter.stop('nested'),result)
                self.assertEqual(fleet.history(),history)
                author['exchanges'][0]['raw_response']['values']['unknown_nested']='caller mutation'
                self.assertEqual(adapter.author_record('nested')['exchanges'][0]['raw_response']['values']['unknown_nested'],nested)

    def test_overdepth_packet_is_sanitized_and_never_retransmitted(self):
        adapter = self.adapter()
        actual = adapter._command
        nested = 'outside packet depth'
        for _ in range(31): nested={'child':nested}
        def command(request_id,action):
            response = actual(request_id,action)
            response['values']['unknown_nested']=nested
            return response
        with patch.object(adapter,'_command',side_effect=command): result=adapter.stop('overdepth')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'invalid_response')
        self.assertEqual(result['acknowledgement']['completion'],'unknown')
        self.assertEqual([item['action'] for item in result['commands']],['stop'])
        self.assertEqual(adapter.author_record('overdepth')['exchanges'][0]['error_code'],'invalid_response')
        history = self.fleet.history()
        self.assertEqual(adapter.stop('overdepth'),result)
        self.assertEqual(self.fleet.history(),history)

    def test_transitive_fleet_helper_overrides_are_rejected_before_callbacks(self):
        for name in ('_request','_envelope','_propagate','_check_result','_remember'):
            with self.subTest(name=name):
                fleet = fleet_fixture()
                calls = []
                original = getattr(fleet,name)
                def marker(*args,**kwargs):
                    calls.append(name)
                    return original(*args,**kwargs)
                setattr(fleet,name,marker)
                with self.assertRaisesRegex(ValueError,'^dut_stop_fleet_invalid$'): self.adapter(fleet=fleet)
                self.assertEqual(calls,[])

    def test_transitive_device_helper_and_class_override_are_rejected(self):
        fleet = fleet_fixture()
        calls = []
        original = fleet._devices['dut']._publish
        def marker(*args,**kwargs):
            calls.append('publish')
            return original(*args,**kwargs)
        fleet._devices['dut']._publish=marker
        with self.assertRaisesRegex(ValueError,'^dut_stop_fleet_invalid$'): self.adapter(fleet=fleet)
        self.assertEqual(calls,[])
        fleet = fleet_fixture()
        original_request = VirtualFleet._request
        def request(*args,**kwargs):
            calls.append('request')
            return original_request(*args,**kwargs)
        with patch.object(VirtualFleet,'_request',request):
            with self.assertRaisesRegex(ValueError,'^dut_stop_fleet_invalid$'): self.adapter(fleet=fleet)
        self.assertEqual(calls,[])

    def test_helper_override_after_creation_never_runs_or_confirms(self):
        adapter = self.adapter()
        calls = []
        original = self.fleet._request
        def marker(*args,**kwargs):
            calls.append('request')
            return original(*args,**kwargs)
        self.fleet._request=marker
        result = adapter.stop('overridden')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(calls,[])
        self.assertEqual(result['commands'],[])
        self.assertEqual(adapter.stop('overridden'),result)

    def test_maximum_json_component_budgets_fit_author_wrapper_and_replay(self):
        """Serialization-only envelope fixtures, not valid semantic DUT results."""
        def sized(value,size):
            value['storage_fixture_padding']=''
            length = len(stop_boundary._fingerprint(value).encode('utf-8'))
            value['storage_fixture_padding']='x'*(size-length)
            self.assertEqual(len(stop_boundary._fingerprint(value).encode('utf-8')),size)
            return value
        for invalid_wrapper in (False,True):
            with self.subTest(invalid_wrapper=invalid_wrapper):
                adapter = self.adapter()
                request_id = 'budget-components'
                before = self.fleet.observations()
                commands = []
                for action in ('stop','read'):
                    command_id = adapter._id(request_id,action)
                    adapter._command(command_id,action)
                    commands.append({'request_id':command_id,'action':action})
                nested = 'PRIVATE_MAX_DEPTH_PACKET'
                for _ in range(31): nested={'child':nested}
                packet = sized({'storage_fixture_nested':nested},32*1024)
                self.assertEqual(stop_boundary._copy(packet,32*1024),packet)
                receipt = adapter._base(request_id)
                receipt.update(status='unconfirmed',reason_code='invalid_response',commands=commands,
                    request_context={'tick':before['tick'],'setup_revision':before['setup_revision']},
                    acknowledgement={'received':False,'completion':'unknown','origin':'none'})
                receipt = sized(receipt,96*1024)
                author = {'schema_version':1,'kind':'synthetic_dut_stop_author_record','request_id':request_id,
                    'configuration':adapter._configuration,'request_context':receipt['request_context'],
                    'exchanges':[{**command,'raw_response':packet,'received_response':packet,'error_code':'invalid_response'}
                                 for command in commands],'receipt':None}
                if invalid_wrapper: author['invalid_wrapper_fixture']=object()
                result = adapter._finish(request_id,receipt,author)
                diagnostic = adapter.author_record(request_id)
                encoded = stop_boundary._fingerprint(diagnostic).encode('utf-8')
                self.assertGreater(len(encoded),224*1024)
                self.assertLessEqual(len(encoded),256*1024)
                for event in diagnostic['exchanges']:
                    for field in ('raw_response','received_response'): self.assertEqual(event[field],packet)
                self.assertEqual(diagnostic['receipt'],result)
                if invalid_wrapper:
                    self.assertEqual(diagnostic['diagnostic_error'],'author_record_invalid')
                    self.assertEqual(result['reason_code'],'runtime_error')
                history = self.fleet.history()
                self.assertEqual(adapter.stop(request_id),result)
                self.assertEqual(self.fleet.history(),history)

    def test_author_aggregate_failure_keeps_progress_and_bounded_raw_diagnostics(self):
        adapter = self.adapter()
        actual = adapter._finish
        before = self.fleet.observations()
        def finish(request_id,receipt,author):
            author['oversized_wrapper_fixture']='x'*(256*1024)
            return actual(request_id,receipt,author)
        with patch.object(adapter,'_finish',side_effect=finish): result=adapter.stop('aggregate-failure')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'runtime_error')
        self.assertEqual([event['action'] for event in result['commands']],['stop','read'])
        self.assertEqual(result['request_context'],{'tick':before['tick'],'setup_revision':before['setup_revision']})
        self.assertEqual(result['acknowledgement']['completion'],'acknowledged')
        diagnostic = adapter.author_record('aggregate-failure')
        self.assertEqual(diagnostic['diagnostic_error'],'author_record_invalid')
        self.assertIsNotNone(diagnostic['exchanges'][0]['raw_response'])
        self.assertIsNotNone(diagnostic['exchanges'][1]['received_response'])
        self.assertEqual(diagnostic['receipt'],result)
        self.assertLessEqual(len(stop_boundary._fingerprint(diagnostic).encode('utf-8')),256*1024)
        history = self.fleet.history()
        self.assertEqual(adapter.stop('aggregate-failure'),result)
        self.assertEqual(self.fleet.history(),history)

    def test_no_file_socket_process_sdk_or_catalog_io(self):
        adapter = self.adapter()
        with patch.object(Path,'open') as files, patch('builtins.open') as opens, patch('os.open') as osopen, \
             patch.object(socket,'socket') as network, patch.object(socket,'getaddrinfo') as dns, \
             patch.object(subprocess,'Popen') as process:
            result = adapter.stop('pure')
            author = adapter.author_record('pure')
            for operation in (files,opens,osopen,network,dns,process): operation.assert_not_called()
        self.assert_receipt(result,'confirmed_synthetic')
        self.assertEqual(author['receipt'],result)

    def test_existing_dut_disconnection_returns_unconfirmed_virtual_reply(self):
        self.fleet.author_control('author-disconnect','dut','disconnect',True)
        result = self.adapter().stop('disconnected-dut')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['reason_code'],'transport_disconnected')
        self.assertEqual(result['stop_response']['status'],'disconnected')
        self.assertEqual([command['action'] for command in result['commands']],['stop'])

    def test_synthetic_ack_without_stop_never_confirms_even_when_dut_is_idle(self):
        result = self.adapter(fleet=fleet_fixture(start=False),scenario='no_effect').stop('already-idle')
        self.assert_receipt(result,'unconfirmed')
        self.assertEqual(result['read_observation']['values']['state'],'idle')
        self.assertEqual(result['reason_code'],'stop_not_observed')

    def test_separate_adapters_namespace_same_operator_id(self):
        first = self.adapter().stop('same-id')
        self.fleet.execute('restart-two','dut','start',{})
        self.fleet.advance('restart-two-clock',1)
        second = self.adapter().stop('same-id')
        self.assert_receipt(second,'confirmed_synthetic')
        self.assertNotEqual(first['commands'][0]['request_id'],second['commands'][0]['request_id'])
        self.assertGreater(second['request_context']['setup_revision'],first['observation_context']['setup_revision'])


if __name__=='__main__':
    unittest.main()
