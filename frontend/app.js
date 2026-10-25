import {FIELDS, FACT_LABELS, JOB_LABELS, describeState, factSources, filterIntakes, noticeContext, seoulTime, bytes, validateSnapshot, docxReferenceMatchesRecord} from './model.mjs';
import {validateFixtureRuns, describeFixtureRecord, describeIntakeWorkflow, requireStableFixtureRecords, createFixtureReadGate, parseConductedPlanPreview, conductedPreviewValue, parseConductedResultView, describeIntakeGapQueue, parseConductedArtifactReadback, describeConductedArtifactStorage, CONDUCTED_ARTIFACT_HTTP_BYTES} from './intake_flow_model.mjs';
import {validateIntakeReferenceContext,parseIntakeReferenceHistoryJson,parseIntakeReferenceCurrentJson} from './intake-references/model.mjs';
import {createIntakeReferenceReview} from './intake-references/view.mjs';
import {createIntakeReferenceTransport} from './intake-references/transport.mjs';
import {createIntakeReferenceActionsReview} from './intake-reference-actions/actions.mjs';

const $ = selector => document.querySelector(selector);
const state = {records: [], notices: [], selected: location.hash.slice(1), loaded: false, request: 0, view: 'intakes'};
const flow = {gate:createFixtureReadGate(), context:null, payload:null, selected:'', pending:false,
  stale:false, status:'가상 기록 조회 대기', updatedText:'아직 조회하지 않음'};
