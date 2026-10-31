const SOURCE_COMMIT='8dec2d783b99609b27fb37f82752f17146206f4d';
export const MAX_BYTES=524288;
export const ACCESS_LABELS={search_index_only:'검색 색인 확인',content_read:'원문 열람',download_read:'내려받은 원문 열람',blocked:'접근 차단',redirected:'리디렉션 확인'};
export const SCOPE_LABELS={included:'제어·계측 대상',excluded_passive:'독립 제어 비대상',identity_unresolved:'식별 보류',needs_scope_review:'제어 대상 여부 검토'};
export const RESEARCH_LABELS={exact_source:'정확 모델 자료',family_source:'제품군 자료',vendor_only:'제조사 자료',searched_no_public_control_source:'검색 범위에서 공개 제어자료 미확인',excluded_passive:'독립 제어 비대상',identity_unresolved:'식별 보류',needs_scope_review:'범위 검토'};
export const CANDIDATE_LABELS={normalized_label_candidates:'정규화한 텍스트 후보',same_model_other_manufacturer_candidates:'다른 제조사 표기의 같은 모델 후보',no_text_candidate:'직접 텍스트 후보 없음'};
const HASH='0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967';
const ROLES=new Set('dut power_sensor attenuator coupler splitter antenna amplifier filter rf_switch lisn power_meter signal_analyzer emi_receiver signal_generator communication_tester bluetooth_tester wireless_ap dfs_system network_test_station test_software power_supply temperature_chamber position_controller antenna_mast turntable network_analyzer inspection_microscope'.split(' '));
const fail=()=>{throw Error('invalid_virtual_support');},need=value=>{if(!value)fail();};
const exact=(value,keys)=>need(value && !Array.isArray(value) && Object.keys(value).sort().join(' ')===keys.split(' ').sort().join(' '));
const text=(value,max=1024)=>need(typeof value==='string' && value.length<=max);
const id=value=>need(typeof value==='string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,149}$/.test(value));
const hash=value=>need(typeof value==='string' && /^[a-f0-9]{64}$/.test(value));
const positive=value=>need(Number.isSafeInteger(value) && value>0 && value<=1000000);
const array=(value,max)=>need(Array.isArray(value) && value.length<=max);
const flags=value=>need(value.virtual_verification==='not_assessed' && value.hardware_verified===false && value.execution_authority===false);
const checked=operation=>{try{return operation();}catch{fail();}};

function nativeSnapshot(input){
  let nodes=0;
  const copy=(value,depth=0)=>{
    need(++nodes<=50000 && depth<=20);
    if(value===null || typeof value==='boolean')return value;
    if(typeof value==='string'){need(value.length<=4096 && !/[\uD800-\uDFFF]/u.test(value));return value;}
    if(typeof value==='number'){need(Number.isFinite(value));return value;}
    need(value && typeof value==='object');
    const list=Array.isArray(value),prototype=Object.getPrototypeOf(value),keys=Reflect.ownKeys(value);
    need(list ? prototype===Array.prototype : prototype===Object.prototype || prototype===null);
    const output=list?[]:{};
    if(list){need(value.length<=4096 && keys.length===value.length+1);for(let i=0;i<value.length;i++)need(Object.hasOwn(value,i));}
    else need(keys.length<=1024);
    for(const key of keys){
      if(list && key==='length')continue;
      const descriptor=Object.getOwnPropertyDescriptor(value,key);
      need(typeof key==='string' && descriptor.enumerable && Object.hasOwn(descriptor,'value'));
      Object.defineProperty(output,key,{value:copy(descriptor.value,depth+1),enumerable:true,writable:true,configurable:true});
      need(++nodes<=50000);
    }
    return output;
  };
  const value=copy(input);
  need(new TextEncoder().encode(JSON.stringify(value)).length<=MAX_BYTES);
  return value;
}

export function safeSourceURL(value){return checked(()=>{
  need(typeof value==='string' && value.length>0 && value.length<=2048 && !/[\x00-\x20\x7f\\]/.test(value));
  const url=new URL(value);
  need(['http:','https:'].includes(url.protocol) && url.hostname && !url.username && !url.password);
  return value;
});}

function reference(value){
  hash(value.sha256);
  if(value.kind==='docx_table'){
    exact(value,Object.hasOwn(value,'part')?'sha256 kind table row part':'sha256 kind table row');
    positive(value.table);positive(value.row);
    if(Object.hasOwn(value,'part'))need(value.part==='word/document.xml');
  }else{
    exact(value,'sha256 kind page');need(value.kind==='pdf_page');positive(value.page);
  }
}
function materials(value){
  exact(value,'candidate_status installed_equipment_binding_established candidates');
  need(Object.hasOwn(CANDIDATE_LABELS,value.candidate_status) && value.installed_equipment_binding_established===false);
  array(value.candidates,100);
  need((value.candidate_status==='no_text_candidate')===(value.candidates.length===0));
  const ids=new Set();
  for(const candidate of value.candidates){
    exact(candidate,'item_id manufacturer model scope research_status sources');
    id(candidate.item_id);need(!ids.has(candidate.item_id));ids.add(candidate.item_id);
    text(candidate.manufacturer);text(candidate.model);
    need(Object.hasOwn(SCOPE_LABELS,candidate.scope) && Object.hasOwn(RESEARCH_LABELS,candidate.research_status));
    array(candidate.sources,100);
    for(const source of candidate.sources){
      exact(source,'url access match_level');safeSourceURL(source.url);
      need(Object.hasOwn(ACCESS_LABELS,source.access) && ['exact_model','documented_family','generic_vendor','family_candidate','discovery_only'].includes(source.match_level));
    }
  }
}
function profile(value){
  exact(value,'profile_id profile_kind manufacturer model role variant evidence_refs materials virtual_role protocol virtual_verification hardware_verified execution_authority');
  id(value.profile_id);need(['report_equipment','dut_context','auxiliary'].includes(value.profile_kind));
  text(value.manufacturer);text(value.model);text(value.variant);need(ROLES.has(value.role));
  array(value.evidence_refs,10000);need(value.evidence_refs.length>0);value.evidence_refs.forEach(reference);
  materials(value.materials);flags(value);
  const role=value.virtual_role;
  exact(role,'status scope action_names protocol_scope');
  need(['declared','not_assessed'].includes(role.status) && role.scope==='virtual_case_actions' && role.protocol_scope===false);
  array(role.action_names,64);role.action_names.forEach(id);need(new Set(role.action_names).size===role.action_names.length);
  need((role.status==='declared')===(role.action_names.length>0));
  exact(value.protocol,'status reason');
  need(value.protocol.status==='not_assessed' && value.protocol.reason==='no_registered_pure_contract_for_this_profile');
}
function contract(value){
  exact(value,'schema_version model profile_id synthetic hardware_verified vendor_binary_executed units window synthetic_input sensor_compatibility calibration firmware options real_support commands source');
  need(value.schema_version===1 && value.model==='N1914A' && value.profile_id==='n1914a-a-ascii-v1'
    && value.synthetic===true && value.hardware_verified===false && value.vendor_binary_executed===false
    && Number.isSafeInteger(value.window) && value.window===1 && value.synthetic_input==='A');
  need(JSON.stringify(value.units)==='["DBM","W"]');
  for(const key of ['sensor_compatibility','calibration','firmware','options','real_support'])need(value[key]==='not_assessed');
  array(value.commands,12);need(value.commands.length===12 && new Set(value.commands).size===12);
  value.commands.forEach(command=>need(typeof command==='string' && /^[\x20-\x7e]{1,128}$/.test(command) && !command.includes(';')));
  exact(value.source,'document edition date sha256');
  need(value.source.document==='N1913-90008.pdf' && value.source.edition===19 && value.source.date==='2025-06-11');hash(value.source.sha256);
}
export function validateVirtualSupport(input){return checked(()=>{
  const value=nativeSnapshot(input);
  exact(value,'schema_version kind provenance snapshot_scope profile_count profiles adapter_contracts virtual_verification hardware_verified execution_authority');
  need(value.schema_version===1 && value.kind==='virtual_support_view' && value.snapshot_scope==='first_success_host_snapshot');flags(value);
  exact(value.provenance,'material_source_commit catalog_path catalog_sha256 role_declaration protocol_declaration');
  need(value.provenance.material_source_commit===SOURCE_COMMIT && value.provenance.catalog_path==='virtual_profiles/sm_a176u_unlicensed.json'
    && value.provenance.catalog_sha256===HASH && value.provenance.role_declaration==='labflow.virtual_fleet.integration.get_role_actions'
    && value.provenance.protocol_declaration==='labflow.n1914a_virtual_adapter.describe_virtual_n1914a_contract');
  need(value.profile_count===64);array(value.profiles,64);need(value.profiles.length===64);
  value.profiles.forEach(profile);need(new Set(value.profiles.map(p=>p.profile_id)).size===64);
  array(value.adapter_contracts,1);need(value.adapter_contracts.length===1);value.adapter_contracts.forEach(contract);
  return value;
});}
export function parseVirtualSupport(text){return checked(()=>{
  need(typeof text==='string' && new TextEncoder().encode(text).length<=MAX_BYTES);
  return validateVirtualSupport(JSON.parse(text));
});}
