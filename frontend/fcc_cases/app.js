import {createFccCaseReader} from '/fcc-cases/view.mjs';
import {parseFccCaseJson, validateFccCaseSummary, FCC_CASE_ERROR_CODES} from '/fcc-cases/model.mjs';
import {createFccCaseDiscovery} from '/fcc-cases/discovery_view.mjs';
import {fccCaseLookupTarget, FCC_CASE_LOOKUP_MAX_BYTES} from '/fcc-cases/discovery_model.mjs';
import {createFccCaseCalculation} from '/fcc-cases/calculation_view.mjs';
import {FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES} from '/fcc-cases/calculation_model.mjs';

const state = document.querySelector('#fcc-route-state');
const status = document.querySelector('#fcc-route-status');
const retry = document.querySelector('#fcc-route-retry');
const container = document.querySelector('#fcc-reader');
const lookupSlot = document.querySelector('#fcc-lookup-slot');
const allowedErrors = new Set([...FCC_CASE_ERROR_CODES, 'fcc_case_catalog_unconfigured', 'fcc_case_catalog_unavailable']);
let reader = null, discovery = null, controller = null, generation = 0, alive = true;
const calculationErrors=new Set([...allowedErrors,'fcc_calc_invalid_case','fcc_calc_invalid_request','fcc_calc_limit_exceeded',
  'fcc_case_catalog_invalid','fcc_case_calculation_invalid_request','fcc_case_calculation_limit_exceeded','fcc_case_calculation_unavailable','local_origin_required','read_only']);
// Coalesce only the initial raw wire reply. Each panel validates and owns its own
// state/tickets; a reader validation failure cannot prevent calculation startup.
const initialSummaryController=new AbortController();
let initialSummaryPromise=null,readerInitial=true,calculationInitial=true;
const initialSummary=()=>initialSummaryPromise??=(calculationRead('/api/fcc-cases/summary',initialSummaryController.signal));

async function calculationRead(target,signal,{body=null,cap=8*1024**2}={}){
  const response=await fetch(target,{signal,method:body===null?'GET':'POST',
    ...(body===null?{}:{headers:{'Content-Type':'application/json'},body}),cache:'no-store',credentials:'same-origin',redirect:'error'});
  const declared=response.headers.get('content-length');
  if(declared!==null && (!/^[0-9]+$/.test(declared) || Number(declared)>cap)){await response.body?.cancel();throw Error('invalid_fcc_case_calculation');}
  const stream=response.body?.getReader();if(!stream)throw Error('invalid_fcc_case_calculation');
  const chunks=[];let length=0;
  try{while(true){const {done,value}=await stream.read();if(done)break;length+=value.byteLength;if(length>cap)throw Error('invalid_fcc_case_calculation');chunks.push(value);}}
  catch(error){await stream.cancel().catch(()=>{});throw error;}finally{stream.releaseLock();}
  const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);
  if(!response.ok){
    // The exact small transport envelope is independent from the service response9.
    const match=/^\s*\{\s*"error"\s*:\s*\{\s*"code"\s*:\s*"([a-z_]+)"\s*\}\s*\}\s*$/.exec(text);
    if(!match || !calculationErrors.has(match[1]))throw Error('invalid_fcc_case_calculation');
    throw Error(match[1]);
  }
  return text;
}
const calculation=createFccCaseCalculation(document.querySelector('#fcc-calculation-slot'),{
  readSummary:signal=>{if(calculationInitial){calculationInitial=false;return initialSummary();}return calculationRead('/api/fcc-cases/summary',signal);},
  readCase:(id,signal)=>calculationRead('/api/fcc-cases/cases/'+encodeURIComponent(id),signal),
  calculate:(request,signal)=>calculationRead('/api/fcc-cases/calculations',signal,{body:JSON.stringify(request),cap:FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES}),
});
void calculation.refresh();

async function readResponse(target, signal, cap) {
  const response = await fetch(target, {signal, cache: 'no-store', credentials: 'same-origin', redirect: 'error'});
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > cap)) {
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
      if (length > cap) throw Error('invalid_fcc_case_response');
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
  const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
  if (!response.ok) {
    const value = parseFccCaseJson(text);
    const code = value?.error?.code;
    if (Object.keys(value).join() !== 'error' || !value.error || Object.keys(value.error).join() !== 'code'
        || !allowedErrors.has(code)) throw Error('invalid_fcc_case_response');
    throw Error(code);
  }
  return text;
}

const get = async (target, signal) => parseFccCaseJson(await readResponse(target, signal, 8 * 1024 * 1024));

async function connect() {
  if (!alive) return;
  if (reader) return reader.refresh({moveFocus: true});
  const ticket = ++generation;
  controller?.abort();
  controller = new AbortController();
  state.dataset.state = 'pending';
  status.textContent = '사례 자료의 구성 상태를 확인하고 있습니다.';
  try {
    const useInitial=readerInitial;readerInitial=false;
    const first = validateFccCaseSummary(useInitial?parseFccCaseJson(await initialSummary()):await get('/api/fcc-cases/summary', controller.signal));
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
    if (!alive || ticket !== generation) return;
    reader.root.insertBefore(lookupSlot, reader.root.querySelector('.fcc-summary'));
    discovery = createFccCaseDiscovery(lookupSlot, {summary: first,
      readLookup: (query, signal) => readResponse(fccCaseLookupTarget(query), signal, FCC_CASE_LOOKUP_MAX_BYTES),
      selectCase: id => reader.select(id)});
    lookupSlot.hidden = false;
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
  alive = false; generation++; controller?.abort();initialSummaryController.abort();discovery?.destroy();reader?.destroy();calculation.destroy();
}, {once: true});
void connect();
