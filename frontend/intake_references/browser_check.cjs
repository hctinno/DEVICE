/*044 A1 whole synthetic DTOs; trusted transport DOM acceptance, no product API. */
const copy=value=>structuredClone(value);
function createSyntheticBundle(){
 const snapshot='a'.repeat(64),receipt='b'.repeat(64),record='c'.repeat(64);
 const created='2026-10-23T14:00:00.123456+00:00';
 const head={record_id:record,seq:3,request_id:'SYNTHETIC-REQUEST-044',revision:2,
  origin_job_id:'SYNTHETIC-JOB-044',reference_receipt_id:receipt,binding_status:'current_at_append',
  expected_snapshot_id:snapshot,append_observation:{expected_snapshot_id:snapshot,captured_snapshot_id:snapshot,
   head_before_record_id:null,head_after_record_id:record,head_advanced:true,preparation_ready:false,observed_at:created},
  source_modes:{intake_revision_synthetic:true,catalog_synthetic:true,intake_provenance_status:'confirmed'},created_at:created};
 const older=copy(head);Object.assign(older,{record_id:'d'.repeat(64),seq:2,request_id:'SYNTHETIC-HISTORICAL-044',revision:1,binding_status:'historical_provided'});
 Object.assign(older.append_observation,{head_advanced:false,head_before_record_id:null,head_after_record_id:null,captured_snapshot_id:null});
 Object.assign(older.source_modes,{catalog_synthetic:null,intake_provenance_status:'not_assessed'});
 const context={intake_id:'SYNTHETIC-INTAKE-044',revision:2,snapshotGeneration:1};
 const history={schema_version:1,kind:'intake_reference_history',intake_id:context.intake_id,available:true,
  records:[head,older],next_before_seq:null,verification:{record_metadata_verified:true,payloads_reverified:false,
   original_sources_reverified:false,database_currentness_verified:false}};
 const current={schema_version:1,kind:'intake_reference_review_current',intake_id:context.intake_id,available:true,status:'current',
  record:copy(head),reference_summary:{receipt_id:receipt,status:'bound',context_id:'e'.repeat(64),
   selected_case_ids:['SYNTHETIC-CASE-A','SYNTHETIC-CASE-B'],accepted_reference_count:2},
  current_observation:{snapshot_id:snapshot,head_record_id:record,preparation_ready:false,observed_at:'2026-10-24T01:02:03+00:00'},
  reason_codes:['preparation_not_ready'],verification:{record_hash_verified:true,database_snapshot_observed:true,
   reference_source_currentness_verified:false,operational_authority_granted:false,model_execution_verified:false,evaluation_executed:false}};
 return {context,history,current};
}
async function main(argv=process.argv.slice(2)){
 if(argv.length===2&&argv[0]==='--mode'&&argv[1]==='frontend')return frontendMain();
 const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
 const {createHash}=require('node:crypto'),{execFileSync}=require('node:child_process');
 assert.equal(argv.length,0,'invalid_configuration');
 const root=fs.realpathSync(path.resolve(__dirname,'../..')),local=path.join(root,'.local');
 fs.mkdirSync(local,{recursive:true});const evidence=fs.mkdtempSync(path.join(local,'ir-'));
 const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
 const write=(name,value)=>fs.writeFileSync(path.join(evidence,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 const snapshot=()=>{
  const names=execFileSync('git',['ls-files','-z','--','labflow','frontend'],{cwd:root}).toString('utf8').split('\0');
  names.push('frontend/intake_references/model.mjs','frontend/intake_references/view.mjs',
   'frontend/intake_references/model.test.mjs','frontend/intake_references/browser_check.cjs','docs/fcc/intake_reference_ui_usage.md');
  return Object.fromEntries([...new Set(names)].filter(name=>name&&/\.(py|mjs|cjs|js|css|html|sql|json|md)$/.test(name)).sort()
   .map(name=>{const p=path.join(root,name);return [name,fs.existsSync(p)?hash(fs.readFileSync(p)):null];}));
 };
 const before=snapshot(),checks=[],errors=[],external=[];write('source-pins-before.json',before);let browser,server,page,failure=null;
 const result={phase:'044 A1 synthetic trusted transport DOM',A2_product_HTTP_executed:false,
  Store_API_model_hardware_executed:false,original_PDF_source_reads:0,checks,
  browser_closed:false,server_closed:false,source_unchanged:false,status:'fail'};
 try{
  const files={'/model.mjs':path.join(__dirname,'model.mjs'),'/view.mjs':path.join(__dirname,'view.mjs'),'/base.css':path.join(root,'frontend/styles.css')};
  const css='body{margin:0;background:#f3f6fa}main{max-width:1200px;margin:auto;padding:16px}.ir-panel{padding:18px;min-width:0}.ir-controls{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.ir-section{margin-top:18px}.ir-record{border-top:1px solid #dbe3ed;padding:12px 0}.ir-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 14px}.ir-fields div{min-width:0}.ir-fields dt{font-size:11px;color:#53657b}.ir-fields dd{margin:2px 0 6px;overflow-wrap:anywhere;font-size:12px}.ir-results[data-stale=true]{border-left:3px solid #d39b30;padding-left:10px}.ir-status{font-size:12px;overflow-wrap:anywhere}button{padding:8px 12px}@media(max-width:600px){main{padding:10px}.ir-panel{padding:12px}.ir-fields{grid-template-columns:1fr}}';
  server=http.createServer((req,res)=>{
   res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
   res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
   if(req.method!=='GET'){res.writeHead(405);return res.end();}
   if(req.url==='/'){res.setHeader('Content-Type','text/html; charset=utf-8');return res.end('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>044 A1 합성 구성요소 검증</title><link rel="stylesheet" href="/base.css"><link rel="stylesheet" href="/harness.css"><main><button id="outside">외부 초점</button><div id="mount"></div></main></html>');}
   if(req.url==='/harness.css'){res.setHeader('Content-Type','text/css');return res.end(css);}
   const file=files[req.url];if(!file||!fs.existsSync(file)){res.writeHead(404);return res.end();}
   res.setHeader('Content-Type',req.url.endsWith('.css')?'text/css':'text/javascript');res.end(fs.readFileSync(file));
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const origin='http://127.0.0.1:'+server.address().port;
  const {chromium}=require('playwright');browser=await chromium.launch({headless:true});
  page=await browser.newPage({viewport:{width:390,height:844}});page.setDefaultTimeout(10000);
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(new URL(request.url()).origin!==origin)external.push(request.url());});
  await page.goto(origin,{waitUntil:'networkidle'});
  const f=createSyntheticBundle();write('synthetic-input.json',f);
  const first=await page.evaluate(async fixture=>{
   const module=await import('/view.mjs');
   if(Object.keys(module).join()!=='createIntakeReferenceReview')throw Error('view_exports');
   const calls={history:[],current:[]},deferred={history:[],current:[]};
   const make=(type,args)=>{calls[type].push({id:args[0],query:type==='history'?args[1]:null,signal:args.at(-1)});let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});deferred[type].push({resolve,reject});return promise;};
   const api=module.createIntakeReferenceReview(document.querySelector('#mount'),{
    readHistory:(...args)=>make('history',args),readCurrent:(...args)=>make('current',args)});
   window.a1={api,calls,deferred,f:fixture,poisonReads:0,encodeCalls:0};
   const NativeEncoder=globalThis.TextEncoder;
   globalThis.TextEncoder=class extends NativeEncoder{encode(value){window.a1.encodeCalls++;return super.encode(value);}};
   const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
   window.a1.tick=async()=>{await tick();await tick();};
   window.a1.hvalue=(id=fixture.context.intake_id,allowed=true)=>{const value=structuredClone(fixture.history);value.intake_id=id;return {raw_json:JSON.stringify(value),read_allowed:allowed};};
   window.a1.cvalue=(id=fixture.context.intake_id)=>{const value=structuredClone(fixture.current);value.intake_id=id;return JSON.stringify(value);};
   window.a1.poison=()=>Object.defineProperty({read_allowed:true},'raw_json',{enumerable:true,get(){window.a1.poisonReads++;throw Error('SYNTHETIC LATE GETTER');}});
   return {keys:Object.keys(api).sort(),calls:calls.history.length+calls.current.length};
  },f);
  assert.deepEqual(first.keys,['destroy','refreshHistory','root','setContext','setPending']);assert.equal(first.calls,0);checks.push('exact_view_exports_no_initial_transport');
  const exercise=async(label,run)=>{const value=await page.evaluate(run);checks.push(label);return value;};
  await exercise('context_metadata_once_false_permission_nulls_and_no_automatic_current',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.api.setContext(null);a.api.setContext(a.f.context);a.api.setContext({...a.f.context});
   expect(a.calls.history.length===1&&a.calls.current.length===0,'automatic_counts');a.deferred.history[0].resolve(a.hvalue(undefined,false));await a.tick();
   expect(a.api.root.querySelector('.ir-current-read').disabled,'permission_false');
   expect(a.api.root.querySelector('.ir-history-results').textContent.includes('null'),'null_preserved');
   expect(a.calls.history[0].query.limit===20&&a.calls.history[0].query.before_seq===null,'query2');
  });
  await exercise('new_generation_enables_only_explicit_current',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.api.setContext({...a.f.context,snapshotGeneration:2});
   a.deferred.history[1].resolve(a.hvalue());await a.tick();expect(a.calls.current.length===0,'generation_current');
  });
  await page.locator('.ir-current-read').focus();await page.locator('.ir-current-read').press('Enter');
  checks.push('native_keyboard_Enter_explicit_current');
  await exercise('explicit_current_once_original_observation_and_outside_focus',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};const button=a.api.root.querySelector('.ir-current-read');
   button.click();expect(a.calls.current.length===1,'duplicate_current');document.querySelector('#outside').focus();
   a.deferred.current[0].resolve(a.cvalue());await a.tick();
   expect(document.activeElement.id==='outside','focus_stolen');expect(a.api.root.querySelector('.ir-current-status').dataset.state==='current','current_status');
   const content=a.api.root.textContent;expect(content.includes('등록 당시 일치')&&content.includes('false')&&content.includes('KST'),'literal_status_time');
   expect(content.includes(a.f.current.current_observation.observed_at),'original_time');
  });
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:path.join(evidence,'a1-390.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:path.join(evidence,'a1-1440.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});checks.push('390_and1440_synthetic_DOM_no_overflow');
  await exercise('independent_lastgood_history_failure_does_not_cancel_current',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.hgood=a.api.root.querySelector('.ir-history-results').textContent;
   a.api.root.querySelector('.ir-current-read').click();void a.api.refreshHistory();a.deferred.history[2].reject(Error('SYNTHETIC PRIVATE TRANSPORT'));
   await a.tick();expect(a.api.root.querySelector('.ir-history-results').textContent===a.hgood,'history_lastgood');
   expect(!a.calls.current[1].signal.aborted,'independent_current_abort');a.deferred.current[1].resolve(a.cvalue());await a.tick();
   expect(a.api.root.querySelector('.ir-current-status').dataset.state==='current','independent_current_result');
  });
  await exercise('metadata_pagination_uses_exact_safe_cursor_without_current',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};void a.api.refreshHistory();const h=structuredClone(a.f.history);
   h.records=Array.from({length:20},(_,i)=>{const r=structuredClone(h.records[1]);r.seq=30-i;r.record_id=(i+20).toString(16).padStart(64,'0');r.request_id='SYNTHETIC-PAGE-'+i;return r;});h.next_before_seq=11;
   a.deferred.history[3].resolve({raw_json:JSON.stringify(h),read_allowed:true});await a.tick();a.api.root.querySelector('.ir-history-previous').click();
   expect(a.calls.history[4].query.before_seq===11,'cursor_exact');h.records=h.records.slice(0,2);h.records[0].seq=10;h.records[1].seq=9;h.next_before_seq=null;
   a.deferred.history[4].resolve({raw_json:JSON.stringify(h),read_allowed:true});await a.tick();expect(a.calls.current.length===2,'pagination_current');
  });
  await exercise('late_history_success_and_current_reject_are_dropped_before_parse',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};void a.api.refreshHistory();a.api.setContext({...a.f.context,intake_id:'SYNTHETIC-B',snapshotGeneration:3});
   expect(a.calls.history[5].signal.aborted,'history_abort');a.deferred.history[5].resolve(a.poison());
   a.deferred.history[6].resolve(a.hvalue('SYNTHETIC-B'));await a.tick();a.api.root.querySelector('.ir-current-read').click();
   a.api.setContext({...a.f.context,snapshotGeneration:4});expect(a.calls.current[2].signal.aborted,'current_abort');
   const error={};Object.defineProperty(error,'message',{get(){a.poisonReads++;throw Error('LATE PRIVATE ERROR');}});a.deferred.current[2].reject(error);
   a.deferred.history[7].resolve(a.hvalue());await a.tick();expect(a.poisonReads===0,'stale_parsed');expect(a.calls.current.length===3,'selection_auto_current');
  });
  await exercise('pending_invalidates_both_and_resumes_only_latest_queued_context',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.api.root.querySelector('.ir-current-read').click();void a.api.refreshHistory();
   a.api.setPending(true);expect(a.calls.current[3].signal.aborted&&a.calls.history[8].signal.aborted,'pending_abort');
   a.api.setContext({...a.f.context,intake_id:'SYNTHETIC-B',snapshotGeneration:5});a.api.setContext({...a.f.context,intake_id:'SYNTHETIC-C',snapshotGeneration:6});
   expect(a.calls.history.length===9,'pending_called');a.api.setPending(false);expect(a.calls.history.length===10&&a.calls.history[9].id==='SYNTHETIC-C','latest_queued');
   const encodes=a.encodeCalls;a.deferred.history[8].resolve(a.poison());a.deferred.current[3].resolve(a.cvalue());await a.tick();
   expect(a.encodeCalls===encodes,'late_current_parser_called');
   a.deferred.history[9].resolve(a.hvalue('SYNTHETIC-C'));await a.tick();expect(a.poisonReads===0,'pending_late_parse');
  });
  await exercise('invalid_context_clears_active_queued_and_pending_new_context_marker',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.api.setPending(true);a.api.setContext({...a.f.context,intake_id:'SYNTHETIC-B',snapshotGeneration:7});
   a.api.setContext({invalid:true});a.api.setPending(false);await a.tick();expect(a.calls.history.length===10,'invalid_queued_revived');
   expect(a.api.root.querySelector('.ir-current-read').disabled,'invalid_allowed');a.api.setPending('false');
   expect(a.calls.history.length===10,'coerced_pending');a.api.setContext({...a.f.context,snapshotGeneration:8});
   a.deferred.history[10].resolve(a.hvalue());await a.tick();expect(a.calls.history.length===11,'repair_context');
  });
  await exercise('unsafe_history_seq_keeps_lastgood_disables_permission_and_pagination',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.hgood=a.api.root.querySelector('.ir-history-results').textContent;
   void a.api.refreshHistory();a.deferred.history[11].resolve({raw_json:JSON.stringify(a.f.history).replace('"seq":3','"seq":9007199254740993'),read_allowed:true});await a.tick();
   expect(a.api.root.querySelector('.ir-history-status').dataset.state==='unrepresentable','unsafe_history_state');
   expect(a.api.root.querySelector('.ir-history-results').textContent===a.hgood,'unsafe_history_lastgood');
   expect(a.api.root.querySelector('.ir-current-read').disabled&&a.api.root.querySelector('.ir-history-previous').disabled,'unsafe_controls');
  });
  await exercise('unsafe_current_keeps_independent_lastgood_without_rounding',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};void a.api.refreshHistory();a.deferred.history[12].resolve(a.hvalue());await a.tick();
   a.cgood=a.api.root.querySelector('.ir-current-results').textContent;a.api.root.querySelector('.ir-current-read').click();
   a.deferred.current[4].resolve(a.cvalue().replace('"seq":3','"seq":9223372036854775807'));await a.tick();
   expect(a.api.root.querySelector('.ir-current-status').dataset.state==='unrepresentable','unsafe_current_state');
   expect(a.api.root.querySelector('.ir-current-results').textContent===a.cgood,'unsafe_current_lastgood');
  });
  await exercise('history_wrapper_boolean_and_extra_secret_fail_closed_without_DOM_echo',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};void a.api.refreshHistory();a.deferred.history[13].resolve({...a.hvalue(),read_allowed:'false'});await a.tick();
   expect(a.api.root.querySelector('.ir-current-read').disabled,'coerced_allowed');void a.api.refreshHistory();
   a.deferred.history[14].resolve({...a.hvalue(),secret:'SYNTHETIC-MUST-NOT-PUBLISH'});await a.tick();
   expect(a.api.root.querySelector('.ir-history-status').dataset.state==='error','wrapper_extra');
   expect(!a.api.root.textContent.includes('SYNTHETIC-MUST-NOT-PUBLISH'),'secret_echo');
  });
  await exercise('none_stale_unavailable_are_business_states_with_historical_head',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};void a.api.refreshHistory();const empty=structuredClone(a.f.history);
   Object.assign(empty,{available:false,records:[],next_before_seq:null});empty.verification.record_metadata_verified=false;
   a.deferred.history[15].resolve({raw_json:JSON.stringify(empty),read_allowed:true});await a.tick();
   expect(!a.api.root.querySelector('.ir-current-read').disabled,'history_absence_disabled_fresh_current');
   for(const [i,status] of ['none','stale','unavailable'].entries()){
    a.api.root.querySelector('.ir-current-read').click();const value=structuredClone(a.f.current);value.status=status;
    if(status==='none'){value.available=false;value.record=null;value.reference_summary=null;value.current_observation.head_record_id=null;value.verification.record_hash_verified=false;value.reason_codes=['no_reference_head'];}
    else{value.current_observation.snapshot_id=status==='unavailable'?null:'f'.repeat(64);value.reason_codes=[status==='unavailable'?'current_capture_unavailable':'reference_snapshot_stale'];}
    a.deferred.current[5+i].resolve(JSON.stringify(value));await a.tick();expect(a.api.root.querySelector('.ir-current-status').dataset.state===status,'business_status');
    if(status!=='none')expect(a.api.root.querySelector('.ir-current-results').textContent.includes('이전 등록'),'historical_head');
   }
  });
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:path.join(evidence,'a1-unavailable-390.png'),fullPage:true});
  await exercise('invalid_active_context_aborts_both_and_drops_late_current_before_parser',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.api.root.querySelector('.ir-current-read').click();void a.api.refreshHistory();
   a.api.setContext({invalid:true});a.api.setPending(false);expect(a.calls.history[16].signal.aborted&&a.calls.current[8].signal.aborted,'invalid_active_abort');
   const encodes=a.encodeCalls;a.deferred.history[16].resolve(a.poison());a.deferred.current[8].resolve(a.cvalue());await a.tick();
   expect(a.calls.history.length===17&&a.calls.current.length===9&&a.encodeCalls===encodes,'invalid_active_revived_or_parsed');
   a.api.setContext({...a.f.context,snapshotGeneration:9});a.deferred.history[17].resolve(a.hvalue());await a.tick();
  });
  await exercise('destroy_is_terminal_idempotent_and_drops_late_data_and_errors',async()=>{
   const a=window.a1,expect=(v,m)=>{if(!v)throw Error(m);};a.api.root.querySelector('.ir-current-read').click();void a.api.refreshHistory();
   const h=a.calls.history.length,c=a.calls.current.length;a.api.destroy();a.api.destroy();a.api.setContext(a.f.context);a.api.setPending(false);await a.api.refreshHistory();
   expect(a.calls.history.length===h&&a.calls.current.length===c,'destroy_called');expect(!a.api.root.isConnected,'destroy_root');
   expect(a.calls.history[18].signal.aborted&&a.calls.current[9].signal.aborted,'destroy_abort');
   a.deferred.history[18].resolve(a.poison());const error={get message(){a.poisonReads++;return 'LATE ERROR';}};a.deferred.current[9].reject(error);await a.tick();expect(a.poisonReads===0,'destroy_parsed');
  });
  const final=await page.evaluate(()=>({storage:[localStorage.length,sessionStorage.length],links:[...document.querySelectorAll('a[download]')].length,
   calls:{history:window.a1.calls.history.length,current:window.a1.calls.current.length},poison_reads:window.a1.poisonReads}));
  assert.deepEqual(final.storage,[0,0]);assert.equal(final.links,0);assert.equal(final.poison_reads,0);write('observations.json',final);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);checks.push('storage_download_external_requests_JS_errors_zero');
 }catch(error){failure=error;write('failure.json',{message:String(error.stack||error)});if(page)try{await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true});}catch{}}
 finally{
  try{if(browser)await browser.close();result.browser_closed=true;}catch(error){failure||=error;}
  try{if(server){server.closeAllConnections();await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));}result.server_closed=true;}catch(error){failure||=error;}
  try{const after=snapshot();write('source-pins-after.json',after);result.source_unchanged=JSON.stringify(after)===JSON.stringify(before);
   result.source_snapshots={before:hash(fs.readFileSync(path.join(evidence,'source-pins-before.json'))),after:hash(fs.readFileSync(path.join(evidence,'source-pins-after.json')))};
   if(!result.source_unchanged)failure||=Error('source_changed');}catch(error){failure||=error;}
  result.javascript_errors=errors.length;result.external_requests=external.length;
  result.status=!failure&&result.browser_closed&&result.server_closed&&result.source_unchanged?'pass':'fail';write('result.json',result);
 }
 console.log(JSON.stringify({phase:result.phase,status:result.status,checks:checks.length,evidence:path.relative(root,evidence).split(path.sep).join('/'),result_sha256:hash(fs.readFileSync(path.join(evidence,'result.json')))}));
 if(failure)throw Error('intake_reference_A1_failed');return result;
}
/*050 F1 loads product app/index/styles; API bytes below are explicit browser wire fixtures.
  This static server provides no session, Store, provider or product reference API. */
