export const FIELDS = {
  product_type: '제품 종류', customer: '고객', manufacturer: '제조사', model: '모델',
  market: '의뢰 시장', purpose: '의뢰 목적', features: '기능', antenna_gain: '안테나 이득',
  power_target: '출력 목표', firmware: '펌웨어',
};
export const FACT_LABELS = {explicit: '원문 명시', inferred: '분석자 추론', uncertain: '불확실', user_confirmed: '사용자 답변'};
export const JOB_LABELS = {queued: '대기', running: '분석 중', completed: '분석 완료', failed: '실패', superseded: '이전 버전으로 종료'};
const STATES = {
  deferred: ['보류', 'neutral', 'Ⅱ', '저장된 보류 의사입니다. 화면에서 자동 재개하지 않습니다.'],
  upload_incomplete: ['자료 미완성', 'warning', '!', '입력 묶음의 안정화 또는 파일 보완이 필요합니다.'],
  analysis_failed: ['분석 실패', 'danger', '!', '분석 작업의 오류와 재시도 기록을 확인하세요.'],
  awaiting_analysis: ['분석 대기', 'neutral', '◷', '접수는 저장됐으며 분석 결과를 기다립니다.'],
  analyzing: ['분석 중', 'info', '↻', '작업 임대가 기록되어 있습니다. 실제 모델 실행 여부는 별도 확인이 필요합니다.'],
  lease_expired: ['임대 만료 · 확인 필요', 'warning', '!', '작업 임대 시각이 지났습니다. 재인수 또는 실패 갱신 여부를 확인해야 합니다.'],
  needs_information: ['확인 필요', 'warning', '!', '누락·충돌 또는 읽지 못한 자료가 있습니다.'],
  plan_pending: ['계획 연결 대기', 'info', '→', '접수 진행이 위임됐습니다. 시험계획 및 실장비 준비는 확인되지 않았습니다.'],
  propose_start: ['착수 제안', 'info', '→', '접수 분석이 저장됐습니다. 후속 업무 착수 제안 상태입니다.'],
  invalid: ['상태 확인 필요', 'warning', '?', '분석 상태와 저장된 결과가 맞지 않습니다.'],
  unsupported: ['지원 미확인 상태', 'warning', '?', '알 수 없는 상태를 완료로 처리하지 않습니다. 원래 상태 코드를 확인하세요.'],
};

export function describeState(record, now = Date.now() / 1000) {
  let code;
  if (!['awaiting_analysis', 'analyzed', 'analysis_failed', 'upload_incomplete'].includes(record.status)) code = 'unsupported';
  else if (record.deferred) code = 'deferred';
  else if (record.status === 'analyzed') {
    const actions = {needs_information: 'needs_information', prepare_plan: 'plan_pending',
      propose_start: 'propose_start', deferred: 'deferred'};
    code = !record.analysis ? 'invalid' : Object.hasOwn(actions, record.analysis.next_action)
      ? actions[record.analysis.next_action] : 'unsupported';
  } else if (record.status === 'awaiting_analysis') {
    const job = (record.jobs || []).find(j => j.revision === record.revision);
    code = !job || job.state === 'queued' ? 'awaiting_analysis'
      : job.state === 'running' ? (Number.isFinite(job.lease_until) && job.lease_until <= now ? 'lease_expired' : 'analyzing') : 'unsupported';
  } else code = record.status;
  const [label, tone, symbol, hint] = STATES[code];
  return {code, label, tone, symbol, hint};
}

export function factSources(record, field) {
  const fact = record.analysis?.facts?.[field];
  if (!fact || fact.status === 'user_confirmed') return [];
  return (record.analysis?.submitted?.facts || [])
    .filter(candidate => candidate.field === field && candidate.value.trim() === fact.value
      && ['explicit', 'inferred'].includes(candidate.status)
      && (!['market', 'purpose'].includes(field)
        || (candidate.status === 'explicit' && (candidate.evidence || []).every(source => source.role === 'request'))))
    .flatMap(candidate => candidate.evidence || []);
}

