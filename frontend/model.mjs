export const FIELDS = {
  product_type: '제품 종류', customer: '고객', manufacturer: '제조사', model: '모델',
  market: '의뢰 시장', purpose: '의뢰 목적', features: '기능', antenna_gain: '안테나 이득',
  power_target: '출력 목표', firmware: '펌웨어',
};
export const FACT_LABELS = {explicit: '원문 명시', inferred: '분석자 추론', uncertain: '불확실', user_confirmed: '사용자 답변'};
export const JOB_LABELS = {queued: '대기', running: '분석 중', completed: '분석 완료', failed: '실패', superseded: '이전 버전으로 종료'};
// A selection-confusion check only; it does not perform physical admission.
export function docxReferenceMatchesRecord(observation, record) {
  try {
    const b=observation.reference.binding;
    const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
    if (!b || !b.document || typeof b.source_id!=='string' || typeof b.intake_id!=='string' ||
        !Number.isSafeInteger(b.revision)||b.revision<1||!sha(b.revision_fingerprint)||!sha(b.document.sha256)||
        typeof b.document.path!=='string'||!b.document.path||!Number.isSafeInteger(b.document.bytes)||b.document.bytes<0||
        !record || b.source_id!==record.source_id || b.intake_id!==record.intake_id ||
        b.revision!==record.revision || !Array.isArray(record.history) || !Array.isArray(record.files)) return false;
    const revisions=record.history.filter(row=>row&&row.revision===b.revision);
    const files=record.files.filter(file=>file&&file.path===b.document.path);
    return revisions.length===1 && revisions[0].fingerprint===b.revision_fingerprint && files.length===1 &&
      files[0].sha256===b.document.sha256 && files[0].bytes===b.document.bytes;
  } catch { return false; }
}
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
    const fields = version === 1 ? ['path', 'sha256', 'line_start', 'line_end', 'quote', 'role']
      : value.kind === 'text_line' ? ['kind', 'path', 'sha256', 'line_start', 'line_end', 'quote', 'role']
        : value.kind === 'pdf_page' ? ['kind', 'path', 'sha256', 'extraction_id', 'page_number', 'text_sha256', 'line_start', 'line_end', 'quote', 'role'] : [];
    if (!fields.length || Object.keys(value).length !== fields.length || Object.keys(value).some(key => !fields.includes(key))) fail(path);
    for (const key of ['path', 'sha256', 'quote', 'role']) text(value[key], `${path}.${key}`);
    if (!['request', 'product', 'reference'].includes(value.role)) fail(`${path}.role`);
    if (!/^[a-f0-9]{64}$/.test(value.sha256)) fail(`${path}.sha256`);
    for (const key of ['line_start', 'line_end']) number(value[key], `${path}.${key}`, true, 1);
    if (value.line_end < value.line_start) fail(`${path}.line_end`);
    if (version === 2 && value.kind === 'pdf_page') {
      text(value.extraction_id, `${path}.extraction_id`);
      if (value.extraction_id.length > 256) fail(`${path}.extraction_id`);
      number(value.page_number, `${path}.page_number`, true, 1);
      text(value.text_sha256, `${path}.text_sha256`);
      if (!/^[a-f0-9]{64}$/.test(value.text_sha256)) fail(`${path}.text_sha256`);
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
  if (Object.hasOwn(payload, 'intake_test_intent_reviews')) {
    const limits={max_input_bytes:41943040,max_context_bytes:6291456,max_analysis_bytes:2097152,max_projection_bytes:8388608,
      max_observation_bytes:12582912,max_proposal_bytes:65536,max_sources_bytes:8388608,max_output_bytes:2097152,
      max_depth:32,max_nodes:2000000,max_source_documents:8,max_candidates_per_field:2,max_refs_per_side:8,
      max_literal_chars:256,max_institution_scope_chars:128,max_edition_chars:256,max_workflow_scope_ids:20,max_questions:200};
    const falseFlags='projection_recomputed result_projection_reverified database_currentness_verified source_authenticity_verified normative_applicability_verified institution_scope_verified edition_currentness_verified model_execution_verified model_quality_verified query_release_authorized case_selection_authorized execution_authorized'.split(' ');
    const reasons='intake_binding_incomplete intake_binding_mismatch intake_questions_open intent_missing intent_conflicting intake_ground_missing basis_missing literal_not_in_citation source_not_normative source_status_unconfirmed institution_scope_unconfirmed scope_conflicting edition_unconfirmed period_unconfirmed period_conflicting period_outside_declared_window applicability_not_assessed'.split(' ');
    let stringBytes=0;
    const keys=(value,names,path)=>{object(value,path);if(Object.keys(value).length!==names.length||names.some(key=>!Object.hasOwn(value,key)))fail(path);};
    const word=(value,path,cap=2097152,empty=false)=>{
      text(value,path,empty);if([...value].length>cap)fail(path);
      stringBytes+=new TextEncoder().encode(value).length;if(stringBytes>2097152)fail(path);
    };
    const integer=(value,path,min=0,max=Number.MAX_SAFE_INTEGER)=>{
      if(!Number.isSafeInteger(value)||value<min||value>max)fail(path);
    };
    const id=(value,path,max=150)=>{word(value,path,max);if(/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.exec(value)?.[0]!==value)fail(path);};
    const sha=(value,path,nullable=false)=>{if(nullable&&value===null)return;word(value,path,64);if(value.length!==64||!/^[a-f0-9]{64}$/.test(value))fail(path);};
    const choice=(value,allowed,path)=>{if(!allowed.includes(value))fail(path);};
    const list=(value,max,path,check)=>{if(!Array.isArray(value)||value.length>max)fail(path);array(value,path,check);};
    const codes=(value,path)=>{
      list(value,reasons.length,path,(item,where)=>{word(item,where,128);choice(item,reasons,where);});
      if(new Set(value).size!==value.length)fail(path);
    };
    const refs=(value,path,basis)=>{
      list(value,8,path,(item,where)=>{
        keys(item,basis?['document_id','page_number','text_sha256','line_start','line_end']:['fact_index','evidence_index'],where);
        if(basis){id(item.document_id,where,128);sha(item.text_sha256,where);integer(item.page_number,where,1);
          integer(item.line_start,where,1);integer(item.line_end,where,item.line_start);
        }else{integer(item.fact_index,where,0,199);integer(item.evidence_index,where,0,19);}
      });
      const tokens=value.map(item=>basis?[item.document_id,item.page_number,item.text_sha256,item.line_start,item.line_end].join('|'):[item.fact_index,item.evidence_index].join('|'));
      if(new Set(tokens).size!==tokens.length)fail(path);
    };
    list(payload.intake_test_intent_reviews,1,'intake_test_intent_reviews',(review,path)=>{
      keys(review,['schema_version','kind','status','input_binding','fields','questions','reason_codes','verification','limits'],path);
      if(review.schema_version!==1||review.kind!=='intake_test_intent_review'||review.status!=='review_only')fail(path);
      const binding=review.input_binding;
      keys(binding,['intake_id','revision','analysis_context_id','result_sha256','observation_snapshot_id','provided_context_sha256',
        'provided_analysis_sha256','provided_projection_sha256','provided_proposal_sha256','provided_sources_sha256','provided_observation_sha256'],path);
      id(binding.intake_id,path);integer(binding.revision,path,1);
      for(const key of ['analysis_context_id','result_sha256','observation_snapshot_id','provided_observation_sha256'])sha(binding[key],path,true);
      for(const key of ['provided_context_sha256','provided_analysis_sha256','provided_projection_sha256','provided_proposal_sha256','provided_sources_sha256'])sha(binding[key],path);
      if(!payload.intakes.some(record=>record.intake_id===binding.intake_id&&record.revision===binding.revision&&record.analysis!==null))fail(path);
      keys(review.verification,[...falseFlags,'intake_citations_checked','basis_literals_checked'],path);
      for(const key of falseFlags)if(review.verification[key]!==false)fail(path);
      for(const key of ['intake_citations_checked','basis_literals_checked'])if(typeof review.verification[key]!=='boolean')fail(path);
      keys(review.limits,Object.keys(limits),path);
      for(const [key,value] of Object.entries(limits))if(review.limits[key]!==value)fail(path);
      keys(review.fields,['rule','method'],path);
      for(const field of ['rule','method']){
        const value=review.fields[field];keys(value,['status','candidates','reason_codes'],path);
        choice(value.status,['missing','proposed','conflicting','literal_linked'],path);codes(value.reason_codes,path);
        list(value.candidates,2,path,(candidate,where)=>{
          keys(candidate,['literal','origin','intake_refs','basis_refs','literal_linked','period_checks','reason_codes'],where);
          word(candidate.literal,where,256);choice(candidate.origin,['explicit_supplied','model_proposed'],where);
          if(typeof candidate.literal_linked!=='boolean')fail(where);
          refs(candidate.intake_refs,where,false);refs(candidate.basis_refs,where,true);codes(candidate.reason_codes,where);
          list(candidate.period_checks,8,where,(period,location)=>{
            keys(period,['document_id','status'],location);id(period.document_id,location,128);
            choice(period.status,['unconfirmed','conflicting','in_declared_window','outside_declared_window'],location);
          });
          if(new Set(candidate.period_checks.map(item=>item.document_id)).size!==candidate.period_checks.length)fail(where);
        });
      }
      codes(review.reason_codes,path);
      list(review.questions,200,path,(value,where)=>{
        const fields='product_type customer manufacturer model market purpose features antenna_gain power_target firmware'.split(' ');
        object(value,where);word(value.key,where);
        const names=value.key==='product_identity'?['key','message']:value.key==='unread_documents'?['key','paths','message']
          :['key','field','message',...(value.key.startsWith('conflict_')?['values']:[])];
        keys(value,names,where);word(value.message,where,2097152,true);
        if(Object.hasOwn(value,'field')){
          choice(value.field,fields,where);
          if(value.key!==(value.key.startsWith('conflict_')?'conflict_':'missing_')+value.field)fail(where);
        }
        if(Object.hasOwn(value,'values')){
          list(value.values,200,where,(item,location)=>word(item,location,4000));if(value.values.length<2)fail(where);
        }
        if(Object.hasOwn(value,'paths'))array(value.paths,where,(item,location)=>{
          word(item,location);if(item.startsWith('/')||/[\\:]/.test(item)||item.split('/').some(part=>['','.','..'].includes(part)))fail(location);
        });
      });
      if(new TextEncoder().encode(JSON.stringify(review)).length>2097152)fail(path);
    });
  }
  return payload;
}
