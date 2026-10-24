import {validateFccCaseCalculationRequest, parseFccCaseCalculationSummaryJson,
  parseFccCaseCalculationCaseJson, parseFccCaseCalculationJson,
  createFccCaseCalculationGate} from './calculation_model.mjs';

const literal=value=>value===null?'미확인 (null)':typeof value==='string'?value:Object.is(value,-0)?'-0':JSON.stringify(value);

export function createFccCaseCalculation(container,{readSummary,readCase,calculate}){
 if(!container?.ownerDocument || ![readSummary,readCase,calculate].every(value=>typeof value==='function'))throw Error('invalid_fcc_case_calculation_transport');
 const doc=container.ownerDocument,summaryGate=createFccCaseCalculationGate(),detailGate=createFccCaseCalculationGate(),calculationGate=createFccCaseCalculationGate();
 let alive=true,summary=null,detail=null,summaryController=null,detailController=null,calculationController=null,generation=0,lastGood=null;
 const el=(tag,className='',value)=>{const node=doc.createElement(tag);if(className)node.className=className;if(value!==undefined)node.textContent=value;return node;};
 const root=el('section','fcc-calculation'),heading=el('h2','','사례 근거 계산');
 const note=el('p','fcc-calculation-note','보고서의 명시한 claim을 기존 계산 서비스로 확인합니다. 원문·검토 상태·부족 사유를 보존하며 시험 실행 권한을 발급하지 않습니다.');
 const refreshButton=el('button','fcc-calculation-refresh','계산 자료 다시 확인');refreshButton.type='button';
 const statusNode=(className,label)=>{const node=el('p',className,label);node.setAttribute('role','status');node.setAttribute('aria-live','polite');node.tabIndex=-1;node.dataset.state='idle';return node;};
 const summaryStatus=statusNode('fcc-calculation-summary-status','계산 자료를 확인하지 않았습니다.');
 const detailStatus=statusNode('fcc-calculation-detail-status','사례를 명시하고 불러오세요.');
 const status=statusNode('fcc-calculation-status','reading claim·규정·방법을 명시한 뒤 계산하세요.');
 const form=el('form','fcc-calculation-form'),grid=el('div','fcc-calculation-grid');
 const makeField=(label,name,select=false)=>{const field=el('label','fcc-calculation-field',label),input=el(select?'select':'input');input.name=name;if(!select){input.type='text';input.maxLength=512;input.autocomplete='off';input.spellcheck=false;}field.append(input);grid.append(field);return input;};
 const caseInput=makeField('사례 명시 선택','case_id',true),claimInput=makeField('reading claim ID 명시 선택','reading',true);
 const ruleInput=makeField('규정 원문 표기','rule'),methodInput=makeField('방법·정확 판본','method');
 const placeholder=(select,label)=>{const option=el('option','',label);option.value='';select.replaceChildren(option);select.value='';};
 placeholder(caseInput,'사례를 선택하세요');placeholder(claimInput,'사례를 먼저 불러오세요');caseInput.disabled=true;claimInput.disabled=true;
 const loadButton=el('button','fcc-calculation-load','사례 불러오기');loadButton.type='button';loadButton.disabled=true;
 const submitButton=el('button','fcc-calculation-submit','근거값으로 계산');submitButton.type='submit';submitButton.disabled=true;
 const contextNode=el('div','fcc-calculation-detail'),results=el('section','fcc-calculation-results');results.dataset.generation='0';
 const lastNote=el('p','fcc-calculation-last-note');lastNote.hidden=true;
 form.append(grid,loadButton,detailStatus,contextNode,submitButton,status);
 root.append(heading,note,refreshButton,summaryStatus,form,lastNote,results,
  el('p','fcc-calculation-note','계산 입력값·비교 tolerance·시험 limit는 받지 않습니다. 실제 AI·실물·현행 규범 적합성 검증과 기존 위임은 별도입니다.'));
 container.replaceChildren(root);
 const setStatus=(node,state,text)=>{node.dataset.state=state;node.textContent=text;};
 const focus=(node,original)=>{if(alive && doc.activeElement===original)node.focus();};
 const markLast=()=>{if(lastGood){lastNote.hidden=false;lastNote.textContent='이전 요청 결과 · '+lastGood.request.case_id+' · 아래 값은 마지막 정상 응답입니다.';results.dataset.stale='true';}};
 function invalidateCalculation(message=true){
  generation++;calculationGate.clear();calculationController?.abort();markLast();
  if(message)setStatus(status,'idle','입력이 바뀌었습니다. 현재 명시값으로 다시 계산하세요.');
 }
 function fields(rows){const dl=el('dl','fcc-calculation-fields');for(const [key,value] of rows){const row=el('div');row.append(el('dt','',key),el('dd','',literal(value)));dl.append(row);}return dl;}
 function command(){return validateFccCaseCalculationRequest({schema_version:1,case_id:caseInput.value,calculation_request:{calculator:'rf_power',rule:ruleInput.value,method:methodInput.value,input_claim_ids:{reading:claimInput.value},reported_result_claim_id:null,comparison_policy:null}});}
 function render(value){
  const fragment=doc.createDocumentFragment(),title=el('h3','fcc-calculation-result-heading','마지막 정상 응답 · '+value.status);title.tabIndex=-1;
  fragment.append(title,fields([['사례',value.case_id],['corpus_id',value.corpus_id],['명시 요청',value.request_context],['상태',value.status],['실행 권한 부여',value.execution_authorized]]));
  const result=value.result;
  fragment.append(fields([['계산 범위',result.validation_scope],['구조화 값 해석 범위',result.interpretation_scope],['부족 사유',result.reason_codes],['원래 문맥',result.context]]));
  if(result.calculation!==null){const output=el('p','fcc-calculation-value',literal(result.calculation.value)+' '+result.calculation.unit);fragment.append(output,fields([['기존 native_result',result.calculation.native_result]]));}
  else fragment.append(el('p','fcc-calculation-no-value','계산값 미제공 (null) · 확인되지 않은 근거를 채우지 않았습니다.'));
  for(const input of result.inputs){
   const section=el('section','fcc-calculation-projection');section.dataset.claimId=input.claim_id;
   section.append(fields([['역할',input.role],['claim_id',input.claim_id],['field',input.field],['원래 값',input.value],['원래 단위',input.unit]]));
   for(const source of input.sources)section.append(fields(Object.entries(source)));
   fragment.append(section);
  }
  fragment.append(fields([['결합한 페이지·행',result.source_page],['보고 결과',result.reported_result],['비교 정책',result.comparison_policy],['비교',result.comparison],['검증 관측',result.verification]]));
  return fragment;
 }
 async function refresh({moveFocus=false}={}){
  if(!alive)return;const original=doc.activeElement,ticket=summaryGate.begin();summaryController?.abort();summaryController=new AbortController();
  detailGate.clear();detailController?.abort();summary=null;detail=null;invalidateCalculation(false);submitButton.disabled=true;loadButton.disabled=true;caseInput.disabled=true;
  setStatus(summaryStatus,'pending','계산 패널의 고정 사례 목록을 확인하고 있습니다.');
  try{
   const raw=await readSummary(summaryController.signal);if(!alive || !summaryGate.current(ticket))return;
   const value=parseFccCaseCalculationSummaryJson(raw),options=doc.createDocumentFragment();
   options.append(el('option','','사례를 선택하세요'));options.firstChild.value='';
   for(const preview of value.case_previews){const option=el('option','',preview.case_id+' · '+(preview.report_number??'보고번호 미확인')+' · '+preview.review_status);option.value=preview.case_id;options.append(option);}
   if(!alive || !summaryGate.current(ticket))return;
   summary=value;caseInput.replaceChildren(options);caseInput.value='';caseInput.disabled=false;
   placeholder(claimInput,'사례를 먼저 불러오세요');claimInput.disabled=true;contextNode.replaceChildren();
   setStatus(detailStatus,'idle','사례를 명시하고 불러오세요.');setStatus(summaryStatus,'ready','고정 사례 '+value.case_previews.length+'개 · 모집단·실행 준비 승인은 별도입니다.');
   setStatus(status,'idle','reading claim·규정·방법을 명시한 뒤 계산하세요.');
   if(moveFocus)focus(summaryStatus,original);
  }catch(error){if(!alive || !summaryGate.current(ticket))return;setStatus(summaryStatus,'error',error?.message==='fcc_case_catalog_unconfigured'?'사례 자료 미구성 · 계산 패널에 검수된 자료가 연결되지 않았습니다.':'사례 목록 조회 실패 · 이전 계산 결과는 보존합니다.');}
 }
 async function loadCase(){
  if(!alive || !summary || !caseInput.value)return;
  const identity=caseInput.value,original=doc.activeElement,ticket=detailGate.begin();detailController?.abort();detailController=new AbortController();detail=null;invalidateCalculation(false);submitButton.disabled=true;claimInput.disabled=true;
  setStatus(detailStatus,'pending','명시한 사례의 근거를 불러오고 있습니다.');
  try{
   const raw=await readCase(identity,detailController.signal);if(!alive || !detailGate.current(ticket))return;
   const value=parseFccCaseCalculationCaseJson(raw,identity,summary),options=doc.createDocumentFragment();
   const first=el('option','','reading claim ID를 선택하세요');first.value='';options.append(first);
   for(const claim of value.case.claims){const option=el('option','',claim.claim_id+' · '+claim.field+' · '+literal(claim.unit)+' · '+claim.status);option.value=claim.claim_id;options.append(option);}
   const context=fields([['사례',value.case.case_id],['사례 전체 검토',value.case.preview.review_status],['규정 표기 참고',value.case.preview.rules],['방법 표기 참고',value.case.preview.methods],['문서 부분 상태',value.documents.map(row=>({document_id:row.document_id,extraction:row.extraction.status,rights:row.rights.status}))]]);
   if(!alive || !detailGate.current(ticket))return;
   detail=value;claimInput.replaceChildren(options);claimInput.value='';claimInput.disabled=false;submitButton.disabled=false;contextNode.replaceChildren(context);
   setStatus(detailStatus,'ready','사례 근거 조회 완료 · reading·규정·방법은 직접 명시하세요.');focus(detailStatus,original);
  }catch(error){if(!alive || !detailGate.current(ticket))return;setStatus(detailStatus,'error','사례 근거 조회 실패 · 현재 입력으로 계산하지 않았습니다.');}
 }
 async function submit(){
  if(!alive)return;invalidateCalculation(false);const original=doc.activeElement;
  let request;
  try{request=command();if(!detail || detail.case.case_id!==request.case_id)throw Error();}
  catch{setStatus(status,'error','사례 근거를 불러오고 reading claim·규정·방법을 명시하세요.');return;}
  const sourceDetail=detail,ticket=calculationGate.begin(),publishedGeneration=generation;calculationController=new AbortController();
  setStatus(status,'pending','명시한 근거로 계산 서비스를 확인하고 있습니다.');
  try{
   const raw=await calculate(request,calculationController.signal);if(!alive || !calculationGate.current(ticket))return;
   const value=parseFccCaseCalculationJson(raw,request,sourceDetail);
   if(!alive || !calculationGate.current(ticket))return;
   if(value.status==='rejected'){setStatus(status,'rejected','계산 서비스 거절 · '+value.error_code+' · 이전 정상 결과는 보존합니다.');focus(status,original);return;}
   const fragment=render(value);if(!alive || !calculationGate.current(ticket))return;
   results.replaceChildren(fragment);results.dataset.generation=String(publishedGeneration);results.dataset.stale='false';
   lastGood={request,response:value};lastNote.hidden=true;
   setStatus(status,value.status,value.status==='calculated'?'보고서 근거 계산 완료 · 실물·규범 적합성 검증은 별도입니다.':'근거 부족 · 원래 사유와 확인된 projection을 보존했습니다.');
   focus(results.querySelector('.fcc-calculation-result-heading'),original);
  }catch(error){if(!alive || !calculationGate.current(ticket))return;setStatus(status,'error','계산 요청 또는 응답 검증 실패 · 이전 정상 결과는 보존합니다.');focus(status,original);}
 }
 const onCase=()=>{detailGate.clear();detailController?.abort();detail=null;placeholder(claimInput,'사례를 먼저 불러오세요');claimInput.disabled=true;loadButton.disabled=!caseInput.value;submitButton.disabled=true;invalidateCalculation();};
 const onInput=()=>invalidateCalculation();
 const onSubmit=event=>{event.preventDefault();void submit();};
 const onRefresh=()=>void refresh({moveFocus:true});
 caseInput.addEventListener('change',onCase);claimInput.addEventListener('change',onInput);
 for(const input of [ruleInput,methodInput]){input.addEventListener('input',onInput);input.addEventListener('change',onInput);}
 loadButton.addEventListener('click',loadCase);form.addEventListener('submit',onSubmit);refreshButton.addEventListener('click',onRefresh);
 return {refresh,root,destroy(){if(!alive)return;alive=false;summaryGate.clear();detailGate.clear();calculationGate.clear();summaryController?.abort();detailController?.abort();calculationController?.abort();caseInput.removeEventListener('change',onCase);claimInput.removeEventListener('change',onInput);for(const input of [ruleInput,methodInput]){input.removeEventListener('input',onInput);input.removeEventListener('change',onInput);}loadButton.removeEventListener('click',loadCase);form.removeEventListener('submit',onSubmit);refreshButton.removeEventListener('click',onRefresh);}};
}
