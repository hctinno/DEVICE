/* Isolated AI connection UI. Credentials and artifact paths never enter this module. */
const MODELS=['gemini-4-argon','gemini-3.8-flash'],LEVELS=['LOW','MEDIUM','HIGH'];
const TARGET='project-a6310591-f8cc-487c-9e3',BASE='/api/ai-connections/';
const CAPS=['read_profile','edit_profile','run_registered_synthetic','cancel_own'];
const SHA=/^[a-f0-9]{64}$/,ID=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;
const PROFILE='schema_version profile_id provider project_id location quota_project_id auth_profile_id selected_model models revision'.split(' ');
const SETTINGS='schema_version kind profile_id profile_revision provider service project_id location quota_project_id auth_profile_id model_id thinking_level max_output_tokens timeout_seconds profile_sha256 settings_sha256'.split(' ');
const USAGE='prompt_token_count candidates_token_count total_token_count thoughts_token_count cached_content_token_count tool_use_prompt_token_count'.split(' ');
const REASONS='unconfigured credential_missing quota_mismatch trial_unconfirmed approval_expired target_mismatch budget_unavailable budget_exhausted scenario_unavailable settings_outside_batch_budget busy closing profile_not_saved'.split(' ');
const FAILURE_CODES=new Set(['ai_connection_ui_unavailable',
  ...'invalid_input invalid_settings credential_invalid credential_quota_mismatch dependency_unavailable evidence_error auth_failed http_error response_invalid incomplete blocked limit_exceeded timeout cancelled cleanup_failed internal_error'.split(' ').map(x=>'vertex_response_'+x),
  ...'invalid_input limit_exceeded state_error dependency_unavailable'.split(' ').map(x=>'model_comparison_'+x)]);
const integer=(v,min=0,max=Number.MAX_SAFE_INTEGER)=>typeof v==='number'&&Number.isSafeInteger(v)&&!Object.is(v,-0)&&v>=min&&v<=max;
const number=(v,min=0,max=Number.MAX_SAFE_INTEGER)=>typeof v==='number'&&Number.isFinite(v)&&!Object.is(v,-0)&&v>=min&&v<=max;
const nullable=(v,check)=>v===null||check(v);
const need=v=>{if(!v)throw Error('ai_connection_ui_invalid_response');};
const keys=(v,names)=>{need(v!==null&&typeof v==='object'&&!Array.isArray(v));const own=Object.keys(v);need(own.length===names.length&&own.every(k=>names.includes(k)));};
const equalList=(v,expected)=>Array.isArray(v)&&v.length===expected.length&&v.every((x,i)=>x===expected[i]);
const clone=value=>JSON.parse(JSON.stringify(value));

function strictJSON(raw){
  need(typeof raw==='string'&&new TextEncoder().encode(raw).length<=262144);
  let i=0,nodes=0;const space=()=>{while(/[\x20\t\r\n]/.test(raw[i]||'!'))i++;};
  const string=()=>{const start=i++;while(i<raw.length){if(raw[i]==='\\'){i+=2;continue;}if(raw[i++]==='"'){
    const v=JSON.parse(raw.slice(start,i));need(!/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v));return v;}}throw Error();};
  const value=depth=>{need(depth<=32&&++nodes<=20000);space();const c=raw[i];
    if(c==='"')return string();
    if(c==='{'){i++;space();const out=Object.create(null);if(raw[i]==='}'){i++;return out;}while(true){space();need(raw[i]==='"');const key=string();need(!Object.hasOwn(out,key));space();need(raw[i++]===':');out[key]=value(depth+1);space();const end=raw[i++];if(end==='}')return out;need(end===',');}}
    if(c==='['){i++;space();const out=[];if(raw[i]===']'){i++;return out;}while(true){out.push(value(depth+1));space();const end=raw[i++];if(end===']')return out;need(end===',');}}
    for(const [token,v]of[['true',true],['false',false],['null',null]])if(raw.startsWith(token,i)){i+=token.length;return v;}
    const match=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(raw.slice(i));need(match);i+=match[0].length;const v=Number(match[0]);need(Number.isFinite(v)&&!Object.is(v,-0));if(!/[.eE]/.test(match[0]))need(Number.isSafeInteger(v));return v;
  };
  const result=value(0);space();need(i===raw.length);return result;
}

