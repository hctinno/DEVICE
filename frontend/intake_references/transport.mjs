/*050 same-origin wire transport. Session secrets stay in this closure. */
import {INTAKE_REFERENCE_VIEW_MAX_BYTES,validateIntakeReferenceContext} from './model.mjs';

const INVALID='intake_reference_ui_invalid_request',UNAVAILABLE='intake_reference_ui_unavailable';
const knownCodes=new Set(Object.entries({
 ui:['unconfigured','invalid_request','input_limit','access_denied','session_unavailable','unavailable'],
 review:['access_denied','input_limit','invalid_argument','parent_invalid','prepared_invalid','review_state_changed','store_invalid','unavailable'],
 ledger:['input_limit','intake_not_found','integrity_invalid','invalid_argument','origin_invalid','parent_invalid','request_conflict','schema_mismatch','storage_error','store_invalid'],
 state:['delegation_invalid','input_limit','intake_not_found','invalid_argument','projection_inconsistent','source_integrity_invalid','storage_error','store_invalid','transaction_required'],
}).flatMap(([prefix,suffixes])=>suffixes.map(suffix=>`intake_reference_${prefix}_${suffix}`)));
const ownQuery=value=>{
 if(!value||typeof value!=='object'||![Object.prototype,null].includes(Object.getPrototypeOf(value)))throw Error();
 const keys=Reflect.ownKeys(value);if(keys.length!==2||!keys.includes('limit')||!keys.includes('before_seq'))throw Error();
 const copy={};for(const key of keys){const item=Object.getOwnPropertyDescriptor(value,key);
  if(!item.enumerable||!Object.hasOwn(item,'value'))throw Error();copy[key]=item.value;}
 if(!Number.isSafeInteger(copy.limit)||copy.limit<1||copy.limit>100||
  (copy.before_seq!==null&&(!Number.isSafeInteger(copy.before_seq)||copy.before_seq<1)))throw Error();
 return copy;
};
const same=(a,b)=>a!==null&&b!==null&&a.intake_id===b.intake_id&&a.revision===b.revision&&a.snapshotGeneration===b.snapshotGeneration;
const wireError=raw=>{
 // The only accepted non-2xx shape has exactly these two keys and a literal known code.
 const match=/^[ \t\r\n]*\{[ \t\r\n]*"error"[ \t\r\n]*:[ \t\r\n]*\{[ \t\r\n]*"code"[ \t\r\n]*:[ \t\r\n]*"([a-z_]+)"[ \t\r\n]*\}[ \t\r\n]*\}[ \t\r\n]*$/.exec(raw);
 return match&&knownCodes.has(match[1])?match[1]:UNAVAILABLE;
};

