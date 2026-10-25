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

const previewFields=['frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','crest_factor_db'];
function previewPacket(){
  const settings={frequency_hz:915000000,power_dbm:-4,bandwidth_hz:1000000,duty_cycle:1,modulation:'CW-synthetic',crest_factor_db:0};
  const units=['Hz','dBm','Hz','ratio','label','dB'];
  const citation={kind:'pdf_page',path:'synthetic-request.pdf',sha256:'a'.repeat(64),extraction_id:'b'.repeat(64),page_number:1,text_sha256:'c'.repeat(64),line_start:1,line_end:1,quote:'smartphone US synthetic check',role:'request'};
  return {schema_version:1,kind:'intake_conducted_plan_preview',intake_id:'I-1',revision:2,context_sha256:'d'.repeat(64),context_scope:'current_provided_context',selection_status:'matched',plan_input:{
    schema_version:1,kind:'intake_conducted_twin_plan_input',status:'ready_for_simulation',
    binding:{intake_id:'I-1',revision:2,analysis_context_id:'e'.repeat(64),context_sha256:'d'.repeat(64),analysis_sha256:'f'.repeat(64),plan_sha256:'a'.repeat(64)},
    intake:{facts:{product_type:{value:'smartphone',status:'explicit'},market:{value:'US',status:'explicit'},purpose:{value:'synthetic check',status:'explicit'}},source_facts:[{field:'product_type',value:'smartphone',status:'explicit',evidence:[citation]}],missing_fields:[],follow_up_missing_fields:[],questions:[]},
    plan:{schema_version:1,method_id:'conducted_synthetic',method_version:1,metric:'on',reference_plane:'source_output',source_settings:settings,
      basis_refs:Object.fromEntries(previewFields.map((key,i)=>[key,{kind:'developer_declared_synthetic',value:settings[key],unit:units[i],evidence:[]}]))},
    gaps:[],verification:{evidence:'validated_in_memory',current_version:'caller_snapshot_only',source_bytes:'not_reopened',regulatory:'not_assessed',measurement_prediction:'not_assessed',execution_authority:false}}};
}
function preview(overrides){
  assert.equal(typeof workflowAPI.parseConductedPlanPreview,'function','missing bounded preview parser');
  const value=previewPacket();Object.assign(value.plan_input.plan,{numeric_limit_dbm:null,uncertainty_db:null,assessment:'not_assessed'});
  if(overrides)overrides(value);
  return workflowAPI.parseConductedPlanPreview(JSON.stringify(value),{intake_id:'I-1',revision:2});
}
test('conducted preview exact wrapper keeps current provided context separate from original prompt and execution authority',()=>{
  const value=preview();assert.equal(value.context_scope,'current_provided_context');assert.equal(value.plan_input.status,'ready_for_simulation');
  assert.equal(value.plan_input.verification.execution_authority,false);assert.equal(value.plan_input.plan.numeric_limit_dbm,null);
  assert.equal(value.plan_input.plan.source_settings.crest_factor_db,0);assert.equal(value.plan_input.plan.assessment,'not_assessed');
});
test('conducted preview preserves blocked null settings and original rejected provided value without using it as a plan value',()=>{
  const value=preview(v=>{const p=v.plan_input;p.status='blocked';p.verification.evidence='not_validated';p.plan.source_settings.power_dbm=null;p.plan.basis_refs.power_dbm=null;p.gaps=[{code:'missing_or_invalid_basis',field:'basis.power_dbm',provided:0,blocking:true}];});
  assert.equal(value.plan_input.plan.source_settings.power_dbm,null);assert.equal(value.plan_input.gaps[0].provided,0);
  assert.equal(typeof workflowAPI.conductedPreviewValue,'function');assert.equal(workflowAPI.conductedPreviewValue(null),'미제공(null)');assert.equal(workflowAPI.conductedPreviewValue(0),'0');
});
test('conducted preview supports only the published nested fact question citation and basis variants',()=>{
  for(const shape of ['schema1','text_line','pdf_page']){
    const value=preview(v=>{const c=v.plan_input.intake.source_facts[0].evidence[0];if(shape!=='pdf_page'){delete c.extraction_id;delete c.page_number;delete c.text_sha256;if(shape==='schema1')delete c.kind;else c.kind='text_line';}
      const p=v.plan_input;p.status='blocked';p.verification.evidence='not_validated';p.intake.questions=[{key:'conflict_market',field:'market',values:['EU','US'],message:'충돌'},{key:'missing_firmware',field:'firmware',message:'누락'},{key:'product_identity',message:'대상 미확인'},{key:'unread_documents',paths:['synthetic-request.pdf'],message:'미독해'}];p.gaps=[{code:'product_identity',field:'intake.identity',provided:null,blocking:true}];});
    assert.equal(value.plan_input.intake.questions.length,4);
  }
});
test('conducted preview rejects another intake revision extra schema fields and promoted verification',()=>{
  preview();
  for(const change of [v=>v.intake_id='other',v=>v.revision=3,v=>v.plan_input.binding.context_sha256='0'.repeat(64),v=>v.context_scope='original_prompt',v=>v.plan_input.verification.execution_authority=true,v=>v.plan_input.plan.assessment='pass',v=>v.plan_input.plan.numeric_limit_dbm=30,v=>v.plan_input.plan.source_settings.frequency_hz=true,v=>v.plan_input.extra='future',v=>v.schema_version=true])assert.throws(()=>preview(change));
});
test('conducted preview refuses unknown gap question and citation keys and ready with a blocking gap',()=>{
  preview();
  for(const change of [v=>v.plan_input.gaps=[{code:'future',field:'input',provided:null,blocking:true}],v=>v.plan_input.gaps=[{code:'missing_setting',field:'source_settings.power_dbm',provided:null,blocking:true}],v=>v.plan_input.intake.source_facts[0].evidence[0].url='https://invalid.example',v=>v.plan_input.intake.questions=[{key:'future',message:'future'}],v=>v.plan_input.plan.basis_refs.power_dbm.unit='W'])assert.throws(()=>preview(change));
});
test('conducted preview raw JSON bounds and duplicate fields fail before a new result can be published',()=>{
  preview();for(const raw of [' '.repeat(262145),'{}{}','{"schema_version":1,"schema_version":1}','{"n":NaN}'])assert.throws(()=>workflowAPI.parseConductedPlanPreview(raw,{intake_id:'I-1',revision:2}));
});
test('conducted preview does not round a large original rejected integer in gap evidence',()=>{
  preview();const packet=previewPacket();Object.assign(packet.plan_input.plan,{numeric_limit_dbm:null,uncertainty_db:null,assessment:'not_assessed'});packet.plan_input.status='blocked';packet.plan_input.verification.evidence='not_validated';packet.plan_input.gaps=[{code:'invalid_setting',field:'source_settings.power_dbm',provided:'RAW_UNSAFE',blocking:true}];
  const raw=JSON.stringify(packet).replace('"RAW_UNSAFE"','9007199254740993');const value=workflowAPI.parseConductedPlanPreview(raw,{intake_id:'I-1',revision:2});
  assert.equal(workflowAPI.conductedPreviewValue(value.plan_input.gaps[0].provided),'9007199254740993');
});
test('conducted preview rejects a gap field outside the published field paths',()=>{
  preview();assert.throws(()=>preview(v=>{v.plan_input.status='blocked';v.plan_input.verification.evidence='not_validated';v.plan_input.gaps=[{code:'missing_setting',field:'future_private_field',provided:null,blocking:true}];}));
});

