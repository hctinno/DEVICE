"""One concrete native Codex exchange; no semantic evaluator or model fallback."""
import codecs
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import stat
import subprocess
import threading
import time
import uuid

_CLIENT_VERSIONS=('0.163.0-alpha.11.2','0.164.0-alpha.11.1')
_VERSION=_CLIENT_VERSIONS[0]
_CLIENT_BANNERS={('codex-cli '+version+'\n').encode('ascii'):version for version in _CLIENT_VERSIONS}
_PREFIX='codex_cli_response_'
_CODES={'invalid_input','limit_exceeded','unsupported_client','evidence_error','spawn_failed',
        'timeout','stream_invalid','process_failed','final_mismatch','cleanup_failed','internal_error','cancelled'}
_CONTROL=(KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError)
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z',re.ASCII)
_LIMITS=dict(max_prompt_bytes=262144,max_schema_bytes=65536,max_stdout_bytes=8388608,
    max_stderr_bytes=1048576,max_last_message_bytes=2097152,max_line_bytes=4194304,
    max_events=4096,max_json_depth=32,max_json_nodes=200000,
    min_json_integer=-9223372036854775808,max_json_integer=9223372036854775807,
    max_version_stdout_bytes=4096,max_version_stderr_bytes=65536,max_timeout_seconds=60.0,
    max_version_seconds=5.0,terminate_wait_seconds=2.0,kill_wait_seconds=2.0,reader_close_seconds=2.0)
_LAYOUT=dict(prompt='request.json',response_schema='response-schema.json',invocation='invocation.json',
    version_stdout='version.stdout',version_stderr='version.stderr',stdout_jsonl='stdout.jsonl',
    stderr='stderr.bin',final_text='final-text.bin',last_message='last-message.bin')
_UNKNOWN=['ignore_user_config_effect','ignore_rules_effect','sandbox_effect','ephemeral_effect',
    'all_tools_off','all_mcp_off','all_hooks_off','global_context_absent','managed_overrides_absent',
    'remote_endpoint','remote_account','remote_resolved_model','cli_internal_retries',
    'descendants_reaped','remote_hard_cancel','remote_billing_stopped']


class CodexCliResponseError(RuntimeError):
    """Fixed public code and a detached partial receipt, never raw process errors."""
    def __init__(self,code,receipt=None):
        suffix=code.removeprefix(_PREFIX) if type(code) is str else 'invalid_input'
        self.code=_PREFIX+(suffix if suffix in _CODES else 'invalid_input')
        self.receipt=receipt
        super().__init__(self.code)


class _Failure(Exception):
    def __init__(self,code): self.code=code


def _fail(code): raise _Failure(code)


def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def _sha(data): return hashlib.sha256(data).hexdigest()


def _detached(value): return json.loads(_canonical(value))


def _fixed(code,receipt):
    try: raise CodexCliResponseError(code,receipt) from None
    except CodexCliResponseError as error:
        error.__context__=None;error.__cause__=None
        raise


def _keys(value,required,optional=()):
    return type(value) is dict and set(required)<=set(value)<=set(required)|set(optional)


def _client_versions_match(supported,observed):
    """Exact selected/observed profile agreement, shared by receipt consumers."""
    return type(supported) is str and type(observed) is str and supported in _CLIENT_VERSIONS and observed==supported


