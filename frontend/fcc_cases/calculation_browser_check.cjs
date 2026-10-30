/*039 real product HTTP/DOM acceptance; actual preparation is explicit and private. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{createHash}=require('node:crypto'),{pathToFileURL}=require('node:url');
const {reserveEvidence}=require('../intake_fixture_browser_check.cjs');
const {readPinned}=require('./route_browser_check.cjs');
const ROOT=fs.realpathSync(path.resolve(__dirname,'../..'));
const hash=blob=>createHash('sha256').update(blob).digest('hex');
const save=(folder,name,value)=>fs.writeFileSync(path.join(folder,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const wait=async(promise,ms=30000)=>{let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('calculation_check_timeout')),ms);})]);}finally{clearTimeout(timer);}};
function parseOptions(argv){
 const values={};for(let i=0;i<argv.length;i+=2){const key=argv[i],value=argv[i+1];if(!['--mode','--descriptor','--sha256'].includes(key)||Object.hasOwn(values,key)||typeof value!=='string'||!value)throw Error('invalid_configuration');values[key]=value;}
 const mode=values['--mode'],descriptor=values['--descriptor'],sha256=values['--sha256'];
 if(!['contract','actual'].includes(mode)||mode==='contract'&&(descriptor||sha256)||mode==='actual'&&(!descriptor||!sha256))throw Error('invalid_configuration');
 if(descriptor&&(!path.isAbsolute(descriptor)||path.extname(descriptor).toLowerCase()!=='.json'||/[\0\r\n]/.test(descriptor)||/^\\\\/.test(descriptor)))throw Error('invalid_configuration');
 if(sha256&&(!/^[a-f0-9]{64}$/.test(sha256)||sha256.length!==64))throw Error('invalid_configuration');
 return {mode,descriptor,sha256};
}
function sourceHashes(){
 const files=[];const visit=directory=>{for(const entry of fs.readdirSync(path.join(ROOT,directory),{withFileTypes:true})){assert(!entry.isSymbolicLink());const name=directory+'/'+entry.name;if(entry.isDirectory()&&entry.name!=='__pycache__')visit(name);else if(entry.isFile()&&/\.(?:py|mjs|cjs|js|css|html|json|sql)$/.test(name))files.push(name);}};
 for(const directory of ['labflow','frontend','control_sources','virtual_profiles'])visit(directory);
 for(const name of ['equipment.sqlite3','tests/test_fcc_case_ui_server.py','docs/fcc/fcc_case_calculation_ui_usage.md'])if(fs.existsSync(path.join(ROOT,name)))files.push(name);
 return Object.fromEntries(files.sort().map(name=>{const file=path.join(ROOT,name),s=fs.statSync(file);return [name,{sha256:hash(fs.readFileSync(file)),identity:[s.dev,s.ino,s.size,s.mtimeMs,s.mode]}];}));
}
const PYTHON_BOOT=String.raw`
from pathlib import Path
import hashlib,json,math,os,re,sys,tempfile,threading,types,traceback
from pypdf import PageObject,PdfReader
from pypdf._encryption import Encryption
from labflow import calculations,document_extract,fcc_report_calculation,control_packet_prepare as native
from labflow.fcc_report_cases import FccReportCaseCatalog
from labflow import fcc_case_calculation as service,fcc_case_catalog_host as host
from labflow.ui_server import create_server

ROOT=Path.cwd();args=json.loads(sys.stdin.readline());out=Path(args['evidence'])
assert out.parent==ROOT/'.local' and out.is_dir()
phase='metadata';protected=set();audit_events=[];servers=[];threads=[];inputs={};responses=[];local=threading.local()
def digest(blob):return hashlib.sha256(blob).hexdigest()
def stamp(p):
 s=p.stat();return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_mode]
def canonical(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def decode(blob,cap,depth=24,nodes=1000000):
 assert len(blob)<=cap and not blob.startswith(b'\xef\xbb\xbf')
 def pairs(rows):
  value={}
  for key,child in rows:
   assert key not in value;value[key]=child
  return value
 def bad(_):raise ValueError('nonfinite')
 value=json.loads(blob.decode('utf-8',errors='strict'),object_pairs_hook=pairs,parse_constant=bad)
 count=0
 def visit(item,level=0):
  nonlocal count
  count+=1;assert level<=depth and count<=nodes
  if type(item) is str:item.encode('utf-8',errors='strict')
  elif type(item) is float:assert math.isfinite(item)
  elif type(item) is dict:
   for key,child in item.items():visit(key,level+1);visit(child,level+1)
  elif type(item) is list:
   for child in item:visit(child,level+1)
 visit(value);return value
def write(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def audit(event,values):
 if phase=='http' and event=='open' and values and isinstance(values[0],(str,bytes,os.PathLike)):
  if str(Path(os.fsdecode(values[0])).resolve()).casefold() in protected:
   audit_events.append('protected_input_open');raise AssertionError('http_source_IO')
sys.addaudithook(audit)
codes={FccReportCaseCatalog.__init__.__wrapped__.__code__:'constructor',FccReportCaseCatalog.case.__wrapped__.__code__:'case',
 service.calculate_case_claim.__code__:'service036',fcc_report_calculation.check_report_calculation.__code__:'check023',
 calculations.calculate.__code__:'RF',document_extract.extract_document.__code__:'generic_extract',PageObject.extract_text.__code__:'native_text',
 PageObject.get_contents.__code__:'page_content',PdfReader.are_permissions_valid.fget.__code__:'permission_integrity',
 PdfReader.user_access_permissions.fget.__code__:'permission_flags',Encryption.verify.__code__:'empty_USER',native._WindowsIO.open_read.__code__:'native_open'}
traces={};source_descriptors=set()
def trace():return {'calls':dict.fromkeys([*codes.values(),'service_case','source_hash_read'],0),'text_pages':[],'content_pages':[],'gate_events':[]}
def profile(frame,event,value):
 if phase not in {'startup','http'}:return
 current=traces.setdefault(phase,trace());name=codes.get(frame.f_code)
 if event=='call' and frame.f_code is host._PinnedInputs.read.__code__ and frame.f_locals.get('role')=='pdf_source':
  local.source_read=True
 if event=='return' and frame.f_code is host._PinnedInputs.read.__code__ and frame.f_locals.get('role')=='pdf_source':
  source_descriptors.update(row['descriptor'] for row in frame.f_locals['self'].records if row['role']=='pdf_source');local.source_read=False
 if event=='call' and frame.f_code is native._read_descriptor.__code__:
  if getattr(local,'source_read',False) or frame.f_locals.get('descriptor') in source_descriptors:current['calls']['source_hash_read']+=1
 if name is None:return
 if event=='call':
  current['calls'][name]+=1
  if name=='service036':local.in_service=True
  if name=='case' and getattr(local,'in_service',False):current['calls']['service_case']+=1
  if phase=='http' and name in {'constructor','generic_extract','native_text','page_content','permission_integrity','permission_flags','empty_USER','native_open'}:
   audit_events.append(name);raise AssertionError('http_source_operation')
  if name in {'native_text','page_content'}:
   page=frame.f_locals['self'];pages=getattr(page.pdf,'flattened_pages',None) or []
   number=next((i+1 for i,candidate in enumerate(pages) if candidate is page),None)
   current['text_pages' if name=='native_text' else 'content_pages'].append(number)
   if name=='native_text':current['gate_events'].append({'event':'text','page':number})
 elif event=='return':
  if name=='service036':responses.append(value);local.in_service=False
  if name=='permission_integrity':current['gate_events'].append({'event':'integrity','valid':value is True})
  if name=='permission_flags' and value is not None:current['gate_events'].append({'event':'flags','copy':bool(int(value)&16),'accessibility':bool(int(value)&512)})
  if name=='empty_USER':current['gate_events'].append({'event':'auth','result':getattr(value,'name',None)})
sys.setprofile(profile);threading.setprofile(profile)
record={'mode':args['mode'],'task':'CALCULATION-UI039','status':'started','previous_attempts_counted':False}
try:
 pins={'labflow/fcc_report_cases.py':'4cc710f4e9a3bb1f604d303c1c9de1191a2a1f5519cf090d71d90c57d4c8394d',
 'labflow/document_extract.py':'7bcda620bddcdcce55e42215a69a335459a594b4964e1fa683305d10b8e5337a',
 'labflow/fcc_case_calculation.py':'f0a7bdd2cd6c851f8b9c461e0c848e29f827b43741e47fe11b315efd20c73b74',
 'labflow/fcc_case_catalog_host.py':'6ce4909dd0edaac800bf27bce2732a4c61e45014b25b6892690222c717435b4a',
 'labflow/fcc_report_calculation.py':'aa30c1cc3386e9dfdeefec2832818b03bbd8cb8525165e1ba4ebe2ed7e48920d',
 'labflow/calculations.py':'b50b416cf450beee44dc687b1d0045f1f99009276e31b8c39e5b5822db72efae'}
 for name,pin in pins.items():assert digest((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==pin
 expected=None;approval=None
 if args['mode']=='actual':
  backend=native._WindowsIO()
  try:
   reader=host._PinnedInputs(backend);descriptor_path=host._path(args['descriptor'],'.json',config=True)
   blob=reader.read(descriptor_path,'descriptor',args['sha256'],8192)
   descriptor=decode(blob,8192,8,512)
   assert type(descriptor) is dict and set(descriptor)=={'schema_version','kind','host_config','read_approval','expected_producer','request','expected_result','expected_response'}
   assert type(descriptor['schema_version']) is int and descriptor['schema_version']==1 and descriptor['kind']=='fcc_case_calculation_browser_input'
   caps={'host_config':65536,'read_approval':16384,'expected_producer':32*1024**2,'request':32768,'expected_result':131072,'expected_response':163840}
   loaded={};identities=set()
   for role,cap in caps.items():
    row=host._descriptor(descriptor[role],'.json',cap);raw=reader.descriptor(row,role,cap);loaded[role]=decode(raw,cap)
    info=stamp(row['path']);assert tuple(info[:2]) not in identities;identities.add(tuple(info[:2]))
    inputs[str(row['path'])]={'stamp':info,'sha256':row['sha256'],'bytes':row['bytes']};protected.add(str(row['path']).casefold())
   config=loaded['host_config'];approval=loaded['read_approval'];expected=loaded['expected_response'];command=loaded['request']
   # Enforce each compact semantic tree before the one approved native phase.
   decode(canonical(command),32768,10,512)
   assert type(command) is dict and set(command)=={'schema_version','case_id','calculation_request'}
   assert type(command['schema_version']) is int and command['schema_version']==1
   assert type(command['case_id']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',command['case_id'],re.ASCII)
   inner=command['calculation_request'];decode(canonical(inner),16384,8,256)
   assert type(inner) is dict and set(inner)=={'calculator','rule','method','input_claim_ids','reported_result_claim_id','comparison_policy'}
   assert inner['calculator']=='rf_power' and inner['reported_result_claim_id'] is None and inner['comparison_policy'] is None
   for field in ('rule','method'):assert type(inner[field]) is str and inner[field].strip() and len(inner[field])<=256 and not service._unsafe_text(inner[field])
   assert type(inner['input_claim_ids']) is dict and set(inner['input_claim_ids'])=={'reading'}
   assert type(inner['input_claim_ids']['reading']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',inner['input_claim_ids']['reading'],re.ASCII)
   decode(canonical(loaded['expected_result']),131072,16,8192)
   decode(canonical(expected),163840,20,10000)
   assert type(loaded['expected_result']) is dict and set(loaded['expected_result'])==service._RESULT_KEYS
   assert type(expected) is dict and set(expected)=={'schema_version','kind','corpus_id','case_id','status','request_context','result','error_code','execution_authorized'}
   assert canonical(expected['request_context'])==canonical(command) and canonical(expected['result'])==canonical(loaded['expected_result'])
   assert expected['status']=='calculated' and expected['execution_authorized'] is False
   assert approval['permission_integrity_and_mode_must_be_verified_before_native'] is True
   assert approval['copy_false_and_unknown_private_rights_preserved'] is True
   assert approval['outside_scope_content_operations_allowed'] is False and approval['decrypted_PDF_bulk_body_export_OCR_permission_change_allowed'] is False
   assert approval['manual_retained_textSHA_or_fake_case_allowed'] is False and approval['raw_values_quotes_and_results_public_or_external_allowed'] is False
   assert len(config['pdf_sources'])==1 and config['pdf_sources'][0]['sha256']==approval['original_PDF_sha256'] and config['pdf_sources'][0]['bytes']==approval['original_PDF_bytes']
   scope_row=host._descriptor(config['page_scope'],'.json',65536);scope_raw=reader.descriptor(scope_row,'approved_scope',65536);policy=decode(scope_raw,65536)
   source_entry=policy['sources'][approval['original_PDF_sha256']]
   assert source_entry['pages']==approval['permitted_selected_pages'] and source_entry['mode']==approval['mode']
   for row in [config['manifest'],config['packet'],config['page_scope'],*config['pdf_sources']]:
    p=host._path(row['path'],Path(row['path']).suffix.lower());inputs[str(p)]={'stamp':stamp(p),'sha256':row['sha256'],'bytes':row['bytes']};protected.add(str(p).casefold())
   inputs[str(descriptor_path)]={'stamp':stamp(descriptor_path),'sha256':args['sha256'],'bytes':len(blob)};protected.add(str(descriptor_path).casefold())
   phase='startup'
   catalog,host_receipt=host.load_fcc_case_catalog(descriptor['host_config']['path'],expected_config_sha256=descriptor['host_config']['sha256'])
   phase='metadata';reader.verify()
  finally:backend.close()
  producer={'schema_version':1,'summary':catalog.summary(),'cases':[catalog.case(p['case_id']) for p in catalog.summary()['case_previews']]}
  assert canonical(producer)==canonical(loaded['expected_producer'])
  startup=traces['startup'];assert startup['calls']['constructor']==1 and startup['calls']['native_text']==len(approval['permitted_selected_pages'])
  assert startup['text_pages']==approval['permitted_selected_pages'] and set(startup['content_pages'])==set(approval['permitted_selected_pages'])
  assert startup['calls']['source_hash_read']==2
  events=startup['gate_events'];first=next(i for i,event in enumerate(events) if event['event']=='text')
  assert {'event':'integrity','valid':True} in events[:first] and {'event':'flags','copy':False,'accessibility':True} in events[:first]
  assert host_receipt['page_scopes'][0]['requested_pages']==approval['permitted_selected_pages']
  write('host-receipt-private.json',host_receipt)
  record.update(genuine_host037_calls=1,producer_canonical_equals031=True,startup_new_phase=True,source_hash_passes=2,original_unchanged_verified_by_host=True)
 else:
  package=types.ModuleType('tests');package.__path__=[str(ROOT/'tests')];sys.modules['tests']=package
  from tests.test_fcc_case_calculation import inputs as synthetic_inputs
  phase='startup';catalog,command,_,_=synthetic_inputs();phase='metadata'
  producer={'schema_version':1,'summary':catalog.summary(),'cases':[catalog.case(command['case_id'])]}
  # Genuine long normal DTO, with existing036 arithmetic. Separate from HTTP/API counts.
  large,large_request,_,_=synthetic_inputs(family='𠮷'*16370,copies=8,explicit=True)
  large_detail=large.case(large_request['case_id']);large_response=service.calculate_case_claim(large,large_request)
  assert large_response['status']=='calculated'
  write('genuine-long-boundary-private.json',{'summary':large.summary(),'detail':large_detail,'request':large_request,'response':large_response})
  responses.clear();record.update(genuine_synthetic=True,boundary_service_calls_outside_HTTP=1)
 write('producer-private.json',producer);write('command-private.json',command)
 if expected is not None:write('expected-response-private.json',expected)
 with tempfile.TemporaryDirectory(dir=out,prefix='workspace-') as workspace:
  server=create_server(workspace,port=0,fcc_case_catalog=catalog);servers.append(server)
  thread=threading.Thread(target=server.serve_forever,daemon=True);threads.append(thread);thread.start()
  phase='http';print(json.dumps({'port':server.server_port,'case_id':command['case_id']}),flush=True)
  action=json.loads(sys.stdin.readline());assert set(action)=={'finish'} and action['finish'] is True
  for server in servers:server.shutdown();server.server_close()
  for thread in threads:thread.join(5);assert not thread.is_alive()
  phase='verification'
  http=traces.get('http',trace());assert not audit_events
  assert http['calls']['constructor']==0 and http['calls']['native_text']==0 and http['calls']['native_open']==0
  if args['mode']=='actual':
   assert http['calls']['service036']==http['calls']['service_case']==http['calls']['check023']==http['calls']['RF']==1
   assert len(responses)==1 and canonical(responses[0])==canonical(expected)
  for name,before in inputs.items():
   p=Path(name);assert stamp(p)==before['stamp']
   if p.suffix.lower()=='.json':assert digest(p.read_bytes())==before['sha256']
  record.update(status='pass',traces=traces,input_states=inputs,input_states_unchanged=True,HTTP_protected_source_IO=0,HTTP_constructor=0,HTTP_responses=len(responses),resources_closed=True)
  write('service-responses-private.json',responses)
except Exception:
 phase='verification';record.update(status='failed',traces=traces,HTTP_audit_events=audit_events)
 (out/'failure-python-private.txt').write_text(traceback.format_exc(),encoding='utf-8')
 raise
finally:
 for server in servers:server.shutdown();server.server_close()
 for thread in threads:thread.join(5)
 write('caller-result-private.json',record)
`;

async function startCaller(options,evidence){
 const executable=process.env.FCC_CASE_CALCULATION_PYTHON||require('../managed_paths.cjs').python(ROOT);
 assert(path.isAbsolute(executable)&&fs.statSync(executable).isFile(),'invalid_python_executable');
 const child=spawn(executable,['-X','utf8','-B','-c',PYTHON_BOOT],{cwd:ROOT,windowsHide:true,stdio:['pipe','pipe','pipe'],env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1',PYTHONNOUSERSITE:'1',PYTHONPATH:ROOT}});
 const stdout=[],stderr=[];let outBytes=0,errBytes=0,ended=false,overflow=false,readyText='',resolved=false;
 let resolveReady,rejectReady;const ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});
 const exit=new Promise(resolve=>child.once('exit',code=>{ended=true;if(!resolved)rejectReady(Error('caller_exited_before_ready'));resolve(code);}));
 child.once('error',rejectReady);
 const collect=(chunks,chunk,total)=>{if(total<1024**2)chunks.push(chunk.subarray(0,1024**2-total));};
 child.stdout.on('data',chunk=>{collect(stdout,chunk,outBytes);outBytes+=chunk.length;if(outBytes>1024**2){overflow=true;child.kill();rejectReady(Error('caller_stdout_limit'));return;}readyText+=chunk.toString('utf8');if(!resolved&&readyText.includes('\n')){try{const value=JSON.parse(readyText.split('\n')[0]);resolved=true;resolveReady(value);}catch(error){rejectReady(error);}}});
 child.stderr.on('data',chunk=>{collect(stderr,chunk,errBytes);errBytes+=chunk.length;if(errBytes>1024**2){overflow=true;child.kill();rejectReady(Error('caller_stderr_limit'));}});
 child.stdin.write(JSON.stringify({...options,evidence})+'\n');
 const resource={child,async close(){if(!ended)child.stdin.end(JSON.stringify({finish:true})+'\n');let code;try{code=await wait(exit,15000);}catch(error){child.kill();await wait(exit,5000).catch(()=>{});throw error;}finally{fs.writeFileSync(path.join(evidence,'caller.stdout.log'),Buffer.concat(stdout),{flag:'wx'});fs.writeFileSync(path.join(evidence,'caller.stderr.log'),Buffer.concat(stderr),{flag:'wx'});}assert(!overflow,'caller_output_limit');return code;}};
 try{return {...resource,...await wait(ready,30000)};}catch(error){await resource.close().catch(()=>{});throw error;}
}

async function productBrowser(caller,options,evidence,checks){
 const {chromium}=require('playwright'),browser=await chromium.launch({headless:true});
 const errors=[],external=[],posts=[];let finalValue;
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});page.setDefaultTimeout(30000);
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{const url=new URL(request.url());if(url.origin!=='http://127.0.0.1:'+caller.port)external.push(request.url());});
  page.on('response',async response=>{if(response.request().method()==='POST'&&response.url().endsWith('/api/fcc-cases/calculations'))posts.push(response);});
  const command=JSON.parse(fs.readFileSync(path.join(evidence,'command-private.json'),'utf8'));
  const producer=JSON.parse(fs.readFileSync(path.join(evidence,'producer-private.json'),'utf8'));
  const model=await import(pathToFileURL(path.join(__dirname,'calculation_model.mjs')).href);
  const summary=model.parseFccCaseCalculationSummaryJson(JSON.stringify(producer.summary));
  const detail=model.parseFccCaseCalculationCaseJson(JSON.stringify(producer.cases.find(value=>value.case.case_id===command.case_id)),command.case_id,summary);
  checks.push('independent_typed_genuine_summary_and_case');
  await page.goto('http://127.0.0.1:'+caller.port+'/fcc-cases',{waitUntil:'networkidle'});
  await page.locator('.fcc-calculation-summary-status[data-state=ready]').waitFor();
  const panel=page.locator('.fcc-calculation');
  for(const name of ['case_id','reading','rule','method'])assert.equal(await panel.locator('[name='+name+']').inputValue(),'');
  assert.equal(posts.length,0);checks.push('explicit_placeholders_no_automatic_POST');
  await panel.locator('[name=case_id]').selectOption(command.case_id);await panel.locator('.fcc-calculation-load').click();
  await panel.locator('.fcc-calculation-detail-status[data-state=ready]').waitFor();
  assert.equal(await panel.locator('[name=reading]').inputValue(),'');
  await panel.locator('[name=case_id]').focus();await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(()=>document.activeElement?.name),'reading');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement?.name),'rule');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement?.name),'method');
  checks.push('keyboard_explicit_input_order');
  await panel.locator('[name=reading]').selectOption(command.calculation_request.input_claim_ids.reading);
  await panel.locator('[name=rule]').fill(command.calculation_request.rule);
  await panel.locator('[name=method]').fill(command.calculation_request.method);
  const responseWait=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/api/fcc-cases/calculations'));
  await panel.locator('.fcc-calculation-submit').click();const response=await responseWait;
  assert.equal(response.status(),200);assert.equal(response.headers()['cache-control'],'no-store');
  assert.deepEqual(response.request().postDataJSON(),command);
  finalValue=model.parseFccCaseCalculationJson(await response.text(),command,detail);
  assert.equal(finalValue.status,'calculated');
  if(options.mode==='actual')assert.deepEqual(finalValue,JSON.parse(fs.readFileSync(path.join(evidence,'expected-response-private.json'),'utf8')));
  await panel.locator('.fcc-calculation-status[data-state=calculated]').waitFor();
  assert.equal(await panel.locator('.fcc-calculation-value').textContent(),JSON.stringify(finalValue.result.calculation.value)+' W');
  const content=await panel.locator('.fcc-calculation-results').textContent();
  for(const value of [finalValue.case_id,finalValue.result.inputs[0].claim_id,finalValue.result.inputs[0].sources[0].source_sha256])assert(content.includes(value));
  assert.equal(finalValue.execution_authorized,false);assert(Object.values(finalValue.result.verification).every(value=>value===false));
  checks.push('explicit_UI_POST_to036_result20_typed_and_DOM','POST_no_store_service_vs_transport','original_projection_source_and_false_authority');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);checks.push('390px_no_horizontal_overflow');
  await page.screenshot({path:path.join(evidence,'calculation-390.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  await page.screenshot({path:path.join(evidence,'calculation-1440.png'),fullPage:true});
  if(options.mode==='contract'){
   const before=await panel.locator('.fcc-calculation-results').textContent();
   await panel.locator('[name=method]').fill(command.calculation_request.method+'-OTHER');
   assert.equal(await panel.locator('.fcc-calculation-results').getAttribute('data-stale'),'true');
   await panel.locator('.fcc-calculation-submit').click();
   await panel.locator('.fcc-calculation-status[data-state=insufficient_evidence]').waitFor();
   assert.equal(await panel.locator('.fcc-calculation-value').count(),0);assert((await panel.locator('.fcc-calculation-results').textContent()).includes('method_mismatch'));
   assert.notEqual(await panel.locator('.fcc-calculation-results').textContent(),before);checks.push('real_service_insufficient_null_calculation');
   const boundary=JSON.parse(fs.readFileSync(path.join(evidence,'genuine-long-boundary-private.json'),'utf8'));
   const index=model.parseFccCaseCalculationSummaryJson(JSON.stringify(boundary.summary));
   const longDetail=model.parseFccCaseCalculationCaseJson(JSON.stringify(boundary.detail),boundary.request.case_id,index);
   assert.deepEqual(model.validateFccCaseCalculationResponse(boundary.response,boundary.request,longDetail),boundary.response);
   assert(Buffer.byteLength(JSON.stringify(boundary.response.result),'utf8')>65536);checks.push('genuine_long_parent_codepoints_and8_source_projection');
   // Explicit fault/projection injection: one raw reply must be independently
   // accepted by039 even when the unchanged024 UTF16 bound rejects it.
   const isolated=await browser.newPage();let summaryReads=0;
   await isolated.route('**/api/fcc-cases/summary',route=>{summaryReads++;return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(boundary.summary)});});
   await isolated.route('**/api/fcc-cases/cases/*',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(boundary.detail)}));
   await isolated.goto('http://127.0.0.1:'+caller.port+'/fcc-cases',{waitUntil:'networkidle'});
   await isolated.locator('#fcc-route-state[data-state=error]').waitFor();
   await isolated.locator('.fcc-calculation-summary-status[data-state=ready]').waitFor();assert.equal(summaryReads,1);
   await isolated.locator('.fcc-calculation [name=case_id]').selectOption(boundary.request.case_id);
   await isolated.locator('.fcc-calculation-load').click();await isolated.locator('.fcc-calculation-detail-status[data-state=ready]').waitFor();
   checks.push('synthetic_injection_shared_raw_independent_typed_parent_limit');await isolated.close();
  }
  const target='http://127.0.0.1:'+caller.port+'/api/fcc-cases/calculations';
  const GET=await page.request.get(target),HEAD=await page.request.head(target);
  assert.equal(GET.status(),405);assert.equal(HEAD.status(),405);assert.equal((await HEAD.body()).length,0);assert.equal(GET.headers()['allow'],'POST');
  checks.push('calculation_GET_HEAD405');
  assert.equal(errors.length,0);assert.equal(external.length,0);checks.push('runtime_JS0_external_requests0');
  save(evidence,'browser-private.json',{posts:posts.length,errors,external,response:finalValue});
 }finally{await browser.close();}
 return finalValue;
}

