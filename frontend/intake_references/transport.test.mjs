/*050 F1 native-fetch boundary tests. Explicit wire fixtures, no product host/Store. */
import test from 'node:test';
import assert from 'node:assert/strict';
import * as api from './transport.mjs';

const INVALID='intake_reference_ui_invalid_request',UNAVAILABLE='intake_reference_ui_unavailable';
const context={intake_id:'SYNTHETIC-050',revision:2,snapshotGeneration:1};
const query={limit:20,before_seq:null};
const tokenA='1'.repeat(64),tokenB='2'.repeat(64);
const raw='{"synthetic_wire_only":true}';
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
const reply=(body=raw,{status=200,allowed='true',token=tokenA,headers={}}={})=>new Response(body,{status,headers:{
 'Content-Type':'application/json; charset=utf-8',
 ...(allowed===null?{}:{'X-Intake-Reference-Read-Allowed':allowed}),
 ...(token===null?{}:{'X-Intake-Reference-CSRF':token}),...headers}});
function harness(t,responder=()=>reply()){
 const calls=[];t.mock.method(globalThis,'fetch',(url,options)=>{calls.push({url,options});return responder(calls.length,calls.at(-1));});
 const transport=api.createIntakeReferenceTransport();transport.setContext(context);t.after(()=>transport.destroy());
 return {transport,calls,history:(q=query,signal=new AbortController().signal)=>transport.readHistory(context.intake_id,q,signal),
  current:(signal=new AbortController().signal)=>transport.readCurrent(context.intake_id,signal)};
}
const rejects=(promise,code=UNAVAILABLE)=>assert.rejects(promise,error=>error instanceof Error&&error.message===code&&Object.keys(error).length===0);

