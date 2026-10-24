"""057 synthetic demo boundaries; lifecycle doubles are separate from native HTTP."""
import importlib
import importlib.util
import io
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import socket
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import urlsplit

from labflow.store import Store

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'intake_reference_demo_'


class DemoBoundaries(unittest.TestCase):
    def api(self):
        return importlib.import_module('labflow.intake_reference_demo')

    def folder(self):
        local = ROOT / '.local'; local.mkdir(exist_ok=True)
        value = tempfile.TemporaryDirectory(prefix='demo057-unit-', dir=local)
        self.addCleanup(value.cleanup)
        return Path(value.name)

    def invoke(self, args, **patches):
        api = self.api(); out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            status = api.main(args)
        return status, out.getvalue(), err.getvalue()

    def lifecycle(self, *, serve=None, close=None, stdout=None, prepare=None, opened=None):
        api = self.api(); folder = self.folder(); output = folder / 'fresh'
        events = []
        state = output / 'state'; store = object.__new__(Store); store.root = state
        store.close = mock.Mock(side_effect=lambda: events.append('store.close'))
        server = SimpleNamespace(server_port=54321,
            serve_forever=mock.Mock(side_effect=serve or (lambda:events.append('serve'))),
            server_close=mock.Mock(side_effect=close or (lambda:events.append('host.close'))))
        prepared = (state, 'DEMO-ID', object(), ({'intake_id':'DEMO-ID','case_context':{},'validated_response':{},'producer_name':'fixture'},))
        out = io.StringIO() if stdout is None else stdout; err = io.StringIO()
        with mock.patch.object(api, '_dependencies'), \
                mock.patch.object(api, '_prepare_demo', return_value=prepared, side_effect=prepare) as preparation, \
                mock.patch.object(Store, 'open_existing', return_value=store, side_effect=opened) as opener, \
                mock.patch.object(api._ui, 'create_server', return_value=server) as factory, \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            result = api.main(['--output', str(output)])
        return result, out, err, events, preparation, opener, factory, server, store, output

    def test_module_and_main_exist(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.intake_reference_demo'))
        self.assertTrue(callable(self.api().main))

    def test_help_has_no_preparation_store_host_or_stream_reconfiguration(self):
        api = self.api()
        class Stream(io.StringIO):
            def reconfigure(self, **kwargs): raise AssertionError('caller stream changed')
        out, err = Stream(), Stream()
        with mock.patch.object(api, '_prepare_demo') as prepare, mock.patch.object(Store, 'open_existing') as opened, \
                mock.patch.object(api._ui, 'create_server') as factory, mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            self.assertEqual(api.main(['--help']), 0)
        prepare.assert_not_called(); opened.assert_not_called(); factory.assert_not_called()
        self.assertIn('--output', out.getvalue()); self.assertEqual(err.getvalue(), '')
        self.assertFalse(out.closed); self.assertFalse(err.closed)

    def test_unknown_duplicate_host_port_and_bad_types_have_no_side_effects(self):
        api = self.api()
        for args in [['--port','0'],['--host','127.0.0.1'],['--workspace','x'],['--output','relative'],
                     ['--output','x','--output','y'],['--help','--output','x'],None,{},[1],['--output']]:
            if args is None: continue
            with self.subTest(args=args), mock.patch.object(api, '_prepare_demo') as p, mock.patch.object(Store, 'open_existing') as s:
                code, out, err = self.invoke(args)
                self.assertEqual(code,2); self.assertEqual(out,'')
                self.assertEqual(json.loads(err),{'error':{'code':PREFIX+'invalid_argument'}})
                p.assert_not_called();s.assert_not_called()

    def test_existing_leaf_even_empty_file_and_missing_parent_are_rejected(self):
        folder=self.folder(); empty=folder/'empty';empty.mkdir(); file=folder/'file';file.write_bytes(b'keep')
        for path in [empty,file,folder/'absent'/'child']:
            with self.subTest(path=path):
                code,out,err=self.invoke(['--output',str(path)])
                self.assertEqual(code,2);self.assertFalse(out);self.assertEqual(json.loads(err)['error']['code'],PREFIX+'invalid_argument')
        self.assertEqual(file.read_bytes(),b'keep');self.assertEqual(list(empty.iterdir()),[])

    def test_missing_dependency_does_not_reserve_output(self):
        api=self.api();output=self.folder()/'fresh'
        with mock.patch.object(api,'_dependencies',side_effect=ImportError('not for output')):
            code,out,err=self.invoke(['--output',str(output)])
        self.assertEqual(code,1);self.assertFalse(output.exists());self.assertFalse(out)
        self.assertEqual(json.loads(err)['error']['code'],PREFIX+'unavailable')

    def test_ready_exact8_scopes_and_host_before_store_close(self):
        code,out,err,events,p,opener,factory,server,store,output=self.lifecycle()
        self.assertEqual(code,0);self.assertEqual(err.getvalue(),'')
        value=json.loads(out.getvalue());self.assertEqual(set(value),{'schema_version','kind','url','workspace','synthetic','ai_model_called','hardware_verified','operational_authority_granted'})
        self.assertEqual(value['kind'],'intake_reference_demo_ready');self.assertEqual(value['url'],'http://127.0.0.1:54321/#DEMO-ID')
        self.assertTrue(value['synthetic']);self.assertFalse(value['ai_model_called']);self.assertFalse(value['hardware_verified']);self.assertFalse(value['operational_authority_granted'])
        self.assertEqual(events,['serve','host.close','store.close']);self.assertEqual(opener.call_count,1)
        self.assertEqual(factory.call_args.kwargs['host'],'127.0.0.1');self.assertEqual(factory.call_args.kwargs['port'],0)
        for scope in ['intake_reference_read_scope','intake_reference_append_scope']:self.assertEqual(factory.call_args.kwargs[scope],('DEMO-ID',))
        self.assertIs(factory.call_args.kwargs['intake_reference_store'],store)
        self.assertEqual(len(factory.call_args.kwargs['intake_reference_review_inputs']),1)
        self.assertTrue((output/'closed.json').is_file())

    def test_pre_ready_interrupt130_and_after_ready_interrupt0(self):
        code,out,err,events,*_=self.lifecycle(prepare=KeyboardInterrupt())
        self.assertEqual(code,130);self.assertEqual(out.getvalue(),'');self.assertEqual(err.getvalue(),'')
        code,out,err,events,*_=self.lifecycle(serve=KeyboardInterrupt())
        self.assertEqual(code,0);self.assertTrue(out.getvalue());self.assertEqual(events,['host.close','store.close'])

    def test_output_failure_serves0_but_closes_owned_resources(self):
        class Broken(io.StringIO):
            def write(self, value):raise OSError('private exception')
        code,out,err,events,p,o,f,server,*_=self.lifecycle(stdout=Broken())
        self.assertEqual(code,1);server.serve_forever.assert_not_called()
        self.assertEqual(events,['host.close','store.close']);self.assertEqual(json.loads(err.getvalue())['error']['code'],PREFIX+'output_failed')

    def test_cleanup_retry_retains_first_failure_even_if_second_closes(self):
        api=self.api();calls=[]
        def close():
            calls.append(1)
            if len(calls)==1:raise RuntimeError('private')
        code,out,err,events,*_=self.lifecycle(close=close)
        self.assertEqual(code,1);self.assertEqual(len(calls),2);self.assertEqual(events,['serve','store.close'])
        self.assertEqual(json.loads(err.getvalue())['error']['code'],PREFIX+'shutdown_failed')

    def test_unconfirmed_host_close_never_closes_store_or_claims_success(self):
        code,out,err,events,p,o,f,server,store,output=self.lifecycle(close=RuntimeError('private'))
        self.assertEqual(code,1);self.assertEqual(server.server_close.call_count,2);store.close.assert_not_called()
        self.assertFalse((output/'closed.json').exists());self.assertTrue(list(output.glob('failure-*.json')))

    def test_repeated_interrupt_during_close_does_not_consume_error_retry(self):
        calls=[]
        def close():
            calls.append(1)
            if len(calls)<3:raise KeyboardInterrupt()
        code,out,err,events,*_=self.lifecycle(close=close)
        self.assertEqual(code,0);self.assertEqual(len(calls),3);self.assertEqual(events,['serve','store.close'])

    def test_first_preparation_error_is_preserved_and_no_server_is_bound(self):
        code,out,err,events,p,o,f,server,store,output=self.lifecycle(prepare=RuntimeError('private raw value'))
        self.assertEqual(code,1);o.assert_not_called();f.assert_not_called();self.assertFalse(out.getvalue())
        self.assertEqual(json.loads(err.getvalue()),{'error':{'code':PREFIX+'unavailable'}})
        self.assertNotIn('private',err.getvalue());self.assertTrue(list(output.glob('failure-*.json')))

    def test_P0_first_error_survives_later_cleanup_failure(self):
        api=self.api();output=self.folder()/'fresh';output.mkdir()
        original=RuntimeError('first');fake=SimpleNamespace(close=mock.Mock(side_effect=[OSError('later'),None]))
        with mock.patch.object(api,'Store',return_value=fake),mock.patch.object(api,'register_source'), \
                mock.patch.object(api,'scan_source',return_value={'accepted':[{'intake_id':'DEMO-ID'}]}), \
                mock.patch.object(api,'run_worker',side_effect=original):
            with self.assertRaises(RuntimeError) as raised:api._prepare_demo(output)
        self.assertIs(raised.exception,original);self.assertEqual(fake.close.call_count,2)

    def test_nonregular_lexical_and_parent_junction_rejected_before_dependency(self):
        api=self.api();folder=self.folder();target=folder/'target';target.mkdir();link=folder/'linked'
        if os.name=='nt':
            result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True)
            self.assertEqual(result.returncode,0)
        else:link.symlink_to(target,target_is_directory=True)
        rows=[str(link/'fresh'),'//server/share/fresh',str(folder/'parent'/'..'/'fresh'),str(folder/'fresh')+'\x00']
        if os.name=='nt':rows += [str(folder/'NUL'),str(folder/'fresh:alternate'),str(folder/'trailing.')]
        with mock.patch.object(api,'_dependencies') as dependencies:
            for row in rows:
                with self.subTest(case=rows.index(row)):
                    code,out,err=self.invoke(['--output',row]);self.assertEqual(code,2);self.assertEqual(out,'')
                    self.assertEqual(json.loads(err)['error']['code'],PREFIX+'invalid_argument')
        dependencies.assert_not_called();self.assertEqual(list(target.iterdir()),[])

    def test_default_UNC_is_rejected_before_any_filesystem_probe(self):
        api=self.api()
        with mock.patch.object(api.Path,'cwd',return_value=Path('//server/share')), \
                mock.patch.object(api.Path,'lstat',side_effect=AssertionError('must not probe UNC')) as probe, \
                mock.patch.object(api,'_dependencies') as dependencies:
            code,out,err=self.invoke([])
        self.assertEqual(code,2);self.assertEqual(out,'');probe.assert_not_called();dependencies.assert_not_called()

    def test_process_help_broken_stdout_and_stderr_fixed_exits(self):
        normal=subprocess.run([sys.executable,'-X','utf8','-B','-m','labflow.intake_reference_demo','--help'],cwd=ROOT,capture_output=True,timeout=10)
        self.assertEqual(normal.returncode,0);self.assertEqual(normal.stderr,b'');self.assertNotIn(b'\r',normal.stdout)
        for descriptor,args,expected in [(1,['--help'],1),(2,['bad'],2)]:
            code='import os,runpy,sys;os.close('+str(descriptor)+');sys.argv='+repr(['demo',*args])+";runpy.run_module('labflow.intake_reference_demo',run_name='__main__')"
            child=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=ROOT,capture_output=True,timeout=10)
            self.assertEqual(child.returncode,expected);self.assertNotIn(b'Traceback',child.stderr);self.assertNotIn(b'Exception ignored',child.stderr)

    def test_closed_process_stdout_is_detected_before_output_or_worker_creation(self):
        output=self.folder()/'fresh'
        code='import os,runpy,sys;os.close(1);sys.argv='+repr(['demo','--output',str(output)])+";runpy.run_module('labflow.intake_reference_demo',run_name='__main__')"
        child=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=ROOT,capture_output=True,timeout=15)
        self.assertEqual(child.returncode,1);self.assertFalse(output.exists());self.assertEqual(child.stdout,b'')
        self.assertEqual(json.loads(child.stderr)['error']['code'],PREFIX+'output_failed')

    def test_forbidden_assigned_ports_never_ready_or_serve(self):
        api=self.api()
        for port in (8765,8766):
            folder=self.folder();output=folder/'fresh'
            store=object.__new__(Store);store.root=output/'state';store.close=mock.Mock(return_value=None)
            server=SimpleNamespace(server_port=port,serve_forever=mock.Mock(),server_close=mock.Mock(return_value=None))
            with mock.patch.object(api,'_dependencies'),mock.patch.object(api,'_prepare_demo',return_value=(store.root,'DEMO-ID',object(),())), \
                    mock.patch.object(Store,'open_existing',return_value=store),mock.patch.object(api._ui,'create_server',return_value=server):
                code,out,err=self.invoke(['--output',str(output)])
            self.assertEqual(code,1);self.assertEqual(out,'');server.serve_forever.assert_not_called()
            server.server_close.assert_called_once();store.close.assert_called_once()


