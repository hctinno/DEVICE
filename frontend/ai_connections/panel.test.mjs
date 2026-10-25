import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// The production export stays factory-only. Pure internals are visible only in this test VM.
const file=new URL('./panel.mjs',import.meta.url);
let api=null;
if(fs.existsSync(file)){
  const context=vm.createContext({TextEncoder,TextDecoder,URL,setTimeout,clearTimeout});
  vm.runInContext(fs.readFileSync(file,'utf8').replace('export function createAIConnectionPanel','function createAIConnectionPanel')+
    '\nglobalThis.testAPI={parseDTO,requestFor,createAIConnectionPanel,admitStart:typeof admitStart==="function"?admitStart:null,scenarioInfo:typeof scenarioInfo==="function"?scenarioInfo:null};',context);
  api=context.testAPI;
}
const requireAPI=()=>assert.ok(api,'assigned AI connection panel module is absent');
const models=['gemini-4-argon','gemini-3.8-flash'];
const profile=()=>({schema_version:1,profile_id:'vertex-trial',provider:'vertex_ai',project_id:'project-a6310591-f8cc-487c-9e3',location:'global',quota_project_id:'project-a6310591-f8cc-487c-9e3',auth_profile_id:'vertex-trial',selected_model:models[1],models:Object.fromEntries(models.map(m=>[m,{thinking_level:'MEDIUM',max_output_tokens:512,timeout_seconds:60.0}])),revision:1});
const state=()=>({schema_version:1,kind:'ai_connection_state',profile:profile(),catalog:{locations:['global','us','eu'],model_ids:models,thinking_levels:['LOW','MEDIUM','HIGH'],defaults:{thinking_level:'MEDIUM',max_output_tokens:512,timeout_seconds:60},ranges:{max_output_tokens:[64,8192],timeout_seconds:[1,120]}},capabilities:['read_profile','edit_profile','run_registered_synthetic','cancel_own'],auth:{state:'access_unknown',credential_file_ready:true,checked_at:1},trial:{state:'confirmed',checked_at:1},budget:{limit_calls:6,reserved_calls:0,remaining_calls:6,limit_output_tokens:3072,reserved_output_tokens:0,wall_budget_seconds:300},gate:{run_allowed:true,reasons:[]},scenarios:[{scenario_id:'DGM-AI-CONNECTION-001',label:'<literal>',input_sha256:'a'.repeat(64),schema_sha256:'b'.repeat(64),evaluator_id:'connection-json-v1'}],active_run_id:null,recent_runs:[]});
const decode=(value,kind='state')=>api.parseDTO(JSON.stringify(value),kind);
const run=()=>{
  const p=profile();
  const setting={schema_version:1,kind:'ai_run_settings',profile_id:p.profile_id,profile_revision:1,provider:p.provider,service:'aiplatform.googleapis.com',project_id:p.project_id,location:p.location,quota_project_id:p.quota_project_id,auth_profile_id:p.auth_profile_id,
    model_id:models[1],thinking_level:'MEDIUM',max_output_tokens:512,timeout_seconds:60.0,profile_sha256:'d'.repeat(64),settings_sha256:'e'.repeat(64)};
  return {schema_version:1,kind:'ai_connection_run',run_id:'c'.repeat(64),profile_revision:1,scenario_id:'DGM-AI-CONNECTION-001',scenario_sha256:'a'.repeat(64),input_kind:'registered_synthetic',execution_mode:'mock',state:'finished',matrix:false,created_at:1,finished_at:2,cancel_requested:false,attempts_used:1,error_code:null,
    cells:Array.from({length:6},(_,i)=>({model_id:models[Math.floor(i/3)],thinking_level:['LOW','MEDIUM','HIGH'][i%3],settings:i===4?setting:null,state:i===4?'success':'not_run',reason_code:i===4?'connection_verified':'not_selected',attempted:i===4,http_status:i===4?200:null,finish_reason:i===4?'STOP':null,reported_model_version:null,response_id:null,response_complete:i===4?true:null,strict_decode:i===4?'pass':'not_run',quality:'not_run',usage:null,cost:null,latency_ms:null,error_code:null}))};
};

