/* Runs the real HTTP boundary and browser against the explicitly synthetic fixture. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '../..');
  const output = path.resolve(process.env.VLAB_EVIDENCE_DIR || path.join(root, '.local/dev4/virtual-fleet'));
  fs.mkdirSync(output, {recursive: true});
  const python = process.env.VLAB_PYTHON || path.join(root, '.venv/Scripts/python.exe');
  const child = spawn(python, ['-m', 'labflow.virtual_fleet_server', '--demo', '--port', '0'], {
    cwd: root, windowsHide: true, env: {...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8'}, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  child.stderr.on('data', chunk => {log += chunk;});
  const origin = await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('server startup timeout: ' + log)), 10000);
    child.once('exit', code => {clearTimeout(timeout); reject(new Error('server exited ' + code + ': ' + log));});
    child.stdout.on('data', chunk => {
      log += chunk;
      const match = log.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) {clearTimeout(timeout); resolve(match[0]);}
    });
  });
  const browser = await chromium.launch({headless: true});
  const results = [];
  const check = async (name, run) => {await run(); results.push(name); console.log('PASS ' + name);};
  try {
    const page = await browser.newPage({viewport: {width: 1512, height: 1100}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    await check('loads synthetic provenance and separates catalog from deployed devices', async () => {
      await page.getByRole('heading', {name: '가상 시험소', exact: true}).waitFor();
      await page.locator('#updated').filter({hasText: 'KST'}).waitFor();
      assert.match(await page.locator('#mode-label').innerText(), /합성 fixture/);
      assert.equal(await page.locator('[data-metric="profiles"]').innerText(), '7');
      assert.equal(await page.locator('[data-metric="devices"]').innerText(), '6');
      assert.equal(await page.locator('#catalog-body tr').count(), 7);
      assert.match(await page.locator('#catalog-body').innerText(), /미배치/);
    });
    await check('topology keyboard selection and all device observations', async () => {
      const node = page.locator('[data-device="supply"]').first();
      await node.focus(); await page.keyboard.press('Enter');
      await page.locator('#device-title').filter({hasText: 'DC 전원'}).waitFor();
      assert.match(await page.locator('#inspector').innerText(), /voltage_v/);
      assert.equal(await page.locator('.device-list [data-device]').count(), 6);
    });
    const action = async (device, name, values = {}) => {
      await page.locator('.device-list [data-device="' + device + '"]').click();
      await page.locator('#action-select').selectOption(name);
      for (const [key, value] of Object.entries(values)) {
        const input = page.locator('[data-parameter="' + key + '"]');
        if (await input.evaluate(node => node.tagName === 'SELECT')) await input.selectOption(String(value));
        else await input.fill(String(value));
      }
      await page.getByRole('button', {name: '가상 동작 실행', exact: true}).click();
      await page.locator('#operation-status').filter({hasText: '응답 수신'}).waitFor();
      await page.getByRole('button', {name: '가상 동작 실행', exact: true}).waitFor({state: 'visible'});
      await page.waitForFunction(() => !document.querySelector('#run-action').disabled);
    };
    await check('missing prerequisites are invalid and operator recovery completes measurement', async () => {
      await action('meter', 'start');
      assert.match(await page.locator('#inspector').innerText(), /데이터 무효/);
      await action('supply', 'set_output', {enabled: true});
      await action('dut', 'set_transmit', {enabled: true});
      await action('meter', 'recover');
      await action('meter', 'start');
      assert.match(await page.locator('#inspector').innerText(), /진행 대기/);
      await page.locator('#advance-ticks').fill('2');
      await page.locator('#advance').click();
      await page.waitForFunction(() => document.querySelector('[data-metric="tick"]').textContent === '2');
      assert.match(await page.locator('#inspector').innerText(), /completed/);
      assert.match(await page.locator('#inspector').innerText(), /power_dbm/);
    });
    await check('configuration revision invalidates old acquired result', async () => {
      await action('pad', 'set_attenuation', {loss_db: 9});
      await page.locator('.device-list [data-device="meter"]').click();
      assert.match(await page.locator('#inspector').innerText(), /데이터 무효/);
      assert.match(await page.locator('#inspector').innerText(), /setup_revision_changed/);
      assert.doesNotMatch(await page.locator('#observation-values').innerText(), /power_dbm/);
    });
    await check('catalog filtering preserves explicit empty and profile evidence scope', async () => {
      await page.locator('#catalog-search').fill('impossible-model');
      await page.locator('#catalog-body').filter({hasText: '검색 결과가 없습니다'}).waitFor();
      await page.locator('#catalog-search').fill('');
      assert.equal(await page.locator('#catalog-body tr').count(), 7);
      assert.match(await page.locator('#catalog').innerText(), /실행 검증/);
    });
    await check('malformed refresh keeps last successful snapshot and update time', async () => {
      const before = await page.locator('#updated').innerText();
      const tick = await page.locator('[data-metric="tick"]').innerText();
      const state = await (await page.request.get(origin + '/api/state')).json();
      state.observations.devices.meter.values = null;
      await page.route('**/api/state', route => route.fulfill({json: state}));
      await page.locator('#refresh').click();
      await page.locator('#load-status').filter({hasText: '마지막 성공 상태'}).waitFor();
      assert.equal(await page.locator('#updated').innerText(), before);
      assert.equal(await page.locator('[data-metric="tick"]').innerText(), tick);
      await page.unroute('**/api/state');
      await page.locator('#refresh').click();
      await page.locator('#load-status').filter({hasText: '관측 갱신 완료'}).waitFor();
    });
    await check('mutation receipt stays distinct from failed state refresh', async () => {
      await page.route('**/api/state', route => route.fulfill({status: 503, json: {error: {code: 'runtime_unavailable'}}}));
      await page.locator('#advance').click();
      await page.locator('#operation-status').filter({hasText: '응답 수신'}).waitFor();
      await page.locator('#load-status').filter({hasText: '마지막 성공 상태'}).waitFor();
      assert.match(await page.locator('#operation-status').innerText(), /새 상태 조회 실패/);
      await page.unroute('**/api/state');
      await page.locator('#refresh').click();
      await page.locator('#load-status').filter({hasText: '관측 갱신 완료'}).waitFor();
    });
    await check('lost mutation response retries the same ID without double advance', async () => {
      const before = Number(await page.locator('[data-metric="tick"]').innerText());
      await page.locator('#advance-ticks').fill('1');
      await page.route('**/api/advance', async route => {await route.fetch(); await route.abort('failed');}, {times: 1});
      await page.locator('#advance').click();
      await page.locator('#retry-request').waitFor({state: 'visible'});
      await page.locator('#retry-request').click();
      await page.locator('#operation-status').filter({hasText: '같은 요청 재수신'}).waitFor();
      await page.waitForFunction(value => document.querySelector('[data-metric="tick"]').textContent === String(value + 1), before);
    });
    await check('untrusted model text is rendered without HTML execution', async () => {
      const state = await (await page.request.get(origin + '/api/state')).json();
      state.catalog.profiles[0].model = '<img src=x onerror="window.injected=true">';
      await page.route('**/api/state', route => route.fulfill({json: state}));
      await page.locator('#refresh').click();
      await page.locator('#catalog-body').filter({hasText: '<img src=x'}).waitFor();
      assert.equal(await page.locator('#catalog-body img').count(), 0);
      assert.equal(await page.evaluate(() => window.injected), undefined);
      await page.unroute('**/api/state');
      await page.locator('#refresh').click();
      await page.locator('#load-status').filter({hasText: '관측 갱신 완료'}).waitFor();
    });
    await page.screenshot({path: path.join(output, 'virtual-fleet-desktop.png'), fullPage: true});
    await check('mobile layout keeps controls reachable without page overflow', async () => {
      await page.setViewportSize({width: 390, height: 844});
      await page.locator('#refresh').focus();
      assert.equal(await page.locator('#refresh').evaluate(node => node === document.activeElement), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.screenshot({path: path.join(output, 'virtual-fleet-mobile.png'), fullPage: true});
    });
    await check('first-load error stays error when controls change and recovers on refresh', async () => {
      const fresh = await browser.newPage();
      await fresh.route('**/api/state', route => route.fulfill({status: 503, json: {error: {code: 'runtime_unavailable'}}}));
      await fresh.goto(origin);
      await fresh.locator('#load-status').filter({hasText: '조회하지 못했습니다'}).waitFor();
      assert.equal(await fresh.locator('#advance').isEnabled(), false);
      assert.equal(await fresh.locator('#catalog-search').isEnabled(), false);
      assert.equal(await fresh.locator('[data-metric="profiles"]').count(), 0);
      await fresh.unroute('**/api/state');
      await fresh.locator('#refresh').click();
      await fresh.locator('[data-metric="profiles"]').waitFor();
      await fresh.close();
    });
    await check('renderer failure before timestamp publication preserves all successful DOM and state', async () => {
      const fresh = await browser.newPage();
      await fresh.goto(origin);
      await fresh.locator('#updated').filter({hasText: 'KST'}).waitFor();
      const hash = html => createHash('sha256').update(html).digest('hex');
      const before = hash(await fresh.locator('#content').innerHTML());
      const beforeTime = await fresh.locator('#updated').innerText();
      const changed = await (await fresh.request.get(origin + '/api/state')).json();
      changed.observations.tick += 40;
      changed.catalog.profiles[0].model = 'NEW SNAPSHOT SHOULD NOT BE PUBLISHED';
      await fresh.route('**/api/state', route => route.fulfill({json: changed}));
      await fresh.evaluate(() => {window.savedFormatter = Intl.DateTimeFormat; Intl.DateTimeFormat = function () {throw new Error('renderer failure');};});
      await fresh.locator('#refresh').click();
      await fresh.locator('#load-status').filter({hasText: '마지막 성공 상태'}).waitFor();
      assert.equal(hash(await fresh.locator('#content').innerHTML()), before);
      assert.equal(await fresh.locator('#updated').innerText(), beforeTime);
      await fresh.evaluate(() => {Intl.DateTimeFormat = window.savedFormatter; delete window.savedFormatter;});
      await fresh.unroute('**/api/state');
      await fresh.locator('#refresh').click();
      await fresh.locator('#load-status').filter({hasText: '관측 갱신 완료'}).waitFor();
      await fresh.close();
    });
    await check('empty valid topology is separate from a failed snapshot', async () => {
      const empty = await browser.newPage();
      const state = await (await page.request.get(origin + '/api/state')).json();
      state.topology = {devices: [], connections: []}; state.observations.devices = {};
      await empty.route('**/api/state', route => route.fulfill({json: state}));
      await empty.goto(origin);
      await empty.locator('#topology').filter({hasText: '배치된 가상 장비가 없습니다'}).waitFor();
      assert.equal(await empty.locator('#catalog-body tr').count(), 7);
      await empty.close();
    });
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({synthetic: true, hardware_verified: false, checks: results}, null, 2));
    console.log(JSON.stringify({checks: results.length, output}));
  } finally {
    await browser.close(); child.kill();
  }
}
main().catch(error => {console.error(error); process.exitCode = 1;});
