import {validateSnapshot, parseParameters, describeStatus, layoutTopology, summarizeProfiles, stringify, seoulTime} from './model.mjs';
import {validateHarnessResponse, describeHarnessResult, requireSameReport} from './harness_model.mjs';

const $ = selector => document.querySelector(selector);
const el = (tag, className = '', text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
};
const add = (parent, ...children) => {for (const child of children.flat()) if (child) parent.append(child); return parent;};
const button = (text, className = '') => {const node = el('button', className, text); node.type = 'button'; return node;};
const id = (node, value) => {node.id = value; return node;};
const ROLE_LABELS = {power_supply: 'DC 전원', temperature_chamber: '항온·항습', dut: '시험 시료', attenuator: 'RF 감쇠', rf_switch: 'RF 경로 제어', power_meter: '전력 측정'};
const KIND_LABELS = {report_equipment: '보고서 장비', dut_context: 'DUT 문맥', auxiliary: '보조 프로필', context: '문맥 프로필', fixture: '합성 fixture'};
const ACTION_LABELS = {configure: '구성', set_output: '전원 출력 설정', set_transmit: '송신 설정', set_attenuation: '감쇠 설정', set_temperature: '온도 설정', select_path: 'RF 경로 선택', start: '시작', cancel: '취소', recover: '복구'};
let snapshot = null, selected = null, busy = false, pending = null, query = '', roleFilter = '';
const actionSelection = new Map(), history = [];
let harnessReport = null, harnessHasSuccess = false, harnessLoadSequence = 0;
const profileFor = (data, device) => data.catalog.profiles.find(profile => profile.profile_id === device.profile_id);

function badge(status) {
  const state = describeStatus(status);
  return el('span', `badge ${state.tone}`, `${state.symbol} ${state.label}`);
}

function heading(kicker, title, note) {
  return add(el('div', 'section-heading'), add(el('div'), el('p', 'eyebrow', kicker), el('h2', '', title)), note ? el('p', 'muted', note) : null);
}

function detail(label, value) {
  return add(el('div', 'detail-row'), el('dt', '', label), el('dd', '', stringify(value ?? '미제공')));
}

function jsonDetails(title, value, className = '') {
  return add(el('details', className), el('summary', '', title), el('pre', 'json', stringify(value)));
}

function renderHero(data) {
  const input = id(el('input'), 'advance-ticks');
  Object.assign(input, {type: 'number', min: '1', max: '1000', step: '1', value: $('#advance-ticks')?.value || '1'});
  const run = id(button('시간 진행 →', 'primary'), 'advance'); run.dataset.mutation = '';
  const label = el('label', '', '진행할 가상 tick'); label.htmlFor = 'advance-ticks';
  return add(el('section', 'hero'), add(el('div'), el('p', 'eyebrow', 'DGM AUTOLAB / VIRTUAL OPERATIONS'), el('h1', '', '가상 시험소'),
    el('p', '', data.runtime_kind === 'synthetic_fixture' ? `${data.topology.devices.length}개 합성 노드로 화면·상태 전이를 검증하는 fixture입니다.` : '주입된 가상 런타임의 장비·연결·운영자 동작을 조회합니다.')),
    add(el('div', 'advance-control'), label, add(el('div'), input, run), el('small', 'muted', '실제 경과 시간과 별개 · 자동 진행 없음')));
}

