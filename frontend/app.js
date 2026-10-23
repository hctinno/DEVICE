import {FIELDS, FACT_LABELS, JOB_LABELS, describeState, factSources, filterIntakes, noticeContext, seoulTime, bytes, validateSnapshot} from './model.mjs';

const $ = selector => document.querySelector(selector);
const state = {records: [], notices: [], selected: location.hash.slice(1), loaded: false, request: 0, view: 'intakes'};
const roles = {request: '의뢰 자료', product: '제품 자료', reference: '참고 자료'};
const producerKinds = {fixture: '합성 분석 예시', manual: '수동 분석', model: '모델 분석자 선언'};
const errorMessages = {
  store_missing: '접수 저장소가 없습니다. 실행할 때 지정한 workspace를 확인하세요.',
  store_unavailable: '접수 저장소를 읽을 수 없습니다. 파일·권한·스키마 상태를 확인하세요.',
  state_invalid: '저장된 접수 상태를 해석할 수 없습니다. 상태 기록을 확인하세요.',
  unsupported_response: '화면에서 지원하지 않는 API 응답입니다.',
  invalid_snapshot: '응답의 필수 필드 또는 자료 구조가 올바르지 않아 조회 결과를 적용하지 않았습니다.',
  render_failed: '조회 결과를 화면으로 구성하지 못해 이전 상태를 유지합니다.',
};

function el(tag, className = '', text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = String(text);
  return node;
}
function badge(text, tone = 'neutral') { return el('span', `badge ${tone}`, text); }
function stateBadge(record) {
  const current = describeState(record);
  return badge(`${current.symbol} ${current.label}`, current.tone);
}
function section(title, detail) {
  const node = el('section', 'section-rule');
  const heading = el('div', 'section-heading');
  heading.append(el('h3', '', title));
  if (detail) heading.append(el('small', '', detail));
  node.append(heading);
  return node;
}
function empty(title, description) {
  const node = el('div', 'empty');
  const icon = el('span', 'empty-icon', '▤');
  icon.setAttribute('aria-hidden', 'true');
  node.append(icon, el('h2', '', title), el('p', '', description));
  return node;
}
function sources(citations) {
  const details = el('details');
  details.append(el('summary', '', `출처 ${citations.length}개 보기`));
  for (const source of citations) {
    const node = el('div', 'source');
    node.append(el('strong', '', source.path || '파일 경로 미확인'),
      el('div', '', `${roles[source.role] || `역할 미확인 (${source.role || '없음'})`} · ${source.line_start ?? '?'}–${source.line_end ?? '?'}행`),
      el('blockquote', '', source.quote || '인용문 없음'), el('p', 'mono', `SHA-256 ${source.sha256 || '없음'}`));
    details.append(node);
  }
  return details;
}
function metadata(entries) {
  const list = el('dl', 'metadata');
  for (const [label, value] of entries) {
    const item = el('div');
    item.append(el('dt', '', label), el('dd', '', value));
    list.append(item);
  }
  return list;
}

function buildMetrics(view) {
  const counts = [['전체 접수', view.records.length, '▤', ''],
    ['확인 필요', filterIntakes(view.records, {filter: 'attention'}).length, '!', 'attention'],
    ['분석 대기·분석 중', filterIntakes(view.records, {filter: 'waiting'}).length, '◷', ''],
    ['사용자 보류', filterIntakes(view.records, {filter: 'deferred'}).length, 'Ⅱ', '']];
  return counts.map(([label, value, icon, style]) => {
    const card = el('div', `metric ${style}`);
    card.append(el('p', '', label), el('strong', '', value), el('small', '', '건'));
    const symbol = el('span', 'metric-icon', icon);
    symbol.setAttribute('aria-hidden', 'true');
    card.append(symbol);
    return card;
  });
}

function buildList(view) {
  const filtered = filterIntakes(view.records, {query: $('#search').value, filter: $('#filter').value});
  const selected = filtered.some(item => item.intake_id === view.selected) ? view.selected : filtered[0]?.intake_id || '';
  const nodes = filtered.map(record => {
    const item = el('li');
    const button = el('button', 'intake-item');
    button.type = 'button';
    if (record.intake_id === selected) button.setAttribute('aria-current', 'true');
    const badges = el('div', 'item-badges');
    badges.append(stateBadge(record), badge(record.synthetic ? '합성' : '제공 자료', 'provenance'));
    button.append(badges, el('span', 'item-title', record.bundle),
      el('span', 'item-meta', `${record.source_id} · v${record.revision} · 원본 ${record.files.length}개`));
    button.addEventListener('click', () => {
      publishView(prepareView({...state, selected: record.intake_id}));
      history.replaceState(null, '', `#${encodeURIComponent(record.intake_id)}`);
      $('#detail-title')?.focus();
      $('#announcer').textContent = `${record.bundle} 상세를 표시했습니다.`;
    });
    item.append(button);
    return item;
  });
  if (!nodes.length) nodes.push(el('li', 'empty small', view.records.length ? '검색·필터 조건에 맞는 접수가 없습니다.' : '등록된 접수가 없습니다.'));
  return {nodes, selected, count: `${filtered.length} / ${view.records.length}건`};
}

