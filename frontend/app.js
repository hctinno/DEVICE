import {FIELDS, FACT_LABELS, JOB_LABELS, describeState, factSources, filterIntakes, noticeContext, seoulTime, bytes, validateSnapshot, docxReferenceMatchesRecord} from './model.mjs';
import {validateFixtureRuns, describeFixtureRecord, describeIntakeWorkflow, requireStableFixtureRecords, createFixtureReadGate} from './intake_flow_model.mjs';
import {validateIntakeReferenceContext,parseIntakeReferenceHistoryJson,parseIntakeReferenceCurrentJson} from './intake-references/model.mjs';
import {createIntakeReferenceReview} from './intake-references/view.mjs';
import {createIntakeReferenceTransport} from './intake-references/transport.mjs';
import {createIntakeReferenceActionsReview} from './intake-reference-actions/actions.mjs';

const $ = selector => document.querySelector(selector);
const state = {records: [], notices: [], selected: location.hash.slice(1), loaded: false, request: 0, view: 'intakes'};
const flow = {gate:createFixtureReadGate(), context:null, payload:null, selected:'', pending:false,
  stale:false, status:'가상 기록 조회 대기', updatedText:'아직 조회하지 않음'};
const referenceTransport = createIntakeReferenceTransport();
const docx={context:null,hintContext:null,visible:false,allowed:false,busy:false,good:null,
  phase:'idle',message:'보존 관측은 명시 버튼으로 읽습니다.',ticket:0,controller:null};
const referencePanel = createIntakeReferenceReview($('#intake-reference-panel'), {
  readHistory:readReferenceHistory, readCurrent:referenceTransport.readCurrent,
});
const referenceActions = createIntakeReferenceActionsReview($('#intake-reference-actions-panel'));
let aiConnectionPanel = null;
let aiConnectionLoading = null;
function showAIConnectionPanel() {
  if (aiConnectionPanel) { aiConnectionPanel.show(); return; }
  if (!aiConnectionLoading) aiConnectionLoading = import('./ai-connections/panel.mjs').then(module => {
    aiConnectionPanel = module.createAIConnectionPanel($('#ai-connections-panel'));
    if (state.view === 'ai-connections') aiConnectionPanel.show();
  }).catch(() => {
    aiConnectionLoading = null;
    $('#ai-connections-panel').textContent = '모델 연결 화면을 불러오지 못했습니다. 다시 선택해 주세요.';
  });
}
let referenceDestroyed = false;
let referenceSuspended = false;
let referencePending = false;
let referenceContext = null;
let referenceGuard = false;
const referenceCanChange = () => !referenceDestroyed && !referenceGuard;
const sameReferenceContext = (a, b) => a && b && a.intake_id === b.intake_id &&
  a.revision === b.revision && a.snapshotGeneration === b.snapshotGeneration;

function setReferencePending(value) {
  if (!referenceCanChange()) return false;
  referenceGuard = true;
  try {
    referencePending = value;
    if (value) {
      invalidateDocxBrowser();
      referenceActions.setPending(true);
      if (referenceDestroyed) return false;
      referenceTransport.setPending(true);
      referencePanel.setPending(true);
    } else {
      referenceTransport.setPending(false);
      referenceActions.setPending(false);
      if (referenceDestroyed) return false;
      referencePanel.setPending(false);
    }
    return true;
  } finally { if (!referenceDestroyed) referenceGuard = false; }
}

function refreshRegisteredHistory(event) {
  if (!referenceCanChange() || referencePending || referenceSuspended ||
      event.target !== referenceActions.root || !referenceActions.root.isConnected) return;
  let captured;
  try { captured = validateIntakeReferenceContext(event.detail); } catch { return; }
  if (!sameReferenceContext(captured, referenceContext)) return;
  referenceGuard = true;
  try { void referencePanel.refreshHistory().catch(() => {}); } catch {}
  finally {
    // C1 is notifying until dispatchEvent has finished every bubbling listener.
    queueMicrotask(() => { if (!referenceDestroyed) referenceGuard = false; });
  }
}
referenceActions.root.addEventListener('intake-reference-history-refresh', refreshRegisteredHistory);

function projectDocxContext(context,record) {
  if (sameReferenceContext(docx.context,context)) return {...docx};
  const good=context&&docx.context?.intake_id===context.intake_id&&docx.good&&
    docxReferenceMatchesRecord(docx.good.value,record)?docx.good:null;
  return {...docx,context,hintContext:null,visible:!!good,allowed:false,busy:false,good,
    phase:good?'previous':'idle',message:good?'이전 명시 요청의 관측입니다. 현재성은 다시 확인하지 않았습니다.':'보존 관측은 명시 버튼으로 읽습니다.',
    controller:null,ticket:docx.ticket+1};
}

function renderDocxResult(value) {
  const fragment=document.createDocumentFragment(),b=value.reference.binding,n=value.reference.result;
  fragment.append(metadata([['보존자료 ID',value.artifact_id],['실제 보존 bytes',value.artifact_bytes],
    ['등록 자료 synthetic',String(value.synthetic)],['입력 출처',b.source_id],['접수 ID',b.intake_id],['자료 버전',b.revision],
    ['전체 manifest fingerprint',b.revision_fingerprint],['문서 경로',b.document.path],['원본 SHA256',b.document.sha256],['원본 bytes',b.document.bytes],
    ['Reader 이름 선언',n.reader.name],['Reader 버전 선언',n.reader.version],['Profile 선언',n.scope.profile],['Native part',n.scope.part===null?'null':n.scope.part],
    ['Native 상태 선언',n.status],['Native complete',String(n.complete)],['페이지 정보',n.scope.page_numbers],['전체 text SHA256',n.text_sha256]]));
  fragment.append(el('p','inline-note','Reader/profile/status는 저장된 선언이며 실행·지원·내용 진위는 미확인입니다. 분석 완료나 인용 승인을 뜻하지 않습니다.'));
  const details=(title,rows)=>{const node=el('details');node.append(el('summary','',title),metadata(rows));return node;};
  const structures=el('div','docx-structures');
  const block=(item,parent)=>{
    const rows=[['구조 종류',item.kind],['저장 locator',JSON.stringify(item.locator)]];
    if(item.kind==='paragraph')rows.push(['문단 text SHA256',item.text_sha256],['문단 complete',String(item.complete)],['저장 break 정보',JSON.stringify(item.breaks)]);
    if(item.kind==='unsupported')rows.push(['지원되지 않은 구조 사유',item.reason]);
    if(item.kind==='table')rows.push(['선언 grid columns',item.grid_columns===null?'null':item.grid_columns]);
    const node=details(item.kind+' · 저장 위치',rows);parent.append(node);
    if(item.kind==='table')for(const row of item.rows){
      const r=details('physical row',[['저장 locator',JSON.stringify(row.locator)],['grid before',row.grid_before],['grid after',row.grid_after]]);node.append(r);
      for(const cell of row.cells){const c=details('physical cell',[['저장 locator',JSON.stringify(cell.locator)],['grid start',cell.grid_start],['grid span',cell.grid_span],
        ['vMerge',cell.v_merge],['merge origin',JSON.stringify(cell.merge_origin)]]);r.append(c);for(const child of cell.blocks)block(child,c);}
    }
  };
  for(const item of n.blocks)block(item,structures);fragment.append(structures);
  const issues=details('Native issues · '+n.issues.length,[]);
  for(const issue of n.issues)issues.append(metadata([['Issue code',issue.code],['저장 locator',JSON.stringify(issue.locator)],['원 occurrences',issue.occurrences]]));
  fragment.append(issues);
  for(const [title,value] of [['제공된 limits',n.limits],['제공된 statistics',n.statistics]]){
    const node=el('details');node.append(el('summary','',title),el('p','mono detail-id',JSON.stringify(value)));fragment.append(node);
  }
  return fragment;
}