function renderMetrics(data) {
  const counts = summarizeProfiles(data);
  const observations = Object.values(data.observations.devices);
  const attention = observations.filter(node => ['invalid', 'error', 'disconnected', 'unsupported'].includes(node.status)).length;
  const pendingCount = observations.filter(node => node.status === 'pending').length;
  const cards = [
    ['등록 프로필', counts.profiles, 'profiles', `${counts.roles}개 역할 · 실행 검증 수와 별도`],
    ['배치 장비', counts.deployed, 'devices', `${counts.undeployed}개 프로필 미배치 · 물리 수량 아님`],
    ['관측 주의', attention, 'attention', `${pendingCount}개 진행 대기 · 원인/복구 확인`],
    ['가상 시간', data.observations.tick, 'tick', `tick · 설정 revision ${data.observations.setup_revision}`],
  ];
  return add(el('section', 'metrics'), cards.map(([label, value, metric, hint]) => {
    const number = el('strong', '', value); number.dataset.metric = metric;
    return add(el('article', `metric ${metric === 'attention' && attention ? 'warning-metric' : ''}`), el('p', '', label), number, el('small', '', hint));
  }));
}

const NS = 'http://www.w3.org/2000/svg';
function svg(tag, attributes = {}, text) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderMap(data, selection) {
  const panel = id(el('section', 'panel topology-panel'), 'topology');
  add(panel, heading('VIRTUAL TOPOLOGY', '연결과 상태', '노드를 선택해 관측·동작·근거를 확인하세요.'));
  const legend = el('div', 'legend');
  for (const [kind, label] of [['rf', 'RF 신호'], ['power', '전원'], ['environment', '환경'], ['control', '제어 / 데이터']]) add(legend, el('span', `legend-${kind}`, label));
  add(panel, legend);
  if (!data.topology.devices.length) return add(panel, el('div', 'empty-state', '배치된 가상 장비가 없습니다. 전체 프로필과 실행 검증 상태를 아래에서 확인하세요.'));
  const layout = layoutTopology(data.topology);
  const width = Math.max(670, (Math.max(...layout.map(node => node.column)) + 1) * 184 + 28);
  const height = Math.max(250, (Math.max(...layout.map(node => node.row)) + 1) * 112 + 52);
  const graph = svg('svg', {viewBox: `0 0 ${width} ${height}`, width, height, role: 'group', 'aria-label': '가상 장비 연결도'});
  const positions = new Map(layout.map(node => [node.id, {x: 20 + node.column * 184, y: 28 + node.row * 112}]));
  const defs = svg('defs');
  const marker = svg('marker', {id: 'arrow', viewBox: '0 0 8 8', refX: 7, refY: 4, markerWidth: 6, markerHeight: 6, orient: 'auto-start-reverse'});
  add(marker, svg('path', {d: 'M 0 0 L 8 4 L 0 8 z', class: 'arrow'})); add(defs, marker); add(graph, defs);
  for (const edge of data.topology.connections) {
    const start = positions.get(edge.source.device_id), end = positions.get(edge.target.device_id);
    const type = ['rf', 'power', 'environment', 'position'].includes(edge.kind) ? edge.kind : 'control';
    const x1 = start.x + 156, y1 = start.y + 40, x2 = end.x, y2 = end.y + 40;
    const path = svg('path', {d: `M ${x1} ${y1} C ${x1 + 18} ${y1}, ${x2 - 18} ${y2}, ${x2} ${y2}`, class: `edge edge-${type}`, 'marker-end': 'url(#arrow)'});
    add(path, svg('title', {}, `${edge.source.device_id}.${edge.source.port} → ${edge.target.device_id}.${edge.target.port} · ${edge.kind}`)); add(graph, path);
  }
  for (const node of layout) {
    const profile = profileFor(data, node), observation = data.observations.devices[node.id], status = describeStatus(observation.status), point = positions.get(node.id);
    const group = svg('g', {transform: `translate(${point.x} ${point.y})`, class: `map-node ${selection === node.id ? 'selected' : ''} ${status.tone}`, role: 'button', tabindex: 0, 'data-device': node.id,
      'aria-label': `${node.id} · ${profile.model} · ${status.label}`, 'aria-pressed': selection === node.id});
    add(group, svg('title', {}, `${profile.model} / ${profile.role}`), svg('rect', {width: 156, height: 80, rx: 9}),
      svg('text', {x: 12, y: 21, class: 'node-id'}, node.id.length > 20 ? node.id.slice(0, 18) + '…' : node.id),
      svg('text', {x: 12, y: 41, class: 'node-model'}, (ROLE_LABELS[profile.role] || profile.role).slice(0, 22)),
      svg('text', {x: 12, y: 64, class: 'node-status'}, `${status.symbol} ${status.label}`));
    add(graph, group);
  }
  add(panel, add(el('div', 'map-scroll'), graph));
  const list = el('div', 'device-list');
  for (const device of data.topology.devices) {
    const profile = profileFor(data, device), observation = data.observations.devices[device.id];
    const item = button('', `device-item ${selection === device.id ? 'selected' : ''}`);
    item.dataset.device = device.id; item.setAttribute('aria-pressed', String(selection === device.id));
    add(item, add(el('span'), el('strong', '', device.id), el('small', '', profile.model)), badge(observation.status));
    add(list, item);
  }
  add(panel, list, jsonDetails(`포트 연결 ${data.topology.connections.length}개 · 연결 형식 보기`, data.topology.connections, 'connection-details'));
  return panel;
}

