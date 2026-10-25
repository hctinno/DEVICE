"""Authored operator records at a substituted OS boundary; real profile/model0."""
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
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
from labflow.intake_jobs import prepare_registered_synthetic_context
from labflow.intake_model_boundary import decode_analysis_response
from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.store import Store,canonical
from labflow import codex_registered_conducted_workflow_host as host
try:api=importlib.import_module('labflow.codex_conducted_workflow_registration')
except ModuleNotFoundError as error:
    if error.name!='labflow.codex_conducted_workflow_registration':raise
    api=None

C=lambda v:canonical(v).encode('utf-8')
H=lambda raw:hashlib.sha256(raw).hexdigest()
LOCAL=ROOT/'.local/reg'/uuid.uuid4().hex
REAL_POPEN=subprocess.Popen

class Budget:
    def __init__(self):self.slots={};self.total=0;self.native=0
    def charge(self,path,size):
        path=Path(os.path.abspath(path));assert path.is_relative_to(LOCAL)
        delta=max(0,size-self.slots.get(path,0))
        assert self.total+delta<=33554432 and len(self.slots)+self.native+(path not in self.slots)<=512,'PROOF_ADMISSION'
        self.slots[path]=max(size,self.slots.get(path,0));self.total+=delta
    def reserve(self):
        assert self.total+2097152<=33554432 and len(self.slots)+self.native+32<=512
        self.total+=2097152;self.native+=32
    def settle(self,folder):
        self.total-=2097152;self.native-=32
        for path in folder.rglob('*'):
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
        BUDGET.reserve();self.addCleanup(lambda:BUDGET.settle(self.root))
        original=Path.open
        def bounded(path,mode='r',*args,**kwargs):
            if any(x in mode for x in 'wax+'):
                BUDGET.charge(path,path.stat().st_size if path.exists() else 0)
                return Writer(original(path,mode,*args,**kwargs),path)
            return original(path,mode,*args,**kwargs)
        self.enterContext(patch.object(Path,'open',bounded))
        for name in ('socket.socket.connect','socket.getaddrinfo'):
            self.enterContext(patch(name,side_effect=AssertionError('REAL_NETWORK_FORBIDDEN')))
        self.parent=self.root/'DGM';self.parent.mkdir()
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
        (bundle/'r.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
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
            def fact(field,value,line):return dict(field=field,value=value,status='explicit',evidence=[dict(path=doc['path'],sha256=doc['sha256'],line_start=line,line_end=line,quote=lines[line-1],role='request')])
            raw=dict(schema_version=1,producer=dict(kind='model',name='SCRIPTED-REG-MOCK'),identity='single',missing_fields=[],facts=[fact('product_type','smartphone',1),fact('model','SM-A176U',2),fact('market','US',3),fact('purpose','synthetic conducted engineering',4),fact('features',lines[4],5)])
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


if __name__=='__main__':
    if '--first-failure' in sys.argv:
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
