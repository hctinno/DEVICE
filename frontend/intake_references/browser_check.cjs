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
 if(argv.length===2&&argv[0]==='--mode'&&argv[1]==='integrated')return integratedMain();
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
const INTEGRATED_SUPERVISOR=String.raw`"""050 F2 acceptance only: public synthetic preparation, genuine049, no HTTP shim."""
import hashlib,json,os,re,socket,sqlite3,sys,threading,time,types
from pathlib import Path

ROOT=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
tests=types.ModuleType('tests');tests.__path__=[str(ROOT/'tests')];sys.modules['tests']=tests
assert 'sitecustomize' not in sys.modules

def emit(value):
    print(json.dumps(value,separators=(',',':')),flush=True)

def fingerprint(folder):
    files={}
    for p in sorted(folder.rglob('*')):
        if p.is_file():
            b=p.read_bytes();s=p.stat();files[p.relative_to(folder).as_posix()]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'identity':[s.st_dev,s.st_ino,s.st_mtime_ns,s.st_mode]}
    return files

def database(folder):
    con=sqlite3.connect((folder/'state/lab.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        dump='\n'.join(con.iterdump()).encode('utf-8')
        tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts={n:con.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in tables}
        return {'dump_sha256':hashlib.sha256(dump).hexdigest(),'table_counts':counts}
    finally:con.close()

def prepare(folder):
    from tests.test_ui_server import ReferenceFixture
    from tests.test_intake_case_references import catalog_fixture,context_for,response_for
    from labflow.intake_reference_review import prepare_reference_review,append_reference_review
    assert not folder.exists();folder.mkdir()
    f=ReferenceFixture(folder,registered=False)
    try:
        catalog=catalog_fixture();context=context_for(catalog);response=response_for(context)
        prepared,preview=prepare_reference_review(f.legacy,catalog,f.intake_id,case_context=context,validated_response=response,
            producer_name=response['expected_producer']['name'],allow_retained_reads=True)
        request={'schema_version':1,'intake_id':f.intake_id,'request_id':'SYNTHETIC-F2-REFERENCE',
            'preparation_id':preview['preparation_id'],'expected_snapshot_id':preview['observation']['snapshot_id'],'expected_head_record_id':None}
        registration=append_reference_review(f.legacy,catalog,prepared,request,allow_retained_reads=True,allow_append=True)
        assert registration['stored'] is True
        with f.legacy.connection() as con:
            submission=json.loads(con.execute("SELECT result_json FROM intake_jobs WHERE state='completed'").fetchone()[0])['submission']
        context_id=submission['context_id'];intake_context=json.loads(f.legacy.blob_path(context_id).read_bytes())
        categories={str(f.legacy.blob_path(context_id)):'context'}
        for d in intake_context['documents']:
            categories[str(f.legacy.blob_path(d['sha256']))]='pdf'
            if d.get('extraction_id'):categories[str(f.legacy.blob_path(d['extraction_id']))]='extraction'
        meta={'intake_id':f.intake_id,'record_id':registration['record_id'],'seq':registration['seq'],
              'case_ids':context['selection']['requested_case_ids'] if 'selection' in context else ['CASE-A'],
              'preparation_ready':preview['preparation_ready'],'categories':categories,
              'P0':{'public042_prepare':1,'public042_append':1,'public025_context_response':1,'synthetic_intake_PDF':1}}
    finally:f.legacy.close()
    meta['database']=database(folder);meta['files']=fingerprint(folder)
    assert all(meta['database']['table_counts'][n]==1 for n in ['intake_reference_records','intake_reference_events','intake_reference_heads'])
    (folder.parent/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    emit({'prepared':True,'intake_id':meta['intake_id'],'record_id':meta['record_id'],'seq':meta['seq'],'P0':meta['P0'],'files':len(meta['files'])})

def serve(folder,mode):
    from labflow.ui_server import create_server
    from labflow.store import Store
    meta=json.loads((folder.parent/'fixture.json').read_text(encoding='utf-8'))
    stats={};phase='startup';live_connections=set();totals={'SQLite_opened':0,'SQLite_closed':0}
    entered=threading.Event();release=threading.Event();close_done=threading.Event();close_started=threading.Event()
    state={'armed':False,'close_error':False,'gate_timed_out':False};codes={};store=None;server=None;loop=None;closer=None;monitor={'enabled':True}
    def count(key,amount=1):
        bucket=stats.setdefault(phase,{});bucket[key]=bucket.get(key,0)+amount
    def audit(event,args):
        if not monitor['enabled']:return
        if event=='open' and args and type(args[0]) is str:
            category=meta['categories'].get(str(Path(args[0]).absolute()))
            if category:count('retained_open_'+category)
        elif event=='sqlite3.connect/handle':
            live_connections.add(id(args[0]));totals['SQLite_opened']+=1
        elif event=='subprocess.Popen':count('subprocess_start')
    def profile(frame,event,arg):
        code=frame.f_code
        label=codes.get(code)
        if label and event=='call':
            if label=='parent042':
                action=frame.f_locals.get('request',{}).get('action','invalid');count('parent_'+action+'_started')
                if action=='current' and state['armed']:
                    state['armed']=False;entered.set()
                    if not release.wait(15):state['gate_timed_out']=True
            else:count(label)
        elif label=='parent042' and event=='return':
            action=frame.f_locals.get('request',{}).get('action','invalid');count('parent_'+action+'_returned')
            if type(arg) is dict:count('parent_'+action+'_normal')
        if event=='return' and code.co_name=='read_bytes' and type(arg) is bytes:
            p=frame.f_locals.get('self');category=meta['categories'].get(str(p))
            if category:count('retained_bytes_'+category,len(arg))
        if event=='return' and label=='snapshot_blob' and type(arg) is tuple and type(arg[0]) is bytes:
            category=meta['categories'].get(str(frame.f_locals.get('path')))
            if category:count('bounded_blob_bytes_'+category,len(arg[0]))
        if event=='c_return' and getattr(arg,'__name__',None)=='close' and isinstance(getattr(arg,'__self__',None),sqlite3.Connection):
            ident=id(arg.__self__)
            if ident in live_connections:live_connections.remove(ident);totals['SQLite_closed']+=1
        if event=='call' and code.co_filename==str(ROOT/'labflow/store.py'):
            if code.co_qualname=='Store.__init__':count('Store_constructor')
            if code.co_qualname=='Store.open_existing':count('Store_open_existing')
        if event=='call' and code.co_filename==str(ROOT/'labflow/document_extract.py') and code.co_name=='extract_document':count('document_reparse')
        return profile
    sys.addaudithook(audit);sys.setprofile(profile);threading.setprofile(profile)
    try:
        if mode=='none':
            assert 'labflow.intake_reference_review' not in sys.modules
            # Exercise040's catalog-only path without a Store/reference runtime.
            from tests.test_intake_case_references import catalog_fixture
            lazy=create_server(folder/'state',port=0,fcc_case_catalog=catalog_fixture());lazy_port=lazy.server_port;lazy.server_close()
            probe=socket.socket();probe.bind(('127.0.0.1',lazy_port));probe.close()
            assert 'labflow.intake_reference_review' not in sys.modules
            server=create_server(folder/'state',port=0)
        else:
            import labflow.intake_reference_review as review
            import labflow.intake_reference_ledger as ledger
            import labflow.intake_reference_snapshot as snapshot
            unwrap=lambda f:getattr(f,'__wrapped__',f).__code__
            codes.update({unwrap(review.read_reference_review):'parent042',unwrap(ledger.reference_history):'ledger_history',
                          unwrap(ledger.current_reference):'ledger_current',unwrap(snapshot.capture_intake_reference_snapshot_in_transaction):'capture034',
                          snapshot._blob.__code__:'snapshot_blob'})
            store=Store.open_existing(str(folder/'state'))
            server=create_server(store.root,port=0,intake_reference_store=store,intake_reference_read_scope=() if mode=='deny' else 'workspace')
        assert server.server_port not in (8765,8766)
        loop=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},name='F2-real049-loop');loop.start()
        phase=mode
        emit({'ready':True,'port':server.server_port,'mode':mode,'reference_module_loaded':'labflow.intake_reference_review' in sys.modules,
              'startup':stats.get('startup',{}),'startup_SQLite':dict(totals),'catalog_only_040_closed_port_rebound':mode=='none',
              'formal_server':type(server).__module__=='labflow.ui_server' or mode=='none'})
        def close():
            close_started.set()
            try:
                if mode=='none':server.shutdown()
                server.server_close()
            except BaseException:state['close_error']=True
            finally:close_done.set()
        def report():
            return {'stats':stats,'SQLite':totals,'SQLite_live':len(live_connections),'entered':entered.is_set(),
                    'close_started':close_started.is_set(),'close_done':close_done.is_set(),'gate_timed_out':state['gate_timed_out'],
                    'reference_module_loaded':'labflow.intake_reference_review' in sys.modules}
        for line in sys.stdin:
            command=json.loads(line);op=command['op']
            if op=='report':emit(report())
            elif op=='arm':phase='lifecycle';state['armed']=True;emit({'armed':True})
            elif op=='expire':
                phase='session_expiry_fault';clock=server._reference_runtime.clock
                server._reference_runtime.clock=lambda:clock()+901
                emit({'clock_advanced_for_expiry':True})
            elif op=='restart_phase':phase='anonymous_restart';emit({'restart_phase':True})
            elif op=='wait':emit({'entered':entered.wait(8)})
            elif op=='begin_close':
                closer=threading.Thread(target=close,name='F2-caller-close');closer.start();assert close_started.wait(2);time.sleep(.1);emit(report())
            elif op=='release':release.set();emit({'released':True})
            elif op=='finish':
                release.set()
                if closer is None:closer=threading.Thread(target=close,name='F2-caller-close');closer.start()
                assert close_done.wait(12) and not state['close_error'];closer.join(2);loop.join(2);assert not loop.is_alive()
                phase='after_HTTP';monitor['enabled']=False;sys.setprofile(None);threading.setprofile(None)
                borrowed_usable=False;blocked=0;targets=[folder,folder/'state',folder/'state/blobs',folder/'state/lab.sqlite3']
                def move_roundtrip(p):
                    bound=folder.parent.resolve();a=p.resolve();b=p.with_name(p.name+'.native-move').resolve()
                    assert a.is_relative_to(bound) and b.is_relative_to(bound) and not b.exists()
                    p.rename(b);b.rename(p)
                if store:
                    with store.connection() as con:borrowed_usable=con.execute('SELECT count(*) FROM intakes').fetchone()[0]==1
                    for p in targets:
                        try:move_roundtrip(p)
                        except OSError:blocked+=1
                    assert blocked==4;store.close();store=None
                released=0
                for p in reversed(targets):move_roundtrip(p);released+=1
                after_db=database(folder);after_files=fingerprint(folder)
                assert after_db==meta['database'] and after_files==meta['files']
                probe=socket.socket();probe.bind(('127.0.0.1',server.server_port));probe.close()
                final=report();final.update({'closed':True,'loop_closed':True,'borrowed_store_usable_after_host':borrowed_usable,
                    'native_blocked':blocked,'native_released':released,'inputs_unchanged':True,'port_rebound':True,'mode':mode})
                emit(final);return
            else:raise AssertionError('unknown_supervisor_command')
    finally:
        release.set()
        if server is not None:
            try:server.server_close()
            except BaseException:pass
        if loop:loop.join(3)
        if store:store.close()
        sys.setprofile(None);threading.setprofile(None)

if __name__=='__main__':
    try:
        assert len(sys.argv) in (4,5)
        folder=Path(sys.argv[3]).resolve();assert folder.is_relative_to(ROOT/'.local')
        if sys.argv[2]=='prepare':prepare(folder)
        elif sys.argv[2]=='serve':serve(folder,sys.argv[4])
        else:raise AssertionError('invalid_supervisor_mode')
    except BaseException as error:
        frames=[];tb=error.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_filename==__file__:frames.append(tb.tb_lineno)
            tb=tb.tb_next
        emit({'fatal':'integrated_supervisor_failed','type':type(error).__name__,'supervisor_lines':frames});sys.exit(1)
`;
/*050 F2 uses genuine049 in fresh Python children. No proxy, mock API or injected transport. */
async function integratedMain(){
 const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
 const {createHash}=require('node:crypto'),{spawn,execFileSync}=require('node:child_process');
 const root=fs.realpathSync(path.resolve(__dirname,'../..')),hash=b=>createHash('sha256').update(b).digest('hex');
 const local=path.join(root,'.local');fs.mkdirSync(local,{recursive:true});const evidence=fs.mkdtempSync(path.join(local,'ir-f2-'));
 const save=(n,v)=>fs.writeFileSync(path.join(evidence,n),JSON.stringify(v,null,2)+'\n',{flag:'wx'});
 const sourcePins=()=>Object.fromEntries(execFileSync('git',['ls-files','-z','--','labflow','frontend','tests'],{cwd:root}).toString('utf8').split('\0').filter(Boolean).sort().map(n=>[n,hash(fs.readFileSync(path.join(root,n)))]));
 const before=sourcePins(),checks=[],children=[],observations=[],errors=[],external=[],secrets=new Set();let browser,stage='initialization',failure;
 const result={phase:'050 F2 genuine049 / public043-042 / native product frontend',checks,status:'fail',
  P0_preparation_separate:true,phases:{},source_unchanged:false,browser_closed:false,children_closed:false,
  backend_full_Python_executed:false,customer_PDF_model_hardware_executed:false};
 result.retained_byte_observation_scope='snapshot._blob native returned bytes are a measured subset; audit counts all retained opens; total read bytes unknown';
 save('source-pins-before.json',before);const helper=path.join(evidence,'supervisor.py');fs.writeFileSync(helper,INTEGRATED_SUPERVISOR,{flag:'wx'});
 const python=path.join(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
 const env={...process.env,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};delete env.PYTHONPATH;delete env.PYTHONHOME;
 function launch(args){
  const child=spawn(python,['-X','utf8','-B',helper,root,...args],{cwd:root,env,windowsHide:true,stdio:['pipe','pipe','pipe']});
  const lines=[],waiters=[];let buffer='',stderrBytes=0,exitState=null;
  const finishWaiters=()=>{while(waiters.length){const w=waiters.shift();clearTimeout(w.timer);w.reject(Error('supervisor_closed'));}};
  const closed=new Promise(resolve=>child.on('close',(code,signal)=>{exitState={code,signal};finishWaiters();resolve(exitState);}));
  child.on('error',()=>finishWaiters());child.stderr.on('data',b=>{stderrBytes+=b.length;});
  child.stdout.on('data',b=>{buffer+=b.toString('utf8');while(buffer.includes('\n')){const end=buffer.indexOf('\n'),line=buffer.slice(0,end);buffer=buffer.slice(end+1);
   let value;try{value=JSON.parse(line);}catch{value={fatal:'invalid_supervisor_frame'};}
   if(waiters.length){const w=waiters.shift();clearTimeout(w.timer);w.resolve(value);}else lines.push(value);
  }});
  const next=(ms=20000)=>lines.length?Promise.resolve(lines.shift()):exitState?Promise.reject(Error('supervisor_closed')):new Promise((resolve,reject)=>{
   const w={resolve,reject,timer:setTimeout(()=>{const at=waiters.indexOf(w);if(at>=0)waiters.splice(at,1);reject(Error('supervisor_timeout'));},ms)};waiters.push(w);
  });
  const api={child,closed,next,ask:async op=>{child.stdin.write(JSON.stringify(op)+'\n');const value=await next();if(value.fatal){api.fatal=value;throw Error('supervisor_failed');}return value;},get stderrBytes(){return stderrBytes;},get exitState(){return exitState;}};
  children.push(api);return api;
 }
 const check=(name,fn)=>{stage=name;return Promise.resolve().then(fn).then(()=>checks.push(name));};
 const quiet=async page=>{
  await settle();for(const cookie of await page.context().cookies()){secrets.add(cookie.value);assert.equal(cookie.httpOnly,true);assert.equal(cookie.sameSite,'Strict');}
  const values=await page.evaluate(()=>({body:document.documentElement.outerHTML,local:Object.entries(localStorage),session:Object.entries(sessionStorage),downloads:document.querySelectorAll('a[download]').length}));
  assert.equal([...secrets].some(s=>s&&values.body.includes(s)),false,'private_value_in_DOM');assert.deepEqual(values.local,[]);assert.deepEqual(values.session,[]);assert.equal(values.downloads,0);
 };
 async function watch(page,origin,mode){
  page.on('pageerror',()=>errors.push(mode));page.on('download',()=>errors.push('unexpected_download'));
  page.on('request',request=>{if(!request.url().startsWith(origin+'/'))external.push(mode);});
  page.on('response',response=>{const url=new URL(response.url());if(!url.pathname.startsWith('/api/intake-references/'))return;
   const request=response.request();const record={phase:mode,kind:url.pathname.endsWith('/history')?'history':'current',method:request.method(),status:response.status()};
   observations.push(record);
   record.promise=(async()=>{
    const headers=await request.allHeaders();record.origin_valid=record.kind!=='current'||headers.origin===origin;
    record.csrf_shape=typeof headers['x-intake-reference-csrf']==='string'&&/^[a-f0-9]{64}$/.test(headers['x-intake-reference-csrf']);
    record.cookie_present=!!headers.cookie;
    if(record.kind==='current')record.exact_body2=JSON.stringify(request.postDataJSON())===JSON.stringify({schema_version:1,action:'current'});
    const token=await response.headerValue('x-intake-reference-csrf');if(token)secrets.add(token);
    record.response_csrf_shape=token!==null&&/^[a-f0-9]{64}$/.test(token);
    record.read_allowed=await response.headerValue('x-intake-reference-read-allowed');
   })().catch(()=>{record.observation_failed=true;});
  });
 }
 const settle=async()=>{await Promise.all(observations.map(o=>o.promise));};
 const ready=async page=>{await page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');};
 const stopped=async host=>{const final=await host.ask({op:'finish'});const exit=await host.closed;assert.deepEqual(exit,{code:0,signal:null});assert.equal(host.stderrBytes,0);assert.equal(final.closed,true);assert.equal(final.loop_closed,true);assert.equal(final.SQLite_live,0);assert.equal(final.SQLite.SQLite_opened,final.SQLite.SQLite_closed);assert.equal(final.inputs_unchanged,true);assert.equal(final.port_rebound,true);return final;};
 try{
  stage='P0_public_fixture';const folder=path.join(evidence,'workspace');const preparation=launch(['prepare',folder]);
  const prepared=await preparation.next();if(prepared.fatal){preparation.fatal=prepared;throw Error('fixture_failed');}
  assert.deepEqual(await preparation.closed,{code:0,signal:null});assert.equal(preparation.stderrBytes,0);assert.equal(prepared.prepared,true);
  result.P0=prepared;checks.push('public_P0_synthetic025_042_prepare_append_rows1_before_HTTP');
  browser=await require('playwright').chromium.launch({headless:true});
  for(const mode of ['none','deny','allow']){
   stage=mode+'_startup';const host=launch(['serve',folder,mode]),initial=await host.next();if(initial.fatal){host.fatal=initial;throw Error('host_start_failed');}
   assert.equal(initial.ready,true);const origin=`http://127.0.0.1:${initial.port}`;assert.equal(initial.startup.Store_constructor||0,0);
   assert.equal(initial.startup.Store_open_existing||0,mode==='none'?0:1);result.phases[mode]={startup:initial};
   const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();await watch(page,origin,mode);
   if(mode==='none')await check('real049_static3_GET_HEAD6_raw_and_GitLF_MIME_CSP',async()=>{
    const assets=[];
    for(const name of ['model','view','transport']){
     const route='/intake-references/'+name+'.mjs',file='frontend/intake_references/'+name+'.mjs';
     const response=await fetch(origin+route);assert.equal(response.status,200);const raw=Buffer.from(await response.arrayBuffer()),disk=fs.readFileSync(path.join(root,file));assert.equal(raw.equals(disk),true);
     assert.equal(response.headers.get('content-type'),'text/javascript; charset=utf-8');assert.equal(response.headers.get('cache-control'),'no-store');
     assert.equal(response.headers.get('content-security-policy').includes("script-src 'self'"),true);
     const canonical=execFileSync('git',['show','HEAD:'+file],{cwd:root});assert.equal(raw.toString('utf8').replace(/\r\n/g,'\n'),canonical.toString('utf8'));
     const head=await fetch(origin+route,{method:'HEAD'});assert.equal(head.status,200);assert.equal((await head.arrayBuffer()).byteLength,0);assert.equal(Number(head.headers.get('content-length')),raw.length);
     assets.push({name,GET:200,HEAD:200,raw_bytes:raw.length,raw_sha256:hash(raw),git_lf_bytes:canonical.length,git_lf_sha256:hash(canonical)});
    }result.static3=assets;
   });
   stage=mode+'_root_app';await page.goto(origin);await page.locator('#detail-title').waitFor();await page.locator('.intake-reference-review').waitFor();
   assert.equal(await page.locator('#intake-reference-panel').count(),1);assert.equal(await page.locator('#detail-panel #intake-reference-panel').count(),0);
   assert.equal(await page.locator('#intake-reference-actions-panel').count(),0);await quiet(page);
   if(mode==='none'){
    await page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='error');assert.equal(await page.locator('.ir-current-read').isDisabled(),true);
    const report=await host.ask({op:'report'});assert.equal(report.reference_module_loaded,false);assert.equal(report.stats.none?.parent_history_started||0,0);
    result.phases.none.final=await stopped(host);assert.equal(result.phases.none.final.reference_module_loaded,false);checks.push('None_and_040_catalog_lazy042_Store0_existing_intake_DOM');
    await context.close();continue;
   }
   await ready(page);
   await check(mode+'_first_history1_metadata_source0',async()=>{
    const report=await host.ask({op:'report'}),s=report.stats[mode];assert.equal(s.parent_history_started,1);assert.equal(s.parent_history_normal,1);assert.equal(s.ledger_history,1);
    assert.equal(s.parent_current_started||0,0);for(const kind of ['pdf','context','extraction'])assert.equal(s['retained_open_'+kind]||0,0);
    assert.equal(await page.locator('.ir-history-results').innerText().then(t=>t.includes(prepared.record_id)),true);result.phases[mode].first_history=report;
   });
   if(mode==='deny'){
    assert.equal(await page.locator('.ir-current-read').isDisabled(),true);
    const denied=await page.evaluate(async id=>{const r=await fetch(`/api/intake-references/${id}/current`,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify({schema_version:1,action:'current'})});return {status:r.status,code:(await r.json()).error.code};},prepared.intake_id);
    assert.deepEqual(denied,{status:403,code:'intake_reference_ui_access_denied'});const report=await host.ask({op:'report'});assert.equal(report.stats.deny.parent_current_started||0,0);
    await quiet(page);await context.close();result.phases.deny.final=await stopped(host);checks.push('default_scope_false_current_disabled_direct403_parent0');continue;
   }
   await check('native_same_origin_explicit_current1_real042_038_034_source_bytes_no_reparse',async()=>{
    assert.equal(await page.locator('.ir-current-read').isEnabled(),true);await page.locator('.ir-current-read').focus();await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('.ir-current-status')?.dataset.state==='current');const report=await host.ask({op:'report'}),s=report.stats.allow;
    assert.equal(s.parent_current_started,1);assert.equal(s.parent_current_normal,1);assert.equal(s.ledger_current,1);assert.ok(s.capture034>0);
    for(const kind of ['pdf','context','extraction']){assert.ok(s['retained_open_'+kind]>0);assert.ok((s['retained_bytes_'+kind]||0)+(s['bounded_blob_bytes_'+kind]||0)>0);}
    assert.equal(s.document_reparse||0,0);assert.equal(s.subprocess_start||0,0);result.phases.allow.normal=report;
   });
   await check('genuine_DOM_public_record_CASE_A_literals_raw_KST_and_external_focus_390_1440',async()=>{
    const text=await page.locator('.intake-reference-review').innerText();assert.equal(text.includes('CASE-A'),true);assert.equal(text.includes('false'),true);assert.equal(text.includes('null'),true);assert.equal(text.includes('KST'),true);
    await page.locator('#search').focus();await quiet(page);await page.screenshot({path:path.join(evidence,'integrated-1440.png'),fullPage:true});
    await page.setViewportSize({width:390,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.equal(await page.locator('#search').evaluate(n=>n===document.activeElement),true);
    await page.screenshot({path:path.join(evidence,'integrated-390.png'),fullPage:true});
   });
   await check('separate_expired_session403_no_parent_preserves_lastgood_and_anonymous_restart',async()=>{
    const good=await page.locator('.ir-current-results').innerText();await host.ask({op:'expire'});await page.locator('.ir-current-read').click();
    await page.waitForFunction(()=>document.querySelector('.ir-current-status')?.dataset.state==='error');assert.equal(await page.locator('.ir-current-results').innerText(),good);
    const report=await host.ask({op:'report'});assert.equal(report.stats.session_expiry_fault?.parent_current_started||0,0);result.phases.expiry=report;
   });
   await quiet(page);await context.close();await host.ask({op:'restart_phase'});
   const restarted=await browser.newContext({viewport:{width:1440,height:1000}}),active=await restarted.newPage();await watch(active,origin,'anonymous_restart');await active.goto(origin);await ready(active);
   await host.ask({op:'arm'});await active.locator('.ir-current-read').click();assert.equal((await host.ask({op:'wait'})).entered,true);
   await check('source1_queue0_second_tab_current429_real_metadata_allowed',async()=>{
    const other=await restarted.newPage();await watch(other,origin,'lifecycle');await other.goto(origin);await ready(other);await other.locator('.ir-current-read').click();
    await other.waitForFunction(()=>document.querySelector('.ir-current-status')?.dataset.state==='error');await settle();assert.equal(observations.some(o=>o.phase==='lifecycle'&&o.kind==='current'&&o.status===429),true);await quiet(other);await other.close();
   });
   await check('browser_abort_does_not_release_parent_close_waits_finally_and_caller_native_release',async()=>{
    await active.close();await restarted.close();await browser.close();browser=null;result.browser_closed=true;const closing=await host.ask({op:'begin_close'});assert.equal(closing.close_started,true);assert.equal(closing.close_done,false);
    assert.equal(closing.stats.lifecycle.parent_current_started,1);assert.equal(closing.stats.lifecycle.parent_current_returned||0,0);
    await host.ask({op:'release'});const final=await stopped(host);assert.equal(final.stats.lifecycle.parent_current_normal,1);assert.equal(final.gate_timed_out,false);
    assert.equal(final.borrowed_store_usable_after_host,true);assert.equal(final.native_blocked,4);assert.equal(final.native_released,4);assert.equal(final.SQLite_live,0);assert.equal(final.SQLite.SQLite_opened,final.SQLite.SQLite_closed);
    assert.equal(final.inputs_unchanged,true);assert.equal(final.port_rebound,true);result.phases.allow.final=final;
   });
  }
  await settle();for(const o of observations){assert.equal(o.observation_failed||false,false);if(o.kind==='history'&&o.status===200)assert.equal(o.response_csrf_shape,o.read_allowed==='true');if(o.kind==='current'&&o.status===200){assert.equal(o.csrf_shape,true);assert.equal(o.cookie_present,true);assert.equal(o.origin_valid,true);assert.equal(o.exact_body2,true);}}
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);checks.push('no_secret_storage_download_external_JS_or_manual_origin_cookie_headers');
 }catch(error){failure=error;save('failure.json',{stage,type:error.name,operator:error.operator,
  actual:typeof error.actual==='number'||typeof error.actual==='boolean'?error.actual:null,expected:typeof error.expected==='number'||typeof error.expected==='boolean'?error.expected:null,
  checker_lines:String(error.stack||'').split('\n').slice(1).filter(s=>s.includes(__filename+':')).map(s=>s.match(/:(\d+):\d+\)?$/)?.[1]),supervisor:children.filter(c=>c.fatal).map(c=>c.fatal)});}
 finally{
  try{if(browser)await browser.close();result.browser_closed=true;}catch{failure||=Error('browser_close_failed');}
  for(const child of children){if(child.exitState)continue;try{await child.ask({op:'release'});await child.ask({op:'finish'});await child.closed;}catch{child.child.kill();await child.closed;failure||=Error('child_cleanup_failed');}}
  result.children_closed=children.every(c=>c.exitState?.code===0&&c.exitState?.signal===null&&c.stderrBytes===0);
  const after=sourcePins();save('source-pins-after.json',after);result.source_unchanged=JSON.stringify(before)===JSON.stringify(after);
  result.javascript_errors=errors.length;result.external_requests=external.length;result.observations=observations.map(({promise,...o})=>o);
  result.status=!failure&&result.browser_closed&&result.children_closed&&result.source_unchanged?'pass':'fail';save('result.json',result);
 }
 console.log(JSON.stringify({phase:result.phase,status:result.status,checks:checks.length,evidence:path.relative(root,evidence).split(path.sep).join('/'),result_sha256:hash(fs.readFileSync(path.join(evidence,'result.json')))}));
 if(failure)throw Error('intake_reference_integrated_F2_failed');return result;
}

module.exports={createSyntheticBundle,main};
if(require.main===module)main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