test('factory exports exactly one constructor and six closures, with no construction I/O or injected options',t=>{
 assert.deepEqual(Object.keys(api),['createIntakeReferenceTransport']);
 const {transport,calls}=harness(t);
 assert.deepEqual(Object.keys(transport).sort(),['destroy','hasRetainedDocxSelection','readCurrent','readHistory','setContext','setPending']);
 assert.equal(calls.length,0);
 for(const options of [{}, {fetch:()=>{}},null])assert.throws(()=>api.createIntakeReferenceTransport(options),{message:INVALID});
});
test('DOCX selection hint only enables an explicit exact2 source POST with the existing private token',async t=>{
 const {transport,calls,history}=harness(t,()=>reply(raw,{headers:{'X-Intake-Reference-Docx-Selected':'true'}}));
 assert.equal(transport.hasRetainedDocxSelection(),false);
 await history();assert.equal(transport.hasRetainedDocxSelection(),true);
 assert.deepEqual(await transport.readCurrent(context.intake_id,new AbortController().signal,'docx_retained'),raw);
 assert.deepEqual(JSON.parse(calls[1].options.body),{schema_version:1,action:'docx_retained'});
 assert.equal(calls[1].options.headers['X-Intake-Reference-CSRF'],tokenA);
 transport.setPending(true);assert.equal(transport.hasRetainedDocxSelection(),false);
});
test('DOCX missing or lost selection never fetches and malformed headers never grant a selection',async t=>{
 let config={};const {transport,calls,history}=harness(t,()=>reply(raw,config));await history();
 assert.equal(transport.hasRetainedDocxSelection(),false);
 await rejects(transport.readCurrent(context.intake_id,new AbortController().signal,'docx_retained'),'intake_reference_ui_unconfigured');
 for(config of [{headers:{'X-Intake-Reference-Docx-Selected':'false'}},{allowed:'false',token:null,headers:{'X-Intake-Reference-Docx-Selected':'true'}}]){
  await rejects(history());assert.equal(transport.hasRetainedDocxSelection(),false);
 }
 const before=calls.length;await rejects(transport.readCurrent(context.intake_id,new AbortController().signal,'docx_retained'),'intake_reference_ui_unconfigured');
 assert.equal(calls.length,before);
});
test('DOCX source403 drops only its private selection and cannot resume it from an old response',async t=>{
 const {transport,history,calls}=harness(t,n=>n===1?reply(raw,{headers:{'X-Intake-Reference-Docx-Selected':'true'}}):reply('{"error":{"code":"intake_reference_ui_access_denied"}}',{status:403}));
 await history();await rejects(transport.readCurrent(context.intake_id,new AbortController().signal,'docx_retained'),'intake_reference_ui_access_denied');
 assert.equal(transport.hasRetainedDocxSelection(),false);
 await rejects(transport.readCurrent(context.intake_id,new AbortController().signal,'docx_retained'),'intake_reference_ui_unconfigured');assert.equal(calls.length,2);
});
test('same_origin_exact_paths_and_body: null cursor omitted, bounded cursor literal and current exact2',async t=>{
 const {transport,calls,history,current}=harness(t);
 assert.deepEqual(await history(),{raw_json:raw,read_allowed:true});
 await history({limit:100,before_seq:Number.MAX_SAFE_INTEGER});await current();
 assert.equal(calls[0].url,'/api/intake-references/SYNTHETIC-050/history?limit=20');
 assert.equal(calls[1].url,'/api/intake-references/SYNTHETIC-050/history?limit=100&before_seq=9007199254740991');
 assert.equal(calls[2].url,'/api/intake-references/SYNTHETIC-050/current');
 for(const {options} of calls){assert.equal(options.credentials,'same-origin');assert.equal(options.cache,'no-store');
  assert.equal(options.redirect,'error');assert.ok(options.signal instanceof AbortSignal);
  assert.ok(!Object.keys(options.headers||{}).some(key=>/^(origin|host|cookie|sec-fetch)/i.test(key)));}
 assert.equal(calls[0].options.method,'GET');assert.equal(calls[2].options.method,'POST');
 assert.deepEqual(JSON.parse(calls[2].options.body),{schema_version:1,action:'current'});
 assert.ok(calls[2].options.headers['X-Intake-Reference-CSRF']===tokenA,'private token forwarded only as header');
 assert.equal(await current(),raw);transport.setContext({...context});await current();
 assert.equal(calls.length,5,'same valid non-null context preserves capability');
});
test('strict_header_false_and_missing_csrf rejects contradictions and never invents read permission',async t=>{
 let options={allowed:'false',token:null};const {history,current,calls}=harness(t,()=>reply(raw,options));
 assert.deepEqual(await history(),{raw_json:raw,read_allowed:false});await rejects(current(),INVALID);
 for(options of [{allowed:null,token:null},{allowed:'TRUE'},{allowed:'false',token:tokenA},
  {allowed:'true',token:null},{allowed:'true',token:'short'},{allowed:'true',token:'A'.repeat(64)}])await rejects(history());
 assert.equal(calls.length,7);
});
test('read arguments and setters reject invalid own-data/context/query/signal without fetching or retained permission',async t=>{
 const {transport,calls,history,current}=harness(t);await history();
 for(const q of [{limit:0,before_seq:null},{limit:101,before_seq:null},{limit:20,before_seq:0},
  {limit:20,before_seq:9007199254740992},{limit:20,before_seq:null,extra:true},{limit:20},
  Object.create({limit:20,before_seq:null})]){transport.setContext(context);await rejects(history(q),INVALID);}
 transport.setContext(context);await rejects(transport.readHistory('OTHER',query,new AbortController().signal),INVALID);
 transport.setContext(context);await rejects(history(query,{}),INVALID);
 transport.setContext(context);await rejects(transport.readHistory(context.intake_id,undefined,new AbortController().signal),INVALID);
 for(const ctx of [{...context,revision:0},{...context,intake_id:'../unsafe'},{...context,extra:true}]){
  assert.throws(()=>transport.setContext(ctx),{message:INVALID});await rejects(current(),INVALID);}
 assert.throws(()=>transport.setPending('false'),{message:INVALID});transport.setPending(false);await rejects(current(),INVALID);
 assert.equal(calls.length,1);
});
test('query/context accessors are not invoked and errors do not echo hostile messages',async t=>{
 const {transport,history,calls}=harness(t);let getter=0;
 const bad={limit:20};Object.defineProperty(bad,'before_seq',{enumerable:true,get(){getter++;throw Error('private path');}});
 await rejects(history(bad),INVALID);assert.equal(getter,0);assert.equal(calls.length,0);
 transport.setContext(context);t.mock.method(globalThis,'fetch',()=>Promise.reject(Error('private raw exception')));
 await rejects(history());
});
test('all exact known server errors retain only their fixed code; unknown prefix and malformed envelope close',async t=>{
 let code='intake_reference_ui_access_denied',body;const {history}=harness(t,()=>reply(body??JSON.stringify({error:{code}}),{status:503,allowed:null,token:null}));
 const codes={ui:['unconfigured','invalid_request','input_limit','access_denied','session_unavailable','unavailable'],
  review:['access_denied','input_limit','invalid_argument','parent_invalid','prepared_invalid','review_state_changed','store_invalid','unavailable'],
  ledger:['input_limit','intake_not_found','integrity_invalid','invalid_argument','origin_invalid','parent_invalid','request_conflict','schema_mismatch','storage_error','store_invalid'],
  state:['delegation_invalid','input_limit','intake_not_found','invalid_argument','projection_inconsistent','source_integrity_invalid','storage_error','store_invalid','transaction_required']};
 for(const [prefix,suffixes] of Object.entries(codes))for(const suffix of suffixes){code=`intake_reference_${prefix}_${suffix}`;await rejects(history(),code);}
 for(body of ['{"error":{"code":"intake_reference_ui_future"}}','{"error":{"code":"intake_reference_ui_access_denied","extra":true}}',
  '{"error":{"code":"intake_reference_ui_access_denied","code":"intake_reference_ui_unavailable"}}',
  '{"error":{"code":"intake_reference_ui_access_denied"},"secret":"hidden"}','not JSON'])await rejects(history());
});
test('fatal_utf8_bom_stream_cap rejects bytes before replacement decode and cancels oversized streams',async t=>{
 let body=new Uint8Array([0xc3,0x28]),headers={},cancelled=0;
 const {history}=harness(t,()=>reply(body,{headers}));
 await rejects(history());body=new Uint8Array([0xef,0xbb,0xbf,0x7b,0x7d]);await rejects(history());
 body=raw;headers={'Content-Length':'2097153'};await rejects(history());
 headers={'Content-Length':'invalid'};await rejects(history());headers={};
 body=new ReadableStream({pull(controller){controller.enqueue(new Uint8Array(2097153));},cancel(){cancelled++;}});
 await rejects(history());assert.equal(cancelled,1);
 body=new ReadableStream({start(controller){controller.enqueue(new Uint8Array([0xef]));controller.enqueue(new Uint8Array([0xbb,0xbf,123,125]));controller.close();}});
 await rejects(history());
});
test('2 MiB boundary and multibyte chunks remain exact raw strings without typed Number parsing',async t=>{
 let text='x'.repeat(2097152);const {history}=harness(t,()=>reply(new ReadableStream({start(controller){
  const b=new TextEncoder().encode(text);controller.enqueue(b.slice(0,1));controller.enqueue(b.slice(1));controller.close();}})));
 assert.equal((await history()).raw_json.length,2097152);
 text='{"한글":9007199254740993}';assert.equal((await history()).raw_json,text);
});
test('invalid content type and network/reader exceptions are fixed unavailable without secret echo',async t=>{
 let mode=0;const {history}=harness(t,()=>{if(mode===0)return reply(raw,{headers:{'Content-Type':'text/html'}});
  if(mode===1)throw Error('private endpoint/path');return reply(new ReadableStream({pull(){throw Error('private stream');}}));});
 for(mode=0;mode<3;mode++)await rejects(history());
});
test('late_history_cannot_publish_secret or inspect headers after context cancellation',async t=>{
 const late=deferred();let accessed=0;const {transport,history,current,calls}=harness(t,n=>n===1?late.promise:reply(raw,{token:tokenB}));
 const old=history(),oldFailure=rejects(old);transport.setContext({...context,revision:3});await oldFailure;
 await history();late.resolve({get headers(){accessed++;throw Error('late secret');}});await Promise.resolve();
 assert.equal(accessed,0);await current();assert.ok(calls.at(-1).options.headers['X-Intake-Reference-CSRF']===tokenB);
});
test('newer history ticket wins within same context and same valid context preserves an in-flight ticket',async t=>{
 const late=deferred();const {transport,history,current,calls}=harness(t,n=>n===1?late.promise:reply(raw,{token:tokenB}));
 const old=history(),oldFailure=rejects(old);await history();await oldFailure;
 late.resolve(reply(raw,{allowed:'false',token:null}));await Promise.resolve();
 await current();assert.ok(calls.at(-1).options.headers['X-Intake-Reference-CSRF']===tokenB);
 const waiting=deferred();t.mock.method(globalThis,'fetch',()=>waiting.promise);
 const request=history();transport.setContext({...context});waiting.resolve(reply());assert.equal((await request).read_allowed,true);
});
test('old403_cannot_clear_new_token from a newer history response',async t=>{
 const late=deferred();const {history,current,calls}=harness(t,n=>n===2?late.promise:reply(raw,{token:n===1?tokenA:tokenB}));
 await history();const old=current(),oldFailure=rejects(old,'intake_reference_ui_access_denied');
 await history();late.resolve(reply('{"error":{"code":"intake_reference_ui_access_denied"}}',{status:403,allowed:null,token:null}));await oldFailure;
 await current();assert.ok(calls.at(-1).options.headers['X-Intake-Reference-CSRF']===tokenB);
});
test('current 403/session failure clears only the token version it used and does not retry',async t=>{
 const {history,current,calls}=harness(t,n=>n===1?reply():reply('{"error":{"code":"intake_reference_ui_access_denied"}}',{status:403,allowed:null,token:null}));
 await history();await rejects(current(),'intake_reference_ui_access_denied');await rejects(current(),INVALID);assert.equal(calls.length,2);
});
test('context_pending_destroy_abort_without_retry closes pending work before a late response',async t=>{
 const pending=[];const {transport,history,current,calls}=harness(t,n=>n===1?reply():(pending.push(deferred()),pending.at(-1).promise));
 await history();const request=current(),failure=rejects(request);transport.setPending(true);await failure;
 assert.equal(calls[1].options.signal.aborted,true);await rejects(history(),INVALID);
 transport.setPending(false);await rejects(current(),INVALID);
 const next=history(),nextFailure=rejects(next);transport.destroy();transport.destroy();await nextFailure;
 assert.equal(calls[2].options.signal.aborted,true);transport.setContext(context);transport.setPending(false);
 await rejects(history(),INVALID);assert.equal(calls.length,3);
 for(const wait of pending)wait.resolve(reply());
});
test('null context, invalid queued context and invalid pending cannot resume an earlier grant',async t=>{
 const {transport,history,current,calls}=harness(t);await history();transport.setContext(null);await rejects(current(),INVALID);
 transport.setContext(context);await history();transport.setPending(true);
 assert.throws(()=>transport.setContext({...context,revision:0}),{message:INVALID});transport.setPending(false);
 await rejects(history(),INVALID);assert.equal(calls.length,2);
});
test('caller abort cancels stream read even when fetch ignores its signal; deadline is exactly 35 seconds',async t=>{
 const waits=[];const {history,calls}=harness(t,()=>{const d=deferred();waits.push(d);return d.promise;});
 const controller=new AbortController(),p=history(query,controller.signal),failure=rejects(p);controller.abort();await failure;
 assert.equal(calls[0].options.signal.aborted,true);
 t.mock.timers.enable({apis:['setTimeout']});const timeout=history(),timeoutFailure=rejects(timeout);
 t.mock.timers.tick(34999);assert.equal(calls[1].options.signal.aborted,false);
 t.mock.timers.tick(1);await timeoutFailure;assert.equal(calls[1].options.signal.aborted,true);
 assert.equal(calls.length,2);for(const wait of waits)wait.resolve(reply());
});
test('already aborted caller does not fetch or publish a capability',async t=>{
 const {history,current,calls}=harness(t);const controller=new AbortController();controller.abort();
 await rejects(history(query,controller.signal));await rejects(current(),INVALID);assert.equal(calls.length,0);
});
test('caller abort during an open body read cancels and releases its reader',async t=>{
 let cancelled=0,stream;const {history,calls}=harness(t,()=>{stream=new ReadableStream({cancel(){cancelled++;}});return reply(stream);});
 const controller=new AbortController(),request=history(query,controller.signal),failure=rejects(request);
 await Promise.resolve();await Promise.resolve();controller.abort();await failure;
 await Promise.resolve();await Promise.resolve();
 assert.equal(cancelled,1);assert.equal(stream.locked,false);assert.equal(calls.length,1);
});
test('completed requests clear deadline and caller abort listeners',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});const {history,calls}=harness(t),controller=new AbortController();
 await history(query,controller.signal);controller.abort();t.mock.timers.tick(35000);
 assert.equal(calls[0].options.signal.aborted,false,'completed request no longer follows caller or deadline');
});
test('a mismatched intake request invalidates active work and closes its retained grant',async t=>{
 const late=deferred();const {transport,history,current,calls}=harness(t,n=>n===1?reply():late.promise);
 await history();const active=current(),failure=rejects(active);
 await rejects(transport.readHistory('OTHER-INTAKE',query,new AbortController().signal),INVALID);
 assert.equal(calls[1].options.signal.aborted,true);await failure;
 transport.setPending(false);await rejects(current(),INVALID);assert.equal(calls.length,2);late.resolve(reply());
});
