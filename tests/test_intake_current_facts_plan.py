"""Disposable authored PDF/DB fixtures; no original response, AI, HTTP or devices."""
import copy
from contextlib import ExitStack
import hashlib
import importlib
import importlib.util
import inspect
from io import BytesIO
import os
from pathlib import Path
import socket
import sqlite3
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from labflow.active_intake import register_source,scan_source
from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.intake_jobs import claim_job,complete_job
from labflow.intake_worker import SyntheticTextProvider
from labflow.store import Store,canonical
from labflow.ui_read_model import IntakeReadModel,ReadModelError


METHOD=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output')
RF='; '.join(['frequency_hz: 906000000 Hz','on_average_power: -13 dBm','bandwidth_hz: 125000 Hz',
              'duty_cycle: 40 %','modulation: LAB-FSK','crest_factor: 1 dB'])


def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def authored_pdf(text):
    from reportlab.pdfgen import canvas
    stream=BytesIO();document=canvas.Canvas(stream,invariant=1,pageCompression=0)
    cursor=document.beginText(36,760);cursor.setFont('Helvetica',6);cursor.setLeading(12)
    for line in text.splitlines():cursor.textLine(line)
    document.drawText(cursor);document.showPage();document.save()
    return stream.getvalue()


def completed_fixture(root,*,duty='40 %',kind='pdf',completed=True,synthetic=True):
    root=Path(root);inbox=root/'inbox';folder=inbox/'authored';folder.mkdir(parents=True)
    text='product_type: lab_receiver\nmarket: US\npurpose: development\nfeatures: '+RF.replace('40 %',duty)+'\n'
    if kind=='pdf':(folder/'request.pdf').write_bytes(authored_pdf(text))
    else:(folder/'request.txt').write_text(text,encoding='utf-8')
    store=Store(root/'state')
    register_source(store,'CURRENT-FACTS-AUTHORED',inbox,synthetic=synthetic,settle_seconds=.001)
    scan_source(store,'CURRENT-FACTS-AUTHORED',now=100)
    intake_id=scan_source(store,'CURRENT-FACTS-AUTHORED',now=100.01)['accepted'][0]['intake_id']
    job=claim_job(store,'current-facts-fixture',now=101)
    context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
    analysis=SyntheticTextProvider().analyze({**context,'synthetic':True})
    if not synthetic:analysis['producer']=dict(kind='manual',name='authored-negative-provenance-case')
    if completed:complete_job(store,job['job_id'],job['token'],analysis,now=102)
    return dict(store=store,intake_id=intake_id,context=context,analysis=analysis,inbox=inbox,folder=folder)