function renderFacts(record) {
  const analysis = record.analysis;
  const factsSection = section('사실과 출처', '저장된 분석 · 의미 정확도 미검증');
  const facts = Object.entries(analysis?.facts || {});
  if (!facts.length) factsSection.append(el('p', 'muted', '아직 저장된 사실이 없습니다. 자료의 제품·시장을 기본값으로 채우지 않습니다.'));
  const grid = el('div', 'fact-list');
  for (const [field, fact] of facts) {
    const card = el('article', 'fact');
    const row = el('div', 'label-row');
    row.append(el('span', '', FIELDS[field] || field), badge(FACT_LABELS[fact.status] || `미지원: ${fact.status}`));
    card.append(row, el('p', 'value', fact.value));
    const citations = factSources(record, field);
    if (fact.status === 'user_confirmed') card.append(el('p', 'inline-note', `사용자 응답 이벤트: ${fact.event_id || '미확인'}`));
    else if (citations.length) card.append(sources(citations));
    else card.append(el('p', 'inline-note', '연결된 원문 근거 없음'));
    grid.append(card);
  }
  factsSection.append(grid);
  const submitted = analysis?.submitted?.facts || [];
  if (submitted.length) {
    const details = el('details', 'history');
    details.append(el('summary', '', `제출된 후보 ${submitted.length}개 · 충돌·불확실 포함`));
    for (const fact of submitted) {
      const item = el('article', 'file');
      item.append(el('strong', '', `${FIELDS[fact.field] || fact.field}: ${fact.value}`),
        el('p', 'inline-note', FACT_LABELS[fact.status] || `미지원 상태: ${fact.status}`));
      if (fact.evidence?.length) item.append(sources(fact.evidence));
      else item.append(el('p', 'inline-note', '원문 근거 없음'));
      details.append(item);
    }
    factsSection.append(details);
  }
  return factsSection;
}

function renderQuestions(record) {
  const questions = record.analysis?.questions || [];
  const node = section('누락·충돌과 다음 조건', `${questions.length}개 질문`);
  if (!record.analysis) node.append(el('p', 'muted', '분석 결과가 없어 누락·충돌을 아직 확인하지 못했습니다.'));
  else if (!questions.length) node.append(el('p', 'muted', '저장된 분석의 열린 질문이 없습니다. 시험 준비 완료를 뜻하지 않습니다.'));
  const list = el('div', 'question-list');
  for (const question of questions) {
    const item = el('article', 'question');
    const type = question.key.startsWith('conflict_') ? '충돌' : question.key.startsWith('missing_') ? '누락'
      : question.key === 'unread_documents' ? '해석 미지원' : '확인 필요';
    item.append(badge(type, 'warning'), el('p', '', question.message));
    const values = question.values || question.paths || [];
    if (values.length) {
      const entries = el('ul');
      for (const value of values) entries.append(el('li', '', value));
      item.append(entries);
    }
    item.append(el('p', 'inline-note', `질문 코드: ${question.key}`));
    list.append(item);
  }
  node.append(list, el('p', 'inline-note', '이 화면은 질문 조회만 제공합니다. 답변·보류 변경은 아직 연결되지 않았습니다.'));
  return node;
}

function renderFiles(record) {
  const node = section('원본과 자료 버전', '저장된 메타데이터 · 바이너리 열기 미연결');
  for (const revision of [...record.history].reverse()) {
    const details = el('details', 'history');
    details.open = revision.revision === record.revision;
    details.append(el('summary', '', `v${revision.revision}${revision.revision === record.revision ? ' · 현재 버전' : ' · 이전 버전'} · ${revision.files.length}개 · ${seoulTime(revision.created_at)} KST`));
    for (const file of revision.files) {
      const item = el('div', 'file');
      item.append(el('strong', '', `${file.path} · ${bytes(file.bytes)}`), el('span', 'mono', `SHA-256 ${file.sha256}`));
      details.append(item);
    }
    node.append(details);
  }
  return node;
}

