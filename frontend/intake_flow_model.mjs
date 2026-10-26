import {validateHarnessResponse, describeHarnessResult} from './virtual_fleet/harness_model.mjs';
import {describeState, factSources, FIELDS, FACT_LABELS} from './model.mjs';

const STATES = {
  queued: ['가상 실행 대기', 'neutral'], running: ['가상 실행 중', 'info'],
  completed: ['실행 기록 저장', 'info'], failed: ['가상 작업 실패', 'danger'],
  uncertain: ['실행·게시 여부 확인 필요', 'warning'], superseded: ['이전 준비 상태로 종료', 'neutral'],
};

export function validateFixtureRuns(payload, context) {
  const fail = path => {throw Object.assign(new Error('invalid_fixture_runs'), {path});};
  const object = (value, fields, path) => {
    if (value === null || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) fail(path);
    const keys = Object.keys(value), expected = fields.split(' ');
    if (keys.length !== expected.length || keys.some(key => !expected.includes(key))) fail(path);
  };
  const text = (value, path, maximum = 128) => {
    if (typeof value !== 'string' || !value.trim() || value.length > maximum || !value.isWellFormed()) fail(path);
  };
  object(payload, 'schema_version intake_id current_revision storage_available records more_available', 'response');
  if (payload.schema_version !== 1) fail('schema_version');
  text(payload.intake_id, 'intake_id', 150);
  if (!Number.isSafeInteger(payload.current_revision) || payload.current_revision < 1) fail('current_revision');
  if (payload.intake_id !== context.intake_id || payload.current_revision !== context.revision) fail('context');
  if (typeof payload.storage_available !== 'boolean' || typeof payload.more_available !== 'boolean') fail('availability');
  if (!Array.isArray(payload.records) || payload.records.length > 20) fail('records');
  if (!payload.storage_available && (payload.records.length || payload.more_available)) fail('storage_available');
  if (payload.more_available && payload.records.length !== 20) fail('more_available');
  const ids = new Set();
  for (const value of payload.records) {
    object(value, 'request_id intake_id revision readiness_fingerprint recipe_id run_id runtime_instance_id state source_current source_synthetic synthetic hardware_verified ai_model_called resumable case_id plan_id error_code report', 'record');
    text(value.request_id, 'request_id', 150); text(value.recipe_id, 'recipe_id');
    if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,149}$/.test(value.request_id)) fail('request_id');
    if (ids.has(value.request_id)) fail('duplicate_request_id');
    ids.add(value.request_id);
    if (value.intake_id !== payload.intake_id || !Number.isSafeInteger(value.revision) || value.revision < 1 || value.revision > payload.current_revision) fail('record.context');
    if (typeof value.readiness_fingerprint !== 'string' || !/^[a-f0-9]{64}$/.test(value.readiness_fingerprint)) fail('readiness_fingerprint');
    if (typeof value.state !== 'string' || !Object.hasOwn(STATES, value.state)) fail('state');
    if (typeof value.source_current !== 'boolean' || typeof value.source_synthetic !== 'boolean' || (value.source_current && value.revision !== payload.current_revision)) fail('source');
    if (value.synthetic !== true || value.hardware_verified !== false || value.ai_model_called !== false || value.resumable !== false || value.case_id !== null || value.plan_id !== null) fail('provenance');
    if ((value.run_id === null) !== (value.runtime_instance_id === null)) fail('identity');
    if (value.run_id !== null) {text(value.run_id, 'run_id'); text(value.runtime_instance_id, 'runtime_instance_id');}
    if (['running', 'completed', 'uncertain'].includes(value.state) && value.run_id === null) fail('missing_identity');
    if (value.error_code !== null && (typeof value.error_code !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value.error_code))) fail('error_code');
    const report = validateHarnessResponse({schema_version:1, report:value.report}).report;
    if (report && (report.run_id !== value.run_id || report.runtime_instance_id !== value.runtime_instance_id || ['queued', 'running'].includes(value.state))) fail('report.identity');
    if (value.state === 'completed' && report === null) fail('missing_report');
  }
  return structuredClone(payload);
}

export function describeFixtureRecord(record, currentRevision) {
  const [label, tone] = STATES[record.state];
  return {state:{label, tone}, context: record.source_current ? '현재 자료·준비 상태의 기록'
    : record.revision === currentRevision ? '같은 자료 버전 · 준비 상태 변경 기록'
      : `이전 자료 버전 v${record.revision} · 현재 v${currentRevision}`,
  result: record.report ? describeHarnessResult(record.report) : null};
}

// A display projection of the existing snapshot and exact fixture-runs API.
// It does not select a method, infer readiness, execute work or assess a task.
export function describeIntakeWorkflow(intake, {payload=null, request_id='', stale=false, pending=false, now=0, provided=null}={}) {
  const records=payload===null?[]:validateFixtureRuns(payload,{intake_id:intake.intake_id,revision:intake.revision}).records;
  const selected=records.find(record=>record.request_id===request_id) || null;
  const description=selected?describeFixtureRecord(selected,intake.revision):null;
  const report=selected?.report, result=description?.result;
  const scope=selected?(stale||pending||provided?.intakeStale||provided?.parentPending?'unconfirmed':selected.source_current?'current':'historical'):'none';
  const relation=scope==='unconfirmed'?'이전 조회 당시 문맥 · 현재 관계 미확인':description?.context || '선택한 가상 기록 없음';
  const revisions=(intake.history||[]).filter(item=>item.revision===intake.revision);
  const context={intake_id:intake.intake_id,revision:intake.revision,
    revision_fingerprint:revisions.length===1?revisions[0].fingerprint??null:null,
    request_id:selected?.request_id??null,record_revision:selected?.revision??null,
    readiness_fingerprint:selected?.readiness_fingerprint??null,fixture_scope:scope,relation};
  const facts=intake.analysis?.facts || {}, questions=intake.analysis?.questions || [];
  const identity=['product_type','purpose','market'];
  const intakeState=describeState(intake,now);
  const entry=(id,title,label,tone,lines,refs=[])=>({id,title,label,tone,lines,refs});
  const unconfirmed=['unconfirmed','historical'].includes(scope);
  const virtualLabel=description?.state.label || (payload===null?'가상 기록 미확인':!payload.storage_available?'가상 기록 저장 기능 미지원':'선택한 가상 기록 없음');
  const view={context,steps:[
    entry('intake','제품·목적·시장과 현재 자료',intakeState.label,intakeState.tone,
      [...identity.map(field=>`${FIELDS[field]}: ${facts[field]?.value??'자료 미확인'} · ${FACT_LABELS[facts[field]?.status]||'상태 미확인'}`),
        `현재 자료 버전 v${intake.revision} · 파일 ${(intake.files||[]).length}개`,
        intake.synthetic?'합성 접수 자료':'제공 접수 자료 · 물리 시료 확인 미실행']),
    entry('gaps','누락·충돌과 해석 범위',!intake.analysis?'누락·충돌 미확인':questions.length?`열린 질문 ${questions.length}개`:'저장된 열린 질문 없음',
      !intake.analysis||questions.length?'warning':'neutral',!intake.analysis?['분석 결과가 없어 아직 확인하지 못했습니다.']:
        [...questions.map(question=>`${question.key}: ${question.message}`),'저장된 분석의 질문 상태이며 시험 준비 완료를 뜻하지 않습니다.']),
    entry('plan','시험계획·방법','시험계획 미연결','neutral',
      ['case_id=null · plan_id=null','시험방법 실행 절차 미제공 · 규정·방법 후보의 문자 대조와 별개입니다.']),
    entry('virtual','가상 준비·실행',virtualLabel,unconfirmed?'warning':description?.state.tone||'neutral',
      [relation,...(selected?[`선택 요청 ${selected.request_id} · 기록 v${selected.revision}`,`선택 recipe ${selected.recipe_id}`,
        `run ${selected.run_id??'예약 전'} · instance ${selected.runtime_instance_id??'예약 전'}`,
        `오류 코드: ${selected.error_code??'기록된 오류 없음'}`]:[]),
        ...(pending?['가상 기록 조회 중 · 현재 관계 확인 대기']:[]),'기술 작업 상태입니다. 시험계획 연결·실장비 준비 완료를 뜻하지 않습니다.']),
    entry('measurement','측정·계산·규격 판정',report?`가상 측정 근거 ${report.evidence.measurement_refs.length}개`:'게시된 측정 근거 미확인',unconfirmed?'warning':'neutral',
      [relation,'원수치/단위·기준면 미제공','보정·계산 결과 미제공','규격 판정 미실행'],report?.evidence.measurement_refs||[]),
    entry('assessment','기록 저장·독립평가',result?.assessment.label||'저장·독립평가 미확인',unconfirmed?'warning':result?.assessment.tone||'neutral',
      [`기술 저장 상태: ${virtualLabel}`,result?`하네스 종료: ${result.termination.label} · ${result.policyClaim}`:'게시된 공개 실행 결과 없음',
        result?`독립 가상 효과 평가: ${result.assessment.label}`:'독립 가상 효과 평가 미확인',
        '작업 결과 미평가(task not_assessed) · 정리 상태 미평가', '이 가상 실행의 실제 AI 호출 없음(ai_model_called=false)'],report?.assessment.evidence_refs||[]),
    entry('physical','실측 대조','실측 대조 미실행','neutral',
      ['실장비 검증 없음(hardware_verified=false)','물리 정확도 미검증 · 실제 시료·계측 원본과 대조하지 않았습니다.']),
  ],citations:identity.flatMap(field=>factSources(intake,field))};
  return provided===null?view:unifyProvidedWorkflow(view,intake,provided);
}

function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
}

export function requireStableFixtureRecords(previous, next) {
  if (!previous || previous.intake_id !== next.intake_id) return;
  for (const old of previous.records) {
    const record = next.records.find(item => item.request_id === old.request_id);
    if (!record) continue; // The recent-20 window can advance.
    const immutable = ['intake_id', 'revision', 'readiness_fingerprint', 'recipe_id', 'source_synthetic'];
    if (old.run_id !== null) immutable.push('run_id', 'runtime_instance_id');
    if (immutable.some(key => old[key] !== record[key]) || (old.report && (canonical(old.report) !== canonical(record.report) || old.state !== record.state))) throw new Error('fixture_record_changed');
  }
}