const conducted={gate:createFixtureReadGate(),context:null,value:null,controller:null,pending:false,parentPending:true,stale:true,status:'가상 계획 미리보기 조회 대기',errorCode:null};
const resultView={gate:createFixtureReadGate(),context:null,value:null,controller:null,pending:false,parentPending:true,stale:true,status:'전도 결과 제공 기록 조회 대기',errorCode:null};
const storageView={gate:createFixtureReadGate(),context:null,value:null,controller:null,pending:false,parentPending:true,stale:true,status:'산출물 저장 읽기 미관측',errorCode:null};
const gapQueueState={intakeStale:true,parentPending:true,intakeCode:null};
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
function workflowProjection(record,payload,current,stale,snapshot=state){
  const freshParent=(snapshot.snapshotGeneration??0)!==(state.snapshotGeneration??0);
  return describeIntakeWorkflow(record,{payload,request_id:current.selected,stale,pending:current.pending,now:Date.now()/1000,
    provided:{generation:snapshot.snapshotGeneration||0,
      intakeStale:snapshot.view!=='intakes'||(!freshParent&&(gapQueueState.intakeStale||gapQueueState.parentPending)),
      plan:conducted,result:resultView,storage:storageView}});
}
function buildWorkflowStepSummary(step){
  const summary=el('div');summary.style.minWidth='0';summary.style.overflowWrap='anywhere';summary.dataset.workflowSummary='';summary.dataset.providedScope=step.provided_scope||'none';
  const label=badge(step.label,step.tone);label.dataset.workflowSummaryLabel='';summary.append(label);
  for(const [index,line]of step.lines.entries()){
    const detail=el('p','inline-note',line);detail.dataset.workflowSummaryLine='';
    if(index===0&&['virtual','measurement'].includes(step.id))detail.dataset.workflowRelation='';summary.append(detail);
  }
  if(step.previous_lines?.length){
    const previous=el('details');previous.dataset.workflowPrevious='';previous.append(el('summary','','제공 이전·차단 관측 원형'));
    for(const line of step.previous_lines)previous.append(el('p','inline-note',line));summary.append(previous);
  }
  return summary;
}
function buildIntakeWorkflow(record, payload, current, stale, snapshot=state) {
  const view=workflowProjection(record,payload,current,stale,snapshot);
  const node=el('section','section-rule');node.id='intake-workflow';
  node.dataset.intakeId=view.context.intake_id;node.dataset.revision=String(view.context.revision);node.dataset.fixtureScope=view.context.fixture_scope;node.dataset.providedScope=view.provided.scope;
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
    item.append(el('h4','',step.title),buildWorkflowStepSummary(step));
    if(step.id==='intake'&&view.citations.length)item.append(sources(view.citations));
    if(step.id==='plan')item.append(buildConductedPlanPreview(record,snapshot));
    if(step.id==='measurement')item.append(buildConductedResult(record,snapshot));
    if(step.id==='assessment')item.append(buildConductedArtifactStorage(record,snapshot));
    if(step.refs.length){const details=el('details');details.append(el('summary','',`${step.reference_source||'공개'} 근거 참조 ${step.refs.length}개`));const refs=el('ul','fixture-refs');for(const ref of step.refs)refs.append(el('li','mono',ref));details.append(refs);item.append(details);}
    list.append(item);
  }
  node.append(buildGapQueue(record,snapshot),list);return node;
}
function markWorkflowUnconfirmed() {
  refreshWorkflowSummary();
}
function refreshWorkflowSummary(){
  const node=$('#intake-workflow'),record=state.records.find(item=>item.intake_id===state.selected);
  if(!node||!record||node.dataset.intakeId!==record.intake_id||node.dataset.revision!==String(record.revision))return;
  try{
    const context=fixtureContext(),matched=sameFixtureSource(flow.context,context),payload=matched?flow.payload:null;
    const stale=flow.stale||!matched||flow.context?.generation!==context?.generation;
    const view=workflowProjection(record,payload,flow,stale),parts=view.steps.map(step=>({
      target:node.querySelector(`[data-workflow-step="${step.id}"] [data-workflow-summary]`),prepared:buildWorkflowStepSummary(step)}));
    if(parts.some(part=>!part.target))throw Error('workflow_summary_target_missing');
    for(const part of parts)part.target.replaceWith(part.prepared);
    node.dataset.fixtureScope=view.context.fixture_scope;node.dataset.providedScope=view.provided.scope;
    $('#workflow-observation').textContent=view.context.relation;
  }catch{
    node.dataset.providedScope='unconfirmed';
    const status=$('#workflow-observation');if(status)status.textContent='이전 업무 요약 · 현재 관계·표시 미확인';
    for(const summary of node.querySelectorAll('[data-workflow-summary]')){
      summary.dataset.providedScope='unconfirmed';const label=summary.querySelector('[data-workflow-summary-label]');
      if(label)label.textContent='이전 업무 요약 · 현재 관계 미확인';
    }
  }
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
  panel.append(buildIntakeWorkflow(record,payload,current,stale,view),controls, updated, content,
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

function conductedContext(view=state){
  const record=view.records.find(item=>item.intake_id===view.selected);
  return record&&view.view==='intakes'?{intake_id:record.intake_id,revision:record.revision,generation:view.snapshotGeneration||0,request_id:''}:null;
}
function buildConductedPlanPreview(record,snapshot=state,current=conducted){
  const context=conductedContext(snapshot),matched=sameFixtureSource(context,current.context);
  const value=matched?current.value:null,stale=current.stale||!matched||context.generation!==current.context.generation;
  const area=el('section','section-rule');area.id='conducted-plan-preview';
  area.dataset.previewStatus=value?.plan_input.status||'unavailable';area.dataset.previewCurrent=String(Boolean(value&&!stale&&!current.pending&&!current.parentPending));
  area.append(el('h4','','가상 계획 미리보기'));
  const status=el('p','inline-note',stale&&value?'이전 관측 · 현재 관계 미확인':matched?current.status:'가상 계획 미리보기 조회 대기');
  status.id='conducted-plan-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const refresh=el('button','button','가상 계획 미리보기 새로고침');refresh.id='conducted-plan-refresh';refresh.type='button';refresh.setAttribute('aria-disabled',String(current.pending||current.parentPending));
  refresh.addEventListener('click',()=>{if(refresh.getAttribute('aria-disabled')!=='true')void refreshConductedPlanPreview();});
  area.append(status,refresh,el('p','inline-note','현재 제공 context의 읽기 관측 · 원 모델 prompt 복원 아님 · 합성 계획 입력이며 실행 권한 없음'));
  const content=el('div');content.id='conducted-plan-content';
  if(value){
    const p=value.plan_input,plan=p.plan,format=conductedPreviewValue;
    content.append(badge(p.status==='ready_for_simulation'?'가상 계획 입력 준비 · ready_for_simulation':'가상 계획 입력 보류 · blocked',p.status==='ready_for_simulation'?'info':'warning'),metadata([
      ['현재 제공 접수 / 버전',`${value.intake_id} / v${value.revision}`],['현재 제공 context C1 SHA-256',value.context_sha256],
      ['제공 설정 선택',({matched:'같은 접수·버전의 명시 선택',not_provided:'제공 설정 없음',other_intake:'다른 접수의 설정 · 적용 안 함',revision_changed:'다른 버전의 설정 · 적용 안 함'})[value.selection_status]],
      ['분석 원 context ID',format(p.binding.analysis_context_id)],['분석 SHA-256',format(p.binding.analysis_sha256)],['계획 입력 SHA-256',p.binding.plan_sha256],
      ['합성 방법 / 버전',`${format(plan.method_id)} / ${format(plan.method_version)}`],['합성 metric / 기준면',`${format(plan.metric)} / ${format(plan.reference_plane)}`],
      ['규제 한계값',format(plan.numeric_limit_dbm)],['불확도',format(plan.uncertainty_db)],['판정',plan.assessment],
    ]));
    content.append(el('p','inline-note','규제 적합성 미평가 · 실측 예측력 미평가 · 규격 판정/실측 대조/실행 승인은 별도입니다. 거절한 원 제공값을 입력값으로 복원하지 않습니다.'));
    const fields=['frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','crest_factor_db'],labels=['주파수','합성 on-average 전력','대역폭','듀티','변조 선언','crest factor'],units=['Hz','dBm','Hz','ratio','label','dB'];
    const scroll=el('div','table-scroll'),table=el('table','data-table'),head=el('tr'),body=el('tbody');table.append(el('caption','','명시 제공된 가상 source 설정 · 관측 측정값 아님'));
    for(const label of ['항목','가상 입력값','계약 단위','근거']){const th=el('th','',label);th.scope='col';head.append(th);}const thead=el('thead');thead.append(head);table.append(thead);
    for(const [index,field]of fields.entries()){
      const row=el('tr');row.dataset.planSetting=field;row.append(el('td','',labels[index]),el('td','mono',format(plan.source_settings[field])),el('td','',units[index]));
      const cell=el('td'),basis=plan.basis_refs[field];if(basis===null)cell.textContent='근거 미제공(null)';
      else{const detail=el('details');detail.append(el('summary','',basis.kind==='source_cited'?'자료 인용 · 합성 조건':'개발자 선언 합성'),el('p','inline-note',`근거 제공값: ${format(basis.value)} ${basis.unit}`));if(basis.evidence.length)detail.append(sources(basis.evidence));else detail.append(el('p','inline-note','개발자가 명시한 합성 설정 · 원문/규정/실측 근거 아님'));cell.append(detail);}
      row.append(cell);body.append(row);
    }
    table.append(body);scroll.append(table);content.append(scroll);
    const gaps=el('div','question-list');
    for(const [index,gap]of p.gaps.entries()){const node=el('article','question');node.dataset.planGap=String(index);node.append(badge(gap.blocking?'입력 차단 공백':'후속 준비 공백',gap.blocking?'warning':'neutral'),el('p','',`${gap.field} · ${gap.code}`),el('p','mono',`원 제공값: ${format(gap.provided)}`));gaps.append(node);}content.append(gaps);
    const facts=el('details');facts.append(el('summary','','제품·목적·시장과 원 사실·질문'));
    facts.append(metadata(Object.entries(p.intake.facts).map(([field,fact])=>[FIELDS[field],`${fact.value} · ${FACT_LABELS[fact.status]}`])),el('p','inline-note',`원 누락: ${format(p.intake.missing_fields)} · 후속 실물 준비 누락: ${format(p.intake.follow_up_missing_fields)}`));
    for(const fact of p.intake.source_facts){const item=el('article','file');item.append(el('strong','',`${FIELDS[fact.field]}: ${fact.value}`),el('p','inline-note',FACT_LABELS[fact.status]),sources(fact.evidence));facts.append(item);}
    for(const q of p.intake.questions)facts.append(el('p','inline-note',`${q.key}: ${q.message}${q.values?' · '+format(q.values):q.paths?' · '+format(q.paths):''}`));content.append(facts);
    content.append(el('p','inline-note','아래는 순수 계획 어댑터의 검증 범위이며 현재 DB·보존 원문 읽기 관측과 구분합니다.'),metadata([
      ['인용 검증',p.verification.evidence],['버전 범위',p.verification.current_version],['순수 어댑터의 원 bytes',p.verification.source_bytes],
      ['규제 / 실측 예측',`${p.verification.regulatory} / ${p.verification.measurement_prediction}`],['실행 권한',String(p.verification.execution_authority)],
    ]));
  }
  area.append(content);return area;
}
function publishConductedPreview(next){
  const record=state.records.find(item=>item.intake_id===state.selected),target=$('#conducted-plan-preview');if(!record||!target)return false;
  const prepared=buildConductedPlanPreview(record,state,next);target.replaceWith(prepared);Object.assign(conducted,next);refreshGapQueue();return true;
}
function markConductedStale(message){
  conducted.stale=true;const target=$('#conducted-plan-preview');if(target)target.dataset.previewCurrent='false';
  const status=$('#conducted-plan-status');if(status)status.textContent=message;refreshGapQueue();
}
function retireConductedObservation(){
  conducted.gate.invalidate();conducted.controller?.abort();conducted.controller=null;conducted.pending=false;conducted.parentPending=true;
  if(conducted.value)markConductedStale('이전 관측 · 접수 자료의 현재 관계 미확인');
  else conducted.stale=true;
  $('#conducted-plan-refresh')?.setAttribute('aria-disabled','true');
}
async function refreshConductedPlanPreview(){
  const context=conductedContext();if(!context||conducted.pending||conducted.parentPending||referenceDestroyed||referenceSuspended)return;
  const ticket=conducted.gate.begin(context);conducted.controller?.abort();const controller=new AbortController();conducted.controller=controller;
  const timer=setTimeout(()=>controller.abort(),10000);
  const current=()=>conducted.gate.isCurrent(ticket,conductedContext()||{})&&!referenceDestroyed&&!referenceSuspended;
  try{
    if(!publishConductedPreview({...conducted,context,pending:true,errorCode:null,stale:Boolean(conducted.value),status:'가상 계획 미리보기 조회 중'}))return;
    const response=await fetch(`/api/intakes/${encodeURIComponent(context.intake_id)}/conducted-plan-preview`,{signal:controller.signal,cache:'no-store'});
    if(!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers.get('content-type')||''))throw Error();
    const length=response.headers.get('content-length');if(length!==null&&(!/^\d+$/.test(length)||Number(length)>262144))throw Error();
    const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let raw='',size=0;
    try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>262144){await reader.cancel();throw Error();}raw+=decoder.decode(part.value,{stream:true});}raw+=decoder.decode();}finally{reader.releaseLock();}
    if(!current())return;
    if(!response.ok){const error=JSON.parse(raw);const code=error?.error?.code;if(typeof code!=='string'||!/^intake_conducted_preview_[a-z_]+$/.test(code))throw Error();throw Error(code);}
    const value=parseConductedPlanPreview(raw,context);if(!current())return;
    publishConductedPreview({...conducted,context,value,pending:false,errorCode:null,stale:false,status:'가상 계획 미리보기 조회 완료'});
  }catch(error){controller.abort();if(current()){
    const label=({intake_conducted_preview_v2_pdf_required:'현재 완료 V2/PDF 필요',intake_conducted_preview_synthetic_required:'합성 접수만 지원',intake_conducted_preview_analysis_unavailable:'현재 완료 분석 미제공',intake_conducted_preview_source_invalid:'보존 자료·분석의 무결성 미확인'})[error.message]||'응답·전송·형상·화면 확인 실패';
    conducted.pending=false;conducted.errorCode=queueErrorCode(error);conducted.status=conducted.value?'조회 실패 · 이전 관측 · 현재 관계 미확인':`가상 계획 미리보기 미지원 · ${label}`;markConductedStale(conducted.status);
  }}finally{clearTimeout(timer);if(current()){conducted.pending=false;conducted.controller=null;$('#conducted-plan-refresh')?.setAttribute('aria-disabled','false');refreshGapQueue();}}
}
function syncConductedContext(){
  const context=conductedContext();if(context&&sameFixtureSource(context,conducted.context)&&context.generation===conducted.context.generation)return;
  conducted.gate.invalidate();conducted.controller?.abort();const retain=sameFixtureSource(context,conducted.context);
  Object.assign(conducted,{context,value:retain?conducted.value:null,controller:null,pending:false,stale:true,errorCode:null,status:'가상 계획 미리보기 조회 대기'});
  if(context)void refreshConductedPlanPreview();else refreshGapQueue();
}