async function frontendMain(){
 const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
 const {createHash}=require('node:crypto'),{execFileSync}=require('node:child_process');
 const root=fs.realpathSync(path.resolve(__dirname,'../..')),hash=bytes=>createHash('sha256').update(bytes).digest('hex');
 fs.mkdirSync(path.join(root,'.local'),{recursive:true});
 const evidence=fs.mkdtempSync(path.join(root,'.local/ir-f1-'));
 const save=(name,value)=>fs.writeFileSync(path.join(evidence,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 const sourcePins=()=>{
  const names=execFileSync('git',['ls-files','-z','--','labflow','frontend'],{cwd:root}).toString('utf8').split('\0');
  names.push('frontend/intake_references/transport.mjs','frontend/intake_references/transport.test.mjs','docs/fcc/intake_reference_ui_usage.md');
  return Object.fromEntries([...new Set(names)].filter(Boolean).sort().map(name=>[name,hash(fs.readFileSync(path.join(root,name)))]));
 };
 const before=sourcePins(),checks=[],errors=[],external=[];save('source-pins-before.json',before);
 const result={phase:'050 F1 product frontend / explicit browser wire fixtures',checks,status:'fail',
  genuine049_HTTP_executed:false,Store_042_043_executed:false,original_source_reads:0,
  backend_full_regression_executed:false,model_hardware_executed:false,
  browser_closed:false,server_closed:false,source_unchanged:false};
 let browser,server,page,failure;
 try{
  const files={'/':['index.html','text/html'],'/app.js':['app.js','text/javascript'],'/model.mjs':['model.mjs','text/javascript'],
   '/intake_flow_model.mjs':['intake_flow_model.mjs','text/javascript'],'/styles.css':['styles.css','text/css'],
   '/virtual_fleet/harness_model.mjs':['virtual_fleet/harness_model.mjs','text/javascript'],
   '/intake-references/model.mjs':['intake_references/model.mjs','text/javascript'],
   '/intake-references/view.mjs':['intake_references/view.mjs','text/javascript'],
   '/intake-references/transport.mjs':['intake_references/transport.mjs','text/javascript']};
  server=http.createServer((req,res)=>{
   res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
   res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
   const file=Object.hasOwn(files,req.url)&&files[req.url];
   if(req.method!=='GET'||!file){res.writeHead(404);return res.end();}
   res.setHeader('Content-Type',file[1]+'; charset=utf-8');res.end(fs.readFileSync(path.join(root,'frontend',file[0])));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
  browser=await require('playwright').chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const bundle=createSyntheticBundle();
  const analysis={facts:{market:{value:'US',status:'explicit'}},questions:[{key:'firmware',field:'firmware',message:'합성 펌웨어 확인'}],
   next_action:'needs_information',submitted:{producer:{kind:'fixture',name:'050 wire fixture'},facts:[{field:'market',value:'US',status:'explicit',
    evidence:[{path:'synthetic/request.txt',sha256:'a'.repeat(64),line_start:1,line_end:1,quote:'Synthetic US',role:'request'}]}]},unread_documents:[]};
  const intake=(id,bundleName)=>({intake_id:id,source_id:'SYNTHETIC-SOURCE-050',bundle:bundleName,revision:2,status:'analyzed',synthetic:true,
   deferred:false,delegated:false,measurement_support:'unverified',analysis:copy(analysis),files:[],
   history:[{revision:2,created_at:1792756800,files:[],synthetic:1}],
   jobs:[{job_id:'SYNTHETIC-JOB-050',revision:2,state:'completed',attempt:1,error_code:null,lease_until:null}]});
  const first=bundle.context.intake_id,second='SYNTHETIC-INTAKE-050-B'.padEnd(150,'X');
  const snapshot={schema_version:1,generated_at:'2026-10-24T01:02:03Z',intakes:[intake(first,'050 합성 접수 A'),intake(second,'050 합성 접수 B')],
   notifications:[{notification_id:1,intake_id:first,revision:2,payload:copy(analysis)}]};
  save('synthetic-input.json',{kind:'explicit frontend wire fixtures; not 049',snapshot,bundle});
  await context.addInitScript(({snapshot,bundle})=>{
   const native=window.fetch.bind(window),clone=value=>structuredClone(value),counts={main:0,history:0,current:0,fixture:0};
   const queues={main:[],history:[],current:[]},held=new Map(),observations=[];
   let mainSnapshot=clone(snapshot);const token='f'.repeat(64);
   const headers={'Content-Type':'application/json; charset=utf-8'};
   const response=(kind,id,mode)=>{
    if(mode==='unconfigured')return new Response('{"error":{"code":"intake_reference_ui_unconfigured"}}',{status:503,headers});
    if(mode==='expired')return new Response('{"error":{"code":"intake_reference_ui_access_denied"}}',{status:403,headers});
    if(kind==='main')return new Response(JSON.stringify(mainSnapshot),{headers});
    if(kind==='fixture')return new Response(JSON.stringify({schema_version:1,intake_id:id,storage_available:false,records:[]}),{headers});
    let data=clone(kind==='history'?bundle.history:bundle.current);data.intake_id=id;
    let raw=JSON.stringify(data);if(mode==='unsafe')raw=raw.replace('"seq":3','"seq":9007199254740993');
    if(mode==='bad_utf8')raw=new Uint8Array([0xc3,0x28]);if(mode==='bom')raw=new Uint8Array([239,187,191,123,125]);
    const extra=kind==='history'?{'X-Intake-Reference-Read-Allowed':mode==='denied'?'false':'true',
     ...(mode==='denied'||mode==='missing_csrf'?{}:{'X-Intake-Reference-CSRF':token})}:{};
    return new Response(raw,{headers:{...headers,...extra}});
   };
   window.f1Wire={counts,observations,setSnapshot(value){mainSnapshot=clone(value);},next(kind,mode){queues[kind].push({mode});},
    hold(kind,label){queues[kind].push({label});},release(label,mode='ok'){const item=held.get(label);if(!item)throw Error('fixture_hold_missing');
     held.delete(label);item.resolve(response(item.kind,item.id,mode));},held(label){return held.has(label);}};
   window.fetch=(url,options={})=>{
    const u=new URL(url,location.origin);if(!u.pathname.startsWith('/api/'))return native(url,options);
    let kind,id='';
    if(u.pathname==='/api/intakes')kind='main';
    else if(/^\/api\/intake-references\/[^/]+\/history$/.test(u.pathname)){kind='history';id=u.pathname.split('/')[3];}
    else if(/^\/api\/intake-references\/[^/]+\/current$/.test(u.pathname)){kind='current';id=u.pathname.split('/')[3];}
    else if(u.pathname.endsWith('/fixture-runs')){kind='fixture';id=u.pathname.split('/')[3];}
    else return Promise.resolve(new Response('{}',{status:404,headers}));
    counts[kind]++;const item={kind,aborted:!!options.signal?.aborted,pending_before_fetch:document.querySelector('.intake-reference-review')?.dataset.pending,
     current_disabled:document.querySelector('.ir-current-read')?.disabled};
    if(kind==='current'){const body=JSON.parse(options.body);item.body_exact2=Object.keys(body).length===2&&body.schema_version===1&&body.action==='current';
     item.csrf_header_present=typeof options.headers?.['X-Intake-Reference-CSRF']==='string';}
    observations.push(item);options.signal?.addEventListener('abort',()=>{item.aborted=true;},{once:true});
    const next=queues[kind]?.shift();if(next?.label)return new Promise(resolve=>held.set(next.label,{resolve,kind,id}));
    return Promise.resolve(response(kind,id,next?.mode||'ok'));
   };
  },{snapshot,bundle});
  context.on('page',p=>{p.on('pageerror',()=>errors.push('pageerror'));p.on('request',r=>{if(!r.url().startsWith(origin+'/'))external.push('external');});});
  page=await context.newPage();page.setDefaultTimeout(10000);await page.goto(origin);
  const state=selector=>page.locator(selector).getAttribute('data-state');
  const ready=()=>page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');
  const counts=()=>page.evaluate(()=>({...window.f1Wire.counts}));
  const mode=(kind,value)=>page.evaluate(({kind,value})=>window.f1Wire.next(kind,value),{kind,value});
  const hold=(kind,label)=>page.evaluate(({kind,label})=>window.f1Wire.hold(kind,label),{kind,label});
  const release=(label,value='ok')=>page.evaluate(({label,value})=>window.f1Wire.release(label,value),{label,value});
  const held=label=>page.waitForFunction(label=>window.f1Wire.held(label),label);
  const dispatchRefresh=()=>page.evaluate(()=>document.querySelector('#refresh').dispatchEvent(new Event('click')));
  await page.locator('#intake-reference-panel .intake-reference-review').waitFor();await ready();
  assert.equal(await page.locator('#detail-panel .intake-reference-review').count(),0);
  assert.equal(await page.locator('#intake-reference-panel').evaluate(n=>n.previousElementSibling.id==='intake-view'&&n.nextElementSibling.id==='notification-view'),true);
  assert.equal((await counts()).history,1);assert.equal((await counts()).current,0);checks.push('product_mount_sibling_context_history1_current0');
  const beforeFilter=await counts();await page.locator('#search').fill('050');await page.locator('#filter').selectOption('attention');
  assert.equal((await counts()).history,beforeFilter.history);checks.push('filter_same_context_no_extra_history');
  await page.locator('#search').focus();await page.locator('.ir-history-refresh').evaluate(button=>button.click());await ready();
  assert.equal(await page.locator('#search').evaluate(n=>n===document.activeElement),true);checks.push('automatic_history_preserves_outside_focus');
  await hold('current','keyboard-current');await page.locator('.ir-current-read').focus();await page.keyboard.press('Enter');
  await held('keyboard-current');await page.locator('#search').focus();await release('keyboard-current');
  await page.waitForFunction(()=>document.querySelector('.ir-current-status').dataset.state==='current');
  assert.equal((await counts()).current,1);assert.match(await page.locator('.ir-current-results').innerText(),/KST/);
  assert.equal(await page.locator('#search').evaluate(n=>n===document.activeElement),true);checks.push('explicit_current_keyboard_exact_body_header_KST_no_focus_theft');
  for(const bad of ['missing_csrf','bad_utf8','bom']){await mode('history',bad);await page.locator('.ir-history-refresh').click();
   await page.waitForFunction(()=>document.querySelector('.ir-history-status').dataset.state==='error');
   assert.equal(await page.locator('.ir-current-read').isDisabled(),true);assert.equal(await page.locator('.ir-history-results').getAttribute('data-stale'),'true');
   await page.locator('.ir-history-refresh').click();await ready();}
  checks.push('bad_headers_UTF8_BOM_preserve_lastgood_and_fail_closed');
  await mode('history','unsafe');await page.locator('.ir-history-refresh').click();
  await page.waitForFunction(()=>document.querySelector('.ir-history-status').dataset.state==='unrepresentable');
  assert.equal(await page.locator('.ir-history-previous').isDisabled(),true);await page.locator('.ir-history-refresh').click();await ready();
  checks.push('unsafe_integer_limit_keeps_lastgood_without_rounding');
  await mode('current','expired');await page.locator('.ir-current-read').click();
  await page.waitForFunction(()=>document.querySelector('.ir-current-status').dataset.state==='error');
  const expiredCount=(await counts()).current;assert.equal(await page.locator('.ir-current-results').getAttribute('data-stale'),'true');
  assert.match(await page.locator('#intake-reference-panel').innerText(),/이력을 새로 조회/);
  await page.locator('.ir-history-refresh').click();await ready();assert.equal((await counts()).current,expiredCount);
  await page.locator('.ir-current-read').click();await page.waitForFunction(()=>document.querySelector('.ir-current-status').dataset.state==='current');
  checks.push('expired_session_fixed_guide_metadata_requery_no_auto_current_retry');
  await mode('history','denied');await page.locator('.ir-history-refresh').click();await ready();
  assert.equal(await page.locator('.ir-current-read').isDisabled(),true);assert.equal(await page.locator('#detail-title').isVisible(),true);
  await mode('history','unconfigured');await page.locator('.ir-history-refresh').click();
  await page.waitForFunction(()=>document.querySelector('.ir-history-status').dataset.state==='error');
  assert.equal(await page.locator('#detail-title').isVisible(),true);assert.equal((await counts()).current,expiredCount+1);
  await page.locator('.ir-history-refresh').click();await ready();checks.push('none_assets_and_permission_false_keep_intake_UI_source0');
  const selectionCounts=await counts();await page.locator('.intake-item').nth(1).click();await ready();
  assert.match(await page.locator('.ir-selection').innerText(),/SYNTHETIC-INTAKE-050-B/);
  assert.equal((await counts()).history,selectionCounts.history+1);assert.equal((await counts()).current,selectionCounts.current);
  assert.equal(await page.locator('.ir-current-results').isVisible(),false);checks.push('new_selection_history1_current0_hides_other_intake_good');
  await page.locator('[data-view="notifications"]').click();assert.equal(await page.locator('#intake-reference-panel').isVisible(),false);
  await page.locator('[data-view="intakes"]').click();assert.equal(await page.locator('#intake-reference-panel').isVisible(),true);
  assert.equal((await counts()).current,selectionCounts.current);checks.push('navigation_only_toggles_sibling_visibility');
  const lastTitle=await page.locator('#detail-title').innerText();const invalid=copy(snapshot);invalid.intakes[0].intake_id='../invalid-context';
  invalid.intakes[1].intake_id='../also-invalid-context';await page.evaluate(value=>window.f1Wire.setSnapshot(value),invalid);
  const beforeBad=await counts();await page.locator('#refresh').click();await page.locator('#error-banner').waitFor();
  assert.equal(await page.locator('#detail-title').innerText(),lastTitle);assert.equal((await counts()).history,beforeBad.history);
  await page.evaluate(value=>window.f1Wire.setSnapshot(value),snapshot);await page.locator('#refresh').click();await ready();
  checks.push('prepare_context_before_DOM_publish_rejects_invalid_snapshot_preserving_good');
  await hold('current','old-current');await page.locator('.ir-current-read').click();await held('old-current');
  await hold('history','old-history');await page.locator('.ir-history-refresh').click();await held('old-history');
  await hold('main','main-older');await dispatchRefresh();await held('main-older');
  const observed=await page.evaluate(()=>window.f1Wire.observations);
  assert.equal(observed.filter(x=>x.kind==='current').at(-1).aborted,true);assert.equal(observed.filter(x=>x.kind==='history').at(-1).aborted,true);
  assert.equal(observed.filter(x=>x.kind==='main').at(-1).pending_before_fetch,'true');
  assert.equal(observed.filter(x=>x.kind==='main').at(-1).current_disabled,true);checks.push('main_refresh_before_fetch_cancels_both_channels');
  await hold('main','main-newer');await dispatchRefresh();await held('main-newer');await release('main-older');
  await page.waitForFunction(()=>!window.f1Wire.held('main-older'));
  assert.equal(await page.locator('.intake-reference-review').getAttribute('data-pending'),'true');assert.equal(await page.locator('#refresh').isDisabled(),true);
  await release('main-newer');await ready();await release('old-current');await release('old-history');
  assert.equal(await state('.ir-current-status'),'idle');checks.push('latest_finally_only_and_late_channels_cannot_publish');
  await hold('main','queued-selection');await dispatchRefresh();await held('queued-selection');
  const queued=await counts();await page.locator('.intake-item').first().click();await page.locator('.intake-item').nth(1).click();
  assert.equal((await counts()).history,queued.history);await release('queued-selection');await ready();
  assert.equal((await counts()).history,queued.history+1);assert.equal((await counts()).current,queued.current);
  checks.push('pending_keeps_latest_selection_and_resumes_metadata_once');
  const bfcache=await counts();await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true})));
  assert.equal(await page.locator('.intake-reference-review').getAttribute('data-pending'),'true');
  await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));await ready();
  assert.equal((await counts()).history,bfcache.history+1);assert.equal((await counts()).current,bfcache.current);checks.push('BFcache_reentry_refreshes_metadata_without_current');
  await hold('main','hidden-main');await dispatchRefresh();await held('hidden-main');const hidden=await counts();
  await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true})));await release('hidden-main');
  await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
  assert.equal(await page.locator('.intake-reference-review').getAttribute('data-pending'),'true');assert.equal((await counts()).history,hidden.history);
  await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));await ready();
  assert.equal((await counts()).history,hidden.history+1);assert.equal((await counts()).current,hidden.current);
  checks.push('main_finally_cannot_resume_reference_while_BFcache_suspended');
  for(const width of [1440,390]){await page.setViewportSize({width,height:width===390?844:1000});
   await page.locator('.intake-reference-review').scrollIntoViewIfNeeded();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   assert.equal(await page.locator('.ir-history-results').evaluate(n=>getComputedStyle(n.closest('.intake-reference-review')).gridTemplateColumns.split(' ').length),width===390?1:2);
   await page.screenshot({path:path.join(evidence,`frontend-${width}.png`),fullPage:true});
   await page.locator('.intake-reference-review').evaluate(n=>n.scrollIntoView({block:'start'}));
   await page.screenshot({path:path.join(evidence,`frontend-${width}-panel.png`)});}
  checks.push('product_CSS_long_ID_KST_wrap_390_and1440_two_to_one_columns');
  const clean=await page.evaluate(()=>({storage:[localStorage.length,sessionStorage.length],downloads:document.querySelectorAll('a[download]').length,
   token_visible:/f{64}/.test(document.body.innerText),token_url:/f{64}/.test(location.href),observations:window.f1Wire.observations,counts:{...window.f1Wire.counts}}));
  assert.deepEqual(clean.storage,[0,0]);assert.equal(clean.downloads,0);assert.equal(clean.token_visible,false);assert.equal(clean.token_url,false);
  assert.ok(clean.observations.filter(x=>x.kind==='current').every(x=>x.body_exact2&&x.csrf_header_present));save('observations.json',clean);
  const terminal=await counts();await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide',{persisted:false})));
  assert.equal(await page.locator('.intake-reference-review').count(),0);await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
  assert.deepEqual(await counts(),terminal);checks.push('nonpersisted_pagehide_terminal_no_resurrection');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);checks.push('no_secret_storage_download_external_or_Javascript_errors');
 }catch(error){failure=error;save('failure.json',{message:String(error.stack||error)});if(page)try{await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true});}catch{}}
 finally{
  try{if(browser)await browser.close();result.browser_closed=true;}catch(error){failure||=error;}
  try{if(server){server.closeAllConnections();await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));}result.server_closed=true;}catch(error){failure||=error;}
  try{const after=sourcePins();save('source-pins-after.json',after);result.source_unchanged=JSON.stringify(before)===JSON.stringify(after);
   if(!result.source_unchanged)failure||=Error('source_changed');}catch(error){failure||=error;}
  result.javascript_errors=errors.length;result.external_requests=external.length;
  result.status=!failure&&result.browser_closed&&result.server_closed&&result.source_unchanged?'pass':'fail';save('result.json',result);
 }
 console.log(JSON.stringify({phase:result.phase,status:result.status,checks:checks.length,evidence:path.relative(root,evidence).split(path.sep).join('/'),
  result_sha256:hash(fs.readFileSync(path.join(evidence,'result.json')))}));
 if(failure)throw Error('intake_reference_frontend_F1_failed');return result;
}
module.exports={createSyntheticBundle,main};
if(require.main===module)main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
