export const SOURCE_COMMIT='8dec2d783b99609b27fb37f82752f17146206f4d';
export const SCOPE_LABELS={included:'제어·계측 대상',excluded_passive:'독립 제어 비대상',identity_unresolved:'식별 보류',needs_scope_review:'제어 대상 여부 검토'};
export const RESEARCH_LABELS={exact_source:'정확 모델 자료',family_source:'제품군 자료',vendor_only:'제조사 자료',searched_no_public_control_source:'검색 범위에서 공개 제어자료 미확인',excluded_passive:'독립 제어 비대상',identity_unresolved:'식별 보류',needs_scope_review:'범위 검토'};
export const ACCESS_LABELS={search_index_only:'검색 색인 확인',content_read:'원문 열람',download_read:'내려받은 원문 열람',blocked:'접근 차단',redirect:'리디렉션'};
export const CANDIDATE_LABELS={normalized_label_candidates:'정규화한 텍스트 후보',same_model_other_manufacturer_candidates:'다른 제조사 표기의 같은 모델 후보',no_text_candidate:'직접 텍스트 후보 없음'};
const fail=()=>{throw new Error('invalid_catalog_response');};
const need=value=>{if(!value)fail();};
const id=value=>need(typeof value==='string' && /^[A-Za-z0-9_.-]{1,150}$/.test(value));
const text=value=>need(typeof value==='string');
const count=value=>need(Number.isSafeInteger(value) && value>=0);
const array=value=>need(Array.isArray(value));
const exact=(value,keys)=>need(value && !Array.isArray(value) && Object.keys(value).sort().join(' ')===keys.split(' ').sort().join(' '));
const strings=value=>{array(value);value.forEach(text);};
const ids=value=>{array(value);value.forEach(id);need(new Set(value).size===value.length);};
const flags=value=>{need(value.adapter_support_status==='not_assessed');need(value.vendor_binary_executed===false && value.hardware_verified===false);};
function jsonData(input) {
  let nodes=0;
  const copy=(value,depth=0)=>{
    need(++nodes<=250000 && depth<=32);
    if(value===null || typeof value==='boolean')return value;
    if(typeof value==='string'){need(value.length<=1048576 && !/[\uD800-\uDFFF]/u.test(value));return value;}
    if(typeof value==='number'){need(Number.isFinite(value));return value;}
    need(value && typeof value==='object');
    const isArray=Array.isArray(value),proto=Object.getPrototypeOf(value);
    need(isArray || proto===Object.prototype || proto===null);
    const keys=Reflect.ownKeys(value),output=isArray?[]:{};
    if(isArray){need(value.length<=250000 && keys.length===value.length+1);for(let i=0;i<value.length;i++)need(Object.hasOwn(value,i));}
    for(const key of keys){
      if(isArray && key==='length')continue;
      const descriptor=Object.getOwnPropertyDescriptor(value,key);
      need(typeof key==='string' && descriptor.enumerable && Object.hasOwn(descriptor,'value'));
      Object.defineProperty(output,key,{value:copy(descriptor.value,depth+1),enumerable:true,writable:true,configurable:true});
    }
    return output;
  };
  return copy(input);
}
function common(value,kind){need(value.schema_version===1 && value.kind===kind && value.source_commit===SOURCE_COMMIT);}
function scoped(value){need(Object.hasOwn(SCOPE_LABELS,value));}
function researched(value){need(Object.hasOwn(RESEARCH_LABELS,value));}
function registry(value){
  exact(value,'path sha256 model_count equipment_count identity_item_count missing_or_mismatched_ids inspection_mode');
  text(value.path);text(value.inspection_mode);need(/^[a-f0-9]{64}$/.test(value.sha256));
  for(const key of ['model_count','equipment_count','identity_item_count','missing_or_mismatched_ids'])count(value[key]);
}
function headerItem(item){
  id(item.item_id);if(item.model_id!==null)id(item.model_id);
  text(item.manufacturer);text(item.model);scoped(item.scope);researched(item.research_status);text(item.public_code_status);
}
const checked=action=>{try{return action();}catch{fail();}};
export function validateSummary(input){return checked(()=>{
  const value=jsonData(input);
  exact(value,'schema_version kind source_commit catalog_state item_count model_count identity_item_count equipment_id_count scope_counts source_association_count research_unique_url_count prior_reference_unique_url_count overlapping_url_count unique_url_count profile_count profile_candidate_counts adapter_support_status vendor_binary_executed hardware_verified profile_binding_established registry_snapshot');
  common(value,'control_source_summary');need(value.catalog_state==='read_only_metadata_catalog');flags(value);need(value.profile_binding_established===false);
  for(const key of ['item_count','model_count','identity_item_count','equipment_id_count','source_association_count','research_unique_url_count','prior_reference_unique_url_count','overlapping_url_count','unique_url_count','profile_count'])count(value[key]);
  exact(value.scope_counts,Object.keys(SCOPE_LABELS).join(' '));Object.values(value.scope_counts).forEach(count);
  exact(value.profile_candidate_counts,Object.keys(CANDIDATE_LABELS).join(' '));Object.values(value.profile_candidate_counts).forEach(count);
  need(Object.values(value.scope_counts).reduce((a,b)=>a+b,0)===value.item_count);
  need(value.model_count+value.identity_item_count===value.item_count);
  need(Object.values(value.profile_candidate_counts).reduce((a,b)=>a+b,0)===value.profile_count);
  need(value.research_unique_url_count+value.prior_reference_unique_url_count-value.overlapping_url_count===value.unique_url_count);
  registry(value.registry_snapshot);return value;
});}
export function validateItems(input){return checked(()=>{
  const value=jsonData(input);exact(value,'schema_version kind source_commit total offset limit next_offset items');common(value,'control_source_items');
  count(value.total);count(value.offset);need(value.offset<=1000000);count(value.limit);need(value.limit>=1 && value.limit<=100);array(value.items);
  need(value.items.length===Math.min(value.limit,Math.max(0,value.total-value.offset)));
  const next=value.offset+value.items.length;need(value.next_offset===(next<value.total?next:null));
  let previous='';for(const item of value.items){
    exact(item,'item_id model_id manufacturer model scope research_status public_code_status source_count equipment_id_count registration_rows candidate_virtual_profile_ids adapter_support_status vendor_binary_executed hardware_verified');
    headerItem(item);need(item.item_id>previous);previous=item.item_id;flags(item);ids(item.candidate_virtual_profile_ids);
    for(const key of ['source_count','equipment_id_count','registration_rows'])count(item[key]);
  }return value;
});}
export function validateDetail(input,expectedId){return checked(()=>{
  id(expectedId);const value=jsonData(input);exact(value,'schema_version kind source_commit catalog_state record profile_candidates review_notes');common(value,'control_source_detail');need(value.catalog_state==='read_only_metadata_catalog');
  const record=value.record;exact(record,'research_record registry_reconciliation candidate_virtual_profile_ids integration_state adapter_support_status vendor_binary_executed hardware_verified');flags(record);ids(record.candidate_virtual_profile_ids);text(record.integration_state);
  const raw=record.research_record;headerItem(raw);need(raw.item_id===expectedId && raw.hardware_verified===false);
  for(const field of ['notes','scope_reason','search_basis','reviewed_at_kst','assignment','research_domain','initial_scope','initial_reason'])text(raw[field]);
  for(const field of ['names','categories','searched_queries'])strings(raw[field]);ids(raw.equipment_ids);count(raw.registration_rows);array(raw.register_numbers);raw.register_numbers.forEach(count);
  for(const key of ['hardware_tested','registered_unit_interface_verified'])if(Object.hasOwn(raw,key))need(raw[key]===false);
  array(raw.sources);for(const source of raw.sources){exact(source,'url kind authority match_level access license evidence');Object.values(source).forEach(text);}
  const mapping=record.registry_reconciliation;
  exact(mapping,'item_id model_id existing_model_id_matched missing_equipment_ids equipment_model_mismatches identity_record automatic_new_model_creation_permitted mapping_status');
  need(mapping.item_id===expectedId && mapping.model_id===raw.model_id && mapping.automatic_new_model_creation_permitted===false);
  need(mapping.identity_record===(raw.model_id===null));
  need(raw.model_id===null?mapping.existing_model_id_matched===null:typeof mapping.existing_model_id_matched==='boolean');
  ids(mapping.missing_equipment_ids);array(mapping.equipment_model_mismatches);text(mapping.mapping_status);
  array(value.profile_candidates);let previous='';
  for(const profile of value.profile_candidates){
    id(profile.profile_id);need(profile.profile_id>previous);previous=profile.profile_id;
    for(const field of ['manufacturer_as_recorded','model_as_recorded','role'])text(profile[field]);
    need(Object.hasOwn(CANDIDATE_LABELS,profile.text_comparison_status));need(profile.installed_equipment_binding_established===false && profile.simulation_profile_retained===true);
    array(profile.profile_evidence_refs);array(profile.review_notes);
    for(const field of ['normalized_label_candidates','same_model_other_manufacturer_candidates']){array(profile[field]);for(const candidate of profile[field]){headerItem(candidate);strings(candidate.source_urls);}}
    need([...profile.normalized_label_candidates,...profile.same_model_other_manufacturer_candidates].some(candidate=>candidate.item_id===expectedId));
  }
  array(value.review_notes);for(const note of value.review_notes){
    exact(note,'note_id item_ids title explanation evidence');id(note.note_id);ids(note.item_ids);need(note.item_ids.includes(expectedId));text(note.title);text(note.explanation);array(note.evidence);
    for(const source of note.evidence){exact(source,'kind url sha256 pdf_pages_1based');text(source.kind);text(source.url);need(/^[a-f0-9]{64}$/.test(source.sha256));array(source.pdf_pages_1based);for(const page of source.pdf_pages_1based){count(page);need(page>=1);}}
  }
  return value;
});}
export function safeSourceHref(value){
  try{if(typeof value!=='string' || !/^https?:\/\//i.test(value) || /[\s\u0000-\u001F\u007F\\]/.test(value))return null;
    const url=new URL(value);return ['http:','https:'].includes(url.protocol) && !url.username && !url.password?url.href:null;
  }catch{return null;}
}
export function createReadGate(){
  let generation=0,selection=0,selected='';
  return {beginList(){generation++;selected='';selection++;return generation;},listCurrent(ticket){return ticket===generation;},
    beginDetail(itemId){id(itemId);selected=itemId;return {generation,selection:++selection,item_id:itemId};},
    detailCurrent(ticket){return ticket.generation===generation && ticket.selection===selection && ticket.item_id===selected;}};
}
