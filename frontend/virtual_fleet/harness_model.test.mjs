import test from 'node:test';
import assert from 'node:assert/strict';
import {validateHarnessResponse, describeHarnessResult, requireSameReport} from './harness_model.mjs';

const result = () => ({schema_version: 1, kind: 'virtual_fleet_harness_result', run_id: 'run:ui-1', runtime_instance_id: 'instance:ui-1',
  synthetic: true, hardware_verified: false, ai_model_called: false, policy: {kind: 'fixture', id: 'rf_sensor_v1'},
  termination: {reason: 'policy_stop', policy_claim: 'completed'}, task_outcome: 'not_assessed', cleanup: {status: 'not_assessed', evidence_refs: []},
  usage: {decisions: 9, logical_requests: 7, transport_retries: 1, tick_delta: 3, reserved_ticks: 3, elapsed_ms: 12.5},
  evidence: {measurement_refs: ['event:18'], operator_transcript_ref: 'artifact:operator_events'}, unresolved_request_ids: [],
  assessment: {status: 'not_assessed', verdict: null, evaluator_id: null, evidence_refs: [], summary_code: null}});

test('absent result is distinct from a completed fixture and malformed response', () => {
  assert.equal(validateHarnessResponse({schema_version: 1, report: null}).report, null);
  assert.equal(validateHarnessResponse({schema_version: 1, report: result()}).report.run_id, 'run:ui-1');
  assert.throws(() => validateHarnessResponse({schema_version: 1}));
});

test('policy completed never turns not_assessed into a pass', () => {
  const view = describeHarnessResult(result());
  assert.equal(view.assessment.label, '독립 평가 미실행');
  assert.notEqual(view.assessment.tone, 'good');
  assert.equal(view.cleanup.label, '정리 상태 미평가');
  assert.match(view.policyClaim, /완료 주장/);
});

test('assessment fail and evaluator failure keep different meanings', () => {
  const data = result();
  data.assessment = {status: 'completed', verdict: 'fail', evaluator_id: 'evaluation:v1', evidence_refs: ['event:18'], summary_code: 'criterion_failed'};
  assert.equal(describeHarnessResult(data).assessment.label, '가상 평가 · 기준 불충족');
  data.assessment = {status: 'failed', verdict: null, evaluator_id: 'evaluation:v1', evidence_refs: [], summary_code: 'evaluator_error'};
  assert.equal(describeHarnessResult(data).assessment.label, '평가기 오류');
  assert.equal(validateHarnessResponse({schema_version: 1, report: data}).report.assessment.verdict, null);
});

test('non-policy stop accepts a null claim and unresolved requests stay visible', () => {
  const data = result(); data.termination = {reason: 'runtime_mutation_uncertain', policy_claim: null}; data.unresolved_request_ids = ['operator:7'];
  const view = describeHarnessResult(validateHarnessResponse({schema_version: 1, report: data}).report);
  assert.match(view.termination.label, /미확인/);
  assert.equal(view.policyClaim, '정책 주장 없음');
  assert.equal(view.unresolvedCount, 1);
});

test('rejects private fields invalid provenance types and malformed unicode', () => {
  for (const mutate of [r => {r.seed = 1;}, r => {r.policy.fault = 'private';}, r => {r.assessment.expected = 12;},
    r => {r.evidence.measurement_refs = [{password: 'private'}];}, r => {r.usage.decisions = true;},
    r => {r.usage.elapsed_ms = Infinity;}, r => {r.ai_model_called = true;}, r => {r.hardware_verified = true;},
    r => {r.policy.id = '\ud800';}, r => {r.assessment.verdict = 'pass';},
    r => {r.termination = {reason: 'supervisor_stop', policy_claim: 'completed'};}]) {
    const data = result(); mutate(data);
    assert.throws(() => validateHarnessResponse({schema_version: 1, report: data}), /invalid_harness_result/);
  }
});

test('a different run instance or missing record cannot replace a successful record', () => {
  const previous = result();
  assert.doesNotThrow(() => requireSameReport(previous, result()));
  for (const changed of [{...result(), run_id: 'other'}, {...result(), runtime_instance_id: 'other'}, null]) assert.throws(() => requireSameReport(previous, changed));
  assert.doesNotThrow(() => requireSameReport(null, result()));
});

test('validated payload is detached from its caller', () => {
  const data = result(); const actual = validateHarnessResponse({schema_version: 1, report: data});
  data.evidence.measurement_refs.push('mutated'); data.policy.id = 'mutated';
  assert.deepEqual(actual.report.evidence.measurement_refs, ['event:18']);
  assert.equal(actual.report.policy.id, 'rf_sensor_v1');
});

test('JSON arrays cannot impersonate reason and claim enum strings', () => {
  for (const termination of [{reason: 'policy_stop', policy_claim: ['completed']}, {reason: ['policy_stop'], policy_claim: null}]) {
    const data = result(); data.termination = termination;
    assert.throws(() => validateHarnessResponse({schema_version: 1, report: data}), /invalid_harness_result/);
  }
});