function validateProfile(v){
  keys(v,PROFILE);need(v.schema_version===1&&v.profile_id==='vertex-trial'&&v.auth_profile_id==='vertex-trial'&&v.provider==='vertex_ai'&&
    v.project_id===TARGET&&v.quota_project_id===TARGET&&['global','us','eu'].includes(v.location)&&MODELS.includes(v.selected_model)&&integer(v.revision));
  keys(v.models,MODELS);for(const item of Object.values(v.models)){keys(item,['thinking_level','max_output_tokens','timeout_seconds']);need(LEVELS.includes(item.thinking_level)&&integer(item.max_output_tokens,64,8192)&&number(item.timeout_seconds,1,120));}
}
function validateSettings(v){
  keys(v,SETTINGS);need(v.schema_version===1&&v.kind==='ai_run_settings'&&v.profile_id===v.auth_profile_id&&v.profile_id==='vertex-trial'&&v.provider==='vertex_ai'&&
    v.service==='aiplatform.googleapis.com'&&v.project_id===TARGET&&v.quota_project_id===TARGET&&['global','us','eu'].includes(v.location)&&integer(v.profile_revision)&&
    MODELS.includes(v.model_id)&&LEVELS.includes(v.thinking_level)&&integer(v.max_output_tokens,64,8192)&&number(v.timeout_seconds,1,120)&&SHA.test(v.profile_sha256)&&SHA.test(v.settings_sha256));
  // Python canonical JSON may contain60.0. Hashes are opaque server bindings, never recomputed in JS.
}
function parseDTO(raw,kind){
  const v=strictJSON(raw);need(v.schema_version===1&&v.kind==='ai_connection_'+kind);
  if(kind==='session'){keys(v,['schema_version','kind','capabilities','expires_at']);need(equalList(v.capabilities,CAPS)&&number(v.expires_at));}
  else if(kind==='state'){
    keys(v,'schema_version kind profile catalog capabilities auth trial budget gate scenarios active_run_id recent_runs'.split(' '));validateProfile(v.profile);need(equalList(v.capabilities,CAPS));
    keys(v.catalog,['locations','model_ids','thinking_levels','defaults','ranges']);need(equalList(v.catalog.locations,['global','us','eu'])&&equalList(v.catalog.model_ids,MODELS)&&equalList(v.catalog.thinking_levels,LEVELS));
    keys(v.catalog.defaults,['thinking_level','max_output_tokens','timeout_seconds']);need(v.catalog.defaults.thinking_level==='MEDIUM'&&v.catalog.defaults.max_output_tokens===512&&v.catalog.defaults.timeout_seconds===60);
    keys(v.catalog.ranges,['max_output_tokens','timeout_seconds']);need(equalList(v.catalog.ranges.max_output_tokens,[64,8192])&&equalList(v.catalog.ranges.timeout_seconds,[1,120]));
    keys(v.auth,['state','credential_file_ready','checked_at']);need(['missing','other_quota','access_unknown','verified'].includes(v.auth.state)&&typeof v.auth.credential_file_ready==='boolean'&&nullable(v.auth.checked_at,number));
    keys(v.trial,['state','checked_at']);need(['unknown','confirmed','approval_expired','blocked'].includes(v.trial.state)&&nullable(v.trial.checked_at,number));
    keys(v.budget,['limit_calls','reserved_calls','remaining_calls','limit_output_tokens','reserved_output_tokens','wall_budget_seconds']);need(v.budget.limit_calls===6&&v.budget.limit_output_tokens===3072&&v.budget.wall_budget_seconds===300&&
      nullable(v.budget.reserved_calls,x=>integer(x,0,6))&&nullable(v.budget.remaining_calls,x=>integer(x,0,6))&&nullable(v.budget.reserved_output_tokens,x=>integer(x,0,3072)));
    keys(v.gate,['run_allowed','reasons']);need(typeof v.gate.run_allowed==='boolean'&&Array.isArray(v.gate.reasons)&&new Set(v.gate.reasons).size===v.gate.reasons.length&&v.gate.reasons.every(x=>REASONS.includes(x))&&
      v.gate.run_allowed===(v.gate.reasons.length===0));
    if(v.gate.run_allowed)need(v.profile.revision>=1&&v.auth.credential_file_ready&&v.trial.state==='confirmed'&&integer(v.budget.remaining_calls,1,6));
    need(Array.isArray(v.scenarios)&&v.scenarios.length<=128);for(const s of v.scenarios){keys(s,['scenario_id','label','input_sha256','schema_sha256','evaluator_id']);need(ID.test(s.scenario_id)&&ID.test(s.evaluator_id)&&typeof s.label==='string'&&new TextEncoder().encode(s.label).length<=256&&SHA.test(s.input_sha256)&&SHA.test(s.schema_sha256));}
    need(nullable(v.active_run_id,x=>typeof x==='string'&&SHA.test(x))&&Array.isArray(v.recent_runs)&&v.recent_runs.length<=16);
    for(const r of v.recent_runs){keys(r,['run_id','state','matrix','scenario_id','created_at','finished_at']);need(SHA.test(r.run_id)&&['queued','running','cancelling','finished'].includes(r.state)&&typeof r.matrix==='boolean'&&ID.test(r.scenario_id)&&number(r.created_at)&&nullable(r.finished_at,number));}
  }else if(kind==='run'){
    keys(v,'schema_version kind run_id profile_revision scenario_id scenario_sha256 input_kind execution_mode state matrix created_at finished_at cancel_requested attempts_used cells error_code'.split(' '));
    need(typeof v.run_id==='string'&&SHA.test(v.run_id)&&integer(v.profile_revision,1)&&ID.test(v.scenario_id)&&SHA.test(v.scenario_sha256)&&v.input_kind==='registered_synthetic'&&
      [null,'actual','mock','replay'].includes(v.execution_mode)&&['queued','running','cancelling','finished'].includes(v.state)&&typeof v.matrix==='boolean'&&number(v.created_at)&&nullable(v.finished_at,number)&&
      typeof v.cancel_requested==='boolean'&&nullable(v.attempts_used,x=>integer(x,0,6))&&Array.isArray(v.cells)&&v.cells.length===6&&(v.error_code===null||FAILURE_CODES.has(v.error_code)));
    for(const [i,c]of v.cells.entries()){
      keys(c,'model_id thinking_level settings state reason_code attempted http_status finish_reason reported_model_version response_id response_complete strict_decode quality usage cost latency_ms error_code'.split(' '));
      need(c.model_id===MODELS[Math.floor(i/3)]&&c.thinking_level===LEVELS[i%3]&&['not_run','running','success','failure','unknown'].includes(c.state)&&
        nullable(c.reason_code,x=>typeof x==='string'&&/^[a-z_]{1,100}$/.test(x))&&[null,true,false].includes(c.attempted)&&nullable(c.http_status,x=>integer(x,100,599))&&
        nullable(c.finish_reason,x=>typeof x==='string'&&/^[A-Z_]{1,64}$/.test(x))&&nullable(c.reported_model_version,x=>typeof x==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$/.test(x))&&
        nullable(c.response_id,x=>typeof x==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$/.test(x))&&[null,true,false].includes(c.response_complete)&&['not_run','pass','fail','unknown'].includes(c.strict_decode)&&
        c.quality==='not_run'&&c.cost===null&&nullable(c.latency_ms,number)&&[null,'ai_connection_ui_unavailable'].includes(c.error_code));
      if(c.settings!==null){validateSettings(c.settings);need(c.settings.model_id===c.model_id&&c.settings.thinking_level===c.thinking_level&&c.settings.profile_revision===v.profile_revision);}
      else need(!v.matrix&&c.state==='not_run'&&c.reason_code==='not_selected');
      if(c.usage!==null){keys(c.usage,USAGE);for(const count of Object.values(c.usage))need(count===null||typeof count==='string'&&/^(0|[1-9]\d{0,18})$/.test(count)&&BigInt(count)<=9223372036854775807n);}
      if(c.state==='success')need(c.response_complete===true&&c.http_status===200&&c.finish_reason==='STOP'&&c.strict_decode==='pass');
    }
    need(v.cells.filter(c=>c.settings!==null).length===(v.matrix?6:1));
  }else need(false);
  return v;
}