def _json(data,invalid):
    """Byte-bound callers, depth pre-scan, bounded ints and exact native JSON."""
    try: text=data.decode('utf-8',errors='strict')
    except UnicodeError: _fail(invalid)
    depth=0;quoted=False;escaped=False
    for char in text:
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True
        elif char in '[{':
            depth+=1
            if depth>_LIMITS['max_json_depth']+1:_fail('limit_exceeded')
        elif char in ']}':depth-=1
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:_fail(invalid)
            result[k]=v
        return result
    def integer(value):
        if len(value)>20:_fail('limit_exceeded')
        parsed=int(value)
        if not _LIMITS['min_json_integer']<=parsed<=_LIMITS['max_json_integer']:_fail('limit_exceeded')
        return parsed
    def constant(_):_fail(invalid)
    try: value=json.loads(text,object_pairs_hook=pairs,parse_int=integer,parse_constant=constant)
    except _Failure:raise
    except (ValueError,UnicodeError,RecursionError):_fail(invalid)
    nodes=0
    def walk(x,level):
        nonlocal nodes
        nodes+=1
        if nodes>_LIMITS['max_json_nodes'] or level>_LIMITS['max_json_depth']:_fail('limit_exceeded')
        if type(x) is str:
            try:x.encode('utf-8')
            except UnicodeError:_fail(invalid)
        elif type(x) is float and not math.isfinite(x):_fail(invalid)
        elif type(x) is dict:
            for k,v in x.items():walk(k,level+1);walk(v,level+1)
        elif type(x) is list:
            for v in x:walk(v,level+1)
    walk(value,0)
    return value


def _path_chain(path):
    for part in (path,*path.parents):
        info=part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
            _fail('invalid_input')


def _preflight(prompt,schema,executable,model,directory,timeout,cancel_event):
    if (type(prompt) is not bytes or type(schema) is not bytes or type(model) is not str or
        model not in {'gpt-6.1-sol','gpt-6-astra'} or type(timeout) not in (int,float) or
        not 0<timeout<=60 or not math.isfinite(timeout) or type(executable) is not type(Path()) or
        type(directory) is not type(Path()) or not executable.is_absolute() or not directory.is_absolute()
        or cancel_event is not None and type(cancel_event) is not threading.Event):
        _fail('invalid_input')
    if len(prompt)>_LIMITS['max_prompt_bytes'] or len(schema)>_LIMITS['max_schema_bytes']:_fail('limit_exceeded')
    value=_json(prompt,'invalid_input');schema_value=_json(schema,'invalid_input')
    if type(value) is not dict or type(schema_value) is not dict or _canonical(value)!=prompt:_fail('invalid_input')
    if os.name!='nt' or executable.name.lower()!='codex.exe':_fail('unsupported_client')
    try:
        if not stat.S_ISREG(executable.lstat().st_mode):_fail('unsupported_client')
        _path_chain(executable)
    except FileNotFoundError:_fail('unsupported_client')
    except OSError:_fail('unsupported_client')
    try:
        if directory.exists() or directory.is_symlink():_fail('invalid_input')
        _path_chain(directory.parent)
        if not stat.S_ISDIR(directory.parent.lstat().st_mode):_fail('invalid_input')
    except OSError:_fail('invalid_input')
    declaration=value.get('expected_producer')
    if not (_keys(declaration,('kind','name')) and declaration['kind']=='model' and
            type(declaration['name']) is str and declaration['name'].strip() and len(declaration['name'])<=200):
        declaration=None
    return declaration


def _descriptor(path):
    return dict(path=path,present=False,bytes=0,sha256=None,complete=False,overflow=False,extent='absent')


