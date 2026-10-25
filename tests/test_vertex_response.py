"""Synthetic ADC, local spawn worker and HTTP doubles; actual provider calls0."""
from copy import deepcopy
import hashlib
import importlib
import json
import multiprocessing
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

try:
    api=importlib.import_module('labflow.vertex_response')
except ModuleNotFoundError as error:
    if error.name!='labflow.vertex_response':raise
    api=None

TARGET='project-a6310591-f8cc-487c-9e3'
RAW=b' {"transport_only": 1}\n'
PROMPT=b'{"expected_producer":{"kind":"model","name":"vertex-test"},"messages":[]}'
SCHEMA=b' { "type": "object" }\n'
def raw(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(x):return hashlib.sha256(raw(x)).hexdigest()
def settings(**changes):
    value=dict(schema_version=1,kind='ai_run_settings',profile_id='vertex-trial',profile_revision=0,
        provider='vertex_ai',service='aiplatform.googleapis.com',project_id=TARGET,location='global',
        quota_project_id=TARGET,auth_profile_id='vertex-trial',model_id='gemini-3.8-flash',thinking_level='MEDIUM',
        max_output_tokens=512,timeout_seconds=3,profile_sha256='a'*64)
    value.update(changes);value['settings_sha256']=sha(value);return value


def response(model,mode='normal'):
    parts=[{'text':'FAKE_THOUGHT_SECRET','thought':True},{'text':RAW.decode()}]
    candidate={'index':0,'content':{'role':'model','parts':parts},'finishReason':'STOP'}
    result={'candidates':[candidate],'modelVersion':model+'-reported','responseId':'fake-response-1',
        'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':3,'totalTokenCount':15,'thoughtsTokenCount':2}}
    if mode=='max_tokens':candidate['finishReason']='MAX_TOKENS'
    elif mode=='safety':candidate['finishReason']='SAFETY'
    elif mode=='continuation':candidate['continuationToken']='do-not-follow'
    elif mode=='two_candidates':result['candidates'].append(deepcopy(candidate))
    elif mode=='wrong_role':candidate['content']['role']='user'
    elif mode=='tool':candidate['content']['parts']=[{'functionCall':{'name':'forbidden'}}]
    elif mode=='thought_only':candidate['content']['parts']=parts[:1]
    elif mode=='usage_bool':result['usageMetadata']['promptTokenCount']=True
    elif mode=='no_usage':result.pop('usageMetadata')
    elif mode=='fence':candidate['content']['parts']=[{'text':'```json\n{}\n```'}]
    elif mode=='bad_metadata':result['responseId']='FAKE SECRET\nheader'
    elif mode=='grounding':candidate['groundingMetadata']={}
    elif mode=='root_grounding':result['groundingMetadata']={}
    elif mode=='root_url_context':result['urlContextMetadata']={}
    return result


