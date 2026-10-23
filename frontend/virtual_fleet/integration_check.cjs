/* Bounded browser acceptance against the actual 64-profile synthetic runtime. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '../..');
  const output = path.resolve(process.argv[3] || path.join(root, '.local/fleet-integrated-browser'));
  fs.mkdirSync(output, {recursive: true});
  const child = spawn(process.argv[2] || 'python', ['-m', 'labflow.virtual_fleet', '--example', 'conducted', '--port', '0'], {
    cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
    env: {...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8'},
  });
  let browser;
  try {
    let log = '';
    const origin = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('virtual server startup timeout')), 10000);
      child.once('error', error => {clearTimeout(timeout); reject(error);});
      child.once('exit', code => {clearTimeout(timeout); reject(new Error('virtual server exited: ' + code));});
      child.stderr.on('data', chunk => {log += chunk;});
      child.stdout.on('data', chunk => {
        log += chunk;
        const match = log.match(/http:\/\/127\.0\.0\.1:\d+/);
        if (match) {clearTimeout(timeout); resolve(match[0]);}
      });
    });
    browser = await chromium.launch({headless: true});
    const page = await browser.newPage({viewport: {width: 1512, height: 1000}});
    page.setDefaultTimeout(10000);
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    const checks = [];
    const check = async (name, run) => {await run(); checks.push(name); console.log('PASS ' + name);};
    const state = async () => (await page.request.get(origin + '/api/state')).json();
    const select = async device => page.locator('.device-list [data-device="' + device + '"]').click();
    const action = async (device, name) => {
      await select(device); await page.locator('#action-select').selectOption(name);
      await page.locator('#run-action').click();
      await page.locator('#operation-status').filter({hasText: '응답 수신'}).waitFor();
      await page.waitForFunction(() => !document.querySelector('#run-action').disabled);
    };
    const advance = async ticks => {
      await page.locator('#advance-ticks').fill(String(ticks)); await page.locator('#advance').click();
      await page.waitForFunction(() => !document.querySelector('#advance').disabled);
    };
    await page.goto(origin);
    await check('actual runtime exposes all 64 catalog profiles and devices', async () => {
      await page.getByRole('heading', {name: '가상 시험소', exact: true}).waitFor();
      await page.locator('#load-status').filter({hasText: '관측 갱신 완료'}).waitFor();
      assert.match(await page.locator('#mode-label').innerText(), /주입 런타임/);
      assert.equal(await page.locator('[data-metric="profiles"]').innerText(), '64');
      assert.equal(await page.locator('[data-metric="devices"]').innerText(), '64');
      assert.equal(await page.locator('#catalog-body tr').count(), 64);
      assert.equal((await state()).hardware_verified, false);
    });
    await check('model search preserves meter and switch-controller identity', async () => {
      await page.locator('#catalog-search').fill('N1911A');
      assert.equal(await page.locator('#catalog-body tr').count(), 1);
      await page.locator('#catalog-search').fill('FBSM-01B');
      assert.equal(await page.locator('#catalog-body tr').count(), 1);
      assert.match(await page.locator('#catalog-body').innerText(), /rf_switch/);
      await page.locator('#catalog-search').fill('');
    });
    await check('selected meter shows the calculated synthetic time-average power', async () => {
      await select('meter');
      assert.equal(await page.locator('#device-title').innerText(), 'N1911A');
      assert.match(await page.locator('#observation-values').innerText(), /time_average/);
      const value = (await state()).observations.devices.meter.values.outputs.measurement.value;
      assert.ok(Math.abs(value - (12.5-10-.5-20+10*Math.log10(.25))) < 1e-8);
    });
    await check('stopped DUT invalidates meter results through real HTTP actions', async () => {
      await action('dut', 'stop'); await action('meter', 'fetch');
      const node = (await state()).observations.devices.meter;
      assert.notEqual(node.status, 'ok');
      assert.equal(node.values.outputs.measurement, undefined);
    });
    await check('fresh acquisition after operator recovery produces a valid result', async () => {
      await action('dut', 'start'); await advance(3); await action('meter', 'acquire');
      await advance(2); await action('meter', 'fetch');
      assert.equal((await state()).observations.devices.meter.values.outputs.measurement.valid, true);
    });
    await check('lost advance response retries the same ID without advancing twice', async () => {
      const before = (await state()).observations.tick;
      let lost = false;
      await page.route('**/api/advance', async route => {
        if (!lost) {lost = true; await route.fetch(); await route.abort('failed');}
        else await route.continue();
      });
      await page.locator('#advance-ticks').fill('1'); await page.locator('#advance').click();
      await page.locator('#retry-request').waitFor({state: 'visible'});
      await page.locator('#retry-request').click();
      await page.locator('#operation-status').filter({hasText: '같은 요청 재수신'}).waitFor();
      await page.waitForFunction(() => !document.querySelector('#advance').disabled);
      assert.equal((await state()).observations.tick, before + 1);
      await page.unroute('**/api/advance');
    });
    await page.screenshot({path: path.join(output, 'desktop.png')});
    await check('64-profile layout remains within a mobile viewport', async () => {
      await page.setViewportSize({width: 390, height: 844});
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
      await page.screenshot({path: path.join(output, 'mobile.png')});
    });
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify({synthetic: true, hardware_verified: false, checks}, null, 2));
    console.log(JSON.stringify({checks: checks.length, output}));
  } finally {
    if (browser) await browser.close();
    child.kill();
  }
}
main().catch(error => {console.error(error); process.exitCode = 1;});