export function createFixtureReadGate() {
  let sequence = 0;
  const identity = value => JSON.stringify([value.intake_id, value.revision, value.generation, value.request_id]);
  return {
    begin(context) {return {sequence:++sequence, identity:identity(context)};},
    isCurrent(ticket, context) {return ticket.sequence === sequence && ticket.identity === identity(context);},
    invalidate() {sequence++;},
  };
}

const PLAN_FIELDS=['frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','crest_factor_db'];
const PLAN_FACTS='product_type customer manufacturer model market purpose features antenna_gain power_target firmware'.split(' ');
const PLAN_GAPS='native_input_invalid analysis_invalid context_invalid expected_revision_changed_or_invalid expected_context_changed_or_invalid analysis_evidence_invalid conflicting_intake_fact missing_intake_field follow_up_missing_field product_identity unread_documents uncertain_intake_fact intent_value_not_in_request_quote invalid_source_settings unknown_source_field missing_setting unsupported_modulation invalid_setting invalid_rf_domain invalid_method unknown_method_field unsupported_method_field missing_method_field invalid_basis unknown_basis_field missing_or_invalid_basis unsupported_or_invalid_basis basis_value_mismatch basis_quote_value_mismatch basis_evidence_invalid'.split(' ');
const previewNeed=value=>{if(!value)throw Error('intake_conducted_preview_invalid_response');};
function previewJSON(raw,cap=262144,countKeys=false,{maxDepth=40,maxNodes=100000,ranges=null}={}){
  previewNeed(typeof raw==='string'&&new TextEncoder().encode(raw).length<=cap);
  let i=0,nodes=0;const space=()=>{while(/[\x20\t\r\n]/.test(raw[i]||'!'))i++;};
  const string=()=>{const start=i++;while(i<raw.length){if(raw[i]==='\\'){i+=2;continue;}if(raw[i++]==='"'){const text=JSON.parse(raw.slice(start,i));previewNeed(text.isWellFormed());return text;}}throw Error('intake_conducted_preview_invalid_response');};
  const value=depth=>{
    previewNeed(depth<=maxDepth&&++nodes<=maxNodes);space();const start=i,c=raw[i],finish=out=>{ranges?.set(out,[start,i]);return out;};if(c==='"')return string();
    if(c==='{'){i++;space();const out=Object.create(null);if(raw[i]==='}'){i++;return finish(out);}while(true){space();previewNeed(raw[i]==='"');const key=string();if(countKeys)previewNeed(++nodes<=maxNodes);previewNeed(!Object.hasOwn(out,key));space();previewNeed(raw[i++]===':');out[key]=value(depth+1);space();const end=raw[i++];if(end==='}')return finish(out);previewNeed(end===',');}}
    if(c==='['){i++;space();const out=[];if(raw[i]===']'){i++;return finish(out);}while(true){out.push(value(depth+1));space();const end=raw[i++];if(end===']')return finish(out);previewNeed(end===',');}}
    for(const [token,result]of [['true',true],['false',false],['null',null]])if(raw.startsWith(token,i)){i+=token.length;return result;}
    const number=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(raw.slice(i));previewNeed(number);i+=number[0].length;
    const parsed=Number(number[0]);if(!/[.eE]/.test(number[0])&&!Number.isSafeInteger(parsed))return BigInt(number[0]);
    previewNeed(Number.isFinite(parsed));return parsed;
  };
  const result=value(0);space();previewNeed(i===raw.length);return result;
}
export function conductedPreviewValue(value){
  const encode=v=>v===null?'null':typeof v==='string'?JSON.stringify(v):Array.isArray(v)?'['+v.map(encode).join(',')+']':typeof v==='object'?'{'+Object.entries(v).map(([k,x])=>JSON.stringify(k)+':'+encode(x)).join(',')+'}':Object.is(v,-0)?'-0':String(v);
  return value===undefined?'제공 항목 없음':value===null?'미제공(null)':typeof value==='object'?encode(value):Object.is(value,-0)?'-0':String(value);
}
export function parseConductedPlanPreview(raw,context){return validatePlanPreviewPacket(previewJSON(raw),context);}
function validatePlanPreviewPacket(v,context){
  const need=previewNeed;
  const keys=(x,names)=>{need(x!==null&&typeof x==='object'&&!Array.isArray(x));const actual=Object.keys(x);need(actual.length===names.length&&actual.every(k=>names.includes(k)));};
  const text=x=>typeof x==='string'&&x.trim().length>0;
  const sha=x=>typeof x==='string'&&x.length===64&&/^[a-f0-9]+$/.test(x);
  const integer=x=>typeof x==='number'&&Number.isSafeInteger(x)&&x>0;
  const number=x=>typeof x==='bigint'||typeof x==='number'&&Number.isFinite(x);
  const nullable=(x,check)=>x===null||check(x);
  const list=(x,check,max=100000)=>{need(Array.isArray(x)&&x.length<=max);for(const item of x)need(check(item));};
  const citation=c=>{
    const extra=c.kind==='pdf_page'?['kind','extraction_id','page_number','text_sha256']:c.kind==='text_line'?['kind']:[];
    keys(c,['path','sha256','line_start','line_end','quote','role',...extra]);need(text(c.path)&&sha(c.sha256)&&integer(c.line_start)&&integer(c.line_end)&&c.line_end>=c.line_start&&text(c.quote)&&['request','product','reference'].includes(c.role));
    if(extra.length===4)need(sha(c.extraction_id)&&sha(c.text_sha256)&&integer(c.page_number));return true;
  };
  const citations=(x,min=0)=>{list(x,citation,20);need(x.length>=min);};
  keys(v,['schema_version','kind','intake_id','revision','context_sha256','context_scope','selection_status','plan_input']);
  need(v.schema_version===1&&v.kind==='intake_conducted_plan_preview'&&v.intake_id===context.intake_id&&v.revision===context.revision&&integer(v.revision)&&sha(v.context_sha256)&&v.context_scope==='current_provided_context'&&['matched','not_provided','other_intake','revision_changed'].includes(v.selection_status));
  const p=v.plan_input;keys(p,['schema_version','kind','status','binding','intake','plan','gaps','verification']);
  need(p.schema_version===1&&p.kind==='intake_conducted_twin_plan_input'&&['ready_for_simulation','blocked'].includes(p.status));
  keys(p.binding,['intake_id','revision','analysis_context_id','context_sha256','analysis_sha256','plan_sha256']);
  need((p.binding.intake_id===null||p.binding.intake_id===v.intake_id)&&(p.binding.revision===null||p.binding.revision===v.revision)&&(p.binding.context_sha256===null||p.binding.context_sha256===v.context_sha256)&&nullable(p.binding.analysis_context_id,sha)&&nullable(p.binding.analysis_sha256,sha)&&sha(p.binding.plan_sha256));
  keys(p.intake,['facts','source_facts','missing_fields','follow_up_missing_fields','questions']);
  need(p.intake.facts!==null&&typeof p.intake.facts==='object'&&!Array.isArray(p.intake.facts));
  for(const [field,fact]of Object.entries(p.intake.facts)){need(PLAN_FACTS.includes(field));keys(fact,['value','status']);need(text(fact.value)&&['explicit','inferred'].includes(fact.status));}
  list(p.intake.source_facts,f=>{keys(f,['field','value','status','evidence']);need(PLAN_FACTS.includes(f.field)&&text(f.value)&&['explicit','inferred','uncertain'].includes(f.status));citations(f.evidence,1);return true;},200);
  for(const key of ['missing_fields','follow_up_missing_fields'])list(p.intake[key],x=>PLAN_FACTS.includes(x),10);
  list(p.intake.questions,q=>{
    if(typeof q.key==='string'&&q.key.startsWith('conflict_')){keys(q,['key','field','values','message']);need(PLAN_FACTS.includes(q.field)&&q.key==='conflict_'+q.field);list(q.values,text);}
    else if(typeof q.key==='string'&&q.key.startsWith('missing_')){keys(q,['key','field','message']);need(PLAN_FACTS.includes(q.field)&&q.key==='missing_'+q.field);}
    else if(q.key==='product_identity')keys(q,['key','message']);
    else{keys(q,['key','paths','message']);need(q.key==='unread_documents');list(q.paths,text);}
    need(text(q.message));return true;
  });
  const plan=p.plan;keys(plan,['schema_version','method_id','method_version','metric','reference_plane','source_settings','basis_refs','numeric_limit_dbm','uncertainty_db','assessment']);
  need(plan.schema_version===1&&[null,'conducted_synthetic'].includes(plan.method_id)&&(plan.method_version===null||plan.method_version===1)&&[null,'on','time','peak'].includes(plan.metric)&&[null,'source_output'].includes(plan.reference_plane)&&plan.numeric_limit_dbm===null&&plan.uncertainty_db===null&&plan.assessment==='not_assessed');
  keys(plan.source_settings,PLAN_FIELDS);keys(plan.basis_refs,PLAN_FIELDS);
  const units=[['Hz','kHz','MHz','GHz'],['dBm'],['Hz','kHz','MHz','GHz'],['ratio','%'],['label'],['dB']];
  for(const [index,field]of PLAN_FIELDS.entries()){
    const setting=plan.source_settings[field],basis=plan.basis_refs[field];
    need((setting===null)===(basis===null));if(setting===null)continue;
    need(field==='modulation'?text(setting)&&setting.length<=200:number(setting));
    if(['frequency_hz','bandwidth_hz','duty_cycle'].includes(field))need(setting>0);
    if(field==='duty_cycle')need(setting<=1);if(field==='crest_factor_db')need(setting>=0);
    keys(basis,['kind','value','unit','evidence']);need(['source_cited','developer_declared_synthetic'].includes(basis.kind)&&units[index].includes(basis.unit)&&(field==='modulation'?text(basis.value):number(basis.value)));
    citations(basis.evidence,basis.kind==='source_cited'?1:0);if(basis.kind==='developer_declared_synthetic')need(basis.evidence.length===0);
  }
  list(p.gaps,g=>{keys(g,['code','field','provided','blocking']);need(PLAN_GAPS.includes(g.code)&&text(g.field)&&/^(?:input|context|analysis|(?:binding|intake)\.[\s\S]+|(?:source_settings|method|basis)(?:\.[\s\S]+)?)$/.test(g.field)&&typeof g.blocking==='boolean');return true;});
  keys(p.verification,['evidence','current_version','source_bytes','regulatory','measurement_prediction','execution_authority']);
  need(p.verification.current_version==='caller_snapshot_only'&&p.verification.source_bytes==='not_reopened'&&p.verification.regulatory==='not_assessed'&&p.verification.measurement_prediction==='not_assessed'&&p.verification.execution_authority===false);
  const ready=p.status==='ready_for_simulation';need(ready===!p.gaps.some(g=>g.blocking)&&p.verification.evidence===(ready?'validated_in_memory':'not_validated'));
  if(ready)need(v.selection_status==='matched'&&Object.values(p.binding).every(x=>x!==null));
  return v;
}

