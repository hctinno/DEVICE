"""Protected UI checks with typed concrete dependency doubles; cloud calls0."""
from contextlib import contextmanager
import copy
import hashlib
import http.client
import importlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

from labflow.ui_server import create_server

MODELS = ('gemini-4-argon', 'gemini-3.8-flash')
TARGET = 'project-a6310591-f8cc-487c-9e3'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def default_profile():
    return dict(schema_version=1, profile_id='vertex-trial', provider='vertex_ai', project_id=TARGET,
                location='global', quota_project_id=TARGET, auth_profile_id='vertex-trial',
                selected_model=MODELS[1], models={m: dict(thinking_level='MEDIUM', max_output_tokens=512,
                timeout_seconds=60.0) for m in MODELS}, revision=0)


class TypedDependencies:
    """Only tests install these modules; production has no injection/fallback API."""
    def __init__(self):
        self.calls = []
        self.profiles = types.ModuleType('labflow.ai_connection_profiles')
        self.vertex = types.ModuleType('labflow.vertex_response')
        self.comparison = types.ModuleType('labflow.model_comparison')
        self.profiles.load_profile = self.load
        self.profiles.save_profile = self.save
        self.profiles.resolve_run_settings = self.resolve
        self.vertex.inspect_vertex_credentials = self.inspect
        self.comparison.build_vertex_comparison_matrix = self.build
        self.comparison.run_vertex_comparison_batch = self.run_batch
        self.comparison.run_vertex_comparison_row = self.run_row
        self.entered = threading.Event(); self.release = threading.Event(); self.release.set()
        self.cancel_seen = threading.Event()
        self.bad_binding = False
        self.bad_summary = False
        self.failure_code = None; self.raise_after_receipt = False; self.raised_error = None

    def load(self, path):
        self.calls.append('load')
        return json.loads(path.read_text()) if path.exists() else default_profile()

    def save(self, path, profile, *, expected_revision):
        self.calls.append('save')
        if self.load(path)['revision'] != expected_revision:
            raise ValueError('ai_connection_profile_revision_conflict')
        result = copy.deepcopy(profile); result['revision'] += 1
        path.write_bytes(canonical(result))
        return result

    def resolve(self, profile, *, model_id=None, overrides=None):
        model = model_id or profile['selected_model']
        values = dict(profile['models'][model]); values.update(overrides or {})
        out = {k: copy.deepcopy(profile[k]) for k in ('schema_version', 'profile_id', 'provider',
               'project_id', 'location', 'quota_project_id', 'auth_profile_id')}
        out.update(kind='ai_run_settings', profile_revision=profile['revision'], service='aiplatform.googleapis.com',
                   model_id=model, **values, profile_sha256=hashlib.sha256(canonical(profile)).hexdigest())
        out['settings_sha256'] = hashlib.sha256(canonical(out)).hexdigest()
        return out

    def inspect(self, path, *, settings):
        self.calls.append('inspect_metadata')
        if not path.is_file(): raise ValueError('vertex_response_credential_invalid')
        return dict(schema_version=1, kind='vertex_credentials_metadata', settings_sha256=settings['settings_sha256'],
                    auth_profile_id=settings['auth_profile_id'], credential_type='authorized_user', quota_project_id=TARGET,
                    token_endpoint='https://oauth2.googleapis.com/token', metadata_valid=True, refresh_attempted=False,
                    model_access_verified=False, credit_status_verified=False)

    def build(self, profile, prompt_bytes, response_schema_bytes, *, batch_id, scenario_id, evaluator_id,
              selection='matrix', model_id=None, overrides=None):
        self.calls.append('build_matrix'); rows=[]
        resolved=self.resolve(profile,model_id=model_id,overrides=overrides) if selection=='selected' else None
        indexes=list(range(6)) if selection=='matrix' else [MODELS.index(resolved['model_id'])*3+('LOW','MEDIUM','HIGH').index(resolved['thinking_level'])]
        for i in range(6):
            setting=self.resolve(profile,model_id=MODELS[i//3],overrides=dict(overrides or {},thinking_level=('LOW','MEDIUM','HIGH')[i%3])) if selection=='matrix' else resolved if i in indexes else None
            rows.append(dict(row_index=i,run_id=hashlib.sha256((batch_id+str(i)).encode()).hexdigest(),settings=copy.deepcopy(setting)))
        value=dict(schema_version=1,kind='vertex_comparison_matrix',batch_id=batch_id,scenario_id=scenario_id,evaluator_id=evaluator_id,
                   profile=copy.deepcopy(profile),binding=dict(profile_sha256=hashlib.sha256(canonical(profile)).hexdigest(),prompt_sha256=hashlib.sha256(prompt_bytes).hexdigest(),response_schema_sha256=hashlib.sha256(response_schema_bytes).hexdigest()),
                   limits=dict(generation_posts=6,max_output_tokens=512,reserved_output_tokens=3072,timeout_seconds=60,wall_seconds=300,retries=0,continuations=0),rows=rows,
                   selection=dict(mode=selection,model_id=model_id,overrides=copy.deepcopy(overrides),row_indexes=indexes))
        value['matrix_sha256']=hashlib.sha256(canonical(value)).hexdigest()
        return value

    def record(self,matrix,index,cancelled=False):
        slot=matrix['rows'][index]; settings=slot['settings']; attempted=settings is not None and not cancelled
        denied=attempted and (settings['max_output_tokens']>512 or settings['timeout_seconds']>60)
        if denied: attempted=False
        receipt=None
        if attempted:
            if self.failure_code != 'vertex_response_auth_failed':self.calls.append(('mock_wire',copy.deepcopy(settings)))
            receipt=dict(schema_version=1,kind='vertex_response_receipt',exchange_ref='vertex-exchange:'+'1'*32,status='complete',failure=None,
                         bindings=dict(prompt_sha256=matrix['binding']['prompt_sha256'],schema_sha256=matrix['binding']['response_schema_sha256'],provider_payload_sha256='2'*64,settings_sha256=settings['settings_sha256']),settings=copy.deepcopy(settings),
                         client=dict(transport='REST',api_version='v1',google_auth_version=None,requests_version=None,google_genai_used=False),
                         request=dict(method='POST',url='https://aiplatform.googleapis.com/v1/projects/'+TARGET+'/locations/global/publishers/google/models/'+settings['model_id']+':generateContent',quota_project_id=TARGET,auth_profile_id='vertex-trial'),
                         attempts=dict(worker_process_attempts=1,auth_refresh_attempts=1,auth_http_attempts=1,generation_post_attempts=1,auth_refresh_completed=True,auth_retry_blocked=False,application_retries=0),
                         response=dict(http_status=200,auth_http_status=200,finish_reason='STOP',reported_model_version='reported-version',provider_response_id='reported-id',text_parts=1,thought_parts=1),
                         usage={k:None for k in ('prompt_token_count','candidates_token_count','total_token_count','thoughts_token_count','cached_content_token_count','tool_use_prompt_token_count')},
                         cost=dict(kind='unknown',amount=None,currency=None,price_version=None),timing=dict(timeout_seconds=float(settings['timeout_seconds']),local_elapsed_seconds=.01),
                         cancellation=dict(requested=False,local_worker_stopped=True,provider_completion='observed_stop',remote_cancel_verified=False),
                         cleanup=dict(worker_reaped=True,transport_handles_closed=True,artifact_handles_closed=True,worker_exit_code=0,secondary_errors=[],remote_cancellation_verified=False),
                         artifacts={k:dict(path=p,present=True,bytes=1,sha256='3'*64,complete=True,overflow=False,extent='whole_file') for k,p in
                             [('prompt','request.json'),('response_schema','response-schema.json'),('settings','settings.json'),('provider_request','provider-request.json'),('provider_response','provider-response.bin'),('final_text','response-text.bin')]},
                         verification=dict(wire_complete=True,credential_metadata_verified=True,remote_identity_verified=False,semantic_quality_verified=False,credit_verified=False))
        binding=dict(scenario_id=matrix['scenario_id'],scenario_version=1,evaluator_id=matrix['evaluator_id'],evaluator_version=1,prompt_sha256=matrix['binding']['prompt_sha256'],schema_sha256=matrix['binding']['response_schema_sha256'],
                     profile_sha256=matrix['binding']['profile_sha256'],settings_sha256=settings['settings_sha256'] if settings else None,matrix_sha256=matrix['matrix_sha256'])
        if self.bad_binding: binding['matrix_sha256']='f'*64
        row=dict(schema_version=1,kind='vertex_comparison_row',batch_id=matrix['batch_id'],run_id=slot['run_id'],row_index=index,binding=binding,settings=copy.deepcopy(settings),execution_mode='mock',status='success' if attempted else 'not_run',
                    reason_code=None if attempted else 'cancelled' if cancelled and settings else 'budget_rejected' if denied else 'not_selected',receipt=receipt,strict_decode=dict(status='checked' if attempted else 'not_run',evaluator_id=matrix['evaluator_id'],error_code=None),
                    assessment=dict(status='not_assessed',verdict=None,reason_code='connection_only'),budget=dict(budget_id='SYN-BUDGET',reservation_id='SYN-RESERVATION' if attempted else None,reserved_calls=1 if attempted else 0,reserved_output_tokens=settings['max_output_tokens'] if attempted else 0,generation_post_attempts=1 if attempted else 0),
                    timing=dict(started_at=time.time(),finished_at=time.time(),elapsed_ms=10 if attempted else None))
        if receipt and self.failure_code:
            auth=self.failure_code=='vertex_response_auth_failed';count=0 if auth else 1
            receipt.update(status='failed',failure=dict(code=self.failure_code,phase='auth' if auth else 'extract'),usage=None)
            receipt['attempts'].update(generation_post_attempts=count,auth_refresh_completed=not auth)
            receipt['cost']['kind']='not_applicable' if count==0 else 'unknown'
            receipt['response'].update(http_status=None if auth else 200,finish_reason=None if auth else 'MAX_TOKENS',text_parts=0,thought_parts=0)
            receipt['verification']['wire_complete']=False
            for desc in receipt['artifacts'].values():desc.update(present=False,bytes=0,sha256=None,complete=False,overflow=False,extent='absent')
            row.update(status='failed',reason_code=self.failure_code,strict_decode=dict(status='not_run',evaluator_id=matrix['evaluator_id'],error_code=None))
            row['budget']['generation_post_attempts']=count
        return row

    def run_batch(self,matrix,prompt_bytes,response_schema_bytes,*,adc_path,evidence_dir,budget_path,approval_path,cancel_event=None):
        self.entered.set()
        while not self.release.wait(.01):
            if cancel_event.is_set(): self.cancel_seen.set(); break
        rows=[self.record(matrix,i,cancelled=cancel_event.is_set()) for i in range(6)]
        if self.raise_after_receipt:
            error=RuntimeError(self.failure_code);error.code=self.failure_code;error.receipt=next(r['receipt'] for r in rows if r['receipt'] is not None)
            self.raised_error=error;raise error
        result=dict(schema_version=1,kind='vertex_comparison_batch',batch_id=matrix['batch_id'],matrix_sha256=matrix['matrix_sha256'],execution_mode='mock',rows=rows,
                    summary=dict(planned_rows=6,selected_rows=len(matrix['selection']['row_indexes']),success_rows=sum(r['status']=='success' for r in rows),failed_rows=0,not_run_rows=sum(r['status']=='not_run' for r in rows),unknown_rows=0,
                                 cumulative_reserved_calls=6,cumulative_reserved_output_tokens=3072,generation_post_attempts=None,generation_post_attempts_known=False,generation_post_attempts_unknown_rows=0),business_assessment='not_assessed')
        if self.bad_summary:result['summary']['unexpected']=True
        return result

    def run_row(self,matrix,row_index,prompt_bytes,response_schema_bytes,**kwargs):
        return self.record(matrix,row_index)

    @contextmanager
    def installed(self):
        with patch.dict(sys.modules, {'labflow.ai_connection_profiles':self.profiles,
                                     'labflow.vertex_response':self.vertex,
                                     'labflow.model_comparison':self.comparison}):
            yield self


class AIConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vertex-ui-tests-')
        self.root = Path(self.temp.name).resolve()
        self.assertEqual(self.root.parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.root.name.startswith('vertex-ui-tests-'))
        self.addCleanup(self.temp.cleanup)
        self.dep = TypedDependencies()
        self.modules = self.dep.installed(); self.modules.__enter__(); self.addCleanup(self.modules.__exit__, None, None, None)
        self.config = dict(profile_path=self.root/'profile.json', adc_path=self.root/'adc.json',
                           approval_path=self.root/'approval.json', budget_path=self.root/'budget.json',
                           evidence_root=self.root/'evidence', scenarios=())

    def start(self, configured=True):
        try:
            server = create_server(self.root, port=0, **({'ai_connections':self.config} if configured else {}))
        except TypeError as error:
            self.fail('missing assigned ai_connections constructor: ' + str(error))
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':.01}, daemon=True); thread.start()
        def stop():
            address = server.server_address
            server.shutdown(); server.server_close(); thread.join(5)
            self.assertFalse(thread.is_alive()); self.assertEqual(server.socket.fileno(), -1)
            with socket.socket() as probe: probe.bind(address)
        self.addCleanup(stop)
        return server

    def request(self, server, path, method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection(*server.server_address, timeout=4)
        try:
            wire = canonical(body) if isinstance(body, dict) else body
            supplied = dict(headers or {})
            if body is not None: supplied.setdefault('Content-Type', 'application/json')
            connection.request(method, '/api/ai-connections/'+path, body=wire, headers=supplied)
            response = connection.getresponse(); data = response.read()
            return response.status, dict((k.lower(),v) for k,v in response.getheaders()), json.loads(data) if data else None
        finally: connection.close()

    def bootstrap(self, server):
        status, headers, body = self.request(server, 'session'); self.assertEqual(status, 200)
        self.assertEqual(set(body), {'schema_version','kind','capabilities','expires_at'})
        cookie = headers['set-cookie']
        for flag in ('Path=/api/ai-connections/', 'HttpOnly', 'SameSite=Strict', 'Max-Age=900'): self.assertIn(flag,cookie)
        self.assertEqual(len(headers['x-ai-connection-csrf']), 64)
        return {'Cookie':cookie.split(';')[0], 'X-AI-Connection-CSRF':headers['x-ai-connection-csrf'],
                'Origin':'http://127.0.0.1:'+str(server.server_port)}

    def ready(self, saved=True):
        prompt=b'{}'; schema=b'{"type":"object"}'
        self.config['scenarios']=(dict(scenario_id='SYN-CONNECTION',evaluator_id='connection-json-v1',prompt_bytes=prompt,response_schema_bytes=schema),)
        self.config['adc_path'].write_text('synthetic metadata marker',encoding='utf-8')
        limits=dict(generation_posts=6,max_output_tokens=512,reserved_output_tokens=3072,timeout_seconds=60,wall_seconds=300,retries=0,continuations=0)
        approval=dict(schema_version=1,kind='vertex_comparison_approval',approval_id='SYN-APPROVAL',scope_id='SYN-CONNECTION/v1',budget_id='SYN-BUDGET',project_id=TARGET,quota_project_id=TARGET,auth_profile_id='vertex-trial',scenario_id='SYN-CONNECTION',evaluator_id='connection-json-v1',prompt_sha256=hashlib.sha256(prompt).hexdigest(),response_schema_sha256=hashlib.sha256(schema).hexdigest(),execution_mode='actual',trial=dict(status='confirmed',source='root_console',observed_at=time.time(),credit_amount='1',credit_currency='KRW',remaining_days=90),limits=limits,issued_at=time.time()-1,expires_at=time.time()+300)
        self.config['approval_path'].write_bytes(canonical(approval))
        self.config['budget_path'].write_bytes(canonical(dict(schema_version=1,kind='vertex_comparison_budget',budget_id='SYN-BUDGET',project_id=TARGET,revision=0,call_limit=6,output_token_limit=3072,reserved_calls=0,reserved_output_tokens=0,active_run_id=None,entries=[])))
        if saved:
            profile=default_profile();profile['revision']=1;self.config['profile_path'].write_bytes(canonical(profile))

    def until_finished(self,server,headers,ident):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            status,_,value=self.request(server,'runs/'+ident,headers=headers)
            self.assertEqual(status,200)
            if value['state']=='finished': return value
            time.sleep(.01)
        self.fail('synthetic worker failed to finish')

    def test_none_is_explicitly_unconfigured_without_importing_dependencies(self):
        with patch('importlib.import_module',side_effect=AssertionError('None must not import optional modules')):
            server = self.start(False)
            status, _, value = self.request(server, 'session')
        self.assertEqual((status,value), (503,{'error':{'code':'ai_connection_ui_unconfigured'}}))
        self.assertEqual(self.dep.calls, [])

    def test_session_cookie_isolated_and_state_requires_private_nonce(self):
        server = self.start(); headers = self.bootstrap(server)
        self.assertEqual(self.request(server,'state')[0],403)
        status, _, state = self.request(server,'state',headers=headers)
        self.assertEqual(status,200); self.assertEqual(state['profile'],default_profile())
        self.assertEqual(state['auth']['state'],'missing'); self.assertFalse(state['gate']['run_allowed'])
        self.assertFalse(self.config['profile_path'].exists())

    def test_profile_cas_persists_both_models_and_float_settings_without_auth(self):
        server=self.start(); headers=self.bootstrap(server); profile=default_profile()
        profile['models'][MODELS[0]]['thinking_level']='LOW';profile['models'][MODELS[1]]['timeout_seconds']=1.5
        status,_,saved=self.request(server,'profile','POST',{'profile':profile,'expected_revision':0},headers)
        self.assertEqual(status,200);self.assertEqual(saved['profile']['revision'],1)
        self.assertEqual(saved['profile']['models'][MODELS[0]]['thinking_level'],'LOW')
        self.assertEqual(saved['profile']['models'][MODELS[1]]['timeout_seconds'],1.5)
        before=self.config['profile_path'].read_bytes()
        self.assertEqual(self.request(server,'profile','POST',{'profile':profile,'expected_revision':0},headers)[0],409)
        self.assertEqual(self.config['profile_path'].read_bytes(),before)

    def test_fixed_target_unknown_keys_and_untrusted_authority_are_rejected(self):
        server=self.start(); headers=self.bootstrap(server)
        profile=default_profile();profile['project_id']='different-project'
        self.assertEqual(self.request(server,'profile','POST',{'profile':profile,'expected_revision':0},headers)[0],400)
        request=dict(expected_revision=0,scenario_id='S01',model_id=None,overrides={},matrix=True,gate=True)
        self.assertEqual(self.request(server,'run','POST',request,headers)[0],400)
        self.assertNotIn('save',self.dep.calls)

    def test_strict_json_and_origin_are_checked_before_profile_or_run(self):
        server=self.start();headers=self.bootstrap(server);self.dep.calls.clear()
        self.assertEqual(self.request(server,'profile','POST',b'{"profile":{},"profile":{},"expected_revision":0}',headers)[0],400)
        self.assertEqual(self.request(server,'profile','POST',{},dict(headers,Origin='https://other.invalid'))[0],403)
        self.assertEqual(self.request(server,'state?x=1',headers=headers)[0],404)
        self.assertEqual(self.dep.calls,[])

    def test_missing_concrete_dependency_fails_without_fallback(self):
        server=self.start();headers=self.bootstrap(server)
        with patch.dict(sys.modules,{'labflow.ai_connection_profiles':None}):
            status,_,body=self.request(server,'state',headers=headers)
        self.assertEqual((status,body),(503,{'error':{'code':'ai_connection_ui_unavailable'}}))

    def test_revision_zero_run_is_explicitly_denied_before_runner(self):
        server=self.start();headers=self.bootstrap(server)
        status,_,body=self.request(server,'run','POST',dict(expected_revision=0,scenario_id='S01',model_id=None,overrides={},matrix=True),headers)
        self.assertEqual((status,body),(409,{'error':{'code':'ai_connection_ui_profile_not_saved'}}))

    def test_metadata_ready_is_not_auth_or_model_access_verified(self):
        self.config['adc_path'].write_text('synthetic metadata marker',encoding='utf-8')
        server=self.start();headers=self.bootstrap(server)
        status,_,state=self.request(server,'state',headers=headers)
        self.assertEqual(status,200);self.assertEqual(state['auth']['state'],'access_unknown')
        self.assertTrue(state['auth']['credential_file_ready']);self.assertFalse(state['gate']['run_allowed'])
        self.assertNotIn('produce',self.dep.calls)

    def test_saved_profile_override_reaches_typed_matrix_record_without_secret_projection(self):
        self.ready();server=self.start();headers=self.bootstrap(server)
        self.assertTrue(self.request(server,'state',headers=headers)[2]['gate']['run_allowed'])
        request=dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=MODELS[0],overrides={'thinking_level':'LOW','max_output_tokens':128,'timeout_seconds':1.5},matrix=False)
        status,_,value=self.request(server,'run','POST',request,headers);self.assertEqual(status,202)
        result=self.until_finished(server,headers,value['run_id']);self.assertEqual(len(result['cells']),6)
        selected=[c for c in result['cells'] if c['state']=='success'];self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]['settings']['timeout_seconds'],1.5);self.assertEqual(selected[0]['settings']['max_output_tokens'],128)
        self.assertEqual(result['execution_mode'],'mock');self.assertIsNone(selected[0]['cost'])
        self.assertEqual(selected[0]['quality'],'not_run')
        self.assertNotIn('provider-response.bin',json.dumps(result));self.assertNotIn('vertex-exchange:',json.dumps(result))
        self.assertEqual(self.dep.load(self.config['profile_path'])['models'][MODELS[0]]['max_output_tokens'],512)

    def test_matrix_flat_override_and_selected_five_not_selected(self):
        self.ready();server=self.start();headers=self.bootstrap(server)
        request=dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=None,overrides={'max_output_tokens':256},matrix=True)
        status,_,value=self.request(server,'run','POST',request,headers);self.assertEqual(status,202)
        result=self.until_finished(server,headers,value['run_id'])
        self.assertEqual([c['thinking_level'] for c in result['cells']],['LOW','MEDIUM','HIGH']*2)
        self.assertTrue(all(c['settings']['max_output_tokens']==256 for c in result['cells']))
        request['overrides']['thinking_level']='HIGH'
        self.assertEqual(self.request(server,'run','POST',request,headers)[0],400)

    def test_status_and_cancel_never_wait_for_active_run_slot_or_allow_other_session(self):
        self.ready();self.dep.release.clear();server=self.start();headers=self.bootstrap(server);other=self.bootstrap(server)
        request=dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=None,overrides={},matrix=True)
        status,_,value=self.request(server,'run','POST',request,headers);self.assertEqual(status,202);self.assertTrue(self.dep.entered.wait(1))
        self.assertEqual(self.request(server,'run','POST',request,headers)[0],429)
        self.assertEqual(self.request(server,'runs/'+value['run_id'],headers=other)[0],404)
        self.assertEqual(self.request(server,'cancel','POST',{'run_id':value['run_id']},other)[0],404)
        before=time.monotonic();self.assertEqual(self.request(server,'cancel','POST',{'run_id':value['run_id']},headers)[0],200)
        self.assertLess(time.monotonic()-before,1);self.assertTrue(self.dep.cancel_seen.wait(1))
        self.until_finished(server,headers,value['run_id']);self.dep.release.set()

    def test_bad_typed_result_is_not_published_as_success(self):
        self.ready();server=self.start();headers=self.bootstrap(server)
        for fault in ('bad_binding','bad_summary'):
            self.dep.bad_binding=self.dep.bad_summary=False;setattr(self.dep,fault,True)
            status,_,value=self.request(server,'run','POST',dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=None,overrides={},matrix=True),headers)
            self.assertEqual(status,202);result=self.until_finished(server,headers,value['run_id'])
            with self.subTest(fault=fault):
                self.assertEqual(result['error_code'],'ai_connection_ui_unavailable');self.assertFalse(any(c['state']=='success' for c in result['cells']))

    def test_missing_D2_is_unavailable_not_fake_missing_auth(self):
        self.config['adc_path'].write_text('synthetic marker',encoding='utf-8')
        server=self.start();headers=self.bootstrap(server)
        with patch.dict(sys.modules,{'labflow.vertex_response':None}):
            status,_,body=self.request(server,'state',headers=headers)
        self.assertEqual((status,body),(503,{'error':{'code':'ai_connection_ui_unavailable'}}))

    def test_close_has_five_second_bound_and_does_not_claim_live_worker_closed(self):
        runtime=importlib.import_module('labflow.ai_connection_ui').AIConnectionRuntime(self.config)
        entered=threading.Event();release=threading.Event()
        worker=threading.Thread(target=lambda:(entered.set(),release.wait()),daemon=True)
        runtime.worker=worker;worker.start();self.assertTrue(entered.wait(1))
        before=time.monotonic()
        try:
            with self.assertRaisesRegex(ValueError,'ai_connection_ui_close_unconfirmed'):runtime.close()
            self.assertLess(time.monotonic()-before,5.8);self.assertTrue(worker.is_alive());self.assertFalse(runtime.closed)
        finally:release.set();worker.join(1)
        runtime.close();self.assertFalse(worker.is_alive())

    def test_unadmitted_approval_and_corrupt_ledger_never_show_ready_gate(self):
        self.ready();server=self.start();headers=self.bootstrap(server)
        approval=json.loads(self.config['approval_path'].read_text());budget=json.loads(self.config['budget_path'].read_text())
        for mutation in ('wrong_scope','bool_limit','corrupt_entry'):
            a=copy.deepcopy(approval);b=copy.deepcopy(budget)
            if mutation=='wrong_scope':a['scope_id']='unrelated-scope'
            if mutation=='bool_limit':a['limits']['retries']=False
            if mutation=='corrupt_entry':b['entries']=[{'unexpected':'record'}]
            self.config['approval_path'].write_bytes(canonical(a));self.config['budget_path'].write_bytes(canonical(b))
            with self.subTest(mutation=mutation):self.assertFalse(self.request(server,'state',headers=headers)[2]['gate']['run_allowed'])

    def test_worker_start_failure_releases_reservation_and_expiry_timer(self):
        self.ready();server=self.start();headers=self.bootstrap(server);original=threading.Thread.start
        def fail_worker(thread):
            if thread.name=='ai-connection-run':raise RuntimeError('synthetic thread start failure')
            return original(thread)
        with patch.object(threading.Thread,'start',fail_worker):
            status,_,body=self.request(server,'run','POST',dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=None,overrides={},matrix=True),headers)
        self.assertEqual((status,body),(503,{'error':{'code':'ai_connection_ui_unavailable'}}))
        rt=server._ai_connection_runtime;self.assertIsNone(rt.active);self.assertIsNone(rt.worker)
        self.assertEqual(rt.runs,{})

    def test_server_close_stops_own_serve_loop_without_separate_shutdown(self):
        server=self.start();self.bootstrap(server)
        server.server_close()
        self.assertIsNone(server._ai_connection_runtime.loop_thread)
        self.assertTrue(server._ai_connection_runtime.closed)

    def test_session_GET_body_is_rejected_before_issuing_nonce(self):
        server=self.start();status,headers,_=self.request(server,'session',body=b'x')
        self.assertEqual(status,400);self.assertNotIn('set-cookie',headers)
        self.assertEqual(server._ai_connection_runtime.sessions,{})

    def test_missing_D3_is_an_explicit_failure_without_leaving_an_active_slot(self):
        self.ready();server=self.start();headers=self.bootstrap(server)
        with patch.dict(sys.modules,{'labflow.model_comparison':None}):
            status,_,body=self.request(server,'run','POST',dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=None,overrides={},matrix=True),headers)
        self.assertEqual((status,body),(503,{'error':{'code':'ai_connection_ui_unavailable'}}))
        self.assertIsNone(server._ai_connection_runtime.active)

    def test_failed_D2_receipt_absent_bytes_zero_and_known_attempts_are_preserved(self):
        self.ready();server=self.start();headers=self.bootstrap(server)
        for code,count in [('vertex_response_auth_failed',0),('vertex_response_incomplete',1)]:
            self.dep.failure_code=code
            status,_,value=self.request(server,'run','POST',dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=MODELS[1],overrides={},matrix=False),headers)
            self.assertEqual(status,202);result=self.until_finished(server,headers,value['run_id'])
            selected=next(c for c in result['cells'] if c['settings'] is not None)
            with self.subTest(code=code):
                self.assertIsNone(result['error_code']);self.assertEqual(result['attempts_used'],count)
                self.assertEqual(selected['state'],'failure');self.assertEqual(selected['reason_code'],code)
                self.assertIsNone(selected['usage']);self.assertIsNone(selected['cost']);self.assertEqual(selected['attempted'],bool(count))
                self.assertNotIn('artifacts',json.dumps(result))

    def test_original_D2_exception_receipt_is_kept_private_when_row_recording_fails(self):
        self.ready();self.dep.failure_code='vertex_response_auth_failed';self.dep.raise_after_receipt=True
        server=self.start();headers=self.bootstrap(server)
        status,_,value=self.request(server,'run','POST',dict(expected_revision=1,scenario_id='SYN-CONNECTION',model_id=MODELS[1],overrides={},matrix=False),headers)
        self.assertEqual(status,202);result=self.until_finished(server,headers,value['run_id'])
        self.assertEqual(result['error_code'],'vertex_response_auth_failed');self.assertIsNone(result['attempts_used'])
        self.assertIs(server._ai_connection_runtime.runs[value['run_id']]['failure'],self.dep.raised_error)
        self.assertNotIn('provider-response.bin',json.dumps(result));self.assertEqual(next(c for c in result['cells'] if c['settings'])['state'],'unknown')


if __name__=='__main__': unittest.main()
