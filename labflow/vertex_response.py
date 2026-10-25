"""Explicit authorized-user Vertex REST transport; no ADC discovery or retries."""
import hashlib
import importlib.metadata
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import stat
import threading
import time
from types import SimpleNamespace
import uuid

_TARGET='project-a6310591-f8cc-487c-9e3'
_OAUTH='https://oauth2.googleapis.com/token'
_HOSTS=dict(global_='https://aiplatform.googleapis.com',us='https://aiplatform.us.rep.googleapis.com',eu='https://aiplatform.eu.rep.googleapis.com')
_HOSTS['global']=_HOSTS.pop('global_')
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z',re.ASCII)
_META=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}\Z',re.ASCII)
_HASH=re.compile(r'[a-f0-9]{64}\Z',re.ASCII)
_SETTINGS=set('schema_version kind profile_id profile_revision provider service project_id location quota_project_id auth_profile_id model_id thinking_level max_output_tokens timeout_seconds profile_sha256 settings_sha256'.split())
_MODELS={'gemini-4-argon','gemini-3.8-flash'}
_LEVELS={'LOW','MEDIUM','HIGH'}
_PREFIX='vertex_response_'
_CODES={'invalid_input','invalid_settings','credential_invalid','credential_quota_mismatch','dependency_unavailable',
    'evidence_error','auth_failed','http_error','response_invalid','incomplete','blocked','limit_exceeded',
    'timeout','cancelled','cleanup_failed','internal_error'}
_PHASES={'validation','credentials','evidence','dependencies','auth','send','collect','extract','cleanup'}
_CONTROL=(KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError)
_LAYOUT=dict(prompt='request.json',response_schema='response-schema.json',settings='settings.json',
    provider_request='provider-request.json',provider_response='provider-response.bin',final_text='response-text.bin')
_USAGE=dict(prompt_token_count='promptTokenCount',candidates_token_count='candidatesTokenCount',
    total_token_count='totalTokenCount',thoughts_token_count='thoughtsTokenCount',
    cached_content_token_count='cachedContentTokenCount',tool_use_prompt_token_count='toolUsePromptTokenCount')
_FINISH={'STOP','MAX_TOKENS','SAFETY','RECITATION','OTHER','BLOCKLIST','PROHIBITED_CONTENT','SPII',
    'MALFORMED_FUNCTION_CALL','FINISH_REASON_UNSPECIFIED'}
_MAXINT=9223372036854775807


class VertexResponseError(RuntimeError):
    """Sanitized public error; optional detached partial primitive receipt."""
    def __init__(self,code,receipt=None):
        suffix=code.removeprefix(_PREFIX) if type(code) is str else 'invalid_input'
        self.code=_PREFIX+(suffix if suffix in _CODES else 'invalid_input')
        self.receipt=receipt
        super().__init__(self.code)


class _Fault(Exception):
    def __init__(self,code):self.code=code


def _fail(code):raise _Fault(code)