function requestFor(profile,scenario,model,overrides,matrix){
  validateProfile(profile);need(profile.revision>=1&&ID.test(scenario)&&typeof matrix==='boolean');
  need(matrix?model===null:MODELS.includes(model));need(overrides!==null&&typeof overrides==='object'&&!Array.isArray(overrides));
  const allowed=matrix?['max_output_tokens','timeout_seconds']:['thinking_level','max_output_tokens','timeout_seconds'];
  for(const [key,value]of Object.entries(overrides)){need(allowed.includes(key));need(key==='thinking_level'?LEVELS.includes(value):key==='max_output_tokens'?integer(value,64,8192):number(value,1,120));}
  return {expected_revision:profile.revision,scenario_id:scenario,model_id:model,overrides:clone(overrides),matrix};
}
function admitStart(value,request,profile){
  validateProfile(profile);need(value.profile_revision===request.expected_revision&&value.scenario_id===request.scenario_id&&value.matrix===request.matrix);
  let count=0,profileHash=null;
  for(const [index,cell]of value.cells.entries()){
    if(cell.settings===null)continue;count++;const settings=cell.settings;validateSettings(settings);
    const model=MODELS[Math.floor(index/3)],stored=profile.models[model];
    need((request.matrix||model===request.model_id)&&settings.model_id===model&&settings.location===profile.location&&settings.profile_revision===request.expected_revision&&
      settings.thinking_level===(request.matrix?LEVELS[index%3]:request.overrides.thinking_level??stored.thinking_level)&&
      settings.max_output_tokens===(request.overrides.max_output_tokens??stored.max_output_tokens)&&settings.timeout_seconds===(request.overrides.timeout_seconds??stored.timeout_seconds));
    if(profileHash===null)profileHash=settings.profile_sha256;else need(profileHash===settings.profile_sha256);
  }
  need(count===(request.matrix?6:1));
}

