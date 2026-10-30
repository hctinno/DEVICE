const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),test=require('node:test');
const evidence=require('./managed_paths.cjs').output(path.resolve(__dirname,'..'),'managed-path-tests');
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

function stageFixture(){
 const temp=fs.mkdtempSync(path.join(evidence,'s-')),development=path.join(temp,'.local/development');
 const runs=path.join(development,'runs'),outside=path.join(development,'workspaces/source');
 fs.mkdirSync(runs,{recursive:true});fs.mkdirSync(outside,{recursive:true});
 fs.writeFileSync(path.join(development,'layout.json'),JSON.stringify({schema_version:1,project_root_relative:'../..',
  directories:{integration:'integration',workspaces:'workspaces',runs:'runs',toolchains:'toolchains',archive:'archive'},workspaces:[],path_aliases:[],control_root:'runs/control/DGMAutoLab'}));
 return {development,runs,outside};
}
const api=require('./managed_paths.cjs'),{reserveEvidence}=require('./intake_fixture_browser_check.cjs');
for(const boundary of ['runs','ancestor','stage','local'])test('rejects '+boundary+' junction before reserving evidence',()=>{
 const {development,runs,outside}=stageFixture();
 let stage=path.join(runs,'stage');
 if(boundary==='runs'){
  fs.renameSync(runs,path.join(development,'plain-runs'));
  fs.mkdirSync(path.join(outside,'stage'));fs.symlinkSync(outside,runs,'junction');
 }else if(boundary==='ancestor'){
  fs.mkdirSync(path.join(outside,'stage'));fs.symlinkSync(outside,path.join(runs,'linked'),'junction');
  stage=path.join(runs,'linked/stage');
 }else if(boundary==='stage')fs.symlinkSync(outside,stage,'junction');
 else{fs.mkdirSync(stage);fs.symlinkSync(outside,path.join(stage,'.local'),'junction');}
 assert.throws(()=>reserveEvidence(stage),/managed_browser_.*(reparse|physical)/);
 assert.deepEqual(fs.readdirSync(outside),boundary==='runs'||boundary==='ancestor'?['stage']:[]);
 if(boundary==='runs'||boundary==='ancestor')assert.deepEqual(fs.readdirSync(path.join(outside,'stage')),[]);
});
test('rejects a stage junction even when its target is also inside runs',()=>{
 const {runs}=stageFixture(),plain=path.join(runs,'plain'),linked=path.join(runs,'linked');
 fs.mkdirSync(plain);fs.symlinkSync(plain,linked,'junction');
 assert.throws(()=>reserveEvidence(linked),/managed_browser_.*reparse/);
 assert.deepEqual(fs.readdirSync(plain),[]);
});
test('rejects a linked proof ancestor before creating any output leaf',()=>{
 const {runs,outside}=stageFixture(),stage=path.join(runs,'stage'),local=path.join(stage,'.local');
 fs.mkdirSync(local,{recursive:true});fs.symlinkSync(outside,path.join(local,'linked'),'junction');
 assert.throws(()=>reserveEvidence(stage,'.local/linked/new'),/managed_browser_.*(reparse|physical)/);
 assert.deepEqual(fs.readdirSync(outside),[]);
});
test('validates explicit proof root before creating stage .local',()=>{
 const {runs,outside}=stageFixture(),stage=path.join(runs,'stage');fs.mkdirSync(stage);
 assert.throws(()=>api.proof(stage,outside),/managed_browser_proof_required/);
 assert.equal(fs.existsSync(path.join(stage,'.local')),false);
 const local=path.join(stage,'.local');fs.mkdirSync(local);
 fs.symlinkSync(outside,path.join(local,'linked'),'junction');
 assert.throws(()=>api.proof(stage,path.join(local,'linked')),/managed_browser_.*(reparse|physical)/);
 assert.deepEqual(fs.readdirSync(outside),[]);
});
test('ordinary runs stage accepts fresh and explicitly parented proof outputs',()=>{
 const {runs}=stageFixture(),stage=path.join(runs,'stage');fs.mkdirSync(stage);
 assert.equal(api.stage(stage),stage);
 const fresh=reserveEvidence(stage);assert.equal(path.dirname(fresh),path.join(stage,'.local'));
 const parent=path.join(stage,'.local/proof');fs.mkdirSync(parent);
 assert.equal(api.proof(stage,parent),parent);
 const leaf=reserveEvidence(stage,'.local/proof/new');
 assert.equal(fs.realpathSync(leaf),leaf);
 assert.throws(()=>reserveEvidence(stage,'.local/proof/new'),/already exists/);
});
test('an escaping requested output is rejected before creating .local',()=>{
 const {runs}=stageFixture(),stage=path.join(runs,'stage');fs.mkdirSync(stage);
 assert.throws(()=>reserveEvidence(stage,'../escape'),/managed_browser_proof_required/);
 assert.equal(fs.existsSync(path.join(stage,'.local')),false);
});
test('default browser output rejects a linked runs output parent',()=>{
 const {runs,outside}=stageFixture();fs.symlinkSync(outside,path.join(runs,'browser-checks'),'junction');
 assert.throws(()=>api.output(outside,'browser'),/managed_browser_.*(reparse|physical)/);
 assert.deepEqual(fs.readdirSync(outside),[]);
});
test('integration and workspaces fixture sources both allocate under the declared runs',()=>{
 const {development,runs}=stageFixture();
 for(const relative of ['integration','workspaces/dev1']){
  const source=path.join(development,relative);fs.mkdirSync(source,{recursive:true});
  assert.equal(path.dirname(api.output(source,'portable-test')),path.join(runs,'browser-checks'));
 }
 assert.equal(fs.existsSync(path.join(path.dirname(development),'runs')),false);
});