export function filterIntakes(records, {query = '', filter = 'all'} = {}) {
  const term = query.trim().toLocaleLowerCase('ko');
  return records.filter(record => {
    const state = describeState(record).code;
    const matches = filter === 'all'
      || (filter === 'attention' && ['needs_information', 'upload_incomplete', 'analysis_failed', 'lease_expired', 'invalid', 'unsupported'].includes(state))
      || (filter === 'waiting' && ['awaiting_analysis', 'analyzing'].includes(state))
      || (filter === 'deferred' && state === 'deferred')
      || (filter === 'failed' && state === 'analysis_failed');
    const text = [record.bundle, record.source_id, record.intake_id,
      ...Object.values(record.analysis?.facts || {}).map(fact => fact.value)].join(' ').toLocaleLowerCase('ko');
    return matches && text.includes(term);
  });
}

export function noticeContext(notice, record) {
  if (notice.revision < record?.revision) return {code: 'previous_revision', label: '이전 버전 기록'};
  if (notice.revision === record?.revision) return {code: 'same_revision', label: '같은 버전 · 생성 당시 기록'};
  return {code: 'unknown_revision', label: '버전 관계 미확인'};
}

export function seoulTime(value) {
  const date = new Date(typeof value === 'number' ? value * 1000 : value);
  if (value == null || !Number.isFinite(date.getTime())) return '기록 없음';
  return new Intl.DateTimeFormat('ko-KR', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false}).format(date);
}

export function bytes(value) {
  if (!Number.isFinite(value)) return '크기 미확인';
  return value < 1024 ? `${value} B` : `${(value / 1024).toFixed(1)} KiB`;
}

