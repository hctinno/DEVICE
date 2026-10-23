/* Metadata/UI binding check against a separately launched synthetic catalog fixture.
 * This intentionally makes no device action or virtual acceptance claim.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

async function main() {
  const [origin, expected = '64'] = process.argv.slice(2);
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin || '')) throw new Error('Pass the local synthetic catalog fixture origin');
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1512, height: 1100}});
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    const state = await (await page.request.get(origin + '/api/state')).json();
    const count = Number(expected);
    assert.equal(state.catalog.profiles.length, count);
    assert.equal(state.runtime_kind, 'synthetic_fixture');
    await page.goto(origin);
    await page.locator('#updated').filter({hasText: 'KST'}).waitFor();
    assert.equal(await page.locator('#catalog-body tr').count(), count);
    assert.equal(await page.locator('[data-metric="profiles"]').innerText(), String(count));
    const classifications = {};
    for (let index = 0; index < state.topology.devices.length; index++) {
      const device = state.topology.devices[index];
      const profile = state.catalog.profiles.find(profile => profile.profile_id === device.profile_id);
      classifications[profile.profile_kind] = (classifications[profile.profile_kind] || 0) + 1;
      await page.locator('.device-list [data-device="' + device.id + '"]').click();
      assert.equal(await page.locator('#device-title').innerText(), profile.model);
      assert.match(await page.locator('#inspector').innerText(), /선언된 운영자 동작이 없습니다/);
    }
    if (count === 64) assert.deepEqual(classifications, {report_equipment: 61, dut_context: 1, auxiliary: 2});
    assert.match(await page.locator('#catalog-body').innerText(), /DUT 문맥/);
    assert.match(await page.locator('#catalog-body').innerText(), /보조 프로필/);
    await page.locator('#catalog-role').selectOption('rf_switch');
    assert.match(await page.locator('#catalog-body').innerText(), /FBSM-01B/);
    const rows = await page.locator('#catalog-body tr').count(); assert.ok(rows > 0 && rows < count);
    await page.locator('#catalog-role').selectOption('');
    assert.equal(await page.locator('#catalog-body tr').count(), count);
    await page.evaluate(() => scrollTo(0, 0));
    const output = path.resolve('.local/dev4/virtual-fleet'); fs.mkdirSync(output, {recursive: true});
    await page.screenshot({path: path.join(output, 'catalog-64-binding.png'), fullPage: false});
    assert.deepEqual(errors, []);
    const result = {profiles: count, selected_nodes: state.topology.devices.length, classifications, role_actions_executed: 0,
      acceptance: 'catalog_metadata_UI_binding_only', synthetic: true, hardware_verified: false};
    fs.writeFileSync(path.join(output, 'catalog-binding-results.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally {await browser.close();}
}
main().catch(error => {console.error(error); process.exitCode = 1;});