function buildDocxSection(record,next,skipResult=false) {
  if(!next.visible||!next.context||record.intake_id!==next.context.intake_id||record.revision!==next.context.revision)return null;
  const node=section('DOCX 보존 관측','원본·보존자료를 명시 요청 시점에 확인합니다.');node.classList.add('docx-retained-observation');
  node.dataset.state=next.phase;node.setAttribute('aria-busy',String(next.busy));
  const button=el('button','button docx-read','DOCX 보존 관측 읽기');button.type='button';
  button.disabled=!next.allowed||referencePending||referenceSuspended||referenceDestroyed;
  button.setAttribute('aria-disabled',String(next.busy||button.disabled));
  button.addEventListener('click',readDocxObservation);
  const status=el('p','inline-note docx-status',next.message);status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const note=el('p','inline-note docx-last-good',next.good&&next.phase!=='ready'?'이전 성공 관측을 보존했습니다. 이번 요청의 새 확인 결과가 아닙니다.':'');
  const results=el('div','docx-results');
  if(next.good&&!skipResult&&docxReferenceMatchesRecord(next.good.value,record))results.append(renderDocxResult(next.good.value));
  node.append(button,status,note,results);return node;
}

function publishDocx(next) {
  // Suspended pages may retire controls; source/history success callers have
  // their own suspension guards and cannot publish a new observation here.
  if(referenceDestroyed||!sameReferenceContext(next.context,referenceContext))return;
  const record=state.records.find(r=>r.intake_id===state.selected);if(!record)return;
  const existing=$('.docx-retained-observation'),sameGood=existing&&next.good===docx.good;
  const prepared=buildDocxSection(record,next,!!sameGood);
  if(referenceDestroyed||!sameReferenceContext(next.context,referenceContext))return;
  if(!prepared)existing?.remove();
  else if(existing){
    if(!sameGood)existing.querySelector('.docx-results').replaceChildren(...prepared.querySelector('.docx-results').childNodes);
    existing.querySelector('.docx-status').textContent=next.message;
    existing.querySelector('.docx-last-good').textContent=prepared.querySelector('.docx-last-good').textContent;
    existing.querySelector('.docx-read').disabled=prepared.querySelector('.docx-read').disabled;
    existing.querySelector('.docx-read').setAttribute('aria-disabled',prepared.querySelector('.docx-read').getAttribute('aria-disabled'));
    existing.dataset.state=next.phase;existing.setAttribute('aria-busy',String(next.busy));
  }else $('#detail-panel .detail-body')?.append(prepared);
  Object.assign(docx,next);
}

function docxRenderFailure(captured) {
  if(referenceDestroyed||!sameReferenceContext(captured,referenceContext))return;
  docx.controller?.abort();docx.controller=null;docx.ticket++;docx.busy=false;docx.phase='error';
  docx.message='화면을 준비하지 못했습니다. 이전 성공 관측을 유지합니다.';
  const node=$('.docx-retained-observation');if(!node)return;
  node.dataset.state='error';node.setAttribute('aria-busy','false');
  node.querySelector('.docx-status').textContent=docx.message;
  node.querySelector('.docx-last-good').textContent=docx.good?'이전 성공 관측입니다. 새 확인 결과가 아닙니다.':'';
  const button=node.querySelector('.docx-read');button.disabled=!docx.allowed||referencePending||referenceSuspended;
  button.setAttribute('aria-disabled',String(button.disabled));
}

function invalidateDocxBrowser() {
  if(!docx.visible&&!docx.controller&&!docx.allowed)return;
  docx.controller?.abort();
  const next={...docx,controller:null,ticket:docx.ticket+1,allowed:false,hintContext:null,busy:false,
    phase:docx.good?'previous':'idle',message:'선택 안내를 다시 확인하고 있습니다. 이전 관측은 현재 확인 결과가 아닙니다.'};
  try{publishDocx(next);Object.assign(docx,next);}catch{Object.assign(docx,next);docxRenderFailure(next.context);}
}

async function readReferenceHistory(id,query,signal) {
  const captured=referenceContext;invalidateDocxBrowser();
  try {
    const response=await referenceTransport.readHistory(id,query,signal);
    if(referenceDestroyed||referenceSuspended||referencePending||!sameReferenceContext(captured,referenceContext))return response;
    const selected=referenceTransport.hasRetainedDocxSelection();
    // Default absence does no extra parse. A previously shown feature must also
    // validate a successful history before erasing its last-good observation.
    if(selected||docx.visible)parseIntakeReferenceHistoryJson(response.raw_json,id,query);
    if(selected)publishDocx({...docx,context:captured,hintContext:captured,visible:true,allowed:true,busy:false,
      phase:docx.good?'previous':'idle',message:docx.good?'이전 명시 요청의 관측입니다. 새 읽기는 버튼으로 실행합니다.':'보존 관측은 명시 버튼으로 읽습니다.'});
    else if(docx.visible)publishDocx({...docx,context:captured,hintContext:null,visible:false,allowed:false,busy:false,good:null,phase:'idle'});
    return response;
  } catch(error) {
    if(!referenceDestroyed&&!referenceSuspended&&sameReferenceContext(captured,referenceContext)&&docx.visible){
      try{publishDocx({...docx,allowed:false,hintContext:null,busy:false,phase:'error',message:'이력의 선택 안내를 확인하지 못했습니다. 이전 관측을 유지합니다.'});}
      catch{docx.allowed=false;docxRenderFailure(captured);}
    }
    throw error;
  }
}

