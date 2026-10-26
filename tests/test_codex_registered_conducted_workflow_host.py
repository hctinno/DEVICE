"""Separate authored native profile; installed CLI/auth/operating ledger access0."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import uuid
from contextlib import contextmanager

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import prepare_registered_synthetic_context
from labflow.intake_model_boundary import decode_analysis_response
from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.store import Store, canonical
try:
    api=importlib.import_module('labflow.codex_registered_conducted_workflow_host')
except ModuleNotFoundError as error:
    if error.name!='labflow.codex_registered_conducted_workflow_host':raise
    api=None

LOCAL=ROOT/'.local/wfh'/uuid.uuid4().hex
REAL_POPEN=subprocess.Popen
C=lambda v:canonical(v).encode('utf-8')
H=lambda v:hashlib.sha256(v).hexdigest()
SQL='CREATE TABLE codex_conducted_workflow_history(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, permit_id TEXT, payload TEXT NOT NULL, UNIQUE(kind,permit_id))'
CHILD=r'''
import sys,json,os
from pathlib import Path
def deny(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):raise AssertionError('NO_NETWORK')
sys.addaudithook(deny)
mode,stage,last=sys.argv[1:]
if stage=='version':
 os.write(1,b'wrong\n' if mode=='bad_version' else b'codex-cli 0.163.0-alpha.11.2\n');sys.exit(0)
data=sys.stdin.buffer.read();p=json.loads(data)
assert data==(Path.cwd().parent/'request.json').read_bytes()
context=json.loads(p['messages'][1]['content'])['request']['user_input']['public_context']
obs,goal=context['observations'],context['goal'];dut=obs['devices'][goal['dut_id']];sensor=obs['devices'][goal['sensor_id']]
m=sensor['values'].get('outputs',{}).get('measurement',{})
state=dut['values'].get('state',dut.get('state'));s=sensor['values'].get('state',sensor.get('state'))
if m.get('valid') is True and m.get('acquisition_tick',-1)>=goal['minimum_acquisition_tick'] and m.get('acquisition_setup_revision')==obs['setup_revision']:
 proposal=dict(kind='stop',claim='completed',reason='scripted public fresh observation')
elif state=='idle':proposal=dict(kind='execute',device_id=goal['dut_id'],action='start',parameters={})
elif state in ('arming','settling') or s in ('measuring','acquiring','pending','running'):proposal=dict(kind='advance',ticks=1)
else:proposal=dict(kind='execute',device_id=goal['sensor_id'],action='acquire',parameters={})
wire=json.dumps(dict(schema_version=1,kind='virtual_operator_response',request_sha256=p['binding']['request_sha256'],producer=p['expected_producer'],proposal=proposal),sort_keys=True,separators=(',',':')).encode()
assert len(wire)<4096;Path(last).write_bytes(wire)
events=[dict(type='thread.started',thread_id='mock-native-workflow'),dict(type='turn.started'),dict(type='item.completed',item=dict(id='a1',type='agent_message',text=wire.decode())),dict(type='turn.completed',usage=dict(input_tokens=10,output_tokens=3))]
os.write(1,b''.join(json.dumps(x,separators=(',',':')).encode()+b'\n' for x in events));sys.exit(7 if mode=='nonzero' else 0)
'''


class Budget:
    def __init__(self):self.files={};self.total=0;self.groups={};self.native_slots=0
    def charge(self,path,size):
        path=Path(os.path.abspath(path));assert path.is_relative_to(LOCAL)
        before=self.files.get(path,0);delta=max(0,size-before)
        assert self.total+delta<=33554432 and len(self.files)+self.native_slots+(path not in self.files)<=512,'PROOF_CAP'
        self.files[path]=max(size,before);self.total+=delta
    def reserve_group(self,key,size):
        assert self.total+size<=33554432 and len(self.files)+self.native_slots+16<=512,'NATIVE_PROOF_CAP'
        self.total+=size;self.groups[key]=size;self.native_slots+=16
    def settle_group(self,key,root):
        # One cold, bounded verification of this completed fixture, never hot-write admission.
        self.total-=self.groups.pop(key);self.native_slots-=16
        for path in root.rglob('*'):
            if path.is_file():self.charge(path,path.stat().st_size)
    def settle(self,path):
        old=self.files.pop(path,0);self.total-=old
        if path.exists() and path.is_file():self.charge(path,path.stat().st_size)


BUDGET=Budget()
class Writer:
    def __init__(self,stream,path):self.stream,self.path=stream,path
    def write(self,data):
        size=len(data.encode('utf-8'))*2 if type(data) is str else len(data)
        BUDGET.charge(self.path,self.stream.tell()+size)
        return self.stream.write(data)
    def __getattr__(self,key):return getattr(self.stream,key)
    def __enter__(self):return self
    def __exit__(self,*args):return self.stream.__exit__(*args)


class WorkflowHostTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned registered workflow host API is absent')
        self.folder=LOCAL/uuid.uuid4().hex[:8];self.folder.mkdir(parents=True)
        self.native_group=str(self.folder);BUDGET.reserve_group(self.native_group,2097152)
        self.addCleanup(lambda:BUDGET.settle_group(self.native_group,self.folder))
        opened=Path.open
        def bounded(path,mode='r',*args,**kwargs):
            if any(c in mode for c in 'wax+'):
                BUDGET.charge(path,path.stat().st_size if path.exists() else 0)
                return Writer(opened(path,mode,*args,**kwargs),path)
            return opened(path,mode,*args,**kwargs)
        self.enterContext(patch.object(Path,'open',bounded))
        (self.folder/'test-case.txt').write_text(self._testMethodName,encoding='utf-8')
        for target in ('socket.socket.connect','socket.getaddrinfo'):
            self.enterContext(patch(target,side_effect=AssertionError('OPERATING_NETWORK_FORBIDDEN')))
        self.profile=self.folder/'p';self.profile.mkdir();self.evidence=self.profile/'runs/P1';self.evidence.mkdir(parents=True)
        self.enterContext(patch.object(api,'_profile_root',return_value=self.profile))
        self.mode='normal';self.children=[];self.argv=[];self.cancel_after_model=False
        self.addCleanup(self.reap)
        self.make_profile()
        self.enterContext(patch('labflow.codex_cli_response.subprocess.Popen',side_effect=self.spawn))

    def put(self,leaf,value):
        raw=value if type(value) is bytes else C(value)
        (self.profile/leaf).write_bytes(raw);return H(raw)

    def make_profile(self):
        inbox=self.folder/'i';bundle=inbox/'case';bundle.mkdir(parents=True)
        lines=['product_type: smartphone','model: SM-A176U','market: US','purpose: synthetic conducted engineering',
               'frequency: 2412 MHz; bandwidth: 20 MHz; on_average_power: 11 dBm; duty_cycle: 50 %; modulation: OFDM; crest_factor: 4 dB']
        (bundle/'r.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
        self.store_root=self.folder/'s';store=Store(self.store_root)
        try:
            register_source(store,'WFH-SYN',inbox,synthetic=True,settle_seconds=1)
            scan_source(store,'WFH-SYN',now=100,synthetic_only=True)
            item=scan_source(store,'WFH-SYN',now=101,synthetic_only=True)['accepted'][0]
            with store.connection() as con:
                revision=con.execute('SELECT * FROM intake_revisions WHERE intake_id=?',(item['intake_id'],)).fetchone()
            selection=dict(source_id='WFH-SYN',intake_id=item['intake_id'],revision=item['revision'],job_id=item['job_id'],
                revision_fingerprint=revision['fingerprint'],files=json.loads(revision['files_json']))
            self.context=prepare_registered_synthetic_context(store,selection,producer_name='SCRIPTED-WFH-MOCK')
            doc=self.context['documents'][0]
            def fact(field,value,line):
                return dict(field=field,value=value,status='explicit',evidence=[dict(path=doc['path'],sha256=doc['sha256'],line_start=line,line_end=line,quote=lines[line-1],role='request')])
            raw=dict(schema_version=1,producer=dict(kind='model',name='SCRIPTED-WFH-MOCK'),identity='single',missing_fields=[],facts=[
                fact('product_type','smartphone',1),fact('model','SM-A176U',2),fact('market','US',3),fact('purpose','synthetic conducted engineering',4),fact('features',lines[4],5)])
            self.analysis=decode_analysis_response(C(raw),self.context,producer_name='SCRIPTED-WFH-MOCK')
            assembled=build_conducted_plan_from_intake_facts(self.context,self.analysis,expected_revision=1,expected_context_sha256=H(C(self.context)),
                method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
            self.plan=assembled['plan_input'];self.assertEqual(assembled['status'],'ready_for_simulation')
        finally:store.close()
        anchor=dict(schema_version=1,kind='codex_conducted_workflow_root_anchor',inherited_history=dict(
            actual_codex_model_processes=17,known_total_before_this_host=17,unknown_usage_components=None,usage_complete=False,cost=None,
            provenance_level='previous_verified_root_rollup_not_fresh_original_receipt_reaudit',
            source_rollup=dict(path='AUTHORED_FIXTURE_NOT_OPERATING_HISTORY',bytes=1,sha256=H(b'fixture')),
            published_source=dict(commit='9fe7e5a41c6f427a77f9592a690e9c027073b9c4',path='fixture-only',bytes=1,sha256=H(b'fixture'))))
        anchor_sha=self.put('root-continuation-anchor.json',anchor)
        manifest=dict(schema_version=1,kind='codex_registered_synthetic_intake',scenario_id='WFH-CASE',synthetic=True,registered_intake=selection)
        registration_sha=self.put('registered-intake-v1.json',manifest)
        analysis_sha=self.put('analysis.json',self.analysis);plan_sha=self.put('plan-input.json',self.plan)
        catalog=(ROOT/'virtual_profiles/sm_a176u_unlicensed.json').read_bytes()
        catalog_sha=self.put('catalog.json',catalog)
        schema=json.loads((ROOT/'docs/fcc/codex_first_decision_contract.json').read_text(encoding='utf-8'))['response_schema']['literal_utf8'].encode()
        self.assertEqual(len(schema),3052);schema_sha=self.put('response-schema.json',schema)
        workflow=dict(schema_version=1,kind='codex_registered_conducted_workflow',scenario_id='WFH-CASE',context_sha256=H(C(self.context)),
            analysis_sha256=analysis_sha,plan_input_sha256=plan_sha,source_settings=self.plan['plan']['source_settings'],
            quantity=dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=1),
            allowed_tools=['dut.start','sensor.acquire','sensor.read','advance1','stop'],measurement_ref='event:17',catalog_sha256=catalog_sha,schema_sha256=schema_sha)
        workflow_sha=self.put('registered-workflow.json',workflow)
        self.put('cancel-request.json',dict(requested=False))
        exe=self.folder/'codex.exe';exe.write_bytes(b'EXPLICIT_KNOWN_PYTHON_MOCK_ONLY')
        self.script=self.folder/'child.py';self.script.write_text(CHILD,encoding='utf-8')
        self.config=dict(schema_version=1,kind='codex_registered_conducted_workflow_control',anchor_sha256=anchor_sha,journal_id='WFH-JOURNAL',permit_id='P1',
            registration_sha256=registration_sha,workflow_sha256=workflow_sha,registered_input_root=str(bundle),store_root=str(self.store_root),executable=str(exe))
        self.put('operator-control.json',self.config)
        self.journal=self.profile/'workflow-continuation.sqlite3'
        self.permit=dict(schema_version=1,kind='codex_conducted_workflow_single_use_permit',journal_id='WFH-JOURNAL',permit_id='P1',anchor_sha256=anchor_sha,
            workflow_sha256=workflow_sha,registration_sha256=registration_sha,requested_model='gpt-6-astra',
            expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        with sqlite3.connect(self.journal) as con:
            con.execute(SQL)
            baseline=dict(schema_version=1,kind='codex_conducted_workflow_continuation_baseline',journal_id='WFH-JOURNAL',anchor_sha256=anchor_sha,inherited_history=anchor['inherited_history'])
            for kind,permit,payload in [('baseline',None,baseline),('permit','P1',self.permit)]:
                con.execute('INSERT INTO codex_conducted_workflow_history(kind,permit_id,payload) VALUES(?,?,?)',(kind,permit,C(payload).decode()))

    def spawn(self,argv,**options):
        self.argv.append(list(argv));stage='version' if argv[1:]==['--version'] else 'model'
        self.assertFalse(options['shell'])
        last=Path(argv[argv.index('--output-last-message')+1]) if stage=='model' else None
        if last:BUDGET.charge(last,2097153)
        child=REAL_POPEN([sys.executable,'-B','-u',str(self.script),self.mode,stage,str(last) if last else '-'],**options)
        self.children.append(child)
        owner=self
        class Child:
            settled=False
            def settle(self):
                if not self.settled:
                    self.settled=True
                    if last:BUDGET.settle(last)
                    if last and owner.cancel_after_model:
                        owner.put('cancel-request.json',dict(requested=True))
                        # A fixture scheduling barrier allows the native watcher
                        # to observe the operator flag before the next stage.
                        time.sleep(.1)
            def poll(self):
                result=child.poll()
                if result is not None:self.settle()
                return result
            def wait(self,*args,**kwargs):
                result=child.wait(*args,**kwargs);self.settle();return result
            def __getattr__(self,key):return getattr(child,key)
        return Child()

    def reap(self):
        for child in self.children:
            if child.poll() is None:child.kill();self.fail('Known child left running')
            child.wait(timeout=3)

    def call(self,model='gpt-6-astra',args=None):
        out,err=io.StringIO(),io.StringIO()
        with patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):
            code=api.main(args if args is not None else ['--scenario-id','WFH-CASE','--model',model])
        text=out.getvalue() or err.getvalue()
        (self.folder/('frame-'+str(len(self.argv))+'-'+uuid.uuid4().hex[:4]+'.json')).write_text(text,encoding='utf-8')
        return code,json.loads(text)

    def rows(self):
        with sqlite3.connect(self.journal) as con:
            return [(row[0],json.loads(row[1])) for row in con.execute('SELECT kind,payload FROM codex_conducted_workflow_history ORDER BY seq')]

    def test_missing_profile_does_not_create_or_dispatch(self):
        with patch.object(api,'_profile_root',return_value=self.folder/'absent'):
            code,result=self.call()
        self.assertEqual(code,3);self.assertEqual(result['status'],'not_run');self.assertEqual(self.argv,[])
        self.assertFalse((self.folder/'absent').exists());self.assertEqual(len(self.rows()),2)

    def test_argument_dict_or_path_cannot_be_an_authority(self):
        for extra in (['--approval','true'],['--profile',str(self.profile)],['--model','gpt-6-luna']):
            code,_=self.call(args=['--scenario-id','WFH-CASE',*extra]);self.assertEqual(code,2)
        self.assertEqual(self.argv,[]);self.assertEqual(len(self.rows()),2)

    def test_genuine_astra_same_runtime_and_finalizer_consumption(self):
        code,result=self.call();self.assertEqual((code,result['status']),(0,'completed'))
        self.assertEqual([k for k,v in self.rows()],['baseline','permit','reserved','consumed','finished'])
        self.assertEqual(result['history']['inherited_model_processes'],17)
        self.assertEqual(result['history']['local_model_processes'],5)
        self.assertEqual(result['history']['known_total_model_processes'],22)
        self.assertIsNone(result['history']['cost']);self.assertFalse(result['history']['usage_complete'])
        self.assertEqual(result['finalization']['artifact']['storage']['status'],'complete')
        execution=json.loads((self.evidence/'execution-receipt.json').read_bytes())
        ids={row['binding']['runtime_instance_id'] for row in execution['loop']['steps']}
        self.assertEqual(ids,{execution['binding']['runtime_instance_id']})
        self.assertEqual(execution['loop']['budget']['limits']['model_calls'],8)
        self.assertEqual(execution['loop']['budget']['application_retries'],0)
        for argv in self.argv:
            if '--model' in argv:self.assertEqual(argv[argv.index('--model')+1],'gpt-6-astra')
        self.assertTrue((self.profile/'workflow-claimed.json').is_file())
        before=self.rows();calls=len(self.argv);code,result=self.call()
        self.assertEqual(code,3);self.assertEqual(self.rows(),before);self.assertEqual(len(self.argv),calls)

    def test_model_mismatch_and_expired_permit_are_not_consumed(self):
        code,result=self.call(model='gpt-6.1-sol');self.assertEqual(code,3);self.assertEqual(self.argv,[])
        self.permit['expires_at']='2020-01-01T00:00:00Z'
        with sqlite3.connect(self.journal) as con:con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='permit'",(C(self.permit).decode(),))
        code,result=self.call();self.assertEqual(code,3);self.assertEqual(len(self.rows()),2)

    def test_native_scope_and_source_hash_tampering_cannot_dispatch(self):
        original=(self.profile/'registered-workflow.json').read_bytes()
        self.put('registered-workflow.json',original+b' ')
        code,_=self.call();self.assertEqual(code,3)
        self.put('registered-workflow.json',original)
        (Path(self.config['registered_input_root'])/'extra.txt').write_text('UNREGISTERED',encoding='utf-8')
        code,_=self.call();self.assertEqual(code,3);self.assertEqual(self.argv,[])

    def test_intake_ledger_and_zero_seed_are_not_accepted(self):
        original=(self.profile/'root-continuation-anchor.json').read_bytes()
        changed=json.loads(original);changed['inherited_history']['actual_codex_model_processes']=0
        self.config['anchor_sha256']=self.put('root-continuation-anchor.json',changed);self.put('operator-control.json',self.config)
        code,_=self.call();self.assertEqual(code,3);self.assertEqual(self.argv,[])
        self.config['anchor_sha256']=self.put('root-continuation-anchor.json',original);self.put('operator-control.json',self.config)
        with sqlite3.connect(self.journal) as con:
            con.execute('ALTER TABLE codex_conducted_workflow_history RENAME TO codex_intake_history')
        code,_=self.call();self.assertEqual(code,3);self.assertEqual(self.argv,[])

    def test_invalid_quantity_or_limits_do_not_gain_an_extra_approval(self):
        workflow=json.loads((self.profile/'registered-workflow.json').read_bytes())
        workflow['quantity']['loss_compensation_sign']=True
        self.config['workflow_sha256']=self.put('registered-workflow.json',workflow);self.put('operator-control.json',self.config)
        code,_=self.call();self.assertEqual(code,3);self.assertEqual(self.argv,[])

    def test_pre_requested_cancel_leaves_permit_unused(self):
        self.put('cancel-request.json',dict(requested=True))
        code,result=self.call();self.assertEqual(code,3);self.assertEqual(self.argv,[]);self.assertEqual(len(self.rows()),2)

    def test_version_rejection_has_consumed_permit_but_model_zero(self):
        self.mode='bad_version';code,result=self.call()
        self.assertIn(code,(4,5));self.assertEqual(self.rows()[3][0],'consumed')
        self.assertEqual(result['history']['local_model_processes'],0)
        self.assertTrue(all(argv[1:]==['--version'] for argv in self.argv))

    def test_nonzero_sol_process_is_retained_and_not_retried(self):
        self.mode='nonzero';self.permit['requested_model']='gpt-6.1-sol'
        with sqlite3.connect(self.journal) as con:con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='permit'",(C(self.permit).decode(),))
        code,result=self.call(model='gpt-6.1-sol');self.assertIn(code,(4,5))
        self.assertEqual(result['history']['local_model_processes'],1)
        self.assertEqual(len([a for a in self.argv if '--model' in a]),1)
        self.assertTrue((self.evidence/'loop/calls/0001/producer/stdout.jsonl').is_file())

    def test_cancel_after_first_process_stops_without_refund(self):
        self.cancel_after_model=True;code,result=self.call();self.assertIn(code,(4,5))
        self.assertEqual(result['history']['local_model_processes'],1)
        self.assertEqual(len([a for a in self.argv if '--model' in a]),1)
        self.assertEqual(self.rows()[3][0],'consumed')

    def test_control_identity_and_unknown_consumption(self):
        control=MemoryError('ORIGINAL_CONTROL')
        with patch.object(api,'_execute',side_effect=control):
            with self.assertRaises(MemoryError) as got:self.call()
        self.assertIs(got.exception,control)
        rows=self.rows();self.assertEqual(rows[3][0],'consumed');self.assertEqual(rows[-1][1]['status'],'unknown')
        self.assertIsNone(rows[-1][1]['local_model_processes'])

    def test_unknown_execution_dto_is_not_a_zero_model_count(self):
        with patch.object(api,'_execute',return_value={}):
            code,result=self.call()
        self.assertEqual(code,5);self.assertIsNone(result['history']['local_model_processes'])
        self.assertEqual(self.rows()[-1][1]['status'],'unknown')

    def test_ledger_close_failure_preserves_claim_and_unknown(self):
        self.mode='bad_version'
        original=api._close_ledger
        def closed(con):original(con);raise OSError('PRIVATE_CLOSE_TEXT')
        with patch.object(api,'_close_ledger',side_effect=closed):code,result=self.call()
        self.assertEqual(code,5);self.assertNotIn('PRIVATE_CLOSE_TEXT',C(result).decode())
        self.assertEqual(result['history']['local_model_processes'],0)
        self.assertTrue((self.profile/'workflow-claimed.json').is_file())
        self.assertEqual(result['errors'][-1]['phase'],'ledger_close')

    def selection_bind_workflow(self,workflow):
        self.config['workflow_sha256']=self.put('registered-workflow.json',workflow)
        self.put('operator-control.json',self.config)
        self.permit['workflow_sha256']=self.config['workflow_sha256']
        con=sqlite3.connect(self.journal)
        try:
            con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='permit'",(C(self.permit).decode(),))
            con.commit()
        finally:con.close()

    def selection_v2(self):
        workflow=json.loads((self.profile/'registered-workflow.json').read_bytes())
        self.assertEqual(workflow['schema_version'],1)
        workflow.update(schema_version=2,measurement_ref=None,
            measurement_selection_policy=dict(schema_version=1,kind='unique_same_run_sensor_acquisition'))
        self.selection_bind_workflow(workflow)
        return workflow

    def selection_explicit_v2_prepares_exact13_without_dispatch(self):
        workflow=self.selection_v2();before=(self.journal.read_bytes(),(self.profile/'registered-workflow.json').read_bytes())
        owned=dict(store=None);prepared=None;rejected=None
        try:
            try:prepared=api._prepare(self.profile,self.config,'WFH-CASE',owned)
            except api._Failure as error:rejected=str(error)
        finally:
            if owned['store'] is not None:owned['store'].close()
        self.assertIsNone(rejected,'The explicit v2 workflow is rejected by the v1-only profile contract')
        self.assertEqual(C(prepared[0]),C(workflow));self.assertEqual(len(prepared[0]),13)
        self.assertEqual(C(prepared[3]),C(self.plan));self.assertEqual(self.argv,[])
        self.assertEqual(before,(self.journal.read_bytes(),(self.profile/'registered-workflow.json').read_bytes()))
        self.assertEqual(len(self.rows()),2);self.assertFalse((self.profile/'workflow-claimed.json').exists())
        (self.folder/'v2-preflight.json').write_bytes(C(dict(status='validated',workflow=prepared[0],runtime_started=False,model_started=False)))

    def selection_genuine_v2_mock5_preserves_selection_and_artifact_chain(self):
        workflow=self.selection_v2();before_workflow=C(workflow);calls=[];finalize=api._finalize
        def finalizing(execution,**options):
            calls.append(copy.deepcopy(options))
            return finalize(execution,**options)
        with patch.object(api,'_finalize',side_effect=finalizing):code,record=self.call()
        self.assertEqual((code,record['status']),(0,'completed'))
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['measurement_selection_policy'],workflow['measurement_selection_policy'])
        self.assertIsNone(calls[0]['measurement_ref'])
        finalized=json.loads((self.evidence/'finalizer-receipt.json').read_bytes())
        self.assertEqual(len(record),12);self.assertEqual(len(record['finalization']),5);self.assertEqual(len(finalized),12)
        selection=finalized['measurement_selection'];self.assertEqual(len(selection),9)
        self.assertEqual(selection['status'],'selected');self.assertEqual(selection['verification']['builder_calls'],1)
        self.assertEqual(selection['measurement_ref'],selection['candidate']['measurement_ref'])
        self.assertEqual(selection['request_id'],selection['candidate']['request_id'])
        self.assertEqual(C(selection['result']),C(finalized['result']))
        self.assertEqual(finalized['result']['status'],'recorded')
        self.assertEqual(finalized['result']['raw_measurement']['packet']['power_dbm'],-19.5)
        self.assertEqual(finalized['result']['calculation']['corrected']['value'],11.0)
        self.assertEqual(finalized['result']['calculation']['conformity']['status'],'not_assessed')
        self.assertFalse(finalized['execution_authority']);self.assertFalse(finalized['verification']['physical_verified'])
        for row in record['finalization']['artifact']['files']:
            raw=(self.evidence/row['path']).read_bytes();self.assertEqual((len(raw),H(raw)),(row['bytes'],row['sha256']))
        marker=self.evidence/record['finalization']['artifact']['storage']['commit_marker']
        self.assertEqual(H(marker.read_bytes()),record['finalization']['artifact']['storage']['sha256'])
        self.assertEqual([kind for kind,_ in self.rows()],['baseline','permit','reserved','consumed','finished'])
        self.assertEqual(record['history']['inherited_model_processes'],17)
        self.assertEqual(record['history']['local_model_processes'],5)
        self.assertEqual(len([argv for argv in self.argv if '--model' in argv]),5)
        self.assertEqual((self.profile/'registered-workflow.json').read_bytes(),before_workflow)
        execution=json.loads((self.evidence/'execution-receipt.json').read_bytes())
        self.assertEqual(execution['plan_input'],self.plan)
        self.assertEqual(execution['loop']['budget']['limits']['model_calls'],8)
        self.assertEqual(execution['loop']['budget']['application_retries'],0)
        self.assertEqual(record['finalization']['receipt'],dict(bytes=(self.evidence/'finalizer-receipt.json').stat().st_size,sha256=H((self.evidence/'finalizer-receipt.json').read_bytes())))
        (self.folder/'selected-chain-observation.json').write_bytes(C(dict(mock_model_processes=5,actual_model_processes=0,selection=selection,
            execution_pin=record['execution']['receipt'],finalizer_pin=record['finalization']['receipt'],frame_status=record['status'])))
        original_sql=self.journal.read_bytes();original_claim=(self.profile/'workflow-claimed.json').read_bytes();dispatches=len(self.argv)
        retry_code,retry_record=self.call()
        self.assertEqual((retry_code,retry_record['status']),(3,'not_run'));self.assertEqual(len(self.argv),dispatches)
        self.assertEqual(self.journal.read_bytes(),original_sql)
        self.assertEqual((self.profile/'workflow-claimed.json').read_bytes(),original_claim)
        self.assertEqual((self.profile/'registered-workflow.json').read_bytes(),before_workflow)
        (self.folder/'v2-reentry-observation.json').write_bytes(C(dict(new_dispatch=0,sql_bytes_unchanged=True,claim_bytes_unchanged=True,receipt=retry_record)))

    def selection_closed_shapes_fail_before_permit_consumption(self):
        original=json.loads((self.profile/'registered-workflow.json').read_bytes())
        v2=copy.deepcopy(original);v2.update(schema_version=2,measurement_ref=None,
            measurement_selection_policy=dict(schema_version=1,kind='unique_same_run_sensor_acquisition'))
        cases=[]
        def add(label,source,**changes):
            value=copy.deepcopy(source);value.update(changes);cases.append((label,value))
        add('v1-policy',original,measurement_selection_policy=v2['measurement_selection_policy'])
        add('v1-null',original,measurement_ref=None)
        value=copy.deepcopy(v2);value.pop('measurement_selection_policy');cases.append(('v2-missing-policy',value))
        add('v2-ref-also-given',v2,measurement_ref='event:17')
        add('v2-null-policy',v2,measurement_selection_policy=None)
        add('v2-extra-field',v2,approved=True)
        for version in (True,2.0,3):add('workflow-version-'+str(version),v2,schema_version=version)
        for index,policy in enumerate(({},True,[],dict(schema_version=True,kind='unique_same_run_sensor_acquisition'),
                dict(schema_version=1.0,kind='unique_same_run_sensor_acquisition'),dict(schema_version=1,kind='other'),
                dict(schema_version=1,kind='unique_same_run_sensor_acquisition',approved=True))):
            add('policy-'+str(index),v2,measurement_selection_policy=policy)
        outcomes=[]
        for label,value in cases:
            with self.subTest(shape=label):
                self.selection_bind_workflow(value)
                code,record=self.call();self.assertEqual((code,record['status']),(3,'not_run'))
                self.assertEqual(record['phase'],'registration');self.assertEqual(self.argv,[])
                self.assertEqual(len(self.rows()),2);self.assertIsNone(record['reservation'])
                self.assertFalse((self.profile/'workflow-claimed.json').exists())
                outcomes.append(dict(label=label,workflow=value,receipt=record))
        (self.folder/'rejected-shape-observations.json').write_bytes(C(outcomes))

    def selection_v2_preserves_original_quantity_source_context_and_hash_checks(self):
        original=self.selection_v2();outcomes=[]
        cases=[]
        for label,key,value in [('quantity-bool','quantity',dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=True)),
                ('source-changed','source_settings',{**original['source_settings'],'power_dbm':12}),
                ('context-changed','context_sha256','0'*64),('tools-changed','allowed_tools',['sensor.acquire'])]:
            workflow=copy.deepcopy(original);workflow[key]=value;cases.append((label,workflow))
        for label,workflow in cases:
            self.selection_bind_workflow(workflow)
            code,record=self.call();self.assertEqual(code,3);self.assertEqual(record['status'],'not_run')
            self.assertEqual(self.argv,[]);self.assertEqual(len(self.rows()),2)
            outcomes.append(dict(label=label,workflow=workflow,receipt=record))
        self.selection_bind_workflow(original)
        self.put('registered-workflow.json',C(original)+b' ')
        code,record=self.call();self.assertEqual(code,3);self.assertEqual(self.argv,[]);self.assertEqual(len(self.rows()),2)
        self.assertTrue(record['errors'][0]['code'].endswith('binding_mismatch'))
        outcomes.append(dict(label='raw-workflow-hash',receipt=record))
        (self.folder/'binding-observations.json').write_bytes(C(outcomes))

    def selection_bad_version_preserves_original_failure_and_blocked_evidence(self):
        self.selection_v2();self.mode='bad_version';code,record=self.call()
        self.assertEqual((code,record['status']),(4,'failed'))
        self.assertEqual(len(self.argv),1);self.assertEqual(self.argv[0][1:],['--version'])
        self.assertEqual(record['history']['local_model_processes'],0)
        execution=json.loads((self.evidence/'execution-receipt.json').read_bytes())
        finalizer=json.loads((self.evidence/'finalizer-receipt.json').read_bytes())
        self.assertEqual(finalizer['failure'],execution['failure'])
        self.assertEqual(finalizer['status'],'held');self.assertEqual(len(finalizer),12)
        self.assertEqual(finalizer['measurement_selection']['status'],'blocked')
        self.assertIsNone(finalizer['result']);self.assertIsNone(finalizer['artifact'])
        self.assertIsNone(finalizer['measurement_selection']['result'])
        self.assertEqual(finalizer['measurement_selection']['verification']['builder_calls'],0)
        self.assertTrue(any(row['code']=='conducted_execution_result_finalizer_measurement_selection_blocked' for row in finalizer['secondary_errors']))
        self.assertEqual([kind for kind,_ in self.rows()],['baseline','permit','reserved','consumed','finished'])
        self.assertFalse((self.evidence/'.local/conducted-result-artifacts').exists())
        self.assertTrue((self.profile/'workflow-claimed.json').is_file())
        (self.folder/'blocked-observation.json').write_bytes(C(dict(mock_version_processes=1,mock_model_processes=0,actual_model_processes=0,receipt=record)))

    def selection_v1_keeps_original_finalizer_keywords_and_receipt(self):
        self.mode='bad_version';finalize=api._finalize;calls=[]
        def finalizing(execution,**options):
            calls.append(copy.deepcopy(options));return finalize(execution,**options)
        with patch.object(api,'_finalize',side_effect=finalizing):code,record=self.call()
        self.assertEqual(code,4);self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['measurement_ref'],'event:17')
        self.assertNotIn('measurement_selection_policy',calls[0])
        finalizer=json.loads((self.evidence/'finalizer-receipt.json').read_bytes())
        self.assertEqual(len(finalizer),11);self.assertNotIn('measurement_selection',finalizer)
        self.assertEqual(finalizer['status'],'stored');self.assertEqual(record['history']['local_model_processes'],0)
        self.assertEqual(len(record),12);self.assertEqual(len(record['finalization']),5)
        self.assertEqual([kind for kind,_ in self.rows()],['baseline','permit','reserved','consumed','finished'])
        (self.folder/'legacy-v1-observation.json').write_bytes(C(dict(finalizer_keyword_names=list(calls[0]),mock_version_processes=1,actual_model_processes=0,receipt=record)))

    def selection_v2_first_control_survives_later_owned_store_close(self):
        self.selection_v2();control=MemoryError('FIRST_V2_G3_CONTROL');opened=api.Store.open_existing
        counts=dict(store_close=0)
        def lease(path):
            store=opened(path)
            class Proxy:
                def close(self):counts['store_close']+=1;store.close();raise OSError('LATER_OWNED_CLOSE')
                def __getattr__(self,key):return getattr(store,key)
            return Proxy()
        with patch.object(api.Store,'open_existing',side_effect=lease), \
                patch.object(api,'prepare_registered_synthetic_context',side_effect=control):
            with self.assertRaises(MemoryError) as got:self.call()
        self.assertIs(got.exception,control);self.assertEqual(counts,dict(store_close=1))
        self.assertEqual(self.argv,[]);self.assertEqual(len(self.rows()),2)
        self.assertFalse((self.profile/'workflow-claimed.json').exists())
        (self.folder/'first-control-observation.json').write_bytes(C(dict(first_control_same_object=True,owned_store_close_attempts=1,dispatch0=True)))

    def boundary_missing_cancel_never_dispatches(self):
        read=api._read
        def missing(path,cap):
            if path.name=='cancel-request.json':raise FileNotFoundError('PRIVATE_PATH')
            return read(path,cap)
        with patch.object(api,'_read',side_effect=missing):code,result=self.call()
        self.assertEqual(code,3);self.assertEqual(len(self.rows()),2);self.assertEqual(self.argv,[])
        workflow=json.loads((self.profile/'registered-workflow.json').read_bytes())
        workflow['schema_sha256']=self.put('response-schema.json',b'{}')
        self.config['workflow_sha256']=self.put('registered-workflow.json',workflow)
        self.put('operator-control.json',self.config)
        self.permit['workflow_sha256']=self.config['workflow_sha256']
        with sqlite3.connect(self.journal) as con:con.execute("UPDATE codex_conducted_workflow_history SET payload=? WHERE kind='permit'",(C(self.permit).decode(),))
        code,result=self.call();self.assertEqual(code,3)
        self.assertEqual(len(self.rows()),2);self.assertEqual(self.argv,[])

    def boundary_partial_claim_blocks_reentry_without_deletion(self):
        write=api._native_host._active_guard
        def prefix(path,raw):write(path,raw[:7]);raise OSError('PRIVATE_WRITE')
        with patch.object(api._native_host,'_active_guard',side_effect=prefix):code,result=self.call()
        self.assertEqual(code,5);self.assertEqual(len(self.rows()),2);self.assertEqual(self.argv,[])
        prefix_bytes=(self.profile/'workflow-claimed.json').read_bytes();self.assertEqual(len(prefix_bytes),7)
        code,_=self.call();self.assertEqual(code,3)
        self.assertEqual((self.profile/'workflow-claimed.json').read_bytes(),prefix_bytes)

    def boundary_pre_dispatch_controls_keep_original_objects(self):
        for control in (KeyboardInterrupt('CONTROL'),SystemExit(9),GeneratorExit()):
            with patch.object(api,'_prepare',side_effect=control):
                with self.assertRaises(type(control)) as got:self.call()
            self.assertIs(got.exception,control)
        self.assertEqual(len(self.rows()),2);self.assertEqual(self.argv,[])

    def connection_fault(self,kind):
        connect=api.sqlite3.connect
        def wrap(*args,**kwargs):
            connection=connect(*args,**kwargs)
            if 'workflow-continuation.sqlite3' not in str(args[0]):return connection
            class Proxy:
                commits=0
                def execute(self,sql,parameters=()):
                    if kind=='finish' and sql.startswith('INSERT INTO codex_conducted_workflow_history') and parameters[0]=='finished':raise sqlite3.OperationalError('PRIVATE_FINISH')
                    return connection.execute(sql,parameters)
                def commit(self):
                    self.commits+=1
                    if kind=='consume' and self.commits==2:raise sqlite3.OperationalError('PRIVATE_CONSUME')
                    return connection.commit()
                def __getattr__(self,key):return getattr(connection,key)
            return Proxy()
        return patch.object(api.sqlite3,'connect',side_effect=wrap)

    def boundary_consume_commit_failure_never_calls_model(self):
        with self.connection_fault('consume'):code,result=self.call()
        self.assertEqual(code,5);self.assertEqual(self.argv,[])
        self.assertEqual([k for k,v in self.rows()],['baseline','permit','reserved'])
        self.assertTrue((self.profile/'workflow-claimed.json').is_file())

    def boundary_finish_failure_keeps_consumed_rows(self):
        self.mode='bad_version'
        with self.connection_fault('finish'):code,result=self.call()
        self.assertEqual(code,5);self.assertIsNone(result['history'])
        self.assertEqual([k for k,v in self.rows()],['baseline','permit','reserved','consumed'])
        self.assertTrue((self.evidence/'loop/calls/0001/producer/receipt.json').is_file())

    def boundary_evidence_budget_refuses_extra_host_write(self):
        self.mode='bad_version'
        with patch.object(api._OutputBudget,'reserve',side_effect=api._Failure(api._PREFIX+'evidence_limit')):
            code,result=self.call()
        self.assertEqual(code,5);self.assertEqual(result['history']['local_model_processes'],0)
        self.assertFalse((self.evidence/'execution-receipt.json').exists())
        self.assertTrue((self.evidence/'loop/calls/0001/producer/receipt.json').is_file())

    def boundary_ambiguous_spawn_is_unknown_instead_of_zero(self):
        spawn=self.spawn
        def ambiguous(argv,**options):
            if argv[1:]!=['--version']:
                self.argv.append(list(argv));raise OSError('PRIVATE_SPAWN_UNCERTAINTY')
            return spawn(argv,**options)
        with patch('labflow.codex_cli_response.subprocess.Popen',side_effect=ambiguous):code,result=self.call()
        self.assertEqual(code,5);self.assertIsNone(result['history']['local_model_processes'])
        self.assertEqual(self.rows()[-1][1]['status'],'unknown')

    def boundary_store_close_cannot_replace_first_control(self):
        control=MemoryError('FIRST_G3_CONTROL')
        opened=api.Store.open_existing
        def lease(path):
            store=opened(path)
            class Proxy:
                def close(self):store.close();raise OSError('LATER_STORE_CLOSE')
                def __getattr__(self,key):return getattr(store,key)
            return Proxy()
        with patch.object(api.Store,'open_existing',side_effect=lease), \
                patch.object(api,'prepare_registered_synthetic_context',side_effect=control):
            with self.assertRaises(MemoryError) as got:self.call()
        self.assertIs(got.exception,control);self.assertEqual(self.argv,[])

    def failure_snapshot(self):
        files={}
        for path in self.store_root.rglob('*'):
            if path.is_file():
                info=path.stat(follow_symlinks=False)
                files[str(path.relative_to(self.store_root))]=dict(bytes=info.st_size,sha256=H(path.read_bytes()),
                    device=info.st_dev,inode=info.st_ino,mtime_ns=info.st_mtime_ns,nlink=info.st_nlink,
                    attributes=info.st_file_attributes,reparse_tag=info.st_reparse_tag)
        connection=sqlite3.connect((self.store_root/'lab.sqlite3').as_uri()+'?mode=ro',uri=True)
        try:
            connection.execute('PRAGMA query_only=ON')
            jobs=connection.execute('SELECT job_id,state,worker_id,token,attempt,result_json FROM intake_jobs ORDER BY job_id').fetchall()
            completed=connection.execute("SELECT count(*) FROM intake_jobs WHERE state='completed'").fetchone()[0]
        finally:connection.close()
        return dict(files=files,jobs=jobs,completed=completed,workflow_rows=self.rows())

    def failure_invoke(self,first,late,*,ledger=False):
        before=self.failure_snapshot();counts=dict(store_close=0,ledger_close=0)
        opened=api.Store.open_existing;close_ledger=api._close_ledger;returned=raised=None
        def lease(path):
            store=opened(path);close_store=store.close
            def closing_store():
                counts['store_close']+=1;close_store()
                if late is not None and not ledger:raise late
            store.close=closing_store
            return store
        def closing(connection):
            counts['ledger_close']+=1;close_ledger(connection)
            if late is not None and ledger:raise late
        try:
            with patch.object(api.Store,'open_existing',side_effect=lease),patch.object(api,'_close_ledger',side_effect=closing):
                if first is None:returned=self.call()
                else:
                    with patch.object(api,'prepare_registered_synthetic_context',side_effect=first):returned=self.call()
            return returned
        except BaseException as error:
            raised=error;raise
        finally:
            after=self.failure_snapshot()
            observation=dict(case=self._testMethodName,first=None if first is None else type(first).__name__,
                late=None if late is None else type(late).__name__,late_phase='ledger_close' if ledger else 'store_close',
                returned=returned,raised=None if raised is None else type(raised).__name__,
                raised_is_first=raised is first and first is not None,raised_is_late=raised is late and late is not None,
                counts=counts,source_before=before,source_after=after,source_unchanged=before==after,
                genuine_runtime_calls=0,actual_model_processes=0,producer_argv=len(self.argv))
            (self.folder/('first-failure-'+uuid.uuid4().hex[:8]+'.json')).write_bytes(C(observation))
            self.assertEqual(before,after);self.assertEqual(counts,dict(store_close=1,ledger_close=1))
            self.assertEqual(self.argv,[]);self.assertEqual(len(self.rows()),2)
            self.assertFalse((self.profile/'workflow-claimed.json').exists());self.assertEqual(list(self.evidence.iterdir()),[])

    def failure_first_ordinary_survives_late_store_controls(self):
        first=ValueError('FIRST_ORDINARY');baseline=self.failure_invoke(first,None)
        self.assertEqual(baseline[0],3);self.assertEqual(baseline[1]['status'],'not_run')
        self.assertEqual(baseline[1]['errors'],[dict(phase='registration',code=api._PREFIX+'operation_failed')])
        for control in (MemoryError,SystemExit,GeneratorExit,KeyboardInterrupt):
            with self.subTest(late=control.__name__):
                try:code,result=self.failure_invoke(first,control('LATER_STORE_CONTROL'))
                except api._CONTROL as error:self.fail('Later '+type(error).__name__+' replaced the first ordinary failure DTO')
                self.assertEqual((code,result['status'],result['phase']),(baseline[0],baseline[1]['status'],baseline[1]['phase']))
                self.assertEqual(result['errors'][0],baseline[1]['errors'][0])
                self.assertEqual(result['errors'][1],dict(phase='store_close',code=api._PREFIX+'interrupted'))
                self.assertEqual(set(result),set(baseline[1]));self.assertIsNone(result['execution']);self.assertIsNone(result['finalization'])

    def failure_first_ordinary_survives_late_ledger_control(self):
        self.selection_v2();first=OSError('FIRST_NATIVE_OPERATION');baseline=self.failure_invoke(first,None)
        try:code,result=self.failure_invoke(first,MemoryError('LATER_LEDGER_CONTROL'),ledger=True)
        except api._CONTROL:self.fail('Later ledger CONTROL replaced the first ordinary failure DTO')
        self.assertEqual((code,result['status'],result['phase']),(baseline[0],baseline[1]['status'],baseline[1]['phase']))
        self.assertEqual(result['errors'][0],baseline[1]['errors'][0])
        self.assertEqual(result['errors'][1],dict(phase='ledger_close',code=api._PREFIX+'interrupted'))

    def failure_first_control_survives_late_ordinary(self):
        first=MemoryError('FIRST_CONTROL')
        with self.assertRaises(MemoryError) as got:self.failure_invoke(first,OSError('LATER_ORDINARY_CLOSE'))
        self.assertIs(got.exception,first)

    def failure_two_controls_keep_first_object(self):
        self.selection_v2();first=SystemExit('FIRST_CONTROL')
        with self.assertRaises(SystemExit) as got:self.failure_invoke(first,MemoryError('SECOND_CONTROL'))
        self.assertIs(got.exception,first)

    def failure_first_close_error_with_no_prior_failure(self):
        code,result=self.failure_invoke(None,OSError('FIRST_BODY_CLOSE'))
        self.assertEqual((code,result['status']),(3,'not_run'))
        self.assertEqual(result['errors'],[dict(phase='registration',code=api._PREFIX+'operation_failed')])
        self.selection_v2();first=MemoryError('FIRST_BODY_CLOSE_CONTROL')
        with self.assertRaises(MemoryError) as got:self.failure_invoke(None,first)
        self.assertIs(got.exception,first)

    def boundary_rollback_failure_still_attempts_owned_close_once(self):
        connect=api.sqlite3.connect;counts=dict(rollback=0,close=0)
        def wrap(*args,**kwargs):
            connection=connect(*args,**kwargs)
            if 'workflow-continuation.sqlite3' not in str(args[0]):return connection
            class Proxy:
                def rollback(self):counts['rollback']+=1;raise sqlite3.OperationalError('FIRST_ROLLBACK')
                def close(self):counts['close']+=1;connection.close()
                def __getattr__(self,key):return getattr(connection,key)
            return Proxy()
        with patch.object(api.sqlite3,'connect',side_effect=wrap):code,result=self.call(model='gpt-6.1-sol')
        self.assertEqual(code,3);self.assertEqual(counts,dict(rollback=1,close=1));self.assertEqual(self.argv,[])


_CURRENT_SEED_FILE=None
_CURRENT_SEED_INFO=None


def _current_seed():
    global _CURRENT_SEED_INFO
    if _CURRENT_SEED_INFO is not None:return _CURRENT_SEED_INFO
    if _CURRENT_SEED_FILE is not None:
        path=Path(_CURRENT_SEED_FILE).absolute()
        assert path.is_relative_to(ROOT/'.local/wch')
        value=json.loads(path.read_bytes());assert value['kind']=='authored_public_completed_TXT_seed'
        _CURRENT_SEED_INFO=value;return value
    from labflow.intake_jobs import claim_job,complete_job,respond
    from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts
    helper=WorkflowHostTests(next(name for name in WorkflowHostTests.__dict__ if name.startswith('test_')))
    helper._testMethodName='current_public_completed_TXT_setup_once';helper.setUp()
    try:
        queued=helper.folder/'q'
        for path in helper.store_root.rglob('*'):
            if path.is_file():
                dest=queued/path.relative_to(helper.store_root);dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as stream:stream.write(path.read_bytes())
        store=Store.open_existing(str(helper.store_root))
        try:
            respond(store,'WCH-SETUP-PROCEED','proceed',intake_id=helper.context['intake_id'])
            claimed=claim_job(store,'WCH-PUBLIC-SETUP',now=102,synthetic_only=True)
            assert claimed is not None and claimed['job_id']==helper.context['job_id']
            context={key:claimed[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
            assert C(context)==C(helper.context)
            analysis=decode_analysis_response(C(helper.analysis),context,producer_name='SCRIPTED-WFH-MOCK')
            complete_job(store,claimed['job_id'],claimed['token'],analysis,now=103)
        finally:store.close()
        current=read_current_conducted_plan_from_facts(helper.store_root,context['intake_id'],method=dict(
            method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
        assert current['facts_plan']['status']=='ready_for_simulation'
        assert H(C(current['context']))!=H(C(context))
        info=dict(kind='authored_public_completed_TXT_seed',folder=str(helper.folder),profile=str(helper.profile),
            store_root=str(helper.store_root),queued_store=str(queued),script=str(helper.script),
            queued_context=helper.context,queued_analysis=helper.analysis,queued_plan=helper.plan,
            current=current,setup=dict(public_proceed=1,public_claim=1,claimed_strict_decode=1,public_complete=1,
                genuine_runtime_calls=0,actual_models=0),seed_file=str(helper.folder/'seed.json'))
        (helper.folder/'seed.json').write_bytes(C(info));_CURRENT_SEED_INFO=info;return info
    finally:helper.doCleanups()


class CurrentWorkflowTests(unittest.TestCase):
    def setUp(self):
        global LOCAL,BUDGET
        previous=(LOCAL,BUDGET);LOCAL=LOCAL/uuid.uuid4().hex[:8];BUDGET=Budget()
        def restore():
            global LOCAL,BUDGET
            LOCAL,BUDGET=previous
        self.addCleanup(restore)

    @contextmanager
    def case(self,label,*,legacy=False,genuine=False):
        seed=_current_seed();helper=WorkflowHostTests(next(name for name in WorkflowHostTests.__dict__ if name.startswith('test_')))
        helper._testMethodName='current_'+label
        def clone(owner):
            def copy(source,target):
                for path in Path(source).rglob('*'):
                    if path.is_file():
                        dest=target/path.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
                        with dest.open('xb') as stream:stream.write(path.read_bytes())
            copy(seed['profile'],owner.profile)
            owner.journal=owner.profile/'workflow-continuation.sqlite3';owner.script=Path(seed['script'])
            owner.config=json.loads((owner.profile/'operator-control.json').read_bytes())
            owner.permit=json.loads(owner.rows()[1][1] if type(owner.rows()[1][1]) is str else C(owner.rows()[1][1]))
            owner.permit['expires_at']=(datetime.now(timezone.utc)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            if genuine:
                owner.store_root=Path(seed['store_root'])
            else:
                owner.store_root=owner.folder/'s';copy(seed['queued_store'] if legacy else seed['store_root'],owner.store_root)
                source=owner.folder/'i';copy(Path(seed['folder'])/'i',source)
                connection=sqlite3.connect(owner.store_root/'lab.sqlite3')
                try:connection.execute('UPDATE intake_sources SET root=?',(str(source),));connection.commit()
                finally:connection.close()
                owner.config['registered_input_root']=str(source/'case')
            owner.config['store_root']=str(owner.store_root);owner.put('operator-control.json',owner.config)
            owner.context=seed['queued_context'];owner.analysis=seed['queued_analysis'];owner.plan=seed['queued_plan']
            if not legacy:
                current=seed['current'];owner.context=current['context'];owner.analysis=current['analysis'];owner.plan=current['facts_plan']['plan_input']
                workflow=json.loads((owner.profile/'registered-workflow.json').read_bytes())
                workflow.update(schema_version=3,context_scope='completed_current_provided',measurement_ref=None,
                    measurement_selection_policy=dict(schema_version=1,kind='unique_same_run_sensor_acquisition'),
                    context_sha256=H(C(owner.context)),analysis_sha256=owner.put('analysis.json',owner.analysis),
                    plan_input_sha256=owner.put('plan-input.json',owner.plan))
                owner.selection_bind_workflow(workflow)
        with patch.object(WorkflowHostTests,'make_profile',clone):helper.setUp()
        try:yield helper
        finally:helper.doCleanups()

    def prepare(self,helper):
        owned=dict(store=None)
        try:return api._prepare(helper.profile,helper.config,'WFH-CASE',owned),owned.get('current_facts_plan')
        finally:
            if owned['store'] is not None:owned['store'].close()

    def reject(self,helper):
        before=helper.failure_snapshot()
        with patch.object(api,'_execute',side_effect=AssertionError('NO_RUNTIME')) as execution:
            code,result=helper.call()
        self.assertEqual(code,3);self.assertEqual(result['status'],'not_run');self.assertFalse(execution.called)
        self.assertEqual(helper.failure_snapshot(),before);self.assertEqual(helper.argv,[])
        self.assertFalse((helper.profile/'workflow-claimed.json').exists());self.assertEqual(list(helper.evidence.iterdir()),[])
        return result

    def current_preflight_binds_completed_original_five_pins(self):
        from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts
        with self.case('preflight') as helper:
            before=helper.failure_snapshot()
            with patch.object(api,'_current_facts',wraps=read_current_conducted_plan_from_facts,create=True) as reader, \
                    patch.object(api._native_host,'_dedicated',side_effect=AssertionError('QUEUED_GATE_FORBIDDEN')), \
                    patch.object(api,'prepare_registered_synthetic_context',side_effect=AssertionError('G3_FORBIDDEN')):
                prepared,current=self.prepare(helper)
            self.assertEqual(prepared[0]['schema_version'],3);self.assertEqual(len(prepared[0]),14)
            self.assertEqual(C(current),C(_current_seed()['current']));self.assertEqual(C(prepared[1:4]),C([current['context'],current['analysis'],current['facts_plan']['plan_input']]))
            self.assertEqual(reader.call_count,1);self.assertEqual(reader.call_args.kwargs['expected_context_sha256'],H(C(current['context'])))
            self.assertEqual(helper.failure_snapshot(),before);self.assertEqual(helper.argv,[]);self.assertEqual(list(helper.evidence.iterdir()),[])

    def current_legacy_queued_v1_v2_keep_original_preparation(self):
        with self.case('legacy',legacy=True) as helper:
            for version in (1,2):
                if version==2:helper.selection_v2()
                with patch.object(api,'_current_facts',side_effect=AssertionError('CURRENT_FORBIDDEN'),create=True):prepared,current=self.prepare(helper)
                self.assertEqual(prepared[0]['schema_version'],version);self.assertEqual(C(prepared[1]),C(_current_seed()['queued_context']));self.assertIsNone(current)
                self.assertEqual(len(helper.rows()),2);self.assertEqual(helper.argv,[])

    def current_closed_shapes_reject_before_consumption(self):
        def missing(v):v.pop('context_scope')
        mutations=[missing,lambda v:v.update(context_scope='queued'),lambda v:v.update(schema_version=True),
            lambda v:v.update(schema_version=3.0),lambda v:v.update(extra=1),lambda v:v.update(measurement_ref='last'),
            lambda v:v.update(measurement_selection_policy=None),lambda v:v.update(schema_version=2)]
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index),self.case('shape'+str(index)) as helper:
                workflow=json.loads((helper.profile/'registered-workflow.json').read_bytes());mutate(workflow);helper.selection_bind_workflow(workflow);self.reject(helper)

    def current_scope_failures_precede_current_read(self):
        changes=[("UPDATE intake_jobs SET state='queued'",()),("UPDATE intake_jobs SET state='running'",()),
            ("UPDATE intakes SET status='upload_incomplete'",()),("UPDATE intakes SET revision=2",()),
            ("UPDATE intake_sources SET synthetic=0",()),("UPDATE intake_revisions SET synthetic=0",()),
            ("UPDATE intakes SET bundle='other'",()),("UPDATE intake_sources SET root=root||'-other'",()),
            ("UPDATE intake_revisions SET files_json='[]'",()),
            ("INSERT INTO intakes(intake_id,source_id,bundle,revision,status) VALUES('OTHER','WFH-SYN','other',1,'queued')",()),
            ("UPDATE intake_jobs SET state='failed'",())]
        for index,(sql,args) in enumerate(changes):
            with self.subTest(index=index),self.case('scope'+str(index)) as helper:
                connection=sqlite3.connect(helper.store_root/'lab.sqlite3')
                try:
                    connection.execute(sql,args)
                    if index==9:
                        connection.execute("INSERT INTO intake_revisions VALUES('OTHER',1,?,'[]',1,101)",('0'*64,))
                        connection.execute("INSERT INTO intake_jobs(job_id,intake_id,revision,state,created_at) VALUES('OTHER-JOB','OTHER',1,'queued',101)")
                    connection.commit()
                finally:connection.close()
                with patch.object(api,'_current_facts',side_effect=AssertionError('SCOPE_MUST_REJECT_FIRST'),create=True) as reader:self.reject(helper)
                self.assertFalse(reader.called)

    def current_binding_and_original_file_drift_reject(self):
        for field in ('context_sha256','analysis_sha256','plan_input_sha256','catalog_sha256','schema_sha256','analysis_other','original_file',
                'selection_source_id','selection_intake_id','selection_job_id','selection_revision'):
            with self.subTest(field=field),self.case(field) as helper:
                workflow=json.loads((helper.profile/'registered-workflow.json').read_bytes())
                if field=='analysis_other':
                    analysis=json.loads(C(helper.analysis));analysis['producer']['name']='OTHER';workflow['analysis_sha256']=helper.put('analysis.json',analysis)
                elif field=='original_file':(Path(helper.config['registered_input_root'])/'r.txt').write_bytes(b'CHANGED\n')
                elif field.startswith('selection_'):
                    manifest=json.loads((helper.profile/'registered-intake-v1.json').read_bytes());key=field.removeprefix('selection_')
                    manifest['registered_intake'][key]=2 if key=='revision' else 'OTHER'
                    helper.config['registration_sha256']=helper.put('registered-intake-v1.json',manifest)
                    helper.permit['registration_sha256']=helper.config['registration_sha256']
                else:workflow[field]='0'*64
                helper.selection_bind_workflow(workflow);self.reject(helper)

    def current_scope_drift_after_reader_rejects(self):
        from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts
        with self.case('read_drift') as helper:
            def drift(*args,**kwargs):
                value=read_current_conducted_plan_from_facts(*args,**kwargs)
                connection=sqlite3.connect(helper.store_root/'lab.sqlite3')
                try:connection.execute("UPDATE intakes SET status='upload_incomplete'");connection.commit()
                finally:connection.close()
                return value
            with patch.object(api,'_current_facts',side_effect=drift,create=True),patch.object(api,'_execute',side_effect=AssertionError('NO_RUNTIME')) as execution:code,result=helper.call()
            self.assertEqual((code,result['status']),(3,'not_run'));self.assertFalse(execution.called);self.assertEqual(len(helper.rows()),2)
            self.assertEqual(list(helper.evidence.iterdir()),[])

    def current_handoff_reservation_and_null_pins_finally(self):
        with self.case('finally_null') as helper:
            before=helper.failure_snapshot();reservations=[];reserve=api._OutputBudget.reserve
            def reserved(owner,files,size):reservations.append((files,size));return reserve(owner,files,size)
            def fail(*args,**kwargs):
                self.assertTrue(reservations and reservations[0][0]==1)
                self.assertEqual(kwargs['evidence_reservation'],dict(files=11,bytes=reservations[0][1]+5505024))
                self.assertFalse((helper.evidence/'current-handoff.json').exists());raise ValueError('FIRST_EXECUTION')
            with patch.object(api._OutputBudget,'reserve',reserved),patch.object(api,'_execute',side_effect=fail):code,result=helper.call()
            self.assertEqual((code,result['status']),(5,'unknown'));packet=json.loads((helper.evidence/'current-handoff.json').read_bytes())
            self.assertEqual(set(packet),set('schema_version kind workflow_sha256 current_facts_plan execution_receipt finalizer_receipt'.split()))
            self.assertEqual(packet['kind'],'codex_conducted_workflow_current_handoff');self.assertIs(type(packet['schema_version']),int);self.assertEqual(packet['schema_version'],1)
            self.assertEqual(C(packet['current_facts_plan']),C(_current_seed()['current']));self.assertIsNone(packet['execution_receipt']);self.assertIsNone(packet['finalizer_receipt'])
            after=helper.failure_snapshot();self.assertEqual(before['files'],after['files']);self.assertEqual(before['jobs'],after['jobs']);self.assertEqual(len(after['workflow_rows']),5)
            self.assertEqual(helper.argv,[]);self.assertEqual(len(result),12)

    def current_handoff_capacity_rejects_before_consume(self):
        with self.case('reservation_denied') as helper:
            with patch.object(api._OutputBudget,'reserve',side_effect=api._Failure(api._PREFIX+'evidence_limit')):self.reject(helper)

    def current_handoff_packet_limits_before_output(self):
        original=_current_seed()['current'];raw=api._handoff_raw('a'*64,original,None,None)
        self.assertEqual(len(json.loads(raw)),6);self.assertLessEqual(len(raw),8388608)
        depth=None
        for _ in range(25):depth=[depth]
        for questions in (['x'*8388608],[None]*50001,depth,[float('nan')],[2**64]):
            current=json.loads(C(original));current['facts_plan']['questions']=questions
            with self.assertRaises(ValueError):api._handoff_raw('a'*64,current,None,None)

    def current_reader_first_errors_before_consume(self):
        for control_first in (False,True):
            with self.subTest(control_first=control_first),self.case('reader_first'+str(control_first)) as helper:
                first=MemoryError('FIRST_READ_CONTROL') if control_first else ValueError('FIRST_READ_ORDINARY')
                late=OSError('LATER_CLOSE') if control_first else MemoryError('LATER_CLOSE_CONTROL')
                opened=api.Store.open_existing;count=[];before=helper.failure_snapshot()
                def lease(path):
                    store=opened(path);close=store.close
                    def closing():count.append(path);close();raise late
                    store.close=closing;return store
                with patch.object(api.Store,'open_existing',side_effect=lease),patch.object(api,'_current_facts',side_effect=first):
                    if control_first:
                        with self.assertRaises(MemoryError) as got:helper.call()
                        self.assertIs(got.exception,first)
                    else:
                        code,result=helper.call();self.assertEqual((code,result['status']),(3,'not_run'))
                        self.assertEqual(result['errors'],[dict(phase='registration',code=api._PREFIX+'operation_failed'),dict(phase='store_close',code=api._PREFIX+'interrupted')])
                self.assertEqual(len(count),1);self.assertEqual(helper.failure_snapshot(),before);self.assertEqual(helper.argv,[])
                self.assertEqual(list(helper.evidence.iterdir()),[])

    def current_handoff_never_overwrites_existing_prefix(self):
        with self.case('no_overwrite') as helper:
            path=helper.evidence/'current-handoff.json';active=api._native_host._active_guard;attempts=[]
            def execute(*args,**kwargs):path.write_bytes(b'EXISTING_PREFIX');raise ValueError('FIRST_EXECUTION')
            def guard(target,raw):
                if target==path:attempts.append(target)
                return active(target,raw)
            with patch.object(api,'_execute',side_effect=execute),patch.object(api._native_host,'_active_guard',side_effect=guard):code,result=helper.call()
            self.assertEqual((code,result['status']),(5,'unknown'));self.assertEqual(result['errors'][0]['phase'],'execution')
            self.assertEqual(result['errors'][1]['phase'],'current_handoff');self.assertEqual(path.read_bytes(),b'EXISTING_PREFIX');self.assertEqual(len(attempts),1)
            self.assertEqual(helper.argv,[])

    def current_first_errors_survive_partial_handoff_once(self):
        for control_first in (False,True):
            with self.subTest(control_first=control_first),self.case('first'+str(control_first)) as helper:
                first=MemoryError('FIRST_CONTROL') if control_first else ValueError('FIRST_ORDINARY');late=OSError('LATE_WRITE') if control_first else MemoryError('LATE_CONTROL')
                active=api._native_host._active_guard;attempts=[];before=helper.failure_snapshot()
                def partial(path,raw):
                    if path.name!='current-handoff.json':return active(path,raw)
                    attempts.append(path)
                    with path.open('xb') as stream:stream.write(b'{')
                    raise late
                with patch.object(api,'_execute',side_effect=first),patch.object(api._native_host,'_active_guard',side_effect=partial):
                    if control_first:
                        with self.assertRaises(MemoryError) as got:helper.call()
                        self.assertIs(got.exception,first)
                    else:
                        code,result=helper.call();self.assertEqual((code,result['status']),(5,'unknown'));self.assertEqual(result['errors'][0]['phase'],'execution')
                        self.assertEqual(result['errors'][1]['phase'],'current_handoff')
                self.assertEqual(len(attempts),1);self.assertEqual((helper.evidence/'current-handoff.json').read_bytes(),b'{')
                after=helper.failure_snapshot();self.assertEqual(before['files'],after['files']);self.assertEqual(before['jobs'],after['jobs']);self.assertEqual(helper.argv,[])

    def current_genuine_completed_same_snapshot_mock_once(self):
        seed=_current_seed();marker=Path(seed['folder'])/'genuine-loop-one-shot.json'
        with marker.open('xb') as stream:stream.write(C(dict(genuine_loop_max=1,actual_models=0)))
        with self.case('genuine',genuine=True) as helper:
            before=helper.failure_snapshot()
            with patch.object(api,'_execute',wraps=api._execute) as execute,patch.object(api,'_finalize',wraps=api._finalize) as finalize:
                code,result=helper.call()
            self.assertEqual((code,result['status']),(0,'completed'));self.assertEqual(execute.call_count,1);self.assertEqual(finalize.call_count,1)
            self.assertEqual(C(execute.call_args.args),C([seed['current']['context'],seed['current']['analysis'],seed['current']['facts_plan']['plan_input']]))
            raw=(helper.evidence/'current-handoff.json').read_bytes();packet=json.loads(raw)
            self.assertEqual(C(packet['current_facts_plan']),C(seed['current']));self.assertEqual(packet['workflow_sha256'],helper.config['workflow_sha256'])
            for name in ('execution','finalizer'):
                value=(helper.evidence/(name+'-receipt.json')).read_bytes();self.assertEqual(packet[name+'_receipt'],dict(bytes=len(value),sha256=H(value)))
            execution=json.loads((helper.evidence/'execution-receipt.json').read_bytes());finalizer=json.loads((helper.evidence/'finalizer-receipt.json').read_bytes())
            self.assertEqual(C(execution['plan_input']),C(seed['current']['facts_plan']['plan_input']))
            self.assertEqual(C(finalize.call_args.args[0]),C(execution))
            maximum=api._handoff_raw(helper.config['workflow_sha256'],seed['current'],dict(bytes=262144,sha256='0'*64),dict(bytes=2097152,sha256='0'*64))
            self.assertEqual(execute.call_args.kwargs['evidence_reservation'],dict(files=11,bytes=len(maximum)+5505024))
            self.assertEqual(finalizer['status'],'stored');self.assertEqual(len(result),12);self.assertEqual(len(result['finalization']),5)
            after=helper.failure_snapshot();self.assertEqual(before['files'],after['files']);self.assertEqual(before['jobs'],after['jobs'])
            calls=len(helper.argv);rows=helper.rows();code,reentry=helper.call();self.assertEqual(code,3);self.assertEqual(helper.rows(),rows);self.assertEqual(len(helper.argv),calls)
            self.assertEqual((helper.evidence/'current-handoff.json').read_bytes(),raw);self.assertEqual(result['history']['local_model_processes'],5)
            self.assertEqual(execution['loop']['budget']['application_retries'],0);self.assertTrue(all(child.poll() is not None for child in helper.children))
            files=[p for p in helper.evidence.rglob('*') if p.is_file()]
            self.assertLessEqual(len(files),192);self.assertLessEqual(sum(p.stat().st_size for p in files),33554432)
            proof=dict(source_before=before,source_after=after,execution_reservation=execute.call_args.kwargs['evidence_reservation'],
                handoff_reserved_files=1,handoff_reserved_bytes=len(maximum),tail_files=10,tail_bytes=5505024,
                actual_handoff_bytes=len(raw),handoff_pin=dict(bytes=len(raw),sha256=H(raw)),evidence_files=len(files),evidence_bytes=sum(p.stat().st_size for p in files),
                mock_model_processes=sum('--model' in argv for argv in helper.argv),actual_models=0,genuine_loop_calls=1,reconsume_blocked=True,
                finalization=finalizer['status'],C1_current=H(C(seed['current']['context'])),C1_queued=H(C(seed['queued_context'])))
            (helper.folder/'genuine-observation.json').write_bytes(C(proof))

    test_current_preflight_binds_completed_original_five_pins=current_preflight_binds_completed_original_five_pins
    test_current_legacy_queued_v1_v2_keep_original_preparation=current_legacy_queued_v1_v2_keep_original_preparation
    test_current_closed_shapes_reject_before_consumption=current_closed_shapes_reject_before_consumption
    test_current_scope_failures_precede_current_read=current_scope_failures_precede_current_read
    test_current_binding_and_original_file_drift_reject=current_binding_and_original_file_drift_reject
    test_current_scope_drift_after_reader_rejects=current_scope_drift_after_reader_rejects
    test_current_handoff_reservation_and_null_pins_finally=current_handoff_reservation_and_null_pins_finally
    test_current_handoff_capacity_rejects_before_consume=current_handoff_capacity_rejects_before_consume
    test_current_handoff_packet_limits_before_output=current_handoff_packet_limits_before_output
    test_current_reader_first_errors_before_consume=current_reader_first_errors_before_consume
    test_current_handoff_never_overwrites_existing_prefix=current_handoff_never_overwrites_existing_prefix
    test_current_first_errors_survive_partial_handoff_once=current_first_errors_survive_partial_handoff_once


if __name__=='__main__':
    if '--current-seed' in sys.argv:
        index=sys.argv.index('--current-seed');_CURRENT_SEED_FILE=sys.argv[index+1];del sys.argv[index:index+2]
    if '--current-seed-prepare' in sys.argv:
        LOCAL=ROOT/'.local/wch'/uuid.uuid4().hex[:8];seed=_current_seed();print(json.dumps(dict(seed_file=seed['seed_file'],setup=seed['setup'])));raise SystemExit(0)
    groups={'--current-preflight':['current_preflight_binds_completed_original_five_pins','current_legacy_queued_v1_v2_keep_original_preparation'],
        '--current-shapes':['current_closed_shapes_reject_before_consumption'],
        '--current-binding':['current_binding_and_original_file_drift_reject'],
        '--current-scope':['current_scope_failures_precede_current_read','current_scope_drift_after_reader_rejects'],
        '--current-handoff':['current_handoff_reservation_and_null_pins_finally','current_handoff_capacity_rejects_before_consume',
            'current_handoff_packet_limits_before_output','current_reader_first_errors_before_consume',
            'current_handoff_never_overwrites_existing_prefix','current_first_errors_survive_partial_handoff_once'],
        '--current-genuine':['current_genuine_completed_same_snapshot_mock_once']}
    group=next((key for key in groups if key in sys.argv),None)
    if group is not None:
        sys.argv.remove(group);LOCAL=ROOT/'.local/wch'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['CurrentWorkflowTests.'+name for name in groups[group]])
    elif '--first-failure' in sys.argv:
        sys.argv.remove('--first-failure');LOCAL=ROOT/'.local/fhf'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['WorkflowHostTests.failure_first_ordinary_survives_late_store_controls',
            'WorkflowHostTests.failure_first_ordinary_survives_late_ledger_control',
            'WorkflowHostTests.failure_first_control_survives_late_ordinary',
            'WorkflowHostTests.failure_two_controls_keep_first_object',
            'WorkflowHostTests.failure_first_close_error_with_no_prior_failure'])
    elif '--selection-preflight' in sys.argv:
        sys.argv.remove('--selection-preflight');LOCAL=ROOT/'.local/wsh'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['WorkflowHostTests.selection_explicit_v2_prepares_exact13_without_dispatch'])
    elif '--selection-genuine' in sys.argv:
        sys.argv.remove('--selection-genuine');LOCAL=ROOT/'.local/wsh'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['WorkflowHostTests.selection_genuine_v2_mock5_preserves_selection_and_artifact_chain'])
    elif '--selection-boundary' in sys.argv:
        sys.argv.remove('--selection-boundary');LOCAL=ROOT/'.local/wsh'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['WorkflowHostTests.selection_explicit_v2_prepares_exact13_without_dispatch',
            'WorkflowHostTests.selection_closed_shapes_fail_before_permit_consumption',
            'WorkflowHostTests.selection_v2_preserves_original_quantity_source_context_and_hash_checks',
            'WorkflowHostTests.selection_v2_first_control_survives_later_owned_store_close'])
    elif '--selection-blocked' in sys.argv:
        sys.argv.remove('--selection-blocked');LOCAL=ROOT/'.local/wsh'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['WorkflowHostTests.selection_bad_version_preserves_original_failure_and_blocked_evidence'])
    elif '--selection-legacy' in sys.argv:
        sys.argv.remove('--selection-legacy');LOCAL=ROOT/'.local/wsh'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['WorkflowHostTests.selection_v1_keeps_original_finalizer_keywords_and_receipt'])
    elif '--boundary' in sys.argv:
        sys.argv.remove('--boundary')
        names=['WorkflowHostTests.'+name for name in WorkflowHostTests.__dict__ if name.startswith('boundary_')]
        unittest.main(defaultTest=names)
    else:unittest.main()
