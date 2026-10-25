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


if __name__=='__main__':
    if '--boundary' in sys.argv:
        sys.argv.remove('--boundary')
        names=['WorkflowHostTests.'+name for name in WorkflowHostTests.__dict__ if name.startswith('boundary_')]
        unittest.main(defaultTest=names)
    else:unittest.main()
