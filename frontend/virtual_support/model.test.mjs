import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {parseVirtualSupport, validateVirtualSupport, safeSourceURL} from './model.mjs';

const require=createRequire(import.meta.url),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const python=require('../managed_paths.cjs').python(root);
const run=spawnSync(python,['-B','-X','utf8','-c','import json; from labflow.virtual_support_view import build_virtual_support_view; print(json.dumps(build_virtual_support_view(),ensure_ascii=False))'],
  {cwd:root,encoding:'utf8',windowsHide:true,maxBuffer:1048576,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONUTF8:'1'}});
assert.equal(run.status,0,run.stderr);
const wire=run.stdout,fixture=JSON.parse(wire),copy=()=>structuredClone(fixture);
const rejects=change=>{const value=copy();change(value);assert.throws(()=>validateVirtualSupport(value),/invalid_virtual_support/);};

test('actual Python fixed catalog DTO retains the 64-profile denominator and separate 12-command contract',()=>{
  const value=parseVirtualSupport(wire);
  assert.equal(value.profile_count,64);
  assert(value.profiles.some(p=>p.model==='N1911A'));
  assert(!value.profiles.some(p=>p.model==='N1914A'));
  assert.equal(value.adapter_contracts[0].model,'N1914A');
  assert.equal(value.adapter_contracts[0].commands.length,12);
});
test('authority, physical verification, linked virtual evidence and installed binding cannot be promoted',()=>{
  for(const key of ['hardware_verified','execution_authority'])rejects(v=>{v[key]=true;});
  rejects(v=>{v.virtual_verification='passed';});
  rejects(v=>{v.profiles[0].materials.installed_equipment_binding_established=true;});
  rejects(v=>{v.profiles[0].virtual_role.protocol_scope=true;});
  rejects(v=>{v.profiles[0].protocol.status='supported';});
});
test('source links accept public HTTP(S) links without executing or fetching them',()=>{
  assert.equal(safeSourceURL('https://example.com/a.pdf?edition=1'),'https://example.com/a.pdf?edition=1');
  for(const url of ['javascript:alert(1)','file:///C:/private','https://name:password@example.com/','https://example.com/\nprivate','https://example.com\\private'])
    assert.throws(()=>safeSourceURL(url),/invalid_virtual_support/);
  rejects(v=>{v.profiles.find(p=>p.materials.candidates.some(c=>c.sources.length)).materials.candidates.find(c=>c.sources.length).sources[0].url='data:text/html,private';});
});
test('unknown fields, provenance substitution and profile-count drift fail closed',()=>{
  rejects(v=>{v.raw_private_auxiliary='PRIVATE_CANARY';});
  rejects(v=>{v.provenance.material_source_commit='685e484ba5e4c8226626a71aaa100366b9b4e40b';});
  rejects(v=>{v.profile_count=65;});
  rejects(v=>{v.profiles[0].evidence_refs[0].path='C:/private';});
});
test('the exact declared adapter scope cannot be widened or aliased',()=>{
  rejects(v=>{v.adapter_contracts[0].window=2;});
  rejects(v=>{v.adapter_contracts[0].window=true;});
  rejects(v=>{v.adapter_contracts[0].model='N1911A';});
  rejects(v=>{v.adapter_contracts[0].commands.push('CAL:ALL');});
  rejects(v=>{v.adapter_contracts[0].real_support='supported';});
});
test('custom prototypes, accessors, sparse arrays and invalid Unicode are refused',()=>{
  const inherited=Object.assign(Object.create({hidden:true}),copy());
  assert.throws(()=>validateVirtualSupport(inherited),/invalid_virtual_support/);
  const accessor=copy();let invoked=0;
  Object.defineProperty(accessor,'kind',{enumerable:true,get(){invoked++;return 'virtual_support_view';}});
  assert.throws(()=>validateVirtualSupport(accessor),/invalid_virtual_support/);assert.equal(invoked,0);
  rejects(v=>{delete v.profiles[1];});
  rejects(v=>{v.profiles[0].model='\ud800';});
});
test('validated metadata is detached from subsequent caller mutation',()=>{
  const input=copy(),validated=validateVirtualSupport(input);
  input.profiles[0].virtual_role.action_names.length=0;
  input.adapter_contracts[0].commands.length=0;
  assert(validated.profiles[0].virtual_role.action_names.length>0);
  assert.equal(validated.adapter_contracts[0].commands.length,12);
});
test('wire and native snapshot limits reject excessive data and malformed JSON',()=>{
  assert.throws(()=>parseVirtualSupport(' '.repeat(524289)),/invalid_virtual_support/);
  assert.throws(()=>parseVirtualSupport('{'),/invalid_virtual_support/);
  rejects(v=>{v.profiles[0].variant='x'.repeat(4097);});
});
