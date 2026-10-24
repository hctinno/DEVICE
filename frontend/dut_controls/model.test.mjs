/* Raw-record presentation contracts; API wrapper DTO is supplied by DUT010. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as dutModel from './model.mjs';
import {validateDutSourceRecord,validateDutRouteRecord,formatAdbIndependence,safeDutSourceHref,createDutReadGate,
 validateDutSummary,validateDutRoutes,validateDutRoute,validateDutSource,validateDutReferences} from './model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL('../../control_sources/'+name,import.meta.url),'utf8'));
const sources=read('dut_sources.json'),paths=read('dut_paths.json');
const flags={support_status:'not_assessed',hardware_verified:false,source_code_executed:false,automatic_fallback_enabled:false};
const common=kind=>({schema_version:1,kind,catalog_state:'read_only_metadata_catalog',...flags});
const summary=()=>structuredClone({...common('dut_control_summary'),counts:sources.counts,route_count:9,provenance:sources.provenance,reference_environment:sources.reference_environment,remaining_public_source_gaps:sources.remaining_public_source_gaps});
const route=backend=>{const record=paths.paths.find(row=>row.backend===backend);return structuredClone({...common('dut_control_route'),route:record,sources:record.sources.map(id=>sources.sources.find(source=>source.id===id)),stable_releases:sources.stable_releases.filter(release=>record.sources.includes(release.source_id))});};
const source=id=>structuredClone({...common('dut_control_source'),record:sources.sources.find(row=>row.id===id),stable_releases:sources.stable_releases.filter(row=>row.source_id===id),dependency_declarations:sources.dependency_declarations.filter(row=>row.source_id===id),manufacturing_member_checks:sources.manufacturing_references.already_acquired_member_checks.filter(row=>row.source_id===id),backends:paths.paths.filter(row=>row.sources.includes(id)).map(row=>row.backend)});

test('all fixed 30 raw source records preserve licenses partial scope and unassessed flags',()=>{
 for(const value of sources.sources){const copy=validateDutSourceRecord(value,value.id);assert.deepEqual(copy,value);const originalLength=value.license_evidence_files.length;copy.license_evidence_files.push({path:'changed'});assert.equal(value.license_evidence_files.length,originalLength);}
 const partial=validateDutSourceRecord(sources.sources.find(value=>value.id==='DUT-G13'),'DUT-G13');
 assert.equal(partial.source_file_count,258);assert.equal(partial.status,'source_files_and_release_acquired');assert(!Object.hasOwn(partial,'snapshot_file_count'));
 const hid=validateDutSourceRecord(sources.sources.find(value=>value.id==='DUT-S01'),'DUT-S01');assert.equal(hid.parent_source_id,'DUT-G18');assert.equal(hid.license_evidence_files.length,4);
});
test('all nine route records retain bool string ADB conditions and empty OEM candidates',()=>{
 for(const value of paths.paths)assert.deepEqual(validateDutRouteRecord(value,value.backend),value);
 const oem=validateDutRouteRecord(paths.paths.find(value=>value.backend==='oem_sdk_cli'),'oem_sdk_cli');assert.deepEqual(oem.sources,[]);assert.equal(oem.acquisition_status,'public_anyway_interface_not_verified');
 const android=paths.paths.find(value=>value.backend==='android_ui_and_test');assert.match(formatAdbIndependence(android.independent_of_adb),/ADB.*의존/);assert.match(formatAdbIndependence(android.independent_of_adb),/usually_no_for_standard_bootstrap/);
 assert.match(formatAdbIndependence(false),/false/);assert.match(formatAdbIndependence(true),/true/);
 assert.throws(()=>formatAdbIndependence('true'),/invalid_dut_catalog_response/);
});
test('wrong selected IDs flags and incomplete source evidence cannot become a successful view',()=>{
 const value=sources.sources[0];assert.throws(()=>validateDutSourceRecord(value,'DUT-G01'),/invalid_dut_catalog_response/);
 for(const mutate of [v=>v.hardware_verified=true,v=>v.vendor_code_executed=true,v=>v.adapter_integrated=true,v=>v.device_or_firmware_supported='supported',v=>v.commit='bad',v=>delete v.license_evidence_files[0].sha256]){
  const bad=structuredClone(value);mutate(bad);assert.throws(()=>validateDutSourceRecord(bad,value.id),/invalid_dut_catalog_response/);
 }
 const route=structuredClone(paths.paths[0]);route.independent_of_adb={value:true};assert.throws(()=>validateDutRouteRecord(route,'adb'),/invalid_dut_catalog_response/);
 let called=false;const bad={...value};Object.defineProperty(bad,'commit',{enumerable:true,get(){called=true;throw Error('PRIVATE');}});assert.throws(()=>validateDutSourceRecord(bad,value.id),/^Error: invalid_dut_catalog_response$/);assert.equal(called,false);
});
test('only explicit HTTP sources are links and member paths remain plain text',()=>{
 assert.equal(safeDutSourceHref('https://example.com/a?q=x'),'https://example.com/a?q=x');
 for(const value of ['javascript:alert(1)','file:///private','NOTICE','C:\\private\\file','https://user:password@example.com','https://example.com/\nsecret'])assert.equal(safeDutSourceHref(value),null);
 const value=structuredClone(sources.sources[0]);value.license_review_status='<img src=x onerror=alert(1)>';assert.equal(validateDutSourceRecord(value,value.id).license_review_status,value.license_review_status);
});
test('new source route or references selection invalidates every older response ticket',()=>{
 const gate=createDutReadGate(),route=gate.begin('route','adb'),source=gate.begin('source','DUT-G13');assert(!gate.current(route));assert(gate.current(source));
 const references=gate.begin('references',null);assert(!gate.current(source));assert(gate.current(references));assert(Object.isFrozen(references));
 for(const [kind,id] of [['route','ADB'],['source','G13'],['references','path'],['dispatcher','adb']])assert.throws(()=>gate.begin(kind,id),/invalid_dut_catalog_response/);
});
test('owner summary has exactly twelve keys and compares a recorded environment without support promotion',()=>{
 const value=summary();assert.deepEqual(validateDutSummary(value),value);
 for(const mutate of [v=>v.schema_version=true,v=>v.extra='private',v=>v.counts.source_units=31,v=>v.hardware_verified=true,
  v=>v.source_code_executed=true,v=>v.automatic_fallback_enabled=true,v=>v.support_status='supported',v=>delete v.provenance.main_prompt_v5_sha256]){
  const bad=summary();mutate(bad);assert.throws(()=>validateDutSummary(bad),/^Error: invalid_dut_catalog_response$/);
 }
});
test('all nine owner route DTOs retain original source order and empty OEM releases',()=>{
 assert.deepEqual(validateDutRoutes(paths.paths),paths.paths);
 for(const record of paths.paths){const value=route(record.backend);assert.deepEqual(validateDutRoute(value,record.backend),value);}
 const oem=validateDutRoute(route('oem_sdk_cli'),'oem_sdk_cli');assert.deepEqual(oem.sources,[]);assert.deepEqual(oem.stable_releases,[]);
 const wrong=route('android_ui_and_test');wrong.sources.reverse();assert.throws(()=>validateDutRoute(wrong,'android_ui_and_test'),/invalid_dut_catalog_response/);
 const bad=route('oem_sdk_cli');bad.route.independent_of_adb=true;assert.throws(()=>validateDutRoute(bad,'oem_sdk_cli'),/invalid_dut_catalog_response/);
});
test('all thirty owner source DTOs preserve sparse licenses releases declarations and existing members',()=>{
 for(const raw of sources.sources){const value=source(raw.id);assert.deepEqual(validateDutSource(value,raw.id),value);}
 assert.deepEqual(validateDutSource(source('DUT-A02'),'DUT-A02').record.license_evidence_files,[]);
 assert.deepEqual(validateDutSource(source('DUT-G21'),'DUT-G21').record.license_evidence_files,[]);
 const g13=validateDutSource(source('DUT-G13'),'DUT-G13');assert.equal(g13.stable_releases[0].release_version,'0.6.9');assert.equal(g13.record.source_file_count,258);
 const g01=validateDutSource(source('DUT-G01'),'DUT-G01');assert.equal(g01.stable_releases[0].requires_python,'>=3.11');assert.equal(g01.dependency_declarations[0].declarations['requires-python'],'>=3.14');
 assert.equal(validateDutSource(source('DUT-G21'),'DUT-G21').manufacturing_member_checks[0].manufacturing_test_code_present,true);
 assert.throws(()=>validateDutSource(source('DUT-G13'),'DUT-G01'),/invalid_dut_catalog_response/);
});
test('manufacturing references preserve two acquired members and nine unacquired reviewed references',()=>{
 const value=sources.manufacturing_references;assert.deepEqual(validateDutReferences(value),value);
 for(const mutate of [v=>v.newly_acquired_repository_archives=9,v=>v.additional_reviewed_references[0].whole_repository_archive_acquired=true,
  v=>v.already_acquired_member_checks[0].product_support='supported',v=>v.additional_reviewed_references.pop()]){
  const bad=structuredClone(value);mutate(bad);assert.throws(()=>validateDutReferences(bad),/invalid_dut_catalog_response/);
 }
});

// DELTA015 DTO fixtures, never actual API evidence.
const delta=read('dut_manufacturer_delta.json');
const deltaCommon=kind=>({schema_version:1,kind,catalog_state:'read_only_acquisition_delta',...flags});
const deltaSummary=()=>structuredClone({...deltaCommon('dut_manufacturer_delta_summary'),counts:delta.counts,provenance:delta.provenance,source_reuse_publication_approved:false});
const deltaReference=id=>structuredClone({...deltaCommon('dut_manufacturer_reference'),reference_id:id,snapshot_reference:sources.manufacturing_references.additional_reviewed_references.find(row=>row.reference_id===id),acquisition_delta:delta.records.find(row=>row.reference_id===id) ?? null});
test('delta exact ten-key summary distinguishes selected six groups and twenty-two private references',()=>{
 assert.deepEqual(dutModel.validateDutAcquisitionSummary(deltaSummary()),deltaSummary());
 for(const mutate of [v=>v.schema_version=true,v=>v.extra=1,v=>v.counts.source_groups=9,v=>v.counts.source_file_references=21,v=>v.counts.public_original_or_code_payload_files=1,v=>v.source_reuse_publication_approved=true,v=>v.hardware_verified=true,v=>v.provenance.parent_catalog_sha256['dut_paths.json']='0'.repeat(64)]){
  const bad=deltaSummary();mutate(bad);assert.throws(()=>dutModel.validateDutAcquisitionSummary(bad),/^Error: invalid_dut_catalog_response$/);
 }
});
test('delta six raw wrappers preserve optional fields and reused LICENSE without adding absent keys',()=>{
 const copy=dutModel.validateDutAcquisitionRecords(delta.records);assert.deepEqual(copy,delta.records);
 assert.equal(copy.reduce((sum,row)=>sum+row.record.files.length,0),22);
 const license=copy[0].record.files.at(-1);assert(!Object.hasOwn(license,'download_url'));assert.equal(license.new_distinct_payload_original,false);
 assert(!Object.hasOwn(copy[1].record,'requires_python'));assert(!Object.hasOwn(copy[1].record,'declared_package_version'));
 assert.deepEqual(copy.at(-1).record.physical_pages,[119,120,152]);assert(!Object.hasOwn(copy.at(-1).record,'repository_commit'));
 copy[0].record.files.pop();assert.equal(delta.records[0].record.files.length,7);
});
test('delta malformed identities links counts optional keys and support promotions cannot become success',()=>{
 for(const mutate of [v=>v.pop(),v=>v.reverse(),v=>v[1].reference_id=v[0].reference_id,v=>v[0].record.source_id=v[1].record.source_id,
  v=>v[0].whole_repository_archive_acquired=true,v=>v[0].record.runtime_or_physical_validation=true,v=>v[0].record.source_reuse_publication_approved=true,
  v=>v[0].record.device_or_Firmware_support='supported',v=>v[0].record.files[0].public_payload_included=true,v=>delete v[0].record.files[0].sha256,
  v=>v[0].record.files[0].bytes=true,v=>v[0].record.files.at(-1).new_distinct_payload_original=true,v=>v[1].record.requires_python=null]){
  const bad=structuredClone(delta.records);mutate(bad);assert.throws(()=>dutModel.validateDutAcquisitionRecords(bad),/^Error: invalid_dut_catalog_response$/);
 }
});
test('all nine delta reference DTOs retain literal old snapshot and six deltas with three explicit nulls',()=>{
 let nulls=0;for(const record of sources.manufacturing_references.additional_reviewed_references){const value=deltaReference(record.reference_id),copy=dutModel.validateDutAcquisitionReference(value,record.reference_id);assert.deepEqual(copy,value);assert.equal(copy.snapshot_reference.repository_commit_pinned,null);assert.equal(copy.snapshot_reference.new_local_source_copy_saved,false);if(copy.acquisition_delta===null)nulls++;}
 assert.equal(nulls,3);
 for(const mutate of [v=>v.reference_id='usb_type_c_reference',v=>v.snapshot_reference.reference_id='usb_type_c_reference',v=>v.snapshot_reference.repository_commit_pinned='1'.repeat(40),v=>v.acquisition_delta=null,v=>v.acquisition_delta.record.hardware_verified=false]){
  const bad=deltaReference('qualcomm_diag');mutate(bad);assert.throws(()=>dutModel.validateDutAcquisitionReference(bad,'qualcomm_diag'),/^Error: invalid_dut_catalog_response$/);
 }
 assert.throws(()=>dutModel.validateDutAcquisitionReference(deltaReference('qualcomm_diag'),'qualcomm_diag\n'),/^Error: invalid_dut_catalog_response$/);
});
test('acquisition tickets share selection generation with route source and reference navigation',()=>{
 const gate=createDutReadGate(),old=gate.begin('route','adb'),delta=gate.begin('acquisition','qualcomm_diag');assert(!gate.current(old));assert(gate.current(delta));
 const next=gate.begin('source','DUT-G13');assert(!gate.current(delta));assert(gate.current(next));
 for(const id of ['', 'Qdiag','diag\n','diag/secret','a'.repeat(97)])assert.throws(()=>gate.begin('acquisition',id),/invalid_dut_catalog_response/);
});
