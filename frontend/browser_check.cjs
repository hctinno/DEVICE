/* Optional browser acceptance checks. Run against the documented synthetic fixtures. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

async function main() {
  const base = process.env.UI_DEMO_URL || 'http://127.0.0.1:8765';
  const emptyBase = process.env.UI_EMPTY_URL || 'http://127.0.0.1:8766';
  const output = require('./managed_paths.cjs').output(path.resolve(__dirname,'..'),'frontend');
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true});
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const errors = [];
  const external = [];
  context.on('page', p => {
    p.on('pageerror', error => errors.push(error.message));
    p.on('request', request => {
      if (![base, emptyBase].some(url => request.url().startsWith(url + '/'))) external.push(request.url());
    });
  });
  const page = await context.newPage();
  const checks = [];
  try {
    await page.goto(emptyBase);
    await page.getByRole('heading', {name: '첫 접수를 기다리고 있습니다'}).waitFor();
    assert.equal(await page.locator('.metric strong').first().innerText(), '0');
    await page.screenshot({path: path.join(output, 'empty.png')});
    checks.push('empty store is distinct from load/error');

    await page.goto(base);
    await page.getByRole('heading', {name: '01 · 의뢰 확인 — 시장 충돌'}).waitFor();
    assert.equal(await page.locator('.metric strong').first().innerText(), '8');
    await page.getByText('합성 자료 · 개발 검증용', {exact: true}).waitFor();
    await page.getByText('의뢰 시장 정보가 서로 다릅니다. 적용할 값을 확인해 주세요.').first().waitFor();
    await page.screenshot({path: path.join(output, 'desktop.png')});
    await page.locator('.fact details summary').first().click();
    await page.getByText('제출된 후보 5개 · 충돌·불확실 포함', {exact: true}).click();
    const candidates = page.locator('details').filter({has: page.getByText('제출된 후보 5개 · 충돌·불확실 포함', {exact: true})});
    await candidates.locator('article').filter({hasText: '원문 HTML 안전 표시 확인'}).locator('summary').click();
    await page.getByText('<img src=x onerror="window.uiInjected=true"> 원문은 실행하지 않습니다.', {exact: true}).waitFor();
    assert.equal(await page.locator('#detail-panel img, #detail-panel script').count(), 0);
    assert.equal(await page.evaluate(() => window.uiInjected), undefined);
    await page.screenshot({path: path.join(output, 'source-evidence.png')});
    checks.push('real service, synthetic provenance, conflict, parser gap, source text/XSS');

    await page.locator('#filter').selectOption('failed');
    assert.equal(await page.locator('.intake-item').count(), 1);
    await page.getByRole('heading', {name: '03 · 분석 실패 — 재시도 한도'}).waitFor();
    await page.getByText('3회 시도', {exact: true}).waitFor();
    await page.locator('#filter').selectOption('deferred');
    await page.getByRole('heading', {name: '02 · 검토 보류 — 사용자 요청'}).waitFor();
    await page.locator('#filter').selectOption('waiting');
    assert.equal(await page.locator('.intake-item').count(), 2);
    await page.locator('#filter').selectOption('all');
    await page.locator('#search').fill('사용자 답변');
    await page.getByText('사용자 응답 이벤트: DEMO-ANSWER', {exact: true}).waitFor();
    await page.locator('#search').fill('없는 접수');
    await page.getByRole('heading', {name: '표시할 접수가 없습니다'}).waitFor();
    await page.locator('#search').fill('');
    await page.locator('.intake-item').first().focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#detail-title').evaluate(node => node === document.activeElement), true);
    checks.push('search, waiting/failure/defer filters, user answer provenance, keyboard navigation');

    await page.locator('[data-view="notifications"]').click();
    await page.getByRole('heading', {name: '저장된 알림 기록'}).waitFor();
    await page.getByRole('button', {name: '현재 접수 보기'}).first().click();
    assert.equal(await page.locator('#intake-view').isVisible(), true);
    checks.push('local notice history to current intake');

    await page.locator('#search').fill('시장 충돌');
    await page.setViewportSize({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await page.screenshot({path: path.join(output, 'mobile.png')});
    await page.locator('#detail-panel').evaluate(node => node.scrollIntoView({block: 'start'}));
    await page.screenshot({path: path.join(output, 'mobile-detail.png')});
    checks.push('390px responsive layout without horizontal overflow');

    await page.setViewportSize({width: 1440, height: 1000});
    const snapshot = await (await context.request.get(base + '/api/intakes')).json();
    snapshot.intakes[0].status = 'future_service_state';
    snapshot.intakes[0].analysis.submitted.facts = [];
    await page.route('**/api/intakes', route => route.fulfill({json: snapshot}));
    await page.locator('#refresh').click();
    await page.getByText('연결된 원문 근거 없음', {exact: true}).first().waitFor();
    await page.getByText('알 수 없는 상태를 완료로 처리하지 않습니다. 원래 상태 코드를 확인하세요.').waitFor();
    checks.push('unsupported state and missing source remain explicit');

    await page.unroute('**/api/intakes');
    await page.route('**/api/intakes', route => route.fulfill({status: 503, json: {error: {code: 'store_unavailable'}}}));
    await page.locator('#refresh').click();
    await page.getByText('아래 내용은 마지막 성공 조회 시점의 기록입니다. 최신 상태가 아닐 수 있습니다.').waitFor();
    await page.unroute('**/api/intakes');
    await page.getByRole('button', {name: '다시 조회', exact: true}).click();
    await page.waitForFunction(() => document.querySelector('#error-banner').hidden);
    checks.push('refresh failure preserves labeled stale data and retry recovers');

    const failedPage = await context.newPage();
    await failedPage.route('**/api/intakes', route => route.fulfill({status: 503, json: {error: {code: 'store_missing'}}}));
    await failedPage.goto(base);
    await failedPage.getByRole('heading', {name: '접수를 읽지 못했습니다'}).waitFor();
    assert.equal(await failedPage.getByRole('heading', {name: '첫 접수를 기다리고 있습니다'}).count(), 0);
    await failedPage.screenshot({path: path.join(output, 'error.png')});
    checks.push('initial error is never an empty-store success');

    const loadingPage = await context.newPage();
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await loadingPage.route('**/api/intakes', async route => { await gate; await route.continue(); });
    await loadingPage.goto(base, {waitUntil: 'domcontentloaded'});
    await loadingPage.getByRole('heading', {name: '접수 상태를 조회하고 있습니다'}).waitFor();
    assert.equal(await loadingPage.locator('#intake-view').getAttribute('aria-busy'), 'true');
    release();
    await loadingPage.getByRole('heading', {name: '01 · 의뢰 확인 — 시장 충돌'}).waitFor();
    checks.push('loading remains distinct until the API responds');

    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    await fs.writeFile(path.join(output, 'browser-results.json'), JSON.stringify({checks, pageErrors: errors, externalRequests: external}, null, 2));
    console.log(JSON.stringify({passed: checks.length, checks, evidence: output}, null, 2));
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
