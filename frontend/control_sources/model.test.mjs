import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateSummary,validateItems,validateDetail,safeSourceHref,createReadGate,SOURCE_COMMIT,
 DEFAULT_NAVIGATION,parseCatalogFragment,serializeCatalogFragment,createNavigationGate} from './model.mjs';

const read=name=>JSON.parse(fs.readFileSync(new URL('../../'+name,import.meta.url),'utf8'));
const overlay=read('control_sources/registry_overlay.json');
const raw=read('research/equipment-control-2026-10-24/deliverables/model_control_sources.json');
const notes=read('control_sources/review_notes.json').notes;
const item=record=>({item_id:record.item_id,model_id:record.model_id,manufacturer:record.manufacturer,model:record.model,
 scope:record.scope,research_status:record.research_status,public_code_status:record.public_code_status,
 source_count:record.sources.length,equipment_id_count:record.equipment_ids.length,registration_rows:record.registration_rows,
 candidate_virtual_profile_ids:overlay.records.find(row=>row.item_id===record.item_id).candidate_virtual_profile_ids,
 adapter_support_status:'not_assessed',vendor_binary_executed:false,hardware_verified:false});
const list=()=>({schema_version:1,kind:'control_source_items',source_commit:SOURCE_COMMIT,total:3137,offset:0,limit:25,next_offset:25,
 items:raw.toSorted((a,b)=>a.item_id<b.item_id?-1:1).slice(0,25).map(item)});
const summary=()=>({schema_version:1,kind:'control_source_summary',source_commit:SOURCE_COMMIT,catalog_state:'read_only_metadata_catalog',
 item_count:3137,model_count:2867,identity_item_count:270,equipment_id_count:6470,
 scope_counts:{included:1433,excluded_passive:1480,identity_unresolved:176,needs_scope_review:48},
 source_association_count:2260,research_unique_url_count:1624,prior_reference_unique_url_count:83,overlapping_url_count:17,unique_url_count:1690,
 profile_count:64,profile_candidate_counts:overlay.profile_crosswalk.status_counts,adapter_support_status:'not_assessed',
 vendor_binary_executed:false,hardware_verified:false,profile_binding_established:false,registry_snapshot:overlay.registry_snapshot});
const detail=(model='N9030A',itemId=null)=>{
 const source=raw.find(row=>itemId?row.item_id===itemId:row.model===model),meta=structuredClone(overlay.records.find(row=>row.item_id===source.item_id));delete meta.item_id;
 return {schema_version:1,kind:'control_source_detail',source_commit:SOURCE_COMMIT,catalog_state:'read_only_metadata_catalog',
 record:{research_record:source,...meta},profile_candidates:overlay.profile_crosswalk.profiles.filter(profile=>[...profile.normalized_label_candidates,...profile.same_model_other_manufacturer_candidates].some(row=>row.item_id===source.item_id)).toSorted((a,b)=>a.profile_id<b.profile_id?-1:1),
 review_notes:notes.filter(note=>note.item_ids.includes(source.item_id))};
};

