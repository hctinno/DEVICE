import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import fixture from './browser_check.cjs';
let model;try{model=await import('./model.mjs');}catch(error){if(error.code!=='ERR_MODULE_NOT_FOUND')throw error;model={};}
const bundle=fixture.createContractBundle;
const invalid=action=>assert.throws(action,/^Error: invalid_fcc_case_response$/);
test('exact twelve-key summary keeps unknown population independent stages rights and blocked official access',()=>{
 const value=bundle().summary,copy=model.validateFccCaseSummary(value);assert.deepEqual(copy,value);assert.equal(copy.counts.candidate_count,null);assert.equal(copy.counts.normative_comparison_completed_cases,null);assert.equal(copy.searches[0].status,'blocked');assert.equal(copy.documents[0].exhibits.length,2);copy.scope.search_scope_notes.push('changed');assert.equal(value.scope.search_scope_notes.length,1);
});
test('case nine-key DTO preserves reviewed zero false inference basis and thirteen-key literal evidence',()=>{
 const value=bundle(),copy=model.validateFccCaseDetail(value.cases[0],'SYNTH-CASE-A',value.summary);assert.deepEqual(copy,value.cases[0]);assert.equal(copy.case.claims.find(c=>c.claim_id==='zero').value,0);assert.equal(copy.case.claims.find(c=>c.claim_id==='false').value,false);assert.equal(copy.case.claims.find(c=>c.claim_id==='class').basis,'developer_inference');assert.equal(Object.keys(copy.case.claims[0].evidence[0]).length,13);assert.equal(copy.case.preview.evaluation_group.eligible,true);assert.equal(copy.verification.model_execution_verified,false);
});
test('pending unknown gaps ambiguity conflicts and original method editions remain independent',()=>{
 const value=bundle(),copy=model.validateFccCaseDetail(value.cases[1],'SYNTH-CASE-B',value.summary);assert.equal(copy.case.preview.issuer_class,'unknown');assert.equal(copy.case.preview.scope_status,'pending');assert.equal(copy.case.preview.methods[0],'SYNTHETIC METHOD 2023');assert.equal(copy.case.claims.find(c=>c.claim_id==='gap').value,null);assert.deepEqual(copy.case.claims.find(c=>c.claim_id==='conflict').value,['2025-05-01','2025-06-01']);assert.equal(copy.case.relations[0].status,'unresolved');
});
test('wrong exact keys nonfinite values bool counts and promoted verification cannot become a successful summary',()=>{
 for(const mutate of [v=>v.extra='PRIVATE',v=>delete v.scope,v=>v.schema_version=true,v=>v.verification.physical_verified=true,v=>v.verification.coverage_complete=true,v=>v.scope.population_status='complete',v=>v.counts.acquired_unique_pdfs=true,v=>v.counts.candidate_count=2,v=>v.counts.model_evaluated_cases=1,v=>v.counts.scope_counts.in_scope=9,v=>v.scope.cutoff_at='2026-99-99T12:00:00+09:00',v=>v.searches[0].searched_at='2027-01-01T00:00:00+09:00',v=>v.documents[0].rights.external_model_use_allowed=true,v=>v.documents[0].source_path='C:\\PRIVATE\\report.pdf']){
  const bad=bundle().summary;mutate(bad);invalid(()=>model.validateFccCaseSummary(bad));
 }
});
test('wrong selected case preview document pages literal flags and line/hash mismatches are rejected',()=>{
 for(const mutate of [v=>v.case.case_id='WRONG',v=>v.case.preview.methods=['different edition'],v=>v.documents[0].sha256='f'.repeat(64),v=>v.case.claims[0].evidence[0].source_sha256='f'.repeat(64),v=>v.case.claims[0].evidence[0].file_page=2,v=>v.case.claims[0].evidence[0].text_sha256='f'.repeat(64),v=>v.case.claims[0].evidence[0].line_end=999,v=>v.case.claims[0].evidence[0].literal_verified=false,v=>v.case.claims[0].evidence[0].file_page=true,v=>v.case.claims[0].evidence[0].local_path='C:\\PRIVATE\\report.pdf',v=>v.case.claims[0].value=null]){
  const value=bundle(),bad=value.cases[0];mutate(bad);invalid(()=>model.validateFccCaseDetail(bad,'SYNTH-CASE-A',value.summary));
 }
 invalid(()=>model.validateFccCaseDetail(bundle().cases[0],'SYNTH-CASE-A\n'));
});
test('complete transport binds one exact case per preview and matching corpus synthetic documents and stage counts',()=>{
 const value=bundle();assert.deepEqual(model.validateFccCaseBundle(value),value);
 for(const mutate of [v=>v.cases.pop(),v=>v.cases.push(v.cases[0]),v=>v.cases[0].corpus_id='OTHER',v=>v.cases[0].synthetic=false,v=>v.summary.counts.reviewed_claim_count=0]){const bad=bundle();mutate(bad);invalid(()=>model.validateFccCaseBundle(bad));}
});
test('plain finite detached JSON has byte depth descriptor symbol and duplicate-key boundaries without invoking hooks',()=>{
 const value=bundle().summary;let invoked=false;Object.defineProperty(value,'kind',{enumerable:true,get(){invoked=true;return 'fcc_report_case_summary';}});invalid(()=>model.validateFccCaseSummary(value));assert.equal(invoked,false);
 const bad=bundle().summary;bad[Symbol('private')]=1;invalid(()=>model.validateFccCaseSummary(bad));
 invalid(()=>model.parseFccCaseJson('{"schema_version":1,"schema_version":1}'));
 invalid(()=>model.parseFccCaseJson('{"number":1e999}'));
 invalid(()=>model.parseFccCaseJson('{"quote":"\\ud800"}'));
 invalid(()=>model.parseFccCaseJson(' '.repeat(8*1024*1024+1)));
 assert.deepEqual(model.parseFccCaseJson('{"value":false,"zero":0}'),{value:false,zero:0});
});
test('literal strings stay unchanged safe HTTP links remain explicit and local source paths are refused',()=>{
 const value=bundle(),quote='<img src=x onerror="window.injected=true">';value.cases[0].case.claims[0].evidence[0].quote=quote;assert.equal(model.validateFccCaseDetail(value.cases[0],'SYNTH-CASE-A',value.summary).case.claims[0].evidence[0].quote,quote);
 assert.equal(model.safeFccCaseHref('https://example.invalid/a?q=x'),'https://example.invalid/a?q=x');for(const url of ['javascript:alert(1)','file:///private/report.pdf','https://user:secret@example.invalid','https://example.invalid/\nprivate'])assert.equal(model.safeFccCaseHref(url),null);
 const bad=bundle().summary;bad.scope.search_scope_notes=['C:\\PRIVATE\\source\\report.pdf'];invalid(()=>model.validateFccCaseSummary(bad));
});
test('new selection refresh and destroy invalidate every older response ticket without shared selection state',()=>{
 const first=model.createFccCaseReadGate(),second=model.createFccCaseReadGate(),old=first.begin(),current=first.begin();assert(!first.current(old));assert(first.current(current));first.clear();assert(!first.current(current));const independent=second.begin();assert(second.current(independent));assert(Object.isFrozen(independent));
});
test('field and timestamp grammars reject trailing linebreaks rather than matching a prefix',()=>{
 const summary=bundle().summary;summary.scope.cutoff_at+='\n';invalid(()=>model.validateFccCaseSummary(summary));
 const value=bundle();value.cases[0].case.claims[0].field+='\n';invalid(()=>model.validateFccCaseDetail(value.cases[0],'SYNTH-CASE-A',value.summary));
});
test('an empty corpus is a valid unconfirmed snapshot with no invented progress',()=>{
 const value=bundle().summary;value.documents=[];value.case_previews=[];for(const key of Object.keys(value.counts))if(typeof value.counts[key]==='number')value.counts[key]=0;for(const key of Object.keys(value.counts.scope_counts))value.counts.scope_counts[key]=0;
 assert.deepEqual(model.validateFccCaseSummary(value),value);
});
test('public empty-user parser metadata stays literal and cannot make an uncitable page valid evidence',()=>{
 const value=bundle();for(const document of [value.summary.documents[0],value.cases[0].documents[0]]){document.extraction.parser.name='pypdf-public-empty-user-password';document.extraction.issues.push({code:'public_empty_user_password_read',file_page:null});}
 assert.deepEqual(model.validateFccCaseBundle(value),value);assert.equal(value.summary.verification.normative_compliance_verified,false);
 value.cases[0].case.claims[0].evidence[0].file_page=2;invalid(()=>model.validateFccCaseDetail(value.cases[0],'SYNTH-CASE-A',value.summary));
});
test('known issuer classification requires separately reviewed legal name and address evidence',()=>{
 for(const mutate of [v=>v.case.claims=v.case.claims.filter(c=>c.field!=='issuer.address'),v=>v.case.claims.find(c=>c.field==='issuer.legal_name').basis='developer_inference',v=>v.case.claims.find(c=>c.field==='issuer.classification').basis='synthetic_policy']){const value=bundle();mutate(value.cases[0]);invalid(()=>model.validateFccCaseDetail(value.cases[0],'SYNTH-CASE-A',value.summary));}
});
test('exhibit access time remains an independent recorded timestamp without an undeclared cutoff rule',()=>{
 const value=bundle().summary;value.documents[0].exhibits[0].accessed_at='2026-10-24T13:00:00+09:00';assert.deepEqual(model.validateFccCaseSummary(value),value);
});
test('CLI requires explicit modes actual JSON pin and rejects duplicate or unknown overrides',()=>{
 assert.deepEqual(fixture.parseOptions(['--mode','contract']),{mode:'contract',bundle:undefined,sha256:undefined});
 for(const argv of [[],['--mode','actual'],['--mode','contract','--bundle','','--sha256',''],['--mode','contract','--output','private'],['--mode','contract','--mode','actual'],['--mode','actual','--bundle',path.resolve('report.pdf'),'--sha256','a'.repeat(64)],['--mode','actual','--bundle',path.resolve('bundle.json'),'--sha256','a'.repeat(64)+'\n']])assert.throws(()=>fixture.parseOptions(argv),/^Error: invalid_configuration$/);
});
test('explicit JSON loader verifies original bytes pin regular-file and size boundaries before decoding',()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'fcc-case-024-')),file=path.join(folder,'bundle.json'),bytes=Buffer.from('{"synthetic":true}'),pin=createHash('sha256').update(bytes).digest('hex');let passed=false;
 try{fs.writeFileSync(file,bytes);assert.deepEqual(fixture.readPinned(file,pin,32),bytes);assert.throws(()=>fixture.readPinned(file,'0'.repeat(64),32),/fcc_case_bundle_pin_mismatch/);assert.throws(()=>fixture.readPinned(file,pin,bytes.length-1),/fcc_case_transport_limit/);assert.throws(()=>fixture.readPinned(folder,pin,32));passed=true;}
 finally{if(passed){assert.equal(path.dirname(path.resolve(folder)),path.resolve(os.tmpdir()));assert(path.basename(folder).startsWith('fcc-case-024-'));fs.rmSync(folder,{recursive:true});}}
});
test('integers beyond exact browser precision are refused instead of silently rounding report values',()=>{
 invalid(()=>model.parseFccCaseJson('{"value":9007199254740993}'));
 const value=bundle();value.cases[0].case.claims[0].value=Number.MAX_SAFE_INTEGER+1;invalid(()=>model.validateFccCaseDetail(value.cases[0],'SYNTH-CASE-A',value.summary));
});