function renderInspector(data, selection) {
  const panel = id(el('aside', 'panel inspector'), 'inspector');
  if (!selection) return add(panel, heading('DEVICE INSPECTOR', '장비 선택'), el('p', 'empty-state', '장비를 선택하면 운영자 동작과 관측을 표시합니다.'));
  const device = data.topology.devices.find(item => item.id === selection), profile = profileFor(data, device), observation = data.observations.devices[selection];
  add(panel, el('p', 'eyebrow', `DEVICE / ${selection}`), id(el('h2', '', profile.model), 'device-title'), el('p', 'muted mono', profile.role),
    add(el('div', 'status-row'), badge(observation.status), el('span', 'state-code', stringify(observation.state ?? 'state 미제공'))),
    el('p', 'revision-line', `tick ${observation.tick} · 설정 revision ${observation.setup_revision} · 합성 관측`));
  const values = id(el('dl', 'observation-values'), 'observation-values');
  for (const [name, value] of Object.entries(observation.values)) add(values, detail(name, value));
  if (!Object.keys(observation.values).length) add(values, el('p', 'muted', '관측 값 없음 · 누락을 0으로 대체하지 않습니다.'));
  add(panel, el('h3', '', '현재 관측'), values);
  const actions = data.role_actions[profile.role] || {};
  add(panel, el('div', 'panel-divider'), el('h3', '', '운영자 가상 동작'));
  if (!Object.keys(actions).length) add(panel, el('p', 'empty-state', '선언된 운영자 동작이 없습니다. 동작 지원과 실행 검증을 확인하세요.'));
  else {
    const action = Object.hasOwn(actions, actionSelection.get(selection)) ? actionSelection.get(selection) : Object.keys(actions)[0];
    actionSelection.set(selection, action);
    const form = id(el('form', 'action-form'), 'action-form');
    const label = el('label', '', '동작'); label.htmlFor = 'action-select';
    const select = id(el('select'), 'action-select');
    for (const name of Object.keys(actions)) {
      const option = el('option', '', `${Object.hasOwn(ACTION_LABELS, name) ? ACTION_LABELS[name] + ' · ' : ''}${name}`);
      option.value = name; option.selected = name === action; add(select, option);
    }
    add(form, label, select);
    for (const [name, schema] of Object.entries(actions[action].parameters)) {
      const field = el('div', 'field'), fieldLabel = el('label', '', `${name}${schema.unit ? ` (${schema.unit})` : ''} · ${schema.required ? '필수' : '선택'}`);
      fieldLabel.htmlFor = `parameter-${name}`;
      let input;
      if (schema.type === 'boolean' || schema.enum) {
        input = el('select'); add(input, el('option', '', '선택하세요')); input.firstChild.value = '';
        for (const value of schema.enum || [true, false]) {const option = el('option', '', String(value)); option.value = String(value); add(input, option);}
      } else if (['object', 'array'].includes(schema.type)) {
        input = el('textarea'); input.rows = 3; input.placeholder = schema.type === 'array' ? 'JSON array: [1, 2]' : 'JSON object: {"key": "value"}';
      } else {
        input = el('input'); input.type = ['number', 'integer'].includes(schema.type) ? 'number' : 'text';
        if (input.type === 'number') {input.step = schema.type === 'integer' ? '1' : 'any'; if (schema.minimum !== undefined) input.min = schema.minimum; if (schema.maximum !== undefined) input.max = schema.maximum;}
      }
      input.id = `parameter-${name}`; input.dataset.parameter = name; input.autocomplete = 'off';
      add(form, add(field, fieldLabel, input));
    }
    add(form, el('p', 'completion-note', `완료 조건: ${actions[action].completion || '선언 미제공'}`));
    const run = id(el('button', 'primary', '가상 동작 실행'), 'run-action'); run.type = 'submit'; run.dataset.mutation = '';
    add(form, run, el('p', 'muted small', '선언된 가상 동작만 실행합니다. 가상 진행은 위의 tick으로 제어합니다.')); add(panel, form);
  }
  add(panel, jsonDetails('장비 프로필 · 지원 범위 · 근거', {profile_id: profile.profile_id, profile_kind: profile.profile_kind ?? '미제공', variant: profile.variant,
    simulation_basis: profile.simulation_basis, capability_scope: profile.capability_scope, evidence_refs: profile.evidence_refs, ports: profile.ports}));
  return panel;
}