const RESULT_INVALID=new Set('acquisition_invalid evidence_context_missing input_limit invalid_evidence journal_header_invalid journal_integrity_invalid journal_invalid journal_limit journal_state_invalid measurement_invalid measurement_path_conflict measurement_stale native_input_invalid observation_clock_regression observation_invalid output_limit plan_basis_invalid plan_binding_invalid plan_binding_mismatch plan_hash_mismatch plan_intake_invalid plan_invalid plan_limit plan_method_invalid plan_verification_invalid receipt_advance_clock receipt_identity_or_clock receipt_invalid report_invalid run_binding_mismatch setup_advance_invalid setup_clock_mismatch setup_duplicate_request setup_hash_mismatch setup_identity_invalid setup_invalid setup_limit setup_receipt_invalid source_metadata_mismatch source_settings_mismatch topology_hash_mismatch topology_invalid'.split(' ')),RESULT_INCOMPLETE=new Set('correction_overflow execution_incomplete journal_incomplete measurement_missing measurement_not_referenced measurement_reference_missing path_ambiguous path_configuration_invalid path_configuration_missing path_selection_missing plan_blocked post_setup_configuration setup_failed setup_missing setup_partial unit_conversion_failed unsupported_path_device'.split(' ')),RESULT_GAP_ONLY=new Set('correction_basis_invalid correction_basis_missing metric_mismatch'.split(' '));
const RESULT_REASONS='provided_revision_changed expected_current_binding_missing expected_intake_mismatch expected_revision_mismatch expected_context_mismatch expected_analysis_context_mismatch expected_analysis_mismatch result_plan_binding_unavailable result_plan_binding_mismatch result_plan_hash_mismatch result_plan_input_hash_mismatch result_report_hash_mismatch result_run_binding_mismatch'.split(' ');
export function parseConductedResultView(raw,context){
  return validateConductedResultPacket(previewJSON(raw,1048576,true),context);
}

export function parseOperatorAttemptView(raw,context){
  const need=x=>{if(!x)throw Error('operator_attempt_invalid');};
  const keys=(x,names)=>{const fields=names.split(' ');need(x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length===fields.length&&fields.every(k=>Object.hasOwn(x,k)));};
  const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x),id=x=>typeof x==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,149}$/.test(x),integer=x=>Number.isSafeInteger(x);
  try{
    const v=previewJSON(raw,16384,true,{maxDepth:9,maxNodes:180});
    keys(v,'schema_version kind status finalization storage termination_reason hold_reason hold_reasons virtual_dut_final_state source_kind declared_mode binding method model steps verification evidence');
    need(v.schema_version===1&&v.kind==='operator_attempt_view'&&v.status==='bounded'&&v.finalization==='held'&&v.storage==='not_created'&&v.termination_reason==='decision_budget'&&v.hold_reason==='execution_incomplete'&&v.virtual_dut_final_state==='transmitting'&&v.source_kind==='provided_actual_cli_record'&&v.declared_mode==='synthetic_only');
    need(Array.isArray(v.hold_reasons)&&v.hold_reasons.length===1);keys(v.hold_reasons[0],'code field detail');
    need(v.hold_reasons[0].code===v.hold_reason&&v.hold_reasons[0].field==='journal/report'&&v.hold_reasons[0].detail===null);
    const b=v.binding;keys(b,'intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256 plan_input_sha256 run_id runtime_instance_id job_id');
    need(b.intake_id===context.intake_id&&b.revision===context.revision&&integer(b.revision)&&b.revision>0&&id(b.intake_id)&&id(b.job_id)&&id(b.run_id)&&id(b.runtime_instance_id));
    for(const key of ['analysis_context_id','context_sha256','analysis_sha256','plan_sha256','plan_input_sha256'])need(sha(b[key]));
    keys(v.method,'method_id method_version metric reference_plane');need(v.method.method_id==='conducted_synthetic'&&v.method.method_version===1&&['on','time','peak'].includes(v.method.metric)&&v.method.reference_plane==='source_output');
    const m=v.model;keys(m,'requested_model remote_resolved_model process_count cli_tool_items cumulative_processes remaining_processes token_usage cost');
    need(typeof m.requested_model==='string'&&/^[a-z0-9][a-z0-9.-]{0,63}$/.test(m.requested_model)&&m.remote_resolved_model===null&&integer(m.process_count)&&m.process_count>0&&m.process_count<=8&&m.cli_tool_items===0&&integer(m.cumulative_processes)&&m.cumulative_processes>=m.process_count&&m.remaining_processes===0&&m.token_usage===null&&m.cost===null);
    need(Array.isArray(v.steps)&&v.steps.length===m.process_count);
    for(const [index,s] of v.steps.entries()){
      keys(s,'index action before_tick after_tick receipt_status effect cli_tool_items');
      need(s.index===index+1&&['advance','dut.start','sensor.acquire','sensor.read'].includes(s.action)&&integer(s.before_tick)&&integer(s.after_tick)&&s.before_tick>=0&&s.after_tick>=s.before_tick&&s.after_tick<=100000&&['pending','ok'].includes(s.receipt_status)&&['changed','unchanged'].includes(s.effect)&&s.cli_tool_items===0);
    }
    keys(v.verification,'origin_authenticated remote_identity_verified hardware_verified execution_authority result_created draft_created');
    need(Object.values(v.verification).every(value=>value===false));
    keys(v.evidence,'evaluation execution finalizer finished handoff');need(Object.values(v.evidence).every(sha));
    return v;
  }catch{throw Error('operator_attempt_invalid');}
}
function validateConductedResultPacket(v,context){
  const need=x=>{if(!x)throw Error('intake_conducted_result_invalid');};
  const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
  const keys=(x,fields)=>need(object(x)&&Object.keys(x).length===fields.split(' ').length&&Object.keys(x).every(k=>fields.split(' ').includes(k)));
  const text=x=>typeof x==='string'&&x.trim().length>0,sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
  const number=x=>typeof x==='bigint'||typeof x==='number'&&Number.isFinite(x),integer=x=>typeof x==='bigint'?x>=0n:Number.isSafeInteger(x)&&x>=0;
  const binding=x=>{keys(x,'intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256');need(text(x.intake_id)&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,149}$/.test(x.intake_id)&&Number.isSafeInteger(x.revision)&&x.revision>0);for(const k of ['analysis_context_id','context_sha256','analysis_sha256','plan_sha256'])need(sha(x[k]));};
  keys(v,'schema_version kind intake_id revision context_sha256 source_kind expected_current_binding relation result');
  need(v.schema_version===1&&v.kind==='intake_conducted_result_view'&&v.intake_id===context.intake_id&&v.revision===context.revision&&Number.isSafeInteger(v.revision)&&v.revision>0&&sha(v.context_sha256)&&v.source_kind==='provided_snapshot');
  keys(v.relation,'status reasons provided_revision');const relation=v.relation;
  need(Array.isArray(relation.reasons)&&relation.reasons.every(x=>RESULT_REASONS.includes(x))&&new Set(relation.reasons).size===relation.reasons.length&&Number.isSafeInteger(relation.provided_revision)&&relation.provided_revision>0&&relation.status===(relation.reasons.length?'blocked':'matched'));
  const resultField=/^(?:input|output|plan_input(?:\.(?:binding|gaps|status|verification|intake|plan(?:\.basis_refs)?))?|journal_read(?:\.(?:events|header|integrity))?|setup_snapshot(?:\.[0-9]+)?|topology|run_report|measurement_ref|calculation|observation\.[\s\S]+)$/;
  const expected=v.expected_current_binding;if(expected!==null)binding(expected);
  const reason=(condition,code)=>{if(condition)need(relation.status==='blocked'&&relation.reasons.includes(code));};
  reason(expected===null,'expected_current_binding_missing');reason(relation.provided_revision!==v.revision,'provided_revision_changed');
  if(expected!==null){reason(expected.intake_id!==v.intake_id,'expected_intake_mismatch');reason(expected.revision!==v.revision,'expected_revision_mismatch');reason(expected.context_sha256!==v.context_sha256,'expected_context_mismatch');}
  const r=v.result;keys(r,'schema_version kind status binding raw_measurement setup_provenance calculation gaps failure verification');
  need(r.schema_version===1&&r.kind==='conducted_twin_result'&&['recorded','incomplete','invalid'].includes(r.status));
  need(object(r.binding));const b=r.binding,size=Object.keys(b).length;
  if(size===2)keys(b,'plan_input run_report');
  else if(size===11){keys(b,'plan_input run_report plan_input_sha256 setup_sha256 journal_file_sha256 journal_head_sha256 report_sha256 topology_sha256 run_id runtime_instance_id measurement_ref');for(const k of ['plan_input_sha256','setup_sha256','journal_file_sha256','journal_head_sha256','report_sha256','topology_sha256'])need(sha(b[k]));for(const k of ['run_id','runtime_instance_id','measurement_ref'])need(text(b[k]));}
  else need(size===0);
  const measurement=r.raw_measurement;
  if(measurement!==null){keys(measurement,'packet event_id sequence device_id tick setup_revision quantity reference_plane');need(object(measurement.packet)&&measurement.device_id==='sensor');}
  const setup=r.setup_provenance;keys(setup,'records topology path');need(Array.isArray(setup.path));
  for(const edge of setup.path){need(object(edge)&&edge.kind==='rf'&&object(edge.source)&&object(edge.target));for(const side of ['source','target'])need(text(edge[side].device_id)&&text(edge[side].port));}
  const calc=r.calculation;keys(calc,'raw_power_w raw_reference_plane correction_ledger target_reference_plane corrected conformity');need([null,'source_output'].includes(calc.target_reference_plane));
  if(calc.raw_power_w!==null){keys(calc.raw_power_w,'value unit');need(number(calc.raw_power_w.value)&&calc.raw_power_w.value>0&&calc.raw_power_w.unit==='W');}
  need(Array.isArray(calc.correction_ledger));for(const row of calc.correction_ledger){
    keys(row,'device_id output_port setting loss_db record_index request_id tick setup_revision propagation_db already_applied compensation_db');
    for(const k of ['device_id','output_port','request_id'])need(text(row[k]));for(const k of ['loss_db','propagation_db','compensation_db'])need(number(row[k]));for(const k of ['record_index','tick','setup_revision'])need(integer(row[k]));
    need(['attenuation_db','loss_db','coupling_db','through_loss_db'].includes(row.setting)&&row.already_applied===false);
  }
  if(calc.corrected!==null){keys(calc.corrected,'value unit power_w');need(number(calc.corrected.value)&&calc.corrected.unit==='dBm'&&number(calc.corrected.power_w)&&calc.corrected.power_w>0);}
  keys(calc.conformity,'status verdict numeric_limit_dbm uncertainty_db');need(calc.conformity.status==='not_assessed'&&calc.conformity.verdict===null&&calc.conformity.numeric_limit_dbm===null&&calc.conformity.uncertainty_db===null);
  need(Array.isArray(r.gaps));if(r.status!=='invalid')for(const gap of r.gaps){keys(gap,'code field provided blocking');need([...PLAN_GAPS,...RESULT_INVALID,...RESULT_INCOMPLETE,...RESULT_GAP_ONLY].includes(gap.code)&&text(gap.field)&&typeof gap.blocking==='boolean');need(PLAN_GAPS.includes(gap.code)?/^(?:input|context|analysis|(?:binding|intake)\.[\s\S]+|(?:source_settings|method|basis)(?:\.[\s\S]+)?)$/.test(gap.field):resultField.test(gap.field)||['quantity','quantity.metric'].includes(gap.field));}
  if(r.failure!==null){keys(r.failure,'code field');need(text(r.failure.field)&&resultField.test(r.failure.field)&&(r.status==='invalid'?RESULT_INVALID:r.status==='incomplete'?RESULT_INCOMPLETE:new Set()).has(r.failure.code));}
  else need(r.status!=='invalid');
  if(r.status!=='invalid'&&size>0){
    const plan=b.plan_input;need(object(plan)&&object(plan.binding));const pc={intake_id:typeof plan.binding.intake_id==='string'?plan.binding.intake_id:v.intake_id,revision:Number.isSafeInteger(plan.binding.revision)&&plan.binding.revision>0?plan.binding.revision:v.revision};
    validatePlanPreviewPacket({schema_version:1,kind:'intake_conducted_plan_preview',...pc,context_sha256:sha(plan.binding.context_sha256)?plan.binding.context_sha256:v.context_sha256,context_scope:'current_provided_context',selection_status:'matched',plan_input:plan},pc);
  }
  if(relation.status==='matched'){
    need(expected!==null&&object(b.plan_input)&&object(b.plan_input.binding));binding(b.plan_input.binding);
    need(Object.keys(expected).every(k=>expected[k]===b.plan_input.binding[k]));
  }
  if(r.status==='recorded'){
    need(r.failure===null&&size===11&&measurement!==null&&calc.corrected!==null&&b.plan_input.status==='ready_for_simulation'&&object(b.run_report)&&Object.keys(b.run_report).length===15);
    const packet=measurement.packet;need('status valid value unit frequency_hz power_dbm duty_cycle crest_factor_db acquisition_tick acquisition_setup_revision source_id'.split(' ').every(k=>Object.hasOwn(packet,k)));
    need(packet.status==='ok'&&packet.valid===true&&packet.unit==='dBm'&&packet.source_id==='sensor');for(const k of ['value','frequency_hz','power_dbm','duty_cycle','crest_factor_db'])need(number(packet[k]));for(const k of ['acquisition_tick','acquisition_setup_revision'])need(integer(packet[k]));
    need(packet.value===packet.power_dbm&&text(measurement.event_id)&&integer(measurement.sequence)&&measurement.sequence>0&&integer(measurement.tick)&&integer(measurement.setup_revision));
    keys(measurement.quantity,'metric reference_plane loss_compensation_applied loss_compensation_sign');need(measurement.quantity.metric==='on'&&measurement.quantity.reference_plane==='sensor_input'&&measurement.quantity.loss_compensation_applied===false&&measurement.quantity.loss_compensation_sign===1);
    need(Array.isArray(setup.records)&&setup.records.length<=32&&object(setup.topology)&&Array.isArray(setup.topology.devices)&&Array.isArray(setup.topology.connections));
    for(const node of setup.topology.devices)need(object(node)&&text(node.id)&&text(node.profile_id));for(const edge of setup.topology.connections){need(object(edge)&&text(edge.kind)&&object(edge.source)&&object(edge.target));for(const side of ['source','target'])need(text(edge[side].device_id)&&text(edge[side].port));}
    need(measurement.reference_plane==='sensor_input'&&calc.target_reference_plane==='source_output');for(const record of setup.records){keys(record,'request_id operation device_id action parameters receipt tick setup_revision');need(text(record.request_id)&&['execute','advance'].includes(record.operation));for(const k of ['device_id','action'])need(record[k]===null||text(record[k]));for(const k of ['parameters','receipt'])need(record[k]===null||object(record[k]));for(const k of ['tick','setup_revision'])need(record[k]===null||integer(record[k]));}
  }
  keys(r.verification,'synthetic hardware_verified physical_verified source_bytes method_approval trust_scope execution_authority');need(r.verification.synthetic===true&&r.verification.hardware_verified===false&&r.verification.physical_verified===false&&r.verification.source_bytes==='not_reopened'&&r.verification.method_approval==='not_assessed'&&r.verification.trust_scope==='provided_host_snapshots_and_hash_consistency'&&r.verification.execution_authority===false);
  return v;
}

