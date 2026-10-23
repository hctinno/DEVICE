/* Pure read UI acceptance. SQL/readiness doubles, no queue or runtime execution. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '..');
  const output = path.join(root, '.local/FLOW-003-IMPLEMENTATION/browser');
  fs.mkdirSync(output, {recursive:true});
  const python = process.env.VLAB_PYTHON || path.join(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  const child = spawn(python, ['-B', '-m', 'frontend.intake_flow_browser_fixture', '--port', '0'], {
    cwd:root, windowsHide:true, env:{...process.env, PYTHONUTF8:'1', PYTHONIOENCODING:'utf-8'}, stdio:['ignore','pipe','pipe'],
  });
  let browser;
  try {
    let log = '';
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
      await page.locator('#fixture-panel').screenshot({path:path.join(output,'intake-flow-desktop.png')});
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
      await sample.locator('#fixture-panel').screenshot({path:path.join(output,'intake-flow-mobile.png')});
      await sample.close();
    });
    { // Existing nine-check acceptance is counted separately from new checks.
      const result=await new Promise((resolve,reject)=>{
        const legacy=spawn(process.execPath,['frontend/browser_check.cjs'],{cwd:root,windowsHide:true,env:{...process.env,UI_DEMO_URL:origin,UI_EMPTY_URL:empty_origin},stdio:['ignore','pipe','pipe']});
        let text=''; legacy.stdout.on('data',chunk=>{text+=chunk;}); legacy.stderr.on('data',chunk=>{text+=chunk;});
        legacy.on('error',reject); legacy.on('exit',code=>resolve({code,text}));
      });
      fs.writeFileSync(path.join(output,'existing-browser.log'),result.text);
      assert.equal(result.code,0,result.text);
      console.log('PASS existing intake browser acceptance: 9 checks');
    }
    assert.deepEqual(errors,[]); assert.deepEqual(external,[]); assert(methods.every(method=>method==='GET'));
    fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:checks.length,legacyPassed:9,checks,pageErrors:errors,externalRequests:external,methods:[...new Set(methods)]},null,2));
    console.log(JSON.stringify({passed:checks.length,legacyPassed:9,evidence:output}));
  } finally {if (browser) await browser.close(); child.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