def _receipt(model,timeout,exchange,declaration):
    return dict(schema_version=1,kind='codex_cli_response_receipt',exchange_ref=exchange,status='failed',failure=None,
        bindings=dict(prompt_sha256=None,schema_sha256=None,invocation_sha256=None,producer_declaration=declaration),
        client=dict(name='codex_cli',supported_version=_VERSION,observed_version=None,binary_content_sha256=None),
        model=dict(requested=model,resolved=None,cli_thread_id=None,remote_request_id=None),
        attempts=dict(version_process_attempts=0,model_process_attempts=0,application_retries=0,internal_network_requests=None,internal_network_retries=None),
        lifecycle=dict(model_process_started=False,exit_code=None,thread_started=0,turn_started=0,turn_completed=0,
            agent_messages=0,reasoning_items=0,tool_items=0,stdout_eof=False,stderr_eof=False),
        usage=None,cost=dict(kind='not_applicable',amount=None,currency=None,price_version=None),
        timing=dict(timeout_seconds=float(timeout),local_elapsed_seconds=None),
        controls=dict(requested=dict(ignore_user_config=True,ignore_rules=True,sandbox='read-only',ephemeral=True,
            empty_cwd=True,model_local_attempt_cap=1,automatic_retries=0),
            documented=dict(ignore_user_config='config_toml_only',ignore_rules='execpolicy_rules_only',sandbox='model_command_policy',ephemeral='session_rollout_only'),
            observed=dict(argv_submitted=False,argv_exit0=None,empty_cwd_at_spawn=None,tool_items=None),unknown=list(_UNKNOWN)),
        cleanup=dict(version_child_reaped=None,model_child_reaped=None,readers_joined=None,pipes_closed=None,
            artifacts_closed=None,descendants_reaped=None,remote_cancelled=None,secondary_errors=[]),
        artifacts={k:_descriptor(v) for k,v in _LAYOUT.items()},limits=dict(_LIMITS),
        verification=dict(wire_complete=False,remote_identity_verified=False,semantic_quality_verified=False,
            external_data_authority_verified=False,storage_authenticity_verified=False))


class _Protocol:
    def __init__(self,receipt):
        self.r=receipt;self.state='thread';self.opened={};self.closed=set();self.events=0;self.final=None

    def accept(self,data):
        self.events+=1
        if self.events>_LIMITS['max_events']:_fail('limit_exceeded')
        e=_json(data,'stream_invalid')
        if type(e) is not dict or type(e.get('type')) is not str or self.state=='done':_fail('stream_invalid')
        kind=e['type'];counts=self.r['lifecycle']
        if kind=='thread.started':
            counts['thread_started']+=1
            if not _keys(e,('type','thread_id')) or self.state!='thread' or type(e['thread_id']) is not str or not _ID.fullmatch(e['thread_id']):_fail('stream_invalid')
            self.r['model']['cli_thread_id']=e['thread_id'];self.state='turn';return
        if kind=='turn.started':
            counts['turn_started']+=1
            if not _keys(e,('type',)) or self.state!='turn':_fail('stream_invalid')
            self.state='items';return
        if kind=='turn.completed':
            counts['turn_completed']+=1
            if not _keys(e,('type',),('usage',)) or self.state!='items' or self.opened or self.final is None:_fail('stream_invalid')
            if 'usage' in e:
                usage=e['usage'];keys=('input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens')
                if not _keys(usage,(),keys) or any(type(v) is not int or not 0<=v<=_LIMITS['max_json_integer'] for v in usage.values()):_fail('stream_invalid')
                if 'cached_input_tokens' in usage and 'input_tokens' in usage and usage['cached_input_tokens']>usage['input_tokens']:_fail('stream_invalid')
                self.r['usage']={k:usage.get(k) for k in keys}
            self.state='done';return
        if kind in {'error','turn.failed'}:_fail('stream_invalid')
        if kind not in {'item.started','item.updated','item.completed'} or self.state!='items' or not _keys(e,('type','item')):_fail('stream_invalid')
        item=e['item']
        if type(item) is not dict or type(item.get('type')) is not str:_fail('stream_invalid')
        if item['type'] not in {'reasoning','agent_message'}:
            counts['tool_items']+=1;self.r['controls']['observed']['tool_items']=counts['tool_items'];_fail('stream_invalid')
        if not _keys(item,('id','type','text')) or type(item['id']) is not str or not _ID.fullmatch(item['id']) or type(item['text']) is not str:_fail('stream_invalid')
        identity=item['id'];subtype=item['type'];text=item['text'].encode('utf-8')
        if identity in self.closed:_fail('stream_invalid')
        if kind=='item.started':
            if identity in self.opened:_fail('stream_invalid')
            self.opened[identity]=subtype
        elif kind=='item.updated':
            if self.opened.get(identity)!=subtype:_fail('stream_invalid')
        else:
            if identity in self.opened and self.opened.pop(identity)!=subtype:_fail('stream_invalid')
            self.closed.add(identity)
            if subtype=='reasoning':counts['reasoning_items']+=1
            else:
                counts['agent_messages']+=1
                if self.final is not None or not text:_fail('stream_invalid')
                if len(text)>_LIMITS['max_last_message_bytes']:_fail('limit_exceeded')
                self.final=text

    def finish(self):
        if self.state!='done' or self.opened or self.final is None:_fail('stream_invalid')


