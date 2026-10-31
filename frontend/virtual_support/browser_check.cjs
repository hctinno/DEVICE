/* Real pinned public catalog -> actual GET byte cache -> current Chromium DOM. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process'),{createHash}=require('node:crypto');
const {reserveEvidence}=require('../intake_fixture_browser_check.cjs');
const ROOT=path.resolve(__dirname,'../..'),sha=value=>createHash('sha256').update(value).digest('hex');
const write=(file,value)=>fs.writeFileSync(file,value,{flag:'wx'}),json=(file,value)=>write(file,JSON.stringify(value,null,2)+'\n');
const bounded=async(promise,code,milliseconds=15000)=>{let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error(code)),milliseconds);})]);}finally{clearTimeout(timer);}};
const BOOT=`import hashlib,importlib,json,sys,threading
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]).resolve(strict=True); evidence=Path(sys.argv[2]).resolve(strict=True)
sys.path.insert(0,str(root))
bindings={}
for name in ('labflow.ui_server','labflow.control_source_catalog','labflow.virtual_support_view'):
    module=importlib.import_module(name); expected=root/Path(*name.split('.')).with_suffix('.py')
    if Path(module.__file__).resolve()!=expected or Path(module.__spec__.origin).resolve()!=expected: raise ValueError('source_binding_mismatch')
    bindings[name]={'path':str(expected),'sha256':hashlib.sha256(expected.read_bytes()).hexdigest()}
from labflow.ui_server import create_server
import labflow.control_source_catalog as controls
import labflow.virtual_support_view as support
counts={'builder':0,'control_source_reads':0,'catalog_reads':0}
original_build=support.build_virtual_support_view; original_read=controls._read; original_catalog=support._catalog
def build(*args,**kwargs):
    counts['builder']+=1; return original_build(*args,**kwargs)
def read(*args,**kwargs):
    counts['control_source_reads']+=1; return original_read(*args,**kwargs)
def catalog(*args,**kwargs):
    counts['catalog_reads']+=1; return original_catalog(*args,**kwargs)
support.build_virtual_support_view=build; controls._read=read; support._catalog=catalog
workspace=evidence/'never-opened-store'
with patch('labflow.virtual_fleet.core.VirtualFleet.__init__',side_effect=AssertionError('fleet_forbidden')), patch('labflow.virtual_lab.VirtualLab.__init__',side_effect=AssertionError('lab_forbidden')):
    server=create_server(workspace,port=0); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        print(json.dumps({'kind':'virtual_support_ready','origin':'http://127.0.0.1:'+str(server.server_address[1]),'bindings':bindings,'initial_counts':dict(counts)}),flush=True)
        if sys.stdin.readline()!='stop\\n': raise ValueError('stop_required')
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        print(json.dumps({'kind':'virtual_support_stopped','server_closed':not thread.is_alive(),'workspace_created':workspace.exists(),'counts':counts}),flush=True)
`;

async function main(){
  if(process.argv.length>2)throw Error('invalid_configuration');
  const evidence=reserveEvidence(ROOT),checks=[],cleanup={browser_closed:false,producer_closed:false,server_closed:false};
  const result={kind:'virtual_support_actual_catalog_browser',actual_catalog_connected:false,contract_fixture:false,
    virtual_verification:'not_assessed',hardware_verified:false,execution_authority:false,checks,cleanup,passed:false};
  const sources=['labflow/ui_server.py','labflow/control_source_catalog.py','labflow/virtual_support_view.py',
    'virtual_profiles/sm_a176u_unlicensed.json','control_sources/registry_overlay.json','control_sources/source_url_index.json',
    'control_sources/prior_vendor_references.json','control_sources/review_notes.json',
    'research/equipment-control-2026-10-24/deliverables/model_control_sources.json','frontend/index.html','frontend/control_sources/styles.css',
    ...fs.readdirSync(__dirname).filter(name=>/\.(mjs|cjs|js|html)$/.test(name)).map(name=>'frontend/virtual_support/'+name)];
  const before=Object.fromEntries(sources.map(name=>[name,sha(fs.readFileSync(path.join(ROOT,name)))]));
  let child,browser,closed,readyResolve,readyReject,stdout='',stderr='',messages=[],exitResolve;
  const ready=new Promise((resolve,reject)=>{readyResolve=resolve;readyReject=reject;});
  try{
    closed=new Promise(resolve=>{exitResolve=resolve;});
    child=spawn(require('../managed_paths.cjs').python(ROOT),['-B','-X','utf8','-c',BOOT,ROOT,evidence],
      {cwd:ROOT,windowsHide:true,stdio:['pipe','pipe','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'}});
    result.producer_pid=child.pid;child.stdin.on('error',()=>{});child.stdout.setEncoding('utf8');child.stderr.setEncoding('utf8');
    child.on('error',()=>readyReject(Error('support_host_start_failed')));
    child.on('close',(code,signal)=>{exitResolve({code,signal});readyReject(Error('support_host_closed'));});
    child.stdout.on('data',chunk=>{
      stdout+=chunk.toString('utf8');if(Buffer.byteLength(stdout)>1048576){readyReject(Error('support_host_output_limit'));child.kill();return;}
      while(stdout.includes('\n')){const split=stdout.indexOf('\n'),line=stdout.slice(0,split);stdout=stdout.slice(split+1);try{const data=JSON.parse(line);messages.push(data);if(data.kind==='virtual_support_ready')readyResolve(data);}catch{readyReject(Error('support_host_output_invalid'));}}
    });
    child.stderr.on('data',chunk=>{if(Buffer.byteLength(stderr)<1048576)stderr+=chunk.toString('utf8');});
    const binding=await bounded(ready,'support_host_start_timeout');
    assert(/^http:\/\/127\.0\.0\.1:[0-9]+$/.test(binding.origin));
    for(const [name,item] of Object.entries(binding.bindings)){assert.equal(path.relative(path.join(ROOT,name.replaceAll('.','/')+'.py'),item.path),'');assert.equal(item.sha256,before[name.replaceAll('.','/')+'.py']);}
    assert.deepEqual(binding.initial_counts,{builder:0,control_source_reads:0,catalog_reads:0});result.source_binding=binding;
    const origin=binding.origin,response=await fetch(origin+'/api/virtual-support',{signal:AbortSignal.timeout(10000)});
    assert.equal(response.status,200);const wire=Buffer.from(await response.arrayBuffer());write(path.join(evidence,'actual-api.json'),wire);
    const dto=JSON.parse(wire.toString('utf8'));assert.equal(dto.profile_count,64);assert.equal(dto.adapter_contracts[0].commands.length,12);
    assert(dto.profiles.some(p=>p.model==='N1911A'));assert(!dto.profiles.some(p=>p.model==='N1914A'));
    assert.equal(dto.execution_authority,false);assert.equal(dto.hardware_verified,false);result.actual_catalog_connected=true;result.api_sha256=sha(wire);
    checks.push({name:'actual_fixed_catalog_api',profiles:64,separate_model:'N1914A',commands:12,passed:true});
    const {chromium}=require('playwright');browser=await chromium.launch({headless:true,executablePath:chromium.executablePath()});result.browser_version=browser.version();
    const context=await browser.newContext({viewport:{width:1440,height:1100}});context.setDefaultTimeout(7000);
    const external=[],errors=[];await context.route('**/*',route=>{if(new URL(route.request().url()).origin!==origin){external.push(route.request().url());return route.abort();}return route.continue();});
    const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
    await page.goto(origin+'/');await page.locator('a[href="/virtual-support"]').click();
    await page.locator('#status').filter({hasText:'조회 완료'}).waitFor();assert.equal(await page.locator('#profiles button').count(),64);
    checks.push({name:'operational_navigation_to_actual_support_dom',passed:true});
    const select=async row=>{await page.locator('#search').fill(row.profile_id);await page.locator(`#profiles button[data-profile-id="${row.profile_id}"]`).click();assert.equal(await page.locator('#detail').getAttribute('data-profile-id'),row.profile_id);};
    const meter=dto.profiles.find(p=>p.model==='N1911A');await select(meter);
    const text=await page.locator('#detail').innerText();assert(text.includes('N1911A'));assert(text.includes('acquire'));assert(text.includes('not_assessed'));assert(text.includes('설치 장비 결박 미확정'));assert(!text.includes('N1914A'));
    await page.screenshot({path:path.join(evidence,'support-n1911a.png')});checks.push({name:'exact_n1911a_role_declaration_and_unknown_protocol',passed:true});
    const unknown=dto.profiles.find(p=>p.materials.candidate_status==='no_text_candidate');await select(unknown);assert((await page.locator('#detail').innerText()).includes('직접 텍스트 후보 없음'));
    const acquired=dto.profiles.find(p=>p.materials.candidates.some(c=>c.sources.some(s=>s.access==='download_read')));await select(acquired);assert((await page.locator('#detail').innerText()).includes('내려받은 원문 열람'));
    const links=await page.locator('#detail a.source-url').evaluateAll(nodes=>nodes.map(node=>({href:node.getAttribute('href'),rel:node.rel})));
    assert(links.length>0 && links.every(link=>/^https?:\/\//.test(link.href) && link.rel.includes('noreferrer')));checks.push({name:'actual_material_unknown_and_acquisition_states_safe_links',passed:true});
    assert.equal(await page.locator('#protocol-commands li').count(),12);
    for(const status of ['declared','unsupported','unknown'])assert((await page.locator(`#contracts [data-support="${status}"]`).innerText()).length>0);
    assert((await page.locator('#contracts').innerText()).includes('N1911A 카탈로그 프로필과 다른 모델'));
    await page.locator('#adapter-contracts').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(evidence,'support-n1914a-contract.png')});
    checks.push({name:'separate_contract_declared_outside_scope_unknown',passed:true});
    await page.locator('#reload').click();await page.locator('#status').filter({hasText:'조회 완료'}).waitFor();
    const again=await fetch(origin+'/api/virtual-support',{signal:AbortSignal.timeout(10000)});assert.equal(sha(Buffer.from(await again.arrayBuffer())),sha(wire));
    assert((await page.locator('#metrics').innerText()).includes('64'));assert((await page.locator('#provenance').innerText()).includes('실행 feature 코드 버전과 별개'));
    checks.push({name:'repeat_get_and_reload_keep_exact_host_snapshot',passed:true});
    await page.setViewportSize({width:390,height:900});await page.locator('#search').fill(meter.profile_id);
    result.mobile=await page.evaluate(()=>({viewport:window.innerWidth,document_width:document.documentElement.scrollWidth}));
    await page.screenshot({path:path.join(evidence,'support-mobile.png')});assert(result.mobile.document_width<=result.mobile.viewport+1);
    checks.push({name:'mobile_no_horizontal_overflow',passed:true});
    await page.route('**/api/virtual-support',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":{"code":"virtual_support_unavailable"}}'}));
    await page.locator('#reload').click();await page.locator('#status').filter({hasText:'조회할 수 없습니다'}).waitFor();
    assert.equal(await page.locator('#profiles button').count(),0);assert.equal(await page.locator('#contracts').innerText(),'');assert.equal(await page.locator('#metrics').innerText(),'');
    checks.push({name:'authored_503_ui_failure_clears_previous_snapshot',actual_catalog_positive_checks_above:true,passed:true});
    assert.deepEqual(external,[]);assert.deepEqual(errors,[]);result.external_requests=external;result.page_errors=errors;
    result.passed=true;
  }finally{
    if(browser){await browser.close();cleanup.browser_closed=true;}
    if(child){child.stdin.end('stop\n');let outcome;try{outcome=await bounded(closed,'support_host_stop_timeout',10000);}catch(error){child.kill();outcome=await bounded(closed,'support_host_kill_timeout',5000);result.cleanup_error=error.message;}
      cleanup.producer_closed=outcome.code===0;cleanup.exit=outcome;const stop=messages.find(message=>message.kind==='virtual_support_stopped');cleanup.server_closed=Boolean(stop?.server_closed);result.host_final=stop;}
    write(path.join(evidence,'host-stderr.txt'),stderr);json(path.join(evidence,'host-messages.json'),messages);
    const after=Object.fromEntries(sources.map(name=>[name,sha(fs.readFileSync(path.join(ROOT,name)))]));result.source_unchanged=JSON.stringify(before)===JSON.stringify(after);json(path.join(evidence,'source-sha.json'),{before,after});
    result.passed=result.passed && result.source_unchanged && cleanup.browser_closed && cleanup.producer_closed && cleanup.server_closed
      && result.host_final.workspace_created===false && JSON.stringify(result.host_final.counts)===JSON.stringify({builder:1,control_source_reads:5,catalog_reads:1});
    json(path.join(evidence,'browser-results.json'),result);console.log(JSON.stringify({evidence,passed:result.passed,checks:checks.length,cleanup}));
  }
  assert.equal(result.passed,true);
}
if(require.main===module)main().catch(error=>{console.error(error.message);process.exitCode=1;});
