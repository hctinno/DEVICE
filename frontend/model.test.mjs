import test from 'node:test';
import assert from 'node:assert/strict';
import {describeState, factSources, filterIntakes, noticeContext,validateSnapshot} from './model.mjs';
import wire from './intake_references/browser_check.cjs';
import * as appModel from './model.mjs';
import {parseIntakeReferenceCurrentJson} from './intake_references/model.mjs';

test('DOCX tagged original6 preserves literal native observations and full current-file binding',()=>{
 const value=wire.createDocxObservation(),b=value.reference.binding;
 assert.deepEqual(parseIntakeReferenceCurrentJson(JSON.stringify(value),b.intake_id,'docx_retained'),value);
 const record={source_id:b.source_id,intake_id:b.intake_id,revision:b.revision,
  history:[{revision:1,fingerprint:b.revision_fingerprint}],files:[{...b.document}],analysis:null};
 assert.equal(appModel.docxReferenceMatchesRecord(value,record),true);
 for(const edit of [r=>r.source_id='OTHER',r=>r.revision=2,r=>r.history[0].fingerprint='e'.repeat(64),r=>r.files[0].bytes++]){
  const other=structuredClone(record);edit(other);assert.equal(appModel.docxReferenceMatchesRecord(value,other),false);
 }
});
test('DOCX literal unknown declarations stay separate from unmappable structures and unsafe wire numbers',()=>{
 const value=wire.createDocxObservation(),id=value.reference.binding.intake_id;
 value.reference.result.status='unknown native state';value.reference.result.reader.version='<script>literal</script>';
 value.reference.result.scope.profile='future declaration';assert.deepEqual(parseIntakeReferenceCurrentJson(JSON.stringify(value),id,'docx_retained'),value);
 for(const edit of [v=>v.reference.result.blocks[0].kind='new structure',v=>v.reference.result.scope.page_numbers=1,
  v=>v.reference.result.complete=1,v=>v.reference.result.reader.name='\ud800',v=>v.reference.binding.revision=true]){
  const bad=structuredClone(value);edit(bad);assert.throws(()=>parseIntakeReferenceCurrentJson(JSON.stringify(bad),id,'docx_retained'));
 }
 assert.throws(()=>parseIntakeReferenceCurrentJson(JSON.stringify(value).replace('"artifact_bytes":1024','"artifact_bytes":9007199254740993'),id,'docx_retained'));
 assert.throws(()=>parseIntakeReferenceCurrentJson(JSON.stringify(value).replace('"artifact_bytes":1024','"artifact_bytes":1e3'),id,'docx_retained'));
 assert.throws(()=>parseIntakeReferenceCurrentJson(JSON.stringify(value),id));
});
test('DOCX missing fingerprints cannot match missing metadata by undefined equality',()=>{
 const value=wire.createDocxObservation(),b=value.reference.binding;
 const record={source_id:b.source_id,intake_id:b.intake_id,revision:b.revision,history:[{revision:1}],files:[{...b.document}]};
 delete b.revision_fingerprint;assert.equal(appModel.docxReferenceMatchesRecord(value,record),false);
});
test('DOCX byte depth value-node structure and issue boundaries reject the whole observation at plus one',()=>{
 const make=wire.createDocxObservation,parse=v=>parseIntakeReferenceCurrentJson(JSON.stringify(v),'DOCX-WIRE','docx_retained');
 let v=make();v.reference.result.statistics.padding='';let size=new TextEncoder().encode(JSON.stringify(v)).length;
 v.reference.result.statistics.padding='x'.repeat(2097152-size);parse(v);v.reference.result.statistics.padding+='x';assert.throws(()=>parse(v));
 for(const count of [60,61]){v=make();let chain=null;for(let i=0;i<count;i++)chain=[chain];v.reference.result.statistics.chain=chain;if(count===60)parse(v);else assert.throws(()=>parse(v));}
 v=make();const nodes=x=>1+(x&&typeof x==='object'?Object.values(x).reduce((sum,child)=>sum+nodes(child),0):0);
 v.reference.result.statistics.values=[];v.reference.result.statistics.values=Array(200000-nodes(v)).fill(null);parse(v);
 v.reference.result.statistics.values.push(null);assert.throws(()=>parse(v));
 v=make();const locator=v.reference.result.blocks[0].locator;v.reference.result.blocks=Array.from({length:2000},()=>({kind:'unsupported',locator:structuredClone(locator),reason:'declared mutation'}));parse(v);
 v.reference.result.blocks.push(structuredClone(v.reference.result.blocks[0]));assert.throws(()=>parse(v));
 v=make();v.reference.result.issues=Array.from({length:128},()=>({code:'stored issue',locator:null,occurrences:1}));parse(v);
 v.reference.result.issues.push({...v.reference.result.issues[0]});assert.throws(()=>parse(v));
});