function conductedResultPacket(){
  const plan=preview().plan_input,binding=structuredClone(plan.binding),report={schema_version:1,kind:'virtual_fleet_harness_result',run_id:'provided-run',runtime_instance_id:'provided-runtime',synthetic:true,hardware_verified:false,ai_model_called:false,policy:{kind:'fixture',id:'typed-provided'},termination:{reason:'policy_stop',policy_claim:'completed'},task_outcome:'not_assessed',cleanup:{status:'not_assessed',evidence_refs:[]},usage:{decisions:0,logical_requests:0,transport_retries:0,tick_delta:0,reserved_ticks:0,elapsed_ms:0},evidence:{measurement_refs:['provided-event'],operator_transcript_ref:'provided-journal'},unresolved_request_ids:[],assessment:{status:'not_assessed',verdict:null,evaluator_id:null,evidence_refs:[],summary_code:null}};
  const result={schema_version:1,kind:'conducted_twin_result',status:'recorded',binding:{plan_input:plan,run_report:report,plan_input_sha256:'a'.repeat(64),setup_sha256:'a'.repeat(64),journal_file_sha256:'a'.repeat(64),journal_head_sha256:'a'.repeat(64),report_sha256:'a'.repeat(64),topology_sha256:'a'.repeat(64),run_id:report.run_id,runtime_instance_id:report.runtime_instance_id,measurement_ref:'provided-event'},raw_measurement:{packet:{status:'ok',valid:true,value:-4,unit:'dBm',frequency_hz:915000000,power_dbm:-4,duty_cycle:1,crest_factor_db:0,acquisition_tick:0,acquisition_setup_revision:0,source_id:'sensor',extra:{zero:0}},event_id:'provided-event',sequence:1,device_id:'sensor',tick:0,setup_revision:0,quantity:{metric:'on',reference_plane:'sensor_input',loss_compensation_applied:false,loss_compensation_sign:1},reference_plane:'sensor_input'},setup_provenance:{records:[],topology:{devices:[],connections:[]},path:[]},calculation:{raw_power_w:{value:0.00039810717055349735,unit:'W'},raw_reference_plane:'sensor_input',correction_ledger:[],target_reference_plane:'source_output',corrected:{value:-4,unit:'dBm',power_w:0.00039810717055349735},conformity:{status:'not_assessed',verdict:null,numeric_limit_dbm:null,uncertainty_db:null}},gaps:[],failure:null,verification:{synthetic:true,hardware_verified:false,physical_verified:false,source_bytes:'not_reopened',method_approval:'not_assessed',trust_scope:'provided_host_snapshots_and_hash_consistency',execution_authority:false}};
  return {schema_version:1,kind:'intake_conducted_result_view',intake_id:'I-1',revision:2,context_sha256:binding.context_sha256,source_kind:'provided_snapshot',expected_current_binding:binding,relation:{status:'matched',reasons:[],provided_revision:2},result};
}
function parseResult(packet=conductedResultPacket()){
  assert.equal(typeof workflowAPI.parseConductedResultView,'function','missing strict provided result parser');
  return workflowAPI.parseConductedResultView(typeof packet==='string'?packet:JSON.stringify(packet),{intake_id:'I-1',revision:2});
}
test('result readonly preserves provided source zero null and actualAI absence without turning recorded into conformity',()=>{
  const value=parseResult();assert.equal(value.source_kind,'provided_snapshot');assert.equal(value.result.raw_measurement.tick,0);assert.equal(value.result.calculation.conformity.verdict,null);assert.equal(value.result.verification.execution_authority,false);assert.equal(Object.hasOwn(value.result.verification,'ai_model_called'),false);
});
test('result readonly keeps original invalid binding0/2/11 raw JSON gaps and partial calculation',()=>{
  for(const count of [0,2,11]){
    const packet=conductedResultPacket(),r=packet.result;r.status='invalid';r.failure={code:'measurement_invalid',field:'observation.sensor'};
    if(count===0)r.binding={};if(count===2)r.binding={plan_input:42,run_report:['original']};
    r.raw_measurement.packet={status:'bad',value:'-3e7',unit:null,extra:[false,0]};r.raw_measurement.quantity=[42];r.raw_measurement.tick='original';r.setup_provenance.records={bad:'original'};r.setup_provenance.topology=['original'];r.calculation.corrected=null;r.gaps=[null,42,{malformed:'original'}];packet.relation={status:'blocked',reasons:['result_plan_binding_unavailable'],provided_revision:2};
    assert.deepEqual(JSON.parse(workflowAPI.conductedPreviewValue(parseResult(packet).result)),JSON.parse(JSON.stringify(r)));
  }
});
test('result readonly accepts incomplete generated W while corrected is null and preserves malformed quantity declaration',()=>{
  const packet=conductedResultPacket(),r=packet.result;r.status='incomplete';r.binding={plan_input:r.binding.plan_input,run_report:null};r.failure=null;r.gaps=[{code:'correction_basis_missing',field:'quantity',provided:null,blocking:true}];r.calculation.corrected=null;r.raw_measurement.quantity=['original'];
  assert.equal(parseResult(packet).result.calculation.corrected,null);assert.ok(parseResult(packet).result.calculation.raw_power_w.value>0);
});
test('result readonly rejects future schema unknown failure authority promoted conformity and mismatched current binding',()=>{
  parseResult();for(const change of [v=>v.result.extra=1,v=>v.result.verification.execution_authority=true,v=>v.result.calculation.conformity.verdict='pass',v=>v.result.status='future',v=>v.expected_current_binding.context_sha256='f'.repeat(64),v=>{v.result.status='invalid';v.result.failure={code:'future',field:'input'};},v=>v.result.raw_measurement.packet.valid=1,v=>v.result.binding.run_report={},v=>{v.result.status='incomplete';v.result.failure={code:'setup_partial',field:'plan_input.plan.future'};},v=>v.result.gaps=[{code:'metric_mismatch',field:'future_private_path',provided:null,blocking:true}],v=>v.result.gaps=[{code:'missing_setting',field:'future_private_path',provided:null,blocking:false}]]){const packet=conductedResultPacket();change(packet);assert.throws(()=>parseResult(packet));}
});
test('result readonly requires explicit blocked reason when expected-current binding is absent',()=>{
  const packet=conductedResultPacket();packet.expected_current_binding=null;assert.throws(()=>parseResult(packet));packet.relation={status:'blocked',reasons:['expected_current_binding_missing'],provided_revision:2};assert.equal(parseResult(packet).relation.status,'blocked');
});
test('result readonly rejects duplicate raw fields nonfinite and output bounds while preserving unsafe original integers',()=>{
  parseResult();const complete=JSON.stringify(conductedResultPacket());assert.throws(()=>parseResult(complete.replace('"schema_version":1','"schema_version":1,"schema_version":1')));for(const raw of [' '.repeat(1048577),'{}{}','{"schema_version":1,"schema_version":1}','{"n":NaN}'])assert.throws(()=>parseResult(raw));
  const packet=conductedResultPacket();packet.result.status='invalid';packet.result.failure={code:'measurement_invalid',field:'observation.sensor'};packet.result.gaps=['RAW_INTEGER'];const raw=JSON.stringify(packet).replace('"RAW_INTEGER"','9007199254740993');assert.equal(workflowAPI.conductedPreviewValue(parseResult(raw).result.gaps[0]),'9007199254740993');
});

