import {parseVirtualSupport, safeSourceURL, ACCESS_LABELS, SCOPE_LABELS, RESEARCH_LABELS, CANDIDATE_LABELS} from './model.mjs';

const $=selector=>document.querySelector(selector);
const node=(tag,text,className)=>{const value=document.createElement(tag);if(text!==undefined)value.textContent=text;if(className)value.className=className;return value;};
const add=(parent,...children)=>{parent.append(...children);return parent;};
const tags=(...labels)=>add(node('div',undefined,'tags'),...labels.map(label=>node('span',label,'tag')));
const section=(title,...children)=>add(node('section',undefined,'section'),node('h3',title),...children);
const para=text=>node('p',text,'literal');
const kv=(label,value)=>add(node('div',undefined,'kv'),node('dt',label),node('dd',value));
let snapshot=null,selected=null,request=0;

function showProfile(row){
  selected=row.profile_id;
  for(const button of $('#profiles').querySelectorAll('button'))button.setAttribute('aria-current',String(button.dataset.profileId===selected));
  const detail=$('#detail');detail.replaceChildren();detail.dataset.profileId=row.profile_id;
  add(detail,node('h2',row.model),para(row.manufacturer),tags('가상 역할',row.virtual_role.status==='declared'?'역할 동작 선언 있음':'역할 동작 선언 미확인','프로토콜 계약 미확인'));
  const facts=node('dl');add(facts,kv('프로필',row.profile_id),kv('역할',row.role),kv('변형',row.variant||'별도 표기 없음'));detail.append(facts);
  const material=section('1. 자료와 후보 관계',para(CANDIDATE_LABELS[row.materials.candidate_status]),para('설치 장비 결박 미확정 · 자료 후보를 장비 지원으로 확정하지 않습니다.'));
  if(!row.materials.candidates.length)material.append(para('이 고정 자료 스냅샷에서 연결된 텍스트 후보가 없습니다.'));
  for(const candidate of row.materials.candidates){
    const card=add(node('article',undefined,'source'),node('h4',`${candidate.manufacturer} · ${candidate.model}`),para(`${candidate.item_id} · ${SCOPE_LABELS[candidate.scope]} · ${RESEARCH_LABELS[candidate.research_status]}`));
    if(!candidate.sources.length)card.append(para('이 후보에 연결된 공개 출처 URL은 없습니다.'));
    for(const source of candidate.sources){
      const link=node('a',source.url,'source-url');link.href=safeSourceURL(source.url);link.target='_blank';link.rel='noopener noreferrer';
      add(card,para(`${ACCESS_LABELS[source.access]} · 모델 대응: ${source.match_level}`),link);
    }
    material.append(card);
  }
  detail.append(material);
  const role=section('2. 가상 역할 동작 선언',para(row.virtual_role.status==='declared'?'지원 선언 · 가상 역할 동작에 한정':'미확인 · 연결된 역할 동작 선언 없음'),para('아래 이름은 역할 동작입니다. 이 모델의 SCPI 명령 전체나 실행 검증을 뜻하지 않습니다.'));
  role.dataset.support=row.virtual_role.status==='declared'?'declared':'unknown';
  role.append(tags(...row.virtual_role.action_names));detail.append(role);
  const protocol=section('3. 장비별 프로토콜 계약',para('미확인 · not_assessed'),para('이 프로필에 연결된 순수 프로토콜 계약을 이 화면에서 확인하지 못했습니다. 코드 존재 여부 전체를 판정한 상태가 아닙니다.'));
  protocol.dataset.support='unknown';detail.append(protocol);
  detail.append(section('4. 검수 근거와 실장비',para('가상 검수: 이 화면에 연결된 검수 근거 미확인 (not_assessed). 기존 코드의 독립 검증 유무 전체를 단정하지 않습니다.'),para('실장비 미검증 · 실행 권한 없음')));
  const evidence=node('details',undefined,'section');evidence.append(node('summary',`프로필 출처 · 근거 ${row.evidence_refs.length}곳`));
  for(const ref of row.evidence_refs){
    const locator=ref.kind==='docx_table'?`표 ${ref.table} · 행 ${ref.row}${ref.part?' · '+ref.part:''}`:`PDF ${ref.page}쪽`;
    evidence.append(node('p',`${locator} · SHA-256 ${ref.sha256}`,'mono'));
  }
  detail.append(evidence);
}
function filterProfiles(){
  if(!snapshot)return;
  const query=$('#search').value.trim().toLocaleLowerCase('ko-KR');
  const rows=snapshot.profiles.filter(row=>[row.model,row.manufacturer,row.role,row.profile_id].some(value=>value.toLocaleLowerCase('ko-KR').includes(query)));
  $('#shown').textContent=`${rows.length} / ${snapshot.profile_count} 프로필`;
  const list=$('#profiles');list.replaceChildren();
  for(const row of rows){
    const button=node('button',undefined,'item-button');button.type='button';button.dataset.profileId=row.profile_id;
    button.setAttribute('aria-current',String(row.profile_id===selected));
    add(button,node('strong',row.model),node('small',`${row.manufacturer} · ${row.role}`));
    button.addEventListener('click',()=>showProfile(row));list.append(add(node('li'),button));
  }
  if(rows.length)showProfile(rows.find(row=>row.profile_id===selected)||rows[0]);
  else{$('#detail').replaceChildren(para('검색된 프로필이 없습니다.'));delete $('#detail').dataset.profileId;}
}
function showContracts(){
  $('#contracts').replaceChildren();
  for(const contract of snapshot.adapter_contracts){
    const card=add(node('article',undefined,'profile'),node('h3',`${contract.model} · 별도 제한 계약`),para(`프로필 ${contract.profile_id} · N1911A 카탈로그 프로필과 다른 모델·계약입니다.`));
    const supported=para(`지원 선언 · ${contract.commands.length}개 단일 명령 · ${contract.synthetic_input} 입력 / window ${contract.window} · ${contract.units.join(' / ')}`);supported.dataset.support='declared';card.append(supported);
    const commands=node('ul');commands.id='protocol-commands';for(const command of contract.commands)commands.append(node('li',command,'mono'));card.append(commands);
    const unsupported=para(`명시 범위 밖 · 미지원: ${contract.synthetic_input} 입력과 window ${contract.window} 이외의 입력·window`);unsupported.dataset.support='unsupported';card.append(unsupported);
    const unknown=para('미확인 · not_assessed: 센서 호환성, 교정, 펌웨어, 옵션, 실장비 지원');unknown.dataset.support='unknown';card.append(unknown);
    add(card,para('이 항목은 등록된 합성 계약의 선언입니다. 현재 배치·실행된 장비 상태나 runtime 실증을 뜻하지 않습니다.'),node('p',`${contract.source.document} · Edition ${contract.source.edition} · ${contract.source.date} · SHA-256 ${contract.source.sha256}`,'mono'));
    $('#contracts').append(card);
  }
}
async function load(){
  const generation=++request;snapshot=null;$('#search').disabled=true;$('#status').textContent='고정 자료를 조회합니다.';
  $('#metrics').replaceChildren();$('#profiles').replaceChildren();$('#detail').replaceChildren();delete $('#detail').dataset.profileId;
  $('#contracts').replaceChildren();$('#shown').textContent='';$('#provenance').textContent='자료 출처를 확인하고 있습니다.';
  try{
    const response=await fetch('/api/virtual-support',{cache:'no-store',credentials:'same-origin',headers:{Accept:'application/json'}});
    if(!response.ok)throw Error('unavailable');
    const value=parseVirtualSupport(await response.text());if(generation!==request)return;
    snapshot=value;
    for(const [number,label] of [[String(value.profile_count),'카탈로그 프로필 · 완성률 아님'],[String(value.adapter_contracts.length),'별도 제한 계약'],['미확인','이 화면에 연결된 검수 근거'],['없음','실행 권한 · 실장비 미검증']])
      $('#metrics').append(add(node('div',undefined,'metric'),node('strong',number),node('span',label)));
    $('#search').disabled=false;filterProfiles();showContracts();
    $('#status').textContent='조회 완료 · 호스트에 고정한 선언 스냅샷 · 실장비 상태 아님';
    $('#provenance').textContent=`자료 조사 source commit: ${value.provenance.material_source_commit} (실행 feature 코드 버전과 별개) · 카탈로그 ${value.provenance.catalog_path} · SHA-256 ${value.provenance.catalog_sha256}`;
  }catch{
    if(generation!==request)return;
    $('#status').textContent='지원 범위를 조회할 수 없습니다. 고정 자료와 응답 형식을 확인하세요.';
    $('#provenance').textContent='현재 응답을 확인하지 못해 이전 표시를 제거했습니다.';
  }
}
$('#search').addEventListener('input',filterProfiles);$('#reload').addEventListener('click',load);load();