def _fake_vertex_worker(task):
    """Importable local process fixture, never imports auth or opens a socket."""
    def deny(event,args):
        if event in {'socket.connect','socket.getaddrinfo'}:raise AssertionError('NETWORK_FORBIDDEN_IN_TEST')
    sys.addaudithook(deny)
    directory=Path(task['directory']);mode=task['credentials'].get('account','normal')
    def marker(name):
        if mode=='missing_generation_marker' and name=='generation-started.json':return
        if mode=='missing_auth_finished' and name=='auth-finished.json':return
        data=b'{"started":1}' if mode=='marker_alias' and name=='generation-started.json' else b'{"started":true}'
        with (directory/name).open('xb') as f:f.write(data)
    marker('auth-started.json')
    if mode=='hang_auth':time.sleep(30);return
    marker('auth-http-started.json')
    result=dict(schema_version=1,code=None,phase='collect',auth_http_status=200,http_status=200,
        auth_retry_blocked=False,transport_handles_closed=True,artifact_handles_closed=True,response_complete=True)
    if mode in {'auth_403','auth_retry'}:
        result.update(code='auth_failed',phase='auth',auth_http_status=403,http_status=None,auth_retry_blocked=mode=='auth_retry',response_complete=False)
    else:
        marker('auth-finished.json');marker('generation-started.json')
        if mode in {'hang_generation','partial'}:
            with (directory/'provider-response.bin').open('xb') as f:f.write(b'{"partial":')
            time.sleep(30);return
        body=raw(response(task['settings']['model_id'],mode))
        if mode=='malformed':body=b'{broken}'
        elif mode=='duplicate':body=b'{"candidates":[],"candidates":[]}'
        elif mode=='surrogate':body=b'{"x":"\\ud800"}'
        elif mode=='body_overflow':body=b'x'*2097153
        elif mode=='http_403':body=b'{"error":{"message":"FAKE_SECRET_DO_NOT_ECHO"}}';result.update(code='http_error',http_status=403)
        elif mode=='http_cleanup':body=b'{"error":{}}';result.update(code='http_error',http_status=403,transport_handles_closed=False)
        elif mode=='gzip':result.update(code='response_invalid',response_complete=False)
        elif mode=='cleanup_only':result['transport_handles_closed']=False
        elif mode=='artifact_cleanup':result['artifact_handles_closed']=False
        with (directory/'provider-response.bin').open('xb') as f:f.write(body)
        if mode=='partial_valid':result['response_complete']=False
        if result['response_complete']:marker('response-complete.json')
    if mode=='missing_status':return
    with (directory/'worker-result.json').open('xb') as f:f.write(raw(result))
    if mode=='nonzero_worker':os._exit(9)


class FakeReply:
    def __init__(self,status,body,headers=None):self.status_code=status;self.body=body;self.headers=headers or {};self.closed=False
    @property
    def content(self):raise AssertionError('unbounded content must never be read')
    def iter_content(self,chunk_size):
        for pos in range(0,len(self.body),chunk_size):yield self.body[pos:pos+chunk_size]
    def close(self):self.closed=True


class VertexTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned Vertex API must exist before GREEN')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.adc=self.root/'synthetic-adc.json';self.number=0;self.children=[]
        self.credential=dict(type='authorized_user',client_id='FAKE_CLIENT',client_secret='FAKE_CLIENT_SECRET',refresh_token='FAKE_REFRESH_TOKEN',quota_project_id=TARGET,account='normal',universe_domain='googleapis.com')
        self.adc.write_bytes(raw(self.credential));self.addCleanup(self.check_workers)

    def check_workers(self):
        self.assertFalse(any(p.is_alive() for p in multiprocessing.active_children()),'Producer left an observed worker alive')

    def call(self,mode='normal',*,run_settings=None,prompt=PROMPT,schema=SCHEMA,cancel_event=None,**kwargs):
        self.number+=1;self.evidence=self.root/('exchange-'+str(self.number));self.credential['account']=mode;self.adc.write_bytes(raw(self.credential))
        args=dict(settings=settings() if run_settings is None else run_settings,adc_path=self.adc,evidence_dir=self.evidence,cancel_event=cancel_event);args.update(kwargs)
        with patch.object(api,'_vertex_worker',new=_fake_vertex_worker):
            return api.produce_vertex_response(prompt,schema,**args)

    def failure(self,mode,code,**kwargs):
        with self.assertRaises(api.VertexResponseError) as got:self.call(mode,**kwargs)
        error=got.exception;expected='vertex_response_'+code
        self.assertEqual((error.code,str(error),error.args),(expected,expected,(expected,)))
        self.assertIsNone(error.__context__);self.assertIsNone(error.__cause__)
        self.assertNotIn('FAKE_',str(error));self.assertNotIn(str(self.root),str(error))
        if error.receipt is not None:
            self.assertEqual(error.receipt['status'],'failed');self.assertFalse(error.receipt['verification']['wire_complete'])
            serialized=json.dumps(error.receipt)
            for secret in ['FAKE_CLIENT','FAKE_REFRESH','FAKE_SECRET','FAKE_THOUGHT',str(self.adc)]:self.assertNotIn(secret,serialized)
        return error

    def test_inspect_exact_metadata_norefresh_and_no_artifacts(self):
        before=self.adc.read_bytes()
        with patch.object(api.multiprocessing,'get_context',side_effect=AssertionError('no child')):
            value=api.inspect_vertex_credentials(self.adc,settings=settings())
        self.assertEqual(set(value),set('schema_version kind settings_sha256 auth_profile_id credential_type quota_project_id token_endpoint metadata_valid refresh_attempted model_access_verified credit_status_verified'.split()))
        self.assertEqual(value['kind'],'vertex_credentials_metadata');self.assertTrue(value['metadata_valid'])
        for k in ['refresh_attempted','model_access_verified','credit_status_verified']:self.assertFalse(value[k])
        self.assertEqual(self.adc.read_bytes(),before);self.assertEqual(list(self.root.iterdir()),[self.adc]);self.assertNotIn('FAKE_',json.dumps(value))

    def test_inspect_invalid_metadata_quota_endpoint_and_path_are_fixed(self):
        for change in [dict(type='service_account'),dict(quota_project_id='other'),dict(token_uri='https://fake.invalid/token'),dict(universe_domain='other.invalid'),dict(extra='forbidden'),dict(client_secret='')]:
            with self.subTest(change=change):
                info=dict(self.credential,**change);self.adc.write_bytes(raw(info))
                with self.assertRaises(api.VertexResponseError) as got:api.inspect_vertex_credentials(self.adc,settings=settings())
                code='credential_quota_mismatch' if 'quota_project_id' in change else 'credential_invalid'
                self.assertEqual(got.exception.code,'vertex_response_'+code);self.assertIsNone(got.exception.receipt)
        self.adc.write_bytes(b'{"type":"authorized_user","type":"authorized_user"}')
        with self.assertRaises(api.VertexResponseError):api.inspect_vertex_credentials(self.adc,settings=settings())

    def test_settings_exact16_target_hash_and_native_types(self):
        for key,value in [('schema_version',True),('provider','other'),('service','generativelanguage.googleapis.com'),('project_id','other'),('quota_project_id','other'),('model_id','unknown'),('thinking_level','MINIMAL'),('thinking_level','low'),('location','us-central1'),('max_output_tokens',True),('max_output_tokens',63),('max_output_tokens',8193),('timeout_seconds',0),('timeout_seconds',121),('profile_revision',True),('settings_sha256','b'*64),('profile_sha256','not-a-hash')]:
            with self.subTest(key=key,value=value):
                value_settings=settings(**{key:value});self.failure('normal','invalid_settings',run_settings=value_settings)
        value=settings();value['credential_path']='do-not-accept';self.failure('normal','invalid_settings',run_settings=value)
        class Sub(dict):pass
        self.failure('normal','invalid_settings',run_settings=Sub(settings()))

    def test_bytes_path_json_and_cancel_types_fail_before_worker(self):
        class Bytes(bytes):pass
        class Event:
            def is_set(self):raise AssertionError('must not call object hook')
        for kwargs in [dict(prompt='not bytes'),dict(prompt=Bytes(PROMPT)),dict(schema=bytearray(SCHEMA)),dict(adc_path=str(self.adc)),dict(evidence_dir=self.root),dict(cancel_event=Event())]:
            self.failure('normal','invalid_input',**kwargs)
        for value in [b'[]',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":"\\ud800"}',b' {"x":1}']:
            self.failure('normal','invalid_input',prompt=value)
        self.failure('normal','limit_exceeded',prompt=b'x'*262145)
        self.failure('normal','limit_exceeded',schema=b'x'*65537)

    def test_success_exact_receipt_artifacts_and_unmodified_wire(self):
        original=settings();snapshot=raw(original);wire,r=self.call(run_settings=original)
        self.assertEqual(wire,RAW);self.assertIs(type(wire),bytes);self.assertIs(type(r),dict)
        self.assertEqual(len(r),18);self.assertEqual(r['kind'],'vertex_response_receipt');self.assertEqual(r['status'],'complete')
        self.assertEqual(r['settings'],original);self.assertEqual(raw(original),snapshot);self.assertEqual(r,json.loads((self.evidence/'receipt.json').read_bytes()))
        self.assertEqual(r['response']['text_parts'],1);self.assertEqual(r['response']['thought_parts'],1)
        self.assertEqual(r['response']['reported_model_version'],original['model_id']+'-reported')
        self.assertEqual(r['attempts'],dict(worker_process_attempts=1,auth_refresh_attempts=1,auth_http_attempts=1,generation_post_attempts=1,auth_refresh_completed=True,auth_retry_blocked=False,application_retries=0))
        self.assertTrue(r['cleanup']['worker_reaped']);self.assertEqual(r['cleanup']['worker_exit_code'],0)
        self.assertIsNone(r['cost']['amount']);self.assertEqual(r['cost']['kind'],'unknown')
        self.assertFalse(r['verification']['remote_identity_verified']);self.assertFalse(r['verification']['credit_verified'])
        self.assertNotIn('FAKE_THOUGHT',json.dumps(r));self.assertIn(b'FAKE_THOUGHT',(self.evidence/'provider-response.bin').read_bytes())
        for d in r['artifacts'].values():
            b=(self.evidence/d['path']).read_bytes();self.assertTrue(d['complete']);self.assertEqual(d['extent'],'whole_file')
            self.assertEqual((len(b),hashlib.sha256(b).hexdigest()),(d['bytes'],d['sha256']))
        self.assertEqual((self.evidence/'request.json').read_bytes(),PROMPT);self.assertEqual((self.evidence/'response-schema.json').read_bytes(),SCHEMA)
        r['artifacts'].clear();self.assertEqual(len(json.loads((self.evidence/'receipt.json').read_bytes())['artifacts']),6)

    def test_six_combinations_exact_envelope_and_same_logical_inputs(self):
        receipts=[]
        for model in ['gemini-4-argon','gemini-3.8-flash']:
            for level in ['LOW','MEDIUM','HIGH']:
                run=settings(model_id=model,thinking_level=level);_,r=self.call(run_settings=run);receipts.append(r)
                envelope=json.loads((self.evidence/'provider-request.json').read_bytes());self.assertEqual(set(envelope),{'contents','generationConfig'})
                wrapper=json.loads(envelope['contents'][0]['parts'][0]['text']);self.assertEqual(wrapper,{'prompt_dto_utf8':PROMPT.decode(),'response_schema_utf8':SCHEMA.decode()})
                self.assertEqual(envelope['generationConfig'],{'maxOutputTokens':512,'thinkingConfig':{'thinkingLevel':level}})
                self.assertIn('/models/'+model+':generateContent',r['request']['url']);self.assertEqual(r['request']['quota_project_id'],TARGET)
        self.assertEqual(len({r['bindings']['prompt_sha256'] for r in receipts}),1);self.assertEqual(len({r['bindings']['schema_sha256'] for r in receipts}),1)
        self.assertEqual(len({r['exchange_ref'] for r in receipts}),6)

    def test_global_us_eu_hosts_are_exact(self):
        for location,host in [('global','aiplatform.googleapis.com'),('us','aiplatform.us.rep.googleapis.com'),('eu','aiplatform.eu.rep.googleapis.com')]:
            _,r=self.call(run_settings=settings(location=location));self.assertEqual(r['request']['url'],f'https://{host}/v1/projects/{TARGET}/locations/{location}/publishers/google/models/gemini-3.8-flash:generateContent')

    def test_noncomplete_safety_continuation_and_malformed_response(self):
        for mode,code in [('max_tokens','incomplete'),('safety','blocked'),('continuation','incomplete'),('two_candidates','response_invalid'),('wrong_role','response_invalid'),('tool','response_invalid'),('thought_only','response_invalid'),('usage_bool','response_invalid'),('bad_metadata','response_invalid'),('grounding','response_invalid'),('malformed','response_invalid'),('duplicate','response_invalid'),('surrogate','response_invalid'),('gzip','response_invalid'),('partial_valid','incomplete')]:
            with self.subTest(mode=mode):
                e=self.failure(mode,code);self.assertEqual(e.receipt['attempts']['generation_post_attempts'],1)

    def test_transport_does_not_repair_fences_or_fill_usage(self):
        wire,r=self.call('fence');self.assertEqual(wire,b'```json\n{}\n```')
        _,r=self.call('no_usage');self.assertIsNone(r['usage']);self.assertIsNone(r['cost']['amount'])

    def test_auth_http_failures_and_retry_guard_do_not_generate(self):
        for mode in ['auth_403','auth_retry']:
            e=self.failure(mode,'auth_failed');self.assertEqual(e.receipt['attempts']['generation_post_attempts'],0)
            self.assertEqual(e.receipt['attempts']['auth_http_attempts'],1)
            self.assertEqual(e.receipt['cost']['kind'],'not_applicable')
        e=self.failure('http_403','http_error');self.assertEqual(e.receipt['response']['http_status'],403);self.assertEqual(e.receipt['cost']['kind'],'unknown')

    def test_body_overflow_keeps_prefix_sha_and_no_fake_response(self):
        e=self.failure('body_overflow','limit_exceeded');d=e.receipt['artifacts']['provider_response']
        self.assertFalse(d['complete']);self.assertTrue(d['overflow']);self.assertEqual(d['extent'],'prefix')
        self.assertEqual(d['bytes'],2097152);self.assertEqual(d['sha256'],hashlib.sha256(b'x'*2097152).hexdigest())

    def test_preset_cancel_is_worker_auth_and_generation_zero(self):
        event=threading.Event();event.set();e=self.failure('normal','cancelled',cancel_event=event);self.assertIsNone(e.receipt)
        self.assertFalse(self.evidence.exists())

    def test_parent_wall_timeout_and_partial_unknown_do_not_refund(self):
        for mode in ['hang_auth','hang_generation']:
            start=time.monotonic();e=self.failure(mode,'timeout',run_settings=settings(timeout_seconds=1))
            self.assertLess(time.monotonic()-start,7);self.assertTrue(e.receipt['cleanup']['worker_reaped'])
            self.assertEqual(e.receipt['cancellation']['provider_completion'],'unknown');self.assertEqual(e.receipt['cost']['kind'],'unknown')
            self.assertIsNone(e.receipt['usage']);self.assertLessEqual(e.receipt['attempts']['worker_process_attempts'],1)

    def test_running_cancel_is_latched_and_reaps_worker(self):
        event=threading.Event()
        def trigger():
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                path=self.root/('exchange-'+str(self.number))/'generation-started.json'
                if path.exists():break
                time.sleep(.01)
            event.set()
        thread=threading.Thread(target=trigger);thread.start()
        try:e=self.failure('hang_generation','cancelled',cancel_event=event)
        finally:thread.join(3)
        self.assertTrue(e.receipt['cancellation']['requested']);self.assertTrue(e.receipt['cancellation']['local_worker_stopped'])
        self.assertFalse(e.receipt['cancellation']['remote_cancel_verified']);self.assertEqual(e.receipt['attempts']['generation_post_attempts'],1)

    def test_child_exit_or_missing_status_never_accepts_valid_looking_raw(self):
        for mode in ['nonzero_worker','missing_status']:
            e=self.failure(mode,'internal_error');self.assertFalse(e.receipt['verification']['wire_complete'])

    def test_parent_control_objects_survive_cleanup(self):
        for signal in [KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError]:
            original=signal('FAKE_CONTROL_SECRET')
            with patch.object(api.multiprocessing,'get_context',side_effect=original):
                with self.assertRaises(signal) as got:self.call()
            self.assertIs(got.exception,original)
        event=threading.Event();original=KeyboardInterrupt('FAKE_CONTROL_SECRET');fired=False;is_set=threading.Event.is_set
        def interrupt(value):
            nonlocal fired
            if value is event and (self.root/('exchange-'+str(self.number))/'generation-started.json').exists() and not fired:fired=True;raise original
            return is_set(value)
        with patch.object(threading.Event,'is_set',new=interrupt):
            with self.assertRaises(KeyboardInterrupt) as got:self.call('hang_generation',cancel_event=event)
        self.assertTrue(fired);self.assertIs(got.exception,original)

    def test_active_exception_context_is_sanitized(self):
        try:raise ValueError('FAKE_SECRET_DO_NOT_ECHO')
        except ValueError:self.failure('malformed','response_invalid')

    def test_only_two_public_functions(self):
        import inspect
        names={n for n,v in vars(api).items() if inspect.isfunction(v) and v.__module__==api.__name__ and not n.startswith('_')}
        self.assertEqual(names,{'inspect_vertex_credentials','produce_vertex_response'})

    def test_http_leaf_guards_auth_once_and_preserves_entire_payload(self):
        self._exercise_http_leaf('normal')

    def test_http_leaf_auth_retry_and_redirect_are_not_followed(self):
        self._exercise_http_leaf('auth_retry')
        self._exercise_http_leaf('http_redirect')

    def test_review_observed_stop_survives_local_cleanup(self):
        _,r=self.call()
        self.assertEqual(r['cancellation']['provider_completion'],'observed_stop')
        self.assertFalse(r['cancellation']['requested']);self.assertEqual(r['cleanup']['secondary_errors'],[])

    def test_fix_outer_metadata_is_rejected_with_normal_and_candidate_controls(self):
        wire,receipt=self.call();self.assertEqual(wire,RAW);self.assertTrue(receipt['verification']['wire_complete'])
        self.failure('grounding','response_invalid')
        for mode in ['root_grounding','root_url_context']:
            with self.subTest(mode=mode):
                error=self.failure(mode,'response_invalid')
                self.assertEqual(error.receipt['attempts']['generation_post_attempts'],1)
                self.assertFalse(error.receipt['verification']['wire_complete'])

    def test_review_parent_handle_close_failure_cannot_return_success(self):
        original=multiprocessing.process.BaseProcess.close;captured=[]
        def broken(process):
            if process.name.startswith('vertex-response-'):
                captured.append(process);raise OSError('FAKE_SECRET_CLOSE')
            return original(process)
        try:
            with patch.object(multiprocessing.process.BaseProcess,'close',new=broken):
                e=self.failure('normal','cleanup_failed')
            self.assertIn('transport_close_failed',e.receipt['cleanup']['secondary_errors'])
            self.assertFalse(e.receipt['cleanup']['transport_handles_closed'])
        finally:
            for process in captured:original(process)

    def test_review_auth_timeout_and_observed_http_error_keep_codes(self):
        self._exercise_http_leaf('auth_timeout')
        self._exercise_http_leaf('http_403_flood')

    def test_review_evidence_and_receipt_write_failures_keep_partial_receipt(self):
        original=Path.open
        for target in ['request.json','receipt.json']:
            def broken(path,*args,**kwargs):
                if path.name==target and args and 'x' in args[0]:raise OSError('FAKE_SECRET_WRITE '+str(path))
                return original(path,*args,**kwargs)
            with patch.object(Path,'open',new=broken):e=self.failure('normal','evidence_error')
            self.assertIsNotNone(e.receipt)
            if target=='receipt.json':self.assertIn('receipt_write_failed',e.receipt['cleanup']['secondary_errors'])

    def test_review_dependency_and_ADC_reparse_fail_before_network(self):
        import stat
        from types import SimpleNamespace
        original=Path.lstat
        def reparse(path,*args,**kwargs):
            value=original(path,*args,**kwargs)
            return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT) if path==self.adc else value
        with patch.object(Path,'lstat',new=reparse):
            with self.assertRaises(api.VertexResponseError) as got:api.inspect_vertex_credentials(self.adc,settings=settings())
        self.assertEqual(got.exception.code,'vertex_response_credential_invalid')
        with patch.object(api.importlib.metadata,'version',return_value='unexpected-version'):
            e=self.failure('normal','dependency_unavailable')
        self.assertEqual(e.receipt['attempts']['worker_process_attempts'],0)

    def test_boundary_timeout_large_integer_is_invalid_settings(self):
        self.failure('normal','invalid_settings',run_settings=settings(timeout_seconds=10**1000))

    def test_boundary_marker_types_and_success_evidence_are_strict(self):
        self.failure('marker_alias','evidence_error')
        for mode in ['missing_generation_marker','missing_auth_finished']:
            e=self.failure(mode,'internal_error')
            self.assertEqual(e.receipt['attempts']['generation_post_attempts'],1)
            self.assertEqual(e.receipt['cost']['kind'],'unknown')

    def test_boundary_child_cleanup_flags_keep_first_error_and_secondary(self):
        for mode,code,secondary in [('cleanup_only','cleanup_failed','transport_close_failed'),
                ('artifact_cleanup','cleanup_failed','artifact_close_failed'),('http_cleanup','http_error','transport_close_failed')]:
            e=self.failure(mode,code)
            self.assertIn(secondary,e.receipt['cleanup']['secondary_errors'])
            self.assertTrue(e.receipt['cleanup']['worker_reaped'])

    def test_boundary_interrupt_after_real_spawn_reaps_before_original_control(self):
        original=KeyboardInterrupt('FAKE_CONTROL_AFTER_SPAWN');start=multiprocessing.process.BaseProcess.start;captured=[]
        def interrupted(process):
            start(process);captured.append(process);raise original
        try:
            with patch.object(multiprocessing.process.BaseProcess,'start',new=interrupted):
                with self.assertRaises(KeyboardInterrupt) as got:self.call('hang_generation')
            self.assertIs(got.exception,original)
            receipt=json.loads((self.evidence/'receipt.json').read_bytes())
            self.assertTrue(receipt['cleanup']['worker_reaped'])
        finally:
            for process in captured:
                try:
                    if process.is_alive():process.kill();process.join(2)
                    process.close()
                except ValueError:pass

    def test_boundary_http_cleanup_and_auth_flood_keep_fixed_failures(self):
        for mode in ['artifact_close','session_close','mount_error','auth_403_flood']:
            with self.subTest(mode=mode):self._exercise_http_leaf(mode)

    def _exercise_http_leaf(self,mode):
        import google.oauth2.credentials
        import requests
        calls=[];sessions=[];replies=[]
        class Credential:
            quota_project_id=TARGET;token=None
            def refresh(self,request):
                reply=request('https://oauth2.googleapis.com/token',method='POST',body=b'FAKE_AUTH_BODY',headers={})
                if mode=='auth_retry':request('https://oauth2.googleapis.com/token',method='POST',body=b'FAKE_AUTH_BODY',headers={})
                if reply.status!=200:raise ValueError('FAKE_AUTH_ERROR')
                self.token='FAKE_ACCESS_TOKEN'
        class Session:
            def __init__(self):self.trust_env=True;self.headers={};self.closed=False;sessions.append(self)
            def mount(self,name,adapter):
                self.adapter=adapter
                if mode=='mount_error':raise ValueError('FAKE_CONFIG_SECRET')
            def request(self,method,url,**kwargs):
                calls.append((method,url,kwargs));self_check=not self.trust_env and kwargs['allow_redirects'] is False and kwargs['verify'] is True
                if not self_check:raise AssertionError('unsafe HTTP settings')
                if mode=='auth_timeout':raise requests.exceptions.Timeout('FAKE_AUTH_TIMEOUT')
                if mode=='auth_403_flood' and url=='https://oauth2.googleapis.com/token':reply=FakeReply(403,b'x'*65537)
                elif url=='https://oauth2.googleapis.com/token':reply=FakeReply(200,b'{"access_token":"FAKE_ACCESS_TOKEN"}')
                elif mode=='http_403_flood':reply=FakeReply(403,b'x'*2097153)
                else:reply=FakeReply(302 if mode=='http_redirect' else 200,raw(response('gemini-3.8-flash')))
                replies.append(reply);return reply
            def post(self,url,**kwargs):return self.request('POST',url,**kwargs)
            def close(self):
                self.closed=True
                if mode=='session_close':raise OSError('FAKE_CLOSE_SECRET')
        self.number+=1;directory=self.root/('leaf-'+str(self.number));directory.mkdir()
        payload=raw({'contents':[],'generationConfig':{}})
        task=dict(directory=str(directory),settings=settings(),credentials=deepcopy(self.credential),payload=payload,url=f'https://aiplatform.googleapis.com/v1/projects/{TARGET}/locations/global/publishers/google/models/gemini-3.8-flash:generateContent',deadline=time.monotonic()+3)
        original_open=Path.open
        class CloseFailure:
            def __init__(self,stream):self.stream=stream
            def write(self,data):return self.stream.write(data)
            def close(self):self.stream.close();raise OSError('FAKE_FILE_CLOSE_SECRET')
        def leaf_open(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return CloseFailure(stream) if mode=='artifact_close' and path.name=='provider-response.bin' and args[0]=='xb' else stream
        with patch.object(google.oauth2.credentials.Credentials,'from_authorized_user_info',return_value=Credential()),patch.object(requests,'Session',new=Session),patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK_FORBIDDEN')),patch.object(Path,'open',new=leaf_open):
            result=api._http_exchange(task)
        if mode=='auth_retry':
            self.assertEqual(result['code'],'auth_failed');self.assertTrue(result['auth_retry_blocked']);self.assertEqual(len(calls),1)
        elif mode=='auth_timeout':self.assertEqual(result['code'],'timeout');self.assertEqual(len(calls),1)
        elif mode=='http_403_flood':self.assertEqual(result['code'],'http_error');self.assertEqual(len(calls),2)
        elif mode=='http_redirect':self.assertEqual(result['code'],'http_error');self.assertEqual(len(calls),2)
        elif mode=='auth_403_flood':self.assertEqual(result['code'],'auth_failed');self.assertEqual(len(calls),1)
        elif mode=='mount_error':self.assertEqual(result['code'],'auth_failed');self.assertEqual(len(calls),0)
        elif mode=='artifact_close':self.assertEqual(result['code'],'cleanup_failed');self.assertFalse(result['artifact_handles_closed'])
        elif mode=='session_close':self.assertEqual(result['code'],'cleanup_failed');self.assertFalse(result['transport_handles_closed'])
        else:
            self.assertIsNone(result['code']);self.assertEqual(len(calls),2)
            self.assertEqual(calls[1][2]['data'],payload);self.assertEqual(calls[1][2]['headers']['x-goog-user-project'],TARGET)
            self.assertEqual((directory/'provider-response.bin').read_bytes(),raw(response('gemini-3.8-flash')))
        self.assertTrue(all(r.closed for r in replies));self.assertTrue(all(not s.trust_env for s in sessions));self.assertTrue(all(s.closed for s in sessions))
        for p in directory.iterdir():
            if p.is_file():self.assertNotIn(b'FAKE_AUTH_BODY',p.read_bytes());self.assertNotIn(b'FAKE_ACCESS_TOKEN',p.read_bytes())


if __name__=='__main__':unittest.main()
