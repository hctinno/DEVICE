// Completed public v1 result only. This module never starts or controls a run.
const REASONS = {
  policy_stop: ['정책 종료', 'neutral'], supervisor_stop: ['감독 중단', 'warning'],
  decision_budget: ['판단 예산 종료', 'warning'], request_budget: ['요청 예산 종료', 'warning'],
  tick_budget: ['가상 tick 예산 종료', 'warning'], wall_deadline: ['협력식 실행 기한 종료', 'warning'],
  policy_error: ['정책 오류', 'danger'], invalid_proposal: ['잘못된 동작 제안', 'danger'],
  runtime_error: ['런타임 오류', 'danger'], runtime_mutation_uncertain: ['동작 반영 여부 미확인', 'danger'], evidence_error: ['증거 저장 오류', 'danger'],
};
const CLAIMS = {completed: '완료 주장', blocked: '진행 불가 주장', unsupported: '미지원 주장', failed: '실패 주장'};
const MAX_BYTES = 256 * 1024;

export function validateHarnessResponse(payload) {
  const fail = path => {throw Object.assign(new Error('invalid_harness_result'), {path});};
  const record = (value, fields, path) => {
    if (value === null || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) fail(path);
    const keys = Object.keys(value), expected = fields.split(' ');
    if (keys.length !== expected.length || keys.some(key => !expected.includes(key))) fail(path);
  };
  const text = (value, path, maximum = 128, nullable = false) => {
    if (nullable && value === null) return;
    if (typeof value !== 'string' || !value.trim() || value.length > maximum) fail(path);
    for (let index = 0; index < value.length; index++) {
      const point = value.charCodeAt(index);
      if (point >= 0xd800 && point <= 0xdbff) {
        const next = value.charCodeAt(++index);
        if (!(next >= 0xdc00 && next <= 0xdfff)) fail(path);
      } else if (point >= 0xdc00 && point <= 0xdfff) fail(path);
    }
  };
  const references = (value, path) => {
    if (!Array.isArray(value) || value.length > 4096) fail(path);
    value.forEach((reference, index) => {
      text(reference, `${path}[${index}]`, 1024);
      if (/^(?:[/\\]|[A-Za-z]:[/\\]|(?:https?|file):)/i.test(reference)) fail(path);
    });
  };
  record(payload, 'schema_version report', 'response');
  if (payload.schema_version !== 1) fail('response.schema_version');
  const report = payload.report;
  if (report !== null) {
    record(report, 'schema_version kind run_id runtime_instance_id synthetic hardware_verified ai_model_called policy termination task_outcome cleanup usage evidence unresolved_request_ids assessment', 'report');
    if (report.schema_version !== 1 || report.kind !== 'virtual_fleet_harness_result') fail('report.schema');
    if (report.synthetic !== true || report.hardware_verified !== false || report.ai_model_called !== false) fail('report.provenance');
    text(report.run_id, 'run_id'); text(report.runtime_instance_id, 'runtime_instance_id');
    record(report.policy, 'kind id', 'policy');
    if (report.policy.kind !== 'fixture') fail('policy.kind');
    text(report.policy.id, 'policy.id');
    record(report.termination, 'reason policy_claim', 'termination');
    if (typeof report.termination.reason !== 'string' || !Object.hasOwn(REASONS, report.termination.reason)) fail('termination.reason');
    if (report.termination.reason === 'policy_stop' ? typeof report.termination.policy_claim !== 'string' || !Object.hasOwn(CLAIMS, report.termination.policy_claim) : report.termination.policy_claim !== null) fail('termination.policy_claim');
    if (report.task_outcome !== 'not_assessed') fail('task_outcome');
    record(report.cleanup, 'status evidence_refs', 'cleanup');
    if (report.cleanup.status !== 'not_assessed') fail('cleanup.status');
    references(report.cleanup.evidence_refs, 'cleanup.evidence_refs');
    record(report.usage, 'decisions logical_requests transport_retries tick_delta reserved_ticks elapsed_ms', 'usage');
    for (const [name, value] of Object.entries(report.usage)) {
      if (name === 'elapsed_ms' ? !Number.isFinite(value) || value < 0 : !Number.isSafeInteger(value) || value < 0) fail(`usage.${name}`);
    }
    record(report.evidence, 'measurement_refs operator_transcript_ref', 'evidence');
    references(report.evidence.measurement_refs, 'evidence.measurement_refs');
    references([report.evidence.operator_transcript_ref], 'evidence.operator_transcript_ref');
    references(report.unresolved_request_ids, 'unresolved_request_ids');
    record(report.assessment, 'status verdict evaluator_id evidence_refs summary_code', 'assessment');
    const assessment = report.assessment;
    if (!['not_assessed', 'completed', 'failed'].includes(assessment.status)) fail('assessment.status');
    if (assessment.status === 'completed' ? !['pass', 'fail', 'inconclusive'].includes(assessment.verdict) : assessment.verdict !== null) fail('assessment.verdict');
    text(assessment.evaluator_id, 'assessment.evaluator_id', 128, true); text(assessment.summary_code, 'assessment.summary_code', 128, true);
    references(assessment.evidence_refs, 'assessment.evidence_refs');
    let size;
    try {size = new TextEncoder().encode(JSON.stringify(report)).length;} catch {fail('report.json');}
    if (size > MAX_BYTES) fail('report.size');
  }
  return structuredClone(payload);
}

export function requireSameReport(previous, next) {
  if (previous && (!next || next.run_id !== previous.run_id || next.runtime_instance_id !== previous.runtime_instance_id)) throw new Error('harness_report_identity_changed');
}

export function describeHarnessResult(report) {
  const [label, tone] = REASONS[report.termination.reason];
  const assessment = report.assessment;
  let status;
  if (assessment.status === 'not_assessed') status = {label: '독립 평가 미실행', tone: 'neutral'};
  else if (assessment.status === 'failed') status = {label: '평가기 오류', tone: 'danger'};
  else status = {pass: {label: '가상 시나리오 평가 통과', tone: 'good'}, fail: {label: '가상 평가 · 기준 불충족', tone: 'danger'}, inconclusive: {label: '평가 완료 · 판정 불가', tone: 'warning'}}[assessment.verdict];
  return {termination: {label, tone}, policyClaim: report.termination.policy_claim === null ? '정책 주장 없음' : `정책의 ${CLAIMS[report.termination.policy_claim]}`,
    assessment: status, cleanup: {label: '정리 상태 미평가', tone: 'neutral'}, taskOutcome: '작업 결과 미평가', unresolvedCount: report.unresolved_request_ids.length};
}