test('summary retains research counts snapshot and separate unsupported states',()=>{
 const value=summary(),copy=validateSummary(value);assert.deepEqual(copy,value);copy.registry_snapshot.path='changed';assert.notEqual(value.registry_snapshot.path,'changed');
 for(const mutate of [v=>v.hardware_verified=true,v=>v.profile_binding_established=true,v=>v.adapter_support_status='supported',v=>v.scope_counts.included++,v=>delete v.registry_snapshot.sha256]){
  const bad=summary();mutate(bad);assert.throws(()=>validateSummary(bad),/invalid_catalog_response/);
 }
});
test('list enforces bounded stable pages and preserves null model identities',()=>{
 assert.deepEqual(validateItems(list()),list());
 const source=raw.find(row=>row.model_id===null),value={...list(),total:1,limit:25,next_offset:null,items:[item(source)]};
 assert.equal(validateItems(value).items[0].model_id,null);
 assert.deepEqual(validateItems({...list(),total:0,offset:25,items:[],next_offset:null}).items,[]);
 for(const mutate of [v=>v.items.reverse(),v=>v.items.pop(),v=>v.next_offset=24,v=>v.limit=101,v=>v.total=Infinity,v=>v.items[0].model_id='',v=>v.items[0].hardware_verified=true]){
  const bad=list();mutate(bad);assert.throws(()=>validateItems(bad),/invalid_catalog_response/);
 }
});
test('real N9030A DMM6500 N1921A detail associations notes and source licenses survive',()=>{
 for(const name of ['N9030A','DMM6500','N1921A']){const value=detail(name);assert.deepEqual(validateDetail(value,value.record.research_record.item_id),value);}
 const value=detail('DMM6500');assert(value.review_notes.length);assert.equal(value.record.adapter_support_status,'not_assessed');
});
test('every fixed research detail including all 270 null model identities remains readable',()=>{
 for(const source of raw){const value=detail(undefined,source.item_id);assert.doesNotThrow(()=>validateDetail(value,source.item_id),source.item_id);}
});
test('wrong detail selection flags schema or source associations cannot publish',()=>{
 const value=detail();assert.throws(()=>validateDetail(value,'different'),/invalid_catalog_response/);
 for(const mutate of [v=>v.schema_version=2,v=>v.source_commit='0'.repeat(40),v=>v.extra=true,v=>v.record.hardware_verified=true,
  v=>delete v.record.research_record.sources[0].license,v=>v.record.registry_reconciliation.item_id='different',
  v=>v.review_notes[0].item_ids=['different'],v=>v.record.research_record.hardware_verified=true]){
  const bad=structuredClone(value);mutate(bad);assert.throws(()=>validateDetail(bad,value.record.research_record.item_id),/invalid_catalog_response/);
 }
});
test('only detached enumerable JSON data is accepted without executing getters',()=>{
 let called=false;const bad=summary();Object.defineProperty(bad,'kind',{enumerable:true,get(){called=true;throw Error('PRIVATE');}});
 assert.throws(()=>validateSummary(bad),/^Error: invalid_catalog_response$/);assert.equal(called,false);
 const hidden=summary();Object.defineProperty(hidden,'hardware_verified',{value:false,enumerable:false});assert.throws(()=>validateSummary(hidden),/invalid_catalog_response/);
 const holes=list();delete holes.items[0];assert.throws(()=>validateItems(holes),/invalid_catalog_response/);
});
test('untrusted text survives while only explicit safe HTTP links are enabled',()=>{
 const value=detail();value.record.research_record.notes='<img src=x onerror=alert(1)>';assert.equal(validateDetail(value,value.record.research_record.item_id).record.research_record.notes,value.record.research_record.notes);
 assert.equal(safeSourceHref('https://example.com/a?q=1#part'),'https://example.com/a?q=1#part');
 for(const url of ['javascript:alert(1)','data:text/html,x','file:///secret','//example.com','https://user:password@example.com','https://example.com/\nsecret'])assert.equal(safeSourceHref(url),null);
});
test('list generations and selection IDs jointly reject late detail and list responses',()=>{
 const gate=createReadGate(),first=gate.beginList();assert(gate.listCurrent(first));
 const a=gate.beginDetail('MOD-a'),b=gate.beginDetail('MOD-b');assert(!gate.detailCurrent(a));assert(gate.detailCurrent(b));
 gate.beginList();assert(!gate.detailCurrent(b));assert(!gate.listCurrent(first));
 const c=gate.beginDetail('MOD-c');assert(gate.detailCurrent(c));assert.throws(()=>gate.beginDetail('../x'),/invalid_catalog_response/);
});
test('fragment round trips have fixed order omitted defaults and RFC3986 encoding',()=>{
 assert.deepEqual(parseCatalogFragment(''),DEFAULT_NAVIGATION);assert.deepEqual(parseCatalogFragment('#'),DEFAULT_NAVIGATION);
 assert.equal(serializeCatalogFragment({...DEFAULT_NAVIGATION}),'');
 const value={...DEFAULT_NAVIGATION,query:'한글 A+B = &',scope:'included',model_id:'MOD-a',equipment_id:'EQ-1',profile_id:'fsv40',offset:25,limit:10,item_id:'MOD-selected'};
 const hash='#query=%ED%95%9C%EA%B8%80%20A%2BB%20%3D%20%26&scope=included&model_id=MOD-a&equipment_id=EQ-1&profile_id=fsv40&offset=25&limit=10&item_id=MOD-selected';
 assert.equal(serializeCatalogFragment(value),hash);assert.deepEqual(parseCatalogFragment(hash),value);
 assert.equal(parseCatalogFragment('#query=A+B').query,'A+B');
 assert.equal(serializeCatalogFragment(parseCatalogFragment('#limit=025&offset=000&query=')),'');
 assert.equal(serializeCatalogFragment({...DEFAULT_NAVIGATION,query:"!'()*"}),'#query=%21%27%28%29%2A');
});
test('fragment rejection is bounded strict and uses one fixed public error',()=>{
 for(const hash of [null,{},'query=x','#query','#=x','#query=a&query=b','#query=a&%71uery=b','#constructor=x','#__proto__=x','#unknown=x',
  '#query=%','#query=%xz','#query=%FF','#query=%C0%AF','#query=%ED%A0%80','#query=%00','#query=%0A','#query=\ud800',
  '#scope=all','#scope=','#model_id=','#item_id=','#profile_id=a%2Fb','#offset=','#offset=true','#offset=-1','#offset=1.5','#offset=%2B1','#offset=1000001','#limit=0','#limit=101',
  '#query='+ 'a'.repeat(201),'#query=x&','#'+ 'x'.repeat(4096)]) {
  assert.throws(()=>parseCatalogFragment(hash),/^Error: invalid_catalog_navigation$/);
 }
});
test('fragment decode occurs once and Unicode count agrees with Python text length',()=>{
 assert.equal(parseCatalogFragment('#query=%252Ftmp%252Ffile').query,'%2Ftmp%2Ffile');
 assert.equal(serializeCatalogFragment(parseCatalogFragment('#query=%252Ftmp%252Ffile')),'#query=%252Ftmp%252Ffile');
 assert.throws(()=>parseCatalogFragment('#item_id=MOD%252F1'),/invalid_catalog_navigation/);
 const value={...DEFAULT_NAVIGATION,query:'😀'.repeat(200)};assert.deepEqual(parseCatalogFragment(serializeCatalogFragment(value)),value);
 assert.throws(()=>serializeCatalogFragment({...value,query:value.query+'😀'}),/invalid_catalog_navigation/);
 const oversized='#query='+encodeURIComponent(value.query)+['model_id','equipment_id','profile_id','item_id'].map(key=>'&'+key+'='+'%41'.repeat(150)).join('');
 assert(Buffer.byteLength(oversized,'utf8')>4096);assert.throws(()=>parseCatalogFragment(oversized),/invalid_catalog_navigation/);
});
test('only eight typed navigation fields can enter a link and getters never execute',()=>{
 for(const bad of [{...DEFAULT_NAVIGATION,offset:true},{...DEFAULT_NAVIGATION,limit:Infinity},{...DEFAULT_NAVIGATION,limit:0},
  {...DEFAULT_NAVIGATION,source_path:'/private/raw'},{...DEFAULT_NAVIGATION,item_id:'../../file'},{...DEFAULT_NAVIGATION,query:17}])assert.throws(()=>serializeCatalogFragment(bad),/invalid_catalog_navigation/);
 let called=false;const bad={...DEFAULT_NAVIGATION};Object.defineProperty(bad,'query',{enumerable:true,get(){called=true;throw Error('PRIVATE');}});
 assert.throws(()=>serializeCatalogFragment(bad),/^Error: invalid_catalog_navigation$/);assert.equal(called,false);
 const copy=parseCatalogFragment('');copy.offset=4;assert.equal(DEFAULT_NAVIGATION.offset,0);
});
test('navigation events coalesce by canonical state while explicit refresh invalidates stale tickets',()=>{
 const gate=createNavigationGate(),first=gate.begin(parseCatalogFragment('#offset=000'));
 assert(first);assert(gate.current(first));assert.equal(gate.begin(parseCatalogFragment('')),null);assert(gate.current(first));
 const next=gate.begin({...DEFAULT_NAVIGATION,item_id:'MOD-b'});assert(!gate.current(first));assert(gate.current(next));
 assert.equal(gate.begin(parseCatalogFragment('#item_id=MOD-b')),null);
 const refreshed=gate.begin(next.state,{force:true});assert(refreshed);assert(!gate.current(next));assert(gate.current(refreshed));
 assert(Object.isFrozen(refreshed) && Object.isFrozen(refreshed.state));
});
