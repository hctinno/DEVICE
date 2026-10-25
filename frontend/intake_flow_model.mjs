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
export function describeIntakeWorkflow(intake, {payload=null, request_id='', stale=false, pending=false, now=0}={}) {
  const records=payload===null?[]:validateFixtureRuns(payload,{intake_id:intake.intake_id,revision:intake.revision}).records;
  const selected=records.find(record=>record.request_id===request_id) || null;
  const description=selected?describeFixtureRecord(selected,intake.revision):null;
  const report=selected?.report, result=description?.result;
  const scope=selected?(stale||pending?'unconfirmed':selected.source_current?'current':'historical'):'none';
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
  return {context,steps:[
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