class CurrentFactsPlanTests(unittest.TestCase):
    maxDiff=None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='current-facts-plan-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def api(self):
        name='labflow.intake_current_facts_plan'
        self.assertIsNotNone(importlib.util.find_spec(name),'assigned current facts read API is absent')
        return importlib.import_module(name).read_current_conducted_plan_from_facts

    def fixture(self,**kwargs):return completed_fixture(self.root/'authored',**kwargs)

    def files(self,fixture):
        result={}
        for path in fixture['store'].root.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:
                    raw=stream.read();metadata=os.fstat(stream.fileno())
                result[path.relative_to(fixture['store'].root).as_posix()]=(
                    hashlib.sha256(raw).hexdigest(),metadata.st_size,metadata.st_ino,metadata.st_nlink,
                    metadata.st_mtime_ns,metadata.st_ctime_ns,getattr(metadata,'st_file_attributes',None))
        return result

    def test_genuine_completed_pdf_automatically_builds_exact_facts_wrapper_without_manual_settings(self):
        api=self.api();fixture=self.fixture();method=copy.deepcopy(METHOD)
        result=api(fixture['store'].root,fixture['intake_id'],method=method)
        self.assertEqual(set(result),{'context','analysis','facts_plan'})
        context,analysis,wrapper=(result[key] for key in ('context','analysis','facts_plan'))
        self.assertEqual(analysis,fixture['analysis']);self.assertEqual(analysis['schema_version'],2)
        self.assertEqual(context['documents'][0]['format'],'pdf')
        self.assertNotEqual(context['instructions'],fixture['context']['instructions'])
        self.assertNotEqual(digest(context),digest(fixture['context']))
        self.assertEqual(context['analysis_context_id'],fixture['context']['analysis_context_id'])
        expected=build_conducted_plan_from_intake_facts(context,analysis,expected_revision=context['revision'],
            expected_context_sha256=digest(context),method=METHOD)
        self.assertEqual(wrapper,expected)
        self.assertEqual(wrapper['status'],'ready_for_simulation')
        self.assertEqual(wrapper['plan_input']['binding']['context_sha256'],digest(context))
        self.assertEqual(wrapper['plan_input']['plan']['source_settings'],dict(frequency_hz=906000000,
            power_dbm=-13,bandwidth_hz=125000,duty_cycle=.4,modulation='LAB-FSK',crest_factor_db=1))
        self.assertIs(wrapper['plan_input']['verification']['execution_authority'],False)
        self.assertIsNone(wrapper['plan_input']['plan']['numeric_limit_dbm'])
        self.assertIsNone(wrapper['plan_input']['plan']['uncertainty_db'])
        self.assertEqual(method,METHOD)

    def test_missing_workspace_propagates_parent_error_without_creating_a_store(self):
        api=self.api();workspace=self.root/'missing'
        with self.assertRaises(ReadModelError) as caught:api(workspace,'missing-intake',method=METHOD)
        self.assertEqual(caught.exception.code,'store_missing')
        self.assertFalse(workspace.exists())

    def test_exact_signature_and_one_genuine_current_read_then_one_facts_build(self):
        api=self.api();fixture=self.fixture();module=importlib.import_module(api.__module__)
        self.assertEqual(list(inspect.signature(api).parameters),[
            'workspace','intake_id','method','expected_revision','expected_context_sha256'])
        original=IntakeReadModel.current_conducted_plan_context
        builder=module.build_conducted_plan_from_intake_facts
        captured=[]
        def read(model,intake_id):
            value=original(model,intake_id);captured.append((value,copy.deepcopy(value)))
            return value
        with patch.object(IntakeReadModel,'current_conducted_plan_context',autospec=True,side_effect=read) as reader,\
             patch.object(module,'build_conducted_plan_from_intake_facts',wraps=builder) as build:
            result=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(reader.call_count,1);self.assertEqual(build.call_count,1)
        native,before=captured[0]
        self.assertIs(result['context'],native['context']);self.assertIs(result['analysis'],native['analysis'])
        self.assertIs(build.call_args.args[0],native['context']);self.assertIs(build.call_args.args[1],native['analysis'])
        self.assertEqual(native,before)
        self.assertEqual(build.call_args.kwargs,dict(method=METHOD,expected_revision=native['context']['revision'],
            expected_context_sha256=digest(native['context'])))

    def test_missing_duty_unit_preserves_exact_blocked_wrapper_and_original_questions(self):
        api=self.api();fixture=self.fixture(duty='40')
        result=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        wrapper=result['facts_plan']
        expected=build_conducted_plan_from_intake_facts(result['context'],result['analysis'],
            expected_revision=result['context']['revision'],expected_context_sha256=digest(result['context']),method=METHOD)
        self.assertEqual(wrapper,expected);self.assertEqual(wrapper['status'],'blocked')
        self.assertIsNone(wrapper['plan_input']['plan']['source_settings']['duty_cycle'])
        self.assertEqual([q['reason'] for q in wrapper['questions']],['source_unit_missing'])
        self.assertEqual(wrapper['plan_input']['intake']['source_facts'],fixture['analysis']['facts'])
        self.assertIs(wrapper['plan_input']['verification']['execution_authority'],False)

    def test_explicit_current_pins_match_but_original_model_context_pin_is_not_restored(self):
        api=self.api();fixture=self.fixture()
        current=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        matched=api(fixture['store'].root,fixture['intake_id'],method=METHOD,expected_revision=1,
            expected_context_sha256=digest(current['context']))
        self.assertEqual(matched,current)
        stale=api(fixture['store'].root,fixture['intake_id'],method=METHOD,
            expected_context_sha256=digest(fixture['context']))
        self.assertEqual(stale['context'],current['context'])
        self.assertEqual(stale['facts_plan']['status'],'blocked')
        self.assertTrue(any(g['code']=='expected_context_changed_or_invalid' for g in stale['facts_plan']['plan_input']['gaps']))
        self.assertEqual(fixture['analysis'],current['analysis'])

    def test_native_bad_pins_and_method_subclass_are_not_defaulted_or_coerced(self):
        api=self.api();fixture=self.fixture()
        for pins in ({'expected_revision':False},{'expected_revision':0},{'expected_revision':'1'},
                     {'expected_context_sha256':''},{'expected_context_sha256':True}):
            with self.subTest(pins=pins):
                result=api(fixture['store'].root,fixture['intake_id'],method=METHOD,**pins)
                self.assertEqual(result['facts_plan']['status'],'blocked')
                self.assertTrue(all(v is None for v in result['facts_plan']['plan_input']['plan']['source_settings'].values()))
        hooks=[]
        class NotNative(dict):
            def __getitem__(self,key):hooks.append(key);raise AssertionError('subclass hook')
        result=api(fixture['store'].root,fixture['intake_id'],method=NotNative(METHOD))
        self.assertEqual(result['facts_plan']['status'],'blocked');self.assertEqual(hooks,[])

    def test_runtime_is_readonly_with_closed_sql_native_bindings_and_no_side_effect_services(self):
        api=self.api();fixture=self.fixture();before=self.files(fixture)
        from labflow.store import _ExistingBinding
        connect=sqlite3.connect;acquire=_ExistingBinding.acquire
        connections=[];bindings=[];statements=[];connect_args=[]
        def observed_connect(*args,**kwargs):
            connect_args.append((args,kwargs));con=connect(*args,**kwargs)
            con.set_trace_callback(statements.append);connections.append(con);return con
        def observed_acquire(binding):
            try:return acquire(binding)
            finally:bindings.append(binding)
        def forbidden(*args,**kwargs):raise AssertionError('read path entered a write/model/HTTP service')
        with ExitStack() as stack:
            for target in ('labflow.store.Store.__init__','labflow.store.Store.connection',
                'labflow.store.Store.write_blob','labflow.store.Store.register_blob','labflow.store.Store.event',
                'labflow.intake_jobs.claim_job','labflow.intake_jobs.complete_job','labflow.intake_jobs.respond',
                'labflow.active_intake.scan_source','labflow.intake_documents.prepare_analysis_documents',
                'labflow.intake_documents._retain','labflow.intake_worker.run_worker',
                'labflow.intake_worker.SyntheticTextProvider.analyze','labflow.document_extract.extract_document',
                'labflow.intake_documents.extract_document','subprocess.Popen','socket.socket'):
                stack.enter_context(patch(target,side_effect=forbidden))
            stack.enter_context(patch.object(sqlite3,'connect',side_effect=observed_connect))
            stack.enter_context(patch.object(_ExistingBinding,'acquire',observed_acquire))
            result=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(result['facts_plan']['status'],'ready_for_simulation')
        self.assertEqual(self.files(fixture),before)
        self.assertTrue(connections);self.assertEqual(len(bindings),1)
        self.assertTrue(all('?mode=ro' in args[0] and kwargs.get('uri') is True for args,kwargs in connect_args))
        writes={'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP','REPLACE','VACUUM','ATTACH','DETACH','REINDEX'}
        self.assertTrue(all(sql.strip().split()[0].upper() not in writes for sql in statements))
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')
        self.assertTrue(all(b.state=='closed' and b.active==0 and not b.handles for b in bindings))

    def test_readonly_file_attributes_are_supported_without_changing_source_bytes_or_metadata(self):
        api=self.api();fixture=self.fixture()
        paths=[p for p in fixture['store'].root.rglob('*') if p.is_file()]
        def restore():
            for p in paths:
                if p.exists():p.chmod(stat.S_IREAD|stat.S_IWRITE)
        self.addCleanup(restore)
        for path in paths:path.chmod(stat.S_IREAD)
        before=self.files(fixture)
        result=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(result['facts_plan']['status'],'ready_for_simulation')
        self.assertEqual(self.files(fixture),before)

    def test_plain_text_nonsynthetic_and_incomplete_keep_parent_unavailable_errors(self):
        api=self.api();module=importlib.import_module(api.__module__)
        cases=[({'kind':'text'},'intake_conducted_preview_v2_pdf_required'),
               ({'synthetic':False},'intake_conducted_preview_synthetic_required'),
               ({'completed':False},'intake_conducted_preview_analysis_unavailable')]
        for index,(options,code) in enumerate(cases):
            with self.subTest(options=options):
                fixture=completed_fixture(self.root/str(index),**options);before=self.files(fixture)
                with patch.object(module,'build_conducted_plan_from_intake_facts') as builder:
                    with self.assertRaises(ReadModelError) as caught:api(fixture['store'].root,fixture['intake_id'],method=METHOD)
                self.assertEqual(caught.exception.code,code);builder.assert_not_called()
                self.assertEqual(self.files(fixture),before)

    def test_missing_or_invalid_intake_has_no_fabricated_plan(self):
        api=self.api();fixture=self.fixture();module=importlib.import_module(api.__module__)
        for intake_id,code in [('unknown-intake','intake_not_found'),(None,'intake_conducted_preview_invalid_request')]:
            with self.subTest(intake_id=intake_id):
                with patch.object(module,'build_conducted_plan_from_intake_facts') as builder:
                    with self.assertRaises(ReadModelError) as caught:api(fixture['store'].root,intake_id,method=METHOD)
                self.assertEqual(caught.exception.code,code);builder.assert_not_called()

    def test_new_revision_is_not_replaced_by_old_model_context_or_stale_pins(self):
        api=self.api();fixture=self.fixture()
        old=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        (fixture['folder']/'supplement.txt').write_text('Authored revision marker.\n',encoding='utf-8')
        scan_source(fixture['store'],'CURRENT-FACTS-AUTHORED',now=120)
        scan_source(fixture['store'],'CURRENT-FACTS-AUTHORED',now=120.01)
        with self.assertRaises(ReadModelError) as caught:api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(caught.exception.code,'intake_conducted_preview_analysis_unavailable')
        job=claim_job(fixture['store'],'current-facts-revision2',now=121)
        analysis=SyntheticTextProvider().analyze(job)
        complete_job(fixture['store'],job['job_id'],job['token'],analysis,now=122)
        stale=api(fixture['store'].root,fixture['intake_id'],method=METHOD,expected_revision=1,
            expected_context_sha256=digest(old['context']))
        self.assertEqual(stale['context']['revision'],2);self.assertEqual(stale['facts_plan']['status'],'blocked')
        self.assertTrue(any(g['code']=='expected_revision_changed_or_invalid' for g in stale['facts_plan']['plan_input']['gaps']))
        current=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(current['context']['revision'],2);self.assertEqual(current['facts_plan']['status'],'ready_for_simulation')
        self.assertEqual(current['analysis'],analysis)

    def test_invalid_retained_source_is_parent_error_before_facts_build(self):
        api=self.api();fixture=self.fixture();module=importlib.import_module(api.__module__)
        blob=fixture['store'].blob_path(fixture['context']['documents'][0]['sha256'])
        blob.write_bytes(blob.read_bytes()+b'authored negative-case tamper')
        before=self.files(fixture)
        with patch.object(module,'build_conducted_plan_from_intake_facts') as builder:
            with self.assertRaises(ReadModelError) as caught:api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(caught.exception.code,'intake_conducted_preview_source_invalid');builder.assert_not_called()
        self.assertEqual(self.files(fixture),before)

    def test_parent_read_and_builder_errors_including_base_exceptions_keep_identity(self):
        api=self.api();fixture=self.fixture();module=importlib.import_module(api.__module__)
        class Stop(BaseException):pass
        for error in (ReadModelError('authored-read-error'),ValueError('authored-value'),RuntimeError('authored-runtime'),
                      OSError('authored-os'),MemoryError('authored-memory'),KeyboardInterrupt('authored-control'),
                      SystemExit('authored-exit'),Stop('authored-base')):
            with self.subTest(kind=type(error).__name__):
                with patch.object(IntakeReadModel,'current_conducted_plan_context',side_effect=error),\
                     patch.object(module,'build_conducted_plan_from_intake_facts') as builder:
                    with self.assertRaises(type(error)) as caught:api(fixture['store'].root,fixture['intake_id'],method=METHOD)
                self.assertIs(caught.exception,error);builder.assert_not_called()
                with patch.object(module,'build_conducted_plan_from_intake_facts',side_effect=error):
                    with self.assertRaises(type(error)) as caught:api(fixture['store'].root,fixture['intake_id'],method=METHOD)
                self.assertIs(caught.exception,error)

    def test_genuine_capture_control_closes_read_sql_and_native_bindings_before_propagating(self):
        api=self.api();fixture=self.fixture()
        from labflow.store import _ExistingBinding
        original_acquire=_ExistingBinding.acquire;original_connect=sqlite3.connect
        bindings=[];connections=[]
        def acquire(binding):
            try:return original_acquire(binding)
            finally:bindings.append(binding)
        def connect(*args,**kwargs):
            con=original_connect(*args,**kwargs);connections.append(con);return con
        error=KeyboardInterrupt('genuine-capture-control')
        with patch.object(_ExistingBinding,'acquire',acquire),patch.object(sqlite3,'connect',side_effect=connect),\
             patch('labflow.intake_reference_snapshot.capture_intake_reference_snapshot_in_transaction',side_effect=error):
            with self.assertRaises(KeyboardInterrupt) as caught:api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertIs(caught.exception,error)
        self.assertEqual(len(bindings),1)
        self.assertTrue(all(b.state=='closed' and b.active==0 and not b.handles for b in bindings))
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')

    def test_returned_native_snapshots_are_detached_from_storage_and_builder_output(self):
        api=self.api();fixture=self.fixture();before=self.files(fixture)
        first=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        second=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(first,second)
        first['context']['documents'].clear();first['analysis']['facts'].clear()
        self.assertTrue(first['facts_plan']['plan_input']['intake']['source_facts'])
        third=api(fixture['store'].root,fixture['intake_id'],method=METHOD)
        self.assertEqual(third,second);self.assertEqual(self.files(fixture),before)


if __name__=='__main__':unittest.main()