const ARTIFACT_BINDING='intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256'.split(' ');
export const CONDUCTED_ARTIFACT_HTTP_BYTES=12*1024*1024+1;
export const CONDUCTED_CURRENT_FACTS_HTTP_BYTES=9*1024*1024;
// A first-class current snapshot. Native source/hash checks remain with the
// readonly API; this parser validates its exact attestation without rewriting it.
export function parseConductedCurrentFacts(raw,context){
  const need=x=>{if(!x)throw Error('intake_current_facts_plan_view_invalid');};
  const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
  const keys=(x,names)=>{const fields=names.split(' ');need(object(x)&&Object.keys(x).length===fields.length&&fields.every(k=>Object.hasOwn(x,k)));};
  const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x),positive=x=>Number.isSafeInteger(x)&&x>0,text=x=>typeof x==='string'&&x.trim().length>0;
  try{
    const ranges=new WeakMap(),v=previewJSON(raw,CONDUCTED_CURRENT_FACTS_HTTP_BYTES,true,{maxDepth:48,maxNodes:400000,ranges});
    keys(v,'schema_version kind status current recheck reasons verification');need(v.schema_version===1&&v.kind==='intake_current_facts_plan_view');
    keys(v.current,'context analysis facts_plan');const range=ranges.get(v.current);need(range&&new TextEncoder().encode(raw.slice(...range)).length<=8*1024*1024);
    const c=v.current.context,f=v.current.facts_plan;keys(c,'job_id intake_id revision synthetic documents analysis_context_id analysis_contract instructions');
    need(c.intake_id===context.intake_id&&c.revision===context.revision&&positive(c.revision)&&c.synthetic===true&&text(c.job_id)&&sha(c.analysis_context_id)&&Array.isArray(c.documents)&&object(c.analysis_contract)&&typeof c.instructions==='string'&&object(v.current.analysis));
    keys(f,'schema_version kind status plan_input assembly_gaps questions');need(f.schema_version===1&&f.kind==='intake_facts_to_conducted_plan'&&['ready_for_simulation','blocked'].includes(f.status)&&f.plan_input?.status===f.status&&Array.isArray(f.assembly_gaps)&&Array.isArray(f.questions));
    const b=f.plan_input.binding;keys(b,'intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256');
    need(b.intake_id===c.intake_id&&b.revision===c.revision&&b.analysis_context_id===c.analysis_context_id&&['analysis_context_id','context_sha256','analysis_sha256','plan_sha256'].every(k=>sha(b[k])));
    // Reuse only the existing pure plan validator, never an artifact compound.
    validatePlanPreviewPacket({schema_version:1,kind:'intake_conducted_plan_preview',intake_id:c.intake_id,revision:c.revision,context_sha256:b.context_sha256,context_scope:'current_provided_context',selection_status:'matched',plan_input:f.plan_input},context);
    for(const gap of f.assembly_gaps){keys(gap,'code field provided blocking');need(typeof gap.code==='string'&&typeof gap.field==='string'&&typeof gap.blocking==='boolean');}
    for(const q of f.questions){keys(q,'key field reason message');need(Object.values(q).every(text));}
    const recheck=v.recheck;keys(recheck,'status before after');
    for(const part of [recheck.before,recheck.after]){keys(part,'context_sha256 analysis_sha256');need(sha(part.context_sha256)&&sha(part.analysis_sha256));}
    need(recheck.before.context_sha256===b.context_sha256&&recheck.before.analysis_sha256===b.analysis_sha256);
    const changed=recheck.before.context_sha256!==recheck.after.context_sha256||recheck.before.analysis_sha256!==recheck.after.analysis_sha256;
    need(recheck.status===(changed?'changed':'unchanged')&&v.status===(changed?'stale':'available')&&Array.isArray(v.reasons)&&v.reasons.length===(changed?1:0)&&(!changed||v.reasons[0]==='current_changed'));
    const verification={scope:'two_readonly_current_snapshots',current_completion:'not_assessed',permanent_current_approval:false,method_approval:'not_assessed',regulatory:'not_assessed',physical_verified:false,execution_authority:false,rerun_authority:false,business_writes:false};
    keys(v.verification,Object.keys(verification).join(' '));need(Object.entries(verification).every(([k,value])=>v.verification[k]===value));
    return v;
  }catch{throw Error('intake_current_facts_plan_view_invalid');}
}