function renderCatalogBody(data) {
  const body = el('tbody');
  const deployed = new Set(data.topology.devices.map(device => device.profile_id));
  const profiles = data.catalog.profiles.filter(profile => (!roleFilter || profile.role === roleFilter)
    && [profile.profile_id, profile.model, profile.manufacturer, profile.role, stringify(profile.variant ?? '')].join(' ').toLocaleLowerCase('ko').includes(query.trim().toLocaleLowerCase('ko')));
  for (const profile of profiles) {
    const record = el('tr');
    add(record, add(el('td'), el('strong', '', profile.model), el('small', 'mono', profile.profile_id), el('small', 'muted', profile.manufacturer)),
      add(el('td'), el('span', 'mono', profile.role), el('small', '', Object.hasOwn(KIND_LABELS, profile.profile_kind) ? KIND_LABELS[profile.profile_kind] : profile.profile_kind || '분류 미제공'), el('small', 'muted', stringify(profile.variant ?? '변형 미제공'))),
      add(el('td'), el('span', `deploy-badge ${deployed.has(profile.profile_id) ? 'deployed' : ''}`, deployed.has(profile.profile_id) ? '배치됨' : '미배치'),
        el('small', 'muted', `운영자 동작 ${Object.keys(data.role_actions[profile.role] || {}).length}개 · 실행 검증 별도`)),
      add(el('td'), el('p', 'scope', stringify(profile.capability_scope ?? '지원 범위 미제공')), jsonDetails(`근거 ${profile.evidence_refs?.length || 0}건 · 지원 동작`, {
        simulation_basis: profile.simulation_basis ?? '미제공', evidence_refs: profile.evidence_refs ?? [], operator_actions: data.role_actions[profile.role] || {}, hardware_verified: false})));
    add(body, record);
  }
  if (!profiles.length) {const cell = el('td', 'empty-state', data.catalog.profiles.length ? '검색 결과가 없습니다.' : '등록된 가상 프로필이 없습니다.'); cell.colSpan = 4; add(body, add(el('tr'), cell));}
  body.id = 'catalog-body';
  return body;
}