test('typed state permits first test with access_unknown and ready host gate',()=>{
  requireAPI();const value=decode(state());assert.equal(value.gate.run_allowed,true);assert.equal(value.auth.state,'access_unknown');
});
test('no JavaScript canonical hash recalculation is required for Python60.0',()=>{
  requireAPI();const x=state();x.profile.models[models[0]].timeout_seconds=60.0;assert.equal(decode(x).profile.models[models[0]].timeout_seconds,60);
});
test('profile revision zero cannot be sent as an executable request',()=>{
  requireAPI();const p=profile();p.revision=0;assert.throws(()=>api.requestFor(p,'DGM-AI-CONNECTION-001',models[1],{},false));
});
test('selected override is detached and retains finite fractional timeout',()=>{
  requireAPI();const p=profile(),override={thinking_level:'HIGH',max_output_tokens:128,timeout_seconds:1.5};
  const value=api.requestFor(p,'DGM-AI-CONNECTION-001',models[0],override,false);assert.equal(value.overrides.timeout_seconds,1.5);override.timeout_seconds=2;assert.equal(value.overrides.timeout_seconds,1.5);assert.equal(p.models[models[0]].max_output_tokens,512);
});
test('matrix permits flat output/timeout overrides and explicitly rejects thinking',()=>{
  requireAPI();assert.equal(api.requestFor(profile(),'DGM-AI-CONNECTION-001',null,{max_output_tokens:256},true).model_id,null);
  assert.throws(()=>api.requestFor(profile(),'DGM-AI-CONNECTION-001',null,{thinking_level:'HIGH'},true));
});
test('unsupported levels, bool numbers, authority fields and nonfinite settings are refused',()=>{
  requireAPI();for(const bad of [{thinking_level:'MINIMAL'},{thinking_level:'OFF'},{timeout_seconds:true},{timeout_seconds:Infinity},{max_output_tokens:512.5},{gate:true}])assert.throws(()=>api.requestFor(profile(),'DGM-AI-CONNECTION-001',models[0],bad,false));
});
test('strict parser rejects duplicate keys, unsafe integer and malformed Unicode',()=>{
  requireAPI();for(const raw of ['{"kind":"a","kind":"b"}','{"x":9007199254740993}','{"x":"\\ud800"}'])assert.throws(()=>api.parseDTO(raw,'state'));
});
test('unknown DTO keys and false authority are not accepted as a current state',()=>{
  requireAPI();for(const change of [x=>x.credential_path='private',x=>x.trial.amount=1,x=>x.capabilities.push('run_arbitrary'),x=>x.auth.state='file_verified']){
    const value=state();change(value);assert.throws(()=>decode(value));
  }
});
test('unknown usage and cost remain null in the typed contract',()=>{
  requireAPI();const x=state();x.budget.reserved_calls=null;x.budget.remaining_calls=null;x.gate={run_allowed:false,reasons:['budget_unavailable']};assert.equal(decode(x).budget.remaining_calls,null);
});
test('unconfirmed trial cannot accompany an allowed gate',()=>{
  requireAPI();const x=state();x.trial.state='unknown';assert.throws(()=>decode(x));
});
test('factory rejects non-DOM roots without issuing requests',()=>{
  requireAPI();assert.throws(()=>api.createAIConnectionPanel(null));assert.throws(()=>api.createAIConnectionPanel({}));
});
test('usage exact6 preserves signed64 counts as decimal strings and missing as null',()=>{
  requireAPI();const v=run();v.cells[4].usage={prompt_token_count:'9223372036854775807',candidates_token_count:null,total_token_count:null,thoughts_token_count:null,cached_content_token_count:null,tool_use_prompt_token_count:null};
  assert.equal(decode(v,'run').cells[4].usage.prompt_token_count,'9223372036854775807');
  v.cells[4].usage.prompt_token_count=9007199254740992;assert.throws(()=>decode(v,'run'));
});
test('run metadata cannot substitute another model/level or leak private artifact fields',()=>{
  requireAPI();const v=run();v.cells[4].settings.model_id=models[0];assert.throws(()=>decode(v,'run'));v.cells[4].settings.model_id=models[1];v.cells[4].artifacts={};assert.throws(()=>decode(v,'run'));
});
test('initial result settings must match the captured request without recomputing hashes',()=>{
  requireAPI();assert.equal(typeof api.admitStart,'function');const v=run(),p=profile(),request=api.requestFor(p,'DGM-AI-CONNECTION-001',models[1],{},false);
  api.admitStart(v,request,p);v.cells[4].settings.timeout_seconds=59;assert.throws(()=>api.admitStart(v,request,p));
});
test('fixed original D2 failure code is admitted while execution and usage stay unknown',()=>{
  requireAPI();const v=run();v.error_code='vertex_response_auth_failed';v.execution_mode=null;v.attempts_used=null;
  Object.assign(v.cells[4],{state:'unknown',reason_code:'unavailable',attempted:null,http_status:null,finish_reason:null,response_complete:null,strict_decode:'not_run'});
  assert.equal(decode(v,'run').error_code,'vertex_response_auth_failed');
  v.error_code='private/path/or/raw-message';assert.throws(()=>decode(v,'run'));
});