export function createIntakeReferenceTransport(...args){
 if(args.length)throw Error(INVALID);
 let alive=true,context=null,pending=false,epoch={},historyTicket=null,historyController=null,secret=null;
 const requests=new Set(),ownErrors=new WeakMap();
 const failure=code=>{const error=Error(code);ownErrors.set(error,code);return error;};
 const clearSecret=()=>{secret=null;};
 const invalidate=()=>{
  epoch={};historyTicket=null;clearSecret();
  for(const controller of requests)controller.abort();
  historyController=null;
 };
 const invalidInput=()=>{invalidate();context=null;return failure(INVALID);};
 const setContext=value=>{
  if(!alive)return;
  let next;try{next=validateIntakeReferenceContext(value);}catch{throw invalidInput();}
  if(same(context,next))return;
  invalidate();context=next;
 };
 const setPending=value=>{
  if(!alive)return;
  if(typeof value!=='boolean')throw invalidInput();
  if(value)invalidate();pending=value;
 };
 const destroy=()=>{if(!alive)return;alive=false;invalidate();context=null;pending=true;requests.clear();};
 const validate=(id,signal,query,history=false)=>{
  let parsed;try{
   if(typeof id!=='string'||!(signal instanceof AbortSignal))throw Error();
   if(history)parsed=ownQuery(query);
  }catch{throw invalidInput();}
  if(context!==null&&id!==context.intake_id)throw invalidInput();
  if(!alive||pending||context===null)throw failure(INVALID);
  return parsed;
 };

 async function perform(kind,id,query,caller){
  const capturedEpoch=epoch,ticket={},usedSecret=secret,controller=new AbortController();
  if(kind==='history'){
   historyController?.abort();historyController=controller;historyTicket=ticket;clearSecret();
  }
  const valid=()=>alive&&!pending&&epoch===capturedEpoch&&!controller.signal.aborted&&
   (kind!=='history'||historyTicket===ticket);
  const guard=()=>{if(!valid())throw failure(UNAVAILABLE);};
  let reader=null,rejectAbort;
  const aborted=new Promise((resolve,reject)=>{rejectAbort=reject;});
  const onAbort=()=>{rejectAbort(failure(UNAVAILABLE));if(reader)void reader.cancel().catch(()=>{});};
  const onCaller=()=>controller.abort();
  controller.signal.addEventListener('abort',onAbort,{once:true});
  caller.addEventListener('abort',onCaller,{once:true});
  requests.add(controller);
  const timer=setTimeout(()=>controller.abort(),35000);
  if(caller.aborted)controller.abort();

  async function bounded(response){
   const type=response.headers.get('Content-Type'),length=response.headers.get('Content-Length');
   if(!type||!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(type)||
    (length!==null&&(!/^[0-9]+$/.test(length)||BigInt(length)>BigInt(INTAKE_REFERENCE_VIEW_MAX_BYTES)))){
    if(response.body)void response.body.cancel().catch(()=>{});throw failure(UNAVAILABLE);
   }
   if(!response.body)throw failure(UNAVAILABLE);
   reader=response.body.getReader();const chunks=[];let count=0,complete=false;
   try{
    while(true){guard();const item=await reader.read();guard();if(item.done){complete=true;break;}
     if(!(item.value instanceof Uint8Array)||item.value.byteLength>INTAKE_REFERENCE_VIEW_MAX_BYTES-count)throw failure(UNAVAILABLE);
     count+=item.value.byteLength;chunks.push(item.value);
    }
    const bytes=new Uint8Array(count);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
    // TextDecoder normally removes a UTF-8 BOM, so inspect bytes before decoding.
    if(bytes[0]===0xef&&bytes[1]===0xbb&&bytes[2]===0xbf)throw failure(UNAVAILABLE);
    return new TextDecoder('utf-8',{fatal:true}).decode(bytes);
   }finally{
    if(!complete)void reader.cancel().catch(()=>{});
    reader.releaseLock();reader=null;
   }
  }
  async function work(){
   guard();const base=`/api/intake-references/${id}`;
   const url=kind==='history'?base+`/history?limit=${query.limit}`+(query.before_seq===null?'':`&before_seq=${query.before_seq}`):base+'/current';
   const options={method:kind==='history'?'GET':'POST',signal:controller.signal,
    credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:'application/json'}};
   if(kind==='current'){
    options.headers['Content-Type']='application/json; charset=utf-8';
    options.headers['X-Intake-Reference-CSRF']=usedSecret.token;
    options.body=JSON.stringify({schema_version:1,action:'current'});
   }
   const response=await fetch(url,options);guard();
   const raw=await bounded(response);guard();
   if(!response.ok){
    const code=wireError(raw);
    if(kind==='current'&&secret===usedSecret&&
     (response.status===403||code==='intake_reference_ui_session_unavailable'||code.endsWith('_access_denied')))clearSecret();
    throw failure(code);
   }
   if(kind==='current')return raw;
   const allowed=response.headers.get('X-Intake-Reference-Read-Allowed'),token=response.headers.get('X-Intake-Reference-CSRF');
   if((allowed!=='true'&&allowed!=='false')||(allowed==='true'&&(token===null||!/^[a-f0-9]{64}$/.test(token)))||
    (allowed==='false'&&token!==null))throw failure(UNAVAILABLE);
   guard();secret=allowed==='true'?{token}:null;
   return {raw_json:raw,read_allowed:allowed==='true'};
  }
  try{return await Promise.race([work(),aborted]);}
  catch(error){throw failure(ownErrors.get(error)||UNAVAILABLE);}
  finally{
   clearTimeout(timer);caller.removeEventListener('abort',onCaller);controller.signal.removeEventListener('abort',onAbort);
   requests.delete(controller);if(historyController===controller)historyController=null;
  }
 }
 const readHistory=async(id,query,signal)=>{const parsed=validate(id,signal,query,true);return perform('history',id,parsed,signal);};
 const readCurrent=async(id,signal)=>{validate(id,signal);if(secret===null)throw failure(INVALID);return perform('current',id,null,signal);};
 return {readHistory,readCurrent,setContext,setPending,destroy};
}
