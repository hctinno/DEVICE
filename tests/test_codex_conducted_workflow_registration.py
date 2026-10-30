"""Authored operator records at a substituted OS boundary; real profile/model0."""
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from labflow.active_intake import register_source,scan_source
from labflow.intake_jobs import prepare_registered_synthetic_context,claim_job,complete_job,respond
from labflow.intake_model_boundary import decode_analysis_response
from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts
from labflow.store import Store,canonical
from labflow import codex_registered_conducted_workflow_host as host
try:api=importlib.import_module('labflow.codex_conducted_workflow_registration')
except ModuleNotFoundError as error:
    if error.name!='labflow.codex_conducted_workflow_registration':raise
    api=None

C=lambda v:canonical(v).encode('utf-8')
H=lambda raw:hashlib.sha256(raw).hexdigest()
LOCAL=ROOT/'.local/reg'/uuid.uuid4().hex
EXTRA_PROOF_ROOT=None
REAL_POPEN=subprocess.Popen

class Budget:
    def __init__(self):self.slots={};self.total=0;self.native=0
    def charge(self,path,size):
        path=Path(os.path.abspath(path))
        assert path.is_relative_to(LOCAL) or (EXTRA_PROOF_ROOT is not None and path.is_relative_to(EXTRA_PROOF_ROOT))
        delta=max(0,size-self.slots.get(path,0))
        assert self.total+delta<=33554432 and len(self.slots)+self.native+(path not in self.slots)<=512,'PROOF_ADMISSION'
        self.slots[path]=max(size,self.slots.get(path,0));self.total+=delta
    def reserve(self):
        assert self.total+2097152<=33554432 and len(self.slots)+self.native+32<=512
        self.total+=2097152;self.native+=32
    def settle(self,folder,additional=None):
        self.total-=2097152;self.native-=32
        for root in (folder,) if additional is None else (folder,additional):
            for path in root.rglob('*'):
                if path.is_file():self.charge(path,path.stat().st_size)

