import {validateIntakeReferenceContext,parseIntakeReferenceHistoryJson,parseIntakeReferenceCurrentJson,createIntakeReferenceGate} from './model.mjs';

const same=(a,b)=>a!==null&&b!==null&&a.intake_id===b.intake_id&&a.revision===b.revision&&a.snapshotGeneration===b.snapshotGeneration;
const literal=value=>value===null?'미확인 (null)':typeof value==='boolean'?String(value):Array.isArray(value)?value.join(', '):String(value);
const labels={current_at_append:'등록 당시 일치',historical_provided:'과거 자료로 등록',preparation_unverified:'준비 상태 미검증',head_conflict:'등록 시점 경합',reference_unbound:'참고 결합 부족',
 current:'현재 관측에 일치',stale:'현재 관측과 불일치',none:'현재 참고 등록 없음',unavailable:'현재 관측 미가용'};
function ownData(value,names){
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('invalid_intake_reference_view');
 const proto=Object.getPrototypeOf(value),keys=Reflect.ownKeys(value);if(proto!==Object.prototype&&proto!==null||keys.length!==names.length||names.some(key=>!keys.includes(key)))throw Error('invalid_intake_reference_view');
 const out={};for(const key of names){const descriptor=Object.getOwnPropertyDescriptor(value,key);if(!descriptor.enumerable||!Object.hasOwn(descriptor,'value'))throw Error('invalid_intake_reference_view');out[key]=descriptor.value;}return out;
}
function errorState(error){
 try{const d=Object.getOwnPropertyDescriptor(error,'message');return d&&Object.hasOwn(d,'value')&&d.value==='intake_reference_view_unrepresentable'?'unrepresentable':'error';}catch{return 'error';}
}
function timeLabel(value){
 // DTO validation preserves Python ISO spellings. Normalize only a display copy.
 const d=/^([0-9]{4})(?:-([0-9]{2})-([0-9]{2})|([0-9]{2})([0-9]{2})|-W([0-9]{2})(?:-([1-7]))?|W([0-9]{2})([1-7])?)/.exec(value);
 const date=new Date(0),year=Number(d[1]);
 if(d[6]||d[8]){date.setUTCFullYear(year,0,4);date.setUTCDate(4-(date.getUTCDay()+6)%7+(Number(d[6]||d[8])-1)*7+Number(d[7]||d[9]||1)-1);}
 else date.setUTCFullYear(year,Number(d[2]||d[4])-1,Number(d[3]||d[5]));
 const rest=[...value.slice(d[0].length)];rest.shift();const clock=rest.join('').split(/[Z+-]/,1)[0];
 const t=/^([0-9]{2})(?:(?::([0-9]{2})(?::([0-9]{2}))?)|(?:([0-9]{2})([0-9]{2})?))?(?:[.,]([0-9]+))?$/.exec(clock);
 date.setUTCHours(Number(t[1]),Number(t[2]||t[4]||0),Number(t[3]||t[5]||0),Number((t[6]||'').slice(0,3).padEnd(3,'0')));
 return value+' · '+new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'short',timeStyle:'medium'}).format(date)+' KST';
}
export function createIntakeReferenceReview(container,options){
 let transports;
 try{transports=ownData(options,['readHistory','readCurrent']);if(!container?.ownerDocument||typeof transports.readHistory!=='function'||typeof transports.readCurrent!=='function')throw Error();}
 catch{throw Error('invalid_intake_reference_view');}
 const doc=container.ownerDocument,historyGate=createIntakeReferenceGate(),currentGate=createIntakeReferenceGate();
 let alive=true,context=null,pending=false,queuedNew=false,readAllowed=false,historyBusy=false,currentBusy=false;
 let historyController=null,currentController=null,historyGood=null,currentGood=null;
 const el=(tag,className='',text)=>{const node=doc.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};
 const root=el('section','intake-reference-review panel ir-panel');root.setAttribute('aria-label','참고 이력과 현재 조회');
 const title=el('h2','','참고 이력 · 현재 조회'),selection=el('p','mono ir-selection','접수를 선택하세요.');
 const hint=el('p','ir-status','현재 상태 조회는 접수 보존자료의 무결성을 새로 확인합니다.');root.append(title,selection,hint);
 const historySection=el('section','ir-section'),currentSection=el('section','ir-section');
 const status=(cls,text)=>{const node=el('p','ir-status '+cls,text);node.setAttribute('role','status');node.setAttribute('aria-live','polite');node.dataset.state='idle';return node;};
 const historyStatus=status('ir-history-status','조회할 접수가 없습니다.'),currentStatus=status('ir-current-status','현재 조회는 명시 버튼으로 실행합니다.');
 const historyResults=el('div','ir-results ir-history-results'),currentResults=el('div','ir-results ir-current-results');
 const historyNote=el('p','mono ir-history-note'),currentNote=el('p','mono ir-current-note');
 const controls=el('div','ir-controls'),refreshButton=el('button','ir-history-refresh','이력 새로 조회'),previousButton=el('button','ir-history-previous','이전 이력');
 const currentControls=el('div','ir-controls'),currentButton=el('button','ir-current-read','현재 상태 조회');
 for(const button of [refreshButton,previousButton,currentButton])button.type='button';
 controls.append(refreshButton,previousButton);currentControls.append(currentButton);
 historySection.append(el('h3','','참고 등록 이력'),controls,historyStatus,historyNote,historyResults);
 currentSection.append(el('h3','','현재 조회 결과'),currentControls,currentStatus,currentNote,currentResults);
 root.append(historySection,currentSection);container.append(root);
 const fields=rows=>{const dl=el('dl','ir-fields');for(const [label,value] of rows){const row=el('div');row.append(el('dt','',label),el('dd','mono',literal(value)));dl.append(row);}return dl;};
 const setStatus=(node,state,text)=>{node.dataset.state=state;node.textContent=text;};
 const stale=(body,note,good)=>{
  if(!good){body.hidden=false;note.textContent='';return;}
  const old=!same(context,good.context)||pending;
  if(old)body.dataset.stale='true';
  body.hidden=context!==null&&(context.intake_id!==good.context.intake_id||context.revision!==good.context.revision);
  note.textContent=good.context.intake_id+' · v'+good.context.revision+(body.dataset.stale==='true'?' · 이전 조회 결과':'');
 };
 const sync=()=>{
  root.dataset.pending=String(pending);selection.textContent=context?context.intake_id+' · v'+context.revision:'현재 선택 없음';
  refreshButton.disabled=!alive||context===null||pending||historyBusy;
  previousButton.disabled=!alive||context===null||pending||historyBusy||!historyGood||!same(context,historyGood.context)||historyGood.value.next_before_seq===null||historyStatus.dataset.state==='unrepresentable';
  currentButton.disabled=!alive||context===null||pending||!readAllowed||currentBusy;
  root.setAttribute('aria-busy',String(pending||historyBusy||currentBusy));
  stale(historyResults,historyNote,historyGood);stale(currentResults,currentNote,currentGood);
 };
 const markStale=()=>{if(historyGood)historyResults.dataset.stale='true';if(currentGood)currentResults.dataset.stale='true';};
 const invalidate=()=>{historyGate.clear();currentGate.clear();historyController?.abort();currentController?.abort();historyController=null;currentController=null;historyBusy=false;currentBusy=false;readAllowed=false;markStale();};
 const valid=(gate,ticket,captured)=>alive&&!pending&&gate.current(ticket)&&same(context,captured);
 function renderRecord(value){
  const article=el('article','ir-record');article.append(el('h4','',(labels[value.binding_status]||value.binding_status)+' · '+value.binding_status));
  article.append(fields([['등록 ID',value.record_id],['이력 번호',value.seq],['요청 ID',value.request_id],['자료 버전',value.revision],
   ['원래 작업 ID',value.origin_job_id],['참고 검토 ID',value.reference_receipt_id],['기대한 접수 상태 ID',value.expected_snapshot_id],['등록 시각',timeLabel(value.created_at)]]));
  const a=value.append_observation;article.append(el('h5','','등록 당시 관측'),fields([['기대한 접수 상태 ID',a.expected_snapshot_id],['당시 관측한 접수 상태 ID',a.captured_snapshot_id],
   ['이전 현재 등록 ID',a.head_before_record_id],['이후 현재 등록 ID',a.head_after_record_id],['현재 등록 갱신',a.head_advanced],['당시 준비 상태',a.preparation_ready],['당시 관측 시각',timeLabel(a.observed_at)]]));
  const modes=value.source_modes;article.append(fields([['접수 합성 여부',modes.intake_revision_synthetic],['참고 catalog 합성 여부',modes.catalog_synthetic],['접수 출처 상태',modes.intake_provenance_status]]));return article;
 }
 function renderHistory(value){
  const fragment=doc.createDocumentFragment();fragment.append(fields([['이력 가용 여부',value.available],['이 페이지 등록 수',value.records.length]]));
  if(value.records.length===0)fragment.append(el('p','ir-status',value.available?'등록된 이력이 없습니다.':'등록 이력을 사용할 수 없습니다.'));
  for(const row of value.records)fragment.append(renderRecord(row));
  fragment.append(fields(Object.entries(value.verification)));return fragment;
 }
 function renderCurrent(value){
  const fragment=doc.createDocumentFragment(),o=value.current_observation;
  fragment.append(el('h4','',labels[value.status]+' · '+value.status),fields([['이력 가용 여부',value.available],['새로 관측한 접수 상태 ID',o.snapshot_id],['관측한 현재 등록 ID',o.head_record_id],
   ['관측한 준비 상태',o.preparation_ready],['새 관측 시각',timeLabel(o.observed_at)],['현재 조회 사유',value.reason_codes.length?value.reason_codes:'추가 사유 없음']]));
  if(value.record){fragment.append(el('h4','',value.status==='stale'||value.status==='unavailable'?'이전 등록':'현재 관측에 결합한 등록'),renderRecord(value.record));}
  if(value.reference_summary){const r=value.reference_summary;fragment.append(el('h4','','정제 참고 요약'),fields([['참고 검토 ID',r.receipt_id],['참고 상태',r.status],['참고 문맥 ID',r.context_id],
   ['선택 사례 ID',r.selected_case_ids],['받아들인 참고 수',r.accepted_reference_count]]));}
  fragment.append(fields(Object.entries(value.verification)));return fragment;
 }
 function showError(node,body,error){const state=errorState(error);setStatus(node,state,state==='unrepresentable'?'일부 번호를 이 화면에서 정확하게 표현할 수 없습니다. 이전 결과를 유지합니다.':'조회 응답을 확인할 수 없습니다. 이전 결과를 유지합니다.');body.dataset.stale='true';}
 async function loadHistory(query={limit:20,before_seq:null}){
  if(!alive||pending||context===null)return;
  const captured=context,ticket=historyGate.begin();historyController?.abort();const controller=new AbortController();historyController=controller;
  historyBusy=true;readAllowed=false;historyResults.dataset.stale='true';setStatus(historyStatus,'pending','등록 이력을 조회하고 있습니다.');sync();
  try{
   const response=await transports.readHistory(captured.intake_id,Object.freeze({...query}),controller.signal);
   if(!valid(historyGate,ticket,captured))return;
   const data=ownData(response,['raw_json','read_allowed']);if(typeof data.raw_json!=='string'||typeof data.read_allowed!=='boolean')throw Error('invalid_intake_reference_view');
   const value=parseIntakeReferenceHistoryJson(data.raw_json,captured.intake_id,query),fragment=renderHistory(value);
   historyResults.replaceChildren(fragment);historyResults.dataset.stale='false';historyGood={context:captured,value};readAllowed=data.read_allowed;
   setStatus(historyStatus,'ready',data.read_allowed?'등록 이력을 조회했습니다. 현재 조회를 사용할 수 있습니다.':'등록 이력을 조회했습니다. 현재 조회는 허용 범위를 사용할 수 없습니다.');
  }catch(error){if(!valid(historyGate,ticket,captured))return;readAllowed=false;showError(historyStatus,historyResults,error);}
  finally{if(valid(historyGate,ticket,captured)){historyBusy=false;historyController=null;sync();}}
 }
 async function readCurrent(){
  if(!alive||pending||context===null||!readAllowed||currentBusy)return;
  const captured=context,ticket=currentGate.begin(),controller=new AbortController();currentController=controller;currentBusy=true;
  currentResults.dataset.stale='true';setStatus(currentStatus,'pending','현재 상태를 새로 관측하고 있습니다.');sync();
  try{
   const raw=await transports.readCurrent(captured.intake_id,controller.signal);if(!valid(currentGate,ticket,captured))return;
   const value=parseIntakeReferenceCurrentJson(raw,captured.intake_id),fragment=renderCurrent(value);
   currentResults.replaceChildren(fragment);currentResults.dataset.stale='false';currentGood={context:captured,value};
   setStatus(currentStatus,value.status,labels[value.status]+' · 관측 시점의 결과입니다.');
  }catch(error){if(!valid(currentGate,ticket,captured))return;showError(currentStatus,currentResults,error);}
  finally{if(valid(currentGate,ticket,captured)){currentBusy=false;currentController=null;sync();}}
 }
 function failClosed(error){invalidate();context=null;queuedNew=false;showError(historyStatus,historyResults,error);showError(currentStatus,currentResults,error);sync();}
 function setContext(input){
  if(!alive)return;let next;try{next=validateIntakeReferenceContext(input);}catch(error){failClosed(error);return;}
  if(next!==null&&same(context,next))return;
  invalidate();context=next;queuedNew=pending&&next!==null;
  setStatus(historyStatus,'idle',next?'새 접수 문맥입니다.':'조회할 접수가 없습니다.');setStatus(currentStatus,'idle','현재 조회는 명시 버튼으로 실행합니다.');sync();
  if(next!==null&&!pending)void loadHistory();
 }
 function setPending(value){
  if(!alive)return;if(typeof value!=='boolean'){failClosed();return;}
  if(value){invalidate();pending=true;queuedNew=false;setStatus(historyStatus,'idle','접수 목록을 갱신하고 있습니다.');setStatus(currentStatus,'idle','접수 목록을 갱신하고 있습니다.');sync();return;}
  const resume=pending&&queuedNew&&context!==null;pending=false;queuedNew=false;sync();if(resume)void loadHistory();
 }
 const refreshHistory=()=>loadHistory();
 const onRefresh=()=>void loadHistory(),onPrevious=()=>{if(!previousButton.disabled)void loadHistory({limit:20,before_seq:historyGood.value.next_before_seq});},onCurrent=()=>void readCurrent();
 refreshButton.addEventListener('click',onRefresh);previousButton.addEventListener('click',onPrevious);currentButton.addEventListener('click',onCurrent);sync();
 return {root,setContext,setPending,refreshHistory,destroy(){
  if(!alive)return;alive=false;invalidate();context=null;queuedNew=false;
  refreshButton.removeEventListener('click',onRefresh);previousButton.removeEventListener('click',onPrevious);currentButton.removeEventListener('click',onCurrent);root.remove();
 }};
}