def _C(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _H(data):return hashlib.sha256(data).hexdigest()
def _copy(value):return json.loads(_C(value))


def _fixed(code,receipt=None):
    try:raise VertexResponseError(code,receipt) from None
    except VertexResponseError as error:
        error.__context__=None;error.__cause__=None
        raise


def _json(data,code,*,depth=32,nodes=200000):
    try:text=data.decode('utf-8',errors='strict')
    except UnicodeError:_fail(code)
    level=0;quoted=False;escaped=False
    for char in text:
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True
        elif char in '[{':
            level+=1
            if level>depth+1:_fail('limit_exceeded')
        elif char in ']}':level-=1
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:_fail(code)
            out[key]=value
        return out
    def integer(value):
        if len(value)>20:_fail('limit_exceeded')
        parsed=int(value)
        if not -_MAXINT-1<=parsed<=_MAXINT:_fail('limit_exceeded')
        return parsed
    def constant(_):_fail(code)
    try:value=json.loads(text,object_pairs_hook=pairs,parse_int=integer,parse_constant=constant)
    except _Fault:raise
    except (ValueError,UnicodeError,RecursionError):_fail(code)
    count=0
    def walk(x,level):
        nonlocal count
        count+=1
        if count>nodes or level>depth:_fail('limit_exceeded')
        if type(x) is str:
            try:x.encode('utf-8')
            except UnicodeError:_fail(code)
        elif type(x) is float and not math.isfinite(x):_fail(code)
        elif type(x) is dict:
            for k,v in x.items():walk(k,level+1);walk(v,level+1)
        elif type(x) is list:
            for v in x:walk(v,level+1)
    walk(value,0);return value


def _settings(value):
    code='invalid_settings'
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value)!=_SETTINGS:_fail(code)
    for key,wanted in [('schema_version',1),('kind','ai_run_settings'),('provider','vertex_ai'),('service','aiplatform.googleapis.com'),('project_id',_TARGET),('quota_project_id',_TARGET)]:
        if type(value[key]) is not type(wanted) or value[key]!=wanted:_fail(code)
    for key in ('profile_id','auth_profile_id'):
        if type(value[key]) is not str or not _ID.fullmatch(value[key]):_fail(code)
    if type(value['profile_revision']) is not int or not 0<=value['profile_revision']<=_MAXINT:_fail(code)
    for key,allowed in [('location',_HOSTS),('model_id',_MODELS),('thinking_level',_LEVELS)]:
        if type(value[key]) is not str or value[key] not in allowed:_fail(code)
    if type(value['max_output_tokens']) is not int or not 64<=value['max_output_tokens']<=8192:_fail(code)
    timeout=value['timeout_seconds']
    if type(timeout) not in (int,float) or not 1<=timeout<=120 or not math.isfinite(timeout):_fail(code)
    for key in ('profile_sha256','settings_sha256'):
        if type(value[key]) is not str or not _HASH.fullmatch(value[key]):_fail(code)
    other={k:v for k,v in value.items() if k!='settings_sha256'}
    if _H(_C(other))!=value['settings_sha256']:_fail(code)
    return _copy(value)


def _path(path):
    if type(path) is not type(Path()) or not path.is_absolute():_fail('invalid_input')


def _chain(path,code):
    for part in (path,*path.parents):
        info=part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:_fail(code)


def _read(path,cap,code):
    try:
        before=path.lstat()
        if not stat.S_ISREG(before.st_mode) or getattr(before,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:_fail(code)
        with path.open('rb',buffering=0) as stream:
            opened=os.fstat(stream.fileno())
            if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):_fail(code)
            data=stream.read(cap+1);after=os.fstat(stream.fileno())
        current=path.lstat()
        if ((current.st_dev,current.st_ino)!=(before.st_dev,before.st_ino) or before.st_size!=after.st_size or after.st_size!=current.st_size):_fail(code)
        return data
    except _Fault:raise
    except OSError:_fail(code)


def _credentials(path,settings):
    _path(path)
    try:_chain(path,'credential_invalid')
    except OSError:_fail('credential_invalid')
    data=_read(path,65536,'credential_invalid')
    if len(data)>65536:_fail('limit_exceeded')
    value=_json(data,'credential_invalid',depth=8,nodes=256)
    required={'type','client_id','client_secret','refresh_token','quota_project_id'};optional={'account','universe_domain','token_uri'}
    if type(value) is not dict or not required<=set(value)<=required|optional:_fail('credential_invalid')
    if value['type']!='authorized_user':_fail('credential_invalid')
    if any(type(value[k]) is not str or not value[k].strip() for k in required-{'type'}):_fail('credential_invalid')
    if value['quota_project_id']!=settings['quota_project_id']:_fail('credential_quota_mismatch')
    if ('account' in value and type(value['account']) is not str or
        'universe_domain' in value and value['universe_domain']!='googleapis.com' or
        'token_uri' in value and value['token_uri']!=_OAUTH):_fail('credential_invalid')
    return value


def _metadata(settings):
    return dict(schema_version=1,kind='vertex_credentials_metadata',settings_sha256=settings['settings_sha256'],
        auth_profile_id=settings['auth_profile_id'],credential_type='authorized_user',quota_project_id=_TARGET,
        token_endpoint=_OAUTH,metadata_valid=True,refresh_attempted=False,model_access_verified=False,credit_status_verified=False)


