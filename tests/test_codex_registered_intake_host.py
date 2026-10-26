"""Disposable native control/Store/history; genuine D2, known Python child only."""
import copy
import ctypes
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source
from labflow.store import Store, canonical


REAL_POPEN = subprocess.Popen
ANCHOR = 'root-continuation-anchor-20261026-v1.json'
TABLE = 'CREATE TABLE codex_intake_history (seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,permit_id TEXT,payload TEXT NOT NULL,UNIQUE(kind,permit_id))'
CHILD = r'''
import json,os,sys
from pathlib import Path
def deny(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):raise AssertionError('FAKE_CHILD_NETWORK_FORBIDDEN')
sys.addaudithook(deny)
if sys.argv[1]=='version':
    os.write(1,b'codex-cli 0.163.0-alpha.11.2\n');sys.exit(0)
prompt=json.loads(sys.stdin.buffer.read())
schema=json.loads((Path.cwd().parent/'response-schema.json').read_bytes())
analysis=dict(schema_version=1,producer=prompt['expected_producer'],identity='unknown',facts=[],
              missing_fields=schema['properties']['missing_fields']['items']['enum'])
wire=json.dumps(analysis,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
Path(sys.argv[2]).write_bytes(wire)
events=[dict(type='thread.started',thread_id='known-fake-native-child'),dict(type='turn.started'),
 dict(type='item.completed',item=dict(id='a1',type='agent_message',text=wire.decode('utf-8'))),
 dict(type='turn.completed',usage=dict(input_tokens=10,cached_input_tokens=2,output_tokens=3))]
os.write(1,b''.join(json.dumps(e,separators=(',',':')).encode()+b'\n' for e in events))
'''

def C(value):
    return canonical(value).encode('utf-8')

def H(value):
    return hashlib.sha256(value).hexdigest()


