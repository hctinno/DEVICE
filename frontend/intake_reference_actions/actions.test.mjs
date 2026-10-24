/*052 C1 native-fetch boundary acceptance; complete synthetic DTOs, not backend API. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import * as api from './actions.mjs';
const {createSyntheticBundle}=createRequire(import.meta.url)('./browser_check.cjs');
const B=createSyntheticBundle(),CTX=B.context,INVALID='intake_reference_ui_invalid_request',UNAVAILABLE='intake_reference_ui_unavailable';
const STATE=['context','phase','pending','prepare_allowed','append_allowed','preview','registration','error_code'].sort();
const token='f'.repeat(64),otherToken='e'.repeat(64),copy=value=>structuredClone(value);
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const response=(value,{status=200,csrf=token,prepare='true',append='true',input='3'.repeat(64),read='true',headers={}}={})=>new Response(
 typeof value==='string'||value instanceof Uint8Array||value instanceof ReadableStream?value:JSON.stringify(value),
 {status,headers:{'Content-Type':'application/json; charset=utf-8',...(csrf===null?{}:{'X-Intake-Reference-CSRF':csrf}),
 'X-Intake-Reference-Read-Allowed':read,'X-Intake-Reference-Prepare-Allowed':prepare,'X-Intake-Reference-Append-Allowed':append,
 ...(input===null?{}:{'X-Intake-Reference-Review-Input':input}),...headers}});
const deeplyFrozen=value=>value===null||typeof value!=='object'||Object.isFrozen(value)&&Object.values(value).every(deeplyFrozen);
function harness(t,handler=null,callbacks={}){
 const calls=[],states=[],registered=[];let serial=0,latest=B;
 t.mock.method(globalThis,'fetch',(url,options)=>{const entry={url,options};calls.push(entry);
  if(handler)return handler(entry,calls.length);
  if(url.includes('/history?'))return Promise.resolve(response(latest.history));
  if(url.endsWith('/prepare')){latest=createSyntheticBundle(++serial);return Promise.resolve(response(latest.envelope));}
  const request=JSON.parse(options.body),value=copy(latest.registration);value.request_id=request.request_id;
  value.replayed=registered.length>0;return Promise.resolve(response(value));
 });
 const controller=api.createIntakeReferenceActionsController({onChange(value){states.push(value);callbacks.change?.(value);},
  onRegistered(value){registered.push(value);callbacks.registered?.(value);}});
 t.after(()=>controller.destroy());
 const ctx=value=>controller.setContext(value);ctx(CTX);
 return {controller,calls,states,registered,ctx,last:()=>states.at(-1)};
}
test('ESM2/controller7/constructor zero I/O and zero emit; invalid options fail without getters',t=>{
 assert.deepEqual(Object.keys(api).sort(),['createIntakeReferenceActionsController','createIntakeReferenceActionsReview']);
 let calls=0,emits=0,getters=0;t.mock.method(globalThis,'fetch',()=>{calls++;});
 const c=api.createIntakeReferenceActionsController({onChange(){emits++;},onRegistered(){}});
 assert.deepEqual(Object.keys(c).sort(),['setContext','setPending','refreshCapabilities','prepare','append','replay','destroy'].sort());
 assert.equal(calls,0);assert.equal(emits,0);c.destroy();
 for(const value of [{},{onChange(){},onRegistered(){},extra:true},null])assert.throws(()=>api.createIntakeReferenceActionsController(value),{message:INVALID});
 const value={onRegistered(){}};Object.defineProperty(value,'onChange',{enumerable:true,get(){getters++;return ()=>{};}});
 assert.throws(()=>api.createIntakeReferenceActionsController(value),{message:INVALID});assert.equal(getters,0);
});
test('prepare exact H1/P1 and public8/preview11 are detached deep-frozen without private keys',async t=>{
 const {controller:c,calls,states,last}=harness(t);await c.prepare();
 assert.equal(calls.length,2);assert.equal(calls[0].url,`/api/intake-references/${CTX.intake_id}/history?limit=1`);
 assert.equal(calls[1].url,`/api/intake-references/${CTX.intake_id}/prepare`);
 assert.deepEqual(Object.keys(JSON.parse(calls[1].options.body)).sort(),['schema_version','review_input_id','replace_handle_id'].sort());
 assert.equal(JSON.parse(calls[1].options.body).replace_handle_id,null);
 for(const entry of calls){assert.equal(entry.options.credentials,'same-origin');assert.equal(entry.options.cache,'no-store');assert.equal(entry.options.redirect,'error');
  assert.ok(!Object.keys(entry.options.headers).some(k=>/^(cookie|origin|host|sec-fetch)/i.test(k)));}
 assert.equal(last().phase,'ready');assert.equal(Object.keys(last().preview).length,11);
 for(const value of states){assert.deepEqual(Object.keys(value).sort(),STATE);assert.ok(deeplyFrozen(value));
  assert.ok(!/handle_id|append_request_id|REF-SYNTHETIC/.test(JSON.stringify(value)));}
 const before=states.length;c.setContext({...CTX});assert.equal(states.length,before);assert.equal(calls.length,2);
});
test('explicit append exact7 yields registration9 and context3 once; no automatic current or source retry',async t=>{
 const {controller:c,calls,registered,last}=harness(t);await c.prepare();await c.append();
 assert.equal(calls.length,3);const body=JSON.parse(calls[2].options.body);
 assert.deepEqual(Object.keys(body).sort(),['schema_version','handle_id','intake_id','request_id','preparation_id','expected_snapshot_id','expected_head_record_id'].sort());
 assert.equal(last().phase,'recorded');assert.equal(Object.keys(last().registration).length,9);assert.equal(Object.hasOwn(last().registration,'request_id'),false);
 assert.equal(registered.length,1);assert.deepEqual(registered[0],CTX);assert.ok(deeplyFrozen(registered[0]));
 assert.equal(calls.some(x=>x.url.endsWith('/current')),false);
});
test('I3 cache clear preserves original request and session anchor across new dispatch generation',async t=>{
 const {controller:c,calls,registered,last}=harness(t);await c.prepare();await c.append();const original=calls[2].options.body;
 c.setPending(true);c.setPending(false);c.setContext({...CTX,snapshotGeneration:2});await c.replay();
 assert.equal(calls.length,5);assert.ok(calls[4].options.body===original,'original exact7 preserved');
 assert.equal(last().registration.replayed,true);assert.deepEqual(registered[1],{...CTX,snapshotGeneration:2});
 c.setContext({...CTX,revision:3,snapshotGeneration:3});const count=calls.length;await c.replay();assert.equal(calls.length,count);
});
test('valid changed token retires occupied slot and blocks the explicit replay POST',async t=>{
 const h=harness(t);await h.controller.prepare();await h.controller.append();const count=h.calls.length;
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return Promise.resolve(response(B.history,{csrf:otherToken}));});
 await h.controller.replay();assert.equal(h.calls.length,count+1);assert.equal(h.last().phase,'retired');assert.equal(h.registered.length,1);
});
test('absent or contradictory token is not a new session and retains original request',async t=>{
 const h=harness(t);await h.controller.prepare();await h.controller.append();const original=h.calls.at(-1).options.body;
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return Promise.resolve(response(B.history,{csrf:null}));});
 await h.controller.replay();assert.notEqual(h.last().phase,'retired');assert.equal(h.last().prepare_allowed,false);
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});if(url.includes('/history?'))return Promise.resolve(response(B.history));
  const v=copy(B.registration);v.replayed=true;return Promise.resolve(response(v));});
 await h.controller.replay();assert.ok(h.calls.at(-1).options.body===original);assert.equal(h.last().phase,'recorded');
});
test('I2 lost replacement response cannot restore old-valid; new explicit preparation uses replace null',async t=>{
 const h=harness(t);await h.controller.prepare();let step=0;
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});if(url.includes('/history?'))return Promise.resolve(response(B.history));
  if(++step===1)return Promise.reject(Error('private path'));return Promise.resolve(response(createSyntheticBundle(2).envelope));});
 await h.controller.prepare();assert.equal(h.last().phase,'replacement_unknown');const count=h.calls.length;
 await h.controller.append();await h.controller.replay();assert.equal(h.calls.length,count);
 await h.controller.prepare();assert.equal(JSON.parse(h.calls.at(-1).options.body).replace_handle_id,null);assert.equal(h.last().phase,'ready');
});
test('initial prepare loss is prepare_unknown and no handle is fabricated',async t=>{
 const h=harness(t,(entry)=>entry.url.includes('/history?')?Promise.resolve(response(B.history)):Promise.reject(Error('private response')));
 await h.controller.prepare();assert.equal(h.last().phase,'prepare_unknown');assert.equal(h.last().preview,null);assert.equal(h.calls.length,2);
 await h.controller.append();await h.controller.replay();assert.equal(h.calls.length,2);
});
test('I3 uncertain is committed before caller-visible abort and late response is not inspected',async t=>{
 const late=deferred();let poison=0,atAbort;const h=harness(t);await h.controller.prepare();
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});options.signal.addEventListener('abort',()=>{atAbort=h.last().phase;});return late.promise;});
 const request=h.controller.append();h.controller.setPending(true);await request;
 assert.equal(atAbort,'uncertain');assert.equal(h.last().phase,'uncertain');
 late.resolve({get headers(){poison++;throw Error('late');}});await Promise.resolve();assert.equal(poison,0);assert.equal(h.registered.length,0);
});
test('invalid context after dispatch preserves unknown original request until same origin returns',async t=>{
 const late=deferred(),h=harness(t);await h.controller.prepare();
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return late.promise;});
 const request=h.controller.append(),original=h.calls.at(-1).options.body;h.controller.setContext({...CTX,revision:0});await request;
 assert.equal(h.last().phase,'uncertain');assert.equal(h.last().context,null);assert.equal(h.last().pending,true);
 h.controller.setPending(false);h.controller.setContext({...CTX,snapshotGeneration:5});
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return Promise.resolve(response(url.includes('/history?')?B.history:B.registration));});
 await h.controller.replay();assert.ok(h.calls.at(-1).options.body===original);assert.equal(h.last().phase,'recorded');late.resolve(response(B.registration));
});
test('callbacks throwing do not roll back recorded, retry, or escape; registered payload is exact3',async t=>{
 const h=harness(t,null,{change(){throw Error('observer private');},registered(){throw Error('observer');}});
 await h.controller.prepare();await h.controller.append();assert.equal(h.last().phase,'recorded');assert.equal(h.calls.length,3);assert.equal(h.registered.length,1);
});
test('callback reentrancy has no state/emit/I/O and destroy suppresses following registered callback',async t=>{
 let c,reentrant,checked=false;const h=harness(t,null,{change(state){if(c&&state.phase==='recorded'){
  assert.throws(()=>c.setContext(CTX),{message:INVALID});reentrant=assert.rejects(c.prepare(),{message:INVALID});checked=true;c.destroy();}}});
 c=h.controller;await c.prepare();await c.append();await reentrant;assert.equal(checked,true);assert.equal(h.registered.length,0);
 const n=h.states.length;await c.replay();c.setContext(CTX);assert.equal(h.states.length,n);assert.equal(h.calls.length,3);
});
test('capability header contradictions close source; legitimate false capability is unconfigured',async t=>{
 for(const options of [{prepare:'TRUE'},{append:'true',prepare:'false',input:null},{input:null},{read:'false'},
  {csrf:null},{input:'z'.repeat(64)}]){
  const h=harness(t,()=>Promise.resolve(response(B.history,options)));await h.controller.prepare();
  assert.equal(h.calls.length,1);assert.equal(h.last().error_code,UNAVAILABLE);assert.equal(h.last().prepare_allowed,false);h.controller.destroy();
 }
 const h=harness(t,()=>Promise.resolve(response(B.history,{csrf:null,read:'false',prepare:'false',append:'false',input:null})));
 await h.controller.prepare();assert.equal(h.last().phase,'unconfigured');assert.equal(h.calls.length,1);
});
test('strict envelope typed flags/reasons/time/duplicate keys/BOM/UTF8 never grant an unknown preparation',async t=>{
 const variants=[];for(const change of [x=>x.preview.verification.model_execution_verified=true,x=>x.preview.reason_codes=['future'],
  x=>x.preview.observation.observed_at='not UTC',x=>x.extra=true]){const e=copy(B.envelope);change(e);variants.push(JSON.stringify(e));}
 variants.push('{"schema_version":1,"schema_version":1}',new Uint8Array([239,187,191,123,125]),new Uint8Array([195,40]));
 for(const wire of variants){const h=harness(t,entry=>Promise.resolve(response(entry.url.includes('/history?')?B.history:wire)));
  await h.controller.prepare();assert.equal(h.last().phase,'prepare_unknown');assert.equal(h.last().preview,null);assert.equal(h.calls.length,2);h.controller.destroy();}
});
test('registration unsafe seq and authority claims preserve original slot as uncertain without emitting secrets',async t=>{
 for(const which of ['seq','authority','request']){const h=harness(t);await h.controller.prepare();let wire=copy(B.registration);
  if(which==='authority')wire.verification.operational_authority_granted=true;if(which==='request')wire.request_id='DIFFERENT';
  wire=JSON.stringify(wire);if(which==='seq')wire=wire.replace('"seq":1','"seq":9007199254740993');
  t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return Promise.resolve(response(wire));});
  await h.controller.append();assert.equal(h.last().phase,'uncertain');assert.equal(h.last().registration,null);assert.equal(h.registered.length,0);
  assert.equal(h.last().error_code,which==='seq'?'intake_reference_view_unrepresentable':UNAVAILABLE);h.controller.destroy();}
});
test('known410 retires while unknown code and 503 replacement do not restore old-valid',async t=>{
 const h=harness(t);await h.controller.prepare();
 t.mock.method(globalThis,'fetch',()=>Promise.resolve(response('{"error":{"code":"intake_reference_review_host_prepared_unavailable"}}',{status:410})));
 await h.controller.append();assert.equal(h.last().phase,'retired');assert.equal(h.registered.length,0);
 const j=harness(t);await j.controller.prepare();t.mock.method(globalThis,'fetch',(url)=>Promise.resolve(response(url.includes('/history?')?B.history:'{"error":{"code":"private_future"}}',{status:url.includes('/history?')?200:503})));
 await j.controller.prepare();assert.equal(j.last().phase,'replacement_unknown');assert.equal(j.last().error_code,UNAVAILABLE);
});
test('same source request deadline is35 seconds with no retry',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});let now=0;t.mock.method(performance,'now',()=>now);
 const h=harness(t);await h.controller.prepare();const wait=deferred();t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return wait.promise;});
 const p=h.controller.append();now=34999;t.mock.timers.tick(34999);assert.equal(h.calls.at(-1).options.signal.aborted,false);
 now=35000;t.mock.timers.tick(1);await p;assert.equal(h.last().phase,'uncertain');assert.equal(h.calls.length,3);wait.resolve(response(B.registration));
});
test('metadata failures and pending changes cannot erase the initial prepare_unknown observation',async t=>{
 const h=harness(t,entry=>entry.url.includes('/history?')?Promise.resolve(response(B.history)):Promise.reject(Error('wire lost')));
 await h.controller.prepare();assert.equal(h.last().phase,'prepare_unknown');
 t.mock.method(globalThis,'fetch',()=>Promise.reject(Error('metadata lost')));
 await h.controller.refreshCapabilities();assert.equal(h.last().phase,'prepare_unknown');
 h.controller.setPending(true);h.controller.setPending(false);assert.equal(h.last().phase,'prepare_unknown');
});
test('original local expiry is not extended by capability refresh or replay',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});let now=0;t.mock.method(performance,'now',()=>now);
 const e=copy(B.envelope);e.expires_in_seconds=2;
 const h=harness(t,entry=>Promise.resolve(response(entry.url.includes('/history?')?B.history:entry.url.endsWith('/prepare')?e:B.registration)));
 await h.controller.prepare();now=1000;t.mock.timers.tick(1000);await h.controller.append();await h.controller.refreshCapabilities();await h.controller.replay();
 const count=h.calls.length;now=2000;t.mock.timers.tick(1000);assert.equal(h.last().phase,'retired');await h.controller.replay();assert.equal(h.calls.length,count);
});
test('destroy is terminal during request: late parse/callback/source0; repeated destroy is harmless',async t=>{
 const h=harness(t);await h.controller.prepare();const wait=deferred();let poison=0;
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return wait.promise;});
 const p=h.controller.append(),n=h.states.length;h.controller.destroy();h.controller.destroy();await p;
 wait.resolve({get headers(){poison++;throw Error('late');}});await Promise.resolve();
 await h.controller.prepare();await h.controller.replay();h.controller.setPending(false);assert.equal(poison,0);assert.equal(h.states.length,n);assert.equal(h.registered.length,0);
});
test('a concurrent programmatic action cannot replace the visible in-flight phase or queue another POST',async t=>{
 const h=harness(t);await h.controller.prepare();const wait=deferred();
 t.mock.method(globalThis,'fetch',(url,options)=>{h.calls.push({url,options});return wait.promise;});
 const first=h.controller.append();await h.controller.prepare();assert.equal(h.calls.length,3);assert.equal(h.last().phase,'appending');
 wait.resolve(response(B.registration));await first;assert.equal(h.last().phase,'recorded');assert.equal(h.registered.length,1);
});
test('bootstrap consuming the whole35-second action budget cannot dispatch a new source POST',async t=>{
 let now=0;t.mock.method(performance,'now',()=>now);
 const h=harness(t,()=>{now=35001;return Promise.resolve(response(B.history));});
 await h.controller.prepare();assert.equal(h.calls.length,1);assert.equal(h.last().phase,'error');assert.equal(h.last().error_code,UNAVAILABLE);
 assert.equal(h.calls[0].options.signal.aborted,true,'deadline rejection releases the native response through its signal');
});
test('envelope byte cap checks both content-length and streamed bytes and cancels oversized readers',async t=>{
 for(const header of [true,false]){let cancelled=0;
  const h=harness(t,entry=>{if(entry.url.includes('/history?'))return Promise.resolve(response(B.history));
   const stream=new ReadableStream({pull(c){c.enqueue(new Uint8Array(65537));},cancel(){cancelled++;}});
   return Promise.resolve(response(stream,{headers:header?{'Content-Length':'65537'}:{}}));});
  await h.controller.prepare();assert.equal(cancelled,1);assert.equal(h.last().phase,'prepare_unknown');assert.equal(h.registered.length,0);h.controller.destroy();
 }
});
test('all five binding states and UTC basic/week/partial forms retain original literals and false flags',async t=>{
 for(const binding of ['current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound']){
  const h=harness(t);await h.controller.prepare();const v=copy(B.registration);v.binding_status=binding;v.verification.mutable_state_verified_at_append=false;
  if(binding!=='current_at_append'){v.append_observation.head_advanced=false;v.append_observation.head_after_record_id=null;}
  v.append_observation.observed_at='2026W431T0002+00';
  t.mock.method(globalThis,'fetch',()=>Promise.resolve(response(v)));await h.controller.append();
  assert.equal(h.last().registration.binding_status,binding);assert.equal(h.last().registration.verification.mutable_state_verified_at_append,false);
  assert.equal(h.last().registration.append_observation.observed_at,'2026W431T0002+00');h.controller.destroy();
 }
});
