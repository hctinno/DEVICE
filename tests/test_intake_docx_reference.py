"""Synthetic registered intake DOCX reference contracts; no original documents."""
import importlib.util
from contextlib import contextmanager
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest import mock

from labflow.active_intake import register_source, scan_source, intake_status
from labflow.store import Store, canonical
from labflow.reference_docx import read_docx as real_reader
from tests.test_reference_docx import package, paragraph, table, cell, flagged


class IntakeDocxAPIAbsenceTests(unittest.TestCase):
    def test_intake_docx_reference_api_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.intake_docx_reference'))

    def test_intake_docx_retention_api_exists(self):
        from labflow import intake_docx_reference
        self.assertTrue(callable(getattr(intake_docx_reference, 'retain_intake_docx_reference', None)))


class RegisteredDocxReferenceTests(unittest.TestCase):
    def setUp(self):
        self.api=__import__('labflow.intake_docx_reference',fromlist=['read_intake_docx_reference'])
        parent=Path(__file__).resolve().parents[1]/'.local'
        parent.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='docx-ref-',dir=parent)
        self.base=Path(self.temp.name).resolve()
        self.assertTrue(self.base.is_relative_to(parent.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.creator=Store(self.base/'state');self.addCleanup(self.creator.close)
        self.inbox=self.base/'inbox';self.bundle=self.inbox/'one';self.bundle.mkdir(parents=True)
        register_source(self.creator,'SYN-DOCX',self.inbox,synthetic=True,settle_seconds=1)
        self.clock=100
        self.stage(package(paragraph('stored body')))
        self.store=Store.open_existing(str(self.creator.root));self.addCleanup(self.store.close)

    def stage(self,data):
        (self.bundle/'request.docx').write_bytes(data)
        self.payload=data
        self.clock+=3
        scan_source(self.creator,'SYN-DOCX',now=self.clock)
        result=scan_source(self.creator,'SYN-DOCX',now=self.clock+2)
        if not hasattr(self,'intake_id'):
            self.intake_id=result['accepted'][0]['intake_id']

    def arguments(self):
        state=intake_status(self.creator,self.intake_id)
        selected=next(item for item in state['files'] if item['path'].endswith('.docx'))
        return dict(store=self.store,intake_id=self.intake_id,document_path=selected['path'],
                    expected_revision=state['revision'],expected_sha256=selected['sha256'])

    def read(self,**changes):
        args=self.arguments();args.update(changes)
        value=self.api.read_intake_docx_reference(**args)
        self.assertIsInstance(value,dict)
        self.assertEqual(set(value),{'schema_version','kind','binding','result'})
        self.assertEqual(value['schema_version'],1);self.assertEqual(value['kind'],'intake_docx_reference')
        self.assertEqual(set(value['binding']),{'source_id','intake_id','revision','revision_fingerprint','document'})
        self.assertEqual(set(value['binding']['document']),{'path','sha256','bytes'})
        self.assertNotIn('extraction_id',value);self.assertNotIn('analysis_context_id',value)
        self.assertEqual(value['result']['scope']['page_numbers'],'unavailable')
        return value

    def error(self,suffix,**changes):
        args=self.arguments();args.update(changes)
        with self.assertRaises(self.api.IntakeDocxReferenceError) as caught:
            self.api.read_intake_docx_reference(**args)
        code='intake_docx_reference_'+suffix
        self.assertEqual(caught.exception.code,code);self.assertEqual(str(caught.exception),code)
        self.assertIsNone(caught.exception.__cause__)

    def rows(self):
        with self.creator.connection() as con:
            names=[row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name:[tuple(row) for row in con.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in names}

    def set_manifest(self,files,*,fingerprint=None):
        digest=hashlib.sha256(canonical(files).encode('utf-8')).hexdigest() if fingerprint is None else fingerprint
        state=intake_status(self.creator,self.intake_id)
        with self.creator.connection() as con:
            con.execute('UPDATE intake_revisions SET files_json=?,fingerprint=? WHERE intake_id=? AND revision=?',
                        (canonical(files),digest,self.intake_id,state['revision']))

    def blob(self):
        return self.creator.blob_path(self.arguments()['expected_sha256'])

    def test_registered_nested_body_binding_and_native_transparency(self):
        self.stage(package(paragraph('first')+table(['<w:tr>'+cell(blocks=table(['<w:tr>'+cell('nested')+'</w:tr>'],1))+'</w:tr>'],1)+paragraph('last')))
        state=intake_status(self.creator,self.intake_id);before=self.rows();captured=[]
        original=self.store.connection;active=[];queries=[]
        @contextmanager
        def observed_connection():
            with original() as con:
                active.append(con);con.set_trace_callback(queries.append)
                try: yield con
                finally: active.remove(con)
        def parse(data,name):
            self.assertEqual(active,[])
            self.assertEqual(data,self.payload);self.assertEqual(name,'request.docx')
            result=real_reader(data,name);captured.append(result);return result
        with mock.patch.object(self.store,'connection',observed_connection),mock.patch.object(self.api,'read_docx',side_effect=parse):
            value=self.read()
        self.assertEqual(len(captured),1);self.assertEqual(value['result'],captured[0])
        self.assertEqual(value['result']['blocks'][0]['text'],'first')
        self.assertEqual(value['result']['blocks'][1]['rows'][0]['cells'][0]['blocks'][0]['rows'][0]['cells'][0]['blocks'][0]['text'],'nested')
        self.assertEqual(value['result']['blocks'][2]['locator']['path'][-1],{'kind':'paragraph','element_index':3})
        self.assertEqual(value['binding'],{'source_id':'SYN-DOCX','intake_id':self.intake_id,'revision':state['revision'],
                         'revision_fingerprint':state['history'][-1]['fingerprint'],'document':state['files'][0]})
        self.assertEqual(value['result']['source'],{'filename':'request.docx','sha256':hashlib.sha256(self.payload).hexdigest(),'size_bytes':len(self.payload)})
        self.assertFalse(any(sql.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'} for sql in queries))
        self.assertEqual(self.rows(),before)
        with self.store.connection() as con:self.assertEqual(con.execute('SELECT 1').fetchone()[0],1)

    def test_invalid_arguments_precede_source_and_parser(self):
        bad=[{'intake_id':''},{'intake_id':'../x'},{'expected_revision':True},{'expected_revision':0},
             {'expected_revision':1.0},{'expected_sha256':'A'*64},{'expected_sha256':'0'*63},
             {'document_path':'../request.docx'},{'document_path':'/request.docx'},
             {'document_path':'a//b.docx'},{'document_path':'a\\b.docx'},{'document_path':'x.txt'},
             {'document_path':'x\x00.docx'},{'document_path':'x\ud800.docx'},{'document_path':'a'*1020+'.docx'}]
        with mock.patch.object(self.api,'read_docx',side_effect=AssertionError('parser')):
            for case in bad:
                with self.subTest(case=repr(case)):self.error('invalid_argument',**case)

    def test_legacy_closed_and_non_store_are_rejected(self):
        self.error('store_invalid',store=self.creator)
        self.error('store_invalid',store=object())
        self.store.close();self.error('store_invalid')

    def test_missing_and_stale_selection_never_parses(self):
        with mock.patch.object(self.api,'read_docx',side_effect=AssertionError('parser')):
            self.error('intake_not_found',intake_id='MISSING')
            self.error('document_not_found',document_path='missing.docx')
            self.error('revision_changed',expected_revision=99)
            self.error('revision_changed',expected_sha256='0'*64)

    def test_upload_incomplete_is_not_a_stable_revision(self):
        with self.creator.connection() as con:con.execute("UPDATE intakes SET status='upload_incomplete' WHERE intake_id=?",(self.intake_id,))
        self.error('intake_unavailable')

    def test_full_manifest_fingerprint_and_duplicates_are_checked(self):
        item=intake_status(self.creator,self.intake_id)['files'][0]
        self.set_manifest([item],fingerprint='0'*64);self.error('source_integrity_invalid')
        self.set_manifest([item,item]);self.error('source_integrity_invalid')
        self.set_manifest([{**item,'bytes':True}]);self.error('source_integrity_invalid')

    def test_registered_blob_metadata_and_actual_hash_are_required(self):
        args=self.arguments()
        with self.creator.connection() as con:con.execute('UPDATE blobs SET bytes=bytes+1 WHERE sha256=?',(args['expected_sha256'],))
        self.error('source_integrity_invalid')
        with self.creator.connection() as con:con.execute('UPDATE blobs SET bytes=bytes-1 WHERE sha256=?',(args['expected_sha256'],))
        self.blob().write_bytes(b'x'*len(self.payload));self.error('source_integrity_invalid')

    def test_missing_blob_is_not_success(self):
        self.blob().unlink();self.error('source_integrity_invalid')

    def test_declared_source_limit_exact_and_plus_one(self):
        self.stage(bytes.fromhex('d0cf11e0a1b11ae1')+b'x'*(16*1024*1024-8))
        value=self.read();self.assertEqual(value['result']['status'],'unsupported_format')
        self.stage(self.payload+b'x')
        with mock.patch.object(self.api,'read_docx',side_effect=AssertionError('parser')):self.error('input_limit')

    def test_path_UTF8_limit_exact_and_plus_one(self):
        item=intake_status(self.creator,self.intake_id)['files'][0]
        path='p/'*509+'x.docx';self.assertEqual(len(path.encode()),1024)
        self.set_manifest([{**item,'path':path}]);self.assertEqual(self.read(document_path=path)['result']['source']['filename'],path)
        self.error('invalid_argument',document_path='p/'*509+'xa.docx')

    def test_manifest_file_count_exact_and_plus_one(self):
        item=intake_status(self.creator,self.intake_id)['files'][0]
        others=[{**item,'path':f'other{i}.txt'} for i in range(999)]
        self.set_manifest([item]+others);self.assertEqual(self.read()['result']['status'],'ok')
        self.set_manifest([item]+others+[{**item,'path':'overflow.txt'}]);self.error('input_limit')

    def test_manifest_bytes_exact_and_plus_one(self):
        state=intake_status(self.creator,self.intake_id);files=state['files'];raw=canonical(files)
        for extra,expected in [(0,'ok'),(1,'input_limit')]:
            padded=raw+' '*(4*1024*1024-len(raw.encode())+extra)
            with self.creator.connection() as con:
                con.execute('UPDATE intake_revisions SET files_json=? WHERE intake_id=? AND revision=?',(padded,self.intake_id,state['revision']))
            if expected=='ok':self.assertEqual(self.read()['result']['status'],'ok')
            else:self.error(expected)

    def test_changed_revision_after_real_parse_discards_result(self):
        def parse(data,name):
            result=real_reader(data,name);self.stage(package(paragraph('replacement')));return result
        args=self.arguments()
        with mock.patch.object(self.api,'read_docx',side_effect=parse):
            with self.assertRaises(self.api.IntakeDocxReferenceError) as caught:self.api.read_intake_docx_reference(**args)
        self.assertEqual(caught.exception.code,'intake_docx_reference_revision_changed')

    def test_changed_blob_bytes_after_parse_discards_result(self):
        path=self.blob()
        def parse(data,name):
            result=real_reader(data,name);path.write_bytes(b'x'*len(data));return result
        with mock.patch.object(self.api,'read_docx',side_effect=parse):self.error('source_integrity_invalid')

    def test_changed_blob_mtime_even_same_bytes_is_rejected(self):
        path=self.blob();before=path.stat()
        def parse(data,name):
            result=real_reader(data,name);os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns+10000000));return result
        with mock.patch.object(self.api,'read_docx',side_effect=parse):self.error('source_integrity_invalid')

    def test_same_bytes_replacement_identity_is_rejected(self):
        path=self.blob();other=self.base/'replacement';other.write_bytes(self.payload);before=path.stat()
        os.utime(other,ns=(before.st_atime_ns,before.st_mtime_ns))
        def parse(data,name):
            result=real_reader(data,name);os.replace(other,path);return result
        with mock.patch.object(self.api,'read_docx',side_effect=parse):self.error('source_integrity_invalid')

    def test_native_empty_partial_and_fatal_statuses_are_preserved(self):
        cases=[(package(''),'empty'),(package(paragraph('kept'),extras=[('word/styles.xml',b'unread')]),'partial'),
               (package(paragraph('x'),namespace='urn:strict'),'unsupported_format'),
               (bytes.fromhex('d0cf11e0a1b11ae1')+b'opaque','unsupported_format'),
               (flagged(package(paragraph('x')),flag=1),'encrypted'),(b'broken','malformed_docx')]
        for data,status in cases:
            self.stage(data);value=self.read()
            self.assertEqual(value['result']['status'],status)
            self.assertEqual(value['result']['complete'],status=='empty')
            if status=='partial':self.assertEqual(value['result']['blocks'][0]['text'],'kept')

    def test_hardlink_and_reparse_sources_are_not_followed(self):
        path=self.blob();alias=self.base/'hardlink';os.link(path,alias)
        self.error('source_integrity_invalid');alias.unlink()
        path.unlink();target=self.base/'junction-target';target.mkdir()
        self.assertTrue(target.resolve().is_relative_to(self.base))
        subprocess.run(['cmd','/c','mklink','/J',str(path),str(target)],check=True,capture_output=True)
        self.error('source_integrity_invalid')

    def test_changed_other_manifest_entry_is_rechecked(self):
        item=intake_status(self.creator,self.intake_id)['files'][0]
        def parse(data,name):
            value=real_reader(data,name)
            self.set_manifest([item,{**item,'path':'other.txt'}])
            return value
        with mock.patch.object(self.api,'read_docx',side_effect=parse):self.error('revision_changed')

    def test_source_id_changes_are_rechecked(self):
        other=self.base/'other-source';other.mkdir()
        register_source(self.creator,'SYN-OTHER',other,synthetic=True,settle_seconds=1)
        def parse(data,name):
            value=real_reader(data,name)
            with self.creator.connection() as con:con.execute('UPDATE intakes SET source_id=? WHERE intake_id=?',('SYN-OTHER',self.intake_id))
            return value
        with mock.patch.object(self.api,'read_docx',side_effect=parse):self.error('revision_changed')

    def test_registered_blob_metadata_is_rechecked_after_native(self):
        sha=self.arguments()['expected_sha256']
        def parse(data,name):
            value=real_reader(data,name)
            with self.creator.connection() as con:con.execute('UPDATE blobs SET bytes=bytes+1 WHERE sha256=?',(sha,))
            return value
        with mock.patch.object(self.api,'read_docx',side_effect=parse):self.error('source_integrity_invalid')

    def test_source_swap_before_native_open_is_rejected(self):
        path=self.blob();replacement=self.base/'swap-before-open';replacement.write_bytes(self.payload)
        info=path.stat();os.utime(replacement,ns=(info.st_atime_ns,info.st_mtime_ns))
        backend=self.store._existing_binding.backend;original=backend.open_read
        def swapped(selected,*args,**kwargs):
            os.replace(replacement,path);return original(selected,*args,**kwargs)
        with mock.patch.object(backend,'open_read',side_effect=swapped),mock.patch.object(self.api,'read_docx',side_effect=AssertionError('parser')):
            self.error('source_integrity_invalid')

    def test_unexpected_bridge_error_is_fixed_and_does_not_log(self):
        from contextlib import redirect_stdout,redirect_stderr
        import io
        output=io.StringIO()
        with redirect_stdout(output),redirect_stderr(output),mock.patch.object(self.api,'read_docx',side_effect=RuntimeError('PRIVATE DATA')):
            self.error('storage_error')
        self.assertEqual(output.getvalue(),'')

    def test_descriptor_reads_are_chunked_twice_and_closed(self):
        self.stage(bytes.fromhex('d0cf11e0a1b11ae1')+b'x'*(200000-8))
        backend=self.store._existing_binding.backend
        opened=[];active=set();reads=[]
        original_open=backend.open_read;original_read=os.read;original_close=os.close
        def open_read(path,*args,**kwargs):
            fd=original_open(path,*args,**kwargs);opened.append(fd);active.add(fd);return fd
        def read(fd,amount):
            data=original_read(fd,amount)
            if fd in active:reads.append((amount,len(data)))
            return data
        def close(fd):
            active.discard(fd);return original_close(fd)
        with mock.patch.object(backend,'open_read',side_effect=open_read),mock.patch('os.read',side_effect=read),mock.patch('os.close',side_effect=close):
            value=self.read()
        self.assertEqual(value['result']['status'],'unsupported_format')
        self.assertEqual(len(opened),2);self.assertEqual(active,set())
        self.assertTrue(all(0<amount<=65536 for amount,_ in reads))
        self.assertEqual(sum(size for _,size in reads),2*len(self.payload))
        for fd in set(opened):
            with self.assertRaises(OSError):os.fstat(fd)

    def test_first_interrupt_survives_source_close_error(self):
        backend=self.store._existing_binding.backend
        original_open=backend.open_read;original_read=os.read;original_close=os.close
        for failure in (MemoryError,KeyboardInterrupt,SystemExit):
            opened=[];active=set();marker=failure('private interruption')
            def open_read(path,*args,**kwargs):
                fd=original_open(path,*args,**kwargs);opened.append(fd);active.add(fd);return fd
            def read(fd,amount):
                if fd in active:raise marker
                return original_read(fd,amount)
            def close(fd):
                original_close(fd)
                if fd in active:active.remove(fd);raise OSError('private close')
            with mock.patch.object(backend,'open_read',side_effect=open_read),mock.patch('os.read',side_effect=read),mock.patch('os.close',side_effect=close):
                with self.assertRaises(failure) as caught:self.read()
            self.assertIs(caught.exception,marker);self.assertEqual(active,set());self.assertTrue(opened)
            for fd in opened:
                with self.assertRaises(OSError):os.fstat(fd)
        with self.store.connection() as con:self.assertEqual(con.execute('SELECT 1').fetchone()[0],1)

    def test_first_integrity_error_survives_source_close_error(self):
        self.blob().write_bytes(b'x'*len(self.payload))
        backend=self.store._existing_binding.backend;opened=set()
        original_open=backend.open_read;original_close=os.close
        def open_read(path,*args,**kwargs):
            fd=original_open(path,*args,**kwargs);opened.add(fd);return fd
        def close(fd):
            original_close(fd)
            if fd in opened:opened.remove(fd);raise OSError('private close')
        with mock.patch.object(backend,'open_read',side_effect=open_read),mock.patch('os.close',side_effect=close):
            self.error('source_integrity_invalid')
        self.assertEqual(opened,set())

    def test_close_only_failure_is_storage_error_without_retry(self):
        backend=self.store._existing_binding.backend;opened=set();closes=[]
        original_open=backend.open_read;original_close=os.close
        def open_read(path,*args,**kwargs):
            fd=original_open(path,*args,**kwargs);opened.add(fd);return fd
        def close(fd):
            original_close(fd)
            if fd in opened:opened.remove(fd);closes.append(fd);raise OSError('private close')
        with mock.patch.object(backend,'open_read',side_effect=open_read),mock.patch('os.close',side_effect=close):self.error('storage_error')
        self.assertEqual(len(closes),1);self.assertEqual(opened,set())

    def connection_close_fault(self):
        from labflow import store as store_module
        original=store_module._open_sql;connections=[]
        class CloseFault:
            def __init__(self,connection):self.connection=connection
            def __getattr__(self,name):return getattr(self.connection,name)
            def close(self):
                self.connection.close()
                raise OSError('PRIVATE SQL CLOSE')
        def opened(*args,**kwargs):
            con=original(*args,**kwargs);connections.append(con);return CloseFault(con)
        return mock.patch.object(store_module,'_open_sql',side_effect=opened),connections

    def test_database_close_only_is_storage_error_and_connection_closed(self):
        fault,connections=self.connection_close_fault()
        with fault:self.error('storage_error')
        self.assertTrue(connections)
        import sqlite3
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')

    def test_first_selection_error_survives_database_close_error(self):
        fault,connections=self.connection_close_fault()
        with fault:self.error('intake_not_found',intake_id='MISSING')
        self.assertTrue(connections)

    def test_native_interrupt_is_propagated_with_caller_alive(self):
        for failure in (MemoryError,KeyboardInterrupt,SystemExit):
            marker=failure('private')
            with mock.patch.object(self.api,'read_docx',side_effect=marker),self.assertRaises(failure) as caught:self.read()
            self.assertIs(caught.exception,marker)
        with self.store.connection() as con:self.assertEqual(con.execute('SELECT 1').fetchone()[0],1)

    def test_native_limit_and_parser_error_remain_native_failures(self):
        self.stage(package(paragraph('x'*1000001)))
        self.assertEqual(self.read()['result']['status'],'limit_exceeded')
        self.stage(package(paragraph('x')))
        with mock.patch('labflow.reference_docx.zipfile.ZipFile',side_effect=RuntimeError('DO_NOT_LOG')):
            value=self.read()
        self.assertEqual(value['result']['status'],'parser_error')
        self.assertNotIn('DO_NOT_LOG',canonical(value))

    def test_wrong_native_source_and_wrapper_output_limit_are_rejected(self):
        def wrong(data,name):
            result=real_reader(data,name);result['source']['sha256']='0'*64;return result
        with mock.patch.object(self.api,'read_docx',side_effect=wrong):self.error('source_integrity_invalid')
        def overbudget(data,name):
            result=real_reader(data,name);result['blocks'][0]['text']='x'*(9*1024*1024);return result
        with mock.patch.object(self.api,'read_docx',side_effect=overbudget):self.error('input_limit')

    def test_recursive_manifest_is_an_integrity_failure(self):
        state=intake_status(self.creator,self.intake_id)
        depth=10000
        with self.creator.connection() as con:
            con.execute('UPDATE intake_revisions SET files_json=? WHERE intake_id=? AND revision=?',('['*depth+']'*depth,self.intake_id,state['revision']))
        args={'store':self.store,'intake_id':self.intake_id,'document_path':'request.docx',
              'expected_revision':state['revision'],'expected_sha256':state['files'][0]['sha256']}
        with self.assertRaises(self.api.IntakeDocxReferenceError) as caught:self.api.read_intake_docx_reference(**args)
        self.assertEqual(caught.exception.code,'intake_docx_reference_source_integrity_invalid')

    def mixed(self):
        from tests.test_intake_documents import pdf
        (self.bundle/'request.txt').write_bytes(b'product_type: sensor_node\npurpose: development\n')
        (self.bundle/'market.pdf').write_bytes(pdf(['market: EU']))
        self.stage(package(paragraph('model: DOCX-MODEL')))

    def test_false_docx_citations_rejected_while_text_pdf_complete(self):
        from labflow.intake_jobs import claim_job,complete_job
        from labflow.intake_worker import SyntheticTextProvider
        from labflow.intake_model_boundary import build_analysis_prompt
        self.mixed();before=self.rows();self.read();self.assertEqual(self.rows(),before)
        job=claim_job(self.store,'SYN-CLAIM',now=self.clock+3)
        doc=next(d for d in job['documents'] if d['path']=='request.docx')
        self.assertEqual((doc['format'],doc['parse_status'],doc['text']),('unsupported','requires_parser',None))
        context={name:job[name] for name in ['job_id','intake_id','revision','synthetic','documents','analysis_contract','instructions','analysis_context_id']}
        self.assertEqual(build_analysis_prompt(context,producer_name='SYN-MODEL')['kind'],'intake_model_prompt')
        analysis=SyntheticTextProvider().analyze(job)
        self.assertFalse(any(e['path']=='request.docx' for f in analysis['facts'] for e in f['evidence']))
        bad=copy.deepcopy(analysis)
        bad['facts'].append({'field':'model','value':'DOCX-MODEL','status':'explicit','evidence':[{
            'kind':'text_line','path':'request.docx','sha256':doc['sha256'],'line_start':1,'line_end':1,
            'quote':'model: DOCX-MODEL','role':'request'}]})
        with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],bad,now=self.clock+4)
        bad['facts'][-1]['evidence'][0].update(kind='pdf_page',page_number=1,extraction_id='0'*64,text_sha256='0'*64)
        with self.assertRaises(ValueError):complete_job(self.store,job['job_id'],job['token'],bad,now=self.clock+4)
        summary=complete_job(self.store,job['job_id'],job['token'],analysis,now=self.clock+4)
        self.assertEqual(summary['facts']['market']['value'],'EU')
        self.assertEqual(summary['unread_documents'],['request.docx'])
        self.assertTrue(any(q['key']=='unread_documents' for q in summary['questions']))
        self.assertNotIn('model',summary['facts'])

    def test_real_fixture_worker_keeps_docx_unread(self):
        from labflow.intake_worker import run_worker,SyntheticTextProvider
        self.mixed();value=self.read()
        self.assertEqual(value['result']['blocks'][0]['text'],'model: DOCX-MODEL')
        report=run_worker(self.store,SyntheticTextProvider(),worker_id='SYN-WORKER',max_jobs=1,
                          max_run_seconds=15,provider_timeout_seconds=5,lease_seconds=10)
        self.assertEqual(report['attempted_jobs'],1)
        self.assertEqual(report['results'][0]['status'],'completed')
        state=intake_status(self.creator,self.intake_id)
        self.assertEqual(state['analysis']['unread_documents'],['request.docx'])
        self.assertNotIn('model',state['analysis']['facts'])


class RetainedDocxReferenceTests(unittest.TestCase):
    stage = RegisteredDocxReferenceTests.stage
    arguments = RegisteredDocxReferenceTests.arguments
    read = RegisteredDocxReferenceTests.read
    rows = RegisteredDocxReferenceTests.rows
    blob = RegisteredDocxReferenceTests.blob
    mixed = RegisteredDocxReferenceTests.mixed
    set_manifest = RegisteredDocxReferenceTests.set_manifest

    def setUp(self):
        RegisteredDocxReferenceTests.setUp(self)
        from labflow import control_packet_prepare
        self.native = control_packet_prepare
        self.evidence = []

    def retain(self, **changes):
        function = getattr(self.api, 'retain_intake_docx_reference', None)
        self.assertTrue(callable(function), 'Actual retention API is not implemented')
        args = self.arguments(); args.update(changes)
        return function(**args)

    def rerror(self, suffix, **changes):
        with self.assertRaises(self.api.IntakeDocxReferenceError) as caught:
            self.retain(**changes)
        error = caught.exception
        self.assertEqual((error.code, str(error)), ('intake_docx_reference_' + suffix,) * 2)
        self.assertIsNone(error.__cause__)
        return error

    def candidate(self):
        reference = self.read()
        payload = canonical(reference).encode('utf-8')
        sha = hashlib.sha256(payload).hexdigest()
        return sha, payload, self.creator.blob_path(sha)

    def registered(self, sha):
        with self.creator.connection() as con:
            row = con.execute('SELECT bytes,kind,synthetic FROM blobs WHERE sha256=?', (sha,)).fetchone()
        return None if row is None else tuple(row)

    def flags(self, values):
        args = self.arguments()
        with self.creator.connection() as con:
            con.execute('UPDATE intake_sources SET synthetic=? WHERE source_id=?', (values[0], 'SYN-DOCX'))
            con.execute('UPDATE intake_revisions SET synthetic=? WHERE intake_id=? AND revision=?',
                        (values[1], self.intake_id, args['expected_revision']))
            con.execute('UPDATE blobs SET synthetic=? WHERE sha256=?', (values[2], args['expected_sha256']))

    @contextmanager
    def before_connection(self, number, action):
        original = self.store.connection; calls = []
        @contextmanager
        def connection():
            calls.append(1)
            if len(calls) == number:
                action()
            with original() as con:
                yield con
        with mock.patch.object(self.store, 'connection', connection):
            yield calls

    def test_retention_exact_signature_does_not_accept_DTO_ID_or_limits(self):
        self.assertTrue(callable(getattr(self.api, 'retain_intake_docx_reference', None)))
        signature = inspect.signature(self.api.retain_intake_docx_reference)
        self.assertEqual(list(signature.parameters), ['store', 'intake_id', 'document_path',
                                                     'expected_revision', 'expected_sha256'])
        for name in ('expected_revision', 'expected_sha256'):
            self.assertIs(signature.parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)

    def test_retention_actual_payload_registration_native_once_and_borrowed_lifetime(self):
        self.stage(package(paragraph('first') + table(['<w:tr>' + cell(blocks=table([
            '<w:tr>' + cell('nested') + '</w:tr>'], 1)) + '</w:tr>'], 1) + paragraph('last')))
        sha, payload, path = self.candidate(); before = self.rows()
        original = self.store.connection; active, connections, queries, results = [], [], [], []
        handles = tuple(self.store._existing_binding.handles)
        @contextmanager
        def connection():
            with original() as con:
                connections.append(con); active.append(con); con.set_trace_callback(queries.append)
                try:
                    yield con
                finally:
                    active.remove(con)
        def parse(data, name):
            self.assertEqual(active, [])
            result = real_reader(data, name); results.append(copy.deepcopy(result)); return result
        with mock.patch.object(self.store, 'connection', connection), \
                mock.patch.object(self.store, 'close', wraps=self.store.close) as closed, \
                mock.patch.object(self.store, 'write_blob', side_effect=AssertionError('unbounded writer')), \
                mock.patch.object(self.store, 'verify_blob', side_effect=AssertionError('unbounded verifier')), \
                mock.patch.object(self.api, 'read_docx', side_effect=parse):
            receipt = self.retain()
        closed.assert_not_called()
        self.assertEqual(set(receipt), {'schema_version', 'kind', 'artifact_id', 'artifact_bytes', 'synthetic', 'reference'})
        self.assertEqual((receipt['schema_version'], receipt['kind']), (1, 'intake_docx_reference_retained'))
        self.assertEqual((receipt['artifact_id'], receipt['artifact_bytes'], receipt['synthetic']), (sha, len(payload), True))
        self.assertIs(type(receipt['artifact_bytes']), int); self.assertIs(type(receipt['synthetic']), bool)
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt['artifact_id'])
        self.assertEqual(receipt['reference'], json.loads(payload))
        self.assertEqual(receipt['reference']['result'], results[0]); self.assertEqual(len(results), 1)
        self.assertEqual(self.registered(sha), (len(payload), 'intake_docx_reference', 1))
        after = self.rows(); before.pop('blobs'); after.pop('blobs'); self.assertEqual(before, after)
        self.assertEqual(tuple(self.store._existing_binding.handles), handles)
        self.assertEqual(self.store._existing_binding.active, 0)
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                con.execute('SELECT 1')
        dml = [q for q in queries if q.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'))]
        self.assertEqual(len(dml), 1); self.assertTrue(dml[0].startswith('INSERT INTO blobs'))
        self.evidence.append({'observed_artifact_id': receipt['artifact_id'], 'actual_bytes': len(payload),
                              'native_calls': len(results), 'SQL_closed': len(connections),
                              'active_after': 0, 'caller_Store_close_calls': 0})

    def test_retention_native_status_and_locator_are_not_upgraded(self):
        cases = [(package(paragraph('known')), 'ok', True), (package(), 'empty', True),
                 (package(paragraph('known') + '<w:unknown/>'), 'partial', False),
                 (bytes.fromhex('d0cf11e0a1b11ae1'), 'unsupported_format', False),
                 (flagged(package(), flag=1), 'encrypted', False), (b'bad', 'malformed_docx', False),
                 (package(paragraph('x' * 1000001)), 'limit_exceeded', False)]
        for data, status, complete in cases:
            with self.subTest(status=status):
                self.stage(data); expected = self.read(); receipt = self.retain()
                self.assertEqual(receipt['reference'], expected)
                result = receipt['reference']['result']
                self.assertEqual((result['status'], result['complete']), (status, complete))
                self.assertEqual(result['scope']['page_numbers'], 'unavailable')
                self.assertEqual(len(result), 11)
                self.evidence.append({'native_status': status, 'complete': complete,
                                      'observed_artifact_id': receipt['artifact_id']})

    def test_retention_native_parser_failure_DTO_is_retained(self):
        with mock.patch('labflow.reference_docx.zipfile.ZipFile', side_effect=RuntimeError('PRIVATE')):
            receipt = self.retain()
        self.assertEqual(receipt['reference']['result']['status'], 'parser_error')
        self.assertFalse(receipt['reference']['result']['complete'])
        self.assertEqual(json.loads(self.creator.blob_path(receipt['artifact_id']).read_bytes()), receipt['reference'])
        self.assertNotIn('PRIVATE', canonical(receipt))

    def test_retention_reuses_only_actual_valid_registered_bytes(self):
        first = self.retain(); path = self.creator.blob_path(first['artifact_id'])
        before = path.stat()
        with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('overwrite')):
            second = self.retain()
        self.assertEqual(first, second)
        after = path.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns, before.st_size),
                         (after.st_ino, after.st_mtime_ns, after.st_size))

    def test_retention_valid_orphan_is_read_back_then_registered(self):
        sha, payload, path = self.candidate(); path.write_bytes(payload)
        self.assertIsNone(self.registered(sha))
        with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('orphan overwrite')):
            receipt = self.retain()
        self.assertEqual(receipt['artifact_id'], sha)
        self.assertEqual(self.registered(sha), (len(payload), 'intake_docx_reference', 1))

    def test_retention_registered_missing_file_is_not_recreated(self):
        receipt = self.retain(); path = self.creator.blob_path(receipt['artifact_id']); path.unlink()
        with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('repair')):
            self.rerror('source_integrity_invalid')
        self.assertFalse(path.exists()); self.assertIsNotNone(self.registered(receipt['artifact_id']))

    def test_retention_invalid_registered_bytes_kind_flags_are_not_repaired(self):
        receipt = self.retain(); sha = receipt['artifact_id']; original = self.registered(sha)
        for field, value in [('bytes', original[0] + 1), ('kind', 'raw'), ('synthetic', 2)]:
            with self.subTest(field=field):
                with self.creator.connection() as con:
                    con.execute('UPDATE blobs SET ' + field + '=? WHERE sha256=?', (value, sha))
                with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('repair')):
                    self.rerror('source_integrity_invalid')
                with self.creator.connection() as con:
                    self.assertEqual(con.execute('SELECT ' + field + ' FROM blobs WHERE sha256=?', (sha,)).fetchone()[0], value)
                    con.execute('UPDATE blobs SET bytes=?,kind=?,synthetic=? WHERE sha256=?', (*original, sha))

    def test_retention_source_provenance_OR_and_registered_MAX(self):
        for number in range(8):
            values = tuple((number >> bit) & 1 for bit in range(3))
            with self.subTest(flags=values):
                self.stage(package(paragraph('flags ' + str(number)))); self.flags(values)
                receipt = self.retain()
                self.assertIs(receipt['synthetic'], bool(any(values)))
                self.assertEqual(self.registered(receipt['artifact_id'])[2], int(any(values)))
        self.flags((0, 0, 0))
        self.assertTrue(self.retain()['synthetic'])

    def test_retention_invalid_source_provenance_is_not_false(self):
        for values in [(2, 0, 0), (0, 'bad', 0), (0, 0, -1)]:
            with self.subTest(flags=values):
                self.flags(values)
                with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('write')):
                    self.rerror('source_integrity_invalid')

    def test_retention_wrong_existing_bytes_and_large_file_are_bounded_failures(self):
        sha, payload, path = self.candidate()
        for size, content in [(len(payload), b'x' * len(payload)), (17 * 1024 * 1024, None)]:
            with self.subTest(size=size):
                with path.open('wb') as stream:
                    if content is None: stream.truncate(size)
                    else: stream.write(content)
                with mock.patch.object(self.store, 'verify_blob', side_effect=AssertionError('unbounded')):
                    self.rerror('source_integrity_invalid')
                self.assertEqual(path.stat().st_size, size); self.assertIsNone(self.registered(sha))

    def test_retention_real_exclusive_create_collision_fails_then_explicit_retry_adopts(self):
        sha, payload, path = self.candidate(); backend = self.store._existing_binding.backend
        create = backend.create_file
        def race(target):
            self.assertEqual(target, path); target.write_bytes(payload)
            return create(target)
        with mock.patch.object(backend, 'create_file', side_effect=race):
            self.rerror('storage_error')
        self.assertEqual(path.read_bytes(), payload); self.assertIsNone(self.registered(sha))
        self.assertEqual(self.retain()['artifact_id'], sha)

    def test_retention_revision_change_before_writer_returns_no_receipt(self):
        sha, _, path = self.candidate()
        with self.before_connection(3, lambda: self.stage(package(paragraph('new revision')))):
            self.rerror('revision_changed')
        self.assertFalse(path.exists()); self.assertIsNone(self.registered(sha))

    def test_retention_provenance_change_after_commit_preserves_real_failed_artifact(self):
        sha, payload, path = self.candidate()
        with self.before_connection(4, lambda: self.flags((0, 1, 1))):
            self.rerror('revision_changed')
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(self.registered(sha), (len(payload), 'intake_docx_reference', 1))
        self.evidence.append({'receipt_returned': False, 'post_commit_file_bytes': len(payload),
                              'registered': True, 'failure_code': 'revision_changed'})

    def test_retention_input_and_store_errors_precede_native_or_writes(self):
        for changes, code in [({'expected_revision': True}, 'invalid_argument'),
                              ({'expected_sha256': 'A' * 64}, 'invalid_argument'),
                              ({'document_path': '../x.docx'}, 'invalid_argument'),
                              ({'store': self.creator}, 'store_invalid'),
                              ({'intake_id': 'MISSING'}, 'intake_not_found')]:
            with self.subTest(code=code), mock.patch.object(self.api, 'read_docx', side_effect=AssertionError('native')), \
                    mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('write')):
                self.rerror(code, **changes)

    def test_retention_read_api_remains_read_only_after_retention(self):
        receipt = self.retain(); before = self.rows()
        self.assertEqual(self.read(), receipt['reference'])
        self.assertEqual(self.rows(), before)

    def test_retention_fixed_error_has_no_active_caller_exception_context(self):
        try:
            raise RuntimeError('PRIVATE caller ' + str(self.base))
        except RuntimeError:
            error = self.rerror('invalid_argument', expected_revision=False)
            self.assertIsNone(error.__context__)

    @contextmanager
    def pin_observation(self, *, close_errors=()):
        backend = self.store._existing_binding.backend
        relative, close = backend._relative, os.close
        state = {'opened': [], 'closed': [], 'active': set(), 'names': {}, 'maximum_active': 0}
        errors = iter(close_errors)
        def opened(parent, name, **options):
            fd = relative(parent, name, **options)
            if (len(name) == 64 and options.get('directory') is False
                    and options.get('share') == 1 and not options.get('create', False)):
                state['opened'].append(fd); state['active'].add(fd); state['names'][fd] = name
                state['maximum_active'] = max(state['maximum_active'], len(state['active']))
            return fd
        def closed(fd):
            tracked = fd in state['active']
            close(fd)
            if tracked:
                state['active'].remove(fd); state['closed'].append(fd)
                error = next(errors, None)
                if error is not None:
                    raise error
        with mock.patch.object(backend, '_relative', side_effect=opened), mock.patch('os.close', side_effect=closed):
            yield state

    def assert_pins_closed(self, state, count=2):
        self.assertEqual(len(state['opened']), count)
        self.assertEqual(len(state['closed']), count)
        self.assertEqual(state['active'], set())
        self.assertEqual(self.store._existing_binding.active, 0)
        for fd in state['opened']:
            with self.assertRaises(OSError): os.fstat(fd)

    def test_retention_resources_real_write_delete_pins_then_positive_controls(self):
        source = self.blob(); register = self.store.register_blob; blocked = []
        held = tuple(self.store._existing_binding.handles)
        with self.pin_observation() as state:
            def registering(con, sha, size, kind, synthetic):
                self.assertEqual(len(state['active']), 2)
                for path in (source, self.store.blob_path(sha)):
                    with self.assertRaises(PermissionError):
                        with path.open('r+b'): pass
                    with self.assertRaises(OSError): path.rename(path.with_name(path.name + '.move'))
                    blocked.append(path)
                return register(con, sha, size, kind, synthetic)
            with mock.patch.object(self.store, 'register_blob', side_effect=registering), \
                    mock.patch.object(self.store, 'close', wraps=self.store.close) as closed:
                receipt = self.retain()
            closed.assert_not_called()
        self.assert_pins_closed(state)
        self.assertEqual(tuple(self.store._existing_binding.handles), held)
        for path in blocked:
            with path.open('r+b'): pass
            moved = path.with_name(path.name + '.move'); path.rename(moved); moved.rename(path)
        self.store.close()
        for fd in held:
            with self.assertRaises(OSError): os.fstat(fd)
        self.evidence.append({'observed_artifact_id': receipt['artifact_id'], 'write_blocks': 2,
                              'rename_blocks': 2, 'positive_write_controls': 2, 'positive_rename_controls': 2,
                              'API_owned_pins_closed': 2, 'caller_native_pins_closed': len(held)})

    def test_retention_resources_source_and_artifact_full_reads_are_chunked(self):
        self.stage(package(paragraph('x' * 200000)))
        read = os.read; observed = []
        with self.pin_observation() as state:
            def reading(fd, amount):
                data = read(fd, amount)
                if fd in state['active']: observed.append((state['names'][fd], amount, len(data)))
                return data
            with mock.patch('os.read', side_effect=reading): receipt = self.retain()
        self.assert_pins_closed(state)
        self.assertTrue(observed); self.assertTrue(all(0 < amount <= 65536 for _, amount, _ in observed))
        source_sha = receipt['reference']['binding']['document']['sha256']
        totals = {name: sum(size for key, _, size in observed if key == name) for name in {v[0] for v in observed}}
        self.assertEqual(totals[source_sha], 2 * len(self.payload))
        self.assertEqual(totals[receipt['artifact_id']], 2 * receipt['artifact_bytes'])
        self.evidence.append({'source_pin_read_bytes': totals[source_sha],
                              'artifact_pin_read_bytes': totals[receipt['artifact_id']],
                              'maximum_chunk_request': max(v[1] for v in observed), 'closed_pins': 2})

    def test_retention_edges_payload_and_receipt_budget_exact_and_plus_one(self):
        self.flags((0, 0, 0)); first = self.retain()
        payload_size = len(canonical(first['reference']).encode('utf-8'))
        receipt_size = len(canonical(first).encode('utf-8'))
        for constant, size in [('_OUTPUT_BYTES', payload_size), ('_RECEIPT_BYTES', receipt_size)]:
            with self.subTest(constant=constant):
                with mock.patch.object(self.api, constant, size): self.assertEqual(self.retain(), first)
                with mock.patch.object(self.api, constant, size - 1), \
                        mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('write')), \
                        mock.patch.object(self.store, 'register_blob', side_effect=AssertionError('register')):
                    self.rerror('input_limit')
        self.assertEqual((self.api._OUTPUT_BYTES, self.api._RECEIPT_BYTES), (9 * 1024 * 1024, 10 * 1024 * 1024))
        self.evidence.append({'real_P_bytes_for_budget_edge': payload_size,
                              'real_receipt_bytes_for_budget_edge': receipt_size,
                              'constant_lowering_is_admission_injection': True})

    def test_retention_edges_source_swap_between_read_and_pin_is_rejected(self):
        sha, _, path = self.candidate(); source = self.blob(); original = self.api._read_reference; swapped = []
        def handoff(*args, **kwargs):
            value = original(*args, **kwargs)
            replacement = source.with_name('same-source'); replacement.write_bytes(self.payload)
            os.replace(replacement, source); swapped.append(True)
            return value
        with mock.patch.object(self.api, '_read_reference', side_effect=handoff):
            self.rerror('source_integrity_invalid')
        self.assertEqual(swapped, [True]); self.assertFalse(path.exists()); self.assertIsNone(self.registered(sha))

    def test_retention_edges_same_bytes_swap_after_writer_close_is_rejected(self):
        sha, payload, path = self.candidate(); write = self.native._write_bytes; swaps = []
        def writing(*args, **kwargs):
            stamp = write(*args, **kwargs)
            replacement = path.with_name('same-artifact'); replacement.write_bytes(payload)
            os.replace(replacement, path); swaps.append(True)
            return stamp
        with mock.patch.object(self.native, '_write_bytes', side_effect=writing):
            self.rerror('source_integrity_invalid')
        self.assertEqual(swaps, [True]); self.assertEqual(path.read_bytes(), payload)
        self.assertIsNone(self.registered(sha))

    def test_retention_edges_same_bytes_existing_swap_before_native_open_is_rejected(self):
        sha, payload, path = self.candidate(); path.write_bytes(payload)
        backend = self.store._existing_binding.backend; relative = backend._relative; swaps = []
        def opening(parent, name, **options):
            if name == sha and options.get('share') == 1:
                replacement = path.with_name('same-artifact'); replacement.write_bytes(payload)
                os.replace(replacement, path); swaps.append(True)
            return relative(parent, name, **options)
        with mock.patch.object(backend, '_relative', side_effect=opening):
            self.rerror('source_integrity_invalid')
        self.assertEqual(swaps, [True]); self.assertEqual(path.read_bytes(), payload)
        self.assertIsNone(self.registered(sha))

    def test_retention_edges_hardlink_is_not_admitted_or_removed(self):
        sha, payload, path = self.candidate(); path.write_bytes(payload)
        alias = self.base / 'artifact-hardlink'; os.link(path, alias)
        self.rerror('source_integrity_invalid')
        self.assertEqual(path.read_bytes(), payload); self.assertEqual(alias.read_bytes(), payload)
        self.assertIsNone(self.registered(sha))

    def test_retention_edges_junction_is_not_followed(self):
        sha, _, path = self.candidate(); target = self.base / 'junction-target'; target.mkdir()
        self.assertTrue(target.resolve().is_relative_to(self.base))
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(path), str(target)], check=True, capture_output=True)
        self.rerror('source_integrity_invalid')
        self.assertTrue(path.exists()); self.assertEqual(list(target.iterdir()), [])
        self.assertIsNone(self.registered(sha))

    def test_retention_edges_other_manifest_entry_and_source_change_before_write(self):
        for change in ('manifest', 'source'):
            with self.subTest(change=change):
                self.stage(package(paragraph('change ' + change))); sha, _, path = self.candidate()
                def mutate():
                    if change == 'manifest':
                        state = intake_status(self.creator, self.intake_id)
                        self.set_manifest(state['files'] + [{'path': 'other.txt', 'sha256': '1' * 64, 'bytes': 0}])
                    else:
                        folder = self.base / 'other-source'; folder.mkdir()
                        register_source(self.creator, 'SYN-OTHER', folder, synthetic=False, settle_seconds=1)
                        with self.creator.connection() as con:
                            con.execute('UPDATE intakes SET source_id=? WHERE intake_id=?', ('SYN-OTHER', self.intake_id))
                with self.before_connection(3, mutate): self.rerror('revision_changed')
                self.assertFalse(path.exists()); self.assertIsNone(self.registered(sha))
                # Restore the synthetic source for the next independent mutation.
                with self.creator.connection() as con:
                    con.execute('UPDATE intakes SET source_id=? WHERE intake_id=?', ('SYN-DOCX', self.intake_id))

    def test_retention_edges_post_commit_registry_mismatch_is_preserved_failure(self):
        sha, payload, path = self.candidate()
        def mutate():
            with self.creator.connection() as con:
                con.execute('UPDATE blobs SET kind=? WHERE sha256=?', ('raw', sha))
        with self.before_connection(4, mutate): self.rerror('source_integrity_invalid')
        self.assertEqual(path.read_bytes(), payload); self.assertEqual(self.registered(sha)[1], 'raw')

    def test_retention_edges_artifact_read_corruption_is_not_a_prefix_hash_success(self):
        sha, _, path = self.candidate(); read = os.read; corrupted = []
        with self.pin_observation(close_errors=(GeneratorExit(), SystemExit())) as state:
            def reading(fd, amount):
                data = read(fd, amount)
                if state['names'].get(fd) == sha and data:
                    corrupted.append(True); return bytes([data[0] ^ 1]) + data[1:]
                return data
            with mock.patch('os.read', side_effect=reading): self.rerror('source_integrity_invalid')
        self.assertTrue(corrupted); self.assert_pins_closed(state)
        self.assertTrue(path.is_file()); self.assertIsNone(self.registered(sha))

    @contextmanager
    def SQL_fault(self, number, *, admission=None, commit=None, rollback=None, close=None):
        from labflow import store as store_module
        connect, schema = sqlite3.connect, store_module._existing_schema
        connections = []
        class FaultConnection(sqlite3.Connection):
            def rollback(self):
                super().rollback(); self.real_rollbacks += 1
                if self.ordinal == number and self.rollback_armed and rollback is not None:
                    raise rollback
            def commit(self):
                super().commit(); self.real_commits += 1
                if self.ordinal == number and commit is not None:
                    raise commit
            def close(self):
                self.close_attempts += 1
                super().close(); self.real_closed = True
                if self.ordinal == number and close is not None:
                    raise close
        def opened(*args, **kwargs):
            # Fixture arguments use the legacy Path connection. Count only the
            # official borrowed Store's URI connections for failure phases.
            if not kwargs.get('uri'):
                return connect(*args, **kwargs)
            con = connect(*args, factory=FaultConnection, **kwargs)
            con.ordinal = len(connections) + 1
            con.real_rollbacks = con.real_commits = con.close_attempts = 0
            con.real_closed = con.rollback_armed = False
            connections.append(con)
            return con
        def validated(con):
            schema(con)
            if con.ordinal == number and admission is not None:
                con.rollback_armed = True
                raise admission
        with mock.patch.object(sqlite3, 'connect', side_effect=opened), \
                mock.patch.object(store_module, '_existing_schema', side_effect=validated):
            yield connections

    def assert_SQL_closed(self, connections):
        self.assertTrue(connections)
        for con in connections:
            self.assertTrue(con.real_closed); self.assertEqual(con.close_attempts, 1)
            with self.assertRaises(sqlite3.ProgrammingError): con.execute('SELECT 1')
        self.assertEqual(self.store._existing_binding.active, 0)

    def test_retention_fault_actual_short_writes_complete_the_whole_payload(self):
        sha, payload, path = self.candidate(); backend = self.store._existing_binding.backend
        create, write = backend.create_file, os.write; writers, calls = [], []
        def created(target):
            fd = create(target); writers.append(fd); return fd
        def written(fd, data):
            if fd in writers:
                calls.append(1); return write(fd, data[:7])
            return write(fd, data)
        with mock.patch.object(backend, 'create_file', side_effect=created), mock.patch('os.write', side_effect=written):
            receipt = self.retain()
        self.assertEqual(receipt['artifact_id'], sha); self.assertEqual(path.read_bytes(), payload)
        self.assertGreater(len(calls), 1)
        for fd in writers:
            with self.assertRaises(OSError): os.fstat(fd)

    def test_retention_fault_zero_write_and_FileExistsError_never_become_success(self):
        for fault in ('zero_write', 'write_exists', 'fsync_exists', 'close_exists'):
            with self.subTest(fault=fault):
                self.stage(package(paragraph('fault ' + fault)))
                sha, payload, path = self.candidate(); backend = self.store._existing_binding.backend
                create, write, sync, close = backend.create_file, os.write, os.fsync, os.close
                writer = []; calls = []
                def created(target):
                    fd = create(target); writer.append(fd); return fd
                def written(fd, data):
                    if fd in writer and fault in {'zero_write', 'write_exists'}:
                        if not calls:
                            calls.append(1); return write(fd, data[:7])
                        if fault == 'zero_write': return 0
                        raise FileExistsError('PRIVATE write, not create collision')
                    return write(fd, data)
                def synced(fd):
                    sync(fd)
                    if fd in writer and fault == 'fsync_exists':
                        raise FileExistsError('PRIVATE fsync, not create collision')
                def closed(fd):
                    close(fd)
                    if fd in writer and fault == 'close_exists' and not calls:
                        calls.append(1); raise FileExistsError('PRIVATE close, not create collision')
                with mock.patch.object(backend, 'create_file', side_effect=created), \
                        mock.patch('os.write', side_effect=written), mock.patch('os.fsync', side_effect=synced), \
                        mock.patch('os.close', side_effect=closed):
                    self.rerror('storage_error')
                self.assertIsNone(self.registered(sha)); self.assertEqual(self.store._existing_binding.active, 0)
                raw = path.read_bytes()
                self.assertEqual(raw, payload[:7] if fault in {'zero_write', 'write_exists'} else payload)
                for fd in writer:
                    with self.assertRaises(OSError): os.fstat(fd)
                self.evidence.append({'fault': fault, 'receipt_returned': False, 'file_bytes': len(raw),
                                      'file_sha256': hashlib.sha256(raw).hexdigest(), 'registered': False,
                                      'known_writer_real_closed': True})
                if fault in {'zero_write', 'write_exists'}:
                    with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('repair')):
                        self.rerror('source_integrity_invalid')
                    self.assertEqual(path.read_bytes(), raw)
                else:
                    self.assertEqual(self.retain()['artifact_id'], sha)

    def test_retention_fault_first_native_interrupt_never_becomes_an_artifact(self):
        for kind in (MemoryError, KeyboardInterrupt, SystemExit, GeneratorExit):
            with self.subTest(kind=kind.__name__):
                sha, _, path = self.candidate(); first = kind('SYN first native interruption')
                with mock.patch.object(self.api, 'read_docx', side_effect=first), self.assertRaises(kind) as caught:
                    self.retain()
                self.assertIs(caught.exception, first)
                self.assertFalse(path.exists()); self.assertIsNone(self.registered(sha))
                self.assertEqual(self.store._existing_binding.active, 0)

    def test_retention_fault_first_selection_real_SQL_close_interrupt_skips_native(self):
        first = KeyboardInterrupt('SYN SQL close before native')
        held = tuple(self.store._existing_binding.handles)
        with self.SQL_fault(1, close=first) as connections, \
                mock.patch.object(self.api, 'read_docx', side_effect=AssertionError('native')):
            with self.assertRaises(KeyboardInterrupt) as caught: self.retain()
        self.assertIs(caught.exception, first); self.assertEqual(len(connections), 1)
        self.assert_SQL_closed(connections)
        self.store.close()
        for fd in held:
            with self.assertRaises(OSError): os.fstat(fd)
        self.evidence.append({'actual_SQL_close_completed': True, 'same_first_KI': True,
                              'native_calls': 0, 'active_after': 0, 'caller_native_pins_closed': len(held)})

    def test_retention_fault_body_control_exception_survives_rollback_SQL_and_file_close(self):
        for kind in (MemoryError, KeyboardInterrupt, SystemExit, GeneratorExit):
            with self.subTest(kind=kind.__name__):
                self.stage(package(paragraph('body interruption ' + kind.__name__)))
                sha, payload, path = self.candidate(); first = kind('SYN first body')
                register = self.store.register_blob
                def registering(con, *args):
                    register(con, *args); con.rollback_armed = True; raise first
                with self.pin_observation(close_errors=(OSError('PRIVATE later pin'), SystemExit())) as state, \
                        self.SQL_fault(3, rollback=SystemExit(), close=GeneratorExit()) as connections, \
                        mock.patch.object(self.store, 'register_blob', side_effect=registering):
                    with self.assertRaises(kind) as caught: self.retain()
                self.assertIs(caught.exception, first)
                self.assert_pins_closed(state); self.assert_SQL_closed(connections)
                self.assertEqual(path.read_bytes(), payload); self.assertIsNone(self.registered(sha))
                self.evidence.append({'first_type': kind.__name__, 'same_first_object': True,
                                      'SQL_connections_real_closed': len(connections), 'owned_pins_real_closed': 2,
                                      'registered_after_real_rollback': False, 'failure_file_bytes': len(payload)})

    def test_retention_fault_first_bridge_error_wins_over_later_base_cleanup(self):
        sha, payload, path = self.candidate(); register = self.store.register_blob
        def registering(con, candidate, size, kind, synthetic):
            register(con, candidate, size, kind, synthetic)
            con.execute('UPDATE blobs SET bytes=? WHERE sha256=?', (size + 1, candidate))
            con.rollback_armed = True
        with self.pin_observation(close_errors=(SystemExit(), GeneratorExit())) as state, \
                self.SQL_fault(3, rollback=KeyboardInterrupt(), close=SystemExit()) as connections, \
                mock.patch.object(self.store, 'register_blob', side_effect=registering):
            self.rerror('source_integrity_invalid')
        self.assert_pins_closed(state); self.assert_SQL_closed(connections)
        self.assertEqual(path.read_bytes(), payload); self.assertIsNone(self.registered(sha))

    def test_retention_fault_SQL_close_only_controls_keep_identity_after_commit(self):
        for kind in (KeyboardInterrupt, SystemExit, GeneratorExit):
            with self.subTest(kind=kind.__name__):
                self.stage(package(paragraph('SQL close ' + kind.__name__)))
                sha, payload, path = self.candidate(); first = kind('SYN first SQL close')
                with self.pin_observation(close_errors=(OSError('PRIVATE later pin'), SystemExit())) as state, \
                        self.SQL_fault(3, close=first) as connections:
                    with self.assertRaises(kind) as caught: self.retain()
                self.assertIs(caught.exception, first)
                self.assert_pins_closed(state); self.assert_SQL_closed(connections)
                self.assertEqual(path.read_bytes(), payload)
                self.assertEqual(self.registered(sha), (len(payload), 'intake_docx_reference', 1))
                self.evidence.append({'first_SQL_close_type': kind.__name__, 'same_first_object': True,
                                      'commit_completed': True, 'receipt_returned': False, 'registered': True})

    def test_retention_fault_parent_admission_and_commit_classification_is_not_raw_restored(self):
        for phase in ('admission', 'commit'):
            for kind, code in ((MemoryError, 'storage_error'), (sqlite3.DatabaseError, 'store_invalid')):
                with self.subTest(phase=phase, first=kind.__name__):
                    self.stage(package(paragraph(phase + kind.__name__)))
                    sha, payload, path = self.candidate(); first = kind('PRIVATE first parent error')
                    if kind is sqlite3.DatabaseError: first.sqlite_errorcode = sqlite3.SQLITE_CORRUPT
                    faults = {phase: first}
                    with self.pin_observation(close_errors=(SystemExit(), GeneratorExit())) as state, \
                            self.SQL_fault(3, rollback=KeyboardInterrupt(), close=SystemExit(), **faults) as connections:
                        self.rerror(code)
                    self.assert_pins_closed(state, 1 if phase == 'admission' else 2)
                    self.assert_SQL_closed(connections)
                    if phase == 'admission':
                        self.assertFalse(path.exists()); self.assertIsNone(self.registered(sha))
                    else:
                        self.assertEqual(path.read_bytes(), payload); self.assertIsNotNone(self.registered(sha))
                    self.evidence.append({'first_parent_phase': phase, 'first_type': kind.__name__,
                                          'existing_public_bridge_code': code, 'raw_exception_restored': False,
                                          'committed_row_present': phase == 'commit'})

    def test_retention_fault_ordinary_SQL_close_only_remains_storage_error(self):
        sha, payload, path = self.candidate()
        with self.pin_observation(close_errors=(GeneratorExit(), SystemExit())) as state, \
                self.SQL_fault(3, close=OSError('PRIVATE ordinary close')) as connections:
            self.rerror('storage_error')
        self.assert_pins_closed(state); self.assert_SQL_closed(connections)
        self.assertEqual(path.read_bytes(), payload); self.assertIsNotNone(self.registered(sha))

    def test_retention_fault_file_close_first_controls_survive_second_close(self):
        for kind in (KeyboardInterrupt, SystemExit, GeneratorExit):
            with self.subTest(kind=kind.__name__):
                self.stage(package(paragraph('pin close ' + kind.__name__)))
                sha, payload, path = self.candidate(); first = kind('SYN first pin close')
                with self.pin_observation(close_errors=(first, OSError('PRIVATE later source close'))) as state:
                    with self.assertRaises(kind) as caught: self.retain()
                self.assertIs(caught.exception, first); self.assert_pins_closed(state)
                self.assertEqual(path.read_bytes(), payload); self.assertIsNotNone(self.registered(sha))

    def test_retention_fault_output_memory_error_occurs_after_real_cleanup_and_commit(self):
        sha, payload, path = self.candidate(); encode = self.api.canonical
        first = MemoryError('SYN final serialization'); observed = []
        with self.pin_observation() as state:
            def encoded(value):
                if type(value) is dict and value.get('kind') == 'intake_docx_reference_retained' and 'artifact_id' in value:
                    self.assertEqual(state['active'], set()); observed.append(True); raise first
                return encode(value)
            with mock.patch.object(self.api, 'canonical', side_effect=encoded), self.assertRaises(MemoryError) as caught:
                self.retain()
        self.assertIs(caught.exception, first); self.assertEqual(observed, [True]); self.assert_pins_closed(state)
        self.assertEqual(path.read_bytes(), payload); self.assertIsNotNone(self.registered(sha))

    def test_retention_edges_missing_source_flag_row_is_not_false_provenance(self):
        sha, _, path = self.candidate()
        with self.creator.connection() as con:
            con.execute('PRAGMA foreign_keys=OFF')
            con.execute('DELETE FROM intake_sources WHERE source_id=?', ('SYN-DOCX',))
        with mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('write')):
            self.rerror('source_integrity_invalid')
        self.assertFalse(path.exists()); self.assertIsNone(self.registered(sha))

    def test_retention_edges_directory_is_not_an_artifact(self):
        sha, _, path = self.candidate(); path.mkdir()
        self.rerror('source_integrity_invalid')
        self.assertTrue(path.is_dir()); self.assertEqual(list(path.iterdir()), [])
        self.assertIsNone(self.registered(sha))

    def test_retention_edges_no_registry_write_has_no_receipt(self):
        sha, payload, path = self.candidate()
        with self.pin_observation() as state, mock.patch.object(self.store, 'register_blob', return_value=None):
            self.rerror('source_integrity_invalid')
        self.assert_pins_closed(state); self.assertEqual(path.read_bytes(), payload)
        self.assertIsNone(self.registered(sha))

    def test_retention_empty_upload_remains_unavailable_before_native_or_writes(self):
        self.stage(b''); before = self.rows()
        self.assertEqual(intake_status(self.creator, self.intake_id)['status'], 'upload_incomplete')
        with mock.patch.object(self.api, 'read_docx', side_effect=AssertionError('native')), \
                mock.patch.object(self.native, '_write_bytes', side_effect=AssertionError('write')):
            self.rerror('intake_unavailable')
        self.assertEqual(self.rows(), before)

    def test_retention_integration_mixed_claim_complete_rejects_DOCX_fact_citations(self):
        from labflow.intake_jobs import claim_job, complete_job
        from labflow.intake_worker import SyntheticTextProvider
        from labflow.intake_model_boundary import build_analysis_prompt
        self.mixed(); receipt = self.retain()
        self.assertEqual(receipt['reference']['result']['blocks'][0]['text'], 'model: DOCX-MODEL')
        job = claim_job(self.store, 'SYN-RETAIN-CLAIM', now=self.clock + 3)
        doc = next(d for d in job['documents'] if d['path'] == 'request.docx')
        self.assertEqual((doc['format'], doc['parse_status'], doc['text']), ('unsupported', 'requires_parser', None))
        context = {name: job[name] for name in ['job_id', 'intake_id', 'revision', 'synthetic', 'documents',
                                               'analysis_contract', 'instructions', 'analysis_context_id']}
        self.assertEqual(build_analysis_prompt(context, producer_name='SYN-MODEL')['kind'], 'intake_model_prompt')
        analysis = SyntheticTextProvider().analyze(job)
        self.assertFalse(any(e['path'] == 'request.docx' for f in analysis['facts'] for e in f['evidence']))
        bad = copy.deepcopy(analysis)
        bad['facts'].append({'field': 'model', 'value': 'DOCX-MODEL', 'status': 'explicit', 'evidence': [{
            'kind': 'text_line', 'path': doc['path'], 'sha256': doc['sha256'], 'line_start': 1, 'line_end': 1,
            'quote': 'model: DOCX-MODEL', 'role': 'request'}]})
        with self.assertRaises(ValueError): complete_job(self.store, job['job_id'], job['token'], bad, now=self.clock + 4)
        bad['facts'][-1]['evidence'][0].update(kind='pdf_page', page_number=1,
            extraction_id=receipt['artifact_id'], text_sha256=receipt['reference']['result']['text_sha256'])
        with self.assertRaises(ValueError): complete_job(self.store, job['job_id'], job['token'], bad, now=self.clock + 4)
        summary = complete_job(self.store, job['job_id'], job['token'], analysis, now=self.clock + 4)
        self.assertEqual(summary['facts']['market']['value'], 'EU'); self.assertNotIn('model', summary['facts'])
        self.assertEqual(summary['unread_documents'], ['request.docx'])
        self.assertTrue(any(q['key'] == 'unread_documents' for q in summary['questions']))
        self.assertIsNotNone(self.registered(receipt['artifact_id']))

    def test_retention_integration_real_fixture_worker_keeps_DOCX_unread(self):
        from labflow.intake_worker import run_worker, SyntheticTextProvider
        self.mixed(); self.retain()
        report = run_worker(self.store, SyntheticTextProvider(), worker_id='SYN-RETAIN-WORKER', max_jobs=1,
                            max_run_seconds=15, provider_timeout_seconds=5, lease_seconds=10)
        self.assertEqual(report['attempted_jobs'], 1); self.assertEqual(report['results'][0]['status'], 'completed')
        state = intake_status(self.creator, self.intake_id)
        self.assertEqual(state['analysis']['unread_documents'], ['request.docx'])
        self.assertTrue(any(q['key'] == 'unread_documents' for q in state['analysis']['questions']))
        self.assertNotIn('model', state['analysis']['facts'])

    def test_retention_limit_ineffective_close_is_failure_and_not_claimed_recovered(self):
        sha, payload, path = self.candidate(); refused = []
        try:
            with self.pin_observation() as state:
                close = os.close
                def ineffective(fd):
                    if fd in state['active'] and state['names'][fd] == sha and not refused:
                        refused.append(fd)
                        raise OSError('SYN close deliberately not performed')
                    return close(fd)
                with mock.patch('os.close', side_effect=ineffective): self.rerror('storage_error')
            self.assertEqual(len(refused), 1)
            self.assertEqual(len(state['closed']), 1)
            self.assertEqual(state['active'], set(refused))
            self.assertEqual(self.store._existing_binding.active, 0)
            self.assertEqual(os.fstat(refused[0]).st_size, len(payload))
            self.assertEqual(path.read_bytes(), payload); self.assertIsNotNone(self.registered(sha))
            self.store.close()
            self.assertEqual(os.fstat(refused[0]).st_size, len(payload))
            with self.assertRaises(OSError): path.rename(path.with_name(path.name + '.still-pinned'))
            self.evidence.append({'receipt_returned': False, 'API_error': 'storage_error',
                                  'deliberately_ineffective_close_attempts': 1, 'API_owned_fd_left_open': 1,
                                  'caller_Store_close_does_not_own_this_fd': True,
                                  'registered_commit_preserved': True,
                                  'fixture_known_fd_cleanup_after_observation_only': True})
        finally:
            # This is test cleanup of the one known leaked descriptor, not a
            # product retry or proof of universal ineffective-close recovery.
            for fd in refused: os.close(fd)
        for fd in refused:
            with self.assertRaises(OSError): os.fstat(fd)


