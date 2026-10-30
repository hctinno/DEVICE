/* Actual protected HTTP -> typed dependency double -> record -> Chromium DOM. Cloud calls0. */
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const http=require('node:http'),crypto=require('node:crypto');
const ROOT=require('../managed_paths.cjs').stage(path.resolve(__dirname,'../..')),LOCAL=path.join(ROOT,'.local');fs.mkdirSync(LOCAL,{recursive:true});
const proofParent=process.env.VERTEX_UI_PROOF_ROOT?fs.realpathSync(process.env.VERTEX_UI_PROOF_ROOT):LOCAL;
assert.ok(proofParent===LOCAL||proofParent.startsWith(LOCAL+path.sep));
const OUT=fs.mkdtempSync(path.join(proofParent,'vertex-ui-dom-')),PROOF=proofParent===LOCAL?OUT:proofParent;
function proofWrite(file,data){
 const target=path.resolve(file);assert.ok(target.startsWith(PROOF+path.sep));const files=[];
 const walk=dir=>{for(const item of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,item.name);assert.equal(item.isSymbolicLink(),false);if(item.isDirectory())walk(p);else if(item.isFile())files.push(p);}};walk(PROOF);
 assert.ok(files.length+(fs.existsSync(target)?0:1)<=512,'proof file cap');
 const total=files.reduce((n,p)=>n+fs.statSync(p).size,0),old=fs.existsSync(target)?fs.statSync(target).size:0;
 assert.ok(total-old+Buffer.byteLength(data)<=33554432,'proof byte cap');fs.writeFileSync(target,data);
}
async function screenshot(page,file,fullPage=true){proofWrite(file,await page.screenshot({fullPage}));}
const python=process.env.VERTEX_UI_PYTHON||require('../managed_paths.cjs').python(ROOT);
const helper=String.raw`
from pathlib import Path
import importlib.util,sys,json,threading,socket,traceback
root=Path(sys.argv[1]);out=Path(sys.argv[2]);mode=sys.argv[3];proof=Path(sys.argv[4])
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location('typed_ui_dependencies',root/'tests/test_ai_connection_ui.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fixture=m.AIConnectionTests();fixture.setUp();fixture.ready(saved=mode=='matrix')
from labflow.store import Store
Store(fixture.root)
server=m.create_server(fixture.root,port=0,ai_connections=fixture.config)
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
print(json.dumps({'origin':'http://127.0.0.1:'+str(server.server_port)}),flush=True)
try:
 for line in sys.stdin:
  cmd=line.strip()
  if cmd=='hold':fixture.dep.entered.clear();fixture.dep.release.clear();print(json.dumps({'control':'hold'}),flush=True)
  elif cmd=='release':fixture.dep.release.set();print(json.dumps({'control':'release'}),flush=True)
  elif cmd=='expire':
   import time
   with server._ai_connection_runtime.lock:
    for session in server._ai_connection_runtime.sessions.values():session['deadline']=time.monotonic()-1
   print(json.dumps({'control':'expire'}),flush=True)
  elif cmd=='stop':break
finally:
 fixture.dep.release.set();server.shutdown();server.server_close();thread.join(5)
 rt=server._ai_connection_runtime;address=server.server_address
 with socket.socket() as p:p.bind(address)
 calls=[c[1] for c in fixture.dep.calls if isinstance(c,tuple) and c[0]=='mock_wire']
 result={'dependency_mode':'test_only_typed_modules','real_GCP_calls':0,'real_model_calls':0,'mock_request_settings':calls,
         'calls':{k:fixture.dep.calls.count(k) for k in ['load','save','inspect_metadata','build_matrix']},
         'loop_stopped':not thread.is_alive(),'listener_closed':server.socket.fileno()==-1,'port_rebind':True,
         'active_slot_released':rt.active is None,'worker_reaped':rt.worker is None or not rt.worker.is_alive(),
         'HTTP_workers_reaped':not rt.request_workers,'expiry_timers_reaped':all(not r['timer'].is_alive() for r in rt.runs.values() if 'timer' in r),
         'server_errors':rt.server_errors,'loop_failure':rt.loop_failure,
         'profile':fixture.dep.load(fixture.config['profile_path'])}
 data=(json.dumps(result,indent=2)+'\n').encode('utf-8');target=out/'resource.json';files=[p for p in proof.rglob('*') if p.is_file()]
 assert len(files)+(not target.exists())<=512 and sum(p.stat().st_size for p in files)-(target.stat().st_size if target.exists() else 0)+len(data)<=33554432
 target.write_bytes(data)
 fixture.doCleanups()
`;
proofWrite(path.join(OUT,'browser_host.py'),helper);
const checks=[],resources=[],failures=[];
const replayChecks=[],replayResources=[];
const campaignChecks=[],campaignResources=[],campaignFaultChecks=[];
function host(mode,dir,campaign=false){
 const child=spawn(python,['-X','utf8','-B',path.join(OUT,campaign?'campaign_host.py':'browser_host.py'),ROOT,dir,mode,PROOF],{stdio:['pipe','pipe','pipe']});
 let pending='',stderr='',queue=[],waiters=[];child.stderr.on('data',b=>{stderr+=b.toString();if(stderr.length>8192)child.kill();});
 child.stdout.on('data',b=>{pending+=b.toString();while(pending.includes('\n')){const i=pending.indexOf('\n'),line=pending.slice(0,i);pending=pending.slice(i+1);let item;try{item=JSON.parse(line);}catch{item={invalid:true};}if(waiters.length)waiters.shift()(item);else queue.push(item);}});
 const next=()=>new Promise((resolve,reject)=>{if(queue.length)return resolve(queue.shift());const timer=setTimeout(()=>reject(Error('host response timeout: '+stderr)),10000);waiters.push(v=>{clearTimeout(timer);resolve(v);});});
 const exited=new Promise(resolve=>child.on('exit',(code,signal)=>resolve({code,signal})));
 return {child,next,stderr:()=>stderr,exited,command:async c=>{child.stdin.write(c+'\n');return next();}};
}
const record=(id,details={})=>checks.push({id,...details});
async function scenario(browser,width,mode){
 const dir=path.join(OUT,mode+'-'+width);fs.mkdirSync(dir);const server=host(mode,dir),errors=[],external=[];let context,page,origin,stopped=false;
 try{
  ({origin}=await server.next());assert.ok(origin&&origin.startsWith('http://127.0.0.1:'));
  context=await browser.newContext({viewport:{width,height:900}});page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));const requests=[];
  page.on('request',r=>{if(!r.url().startsWith(origin+'/'))external.push(r.url());if(r.url().includes('/api/ai-connections/'))requests.push({path:new URL(r.url()).pathname,method:r.method()});});
  await page.goto(origin);await page.locator('#result-count').waitFor();
  assert.equal(requests.length,0);record(mode+'-'+width+'-no-implicit-session');
  await page.locator('[data-view="ai-connections"]').click();await page.locator('#ai-save').waitFor();
  await page.waitForFunction(()=>document.querySelector('#ai-status')?.textContent.includes('연결 상태를 조회했습니다'));
  assert.ok((await page.locator('#ai-connections-panel').innerText()).includes('모델 접근 미확인'));
  assert.equal(await page.locator('#ai-run-selected').getAttribute('aria-disabled'),mode==='matrix'?'false':'true');record(mode+'-'+width+'-metadata-and-persistence-gate');
  if(mode==='controls'){
   await page.locator('#ai-level-0').selectOption('LOW');await page.locator('#ai-output-0').fill('128');await page.locator('#ai-timeout-0').fill('1.5');
   await page.locator('#ai-level-1').selectOption('HIGH');await page.locator('#ai-output-1').fill('256');await page.locator('#ai-timeout-1').fill('2');
   await page.locator('#ai-default-model').selectOption('gemini-4-argon');
   await page.locator('#ai-save').click();await page.waitForFunction(()=>document.querySelector('#ai-status')?.textContent.includes('프로필을 저장했습니다'));
   assert.equal(await page.locator('#ai-timeout-0').inputValue(),'1.5');assert.equal(await page.locator('#ai-level-1').inputValue(),'HIGH');
   assert.equal(await page.locator('#ai-run-model').inputValue(),'gemini-4-argon','untouched run model follows saved selection');record(width+'-separate-profile-models-persisted');
   await page.locator('#ai-run-model').selectOption('gemini-4-argon');await page.locator('#ai-run-level').selectOption('HIGH');
   await page.locator('#ai-run-output').fill('256');await page.locator('#ai-run-timeout').fill('1.25');
   await page.locator('#ai-run-selected').click();await page.waitForFunction(()=>document.querySelector('.ai-result tr[data-state="success"]'));
   assert.equal(await page.locator('.ai-result tbody tr').count(),6);assert.equal(await page.locator('.ai-result tr[data-state="success"]').count(),1);
   const text=await page.locator('.ai-result').innerText();assert.ok(text.includes('mock')&&text.includes('미평가')&&text.includes('비용 미확인'));
   assert.ok(!text.includes('provider-response.bin')&&!text.includes('vertex-exchange:'));record(width+'-selected1-notselected5-typed-record');
   assert.ok(await page.locator('.ai-history button').count()>0,'terminal run refreshes own history and budget metadata');record(width+'-selected-terminal-metadata');
   const before=requests.length;await page.locator('.ai-result summary').first().click();assert.equal(requests.length,before);
   const detail=await page.locator('.ai-result details').first().innerText();assert.ok(detail.includes('1.25')&&detail.includes('settings_sha256'));record(width+'-details-no-generation-hash-opaque');
   const starts=requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length;
   await page.locator('#ai-run-matrix').click();assert.equal(requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length,starts);record(width+'-matrix-thinking-explicit-rejection');
   await page.locator('#ai-run-level').selectOption('');await server.command('hold');await page.locator('#ai-run-matrix').click();
   await page.waitForFunction(()=>document.querySelector('#ai-cancel')?.getAttribute('aria-disabled')==='false');
   const cancelStart=Date.now();await page.locator('#ai-cancel').click();await page.waitForFunction(()=>document.querySelector('#ai-status')?.textContent.includes('취소를 요청했습니다'));
   assert.ok(Date.now()-cancelStart<4000);await page.waitForFunction(()=>document.querySelector('.ai-result')?.textContent.includes('finished'));record(width+'-cancel-while-slot-held');await server.command('release');
   // A state403 must retain the last successful observation and must not resubmit a run.
   const rejected=origin+'/api/ai-connections/state';await page.route(rejected,r=>r.fulfill({status:403,contentType:'application/json',body:'{"error":{"code":"ai_connection_ui_access_denied"}}'}));
   const count=requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length;
   await page.locator('#ai-refresh').click();await page.waitForFunction(()=>document.querySelector('#ai-status')?.textContent.includes('조회 실패'));
   assert.ok((await page.locator('#ai-connections-panel').innerText()).includes('이전 관측'));assert.equal(requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length,count);
   await page.unroute(rejected);await page.locator('#ai-refresh').click();await page.waitForFunction(()=>document.querySelector('#ai-status')?.textContent.includes('연결 상태를 조회했습니다'));record(width+'-source403-last-good-no-retry');
   // Preserve this failure if the renderer lacks its required publication guard.
   await page.evaluate(()=>{const original=Document.prototype.createElement;Document.prototype.createElement=function(name,...args){if(name==='fieldset'){Document.prototype.createElement=original;throw Error('synthetic-render-failure');}return original.call(this,name,...args);};});
   const startsBeforeRender=requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length;
   await page.locator('#ai-run-selected').click();await page.waitForTimeout(100);assert.equal(errors.length,0,'render failure must not become an unhandled page rejection');
   assert.equal(requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length,startsBeforeRender,'render preparation failure must prevent a source POST');record(width+'-render-failure-last-good');
   await page.evaluate(()=>{dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));});
   assert.equal(requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length,count);record(width+'-synthetic-bfcache-no-auto-run');
   await server.command('expire');await page.locator('#ai-refresh').click();await page.waitForFunction(()=>document.querySelector('#ai-status')?.textContent.includes('연결 상태를 조회했습니다'));
   assert.equal(await page.locator('.ai-result').count(),0,'new session must retire old-session run controls/observations');
   assert.equal(requests.filter(x=>x.method==='POST'&&x.path.endsWith('/run')).length,count);record(width+'-new-session-retires-old-run-scope');
  }else{
   await page.locator('#ai-run-matrix').focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>document.querySelectorAll('.ai-result tr[data-state="success"]').length===6);
   assert.equal(await page.locator('.ai-result tbody tr').count(),6);assert.ok((await page.locator('.ai-result').innerText()).includes('mock'));record(width+'-keyboard-matrix6');
   assert.ok(await page.locator('.ai-history button').count()>0,'matrix completion refreshes own history and budget metadata');record(width+'-matrix-terminal-metadata');
  }
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);record(mode+'-'+width+'-no-viewport-overflow');
  assert.equal(external.length,0);assert.equal(errors.length,0);await screenshot(page,path.join(dir,'page.png'));
 }catch(error){failures.push({width,mode,message:error.message,page_errors:errors});if(page)await screenshot(page,path.join(dir,'failure.png')).catch(()=>{});throw error;}
 finally{
  if(context)await context.close();server.child.stdin.end('stop\n');let cleanupTimer;const exited=await Promise.race([server.exited,new Promise((_,reject)=>{cleanupTimer=setTimeout(()=>reject(Error('host cleanup timeout')),10000);})]);clearTimeout(cleanupTimer);stopped=true;
  assert.equal(exited.code,0,server.stderr());assert.equal(server.stderr(),'');const resource=JSON.parse(fs.readFileSync(path.join(dir,'resource.json'),'utf8'));
  for(const key of ['loop_stopped','listener_closed','port_rebind','active_slot_released','worker_reaped','HTTP_workers_reaped','expiry_timers_reaped'])assert.equal(resource[key],true,key);
  assert.equal(resource.server_errors.length,0);assert.equal(resource.loop_failure,false);
  resources.push({width,mode,...resource,child_exit:exited.code,browser_context_closed:true});
 }
}
async function registeredReplay(browser,width,packet){
 const positive=new Map();for(const r of packet.records)if(r.variant==='registered-pass'&&!positive.has(r.scenario_id))positive.set(r.scenario_id,r);
 assert.equal(positive.size,7,'owned genuine HTTP capture must contain all seven independently registered inputs');
 const records=[...positive.values(),...packet.records.filter(r=>r.variant==='strict-reject'||r.variant.startsWith('transport-'))];
 assert.equal(records.length,12);assert.ok(records.every(r=>r.scope.startsWith('genuine D1+D3')));
 const sockets=new Set();let origin,context,current,delivered=false,overlay=false,page;const errors=[],requests=[],external=[];
 const server=http.createServer((req,res)=>{
  const name=new URL(req.url,'http://127.0.0.1').pathname;
  if(name==='/'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><button id="show-ai">모델 연결</button><main id="panel"></main><script type="module">import {createAIConnectionPanel} from "/panel.mjs";globalThis.panel=createAIConnectionPanel(document.querySelector("#panel"));document.querySelector("#show-ai").addEventListener("click",()=>panel.show());</script>');}
  else if(name==='/panel.mjs'||name==='/styles.css'){res.setHeader('Content-Type',name.endsWith('.mjs')?'text/javascript; charset=utf-8':'text/css; charset=utf-8');res.end(fs.readFileSync(path.join(ROOT,name==='/panel.mjs'?'frontend/ai_connections/panel.mjs':'frontend/styles.css')));}
  else{res.statusCode=404;res.end();}
 });
 server.on('connection',socket=>{sockets.add(socket);socket.on('close',()=>sockets.delete(socket));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const address=server.address();origin='http://127.0.0.1:'+address.port;
 const dir=path.join(OUT,'registered-replay-'+width);fs.mkdirSync(dir);
 try{
  context=await browser.newContext({viewport:{width,height:900}});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(origin+'/'))external.push(r.url());if(r.url().includes('/api/ai-connections/'))requests.push({method:r.method(),path:new URL(r.url()).pathname});});
  await page.route(origin+'/api/ai-connections/**',async route=>{
   const request=route.request(),name=new URL(request.url()).pathname.split('/').pop(),headers={'Content-Type':'application/json','X-AI-Connection-CSRF':'a'.repeat(64)};let value;
   if(name==='session')value={schema_version:1,kind:'ai_connection_session',capabilities:['read_profile','edit_profile','run_registered_synthetic','cancel_own'],expires_at:Date.now()/1000+900};
   else if(name==='state'){
    value=JSON.parse(JSON.stringify(delivered?current.after:current.state));
    if(overlay)value.scenarios.push({scenario_id:'unsupported-synthetic-x',label:'미지원 · synthetic overlay',input_sha256:'1'.repeat(64),schema_sha256:'2'.repeat(64),evaluator_id:'unsupported-evaluator'});
   }else if(name==='run'){
    assert.equal(request.method(),'POST');assert.equal(request.headers()['x-ai-connection-csrf'],'a'.repeat(64));
    const body=request.postDataJSON();assert.equal(body.scenario_id,current.scenario_id);assert.equal(body.matrix,false);assert.equal(Object.keys(body).length,5);value=current.queued;
   }else{assert.equal(name,current.terminal.run_id);value=current.terminal;delivered=true;}
   await route.fulfill({status:name==='run'?202:200,headers,body:JSON.stringify(value)});
  });
  for(const record of records){
   current=record;delivered=false;overlay=false;await page.goto(origin+'/');await page.locator('#show-ai').click();await page.locator('#ai-scenario').waitFor();
   assert.equal(await page.locator('#ai-scenario option').count(),7);assert.ok((await page.locator('#panel').innerText()).includes('인증 메타데이터 사전 점검'));
   await page.locator('#ai-scenario').selectOption(record.scenario_id);await page.locator('#ai-run-selected').click();
   await page.waitForFunction(()=>document.querySelector('.ai-result')?.textContent.includes('finished'));
   assert.equal(await page.locator('.ai-result tbody tr').count(),6);
   const observed=await page.locator('.ai-result').innerText(),selected=record.terminal.cells.find(c=>c.settings!==null);
   assert.ok(observed.includes(selected.reason_code));assert.ok(observed.includes('미평가')&&observed.includes('비용 미확인'));
   assert.ok(!observed.includes('provider-response.bin')&&!observed.includes('vertex-exchange:'));
   if(record.scenario_id.startsWith('intent-')||record.scenario_id.startsWith('intake-'))assert.ok(observed.includes('의미평가 미연결'));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   replayChecks.push({width,scenario_id:record.scenario_id,variant:record.variant,source_run_id:record.terminal.run_id,scope:'same genuine protected HTTP DTO replay only; new genuine API/producer executions0'});
   await screenshot(page,path.join(dir,record.scenario_id+'-'+record.variant+'.png'));
  }
  const starts=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/run')).length;current=positive.get('DGM-AI-CONNECTION-001');delivered=false;overlay=true;
  await page.locator('#ai-refresh').click();await page.waitForFunction(()=>document.querySelector('#ai-scenario')?.options.length===8);
  assert.equal(await page.locator('#ai-run-selected').getAttribute('aria-disabled'),'false','global ready gate alone must not masquerade as unsupported selection gating');
  await page.locator('#ai-scenario').selectOption('unsupported-synthetic-x');
  assert.equal(await page.locator('#ai-run-selected').getAttribute('aria-disabled'),'true');assert.equal(await page.locator('#ai-run-matrix').getAttribute('aria-disabled'),'true');
  await page.locator('#ai-run-selected').dispatchEvent('click');assert.equal(requests.filter(r=>r.method==='POST'&&r.path.endsWith('/run')).length,starts);
  assert.ok((await page.locator('#panel').innerText()).includes('미지원입니다'));replayChecks.push({width,scope:'synthetic catalog negative overlay; unsupported selection sends no POST'});
  assert.equal(external.length,0);assert.equal(errors.length,0);
 }catch(error){if(page)await screenshot(page,path.join(dir,'failure.png')).catch(()=>{});failures.push({width,mode:'registered-replay',message:error.message,page_errors:errors});throw error;}
 finally{
  if(context)await context.close();server.closeIdleConnections?.();await new Promise(resolve=>server.close(resolve));
  const closeDeadline=Date.now()+2000;while(sockets.size&&Date.now()<closeDeadline)await new Promise(resolve=>setTimeout(resolve,10));
  const probe=http.createServer();await new Promise(resolve=>probe.listen(address.port,'127.0.0.1',resolve));await new Promise(resolve=>probe.close(resolve));
  assert.equal(server.listening,false);assert.equal(sockets.size,0);replayResources.push({width,browser_context_closed:true,listener_closed:true,sockets_closed:true,port_rebind:true,genuine_API_executions:0,fake_D2_productions:0});
 }
}
const campaignHelper=String.raw`
from pathlib import Path
import importlib.util,json,sys,socket
root=Path(sys.argv[1]);case=sys.argv[3];sys.path[:0]=[str(root),str(root/'tests')]
spec=importlib.util.spec_from_file_location('owned_campaign_ui',root/'tests/test_ai_connection_ui.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fixture=m.CampaignReadbackHTTPTests();fixture.setUp()
packet=dict(m.campaign_inputs())[case];server=fixture.start(packet);rt=server._ai_connection_runtime
report=json.loads(rt.campaign_json)
print(json.dumps({'origin':'http://127.0.0.1:'+str(server.server_port),'case':case,
 'report_json':rt.campaign_json.decode('utf-8'),'selection':rt.campaign_selection,
 'history_rows':sum(len(c['history']) for c in report['cells']),
 'reader_startups':fixture.reader_spy.call_count}),flush=True)
try:
 for line in sys.stdin:
  cmd=line.strip()
  if cmd=='rotate':
   with rt.lock:rt.sessions.clear()
   print(json.dumps({'control':'rotate'}),flush=True)
  elif cmd=='stop':break
finally:
 workspace_unchanged=not list(fixture.root.iterdir())
 assert workspace_unchanged, 'readback-only host wrote workspace/DB files'
 fixture.doCleanups()
 with socket.socket() as probe:probe.bind(server.server_address)
 print(json.dumps({'resource':{'loop_stopped':rt.loop_thread is None,'listener_closed':server.socket.fileno()==-1,
  'active_slot_released':rt.active is None,'worker_reaped':rt.worker is None,'HTTP_workers_reaped':not rt.request_workers,
  'expiry_timers_reaped':not rt.runs,'port_rebind':True,'server_errors':rt.server_errors,'loop_failure':rt.loop_failure,
  'reader_startups':fixture.reader_spy.call_count,'workspace_unchanged':workspace_unchanged,'actual_model_calls':0}}),flush=True)
`;
proofWrite(path.join(OUT,'campaign_host.py'),campaignHelper);
async function campaignScenario(browser,width,caseName){
 const dir=path.join(OUT,'campaign-'+caseName+'-'+width);fs.mkdirSync(dir);const server=host(caseName,dir,true),errors=[],external=[],requests=[];let context,page,info;
 try{
  info=await server.next();assert.ok(info.origin&&info.report_json);assert.equal(info.reader_startups,1);
  context=await browser.newContext({viewport:{width,height:900}});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/ai-connections/'))requests.push({method:r.method(),path:new URL(r.url()).pathname});});
  if(caseName==='mixed'&&width===390){
   const intakeStatuses=[];page.on('response',r=>{if(r.url()===info.origin+'/api/intakes')intakeStatuses.push(r.status());});
   await page.goto(info.origin+'/');await page.locator('[data-view="ai-connections"]').click();await page.locator('#ai-campaign-read').waitFor();
   assert.ok(intakeStatuses.every(s=>s===503));campaignFaultChecks.push({width,fault:'full-app-readback-only-shell',scope:'real default app/static assets; unrelated intake API denied, workspace unchanged'});
  }
  await page.route(info.origin+'/',route=>route.fulfill({status:200,contentType:'text/html; charset=utf-8',body:'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><button id="show-ai">모델 연결</button><main id="panel"></main><script type="module">import {createAIConnectionPanel} from "/ai-connections/panel.mjs";globalThis.panel=createAIConnectionPanel(document.querySelector("#panel"));document.querySelector("#show-ai").addEventListener("click",()=>panel.show());</script>'}));
  await page.goto(info.origin+'/');await page.locator('#show-ai').click();await page.locator('#ai-campaign-read').waitFor({timeout:3000});
  await page.waitForFunction(()=>document.querySelector('#ai-campaign-read')?.getAttribute('aria-disabled')==='false');
  assert.equal(requests.filter(r=>r.path.endsWith('/campaign-readback')).length,0,'campaign is explicit, never fetched by show/state refresh');
  await page.locator('#ai-campaign-read').click();await page.waitForFunction(()=>document.querySelector('#ai-campaign-status')?.textContent.includes('조회했습니다'));
  assert.equal(await page.locator('[data-campaign-axis]').count(),6);assert.equal(await page.locator('[data-campaign-history]').count(),info.history_rows);
  const evidence=page.locator('[data-campaign-history] summary').first();await evidence.focus();await page.keyboard.press('Enter');
  const text=await page.locator('#panel').innerText();assert.ok(text.includes('provided_records_only')&&text.includes('권한 확인 미검증(false)')&&text.includes('기초 자료 검증 미검증(false)')&&text.includes('업무 품질 미평가'));
  assert.ok(text.includes('source')&&text.includes('성공을 뜻하지'));assert.ok(text.includes('미확인(null)'));
  if(caseName==='linked-replay')assert.ok(text.includes('원 기록 상태')&&text.includes('판단 불명')&&text.includes('제공 해석 후 상태')&&text.includes('기록 성공'));
  if(caseName==='unlinked-replay')assert.ok(text.includes('원 연결 없는 제공 재생')&&text.includes('제공 항목 없음'));
  if(caseName==='big-partials')assert.ok(text.includes('1770887431076116954944')&&text.includes('9223372036854775807'));
  for(const secret of ['DO-NOT-EXPOSE-AUTH-ID','DO-NOT-EXPOSE-RESPONSE-ID','provider-response.bin','response-text.bin'])assert.ok(!text.includes(secret));
  assert.equal(requests.some(r=>r.method==='POST'),false);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  if(caseName==='mixed'||caseName==='linked-replay')await screenshot(page,path.join(dir,'viewport.png'),false);
  if(width===390)proofWrite(path.join(OUT,'campaign-'+caseName+'-report.json'),info.report_json);
  campaignChecks.push({width,case:caseName,history_rows:info.history_rows,reader_startups:1,scope:'genuine pure reader startup -> real protected GET -> production panel; actual model0'});
  if(caseName==='linked-replay'){
   const endpoint=info.origin+'/api/ai-connections/campaign-readback';
   for(const fault of ['HTTP503','selection-mismatch','authority-true']){
    await page.route(endpoint,route=>route.fulfill({status:fault==='HTTP503'?503:200,headers:{'Content-Type':'application/json','X-AI-Campaign-Selection':fault==='selection-mismatch'?'0'.repeat(64):info.selection},
      body:fault==='HTTP503'?'{"error":{"code":"ai_connection_ui_unavailable"}}':fault==='authority-true'?info.report_json.replace('"root_authorization_verified":false','"root_authorization_verified":true'):info.report_json}));
    await page.locator('#ai-campaign-read').click();await page.waitForFunction(()=>document.querySelector('#ai-campaign-status')?.textContent.includes('조회 실패'));
    assert.equal(await page.locator('[data-campaign-history]').count(),info.history_rows);assert.ok((await page.locator('#panel').innerText()).includes('이전 관측'));
    await page.unroute(endpoint);campaignFaultChecks.push({width,fault,scope:'typed transport injection only; not a genuine API success'});
   }
   const readsBeforeRender=requests.filter(r=>r.path.endsWith('/campaign-readback')).length;
   await page.evaluate(()=>{const native=Document.prototype.createElement;Document.prototype.createElement=function(name,...args){if(name==='caption'){Document.prototype.createElement=native;throw Error('synthetic-campaign-render-failure');}return native.call(this,name,...args);};});
   await page.locator('#ai-campaign-read').click();await page.waitForFunction(()=>document.querySelector('#ai-campaign-status')?.textContent.includes('화면 준비 실패'));
   assert.equal(requests.filter(r=>r.path.endsWith('/campaign-readback')).length,readsBeforeRender);assert.equal(await page.locator('[data-campaign-history]').count(),info.history_rows);
   campaignFaultChecks.push({width,fault:'render-before-request',scope:'synthetic DOM failure; last-good preserved and new GET prevented'});
   let releaseDeadline,deadlineEntered;const deadlineGate=new Promise(resolve=>releaseDeadline=resolve),deadlineArrival=new Promise(resolve=>deadlineEntered=resolve);
   await page.evaluate(()=>{const nativeSet=window.setTimeout,nativeClear=window.clearTimeout,timers=new Map();window.setTimeout=function(fn,ms,...args){const id=nativeSet.call(window,fn,ms,...args);if(ms===10000)timers.set(id,()=>fn(...args));return id;};window.clearTimeout=function(id){timers.delete(id);return nativeClear.call(window,id);};window.__campaignDeadline={fire(){const pending=[...timers];for(const [id,fn]of pending){nativeClear.call(window,id);timers.delete(id);fn();}return pending.length;},restore(){for(const id of timers.keys())nativeClear.call(window,id);window.setTimeout=nativeSet;window.clearTimeout=nativeClear;delete window.__campaignDeadline;}};});
   await page.route(endpoint,async route=>{deadlineEntered();await deadlineGate;await route.abort().catch(()=>{});});
   try{
    await page.locator('#ai-campaign-read').click();await deadlineArrival;assert.equal(await page.evaluate(()=>__campaignDeadline.fire()),1);
    await page.waitForFunction(()=>document.querySelector('#ai-campaign-status')?.textContent.includes('조회 실패'));assert.equal(await page.locator('[data-campaign-history]').count(),info.history_rows);
    campaignFaultChecks.push({width,fault:'deadline-callback',scope:'synthetic deadline callback, no wall-clock duration claim; last-good preserved'});
   }finally{releaseDeadline();await page.unroute(endpoint);await page.evaluate(()=>__campaignDeadline.restore());}
   let deliverLate,lateArrived;const late=new Promise(resolve=>deliverLate=resolve),arrived=new Promise(resolve=>lateArrived=resolve);
   await page.route(endpoint,async route=>{lateArrived();await late;await route.fulfill({status:200,headers:{'Content-Type':'application/json','X-AI-Campaign-Selection':info.selection},body:info.report_json.replace('UI-SYN-linked-replay','LATE-INJECTED')}).catch(()=>{});});
   try{
    await page.locator('#ai-campaign-read').click();await arrived;await page.evaluate(()=>panel.hide());deliverLate();
    await page.unroute(endpoint);await page.evaluate(()=>panel.show());await page.waitForFunction(()=>document.querySelector('#ai-campaign-read')?.getAttribute('aria-disabled')==='false');
    assert.ok(!(await page.locator('#panel').innerText()).includes('LATE-INJECTED'));assert.equal(await page.locator('[data-campaign-history]').count(),info.history_rows);
    campaignFaultChecks.push({width,fault:'late-after-hide',scope:'typed late response; previous observation retained, never published as current'});
   }finally{deliverLate();await page.unroute(endpoint);}
   await page.locator('#ai-campaign-read').click();await page.waitForFunction(()=>document.querySelector('#ai-campaign-status')?.textContent.includes('조회했습니다'));
   await server.command('rotate');let continueRead,scopeArrived;const hold=new Promise(resolve=>continueRead=resolve),scopeReady=new Promise(resolve=>scopeArrived=resolve);
   await page.route(endpoint,async route=>{scopeArrived();await hold;await route.continue().catch(()=>{});});
   try{
    await page.locator('#ai-campaign-read').click();await scopeReady;
    assert.equal(await page.locator('[data-campaign-history]').count(),0,'new nonce must retire old read scope before the next GET completes');
    continueRead();await page.waitForFunction(()=>document.querySelector('#ai-campaign-status')?.textContent.includes('조회했습니다'));
    assert.equal(await page.locator('[data-campaign-history]').count(),info.history_rows);
    campaignFaultChecks.push({width,fault:'new-session-pending-read',scope:'genuine new session and delayed genuine GET; old scope retired before response'});
   }finally{continueRead();await page.unroute(endpoint);}
  }
  assert.equal(errors.length,0);assert.equal(external.length,0);
  await page.evaluate(()=>panel.destroy());assert.equal(await page.locator('#panel').innerText(),'');
 }catch(error){failures.push({width,mode:'campaign',case:caseName,message:error.message,page_errors:errors});if(page)await screenshot(page,path.join(dir,'failure.png'),false).catch(()=>{});throw error;}
 finally{
  if(context)await context.close();server.child.stdin.end('stop\n');const stopped=await server.next();const exited=await server.exited;
  assert.equal(exited.code,0,server.stderr());assert.equal(server.stderr(),'');assert.ok(stopped.resource);
  for(const key of ['loop_stopped','listener_closed','active_slot_released','worker_reaped','HTTP_workers_reaped','expiry_timers_reaped','port_rebind','workspace_unchanged'])assert.equal(stopped.resource[key],true,key);
  assert.equal(stopped.resource.server_errors.length,0);assert.equal(stopped.resource.loop_failure,false);assert.equal(stopped.resource.reader_startups,1);
  campaignResources.push({width,case:caseName,...stopped.resource,browser_context_closed:true,child_exit:exited.code});
 }
}
(async()=>{let browser;try{browser=await chromium.launch({headless:true});if(process.env.VERTEX_UI_CAMPAIGN_ONLY!=='1')for(const width of [390,1440])for(const mode of ['controls','matrix'])await scenario(browser,width,mode);
 let replay={status:'not_run',reason:'owned genuine HTTP capture not supplied'};
 if(process.env.VERTEX_UI_HTTP_REPLAY){
  const file=fs.realpathSync(process.env.VERTEX_UI_HTTP_REPLAY);assert.ok(file.startsWith(LOCAL+path.sep));assert.ok(fs.statSync(file).size<=33554432);
  const bytes=fs.readFileSync(file),packet=JSON.parse(bytes);assert.equal(packet.actual_model_calls,0);proofWrite(path.join(OUT,'genuine-HTTP-captures.json'),bytes);
  for(const width of [390,1440])await registeredReplay(browser,width,packet);
  replay={status:'pass',capture_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),registered_unique_inputs:7,checks:replayChecks,resources:replayResources,genuine_API_executions:0,fake_D2_productions:0,scope:'DTO copies; never added to genuine API pass counts'};
 }
 for(const width of [390,1440])for(const name of ['mixed','linked-replay','unlinked-replay','competing-replay','valid-source-conflict','big-partials'].filter(n=>!process.env.VERTEX_UI_CAMPAIGN_CASE||n===process.env.VERTEX_UI_CAMPAIGN_CASE))await campaignScenario(browser,width,name);
 proofWrite(path.join(OUT,'result.json'),JSON.stringify({status:'pass',checks,resources,registered_replay:replay,campaign_checks:campaignChecks,campaign_resources:campaignResources,campaign_transport_faults:campaignFaultChecks,real_GCP_calls:0,real_model_calls:0,scope:'separate legacy typed HTTP, optional DTO replay, and genuine pure-reader protected HTTP/DOM'},null,2));console.log(JSON.stringify({status:'pass',checks:checks.length,registered_replay_checks:replayChecks.length,campaign_checks:campaignChecks.length,output:OUT}));
 }catch(error){proofWrite(path.join(OUT,'failure.json'),JSON.stringify({status:'fail',message:error.message,checks,resources,registered_replay_checks:replayChecks,registered_replay_resources:replayResources,campaign_checks:campaignChecks,campaign_resources:campaignResources,campaign_transport_faults:campaignFaultChecks,failures},null,2));console.error(JSON.stringify({status:'fail',message:error.message,output:OUT}));process.exitCode=1;}
 finally{if(browser)await browser.close();}})();
