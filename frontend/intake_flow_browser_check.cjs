/* UI acceptance modes. Fresh authored-MOCK generation requires explicit opt-in. */
const assert = require('node:assert/strict');
const {spawn,spawnSync} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const ROOT=path.resolve(__dirname,'..'),LOCAL=path.join(ROOT,'.local');
fs.mkdirSync(LOCAL,{recursive:true});
const proof=process.env.VLAB_FLOW_PROOF_ROOT?fs.realpathSync(process.env.VLAB_FLOW_PROOF_ROOT):LOCAL;
assert.ok(proof===LOCAL||proof.startsWith(LOCAL+path.sep));
const OUTPUT=fs.mkdtempSync(path.join(proof,process.env.VLAB_FRESH_CONDUCTED_OPERATOR_ONLY==='1'?'fresh-conducted-operator-':process.env.VLAB_ARTIFACT_STORAGE_KEYBOARD_ONLY==='1'?'artifact-storage-keyboard-':process.env.VLAB_ARTIFACT_STORAGE_VIEW_ONLY==='1'?'artifact-storage-browser-':process.env.VLAB_UNIFIED_PROVIDED_FLOW_ONLY==='1'?'unified-provided-browser-':process.env.VLAB_GAP_QUEUE_ONLY==='1'?'gap-queue-browser-':process.env.VLAB_CONDUCTED_RESULT_ONLY==='1'?'conducted-result-browser-':process.env.VLAB_CONDUCTED_PREVIEW_ONLY==='1'?'conducted-preview-browser-':'first-twin-browser-'));
const PROOF=proof===LOCAL?OUTPUT:proof;
const FRESH_OUTPUT_ROOTS=[];
function proofWrite(file,data){
  const target=path.resolve(file);assert.ok(target.startsWith(PROOF+path.sep));const files=[];
  const walk=dir=>{for(const entry of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(entry.isSymbolicLink(),false);const p=path.join(dir,entry.name);if(entry.isDirectory())walk(p);else if(entry.isFile())files.push(p);}};walk(PROOF);for(const root of FRESH_OUTPUT_ROOTS)if(fs.existsSync(root))walk(root);
  assert.ok(files.length+(fs.existsSync(target)?0:1)<=512);
  assert.ok(files.reduce((sum,p)=>sum+fs.statSync(p).size,0)-(fs.existsSync(target)?fs.statSync(target).size:0)+Buffer.byteLength(data)<=33554432);
  fs.writeFileSync(target,data);
}
async function screenshot(page,file){proofWrite(file,await page.screenshot({fullPage:false}));}

async function main() {
  const root = path.resolve(__dirname, '..');
  const output = OUTPUT;
  const python = process.env.VLAB_PYTHON || path.join(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  // Copy only this public test helper's code, keeping its disposable stores in
  // native temp and closing it over stdin; never reuse its old fixed proof path.
  const helper=fs.readFileSync(path.join(root,'frontend/intake_flow_browser_fixture.py'),'utf8')
    .replace("Path('.local/FLOW-003-IMPLEMENTATION').resolve()",'Path(tempfile.gettempdir())')
    .replace("Path(__file__).resolve().parents[1] / 'tests'",'Path('+JSON.stringify(root.replaceAll('\\','/'))+") / 'tests'")
    .replace("threading.Event().wait()",'sys.stdin.readline()')
    .replace('thread.join(timeout=3)','thread.join(timeout=3)\n                server.server_close()\n                assert not thread.is_alive() and server.socket.fileno()==-1');
  const helperPath=path.join(output,'legacy_host.py');proofWrite(helperPath,helper);
  const child = spawn(python, ['-B', helperPath, '--port', '0'], {
    cwd:root, windowsHide:true, env:{...process.env,PYTHONPATH:root,PYTHONUTF8:'1', PYTHONIOENCODING:'utf-8'}, stdio:['pipe','pipe','pipe'],
  });
  const exited=new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal})));
  let browser,log='';
  try {
    const {origin, empty_origin} = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('fixture startup timeout: '+log)), 15000);
      child.once('error', error => {clearTimeout(timer); reject(error);});
      child.once('exit', code => {clearTimeout(timer); reject(new Error('fixture exit '+code+': '+log));});
      child.stderr.on('data', chunk => {log += chunk;});
      child.stdout.on('data', chunk => {
        log += chunk;
        const line = log.split(/\r?\n/).find(text => text.startsWith('{"origin":'));
        if (line) {clearTimeout(timer); resolve(JSON.parse(line));}
      });
    });
    browser = await chromium.launch({headless:true});
    const context = await browser.newContext({viewport:{width:1512,height:1100}});
    context.setDefaultTimeout(5000);
    const errors = [], external = [], methods = [];
    context.on('page', page => {
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => {
        if (!request.url().startsWith(origin+'/') && !request.url().startsWith(empty_origin+'/')) external.push(request.url());
        if (request.url().includes('/api/')) methods.push(request.method());
      });
    });
    const snapshot = await (await context.request.get(origin+'/api/intakes')).json();
    const intake = snapshot.intakes[0], other = snapshot.intakes[1];
    const route = `/api/intakes/${intake.intake_id}/fixture-runs`;
    const original = await (await context.request.get(origin+route)).json();
    const loaded = async page => {
      await page.locator('#fixture-status').filter({hasText:'가상 기록 조회 완료'}).waitFor();
      await page.waitForFunction(()=>!document.querySelector('#conducted-plan-refresh')||document.querySelector('#conducted-plan-refresh').getAttribute('aria-disabled')==='false');
    };
    const refreshIntakes = async page => {
      await page.locator('#refresh').click();
      await page.waitForFunction(() => !document.querySelector('#refresh').disabled);
    };
    const contentState = async page => ({body:createHash('sha256').update(await page.locator('#fixture-records').innerHTML()).digest('hex'),
      time:await page.locator('#fixture-updated').innerText(), selected:await page.locator('.fixture-request[aria-pressed=true]').getAttribute('data-request-id')});
    const checks = [];
    const check = async (name, run) => {await run(); checks.push(name); console.log('PASS '+name);};
    const page = await context.newPage();
    await page.goto(origin);
    await check('actual GET shows recent20 current and changed-readiness records with separate result semantics', async () => {
      await loaded(page);
      assert.equal(await page.locator('.fixture-request').count(), 20);
      const text = await page.locator('#fixture-panel').innerText();
      assert.match(text, /최신 20건/); assert.match(text, /준비 상태 변경 기록/);
      assert.match(text, /현재 자료·준비 상태/); assert.match(text, /실행 기록 저장/);
      assert.match(text, /독립 평가 미실행/); assert.match(text, /정책의 완료 주장/);
      assert.match(text, /작업 결과 미평가/); assert.match(text, /실제 AI 호출 없음/);
      assert.equal(await page.locator('#fixture-panel input, #fixture-panel select, #fixture-panel a').count(), 0);
    });
    await check('malformed V1 citation snapshots preserve the successful DOM intake request selection and times', async () => {
      const good=structuredClone(snapshot); good.intakes[0].bundle='LAST_GOOD';
      await page.route('**/api/intakes',handler=>handler.fulfill({json:good}));
      await refreshIntakes(page); await loaded(page);
      await page.locator('.fixture-request').nth(1).click();
      const view=async()=>({detail:createHash('sha256').update(await page.locator('#detail-panel').innerHTML()).digest('hex'),
        intake:await page.locator('.intake-item[aria-current]').innerText(),time:await page.locator('#last-updated').innerText(),flow:await contentState(page)});
      const before=await view();
      await page.unroute('**/api/intakes');
      for (const change of [()=>({}),s=>({...s,sha256:'bad'}),s=>({...s,line_start:4,line_end:2}),
        s=>({...s,role:'future'}),s=>({...s,seed:0}),s=>{delete s.quote;return s;}]) {
        const bad=structuredClone(good); bad.intakes[0].bundle='MALFORMED_V1_REPLACEMENT'; bad.generated_at='2026-10-24T23:59:00Z';
        const fact=bad.intakes[0].analysis.submitted.facts[0]; fact.evidence[0]=change(fact.evidence[0]);
        await page.route('**/api/intakes',handler=>handler.fulfill({json:bad}));
        await refreshIntakes(page);
        await page.locator('#error-banner').filter({hasText:'조회 실패'}).waitFor();
        assert.deepEqual(await view(),before);
        assert.equal(await page.getByRole('heading',{name:'MALFORMED_V1_REPLACEMENT',exact:true}).count(),0);
        await page.unroute('**/api/intakes');
      }
      await refreshIntakes(page); await loaded(page);
      assert.equal(await page.locator('#error-banner').isHidden(),true);
    });
    await check('record selection is local and scoped to request identity', async () => {
      await page.locator('.fixture-request').nth(1).click();
      assert.match(await page.locator('#fixture-result').innerText(), /FIXTURE-21/);
      assert.equal(await page.locator('.fixture-request[aria-pressed=true]').getAttribute('data-request-id'), 'FIXTURE-21');
      await page.locator('#fixture-refresh').click(); await loaded(page);
      assert.equal(await page.locator('.fixture-request[aria-pressed=true]').getAttribute('data-request-id'), 'FIXTURE-21');
    });
    await check('read failure and invalid cross binding keep successful content selection and time', async () => {
      const before = await contentState(page);
      for (const payload of [{error:{code:'unavailable'}}, {...original, intake_id:other.intake_id},
        {...original, current_revision:2}, (() => {const p=structuredClone(original); p.records[0].report.run_id='other'; return p;})(),
        (() => {const p=structuredClone(original); p.records[0].report.policy.seed=1; return p;})()]) {
        await page.route('**'+route, handler => handler.fulfill({status:payload.error ? 503:200, json:payload}));
        await page.locator('#fixture-refresh').click();
        await page.locator('#fixture-status').filter({hasText:'마지막 성공 기록 유지'}).waitFor();
        assert.deepEqual(await contentState(page), before);
        await page.unroute('**'+route);
      }
    });
    await check('renderer failure preserves record body selection and timestamp', async () => {
      const before = await contentState(page);
      await page.evaluate(() => {
        const original = document.createElement.bind(document);
        document.createElement = (...args) => {if (args[0] === 'h4') {document.createElement=original; throw new Error('synthetic renderer failure');} return original(...args);};
      });
      await page.locator('#fixture-refresh').click();
      await page.locator('#fixture-status').filter({hasText:'마지막 성공 기록 유지'}).waitFor();
      assert.deepEqual(await contentState(page), before);
      await page.locator('#fixture-refresh').click(); await loaded(page);
    });
    await check('selection changes fence delayed responses even when transport ignores abort', async () => {
      let release, arrived;
      const wait = new Promise(resolve => {release=resolve;});
      const seen = new Promise(resolve => {arrived=resolve;});
      await page.evaluate(() => {
        window.fixtureFetch = window.fetch;
        window.fetch = (url, options) => window.fixtureFetch(url, String(url).endsWith('/fixture-runs') ? {...options,signal:undefined}:options);
      });
      await page.route('**'+route, async handler => {arrived(); await wait; const p=structuredClone(original); p.records[0].report.usage.decisions++; await handler.fulfill({json:p});});
      await page.locator('#fixture-refresh').click(); await seen;
      await page.locator('.fixture-request').nth(2).click();
      const before = await contentState(page);
      release(); await page.waitForTimeout(100);
      assert.deepEqual(await contentState(page), before);
      await page.unroute('**'+route);
    });
    await check('different intake clears previous records and late old intake cannot repaint it', async () => {
      let release, arrived;
      const wait = new Promise(resolve => {release=resolve;});
      const seen = new Promise(resolve => {arrived=resolve;});
      await page.route('**'+route, async handler => {arrived(); await wait; await handler.fulfill({json:original});});
      await page.locator('#fixture-refresh').click(); await seen;
      await page.locator('.intake-item').nth(1).click(); await loaded(page);
      assert.equal(await page.locator('.fixture-request').count(), 0);
      release(); await page.waitForTimeout(100);
      assert.match(await page.locator('#fixture-records').innerText(), /가상 실행 기록이 없습니다/);
      assert.equal(await page.locator('#fixture-result').count(), 0);
      await page.unroute('**'+route);
      await page.locator('.intake-item').first().click(); await loaded(page);
    });
    await check('available empty legacy unavailable and initial error remain distinct', async () => {
      for (const [payload, status, label] of [
        [{...original,records:[],more_available:false},200,'저장된 가상 실행 기록이 없습니다'],
        [{...original,storage_available:false,records:[],more_available:false},200,'이전 저장소'],
        [{error:{code:'state_invalid'}},503,'기록 조회 불가'],
      ]) {
        const sample = await context.newPage();
        await sample.route('**'+route, handler => handler.fulfill({status,json:payload}));
        await sample.goto(origin);
        await sample.locator('#fixture-panel').filter({hasText:label}).waitFor();
        assert.equal(await sample.locator('#fixture-result').count(),0);
        await sample.close();
      }
    });
    await check('technical failure uncertainty and independent virtual pass never become physical measurement success', async () => {
      for (const [state,label] of [['queued','가상 실행 대기'],['running','가상 실행 중'],['failed','가상 작업 실패'],
        ['uncertain','실행·게시 여부 확인 필요'],['superseded','이전 준비 상태로 종료'],['completed','가상 시나리오 평가 통과']]) {
        const payload=structuredClone(original); payload.records=payload.records.slice(0,1); payload.more_available=false;
        const record=payload.records[0]; record.state=state;
        if (state !== 'completed') record.report=null;
        else {
          record.report.termination={reason:'policy_stop',policy_claim:'blocked'};
          record.report.assessment={status:'completed',verdict:'pass',evaluator_id:'fixture:evaluator',evidence_refs:[],summary_code:'fixture_blocked_as_expected'};
        }
        if (state === 'queued') {record.run_id=null;record.runtime_instance_id=null;}
        const sample=await context.newPage();
        await sample.route('**'+route,handler=>handler.fulfill({json:payload}));
        await sample.goto(origin); await loaded(sample);
        const text=await sample.locator('#fixture-result').innerText();
        assert.match(text,new RegExp(label)); assert.doesNotMatch(text,/측정 완료|FCC 합격/);
        if (state === 'completed') {assert.match(text,/진행 불가 주장/);assert.match(text,/작업 결과 미평가/);}
        else assert.match(text,/게시된 공개 결과가 없습니다/);
        await sample.close();
      }
    });
    await check('past revision and PDF V2 citation coordinates context extraction and literal XSS are preserved', async () => {
      const next = structuredClone(snapshot), p = structuredClone(original);
      next.intakes[0].revision = 2; p.current_revision=2; p.records.forEach(record => {record.source_current=false;});
      const submitted = next.intakes[0].analysis.submitted;
      Object.assign(submitted,{schema_version:2,context_id:'context:synthetic-page'});
      for (const fact of submitted.facts) for (const citation of fact.evidence) citation.kind='text_line';
      const citation = submitted.facts[0].evidence[0];
      Object.assign(citation,{kind:'pdf_page',path:'합성 인용.pdf',extraction_id:'extract:synthetic-page',page_number:2,text_sha256:'b'.repeat(64),
        line_start:3,line_end:4,quote:'<img src=x onerror="window.fixtureXss=true"> synthetic page quote'});
      await page.route('**/api/intakes', handler => handler.fulfill({json:next}));
      await page.route('**'+route, handler => handler.fulfill({json:p}));
      await refreshIntakes(page); await loaded(page);
      assert.match(await page.locator('#fixture-result').innerText(), /이전 자료 버전 v1 · 현재 v2/);
      await page.locator('.fact details summary').first().click();
      await page.getByText('PDF 2쪽 · 페이지 안 3–4행', {exact:false}).first().waitFor();
      assert.match(await page.locator('#detail-panel').innerText(), /context:synthetic-page/);
      assert.match(await page.locator('#detail-panel').innerText(), /extract:synthetic-page/);
      assert.equal(await page.locator('#detail-panel img, #detail-panel script').count(),0);
      assert.equal(await page.evaluate(() => window.fixtureXss),undefined);
      await screenshot(page,path.join(output,'intake-flow-desktop.png'));
      await page.unroute('**/api/intakes'); await page.unroute('**'+route);
    });
    await check('revision change fences old response and fresh GET uses the selected current revision', async () => {
      let release, arrived;
      const wait = new Promise(resolve => {release=resolve;});
      const seen = new Promise(resolve => {arrived=resolve;});
      let first=true;
      await page.route('**'+route, async handler => {
        if (!first) return handler.continue();
        first=false; arrived(); await wait; await handler.fulfill({json:{...original,current_revision:2}});
      });
      await page.locator('#fixture-refresh').click(); await seen;
      // Refresh back to the unchanged actual R1 fixture while the old R2 request waits.
      await refreshIntakes(page); await loaded(page);
      const before=await contentState(page);
      release(); await page.waitForTimeout(100);
      assert.deepEqual(await contentState(page),before);
      await page.unroute('**'+route);
    });
    await check('same revision snapshot refresh retains stale records explicitly until readiness reread', async () => {
      await page.route('**'+route, handler => handler.fulfill({status:503,json:{error:{code:'unavailable'}}}));
      const before=await contentState(page);
      await refreshIntakes(page);
      await page.locator('#fixture-status').filter({hasText:'마지막 성공 기록 유지'}).waitFor();
      assert.equal(await page.locator('#fixture-updated').innerText(),before.time);
      assert.match(await page.locator('#fixture-result').innerText(), /현재 관계 미확인/);
      await page.unroute('**'+route);
      await page.locator('#fixture-refresh').click(); await loaded(page);
    });
    await check('mobile layout and public refs stay literal with no active run controls', async () => {
      const payload=structuredClone(original);
      payload.records[0].report.policy.id='<img src=x onerror="window.fixtureXss=true">';
      payload.records[0].report.evidence.measurement_refs=['event:<img src=x onerror="window.fixtureXss=true">'];
      const sample=await context.newPage();
      await sample.route('**'+route,handler=>handler.fulfill({json:payload}));
      await sample.goto(origin); await loaded(sample);
      await sample.setViewportSize({width:390,height:844});
      await sample.locator('#fixture-panel').scrollIntoViewIfNeeded();
      assert.equal(await sample.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth),true);
      assert.equal(await sample.locator('#fixture-panel img, #fixture-panel script, #fixture-panel a').count(),0);
      assert.equal(await sample.evaluate(()=>window.fixtureXss),undefined);
      const labels=await sample.locator('#fixture-panel button').allTextContents();
      assert.equal(labels.some(text=>/시작|중지|재개|업로드/.test(text)),false);
      await screenshot(sample,path.join(output,'intake-flow-mobile.png'));
      await sample.close();
    });
    if(process.env.VLAB_EXISTING_NINE==='1') { // Optional unrelated legacy suite.
      const isolated=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'intake-nine-'));
      const result=await new Promise((resolve,reject)=>{
        const legacy=spawn(process.execPath,[path.join(root,'frontend/browser_check.cjs')],{cwd:isolated,windowsHide:true,env:{...process.env,UI_DEMO_URL:origin,UI_EMPTY_URL:empty_origin},stdio:['ignore','pipe','pipe']});
        let text=''; legacy.stdout.on('data',chunk=>{text+=chunk;}); legacy.stderr.on('data',chunk=>{text+=chunk;});
        legacy.on('error',reject); legacy.on('exit',code=>resolve({code,text}));
      });
      proofWrite(path.join(output,'existing-browser.log'),result.text);
      assert.equal(result.code,0,result.text);
      console.log('PASS existing intake browser acceptance: 9 checks');
    }
    assert.deepEqual(errors,[]); assert.deepEqual(external,[]); assert(methods.every(method=>method==='GET'));
    proofWrite(path.join(output,'browser-results.json'),JSON.stringify({passed:checks.length,optionalLegacyNine:process.env.VLAB_EXISTING_NINE==='1'?'pass':'not_run',checks,pageErrors:errors,externalRequests:external,methods:[...new Set(methods)]},null,2));
    console.log(JSON.stringify({passed:checks.length,evidence:output}));
  } finally {if (browser) await browser.close();child.stdin.end('stop\n');let timer;const result=await Promise.race([exited,new Promise((_,reject)=>{timer=setTimeout(()=>{child.kill();reject(Error('legacy host close timeout'));},10000);})]);clearTimeout(timer);assert.equal(result.code,0,log);}
}

