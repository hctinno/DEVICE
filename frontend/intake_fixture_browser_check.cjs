/* Actual synthetic CLI -> same-origin browser acceptance. No API fixture routes. */
const assert = require('node:assert/strict');
const {spawn, spawnSync} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const OWN = path.resolve(__dirname, '..');
const SOURCES = ['labflow/__init__.py', 'labflow/intake_fixture_check.py', 'labflow/intake_fixture_bridge.py',
  'labflow/virtual_fleet/method_adapter.py', 'labflow/intake_fixture_jobs.py', 'labflow/intake_jobs.py',
  'labflow/intake_worker.py', 'labflow/intake_analysis.py', 'labflow/intake_documents.py',
  'labflow/document_extract.py', 'labflow/store.py', 'labflow/schema.sql', 'labflow/ui_read_model.py',
  'labflow/ui_server.py', 'frontend/app.js', 'frontend/model.mjs', 'frontend/intake_flow_model.mjs',
  'frontend/virtual_fleet/harness_model.mjs', 'frontend/index.html', 'frontend/styles.css'];
const hash = data => createHash('sha256').update(data).digest('hex');
const exists = file => {try {fs.lstatSync(file); return true;} catch (error) {if (error.code === 'ENOENT') return false; throw error;}};
const within = (parent, target) => {const relative=path.relative(parent,target); return relative && !relative.startsWith('..'+path.sep) && relative !== '..' && !path.isAbsolute(relative);};
const samePath = (left, right) => path.relative(path.resolve(left),path.resolve(right)) === '';

function evidenceAncestors(output, own) {
  const parents=[];
  for (let parent=path.dirname(output); !samePath(parent,own);) {
    parents.push(parent);
    const next=path.dirname(parent);
    assert(!samePath(next,parent), 'Evidence ancestors did not reach the checkout root');
    parent=next;
  }
  return parents;
}

function readConfig(env = process.env) {
  const kind=env.FLOW_DOCUMENT_KIND || 'both';
  assert(['text','pdf','both'].includes(kind), 'Invalid document kind: use text, pdf or both');
  const power=env.FLOW_POWER_DBM === undefined ? -4 : Number(env.FLOW_POWER_DBM);
  assert((env.FLOW_POWER_DBM === undefined || String(env.FLOW_POWER_DBM).trim()) && Number.isFinite(power) && power >= -30 && power <= 20, 'Invalid power: use -30..20 dBm');
  return {source:path.resolve(env.FLOW_SOURCE_ROOT || OWN), python:env.FLOW_PYTHON || require('./managed_paths.cjs').python(OWN),
    kinds:kind === 'both' ? ['text','pdf'] : [kind], power, requested:env.FLOW_OUTPUT_ROOT};
}

function reserveEvidence(own, requested) {
  const managed=require('./managed_paths.cjs');
  own=managed.stage(path.resolve(own));
  const local=path.join(own,'.local');
  const output=requested ? managed.proof(own,requested) : null;
  if(requested){
    assert(within(local,output), 'Evidence must stay inside this checkout .local');
    assert(!exists(output), 'Evidence output already exists; preserve it and choose a new folder');
  }
  if (!exists(local)) fs.mkdirSync(local);
  assert(!fs.lstatSync(local).isSymbolicLink(), 'Evidence .local must be a plain directory');
  if (!requested) return fs.mkdtempSync(path.join(local,'ib-'));
  for (const parent of evidenceAncestors(output,own)) {
    if (exists(parent)) assert(!fs.lstatSync(parent).isSymbolicLink(), 'Linked evidence paths are forbidden');
  }
  fs.mkdirSync(output); // Parent must already exist; never create or reuse another run.
  return output;
}