// Validate the public reader's attestation. File-byte/hash checks belong to the
// native reader; this parser neither reserializes parents nor grants authority.
export function parseConductedArtifactReadback(raw,context){
  const need=x=>{if(!x)throw Error('intake_conducted_artifact_readback_invalid');};
  const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
  const keys=(x,names)=>{const fields=names.split(' ');need(object(x)&&Object.keys(x).length===fields.length&&fields.every(k=>Object.hasOwn(x,k)));};
  const equal=(a,b)=>ARTIFACT_BINDING.every(k=>a[k]===b[k]);
  const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x),positive=x=>Number.isSafeInteger(x)&&x>0;
  const text=x=>typeof x==='string'&&x.trim().length>0;
  const literals=(x,expected)=>{keys(x,Object.keys(expected).join(' '));need(Object.entries(expected).every(([k,v])=>x[k]===v));};
  const binding=(x,nullable=false)=>{keys(x,ARTIFACT_BINDING.join(' '));need((nullable&&x.intake_id===null||text(x.intake_id))&&(nullable&&x.revision===null||positive(x.revision)));for(const k of ARTIFACT_BINDING.slice(2))need(nullable&&x[k]===null||sha(x[k]));};
  const ranges=new WeakMap(),v=previewJSON(raw,CONDUCTED_ARTIFACT_HTTP_BYTES,true,{maxDepth:48,maxNodes:400000,ranges});
  const bytes=x=>{const range=ranges.get(x);need(range);return new TextEncoder().encode(raw.slice(...range)).length;};
  const bounded=(part,cap)=>{
    need(bytes(part)<=cap);let nodes=0;
    const walk=(item,depth)=>{need(depth<=32&&++nodes<=1000000);if(Array.isArray(item))for(const child of item)walk(child,depth+1);else if(object(item))for(const [key,child]of Object.entries(item)){walk(key,depth+1);walk(child,depth+1);}};
    walk(part,0);
  };
  keys(v,'schema_version kind status current artifact relation verification');
  need(v.schema_version===1&&v.kind==='intake_conducted_artifact_readback'&&['matched','blocked','different_intake','different_plan','stale'].includes(v.status));
  keys(v.current,'context analysis facts_plan');bounded(v.current,8*1024*1024);
  const c=v.current.context,f=v.current.facts_plan,rel=v.relation;
  keys(c,'job_id intake_id revision synthetic documents analysis_context_id analysis_contract instructions');
  need(c.intake_id===context.intake_id&&c.revision===context.revision&&positive(c.revision)&&object(v.current.analysis));
  keys(f,'schema_version kind status plan_input assembly_gaps questions');
  need(f.schema_version===1&&f.kind==='intake_facts_to_conducted_plan'&&['ready_for_simulation','blocked'].includes(f.status)&&f.plan_input?.status===f.status&&Array.isArray(f.assembly_gaps)&&Array.isArray(f.questions));
  keys(rel,'status current_binding artifact_binding fields recheck reasons');need(rel.status===v.status);binding(rel.current_binding,true);
  need(equal(rel.current_binding,f.plan_input.binding));keys(rel.fields,ARTIFACT_BINDING.join(' '));
  keys(rel.recheck,'status context_sha256_before context_sha256_after analysis_sha256_before analysis_sha256_after');
  const recheck=rel.recheck;for(const k of Object.keys(recheck).filter(k=>k!=='status'))need(sha(recheck[k]));
  const contextChanged=recheck.context_sha256_before!==recheck.context_sha256_after,analysisChanged=recheck.analysis_sha256_before!==recheck.analysis_sha256_after;
  need(recheck.status===(contextChanged||analysisChanged?'changed':'unchanged'));
  validatePlanPreviewPacket({schema_version:1,kind:'intake_conducted_plan_preview',intake_id:c.intake_id,revision:c.revision,context_sha256:recheck.context_sha256_before,context_scope:'current_provided_context',selection_status:'matched',plan_input:f.plan_input},context);
  if(f.status==='ready_for_simulation'){
    binding(rel.current_binding);need(rel.current_binding.analysis_context_id===c.analysis_context_id&&rel.current_binding.context_sha256===recheck.context_sha256_before&&rel.current_binding.analysis_sha256===recheck.analysis_sha256_before);
  }
  need(Array.isArray(rel.reasons)&&rel.reasons.every(text)&&new Set(rel.reasons).size===rel.reasons.length);
  const reasons=[],artifact=v.artifact;let status='blocked';
  if(artifact===null){
    need(rel.artifact_binding===null&&ARTIFACT_BINDING.every(k=>rel.fields[k]===null));
    if(rel.reasons.includes('current_pin_missing'))reasons.push('current_pin_missing');
    if(f.status==='blocked')reasons.push('current_plan_blocked');need(reasons.length>0);
  }else{
    need(f.status==='ready_for_simulation');bounded(artifact,2*1024*1024);
    keys(artifact,'schema_version kind selection storage result manifest draft verification');need(artifact.schema_version===1&&artifact.kind==='conducted_result_artifact_read');
    const s=artifact.selection,storage=artifact.storage,m=artifact.manifest,r=artifact.result;
    keys(s,'artifact_name expected_manifest_sha256 expected_result_sha256 run_id runtime_instance_id');
    need(typeof s.artifact_name==='string'&&/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(s.artifact_name)&&sha(s.expected_manifest_sha256)&&sha(s.expected_result_sha256)&&text(s.run_id)&&text(s.runtime_instance_id));
    literals(storage,{status:'manifest_payloads_verified',completion_marker:'manifest.json',manifest_sha256:s.expected_manifest_sha256,result_sha256:s.expected_result_sha256,draft_sha256:storage?.draft_sha256,verified_file_count:3,binding_scope:'full_bound'});need(sha(storage.draft_sha256));
    keys(m,'schema_version kind artifact_name run_id runtime_instance_id result_sha256 result_status files verification execution_authority');need(bytes(m)+1<=8192);
    need(m.schema_version===1&&m.kind==='conducted_result_artifact_manifest'&&m.artifact_name===s.artifact_name&&m.run_id===s.run_id&&m.runtime_instance_id===s.runtime_instance_id&&m.result_sha256===s.expected_result_sha256&&m.result_status===r?.status&&m.execution_authority===false);
    literals(m.verification,{report_status:'DRAFT',binding_scope:'full_bound',data_origin:'provided_synthetic_result',storage_hashes_verified:true,hardware_verified:false,physical_verified:false,method_approval:'not_assessed',conformity_status:'not_assessed',execution_authorized:false,rerun_authorized:false});
    need(Array.isArray(m.files)&&m.files.length===2);for(const [i,row]of m.files.entries()){
      keys(row,'path bytes sha256 media_type');need(row.path===['result.json','draft.md'][i]&&row.media_type===['application/json','text/markdown'][i]&&positive(row.bytes)&&row.bytes<=[1048577,262144][i]&&sha(row.sha256));
    }
    need(typeof artifact.draft==='string'&&new TextEncoder().encode(artifact.draft).length<=262144&&new TextEncoder().encode(artifact.draft).length===m.files[1].bytes&&m.files[1].sha256===storage.draft_sha256&&artifact.draft.startsWith('# Conducted result DRAFT\n\nProvided synthetic snapshot. Storage completion is not conformity PASS.\n'));
    literals(artifact.verification,{source_references:'not_opened',current_binding:'caller_provided_hashes_and_ids_only',historical_publication_order:'not_verified',writer_outcome:'not_verified',draft_content:'not_interpreted',hardware_verified:false,physical_verified:false,source_authenticity_verified:false,method_approval:'not_assessed',conformity_status:'not_assessed',issuance_approval:'not_assessed',execution_authority:false,rerun_authority:false});
    need(bytes(r)+1<=1048577);binding(rel.artifact_binding);need(object(r.binding)&&Object.keys(r.binding).length===11&&equal(rel.artifact_binding,r.binding.plan_input?.binding??{}));
    need(r.binding.run_id===s.run_id&&r.binding.runtime_instance_id===s.runtime_instance_id);
    const ac={intake_id:rel.artifact_binding.intake_id,revision:rel.artifact_binding.revision};
    validatePlanPreviewPacket({schema_version:1,kind:'intake_conducted_plan_preview',...ac,context_sha256:rel.artifact_binding.context_sha256,context_scope:'current_provided_context',selection_status:'matched',plan_input:r.binding.plan_input},ac);
    validateConductedResultPacket({schema_version:1,kind:'intake_conducted_result_view',...ac,context_sha256:rel.artifact_binding.context_sha256,source_kind:'provided_snapshot',expected_current_binding:rel.artifact_binding,relation:{status:'matched',reasons:[],provided_revision:ac.revision},result:r},ac);
    for(const k of ARTIFACT_BINDING){const same=rel.current_binding[k]===rel.artifact_binding[k];need(rel.fields[k]===same);if(!same)reasons.push('artifact_'+k+'_mismatch');}
    status=!rel.fields.intake_id?'different_intake':reasons.length?'different_plan':'matched';
  }
  if(contextChanged)reasons.push('current_context_changed');if(analysisChanged)reasons.push('current_analysis_changed');if(contextChanged||analysisChanged)status='stale';
  need(status===v.status&&reasons.length===rel.reasons.length&&reasons.every((reason,i)=>rel.reasons[i]===reason));
  literals(v.verification,{scope:'two_readonly_current_snapshots_and_provided_artifact_pins',current_completion:'not_assessed',permanent_current_approval:false,method_approval:'not_assessed',regulatory:'not_assessed',physical_verified:false,execution_authority:false,rerun_authority:false,business_writes:false,artifact_history:'reader_scope_only'});
  return v;
}

