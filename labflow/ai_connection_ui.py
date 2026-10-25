"""Optional, isolated local UI facade for registered Vertex synthetic tests."""
from contextlib import suppress
from datetime import datetime
from decimal import Decimal, InvalidOperation
import copy
import hashlib
import hmac
import importlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import sys
import threading
import time

PREFIX = '/api/ai-connections/'
MODELS = ('gemini-4-argon', 'gemini-3.8-flash')
TARGET = 'project-a6310591-f8cc-487c-9e3'
CAPABILITIES = ('read_profile', 'edit_profile', 'run_registered_synthetic', 'cancel_own')
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_D3_RUN_ID = re.compile(r'vertex-run:[a-f0-9]{64}\Z')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z')
_PROFILE = frozenset('schema_version profile_id provider project_id location quota_project_id auth_profile_id selected_model models revision'.split())
_SETTINGS = frozenset('schema_version kind profile_id profile_revision provider service project_id location quota_project_id auth_profile_id model_id thinking_level max_output_tokens timeout_seconds profile_sha256 settings_sha256'.split())
_RECEIPT = frozenset('schema_version kind exchange_ref status failure bindings settings client request attempts response usage cost timing cancellation cleanup artifacts verification'.split())
_USAGE = ('prompt_token_count','candidates_token_count','total_token_count','thoughts_token_count','cached_content_token_count','tool_use_prompt_token_count')
_LIMITS = dict(generation_posts=6,max_output_tokens=512,reserved_output_tokens=3072,timeout_seconds=60,wall_seconds=300,retries=0,continuations=0)
_PUBLIC_FAILURES = frozenset({'ai_connection_ui_unavailable'} | {'vertex_response_'+s for s in
    'invalid_input invalid_settings credential_invalid credential_quota_mismatch dependency_unavailable evidence_error auth_failed http_error response_invalid incomplete blocked limit_exceeded timeout cancelled cleanup_failed internal_error'.split()} |
    {'model_comparison_'+s for s in 'invalid_input limit_exceeded state_error dependency_unavailable'.split()})
_REASONS = frozenset('not_selected cancelled budget_rejected wall_limit gate_rejected dependency_unavailable credential_metadata_invalid budget_unavailable run_already_reserved budget_busy receipt_invalid connection_verified connection_response_invalid batch_stopped'.split())
_REASONS |= frozenset(('intake_response_verified','intake_response_invalid','intent_response_verified','intent_response_invalid'))
_SCENARIOS = {
    'DGM-AI-CONNECTION-001': ('connection-json-v1','연결 응답 형상','connection_verified','connection_response_invalid','connection_only'),
    **dict.fromkeys(('intake-synthetic-s01','intake-synthetic-s02','intake-synthetic-s03'),
        ('intake-understanding-v1','접수 분석','intake_response_verified','intake_response_invalid','semantic_evaluator_not_connected')),
    **dict.fromkeys(('intent-synthetic-i01','intent-synthetic-i02','intent-synthetic-i03'),
        ('intake-test-intent-semantic-v1','의뢰 이해 후보','intent_response_verified','intent_response_invalid','semantic_evaluator_not_connected')),
}
_STRICT_REASONS = frozenset(value for item in _SCENARIOS.values() for value in item[2:4])


def _scenario(scenario_id, evaluator_id):
    item=_SCENARIOS.get(scenario_id) if type(scenario_id) is str else None
    return item if item is not None and item[0]==evaluator_id else None


class AIConnectionUIError(ValueError):
    def __init__(self, suffix='unavailable', status=503):
        self.code, self.status = 'ai_connection_ui_' + suffix, status
        super().__init__(self.code)


def _need(value, suffix='invalid_request', status=400):
    if not value:
        raise AIConnectionUIError(suffix, status)


def _keys(value, names):
    _need(type(value) is dict and set(value) == set(names))


def _integer(value, low=0, high=2**53-1):
    return type(value) is int and low <= value <= high


def _number(value, low=0, high=2**53-1):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _json(raw, maximum=32768):
    _need(type(raw) is bytes and len(raw) <= maximum, 'input_limit', 413)
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result); result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        nodes = 0
        def visit(item, depth=0):
            nonlocal nodes
            nodes += 1; _need(depth <= 8 and nodes <= 2048, 'input_limit', 413)
            if type(item) is dict:
                for key, child in item.items(): key.encode('utf-8'); visit(child, depth+1)
            elif type(item) is list:
                for child in item: visit(child, depth+1)
            elif type(item) is str: item.encode('utf-8')
            elif item is None or type(item) is bool: pass
            else: _need(_number(item, -2**53+1))
        visit(value)
        return value
    except AIConnectionUIError:
        raise
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        pass
    raise AIConnectionUIError('invalid_request', 400)


def _profile(value):
    _keys(value, _PROFILE)
    _need(type(value['schema_version']) is int and value['schema_version'] == 1 and
          value['profile_id'] == value['auth_profile_id'] == 'vertex-trial' and value['provider'] == 'vertex_ai' and
          value['project_id'] == value['quota_project_id'] == TARGET and value['location'] in ('global','us','eu') and
          value['selected_model'] in MODELS and _integer(value['revision']))
    _keys(value['models'], MODELS)
    for item in value['models'].values():
        _keys(item, ('thinking_level','max_output_tokens','timeout_seconds'))
        _need(item['thinking_level'] in ('LOW','MEDIUM','HIGH') and _integer(item['max_output_tokens'],64,8192) and
              _number(item['timeout_seconds'],1,120))
    return copy.deepcopy(value)