test('queue, running, failure, deferral and unsupported states stay distinguishable', () => {
  const base = {status: 'awaiting_analysis', revision: 1, jobs: [{revision: 1, state: 'queued'}]};
  assert.equal(describeState(base).code, 'awaiting_analysis');
  assert.equal(describeState({...base, jobs: [{revision: 1, state: 'running'}]}).code, 'analyzing');
  assert.equal(describeState({...base, jobs: [{revision: 0, state: 'running'}]}).code, 'awaiting_analysis');
  assert.equal(describeState({...base, status: 'analysis_failed'}).code, 'analysis_failed');
  assert.equal(describeState({...base, deferred: true}).code, 'deferred');
  assert.equal(describeState({...base, status: 'new_state'}).code, 'unsupported');
  assert.equal(describeState({...base, jobs: [{revision: 1, state: 'new_job_state'}]}).code, 'unsupported');
});

function intentSnapshot(){
 const record={intake_id:'VIEW-1',revision:1,source_id:'SYN-VIEW',bundle:'선언 wire',status:'analyzed',
  synthetic:true,delegated:false,deferred:false,measurement_support:'unverified',analysis:{facts:{},questions:[],next_action:'needs_information'},files:[],history:[],jobs:[]};
 return {schema_version:1,generated_at:'2026-10-25T00:00:00+09:00',intakes:[record],notifications:[],
  intake_test_intent_reviews:[wire.createIntentReview(record)]};
}
const invalidIntent=payload=>assert.throws(()=>validateSnapshot(payload),error=>error.message==='invalid_snapshot');
test('supplied intent optional metadata preserves original missing/null/false values',()=>{
 const payload=intentSnapshot();assert.equal(validateSnapshot(payload),payload);
 assert.equal(payload.intake_test_intent_reviews[0].fields.rule.status,'missing');
 assert.equal(payload.intake_test_intent_reviews[0].input_binding.analysis_context_id,null);
 delete payload.intake_test_intent_reviews;assert.equal(validateSnapshot(payload),payload);
});
test('intent exact keys statuses and every false authority flag reject invalid snapshots',()=>{
 const edits=[v=>v.extra=1,v=>delete v.fields,v=>v.schema_version=true,v=>v.status='approved',v=>v.fields.rule.status='selected',
  v=>v.verification.execution_authorized=true,v=>v.verification.query_release_authorized=true,
  v=>delete v.verification.model_quality_verified,v=>v.verification.basis_literals_checked=1,
  v=>v.limits.max_output_bytes=2097153];
 for(const edit of edits){const payload=intentSnapshot();edit(payload.intake_test_intent_reviews[0]);invalidIntent(payload);}
 for(const value of [null,{},[...Array(2)].map(()=>intentSnapshot().intake_test_intent_reviews[0])]){
  const payload=intentSnapshot();payload.intake_test_intent_reviews=value;invalidIntent(payload);
 }
});
test('intent binding indices SHA and safe integer constraints are checked without coercion',()=>{
 for(const edit of [v=>v.input_binding.revision=9007199254740992,v=>v.input_binding.revision=true,
  v=>v.input_binding.intake_id='UNRELATED',v=>v.input_binding.provided_projection_sha256='BAD',
  v=>v.input_binding.revision=2]){
  const payload=intentSnapshot();edit(payload.intake_test_intent_reviews[0]);invalidIntent(payload);
 }
});
test('intent candidates keep literal/origin/locator and all four parent field states',()=>{
 for(const status of ['missing','proposed','conflicting','literal_linked']){
  const payload=intentSnapshot(),value=payload.intake_test_intent_reviews[0];value.fields.rule.status=status;
  value.fields.rule.candidates=[{literal:'<script>literal</script>',origin:'model_proposed',literal_linked:false,
   intake_refs:[{fact_index:0,evidence_index:0}],basis_refs:[{document_id:'SYN-BASIS',page_number:1,text_sha256:'a'.repeat(64),line_start:1,line_end:2}],
   period_checks:[{document_id:'SYN-BASIS',status:'unconfirmed'}],reason_codes:['basis_missing']}];
  assert.equal(validateSnapshot(payload),payload);assert.equal(value.fields.rule.candidates[0].literal,'<script>literal</script>');
  value.fields.rule.candidates[0].basis_refs[0].line_end=0;invalidIntent(payload);
 }
});
test('intent parent field budgets references and questions are not truncated into success',()=>{
 for(const edit of [v=>v.fields.rule.candidates=Array(3).fill({}),v=>v.questions=Array(201).fill({}),
  v=>v.fields.rule.reason_codes=['unknown_parent_reason'],v=>v.questions=[{key:'missing_market',field:'market',message:'x'.repeat(2097152)}]]){
  const payload=intentSnapshot();edit(payload.intake_test_intent_reviews[0]);invalidIntent(payload);
 }
});

