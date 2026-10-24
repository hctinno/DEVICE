/*052 feature-local controller. No Store, producer, authority or session creation. */
const model=await import(new URL(import.meta.url.startsWith('file:')?'../intake_references/model.mjs':'../intake-references/model.mjs',import.meta.url));
const INVALID='intake_reference_ui_invalid_request',UNAVAILABLE='intake_reference_ui_unavailable',UNSAFE='intake_reference_view_unrepresentable';
const faults=new WeakMap(),encoder=new TextEncoder();
const fail=(code=UNAVAILABLE,status=0)=>{const e=Error(code);faults.set(e,{code,status});throw e;};
const need=value=>{if(!value)fail();};
const copy=value=>structuredClone(value);
const freeze=value=>{if(value&&typeof value==='object'){for(const x of Object.values(value))freeze(x);Object.freeze(value);}return value;};
const same=(a,b)=>a!==null&&b!==null&&a.intake_id===b.intake_id&&a.revision===b.revision&&a.snapshotGeneration===b.snapshotGeneration;
const origin=(a,b)=>a&&b&&a.intake_id===b.intake_id&&a.revision===b.revision;
const bytes=value=>encoder.encode(value).length;
const scalar=value=>need(typeof value==='string'&&!/[\uD800-\uDFFF]/u.test(value));
const exact=(value,keys)=>{need(value&&typeof value==='object'&&!Array.isArray(value));const expected=keys.split(' ');
 need(Object.keys(value).length===expected.length&&expected.every(k=>Object.hasOwn(value,k)));};
const sha=value=>need(typeof value==='string'&&/^[a-f0-9]{64}$/.test(value));
const nullable=(value,check)=>{if(value!==null)check(value);};
const id=(value,max=150)=>need(typeof value==='string'&&value.length<=max&&/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(value));
const integer=(value,min=1,max=Number.MAX_SAFE_INTEGER)=>need(Number.isSafeInteger(value)&&value>=min&&value<=max);
const bool=value=>need(typeof value==='boolean');
const choice=(value,values)=>need(values.includes(value));
const BINDINGS=['current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound'];
const REASONS=['analysis_not_ready','profile_changed','delegation_missing','intake_deferred','delegation_evidence_missing','required_questions_open','unread_documents','source_provenance_unconfirmed','preparation_not_ready'];
const KNOWN=new Set([...['unconfigured','invalid_request','input_limit','access_denied','session_unavailable','unavailable'].map(x=>'intake_reference_ui_'+x),
 ...['unconfigured','invalid_request','input_limit','access_denied','review_input_unavailable','prepared_unavailable','request_conflict','unavailable'].map(x=>'intake_reference_review_host_'+x)]);
