import {validateSummary,validateItems,validateDetail,safeSourceHref,createReadGate,SCOPE_LABELS,RESEARCH_LABELS,ACCESS_LABELS,CANDIDATE_LABELS,
  DEFAULT_NAVIGATION,parseCatalogFragment,serializeCatalogFragment,createNavigationGate} from './model.mjs';
const $=selector=>document.querySelector(selector);
const gate=createReadGate(),state={list:null,detail:null,selected:'',pending:false,criteria:null};
const navigationGate=createNavigationGate();let activeNavigation=null;
const filterInputs=[['query','#query'],['scope','#scope'],['model_id','#model-id'],['equipment_id','#equipment-id'],['profile_id','#profile-id']];
const controllers={};let summaryGeneration=0;
const messages={catalog_unavailable:'자료 카탈로그를 읽지 못했습니다.',catalog_invalid_query:'검색 조건이나 ID의 형식을 확인하세요.',catalog_item_not_found:'해당 조사 항목이 없습니다.',invalid_catalog_response:'응답의 자료 구조·선택 ID·지원 상태를 확인하지 못했습니다.'};
function el(tag,className='',text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=String(text);return node;}
const literal=value=>typeof value==='string'?value:JSON.stringify(value);
function tag(text,warning=false){return el('span','tag'+(warning?' warning':''),text);}
function status(id,text,tone=''){const node=$(id);node.textContent=text;node.className='status '+tone;}
function kv(list,label,value){const row=el('div','kv');row.append(el('dt','',label),el('dd','',value===null?'미확정':value===''?'기록 없음':literal(value)));list.append(row);}
function section(title){const node=el('section','section');node.append(el('h3','',title));return node;}
function link(value){const href=safeSourceHref(value);if(!href)return el('span','source-url unavailable-link',value+' · 링크 비활성');const node=el('a','source-url',value);node.href=href;node.target='_blank';node.rel='noopener noreferrer';return node;}
function bullets(values){const list=el('ul');for(const value of values)list.append(el('li','literal',literal(value)));return list;}
function errorText(error){return Object.hasOwn(messages,error?.message)?messages[error.message]:'서버 연결 또는 조회 응답을 확인할 수 없습니다.';}
async function fetchData(key,url){
  controllers[key]?.abort();const controller=new AbortController();controllers[key]=controller;
  const timer=setTimeout(()=>controller.abort(),10000);
  try{const response=await fetch(url,{signal:controller.signal,cache:'no-store'});let value;try{value=await response.json();}catch{throw Error('invalid_catalog_response');}
    if(!response.ok)throw Error(Object.hasOwn(messages,value?.error?.code)?value.error.code:'catalog_unavailable');return value;
  }finally{clearTimeout(timer);}
}
function renderSummary(value){
  const fragment=document.createDocumentFragment(),metrics=el('div','metrics');
  for(const [label,number] of [['조사 항목',value.item_count],['모델 ID',value.model_count],['식별 항목 · 모델 ID 없음',value.identity_item_count],['대장 장비 ID',value.equipment_id_count]]){const card=el('div','metric');card.append(el('span','muted',label),el('strong','',number.toLocaleString('ko-KR')));metrics.append(card);}
  fragment.append(metrics);const snapshot=el('details','snapshot');snapshot.append(el('summary','','고정 대장 대응·출처·프로필 후보 집계'));
  const fields=el('dl');kv(fields,'조사 commit',value.source_commit);kv(fields,'대장 확인 방식',value.registry_snapshot.inspection_mode);kv(fields,'대장 SHA-256',value.registry_snapshot.sha256);kv(fields,'대장 경로 표기',value.registry_snapshot.path);
  kv(fields,'대장 대응 스냅샷',`모델 ${value.registry_snapshot.model_count} · 장비 ${value.registry_snapshot.equipment_count} · 불일치 ${value.registry_snapshot.missing_or_mismatched_ids}`);
  for(const [key,count] of Object.entries(value.scope_counts))kv(fields,SCOPE_LABELS[key],count);
  kv(fields,'출처 관계',`${value.source_association_count}건 · 고유 조사 URL ${value.research_unique_url_count} · 이전 참고 ${value.prior_reference_unique_url_count} · 중복 ${value.overlapping_url_count} · 합집합 ${value.unique_url_count}`);
  for(const [key,count] of Object.entries(value.profile_candidate_counts))kv(fields,CANDIDATE_LABELS[key],count);
  snapshot.append(fields,el('p','muted','고정 자료를 인수할 때 확인한 대장 대응입니다. 현재 DB·가동 장비를 다시 검사한 결과가 아니며 프로필과 설치 자산의 연결은 미확정입니다.'));
  fragment.append(snapshot);return fragment;
}
function renderItems(value){const fragment=document.createDocumentFragment();for(const item of value.items){const li=el('li'),button=el('button','item-button');button.type='button';button.dataset.itemId=item.item_id;
  button.append(el('strong','',item.model || '모델 표기 없음'),el('small','',item.manufacturer || '제조사 미확정'),el('small','mono',item.item_id),el('small','',SCOPE_LABELS[item.scope]),el('small','',`출처 ${item.source_count} · 장비 ID ${item.equipment_id_count} · 지원 미평가`));li.append(button);fragment.append(li);}return fragment;}