function renderCatalog(data) {
  const section = id(el('section', 'panel catalog-panel'), 'catalog');
  add(section, heading('CATALOG / SUPPORT / EVIDENCE', '전체 프로필', '등록 수는 구현 완료·물리 장비 수·실행 검증 수가 아닙니다.'));
  const search = id(el('input'), 'catalog-search'); search.type = 'search'; search.value = query; search.placeholder = '모델·역할·프로필 검색';
  const searchLabel = el('label', 'sr-only', '모델·역할·프로필 검색'); searchLabel.htmlFor = 'catalog-search';
  const select = id(el('select'), 'catalog-role'); select.setAttribute('aria-label', '프로필 역할 필터');
  const all = el('option', '', '전체 역할'); all.value = ''; add(select, all);
  for (const role of [...new Set(data.catalog.profiles.map(profile => profile.role))].sort()) {const option = el('option', '', role); option.value = role; option.selected = roleFilter === role; add(select, option);}
  add(section, add(el('div', 'catalog-tools'), searchLabel, search, select));
  const table = el('table'); add(table, add(el('thead'), add(el('tr'), ['모델 / 프로필', '역할 / 구분', '배치 / 동작 지원', '지원 범위 / 근거'].map(title => el('th', '', title)))), renderCatalogBody(data));
  add(section, add(el('div', 'table-scroll'), table), jsonDetails('runtime coverage 원문 · 실행 검증 상태 확인', data.coverage),
    el('p', 'muted small', `catalog: ${data.catalog.catalog_id || 'ID 미제공'} · 근거: ${data.catalog.source_basis || '미제공'} · 실장비 검증 없음`));
  return section;
}

function renderHistory() {
  const section = id(el('section', 'panel history-panel'), 'history');
  add(section, heading('OPERATOR REQUEST LOG', '실행 이력', '현재 브라우저 세션의 최근 100개 요청 · 원시 측정 기록과 별도'));
  if (!history.length) return add(section, el('p', 'empty-state', '아직 운영자 가상 동작을 요청하지 않았습니다.'));
  const list = el('ol', 'history-list');
  for (const item of [...history].reverse()) {
    add(list, add(el('li'), add(el('div', 'history-line'), el('time', 'mono', `${seoulTime(item.at)} KST`), el('strong', '', item.label), el('span', 'muted', item.outcome)),
      jsonDetails(`요청 ${item.payload.request_id}`, {request: item.payload, receipt: item.receipt ?? '응답 미확인'})));
  }
  return add(section, list);
}

function buildContent(data, selection) {
  const fragment = document.createDocumentFragment();
  const workspace = id(el('div', 'workspace'), 'operations');
  add(workspace, renderMap(data, selection), renderInspector(data, selection));
  return add(fragment, renderHero(data), renderMetrics(data), workspace, renderCatalog(data), renderHistory());
}