async function readDocxObservation() {
  if(!referenceCanChange()||referencePending||referenceSuspended||docx.busy||!docx.allowed||
    !sameReferenceContext(docx.hintContext,referenceContext)||!referenceTransport.hasRetainedDocxSelection())return;
  const captured=referenceContext,ticket=docx.ticket+1,controller=new AbortController();docx.controller?.abort();
  try{publishDocx({...docx,ticket,controller,busy:true,phase:'pending',message:'보존자료를 이번 요청에서 확인하고 있습니다.'});}
  catch{controller.abort();docxRenderFailure(captured);return;}
  if(docx.ticket!==ticket||referenceDestroyed||referenceSuspended){controller.abort();return;}
  const valid=()=>!referenceDestroyed&&!referenceSuspended&&!referencePending&&docx.ticket===ticket&&sameReferenceContext(captured,referenceContext);
  try {
    const raw=await referenceTransport.readCurrent(captured.intake_id,controller.signal,'docx_retained');if(!valid())return;
    const value=parseIntakeReferenceCurrentJson(raw,captured.intake_id,'docx_retained');
    const record=state.records.find(r=>r.intake_id===captured.intake_id);
    if(!docxReferenceMatchesRecord(value,record))throw Error('invalid_intake_reference_view');
    publishDocx({...docx,busy:false,controller:null,good:{context:captured,value},phase:'ready',
      message:'이번 명시 요청 중 확인한 보존 읽기 관측 · 반환 이후 현재성 미확인'});
  }catch(error){
    if(!valid())return;
    const messages={intake_docx_reference_revision_changed:'현재 원본·출처 결합이 변경되어 새 관측을 확인하지 못했습니다.',
      intake_docx_reference_intake_unavailable:'현재 접수 상태에서 보존자료를 확인하지 못했습니다.',
      intake_docx_reference_input_limit:'원자료 읽기 한도를 넘어 새 관측을 확인하지 못했습니다.',
      intake_reference_ui_input_limit:'화면 표시 한도를 넘어 새 관측을 표시하지 못했습니다.',
      intake_reference_ui_access_denied:'접근 허용을 다시 확인해야 합니다. 이력을 새로 조회하세요.',
      intake_reference_ui_unconfigured:'이 접수의 명시 보존 선택을 사용할 수 없습니다.'};
    try{publishDocx({...docx,busy:false,controller:null,allowed:referenceTransport.hasRetainedDocxSelection(),phase:'error',
      message:messages[error.message]||'보존 읽기 응답을 확인하지 못했습니다. 이전 성공 관측이 있으면 유지합니다.'});}
    catch{docxRenderFailure(captured);}
  }finally{
    if(valid()&&docx.busy)publishDocx({...docx,busy:false,controller:null});
  }
}
const roles = {request: '의뢰 자료', product: '제품 자료', reference: '참고 자료'};
const producerKinds = {fixture: '합성 분석 예시', manual: '수동 분석', model: '모델 분석자 선언'};
const errorMessages = {
  store_missing: '접수 저장소가 없습니다. 실행할 때 지정한 workspace를 확인하세요.',
  store_unavailable: '접수 저장소를 읽을 수 없습니다. 파일·권한·스키마 상태를 확인하세요.',
  state_invalid: '저장된 접수 상태를 해석할 수 없습니다. 상태 기록을 확인하세요.',
  unsupported_response: '화면에서 지원하지 않는 API 응답입니다.',
  invalid_snapshot: '응답의 필수 필드 또는 자료 구조가 올바르지 않아 조회 결과를 적용하지 않았습니다.',
  render_failed: '조회 결과를 화면으로 구성하지 못해 이전 상태를 유지합니다.',
};

function el(tag, className = '', text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = String(text);
  return node;
}
function badge(text, tone = 'neutral') { return el('span', `badge ${tone}`, text); }
function stateBadge(record) {
  const current = describeState(record);
  return badge(`${current.symbol} ${current.label}`, current.tone);
}
function section(title, detail) {
  const node = el('section', 'section-rule');
  const heading = el('div', 'section-heading');
  heading.append(el('h3', '', title));
  if (detail) heading.append(el('small', '', detail));
  node.append(heading);
  return node;
}
function empty(title, description) {
  const node = el('div', 'empty');
  const icon = el('span', 'empty-icon', '▤');
  icon.setAttribute('aria-hidden', 'true');
  node.append(icon, el('h2', '', title), el('p', '', description));
  return node;
}
function sources(citations) {
  const details = el('details');
  details.append(el('summary', '', `출처 ${citations.length}개 보기`));
  for (const source of citations) {
    const node = el('div', 'source');
    node.append(el('strong', '', source.path || '파일 경로 미확인'),
      el('div', '', `${roles[source.role] || `역할 미확인 (${source.role || '없음'})`} · ${source.kind === 'pdf_page' ? `PDF ${source.page_number}쪽 · 페이지 안 ` : ''}${source.line_start ?? '?'}–${source.line_end ?? '?'}행`),
      el('blockquote', '', source.quote || '인용문 없음'), el('p', 'mono', `SHA-256 ${source.sha256 || '없음'}`));
    if (source.kind === 'pdf_page') node.append(el('p', 'mono', `추출 ID ${source.extraction_id}`), el('p', 'mono', `페이지 텍스트 SHA-256 ${source.text_sha256}`));
    details.append(node);
  }
  return details;
}
function metadata(entries) {
  const list = el('dl', 'metadata');
  for (const [label, value] of entries) {
    const item = el('div');
    item.append(el('dt', '', label), el('dd', '', value));
    list.append(item);
  }
  return list;
}