def _settings(value):
    _keys(value, _SETTINGS)
    _need(value['schema_version'] == 1 and type(value['schema_version']) is int and value['kind'] == 'ai_run_settings' and
          value['profile_id'] == value['auth_profile_id'] == 'vertex-trial' and value['provider'] == 'vertex_ai' and
          value['service'] == 'aiplatform.googleapis.com' and value['project_id'] == value['quota_project_id'] == TARGET and
          value['location'] in ('global','us','eu') and value['model_id'] in MODELS and _integer(value['profile_revision']) and
          value['thinking_level'] in ('LOW','MEDIUM','HIGH') and _integer(value['max_output_tokens'],64,8192) and
          _number(value['timeout_seconds'],1,120) and type(value['profile_sha256']) is str and _SHA.fullmatch(value['profile_sha256']) and
          type(value['settings_sha256']) is str and _SHA.fullmatch(value['settings_sha256']))
    _need(hashlib.sha256(_canonical({k:v for k,v in value.items() if k != 'settings_sha256'})).hexdigest() == value['settings_sha256'])
    return copy.deepcopy(value)


def _module(name):
    try:
        return importlib.import_module('.' + name, __package__)
    except Exception:
        pass
    raise AIConnectionUIError()


def _private_path(value):
    _need(type(value) is type(Path()) and value.is_absolute() and '..' not in value.parts)
    for part in (value, *value.parents):
        try: info = part.lstat()
        except FileNotFoundError: continue
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes',0) & 0x400)
    return value