const reasonLabels={profile_not_saved:'프로필을 먼저 저장하세요.',credential_missing:'별도 인증파일 준비를 확인하지 못했습니다.',quota_mismatch:'인증 quota 프로젝트가 다릅니다.',trial_unconfirmed:'무료 체험 실행 허용을 확인하지 못했습니다.',approval_expired:'실행 허용의 확인 기간이 만료됐습니다.',budget_unavailable:'누적 예산을 확인하지 못했습니다.',budget_exhausted:'허용된 호출 예산을 모두 사용했습니다.',scenario_unavailable:'등록된 합성 입력이 없습니다.',busy:'다른 실행이 진행 중입니다.',closing:'서버가 종료 중입니다.',target_mismatch:'대상 프로젝트가 다릅니다.',settings_outside_batch_budget:'현재 승인 묶음의 설정 한도를 넘었습니다.',unconfigured:'연결 기능이 설정되지 않았습니다.'};
const when=v=>v===null?'미확인':new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'short',timeStyle:'medium'}).format(new Date(v*1000))+' KST';

export function createAIConnectionPanel(root){
  need(root&&root.nodeType===1&&root.ownerDocument&&typeof root.ownerDocument.createElement==='function');
  const document=root.ownerDocument;
  let alive=true,visible=false,csrf=null,sessionBinding=null,epoch=0,poll=null,busy=false,current=null,good=null,run=null,previous=null,draft=null,message='연결 설정을 조회하지 않았습니다.';
  let runModel=MODELS[1],runModelEdited=false,scenario='',overrides={thinking_level:'',max_output_tokens:'',timeout_seconds:''};
  let painted=null;
  const requests=new Set();
  const el=(tag,text='',className='')=>{const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;};
  const stop=()=>{epoch++;clearTimeout(poll);poll=null;for(const c of requests)c.abort();requests.clear();};
  const field=(label,id,input)=>{const box=el('label',label,'ai-field');input.id=id;box.htmlFor=id;box.append(input);return box;};
  const select=(options,value,change)=>{const s=el('select');for(const [v,label]of options){const o=el('option',label);o.value=v;s.append(o);}s.value=value;s.addEventListener('change',()=>change(s.value));return s;};
  const input=(value,change)=>{const n=el('input');n.type='number';n.step='any';n.value=String(value);n.addEventListener('input',()=>change(n.value));return n;};
  const button=(label,id,handler,disabled=false)=>{const n=el('button',label,'button');n.type='button';n.id=id;n.setAttribute('aria-disabled',String(disabled));n.addEventListener('click',()=>{if(n.getAttribute('aria-disabled')!=='true')void handler();});return n;};
  const finiteInput=(value,lo,hi,whole=false)=>{need(String(value).trim()!=='');const n=Number(value);need(whole?integer(n,lo,hi):number(n,lo,hi));return n;};
  const valid=token=>alive&&visible&&token===epoch;
  function renderResult(value,title){
    const area=el('section','','ai-result');area.append(el('h3',title),el('p',`${value.state} · ${value.execution_mode??'실행 출처 미확인'} · 설정 revision ${value.profile_revision} · 생성 시도 ${value.attempts_used??'미확인'}`));
    if(value.error_code){const label=value.error_code==='vertex_response_auth_failed'?'인증 실패 관측':value.error_code==='vertex_response_incomplete'?'응답 미완료 관측':'실행 관측 미확정';area.append(el('p',label+' · 이번 결과의 완결을 확인하지 못했습니다. 이전 관측을 보존합니다.','ai-warning'));}
    const scroll=el('div','','ai-table-scroll'),table=el('table'),head=el('tr');for(const h of ['모델·추론','상태·사유','HTTP·완결','JSON·품질','사용량·비용','설정 근거'])head.append(el('th',h));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');
    for(const c of value.cells){const row=el('tr');row.dataset.state=c.state;row.append(el('td',`${c.model_id}\n${c.thinking_level}`),el('td',`${c.state}${c.reason_code?' · '+c.reason_code:''}`),el('td',`${c.http_status??'미전송/미확인'} · ${c.response_complete===null?'미확인':c.response_complete?'완결':'미완결'}`),el('td',`JSON ${c.strict_decode} · 업무 품질 미평가`));
      const usage=el('td',`비용 미확인\n${c.usage===null?'사용량 미제공':USAGE.map(k=>`${k}: ${c.usage[k]??'미제공'}`).join('\n')}`);row.append(usage);const source=el('td');
      if(c.settings){const details=el('details'),summary=el('summary','적용 설정 보기');details.append(summary);for(const k of ['profile_revision','model_id','thinking_level','max_output_tokens','timeout_seconds','profile_sha256','settings_sha256'])details.append(el('p',`${k}: ${c.settings[k]}`));if(c.reported_model_version!==null)details.append(el('p',`공급자 modelVersion 선언: ${c.reported_model_version}`));if(c.response_id!==null)details.append(el('p',`공급자 responseId: ${c.response_id}`));source.append(details);}else source.append(el('span','미선택 · 설정 없음'));row.append(source);body.append(row);}
    table.append(body);scroll.append(table);area.append(scroll);return area;
  }
  function paint(){
    if(!alive)return;
    const focus=document.activeElement?.id,selection=document.activeElement?.selectionStart;
    const fragment=document.createDocumentFragment(),heading=el('div','','section-heading');heading.append(el('h2','모델 연결 · Vertex AI'),el('small','등록 합성 입력 · 명시적 테스트'));fragment.append(heading);
    const status=el('p',message,'ai-status');status.id='ai-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');fragment.append(status);
    fragment.append(button('연결 상태 새로고침','ai-refresh',refresh,busy));
    if(good&&current!==good)fragment.append(el('p','이전 성공 조회 시점의 연결 상태입니다. 이번 요청의 새 확인 결과가 아닙니다.','ai-warning'));
    const state=current||good;
    if(state&&draft){
      fragment.append(el('p',`프로젝트 ${state.profile.project_id} · quota ${state.profile.quota_project_id} · aiplatform.googleapis.com · 저장 revision ${state.profile.revision}`,'ai-binding'));
      const authLabels={missing:'인증파일 준비 미확인',other_quota:'quota 불일치',access_unknown:'인증파일 준비 · 모델 접근 미확인',verified:'실제 접근 확인 관측'};
      fragment.append(el('p',`${authLabels[state.auth.state]} · 점검 ${when(state.auth.checked_at)}\n무료 체험 실행 허용 ${state.trial.state} · 확인 ${when(state.trial.checked_at)}\n최근 연결 조회의 잔여 생성 예산 ${state.budget.remaining_calls??'미확인'} / 6`));
      if(state.auth.state==='access_unknown')fragment.append(el('p','모델 접근 미확인은 첫 연결 테스트의 차단 사유가 아닙니다. 다른 준비 조건이 충족되면 테스트로 확인합니다.','inline-note'));
      if(!state.gate.run_allowed)fragment.append(el('p',state.gate.reasons.map(r=>reasonLabels[r]||r).join(' '),'ai-warning'));
      const form=el('section','','ai-profile');form.append(el('h3','모델별 저장 설정'));
      form.append(field('지역','ai-location',select(state.catalog.locations.map(x=>[x,x]),draft.location,v=>draft.location=v)),field('저장 기본 모델','ai-default-model',select(MODELS.map(x=>[x,x]),draft.selected_model,v=>draft.selected_model=v)));
      const grid=el('div','','ai-model-grid');for(const [i,model]of MODELS.entries()){const set=el('fieldset');set.append(el('legend',model));const values=draft.models[model];set.append(field('추론 수준','ai-level-'+i,select(LEVELS.map(x=>[x,x]),values.thinking_level,v=>values.thinking_level=v)),field('출력 토큰 64–8192','ai-output-'+i,input(values.max_output_tokens,v=>values.max_output_tokens=v)),field('timeout 초 1–120','ai-timeout-'+i,input(values.timeout_seconds,v=>values.timeout_seconds=v)));grid.append(set);}form.append(grid);
      const active=run&&run.state!=='finished';form.append(button('프로필 저장','ai-save',save,busy||!!active),button('저장값으로 되돌리기','ai-reset',()=>{draft=clone(state.profile);render();},busy));fragment.append(form);
      const execution=el('section','','ai-execution');execution.append(el('h3','이번 실행 override · 저장 설정과 별개'));
      execution.append(field('등록 합성 입력','ai-scenario',select(state.scenarios.map(s=>[s.scenario_id,s.label]),scenario,v=>scenario=v)),field('선택 테스트 모델','ai-run-model',select(MODELS.map(x=>[x,x]),runModel,v=>{runModel=v;runModelEdited=true;})),
        field('선택 테스트 추론 override','ai-run-level',select([['','저장값 사용'],...LEVELS.map(x=>[x,x])],overrides.thinking_level,v=>overrides.thinking_level=v)),field('출력 override · 빈칸은 저장값','ai-run-output',input(overrides.max_output_tokens,v=>overrides.max_output_tokens=v)),field('timeout override · 빈칸은 저장값','ai-run-timeout',input(overrides.timeout_seconds,v=>overrides.timeout_seconds=v)));
      const denied=busy||!!active||!current||!state.gate.run_allowed||state.profile.revision<1;
      execution.append(button('선택 모델 테스트 1회','ai-run-selected',()=>start(false),denied),button('6개 조합 비교','ai-run-matrix',()=>start(true),denied),button('실행 취소 요청','ai-cancel',cancel,busy||!active));
      execution.append(el('p','6조합은 LOW/MEDIUM/HIGH 고정입니다. 추론 override를 비운 뒤 실행하세요. 최초 묶음의 512토큰·60초 상한을 초과하면 미실행 사유로 기록하며 저장값을 자동 변경하지 않습니다.','inline-note'));fragment.append(execution);
      if(state.recent_runs.length){const history=el('div','','ai-history');history.append(el('h3','이 세션의 실행 이력'));for(const r of state.recent_runs)history.append(button(`${r.matrix?'6조합':'선택1'} · ${r.state} · ${when(r.created_at)}`,'ai-history-'+r.run_id,()=>loadRun(r.run_id),busy));fragment.append(history);}
    }
    if(run)fragment.append(renderResult(run,'현재 실행 관측'));
    if(previous&&(!run||previous.run_id!==run.run_id))fragment.append(renderResult(previous,'이전 성공 관측 · 현재 실행 결과와 별도'));
    root.replaceChildren(fragment);root.classList.add('ai-connection-panel');root.setAttribute('aria-busy',String(busy));
    if(focus){const target=root.querySelector('#'+focus);target?.focus({preventScroll:true});if(typeof selection==='number'&&target?.type==='text')target.setSelectionRange(selection,selection);}
  }
  function render(){
    try{paint();painted={good,current,run,previous,draft};}
    catch{
      stop();busy=false;
      if(painted){good=painted.good;run=painted.run;previous=painted.previous;draft=painted.draft;}
      current=null;message='화면을 준비하지 못했습니다. 이전 관측과 입력을 보존했습니다. 명시 새로고침으로 확인하세요.';
      const status=root.querySelector('#ai-status');if(status)status.textContent=message;
      for(const control of root.querySelectorAll('button'))control.setAttribute('aria-disabled',String(control.id!=='ai-refresh'));
    }
  }
  async function http(path,method='GET',body=null){
    const requestEpoch=epoch,controller=new AbortController();requests.add(controller);const timer=setTimeout(()=>controller.abort(),10000);
    try{
      const headers={};if(path!=='session'){need(csrf!==null);headers['X-AI-Connection-CSRF']=csrf;}if(body!==null)headers['Content-Type']='application/json';
      const response=await fetch(BASE+path,{method,headers,body:body===null?undefined:JSON.stringify(body),cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal});
      need(/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers.get('content-type')||''));
      const maximum=path==='session'?4096:path==='state'||path==='profile'?65536:262144;
      const declared=response.headers.get('content-length');if(declared!==null)need(/^\d+$/.test(declared)&&Number(declared)<=maximum);
      const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let size=0,raw='';
      try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>maximum){await reader.cancel();throw Error();}raw+=decoder.decode(part.value,{stream:true});}raw+=decoder.decode();}finally{reader.releaseLock();}
      need(valid(requestEpoch));
      if(!response.ok){const error=strictJSON(raw);keys(error,['error']);keys(error.error,['code']);need(typeof error.error.code==='string'&&/^ai_connection_ui_[a-z_]+$/.test(error.error.code));if(response.status===403)csrf=null;throw Error(error.error.code);}
      const kind=path==='session'?'session':path==='state'||path==='profile'?'state':'run';const value=parseDTO(raw,kind);
      if(path==='session'){
        const token=response.headers.get('x-ai-connection-csrf');need(typeof token==='string'&&SHA.test(token));
        if(sessionBinding!==null&&sessionBinding!==token){
          run=previous=null;current=null;
          if(good)good={...good,active_run_id:null,recent_runs:[]};
          if(painted)painted={...painted,current:null,good,run:null,previous:null};
        }
        sessionBinding=csrf=token;
      }
      return value;
    }finally{clearTimeout(timer);requests.delete(controller);}
  }
  function publishRun(value){
    if(run&&run.run_id===value.run_id){need(run.profile_revision===value.profile_revision&&run.scenario_id===value.scenario_id&&run.scenario_sha256===value.scenario_sha256&&run.matrix===value.matrix);
      for(let i=0;i<6;i++){const a=run.cells[i].settings,b=value.cells[i].settings;need((a===null)===(b===null));if(a)need(SETTINGS.every(k=>a[k]===b[k]));}}
    run=value;if(value.state==='finished'&&!value.error_code)previous=value;
  }
  function schedule(){clearTimeout(poll);if(alive&&visible&&run&&run.state!=='finished')poll=setTimeout(()=>void pollRun(),1000);}
  async function pollRun(){const token=epoch,id=run?.run_id;if(!id||!valid(token))return;let terminalObserved=false;
    try{const value=await http('runs/'+id);if(!valid(token)||run?.run_id!==id)return;publishRun(value);message='실행 상태를 확인했습니다.';
      if(value.state==='finished'){
        terminalObserved=true;const next=await http('state');if(!valid(token)||run?.run_id!==id)return;
        if(current&&next.profile.revision!==current.profile.revision){current=null;message='실행 기록은 확인했습니다. 설정 revision이 변경됐으니 명시 새로고침 후 입력을 대조하세요.';}
        else current=good=next;
      }
      render();schedule();}
    catch{if(valid(token)){if(terminalObserved){current=null;message='실행 기록은 확인했지만 잔여 예산·이력 조회는 미확인입니다. 명시 새로고침으로 확인하세요.';}
      else message='실행 상태를 확인하지 못했습니다. 전달·완료 여부는 미확인입니다. 명시 새로고침으로 확인하세요.';render();}}
  }
  async function refresh(){
    if(!alive||!visible)return;stop();const token=epoch;busy=true;message='연결 상태를 조회하고 있습니다.';render();if(!valid(token))return;
    try{await http('session');if(!valid(token))return;const next=await http('state');if(!valid(token))return;
      current=good=next;if(!draft||draft.revision!==next.profile.revision)draft=clone(next.profile);if(!runModelEdited)runModel=next.profile.selected_model;if(!scenario||!next.scenarios.some(s=>s.scenario_id===scenario))scenario=next.scenarios[0]?.scenario_id||'';
      if(next.active_run_id){const value=await http('runs/'+next.active_run_id);if(!valid(token))return;publishRun(value);}message='연결 상태를 조회했습니다. 모델 실행은 버튼으로 요청합니다.';
    }catch{if(valid(token)){current=null;message='연결 상태 조회 실패 · 이전 관측을 보존합니다. 기능 설정과 연결을 확인하세요.';}}
    finally{if(valid(token)){busy=false;render();schedule();}}
  }
  async function save(){
    if(busy||!current)return;let value;
    try{value=clone(draft);for(const m of MODELS){value.models[m].max_output_tokens=finiteInput(value.models[m].max_output_tokens,64,8192,true);value.models[m].timeout_seconds=finiteInput(value.models[m].timeout_seconds,1,120);}validateProfile(value);}catch{message='저장할 설정값을 확인하세요. 토큰은 정수, timeout은 유한한 초 단위 값입니다.';render();return;}
    const token=epoch;busy=true;message='프로필을 저장하고 있습니다.';render();if(!valid(token))return;
    try{const next=await http('profile','POST',{profile:value,expected_revision:current.profile.revision});if(!valid(token))return;current=good=next;draft=clone(next.profile);if(!runModelEdited)runModel=next.profile.selected_model;message='프로필을 저장했습니다. 실행 override는 저장하지 않습니다.';}
    catch(error){if(valid(token))message=error.message==='ai_connection_ui_revision_conflict'?'프로필 revision이 변경됐습니다. 입력을 보존했으니 새로고침 후 대조하세요.':'프로필 저장을 확인하지 못했습니다. 입력과 이전 관측을 보존합니다.';}
    finally{if(valid(token)){busy=false;render();}}
  }
  async function start(matrix){
    if(busy||!current||!current.gate.run_allowed||run&&run.state!=='finished')return;
    let body;try{const values={};if(overrides.thinking_level)values.thinking_level=overrides.thinking_level;if(overrides.max_output_tokens!=='')values.max_output_tokens=finiteInput(overrides.max_output_tokens,64,8192,true);if(overrides.timeout_seconds!=='')values.timeout_seconds=finiteInput(overrides.timeout_seconds,1,120);body=requestFor(current.profile,scenario,matrix?null:runModel,values,matrix);}catch{message='이번 실행 override를 확인하세요. 6조합에는 추론 override를 넣을 수 없습니다.';render();return;}
    const capturedProfile=clone(current.profile),capturedScenario=current.scenarios.find(s=>s.scenario_id===body.scenario_id),token=epoch;
    busy=true;message='명시 실행을 요청하고 있습니다.';render();if(!valid(token))return;
    try{const value=await http('run','POST',body);if(!valid(token))return;admitStart(value,body,capturedProfile);need(capturedScenario&&value.scenario_sha256===capturedScenario.input_sha256);if(run&&run.state==='finished'&&!run.error_code)previous=run;run=null;publishRun(value);message='실행 요청을 접수했습니다. 실제 호출·완료 여부는 행별 관측을 확인하세요.';}
    catch{if(valid(token)){current=null;message='실행 요청의 접수·전달 여부를 확인하지 못했습니다. 자동 재전송하지 않습니다. 명시 새로고침으로 자기 실행을 확인하세요.';}}
    finally{if(valid(token)){busy=false;render();schedule();}}
  }
  async function cancel(){if(busy||!run||run.state==='finished')return;const token=epoch,id=run.run_id;busy=true;render();if(!valid(token))return;
    try{const value=await http('cancel','POST',{run_id:id});if(!valid(token)||run?.run_id!==id)return;publishRun(value);message='취소를 요청했습니다. 이미 전송한 호출의 원격 중단·무과금은 미확인입니다.';}
    catch{if(valid(token))message='취소 요청 전달 여부가 미확인입니다. 실행 상태를 명시 조회하세요.';}
    finally{if(valid(token)){busy=false;render();schedule();}}
  }
  async function loadRun(id){if(busy)return;stop();const token=epoch;busy=true;render();if(!valid(token))return;try{const value=await http('runs/'+id);if(valid(token)){run=null;publishRun(value);message='자기 세션의 저장 실행 관측입니다.';}}catch{if(valid(token))message='선택한 실행을 조회하지 못했습니다.';}finally{if(valid(token)){busy=false;render();schedule();}}}
  const hide=()=>{if(!alive)return;visible=false;stop();busy=false;root.hidden=true;};
  const show=()=>{if(!alive)return;root.hidden=false;if(visible)return;visible=true;render();void refresh();};
  const suspend=()=>{if(!alive)return;stop();csrf=null;current=null;busy=false;message='화면 수명 변경으로 조회를 중지했습니다. 다시 표시한 뒤 명시 새로고침으로 확인하세요.';if(visible)render();};
  const pagehide=e=>{if(e.persisted)suspend();else destroy();};
  function destroy(){if(!alive)return;hide();alive=false;csrf=sessionBinding=null;current=good=run=previous=draft=null;root.replaceChildren();window.removeEventListener('pagehide',pagehide);window.removeEventListener('pageshow',suspend);}
  window.addEventListener('pagehide',pagehide);window.addEventListener('pageshow',suspend);
  return Object.freeze({show,hide,refresh,destroy});
}