function writeNew(file, data) {fs.writeFileSync(file,data,{flag:'wx',encoding:'utf8'});}
function writeJson(file, value) {writeNew(file,JSON.stringify(value,null,2)+'\n');}
function sourceHashes(source) {return Object.fromEntries(SOURCES.map(name => [name,exists(path.join(source,name)) ? hash(fs.readFileSync(path.join(source,name))) : null]));}
function treeHashes(root) {
  const result={};
  function visit(folder) {
    for (const name of fs.readdirSync(folder).sort()) {
      const file=path.join(folder,name), info=fs.lstatSync(file);
      assert(!info.isSymbolicLink(),'Linked generated evidence is forbidden');
      if (info.isDirectory()) visit(file);
      else if (info.isFile()) result[path.relative(root,file)]=hash(fs.readFileSync(file));
    }
  }
  visit(root); return result;
}

const DB_READ = `import json, pathlib, sqlite3, sys
p=pathlib.Path(sys.argv[1]).resolve()/"lab.sqlite3"
c=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True); c.row_factory=sqlite3.Row
c.execute("PRAGMA query_only=ON"); c.execute("BEGIN")
r=c.execute("SELECT request_id,intake_id,revision,readiness_fingerprint,run_id,runtime_instance_id,state,source_synthetic,result_json FROM intake_fixture_jobs").fetchone()
v={k:r[k] for k in r.keys() if k!="result_json"}
v.update(json.loads(r["result_json"]))
v["records"]=c.execute("SELECT count(*) FROM intake_fixture_jobs").fetchone()[0]
v["source_flag"]=c.execute("SELECT synthetic FROM intake_sources").fetchone()[0]
v["delegation_event"]=json.loads(c.execute("SELECT details_json FROM events WHERE action='intake.user_response' ORDER BY event_id LIMIT 1").fetchone()[0])
v["workflow_counts"]={n:c.execute("SELECT count(*) FROM "+n).fetchone()[0] for n in ("cases","plans","runs","evaluations")}
print(json.dumps(v,ensure_ascii=False,allow_nan=False)); c.close()`;

// Run this in every Python process that imports the selected project. Both the
// import spec and the imported objects must belong to the requested regular package.
const SOURCE_GUARD = `import importlib, importlib.util, json, sys
from pathlib import Path
_flow_root=Path(sys.argv.pop(1)).resolve(strict=True)
_flow_package_dir=_flow_root/"labflow"
_flow_init=_flow_package_dir/"__init__.py"
_flow_entry=_flow_package_dir/"intake_fixture_check.py"
if not _flow_init.is_file() or not _flow_entry.is_file():
    raise ValueError("source_regular_package_required")
if _flow_init.resolve()!=_flow_init or _flow_entry.resolve()!=_flow_entry or _flow_package_dir.resolve()!=_flow_package_dir:
    raise ValueError("source_path_outside_root")
def _flow_file(value,expected):
    if not isinstance(value,str) or Path(value).resolve(strict=True)!=expected:
        raise ValueError("source_module_path_mismatch")
def _flow_paths(value):
    if value is None or tuple(Path(item).resolve(strict=True) for item in value)!=(_flow_package_dir,):
        raise ValueError("source_package_path_mismatch")
sys.path.insert(0,str(_flow_root))
_flow_spec=importlib.util.find_spec("labflow")
if _flow_spec is None:
    raise ValueError("source_package_missing")
_flow_file(_flow_spec.origin,_flow_init)
_flow_paths(_flow_spec.submodule_search_locations)
_flow_package=importlib.import_module("labflow")
_flow_file(_flow_package.__file__,_flow_init)
_flow_paths(_flow_package.__path__)
_flow_spec=importlib.util.find_spec("labflow.intake_fixture_check")
if _flow_spec is None:
    raise ValueError("source_cli_missing")
_flow_file(_flow_spec.origin,_flow_entry)
_flow_cli=importlib.import_module("labflow.intake_fixture_check")
_flow_file(_flow_cli.__file__,_flow_entry)
_flow_file(_flow_cli.__spec__.origin,_flow_entry)
_flow_file(_flow_package.__file__,_flow_init)
_flow_paths(_flow_package.__path__)
if _flow_cli.__package__!="labflow":
    raise ValueError("source_cli_package_mismatch")
_flow_binding={"kind":"intake_fixture_import_binding","source_root":str(_flow_root),
    "package_file":str(Path(_flow_package.__file__).resolve()),
    "package_paths":[str(Path(item).resolve()) for item in _flow_package.__path__],
    "module_file":str(Path(_flow_cli.__file__).resolve())}`;