async function viewContract(caller,evidence,checks){
 const {chromium}=require('playwright'),browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();page.setDefaultTimeout(30000);await page.goto('http://127.0.0.1:'+caller.port+'/fcc-cases',{waitUntil:'networkidle'});
  const producer=JSON.parse(fs.readFileSync(path.join(evidence,'producer-private.json'),'utf8')),command=JSON.parse(fs.readFileSync(path.join(evidence,'command-private.json'),'utf8'));
  const response=JSON.parse(fs.readFileSync(path.join(evidence,'browser-private.json'),'utf8')).response;
  const result=await page.evaluate(async({producer,command,response})=>{
   const {createFccCaseCalculation}=await import('/fcc-cases/calculation_view.mjs');
   const container=document.createElement('div');document.body.append(container);const pending=[];let pendingSummary=null;
   const panel=createFccCaseCalculation(container,{readSummary:()=>pendingSummary??Promise.resolve(JSON.stringify(producer.summary)),readCase:async()=>JSON.stringify(producer.cases[0]),calculate:request=>new Promise((resolve,reject)=>pending.push({request,resolve,reject}))});
   await panel.refresh();const root=panel.root,field=name=>root.querySelector('[name='+name+']');
   const tick=()=>new Promise(resolve=>setTimeout(resolve,0)),change=(name,value)=>{field(name).value=value;field(name).dispatchEvent(new Event(name==='rule'||name==='method'?'input':'change',{bubbles:true}));};
   change('case_id',command.case_id);root.querySelector('.fcc-calculation-load').click();await tick();
   change('reading',command.calculation_request.input_claim_ids.reading);change('rule',command.calculation_request.rule);change('method',command.calculation_request.method);
   const submit=()=>root.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
   submit();submit();pending[1].resolve(JSON.stringify(response));await tick();
   const content=root.querySelector('.fcc-calculation-results').textContent;
   pending[0].resolve('{bad stale JSON');await tick();
   const staleIgnored=content===root.querySelector('.fcc-calculation-results').textContent && root.querySelector('.fcc-calculation-status').dataset.state==='calculated';
   submit();change('method',command.calculation_request.method+'-CHANGED');pending[2].resolve(JSON.stringify(response));await tick();
   const inputOnlyIgnored=root.querySelector('.fcc-calculation-status').dataset.state==='idle' && content===root.querySelector('.fcc-calculation-results').textContent;
   change('method',command.calculation_request.method);submit();change('method','');pending[3].reject(Error('synthetic transport failure'));await tick();
   const staleErrorIgnored=root.querySelector('.fcc-calculation-status').dataset.state==='idle';
   submit();const noPOSTonInvalid=pending.length===4 && root.querySelector('.fcc-calculation-status').dataset.state==='error';
   change('method',command.calculation_request.method);submit();const elsewhere=document.createElement('button');elsewhere.textContent='reader focus sentinel';document.body.append(elsewhere);elsewhere.focus();pending[4].resolve(JSON.stringify(response));await tick();
   const focusKept=document.activeElement===elsewhere;
   submit();pending[5].reject(Error('synthetic failure'));await tick();const lastGoodKept=content===root.querySelector('.fcc-calculation-results').textContent && root.querySelector('.fcc-calculation-status').dataset.state==='error';
   submit();pending[6].resolve(JSON.stringify({...response,corpus_id:null,status:'rejected',result:null,error_code:'fcc_case_not_found'}));await tick();
   const rejectedDistinct=root.querySelector('.fcc-calculation-status').dataset.state==='rejected' && content===root.querySelector('.fcc-calculation-results').textContent;
   submit();await panel.refresh();pending[7].resolve(JSON.stringify(response));await tick();const refreshClears=root.querySelector('.fcc-calculation-status').dataset.state==='idle';
   let release;pendingSummary=new Promise(resolve=>{release=resolve;});const refreshing=panel.refresh();
   const refreshBlocksOldSelection=field('case_id').disabled && root.querySelector('.fcc-calculation-load').disabled;
   release(JSON.stringify(producer.summary));await refreshing;
   panel.destroy();elsewhere.remove();container.remove();return {staleIgnored,inputOnlyIgnored,staleErrorIgnored,noPOSTonInvalid,focusKept,lastGoodKept,rejectedDistinct,refreshClears,refreshBlocksOldSelection};
  },{producer,command,response});
  for(const [name,value] of Object.entries(result)){assert.equal(value,true,name);checks.push('DOM_'+name);}
  save(evidence,'view-contract-private.json',{synthetic_trusted_transport:true,result});
 }finally{await browser.close();}
}