function renderDetail(value){
  const record=value.record,raw=record.research_record,root=el('article','detail-card');root.dataset.itemId=raw.item_id;
  const heading=el('h3','focus-target',raw.model || '모델 표기 없음');heading.id='catalog-detail-heading';heading.tabIndex=-1;
  root.append(el('p','eyebrow',raw.manufacturer || '제조사 미확정'),heading,el('p','mono',raw.item_id));
  const tags=el('div','tags');tags.append(tag('조사 분류 · '+SCOPE_LABELS[raw.scope],raw.scope!=='included'),tag('자료 확인 · '+RESEARCH_LABELS[raw.research_status]),tag('지원 미평가',true),tag('실물 미검증'),tag('설치·코드 실행 없음'));root.append(tags);
  const identity=el('dl');for(const [label,value] of [['모델 ID',raw.model_id],['등록행',raw.registration_rows],['장비 ID',raw.equipment_ids.join(' · ')],['장비명',raw.names.join(' · ')],['조사 분류 사유',raw.scope_reason],['공개 코드 조사',raw.public_code_status]])kv(identity,label,value);
  kv(identity,'자료 인수 상태','별도 카탈로그 인계 자료 · 실제 지원 상태와 별도');kv(identity,'식별 대응',raw.model_id===null?'장비 ID 대응 · 모델 식별 미확정':'고정 대장의 모델·장비 ID 대응');kv(identity,'정규화 프로필 후보 ID',record.candidate_virtual_profile_ids.join(' · ') || '없음');root.append(identity);
  const note=section('조사 기록');note.append(el('p','literal',raw.notes));if(Object.hasOwn(raw,'identity_assessment'))note.append(el('p','literal',literal(raw.identity_assessment)));root.append(note);
  const sources=section(`출처 ${raw.sources.length}건`);sources.append(el('p','muted','출처별 일치 수준·접근 상태·라이선스를 각각 보존합니다. 링크는 선택할 때만 외부로 이동합니다.'));
  if(!raw.sources.length)sources.append(el('p','empty','이 조사 항목에 연결된 출처가 없습니다. 공개 자료가 없다는 판정은 아닙니다.'));
  raw.sources.forEach((source,index)=>{const card=el('article','source');card.append(el('h4','',`출처 ${index+1} · ${source.kind}`),link(source.url));const fields=el('dl');for(const [label,value] of [['자료 종류',source.kind],['출처 권위',source.authority],['모델 일치 수준',source.match_level],['접근 상태',ACCESS_LABELS[source.access] ? `${ACCESS_LABELS[source.access]} (${source.access})`:source.access],['권리·라이선스',source.license],['근거',source.evidence]])kv(fields,label,value);card.append(fields);sources.append(card);});root.append(sources);
  const reviews=section('총괄 검토 주석');if(!value.review_notes.length)reviews.append(el('p','muted','이 항목에 연결된 별도 검토 주석이 없습니다.'));
  for(const review of value.review_notes){const card=el('article','review');card.append(el('h4','',review.title),el('p','mono',review.note_id),el('p','literal',review.explanation));for(const source of review.evidence){card.append(link(source.url),el('p','mono',`SHA-256 ${source.sha256}`));if(source.pdf_pages_1based.length)card.append(el('p','muted',`원문 PDF ${source.pdf_pages_1based.join(', ')}쪽`));}reviews.append(card);}root.append(reviews);
  const profiles=section(`프로필 텍스트 후보 ${value.profile_candidates.length}건`);profiles.append(el('p','literal','프로필과 설치 자산·펌웨어·옵션의 연결은 미확정입니다. 여러 정규화 후보나 다른 제조사 후보를 합치지 않으며 기존 가상 프로필을 유지합니다.'));
  if(!value.profile_candidates.length)profiles.append(el('p','muted','이 조사 항목에 연결된 텍스트 후보가 없습니다. 장비 지원 여부를 판정한 결과가 아닙니다.'));
  for(const profile of value.profile_candidates){const card=el('article','profile');card.append(el('h4','',`${profile.manufacturer_as_recorded} ${profile.model_as_recorded}`),el('p','mono',profile.profile_id),el('p','literal',CANDIDATE_LABELS[profile.text_comparison_status]),tag('설치 자산 연결 미확정',true));
    for(const field of ['normalized_label_candidates','same_model_other_manufacturer_candidates']){card.append(el('h4','',CANDIDATE_LABELS[field]));const list=el('ul');for(const candidate of profile[field]){const entry=el('li','literal',`${candidate.manufacturer} ${candidate.model} · ${candidate.item_id} · ${SCOPE_LABELS[candidate.scope]} · ${RESEARCH_LABELS[candidate.research_status]}`);for(const url of candidate.source_urls)entry.append(link(url));list.append(entry);}card.append(list);}
    const evidence=el('details');evidence.append(el('summary','','프로필의 원래 근거와 검토 기록'),bullets(profile.profile_evidence_refs),bullets(profile.review_notes));card.append(evidence);profiles.append(card);
  }root.append(profiles);return root;
}
function pagination(){const value=state.list;$('#previous').disabled=state.pending || !value || value.offset===0;$('#next').disabled=state.pending || !value || value.next_offset===null;}
async function loadSummary(){const generation=++summaryGeneration;status('#summary-status','자료 집계를 조회하고 있습니다.','pending');try{const value=validateSummary(await fetchData('summary','/api/control-sources/summary'));if(generation!==summaryGeneration)return;const prepared=renderSummary(value);$('#summary').replaceChildren(prepared);$('#summary').dataset.stale='false';status('#summary-status','고정 조사 집계 · 지원 미평가 · 프로필 연결 미확정');}catch(error){if(generation!==summaryGeneration)return;$('#summary').dataset.stale='true';status('#summary-status',errorText(error)+' 표시 중인 집계가 있으면 마지막 성공 조회 기록입니다.','error');}}
function focusNode(node){if(node){if(!node.matches('button,a,input,select,textarea'))node.tabIndex=-1;node.focus();}}
function currentRead(ticket,navigation){return gate.detailCurrent(ticket) && navigationGate.current(navigation);}
async function selectItem(itemId,{navigation=activeNavigation,focusMode='none',outsidePage=false}={}){
  const ticket=gate.beginDetail(itemId);state.selected=itemId;$('#detail').dataset.stale='true';status('#detail-status',`${itemId} 조회 중 · 아래 내용이 있으면 이전 성공 항목입니다.`,'pending');
  for(const button of $('#items').querySelectorAll('button'))button.setAttribute('aria-current',String(button.dataset.itemId===itemId));
  try{const value=validateDetail(await fetchData('detail','/api/control-sources/'+encodeURIComponent(itemId)),itemId);if(!currentRead(ticket,navigation))return;const prepared=renderDetail(value);if(!currentRead(ticket,navigation))return;$('#detail').replaceChildren(prepared);$('#detail').dataset.stale='false';state.detail=value;status('#detail-status',`선택 항목 ${itemId} · 고정 조사 자료`+(outsidePage?' · 현재 목록 페이지 밖의 직접 선택 항목':''));$('#announcer').textContent=`${value.record.research_record.model} 상세를 조회했습니다.`;if(focusMode==='detail')focusNode($('#catalog-detail-heading'));}
  catch(error){if(!currentRead(ticket,navigation))return;status('#detail-status',`${itemId} 조회 실패. ${errorText(error)} 아래 내용이 있으면 이전 성공 항목이며 현재 선택의 최신 결과가 아닙니다.`,'error');if(focusMode==='detail')focusNode($('#detail-status'));}
}
async function loadList(route,navigation,focusMode='none'){
  const {offset,limit,item_id:itemId}=route;
  const ticket=gate.beginList();controllers.detail?.abort();state.pending=true;pagination();$('#items').inert=true;$('#items').setAttribute('aria-busy','true');$('#detail').dataset.stale='true';status('#list-status','검색 조건의 목록을 조회하고 있습니다.','pending');status('#detail-status','목록 조회 중 · 아래 상세가 있으면 이전 성공 항목입니다.','pending');
  const criteria={};for(const [key] of filterInputs)if(route[key]!==DEFAULT_NAVIGATION[key])criteria[key]=route[key];
  const params=new URLSearchParams({offset:String(offset),limit:String(limit),...criteria});
  const current=()=>gate.listCurrent(ticket) && navigationGate.current(navigation);
  try{const value=validateItems(await fetchData('list','/api/control-sources?'+params));if(value.offset!==offset || value.limit!==limit)throw Error('invalid_catalog_response');if(!current())return;const prepared=renderItems(value);$('#items').replaceChildren(prepared);$('#items').dataset.stale='false';state.list=value;state.criteria=criteria;$('#result-count').textContent=`${value.total.toLocaleString('ko-KR')}항목`;$('#page-info').textContent=value.items.length?`${value.offset+1}–${value.offset+value.items.length} / ${value.total}`:`0 / ${value.total}`;status('#list-status',(value.items.length?'항목을 선택해 출처와 검토 내용을 확인하세요.':'조건에 맞는 조사 항목이 없습니다.')+' 적용 조건: '+(Object.entries(criteria).map(([key,value])=>key==='scope'?SCOPE_LABELS[value]:value).join(' · ') || '전체 조사 항목'));
    $('#items').inert=false;
    if(focusMode==='list')focusNode($('#items button') || $('#list-title'));
    if(itemId!==null)void selectItem(itemId,{navigation,focusMode:focusMode==='none'?'none':'detail',outsidePage:!value.items.some(item=>item.item_id===itemId)});
    else if(value.items.length)void selectItem(value.items[0].item_id,{navigation});
    else{state.detail=null;state.selected='';$('#detail').replaceChildren(el('p','empty','조건에 맞는 항목이 없어 상세를 표시하지 않습니다.'));$('#detail').dataset.stale='false';status('#detail-status','선택할 항목 없음');}
  }catch(error){if(!current())return;$('#items').dataset.stale='true';status('#list-status',errorText(error)+' 아래 목록이 있으면 이전 성공 조회이며 현재 조건의 결과가 아닙니다.','error');status('#detail-status','목록 조회 실패 · 아래 상세가 있으면 이전 성공 항목입니다.','error');if(focusMode!=='none')focusNode($('#list-status'));}
  finally{if(current()){state.pending=false;$('#items').inert=false;$('#items').setAttribute('aria-busy','false');pagination();}}
}
function navigationError(fallback=false){
  status('#navigation-status',fallback?'조회 링크를 읽지 못해 기본 목록을 표시합니다. (invalid_catalog_navigation)':'검색 조건의 형식을 확인하세요. 이전 조회를 유지하며 링크에 적용하지 않았습니다. (invalid_catalog_navigation)','error');
}
function navigate(route,{historyMode='push',force=false,focusMode='list',warning=false}={}){
  const fragment=serializeCatalogFragment(route),ticket=navigationGate.begin(route,{force});
  if(location.hash!==fragment){
    const method=historyMode==='push'?'pushState':'replaceState';
    history[method](null,'',location.pathname+fragment);
  }
  if(ticket===null)return;
  activeNavigation=ticket;
  if(!warning)status('#navigation-status','');
  for(const [key,selector] of filterInputs)$(selector).value=ticket.state[key] ?? '';
  $('.id-filters').open=['model_id','equipment_id','profile_id'].some(key=>ticket.state[key]!==null);
  void loadList(ticket.state,ticket,focusMode);
}
function restoreLocation(initial=false){
  try{
    const route=parseCatalogFragment(location.hash);
    navigate(route,{historyMode:'replace',focusMode:initial?'none':route.item_id!==null?'detail':'list'});
  }catch{
    navigationError(true);
    navigate({...DEFAULT_NAVIGATION},{historyMode:'replace',force:true,focusMode:initial?'none':'list',warning:true});
  }
}
function publishedRoute(itemId=null){
  return {...DEFAULT_NAVIGATION,...state.criteria,offset:state.list?.offset ?? 0,limit:state.list?.limit ?? activeNavigation?.state.limit ?? 25,item_id:itemId};
}
$('#filters').addEventListener('submit',event=>{
  event.preventDefault();
  const route={...DEFAULT_NAVIGATION,limit:activeNavigation?.state.limit ?? 25};
  for(const [key,selector] of filterInputs){const value=$(selector).value.trim();if(value)route[key]=value;}
  try{navigate(route,{force:true});}catch{navigationError();focusNode($('#navigation-status'));}
});
$('#refresh').addEventListener('click',()=>{void loadSummary();navigate(activeNavigation?.state || {...DEFAULT_NAVIGATION},{historyMode:'replace',force:true,focusMode:'none'});});
$('#items').addEventListener('click',event=>{const button=event.target.closest('[data-item-id]');if(button && !state.pending)navigate(publishedRoute(button.dataset.itemId),{force:true,focusMode:'detail'});});
$('#previous').addEventListener('click',()=>{const route=publishedRoute();route.offset=Math.max(0,state.list.offset-state.list.limit);navigate(route);});
$('#next').addEventListener('click',()=>{if(state.list && state.list.next_offset!==null){const route=publishedRoute();route.offset=state.list.next_offset;navigate(route);}});
$('.skip').addEventListener('click',event=>{event.preventDefault();$('#main').focus({preventScroll:true});$('#main').scrollIntoView({block:'start'});});
addEventListener('popstate',()=>restoreLocation());
addEventListener('hashchange',()=>restoreLocation());
void loadSummary();restoreLocation(true);
