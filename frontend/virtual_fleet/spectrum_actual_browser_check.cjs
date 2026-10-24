/* Actual pinned Python math -> same-origin GET -> component DOM. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto'),{pathToFileURL}=require('node:url');
const {reserveEvidence,evidenceAncestors}=require('../intake_fixture_browser_check.cjs');
const ROOT=fs.realpathSync(path.resolve(__dirname,'../..'));
const CASES=['normal','bandwidth-below','incomplete','axis-unrepresentable','density-rounded-eight'];
const MAX_BYTES=1024*1024;
const samePath=(a,b)=>path.relative(path.resolve(a),path.resolve(b))==='';
const digest=data=>createHash('sha256').update(data).digest('hex');
class ToolFailure extends Error {constructor(code){super(code);this.code=code;}}
const reject=code=>{throw new ToolFailure(code);};
const write=(file,data)=>fs.writeFileSync(file,data,{flag:'wx'});
const writeJson=(file,value)=>write(file,JSON.stringify(value,null,2)+'\n');

function readConfig(env=process.env,args=[]) {
  if(Object.keys(env).some(key=>key.startsWith('SPECTRUM_') && key!=='SPECTRUM_PYTHON')
    || args.some(arg=>arg!=='--self-test') || args.length>1) reject('invalid_configuration');
  const python=env.SPECTRUM_PYTHON ?? path.join(ROOT,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
  if(typeof python!=='string' || !python.trim() || /[\r\n\0]/.test(python)) reject('invalid_configuration');
  return {python}; // No source or output override: actual source is always ROOT.
}

const GUARD=`import importlib, importlib.util, hashlib, json, sys
from pathlib import Path
_root=Path(sys.argv.pop(1)).resolve(strict=True)
_packages={"labflow":_root/"labflow", "labflow.virtual_fleet":_root/"labflow/virtual_fleet"}
_entry=_root/"labflow/virtual_fleet/spectrum_math.py"
if any(not (p/"__init__.py").is_file() for p in _packages.values()) or not _entry.is_file():
    raise ValueError("spectrum_regular_source_required")
if any(p.resolve()!=p or (p/"__init__.py").resolve()!=p/"__init__.py" for p in _packages.values()) or _entry.resolve()!=_entry:
    raise ValueError("spectrum_source_path_mismatch")
def _file(value,expected):
    if not isinstance(value,str) or Path(value).resolve(strict=True)!=expected:
        raise ValueError("spectrum_module_path_mismatch")
def _paths(value,expected):
    if value is None or tuple(Path(item).resolve(strict=True) for item in value)!=(expected,):
        raise ValueError("spectrum_package_path_mismatch")
sys.path.insert(0,str(_root))
_loaded={}
for _name,_directory in _packages.items():
    _spec=importlib.util.find_spec(_name)
    if _spec is None: raise ValueError("spectrum_package_missing")
    _file(_spec.origin,_directory/"__init__.py"); _paths(_spec.submodule_search_locations,_directory)
    _module=importlib.import_module(_name)
    _file(_module.__file__,_directory/"__init__.py"); _paths(_module.__path__,_directory)
    _file(_module.__spec__.origin,_directory/"__init__.py"); _paths(_module.__spec__.submodule_search_locations,_directory)
    _loaded[_name]=_module
_spec=importlib.util.find_spec("labflow.virtual_fleet.spectrum_math")
if _spec is None: raise ValueError("spectrum_math_missing")
_file(_spec.origin,_entry)
_math=importlib.import_module("labflow.virtual_fleet.spectrum_math")
_file(_math.__file__,_entry); _file(_math.__spec__.origin,_entry)
if _math.__package__!="labflow.virtual_fleet": raise ValueError("spectrum_math_package_mismatch")
for _name,_directory in _packages.items():
    _file(_loaded[_name].__file__,_directory/"__init__.py"); _paths(_loaded[_name].__path__,_directory)
    _file(_loaded[_name].__spec__.origin,_directory/"__init__.py"); _paths(_loaded[_name].__spec__.submodule_search_locations,_directory)
_imported={}
for _name,_module in tuple(sys.modules.items()):
    if _name=="labflow" or _name.startswith("labflow."):
        _source=Path(_module.__file__).resolve(strict=True)
        if not _source.is_relative_to(_root): raise ValueError("spectrum_foreign_import")
        _imported[_name]={"file":str(_source),"sha256":hashlib.sha256(_source.read_bytes()).hexdigest()}
_binding={"kind":"spectrum_math_import_binding","source_root":str(_root),
    "packages":{name:{"file":str(Path(module.__file__).resolve()),"paths":[str(Path(p).resolve()) for p in module.__path__]} for name,module in _loaded.items()},
    "module_file":str(Path(_math.__file__).resolve()),"module_sha256":hashlib.sha256(_entry.read_bytes()).hexdigest(),"imported_sources":_imported}`;

const PRODUCER=GUARD+`
import copy
def trace(name,offsets,levels):
    return {"schema_version":1,"kind":"synthetic_frequency_spectrum","capture_id":"actual:"+name+":bw","synthetic":True,
        "axis_domain":"frequency_offset_hz","sample_unit":"dB","amplitude_basis":"relative_to_peak",
        "selection_policy":"unique_peak_single_lobe_linear_db","frequency_offsets_hz":offsets,"relative_levels_db":levels}
def sample(name,density=False):
    value={"schema_version":1,"kind":"synthetic_psd_input","capture_id":"actual:"+name+":psd","synthetic":True,
        "reference_plane":"dut_output","time_basis":"on_interval","output_power_method":"on_mean","psd_power_method":"on_mean",
        "path_correction_state":"already_applied","input_basis":"flat_density_mw_per_hz" if density else "band_power_3khz"}
    value["density_mw_per_hz" if density else "power_dbm"]=.002103191148267311 if density else 0
    return value
_cases=[]
for name,offsets,levels,density in [
    ("normal",[-400000,-250000,0,250000,400000],[-12,-6,0,-6,-12],False),
    ("bandwidth-below",[-400000,-249999.99999999997,0,249999.99999999997,400000],[-12,-6,0,-6,-12],False),
    ("incomplete",[0,100000,200000],[0,-3,-6],False),
    ("axis-unrepresentable",[-1e308,-1,0,1,1e308],[-100,-12,0,-12,-100],False),
    ("density-rounded-eight",[-400000,-250000,0,250000,400000],[-12,-6,0,-6,-12],True),
]:
    source_trace=trace(name,offsets,levels); source_sample=sample(name,density)
    before_trace=copy.deepcopy(source_trace); before_sample=copy.deepcopy(source_sample)
    value={"schema_version":1,"kind":"synthetic_spectrum_view","trace":source_trace,
        "bandwidth":_math.analyze_6db_bandwidth(source_trace),"psd":_math.analyze_psd_band(source_sample)}
    if source_trace!=before_trace or source_sample!=before_sample: raise ValueError("spectrum_inputs_mutated")
    _cases.append({"name":name,"trace_input":before_trace,"psd_input":before_sample,"value":value})
print(json.dumps({"schema_version":1,"kind":"synthetic_spectrum_python_producer","source_binding":_binding,"cases":_cases},ensure_ascii=False,allow_nan=False))`;

function parseProducer(bytes) {
  try {
    if(!Buffer.isBuffer(bytes) || bytes.length>MAX_BYTES || bytes.length===0) reject('invalid_producer');
    const payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    const finite=(value,depth=0)=>{
      if(depth>32) reject('invalid_producer');
      if(value===null || typeof value==='string' || typeof value==='boolean') return;
      if(typeof value==='number') {if(!Number.isFinite(value)) reject('invalid_producer');return;}
      if(Array.isArray(value)) {for(const child of value) finite(child,depth+1);return;}
      if(typeof value==='object') {for(const child of Object.values(value)) finite(child,depth+1);return;}
      reject('invalid_producer');
    };
    finite(payload);
    assert(payload && Object.keys(payload).sort().join(' ')==='cases kind schema_version source_binding');
    assert.equal(payload.schema_version,1);assert.equal(payload.kind,'synthetic_spectrum_python_producer');
    assert.deepEqual(payload.cases.map(item=>item.name),CASES);
    for(const item of payload.cases) assert.equal(Object.keys(item).sort().join(' '),'name psd_input trace_input value');
    return payload;
  }catch{reject('invalid_producer');}
}

function sourceHashes() {
  const files=['frontend/virtual_fleet/spectrum_actual_browser_check.cjs','frontend/virtual_fleet/spectrum_model.mjs',
    'frontend/virtual_fleet/spectrum_view.mjs','frontend/virtual_fleet/spectrum_browser_check.cjs','frontend/virtual_fleet/spectrum_model.test.mjs',
    'frontend/intake_fixture_browser_check.cjs'];
  const visit=directory=>{for(const entry of fs.readdirSync(directory,{withFileTypes:true})) {
    const file=path.join(directory,entry.name);if(entry.isSymbolicLink()) reject('linked_source');
    if(entry.isDirectory() && entry.name!=='__pycache__') visit(file);
    else if(entry.isFile() && entry.name.endsWith('.py')) files.push(path.relative(ROOT,file));
  }};
  visit(path.join(ROOT,'labflow'));
  return Object.fromEntries(files.sort().map(name=>[name.split(path.sep).join('/'),digest(fs.readFileSync(path.join(ROOT,name)))]));
}
function validateSourceBinding(binding,source=ROOT) {
  const root=fs.realpathSync(source);
  assert.equal(binding.kind,'spectrum_math_import_binding');assert(samePath(binding.source_root,root));
  for(const [name,relative] of [['labflow','labflow'],['labflow.virtual_fleet','labflow/virtual_fleet']]) {
    const pkg=binding.packages[name],directory=path.join(root,relative);
    assert(samePath(pkg.file,path.join(directory,'__init__.py')));assert.equal(pkg.paths.length,1);assert(samePath(pkg.paths[0],directory));
  }
  const module=path.join(root,'labflow/virtual_fleet/spectrum_math.py');assert(samePath(binding.module_file,module));
  assert.equal(binding.module_sha256,digest(fs.readFileSync(module)));
  for(const data of Object.values(binding.imported_sources)) {
    const relative=path.relative(root,data.file);assert(relative && !relative.startsWith('..') && !path.isAbsolute(relative));
    assert.equal(data.sha256,digest(fs.readFileSync(data.file)));
  }
}
function dependencies() {
  for(const file of ['labflow/__init__.py','labflow/virtual_fleet/__init__.py','labflow/virtual_fleet/spectrum_math.py']) {
    try{if(!fs.statSync(path.join(ROOT,file)).isFile()) reject('spectrum_math_dependency_missing');}catch{reject('spectrum_math_dependency_missing');}
  }
}
function executePython(config,script,root=ROOT,prefix='') {
  return spawnSync(config.python,['-B','-X','utf8','-c',prefix+script,root],{cwd:ROOT,windowsHide:true,timeout:30000,maxBuffer:MAX_BYTES,killSignal:'SIGKILL',
    env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'},encoding:null});
}

async function main(env=process.env) {
  const config=readConfig(env,[]);dependencies();
  const evidence=reserveEvidence(ROOT),checks=[],cleanup={producer_closed:false,browser_closed:false,server_closed:false};
  const result={schema_version:1,kind:'synthetic_spectrum_actual_browser',contract_fixture:false,python_math_connected:true,
    synthetic:true,hardware_verified:false,ai_model_called:false,actual_flow_executed:false,checks,cleanup,passed:false,stage:'producer'};
  let browser,server,page,failure,raw,sourceBefore;
  const errors=[],external=[],reads=[];
  try {
    sourceBefore=sourceHashes();result.source_sha256=sourceBefore;
    const run=executePython(config,PRODUCER);
    write(path.join(evidence,'producer-stdout.raw'),run.stdout || Buffer.alloc(0));write(path.join(evidence,'producer-stderr.raw'),run.stderr || Buffer.alloc(0));
    writeJson(path.join(evidence,'producer-process.json'),{pid:run.pid,status:run.status,signal:run.signal,
      error:run.error?{name:run.error.name,code:run.error.code,message:run.error.message}:null});
    cleanup.producer_closed=true;cleanup.producer_pid=run.pid;cleanup.producer_exit_code=run.status;cleanup.producer_signal=run.signal;
    if(run.error || run.status!==0 || run.signal) reject('python_producer_failed');
    raw=run.stdout;const producer=parseProducer(raw);validateSourceBinding(producer.source_binding);result.source_binding=producer.source_binding;
    write(path.join(evidence,'producer.json'),raw);const producerHash=digest(raw);result.producer_sha256=producerHash;
    const model=await import(pathToFileURL(path.join(ROOT,'frontend/virtual_fleet/spectrum_model.mjs')).href);
    const view=await import(pathToFileURL(path.join(ROOT,'frontend/virtual_fleet/spectrum_view.mjs')).href);
    for(const item of producer.cases) {model.validateSpectrumView(item.value);assert.deepEqual(item.value.trace,item.trace_input);}
    const values=Object.fromEntries(producer.cases.map(item=>[item.name,item.value]));
    const normal=values.normal;
    assert.equal(normal.bandwidth.bandwidth_hz,500000);assert.equal(normal.psd.power_dbm,0);assert.equal(normal.psd.power_mw,1);
    assert.equal(values['bandwidth-below'].bandwidth.bandwidth_hz,499999.99999999994);assert.equal(values['bandwidth-below'].bandwidth.conditional_comparison,'below');
    assert.equal(values.incomplete.bandwidth.status,'incomplete');assert.equal(values.incomplete.bandwidth.bandwidth_hz,null);
    assert.equal(values['axis-unrepresentable'].bandwidth.bandwidth_hz,1);
    assert.equal(values['density-rounded-eight'].psd.power_dbm,8);assert.equal(values['density-rounded-eight'].psd.conditional_comparison,'above');
    assert.equal(values['density-rounded-eight'].psd.margin_db,-5.6220036403531095e-16);
    const invalid=structuredClone(normal);invalid.psd.capture_id='other:<img src=x onerror="window.spectrumInjected=true">';
    const wrong=structuredClone(normal);wrong.bandwidth.capture_id='other';
    const badSchema=structuredClone(normal);badSchema.schema_version=2;
    const badFlags=structuredClone(normal);badFlags.psd.hardware_verified=true;
    const negatives={'invalid-xss':invalid,'invalid-binding':wrong,'invalid-schema':badSchema,'invalid-flags':badFlags};
    const html='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>실제 합성 스펙트럼 계산 수용 검사</title><link rel="stylesheet" href="/view.css"></head><body><main id="mount"></main><script type="module" src="/harness.mjs"></script></body></html>';
    const harness="import {renderSpectrumView} from '/spectrum_view.mjs';window.loadSpectrum=async name=>{const response=await fetch('/data/'+encodeURIComponent(name)+'.json',{cache:'no-store'});if(!response.ok)throw new Error('spectrum_response_failed');const value=await response.json();renderSpectrumView(document.getElementById('mount'),value);window.lastSpectrum=structuredClone(value);return value;};window.spectrumReady=true;";
    result.harness_sha256=digest(harness);result.stylesheet_sha256=digest(view.SPECTRUM_VIEW_CSS);
    const assets={'/':['text/html; charset=utf-8',html],'/harness.mjs':['text/javascript; charset=utf-8',harness],
      '/view.css':['text/css; charset=utf-8','body{margin:0;padding:20px;background:#080f1b;color:#e8eff8}#mount{max-width:1100px;margin:auto;min-width:0}'+view.SPECTRUM_VIEW_CSS],
      '/spectrum_model.mjs':['text/javascript; charset=utf-8',fs.readFileSync(path.join(ROOT,'frontend/virtual_fleet/spectrum_model.mjs'))],
      '/spectrum_view.mjs':['text/javascript; charset=utf-8',fs.readFileSync(path.join(ROOT,'frontend/virtual_fleet/spectrum_view.mjs'))]};
    result.stage='browser';
    server=http.createServer((request,response)=>{
      let asset=request.method==='GET' && Object.hasOwn(assets,request.url)?assets[request.url]:null;
      const match=/^\/data\/([A-Za-z0-9-]+)\.json$/.exec(request.url);
      if(request.method==='GET' && match) {
        const key=match[1],data=Object.hasOwn(negatives,key)?negatives[key]:Object.hasOwn(values,key)?values[key]:null;
        if(data) asset=['application/json; charset=utf-8',JSON.stringify(data)];
      }
      reads.push({method:request.method,path:request.url,status:asset?200:404});
      response.writeHead(asset?200:404,{'Content-Type':asset?asset[0]:'text/plain','Cache-Control':'no-store',
        'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"});
      response.end(asset?asset[1]:'not found');
    });
    await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
    const origin='http://127.0.0.1:'+server.address().port;result.origin=origin;
    const {chromium}=require('playwright');browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:1440,height:1000}});
    context.setDefaultTimeout(5000);context.on('page',item=>item.on('pageerror',error=>errors.push(error.message)));
    context.on('request',request=>{if(!request.url().startsWith(origin+'/'))external.push(request.url());});
    page=await context.newPage();await page.goto(origin);await page.waitForFunction(()=>window.spectrumReady);
    const load=name=>page.evaluate(name=>window.loadSpectrum(name),name);
    const check=async(name,action)=>{await action();checks.push(name);console.log('PASS '+name);};
    for(const name of CASES) await check('actual Python -> GET -> DOM: '+name,async()=>{
      const received=await load(name);assert.deepEqual(received,values[name]);
      const text=await page.locator('#mount').innerText();
      for(const item of [received.trace.capture_id,received.psd.capture_id,received.bandwidth.input_sha256,received.psd.input_sha256,
        '합성','실장비 미검증','실제 AI 호출 없음','방법 승인 미평가','전체 규범 범위 미완료','최대 탐색 미실행'])assert(text.includes(item),item);
      assert.notEqual(received.trace.capture_id,received.psd.capture_id);
      assert.equal(await page.locator('#mount button, #mount input, #mount a, #mount select, #mount textarea').count(),0);
      if(name==='incomplete') {
        assert.equal(await page.locator('[data-spectrum=bandwidth]').count(),0);assert.match(await page.locator('[data-field=bandwidth-value]').innerText(),/계산값 없음/);
      } else if(name==='axis-unrepresentable') {
        assert.equal(await page.locator('svg').count(),0);assert.equal(await page.locator('[data-spectrum-chart-error]').count(),1);
        assert.match(await page.locator('[data-field=bandwidth-value]').innerText(),/1 Hz/);
      } else {
        assert.equal(await page.locator('[data-spectrum=trace]').count(),1);assert.equal(await page.locator('[data-spectrum=bandwidth]').count(),1);
        const band=await page.locator('[data-spectrum=bandwidth]').evaluate(node=>({left:node.x1.baseVal.value,right:node.x2.baseVal.value,width:node.getBBox().width}));
        assert(band.left<band.right && band.width>0);
      }
      if(name==='bandwidth-below') {
        assert.equal(await page.locator('[data-field=bandwidth-comparison]').getAttribute('data-comparison'),'below');
        assert.match(await page.locator('[data-field=bandwidth-margin]').innerText(),/e-11/);
      }
      if(name==='density-rounded-eight') {
        assert.match(await page.locator('[data-field=psd-power]').innerText(),/8 dBm/);
        assert.match(await page.locator('[data-field=psd-margin]').innerText(),/e-16/);
        assert.equal(await page.locator('[data-field=psd-comparison]').getAttribute('data-comparison'),'above');
      }
      await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(evidence,name+'-desktop.png'),fullPage:true});
      await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.screenshot({path:path.join(evidence,name+'-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1000});
    });
    result.actual_flow_executed=true;
    const dom=async()=>digest(await page.locator('#mount').innerHTML());await load('normal');const before=await dom();
    await check('bad GET responses retain the last actual normal DOM and value',async()=>{
      for(const name of Object.keys(negatives)) {
        const error=await page.evaluate(async name=>{try{await window.loadSpectrum(name);return null;}catch(error){return error.message;}},name);
        assert.equal(error,'invalid_spectrum_view');assert.equal(await dom(),before);
        assert.deepEqual(await page.evaluate(()=>window.lastSpectrum),normal);
      }
      assert.equal(await page.locator('#mount img, #mount script').count(),0);assert.equal(await page.evaluate(()=>window.spectrumInjected),undefined);
    });
    await check('forced renderer failure retains the actual normal DOM and value',async()=>{
      const error=await page.evaluate(async()=>{
        const original=document.createElementNS.bind(document);document.createElementNS=(namespace,tag,...args)=>{if(tag==='polyline'){document.createElementNS=original;throw new Error('PRIVATE_RENDER_CANARY');}return original(namespace,tag,...args);};
        try{await window.loadSpectrum('normal');return null;}catch(error){return error.message;}
      });
      assert.equal(error,'spectrum_render_failed');assert.equal(await dom(),before);assert.deepEqual(await page.evaluate(()=>window.lastSpectrum),normal);
    });
    await check('all five actual cases were fetched from self with zero JS errors external requests or browser writes',async()=>{
      for(const name of CASES) assert(reads.some(item=>item.path==='/data/'+name+'.json' && item.status===200));
      assert(reads.every(item=>item.method==='GET'));assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    });
    assert.equal(digest(fs.readFileSync(path.join(evidence,'producer.json'))),producerHash);result.immutable_producer=true;
  }catch(error){failure=error;result.error_code=error instanceof ToolFailure?error.code:'spectrum_actual_browser_failed';
    try{writeJson(path.join(evidence,'private-error.json'),{message:String(error?.stack || error)});}catch{}
  }finally{
    try{try{if(browser)await browser.close();cleanup.browser_closed=true;}finally{if(server)await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));cleanup.server_closed=true;}}
    catch(error){failure ||= error;result.error_code='owned_cleanup_failed';}
    try{if(sourceBefore){result.source_sha256_after=sourceHashes();assert.deepEqual(result.source_sha256_after,sourceBefore);result.source_unchanged=true;}}catch(error){failure ||= error;result.error_code='source_changed';}
    result.javascript_errors=errors.length;result.external_requests=external.length;
    result.passed=!failure && checks.length===8 && cleanup.producer_closed && cleanup.browser_closed && cleanup.server_closed;
    result.stage=result.passed?'complete':result.stage;
    writeJson(path.join(evidence,'http-reads.json'),reads);
    writeJson(path.join(evidence,'result.json'),result);
  }
  if(!result.passed) throw new ToolFailure(result.error_code || 'spectrum_actual_browser_failed');
  console.log(JSON.stringify({kind:result.kind,passed:checks.length,contract_fixture:false,python_math_connected:true,evidence}));return result;
}

async function selfTest(env=process.env) {
  const config=readConfig(env,['--self-test']),evidence=reserveEvidence(ROOT),checks=[];
  const result={kind:'synthetic_spectrum_actual_browser_self_test',actual_flow_executed:false,python_math_connected:false,
    synthetic:true,hardware_verified:false,ai_model_called:false,checks,passed:false};
  const check=(name,action,skip=false)=>{if(skip)checks.push({name,status:'skipped'});else{action();checks.push({name,status:'pass'});}};
  const fixture=(name,init='',vfinit='',entry='')=>{
    const root=path.join(evidence,name);fs.mkdirSync(root);fs.mkdirSync(path.join(root,'labflow'));fs.mkdirSync(path.join(root,'labflow/virtual_fleet'));
    for(const [relative,data] of [['labflow/__init__.py',init],['labflow/virtual_fleet/__init__.py',vfinit],['labflow/virtual_fleet/spectrum_math.py',entry]])if(data!==null)write(path.join(root,relative),data);
    return root;
  };
  const complete=fixture('complete'),guardScript=GUARD+'\nprint(json.dumps(_binding,ensure_ascii=False))';let probe=0;
  const launch=(source,cache=false)=>{
    const prefix='import sys;sys.path.insert(0,'+JSON.stringify(complete)+');'+(cache?'import labflow.virtual_fleet.spectrum_math;':'');
    const run=executePython(config,guardScript,source,prefix);
    write(path.join(evidence,'probe-'+probe+'-stdout.raw'),run.stdout || Buffer.alloc(0));write(path.join(evidence,'probe-'+probe+++'-stderr.raw'),run.stderr || Buffer.alloc(0));
    assert(!run.error,run.error?.message);return run;
  };
  try{
    check('only Python executable configuration is supported',()=>{
      for(const key of ['SPECTRUM_SOURCE_ROOT','SPECTRUM_OUTPUT_ROOT'])assert.throws(()=>readConfig({[key]:'foreign'},[]),/invalid_configuration/);
      assert.throws(()=>readConfig({SPECTRUM_PYTHON:''},[]),/invalid_configuration/);assert.throws(()=>readConfig({},['--source']),/invalid_configuration/);
    });
    check('existing evidence remains unchanged',()=>{const parent=path.join(evidence,'existing');fs.mkdirSync(parent);write(path.join(parent,'marker'),'preserve');assert.throws(()=>reserveEvidence(ROOT,parent),/exists/);assert.equal(fs.readFileSync(path.join(parent,'marker'),'utf8'),'preserve');});
    check('Windows case aliases terminate',()=>{
      const parent=path.join(evidence,'case');fs.mkdirSync(parent);const output=path.join(parent,'e').toUpperCase();
      const run=spawnSync(process.execPath,['-e',"require(process.argv[1]).reserveEvidence(process.argv[2],process.argv[3])",path.join(ROOT,'frontend/intake_fixture_browser_check.cjs'),ROOT,output],{cwd:ROOT,windowsHide:true,timeout:3000});
      assert(!run.error,run.error?.message);assert.equal(run.status,0);assert(fs.statSync(output).isDirectory());
    },process.platform!=='win32');
    check('ancestor traversal terminates at a root',()=>assert.throws(()=>evidenceAncestors(path.resolve(ROOT,'..','outside','new'),ROOT),/checkout root/));
    for(const [name,source,cache] of [
      ['missing math rejects fallback',fixture('missing-math','','',null),false],
      ['namespace parent rejects fallback',fixture('namespace',null,'',''),false],
      ['namespace virtual package is rejected',fixture('namespace-vf','',null,''),false],
      ['redirected package path is rejected',fixture('redirected','','__path__=['+JSON.stringify(path.join(complete,'labflow/virtual_fleet'))+']\n',''),false],
      ['cached foreign imports are rejected',fixture('cached'),true],
      ['foreign actual math file is rejected',fixture('wrong-file','','','__file__='+JSON.stringify(path.join(complete,'labflow/virtual_fleet/spectrum_math.py'))+'\n'),false],
      ['mutated parent import spec is rejected',fixture('wrong-parent-spec','__spec__.origin='+JSON.stringify(path.join(complete,'labflow/__init__.py'))+'\n'),false],
      ['mutated virtual package import spec is rejected',fixture('wrong-vf-spec','','__spec__.submodule_search_locations=['+JSON.stringify(path.join(complete,'labflow/virtual_fleet'))+']\n'),false],
    ])check(name,()=>assert.notEqual(launch(source,cache).status,0));
    check('complete source supplies exact actual import binding',()=>{const run=launch(complete);assert.equal(run.status,0);validateSourceBinding(JSON.parse(run.stdout.toString('utf8')),complete);});
    check('bad finite JSON and partial producer results are rejected',()=>{for(const value of ['null','{}','{"value":1e999}','[',' '.repeat(MAX_BYTES+1)])assert.throws(()=>parseProducer(Buffer.from(value)),/invalid_producer/);});
    result.passed=true;
  }catch{result.error_code='spectrum_self_test_failed';throw new ToolFailure(result.error_code);}
  finally{writeJson(path.join(evidence,'self-test.json'),result);}
  console.log(JSON.stringify({kind:result.kind,passed:checks.filter(item=>item.status==='pass').length,skipped:checks.filter(item=>item.status==='skipped').length,evidence}));return result;
}

module.exports={readConfig,parseProducer,main,selfTest};
if(require.main===module){
  try{readConfig(process.env,process.argv.slice(2));(process.argv[2]==='--self-test'?selfTest():main()).catch(error=>{console.error(JSON.stringify({error:error instanceof ToolFailure?error.code:'spectrum_actual_browser_failed'}));process.exitCode=1;});}
  catch{console.error(JSON.stringify({error:'invalid_configuration'}));process.exitCode=1;}
}
