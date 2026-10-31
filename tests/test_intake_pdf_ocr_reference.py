"""Current synthetic Store -> installed local OCR -> explicitly derived evidence."""
import copy
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from labflow.active_intake import register_source, scan_source, intake_status
from labflow.development_paths import load_layout
from labflow.document_extract import extract_document
from labflow.intake_documents import current_extraction_profile_id
from labflow.intake_jobs import prepare_registered_synthetic_context
from labflow.codex_intake_once import preflight_codex_intake_once_inputs
from labflow.store import Store, canonical

try:
    api=importlib.import_module('labflow.intake_pdf_ocr_reference')
except ModuleNotFoundError as error:
    if error.name!='labflow.intake_pdf_ocr_reference':raise
    api=None

OBSERVATIONS=[]
def H(raw):return hashlib.sha256(raw).hexdigest()
def image_pdf(pages=1):
    image=Image.new('RGB',(1200,400),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=54)
    draw.text((65,75),'MODEL SYN OCR 001',fill='black',font=font)
    draw.text((65,180),'PURPOSE RF TEST',fill='black',font=font)
    stream=io.BytesIO();image.save(stream,'PDF',resolution=100)
    if pages==1:return stream.getvalue()
    reader=PdfReader(io.BytesIO(stream.getvalue()));writer=PdfWriter()
    for _ in range(pages):writer.add_page(reader.pages[0])
    output=io.BytesIO();writer.write(output);return output.getvalue()


class OcrReferenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned real local OCR reference API absent')
        parent=Path(os.environ.get('DGM_LOCAL_OCR_TEST_ROOT',str(load_layout().output('dev1/local-ocr-tests'))))
        parent.mkdir(parents=True,exist_ok=True)
        self.base=Path(tempfile.mkdtemp(prefix='ocr-',dir=parent));self.clock=100
        self.creator=Store(self.base/'state');self.addCleanup(self.creator.close)
        self.bundle=self.base/'inbox'/'one';self.bundle.mkdir(parents=True)
        register_source(self.creator,'OCR-SYN',self.bundle.parent,synthetic=True,settle_seconds=1)
        self.stage(image_pdf())
        self.store=Store.open_existing(str(self.creator.root));self.addCleanup(self.store.close)
        self.tools=None
        config=os.environ.get('DGM_LOCAL_OCR_TOOLS_CONFIG')
        if config:self.tools=api.LocalOcrTools(**json.loads(Path(config).read_bytes()))
        self.counter=0
        self.addCleanup(lambda:OBSERVATIONS.append(dict(test=self._testMethodName,root=str(self.base))))

    def stage(self,payload):
        (self.bundle/'scan.PDF').write_bytes(payload);self.payload=payload;self.clock+=3
        scan_source(self.creator,'OCR-SYN',now=self.clock,synthetic_only=True)
        result=scan_source(self.creator,'OCR-SYN',now=self.clock+2,synthetic_only=True)
        if not hasattr(self,'intake_id'):self.intake_id=result['accepted'][0]['intake_id']

    def arguments(self):
        status=intake_status(self.creator,self.intake_id);item=status['files'][0];self.counter+=1
        return dict(store=self.store,intake_id=self.intake_id,document_path=item['path'],
            expected_revision=status['revision'],expected_sha256=item['sha256'],tools=self.tools,
            run_root=self.base/('evidence-'+str(self.counter)))

    def rows(self):
        with self.creator.connection() as con:
            tables=[row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name:[tuple(row) for row in con.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in tables}

    def test_installed_english_OCR_links_current_store_and_derived_citation_without_promotion(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        original=extract_document(self.payload,'scan.PDF')
        self.assertEqual(original['status'],'image_only');self.assertFalse(original['complete'])
        args=self.arguments();state=intake_status(self.creator,self.intake_id)
        selection=dict(source_id='OCR-SYN',intake_id=self.intake_id,revision=state['revision'],
            job_id=state['jobs'][0]['job_id'],revision_fingerprint=state['history'][-1]['fingerprint'],files=state['files'])
        context=prepare_registered_synthetic_context(self.creator,selection,producer_name='OCR-BASELINE')
        blocked=preflight_codex_intake_once_inputs(context,producer_name='OCR-BASELINE')
        self.assertEqual(blocked['status'],'blocked');self.assertEqual(blocked['failure'],'codex_intake_once_unsupported_schema')
        before=self.rows();profile=current_extraction_profile_id()
        database=H(self.creator.db.read_bytes());blob=H(self.creator.blob_path(args['expected_sha256']).read_bytes())
        result=api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(result['status'],'ocr_observed',result)
        self.assertIn('MODEL SYN OCR 001',result['ocr']['text'])
        self.assertIn('PURPOSE RF TEST',result['ocr']['text'])
        self.assertEqual(result['baseline'],original)
        self.assertFalse(result['complete']);self.assertFalse(result['native_once_eligible'])
        self.assertEqual(result['ocr']['method'],'tesseract_local')
        self.assertEqual(result['ocr']['page_number'],1)
        self.assertEqual(result['ocr']['text_sha256'],H(result['ocr']['text'].encode('utf-8')))
        self.assertEqual(result['tools']['tesseract_version_source'],'installed_dll_TessVersion')
        self.assertEqual(result['tools']['tesseract_version'],'v5.3.3.20231005')
        self.assertEqual(result['tools']['language'],'eng')
        citation=api.ocr_page_citation(result,1,1)
        self.assertEqual(citation['kind'],'pdf_ocr_page');self.assertEqual(citation['page_number'],1)
        self.assertEqual(citation['source_sha256'],args['expected_sha256'])
        self.assertEqual(citation['quote'],'MODEL SYN OCR 001')
        self.assertFalse(citation['original_text']);self.assertEqual(citation['image_text_equivalence'],'not_verified')
        self.assertEqual(self.rows(),before);self.assertEqual(current_extraction_profile_id(),profile)
        self.assertEqual(preflight_codex_intake_once_inputs(context,producer_name='OCR-BASELINE'),blocked)
        self.assertEqual(H(self.creator.db.read_bytes()),database)
        self.assertEqual(H(self.creator.blob_path(args['expected_sha256']).read_bytes()),blob)
        persisted=json.loads((args['run_root']/'reference.json').read_bytes());self.assertEqual(persisted,result)
        OBSERVATIONS.append(dict(test='real_positive',reference=result,run_root=str(args['run_root']),
            original_blob_unchanged=True,database_rows_and_bytes_unchanged=True,extraction_profile_unchanged=True))

    def test_revision_hash_and_nonsynthetic_are_rejected_before_native_children(self):
        for changes,suffix in ((dict(expected_revision=999),'revision_changed'),(dict(expected_sha256='f'*64),'revision_changed')):
            args=self.arguments();args.update(changes)
            with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:api.read_intake_pdf_ocr_reference(**args)
            self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_'+suffix)
            self.assertFalse(args['run_root'].exists())
        with self.creator.connection() as con:con.execute("UPDATE intake_sources SET synthetic=0 WHERE source_id='OCR-SYN'")
        args=self.arguments()
        with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_synthetic_required')
        self.assertFalse(args['run_root'].exists())

    def test_unconfigured_tools_keep_ocr_required_and_baseline_incomplete(self):
        args=self.arguments();args['tools']=None;before=self.rows()
        result=api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(result['status'],'ocr_required');self.assertIsNone(result['ocr'])
        self.assertEqual(result['errors'],['intake_pdf_ocr_reference_tools_unavailable'])
        self.assertFalse(result['complete']);self.assertFalse(result['native_once_eligible'])
        self.assertIn('ocr_required',[row['code'] for row in result['baseline']['issues']])
        self.assertEqual(self.rows(),before)

    def test_multipage_and_malformed_preserve_original_without_child_entry(self):
        for payload in (image_pdf(2),b'%PDF-1.7\nauthored malformed'):
            self.stage(payload);args=self.arguments()
            with patch.object(api,'_run',side_effect=AssertionError('CHILD_FORBIDDEN')):
                result=api.read_intake_pdf_ocr_reference(**args)
            self.assertEqual(result['status'],'ocr_required');self.assertIsNone(result['ocr'])
            self.assertFalse(result['complete']);self.assertFalse(result['native_once_eligible'])

    def test_language_pin_mismatch_never_invokes_renderer_or_OCR(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        args=self.arguments();args['tools']=replace(self.tools,language_sha256='f'*64)
        with patch.object(api,'_run',side_effect=AssertionError('CHILD_FORBIDDEN')):
            result=api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(result['status'],'ocr_required')
        self.assertEqual(result['errors'],['intake_pdf_ocr_reference_tool_pin_mismatch'])

    def test_remote_tool_path_is_unavailable_before_any_tool_file_read(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        args=self.arguments();args['tools']=replace(self.tools,tesseract_executable=r'\\server\share\tesseract.exe')
        with patch.object(api,'_file_pin',side_effect=AssertionError('REMOTE_TOOL_READ_FORBIDDEN')):
            result=api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(result['status'],'ocr_required')
        self.assertEqual(result['errors'],['intake_pdf_ocr_reference_tools_unavailable'])

    def test_input_byte_limit_blocks_before_parser_and_work_creation(self):
        self.stage(b'%PDF-'+b'x'*(2*1024*1024));args=self.arguments()
        with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_input_limit')
        self.assertFalse(args['run_root'].exists())

    def test_out_of_scope_text_page_is_bounded_without_OCR_or_default_path_changes(self):
        writer=PdfWriter();page=writer.add_blank_page(612,792)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 12 TL '+b'(A) Tj T* '*20000+b'ET')
        page[NameObject('/Contents')]=writer._add_object(stream);payload=io.BytesIO();writer.write(payload)
        self.stage(payload.getvalue());args=self.arguments()
        with patch.object(api,'_run',side_effect=AssertionError('CHILD_FORBIDDEN')):
            result=api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(result['status'],'ocr_required');self.assertIsNone(result['ocr'])
        self.assertLessEqual(len(result['baseline']['pages'][0]['text']),16384)
        self.assertFalse(result['baseline']['complete'])

    def test_control_exception_preserves_failure_and_never_returns_observed(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        args=self.arguments();sentinel=MemoryError('authored first control')
        with patch.object(api,'_run',side_effect=sentinel):
            with self.assertRaises(MemoryError) as caught:api.read_intake_pdf_ocr_reference(**args)
        self.assertIs(caught.exception,sentinel)
        retained=json.loads((args['run_root']/'reference.json').read_bytes())
        self.assertEqual(retained['status'],'ocr_required');self.assertIsNone(retained['ocr'])

    def test_invalid_unicode_and_run_root_return_fixed_argument_errors(self):
        for change in (dict(document_path='bad\ud800.pdf'),dict(run_root=None)):
            with self.subTest(field=next(iter(change))):
                args=self.arguments();args.update(change)
                try:api.read_intake_pdf_ocr_reference(**args)
                except Exception as error:
                    self.assertIsInstance(error,api.IntakePdfOcrReferenceError)
                    self.assertEqual(error.code,'intake_pdf_ocr_reference_invalid_argument')
                else:self.fail('invalid argument accepted')

    def authored_process(self,command,work,label,**limits):
        if label=='renderer-version':return b'',b'pdftoppm version 26.07.0\n'
        if label=='render':
            Image.new('L',(300,100),255).save(work/'page.png');return b'',b''
        self.assertEqual(label,'ocr')
        if getattr(self,'revoke_synthetic',False):
            with self.creator.connection() as con:con.execute("UPDATE intake_sources SET synthetic=0 WHERE source_id='OCR-SYN'")
        return getattr(self,'authored_ocr_raw',b'MODEL SYN OCR 001\n'),b''

    def test_source_provenance_change_during_child_cannot_return_observed(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        self.revoke_synthetic=True
        with patch.object(api,'_run',side_effect=self.authored_process):
            result=api.read_intake_pdf_ocr_reference(**self.arguments())
        self.assertEqual(result['status'],'ocr_required');self.assertIsNone(result['ocr'])
        self.assertEqual(result['errors'],['intake_pdf_ocr_reference_synthetic_required'])

    def test_authored_citation_tamper_empty_OCR_and_reused_run_stay_closed(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        args=self.arguments()
        with patch.object(api,'_run',side_effect=self.authored_process):
            result=api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(result['status'],'ocr_observed')
        for part in ('text','binding','method'):
            with self.subTest(part=part):
                changed=copy.deepcopy(result)
                if part=='text':changed['ocr']['text']='forged quote'
                elif part=='binding':changed['binding']['document']['sha256']='f'*64
                else:changed['ocr']['method']='original_pdf_text'
                with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:api.ocr_page_citation(changed,1,1)
                self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_invalid_reference')
        saved=(args['run_root']/'reference.json').read_bytes()
        with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:api.read_intake_pdf_ocr_reference(**args)
        self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_run_unavailable')
        self.assertEqual((args['run_root']/'reference.json').read_bytes(),saved)
        self.authored_ocr_raw=b' \n'
        with patch.object(api,'_run',side_effect=self.authored_process):
            empty=api.read_intake_pdf_ocr_reference(**self.arguments())
        self.assertEqual(empty['status'],'ocr_required');self.assertIsNone(empty['ocr'])
        self.assertEqual(empty['errors'],['intake_pdf_ocr_reference_empty_ocr'])

    def test_late_source_close_control_cannot_leave_observed_receipt(self):
        if self.tools is None:self.skipTest('explicit installed-tool pin configuration absent')
        original=api._source._source;sentinel=MemoryError('authored late source close')
        @contextmanager
        def late_close(*args,**kwargs):
            with original(*args,**kwargs) as opened:yield opened
            raise sentinel
        args=self.arguments()
        with patch.object(api._source,'_source',late_close),patch.object(api,'_run',side_effect=self.authored_process):
            with self.assertRaises(MemoryError) as caught:api.read_intake_pdf_ocr_reference(**args)
        self.assertIs(caught.exception,sentinel)
        retained=json.loads((args['run_root']/'reference.json').read_bytes())
        self.assertEqual(retained['status'],'ocr_required');self.assertIsNone(retained['ocr'])


class BoundedChildTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned real local OCR reference API absent')
        parent=Path(os.environ.get('DGM_LOCAL_OCR_TEST_ROOT',str(load_layout().output('dev1/local-ocr-tests'))))
        parent.mkdir(parents=True,exist_ok=True);self.base=Path(tempfile.mkdtemp(prefix='child-',dir=parent))

    def test_timeout_reaps_real_python_child_and_preserves_bounded_prefix(self):
        command=[sys.executable,'-B','-c','import time; time.sleep(10)']
        with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:
            api._run(command,self.base,'timeout',seconds=0.05,stdout_cap=16384)
        self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_process_timeout')
        record=json.loads((self.base/'timeout-process.json').read_bytes())
        self.assertTrue(record['child_reaped']);self.assertTrue(record['readers_joined']);self.assertTrue(record['pipes_closed'])
        self.assertTrue(record['job_assigned_before_resume']);self.assertTrue(record['job_closed'])

    def test_output_overflow_reaps_child_and_retains_only_limit(self):
        command=[sys.executable,'-B','-c',"import os; os.write(1,b'x'*65536)"]
        with self.assertRaises(api.IntakePdfOcrReferenceError) as caught:
            api._run(command,self.base,'overflow',seconds=5,stdout_cap=16384)
        self.assertEqual(caught.exception.code,'intake_pdf_ocr_reference_output_limit')
        self.assertEqual((self.base/'overflow-stdout.bin').stat().st_size,16384)
        record=json.loads((self.base/'overflow-process.json').read_bytes())
        self.assertTrue(record['child_reaped']);self.assertTrue(record['readers_joined']);self.assertTrue(record['pipes_closed'])
        self.assertTrue(record['job_assigned_before_resume']);self.assertTrue(record['job_closed'])


if __name__=='__main__':unittest.main()
