"""Imported historical completion replay is detached and entirely read-only."""
from contextlib import contextmanager
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import intake_documents
from labflow.active_intake import register_source,scan_source
from labflow.document_extract import ExtractionLimits
from labflow.intake_generation_ledger import import_completed_generation,generation_history
from labflow.intake_jobs import claim_job,complete_job,respond
from labflow.intake_worker import SyntheticTextProvider
from labflow.store import Store,canonical
from test_intake_documents import pdf


def digest(payload):return hashlib.sha256(payload).hexdigest()


@unittest.skipUnless(importlib.util.find_spec('pypdf') is not None,'Optional pypdf is not installed')
class ImportedCompletionReplayTests(unittest.TestCase):
    def setUp(self):
        local=Path(__file__).resolve().parents[1]/'.local';local.mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(prefix='replay-test-',dir=local)
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.inbox=self.root/'inbox';self.inbox.mkdir();self.store=Store(self.root/'state')
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)
        self.job,self.analysis,self.summary=self.complete_revision(1);self.intake=self.job['intake_id']
        respond(self.store,'answer','answer',intake_id=self.intake,answers={'market':'US'})
        respond(self.store,'proceed','proceed',intake_id=self.intake)

    def complete_revision(self,revision):
        folder=self.inbox/'one';folder.mkdir(exist_ok=True)
        (folder/'request.pdf').write_bytes(pdf(['product_type: smartphone\nmodel: SM-A176U',
            'purpose: certification\nrevision: '+str(revision)]))
        scan_source(self.store,'INBOX',now=100+revision*10);scan_source(self.store,'INBOX',now=102+revision*10)
        job=claim_job(self.store,'worker',now=103+revision*10);value=SyntheticTextProvider().analyze(job)
        summary=complete_job(self.store,job['job_id'],job['token'],value,now=104+revision*10)
        return job,value,summary

    def module(self):return importlib.import_module('labflow.intake_generation_ledger')

    def imported(self,job=None):
        job=job or self.job
        with self.store.connection() as con:raw=con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0]
        return import_completed_generation(self.store,job['intake_id'],expected_revision=job['revision'],expected_result_sha256=digest(raw.encode()))

    def state(self):
        with self.store.connection() as con:
            tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows={name:[dict(row) for row in con.execute('SELECT * FROM '+name+' ORDER BY rowid')] for name in tables}
        files={str(path.relative_to(self.root)):digest(path.read_bytes()) for path in self.root.rglob('*') if path.is_file()}
        return rows,files

    def call(self,job_id=None,token=None,analysis=None):
        return self.module().replay_imported_completion(self.store,job_id or self.job['job_id'],
            self.job['token'] if token is None else token,self.analysis if analysis is None else analysis)

    def immutable_origin_fault(self,**changes):
        with self.store.connection() as con:
            triggers=[dict(row) for row in con.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='intake_analysis_generations' AND sql LIKE '%BEFORE UPDATE%'")]
            for trigger in triggers:con.execute('DROP TRIGGER '+trigger['name'])
            con.execute('UPDATE intake_analysis_generations SET '+','.join(name+'=?' for name in changes)+' WHERE origin_job_id=?',(*changes.values(),self.job['job_id']))
            for trigger in triggers:con.execute(trigger['sql'])

    def test_imported_profile_change_returns_exact_old_summary_without_parsing_or_writing(self):
        self.imported();before=self.state();denied=AssertionError('historical replay attempted prepare/parser/write/provider')
        with patch.object(intake_documents,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=199)),\
             patch.dict(sys.modules,{'pypdf':None}),\
             patch.object(intake_documents,'extract_document',side_effect=denied),\
             patch.object(intake_documents,'prepare_analysis_documents',side_effect=denied),\
             patch('labflow.intake_jobs._prepare',side_effect=denied),\
             patch.object(Store,'__init__',side_effect=denied),\
             patch.object(self.store,'write_blob',side_effect=denied),\
             patch.object(self.store,'register_blob',side_effect=denied),\
             patch.object(self.store,'event',side_effect=denied),\
             patch.object(SyntheticTextProvider,'analyze',side_effect=denied):
            self.assertEqual(self.call(),self.summary);self.assertEqual(self.call(),self.summary)
        self.assertEqual(self.state(),before)

    def test_earlier_revision_replay_preserves_current_head_questions_notices_and_results(self):
        first=self.imported();current,_,_=self.complete_revision(2);second=self.imported(current);before=self.state()
        with patch.object(intake_documents,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=199)):
            self.assertEqual(self.call(),self.summary)
        self.assertEqual(self.state(),before)
        self.assertEqual(generation_history(self.store,self.intake)['records'],[second,first])

    def test_ledger_absence_and_job_origin_absence_return_none_without_ddl(self):
        before=self.state();self.assertIsNone(self.call());self.assertEqual(self.state(),before)
        self.imported();before=self.state();self.assertIsNone(self.call(job_id='MISSING'));self.assertEqual(self.state(),before)
        current,value,_=self.complete_revision(2);before=self.state()
        self.assertIsNone(self.module().replay_imported_completion(self.store,current['job_id'],current['token'],value))
        self.assertEqual(self.state(),before)

    def test_wrong_token_and_changed_submission_are_errors_and_never_fallback(self):
        self.imported();before=self.state()
        for token in ('wrong-token','',None,b'bytes','\ud800'):
            with self.subTest(token_type=type(token).__name__),self.assertRaises(ValueError):
                self.module().replay_imported_completion(self.store,self.job['job_id'],token,self.analysis)
        value=copy.deepcopy(self.analysis);value['facts'][0]['value']='changed'
        with self.assertRaises(ValueError):self.call(analysis=value)
        self.assertEqual(self.state(),before)

    def test_returned_summary_is_detached_and_cannot_change_next_replay(self):
        self.imported();before=self.state();first=self.call()
        first['submitted']['facts'][0]['value']='mutated returned value'
        self.assertEqual(self.call(),self.summary);self.assertEqual(self.state(),before)

    def test_caller_nested_alias_is_fixed_before_first_database_io(self):
        self.imported();before=self.state();value=copy.deepcopy(self.analysis);connection=self.store.connection;changed=False
        @contextmanager
        def mutate_before_read():
            nonlocal changed
            if not changed:
                changed=True;value['context_id']='0'*64
                value['facts'][0]['evidence'][0].update(page_number=99,quote='caller changed after entry')
            with connection() as con:yield con
        with patch.object(self.store,'connection',side_effect=mutate_before_read):
            result=self.call(analysis=value)
        self.assertTrue(changed);self.assertEqual(result,self.summary);self.assertEqual(self.state(),before)

    def test_caller_nested_alias_is_fixed_before_first_blob_read(self):
        self.imported();before=self.state();value=copy.deepcopy(self.analysis);blob_path=self.store.blob_path;changed=False
        def mutate_before_blob(sha):
            nonlocal changed
            if not changed:
                changed=True;value['facts'][0]['value']='changed after DB read'
            return blob_path(sha)
        with patch.object(self.store,'blob_path',side_effect=mutate_before_blob):result=self.call(analysis=value)
        self.assertTrue(changed);self.assertEqual(result,self.summary);self.assertEqual(self.state(),before)

    def test_invalid_nonfinite_utf8_recursive_and_oversized_analysis_reject_before_io(self):
        module=self.module();invalid=[]
        for bad in (float('nan'),'\ud800'):
            value=copy.deepcopy(self.analysis);value['facts'][0]['value']=bad;invalid.append(value)
        cycle={};cycle['cycle']=cycle;invalid.append(cycle)
        large=copy.deepcopy(self.analysis);large['extra']='x'*(8*1024*1024+1);invalid.append(large)
        invalid.append([])
        with patch.object(self.store,'connection',side_effect=AssertionError('invalid input reached DB')):
            for value in invalid:
                with self.subTest(kind=type(value).__name__),self.assertRaises(ValueError):
                    module.replay_imported_completion(self.store,self.job['job_id'],self.job['token'],value)

    def test_corrupt_source_context_and_extraction_are_errors_with_no_state_change(self):
        self.imported()
        for sha in (self.job['documents'][0]['sha256'],self.analysis['context_id'],self.job['documents'][0]['extraction_id']):
            path=self.store.blob_path(sha);raw=path.read_bytes();path.write_bytes(b'corrupt');before=self.state()
            with self.subTest(sha=sha),self.assertRaises(ValueError):self.call()
            self.assertEqual(self.state(),before);path.write_bytes(raw)

    def test_result_snapshot_and_token_hash_faults_are_rejected(self):
        self.imported()
        with self.store.connection() as con:original=dict(con.execute('SELECT * FROM intake_analysis_generations').fetchone())
        for field,value in (('result_json','{}'),('snapshot_json','{}'),('result_sha256','0'*64),('snapshot_sha256','0'*64),('token_sha256','0'*64)):
            self.immutable_origin_fault(**{field:value});before=self.state()
            with self.subTest(field=field),self.assertRaises(ValueError):self.call()
            self.assertEqual(self.state(),before);self.immutable_origin_fault(**{field:original[field]})

    def test_cross_bound_snapshot_with_a_valid_hash_is_rejected(self):
        self.imported()
        with self.store.connection() as con:raw=con.execute('SELECT snapshot_json FROM intake_analysis_generations').fetchone()[0]
        snapshot=json.loads(raw);snapshot['intake']['intake_id']='OTHER';payload=canonical(snapshot)
        self.immutable_origin_fault(snapshot_json=payload,snapshot_sha256=digest(payload.encode()));before=self.state()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.state(),before)

    def test_snapshot_version_scope_and_row_shapes_with_valid_hash_are_rejected(self):
        self.imported()
        with self.store.connection() as con:original=json.loads(con.execute('SELECT snapshot_json FROM intake_analysis_generations').fetchone()[0])
        for target in ('version','scope','rows'):
            value=copy.deepcopy(original)
            if target=='version':value['schema_version']=True
            elif target=='scope':value['scope']='completion_time'
            else:value['questions']={}
            raw=canonical(value);self.immutable_origin_fault(snapshot_json=raw,snapshot_sha256=digest(raw.encode()));before=self.state()
            with self.subTest(target=target),self.assertRaises(ValueError):self.call()
            self.assertEqual(self.state(),before)

    def test_invalid_legacy_creation_metadata_cannot_match_a_null_origin(self):
        self.imported();self.immutable_origin_fault(origin_created_at=None)
        with self.store.connection() as con:con.execute("UPDATE intake_jobs SET created_at='invalid' WHERE job_id=?",(self.job['job_id'],))
        before=self.state()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.state(),before)

    def test_imported_wrong_state_never_becomes_absent_fallback(self):
        self.imported();self.immutable_origin_fault(state='queued');before=self.state()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.state(),before)

    def test_missing_legacy_parent_and_changed_legacy_result_are_not_none(self):
        self.imported()
        with self.store.connection() as con:
            con.execute('PRAGMA foreign_keys=OFF');con.execute('DELETE FROM intake_jobs WHERE job_id=?',(self.job['job_id'],))
        before=self.state()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.state(),before)

    def test_changed_legacy_result_is_rejected_with_no_archive_rewrite(self):
        self.imported()
        with self.store.connection() as con:con.execute("UPDATE intake_jobs SET result_json='{}' WHERE job_id=?",(self.job['job_id'],))
        before=self.state()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.state(),before)

    def test_partial_or_changed_ledger_schema_is_error_not_fallback(self):
        with self.store.connection() as con:con.execute('CREATE TABLE intake_analysis_generations(wrong TEXT)')
        before=self.state()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.state(),before)

    def test_read_snapshot_is_single_and_never_fetches_raw_legacy_token(self):
        self.imported();module=self.module();connection=self.store.connection;connections=[];statements=[]
        @contextmanager
        def checked():
            with connection() as con:
                connections.append(con);con.set_trace_callback(statements.append)
                def no_token(cursor,values):
                    self.assertFalse(any(column[0] in {'token','legacy_token'} for column in cursor.description))
                    return sqlite3.Row(cursor,values)
                con.row_factory=no_token;yield con
        with patch.object(self.store,'connection',side_effect=checked):self.assertEqual(self.call(),self.summary)
        self.assertEqual(len(connections),1)
        verbs=[statement.strip().split()[0].upper() for statement in statements]
        self.assertTrue(set(verbs)<={'BEGIN','SELECT','COMMIT'});self.assertLess(verbs.index('BEGIN'),verbs.index('SELECT'))

    def test_oversized_retained_result_and_snapshot_are_rejected_before_fetch(self):
        self.imported();connection=self.store.connection
        with connection() as con:original=dict(con.execute('SELECT * FROM intake_analysis_generations').fetchone())
        @contextmanager
        def bounded():
            with connection() as con:
                def bounded_row(cursor,values):
                    for value in values:
                        if isinstance(value,str) and len(value.encode())>8*1024*1024:
                            raise AssertionError('oversized retained payload loaded before SQL limit')
                    return sqlite3.Row(cursor,values)
                con.row_factory=bounded_row;yield con
        for field in ('result_json','snapshot_json'):
            self.immutable_origin_fault(**{field:'x'*(8*1024*1024+1)});before=self.state()
            with self.subTest(field=field),patch.object(self.store,'connection',side_effect=bounded),self.assertRaises(ValueError):self.call()
            self.assertEqual(self.state(),before);self.immutable_origin_fault(**{field:original[field]})

    def test_error_body_never_exposes_token_submission_or_paths(self):
        self.imported()
        try:self.call(token='incorrect')
        except ValueError as error:
            for secret in (self.job['token'],str(self.root),'SM-A176U','smartphone'):
                self.assertNotIn(secret,str(error))
        else:self.fail('wrong token was not rejected')


if __name__=='__main__':unittest.main()