def inspect_vertex_credentials(adc_path: Path,*,settings: dict) -> dict:
    """Inspect only the explicitly supplied file; no refresh, network or writes."""
    code='credential_invalid'
    try:
        snapshot=_settings(settings);_credentials(adc_path,snapshot)
        return _metadata(snapshot)
    except _Fault as error:code=error.code
    except _CONTROL:raise
    except Exception:pass
    _fixed(code)


def _write(path,data):
    with path.open('xb',buffering=0) as stream:
        view=memoryview(data)
        while view:
            amount=stream.write(view)
            if not amount:raise OSError('artifact_write_failed')
            view=view[amount:]


def _marker(directory,name):_write(directory/name,b'{"started":true}')


def _versions():
    try:
        auth=importlib.metadata.version('google-auth');requests=importlib.metadata.version('requests')
    except importlib.metadata.PackageNotFoundError:_fail('dependency_unavailable')
    if auth!='2.62.0' or requests!='2.34.2':_fail('dependency_unavailable')
    return auth,requests


def _http_exchange(task):
    """Concrete child HTTP leaf; auth data never reaches artifacts or status."""
    result=dict(schema_version=1,code=None,phase='dependencies',auth_http_status=None,http_status=None,
        auth_retry_blocked=False,transport_handles_closed=False,artifact_handles_closed=True,response_complete=False)
    sessions=[];responses=[];phase='dependencies';auth_requests=0;directory=Path(task['directory'])
    timeout_errors=();request_errors=()
    def check():
        if time.monotonic()>=task['deadline']:_fail('timeout')
    def timeout():
        check();left=task['deadline']-time.monotonic();return min(10.0,left),left
    def session():
        client=requests.Session();client.trust_env=False;client.headers.update({'Accept-Encoding':'identity'})
        sessions.append(client);client.mount('https://',requests.adapters.HTTPAdapter(max_retries=0));return client
    def compressed(reply):
        headers={k.lower():v for k,v in reply.headers.items()}
        return headers.get('content-encoding','identity').lower() not in {'','identity'}
    def bounded(reply,cap,path=None):
        count=0;parts=[];handle=None;primary=None
        try:
            if path is not None:handle=path.open('xb',buffering=0)
            for data in reply.iter_content(chunk_size=65536):
                check()
                if not data:continue
                keep=data[:cap+1-count];count+=len(keep)
                if handle is not None:
                    view=memoryview(keep)
                    while view:
                        n=handle.write(view)
                        if not n:raise OSError('artifact_write_failed')
                        view=view[n:]
                else:parts.append(keep)
                if count>cap:_fail('limit_exceeded')
            return b''.join(parts)
        except BaseException as error:primary=error;raise
        finally:
            if handle is not None:
                try:handle.close()
                except BaseException as error:
                    result['artifact_handles_closed']=False
                    if primary is None:
                        if isinstance(error,_CONTROL):raise
                        if result['code'] is None:_fail('cleanup_failed')
    try:
        _versions()
        import requests
        timeout_errors=(requests.exceptions.Timeout,);request_errors=(requests.exceptions.RequestException,)
        from google.oauth2.credentials import Credentials
        phase='auth';check();credential=Credentials.from_authorized_user_info(task['credentials'],scopes=['https://www.googleapis.com/auth/cloud-platform'])
        if credential.quota_project_id!=task['settings']['quota_project_id']:_fail('credential_quota_mismatch')
        auth_session=session()
        def auth_request(url,method='GET',body=None,headers=None,**kwargs):
            nonlocal auth_requests
            if url!=_OAUTH or method!='POST':_fail('auth_failed')
            if auth_requests:
                result['auth_retry_blocked']=True;_fail('auth_failed')
            check();auth_requests+=1;_marker(directory,'auth-http-started.json')
            reply=auth_session.request('POST',_OAUTH,data=body,headers=headers or {},timeout=timeout(),stream=True,allow_redirects=False,verify=True)
            responses.append(reply);result['auth_http_status']=reply.status_code
            if reply.status_code!=200:result['code']='auth_failed'
            if compressed(reply):_fail('auth_failed')
            data=bounded(reply,65536)
            if reply.status_code!=200:_fail('auth_failed')
            return SimpleNamespace(status=reply.status_code,data=data,headers=reply.headers)
        _marker(directory,'auth-started.json')
        credential.refresh(auth_request)
        if type(credential.token) is not str or not credential.token or len(credential.token)>16384:_fail('auth_failed')
        _marker(directory,'auth-finished.json');check();phase='send'
        model_session=session();_marker(directory,'generation-started.json')
        reply=model_session.post(task['url'],data=task['payload'],headers={'Authorization':'Bearer '+credential.token,
            'Content-Type':'application/json','Accept-Encoding':'identity','x-goog-user-project':_TARGET},
            timeout=timeout(),stream=True,allow_redirects=False,verify=True)
        responses.append(reply);result['http_status']=reply.status_code;phase='collect'
        if reply.status_code!=200:result['code']='http_error'
        if compressed(reply):_fail('response_invalid')
        bounded(reply,2097152,directory/'provider-response.bin');result['response_complete']=True
        _marker(directory,'response-complete.json')
        if reply.status_code!=200:_fail('http_error')
    except _Fault as error:result['code']=result['code'] or error.code
    except _CONTROL:raise
    except timeout_errors:result['code']=result['code'] or 'timeout'
    except request_errors:result['code']=result['code'] or ('auth_failed' if phase=='auth' else 'http_error')
    except OSError:result['code']=result['code'] or 'evidence_error'
    except Exception:result['code']=result['code'] or ('dependency_unavailable' if phase=='dependencies' else 'auth_failed' if phase=='auth' else 'http_error')
    finally:
        closed=True
        for item in responses+sessions:
            try:item.close()
            except _CONTROL:raise
            except Exception:closed=False
        result['transport_handles_closed']=closed
        if not closed and result['code'] is None:result['code']='cleanup_failed'
    result['phase']=phase
    return result