function fixtureContext(view = state) {
  const record = view.records.find(item => item.intake_id === view.selected);
  return record ? {intake_id:record.intake_id, revision:record.revision,
    generation:view.snapshotGeneration || 0, request_id:flow.selected} : null;
}
function sameFixtureSource(a, b) {
  return a && b && a.intake_id === b.intake_id && a.revision === b.revision;
}
function buildIntakeWorkflow(record, payload, current, stale) {
  const view=describeIntakeWorkflow(record,{payload,request_id:current.selected,stale,pending:current.pending,now:Date.now()/1000});
  const node=el('section','section-rule');node.id='intake-workflow';
  node.dataset.intakeId=view.context.intake_id;node.dataset.revision=String(view.context.revision);node.dataset.fixtureScope=view.context.fixture_scope;
  node.append(el('h3','','같은 접수의 업무 흐름'),metadata([
    ['현재 접수 / 자료 버전',`${view.context.intake_id} / v${view.context.revision}`],
    ['현재 자료 fingerprint',view.context.revision_fingerprint??'미제공'],
    ['선택 가상 요청 / 기록 버전',view.context.request_id?`${view.context.request_id} / v${view.context.record_revision}`:'미선택'],
    ['선택 기록의 준비 fingerprint',view.context.readiness_fingerprint??'미제공'],
  ]));
  const observation=el('p','inline-note',view.context.relation);observation.id='workflow-observation';observation.setAttribute('role','status');node.append(observation);
  const list=el('ol','question-list');
  for(const step of view.steps){
    const item=el('li','question');item.dataset.workflowStep=step.id;
    item.append(el('h4','',step.title),badge(step.label,step.tone));
    for(const [lineIndex,line] of step.lines.entries()){
      const detail=el('p','inline-note',line);
      if(lineIndex===0&&['virtual','measurement'].includes(step.id))detail.dataset.workflowRelation='';
      item.append(detail);
    }
    if(step.id==='intake'&&view.citations.length)item.append(sources(view.citations));
    if(step.refs.length){const details=el('details');details.append(el('summary','',`공개 근거 참조 ${step.refs.length}개`));const refs=el('ul','fixture-refs');for(const ref of step.refs)refs.append(el('li','mono',ref));details.append(refs);item.append(details);}
    list.append(item);
  }
  node.append(list);return node;
}
function markWorkflowUnconfirmed() {
  const node=$('#intake-workflow');if(!node)return;
  const selected=flow.payload?.records.some(record=>record.request_id===flow.selected);
  node.dataset.fixtureScope=selected?'unconfirmed':'none';
  const message=selected?'이전 조회 당시 문맥 · 현재 관계 미확인':'이 접수·자료 버전의 가상 기록 미확인';
  const status=$('#workflow-observation');if(status)status.textContent=message;
  for(const relation of node.querySelectorAll('[data-workflow-relation]'))relation.textContent=message;
}
function buildFixturePanel(record, view, current = flow) {
  const panel = section('가상 실행 기록', '합성 시도 · 실측·FCC 판정 미검증');
  panel.id = 'fixture-panel';
  const context = fixtureContext(view);
  const matched = sameFixtureSource(current.context, context);
  const payload = matched ? current.payload : null;
  const stale = current.stale || (matched && current.context.generation !== context.generation);
  const controls = el('div', 'section-heading');
  const status = el('p', 'inline-note', matched ? current.status : '가상 기록 조회 대기'); status.id = 'fixture-status'; status.setAttribute('role', 'status');
  const refresh = el('button', 'button', '가상 기록 새로고침'); refresh.id = 'fixture-refresh'; refresh.type = 'button';
  refresh.disabled = matched && current.pending;
  refresh.addEventListener('click', refreshFixtureRuns);
  controls.append(status, refresh);
  const updated = el('p', 'inline-note', matched ? current.updatedText : '아직 조회하지 않음'); updated.id = 'fixture-updated';
  const content = el('div'); content.id = 'fixture-records';
  if (!payload) content.append(el('p', 'muted', '이 접수·자료 버전의 가상 기록을 아직 확인하지 못했습니다.'));
  else if (!payload.storage_available) content.append(el('p', 'muted', '가상 기록 저장 기능이 없는 이전 저장소입니다. 조회로 초기화하거나 자료를 변경하지 않습니다.'));
  else if (!payload.records.length) content.append(el('p', 'muted', '이 접수에 저장된 가상 실행 기록이 없습니다.'));
  else {
    if (stale) content.append(el('p', 'state-note warning', '마지막 성공 기록입니다. 현재 준비 상태와의 관계는 다시 확인해야 합니다.'));
    const list = el('div', 'fixture-list');
    for (const entry of payload.records) {
      const description = describeFixtureRecord(entry, record.revision);
      const button = el('button', 'button fixture-request'); button.type = 'button'; button.dataset.requestId = entry.request_id;
      button.setAttribute('aria-pressed', String(entry.request_id === current.selected));
      button.append(el('span', 'mono', entry.request_id), badge(description.state.label, description.state.tone),
        el('span', 'inline-note', stale ? `v${entry.revision} · 이전 조회 당시 문맥` : description.context));
      button.addEventListener('click', () => {
        flow.gate.invalidate(); flow.controller?.abort();
        const next = {...flow, selected:entry.request_id, pending:false,
          status:flow.stale ? '마지막 성공 기록 · 현재 준비 상태 미확인' : '기록 선택 완료'};
        try {publishFixturePanel(next);} catch {fixtureFailure('화면 구성 실패');}
      });
      list.append(button);
    }
    content.append(list);
    if (payload.more_available) content.append(el('p', 'inline-note', '최신 20건을 표시합니다. 더 오래된 기록이 저장돼 있습니다.'));
    const selected = payload.records.find(entry => entry.request_id === current.selected);
    if (selected) content.append(buildFixtureResult(selected, record.revision, stale));
  }
  panel.append(buildIntakeWorkflow(record,payload,current,stale),controls, updated, content,
    el('p', 'inline-note', '이 가상 실행의 실제 AI 호출 없음 · 실장비 검증 없음 · runtime 재개 지원 없음 · case/plan 자동 생성 없음'));
  return panel;
}
function buildFixtureResult(record, revision, stale) {
  const node = el('article', 'fixture-result'); node.id = 'fixture-result';
  const description = describeFixtureRecord(record, revision), result = description.result;
  node.append(el('h4', '', '선택한 과거 실행'), metadata([
    ['요청 / 자료 버전', `${record.request_id} / v${record.revision}`],
    ['준비 상태 관계', stale ? '이전 조회 당시 문맥 · 현재 관계 미확인' : description.context],
    ['기술 작업 상태', description.state.label], ['선택 recipe', record.recipe_id],
    ['원본 자료 구분', record.source_synthetic ? '합성 접수 자료' : '제공 접수 자료 · 실행은 합성'],
    ['오류 코드', record.error_code || '기록된 오류 없음'],
    ['run ID', record.run_id || '예약 전'], ['runtime instance ID', record.runtime_instance_id || '예약 전'],
    ['준비 fingerprint', record.readiness_fingerprint],
  ]));
  if (!result) {node.append(el('p', 'state-note', '게시된 공개 결과가 없습니다. 작업 상태를 측정 성공으로 해석하지 않습니다.')); return node;}
  const report = record.report;
  node.append(metadata([
    ['하네스 종료', result.termination.label], ['정책 주장', result.policyClaim],
    ['독립 가상 평가', result.assessment.label], ['작업 결과', result.taskOutcome],
    ['정책 ID', report.policy.id], ['평가기 ID', report.assessment.evaluator_id || '기록 없음'],
    ['평가 요약 코드', report.assessment.summary_code || '기록 없음'],
    ['정리', result.cleanup.label], ['미결 요청', `${result.unresolvedCount}개`],
    ['논리 요청 / 재전송', `${report.usage.logical_requests} / ${report.usage.transport_retries}`],
    ['가상 tick / 예약 tick', `${report.usage.tick_delta} / ${report.usage.reserved_ticks}`],
    ['판단 / 소요 ms', `${report.usage.decisions} / ${report.usage.elapsed_ms}`],
  ]));
  const refs = el('ul', 'fixture-refs');
  for (const [label, values] of [
    ['측정 근거', report.evidence.measurement_refs], ['운영 journal', [report.evidence.operator_transcript_ref]],
    ['평가 근거', report.assessment.evidence_refs], ['정리 근거', report.cleanup.evidence_refs], ['미결 요청', report.unresolved_request_ids],
  ]) {
    for (const reference of values) refs.append(el('li', 'mono', `${label}: ${reference}`));
  }
  node.append(el('p', 'inline-note', '근거는 opaque ref로 표시합니다. fresh 여부·측정 단위·기준면과 원본 내용은 이 화면에서 확인되지 않았습니다.'), refs);
  return node;
}
function publishFixturePanel(next) {
  const record = state.records.find(item => item.intake_id === state.selected);
  const target = $('#fixture-panel');
  if (!record || !target) return;
  const prepared = buildFixturePanel(record, state, next);
  target.replaceChildren(...prepared.childNodes);
  Object.assign(flow, next);
}
function fixtureFailure(reason) {
  flow.pending = false;
  flow.stale = Boolean(flow.payload);
  markWorkflowUnconfirmed();
  flow.status = `${reason} · ${flow.payload ? '마지막 성공 기록 유지' : '기록 조회 불가'}`;
  const status = $('#fixture-status'); if (status) status.textContent = flow.status;
  const refresh = $('#fixture-refresh'); if (refresh) refresh.disabled = false;
}
async function refreshFixtureRuns() {
  const context = fixtureContext(); if (!context) return;
  const ticket = flow.gate.begin(context);
  flow.controller?.abort();
  const controller = new AbortController(); flow.controller = controller;
  const timer = setTimeout(() => controller.abort(), 10000);
  flow.pending = true;
  flow.stale = Boolean(flow.payload);
  markWorkflowUnconfirmed();
  $('#fixture-refresh').disabled = true; $('#fixture-status').textContent = '가상 기록 조회 중…';
  try {
    const response = await fetch(`/api/intakes/${encodeURIComponent(context.intake_id)}/fixture-runs`, {signal:controller.signal, cache:'no-store'});
    const raw = await response.json();
    if (!flow.gate.isCurrent(ticket, fixtureContext() || {})) return;
    if (!response.ok) throw new Error('fixture_read_failed');
    const payload = validateFixtureRuns(raw, context);
    requireStableFixtureRecords(flow.payload, payload);
    const selected = payload.records.some(record => record.request_id === flow.selected) ? flow.selected : payload.records[0]?.request_id || '';
    const next = {...flow, context, payload, selected, pending:false, stale:false, status:'가상 기록 조회 완료',
      updatedText:`${seoulTime(new Date().toISOString())} KST 가상 기록 조회`};
    publishFixturePanel(next);
  } catch {
    if (flow.gate.isCurrent(ticket, fixtureContext() || {})) fixtureFailure('가상 기록 조회·검증·화면 구성 실패');
  } finally {clearTimeout(timer);}
}
function syncFixtureContext() {
  const context = fixtureContext();
  if (context && sameFixtureSource(context, flow.context) && context.generation === flow.context.generation) return;
  flow.gate.invalidate(); flow.controller?.abort();
  const retain = sameFixtureSource(context, flow.context);
  Object.assign(flow, {context, payload:retain ? flow.payload : null, selected:retain ? flow.selected : '',
    pending:false, stale:retain && Boolean(flow.payload), status:'가상 기록 조회 대기', updatedText:retain ? flow.updatedText : '아직 조회하지 않음'});
  if (context) refreshFixtureRuns();
}

