//044 A1: full synthetic DTOs against the real public parser/gate; no Store/API.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import fixtures from './browser_check.cjs';
const target=new URL('./model.mjs',import.meta.url);
let model=null;
try{model=await import(target.href);}catch(error){if(error.code!=='ERR_MODULE_NOT_FOUND'||existsSync(target))throw error;}
const check=(name,run)=>test(name,()=>{assert.ok(model,'044 public model is not implemented');run();});
const bundle=()=>fixtures.createSyntheticBundle(),clone=value=>structuredClone(value),raw=value=>JSON.stringify(value);
const invalid=action=>assert.throws(action,/^Error: invalid_intake_reference_view$/);
const unsafe=action=>assert.throws(action,/^Error: intake_reference_view_unrepresentable$/);
const query={limit:20,before_seq:null};
const history=(f=bundle(),q=query)=>model.parseIntakeReferenceHistoryJson(raw(f.history),f.context.intake_id,q);
const current=(f=bundle())=>model.parseIntakeReferenceCurrentJson(raw(f.current),f.context.intake_id);

check('public model exposes exactly one constant and four functions',()=>{
 assert.deepEqual(Object.keys(model).sort(),['INTAKE_REFERENCE_VIEW_MAX_BYTES','createIntakeReferenceGate',
  'parseIntakeReferenceCurrentJson','parseIntakeReferenceHistoryJson','validateIntakeReferenceContext'].sort());
 assert.equal(model.INTAKE_REFERENCE_VIEW_MAX_BYTES,2097152);
});
check('full metadata history7 and current10 remain detached original values',()=>{
 const f=bundle(),h=history(f),c=current(f);
 assert.deepEqual(h,f.history);assert.deepEqual(c,f.current);
 h.records[0].append_observation.preparation_ready=true;c.reference_summary.selected_case_ids.pop();
 assert.equal(f.history.records[0].append_observation.preparation_ready,false);
 assert.equal(f.current.reference_summary.selected_case_ids.length,2);
});
check('context3 null and safe zero generation remain exact detached values',()=>{
 const f=bundle(),input={...f.context,snapshotGeneration:0},result=model.validateIntakeReferenceContext(input);
 assert.deepEqual(result,input);result.revision=1;assert.equal(input.revision,2);
 assert.equal(model.validateIntakeReferenceContext(null),null);
});
check('ASCII intake IDs accept150 and refuse151 invalid first character LF CRLF and aliases',()=>{
 for(const id of ['A','A'+'.'.repeat(149)]){
  const f=bundle();f.context.intake_id=id;f.history.intake_id=id;f.current.intake_id=id;
  assert.equal(history(f).intake_id,id);assert.equal(current(f).intake_id,id);
  assert.equal(model.validateIntakeReferenceContext(f.context).intake_id,id);
 }
 for(const id of ['', 'A'.repeat(151),'_A','한글',' A','A ','A/1','A%31','A\n','A\r\n']){
  const f=bundle();f.context.intake_id=id;invalid(()=>model.validateIntakeReferenceContext(f.context));
 }
});
check('context rejects extra missing boolean fraction negative and unsafe fields',()=>{
 for(const change of [v=>{v.extra=false;},v=>{delete v.revision;},v=>{v.revision=true;},
  v=>{v.revision=0;},v=>{v.revision=1.5;},v=>{v.snapshotGeneration=-1;},v=>{v.snapshotGeneration=false;}]){
  const f=bundle();change(f.context);invalid(()=>model.validateIntakeReferenceContext(f.context));
 }
 const f=bundle();f.context.revision=9007199254740992;unsafe(()=>model.validateIntakeReferenceContext(f.context));
});
check('context rejects accessors symbols nonenumerable fields prototypes and cycles without hooks',()=>{
 let calls=0;const accessor={...bundle().context};Object.defineProperty(accessor,'revision',{enumerable:true,get(){calls++;return 2;}});
 invalid(()=>model.validateIntakeReferenceContext(accessor));assert.equal(calls,0);
 for(const value of [Object.assign(Object.create({extra:true}),bundle().context),
  Object.defineProperty({...bundle().context},'secret',{value:true}),
  {...bundle().context,[Symbol('secret')]:true}])invalid(()=>model.validateIntakeReferenceContext(value));
 const cyclic={...bundle().context};cyclic.revision=cyclic;invalid(()=>model.validateIntakeReferenceContext(cyclic));
});
check('foreign thrown Error accessors cannot escape fixed errors or execute a message hook',()=>{
 let calls=0;const error=new Error();Object.defineProperty(error,'message',{get(){calls++;throw Error('SYNTHETIC PRIVATE FAILURE');}});
 const input=new Proxy({...bundle().context},{getPrototypeOf(){throw error;}});
 invalid(()=>model.validateIntakeReferenceContext(input));assert.equal(calls,0);
});
check('history available false is metadata absence and keeps null and false flags',()=>{
 const f=bundle();Object.assign(f.history,{available:false,records:[],next_before_seq:null});
 f.history.verification.record_metadata_verified=false;
 assert.deepEqual(history(f),f.history);
 f.history.records=[bundle().history.records[0]];invalid(()=>history(f));
});
check('zero count false readiness and nullable catalog survive without default conversion',()=>{
 const f=bundle();Object.assign(f.current.reference_summary,{status:'insufficient_evidence',context_id:null,selected_case_ids:[],accepted_reference_count:0});
 const value=current(f);assert.equal(value.reference_summary.accepted_reference_count,0);
 assert.equal(value.current_observation.preparation_ready,false);
 assert.equal(history(f).records[1].source_modes.catalog_synthetic,null);
});
check('current none with absent ledger and a real observation is distinct from unavailable',()=>{
 const f=bundle();Object.assign(f.current,{available:false,status:'none',record:null,reference_summary:null,reason_codes:['no_reference_head']});
 f.current.current_observation.head_record_id=null;f.current.verification.record_hash_verified=false;
 const value=current(f);assert.equal(value.status,'none');assert.equal(value.available,false);
 assert.equal(value.current_observation.snapshot_id,'a'.repeat(64));
});
check('stale and unavailable can preserve their verified historical head and summary',()=>{
 for(const status of ['stale','unavailable']){
  const f=bundle();f.current.status=status;
  f.current.current_observation.snapshot_id=status==='stale'?'f'.repeat(64):null;
  f.current.reason_codes=[status==='stale'?'reference_snapshot_stale':'current_capture_unavailable'];
  assert.equal(current(f).record.record_id,'c'.repeat(64));
 }
});
check('current status snapshot head record hash and receipt invariants reject mutations',()=>{
 for(const change of [v=>{v.status='none';},v=>{v.status='unavailable';},
  v=>{v.current_observation.snapshot_id='f'.repeat(64);},v=>{v.current_observation.head_record_id=null;},
  v=>{v.record.binding_status='historical_provided';},v=>{v.available=false;},
  v=>{v.reference_summary.receipt_id='f'.repeat(64);},v=>{v.verification.record_hash_verified=false;},
  v=>{v.verification.database_snapshot_observed=false;}]){
  const f=bundle();change(f.current);invalid(()=>current(f));
 }
});
check('append observation is historical and must match its record and original time',()=>{
 for(const change of [v=>{v.append_observation.expected_snapshot_id='f'.repeat(64);},
  v=>{v.append_observation.captured_snapshot_id=null;},v=>{v.append_observation.head_advanced=false;},
  v=>{v.append_observation.head_after_record_id=null;},v=>{v.append_observation.observed_at='2026-10-24T00:00:00Z';}]){
  const f=bundle();change(f.history.records[0]);invalid(()=>history(f));
 }
});
check('all five binding statuses preserve their exact source mode values',()=>{
 for(const status of ['current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound']){
  const f=bundle(),record=f.history.records[0];record.binding_status=status;
  if(status!=='current_at_append')Object.assign(record.append_observation,{head_advanced:false,head_before_record_id:null,head_after_record_id:null});
  assert.equal(history(f).records[0].binding_status,status);
 }
});
check('history page limit exact cursor descending sequence and next cursor stay strict',()=>{
 const f=bundle();f.history.next_before_seq=2;assert.equal(history(f,{limit:2,before_seq:null}).next_before_seq,2);
 for(const change of [v=>v.records.reverse(),v=>{v.records[1].seq=3;},v=>{v.next_before_seq=1;}]){
  const f=bundle();change(f.history);invalid(()=>history(f));
 }
 invalid(()=>history(bundle(),{limit:1,before_seq:null}));
 invalid(()=>history(bundle(),{limit:20,before_seq:3}));
 for(const q of [{limit:0,before_seq:null},{limit:101,before_seq:null},{limit:20,before_seq:0},
  {limit:true,before_seq:null},{limit:20,before_seq:false},{limit:20,before_seq:null,secret:true}])invalid(()=>history(bundle(),q));
});
check('history100 and safe SQLite seq boundary are accepted without narrowing the parent',()=>{
 const f=bundle(),template=f.history.records[1];f.history.records=Array.from({length:100},(_,i)=>({...clone(template),seq:100-i,
  record_id:(i+1).toString(16).padStart(64,'0'),request_id:'SYNTHETIC-REQUEST-'+i}));
 assert.equal(history(f,{limit:100,before_seq:null}).records.length,100);
 f.history.records.push({...clone(template),seq:1});invalid(()=>history(f,{limit:100,before_seq:null}));
 const safe=bundle();safe.history.records[0].seq=Number.MAX_SAFE_INTEGER;
 assert.equal(history(safe).records[0].seq,9007199254740991);
});
check('history cannot duplicate a durable record or request identity under different sequences',()=>{
 for(const key of ['record_id','request_id']){
  const f=bundle();f.history.records[1][key]=f.history.records[0][key];invalid(()=>history(f));
 }
});
check('current wrapper reasons correspond exactly to the observed business state',()=>{
 const f=bundle();for(const reason of ['current_capture_unavailable','no_reference_head']){
  const copy=clone(f);copy.current.reason_codes=[reason];invalid(()=>current(copy));
 }
 const stale=clone(f);stale.current.status='stale';stale.current.current_observation.snapshot_id='f'.repeat(64);
 stale.current.reason_codes=[];invalid(()=>current(stale));
});
check('raw unsafe integer lexemes fail before Number rounding including SQLite63bit maximum',()=>{
 const f=bundle(),encoded=raw(f.history);
 for(const number of ['9007199254740992','9007199254740993','9223372036854775807'])
  unsafe(()=>model.parseIntakeReferenceHistoryJson(encoded.replace('"seq":3','"seq":'+number),f.context.intake_id,query));
 unsafe(()=>history(bundle(),{limit:20,before_seq:9007199254740992}));
});
check('fraction and exponent numeric lexemes are not Python integer DTO fields',()=>{
 const f=bundle();for(const number of ['3.0','3e0','2.999999999999999999'])
  invalid(()=>model.parseIntakeReferenceHistoryJson(raw(f.history).replace('"seq":3','"seq":'+number),f.context.intake_id,query));
});
check('case IDs16 accepted references256 and sorted unique IDs preserve original count',()=>{
 const f=bundle();f.current.reference_summary.selected_case_ids=Array.from({length:16},(_,i)=>'SYNTHETIC-'+String(i).padStart(2,'0'));
 f.current.reference_summary.accepted_reference_count=256;assert.equal(current(f).reference_summary.accepted_reference_count,256);
 for(const change of [v=>v.selected_case_ids.reverse(),v=>v.selected_case_ids.push('SYNTHETIC-EXTRA'),
  v=>{v.accepted_reference_count=257;},v=>{v.selected_case_ids[1]=v.selected_case_ids[0];}]){
  const copy=clone(f);change(copy.current.reference_summary);invalid(()=>current(copy));
 }
});
check('reason codes require exact known sorted unique strings without repairing parent data',()=>{
 for(const reasons of [['unknown'],['preparation_not_ready','analysis_not_ready'],
  ['analysis_not_ready','analysis_not_ready'],[false]]){
  const f=bundle();f.current.reason_codes=reasons;invalid(()=>current(f));
 }
});
check('every authority or history revalidation flag promotion is rejected',()=>{
 for(const key of ['reference_source_currentness_verified','operational_authority_granted','model_execution_verified','evaluation_executed']){
  const f=bundle();f.current.verification[key]=true;invalid(()=>current(f));
 }
 for(const key of ['payloads_reverified','original_sources_reverified','database_currentness_verified']){
  const f=bundle();f.history.verification[key]=true;invalid(()=>history(f));
 }
});
check('wrong intake missing extra private fields unknown enums and scalar types are refused',()=>{
 for(const change of [v=>{v.intake_id='SYNTHETIC-OTHER';},v=>{delete v.available;},
  v=>{v.private_receipt={quote:'SYNTHETIC PRIVATE'};},v=>{v.schema_version=true;},
  v=>{v.records[0].source_modes.catalog_synthetic=0;},v=>{v.records[0].seq=false;},
  v=>{v.records[0].source_modes.intake_provenance_status='unknown';},v=>{v.available=1;}]){
  const f=bundle();change(f.history);invalid(()=>history(f));
 }
 const f=bundle();f.current.reference_summary.raw_json='SYNTHETIC PRIVATE';invalid(()=>current(f));
});
check('UTC timestamps preserve microseconds Z and valid calendar values',()=>{
 for(const time of ['2026-10-24T01:02:03.123456+00:00','2026-10-24T01:02:03Z','2024-02-29T23:59:59+00:00']){
  const f=bundle();f.current.current_observation.observed_at=time;assert.equal(current(f).current_observation.observed_at,time);
 }
});
check('parent Python ISO basic week partial and zero-offset timestamp forms are not narrowed',()=>{
 for(const time of ['20261024T010203Z','2026-W43-6T01:02:03+00:00','2026W436T01Z',
  '2026-10-24T01.5Z','2026-10-24T01:02.5Z','2026-10-24T01:02:03+00',
  '2026-10-24T01:02:03+00:00:00.5','2026-10-24T01:02:03-00:00',
  '2026-10-24T01:02:03.123456789Z','2026-10-24𠮷01:02:03Z']){
  const f=bundle();f.current.current_observation.observed_at=time;
  assert.equal(current(f).current_observation.observed_at,time);
 }
});
check('invalid calendar timezone omission and nonUTC offset fail',()=>{
 for(const time of ['2026-02-29T01:02:03Z','2026-10-24T24:00:00Z','2026-10-24T01:02:03',
  '2026-10-24T01:02:03+09:00','2026-10-24T01:60:00Z','SYNTHETIC-INVALID',
  '2026-10-24T01:02:03Z\n','2026-10-24T01:02:03+00:00\r\n']){
  const f=bundle();f.current.current_observation.observed_at=time;invalid(()=>current(f));
 }
});
check('raw exactly2MiB accepts whitespace and one extra byte is refused',()=>{
 const f=bundle(),encoded=raw(f.history),padded=' '.repeat(2097152-Buffer.byteLength(encoded))+encoded;
 assert.deepEqual(model.parseIntakeReferenceHistoryJson(padded,f.context.intake_id,query),f.history);
 invalid(()=>model.parseIntakeReferenceHistoryJson(' '+padded,f.context.intake_id,query));
});
check('strict JSON refuses BOM duplicate keys bad escapes lone surrogates trailing and nonfinite',()=>{
 const f=bundle(),encoded=raw(f.history);
 for(const value of ['\ufeff'+encoded,encoded+'x',encoded.replace('"schema_version":1','"schema_version":1,"schema_version":1'),
  encoded.replace('"seq":3','"seq":NaN'),encoded.replace('"seq":3','"seq":1e999'),
  encoded.replace('SYNTHETIC-INTAKE-044','\\ud800'),'{"x":"\\q"}','['.repeat(22)+'0'+']'.repeat(22)])
  invalid(()=>model.parseIntakeReferenceHistoryJson(value,f.context.intake_id,query));
});
check('gate identity cannot be replayed after begin clear or across independent channels',()=>{
 const h=model.createIntakeReferenceGate(),c=model.createIntakeReferenceGate();
 assert.equal(h.current(null),false);const a=h.begin(),b=h.begin(),other=c.begin();
 assert.equal(h.current(a),false);assert.equal(h.current(b),true);assert.equal(h.current(other),false);
 c.clear();assert.equal(h.current(b),true);h.clear();assert.equal(h.current(b),false);
});