class RegisteredNativeHostTests(unittest.TestCase):
    maxDiff = None
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='native-host-authored-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.control = self.root/'native-control';self.control.mkdir()
        self.bundle = self.root/'inbox'/'bundle';self.bundle.mkdir(parents=True)
        (self.bundle/'request.txt').write_bytes(b'Authored synthetic candidate review only.\n')
        initial = Store(self.root/'store')
        try:
            register_source(initial,'NATIVE-SYN',self.bundle.parent,synthetic=True,settle_seconds=1)
            scan_source(initial,'NATIVE-SYN',now=100,synthetic_only=True)
            accepted=scan_source(initial,'NATIVE-SYN',now=101,synthetic_only=True)['accepted'][0]
            with initial.connection() as con:
                revision=con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                    (accepted['intake_id'],accepted['revision'])).fetchone()
                self.selection=dict(source_id='NATIVE-SYN',intake_id=accepted['intake_id'],revision=accepted['revision'],
                    job_id=accepted['job_id'],revision_fingerprint=revision['fingerprint'],files=json.loads(revision['files_json']))
        finally:
            initial.close()
        self.history=dict(actual_codex_model_processes=16,known_total_before_this_host=16,unknown_usage_components=None,
            usage_complete=False,cost=None,provenance_level='previous_verified_root_rollup_not_fresh_original_receipt_reaudit',
            source_rollup=dict(path='authored-rollup-not-opened.json',bytes=1,sha256=H(b'authored rollup')),
            published_source=dict(commit='a'*40,path='authored-public-metadata.md',bytes=1,sha256=H(b'authored public')))
        self.anchor=dict(schema_version=1,kind='codex_intake_root_operator_continuation_anchor',
            recorded_at_kst='2026-10-26T00:00:00+09:00',state='standing_delegation_recorded_no_reservation_or_model_started',
            authority_source=dict(kind='direct_human_instructions_to_this_root_thread',instruction_reference='AUTHORED TEST FACSIMILE',
                authority_is_not_inferred_from_uploaded_documents_or_model_output=True),
            scope=dict(action='one_registered_synthetic_intake_run',allowed_models=['gpt-6.1-sol','gpt-6-astra'],
                maximum_attempts_per_once=1,timeout_seconds_maximum=60,automatic_retries=0,
                scope_is_existing_delegation_not_new_global_budget=True,customer_originals_or_decryption_external_transmission=False,
                hardware_network_output_motion_submission=False),inherited_history=copy.deepcopy(self.history),
            admission=dict(registered_input_root=None,registration_manifest=None,existing_store=None,cumulative_journal=None,
                reservation=None,permitted_to_dispatch_now=False,missing_registration_or_journal_is_not_run=True,
                actual_global_call_cap=None,global_cap_unknown_does_not_mean_unlimited=True,
                exhausted_Vertex_ledger_is_separate_and_must_not_be_read_or_modified=True),
            trust_boundary=dict(operator_control_directory=str(self.control),customer_input_argv_env_cannot_select_control_source=True,
                native_operator_local_account_boundary=True,protection_against_same_account_arbitrary_code_execution=False),
            new_model_processes=0,original_receipt_or_customer_body_reads=0,registration_created=False,
            cumulative_journal_seeded=False,new_budget_or_active_permit_issued=False)
        self.put(ANCHOR,self.anchor)
        self.manifest=dict(schema_version=1,kind='codex_registered_synthetic_intake',scenario_id='NATIVE-CASE',
            synthetic=True,registered_intake=self.selection)
        self.put('registered-intake-v1.json',self.manifest)
        self.exe=self.root/'codex.exe';self.exe.write_bytes(b'KNOWN FAKE PATH; NEVER EXECUTE THIS FILE')
        self.config=dict(schema_version=1,kind='codex_registered_intake_operator_control',anchor_sha256=H(C(self.anchor)),
            journal_id='AUTHORED-HISTORY',permit_id='AUTHORED-ONCE',registration_sha256=H(C(self.manifest)),
            registered_input_root=str(self.bundle),store_root=str(self.root/'store'),executable=str(self.exe))
        self.put('operator-control-v1.json',self.config)
        self.permit=dict(schema_version=1,kind='codex_intake_single_use_permit',journal_id=self.config['journal_id'],
            permit_id=self.config['permit_id'],anchor_sha256=self.config['anchor_sha256'],scenario_id='NATIVE-CASE',
            requested_model='gpt-6.1-sol',registration_sha256=self.config['registration_sha256'],store_root=self.config['store_root'],
            worker_id='native-fixture-worker',producer_name='NATIVE-AUTHORED',maximum_model_processes=1,
            timeout_seconds=5,automatic_retries=0,expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        self.journal=self.control/'continuation.sqlite3'
        con=sqlite3.connect(self.journal)
        try:
            con.execute(TABLE)
            baseline=dict(schema_version=1,kind='codex_intake_continuation_baseline',journal_id=self.config['journal_id'],
                anchor_sha256=self.config['anchor_sha256'],inherited_history=copy.deepcopy(self.history))
            con.execute('INSERT INTO codex_intake_history(kind,permit_id,payload) VALUES(?,?,?)',('baseline',None,canonical(baseline)))
            con.execute('INSERT INTO codex_intake_history(kind,permit_id,payload) VALUES(?,?,?)',('permit',self.config['permit_id'],canonical(self.permit)))
            con.commit()
        finally:
            con.close()
        self.evidence=self.control/'runs'/self.config['permit_id'];self.evidence.mkdir(parents=True)
        self.script=self.root/'known-fake-child.py';self.script.write_bytes(CHILD.encode())
        self.calls=[];self.children=[];self.spawn_errors=[]
        self.addCleanup(self.child_cleanup)

    def put(self,name,value):
        (self.control/name).write_bytes(C(value))

    def api(self):
        name='labflow.codex_registered_intake_host'
        self.assertIsNotNone(importlib.util.find_spec(name),'native registered operator entrypoint is absent')
        return importlib.import_module(name)

    def child_cleanup(self):
        live=[]
        for child in self.children:
            if child.poll() is None:live.append(child);child.kill()
            child.wait(timeout=3)
        self.assertEqual(live,[])

    def spawn(self,argv,**kwargs):
        try:
            self.assertEqual(Path(argv[0]),self.exe)
            self.assertFalse(kwargs['shell'])
            stage='version' if argv[1:]==['--version'] else 'model'
            self.calls.append(stage)
            last=argv[argv.index('--output-last-message')+1] if stage=='model' else '-'
            child=REAL_POPEN([sys.executable,'-B','-u',str(self.script),stage,last],**kwargs)
            self.children.append(child)
            return child
        except BaseException as exc:
            self.spawn_errors.append((type(exc).__name__,str(exc)))
            raise

    def invoke(self,args=None):
        api=self.api();out,err=io.StringIO(),io.StringIO()
        with patch.object(api,'_control_root',return_value=self.control), \
                patch('labflow.codex_cli_response.subprocess.Popen',side_effect=self.spawn), \
                redirect_stdout(out),redirect_stderr(err):
            status=api.main(['--scenario-id','NATIVE-CASE','--model',self.permit['requested_model']] if args is None else args)
        frame=(out.getvalue() or err.getvalue()).strip()
        return status,json.loads(frame),out.getvalue(),err.getvalue()

    def events(self):
        con=sqlite3.connect(self.journal)
        try:return [(r[0],r[1],json.loads(r[2])) for r in con.execute('SELECT kind,permit_id,payload FROM codex_intake_history ORDER BY seq')]
        finally:con.close()

    def job(self):
        con=sqlite3.connect(self.root/'store'/'lab.sqlite3')
        try:return con.execute('SELECT state,attempt FROM intake_jobs WHERE job_id=?',(self.selection['job_id'],)).fetchone()
        finally:con.close()

    def replace_event(self,kind,body):
        con=sqlite3.connect(self.journal)
        try:
            con.execute('UPDATE codex_intake_history SET payload=? WHERE kind=? AND permit_id=?',
                (canonical(body),kind,self.config['permit_id']));con.commit()
        finally:con.close()

    def new_permit(self):
        self.config['permit_id']='AUTHORED-NEXT'
        self.permit={**self.permit,'permit_id':self.config['permit_id']}
        self.put('operator-control-v1.json',self.config)
        con=sqlite3.connect(self.journal)
        try:
            con.execute('INSERT INTO codex_intake_history(kind,permit_id,payload) VALUES(?,?,?)',
                ('permit',self.config['permit_id'],canonical(self.permit)));con.commit()
        finally:con.close()
        (self.control/'runs'/self.config['permit_id']).mkdir()

    def refused(self):
        before=self.events();api=self.api()
        with patch.object(Store,'open_existing',wraps=Store.open_existing) as opener, \
                patch.object(api,'run_codex_intake_once',wraps=api.run_codex_intake_once) as once:
            status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'),result)
        self.assertEqual((opener.call_count,once.call_count),(0,0))
        self.assertEqual(self.events(),before)
        return result

    def test_genuine_once_with_known_fake_child_extends_history_and_closes_store(self):
        api=self.api();opened=[];original=Store.open_existing
        def opener(path):
            store=original(path);opened.append(store);return store
        with patch.object(Store,'open_existing',side_effect=opener), \
                patch.object(api,'prepare_registered_synthetic_context',wraps=api.prepare_registered_synthetic_context) as g3, \
                patch.object(api,'run_codex_intake_once',wraps=api.run_codex_intake_once) as once:
            status,result,out,err=self.invoke()
        self.assertEqual((status,result['status'],err),(0,'completed',''),repr(self.spawn_errors))
        self.assertEqual((g3.call_count,once.call_count,self.calls),(1,1,['version','model']))
        self.assertIs(g3.call_args.args[0],once.call_args.args[0])
        self.assertEqual(self.job(),('completed',1))
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed','finished'])
        self.assertEqual(result['history']['known_total_model_processes'],17)
        self.assertEqual(result['history']['actual_total_model_processes'],17)
        self.assertFalse(result['history']['usage_complete']);self.assertIsNone(result['history']['cost'])
        self.assertEqual([s._existing_binding.state for s in opened],['closed'])
        self.assertEqual(self.events()[0][2]['inherited_history'],self.history)
        self.assertEqual((self.evidence/'caller-receipt.json').exists(),True)
        self.assertEqual(result['once']['strict_decode'],'accepted')

    def test_same_permit_cannot_be_reset_with_a_new_empty_evidence_directory(self):
        self.assertEqual(self.invoke()[0],0)
        self.evidence.rename(self.evidence.with_name('preserved-first-evidence'));self.evidence.mkdir()
        before=self.events();status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'))
        self.assertEqual(self.events(),before);self.assertEqual(self.calls,['version','model'])
        self.assertEqual(self.job(),('completed',1))

    def test_partial_prior_finished_record_blocks_new_permit_before_store_open(self):
        self.assertEqual(self.invoke()[0],0)
        partial=self.events()[-1][2];del partial['once'];self.replace_event('finished',partial)
        self.new_permit();self.refused()

    def test_missing_prior_caller_evidence_blocks_new_permit_before_store_open(self):
        self.assertEqual(self.invoke()[0],0)
        caller=self.evidence/'caller-receipt.json';caller.rename(caller.with_suffix('.preserved'))
        self.new_permit();self.refused()

    def test_missing_operator_config_does_not_turn_anchor_into_a_permit(self):
        (self.control/'operator-control-v1.json').rename(self.control/'preserved-config.json')
        self.refused();self.assertEqual(self.calls,[])

    def test_missing_journal_is_not_created(self):
        self.journal.rename(self.journal.with_suffix('.preserved'))
        status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'))
        self.assertFalse(self.journal.exists());self.assertEqual(self.calls,[])

    def test_expired_or_mismatched_permit_has_no_store_or_dispatch(self):
        original=copy.deepcopy(self.permit)
        for change in [dict(expires_at='2000-01-01T00:00:00Z'),dict(requested_model='gpt-6-astra'),
                       dict(maximum_model_processes=2),dict(automatic_retries=1),dict(timeout_seconds=61),dict(timeout_seconds=True)]:
            with self.subTest(change=change):
                self.replace_event('permit',{**original,**change});self.refused()

    def test_original_bytes_and_extra_file_are_not_silently_accepted(self):
        path=self.bundle/'request.txt';original=path.read_bytes()
        path.write_bytes(b'Changed original; retained working blob did not change.\n')
        self.refused();path.write_bytes(original)
        (self.bundle/'extra.txt').write_bytes(b'Unregistered synthetic addition.\n');self.refused()

    def test_registration_hash_and_fingerprint_are_not_authority_defaults(self):
        self.config['registration_sha256']='0'*64;self.put('operator-control-v1.json',self.config)
        self.refused()

    def test_missing_registered_pdf_is_rejected_before_original_bytes_or_store(self):
        self.selection['files'][0]['path']='not-opened.PDF'
        self.selection['revision_fingerprint']=H(C(self.selection['files']))
        self.put('registered-intake-v1.json',self.manifest)
        self.config['registration_sha256']=H(C(self.manifest));self.put('operator-control-v1.json',self.config)
        self.permit['registration_sha256']=self.config['registration_sha256'];self.replace_event('permit',self.permit)
        api=self.api()
        with patch.object(api,'_read',wraps=api._read) as read:self.refused()
        self.assertFalse(any(str(call.args[0]).endswith('.PDF') for call in read.call_args_list))

    def test_zero_history_is_rejected_before_store(self):
        self.anchor['inherited_history']['actual_codex_model_processes']=0
        self.anchor['inherited_history']['known_total_before_this_host']=0
        self.put(ANCHOR,self.anchor)
        self.config['anchor_sha256']=H(C(self.anchor));self.put('operator-control-v1.json',self.config)
        self.refused()

    def test_busy_existing_journal_is_not_retried(self):
        con=sqlite3.connect(self.journal)
        try:
            con.execute('BEGIN IMMEDIATE');self.refused()
        finally:con.rollback();con.close()

    def test_non_synthetic_working_source_never_reserves_or_claims(self):
        con=sqlite3.connect(self.root/'store'/'lab.sqlite3')
        try:con.execute('UPDATE intake_sources SET synthetic=0');con.commit()
        finally:con.close()
        before=self.events();status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'))
        self.assertEqual(self.events(),before);self.assertEqual(self.job(),('queued',0));self.assertEqual(self.calls,[])

    def test_other_outstanding_job_is_not_claimed(self):
        other=self.root/'other-inbox'/'one';other.mkdir(parents=True)
        (other/'request.txt').write_bytes(b'Other synthetic registered case.\n')
        store=Store.open_existing(str(self.root/'store'))
        try:
            register_source(store,'OTHER-SYN',other.parent,synthetic=True,settle_seconds=1)
            scan_source(store,'OTHER-SYN',now=100,synthetic_only=True);scan_source(store,'OTHER-SYN',now=101,synthetic_only=True)
        finally:store.close()
        before=self.events();status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'))
        self.assertEqual(self.events(),before);self.assertEqual(self.job(),('queued',0));self.assertEqual(self.calls,[])

    def test_original_changes_after_g3_block_before_reservation(self):
        api=self.api();prepare=api.prepare_registered_synthetic_context
        def changed(*args,**kwargs):
            context=prepare(*args,**kwargs);(self.bundle/'request.txt').write_bytes(b'After G3 change.\n');return context
        before=self.events()
        with patch.object(api,'prepare_registered_synthetic_context',side_effect=changed):status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(3,'not_run'))
        self.assertEqual(self.events(),before);self.assertEqual(self.job(),('queued',0));self.assertEqual(self.calls,[])

    def test_control_objects_before_reservation_are_preserved(self):
        api=self.api();before=self.events()
        for kind in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            control=kind('authored control')
            with self.subTest(kind=kind.__name__),patch.object(api,'prepare_registered_synthetic_context',side_effect=control):
                with self.assertRaises(kind) as caught:self.invoke()
                self.assertIs(caught.exception,control)
        self.assertEqual(self.events(),before);self.assertEqual(self.calls,[])

    def test_control_after_consumption_leaves_unknown_and_cannot_reexecute(self):
        api=self.api();control=KeyboardInterrupt('authored control')
        with patch.object(api,'run_codex_intake_once',side_effect=control):
            with self.assertRaises(KeyboardInterrupt) as caught:self.invoke()
        self.assertIs(caught.exception,control)
        finished=self.events()[-1][2]
        self.assertEqual(finished['status'],'unknown');self.assertIsNone(finished['local_model_processes'])
        self.new_permit();self.refused();self.assertEqual(self.calls,[])

    def test_model_spawn_failure_does_not_confuse_attempt_with_process_start(self):
        original=self.spawn
        def failure(argv,**kwargs):
            if argv[1:]!=['--version']:
                self.calls.append('model-spawn-failed');raise OSError('Authored fake spawn failure')
            return original(argv,**kwargs)
        self.spawn=failure
        status,result,_,_=self.invoke()
        self.assertIn(status,(4,5));self.assertEqual(result['once']['attempts']['model_process_attempts'],1)
        self.assertEqual(self.events()[-1][2]['local_model_processes'],0)
        self.assertEqual(result['history']['known_total_model_processes'],16)
        self.assertEqual(result['history']['consumed_single_use_permits'],1)
        self.assertEqual(self.calls,['version','model-spawn-failed'])

    def test_store_close_failure_preserves_original_control(self):
        api=self.api();control=KeyboardInterrupt('original dispatch control');close=Store.close
        def failure(store):close(store);raise OSError('authored close failure after actual close')
        with patch.object(api,'run_codex_intake_once',side_effect=control),patch.object(Store,'close',side_effect=failure,autospec=True):
            with self.assertRaises(KeyboardInterrupt) as caught:self.invoke()
        self.assertIs(caught.exception,control)
        self.assertEqual(self.events()[-1][2]['status'],'unknown')

    def test_arguments_cannot_select_control_or_supply_authority(self):
        api=self.api()
        for args in [[],['--scenario-id','NATIVE-CASE','--model','gpt-6.1-sol','--control-root',str(self.control)],
                     ['--scenario-id','NATIVE-CASE','--scenario-id','NATIVE-CASE'],['--model','other','--scenario-id','NATIVE-CASE']]:
            with self.subTest(args=args),patch.object(api,'_control_root',side_effect=AssertionError('must not resolve')):
                with redirect_stderr(io.StringIO()):self.assertEqual(api.main(args),2)
        with self.assertRaises(TypeError):api.main([],authorization={'approved':True})

    def test_help_reads_no_control_and_writes_no_journal(self):
        api=self.api();before=self.events()
        with patch.object(api,'_control_root',side_effect=AssertionError('control forbidden')),redirect_stdout(io.StringIO()):
            self.assertEqual(api.main(['--help']),0)
        self.assertEqual(self.events(),before)

    def test_late_journal_close_failure_blocks_a_new_permit(self):
        connect=sqlite3.connect
        class ClosingFailure:
            def __init__(self,con):self.con=con
            def __getattr__(self,name):return getattr(self.con,name)
            def close(self):self.con.close();raise OSError('authored failure after native journal close')
        def opener(path,*args,**kwargs):
            con=connect(path,*args,**kwargs)
            return ClosingFailure(con) if str(path).startswith('file:') and 'continuation.sqlite3' in str(path) else con
        with patch('sqlite3.connect',side_effect=opener):status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.new_permit();self.refused()

    def test_existing_partial_active_guard_blocks_before_any_store(self):
        (self.control/'active-run.json').write_bytes(b'{partial-guard')
        self.refused();self.assertEqual(self.calls,[])

    def test_known_folder_uses_current_token_and_frees_fake_native_memory(self):
        api=self.api();buffer=ctypes.create_unicode_buffer(str(self.root/'fake-local-appdata'));freed=[];calls=[]
        def folder(guid,flags,token,output):
            calls.append((flags,token))
            ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(ctypes.addressof(buffer))
            return 0
        def free(pointer):freed.append(pointer.value)
        def library(name,**kwargs):
            return SimpleNamespace(SHGetKnownFolderPath=folder) if name=='shell32' else SimpleNamespace(CoTaskMemFree=free)
        with patch.object(api.ctypes,'WinDLL',side_effect=library),patch.dict(os.environ,dict(LOCALAPPDATA='C:/wrong',USERPROFILE='C:/wrong')):
            root=api._control_root()
        self.assertEqual(root,self.root/'fake-local-appdata'/'DGMAutoLab'/'codex-intake-host')
        self.assertEqual(calls,[(0,None)]);self.assertEqual(freed,[ctypes.addressof(buffer)])

    def test_known_folder_keeps_original_control_when_memory_free_also_fails(self):
        api=self.api();buffer=ctypes.create_unicode_buffer('C:/authored-only');control=KeyboardInterrupt('first native control')
        def folder(guid,flags,token,output):
            ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(ctypes.addressof(buffer))
            raise control
        def free(pointer):raise OSError('secondary native free failure')
        def library(name,**kwargs):
            return SimpleNamespace(SHGetKnownFolderPath=folder) if name=='shell32' else SimpleNamespace(CoTaskMemFree=free)
        with patch.object(api.ctypes,'WinDLL',side_effect=library):
            with self.assertRaises(KeyboardInterrupt) as caught:api._control_root()
        self.assertIs(caught.exception,control)

    def test_failure_after_reservation_keeps_it_without_refund_or_retry(self):
        api=self.api();append=api._append
        def failure(con,kind,permit_id,body):
            if kind=='consumed':raise OSError('authored consumption write failure')
            return append(con,kind,permit_id,body)
        with patch.object(api,'_append',side_effect=failure):status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved'])
        self.assertTrue((self.control/'active-run.json').exists())
        self.assertEqual(self.calls,[]);self.assertEqual(self.job(),('queued',0))
        self.new_permit();self.refused()

    def test_native_guard_postwrite_control_is_preserved_and_blocks_more_runs(self):
        api=self.api();write=api._active_guard;control=KeyboardInterrupt('postwrite first control')
        def failure(*args):write(*args);raise control
        with patch.object(api,'_active_guard',side_effect=failure):
            with self.assertRaises(KeyboardInterrupt) as caught:self.invoke()
        self.assertIs(caught.exception,control)
        self.assertEqual([e[0] for e in self.events()],['baseline','permit'])
        self.new_permit();self.refused();self.assertEqual(self.calls,[])

    def test_real_once_rejects_context_changed_after_consumption_before_model(self):
        api=self.api();append=api._append
        def changed(con,kind,permit_id,body):
            append(con,kind,permit_id,body)
            if kind=='consumed':
                (self.bundle/'request.txt').write_bytes(b'Authored new revision after reservation.\n')
                store=Store.open_existing(str(self.root/'store'))
                try:
                    scan_source(store,'NATIVE-SYN',now=200,synthetic_only=True)
                    scan_source(store,'NATIVE-SYN',now=201,synthetic_only=True)
                finally:store.close()
        with patch.object(api,'_append',side_effect=changed):status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(4,'failed'),result)
        self.assertEqual(result['once']['attempts']['producer_invocations'],0)
        self.assertEqual(self.calls,[])
        self.assertEqual(result['history']['known_total_model_processes'],16)
        self.assertEqual(result['history']['consumed_single_use_permits'],1)

    def test_process_stream_failure_and_control_have_bounded_quiet_exit(self):
        code=r'''
import sys
sys.path.insert(0,sys.argv[2])
import labflow.codex_registered_intake_host as host
if sys.argv[1]=='broken':
    class Broken:
        def reconfigure(self,**kwargs):pass
        def write(self,payload):raise OSError('known fake broken output')
        def flush(self):raise OSError('known fake final flush')
    sys.stdout=Broken()
    original=host.main
    host.main=lambda:original(['--help'])
else:
    def interrupted():raise KeyboardInterrupt('known fake process control')
    host.main=interrupted
raise SystemExit(host._process_main())
'''
        path=self.root/'known-fake-stream-child.py';path.write_bytes(code.encode())
        for mode,expected in [('broken',5),('control',130)]:
            with self.subTest(mode=mode):
                child=REAL_POPEN([sys.executable,'-X','utf8','-B',str(path),mode,str(Path(__file__).parents[1])],
                    stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.children.append(child);out,err=child.communicate(timeout=5)
                self.assertEqual((child.returncode,out,err),(expected,b'',b''))

    def faulty_journal(self,kind='finished',mode='insert',*,rollback_failure=False,history_failure=False,control=None):
        connect=sqlite3.connect
        state=dict(faulted=False,last_kind=None,finished_committed=False,rollback_calls=0,errors=[])
        class Journal:
            def __init__(self,con):self.con=con
            def __getattr__(self,name):return getattr(self.con,name)
            def native_error(self):
                try:self.con.execute('SELECT * FROM authored_missing_journal_fault_table')
                except sqlite3.OperationalError as exc:state['errors'].append(exc);raise
            def execute(self,sql,parameters=()):
                if history_failure and state['finished_committed'] and sql.startswith('PRAGMA table_info'):
                    self.native_error()
                if sql.startswith('INSERT INTO codex_intake_history'):
                    state['last_kind']=parameters[0]
                    if parameters[0]==kind and mode=='insert':
                        state['faulted']=True
                        if control is not None:
                            self.con.execute(sql,parameters)
                            raise control
                        self.native_error()
                return self.con.execute(sql,parameters)
            def commit(self):
                self.con.commit()
                if state['last_kind']=='finished':state['finished_committed']=True
                if state['last_kind']==kind and mode=='post_commit':
                    state['faulted']=True;self.native_error()
            def rollback(self):
                state['rollback_calls']+=1
                if rollback_failure and state['faulted']:self.native_error()
                self.con.rollback()
        def opener(path,*args,**kwargs):
            con=connect(path,*args,**kwargs)
            return Journal(con) if str(path).startswith('file:') and 'continuation.sqlite3' in str(path) else con
        return patch('sqlite3.connect',side_effect=opener),state

    def current_history(self):
        con=sqlite3.connect(self.journal)
        try:return self.api()._history(con,self.anchor,self.config,self.control)[1]
        finally:con.close()

    def test_finish_insert_failure_returns_durable_pending_history_not_prelaunch_zeroes(self):
        fault,state=self.faulty_journal()
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertTrue(state['errors']);self.assertIsInstance(state['errors'][0],sqlite3.OperationalError)
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed'])
        self.assertEqual(result['reservation']['state'],'consumed')
        self.assertEqual(result['history'],self.current_history())
        self.assertEqual((result['history']['reserved_single_use_permits'],result['history']['consumed_single_use_permits'],
                          result['history']['pending_permits']),(1,1,1))
        self.assertIsNone(result['history']['actual_total_model_processes'])
        self.assertTrue((self.control/'active-run.json').exists())
        self.assertEqual((self.evidence/'caller-receipt.json').read_bytes(),C(result['once']))

    def test_reserved_postcommit_error_returns_verified_current_reservation(self):
        fault,_=self.faulty_journal('reserved','post_commit')
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved'])
        self.assertEqual(result['history'],self.current_history())
        self.assertEqual(result['history']['reserved_single_use_permits'],1)
        self.assertIsNone(result['history']['actual_total_model_processes'])
        self.assertEqual(self.calls,[]);self.assertTrue((self.control/'active-run.json').exists())

    def test_consumed_postcommit_error_returns_verified_pending_consumption(self):
        fault,_=self.faulty_journal('consumed','post_commit')
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed'])
        self.assertEqual(result['history'],self.current_history())
        self.assertEqual(result['history']['consumed_single_use_permits'],1)
        self.assertIsNone(result['history']['actual_total_model_processes'])
        self.assertEqual(self.calls,[])

    def test_finish_failure_and_failed_rollback_hold_history_null_without_retry(self):
        fault,state=self.faulty_journal(rollback_failure=True)
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertIsNone(result['history'])
        self.assertEqual(state['rollback_calls'],1)
        self.assertEqual(result['errors'][0]['phase'],'finish')
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed'])
        self.assertTrue((self.control/'active-run.json').exists())

    def test_finished_commit_then_unverifiable_history_is_null_without_rollback_or_rewrite(self):
        fault,state=self.faulty_journal(None,history_failure=True)
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertIsNone(result['history'])
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed','finished'])
        self.assertEqual(state['rollback_calls'],0)
        self.assertTrue((self.control/'active-run.json').exists())

    def test_initial_rollback_failure_does_not_retry_or_expose_prelaunch_statistics(self):
        fault,state=self.faulty_journal('consumed',rollback_failure=True)
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertIsNone(result['history']);self.assertEqual(state['rollback_calls'],1)
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved'])
        self.assertEqual(self.calls,[])

    def test_finish_control_remains_the_original_object_with_rollback_fault_configured(self):
        control=MemoryError('authored first finish control')
        fault,_=self.faulty_journal(rollback_failure=True,control=control)
        with fault:
            with self.assertRaises(MemoryError) as caught:self.invoke()
        self.assertIs(caught.exception,control)
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed'])
        self.assertTrue((self.control/'active-run.json').exists())

    def test_finished_postcommit_error_returns_verified_committed_history(self):
        fault,state=self.faulty_journal('finished','post_commit')
        with fault:status,result,_,_=self.invoke()
        self.assertEqual((status,result['status']),(5,'unknown'))
        self.assertEqual([e[0] for e in self.events()],['baseline','permit','reserved','consumed','finished'])
        self.assertEqual(result['history'],self.current_history())
        self.assertEqual((result['history']['known_total_model_processes'],result['history']['actual_total_model_processes'],
                          result['history']['pending_permits']),(17,17,0))
        self.assertEqual(state['rollback_calls'],0)
        self.assertEqual(result['once']['status'],'completed')
        self.assertTrue((self.control/'active-run.json').exists())


NATIVE_PDF_PREP_OBSERVATIONS = []


class NativePDFPreflightTests(unittest.TestCase):
    """Fresh synthetic G3; native authority/ledger are explicit memory seams."""
    NAME = 'NATIVE-PDF-AUTHORED-ONLY'
    SCENARIO = 'NATIVE-PDF-LOCAL'

    def setUp(self):
        from reportlab.pdfgen import canvas
        from labflow.intake_jobs import prepare_registered_synthetic_context
        self.api = importlib.import_module('labflow.codex_registered_intake_host')
        self.common = importlib.import_module('labflow.codex_intake_once')
        self.temp = tempfile.TemporaryDirectory(prefix='native-pdf-preflight-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root/'inbox/bundle';self.bundle.mkdir(parents=True)
        buffer=io.BytesIO();pdf=canvas.Canvas(buffer,invariant=1)
        for lines in (('product_type: industrial_sensor','model: NATIVE-PDF-SYN'),
                      ('market: EU','purpose: local development evaluation')):
            text=pdf.beginText(48,790)
            for line in lines:text.textLine(line)
            pdf.drawText(text);pdf.showPage()
        pdf.save();(self.bundle/'REQUEST.PDF').write_bytes(buffer.getvalue())
        (self.bundle/'attachment.TXT').write_text('purpose: local development evaluation\n',encoding='utf-8')
        self.store=Store(self.root/'state');self.addCleanup(self.store.close)
        register_source(self.store,'NATIVE-PDF-SYN',self.bundle.parent,synthetic=True,settle_seconds=1)
        scan_source(self.store,'NATIVE-PDF-SYN',now=100,synthetic_only=True)
        item=scan_source(self.store,'NATIVE-PDF-SYN',now=101,synthetic_only=True)['accepted'][0]
        with self.store.connection() as con:
            row=con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                            (item['intake_id'],item['revision'])).fetchone()
        self.selection=dict(source_id='NATIVE-PDF-SYN',intake_id=item['intake_id'],revision=item['revision'],
            job_id=item['job_id'],revision_fingerprint=row['fingerprint'],files=json.loads(row['files_json']))
        self.context=prepare_registered_synthetic_context(self.store,self.selection,producer_name=self.NAME)
        self.manifest=dict(schema_version=1,kind='codex_registered_synthetic_intake',scenario_id=self.SCENARIO,
                           synthetic=True,registered_intake=self.selection)
        self.registration=self.root/'registration-only';self.registration.mkdir()
        (self.registration/'registered-intake-v1.json').write_bytes(C(self.manifest))
        self.exe=self.root/'codex.exe';self.exe.write_bytes(b'authored path only; never executed')
        self.record=dict(case=self._testMethodName,context=copy.deepcopy(self.context),actual_CLI=0,actual_models=0,
            authority='native control/anchor/permit/journal seams in memory; no issued profile or permit',outcomes=[])
        self.counter=0;self.addCleanup(self.capture)

    def capture(self):
        files={}
        for path in self.root.rglob('*'):
            if path.is_file() and path.suffix!='.sqlite3':files[path.relative_to(self.root).as_posix()]=path.read_bytes()
        self.assertLessEqual(len(files),192);self.assertLessEqual(sum(map(len,files.values())),8*1024*1024)
        NATIVE_PDF_PREP_OBSERVATIONS.append(dict(self.record,files=files))

    def exercise(self, context=None, *, first=None, late=None, source_changed=False, genuine=False):
        api=self.api;self.counter+=1;root=self.root/('memory-native-'+str(self.counter));root.mkdir()
        evidence=root/'runs/MEMORY-ONLY';evidence.mkdir(parents=True)
        (root/'registered-intake-v1.json').write_bytes(C(self.manifest))
        anchor_bytes=C(dict(fixture_only=True));journal=root/'continuation.sqlite3'
        config=dict(schema_version=1,kind='codex_registered_intake_operator_control',anchor_sha256=H(anchor_bytes),
            journal_id='MEMORY-ONLY',permit_id='MEMORY-ONLY',registration_sha256=H(C(self.manifest)),
            registered_input_root=str(self.bundle),store_root=str(self.store.root),executable=str(self.exe))
        config_bytes=C(config);context=copy.deepcopy(self.context if context is None else context)
        permit=dict(producer_name=self.NAME,worker_id='native-pdf-memory-worker',timeout_seconds=5,
                    expires_at='2099-01-01T00:00:00Z')
        trace=[];events={};registrations=[];preflights=[];once_calls=[]
        info=SimpleNamespace(st_size=0,st_dev=1,st_ino=1)
        class Journal:
            in_transaction=False
            closes=0
            def execute(inner,sql,*args):
                trace.append('sql:'+sql)
                if first is not None and sql=='PRAGMA trusted_schema=OFF':raise first
                if sql=='BEGIN IMMEDIATE':inner.in_transaction=True
                return inner
            def commit(inner):trace.append('commit');inner.in_transaction=False
            def rollback(inner):trace.append('rollback');inner.in_transaction=False
            def close(inner):
                inner.closes+=1;trace.append('journal_close')
                if late is not None:raise late
        class Guard:
            closes=0
            def fileno(inner):return -7654321
            def close(inner):inner.closes+=1;trace.append('guard_close')
        class Borrowed:
            def close(inner):trace.append('store_close')
        con=Journal();guard=Guard();borrowed=self.store if genuine else Borrowed()
        real_path,real_read,real_open,real_stat,real_connect=api._path,api._read,Path.open,os.fstat,sqlite3.connect
        real_registration,real_dedicated,real_prepare=api._registration,api._dedicated,api.prepare_registered_synthetic_context
        def path(value,*,directory):
            value=Path(value)
            return (value,info) if value==journal else real_path(value,directory=directory)
        def read(value,cap):
            if value==root/api._ANCHOR:return anchor_bytes
            if value==root/'operator-control-v1.json':return config_bytes
            return real_read(value,cap)
        def opened(value,*args,**kwargs):
            return guard if value==journal else real_open(value,*args,**kwargs)
        def connect(value,*args,**kwargs):
            return con if value==journal.as_uri()+'?mode=rw' else real_connect(value,*args,**kwargs)
        def history(*args):
            pending={config['permit_id']} if any(kind in ('reserved','consumed') for kind,_ in events) and ('finished',config['permit_id']) not in events else set()
            return copy.deepcopy(events),dict(fixture_only=True),pending
        def append(connection,kind,permit_id,body):
            self.assertIs(connection,con);trace.append(kind);events[kind,permit_id]=copy.deepcopy(body)
        def registration(*args):
            registrations.append(True);trace.append('registration')
            if source_changed and len(registrations)>1:api._fail('registration_changed')
            return real_registration(*args) if genuine else copy.deepcopy(self.selection)
        def dedicated(*args):
            trace.append('dedicated')
            if genuine:return real_dedicated(*args)
        def prepare(*args,**kwargs):
            trace.append('G3')
            return real_prepare(*args,**kwargs) if genuine else context
        def preflight(value,*,producer_name):
            trace.append('preflight');result=self.common.preflight_codex_intake_once_inputs(value,producer_name=producer_name)
            preflights.append(copy.deepcopy(result));return result
        def once(*args,**kwargs):
            trace.append('once');once_calls.append(C(args[1]))
            return self.common.run_codex_intake_once(*args,**kwargs) if genuine else dict(status='failed',fixture_only=True)
        def active(value,data):
            trace.append('active_guard');return SimpleNamespace(st_dev=1,st_ino=1)
        result=outward=None;authored_calls=[]
        with ExitStack() as stack:
            stack.enter_context(patch.object(api,'_control_root',return_value=root))
            stack.enter_context(patch.object(api,'_path',side_effect=path))
            stack.enter_context(patch.object(api,'_read',side_effect=read))
            stack.enter_context(patch.object(api,'_anchor',return_value=None))
            stack.enter_context(patch.object(Path,'open',new=opened))
            stack.enter_context(patch.object(api.os,'fstat',side_effect=lambda fd:info if fd==-7654321 else real_stat(fd)))
            stack.enter_context(patch.object(api.sqlite3,'connect',side_effect=connect))
            stack.enter_context(patch.object(api,'_history',side_effect=history))
            stack.enter_context(patch.object(api,'_permit',return_value=permit))
            stack.enter_context(patch.object(api,'_append',side_effect=append))
            stack.enter_context(patch.object(api,'_registration',side_effect=registration))
            stack.enter_context(patch.object(api.Store,'open_existing',return_value=borrowed))
            stack.enter_context(patch.object(api,'_dedicated',side_effect=dedicated))
            stack.enter_context(patch.object(api,'prepare_registered_synthetic_context',side_effect=prepare))
            stack.enter_context(patch.object(api,'preflight_codex_intake_once_inputs',side_effect=preflight,create=True))
            stack.enter_context(patch.object(api,'run_codex_intake_once',side_effect=once))
            if genuine:
                from test_codex_intake_once import SchemaTwoOnceTests
                helper=SchemaTwoOnceTests();case=dict(calls=authored_calls)
                stack.enter_context(patch.object(self.common,'produce_codex_cli_response',side_effect=helper.producer(case)))
            else:
                stack.enter_context(patch.object(api,'_active_guard',side_effect=active))
                stack.enter_context(patch.object(api,'_observation',return_value=(0,None,True,None)))
            try:result=api._run(self.SCENARIO,'gpt-6.1-sol')
            except BaseException as error:outward=error
        observation=dict(trace=trace,events=[dict(kind=kind,body=body) for (kind,_),body in events.items()],
            preflights=preflights,once_calls=len(once_calls),result=result,
            outward_type=type(outward).__name__ if outward is not None else None,
            journal_closes=con.closes,guard_closes=guard.closes,authored_stub_invocations=len(authored_calls),
            genuine_source_Store_once=genuine,actual_CLI=0,actual_models=0)
        self.record['outcomes'].append(observation)
        return SimpleNamespace(record=result,outward=outward,trace=trace,events=events,preflights=preflights,
                               once_calls=once_calls,guard=guard,journal=con,evidence=evidence,authored=authored_calls)

    def test_registered_uppercase_pdf_and_mixed_bytes_pass_registration_before_any_authority(self):
        config=dict(registration_sha256=H(C(self.manifest)),registered_input_root=str(self.bundle))
        before={path.name:path.read_bytes() for path in self.bundle.iterdir()}
        try:result=self.api._registration(self.registration,config,self.SCENARIO)
        except ValueError as error:self.fail('registered authored complete PDF is categorically rejected: '+str(error))
        self.assertEqual(result,self.selection)
        self.assertEqual(before,{path.name:path.read_bytes() for path in self.bundle.iterdir()})

    def test_common_complete_context_preflight_precedes_guard_reservation_and_consumption(self):
        outcome=self.exercise()
        self.assertEqual(len(outcome.preflights),1,'native host omitted the common pre-consume request check')
        self.assertEqual(outcome.preflights[0]['status'],'validated')
        for event in ('active_guard','reserved','consumed','once'):
            self.assertLess(outcome.trace.index('preflight'),outcome.trace.index(event))
        self.assertEqual(outcome.once_calls,[C(outcome.preflights[0]['context'])])

    def test_quality_and_request_caps_stop_before_guard_reservation_consumption_or_once(self):
        from labflow.intake_model_boundary import build_analysis_response_schema
        for kind in ('partial','prompt_limit','schema_limit'):
            context=copy.deepcopy(self.context)
            if kind=='partial':next(d for d in context['documents'] if d.get('format')=='pdf')['complete']=False
            if kind=='prompt_limit':context['instructions']='x'*262144
            with self.subTest(kind=kind),ExitStack() as stack:
                if kind=='schema_limit':
                    schema=build_analysis_response_schema(producer_name=self.NAME,context=context);schema['description']='x'*65537
                    stack.enter_context(patch.object(self.common,'build_analysis_response_schema',return_value=schema))
                self.assertEqual(self.common.preflight_codex_intake_once_inputs(context,producer_name=self.NAME)['status'],'blocked')
                outcome=self.exercise(context)
                self.assertEqual(outcome.once_calls,[],'unsupported input consumed the manual seam before dispatch')
                self.assertEqual(outcome.events,{})
                self.assertNotIn('active_guard',outcome.trace)
                self.assertEqual(outcome.record['status'],'not_run')

    def test_first_ordinary_receipt_survives_all_late_cleanup_control_families(self):
        for kind in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            first=OSError('AUTHORED_FIRST_ORDINARY');late=kind('AUTHORED_LATE_CONTROL')
            with self.subTest(kind=kind.__name__):
                outcome=self.exercise(first=first,late=late)
                self.assertIsNone(outcome.outward,'a late cleanup control replaced the first ordinary receipt outcome')
                self.assertEqual(outcome.record['errors'][0]['phase'],'history')
                self.assertEqual(outcome.record['errors'][-1]['phase'],'journal_close')
                self.assertEqual(outcome.journal.closes,1);self.assertEqual(outcome.guard.closes,1)
                self.assertEqual(vars(first),{});self.assertEqual(vars(late),{})

    def test_first_control_keeps_identity_when_journal_cleanup_later_fails(self):
        for kind in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            first=kind('AUTHORED_FIRST_CONTROL')
            with self.subTest(kind=kind.__name__):
                outcome=self.exercise(first=first,late=OSError('AUTHORED_LATE_ORDINARY'))
                self.assertIs(outcome.outward,first)
                self.assertEqual(outcome.journal.closes,1);self.assertEqual(outcome.guard.closes,1)
                self.assertEqual(outcome.events,{})
                self.assertEqual(vars(first),{})

    def test_source_recheck_after_G3_prevents_reservation_and_dispatch(self):
        outcome=self.exercise(source_changed=True)
        self.assertIsNone(outcome.outward)
        self.assertEqual(outcome.record['status'],'not_run')
        self.assertTrue(outcome.record['errors'][0]['code'].endswith('registration_changed'))
        self.assertEqual(outcome.events,{})
        self.assertEqual(outcome.once_calls,[])

    def test_fresh_mixed_G3_real_once_and_strict_complete_with_memory_authority_seams(self):
        outcome=self.exercise(genuine=True)
        self.assertIsNone(outcome.outward)
        self.assertEqual(outcome.record['status'],'completed')
        self.assertEqual(outcome.record['once']['strict_decode'],'accepted')
        self.assertEqual(len(outcome.authored),1)
        self.assertEqual(outcome.record['once']['job']['attempt'],1)
        self.assertEqual(outcome.record['once']['attempts']['automatic_retries'],0)
        self.assertEqual([item for item in outcome.trace if item in ('reserved','consumed','once')],['reserved','consumed','once'])
        self.assertEqual(outcome.record['reservation']['state'],'finished')
        self.assertEqual(outcome.journal.closes,1);self.assertEqual(outcome.guard.closes,1)
        self.assertFalse((outcome.evidence.parent.parent/'active-run.json').exists())

    def test_legacy_text_only_schema_one_keeps_real_once_and_common_preflight(self):
        from labflow.intake_jobs import prepare_registered_synthetic_context
        base=self.root/'separate-text-case';bundle=base/'inbox/bundle';bundle.mkdir(parents=True)
        (bundle/'request.TXT').write_text('product_type: industrial_sensor\nmodel: LEGACY-TEXT-SYN\n'
            'market: EU\npurpose: local development evaluation\n',encoding='utf-8')
        store=Store(base/'state');self.addCleanup(store.close)
        register_source(store,'NATIVE-TEXT-SYN',bundle.parent,synthetic=True,settle_seconds=1)
        scan_source(store,'NATIVE-TEXT-SYN',now=200,synthetic_only=True)
        item=scan_source(store,'NATIVE-TEXT-SYN',now=201,synthetic_only=True)['accepted'][0]
        with store.connection() as con:
            row=con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                            (item['intake_id'],item['revision'])).fetchone()
        selection=dict(source_id='NATIVE-TEXT-SYN',intake_id=item['intake_id'],revision=item['revision'],
            job_id=item['job_id'],revision_fingerprint=row['fingerprint'],files=json.loads(row['files_json']))
        context=prepare_registered_synthetic_context(store,selection,producer_name=self.NAME)
        self.store,self.bundle,self.selection,self.context=store,bundle,selection,context
        self.manifest=dict(schema_version=1,kind='codex_registered_synthetic_intake',scenario_id=self.SCENARIO,
                           synthetic=True,registered_intake=selection)
        self.record['separate_legacy_context']=copy.deepcopy(context)
        outcome=self.exercise(genuine=True)
        self.assertIsNone(outcome.outward)
        self.assertEqual(outcome.record['status'],'completed')
        self.assertEqual(outcome.record['once']['strict_decode'],'accepted')
        self.assertEqual(len(outcome.preflights),1)
        self.assertEqual(outcome.preflights[0]['response_schema']['properties']['schema_version']['enum'],[1])
        self.assertNotIn('context_id',outcome.preflights[0]['response_schema']['properties'])
        self.assertEqual(len(outcome.authored),1)
        self.assertEqual(outcome.record['once']['attempts']['automatic_retries'],0)

    def test_bad_preflight_envelope_pins_and_byte_caps_never_reserve_or_dispatch(self):
        original=self.common.preflight_codex_intake_once_inputs(self.context,producer_name=self.NAME)
        self.assertEqual(original['status'],'validated')
        for kind in ('boolean_version','authority','extra_key','extra_pin','prompt_hash','context','prompt_cap','schema_cap'):
            bad=copy.deepcopy(original)
            if kind=='boolean_version':bad['schema_version']=True
            elif kind=='authority':bad['execution_authority']=True
            elif kind=='extra_key':bad['unknown']=True
            elif kind=='extra_pin':bad['pins']['unknown']='0'*64
            elif kind=='prompt_hash':bad['pins']['prompt_sha256']='0'*64
            elif kind=='context':
                bad['context']['instructions']+=' authored changed snapshot'
                bad['pins']['context_sha256']=H(C(bad['context']))
            elif kind=='prompt_cap':
                bad['prompt']['oversize']='x'*262144;bad['pins']['prompt_sha256']=H(C(bad['prompt']))
            else:
                bad['response_schema']['description']='x'*65537;bad['pins']['schema_sha256']=H(C(bad['response_schema']))
            with self.subTest(kind=kind),patch.object(self.common,'preflight_codex_intake_once_inputs',return_value=bad):
                outcome=self.exercise()
                self.assertIsNone(outcome.outward)
                self.assertEqual(outcome.record['status'],'not_run')
                self.assertEqual(outcome.events,{})
                self.assertEqual(outcome.once_calls,[])
                self.assertNotIn('active_guard',outcome.trace)

    def test_completed_once_first_store_close_error_and_late_control_keep_unknown_and_guard(self):
        first=OSError('AUTHORED_FIRST_STORE_CLOSE');late=MemoryError('AUTHORED_LATE_JOURNAL_CLOSE')
        with patch.object(self.store,'close',side_effect=first):
            outcome=self.exercise(genuine=True,late=late)
        self.assertIsNone(outcome.outward)
        self.assertEqual(outcome.record['status'],'unknown')
        self.assertEqual(outcome.record['errors'][0]['phase'],'store_close')
        self.assertEqual(outcome.record['errors'][-1]['phase'],'journal_close')
        self.assertEqual(outcome.record['once']['status'],'completed')
        self.assertEqual(len(outcome.authored),1)
        self.assertEqual(outcome.record['reservation']['state'],'finished')
        self.assertTrue((outcome.evidence.parent.parent/'active-run.json').is_file())
        self.assertEqual(vars(first),{});self.assertEqual(vars(late),{})


if __name__=='__main__':
    unittest.main()