def _vertex_worker(task):
    """Spawn entry with silent stdio and only fixed, bounded status output."""
    fd=os.open(os.devnull,os.O_RDWR)
    for destination in (0,1,2):os.dup2(fd,destination)
    if fd>2:os.close(fd)
    try:result=_http_exchange(task)
    except BaseException:
        result=dict(schema_version=1,code='internal_error',phase='collect',auth_http_status=None,http_status=None,
            auth_retry_blocked=False,transport_handles_closed=False,artifact_handles_closed=False,response_complete=False)
    try:_write(Path(task['directory'])/'worker-result.json',_C(result))
    except BaseException:pass


def _empty(path):return dict(path=path,present=False,bytes=0,sha256=None,complete=False,overflow=False,extent='absent')


def _new_receipt(settings,reference,url):
    return dict(schema_version=1,kind='vertex_response_receipt',exchange_ref=reference,status='failed',failure=None,
        bindings=dict(prompt_sha256=None,schema_sha256=None,provider_payload_sha256=None,settings_sha256=settings['settings_sha256']),
        settings=settings,client=dict(transport='REST',api_version='v1',google_auth_version=None,requests_version=None,google_genai_used=False),
        request=dict(method='POST',url=url,quota_project_id=_TARGET,auth_profile_id=settings['auth_profile_id']),
        attempts=dict(worker_process_attempts=0,auth_refresh_attempts=0,auth_http_attempts=0,generation_post_attempts=0,
            auth_refresh_completed=False,auth_retry_blocked=False,application_retries=0),
        response=dict(http_status=None,auth_http_status=None,finish_reason=None,reported_model_version=None,provider_response_id=None,text_parts=0,thought_parts=0),
        usage=None,cost=dict(kind='not_applicable',amount=None,currency=None,price_version=None),
        timing=dict(timeout_seconds=float(settings['timeout_seconds']),local_elapsed_seconds=None),
        cancellation=dict(requested=False,local_worker_stopped=None,provider_completion='not_started',remote_cancel_verified=False),
        cleanup=dict(worker_reaped=None,worker_exit_code=None,transport_handles_closed=None,artifact_handles_closed=None,secondary_errors=[],remote_cancellation_verified=False),
        artifacts={key:_empty(path) for key,path in _LAYOUT.items()},
        verification=dict(wire_complete=False,credential_metadata_verified=True,remote_identity_verified=False,semantic_quality_verified=False,credit_verified=False))


