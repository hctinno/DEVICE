"""Supplied intent review host tests; genuine P0 preparation precedes P1 reads."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import http.client
import io
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock
import uuid

from labflow import ui_server as host
from labflow.active_intake import intake_status, register_source, scan_source
from labflow.document_extract import extract_document
from labflow.intake_jobs import claim_job, complete_job, respond
from labflow.intake_reference_snapshot import read_intake_reference_snapshot
from labflow.intake_test_intent import IntakeTestIntentError, build_intake_test_intent_review
from labflow.intake_worker import SyntheticTextProvider
from labflow.store import Store, canonical
from labflow import intake_test_intent as parent

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / '.local/INTAKE-INTENT-VIEW-001/test-evidence'


def fixture(label='host',*,text_request=False):
    """Public jobs/034 and actual new PDF; never imported by production."""
    from reportlab.pdfgen import canvas
    root=EVIDENCE/(label+'-'+uuid.uuid4().hex);root.mkdir(parents=True,exist_ok=False)
    inbox=root/'inbox';bundle=inbox/'제공 근거 합성 의뢰';bundle.mkdir(parents=True)
    buffer=io.BytesIO();pdf=canvas.Canvas(buffer)
    text=pdf.beginText(40,790)
    for line in ['SYNTHETIC / NO MODEL OR HARDWARE','product_type: sensor_node','market: FCC',
                 'model: VIEW-DEMO','purpose: RULE-VIEW METHOD-VIEW']:
        text.textLine(line)
    pdf.drawText(text);pdf.showPage();pdf.save();raw=buffer.getvalue()
    if text_request:
        (bundle/'request.txt').write_text('product_type: sensor_node\nmarket: FCC\nmodel: VIEW-DEMO\npurpose: RULE-VIEW METHOD-VIEW\n',encoding='utf-8')
    else:(bundle/'request.pdf').write_bytes(raw)
    store=Store(root/'state')
    try:
        register_source(store,'VIEW-INBOX',inbox,synthetic=True,settle_seconds=.001)
        scan_source(store,'VIEW-INBOX',now=100);scan_source(store,'VIEW-INBOX',now=100.002)
        job=claim_job(store,'VIEW-WORKER',now=101)
        context={key:deepcopy(job[key]) for key in ('job_id','intake_id','revision','synthetic','documents',
            'analysis_contract','instructions','analysis_context_id')}
        analysis=SyntheticTextProvider().analyze(job)
        complete_job(store,job['job_id'],job['token'],analysis,now=102)
        respond(store,'VIEW-PROCEED','proceed',intake_id=job['intake_id'])
        projection=intake_status(store,job['intake_id'])['analysis']
        observation=read_intake_reference_snapshot(store,job['intake_id'])
    finally:store.close()
    extraction=extract_document(raw,'basis.pdf');page=extraction['pages'][0]
    line=next(i for i,value in enumerate(page['text'].splitlines(),1) if 'RULE-VIEW' in value)
    fact_index=next(i for i,value in enumerate(analysis['facts']) if value['field']=='purpose')
    basis={'document_id':'SYN-BASIS','page_number':1,'text_sha256':page['text_sha256'],'line_start':line,'line_end':line}
    proposal={'as_of':None,'institution_scope':None,'workflow_scope_id':None,'fields':{field:[{
        'literal':literal,'origin':'explicit_supplied','intake_refs':[{'fact_index':fact_index,'evidence_index':0}],
        'basis_refs':[deepcopy(basis)]}] for field,literal in [('rule','RULE-VIEW'),('method','METHOD-VIEW')]}}
    sources=[{'document_id':'SYN-BASIS','source_kind':'report','representation':'original',
        'artifact_sha256':hashlib.sha256(raw).hexdigest(),'institution_scope':None,'workflow_scope_ids':[],
        'edition':None,'effective_from':None,'effective_to':None,'review_status':'reviewed','rights_status':'usable','extraction':extraction}]
    supplied=({'context':context,'analysis':analysis,'projection':projection,'observation':observation},proposal,sources)
    return root,job['intake_id'],supplied


def database(root):
    con=sqlite3.connect((root/'state/lab.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:return '\n'.join(con.iterdump())
    finally:con.close()


def table_counts(root):
    con=sqlite3.connect((root/'state/lab.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        names=[row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {name:con.execute('SELECT COUNT(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in names}
    finally:con.close()


class IntentHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.root,cls.ident,cls.supplied=fixture()

    @contextmanager
    def server(self,inputs=(),*,root=None):
        root=self.root if root is None else root
        store=Store.open_existing(str(root/'state'));server=thread=None
        try:
            server=host.create_server(store.root,host='127.0.0.1',port=0,
                intake_reference_store=store,intake_reference_read_scope=(self.ident,),
                intake_test_intent_inputs=inputs)
            thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02});thread.start()
            yield server,store
        finally:
            if server is not None:server.server_close()
            if thread is not None:thread.join(5);self.assertFalse(thread.is_alive())
            store.close()

    def get(self,server,path='/api/intakes',method='GET'):
        con=http.client.HTTPConnection(*server.server_address,timeout=6)
        try:
            con.request(method,path);reply=con.getresponse();return reply.status,dict(reply.getheaders()),reply.read()
        finally:con.close()

    def test_default_empty_does_not_import_parent_or_add_metadata(self):
        original=host.importlib.import_module;imports=[]
        def importing(name,*args,**kwargs):
            if name.endswith('intake_test_intent'):imports.append(name);raise AssertionError('default imports optional API')
            return original(name,*args,**kwargs)
        with mock.patch.object(host.importlib,'import_module',side_effect=importing),self.server() as (server,store):
            status,_,raw=self.get(server);self.assertEqual(status,200)
            self.assertNotIn('intake_test_intent_reviews',json.loads(raw))
        self.assertEqual(imports,[])

    def test_isolated_default_server_does_not_load_optional_API_module(self):
        code="import json,sys;from labflow.ui_server import create_server;s=create_server(sys.argv[1],port=0);s.server_close();print(json.dumps({'optional_imported':'labflow.intake_test_intent' in sys.modules}))"
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code,str(self.root/'state')],cwd=ROOT,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0);self.assertEqual(result.stderr,b'');self.assertFalse(json.loads(result.stdout)['optional_imported'])

    def test_public_parent_once_cache_exact_result_and_inputs_detached(self):
        supplied=deepcopy(self.supplied);before=canonical(supplied);expected=build_intake_test_intent_review(*supplied)
        with mock.patch.object(parent,'build_intake_test_intent_review',wraps=build_intake_test_intent_review) as api:
            with self.server((supplied,)) as (server,store):
                self.assertEqual(api.call_count,1);self.assertEqual(canonical(supplied),before)
                supplied[1]['fields']['rule'][0]['literal']='caller changed after configuration'
                for path in ['/api/intakes','/api/intakes/'+self.ident]:
                    status,headers,raw=self.get(server,path);self.assertEqual(status,200)
                    result=json.loads(raw)['intake_test_intent_reviews'];self.assertEqual(len(result),1)
                    self.assertTrue(result[0]==expected,'host must preserve exact public review')
                    self.assertEqual(headers['Cache-Control'],'no-store')
                status,_,raw=self.get(server,'/api/intakes','HEAD');self.assertEqual(status,200);self.assertEqual(raw,b'')
                self.assertNotIn('intake_test_intent_reviews',json.loads(self.get(server,'/api/intakes/'+self.ident+'/fixture-runs')[2]))
                self.assertEqual(api.call_count,1)

    def test_outer_types_and_parent_fixed_errors_fail_before_bind(self):
        invalid=deepcopy(self.supplied);invalid[0]['context']={}
        limit=deepcopy(self.supplied);limit[1]['fields']['rule'][0]['literal']='x'*257
        source=deepcopy(self.supplied);source[2][0]['artifact_sha256']='0'*64
        rows=[(None,'invalid_input'),([], 'invalid_input'),((self.supplied,self.supplied),'invalid_input'),
              ((list(self.supplied),),'invalid_input'),((invalid,),'invalid_input'),((limit,),'limit_exceeded'),((source,),'source_error')]
        store=Store.open_existing(str(self.root/'state'))
        try:
            for inputs,suffix in rows:
                with self.subTest(code=suffix),mock.patch.object(host.ThreadingHTTPServer,'server_bind') as bind:
                    with self.assertRaises(IntakeTestIntentError) as caught:
                        host.create_server(store.root,port=0,intake_reference_store=store,intake_test_intent_inputs=inputs)
                    self.assertEqual(caught.exception.code,'test_intent_'+suffix);bind.assert_not_called()
                    with store.connection() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM intakes').fetchone()[0],1)
        finally:store.close()

    def test_same_revision_answer_change_hides_stale_full_projection(self):
        root,ident,supplied=fixture('answer-change')
        with self.server((supplied,),root=root) as (server,store):
            self.assertIn('intake_test_intent_reviews',json.loads(self.get(server)[2]))
            before=intake_status(store,ident)['revision']
            respond(store,'VIEW-ANSWER','answer',intake_id=ident,answers={'purpose':'changed explicit answer'})
            payload=json.loads(self.get(server)[2]);self.assertEqual(payload['intakes'][0]['revision'],before)
            self.assertNotIn('intake_test_intent_reviews',payload)

    def test_other_identity_and_revision_are_not_attached(self):
        for key,value in [('intake_id','UNRELATED'),('revision',2)]:
            supplied=deepcopy(self.supplied);supplied[0]['context'][key]=value;supplied[0]['projection'][key]=value
            supplied[0]['observation']=None
            with self.subTest(key=key),self.server((supplied,)) as (server,store):
                self.assertNotIn('intake_test_intent_reviews',json.loads(self.get(server)[2]))

    def test_null_analysis_is_not_matched_or_reconstructed(self):
        original=host.IntakeReadModel.snapshot
        def snapshot(model,intake_id=None):
            payload=original(model,intake_id);payload['intakes'][0]['analysis']=None;return payload
        with self.server((deepcopy(self.supplied),)) as (server,store),mock.patch.object(host.IntakeReadModel,'snapshot',snapshot):
            self.assertNotIn('intake_test_intent_reviews',json.loads(self.get(server)[2]))

    def test_V1_genuine_unavailable_capture_preserves_unknown_and_null(self):
        root,ident,supplied=fixture('text-V1',text_request=True)
        self.assertEqual(supplied[0]['analysis']['schema_version'],1)
        self.assertNotIn('context_id',supplied[0]['analysis']);self.assertEqual(supplied[0]['observation']['status'],'unavailable')
        with self.server((supplied,),root=root) as (server,store):
            value=json.loads(self.get(server)[2])['intake_test_intent_reviews'][0]
            self.assertEqual(value['status'],'review_only');self.assertIn('intake_binding_incomplete',value['reason_codes'])
            self.assertIsNone(value['input_binding']['result_sha256']);self.assertIsNone(value['input_binding']['observation_snapshot_id'])
            self.assertFalse(value['verification']['model_execution_verified']);self.assertFalse(value['verification']['execution_authorized'])

    def test_mismatched_submission_keeps_reason_and_does_not_become_a_new_quote(self):
        supplied=deepcopy(self.supplied)
        supplied[0]['analysis']['facts'][0]['status']='uncertain'
        with self.server((supplied,)) as (server,store):
            value=json.loads(self.get(server)[2])['intake_test_intent_reviews'][0]
            self.assertIn('intake_binding_mismatch',value['reason_codes'])
            self.assertFalse(value['verification']['query_release_authorized'])
            for field in value['fields'].values():
                for candidate in field['candidates']:
                    self.assertFalse(candidate['literal_linked']);self.assertNotIn('quote',candidate)

    def test_GET_does_not_read_sources_repeat_API_or_write_database(self):
        before=database(self.root);opens=[];original=Path.open
        def opening(path,*args,**kwargs):
            if path.parent==self.root/'state/blobs':opens.append(1)
            return original(path,*args,**kwargs)
        with self.server((deepcopy(self.supplied),)) as (server,store):
            with mock.patch.object(Path,'open',opening),mock.patch.object(parent,'build_intake_test_intent_review',side_effect=AssertionError('GET must not repeat API')):
                for _ in range(3):self.assertEqual(self.get(server)[0],200)
        self.assertEqual(opens,[]);self.assertTrue(database(self.root)==before,'metadata reads must preserve full SQL')

    def test_genuine_parent_interrupt_prevents_binding_and_preserves_borrower(self):
        store=Store.open_existing(str(self.root/'state'));interrupted=KeyboardInterrupt()
        def supplied(*args):
            build_intake_test_intent_review(*args)
            raise interrupted
        try:
            with mock.patch.object(parent,'build_intake_test_intent_review',supplied), \
                    mock.patch.object(host.ThreadingHTTPServer,'server_bind') as bind, \
                    mock.patch.object(store,'close',wraps=store.close) as close:
                with self.assertRaises(KeyboardInterrupt) as caught:
                    host.create_server(store.root,port=0,intake_reference_store=store,
                        intake_test_intent_inputs=(deepcopy(self.supplied),))
                self.assertIs(caught.exception,interrupted);bind.assert_not_called();close.assert_not_called()
                with store.connection() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM intakes').fetchone()[0],1)
        finally:store.close()

    def test_owned_port_collision_uses_existing_failure_and_keeps_Store_open(self):
        store=Store.open_existing(str(self.root/'state'))
        try:
            with socket.socket() as occupied:
                if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):occupied.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
                occupied.bind(('127.0.0.1',0));occupied.listen()
                with mock.patch.object(parent,'build_intake_test_intent_review',wraps=build_intake_test_intent_review) as api:
                    with self.assertRaises(host._ReferenceFailure) as caught:
                        host.create_server(store.root,port=occupied.getsockname()[1],intake_reference_store=store,
                            intake_test_intent_inputs=(deepcopy(self.supplied),))
                    self.assertEqual(caught.exception.code,'intake_reference_ui_unavailable')
                    self.assertEqual(api.call_count,1)
                with store.connection() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM intakes').fetchone()[0],1)
        finally:store.close()


class IntentNativeTests(unittest.TestCase):
    def wait_file(self,path,process):
        until=time.monotonic()+30
        while not path.exists() and time.monotonic()<until and process.poll() is None:time.sleep(.02)
        self.assertTrue(path.exists(),'native browser stage did not complete')

    def moves(self,root,blocked):
        for path in [root/'state/lab.sqlite3',root/'state/blobs',root/'state',root]:
            target=path.with_name(path.name+'.moved')
            self.assertTrue(path.resolve().is_relative_to(EVIDENCE.resolve()));self.assertTrue(target.resolve().is_relative_to(EVIDENCE.resolve()))
            self.assertFalse(target.exists())
            try:path.rename(target)
            except OSError:self.assertTrue(blocked)
            else:target.rename(path);self.assertFalse(blocked,'borrowed Store native pin released early')

    def run_native(self,width,configured):
        root,ident,supplied=fixture('native-'+str(width)+('-supplied' if configured else '-empty'))
        control=root/'control';control.mkdir();script=control/'browser.cjs';script.write_text(_BROWSER,encoding='utf-8',newline='\n')
        from labflow.fcc_report_cases import FccReportCaseCatalog
        from labflow.fcc_case_review import build_case_review_context,decode_case_review_response
        catalog=FccReportCaseCatalog({'schema_version':1,'corpus_id':'SYN-INTENT-VIEW',
            'scope':{'issue_date_from':'2025-01-01','cutoff_at':'2026-10-25T00:00:00+09:00','timezone':'Asia/Seoul',
                'population_status':'unconfirmed','search_scope_notes':['synthetic fixture only'],
                'unverified_ranges':['all real rules, methods and reports'],'synthetic':True},'searches':[],'documents':[],'cases':[]},{})
        context=build_case_review_context(catalog,query={'product_family':'sensor_node','rule':'DEMO-RULE-NONNORMATIVE',
            'method':'DEMO-METHOD-NONNORMATIVE','model':'VIEW-DEMO'},case_ids=[])
        name='SYN-MANUAL-VIEW'
        response=decode_case_review_response(json.dumps({'schema_version':1,'kind':'fcc_case_review_response',
            'context_id':context['context_id'],'producer':{'kind':'model','name':name},'status':'no_candidate',
            'references':[],'reason_codes':['no_reviewed_case']}),context,producer_name=name)
        before=database(root);before_counts=table_counts(root)
        original_blobs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'state/blobs').iterdir()}
        stats={'phase':'startup','API':0,'source_opens':{},'SQL':{},'SQLite_open':0,'SQLite_C_close':0,'actions_close':0,'order':[]}
        active=[True];owned=[];armed=set();original_open=Path.open;old_profile=sys.getprofile();old_thread_profile=threading.getprofile()
        def audit(event,args):
            if active[0] and event=='sqlite3.connect/handle':owned.append(args[0]);stats['SQLite_open']+=1
        sys.addaudithook(audit)
        def opened(path,*args,**kwargs):
            if path.parent==root/'state/blobs':
                phase=stats['phase'];stats['source_opens'][phase]=stats['source_opens'].get(phase,0)+1
            return original_open(path,*args,**kwargs)
        def arm(con):
            if id(con) in armed:return
            armed.add(id(con))
            def trace(sql):
                phase=stats['phase'];value=stats['SQL'].setdefault(phase,{'statements':0,'DDL':0,'datawrite':0})
                verb=sql.lstrip().split(None,1)[0].upper() if sql.strip() else ''
                value['statements']+=1;value['DDL']+=verb in ('CREATE','DROP','ALTER')
                value['datawrite']+=verb in ('INSERT','UPDATE','DELETE','REPLACE')
            con.set_trace_callback(trace)
        originals={}
        def profile(frame,event,arg):
            package,name=frame.f_globals.get('__name__'),frame.f_code.co_name
            if event=='c_call' and getattr(arg,'__name__',None) in ('execute','cursor','executemany','executescript'):
                value=getattr(arg,'__self__',None);con=value if type(value) is sqlite3.Connection else getattr(value,'connection',None)
                if any(con is c for c in owned):arm(con)
            if event=='c_return' and getattr(arg,'__name__',None)=='close' and any(getattr(arg,'__self__',None) is c for c in owned):stats['SQLite_C_close']+=1
            if package=='labflow.intake_test_intent' and name=='build_intake_test_intent_review' and event=='call':stats['API']+=1
            if package=='labflow.intake_reference_review_host' and name=='append' and event=='call':
                value=frame.f_locals['request'];key=value['handle_id']
                if key in originals:stats['original7_equal']=originals[key]==value
                else:originals[key]=dict(value)
            if package=='labflow.intake_reference_review_host' and name=='close':
                if event=='call':stats['actions_close']+=1;stats['order'].append('actions.close')
                elif event=='return':stats['actions_close_None']=arg is None
            if package=='labflow.ui_server' and name=='server_close' and event=='return':stats['order'].append('host.closed')
            if package=='labflow.store' and name=='close' and event=='call' and type(frame.f_locals.get('self')) is Store:stats['order'].append('Store.close')
        server=store=thread=process=None
        try:
            sys.setprofile(profile);threading.setprofile(profile)
            with mock.patch.object(Path,'open',opened):
                store=Store.open_existing(str(root/'state'))
                server=host.create_server(store.root,port=0,intake_reference_store=store,
                    intake_reference_read_scope=(ident,),intake_reference_append_scope=(ident,),fcc_case_catalog=catalog,
                    intake_reference_review_inputs=({'intake_id':ident,'case_context':context,'validated_response':response,'producer_name':name},),
                    intake_test_intent_inputs=(deepcopy(supplied),) if configured else ())
                self.assertEqual(stats['API'],int(configured));stats['phase']='view'
                thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02});thread.start()
                import os
                env=os.environ.copy();env.setdefault('NODE_PATH','C:/Users/HCT-2838/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')
                process=subprocess.Popen(['node',str(script),'http://127.0.0.1:'+str(server.server_port)+'/#'+ident,str(control),str(width),'supplied' if configured else 'empty'],
                    cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                self.wait_file(control/'view-ready',process)
                stats['phase']='observer';stats['view_full_SQL_unchanged']=database(root)==before
                self.assertTrue(stats['view_full_SQL_unchanged'],'intent view must preserve SQL')
                self.moves(root,True);stats['native_blocked_before_host_close']=4
                self.assertEqual(stats['source_opens'].get('view',0),0)
                self.assertEqual(stats['SQL']['view']['DDL'],0);self.assertEqual(stats['SQL']['view']['datawrite'],0)
                self.assertGreater(stats['SQL']['view']['statements'],0);stats['phase']='C2'
                (control/'allow-c2').write_text('1',encoding='ascii');self.wait_file(control/'append-ready',process)
                stats['phase']='observer';recorded=database(root);stats['phase']='replay'
                (control/'allow-replay').write_text('1',encoding='ascii')
                out,err=process.communicate(timeout=30);self.assertEqual(process.returncode,0);self.assertEqual(err,b'');self.assertEqual(out,b'')
                stats['phase']='observer';stats['replay_full_SQL_unchanged']=database(root)==recorded
                self.assertTrue(stats['replay_full_SQL_unchanged'],'C2 replay must preserve SQL')
                after_counts=table_counts(root)
                stats['reference_rows']=[after_counts[name] for name in ('intake_reference_records','intake_reference_events','intake_reference_heads')]
                self.assertEqual(stats['reference_rows'],[1,1,1])
                stats['original_nonreference_rows_unchanged']=all(after_counts[name]==count for name,count in before_counts.items())
                self.assertTrue(stats['original_nonreference_rows_unchanged'])
                self.assertEqual(stats['SQL']['replay']['DDL'],0);self.assertEqual(stats['SQL']['replay']['datawrite'],0)
                self.assertTrue(stats['original7_equal']);self.assertEqual(stats['API'],int(configured))
                server.server_close();thread.join(5);self.assertFalse(thread.is_alive())
                self.moves(root,True);stats['native_blocked_after_host_close']=4
                store.close();self.moves(root,False);stats['native_released_after_caller_close']=4
                self.assertEqual(stats['actions_close'],1);self.assertTrue(stats['actions_close_None'])
                self.assertLess(stats['order'].index('host.closed'),stats['order'].index('Store.close'))
                self.assertEqual(stats['SQLite_open'],stats['SQLite_C_close'])
                stats['original_blobs_unchanged']=all(hashlib.sha256((root/'state/blobs'/key).read_bytes()).hexdigest()==value for key,value in original_blobs.items())
                self.assertTrue(stats['original_blobs_unchanged'])
                self.assertEqual(list((root/'state').glob('lab.sqlite3-*')),[])
                with socket.socket() as probe:probe.bind(('127.0.0.1',server.server_port))
                stats['own_port_rebound']=True;stats['sidecars_absent']=True
                server=store=thread=None
        finally:
            if process is not None and process.poll() is None:process.kill();process.communicate(timeout=5)
            if server is not None:server.server_close()
            if thread is not None:thread.join(5)
            if store is not None:store.close()
            active[0]=False;sys.setprofile(old_profile);threading.setprofile(old_thread_profile)
        with (control/'native-proof.json').open('x',encoding='utf-8') as stream:json.dump(stats,stream,indent=2)

    def test_genuine_supplied_API_GET_DOM_1440_and_390_with_C2(self):
        for width in (1440,390):
            with self.subTest(width=width):self.run_native(width,True)

    def test_genuine_unconfigured_API0_section0_existing_C2_stays_available(self):
        self.run_native(1440,False)


_BROWSER = r'''
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const [url,control,width,mode]=process.argv.slice(2),origin=new URL(url).origin;
const proof={mode,width:Number(width),status:'fail',counts:{prepare:0,append:0,current:0},external:0,downloads:0,page_errors:0};
let browser,stage='start';const secrets=new Set(),originals=new Map();
const wait=async name=>{const until=Date.now()+20000;while(!fs.existsSync(path.join(control,name))){assert.ok(Date.now()<until);await new Promise(r=>setTimeout(r,20));}};
const phase=(page,value)=>page.waitForFunction(v=>document.querySelector('.reference-actions-review')?.dataset.phase===v,value);
(async()=>{
 try{
  browser=await require('playwright').chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:Number(width),height:1000}}),page=await context.newPage();
  page.on('request',request=>{
   if(!request.url().startsWith(origin+'/')){proof.external++;return;}
   const key=new URL(request.url()).pathname.split('/').at(-1);
   if(Object.hasOwn(proof.counts,key))proof.counts[key]++;
   const token=request.headers()['x-intake-reference-csrf'];if(token)secrets.add(token);
   if(key==='append'){
    const value=request.postDataJSON();secrets.add(value.handle_id);
    if(originals.has(value.handle_id))proof.original7_equal=originals.get(value.handle_id)===JSON.stringify(value);else originals.set(value.handle_id,JSON.stringify(value));
   }
  });page.on('download',()=>proof.downloads++);page.on('pageerror',()=>proof.page_errors++);
  stage='view';await page.goto(url);await phase(page,'idle');await page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');
  const panel=page.locator('.test-intent-review');
  if(mode==='supplied'){
   await panel.waitFor();const text=await panel.innerText();assert.ok(text.includes('literal_linked'));assert.ok(text.includes('source_not_normative'));
   assert.ok(text.includes('모델 호출 없음'));assert.ok(text.includes('기존 분석의 모델 실행/품질 미검증'));
   assert.equal(await page.locator('.test-intent-authority dd').count(),12);assert.equal(await page.locator('.test-intent-authority dd').evaluateAll(nodes=>nodes.every(n=>n.textContent==='false')),true);
   assert.equal(await page.locator('.test-intent-checks dd').evaluateAll(nodes=>nodes.every(n=>n.textContent==='true')),true);
   assert.equal(await panel.locator('blockquote,button,a[download]').count(),0);
   await panel.locator('summary').first().focus();await page.keyboard.press('Enter');assert.equal(await panel.locator('details').first().evaluate(n=>n.open),true);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await panel.screenshot({path:path.join(control,'intent-'+width+'.png')});
  }else assert.equal(await panel.count(),0);
  assert.deepEqual(proof.counts,{prepare:0,append:0,current:0});fs.writeFileSync(path.join(control,'view-ready'),'1');await wait('allow-c2');
  stage='prepare';await page.locator('.ra-prepare').focus();await page.keyboard.press('Enter');await phase(page,'ready');
  assert.ok((await page.locator('.ra-preview').innerText()).includes('no_candidate'));
  stage='append';await page.locator('.ra-append').focus();await page.keyboard.press('Enter');await phase(page,'recorded');
  await page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');
  fs.writeFileSync(path.join(control,'append-ready'),'1');await wait('allow-replay');
  stage='replay';await page.locator('.ra-replay').focus();await page.keyboard.press('Enter');await phase(page,'recorded');
  await page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');
  assert.equal(await page.locator('.ra-registration .ra-fields>div').filter({hasText:'원래 요청 재전송 결과'}).locator('dd').innerText(),'true');
  assert.deepEqual(proof.counts,{prepare:1,append:2,current:0});assert.equal(proof.original7_equal,true);
  stage='privacy';for(const cookie of await context.cookies())secrets.add(cookie.value);
  const privacy=await page.evaluate(()=>({html:document.documentElement.outerHTML,storage:[localStorage.length,sessionStorage.length]}));
  assert.equal([...secrets].some(value=>value&&privacy.html.includes(value)),false);assert.deepEqual(privacy.storage,[0,0]);
  assert.equal(proof.external,0);assert.equal(proof.downloads,0);assert.equal(proof.page_errors,0);proof.status='pass';await context.close();
 }catch{proof.stage=stage;process.exitCode=1;}
 finally{if(browser)await browser.close();fs.writeFileSync(path.join(control,'browser-proof.json'),JSON.stringify(proof,null,2),{flag:'wx'});}
})().catch(()=>{process.exitCode=1;});
'''


if __name__=='__main__':unittest.main()
