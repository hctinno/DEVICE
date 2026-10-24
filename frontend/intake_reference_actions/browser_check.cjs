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
 if(argv.length===2&&argv[0]==='--mode'&&argv[1]==='integrated')return integratedMain();
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
  assert.equal(await page.locator('.ra-unresolved').count(),1);assert.equal(await page.locator('.ra-unresolved').isVisible(),true);
  assert.match(await page.locator('.ra-unresolved').innerText(),/등록 결과.*확인/);
  checks.push('retired_keeps_prior_delivery_unknown_public_observation');
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
const INTEGRATED_SUPERVISOR=String.raw`"""052 C2 acceptance only: public synthetic preparation, genuine049/053, no HTTP shim."""
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
        base={n:[list(row) for row in con.execute('SELECT * FROM "'+n.replace('"','""')+'" ORDER BY rowid')]
              for n in tables if not n.startswith('intake_reference_')}
        encoded=json.dumps(base,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        return {'dump_sha256':hashlib.sha256(dump).hexdigest(),'table_counts':counts,
                'base_rows_sha256':hashlib.sha256(encoded).hexdigest(),
                'reference_rows':[counts.get(n,0) for n in ['intake_reference_records','intake_reference_events','intake_reference_heads']]}
    finally:con.close()

def prepare(folder):
    from tests.test_ui_server import ReferenceFixture
    from labflow.active_intake import scan_source
    from labflow.intake_jobs import claim_job,complete_job,respond
    from labflow.intake_worker import SyntheticTextProvider
    from tests.test_document_extract import synthetic_pdf
    assert not folder.exists();folder.mkdir()
    f=ReferenceFixture(folder,registered=False)
    try:
        second=folder/'inbox/two';second.mkdir()
        (second/'request.pdf').write_bytes(synthetic_pdf(['product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A\nrevision_label: SECOND']))
        scan_source(f.legacy,'SYN-INBOX',now=200);scan_source(f.legacy,'SYN-INBOX',now=202)
        job=claim_job(f.legacy,'C2-WORKER',now=203)
        assert job is not None and job['intake_id']!=f.intake_id
        complete_job(f.legacy,job['job_id'],job['token'],SyntheticTextProvider().analyze(job),now=204)
        respond(f.legacy,'C2-PROCEED-SECOND','proceed',intake_id=job['intake_id'])
        categories={}
        with f.legacy.connection() as con:
            submissions=[json.loads(row[0])['submission'] for row in con.execute("SELECT result_json FROM intake_jobs WHERE state='completed'")]
        for submission in submissions:
            context_id=submission['context_id'];intake_context=json.loads(f.legacy.blob_path(context_id).read_bytes())
            categories[str(f.legacy.blob_path(context_id))]='context'
            for d in intake_context['documents']:
                categories[str(f.legacy.blob_path(d['sha256']))]='pdf'
                if d.get('extraction_id'):categories[str(f.legacy.blob_path(d['extraction_id']))]='extraction'
        meta={'intake_id':f.intake_id,'other_intake_id':job['intake_id'],'categories':categories,
              'P0':{'synthetic_intake_PDFs':2,'completed_jobs':2,'public042_prepare_append':0,'reference_rows':[0,0,0]}}
    finally:f.legacy.close()
    meta['database']=database(folder);meta['files']=fingerprint(folder)
    assert meta['database']['reference_rows']==[0,0,0]
    (folder.parent/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    emit({'prepared':True,'intake_id':meta['intake_id'],'other_intake_id':meta['other_intake_id'],'P0':meta['P0'],'files':len(meta['files'])})

def serve(folder,mode):
    from labflow.ui_server import create_server
    from labflow.store import Store
    meta=json.loads((folder.parent/'fixture.json').read_text(encoding='utf-8'))
    baseline_db=database(folder);baseline_files=fingerprint(folder)
    phase='startup';stats={};connections={};sql={'service_opened':0,'service_closed':0,'observer_opened':0,'observer_closed':0}
    monitor={'enabled':True};codes={};active_parents=0;main_ident=threading.get_ident();instrumented=set()
    entered=threading.Event();release=threading.Event();close_done=threading.Event()
    state={'gate_kind':None,'gate_when':None,'gate_timeout':False,'close_error':False,'closing':False,
           'core_close_calls':0,'core_close_None':False,'public_active_at_core_close':None,'original7_equal':True}
    originals={};store=None;server=None;loop=None;closer=None;actions_module=None
    def count(key,amount=1):
        b=stats.setdefault(phase,{});b[key]=b.get(key,0)+amount
    def trace(statement):
        # Only schema names are retained. Expanded INSERT values/requests are never saved.
        m=re.match(r'CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX|TRIGGER)(?:\s+IF\s+NOT\s+EXISTS)?\s+([A-Z_][A-Z0-9_]*)',statement.strip().upper())
        if m and m[1].startswith('INTAKE_REFERENCE_'):count('reference_DDL_attempt')
    def authorize(action,arg1,arg2,db,trigger):
        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
            if arg1 and arg1.startswith('intake_reference_'):count('reference_data_write_authorized')
            elif arg1 not in ('sqlite_master','sqlite_temp_master'):count('nonreference_write_authorized')
        return sqlite3.SQLITE_OK
    def audit(event,args):
        if not monitor['enabled']:return
        if event=='open' and args and type(args[0]) is str:
            category=meta['categories'].get(str(Path(args[0]).absolute()))
            if category:count('retained_open_'+category)
        elif event=='sqlite3.connect/handle':
            owner='observer' if threading.get_ident()==main_ident and phase!='startup' else 'service'
            connections[id(args[0])]=owner;sql[owner+'_opened']+=1
        elif event=='subprocess.Popen':count('subprocess_start')
    def gate(label,when):
        if state['gate_kind']==label and state['gate_when']==when:
            state['gate_kind']=None;entered.set()
            if not release.wait(18):state['gate_timeout']=True
    def profile(frame,event,arg):
        nonlocal active_parents
        code=frame.f_code;label=codes.get(code)
        if event=='c_call' and getattr(arg,'__name__',None) in ('execute','executemany','executescript','cursor'):
            con=getattr(arg,'__self__',None)
            if isinstance(con,sqlite3.Connection) and connections.get(id(con))=='service' and id(con) not in instrumented:
                # connect/handle is emitted before initialization; attach at the first native SQL call.
                instrumented.add(id(con));con.set_trace_callback(trace);con.set_authorizer(authorize)
        if label and event=='call':
            count(label+'_started')
            if label in ('core_prepare','core_append','read042','prepare042','append042'):active_parents+=1
            if label=='core_append':
                request=frame.f_locals['request'];key=request.get('handle_id')
                count('append_exact7' if set(request)=={'schema_version','handle_id','intake_id','request_id','preparation_id','expected_snapshot_id','expected_head_record_id'} else 'append_bad_keys')
                if key in originals:state['original7_equal'] &= originals[key]==request
                else:originals[key]=dict(request)
            if label=='core_close':state['core_close_calls']+=1;state['public_active_at_core_close']=active_parents
            gate(label,'entry')
        elif label and event=='return':
            if label=='core_append' and type(arg) is dict:
                state['last_registration']={k:arg[k] for k in ['seq','stored','replayed','binding_status']}
                state['last_registration'].update({k:arg['append_observation'][k] for k in ['head_advanced','preparation_ready']})
            gate(label,'return')
            count(label+'_returned')
            if type(arg) is dict:count(label+'_normal')
            if label in ('core_prepare','core_append','read042','prepare042','append042'):active_parents-=1
            if label=='core_close':state['core_close_None']=arg is None
        if event=='return' and label=='snapshot_blob' and type(arg) is tuple and type(arg[0]) is bytes:
            category=meta['categories'].get(str(frame.f_locals.get('path')))
            if category:count('bounded_blob_bytes_'+category,len(arg[0]))
        if event=='c_return' and getattr(arg,'__name__',None)=='close' and isinstance(getattr(arg,'__self__',None),sqlite3.Connection):
            owner=connections.pop(id(arg.__self__),None)
            instrumented.discard(id(arg.__self__))
            if owner:sql[owner+'_closed']+=1
        if event=='call' and code.co_filename==str(ROOT/'labflow/document_extract.py') and code.co_name=='extract_document':count('document_reparse')
        if event=='call' and code.co_filename==str(ROOT/'labflow/store.py'):
            if code.co_qualname=='Store.__init__':count('Store_constructor')
            if code.co_qualname=='Store.open_existing':count('Store_open_existing')
        return profile
    sys.addaudithook(audit);sys.setprofile(profile);threading.setprofile(profile)
    try:
        if mode=='none':
            assert 'labflow.intake_reference_review_host' not in sys.modules
            server=create_server(folder/'state',port=0)
        else:
            import labflow.intake_reference_review as review
            import labflow.intake_reference_ledger as ledger
            import labflow.intake_reference_snapshot as snapshot
            unwrap=lambda f:getattr(f,'__wrapped__',f).__code__
            codes.update({unwrap(review.read_reference_review):'read042',unwrap(review.prepare_reference_review):'prepare042',
                unwrap(review.append_reference_review):'append042',unwrap(ledger.reference_history):'history038',
                unwrap(ledger.current_reference):'current038',snapshot._blob.__code__:'snapshot_blob'})
            store=Store.open_existing(str(folder/'state'));kwargs={}
            if mode not in ('unconfigured',):
                from tests.test_intake_case_references import catalog_fixture,context_for,response_for
                catalog=catalog_fixture();context=context_for(catalog)
                response=response_for(context)
                if mode=='unbound':context['query']['model']='OTHER'
                supplied=tuple({'intake_id':ident,'case_context':context,'validated_response':response,
                    'producer_name':response['expected_producer']['name']} for ident in [meta['intake_id'],meta['other_intake_id']])
                if mode=='profile_fault':snapshot.current_extraction_profile_id=lambda:'b'*64
                kwargs={'fcc_case_catalog':catalog,'intake_reference_review_inputs':supplied,
                    'intake_reference_append_scope':() if mode in ('scope_deny','append_deny') else 'workspace'}
                import labflow.intake_reference_review_host as actions_module
                for name in ['prepare','append','capabilities','discard_session','close']:
                    codes[unwrap(getattr(actions_module.ReferenceReviewActions,name))]='core_'+name
                codes[unwrap(actions_module.create_reference_review_actions)]='core_factory'
            server=create_server(store.root,port=0,intake_reference_store=store,
                intake_reference_read_scope=() if mode=='scope_deny' else 'workspace',**kwargs)
        assert server.server_port not in (8765,8766)
        loop=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},name='C2-genuine-host');loop.start()
        phase=mode
        emit({'ready':True,'port':server.server_port,'mode':mode,'startup':stats.get('startup',{}),
            'core046_loaded':'labflow.intake_reference_review_host' in sys.modules,'baseline_rows':baseline_db['reference_rows']})
        def close():
            state['closing']=True
            try:
                if mode=='none':server.shutdown()
                server.server_close()
            except BaseException:state['close_error']=True
            finally:close_done.set()
        def report(with_db=False):
            out={'phase':phase,'stats':stats,'SQLite':sql,'SQLite_live':len(connections),'active_public_parents':active_parents,
                'entered':entered.is_set(),'close_started':state['closing'],'close_done':close_done.is_set(),
                'gate_timeout':state['gate_timeout'],'core_close_calls':state['core_close_calls'],
                'core_close_None':state['core_close_None'],'public_active_at_core_close':state['public_active_at_core_close'],
                'original7_equal':state['original7_equal'],'last_registration':state.get('last_registration')}
            if mode!='none':
                rt=server._reference_runtime
                with rt.lock:out.update(runtime_active=rt.active,source_active=rt.source_active,admission_closing=rt.closing)
            if with_db:out['database']=database(folder)
            return out
        for line in sys.stdin:
            command=json.loads(line);op=command['op']
            if op=='report':emit(report(command.get('database',False)))
            elif op=='phase':phase=command['name'];emit({'phase':phase})
            elif op=='arm':
                assert command['kind'] in ('core_prepare','core_append','read042') and command['when'] in ('entry','return')
                entered.clear();release.clear();state['gate_kind']=command['kind'];state['gate_when']=command['when'];phase=command.get('phase','fault');emit({'armed':True})
            elif op=='wait':emit({'entered':entered.wait(8)})
            elif op=='release':release.set();emit({'released':True})
            elif op=='expire_core':
                clock=actions_module._clock;actions_module._clock=lambda:clock()+901;phase='core_expiry_fault';emit({'core_clock_advanced':True})
            elif op=='expire_session':
                clock=server._reference_runtime.clock;server._reference_runtime.clock=lambda:clock()+901;phase='session_expiry_fault';emit({'session_clock_advanced':True})
            elif op=='revise':
                # Explicit synthetic fixture mutation, separate from HTTP/normal source counts.
                phase='fixture_mutation'
                from labflow.active_intake import scan_source
                from labflow.intake_jobs import claim_job,complete_job,respond
                from labflow.intake_worker import SyntheticTextProvider
                from tests.test_document_extract import synthetic_pdf
                p=folder/'inbox/one/request.pdf';p.write_bytes(synthetic_pdf(['product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A\nrevision_label: CHANGED']))
                scan_source(store,'SYN-INBOX',now=400);scan_source(store,'SYN-INBOX',now=402);job=claim_job(store,'C2-REVISION',now=403)
                assert job['intake_id']==meta['intake_id'];complete_job(store,job['job_id'],job['token'],SyntheticTextProvider().analyze(job),now=404)
                respond(store,'C2-PROCEED-REVISION','proceed',intake_id=job['intake_id'])
                baseline_db=database(folder);baseline_files=fingerprint(folder);emit({'public_revision':2})
            elif op=='begin_close':
                closer=threading.Thread(target=close,name='C2-caller-close');closer.start();time.sleep(.1);emit(report())
            elif op=='finish':
                release.set()
                if closer is None:closer=threading.Thread(target=close,name='C2-caller-close');closer.start()
                assert close_done.wait(14) and not state['close_error'];closer.join(2);loop.join(2);assert not loop.is_alive()
                monitor['enabled']=False;sys.setprofile(None);threading.setprofile(None)
                borrowed=False;blocked=0;targets=[folder,folder/'state',folder/'state/blobs',folder/'state/lab.sqlite3']
                def move(p):
                    bound=folder.parent.resolve();a=p.resolve();b=p.with_name(p.name+'.native-move').resolve()
                    assert a.is_relative_to(bound) and b.is_relative_to(bound) and not b.exists();p.rename(b);b.rename(p)
                if store:
                    with store.connection() as con:borrowed=con.execute('SELECT count(*) FROM intakes').fetchone()[0]==2
                    for p in targets:
                        try:move(p)
                        except OSError:blocked+=1
                    assert blocked==4;store.close();store=None
                for p in reversed(targets):move(p)
                after_db=database(folder);after_files=fingerprint(folder)
                sidecars_absent=not any((folder/'state'/('lab.sqlite3'+suffix)).exists() for suffix in ['-journal','-wal','-shm'])
                immutable=lambda files:{n:v for n,v in files.items() if n!='state/lab.sqlite3'}
                assert immutable(after_files)==immutable(baseline_files) and after_db['base_rows_sha256']==baseline_db['base_rows_sha256']
                probe=socket.socket();probe.bind(('127.0.0.1',server.server_port));probe.close()
                final=report();final.update({'closed':True,'loop_closed':True,'borrowed_store_usable_after_host':borrowed,
                    'native_blocked':blocked,'native_released':4,'port_rebound':True,'immutable_inputs_and_base_rows_unchanged':True,
                    'sidecars_absent':sidecars_absent,
                    'reference_rows_before':baseline_db['reference_rows'],'reference_rows_after':after_db['reference_rows'],
                    'mode':mode,'core046_loaded':'labflow.intake_reference_review_host' in sys.modules})
                emit(final);return
            else:raise AssertionError('unknown_supervisor_command')
    finally:
        release.set()
        if server:
            if mode=='none' and loop and loop.is_alive():server.shutdown()
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
/* C2 actual-app acceptance. Product requests reach genuine049/053; faults are named separately. */
async function integratedMain(){
 const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
 const {spawn,execFileSync}=require('node:child_process'),{createHash}=require('node:crypto');
 const root=fs.realpathSync(path.resolve(__dirname,'../..')),hash=b=>createHash('sha256').update(b).digest('hex');
 fs.mkdirSync(path.join(root,'.local'),{recursive:true});const evidence=fs.mkdtempSync(path.join(root,'.local/ra-c2-'));
 const save=(n,v)=>fs.writeFileSync(path.join(evidence,n),JSON.stringify(v,null,2)+'\n',{flag:'wx'});
 const pins=()=>Object.fromEntries(execFileSync('git',['ls-files','-z','--','labflow','frontend','tests'],{cwd:root}).toString('utf8').split('\0').filter(Boolean).sort().map(n=>[n,hash(fs.readFileSync(path.join(root,n)))]));
 const before=pins(),checks=[],children=[],observations=[],publicEvents=[],errors=[],external=[],wireSecrets=new Set(),privateRequests=new Set();
 const pendingObservations=new Set(),originals=new Map();let browser,stage='initialization',currentCheck=null,failure;
 const result={phase:'052 C2 genuine053 actual application composition',status:'fail',checks,phases:{},browser_closed:false,children_closed:false,source_unchanged:false,
  actual_model_customer_PDF_hardware_fullbackendPython_executed:false,retained_bytes_scope:'native bounded snapshot._blob subset; total bytes unknown'};
 save('source-pins-before.json',before);const helper=path.join(evidence,'supervisor.py');fs.writeFileSync(helper,INTEGRATED_SUPERVISOR,{flag:'wx'});
 const python=path.join(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),env={...process.env,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};delete env.PYTHONPATH;delete env.PYTHONHOME;
 function launch(args){
  const processChild=spawn(python,['-X','utf8','-B',helper,root,...args],{cwd:root,env,windowsHide:true,stdio:['pipe','pipe','pipe']});
  const lines=[],waiters=[];let buffer='',stderrBytes=0,exited=null;
  const closed=new Promise(resolve=>processChild.on('close',(code,signal)=>{exited={code,signal};for(const w of waiters.splice(0)){clearTimeout(w.timer);w.reject(Error('supervisor_closed'));}resolve(exited);}));
  processChild.stderr.on('data',b=>{stderrBytes+=b.length;});processChild.on('error',()=>{});
  processChild.stdout.on('data',b=>{buffer+=b.toString('utf8');while(buffer.includes('\n')){const i=buffer.indexOf('\n'),line=buffer.slice(0,i);buffer=buffer.slice(i+1);let value;try{value=JSON.parse(line);}catch{value={fatal:'invalid_supervisor_frame'};}
   if(waiters.length){const w=waiters.shift();clearTimeout(w.timer);w.resolve(value);}else lines.push(value);
  }});
  const next=()=>lines.length?Promise.resolve(lines.shift()):exited?Promise.reject(Error('supervisor_closed')):new Promise((resolve,reject)=>{
   const w={resolve,reject,timer:setTimeout(()=>{const i=waiters.indexOf(w);if(i>=0)waiters.splice(i,1);reject(Error('supervisor_timeout'));},25000)};waiters.push(w);
  });
  const api={child:processChild,closed,next,ask:async command=>{processChild.stdin.write(JSON.stringify(command)+'\n');const v=await next();if(v.fatal){api.fatal=v;throw Error('supervisor_failed');}return v;},get exit(){return exited;},get stderr(){return stderrBytes;}};
  children.push(api);return api;
 }
 const test=async(name,fn)=>{stage=name;currentCheck=name;console.log(JSON.stringify({running:name}));await fn();checks.push(name);};
 const settle=async()=>{while(pendingObservations.size)await Promise.all([...pendingObservations]);};
 const counts=(label=null)=>observations.filter(o=>!label||o.phase===label).reduce((a,o)=>(a[o.kind]=(a[o.kind]||0)+1,a),{history:0,current:0,prepare:0,append:0,main:0});
 async function watch(page,origin,label){
  page.on('pageerror',()=>errors.push(label));page.on('download',()=>errors.push('unexpected_download'));
  page.on('request',request=>{
   if(!request.url().startsWith(origin+'/')){external.push(label);return;}
   const url=new URL(request.url()),kind=url.pathname==='/api/intakes'?'main':url.pathname.startsWith('/api/intake-references/')?url.pathname.split('/').at(-1):null;
   if(!kind)return;const record={phase:label,kind,method:request.method(),response:null};observations.push(record);
   if(['prepare','append','current'].includes(kind)){
    const body=request.postDataJSON(),keys=Object.keys(body).sort();record.body_keys=keys;
    if(kind==='prepare')record.replace_null=body.replace_handle_id===null;
    if(kind==='append'){
     const text=JSON.stringify(body);wireSecrets.add(body.handle_id);privateRequests.add(body.request_id);
     if(originals.has(body.handle_id))record.original7_equal=originals.get(body.handle_id)===text;
     else originals.set(body.handle_id,text);
    }
   }
   const p=(async()=>{
    const headers=await request.allHeaders();record.same_origin=kind==='history'||kind==='main'||headers.origin===origin;
    record.csrf_shape=typeof headers['x-intake-reference-csrf']==='string'&&/^[a-f0-9]{64}$/.test(headers['x-intake-reference-csrf']);record.cookie_present=!!headers.cookie;
    const response=await request.response();if(!response){record.aborted=true;return;}
    record.response=response.status();const token=await response.headerValue('x-intake-reference-csrf');if(token)wireSecrets.add(token);
    record.read_allowed=await response.headerValue('x-intake-reference-read-allowed');
    if(kind==='history'){
     record.prepare_allowed=await response.headerValue('x-intake-reference-prepare-allowed');record.append_allowed=await response.headerValue('x-intake-reference-append-allowed');
     const input=await response.headerValue('x-intake-reference-review-input');if(input)wireSecrets.add(input);record.review_input_present=input!==null;
    }
    if(kind==='prepare'&&response.ok()){
     const v=await response.json();wireSecrets.add(v.handle_id);privateRequests.add(v.append_request_id);record.envelope_keys=Object.keys(v).sort();
    }
    if(kind==='append'&&response.ok()){
     const v=await response.json();record.registration_keys=Object.keys(v).sort();record.binding_status=v.binding_status;record.replayed=v.replayed;record.stored=v.stored;
    }
   })().catch(()=>{record.delivery_unknown=true;});pendingObservations.add(p);p.finally(()=>pendingObservations.delete(p));
  });
 }
 async function quiet(page){
  await settle();for(const cookie of await page.context().cookies()){wireSecrets.add(cookie.value);assert.equal(cookie.httpOnly,true);assert.equal(cookie.sameSite,'Strict');}
  const v=await page.evaluate(()=>({body:document.documentElement.outerHTML,actions:document.querySelector('.reference-actions-review')?.outerHTML||'',storage:[localStorage.length,sessionStorage.length],downloads:document.querySelectorAll('a[download]').length}));
  assert.equal([...wireSecrets].some(s=>s&&v.body.includes(s)),false);assert.equal([...privateRequests].some(s=>s&&v.actions.includes(s)),false);
  assert.deepEqual(v.storage,[0,0]);assert.equal(v.downloads,0);
 }
 const historyReady=page=>page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='ready');
 const actionPhase=(page,name)=>page.waitForFunction(value=>document.querySelector('.reference-actions-review')?.dataset.phase===value,name);
 async function start(mode,folder){
  stage='host_start_'+mode;
  const host=launch(['serve',folder,mode]);host.mode=mode;const initial=await host.next();if(initial.fatal){host.fatal=initial;throw Error('host_start_failed');}
  assert.equal(initial.ready,true);assert.equal(initial.startup.Store_constructor||0,0);return {host,initial,origin:`http://127.0.0.1:${initial.port}`};
 }
 async function open(s,prepared,label=s.initial.mode){
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();await watch(page,s.origin,label);
  await page.goto(s.origin+'/#'+prepared.intake_id);await page.locator('#detail-title').waitFor();await page.locator('.reference-actions-review').waitFor();
  return {context,page};
 }
 async function stopped(s){
  const v=await s.host.ask({op:'finish'});result.phases[s.initial.mode]=v;assert.deepEqual(await s.host.closed,{code:0,signal:null});assert.equal(s.host.stderr,0);
  assert.equal(v.closed,true);assert.equal(v.loop_closed,true);assert.equal(v.SQLite_live,0);assert.equal(v.SQLite.service_opened,v.SQLite.service_closed);assert.equal(v.SQLite.observer_opened,v.SQLite.observer_closed);
  assert.equal(v.immutable_inputs_and_base_rows_unchanged,true);assert.equal(v.port_rebound,true);
  assert.equal(v.native_released,4);assert.equal(v.sidecars_absent,true);assert.equal(v.gate_timeout,false);if(s.initial.mode!=='none'){assert.equal(v.native_blocked,4);assert.equal(v.borrowed_store_usable_after_host,true);}
  if(s.initial.core046_loaded){assert.equal(v.core_close_calls,1);assert.equal(v.core_close_None,true);assert.equal(v.public_active_at_core_close,0);}
  else assert.equal(v.core_close_calls,0);
  result.phases[s.initial.mode]=v;return v;
 }
 async function prepare(page){await page.locator('.ra-prepare').click();await actionPhase(page,'ready');assert.equal(await page.locator('.ra-append').isEnabled(),true);}
 async function append(page,replay=false){await page.locator(replay?'.ra-replay':'.ra-append').click();await actionPhase(page,'recorded');await historyReady(page);await settle();}
 async function fresh(mode){
  const parent=path.join(evidence,mode);fs.mkdirSync(parent);const folder=path.join(parent,'workspace'),p=launch(['prepare',folder]),prepared=await p.next();
  assert.equal(prepared.prepared,true);assert.deepEqual(await p.closed,{code:0,signal:null});assert.equal(p.stderr,0);
  result.P0_batches[mode]=prepared.P0;const s=await start(mode,folder),opened=await open(s,prepared);await historyReady(opened.page);return {...s,...opened,prepared};
 }
 async function drained(s){
  const deadline=Date.now()+8000;let v;do{v=await s.host.ask({op:'report',database:true});if(v.active_public_parents===0&&v.runtime_active===0)return v;
   assert.ok(Date.now()<deadline);await new Promise(r=>setTimeout(r,10));}while(true);
 }
 async function lost(s,kind,expected,selector){
  await s.host.ask({op:'arm',kind,when:'return',phase:expected+'_fault'});await s.page.locator(selector).click();assert.equal((await s.host.ask({op:'wait'})).entered,true);
  const committed=await s.host.ask({op:'report',database:true});await s.page.locator('#refresh').click();await historyReady(s.page);await actionPhase(s.page,expected);
  const observed={before_release_phase:await s.page.locator('.reference-actions-review').getAttribute('data-phase'),pending:await s.page.locator('.reference-actions-review').getAttribute('data-pending')};
  await s.host.ask({op:'release'});const after=await drained(s);await actionPhase(s.page,expected);await settle();return {committed,after,observed};
 }
 async function instrumentR1(page,origin){
  const cdp=await page.context().newCDPSession(page),hit={setContext:0,setPending:0,action:0},outside={setContext:0,setPending:0,action:0};let failed=false;
  cdp.on('Debugger.paused',async p=>{try{
   const frame=p.callFrames[0];const {result:r}=await cdp.send('Debugger.evaluateOnCallFrame',{callFrameId:frame.callFrameId,expression:'Boolean(globalThis.__C2R1?.active)',returnByValue:true});
   if(Object.hasOwn(hit,frame.functionName))(r.value?hit:outside)[frame.functionName]++;
  }catch{failed=true;}finally{try{await cdp.send('Debugger.resume');}catch{failed=true;}}});
  await cdp.send('Debugger.enable');
  const source=fs.readFileSync(path.join(root,'frontend/intake_reference_actions/actions.mjs'),'utf8').split(/\r?\n/),breakpoints=[];
  for(const [name,marker] of [['setContext','const setContext=value=>{'],['setPending','const setPending=value=>{'],['action','async function action(kind){']]){
   const line=source.findIndex(s=>s.includes(marker));assert.ok(line>=0);const v=await cdp.send('Debugger.setBreakpointByUrl',{url:origin+'/intake-reference-actions/actions.mjs',lineNumber:line+1});assert.ok(v.locations.length>0);breakpoints.push(v.breakpointId);
  }
  await page.evaluate(()=>{
   window.__C2R1={active:false,seen:0,unchanged:false,microtask:false};
   document.addEventListener('intake-reference-history-refresh',event=>{
    if(event.target!==document.querySelector('.reference-actions-review')||window.__C2R1.seen)return;
    window.__C2R1.active=true;queueMicrotask(()=>{window.__C2R1.active=false;window.__C2R1.microtask=true;});
   },{capture:true});
   document.addEventListener('intake-reference-history-refresh',event=>{
    if(event.target!==document.querySelector('.reference-actions-review')||window.__C2R1.seen)return;
    const snap=()=>[document.querySelector('#detail-title').textContent,location.hash,document.querySelector('#refresh').disabled,document.querySelector('#last-updated').textContent,document.querySelector('.reference-actions-review').dataset.pending,document.querySelector('#intake-view').getAttribute('aria-busy')];
    const before=snap();const selected=document.querySelector('.intake-item[aria-current="true"]');
    [...document.querySelectorAll('.intake-item')].find(n=>n!==selected)?.click();document.querySelector('#refresh').click();
    dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));window.__C2R1.unchanged=JSON.stringify(before)===JSON.stringify(snap());
    window.__C2R1.seen++;window.__C2R1.keys=Object.keys(event.detail).sort();window.__C2R1.frozen=Object.isFrozen(event.detail);window.__C2R1.context={...event.detail};
   });
  });
  return async()=>{
   const v=await page.evaluate(()=>window.__C2R1);for(const id of breakpoints)await cdp.send('Debugger.removeBreakpoint',{breakpointId:id});await cdp.detach();
   assert.equal(failed,false);assert.deepEqual(hit,{setContext:0,setPending:0,action:0});assert.ok(outside.action>0);assert.equal(v.seen,1);assert.equal(v.unchanged,true);assert.equal(v.microtask,true);assert.equal(v.frozen,true);
   assert.deepEqual(v.keys,['intake_id','revision','snapshotGeneration']);return {CDP_public_calls_during_bubbling:hit,main_unchanged:true,context_keys:v.keys};
  };
 }
 try{
  stage='P0_public_synthetic_fixture';const folder=path.join(evidence,'workspace'),p0=launch(['prepare',folder]),prepared=await p0.next();
  if(prepared.fatal){p0.fatal=prepared;throw Error('P0_failed');}assert.deepEqual(await p0.closed,{code:0,signal:null});assert.equal(prepared.prepared,true);assert.equal(p0.stderr,0);result.P0=prepared;result.P0_batches={initial:prepared.P0};
  browser=await require('playwright').chromium.launch({headless:true});
  await test('C2-20_actual_static4_GET_HEAD_bytes_MIME_no_store_CSP_alias404_method405',async()=>{
   const s=await fresh('static_assets');result.static=[];
   for(const [url,file] of [['/intake-references/model.mjs','frontend/intake_references/model.mjs'],['/intake-references/view.mjs','frontend/intake_references/view.mjs'],['/intake-references/transport.mjs','frontend/intake_references/transport.mjs'],['/intake-reference-actions/actions.mjs','frontend/intake_reference_actions/actions.mjs']]){
    const raw=fs.readFileSync(path.join(root,file)),git=execFileSync('git',['show','HEAD:'+file],{cwd:root});
    for(const method of ['GET','HEAD']){const response=await fetch(s.origin+url,{method}),data=Buffer.from(await response.arrayBuffer());
     assert.equal(response.status,200);assert.equal(response.headers.get('content-type'),'text/javascript; charset=utf-8');assert.equal(response.headers.get('cache-control'),'no-store');
     const csp=response.headers.get('content-security-policy');assert.equal(csp,"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
     assert.equal(response.headers.get('x-content-type-options'),'nosniff');assert.equal(response.headers.get('referrer-policy'),'no-referrer');
     assert.equal(Number(response.headers.get('content-length')),raw.length);if(method==='GET'){
      assert.ok(data.equals(raw));assert.ok(Buffer.from(data.toString('utf8').replace(/\r\n/g,'\n')).equals(git));
     }else assert.equal(data.length,0);
     result.static.push({url,method,status:200,response_matches_raw_file:method==='GET',normalized_GitLF_equal:method==='GET',raw_equals_GitLF:raw.equals(git),body_bytes:data.length,raw_file_bytes:raw.length,GitLF_bytes:git.length});
    }
   }
   for(const url of ['/intake_reference_actions/actions.mjs','/intake-reference-actions/missing.mjs','/intake-reference-actions/actions.mjs?alias=1'])assert.equal((await fetch(s.origin+url)).status,404);
   assert.equal((await fetch(s.origin+'/intake-reference-actions/actions.mjs',{method:'POST'})).status,405);await quiet(s.page);await s.context.close();await stopped(s);
  });
  await test('C2-10_None_empty_inputs_scope_default_and_append_default_preserve_capabilities',async()=>{
   for(const mode of ['none','unconfigured','scope_deny','append_deny']){
    const s=await start(mode,folder),{context,page}=await open(s,prepared);if(mode!=='none')await historyReady(page);
    else await page.waitForFunction(()=>document.querySelector('.ir-history-status')?.dataset.state==='error');
    await page.locator('.ra-capabilities').focus();await page.keyboard.press('Enter');await actionPhase(page,mode==='none'?'error':mode==='append_deny'?'idle':'unconfigured');
    if(mode!=='none'&&mode!=='append_deny')assert.equal((await page.locator('.ra-status').innerText()).includes('검토 입력이 없습니다'),true);
    if(mode==='append_deny'){await page.locator('.ra-prepare').click();await actionPhase(page,'ready');assert.equal(await page.locator('.ra-append').isDisabled(),true);}
    assert.equal(counts(mode).append,0);assert.equal(counts(mode).current,0);if(mode!=='append_deny')assert.equal(counts(mode).prepare,0);
    await quiet(page);await context.close();const done=await stopped(s);assert.deepEqual(done.reference_rows_before,done.reference_rows_after);
   }
  });
  const s=await start('normal',folder),{context,page}=await open(s,prepared);
  await test('C2-02_actual_sibling_single_mount_and_constructor_source0',async()=>{
   await historyReady(page);assert.equal(await page.locator('#intake-reference-actions-panel').count(),1);assert.equal(await page.locator('#detail-panel #intake-reference-actions-panel').count(),0);
   assert.equal(await page.locator('.reference-actions-review').count(),1);assert.equal(await page.locator('.intake-reference-review').count(),1);
   await page.evaluate(()=>window.__C2Nodes={actions:document.querySelector('.reference-actions-review'),reader:document.querySelector('.intake-reference-review')});
   const c=counts('normal');assert.equal(c.prepare,0);assert.equal(c.append,0);assert.equal(c.current,0);assert.equal(c.history,1);
  });
  await test('C2-11_native_prepare3_append7_original_replay7_and_metadata_only',async()=>{
   const before=await s.host.ask({op:'report',database:true});assert.deepEqual(before.database.reference_rows,[0,0,0]);await prepare(page);
   const finishR1=await instrumentR1(page,s.origin);await append(page);result.R1=await finishR1();
   const one=await s.host.ask({op:'report',database:true});assert.deepEqual(one.database.reference_rows,[1,1,1]);assert.equal(one.last_registration.binding_status,'current_at_append');
   assert.equal(counts('normal').main,1);assert.equal(counts('normal').current,0);await append(page,true);
   const replay=await s.host.ask({op:'report',database:true});assert.deepEqual(replay.database.reference_rows,[1,1,1]);assert.equal(replay.last_registration.replayed,true);assert.equal(replay.original7_equal,true);
   assert.equal(counts('normal').prepare,1);assert.equal(counts('normal').append,2);assert.equal(counts('normal').history,5);assert.equal(counts('normal').current,0);
   assert.equal(observations.filter(x=>x.kind==='append').at(-1).original7_equal,true);
  });
  checks.push('C2-06_actual_late_bubbling_selection_refresh_pending_guard_microtask_calls0');
  await test('C2-08_09_literals_false_authority_KST_focus_and_390_1440',async()=>{
   const text=await page.locator('.reference-actions-review').innerText();for(const v of ['false','KST','CASE-A'])assert.equal(text.includes(v),true);
   assert.equal((await page.locator('.intake-reference-review').innerText()).includes('null'),true);assert.ok(await page.locator('.metric strong').filter({hasText:/^0$/}).count()>0);
   await page.locator('#search').focus();await quiet(page);await page.screenshot({path:path.join(evidence,'C2-1440.png'),fullPage:true});
   await page.setViewportSize({width:390,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.equal(await page.locator('#search').evaluate(n=>n===document.activeElement),true);
   await page.screenshot({path:path.join(evidence,'C2-390.png'),fullPage:true});
  });
  result.normal_before_composition_faults=await s.host.ask({op:'report',database:true});
  await test('C2-05_current_event_metadata1_wrong_context_generation_target_getter0',async()=>{
   await s.host.ask({op:'phase',name:'composition_events'});await settle();const before=counts('normal');
   const poison=await page.evaluate(other=>{
    const root=document.querySelector('.reference-actions-review'),ctx=window.__C2R1.context;let reads=0;
    for(const detail of [{...ctx,intake_id:other},{...ctx,snapshotGeneration:ctx.snapshotGeneration+1},{...ctx,extra:true}])root.dispatchEvent(new CustomEvent('intake-reference-history-refresh',{detail,bubbles:true}));
    const detail={intake_id:ctx.intake_id,snapshotGeneration:ctx.snapshotGeneration};Object.defineProperty(detail,'revision',{enumerable:true,get(){reads++;return ctx.revision;}});
    root.dispatchEvent(new CustomEvent('intake-reference-history-refresh',{detail,bubbles:true}));root.querySelector('.ra-controls').dispatchEvent(new CustomEvent('intake-reference-history-refresh',{detail:ctx,bubbles:true}));
    return reads;
   },prepared.other_intake_id);assert.equal(poison,0);await page.evaluate(()=>Promise.resolve());assert.deepEqual(counts('normal'),before);
   await page.evaluate(()=>document.querySelector('.reference-actions-review').dispatchEvent(new CustomEvent('intake-reference-history-refresh',{detail:window.__C2R1.context,bubbles:true})));
   await historyReady(page);await settle();const after=counts('normal');assert.equal(after.history,before.history+1);for(const k of ['prepare','append','current','main'])assert.equal(after[k],before[k]);
  });
  await test('C2-03_selection_and_same_context_filter_keep_single_roots_hide_other_origin',async()=>{
   await s.host.ask({op:'phase',name:'composition_context'});const before=counts('normal');await page.locator('.intake-item').filter({hasText:'two'}).click();await historyReady(page);
   assert.equal((await page.locator('.ra-selection').innerText()).includes(prepared.other_intake_id),true);assert.equal(await page.locator('.ra-registration').isVisible(),false);assert.equal(await page.locator('.ra-replay').isDisabled(),true);
   await page.locator('.intake-item').filter({hasText:'one'}).click();await historyReady(page);await page.locator('.ra-capabilities').click();await actionPhase(page,'recorded');
   assert.equal(await page.locator('.ra-replay').isEnabled(),true);assert.equal(await page.evaluate(()=>window.__C2Nodes.actions===document.querySelector('.reference-actions-review')&&window.__C2Nodes.reader===document.querySelector('.intake-reference-review')),true);
   const stable=counts('normal').history;await page.locator('#filter').selectOption('all');await page.evaluate(()=>Promise.resolve());assert.equal(counts('normal').history,stable);
   assert.equal(counts('normal').append,before.append);assert.equal(counts('normal').prepare,before.prepare);assert.equal(counts('normal').current,0);
   await page.locator('[data-view="notifications"]').click();assert.equal(await page.locator('#intake-reference-actions-panel').isVisible(),false);
   await page.locator('[data-view="intakes"]').click();assert.equal(await page.locator('#intake-reference-actions-panel').isVisible(),true);
  });
  await test('C2-04_latest_main_finally_pending_and_C2-12_new_generation_original7',async()=>{
   await s.host.ask({op:'phase',name:'composition_pending'});const held=[];
   await page.route(s.origin+'/api/intakes',async route=>{const response=await route.fetch({maxRedirects:0,maxRetries:0});await new Promise(resolve=>held.push({resolve}));try{await route.fulfill({response});}catch{}});
   const waitHeld=async n=>{const end=Date.now()+8000;while(held.length<n){assert.ok(Date.now()<end);await new Promise(r=>setTimeout(r,10));}};
   await page.locator('#refresh').click();await waitHeld(1);await page.evaluate(()=>document.querySelector('#refresh').dispatchEvent(new Event('click')));await waitHeld(2);
   held[0].resolve();await page.evaluate(()=>new Promise(r=>setTimeout(r,25)));assert.equal(await page.locator('.reference-actions-review').getAttribute('data-pending'),'true');assert.equal(await page.locator('#refresh').isDisabled(),true);
   const h=counts('normal').history;held[1].resolve();await historyReady(page);await page.locator('#refresh').isEnabled();await settle();assert.equal(counts('normal').history,h+1);assert.equal(await page.locator('.reference-actions-review').getAttribute('data-pending'),'false');
   await page.unroute(s.origin+'/api/intakes');await page.locator('.ra-capabilities').click();await actionPhase(page,'recorded');await append(page,true);
   assert.equal(observations.filter(o=>o.kind==='append').at(-1).original7_equal,true);assert.equal(counts('normal').current,0);
  });
  await test('C2-03_null_selection_fallback_and_C2-04_main_failure_does_not_create_generation',async()=>{
   await page.evaluate(()=>{window.__C2Events=[];document.addEventListener('intake-reference-history-refresh',e=>window.__C2Events.push({...e.detail}));});
   await append(page,true);const original=await page.evaluate(()=>window.__C2Events.at(-1));
   await page.route(s.origin+'/api/intakes',async route=>{const response=await route.fetch();await route.fulfill({response,status:502});});
   const selected=await page.locator('.ra-selection').innerText(),before=counts('normal');await page.locator('#refresh').click();await page.locator('#error-banner').waitFor();
   await page.waitForFunction(()=>document.querySelector('.reference-actions-review')?.dataset.pending==='false');assert.equal(await page.locator('.ra-selection').innerText(),selected);
   assert.equal(counts('normal').prepare,before.prepare);assert.equal(counts('normal').append,before.append);assert.equal(counts('normal').current,0);await page.unroute(s.origin+'/api/intakes');
   await page.locator('.ra-capabilities').click();await actionPhase(page,'recorded');await append(page,true);assert.deepEqual(await page.evaluate(()=>window.__C2Events.at(-1)),original);
   const empty=counts('normal');await page.locator('#search').fill('__C2_NO_MATCH__');assert.equal(await page.locator('.ra-selection').innerText(),'현재 선택 없음');
   assert.equal(await page.locator('.ra-prepare').isDisabled(),true);assert.equal(await page.locator('.ra-append').isDisabled(),true);assert.equal(await page.locator('.ra-replay').isDisabled(),true);
   assert.equal(await page.locator('.ra-registration').getAttribute('data-stale'),'true');assert.equal(counts('normal').history,empty.history);
   await page.locator('#search').fill('');await historyReady(page);assert.equal((await page.locator('.ra-selection').innerText()).includes(prepared.intake_id),true);
   assert.equal(await page.evaluate(()=>window.__C2Nodes.actions===document.querySelector('.reference-actions-review')),true);
  });
  await test('C2-07_BFcache_metadata_only_and_terminal_destroy_inside_bubbling',async()=>{
   await s.host.ask({op:'phase',name:'bfcache'});const before=counts('normal');await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true})));
   assert.equal(await page.locator('.reference-actions-review').getAttribute('data-pending'),'true');await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));await historyReady(page);await settle();
   assert.equal(counts('normal').main,before.main+1);assert.equal(counts('normal').history,before.history+1);for(const k of ['prepare','append','current'])assert.equal(counts('normal')[k],before[k]);
   await s.host.ask({op:'phase',name:'terminal'});await prepare(page);
   await page.evaluate(()=>document.addEventListener('intake-reference-history-refresh',()=>{
    dispatchEvent(new PageTransitionEvent('pagehide',{persisted:false}));document.querySelector('#refresh').click();document.querySelector('.intake-item')?.click();
   },{once:true}));await page.locator('.ra-append').click();await page.waitForFunction(()=>!document.querySelector('.reference-actions-review'));
   assert.equal(await page.locator('.intake-reference-review').count(),0);await settle();const done=counts('normal');await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));await page.evaluate(()=>Promise.resolve());assert.deepEqual(counts('normal'),done);
  });
  await context.close();await stopped(s);
  await test('C2-13_commit_lost_response_uncertain_original7_replay_and_C2-15_real410_retired_note',async()=>{
   const s=await fresh('lost_append');await prepare(s.page);const lostFirst=await lost(s,'core_append','uncertain','.ra-append');
   assert.deepEqual(lostFirst.committed.database.reference_rows,[1,1,1]);assert.deepEqual(lostFirst.after.database.reference_rows,[1,1,1]);assert.equal(await s.page.locator('.ra-prepare').isDisabled(),true);
   const n=counts('lost_append').append;await s.page.locator('.ra-capabilities').click();await actionPhase(s.page,'uncertain');await append(s.page,true);
   assert.equal(counts('lost_append').append,n+1);assert.equal(observations.filter(o=>o.phase==='lost_append'&&o.kind==='append').at(-1).original7_equal,true);
   const recovered=await s.host.ask({op:'report',database:true});assert.deepEqual(recovered.database.reference_rows,[1,1,1]);assert.equal(recovered.last_registration.replayed,true);
   const lostReplay=await lost(s,'core_append','uncertain','.ra-replay');assert.deepEqual(lostReplay.after.database.reference_rows,[1,1,1]);
   await s.host.ask({op:'expire_core'});await s.page.locator('.ra-capabilities').click();await actionPhase(s.page,'uncertain');await s.page.locator('.ra-replay').click();await actionPhase(s.page,'retired');await settle();
   assert.equal(observations.filter(o=>o.phase==='lost_append'&&o.kind==='append').at(-1).response,410);assert.equal(await s.page.locator('.ra-unresolved').isVisible(),true);
   assert.equal(await s.page.locator('.ra-replay').isDisabled(),true);assert.equal(counts('lost_append').current,0);
   result.lost_append={first:lostFirst,recovered,retired:await s.host.ask({op:'report',database:true})};await quiet(s.page);await s.context.close();await stopped(s);
  });
  await test('C2-14_lost_prepare_and_replacement_unknown_new_prepare_null_keep_reservations',async()=>{
   for(const [mode,expected,replace] of [['lost_prepare','prepare_unknown',false],['lost_replace','replacement_unknown',true]]){
    const s=await fresh(mode);if(replace)await prepare(s.page);const before=counts(mode).prepare;
    const failure=await lost(s,'core_prepare',expected,'.ra-prepare');assert.deepEqual(failure.after.database.reference_rows,[0,0,0]);
    assert.equal(await s.page.locator('.ra-append').isDisabled(),true);assert.equal(await s.page.locator('.ra-prepare').innerText(),'새로 준비');
    assert.equal(counts(mode).prepare,before+1);assert.equal(observations.filter(o=>o.phase===mode&&o.kind==='prepare').at(-1).replace_null,!replace);
    await prepare(s.page);assert.equal(observations.filter(o=>o.phase===mode&&o.kind==='prepare').at(-1).replace_null,true);assert.equal(counts(mode).append,0);
    result[mode]=failure;await quiet(s.page);await s.context.close();await stopped(s);
   }
  });
  await test('C2-15_missing_contradictory_headers_preserve_slot_real_session_change_and_expiry',async()=>{
   const s=await fresh('session_faults');await prepare(s.page);
   for(const form of ['absent','contradictory']){
    await s.page.route(s.origin+'/api/intake-references/*/history?limit=1',async route=>{
     const response=await route.fetch(),headers={...response.headers()};if(form==='absent')delete headers['x-intake-reference-csrf'];else headers['x-intake-reference-prepare-allowed']='false';
     await route.fulfill({response,headers});
    });
    const before=counts('session_faults');await s.page.locator('.ra-capabilities').click();await actionPhase(s.page,'error');
    assert.equal(counts('session_faults').append,before.append);assert.equal(counts('session_faults').prepare,before.prepare);await s.page.unroute(s.origin+'/api/intake-references/*/history?limit=1');
    await s.page.locator('.ra-capabilities').click();await actionPhase(s.page,'ready');assert.equal(await s.page.locator('.ra-append').isEnabled(),true);
   }
   const unknown=await lost(s,'core_append','uncertain','.ra-append');assert.deepEqual(unknown.after.database.reference_rows,[1,1,1]);
   await s.host.ask({op:'expire_session'});const before=counts('session_faults');await s.page.locator('.ra-capabilities').click();await actionPhase(s.page,'uncertain');
   assert.equal(await s.page.locator('.ra-replay').isDisabled(),true);assert.equal(counts('session_faults').append,before.append);
   await s.context.clearCookies();await s.page.locator('.ra-capabilities').click();await actionPhase(s.page,'retired');assert.equal(await s.page.locator('.ra-unresolved').isVisible(),true);
   assert.equal(counts('session_faults').append,before.append);await quiet(s.page);await s.context.close();await stopped(s);
  });
  await test('C2-16_native_five_binding_classes_readiness_false_and_historical_revision',async()=>{
   result.binding_classes=['current_at_append'];
   for(const [mode,binding,heads] of [['profile_fault','preparation_unverified',0],['unbound','reference_unbound',0],['head_conflict','head_conflict',1],['historical','historical_provided',0]]){
    const s=await fresh(mode);await prepare(s.page);let rival;
    if(mode==='head_conflict'){rival=await open(s,s.prepared,'head_rival');await historyReady(rival.page);await prepare(rival.page);await append(rival.page);}
    if(mode==='historical')assert.equal((await s.host.ask({op:'revise'})).public_revision,2);
    await append(s.page);const actual=await s.host.ask({op:'report',database:true});assert.equal(actual.last_registration.binding_status,binding);assert.equal(actual.last_registration.head_advanced,false);
    assert.deepEqual(actual.database.reference_rows,[mode==='head_conflict'?2:1,mode==='head_conflict'?2:1,heads]);assert.equal((await s.page.locator('.ra-registration').innerText()).includes(binding),true);
    if(mode==='profile_fault'){assert.equal(actual.last_registration.preparation_ready,false);assert.equal((await s.page.locator('.ra-preview').innerText()).includes('profile_changed'),true);}
    if(mode==='historical'){
     const before=counts(mode);await s.page.locator('#refresh').click();await historyReady(s.page);assert.equal((await s.page.locator('.ra-selection').innerText()).includes('v2'),true);
     assert.equal(await s.page.locator('.ra-registration').isVisible(),false);assert.equal(await s.page.locator('.ra-replay').isDisabled(),true);assert.equal(counts(mode).append,before.append);
    }
    result.binding_classes.push(binding);result[mode]=actual;await quiet(s.page);if(rival)await rival.context.close();await s.context.close();await stopped(s);
   }
  });
  await test('C2-17_source_one_queue0_metadata_allowed_abort_holds_lease_C2-18_native_drain',async()=>{
   const s=await fresh('source_drain'),b=await open(s,s.prepared,'source_replay'),c=await open(s,s.prepared,'source_append'),d=await open(s,s.prepared,'source_prepare');
   await Promise.all([historyReady(b.page),historyReady(c.page),historyReady(d.page)]);await prepare(b.page);await append(b.page);await prepare(c.page);
   await s.host.ask({op:'arm',kind:'read042',when:'entry',phase:'held_source'});await s.page.locator('.ir-current-read').click();assert.equal((await s.host.ask({op:'wait'})).entered,true);
   const held=await s.host.ask({op:'report',database:true});assert.equal(held.source_active,true);assert.equal(held.active_public_parents,1);
   await b.page.locator('.ra-replay').click();await actionPhase(b.page,'uncertain');await c.page.locator('.ra-append').click();await actionPhase(c.page,'uncertain');await d.page.locator('.ra-prepare').click();await actionPhase(d.page,'prepare_unknown');
   const deadline=Date.now()+8000;for(const [label,kind] of [['source_replay','append'],['source_append','append'],['source_prepare','prepare']]){
    while(observations.filter(o=>o.phase===label&&o.kind===kind).at(-1)?.response!==429){assert.ok(Date.now()<deadline);await new Promise(r=>setTimeout(r,10));}
   }
   await s.page.locator('#refresh').click();await historyReady(s.page);await b.page.locator('.ra-capabilities').click();await actionPhase(b.page,'uncertain');
   const aborted=await s.host.ask({op:'report',database:true});assert.equal(aborted.source_active,true);assert.equal(aborted.active_public_parents,1);assert.deepEqual(aborted.database.reference_rows,[1,1,1]);
   assert.equal(aborted.stats.held_source.core_prepare_started||0,0);assert.equal(aborted.stats.held_source.core_append_started||0,0);
   const closing=await s.host.ask({op:'begin_close'});assert.equal(closing.close_done,false);assert.equal(closing.core_close_calls,0);assert.equal(closing.admission_closing,true);
   await Promise.all([s.context.close(),b.context.close(),c.context.close(),d.context.close()]);await s.host.ask({op:'release'});const done=await stopped(s);
   assert.equal(done.public_active_at_core_close,0);assert.equal(done.source_active,false);assert.equal(done.runtime_active,0);result.source_lease={held,after_browser_abort:aborted,closing};
  });
  await settle();assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 }catch(error){failure=error;save('failure.json',{check:currentCheck,stage,type:error.name,operator:error.operator,
  actual:typeof error.actual==='number'||typeof error.actual==='boolean'?error.actual:null,expected:typeof error.expected==='number'||typeof error.expected==='boolean'?error.expected:null,
  lines:String(error.stack||'').split('\n').slice(1).filter(s=>s.includes(__filename+':')).map(s=>s.match(/:(\d+):\d+\)?$/)?.[1]),supervisor:children.filter(c=>c.fatal).map(c=>c.fatal)});}
 finally{
  try{if(browser)await browser.close();result.browser_closed=true;}catch{failure||=Error('browser_close_failed');}
  for(const child of children){if(child.exit)continue;try{await child.ask({op:'release'});const value=await child.ask({op:'finish'});if(child.mode)result.phases[child.mode]=value;await child.closed;}catch{child.child.kill();await child.closed;failure||=Error('cleanup_failed');}}
  result.cleanup_fatal=children.filter(c=>c.fatal).map(c=>({mode:c.mode||'P0',...c.fatal}));
  result.children_closed=children.every(c=>c.exit?.code===0&&c.exit?.signal===null&&c.stderr===0);const after=pins();save('source-pins-after.json',after);result.source_unchanged=JSON.stringify(before)===JSON.stringify(after);
  result.observations=observations;result.javascript_errors=errors.length;result.external_requests=external.length;
  result.status=!failure&&result.browser_closed&&result.children_closed&&result.source_unchanged?'pass':'fail';save('result.json',result);
 }
 console.log(JSON.stringify({phase:result.phase,status:result.status,checks:checks.length,evidence:path.relative(root,evidence).split(path.sep).join('/'),result_sha256:hash(fs.readFileSync(path.join(evidence,'result.json')))}));
 if(failure)throw Error('intake_reference_composition_C2_failed');return result;
}

module.exports={createSyntheticBundle,main};
if(require.main===module)main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
