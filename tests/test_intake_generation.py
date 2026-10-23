"""Read-only generation inspection against retained synthetic PDF completions."""
from contextlib import closing, contextmanager
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
from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job, complete_job
from labflow.intake_worker import SyntheticTextProvider
from labflow.store import Store, canonical
from test_intake_documents import pdf


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


class CurrentProfileTests(unittest.TestCase):
    def test_public_profile_id_matches_prepared_profile_without_parsing(self):
        expected=digest(intake_documents._profile())
        with patch.object(intake_documents,'extract_document',side_effect=AssertionError('parser called')):
            self.assertEqual(intake_documents.current_extraction_profile_id(),expected)
            self.assertEqual(intake_documents.current_extraction_profile_id(),expected)


@unittest.skipUnless(importlib.util.find_spec('pypdf') is not None,'Optional pypdf is not installed')
class GenerationInspectionTests(unittest.TestCase):
    def setUp(self):
        local=Path(__file__).resolve().parents[1]/'.local';local.mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(prefix='gen004a-test-',dir=local)
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.inbox=self.root/'inbox';self.inbox.mkdir();self.store=Store(self.root/'state')
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)
        self.intake_id,self.job,self.analysis,self.summary=self.complete('one')

    def complete(self,folder,payload=None,path='request.pdf'):
        target=self.inbox/folder;target.mkdir(exist_ok=True)
        (target/path).write_bytes(payload if payload is not None else pdf([
            'product_type: remote_control','market: EU\npurpose: radio_test']))
        scan_source(self.store,'INBOX',now=100); received=scan_source(self.store,'INBOX',now=102)['accepted']
        job=claim_job(self.store,'worker',now=103)
        value=SyntheticTextProvider().analyze(job)
        result=complete_job(self.store,job['job_id'],job['token'],value,now=104)
        return job['intake_id'],job,value,result

    def module(self):
        return importlib.import_module('labflow.intake_generation')

    def files_snapshot(self):
        return {str(path.relative_to(self.root)):hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob('*') if path.is_file()}

    def inspect(self,intake_id=None):
        module=self.module(); before=self.files_snapshot()
        with self.store.connection() as con:rows_before='\n'.join(con.iterdump())
        forbidden=AssertionError('inspection attempted a write or parse')
        with patch.object(Store,'__init__',side_effect=forbidden),\
             patch.object(self.store,'write_blob',side_effect=forbidden),\
             patch.object(self.store,'register_blob',side_effect=forbidden),\
             patch.object(self.store,'event',side_effect=forbidden),\
             patch('labflow.document_extract.extract_document',side_effect=forbidden),\
             patch.object(intake_documents,'extract_document',side_effect=forbidden),\
             patch('labflow.intake_jobs._prepare',side_effect=forbidden),\
             patch.object(SyntheticTextProvider,'analyze',side_effect=forbidden):
            result=module.analysis_generation_status(self.store,intake_id or self.intake_id)
        with self.store.connection() as con:self.assertEqual('\n'.join(con.iterdump()),rows_before)
        self.assertEqual(self.files_snapshot(),before)
        self.assertEqual(set(result),{'schema_version','kind','intake_id','revision','status','reason_codes',
                                      'context_id','stored_profile_id','current_profile_id','reanalysis_required'})
        self.assertEqual(result['schema_version'],1);self.assertEqual(result['kind'],'intake_analysis_generation')
        self.assertEqual(result['intake_id'],intake_id or self.intake_id)
        self.assertIs(type(result['reanalysis_required']),bool)
        self.assertEqual(len(result['reason_codes']),1)
        self.assertTrue(set(result['reason_codes']) <= module.REASON_CODES)
        self.assertIn(result['status'],{'current','stale','unavailable','legacy_unbound','invalid'})
        self.assertEqual(result['reanalysis_required'],result['status']=='stale')
        for key in ('context_id','stored_profile_id','current_profile_id'):
            if result[key] is not None:self.assertRegex(result[key],r'^[a-f0-9]{64}$')
        self.assertNotIn(str(self.root),canonical(result))
        self.assertNotIn(self.job['token'],canonical(result))
        self.assertNotIn('remote_control',canonical(result))
        return result

    def update_result(self,change):
        with self.store.connection() as con:
            result=json.loads(con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(self.job['job_id'],)).fetchone()[0])
            change(result);con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(canonical(result),self.job['job_id']))

    def point_to_context(self,context):
        context_id=self.store.write_blob(canonical(context).encode('utf-8'))
        def change(result):
            result['submission']['context_id']=context_id
            result['summary']['submitted']=copy.deepcopy(result['submission'])
        self.update_result(change)
        return context_id

    def retained_context(self):
        return json.loads(self.store.blob_path(self.analysis['context_id']).read_bytes())

    def test_actual_completed_pdf_is_current_and_repeat_query_is_unchanged(self):
        first=self.inspect();self.assertEqual(first,self.inspect())
        self.assertEqual(first['status'],'current');self.assertFalse(first['reanalysis_required'])
        self.assertEqual(first['context_id'],self.analysis['context_id'])
        self.assertEqual(first['stored_profile_id'],first['current_profile_id'])
        self.assertEqual(first['reason_codes'],['profile_matches'])

    def test_parser_version_change_detects_stale_without_reparsing(self):
        with patch.object(intake_documents.importlib.metadata,'version',return_value='changed-parser-version'):
            result=self.inspect()
        self.assertEqual(result['status'],'stale');self.assertTrue(result['reanalysis_required'])
        self.assertNotEqual(result['stored_profile_id'],result['current_profile_id'])
        self.assertEqual(result['reason_codes'],['profile_changed'])

    def test_inspection_does_not_import_or_need_the_pdf_parser(self):
        import sys
        with patch.dict(sys.modules,{'pypdf':None}):
            self.assertEqual(self.inspect()['status'],'current')

    def test_empty_completed_pdf_has_current_generation_but_stays_unread(self):
        intake,_,_,summary=self.complete('two',pdf(['','']))
        self.assertTrue(summary['unread_documents'])
        self.assertEqual(self.inspect(intake)['status'],'current')

    def test_code_and_limit_profile_changes_detect_stale(self):
        profile=intake_documents._profile()
        for field in ('extractor_sha256','bridge_sha256','limits'):
            changed=copy.deepcopy(profile)
            if field=='limits':changed[field]['max_pages']=1
            else:changed[field]='0'*64
            with self.subTest(field=field),patch.object(intake_documents,'_profile',return_value=changed):
                result=self.inspect();self.assertEqual(result['status'],'stale');self.assertTrue(result['reanalysis_required'])

    def test_unfinished_current_revision_does_not_reuse_old_completed_analysis(self):
        (self.inbox/'one'/'request.pdf').write_bytes(pdf(['product_type: changed']))
        scan_source(self.store,'INBOX',now=105);scan_source(self.store,'INBOX',now=107)
        result=self.inspect();self.assertEqual(result['revision'],2)
        self.assertEqual(result['status'],'unavailable');self.assertFalse(result['reanalysis_required'])
        self.assertIsNone(result['context_id']);self.assertEqual(result['reason_codes'],['analysis_not_completed'])

    def test_queued_running_failed_and_superseded_are_not_completed_analysis(self):
        for state in ('queued','running','failed','superseded'):
            with self.store.connection() as con:con.execute('UPDATE intake_jobs SET state=? WHERE job_id=?',(state,self.job['job_id']))
            with self.subTest(state=state):
                result=self.inspect();self.assertEqual(result['status'],'unavailable');self.assertFalse(result['reanalysis_required'])

    def test_missing_current_job_is_unavailable(self):
        with self.store.connection() as con:con.execute('DELETE FROM intake_jobs WHERE job_id=?',(self.job['job_id'],))
        result=self.inspect();self.assertEqual(result['status'],'unavailable');self.assertFalse(result['reanalysis_required'])

    def test_text_v1_is_legacy_unbound_and_not_promoted(self):
        intake,_,_,_=self.complete('two',b'product_type: remote_control\nmarket: EU\npurpose: radio_test','request.txt')
        result=self.inspect(intake);self.assertEqual(result['status'],'legacy_unbound')
        self.assertEqual(result['reason_codes'],['legacy_analysis']);self.assertFalse(result['reanalysis_required'])
        self.assertIsNone(result['context_id']);self.assertIsNone(result['stored_profile_id'])

    def test_unbound_v2_text_is_legacy_not_pdf_success(self):
        target=self.inbox/'two';target.mkdir();(target/'request.txt').write_bytes(b'product_type: remote_control\nmarket: EU\npurpose: radio_test')
        scan_source(self.store,'INBOX',now=100);scan_source(self.store,'INBOX',now=102)
        job=claim_job(self.store,'worker',now=103);value=SyntheticTextProvider().analyze(job)
        value.update(schema_version=2,context_id=job['analysis_context_id'])
        for fact in value['facts']:
            for evidence in fact['evidence']:evidence['kind']='text_line'
        complete_job(self.store,job['job_id'],job['token'],value,now=104)
        result=self.inspect(job['intake_id']);self.assertEqual(result['status'],'legacy_unbound')
        self.assertEqual(result['reason_codes'],['no_pdf_context']);self.assertFalse(result['reanalysis_required'])

    def test_corrupt_context_and_original_are_invalid_not_stale(self):
        for target,code in ((self.analysis['context_id'],'invalid_context'),(self.job['documents'][0]['sha256'],'invalid_source')):
            path=self.store.blob_path(target);original=path.read_bytes();path.write_bytes(b'damaged')
            with self.subTest(target=code):
                result=self.inspect();self.assertEqual(result['status'],'invalid');self.assertFalse(result['reanalysis_required'])
                self.assertEqual(result['reason_codes'],[code])
            path.write_bytes(original)

    def test_corrupt_extraction_and_invalid_page_citation_are_invalid(self):
        path=self.store.blob_path(self.job['documents'][0]['extraction_id']);original=path.read_bytes();path.write_bytes(b'damaged')
        self.assertEqual(self.inspect()['reason_codes'],['invalid_extraction']);path.write_bytes(original)
        def change(result):
            result['submission']['facts'][0]['evidence'][0]['page_number']=99
            result['summary']['submitted']=copy.deepcopy(result['submission'])
        self.update_result(change)
        self.assertEqual(self.inspect()['reason_codes'],['invalid_analysis'])

    def test_context_from_another_intake_is_not_a_current_binding(self):
        _,_,other,_=self.complete('two')
        def change(result):
            result['submission']['context_id']=other['context_id']
            result['summary']['submitted']=copy.deepcopy(result['submission'])
        self.update_result(change)
        result=self.inspect();self.assertEqual(result['status'],'invalid');self.assertEqual(result['reason_codes'],['invalid_binding'])

    def test_revision_fingerprint_and_context_source_binding_are_checked(self):
        context=self.retained_context();context['binding']['source_id']='OTHER';self.point_to_context(context)
        self.assertEqual(self.inspect()['reason_codes'],['invalid_binding'])
        self.point_to_context(self.retained_context())
        with self.store.connection() as con:con.execute('UPDATE intake_revisions SET fingerprint=? WHERE intake_id=?',('0'*64,self.intake_id))
        self.assertEqual(self.inspect()['reason_codes'],['invalid_binding'])

    def test_stored_profile_hash_is_verified_before_comparing_current_profile(self):
        context=self.retained_context();context['profile']['parser']['version']='forged'
        self.point_to_context(context)
        result=self.inspect();self.assertEqual(result['status'],'invalid');self.assertEqual(result['reason_codes'],['invalid_profile'])
        self.assertFalse(result['reanalysis_required'])

    def test_cross_bound_extraction_source_is_invalid_even_with_valid_blob_hashes(self):
        context=self.retained_context();document=context['documents'][0]
        artifact=json.loads(self.store.blob_path(document['extraction_id']).read_bytes())
        artifact['result']['source']['sha256']='0'*64
        document['extraction_id']=self.store.write_blob(canonical(artifact).encode('utf-8'))
        self.point_to_context(context)
        self.assertEqual(self.inspect()['reason_codes'],['invalid_extraction'])

    def test_malformed_nested_metadata_is_a_typed_invalid_result(self):
        context=self.retained_context();document=context['documents'][0]
        artifact=json.loads(self.store.blob_path(document['extraction_id']).read_bytes())
        artifact['result']['parser']['name']=[];document['parser']['name']=[]
        document['extraction_id']=self.store.write_blob(canonical(artifact).encode('utf-8'))
        self.point_to_context(context)
        self.assertEqual(self.inspect()['reason_codes'],['invalid_extraction'])

    def test_retained_character_limit_and_completion_flag_must_be_consistent(self):
        for mode in ('character_limit','complete_flag'):
            context=self.retained_context();document=context['documents'][0]
            artifact=json.loads(self.store.blob_path(document['extraction_id']).read_bytes())
            if mode=='character_limit':
                context['profile']['limits']['max_output_chars']=1
                context['extraction_profile_id']=digest(context['profile'])
                artifact['extraction_profile_id']=context['extraction_profile_id']
                artifact['result']['limits']=copy.deepcopy(context['profile']['limits'])
                document['limits']=copy.deepcopy(context['profile']['limits'])
            else:
                artifact['result']['complete']=False;document['complete']=False
            document['extraction_id']=self.store.write_blob(canonical(artifact).encode('utf-8'))
            self.point_to_context(context)
            def bind_citations(result):
                for fact in result['submission']['facts']:
                    for evidence in fact['evidence']:
                        if evidence.get('kind')=='pdf_page':evidence['extraction_id']=document['extraction_id']
                result['summary']['submitted']=copy.deepcopy(result['submission'])
            self.update_result(bind_citations)
            with self.subTest(mode=mode):self.assertEqual(self.inspect()['reason_codes'],['invalid_extraction'])

    def test_valid_partial_with_unread_page_is_current_generation_not_read_success(self):
        from pypdf import PageObject
        extract=PageObject.extract_text; calls=0
        def unread_second(page,*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls%2==0:raise ValueError('synthetic page failure')
            return extract(page,*args,**kwargs)
        with patch.object(PageObject,'extract_text',new=unread_second):
            intake,job,_,summary=self.complete('two')
        self.assertEqual(job['documents'][0]['parse_status'],'partial')
        self.assertEqual(job['documents'][0]['pages'][1]['status'],'error')
        self.assertTrue(summary['unread_documents'])
        result=self.inspect(intake);self.assertEqual(result['status'],'current')
        self.assertFalse(result['reanalysis_required'])

    def test_malformed_result_and_disagreeing_saved_submission_are_invalid(self):
        with self.store.connection() as con:
            original=con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(self.job['job_id'],)).fetchone()[0]
        for bad in ('not JSON',canonical({'submission':self.analysis}),canonical({'submission':self.analysis,'summary':{'submitted':{}}})):
            with self.store.connection() as con:con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(bad,self.job['job_id']))
            with self.subTest(bad=bad[:20]):self.assertEqual(self.inspect()['reason_codes'],['invalid_result'])
        with self.store.connection() as con:con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',(original,self.job['job_id']))

    def test_oversized_context_is_rejected_without_unbounded_reads(self):
        path=self.store.blob_path(self.analysis['context_id']);path.write_bytes(b' '*(intake_documents.MAX_CONTEXT_BYTES+1))
        result=self.inspect();self.assertEqual(result['status'],'invalid');self.assertEqual(result['reason_codes'],['invalid_context'])

    def test_invalid_and_missing_identifiers_have_sanitized_errors(self):
        module=self.module()
        for value in ('../secret',None,{},'MISSING'):
            with self.subTest(value=value),self.assertRaises(ValueError) as caught:
                module.analysis_generation_status(self.store,value)
            message=str(caught.exception)
            self.assertNotIn(str(self.root),message);self.assertNotIn('secret',message)
            self.assertNotIn('SELECT',message);self.assertNotIn(self.job['token'],message)

    def test_database_values_come_from_one_explicit_read_transaction(self):
        module=self.module(); connection=self.store.connection; statements=[];connections=[]
        @contextmanager
        def traced():
            with connection() as con:
                connections.append(con);con.set_trace_callback(statements.append)
                yield con
        with patch.object(self.store,'connection',side_effect=traced):
            result=module.analysis_generation_status(self.store,self.intake_id)
        self.assertEqual(result['status'],'current');self.assertEqual(len(connections),1)
        sql=[value.strip().split()[0].upper() for value in statements]
        self.assertIn('BEGIN',sql);self.assertLess(sql.index('BEGIN'),sql.index('SELECT'))
        self.assertTrue(set(sql)<= {'BEGIN','SELECT','COMMIT'},sql)

    def test_oversized_database_result_is_not_loaded_into_python(self):
        module=self.module(); connection=self.store.connection
        with connection() as con:
            con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',
                        (' '*(module.MAX_RESULT_BYTES+1),self.job['job_id']))
        def bounded_row(cursor,values):
            for value in values:
                if isinstance(value,str) and len(value.encode('utf-8'))>module.MAX_RESULT_BYTES:
                    raise AssertionError('oversized DB value loaded before limit check')
            return sqlite3.Row(cursor,values)
        @contextmanager
        def bounded_connection():
            with connection() as con:
                con.row_factory=bounded_row;yield con
        with patch.object(self.store,'connection',side_effect=bounded_connection):
            result=module.analysis_generation_status(self.store,self.intake_id)
        self.assertEqual(result['status'],'invalid');self.assertEqual(result['reason_codes'],['invalid_result'])

    def test_concurrent_job_change_does_not_mix_database_snapshots(self):
        module=self.module(); connection=self.store.connection; changed=False
        with connection() as con:con.execute('PRAGMA journal_mode=WAL')
        class Cursor:
            def __init__(self,cursor):self.cursor=cursor
            def fetchone(inner):
                nonlocal changed
                row=inner.cursor.fetchone()
                if not changed:
                    changed=True
                    with closing(sqlite3.connect(self.store.db)) as writer:
                        with writer:
                            writer.execute("UPDATE intake_jobs SET state='failed' WHERE job_id=?",(self.job['job_id'],))
                return row
        class ReadConnection:
            def __init__(self,con):self.con=con
            def execute(inner,sql,args=()):
                cursor=inner.con.execute(sql,args)
                return Cursor(cursor) if sql.lstrip().upper().startswith('SELECT') else cursor
        @contextmanager
        def concurrent_change():
            with connection() as con:yield ReadConnection(con)
        with patch.object(self.store,'connection',side_effect=concurrent_change):
            result=module.analysis_generation_status(self.store,self.intake_id)
        self.assertTrue(changed);self.assertEqual(result['status'],'current')
        with connection() as con:self.assertEqual(con.execute('SELECT state FROM intake_jobs WHERE job_id=?',(self.job['job_id'],)).fetchone()[0],'failed')


if __name__=='__main__':unittest.main()