function renderJobs(record) {
  const node = section('분석 작업', '분석 완료 ≠ 시험 완료');
  if (!record.jobs.length) { node.append(el('p', 'muted', '저장된 분석 작업이 없습니다.')); return node; }
  const table = el('table', 'data-table');
  const head = el('thead');
  const header = el('tr');
  for (const name of ['작업 / 버전', '상태 / 시도', '오류 / 임대 만료']) header.append(el('th', '', name));
  head.append(header);
  const body = el('tbody');
  for (const job of [...record.jobs].reverse()) {
    const row = el('tr');
    const first = el('td'); first.append(el('p', 'mono', job.job_id), el('p', '', `v${job.revision}${job.revision === record.revision ? ' · 현재' : ' · 이전'}`));
    const second = el('td'); second.append(el('p', '', JOB_LABELS[job.state] || `미지원: ${job.state}`), el('p', '', `${job.attempt}회 시도`));
    const third = el('td'); third.append(el('p', '', job.error_code || '기록된 오류 없음'), el('p', '', job.lease_until == null ? '임대 기록 없음' : `${seoulTime(job.lease_until)} KST`));
    row.append(first, second, third); body.append(row);
  }
  table.append(head, body);
  const scroll = el('div', 'table-scroll'); scroll.append(table); node.append(scroll);
  return node;
}

function noticeNode(notice, includeLink, view) {
  const record = view.records.find(item => item.intake_id === notice.intake_id);
  const node = el('article', 'notice');
  const header = el('div', 'notice-meta');
  header.append(badge(`기록 #${notice.notification_id}`), el('span', '', `${record?.bundle || notice.intake_id} · v${notice.revision}`),
    el('span', 'muted', noticeContext(notice, record).label));
  node.append(header);
  const payload = notice.payload || {};
  node.append(el('p', '', `생성 당시: ${describeState({status: 'analyzed', analysis: payload}).label}`));
  if (payload.questions?.length) {
    const list = el('ul', 'notice-questions');
    for (const question of payload.questions) list.append(el('li', '', question.message));
    node.append(list);
  }
  node.append(el('p', 'inline-note', '로컬 기록 · 외부 전송/읽음 여부 없음 · 현재 상세 상태와 다를 수 있음'));
  if (includeLink && record) {
    const button = el('button', 'button', '현재 접수 보기'); button.type = 'button';
    button.addEventListener('click', () => {
      $('#search').value = ''; $('#filter').value = 'all';
      changeView('intakes'); publishView(prepareView({...state, selected: record.intake_id})); $('#detail-title')?.focus();
    }); node.append(button);
  }
  return node;
}

function buildDetail(view) {
  const record = view.records.find(item => item.intake_id === view.selected);
  if (!record) {
    return [empty(view.records.length ? '표시할 접수가 없습니다' : '첫 접수를 기다리고 있습니다', view.records.length
      ? '검색어 또는 상태 필터를 변경하세요.' : '등록된 접수 자료가 없습니다. 기존 접수 서비스로 자료가 저장되면 새로고침하여 확인할 수 있습니다.')];
  }
  const current = describeState(record);
  const header = el('header', 'detail-header');
  const kicker = el('div', 'detail-kicker'); kicker.append(stateBadge(record), badge(record.synthetic ? '합성 자료 · 개발 검증용' : '제공 자료 · 실측 미확인', 'provenance'));
  const title = el('h2', '', record.bundle); title.id = 'detail-title'; title.tabIndex = -1;
  header.append(kicker, title, el('p', 'mono detail-id', `${record.intake_id} · revision ${record.revision}`));
  const body = el('div', 'detail-body');
  const note = el('div', `state-note ${current.tone}`); note.append(el('strong', '', current.label), el('p', '', current.hint));
  const producer = record.analysis?.submitted?.producer;
  body.append(note, metadata([
    ['입력 출처', record.source_id], ['자료 버전', `v${record.revision} · ${record.files.length}개 파일`],
    ['접수 진행 위임', record.delegated ? '저장됨 · 접수 업무 한정' : '저장된 위임 없음'],
    ['분석 출처', producer ? `${producerKinds[producer.kind] || producer.kind} · ${producer.name}` : '분석 전'],
    ['시료 · 물리 위치', '제공 안 됨'], ['실측 지원', `미검증 (${record.measurement_support})`],
    ['접수 / 후속 상태 코드', `${record.status} / ${record.analysis?.next_action || '없음'}`],
    ['보류 의사', record.deferred ? '저장됨' : '저장된 보류 없음'],
  ]), renderFacts(record), renderQuestions(record), renderJobs(record), renderFiles(record));
  const notices = section('이 접수의 알림 기록', '전송·읽음 상태 미제공');
  const related = view.notices.filter(notice => notice.intake_id === record.intake_id);
  if (!related.length) notices.append(el('p', 'muted', '저장된 알림이 없습니다.'));
  else for (const notice of [...related].reverse()) notices.append(noticeNode(notice, false, view));
  body.append(notices);
  return [header, body];
}