function ownOptions(value){
 try{need(value&&[Object.prototype,null].includes(Object.getPrototypeOf(value)));need(Reflect.ownKeys(value).length===2);
  const out={};for(const name of ['onChange','onRegistered']){const d=Object.getOwnPropertyDescriptor(value,name);need(d&&d.enumerable&&Object.hasOwn(d,'value')&&typeof d.value==='function');out[name]=d.value;}return out;
 }catch{fail(INVALID);}
}
function json(raw,cap,depthMax,nodesMax){
 scalar(raw);need(bytes(raw)<=cap);let p=0,nodes=0;
 const space=()=>{while(/[ \t\r\n]/.test(raw[p]||'\u0000'))p++;};
 const string=()=>{const start=p++;let escaped=false;while(p<raw.length){const c=raw[p++];
  if(!escaped&&c==='"'){const out=JSON.parse(raw.slice(start,p));scalar(out);return out;}if(!escaped&&c==='\\')escaped=true;else escaped=false;}fail();};
 const value=depth=>{need(++nodes<=nodesMax&&depth<=depthMax);space();const c=raw[p];
  if(c==='"')return string();
  if(c==='{'||c==='['){p++;const object=c==='{',out=object?{}:[],end=object?'}':']';space();if(raw[p]===end){p++;return out;}
   while(true){space();let key;if(object){need(raw[p]==='"'&&++nodes<=nodesMax&&depth+1<=depthMax);key=string();need(!Object.hasOwn(out,key));space();need(raw[p++]===':');}
    const x=value(depth+1);if(object)Object.defineProperty(out,key,{value:x,enumerable:true,writable:true,configurable:true});else out.push(x);
    space();const next=raw[p++];if(next===end)break;need(next===',');}return out;
  }
  for(const [token,out] of [['true',true],['false',false],['null',null]])if(raw.slice(p,p+token.length)===token){p+=token.length;return out;}
  const pattern=/-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y;pattern.lastIndex=p;const match=pattern.exec(raw);need(match);p=pattern.lastIndex;
  need(!/[.eE]/.test(match[0]));const n=BigInt(match[0]);if(n>BigInt(Number.MAX_SAFE_INTEGER)||n<BigInt(Number.MIN_SAFE_INTEGER))fail(UNSAFE);return Number(match[0]);
 };const result=value(0);space();need(p===raw.length);return result;
}
function timestamp(value){
 scalar(value);need([...value].length<=128);
 const d=/^([0-9]{4})(?:-([0-9]{2})-([0-9]{2})|([0-9]{2})([0-9]{2})|-W([0-9]{2})(?:-([1-7]))?|W([0-9]{2})([1-7])?)/.exec(value);need(d);
 const year=Number(d[1]);need(year>=1);const leap=year%4===0&&(year%100!==0||year%400===0);
 if(d[6]||d[8]){const week=Number(d[6]||d[8]),day=Number(d[7]||d[9]||1),date=new Date(0);date.setUTCFullYear(year,0,1);const first=date.getUTCDay();
  need(week>=1&&week<=(first===4||first===3&&leap?53:52));date.setUTCDate(4);date.setUTCDate(4-(date.getUTCDay()+6)%7+(week-1)*7+day-1);need(date.getUTCFullYear()>=1&&date.getUTCFullYear()<=9999);
 }else{const month=Number(d[2]||d[4]),day=Number(d[3]||d[5]);need(month>=1&&month<=12&&day>=1&&day<=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]);}
 const tail=[...value.slice(d[0].length)];need(tail.length>1);tail.shift();const parts=/^(.+?)(Z|[+-].+)$/.exec(tail.join(''));need(parts);
 const clock=piece=>{const m=/^([0-9]{2})(?:(?::([0-9]{2})(?::([0-9]{2}))?)|(?:([0-9]{2})([0-9]{2})?))?(?:[.,][0-9]+)?$/.exec(piece);need(m);return [Number(m[1]),Number(m[2]||m[4]||0),Number(m[3]||m[5]||0)];};
 const t=clock(parts[1]);need(t[0]<24&&t[1]<60&&t[2]<60);if(parts[2]!=='Z')need(clock(parts[2].slice(1)).every(n=>n===0));
}
function flags(value,positive,negative,variable=[]){exact(value,[...positive,...negative,...variable].join(' '));
 for(const v of Object.values(value))bool(v);for(const key of positive)need(value[key]===true);for(const key of negative)need(value[key]===false);}