function buildConductedResult(record,snapshot=state,current=resultView){
  const context=conductedContext(snapshot),matched=sameFixtureSource(context,current.context),value=matched?current.value:null;
  const stale=current.stale||!matched||context.generation!==current.context.generation,area=el('section','section-rule');area.id='conducted-result-view';
  area.dataset.pending=String(current.pending||current.parentPending);area.dataset.sourceKind='provided_snapshot';
  area.dataset.current=String(Boolean(value&&!stale&&!current.pending&&!current.parentPending&&value.relation.status==='matched'));
  area.dataset.resultStatus=value?.result.status||'unavailable';
  area.append(el('h4','','전도 측정·계산 제공 기록'));
  const status=el('p','inline-note',stale&&value?'이전 관측 · 현재 관계 미확인':matched?current.status:'전도 결과 제공 기록 조회 대기');status.id='conducted-result-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');area.append(status);
  area.append(el('p','inline-note','provided_snapshot · 생성 origin/진위 미확인 · 저장/실시간 결과 조회 미지원 · 실제 AI 호출 여부 unknown'));
  const content=el('div');content.id='conducted-result-content';const format=conductedPreviewValue;
  if(value){
    const r=value.result,raw=r.raw_measurement,c=r.calculation;
    content.append(el('h5','','제공 원수치·계산'));
    content.append(badge(`제공 원 상태: ${r.status}`,r.status==='invalid'?'danger':r.status==='incomplete'?'warning':'info'),metadata([
      ['현재 접수 / 자료 버전',`${value.intake_id} / v${value.revision}`],['제공 snapshot 버전',String(value.relation.provided_revision)],['현재 제공 context C1 SHA-256',value.context_sha256],
      ['현재 계획 binding 대조',value.relation.status==='matched'?'일치 · 제공 결과의 생성·물리 진위 승인이 아님':'차단 · 현재 계획의 결과로 사용 불가'],['차단 이유',format(value.relation.reasons)],
      ['원 run / runtime',`${format(r.binding.run_id)} / ${format(r.binding.runtime_instance_id)}`],['선택 원 event',format(r.binding.measurement_ref)],
    ]));
    const expected=el('details');expected.append(el('summary','','명시 expected-current binding6'),metadata([['제공된 결합값',format(value.expected_current_binding)]]));content.append(expected);
    if(raw===null)content.append(el('p','inline-note','원 측정 미생성(null)'));
    else{
      const packet=raw.packet;
      content.append(metadata([['원 값 / 단위',`${format(packet.value)} / ${format(packet.unit)}`],['원 기준면',format(raw.reference_plane)],['원 quantity 선언',format(raw.quantity)],['원 event / seq',`${format(raw.event_id)} / ${format(raw.sequence)}`],['원 device / tick / setup revision',`${format(raw.device_id)} / ${format(raw.tick)} / ${format(raw.setup_revision)}`]]));
      const detail=el('details');detail.append(el('summary','','원 packet 전체 · 실패 원형 포함'),metadata([['제공 원 JSON',format(packet)]]));content.append(detail);
    }
    content.append(metadata([['원 단위 변환 W',format(c.raw_power_w)],['단위 변환 원 기준면',format(c.raw_reference_plane)],['보정 target 기준면',format(c.target_reference_plane)],['제공 보정 dBm / W',format(c.corrected)],['규범 판정',c.conformity.status],['verdict / limit / uncertainty',`${format(c.conformity.verdict)} / ${format(c.conformity.numeric_limit_dbm)} / ${format(c.conformity.uncertainty_db)}`]]));
    content.append(el('p','inline-note','규범 적합성·최종 판정 승인 미평가 · 실물/교정/전체 업무 검증 아님 · 화면에서 수치·보정을 다시 계산하지 않습니다.'));
    const ledger=el('details');ledger.append(el('summary','',`원 correction ledger ${c.correction_ledger.length}개 · 전파 손실과 역보상 구분`));
    for(const [i,row]of c.correction_ledger.entries()){const item=el('article','file');item.dataset.resultLedger=String(i);item.append(metadata([['device / output / setting',`${row.device_id} / ${row.output_port} / ${row.setting}`],['원 loss / propagation / compensation (dB)',`${format(row.loss_db)} / ${format(row.propagation_db)} / ${format(row.compensation_db)}`],['이미 적용 선언',format(row.already_applied)],['record index / request / tick / revision',`${format(row.record_index)} / ${row.request_id} / ${format(row.tick)} / ${format(row.setup_revision)}`]]));ledger.append(item);}content.append(ledger);
    const setup=el('details');setup.append(el('summary','','제공 setup · topology · 선택 path'),metadata([['원 records',format(r.setup_provenance.records)],['원 topology',format(r.setup_provenance.topology)],['원 path',format(r.setup_provenance.path)]]));content.append(setup);
    const gaps=el('div','question-list');for(const [i,gap]of r.gaps.entries()){const node=el('article','question');node.dataset.resultGap=String(i);node.append(metadata([['원 gap JSON',format(gap)]]));gaps.append(node);}content.append(gaps,metadata([['원 failure',format(r.failure)]]));
    const verification=el('details');verification.append(el('summary','','원 D3 검증 범위'),metadata(Object.entries(r.verification).map(([key,value])=>[key,format(value)])));content.append(verification);
  }
  area.append(content);return area;
}
function publishResultView(next){
  const record=state.records.find(item=>item.intake_id===state.selected),target=$('#conducted-result-view');if(!record||!target)return false;
  const prepared=buildConductedResult(record,state,next);target.replaceWith(prepared);Object.assign(resultView,next);refreshGapQueue();return true;
}
function staleResultView(message){
  resultView.stale=true;const node=$('#conducted-result-view');if(node)node.dataset.current='false';const status=$('#conducted-result-status');if(status)status.textContent=message;refreshGapQueue();
}
function retireResultView(){
  resultView.gate.invalidate();resultView.controller?.abort();resultView.controller=null;resultView.pending=false;resultView.parentPending=true;
  if(resultView.value)staleResultView('이전 관측 · 현재 관계 미확인');else resultView.stale=true;
  const node=$('#conducted-result-view');if(node)node.dataset.pending='true';
}
async function refreshResultView(){
  const context=conductedContext();if(!context||resultView.pending||resultView.parentPending||referenceDestroyed||referenceSuspended)return;
  const ticket=resultView.gate.begin(context);resultView.controller?.abort();const controller=new AbortController();resultView.controller=controller;const timer=setTimeout(()=>controller.abort(),10000);
  const current=()=>resultView.gate.isCurrent(ticket,conductedContext()||{})&&!referenceDestroyed&&!referenceSuspended;
  try{
    if(!publishResultView({...resultView,context,pending:true,errorCode:null,stale:Boolean(resultView.value),status:'전도 결과 제공 기록 조회 중'}))return;
    const response=await fetch(`/api/intakes/${encodeURIComponent(context.intake_id)}/conducted-result`,{signal:controller.signal,cache:'no-store'});
    if(!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers.get('content-type')||''))throw Error();
    const length=response.headers.get('content-length');if(length!==null&&(!/^\d+$/.test(length)||Number(length)>1048576))throw Error();
    const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let raw='',size=0;
    try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>1048576){await reader.cancel();throw Error();}raw+=decoder.decode(part.value,{stream:true});}raw+=decoder.decode();}finally{reader.releaseLock();}
    if(!current())return;
    if(!response.ok){const code=JSON.parse(raw)?.error?.code;if(typeof code!=='string'||!/^(?:intake_conducted_(?:result|preview)_[a-z_]+|store_missing|store_unavailable|intake_not_found)$/.test(code))throw Error();throw Error(code);}
    const value=parseConductedResultView(raw,context);if(!current())return;
    publishResultView({...resultView,context,value,pending:false,errorCode:null,stale:false,status:value.relation.status==='matched'?'제공 snapshot 조회 · 현재 계획 binding 대조 일치':'제공 snapshot 조회 · 현재 계획 binding 차단'});
  }catch(error){controller.abort();if(current()){
    const label=({intake_conducted_result_missing:'제공 snapshot 미제공',intake_conducted_result_invalid:'형상·한도·결합 부적합',intake_conducted_result_unavailable:'지정 접수의 제공 결과 미지원',intake_conducted_preview_source_invalid:'현재 보존 자료 무결성 미확인'})[error.message]||'응답·전송·형상·화면 확인 실패';
    resultView.pending=false;resultView.errorCode=queueErrorCode(error);resultView.status=resultView.value?'조회 실패 · 이전 관측 · 현재 관계 미확인':`전도 결과 조회 불가 · ${label}`;staleResultView(resultView.status);
  }}finally{clearTimeout(timer);if(current()){resultView.pending=false;resultView.controller=null;const node=$('#conducted-result-view');if(node)node.dataset.pending=String(resultView.parentPending);refreshGapQueue();}}
}
function syncResultView(){
  const context=conductedContext();if(context&&sameFixtureSource(context,resultView.context)&&context.generation===resultView.context.generation)return;
  resultView.gate.invalidate();resultView.controller?.abort();const retain=sameFixtureSource(context,resultView.context);
  Object.assign(resultView,{context,value:retain?resultView.value:null,controller:null,pending:false,stale:true,errorCode:null,status:'전도 결과 제공 기록 조회 대기'});
  if(context)void refreshResultView();else refreshGapQueue();
}