async function main(argv=process.argv.slice(2)){
 const options=parseOptions(argv);if(options.mode==='actual')readPinned(options.descriptor,options.sha256,8192);
 const evidence=reserveEvidence(ROOT),before=sourceHashes(),checks=[];let caller=null,error=null;
 const result={kind:'fcc_case_calculation_product_browser',mode:options.mode,evidence:path.relative(ROOT,evidence).replaceAll('\\','/'),status:'started',checks};
 const deadline=setTimeout(()=>{caller?.child.kill();},180000);
 try{
  caller=await startCaller(options,evidence);await wait(productBrowser(caller,options,evidence,checks),90000);
  if(options.mode==='contract')await wait(viewContract(caller,evidence,checks),30000);
  result.status='pass';
 }catch(failure){error=failure;result.status='failed';fs.writeFileSync(path.join(evidence,'failure-private.txt'),failure.stack||String(failure),{flag:'wx'});}
 finally{
  try{if(caller){result.child_exit=await caller.close();assert.equal(result.child_exit,0);const receipt=JSON.parse(fs.readFileSync(path.join(evidence,'caller-result-private.json'),'utf8'));assert.equal(receipt.status,'pass');result.caller_status=receipt.status;result.source_IO_during_HTTP=receipt.HTTP_protected_source_IO;result.resources_closed=receipt.resources_closed;}}
  catch(failure){error=error||failure;result.status='failed';result.cleanup_failure=String(failure);}
  clearTimeout(deadline);result.source_before=before;result.source_unchanged=JSON.stringify(before)===JSON.stringify(sourceHashes());if(!result.source_unchanged){error=error||Error('source_changed');result.status='failed';}
  result.check_count=checks.length;save(evidence,'result.json',result);
 }
 process.stdout.write(JSON.stringify({mode:options.mode,status:result.status,checks:checks.length,evidence:result.evidence,result_sha256:hash(fs.readFileSync(path.join(evidence,'result.json')))})+'\n');
 if(error)throw Error('calculation_browser_check_failed; inspect private evidence '+result.evidence);
 return result;
}
module.exports={parseOptions,main};
if(require.main===module)main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
