/* Completed-result UI checks using synthetic schema data; no harness/AI call. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '../..');
  const output = path.resolve(process.env.HARNESS_UI_EVIDENCE || require('../managed_paths.cjs').output(root,'fleet-harness'));
  fs.mkdirSync(output, {recursive: true});
  const python = process.env.VLAB_PYTHON || require('../managed_paths.cjs').python(root);
  const child = spawn(python, ['-m', 'frontend.virtual_fleet.harness_browser_fixture', '--port', '0'], {
    cwd: root, windowsHide: true, env: {...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8'}, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let browser;
  try {
    let log = '';
    const origin = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('fixture startup timeout: ' + log)), 10000);
      child.once('error', error => {clearTimeout(timeout); reject(error);});
      child.once('exit', code => {clearTimeout(timeout); reject(new Error('fixture exited ' + code + ': ' + log));});
      child.stderr.on('data', chunk => {log += chunk;});
      child.stdout.on('data', chunk => {log += chunk; const match = log.match(/http:\/\/127\.0\.0\.1:\d+/); if (match) {clearTimeout(timeout); resolve(match[0]);}});
    });
    browser = await chromium.launch({headless: true});
    const context = await browser.newContext({viewport: {width: 1512, height: 1100}});
    context.setDefaultTimeout(4000);
    const errors = []; context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
    const original = await (await context.request.get(origin + '/api/harness-result')).json();
    const checks = [];
    const check = async (name, run) => {await run(); checks.push(name); console.log('PASS ' + name);};
    const open = async payload => {
      const page = await context.newPage();
      if (payload !== undefined) await page.route('**/api/harness-result', route => route.fulfill({json: payload}));
      await page.goto(origin);
      return page;
    };
    const loaded = async page => page.locator('#harness-status').filter({hasText: '기록 조회 완료'}).waitFor();
    const state = async page => ({body: createHash('sha256').update(await page.locator('#harness-result-body').innerHTML()).digest('hex'), time: await page.locator('#harness-updated').innerText()});
    const page = await open();
    await check('policy claim not_assessed cleanup and fixture provenance remain separate', async () => {
      await loaded(page);
      const panel = page.locator('#harness-result-panel');
      assert.match(await panel.innerText(), /실제 AI 호출 없음/);
      assert.match(await panel.innerText(), /독립 평가 미실행/);
      assert.match(await panel.innerText(), /정책의 완료 주장/);
      assert.match(await panel.innerText(), /정리 상태 미평가/);
      assert.doesNotMatch(await page.locator('#harness-assessment').innerText(), /통과|PASS/);
      assert.equal(await panel.getByRole('button').count(), 1);
      assert.equal(await panel.locator('input, select, textarea').count(), 0);
    });
    await check('completed pass fail inconclusive and evaluator failure display independently', async () => {
      for (const [status, verdict, label] of [['completed', 'pass', '가상 시나리오 평가 통과'], ['completed', 'fail', '가상 평가 · 기준 불충족'], ['completed', 'inconclusive', '평가 완료 · 판정 불가'], ['failed', null, '평가기 오류']]) {
        const payload = structuredClone(original);
        payload.report.assessment = {status, verdict, evaluator_id: 'fixture:evaluation', evidence_refs: ['event:18'], summary_code: status === 'failed' ? 'evaluator_error' : 'fixture_assessed'};
        await page.route('**/api/harness-result', route => route.fulfill({json: payload}));
        await page.locator('#harness-refresh').click(); await loaded(page);
        assert.equal(await page.locator('#harness-assessment .report-badge').innerText(), label);
        assert.match(await page.locator('#harness-result-body').innerText(), /작업 결과 미평가/);
        await page.unroute('**/api/harness-result');
      }
    });
    await check('non-policy termination has no completion claim and preserves unresolved request', async () => {
      const payload = structuredClone(original); payload.report.termination = {reason: 'runtime_mutation_uncertain', policy_claim: null}; payload.report.unresolved_request_ids = ['operator:pending:7'];
      await page.route('**/api/harness-result', route => route.fulfill({json: payload}));
      await page.locator('#harness-refresh').click(); await loaded(page);
      assert.match(await page.locator('#harness-result-body').innerText(), /동작 반영 여부 미확인/);
      assert.match(await page.locator('#harness-result-body').innerText(), /정책 주장 없음/);
      assert.match(await page.locator('#harness-result-body').innerText(), /operator:pending:7/);
      await page.unroute('**/api/harness-result');
    });
    await check('current device mutation does not overwrite the historical result', async () => {
      const before = await state(page);
      await page.locator('#advance-ticks').fill('1'); await page.locator('#advance').click();
      await page.waitForFunction(() => document.querySelector('[data-metric="tick"]').textContent === '1');
      assert.deepEqual(await state(page), before);
      assert.match(await page.locator('#harness-result-panel').innerText(), /과거 실행 기록/);
    });
    await check('transport failure keeps last report and recovers with its own refresh', async () => {
      const before = await state(page);
      await page.route('**/api/harness-result', route => route.fulfill({status: 503, json: {error: {code: 'unavailable'}}}));
      await page.locator('#harness-refresh').click();
      await page.locator('#harness-status').filter({hasText: '마지막 성공 기록'}).waitFor();
      assert.deepEqual(await state(page), before);
      await page.unroute('**/api/harness-result');
      await page.locator('#harness-refresh').click(); await loaded(page);
    });
    await check('different run instance private injection and missing record do not replace success', async () => {
      const before = await state(page);
      for (const mutate of [p => {p.report.run_id = 'other-run';}, p => {p.report.runtime_instance_id = 'other-instance';}, p => {p.report.usage.seed = 'private';}, p => {p.report = null;}]) {
        const payload = structuredClone(original); mutate(payload);
        await page.route('**/api/harness-result', route => route.fulfill({json: payload}));
        await page.locator('#harness-refresh').click();
        await page.locator('#harness-status').filter({hasText: '마지막 성공 기록'}).waitFor();
        assert.deepEqual(await state(page), before);
        await page.unroute('**/api/harness-result');
      }
    });
    await check('malicious public text is displayed literally and never executes', async () => {
      const payload = structuredClone(original); payload.report.policy.id = '<img src=x onerror="window.harnessInjected=true">';
      await page.route('**/api/harness-result', route => route.fulfill({json: payload}));
      await page.locator('#harness-refresh').click(); await loaded(page);
      assert.match(await page.locator('#harness-result-body').innerText(), /<img src=x/);
      assert.equal(await page.locator('#harness-result-panel img, #harness-result-panel script').count(), 0);
      assert.equal(await page.evaluate(() => window.harnessInjected), undefined);
      await page.unroute('**/api/harness-result');
      await page.locator('#harness-refresh').click(); await loaded(page);
    });
    await check('renderer failure preserves report DOM update time and recovery', async () => {
      const before = await state(page);
      await page.evaluate(() => {window.harnessFormatter = Intl.DateTimeFormat; Intl.DateTimeFormat = function () {throw new Error('renderer failure');};});
      await page.locator('#harness-refresh').click();
      await page.locator('#harness-status').filter({hasText: '마지막 성공 기록'}).waitFor();
      assert.deepEqual(await state(page), before);
      await page.evaluate(() => {Intl.DateTimeFormat = window.harnessFormatter; delete window.harnessFormatter;});
      await page.locator('#harness-refresh').click(); await loaded(page);
    });
    await check('initial report failure remains separate from device success and null record', async () => {
      const failed = await context.newPage();
      await failed.route('**/api/harness-result', route => route.fulfill({status: 503, json: {error: {code: 'unavailable'}}}));
      await failed.goto(origin);
      await failed.locator('#harness-status').filter({hasText: '기록을 조회하지 못했습니다'}).waitFor();
      assert.equal(await failed.locator('[data-metric="profiles"]').innerText(), '7');
      assert.equal(await failed.locator('#harness-result-body').getByText('완료된 실행 기록이 없습니다.', {exact: true}).count(), 0);
      await failed.unroute('**/api/harness-result'); await failed.locator('#harness-refresh').click(); await loaded(failed); await failed.close();
      const empty = await open({schema_version: 1, report: null}); await loaded(empty);
      assert.match(await empty.locator('#harness-result-body').innerText(), /완료된 실행 기록이 없습니다/);
      await empty.close();
    });
    await check('late initial response cannot overwrite a newer successful record', async () => {
      const late = await context.newPage();
      let release, started; const gate = new Promise(resolve => {release = resolve;}); const begun = new Promise(resolve => {started = resolve;}); let calls = 0;
      await late.route('**/api/harness-result', async route => {
        calls++;
        if (calls === 1) {started(); await gate; const old = structuredClone(original); old.report.run_id = 'late-other-run'; await route.fulfill({json: old});}
        else await route.fulfill({json: original});
      });
      await late.goto(origin, {waitUntil: 'domcontentloaded'}); await begun;
      await late.locator('#harness-status').filter({hasText: '불러오는 중'}).waitFor();
      await late.locator('#harness-refresh').click(); await loaded(late);
      const before = await state(late);
      release();
      await late.waitForFunction(() => performance.getEntriesByType('resource').filter(entry => entry.name.endsWith('/api/harness-result')).length >= 2);
      await late.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert.deepEqual(await state(late), before);
      assert.match(await late.locator('#harness-status').innerText(), /기록 조회 완료/);
      await late.close();
    });
    await page.locator('#harness-result-panel').scrollIntoViewIfNeeded();
    await page.screenshot({path: path.join(output, 'harness-report-desktop.png')});
    await check('completed panel remains readable on mobile without page overflow', async () => {
      await page.setViewportSize({width: 390, height: 844});
      await page.locator('#harness-result-panel').scrollIntoViewIfNeeded();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.locator('#harness-refresh').focus(); assert.equal(await page.locator('#harness-refresh').evaluate(node => node === document.activeElement), true);
      await page.screenshot({path: path.join(output, 'harness-report-mobile.png'), fullPage: true});
    });
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'harness-ui-results.json'), JSON.stringify({synthetic: true, ai_model_called: false, checks}, null, 2));
    console.log(JSON.stringify({checks: checks.length, output}));
  } finally {if (browser) await browser.close(); child.kill();}
}
main().catch(error => {console.error(error); process.exitCode = 1;});
