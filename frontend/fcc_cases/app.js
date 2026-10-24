import {createFccCaseReader} from '/fcc-cases/view.mjs';
import {parseFccCaseJson, validateFccCaseSummary, FCC_CASE_ERROR_CODES} from '/fcc-cases/model.mjs';

const state = document.querySelector('#fcc-route-state');
const status = document.querySelector('#fcc-route-status');
const retry = document.querySelector('#fcc-route-retry');
const container = document.querySelector('#fcc-reader');
const allowedErrors = new Set([...FCC_CASE_ERROR_CODES, 'fcc_case_catalog_unconfigured', 'fcc_case_catalog_unavailable']);
let reader = null, controller = null, generation = 0, alive = true;

async function get(target, signal) {
  const response = await fetch(target, {signal, cache: 'no-store', credentials: 'same-origin', redirect: 'error'});
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > 8 * 1024 * 1024)) {
    await response.body?.cancel();
    throw Error('invalid_fcc_case_response');
  }
  let length = 0;
  const chunks = [], stream = response.body?.getReader();
  if (!stream) throw Error('invalid_fcc_case_response');
  try {
    while (true) {
      const {done, value} = await stream.read();
      if (done) break;
      length += value.byteLength;
      if (length > 8 * 1024 * 1024) throw Error('invalid_fcc_case_response');
      chunks.push(value);
    }
  } catch (error) {
    await stream.cancel().catch(() => {});
    throw error;
  } finally {
    stream.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  const value = parseFccCaseJson(new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes));
  if (!response.ok) {
    const code = value?.error?.code;
    if (Object.keys(value).join() !== 'error' || !value.error || Object.keys(value.error).join() !== 'code'
        || !allowedErrors.has(code)) throw Error('invalid_fcc_case_response');
    throw Error(code);
  }
  return value;
}

async function connect() {
  if (!alive) return;
  if (reader) return reader.refresh({moveFocus: true});
  const ticket = ++generation;
  controller?.abort();
  controller = new AbortController();
  state.dataset.state = 'pending';
  status.textContent = '사례 자료의 구성 상태를 확인하고 있습니다.';
  try {
    const first = validateFccCaseSummary(await get('/api/fcc-cases/summary', controller.signal));
    if (!alive || ticket !== generation) return;
    let initial = first;
    reader = createFccCaseReader(container, {
      async readSummary(signal) {
        if (initial !== null) { const value = initial; initial = null; return Promise.resolve(value); }
        const value = validateFccCaseSummary(await get('/api/fcc-cases/summary', signal));
        return value;
      },
      readCase: (id, signal) => get('/api/fcc-cases/cases/' + encodeURIComponent(id), signal),
    });
    container.hidden = false;
    state.hidden = true;
    await reader.refresh();
  } catch (error) {
    if (!alive || ticket !== generation) return;
    const unconfigured = error?.message === 'fcc_case_catalog_unconfigured';
    state.dataset.state = unconfigured ? 'unconfigured' : 'error';
    status.textContent = unconfigured
      ? '사례 자료 미구성 · 이 서버에 검수된 사례 자료가 연결되지 않았습니다. 사례 수와 모집단은 확인되지 않았습니다.'
      : '사례 자료 조회 실패 · 현재 자료를 확인할 수 없습니다. 빈 corpus가 확인된 것은 아닙니다.';
  }
}

retry.addEventListener('click', () => { void connect(); });
window.addEventListener('pagehide', () => {
  alive = false; generation++; controller?.abort(); reader?.destroy();
}, {once: true});
void connect();
