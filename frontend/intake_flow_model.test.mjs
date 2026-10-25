import test from 'node:test';
import assert from 'node:assert/strict';
import {validateFixtureRuns, describeFixtureRecord, requireStableFixtureRecords, createFixtureReadGate} from './intake_flow_model.mjs';
import * as workflowAPI from './intake_flow_model.mjs';

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

function workflowIntake() {
  return {intake_id:'I-1', revision:2, status:'analyzed', synthetic:true, delegated:true, deferred:false,
    measurement_support:'not_connected', jobs:[], files:[{path:'request.txt',sha256:'d'.repeat(64),bytes:80}],
    history:[{revision:2,fingerprint:'f'.repeat(64)}], analysis:{next_action:'prepare_plan', questions:[],
      facts:{product_type:{value:'smartphone',status:'explicit'},market:{value:'US',status:'explicit'},purpose:{value:'synthetic check',status:'explicit'}},
      submitted:{facts:[]}}};
}
function workflow(intake=workflowIntake(), options={}) {
  assert.equal(typeof workflowAPI.describeIntakeWorkflow,'function','missing same-context workflow view');
  return workflowAPI.describeIntakeWorkflow(intake,options);
}
const step=(view,id)=>view.steps.find(item=>item.id===id);
const stepText=(view,id)=>[step(view,id).label,...step(view,id).lines].join('\n');
function currentFixture() {
  const payload=fixture();Object.assign(payload.records[0],{revision:2,source_current:true});return payload;
}

test('workflow shows product purpose market version and all seven stages without inventing plan or quantities',()=>{
  const view=workflow();
  assert.deepEqual(view.steps.map(item=>item.id),['intake','gaps','plan','virtual','measurement','assessment','physical']);
  assert.equal(view.context.intake_id,'I-1');assert.equal(view.context.revision,2);assert.equal(view.context.revision_fingerprint,'f'.repeat(64));
  assert.match(stepText(view,'intake'),/smartphone/);assert.match(stepText(view,'intake'),/US/);assert.match(stepText(view,'intake'),/synthetic check/);
  assert.match(stepText(view,'plan'),/시험계획 미연결/);assert.match(stepText(view,'measurement'),/원수치\/단위·기준면 미제공/);
  assert.match(stepText(view,'measurement'),/규격 판정 미실행/);assert.match(stepText(view,'physical'),/실측 대조 미실행/);
});

test('missing conflicting unread and unsupported intake remain explicit even when a stored run exists',()=>{
  const intake=workflowIntake();intake.analysis.questions=[{key:'missing_firmware',message:'펌웨어 누락'},{key:'conflict_market',message:'시장 충돌'},{key:'unread_documents',message:'PDF 해석 미지원'}];
  const view=workflow(intake,{payload:currentFixture(),request_id:'REQ-UI-1'});
  assert.match(stepText(view,'gaps'),/펌웨어 누락/);assert.match(stepText(view,'gaps'),/시장 충돌/);assert.match(stepText(view,'gaps'),/PDF 해석 미지원/);
  intake.analysis=null;assert.match(stepText(workflow(intake),'gaps'),/아직 확인하지 못/);
  intake.status='future';assert.match(stepText(workflow(intake),'intake'),/지원 미확인/);
});

test('policy completed and independent virtual pass cannot complete calculation regulatory task or physical stages',()=>{
  const payload=currentFixture();payload.records[0].report.assessment={status:'completed',verdict:'pass',evaluator_id:'fixture:evaluator',evidence_refs:['artifact:assessment'],summary_code:'synthetic_observed'};
  const before=structuredClone(payload),view=workflow(workflowIntake(),{payload,request_id:'REQ-UI-1'});
  assert.match(stepText(view,'virtual'),/실행 기록 저장/);assert.match(stepText(view,'assessment'),/가상 시나리오 평가 통과/);
  assert.match(stepText(view,'assessment'),/작업 결과 미평가/);assert.match(stepText(view,'measurement'),/가상 측정 근거 1개/);
  assert.match(stepText(view,'measurement'),/규격 판정 미실행/);assert.match(stepText(view,'physical'),/물리 정확도 미검증/);
  assert.deepEqual(payload,before);assert.doesNotMatch(JSON.stringify(view),/FCC PASS|전체 업무 완료|실측 완료/);
});

test('failed uncertain queued running and superseded are technical observations without a published measurement',()=>{
  for(const state of ['failed','uncertain','queued','running','superseded']){
    const payload=currentFixture();Object.assign(payload.records[0],{state,report:null});
    if(state==='queued')Object.assign(payload.records[0],{run_id:null,runtime_instance_id:null});
    const view=workflow(workflowIntake(),{payload,request_id:'REQ-UI-1'});
    assert.equal(step(view,'virtual').label,describeFixtureRecord(payload.records[0],2).state.label);
    assert.match(stepText(view,'measurement'),/게시된 측정 근거 미확인/);assert.match(stepText(view,'physical'),/실측 대조 미실행/);
  }
});

test('revision readiness stale and pending scopes keep stored evidence historical or unconfirmed',()=>{
  const payload=currentFixture(), options={payload,request_id:'REQ-UI-1'};
  assert.equal(workflow(workflowIntake(),options).context.fixture_scope,'current');
  for(const flag of [{stale:true},{pending:true}])assert.equal(workflow(workflowIntake(),{...options,...flag}).context.fixture_scope,'unconfirmed');
  payload.records[0].source_current=false;
  assert.equal(workflow(workflowIntake(),options).context.fixture_scope,'historical');
  assert.match(stepText(workflow(workflowIntake(),options),'virtual'),/준비 상태 변경/);
  payload.records[0].revision=1;assert.match(stepText(workflow(workflowIntake(),options),'virtual'),/이전 자료 버전 v1/);
  assert.equal(workflow(workflowIntake(),{...options,request_id:'absent'}).context.fixture_scope,'none');
});

test('workflow does not loosen existing exact API or join another intake and future fields',()=>{
  for(const change of [p=>p.intake_id='other',p=>p.current_revision=3,p=>p.records[0].case_id='C-future',p=>p.records[0].plan_id='P-future',p=>p.records[0].ai_model_called=true,p=>p.records[0].report.task_outcome='completed']){
    const payload=currentFixture();change(payload);assert.throws(()=>workflow(workflowIntake(),{payload,request_id:'REQ-UI-1'}),/invalid_fixture_runs|invalid_harness_result/);
  }
});

test('workflow classifies an analysis lease using only the supplied observation time',()=>{
  const intake=workflowIntake();Object.assign(intake,{status:'awaiting_analysis',analysis:null,jobs:[{revision:2,state:'running',lease_until:50}]});
  assert.equal(step(workflow(intake,{now:25}),'intake').label,'분석 중');
  assert.equal(step(workflow(intake,{now:100}),'intake').label,'임대 만료 · 확인 필요');
});