BUDGET=Budget()
class Writer:
    def __init__(self,s,p):self.s,self.p=s,p
    def write(self,v):
        size=len(v.encode('utf-8'))*2 if type(v) is str else len(v)
        BUDGET.charge(self.p,self.s.tell()+size);return self.s.write(v)
    def __getattr__(self,key):return getattr(self.s,key)
    def __enter__(self):return self
    def __exit__(self,*args):return self.s.__exit__(*args)


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned operator registration API is absent')
        self.root=LOCAL/uuid.uuid4().hex[:8];self.root.mkdir(parents=True)
        BUDGET.reserve();self.addCleanup(lambda:BUDGET.settle(self.root,getattr(self,'operator_parent_override',None)))
        original=Path.open
        def bounded(path,mode='r',*args,**kwargs):
            if any(x in mode for x in 'wax+'):
                BUDGET.charge(path,path.stat().st_size if path.exists() else 0)
                return Writer(original(path,mode,*args,**kwargs),path)
            return original(path,mode,*args,**kwargs)
        self.enterContext(patch.object(Path,'open',bounded))
        for name in ('socket.socket.connect','socket.getaddrinfo'):
            self.enterContext(patch(name,side_effect=AssertionError('REAL_NETWORK_FORBIDDEN')))
        self.parent=getattr(self,'operator_parent_override',self.root/'DGM');self.parent.mkdir()
        self.operator=self.parent/'codex-conducted-workflow-operator';self.operator.mkdir()
        self.data=self.operator/'prepared-data';self.data.mkdir()
        self.target=self.parent/'codex-conducted-workflow-host'
        self.stage=self.parent/'codex-conducted-workflow-host.preparing'
        self.enterContext(patch.object(api,'_operator_parent',return_value=self.parent))
        self.enterContext(patch.object(host,'_profile_root',return_value=self.target))
        (self.root/'test-case.txt').write_text(self._testMethodName,encoding='utf-8')
        self.make_inputs()
        self.sequence=0

    def put(self,path,value):
        raw=value if type(value) is bytes else C(value)
        path.write_bytes(raw);return dict(bytes=len(raw),sha256=H(raw))

    def make_inputs(self):
        inbox=self.root/'i';bundle=inbox/'b';bundle.mkdir(parents=True)
        lines=['product_type: smartphone','model: SM-A176U','market: US','purpose: synthetic conducted engineering',
            'frequency: 2412 MHz; bandwidth: 20 MHz; on_average_power: 11 dBm; duty_cycle: 50 %; modulation: OFDM; crest_factor: 4 dB']
        suffix=getattr(self,'source_suffix','.txt')
        self.original=bundle/('r'+suffix)
        if suffix=='.pdf':
            from io import BytesIO
            from reportlab.pdfgen import canvas
            stream=BytesIO();document=canvas.Canvas(stream,invariant=1,pageCompression=0)
            cursor=document.beginText(36,760);cursor.setFont('Helvetica',6);cursor.setLeading(12)
            for line in lines:cursor.textLine(line)
            document.drawText(cursor);document.showPage();document.save()
            self.original.write_bytes(stream.getvalue())
        else:self.original.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
        self.store_root=self.root/'s';store=Store(self.store_root)
        try:
            register_source(store,'REG-SYN',inbox,synthetic=True,settle_seconds=1)
            scan_source(store,'REG-SYN',now=100,synthetic_only=True)
            item=scan_source(store,'REG-SYN',now=101,synthetic_only=True)['accepted'][0]
            with store.connection() as con:rev=con.execute('SELECT * FROM intake_revisions WHERE intake_id=?',(item['intake_id'],)).fetchone()
            selection=dict(source_id='REG-SYN',intake_id=item['intake_id'],revision=item['revision'],job_id=item['job_id'],
                revision_fingerprint=rev['fingerprint'],files=json.loads(rev['files_json']))
            self.context=prepare_registered_synthetic_context(store,selection,producer_name='SCRIPTED-REG-MOCK')
            doc=self.context['documents'][0]
            def fact(field,value,line):
                evidence=dict(path=doc['path'],sha256=doc['sha256'],line_start=line,line_end=line,quote=lines[line-1],role='request')
                if suffix=='.pdf':evidence.update(kind='pdf_page',extraction_id=doc['extraction_id'],page_number=1,text_sha256=doc['pages'][0]['text_sha256'])
                return dict(field=field,value=value,status='explicit',evidence=[evidence])
            raw=dict(schema_version=1,producer=dict(kind='model',name='SCRIPTED-REG-MOCK'),identity='single',missing_fields=[],facts=[fact('product_type','smartphone',1),fact('model','SM-A176U',2),fact('market','US',3),fact('purpose','synthetic conducted engineering',4),fact('features',lines[4],5)])
            if suffix=='.pdf':raw.update(schema_version=2,context_id=self.context['analysis_context_id'])
            self.analysis=decode_analysis_response(C(raw),self.context,producer_name='SCRIPTED-REG-MOCK')
            out=build_conducted_plan_from_intake_facts(self.context,self.analysis,expected_revision=1,expected_context_sha256=H(C(self.context)),
                method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
            self.plan=out['plan_input'];self.assertEqual(out['status'],'ready_for_simulation')
        finally:store.close()
        schema=json.loads((ROOT/'docs/fcc/codex_first_decision_contract.json').read_text(encoding='utf-8'))['response_schema']['literal_utf8'].encode()
        payloads={'registered-intake-v1.json':dict(schema_version=1,kind='codex_registered_synthetic_intake',scenario_id='REG-CASE',synthetic=True,registered_intake=selection),
            'analysis.json':self.analysis,'plan-input.json':self.plan,'catalog.json':(ROOT/'virtual_profiles/sm_a176u_unlicensed.json').read_bytes(),'response-schema.json':schema}
        files={name:self.put(self.data/name,value) for name,value in payloads.items()}
        exe=self.root/'codex.exe';exe.write_bytes(b'KNOWN_MOCK_INSTALLED_EXECUTABLE_BOUNDARY')
        self.q=dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=1)
        self.meta=dict(schema_version=1,kind='codex_conducted_workflow_prepared_data',scenario_id='REG-CASE',requested_model='gpt-6-astra',journal_id='REG-JOURNAL',permit_id='REG-P1',
            registered_input_root=str(bundle),store_root=str(self.store_root),executable=str(exe),expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            quantity=self.q,allowed_tools=['dut.start','sensor.acquire','sensor.read','advance1','stop'],measurement_ref='event:17',files=files)
        self.authority=dict(schema_version=1,kind='codex_root_conducted_workflow_manual_preparation',authority_source=dict(kind='direct_human_instructions_to_this_root_thread',
            instruction_reference='AUTHORED_TEST_ONLY_NOT_A_HUMAN_GRANT',authority_is_not_inferred_from_uploaded_documents_or_model_output=True),
            manual_preparation_reference='AUTHORED_MANUAL_PREP_FIXTURE_ONLY',action='prepare_one_registered_synthetic_conducted_workflow_profile',
            scope=dict(allowed_models=['gpt-6.1-sol','gpt-6-astra'],maximum_workflows=1,maximum_model_processes=8,loop_seconds=180,producer_seconds=60,automatic_retries=0,
                output_bytes=262144,evidence_files=192,evidence_bytes=33554432,synthetic_only=True,hardware_network_output_motion_submission=False,scope_is_existing_delegation_not_new_global_budget=True),
            prepared_manifest_sha256='',inherited_history=dict(actual_codex_model_processes=17,known_total_before_this_host=17,unknown_usage_components=None,usage_complete=False,cost=None,
                provenance_level='previous_verified_root_rollup_not_fresh_original_receipt_reaudit',source_rollup=dict(path='AUTHORED_TEST_ONLY',bytes=1,sha256=H(b'fixture')),
                published_source=dict(commit='ab45019e411fbd9ebde1ec091acb6e054d83af1b',path='fixture-only',bytes=1,sha256=H(b'fixture'))))
        self.bind()

    def bind(self):
        self.authority['prepared_manifest_sha256']=self.put(self.operator/'prepared-inputs-v1.json',self.meta)['sha256']
        self.put(self.operator/'root-delegation-v1.json',self.authority)

    def call(self,**changes):
        self.sequence+=1;options=dict(scenario_id='REG-CASE',requested_model='gpt-6-astra');options.update(changes)
        result=api.prepare_registered_conducted_workflow(**options)
        self.put(self.root/('result-'+str(self.sequence)+'.json'),result);return result

    def make_completed_inputs(self):
        """Genuine disposable completion; never make a completed row queued again."""
        store=Store.open_existing(str(self.store_root))
        try:
            if getattr(self,'source_suffix','.txt')=='.pdf':
                response=respond(store,'AUTHORED-PDF-PROCEED','proceed',intake_id=self.context['intake_id'])
                self.assertEqual(response['status'],'recorded')
            job=claim_job(store,'completed-registration-fixture',now=102)
            if getattr(self,'source_suffix','.txt')=='.pdf':
                claimed={key:job[key] for key in self.context}
                self.analysis=decode_analysis_response(C(self.analysis),claimed,producer_name='SCRIPTED-REG-MOCK')
            # The same already-decoded authored response belongs to this job;
            # a convenience text provider would omit its non-FIELDS RF line.
            complete_job(store,job['job_id'],job['token'],self.analysis,now=103)
        finally:store.close()
        self.method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output')
        current=read_current_conducted_plan_from_facts(self.store_root,job['intake_id'],method=self.method)
        self.context=current['context'];self.analysis=current['analysis'];self.plan=current['facts_plan']['plan_input']
        self.assertEqual(current['facts_plan']['status'],'ready_for_simulation')
        self.meta['files']['analysis.json']=self.put(self.data/'analysis.json',self.analysis)
        self.meta['files']['plan-input.json']=self.put(self.data/'plan-input.json',self.plan)
        self.meta.update(schema_version=3,context_scope='completed_current_provided',measurement_ref=None,
            measurement_selection_policy=dict(schema_version=1,kind='unique_same_run_sensor_acquisition'))
        self.bind()

    def completed_host_dependency(self,root,config,scenario,owned):
        """Named _prepare dependency seam only; the native data gate stays real."""
        self.assertEqual(scenario,'REG-CASE')
        workflow=json.loads((root/'registered-workflow.json').read_bytes())
        self.assertEqual(H(C(workflow)),config['workflow_sha256'])
        owned['store']=Store.open_existing(config['store_root'])
        current=read_current_conducted_plan_from_facts(owned['store'].root,self.context['intake_id'],method=self.method)
        return workflow,current['context'],current['analysis'],current['facts_plan']['plan_input'],(root/'response-schema.json').read_bytes()

    def test_completed_current_txt_is_verified_with_named_host_dependency(self):
        self.make_completed_inputs()
        originals={p:p.read_bytes() for p in [self.store_root/'lab.sqlite3',self.root/'i/b/r.txt']}
        native={p:(p.stat().st_dev,p.stat().st_ino,p.stat().st_nlink,p.stat().st_size,p.stat().st_mtime_ns,p.stat().st_ctime_ns) for p in originals}
        with patch.object(host,'_prepare',side_effect=self.completed_host_dependency) as prepared,patch.object(api,'prepare_registered_synthetic_context',side_effect=AssertionError('QUEUED_G3_FORBIDDEN')):
            result=self.call()
        self.assertEqual(result['status'],'prepared');self.assertEqual(prepared.call_count,1)
        workflow=json.loads((self.target/'registered-workflow.json').read_bytes())
        self.assertEqual(len(workflow),14);self.assertEqual(workflow['schema_version'],3)
        self.assertEqual(workflow['context_scope'],'completed_current_provided');self.assertIsNone(workflow['measurement_ref'])
        self.assertEqual(workflow['context_sha256'],H(C(self.context)));self.assertEqual(workflow['analysis_sha256'],H(C(self.analysis)))
        self.assertEqual(workflow['plan_input_sha256'],H(C(self.plan)));self.assertEqual(len(self.meta),16)
        self.assertEqual({p:p.read_bytes() for p in originals},originals)
        self.assertEqual({p:(p.stat().st_dev,p.stat().st_ino,p.stat().st_nlink,p.stat().st_size,p.stat().st_mtime_ns,p.stat().st_ctime_ns) for p in originals},native)

    def test_completed_foreign_source_root_is_rejected_before_staging(self):
        self.make_completed_inputs();foreign=self.root/'foreign';foreign.mkdir();self.put(foreign/'r.txt',(self.root/'i/b/r.txt').read_bytes())
        self.meta['registered_input_root']=str(foreign);self.bind()
        with patch.object(host,'_prepare',side_effect=AssertionError('HOST_BEFORE_DATA_GATE')) as prepared:result=self.call()
        self.assertEqual(result['status'],'not_prepared');self.assertEqual(prepared.call_count,0)
        self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())
        self.assertEqual(result['errors'][0]['code'],'codex_conducted_workflow_registration_binding_mismatch')

    def test_completed_other_active_job_is_rejected_before_staging(self):
        self.make_completed_inputs();bundle=self.root/'i/other';bundle.mkdir();self.put(bundle/'new.txt',b'product_type: lab_receiver\n')
        store=Store.open_existing(str(self.store_root))
        try:scan_source(store,'REG-SYN',now=110,synthetic_only=True);scan_source(store,'REG-SYN',now=111,synthetic_only=True)
        finally:store.close()
        with patch.object(host,'_prepare',side_effect=AssertionError('HOST_BEFORE_DATA_GATE')) as prepared:result=self.call()
        self.assertEqual(result['status'],'not_prepared');self.assertEqual(prepared.call_count,0);self.assertFalse(self.stage.exists())
        self.assertEqual(result['errors'][0]['code'],'codex_conducted_workflow_registration_store_not_dedicated')

    def test_completed_canonical_bytes_cannot_replace_current_analysis(self):
        self.make_completed_inputs();changed=copy.deepcopy(self.analysis);changed['producer']['name']='DIFFERENT-SUPPLIED-ANALYSIS'
        self.meta['files']['analysis.json']=self.put(self.data/'analysis.json',changed);self.bind()
        with patch.object(host,'_prepare',side_effect=AssertionError('HOST_BEFORE_DATA_GATE')) as prepared:result=self.call()
        self.assertEqual(result['status'],'not_prepared');self.assertEqual(prepared.call_count,0);self.assertFalse(self.stage.exists())
        self.assertEqual(result['errors'][0]['code'],'codex_conducted_workflow_registration_binding_mismatch')

    def test_completed_scope_and_policy_are_closed_before_staging(self):
        self.make_completed_inputs();self.meta['context_scope']='original_model_prompt';self.bind()
        with patch.object(host,'_prepare',side_effect=AssertionError('HOST_BEFORE_DATA_GATE')) as prepared:result=self.call()
        self.assertEqual(result['status'],'not_prepared');self.assertEqual(prepared.call_count,0);self.assertFalse(self.stage.exists())
        self.assertEqual(result['errors'][0]['code'],'codex_conducted_workflow_registration_data_invalid')

    def test_completed_host_return_cannot_hide_post_prepare_drift(self):
        self.make_completed_inputs()
        def drift(*args):
            ready=self.completed_host_dependency(*args)
            with sqlite3.connect(self.store_root/'lab.sqlite3') as con:con.execute('UPDATE intakes SET revision=revision+1 WHERE intake_id=?',(self.context['intake_id'],))
            return ready
        with patch.object(host,'_prepare',side_effect=drift) as prepared:result=self.call()
        self.assertEqual(prepared.call_count,1);self.assertEqual(result['status'],'failed')
        self.assertTrue((self.stage/'workflow-continuation.sqlite3').exists());self.assertFalse(self.target.exists())

    def test_completed_first_current_control_survives_late_close(self):
        self.make_completed_inputs();control=MemoryError('FIRST_CURRENT_CONTROL');close=api._IO.close_dirs
        def late(obj):close(obj);raise OSError('LATE_DIRECTORY_CLOSE')
        with patch('labflow.intake_current_facts_plan.read_current_conducted_plan_from_facts',side_effect=control),patch.object(api._IO,'close_dirs',late):
            with self.assertRaises(MemoryError) as got:self.call()
        self.assertIs(got.exception,control);self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())

    def test_completed_unsupported_host_dependency_retains_staging(self):
        self.make_completed_inputs()
        def unsupported_host(root,config,scenario,owned):
            self.assertEqual(scenario,'REG-CASE')
            self.assertEqual(json.loads((root/'registered-workflow.json').read_bytes())['schema_version'],3)
            raise NotImplementedError('AUTHORED_SCHEMA3_HOST_UNSUPPORTED')
        with patch.object(host,'_prepare',side_effect=unsupported_host) as prepared:
            result=self.call()
        self.assertEqual(prepared.call_count,1)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['phase'],'current')
        self.assertTrue(self.stage.exists());self.assertFalse(self.target.exists())
        self.assertFalse((self.operator/'preparation-complete-v1.json').exists())

    def test_completed_closed_metadata_rejects_ref_policy_extra_and_native_version(self):
        self.make_completed_inputs();original=copy.deepcopy(self.meta)
        changes=[dict(measurement_ref='event:17'),dict(measurement_selection_policy=None),
            dict(measurement_selection_policy=dict(schema_version=True,kind='unique_same_run_sensor_acquisition')),
            dict(schema_version=True),dict(context_scope=None),dict(extra=True)]
        with patch.object(host,'_prepare',side_effect=AssertionError('HOST_BEFORE_DATA_GATE')) as prepared:
            for change in changes:
                with self.subTest(change=change):
                    self.meta=copy.deepcopy(original);self.meta.update(change);self.bind();result=self.call()
                    self.assertEqual(result['status'],'not_prepared');self.assertFalse(self.stage.exists())
        self.assertEqual(prepared.call_count,0);self.assertFalse(self.target.exists())

    def test_completed_old_context_sha_and_noncanonical_plan_reject_before_staging(self):
        self.make_completed_inputs();original=copy.deepcopy(self.plan)
        changed=copy.deepcopy(original);changed['binding']['context_sha256']='0'*64
        for raw in (C(changed),C(original)+b'\n'):
            with self.subTest(sha=H(raw)):
                self.meta['files']['plan-input.json']=self.put(self.data/'plan-input.json',raw);self.bind()
                with patch.object(host,'_prepare',side_effect=AssertionError('HOST_BEFORE_DATA_GATE')) as prepared:result=self.call()
                self.assertEqual(result['status'],'not_prepared');self.assertFalse(self.stage.exists());self.assertEqual(prepared.call_count,0)

    def test_completed_typed_host_wrong_tuple_cannot_publish(self):
        self.make_completed_inputs()
        def wrong(*args):
            values=self.completed_host_dependency(*args);changed=copy.deepcopy(values[1]);changed['instructions']='CALLER-CONTEXT'
            return values[0],changed,*values[2:]
        with patch.object(host,'_prepare',side_effect=wrong):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertEqual(result['phase'],'current')
        self.assertTrue(self.stage.exists());self.assertFalse(self.target.exists())

    def test_completed_host_owned_store_must_be_the_registered_store(self):
        self.make_completed_inputs();other=self.root/'copy-s'
        for path in self.store_root.rglob('*'):
            target=other/path.relative_to(self.store_root)
            if path.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:target.parent.mkdir(parents=True,exist_ok=True);self.put(target,path.read_bytes())
        def copied(*args):
            values=self.completed_host_dependency(*args);owned=args[3]
            owned['store'].close();owned['store']=Store.open_existing(str(other));return values
        with patch.object(host,'_prepare',side_effect=copied):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertEqual(result['phase'],'current')
        self.assertTrue(self.stage.exists());self.assertFalse(self.target.exists())

    def test_completed_first_ordinary_current_failure_survives_late_control(self):
        self.make_completed_inputs();close=api._IO.close_dirs
        def late(obj):close(obj);raise KeyboardInterrupt('LATE_DIRECTORY_CONTROL')
        with patch('labflow.intake_current_facts_plan.read_current_conducted_plan_from_facts',side_effect=ValueError('PRIVATE_CURRENT_ERROR')),patch.object(api._IO,'close_dirs',late):
            result=self.call()
        self.assertEqual(result['status'],'not_prepared');self.assertFalse(self.stage.exists())
        self.assertEqual(result['errors'][0],dict(phase='operator',code='codex_conducted_workflow_registration_native_or_data_rejected'))
        self.assertIn(dict(phase='directory_close',code='codex_conducted_workflow_registration_interrupted'),result['errors'])

    def test_pure_preflight_is_detached_and_not_authority(self):
        before=C([self.context,self.analysis,self.plan,self.q])
        result=api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,quantity=self.q,
            allowed_tools=self.meta['allowed_tools'],measurement_ref='event:17')
        self.assertEqual(result['status'],'validated');self.assertFalse(result['execution_authority'])
        self.assertFalse(self.target.exists());self.assertFalse(self.stage.exists());self.assertEqual(before,C([self.context,self.analysis,self.plan,self.q]))
        for control in (KeyboardInterrupt(),SystemExit(9),GeneratorExit(),MemoryError()):
            with patch.object(api,'build_conducted_twin_plan_input',side_effect=control):
                with self.assertRaises(type(control)) as got:
                    api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,quantity=self.q,allowed_tools=self.meta['allowed_tools'],measurement_ref='event:17')
            self.assertIs(got.exception,control)

    def test_missing_native_authority_does_not_publish(self):
        original=api._read
        def missing(path,cap):
            if path.name=='root-delegation-v1.json':raise FileNotFoundError('PRIVATE')
            return original(path,cap)
        with patch.object(api,'_read',side_effect=missing):result=self.call()
        self.assertEqual(result['status'],'not_prepared');self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())

    def test_caller_approval_paths_or_environment_cannot_grant(self):
        with self.assertRaises(TypeError):self.call(approval=True)
        with self.assertRaises(TypeError):self.call(profile_root=self.target)
        out,err=io.StringIO(),io.StringIO()
        with patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):code=api.main(['--scenario-id','REG-CASE','--model','gpt-6-astra','--approval','true'])
        self.assertEqual(code,2);self.assertFalse(self.stage.exists())

    def test_wrong_scope_budget_or_model_is_not_prepared(self):
        self.authority['scope']['maximum_model_processes']=9;self.bind()
        self.assertEqual(self.call()['status'],'not_prepared')
        self.authority['scope']['maximum_model_processes']=8;self.bind()
        self.assertEqual(self.call(requested_model='gpt-6.1-sol')['status'],'not_prepared');self.assertFalse(self.stage.exists())

    def test_native_prepare_exact_host_files_and_genuine_consumption_model0(self):
        result=self.call();self.assertEqual(result['status'],'prepared');self.assertFalse(self.stage.exists())
        required=set('root-continuation-anchor.json operator-control.json registered-intake-v1.json registered-workflow.json analysis.json plan-input.json catalog.json response-schema.json cancel-request.json workflow-continuation.sqlite3'.split())
        self.assertEqual({p.name for p in self.target.iterdir() if p.is_file()},required)
        with sqlite3.connect(self.target/'workflow-continuation.sqlite3') as con:
            rows=con.execute('SELECT kind,payload FROM codex_conducted_workflow_history ORDER BY seq').fetchall()
        self.assertEqual([x[0] for x in rows],['baseline','permit']);self.assertEqual(json.loads(rows[0][1])['inherited_history'],self.authority['inherited_history'])
        self.put(self.root/'prepared-sql-before-host.sqlite3',(self.target/'workflow-continuation.sqlite3').read_bytes())
        script=self.root/'version.py';script.write_text("import os;os.write(1,b'known-mock-unsupported-version\\n')",encoding='utf-8')
        seen=[];children=[]
        def spawn(argv,**options):
            seen.append(list(argv));self.assertEqual(argv[1:],['--version'])
            child=REAL_POPEN([sys.executable,'-B',str(script)],**options);children.append(child);return child
        out,err=io.StringIO(),io.StringIO()
        with patch('labflow.codex_cli_response.subprocess.Popen',side_effect=spawn),patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):
            code=host.main(['--scenario-id','REG-CASE','--model','gpt-6-astra'])
        frame=json.loads(out.getvalue() or err.getvalue());self.put(self.root/'host-consumption.json',frame)
        self.assertIn(code,(4,5));self.assertEqual(frame['history']['local_model_processes'],0);self.assertEqual(len(seen),1)
        self.assertTrue(all(p.poll() is not None for p in children));self.assertEqual(self.call()['status'],'not_prepared')

    def test_changed_source_or_file_pin_does_not_prepare(self):
        (self.data/'analysis.json').write_bytes(C(self.analysis)+b' ')
        self.assertEqual(self.call()['status'],'not_prepared');self.assertFalse(self.stage.exists())

    def test_existing_final_and_staging_are_never_replaced(self):
        self.target.mkdir();self.stage.mkdir();self.put(self.target/'canary',b'FINAL');self.put(self.stage/'canary',b'STAGE')
        self.assertEqual(self.call()['status'],'not_prepared');self.assertEqual((self.target/'canary').read_bytes(),b'FINAL');self.assertEqual((self.stage/'canary').read_bytes(),b'STAGE')

    def test_zero_history_and_bool_quantity_are_not_filled(self):
        self.authority['inherited_history']['actual_codex_model_processes']=0;self.bind()
        self.assertEqual(self.call()['status'],'not_prepared')
        self.authority['inherited_history']['actual_codex_model_processes']=17;self.meta['quantity']['loss_compensation_sign']=True;self.bind()
        self.assertEqual(self.call()['status'],'not_prepared');self.assertFalse(self.stage.exists())

    def boundary_partial_file_write_preserves_staging(self):
        original=api._native._write_all
        def partial(fd,data,code):
            os.write(fd,data[:9]);raise OSError('PRIVATE_WRITE_FAILURE')
        with patch.object(api._native,'_write_all',side_effect=partial):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertTrue(self.stage.is_dir());self.assertFalse(self.target.exists())
        self.assertEqual((self.operator/'preparation-record-v1.json').stat().st_size,9)
        self.assertEqual(self.call()['status'],'not_prepared')

    def boundary_fsync_failure_never_publishes(self):
        with patch.object(api.os,'fsync',side_effect=OSError('PRIVATE_SYNC')):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertFalse(self.target.exists());self.assertTrue(self.stage.exists())

    def boundary_sql_commit_failure_keeps_new_database(self):
        connect=api.sqlite3.connect
        def wrap(*args,**kwargs):
            con=connect(*args,**kwargs)
            if 'workflow-continuation.sqlite3' not in str(args[0]):return con
            class Proxy:
                def commit(self):raise sqlite3.OperationalError('PRIVATE_COMMIT')
                def __getattr__(self,key):return getattr(con,key)
            return Proxy()
        with patch.object(api.sqlite3,'connect',side_effect=wrap):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertTrue((self.stage/'workflow-continuation.sqlite3').exists());self.assertFalse(self.target.exists())

    def boundary_sql_close_first_control_is_preserved(self):
        control=MemoryError('FIRST_SQL_CONTROL');close=api._close_sql
        def closing(con):close(con);raise control
        with patch.object(api,'_close_sql',side_effect=closing):
            with self.assertRaises(MemoryError) as got:self.call()
        self.assertIs(got.exception,control);self.assertTrue(self.stage.exists());self.assertFalse(self.target.exists())

    def boundary_body_control_survives_later_native_close(self):
        control=KeyboardInterrupt('FIRST_WRITE_CONTROL');close=api._IO.close_file
        def closing(obj,token):close(obj,token);raise OSError('LATER_CLOSE')
        with patch.object(api._native,'_write_all',side_effect=control),patch.object(api._IO,'close_file',closing):
            with self.assertRaises(KeyboardInterrupt) as got:self.call()
        self.assertIs(got.exception,control);self.assertFalse(self.target.exists())

    def boundary_native_publish_collision_never_overwrites_final(self):
        publish=api._publish_directory
        def collision(*args):
            self.target.mkdir();self.put(self.target/'canary',b'OTHER_FINAL');return publish(*args)
        with patch.object(api,'_publish_directory',side_effect=collision):result=self.call()
        self.assertEqual(result['status'],'publication_uncertain');self.assertTrue(self.stage.exists())
        self.assertEqual((self.target/'canary').read_bytes(),b'OTHER_FINAL')

    def boundary_post_publish_close_is_uncertain_not_success(self):
        close=api._IO.close_dirs
        def closing(obj):close(obj);raise OSError('LATE_DIR_CLOSE')
        with patch.object(api._IO,'close_dirs',closing):result=self.call()
        self.assertEqual(result['status'],'publication_uncertain');self.assertTrue(self.target.is_dir());self.assertFalse(self.stage.exists())

    def boundary_current_store_c1_failure_leaves_prefix(self):
        control=RuntimeError('CURRENT_SNAPSHOT_CHANGED')
        with patch.object(api._host,'_prepare',side_effect=control):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertTrue((self.stage/'workflow-continuation.sqlite3').exists());self.assertFalse(self.target.exists())

    def boundary_staging_exists_and_source_overlap_cannot_prepare(self):
        self.meta['registered_input_root']=str(self.operator);self.bind()
        self.assertEqual(self.call()['status'],'not_prepared');self.assertFalse(self.stage.exists())
        self.meta['registered_input_root']=str(self.root/'i/b');self.bind()
        self.stage.mkdir();self.put(self.stage/'guard',b'KEEP_PARTIAL')
        self.assertEqual(self.call()['status'],'not_prepared');self.assertEqual((self.stage/'guard').read_bytes(),b'KEEP_PARTIAL')


    def selection_policy(self):
        return dict(schema_version=1,kind='unique_same_run_sensor_acquisition')

    def selection_preflight_v2_preserves_data_only_dto_and_legacy_pins(self):
        self.assertIn('measurement_selection_policy',inspect.signature(api.preflight_conducted_workflow_inputs).parameters,
            'The explicit selection preflight keyword has not been implemented')
        before=C([self.context,self.analysis,self.plan,self.q]);options=dict(quantity=self.q,allowed_tools=self.meta['allowed_tools'])
        legacy=api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,measurement_ref='event:17',**options)
        explicit_none=api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,measurement_ref='event:17',measurement_selection_policy=None,**options)
        selected=api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,measurement_ref=None,measurement_selection_policy=self.selection_policy(),**options)
        self.assertEqual(C(legacy),C(explicit_none));self.assertEqual(C(legacy),C(selected))
        self.assertEqual(set(selected),set('schema_version kind status pins gaps failure execution_authority'.split()))
        self.assertEqual(selected['status'],'validated');self.assertFalse(selected['execution_authority'])
        self.assertEqual(set(selected['pins']),set('context_sha256 analysis_sha256 plan_input_sha256 source_settings_sha256 quantity_sha256'.split()))
        self.assertEqual(C([self.context,self.analysis,self.plan,self.q]),before)
        self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())
        self.put(self.root/'selection-preflight-observation.json',dict(legacy=legacy,explicit_none=explicit_none,selected=selected,io_or_execution=False))

    def selection_preflight_policy_requires_native_exact2_and_explicit_null_ref(self):
        self.assertIn('measurement_selection_policy',inspect.signature(api.preflight_conducted_workflow_inputs).parameters)
        class NonNative(dict):pass
        invalid=[True,{},[],dict(schema_version=True,kind='unique_same_run_sensor_acquisition'),
            dict(schema_version=1.0,kind='unique_same_run_sensor_acquisition'),dict(schema_version=1,kind='other'),
            dict(schema_version=1,kind='unique_same_run_sensor_acquisition',approved=True),NonNative(self.selection_policy())]
        rows=[];options=dict(quantity=self.q,allowed_tools=self.meta['allowed_tools'])
        for value in invalid:
            result=api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,measurement_ref=None,measurement_selection_policy=value,**options)
            self.assertEqual(result['status'],'invalid');self.assertIsNone(result['pins']);self.assertFalse(result['execution_authority'])
            rows.append(dict(input_type=type(value).__name__,result=result))
        for ref,policy in [('event:17',self.selection_policy()),(None,None)]:
            result=api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,measurement_ref=ref,measurement_selection_policy=policy,**options)
            self.assertEqual(result['status'],'invalid');rows.append(dict(ref=ref,policy=policy,result=result))
        control=MemoryError('FIRST_EXPLICIT_PREFLIGHT_CONTROL')
        with patch.object(api,'build_conducted_twin_plan_input',side_effect=control):
            with self.assertRaises(MemoryError) as got:
                api.preflight_conducted_workflow_inputs(self.context,self.analysis,self.plan,measurement_ref=None,measurement_selection_policy=self.selection_policy(),**options)
        self.assertIs(got.exception,control);self.put(self.root/'policy-rejections.json',rows)

    def selection_publish_v2_native_profile_matches_trusted_pin_and_host_prepare(self):
        self.meta.update(schema_version=2,measurement_ref=None,measurement_selection_policy=self.selection_policy());self.bind()
        manifest_raw=(self.operator/'prepared-inputs-v1.json').read_bytes();source_raw=(self.operator/'root-delegation-v1.json').read_bytes()
        with patch.object(host,'main',side_effect=AssertionError('NO_HOST_RUN')),patch.object(subprocess,'Popen',side_effect=AssertionError('NO_CHILD_RUN')):
            result=self.call()
        self.assertEqual(result['status'],'prepared');self.assertEqual(len(result),11);self.assertEqual(len(result['files']),10)
        self.assertFalse(self.stage.exists());self.assertTrue(self.target.is_dir())
        workflow=json.loads((self.target/'registered-workflow.json').read_bytes())
        self.assertEqual(workflow['schema_version'],2);self.assertEqual(len(workflow),13)
        self.assertIsNone(workflow['measurement_ref']);self.assertEqual(C(workflow['measurement_selection_policy']),C(self.meta['measurement_selection_policy']))
        self.assertEqual(result['operator_source'],dict(bytes=len(source_raw),sha256=H(source_raw)))
        complete=json.loads((self.operator/'preparation-complete-v1.json').read_bytes())
        self.assertEqual(complete['prepared_input'],dict(bytes=len(manifest_raw),sha256=H(manifest_raw)))
        self.assertEqual(self.authority['prepared_manifest_sha256'],H(manifest_raw));self.assertEqual(complete['files'],result['files'])
        config=json.loads((self.target/'operator-control.json').read_bytes());self.assertEqual(config['workflow_sha256'],H(C(workflow)))
        before={p.name:p.read_bytes() for p in self.target.iterdir() if p.is_file()};owned=dict(store=None)
        try:prepared=host._prepare(self.target,config,'REG-CASE',owned)
        finally:
            if owned['store'] is not None:owned['store'].close()
        self.assertEqual(C(prepared[0]),C(workflow));self.assertEqual(C(prepared[3]),C(self.plan))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.target.iterdir() if p.is_file()})
        for leaf,pin in result['files'].items():self.assertEqual(dict(bytes=len(before[leaf]),sha256=H(before[leaf])),pin)
        con=sqlite3.connect((self.target/'workflow-continuation.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True)
        try:rows=con.execute('SELECT kind,payload FROM codex_conducted_workflow_history ORDER BY seq').fetchall()
        finally:con.close()
        self.assertEqual([row[0] for row in rows],['baseline','permit'])
        self.assertEqual(json.loads(rows[0][1])['inherited_history'],self.authority['inherited_history'])
        self.assertEqual(json.loads(rows[1][1])['workflow_sha256'],config['workflow_sha256'])
        self.assertFalse(any((self.target/'runs/REG-P1').iterdir()))
        self.put(self.root/'published-v2-binding.json',dict(result=result,workflow=workflow,manifest_pin=complete['prepared_input'],
            host_prepare_same_snapshot=True,host_dispatches=0,child_processes=0,sql_rows=2))
        first_sql=before['workflow-continuation.sqlite3'];again=self.call()
        self.assertEqual(again['status'],'not_prepared');self.assertEqual((self.target/'workflow-continuation.sqlite3').read_bytes(),first_sql)

    def selection_metadata_closed_versions_and_policy_fail_before_staging(self):
        original=copy.deepcopy(self.meta);v2=copy.deepcopy(original)
        v2.update(schema_version=2,measurement_ref=None,measurement_selection_policy=self.selection_policy())
        cases=[]
        def add(label,source,**changes):
            value=copy.deepcopy(source);value.update(changes);cases.append((label,value))
        add('v1-policy',original,measurement_selection_policy=self.selection_policy())
        add('v1-null',original,measurement_ref=None)
        missing=copy.deepcopy(v2);missing.pop('measurement_selection_policy');cases.append(('v2-missing-policy',missing))
        add('v2-null-policy',v2,measurement_selection_policy=None)
        add('v2-null-policy-with-string-ref',v2,measurement_selection_policy=None,measurement_ref='event:17')
        add('v2-string-ref',v2,measurement_ref='event:17')
        add('v2-extra-field',v2,approved=True)
        for version in (True,2.0,3):add('version-'+str(version),v2,schema_version=version)
        for index,policy in enumerate((True,{},[],dict(schema_version=True,kind='unique_same_run_sensor_acquisition'),
                dict(schema_version=1.0,kind='unique_same_run_sensor_acquisition'),dict(schema_version=1,kind='other'),
                dict(schema_version=1,kind='unique_same_run_sensor_acquisition',approved=True))):
            add('policy-'+str(index),v2,measurement_selection_policy=policy)
        observations=[]
        for label,value in cases:
            self.meta=value;self.bind();result=self.call()
            self.assertEqual(result['status'],'not_prepared');self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())
            self.assertIsNone(result['profile']);self.assertEqual(result['files'],{})
            observations.append(dict(label=label,metadata=value,receipt=result))
        self.put(self.root/'metadata-rejections.json',observations)

    def selection_manifest_sha_and_existing_authority_scope_cannot_be_inferred(self):
        self.meta.update(schema_version=2,measurement_ref=None,measurement_selection_policy=self.selection_policy());self.bind()
        before=(self.operator/'root-delegation-v1.json').read_bytes()
        self.meta['measurement_selection_policy']['kind']='other';self.put(self.operator/'prepared-inputs-v1.json',self.meta)
        changed=self.call();self.assertEqual(changed['status'],'not_prepared')
        self.assertEqual((self.operator/'root-delegation-v1.json').read_bytes(),before)
        self.assertTrue(changed['errors'][0]['code'].endswith('binding_mismatch'))
        self.meta['measurement_selection_policy']=self.selection_policy();self.authority['scope']['maximum_model_processes']=9;self.bind()
        expanded=self.call();self.assertEqual(expanded['status'],'not_prepared')
        self.assertFalse(self.stage.exists());self.assertFalse(self.target.exists())
        self.assertEqual(expanded['verification']['authority_scope'],'not_validated')
        self.put(self.root/'trusted-binding-rejections.json',dict(raw_manifest_change=changed,scope_expansion=expanded,
            caller_metadata_is_authority=False,real_operator_record_created=False))

    def selection_v2_first_ordinary_failure_keeps_partial_sql_before_later_control(self):
        self.meta.update(schema_version=2,measurement_ref=None,measurement_selection_policy=self.selection_policy());self.bind()
        self.first_failure_sql_sync_before_directory_control(MemoryError('LATER_V2_DIRECTORY_CONTROL'))

    def selection_v2_first_control_identity_survives_later_directory_error(self):
        self.meta.update(schema_version=2,measurement_ref=None,measurement_selection_policy=self.selection_policy());self.bind()
        primary=MemoryError('FIRST_V2_SQL_CLOSE_CONTROL');close_sql=api._close_sql;close_dirs=api._IO.close_dirs
        counts=dict(sql_close=0,directory_close=0)
        def sql_close(con):counts['sql_close']+=1;close_sql(con);raise primary
        def dirs(obj):counts['directory_close']+=1;close_dirs(obj);raise OSError('LATER_V2_DIRECTORY_CLOSE')
        with patch.object(api,'_close_sql',side_effect=sql_close),patch.object(api._IO,'close_dirs',dirs), \
                patch.object(api,'_publish_directory',side_effect=AssertionError('NO_PUBLISH_AFTER_CONTROL')):
            with self.assertRaises(MemoryError) as got:self.call()
        self.assertIs(got.exception,primary);self.assertEqual(counts,dict(sql_close=1,directory_close=1))
        self.assertTrue((self.stage/'workflow-continuation.sqlite3').is_file());self.assertFalse(self.target.exists())
        marker=json.loads((self.operator/'preparation-failure-v1.json').read_bytes())
        self.assertEqual(marker['phase'],'sql');self.assertTrue(marker['code'].endswith('interrupted'))
        self.put(self.root/'v2-first-control-observation.json',dict(first_control_same_object=True,counts=counts,failure_marker=marker,
            retained_sql_pin=dict(bytes=(self.stage/'workflow-continuation.sqlite3').stat().st_size,sha256=H((self.stage/'workflow-continuation.sqlite3').read_bytes())),publish0=True))

    def first_failure_sql_sync_before_directory_control(self,control):
        primary=OSError('AUTHORED_FIRST_SQL_FSYNC_FAILURE')
        database=api._IO.database;fsync=api.os.fsync;close_dirs=api._IO.close_dirs
        calls=dict(database_active=False,sql_fsync_faults=0,directory_close=0)
        def sql(obj,*args,**kwargs):
            calls['database_active']=True
            try:return database(obj,*args,**kwargs)
            finally:calls['database_active']=False
        def sync(fd):
            if calls['database_active']:
                calls['sql_fsync_faults']+=1
                raise primary
            return fsync(fd)
        def closing(obj):
            calls['directory_close']+=1
            close_dirs(obj)
            raise control
        escaped=result=None
        with patch.object(api._IO,'database',sql),patch.object(api.os,'fsync',sync), \
                patch.object(api._IO,'close_dirs',closing), \
                patch.object(api,'_publish_directory',side_effect=AssertionError('NO_PUBLISH_AFTER_SQL_FAILURE')):
            try:result=self.call()
            except BaseException as observed:escaped=observed
        sql_path=self.stage/'workflow-continuation.sqlite3'
        self.assertTrue(sql_path.is_file());raw=sql_path.read_bytes()
        con=sqlite3.connect(sql_path.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:kinds=[row[0] for row in con.execute('SELECT kind FROM codex_conducted_workflow_history ORDER BY seq')]
        finally:con.close()
        failure=json.loads((self.operator/'preparation-failure-v1.json').read_bytes())
        outcome=dict(result=result,escaped_type=type(escaped).__name__ if escaped is not None else None,
            escaped_is_later_control=escaped is control,first_error_type=type(primary).__name__,failure_record=failure,
            sql_pin=dict(bytes=len(raw),sha256=H(raw)),sql_kinds=kinds,calls=calls,
            staging_retained=self.stage.exists(),final_absent=not self.target.exists(),real_profile_model_host_calls=0)
        self.put(self.root/'first-failure-observation.json',outcome)
        self.assertEqual(calls,dict(database_active=False,sql_fsync_faults=1,directory_close=1))
        self.assertEqual(kinds,['baseline','permit'])
        self.assertTrue(self.stage.is_dir());self.assertFalse(self.target.exists())
        self.assertIsNone(escaped,'A later directory control replaced the first ordinary SQL fsync failure')
        self.assertEqual(len(result),11)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['phase'],'sql')
        first=dict(phase='sql',code='codex_conducted_workflow_registration_native_or_data_rejected')
        self.assertEqual(result['errors'],[first,dict(phase='directory_close',code='codex_conducted_workflow_registration_interrupted')])
        self.assertEqual(failure['code'],first['code']);self.assertEqual(failure['phase'],'sql')
        self.assertIsNone(result['profile']);self.assertEqual(result['files'],{})
        self.assertEqual(result['verification']['dispatch'],'not_invoked')

    def first_failure_ordinary_sql_sync_survives_later_keyboard_interrupt(self):
        self.first_failure_sql_sync_before_directory_control(KeyboardInterrupt('AUTHORED_LATER_DIRECTORY_CONTROL'))

    def first_failure_ordinary_sql_sync_survives_later_memory_error(self):
        self.first_failure_sql_sync_before_directory_control(MemoryError('AUTHORED_LATER_DIRECTORY_CONTROL'))


class NativeNamespacePathTests(unittest.TestCase):
    def setUp(self):
        self.root=api._operator_parent().parent/'.local'/('dev1-native-path-test-'+uuid.uuid4().hex[:12])
        self.root.mkdir(parents=True)
        self.record=dict(test=self._testMethodName,root=str(self.root),resolved=str(self.root.resolve(strict=True)),models=0)
        def preserve():
            raw=C(self.record);self.assertLessEqual(len(raw),16384)
            (self.root/'observation.json').write_bytes(raw)
        self.addCleanup(preserve)

    def io(self):
        parent=self.root/'DGM';parent.mkdir();io=api._IO(parent)
        self.addCleanup(io.close_dirs);self.addCleanup(io.close_files)
        return io,parent,parent/api._STAGE,parent/api._TARGET

    def test_reinterpreted_parent_with_a_different_native_id_is_rejected(self):
        parent=self.root/'DGM';other=self.root/'different';parent.mkdir();other.mkdir()
        original=Path.resolve
        def resolve(path,*args,**kwargs):
            return original(other,strict=True) if path==parent else original(path,*args,**kwargs)
        self.assertNotEqual(api._native._identity(parent.lstat()),api._native._identity(other.lstat()))
        with patch.object(Path,'resolve',resolve),self.assertRaisesRegex(ValueError,'codex_conducted_workflow_registration_path_invalid'):
            api._IO(parent)
        self.record.update(parent_id=api._native._identity(parent.lstat()),foreign_id=api._native._identity(other.lstat()),rejected=True)

    def test_native_claim_cannot_publish_under_a_different_parent(self):
        io,parent,stage,target=self.io();io.claim(stage);other=self.root/'outside';other.mkdir()
        with self.assertRaisesRegex(ValueError,'codex_conducted_workflow_registration_path_invalid'):
            io.publish(stage,other/target.name)
        self.assertTrue(stage.exists());self.assertFalse(target.exists());self.assertFalse(io.publication_attempted)
        self.record.update(stage_retained=True,publication_attempted=io.publication_attempted,rejected=True)

    def test_changed_final_path_mapping_is_rejected_before_publication(self):
        io,parent,stage,target=self.io();io.claim(stage);original=Path.resolve
        def resolve(path,*args,**kwargs):
            return self.root/'outside'/target.name if path==target else original(path,*args,**kwargs)
        with patch.object(Path,'resolve',resolve),self.assertRaisesRegex(ValueError,'codex_conducted_workflow_registration_path_invalid'):
            io.publish(stage,target)
        self.assertTrue(stage.exists());self.assertFalse(target.exists());self.assertFalse(io.publication_attempted)
        self.record.update(stage_retained=True,publication_attempted=io.publication_attempted,rejected=True)

    def test_actual_junction_parent_remains_rejected(self):
        parent=self.root/'junction';other=self.root/'actual';other.mkdir()
        child=subprocess.run(['cmd.exe','/c','mklink','/J',str(parent),str(other)],capture_output=True,check=True)
        self.assertTrue(parent.lstat().st_file_attributes&0x400)
        with self.assertRaises(ValueError):api._IO(parent)
        self.assertFalse((other/api._STAGE).exists())
        self.record.update(junction_attributes=parent.lstat().st_file_attributes,junction_tag=parent.lstat().st_reparse_tag,
            junction_command_stdout_sha256=H(child.stdout),rejected=True)


class CompletedPdfRegistrationTests(unittest.TestCase):
    """Native PDF extraction, strict schema2 completion, then real registration."""
    def setUp(self):
        self.fixture=RegistrationTests('test_pure_preflight_is_detached_and_not_authority')
        self.fixture.source_suffix='.pdf';self.fixture._testMethodName=self._testMethodName
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.fixture.make_completed_inputs()

    def rejected(self):
        helper=self.fixture
        result=helper.call()
        self.assertEqual(result['status'],'not_prepared')
        self.assertFalse(helper.stage.exists());self.assertFalse(helper.target.exists())
        self.assertEqual(result['verification']['dispatch'],'not_invoked')
        return result

    def test_pdf_wrong_page_citation_rejected_by_native_decoder_and_registration(self):
        helper=self.fixture;bad=copy.deepcopy(helper.analysis)
        bad['facts'][0]['evidence'][0]['text_sha256']='0'*64
        with self.assertRaises(ValueError):decode_analysis_response(C(bad),helper.context,producer_name='SCRIPTED-REG-MOCK')
        helper.meta['files']['analysis.json']=helper.put(helper.data/'analysis.json',bad);helper.bind()
        self.assertEqual(self.rejected()['errors'][0]['code'],'codex_conducted_workflow_registration_binding_mismatch')

    def test_pdf_wrong_analysis_schema_rejected_before_publication(self):
        helper=self.fixture;bad=copy.deepcopy(helper.analysis);bad['schema_version']=1
        helper.meta['files']['analysis.json']=helper.put(helper.data/'analysis.json',bad);helper.bind()
        self.rejected()

    def test_pdf_original_source_drift_rejected_without_replacing_retained_pdf(self):
        helper=self.fixture;retained=helper.context['documents'][0]['sha256']
        helper.original.write_bytes(helper.original.read_bytes()+b'\nAUTHORED_DRIFT')
        self.rejected()
        store=Store.open_existing(str(helper.store_root))
        try:self.assertEqual(H(store.verify_blob(retained).read_bytes()),retained)
        finally:store.close()

    def test_pdf_does_not_enable_legacy_queued_schema1_or_schema2(self):
        helper=self.fixture;helper.meta.pop('context_scope')
        for version in (1,2):
            helper.meta['schema_version']=version
            if version==1:
                helper.meta.pop('measurement_selection_policy',None);helper.meta['measurement_ref']='event:17'
            else:
                helper.meta['measurement_ref']=None
                helper.meta['measurement_selection_policy']=dict(schema_version=1,kind='unique_same_run_sensor_acquisition')
            helper.bind();self.rejected()


if __name__=='__main__':
    if '--completed-current' in sys.argv:
        sys.argv.remove('--completed-current');LOCAL=ROOT/'.local/ccr'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['RegistrationTests.'+name for name in RegistrationTests.__dict__ if name.startswith('test_completed_')])
    elif '--selection-preflight' in sys.argv:
        sys.argv.remove('--selection-preflight');LOCAL=ROOT/'.local/wsr'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['RegistrationTests.selection_preflight_v2_preserves_data_only_dto_and_legacy_pins',
            'RegistrationTests.selection_preflight_policy_requires_native_exact2_and_explicit_null_ref'])
    elif '--selection-publish' in sys.argv:
        sys.argv.remove('--selection-publish');LOCAL=ROOT/'.local/wsr'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['RegistrationTests.selection_publish_v2_native_profile_matches_trusted_pin_and_host_prepare'])
    elif '--selection-boundary' in sys.argv:
        sys.argv.remove('--selection-boundary');LOCAL=ROOT/'.local/wsr'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['RegistrationTests.selection_metadata_closed_versions_and_policy_fail_before_staging',
            'RegistrationTests.selection_manifest_sha_and_existing_authority_scope_cannot_be_inferred',
            'RegistrationTests.selection_v2_first_ordinary_failure_keeps_partial_sql_before_later_control',
            'RegistrationTests.selection_v2_first_control_identity_survives_later_directory_error'])
    elif '--selection-metadata' in sys.argv:
        sys.argv.remove('--selection-metadata');LOCAL=ROOT/'.local/wsr'/uuid.uuid4().hex[:8]
        unittest.main(defaultTest=['RegistrationTests.selection_metadata_closed_versions_and_policy_fail_before_staging'])
    elif '--first-failure' in sys.argv:
        sys.argv.remove('--first-failure')
        unittest.main(defaultTest=['RegistrationTests.'+name for name in RegistrationTests.__dict__ if name.startswith('first_failure_ordinary_')])
    elif '--first-control-legacy' in sys.argv:
        sys.argv.remove('--first-control-legacy')
        unittest.main(defaultTest=['RegistrationTests.boundary_sql_close_first_control_is_preserved',
                                  'RegistrationTests.boundary_body_control_survives_later_native_close'])
    elif '--boundary' in sys.argv:
        sys.argv.remove('--boundary')
        unittest.main(defaultTest=['RegistrationTests.'+name for name in RegistrationTests.__dict__ if name.startswith('boundary_')])
    else:unittest.main()
