/* DUT010 v1 owner DTO. This module never loads or executes source material. */
export const DUT_ROUTE_LABELS=Object.freeze({adb:'ADB 기본 경로',android_ui_and_test:'Android UI·시험',oem_sdk_cli:'OEM SDK·CLI',windows_vendor_gui:'Windows GUI 후보',serial_at_or_documented_protocol:'Serial·문서화 프로토콜',usb_hid_documented_protocol:'USB·HID 후보',chipset_rf_reference:'칩셋 RF 참고',firmware_service_reference:'펌웨어·서비스 참고',future_ios:'후속 iOS 참고'});
export const DUT_CODE_REFERENCE_IDS=Object.freeze(['samsung_at_legacy','android_at_research','qualcomm_diag','qualcomm_ath10k_testmode','samsung_legacy_muic']);
const REFERENCE_IDS=[...DUT_CODE_REFERENCE_IDS,'etsi_at_reference','usb_type_c_reference','samsung_diagnostic_reference','qualcomm_sdk_distribution'];
const ROUTES=Object.keys(DUT_ROUTE_LABELS);
const SOURCE_IDS=new Set([...Array.from({length:4},(_,i)=>'DUT-A'+String(i+1).padStart(2,'0')),...Array.from({length:25},(_,i)=>'DUT-G'+String(i+1).padStart(2,'0')),'DUT-S01']);
const COUNTS={source_units:30,github_projects:25,aosp_components:4,pinned_submodules:1,archive_files:32,archive_bytes:74333207,snapshot_files_verified:10538,stable_source_distributions:2};
const INDEPENDENCE={adb:false,android_ui_and_test:'usually_no_for_standard_bootstrap',oem_sdk_cli:'unknown_per_tool',windows_vendor_gui:true,serial_at_or_documented_protocol:true,usb_hid_documented_protocol:true,chipset_rf_reference:'depends_on_host_driver_and_firmware',firmware_service_reference:true,future_ios:true};
const fail=()=>{throw new Error('invalid_dut_catalog_response');};
const need=value=>{if(!value)fail();};
const checked=action=>{try{return action();}catch{fail();}};
const text=value=>need(typeof value==='string');
const count=value=>need(Number.isSafeInteger(value) && value>=0);
const array=value=>need(Array.isArray(value));
const strings=value=>{array(value);value.forEach(text);};
const exact=(value,keys)=>need(value && !Array.isArray(value) && Object.keys(value).sort().join(' ')===keys.split(' ').sort().join(' '));
const hex=(value,length)=>need(typeof value==='string' && value.length===length && /^[a-f0-9]+$/.test(value));
const sourceId=value=>need(typeof value==='string' && value.length===7 && /^DUT-[AGS][0-9]{2}$/.test(value));
const backendId=value=>need(typeof value==='string' && value.length>=1 && value.length<=80 && /^[a-z]/.test(value) && !/[^a-z0-9_]/.test(value));
const referenceId=value=>need(typeof value==='string' && value.length>=1 && value.length<=96 && /^[a-z]/.test(value) && !/[^a-z0-9_]/.test(value));
const memberPath=value=>{text(value);need(value && !/^[A-Za-z]:|^\/|\\|(?:^|\/)\.\.(?:\/|$)/.test(value));};
function clone(input){
  let nodes=0;
  const copy=(value,depth=0)=>{
    need(++nodes<=100000 && depth<=32);
    if(value===null || typeof value==='boolean')return value;
    if(typeof value==='string'){need(value.length<=262144 && !/[\uD800-\uDFFF]/u.test(value));return value;}
    if(typeof value==='number'){need(Number.isFinite(value));return value;}
    need(value && typeof value==='object');const isArray=Array.isArray(value),proto=Object.getPrototypeOf(value);
    need(isArray || proto===Object.prototype || proto===null);const keys=Reflect.ownKeys(value),output=isArray?[]:{};
    if(isArray){need(value.length<=100000 && keys.length===value.length+1);for(let i=0;i<value.length;i++)need(Object.hasOwn(value,i));}
    for(const key of keys){if(isArray && key==='length')continue;const descriptor=Object.getOwnPropertyDescriptor(value,key);need(typeof key==='string' && descriptor.enumerable && Object.hasOwn(descriptor,'value'));Object.defineProperty(output,key,{value:copy(descriptor.value,depth+1),enumerable:true,writable:true,configurable:true});}
    return output;
  };return copy(input);
}
function common(value,kind){need(value.schema_version===1 && value.kind===kind && value.catalog_state==='read_only_metadata_catalog');need(value.support_status==='not_assessed' && value.hardware_verified===false && value.source_code_executed===false && value.automatic_fallback_enabled===false);}
function sourceRecord(value,expectedId){
  sourceId(expectedId);sourceId(value.id);need(value.id===expectedId && SOURCE_IDS.has(value.id));
  const required='id category commit status archive_bytes archive_sha256 snapshot_scope license_evidence_files license_review_status device_or_firmware_supported adapter_integrated vendor_code_executed hardware_verified'.split(' ');
  const optional='repository repository_url base_url git_ref subtree snapshot_file_count source_file_count symlink_entries_retained_in_archive_only license_review installed_product_support application_boundary parent_source_id parent_path'.split(' ');
  need(required.every(key=>Object.hasOwn(value,key)) && Object.keys(value).every(key=>required.includes(key) || optional.includes(key)));
  for(const key of ['category','snapshot_scope','license_review_status'])text(value[key]);hex(value.commit,40);hex(value.archive_sha256,64);count(value.archive_bytes);need(value.archive_bytes>0);
  need(value.device_or_firmware_supported==='not_assessed' && value.adapter_integrated===false && value.vendor_code_executed===false && value.hardware_verified===false);
  if(Object.hasOwn(value,'installed_product_support'))need(value.installed_product_support==='not_assessed');
  if(value.id==='DUT-G13'){need(value.status==='source_files_and_release_acquired' && !Object.hasOwn(value,'snapshot_file_count'));count(value.source_file_count);}
  else{need(value.status==='acquired' && !Object.hasOwn(value,'source_file_count'));count(value.snapshot_file_count);}
  array(value.license_evidence_files);for(const file of value.license_evidence_files){exact(file,'path sha256 bytes');memberPath(file.path);hex(file.sha256,64);count(file.bytes);}
  for(const key of ['repository','repository_url','base_url','git_ref','license_review','application_boundary'])if(Object.hasOwn(value,key))text(value[key]);
  for(const key of ['subtree','parent_path'])if(Object.hasOwn(value,key))memberPath(value[key]);
  if(Object.hasOwn(value,'symlink_entries_retained_in_archive_only'))array(value.symlink_entries_retained_in_archive_only);
  if(value.id==='DUT-S01'){need(value.parent_source_id==='DUT-G18');memberPath(value.parent_path);}else need(!Object.hasOwn(value,'parent_source_id'));
}
function routeRecord(value,expected){
  backendId(expected);need(value.backend===expected && Object.hasOwn(DUT_ROUTE_LABELS,expected));
  exact(value,expected==='oem_sdk_cli'?'backend sources independent_of_adb use conditions acquisition_status':'backend sources independent_of_adb use conditions');
  need(value.independent_of_adb===INDEPENDENCE[expected]);text(value.use);strings(value.conditions);array(value.sources);
  value.sources.forEach(id=>{sourceId(id);need(SOURCE_IDS.has(id));});need(new Set(value.sources).size===value.sources.length);
  if(expected==='oem_sdk_cli')need(value.sources.length===0 && value.acquisition_status==='public_anyway_interface_not_verified');
}
function releases(values,allowed){
  array(values);const expected={'DUT-G01':'1.13.1','DUT-G13':'0.6.9'},seen=new Set();
  for(const value of values){exact(value,value.source_id==='DUT-G01'?'source_id release_version requires_python metadata_url archive_bytes archive_sha256':'source_id release_version metadata_url archive_bytes archive_sha256');need(allowed.includes(value.source_id) && !seen.has(value.source_id) && Object.hasOwn(expected,value.source_id));seen.add(value.source_id);need(value.release_version===expected[value.source_id]);text(value.metadata_url);count(value.archive_bytes);hex(value.archive_sha256,64);if(value.source_id==='DUT-G01')need(value.requires_python==='>=3.11');}
  need(values.length===allowed.filter(id=>Object.hasOwn(expected,id)).length);
}
function members(values,expectedId=null,commit=null){
  array(values);for(const value of values){exact(value,'source_id commit member_path member_sha256 member_git_blob_oid acquisition_scope manufacturing_test_code_present product_support');need(['DUT-G21','DUT-G19'].includes(value.source_id));if(expectedId!==null)need(value.source_id===expectedId);hex(value.commit,40);if(commit!==null)need(value.commit===commit);memberPath(value.member_path);hex(value.member_sha256,64);hex(value.member_git_blob_oid,40);need(value.acquisition_scope==='already_acquired_archive_member_independently_verified' && value.manufacturing_test_code_present===true && value.product_support==='not_assessed');}
  if(expectedId!==null)need(values.length===(['DUT-G21','DUT-G19'].includes(expectedId)?1:0));
  else need(values.length===2 && new Set(values.map(value=>value.source_id)).size===2);
}
export function validateDutSourceRecord(input,expectedId){return checked(()=>{const value=clone(input);sourceRecord(value,expectedId);return value;});}
export function validateDutRouteRecord(input,expectedBackend){return checked(()=>{const value=clone(input);routeRecord(value,expectedBackend);return value;});}
export function validateDutSummary(input){return checked(()=>{
  const value=clone(input);exact(value,'schema_version kind catalog_state counts route_count provenance support_status hardware_verified source_code_executed automatic_fallback_enabled reference_environment remaining_public_source_gaps');common(value,'dut_control_summary');need(value.route_count===9);exact(value.counts,Object.keys(COUNTS).join(' '));for(const key of Object.keys(COUNTS))need(value.counts[key]===COUNTS[key]);
  exact(value.provenance,'source_catalog_sha256 control_paths_sha256 main_prompt_v5_sha256 manufacturer_addendum_sha256');Object.values(value.provenance).forEach(hash=>hex(hash,64));
  const environment=value.reference_environment;exact(environment,'python_version node_version comparison_scope mobly_master_python_constraint_satisfied mobly_1_13_1_python_constraint_satisfied appium_and_uiautomator2_node_constraint_satisfied npm_android_sdk_jdk_device_requirements_checked');
  need(environment.python_version==='3.12.4' && environment.node_version==='24.16.0' && environment.comparison_scope==='declared_interpreter_constraints_only_not_install_or_product_support');need(environment.mobly_master_python_constraint_satisfied===false && environment.mobly_1_13_1_python_constraint_satisfied===true && environment.appium_and_uiautomator2_node_constraint_satisfied===true && environment.npm_android_sdk_jdk_device_requirements_checked===false);strings(value.remaining_public_source_gaps);return value;
});}
export function validateDutRoutes(input){return checked(()=>{
  const value=clone(input);array(value);need(value.length===9);const ids=[];value.forEach((route,index)=>{routeRecord(route,ROUTES[index]);ids.push(...route.sources);});need(ids.length===30 && new Set(ids).size===30);return value;
});}
export function validateDutRoute(input,expectedBackend){return checked(()=>{
  const value=clone(input);exact(value,'schema_version kind catalog_state route sources stable_releases support_status hardware_verified source_code_executed automatic_fallback_enabled');common(value,'dut_control_route');routeRecord(value.route,expectedBackend);array(value.sources);need(value.sources.length===value.route.sources.length);value.sources.forEach((source,index)=>sourceRecord(source,value.route.sources[index]));releases(value.stable_releases,value.route.sources);return value;
});}
export function validateDutSource(input,expectedId){return checked(()=>{
  const value=clone(input);exact(value,'schema_version kind catalog_state record stable_releases dependency_declarations manufacturing_member_checks backends support_status hardware_verified source_code_executed automatic_fallback_enabled');common(value,'dut_control_source');sourceRecord(value.record,expectedId);releases(value.stable_releases,[expectedId]);array(value.dependency_declarations);
  for(const declaration of value.dependency_declarations){exact(declaration,'source_id member_path sha256 declarations installed_dependency_lock_verified');need(declaration.source_id===expectedId && declaration.installed_dependency_lock_verified===false);memberPath(declaration.member_path);hex(declaration.sha256,64);need(declaration.declarations && typeof declaration.declarations==='object' && !Array.isArray(declaration.declarations));}
  members(value.manufacturing_member_checks,expectedId,value.record.commit);strings(value.backends);need(value.backends.length>0);let previous=-1;for(const backend of value.backends){const index=ROUTES.indexOf(backend);need(index>previous);previous=index;}return value;
});}
export function validateDutReferences(input){return checked(()=>{
  const value=clone(input);exact(value,'additional_reviewed_references additional_reviewed_reference_count newly_acquired_repository_archives new_links_in_equipment_url_index anyway_official_public_sdk_or_complete_protocol sm_a176u_chipset_or_transport_support samsung_legacy_muic_resistance_ohm_to_code etsi_reference_version clac cfun unverified_user_supplied_claims already_acquired_member_checks');
  need(value.additional_reviewed_reference_count===9 && value.newly_acquired_repository_archives===0 && value.new_links_in_equipment_url_index===false && value.anyway_official_public_sdk_or_complete_protocol==='not_verified' && value.sm_a176u_chipset_or_transport_support==='not_established_by_this_review');
  array(value.additional_reviewed_references);need(value.additional_reviewed_references.length===9);const ids=new Set();
  for(const reference of value.additional_reviewed_references){exact(reference,'reference_id url review_scope file_path_if_known file_blob_oid_if_verified repository_commit_pinned whole_repository_archive_acquired new_local_source_copy_saved target_device_support reuse_license_review');text(reference.reference_id);need(REFERENCE_IDS.includes(reference.reference_id) && !ids.has(reference.reference_id));ids.add(reference.reference_id);text(reference.url);text(reference.review_scope);if(reference.file_path_if_known!==null)memberPath(reference.file_path_if_known);if(reference.file_blob_oid_if_verified!==null)hex(reference.file_blob_oid_if_verified,40);need(reference.repository_commit_pinned===null && reference.whole_repository_archive_acquired===false && reference.new_local_source_copy_saved===false && reference.target_device_support==='not_verified' && reference.reuse_license_review==='required_per_file_before_reuse');}
  const muic=value.samsung_legacy_muic_resistance_ohm_to_code;exact(muic,'255000 301000 523000 619000');Object.values(muic).forEach(text);for(const key of ['etsi_reference_version','clac','cfun'])text(value[key]);strings(value.unverified_user_supplied_claims);members(value.already_acquired_member_checks);return value;
});}
export function formatAdbIndependence(value){return checked(()=>{
  if(value===true)return 'ADB 독립성 표기 true · 자동 대체 경로 아님';
  if(value===false)return 'ADB 독립성 표기 false · ADB 사용 조건 확인';
  const labels={usually_no_for_standard_bootstrap:'일반 부트스트랩은 ADB에 의존',unknown_per_tool:'도구별 ADB 독립성 미확정',depends_on_host_driver_and_firmware:'호스트 드라이버·펌웨어에 따라 다름'};
  need(typeof value==='string' && Object.hasOwn(labels,value));return labels[value]+' ('+value+')';
});}
export function safeDutSourceHref(value){try{if(typeof value!=='string' || !/^https?:\/\//i.test(value) || /[\s\u0000-\u001F\u007F\\]/.test(value))return null;const url=new URL(value);return ['http:','https:'].includes(url.protocol) && !url.username && !url.password?url.href:null;}catch{return null;}}
export function createDutReadGate(){let generation=0,current=null;return {begin(kind,id){if(kind==='route')backendId(id);else if(kind==='source')sourceId(id);else if(kind==='acquisition')referenceId(id);else need(kind==='references' && id===null);current=Object.freeze({generation:++generation,kind,id});return current;},clear(){generation++;current=null;},current(ticket){return ticket!==null && ticket===current;}};}

const DELTA_RECORDS=Object.freeze([
 ['qualcomm_diag','DUT-CONTROL-QCSUPER-001','65e14771804cec8fe70ffb55552da9d85721f0eb',7],
 ['samsung_at_legacy','DUT-CONTROL-GALAXY-AT-001','a4247497cca7da96b9aaa7f533cff23e13ad6437',2],
 ['android_at_research','DUT-CONTROL-FICS-AT-001','766a6b918289f5c2f4c3e1b82a65b964e4a0c8f5',6],
 ['qualcomm_ath10k_testmode','DUT-CONTROL-ATH10K-001','17bb0e2f6c8043f70a693a5f3797471cbed354c8',4],
 ['samsung_legacy_muic','DUT-CONTROL-LEGACY-MUIC-001','33ca16cbaf4bd144df3beef64283302c0aa35eed',2],
 ['etsi_at_reference','DUT-CONTROL-ETSI-REFERENCE-001',null,1]
]);
function deltaCommon(value,kind){
 need(value.schema_version===1 && value.kind===kind && value.catalog_state==='read_only_acquisition_delta');
 need(value.support_status==='not_assessed' && value.hardware_verified===false && value.source_code_executed===false && value.automatic_fallback_enabled===false);
}
function snapshotReference(value,id){
 exact(value,'reference_id url review_scope file_path_if_known file_blob_oid_if_verified repository_commit_pinned whole_repository_archive_acquired new_local_source_copy_saved target_device_support reuse_license_review');
 referenceId(id);need(REFERENCE_IDS.includes(id) && value.reference_id===id);text(value.url);text(value.review_scope);
 if(value.file_path_if_known!==null)memberPath(value.file_path_if_known);if(value.file_blob_oid_if_verified!==null)hex(value.file_blob_oid_if_verified,40);
 need(value.repository_commit_pinned===null && value.whole_repository_archive_acquired===false && value.new_local_source_copy_saved===false && value.target_device_support==='not_verified' && value.reuse_license_review==='required_per_file_before_reuse');
}
function acquisitionRecord(value,id){
 const expected=DELTA_RECORDS.find(row=>row[0]===id);need(expected);
 exact(value,'reference_id acquisition_scope selected_file_hashes_independently_verified whole_repository_archive_acquired record');
 need(value.reference_id===id && value.acquisition_scope==='selected_private_source_files_or_reference_document' && value.selected_file_hashes_independently_verified===true && value.whole_repository_archive_acquired===false);
 const record=value.record,keys='source_id authority license_basis scope limits files source_reuse_publication_approved device_or_Firmware_support runtime_or_physical_validation';
 exact(record,keys+(expected[2]===null?' title physical_pages printed_pages':' repository repository_commit commit_url')+(id==='qualcomm_diag'?' declared_package_version requires_python':''));
 need(record.source_id===expected[1] && record.source_reuse_publication_approved===false && record.device_or_Firmware_support==='not_assessed' && record.runtime_or_physical_validation===false);
 for(const key of ['authority','license_basis','scope'])text(record[key]);strings(record.limits);
 if(expected[2]!==null){text(record.repository);text(record.commit_url);need(record.repository_commit===expected[2]);}
 else{ text(record.title);for(const key of ['physical_pages','printed_pages']){array(record[key]);record[key].forEach(page=>{count(page);need(page>0);});}need(record.physical_pages.join(',')==='119,120,152' && record.printed_pages.join(',')==='118,119,151');}
 if(id==='qualcomm_diag'){text(record.declared_package_version);text(record.requires_python);}
 array(record.files);need(record.files.length===expected[3]);const seen=new Set();
 record.files.forEach((file,index)=>{
  const reused=id==='qualcomm_diag' && index===6;
  exact(file,'primary_source_url sha256 bytes public_payload_included'+(reused?' scope new_distinct_payload_original':' download_url'));
  text(file.primary_source_url);need(!seen.has(file.primary_source_url));seen.add(file.primary_source_url);hex(file.sha256,64);count(file.bytes);need(file.bytes>0 && file.public_payload_included===false);
  if(reused){text(file.scope);need(file.new_distinct_payload_original===false);}else text(file.download_url);
 });
}
export function validateDutAcquisitionSummary(input){return checked(()=>{
 const value=clone(input);exact(value,'schema_version kind catalog_state counts provenance support_status hardware_verified source_code_executed automatic_fallback_enabled source_reuse_publication_approved');deltaCommon(value,'dut_manufacturer_delta_summary');need(value.source_reuse_publication_approved===false);
 exact(value.counts,'source_groups source_file_references new_whole_repository_archives public_original_or_code_payload_files');
 for(const [key,number] of Object.entries({source_groups:6,source_file_references:22,new_whole_repository_archives:0,public_original_or_code_payload_files:0}))need(value.counts[key]===number);
 const provenance=value.provenance;exact(provenance,'public_collection_commit public_collection_path public_collection_sha256 source_request_id main_prompt_sha256 parent_catalog_sha256 relationship');
 hex(provenance.public_collection_commit,40);hex(provenance.public_collection_sha256,64);hex(provenance.main_prompt_sha256,64);memberPath(provenance.public_collection_path);text(provenance.source_request_id);need(provenance.relationship==='later_acquisition_metadata_without_rewriting_the_parent_snapshot');
 exact(provenance.parent_catalog_sha256,'dut_sources.json dut_paths.json');need(provenance.parent_catalog_sha256['dut_sources.json']==='e561182cf35b72ed47c45de28bf921b53b3eb7d662a226f686535c346c6b9858' && provenance.parent_catalog_sha256['dut_paths.json']==='3eb9d1d7623ddaa1f99ca1d3d50c749f184e7bb6a09767fc87800a9288dfe77b');return value;
});}
export function validateDutAcquisitionRecords(input){return checked(()=>{const value=clone(input);array(value);need(value.length===6);value.forEach((record,index)=>acquisitionRecord(record,DELTA_RECORDS[index][0]));return value;});}
export function validateDutAcquisitionReference(input,expectedId){return checked(()=>{
 referenceId(expectedId);need(REFERENCE_IDS.includes(expectedId));const value=clone(input);exact(value,'schema_version kind catalog_state reference_id snapshot_reference acquisition_delta support_status hardware_verified source_code_executed automatic_fallback_enabled');deltaCommon(value,'dut_manufacturer_reference');need(value.reference_id===expectedId);snapshotReference(value.snapshot_reference,expectedId);
 if(DELTA_RECORDS.some(row=>row[0]===expectedId))acquisitionRecord(value.acquisition_delta,expectedId);else need(value.acquisition_delta===null);return value;
});}
