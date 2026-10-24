"""Real SQLite transactions over synthetic retained PDF workflow fixtures."""
from copy import deepcopy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import intake_reference_snapshot as snapshot
from labflow.active_intake import register_source,scan_source
from labflow.intake_jobs import claim_job,complete_job,respond
from labflow.intake_worker import SyntheticTextProvider
from labflow.intake_documents import current_extraction_profile_id
from labflow.intake_case_references import build_intake_case_reference_receipt
from labflow.store import Store,canonical
from tests.test_document_extract import synthetic_pdf
from tests.test_intake_case_references import catalog_fixture,context_for,response_for


TOP={'schema_version','kind','status','reason_codes','snapshot_id','snapshot','origin','state','delegation','profile','readiness','verification','limits'}
FALSE=('operational_authority_granted','model_execution_verified','evaluation_executed')


def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


class ReferenceSnapshotTests(unittest.TestCase):
    def setUp(self):
        local=Path(__file__).resolve().parents[1]/'.local';local.mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(prefix='snapshot034-',dir=local);self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.store=Store(self.root/'state');self.inbox=self.root/'inbox';self.inbox.mkdir()
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)
        self.intake,self.job,self.analysis=self.complete('one');respond(self.store,'PROCEED-1','proceed',intake_id=self.intake)

    def complete(self,name,*,text=False,force_v2=False,pages=None):
        folder=self.inbox/name;folder.mkdir()
        content='product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A'
        if text:(folder/'request.txt').write_text(content,encoding='utf-8')
        else:(folder/'request.pdf').write_bytes(synthetic_pdf([content] if pages is None else pages))
        scan_source(self.store,'INBOX',now=100);scan_source(self.store,'INBOX',now=102)
        job=claim_job(self.store,'WORKER',now=103);analysis=SyntheticTextProvider().analyze(job)
        if force_v2:
            analysis['schema_version']=2;analysis['context_id']=job['analysis_context_id']
            for fact in analysis['facts']:
                for evidence in fact['evidence']:evidence['kind']='text_line'
        complete_job(self.store,job['job_id'],job['token'],analysis,now=104)
        return job['intake_id'],job,analysis

    def read(self,**kwargs):return snapshot.read_intake_reference_snapshot(self.store,self.intake,**kwargs)

    def error(self,code,operation):
        with self.assertRaises(snapshot.IntakeReferenceStateError) as caught:operation()
        e=caught.exception;expected='intake_reference_state_'+code
        self.assertEqual((e.code,str(e),e.args),(expected,expected,(expected,)));self.assertIsNone(e.__context__)
        self.assertNotIn(str(self.root),repr(e));self.assertNotIn('PRIVATE-SYNTHETIC',repr(e))

    def files(self):
        return {str(p.relative_to(self.store.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size,p.stat().st_mtime_ns)
                for p in self.store.root.rglob('*') if p.is_file()}

    def dump(self):
        with closing(sqlite3.connect(self.store.db.as_uri()+'?mode=ro',uri=True)) as con:return '\n'.join(con.iterdump())

    def test_exact_observed_capture_and_private032_snapshot(self):
        x=self.read();self.assertEqual(set(x),TOP);self.assertEqual((x['schema_version'],x['kind'],x['status']),(1,'intake_reference_snapshot_capture','observed'))
        for key,count in [('origin',5),('state',6),('delegation',3),('profile',3),('readiness',5),('verification',8),('limits',11),('snapshot',13)]:self.assertEqual(len(x[key]),count)
        self.assertTrue(x['readiness']['ready']);self.assertEqual(x['readiness']['kind'],'reference_preparation_v1')
        self.assertEqual(x['snapshot']['readiness_fingerprint'],x['readiness']['reference_state_fingerprint'])
        for key,value in x['verification'].items():self.assertIs(value,key not in FALSE)
        basis={k:x[k] for k in ['schema_version','kind','snapshot','origin','state','delegation','profile','readiness']}
        self.assertEqual(x['snapshot_id'],digest(basis));self.assertEqual(x['snapshot_id'],self.read()['snapshot_id'])

    def test_same_snapshot_binds032_without_changing032_authority_flags(self):
        x=self.read();catalog=catalog_fixture();context=context_for(catalog);response=response_for(context)
        r=build_intake_case_reference_receipt(x['snapshot'],catalog,context,response,producer_name=response['expected_producer']['name'])
        self.assertEqual(r['status'],'bound');self.assertFalse(r['verification']['database_currentness_verified'])
        self.assertFalse(r['verification']['operational_authority_granted']);self.assertIsNone(r['evaluation']['score'])

    def test_no_store_connection_creation_or_application_write_or_pdf_parser(self):
        before=self.files();dump=self.dump();forbidden=AssertionError('unexpected write/parse')
        with patch.object(Store,'__init__',side_effect=forbidden),patch.object(Store,'connection',side_effect=forbidden), \
             patch.object(Store,'write_blob',side_effect=forbidden),patch.object(Store,'register_blob',side_effect=forbidden), \
             patch.object(Store,'event',side_effect=forbidden),patch('labflow.document_extract.extract_document',side_effect=forbidden), \
             patch('labflow.intake_documents.extract_document',side_effect=forbidden),patch.object(SyntheticTextProvider,'analyze',side_effect=forbidden):
            self.assertEqual(self.read()['status'],'observed')
        self.assertEqual(self.files(),before);self.assertEqual(self.dump(),dump)

    def test_missing_database_is_not_created(self):
        self.store.db.unlink();before=set(self.store.root.iterdir())
        self.error('storage_error',lambda:self.read());self.assertFalse(self.store.db.exists());self.assertEqual(set(self.store.root.iterdir()),before)

    def test_upper_reader_opens_mode_ro_and_never_immutable(self):
        original=sqlite3.connect;seen=[]
        def connect(*args,**kwargs):seen.append((args,kwargs));return original(*args,**kwargs)
        with patch('labflow.intake_reference_snapshot.sqlite3.connect',side_effect=connect):self.read()
        self.assertEqual(len(seen),1);self.assertIn('mode=ro',str(seen[0][0][0]));self.assertNotIn('immutable',str(seen))

    def test_same_connection_leaves_transaction_row_factory_and_options_unchanged(self):
        with closing(sqlite3.connect(self.store.db)) as con:
            con.execute('BEGIN');before=(con.in_transaction,con.row_factory,con.isolation_level,con.total_changes)
            trace=[];con.set_trace_callback(trace.append)
            x=snapshot.capture_intake_reference_snapshot_in_transaction(self.store,con,self.intake)
            self.assertEqual((con.in_transaction,con.row_factory,con.isolation_level,con.total_changes),before)
            self.assertEqual(x['status'],'observed');self.assertTrue(all(q.lstrip().upper().startswith('SELECT') or q=='-- PRAGMA database_list' for q in trace))
            con.set_trace_callback(None);con.rollback()

    def test_wrong_connection_or_absent_transaction_is_rejected(self):
        with closing(sqlite3.connect(self.store.db)) as con:self.error('transaction_required',lambda:snapshot.capture_intake_reference_snapshot_in_transaction(self.store,con,self.intake))
        with closing(sqlite3.connect(':memory:')) as con:
            con.execute('BEGIN');self.error('transaction_required',lambda:snapshot.capture_intake_reference_snapshot_in_transaction(self.store,con,self.intake))
        self.error('transaction_required',lambda:snapshot.capture_intake_reference_snapshot_in_transaction(self.store,object(),self.intake))

    def test_arguments_are_checked_before_database_reads(self):
        for kwargs in [{'expected_revision':True,'expected_result_sha256':'a'*64},{'expected_revision':1},{'expected_result_sha256':'a'*64},{'expected_revision':1,'expected_result_sha256':'bad'}]:
            self.error('invalid_argument',lambda:self.read(**kwargs))
        self.error('invalid_argument',lambda:snapshot.read_intake_reference_snapshot(self.store,'../bad'))
        self.error('store_invalid',lambda:snapshot.read_intake_reference_snapshot(object(),self.intake))
        self.error('intake_not_found',lambda:snapshot.read_intake_reference_snapshot(self.store,'UNKNOWN'))

    def test_expected_stale_returns_actual_snapshot_but_does_not_rebind(self):
        x=self.read();stale=self.read(expected_revision=2,expected_result_sha256='a'*64)
        self.assertEqual(stale['status'],'stale');self.assertEqual(stale['snapshot_id'],x['snapshot_id'])
        self.assertEqual(stale['snapshot'],x['snapshot']);self.assertIn('expected_revision_changed',stale['reason_codes'])
        self.assertIn('expected_result_changed',stale['reason_codes'])

    def test_result_hash_preserves_original_whitespace_bytes(self):
        with self.store.connection() as con:
            raw=con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(self.job['job_id'],)).fetchone()[0]
            raw='\n'+raw+' ';con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(raw,self.job['job_id']))
        x=self.read();self.assertEqual(x['snapshot']['result_sha256'],hashlib.sha256(raw.encode()).hexdigest())

    def test_genuine_answer_changes_projection_and_snapshot_without_changing_origin(self):
        before=self.read();respond(self.store,'ANSWER-1','answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        after=self.read();self.assertEqual(after['status'],'observed');self.assertNotEqual(after['snapshot_id'],before['snapshot_id'])
        self.assertEqual(after['origin'],before['origin']);self.assertEqual(after['snapshot']['projection']['facts']['model']['status'],'user_confirmed')
        self.assertEqual(after['snapshot']['projection']['facts']['model']['event_id'],'ANSWER-1')

    def test_unused_old_answer_basis_is_hashed_but_not_promoted(self):
        respond(self.store,'ANSWER-1','answer',intake_id=self.intake,answers={'model':'MODEL-B'});before=self.read()
        with self.store.connection() as con:
            basis=json.loads(con.execute('SELECT basis_json FROM intake_answers WHERE intake_id=?',(self.intake,)).fetchone()[0]);basis['identity']='unknown'
            con.execute('UPDATE intake_answers SET basis_json=? WHERE intake_id=?',(canonical(basis),self.intake))
        # Refresh through a real user event; stale basis remains but is not used.
        respond(self.store,'PROCEED-2','proceed',intake_id=self.intake)
        after=self.read();self.assertNotEqual(after['state']['answers_sha256'],before['state']['answers_sha256'])
        self.assertEqual(after['snapshot']['projection']['facts']['model']['value'],'MODEL-A')
        self.assertEqual(after['snapshot']['projection']['facts']['model']['status'],'explicit')

    def test_defer_and_proceed_change_observed_preparation(self):
        first=self.read();respond(self.store,'DEFER-1','defer',intake_id=self.intake);deferred=self.read()
        self.assertEqual(deferred['status'],'observed');self.assertFalse(deferred['readiness']['ready']);self.assertIn('intake_deferred',deferred['readiness']['reason_codes'])
        self.assertNotEqual(first['snapshot_id'],deferred['snapshot_id'])
        respond(self.store,'PROCEED-2','proceed',intake_id=self.intake);self.assertTrue(self.read()['readiness']['ready'])

    def test_no_delegation_is_valid_observation_with_ready_false(self):
        intake,_,_=self.complete('two');x=snapshot.read_intake_reference_snapshot(self.store,intake)
        self.assertEqual(x['status'],'observed');self.assertFalse(x['readiness']['ready']);self.assertIn('delegation_missing',x['readiness']['reason_codes'])

    def test_old_profile_is_retained_but_preparation_false(self):
        with patch('labflow.intake_reference_snapshot.current_extraction_profile_id',return_value='b'*64):x=self.read()
        self.assertEqual(x['status'],'observed');self.assertFalse(x['profile']['matches']);self.assertFalse(x['readiness']['ready'])
        self.assertIn('profile_changed',x['reason_codes'])

    def test_profile_change_during_validation_is_an_error(self):
        current=current_extraction_profile_id()
        with patch('labflow.intake_reference_snapshot.current_extraction_profile_id',side_effect=[current,'b'*64]):self.error('source_integrity_invalid',lambda:self.read())

    def test_v1_and_v2_without_pdf_are_unavailable(self):
        for text,force,reason in [(True,False,'legacy_analysis'),(True,True,'no_pdf_context')]:
            intake,_,_=self.complete('text-'+str(force),text=text,force_v2=force)
            x=snapshot.read_intake_reference_snapshot(self.store,intake);self.assertEqual(x['status'],'unavailable');self.assertIsNone(x['snapshot'])
            self.assertIsNone(x['snapshot_id']);self.assertIn(reason,x['reason_codes'])

    def test_noncompleted_current_job_is_unavailable(self):
        with self.store.connection() as con:con.execute("UPDATE intake_jobs SET state='failed' WHERE job_id=?",(self.job['job_id'],))
        x=self.read();self.assertEqual(x['status'],'unavailable');self.assertIsNone(x['snapshot_id']);self.assertIn('analysis_not_completed',x['reason_codes'])

    def test_unread_pdf_is_not_ready_and_not_fabricated(self):
        intake,_,_=self.complete('empty',pages=['']);x=snapshot.read_intake_reference_snapshot(self.store,intake)
        self.assertEqual(x['status'],'observed');self.assertFalse(x['readiness']['ready']);self.assertIn('unread_documents',x['readiness']['reason_codes'])

    def test_live_projection_tampering_is_fixed_error(self):
        with self.store.connection() as con:
            live=json.loads(con.execute('SELECT analysis_json FROM intakes WHERE intake_id=?',(self.intake,)).fetchone()[0]);live['facts']['model']['value']='PRIVATE-SYNTHETIC'
            con.execute('UPDATE intakes SET analysis_json=? WHERE intake_id=?',(canonical(live),self.intake))
        self.error('projection_inconsistent',lambda:self.read())

    def test_forged_answer_event_or_value_is_fixed_error(self):
        respond(self.store,'ANSWER-1','answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        with self.store.connection() as con:con.execute("UPDATE intake_answers SET event_id='MISSING' WHERE intake_id=?",(self.intake,))
        self.error('delegation_invalid',lambda:self.read())

    def test_later_recorded_field_cannot_hide_behind_an_older_answer_row(self):
        respond(self.store,'ANSWER-MODEL','answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        respond(self.store,'ANSWER-PURPOSE','answer',intake_id=self.intake,answers={'purpose':'development'})
        self.assertTrue(self.read()['readiness']['ready'])
        with self.store.connection() as con:
            request=json.loads(con.execute("SELECT request_json FROM intake_responses WHERE event_id='ANSWER-PURPOSE'").fetchone()[0])
            request['answers']['model']='MODEL-C'
            con.execute("UPDATE intake_responses SET request_json=? WHERE event_id='ANSWER-PURPOSE'",(canonical(request),))
        self.error('delegation_invalid',lambda:self.read())

    def test_latest_recorded_answer_field_cannot_be_missing_from_current_rows(self):
        respond(self.store,'ANSWER-MULTI','answer',intake_id=self.intake,answers={'model':'MODEL-B','purpose':'development'})
        with self.store.connection() as con:con.execute("DELETE FROM intake_answers WHERE intake_id=? AND field='model'",(self.intake,))
        # Public refresh makes the live projection consistent with the missing row.
        respond(self.store,'PROCEED-REFRESH','proceed',intake_id=self.intake)
        self.error('delegation_invalid',lambda:self.read())

    def test_current_answer_cannot_restore_a_valid_older_event_and_value(self):
        respond(self.store,'ANSWER-OLD','answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        with self.store.connection() as con:old=con.execute("SELECT value,basis_json,event_id FROM intake_answers WHERE intake_id=? AND field='model'",(self.intake,)).fetchone()
        respond(self.store,'ANSWER-NEW','answer',intake_id=self.intake,answers={'model':'MODEL-C'})
        with self.store.connection() as con:con.execute("UPDATE intake_answers SET value=?,basis_json=?,event_id=? WHERE intake_id=? AND field='model'",(*old,self.intake))
        respond(self.store,'PROCEED-REFRESH','proceed',intake_id=self.intake)
        self.error('delegation_invalid',lambda:self.read())

    def test_same_value_still_requires_the_latest_recorded_answer_event(self):
        for event in ['ANSWER-OLD','ANSWER-NEW']:
            respond(self.store,event,'answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        with self.store.connection() as con:con.execute("UPDATE intake_answers SET event_id='ANSWER-OLD' WHERE intake_id=? AND field='model'",(self.intake,))
        respond(self.store,'PROCEED-REFRESH','proceed',intake_id=self.intake)
        self.error('delegation_invalid',lambda:self.read())

    def test_clean_repeated_multi_field_answers_keep_latest_event_and_strip_values(self):
        respond(self.store,'ANSWER-OLD','answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        respond(self.store,'ANSWER-MULTI','answer',intake_id=self.intake,answers={'model':'  MODEL-B  ','purpose':' development '})
        respond(self.store,'ANSWER-PURPOSE','answer',intake_id=self.intake,answers={'purpose':'development'})
        result=self.read();fact=result['snapshot']['projection']['facts']['model']
        self.assertEqual((fact['value'],fact['event_id']),('MODEL-B','ANSWER-MULTI'))
        self.assertEqual(result['status'],'observed');self.assertTrue(result['readiness']['ready'])

    def test_latest_answer_uses_database_event_sequence_not_response_identifier_order(self):
        respond(self.store,'Z-LAST-ALPHABETICALLY','answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        respond(self.store,'A-LATEST-RECORDED','answer',intake_id=self.intake,answers={'model':'MODEL-C'})
        result=self.read();fact=result['snapshot']['projection']['facts']['model']
        self.assertEqual((fact['value'],fact['event_id']),('MODEL-C','A-LATEST-RECORDED'))
        self.assertTrue(result['readiness']['ready'])

    def test_delegation_flags_cannot_outlive_corresponding_evidence(self):
        with self.store.connection() as con:con.execute("DELETE FROM intake_responses WHERE event_id='PROCEED-1'")
        self.error('delegation_invalid',lambda:self.read())

    def test_original_corruption_is_rejected_without_parser(self):
        raw=self.store.blob_path(self.job['documents'][0]['sha256']);raw.write_bytes(b'PRIVATE-SYNTHETIC')
        self.error('source_integrity_invalid',lambda:self.read())

    def test_original_change_after_parent_validation_is_detected(self):
        real=snapshot.validate_retained_analysis
        def change(store,row):
            answer=real(store,row);store.blob_path(self.job['documents'][0]['sha256']).write_bytes(b'PRIVATE-SYNTHETIC');return answer
        with patch('labflow.intake_reference_snapshot.validate_retained_analysis',side_effect=change):self.error('source_integrity_invalid',lambda:self.read())

    def test_blob_provenance_change_is_observed_without_reclassification(self):
        before=self.read()
        with self.store.connection() as con:con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?',(self.job['documents'][0]['sha256'],))
        x=self.read();self.assertNotEqual(x['snapshot_id'],before['snapshot_id']);self.assertTrue(x['snapshot']['synthetic'])
        self.assertFalse(x['readiness']['ready']);self.assertIn('source_provenance_unconfirmed',x['reason_codes'])

    def test_sql_byte_row_and_escaping_limits_are_enforced(self):
        with self.store.connection() as con:con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',('x'*(8*1024*1024+1),self.job['job_id']))
        self.error('input_limit',lambda:self.read())

    def test_same_read_transaction_observes_one_wal_snapshot_then_next_read_changes(self):
        with closing(sqlite3.connect(self.store.db)) as writer:writer.execute('PRAGMA journal_mode=WAL')
        with closing(sqlite3.connect(self.store.db.as_uri()+'?mode=ro',uri=True)) as con:
            con.execute('BEGIN');first=snapshot.capture_intake_reference_snapshot_in_transaction(self.store,con,self.intake)
            respond(self.store,'DEFER-WAL','defer',intake_id=self.intake)
            second=snapshot.capture_intake_reference_snapshot_in_transaction(self.store,con,self.intake)
            self.assertEqual(first['snapshot_id'],second['snapshot_id']);self.assertTrue(con.in_transaction);con.rollback()
        current=self.read();self.assertNotEqual(current['snapshot_id'],first['snapshot_id']);self.assertTrue(current['state']['deferred'])

    def test_reopen_existing_store_has_same_observed_state(self):
        before=self.read();reopened=Store(self.store.root)
        after=snapshot.read_intake_reference_snapshot(reopened,self.intake);self.assertEqual(before['snapshot_id'],after['snapshot_id'])

    def test_detached_values_and_no_token_paths_in_metadata(self):
        first=self.read();second=self.read();first['snapshot']['projection']['facts']['model']['value']='CHANGED'
        self.assertEqual(self.read(),second)
        summary={k:v for k,v in second.items() if k!='snapshot'};text=canonical(summary)
        self.assertNotIn('MODEL-A',text);self.assertNotIn(self.job['token'],text);self.assertNotIn(str(self.root),text)

    def test_database_identity_change_is_not_returned_as_current(self):
        with patch('labflow.intake_reference_snapshot._db_identity',side_effect=[(1,1),(1,1),(1,2)]):
            self.error('storage_error',lambda:self.read())

    def test_question_row_limit_is_checked_before_materializing(self):
        with self.store.connection() as con:
            con.executemany('INSERT INTO intake_questions VALUES(?,?,?,?,?)',[(self.intake,'Q-'+str(i),canonical({'key':'Q-'+str(i)}),'resolved',1) for i in range(10001)])
        self.error('input_limit',lambda:self.read())

    def test_answer_row_limit_is_checked_before_interpretation(self):
        with self.store.connection() as con:
            con.executemany('INSERT INTO intake_answers VALUES(?,?,?,?,?)',[(self.intake,'EXTRA-'+str(i),'x','{}','UNKNOWN') for i in range(11)])
        self.error('input_limit',lambda:self.read())

    def test_canonical_escaping_limit_precedes_answer_interpretation(self):
        with self.store.connection() as con:
            con.execute('INSERT INTO intake_answers VALUES(?,?,?,?,?)',(self.intake,'model','\x00'*(1500000),'{}','UNKNOWN'))
        self.error('input_limit',lambda:self.read())

    def test_state_evidence_category_limit_is_checked_before_parsing(self):
        with self.store.connection() as con:
            con.execute("UPDATE intake_responses SET request_json=? WHERE event_id='PROCEED-1'",('x'*(8*1024*1024+1),))
        self.error('input_limit',lambda:self.read())

    def test_separate_process_observes_same_snapshot_after_caller_reopens_store(self):
        before=self.read()
        code="import json,sys; from labflow.store import Store; from labflow.intake_reference_snapshot import read_intake_reference_snapshot; s=Store(sys.argv[1]); r=read_intake_reference_snapshot(s,sys.argv[2]); print(json.dumps({'snapshot_id':r['snapshot_id'],'status':r['status']}))"
        run=subprocess.run([sys.executable,'-X','utf8','-B','-c',code,str(self.store.root),self.intake],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stderr)
        after=json.loads(run.stdout);self.assertEqual(after,{'snapshot_id':before['snapshot_id'],'status':'observed'})

    def test_user_confirmed_event_inherits_stricter032_identifier_limit(self):
        respond(self.store,'E'*129,'answer',intake_id=self.intake,answers={'model':'MODEL-B'})
        self.error('input_limit',lambda:self.read())

    def test_missing_registered_blob_provenance_is_not_an_actual_source_default(self):
        with self.store.connection() as con:con.execute('DELETE FROM blobs WHERE sha256=?',(self.job['documents'][0]['sha256'],))
        self.error('source_integrity_invalid',lambda:self.read())

    def test_non_boolean_state_flags_are_not_truthy_delegation(self):
        with self.store.connection() as con:con.execute('UPDATE intakes SET delegated=2 WHERE intake_id=?',(self.intake,))
        self.error('delegation_invalid',lambda:self.read())

    def test_source_file_global_budget_is_input_limit_not_hidden_integrity_error(self):
        self.store.blob_path(self.job['documents'][0]['sha256']).write_bytes(b'x'*(16*1024*1024+1))
        self.error('input_limit',lambda:self.read())

    def test_enlarged_corrupt_source_below_global_limit_remains_integrity_error(self):
        path=self.store.blob_path(self.job['documents'][0]['sha256']);path.write_bytes(path.read_bytes()+b'changed')
        self.error('source_integrity_invalid',lambda:self.read())


if __name__=='__main__':unittest.main()