_CHILD = r'''
import json,os,runpy,sqlite3,sys,threading,time
from pathlib import Path

def run():
 root,control,output=map(Path,sys.argv[1:4]);mode=sys.argv[4]
 sys.path.insert(0,str(root))
 from labflow.store import Store
 stats={'phase':'P0','P0':{'Store_create':0,'Store_close':0,'parser':0,'prepare':0,'append':0,'current':0},
  'P1':{'open_existing':0,'factory':0,'serve':0,'host_close':0,'Store_close':0,'parser':0,
        'prepare':0,'append':0,'current':0,'history':0,'actions_close':0,'source_opens':0,'source_bytes':0},
  'SQL':{},'SQLite_open':0,'SQLite_C_close':0,'KI_sent':0,'order':[]}
 objects={};owned=[];armed=set();local=threading.local();raw_open=Path.open
 first_requests={};append_ordinal=[0]
 def save(name='proof.json'):
  with raw_open(control/name,'w',encoding='utf-8',newline='\n') as stream:json.dump(stats,stream,sort_keys=True)
 def audit(event,args):
  if event=='sqlite3.connect/handle':owned.append(args[0]);stats['SQLite_open']+=1
 sys.addaudithook(audit)
 def arm(con):
  if id(con) in armed:return
  armed.add(id(con))
  def trace(sql):
   key=stats['phase']+'/'+getattr(local,'action','metadata')
   row=stats['SQL'].setdefault(key,{'DDL':0,'reference_DDL':0,'datawrite':0,'statements':0})
   row['statements']+=1
   verb=sql.lstrip().split(None,1)[0].upper() if sql.strip() else ''
   row['DDL']+=verb in ('CREATE','DROP','ALTER','REINDEX')
   row['reference_DDL']+=verb in ('CREATE','DROP','ALTER','REINDEX') and 'intake_reference_' in sql
   row['datawrite']+=verb in ('INSERT','UPDATE','DELETE','REPLACE')
  con.set_trace_callback(trace)
 class Stream:
  def __init__(self,value):self.value=value
  def __getattr__(self,key):return getattr(self.value,key)
  def __enter__(self):self.value.__enter__();return self
  def __exit__(self,*args):return self.value.__exit__(*args)
  def read(self,*args):
   value=self.value.read(*args);stats['P1']['source_bytes']+=len(value);return value
 def opened(path,*args,**kwargs):
  value=raw_open(path,*args,**kwargs)
  if stats['phase']=='P1' and path.parent==output/'state'/'blobs':
   stats['P1']['source_opens']+=1;return Stream(value)
  return value
 def profile(frame,event,arg):
  nonlocal output
  package,name=frame.f_globals.get('__name__'),frame.f_code.co_name
  phase=stats['phase'];row=stats[phase]
  if event=='c_call' and getattr(arg,'__name__',None) in ('execute','executemany','executescript','cursor'):
   owner=getattr(arg,'__self__',None);con=owner if type(owner) is sqlite3.Connection else getattr(owner,'connection',None)
   if any(con is c for c in owned):arm(con)
  if event=='c_return' and getattr(arg,'__name__',None)=='close' and any(getattr(arg,'__self__',None) is c for c in owned):stats['SQLite_C_close']+=1
  if package=='labflow.store' and name=='__init__' and event=='call' and type(frame.f_locals.get('self')) is Store:stats['P0']['Store_create']+=1
  if package=='labflow.store' and name=='open_existing':
   if event=='call':stats['P1']['open_existing']+=1
   elif event=='return' and type(arg) is Store:objects['store']=arg
  if name=='_prepare_demo' and frame.f_code.co_filename.endswith('intake_reference_demo.py') and event=='call':
   output=frame.f_locals['output']
  if name=='_prepare_demo' and frame.f_code.co_filename.endswith('intake_reference_demo.py') and event=='return' and arg is not None:
   stats['phase']='P1'
   stats['P0']['genuine_catalog']=type(arg[2]).__name__=='FccReportCaseCatalog'
   stats['P0']['inputs_exact4']=len(arg[3])==1 and set(arg[3][0])=={'intake_id','case_context','validated_response','producer_name'}
   stats['P0']['test_imports']=sum(name=='tests' or name.startswith(('tests.','test_')) for name in sys.modules)
   save('startup.json')
  if package=='labflow.ui_server' and name=='create_server':
   if event=='call':
    row['factory']+=1
    values=frame.f_locals
    stats['scopes_ID1']=values['intake_reference_read_scope']==values['intake_reference_append_scope'] and len(values['intake_reference_read_scope'])==1
    stats['same_Store']=values['intake_reference_store'] is objects.get('store')
   elif event=='return' and arg is not None:
    objects['server']=arg;stats['port']=arg.server_port
    if mode=='closed_ready_stdout':os.close(1)
    service=arg.service_actions;wait=arg._reference_runtime.changed.wait;repeats=[0]
    def tick():
     if (control/'expire-core').exists():
      with arg._reference_runtime.actions._lock:
       for entry in arg._reference_runtime.actions._entries.values():entry.deadline=0
      (control/'expire-core').rename(control/'expired-core')
     if (control/'expire-session').exists():
      with arg._reference_runtime.lock:
       for item in arg._reference_runtime.sessions.values():item['last_seen']=0
      (control/'expire-session').rename(control/'expired-session')
     if (control/'checkpoint').exists():save('checkpoint.json');(control/'checkpoint').unlink()
     for marker in control.glob('drain-*'):
      if arg._reference_runtime.active==0:marker.rename(marker.with_name('drained-'+marker.name[6:]))
     if (control/'interrupt').exists():stats['KI_sent']+=1;raise KeyboardInterrupt()
     return service()
    def waiting(timeout=None):
     if (control/'repeat').exists() and repeats[0]<2:
      repeats[0]+=1;stats['KI_sent']+=1;raise KeyboardInterrupt()
     return wait(timeout)
    arg.service_actions=tick;arg._reference_runtime.changed.wait=waiting
  if package=='labflow.ui_server' and name=='serve_forever' and event=='call':row['serve']+=1
  if package=='labflow.ui_server' and name=='server_close' and event=='call':
   row['host_close']+=1;stats['order'].append('host.close');stats['active_at_close']=frame.f_locals['self']._reference_runtime.active
   (control/'closing').write_text('1',encoding='ascii')
  if package=='labflow.document_extract' and name=='extract_document' and event=='call':row['parser']+=1
  if package=='labflow.intake_reference_review' and name in ('prepare_reference_review','append_reference_review','read_reference_review'):
   action={'prepare_reference_review':'prepare','append_reference_review':'append'}.get(name)
   if action is None:action=frame.f_locals['request']['action']
   if event=='call':
    row[action]+=1;local.action=action
    if action=='append':
     append_ordinal[0]+=1;local.action='append'+str(append_ordinal[0])
     if (control/'block-append').exists():
      (control/'entered').write_text('1',encoding='ascii')
      while not (control/'release').exists():time.sleep(.01)
    if action=='current' and (control/'block-current').exists():
     (control/'entered').write_text('1',encoding='ascii')
     while not (control/'release').exists():time.sleep(.01)
   elif event=='return':
    if action=='append' and (control/'hold-response').exists():
     marker=control/'hold-response';serial=marker.read_text(encoding='ascii');marker.rename(control/('held-'+serial))
     stats['committed_response_held']=bool(arg is not None and arg.get('stored') is True)
     (control/('committed-'+serial)).write_text('1',encoding='ascii')
     while not (control/('release-'+serial)).exists():time.sleep(.01)
    if action in ('append','current'):stats['order'].append(action+'.finally')
    local.action='metadata'
  if package=='labflow.intake_reference_review_host' and name=='append' and event=='call':
   req=frame.f_locals['request'];key=req['handle_id'];original=first_requests.get(key)
   if original is None:first_requests[key]=dict(req)
   else:stats['original7_equal']=req==original
  if package=='labflow.intake_reference_review_host' and name=='close':
   if event=='call':row['actions_close']+=1;stats['order'].append('actions.close')
   elif event=='return':stats['actions_close_None']=arg is None
  if package=='labflow.store' and name=='close' and type(frame.f_locals.get('self')) is Store:
   if event=='call':
    row['Store_close']+=1;stats['order'].append(phase+'.Store.close')
    if phase=='P1':
     server=objects['server'];rt=server._reference_runtime
     stats['at_Store_close']={'active':rt.active,'workers':len(rt.worker_refs),'clients':len(rt.clients),
      'loop':rt.loop_thread is not None,'socket':server.socket.fileno(),'sessions':len(rt.sessions),'actions_closed':rt.actions_closed}
   elif event=='return' and phase=='P1':
    stats['native_handles_after']=len(objects['store']._existing_binding.handles);save()
 Path.open=opened;sys.setprofile(profile);threading.setprofile(profile)
 if mode=='closed_stdout':os.close(1)
 if mode=='closed_stderr':os.close(2)
 sys.argv=['labflow.intake_reference_demo']+([] if mode=='default' else ['--output',str(output)])
 runpy.run_module('labflow.intake_reference_demo',run_name='__main__')

if __name__=='__main__':run()
'''


