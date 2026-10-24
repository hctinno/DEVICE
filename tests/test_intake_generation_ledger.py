"""Explicit completed PDF imports preserve existing data and immutable history."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing,contextmanager
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from labflow import intake_documents
from labflow.active_intake import register_source,scan_source
from labflow.intake_jobs import claim_job,complete_job,respond
from labflow.intake_worker import SyntheticTextProvider
from labflow.store import Store,canonical
from test_intake_documents import pdf


@unittest.skipUnless(importlib.util.find_spec('pypdf') is not None,'Optional pypdf is not installed')
class GenerationLedgerTests(unittest.TestCase):
    def setUp(self):
        local=Path(__file__).resolve().parents[1]/'.local';local.mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(prefix='ledger-test-',dir=local)
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.inbox=self.root/'inbox';self.inbox.mkdir();self.store=Store(self.root/'state')
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)
        self.job,self.analysis=self.finish()
        self.intake=self.job['intake_id']
        respond(self.store,'answer','answer',intake_id=self.intake,answers={'market':'US'})
        respond(self.store,'proceed','proceed',intake_id=self.intake)
        with self.store.connection() as con:
            self._saved_result=con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(self.job['job_id'],)).fetchone()[0]

    def finish(self,revision=1,folder='one',payload=None,path='request.pdf'):
        target=self.inbox/folder;target.mkdir(exist_ok=True)
        (target/path).write_bytes(payload if payload is not None else pdf([
            'product_type: smartphone\nmodel: SM-A176U','purpose: certification\nrevision: '+str(revision)]))
        scan_source(self.store,'INBOX',now=100+revision*10);scan_source(self.store,'INBOX',now=102+revision*10)
        job=claim_job(self.store,'worker',now=103+revision*10);analysis=SyntheticTextProvider().analyze(job)
        complete_job(self.store,job['job_id'],job['token'],analysis,now=104+revision*10)
        return job,analysis

    def module(self):return importlib.import_module('labflow.intake_generation_ledger')

    def result_hash(self,job=None):
        with self.store.connection() as con:
            result=con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',((job or self.job)['job_id'],)).fetchone()[0]
        return hashlib.sha256(result.encode('utf-8')).hexdigest()

    def rows(self):
        with self.store.connection() as con:
            tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'intake_analysis_%' ORDER BY name")]
            return {name:[dict(r) for r in con.execute('SELECT * FROM '+name+' ORDER BY rowid')] for name in tables}

    def original_hashes(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for source in (self.inbox,self.store.root/'blobs') for p in source.rglob('*') if p.is_file()}

    def no_ledger(self):
        with self.store.connection() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'intake_analysis_%'").fetchone()[0],0)

    def receipt(self,**changes):
        return self.module().import_completed_generation(self.store,self.intake,
            **{'expected_revision':self.job['revision'],'expected_result_sha256':self.result_hash(),**changes})

    def public(self,value):
        text=canonical(value)
        for secret in (str(self.root),self.job['token'],'SM-A176U','smartphone','certification'):
            self.assertNotIn(secret,text)

    def test_actual_import_preserves_all_existing_rows_sources_and_blobs(self):
        module=self.module();before=self.rows();blobs=self.original_hashes()
        denied=AssertionError('ledger attempted parse/provider/source write')
        with patch.object(Store,'__init__',side_effect=denied),patch.object(self.store,'write_blob',side_effect=denied),\
             patch.object(self.store,'register_blob',side_effect=denied),patch.object(intake_documents,'extract_document',side_effect=denied),\
             patch('labflow.document_extract.extract_document',side_effect=denied),patch.object(SyntheticTextProvider,'analyze',side_effect=denied):
            receipt=self.receipt()
        self.assertEqual(self.rows(),before);self.assertEqual(self.original_hashes(),blobs)
        self.assertEqual(set(receipt),{'schema_version','kind','intake_id','revision','generation_id','epoch',
             'origin_job_id','context_id','profile_id','result_sha256','synthetic','snapshot_scope'})
        self.assertEqual((receipt['schema_version'],receipt['kind'],receipt['epoch']),(1,'intake_analysis_generation_import',0))
        self.assertEqual(receipt['context_id'],self.analysis['context_id']);self.assertTrue(receipt['synthetic'])
        self.assertEqual(receipt['snapshot_scope'],'migration_time');self.public(receipt)
        with self.store.connection() as con:
            row=con.execute('SELECT * FROM intake_analysis_generations').fetchone()
            self.assertEqual(row['result_json'],before['intake_jobs'][0]['result_json'])
            self.assertEqual(row['token_sha256'],hashlib.sha256(self.job['token'].encode()).hexdigest())
            snapshot=json.loads(row['snapshot_json']);self.assertEqual(snapshot['questions'],before['intake_questions'])
            self.assertEqual(snapshot['answers'],before['intake_answers']);self.assertEqual(snapshot['notifications'],before['intake_notifications'])
            self.assertEqual(con.execute('SELECT count(*) FROM intake_analysis_requests').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT count(*) FROM intake_analysis_events').fetchone()[0],1)
        history=module.generation_history(self.store,self.intake)
        self.assertEqual(history['records'],[receipt]);self.assertTrue(history['available']);self.public(history)

    def test_history_without_ledger_is_read_only_and_does_not_initialize(self):
        module=self.module();before=self.rows();db=self.store.db.read_bytes();files=self.original_hashes()
        value=module.generation_history(self.store,self.intake)
        self.assertEqual(value,{'schema_version':1,'kind':'intake_analysis_generation_history','intake_id':self.intake,
                              'available':False,'records':[],'next_before_epoch':None})
        self.no_ledger();self.assertEqual(self.rows(),before);self.assertEqual(self.store.db.read_bytes(),db)
        self.assertEqual(self.original_hashes(),files)

    def test_repeat_and_eight_concurrent_imports_have_one_receipt_head_and_event(self):
        module=self.module();sha=self.result_hash()
        with ThreadPoolExecutor(max_workers=8) as pool:
            values=list(pool.map(lambda _:module.import_completed_generation(self.store,self.intake,
                expected_revision=1,expected_result_sha256=sha),range(8)))
        self.assertTrue(all(value==values[0] for value in values));self.assertEqual(self.receipt(),values[0])
        with self.store.connection() as con:
            for table in ('intake_analysis_generations','intake_analysis_heads','intake_analysis_events'):
                self.assertEqual(con.execute('SELECT count(*) FROM '+table).fetchone()[0],1)

    def test_stale_profile_is_validated_without_current_parser(self):
        with patch.object(intake_documents.importlib.metadata,'version',return_value='synthetic-new-parser'):
            receipt=self.receipt()
        self.assertEqual(receipt['context_id'],self.analysis['context_id']);self.public(receipt)

    def test_revision_epochs_and_strict_limit_one_cursor_preserve_both_origins(self):
        first=self.receipt();self.job,self.analysis=self.finish(revision=2);second=self.receipt()
        self.assertEqual((first['epoch'],second['epoch']),(0,1));self.assertNotEqual(first['generation_id'],second['generation_id'])
        module=self.module();page=module.generation_history(self.store,self.intake,limit=1)
        self.assertEqual(page['records'],[second]);self.assertEqual(page['next_before_epoch'],1)
        older=module.generation_history(self.store,self.intake,limit=1,before_epoch=page['next_before_epoch'])
        self.assertEqual(older['records'],[first]);self.assertIsNone(older['next_before_epoch'])
        self.assertEqual(module.generation_history(self.store,self.intake,before_epoch=0)['records'],[])
        with self.store.connection() as con:
            heads=[tuple(row) for row in con.execute('SELECT revision,generation_id FROM intake_analysis_heads ORDER BY revision')]
        self.assertEqual(heads,[(1,first['generation_id']),(2,second['generation_id'])])

    def test_completion_time_is_exact_matching_event_or_null_if_missing_or_ambiguous(self):
        with self.store.connection() as con:
            event=dict(con.execute("SELECT * FROM events WHERE action='intake.analysis_completed'").fetchone())
        self.receipt()
        with self.store.connection() as con:
            row=con.execute('SELECT origin_created_at,origin_completed_at,imported_at FROM intake_analysis_generations').fetchone()
            self.assertEqual(row['origin_completed_at'],event['created_at']);self.assertIsNotNone(row['imported_at'])

    def test_missing_completion_event_remains_null(self):
        with self.store.connection() as con:con.execute("DELETE FROM events WHERE action='intake.analysis_completed'")
        self.receipt()
        with self.store.connection() as con:self.assertIsNone(con.execute('SELECT origin_completed_at FROM intake_analysis_generations').fetchone()[0])

    def test_ambiguous_completion_event_remains_null(self):
        with self.store.connection() as con:
            event=dict(con.execute("SELECT * FROM events WHERE action='intake.analysis_completed'").fetchone())
            con.execute('INSERT INTO events(created_at,action,subject_id,details_json) VALUES(?,?,?,?)',
                        (event['created_at'],event['action'],event['subject_id'],event['details_json']))
        self.receipt()
        with self.store.connection() as con:self.assertIsNone(con.execute('SELECT origin_completed_at FROM intake_analysis_generations').fetchone()[0])

    def test_bad_inputs_missing_intake_and_expectations_do_not_create_ledger(self):
        module=self.module();before=self.rows();sha=self.result_hash()
        for revision,bad_hash in ((True,sha),(0,sha),(1,'x'),(1,'A'*64),(1,'0'*64),(2,sha)):
            with self.subTest(revision=revision,hash=bad_hash[:2]),self.assertRaises(ValueError):
                module.import_completed_generation(self.store,self.intake,expected_revision=revision,expected_result_sha256=bad_hash)
        for intake in ('../secret','MISSING'):
            with self.subTest(intake=intake),self.assertRaises(ValueError) as caught:
                module.import_completed_generation(self.store,intake,expected_revision=1,expected_result_sha256=sha)
            self.assertNotIn('secret',str(caught.exception));self.assertNotIn(str(self.root),str(caught.exception))
        self.no_ledger();self.assertEqual(self.rows(),before)

    def test_history_argument_validation_and_large_integer_cursor(self):
        module=self.module()
        for kwargs in ({'limit':True},{'limit':0},{'limit':101},{'before_epoch':True},{'before_epoch':-1},{'before_epoch':1.5}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):module.generation_history(self.store,self.intake,**kwargs)
        self.no_ledger();receipt=self.receipt()
        self.assertEqual(module.generation_history(self.store,self.intake,before_epoch=10**100)['records'],[receipt])

    def test_incomplete_v1_and_text_only_v2_are_rejected(self):
        module=self.module()
        with self.store.connection() as con:con.execute("UPDATE intake_jobs SET state='failed' WHERE job_id=?",(self.job['job_id'],))
        with self.assertRaises(ValueError):self.receipt()
        for version in (1,2):
            job,analysis=self.finish(folder='text'+str(version),payload=b'product_type: radio\nmarket: EU\npurpose: certification',path='request.txt')
            if version==2:
                analysis.update(schema_version=2,context_id=job['analysis_context_id'])
                for fact in analysis['facts']:
                    for evidence in fact['evidence']:evidence['kind']='text_line'
                with self.store.connection() as con:
                    result=json.loads(con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0])
                    result['submission']=analysis;result['summary']['submitted']=analysis
                    con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(canonical(result),job['job_id']))
            with self.subTest(version=version),self.assertRaises(ValueError):
                module.import_completed_generation(self.store,job['intake_id'],expected_revision=1,expected_result_sha256=self.result_hash(job))
        self.no_ledger()

    def test_corrupt_source_context_or_extraction_rolls_back_without_repair(self):
        before=self.rows()
        for sha in (self.job['documents'][0]['sha256'],self.analysis['context_id'],self.job['documents'][0]['extraction_id']):
            path=self.store.blob_path(sha);payload=path.read_bytes();path.write_bytes(b'corrupt')
            with self.subTest(sha=sha),self.assertRaises(ValueError):self.receipt()
            self.no_ledger();path.write_bytes(payload)
        self.assertEqual(self.rows(),before)

    def test_changed_result_never_rewrites_an_imported_origin(self):
        first=self.receipt()
        with self.store.connection() as con:
            value=json.loads(con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(self.job['job_id'],)).fetchone()[0])
            value['submission']['producer']['name']='changed-origin';value['summary']['submitted']=copy.deepcopy(value['submission'])
            con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(canonical(value),self.job['job_id']))
        with self.assertRaises(ValueError):self.receipt()
        self.assertEqual(self.module().generation_history(self.store,self.intake)['records'],[first])

    def test_other_intake_context_with_valid_hashes_is_not_imported(self):
        other,other_analysis=self.finish(folder='two')
        with self.store.connection() as con:
            value=json.loads(self.saved_result)
            value['submission']['context_id']=other_analysis['context_id']
            value['summary']['submitted']=copy.deepcopy(value['submission'])
            con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(canonical(value),self.job['job_id']))
        with self.assertRaises(ValueError):self.receipt()
        self.no_ledger()

    def test_noncanonical_valid_result_bytes_are_preserved_and_duplicate_keys_rejected(self):
        value=json.loads(self.saved_result);raw=json.dumps(value,ensure_ascii=False,indent=2)
        with self.store.connection() as con:con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(raw,self.job['job_id']))
        receipt=self.receipt();self.assertEqual(receipt['result_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        with self.store.connection() as con:self.assertEqual(con.execute('SELECT result_json FROM intake_analysis_generations').fetchone()[0],raw)

    def test_ambiguous_result_json_is_not_imported(self):
        value=json.loads(self.saved_result)
        raw='{"submission":'+canonical(value['submission'])+',"submission":'+canonical(value['submission'])+',"summary":'+canonical(value['summary'])+'}'
        with self.store.connection() as con:con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(raw,self.job['job_id']))
        with self.assertRaises(ValueError):self.receipt()
        self.no_ledger()

    def test_old_revision_reimport_cannot_promote_an_earlier_head(self):
        first=self.receipt();old_hash=self.result_hash();self.job,self.analysis=self.finish(revision=2);second=self.receipt()
        with self.assertRaises(ValueError):self.module().import_completed_generation(self.store,self.intake,
            expected_revision=1,expected_result_sha256=old_hash)
        self.assertEqual(self.module().generation_history(self.store,self.intake)['records'],[second,first])

    def test_final_retained_validation_failure_rolls_back_created_ledger(self):
        module=self.module();actual=module.validate_retained_analysis;calls=0;before=self.rows()
        path=self.store.blob_path(self.job['documents'][0]['sha256']);payload=path.read_bytes()
        def corrupt_before_final(*args):
            nonlocal calls
            calls+=1
            if calls==2:path.write_bytes(b'changed during import')
            return actual(*args)
        try:
            with patch.object(module,'validate_retained_analysis',side_effect=corrupt_before_final),self.assertRaises(ValueError):self.receipt()
        finally:path.write_bytes(payload)
        self.assertEqual(calls,2);self.no_ledger();self.assertEqual(self.rows(),before)

    def test_origin_validation_is_inside_the_same_writer_transaction(self):
        module=self.module();actual=module.validate_retained_analysis;blocked=[]
        def external_writer(*args):
            with closing(sqlite3.connect(self.store.db,timeout=.05)) as writer:
                with self.assertRaises(sqlite3.OperationalError):writer.execute("UPDATE intakes SET status='changed' WHERE intake_id=?",(self.intake,))
                blocked.append(True)
            return actual(*args)
        with patch.object(module,'validate_retained_analysis',side_effect=external_writer):self.receipt()
        self.assertEqual(len(blocked),2)

    def test_unknown_schema_is_rejected_without_silent_repair(self):
        with self.store.connection() as con:con.execute('CREATE TABLE intake_analysis_generations(wrong TEXT)')
        with self.assertRaises(ValueError):self.receipt()
        with self.assertRaises(ValueError):self.module().generation_history(self.store,self.intake)
        with self.store.connection() as con:self.assertEqual([row[1] for row in con.execute('PRAGMA table_info(intake_analysis_generations)')],['wrong'])

    def test_repeat_import_does_not_repair_a_missing_revision_head(self):
        receipt=self.receipt()
        with self.store.connection() as con:con.execute('DELETE FROM intake_analysis_heads')
        with self.assertRaises(ValueError):self.receipt()
        with self.store.connection() as con:self.assertEqual(con.execute('SELECT count(*) FROM intake_analysis_heads').fetchone()[0],0)
        self.assertEqual(self.module().generation_history(self.store,self.intake)['records'],[receipt])

    def test_schema_validation_preserves_case_sensitive_trigger_literals(self):
        module=self.module();self.receipt()
        with self.store.connection() as con:
            trigger=con.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='intake_analysis_generations' AND sql LIKE '%BEFORE UPDATE%'").fetchone()
            altered=trigger['sql'].replace("OLD.state='completed'","OLD.state='COMPLETED'")
            self.assertNotEqual(altered,trigger['sql'])
            con.execute('DROP TRIGGER '+trigger['name']);con.execute(altered)
        with self.assertRaises(ValueError):module.generation_history(self.store,self.intake)

    def test_ddl_and_import_event_failures_roll_back_every_new_object(self):
        module=self.module();connection=self.store.connection;before=self.rows()
        for denied_action in ('trigger','event'):
            @contextmanager
            def blocked():
                with connection() as con:
                    def authorize(action,one,two,db,source):
                        if denied_action=='trigger' and action==sqlite3.SQLITE_CREATE_TRIGGER:return sqlite3.SQLITE_DENY
                        if denied_action=='event' and action==sqlite3.SQLITE_INSERT and one=='intake_analysis_events':return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK
                    con.set_authorizer(authorize);yield con
            with patch.object(self.store,'connection',side_effect=blocked),self.assertRaises(ValueError):self.receipt()
            self.no_ledger();self.assertEqual(self.rows(),before)

    def test_result_and_aggregate_snapshot_limits_are_checked_before_large_rows_are_loaded(self):
        module=self.module();connection=self.store.connection
        def bounded_row(cursor,values):
            for value in values:
                if isinstance(value,str) and len(value.encode('utf-8'))>1024*1024:
                    raise AssertionError('large row loaded before SQL budget check')
            return sqlite3.Row(cursor,values)
        @contextmanager
        def bounded():
            with connection() as con:con.row_factory=bounded_row;yield con
        for field in ('result','raw_snapshot','encoded_snapshot'):
            with connection() as con:
                if field=='result':
                    value='x'*(8*1024*1024+1);con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(value,self.job['job_id']))
                    result_hash=hashlib.sha256(value.encode()).hexdigest()
                else:
                    original=self.saved_result
                    con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(original,self.job['job_id']))
                    con.execute('DELETE FROM intake_questions WHERE intake_id=?',(self.intake,))
                    value=('x'*(5*1024*1024)) if field=='raw_snapshot' else ('\x00'*(1024*1024))
                    for number in range(2):con.execute("INSERT INTO intake_questions VALUES(?,?,?,'open',1)",(self.intake,'large'+str(number),value))
                    result_hash=hashlib.sha256(original.encode()).hexdigest()
            with self.subTest(field=field),patch.object(self.store,'connection',side_effect=bounded),self.assertRaises(ValueError):
                module.import_completed_generation(self.store,self.intake,expected_revision=1,expected_result_sha256=result_hash)
            self.no_ledger()

    def test_completed_request_and_event_immutability_and_foreign_keys(self):
        receipt=self.receipt()
        with self.store.connection() as con:
            for sql in ("UPDATE intake_analysis_generations SET profile_id='changed'",'DELETE FROM intake_analysis_generations',
                        "UPDATE intake_analysis_events SET kind='changed'",'DELETE FROM intake_analysis_events'):
                with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):con.execute(sql)
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute('UPDATE intake_analysis_heads SET generation_id=?',('0'*64,))
            con.execute('INSERT INTO intake_analysis_requests VALUES(?,?,?,?,?,?,?,?)',
                        ('trusted-test','0'*64,canonical(receipt),self.intake,1,receipt['generation_id'],0,'test-time'))
            for sql in ("UPDATE intake_analysis_requests SET receipt_json='changed'",'DELETE FROM intake_analysis_requests'):
                with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):con.execute(sql)
            with self.assertRaises(sqlite3.IntegrityError):con.execute('DELETE FROM intake_jobs WHERE job_id=?',(self.job['job_id'],))

    @property
    def saved_result(self):
        return self._saved_result


if __name__=='__main__':unittest.main()