class _Run:
    def __init__(self,settings,directory,event,start):
        self.directory=directory;self.event=event;self.start=start;self.deadline=start+float(settings['timeout_seconds'])
        url=_HOSTS[settings['location']]+f"/v1/projects/{_TARGET}/locations/{settings['location']}/publishers/google/models/{settings['model_id']}:generateContent"
        self.r=_new_receipt(settings,'vertex-exchange:'+uuid.uuid4().hex,url)
        self.process=None;self.started=False;self.result=None;self.first=None;self.control=None;self.phase='evidence';self.text=None

    def error(self,code,phase=None):
        if self.first is None:self.first=dict(code=_PREFIX+code,phase=phase or self.phase)

    def signal(self,error):
        if self.control is None:self.control=error
        self.error('internal_error')

    def secondary(self,code):
        codes=self.r['cleanup']['secondary_errors']
        if code not in codes:
            if len(codes)<8:codes.append(code)
            else:codes[-1]='secondary_overflow'

    def check(self):
        if self.event is not None and self.event.is_set():self.r['cancellation']['requested']=True;_fail('cancelled')
        if time.monotonic()>=self.deadline:_fail('timeout')

    def write(self,name,data):
        self.check();_write(self.directory/_LAYOUT[name],data)
        self.r['artifacts'][name].update(present=True,bytes=len(data),sha256=_H(data),complete=True,extent='whole_file')

    def marker(self,name):
        path=self.directory/name
        if not path.exists():return False
        value=_json(_read(path,4096,'evidence_error'),'evidence_error',depth=8,nodes=256)
        if type(value) is not dict or set(value)!={'started'} or value['started'] is not True:_fail('evidence_error')
        return True

    def progress(self,known=False):
        attempts=self.r['attempts']
        completed=self.marker('auth-finished.json')
        observed_auth=self.result is not None and self.result['auth_http_status'] is not None
        observed_generation=self.result is not None and self.result['http_status'] is not None
        observed={'auth_refresh_attempts':completed or observed_auth or observed_generation,
            'auth_http_attempts':observed_auth or observed_generation,'generation_post_attempts':observed_generation}
        for name,key in [('auth-started.json','auth_refresh_attempts'),('auth-http-started.json','auth_http_attempts'),('generation-started.json','generation_post_attempts')]:
            attempts[key]=1 if self.marker(name) or observed[key] else 0 if known or not self.started else None
        attempts['auth_refresh_completed']=completed
        self.r['cost']['kind']='not_applicable' if attempts['generation_post_attempts']==0 else 'unknown'
        if attempts['generation_post_attempts']!=0 and self.r['cancellation']['provider_completion']=='not_started':
            self.r['cancellation']['provider_completion']='unknown'

    def collect_body(self,complete):
        path=self.directory/_LAYOUT['provider_response']
        if not path.exists():return None
        data=_read(path,2097152,'evidence_error');prefix=data[:2097152];overflow=len(data)>2097152
        desc=self.r['artifacts']['provider_response'];good=complete and not overflow
        desc.update(present=True,bytes=len(prefix),sha256=_H(prefix),complete=good,overflow=overflow,extent='whole_file' if good else 'prefix')
        if overflow:_fail('limit_exceeded')
        return data

    def run(self,prompt,schema,credentials):
        self.r['bindings'].update(prompt_sha256=_H(prompt),schema_sha256=_H(schema))
        wrapper=_C(dict(prompt_dto_utf8=prompt.decode('utf-8'),response_schema_utf8=schema.decode('utf-8'))).decode('utf-8')
        payload=_C(dict(contents=[dict(role='user',parts=[dict(text=wrapper)])],generationConfig=dict(
            maxOutputTokens=self.r['settings']['max_output_tokens'],thinkingConfig=dict(thinkingLevel=self.r['settings']['thinking_level']))))
        if len(payload)>1048576:_fail('limit_exceeded')
        self.r['bindings']['provider_payload_sha256']=_H(payload)
        for name,data in [('prompt',prompt),('response_schema',schema),('settings',_C(self.r['settings'])),('provider_request',payload)]:self.write(name,data)
        self.phase='dependencies';auth,requests=_versions();self.r['client'].update(google_auth_version=auth,requests_version=requests)
        self.check();task=dict(directory=str(self.directory),settings=self.r['settings'],credentials=credentials,payload=payload,url=self.r['request']['url'],deadline=self.deadline)
        context=multiprocessing.get_context('spawn');self.r['attempts']['worker_process_attempts']=1
        self.process=context.Process(target=_vertex_worker,args=(task,),daemon=True,name='vertex-response-'+self.r['exchange_ref'][-8:])
        try:self.process.start()
        finally:
            self.started=self.process.pid is not None
            if self.started:
                for key in ('auth_refresh_attempts','auth_http_attempts','generation_post_attempts'):self.r['attempts'][key]=None
                self.r['cost']['kind']='unknown';self.r['cancellation']['provider_completion']='unknown'
        self.phase='collect'
        while self.process.is_alive():self.check();time.sleep(min(.05,max(0,self.deadline-time.monotonic())))
        self.process.join(timeout=0);self.r['cleanup']['worker_exit_code']=self.process.exitcode
        if self.process.exitcode!=0:_fail('internal_error')
        self.check();path=self.directory/'worker-result.json'
        if not path.exists():_fail('internal_error')
        result=_json(_read(path,65536,'evidence_error'),'internal_error',depth=8,nodes=256)
        keys={'schema_version','code','phase','auth_http_status','http_status','auth_retry_blocked','transport_handles_closed','artifact_handles_closed','response_complete'}
        if type(result) is not dict or set(result)!=keys or type(result['schema_version']) is not int or result['schema_version']!=1:_fail('internal_error')
        if (result['code'] is not None and (type(result['code']) is not str or result['code'] not in _CODES) or
            type(result['phase']) is not str or result['phase'] not in _PHASES):_fail('internal_error')
        for key in ('auth_retry_blocked','transport_handles_closed','artifact_handles_closed','response_complete'):
            if type(result[key]) is not bool:_fail('internal_error')
        for key in ('auth_http_status','http_status'):
            if result[key] is not None and (type(result[key]) is not int or not 100<=result[key]<=599):_fail('internal_error')
        self.result=result;self.progress(known=True);self.r['attempts']['auth_retry_blocked']=result['auth_retry_blocked']
        self.r['response'].update(http_status=result['http_status'],auth_http_status=result['auth_http_status'])
        self.r['cleanup'].update(transport_handles_closed=result['transport_handles_closed'],artifact_handles_closed=result['artifact_handles_closed'])
        if not result['transport_handles_closed']:self.secondary('transport_close_failed')
        if not result['artifact_handles_closed']:self.secondary('artifact_close_failed')
        if result['code'] is not None:self.error(result['code'],result['phase'])
        elif (not all(self.marker(name) for name in ('auth-started.json','auth-http-started.json','auth-finished.json','generation-started.json')) or
            result['auth_http_status']!=200 or result['auth_retry_blocked']):self.error('internal_error')
        data=self.collect_body(result['response_complete'] and self.marker('response-complete.json'))
        if self.first is not None:_fail(self.first['code'].removeprefix(_PREFIX))
        if not result['transport_handles_closed'] or not result['artifact_handles_closed']:_fail('cleanup_failed')
        if result['http_status']!=200:_fail('http_error')
        if data is None or not self.r['artifacts']['provider_response']['complete']:_fail('incomplete')
        self.phase='extract';self.extract(data)

    def extract(self,data):
        value=_json(data,'response_invalid')
        if type(value) is not dict:_fail('response_invalid')
        if any(k in value for k in ('groundingMetadata','urlContextMetadata')):_fail('response_invalid')
        if 'continuationToken' in value:_fail('incomplete')
        feedback=value.get('promptFeedback',{})
        if type(feedback) is not dict:_fail('response_invalid')
        if feedback.get('blockReason') not in (None,'','BLOCK_REASON_UNSPECIFIED'):_fail('blocked')
        candidates=value.get('candidates')
        if type(candidates) is not list or len(candidates)!=1 or type(candidates[0]) is not dict:_fail('response_invalid')
        candidate=candidates[0]
        if 'continuationToken' in candidate:_fail('incomplete')
        if any(k in candidate for k in ('groundingMetadata','urlContextMetadata')):_fail('response_invalid')
        if 'index' in candidate and (type(candidate['index']) is not int or candidate['index']!=0):_fail('response_invalid')
        finish=candidate.get('finishReason')
        if type(finish) is not str or finish not in _FINISH:_fail('response_invalid')
        self.r['response']['finish_reason']=finish
        for source,destination in [('modelVersion','reported_model_version'),('responseId','provider_response_id')]:
            if source in value:
                item=value[source]
                if type(item) is not str or not _META.fullmatch(item):_fail('response_invalid')
                self.r['response'][destination]=item
        usage=value.get('usageMetadata')
        if usage is not None:
            if type(usage) is not dict:_fail('response_invalid')
            projected={}
            for destination,source in _USAGE.items():
                number=usage.get(source)
                if source in usage and (type(number) is not int or not 0<=number<=_MAXINT):_fail('response_invalid')
                projected[destination]=number
            self.r['usage']=projected
        if finish in {'SAFETY','RECITATION','BLOCKLIST','PROHIBITED_CONTENT','SPII'}:_fail('blocked')
        if finish=='MALFORMED_FUNCTION_CALL':_fail('response_invalid')
        if finish!='STOP':self.r['cancellation']['provider_completion']='observed_incomplete';_fail('incomplete')
        ratings=candidate.get('safetyRatings',[])
        if type(ratings) is not list:_fail('response_invalid')
        for rating in ratings:
            if type(rating) is not dict or 'blocked' in rating and type(rating['blocked']) is not bool:_fail('response_invalid')
            if rating.get('blocked') is True:_fail('blocked')
        content=candidate.get('content')
        if type(content) is not dict or set(content)!={'role','parts'} or content['role']!='model':_fail('response_invalid')
        parts=content['parts']
        if type(parts) is not list or not parts:_fail('response_invalid')
        text=[];size=0
        for part in parts:
            self.check()
            if (type(part) is not dict or not {'text'}<=set(part)<={'text','thought','thoughtSignature'} or
                type(part['text']) is not str or 'thought' in part and type(part['thought']) is not bool or
                'thoughtSignature' in part and type(part['thoughtSignature']) is not str):_fail('response_invalid')
            if part.get('thought',False):self.r['response']['thought_parts']+=1;continue
            b=part['text'].encode('utf-8');size+=len(b)
            if size>2097152:_fail('limit_exceeded')
            text.append(b);self.r['response']['text_parts']+=1
        self.text=b''.join(text)
        if not self.text:_fail('response_invalid')
        self.write('final_text',self.text);self.r['cancellation']['provider_completion']='observed_stop'

    def cleanup(self):
        process=self.process;reaped=None;exitcode=None
        def safe(call,code):
            try:return True,call()
            except _CONTROL as error:self.signal(error);self.secondary(code)
            except Exception:self.secondary(code)
            return False,None
        if process is not None and self.started:
            ok,alive=safe(process.is_alive,'join_timeout')
            if not ok or alive:
                safe(process.terminate,'terminate_failed');safe(lambda:process.join(2),'join_timeout')
                ok,alive=safe(process.is_alive,'join_timeout')
                if not ok or alive:safe(process.kill,'kill_failed');safe(lambda:process.join(2),'join_timeout')
            else:safe(lambda:process.join(0),'join_timeout')
            ok,alive=safe(process.is_alive,'join_timeout');reaped=ok and not alive
            if reaped:
                exitcode=process.exitcode;closed,_=safe(process.close,'transport_close_failed')
                if not closed:
                    self.r['cleanup']['transport_handles_closed']=False;self.error('cleanup_failed','cleanup')
            else:self.error('cleanup_failed','cleanup')
        self.r['cleanup']['worker_reaped']=reaped;self.r['cleanup']['worker_exit_code']=exitcode
        if self.r['cancellation']['requested']:self.r['cancellation']['local_worker_stopped']=reaped
        try:
            self.progress(known=self.result is not None)
            if not self.r['artifacts']['provider_response']['present']:self.collect_body(False)
        except _Fault as error:self.error(error.code)
        except _CONTROL as error:self.signal(error)
        except Exception:self.error('evidence_error')
        if self.r['attempts']['generation_post_attempts']==0:self.r['cancellation']['provider_completion']='not_started'
        elif self.first is not None and self.r['cancellation']['provider_completion'] not in {'observed_stop','observed_incomplete'}:
            self.r['cancellation']['provider_completion']='observed_error' if self.result is not None and self.result['http_status'] is not None and self.result['http_status']!=200 else 'unknown'

    def finalize(self):
        self.r['failure']=self.first;self.r['status']='failed' if self.first else 'complete'
        self.r['verification']['wire_complete']=self.first is None
        self.r['timing']['local_elapsed_seconds']=max(0.0,time.monotonic()-self.start)
        try:
            data=_C(self.r)
            if len(data)>131072:_fail('limit_exceeded')
            _write(self.directory/'receipt.json',data)
        except _CONTROL as error:self.signal(error);self.secondary('receipt_write_failed')
        except Exception:self.error('evidence_error','evidence');self.secondary('receipt_write_failed')
        self.r['failure']=self.first;self.r['status']='failed' if self.first else 'complete';self.r['verification']['wire_complete']=self.first is None