class DemoNative(unittest.TestCase):
    def child(self, mode='normal'):
        folder = ROOT / '.local/INTAKE-DEMO-057/test-evidence' / uuid_hex()
        folder.mkdir(parents=True, exist_ok=False)
        control = folder / 'control'; control.mkdir()
        script = folder / 'child.py'; script.write_text(_CHILD, encoding='utf-8', newline='\n')
        output = folder / 'output'
        process = subprocess.Popen([sys.executable, '-X', 'utf8', '-B', str(script), str(ROOT), str(control), str(output), mode],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def stop():
            if process.poll() is None:
                process.kill(); out, err = process.communicate(timeout=10)
                (control/'unexpected-kill-stdout.bin').write_bytes(out)
                (control/'unexpected-kill-stderr.bin').write_bytes(err)
        self.addCleanup(stop)
        return process, output, control

    def ready(self, process):
        lines=[]; done=threading.Event()
        def read():
            lines.append(process.stdout.readline()); done.set()
        threading.Thread(target=read, daemon=True).start()
        self.assertTrue(done.wait(30), 'ready timeout')
        if not lines[0]:
            _,err=process.communicate(timeout=5)
            self.fail('CLI exited before ready: '+err.decode('utf-8'))
        self.assertNotIn(b'\r',lines[0]); value=json.loads(lines[0])
        self.assertEqual(set(value),{'schema_version','kind','url','workspace','synthetic','ai_model_called','hardware_verified','operational_authority_granted'})
        address=urlsplit(value['url']);self.assertEqual(address.hostname,'127.0.0.1');self.assertNotIn(address.port,(8765,8766))
        return value,address.port,address.fragment

    def http(self,port,path,method='GET',*,cookie=None,csrf=None,body=None):
        headers={}
        if cookie:headers['Cookie']=cookie
        if method=='POST':headers.update({'Origin':'http://127.0.0.1:'+str(port),'Sec-Fetch-Site':'same-origin',
            'Content-Type':'application/json; charset=utf-8','X-Intake-Reference-CSRF':csrf or '0'*64})
        con=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
        try:
            con.request(method,path,body=json.dumps(body).encode() if type(body) is dict else body,headers=headers)
            r=con.getresponse();return r.status,dict(r.getheaders()),r.read()
        finally:con.close()

    def wait_file(self,path):
        deadline=time.monotonic()+15
        while not path.exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(path.exists(),'observer checkpoint timeout')

    def snapshot(self,output):
        con=sqlite3.connect((output/'state/lab.sqlite3').as_uri()+'?mode=ro',uri=True)
        try:
            names=[row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows={name:con.execute('SELECT COUNT(*) FROM "'+name+'"').fetchone()[0] for name in names}
            dump='\n'.join(con.iterdump())
        finally:con.close()
        files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for p in output.rglob('*') if p.is_file() and p.name!='lab.sqlite3' and not p.name.startswith('lab.sqlite3-')}
        return rows,dump,files

    def moves(self,output,blocked):
        for path in [output/'state/lab.sqlite3',output/'state/blobs',output/'state',output]:
            target=path.with_name(path.name+'.moved')
            self.assertTrue(path.resolve().is_relative_to(ROOT/'.local'));self.assertTrue(target.resolve().is_relative_to(ROOT/'.local'))
            self.assertFalse(target.exists())
            try:path.rename(target)
            except OSError:
                self.assertTrue(blocked)
            else:
                target.rename(path);self.assertFalse(blocked,'native ownership released early')

    def finish(self,process,output,control,port,expected=0):
        out,err=process.communicate(timeout=30)
        (control/'exit.json').write_text(json.dumps({'exit':process.returncode,'remaining_stdout_bytes':len(out),'stderr_bytes':len(err)}),encoding='utf-8')
        self.assertEqual(process.returncode,expected);self.assertEqual(out,b'')
        if expected==0:self.assertEqual(err,b'')
        else:self.assertEqual(json.loads(err)['error']['code'],PREFIX+'output_failed')
        proof=json.loads((control/'proof.json').read_text(encoding='utf-8'))
        self.assertEqual(proof['P0']['Store_create'],1);self.assertEqual(proof['P0']['Store_close'],1)
        self.assertEqual(proof['P0']['test_imports'],0);self.assertTrue(proof['P0']['genuine_catalog']);self.assertTrue(proof['P0']['inputs_exact4'])
        self.assertEqual(proof['SQL']['P0/metadata']['reference_DDL'],0)
        self.assertEqual(proof['P1']['open_existing'],1);self.assertEqual(proof['P1']['factory'],1)
        self.assertTrue(proof['same_Store']);self.assertTrue(proof['scopes_ID1'])
        self.assertEqual(proof['at_Store_close'],{'active':0,'workers':0,'clients':0,'loop':False,'socket':-1,'sessions':0,'actions_closed':True})
        self.assertEqual(proof['P1']['actions_close'],1);self.assertTrue(proof['actions_close_None'])
        self.assertEqual(proof['native_handles_after'],0);self.assertEqual(proof['SQLite_open'],proof['SQLite_C_close'])
        self.moves(output,False)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);probe.bind(('127.0.0.1',port))
        self.assertEqual(list((output/'state').glob('lab.sqlite3-*')),[])
        self.assertEqual((output/'closed.json').exists(),expected==0)
        return proof

    def prepare(self,port,ident):
        route='/api/intake-references/'+ident
        status,headers,body=self.http(port,route+'/history');self.assertEqual(status,200)
        self.assertEqual(headers['X-Intake-Reference-Prepare-Allowed'],'true')
        self.assertEqual(headers['X-Intake-Reference-Append-Allowed'],'true')
        cookie=headers['Set-Cookie'].split(';')[0];csrf=headers['X-Intake-Reference-CSRF']
        request={'schema_version':1,'review_input_id':headers['X-Intake-Reference-Review-Input'],'replace_handle_id':None}
        status,_,raw=self.http(port,route+'/prepare','POST',cookie=cookie,csrf=csrf,body=request);self.assertEqual(status,200)
        envelope=json.loads(raw);preview=envelope['preview']
        self.assertEqual(preview['selection']['status'],'no_candidate');self.assertEqual(preview['selection']['accepted_reference_count'],0)
        self.assertEqual(preview['selection']['requested_case_ids'],[]);self.assertTrue(preview['preparation_ready'])
        for name in ('operational_authority_granted','model_execution_verified','evaluation_executed'):self.assertFalse(preview['verification'][name])
        append={'schema_version':1,'intake_id':ident,'handle_id':envelope['handle_id'],'request_id':envelope['append_request_id'],
            'preparation_id':preview['preparation_id'],'expected_snapshot_id':preview['observation']['snapshot_id'],
            'expected_head_record_id':preview['observation']['head_record_id']}
        return route,cookie,csrf,request,append

    def test_genuine_cli_P0_V2_empty_catalog_native_append_replay_and_assets(self):
        process,output,control=self.child();ready,port,ident=self.ready(process)
        rows0,dump0,files0=self.snapshot(output)
        self.assertFalse(any(name.startswith('intake_reference_') for name in rows0))
        for name,count in rows0.items():
            if name in ('cases','plans','runs','evaluations','intake_fixture_jobs'):self.assertEqual(count,0)
        con=sqlite3.connect((output/'state/lab.sqlite3').as_uri()+'?mode=ro',uri=True)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM intake_jobs WHERE state='completed'").fetchone()[0],1)
            analysis=json.loads(con.execute('SELECT analysis_json FROM intakes').fetchone()[0])
            self.assertEqual(con.execute('SELECT delegated FROM intakes').fetchone()[0],1)
        finally:con.close()
        submitted=analysis['submitted'];self.assertEqual(submitted['schema_version'],2);self.assertEqual(submitted['producer']['kind'],'fixture')
        evidence=[item for fact in submitted['facts'] for item in fact['evidence']]
        self.assertTrue(any(item.get('kind')=='pdf_page' and item['page_number']==1 and item['line_start']>=1 for item in evidence))
        bundle=output/'inbox'/'057 합성 수동참고 데모(모델호출0)'
        self.assertEqual(len(list(bundle.glob('*.pdf'))),1);self.assertEqual(len(list(bundle.glob('*.txt'))),1)
        from pypdf import PdfReader
        extracted=PdfReader(bundle/'request.pdf').pages[0].extract_text()
        self.assertIn('SYNTHETIC / NO REAL MODEL OR HARDWARE',extracted)
        pdf_sha=hashlib.sha256((bundle/'request.pdf').read_bytes()).hexdigest()
        pdf_evidence=[item for item in evidence if item.get('kind')=='pdf_page']
        self.assertTrue(all(item['sha256']==pdf_sha and item['quote']==extracted.splitlines()[item['line_start']-1] for item in pdf_evidence),
            'PDF original bytes and page/line quotes must agree')
        self.assertEqual(ready['workspace'],str(output/'state'))
        static={'/':'frontend/index.html','/app.js':'frontend/app.js','/styles.css':'frontend/styles.css',
                '/intake-references/model.mjs':'frontend/intake_references/model.mjs',
                '/intake-references/view.mjs':'frontend/intake_references/view.mjs',
                '/intake-references/transport.mjs':'frontend/intake_references/transport.mjs',
                '/intake-reference-actions/actions.mjs':'frontend/intake_reference_actions/actions.mjs'}
        for route,name in static.items():
            status,headers,body=self.http(port,route);self.assertEqual(status,200)
            self.assertEqual(body,(ROOT/name).read_bytes());self.assertEqual(headers['Cache-Control'],'no-store')
            self.assertIn("default-src 'none'",headers['Content-Security-Policy'])
            git=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
            self.assertEqual(body.replace(b'\r\n',b'\n'),git)
            status,head,empty=self.http(port,route,'HEAD');self.assertEqual(status,200);self.assertEqual(empty,b'')
            self.assertEqual(head['Content-Type'],headers['Content-Type'])
        self.assertEqual(self.http(port,'/intake_reference_actions/actions.mjs')[0],404)
        route,cookie,csrf,prepare,append=self.prepare(port,ident)
        self.assertEqual(self.http(port,'/api/intake-references/FOREIGN/prepare','POST',cookie=cookie,csrf=csrf,body=prepare)[0],403)
        status,_,raw=self.http(port,route+'/append','POST',cookie=cookie,csrf=csrf,body=append);self.assertEqual(status,200)
        registered=json.loads(raw);self.assertEqual(registered['binding_status'],'current_at_append');self.assertFalse(registered['replayed'])
        rows1,dump1,files1=self.snapshot(output)
        for name in ('intake_reference_records','intake_reference_events','intake_reference_heads'):self.assertEqual(rows1[name],1)
        status,_,raw=self.http(port,route+'/append','POST',cookie=cookie,csrf=csrf,body=append);self.assertEqual(status,200);self.assertTrue(json.loads(raw)['replayed'])
        rows2,dump2,files2=self.snapshot(output)
        self.assertTrue(dump1==dump2,'replay must preserve full SQL dump')
        self.assertTrue(files0==files1==files2,'retained originals and declared inputs must remain unchanged')
        for name in rows0:self.assertEqual(rows0[name],rows2[name])
        self.moves(output,True);(control/'interrupt').write_text('1',encoding='ascii')
        proof=self.finish(process,output,control,port)
        self.assertTrue(proof['original7_equal']);self.assertEqual(proof['P0']['prepare'],0);self.assertEqual(proof['P0']['append'],0)
        self.assertEqual(proof['P1']['current'],0);self.assertEqual(proof['P1']['prepare'],1);self.assertEqual(proof['P1']['append'],2)
        self.assertEqual(proof['SQL']['P1/append2']['DDL'],0);self.assertEqual(proof['SQL']['P1/append2']['datawrite'],0)

    def test_default_output_is_fresh_UUID_under_current_repository(self):
        process,placeholder,control=self.child('default');ready,port,_=self.ready(process)
        output=Path(ready['workspace']).parent
        self.assertEqual(output.parent,ROOT/'.local/intake-reference-demo')
        self.assertEqual(len(output.name),32);self.assertTrue(all(c in '0123456789abcdef' for c in output.name))
        self.assertFalse(placeholder.exists());self.moves(output,True)
        (control/'interrupt').write_text('1',encoding='ascii');proof=self.finish(process,output,control,port)
        self.assertEqual(proof['P1']['prepare'],0);self.assertEqual(proof['P1']['append'],0);self.assertEqual(proof['P1']['current'],0)

    def test_active_parent_abort_source_one_metadata_and_repeated_interrupt_drain(self):
        process,output,control=self.child();_,port,ident=self.ready(process)
        route,cookie,csrf,prepare,append=self.prepare(port,ident)
        (control/'block-append').write_text('1',encoding='ascii')
        body=json.dumps(append).encode();raw=socket.create_connection(('127.0.0.1',port),timeout=10)
        request=(f'POST {route}/append HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nOrigin: http://127.0.0.1:{port}\r\n'
                 f'Sec-Fetch-Site: same-origin\r\nContent-Type: application/json\r\nCookie: {cookie}\r\n'
                 f'X-Intake-Reference-CSRF: {csrf}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode()+body
        try:
            raw.sendall(request);self.wait_file(control/'entered')
            self.assertEqual(self.http(port,route+'/prepare','POST',cookie=cookie,csrf=csrf,body=prepare)[0],429)
            self.assertEqual(self.http(port,route+'/current','POST',cookie=cookie,csrf=csrf,body={'schema_version':1,'action':'current'})[0],429)
            self.assertEqual(self.http(port,route+'/history',cookie=cookie)[0],200)
            raw.shutdown(socket.SHUT_RDWR);raw.close()
            (control/'repeat').write_text('1',encoding='ascii');(control/'interrupt').write_text('1',encoding='ascii')
            self.wait_file(control/'closing');time.sleep(.15)
            self.assertIsNone(process.poll());self.assertFalse((control/'proof.json').exists());self.moves(output,True)
        finally:
            raw.close();(control/'release').write_text('1',encoding='ascii')
        proof=self.finish(process,output,control,port)
        self.assertEqual(proof['KI_sent'],3);self.assertEqual(proof['active_at_close'],1)
        self.assertEqual(proof['P1']['append'],1);self.assertEqual(proof['P1']['prepare'],1);self.assertEqual(proof['P1']['current'],0)
        order=proof['order'];self.assertLess(order.index('host.close'),order.index('append.finally'))
        self.assertLess(order.index('append.finally'),order.index('actions.close'));self.assertLess(order.index('actions.close'),order.index('P1.Store.close'))
        rows,_,_=self.snapshot(output)
        for name in ('intake_reference_records','intake_reference_events','intake_reference_heads'):self.assertEqual(rows[name],1)

    def test_real_ready_output_failure_preserves_inputs_and_None_empty_stay_unconfigured(self):
        process,output,control=self.child('closed_ready_stdout')
        out,err=process.communicate(timeout=30);self.assertEqual(out,b'');self.assertEqual(process.returncode,1)
        self.assertEqual(json.loads(err)['error']['code'],PREFIX+'output_failed')
        proof=json.loads((control/'proof.json').read_text(encoding='utf-8'))
        self.assertEqual(proof['P1']['serve'],0);self.assertEqual(proof['P1']['prepare'],0);self.assertEqual(proof['P1']['append'],0)
        self.assertEqual(proof['native_handles_after'],0);self.assertEqual(proof['SQLite_open'],proof['SQLite_C_close'])
        self.assertFalse((output/'closed.json').exists());self.assertEqual(len(list(output.glob('failure-*.json'))),1)
        self.moves(output,False)
        from labflow.ui_server import create_server
        from labflow.fcc_report_cases import FccReportCaseCatalog
        value=json.loads((output/'review-input.json').read_text(encoding='utf-8'))
        catalog=FccReportCaseCatalog(value['packet'],{});ident=value['review_inputs'][0]['intake_id']
        store=Store.open_existing(str(output/'state'))
        try:
            for configured in (False,True):
                kwargs={'intake_reference_store':store,'fcc_case_catalog':catalog,
                    'intake_reference_read_scope':(ident,),'intake_reference_append_scope':(ident,)} if configured else {}
                server=create_server(output/'state',host='127.0.0.1',port=0,**kwargs)
                thread=threading.Thread(target=server.serve_forever);thread.start()
                try:
                    status,headers,raw=self.http(server.server_port,'/api/intake-references/'+ident+'/history')
                    if configured:
                        self.assertEqual(status,200);self.assertEqual(headers['X-Intake-Reference-Prepare-Allowed'],'false')
                        self.assertEqual(headers['X-Intake-Reference-Append-Allowed'],'false')
                    else:self.assertEqual(status,503)
                finally:server.shutdown();thread.join(5);server.server_close()
        finally:store.close()
        rows,_,_=self.snapshot(output);self.assertFalse(any(name.startswith('intake_reference_') for name in rows))

    def test_forced_kill_is_only_OS_recovery_and_preserves_new_originals(self):
        process,output,control=self.child();_,port,_=self.ready(process)
        before=self.snapshot(output);self.moves(output,True)
        process.kill();out,err=process.communicate(timeout=10)
        self.assertNotEqual(process.returncode,0);self.assertEqual(out,b'');self.assertEqual(err,b'')
        self.assertFalse((control/'proof.json').exists());self.assertFalse((output/'closed.json').exists())
        self.assertTrue(self.snapshot(output)==before,'kill must preserve original inputs and SQL');self.moves(output,False)
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        (control/'kill-receipt.json').write_text(json.dumps({'exit':process.returncode,'OS_resources_released':True,
            'graceful_API_drain_proven':False,'originals_and_SQL_unchanged':True}),encoding='utf-8')

    def browser(self,mode,width=1440):
        process,output,control=self.child();ready,port,_=self.ready(process)
        script=control/'browser.cjs';script.write_text(_BROWSER,encoding='utf-8',newline='\n')
        env=os.environ.copy()
        env.setdefault('NODE_PATH','C:/Users/HCT-2838/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')
        result=subprocess.run(['node',str(script),ready['url'],str(control),mode,str(width)],cwd=ROOT,env=env,capture_output=True,timeout=70)
        # The checker only emits a sanitized stage/result; never original requests.
        (control/'browser-stdout.log').write_bytes(result.stdout);(control/'browser-stderr.log').write_bytes(result.stderr)
        self.assertEqual(result.returncode,0,'native browser checker failed; see sanitized browser receipt')
        value=json.loads((control/'browser.json').read_text(encoding='utf-8'))
        self.assertEqual(value['status'],'pass');self.assertEqual(value['counts']['current'],0)
        (control/'interrupt').write_text('1',encoding='ascii');proof=self.finish(process,output,control,port)
        rows,_,_=self.snapshot(output)
        for name in ('intake_reference_records','intake_reference_events','intake_reference_heads'):self.assertEqual(rows[name],1)
        self.assertTrue(proof['original7_equal']);return value,proof

    def test_actual_main_keyboard_1440_and_390_normal_flow(self):
        for width in (1440,390):
            with self.subTest(width=width):
                value,proof=self.browser('normal',width)
                self.assertEqual(value['counts'],{'history':5,'prepare':1,'append':2,'current':0})
                self.assertEqual(proof['SQL']['P1/append2']['datawrite'],0);self.assertEqual(proof['SQL']['P1/append2']['DDL'],0)

    def test_actual_main_commit_delivery_loss_original_replay_and_410(self):
        value,proof=self.browser('lost')
        self.assertTrue(value['committed_response_lost']);self.assertTrue(value['retired_410'])
        self.assertEqual(value['counts']['prepare'],1);self.assertEqual(value['counts']['append'],4)
        self.assertEqual(proof['P1']['prepare'],1);self.assertEqual(proof['P1']['append'],3)
        for number in (2,3):
            self.assertEqual(proof['SQL']['P1/append'+str(number)]['datawrite'],0)

    def test_actual_main_commit_delivery_loss_session_change_retires(self):
        value,proof=self.browser('session')
        self.assertTrue(value['session_retired']);self.assertEqual(value['counts']['prepare'],1)
        self.assertEqual(value['counts']['append'],3);self.assertEqual(proof['P1']['append'],3)


_BROWSER = r'''
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const [url,control,mode,width]=process.argv.slice(2),origin=new URL(url).origin;
const result={status:'fail',mode,width:Number(width),counts:{history:0,prepare:0,append:0,current:0},
 original7_equal:true,storage_empty:false,secret_exposed:false,external:0,downloads:0,console_errors:0};
let browser,stage='start';const secrets=new Set(),requestIDs=new Set(),originals=new Map(),responses=[];
const save=()=>fs.writeFileSync(path.join(control,'browser.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
const phase=(page,value)=>page.waitForFunction(v=>document.querySelector('.reference-actions-review')?.dataset.phase===v,value);
const history=page=>page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');
async function keyboard(page,selector){
 for(let i=0;i<100;i++){
  if(await page.evaluate(s=>document.activeElement?.matches(s),selector)){await page.keyboard.press('Enter');return;}
  await page.keyboard.press('Tab');
 }
 throw Error('keyboard_target_missing');
}
async function waitFile(name){const until=Date.now()+5000;while(!fs.existsSync(path.join(control,name))){assert.ok(Date.now()<until);await new Promise(r=>setTimeout(r,20));}}
(async()=>{
 try{
  browser=await require('playwright').chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:Number(width),height:1000}}),page=await context.newPage();
  page.on('pageerror',()=>result.console_errors++);page.on('download',()=>result.downloads++);
  page.on('request',request=>{
   if(!request.url().startsWith(origin+'/')){result.external++;return;}
   const kind=new URL(request.url()).pathname.split('/').at(-1);if(!Object.hasOwn(result.counts,kind))return;
   result.counts[kind]++;
   const csrf=request.headers()['x-intake-reference-csrf'];if(csrf)secrets.add(csrf);
   if(kind==='prepare')secrets.add(request.postDataJSON().review_input_id);
   if(kind==='append'){
    const body=request.postDataJSON(),raw=JSON.stringify(body);secrets.add(body.handle_id);requestIDs.add(body.request_id);
    assert.equal(Object.keys(body).length,7);
    if(originals.has(body.handle_id))result.original7_equal&&=originals.get(body.handle_id)===raw;else originals.set(body.handle_id,raw);
   }
  });
  page.on('response',response=>{
   const kind=new URL(response.url()).pathname.split('/').at(-1);if(!Object.hasOwn(result.counts,kind))return;
   // C1 itself parses and validates the body. Read its rendered observation;
   // a second CDP body read can race with the subsequent history refresh.
   if(kind==='append')responses.push({status:response.status()});
  });
  stage='initial';await page.goto(url);await history(page);await phase(page,'idle');
  assert.ok((await page.locator('#detail-title').innerText()).includes('057 합성 수동참고 데모(모델호출0)'));
  const text=await page.locator('body').innerText();assert.ok(text.includes('Synthetic manual/fixture 025 review'));
  assert.ok(text.includes('schema producer.kind=model'));assert.ok(text.includes('actual model calls=0'));
  assert.equal(await page.locator('.reference-actions-review').evaluate(node=>node.contains(document.activeElement)),false);
  assert.equal(result.counts.prepare,0);assert.equal(result.counts.append,0);assert.equal(result.counts.current,0);
  stage='prepare';await keyboard(page,'.ra-prepare');await phase(page,'ready');
  assert.ok((await page.locator('.ra-preview').innerText()).includes('no_candidate'));
  if(mode==='normal'){
   stage='append';await keyboard(page,'.ra-append');await phase(page,'recorded');await history(page);
   stage='replay';await keyboard(page,'.ra-replay');await phase(page,'recorded');await history(page);
   assert.equal(await page.locator('.ra-registration .ra-fields>div').filter({hasText:'원래 요청 재전송 결과'}).locator('dd').innerText(),'true');
  }else{
   let serial=0;
   const lose=async selector=>{
    const number=String(++serial);fs.writeFileSync(path.join(control,'hold-response'),number,{flag:'wx'});
    await keyboard(page,selector);await waitFile('committed-'+number);
    await page.locator('#refresh').click();await history(page);await phase(page,'uncertain');
    fs.writeFileSync(path.join(control,'release-'+number),'1',{flag:'wx'});
    fs.writeFileSync(path.join(control,'drain-'+number),'1',{flag:'wx'});await waitFile('drained-'+number);
   };
   stage='lost_commit';await lose('.ra-append');result.committed_response_lost=true;
   assert.equal(await page.locator('.ra-prepare').isDisabled(),true);
   await keyboard(page,'.ra-capabilities');await phase(page,'uncertain');
   stage='original_replay';await keyboard(page,'.ra-replay');await phase(page,'recorded');await history(page);
   assert.equal(await page.locator('.ra-registration .ra-fields>div').filter({hasText:'원래 요청 재전송 결과'}).locator('dd').innerText(),'true');
   if(mode==='lost'){
    stage='lost_replay';await lose('.ra-replay');
    await keyboard(page,'.ra-capabilities');await phase(page,'uncertain');
    fs.writeFileSync(path.join(control,'expire-core'),'1');await waitFile('expired-core');
    stage='expired_410';await keyboard(page,'.ra-replay');await phase(page,'retired');
    assert.equal(responses.at(-1).status,410);result.retired_410=true;
   }else{
    // Lose a genuine idempotent response, then expire the native session.
    stage='lost_before_session';await lose('.ra-replay');
    fs.writeFileSync(path.join(control,'expire-session'),'1');await waitFile('expired-session');
    stage='session';await keyboard(page,'.ra-capabilities');await phase(page,'uncertain');
    assert.equal(await page.locator('.ra-replay').isDisabled(),true);await context.clearCookies();
    await keyboard(page,'.ra-capabilities');await phase(page,'retired');result.session_retired=true;
   }
   assert.equal(await page.locator('.ra-unresolved').isVisible(),true);
  }
  stage='privacy';for(const cookie of await context.cookies()){
   secrets.add(cookie.value);assert.equal(cookie.httpOnly,true);assert.equal(cookie.sameSite,'Strict');
  }
  const privacy=await page.evaluate(()=>({html:document.documentElement.outerHTML,actions:document.querySelector('.reference-actions-review').outerHTML,storage:[localStorage.length,sessionStorage.length],
   downloads:document.querySelectorAll('a[download]').length,overflow:document.documentElement.scrollWidth>innerWidth}));
  result.secret_exposed=[...secrets].some(value=>value&&privacy.html.includes(value))||[...requestIDs].some(value=>value&&privacy.actions.includes(value));
  result.storage_empty=privacy.storage.every(value=>value===0);assert.equal(privacy.downloads,0);assert.equal(privacy.overflow,false);
  assert.equal(result.secret_exposed,false);assert.equal(result.storage_empty,true);assert.equal(result.original7_equal,true);
  assert.equal(result.external,0);assert.equal(result.downloads,0);assert.equal(result.console_errors,0);
  assert.equal(result.counts.current,0);
  if(mode==='normal'){
   await page.screenshot({path:path.join(control,'main-'+width+'.png'),fullPage:true});
   await page.locator('.reference-actions-review').screenshot({path:path.join(control,'actions-'+width+'.png')});
  }
  result.status='pass';await context.close();
 }catch{result.stage=stage;process.exitCode=1;}
 finally{if(browser)await browser.close();save();}
})().catch(()=>{process.exitCode=1;});
'''


def uuid_hex():
    import uuid
    return uuid.uuid4().hex


if __name__ == '__main__':
    unittest.main()