class _Sink:
    """Main-thread-only artifact owner; reader threads only hand off bytes."""
    def __init__(self,path,desc,cap,utf8=False,capture=False):
        self.path=path;self.desc=desc;self.cap=cap;self.hash=hashlib.sha256();self.eof=False
        self.decoder=codecs.getincrementaldecoder('utf-8')('strict') if utf8 else None
        self.capture=bytearray() if capture else None
        self.handle=path.open('xb',buffering=0)
        desc.update(present=True,sha256=self.hash.hexdigest(),extent='prefix')

    def consume(self,data,validate=True):
        remaining=self.cap-self.desc['bytes'];prefix=data[:remaining]
        if prefix:
            view=memoryview(prefix)
            while view:
                written=self.handle.write(view)
                if not written:raise OSError('artifact_write_failed')
                self.hash.update(view[:written]);self.desc['bytes']+=written;view=view[written:]
            self.desc['sha256']=self.hash.hexdigest()
            if self.capture is not None:self.capture.extend(prefix)
        if len(data)>remaining:self.desc['overflow']=True;_fail('limit_exceeded')
        if validate and self.decoder is not None:
            try:self.decoder.decode(data,final=False)
            except UnicodeError:_fail('stream_invalid')

    def finish(self,validate=True):
        self.eof=True
        self.desc.update(complete=not self.desc['overflow'],extent='prefix' if self.desc['overflow'] else 'whole_file')
        if validate and self.decoder is not None:
            try:self.decoder.decode(b'',final=True)
            except UnicodeError:_fail('stream_invalid')