function renderHarnessReport(report) {
  const content = document.createDocumentFragment();
  if (report === null) return add(content, el('p', 'empty-state', '완료된 실행 기록이 없습니다.'));
  const view = describeHarnessResult(report);
  const reportBadge = status => el('span', `report-badge ${status.tone}`, status.label);
  add(content, add(el('div', 'report-provenance'), el('strong', '', 'fixture · 실제 AI 호출 없음'), el('span', '', '합성 결과 · 실장비 미검증')),
    el('p', 'report-history-note', '과거 실행 기록 · 현재 장비 관측과 별도로 보존합니다.'));
  const identity = el('dl', 'report-identity');
  add(identity, detail('실행 ID', report.run_id), detail('runtime instance', report.runtime_instance_id), detail('fixture policy', report.policy.id));
  add(content, identity);
  const cards = el('div', 'report-summary');
  add(cards, add(el('article', 'report-card'), el('h3', '', '종료 사유'), reportBadge(view.termination), el('p', 'mono small', report.termination.reason),
    el('p', '', view.policyClaim), el('p', 'muted small', view.taskOutcome)),
    add(id(el('article', 'report-card'), 'harness-assessment'), el('h3', '', '독립 평가'), reportBadge(view.assessment),
      el('p', 'mono small', `status: ${report.assessment.status} · verdict: ${report.assessment.verdict ?? 'null'}`),
      el('p', 'muted small', `평가 ID: ${report.assessment.evaluator_id ?? '없음'}`), el('p', 'muted small', `결과 코드: ${report.assessment.summary_code ?? '없음'}`)),
    add(el('article', 'report-card'), el('h3', '', '정리 상태'), reportBadge(view.cleanup), el('p', 'muted small', '자동 정리 없음 · 종료를 장비 정지 완료로 해석하지 않습니다.')));
  add(content, cards);
  const usage = el('dl', 'report-usage');
  for (const [key, label] of [['decisions', '판단'], ['logical_requests', '논리 요청'], ['transport_retries', '전송 재시도'], ['tick_delta', '진행 tick'], ['reserved_ticks', '예약 tick'], ['elapsed_ms', '협력식 경과 시간 (ms)']]) {
    add(usage, add(el('div'), el('dt', '', label), el('dd', 'mono', report.usage[key].toLocaleString('ko-KR', {maximumFractionDigits: 3}))));
  }
  add(content, el('h3', 'report-subheading', '예산 사용'), usage);
  if (view.unresolvedCount) add(content, add(el('div', 'report-unresolved'), el('strong', '', `응답 미확인 요청 ${view.unresolvedCount}개`),
    el('p', 'small', '종료 시 미결 ID를 보존합니다. 재개나 새 ID 자동 재실행은 제공하지 않습니다.'), el('pre', 'json', stringify(report.unresolved_request_ids))));
  add(content, jsonDetails(`관측 참조 ${report.evidence.measurement_refs.length}개 · 공개 참조 ID`, report.evidence),
    jsonDetails(`평가 참조 ${report.assessment.evidence_refs.length}개 · 정리 참조 ${report.cleanup.evidence_refs.length}개`, {assessment: report.assessment.evidence_refs, cleanup: report.cleanup.evidence_refs}),
    el('p', 'muted small report-history-note', '참조 ID만 조회합니다. 원시 파일·작성자 고장/정답은 이 화면에 제공하지 않습니다. runtime coverage의 미평가 상태는 유지됩니다.'));
  return content;
}

async function refreshHarnessReport() {
  const sequence = ++harnessLoadSequence;
  const panel = $('#harness-result-panel');
  panel.setAttribute('aria-busy', 'true');
  $('#harness-status').textContent = harnessHasSuccess ? '완료 기록을 불러오는 중입니다. 마지막 성공 기록을 표시합니다.' : '완료 기록을 불러오는 중입니다.';
  $('#harness-status').className = '';
  try {
    const response = await fetchJSON('/api/harness-result');
    if (sequence !== harnessLoadSequence) return;
    if (!response.ok) throw new Error('harness_result_unavailable');
    const next = validateHarnessResponse(response.data);
    requireSameReport(harnessReport, next.report);
    const updatedText = `기록 조회 ${seoulTime(new Date().toISOString())} KST`;
    const staged = renderHarnessReport(next.report);
    $('#harness-result-body').replaceChildren(staged);
    $('#harness-updated').textContent = updatedText;
    harnessReport = next.report;
    harnessHasSuccess = true;
    $('#harness-status').textContent = '기록 조회 완료 · 완료된 합성 실행 기록입니다.';
    $('#harness-status').className = 'load-ok';
  } catch {
    if (sequence !== harnessLoadSequence) return;
    $('#harness-status').textContent = harnessHasSuccess ? '기록을 조회하지 못했습니다. 마지막 성공 기록을 표시합니다.' : '완료 기록을 조회하지 못했습니다. 기록 새로고침으로 다시 시도하세요.';
    $('#harness-status').className = 'load-error';
    if (!harnessHasSuccess) $('#harness-result-body').replaceChildren(el('p', 'empty-state', '완료 기록 조회가 필요합니다. 장비 상태 조회와 별개로 다시 시도할 수 있습니다.'));
  } finally {
    if (sequence === harnessLoadSequence) panel.setAttribute('aria-busy', 'false');
  }
}