function buildMetrics(view) {
  const counts = [['전체 접수', view.records.length, '▤', ''],
    ['확인 필요', filterIntakes(view.records, {filter: 'attention'}).length, '!', 'attention'],
    ['분석 대기·분석 중', filterIntakes(view.records, {filter: 'waiting'}).length, '◷', ''],
    ['사용자 보류', filterIntakes(view.records, {filter: 'deferred'}).length, 'Ⅱ', '']];
  return counts.map(([label, value, icon, style]) => {
    const card = el('div', `metric ${style}`);
    card.append(el('p', '', label), el('strong', '', value), el('small', '', '건'));
    const symbol = el('span', 'metric-icon', icon);
    symbol.setAttribute('aria-hidden', 'true');
    card.append(symbol);
    return card;
  });
}

function buildList(view) {
  const filtered = filterIntakes(view.records, {query: $('#search').value, filter: $('#filter').value});
  const selected = filtered.some(item => item.intake_id === view.selected) ? view.selected : filtered[0]?.intake_id || '';
  const nodes = filtered.map(record => {
    const item = el('li');
    const button = el('button', 'intake-item');
    button.type = 'button';
    if (record.intake_id === selected) button.setAttribute('aria-current', 'true');
    const badges = el('div', 'item-badges');
    badges.append(stateBadge(record), badge(record.synthetic ? '합성' : '제공 자료', 'provenance'));
    button.append(badges, el('span', 'item-title', record.bundle),
      el('span', 'item-meta', `${record.source_id} · v${record.revision} · 원본 ${record.files.length}개`));
    button.addEventListener('click', () => {
      if (!referenceCanChange()) return;
      publishView(prepareView({...state, selected: record.intake_id}));
      history.replaceState(null, '', `#${encodeURIComponent(record.intake_id)}`);
      $('#detail-title')?.focus();
      $('#announcer').textContent = `${record.bundle} 상세를 표시했습니다.`;
    });
    item.append(button);
    return item;
  });
  if (!nodes.length) nodes.push(el('li', 'empty small', view.records.length ? '검색·필터 조건에 맞는 접수가 없습니다.' : '등록된 접수가 없습니다.'));
  return {nodes, selected, count: `${filtered.length} / ${view.records.length}건`};
}