class ObservedRetainedDocxTests(unittest.TestCase):
    stage = RegisteredDocxReferenceTests.stage
    arguments = RegisteredDocxReferenceTests.arguments
    rows = RegisteredDocxReferenceTests.rows
    blob = RegisteredDocxReferenceTests.blob
    set_manifest = RegisteredDocxReferenceTests.set_manifest
    retain = RetainedDocxReferenceTests.retain
    registered = RetainedDocxReferenceTests.registered
    before_connection = RetainedDocxReferenceTests.before_connection
    pin_observation = RetainedDocxReferenceTests.pin_observation
    assert_pins_closed = RetainedDocxReferenceTests.assert_pins_closed
    SQL_fault = RetainedDocxReferenceTests.SQL_fault
    assert_SQL_closed = RetainedDocxReferenceTests.assert_SQL_closed
    flags = RetainedDocxReferenceTests.flags

    def setUp(self):
        self.api = __import__('labflow.intake_docx_reference', fromlist=['read_retained_intake_docx_reference'])
        from labflow import control_packet_prepare
        self.native = control_packet_prepare
        parent = Path(__file__).resolve().parents[1] / '.local'
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='docx-observe-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.creator = Store(self.base / 'state'); self.addCleanup(self.creator.close)
        self.inbox = self.base / 'inbox'; self.bundle = self.inbox / 'one'; self.bundle.mkdir(parents=True)
        register_source(self.creator, 'SYN-DOCX', self.inbox, synthetic=True, settle_seconds=1)
        self.clock = 300
        self.stage(package(paragraph('owner read observation 20261025') + table([
            '<w:tr>' + cell('cell retained for observation') + '</w:tr>'], 1)))
        self.store = Store.open_existing(str(self.creator.root)); self.addCleanup(self.store.close)
        self.evidence = []
        self.receipt = self.retain()
        self.expected_binding = copy.deepcopy(self.receipt['reference']['binding'])
        self.artifact = self.store.blob_path(self.receipt['artifact_id'])
        if hasattr(self, 'proof_dir'):
            self.proof_dir.mkdir(parents=True, exist_ok=True)
            (self.proof_dir / 'original.docx').write_bytes(self.payload)
            (self.proof_dir / 'retained.json').write_bytes(self.artifact.read_bytes())
            (self.proof_dir / 'receipt.json').write_text(canonical(self.receipt), encoding='utf-8')

    def observe(self, **changes):
        function = getattr(self.api, 'read_retained_intake_docx_reference', None)
        self.assertTrue(callable(function), 'Readonly retained observation API is not implemented')
        args = dict(store=self.store, artifact_id=self.receipt['artifact_id'],
                    expected_binding=copy.deepcopy(self.expected_binding))
        args.update(changes)
        return function(**args)

    def oerror(self, suffix, **changes):
        with self.assertRaises(self.api.IntakeDocxReferenceError) as caught:
            self.observe(**changes)
        error = caught.exception
        self.assertEqual((error.code, str(error), error.args),
                         ('intake_docx_reference_' + suffix,) * 2 + (('intake_docx_reference_' + suffix,),))
        self.assertIsNone(error.__cause__); self.assertIsNone(error.__context__)
        return error

    def test_actual_retention_is_observed_without_native_or_writes(self):
        before = self.rows(); blobs = self.creator.root / 'blobs'
        files = {p.name: p.read_bytes() for p in blobs.iterdir() if p.is_file()}
        connections, queries = [], []
        original = self.store.connection
        @contextmanager
        def connection():
            with original() as con:
                connections.append(con); con.set_trace_callback(queries.append)
                yield con
        with mock.patch.object(self.store, 'connection', connection), \
                mock.patch.object(self.api, 'read_docx', side_effect=AssertionError('unexpected native execution')), \
                mock.patch.object(self.store, 'register_blob', side_effect=AssertionError('unexpected write')), \
                mock.patch.object(self.store, 'close', wraps=self.store.close) as closed:
            result = self.observe()
        self.assertEqual(result, self.receipt)
        self.assertEqual(self.rows(), before)
        self.assertEqual({p.name: p.read_bytes() for p in blobs.iterdir() if p.is_file()}, files)
        self.assertIn(self.receipt['artifact_id'], files)
        self.assertEqual(len(connections), 2); self.assertEqual(sum(q == 'BEGIN' for q in queries), 2)
        self.assertEqual(sum(q == 'PRAGMA query_only=ON' for q in queries), 2)
        self.assertFalse(any(q.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')) for q in queries))
        closed.assert_not_called()
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError): con.execute('SELECT 1')
        self.assertEqual(result['reference']['result']['blocks'][0]['text'], 'owner read observation 20261025')
        self.assertEqual(result['reference']['result']['blocks'][1]['rows'][0]['cells'][0]['blocks'][0]['text'],
                         'cell retained for observation')
        self.evidence.append({'artifact_id': result['artifact_id'], 'artifact_bytes': result['artifact_bytes'],
                              'fresh_read_transactions': 2, 'native_during_observation': 0, 'SQL_writes': 0})

    def test_observation_explicit_signature_and_invalid_selectors_precede_IO(self):
        function = getattr(self.api, 'read_retained_intake_docx_reference', None)
        self.assertTrue(callable(function))
        signature = inspect.signature(function)
        self.assertEqual(list(signature.parameters), ['store', 'artifact_id', 'expected_binding'])
        self.assertIs(signature.parameters['expected_binding'].kind, inspect.Parameter.KEYWORD_ONLY)
        cases = [{'artifact_id': v} for v in (None, True, '', 'A' * 64, '0' * 63, '../artifact')]
        for field, value in [('source_id', True), ('source_id', '../source'), ('intake_id', ''),
                             ('revision', True), ('revision', 0), ('revision', 1.0),
                             ('revision_fingerprint', 'A' * 64)]:
            cases.append({'expected_binding': {**self.expected_binding, field: value}})
        for field, value in [('path', '../x.docx'), ('path', 'x.txt'), ('path', 'x\ud800.docx'),
                             ('path', 'a' * 1020 + '.docx'), ('sha256', 'A' * 64),
                             ('bytes', True), ('bytes', -1), ('bytes', 16777217)]:
            binding = copy.deepcopy(self.expected_binding); binding['document'][field] = value
            cases.append({'expected_binding': binding})
        class DictSubclass(dict): pass
        cases.extend({'expected_binding': value} for value in (None, {},
            {**self.expected_binding, 'extra': 1}, DictSubclass(self.expected_binding)))
        with mock.patch.object(self.store, 'connection', side_effect=AssertionError('unexpected I/O')):
            for change in cases:
                with self.subTest(change=repr(change)): self.oerror('invalid_argument', **change)

    def test_observation_detaches_binding_before_IO(self):
        binding = copy.deepcopy(self.expected_binding)
        def mutate():
            binding['source_id'] = 'CHANGED'; binding['document']['bytes'] = 0
        with self.before_connection(1, mutate): result = self.observe(expected_binding=binding)
        self.assertEqual(result['reference']['binding'], self.expected_binding)

    def test_observation_requires_official_borrowed_open_Store(self):
        for value in (self.creator, object()):
            with self.subTest(store=type(value).__name__): self.oerror('store_invalid', store=value)
        self.store.close(); self.oerror('store_invalid')

    def test_observation_missing_or_stale_current_binding(self):
        for field, value, code in [('intake_id', 'MISSING', 'intake_not_found'),
                                   ('revision', 99, 'revision_changed'), ('source_id', 'OTHER', 'revision_changed'),
                                   ('revision_fingerprint', '0' * 64, 'revision_changed')]:
            with self.subTest(field=field):
                self.oerror(code, expected_binding={**self.expected_binding, field: value})
        binding = copy.deepcopy(self.expected_binding); binding['document']['path'] = 'absent.docx'
        self.oerror('document_not_found', expected_binding=binding)

    def test_observation_upload_incomplete_is_unavailable(self):
        with self.creator.connection() as con:
            con.execute("UPDATE intakes SET status='upload_incomplete' WHERE intake_id=?", (self.intake_id,))
        self.oerror('intake_unavailable')

    def test_observation_requires_registered_row_and_never_adopts_orphan(self):
        with self.creator.connection() as con: con.execute('DELETE FROM blobs WHERE sha256=?', (self.receipt['artifact_id'],))
        before = self.rows(); self.oerror('source_integrity_invalid'); self.assertEqual(self.rows(), before)
        self.assertTrue(self.artifact.is_file())

    def test_observation_invalid_registry_metadata_is_not_repaired(self):
        for field, value in [('kind', 'other'), ('bytes', self.receipt['artifact_bytes'] + 1), ('synthetic', 2)]:
            with self.subTest(field=field):
                with self.creator.connection() as con:
                    con.execute('UPDATE blobs SET bytes=?,kind=?,synthetic=? WHERE sha256=?',
                                (self.receipt['artifact_bytes'], 'intake_docx_reference', 1, self.receipt['artifact_id']))
                    con.execute('UPDATE blobs SET ' + field + '=? WHERE sha256=?', (value, self.receipt['artifact_id']))
                before = self.rows(); self.oerror('source_integrity_invalid'); self.assertEqual(self.rows(), before)

    def test_observation_oversize_registry_is_rejected_before_file_open(self):
        with self.creator.connection() as con:
            con.execute('UPDATE blobs SET bytes=? WHERE sha256=?', (9437185, self.receipt['artifact_id']))
        with mock.patch.object(self.api, '_source', side_effect=AssertionError('opened before bound')):
            self.oerror('input_limit')

    def test_observation_missing_artifact_is_not_recreated(self):
        self.artifact.unlink(); before = self.rows(); self.oerror('source_integrity_invalid')
        self.assertEqual(self.rows(), before); self.assertFalse(self.artifact.exists())

    def test_observation_corrupt_or_truncated_or_extended_artifact_is_rejected(self):
        data = self.artifact.read_bytes()
        for changed in (b'x' * len(data), data[:-1], data + b'x'):
            with self.subTest(bytes=len(changed)):
                self.artifact.write_bytes(changed); self.oerror('source_integrity_invalid')

    def test_observation_current_original_hash_and_registered_bytes_are_required(self):
        self.blob().write_bytes(b'x' * len(self.payload)); self.oerror('source_integrity_invalid')

    def test_observation_hardlink_or_directory_artifact_is_rejected(self):
        link = self.artifact.with_name('SYN-link')
        os.link(self.artifact, link); self.oerror('source_integrity_invalid'); link.unlink()
        self.artifact.unlink(); self.artifact.mkdir(); self.oerror('source_integrity_invalid')

    def negative_artifact(self, payload):
        # Explicitly forged NEGATIVE input, never evidence of genuine success.
        sha = hashlib.sha256(payload).hexdigest(); self.creator.blob_path(sha).write_bytes(payload)
        with self.creator.connection() as con:
            self.creator.register_blob(con, sha, len(payload), 'intake_docx_reference', True)
        return sha

    def test_observation_strict_JSON_and_canonical_bytes(self):
        data = self.artifact.read_bytes()
        for payload in (b'\xef\xbb\xbf' + data, data + b'\n', b'{"x":1,"x":2}',
                        b'{"x":NaN}', b'\xff', b'[' * 1500 + b']' * 1500):
            with self.subTest(prefix=repr(payload[:30])):
                self.oerror('source_integrity_invalid', artifact_id=self.negative_artifact(payload))

    def test_observation_rejects_unsupported_envelope_or_native_types_and_binding(self):
        changes = [('schema_version', True), ('schema_version', 2), ('kind', 'other'), ('extra', 1)]
        for key, value in changes:
            reference = copy.deepcopy(self.receipt['reference']); reference[key] = value
            self.oerror('source_integrity_invalid', artifact_id=self.negative_artifact(canonical(reference).encode('utf-8')))
        for key, value in [('schema_version', True), ('complete', 1), ('status', ''), ('reader', []),
                           ('scope', {}), ('blocks', {}), ('limits', []), ('issues', {}),
                           ('statistics', []), ('text_sha256', 'A' * 64), ('extra', 1)]:
            with self.subTest(key=key):
                reference = copy.deepcopy(self.receipt['reference']); reference['result'][key] = value
                self.oerror('source_integrity_invalid', artifact_id=self.negative_artifact(canonical(reference).encode('utf-8')))
        for edit in ('binding', 'source', 'page'):
            reference = copy.deepcopy(self.receipt['reference'])
            if edit == 'binding': reference['binding']['source_id'] = 'OTHER'
            if edit == 'source': reference['result']['source']['size_bytes'] = True
            if edit == 'page': reference['result']['scope']['page_numbers'] = 'available'
            self.oerror('source_integrity_invalid', artifact_id=self.negative_artifact(canonical(reference).encode('utf-8')))

    def test_observation_provenance_OR_and_conservative_registered_flag(self):
        for values in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)):
            with self.subTest(flags=values):
                self.flags(values); result = self.observe(); self.assertIs(result['synthetic'], True)
        with self.creator.connection() as con:
            con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?', (self.receipt['artifact_id'],))
        self.oerror('source_integrity_invalid')
        self.flags((0, 0, 0)); self.assertIs(self.observe()['synthetic'], False)

    def test_observation_provenance_change_between_snapshots_is_stale(self):
        with self.before_connection(2, lambda: self.flags((1, 0, 1))):
            self.oerror('revision_changed')

    def test_observation_current_revision_change_between_snapshots_is_stale(self):
        def mutate():
            with self.creator.connection() as con:
                con.execute('UPDATE intakes SET revision=revision+1 WHERE intake_id=?', (self.intake_id,))
        with self.before_connection(2, mutate): self.oerror('revision_changed')

    def test_observation_registered_flag_change_between_snapshots_is_invalid(self):
        self.flags((0, 0, 0))
        def mutate():
            with self.creator.connection() as con:
                con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?', (self.receipt['artifact_id'],))
        with self.before_connection(2, mutate): self.oerror('source_integrity_invalid')

    def test_observation_native_partial_empty_and_failure_are_preserved(self):
        cases = [(package(), 'empty', True), (package(paragraph('read partial') + '<w:unknown/>'), 'partial', False),
                 (b'new owner malformed payload', 'malformed_docx', False),
                 (flagged(package(paragraph('encrypted read')), flag=1), 'encrypted', False)]
        for data, status, complete in cases:
            with self.subTest(status=status):
                self.stage(data); self.receipt = self.retain()
                self.expected_binding = copy.deepcopy(self.receipt['reference']['binding'])
                with mock.patch.object(self.api, 'read_docx', side_effect=AssertionError('reparse')): result = self.observe()
                self.assertEqual(result, self.receipt)
                self.assertEqual((result['reference']['result']['status'], result['reference']['result']['complete']), (status, complete))
                self.evidence.append({'genuine_retention_status': status, 'artifact_id': result['artifact_id'], 'observation_native_calls': 0})

    def test_observation_unknown_declarations_are_literal_not_native_attestation(self):
        def declared(data, name):
            result = real_reader(data, name)
            result['reader'] = {'name': 'SYN-unknown-reader', 'version': 'SYN-unknown'}
            result['status'] = 'SYN-unknown-status'; result['scope']['profile'] = 'SYN-unknown-profile'
            return result
        with mock.patch.object(self.api, 'read_docx', side_effect=declared): self.receipt = self.retain()
        self.expected_binding = copy.deepcopy(self.receipt['reference']['binding'])
        self.assertEqual(self.observe(), self.receipt)
        self.evidence.append({'declaration_injection_after_real_native_read': True, 'native_authenticity_proven': False})

    def test_observation_real_pins_block_writes_rename_and_close_then_positive_controls(self):
        verified = self.api._verified_read; blocked = []
        held = tuple(self.store._existing_binding.handles)
        def reading(binding, path, fd, stamp, sha, **options):
            if options.get('retain'):
                self.assertEqual(len(state['active']), 2)
                for candidate in (self.blob(), self.artifact):
                    with self.assertRaises(PermissionError):
                        with candidate.open('r+b'): pass
                    with self.assertRaises(OSError): candidate.rename(candidate.with_name(candidate.name + '.move'))
                    blocked.append(candidate)
            return verified(binding, path, fd, stamp, sha, **options)
        with self.pin_observation() as state, mock.patch.object(self.api, '_verified_read', side_effect=reading): self.observe()
        self.assert_pins_closed(state); self.assertEqual(tuple(self.store._existing_binding.handles), held)
        self.assertEqual(len(blocked), 2)
        for candidate in blocked:
            with candidate.open('r+b'): pass
            moved = candidate.with_name(candidate.name + '.move'); candidate.rename(moved); moved.rename(candidate)
        self.evidence.append({'blocked_write': 2, 'blocked_rename': 2, 'positive_write': 2, 'positive_rename': 2, 'own_closed': 2})

    def test_observation_source_artifact_each_two_full_chunked_reads_and_owned_close(self):
        self.stage(package(paragraph('owner chunk observation ' * 9000)))
        self.receipt = self.retain(); self.expected_binding = copy.deepcopy(self.receipt['reference']['binding'])
        self.artifact = self.store.blob_path(self.receipt['artifact_id'])
        if hasattr(self, 'proof_dir'):
            (self.proof_dir / 'chunk-original.docx').write_bytes(self.payload)
            (self.proof_dir / 'chunk-retained.json').write_bytes(self.artifact.read_bytes())
        read = os.read; observed = []
        with self.pin_observation() as state:
            def reading(fd, count):
                value = read(fd, count)
                if fd in state['active']: observed.append((state['names'][fd], count, len(value)))
                return value
            with mock.patch('os.read', side_effect=reading): self.observe()
        self.assert_pins_closed(state)
        totals = {sha: sum(size for key, _, size in observed if key == sha) for sha in state['names'].values()}
        self.assertEqual(totals, {self.expected_binding['document']['sha256']: 2 * len(self.payload),
                                  self.receipt['artifact_id']: 2 * self.receipt['artifact_bytes']})
        self.assertTrue(all(0 < count <= 65536 for _, count, _ in observed))
        self.assertGreater(self.receipt['artifact_bytes'], 65536)
        self.evidence.append({'full_read_totals': totals, 'own_pins_closed': 2, 'max_chunk': max(n for _, n, _ in observed)})

    def test_observation_artifact_and_receipt_budget_edges_cleanup(self):
        size = self.receipt['artifact_bytes']; receipt_size = len(canonical(self.receipt).encode('utf-8'))
        for cap, success in ((size, True), (size - 1, False)):
            with mock.patch.object(self.api, '_OUTPUT_BYTES', cap):
                if success: self.assertEqual(self.observe(), self.receipt)
                else: self.oerror('input_limit')
        for cap, success in ((receipt_size, True), (receipt_size - 1, False)):
            with self.pin_observation() as state, mock.patch.object(self.api, '_RECEIPT_BYTES', cap):
                if success: self.assertEqual(self.observe(), self.receipt)
                else: self.oerror('input_limit')
            self.assert_pins_closed(state)

    def test_observation_real_SQL_close_control_identity_first_and_second(self):
        for ordinal in (1, 2):
            for cls in (KeyboardInterrupt, SystemExit, GeneratorExit):
                marker = cls('PRIVATE-close')
                with self.subTest(ordinal=ordinal, cls=cls.__name__), self.SQL_fault(ordinal, close=marker) as cons:
                    with self.assertRaises(cls) as caught: self.observe()
                    self.assertIs(caught.exception, marker)
                self.assert_SQL_closed(cons)

    def test_observation_first_control_survives_actual_rollback_SQL_and_own_close(self):
        current = self.api._current; count = []
        primary = KeyboardInterrupt('PRIVATE-first')
        def checked(con, binding):
            count.append(1)
            if len(count) == 2:
                cons[-1].rollback_armed = True
                raise primary
            return current(con, binding)
        with self.SQL_fault(2, rollback=SystemExit('PRIVATE-rollback'), close=GeneratorExit('PRIVATE-close')) as cons, \
                self.pin_observation(close_errors=(SystemExit('PRIVATE-pin'), GeneratorExit('PRIVATE-pin2'))) as pins, \
                mock.patch.object(self.api, '_current', side_effect=checked):
            with self.assertRaises(KeyboardInterrupt) as caught: self.observe()
        self.assertIs(caught.exception, primary); self.assert_SQL_closed(cons); self.assert_pins_closed(pins)

    def test_observation_first_integrity_error_survives_later_pin_control(self):
        with self.pin_observation(close_errors=(KeyboardInterrupt('PRIVATE-later'),)) as state, \
                mock.patch.object(self.api, '_verified_read', side_effect=self.api.IntakeDocxReferenceError('source_integrity_invalid')):
            self.oerror('source_integrity_invalid')
        self.assert_pins_closed(state)

    def test_observation_first_surfaced_memory_control_is_same_object(self):
        primary = MemoryError('PRIVATE-first')
        with self.pin_observation(close_errors=(SystemExit('PRIVATE-later'),)) as state, \
                mock.patch.object(self.api, '_verified_read', side_effect=primary):
            with self.assertRaises(MemoryError) as caught: self.observe()
        self.assertIs(caught.exception, primary); self.assert_pins_closed(state)

    def test_observation_SQL_ordinary_close_and_active_context_are_fixed_errors(self):
        for ordinal in (1, 2):
            with self.SQL_fault(ordinal, close=OSError('PRIVATE-sql')) as cons:
                self.oerror('storage_error')
            self.assert_SQL_closed(cons)
        try: raise RuntimeError('PRIVATE-caller')
        except RuntimeError:
            self.oerror('invalid_argument', artifact_id='bad')

    def test_observation_actual_own_close_first_controls_keep_identity(self):
        for cls in (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
            marker = cls('PRIVATE-own-close')
            with self.subTest(cls=cls.__name__), self.pin_observation(close_errors=(marker, SystemExit('PRIVATE-second'))) as state:
                with self.assertRaises(cls) as caught: self.observe()
                self.assertIs(caught.exception, marker)
            self.assert_pins_closed(state)

    def test_observation_ineffective_close_leaves_known_fd_without_success(self):
        refused = []
        try:
            with self.pin_observation() as state:
                close = os.close
                def ineffective(fd):
                    if fd in state['active'] and state['names'][fd] == self.receipt['artifact_id'] and not refused:
                        refused.append(fd); raise OSError('PRIVATE-no-op-close')
                    return close(fd)
                with mock.patch('os.close', side_effect=ineffective): self.oerror('storage_error')
            self.assertEqual(state['active'], set(refused)); self.assertEqual(len(refused), 1)
            self.assertEqual(os.fstat(refused[0]).st_size, self.receipt['artifact_bytes'])
            self.store.close(); self.assertEqual(os.fstat(refused[0]).st_size, self.receipt['artifact_bytes'])
            self.evidence.append({'success': False, 'own_fd_remaining_after_ineffective_close': 1,
                                  'caller_close_does_not_own_fd': True, 'known_fd_test_cleanup_after_observation': True})
        finally:
            for fd in refused: os.close(fd)

    def test_observation_source_and_artifact_swap_before_open_are_rejected(self):
        backend = self.store._existing_binding.backend; opened = backend._relative
        for target in (self.blob(), self.artifact):
            with self.subTest(target=target.name):
                changed = []
                def swapping(parent, name, **options):
                    if name == target.name and options.get('share') == 1 and not changed:
                        data = target.read_bytes(); old = target.with_name(target.name + '.old')
                        target.rename(old); target.write_bytes(data); old.unlink(); changed.append(True)
                    return opened(parent, name, **options)
                with mock.patch.object(backend, '_relative', side_effect=swapping): self.oerror('source_integrity_invalid')
                self.assertEqual(changed, [True]); self.assertEqual(self.store._existing_binding.active, 0)

    def test_observation_registry_deleted_at_second_snapshot_is_not_cached(self):
        def removed():
            with self.creator.connection() as con:
                con.execute('DELETE FROM blobs WHERE sha256=?', (self.receipt['artifact_id'],))
        with self.before_connection(2, removed), self.pin_observation() as pins: self.oerror('source_integrity_invalid')
        self.assert_pins_closed(pins)

    def test_observation_other_manifest_entry_and_missing_provenance_are_checked(self):
        item = copy.deepcopy(self.expected_binding['document'])
        def changed(): self.set_manifest([item, {'path': 'other.txt', 'sha256': '0' * 64, 'bytes': 1}])
        with self.before_connection(2, changed): self.oerror('revision_changed')
        self.set_manifest([item])
        with self.creator.connection() as con:
            con.execute('PRAGMA foreign_keys=OFF')
            con.execute("DELETE FROM intake_sources WHERE source_id='SYN-DOCX'")
        self.oerror('source_integrity_invalid')

    def test_observation_real_read_error_and_short_EOF_never_return_prefix_success(self):
        read = os.read
        for corruption in ('error', 'short'):
            with self.subTest(corruption=corruption), self.pin_observation() as pins:
                def reading(fd, count):
                    if fd in pins['active'] and pins['names'][fd] == self.receipt['artifact_id']:
                        if corruption == 'error': raise OSError('PRIVATE-read')
                        return b''
                    return read(fd, count)
                with mock.patch('os.read', side_effect=reading): self.oerror('source_integrity_invalid')
            self.assert_pins_closed(pins)

    def test_observation_ordinary_own_close_failure_is_fixed_without_retry(self):
        with self.pin_observation(close_errors=(OSError('PRIVATE-own-close'),)) as pins: self.oerror('storage_error')
        self.assert_pins_closed(pins)

    def test_observation_parent_admission_classification_is_not_raw_restored(self):
        corrupt = sqlite3.DatabaseError('PRIVATE-corrupt'); corrupt.sqlite_errorcode = sqlite3.SQLITE_CORRUPT
        for marker, suffix in ((MemoryError('PRIVATE-parent'), 'storage_error'),
                               (sqlite3.DatabaseError('PRIVATE-parent'), 'storage_error'),
                               (corrupt, 'store_invalid')):
            with self.subTest(marker=type(marker).__name__), self.SQL_fault(1, admission=marker) as cons:
                self.oerror(suffix)
            self.assert_SQL_closed(cons)


if __name__=='__main__':
    unittest.main()