export function describeConductedArtifactStorage(intake,observations={}){
  const observation=observations.storage,packet=observation?.value,context=packet?.current?.context;
  const belongs=context?.intake_id===intake.intake_id&&(!observation.context||observation.context.intake_id===intake.intake_id);
  const artifact=belongs&&packet.artifact?.result.binding.plan_input.binding.intake_id===intake.intake_id?packet.artifact:null;
  const foreign=Boolean(packet&&(!belongs||packet.artifact&&!artifact));
  const queue=describeIntakeGapQueue(intake,observations),planGate=queue.groups.find(x=>x.source==='plan_gaps'),plan=observations.plan?.value;
  const sameBinding=(a,b)=>a&&b&&ARTIFACT_BINDING.every(k=>a[k]===b[k]);
  const reasons=[];if(foreign)reasons.push('different_intake');
  if(observations.intakeStale||observations.parentPending)reasons.push('parent_snapshot_unconfirmed');
  if(observation?.pending||observation?.parentPending||observation?.stale)reasons.push('observation_unconfirmed');
  if(packet&&observation?.context?.generation!==(observations.generation??0))reasons.push('snapshot_generation_changed');
  if(belongs&&context.revision!==intake.revision)reasons.push('revision_changed');
  if(packet&&(planGate.state!=='current'||plan?.plan_input.status!=='ready_for_simulation'||!sameBinding(plan?.plan_input.binding,packet.relation.current_binding)||plan?.context_sha256!==packet.relation.recheck.context_sha256_before))reasons.push('current_plan_unconfirmed');
  if(packet&&packet.status!=='matched')reasons.push(packet.status);
  const current=Boolean(belongs&&artifact&&packet.status==='matched'&&!reasons.length);
  const scope=current?'current':!packet?'none':foreign?'blocked':reasons.some(x=>['parent_snapshot_unconfirmed','observation_unconfirmed','snapshot_generation_changed','revision_changed','stale'].includes(x))?'unconfirmed':'blocked';
  return {source_kind:'artifact_storage_readback',current,scope,foreign,reasons,status:belongs?packet.status:'unknown',code:observation?.errorCode??null,
    original_status:artifact?.result.status??null,artifact:artifact?structuredClone(artifact):null,
    current_facts:belongs?structuredClone(packet.current):null,relation:belongs&&!foreign?structuredClone(packet.relation):null,
    execution_authority:false,permanent_current_approval:false,ai:'unknown',conformity:'not_assessed'};
}

