import test from 'node:test';
import assert from 'node:assert/strict';
import {validateFixtureRuns, describeFixtureRecord, requireStableFixtureRecords, createFixtureReadGate} from './intake_flow_model.mjs';

export function fixture() {
  const report = {schema_version: 1, kind: 'virtual_fleet_harness_result', run_id: 'run:ui-1', runtime_instance_id: 'instance:ui-1',
    synthetic: true, hardware_verified: false, ai_model_called: false, policy: {kind: 'fixture', id: 'rf_sensor_v1'},
    termination: {reason: 'policy_stop', policy_claim: 'completed'}, task_outcome: 'not_assessed', cleanup: {status: 'not_assessed', evidence_refs: []},
    usage: {decisions: 9, logical_requests: 7, transport_retries: 1, tick_delta: 3, reserved_ticks: 3, elapsed_ms: 12.5},
    evidence: {measurement_refs: ['event:18'], operator_transcript_ref: 'artifact:operator_events'}, unresolved_request_ids: [],
    assessment: {status: 'not_assessed', verdict: null, evaluator_id: null, evidence_refs: [], summary_code: null}};
  return {schema_version: 1, intake_id: 'I-1', current_revision: 2, storage_available: true, more_available: false, records: [{
    request_id: 'REQ-UI-1', intake_id: 'I-1', revision: 1, readiness_fingerprint: 'a'.repeat(64), recipe_id: 'conducted_sensor_fixture_v1',
    run_id: report.run_id, runtime_instance_id: report.runtime_instance_id, state: 'completed', source_current: false,
    source_synthetic: true, synthetic: true, hardware_verified: false, ai_model_called: false, resumable: false,
    case_id: null, plan_id: null, error_code: null, report}]};
}
const context = {intake_id: 'I-1', revision: 2};

test('legacy unavailable and available empty have distinct exact envelopes', () => {
  for (const storage_available of [false, true]) {
    const payload = {...fixture(), records: [], storage_available};
    assert.equal(validateFixtureRuns(payload, context).storage_available, storage_available);
  }
  const payload = fixture(); payload.storage_available = false;
  assert.throws(() => validateFixtureRuns(payload, context), /invalid_fixture_runs/);
});

test('only the exact intake revision and internally bound public report are accepted', () => {
  for (const mutate of [p => {p.intake_id = 'I-other';}, p => {p.current_revision = 3;},
    p => {p.records[0].intake_id = 'I-other';}, p => {p.records[0].revision = 3;},
    p => {p.records[0].source_current = true;}, p => {p.records[0].report.run_id = 'other';},
    p => {p.records[0].report.runtime_instance_id = 'other';}, p => {p.records[0].report = null;},
    p => {p.records[0].token = 'private';}, p => {p.records[0].report.policy.seed = 0;},
    p => {p.records[0].hardware_verified = true;}, p => {p.records[0].resumable = true;},
    p => {p.records[0].source_synthetic = 1;}, p => {p.records[0].case_id = 'C-1';},
    p => {p.records[0].readiness_fingerprint = 'bad';}, p => {p.records[0].error_code = 'C:/private.txt';},
    p => {p.records[0].readiness_fingerprint += '\n';}, p => {p.records[0].request_id += '\n';},
    p => {p.records[0].error_code = 'lease_lost\n';},
    p => {p.records[0].state = ['completed'];}, p => {p.records.push(structuredClone(p.records[0]));}]) {
    const payload = fixture(); mutate(payload);
    assert.throws(() => validateFixtureRuns(payload, context));
  }
});

test('recent twenty bound and more flag are strict and records are detached', () => {
  const data = fixture();
  const copy = validateFixtureRuns(data, context);
  data.records[0].report.evidence.measurement_refs.push('changed');
  assert.deepEqual(copy.records[0].report.evidence.measurement_refs, ['event:18']);
  data.records = Array.from({length:21}, (_, index) => ({...copy.records[0], request_id: `Q-${index}`}));
  assert.throws(() => validateFixtureRuns(data, context));
});

test('queue request identifiers allow the existing 150 character boundary', () => {
  const data=fixture(); data.records[0].request_id='Q'.repeat(150);
  assert.equal(validateFixtureRuns(data, context).records[0].request_id.length,150);
  data.records[0].request_id+='Q'; assert.throws(()=>validateFixtureRuns(data,context));
});

test('previous revision and changed readiness never appear as a current preparation', () => {
  const value = fixture().records[0];
  assert.match(describeFixtureRecord(value, 2).context, /이전 자료 버전/);
  value.revision = 2;
  assert.match(describeFixtureRecord(value, 2).context, /준비 상태 변경/);
  value.source_current = true;
  assert.match(describeFixtureRecord(value, 2).context, /현재 자료·준비 상태/);
  assert.doesNotMatch(describeFixtureRecord(value, 2).state.label, /측정 완료|FCC/);
});

test('completed historical identities and result cannot change under the same request ID', () => {
  const previous = fixture();
  assert.doesNotThrow(() => requireStableFixtureRecords(previous, fixture()));
  for (const mutate of [p => {p.records[0].run_id = 'other';}, p => {p.records[0].report = null;},
    p => {p.records[0].readiness_fingerprint = 'b'.repeat(64);}, p => {p.records[0].revision = 2;},
    p => {p.records[0].report.usage.decisions++;}, p => {p.records[0].state = 'running';}]) {
    const next = fixture(); mutate(next);
    assert.throws(() => requireStableFixtureRecords(previous, next), /fixture_record_changed/);
  }
  const queued = fixture(); Object.assign(queued.records[0], {state:'queued', run_id:null, runtime_instance_id:null, report:null});
  assert.doesNotThrow(() => requireStableFixtureRecords(queued, fixture()));
});

test('request sequence intake revision generation and selected request fence late results', () => {
  const gate = createFixtureReadGate();
  const current = {...context, generation: 1, request_id: 'Q-1'};
  const old = gate.begin(current);
  assert.equal(gate.isCurrent(old, current), true);
  const newer = gate.begin(current);
  assert.equal(gate.isCurrent(old, current), false);
  for (const changed of [{...current, intake_id:'I-2'}, {...current, revision:3},
    {...current, generation:2}, {...current, request_id:'Q-2'}]) assert.equal(gate.isCurrent(newer, changed), false);
  gate.invalidate(); assert.equal(gate.isCurrent(newer, current), false);
});