test('analysis completion or plan request is never a completed test', () => {
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'prepare_plan'}}).code, 'plan_pending');
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'propose_start'}}).code, 'propose_start');
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'needs_information'}}).code, 'needs_information');
  assert.equal(describeState({status: 'analyzed', analysis: null}).code, 'invalid');
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'future'}}).code, 'unsupported');
  for (const next_action of ['constructor', 'toString', '__proto__']) {
    assert.equal(describeState({status: 'analyzed', analysis: {next_action}}).code, 'unsupported');
  }
});

test('projected facts only cite matching candidates and never forge citations for user answers', () => {
  const citation = {path: 'request.txt', role: 'request', quote: '<script>alert(1)</script>'};
  const record = {analysis: {facts: {market: {value: 'EU', status: 'explicit'}}, submitted: {facts: [
    {field: 'market', value: 'EU', status: 'explicit', evidence: [citation]},
    {field: 'market', value: 'US', status: 'explicit', evidence: [{path: 'other.txt'}]},
    {field: 'market', value: 'EU', status: 'uncertain', evidence: [{path: 'uncertain.txt'}]},
  ]}}};
  assert.deepEqual(factSources(record, 'market'), [citation]);
  record.analysis.facts.market = {value: 'EU', status: 'user_confirmed', event_id: 'ANSWER-1'};
  assert.deepEqual(factSources(record, 'market'), []);
  assert.deepEqual(factSources({analysis: {facts: {model: {value: 'X', status: 'explicit'}}}}, 'model'), []);
});

test('market and purpose only cite explicit candidates entirely from request sources', () => {
  for (const field of ['market', 'purpose']) {
    const request = {path: 'request.txt', role: 'request'};
    const record = {analysis: {facts: {[field]: {value: 'US', status: 'explicit'}}, submitted: {facts: [
      {field, value: ' US ', status: 'explicit', evidence: [request]},
      {field, value: 'US', status: 'explicit', evidence: [{path: 'reference.txt', role: 'reference'}]},
      {field, value: 'US', status: 'inferred', evidence: [{path: 'guess.txt', role: 'request'}]},
      {field, value: 'US', status: 'explicit', evidence: [request, {path: 'mixed.txt', role: 'reference'}]},
    ]}}};
    assert.deepEqual(factSources(record, field), [request]);
    assert.equal(record.analysis.submitted.facts.length, 4);
  }
});

test('general facts keep explicit and inferred sources regardless of source role', () => {
  const reference = {path: 'reference.txt', role: 'reference'};
  const inference = {path: 'guess.txt', role: 'request'};
  const record = {analysis: {facts: {manufacturer: {value: 'Maker', status: 'explicit'}}, submitted: {facts: [
    {field: 'manufacturer', value: 'Maker', status: 'explicit', evidence: [reference]},
    {field: 'manufacturer', value: 'Maker', status: 'inferred', evidence: [inference]},
  ]}}};
  assert.deepEqual(factSources(record, 'manufacturer'), [reference, inference]);
});

test('Korean search combines with filters without hiding unsupported or failed work', () => {
  const records = [
    {bundle: '새 의뢰', source_id: 'INBOX', status: 'awaiting_analysis'},
    {bundle: '보류 의뢰', status: 'analyzed', deferred: true},
    {bundle: '실패 의뢰', status: 'analysis_failed'},
    {bundle: '알 수 없음', status: 'future'},
  ];
  assert.equal(filterIntakes(records, {query: '의뢰'}).length, 3);
  assert.equal(filterIntakes(records, {query: 'INBOX', filter: 'waiting'}).length, 1);
  assert.equal(filterIntakes(records, {filter: 'attention'}).length, 2);
  assert.equal(filterIntakes(records, {filter: 'deferred'}).length, 1);
  assert.equal(filterIntakes(records, {filter: 'failed'}).length, 1);
});

test('notifications remain creation-time records even on the same revision', () => {
  assert.equal(noticeContext({revision: 1}, {revision: 2}).code, 'previous_revision');
  assert.equal(noticeContext({revision: 2}, {revision: 2}).code, 'same_revision');
  assert.equal(noticeContext({revision: 3}, {revision: 2}).code, 'unknown_revision');
});

test('an expired lease is not presented as a currently running worker', () => {
  const record = {status: 'awaiting_analysis', revision: 1, jobs: [{revision: 1, state: 'running', lease_until: 100}]};
  assert.equal(describeState(record, 99).code, 'analyzing');
  assert.equal(describeState(record, 100).code, 'lease_expired');
  assert.equal(describeState(record, 101).code, 'lease_expired');
});