function buildConductedArtifactStorage(record,snapshot=state,current=storageView){
  const freshParent=(snapshot.snapshotGeneration??0)!==(state.snapshotGeneration??0);
  const view=describeConductedArtifactStorage(record,{generation:snapshot.snapshotGeneration||0,intakeStale:snapshot.view!=='intakes'||(!freshParent&&(gapQueueState.intakeStale||gapQueueState.parentPending)),plan:conducted,storage:current});
  const area=el('section','section-rule');area.id='conducted-artifact-storage';area.style.minWidth='0';area.style.overflowWrap='anywhere';
  area.dataset.sourceKind='artifact_storage_readback';area.dataset.current=String(view.current);area.dataset.scope=view.scope;area.dataset.pending=String(current.pending||current.parentPending);area.dataset.resultStatus=view.original_status||'unknown';
  area.append(el('h4','','별도 산출물 저장 읽기'));
  const status=el('p','inline-note',view.current?'고정 3파일 bytes·hash·full binding 일치 관측':view.foreign?'다른 접수의 산출물 제외':view.scope==='unconfirmed'?'이전 관측 · 현재 관계 미확인':current.status);
  status.id='conducted-artifact-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const refresh=el('button','button','산출물 저장 읽기 새로고침');refresh.id='conducted-artifact-refresh';refresh.type='button';refresh.setAttribute('aria-disabled',String(current.pending||current.parentPending));
  refresh.addEventListener('click',()=>{if(refresh.getAttribute('aria-disabled')!=='true')void refreshArtifactStorage();});
  area.append(status,refresh,el('p','inline-note','지정한 manifest.json · result.json · draft.md의 읽기 관측입니다. 기존 제공 snapshot·fixture와 별도 출처이며 작성 결과·게시 순서·실제 AI·영구 현재 승인·규범 판정은 미확인입니다.'));
  const content=el('div');content.id='conducted-artifact-content';content.dataset.artifactOriginal='';
  const original=(title,value,name)=>{const details=el('details'),pre=el('pre','mono',typeof value==='string'?value:conductedPreviewValue(value));details.append(el('summary','',title));pre.style.whiteSpace='pre-wrap';pre.style.overflowWrap='anywhere';pre.style.maxWidth='100%';pre.dataset.artifactRaw=name;details.append(pre);content.append(details);};
  if(view.artifact){
    const a=view.artifact,s=a.storage,m=a.manifest;
    content.append(badge(view.current?'저장 읽기 일치 관측':`이전·차단 관측 · ${view.status}`,view.current?'info':'warning'),metadata([
      ['별도 산출물 / 원 상태',`${a.selection.artifact_name} / ${a.result.status}`],['별도 run / runtime',`${a.selection.run_id} / ${a.selection.runtime_instance_id}`],
      ['manifest 원 파일 SHA-256 · LF 포함',s.manifest_sha256],['result canonical SHA-256 · LF 제외',s.result_sha256],['result 원 파일 SHA-256 · LF 포함',m.files[0].sha256],['draft 원 UTF-8 SHA-256',s.draft_sha256],
      ['읽은 파일 수 / 결합 범위',`${s.verified_file_count} / ${s.binding_scope}`],['원 측정 / 보정',`${conductedPreviewValue(a.result.raw_measurement)} / ${conductedPreviewValue(a.result.calculation.corrected)}`],
      ['원 측정 유효성 / 규범',`${a.result.status} / ${a.result.calculation.conformity.status}`],['실행 / 재실행 권한',`${a.verification.execution_authority} / ${a.verification.rerun_authority}`],
    ]));
    original('원 manifest JSON · 관측 hash/bytes',m,'manifest');original('원 DRAFT UTF-8 텍스트',a.draft,'draft');original('별도 원 결과 JSON · invalid/null 보존',a.result,'result');
    original('읽기 검증 범위 · 작성 결과·순서 미확인',a.verification,'verification');
  }
  if(view.current_facts)original('관측 당시 원 facts-plan · 공백·질문·null',view.current_facts.facts_plan,'facts-plan');
  if(view.relation)original('원 현재 binding 대조 · 읽기 후 재확인',view.relation,'relation');
  if(view.code||view.reasons.length)content.append(el('p','inline-note',`원 조회 코드 ${conductedPreviewValue(view.code)} · 연결 차단 ${conductedPreviewValue(view.reasons)}`));
  area.append(content);return area;
}
function refreshArtifactStorageCard(){
  const record=state.records.find(x=>x.intake_id===state.selected),target=$('#conducted-artifact-storage');if(!record||!target)return;
  try{target.replaceWith(buildConductedArtifactStorage(record));}catch{target.dataset.current='false';target.dataset.scope='unconfirmed';const status=$('#conducted-artifact-status');if(status)status.textContent='화면 확인 실패 · 이전 관측 · 현재 관계 미확인';}
}
function publishArtifactStorage(next){
  const record=state.records.find(x=>x.intake_id===state.selected),target=$('#conducted-artifact-storage');if(!record||!target)return false;
  const prepared=buildConductedArtifactStorage(record,state,next);target.replaceWith(prepared);Object.assign(storageView,next);refreshGapQueue();return true;
}
function retireArtifactStorage(){
  storageView.gate.invalidate();storageView.controller?.abort();Object.assign(storageView,{controller:null,pending:false,parentPending:true,stale:true});refreshArtifactStorageCard();
}
async function refreshArtifactStorage(){
  const context=conductedContext();if(!context||storageView.pending||storageView.parentPending||referenceDestroyed||referenceSuspended)return;
  const ticket=storageView.gate.begin(context);storageView.controller?.abort();const controller=new AbortController();storageView.controller=controller;const timer=setTimeout(()=>controller.abort(),10000);
  const current=()=>storageView.gate.isCurrent(ticket,conductedContext()||{})&&!referenceDestroyed&&!referenceSuspended;
  try{
    if(!publishArtifactStorage({...storageView,context,pending:true,errorCode:null,stale:Boolean(storageView.value),status:'산출물 저장 읽기 조회 중'}))return;
    const response=await fetch(`/api/intakes/${encodeURIComponent(context.intake_id)}/conducted-artifact-readback`,{signal:controller.signal,cache:'no-store'});
    if(!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers.get('content-type')||''))throw Error('intake_conducted_artifact_readback_invalid');
    const length=response.headers.get('content-length');if(length!==null&&(!/^\d+$/.test(length)||Number(length)>CONDUCTED_ARTIFACT_HTTP_BYTES))throw Error('intake_conducted_artifact_readback_input_limit');
    const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true});let raw='',size=0,primary=null;
    try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>CONDUCTED_ARTIFACT_HTTP_BYTES)throw Error('intake_conducted_artifact_readback_input_limit');raw+=decoder.decode(part.value,{stream:true});}raw+=decoder.decode();}
    catch(error){primary=error;try{await reader.cancel();}catch{}throw error;}
    finally{try{reader.releaseLock();}catch(error){if(!primary)throw error;}}
    if(!current())return;
    if(!response.ok){const code=JSON.parse(raw)?.error?.code;if(typeof code!=='string'||!/^(?:intake_conducted_(?:artifact_readback|preview)_[a-z_]+|conducted_result_artifact_read_[a-z_]+|store_missing|store_unavailable|intake_not_found)$/.test(code))throw Error('intake_conducted_artifact_readback_invalid');throw Error(code);}
    const value=parseConductedArtifactReadback(raw,context);if(!current())return;
    publishArtifactStorage({...storageView,context,value,pending:false,errorCode:null,stale:false,status:value.status==='matched'?'산출물 원 읽기 대조 관측':`산출물 원 관계 ${value.status} · 현재 사용 차단`});
  }catch(error){controller.abort();if(current()){
    storageView.pending=false;storageView.errorCode=queueErrorCode(error);storageView.stale=true;storageView.status=storageView.value?'조회 실패 · 이전 관측 · 현재 관계 미확인':'산출물 저장 읽기 미확인';refreshGapQueue();
  }}finally{clearTimeout(timer);if(current()){storageView.pending=false;storageView.controller=null;refreshGapQueue();}}
}
function syncArtifactStorage(){
  const context=conductedContext();if(context&&sameFixtureSource(context,storageView.context)&&context.generation===storageView.context.generation)return;
  storageView.gate.invalidate();storageView.controller?.abort();const original=storageView.value?.current?.context,retain=!context||sameFixtureSource(context,original);
  Object.assign(storageView,{context,value:retain?storageView.value:null,controller:null,pending:false,stale:true,errorCode:null,status:'산출물 저장 읽기 미관측'});
  if(context)void refreshArtifactStorage();else refreshGapQueue();
}