function preview(value,intakeId){
 need(bytes(JSON.stringify(value))<=32768);
 exact(value,'schema_version kind intake_id preparation_id observation preparation_ready reason_codes review_status selection source_modes verification');
 need(value.schema_version===1&&value.kind==='intake_reference_review_preview'&&value.intake_id===intakeId);id(value.intake_id);sha(value.preparation_id);
 const o=value.observation;exact(o,'kind snapshot_id head_record_id observed_at');need(o.kind==='paired_public_reads');sha(o.snapshot_id);nullable(o.head_record_id,sha);timestamp(o.observed_at);
 bool(value.preparation_ready);need(Array.isArray(value.reason_codes)&&value.reason_codes.length<=9);
 value.reason_codes.forEach(x=>choice(x,REASONS));need(value.reason_codes.every((x,i)=>i===0||value.reason_codes[i-1]<x));need(value.preparation_ready===(value.reason_codes.length===0));
 choice(value.review_status,['bound','insufficient_evidence']);const s=value.selection;exact(s,'context_id corpus_id requested_case_ids status accepted_reference_count receipt_id');
 nullable(s.context_id,sha);nullable(s.corpus_id,x=>id(x,128));need(Array.isArray(s.requested_case_ids)&&s.requested_case_ids.length<=16);s.requested_case_ids.forEach(x=>id(x,128));
 need(new Set(s.requested_case_ids).size===s.requested_case_ids.length);choice(s.status,['selected','no_candidate','unknown']);integer(s.accepted_reference_count,0,256);sha(s.receipt_id);
 const m=value.source_modes;exact(m,'intake_revision_synthetic catalog_synthetic intake_provenance_status');bool(m.intake_revision_synthetic);nullable(m.catalog_synthetic,bool);choice(m.intake_provenance_status,['confirmed','unconfirmed']);
 flags(value.verification,['reference_receipt_validated','retained_snapshot_observed'],['reference_source_currentness_verified','operational_authority_granted','model_execution_verified','evaluation_executed']);return value;
}
function envelope(raw,intakeId){const value=json(raw,65536,16,10000);exact(value,'schema_version kind handle_id append_request_id expires_in_seconds preview');
 need(value.schema_version===1&&value.kind==='intake_reference_preparation_handle');sha(value.handle_id);id(value.append_request_id);integer(value.expires_in_seconds,1,900);preview(value.preview,intakeId);return value;}
function registration(raw,request){const v=json(raw,2097152,20,200000);exact(v,'schema_version kind request_id record_id seq stored replayed binding_status append_observation verification');
 need(v.schema_version===1&&v.kind==='intake_reference_registration'&&v.request_id===request.request_id&&v.stored===true);sha(v.record_id);integer(v.seq);bool(v.replayed);choice(v.binding_status,BINDINGS);
 const o=v.append_observation;exact(o,'expected_snapshot_id captured_snapshot_id head_before_record_id head_after_record_id head_advanced preparation_ready observed_at');
 sha(o.expected_snapshot_id);for(const key of ['captured_snapshot_id','head_before_record_id','head_after_record_id'])nullable(o[key],sha);bool(o.head_advanced);bool(o.preparation_ready);timestamp(o.observed_at);
 need(o.expected_snapshot_id===request.expected_snapshot_id&&o.head_advanced===(v.binding_status==='current_at_append'));
 if(o.head_advanced)need(o.captured_snapshot_id===o.expected_snapshot_id&&o.head_after_record_id===v.record_id);else need(o.head_after_record_id===o.head_before_record_id);
 flags(v.verification,['record_hash_verified','parent_revalidated_at_append','origin_revalidated_at_append'],['operational_authority_granted','model_execution_verified','evaluation_executed','independent_evaluation_approved'],['mutable_state_verified_at_append']);
 const {request_id,...publicValue}=v;return publicValue;
}

