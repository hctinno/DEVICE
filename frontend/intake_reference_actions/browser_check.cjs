/*052 C1 complete synthetic wire DTOs. No025 producer, Store, provider or real host. */
const clone=value=>structuredClone(value);
function createSyntheticBundle(serial=1){
 const {context,history}=require('../intake_references/browser_check.cjs').createSyntheticBundle();
 history.records=history.records.slice(0,1);history.next_before_seq=null;
 const preview={schema_version:1,kind:'intake_reference_review_preview',intake_id:context.intake_id,
  preparation_id:'1'.repeat(64),observation:{kind:'paired_public_reads',snapshot_id:'a'.repeat(64),head_record_id:null,observed_at:'2026-10-25T00:01:02.123456+00:00'},
  preparation_ready:true,reason_codes:[],review_status:'bound',
  selection:{context_id:'2'.repeat(64),corpus_id:'SYNTHETIC-CORPUS-052',requested_case_ids:['CASE-A'],status:'selected',accepted_reference_count:1,receipt_id:'b'.repeat(64)},
  source_modes:{intake_revision_synthetic:true,catalog_synthetic:true,intake_provenance_status:'confirmed'},
  verification:{reference_receipt_validated:true,retained_snapshot_observed:true,reference_source_currentness_verified:false,
   operational_authority_granted:false,model_execution_verified:false,evaluation_executed:false}};
 const envelope={schema_version:1,kind:'intake_reference_preparation_handle',handle_id:serial.toString(16).padStart(64,'0'),
  append_request_id:'REF-SYNTHETIC-052-'+serial,expires_in_seconds:900,preview};
 const registration={schema_version:1,kind:'intake_reference_registration',request_id:envelope.append_request_id,
  record_id:'c'.repeat(64),seq:1,stored:true,replayed:false,binding_status:'current_at_append',
  append_observation:{expected_snapshot_id:preview.observation.snapshot_id,captured_snapshot_id:preview.observation.snapshot_id,
   head_before_record_id:null,head_after_record_id:'c'.repeat(64),head_advanced:true,preparation_ready:true,observed_at:'2026-10-25T00:02:03+00:00'},
  verification:{record_hash_verified:true,parent_revalidated_at_append:true,origin_revalidated_at_append:true,
   mutable_state_verified_at_append:true,operational_authority_granted:false,model_execution_verified:false,evaluation_executed:false,independent_evaluation_approved:false}};
 return clone({context,history,envelope,registration});
}
async function main(argv=process.argv.slice(2)){
 if(argv.length!==2||argv[0]!=='--mode'||argv[1]!=='component')throw Error('invalid_configuration');
 const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
 const {createHash}=require('node:crypto'),{execFileSync}=require('node:child_process');
 const root=fs.realpathSync(path.resolve(__dirname,'../..')),hash=b=>createHash('sha256').update(b).digest('hex');
 const local=path.join(root,'.local');fs.mkdirSync(local,{recursive:true});const evidence=fs.mkdtempSync(path.join(local,'ra052-'));
 const save=(name,value)=>fs.writeFileSync(path.join(evidence,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 const pins=()=>{const names=execFileSync('git',['ls-files','-z','--','labflow','frontend','tests'],{cwd:root}).toString().split('\0');
  names.push('frontend/intake_reference_actions/actions.mjs','frontend/intake_reference_actions/actions.test.mjs','frontend/intake_reference_actions/browser_check.cjs','docs/fcc/intake_reference_actions_usage.md');
  return Object.fromEntries([...new Set(names)].filter(Boolean).sort().map(n=>[n,hash(fs.readFileSync(path.join(root,n)))]));};
 const before=pins(),checks=[],errors=[],external=[];save('source-pins-before.json',before);
 const result={phase:'052 C1 synthetic wire/component DOM',status:'fail',checks,genuine049_053_F2_C2_executed:false,
  Store_025_source_model_hardware_executed:false,API_source_reads:0,browser_closed:false,server_closed:false,source_unchanged:false};
 let server,browser,page,failure;
 try{
  const files={'/intake-reference-actions/actions.mjs':['frontend/intake_reference_actions/actions.mjs','text/javascript'],
   '/intake-references/model.mjs':['frontend/intake_references/model.mjs','text/javascript'],'/base.css':['frontend/styles.css','text/css']};
  const css='body{margin:0;background:#f3f6fa;color:#1c2e45}main{max-width:1250px;margin:auto;padding:20px}.reference-actions-review{padding:22px;margin-top:18px;min-width:0}.ra-controls{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.ra-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.ra-columns>section{min-width:0}.ra-fields{display:grid;gap:8px 14px;grid-template-columns:repeat(2,minmax(0,1fr))}.ra-fields div{min-width:0}.ra-fields dt{font-size:11px;color:#64748b}.ra-fields dd{margin:2px 0;overflow-wrap:anywhere;font-size:12px}.ra-selection,.ra-status,.ra-note{overflow-wrap:anywhere;margin:8px 0}.ra-note{font-size:12px;color:#64748b}[data-stale=true]{border-left:3px solid #c88c27;padding-left:10px}@media(max-width:700px){main{padding:12px}.reference-actions-review{padding:14px}.ra-columns,.ra-fields{grid-template-columns:1fr}}';
  server=http.createServer((req,res)=>{res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
   res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
   if(req.method!=='GET'){res.writeHead(405);return res.end();}
   if(req.url==='/'){res.setHeader('Content-Type','text/html; charset=utf-8');return res.end('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>052 C1 합성 wire 구성요소</title><link rel="stylesheet" href="/base.css"><link rel="stylesheet" href="/component.css"><script type="module" src="/entry.mjs"></script><main><h1>참고 검토 구성요소 검증</h1><button id="outside">외부 초점</button><div id="mount"></div></main></html>');}
   if(req.url==='/component.css'){res.setHeader('Content-Type','text/css; charset=utf-8');return res.end(css);}
   if(req.url==='/entry.mjs'){res.setHeader('Content-Type','text/javascript; charset=utf-8');return res.end("import * as api from '/intake-reference-actions/actions.mjs';window.api=api;window.events=[];window.review=api.createIntakeReferenceActionsReview(document.querySelector('#mount'));document.querySelector('#mount').addEventListener('intake-reference-history-refresh',e=>window.events.push(e.detail));");}
   if(Object.hasOwn(files,req.url)){const [name,type]=files[req.url];res.setHeader('Content-Type',type+'; charset=utf-8');return res.end(fs.readFileSync(path.join(root,name)));}
   res.writeHead(404);res.end();
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
  browser=await require('playwright').chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const initial=createSyntheticBundle();save('fixture-manifest.json',{kind:'complete synthetic wire DTOs; no025 input producer',context:initial.context,actual_backend:false});
  await context.addInitScript(({initial,variants})=>{
   const native=fetch.bind(window),clone=x=>structuredClone(x),token='f'.repeat(64),other='e'.repeat(64);
   const queues={history:[],prepare:[],append:[]},holds=new Map(),counts={history:0,prepare:0,append:0,current:0},observations=[];
   let latest=clone(initial),serial=0;const registered=new Set();
   const headers={'Content-Type':'application/json; charset=utf-8'};
   function reply(kind,body,mode,intakeId){
    if(mode==='lost')return Promise.reject(Error('synthetic wire unavailable'));
    if(mode==='expired')return new Response('{"error":{"code":"intake_reference_review_host_prepared_unavailable"}}',{status:410,headers});
    if(mode==='cap')return new Response('{"error":{"code":"intake_reference_review_host_unavailable"}}',{status:503,headers});
    if(kind==='history'){
     const denied=mode==='denied',history=clone(latest.history);history.intake_id=intakeId;return new Response(JSON.stringify(history),{headers:{...headers,
      'X-Intake-Reference-Read-Allowed':denied?'false':'true','X-Intake-Reference-Prepare-Allowed':denied?'false':'true',
      'X-Intake-Reference-Append-Allowed':denied?'false':'true',...(denied?{}:{'X-Intake-Reference-Review-Input':'3'.repeat(64)}),
      ...(denied||mode==='missing_csrf'?{}:{'X-Intake-Reference-CSRF':mode==='changed_token'?other:token})}});
    }
    if(kind==='prepare'){
     latest=clone(variants[serial++%variants.length]);latest.envelope.preview.intake_id=intakeId;
     if(mode==='not_ready'){latest.envelope.preview.preparation_ready=false;latest.envelope.preview.reason_codes=['preparation_not_ready'];}
     if(mode==='zero_nullable'){latest.envelope.preview.selection.accepted_reference_count=0;latest.envelope.preview.selection.status='no_candidate';
      latest.envelope.preview.selection.context_id=null;latest.envelope.preview.selection.corpus_id=null;latest.envelope.preview.selection.requested_case_ids=[];
      latest.envelope.preview.review_status='insufficient_evidence';latest.envelope.preview.source_modes.catalog_synthetic=null;}
     if(mode==='all_reasons'){latest.envelope.preview.preparation_ready=false;
      latest.envelope.preview.reason_codes=['analysis_not_ready','profile_changed','delegation_missing','intake_deferred','delegation_evidence_missing','required_questions_open','unread_documents','source_provenance_unconfirmed','preparation_not_ready'].sort();}
     if(mode==='bad_json')return new Response('{"schema_version":1,"schema_version":1}',{headers});
     return new Response(JSON.stringify(latest.envelope),{headers});
    }
    const value=clone(latest.registration),req=JSON.parse(body);value.request_id=req.request_id;value.replayed=registered.has(req.request_id);registered.add(req.request_id);
    if(['historical_provided','head_conflict','preparation_unverified','reference_unbound'].includes(mode)){
     value.binding_status=mode;value.append_observation.head_advanced=false;value.append_observation.head_after_record_id=value.append_observation.head_before_record_id;
    }
    let raw=JSON.stringify(value);if(mode==='unsafe')raw=raw.replace('"seq":1','"seq":9007199254740993');return new Response(raw,{headers});
   }
   window.wire={counts,observations,poison_reads:0,next(kind,mode){queues[kind].push({mode});},hold(kind,label){queues[kind].push({label});},
    held(label){return holds.has(label);},release(label,mode='ok'){const h=holds.get(label);if(!h)throw Error('fixture_hold_missing');holds.delete(label);
     if(mode==='poison')return h.resolve({get headers(){window.wire.poison_reads++;throw Error('late');}});
     Promise.resolve(reply(h.kind,h.body,mode,h.intakeId)).then(h.resolve,h.reject);}};
   window.fetch=(url,options={})=>{
    if(!String(url).startsWith('/api/'))return native(url,options);
    const kind=String(url).includes('/history?')?'history':String(url).endsWith('/prepare')?'prepare':String(url).endsWith('/append')?'append':'current';counts[kind]++;
    if(kind==='current')return Promise.reject(Error('unexpected source'));
    const item={kind,method:options.method,aborted:!!options.signal.aborted,csrf_header_present:typeof options.headers?.['X-Intake-Reference-CSRF']==='string'};
    if(options.body){const body=JSON.parse(options.body);item.body_keys=Object.keys(body).sort();item.replace_null=kind==='prepare'?body.replace_handle_id===null:null;}
    observations.push(item);options.signal.addEventListener('abort',()=>{item.aborted=true;},{once:true});
    const intakeId=String(url).split('/')[3];
    const next=queues[kind].shift();if(next?.label)return new Promise((resolve,reject)=>holds.set(next.label,{kind,intakeId,body:options.body,resolve,reject}));
    return Promise.resolve(reply(kind,options.body,next?.mode||'ok',intakeId));
   };
  },{initial,variants:[1,2,3,4,5,6,7,8].map(createSyntheticBundle)});
  context.on('page',p=>{p.on('pageerror',()=>errors.push('pageerror'));p.on('request',r=>{if(!r.url().startsWith(origin+'/'))external.push('external');});});
  page=await context.newPage();page.setDefaultTimeout(10000);await page.goto(origin);await page.waitForFunction(()=>!!window.review);
  const phase=value=>page.waitForFunction(value=>document.querySelector('.reference-actions-review')?.dataset.phase===value,value);
  const counts=()=>page.evaluate(()=>({...window.wire.counts}));
  const next=(kind,mode)=>page.evaluate(({kind,mode})=>window.wire.next(kind,mode),{kind,mode});
  const hold=(kind,label)=>page.evaluate(({kind,label})=>window.wire.hold(kind,label),{kind,label});
  const held=label=>page.waitForFunction(label=>window.wire.held(label),label);
  const release=(label,mode='ok')=>page.evaluate(({label,mode})=>window.wire.release(label,mode),{label,mode});
  assert.deepEqual(await counts(),{history:0,prepare:0,append:0,current:0});
  const inventory=await page.evaluate(()=>({exports:Object.keys(window.api).sort(),view:Object.keys(window.review).sort()}));
  assert.deepEqual(inventory.exports,['createIntakeReferenceActionsController','createIntakeReferenceActionsReview']);
  assert.deepEqual(inventory.view,['destroy','refreshCapabilities','root','setContext','setPending']);checks.push('exports2_view5_constructor_zero_API');
  await page.evaluate(ctx=>window.review.setContext(ctx),initial.context);await page.locator('.ra-prepare').click();await phase('ready');
  assert.deepEqual(await counts(),{history:1,prepare:1,append:0,current:0});checks.push('explicit_prepare_bootstrap_H1_P1_no_auto_append_current');
  const n=(await counts()).history;await page.evaluate(ctx=>window.review.setContext(ctx),initial.context);assert.equal((await counts()).history,n);
  checks.push('same_context_noop_no_duplicate_metadata');
  await hold('append','keyboard');await page.locator('.ra-append').focus();await page.keyboard.press('Enter');await held('keyboard');
  assert.equal(await page.locator('.ra-append').isDisabled(),true);await page.locator('#outside').focus();await release('keyboard');await phase('recorded');
  assert.equal(await page.locator('#outside').evaluate(n=>n===document.activeElement),true);
  assert.equal(await page.evaluate(()=>window.events.length),1);assert.deepEqual(await page.evaluate(()=>window.events[0]),initial.context);
  assert.match(await page.locator('.ra-registration').innerText(),/KST/);checks.push('keyboard_append_event_context3_once_no_focus_theft_KST');
  await page.locator('.ra-replay').click();await phase('recorded');assert.match(await page.locator('.ra-registration').innerText(),/true/);
  assert.equal(await page.evaluate(()=>window.events.length),2);checks.push('explicit_original_replay_retains_observation_and_context_event');
  for(const status of ['historical_provided','head_conflict','preparation_unverified','reference_unbound']){
   await next('append',status);await page.locator('.ra-replay').click();await phase('recorded');assert.match(await page.locator('.ra-registration').innerText(),new RegExp(status));}
  checks.push('binding_five_business_states_false_authority_not_normalized');
  await next('prepare','not_ready');await page.locator('.ra-prepare').click();await phase('ready');
  assert.match(await page.locator('.ra-preview').innerText(),/preparation_not_ready/);assert.equal(await page.locator('.ra-append').isDisabled(),false);
  checks.push('false_readiness_preserved_without_inventing_authority');
  await next('prepare','zero_nullable');await page.locator('.ra-prepare').click();await phase('ready');
  assert.match(await page.locator('.ra-preview').innerText(),/no_candidate/);assert.match(await page.locator('.ra-preview').innerText(),/null/);
  assert.equal(await page.locator('.ra-preview dt').filter({hasText:'받아들인 참고 수'}).locator('..').locator('dd').innerText(),'0');
  checks.push('zero_nullable_insufficient_evidence_literals_preserved');
  await next('prepare','all_reasons');await page.locator('.ra-prepare').click();await phase('ready');
  const reasonsText=await page.locator('.ra-preview').innerText();for(const code of ['analysis_not_ready','profile_changed','delegation_missing','intake_deferred','delegation_evidence_missing','required_questions_open','unread_documents','source_provenance_unconfirmed','preparation_not_ready'])assert.ok(reasonsText.includes(code));
  checks.push('all_nine_preparation_reason_codes_have_literal_Korean_display');
  await next('prepare','lost');await page.locator('.ra-prepare').click();await phase('replacement_unknown');
  assert.equal(await page.locator('.ra-append').isDisabled(),true);assert.equal(await page.locator('.ra-replay').isDisabled(),true);
  assert.equal(await page.locator('.ra-preview').getAttribute('data-stale'),'true');checks.push('lost_replacement_old_invalid_lastgood_preserved');
  await page.locator('.ra-prepare').click();await phase('ready');
  assert.equal(await page.evaluate(()=>window.wire.observations.filter(x=>x.kind==='prepare').at(-1).replace_null),true);
  checks.push('explicit_new_prepare_after_unknown_replace_null');
  await hold('append','pending-append');await page.locator('.ra-append').click();await held('pending-append');
  await page.evaluate(()=>window.review.setPending(true));await phase('uncertain');
  assert.equal(await page.evaluate(()=>window.wire.observations.filter(x=>x.kind==='append').at(-1).aborted),true);
  await release('pending-append','poison');await page.evaluate(()=>window.review.setPending(false));
  await page.evaluate(ctx=>window.review.setContext({...ctx,snapshotGeneration:2}),initial.context);
  await page.locator('.ra-capabilities').click();await phase('uncertain');
  await page.locator('.ra-replay').click();await phase('recorded');
  assert.deepEqual(await page.evaluate(()=>window.events.at(-1)),{...initial.context,snapshotGeneration:2});
  assert.equal(await page.evaluate(()=>window.wire.poison_reads),0);checks.push('uncertain_before_abort_same_revision_new_generation_replay_late_before_parse');
  const changed={...initial.context,revision:3,snapshotGeneration:3};await page.evaluate(ctx=>window.review.setContext(ctx),changed);
  assert.equal(await page.locator('.ra-replay').isDisabled(),true);assert.equal(await page.locator('.ra-registration').isVisible(),false);
  checks.push('other_revision_hides_old_good_blocks_original_replay');
  await page.evaluate(ctx=>window.review.setContext({...ctx,snapshotGeneration:4}),initial.context);
  await next('history','missing_csrf');await page.locator('.ra-capabilities').click();
  await page.waitForFunction(()=>document.querySelector('.ra-status').dataset.error!=='');
  assert.notEqual(await page.locator('.reference-actions-review').getAttribute('data-phase'),'retired');
  await page.locator('.ra-capabilities').click();await phase('recorded');await page.locator('.ra-replay').click();await phase('recorded');
  checks.push('missing_token_not_session_change_preserves_original_slot');
  await next('history','changed_token');await page.locator('.ra-replay').click();await phase('retired');
  assert.equal(await page.locator('.ra-replay').isDisabled(),true);checks.push('valid_changed_token_retires_without_source_replay');
  await page.locator('.ra-prepare').click();await phase('ready');
  await next('append','unsafe');await page.locator('.ra-append').click();await phase('uncertain');
  assert.match(await page.locator('.ra-status').innerText(),/정확하게 표현/);checks.push('unsafe_seq_keeps_uncertain_never_rounded_or_success');
  await page.locator('.ra-capabilities').click();await phase('uncertain');await next('append','expired');await page.locator('.ra-replay').click();await phase('retired');
  checks.push('server_410_retired_without_fake_restoration');
  await next('history','denied');await page.locator('.ra-prepare').click();await phase('unconfigured');assert.equal(await page.locator('.ra-append').isDisabled(),true);
  checks.push('unconfigured_capability_closes_source_fixed_Korean_state');
  await page.locator('.ra-capabilities').click();await page.locator('.ra-prepare').click();await phase('ready');
  const longContext={...initial.context,intake_id:'SYNTHETIC-052-LONG-'.padEnd(150,'X'),snapshotGeneration:8};
  await page.evaluate(ctx=>window.review.setContext(ctx),longContext);await page.locator('.ra-prepare').click();await phase('ready');
  assert.ok((await page.locator('.ra-selection').innerText()).includes(longContext.intake_id));
  for(const width of [1440,390]){await page.setViewportSize({width,height:width===390?844:1000});await page.locator('.reference-actions-review').scrollIntoViewIfNeeded();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.screenshot({path:path.join(evidence,`component-${width}.png`),fullPage:true});}
  checks.push('light_component_CSS_390_1440_long_ASCII150_no_horizontal_overflow');
  const publicFacts=await page.evaluate(()=>({storage:[localStorage.length,sessionStorage.length],events:window.events,
   counts:{...window.wire.counts},observations:window.wire.observations,poison_reads:window.wire.poison_reads,
   private_visible:/f{64}|REF-SYNTHETIC-052|000000000000000000000000000000000000000000000000000000000000000[1-8]/.test(document.body.innerText),
   downloads:document.querySelectorAll('a[download]').length}));
  assert.deepEqual(publicFacts.storage,[0,0]);assert.equal(publicFacts.private_visible,false);assert.equal(publicFacts.downloads,0);assert.equal(publicFacts.counts.current,0);
  assert.ok(publicFacts.events.every(x=>Object.keys(x).sort().join(',')==='intake_id,revision,snapshotGeneration'));save('observations.json',publicFacts);
  checks.push('private_request_token_storage_download_current_zero');
  await hold('append','terminal');await page.locator('.ra-append').click();await held('terminal');const total=await counts(),events=await page.evaluate(()=>window.events.length);
  await page.evaluate(()=>{window.review.destroy();window.review.destroy();});await release('terminal','poison');
  await page.evaluate(ctx=>{window.review.setContext(ctx);window.review.setPending(false);window.review.refreshCapabilities();},initial.context);
  assert.equal(await page.locator('.reference-actions-review').count(),0);assert.deepEqual(await counts(),total);
  assert.equal(await page.evaluate(()=>window.events.length),events);assert.equal(await page.evaluate(()=>window.wire.poison_reads),0);
  checks.push('destroy_terminal_private_release_late_callbacks_events_zero');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);checks.push('Javascript_external_zero');
 }catch(e){failure=e;save('failure.json',{message:String(e.stack||e).replace(/[a-f0-9]{64}/g,'[redacted]')});if(page)try{await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true});}catch{}}
 finally{
  try{if(browser)await browser.close();result.browser_closed=true;}catch(e){failure||=e;}
  try{if(server){server.closeAllConnections();await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));}result.server_closed=true;}catch(e){failure||=e;}
  try{const after=pins();save('source-pins-after.json',after);result.source_unchanged=JSON.stringify(before)===JSON.stringify(after);if(!result.source_unchanged)failure||=Error('source_changed');}catch(e){failure||=e;}
  result.javascript_errors=errors.length;result.external_requests=external.length;result.status=!failure&&result.source_unchanged&&result.browser_closed&&result.server_closed?'pass':'fail';save('result.json',result);
 }
 console.log(JSON.stringify({phase:result.phase,status:result.status,checks:checks.length,evidence:path.relative(root,evidence).split(path.sep).join('/'),result_sha256:hash(fs.readFileSync(path.join(evidence,'result.json')))}));
 if(failure)throw Error('reference_actions_component_failed');return result;
}
module.exports={createSyntheticBundle,main};
if(require.main===module)main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