function gapQueueInputs(){
  const packet=conductedResultPacket(),plan=preview(),context={intake_id:'I-1',revision:2,generation:7};
  plan.plan_input.intake.questions=[{key:'missing_firmware',field:'firmware',message:'firmware 확인'}];
  plan.plan_input.gaps=[{code:'follow_up_missing_field',field:'intake.firmware',provided:null,blocking:false}];
  const intake={intake_id:'I-1',revision:2,analysis:{questions:[{key:'missing_customer',field:'customer',message:'동일한 원 문구',refs:null},{key:'conflict_market',field:'market',values:['US','EU'],message:'동일한 원 문구',refs:['ref-B','ref-A']}]}};
  packet.result.status='incomplete';packet.result.calculation.corrected=null;packet.result.failure={code:'measurement_missing',field:'measurement_ref'};packet.result.gaps=[{code:'measurement_missing',field:'measurement_ref',provided:null,blocking:true}];
  return {intake,options:{generation:7,intakeStale:false,plan:{context:{...context},value:plan,pending:false,parentPending:false,stale:false,errorCode:null},result:{context:{...context},value:packet,pending:false,parentPending:false,stale:false,errorCode:null}}};
}
function gapQueue(input=gapQueueInputs()){
  assert.equal(typeof workflowAPI.describeIntakeGapQueue,'function','missing readonly source-separated gap queue');
  return workflowAPI.describeIntakeGapQueue(input.intake,input.options);
}
const queueGroup=(view,id)=>view.groups.find(group=>group.source===id);
const rawRows=group=>group.items.map(item=>workflowAPI.conductedPreviewValue(item.raw));
test('gap queue preserves source order duplicate text original refs and null without merging conditions',()=>{
  const input=gapQueueInputs(),view=gapQueue(input);
  assert.deepEqual(view.groups.map(g=>g.source),['intake_questions','plan_questions','plan_gaps','result_gaps']);
  assert.deepEqual(queueGroup(view,'intake_questions').items.map(x=>x.index),[0,1]);
  assert.deepEqual(rawRows(queueGroup(view,'intake_questions')),input.intake.analysis.questions.map(workflowAPI.conductedPreviewValue));
  assert.equal(queueGroup(view,'intake_questions').items[0].raw.refs,null);
  assert.deepEqual(queueGroup(view,'intake_questions').items[1].raw.refs,['ref-B','ref-A']);
  assert.deepEqual(rawRows(queueGroup(view,'plan_gaps')),input.options.plan.value.plan_input.gaps.map(workflowAPI.conductedPreviewValue));
  assert.equal(queueGroup(view,'intake_questions').items[0].category,'facts_required');assert.equal(queueGroup(view,'plan_questions').items[0].category,'facts_required');
  queueGroup(view,'intake_questions').items[1].raw.refs.push('mutated');assert.deepEqual(input.intake.analysis.questions[1].refs,['ref-B','ref-A']);assert.equal(view.execution_authority,false);
});
test('gap queue never disguises native auth registration or source settings as product fact questions',()=>{
  const input=gapQueueInputs();input.intake.analysis.questions=[{key:'missing_native_auth',field:'native_auth',message:'등록/auth 설정 필요',refs:null}];
  input.options.plan.value.plan_input.gaps=[{code:'missing_setting',field:'source_settings.power_dbm',provided:0,blocking:true},{code:'missing_or_invalid_basis',field:'basis.power_dbm',provided:null,blocking:true}];
  const view=gapQueue(input);assert.equal(queueGroup(view,'intake_questions').items[0].category,'uninterpreted');
  assert.ok(queueGroup(view,'plan_gaps').items.every(x=>x.category==='conditions_required'));
  assert.equal(queueGroup(view,'plan_gaps').items[0].raw.provided,0);assert.equal(queueGroup(view,'plan_gaps').items[1].raw.provided,null);
});
test('gap queue blocks stale pending generation and binding mismatches without dropping same-intake originals',()=>{
  for(const fault of ['stale','pending','generation','binding']){
    const input=gapQueueInputs(),obs=input.options.plan;
    if(fault==='stale')obs.stale=true;if(fault==='pending')obs.pending=true;if(fault==='generation')obs.context.generation=6;if(fault==='binding')obs.value.plan_input.binding.context_sha256='f'.repeat(64);
    const view=gapQueue(input);assert.equal(queueGroup(view,'plan_questions').state,'blocked');assert.ok(queueGroup(view,'plan_questions').items.every(x=>x.category==='blocked'));assert.deepEqual(rawRows(queueGroup(view,'plan_questions')),obs.value.plan_input.intake.questions.map(workflowAPI.conductedPreviewValue));assert.equal(queueGroup(view,'result_gaps').state,'blocked');
  }
});
test('gap queue blocks different current plan condition hashes and preserves provided gaps as a separate source',()=>{
  const input=gapQueueInputs();input.options.result.value.expected_current_binding.plan_sha256='f'.repeat(64);input.options.result.value.result.binding.plan_input.binding.plan_sha256='f'.repeat(64);
  const view=gapQueue(input),group=queueGroup(view,'result_gaps');assert.equal(group.state,'blocked');assert.ok(group.reasons.includes('plan_condition_mismatch'));assert.equal(group.items[0].category,'blocked');assert.deepEqual(rawRows(group),input.options.result.value.result.gaps.map(workflowAPI.conductedPreviewValue));assert.equal(queueGroup(view,'plan_questions').state,'current');
});
test('gap queue excludes other intake data and labels old revision and provided-binding conflicts blocked',()=>{
  const other=gapQueueInputs();other.options.plan.context.intake_id='I-other';other.options.plan.value.intake_id='I-other';assert.equal(queueGroup(gapQueue(other),'plan_questions').items.length,0);
  const old=gapQueueInputs();old.options.plan.context.revision=1;old.options.plan.value.revision=1;const oldGroup=queueGroup(gapQueue(old),'plan_questions');assert.equal(oldGroup.state,'blocked');assert.equal(oldGroup.observed_revision,1);assert.equal(oldGroup.items[0].category,'blocked');
  const provided=gapQueueInputs();provided.options.result.value.relation={status:'blocked',reasons:['provided_revision_changed'],provided_revision:1};const group=queueGroup(gapQueue(provided),'result_gaps');assert.equal(group.state,'blocked');assert.ok(group.reasons.includes('provided_revision_changed'));assert.equal(group.items[0].category,'blocked');
});
test('gap queue retains malformed invalid result JSON and large original integers without current-question promotion',()=>{
  const input=gapQueueInputs(),r=input.options.result.value.result;r.status='invalid';r.failure={code:'measurement_invalid',field:'observation.sensor'};r.gaps=[null,42,9007199254740993n,{native_auth:'unknown',refs:null},{code:'missing_intake_field',field:'intake.market',provided:null,blocking:true}];
  const view=gapQueue(input),group=queueGroup(view,'result_gaps');assert.equal(group.state,'blocked');assert.ok(group.items.every(x=>x.category==='blocked'));assert.deepEqual(rawRows(group),r.gaps.map(workflowAPI.conductedPreviewValue));assert.equal(workflowAPI.conductedPreviewValue(group.items[2].raw),'9007199254740993');
});
test('gap queue distinguishes unavailable unsupported and not-run headers from an empty fact list',()=>{
  const input=gapQueueInputs();input.intake.analysis=null;input.options.plan={value:null,errorCode:'intake_conducted_preview_v2_pdf_required'};input.options.result={value:null,errorCode:'intake_conducted_result_missing'};
  const view=gapQueue(input);assert.equal(queueGroup(view,'intake_questions').state,'not_run');assert.equal(queueGroup(view,'plan_gaps').category,'unsupported');assert.equal(queueGroup(view,'result_gaps').category,'not_run');assert.equal(view.summary.current_facts,0);assert.equal(Object.hasOwn(view,'approved'),false);
});
test('gap queue marks the entire last parent observation blocked after failed refresh while preserving originals',()=>{
  const input=gapQueueInputs();input.options.intakeStale=true;const view=gapQueue(input);assert.ok(view.groups.every(g=>g.state==='blocked'));assert.ok(view.groups.flatMap(g=>g.items).every(x=>x.category==='blocked'));assert.equal(view.summary.current_facts,0);assert.deepEqual(rawRows(queueGroup(view,'intake_questions')),input.intake.analysis.questions.map(workflowAPI.conductedPreviewValue));
});

