/*044 A1 strict sanitized DTOs. No Store, HTTP, source read, secret or authority. */
export const INTAKE_REFERENCE_VIEW_MAX_BYTES=2097152;
const INVALID='invalid_intake_reference_view',UNSAFE='intake_reference_view_unrepresentable';
const unsafeToken=Object.freeze({});
const fail=(code=INVALID)=>{throw code===UNSAFE?unsafeToken:Error(INVALID);};
const need=value=>{if(!value)fail();};
const checked=run=>{try{return run();}catch(error){throw Error(error===unsafeToken?UNSAFE:INVALID);}};
const scalarString=value=>need(typeof value==='string'&&!/[\uD800-\uDFFF]/u.test(value));
const encoded=value=>new TextEncoder().encode(value).length;
function plainCopy(input,cap=INTAKE_REFERENCE_VIEW_MAX_BYTES){
 let nodes=0;const visit=(value,depth=0)=>{
  need(++nodes<=200000&&depth<=20);
  if(value===null||typeof value==='boolean')return value;
  if(typeof value==='number'){need(Number.isFinite(value)&&Number.isInteger(value));if(!Number.isSafeInteger(value))fail(UNSAFE);return value;}
  if(typeof value==='string'){scalarString(value);need(value.length<=cap);return value;}
  need(value&&typeof value==='object');const array=Array.isArray(value),proto=Object.getPrototypeOf(value);
  need(array?proto===Array.prototype:proto===Object.prototype||proto===null);
  const keys=Reflect.ownKeys(value),out=array?[]:{};
  if(array){need(value.length<=200000&&keys.length===value.length+1);for(let i=0;i<value.length;i++)need(Object.hasOwn(value,i));}
  for(const key of keys){if(array&&key==='length')continue;const item=Object.getOwnPropertyDescriptor(value,key);
   need(typeof key==='string'&&item.enumerable&&Object.hasOwn(item,'value'));scalarString(key);
   if(!array)need(++nodes<=200000&&depth+1<=20);
   Object.defineProperty(out,key,{value:visit(item.value,depth+1),enumerable:true,writable:true,configurable:true});
  }return out;
 };const out=visit(input);need(encoded(JSON.stringify(out))<=cap);return out;
}
function parse(raw){
 scalarString(raw);need(encoded(raw)<=INTAKE_REFERENCE_VIEW_MAX_BYTES);let p=0,nodes=0;
 const space=()=>{while(p<raw.length&&/[ \t\r\n]/.test(raw[p]))p++;};
 const string=()=>{const start=p++;let escaped=false;while(p<raw.length){const c=raw[p++];
  if(!escaped&&c==='"'){const value=JSON.parse(raw.slice(start,p));scalarString(value);return value;}
  if(!escaped&&c==='\\')escaped=true;else escaped=false;
 }fail();};
 const value=depth=>{need(++nodes<=200000&&depth<=20);space();const c=raw[p];
  if(c==='"')return string();
  if(c==='{'||c==='['){p++;const object=c==='{',out=object?{}:[],end=object?'}':']';space();if(raw[p]===end){p++;return out;}
   while(true){space();let key;if(object){need(raw[p]==='"'&&++nodes<=200000&&depth+1<=20);key=string();need(!Object.hasOwn(out,key));space();need(raw[p++]===':');}
    const item=value(depth+1);if(object)Object.defineProperty(out,key,{value:item,enumerable:true,writable:true,configurable:true});else out.push(item);
    space();const next=raw[p++];if(next===end)break;need(next===',');
   }return out;
  }
  for(const [token,result] of [['true',true],['false',false],['null',null]])if(raw.slice(p,p+token.length)===token){p+=token.length;return result;}
  const regex=/-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y;regex.lastIndex=p;
  const match=regex.exec(raw);need(match);p=regex.lastIndex;
  // Every numeric field in these DTOs is a Python int. Never round a float token.
  need(!/[.eE]/.test(match[0]));const integer=BigInt(match[0]);
  if(integer>BigInt(Number.MAX_SAFE_INTEGER)||integer<BigInt(Number.MIN_SAFE_INTEGER))fail(UNSAFE);
  return Number(match[0]);
 };const result=value(0);space();need(p===raw.length);return plainCopy(result);
}
const exact=(value,keys)=>need(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(' ')===keys.split(' ').sort().join(' '));
const bool=value=>need(typeof value==='boolean');
const integer=(value,min=1,max=Number.MAX_SAFE_INTEGER)=>{need(typeof value==='number'&&Number.isInteger(value));if(!Number.isSafeInteger(value))fail(UNSAFE);need(value>=min&&value<=max);};
const id=(value,max=150)=>need(typeof value==='string'&&value.length>=1&&value.length<=max&&/^[A-Za-z0-9]/.test(value)&&!/[^A-Za-z0-9_.-]/.test(value));
const sha=value=>need(typeof value==='string'&&value.length===64&&!/[^a-f0-9]/.test(value));
const nullable=(value,check)=>{if(value!==null)check(value);};
const list=(value,max)=>need(Array.isArray(value)&&value.length<=max);
const choice=(value,allowed)=>need(allowed.includes(value));
const ordered=values=>need(values.every((value,i)=>i===0||values[i-1]<value));
function timestamp(value){
 scalarString(value);need([...value].length<=128);
 const d=/^([0-9]{4})(?:-([0-9]{2})-([0-9]{2})|([0-9]{2})([0-9]{2})|-W([0-9]{2})(?:-([1-7]))?|W([0-9]{2})([1-7])?)/.exec(value);need(d);
 const year=Number(d[1]);need(year>=1);const leap=year%4===0&&(year%100!==0||year%400===0);
 if(d[6]||d[8]){
  const week=Number(d[6]||d[8]),day=Number(d[7]||d[9]||1),date=new Date(0);
  date.setUTCFullYear(year,0,1);const first=date.getUTCDay();need(week>=1&&week<=(first===4||first===3&&leap?53:52));
  date.setUTCDate(4);date.setUTCDate(4-(date.getUTCDay()+6)%7+(week-1)*7+day-1);need(date.getUTCFullYear()>=1&&date.getUTCFullYear()<=9999);
 }else{
  const month=Number(d[2]||d[4]),day=Number(d[3]||d[5]);need(month>=1&&month<=12);
  need(day>=1&&day<=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]);
 }
 const tail=[...value.slice(d[0].length)];need(tail.length>1);tail.shift();const clock=tail.join('');
 const parts=/^(.+?)(Z|[+-].+)$/.exec(clock);need(parts);
 const time=piece=>{const m=/^([0-9]{2})(?:(?::([0-9]{2})(?::([0-9]{2}))?)|(?:([0-9]{2})([0-9]{2})?))?(?:[.,][0-9]+)?$/.exec(piece);need(m);return [Number(m[1]),Number(m[2]||m[4]||0),Number(m[3]||m[5]||0)];};
 const [hour,minute,second]=time(parts[1]);need(hour<24&&minute<60&&second<60);
 if(parts[2]!=='Z')need(time(parts[2].slice(1)).every(v=>v===0));
}
const BINDINGS=['current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound'];
const REASONS=['analysis_not_completed','legacy_analysis','no_pdf_context','expected_revision_changed','expected_result_changed',
 'analysis_not_ready','profile_changed','delegation_missing','intake_deferred','delegation_evidence_missing','required_questions_open',
 'unread_documents','source_provenance_unconfirmed','preparation_not_ready','current_capture_unavailable','no_reference_head','reference_snapshot_stale'];
