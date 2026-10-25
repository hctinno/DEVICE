/* Actual protected HTTP -> typed dependency double -> record -> Chromium DOM. Cloud calls0. */
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'../..'),LOCAL=path.join(ROOT,'.local');fs.mkdirSync(LOCAL,{recursive:true});
const OUT=fs.mkdtempSync(path.join(LOCAL,'vertex-ui-dom-'));
const python=process.env.VERTEX_UI_PYTHON||'python';
const helper=String.raw`
from pathlib import Path
import importlib.util,sys,json,threading,socket,traceback
root=Path(sys.argv[1]);out=Path(sys.argv[2]);mode=sys.argv[3]
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
 (out/'resource.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 fixture.doCleanups()
`;
fs.writeFileSync(path.join(OUT,'browser_host.py'),helper,'utf8');
const checks=[],resources=[],failures=[];
function host(mode,dir){
 const child=spawn(python,['-X','utf8','-B',path.join(OUT,'browser_host.py'),ROOT,dir,mode],{stdio:['pipe','pipe','pipe']});
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
  assert.equal(external.length,0);assert.equal(errors.length,0);await page.screenshot({path:path.join(dir,'page.png'),fullPage:true});
 }catch(error){failures.push({width,mode,message:error.message,page_errors:errors});if(page)await page.screenshot({path:path.join(dir,'failure.png'),fullPage:true}).catch(()=>{});throw error;}
 finally{
  if(context)await context.close();server.child.stdin.end('stop\n');let cleanupTimer;const exited=await Promise.race([server.exited,new Promise((_,reject)=>{cleanupTimer=setTimeout(()=>reject(Error('host cleanup timeout')),10000);})]);clearTimeout(cleanupTimer);stopped=true;
  assert.equal(exited.code,0,server.stderr());assert.equal(server.stderr(),'');const resource=JSON.parse(fs.readFileSync(path.join(dir,'resource.json'),'utf8'));
  for(const key of ['loop_stopped','listener_closed','port_rebind','active_slot_released','worker_reaped','HTTP_workers_reaped','expiry_timers_reaped'])assert.equal(resource[key],true,key);
  assert.equal(resource.server_errors.length,0);assert.equal(resource.loop_failure,false);
  resources.push({width,mode,...resource,child_exit:exited.code,browser_context_closed:true});
 }
}
(async()=>{let browser;try{browser=await chromium.launch({headless:true});for(const width of [390,1440])for(const mode of ['controls','matrix'])await scenario(browser,width,mode);
 fs.writeFileSync(path.join(OUT,'result.json'),JSON.stringify({status:'pass',checks,resources,real_GCP_calls:0,real_model_calls:0,scope:'actual protected HTTP and Chromium with test-only typed concrete dependency doubles'},null,2));console.log(JSON.stringify({status:'pass',checks:checks.length,output:OUT}));
 }catch(error){fs.writeFileSync(path.join(OUT,'failure.json'),JSON.stringify({status:'fail',message:error.message,checks,resources,failures},null,2));console.error(JSON.stringify({status:'fail',message:error.message,output:OUT}));process.exitCode=1;}
 finally{if(browser)await browser.close();}})();