def produce_vertex_response(prompt_bytes: bytes,response_schema_bytes: bytes,*,settings: dict,adc_path: Path,
        evidence_dir: Path,cancel_event: threading.Event | None=None) -> tuple[bytes,dict]:
    """One bounded child/auth/generate attempt; host must reserve credit/budget first."""
    run=None;code='internal_error';control=None;receipt=None
    try:
        if type(prompt_bytes) is not bytes or type(response_schema_bytes) is not bytes:_fail('invalid_input')
        _path(adc_path);_path(evidence_dir)
        if cancel_event is not None and type(cancel_event) is not threading.Event:_fail('invalid_input')
        snapshot=_settings(settings)
        if cancel_event is not None and cancel_event.is_set():_fail('cancelled')
        if len(prompt_bytes)>262144 or len(response_schema_bytes)>65536:_fail('limit_exceeded')
        prompt=_json(prompt_bytes,'invalid_input');schema=_json(response_schema_bytes,'invalid_input')
        if type(prompt) is not dict or type(schema) is not dict or _C(prompt)!=prompt_bytes:_fail('invalid_input')
        credential=_credentials(adc_path,snapshot)
        try:
            if evidence_dir.exists() or evidence_dir.is_symlink():_fail('invalid_input')
            _chain(evidence_dir.parent,'invalid_input')
            if not evidence_dir.parent.is_dir():_fail('invalid_input')
        except OSError:_fail('invalid_input')
        if cancel_event is not None and cancel_event.is_set():_fail('cancelled')
        start=time.monotonic()
        try:evidence_dir.mkdir()
        except OSError:_fail('evidence_error')
        run=_Run(snapshot,evidence_dir,cancel_event,start);run.run(prompt_bytes,response_schema_bytes,credential)
    except _Fault as error:
        code=error.code
        if run is not None:run.error(code)
    except _CONTROL as error:
        control=error
        if run is not None:run.signal(error)
    except OSError:
        code='evidence_error'
        if run is not None:run.error(code)
    except Exception:
        if run is not None:run.error(code)
    if run is not None:
        try:run.cleanup()
        except _CONTROL as error:
            if control is None:control=error
        except Exception:run.error('cleanup_failed','cleanup')
        try:run.finalize()
        except _CONTROL as error:
            if control is None:control=error
        except Exception:run.error('internal_error')
        if control is None:control=run.control
        if run.first is not None:code=run.first['code']
        try:receipt=_copy(run.r)
        except _CONTROL as error:
            if control is None:control=error
        if control is None and run.first is None:return bytes(run.text),receipt
    if control is not None:raise control
    _fixed(code,receipt)