function flags(value,keys,positive=[]){exact(value,keys);for(const [key,flag] of Object.entries(value)){bool(flag);need(flag===positive.includes(key));}}
function record(value){
 exact(value,'record_id seq request_id revision origin_job_id reference_receipt_id binding_status expected_snapshot_id append_observation source_modes created_at');
 for(const key of ['record_id','reference_receipt_id','expected_snapshot_id'])sha(value[key]);
 for(const key of ['request_id','origin_job_id'])id(value[key]);for(const key of ['seq','revision'])integer(value[key]);
 choice(value.binding_status,BINDINGS);timestamp(value.created_at);
 const a=value.append_observation;exact(a,'expected_snapshot_id captured_snapshot_id head_before_record_id head_after_record_id head_advanced preparation_ready observed_at');
 sha(a.expected_snapshot_id);for(const key of ['captured_snapshot_id','head_before_record_id','head_after_record_id'])nullable(a[key],sha);
 bool(a.head_advanced);bool(a.preparation_ready);timestamp(a.observed_at);
 need(a.expected_snapshot_id===value.expected_snapshot_id&&a.observed_at===value.created_at&&a.head_advanced===(value.binding_status==='current_at_append'));
 if(a.head_advanced)need(a.head_after_record_id===value.record_id&&a.captured_snapshot_id===a.expected_snapshot_id);
 else need(a.head_after_record_id===a.head_before_record_id);
 const m=value.source_modes;exact(m,'intake_revision_synthetic catalog_synthetic intake_provenance_status');bool(m.intake_revision_synthetic);
 nullable(m.catalog_synthetic,bool);choice(m.intake_provenance_status,['confirmed','unconfirmed','not_assessed']);
}
function context(input){
 if(input===null)return null;const value=plainCopy(input,16384);exact(value,'intake_id revision snapshotGeneration');
 id(value.intake_id);integer(value.revision);integer(value.snapshotGeneration,0);return value;
}
function history(raw,intakeId,query){
 id(intakeId);query=plainCopy(query,16384);exact(query,'limit before_seq');integer(query.limit,1,100);nullable(query.before_seq,integer);
 const value=parse(raw);exact(value,'schema_version kind intake_id available records next_before_seq verification');
 need(value.schema_version===1&&value.kind==='intake_reference_history'&&value.intake_id===intakeId);bool(value.available);
 list(value.records,query.limit);value.records.forEach(record);nullable(value.next_before_seq,integer);
 for(const key of ['record_id','request_id'])need(new Set(value.records.map(row=>row[key])).size===value.records.length);
 flags(value.verification,'record_metadata_verified payloads_reverified original_sources_reverified database_currentness_verified',value.available?['record_metadata_verified']:[]);
 need(value.available||value.records.length===0);
 const seqs=value.records.map(row=>row.seq);need(seqs.every((seq,i)=>(i===0||seqs[i-1]>seq)&&(query.before_seq===null||seq<query.before_seq)));
 if(value.next_before_seq!==null)need(seqs.length===query.limit&&value.next_before_seq===seqs.at(-1));
 return value;
}
function current(raw,intakeId){
 id(intakeId);const value=parse(raw);exact(value,'schema_version kind intake_id available status record reference_summary current_observation reason_codes verification');
 need(value.schema_version===1&&value.kind==='intake_reference_review_current'&&value.intake_id===intakeId);bool(value.available);
 choice(value.status,['current','stale','none','unavailable']);list(value.reason_codes,REASONS.length);value.reason_codes.forEach(code=>choice(code,REASONS));ordered(value.reason_codes);
 for(const [status,reason] of [['unavailable','current_capture_unavailable'],['none','no_reference_head'],['stale','reference_snapshot_stale']])need(value.reason_codes.includes(reason)===(value.status===status));
 const o=value.current_observation;exact(o,'snapshot_id head_record_id preparation_ready observed_at');nullable(o.snapshot_id,sha);nullable(o.head_record_id,sha);bool(o.preparation_ready);timestamp(o.observed_at);
 flags(value.verification,'record_hash_verified database_snapshot_observed reference_source_currentness_verified operational_authority_granted model_execution_verified evaluation_executed',
  value.record===null?['database_snapshot_observed']:['record_hash_verified','database_snapshot_observed']);
 if(value.record===null)need(value.reference_summary===null&&o.head_record_id===null);
 else{
  record(value.record);need(value.available&&value.record.record_id===o.head_record_id&&value.record.binding_status==='current_at_append');
  const r=value.reference_summary;exact(r,'receipt_id status context_id selected_case_ids accepted_reference_count');sha(r.receipt_id);
  need(r.receipt_id===value.record.reference_receipt_id);choice(r.status,['bound','insufficient_evidence']);nullable(r.context_id,sha);
  list(r.selected_case_ids,16);r.selected_case_ids.forEach(v=>id(v,128));ordered(r.selected_case_ids);integer(r.accepted_reference_count,0,256);
  need(r.accepted_reference_count>=r.selected_case_ids.length&&(r.accepted_reference_count===0)===(r.selected_case_ids.length===0));
 }
 need((value.status==='unavailable')===(o.snapshot_id===null));
 if(value.status==='current'||value.status==='stale')need(value.record!==null);
 if(value.status==='none')need(value.record===null);
 if(value.status==='current')need(value.record.expected_snapshot_id===o.snapshot_id&&!value.reason_codes.includes('reference_snapshot_stale'));
 return value;
}
export const validateIntakeReferenceContext=input=>checked(()=>context(input));
export const parseIntakeReferenceHistoryJson=(raw,intakeId,query)=>checked(()=>history(raw,intakeId,query));
export const parseIntakeReferenceCurrentJson=(raw,intakeId)=>checked(()=>current(raw,intakeId));
export function createIntakeReferenceGate(){let current=null;return {begin(){current=Object.freeze({});return current;},clear(){current=null;},current(ticket){return current!==null&&ticket===current;}};}
