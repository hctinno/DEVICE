"""Synthetic registered intake DOCX reference contracts; no original documents."""
import importlib.util
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
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


if __name__=='__main__':
    unittest.main()