class AIConnectionRuntime:
    def __init__(self, config):
        _keys(config, ('profile_path','adc_path','approval_path','budget_path','evidence_root','scenarios'))
        self.paths = {k:_private_path(config[k]) for k in config if k != 'scenarios'}
        _need(len(set(os.path.normcase(str(p)) for p in self.paths.values())) == 5)
        _need(type(config['scenarios']) is tuple and len(config['scenarios']) <= 128)
        self.scenarios = {}
        for item in config['scenarios']:
            _keys(item, ('scenario_id','evaluator_id','prompt_bytes','response_schema_bytes'))
            _need(type(item['scenario_id']) is str and _ID.fullmatch(item['scenario_id']) and
                  type(item['evaluator_id']) is str and _ID.fullmatch(item['evaluator_id']) and
                  item['scenario_id'] not in self.scenarios)
            _need(type(item['prompt_bytes']) is bytes and len(item['prompt_bytes']) <= 262144 and
                  type(item['response_schema_bytes']) is bytes and len(item['response_schema_bytes']) <= 65536)
            self.scenarios[item['scenario_id']] = dict(item)
        self.lock = threading.RLock()
        self.sessions, self.runs, self.clients = {}, {}, set()
        self.request_workers=set();self.server_errors=[];self.loop_failure=False
        self.active = None; self.worker = None; self.closing = self.closed = False
        self.loop_thread = None

    def _guard(self, handler):
        host = handler.headers.get_all('Host', [])
        origin = handler.headers.get_all('Origin', [])
        fetch = handler.headers.get_all('Sec-Fetch-Site', [])
        _need(len(host) == 1 and host[0] in {f'127.0.0.1:{handler.server.server_port}',f'localhost:{handler.server.server_port}'} and
              len(origin) <= 1 and (not origin or origin[0] == 'http://' + host[0]) and
              len(fetch) <= 1 and (not fetch or fetch[0] in ('same-origin','none')), 'access_denied',403)

    def _session(self, handler, bootstrap=False):
        cookies = handler.headers.get_all('Cookie', [])
        _need(len(cookies) <= 1, 'access_denied',403)
        name = 'dgm_ai_connection_' + str(handler.server.server_port)
        values = [p.strip().split('=',1)[1] for p in (cookies[0].split(';') if cookies else []) if p.strip().startswith(name+'=')]
        _need(len(values) <= 1, 'access_denied',403)
        now = time.monotonic()
        with self.lock:
            _need(not self.closing, 'unavailable',503)
            for key, item in list(self.sessions.items()):
                if now >= item['deadline']:
                    if self.active and self.runs[self.active]['owner'] == key: self.runs[self.active]['cancel'].set()
                    if not self.active or self.runs[self.active]['owner'] != key:
                        self.sessions.pop(key)
                        self.runs = {rid:run for rid,run in self.runs.items() if run['owner'] != key}
            sid = values[0] if values else None
            item = self.sessions.get(sid)
            if item is not None and now >= item['deadline']: item = None
            if bootstrap:
                if item is None:
                    _need(len(self.sessions) < 128, 'session_unavailable',503)
                    sid = secrets.token_hex(32); item = dict(csrf=secrets.token_hex(32),deadline=now+900,expires=time.time()+900)
                    self.sessions[sid] = item
                    cookie = f'{name}={sid}; Path={PREFIX}; HttpOnly; SameSite=Strict; Max-Age=900'
                else: cookie = None
                return sid, item, cookie
            tokens = handler.headers.get_all('X-AI-Connection-CSRF', [])
            _need(item is not None and len(tokens) == 1 and type(tokens[0]) is str and
                  _SHA.fullmatch(tokens[0]) and hmac.compare_digest(tokens[0],item['csrf']), 'access_denied',403)
            return sid, item, None

    def _load(self):
        try: return _profile(_module('ai_connection_profiles').load_profile(self.paths['profile_path']))
        except AIConnectionUIError as error:
            if error.status == 503: raise
        except Exception: pass
        raise AIConnectionUIError()

    def _auth(self, profile):
        if not self.paths['adc_path'].is_file(): return dict(state='missing',credential_file_ready=False,checked_at=None)
        try:
            settings = _settings(_module('ai_connection_profiles').resolve_run_settings(profile))
            result = _module('vertex_response').inspect_vertex_credentials(self.paths['adc_path'],settings=settings)
            _keys(result,'schema_version kind settings_sha256 auth_profile_id credential_type quota_project_id token_endpoint metadata_valid refresh_attempted model_access_verified credit_status_verified'.split())
            _need(result['metadata_valid'] is True and result['refresh_attempted'] is False and result['model_access_verified'] is False and
                  result['credit_status_verified'] is False and result['settings_sha256'] == settings['settings_sha256'] and
                  result['quota_project_id'] == TARGET and result['auth_profile_id'] == 'vertex-trial')
            return dict(state='access_unknown',credential_file_ready=True,checked_at=time.time())
        except Exception as error:
            code=getattr(error,'code',str(error))
            if code not in ('vertex_response_credential_invalid','vertex_response_credential_quota_mismatch'):
                raise AIConnectionUIError() from None
            mismatch = code == 'vertex_response_credential_quota_mismatch'
        return dict(state='other_quota' if mismatch else 'missing',credential_file_ready=False,checked_at=time.time())

    def _policy(self, profile, auth, scenario_id=None):
        # Read-only UI projection. D3 independently admits and reserves the authoritative files.
        trial=dict(state='unknown',checked_at=None)
        budget=dict(limit_calls=6,reserved_calls=None,remaining_calls=None,limit_output_tokens=3072,reserved_output_tokens=None,wall_budget_seconds=300)
        reasons=[]
        def read(name):
            path=_private_path(self.paths[name]); _need(path.is_file())
            with path.open('rb') as stream: raw=stream.read(65537)
            return _json(raw,65536)
        def timestamp(value):
            if _number(value): return value
            _need(type(value) is str)
            parsed=datetime.fromisoformat(value.replace('Z','+00:00')); _need(parsed.tzinfo is not None)
            return parsed.timestamp()
        try:
            approval=read('approval_path')
            _keys(approval,'schema_version kind approval_id scope_id budget_id project_id quota_project_id auth_profile_id scenario_id evaluator_id prompt_sha256 response_schema_sha256 execution_mode trial limits issued_at expires_at'.split())
            _need(approval['schema_version']==1 and type(approval['schema_version']) is int and approval['kind']=='vertex_comparison_approval' and
                  approval['project_id']==approval['quota_project_id']==TARGET and approval['auth_profile_id']=='vertex-trial' and approval['execution_mode']=='actual')
            scenario=self.scenarios[approval['scenario_id']]
            _need(_scenario(scenario['scenario_id'],scenario['evaluator_id']) is not None and
                  (scenario_id is None or approval['scenario_id']==scenario_id))
            _need(all(type(approval[k]) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',approval[k])
                      for k in ('approval_id','scope_id','budget_id')))
            _need(approval['evaluator_id']==scenario['evaluator_id'] and approval['prompt_sha256']==hashlib.sha256(scenario['prompt_bytes']).hexdigest() and
                  approval['response_schema_sha256']==hashlib.sha256(scenario['response_schema_bytes']).hexdigest() and approval['limits']==_LIMITS)
            _keys(approval['limits'],_LIMITS)
            _need(all((type(v) in (int,float) and type(v) is not bool if k=='timeout_seconds' else type(v) is int) and v==_LIMITS[k] for k,v in approval['limits'].items()))
            declared=approval['trial'];_keys(declared,('status','source','observed_at','credit_amount','credit_currency','remaining_days'))
            _need(declared['status']=='confirmed' and declared['source']=='root_console' and type(declared['credit_amount']) is str and
                  Decimal(declared['credit_amount']).is_finite() and Decimal(declared['credit_amount'])>0 and _number(declared['remaining_days'],1,1000))
            issued,expires=timestamp(approval['issued_at']),timestamp(approval['expires_at'])
            _need(issued<=time.time() and issued<expires and expires-issued<=86400)
            trial=dict(state='confirmed' if time.time()<expires else 'approval_expired',checked_at=timestamp(declared['observed_at']))
            if trial['state']!='confirmed': reasons.append('approval_expired')
        except Exception:
            approval=None;reasons.append('trial_unconfirmed')
        try:
            ledger=read('budget_path')
            _keys(ledger,'schema_version kind budget_id project_id revision call_limit output_token_limit reserved_calls reserved_output_tokens active_run_id entries'.split())
            _need(ledger['schema_version']==1 and type(ledger['schema_version']) is int and ledger['kind']=='vertex_comparison_budget' and ledger['project_id']==TARGET and
                  ledger['call_limit']==6 and ledger['output_token_limit']==3072 and _integer(ledger['revision']) and
                  _integer(ledger['reserved_calls'],0,6) and _integer(ledger['reserved_output_tokens'],0,3072) and type(ledger['entries']) is list and
                  (approval is None or ledger['budget_id']==approval['budget_id']))
            _need(len(ledger['entries'])==ledger['reserved_calls'] and (ledger['active_run_id'] is None or type(ledger['active_run_id']) is str and len(ledger['active_run_id'])<=128))
            reservations=set();output=0
            for entry in ledger['entries']:
                _keys(entry,'reservation_id batch_id run_id row_index matrix_sha256 settings_sha256 output_tokens state record_ref receipt_ref'.split())
                _need(type(entry['reservation_id']) is str and entry['reservation_id'] not in reservations and _integer(entry['row_index'],0,5) and
                      type(entry['run_id']) is str and _D3_RUN_ID.fullmatch(entry['run_id']) and
                      all(type(entry[k]) is str and _SHA.fullmatch(entry[k]) for k in ('matrix_sha256','settings_sha256')) and
                      _integer(entry['output_tokens'],64,8192) and entry['state'] in ('reserved','complete','failed','unknown') and
                      all(entry[k] is None or type(entry[k]) is str and len(entry[k])<=4096 for k in ('record_ref','receipt_ref')))
                reservations.add(entry['reservation_id']);output+=entry['output_tokens']
            _need(output==ledger['reserved_output_tokens'])
            budget.update(reserved_calls=ledger['reserved_calls'],remaining_calls=6-ledger['reserved_calls'],reserved_output_tokens=ledger['reserved_output_tokens'])
            if ledger['reserved_calls']>=6 or ledger['reserved_output_tokens']>=3072: reasons.append('budget_exhausted')
            if ledger['active_run_id'] is not None: reasons.append('busy')
        except Exception: reasons.append('budget_unavailable')
        return trial,budget,reasons

    def _state(self, owner):
        profile = self._load(); auth = self._auth(profile); trial,budget,reasons = self._policy(profile,auth)
        if not auth['credential_file_ready']: reasons.insert(0,'quota_mismatch' if auth['state']=='other_quota' else 'credential_missing')
        if profile['revision'] == 0: reasons.append('profile_not_saved')
        if not any(_scenario(s['scenario_id'],s['evaluator_id']) for s in self.scenarios.values()): reasons.append('scenario_unavailable')
        with self.lock:
            if self.active: reasons.append('busy')
            own = [r['view'] for r in self.runs.values() if r['owner'] == owner and r['view'] is not None]
            active = self.active if self.active and self.runs[self.active]['owner'] == owner and self.runs[self.active]['view'] is not None else None
        return dict(schema_version=1,kind='ai_connection_state',profile=profile,
                    catalog=dict(locations=['global','us','eu'],model_ids=list(MODELS),thinking_levels=['LOW','MEDIUM','HIGH'],
                                 defaults=dict(thinking_level='MEDIUM',max_output_tokens=512,timeout_seconds=60),
                                 ranges=dict(max_output_tokens=[64,8192],timeout_seconds=[1,120])),
                    capabilities=list(CAPABILITIES),auth=auth,trial=trial,budget=budget,gate=dict(run_allowed=not reasons,reasons=list(dict.fromkeys(reasons))),
                    scenarios=[dict(scenario_id=i['scenario_id'],label=((_scenario(i['scenario_id'],i['evaluator_id']) or (None,'미지원'))[1]+' · '+i['scenario_id']),input_sha256=hashlib.sha256(i['prompt_bytes']).hexdigest(),
                                    schema_sha256=hashlib.sha256(i['response_schema_bytes']).hexdigest(),evaluator_id=i['evaluator_id']) for i in self.scenarios.values()],
                    active_run_id=active,recent_runs=[{k:v[k] for k in ('run_id','state','matrix','scenario_id','created_at','finished_at')} for v in own[-16:]])

    def _save(self, owner, request):
        _keys(request,('profile','expected_revision')); profile=_profile(request['profile'])
        _need(_integer(request['expected_revision']) and profile['revision'] == request['expected_revision'])
        with self.lock:
            _need(not self.active, 'busy',429)
            if getattr(self,'saving',False): raise AIConnectionUIError('busy',429)
            self.saving = True
        try:
            current = self._load()
            _need(current['revision'] == request['expected_revision'], 'revision_conflict',409)
            try: saved = _module('ai_connection_profiles').save_profile(self.paths['profile_path'], profile, expected_revision=request['expected_revision'])
            except Exception as error:
                code = getattr(error,'code',str(error))
                if code in ('ai_connection_profile_revision_conflict','ai_connection_profiles_revision_conflict'): raise AIConnectionUIError('revision_conflict',409) from None
                raise AIConnectionUIError() from None
            _need(_profile(saved)['revision'] == profile['revision']+1, 'unavailable',503)
        finally:
            with self.lock: self.saving = False
        return self._state(owner)

    def _start(self, owner, request):
        _keys(request,('expected_revision','scenario_id','model_id','overrides','matrix'))
        _need(_integer(request['expected_revision']) and type(request['matrix']) is bool and type(request['scenario_id']) is str and _ID.fullmatch(request['scenario_id']))
        _need(type(request['overrides']) is dict and set(request['overrides']) <= ({'max_output_tokens','timeout_seconds'} if request['matrix'] else {'thinking_level','max_output_tokens','timeout_seconds'}))
        _need(request['model_id'] is None if request['matrix'] else request['model_id'] in MODELS)
        for key,value in request['overrides'].items():
            _need(value in ('LOW','MEDIUM','HIGH') if key=='thinking_level' else _integer(value,64,8192) if key=='max_output_tokens' else _number(value,1,120))
        profile=self._load()
        _need(profile['revision'] >= 1,'profile_not_saved',409)
        _need(profile['revision'] == request['expected_revision'],'revision_conflict',409)
        return self._start_registered(owner,request,profile)

    def _start_registered(self, owner, request, profile):
        _need(request['scenario_id'] in self.scenarios)
        scenario=self.scenarios[request['scenario_id']]
        _need(_scenario(scenario['scenario_id'],scenario['evaluator_id']) is not None)
        with self.lock:
            _need(not self.closing,'unavailable',503)
            _need(self.active is None and not getattr(self,'saving',False),'busy',429)
            _need(len(self.runs)<128 and sum(r['owner']==owner for r in self.runs.values())<16,'input_limit',413)
            rid=secrets.token_hex(32);self.active=rid
            self.runs[rid]=dict(owner=owner,cancel=threading.Event(),view=None,matrix=None)
        try:
            module=_module('model_comparison')
            _need(callable(getattr(module,'build_vertex_comparison_matrix',None)) and callable(getattr(module,'run_vertex_comparison_batch',None)),'unavailable',503)
            auth=self._auth(profile);_,_,reasons=self._policy(profile,auth,request['scenario_id'])
            _need(auth['credential_file_ready'] and not reasons,'gate_blocked',409)
            scenario=self.scenarios[request['scenario_id']]
            matrix=module.build_vertex_comparison_matrix(profile,scenario['prompt_bytes'],scenario['response_schema_bytes'],batch_id='AIUI-'+secrets.token_hex(16),
                    scenario_id=scenario['scenario_id'],evaluator_id=scenario['evaluator_id'],selection='matrix' if request['matrix'] else 'selected',
                    model_id=request['model_id'],overrides=copy.deepcopy(request['overrides']))
            self._matrix(matrix,profile,scenario,request)
            view=dict(schema_version=1,kind='ai_connection_run',run_id=rid,profile_revision=profile['revision'],scenario_id=scenario['scenario_id'],
                      scenario_sha256=matrix['binding']['prompt_sha256'],input_kind='registered_synthetic',execution_mode=None,state='queued',matrix=request['matrix'],
                      created_at=time.time(),finished_at=None,cancel_requested=False,attempts_used=0,cells=self._planned(matrix),error_code=None)
            with self.lock:
                _need(not self.closing and owner in self.sessions and self.sessions[owner]['deadline']>time.monotonic(),'unavailable',503)
                run=self.runs[rid];run.update(matrix=copy.deepcopy(matrix),view=view)
                timer=threading.Timer(max(0,self.sessions[owner]['deadline']-time.monotonic()),run['cancel'].set);timer.daemon=True;run['timer']=timer
                worker=threading.Thread(target=self._work,args=(rid,module,scenario),name='ai-connection-run',daemon=True)
                run['thread']=worker;self.worker=worker
                response=copy.deepcopy(view)
                timer.start();worker.start()
                return response
        except BaseException:
            with self.lock:
                run=self.runs.get(rid);timer=run.get('timer') if run else None;worker=run.get('thread') if run else None
                if timer:timer.cancel()
                if worker and worker.ident is not None:
                    run['cancel'].set()
                else:
                    self.runs.pop(rid,None)
                    if self.active==rid:self.active=None
                    if self.worker is worker:self.worker=None
            if timer and timer.ident is not None:timer.join(.5)
            raise

    def _matrix(self, matrix, profile, scenario, request):
        _keys(matrix,'schema_version kind batch_id scenario_id evaluator_id profile binding limits rows selection matrix_sha256'.split())
        _need(matrix['schema_version']==1 and type(matrix['schema_version']) is int and matrix['kind']=='vertex_comparison_matrix' and matrix['profile']==profile and
              matrix['scenario_id']==scenario['scenario_id'] and matrix['evaluator_id']==scenario['evaluator_id'] and matrix['limits']==_LIMITS)
        _keys(matrix['binding'],('profile_sha256','prompt_sha256','response_schema_sha256'))
        _need(matrix['binding']==dict(profile_sha256=hashlib.sha256(_canonical(profile)).hexdigest(),prompt_sha256=hashlib.sha256(scenario['prompt_bytes']).hexdigest(),response_schema_sha256=hashlib.sha256(scenario['response_schema_bytes']).hexdigest()))
        _need(type(matrix['matrix_sha256']) is str and _SHA.fullmatch(matrix['matrix_sha256']) and
              matrix['matrix_sha256']==hashlib.sha256(_canonical({k:v for k,v in matrix.items() if k!='matrix_sha256'})).hexdigest())
        _keys(matrix['selection'],('mode','model_id','overrides','row_indexes'))
        selected=matrix['selection'];_need(selected['mode']==('matrix' if request['matrix'] else 'selected') and selected['model_id']==request['model_id'] and selected['overrides']==request['overrides'])
        _need(type(matrix['rows']) is list and len(matrix['rows'])==6 and type(selected['row_indexes']) is list and
              len(selected['row_indexes'])==(6 if request['matrix'] else 1) and all(_integer(i,0,5) for i in selected['row_indexes']) and len(set(selected['row_indexes']))==len(selected['row_indexes']))
        if request['matrix']: _need(selected['row_indexes']==list(range(6)))
        for index,slot in enumerate(matrix['rows']):
            _keys(slot,('row_index','run_id','settings'));_need(type(slot['row_index']) is int and slot['row_index']==index and type(slot['run_id']) is str and _D3_RUN_ID.fullmatch(slot['run_id']))
            if index not in selected['row_indexes']: _need(slot['settings'] is None);continue
            settings=_settings(slot['settings']);overrides=dict(request['overrides'])
            model=MODELS[index//3]
            if request['matrix']: overrides['thinking_level']=('LOW','MEDIUM','HIGH')[index%3]
            else: _need(model==request['model_id'])
            expected=_settings(_module('ai_connection_profiles').resolve_run_settings(profile,model_id=model,overrides=overrides))
            _need(settings==expected and settings['thinking_level']==('LOW','MEDIUM','HIGH')[index%3])

    def _planned(self,matrix):
        return [dict(model_id=MODELS[i//3],thinking_level=('LOW','MEDIUM','HIGH')[i%3],settings=copy.deepcopy(slot['settings']),state='not_run',
                     reason_code='pending' if slot['settings'] else 'not_selected',attempted=False,http_status=None,finish_reason=None,reported_model_version=None,response_id=None,
                     response_complete=None,strict_decode='not_run',quality='not_run',usage=None,cost=None,latency_ms=None,error_code=None) for i,slot in enumerate(matrix['rows'])]

    def _record_cells(self, report, matrix):
        contract=_scenario(matrix['scenario_id'],matrix['evaluator_id']);_need(contract is not None)
        _keys(report,'schema_version kind batch_id matrix_sha256 execution_mode rows summary business_assessment'.split())
        _need(report['schema_version']==1 and type(report['schema_version']) is int and report['kind']=='vertex_comparison_batch' and report['batch_id']==matrix['batch_id'] and
              report['matrix_sha256']==matrix['matrix_sha256'] and report['execution_mode'] in ('actual','mock','replay') and
              type(report['rows']) is list and len(report['rows'])==6 and report['business_assessment']=='not_assessed')
        _keys(report['summary'],'planned_rows selected_rows success_rows failed_rows not_run_rows unknown_rows cumulative_reserved_calls cumulative_reserved_output_tokens generation_post_attempts generation_post_attempts_known generation_post_attempts_unknown_rows'.split())
        _need(type(report['summary']['planned_rows']) is int and report['summary']['planned_rows']==6 and
              type(report['summary']['selected_rows']) is int and report['summary']['selected_rows']==len(matrix['selection']['row_indexes']))
        cells=self._planned(matrix); attempts=[]
        for index,row in enumerate(report['rows']):
            _keys(row,'schema_version kind batch_id run_id row_index binding settings execution_mode status reason_code receipt strict_decode assessment budget timing'.split())
            slot=matrix['rows'][index];cell=cells[index]
            _need(row['schema_version']==1 and type(row['schema_version']) is int and row['kind']=='vertex_comparison_row' and row['batch_id']==matrix['batch_id'] and
                  row['run_id']==slot['run_id'] and type(row['row_index']) is int and row['row_index']==index and row['settings']==slot['settings'] and
                  row['execution_mode']==report['execution_mode'] and row['status'] in ('success','failed','not_run','unknown'))
            expected=dict(scenario_id=matrix['scenario_id'],scenario_version=1,evaluator_id=matrix['evaluator_id'],evaluator_version=1,
                          prompt_sha256=matrix['binding']['prompt_sha256'],schema_sha256=matrix['binding']['response_schema_sha256'],profile_sha256=matrix['binding']['profile_sha256'],
                          settings_sha256=slot['settings']['settings_sha256'] if slot['settings'] else None,matrix_sha256=matrix['matrix_sha256'])
            _keys(row['binding'],expected)
            _need(row['binding']==expected and type(row['binding']['scenario_version']) is int and type(row['binding']['evaluator_version']) is int)
            _keys(row['strict_decode'],('status','evaluator_id','error_code'));_keys(row['assessment'],('status','verdict','reason_code'))
            _need(row['strict_decode']['status'] in ('checked','rejected','not_run') and row['strict_decode']['evaluator_id']==matrix['evaluator_id'] and
                  row['assessment']['status']=='not_assessed' and row['assessment']['verdict'] is None and row['assessment']['reason_code']==contract[4])
            if row['strict_decode']['status']=='checked':_need(row['strict_decode']['error_code'] is None)
            _keys(row['budget'],('budget_id','reservation_id','reserved_calls','reserved_output_tokens','generation_post_attempts'))
            _keys(row['timing'],('started_at','finished_at','elapsed_ms'))
            count=row['budget']['generation_post_attempts'];_need(count is None or _integer(count,0,1));attempts.append(count)
            reason=row['reason_code'];_need(type(reason) is str and (reason in _REASONS or reason in {'vertex_response_'+s for s in 'invalid_input invalid_settings credential_invalid credential_quota_mismatch dependency_unavailable evidence_error auth_failed http_error response_invalid incomplete blocked limit_exceeded timeout cancelled cleanup_failed internal_error'.split()}))
            decoded=row['strict_decode']
            if decoded['status']=='checked':
                _need(row['status']=='success' and reason==contract[2] and decoded['error_code'] is None)
            elif decoded['status']=='rejected':
                _need(row['status']=='failed' and reason==contract[3] and decoded['error_code']==contract[3])
            else:
                _need(row['status']!='success' and reason not in _STRICT_REASONS and decoded['error_code'] is None)
            cell.update(state={'failed':'failure'}.get(row['status'],row['status']),reason_code=reason,attempted=None if count is None else bool(count),
                        strict_decode={'checked':'pass','rejected':'fail','not_run':'not_run'}[row['strict_decode']['status']],quality='not_run',latency_ms=row['timing']['elapsed_ms'])
            _need(cell['latency_ms'] is None or _number(cell['latency_ms']))
            receipt=row['receipt']
            if receipt is None:
                _need(row['status']!='success');continue
            _keys(receipt,_RECEIPT)
            _need(receipt['schema_version']==1 and type(receipt['schema_version']) is int and receipt['kind']=='vertex_response_receipt' and receipt['status'] in ('complete','failed') and _settings(receipt['settings'])==slot['settings'])
            _keys(receipt['bindings'],('prompt_sha256','schema_sha256','provider_payload_sha256','settings_sha256'))
            for key,expected_sha in (('prompt_sha256',matrix['binding']['prompt_sha256']),('schema_sha256',matrix['binding']['response_schema_sha256']),('settings_sha256',slot['settings']['settings_sha256'])):
                _need(receipt['bindings'][key] is None or receipt['bindings'][key]==expected_sha)
            _need(receipt['bindings']['provider_payload_sha256'] is None or type(receipt['bindings']['provider_payload_sha256']) is str and _SHA.fullmatch(receipt['bindings']['provider_payload_sha256']))
            _keys(receipt['request'],('method','url','quota_project_id','auth_profile_id'))
            host={'global':'aiplatform.googleapis.com','us':'aiplatform.us.rep.googleapis.com','eu':'aiplatform.eu.rep.googleapis.com'}[slot['settings']['location']]
            expected_url=f'https://{host}/v1/projects/{TARGET}/locations/{slot["settings"]["location"]}/publishers/google/models/{slot["settings"]["model_id"]}:generateContent'
            _need(receipt['request']==dict(method='POST',url=expected_url,quota_project_id=TARGET,auth_profile_id='vertex-trial'))
            _keys(receipt['client'],('transport','api_version','google_auth_version','requests_version','google_genai_used'))
            _need(receipt['client']['transport']=='REST' and receipt['client']['api_version']=='v1' and receipt['client']['google_genai_used'] is False)
            _keys(receipt['response'],('http_status','auth_http_status','finish_reason','reported_model_version','provider_response_id','text_parts','thought_parts'))
            _keys(receipt['attempts'],'worker_process_attempts auth_refresh_attempts auth_http_attempts generation_post_attempts auth_refresh_completed auth_retry_blocked application_retries'.split())
            _need(receipt['attempts']['generation_post_attempts']==count and type(receipt['attempts']['application_retries']) is int and receipt['attempts']['application_retries']==0)
            _need(all(receipt['attempts'][k] is None or _integer(receipt['attempts'][k],0,1) for k in ('worker_process_attempts','auth_refresh_attempts','auth_http_attempts','generation_post_attempts')) and
                  all(type(receipt['attempts'][k]) is bool for k in ('auth_refresh_completed','auth_retry_blocked')))
            response=receipt['response'];_need(response['http_status'] is None or _integer(response['http_status'],100,599))
            for key in ('reported_model_version','provider_response_id'):
                _need(response[key] is None or type(response[key]) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}',response[key]))
            _need(response['finish_reason'] in (None,'STOP','MAX_TOKENS','SAFETY','RECITATION','OTHER','BLOCKLIST','PROHIBITED_CONTENT','SPII','MALFORMED_FUNCTION_CALL','FINISH_REASON_UNSPECIFIED'))
            _keys(receipt['verification'],('wire_complete','credential_metadata_verified','remote_identity_verified','semantic_quality_verified','credit_verified'))
            _need(all(type(v) is bool for v in receipt['verification'].values()) and all(receipt['verification'][k] is False for k in ('remote_identity_verified','semantic_quality_verified','credit_verified')))
            complete=receipt['status']=='complete'
            _keys(receipt['cleanup'],('worker_reaped','transport_handles_closed','artifact_handles_closed','worker_exit_code','secondary_errors','remote_cancellation_verified'))
            if complete:
                _need(receipt['failure'] is None and response['http_status']==200 and response['finish_reason']=='STOP' and receipt['verification']['wire_complete'] is True and
                      all(receipt['bindings'][k] is not None for k in receipt['bindings']) and
                      all(receipt['cleanup'][k] is True for k in ('worker_reaped','transport_handles_closed','artifact_handles_closed')) and
                      type(receipt['cleanup']['worker_exit_code']) is int and receipt['cleanup']['worker_exit_code']==0 and receipt['cleanup']['secondary_errors']==[])
            else:
                _keys(receipt['failure'],('code','phase'))
                _need(type(receipt['failure']['code']) is str and re.fullmatch(r'vertex_response_[a-z_]{1,64}',receipt['failure']['code']) and
                      receipt['failure']['phase'] in ('validation','credentials','evidence','dependencies','auth','send','collect','extract','cleanup'))
            if row['status']=='success': _need(complete and row['strict_decode']['status']=='checked')
            usage=receipt['usage']
            if usage is not None:
                _keys(usage,_USAGE);_need(all(v is None or _integer(v,0,2**63-1) for v in usage.values()))
                usage={k:None if v is None else str(v) for k,v in usage.items()}
            cell.update(http_status=response['http_status'],finish_reason=response['finish_reason'],reported_model_version=response['reported_model_version'],response_id=response['provider_response_id'],response_complete=complete,usage=usage)
        return cells,None if any(v is None for v in attempts) else sum(attempts)

    def _work(self,rid,module,scenario):
        run=self.runs[rid];matrix=run['matrix'];runner_entered=False
        try:
            with self.lock:
                run['view']['state']='running';run['view']['attempts_used']=None
                for cell in run['view']['cells']:
                    if cell['settings'] is not None: cell.update(state='running',attempted=None)
            self.paths['evidence_root'].mkdir(parents=True,exist_ok=True)
            runner=module.run_vertex_comparison_batch
            args=(copy.deepcopy(matrix),scenario['prompt_bytes'],scenario['response_schema_bytes'])
            kwargs=dict(adc_path=self.paths['adc_path'],evidence_dir=self.paths['evidence_root']/('ai-run-'+rid),
                        budget_path=self.paths['budget_path'],approval_path=self.paths['approval_path'],cancel_event=run['cancel'])
            runner_entered=True
            report=runner(*args,**kwargs)
            cells,attempts=self._record_cells(report,matrix)
            with self.lock: run['view'].update(cells=cells,attempts_used=attempts,execution_mode=report['execution_mode'])
        except BaseException as error:
            with self.lock:
                run['failure']=error
                try:code=getattr(error,'code',None)
                except Exception:code=None
                code=code if runner_entered and type(code) is str and code in _PUBLIC_FAILURES else 'ai_connection_ui_unavailable'
                run['view'].update(cells=self._planned(matrix),attempts_used=None if runner_entered else 0,error_code=code)
                for cell in run['view']['cells']:
                    if cell['settings'] is not None:
                        cell.update(state='unknown' if runner_entered else 'not_run',reason_code='unavailable',attempted=None if runner_entered else False)
        finally:
            run['timer'].cancel()
            with self.lock:
                run['view'].update(state='finished',finished_at=time.time(),cancel_requested=run['cancel'].is_set())
                if self.active==rid:self.active=None

    def _owned(self, owner, rid):
        _need(type(rid) is str and _SHA.fullmatch(rid),'not_found',404)
        with self.lock:
            _need(rid in self.runs and self.runs[rid]['owner']==owner and self.runs[rid]['view'] is not None,'not_found',404)
            return copy.deepcopy(self.runs[rid]['view'])

    def _cancel(self, owner, rid):
        self._owned(owner,rid)
        with self.lock:
            run=self.runs[rid]
            if run['view']['state']!='finished':
                run['cancel'].set();run['view'].update(state='cancelling',cancel_requested=True)
            return copy.deepcopy(run['view'])

    def _body(self, handler):
        _need(not handler.headers.get_all('Expect'),'expectation_failed',417)
        _need(not handler.headers.get_all('Transfer-Encoding') and not handler.headers.get_all('Content-Encoding'))
        types = handler.headers.get_all('Content-Type',[])
        _need(len(types)==1 and re.fullmatch(r'application/json(?:\s*;\s*charset\s*=\s*utf-8)?',types[0],re.I),'unsupported_media',415)
        lengths = handler.headers.get_all('Content-Length',[])
        _need(bool(lengths),'length_required',411)
        _need(len(lengths)==1 and re.fullmatch('[0-9]+',lengths[0],re.ASCII))
        literal=lengths[0].lstrip('0') or '0'
        _need(len(literal)<=5 and int(literal)<=32768,'input_limit',413)
        length=int(literal)
        try: raw=handler.rfile.read(length)
        except (OSError,TimeoutError): raise AIConnectionUIError('request_timeout',408) from None
        _need(len(raw)==length); return _json(raw)

    def _send(self, handler, status, payload, headers=(), maximum=262144):
        raw=_canonical(payload); _need(len(raw)<=maximum,'unavailable',503)
        handler._ai_started=True; handler.close_connection=True
        handler.send_response(status)
        for key,value in [('Content-Type','application/json; charset=utf-8'),('Content-Length',str(len(raw))),('Cache-Control','no-store'),
                          ('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'"),*headers]:
            handler.send_header(key,value)
        handler.end_headers()
        if handler.command!='HEAD': handler.wfile.write(raw)

    def dispatch(self, handler):
        if not handler.path.startswith(PREFIX): return False
        handler._ai_started=False
        try:
            self._guard(handler)
            route=handler.path[len(PREFIX):]
            _need(handler.requestline.split()[1] == handler.path and not any(c in route for c in '?%#\\') and '//' not in route,'not_found',404)
            known=route in ('session','state','profile','run','cancel') or re.fullmatch(r'runs/[a-f0-9]{64}',route)
            _need(known,'not_found',404)
            expected='GET' if route in ('session','state') or route.startswith('runs/') else 'POST'
            _need(handler.command==expected,'method_not_allowed',405)
            if expected=='GET':
                lengths=handler.headers.get_all('Content-Length',[])
                _need(not handler.headers.get_all('Transfer-Encoding') and not handler.headers.get_all('Content-Encoding') and
                      not handler.headers.get_all('Expect') and len(lengths)<=1 and (not lengths or re.fullmatch('0+',lengths[0],re.ASCII)))
            sid,item,cookie=self._session(handler,route=='session')
            if route=='session':
                headers=[('X-AI-Connection-CSRF',item['csrf'])]
                if cookie: headers.append(('Set-Cookie',cookie))
                self._send(handler,200,dict(schema_version=1,kind='ai_connection_session',capabilities=list(CAPABILITIES),expires_at=item['expires']),headers,4096)
            elif route=='state': self._send(handler,200,self._state(sid),maximum=65536)
            elif route=='profile': self._send(handler,200,self._save(sid,self._body(handler)),maximum=65536)
            elif route=='run': self._send(handler,202,self._start(sid,self._body(handler)))
            elif route.startswith('runs/'): self._send(handler,200,self._owned(sid,route[5:]))
            elif route=='cancel':
                request=self._body(handler); _keys(request,('run_id',)); self._send(handler,200,self._cancel(sid,request['run_id']))
        except AIConnectionUIError as error:
            if not handler._ai_started:
                self._send(handler,error.status,{'error':{'code':error.code}},[('Allow','GET' if handler.path.endswith(('session','state')) or '/runs/' in handler.path else 'POST')] if error.status==405 else ())
        except (OSError,TimeoutError): handler.close_connection=True
        except Exception:
            if not handler._ai_started: self._send(handler,503,{'error':{'code':'ai_connection_ui_unavailable'}})
        return True

    def close(self):
        deadline=time.monotonic()+5
        with self.lock:
            self.closing=True
            if self.active: self.runs[self.active]['cancel'].set()
            worker=self.worker
            timers=[r['timer'] for r in self.runs.values() if 'timer' in r]
        for timer in timers:timer.cancel()
        if worker is threading.current_thread(): raise AIConnectionUIError('close_unconfirmed')
        if worker and worker.ident is not None: worker.join(max(0,deadline-time.monotonic()))
        for timer in timers:
            if timer.ident is not None:timer.join(max(0,deadline-time.monotonic()))
        if worker and worker.is_alive(): raise AIConnectionUIError('close_unconfirmed')


def wrap_ai_server(base, runtime):
    class AIConnectionServer(base):
        _ai_connection_runtime = runtime
        def get_request(self):
            client,address=super().get_request();client.settimeout(5)
            with runtime.lock: runtime.clients.add(client)
            return client,address

        def process_request_thread(self, request, address):
            current=threading.current_thread()
            with runtime.lock:runtime.request_workers.add(current)
            try: super().process_request_thread(request,address)
            finally:
                with runtime.lock:runtime.clients.discard(request);runtime.request_workers.discard(current)

        def handle_error(self, request, address):
            error=sys.exception()
            with runtime.lock:
                runtime.last_server_exception=error
                if len(runtime.server_errors)<32:runtime.server_errors.append(dict(type=type(error).__name__,errno=getattr(error,'errno',None)))

        def serve_forever(self, poll_interval=.5):
            runtime.loop_thread=threading.current_thread()
            try: return super().serve_forever(poll_interval=poll_interval)
            except BaseException:
                runtime.loop_failure=True;raise
            finally: runtime.loop_thread=None

        def server_close(self):
            current=threading.current_thread()
            with runtime.lock:
                if current is runtime.loop_thread or current in runtime.request_workers or current is runtime.worker:
                    raise AIConnectionUIError('close_unconfirmed')
                runtime.closing=True
            failure=None;deadline=time.monotonic()+5
            try:
                if runtime.loop_thread is not None:self.shutdown()
                runtime.close()
            except BaseException as error: failure=error
            finally:
                for client in list(runtime.clients):
                    with suppress(OSError): client.shutdown(socket.SHUT_RDWR)
                    with suppress(OSError): client.close()
                super().server_close()
                for worker in list(runtime.request_workers):worker.join(max(0,deadline-time.monotonic()))
                runtime.closed=(failure is None and self.socket.fileno()==-1 and runtime.loop_thread is None and not runtime.request_workers and
                                (runtime.worker is None or not runtime.worker.is_alive()))
                if not runtime.closed and failure is None:failure=AIConnectionUIError('close_unconfirmed')
            if failure: raise failure
    return AIConnectionServer