// Validate the structures consumed by the renderer, without reinterpreting
// analysis claims or replacing missing evidence with invented sources.
export function validateSnapshot(payload) {
  const fail = path => { throw Object.assign(new Error('invalid_snapshot'), {path}); };
  const object = (value, path) => {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(path);
  };
  const text = (value, path, allowEmpty = false) => {
    if (typeof value !== 'string' || (!allowEmpty && !value.trim())) fail(path);
  };
  const number = (value, path, integer = false, minimum = 0) => {
    if (!Number.isFinite(value) || value < minimum || (integer && !Number.isInteger(value))) fail(path);
  };
  const array = (value, path, check) => {
    if (!Array.isArray(value)) fail(path);
    value.forEach((item, index) => check(item, `${path}[${index}]`));
  };
  const optionalText = (value, path) => { if (value !== undefined) text(value, path, true); };
  const citation = (value, path, version = 1) => {
    object(value, path);
    if (version === 2) {
      const fields = value.kind === 'text_line' ? ['kind', 'path', 'sha256', 'line_start', 'line_end', 'quote', 'role']
        : value.kind === 'pdf_page' ? ['kind', 'path', 'sha256', 'extraction_id', 'page_number', 'text_sha256', 'line_start', 'line_end', 'quote', 'role'] : [];
      if (!fields.length || Object.keys(value).length !== fields.length || Object.keys(value).some(key => !fields.includes(key))) fail(path);
      for (const key of ['path', 'sha256', 'quote', 'role']) text(value[key], `${path}.${key}`);
      if (!['request', 'product', 'reference'].includes(value.role)) fail(`${path}.role`);
      if (!/^[a-f0-9]{64}$/.test(value.sha256)) fail(`${path}.sha256`);
      for (const key of ['line_start', 'line_end']) number(value[key], `${path}.${key}`, true, 1);
      if (value.line_end < value.line_start) fail(`${path}.line_end`);
      if (value.kind === 'pdf_page') {
        text(value.extraction_id, `${path}.extraction_id`);
        if (value.extraction_id.length > 256) fail(`${path}.extraction_id`);
        number(value.page_number, `${path}.page_number`, true, 1);
        text(value.text_sha256, `${path}.text_sha256`);
        if (!/^[a-f0-9]{64}$/.test(value.text_sha256)) fail(`${path}.text_sha256`);
      }
    } else if (value.kind !== undefined) fail(`${path}.kind`);
    for (const key of ['path', 'sha256', 'quote', 'role']) optionalText(value[key], `${path}.${key}`);
    for (const key of ['line_start', 'line_end']) {
      if (value[key] !== undefined) number(value[key], `${path}.${key}`, true, 1);
    }
  };
  const candidate = (value, path, version) => {
    object(value, path);
    for (const key of ['field', 'value', 'status']) text(value[key], `${path}.${key}`);
    if (value.evidence !== undefined) array(value.evidence, `${path}.evidence`, (source, location) => citation(source, location, version));
  };
  const question = (value, path) => {
    object(value, path);
    for (const key of ['key', 'message']) text(value[key], `${path}.${key}`);
    optionalText(value.field, `${path}.field`);
    for (const key of ['values', 'paths']) {
      if (value[key] !== undefined) array(value[key], `${path}.${key}`, text);
    }
  };
  const analysis = (value, path) => {
    object(value, path);
    object(value.facts, `${path}.facts`);
    for (const [field, fact] of Object.entries(value.facts)) {
      const location = `${path}.facts.${field}`;
      object(fact, location);
      text(fact.value, `${location}.value`);
      text(fact.status, `${location}.status`);
      optionalText(fact.event_id, `${location}.event_id`);
    }
    array(value.questions, `${path}.questions`, question);
    text(value.next_action, `${path}.next_action`);
    if (value.submitted !== undefined) {
      object(value.submitted, `${path}.submitted`);
      const version = value.submitted.schema_version === undefined ? 1 : value.submitted.schema_version;
      if (![1, 2].includes(version)) fail(`${path}.submitted.schema_version`);
      if (version === 2) {
        text(value.submitted.context_id, `${path}.submitted.context_id`);
        if (value.submitted.context_id.length > 256) fail(`${path}.submitted.context_id`);
      } else if (value.submitted.context_id !== undefined) fail(`${path}.submitted.context_id`);
      array(value.submitted.facts, `${path}.submitted.facts`, (fact, location) => candidate(fact, location, version));
      if (value.submitted.producer !== undefined) {
        object(value.submitted.producer, `${path}.submitted.producer`);
        for (const key of ['kind', 'name']) text(value.submitted.producer[key], `${path}.submitted.producer.${key}`);
      }
    }
    if (value.unread_documents !== undefined) array(value.unread_documents, `${path}.unread_documents`, text);
  };
  const file = (value, path) => {
    object(value, path);
    text(value.path, `${path}.path`);
    text(value.sha256, `${path}.sha256`);
    number(value.bytes, `${path}.bytes`, true);
  };
  const record = (value, path) => {
    object(value, path);
    for (const key of ['intake_id', 'source_id', 'bundle', 'status', 'measurement_support']) text(value[key], `${path}.${key}`);
    for (const key of ['synthetic', 'deferred', 'delegated']) if (typeof value[key] !== 'boolean') fail(`${path}.${key}`);
    number(value.revision, `${path}.revision`, true, 1);
    if (value.analysis !== null) analysis(value.analysis, `${path}.analysis`);
    array(value.files, `${path}.files`, file);
    array(value.history, `${path}.history`, (revision, location) => {
      object(revision, location);
      number(revision.revision, `${location}.revision`, true, 1);
      number(revision.created_at, `${location}.created_at`);
      array(revision.files, `${location}.files`, file);
    });
    array(value.jobs, `${path}.jobs`, (job, location) => {
      object(job, location);
      text(job.job_id, `${location}.job_id`);
      text(job.state, `${location}.state`);
      number(job.revision, `${location}.revision`, true, 1);
      number(job.attempt, `${location}.attempt`, true);
      if (job.error_code != null) text(job.error_code, `${location}.error_code`);
      if (job.lease_until != null) number(job.lease_until, `${location}.lease_until`);
    });
  };
  object(payload, 'response');
  if (payload.schema_version !== 1) fail('schema_version');
  text(payload.generated_at, 'generated_at');
  if (!Number.isFinite(new Date(payload.generated_at).getTime())) fail('generated_at');
  array(payload.intakes, 'intakes', record);
  array(payload.notifications, 'notifications', (notice, path) => {
    object(notice, path);
    number(notice.notification_id, `${path}.notification_id`, true, 1);
    text(notice.intake_id, `${path}.intake_id`);
    number(notice.revision, `${path}.revision`, true, 1);
    analysis(notice.payload, `${path}.payload`);
  });
  return payload;
}