export function createIntakeReferenceActionsController(options){
 let callbacks=ownOptions(options),alive=true,notifying=false,context=null,pending=false,phase='idle',error=null;
 let csrf=null,input=null,prepareAllowed=false,appendAllowed=false,slot=null,previewGood=null,registrationGood=null;
 let epoch={},active=null,expiryTimer=null;
 const clearCache=()=>{csrf=null;input=null;prepareAllowed=false;appendAllowed=false;};
 const unknown=()=>['uncertain','replacement_unknown','prepare_unknown'].includes(phase);
 const emit=()=>{
  if(!alive)return;
  const state=freeze(copy({context,phase,pending,prepare_allowed:prepareAllowed,append_allowed:appendAllowed,
   preview:previewGood&&same(previewGood.context,context)?previewGood.value:null,
   registration:registrationGood&&same(registrationGood.context,context)?registrationGood.value:null,error_code:error}));
  notifying=true;try{callbacks.onChange(state);}catch{}finally{notifying=false;}
 };
 const markUnknown=op=>{
  if(!op?.dispatched){if(op&&['uncertain','replacement_unknown','prepare_unknown'].includes(op.priorPhase))phase=op.priorPhase;return;}
  if(op.kind==='append'||op.kind==='replay'){if(slot)slot.state='uncertain';phase='uncertain';}
  else if(op.kind==='prepare'){phase=op.replace?'replacement_unknown':'prepare_unknown';if(slot&&op.replace)slot.state='replacement_unknown';}
 };
 const invalidate=(change)=>{
  const op=active;markUnknown(op);epoch={};active=null;clearCache();change();emit();op?.controller.abort();
 };
 const rejectReentry=()=>{if(notifying)fail(INVALID);};
 const setContext=value=>{
  if(!alive)return;rejectReentry();let next;
  try{next=model.validateIntakeReferenceContext(value);}catch{
   invalidate(()=>{context=null;pending=true;error=INVALID;if(!unknown())phase='error';});return;
  }
  if(same(context,next))return;
  invalidate(()=>{context=next;error=null;if(!unknown())phase=slot?.state||'idle';});
 };
 const setPending=value=>{
  if(!alive)return;rejectReentry();
  if(typeof value!=='boolean'){invalidate(()=>{context=null;pending=true;error=INVALID;if(!unknown())phase='error';});return;}
  if(value)invalidate(()=>{pending=true;error=null;if(!unknown())phase=slot?.state||'idle';});
  else{pending=false;emit();}
 };
 const retire=()=>{slot=null;clearTimeout(expiryTimer);expiryTimer=null;phase='retired';error=null;};
 const expire=()=>{
  if(!slot||performance.now()<slot.deadline)return false;
  const op=active;epoch={};active=null;clearCache();retire();emit();op?.controller.abort();return true;
 };
 const current=op=>alive&&!pending&&active===op&&epoch===op.epoch&&same(context,op.context);
 const valid=op=>current(op)&&!op.controller.signal.aborted;
 const guard=op=>{if(!valid(op)||performance.now()>=op.deadline)fail();};
 const registered=op=>{
  if(!valid(op))return;notifying=true;try{callbacks.onRegistered(freeze(copy(op.context)));}catch{}finally{notifying=false;}
 };
 async function wire(op,path,{body=null,cap=2097152}={}){
  guard(op);let reader=null;const signal=op.controller.signal;
  let rejectAbort;const aborted=new Promise((resolve,reject)=>{rejectAbort=reject;});
  const stop=()=>{try{fail();}catch(e){rejectAbort(e);}if(reader)void reader.cancel().catch(()=>{});};
  signal.addEventListener('abort',stop,{once:true});const timer=setTimeout(()=>{
   if(current(op)){markUnknown(op);clearCache();if(!op.dispatched&&!unknown())phase='error';error=UNAVAILABLE;op.timeout=true;emit();}
   op.controller.abort();
  },Math.max(1,op.deadline-performance.now()));
  const work=async()=>{
   guard(op);const headers={Accept:'application/json'};
   const config={method:body===null?'GET':'POST',signal,credentials:'same-origin',cache:'no-store',redirect:'error',headers};
   if(body!==null){need(bytes(body)<=16384);headers['Content-Type']='application/json; charset=utf-8';headers['X-Intake-Reference-CSRF']=csrf;config.body=body;op.dispatched=true;}
   const response=await fetch(path,config);guard(op);
   const type=response.headers.get('Content-Type'),length=response.headers.get('Content-Length');
   if(!type||!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(type)||length!==null&&(!/^[0-9]+$/.test(length)||BigInt(length)>BigInt(cap))){if(response.body)void response.body.cancel().catch(()=>{});fail();}
   need(response.body);reader=response.body.getReader();const chunks=[];let count=0,complete=false;
   try{while(true){guard(op);const item=await reader.read();guard(op);if(item.done){complete=true;break;}need(item.value instanceof Uint8Array&&item.value.byteLength<=cap-count);count+=item.value.byteLength;chunks.push(item.value);}
    const b=new Uint8Array(count);let offset=0;for(const c of chunks){b.set(c,offset);offset+=c.byteLength;}need(!(b[0]===239&&b[1]===187&&b[2]===191));
    const raw=new TextDecoder('utf-8',{fatal:true}).decode(b);guard(op);
    if(!response.ok){const e=json(raw,cap,20,200000);exact(e,'error');exact(e.error,'code');const code=KNOWN.has(e.error.code)?e.error.code:UNAVAILABLE;fail(code,response.status);}
    return {raw,headers:response.headers};
   }finally{if(!complete)void reader.cancel().catch(()=>{});reader.releaseLock();reader=null;}
  };
  try{return await Promise.race([work(),aborted]);}finally{clearTimeout(timer);signal.removeEventListener('abort',stop);}
 }
 async function bootstrap(op){
  phase='capabilities_pending';error=null;emit();guard(op);
  const result=await wire(op,`/api/intake-references/${op.context.intake_id}/history?limit=1`);guard(op);
  try{model.parseIntakeReferenceHistoryJson(result.raw,op.context.intake_id,{limit:1,before_seq:null});}
  catch(e){if(Object.getOwnPropertyDescriptor(e||{},'message')?.value===UNSAFE)fail(UNSAFE);fail();}
  const read=result.headers.get('X-Intake-Reference-Read-Allowed'),token=result.headers.get('X-Intake-Reference-CSRF');
  const p=result.headers.get('X-Intake-Reference-Prepare-Allowed'),a=result.headers.get('X-Intake-Reference-Append-Allowed'),r=result.headers.get('X-Intake-Reference-Review-Input');
  need(['true','false'].includes(read)&&['true','false'].includes(p)&&['true','false'].includes(a));
  if(read==='true')sha(token);else need(token===null&&p==='false'&&a==='false');
  if(p==='true'){need(read==='true');sha(r);}else need(a==='false'&&r===null);
  guard(op);csrf=token;input=r;prepareAllowed=p==='true';appendAllowed=a==='true';
  if(slot&&token!==null&&slot.marker!==token){retire();emit();return false;}
  phase=slot?.state||(['uncertain','replacement_unknown','prepare_unknown'].includes(op.priorPhase)?op.priorPhase:prepareAllowed?'idle':'unconfigured');error=null;emit();guard(op);return true;
 }
 async function action(kind){
  if(!alive)return;rejectReentry();
  if(expire())return;
  if(active){error=UNAVAILABLE;emit();return;}
  if(pending||context===null){error=INVALID;if(!unknown()&&phase!=='retired')phase='error';emit();return;}
  if(kind==='prepare'&&(slot?.state==='uncertain'||phase==='uncertain')){error=INVALID;emit();return;}
  if(kind==='append'||kind==='replay'){
   if(!slot||!origin(slot.origin,context)||!['ready','recorded','uncertain'].includes(slot.state)||phase==='replacement_unknown'||phase==='prepare_unknown'){
    error=INVALID;if(!unknown())phase='error';emit();return;
   }
   if(kind==='append'&&slot.state!=='ready'){error=INVALID;emit();return;}
   if(kind==='replay'&&slot.state==='ready'){error=INVALID;emit();return;}
  }
  const op={kind,context:copy(context),epoch,controller:new AbortController(),deadline:performance.now()+35000,dispatched:false,replace:false,priorPhase:phase};active=op;
  try{
   if(kind!=='append'&&!(await bootstrap(op)))return;guard(op);
   if(kind==='capabilities')return;
   if(kind==='prepare'){
    if(!prepareAllowed||!csrf||!input)return;
    op.replace=!!slot&&slot.origin.intake_id===context.intake_id&&['ready','recorded'].includes(slot.state)&&!['replacement_unknown','prepare_unknown'].includes(phase);
    const body=JSON.stringify({schema_version:1,review_input_id:input,replace_handle_id:op.replace?slot.request.handle_id:null});
    phase='preparing';error=null;emit();guard(op);const started=performance.now();
    const result=await wire(op,`/api/intake-references/${op.context.intake_id}/prepare`,{body,cap:65536});guard(op);
    const v=envelope(result.raw,op.context.intake_id);guard(op);const p=v.preview;
    const request={schema_version:1,handle_id:v.handle_id,intake_id:op.context.intake_id,request_id:v.append_request_id,
     preparation_id:p.preparation_id,expected_snapshot_id:p.observation.snapshot_id,expected_head_record_id:p.observation.head_record_id};
    clearTimeout(expiryTimer);slot={origin:{intake_id:op.context.intake_id,revision:op.context.revision},marker:csrf,request,deadline:started+v.expires_in_seconds*1000,state:'ready'};
    expiryTimer=setTimeout(()=>{if(alive)expire();},Math.max(1,slot.deadline-performance.now()));
    previewGood={context:copy(op.context),value:p};phase='ready';error=null;emit();
   }else{
    if(!appendAllowed||!csrf){error=INVALID;emit();return;}
    const request=slot.request;phase='appending';error=null;emit();guard(op);
    const result=await wire(op,`/api/intake-references/${op.context.intake_id}/append`,{body:JSON.stringify(request)});guard(op);
    const value=registration(result.raw,request);guard(op);slot.state='recorded';phase='recorded';error=null;registrationGood={context:copy(op.context),value};emit();registered(op);
   }
  }catch(e){
   if(!current(op)||op.timeout)return;
   const f=faults.get(e)||{code:UNAVAILABLE,status:0};clearCache();
   if(f.status===410&&f.code==='intake_reference_review_host_prepared_unavailable')retire();
   else{markUnknown(op);if(!op.dispatched&&!unknown())phase='error';}
   error=f.code;emit();
   op.controller.abort();
  }finally{if(active===op)active=null;}
 }
 const destroy=()=>{
  if(!alive)return;alive=false;epoch={};const op=active;active=null;clearCache();clearTimeout(expiryTimer);expiryTimer=null;
  slot=null;previewGood=null;registrationGood=null;context=null;callbacks=null;op?.controller.abort();
 };
 return Object.freeze({setContext,setPending,refreshCapabilities:()=>action('capabilities'),prepare:()=>action('prepare'),append:()=>action('append'),replay:()=>action('replay'),destroy});
}

