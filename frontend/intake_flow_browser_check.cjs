/* Pure read UI acceptance. SQL/readiness doubles, no queue or runtime execution. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const ROOT=path.resolve(__dirname,'..'),LOCAL=path.join(ROOT,'.local');
fs.mkdirSync(LOCAL,{recursive:true});
const proof=process.env.VLAB_FLOW_PROOF_ROOT?fs.realpathSync(process.env.VLAB_FLOW_PROOF_ROOT):LOCAL;
assert.ok(proof===LOCAL||proof.startsWith(LOCAL+path.sep));
const OUTPUT=fs.mkdtempSync(path.join(proof,process.env.VLAB_CONDUCTED_PREVIEW_ONLY==='1'?'conducted-preview-browser-':'first-twin-browser-'));
const PROOF=proof===LOCAL?OUTPUT:proof;
function proofWrite(file,data){
  const target=path.resolve(file);assert.ok(target.startsWith(PROOF+path.sep));const files=[];
  const walk=dir=>{for(const entry of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(entry.isSymbolicLink(),false);const p=path.join(dir,entry.name);if(entry.isDirectory())walk(p);else if(entry.isFile())files.push(p);}};walk(PROOF);
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
   'adapter_path':str(Path(adapter.__file__).resolve()),'adapter_sha256':hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest()}),flush=True)
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
function startPreviewHost(mode){
  const file=path.join(OUTPUT,'preview_host.py');if(!fs.existsSync(file))proofWrite(file,previewHost);
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
  const observations=[],faults=[],resources=[];let browser;
  try{
    browser=await chromium.launch({headless:true});
    for(const mode of ['matched','missing','other','old-revision','basis-missing','text','non-synthetic','incomplete','unconfirmed-source']){
      const host=startPreviewHost(mode);let info;
      try{
        info=await host.next();assert.equal(info.adapter_sha256,'0286769450f4efef874602164b2bfdb5aa0ac2f027aa48fcc4c0a219f230ebc9');
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
    proofWrite(path.join(OUTPUT,'preview-results.json'),JSON.stringify({status:'pass',observations,typed_faults:faults,resources,actual_model_calls:0,hardware_calls:0},null,2));
    console.log(JSON.stringify({status:'pass',observations:observations.length,typed_faults:faults.length,output:OUTPUT}));
  }catch(error){proofWrite(path.join(OUTPUT,'preview-failure.json'),JSON.stringify({status:'fail',message:error.message,observations,typed_faults:faults,resources},null,2));throw error;}
  finally{if(browser)await browser.close();}
}
(process.env.VLAB_CONDUCTED_PREVIEW_ONLY==='1'?conductedPreviewMain():process.env.VLAB_WORKFLOW_ONLY==='1'?workflowMain():main()).catch(error=>{console.error(error);process.exitCode=1;});
