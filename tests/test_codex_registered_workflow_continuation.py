"""Authored fixed native profiles only; installed model/vendor calls forbidden."""
import importlib
import copy
from datetime import datetime,timedelta,timezone
import json
import sqlite3
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_codex_conducted_workflow_registration import RegistrationTests,C,H,api as registrar,BUDGET,REAL_POPEN
from labflow import codex_registered_conducted_workflow_host as host
from labflow import codex_cli_response as producer

try: api=importlib.import_module('labflow.codex_registered_workflow_continuation')
except ModuleNotFoundError: api=None


class ContinuationTests(RegistrationTests):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned manual continuation API absent')
        if self._testMethodName in ('test_budget_deducts_original_one_and_elapsed','test_unknown_overbudget_and_zero_seed_are_closed'):
            self.enterContext(patch('subprocess.Popen',side_effect=AssertionError('MODEL_VENDOR_FORBIDDEN')))
            return
        super().setUp()
        self.make_completed_inputs()
        self.enterContext(patch('subprocess.Popen',side_effect=AssertionError('MODEL_VENDOR_FORBIDDEN')))

    def fixture(self):
        """Authored historical original1, not an executed model receipt."""
        prepared=registrar.prepare_registered_conducted_workflow(scenario_id='REG-CASE',requested_model='gpt-6-astra')
        self.assertEqual(prepared['status'],'prepared',prepared)
        self.profile=self.target
        self.evidence=self.target/'runs/REG-P1'
        self.config=json.loads((self.target/'operator-control.json').read_bytes())
        self.workflow=json.loads((self.target/'registered-workflow.json').read_bytes())
        self.journal=self.target/'workflow-continuation.sqlite3'
        legacy=json.loads((ROOT/'docs/fcc/codex_first_decision_contract.json').read_text(encoding='utf-8'))['response_schema']['literal_utf8'].encode().replace(b'"anyOf"',b'"oneOf"')
        # The historical fixture is explicitly authored, never a migration API.
        self.put(self.target/'response-schema.json',legacy)
        self.meta['files']['response-schema.json']=self.put(self.data/'response-schema.json',legacy)
        self.bind()
        self.workflow['schema_sha256']=H(legacy)
        self.config['workflow_sha256']=self.put(self.target/'registered-workflow.json',self.workflow)['sha256']
        self.put(self.target/'operator-control.json',self.config)
        publication=json.loads((self.operator/'preparation-complete-v1.json').read_bytes())
        publication['operator_source']=dict(bytes=len((self.operator/'root-delegation-v1.json').read_bytes()),sha256=H((self.operator/'root-delegation-v1.json').read_bytes()))
        publication['prepared_input']=dict(bytes=len((self.operator/'prepared-inputs-v1.json').read_bytes()),sha256=H((self.operator/'prepared-inputs-v1.json').read_bytes()))
        for leaf in ('response-schema.json','registered-workflow.json','operator-control.json'):
            raw=(self.target/leaf).read_bytes();publication['files'][leaf]=dict(bytes=len(raw),sha256=H(raw))
        self.put(self.operator/'preparation-complete-v1.json',publication)
        with sqlite3.connect(self.journal) as con:
            permit=json.loads(con.execute("SELECT payload FROM codex_conducted_workflow_history WHERE kind='permit'").fetchone()[0])
            permit['workflow_sha256']=self.config['workflow_sha256']
            con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='permit'",(C(permit).decode(),))
        reserved=dict(permit_id='REG-P1',context_sha256=self.workflow['context_sha256'],workflow_sha256=self.config['workflow_sha256'],
            plan_input_sha256=self.workflow['plan_input_sha256'],requested_model='gpt-6-astra',maximum_model_processes=8)
        self.put(self.target/'workflow-claimed.json',reserved)
        wire=C(dict(type='error',message='HTTP 400 invalid response schema oneOf rejected'))+b'\n'
        folder=self.evidence/'loop/calls/0001/producer';folder.mkdir(parents=True)
        self.put(folder/'stdout.jsonl',wire)
        receipt=producer._receipt('gpt-6-astra',60,'AUTHORED-FAILED-ORIGINAL',dict(kind='model',name='AUTHORED-ORIGINAL'))
        receipt['failure']=dict(code='codex_cli_response_stream_invalid',phase='collect')
        receipt['bindings'].update(prompt_sha256=H(b'AUTHORED-ORIGINAL-PROMPT'),schema_sha256=H(legacy))
        receipt['lifecycle'].update(model_process_started=True,agent_messages=0,tool_items=0)
        receipt['attempts'].update(model_process_attempts=1)
        receipt['cleanup'].update(version_child_reaped=True,model_child_reaped=True,readers_joined=True,pipes_closed=True,artifacts_closed=True)
        receipt['artifacts']['stdout_jsonl'].update(present=True,complete=True,overflow=False,bytes=len(wire),sha256=H(wire))
        receipt_pin=self.put(folder/'receipt.json',receipt)
        step=dict(index=1,producer=dict(receipt=receipt,receipt_sha256=H(C(receipt))),
            artifacts=dict(prompt=dict(sha256=H(b'AUTHORED-ORIGINAL-PROMPT'))),wire=None,
            dispatch=dict(intent_seen=False,request_id=None,operation=None,reserved_logical_requests=0,confirmed_receipts=0,
                runtime_call_attempts=0,receipt_status=None,effect='not_applicable'))
        failure=dict(code='codex_cli_response_stream_invalid',stage='producer')
        execution=dict(status='failed',failure=failure,binding=dict(self.plan['binding'],plan_input_sha256=H(C(self.plan)),
            run_id='AUTHORED-ORIGINAL-RUN',runtime_instance_id='AUTHORED-ORIGINAL-RUNTIME'),
            loop=dict(budget=dict(producer_calls_started=1,elapsed_seconds=12.25),steps=[step],
                cleanup=dict(host_artifacts_closed=True,runtime_references_released=True),declaration=dict(schema_sha256=H(legacy))))
        execution_pin=self.put(self.evidence/'execution-receipt.json',execution)
        finalizer_pin=self.put(self.evidence/'finalizer-receipt.json',dict(status='held',failure=failure))
        self.finished=dict(permit_id='REG-P1',status='failed',local_model_processes=1,cleanup_confirmed=True,execution_receipt=execution_pin,
            finalizer_receipt=finalizer_pin,producer_receipts=[dict(index=1,**receipt_pin)],errors=[dict(phase='execution',code='codex_cli_response_stream_invalid')])
        with sqlite3.connect(self.journal) as con:
            for kind,value in [('reserved',reserved),('consumed',dict(permit_id='REG-P1',reservation_sha256=H(C(reserved)))),('finished',self.finished)]:
                con.execute('INSERT INTO codex_conducted_workflow_history(kind,permit_id,payload) VALUES(?,?,?)',(kind,'REG-P1',C(value).decode()))
        from labflow.virtual_fleet.operator_response_schema import CURRENT_SCHEMA_SHA256
        pin=lambda p:dict(bytes=len(p.read_bytes()),sha256=H(p.read_bytes()))
        self.manual=dict(schema_version=1,kind='codex_root_same_case_manual_continuation',authority_source=self.authority['authority_source'],
            manual_continuation_reference='AUTHORED_FIXTURE_ROOT_INTERPRETATION_NOT_DIRECT_USER_WORDS',interpretation=api._INTERPRETATION,
            action='continue_same_registered_synthetic_workflow_once',original_operator_source=pin(self.operator/'root-delegation-v1.json'),
            original_publication=pin(self.operator/'preparation-complete-v1.json'),scope=self.authority['scope'],current_schema_sha256=CURRENT_SCHEMA_SHA256,
            remaining_model_processes=7,expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            original=dict(journal_id=self.config['journal_id'],permit_id=self.config['permit_id'],workflow_sha256=self.config['workflow_sha256'],
                registration_sha256=self.config['registration_sha256'],finished_sha256=H(C(self.finished)),execution_receipt=execution_pin,
                finalizer_receipt=finalizer_pin,producer_receipts=self.finished['producer_receipts']),
            case=dict(scenario_id='REG-CASE',requested_model='gpt-6-astra',context_sha256=self.workflow['context_sha256'],analysis_sha256=self.workflow['analysis_sha256'],
                plan_input_sha256=self.workflow['plan_input_sha256'],source_settings_sha256=H(C(self.workflow['source_settings'])),catalog_sha256=self.workflow['catalog_sha256']))
        self.put(self.operator/api._RECORD,self.manual)

    def attempt(self):
        return api.continue_registered_workflow(scenario_id='REG-CASE',requested_model='gpt-6-astra')

    def test_bound_manual_record_reaches_lowered_execution_and_partial_claim_blocks(self):
        self.fixture()
        original={p:p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
        # This is a deliberate execution error seam, not fake dependency success.
        with patch.object(host,'_execute',side_effect=RuntimeError('AUTHORED_EXECUTION_ENTRY_STOP')) as execute:
            result=self.attempt()
        self.assertEqual(execute.call_count,1,result)
        self.assertEqual(result['status'],'unknown',result)
        self.assertEqual(execute.call_args.kwargs['model_process_limit'],7)
        self.assertLess(execute.call_args.kwargs['wall_seconds_limit'],167.75)
        self.assertGreater(execute.call_args.kwargs['evidence_reservation']['files'],0)
        self.assertTrue((self.evidence/api._NAMESPACE/'claim-v1.json').is_file())
        self.assertTrue(all(p.read_bytes()==raw for p,raw in original.items()))
        with patch.object(host,'_execute',side_effect=AssertionError('SECOND_CONTINUATION_FORBIDDEN')) as execute:
            again=self.attempt()
        self.assertEqual(again['status'],'not_run');self.assertEqual(execute.call_count,0)
        self.assertTrue(again['errors'][0]['code'].endswith('already_claimed'))

    def test_manual_scope_case_and_expiry_drift_cannot_enter(self):
        self.fixture();original=copy.deepcopy(self.manual)
        changes=[dict(remaining_model_processes=8),dict(remaining_model_processes=True),dict(current_schema_sha256='0'*64),
            dict(expires_at='2020-01-01T00:00:00Z'),dict(interpretation='user_said_continuation'),dict(scope=dict(self.manual['scope'],maximum_workflows=2)),
            dict(case=dict(self.manual['case'],plan_input_sha256='0'*64)),dict(original=dict(self.manual['original'],finished_sha256='0'*64))]
        with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
            for change in changes:
                with self.subTest(change=change):
                    self.manual=copy.deepcopy(original);self.manual.update(change);self.put(self.operator/api._RECORD,self.manual)
                    result=self.attempt();self.assertEqual(result['status'],'not_run',result)
                    self.assertFalse((self.evidence/api._NAMESPACE).exists())
        self.assertEqual(execute.call_count,0)

    def test_original_ledger_states_unknown_count_and_cleanup_cannot_enter(self):
        self.fixture();original=copy.deepcopy(self.finished)
        changes=[dict(status='completed'),dict(status='unknown'),dict(local_model_processes=None),
            dict(local_model_processes=0),dict(local_model_processes=True),dict(cleanup_confirmed=False)]
        with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
            for change in changes:
                changed=copy.deepcopy(original);changed.update(change)
                with sqlite3.connect(self.journal) as con:
                    con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='finished'",(C(changed).decode(),))
                result=self.attempt();self.assertEqual(result['status'],'not_run',result)
                self.assertFalse((self.evidence/api._NAMESPACE).exists())
        self.assertEqual(execute.call_count,0)

    def test_original_partial_or_missing_ledger_and_source_drift_cannot_enter(self):
        self.fixture();raw=self.original.read_bytes();self.original.write_bytes(raw+b'changed')
        with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
            result=self.attempt();self.assertEqual(result['status'],'not_run',result)
            self.original.write_bytes(raw)
            with sqlite3.connect(self.journal) as con:con.execute("DELETE FROM codex_conducted_workflow_history WHERE kind='finished'")
            result=self.attempt();self.assertEqual(result['status'],'not_run',result)
        self.assertEqual(execute.call_count,0);self.assertFalse((self.evidence/api._NAMESPACE).exists())

    def test_new_initial_registration_rejects_legacy_schema_before_staging(self):
        current=(self.data/'response-schema.json').read_bytes()
        legacy=current.replace(b'"anyOf"',b'"oneOf"')
        self.meta['files']['response-schema.json']=self.put(self.data/'response-schema.json',legacy);self.bind()
        result=registrar.prepare_registered_conducted_workflow(scenario_id='REG-CASE',requested_model='gpt-6-astra')
        self.assertEqual(result['status'],'not_prepared',result)
        self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())
        self.assertTrue(result['errors'][0]['code'].endswith('unsupported_schema'))

    def test_missing_namespace_with_existing_claim_or_partial_namespace_is_terminal(self):
        self.fixture();self.put(self.evidence/api._CLAIM,b'AUTHORED_PARTIAL_CLAIM_COUNTER')
        with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
            result=self.attempt();self.assertEqual(result['status'],'not_run',result)
        self.assertEqual(execute.call_count,0);self.assertFalse((self.evidence/api._NAMESPACE).exists())

    def test_original_zero_effect_failure_gate_rejects_agent_tools_and_unknown_elapsed(self):
        self.fixture()
        execution_path=self.evidence/'execution-receipt.json';producer_path=self.evidence/'loop/calls/0001/producer/receipt.json'
        base=json.loads(execution_path.read_bytes());manual=copy.deepcopy(self.manual);finished=copy.deepcopy(self.finished)
        for kind in ('agent','dispatch','elapsed','other_error'):
            changed=copy.deepcopy(base);receipt=changed['loop']['steps'][0]['producer']['receipt']
            if kind=='agent':receipt['lifecycle']['agent_messages']=1
            elif kind=='dispatch':changed['loop']['steps'][0]['dispatch']['intent_seen']=True
            elif kind=='elapsed':changed['loop']['budget']['elapsed_seconds']=None
            else:changed['failure']=dict(code='codex_cli_response_process_failed',stage='producer')
            receipt_pin=self.put(producer_path,receipt)
            changed['loop']['steps'][0]['producer']['receipt_sha256']=H(C(receipt))
            row=copy.deepcopy(finished);row['producer_receipts']=[dict(index=1,**receipt_pin)]
            row['execution_receipt']=self.put(execution_path,changed)
            with sqlite3.connect(self.journal) as con:con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='finished'",(C(row).decode(),))
            value=copy.deepcopy(manual);value['original'].update(finished_sha256=H(C(row)),execution_receipt=row['execution_receipt'],producer_receipts=row['producer_receipts'])
            self.put(self.operator/api._RECORD,value)
            with patch.object(host,'_execute',side_effect=AssertionError('EXECUTION_FORBIDDEN')) as execute:
                result=self.attempt();self.assertEqual(result['status'],'not_run',result)
            self.assertEqual(execute.call_count,0);self.assertFalse((self.evidence/api._NAMESPACE).exists())

    def test_genuine_lowered_same_profile_mock_continuation_once(self):
        self.fixture()
        from test_codex_registered_conducted_workflow_host import CHILD
        script=self.root/'authored-child.py';script.write_text(CHILD,encoding='utf-8')
        originals={p:p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
        children=[];argvs=[]
        def spawn(argv,**options):
            argvs.append(list(argv));stage='version' if argv[1:]==['--version'] else 'model'
            last=Path(argv[argv.index('--output-last-message')+1]) if stage=='model' else None
            if last:BUDGET.charge(last,2097153)
            child=REAL_POPEN([sys.executable,'-B','-u',str(script),'normal',stage,str(last) if last else '-'],**options)
            children.append(child);return child
        with patch('labflow.codex_cli_response.subprocess.Popen',side_effect=spawn):result=self.attempt()
        for child in children:
            self.assertIsNotNone(child.poll());child.wait(timeout=3)
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(result['history']['original_model_processes'],1)
        self.assertEqual(result['history']['continuation_model_processes'],5)
        self.assertEqual(result['history']['known_total_model_processes'],23)
        self.assertFalse(result['history']['usage_complete']);self.assertIsNone(result['history']['cost'])
        self.assertEqual(len([a for a in argvs if a[1:]!=['--version']]),5)
        target=self.evidence/api._NAMESPACE
        execution=json.loads((target/'execution-receipt.json').read_bytes())
        self.assertEqual(execution['loop']['budget']['limits']['model_calls'],7)
        self.assertLess(execution['loop']['budget']['limits']['wall_seconds'],167.75)
        self.assertEqual(execution['loop']['budget']['application_retries'],0)
        self.assertNotEqual(result['execution']['runtime_instance_id'],'AUTHORED-ORIGINAL-RUNTIME')
        self.assertTrue(all(p.read_bytes()==raw for p,raw in originals.items()))
        finished=json.loads((target/'finished-v1.json').read_bytes())
        self.assertEqual(finished['current_valid_result'],'continuation');self.assertTrue(finished['original_failure_preserved'])
        self.assertTrue((target/'current-handoff.json').is_file())
        self.assertEqual(self.attempt()['status'],'not_run')

    def test_unknown_or_missing_authority_never_creates_state(self):
        before={p:p.read_bytes() for p in self.parent.rglob('*') if p.is_file()}
        result=api.continue_registered_workflow(scenario_id='REG-CASE',requested_model='gpt-6-astra')
        self.assertEqual(result['status'],'not_run')
        self.assertEqual(result['verification']['dispatch'],'not_invoked')
        self.assertEqual(before,{p:p.read_bytes() for p in self.parent.rglob('*') if p.is_file()})

    def test_budget_deducts_original_one_and_elapsed(self):
        result=api._remaining_budget(1,12.25,40,1024)
        self.assertEqual(result['model_process_limit'],7)
        self.assertEqual(result['wall_seconds_limit'],167.75)
        self.assertEqual(result['known_total_before_continuation'],18)
        self.assertLessEqual(result['maximum_known_total'],25)
        self.assertGreaterEqual(result['evidence_reservation']['files'],40+12)
        self.assertGreaterEqual(result['evidence_reservation']['bytes'],1024+5505024)

    def test_unknown_overbudget_and_zero_seed_are_closed(self):
        for count,elapsed,files,size in [(None,1,0,0),(0,1,0,0),(2,1,0,0),(True,1,0,0),
                (1,None,0,0),(1,float('nan'),0,0),(1,float('inf'),0,0),(1,-1,0,0),(1,180,0,0),
                (1,1,192,0),(1,1,0,33554432),(1,1,True,0)]:
            with self.subTest(values=(count,elapsed,files,size)):
                with self.assertRaises(api._Failure):api._remaining_budget(count,elapsed,files,size)

    def test_arguments_cannot_pass_authority_profile_or_output(self):
        for extra in (['--approval','true'],['--profile',str(self.target)],['--output',str(self.root/'new')]):
            self.assertEqual(api.main(['--scenario-id','REG-CASE',*extra]),2)


NAMES=['test_unknown_or_missing_authority_never_creates_state','test_budget_deducts_original_one_and_elapsed',
       'test_unknown_overbudget_and_zero_seed_are_closed','test_arguments_cannot_pass_authority_profile_or_output',
       'test_bound_manual_record_reaches_lowered_execution_and_partial_claim_blocks','test_manual_scope_case_and_expiry_drift_cannot_enter',
       'test_original_ledger_states_unknown_count_and_cleanup_cannot_enter','test_original_partial_or_missing_ledger_and_source_drift_cannot_enter',
       'test_new_initial_registration_rejects_legacy_schema_before_staging',
       'test_missing_namespace_with_existing_claim_or_partial_namespace_is_terminal','test_original_zero_effect_failure_gate_rejects_agent_tools_and_unknown_elapsed',
       'test_genuine_lowered_same_profile_mock_continuation_once']

def load_tests(loader,tests,pattern):
    return unittest.TestSuite(ContinuationTests(name) for name in SELECTED)

SELECTED=NAMES
if __name__=='__main__':
    if '--guards' in sys.argv:
        sys.argv.remove('--guards');SELECTED=NAMES[:-1]
    unittest.main()
