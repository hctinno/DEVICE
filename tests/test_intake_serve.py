"""047 CLI boundaries; lifecycle doubles are distinct from genuine HTTP children."""
import importlib
import importlib.util
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import urlsplit

from labflow.store import Store, StoreOpenError
from test_ui_server import ReferenceFixture


class IntakeServeTests(unittest.TestCase):
    def api(self):
        return importlib.import_module('labflow.intake_serve')

    def state(self):
        if not hasattr(self, '_state'):
            local=Path(__file__).resolve().parents[1]/'.local';local.mkdir(exist_ok=True)
            temporary = tempfile.TemporaryDirectory(prefix='serve047-', dir=local)
            self.addCleanup(temporary.cleanup); self.fixture = ReferenceFixture(temporary.name)
            self._state = Store.open_existing(str(self.fixture.legacy.root)); self.addCleanup(self._state.close)
        return self._state

    def argv(self, scope='metadata', ids=()):
        return ['--workspace', str(Path.cwd() / '.local' / 'explicit047'), '--port', '0', '--read-scope', scope,
                *[part for ident in ids for part in ('--intake-id', ident)]]

    def invoke(self, arguments, *, server=None, stdout=None, stderr=None, host_error=None, close_store=None):
        api = self.api(); store = self.state(); events = []
        if store._existing_binding.state != 'open':
            store = Store.open_existing(str(self.fixture.legacy.root)); self._state = store; self.addCleanup(store.close)
        if server is None:
            server = SimpleNamespace(server_port=54321, serve_forever=mock.Mock(side_effect=lambda:events.append('serve')),
                                     server_close=mock.Mock(side_effect=lambda:events.append('host.close')))
        stdout = io.StringIO() if stdout is None else stdout; stderr = io.StringIO() if stderr is None else stderr
        actual_close = store.close
        def closed():
            events.append('store.close')
            return actual_close() if close_store is None else close_store()
        with mock.patch.object(Store, 'open_existing', return_value=store) as opened, \
                mock.patch.object(api._ui, 'create_server', return_value=server, side_effect=host_error) as factory, \
                mock.patch.object(store, 'close', side_effect=closed), \
                mock.patch.object(sys, 'stdout', stdout), mock.patch.object(sys, 'stderr', stderr):
            status = api.main(arguments)
        return status, stdout, stderr, opened, factory, server, events

    def test_module_and_main_exist(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.intake_serve'))
        self.assertTrue(callable(self.api().main))

    def test_help_has_no_store_or_host_and_preserves_caller_streams(self):
        api = self.api()
        class CallerStream(io.StringIO):
            def reconfigure(self, **kwargs): raise AssertionError('caller stream reconfigured')
        out, err = CallerStream(), CallerStream()
        with mock.patch.object(Store, 'open_existing') as opened, mock.patch.object(api._ui, 'create_server') as host, \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            self.assertEqual(api.main(['--help']), 0)
        opened.assert_not_called(); host.assert_not_called(); self.assertFalse(out.closed); self.assertFalse(err.closed)
        self.assertIn('--read-scope', out.getvalue()); self.assertEqual(err.getvalue(), '')

    def test_invalid_argv_is_fixed2_without_store_or_host(self):
        api = self.api(); valid = self.argv()
        class Text(str): pass
        rows = [[], None, 'bad', {}, [1], [Text('--help')], ['--help','extra'], valid[:-1], valid+['extra'],
                valid+['--port','1'], ['--workspace=C:/state',*valid[2:]], [*valid[:2],'--port','00',*valid[4:]],
                [*valid[:2],'--port','65536',*valid[4:]], [*valid[:2],'--port','-1',*valid[4:]],
                [*valid[:2],'--port','1.0',*valid[4:]], [*valid[:2],'--port','1'*10000,*valid[4:]],
                ['--workspace','relative',*valid[2:]], ['--workspace','C:/'+('a'*32768),*valid[2:]],
                ['--workspace','C:/'+('한'*11000),*valid[2:]],
                ['--workspace','C:/bad\ud800',*valid[2:]], self.argv('unknown'), self.argv('metadata',['A']),
                self.argv('workspace',['A']), self.argv('intakes'), self.argv('intakes',['A','A']),
                self.argv('intakes',['A'*151]), self.argv('intakes',['한글']), self.argv('intakes',['-A']),
                self.argv('intakes',['A'+str(i) for i in range(101)])]
        with mock.patch.object(Store, 'open_existing') as opened, mock.patch.object(api._ui, 'create_server') as host:
            for row in rows:
                with self.subTest(shape=type(row).__name__):
                    out, err = io.StringIO(), io.StringIO()
                    with mock.patch.object(sys, 'argv', ['entry','bad']), mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
                        self.assertEqual(api.main(row), 2)
                    self.assertEqual(out.getvalue(), '')
                    self.assertEqual(json.loads(err.getvalue()), {'error':{'code':'intake_reference_server_invalid_argument'}})
        opened.assert_not_called(); host.assert_not_called()

    def test_scope_exact_mapping_and_100_IDs_of150_are_not_silently_reduced(self):
        ids = ['A' + 'a'*146 + str(i).zfill(3) for i in range(100)]
        for mode, values, expected in [('metadata',[],()),('workspace',[],'workspace'),('intakes',ids,tuple(ids))]:
            with self.subTest(mode=mode):
                status, out, err, opened, factory, server, _ = self.invoke(self.argv(mode, values))
                self.assertEqual(status, 0); self.assertEqual(err.getvalue(), '')
                opened.assert_called_once_with(self.argv()[1])
                factory.assert_called_once_with(self.state().root, host='127.0.0.1', port=0,
                    intake_reference_store=self.state(), intake_reference_read_scope=expected)
                server.serve_forever.assert_called_once(); server.server_close.assert_called_once()
                ready = json.loads(out.getvalue()); self.assertEqual(set(ready), {'schema_version','kind','url','store_mode'})
                self.assertEqual(ready, {'schema_version':1,'kind':'intake_reference_server_ready',
                    'url':'http://127.0.0.1:54321/','store_mode':'open_existing'})
                self.assertEqual(out.getvalue().count('\n'), 1); self.assertLessEqual(len(out.getvalue().encode()),1024)

    def test_None_uses_sys_argv_and_raw_workspace_reaches_official_opener(self):
        api = self.api(); raw = str(Path.cwd() / '.local') + '\\.'
        error = StoreOpenError('store_open_path_invalid'); out, err = io.StringIO(), io.StringIO()
        args = ['--workspace',raw,'--port','0','--read-scope','metadata']
        with mock.patch.object(sys, 'argv', ['entry',*args]), mock.patch.object(sys,'stdout',out), mock.patch.object(sys,'stderr',err), \
                mock.patch.object(Store,'open_existing',side_effect=error) as opened, mock.patch.object(api._ui,'create_server') as host:
            self.assertEqual(api.main(),2)
        opened.assert_called_once_with(raw); host.assert_not_called(); self.assertEqual(out.getvalue(),'')
        self.assertEqual(json.loads(err.getvalue())['error']['code'],'store_open_path_invalid')

    def test_exact_StoreOpenError9_preserved_and_other_exceptions_sanitized(self):
        api = self.api()
        suffixes = 'invalid_argument path_invalid unavailable schema_mismatch input_changed integrity_invalid closed backend_unavailable mode_unsupported'.split()
        class Derived(StoreOpenError):
            def __str__(self): raise AssertionError('raw exception string read')
        invalid = StoreOpenError('store_open_unavailable'); invalid.code = 'store_open_SECRET'
        values = [(StoreOpenError('store_open_'+s),'store_open_'+s,2 if s in {'invalid_argument','path_invalid'} else 1) for s in suffixes]
        values += [(invalid,'intake_reference_server_unavailable',1),(Derived('store_open_path_invalid'),'intake_reference_server_unavailable',1),
                   (OSError('PRIVATE SQL path'),'intake_reference_server_unavailable',1)]
        for error, code, status in values:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(Store,'open_existing',side_effect=error), mock.patch.object(api._ui,'create_server') as host, \
                    mock.patch.object(sys,'stdout',out), mock.patch.object(sys,'stderr',err):
                self.assertEqual(api.main(self.argv()),status)
            host.assert_not_called(); self.assertEqual(out.getvalue(),'')
            self.assertEqual(json.loads(err.getvalue()),{'error':{'code':code}}); self.assertLessEqual(len(err.getvalue().encode()),256)

    def test_host_unavailable_never_falls_back_or_serves_and_closes_borrowed_Store(self):
        status,out,err,opened,factory,server,events = self.invoke(self.argv(),host_error=TypeError('unsupported keywords PRIVATE'))
        self.assertEqual(status,1); self.assertEqual(out.getvalue(),''); opened.assert_called_once(); factory.assert_called_once()
        self.assertEqual(json.loads(err.getvalue())['error']['code'],'intake_reference_server_host_unavailable')
        server.serve_forever.assert_not_called(); server.server_close.assert_not_called(); self.assertEqual(events,['store.close'])

    def test_ready_short_write_or_flush_failure_never_serves_and_first_error_survives_cleanup(self):
        class Short(io.StringIO):
            def write(self, text): super().write(text[:-1]); return len(text)-1
        class Flush(io.StringIO):
            def flush(self): raise OSError('PRIVATE flush')
        for stream in (Short(), Flush()):
            host = SimpleNamespace(server_port=54321,serve_forever=mock.Mock(),server_close=mock.Mock(side_effect=[OSError('host'),None]))
            attempts=[]
            def close():
                attempts.append(1)
                if len(attempts)==1:raise OSError('store')
            status,_,err,_,_,_,_ = self.invoke(self.argv(),stdout=stream,server=host,close_store=close)
            self.assertEqual(status,1); self.assertEqual(json.loads(err.getvalue())['error']['code'],'intake_reference_server_output_failed')
            host.serve_forever.assert_not_called(); self.assertEqual(host.server_close.call_count,2); self.assertEqual(len(attempts),2)

    def test_closed_caller_output_does_not_escape_or_close_other_streams(self):
        closed = io.StringIO(); closed.close(); status,_,err,_,_,server,_=self.invoke(self.argv(),stdout=closed)
        self.assertEqual(status,1); server.serve_forever.assert_not_called(); self.assertFalse(err.closed)
        self.assertEqual(json.loads(err.getvalue())['error']['code'],'intake_reference_server_output_failed')

    def test_normal_and_KeyboardInterrupt_serve_always_close_host_before_Store(self):
        for error in (None, KeyboardInterrupt()):
            events=[]
            def serve():
                events.append('serve')
                if error is not None:raise error
            host=SimpleNamespace(server_port=54321,serve_forever=mock.Mock(side_effect=serve),server_close=mock.Mock(side_effect=lambda:events.append('host.close')))
            status,_,err,_,_,_,_=self.invoke(self.argv(),server=host,close_store=lambda:events.append('store.close'))
            self.assertEqual(status,0); self.assertEqual(err.getvalue(),''); self.assertEqual(events,['serve','host.close','store.close'])

    def test_repeated_interrupt_and_one_ordinary_retry_preserve_first_error(self):
        host=SimpleNamespace(server_port=54321,serve_forever=mock.Mock(side_effect=KeyboardInterrupt()),
                             server_close=mock.Mock(side_effect=[KeyboardInterrupt(),KeyboardInterrupt(),OSError('PRIVATE host'),None]))
        values=iter([KeyboardInterrupt(),OSError('PRIVATE store'),None]); attempts=[]
        def close():
            attempts.append(1); value=next(values)
            if value is not None:raise value
        status,_,err,_,_,_,_=self.invoke(self.argv(),server=host,close_store=close)
        self.assertEqual(status,1); self.assertEqual(host.server_close.call_count,4); self.assertEqual(len(attempts),3)
        self.assertEqual(json.loads(err.getvalue())['error']['code'],'intake_reference_server_unavailable')

    def test_startup_KeyboardInterrupt_is_not_ready_and_does_not_bind(self):
        api=self.api();out,err=io.StringIO(),io.StringIO()
        with mock.patch.object(Store,'open_existing',side_effect=KeyboardInterrupt()),mock.patch.object(api._ui,'create_server') as host, \
                mock.patch.object(sys,'stdout',out),mock.patch.object(sys,'stderr',err):self.assertEqual(api.main(self.argv()),0)
        self.assertEqual((out.getvalue(),err.getvalue()),('',''));host.assert_not_called()

    def test_missing_real_workspace_is_not_created(self):
        api=self.api()
        (Path.cwd()/'.local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='serve047-missing-',dir=Path.cwd()/'.local') as temporary:
            target=Path(temporary)/'absent';args=['--workspace',str(target),'--port','0','--read-scope','metadata'];out,err=io.StringIO(),io.StringIO()
            with mock.patch.object(sys,'stdout',out),mock.patch.object(sys,'stderr',err):status=api.main(args)
            self.assertEqual(status,1);self.assertFalse(target.exists());self.assertEqual(out.getvalue(),'')
            self.assertEqual(json.loads(err.getvalue())['error']['code'],'store_open_unavailable')

    def test_error_flush_interrupt_does_not_resend_a_second_frame(self):
        api=self.api()
        class Interrupted(io.StringIO):
            count=0
            def flush(self):
                self.count+=1
                if self.count==1:raise KeyboardInterrupt()
        out,err=io.StringIO(),Interrupted()
        with mock.patch.object(sys,'stdout',out),mock.patch.object(sys,'stderr',err):self.assertEqual(api.main(['bad']),2)
        self.assertEqual(err.getvalue().count('\n'),1)
        self.assertEqual(json.loads(err.getvalue()),{'error':{'code':'intake_reference_server_invalid_argument'}})

    def test_module_configuration_interrupt_is_quiet_stop_before_main(self):
        api=self.api()
        class Interrupted(io.StringIO):
            def reconfigure(self,**kwargs):raise KeyboardInterrupt()
        with mock.patch.object(sys,'stdout',Interrupted()),mock.patch.object(sys,'stderr',io.StringIO()),mock.patch.object(api,'main') as main:
            self.assertEqual(api._process_main(),0)
        main.assert_not_called()

    def test_real_module_help_and_broken_output_have_quiet_fixed_exit(self):
        root=Path(__file__).resolve().parents[1]
        normal=subprocess.run([sys.executable,'-X','utf8','-B','-m','labflow.intake_serve','--help'],cwd=root,capture_output=True,timeout=10)
        self.assertEqual(normal.returncode,0);self.assertEqual(normal.stderr,b'');self.assertNotIn(b'\r\n',normal.stdout)
        for descriptor,args,expected in [(1,['--help'],1),(2,['bad'],2)]:
            code='import os,runpy,sys;os.close('+str(descriptor)+');sys.argv='+repr(['labflow.intake_serve',*args])+";runpy.run_module('labflow.intake_serve',run_name='__main__')"
            child=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=root,capture_output=True,timeout=10)
            self.assertEqual(child.returncode,expected);self.assertNotIn(b'Traceback',child.stderr);self.assertNotIn(b'Exception ignored',child.stderr)
            if descriptor==1:self.assertEqual(json.loads(child.stderr)['error']['code'],'intake_reference_server_output_failed')


_CHILD = r'''
import _thread,hashlib,json,os,runpy,sqlite3,sys,threading,time
from pathlib import Path
root=Path(sys.argv[1]);control=Path(sys.argv[2]);workspace=Path(sys.argv[3]);mode=sys.argv[4];args=sys.argv[5:]
sys.path.insert(0,str(root))
from labflow.store import Store
stats={'creating_Store':0,'open_existing':0,'factory':0,'serve':0,'host_close':0,'Store_close':0,'parent':[],'parser_calls':0,
       'source_opens':0,'source_bytes':0,'SQLite_open':0,'SQLite_C_close':0,'SQL_write_requests':0,'KI_sent':0}
owned=[];objects={};original_connect=sqlite3.connect;original_open=Path.open
class Stream:
 def __init__(self,value):self.value=value
 def __getattr__(self,name):return getattr(self.value,name)
 def __enter__(self):self.value.__enter__();return self
 def __exit__(self,*args):return self.value.__exit__(*args)
 def read(self,*args):
  value=self.value.read(*args);stats['source_bytes']+=len(value);return value
def opened(path,*args,**kwargs):
 value=original_open(path,*args,**kwargs)
 if path.parent==workspace/'blobs':stats['source_opens']+=1;return Stream(value)
 return value
def connected(*args,**kwargs):
 assert kwargs.get('uri') is True and str(args[0]).endswith('?mode=ro')
 con=original_connect(*args,**kwargs);owned.append(con);stats['SQLite_open']+=1
 write_names=('INSERT','UPDATE','DELETE','CREATE_INDEX','CREATE_TABLE','CREATE_TEMP_INDEX','CREATE_TEMP_TABLE',
  'CREATE_TEMP_TRIGGER','CREATE_TEMP_VIEW','CREATE_TRIGGER','CREATE_VIEW','DROP_INDEX','DROP_TABLE',
  'DROP_TEMP_INDEX','DROP_TEMP_TABLE','DROP_TEMP_TRIGGER','DROP_TEMP_VIEW','DROP_TRIGGER','DROP_VIEW',
  'ALTER_TABLE','REINDEX','ANALYZE','CREATE_VTABLE','DROP_VTABLE','ATTACH','DETACH')
 writes={getattr(sqlite3,'SQLITE_'+name) for name in write_names}
 def authorize(action,*args):
  if action in writes:stats['SQL_write_requests']+=1
  return sqlite3.SQLITE_OK
 con.set_authorizer(authorize);return con
def save():
 (control/'proof.json').write_text(json.dumps(stats,sort_keys=True),encoding='utf-8')
def profile(frame,event,arg):
 package,name=frame.f_globals.get('__name__'),frame.f_code.co_name
 if event=='c_return' and getattr(arg,'__name__',None)=='close' and any(getattr(arg,'__self__',None) is c for c in owned):stats['SQLite_C_close']+=1
 if package=='labflow.store' and name=='open_existing':
  if event=='call':stats['open_existing']+=1
  elif event=='return' and type(arg) is Store:objects['store']=arg
 if package=='labflow.store' and name=='__init__' and event=='call' and type(frame.f_locals.get('self')) is Store:stats['creating_Store']+=1
 if package=='labflow.ui_server' and name=='create_server':
  if event=='call':stats['factory']+=1
  elif event=='return' and arg is not None:
   objects['server']=arg;stats['port']=arg.server_port
   original_service=arg.service_actions;original_wait=arg._reference_runtime.changed.wait;repeats=[0]
   def service():
    if (control/'interrupt').exists():stats['KI_sent']+=1;raise KeyboardInterrupt()
    return original_service()
   def wait(timeout=None):
    if (control/'repeat').exists() and repeats[0]<2:
     repeats[0]+=1;stats['KI_sent']+=1;raise KeyboardInterrupt()
    return original_wait(timeout)
   arg.service_actions=service;arg._reference_runtime.changed.wait=wait
 if package=='labflow.ui_server' and name=='serve_forever' and event=='call':stats['serve']+=1
 if package=='labflow.ui_server' and name=='server_close' and event=='call':
  stats['host_close']+=1;stats['active_at_host_close']=frame.f_locals['self']._reference_runtime.active
  (control/'closing').write_text('1',encoding='ascii')
 if package=='labflow.intake_reference_review' and name=='read_reference_review' and event=='call':
  action=frame.f_locals['request']['action'];stats['parent'].append(action)
  if action=='current' and (control/'block').exists():
   (control/'entered').write_text('1',encoding='ascii')
   while not (control/'release').exists():time.sleep(.01)
 if package=='labflow.document_extract' and name=='extract_document' and event=='call':stats['parser_calls']+=1
 if package=='labflow.store' and name=='close' and type(frame.f_locals.get('self')) is Store:
  if event=='call':
   stats['Store_close']+=1;server=objects.get('server')
   if server:
    rt=server._reference_runtime
    stats['at_Store_close']={'active':rt.active,'workers':len(rt.worker_refs),'clients':len(rt.clients),'loop':rt.loop_thread is not None,'socket':server.socket.fileno()}
  elif event=='return':
   stats['native_handles_after']=len(objects['store']._existing_binding.handles);save()
sqlite3.connect=connected;Path.open=opened;sys.setprofile(profile);threading.setprofile(profile)
if mode=='closed_stdout':os.close(1)
sys.argv=['labflow.intake_serve',*args]
runpy.run_module('labflow.intake_serve',run_name='__main__')
'''


class IntakeServeChildTests(unittest.TestCase):
    def fixture_child(self, scope, *, mode='normal', block=False):
        root=Path(__file__).resolve().parents[1]
        (root/'.local').mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(prefix='serve047-real-',dir=root/'.local');self.addCleanup(temporary.cleanup)
        folder=Path(temporary.name);fixture=ReferenceFixture(folder/'input');control=folder/'control';control.mkdir()
        script=folder/'child.py';script.write_text(_CHILD,encoding='utf-8')
        args=['--workspace',str(fixture.legacy.root),'--port','0','--read-scope',scope]
        if scope=='intakes':args+=['--intake-id',fixture.intake_id]
        if block:(control/'block').write_text('1',encoding='ascii')
        before=self.snapshot(fixture.root)
        def preserve():
            archive=root/'.local/INTAKE-SERVE-047/child-evidence'/folder.name
            archive.mkdir(parents=True,exist_ok=False)
            shutil.copytree(fixture.root,archive/'input');shutil.copytree(control,archive/'control');shutil.copy2(script,archive/'child.py')
            (archive/'before.json').write_text(json.dumps(before),encoding='utf-8')
        self.addCleanup(preserve)
        process=subprocess.Popen([sys.executable,'-X','utf8','-B',str(script),str(root),str(control),str(fixture.legacy.root),mode,*args],
            cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def stop():
            if process.poll() is None:
                process.kill();out,err=process.communicate(timeout=10)
                (control/'cleanup-kill-stdout.bin').write_bytes(out);(control/'cleanup-kill-stderr.bin').write_bytes(err)
        self.addCleanup(stop)
        return process,fixture,control,before

    def snapshot(self, root):
        files={p.relative_to(root).as_posix():(p.stat().st_size,p.stat().st_dev,p.stat().st_ino,p.stat().st_mtime_ns,p.stat().st_mode,
               hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob('*') if p.is_file()}
        db=root/'state/lab.sqlite3';con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        try:sql=hashlib.sha256('\n'.join(con.iterdump()).encode('utf-8')).hexdigest()
        finally:con.close()
        return files,sql

    def ready(self, process):
        lines=[];done=threading.Event()
        def read():
            try:lines.append(process.stdout.readline())
            finally:done.set()
        reader=threading.Thread(target=read,daemon=True);reader.start();self.assertTrue(done.wait(10));reader.join(2)
        raw=lines[0];self.assertFalse(b'\r\n' in raw);value=json.loads(raw)
        self.assertEqual(set(value),{'schema_version','kind','url','store_mode'})
        self.assertEqual((value['schema_version'],value['kind'],value['store_mode']),(1,'intake_reference_server_ready','open_existing'))
        address=urlsplit(value['url']);self.assertEqual(address.hostname,'127.0.0.1');self.assertNotIn(address.port,{8765,8766})
        return address.port

    def http(self, port, path, method='GET', *, cookie=None, csrf=None, body=None):
        headers={}
        if cookie:headers['Cookie']=cookie
        if method=='POST':headers.update({'Origin':'http://127.0.0.1:'+str(port),'Sec-Fetch-Site':'same-origin',
            'Content-Type':'application/json; charset=utf-8','X-Intake-Reference-CSRF':csrf or '0'*64})
        con=http.client.HTTPConnection('127.0.0.1',port,timeout=8)
        try:
            con.request(method,path,body=body,headers=headers);r=con.getresponse();return r.status,dict(r.getheaders()),r.read()
        finally:con.close()

    def wait_file(self, path):
        deadline=time.monotonic()+8
        while not path.exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(path.exists())

    def moves(self, fixture, blocked):
        paths=[fixture.legacy.db,fixture.legacy.root/'blobs',fixture.legacy.root,fixture.root]
        allowed=Path(__file__).resolve().parents[1]/'.local';count=0
        for path in paths:
            target=path.with_name(path.name+'.moved')
            self.assertTrue(path.resolve().is_relative_to(allowed.resolve()));self.assertTrue(target.resolve().is_relative_to(allowed.resolve()))
            try:path.rename(target)
            except OSError:
                if not blocked:raise
                count+=1
            else:
                target.rename(path)
                if blocked:self.fail('native pin released while child is running')
                count+=1
        return count

    def finish(self, process, fixture, control, before, port, expected=0):
        stdout,stderr=process.communicate(timeout=12);self.assertEqual(process.returncode,expected)
        self.assertEqual(stdout,b'')
        if expected==0:self.assertEqual(stderr,b'')
        else:self.assertEqual(json.loads(stderr)['error']['code'],'intake_reference_server_output_failed')
        proof=json.loads((control/'proof.json').read_text(encoding='utf-8'))
        self.assertEqual((proof['creating_Store'],proof['open_existing'],proof['factory']),(0,1,1))
        self.assertGreaterEqual(proof['host_close'],1);self.assertGreaterEqual(proof['Store_close'],1)
        self.assertEqual(proof['at_Store_close'],{'active':0,'workers':0,'clients':0,'loop':False,'socket':-1})
        self.assertEqual(proof['native_handles_after'],0);self.assertEqual(proof['SQLite_open'],proof['SQLite_C_close'])
        self.assertEqual(proof['SQL_write_requests'],0);self.assertEqual(self.snapshot(fixture.root),before)
        self.assertEqual(proof['parser_calls'],0)
        self.assertEqual(self.moves(fixture,False),4)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);probe.bind(('127.0.0.1',port))
        return proof

    def test_actual_module_metadata_scope_HTTP_and_native_cleanup(self):
        process,fixture,control,before=self.fixture_child('metadata');port=self.ready(process)
        route='/api/intake-references/'+fixture.intake_id
        status,headers,raw=self.http(port,route+'/history');self.assertEqual(status,200);self.assertEqual(len(json.loads(raw)),7)
        self.assertEqual(headers['X-Intake-Reference-Read-Allowed'],'false');self.assertFalse('X-Intake-Reference-CSRF' in headers)
        cookie=headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.http(port,route+'/history','HEAD',cookie=cookie)[2],b'')
        self.assertEqual(self.http(port,route+'/current','POST',cookie=cookie)[0],403)
        self.assertEqual(self.moves(fixture,True),4)
        (control/'interrupt').write_text('1',encoding='ascii')
        proof=self.finish(process,fixture,control,before,port)
        self.assertEqual(proof['parent'],['history','history']);self.assertEqual(proof['source_opens'],0)
        self.evidence={'kind':'047_actual_module_metadata','parent_history':2,'source_opens':0,'closed_SQLite':proof['SQLite_C_close'],
                       'controlled_KI':1,'native_blocked_released':[4,4],'inputs_SQL_unchanged':True,'own_port_rebound':True}

    def test_actual_module_scoped_current_abort_and_repeated_interrupt_drain(self):
        process,fixture,control,before=self.fixture_child('intakes',block=True);port=self.ready(process)
        route='/api/intake-references/'+fixture.intake_id
        status,headers,_=self.http(port,route+'/history');self.assertEqual(status,200)
        cookie=headers['Set-Cookie'].split(';')[0];csrf=headers['X-Intake-Reference-CSRF']
        self.assertEqual(self.http(port,'/api/intake-references/OTHER/current','POST',cookie=cookie,csrf=csrf)[0],403)
        raw=socket.create_connection(('127.0.0.1',port),timeout=8)
        body=b'{"schema_version":1,"action":"current"}'
        request=(f'POST {route}/current HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nOrigin: http://127.0.0.1:{port}\r\n'
                 f'Sec-Fetch-Site: same-origin\r\nContent-Type: application/json\r\nCookie: {cookie}\r\n'
                 f'X-Intake-Reference-CSRF: {csrf}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode()+body
        try:
            raw.sendall(request);self.wait_file(control/'entered')
            self.assertEqual(self.http(port,route+'/current','POST',cookie=cookie,csrf=csrf,body=body)[0],429)
            raw.shutdown(socket.SHUT_RDWR);raw.close()
            (control/'interrupt').write_text('1',encoding='ascii');self.wait_file(control/'closing')
            (control/'repeat').write_text('1',encoding='ascii');time.sleep(.16)
            self.assertIsNone(process.poll());self.assertFalse((control/'proof.json').exists());self.assertEqual(self.moves(fixture,True),4)
        finally:
            raw.close();(control/'release').write_text('1',encoding='ascii')
        proof=self.finish(process,fixture,control,before,port)
        self.assertEqual(proof['parent'],['history','current']);self.assertGreater(proof['source_bytes'],0);self.assertEqual(proof['KI_sent'],3)
        self.evidence={'kind':'047_actual_module_current_abort_drain','actual_current':1,'busy':429,'delivery':'unknown; client aborted',
                       'controlled_KI_sent':3,'Store_close_waited_parent_host':True,'source_bytes':proof['source_bytes'],
                       'SQLite_closed':proof['SQLite_C_close'],'native_blocked_released':[4,4],'inputs_SQL_unchanged':True}

    def test_actual_module_closed_output_and_forced_kill_are_distinct(self):
        process,fixture,control,before=self.fixture_child('metadata',mode='closed_stdout')
        stdout,stderr=process.communicate(timeout=12);self.assertEqual(process.returncode,1);self.assertEqual(stdout,b'')
        self.assertEqual(json.loads(stderr)['error']['code'],'intake_reference_server_output_failed')
        proof=json.loads((control/'proof.json').read_text(encoding='utf-8'));self.assertEqual(proof['serve'],0);self.assertEqual(proof['parent'],[])
        self.assertEqual((proof['host_close'],proof['Store_close'],proof['native_handles_after']),(1,1,0));self.assertEqual(self.snapshot(fixture.root),before)
        self.assertEqual(self.moves(fixture,False),4)
        with socket.socket() as probe:probe.bind(('127.0.0.1',proof['port']))
        killed,fixture2,control2,before2=self.fixture_child('metadata');port=self.ready(killed);self.assertEqual(self.moves(fixture2,True),4)
        killed.kill();out,err=killed.communicate(timeout=10);self.assertNotEqual(killed.returncode,0)
        self.assertFalse((control2/'proof.json').exists());self.assertEqual(self.snapshot(fixture2.root),before2);self.assertEqual(self.moves(fixture2,False),4)
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        self.evidence={'kind':'047_actual_child_output_and_kill','closed_output_exit':1,'closed_output_host_store_closed':True,
                       'forced_kill_exit':killed.returncode,'forced_kill_graceful_close_proven':False,
                       'OS_released_native_and_port':True,'inputs_SQL_unchanged':True}


if __name__ == '__main__':
    unittest.main()