function setBusy(value) {
  busy = value;
  $('#refresh').disabled = busy;
  for (const control of document.querySelectorAll('#advance, #advance-ticks, #action-form input, #action-form select, #action-form textarea, #run-action')) control.disabled = busy || !!pending || !snapshot;
  $('#retry-request').disabled = busy || !pending;
  $('#content').setAttribute('aria-busy', String(busy));
}

function publish(data) {
  const selection = data.topology.devices.some(device => device.id === selected) ? selected : data.topology.devices[0]?.id ?? null;
  const updatedText = `최근 조회 ${seoulTime(data.generated_at)} KST`;
  const staged = buildContent(data, selection); // All builders finish before any successful data is published.
  $('#content').replaceChildren(staged);
  snapshot = data; selected = selection;
  $('#mode-label').textContent = data.runtime_kind === 'synthetic_fixture' ? '가상 시뮬레이션 · 합성 fixture' : '가상 시뮬레이션 · 주입 런타임';
  $('#updated').textContent = updatedText;
  setBusy(busy);
}

async function fetchJSON(path, options = {}) {
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, {...options, credentials: 'omit', cache: 'no-store', signal: controller.signal});
    const data = await response.json();
    return {ok: response.ok, status: response.status, data};
  } finally {clearTimeout(timeout);}
}

function operationMessage(message, retry = false) {
  $('#operation-message').hidden = false;
  $('#operation-status').textContent = message;
  $('#retry-request').hidden = !retry;
}

async function refresh({afterMutation = false} = {}) {
  try {
    const response = await fetchJSON('/api/state');
    if (!response.ok) throw new Error('state_unavailable');
    const next = validateSnapshot(response.data);
    if (pending && pending.session_id !== next.session_id) {
      operationMessage('서버 세션이 변경됐습니다. 이전 요청 결과는 미확인으로 보존하며 새 세션에서 자동 재실행하지 않습니다.');
      pending = null;
    }
    publish(next);
    $('#load-status').textContent = '관측 갱신 완료 · 가상 상태입니다.';
    $('#load-status').className = 'load-ok';
    return true;
  } catch {
    $('#load-status').textContent = snapshot ? '새 상태를 조회하지 못했습니다. 마지막 성공 상태를 표시합니다.' : '가상 장비 상태를 조회하지 못했습니다. 새로고침으로 다시 시도하세요.';
    $('#load-status').className = 'load-error';
    if (afterMutation) $('#operation-status').textContent += ' · 새 상태 조회 실패 (마지막 성공 관측 유지)';
    return false;
  }
}

function recordRequest(request, outcome, receipt) {
  const item = {payload: request.payload, label: request.label, outcome, receipt, at: new Date().toISOString()};
  const existing = history.findIndex(row => row.payload.request_id === request.payload.request_id);
  if (existing >= 0) history[existing] = item; else history.push(item);
  if (history.length > 100) history.shift();
  if ($('#history')) $('#history').replaceWith(renderHistory());
}