test('seven explicit input identities are supported and unknown/evaluator substitutions are not',()=>{
  requireAPI();assert.equal(typeof api.scenarioInfo,'function');
  for(const [id,evaluator] of [['DGM-AI-CONNECTION-001','connection-json-v1'],
    ...[1,2,3].map(i=>['intake-synthetic-s0'+i,'intake-understanding-v1']),
    ...[1,2,3].map(i=>['intent-synthetic-i0'+i,'intake-test-intent-semantic-v1'])]){
    assert.ok(api.scenarioInfo(id,evaluator));assert.equal(api.requestFor(profile(),id,models[1],{},false).scenario_id,id);
    assert.equal(api.scenarioInfo(id,'unknown-evaluator'),null);
  }
  assert.equal(api.scenarioInfo('unsupported-synthetic-x','connection-json-v1'),null);
  assert.throws(()=>api.requestFor(profile(),'unsupported-synthetic-x',models[1],{},false));
});

test('family-specific strict pass/fail never becomes semantic quality or another family result',()=>{
  requireAPI();
  for(const [id,verified,invalid] of [['DGM-AI-CONNECTION-001','connection_verified','connection_response_invalid'],
    ['intake-synthetic-s01','intake_response_verified','intake_response_invalid'],['intent-synthetic-i01','intent_response_verified','intent_response_invalid']]){
    const v=run();v.scenario_id=id;v.cells[4].reason_code=verified;
    assert.equal(decode(v,'run').cells[4].quality,'not_run');
    Object.assign(v.cells[4],{state:'failure',strict_decode:'fail',reason_code:invalid});assert.equal(decode(v,'run').cells[4].strict_decode,'fail');
    v.cells[4].reason_code=verified;assert.throws(()=>decode(v,'run'));
    Object.assign(v.cells[4],{state:'success',strict_decode:'pass',reason_code:id.startsWith('intent-')?'intake_response_verified':'intent_response_verified'});
    assert.throws(()=>decode(v,'run'));
  }
});

test('unsupported catalog metadata can be displayed but unknown row reasons and authority stay denied',()=>{
  requireAPI();const s=state();s.scenarios.push({scenario_id:'unsupported-synthetic-x',label:'미지원',input_sha256:'a'.repeat(64),schema_sha256:'b'.repeat(64),evaluator_id:'unknown-evaluator'});
  assert.equal(decode(s).scenarios.length,2);
  const v=run();v.cells[4].reason_code='unregistered_reason';assert.throws(()=>decode(v,'run'));
  v.cells[4].reason_code='connection_verified';v.cells[4].quality='pass';assert.throws(()=>decode(v,'run'));
});