function buildNotifications(view) {
  const heading = el('div', 'section-heading'); heading.append(el('h2', '', '저장된 알림 기록'), el('small', '', `${view.notices.length}개`));
  const nodes = [heading, el('p', 'muted', '알림 생성 당시의 기록입니다. 조회로 읽음 처리하거나 외부에 발송하지 않습니다.')];
  if (!view.notices.length) nodes.push(empty('알림 기록이 없습니다', '분석 결과로 생성된 로컬 알림이 여기에 표시됩니다.'));
  else for (const notice of [...view.notices].reverse()) nodes.push(noticeNode(notice, true, view));
  return nodes;
}

function prepareView(next) {
  // Build every panel off-DOM before committing either DOM or application state.
  const list = buildList(next);
  const view = {...next, selected: list.selected};
  return {view, list, metrics: buildMetrics(view), detail: buildDetail(view), notifications: buildNotifications(view)};
}

function publishView(prepared) {
  $('#metrics').replaceChildren(...prepared.metrics);
  $('#intake-list').replaceChildren(...prepared.list.nodes);
  $('#detail-panel').replaceChildren(...prepared.detail);
  $('#notification-view').replaceChildren(...prepared.notifications);
  $('#result-count').textContent = prepared.list.count;
  $('#notice-count').textContent = prepared.view.notices.length;
  $('#last-updated').textContent = prepared.view.updatedText;
  Object.assign(state, prepared.view);
}

function changeView(view) {
  state.view = view;
  $('#intake-view').hidden = view !== 'intakes'; $('#notification-view').hidden = view !== 'notifications';
  $('#page-title').textContent = view === 'intakes' ? '접수 운영' : '알림 기록';
  for (const button of document.querySelectorAll('[data-view]')) {
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
}

async function refresh() {
  const request = ++state.request;
  state.controller?.abort();
  const controller = new AbortController(); state.controller = controller;
  const timer = setTimeout(() => controller.abort(), 10000);
  $('#refresh').disabled = true; $('#refresh').textContent = '조회 중…';
  $('#intake-view').setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/api/intakes', {signal: controller.signal, cache: 'no-store'});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.code || 'store_unavailable');
    validateSnapshot(payload);
    if (request !== state.request) return;
    let prepared;
    try { prepared = prepareView({...state, records: payload.intakes, notices: payload.notifications, loaded: true,
      updatedText: `${seoulTime(payload.generated_at)} KST 조회`}); }
    catch { throw new Error('render_failed'); }
    publishView(prepared);
    $('#error-banner').hidden = true;
    $('#announcer').textContent = `접수 ${state.records.length}건을 조회했습니다.`;
  } catch (error) {
    if (request !== state.request) return;
    const message = Object.hasOwn(errorMessages, error.message) ? errorMessages[error.message]
      : '서버 연결 또는 응답을 확인할 수 없습니다. 서버 실행 상태를 확인하고 다시 시도하세요.';
    const banner = $('#error-banner');
    banner.replaceChildren(el('strong', '', '조회 실패'), el('p', '', message),
      el('p', 'inline-note', state.loaded ? '아래 내용은 마지막 성공 조회 시점의 기록입니다. 최신 상태가 아닐 수 있습니다.' : '저장소가 비었다는 뜻이 아닙니다. 접수 건수를 확인하지 못했습니다.'));
    const retry = el('button', 'button', '다시 조회'); retry.type = 'button'; retry.addEventListener('click', refresh);
    if (error.message === 'invalid_snapshot') banner.append(el('p', 'inline-note', `응답 필드: ${error.path}`));
    banner.append(retry); banner.hidden = false;
    if (!state.loaded) {
      $('#result-count').textContent = '조회 불가'; $('#metrics').replaceChildren();
      $('#intake-list').replaceChildren(el('li', 'empty small', '목록 조회 실패'));
      $('#detail-panel').replaceChildren(empty('접수를 읽지 못했습니다', message));
    }
  } finally {
    clearTimeout(timer);
    if (request === state.request) {
      $('#refresh').disabled = false; $('#refresh').textContent = '↻ 새로고침';
      $('#intake-view').setAttribute('aria-busy', 'false');
    }
  }
}

function renderFilteredIntakes() {
  if (!state.loaded) return;
  publishView(prepareView(state));
}
$('#search').addEventListener('input', renderFilteredIntakes);
$('#filter').addEventListener('change', renderFilteredIntakes);
$('#refresh').addEventListener('click', refresh);
for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => changeView(button.dataset.view));
refresh();
