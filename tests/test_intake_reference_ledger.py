"""Genuine synthetic V2/PDF/SQLite reference publication; no customer or model."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import intake_reference_ledger as ledger
from labflow.active_intake import register_source,scan_source
from labflow.intake_jobs import claim_job,complete_job,respond
from labflow.intake_worker import SyntheticTextProvider
from labflow.intake_reference_snapshot import read_intake_reference_snapshot
from labflow.intake_case_references import build_intake_case_reference_receipt
from labflow.fcc_report_cases import FccReportCaseCatalog
from labflow.fcc_case_review import decode_case_review_response
from labflow.store import Store,canonical
from tests.test_document_extract import synthetic_pdf
from tests.test_intake_case_references import catalog_fixture,context_for,response_for
from tests.test_fcc_report_cases import fixture as report_fixture
from tests.test_fcc_case_review import wire as response_wire


R='intake_reference_records';H='intake_reference_heads';E='intake_reference_events'
REG={'schema_version','kind','request_id','record_id','seq','stored','replayed','binding_status','append_observation','verification'}
HISTORY={'schema_version','kind','intake_id','available','records','next_before_seq','verification'}
CURRENT={'schema_version','kind','intake_id','available','status','record','reference_receipt','current_observation','reason_codes','verification'}
SUMMARY={'record_id','seq','request_id','revision','origin_job_id','reference_receipt_id','binding_status','expected_snapshot_id','append_observation','source_modes','created_at'}
FALSE={'operational_authority_granted','model_execution_verified','evaluation_executed','independent_evaluation_approved','reference_source_currentness_verified'}
ROOT=Path(__file__).resolve().parents[1]


def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


class ReferenceLedgerTests(unittest.TestCase):
    def setUp(self):
        local=ROOT/'.local';local.mkdir(exist_ok=True)
        temp=tempfile.TemporaryDirectory(prefix='ledger038-',dir=local);self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.store=Store(self.root/'state');self.inbox=self.root/'inbox'
        (self.inbox/'one').mkdir(parents=True);self.tick=100
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)
        self.intake,self.job=self.revision('FIRST');respond(self.store,'PROCEED-1','proceed',intake_id=self.intake)
        self.catalog=catalog_fixture();self.context=context_for(self.catalog);self.response=response_for(self.context)

    def revision(self,label,*,finish=True):
        (self.inbox/'one/request.pdf').write_bytes(synthetic_pdf(['product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A\nrevision_label: '+label]))
        scan_source(self.store,'INBOX',now=self.tick);result=scan_source(self.store,'INBOX',now=self.tick+2)
        self.tick+=100
        if not finish:return result['accepted'][0]['intake_id'],None
        job=claim_job(self.store,'WORKER',now=self.tick-97);analysis=SyntheticTextProvider().analyze(job)
        complete_job(self.store,job['job_id'],job['token'],analysis,now=self.tick-96)
        return job['intake_id'],job

    def inputs(self,capture=None,*,catalog=None,context=None,response=None):
        capture=read_intake_reference_snapshot(self.store,self.intake) if capture is None else capture
        catalog=self.catalog if catalog is None else catalog;context=self.context if context is None else context;response=self.response if response is None else response
        parent=build_intake_case_reference_receipt(capture['snapshot'],catalog,context,response,producer_name=response['expected_producer']['name'])
        return {'expected_snapshot_id':capture['snapshot_id'],'expected_head_record_id':None,'intake_snapshot':capture['snapshot'],
            'catalog':catalog,'case_context':context,'validated_response':response,'reference_receipt':parent,'producer_name':response['expected_producer']['name']}

    def record(self,request='REQUEST-1',*,args=None,**changes):
        args=self.inputs() if args is None else dict(args);args.update(changes)
        return ledger.record_intake_reference(self.store,request,**args)

    def error(self,code,operation):
        with self.assertRaises(ledger.IntakeReferenceLedgerError) as caught:operation()
        error=caught.exception;expected='intake_reference_ledger_'+code
        self.assertEqual((error.code,str(error),error.args),(expected,expected,(expected,)));self.assertIsNone(error.__context__)
        self.assertNotIn(str(self.root),repr(error));self.assertNotIn('MODEL-A',repr(error))

    def namespace(self):
        with self.store.connection() as con:return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE name LIKE 'intake_reference_%' ORDER BY name")]

    def counts(self):
        with self.store.connection() as con:return tuple(con.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in [R,E,H])

    def base(self):
        with self.store.connection() as con:
            names=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'intake_reference_%' ORDER BY name")]
            return {name:[tuple(row) for row in con.execute('SELECT * FROM '+name+' ORDER BY rowid')] for name in names}

    def edit(self,table,sql,args=(),*,delete=False):
        trigger=table+('_no_delete' if delete else '_no_update')
        with self.store.connection() as con:
            saved=con.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger,)).fetchone()[0]
            con.execute('DROP TRIGGER '+trigger);con.execute(sql,args);con.execute(saved)

    def test_exact_registration_persisted_history_and_current(self):
        args=self.inputs();self.assertEqual(args['reference_receipt']['status'],'bound');before=self.base()
        result=self.record(args=args);self.assertEqual(set(result),REG);self.assertEqual(result['kind'],'intake_reference_registration')
        self.assertEqual(result['binding_status'],'current_at_append');self.assertTrue(result['stored']);self.assertFalse(result['replayed'])
        self.assertEqual(len(result['append_observation']),7);self.assertEqual(len(result['verification']),8)
        self.assertEqual(self.counts(),(1,1,1));self.assertEqual(self.base(),before)
        history=ledger.reference_history(self.store,self.intake);self.assertEqual(set(history),HISTORY);self.assertTrue(history['available'])
        self.assertEqual(set(history['records'][0]),SUMMARY);self.assertEqual(len(history['verification']),4)
        current=ledger.current_reference(self.store,self.intake);self.assertEqual(set(current),CURRENT);self.assertEqual(current['status'],'current')
        self.assertEqual(len(current['current_observation']),4);self.assertEqual(len(current['verification']),6)
        self.assertEqual(current['reference_receipt'],args['reference_receipt']);self.assertIsNone(current['reference_receipt']['evaluation']['score'])
        for dto in [result,current]:
            for key in FALSE & set(dto['verification']):self.assertIs(dto['verification'][key],False)

    def test_fingerprint_exact_keys_and_origin_foreign_key_shape(self):
        args=self.inputs();result=self.record(args=args)
        fingerprint=digest({'schema_version':1,'request_id':'REQUEST-1','expected_snapshot_id':args['expected_snapshot_id'],
            'expected_head_record_id':None,'intake_snapshot_sha256':digest(args['intake_snapshot']),'case_context_sha256':digest(args['case_context']),
            'validated_response_sha256':digest(args['validated_response']),'reference_receipt_sha256':digest(args['reference_receipt']),'producer_name':args['producer_name']})
        self.assertEqual(result['record_id'],digest({'schema_version':1,'request_id':'REQUEST-1','request_fingerprint':fingerprint}))
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT request_fingerprint FROM '+R).fetchone()[0],fingerprint)
            foreign=[tuple(row) for row in con.execute('PRAGMA foreign_key_list('+R+')')]
        self.assertEqual({row[2] for row in foreign},{'intake_revisions','intake_jobs'})
        self.assertTrue(all(row[5:7]==('NO ACTION','NO ACTION') for row in foreign))

    def test_readers_without_ledger_observe_current_without_creating_schema(self):
        before=self.base();self.assertEqual(self.namespace(),[])
        history=ledger.reference_history(self.store,self.intake);current=ledger.current_reference(self.store,self.intake)
        self.assertFalse(history['available']);self.assertEqual(history['records'],[]);self.assertIsNone(history['next_before_seq'])
        self.assertTrue(all(value is False for value in history['verification'].values()))
        self.assertFalse(current['available']);self.assertEqual(current['status'],'none');self.assertIn('no_reference_head',current['reason_codes'])
        self.assertIsNotNone(current['current_observation']['snapshot_id']);self.assertEqual(self.namespace(),[]);self.assertEqual(before,self.base())

    def test_modes_are_noncreating_and_never_store_connections(self):
        args=self.inputs();connect=sqlite3.connect;seen=[]
        def open_db(*values,**kwargs):seen.append((str(values[0]),kwargs));return connect(*values,**kwargs)
        forbidden=AssertionError('unexpected application write/parse')
        with patch.object(Store,'__init__',side_effect=forbidden),patch.object(Store,'connection',side_effect=forbidden), \
             patch.object(Store,'write_blob',side_effect=forbidden),patch.object(Store,'register_blob',side_effect=forbidden),patch.object(Store,'event',side_effect=forbidden), \
             patch('labflow.document_extract.extract_document',side_effect=forbidden),patch.object(SyntheticTextProvider,'analyze',side_effect=forbidden), \
             patch('labflow.intake_reference_ledger.sqlite3.connect',side_effect=open_db):
            self.record(args=args);ledger.reference_history(self.store,self.intake);ledger.current_reference(self.store,self.intake)
        self.assertEqual(len(seen),3);self.assertIn('mode=rw',seen[0][0]);self.assertTrue(all('mode=ro' in x[0] for x in seen[1:]))
        self.assertTrue(all(x[1].get('uri') is True and 'immutable' not in x[0] for x in seen))

    def test_missing_database_and_missing_parent_are_not_created(self):
        args=self.inputs();real=self.store.db;real.unlink()
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('storage_error',operation)
        self.assertFalse(real.exists());self.store.db=self.root/'ABSENT'/'lab.sqlite3'
        self.error('storage_error',lambda:self.record(args=args));self.assertFalse(self.store.db.parent.exists())

    def test_idempotent_replay_preserves_append_after_answer_and_fresh_current_changes(self):
        args=self.inputs();first=self.record(args=args);before=self.counts()
        respond(self.store,'ANSWER-1','answer',intake_id=self.intake,answers={'purpose':'revised development'})
        with patch('labflow.intake_reference_ledger.build_intake_case_reference_receipt',side_effect=AssertionError('replay parent revalidation')), \
             patch('labflow.intake_reference_ledger.capture_intake_reference_snapshot_in_transaction',side_effect=AssertionError('replay current observation')):
            replay=self.record(args=args)
        self.assertTrue(replay.pop('replayed'));expected=dict(first);expected.pop('replayed');self.assertEqual(replay,expected)
        self.assertEqual(self.counts(),before);current=ledger.current_reference(self.store,self.intake)
        self.assertEqual(current['status'],'stale');self.assertNotEqual(current['current_observation']['snapshot_id'],first['append_observation']['captured_snapshot_id'])
        self.assertIn('reference_snapshot_stale',current['reason_codes'])

    def test_same_request_different_payload_conflicts_without_writes(self):
        args=self.inputs();self.record(args=args);before=self.counts()
        self.error('request_conflict',lambda:self.record(args=args,expected_head_record_id='a'*64));self.assertEqual(self.counts(),before)

    def test_different_request_cas_null_is_not_a_wildcard(self):
        args=self.inputs();first=self.record(args=args);late=self.record('REQUEST-2',args=args)
        self.assertEqual(late['binding_status'],'head_conflict');self.assertFalse(late['append_observation']['head_advanced'])
        self.assertEqual(ledger.current_reference(self.store,self.intake)['record']['record_id'],first['record_id'])
        third=self.record('REQUEST-3',args=args,expected_head_record_id=first['record_id'])
        self.assertEqual(third['binding_status'],'current_at_append');self.assertEqual(self.counts(),(3,3,1))

    def test_historical_provided_is_not_current_even_when_append_observes_new_state(self):
        old=self.inputs();respond(self.store,'DEFER-NEW','defer',intake_id=self.intake)
        result=self.record(args=old);self.assertEqual(result['binding_status'],'historical_provided')
        self.assertFalse(result['verification']['mutable_state_verified_at_append']);self.assertTrue(result['verification']['origin_revalidated_at_append'])
        self.assertNotEqual(result['append_observation']['captured_snapshot_id'],old['expected_snapshot_id'])
        self.assertEqual(ledger.current_reference(self.store,self.intake)['status'],'none');self.assertEqual(self.counts(),(1,1,0))

    def test_historical_own_source_is_revalidated_after_current_A2(self):
        old=self.inputs();path=self.store.blob_path(self.job['documents'][0]['sha256']);self.revision('SECOND')
        real=ledger.capture_intake_reference_snapshot_in_transaction;calls=[]
        def capture(*args,**kwargs):
            value=real(*args,**kwargs);calls.append(value['snapshot_id'])
            if len(calls)==2:path.write_bytes(path.read_bytes()+b'corruption')
            return value
        with patch('labflow.intake_reference_ledger.capture_intake_reference_snapshot_in_transaction',side_effect=capture):
            self.error('origin_invalid',lambda:self.record(args=old))
        self.assertEqual(len(calls),2);self.assertEqual(self.namespace(),[])

    def test_current_unavailable_preserves_verified_past_head_and_historical_append(self):
        args=self.inputs();first=self.record(args=args);self.revision('PENDING',finish=False)
        view=ledger.current_reference(self.store,self.intake);self.assertEqual(view['status'],'unavailable');self.assertTrue(view['available'])
        self.assertEqual(view['record']['record_id'],first['record_id']);self.assertIsNone(view['current_observation']['snapshot_id'])
        self.assertIn('current_capture_unavailable',view['reason_codes']);self.assertIn('analysis_not_completed',view['reason_codes'])
        result=self.record('LATE-OLD',args=args,expected_head_record_id=first['record_id']);self.assertEqual(result['binding_status'],'historical_provided')

    def test_old_profile_is_preparation_unverified_not_a_head(self):
        with patch('labflow.intake_reference_snapshot.current_extraction_profile_id',return_value='b'*64):result=self.record()
        self.assertEqual(result['binding_status'],'preparation_unverified');self.assertFalse(result['append_observation']['preparation_ready']);self.assertEqual(self.counts(),(1,1,0))

    def test_unknown_provenance_preserves_synthetic_mode_and_blocks_head(self):
        with self.store.connection() as con:con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?',(self.job['documents'][0]['sha256'],))
        self.assertEqual(self.record()['binding_status'],'preparation_unverified')
        modes=ledger.reference_history(self.store,self.intake)['records'][0]['source_modes']
        self.assertEqual(modes,{'intake_revision_synthetic':True,'catalog_synthetic':True,'intake_provenance_status':'unconfirmed'})

    def test_unbound_priority_and_source_mode_unknown_are_not_successful_reference_selection(self):
        capture=read_intake_reference_snapshot(self.store,self.intake);capture=deepcopy(capture)
        capture['snapshot']['projection']['facts']['model']['value']='UNKNOWN-MODEL'
        capture['snapshot']['projection_sha256']=digest(capture['snapshot']['projection'])
        args=self.inputs(capture);self.assertEqual(args['reference_receipt']['status'],'insufficient_evidence')
        result=self.record(args=args);self.assertEqual(result['binding_status'],'reference_unbound');self.assertEqual(self.counts(),(1,1,0))
        self.assertFalse(result['verification']['mutable_state_verified_at_append'])

    def test_deferred_preparation_false_can_bind_reference_without_authority(self):
        respond(self.store,'DEFER-1','defer',intake_id=self.intake);result=self.record()
        self.assertEqual(result['binding_status'],'current_at_append');self.assertFalse(result['append_observation']['preparation_ready'])
        current=ledger.current_reference(self.store,self.intake);self.assertEqual(current['status'],'current');self.assertIn('intake_deferred',current['reason_codes'])

    def test_parent_receipt_mismatch_and_invalid_origin_rollback_new_schema(self):
        args=self.inputs();bad=deepcopy(args['reference_receipt']);bad['receipt_id']='f'*64
        self.error('parent_invalid',lambda:self.record(args=args,reference_receipt=bad));self.assertEqual(self.namespace(),[])
        capture=read_intake_reference_snapshot(self.store,self.intake);capture['snapshot']['result_sha256']='e'*64
        self.error('origin_invalid',lambda:self.record(args=self.inputs(capture)));self.assertEqual(self.namespace(),[])

    def test_two_valid_split_foreign_keys_do_not_authorize_a_cross_intake_job(self):
        folder=self.inbox/'two';folder.mkdir();(folder/'request.pdf').write_bytes(synthetic_pdf(['product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A']))
        scan_source(self.store,'INBOX',now=300);scan_source(self.store,'INBOX',now=302);job=claim_job(self.store,'OTHER',now=303)
        complete_job(self.store,job['job_id'],job['token'],SyntheticTextProvider().analyze(job),now=304)
        capture=read_intake_reference_snapshot(self.store,self.intake);capture['snapshot']['origin_job_id']=job['job_id']
        self.error('origin_invalid',lambda:self.record(args=self.inputs(capture)));self.assertEqual(self.namespace(),[])

    def test_partial_or_extra_schema_is_rejected_without_repair(self):
        with self.store.connection() as con:con.execute('CREATE TABLE '+R+'(fake TEXT)')
        for operation in [lambda:self.record(),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('schema_mismatch',operation)
        self.assertEqual(self.namespace(),[R])

    def test_case_variant_namespace_collision_is_not_reported_as_missing_ledger(self):
        with self.store.connection() as con:con.execute('CREATE TABLE INTAKE_REFERENCE_RECORDS(fake TEXT)')
        operations=[lambda:self.record(),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]
        for index,operation in enumerate(operations):
            with self.subTest(operation=index):self.error('schema_mismatch',operation)
        self.assertEqual(self.namespace(),['INTAKE_REFERENCE_RECORDS'])

    def test_atomic_ddl_record_event_and_head_failures_leave_no_namespace(self):
        args=self.inputs();connect=sqlite3.connect
        for action,target in [(sqlite3.SQLITE_CREATE_TABLE,H),(sqlite3.SQLITE_INSERT,R),(sqlite3.SQLITE_INSERT,E),(sqlite3.SQLITE_INSERT,H)]:
            with self.subTest(action=action,target=target):
                def opened(*values,**kwargs):
                    con=connect(*values,**kwargs)
                    con.set_authorizer(lambda op,name,_a,_b,_c:sqlite3.SQLITE_DENY if op==action and name==target else sqlite3.SQLITE_OK)
                    return con
                with patch('labflow.intake_reference_ledger.sqlite3.connect',side_effect=opened):self.error('storage_error',lambda:self.record(args=args))
                self.assertEqual(self.namespace(),[])

    def test_records_and_events_are_immutable_and_origins_cannot_be_deleted(self):
        self.record()
        for table in [R,E]:
            for verb in ['UPDATE '+table+' SET record_id=record_id','DELETE FROM '+table]:
                with self.assertRaises(sqlite3.IntegrityError),self.store.connection() as con:con.execute(verb)
        with self.assertRaises(sqlite3.IntegrityError),self.store.connection() as con:con.execute('DELETE FROM intake_jobs WHERE job_id=?',(self.job['job_id'],))

    def test_replay_history_current_reject_corrupt_summary_and_missing_event(self):
        args=self.inputs();self.record(args=args)
        self.edit(R,'UPDATE '+R+" SET summary_json='{}'")
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_missing_event_is_not_valid_history_or_replay_or_current(self):
        args=self.inputs();self.record(args=args);self.edit(E,'DELETE FROM '+E,delete=True)
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_nontext_head_timestamp_is_integrity_error_not_storage_error(self):
        args=self.inputs();self.record(args=args)
        with self.store.connection() as con:con.execute('UPDATE '+H+' SET updated_at=?',(b'not-a-timestamp',))
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_nontext_event_timestamp_is_integrity_error_not_storage_error(self):
        args=self.inputs();self.record(args=args);self.edit(E,'UPDATE '+E+' SET created_at=?',(b'not-a-timestamp',))
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_unknown_structured_provenance_enum_is_integrity_error(self):
        args=self.inputs();self.record(args=args)
        with self.store.connection() as con:row=con.execute('SELECT source_modes_json,summary_json FROM '+R).fetchone()
        modes=json.loads(row['source_modes_json']);modes['intake_provenance_status']=['unknown']
        summary=json.loads(row['summary_json']);summary['source_modes']=modes
        self.edit(R,'UPDATE '+R+' SET source_modes_json=?,source_modes_sha256=?,summary_json=?,summary_sha256=?',
            (canonical(modes),digest(modes),canonical(summary),digest(summary)))
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_matched_head_conflict_cannot_claim_a_different_captured_snapshot(self):
        args=self.inputs();self.record(args=args);second=self.record('SECOND',args=args)
        self.assertEqual(second['binding_status'],'head_conflict')
        with self.store.connection() as con:row=con.execute('SELECT append_json,summary_json FROM '+R+' WHERE record_id=?',(second['record_id'],)).fetchone()
        append=json.loads(row['append_json']);append['captured_snapshot_id']='a'*64
        summary=json.loads(row['summary_json']);summary['append_observation']=append
        self.edit(R,'UPDATE '+R+' SET append_json=?,append_sha256=?,summary_json=?,summary_sha256=? WHERE record_id=?',
            (canonical(append),digest(append),canonical(summary),digest(summary),second['record_id']))
        self.edit(E,'UPDATE '+E+' SET append_sha256=? WHERE record_id=?',(digest(append),second['record_id']))
        for operation in [lambda:self.record('SECOND',args=args),lambda:ledger.reference_history(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_stale_current_and_replay_reject_corrupt_private_payload_while_history_stays_metadata_only(self):
        args=self.inputs();self.record(args=args);self.edit(R,'UPDATE '+R+" SET snapshot_json='{}'")
        respond(self.store,'DEFER-LATER','defer',intake_id=self.intake)
        self.assertEqual(len(ledger.reference_history(self.store,self.intake)['records']),1)
        for operation in [lambda:self.record(args=args),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_head_cannot_silently_disappear_or_regress_to_an_old_publication(self):
        first=self.record();self.record('SECOND',expected_head_record_id=first['record_id'])
        with self.store.connection() as con:con.execute('DELETE FROM '+H)
        for operation in [lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('integrity_invalid',operation)

    def test_history_pagination_is_bounded_metadata_and_does_not_select_private_payloads(self):
        first=self.record();self.record('SECOND',expected_head_record_id=first['record_id']);self.record('THIRD')
        connect=sqlite3.connect;trace=[]
        def opened(*args,**kwargs):con=connect(*args,**kwargs);con.set_trace_callback(trace.append);return con
        with patch('labflow.intake_reference_ledger.sqlite3.connect',side_effect=opened):page=ledger.reference_history(self.store,self.intake,limit=2)
        self.assertEqual([r['seq'] for r in page['records']],[3,2]);self.assertEqual(page['next_before_seq'],2)
        tail=ledger.reference_history(self.store,self.intake,limit=2,before_seq=page['next_before_seq']);self.assertEqual([r['seq'] for r in tail['records']],[1]);self.assertIsNone(tail['next_before_seq'])
        self.assertTrue(all('snapshot_json' not in sql and 'receipt_json' not in sql for sql in trace))

    def test_reopen_and_two_process_cas_preserve_one_winner(self):
        args=self.inputs();wire={key:value for key,value in args.items() if key!='catalog'}
        packet=self.root/'private-request.json';packet.write_text(canonical(wire),encoding='utf-8')
        code="import json,sys; from pathlib import Path; from labflow.store import Store; from labflow.intake_reference_ledger import record_intake_reference; from tests.test_intake_case_references import catalog_fixture; a=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')); a['catalog']=catalog_fixture(); s=Store(sys.argv[1]); print(json.dumps(record_intake_reference(s,sys.argv[3],**a)))"
        children=[subprocess.Popen([sys.executable,'-X','utf8','-B','-c',code,str(self.store.root),str(packet),request],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8') for request in ['PROCESS-A','PROCESS-B']]
        try:
            outputs=[child.communicate(timeout=45) for child in children]
            self.assertTrue(all(child.returncode==0 for child in children),outputs)
        finally:
            for child in children:
                if child.poll() is None:child.kill();child.communicate()
        registrations=[json.loads(stdout) for stdout,_ in outputs]
        self.assertEqual(sorted(r['binding_status'] for r in registrations),['current_at_append','head_conflict'])
        reopened=Store(self.store.root);view=ledger.current_reference(reopened,self.intake)
        self.assertEqual(view['status'],'current');self.assertEqual(self.counts(),(2,2,1))

    def test_exact_argument_errors_and_input_limits_precede_store_io(self):
        args=self.inputs()
        for change in [{'expected_snapshot_id':'bad'},{'expected_head_record_id':False},{'producer_name':'bad name'}]:self.error('invalid_argument',lambda:self.record(args=args,**change))
        for options in [{'limit':True},{'limit':101},{'before_seq':False},{'before_seq':0}]:self.error('invalid_argument',lambda:ledger.reference_history(self.store,self.intake,**options))
        self.error('store_invalid',lambda:ledger.current_reference(object(),self.intake))
        self.error('intake_not_found',lambda:ledger.reference_history(self.store,'UNKNOWN'))
        self.error('input_limit',lambda:self.record(args=args,case_context={'oversize':'x'*(8*1024*1024+1)}))
        self.assertEqual(self.namespace(),[])

    def test_detached_dtos_and_metadata_contain_no_fact_values_or_tokens(self):
        args=self.inputs();registration=self.record(args=args);view=ledger.current_reference(self.store,self.intake)
        registration['append_observation']['expected_snapshot_id']='x';view['reference_receipt']['reason_codes'].append('MUTATED')
        self.assertNotIn('MUTATED',ledger.current_reference(self.store,self.intake)['reference_receipt']['reason_codes'])
        text=canonical(ledger.reference_history(self.store,self.intake))
        for value in ['MODEL-A',self.job['token'],str(self.root)]:self.assertNotIn(value,text)

    def test_maximum_requested_cases_and_ascii_identifiers_are_normal_inputs(self):
        packet,sources,_=report_fixture();original=packet['cases'][0]
        packet['cases']=[]
        for i in range(16):
            case=deepcopy(original);case['case_id']='CASE-'+str(i);packet['cases'].append(case)
        catalog=FccReportCaseCatalog(packet,sources);context=context_for(catalog,ids=[case['case_id'] for case in packet['cases']])
        wire=response_wire(context);wire['producer']['name']='P'*150
        response=decode_case_review_response(json.dumps(wire),context,producer_name='P'*150)
        result=self.record('R'*150,args=self.inputs(catalog=catalog,context=context,response=response))
        self.assertEqual(result['binding_status'],'current_at_append');self.assertEqual(len(ledger.current_reference(self.store,self.intake)['reference_receipt']['case_states']),16)

    def test_maximum_history_page_contains_100_genuine_publications(self):
        args=self.inputs()
        for index in range(100):self.record('PUBLICATION-'+str(index),args=args)
        page=ledger.reference_history(self.store,self.intake,limit=100)
        self.assertEqual(len(page['records']),100);self.assertEqual([r['seq'] for r in page['records']],list(range(100,0,-1)))
        self.assertIsNone(page['next_before_seq']);self.assertEqual(self.counts(),(100,100,1))

    def test_escaping_depth_nodes_and_nonplain_inputs_are_bounded_before_sql(self):
        args=self.inputs();nested=None
        for _ in range(26):nested=[nested]
        cases=[{'escaped':'\0'*1400000},nested,{'nodes':[None]*500001}]
        with patch('labflow.intake_reference_ledger.sqlite3.connect',side_effect=AssertionError('SQL before input validation')):
            for value in cases:self.error('input_limit',lambda:self.record(args=args,case_context=value))
            class Nonplain(dict):pass
            self.error('parent_invalid',lambda:self.record(args=args,case_context=Nonplain()))
            self.error('parent_invalid',lambda:self.record(args=args,case_context={'number':float('nan')}))
        self.assertEqual(self.namespace(),[])

    def test_replaced_db_identity_rolls_back_and_owned_connection_is_closed(self):
        args=self.inputs();connect=sqlite3.connect;opened=[]
        def connection(*values,**kwargs):con=connect(*values,**kwargs);opened.append(con);return con
        with patch('labflow.intake_reference_ledger._identity',side_effect=[(1,1),(1,1),(1,2)]), \
             patch('labflow.intake_reference_ledger.sqlite3.connect',side_effect=connection):self.error('storage_error',lambda:self.record(args=args))
        self.assertEqual(self.namespace(),[]);self.assertEqual(len(opened),1)
        with self.assertRaises(sqlite3.ProgrammingError):opened[0].execute('SELECT 1')

    def test_live_wal_readers_and_replay_leave_application_rows_and_blobs_unchanged(self):
        with closing(sqlite3.connect(self.store.db)) as keepalive:
            keepalive.execute('PRAGMA journal_mode=WAL');args=self.inputs();self.record(args=args)
            with self.store.connection() as con:before='\n'.join(con.iterdump())
            blobs={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (self.store.root/'blobs').iterdir()}
            ledger.reference_history(self.store,self.intake);ledger.current_reference(self.store,self.intake);self.record(args=args)
            with self.store.connection() as con:self.assertEqual('\n'.join(con.iterdump()),before)
            self.assertEqual({path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (self.store.root/'blobs').iterdir()},blobs)

    def test_historical_source_global_budget_is_input_limit(self):
        args=self.inputs();old=self.store.blob_path(self.job['documents'][0]['sha256']);self.revision('NEW')
        old.write_bytes(b'x'*(16*1024*1024+1))
        self.error('input_limit',lambda:self.record(args=args));self.assertEqual(self.namespace(),[])

    def test_sql_event_and_payload_byte_budgets_precede_decode(self):
        args=self.inputs();result=self.record(args=args)
        self.edit(E,'UPDATE '+E+' SET created_at=?',('x'*5000,))
        for operation in [lambda:self.record(args=args),lambda:ledger.reference_history(self.store,self.intake),lambda:ledger.current_reference(self.store,self.intake)]:self.error('input_limit',operation)
        self.edit(E,'UPDATE '+E+' SET created_at=?',(result['append_observation']['observed_at'],))
        self.edit(R,'UPDATE '+R+' SET snapshot_json=?',('x'*(9*1024*1024+1),))
        self.assertEqual(len(ledger.reference_history(self.store,self.intake)['records']),1)
        for operation in [lambda:self.record(args=args),lambda:ledger.current_reference(self.store,self.intake)]:self.error('input_limit',operation)

    def test_context_mismatch_retains_null_catalog_provenance_in_unbound_receipt(self):
        other=catalog_fixture(two=True);context=context_for(other);response=response_for(context)
        args=self.inputs(context=context,response=response)
        self.assertEqual(args['reference_receipt']['status'],'insufficient_evidence');self.assertIsNone(args['reference_receipt']['case_binding']['catalog_synthetic'])
        self.assertEqual(self.record(args=args)['binding_status'],'reference_unbound')
        self.assertIsNone(ledger.reference_history(self.store,self.intake)['records'][0]['source_modes']['catalog_synthetic'])


if __name__=='__main__':unittest.main()