function renderFacts(record) {
  const analysis = record.analysis;
  const factsSection = section('사실과 출처', '저장된 분석 · 의미 정확도 미검증');
  const facts = Object.entries(analysis?.facts || {});
  if (!facts.length) factsSection.append(el('p', 'muted', '아직 저장된 사실이 없습니다. 자료의 제품·시장을 기본값으로 채우지 않습니다.'));
  const grid = el('div', 'fact-list');
  for (const [field, fact] of facts) {
    const card = el('article', 'fact');
    const row = el('div', 'label-row');
    row.append(el('span', '', FIELDS[field] || field), badge(FACT_LABELS[fact.status] || `미지원: ${fact.status}`));
    card.append(row, el('p', 'value', fact.value));
    const citations = factSources(record, field);
    if (fact.status === 'user_confirmed') card.append(el('p', 'inline-note', `사용자 응답 이벤트: ${fact.event_id || '미확인'}`));
    else if (citations.length) card.append(sources(citations));
    else card.append(el('p', 'inline-note', '연결된 원문 근거 없음'));
    grid.append(card);
  }
  factsSection.append(grid);
  if (analysis?.submitted?.schema_version === 2) factsSection.append(el('p', 'mono', `분석 문맥 ID ${analysis.submitted.context_id}`));
  const submitted = analysis?.submitted?.facts || [];
  if (submitted.length) {
    const details = el('details', 'history');
    details.append(el('summary', '', `제출된 후보 ${submitted.length}개 · 충돌·불확실 포함`));
    for (const fact of submitted) {
      const item = el('article', 'file');
      item.append(el('strong', '', `${FIELDS[fact.field] || fact.field}: ${fact.value}`),
        el('p', 'inline-note', FACT_LABELS[fact.status] || `미지원 상태: ${fact.status}`));
      if (fact.evidence?.length) item.append(sources(fact.evidence));
      else item.append(el('p', 'inline-note', '원문 근거 없음'));
      details.append(item);
    }
    factsSection.append(details);
  }
  return factsSection;
}

function renderQuestions(record) {
  const questions = record.analysis?.questions || [];
  const node = section('누락·충돌과 다음 조건', `${questions.length}개 질문`);
  if (!record.analysis) node.append(el('p', 'muted', '분석 결과가 없어 누락·충돌을 아직 확인하지 못했습니다.'));
  else if (!questions.length) node.append(el('p', 'muted', '저장된 분석의 열린 질문이 없습니다. 시험 준비 완료를 뜻하지 않습니다.'));
  const list = el('div', 'question-list');
  for (const question of questions) {
    const item = el('article', 'question');
    const type = question.key.startsWith('conflict_') ? '충돌' : question.key.startsWith('missing_') ? '누락'
      : question.key === 'unread_documents' ? '해석 미지원' : '확인 필요';
    item.append(badge(type, 'warning'), el('p', '', question.message));
    const values = question.values || question.paths || [];
    if (values.length) {
      const entries = el('ul');
      for (const value of values) entries.append(el('li', '', value));
      item.append(entries);
    }
    item.append(el('p', 'inline-note', `질문 코드: ${question.key}`));
    list.append(item);
  }
  node.append(list, el('p', 'inline-note', '이 화면은 질문 조회만 제공합니다. 답변·보류 변경은 아직 연결되지 않았습니다.'));
  return node;
}

function renderTestIntentReview(record, review) {
  const node = section('제공된 규정·방법 대조', '제공 시점의 대조 · review_only');
  node.classList.add('test-intent-review');
  const states = {missing:'후보 미제공',proposed:'제공 후보 · 인용 연결 미완료',
    conflicting:'서로 다른 제공 후보',literal_linked:'양쪽 인용의 문자 연결 · 적용성 미판정'};
  const literal = value => value === null ? 'null' : Array.isArray(value) ? JSON.stringify(value) : String(value);
  node.append(el('p', 'inline-note', '제공된 인용의 문자 연결을 대조한 결과입니다. 적용성·현재성·실행 권한은 확인하지 않습니다.'),
    el('p', 'inline-note', '이번 제공 대조에서 모델 호출 없음 · 기존 분석의 모델 실행/품질 미검증'),
    metadata([['제공 접수', `${record.intake_id} · v${review.input_binding.revision}`],
      ['제공 관측의 질문 수', review.questions.length], ['대조 사유', literal(review.reason_codes)]]));
  for (const [field, label] of [['rule','규정'],['method','시험방법']]) {
    const value = review.fields[field], part = el('div', 'source');
    part.append(el('h4', '', label), metadata([['상태', `${states[value.status]} · ${value.status}`],
      ['원 사유 코드', literal(value.reason_codes)]]));
    for (const candidate of value.candidates) {
      const details = el('details', 'history');
      details.append(el('summary', '', candidate.literal), metadata([
        ['제공자 선언', `${candidate.origin === 'model_proposed' ? '모델 제안으로 표시된 제공값' : '명시 공급값'} · ${candidate.origin}`],
        ['문자 연결', candidate.literal_linked], ['사유 코드', literal(candidate.reason_codes)],
        ['제공 기간 대조', literal(candidate.period_checks)],
      ]), el('p', 'inline-note', '제공 결과에 담긴 인용 위치입니다. 다른 현재 사실의 인용문을 가져와 붙이지 않습니다.'));
      for (const ref of candidate.intake_refs) details.append(el('p', 'mono', `원 analysis fact_index=${ref.fact_index} · evidence_index=${ref.evidence_index}`));
      for (const ref of candidate.basis_refs) details.append(el('p', 'mono', `${ref.document_id} · PDF ${ref.page_number}쪽 · ${ref.line_start}–${ref.line_end}행 · 텍스트 SHA-256 ${ref.text_sha256}`));
      part.append(details);
    }
    node.append(part);
  }
  const checks = metadata(['intake_citations_checked','basis_literals_checked'].map(key=>[key,review.verification[key]]));
  checks.classList.add('test-intent-checks');
  const authority = metadata(Object.entries(review.verification).filter(([key])=>!['intake_citations_checked','basis_literals_checked'].includes(key)));
  authority.classList.add('test-intent-authority');
  node.append(el('h4', '', '인용 검사 수행 여부'), checks, el('h4', '', '미검증·미승인 범위'), authority);
  return node;
}