function sourceBootstrap() {
  return SOURCE_GUARD+'\nprint(json.dumps(_flow_binding,ensure_ascii=False),flush=True)\nraise SystemExit(_flow_cli.main())';
}

function validateSourceBinding(binding, source) {
  const root=fs.realpathSync(source), directory=path.join(root,'labflow');
  assert(binding && binding.kind === 'intake_fixture_import_binding','Actual import binding is required');
  assert(samePath(binding.source_root,root),'Actual source root mismatch');
  assert(samePath(binding.package_file,path.join(directory,'__init__.py')),'Actual package file mismatch');
  assert(Array.isArray(binding.package_paths) && binding.package_paths.length === 1 && samePath(binding.package_paths[0],directory),'Actual package search path mismatch');
  assert(samePath(binding.module_file,path.join(directory,'intake_fixture_check.py')),'Actual CLI module file mismatch');
}

const DEFER = SOURCE_GUARD+`\nimport pathlib, sqlite3
from labflow.store import Store
from labflow.intake_jobs import respond
p=pathlib.Path(sys.argv[1]).resolve(); c=sqlite3.connect((p/"lab.sqlite3").as_uri()+"?mode=ro",uri=True)
assert c.execute("SELECT count(*) FROM intake_sources WHERE synthetic!=1").fetchone()[0]==0
assert c.execute("SELECT count(*) FROM intakes").fetchone()[0]==1
assert c.execute("SELECT intake_id FROM intakes").fetchone()[0]==sys.argv[2]
c.close()
respond(Store(p),'FLOW-BROWSER-DEFER','defer',intake_id=sys.argv[2])`;