async function submit(request) {
  if (busy) return;
  pending = request; setBusy(true);
  operationMessage(`가상 동작 응답 대기 · ${request.payload.request_id}`);
  try {
    const response = await fetchJSON(request.path, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': request.csrf_token}, body: JSON.stringify(request.payload)});
    const receipt = response.data;
    if (response.ok && (!receipt || receipt.request_id !== request.payload.request_id || receipt.session_id !== request.session_id || !receipt.result || typeof receipt.result !== 'object' || receipt.synthetic !== true || receipt.hardware_verified !== false)) throw new Error('invalid_receipt');
    pending = null;
    if (!response.ok) {
      const code = receipt.error?.code || `http_${response.status}`;
      const uncertain = code === 'runtime_mutation_uncertain';
      recordRequest(request, uncertain ? '실행 결과 미확인' : '요청 거절', receipt);
      operationMessage(uncertain ? 'runtime 호출 중 오류 · 동작 반영 여부 미확인. 같은 ID는 재실행하지 않습니다. 관측과 복구 동작을 확인하세요.' : `요청 거절 · ${code}`);
      if (uncertain) await refresh();
    } else {
      const status = describeStatus(receipt.result.status);
      recordRequest(request, status.label, receipt);
      operationMessage(`${receipt.replayed ? '같은 요청 재수신' : '응답 수신'} · ${request.label} · ${status.label} (${receipt.result.status ?? '상태 미제공'})`);
      await refresh({afterMutation: true});
    }
  } catch {
    pending = request;
    recordRequest(request, '응답 미확인', null);
    operationMessage('응답을 확인하지 못했습니다. 동작이 반영됐을 수 있으므로 같은 요청 ID로 재시도하세요.', true);
  } finally {setBusy(false);}
}

function request(path, payload, label) {
  return {path, payload: {request_id: crypto.randomUUID(), ...payload}, label, csrf_token: snapshot.csrf_token, session_id: snapshot.session_id};
}

document.addEventListener('click', async event => {
  const target = event.target.closest('button, [data-device][role="button"]');
  if (!target) return;
  if (target.id === 'harness-refresh') await refreshHarnessReport();
  else if (target.id === 'refresh') {setBusy(true); await refresh(); setBusy(false);}
  else if (target.id === 'retry-request' && pending) await submit(pending);
  else if (target.id === 'advance' && snapshot && !busy && !pending) {
    const ticks = Number($('#advance-ticks').value);
    if (!Number.isSafeInteger(ticks) || ticks < 1 || ticks > 1000) {operationMessage('진행할 tick을 1~1000의 정수로 입력하세요.'); return;}
    await submit(request('/api/advance', {ticks}, `가상 시간 +${ticks} tick`));
  } else if (target.dataset.device && snapshot) {
    const next = target.dataset.device;
    const staged = renderInspector(snapshot, next);
    $('#inspector').replaceWith(staged); selected = next;
    for (const node of document.querySelectorAll('[data-device]')) {node.classList.toggle('selected', node.dataset.device === selected); node.setAttribute('aria-pressed', String(node.dataset.device === selected));}
    setBusy(busy);
  }
});

document.addEventListener('keydown', event => {
  const target = event.target.closest('[data-device][role="button"]');
  if (target && ['Enter', ' '].includes(event.key)) {event.preventDefault(); target.dispatchEvent(new MouseEvent('click', {bubbles: true}));}
});

document.addEventListener('change', event => {
  if (!snapshot) return;
  if (event.target.id === 'action-select') {
    actionSelection.set(selected, event.target.value);
    $('#inspector').replaceWith(renderInspector(snapshot, selected));
    setBusy(busy); $('#action-select').focus();
  } else if (event.target.id === 'catalog-role') {roleFilter = event.target.value; $('#catalog-body').replaceWith(renderCatalogBody(snapshot));}
});

document.addEventListener('input', event => {
  if (event.target.id === 'catalog-search' && snapshot) {query = event.target.value; $('#catalog-body').replaceWith(renderCatalogBody(snapshot));}
});

document.addEventListener('submit', async event => {
  if (event.target.id !== 'action-form') return;
  event.preventDefault();
  if (!snapshot || busy || pending) return;
  const action = $('#action-select').value, device = snapshot.topology.devices.find(item => item.id === selected), profile = profileFor(snapshot, device);
  try {
    const raw = Object.fromEntries([...event.target.querySelectorAll('[data-parameter]')].map(input => [input.dataset.parameter, input.value]));
    const parameters = parseParameters(snapshot.role_actions[profile.role][action].parameters, raw);
    await submit(request('/api/actions', {device_id: selected, action, parameters}, `${selected} · ${action}`));
  } catch (error) {operationMessage(error.message);}
});

void refreshHarnessReport();
setBusy(true);
await refresh();
setBusy(false);