function renderFiles(record) {
  const node = section('원본과 자료 버전', '저장된 메타데이터 · 바이너리 열기 미연결');
  for (const revision of [...record.history].reverse()) {
    const details = el('details', 'history');
    details.open = revision.revision === record.revision;
    details.append(el('summary', '', `v${revision.revision}${revision.revision === record.revision ? ' · 현재 버전' : ' · 이전 버전'} · ${revision.files.length}개 · ${seoulTime(revision.created_at)} KST`));
    for (const file of revision.files) {
      const item = el('div', 'file');
      item.append(el('strong', '', `${file.path} · ${bytes(file.bytes)}`), el('span', 'mono', `SHA-256 ${file.sha256}`));
      details.append(item);
    }
    node.append(details);
  }
  return node;
}

function renderJobs(record) {
  const node = section('분석 작업', '분석 완료 ≠ 시험 완료');
  if (!record.jobs.length) { node.append(el('p', 'muted', '저장된 분석 작업이 없습니다.')); return node; }
  const table = el('table', 'data-table');
  const head = el('thead');
  const header = el('tr');
  for (const name of ['작업 / 버전', '상태 / 시도', '오류 / 임대 만료']) header.append(el('th', '', name));
  head.append(header);
  const body = el('tbody');
  for (const job of [...record.jobs].reverse()) {
    const row = el('tr');
    const first = el('td'); first.append(el('p', 'mono', job.job_id), el('p', '', `v${job.revision}${job.revision === record.revision ? ' · 현재' : ' · 이전'}`));
    const second = el('td'); second.append(el('p', '', JOB_LABELS[job.state] || `미지원: ${job.state}`), el('p', '', `${job.attempt}회 시도`));
    const third = el('td'); third.append(el('p', '', job.error_code || '기록된 오류 없음'), el('p', '', job.lease_until == null ? '임대 기록 없음' : `${seoulTime(job.lease_until)} KST`));
    row.append(first, second, third); body.append(row);
  }
  table.append(head, body);
  const scroll = el('div', 'table-scroll'); scroll.append(table); node.append(scroll);
  return node;
}

function noticeNode(notice, includeLink, view) {
  const record = view.records.find(item => item.intake_id === notice.intake_id);
  const node = el('article', 'notice');
  const header = el('div', 'notice-meta');
  header.append(badge(`기록 #${notice.notification_id}`), el('span', '', `${record?.bundle || notice.intake_id} · v${notice.revision}`),
    el('span', 'muted', noticeContext(notice, record).label));
  node.append(header);
  const payload = notice.payload || {};
  node.append(el('p', '', `생성 당시: ${describeState({status: 'analyzed', analysis: payload}).label}`));
  if (payload.questions?.length) {
    const list = el('ul', 'notice-questions');
    for (const question of payload.questions) list.append(el('li', '', question.message));
    node.append(list);
  }
  node.append(el('p', 'inline-note', '로컬 기록 · 외부 전송/읽음 여부 없음 · 현재 상세 상태와 다를 수 있음'));
  if (includeLink && record) {
    const button = el('button', 'button', '현재 접수 보기'); button.type = 'button';
    button.addEventListener('click', () => {
      if (!referenceCanChange()) return;
      $('#search').value = ''; $('#filter').value = 'all';
      changeView('intakes'); publishView(prepareView({...state, selected: record.intake_id})); $('#detail-title')?.focus();
    }); node.append(button);
  }
  return node;
}

function buildDetail(view,docxNext=docx) {
  const record = view.records.find(item => item.intake_id === view.selected);
  if (!record) {
    return [empty(view.records.length ? '표시할 접수가 없습니다' : '첫 접수를 기다리고 있습니다', view.records.length
      ? '검색어 또는 상태 필터를 변경하세요.' : '등록된 접수 자료가 없습니다. 기존 접수 서비스로 자료가 저장되면 새로고침하여 확인할 수 있습니다.')];
  }
  const current = describeState(record);
  const header = el('header', 'detail-header');
  const kicker = el('div', 'detail-kicker'); kicker.append(stateBadge(record), badge(record.synthetic ? '합성 자료 · 개발 검증용' : '제공 자료 · 실측 미확인', 'provenance'));
  const title = el('h2', '', record.bundle); title.id = 'detail-title'; title.tabIndex = -1;
  header.append(kicker, title, el('p', 'mono detail-id', `${record.intake_id} · revision ${record.revision}`));
  const body = el('div', 'detail-body');
  const note = el('div', `state-note ${current.tone}`); note.append(el('strong', '', current.label), el('p', '', current.hint));
  const producer = record.analysis?.submitted?.producer;
  body.append(note, metadata([
    ['입력 출처', record.source_id], ['자료 버전', `v${record.revision} · ${record.files.length}개 파일`],
    ['접수 진행 위임', record.delegated ? '저장됨 · 접수 업무 한정' : '저장된 위임 없음'],
    ['분석 출처', producer ? `${producerKinds[producer.kind] || producer.kind} · ${producer.name}` : '분석 전'],
    ['시료 · 물리 위치', '제공 안 됨'], ['실측 지원', `미검증 (${record.measurement_support})`],
    ['접수 / 후속 상태 코드', `${record.status} / ${record.analysis?.next_action || '없음'}`],
    ['보류 의사', record.deferred ? '저장됨' : '저장된 보류 없음'],
  ]));
  const intent = (view.intentReviews || []).find(value=>value.input_binding.intake_id===record.intake_id&&value.input_binding.revision===record.revision);
  if (intent) body.append(renderTestIntentReview(record, intent));
  body.append(renderFacts(record), renderQuestions(record), buildFixturePanel(record, view), renderJobs(record), renderFiles(record));
  const notices = section('이 접수의 알림 기록', '전송·읽음 상태 미제공');
  const related = view.notices.filter(notice => notice.intake_id === record.intake_id);
  if (!related.length) notices.append(el('p', 'muted', '저장된 알림이 없습니다.'));
  else for (const notice of [...related].reverse()) notices.append(noticeNode(notice, false, view));
  body.append(notices);
  const docxSection=buildDocxSection(record,docxNext);if(docxSection)body.append(docxSection);
  return [header, body];
}

function buildNotifications(view) {
  const heading = el('div', 'section-heading'); heading.append(el('h2', '', '저장된 알림 기록'), el('small', '', `${view.notices.length}개`));
  const nodes = [heading, el('p', 'muted', '알림 생성 당시의 기록입니다. 조회로 읽음 처리하거나 외부에 발송하지 않습니다.')];
  if (!view.notices.length) nodes.push(empty('알림 기록이 없습니다', '분석 결과로 생성된 로컬 알림이 여기에 표시됩니다.'));
  else for (const notice of [...view.notices].reverse()) nodes.push(noticeNode(notice, true, view));
  return nodes;
}