function timeLabel(value){
 const d=/^([0-9]{4})(?:-([0-9]{2})-([0-9]{2})|([0-9]{2})([0-9]{2})|-W([0-9]{2})(?:-([1-7]))?|W([0-9]{2})([1-7])?)/.exec(value);
 const date=new Date(0),year=Number(d[1]);
 if(d[6]||d[8]){date.setUTCFullYear(year,0,4);date.setUTCDate(4-(date.getUTCDay()+6)%7+(Number(d[6]||d[8])-1)*7+Number(d[7]||d[9]||1)-1);}
 else date.setUTCFullYear(year,Number(d[2]||d[4])-1,Number(d[3]||d[5]));
 const tail=[...value.slice(d[0].length)];tail.shift();const clock=tail.join('').split(/[Z+-]/,1)[0];
 const t=/^([0-9]{2})(?:(?::([0-9]{2})(?::([0-9]{2}))?)|(?:([0-9]{2})([0-9]{2})?))?(?:[.,]([0-9]+))?$/.exec(clock);
 date.setUTCHours(Number(t[1]),Number(t[2]||t[4]||0),Number(t[3]||t[5]||0),Number((t[6]||'').slice(0,3).padEnd(3,'0')));
 return value+' · '+new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'short',timeStyle:'medium'}).format(date)+' KST';
}
export function createIntakeReferenceActionsReview(container){
 let doc;try{doc=container.ownerDocument;need(container instanceof doc.defaultView.HTMLElement);}catch{fail(INVALID);}
 let alive=true,current={context:null,phase:'idle',pending:false,prepare_allowed:false,append_allowed:false,preview:null,registration:null,error_code:null};
 let lastPreview=null,lastRegistration=null;
 const el=(tag,cls='',text)=>{const node=doc.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
 const root=el('section','reference-actions-review panel');root.setAttribute('aria-label','참고 검토 준비와 등록');
 const selection=el('p','ra-selection mono','접수를 선택하세요.'),status=el('p','ra-status','아직 준비하지 않았습니다.');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 const controls=el('div','ra-controls');
 const buttons={capabilities:el('button','button ra-capabilities','준비 가능 여부 다시 확인'),prepare:el('button','button ra-prepare','검토 준비'),
  append:el('button','button ra-append','참고 이력 등록'),replay:el('button','button ra-replay','원래 요청 재전송')};
 for(const button of Object.values(buttons)){button.type='button';controls.append(button);}
 const columns=el('div','ra-columns'),pSection=el('section'),rSection=el('section');
 const pNote=el('p','ra-note'),rNote=el('p','ra-note'),pBody=el('div','ra-preview'),rBody=el('div','ra-registration');
 pSection.append(el('h3','','검토 준비 관측'),pNote,pBody);rSection.append(el('h3','','참고 등록 관측'),rNote,rBody);columns.append(pSection,rSection);
 root.append(el('h2','','참고 검토 · 준비와 등록'),selection,
  el('p','ra-note','보존자료와 참고 결합을 확인하고 명시적으로 참고 이력에 등록합니다. 시험 착수 권한은 변경되지 않습니다.'),controls,status,
  el('p','ra-note','서버의 준비 기한을 따릅니다. 연결이 바뀌거나 응답을 확인하지 못하면 이력을 먼저 확인하세요.'),columns);container.append(root);
 const literal=value=>value===null?'null':Array.isArray(value)?value.join(', '):String(value);
 const fields=items=>{const dl=el('dl','ra-fields');for(const [key,value] of items){const row=el('div');row.append(el('dt','',key),el('dd','mono',literal(value)));dl.append(row);}return dl;};
 const reasonLabels={analysis_not_ready:'분석 준비 미완료',profile_changed:'분석 기준 변경',delegation_missing:'진행 위임 기록 없음',intake_deferred:'접수 보류',
  delegation_evidence_missing:'위임 근거 미확인',required_questions_open:'필수 확인 사항 미해결',unread_documents:'미확인 문서 있음',
  source_provenance_unconfirmed:'자료 출처 미확인',preparation_not_ready:'준비 조건 미충족'};
 const bindingLabels={current_at_append:'등록 당시 일치',historical_provided:'과거 자료 등록',preparation_unverified:'준비 미검증',head_conflict:'현재 등록 변경 감지',reference_unbound:'참고 결합 부족'};
 function paintPreview(value){
  const s=value.selection,o=value.observation;const fragment=doc.createDocumentFragment();
  fragment.append(fields([['준비 조건',value.preparation_ready],['참고 검토 상태',value.review_status],['관측 방식',o.kind],['관측 시각',timeLabel(o.observed_at)],
   ['선택 사례',s.requested_case_ids],['받아들인 참고 수',s.accepted_reference_count],['선택 상태',s.status],['접수 합성 여부',value.source_modes.intake_revision_synthetic],
   ['Catalog 합성 여부',value.source_modes.catalog_synthetic],['자료 출처 상태',value.source_modes.intake_provenance_status]]));
  fragment.append(el('p','ra-note',value.reason_codes.length?'준비 조건 미충족: '+value.reason_codes.map(x=>(reasonLabels[x]||x)+' · '+x).join(', '):'열린 준비 사유가 없습니다.'));
  fragment.append(fields(Object.entries(value.verification)));return fragment;
 }
 function paintRegistration(value){
  const fragment=doc.createDocumentFragment(),o=value.append_observation;
  fragment.append(el('h4','',(bindingLabels[value.binding_status]||value.binding_status)+' · '+value.binding_status),
   fields([['이력 번호',value.seq],['기록 ID',value.record_id],['저장 응답 확인',value.stored],['원래 요청 재전송 결과',value.replayed],
    ['현재 등록 갱신',o.head_advanced],['당시 준비 조건',o.preparation_ready],['등록 당시 관측 시각',timeLabel(o.observed_at)]]),fields(Object.entries(value.verification)));
  return fragment;
 }
 const messages={idle:'아직 준비하지 않았습니다.',capabilities_pending:'준비 가능 여부를 확인하고 있습니다.',unconfigured:'검토 입력이 없습니다.',
  preparing:'보존자료와 참고 결합 확인 중',ready:'검토 준비를 확인했습니다.',appending:'참고 등록 응답 대기',recorded:'참고 이력에 등록했습니다.',
  uncertain:'등록 결과를 확인하지 못했습니다. 이력 확인 또는 원래 요청 재전송이 필요합니다.',
  replacement_unknown:'준비 교체 응답을 확인하지 못했습니다. 이전 준비의 유효성은 미확인입니다.',prepare_unknown:'준비 응답을 확인하지 못했습니다. 준비 번호를 복원할 수 없습니다.',
  retired:'준비 만료 또는 연결 변경입니다. 이력을 확인한 뒤 필요하면 새로 준비하세요.',error:'응답을 확인할 수 없습니다. 준비 가능 여부를 다시 확인하세요.'};
 function showGood(body,note,good,state){
  body.hidden=!!good&&state.context!==null&&!origin(good.context,state.context);
  const stale=good&&(!same(good.context,state.context)||state.pending||!['ready','recorded'].includes(state.phase));
  body.dataset.stale=String(!!stale);note.textContent=good?good.context.intake_id+' · v'+good.context.revision+(stale?' · 이전 관측 결과':''):'';
 }
 function render(state){
  if(!alive)return;current=state;root.dataset.phase=state.phase;root.dataset.pending=String(state.pending);root.setAttribute('aria-busy',String(state.pending||['capabilities_pending','preparing','appending'].includes(state.phase)));
  selection.textContent=state.context?state.context.intake_id+' · v'+state.context.revision:'현재 선택 없음';
  status.dataset.error=state.error_code||'';status.textContent=state.error_code===UNSAFE?'일부 번호를 이 화면에서 정확하게 표현할 수 없습니다. 원래 요청과 이전 결과를 유지합니다.':messages[state.phase];
  if(state.preview){pBody.replaceChildren(paintPreview(state.preview));lastPreview={context:copy(state.context),value:state.preview};}
  if(state.registration){rBody.replaceChildren(paintRegistration(state.registration));lastRegistration={context:copy(state.context),value:state.registration};}
  showGood(pBody,pNote,lastPreview,state);showGood(rBody,rNote,lastRegistration,state);
  const closed=!state.context||state.pending||['capabilities_pending','preparing','appending'].includes(state.phase);
  buttons.capabilities.disabled=closed;
  buttons.prepare.disabled=closed||state.phase==='uncertain'||state.phase==='unconfigured';
  buttons.prepare.textContent=['replacement_unknown','prepare_unknown'].includes(state.phase)?'새로 준비':'검토 준비';
  const matched=origin(lastPreview?.context,state.context);
  buttons.append.disabled=closed||!matched||!state.append_allowed||state.phase!=='ready';
  buttons.replay.disabled=closed||!matched||!state.append_allowed||!['recorded','uncertain'].includes(state.phase);
 }
 const controller=createIntakeReferenceActionsController({onChange:render,onRegistered:captured=>{
  if(!alive||current.pending||!same(current.context,captured))return;
  root.dispatchEvent(new doc.defaultView.CustomEvent('intake-reference-history-refresh',{detail:captured,bubbles:true}));
 }});
 const listeners=[];for(const [name,button] of Object.entries(buttons)){
  const handler=()=>{if(!button.disabled)void controller[name==='capabilities'?'refreshCapabilities':name]().catch(()=>{});};
  button.addEventListener('click',handler);listeners.push([button,handler]);
 }
 render(current);
 const destroy=()=>{if(!alive)return;alive=false;controller.destroy();for(const [button,fn] of listeners)button.removeEventListener('click',fn);
  lastPreview=null;lastRegistration=null;root.remove();};
 return Object.freeze({root,setContext:value=>controller.setContext(value),setPending:value=>controller.setPending(value),refreshCapabilities:()=>controller.refreshCapabilities(),destroy});
}