const workflowHost=String.raw`
import json,sys,tempfile,threading,socket,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from labflow.intake_fixture_check import run_fixture_flow
from labflow.ui_server import create_server
from labflow.store import Store
from labflow.intake_jobs import respond
from labflow.active_intake import scan_source
def main():
 mode=sys.argv[2]
 with tempfile.TemporaryDirectory(prefix='first-twin-workflow-') as tmp:
  if mode=='demo':
   from frontend.demo_fixture import build_demo
   workspace=build_demo(Path(tmp)/'demo');summary=None
  else:
   flow=run_fixture_flow(Path(tmp)/'genuine',power_dbm=-4,document_kind=mode)
   workspace=flow['workspace'];summary=flow['summary']
  server=create_server(workspace,port=0)
  thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
  print(json.dumps({'origin':'http://127.0.0.1:'+str(server.server_port),'summary':summary,'mode':mode}),flush=True)
  try:
   for line in sys.stdin:
    cmd=line.strip()
    if cmd=='stop':break
    if cmd=='defer':respond(Store(workspace),'VIEW-HOLD','defer',intake_id=summary['intake_id'])
    elif cmd=='revise':
     source=Path(tmp)/'genuine/inbox/fixture-request/request.txt'
     source.write_text(source.read_text(encoding='utf-8')+'firmware: synthetic revision 2\n',encoding='utf-8')
     store=Store(workspace);now=time.time();scan_source(store,'FLOW-INBOX',now=now);scan_source(store,'FLOW-INBOX',now=now+.01)
    else:raise ValueError('unknown_test_control')
    print(json.dumps({'control':cmd}),flush=True)
  finally:
   address=server.server_address;server.shutdown();server.server_close();thread.join(5)
   assert not thread.is_alive() and server.socket.fileno()==-1
   with socket.socket() as probe:probe.bind(address)
   print(json.dumps({'resource':{'loop_stopped':not thread.is_alive(),'listener_closed':server.socket.fileno()==-1,'port_rebind':True,'actual_model_calls':0,'hardware_calls':0}}),flush=True)
if __name__=='__main__':main()
`;
function startWorkflowHost(mode){
  const file=path.join(OUTPUT,'workflow_host.py');if(!fs.existsSync(file))proofWrite(file,workflowHost);
  const python=process.env.VLAB_PYTHON||path.join(ROOT,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
  const child=spawn(python,['-B','-X','utf8',file,ROOT,mode],{cwd:ROOT,windowsHide:true,stdio:['pipe','pipe','pipe']});
  let pending='',stderr='';const queue=[],waiters=[];
  child.stdout.on('data',b=>{pending+=b.toString();while(pending.includes('\n')){const i=pending.indexOf('\n'),line=pending.slice(0,i);pending=pending.slice(i+1);const item=JSON.parse(line);if(waiters.length)waiters.shift()(item);else queue.push(item);}});
  child.stderr.on('data',b=>{stderr+=b.toString();if(stderr.length>8192)child.kill();});
  const exited=new Promise(resolve=>child.once('exit',code=>resolve(code)));
  const next=()=>new Promise((resolve,reject)=>{if(queue.length)return resolve(queue.shift());const timer=setTimeout(()=>reject(Error('workflow host timeout: '+stderr)),20000);waiters.push(item=>{clearTimeout(timer);resolve(item);});});
  return {child,next,exited,stderr:()=>stderr,command:async cmd=>{child.stdin.write(cmd+'\n');const value=await next();assert.equal(value.control,cmd);}};
}
async function workflowMain(){
  const checks=[],faults=[],resources=[];let browser;
  try{
    browser=await chromium.launch({headless:true});
    for(const mode of ['text','pdf','demo']){
      const host=startWorkflowHost(mode);let info;
      try{
        info=await host.next();assert.ok(info.origin);if(mode!=='demo'){assert.equal(info.summary.fixture_acceptance,'pass');assert.equal(info.summary.ai_model_called,false);}
        const observe=async(width,phase='normal')=>{
          const context=await browser.newContext({viewport:{width,height:900}}),errors=[],external=[],methods=[];
          const page=await context.newPage();page.setDefaultTimeout(5000);page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/'))methods.push(r.method());});
          try{
            await page.goto(info.origin+(info.summary?'/#'+info.summary.intake_id:'/'));
            await page.locator('#fixture-status').filter({hasText:'가상 기록 조회 완료'}).waitFor();
            const workflow=page.locator('#intake-workflow');await workflow.waitFor();assert.equal(await workflow.locator('[data-workflow-step]').count(),7);
            const text=await workflow.innerText();for(const missing of ['시험계획 미연결','원수치/단위·기준면 미제공','규격 판정 미실행','실측 대조 미실행','물리 정확도 미검증'])assert.ok(text.includes(missing));
            assert.equal(await workflow.locator('input,select,a').count(),0);
            assert.deepEqual(await workflow.locator('button').evaluateAll(nodes=>nodes.map(node=>node.id)),['conducted-plan-refresh']);
            assert.doesNotMatch(text,/FCC PASS|전체 업무 완료|실측 완료/);
            if(mode==='demo')assert.match(text,/시장 충돌|conflict_market/);
            else{
              if(phase==='revise')assert.ok(text.includes('자료 미확인'));
              else assert.ok(text.includes('smartphone')&&text.includes('US')&&text.includes('synthetic fixture acceptance'));
              assert.ok(text.includes('실행 기록 저장')&&text.includes('가상 시나리오 평가 통과')&&text.includes('작업 결과 미평가'));
              const snapshot=await(await context.request.get(info.origin+'/api/intakes')).json();const intake=snapshot.intakes.find(i=>i.intake_id===info.summary.intake_id);
              assert.equal(await workflow.getAttribute('data-intake-id'),intake.intake_id);assert.equal(await workflow.getAttribute('data-revision'),String(intake.revision));
              const records=await(await context.request.get(info.origin+`/api/intakes/${intake.intake_id}/fixture-runs`)).json(),selected=records.records[0];
              assert.ok(text.includes(selected.request_id)&&text.includes(selected.readiness_fingerprint)&&text.includes(selected.run_id));
              const revision=intake.history.find(item=>item.revision===intake.revision);assert.ok(text.includes(revision.fingerprint));
              const refs=workflow.locator('[data-workflow-step="measurement"] summary');await refs.focus();await page.keyboard.press('Enter');
              assert.ok((await workflow.innerText()).includes(selected.report.evidence.measurement_refs[0]));
              if(phase==='normal')assert.equal(await workflow.getAttribute('data-fixture-scope'),'current');
              else{assert.equal(await workflow.getAttribute('data-fixture-scope'),'historical');assert.match(text,phase==='defer'?/준비 상태 변경/:/이전 자료 버전 v1/);}
              if(mode==='pdf'){
                await page.locator('.fact details summary').first().click();assert.match(await page.locator('#detail-panel').innerText(),/PDF 1쪽|PDF 2쪽/);
              }
              if(phase==='normal'&&mode==='text'){
                const endpoint=info.origin+`/api/intakes/${intake.intake_id}/fixture-runs`,original=await(await context.request.get(endpoint)).json();
                await page.route(endpoint,r=>r.fulfill({status:503,json:{error:{code:'unavailable'}}}));
                await page.locator('#fixture-refresh').click();await page.locator('#fixture-status').filter({hasText:'마지막 성공 기록 유지'}).waitFor();
                assert.equal(await workflow.getAttribute('data-fixture-scope'),'unconfirmed');assert.ok((await workflow.innerText()).includes('현재 관계 미확인'));await page.unroute(endpoint);
                faults.push({width,case:'HTTP503-last-good',scope:'typed transport failure after genuine successful GET'});
                for(const state of ['failed','uncertain']){
                  const sample=await context.newPage(),payload=structuredClone(original);payload.records[0].state=state;payload.records[0].report=null;
                  await sample.route(endpoint,r=>r.fulfill({json:payload}));await sample.goto(info.origin+'/#'+intake.intake_id);await sample.locator('#fixture-status').filter({hasText:'가상 기록 조회 완료'}).waitFor();
                  const observed=await sample.locator('#intake-workflow').innerText();assert.ok(observed.includes(state==='failed'?'가상 작업 실패':'실행·게시 여부 확인 필요'));assert.ok(observed.includes('게시된 측정 근거 미확인')&&observed.includes('규격 판정 미실행'));
                  await sample.close();faults.push({width,case:state,scope:'typed technical-state overlay, not a genuine runtime execution'});
                }
                const sample=await context.newPage(),unsupported=structuredClone(snapshot);unsupported.intakes.find(i=>i.intake_id===intake.intake_id).status='future';
                await sample.route('**/api/intakes',r=>r.fulfill({json:unsupported}));await sample.goto(info.origin+'/#'+intake.intake_id);await sample.locator('#intake-workflow').filter({hasText:'지원 미확인 상태'}).waitFor();await sample.close();
                faults.push({width,case:'unsupported',scope:'typed unsupported intake state; never marked complete'});
                const empty=await context.newPage();let reads=0;
                await empty.route(endpoint,r=>r.fulfill(++reads===1?{json:{...original,records:[],more_available:false}}:{status:503,json:{error:{code:'unavailable'}}}));
                await empty.goto(info.origin+'/#'+intake.intake_id);await empty.locator('#fixture-status').filter({hasText:'가상 기록 조회 완료'}).waitFor();
                await empty.locator('#fixture-refresh').click();await empty.locator('#fixture-status').filter({hasText:'마지막 성공 기록 유지'}).waitFor();
                assert.equal(await empty.locator('#intake-workflow').getAttribute('data-fixture-scope'),'none','an empty last-good response is not a selected historical execution');
                assert.ok((await empty.locator('#workflow-observation').innerText()).includes('가상 기록 미확인'));await empty.close();
                faults.push({width,case:'empty-last-good-failure',scope:'typed empty record set and HTTP failure; no execution identity invented'});
              }
            }
            assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(method=>method==='GET'));
            if(phase==='normal'&&mode!=='demo'){await workflow.scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,mode+'-'+width+'.png'));}
            checks.push({mode,width,phase,scope:mode==='demo'?'genuine synthetic intake API; no fixture execution':'genuine run_fixture_flow -> actual protected GET -> production DOM; one producer execution per document kind'});
          }finally{await context.close();}
        };
        for(const width of [390,1440])await observe(width);
        if(mode==='text')for(const command of ['defer','revise']){await host.command(command);for(const width of [390,1440])await observe(width,command);}
      }finally{
        host.child.stdin.end('stop\n');const stopped=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');
        assert.ok(stopped.resource?.loop_stopped&&stopped.resource.listener_closed&&stopped.resource.port_rebind);resources.push({mode,...stopped.resource,child_exit:code});
      }
    }
    proofWrite(path.join(OUTPUT,'workflow-results.json'),JSON.stringify({status:'pass',checks,typed_faults:faults,resources,actual_model_calls:0,hardware_calls:0},null,2));
    console.log(JSON.stringify({status:'pass',workflow_checks:checks.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'workflow-failure.json'),JSON.stringify({status:'fail',message:error.message,checks,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}
const previewHost=String.raw`
import json,sys,tempfile,threading,socket,hashlib
from pathlib import Path
sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'tests')]
from test_ui_read_model import conducted_context_fixture
from test_ui_server import conducted_preview_inputs
from labflow.ui_server import create_server
from labflow import intake_conducted_twin_plan as adapter
from labflow.active_intake import scan_source
from labflow.intake_jobs import claim_job,complete_job
from labflow.intake_worker import SyntheticTextProvider
def main():
 mode=sys.argv[2];calls=[];genuine=adapter.build_conducted_twin_plan_input
 adapter_raw=Path(adapter.__file__).read_bytes();adapter_git_lf=adapter_raw.replace(b'\r\n',b'\n')
 def observed(*args,**kwargs):
  report=genuine(*args,**kwargs);calls.append(report);return report
 adapter.build_conducted_twin_plan_input=observed
 with tempfile.TemporaryDirectory(prefix='conducted-preview-') as directory:
  fixture=conducted_context_fixture(Path(directory)/'fixture',kind='text' if mode=='text' else 'pdf',completed=mode!='incomplete',synthetic=mode!='non-synthetic')
  if mode=='unconfirmed-source':
   with fixture['store'].connection() as con:con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?',(fixture['context']['documents'][0]['sha256'],))
  inputs=conducted_preview_inputs(fixture['intake_id'])
  if mode=='missing':inputs=None
  elif mode=='other':inputs['intake_id']='I-other'
  elif mode=='old-revision':inputs['revision']=99
  elif mode=='basis-missing':inputs['source_settings']['power_dbm']=0;del inputs['basis']['power_dbm']
  server=create_server(fixture['store'].root,port=0,conducted_plan_preview_inputs=inputs)
  thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
  print(json.dumps({'origin':'http://127.0.0.1:'+str(server.server_port),'intake_id':fixture['intake_id'],'mode':mode,
   'adapter_path':str(Path(adapter.__file__).resolve()),'adapter_bytes':len(adapter_raw),'adapter_sha256':hashlib.sha256(adapter_raw).hexdigest(),'adapter_git_lf_bytes':len(adapter_git_lf),'adapter_git_lf_sha256':hashlib.sha256(adapter_git_lf).hexdigest()}),flush=True)
  try:
   for line in sys.stdin:
    command=line.strip()
    if command=='stop':break
    if command=='revise':
     (fixture['inbox']/'request'/'revision.txt').write_text('firmware: synthetic revision 2\n',encoding='utf-8')
     scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120);scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120.01)
    elif command=='complete_revision':
     job=claim_job(fixture['store'],'preview-revision',now=121)
     context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
     complete_job(fixture['store'],job['job_id'],job['token'],SyntheticTextProvider().analyze(context),now=122)
    else:raise ValueError('unknown test control')
    print(json.dumps({'control':command}),flush=True)
  finally:
   address=server.server_address;server.shutdown();server.server_close();thread.join(5)
   assert not thread.is_alive() and server.socket.fileno()==-1
   with socket.socket() as probe:probe.bind(address)
   print(json.dumps({'resource':{'loop_stopped':True,'listener_closed':True,'port_rebind':True,'adapter_calls':len(calls),'actual_model_calls':0,'hardware_calls':0}}),flush=True)
if __name__=='__main__':main()
`;
function verifyPreviewAdapterSource(info){
  const fixed=fs.realpathSync(path.join(ROOT,'labflow','intake_conducted_twin_plan.py'));
  assert.equal(fs.realpathSync(info.adapter_path),fixed);
  const raw=fs.readFileSync(fixed);
  // Normalize only CRLF byte pairs. Preserve raw bytes/hash as a separate pin.
  const gitLF=Buffer.from(raw.toString('latin1').replaceAll('\r\n','\n'),'latin1');
  const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
  const pins={adapter_path:fixed,raw:{bytes:raw.length,sha256:hash(raw)},git_lf:{bytes:gitLF.length,sha256:hash(gitLF)},normalization:'CRLF bytes to LF only'};
  assert.equal(info.adapter_bytes,pins.raw.bytes);assert.equal(info.adapter_sha256,pins.raw.sha256);
  assert.equal(info.adapter_git_lf_bytes,pins.git_lf.bytes);assert.equal(info.adapter_git_lf_sha256,pins.git_lf.sha256);
  assert.equal(pins.git_lf.sha256,'0286769450f4efef874602164b2bfdb5aa0ac2f027aa48fcc4c0a219f230ebc9');
  return pins;
}

function startPreviewHost(mode,source=previewHost,fileName='preview_host.py'){
  const file=path.join(OUTPUT,fileName);if(!fs.existsSync(file))proofWrite(file,source);
  const python=process.env.VLAB_PYTHON||path.join(ROOT,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
  const child=spawn(python,['-B','-X','utf8',file,ROOT,mode],{cwd:ROOT,windowsHide:true,stdio:['pipe','pipe','pipe']});
  let buffer='',stderr='',exitCode=null;const queue=[],waiters=[];
  child.stderr.on('data',chunk=>{stderr+=chunk.toString();if(stderr.length>8192)child.kill();});
  child.stdout.on('data',chunk=>{buffer+=chunk.toString();while(buffer.includes('\n')){const i=buffer.indexOf('\n'),line=buffer.slice(0,i);buffer=buffer.slice(i+1);const value=JSON.parse(line);if(waiters.length){const w=waiters.shift();clearTimeout(w.timer);w.resolve(value);}else queue.push(value);}});
  const exited=new Promise(resolve=>child.once('exit',code=>{exitCode=code;for(const w of waiters.splice(0)){clearTimeout(w.timer);w.reject(Error('preview host exited '+code+': '+stderr));}resolve(code);}));
  const next=()=>new Promise((resolve,reject)=>{if(queue.length)return resolve(queue.shift());if(exitCode!==null)return reject(Error('preview host exited '+exitCode+': '+stderr));const w={resolve,reject};w.timer=setTimeout(()=>{const i=waiters.indexOf(w);if(i>=0)waiters.splice(i,1);reject(Error('preview host response timeout: '+stderr));},15000);waiters.push(w);});
  return {child,next,exited,alive:()=>exitCode===null,stderr:()=>stderr,command:async cmd=>{child.stdin.write(cmd+'\n');assert.equal((await next()).control,cmd);}};
}
async function conductedPreviewMain(){
  const observations=[],faults=[],resources=[],sourcePins=[];let browser;
  try{
    browser=await chromium.launch({headless:true});
    for(const mode of ['matched','missing','other','old-revision','basis-missing','text','non-synthetic','incomplete','unconfirmed-source']){
      const host=startPreviewHost(mode);let info;
      try{
        info=await host.next();sourcePins.push({mode,...verifyPreviewAdapterSource(info)});
        const endpoint=info.origin+'/api/intakes/'+info.intake_id+'/conducted-plan-preview';
        const observe=async(width,phase='initial')=>{
          const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[],external=[],methods=[];let previewRequests=0;
          page.setDefaultTimeout(5000);page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/'))methods.push(r.method());if(r.url()===endpoint)previewRequests++;});
          try{
            await page.goto(info.origin+'/#'+info.intake_id);const panel=page.locator('#conducted-plan-preview');await panel.waitFor();
            await page.waitForFunction(()=>document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');
            const response=await context.request.get(endpoint),status=response.status(),body=await response.json();
            if(status===200){
              await page.locator('#conducted-plan-status').filter({hasText:'조회 완료'}).waitFor();
              const text=await panel.innerText();assert.ok(text.includes(body.context_sha256)&&text.includes('현재 제공 context')&&text.includes('원 모델 prompt 복원 아님'));
              assert.ok(text.includes('실행 권한 없음')&&text.includes('규제 적합성 미평가')&&text.includes('실측 예측력 미평가'));
              assert.equal(await panel.getAttribute('data-preview-status'),body.plan_input.status);
              assert.equal(await panel.locator('[data-plan-setting]').count(),6);
              if(body.plan_input.status==='ready_for_simulation'){assert.equal(mode,'matched');assert.equal(phase,'initial');assert.ok(text.includes('가상 계획 입력 준비'));}
              else{assert.ok(text.includes('가상 계획 입력 보류'));assert.ok(body.plan_input.gaps.length>0);assert.equal(await panel.locator('[data-plan-gap]').count(),body.plan_input.gaps.length);}
              if(mode==='basis-missing'){const row=panel.locator('[data-plan-setting="power_dbm"]');assert.ok((await row.innerText()).includes('미제공(null)'));assert.ok(text.includes('원 제공값: 0'));}
              if(mode==='matched'&&phase==='initial'){
                await panel.evaluate(node=>node.scrollIntoView({block:'start'}));await screenshot(page,path.join(OUTPUT,'preview-top-'+width+'.png'));
                await panel.locator('table').scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'preview-settings-'+width+'.png'));
                const good=await panel.locator('#conducted-plan-content').innerText();
                for(const fault of ['HTTP503','authority','binding','oversize']){
                  const altered=structuredClone(body);if(fault==='authority')altered.plan_input.verification.execution_authority=true;if(fault==='binding')altered.intake_id='I-other';
                  await page.route(endpoint,r=>r.fulfill({status:fault==='HTTP503'?503:200,contentType:'application/json',body:fault==='HTTP503'?'{"error":{"code":"intake_conducted_preview_unavailable"}}':fault==='oversize'?' '.repeat(262145):JSON.stringify(altered)}));
                  await page.locator('#conducted-plan-refresh').click();await page.locator('#conducted-plan-status').filter({hasText:'이전 관측'}).waitFor();
                  await page.waitForFunction(()=>document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');
                  assert.equal(await panel.locator('#conducted-plan-content').innerText(),good);assert.equal(await panel.getAttribute('data-preview-current'),'false');
                  await page.unroute(endpoint);faults.push({width,fault,scope:'typed HTTP/contract injection after genuine read; not genuine adapter success'});
                }
                const beforeRender=previewRequests;
                await page.evaluate(()=>{const native=document.createElement.bind(document);document.createElement=(tag,...args)=>{if(tag==='caption'){document.createElement=native;throw Error('synthetic preview render failure');}return native(tag,...args);};});
                await page.locator('#conducted-plan-refresh').click();await page.waitForFunction(()=>document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');
                assert.equal(previewRequests,beforeRender);assert.equal(await panel.locator('#conducted-plan-content').innerText(),good);
                faults.push({width,fault:'render-before-request',scope:'synthetic DOM failure, last-good kept and no new GET'});
                await page.waitForFunction(()=>!document.querySelector('#fixture-refresh')?.disabled);
                let deadlineRelease,deadlineArrived;const deadlineHold=new Promise(r=>deadlineRelease=r),deadlineSeen=new Promise(r=>deadlineArrived=r);
                await page.evaluate(()=>{const set=window.setTimeout,clear=window.clearTimeout,timers=new Map();window.setTimeout=function(fn,ms,...args){const id=set.call(window,fn,ms,...args);if(ms===10000)timers.set(id,()=>fn(...args));return id;};window.clearTimeout=function(id){timers.delete(id);return clear.call(window,id);};window.__previewClock={fire(){const pending=[...timers];for(const [id,fn]of pending){clear.call(window,id);timers.delete(id);fn();}return pending.length;},restore(){for(const id of timers.keys())clear.call(window,id);window.setTimeout=set;window.clearTimeout=clear;delete window.__previewClock;}};});
                await page.route(endpoint,async route=>{deadlineArrived();await deadlineHold;await route.abort().catch(()=>{});});
                try{
                  await page.locator('#conducted-plan-refresh').click();await deadlineSeen;assert.equal(await page.evaluate(()=>__previewClock.fire()),1);
                  await page.waitForFunction(()=>document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');assert.equal(await panel.locator('#conducted-plan-content').innerText(),good);assert.equal(await panel.getAttribute('data-preview-current'),'false');
                  faults.push({width,fault:'deadline-callback',scope:'synthetic10s callback, no elapsed-wall-time claim; last-good kept'});
                }finally{deadlineRelease();await page.unroute(endpoint);await page.evaluate(()=>__previewClock.restore());}
                let release,arrived;const hold=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);let first=true;
                await page.evaluate(()=>{window.__previewFetch=window.fetch;window.fetch=(url,options)=>window.__previewFetch(url,String(url).endsWith('/conducted-plan-preview')?{...options,signal:undefined}:options);});
                await page.route(endpoint,async route=>{if(!first)return route.continue();first=false;arrived();await hold;const late=structuredClone(body);late.plan_input.intake.facts.product_type.value='LATE-INJECTED';await route.fulfill({json:late}).catch(()=>{});});
                try{
                  await page.locator('#conducted-plan-refresh').click();await seen;await page.locator('#refresh').click();
                  await page.locator('#conducted-plan-status').filter({hasText:'조회 완료'}).waitFor();release();await page.waitForTimeout(100);
                  assert.ok(!(await panel.innerText()).includes('LATE-INJECTED'));faults.push({width,fault:'late-after-snapshot',scope:'typed late transport ignoring abort; current generation preserved'});
                }finally{release();await page.unroute(endpoint);await page.evaluate(()=>{window.fetch=window.__previewFetch;delete window.__previewFetch;});}
              }
            }else{
              assert.equal(status,503);await page.locator('#conducted-plan-status').filter({hasText:'미지원'}).waitFor();assert.equal(await panel.locator('[data-plan-setting]').count(),0);
            }
            assert.equal(await panel.locator('input,select,a').count(),0);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
            assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(x=>x==='GET'));
            observations.push({mode,width,phase,status,adapter_report:status===200,scope:'genuine retained completion -> current RO context -> genuine D1 adapter when supported -> protected GET -> production DOM; synthetic analyzer function, actual model0'});
          }finally{await context.close();}
        };
        for(const width of [390,1440])await observe(width);
        if(mode==='matched'){
          await host.command('revise');for(const width of [390,1440])await observe(width,'new-incomplete-revision');
          await host.command('complete_revision');for(const width of [390,1440])await observe(width,'completed-revision-with-old-selection');
        }
      }finally{
        if(host.alive()&&info){host.child.stdin.end('stop\n');const value=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(value.resource?.loop_stopped&&value.resource.listener_closed&&value.resource.port_rebind);resources.push({mode,...value.resource,child_exit:code});}
        else{if(host.alive())host.child.kill();await host.exited;}
      }
    }
    proofWrite(path.join(OUTPUT,'preview-results.json'),JSON.stringify({status:'pass',observations,typed_faults:faults,resources,adapter_source_pins:sourcePins,actual_model_calls:0,hardware_calls:0},null,2));
    console.log(JSON.stringify({status:'pass',observations:observations.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'preview-failure.json'),JSON.stringify({status:'fail',message:error.message,observations,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}

const resultHost=String.raw`
import json,sys,tempfile,threading,socket
from pathlib import Path
sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'tests')]
from test_ui_read_model import conducted_context_fixture,provided_result_fixture
from labflow.ui_server import create_server
from labflow.active_intake import scan_source
from labflow.intake_jobs import claim_job,complete_job
from labflow.intake_worker import SyntheticTextProvider
def main():
 mode=sys.argv[2]
 with tempfile.TemporaryDirectory(prefix='result-provided-') as directory:
  fixture=conducted_context_fixture(Path(directory)/'actual',kind='text' if mode=='text' else 'pdf',completed=mode!='incomplete-intake',synthetic=mode!='non-synthetic')
  reference=conducted_context_fixture(Path(directory)/'typed') if mode in ('text','incomplete-intake','non-synthetic') else fixture
  snapshot=provided_result_fixture(reference);snapshot['intake_id']=fixture['intake_id'];r=snapshot['result']
  if mode in ('incomplete','invalid0','invalid2','invalid11'):
   r['calculation']['corrected']=None
   if mode=='incomplete':
    r['status']='incomplete';r['binding']={k:r['binding'][k] for k in ('plan_input','run_report')};r['failure']={'code':'setup_partial','field':'setup_snapshot'};r['gaps']=[{'code':'setup_partial','field':'setup_snapshot','provided':None,'blocking':True}]
   else:
    r['status']='invalid';r['failure']={'code':'measurement_invalid','field':'observation.sensor'};r['gaps']=[None,42,{'malformed':'original'}];r['raw_measurement']['packet']={'status':'bad','value':'-3e7','unit':None,'original_extra':[0,False]};r['raw_measurement']['quantity']=['original',0];r['setup_provenance']['records']={'malformed':'original'}
    if mode=='invalid0':r['binding']={}
    if mode=='invalid2':r['binding']={'plan_input':42,'run_report':['original']}
  if mode=='expected-missing':snapshot['expected_current_binding']=None
  if mode=='expected-conflict':snapshot['expected_current_binding']['context_sha256']='f'*64
  if mode=='revision-conflict':snapshot['revision']=99
  if mode=='shape-invalid':r['verification']['execution_authority']=True
  if mode=='source-invalid':fixture['store'].blob_path(fixture['context']['documents'][0]['sha256']).write_bytes(b'changed')
  server=create_server(fixture['store'].root,port=0,conducted_result_snapshot=None if mode=='missing' else snapshot)
  thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
  assert 'labflow.virtual_fleet.conducted_twin_result' not in sys.modules
  print(json.dumps({'origin':'http://127.0.0.1:'+str(server.server_port),'intake_id':fixture['intake_id'],'mode':mode}),flush=True)
  try:
   for line in sys.stdin:
    command=line.strip()
    if command=='stop':break
    if command=='revise':
     (fixture['inbox']/'request'/'revision.txt').write_text('firmware: synthetic revision 2\n',encoding='utf-8');scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120);scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120.01)
    elif command=='complete_revision':
     job=claim_job(fixture['store'],'provided-revision',now=121);context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')};complete_job(fixture['store'],job['job_id'],job['token'],SyntheticTextProvider().analyze(context),now=122)
    else:raise ValueError('unknown test control')
    print(json.dumps({'control':command}),flush=True)
  finally:
   address=server.server_address;server.shutdown();server.server_close();thread.join(5);assert not thread.is_alive() and server.socket.fileno()==-1
   with socket.socket() as probe:probe.bind(address)
   assert 'labflow.virtual_fleet.conducted_twin_result' not in sys.modules
   print(json.dumps({'resource':{'loop_stopped':True,'listener_closed':True,'port_rebind':True,'D3_builder_calls':0,'actual_model_calls':0,'hardware_calls':0}}),flush=True)
if __name__=='__main__':main()
`;
async function conductedResultMain(){
  const observations=[],faults=[],resources=[];let browser;
  try{
    browser=await chromium.launch({headless:true});
    for(const mode of ['recorded','incomplete','invalid0','invalid2','invalid11','expected-missing','expected-conflict','revision-conflict','missing','shape-invalid','source-invalid','non-synthetic','text','incomplete-intake']){
      const host=startPreviewHost(mode,resultHost,'result_host.py');let info;
      try{
        info=await host.next();const endpoint=info.origin+'/api/intakes/'+info.intake_id+'/conducted-result';
        const observe=async(width,phase='initial')=>{
          const context=await browser.newContext({viewport:{width,height:950}}),page=await context.newPage(),errors=[],external=[],methods=[];
          page.setDefaultTimeout(6000);page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/'))methods.push(r.method());});
          const idle=()=>page.waitForFunction(()=>document.querySelector('#conducted-result-view')?.dataset.pending==='false');
          const refresh=async()=>{await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await page.locator('#refresh').click();await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await idle();};
          try{
            await page.goto(info.origin+'/#'+info.intake_id);const panel=page.locator('#conducted-result-view');await panel.waitFor();await idle();
            const response=await context.request.get(endpoint),status=response.status(),body=await response.json();
            if(status===200){
              await page.locator('#conducted-result-status').filter({hasText:'제공 snapshot 조회'}).waitFor();
              const text=await panel.innerText();assert.ok(text.includes('provided_snapshot')&&text.includes('실제 AI 호출 여부 unknown')&&text.includes('저장/실시간 결과 조회 미지원')&&text.includes(body.context_sha256));
              assert.ok(text.includes('최종 판정 승인 미평가'));assert.equal(await panel.getAttribute('data-result-status'),body.result.status);
              assert.equal(await panel.getAttribute('data-current'),String(body.relation.status==='matched'));
              if(mode.startsWith('invalid')){assert.ok(text.includes('-3e7'));assert.ok(text.includes('미제공(null)'));assert.equal(await panel.locator('[data-result-gap]').count(),3);}
              if(body.relation.status==='blocked')for(const reason of body.relation.reasons)assert.ok(text.includes(reason));
              if(mode==='recorded'&&phase==='initial'){
                await panel.scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'result-top-'+width+'.png'));
                await panel.locator('#conducted-result-content').scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'result-content-'+width+'.png'));
                const good=await panel.locator('#conducted-result-content').innerText();
                for(const fault of ['HTTP503','authority','binding','failure-code','oversize']){
                  const altered=structuredClone(body);if(fault==='authority')altered.result.verification.execution_authority=true;if(fault==='binding')altered.context_sha256='f'.repeat(64);if(fault==='failure-code'){altered.result.status='invalid';altered.result.failure={code:'future',field:'input'};}
                  await page.route(endpoint,r=>r.fulfill({status:fault==='HTTP503'?503:200,contentType:'application/json',body:fault==='HTTP503'?'{"error":{"code":"intake_conducted_result_unavailable"}}':fault==='oversize'?' '.repeat(1048577):JSON.stringify(altered)}));
                  await refresh();assert.equal(await panel.locator('#conducted-result-content').innerText(),good);assert.equal(await panel.getAttribute('data-current'),'false');assert.ok((await page.locator('#conducted-result-status').innerText()).includes('이전 관측'));await page.unroute(endpoint);faults.push({width,fault,scope:'typed transport/contract injection; not D3 builder observation'});
                }
                await page.evaluate(()=>{const native=document.createElement.bind(document);document.createElement=(tag,...args)=>{if(tag==='h5'){document.createElement=native;throw Error('typed result render failure');}return native(tag,...args);};});
                await refresh();assert.equal(await panel.locator('#conducted-result-content').innerText(),good);faults.push({width,fault:'render-before-parent-publication',scope:'typed DOM render failure; previous content retained'});
                let releaseDeadline,seenDeadline;const holdDeadline=new Promise(r=>releaseDeadline=r),arrivedDeadline=new Promise(r=>seenDeadline=r);
                await page.evaluate(()=>{const set=window.setTimeout,clear=window.clearTimeout,timers=new Map();window.setTimeout=function(fn,ms,...args){const id=set.call(window,fn,ms,...args);if(ms===10000)timers.set(id,()=>fn(...args));return id;};window.clearTimeout=function(id){timers.delete(id);return clear.call(window,id);};window.__resultClock={fire(){const pending=[...timers];for(const [id,fn]of pending){clear.call(window,id);timers.delete(id);fn();}return pending.length;},restore(){for(const id of timers.keys())clear.call(window,id);window.setTimeout=set;window.clearTimeout=clear;delete window.__resultClock;}};});
                await page.route(endpoint,async route=>{seenDeadline();await holdDeadline;await route.abort().catch(()=>{});});
                try{
                  const pendingRefresh=refresh();await arrivedDeadline;await page.waitForFunction(()=>document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');assert.equal(await page.evaluate(()=>__resultClock.fire()),1);await pendingRefresh;assert.equal(await panel.locator('#conducted-result-content').innerText(),good);assert.equal(await panel.getAttribute('data-current'),'false');faults.push({width,fault:'deadline-callback',scope:'synthetic10s callback; no elapsed wall-time claim'});
                }finally{releaseDeadline();await page.unroute(endpoint);await page.evaluate(()=>__resultClock.restore());}
                let release,seen;const hold=new Promise(r=>release=r),arrived=new Promise(r=>seen=r);let first=true;
                await page.evaluate(()=>{window.__resultFetch=window.fetch;window.fetch=(url,options)=>window.__resultFetch(url,String(url).endsWith('/conducted-result')?{...options,signal:undefined}:options);});
                await page.route(endpoint,async route=>{if(!first)return route.continue();first=false;seen();await hold;const late=structuredClone(body);late.result.raw_measurement.packet.extra_marker='LATE-INJECTED';await route.fulfill({json:late}).catch(()=>{});});
                try{
                  await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await page.locator('#refresh').click();await arrived;await refresh();release();await page.waitForTimeout(100);assert.ok(!(await panel.innerText()).includes('LATE-INJECTED'));faults.push({width,fault:'late-after-parent-snapshot',scope:'typed late result ignoring abort; current generation retained'});
                }finally{release();await page.unroute(endpoint);await page.evaluate(()=>{window.fetch=window.__resultFetch;delete window.__resultFetch;});}
              }
            }else{assert.equal(status,503);assert.ok((await page.locator('#conducted-result-status').innerText()).includes('조회 불가'));assert.equal(await panel.locator('#conducted-result-content').innerText(),'');}
            assert.equal(await panel.locator('button,input,select,a').count(),0);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(x=>x==='GET'));
            observations.push({mode,width,phase,status,source_kind:'provided_snapshot',scope:'typed provided public D3 snapshot + genuine current RO context/protected GET/production DOM; D3 builder0,actual model0'});
          }finally{await context.close();}
        };
        for(const width of [390,1440])await observe(width);
        if(mode==='recorded'){await host.command('revise');for(const width of [390,1440])await observe(width,'incomplete-revision');await host.command('complete_revision');for(const width of [390,1440])await observe(width,'new-revision-old-provided-snapshot');}
      }finally{
        if(host.alive()&&info){host.child.stdin.end('stop\n');const value=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(value.resource?.loop_stopped&&value.resource.listener_closed&&value.resource.port_rebind);resources.push({mode,...value.resource,child_exit:code});}
        else{if(host.alive())host.child.kill();await host.exited;}
      }
    }
    proofWrite(path.join(OUTPUT,'result-results.json'),JSON.stringify({status:'pass',observations,typed_faults:faults,resources,D3_builder_calls:0,actual_model_calls:0,hardware_calls:0},null,2));console.log(JSON.stringify({status:'pass',observations:observations.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'result-failure.json'),JSON.stringify({status:'fail',message:error.message,observations,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}


const queueFixtureInjection=String.raw`
  plan=r['binding']['plan_input']['plan']
  plan_inputs={'intake_id':fixture['intake_id'],'revision':1,'source_settings':dict(plan['source_settings']),'basis':{key:dict(value) for key,value in plan['basis_refs'].items()},'method':{key:plan[key] for key in ('method_id','method_version','metric','reference_plane')}}
  if mode=='missing':plan_inputs=None
  if mode=='error':
   r.update(status='incomplete',failure={'code':'setup_failed','field':'setup_snapshot'},gaps=[{'code':'setup_failed','field':'setup_snapshot','provided':None,'blocking':True}]);r['calculation']['corrected']=None
  if mode=='unsupported':
   plan_inputs['method']['metric']='unsupported';r.update(status='incomplete',failure={'code':'unsupported_path_device','field':'topology'},gaps=[{'code':'unsupported_path_device','field':'topology','provided':None,'blocking':True}]);r['calculation']['corrected']=None
  if mode=='old-revision':
   r.update(status='incomplete',failure={'code':'measurement_missing','field':'measurement_ref'},gaps=[{'code':'measurement_missing','field':'measurement_ref','provided':None,'blocking':True}]);r['calculation']['corrected']=None
  if mode=='condition-mismatch':
   plan_inputs['source_settings']['power_dbm']=0;plan_inputs['basis']['power_dbm']['value']=0;r.update(status='incomplete',failure=None,gaps=[{'code':'correction_basis_missing','field':'quantity','provided':None,'blocking':True}]);r['calculation']['corrected']=None
  if mode=='evidence-review':
   r.update(status='invalid',failure={'code':'evidence_context_missing','field':'input'},gaps=[{'code':code,'field':'source_settings.frequency_hz','provided':None,'blocking':True,'refs':['condition-'+str(index)]} for index,code in enumerate(['source_statement_unsupported','source_quote_mismatch','source_condition_unbound','source_fact_missing'])]);r['gaps'].append({**r['gaps'][2],'refs':['different-condition']});r['calculation']['corrected']=None
`;
const queueServerLine="  server=create_server(fixture['store'].root,port=0,conducted_result_snapshot=None if mode=='missing' else snapshot)";
assert.ok(resultHost.includes(queueServerLine));
const queueHost=resultHost.replace(queueServerLine,queueFixtureInjection+"\n  server=create_server(fixture['store'].root,port=0,conducted_plan_preview_inputs=plan_inputs,conducted_result_snapshot=None if mode=='missing' else snapshot)");
async function gapQueueMain(){
  const observations=[],faults=[],resources=[];let browser;
  try{
    browser=await chromium.launch({headless:true});
    for(const mode of ['normal','missing','error','unsupported','old-revision','condition-mismatch','evidence-review']){
      const host=startPreviewHost(mode,queueHost,'queue_host.py');let info;
      try{
        info=await host.next();if(mode==='old-revision'){await host.command('revise');await host.command('complete_revision');}
        for(const width of [390,1440]){
          const context=await browser.newContext({viewport:{width,height:950}}),page=await context.newPage(),errors=[],external=[],methods=[];
          page.setDefaultTimeout(6000);page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!request.url().startsWith(info.origin+'/'))external.push(request.url());if(request.url().includes('/api/'))methods.push(request.method());});
          const planURL=info.origin+'/api/intakes/'+info.intake_id+'/conducted-plan-preview',resultURL=info.origin+'/api/intakes/'+info.intake_id+'/conducted-result';
          const idle=()=>page.waitForFunction(()=>!document.querySelector('#refresh').disabled&&document.querySelector('#intake-gap-queue')?.dataset.pending==='false');
          const refresh=async()=>{await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await page.locator('#refresh').click();await idle();};
          const rawRows=()=>page.locator('#intake-gap-queue [data-gap-queue-original]').allTextContents();
          try{
            await page.goto(info.origin+'/#'+info.intake_id);const queue=page.locator('#intake-gap-queue');await queue.waitFor();await idle();
            const bodies={};for(const [name,url]of [['intakes',info.origin+'/api/intakes'],['plan',planURL],['result',resultURL]]){const response=await context.request.get(url),raw=await response.body();proofWrite(path.join(OUTPUT,mode+'-'+width+'-'+name+'.json'),raw);bodies[name]={status:response.status(),value:JSON.parse(raw.toString('utf8'))};}
            assert.deepEqual(await queue.locator('[data-gap-queue-group]').evaluateAll(nodes=>nodes.map(node=>node.dataset.gapQueueGroup)),['intake_questions','plan_questions','plan_gaps','result_gaps']);
            const intake=bodies.intakes.value.intakes.find(record=>record.intake_id===info.intake_id),revision=intake.revision;assert.equal(await queue.getAttribute('data-intake-id'),info.intake_id);assert.equal(await queue.getAttribute('data-revision'),String(revision));
            const expected={'intake_questions':intake.analysis?.questions||[],plan_questions:bodies.plan.value.plan_input?.intake.questions||[],plan_gaps:bodies.plan.value.plan_input?.gaps||[],result_gaps:bodies.result.value.result?.gaps||[]};
            for(const [source,rows]of Object.entries(expected)){const group=queue.locator('[data-gap-queue-group="'+source+'"]');assert.equal(await group.locator('[data-gap-queue-item]').count(),rows.length);const indices=await group.locator('[data-gap-queue-item]').evaluateAll(nodes=>nodes.map(node=>Number(node.dataset.gapQueueItem.split(':').pop())));assert.deepEqual(indices,rows.map((_,index)=>index));const raw=await group.locator('[data-gap-queue-original]').allTextContents();for(const [index,value]of rows.entries()){if(value&&typeof value==='object')for(const key of Object.keys(value))assert.ok(raw[index].includes(key));if(value?.message)assert.ok(raw[index].includes(value.message));}}
            if(mode==='normal'){assert.ok(await queue.locator('[data-gap-queue-group="plan_gaps"][data-state="current"]').count());}
            if(mode==='missing'){assert.ok(await queue.locator('[data-gap-queue-group="plan_gaps"] [data-category="conditions_required"]').count());assert.ok((await queue.innerText()).includes('intake_conducted_result_missing'));}
            if(mode==='error')assert.equal(await queue.locator('[data-gap-queue-group="result_gaps"] [data-category="system_error"]').count(),1);
            if(mode==='unsupported')assert.ok(await queue.locator('[data-gap-queue-group="plan_gaps"] [data-category="unsupported"]').count());
            if(mode==='old-revision'){assert.equal(revision,2);assert.equal(await queue.locator('[data-gap-queue-group="plan_questions"]').getAttribute('data-state'),'blocked');assert.equal(await queue.locator('[data-gap-queue-group="result_gaps"]').getAttribute('data-state'),'blocked');assert.equal(await queue.locator('[data-gap-queue-group="result_gaps"] [data-category="facts_required"]').count(),0);assert.ok((await queue.innerText()).includes('provided_revision_changed'));}
            if(mode==='condition-mismatch'){assert.ok((await queue.innerText()).includes('plan_condition_mismatch'));assert.equal(await queue.locator('[data-gap-queue-group="result_gaps"] [data-category="blocked"]').count(),1);}
            if(mode==='evidence-review'){assert.equal(await queue.locator('[data-gap-queue-group="result_gaps"] [data-gap-queue-review]').count(),5);assert.equal(await queue.locator('[data-gap-queue-group="result_gaps"] [data-category="facts_required"]').count(),0);const raw=await queue.locator('[data-gap-queue-group="result_gaps"] [data-gap-queue-original]').allTextContents();assert.ok(raw[2].includes('condition-2'));assert.ok(raw[4].includes('different-condition'));assert.ok((await queue.innerText()).includes('원자료 부재는 미확인'));}
            if(mode==='normal'){
              await queue.scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'queue-top-'+width+'.png'));await queue.locator('[data-gap-queue-group="plan_gaps"]').scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'queue-conditions-'+width+'.png'));
            }
            if(mode==='error'){
              const originals=await rawRows();assert.ok(originals.length>0,'nonempty last-good rows required for preservation fault checks');await page.route(info.origin+'/api/intakes',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":{"code":"store_unavailable"}}'}));await refresh();assert.deepEqual(await rawRows(),originals);assert.equal(await queue.locator('[data-category="facts_required"]').count(),0);assert.equal(await queue.getAttribute('data-current'),'false');faults.push({width,fault:'parent-HTTP503',scope:'typed parent failure; last original rows retained and all current-question promotion blocked'});await page.unroute(info.origin+'/api/intakes');await refresh();
              await page.route(info.origin+'/api/intakes',async route=>{const response=await route.fetch(),payload=await response.json(),record=payload.intakes.find(value=>value.intake_id===info.intake_id);const original=record.analysis.questions;const hasFact=original.some(q=>['customer','model','firmware','manufacturer'].includes(q.field)&&q.key==='missing_'+q.field);const extra=['source_statement_unsupported','source_quote_mismatch','source_condition_unbound','source_fact_missing'].map((code,index)=>({key:code,code,field:'source_settings.frequency_hz',message:'근거 연결 상태 '+code,provided:null,refs:['condition-'+index]}));extra.push({...extra[2],refs:['different-condition']});record.analysis.questions=[...original,...(hasFact?[]:[{key:'missing_firmware',field:'firmware',message:'firmware 사실 확인 · typed',refs:null}]),...extra];const raw=JSON.stringify(payload);proofWrite(path.join(OUTPUT,'error-'+width+'-typed-evidence-snapshot.json'),raw);await route.fulfill({body:raw,contentType:'application/json'});});
              await refresh();assert.equal(await queue.locator('[data-gap-queue-group="intake_questions"] [data-category="evidence_review"]').count(),5);assert.ok(await queue.locator('[data-gap-queue-group="intake_questions"] [data-category="facts_required"]').count());assert.ok((await queue.innerText()).includes('원자료 부재는 미확인'));const reviewRaw=await queue.locator('[data-gap-queue-group="intake_questions"] [data-gap-queue-review]').allInnerTexts();assert.equal(reviewRaw.length,5);faults.push({width,fault:'extraction-evidence-public-literals',scope:'typed snapshot projection additions over genuine local host; not actual extractor/raw-absence evidence, original questions preserved'});await page.unroute(info.origin+'/api/intakes');await refresh();
              let release,seen;const hold=new Promise(resolve=>release=resolve),arrived=new Promise(resolve=>seen=resolve);let first=true;const actualPlan=bodies.plan.value;
              await page.evaluate(()=>{window.__queueFetch=window.fetch;window.fetch=(url,options)=>window.__queueFetch(url,String(url).endsWith('/conducted-plan-preview')?{...options,signal:undefined}:options);});
              await page.route(planURL,async route=>{if(!first)return route.continue();first=false;seen();await hold;const late=structuredClone(actualPlan);late.plan_input.intake.questions.push({key:'missing_firmware',field:'firmware',message:'LATE_QUEUE_ORIGIN'});const raw=JSON.stringify(late);proofWrite(path.join(OUTPUT,'error-'+width+'-typed-late-plan.json'),raw);await route.fulfill({body:raw,contentType:'application/json'}).catch(()=>{});});
              try{await page.locator('#refresh').click();await arrived;await refresh();release();await page.waitForTimeout(100);assert.ok(!(await queue.innerText()).includes('LATE_QUEUE_ORIGIN'));faults.push({width,fault:'late-plan-after-parent-snapshot',scope:'typed valid late plan ignoring abort; previous generation never becomes a current queue question'});}finally{release();await page.unroute(planURL);await page.evaluate(()=>{window.fetch=window.__queueFetch;delete window.__queueFetch;});}
              const beforeRender=await rawRows();await page.evaluate(()=>{const descriptor=Object.getOwnPropertyDescriptor(Node.prototype,'textContent');window.__restoreQueueText=()=>{Object.defineProperty(Node.prototype,'textContent',descriptor);delete window.__restoreQueueText;};Object.defineProperty(Node.prototype,'textContent',{...descriptor,set(value){if(value==='예외·다음 조건 큐')throw Error('typed queue render failure');return descriptor.set.call(this,value);}});});
              try{await refresh();assert.deepEqual(await rawRows(),beforeRender);assert.equal(await queue.locator('[data-category="facts_required"]').count(),0);assert.equal(await queue.getAttribute('data-current'),'false');faults.push({width,fault:'queue-render-failure',scope:'typed renderer failure; original rows kept, blocked state displayed; no backend mutation'});}finally{await page.evaluate(()=>__restoreQueueText());}await refresh();
            }
            assert.equal(await queue.locator('button,input,select,a').count(),0);assert.equal(await page.locator('#intake-workflow [data-workflow-step]').count(),7);assert.ok((await page.locator('#conducted-result-view').innerText()).includes('실제 AI 호출 여부 unknown'));assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(method=>method==='GET'));
            observations.push({mode,width,intake_id:info.intake_id,revision,plan_status:bodies.plan.status,result_status:bodies.result.status,group_counts:Object.fromEntries(Object.entries(expected).map(([key,rows])=>[key,rows.length])),scope:'genuine current intake/plan/protected GET/production DOM plus explicitly typed provided result snapshots; no D3 builder/extractor/model accuracy claim'});
          }finally{await context.close();}
        }
      }finally{
        if(host.alive()&&info){host.child.stdin.end('stop\n');const value=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(value.resource?.loop_stopped&&value.resource.listener_closed&&value.resource.port_rebind);resources.push({mode,...value.resource,child_exit:code});}
        else{if(host.alive())host.child.kill();await host.exited;}
      }
    }
    proofWrite(path.join(OUTPUT,'queue-results.json'),JSON.stringify({status:'pass',observations,typed_faults:faults,resources,actual_model_calls:0,D3_builder_calls:0,hardware_calls:0},null,2));console.log(JSON.stringify({status:'pass',observations:observations.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'queue-failure.json'),JSON.stringify({status:'fail',message:error.message,observations,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}

const unifiedSavedHost=String.raw`
import sys,json,threading,socket
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from labflow.ui_server import create_server
saved=Path(sys.argv[2]);summary=json.loads((saved/'public-summary.json').read_bytes())
startup=saved/'server-startup-original.json';options=json.loads(startup.read_bytes()) if startup.exists() else {}
with create_server(saved/'s',port=0,**options) as server:
 port=server.server_port;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 print(json.dumps({'origin':'http://127.0.0.1:'+str(port),'intake_id':summary['intake_id']}),flush=True)
 try:
  if sys.stdin.readline().strip()!='stop':raise ValueError('saved_host_stop_required')
 finally:server.shutdown();thread.join(10)
probe=socket.socket();probe.bind(('127.0.0.1',port));probe.close()
print(json.dumps({'resource':{'loop_stopped':not thread.is_alive(),'listener_closed':server.socket.fileno()==-1,'port_rebind':True,'new_runtime_calls':0,'actual_model_calls':0,'hardware_calls':0}}),flush=True)
`;
function unifiedTypedFixture(id,revision){
  const report={schema_version:1,kind:'virtual_fleet_harness_result',run_id:'typed-fixture-run',runtime_instance_id:'typed-fixture-runtime',synthetic:true,hardware_verified:false,ai_model_called:false,policy:{kind:'fixture',id:'typed-coexist'},termination:{reason:'policy_stop',policy_claim:'completed'},task_outcome:'not_assessed',cleanup:{status:'not_assessed',evidence_refs:[]},usage:{decisions:0,logical_requests:0,transport_retries:0,tick_delta:0,reserved_ticks:0,elapsed_ms:0},evidence:{measurement_refs:['typed-fixture-event'],operator_transcript_ref:'typed-fixture-journal'},unresolved_request_ids:[],assessment:{status:'not_assessed',verdict:null,evaluator_id:null,evidence_refs:[],summary_code:null}};
  return {schema_version:1,intake_id:id,current_revision:revision,storage_available:true,more_available:false,records:[{request_id:'TYPED-FIXTURE-COEXIST',intake_id:id,revision,readiness_fingerprint:'a'.repeat(64),recipe_id:'conducted_sensor_fixture_v1',run_id:report.run_id,runtime_instance_id:report.runtime_instance_id,state:'completed',source_current:true,source_synthetic:true,synthetic:true,hardware_verified:false,ai_model_called:false,resumable:false,case_id:null,plan_id:null,error_code:null,report}]};
}
async function unifiedProvidedFlowMain(){
  const indexFile=process.env.VLAB_UNIFIED_FLOW_REPLAY_INDEX;assert.ok(indexFile&&path.isAbsolute(indexFile),'explicit saved-output replay index required; no runtime/provider fallback');
  const index=JSON.parse(fs.readFileSync(indexFile,'utf8'));assert.equal(index.kind,'explicit_own_saved_authored_outputs');assert.equal(index.new_runtime_calls,0);
  const observations=[],faults=[],resources=[];let browser;
  const model=await import(require('node:url').pathToFileURL(path.join(ROOT,'frontend/intake_flow_model.mjs')).href);
  const recordFault=value=>{faults.push(value);const file=path.join(OUTPUT,'typed-progress.jsonl');proofWrite(file,(fs.existsSync(file)?fs.readFileSync(file,'utf8'):'')+JSON.stringify(value)+'\n');};
  try{
    browser=await chromium.launch({headless:true});
    for(const entry of index.cases){
      assert.ok(path.isAbsolute(entry.output));const summary=JSON.parse(fs.readFileSync(path.join(entry.output,'public-summary.json'),'utf8'));
      const host=startPreviewHost(entry.output,unifiedSavedHost,'unified_saved_host.py');let info;
      try{
        info=await host.next();proofWrite(path.join(OUTPUT,entry.name+'-host-startup.json'),JSON.stringify({...info,saved_output:entry.output,new_runtime_calls:0}));const bodies={};
        for(const [name,url]of [['intakes','/api/intakes'],['plan','/api/intakes/'+info.intake_id+'/conducted-plan-preview'],['result','/api/intakes/'+info.intake_id+'/conducted-result']]){
          const response=await fetch(info.origin+url),raw=Buffer.from(await response.arrayBuffer());proofWrite(path.join(OUTPUT,entry.name+'-'+name+'.json'),raw);bodies[name]={status:response.status,value:JSON.parse(raw)};
        }
        for(const width of [390,1440]){
          const context=await browser.newContext({viewport:{width,height:950}}),page=await context.newPage(),errors=[],external=[],methods=[];page.setDefaultTimeout(8000);
          page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!request.url().startsWith(info.origin+'/'))external.push(request.url());if(request.url().includes('/api/'))methods.push(request.method());});
          const root=page.locator('#intake-workflow'),part=id=>root.locator('[data-workflow-step="'+id+'"] [data-workflow-summary]');
          const planURL=info.origin+'/api/intakes/'+info.intake_id+'/conducted-plan-preview',resultURL=info.origin+'/api/intakes/'+info.intake_id+'/conducted-result',intakesURL=info.origin+'/api/intakes';
          const idle=()=>page.waitForFunction(()=>!document.querySelector('#refresh').disabled&&document.querySelector('#intake-gap-queue')?.dataset.pending==='false'&&!document.querySelector('#fixture-refresh')?.disabled);
          const current=()=>page.waitForFunction(()=>document.querySelector('#intake-workflow')?.dataset.providedScope==='current');
          const refresh=async()=>{await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await page.locator('#refresh').click();await idle();};
          const previous=()=>root.locator('[data-workflow-previous]').allTextContents();
          try{
            await page.goto(info.origin+'/#'+info.intake_id);await root.waitFor();await idle();assert.equal(await root.locator('[data-workflow-step]').count(),7);
            if(entry.name==='normal'){
              await current();const original=JSON.parse(fs.readFileSync(path.join(entry.output,'finalizer-original.json'),'utf8')).result;
              assert.equal(bodies.result.status,200);assert.equal(bodies.result.value.relation.status,'matched');assert.deepEqual(bodies.result.value.result,original);
              assert.ok((await part('plan').innerText()).includes('ready_for_simulation'));assert.ok((await part('virtual').innerText()).includes(original.binding.run_id));assert.ok((await part('measurement').innerText()).includes('-19.5 / dBm'));assert.ok((await part('measurement').innerText()).includes('not_assessed'));
              assert.ok(!(await part('virtual').locator('[data-workflow-summary-label]').innerText()).includes('선택한 가상 기록 없음'));assert.ok(!(await part('measurement').locator('[data-workflow-summary-label]').innerText()).includes('게시된 측정 근거 미확인'));
              const assessment=await part('assessment').innerText();assert.ok(assessment.includes('저장 완료 marker·DRAFT 검증 미확인')&&assessment.includes('실제 AI 호출 여부 unknown')&&assessment.includes('정리·독립평가 미확인'));assert.ok(!assessment.includes('ai_model_called=false'));
              await part('virtual').scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'unified-normal-'+width+'.png'));
              const layout=await root.locator('[data-workflow-summary]').evaluateAll(nodes=>nodes.map(node=>({left:node.getBoundingClientRect().left,right:node.getBoundingClientRect().right,client:node.clientWidth,scroll:node.scrollWidth,viewport:innerWidth})));
              proofWrite(path.join(OUTPUT,'unified-layout-'+width+'.json'),JSON.stringify(layout));assert.ok(layout.every(box=>box.left>=-1&&box.right<=box.viewport+1&&box.scroll<=box.client+1),'summary must fit its mobile card without internal clipping');

              const fixture=unifiedTypedFixture(info.intake_id,summary.revision);model.validateFixtureRuns(fixture,{intake_id:info.intake_id,revision:summary.revision});proofWrite(path.join(OUTPUT,'typed-fixture-'+width+'.json'),JSON.stringify(fixture));
              await page.route(info.origin+'/api/intakes/'+info.intake_id+'/fixture-runs',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(fixture)}));await refresh();await current();
              assert.ok((await part('virtual').innerText()).includes('typed-fixture-run'));assert.ok((await part('virtual').innerText()).includes('기존 fixture: 실행 기록 저장'));assert.ok((await part('virtual').innerText()).includes(original.binding.run_id));assert.ok((await part('assessment').innerText()).includes('기존 fixture: 이 가상 실행의 실제 AI 호출 없음'));await part('virtual').scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'unified-typed-coexist-'+width+'.png'));recordFault({width,fault:'typed-fixture-coexist',scope:'typed fixture API projection alongside genuine saved provided snapshot; not another actual fixture execution'});
              await page.route(resultURL,route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":{"code":"intake_conducted_result_missing"}}'}));await refresh();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await part('virtual').innerText()).includes('typed-fixture-run'));recordFault({width,fault:'typed-fixture-only-result-unavailable',scope:'typed HTTP availability; fixture identity retained independently'});await page.unroute(resultURL);await page.unroute(info.origin+'/api/intakes/'+info.intake_id+'/fixture-runs');await refresh();await current();

              await page.route(resultURL,route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":{"code":"intake_conducted_result_missing"}}'}));await refresh();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await previous()).some(text=>text.includes(original.binding.measurement_ref)));recordFault({width,fault:'typed-result-HTTP503',scope:'last original provided observation kept in previous-only details'});await page.unroute(resultURL);await refresh();await current();
              await page.route(intakesURL,route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":{"code":"store_unavailable"}}'}));await refresh();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await previous()).some(text=>text.includes(original.binding.run_id)));recordFault({width,fault:'typed-parent-HTTP503',scope:'parent currentness retired; no fresh result promotion'});await page.unroute(intakesURL);await refresh();await current();

              let release,seen,finished,routeError;const hold=new Promise(resolve=>release=resolve),arrived=new Promise(resolve=>seen=resolve),handled=new Promise(resolve=>finished=resolve);await page.route(planURL,async route=>{seen();try{await hold;await route.fulfill({contentType:'application/json',body:JSON.stringify(bodies.plan.value)});}catch(error){routeError=error;}finally{finished();}});
              try{await page.locator('#conducted-plan-refresh').click();await arrived;assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await previous()).some(text=>text.includes(original.binding.run_id)));recordFault({width,fault:'typed-plan-pending',scope:'pending plan blocks provided summary until bound response is observed'});}finally{release();await handled;await page.unroute(planURL);}if(routeError)throw routeError;await current();

              const mismatched=structuredClone(bodies.plan.value);mismatched.context_sha256='f'.repeat(64);mismatched.plan_input.binding.context_sha256='f'.repeat(64);model.parseConductedPlanPreview(JSON.stringify(mismatched),{intake_id:info.intake_id,revision:summary.revision});proofWrite(path.join(OUTPUT,'typed-C1-mismatch-'+width+'.json'),JSON.stringify(mismatched));await page.route(planURL,route=>route.fulfill({contentType:'application/json',body:JSON.stringify(mismatched)}));await refresh();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await previous()).some(text=>text.includes(original.binding.run_id)));recordFault({width,fault:'typed-plan-C1-mismatch',scope:'valid-shaped typed C1 counterfactual only; original result/binding untouched'});await page.unroute(planURL);await refresh();await current();
              const partial=structuredClone(bodies.result.value);Object.assign(partial.result,{status:'incomplete',raw_measurement:null,failure:{code:'measurement_missing',field:'measurement_ref'},gaps:[{code:'measurement_missing',field:'measurement_ref',provided:null,blocking:true}]});Object.assign(partial.result.calculation,{corrected:null,raw_power_w:null,raw_reference_plane:null,correction_ledger:[]});model.parseConductedResultView(JSON.stringify(partial),{intake_id:info.intake_id,revision:summary.revision});proofWrite(path.join(OUTPUT,'typed-null-result-'+width+'.json'),JSON.stringify(partial));await page.route(resultURL,route=>route.fulfill({contentType:'application/json',body:JSON.stringify(partial)}));await refresh();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await previous()).some(text=>text.includes('미제공(null)')));recordFault({width,fault:'typed-incomplete-null',scope:'typed nullable partial result kept as blocked original, no zero/completion substitution'});await page.unroute(resultURL);await refresh();await current();
              const foreign=structuredClone(bodies.result.value);foreign.intake_id='I-OTHER';foreign.result.binding.run_id='FOREIGN-UNIFIED-SECRET';proofWrite(path.join(OUTPUT,'typed-other-intake-'+width+'.json'),JSON.stringify(foreign));await page.route(resultURL,route=>route.fulfill({contentType:'application/json',body:JSON.stringify(foreign)}));await refresh();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok(!(await root.textContent()).includes('FOREIGN-UNIFIED-SECRET'));recordFault({width,fault:'typed-other-intake',scope:'strict transport parser rejects foreign response; previous original remains separate'});await page.unroute(resultURL);await refresh();await current();
              await page.evaluate(()=>{const original=Object.getOwnPropertyDescriptor(Node.prototype,'textContent');window.__unifiedRestore=()=>Object.defineProperty(Node.prototype,'textContent',original);Object.defineProperty(Node.prototype,'textContent',{...original,set(value){if(value==='제공 측정·계산 기록')throw Error('typed unified render failure');return original.set.call(this,value);}});});
              try{await page.locator('#conducted-plan-refresh').click();await idle();assert.notEqual(await root.getAttribute('data-provided-scope'),'current');assert.ok((await root.textContent()).includes(original.binding.run_id));recordFault({width,fault:'typed-summary-render-failure',scope:'last summary retained with unconfirmed badges; no backend/model execution'});}finally{await page.evaluate(()=>{__unifiedRestore();delete window.__unifiedRestore;});}await refresh();await current();
            }else{
              assert.notEqual(await root.getAttribute('data-provided-scope'),'current');
              if(entry.name==='plan-blocked'){assert.ok((await part('plan').innerText()).includes('blocked'));assert.ok(!(await part('virtual').innerText()).includes('operator-loop-run:'));}
              if(['result-invalid','RF-disconnected'].includes(entry.name)){assert.ok((await part('measurement').innerText()).includes('invalid'));assert.ok((await previous()).some(text=>text.includes('미제공(null)')));}
              if(entry.name==='analysis-rejected')assert.ok((await part('plan').innerText()).includes('미관측'));
            }
            assert.equal(await root.locator('[data-workflow-summary] button,[data-workflow-summary] input,[data-workflow-summary] select,[data-workflow-summary] a').count(),0);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(method=>method==='GET'));
            observations.push({case:entry.name,width,origin:info.origin,scope:await root.getAttribute('data-provided-scope'),plan_HTTP:bodies.plan.status,result_HTTP:bodies.result.status,source:'genuine own saved Store/original startup replay; new runtime0/model0',overflow:false});
          }finally{await context.close();}
        }
      }finally{
        if(info&&host.alive()){host.child.stdin.end('stop\n');const resource=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(resource.resource.loop_stopped&&resource.resource.listener_closed&&resource.resource.port_rebind);resources.push({case:entry.name,...resource.resource,child_exit:code});}
        else{if(host.alive())host.child.kill();await host.exited;}
      }
    }
    proofWrite(path.join(OUTPUT,'unified-results.json'),JSON.stringify({status:'pass',observations,typed_faults:faults,resources,new_runtime_calls:0,actual_model_calls:0,hardware_calls:0},null,2));console.log(JSON.stringify({status:'pass',genuine_DOM:observations.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'unified-failure.json'),JSON.stringify({status:'fail',message:error.message,observations,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}

// Requires an accepted genuine backend and explicit own saved inputs. No seed,
// model, runtime, writer, or fallback fixture is constructed by this observer.
const artifactStorageHost=String.raw`
import sys,json,threading,socket,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from labflow.ui_server import create_server
spec=json.loads(Path(sys.argv[2]).read_bytes());proof=Path(spec['proof_root']).resolve()
proof.relative_to(Path(sys.argv[1]).resolve()/'.local')
def save(name,value):
 raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8');target=proof/name;target.resolve().relative_to(proof)
 files=[p for p in proof.rglob('*') if p.is_file()]
 assert len(files)+(not target.exists())<=512 and sum(p.stat().st_size for p in files)-(target.stat().st_size if target.exists() else 0)+len(raw)<=33554432
 target.write_bytes(raw)
 return dict(path=str(target),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def snapshot():
 rows=[]
 for supplied in spec['source_roots']:
  root=Path(supplied);assert root.is_absolute() and root.exists() and not root.is_symlink()
  for p in sorted(root.rglob('*') if root.is_dir() else [root]):
   assert not p.is_symlink()
   if p.is_file():
    stat=p.stat();raw=p.read_bytes();rows.append(dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mtime_ns=stat.st_mtime_ns))
 return rows
before=snapshot();before_pin=save(spec['native_prefix']+'-native-before.json',before)
thread=server=None;port=None
try:
 options=json.loads(Path(spec['original_startup_file']).read_bytes()) if 'original_startup_file' in spec else spec['server_options']
 with create_server(Path(spec['workspace']),port=0,**options) as server:
  port=server.server_port;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  print(json.dumps(dict(origin='http://127.0.0.1:'+str(port),intake_id=spec['intake_id'],before_pin=before_pin)),flush=True)
  try:
   if sys.stdin.readline().strip()!='stop':raise ValueError('artifact_storage_observer_stop_required')
  finally:server.shutdown();thread.join(10)
finally:
 after=snapshot();after_pin=save(spec['native_prefix']+'-native-after.json',after)
 if port is not None:
  probe=socket.socket();probe.bind(('127.0.0.1',port));probe.close()
  resource=dict(loop_stopped=not thread.is_alive(),listener_closed=server.socket.fileno()==-1,port_rebind=True,source_unchanged=before==after,before_pin=before_pin,after_pin=after_pin,new_runtime_calls=0,actual_model_calls=0,hardware_calls=0)
  print(json.dumps(dict(resource=resource)),flush=True)
`;
async function artifactStorageViewMain(){
  const indexFile=process.env.VLAB_ARTIFACT_STORAGE_REPLAY_INDEX;assert.ok(indexFile&&path.isAbsolute(indexFile),'explicit accepted-backend replay index required');
  const index=JSON.parse(fs.readFileSync(indexFile,'utf8'));assert.equal(index.kind,'explicit_own_saved_artifact_readback');assert.equal(index.backend_accepted,true);assert.equal(index.new_runtime_calls,0);
  const model=await import(require('node:url').pathToFileURL(path.join(ROOT,'frontend/intake_flow_model.mjs')).href),encode=model.conductedPreviewValue;
  const observations=[],faults=[],resources=[];let browser;
  const recordFault=(width,fault,detail={})=>{faults.push({width,fault,scope:'typed UI/transport counterfactual; no genuine reader outcome inferred',...detail});proofWrite(path.join(OUTPUT,'typed-progress.json'),JSON.stringify(faults,null,2));};
  try{
    browser=await chromium.launch({headless:true});
    for(const entry of index.cases){
      assert.match(entry.name,/^[A-Za-z0-9_-]{1,64}$/);assert.ok(path.isAbsolute(entry.workspace)&&Array.isArray(entry.source_roots)&&entry.source_roots.length>0);
      const specFile=path.join(OUTPUT,entry.name+'-host-spec.json');proofWrite(specFile,JSON.stringify({...entry,proof_root:PROOF,native_prefix:path.relative(PROOF,OUTPUT)+'/'+entry.name}));const host=startPreviewHost(specFile,artifactStorageHost,'artifact_storage_host.py');let info,firstFailure=null;
      try{
        info=await host.next();const url=info.origin+'/api/intakes/'+encodeURIComponent(info.intake_id)+'/conducted-artifact-readback',planURL=info.origin+'/api/intakes/'+encodeURIComponent(info.intake_id)+'/conducted-plan-preview';
        const bodies={};for(const [name,suffix]of [['intakes','/api/intakes'],['plan','/api/intakes/'+info.intake_id+'/conducted-plan-preview'],['result','/api/intakes/'+info.intake_id+'/conducted-result'],['storage',url.slice(info.origin.length)]]){
          const response=await fetch(info.origin+suffix),raw=Buffer.from(await response.arrayBuffer());proofWrite(path.join(OUTPUT,entry.name+'-'+name+'.json'),raw);bodies[name]={status:response.status,raw};
        }
        const intake=JSON.parse(bodies.intakes.raw).intakes.find(x=>x.intake_id===info.intake_id);assert.ok(intake);
        const genuine=bodies.storage.status===200?model.parseConductedArtifactReadback(bodies.storage.raw.toString('utf8'),intake):null;
        assert.equal(bodies.storage.status,entry.expected_http);if(genuine)assert.equal(genuine.status,entry.expected_relation);
        for(const width of [390,1440]){
          const context=await browser.newContext({viewport:{width,height:950}}),page=await context.newPage(),errors=[],external=[],methods=[];page.setDefaultTimeout(8000);
          page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/'))methods.push(r.method());});
          const card=page.locator('#conducted-artifact-storage'),idle=()=>page.waitForFunction(()=>!document.querySelector('#refresh').disabled&&document.querySelector('#conducted-artifact-storage')?.dataset.pending==='false'&&document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');
          const refresh=async()=>{await idle();await page.locator('#conducted-artifact-refresh').click();await idle();};
          const parentRefresh=async()=>{await page.locator('#refresh').click();await idle();};
          const current=()=>page.waitForFunction(()=>document.querySelector('#conducted-artifact-storage')?.dataset.current==='true');
          const reset=async()=>{await page.unroute(url);await refresh();await current();};
          try{
            await page.goto(info.origin+'/#'+info.intake_id);await card.waitFor();await idle();assert.equal(await page.locator('[data-workflow-step]').count(),7);
            assert.equal(await card.getAttribute('data-current'),String(entry.expected_current));
            if(genuine?.artifact&&genuine.relation.artifact_binding.intake_id===intake.intake_id){assert.equal(await card.locator('[data-artifact-raw="draft"]').textContent(),genuine.artifact.draft);assert.equal(await card.getAttribute('data-result-status'),genuine.artifact.result.status);}
            const judgement=card.locator('[data-artifact-judgement]'),decisionText=await judgement.innerText();assert.ok(decisionText.includes('현재 관계')&&decisionText.includes('판정')&&decisionText.includes('미평가(not_assessed)')&&decisionText.includes('미확인(unknown)'));
            if(genuine?.artifact&&genuine.relation.artifact_binding.intake_id===intake.intake_id){assert.ok(decisionText.includes('3파일 일치'));assert.ok(!decisionText.includes(genuine.artifact.storage.manifest_sha256));assert.equal(await card.locator('[data-artifact-raw="draft"]').evaluate(node=>node.closest('details').open),false);if(genuine.artifact.result.status==='invalid')assert.ok(decisionText.includes('측정 무효'));}
            assert.ok((await card.innerText()).includes('게시 순서'));assert.ok((await page.locator('[data-workflow-step="assessment"] [data-workflow-summary]').innerText()).includes('실제 AI 호출 여부 unknown'));
            await card.scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,entry.name+'-'+width+'.png'));
            const layout=await card.evaluate(node=>({left:node.getBoundingClientRect().left,right:node.getBoundingClientRect().right,client:node.clientWidth,scroll:node.scrollWidth,viewport:innerWidth}));proofWrite(path.join(OUTPUT,entry.name+'-'+width+'-layout.json'),JSON.stringify(layout));assert.ok(layout.left>=-1&&layout.right<=width+1&&layout.scroll<=layout.client+1);
            observations.push({case:entry.name,width,HTTP:bodies.storage.status,relation:genuine?.status??null,current:entry.expected_current,scope:'genuine accepted D1 GET + production DOM; saved synthetic inputs, no new model/runtime/writer',overflow:false});
            if(entry.typed_faults&&entry.expected_current){
              const typed=async(name,mutate,{valid=true,expectedCurrent=false,check=async()=>{}}={})=>{
                const packet=structuredClone(genuine);mutate(packet);const raw=encode(packet);if(valid)model.parseConductedArtifactReadback(raw,intake);else assert.throws(()=>model.parseConductedArtifactReadback(raw,intake));
                proofWrite(path.join(OUTPUT,'typed-'+name+'-'+width+'.json'),raw);await page.route(url,r=>r.fulfill({contentType:'application/json',body:raw}));await refresh();assert.equal(await card.getAttribute('data-current'),String(expectedCurrent));await check();recordFault(width,name);await reset();
              };
              await page.route(url,r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'conducted_result_artifact_read_input_changed'}})}));await refresh();assert.equal(await card.getAttribute('data-current'),'false');assert.equal(await card.locator('[data-artifact-raw="draft"]').textContent(),genuine.artifact.draft);recordFault(width,'reader-error-retains-previous');await reset();
              await typed('unknown-key',p=>p.extra=true,{valid:false});
              await typed('stale-recheck',p=>{p.status=p.relation.status='stale';p.relation.recheck.status='changed';p.relation.recheck.analysis_sha256_after='5'.repeat(64);p.relation.reasons=['current_analysis_changed'];});
              await typed('different-plan',p=>{p.status=p.relation.status='different_plan';p.artifact.result.binding.plan_input.binding.plan_sha256='5'.repeat(64);p.relation.artifact_binding.plan_sha256='5'.repeat(64);p.relation.fields.plan_sha256=false;p.relation.reasons=['artifact_plan_sha256_mismatch'];});
              await typed('foreign-artifact',p=>{p.status=p.relation.status='different_intake';p.artifact.result.binding.plan_input.binding.intake_id='I-TYPED-FOREIGN-STORAGE';p.relation.artifact_binding.intake_id='I-TYPED-FOREIGN-STORAGE';p.relation.fields.intake_id=false;p.relation.reasons=['artifact_intake_id_mismatch'];p.artifact.selection.artifact_name=p.artifact.manifest.artifact_name='TYPED-FOREIGN-STORAGE';},{check:async()=>{assert.equal(await card.locator('[data-artifact-raw="draft"]').count(),0);assert.ok(!(await card.textContent()).includes('TYPED-FOREIGN-STORAGE'));}});
              await typed('invalid-measurement',p=>{p.artifact.result.status=p.artifact.manifest.result_status='invalid';p.artifact.result.raw_measurement=null;p.artifact.result.calculation.corrected=null;p.artifact.result.failure={code:'measurement_invalid',field:'measurement_ref'};},{expectedCurrent:true,check:async()=>{assert.equal(await card.getAttribute('data-result-status'),'invalid');assert.ok((await card.textContent()).includes('미제공(null)'));}});
              await typed('draft-text-only',p=>{p.artifact.draft+='\n<script>window.__artifactExecuted=true</script>';p.artifact.manifest.files[1].bytes=Buffer.byteLength(p.artifact.draft);},{expectedCurrent:true,check:async()=>{assert.match(await card.locator('[data-artifact-raw="draft"]').textContent(),/<script>/);assert.equal(await page.evaluate(()=>window.__artifactExecuted),undefined);}});
              const plan=JSON.parse(bodies.plan.raw);plan.context_sha256=plan.plan_input.binding.context_sha256='5'.repeat(64);await page.route(planURL,r=>r.fulfill({contentType:'application/json',body:JSON.stringify(plan)}));await parentRefresh();assert.equal(await card.getAttribute('data-current'),'false');recordFault(width,'plan-C1-mismatch');await page.unroute(planURL);await parentRefresh();await current();
              let seen,release,completed;const started=new Promise(r=>seen=r),hold=new Promise(r=>release=r),finished=new Promise(r=>completed=r);let first=true,lateError=null;
              await page.route(url,async route=>{if(!first)return route.continue();first=false;seen();await hold;try{const late=structuredClone(genuine);late.artifact.draft+='\nLATE_STORAGE_GENERATION';late.artifact.manifest.files[1].bytes=Buffer.byteLength(late.artifact.draft);await route.fulfill({contentType:'application/json',body:encode(late)});}catch(error){lateError=error.message;}finally{completed();}});
              try{await page.locator('#conducted-artifact-refresh').click();await started;await page.waitForFunction(()=>document.querySelector('#conducted-artifact-storage')?.dataset.pending==='true');await page.locator('#refresh').click();await idle();await current();}
              finally{release();await finished;await page.unroute(url);}assert.ok(!(await card.textContent()).includes('LATE_STORAGE_GENERATION'));recordFault(width,'late-prior-generation-excluded',{route_observation_error:lateError});
              await page.locator('[data-view="notifications"]').click();assert.equal(await card.getAttribute('data-current'),'false');await page.locator('[data-view="intakes"]').click();await idle();await current();recordFault(width,'hide-cancels-and-resumes-separate-source');
              await page.evaluate(()=>{const original=Object.getOwnPropertyDescriptor(Node.prototype,'textContent');window.__storageTextRestore=()=>Object.defineProperty(Node.prototype,'textContent',original);Object.defineProperty(Node.prototype,'textContent',{...original,set(value){if(typeof value==='string'&&value.startsWith('# Conducted result DRAFT'))throw Error('typed storage render failure');return original.set.call(this,value);}});});
              try{await refresh();assert.equal(await card.getAttribute('data-current'),'false');assert.equal(await card.locator('[data-artifact-raw="draft"]').textContent(),genuine.artifact.draft);assert.match(await card.locator('[data-artifact-relation-summary]').textContent(),/확인 불가/);assert.doesNotMatch(await card.locator('[data-artifact-judgement]').innerText(),/확인 · 이 조회 시점/);recordFault(width,'render-failure-preserves-previous');}finally{await page.evaluate(()=>{__storageTextRestore();delete window.__storageTextRestore;});}await refresh();await current();
              await page.route(url,r=>r.fulfill({contentType:'application/json',body:Buffer.from([0xff])}));await refresh();assert.equal(await card.getAttribute('data-current'),'false');recordFault(width,'invalid-UTF8-retains-previous');await reset();
              const oversize=model.CONDUCTED_ARTIFACT_HTTP_BYTES+1,oversizeFile=path.join(OUTPUT,'typed-oversize-zero-body.bin');if(!fs.existsSync(oversizeFile))proofWrite(oversizeFile,Buffer.alloc(oversize));
              await page.evaluate(({endpoint,size})=>{const original=window.fetch;window.__storageFetchOriginal=original;window.__storageCanceled=false;window.__storageTypedCalls=0;window.fetch=(input,options)=>{if(String(input).endsWith(endpoint)){window.__storageTypedCalls++;return Promise.resolve(new Response(new ReadableStream({start(c){c.enqueue(new Uint8Array(size));},cancel(){window.__storageCanceled=true;}}),{headers:{'Content-Type':'application/json'}}));}return original(input,options);};},{endpoint:new URL(url).pathname,size:oversize});
              try{await refresh();assert.equal(await card.getAttribute('data-current'),'false');assert.deepEqual(await page.evaluate(()=>[window.__storageCanceled,window.__storageTypedCalls]),[true,1]);recordFault(width,'stream-cap-cancel-no-auto-retry');}finally{await page.evaluate(()=>{window.fetch=window.__storageFetchOriginal;delete window.__storageFetchOriginal;});}await refresh();await current();
            }
            assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(x=>x==='GET'));
          }finally{await context.close();}
        }
      }catch(error){firstFailure=error;throw error;}finally{
        try{
          if(info&&host.alive()){host.child.stdin.end('stop\n');const item=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(item.resource.loop_stopped&&item.resource.listener_closed&&item.resource.port_rebind&&item.resource.source_unchanged);resources.push({case:entry.name,...item.resource,child_exit:code});}
          else{if(host.alive())host.child.kill();await host.exited;}
        }catch(error){resources.push({case:entry.name,cleanup_observation_error:error.message,cleanup_verified:false,first_error_preserved:Boolean(firstFailure)});if(!firstFailure)throw error;}
      }
    }
    proofWrite(path.join(OUTPUT,'artifact-storage-results.json'),JSON.stringify({status:'pass',observations,typed_faults:faults,resources,new_runtime_calls:0,actual_model_calls:0,hardware_calls:0},null,2));console.log(JSON.stringify({status:'pass',genuine_DOM:observations.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'artifact-storage-failure.json'),JSON.stringify({status:'fail',message:error.message,observations,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}

async function artifactStorageKeyboardMain(){
  const indexFile=process.env.VLAB_ARTIFACT_STORAGE_KEYBOARD_INDEX;assert.ok(indexFile&&path.isAbsolute(indexFile),'explicit keyboard saved-input index required');
  const index=JSON.parse(fs.readFileSync(indexFile,'utf8'));assert.equal(index.kind,'explicit_own_saved_artifact_readback');assert.equal(index.backend_accepted,true);assert.equal(index.new_runtime_calls,0);assert.deepEqual(index.cases.map(x=>x.name),['normal','measurement-invalid']);
  const model=await import(require('node:url').pathToFileURL(path.join(ROOT,'frontend/intake_flow_model.mjs')).href),flows=[],resources=[];let browser;
  const record=()=>proofWrite(path.join(OUTPUT,'keyboard-progress.json'),JSON.stringify({flows,resources},null,2));
  try{
    browser=await chromium.launch({headless:true});
    for(const entry of index.cases){
      const flow={case:entry.name,width:1440,scope:'genuine saved-input native keyboard flow; refresh failure alone is typed HTTP503',steps:[],issues:[]};flows.push(flow);
      const specFile=path.join(OUTPUT,entry.name+'-host-spec.json');proofWrite(specFile,JSON.stringify({...entry,proof_root:PROOF,native_prefix:path.relative(PROOF,OUTPUT)+'/'+entry.name}));
      const host=startPreviewHost(specFile,artifactStorageHost,'keyboard_storage_host.py');let info,firstFailure=null;
      try{
        info=await host.next();const url=info.origin+'/api/intakes/'+encodeURIComponent(info.intake_id)+'/conducted-artifact-readback';
        const direct=await fetch(url),raw=Buffer.from(await direct.arrayBuffer());proofWrite(path.join(OUTPUT,entry.name+'-genuine-storage.json'),raw);assert.equal(direct.status,200);
        const packet=model.parseConductedArtifactReadback(raw.toString('utf8'),{intake_id:entry.intake_id,revision:entry.server_options.conducted_artifact_readback_inputs.expected_revision});assert.equal(packet.status,'matched');
        const context=await browser.newContext({viewport:{width:1440,height:950}}),page=await context.newPage(),errors=[],external=[],methods=[];page.setDefaultTimeout(8000);let pointerEvents=0;
        await page.addInitScript(()=>{window.__keyboardPointerEvents=0;addEventListener('pointerdown',()=>window.__keyboardPointerEvents++);});
        page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/'))methods.push(r.method());});
        const card=page.locator('#conducted-artifact-storage'),idle=()=>page.waitForFunction(()=>!document.querySelector('#refresh').disabled&&document.querySelector('#conducted-artifact-storage')?.dataset.pending==='false'&&document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');
        const tabTo=async(selector,reverse=false)=>{for(let tabs=0;tabs<180;tabs++){if(await page.evaluate(s=>document.activeElement?.matches(s),selector))return tabs;await page.keyboard.press(reverse?'Shift+Tab':'Tab');}throw Error('keyboard target unreachable: '+selector);};
        const focused=()=>page.evaluate(()=>({tag:document.activeElement?.tagName,id:document.activeElement?.id,text:document.activeElement?.textContent?.slice(0,100),connected:document.activeElement?.isConnected}));
        const saveStep=async(name,detail={})=>{flow.steps.push({name,focus:await focused(),...detail});record();};
        const originalDraft=()=>card.locator('[data-artifact-raw="draft"]').textContent();
        const originalResult=()=>card.locator('[data-artifact-raw="result"]').textContent();
        try{
          await page.goto(info.origin+'/');await idle();await page.waitForFunction(()=>document.querySelector('#conducted-artifact-storage')?.dataset.current==='true');
          const selectTabs=await tabTo('#intake-list button');await page.keyboard.press('Enter');assert.equal(await page.locator('#intake-list button[aria-current="true"]').count(),1);assert.equal((await focused()).id,'detail-title');await saveStep('keyboard-intake-selection',{tabs:selectTabs});
          const cardTabs=await tabTo('#conducted-artifact-refresh');assert.equal(await page.locator('#conducted-artifact-refresh').getAttribute('aria-disabled'),'false');await saveStep('keyboard-storage-card',{tabs:cardTabs});
          for(const [key,press]of [['draft','Enter'],['manifest','Space'],['facts-plan','Enter']]){
            const selector='#conducted-artifact-storage details:has([data-artifact-raw="'+key+'"]) > summary';await tabTo(selector);
            await page.keyboard.press(press);assert.equal(await page.locator(selector).evaluate(s=>s.parentElement.open),true);assert.equal(await page.locator(selector).getAttribute('role'),null);assert.equal(await page.locator(selector).getAttribute('aria-expanded'),null);await saveStep('keyboard-open-'+key,{native_summary:true,key:press});
            await page.keyboard.press(press);assert.equal(await page.locator(selector).evaluate(s=>s.parentElement.open),false);assert.equal(await page.locator(selector).evaluate(s=>document.activeElement===s),true);await saveStep('keyboard-close-'+key);
          }
          assert.equal(await originalDraft(),packet.artifact.draft);const beforeResult=await originalResult();
          await tabTo('#conducted-artifact-refresh',true);await page.route(url,r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'conducted_result_artifact_read_input_changed'}})}));
          await page.keyboard.press('Enter');await idle();assert.equal(await card.getAttribute('data-current'),'false');assert.equal(await originalDraft(),packet.artifact.draft);assert.equal(await originalResult(),beforeResult);assert.match(await card.locator('[data-artifact-relation-summary]').textContent(),/확인 불가/);
          const failureFocus=await focused();if(failureFocus.id!=='conducted-artifact-refresh')flow.issues.push({code:'keyboard_refresh_focus_lost',observed:failureFocus,expected:'conducted-artifact-refresh'});await saveStep('typed-refresh-error-previous-observation',{scope:'typed503 only; original genuine values and native keyboard path unchanged'});await screenshot(page,path.join(OUTPUT,entry.name+'-keyboard-error.png'));await page.unroute(url);
          const backTabs=await tabTo('#intake-list button',true);await page.keyboard.press('Enter');assert.equal((await focused()).id,'detail-title');await saveStep('keyboard-return-same-intake',{tabs:backTabs});
          await tabTo('#conducted-artifact-refresh');await page.keyboard.press('Enter');await idle();await page.waitForFunction(()=>document.querySelector('#conducted-artifact-storage')?.dataset.current==='true');
          const recoveredFocus=await focused();if(recoveredFocus.id!=='conducted-artifact-refresh')flow.issues.push({code:'keyboard_recovery_focus_lost',observed:recoveredFocus,expected:'conducted-artifact-refresh'});
          assert.equal(await originalDraft(),packet.artifact.draft);assert.equal(await originalResult(),beforeResult);assert.match(await card.locator('[data-artifact-judgement]').innerText(),/not_assessed/);assert.match(await card.locator('[data-artifact-judgement]').innerText(),/unknown/);assert.equal(await card.getAttribute('data-result-status'),packet.artifact.result.status);
          if(entry.name==='measurement-invalid')assert.match(await card.locator('[data-artifact-judgement]').innerText(),/측정 무효[\s\S]*미제공\(null\)/);
          for(const other of index.cases.filter(x=>x.intake_id!==entry.intake_id))assert.ok(!(await card.textContent()).includes(other.intake_id));
          pointerEvents=await page.evaluate(()=>window.__keyboardPointerEvents);assert.equal(pointerEvents,0);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(x=>x==='GET'));
          await saveStep('keyboard-recovery-current',{pointer_events:pointerEvents,source_intake:packet.current.context.intake_id,original_result_status:packet.artifact.result.status,raw_and_draft_preserved:true});await screenshot(page,path.join(OUTPUT,entry.name+'-keyboard-current.png'));
          flow.status=flow.issues.length?'fail':'pass';flow.page_errors=errors;flow.pointer_events=pointerEvents;record();
        }finally{await context.close();}
      }catch(error){firstFailure=error;flow.status='error';flow.error=error.message;record();throw error;}finally{
        try{if(info&&host.alive()){host.child.stdin.end('stop\n');const item=await host.next(),code=await host.exited;assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(item.resource.loop_stopped&&item.resource.listener_closed&&item.resource.port_rebind&&item.resource.source_unchanged);resources.push({case:entry.name,...item.resource,child_exit:code});}else{if(host.alive())host.child.kill();await host.exited;}record();}
        catch(error){resources.push({case:entry.name,cleanup_verified:false,error:error.message,first_error_preserved:Boolean(firstFailure)});record();if(!firstFailure)throw error;}
      }
    }
    const status=flows.every(x=>x.status==='pass')?'pass':'fail';proofWrite(path.join(OUTPUT,'keyboard-results.json'),JSON.stringify({status,flows,resources,new_model_RF_runtime_calls:0,wide26_or_puretyped12_repeated:0,SQL_close_directly_instrumented:false},null,2));assert.equal(status,'pass','native keyboard focus gaps recorded');console.log(JSON.stringify({status,keyboard_flows:flows.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'keyboard-failure.json'),JSON.stringify({status:'fail',message:error.message,flows,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}

async function freshConductedOperatorMain(){
  const python=process.env.VLAB_FRESH_CONDUCTED_PYTHON,output=process.env.VLAB_FRESH_CONDUCTED_OUTPUT;
  assert.ok(python&&path.isAbsolute(python)&&fs.existsSync(python),'explicit root Python required');assert.ok(output&&path.isAbsolute(output),'explicit new short absolute output required');
  const saved=path.resolve(output);assert.ok(saved.startsWith(LOCAL+path.sep)&&!saved.startsWith(PROOF+path.sep)&&!PROOF.startsWith(saved+path.sep));assert.equal(fs.existsSync(saved),false,'never overwrite/reuse an output, including a failed one');FRESH_OUTPUT_ROOTS.push(saved);
  const args=['-B','-X','utf8','-m','labflow.intake_fixture_check','--conducted-workflow','--document-kind','pdf','--measurement-ref','event:17','--mock-model','gpt-6.1-sol','--output',saved];
  let browser,host,info,firstFailure=null;const resources=[],observations=[];
  const cliRecord={executable:python,argv:args,cwd:ROOT,with_port:false,timeout_ms:240000,max_output_buffer_bytes:2097152,generation_attempts:1,known_authored_fixture:true,actual_model_calls:0};
  try{
    proofWrite(path.join(OUTPUT,'generation-intent.json'),JSON.stringify(cliRecord,null,2));
    const child=spawnSync(python,args,{cwd:ROOT,windowsHide:true,timeout:240000,maxBuffer:2097152,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONPATH:ROOT}});
    // Retain exit and literal streams before attempting to parse any CLI data.
    proofWrite(path.join(OUTPUT,'generation.stdout.bin'),child.stdout||Buffer.alloc(0));proofWrite(path.join(OUTPUT,'generation.stderr.bin'),child.stderr||Buffer.alloc(0));
    Object.assign(cliRecord,{pid:child.pid,status:child.status,signal:child.signal,error_code:child.error?.code??null});proofWrite(path.join(OUTPUT,'generation-child.json'),JSON.stringify(cliRecord,null,2));
    assert.equal(child.error,undefined,'original CLI launch/timeout/buffer failure retained');assert.equal(child.status,0,'original CLI failed; partial output retained, no retry');assert.equal(child.signal,null);
    const summary=JSON.parse(fs.readFileSync(path.join(saved,'public-summary.json'),'utf8'));assert.deepEqual(JSON.parse(child.stdout.toString('utf8')),summary);
    assert.equal(summary.kind,'conducted_intake_workflow_demo');assert.equal(summary.provider,'authored_scripted_mock');assert.equal(summary.synthetic,true);assert.equal(summary.ai_model_called,false);assert.equal(summary.hardware_verified,false);assert.equal(summary.physical_verified,false);
    assert.equal(summary.runtime_calls,1);assert.equal(summary.producer_calls,5);assert.equal(summary.fixture_acceptance,'pass');assert.equal(summary.result_status,'recorded');assert.equal(summary.storage_status,'complete');assert.equal(summary.draft_status,'DRAFT');assert.equal(summary.task_outcome,'not_assessed');assert.equal(summary.conformity,'not_assessed');
    const startupFile=path.join(saved,'server-startup-original.json'),startup=JSON.parse(fs.readFileSync(startupFile,'utf8')),readback=JSON.parse(fs.readFileSync(path.join(saved,'readback-inputs.json'),'utf8'));
    const selection=startup.conducted_artifact_readback_inputs;assert.equal(Object.keys(selection).length,10);assert.equal(Object.keys(readback).length,9);const expected={...selection};delete expected.intake_id;assert.deepEqual(readback,expected);
    assert.equal(selection.intake_id,summary.intake_id);assert.equal(selection.expected_revision,summary.revision);assert.equal(selection.expected_context_sha256,summary.context_sha256);assert.equal(selection.artifact_workspace_root,saved);assert.equal(selection.run_id,summary.run_id);assert.equal(selection.runtime_instance_id,summary.runtime_instance_id);
    const original=JSON.parse(fs.readFileSync(path.join(saved,'finalizer-original.json'),'utf8')).result,facts=JSON.parse(fs.readFileSync(path.join(saved,'facts-plan-original.json'),'utf8')).plan_input.intake.facts;
    const fileRoot=path.join(saved,'.local','conducted-result-artifacts',selection.artifact_name),draft=fs.readFileSync(path.join(fileRoot,'draft.md'),'utf8'),mock=JSON.parse(fs.readFileSync(path.join(saved,'m','mock-origin.json'),'utf8'));
    const pins=Object.fromEntries(['public-summary.json','server-startup-original.json','readback-inputs.json','m/authored-mock.cs','m/codex.exe'].map(name=>{const raw=fs.readFileSync(path.join(saved,name));return [name,{bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}];}));
    proofWrite(path.join(OUTPUT,'generated-source-pins.json'),JSON.stringify({pins,mock,readback_keys:Object.keys(readback),generation:cliRecord,versions:{node:process.version,playwright:require('playwright/package.json').version},source:'known author fixture and newly generated local MOCK; actual model0'},null,2));
    const specFile=path.join(OUTPUT,'fresh-host-spec.json');proofWrite(specFile,JSON.stringify({name:'fresh',workspace:path.join(saved,'s'),intake_id:summary.intake_id,original_startup_file:startupFile,source_roots:[saved],proof_root:PROOF,native_prefix:path.relative(PROOF,OUTPUT)+'/fresh'}));
    host=startPreviewHost(specFile,artifactStorageHost,'fresh_original_startup_host.py');info=await host.next();
    const bodies={};for(const [name,suffix]of [['intakes','/api/intakes'],['plan','/api/intakes/'+summary.intake_id+'/conducted-plan-preview'],['provided','/api/intakes/'+summary.intake_id+'/conducted-result'],['storage','/api/intakes/'+summary.intake_id+'/conducted-artifact-readback']]){
      const response=await fetch(info.origin+suffix),raw=Buffer.from(await response.arrayBuffer());proofWrite(path.join(OUTPUT,'fresh-'+name+'.json'),raw);assert.equal(response.status,200);bodies[name]=JSON.parse(raw.toString('utf8'));
    }
    assert.deepEqual(bodies.provided.result,original);assert.deepEqual(bodies.storage.artifact.result,original);assert.equal(bodies.storage.artifact.draft,draft);assert.equal(bodies.storage.status,'matched');assert.equal(bodies.storage.relation.recheck.status,'unchanged');assert.deepEqual(bodies.storage.relation.current_binding,bodies.plan.plan_input.binding);assert.deepEqual(bodies.storage.relation.artifact_binding,bodies.plan.plan_input.binding);assert.equal(bodies.storage.artifact.storage.verified_file_count,3);
    browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:1440,height:950}}),page=await context.newPage(),errors=[],external=[],methods=[];page.setDefaultTimeout(8000);
    page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(info.origin+'/'))external.push(r.url());if(r.url().includes('/api/'))methods.push(r.method());});
    try{
      await page.goto(info.origin+'/');await page.waitForFunction(()=>document.querySelector('#conducted-artifact-storage')?.dataset.current==='true'&&document.querySelector('#conducted-plan-refresh')?.getAttribute('aria-disabled')==='false');
      await page.locator('#intake-list button[aria-current="true"]').click();const workflow=page.locator('#intake-workflow'),part=id=>workflow.locator('[data-workflow-step="'+id+'"] [data-workflow-summary]');assert.equal(await workflow.getAttribute('data-intake-id'),summary.intake_id);
      const intakeText=await part('intake').innerText();for(const field of ['product_type','market','purpose']){assert.ok(facts[field]?.value,'known author field absent');assert.ok(intakeText.includes(facts[field].value),'operator intake must show original '+field);}
      assert.equal(await page.locator('#conducted-plan-preview').getAttribute('data-preview-current'),'true');assert.match(await part('plan').innerText(),/ready_for_simulation/);
      const factSummary=page.locator('#conducted-plan-content summary').filter({hasText:'제품·목적·시장과 원 사실·질문'});await factSummary.click();assert.ok((await page.locator('#conducted-plan-content').innerText()).includes('SM-A176U'));await factSummary.click();
      assert.ok((await part('virtual').innerText()).includes(summary.run_id));assert.ok((await part('virtual').innerText()).includes(summary.runtime_instance_id));const measurementText=await part('measurement').innerText();assert.ok(measurementText.includes(String(summary.raw_measurement.packet.value))&&measurementText.includes(summary.raw_measurement.packet.unit)&&measurementText.includes(String(summary.corrected.value)));
      const card=page.locator('#conducted-artifact-storage');assert.equal(await card.getAttribute('data-current'),'true');const judgement=await card.locator('[data-artifact-judgement]').innerText();assert.match(judgement,/3파일 일치/);assert.match(judgement,/not_assessed/);assert.match(judgement,/unknown/);
      const sourceSummary=card.locator('details').first().locator('summary');await sourceSummary.click();assert.ok((await card.innerText()).includes(summary.run_id));assert.ok((await card.innerText()).includes(selection.expected_manifest_sha256));
      const draftSummary=card.locator('details:has([data-artifact-raw="draft"]) > summary');await draftSummary.click();assert.equal(await card.locator('[data-artifact-raw="draft"]').isVisible(),true);assert.equal(await card.locator('[data-artifact-raw="draft"]').textContent(),draft);await screenshot(page,path.join(OUTPUT,'fresh-operator-DRAFT-1440.png'));await draftSummary.click();await sourceSummary.click();
      await card.scrollIntoViewIfNeeded();await screenshot(page,path.join(OUTPUT,'fresh-operator-summary-1440.png'));assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(methods.every(x=>x==='GET'));
      observations.push({width:1440,source:'one generation CLI without port -> exact original startup readonly UI',known_author_fixture:true,intake_id:summary.intake_id,run_id:summary.run_id,runtime_instance_id:summary.runtime_instance_id,product_type:facts.product_type.value,purpose:facts.purpose.value,market:facts.market.value,original_raw:summary.raw_measurement,original_corrected:summary.corrected,storage_read:'fixed3 matched current relation observation',draft:'original UTF8 text',task:'not_assessed',conformity:'not_assessed',actual_AI_display:'unknown',typed_faults:0,versions:{node:process.version,chromium:browser.version()}});
    }finally{await context.close();}
  }catch(error){firstFailure=error;try{proofWrite(path.join(OUTPUT,'fresh-operator-failure.json'),JSON.stringify({status:'fail',message:error.message,cli:cliRecord,observations,resources,partial_output:saved,no_retry:true},null,2));}catch{console.error('fresh observer failure-receipt write also failed; first error retained');}throw error;}
  finally{
    let cleanupFailure=null;
    try{if(host?.alive()){host.child.stdin.end('stop\n');const item=await host.next(),code=await host.exited;assert.ok(info,'startup was not observed');assert.equal(code,0,host.stderr());assert.equal(host.stderr(),'');assert.ok(item.resource.loop_stopped&&item.resource.listener_closed&&item.resource.port_rebind&&item.resource.source_unchanged);resources.push({...item.resource,child_exit:code});}else if(host){const code=await host.exited;resources.push({child_exit:code,cleanup_verified:false});}}
    catch(error){resources.push({cleanup_verified:false,message:error.message,first_error_preserved:Boolean(firstFailure)});cleanupFailure=error;}
    try{if(browser)await browser.close();}catch(error){resources.push({browser_close_verified:false,message:error.message});cleanupFailure??=error;}
    try{proofWrite(path.join(OUTPUT,'fresh-operator-resources.json'),JSON.stringify(resources,null,2));}catch(error){cleanupFailure??=error;}
    if(!firstFailure&&cleanupFailure)throw cleanupFailure;
  }
  proofWrite(path.join(OUTPUT,'fresh-operator-results.json'),JSON.stringify({status:'pass',generation_cli:cliRecord,observations,resources,generation_MOCK_flows:1,generation_virtual_runtime_calls:1,generation_producer_calls:5,actual_model_calls:0,readonly_server_new_runtime_calls:0,CLI_port_branch_tested:false,SQL_close_directly_instrumented:false,prior_wide_or_unit_repeated:0},null,2));console.log(JSON.stringify({status:'pass',generation_CLI:1,genuine_DOM:1,output:OUTPUT,generated_output:saved}));
}

(process.env.VLAB_FRESH_CONDUCTED_OPERATOR_ONLY==='1'?freshConductedOperatorMain():process.env.VLAB_ARTIFACT_STORAGE_KEYBOARD_ONLY==='1'?artifactStorageKeyboardMain():process.env.VLAB_ARTIFACT_STORAGE_VIEW_ONLY==='1'?artifactStorageViewMain():process.env.VLAB_UNIFIED_PROVIDED_FLOW_ONLY==='1'?unifiedProvidedFlowMain():process.env.VLAB_GAP_QUEUE_ONLY==='1'?gapQueueMain():process.env.VLAB_CONDUCTED_RESULT_ONLY==='1'?conductedResultMain():process.env.VLAB_CONDUCTED_PREVIEW_ONLY==='1'?conductedPreviewMain():process.env.VLAB_WORKFLOW_ONLY==='1'?workflowMain():main()).catch(error=>{console.error(error);process.exitCode=1;});