const QUEUE_EVIDENCE=new Set('source_statement_unsupported source_quote_mismatch source_condition_unbound source_fact_missing'.split(' '));
const QUEUE_LABELS={evidence_review:'해석·근거 연결 검토',facts_required:'제품 사실 확인',conditions_required:'시스템·시험조건 준비',system_error:'시스템·실행 오류',unsupported:'미지원',not_run:'미실행·미완료',uninterpreted:'미해석 원형',blocked:'차단 · 현재 질문 아님'};
const QUEUE_FACT_CODES=new Set('conflicting_intake_fact missing_intake_field follow_up_missing_field product_identity uncertain_intake_fact'.split(' '));
const QUEUE_CONDITIONS=new Set('missing_setting missing_method_field missing_or_invalid_basis intent_value_not_in_request_quote correction_basis_invalid correction_basis_missing metric_mismatch path_configuration_missing path_selection_missing'.split(' '));
const QUEUE_NOT_RUN=new Set('unread_documents execution_incomplete journal_incomplete measurement_missing measurement_not_referenced measurement_reference_missing setup_missing setup_partial plan_blocked'.split(' '));
const QUEUE_UNSUPPORTED=new Set('unsupported_modulation unsupported_method_field unsupported_or_invalid_basis unknown_source_field unknown_method_field unknown_basis_field unsupported_path_device'.split(' '));
const QUEUE_BINDING=new Set('expected_revision_changed_or_invalid expected_context_changed_or_invalid plan_binding_invalid plan_binding_mismatch plan_hash_mismatch run_binding_mismatch setup_hash_mismatch topology_hash_mismatch'.split(' '));
export function describeIntakeGapQueue(intake,{generation=0,intakeStale=false,intakeCode=null,plan=null,result=null,storage=null,currentFacts=null}={}){
  const clone=value=>structuredClone(value),object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
  const context={intake_id:intake.intake_id,revision:intake.revision,generation};
  const fields=Object.keys(FIELDS),bindingFields='intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256'.split(' ');
  const binding=value=>object(value)&&Object.keys(value).length===6&&bindingFields.every(key=>Object.hasOwn(value,key))&&typeof value.intake_id==='string'&&Number.isSafeInteger(value.revision)&&value.revision>0&&bindingFields.slice(2).every(key=>typeof value[key]==='string'&&/^[a-f0-9]{64}$/.test(value[key]));
  const availability=code=>code==='intake_conducted_preview_v2_pdf_required'||code==='intake_conducted_preview_synthetic_required'?'unsupported':code==='intake_conducted_preview_analysis_unavailable'||code==='intake_conducted_result_missing'?'not_run':code==='store_missing'?'conditions_required':code?'system_error':'not_run';
  const questionCategory=raw=>{
    if(!object(raw)||typeof raw.key!=='string'||typeof raw.message!=='string')return 'uninterpreted';
    if(QUEUE_EVIDENCE.has(raw.key)||QUEUE_EVIDENCE.has(raw.code))return 'evidence_review';
    if(raw.key==='product_identity')return 'facts_required';
    if(raw.key==='unread_documents'&&Array.isArray(raw.paths))return 'not_run';
    if(fields.includes(raw.field)&&(raw.key==='missing_'+raw.field||raw.key==='conflict_'+raw.field))return 'facts_required';
    return 'uninterpreted';
  };
  const gapCategory=raw=>{
    if(object(raw)&&QUEUE_EVIDENCE.has(raw.code))return 'evidence_review';
    if(!object(raw)||typeof raw.code!=='string'||typeof raw.field!=='string'||typeof raw.blocking!=='boolean'||!Object.hasOwn(raw,'provided'))return 'uninterpreted';
    if(QUEUE_BINDING.has(raw.code))return 'blocked';
    if(QUEUE_FACT_CODES.has(raw.code))return fields.some(field=>raw.field==='intake.'+field||raw.field==='intake.facts.'+field)||raw.code==='product_identity'&&raw.field==='intake.identity'?'facts_required':'uninterpreted';
    if(QUEUE_CONDITIONS.has(raw.code))return 'conditions_required';
    if(QUEUE_UNSUPPORTED.has(raw.code))return 'unsupported';
    if(QUEUE_NOT_RUN.has(raw.code))return 'not_run';
    if(PLAN_GAPS.includes(raw.code)||RESULT_INVALID.has(raw.code)||RESULT_INCOMPLETE.has(raw.code)||RESULT_GAP_ONLY.has(raw.code))return 'system_error';
    return 'uninterpreted';
  };
  function sourceState(obs,kind){
    const value=obs?.value,reasons=[];
    if(!value)return {state:intakeStale?'blocked':obs?.errorCode?'unavailable':'not_run',category:availability(obs?.errorCode),reasons:intakeStale?['parent_snapshot_unconfirmed']:[],code:obs?.errorCode||null,observed_revision:null,value:null,include:false};
    const revision=value.revision;
    if(value.intake_id!==intake.intake_id)return {state:'blocked',category:'blocked',reasons:['other_intake'],code:obs?.errorCode||null,observed_revision:revision??null,value,include:false};
    if(intakeStale)reasons.push('parent_snapshot_unconfirmed');
    if(obs.stale||obs.pending||obs.parentPending)reasons.push('observation_unconfirmed');
    if(!obs.context||obs.context.intake_id!==intake.intake_id||obs.context.revision!==intake.revision||revision!==intake.revision)reasons.push('revision_or_context_changed');
    if(obs.context?.generation!==generation)reasons.push('snapshot_generation_changed');
    if(kind==='plan'){
      const b=value.plan_input?.binding;
      if(value.context_scope!=='current_provided_context'||!binding(b)||b.intake_id!==value.intake_id||b.revision!==value.revision||b.context_sha256!==value.context_sha256)reasons.push('plan_binding_unconfirmed');
      if(['other_intake','revision_changed'].includes(value.selection_status))reasons.push('plan_selection_changed');
      if(Array.isArray(value.plan_input?.gaps)&&value.plan_input.gaps.some(raw=>object(raw)&&QUEUE_BINDING.has(raw.code)))reasons.push('plan_gap_binding_conflict');
    }else{
      const b=value.expected_current_binding;
      if(value.source_kind!=='provided_snapshot'||value.relation?.status!=='matched'||!binding(b)||b.intake_id!==value.intake_id||b.revision!==value.revision||b.context_sha256!==value.context_sha256)reasons.push('provided_binding_unconfirmed');
      if(Array.isArray(value.relation?.reasons))reasons.push(...value.relation.reasons);
      if(value.result?.status==='invalid')reasons.push('invalid_result_original_only');
    }
    return {state:reasons.length?'blocked':'current',category:reasons.length?'blocked':'observed',reasons:[...new Set(reasons)],code:obs.errorCode||null,observed_revision:revision,value,include:true};
  }
  const planState=sourceState(plan,'plan'),resultState=sourceState(result,'result');
  if(resultState.state==='current'){
    if(planState.state!=='current'){resultState.state='blocked';resultState.category='blocked';resultState.reasons.push('current_plan_unavailable');}
    else if(!binding(planState.value.plan_input?.binding)||!binding(resultState.value.expected_current_binding)||bindingFields.some(key=>planState.value.plan_input.binding[key]!==resultState.value.expected_current_binding[key])){resultState.state='blocked';resultState.category='blocked';resultState.reasons.push('plan_condition_mismatch');}
  }
  function group(source,label,state,raw,kind){
    const normal=Array.isArray(raw),items=state.include?(normal?raw:raw===undefined?[]:[raw]):[];
    const rows=items.map((value,index)=>{
      let category=normal?(kind==='question'?questionCategory(value):gapCategory(value)):'uninterpreted';
      const classification=category;
      if(state.state==='blocked')category='blocked';
      return {source,classification,note:classification==='evidence_review'?'원자료 부재는 미확인입니다. RF6 재입력 필요 여부는 이 공백만으로 정하지 않습니다.':null,index:normal?index:null,state:category==='blocked'||category==='uninterpreted'?'blocked':'current',category,label:QUEUE_LABELS[category],raw:clone(value)};
    });
    return {source,label,state:state.state,category:state.category,reasons:clone(state.reasons),code:state.code,observed_intake_id:state.value?.intake_id??intake.intake_id,observed_revision:state.observed_revision,provided_revision:source==='result_gaps'?state.value?.relation?.provided_revision??null:null,source_kind:source==='intake_questions'?'current_intake_snapshot':source==='result_gaps'?'provided_snapshot':'current_provided_context',condition_sha256:!state.include?null:source==='result_gaps'?state.value?.expected_current_binding?.plan_sha256??null:source.startsWith('plan_')?state.value?.plan_input?.binding?.plan_sha256??null:null,items:rows};
  }
  const intakeState={state:intakeStale?'blocked':intake.analysis?'current':'not_run',category:intakeStale?'blocked':intake.analysis?'observed':'not_run',reasons:intakeStale?['parent_snapshot_unconfirmed']:[],code:intakeCode,observed_revision:intake.revision,include:Boolean(intake.analysis),value:null};
  const groups=[group('intake_questions','접수 원 질문',intakeState,intake.analysis?.questions,'question'),group('plan_questions','계획 원 질문',planState,planState.value?.plan_input?.intake?.questions,'question'),group('plan_gaps','계획 원 조건·공백',planState,planState.value?.plan_input?.gaps,'gap'),group('result_gaps','제공 결과 원 공백',resultState,resultState.value?.result?.gaps,'gap')];
  function projectMinimumQuestions(f,source,observation,original){
    const rf={frequency_hz:'주파수',power_dbm:'source 전력',bandwidth_hz:'대역폭',duty_cycle:'듀티',modulation:'변조',crest_factor_db:'crest factor'};
    const actions={
      source_condition_unbound:['source_check','원 조건 연결 확인','원 인용들이 같은 시험 조건을 가리키는지 연결 근거를 확인하세요.'],
      source_unit_missing:['source_check','명시 단위 확인','원 값에 대응하는 명시 단위만 원문에서 확인하세요.'],
      source_statement_unsupported:['development_review','개발 지원 검토','제공된 문장의 형식과 해석 지원 범위를 검토하세요.'],
      source_unit_unsupported:['development_review','개발 지원 검토','원문에 적힌 단위의 지원 범위를 검토하세요.'],
      source_power_quantity_unsupported:['development_review','개발 지원 검토','원문 전력량 구분의 지원 범위를 검토하세요.'],
      source_fact_missing:['source_check','원 위치·제공 기록 확인','현재 검증한 인용에서 해당 후보를 얻지 못했습니다. 원 위치·제공 기록을 확인하세요.'],
      source_fact_unverified:['source_check','원 사실 근거 확인','제공된 사실과 그 명시 인용의 연결을 확인하세요.'],
      source_quote_mismatch:['source_check','인용 연결 확인','원 값과 인용이 같은 문장을 가리키는지 확인하세요.'],
      source_value_conflict:['source_check','원 값 충돌 확인','서로 다른 원 값과 각각의 조건·근거를 확인하세요.'],
      source_number_unrepresentable:['development_review','개발 지원 검토','원 수치 표현의 처리 지원 범위를 검토하세요.'],
      source_candidate_limit:['development_review','개발 지원 검토','원 후보 목록과 처리 한도를 검토하세요.'],
      invalid_rf_domain:['source_check','주파수·대역폭 근거 확인','원 주파수·대역폭의 제공 근거와 조건을 확인하세요.'],
    };
    const grouped=new Map(),uninterpreted=[],sourceFacts=f.plan_input.intake?.source_facts;
    f.questions.forEach((q,index)=>{
      const field=typeof q?.field==='string'?q.field.replace(/^source_settings\./,''):null,action=typeof q?.reason==='string'&&Object.hasOwn(actions,q.reason)?actions[q.reason]:null;
      if(!action||Object.keys(q).length!==4||!['key','field','reason','message'].every(k=>typeof q[k]==='string')||!q.message.trim()||!(q.field==='source_settings'||q.field.startsWith('source_settings.')&&Object.hasOwn(rf,field))){uninterpreted.push(index);return;}
      if(!(q.field==='source_settings'?['source_condition','source_domain'].includes(q.key):q.key==='source_'+field)){uninterpreted.push(index);return;}
      const key=q.reason+'\0'+q.field;
      if(!grouped.has(key))grouped.set(key,{reason:q.reason,field:q.field,kind:action[0],title:action[1],prompt:(rf[field]?rf[field]+': ':'')+action[2],origins:[],gaps:[],source_facts:[]});
      const row=grouped.get(key);row.origins.push({question_index:index,raw_question:clone(q)});
    });
    for(const row of grouped.values()){
      const factIndexes=new Set();
      f.assembly_gaps.forEach((gap,index)=>{
        if(!object(gap)||gap.code!==row.reason||!(gap.field===row.field||row.field==='source_settings'&&typeof gap.field==='string'&&gap.field.startsWith('source_settings.')))return;
        row.gaps.push({gap_index:index,raw:clone(gap)});
        const candidates=Array.isArray(gap.provided)?gap.provided:[gap.provided];for(const candidate of candidates)if(object(candidate)&&Number.isSafeInteger(candidate.fact_index)&&candidate.fact_index>=0)factIndexes.add(candidate.fact_index);
      });
      if(Array.isArray(sourceFacts))sourceFacts.forEach((raw,index)=>{if(factIndexes.has(index))row.source_facts.push({fact_index:index,raw:clone(raw)});});
    }
    return {state:'current',current:true,source,reasons:[],questions:[...grouped.values()],uninterpreted_question_indexes:uninterpreted,original,observation,execution_authority:false};
  }  function minimumStorage(){
    // This consumes an already parsed readback. It does not supply new facts,
    // infer RF settings, or require the artifact itself to have matched.
    const packet=storage?.value,c=packet?.current?.context,f=packet?.current?.facts_plan;
    const empty=(state,reasons,original=null)=>({state,current:false,reasons,questions:[],uninterpreted_question_indexes:[],original,execution_authority:false});
    if(!packet)return empty(storage?.errorCode?'unavailable':'not_provided',storage?.errorCode?[storage.errorCode]:[]);
    if(c?.intake_id!==intake.intake_id||storage.context?.intake_id!==intake.intake_id)return empty('blocked',['other_intake']);
    const original=object(f)?clone(f):null,reasons=[];
    if(intakeStale)reasons.push('parent_snapshot_unconfirmed');
    if(storage.pending||storage.parentPending||storage.stale||storage.errorCode)reasons.push('observation_unconfirmed');
    if(storage.context?.revision!==intake.revision||c.revision!==intake.revision)reasons.push('revision_changed');
    if(storage.context?.generation!==generation)reasons.push('snapshot_generation_changed');
    const b=packet.relation?.current_binding,recheck=packet.relation?.recheck,pb=planState.value?.plan_input?.binding;
    if(planState.state!=='current'||plan?.errorCode||!binding(b)||!binding(pb)||bindingFields.some(key=>b?.[key]!==pb?.[key])||b?.analysis_context_id!==c.analysis_context_id||b?.context_sha256!==planState.value?.context_sha256)reasons.push('current_plan_binding_unconfirmed');
    if(packet.schema_version!==1||packet.kind!=='intake_conducted_artifact_readback'||!object(f)||f.kind!=='intake_facts_to_conducted_plan'||f.schema_version!==1||!['ready_for_simulation','blocked'].includes(f.status)||!Array.isArray(f.questions)||!Array.isArray(f.assembly_gaps)||!binding(f.plan_input?.binding)||bindingFields.some(key=>b?.[key]!==f.plan_input?.binding[key]))reasons.push('facts_plan_unconfirmed');
    if(packet.status==='stale'||recheck?.status!=='unchanged'||recheck?.context_sha256_before!==recheck?.context_sha256_after||recheck?.analysis_sha256_before!==recheck?.analysis_sha256_after||recheck?.context_sha256_before!==b?.context_sha256||recheck?.analysis_sha256_before!==b?.analysis_sha256||packet.relation?.reasons?.includes('current_pin_missing'))reasons.push('current_recheck_unconfirmed');
    if(reasons.length)return empty('blocked',[...new Set(reasons)],original);
    return projectMinimumQuestions(f,'storage_fallback',null,original);
  }
  function minimumEvidence(){
    const s=currentFacts,empty=(state,reasons,original=null)=>({state,current:false,source:'current_facts',reasons,questions:[],uninterpreted_question_indexes:[],original,execution_authority:false});
    const fresh=s?.context?.intake_id===intake.intake_id&&s.context.revision===intake.revision&&s.context.generation===generation&&!intakeStale&&!s.pending&&!s.parentPending&&!s.stale;
    // Only a fresh, explicit unconfigured reply permits the independent legacy
    // readback path. Missing/error/stale configured observations never fall back.
    if(fresh&&s.errorCode==='intake_current_facts_plan_view_not_provided')return minimumStorage();
    const p=s?.value,c=p?.current?.context,f=p?.current?.facts_plan;
    if(!p){
      const history=s?.errorCode==='intake_current_facts_plan_view_not_provided'&&s.context?.intake_id===intake.intake_id&&storage?.context?.intake_id===intake.intake_id&&storage?.value?.current?.context?.intake_id===intake.intake_id?storage.value.current.facts_plan:null;
      const view=empty(s?.errorCode?'unavailable':'not_provided',s?.errorCode?[s.errorCode]:['current_facts_unobserved'],object(history)?clone(history):null);
      if(history)view.source='storage_history';return view;
    }
    if(c?.intake_id!==intake.intake_id||s.context?.intake_id!==intake.intake_id)return empty('blocked',['other_intake']);
    const original=object(f)?clone(f):null,reasons=[],b=f?.plan_input?.binding,r=p.recheck;
    if(intakeStale)reasons.push('parent_snapshot_unconfirmed');
    if(s.pending||s.parentPending||s.stale||s.errorCode)reasons.push('observation_unconfirmed');
    if(s.context?.revision!==intake.revision||c.revision!==intake.revision)reasons.push('revision_changed');
    if(s.context?.generation!==generation)reasons.push('snapshot_generation_changed');
    if(p.schema_version!==1||p.kind!=='intake_current_facts_plan_view'||!object(f)||f.schema_version!==1||f.kind!=='intake_facts_to_conducted_plan'||!['ready_for_simulation','blocked'].includes(f.status)||f.plan_input?.status!==f.status||!Array.isArray(f.questions)||!Array.isArray(f.assembly_gaps)||!binding(b)||b.intake_id!==c.intake_id||b.revision!==c.revision||b.analysis_context_id!==c.analysis_context_id||p.verification?.execution_authority!==false||p.verification?.permanent_current_approval!==false)reasons.push('current_facts_unconfirmed');
    if(p.status!=='available'||r?.status!=='unchanged'||r?.before?.context_sha256!==r?.after?.context_sha256||r?.before?.analysis_sha256!==r?.after?.analysis_sha256||r?.before?.context_sha256!==b?.context_sha256||r?.before?.analysis_sha256!==b?.analysis_sha256)reasons.push('current_recheck_unconfirmed');
    if(reasons.length)return empty('blocked',[...new Set(reasons)],original);
    return projectMinimumQuestions(f,'current_facts',clone({context:c,binding:b,recheck:r,verification:p.verification}),original);
  }

  const all=groups.flatMap(group=>group.items),count=category=>all.filter(row=>row.category===category).length;
  return {context,groups,minimum_evidence:minimumEvidence(),summary:{evidence_review:count('evidence_review'),current_facts:count('facts_required'),conditions:count('conditions_required'),system_errors:count('system_error'),unsupported:count('unsupported'),not_run:count('not_run'),blocked:count('blocked'),uninterpreted:count('uninterpreted')},execution_authority:false};
}

