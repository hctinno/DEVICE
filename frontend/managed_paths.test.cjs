const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),test=require('node:test');
const evidence=path.resolve(__dirname,'../../../runs/migration-20261031/toolchains/frontend-tests');
fs.mkdirSync(evidence,{recursive:true});
test('managed defaults ignore a repository .venv and emit runs outputs',()=>{
 const api=require('./managed_paths.cjs');
 const temp=fs.mkdtempSync(path.join(evidence,'m-')),development=path.join(temp,'.local/development');
 const source=path.join(development,'workspaces/fixture');fs.mkdirSync(source,{recursive:true});
 fs.writeFileSync(path.join(development,'layout.json'),JSON.stringify({schema_version:1,project_root_relative:'../..',
  directories:{integration:'integration',workspaces:'workspaces',runs:'runs',toolchains:'toolchains',archive:'archive'},workspaces:[],path_aliases:[],control_root:'runs/control/DGMAutoLab'}));
 assert.equal(api.python(source),path.join(development,'toolchains/python',process.platform==='win32'?'Scripts/python.exe':'bin/python'));
 const first=api.output(source,'browser'),second=api.output(source,'browser');
 assert.equal(path.dirname(first),path.join(development,'runs/browser-checks'));
 assert.notEqual(first,second);assert.equal(fs.existsSync(first),false);
 assert.throws(()=>api.output(source,'../escape'));
 assert.throws(()=>api.stage(source));
 const staged=path.join(development,'runs/source-stage');fs.mkdirSync(staged,{recursive:true});
 assert.equal(api.stage(staged),staged);
 const {reserveEvidence}=require('./intake_fixture_browser_check.cjs');
 assert.throws(()=>reserveEvidence(source),/managed_browser_stage_required/);
 assert.equal(fs.existsSync(path.join(source,'.local')),false);
 const evidenceRoot=reserveEvidence(staged);
 assert.equal(path.dirname(evidenceRoot),path.join(staged,'.local'));
});
test('unmanaged or malformed layout does not fall back to .venv',()=>{
 const api=require('./managed_paths.cjs');
 assert.throws(()=>api.python(path.parse(evidence).root));
 const temp=fs.mkdtempSync(path.join(evidence,'b-')),development=path.join(temp,'.local/development');
 fs.mkdirSync(development,{recursive:true});fs.writeFileSync(path.join(development,'layout.json'),'{}');
 assert.throws(()=>api.python(development));
});
