/* Raw-record presentation contracts; API wrapper DTO is supplied by DUT010. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
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
