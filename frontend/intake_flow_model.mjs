import {validateHarnessResponse, describeHarnessResult} from './virtual_fleet/harness_model.mjs';

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
