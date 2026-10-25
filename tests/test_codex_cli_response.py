"""Contract tests with real local pipes and a substituted Python child; provider0."""
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

try:
    api=importlib.import_module('labflow.codex_cli_response')
except ModuleNotFoundError as error:
    if error.name!='labflow.codex_cli_response': raise
    api=None

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'docs/fcc/codex_cli_response_contract.json').read_text(encoding='utf-8'))['contracts']
SCHEMA=CONTRACT['analysis_schema']['literal_utf8'].encode('utf-8')
RAW=b' {"transport_only": 1}\n'
PROMPT=json.dumps({'expected_producer':{'kind':'model','name':'dgm-codex-cli-v1'},'messages':[]},sort_keys=True,separators=(',',':')).encode('utf-8')
REAL_POPEN=subprocess.Popen

CHILD=r'''
import json,os,sys,time
from pathlib import Path
def deny(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):raise AssertionError('NETWORK_FORBIDDEN_IN_TEST')
sys.addaudithook(deny)
c=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));mode=c['mode'];stage=sys.argv[2]
if stage=='version':
    if mode=='version_hang': time.sleep(30)
    if mode=='version_flood': os.write(1,b'x'*4097)
    elif mode=='version_bad': os.write(1,b'wrong-version-secret\n')
    else: os.write(1,b'codex-cli 0.163.0-alpha.11.2\n')
    if mode=='version_stderr': os.write(2,b'fake-version-secret')
    sys.exit(0)
last=Path(sys.argv[3]);wire=bytes.fromhex(c['wire'])
if mode=='stdin_stall': time.sleep(30)
data=sys.stdin.buffer.read()
assert data==(Path.cwd().parent/'request.json').read_bytes()
if mode=='hang': os.write(1,b'{"type":');time.sleep(30)
if mode=='stderr_flood': os.write(2,b'x'*1048577);time.sleep(.1);sys.exit(0)
if mode=='stderr_invalid': os.write(2,b'\xff')
if mode=='stderr_secret': os.write(2,b'FAKE_SECRET_DO_NOT_ECHO https://fake.invalid/header')
if mode=='last_directory': last.mkdir()
elif mode!='last_missing': last.write_bytes(b'\xff' if mode=='last_invalid' else b'x'*2097153 if mode=='last_flood' else wire+b'\n' if mode=='last_mismatch' else wire)
if mode=='last_replace':
    time.sleep(.2);other=last.with_name('replacement.bin');other.write_bytes(wire);os.replace(other,last);time.sleep(.2)
events=[{'type':'thread.started','thread_id':'fake-thread-1'},{'type':'turn.started'},
        {'type':'item.completed','item':{'id':'a1','type':'agent_message','text':wire.decode('utf-8')}},
        {'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':2,'output_tokens':3}}]
if mode=='no_usage': events[-1].pop('usage')
elif mode=='reasoning': events[2:2]=[{'type':'item.started','item':{'id':'r1','type':'reasoning','text':''}},{'type':'item.updated','item':{'id':'r1','type':'reasoning','text':'bounded fake reasoning'}},{'type':'item.completed','item':{'id':'r1','type':'reasoning','text':'bounded fake reasoning'}}]
elif mode=='duplicate_thread': events.insert(1,events[0])
elif mode=='duplicate_turn': events.insert(2,events[1])
elif mode=='unknown_event': events[1]={'type':'unknown.event'}
elif mode=='unknown_key': events[0]['extra']='untrusted'
elif mode=='bad_id': events[0]['thread_id']='bad id'
elif mode=='duplicate_final': events.insert(3,events[2])
elif mode=='missing_final': del events[2]
elif mode=='dangling': events.insert(2,{'type':'item.started','item':{'id':'open1','type':'reasoning','text':''}})
elif mode=='bad_update': events.insert(2,{'type':'item.updated','item':{'id':'unopened','type':'reasoning','text':''}})
elif mode=='unknown_item_key': events[2]['item']['phase']='final_answer'
elif mode=='item_type_list': events[2]['item']['type']=[]
elif mode=='item_type_dict': events[2]['item']['type']={}
elif mode in ('tool','refusal'): events[2]['item']['type']='command_execution' if mode=='tool' else 'refusal'
elif mode=='error': events[2]={'type':'error','message':'FAKE_SECRET_DO_NOT_ECHO'}
elif mode=='turn_failed': events[-1]={'type':'turn.failed','error':{'message':'FAKE_SECRET_DO_NOT_ECHO'}}
elif mode=='usage_bool': events[-1]['usage']['input_tokens']=True
elif mode=='usage_negative': events[-1]['usage']['input_tokens']=-1
elif mode=='usage_cached': events[-1]['usage']['cached_input_tokens']=11
elif mode=='usage_unknown': events[-1]['usage']['private_header']='FAKE_SECRET_DO_NOT_ECHO'
elif mode=='premature_complete': events[2:]=[events[-1],events[2]]
elif mode=='after_complete': events.append({'type':'turn.started'})
elif mode=='events_flood': events=events[:2]+[{'type':'item.completed','item':{'id':'r'+str(i),'type':'reasoning','text':''}} for i in range(4096)]
elif mode=='stdout_flood': events=events[:2]+[{'type':'item.completed','item':{'id':'r'+str(i),'type':'reasoning','text':'x'*2097152}} for i in range(5)]
elif mode=='nodes': events[1]['padding']=[0]*200000
elif mode=='depth':
    v=None
    for _ in range(40):v=[v]
    events[1]['padding']=v
output=b''.join(json.dumps(e,ensure_ascii=False,separators=(',',':')).encode('utf-8')+b'\n' for e in events)
if mode=='no_lf': output=output[:-1]
elif mode=='empty_line': output=b'\n'+output
elif mode=='malformed': output=b'{broken}\n'
elif mode=='stdout_invalid': output=b'\xff\n'
elif mode=='duplicate_key': output=b'{"type":"turn.started","type":"turn.started"}\n'
elif mode=='line_flood': output=b'x'*4194305+b'\n'
os.write(1,output)
if mode=='late_exit':time.sleep(30)
sys.exit(7 if mode=='nonzero' else 0)
'''


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api,'Assigned concrete producer API must exist before GREEN')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.exe=self.root/'codex.exe';self.exe.write_bytes(b'LOCAL_TEST_DOUBLE_ONLY')
        self.script=self.root/'child.py';self.script.write_text(CHILD,encoding='utf-8')
        self.control=self.root/'control.json';self.calls=[];self.children=[];self.counter=0;self.mode='normal';self.model_started=False
        self.addCleanup(self.cleanup_children)

    def cleanup_children(self):
        live=[]
        for child in self.children:
            if child.poll() is None:live.append(child);child.kill()
            child.wait(timeout=3)
        self.assertEqual(live,[], 'Producer left its directly observed child alive')

    def spawn(self,argv,**kwargs):
        self.calls.append(list(argv));self.assertFalse(kwargs['shell']);self.assertEqual(kwargs['bufsize'],0)
        stage='version' if argv[1:] == ['--version'] else 'model'
        if stage=='model':self.model_started=True
        if self.mode=='spawn_error' and stage=='model':raise OSError('FAKE_SECRET_DO_NOT_ECHO '+str(self.root))
        last=str(Path(argv[argv.index('--output-last-message')+1])) if stage=='model' else '-'
        child=REAL_POPEN([sys.executable,'-B','-u',str(self.script),str(self.control),stage,last],**kwargs)
        self.children.append(child);return child

    def call(self,mode='normal',*,wire=RAW,prompt=PROMPT,schema=SCHEMA,model='gpt-6.1-sol',timeout=3,**overrides):
        self.mode=mode;self.counter+=1;self.evidence=self.root/('exchange-'+str(self.counter))
        self.control.write_text(json.dumps({'mode':mode,'wire':wire.hex()}),encoding='utf-8')
        options=dict(executable=self.exe,requested_model=model,evidence_dir=self.evidence,timeout_seconds=timeout);options.update(overrides)
        with patch.object(api.subprocess,'Popen',side_effect=self.spawn):
            return api.produce_codex_cli_response(prompt,schema,**options)

    def failure(self,mode,code,**kwargs):
        with self.assertRaises(api.CodexCliResponseError) as caught:self.call(mode,**kwargs)
        e=caught.exception;expected='codex_cli_response_'+code
        self.assertEqual((e.code,str(e),e.args),(expected,expected,(expected,)))
        self.assertIsNone(e.__context__);self.assertIsNone(e.__cause__)
        self.assertNotIn('FAKE_SECRET',str(e));self.assertNotIn(str(self.root),str(e))
        if e.receipt is not None:
            self.assertEqual(e.receipt['status'],'failed');self.assertFalse(e.receipt['verification']['wire_complete'])
            self.assertEqual(e.receipt['failure']['code'],expected)
            self.assertNotIn('FAKE_SECRET',json.dumps(e.receipt));self.assertNotIn(str(self.root),json.dumps(e.receipt))
        return e

    def shape(self,value,schema):
        if 'anyOf' in schema:
            choices=schema['anyOf'];self.shape(value,next(s for s in choices if (s.get('type')=='null')==(value is None)));return
        if 'const' in schema:self.assertEqual(value,schema['const'])
        if 'enum' in schema:self.assertIn(value,schema['enum'])
        kind=schema.get('type')
        if kind=='object':
            self.assertIs(type(value),dict);self.assertEqual(set(value),set(schema['properties']))
            for k,v in value.items():self.shape(v,schema['properties'][k])
        elif kind=='array':
            self.assertIs(type(value),list)
            for v in value:self.shape(v,schema['items'])
        elif kind=='integer':self.assertIs(type(value),int)
        elif kind=='boolean':self.assertIs(type(value),bool)
        elif kind=='number':self.assertIn(type(value),(int,float))
        elif kind=='string':self.assertIs(type(value),str)
        elif kind=='null':self.assertIsNone(value)

    def test_public_signature_exact(self):
        sig=inspect.signature(api.produce_codex_cli_response)
        self.assertEqual(list(sig.parameters),['prompt_bytes','response_schema_bytes','executable','requested_model','evidence_dir','timeout_seconds'])
        for name in list(sig.parameters)[2:]:self.assertEqual(sig.parameters[name].kind,inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(sig.parameters['timeout_seconds'].default,60.0)

    def test_success_tuple_receipt_and_original_artifacts(self):
        result=self.call();self.assertIs(type(result),tuple);self.assertEqual(len(result),2)
        wire,r=result;self.assertIs(type(wire),bytes);self.assertEqual(wire,RAW);self.shape(r,CONTRACT['receipt'])
        self.assertEqual(r,json.loads((self.evidence/'receipt.json').read_bytes()))
        for desc in r['artifacts'].values():
            b=(self.evidence/desc['path']).read_bytes();self.assertTrue(desc['complete']);self.assertEqual(desc['extent'],'whole_file')
            self.assertEqual((len(b),hashlib.sha256(b).hexdigest()),(desc['bytes'],desc['sha256']))
        self.assertEqual((self.evidence/'request.json').read_bytes(),PROMPT);self.assertEqual((self.evidence/'response-schema.json').read_bytes(),SCHEMA)
        self.assertEqual(r['model']['requested'],'gpt-6.1-sol');self.assertIsNone(r['model']['resolved']);self.assertIsNone(r['model']['remote_request_id'])
        self.assertEqual(r['usage'],dict(input_tokens=10,cached_input_tokens=2,output_tokens=3,reasoning_output_tokens=None))
        self.assertEqual(r['controls']['unknown'],CONTRACT['controls_unknown_exact16']);self.assertEqual(r['limits'],CONTRACT['limits'])
        self.assertEqual(len(self.calls),2);self.assertEqual(self.calls[0],[str(self.exe),'--version'])
        invocation=json.loads((self.evidence/'invocation.json').read_bytes());self.assertEqual(invocation['model_argv'],self.calls[1]);self.assertEqual(len(self.calls[1]),18)
        self.assertTrue(all(r['cleanup'][k] for k in ['version_child_reaped','model_child_reaped','readers_joined','pipes_closed','artifacts_closed']))
        r['artifacts'].clear();self.assertEqual(len(json.loads((self.evidence/'receipt.json').read_bytes())['artifacts']),9)

    def test_two_models_same_prompt_schema_and_neutral_declaration(self):
        receipts=[]
        for model in CONTRACT['public_function']['requested_models']:
            _,r=self.call(model=model);receipts.append(r)
        self.assertEqual(receipts[0]['bindings']['prompt_sha256'],receipts[1]['bindings']['prompt_sha256'])
        self.assertEqual(receipts[0]['bindings']['schema_sha256'],receipts[1]['bindings']['schema_sha256'])
        self.assertNotEqual(receipts[0]['exchange_ref'],receipts[1]['exchange_ref'])
        self.assertEqual(receipts[0]['bindings']['producer_declaration'],{'kind':'model','name':'dgm-codex-cli-v1'})

    def test_literal_schema_format_and_text_are_not_normalized(self):
        schema=b' { "type" : "object" }\n';wire=' {"text":"\ud55c\uae00"}\n'.encode('utf-8')
        returned,r=self.call(wire=wire,schema=schema);self.assertEqual(returned,wire)
        self.assertEqual((self.evidence/'response-schema.json').read_bytes(),schema)
        self.assertEqual(r['bindings']['schema_sha256'],hashlib.sha256(schema).hexdigest())

    def test_optional_usage_and_reasoning_lifecycle(self):
        _,r=self.call('no_usage');self.assertIsNone(r['usage']);self.assertEqual(r['cost']['kind'],'unknown');self.assertIsNone(r['cost']['amount'])
        _,r=self.call('reasoning');self.assertEqual(r['lifecycle']['reasoning_items'],1)
        _,r=self.call(prompt=b'{"x":1}');self.assertIsNone(r['bindings']['producer_declaration'])

    def test_native_argument_types_and_keyword_contract(self):
        class Bytes(bytes):pass
        class PathLike:
            def __fspath__(self):raise AssertionError('must not call hook')
        for change in [dict(prompt='text'),dict(prompt=Bytes(PROMPT)),dict(schema=bytearray(SCHEMA)),dict(executable=str(self.exe)),dict(executable=PathLike()),dict(evidence_dir=str(self.root/'new'))]:
            with self.subTest(change=change):self.assertIsNone(self.failure('normal','invalid_input',**change).receipt)
        self.assertEqual(self.calls,[])

    def test_models_and_timeouts_fail_before_process_or_evidence(self):
        for model in ('gpt-6-astra-pro','',True,None):self.failure('normal','invalid_input',model=model)
        for timeout in (True,0,-1,61,float('nan'),float('inf'),'60'):self.failure('normal','invalid_input',timeout=timeout)
        self.assertEqual(self.calls,[]);self.assertFalse(self.evidence.exists())

    def test_malformed_noncanonical_duplicate_and_native_json_limits(self):
        for data in (b'{',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":"\\ud800"}',b'\xff',b'[]',b'{ "x": 1 }',b'{"x":1}\n'):
            with self.subTest(data=data):self.failure('normal','invalid_input',prompt=data)
        self.failure('normal','limit_exceeded',prompt=b'x'*262145)
        self.failure('normal','limit_exceeded',schema=b'x'*65537)
        self.failure('normal','limit_exceeded',prompt=b'{"n":9223372036854775808}')
        self.failure('normal','limit_exceeded',prompt=b'{"n":'+b'9'*1000+b'}')
        nested=None
        for _ in range(40):nested=[nested]
        self.failure('normal','limit_exceeded',prompt=json.dumps({'x':nested},sort_keys=True,separators=(',',':')).encode())
        self.assertEqual(self.calls,[])

    def test_schema_is_strict_json_object_without_rewriting(self):
        for data in (b'[]',b'{"x":Infinity}',b'{"type":"object","type":"array"}',b'\xef\xbb\xbf{}'):
            self.failure('normal','invalid_input',schema=data)
        self.assertEqual(self.calls,[])

    def test_paths_existing_destination_and_nonregular_client(self):
        self.failure('normal','invalid_input',executable=Path('codex.exe'))
        self.failure('normal','invalid_input',evidence_dir=Path('relative'))
        self.failure('normal','invalid_input',evidence_dir=self.root)
        self.failure('normal','unsupported_client',executable=self.root/'missing.exe')
        self.failure('normal','unsupported_client',executable=self.root)
        self.assertEqual(self.calls,[])

    def test_version_failures_do_not_attempt_model(self):
        for mode in ('version_bad','version_stderr'):
            before=len(self.calls);e=self.failure(mode,'unsupported_client');self.assertEqual(len(self.calls)-before,1)
            self.assertEqual(e.receipt['attempts']['model_process_attempts'],0);self.assertEqual(e.receipt['cost']['kind'],'not_applicable')
        self.failure('version_flood','limit_exceeded')

    def test_stream_error_cohort_never_becomes_response(self):
        for mode in ('duplicate_thread','duplicate_turn','unknown_event','unknown_key','bad_id','duplicate_final','missing_final','dangling','bad_update','unknown_item_key','tool','refusal','error','turn_failed','usage_bool','usage_negative','usage_cached','usage_unknown','premature_complete','after_complete','no_lf','empty_line','malformed','stdout_invalid','stderr_invalid','duplicate_key'):
            with self.subTest(mode=mode):
                before=len(self.calls);self.failure(mode,'stream_invalid');self.assertEqual(len(self.calls)-before,2)

    def test_stdout_line_event_node_depth_and_stderr_caps(self):
        for mode in ('line_flood','events_flood','stdout_flood','stderr_flood','nodes','depth'):
            with self.subTest(mode=mode):
                e=self.failure(mode,'limit_exceeded');self.assertEqual(e.receipt['attempts']['model_process_attempts'],1)
                for desc in e.receipt['artifacts'].values():
                    if desc['present']:
                        b=(self.evidence/desc['path']).read_bytes()[:desc['bytes']]
                        self.assertEqual(hashlib.sha256(b).hexdigest(),desc['sha256'])

    def test_last_message_missing_mismatch_invalid_oversize_and_replacement(self):
        for mode,code in [('last_missing','final_mismatch'),('last_mismatch','final_mismatch'),('last_invalid','stream_invalid'),('last_flood','limit_exceeded'),('last_directory','evidence_error'),('last_replace','evidence_error')]:
            with self.subTest(mode=mode):self.failure(mode,code)

    def test_nonzero_exit_and_spawn_error_keep_private_evidence(self):
        e=self.failure('nonzero','process_failed');self.assertEqual(e.receipt['lifecycle']['exit_code'],7)
        e=self.failure('spawn_error','spawn_failed');self.assertEqual(e.receipt['attempts']['model_process_attempts'],1)
        self.assertFalse(e.receipt['lifecycle']['model_process_started'])

    def test_timeout_partial_stdout_late_exit_and_stdin_stall_are_bounded(self):
        for mode in ('hang','late_exit','stdin_stall','version_hang'):
            with self.subTest(mode=mode):
                prompt=json.dumps({'padding':'x'*200000},sort_keys=True,separators=(',',':')).encode() if mode=='stdin_stall' else PROMPT
                start=time.monotonic();e=self.failure(mode,'timeout',prompt=prompt,timeout=.25)
                self.assertLess(time.monotonic()-start,7)
                self.assertLessEqual(e.receipt['attempts']['model_process_attempts'],1)
                self.assertEqual(e.receipt['attempts']['application_retries'],0)

    def test_public_receipt_and_error_do_not_echo_stderr_or_exception(self):
        _,r=self.call('stderr_secret');self.assertNotIn('FAKE_SECRET',json.dumps(r))
        self.assertIn(b'FAKE_SECRET',(self.evidence/'stderr.bin').read_bytes())
        try:raise ValueError('FAKE_SECRET_DO_NOT_ECHO')
        except ValueError:self.failure('spawn_error','spawn_failed')

    def test_control_exceptions_before_model_and_after_spawn_keep_identity(self):
        for signal in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            original=signal('FAKE_SECRET_DO_NOT_ECHO')
            with patch.object(api.subprocess,'Popen',side_effect=original):
                self.counter+=1
                with self.assertRaises(signal) as got:
                    api.produce_codex_cli_response(PROMPT,SCHEMA,executable=self.exe,requested_model='gpt-6.1-sol',evidence_dir=self.root/('control-'+str(self.counter)))
            self.assertIs(got.exception,original)
        for signal in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            original=signal('FAKE_SECRET_DO_NOT_ECHO');fired=False;self.model_started=False;get=queue.Queue.get
            def interrupt(q,*args,**kwargs):
                nonlocal fired
                if self.model_started and not fired and threading.current_thread() is threading.main_thread():fired=True;raise original
                return get(q,*args,**kwargs)
            with patch.object(queue.Queue,'get',new=interrupt):
                with self.assertRaises(signal) as got:self.call('late_exit')
            self.assertTrue(fired);self.assertIs(got.exception,original)

    def test_only_declared_public_function_and_no_background_reader_leak(self):
        self.call();self.assertFalse(any(t.name.startswith('codex-cli-response-') for t in threading.enumerate()))
        names=[n for n,v in vars(api).items() if inspect.isfunction(v) and v.__module__==api.__name__ and not n.startswith('_')]
        self.assertEqual(names,['produce_codex_cli_response'])

    def test_review_huge_timeout_is_invalid_before_evidence(self):
        e=self.failure('normal','invalid_input',timeout=10**1000)
        self.assertIsNone(e.receipt);self.assertEqual(self.calls,[]);self.assertFalse(self.evidence.exists())

    def test_review_nonstring_item_types_are_stream_invalid(self):
        for mode in ['item_type_list','item_type_dict']:
            with self.subTest(mode=mode):self.failure(mode,'stream_invalid')

    def test_review_reparse_inputs_and_last_message_fail_closed(self):
        import stat
        original=Path.lstat
        def reparse(path,*args,**kwargs):
            value=original(path,*args,**kwargs)
            if path==self.exe or path.name=='last-message.bin':
                return types.SimpleNamespace(st_mode=value.st_mode,st_dev=value.st_dev,st_ino=value.st_ino,
                    st_size=value.st_size,st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return value
        with patch.object(Path,'lstat',new=reparse):
            e=self.failure('normal','invalid_input');self.assertIsNone(e.receipt);self.assertEqual(self.calls,[])
        def last_reparse(path,*args,**kwargs):
            return reparse(path,*args,**kwargs) if path.name=='last-message.bin' else original(path,*args,**kwargs)
        with patch.object(Path,'lstat',new=last_reparse):self.failure('normal','evidence_error')

    def test_review_evidence_and_receipt_IO_keep_partial_first_error(self):
        original=Path.open
        for target,mode,expected in [('request.json','normal','evidence_error'),('stdout.jsonl','normal','evidence_error'),
                ('receipt.json','normal','evidence_error'),('receipt.json','malformed','stream_invalid')]:
            with self.subTest(target=target,mode=mode):
                def broken(path,*args,**kwargs):
                    if path.name==target and args and 'x' in args[0]:raise OSError('FAKE_WRITE_SECRET '+str(path))
                    return original(path,*args,**kwargs)
                with patch.object(Path,'open',new=broken):e=self.failure(mode,expected)
                self.assertIsNotNone(e.receipt)
                if target=='receipt.json':self.assertIn('receipt_write_failed',e.receipt['cleanup']['secondary_errors'])

    def test_review_control_during_file_IO_survives_close_failure(self):
        original_open=Path.open
        for target in ['request.json','last-message.bin','receipt.json']:
            for signal in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
                original=signal('FAKE_ORIGINAL_CONTROL');reached=[]
                class Broken:
                    def __init__(self,stream):self.stream=stream
                    def __getattr__(self,name):return getattr(self.stream,name)
                    def __enter__(self):return self
                    def __exit__(self,*args):self.close()
                    def write(self,data):reached.append('write');raise original
                    def read(self,*args):reached.append('read');raise original
                    def close(self):self.stream.close();raise OSError('FAKE_CLOSE_SECRET')
                def opened(path,*args,**kwargs):
                    stream=original_open(path,*args,**kwargs)
                    return Broken(stream) if path.name==target and args and args[0] in ('xb','rb') else stream
                with self.subTest(target=target,signal=signal.__name__):
                    with patch.object(Path,'open',new=opened):
                        with self.assertRaises(signal) as got:self.call()
                    self.assertTrue(reached);self.assertIs(got.exception,original)

    def test_review_artifact_close_failure_and_first_stream_error(self):
        original_open=Path.open
        class Broken:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def close(self):self.stream.close();raise OSError('FAKE_CLOSE_SECRET')
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return Broken(stream) if path.name=='stdout.jsonl' and args and args[0]=='xb' else stream
        for mode,code in [('normal','cleanup_failed'),('malformed','stream_invalid')]:
            with patch.object(Path,'open',new=opened):e=self.failure(mode,code)
            self.assertFalse(e.receipt['cleanup']['artifacts_closed']);self.assertIn('artifact_close_failed',e.receipt['cleanup']['secondary_errors'])

    def test_review_native_kill_wait_faults_preserve_timeout(self):
        original_spawn=self.spawn;reached=[]
        def spawn(argv,**kwargs):
            child=original_spawn(argv,**kwargs)
            if len(argv)>2:
                kill=child.kill
                def failed_terminate():reached.append('terminate');raise OSError('FAKE_TERMINATE_SECRET')
                def killed_with_error():reached.append('kill');kill();raise OSError('FAKE_KILL_SECRET')
                child.terminate=failed_terminate;child.kill=killed_with_error
            return child
        with patch.object(self,'spawn',new=spawn):e=self.failure('hang','timeout',timeout=1)
        self.assertEqual(e.receipt['attempts']['model_process_attempts'],1)
        self.assertEqual(reached,['terminate','kill']);self.assertTrue(e.receipt['cleanup']['model_child_reaped'])
        self.assertEqual(e.receipt['cleanup']['secondary_errors'][:3],['terminate_failed','wait_failed','kill_failed'])

    def test_review_slow_artifact_close_is_bounded_failure(self):
        original_open=Path.open;release=threading.Event();entered=threading.Event()
        class Slow:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def close(self):entered.set();release.wait(5);self.stream.close()
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return Slow(stream) if path.name=='stdout.jsonl' and args and args[0]=='xb' else stream
        start=time.monotonic()
        try:
            with patch.object(Path,'open',new=opened):e=self.failure('normal','cleanup_failed')
            self.assertTrue(entered.is_set());self.assertLess(time.monotonic()-start,4)
            self.assertFalse(e.receipt['cleanup']['artifacts_closed']);self.assertIn('artifact_close_failed',e.receipt['cleanup']['secondary_errors'])
        finally:
            release.set()
            for thread in threading.enumerate():
                if thread.name.startswith('codex-cli-response-'):thread.join(3)


if __name__=='__main__':unittest.main()
