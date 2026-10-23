/* Regression checks for the DEV4-UI-001 integration review. No server writes. */
const {chromium} = require('playwright');
const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {createHash} = require('node:crypto');

const base = process.env.UI_DEMO_URL || 'http://127.0.0.1:8765';
const output = path.resolve('.local/dev4/review-evidence');
let browser, context, original;

before(async () => {
  await fs.mkdir(output, {recursive: true});
  browser = await chromium.launch({headless: true});
  context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  context.setDefaultTimeout(3000);
  original = await (await context.request.get(base + '/api/intakes')).json();
});
after(async () => { await browser?.close(); });

async function displayState(page) {
  const values = await page.evaluate(() => Object.fromEntries(
    ['#metrics', '#intake-list', '#detail-panel', '#notification-view', '#result-count', '#last-updated']
      .map(selector => [selector, document.querySelector(selector).innerHTML])));
  return Object.fromEntries(Object.entries(values).map(([key, html]) => [key, createHash('sha256').update(html).digest('hex')]));
}

const invalidCases = [
  ['missing question key', data => { data.intakes[0].analysis.questions = [{message: 'Missing key'}]; }],
  ['missing candidate value', data => { delete data.intakes[0].analysis.submitted.facts[0].value; }],
  ['object instead of question array', data => { data.intakes[0].analysis.questions = {message: 'Wrong boundary'}; }],
  ['array instead of projected facts object', data => { data.intakes[0].analysis.facts = []; }],
  ['null notification record', data => { data.notifications.push(null); }],
];

for (const [name, corrupt] of invalidCases) {
  test(`refresh rejects ${name} without mixing snapshots`, async () => {
    const page = await context.newPage();
    try {
      await page.goto(base);
      await page.locator('#detail-title').waitFor();
      const previous = await displayState(page);
      const malformed = structuredClone(original);
      malformed.intakes[0].bundle = 'MALFORMED NEW SNAPSHOT';
      const extra = structuredClone(malformed.intakes[0]);
      extra.intake_id = 'I-extra';
      malformed.intakes.push(extra);
      corrupt(malformed);
      await page.route('**/api/intakes', route => route.fulfill({json: malformed}));
      await page.locator('#refresh').click();
      await page.locator('#error-banner').waitFor({state: 'visible'});
      assert.deepEqual(await displayState(page), previous);
      assert.match(await page.locator('#error-banner').innerText(), /마지막 성공 조회/);
      if (name === 'missing question key') await page.screenshot({path: path.join(output, 'rejected-snapshot.png')});
      await page.unroute('**/api/intakes');
      await page.getByRole('button', {name: '다시 조회', exact: true}).click();
      await page.waitForFunction(() => document.querySelector('#error-banner').hidden);
      await page.locator('.intake-item').nth(1).click();
      assert.equal(await page.locator('#detail-title').innerText(), original.intakes[1].bundle);
      if (name === 'missing question key') await page.screenshot({path: path.join(output, 'recovered.png')});
    } finally { await page.close(); }
  });
}

for (const empty of [false, true]) test(`a rendering exception preserves the successful snapshot (${empty ? 'empty response' : 'populated response'})`, async () => {
  const page = await context.newPage();
  try {
    await page.goto(base);
    await page.locator('#detail-title').waitFor();
    const previous = await displayState(page);
    const replacement = structuredClone(original);
    replacement.intakes[0].bundle = 'VALID NEW SNAPSHOT';
    if (empty) { replacement.intakes = []; replacement.notifications = []; }
    await page.route('**/api/intakes', route => route.fulfill({json: replacement}));
    await page.evaluate(() => {
      window.savedFormatter = Intl.DateTimeFormat;
      Intl.DateTimeFormat = function () { throw new Error('Injected renderer failure'); };
    });
    await page.locator('#refresh').click();
    await page.locator('#error-banner').waitFor({state: 'visible'});
    assert.deepEqual(await displayState(page), previous);
    await page.evaluate(() => { Intl.DateTimeFormat = window.savedFormatter; delete window.savedFormatter; });
    await page.unroute('**/api/intakes');
    await page.getByRole('button', {name: '다시 조회', exact: true}).click();
    await page.waitForFunction(() => document.querySelector('#error-banner').hidden);
  } finally { await page.close(); }
});

test('a malformed first response stays an error when search and filter change', async () => {
  const page = await context.newPage();
  try {
    const malformed = structuredClone(original);
    malformed.intakes[0].analysis.questions = [{message: 'Missing key'}];
    await page.route('**/api/intakes', route => route.fulfill({json: malformed}));
    await page.goto(base);
    await page.locator('#error-banner').waitFor({state: 'visible'});
    await page.locator('#search').fill('없는 자료');
    await page.locator('#filter').selectOption('failed');
    assert.equal(await page.getByRole('heading', {name: '접수를 읽지 못했습니다'}).count(), 1);
    assert.equal(await page.locator('#result-count').innerText(), '조회 불가');
    assert.equal(await page.locator('.metric').count(), 0);
    await page.screenshot({path: path.join(output, 'initial-invalid.png')});
  } finally { await page.close(); }
});

test('initial HTTP failure survives search and filter interaction', async () => {
  const page = await context.newPage();
  try {
    await page.route('**/api/intakes', route => route.fulfill({status: 503, json: {error: {code: 'store_unavailable'}}}));
    await page.goto(base);
    await page.getByRole('heading', {name: '접수를 읽지 못했습니다'}).waitFor();
    await page.locator('#search').fill('검색');
    await page.locator('#filter').selectOption('failed');
    assert.equal(await page.getByRole('heading', {name: '접수를 읽지 못했습니다'}).count(), 1);
    assert.equal(await page.locator('#result-count').innerText(), '조회 불가');
    assert.equal(await page.getByText('등록된 접수가 없습니다.', {exact: true}).count(), 0);
  } finally { await page.close(); }
});

test('search and filter during initial loading do not invent an empty result', async () => {
  const page = await context.newPage();
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  try {
    await page.route('**/api/intakes', async route => { await gate; await route.continue(); });
    await page.goto(base, {waitUntil: 'domcontentloaded'});
    await page.locator('#search').fill('검색');
    await page.locator('#filter').selectOption('failed');
    assert.equal(await page.getByRole('heading', {name: '접수 상태를 조회하고 있습니다'}).count(), 1);
    assert.equal(await page.locator('#result-count').innerText(), '조회 중');
    release();
    await page.waitForFunction(() => document.querySelectorAll('.metric').length === 4);
  } finally { release(); await page.close(); }
});