function prepareView(next) {
  // Build every panel off-DOM before committing either DOM or application state.
  const list = buildList(next);
  const view = {...next, selected: list.selected};
  const selected = view.records.find(record => record.intake_id === view.selected);
  const referenceContext = validateIntakeReferenceContext(selected ? {intake_id:selected.intake_id,
    revision:selected.revision, snapshotGeneration:view.snapshotGeneration ?? 0} : null);
  const docxNext=projectDocxContext(referenceContext,selected);
  return {view, list, referenceContext,docxNext, metrics: buildMetrics(view), detail: buildDetail(view,docxNext), notifications: buildNotifications(view)};
}

function publishView(prepared) {
  if (!referenceCanChange()) return;
  referenceGuard = true;
  try {
    $('#metrics').replaceChildren(...prepared.metrics);
    $('#intake-list').replaceChildren(...prepared.list.nodes);
    $('#detail-panel').replaceChildren(...prepared.detail);
    $('#notification-view').replaceChildren(...prepared.notifications);
    $('#result-count').textContent = prepared.list.count;
    $('#notice-count').textContent = prepared.view.notices.length;
    $('#last-updated').textContent = prepared.view.updatedText;
    Object.assign(state, prepared.view);
    if(docx.ticket!==prepared.docxNext.ticket)docx.controller?.abort();
    Object.assign(docx,prepared.docxNext);
    referenceContext = prepared.referenceContext;
    referenceActions.setContext(referenceContext);
    if (referenceDestroyed) return;
    referenceTransport.setContext(prepared.referenceContext);
    referencePanel.setContext(prepared.referenceContext);
    syncFixtureContext();
  } finally { if (!referenceDestroyed) referenceGuard = false; }
}

function changeView(view) {
  if (!referenceCanChange()) return;
  state.view = view;
  $('#intake-view').hidden = view !== 'intakes'; $('#notification-view').hidden = view !== 'notifications';
  $('#intake-reference-panel').hidden = view !== 'intakes';
  $('#intake-reference-actions-panel').hidden = view !== 'intakes';
  $('#page-title').textContent = view === 'intakes' ? '접수 운영' : view === 'ai-connections' ? '모델 연결' : '알림 기록';
  $('#metrics').hidden = view === 'ai-connections';
  $('.scope-note').hidden = view === 'ai-connections';
  $('#last-updated').hidden = view === 'ai-connections';
  $('.mode-tag').textContent = view === 'ai-connections' ? '설정 · 등록 합성 테스트' : '◉ 조회 전용';
  if (view === 'ai-connections') showAIConnectionPanel(); else aiConnectionPanel?.hide();
  for (const button of document.querySelectorAll('[data-view]')) {
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
}

async function refresh() {
  if (!referenceCanChange()) return;
  const request = ++state.request;
  if (!setReferencePending(true)) return;
  state.controller?.abort();
  const controller = new AbortController(); state.controller = controller;
  const timer = setTimeout(() => controller.abort(), 10000);
  $('#refresh').disabled = true; $('#refresh').textContent = '조회 중…';
  $('#intake-view').setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/api/intakes', {signal: controller.signal, cache: 'no-store'});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.code || 'store_unavailable');
    validateSnapshot(payload);
    if (request !== state.request || !referenceCanChange()) return;
    let prepared;
    try { prepared = prepareView({...state, records: payload.intakes, notices: payload.notifications,
      intentReviews:payload.intake_test_intent_reviews || [], loaded: true,
      updatedText: `${seoulTime(payload.generated_at)} KST 조회`, snapshotGeneration:(state.snapshotGeneration || 0) + 1}); }
    catch { throw new Error('render_failed'); }
    publishView(prepared);
    $('#error-banner').hidden = true;
    $('#announcer').textContent = `접수 ${state.records.length}건을 조회했습니다.`;
  } catch (error) {
    if (request !== state.request || !referenceCanChange()) return;
    const message = Object.hasOwn(errorMessages, error.message) ? errorMessages[error.message]
      : '서버 연결 또는 응답을 확인할 수 없습니다. 서버 실행 상태를 확인하고 다시 시도하세요.';
    const banner = $('#error-banner');
    banner.replaceChildren(el('strong', '', '조회 실패'), el('p', '', message),
      el('p', 'inline-note', state.loaded ? '아래 내용은 마지막 성공 조회 시점의 기록입니다. 최신 상태가 아닐 수 있습니다.' : '저장소가 비었다는 뜻이 아닙니다. 접수 건수를 확인하지 못했습니다.'));
    const retry = el('button', 'button', '다시 조회'); retry.type = 'button'; retry.addEventListener('click', refresh);
    if (error.message === 'invalid_snapshot') banner.append(el('p', 'inline-note', `응답 필드: ${error.path}`));
    banner.append(retry); banner.hidden = false;
    if (!state.loaded) {
      $('#result-count').textContent = '조회 불가'; $('#metrics').replaceChildren();
      $('#intake-list').replaceChildren(el('li', 'empty small', '목록 조회 실패'));
      $('#detail-panel').replaceChildren(empty('접수를 읽지 못했습니다', message));
    }
  } finally {
    clearTimeout(timer);
    if (request === state.request && referenceCanChange()) {
      if (!referenceSuspended) {
        setReferencePending(false);
      }
      $('#refresh').disabled = false; $('#refresh').textContent = '↻ 새로고침';
      $('#intake-view').setAttribute('aria-busy', 'false');
    }
  }
}

addEventListener('pagehide', event => {
  if (event.persisted) {
    if (!referenceCanChange()) return;
    referenceSuspended = true;
    setReferencePending(true);
  } else {
    if (referenceDestroyed) return;
    referenceDestroyed = true;
    docx.controller?.abort();docx.ticket++;docx.controller=null;docx.good=null;docx.allowed=false;docx.visible=false;
    $('.docx-retained-observation')?.remove();
    referenceActions.root.removeEventListener('intake-reference-history-refresh', refreshRegisteredHistory);
    referenceActions.destroy();
    referenceTransport.destroy();
    referencePanel.destroy();
  }
});
addEventListener('pageshow', event => {
  if (event.persisted && referenceCanChange()) {
    referenceSuspended = false;
    refresh();
  }
});

function renderFilteredIntakes() {
  if (!state.loaded || !referenceCanChange()) return;
  publishView(prepareView(state));
}
$('#search').addEventListener('input', renderFilteredIntakes);
$('#filter').addEventListener('change', renderFilteredIntakes);
$('#refresh').addEventListener('click', () => state.view === 'ai-connections' ? aiConnectionPanel?.refresh() : refresh());
for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => changeView(button.dataset.view));
refresh();
