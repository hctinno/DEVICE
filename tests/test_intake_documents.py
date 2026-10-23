"""Synthetic retained PDFs through the actual analysis queue, without models."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source, intake_status
from labflow.document_extract import ExtractionLimits, extract_document, _page
from labflow.intake_analysis import document_context
from labflow.intake_jobs import claim_job, complete_job, fail_job, notifications
from labflow.intake_worker import SyntheticTextProvider, run_worker
from labflow.store import Store, canonical


def pdf(pages):
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids=[]
    for text in pages:
        page_id=len(objects)+1; content_id=page_id+1; kids.append(f'{page_id} 0 R')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        lines=['BT /F1 12 Tf 20 760 Td']
        for line in text.splitlines():
            escaped=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
            lines.append(f'({escaped}) Tj 0 -16 Td')
        data=('\n'.join(lines)+'\nET').encode('ascii')
        objects.append(b'<< /Length '+str(len(data)).encode()+b' >>\nstream\n'+data+b'\nendstream')
    objects[1]=f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
    data=bytearray(b'%PDF-1.4\n'); offsets=[0]
    for number,value in enumerate(objects,1):
        offsets.append(len(data)); data.extend(f'{number} 0 obj\n'.encode()+value+b'\nendobj\n')
    xref=len(data); data.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:data.extend(f'{offset:010} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(data)


class DocumentBridgeCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.intake_documents'),'PDF intake bridge is not implemented')
        self.bridge=importlib.import_module('labflow.intake_documents')
        root=Path(__file__).resolve().parents[1]/'.local'; root.mkdir(exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='flow003-test-',dir=root)
        self.addCleanup(self.temporary.cleanup); self.root=Path(self.temporary.name)
        self.store=Store(self.root/'state')

    def retained(self,path,data):
        sha=self.store.write_blob(data)
        with self.store.connection() as con:self.store.register_blob(con,sha,len(data),'intake_document',True)
        return {'path':path,'sha256':sha,'bytes':len(data)}

    def prepare(self,files,**changes):
        metadata={'source_id':'INBOX','intake_id':'I-example','revision':1,
                  'revision_fingerprint':hashlib.sha256(canonical(files).encode()).hexdigest(),**changes}
        return self.bridge.prepare_analysis_documents(self.store,files,**metadata)


class DocumentPreparationTests(DocumentBridgeCase):
    def test_pdf_pages_keep_original_and_derived_hashes_and_stable_context(self):
        if importlib.util.find_spec('pypdf') is None:self.skipTest('Optional pypdf is not installed')
        payload=pdf(['product_type: remote_control','market: EU\npurpose: radio_test'])
        files=[self.retained('request.pdf',payload)]
        prepared=self.prepare(files); document=prepared['documents'][0]
        self.assertEqual(set(prepared),{'context_id','extraction_profile_id','documents'})
        self.assertIsNone(document['text']); self.assertEqual(document['parse_status'],'ok')
        self.assertEqual(document['sha256'],hashlib.sha256(payload).hexdigest())
        self.assertEqual([page['page_number'] for page in document['pages']],[1,2])
        for page in document['pages']:
            self.assertEqual(page['text_sha256'],hashlib.sha256(page['text'].encode()).hexdigest())
        self.assertEqual(self.prepare(files),prepared)
        self.assertTrue(self.store.verify_blob(document['extraction_id']).is_file())
        self.assertNotIn(str(self.store.root),canonical(prepared))

    def test_legacy_text_and_non_pdf_inputs_are_preserved(self):
        files=[self.retained('request.txt',b'\xef\xbb\xbfproduct_type: remote\r\nmarket: EU\r\n'),
               self.retained('sheet.xlsx',b'not executed'),self.retained('invalid.txt',b'\xff')]
        old=document_context(self.store,files); new=self.prepare(files)['documents']
        for original,document in zip(old,new):
            for key in ('path','sha256','bytes','text','parse_status'):self.assertEqual(document[key],original[key])
        self.assertEqual(new[0]['text'],'product_type: remote\r\nmarket: EU\r\n')

    def test_typed_pdf_failures_and_partial_are_not_success(self):
        if importlib.util.find_spec('pypdf') is None:self.skipTest('Optional pypdf is not installed')
        malformed=self.prepare([self.retained('broken.pdf',b'%PDF-invalid')])['documents'][0]
        empty=self.prepare([self.retained('empty.pdf',b'')])['documents'][0]
        blank=self.prepare([self.retained('blank.pdf',pdf(['']))])['documents'][0]
        self.assertEqual(malformed['parse_status'],'malformed_pdf')
        self.assertEqual(empty['parse_status'],'empty'); self.assertEqual(blank['parse_status'],'empty')
        with patch.object(self.bridge,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=1)):
            partial=self.prepare([self.retained('partial.pdf',pdf(['first','second']))])['documents'][0]
        self.assertEqual(partial['parse_status'],'partial'); self.assertTrue(partial['issues'])

    def test_utf8_page_output_limit_is_explicit_and_codepoint_safe(self):
        payload=pdf(['placeholder']); files=[self.retained('request.pdf',payload)]
        extracted=extract_document(payload,'request.pdf'); extracted['pages']=[_page(1,'가나다라마','ok')]
        with patch.object(self.bridge,'MAX_TEXT_BYTES',8),patch.object(self.bridge,'extract_document',return_value=extracted):
            document=self.prepare(files)['documents'][0]
        self.assertLessEqual(len(document['pages'][0]['text'].encode()),8)
        self.assertEqual(document['parse_status'],'partial')
        self.assertIn('utf8_output_limit',{item['code'] for item in document['issues']})

    def test_context_binds_revision_source_and_extraction_profile(self):
        files=[self.retained('request.pdf',pdf(['source']))]; first=self.prepare(files)
        self.assertNotEqual(first['context_id'],self.prepare(files,revision=2)['context_id'])
        self.assertNotEqual(first['context_id'],self.prepare(files,source_id='OTHER')['context_id'])
        with patch.object(self.bridge,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=1)):
            changed=self.prepare(files)
        self.assertNotEqual(first['extraction_profile_id'],changed['extraction_profile_id'])
        self.assertNotEqual(first['context_id'],changed['context_id'])

    def test_page_metadata_context_limit_remains_a_typed_pdf_failure(self):
        payload=pdf(['source']);files=[self.retained('request.pdf',payload)]
        extracted=extract_document(payload,'request.pdf')
        extracted.update(status='ok',complete=True,pages=[_page(1,'x\n'*3000,'ok')])
        with patch.object(self.bridge,'MAX_CONTEXT_BYTES',6000),patch.object(self.bridge,'extract_document',return_value=extracted):
            prepared=self.prepare(files)
        document=prepared['documents'][0]
        self.assertEqual(document['parse_status'],'limit_exceeded');self.assertEqual(document['pages'],[])
        self.assertIn('context_byte_limit',{issue['code'] for issue in document['issues']})
        self.assertLessEqual(len(canonical(prepared).encode('utf-8')),6000)

    def test_corrupt_original_and_oversized_context_are_rejected(self):
        files=[self.retained('request.pdf',pdf(['source']))]
        with patch.object(self.bridge,'MAX_CONTEXT_BYTES',100):
            with self.assertRaises(ValueError):self.prepare(files)
        self.store.blob_path(files[0]['sha256']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):self.prepare(files)

    def test_concurrent_preparation_never_reads_a_partially_written_context_blob(self):
        files=[self.retained('request.txt',b'market: EU')]
        first_started=threading.Event(); release=threading.Event(); original=self.store.write_blob
        def slow_first(payload):
            if first_started.is_set():return original(payload)
            sha=hashlib.sha256(payload).hexdigest()
            with self.store.blob_path(sha).open('xb') as stream:
                stream.write(payload[:1]);stream.flush();first_started.set()
                if not release.wait(5):raise RuntimeError('test writer was not released')
                stream.write(payload[1:])
            return sha
        with patch.object(self.store,'write_blob',side_effect=slow_first),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.prepare,files)
            self.assertTrue(first_started.wait(5))
            second=pool.submit(self.prepare,files)
            time.sleep(.1);release.set()
            self.assertEqual(first.result(5),second.result(5))

    def test_encrypted_and_missing_parser_remain_distinct(self):
        if importlib.util.find_spec('pypdf') is None:self.skipTest('Optional pypdf is not installed')
        import sys
        from io import BytesIO
        from pypdf import PdfWriter
        writer=PdfWriter(clone_from=BytesIO(pdf(['source'])))
        writer.encrypt('synthetic-test-password');stream=BytesIO();writer.write(stream)
        encrypted=self.prepare([self.retained('encrypted.pdf',stream.getvalue())])['documents'][0]
        self.assertEqual(encrypted['parse_status'],'encrypted');self.assertEqual(encrypted['pages'],[])
        with patch.dict(sys.modules,{'pypdf':None}):
            missing=self.prepare([self.retained('missing.pdf',pdf(['source']))])['documents'][0]
        self.assertEqual(missing['parse_status'],'parser_unavailable')

    def test_missing_optional_parser_keeps_the_pdf_failure_visible(self):
        import sys
        with patch.dict(sys.modules,{'pypdf':None}):
            document=self.prepare([self.retained('request.pdf',pdf(['source']))])['documents'][0]
        self.assertEqual(document['parse_status'],'parser_unavailable')
        self.assertIsNone(document['text']);self.assertEqual(document['pages'],[])

    def test_other_pdf_failure_states_are_preserved_without_text_fallback(self):
        payload=pdf(['source']);files=[self.retained('request.pdf',payload)]
        for status in ('image_only','no_text','parser_error','limit_exceeded'):
            result=extract_document(payload,'request.pdf')
            result.update(status=status,complete=False,pages=[_page(1,'',status)])
            with self.subTest(status=status),patch.object(self.bridge,'extract_document',return_value=result):
                document=self.prepare(files)['documents'][0]
                self.assertEqual(document['parse_status'],status);self.assertIsNone(document['text'])


@unittest.skipUnless(importlib.util.find_spec('pypdf') is not None,'Optional pypdf is not installed')
class PDFAnalysisConnectionTests(DocumentBridgeCase):
    def setUp(self):
        super().setUp(); self.inbox=self.root/'inbox';self.inbox.mkdir()
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)

    def receive(self,payload,path='request.pdf'):
        folder=self.inbox/'one';folder.mkdir(exist_ok=True);(folder/path).write_bytes(payload)
        scan_source(self.store,'INBOX',now=100)
        return scan_source(self.store,'INBOX',now=102)['accepted'][0]

    def provider_context(self,job):
        return {key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents',
                                        'analysis_context_id','analysis_contract','instructions')}

    def test_actual_two_page_claim_provider_complete_uses_schema_two(self):
        received=self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); analysis=SyntheticTextProvider().analyze(self.provider_context(job))
        self.assertEqual(analysis['schema_version'],2);self.assertEqual(analysis['context_id'],job['analysis_context_id'])
        market=next(f for f in analysis['facts'] if f['field']=='market')
        self.assertEqual(market['evidence'][0]['page_number'],2)
        result=complete_job(self.store,job['job_id'],job['token'],analysis,now=104)
        self.assertEqual(result['facts']['product_type']['value'],'remote_control')
        self.assertEqual(result['facts']['market']['value'],'EU')
        self.assertEqual(result['unread_documents'],[]);self.assertEqual(result['next_action'],'propose_start')
        self.assertEqual(complete_job(self.store,job['job_id'],job['token'],analysis,now=500),result)
        self.assertEqual(len(notifications(self.store)),1)
        self.assertEqual(intake_status(self.store)[0]['revision'],received['revision'])

    def test_actual_bounded_fixture_worker_consumes_pdf_pages(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        report=run_worker(self.store,SyntheticTextProvider(),worker_id='pdf-fixture',max_jobs=1,
                          provider_timeout_seconds=10,lease_seconds=30)
        self.assertEqual(report['results'][0]['status'],'completed')
        self.assertEqual(intake_status(self.store)[0]['analysis']['facts']['market']['value'],'EU')

    def test_pdf_citation_tampering_is_rejected_atomically(self):
        self.receive(pdf(['product_type: remote_control\nmarket: EU','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); original=SyntheticTextProvider().analyze(self.provider_context(job))
        for key,bad in (('page_number',2),('text_sha256','0'*64),('extraction_id','0'*64),
                        ('line_start',0),('sha256','0'*64),('quote','fabricated'),('path','other.pdf')):
            value=copy.deepcopy(original); value['facts'][0]['evidence'][0][key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):
                complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertIsNone(intake_status(self.store)[0]['analysis']);self.assertEqual(notifications(self.store),[])

    def test_partial_valid_page_keeps_unread_question(self):
        self.receive(pdf(['product_type: remote_control\nmarket: EU\npurpose: radio_test','unread page']))
        with patch.object(self.bridge,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=1)):
            job=claim_job(self.store,'worker',now=103)
            value=SyntheticTextProvider().analyze(self.provider_context(job))
            result=complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertEqual(result['facts']['market']['value'],'EU')
        self.assertIn('unread_documents',{q['key'] for q in result['questions']})
        self.assertEqual(result['next_action'],'needs_information')

    def test_old_context_is_rejected_including_completed_resubmission(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        with patch.object(self.bridge,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=1)):
            with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=104)
        result=complete_job(self.store,job['job_id'],job['token'],value,now=104)
        with patch.object(self.bridge,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=1)):
            with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=105)
        self.assertEqual(intake_status(self.store)[0]['analysis'],result)

    def test_pdf_parsing_is_outside_claim_and_complete_write_transactions(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        actual=self.bridge.extract_document; calls=[]
        def checked(*args,**kwargs):
            with self.store.connection() as con:
                con.execute('PRAGMA busy_timeout=50');con.execute('BEGIN IMMEDIATE');con.rollback()
            calls.append(1);return actual(*args,**kwargs)
        with patch.object(self.bridge,'extract_document',side_effect=checked):
            job=claim_job(self.store,'worker',now=103)
            value=SyntheticTextProvider().analyze(self.provider_context(job))
            complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertGreaterEqual(len(calls),2)

    def test_corrupted_retained_extraction_cannot_complete(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        self.store.blob_path(job['documents'][0]['extraction_id']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertIsNone(intake_status(self.store)[0]['analysis'])

    def test_corrupted_retained_context_cannot_complete(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        self.store.blob_path(job['analysis_context_id']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertEqual(notifications(self.store),[])

    def test_claim_marker_rejects_a_new_context_not_seen_in_that_lease(self):
        received=self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103)
        with self.store.connection() as con:
            revision=dict(con.execute('SELECT * FROM intake_revisions WHERE intake_id=?',(received['intake_id'],)).fetchone())
        with patch.object(self.bridge,'EXTRACTION_LIMITS',ExtractionLimits(max_pages=1)):
            prepared=self.bridge.prepare_analysis_documents(self.store,json.loads(revision['files_json']),
                source_id='INBOX',intake_id=job['intake_id'],revision=job['revision'],revision_fingerprint=revision['fingerprint'])
            changed={**job,'analysis_context_id':prepared['context_id'],'documents':prepared['documents']}
            value=SyntheticTextProvider().analyze(self.provider_context(changed))
            with self.assertRaisesRegex(ValueError,'Claimed analysis context'):
                complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertIsNone(intake_status(self.store)[0]['analysis'])

    def test_expired_claim_replaces_marker_and_token(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        old=claim_job(self.store,'old',now=103,lease_seconds=1)
        with self.store.connection() as con:
            con.execute('UPDATE intake_jobs SET result_json=? WHERE job_id=?',
                        (canonical({'analysis_context_id':'0'*64}),old['job_id']))
        new=claim_job(self.store,'new',now=105)
        self.assertNotEqual(new['token'],old['token'])
        with self.store.connection() as con:
            marker=con.execute('SELECT result_json FROM intake_jobs WHERE job_id=?',(new['job_id'],)).fetchone()[0]
        self.assertEqual(json.loads(marker),{'analysis_context_id':new['analysis_context_id']})
        self.assertNotIn('result_json',new)
        value=SyntheticTextProvider().analyze(self.provider_context(new))
        with self.assertRaises(ValueError):complete_job(self.store,old['job_id'],old['token'],value,now=106)
        self.assertEqual(complete_job(self.store,new['job_id'],new['token'],value,now=106)['unread_documents'],[])

    def test_mixed_text_pdf_schema_two_and_legacy_v1_unread_behavior(self):
        self.receive(pdf(['manufacturer: SYNTHETIC']))
        (self.inbox/'one'/'request.txt').write_text('product_type: remote_control\nmarket: EU\npurpose: radio_test\n',encoding='utf-8')
        scan_source(self.store,'INBOX',now=104);scan_source(self.store,'INBOX',now=106)
        job=claim_job(self.store,'worker',now=107)
        original=SyntheticTextProvider().analyze(self.provider_context(job))
        kinds={e['kind'] for f in original['facts'] for e in f['evidence']}
        self.assertEqual(kinds,{'text_line','pdf_page'})
        legacy=copy.deepcopy(original);legacy['schema_version']=1;legacy.pop('context_id')
        legacy['facts']=[f for f in legacy['facts'] if f['evidence'][0]['kind']=='text_line']
        for fact in legacy['facts']:fact['evidence'][0].pop('kind')
        result=complete_job(self.store,job['job_id'],job['token'],legacy,now=108)
        self.assertEqual(result['unread_documents'],['request.pdf'])
        self.assertEqual(result['next_action'],'needs_information')

    def test_real_pdf_is_not_parsed_or_mutated_by_fixture_worker(self):
        real=self.root/'real';folder=real/'one';folder.mkdir(parents=True)
        (folder/'real.pdf').write_bytes(pdf(['product_type: real-scope-unique\nmarket: EU\npurpose: keep queued']))
        register_source(self.store,'REAL',real,synthetic=False,settle_seconds=1)
        scan_source(self.store,'REAL',now=100);received=scan_source(self.store,'REAL',now=102)['accepted'][0]
        with self.store.connection() as con:
            before=dict(con.execute('SELECT * FROM intake_jobs WHERE intake_id=?',(received['intake_id'],)).fetchone())
        with patch.object(self.bridge,'extract_document',side_effect=AssertionError('real PDF parser called')):
            result=run_worker(self.store,SyntheticTextProvider(),worker_id='fixture-only',max_jobs=1)
        self.assertEqual(result['attempted_jobs'],0)
        with self.store.connection() as con:
            after=dict(con.execute('SELECT * FROM intake_jobs WHERE intake_id=?',(received['intake_id'],)).fetchone())
        self.assertEqual(before,after)

    def test_revision_change_during_claim_preparation_only_claims_new_revision(self):
        first=self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        actual=self.bridge.extract_document; changed=[]
        def supplement(*args,**kwargs):
            if not changed:
                changed.append(True)
                (self.inbox/'one'/'supplement.txt').write_text('note: supplement',encoding='utf-8')
                scan_source(self.store,'INBOX',now=104);scan_source(self.store,'INBOX',now=106)
            return actual(*args,**kwargs)
        with patch.object(self.bridge,'extract_document',side_effect=supplement):
            job=claim_job(self.store,'worker',now=107)
        self.assertEqual(job['revision'],2)
        with self.store.connection() as con:
            old=con.execute('SELECT state,attempt FROM intake_jobs WHERE job_id=?',(first['job_id'],)).fetchone()
        self.assertEqual(tuple(old),('superseded',0))

    def test_revision_change_during_completion_preparation_cannot_post_old_analysis(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        actual=self.bridge.extract_document
        def supplement(*args,**kwargs):
            (self.inbox/'one'/'supplement.txt').write_text('note: supplement',encoding='utf-8')
            scan_source(self.store,'INBOX',now=104);scan_source(self.store,'INBOX',now=106)
            return actual(*args,**kwargs)
        with patch.object(self.bridge,'extract_document',side_effect=supplement):
            with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=107)
        self.assertEqual(intake_status(self.store)[0]['revision'],2)
        self.assertIsNone(intake_status(self.store)[0]['analysis']);self.assertEqual(notifications(self.store),[])

    def test_lease_expiry_during_pdf_preparation_does_not_complete(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103,lease_seconds=1)
        value=SyntheticTextProvider().analyze(self.provider_context(job));clock=[103.5]
        actual=self.bridge.extract_document
        def expires(*args,**kwargs):
            result=actual(*args,**kwargs);clock[0]=105;return result
        with patch('labflow.intake_jobs.timestamp',side_effect=lambda now=None:clock[0] if now is None else now), \
                patch.object(self.bridge,'extract_document',side_effect=expires):
            with self.assertRaisesRegex(ValueError,'expired analysis lease'):
                complete_job(self.store,job['job_id'],job['token'],value)
        self.assertIsNone(intake_status(self.store)[0]['analysis']);self.assertEqual(notifications(self.store),[])

    def test_lease_expiry_during_final_artifact_verification_rolls_back(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103,lease_seconds=1)
        value=SyntheticTextProvider().analyze(self.provider_context(job));clock=[103.5];calls=[]
        from labflow import intake_jobs
        actual=intake_jobs.verify_analysis_documents
        def verify(*args,**kwargs):
            result=actual(*args,**kwargs);calls.append(1)
            if len(calls)==2:clock[0]=105
            return result
        with patch('labflow.intake_jobs.timestamp',side_effect=lambda now=None:clock[0] if now is None else now), \
                patch('labflow.intake_jobs.verify_analysis_documents',side_effect=verify):
            with self.assertRaisesRegex(ValueError,'expired analysis lease'):
                complete_job(self.store,job['job_id'],job['token'],value)
        self.assertIsNone(intake_status(self.store)[0]['analysis']);self.assertEqual(notifications(self.store),[])

    def test_last_source_verification_rolls_back_projection_writes(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        value['facts']=[fact for fact in value['facts'] if fact['field']!='purpose']
        from labflow import intake_jobs
        actual=intake_jobs._refresh
        def corrupt_after_projection(*args,**kwargs):
            result=actual(*args,**kwargs)
            self.store.blob_path(job['documents'][0]['sha256']).write_bytes(b'changed during projection')
            return result
        with patch('labflow.intake_jobs._refresh',side_effect=corrupt_after_projection):
            with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=104)
        with self.store.connection() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM intake_questions').fetchone()[0],0)
        self.assertIsNone(intake_status(self.store)[0]['analysis']);self.assertEqual(notifications(self.store),[])

    def test_same_quote_on_another_page_cannot_replace_page_hash(self):
        self.receive(pdf(['product_type: remote_control\nmarket: EU','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        market=next(fact for fact in value['facts'] if fact['field']=='market')
        self.assertEqual(market['evidence'][0]['page_number'],1)
        market['evidence'][0].update(page_number=2,line_start=1,line_end=1)
        with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],value,now=104)

    def test_reference_page_does_not_set_requested_market(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        for fact in value['facts']:
            if fact['field']=='market':fact['evidence'][0]['role']='reference'
        result=complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertNotIn('market',result['facts']);self.assertIn('missing_market',{q['key'] for q in result['questions']})

    def test_conflicting_pages_keep_the_existing_conflict_question(self):
        self.receive(pdf(['product_type: remote_control\nmarket: EU','market: US\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); value=SyntheticTextProvider().analyze(self.provider_context(job))
        result=complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertIn('conflict_market',{q['key'] for q in result['questions']})
        self.assertEqual(result['next_action'],'needs_information')

    def test_nonrunning_failure_preserves_inactive_context_audit(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        for attempt in (1,2):
            job=claim_job(self.store,'worker',now=102+attempt,lease_seconds=1)
            fail_job(self.store,job['job_id'],job['token'],now=102+attempt+.5)
            with self.store.connection() as con:
                state,marker=con.execute('SELECT state,result_json FROM intake_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
            self.assertEqual(state,'queued')
            self.assertEqual(json.loads(marker) if marker else None,{'analysis_context_id':job['analysis_context_id']})
        final=claim_job(self.store,'worker',now=105,lease_seconds=1)
        self.assertIsNone(claim_job(self.store,'worker',now=107))
        with self.store.connection() as con:
            state,marker=con.execute('SELECT state,result_json FROM intake_jobs WHERE job_id=?',(final['job_id'],)).fetchone()
        self.assertEqual(state,'failed')
        self.assertEqual(json.loads(marker) if marker else None,{'analysis_context_id':final['analysis_context_id']})
        value=SyntheticTextProvider().analyze(self.provider_context(final))
        with self.assertRaises(ValueError):complete_job(self.store,final['job_id'],final['token'],value,now=107)

    def test_schema_two_discriminators_and_private_extra_fields_are_strict(self):
        self.receive(pdf(['product_type: remote_control','market: EU\npurpose: radio_test']))
        job=claim_job(self.store,'worker',now=103); original=SyntheticTextProvider().analyze(self.provider_context(job))
        for target in ('citation_kind','role','fact_status','producer','identity','context','extra'):
            value=copy.deepcopy(original)
            if target=='citation_kind':value['facts'][0]['evidence'][0]['kind']=[]
            elif target=='role':value['facts'][0]['evidence'][0]['role']=[]
            elif target=='fact_status':value['facts'][0]['status']=[]
            elif target=='producer':value['producer']['kind']=[]
            elif target=='identity':value['identity']=[]
            elif target=='context':value['context_id']=None
            else:value['grant_authority']=True
            with self.subTest(target=target),self.assertRaises(ValueError):
                complete_job(self.store,job['job_id'],job['token'],value,now=104)
        self.assertIsNone(intake_status(self.store)[0]['analysis'])

    def test_invalid_analysis_with_legacy_missing_marker_is_rejected(self):
        self.receive(pdf(['source']))
        job=claim_job(self.store,'worker',now=103)
        with self.store.connection() as con:
            con.execute('UPDATE intake_jobs SET result_json=NULL WHERE job_id=?',(job['job_id'],))
        with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],None,now=104)


if __name__=='__main__':unittest.main()