class _Exchange:
    def __init__(self,directory,executable,model,timeout,start,reference,declaration,cancel_event=None):
        self.directory=directory;self.executable=executable;self.start=start;self.deadline=start+float(timeout)
        self.r=_receipt(model,timeout,reference,declaration);self.first=None;self.control=None;self.phase='evidence'
        self.protocol=_Protocol(self.r);self.line=bytearray();self.last_identity=None;self.last_size=0
        self.response=None;self.tag='codex-cli-response-'+reference[-8:]
        self.cancel_event=cancel_event

    def error(self,code,phase=None):
        if self.first is None:self.first=dict(code=_PREFIX+code,phase=phase or self.phase)

    def signal(self,error):
        if self.control is None:self.control=error
        self.error('internal_error')

    def secondary(self,code):
        values=self.r['cleanup']['secondary_errors']
        if code not in values:
            if len(values)<8:values.append(code)
            else:values[-1]='secondary_overflow'

    def check(self,deadline=None):
        if self.cancel_event is not None:self.throw()
        if time.monotonic()>=(self.deadline if deadline is None else min(self.deadline,deadline)):_fail('timeout')
        if self.cancel_event is not None and self.cancel_event.is_set():_fail('cancelled')

    def throw(self):
        if self.control is not None:raise self.control
        if self.first is not None:raise _Failure(self.first['code'].removeprefix(_PREFIX))

    def write(self,name,data):
        self.check();desc=self.r['artifacts'][name];sink=None
        try:
            sink=_Sink(self.directory/desc['path'],desc,len(data));sink.consume(data);sink.finish()
        except _Failure as error:self.error(error.code);raise
        except _CONTROL as error:self.signal(error);raise
        except OSError:self.error('evidence_error');raise
        except Exception:self.error('internal_error');raise
        finally:
            if sink is not None:self._close_artifact(sink.handle)
        self.throw()

    def _close_artifact(self,handle):
        try:handle.close()
        except _CONTROL as error:
            self.signal(error);self.secondary('artifact_close_failed');self._combined('artifacts_closed',False)
        except Exception:
            self.error('cleanup_failed','cleanup');self.secondary('artifact_close_failed');self._combined('artifacts_closed',False)

    def setup(self,prompt,schema):
        self.r['bindings'].update(prompt_sha256=_sha(prompt),schema_sha256=_sha(schema))
        self.write('prompt',prompt);self.write('response_schema',schema)
        work=self.directory/'work';self.check();work.mkdir()
        executable=str(self.executable)
        self.version_argv=[executable,'--version']
        self.model_argv=[executable,'exec','--ignore-user-config','--ignore-rules','--sandbox','read-only',
            '--ephemeral','--skip-git-repo-check','--color','never','--json','--model',self.r['model']['requested'],
            '--output-schema',str(self.directory/_LAYOUT['response_schema']),
            '--output-last-message',str(self.directory/_LAYOUT['last_message']),'-']
        return work

    def invocation(self,work):
        self.phase='evidence'
        invocation=dict(schema_version=1,kind='codex_cli_invocation',exchange_ref=self.r['exchange_ref'],
            executable=str(self.executable),cwd=str(work),version_argv=self.version_argv,model_argv=self.model_argv,
            requested_model=self.r['model']['requested'],supported_version=self.r['client']['supported_version'],
            timeout_seconds=self.r['timing']['timeout_seconds'],prompt_sha256=self.r['bindings']['prompt_sha256'],
            response_schema_sha256=self.r['bindings']['schema_sha256'])
        data=_canonical(invocation);self.r['bindings']['invocation_sha256']=_sha(data);self.write('invocation',data)

    def stdout(self,data):
        pos=0
        while pos<len(data):
            end=data.find(b'\n',pos);end=len(data) if end<0 else end+1
            part=data[pos:end]
            if len(part)>_LIMITS['max_line_bytes']-len(self.line):_fail('limit_exceeded')
            self.line.extend(part);pos=end
            if self.line.endswith(b'\n'):
                if len(self.line)==1:_fail('stream_invalid')
                self.protocol.accept(bytes(self.line[:-1]));self.line.clear()
                if self.protocol.final is not None and not self.r['artifacts']['final_text']['present']:
                    self.write('final_text',self.protocol.final)

    def last(self,final=False):
        path=self.directory/_LAYOUT['last_message'];desc=self.r['artifacts']['last_message']
        try:before=path.lstat()
        except FileNotFoundError:
            if self.last_identity is not None:_fail('evidence_error')
            if final:_fail('final_mismatch')
            return
        if not stat.S_ISREG(before.st_mode) or getattr(before,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:_fail('evidence_error')
        identity=(before.st_dev,before.st_ino)
        if self.last_identity is not None and (identity!=self.last_identity or before.st_size<self.last_size):_fail('evidence_error')
        self.last_identity=identity;self.last_size=before.st_size;cap=_LIMITS['max_last_message_bytes']
        handle=None
        try:
            handle=path.open('rb',buffering=0)
            opened=os.fstat(handle.fileno())
            if (opened.st_dev,opened.st_ino)!=identity:_fail('evidence_error')
            data=handle.read(cap+1);after=os.fstat(handle.fileno())
        except _Failure as error:self.error(error.code);raise
        except _CONTROL as error:self.signal(error);raise
        except OSError:self.error('evidence_error');raise
        except Exception:self.error('internal_error');raise
        finally:
            if handle is not None:self._close_artifact(handle)
        self.throw()
        current=path.lstat()
        if (current.st_dev,current.st_ino)!=identity or getattr(current,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:_fail('evidence_error')
        prefix=data[:cap];overflow=len(data)>cap or max(before.st_size,after.st_size,current.st_size)>cap
        desc.update(present=True,bytes=len(prefix),sha256=_sha(prefix),complete=False,overflow=overflow,extent='prefix')
        if overflow:_fail('limit_exceeded')
        if final:
            if len(data)!=after.st_size or after.st_size!=current.st_size:_fail('evidence_error')
            desc.update(complete=True,extent='whole_file')
            try:data.decode('utf-8',errors='strict')
            except UnicodeError:_fail('stream_invalid')
            if data!=self.protocol.final:_fail('final_mismatch')
            self.response=data

    def _combined(self,key,value):
        prior=self.r['cleanup'][key];self.r['cleanup'][key]=value if prior is None else prior and value

    def cleanup(self,process,stop,threads,sinks,kind):
        stop.set();reaped=None
        def safe(call,code):
            try:return True,call()
            except _CONTROL as error:self.signal(error);self.secondary(code)
            except Exception:self.secondary(code)
            return False,None
        if process is not None:
            ok,status=safe(process.poll,'wait_failed')
            if not ok or status is None:
                safe(process.terminate,'terminate_failed')
                ok,_=safe(lambda:process.wait(timeout=_LIMITS['terminate_wait_seconds']),'wait_failed')
                if not ok:
                    safe(process.kill,'kill_failed')
                    ok,_=safe(lambda:process.wait(timeout=_LIMITS['kill_wait_seconds']),'wait_failed')
            else:ok,_=safe(lambda:process.wait(timeout=0),'wait_failed')
            reaped=ok
        self.r['cleanup'][kind+'_child_reaped']=reaped
        close_deadline=time.monotonic()+_LIMITS['reader_close_seconds'];closers=[];errors=queue.Queue(maxsize=8)
        pipes=[] if process is None else [p for p in (process.stdin,process.stdout,process.stderr) if p is not None]
        def close(handle,code):
            try:handle.close()
            except BaseException as error:errors.put_nowait((code,error))
        for handle,code in [(p,'pipe_close_failed') for p in pipes]+[(s.handle,'artifact_close_failed') for s in sinks]:
            thread=threading.Thread(target=close,args=(handle,code),daemon=True,name=self.tag+'-close');closers.append((thread,code));thread.start()
        for thread in threads+[t for t,_ in closers]:
            safe(lambda t=thread:t.join(timeout=max(0,close_deadline-time.monotonic())),'reader_join_timeout')
        readers_ok=all(not t.is_alive() for t in threads)
        if not readers_ok:self.secondary('reader_join_timeout')
        pipes_ok=True;files_ok=True
        for thread,code in closers:
            if thread.is_alive():
                self.secondary(code)
                if code=='pipe_close_failed':pipes_ok=False
                else:files_ok=False
        while not errors.empty():
            code,error=errors.get_nowait();self.secondary(code)
            if isinstance(error,_CONTROL):self.signal(error)
            if code=='pipe_close_failed':pipes_ok=False
            else:files_ok=False
        self._combined('readers_joined',readers_ok);self._combined('pipes_closed',pipes_ok);self._combined('artifacts_closed',files_ok)
        if reaped is False or not readers_ok or not pipes_ok or not files_ok:self.error('cleanup_failed','cleanup')

    def process(self,kind,argv,prompt,work):
        self.phase='version' if kind=='version' else 'spawn';self.check()
        process=None;sinks=[];threads=[];stop=threading.Event();queues=[];writer=queue.Queue(maxsize=1)
        deadline=min(self.deadline,time.monotonic()+_LIMITS['max_version_seconds']) if kind=='version' else self.deadline
        names=('version_stdout','version_stderr') if kind=='version' else ('stdout_jsonl','stderr')
        caps=(_LIMITS['max_version_stdout_bytes'],_LIMITS['max_version_stderr_bytes']) if kind=='version' else (_LIMITS['max_stdout_bytes'],_LIMITS['max_stderr_bytes'])
        def put(target,item):
            while not stop.is_set() and time.monotonic()<deadline:
                try:target.put(item,timeout=.05);return
                except queue.Full:pass
        def reader(pipe,target,cap):
            count=0
            try:
                while not stop.is_set() and count<=cap:
                    data=os.read(pipe.fileno(),min(65536,cap+1-count))
                    if not data:put(target,('eof',None));return
                    count+=len(data);put(target,('data',data))
            except BaseException as error:put(target,('error',error))
        def write_stdin(pipe):
            try:
                view=memoryview(prompt)
                while view and not stop.is_set() and time.monotonic()<deadline:
                    amount=os.write(pipe.fileno(),view[:65536])
                    if not amount:raise OSError('stdin_closed')
                    view=view[amount:]
                pipe.close();put(writer,('done',None))
            except BaseException as error:put(writer,('error',error))
        try:
            for name,cap in zip(names,caps):
                sinks.append(_Sink(self.directory/_LAYOUT[name],self.r['artifacts'][name],cap,utf8=kind=='model',capture=kind=='version'))
            if kind=='model':
                self.r['controls']['observed']['empty_cwd_at_spawn']=not any(work.iterdir())
                if not self.r['controls']['observed']['empty_cwd_at_spawn']:_fail('evidence_error')
            self.check(deadline);self.r['attempts'][kind+'_process_attempts']+=1
            if kind=='model':self.r['cost']['kind']='unknown';self.r['controls']['observed']['argv_submitted']=True
            try:
                process=subprocess.Popen(argv,stdin=subprocess.PIPE if kind=='model' else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(work),shell=False,bufsize=0,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            except OSError:_fail('spawn_failed')
            if kind=='model':self.r['lifecycle']['model_process_started']=True
            self.phase='version' if kind=='version' else 'collect'
            for pipe,cap in zip((process.stdout,process.stderr),caps):
                target=queue.Queue(maxsize=2);queues.append(target)
                thread=threading.Thread(target=reader,args=(pipe,target,cap),daemon=True,name=self.tag+'-reader');threads.append(thread);thread.start()
            writer_done=kind=='version'
            if kind=='model':
                thread=threading.Thread(target=write_stdin,args=(process.stdin,),daemon=True,name=self.tag+'-writer');threads.append(thread);thread.start()
            next_last=0
            while True:
                self.check(deadline)
                for i,(target,sink) in enumerate(zip(queues,sinks)):
                    if sink.eof:continue
                    try:event,data=target.get(timeout=.005)
                    except queue.Empty:continue
                    if event=='data':
                        sink.consume(data)
                        if kind=='model' and i==0:self.stdout(data)
                    elif event=='eof':
                        sink.finish()
                        if kind=='model':
                            self.r['lifecycle']['stdout_eof' if i==0 else 'stderr_eof']=True
                            if i==0:
                                if self.line:_fail('stream_invalid')
                                self.protocol.finish()
                    else:
                        if isinstance(data,_CONTROL):raise data
                        _fail('stream_invalid')
                if not writer_done:
                    try:event,data=writer.get_nowait()
                    except queue.Empty:pass
                    else:
                        if event=='error':
                            if isinstance(data,_CONTROL):raise data
                            _fail('stream_invalid')
                        writer_done=True
                if kind=='model' and time.monotonic()>=next_last:self.last();next_last=time.monotonic()+.05
                code=process.poll()
                if code is not None and kind=='model':
                    self.r['lifecycle']['exit_code']=code;self.r['controls']['observed']['argv_exit0']=code==0
                    if code!=0:_fail('process_failed')
                if code is not None and all(s.eof for s in sinks) and writer_done:
                    if kind=='version':
                        version=_CLIENT_BANNERS.get(bytes(sinks[0].capture))
                        if code!=0 or version is None or sinks[1].desc['bytes']:_fail('unsupported_client')
                        self.r['client'].update(supported_version=version,observed_version=version)
                    else:
                        self.phase='completion';self.protocol.finish();self.last(final=True)
                        self.r['controls']['observed']['tool_items']=self.r['lifecycle']['tool_items']
                    break
        except _Failure as error:self.error(error.code)
        except _CONTROL as error:self.signal(error)
        except OSError:self.error('evidence_error')
        except Exception:self.error('internal_error')
        finally:
            stop.set()
            for target,sink in zip(queues,sinks):
                while True:
                    try:event,data=target.get_nowait()
                    except queue.Empty:break
                    except _CONTROL as error:self.signal(error);break
                    if event=='data':
                        try:sink.consume(data,validate=False)
                        except _Failure as error:self.error(error.code)
                        except _CONTROL as error:self.signal(error)
                        except Exception:self.error('evidence_error')
                    elif event=='eof':sink.finish(validate=False)
                    elif isinstance(data,_CONTROL):self.signal(data)
            self.cleanup(process,stop,threads,sinks,kind)
        self.throw()

    def finalize(self):
        self.r['failure']=self.first;self.r['status']='failed' if self.first else 'complete'
        self.r['verification']['wire_complete']=self.first is None
        self.r['timing']['local_elapsed_seconds']=max(0.0,time.monotonic()-self.start)
        handle=None
        try:
            handle=(self.directory/'receipt.json').open('xb',buffering=0)
            view=memoryview(_canonical(self.r))
            while view:
                amount=handle.write(view)
                if not amount:raise OSError('receipt_write_failed')
                view=view[amount:]
        except _CONTROL as error:self.signal(error);self.secondary('receipt_write_failed')
        except Exception:self.error('evidence_error','evidence');self.secondary('receipt_write_failed')
        finally:
            if handle is not None:
                try:handle.close()
                except _CONTROL as error:
                    self.signal(error);self.secondary('receipt_write_failed');self._combined('artifacts_closed',False)
                except Exception:
                    self.error('evidence_error','evidence');self.secondary('receipt_write_failed');self._combined('artifacts_closed',False)
        self.r['failure']=self.first;self.r['status']='failed' if self.first else 'complete'
        self.r['verification']['wire_complete']=self.first is None


def produce_codex_cli_response(prompt_bytes: bytes,response_schema_bytes: bytes,*,executable: Path,
        requested_model: str,evidence_dir: Path,timeout_seconds: int | float=60.0,cancel_event=None) -> tuple[bytes,dict]:
    """Return one immutable final text and a detached receipt, or one fixed error."""
    exchange=None;control=None;code='internal_error';receipt=None
    try:
        declaration=_preflight(prompt_bytes,response_schema_bytes,executable,requested_model,evidence_dir,timeout_seconds,cancel_event)
        if cancel_event is not None and cancel_event.is_set():_fail('cancelled')
        start=time.monotonic();reference='codex-cli-exchange:'+uuid.uuid4().hex
        try:evidence_dir.mkdir()
        except OSError:_fail('evidence_error')
        exchange=_Exchange(evidence_dir,executable,requested_model,timeout_seconds,start,reference,declaration,cancel_event)
        work=exchange.setup(prompt_bytes,response_schema_bytes)
        exchange.process('version',exchange.version_argv,b'',work)
        exchange.invocation(work)
        exchange.process('model',exchange.model_argv,prompt_bytes,work)
    except _Failure as error:
        code=error.code
        if exchange is not None:exchange.error(code)
    except _CONTROL as error:
        control=error
        if exchange is not None:exchange.signal(error)
    except OSError:
        code='evidence_error'
        if exchange is not None:exchange.error(code)
    except Exception:
        if exchange is not None:exchange.error(code)
    if exchange is not None:
        try:exchange.finalize()
        except _CONTROL as error:
            if control is None:control=error
        except Exception:exchange.error('internal_error')
        if control is None:control=exchange.control
        if exchange.first is not None:code=exchange.first['code']
        try:receipt=_detached(exchange.r)
        except _CONTROL as error:
            if control is None:control=error
        if control is None and exchange.first is None:return bytes(exchange.response),receipt
    if control is not None:raise control
    _fixed(code,receipt)
