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
const OUTPUT=fs.mkdtempSync(path.join(proof,'first-twin-browser-'));
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
    const loaded = async page => page.locator('#fixture-status').filter({hasText:'가상 기록 조회 완료'}).waitFor();
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
            assert.equal(await workflow.locator('button,input,select,a').count(),0);assert.doesNotMatch(text,/FCC PASS|전체 업무 완료|실측 완료/);
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
(process.env.VLAB_WORKFLOW_ONLY==='1'?workflowMain():main()).catch(error=>{console.error(error);process.exitCode=1;});