test('gap queue separates real fact questions from extraction evidence gaps without declaring RF reentry mandatory',()=>{
  const input=gapQueueInputs(),codes=['source_statement_unsupported','source_quote_mismatch','source_condition_unbound','source_fact_missing'];
  const diagnostics=codes.map((code,index)=>({key:code,code,field:'source_settings.frequency_hz',message:'해석 연결 상태 '+code,provided:null,refs:['condition-'+index]}));
  diagnostics.push({...diagnostics[2],refs:['different-condition']});
  input.intake.analysis.questions=[{key:'missing_model',field:'model',message:'제품 모델 사실 확인',refs:null},...diagnostics];
  input.options.result.value.result.status='invalid';input.options.result.value.result.failure={code:'evidence_context_missing',field:'input'};
  input.options.result.value.result.gaps=codes.map(code=>({code,field:'source_settings.frequency_hz',provided:null,blocking:true}));
  const view=gapQueue(input),questions=queueGroup(view,'intake_questions').items,result=queueGroup(view,'result_gaps').items;
  assert.equal(questions[0].category,'facts_required');assert.ok(questions.slice(1).every(row=>row.category==='evidence_review'));
  assert.equal(questions.length,6);assert.deepEqual(questions[3].raw.refs,['condition-2']);assert.deepEqual(questions[5].raw.refs,['different-condition']);
  assert.ok(result.every(row=>row.category==='blocked'&&row.classification==='evidence_review'));
  assert.ok([...questions.slice(1),...result].every(row=>!row.label.includes('필수')&&row.note.includes('원자료 부재')));
  assert.deepEqual(rawRows(queueGroup(view,'intake_questions')),input.intake.analysis.questions.map(workflowAPI.conductedPreviewValue));
});
test('gap queue retains an unfamiliar fact namespace as uninterpreted instead of inventing a system failure',()=>{
  const input=gapQueueInputs();input.options.plan.value.plan_input.gaps=[{code:'missing_intake_field',field:'intake.native_auth',provided:null,blocking:true}];
  const row=queueGroup(gapQueue(input),'plan_gaps').items[0];assert.equal(row.category,'uninterpreted');assert.equal(row.state,'blocked');assert.equal(row.raw.field,'intake.native_auth');
});