function pythonOnce(config, script, args) {
  const result=spawnSync(config.python,['-B','-X','utf8','-c',script,...args],{cwd:OWN,windowsHide:true,encoding:'utf8',timeout:30000,
    env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'}});
  assert(!result.error,result.error?.message); assert.equal(result.status,0,result.stderr || result.stdout);
  return result.stdout;
}

function validateBinding(summary, response, database, kind) {
  assert.equal(summary.schema_version,1); assert.equal(summary.kind,'intake_fixture_flow_check');
  assert.equal(summary.document_kind,kind); assert.equal(summary.records,1); assert.equal(database.records,1);
  for (const value of [summary,...response.records]) {
    assert.equal(value.synthetic,true); assert.equal(value.hardware_verified,false); assert.equal(value.ai_model_called,false); assert.equal(value.resumable,false);
    assert.equal(value.source_synthetic,true); assert.equal(value.source_current,true);
  }
  assert.equal(summary.historical,false); assert.equal(summary.intake_ready,true); assert.equal(summary.fixture_acceptance,'pass');
  assert.equal(summary.fixture_measurement_observed,true); assert.equal(summary.execution_state,'completed');
  assert.equal(summary.task_outcome,'not_assessed'); assert.equal(summary.cleanup_status,'not_assessed');
  assert.equal(response.schema_version,1); assert.equal(response.storage_available,true); assert.equal(response.more_available,false);
  assert.equal(response.records.length,1); assert.equal(response.intake_id,summary.intake_id);
  assert.equal(response.current_revision,summary.revision); assert.equal(summary.current_revision,summary.revision);
  const record=response.records[0];
  assert.equal(record.recipe_id,'conducted_sensor_fixture_v1');
  for (const key of ['intake_id','revision','request_id','run_id']) {
    assert.equal(record[key],summary[key],key); assert.equal(database[key],summary[key],key);
  }
  assert.equal(record.runtime_instance_id,database.runtime_instance_id); assert.equal(record.readiness_fingerprint,database.readiness_fingerprint);
  assert.equal(record.case_id,null); assert.equal(record.plan_id,null); assert.equal(record.state,'completed'); assert.equal(database.state,'completed');
  assert.equal(database.source_synthetic,1); assert.equal(database.source_flag,1);
  assert.deepEqual(database.delegation_event,{event_id:'FLOW-DELEGATION',action:'proceed'});
  assert.deepEqual(database.workflow_counts,{cases:0,plans:0,runs:0,evaluations:0});
  const report=record.report;
  assert.deepEqual(report,database.report); assert.equal(report.run_id,record.run_id); assert.equal(report.runtime_instance_id,record.runtime_instance_id);
  assert.equal(report.synthetic,true); assert.equal(report.hardware_verified,false); assert.equal(report.ai_model_called,false);
  assert.equal(report.policy.kind,'fixture'); assert.deepEqual(report.termination,{reason:'policy_stop',policy_claim:'completed'});
  assert.equal(report.assessment.status,'completed'); assert.equal(report.assessment.verdict,'pass');
  assert.equal(report.task_outcome,'not_assessed'); assert.equal(report.cleanup.status,'not_assessed');
  assert(report.evidence.measurement_refs.length>0); assert.deepEqual(report.unresolved_request_ids,[]); assert.equal(report.usage.reserved_ticks,0);
  return record;
}

function retainedBlob(workspace, identity) {
  assert(typeof identity === 'string' && /^[a-f0-9]{64}$/.test(identity),'Expected retained SHA-256 identity');
  const payload=fs.readFileSync(path.join(workspace,'blobs',identity)); assert.equal(hash(payload),identity);
  return JSON.parse(payload.toString('utf8'));
}
function verifyCitations(intake, output, kind) {
  const submitted=intake.analysis.submitted, workspace=path.join(output,'state');
  const name=kind === 'pdf' ? 'request.pdf':'request.txt';
  const original=fs.readFileSync(path.join(output,'inbox','fixture-request',name)), originalHash=hash(original);
  assert.equal(intake.files.length,1); assert.equal(intake.files[0].path,name); assert.equal(intake.files[0].sha256,originalHash);
  assert.equal(submitted.schema_version,kind === 'pdf' ? 2:1);
  if (kind === 'pdf') {
    const context=retainedBlob(workspace,submitted.context_id);
    assert.equal(context.binding.intake_id,intake.intake_id); assert.equal(context.binding.revision,intake.revision);
  }
  const locators=[];
  for (const field of ['market','purpose']) {
    const fact=submitted.facts.find(value=>value.field===field); assert(fact && fact.evidence.length,'Expected request evidence');
    for (const citation of fact.evidence) {
      assert.equal(citation.path,name); assert.equal(citation.sha256,originalHash); assert.equal(citation.role,'request');
      let text=original.toString('utf8');
      if (kind === 'pdf') {
        assert.equal(citation.kind,'pdf_page'); assert.equal(citation.page_number,2);
        const extraction=retainedBlob(workspace,citation.extraction_id);
        assert.equal(extraction.result.source.sha256,originalHash); assert.equal(extraction.result.total_pages,2);
        const page=extraction.result.pages.find(value=>value.page_number===2); assert(page);
        assert.equal(hash(Buffer.from(page.text,'utf8')),citation.text_sha256); assert.equal(page.text_sha256,citation.text_sha256);
        text=page.text;
      }
      assert(Number.isSafeInteger(citation.line_start) && citation.line_start>=1 && citation.line_end>=citation.line_start);
      assert.equal(text.split(/\r?\n/).slice(citation.line_start-1,citation.line_end).join('\n'),citation.quote);
      locators.push(citation);
    }
  }
  return locators;
}

function startCLI(config, output, kind) {
  const child=spawn(config.python,['-B','-X','utf8','-c',sourceBootstrap(),config.source,'--output',output,'--power-dbm',String(config.power),'--document-kind',kind,'--port','0'],
    {cwd:OWN,windowsHide:true,stdio:['ignore','pipe','pipe'],env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'}});
  const logs={stdout:'',stderr:''}; child.stdout.on('data',chunk=>{logs.stdout+=chunk;}); child.stderr.on('data',chunk=>{logs.stderr+=chunk;});
  const closed=new Promise(resolve=>child.once('close',resolve));
  return {child,logs,closed,ready:new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Actual CLI startup timed out; preserved server log')),45000);
    child.once('error',error=>{clearTimeout(timer);reject(error);});
    child.once('exit',code=>{clearTimeout(timer);reject(new Error('Actual CLI exited before serving: '+code));});
    child.stdout.on('data',()=>{
      const match=logs.stdout.match(/^DGM synthetic intake fixture: (http:\/\/127\.0\.0\.1:(\d+))\/#([A-Za-z0-9_.-]+)\r?$/m);
      if (match) {
        clearTimeout(timer);
        if (!(Number(match[2])>0 && Number(match[2])<=65535)) return reject(new Error('Invalid actual server port'));
        resolve({origin:match[1],intake_id:match[3]});
      }
    });
  })};
}
async function stopChild(session) {
  const {child,closed}=session;
  const live=()=>child.pid && child.exitCode === null && child.signalCode === null;
  const wait=async()=>{
    let timer;
    try {await Promise.race([closed,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Owned CLI child did not stop')),5000);})]);}
    finally {clearTimeout(timer);}
  };
  if (live()) child.kill();
  try {await wait();} catch {if (live()) child.kill('SIGKILL');await wait();}
}
async function screenshot(page, file) {
  assert(!exists(file),'Preserve existing screenshot');
  await page.evaluate(()=>window.scrollTo({top:0,left:0,behavior:'instant'}));
  await page.screenshot({path:file,fullPage:true});
}

async function runKind(config, evidence, kind, checks) {
  const output=path.join(evidence,kind === 'text' ? 't':'p'); assert(!exists(output));
  const session=startCLI(config,output,kind); let browser, page;
  try {
    const {origin,intake_id}=await session.ready;
    const summary=JSON.parse(fs.readFileSync(path.join(output,'public-summary.json'),'utf8'));
    assert.equal(intake_id,summary.intake_id);
    const stdoutRecords=session.logs.stdout.split(/\r?\n/).filter(line=>line.startsWith('{')).map(JSON.parse);
    const sourceBinding=stdoutRecords.find(value=>value.kind === 'intake_fixture_import_binding');
    validateSourceBinding(sourceBinding,config.source);
    assert.deepEqual(stdoutRecords.find(value=>value.kind === 'intake_fixture_flow_check'),summary);
    const database=JSON.parse(pythonOnce(config,DB_READ,[path.join(output,'state')]));
    const {chromium}=require('playwright'); browser=await chromium.launch({headless:true});
    const context=await browser.newContext({viewport:{width:1512,height:1100}}); context.setDefaultTimeout(10000);
    const errors=[],external=[],methods=[];
    context.on('page',item=>{
      item.on('pageerror',error=>errors.push(error.message));
      item.on('websocket',socket=>external.push(socket.url()));
    });
    context.on('request',request=>{if (!request.url().startsWith(origin+'/')) external.push(request.url());if(request.url().includes('/api/')) methods.push(request.method());});
    page=await context.newPage();
    const get=async route=>{const response=await context.request.get(origin+route);assert.equal(response.status(),200);assert.equal(response.headers()['cache-control'],'no-store');return response.json();};
    const flowRoute=`/api/intakes/${encodeURIComponent(intake_id)}/fixture-runs`;
    const loaded=async()=>page.locator('#fixture-status').filter({hasText:'가상 기록 조회 완료'}).waitFor();
    const before=treeHashes(output);
    await page.goto(origin+'/#'+encodeURIComponent(intake_id)); await loaded();
    const response=await get(flowRoute), record=validateBinding(summary,response,database,kind);
    const detail=await get(`/api/intakes/${encodeURIComponent(intake_id)}`), intake=detail.intake;
    assert.equal(intake.intake_id,intake_id);assert.equal(intake.revision,summary.revision);assert.equal(intake.synthetic,true);assert.equal(intake.delegated,true);
    assert.equal(intake.analysis.facts.model.value,'SM-A176U');assert.equal(intake.analysis.submitted.producer.kind,'fixture');
    const locators=verifyCitations(intake,output,kind);
    for (const artifact of database.artifacts) {
      assert.equal(artifact.artifact_id,'blob:'+artifact.sha256);
      const bytes=fs.readFileSync(path.join(output,'state','blobs',artifact.sha256));
      assert.equal(hash(bytes),artifact.sha256);assert.equal(bytes.length,artifact.bytes);
      if (artifact.kind === 'result') assert.deepEqual(JSON.parse(bytes.toString('utf8')),record.report);
    }
    checks.push(`${kind}: actual CLI, fixture delegation, one intake/request/run/report, exact revision/instance and retained artifact hashes`);
    assert.equal(await page.locator('.intake-item').count(),1);assert.equal(await page.locator('.fixture-request').count(),1);
    assert.equal(await page.locator('.fixture-request[aria-pressed=true]').getAttribute('data-request-id'),summary.request_id);
    const resultText=await page.locator('#fixture-result').innerText();
    for (const value of [summary.intake_id,summary.run_id]) assert((await page.locator('#detail-panel').innerText()).includes(value));
    assert(resultText.includes(summary.request_id) && resultText.includes(record.runtime_instance_id));
    for (const label of ['가상 시나리오 평가 통과','정책의 완료 주장','작업 결과 미평가','정리 상태 미평가']) assert(resultText.includes(label));
    for (const label of ['실제 AI 호출 없음','실장비 검증 없음','runtime 재개 지원 없음']) assert((await page.locator('#fixture-panel').innerText()).includes(label));
    assert.equal(await page.locator('#fixture-panel input, #fixture-panel select, #fixture-panel textarea, #fixture-panel a').count(),0);
    assert.equal(await page.locator('#fixture-panel button').count(),2);
    assert.deepEqual(await page.locator('#fixture-panel button').evaluateAll(nodes=>nodes.map(node=>node.id || node.dataset.requestId)),['fixture-refresh',summary.request_id]);
    for (const [field,label] of [['market','의뢰 시장'],['purpose','의뢰 목적']]) {
      const card=page.locator('.fact').filter({has:page.getByText(label,{exact:true})});
      assert.equal(await card.count(),1);await card.locator('summary').first().click();
      for (const source of intake.analysis.submitted.facts.find(fact=>fact.field===field).evidence) {
        await card.getByText('SHA-256 '+source.sha256,{exact:true}).waitFor();
        await card.getByText(source.quote,{exact:true}).waitFor();
        if (kind === 'pdf') {
          await card.getByText(`PDF 2쪽 · 페이지 안 ${source.line_start}–${source.line_end}행`,{exact:false}).waitFor();
          await card.getByText('페이지 텍스트 SHA-256 '+source.text_sha256,{exact:true}).waitFor();
          await card.getByText('추출 ID '+source.extraction_id,{exact:true}).waitFor();
        }
      }
    }
    if (kind === 'pdf') await page.getByText('분석 문맥 ID '+intake.analysis.submitted.context_id,{exact:true}).waitFor();
    checks.push(`${kind}: actual source citations, independent virtual assessment/not_assessed/provenance and read-only controls`);
    await screenshot(page,path.join(evidence,`${kind}-desktop.png`));
    for (let index=0;index<2;index++) {await get('/api/intakes');await get(flowRoute);}
    assert.deepEqual(treeHashes(output),before,'GET/browser reads changed generated evidence');
    checks.push(`${kind}: browser and repeated GET leave all generated file bytes unchanged`);
    pythonOnce(config,DEFER,[config.source,path.join(output,'state'),intake_id]);
    const changed=await get(flowRoute);
    assert.equal(changed.current_revision,response.current_revision);assert.equal(changed.records.length,1);
    const historical=changed.records[0];assert.equal(historical.source_current,false);
    for (const key of ['intake_id','revision','request_id','run_id','runtime_instance_id','readiness_fingerprint']) assert.equal(historical[key],record[key]);
    assert.deepEqual(historical.report,record.report);
    const refreshResponse=page.waitForResponse(item=>item.url()===origin+'/api/intakes');
    await page.locator('#refresh').click();await refreshResponse;
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await loaded();
    assert.match(await page.locator('#fixture-result').innerText(),/준비 상태 변경 기록/);
    assert.equal(await page.locator('.fixture-request[aria-pressed=true]').getAttribute('data-request-id'),summary.request_id);
    assert.match(await page.locator('#fixture-result').innerText(),/가상 시나리오 평가 통과/);
    const afterDefer=treeHashes(output);await get(flowRoute);assert.deepEqual(treeHashes(output),afterDefer);
    checks.push(`${kind}: explicit same-revision synthetic defer changes current context and preserves the historical report and selection`);
    await page.setViewportSize({width:390,height:844});await page.locator('#fixture-panel').scrollIntoViewIfNeeded();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await screenshot(page,path.join(evidence,`${kind}-mobile.png`));
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert(methods.length && methods.every(method=>method==='GET'));
    checks.push(`${kind}: 390px overflow 0, JavaScript errors 0, external requests 0 and browser API writes 0`);
    writeJson(path.join(evidence,`${kind}-binding.json`),{source_binding:sourceBinding,summary,record,after_defer:historical,citations:locators,pageErrors:errors,externalRequests:external,apiMethods:[...new Set(methods)]});
  } finally {
    try {if(browser) await browser.close();}
    finally {try {await stopChild(session);}finally{writeJson(path.join(evidence,`${kind}-server-log.json`),{
      ...session.logs,child_pid:session.child.pid,exit_code:session.child.exitCode,signal:session.child.signalCode,termination_requested:session.child.killed});}}
  }
}
async function main(env = process.env) {
  const config=readConfig(env);
  assert(fs.statSync(path.join(config.source,'labflow/intake_fixture_check.py')).isFile(),'Actual intake_fixture_check module is required');
  assert(fs.statSync(path.join(config.source,'labflow/__init__.py')).isFile(),'Actual regular labflow package is required');
  const evidence=reserveEvidence(OWN,config.requested), hashes=sourceHashes(config.source), checks=[];
  console.log('Actual fixture acceptance evidence: '+evidence);
  const result={synthetic:true,hardware_verified:false,ai_model_called:false,resumable:false,tool_sha256:hash(fs.readFileSync(__filename)),source_root:config.source,source_sha256:hashes,kinds:config.kinds,checks,passed:false};
  try {
    for (const kind of config.kinds) {await runKind(config,evidence,kind,checks);console.log('PASS actual '+kind+' acceptance');}
    assert.deepEqual(sourceHashes(config.source),hashes,'Source changed during actual acceptance; preserve this attempt and rerun');
    result.passed=true;
  } catch(error) {result.error=error.message;throw error;}
  finally {writeJson(path.join(evidence,'result.json'),result);}
  console.log(JSON.stringify({passed:checks.length,kinds:config.kinds,evidence}));
  return result;
}

async function selfTest(env = process.env) {
  const config=readConfig({FLOW_PYTHON:env.FLOW_PYTHON}), evidence=reserveEvidence(OWN), checks=[];
  const result={kind:'intake_fixture_browser_self_test',synthetic:true,hardware_verified:false,ai_model_called:false,
    actual_flow_executed:false,checks,passed:false};
  const check=(name,action,skip=false)=>{if(skip) checks.push({name,status:'skipped'});else{action();checks.push({name,status:'pass'});}};
  const fixture=(name,initializer,entry)=>{
    const root=path.join(evidence,name);fs.mkdirSync(root);fs.mkdirSync(path.join(root,'labflow'));
    if(initializer !== null) writeNew(path.join(root,'labflow/__init__.py'),initializer);
    if(entry !== null) writeNew(path.join(root,'labflow/intake_fixture_check.py'),entry);
    return root;
  };
  const cli="def main():\n    print('SELF_TEST_MAIN')\n    return 0\nif __name__=='__main__':\n    main()\n";
  const complete=fixture('complete','',cli), marker="raise RuntimeError('OVERRIDE_MUST_NOT_FALLBACK')\n";
  const launch=(source,cache=false)=>{
    const prefix='import sys; sys.path.insert(0,'+JSON.stringify(complete)+'); '+(cache?'import labflow; ':'');
    const run=spawnSync(config.python,['-B','-X','utf8','-c',prefix+sourceBootstrap(),source,'--help'],{
      cwd:OWN,windowsHide:true,encoding:'utf8',timeout:15000,
      env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'}});
    assert(!run.error,run.error?.message);return run;
  };
  try {
    check('Windows alternate-case output terminates',()=>{
      const parent=path.join(evidence,'case');fs.mkdirSync(parent);const output=path.join(parent,'e').toUpperCase();
      const script="require(process.argv[1]).reserveEvidence(process.argv[2],process.argv[3])";
      const run=spawnSync(process.execPath,['-e',script,__filename,OWN,output],{cwd:OWN,windowsHide:true,encoding:'utf8',timeout:3000});
      assert(!run.error,run.error?.message);assert.equal(run.status,0,run.stderr);assert(fs.statSync(output).isDirectory());
      assert.deepEqual(fs.readdirSync(parent).map(name=>name.toLowerCase()),['e']);
    },process.platform !== 'win32');
    check('ancestor traversal stops at a root',()=>{
      assert.throws(()=>evidenceAncestors(path.resolve(OWN,'..','outside-root','new'),OWN),/checkout root/);
    });
    for(const [name,root,cache] of [
      ['missing package initializer',fixture('missing-init',null,marker),false],
      ['namespace root',fixture('namespace',null,null),false],
      ['redirected package search path',fixture('redirected','__path__=['+JSON.stringify(path.join(complete,'labflow'))+']\n',marker),false],
      ['cached foreign package',fixture('cached','',marker),true],
      ['actual imported module file mismatch',fixture('wrong-file','',"__file__="+JSON.stringify(path.join(complete,'labflow/intake_fixture_check.py'))+'\n'+cli),false],
    ]) check(name,()=>{
      const run=launch(root,cache);assert.notEqual(run.status,0,run.stdout);assert(!run.stdout.includes('SELF_TEST_MAIN'));
    });
    check('complete package supplies verified import paths',()=>{
      const run=launch(complete);assert.equal(run.status,0,run.stderr);assert(run.stdout.includes('SELF_TEST_MAIN'));
      const binding=run.stdout.split(/\r?\n/).filter(line=>line.startsWith('{')).map(JSON.parse).find(value=>value.kind === 'intake_fixture_import_binding');
      validateSourceBinding(binding,complete);
    });
    result.passed=true;
  } catch(error) {result.error=error.message;throw error;}
  finally {writeJson(path.join(evidence,'self-test.json'),result);}
  const response={kind:result.kind,passed:checks.filter(item=>item.status === 'pass').length,skipped:checks.filter(item=>item.status === 'skipped').length,evidence};
  console.log(JSON.stringify(response));return result;
}

module.exports={readConfig,reserveEvidence,evidenceAncestors,sourceBootstrap,validateSourceBinding,validateBinding,main,selfTest};
if (require.main===module) (process.argv[2] === '--self-test' ? selfTest() : main()).catch(error=>{console.error(error);process.exitCode=1;});