function queueErrorCode(error){return typeof error?.message==='string'&&/^[a-z_]{1,128}$/.test(error.message)?error.message:'transport_or_shape_error';}
function buildGapQueue(record,snapshot=state){
  const freshParent=(snapshot.snapshotGeneration??0)!==(state.snapshotGeneration??0);
  const model=describeIntakeGapQueue(record,{generation:snapshot.snapshotGeneration||0,intakeStale:freshParent?false:gapQueueState.intakeStale||gapQueueState.parentPending,intakeCode:freshParent?null:gapQueueState.intakeCode,plan:conducted,result:resultView});
  const area=el('section','section-rule');area.id='intake-gap-queue';area.dataset.intakeId=record.intake_id;area.dataset.revision=String(record.revision);
  area.dataset.pending=String(gapQueueState.parentPending||conducted.pending||resultView.pending);area.dataset.current=String(model.groups.every(group=>group.state==='current'));
  area.append(el('h4','','예외·다음 조건 큐'));
  const status=el('p','inline-note','원 출처·순서별 읽기 관측 · 표시 항목 없음은 시험 준비/실행 완료가 아닙니다.');status.id='gap-queue-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');area.append(status);
  area.append(el('p','inline-note','제품 사실 질문은 원자료의 실제 부재·필수 재입력 판정이 아닙니다. 해석/근거 연결 검토와 시스템·시험조건, 미지원·미실행을 구분하며 답변·승인·실행은 연결하지 않습니다.'));
  const labels={current:'현재 조회 scope',blocked:'차단 · 현재 질문 아님',unavailable:'관측 불가',not_run:'미실행·미관측'};
  const categories={evidence_review:'해석·근거 연결 검토',facts_required:'제품 사실 확인',conditions_required:'시스템·시험조건 준비',system_error:'시스템·실행 오류',unsupported:'미지원',not_run:'미실행·미완료',uninterpreted:'미해석 원형',blocked:'차단 · 현재 질문 아님',observed:'출처 관측'};
  for(const group of model.groups){
    const section=el('section','question');section.dataset.gapQueueGroup=group.source;section.dataset.state=group.state;
    section.append(el('h5','',group.label),badge(labels[group.state]||group.state,group.state==='blocked'?'warning':'neutral'),el('p','inline-note',`${group.source_kind} · ${categories[group.category]||group.category}`));
    if(group.code||group.reasons.length)section.append(el('p','inline-note',`원 조회 코드: ${conductedPreviewValue(group.code)} · 연결 차단: ${conductedPreviewValue(group.reasons)}`));
    const context=el('details');context.append(el('summary','','원 관측 접수·버전·조건 지문'),metadata([['관측 접수 / 버전 / 제공 버전',`${conductedPreviewValue(group.observed_intake_id)} / ${conductedPreviewValue(group.observed_revision)} / ${conductedPreviewValue(group.provided_revision)}`],['원 조건 SHA',conductedPreviewValue(group.condition_sha256)]]));section.append(context);
    if(group.source==='result_gaps')section.append(el('p','inline-note','제공 snapshot의 원 공백 · 실제 AI 여부 unknown · 생성 origin/실물 진위 미확인'));
    if(!group.items.length)section.append(el('p','inline-note',group.state==='current'?'이 원 출처에 표시된 질문/공백 없음 · 전체 완료 의미 아님':'현재 연결된 원 항목을 확인하지 못했습니다.'));
    for(const row of group.items){
      const item=el('article','file');item.dataset.gapQueueItem=group.source+':'+String(row.index);item.dataset.state=row.state;item.dataset.category=row.category;
      item.append(el('h6','',`${group.label} · 원 순서 ${row.index===null?'미해석 목록':row.index+1}`));const category=badge(row.label,row.category==='system_error'?'danger':row.state==='blocked'?'warning':'neutral');category.dataset.gapQueueCategory='';item.append(category);
      if(row.classification==='evidence_review'){const hint=el('p','inline-note',`해석·근거 연결 검토 · ${row.note}`);hint.dataset.gapQueueReview='';item.append(hint);}
      if(row.raw&&typeof row.raw==='object'&&!Array.isArray(row.raw)&&typeof row.raw.message==='string')item.append(el('p','',row.raw.message));
      const raw=metadata([['원 질문/공백 JSON · refs/null 포함',conductedPreviewValue(row.raw)]]);raw.dataset.gapQueueOriginal='';const original=el('details');original.append(el('summary','','원 JSON · refs/null 보존'),raw);item.append(original);section.append(item);
    }
    area.append(section);
  }
  return area;
}
function staleGapQueue(message){
  const area=$('#intake-gap-queue');if(!area)return;area.dataset.current='false';
  const status=$('#gap-queue-status');if(status)status.textContent=message;
  for(const row of area.querySelectorAll('[data-gap-queue-item]')){row.dataset.state='blocked';row.dataset.category='blocked';const label=row.querySelector('[data-gap-queue-category]');if(label)label.textContent='차단 · 이전 관측 · 현재 질문 아님';}
}
function refreshGapQueue(){
  refreshWorkflowSummary();
  refreshArtifactStorageCard();
  const target=$('#intake-gap-queue'),record=state.records.find(item=>item.intake_id===state.selected);if(!target||!record)return;
  if(state.view!=='intakes'){staleGapQueue('접수 보기 숨김 · 현재 질문 아님');return;}
  try{const prepared=buildGapQueue(record,state);target.replaceWith(prepared);}catch{staleGapQueue('큐 표시 확인 실패 · 이전 관측 · 현재 질문 아님');}
}
function retireGapQueue(){gapQueueState.intakeStale=true;gapQueueState.parentPending=true;gapQueueState.intakeCode=null;refreshGapQueue();}

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
    const freshGapSnapshot=(prepared.view.snapshotGeneration??0)!==(state.snapshotGeneration??0);
    Object.assign(state, prepared.view);
    if(freshGapSnapshot){gapQueueState.intakeStale=false;gapQueueState.parentPending=false;gapQueueState.intakeCode=null;}
    if(docx.ticket!==prepared.docxNext.ticket)docx.controller?.abort();
    Object.assign(docx,prepared.docxNext);
    referenceContext = prepared.referenceContext;
    referenceActions.setContext(referenceContext);
    if (referenceDestroyed) return;
    referenceTransport.setContext(prepared.referenceContext);
    referencePanel.setContext(prepared.referenceContext);
    syncFixtureContext();
    conducted.parentPending=false;
    syncConductedContext();
    resultView.parentPending=false;
    syncResultView();
    storageView.parentPending=false;
    syncArtifactStorage();
    refreshGapQueue();
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
  syncConductedContext();
  syncResultView();
  syncArtifactStorage();
  refreshGapQueue();
}

async function refresh() {
  if (!referenceCanChange()) return;
  retireGapQueue();
  retireConductedObservation();
  retireResultView();
  retireArtifactStorage();
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
    gapQueueState.intakeCode=queueErrorCode(error);
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
      conducted.parentPending=false;
      $('#conducted-plan-refresh')?.setAttribute('aria-disabled',String(conducted.pending));
      resultView.parentPending=false;
      const resultNode=$('#conducted-result-view');if(resultNode)resultNode.dataset.pending=String(resultView.pending);
      storageView.parentPending=false;
      gapQueueState.parentPending=false;refreshGapQueue();
    }
  }
}

addEventListener('pagehide', event => {
  retireGapQueue();
  retireConductedObservation();
  retireResultView();
  retireArtifactStorage();
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