function unifyProvidedWorkflow(view,intake,observations){
  const parentStale=Boolean(observations.intakeStale||observations.parentPending);
  // Reuse the existing source/revision/generation/C1/binding fences. This is a
  // display projection of already parsed observations, not another DTO validator.
  const queue=describeIntakeGapQueue(intake,{...observations,intakeStale:parentStale});
  const planGate=queue.groups.find(group=>group.source==='plan_gaps');
  const resultGate=queue.groups.find(group=>group.source==='result_gaps');
  const same=value=>value?.intake_id===intake.intake_id?value:null;
  const plan=same(observations.plan?.value),packet=same(observations.result?.value),r=packet?.result;
  const planCurrent=Boolean(plan&&planGate.state==='current');
  const planReady=planCurrent&&plan.plan_input.status==='ready_for_simulation';
  const storage=describeConductedArtifactStorage(intake,observations);
  const current=Boolean(r&&planReady&&resultGate.state==='current'&&r.status==='recorded'
    &&r.raw_measurement!==null&&r.calculation.corrected!==null);
  const reasons=[...new Set([...planGate.reasons,...resultGate.reasons,
    ...(r&&!planReady?['plan_not_ready']:[]),...(r&&r.status!=='recorded'?['result_not_recorded']:[]),
    ...(r&&(r.raw_measurement===null||r.calculation.corrected===null)?['measurement_or_correction_null']:[])])];
  const unstable=parentStale||[observations.plan,observations.result].some(value=>value?.pending||value?.parentPending||value?.stale)
    ||reasons.some(value=>['snapshot_generation_changed','observation_unconfirmed','parent_snapshot_unconfirmed'].includes(value));
  const foreign=Boolean(observations.plan?.value&&!plan||observations.result?.value&&!packet);
  const scope=current?'current':r?(unstable?'unconfirmed':'blocked'):foreign?'blocked':'none';
  const relation=current?'제공 snapshot · 현재 C1/계획 binding 대조 일치 · 생성·실행 진위 미확인'
    :r?(scope==='unconfirmed'?'제공 이전 관측 · 현재 관계 미확인':`제공 원 상태 ${r.status} · 현재 측정으로 사용 차단`)
      :foreign?'다른 접수의 제공 관측 제외':planReady?'제공 계획 입력 관측 · 제공 결과 미관측':'제공 계획·결과 미관측 또는 미제공';
  const p={scope,current,relation,reasons,source_kind:'provided_snapshot',plan_scope:planGate.state,
    plan_status:plan?.plan_input.status??null,plan_ready:planReady,plan_current:planCurrent,
    original_status:r?.status??null,context_sha256:packet?.context_sha256??plan?.context_sha256??null,
    provided_revision:packet?.relation.provided_revision??null,
    run_id:r?.binding.run_id??null,runtime_instance_id:r?.binding.runtime_instance_id??null,
    measurement_ref:r?.binding.measurement_ref??null,
    raw_measurement:structuredClone(r?.raw_measurement??null),corrected:structuredClone(r?.calculation.corrected??null),
    conformity:structuredClone(r?.calculation.conformity??null),failure:structuredClone(r?.failure??null),
    storage:'unknown',ai:'unknown',cleanup:'unknown',independent_evaluation:'unknown',physical:'not_run',execution_authority:false};
  const fmt=conductedPreviewValue,selected=view.context.request_id!==null;
  const fixtureLines=step=>selected?[`기존 fixture: ${step.label}`,...step.lines.map(line=>`기존 fixture: ${line}`)]:['기존 fixture: 선택 기록 없음 · 제공 snapshot과 별도 출처'];
  const runLines=r?[
    `제공 기록: 원 run / runtime ${fmt(p.run_id)} / ${fmt(p.runtime_instance_id)}`,
    `제공 기록: 원 event ${fmt(p.measurement_ref)} · 제공 버전 ${fmt(p.provided_revision)}`,
    '제공 식별자 관측은 실제 실행·정리 확인을 뜻하지 않습니다.',
  ]:[];
  const measurementLines=r?[
    `제공 기록: 원 상태 ${r.status}`,
    `제공 기록: 원 값 / 단위 ${r.raw_measurement===null?fmt(null):`${fmt(r.raw_measurement.packet.value)} / ${fmt(r.raw_measurement.packet.unit)}`}`,
    `제공 기록: 원 기준면 ${fmt(r.raw_measurement?.reference_plane??null)}`,
    `제공 기록: 보정 ${fmt(r.calculation.corrected)} · target 기준면 ${fmt(r.calculation.target_reference_plane)}`,
    `제공 기록: 원 event ${fmt(p.measurement_ref)}`,
    `제공 기록: 규범 ${r.calculation.conformity.status} · 수치·보정을 화면에서 다시 계산하지 않습니다.`,
  ]:[];
  const steps=view.steps.map(step=>{
    if(!['plan','virtual','measurement','assessment'].includes(step.id))return step;
    const common={...step,provided_scope:scope,previous_lines:[],reference_source:'기존 fixture'};
    if(step.id==='plan')return {...common,
      label:planCurrent?`제공 계획 입력 · ${p.plan_status}`:plan?'제공 계획 이전 관측 · 현재 관계 미확인':'제공 계획 미관측 · DB 계획 미연결',
      tone:planReady?'info':'warning',lines:[
        'DB Case/Plan: case_id=null · plan_id=null',
        planCurrent?`제공 계획: ${p.plan_status} · 현재 C1 ${fmt(plan.context_sha256)}`:'제공 계획의 현재 C1/조건 결합 미확인',
        '제공 미리보기는 DB 계획 생성·방법 승인·실제 실행 권한이 아닙니다.',
      ],previous_lines:plan&&!planCurrent?[`제공 이전 계획 상태 ${p.plan_status} · C1 ${fmt(plan.context_sha256)}`]:[]};
    if(step.id==='virtual')return {...common,
      label:current?'제공 실행 식별 관측':r?'제공 실행 관측 · 현재 사용 차단':selected?`기존 fixture · ${step.label}`:'제공 실행 관측 미확인',
      tone:current?'info':r?'warning':step.tone,
      lines:[relation,...(current?runLines:[]),...fixtureLines(step)],previous_lines:r&&!current?runLines:[]};
    if(step.id==='measurement')return {...common,
      label:current?'제공 측정·계산 기록':r?`제공 결과 ${r.status} · 현재 사용 차단`:selected?`기존 fixture · ${step.label}`:'제공 측정·계산 미관측',
      tone:current?'info':r?'warning':step.tone,
      lines:[relation,...(current?measurementLines:[]),...fixtureLines(step)],previous_lines:r&&!current?measurementLines:[]};
    return {...common,label:storage.current?'산출물 고정 3파일 읽기 일치 · 판정 미평가':plan||r?'제공 기록 · 저장·독립평가 미확인':selected?`기존 fixture · ${step.label}`:'저장·독립평가 미확인',tone:storage.current?'info':'neutral',lines:[
      '제공 snapshot: 저장 완료 marker·DRAFT 검증 미확인',
      storage.current?`별도 산출물 읽기: 고정 3파일 bytes·hash·full binding 일치 관측 · 원 결과 ${storage.original_status}`:storage.scope==='none'?'별도 산출물 읽기: unknown · 미관측':`별도 산출물 읽기: ${storage.scope} · 현재 관계 미확인`,
      '산출물 읽기 일치는 당시 관측입니다. 작성 결과·게시 순서·영구 현재 승인·규범 판정을 보증하지 않습니다.',
      '제공 snapshot: 실제 AI 호출 여부 unknown · 정리·독립평가 미확인',
      '제공 snapshot: 작업 결과·규범 미평가(not_assessed) · 실측 대조 미실행',
      ...fixtureLines(step),
    ]};
  });
  return {...view,provided:p,artifact_storage:storage,steps,context:{...view.context,fixture_relation:view.context.relation,
    provided_scope:scope,relation:`${relation} · 기존 fixture: ${view.context.relation}`}};
}
