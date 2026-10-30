/* Real catalog API -> owned loopback HTTP -> read-only catalog DOM. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process'),{createHash}=require('node:crypto');
const {reserveEvidence}=require('../intake_fixture_browser_check.cjs');
const ROOT=fs.realpathSync(path.resolve(__dirname,'../..')),sha=value=>createHash('sha256').update(value).digest('hex');
const write=(file,value)=>fs.writeFileSync(file,value,{flag:'wx'}),json=(file,value)=>write(file,JSON.stringify(value,null,2)+'\n');
const same=(a,b)=>path.relative(path.resolve(a),path.resolve(b))==='';
const bounded=async(promise,code,milliseconds=7000)=>{let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error(code)),milliseconds);})]);}finally{clearTimeout(timer);}};
const BOOT=`import importlib, importlib.util, hashlib, json, sys, threading
from pathlib import Path
root=Path(sys.argv[1]).resolve(strict=True); evidence=Path(sys.argv[2]).resolve(strict=True)
if not (root/'labflow/__init__.py').is_file(): raise ValueError('regular_source_required')
sys.path.insert(0,str(root))
package=importlib.import_module('labflow')
if Path(package.__file__).resolve()!=root/'labflow/__init__.py' or tuple(Path(p).resolve() for p in package.__path__)!=(root/'labflow',): raise ValueError('package_path_mismatch')
bindings={}
for name,relative in [('labflow.ui_server','labflow/ui_server.py'),('labflow.control_source_catalog','labflow/control_source_catalog.py')]:
    expected=root/relative
    spec=importlib.util.find_spec(name)
    if spec is None or Path(spec.origin).resolve()!=expected: raise ValueError('spec_path_mismatch')
    module=importlib.import_module(name)
    if Path(module.__file__).resolve()!=expected or Path(module.__spec__.origin).resolve()!=expected: raise ValueError('module_path_mismatch')
    bindings[name]={'file':str(expected),'sha256':hashlib.sha256(expected.read_bytes()).hexdigest()}
from labflow.store import Store
from labflow.active_intake import register_source, scan_source
from labflow.ui_server import create_server
store=Store(evidence/'workspace/state'); inbox=evidence/'workspace/inbox'; inbox.mkdir()
register_source(store,'CATALOG-UI',inbox,synthetic=True,settle_seconds=1)
bundle=inbox/'synthetic-request'; bundle.mkdir(); (bundle/'request.txt').write_text('Synthetic catalog UI intake\\nMarket: US\\n',encoding='utf-8')
scan_source(store,'CATALOG-UI',now=100); scan_source(store,'CATALOG-UI',now=101)
before=hashlib.sha256(store.db.read_bytes()).hexdigest()
server=create_server(store.root,port=0); thread=threading.Thread(target=server.serve_forever); thread.start()
try:
    print(json.dumps({'kind':'control_catalog_browser_ready','source_root':str(root),'bindings':bindings,'origin':'http://127.0.0.1:'+str(server.server_port),'database_before':before}),flush=True)
    if sys.stdin.readline().strip()!='stop': raise ValueError('owned_stop_required')
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
    after=hashlib.sha256(store.db.read_bytes()).hexdigest()
    print(json.dumps({'kind':'control_catalog_browser_stopped','server_closed':not thread.is_alive(),'database_after':after,'database_unchanged':before==after}),flush=True)
`;
function sourceHashes(){
  const names=['frontend/index.html','frontend/app.js','frontend/styles.css','frontend/model.mjs','frontend/intake_flow_model.mjs','frontend/virtual_fleet/harness_model.mjs','frontend/intake_fixture_browser_check.cjs',...fs.readdirSync(path.join(ROOT,'frontend/control_sources')).filter(n=>/\.(js|mjs|cjs|html|css)$/.test(n)).map(n=>'frontend/control_sources/'+n),
    ...fs.readdirSync(path.join(ROOT,'control_sources')).filter(n=>n.endsWith('.json')).map(n=>'control_sources/'+n),'research/equipment-control-2026-10-24/deliverables/model_control_sources.json'];
  const visit=folder=>{for(const entry of fs.readdirSync(folder,{withFileTypes:true})){assert(!entry.isSymbolicLink());const full=path.join(folder,entry.name);if(entry.isDirectory() && entry.name!=='__pycache__')visit(full);else if(entry.isFile() && entry.name.endsWith('.py'))names.push(path.relative(ROOT,full).split(path.sep).join('/'));}};
  visit(path.join(ROOT,'labflow'));return Object.fromEntries(names.sort().map(name=>[name,sha(fs.readFileSync(path.join(ROOT,name)))]));
}
async function main(){
  if(process.argv.length>2 || Object.keys(process.env).some(key=>key.startsWith('CONTROL_CATALOG_') && key!=='CONTROL_CATALOG_PYTHON'))throw Error('invalid_configuration');
  if(!fs.existsSync(path.join(ROOT,'labflow/control_source_catalog.py')))throw Error('catalog_dependency_missing');
  const python=process.env.CONTROL_CATALOG_PYTHON || require('../managed_paths.cjs').python(ROOT);
  if(!python.trim() || /[\r\n\0]/.test(python))throw Error('invalid_configuration');
  const evidence=reserveEvidence(ROOT),checks=[],navigationChecks=[],cleanup={browser_closed:false,producer_closed:false,server_closed:false};
  const result={kind:'control_source_actual_browser',contract_fixture:false,actual_catalog_connected:false,synthetic_workspace:true,intake_source_synthetic:true,
    hardware_verified:false,vendor_binary_executed:false,checks,navigation_checks:navigationChecks,navigation_contract:'fragment_v1',cleanup,passed:false};
  const before=sourceHashes();result.source_sha256=before;let browser,child,closed,stdout='',stderr='',failed,ready,rejectReady;
  const errors=[],external=[],requests=[];let exitResolve;
  try{
    const initialized=new Promise((resolve,reject)=>{ready=resolve;rejectReady=reject;});closed=new Promise(resolve=>exitResolve=resolve);
    child=spawn(python,['-B','-X','utf8','-c',BOOT,ROOT,evidence],{cwd:ROOT,windowsHide:true,stdio:['pipe','pipe','pipe'],env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'}});
    result.producer_pid=child.pid;
    child.stdin.on('error',()=>{});
    child.on('error',()=>rejectReady(Error('catalog_server_start_failed')));child.on('close',(code,signal)=>{exitResolve({code,signal});rejectReady(Error('catalog_server_closed_early'));});
    child.stdout.on('data',chunk=>{stdout+=chunk.toString('utf8');if(Buffer.byteLength(stdout)>1048576){rejectReady(Error('catalog_server_output_excessive'));child.kill();}else if(stdout.includes('\n')){try{ready(JSON.parse(stdout.slice(0,stdout.indexOf('\n'))));}catch{rejectReady(Error('catalog_server_output_invalid'));}}});
    child.stderr.on('data',chunk=>{if(Buffer.byteLength(stderr)<1048576)stderr+=chunk.toString('utf8');});
    let timer;const binding=await Promise.race([initialized,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('catalog_server_start_timeout')),15000);})]).finally(()=>clearTimeout(timer));
    assert.equal(binding.kind,'control_catalog_browser_ready');assert(same(binding.source_root,ROOT));assert(/^http:\/\/127\.0\.0\.1:[0-9]+$/.test(binding.origin));
    for(const [name,relative] of [['labflow.ui_server','labflow/ui_server.py'],['labflow.control_source_catalog','labflow/control_source_catalog.py']]){assert(same(binding.bindings[name].file,path.join(ROOT,relative)));assert.equal(binding.bindings[name].sha256,before[relative]);}
    result.source_binding=binding;const origin=binding.origin;
    const get=async endpoint=>{const response=await fetch(origin+endpoint,{signal:AbortSignal.timeout(10000)});assert.equal(response.status,200);return response.json();};
    const summary=await get('/api/control-sources/summary');json(path.join(evidence,'actual-summary.json'),summary);assert.equal(summary.item_count,3137);assert.equal(summary.model_count,2867);assert.equal(summary.identity_item_count,270);assert.equal(summary.equipment_id_count,6470);
    result.actual_catalog_connected=true;
    const {chromium}=require('playwright');browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:1440,height:1000}});context.setDefaultTimeout(7000);
    context.on('page',page=>page.on('pageerror',error=>errors.push(error.message)));context.on('request',request=>{requests.push({method:request.method(),url:request.url()});if(!request.url().startsWith(origin+'/'))external.push(request.url());});
    const page=await context.newPage();await page.goto(origin+'/control-sources');
    const settled=()=>page.waitForFunction(()=>document.querySelector('#detail-status').textContent.includes('· 고정 조사 자료'));
    await settled();const check=async(name,action)=>{await action();checks.push(name);console.log('PASS '+name);};
    const search=async(query='',profile='')=>{await page.locator('.id-filters').evaluate(node=>node.open=true);await page.locator('#query').fill(query);await page.locator('#scope').selectOption('');await page.locator('#profile-id').fill(profile);await page.locator('#filters button[type=submit]').click();};
    const selected=async id=>{await page.locator('[data-item-id="'+id+'"]').first().click();await page.waitForFunction(id=>document.querySelector('#detail .detail-card')?.dataset.itemId===id && !document.querySelector('#detail-status').classList.contains('pending'),id);};
    const verifyDetail=async id=>{const value=await get('/api/control-sources/'+id);json(path.join(evidence,id+'-actual.json'),value);const text=await page.locator('#detail').innerText();
      for(const source of value.record.research_record.sources)for(const key of ['url','kind','authority','match_level','access','license','evidence'])assert(text.includes(source[key]));
      assert(text.includes(value.record.research_record.notes));assert.equal(await page.locator('#detail .source').count(),value.record.research_record.sources.length);assert(text.includes('지원 미평가'));
      return value;};
    await check('actual summary and separate intake remain readable',async()=>{assert((await page.locator('#summary').innerText()).includes('3,137'));assert.equal((await get('/api/intakes')).intakes.length,1);assert.equal(summary.adapter_support_status,'not_assessed');assert.equal(summary.hardware_verified,false);
      const intake=await context.newPage();await intake.goto(origin+'/');await intake.waitForFunction(()=>document.querySelector('#last-updated').textContent.includes('KST 조회'));assert(await intake.locator('#error-banner').isHidden());await intake.locator('a[href="/control-sources"]').click();await intake.waitForSelector('.detail-card');await intake.close();});
    await check('stable bounded pagination uses the actual API',async()=>{const first=await page.locator('#items button').evaluateAll(nodes=>nodes.map(n=>n.dataset.itemId));assert.equal(first.length,25);await page.locator('#next').click();await page.waitForFunction(()=>document.querySelector('#page-info').textContent.startsWith('26–'));const next=await page.locator('#items button').evaluateAll(nodes=>nodes.map(n=>n.dataset.itemId));assert.equal(next.length,25);assert(!next.some(id=>first.includes(id)));await page.locator('#previous').click();await page.waitForFunction(()=>document.querySelector('#page-info').textContent.startsWith('1–'));});
    await check('N9030A source associations distinguish IVI and MCP N9030B',async()=>{await search('N9030A');await settled();await selected('MOD-c40c6c5f1b4e7ca9');await verifyDetail('MOD-c40c6c5f1b4e7ca9');assert((await page.locator('#detail').innerText()).includes('N9030B'));await page.screenshot({path:path.join(evidence,'N9030A-desktop.png'),fullPage:true});await page.locator('#detail .source').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(evidence,'N9030A-source-desktop.png')});});
    let keithley;
    await check('DMM6500 manufacturer uncertainty and per-source licenses remain separate',async()=>{await search('DMM6500');await settled();await selected('MOD-4e1a45a25496a054');await verifyDetail('MOD-4e1a45a25496a054');assert((await page.locator('#detail').innerText()).includes('식별 보류'));await selected('MOD-ce43da835609baea');keithley=await verifyDetail('MOD-ce43da835609baea');assert.equal(keithley.record.research_record.sources.length,6);
      await page.locator('#scope').selectOption('identity_unresolved');await page.locator('#filters button[type=submit]').click();await settled();assert.equal(await page.locator('#items button').count(),1);assert.equal(await page.locator('#detail .detail-card').getAttribute('data-item-id'),'MOD-4e1a45a25496a054');});
    await check('N1921A passive classification retains the sensor and host relationship',async()=>{await search('N1921A');await settled();const id=await page.locator('#detail .detail-card').getAttribute('data-item-id');await verifyDetail(id);const text=await page.locator('#detail').innerText();assert(text.includes('독립 제어 비대상') && text.includes('센서') && text.includes('호스트'));});
    await check('multiple normalized and other-manufacturer profile candidates remain unbound',async()=>{for(const id of ['fsv40-dc6e428d29','11667b-1839151d7a']){await search('',id);await settled();assert(await page.locator('#items button').count()>1);const text=await page.locator('#detail').innerText();assert(text.includes('설치 자산 연결 미확정'));assert(text.includes('다른 제조사 표기의 같은 모델 후보'));}
      await search('NO-CATALOG-MATCH-PRIVATE-TEST');await page.waitForFunction(()=>document.querySelector('#detail-status').textContent==='선택할 항목 없음');assert.equal(await page.locator('#items button').count(),0);assert.equal(await page.locator('#detail .detail-card').count(),0);});
    await search('DMM6500');await settled();await selected('MOD-ce43da835609baea');const normalDom=await page.locator('#detail').innerHTML();
    await check('bad DTO and failed GET preserve explicit stale last-good detail',async()=>{
      const listDom=await page.locator('#items').innerHTML(),wrongPage=await get('/api/control-sources?query=DMM6500&offset=0&limit=25');wrongPage.total=3;wrongPage.offset=1;wrongPage.next_offset=null;
      const listRoute=/\/api\/control-sources\?/;await page.route(listRoute,route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(wrongPage)}));await page.locator('#filters button[type=submit]').click();await page.waitForFunction(()=>document.querySelector('#list-status').classList.contains('error'));assert.equal(await page.locator('#items').innerHTML(),listDom);assert.equal(await page.locator('#detail').innerHTML(),normalDom);await page.unroute(listRoute);
      for(const mode of ['bad-dto','bad-id','http-error']){
      await page.route('**/api/control-sources/MOD-ce43da835609baea',async route=>{const value=structuredClone(keithley);if(mode==='bad-dto')value.record.hardware_verified=true;if(mode==='bad-id')value.record.research_record.item_id='MOD-other';await route.fulfill({status:mode==='http-error'?503:200,contentType:'application/json',body:JSON.stringify(mode==='http-error'?{error:{code:'PRIVATE_SERVER_CANARY'}}:value)});});
      await page.locator('#items button[data-item-id="MOD-ce43da835609baea"]').click();await page.waitForFunction(()=>document.querySelector('#detail-status').classList.contains('error'));assert.equal(await page.locator('#detail').innerHTML(),normalDom);assert.equal(await page.locator('#detail').getAttribute('data-stale'),'true');assert(!(await page.locator('body').innerText()).includes('PRIVATE_SERVER_CANARY'));await page.unroute('**/api/control-sources/MOD-ce43da835609baea');
    }});
    await check('literal model notes and unsafe links never execute or autoload',async()=>{const hostile=structuredClone(keithley);hostile.record.research_record.notes='<img src=x onerror="window.catalogInjected=true">';hostile.record.research_record.sources[0].url='javascript:window.catalogInjected=true';
      await page.route('**/api/control-sources/MOD-ce43da835609baea',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(hostile)}));await page.locator('#items button[data-item-id="MOD-ce43da835609baea"]').click();await settled();assert((await page.locator('#detail').innerText()).includes(hostile.record.research_record.notes));assert.equal(await page.locator('#detail img, #detail script, #detail a[href^="javascript:"]').count(),0);assert.equal(await page.evaluate(()=>window.catalogInjected),undefined);await page.unroute('**/api/control-sources/MOD-ce43da835609baea');});
    await check('late detail cannot replace the currently selected ID even when abort is ignored',async()=>{
      await page.evaluate(()=>{window.catalogOriginalFetch=window.fetch;window.fetch=(url,options)=>window.catalogOriginalFetch(url,{...options,signal:undefined});});
      const old=await get('/api/control-sources/MOD-4e1a45a25496a054');let release,arrived;const waiting=new Promise(resolve=>arrived=resolve),hold=new Promise(resolve=>release=resolve);
      await page.route('**/api/control-sources/MOD-4e1a45a25496a054',async route=>{arrived();await hold;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(old)});});
      await page.locator('#items button[data-item-id="MOD-4e1a45a25496a054"]').click();await bounded(waiting,'late_detail_request_not_observed');await selected('MOD-ce43da835609baea');const retained=await page.locator('#detail').innerHTML();const response=page.waitForResponse(url=>url.url().endsWith('/MOD-4e1a45a25496a054'));release();await (await response).finished();await page.evaluate(()=>new Promise(requestAnimationFrame));assert.equal(await page.locator('#detail').innerHTML(),retained);await page.unroute('**/api/control-sources/MOD-4e1a45a25496a054');await page.evaluate(()=>{window.fetch=window.catalogOriginalFetch;delete window.catalogOriginalFetch;});
    });
    await check('390px keyboard view and all requests remain read-only with no external or JS errors',async()=>{await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(evidence,'DMM6500-mobile.png'),fullPage:true});await page.screenshot({path:path.join(evidence,'DMM6500-mobile-top.png')});await page.locator('#detail .source').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(evidence,'DMM6500-mobile-source.png')});await page.locator('#detail .review').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(evidence,'DMM6500-mobile-review.png')});await page.locator('#query').focus();assert.equal(await page.evaluate(()=>document.activeElement.id),'query');
      for(const link of await page.locator('#detail a').evaluateAll(nodes=>nodes.map(n=>({href:n.href,rel:n.rel,target:n.target})))){assert(/^https?:/.test(link.href));assert(link.rel.includes('noopener') && link.rel.includes('noreferrer'));assert.equal(link.target,'_blank');}
      assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert(requests.every(request=>request.method==='GET'));
    });
    const navCheck=async(name,action)=>{await action();navigationChecks.push(name);console.log('PASS NAV '+name);};
    const waitId=id=>page.waitForFunction(id=>document.querySelector('#detail .detail-card')?.dataset.itemId===id && !document.querySelector('#detail-status').classList.contains('pending') && !document.querySelector('#detail-status').classList.contains('error'),id);
    // Both documented page routes force a fresh document for direct-link cases.
    const go=async fragment=>{const target=new URL(page.url()).pathname==='/control-sources'?'/control-sources/':'/control-sources';await page.goto(origin+target+fragment);};
    const hash=()=>page.evaluate(()=>location.hash);
    const listReads=()=>requests.filter(request=>new URL(request.url).pathname==='/api/control-sources').length;
    await page.setViewportSize({width:1440,height:1000});
    await navCheck('direct link and reload restore typed filters limit and off-page selection',async()=>{
      const fragment='#query=N9030A&scope=included&limit=1&item_id=MOD-c40c6c5f1b4e7ca9';
      await go(fragment);await waitId('MOD-c40c6c5f1b4e7ca9');assert.equal(await page.locator('#query').inputValue(),'N9030A');assert.equal(await page.locator('#scope').inputValue(),'included');assert.equal(await page.locator('#items button').count(),1);assert((await page.locator('#detail-status').innerText()).includes('현재 목록 페이지 밖'));assert.equal(await hash(),fragment);
      await page.reload();await waitId('MOD-c40c6c5f1b4e7ca9');assert.equal(await hash(),fragment);assert.equal(await page.locator('#items button').count(),1);
      await go('#item_id=MOD-NAV-unknown');await page.waitForFunction(()=>document.querySelector('#detail-status').classList.contains('error'));assert.equal(await hash(),'#item_id=MOD-NAV-unknown');assert.equal(await page.locator('#detail .detail-card').count(),0);
    });
    await navCheck('search explicit selection and back forward preserve scope and one history entry per action',async()=>{
      await go('#query=N9030A&scope=included&item_id=MOD-c40c6c5f1b4e7ca9');await waitId('MOD-c40c6c5f1b4e7ca9');
      const length=await page.evaluate(()=>history.length);await selected('MOD-aecdf6d16380a2be');assert.equal(await hash(),'#query=N9030A&scope=included&item_id=MOD-aecdf6d16380a2be');assert.equal(await page.evaluate(()=>history.length),length+1);
      await page.locator('#query').fill('DMM6500');await page.locator('#scope').selectOption('identity_unresolved');await page.locator('#filters button[type=submit]').click();await waitId('MOD-4e1a45a25496a054');assert.equal(await hash(),'#query=DMM6500&scope=identity_unresolved');assert.equal(await page.evaluate(()=>history.length),length+2);
      await page.goBack();await waitId('MOD-aecdf6d16380a2be');assert.equal(await page.locator('#query').inputValue(),'N9030A');assert.equal(await page.locator('#scope').inputValue(),'included');
      await page.goForward();await waitId('MOD-4e1a45a25496a054');assert.equal(await page.locator('#query').inputValue(),'DMM6500');assert.equal(await page.locator('#scope').inputValue(),'identity_unresolved');
    });
    await navCheck('bounded pages custom limit and empty query result survive navigation',async()=>{
      await go('#offset=10&limit=10');await page.waitForFunction(()=>document.querySelector('#page-info').textContent.startsWith('11–20'));await settled();await page.locator('#next').click();await page.waitForFunction(()=>document.querySelector('#page-info').textContent.startsWith('21–30'));assert.equal(await hash(),'#offset=20&limit=10');
      await page.goBack();await page.waitForFunction(()=>document.querySelector('#page-info').textContent.startsWith('11–20'));await page.goForward();await page.waitForFunction(()=>document.querySelector('#page-info').textContent.startsWith('21–30'));
      await go('#query=NO-CATALOG-NAV-MATCH&limit=10');await page.waitForFunction(()=>document.querySelector('#detail-status').textContent==='선택할 항목 없음');assert.equal(await page.locator('#items button').count(),0);await page.reload();await page.waitForFunction(()=>document.querySelector('#detail-status').textContent==='선택할 항목 없음');assert.equal(await hash(),'#query=NO-CATALOG-NAV-MATCH&limit=10');
    });
    await navCheck('N1921A and other-manufacturer profile links retain unassessed source meaning',async()=>{
      await go('#query=N1921A&scope=excluded_passive&item_id=MOD-753eb28b11306834');await waitId('MOD-753eb28b11306834');assert((await page.locator('#detail').innerText()).includes('센서'));
      const actual=await get('/api/control-sources?profile_id=11667b-1839151d7a');const id=actual.items[0].item_id;await go('#profile_id=11667b-1839151d7a&item_id='+id);await waitId(id);assert.equal(await page.locator('#profile-id').inputValue(),'11667b-1839151d7a');assert((await page.locator('#detail').innerText()).includes('다른 제조사 표기의 같은 모델 후보'));assert((await page.locator('#detail').innerText()).includes('설치 자산 연결 미확정'));
    });
    await navCheck('bad fragments show fixed error and replace with safe default without raw payload',async()=>{
      await page.addInitScript(()=>{window.catalogInitialHistoryLength=history.length;});
      for(const fragment of ['#unknown=PRIVATE_NAV_CANARY','#query=a&query=b','#query=%FF','#offset=-1','#profile_id=MOD%252F1','#query='+'A'.repeat(4096)]){
        await go(fragment);await page.waitForFunction(()=>document.querySelector('#navigation-status')?.textContent.includes('invalid_catalog_navigation'));await settled();assert.equal(await hash(),'');assert.equal(await page.locator('#query').inputValue(),'');assert.equal(await page.locator('#items button').count(),25);assert(!(await page.locator('body').innerText()).includes('PRIVATE_NAV_CANARY'));assert.equal(await page.evaluate(()=>history.length===window.catalogInitialHistoryLength),true);
      }
    });
    await navCheck('duplicate history events coalesce and late restored requests cannot change URL DOM or focus',async()=>{
      await go('#query=DMM6500&item_id=MOD-ce43da835609baea');await waitId('MOD-ce43da835609baea');await page.evaluate(()=>{window.catalogOriginalFetch=window.fetch;window.fetch=(url,options)=>window.catalogOriginalFetch(url,{...options,signal:undefined});});
      const old=await get('/api/control-sources?query=N9030A&offset=0&limit=25');let release,arrived;const waiting=new Promise(resolve=>arrived=resolve),hold=new Promise(resolve=>release=resolve);const routePattern=/\/api\/control-sources\?/;
      await page.route(routePattern,async route=>{if(new URL(route.request().url()).searchParams.get('query')==='N9030A'){arrived();await hold;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(old)});}else await route.continue();});
      await page.evaluate(()=>{location.hash='#query=N9030A&item_id=MOD-c40c6c5f1b4e7ca9';});await bounded(waiting,'late_navigation_request_not_observed');await page.evaluate(()=>{location.hash='#query=DMM6500&item_id=MOD-4e1a45a25496a054';});await waitId('MOD-4e1a45a25496a054');const retained=await page.locator('#detail').innerHTML(),currentHash=await hash(),active=await page.evaluate(()=>document.activeElement.id);const response=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/control-sources' && new URL(response.url()).searchParams.get('query')==='N9030A');release();await (await response).finished();await page.evaluate(()=>new Promise(requestAnimationFrame));assert.equal(await page.locator('#detail').innerHTML(),retained);assert.equal(await hash(),currentHash);assert.equal(await page.evaluate(()=>document.activeElement.id),active);assert.equal(active,'catalog-detail-heading');await page.unroute(routePattern);
      const count=listReads();await page.evaluate(()=>{dispatchEvent(new PopStateEvent('popstate'));dispatchEvent(new HashChangeEvent('hashchange'));});await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));assert.equal(listReads(),count);await page.evaluate(()=>{window.fetch=window.catalogOriginalFetch;delete window.catalogOriginalFetch;});
    });
    await navCheck('keyboard focus skip link mobile and storage boundaries survive restored reads',async()=>{
      await page.locator('#query').fill('N1921A');await page.locator('#scope').selectOption('');await page.locator('#query').focus();await page.keyboard.press('Enter');await settled();assert(await page.evaluate(()=>document.activeElement.matches('#items button') && document.activeElement.tabIndex===0));
      const beforeHash=await hash();await page.locator('.skip').focus();await page.keyboard.press('Enter');assert.equal(await hash(),beforeHash);assert.equal(await page.evaluate(()=>document.activeElement.id),'main');await page.setViewportSize({width:390,height:844});await page.locator('#items button').first().focus();await page.keyboard.press('Enter');await settled();const focus=await page.evaluate(()=>{const node=document.activeElement,box=node.getBoundingClientRect();return {id:node.id,top:box.top,bottom:box.bottom,height:innerHeight};});assert.equal(focus.id,'catalog-detail-heading');assert(focus.top>=0 && focus.bottom<=focus.height,JSON.stringify(focus));await page.screenshot({path:path.join(evidence,'NAV002-mobile-focus.png')});await page.evaluate(()=>scrollTo(0,0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(evidence,'NAV002-mobile-top.png')});await page.locator('#detail').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(evidence,'NAV002-mobile-detail.png')});assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length,state:history.state,query:location.search})),{local:0,session:0,state:null,query:''});
      assert(requests.filter(request=>['/control-sources','/control-sources/'].includes(new URL(request.url).pathname)).every(request=>new URL(request.url).search===''));assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert(requests.every(request=>request.method==='GET'));
    });
  }catch(error){failed=error;json(path.join(evidence,'private-error.json'),{message:String(error.stack || error)});}
  finally{
    try{if(browser)await browser.close();cleanup.browser_closed=true;}catch(error){failed ||= error;}
    try{if(child){if(child.exitCode===null && child.stdin.writable)child.stdin.end('stop\n');let timer;const stopped=await Promise.race([closed,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('owned_cleanup_timeout')),7000);})]).finally(()=>clearTimeout(timer));cleanup.producer_closed=stopped.code===0;const last=stdout.trim().split(/\r?\n/).at(-1);const record=JSON.parse(last);cleanup.server_closed=record.kind==='control_catalog_browser_stopped' && record.server_closed;result.database_after=record.database_after;result.database_unchanged=record.database_unchanged;assert(result.database_unchanged);assert(cleanup.producer_closed && cleanup.server_closed);}}catch(error){if(child && child.exitCode===null)child.kill();failed ||= error;}
    write(path.join(evidence,'producer-stdout.raw'),stdout);write(path.join(evidence,'producer-stderr.raw'),stderr);json(path.join(evidence,'http-requests.json'),requests);
    try{result.source_sha256_after=sourceHashes();assert.deepEqual(result.source_sha256_after,before);result.source_unchanged=true;}catch(error){failed ||= error;}
    result.javascript_errors=errors.length;result.external_requests=external.length;result.passed=!failed && checks.length===10 && navigationChecks.length===7 && errors.length===0 && external.length===0 && cleanup.browser_closed && cleanup.producer_closed && cleanup.server_closed && result.source_unchanged;json(path.join(evidence,'result.json'),result);
  }
  if(!result.passed)throw Error('control_catalog_browser_failed');console.log(JSON.stringify({kind:result.kind,passed:checks.length,navigation_passed:navigationChecks.length,evidence}));return result;
}
if(require.main===module)main().catch(error=>{console.error(JSON.stringify({error:['catalog_dependency_missing','invalid_configuration'].includes(error.message)?error.message:'control_catalog_browser_failed'}));process.exitCode=1;});
module.exports={main};
