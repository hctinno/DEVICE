import {parseFccCaseLookupJson, validateFccCaseLookupQuery} from './discovery_model.mjs';
import {createFccCaseReadGate} from './model.mjs';

const labels = {product_family: '제품군 원문 표기', rule: '규정 원문 표기', method: '방법·정확 판본', model: '모델 원문 표기'};
const literal = value => value === null ? '미확인 (null)' : typeof value === 'string' ? value : Object.is(value, -0) ? '-0' : JSON.stringify(value);
const errors = new Set(['fcc_case_catalog_unconfigured', 'fcc_case_catalog_unavailable', 'fcc_case_invalid_query', 'fcc_case_limit_exceeded']);

export function createFccCaseDiscovery(container, {summary, readLookup, selectCase}) {
  if (!container?.ownerDocument || typeof readLookup !== 'function' || typeof selectCase !== 'function') throw Error('invalid_fcc_case_lookup_view');
  const doc = container.ownerDocument, gate = createFccCaseReadGate();
  let controller = null, alive = true, generation = 0;
  const el = (tag, className = '', value) => { const node = doc.createElement(tag); if (className) node.className = className; if (value !== undefined) node.textContent = value; return node; };
  const fields = rows => {
    const dl = el('dl', 'fcc-lookup-fields');
    for (const [key, value] of rows) { const row = el('div'); row.append(el('dt', '', key), el('dd', '', literal(value))); dl.append(row); }
    return dl;
  };
  const root = el('section', 'fcc-lookup');
  const heading = el('h2', '', '검토 자료 찾기');
  root.append(heading, el('p', 'fcc-lookup-note', '기존 search의 후보와 검토할 자료를 따로 봅니다. 조건 문자 일치는 사례 전체 검토 완료·규정 승인·실물 지원을 뜻하지 않습니다.'));
  const form = el('form', 'fcc-lookup-form'), grid = el('div', 'fcc-lookup-grid');
  const inputs = {};
  for (const [key, label] of Object.entries(labels)) {
    const field = el('label', 'fcc-lookup-input', label), input = el('input');
    input.name = key; input.type = 'text'; input.autocomplete = 'off'; input.spellcheck = false; input.maxLength = 512;
    field.append(input); grid.append(field); inputs[key] = input;
  }
  const button = el('button', 'fcc-lookup-submit', '검토 자료 조회'); button.type = 'submit';
  form.append(grid, button, el('p', 'fcc-lookup-note', '필요한 조건만 입력할 수 있습니다. 빈 조건은 미지정이며 기본 제품·규정·모델은 넣지 않습니다.'));
  const status = el('p', 'fcc-lookup-status', '조건 입력 후 조회하세요. 아직 조회하지 않았습니다.');
  status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); status.tabIndex = -1; status.dataset.state = 'idle';
  const results = el('div', 'fcc-lookup-results'); results.dataset.generation = '0';
  root.append(form, status, results, el('p', 'fcc-lookup-note', '이 조회는 실행 권한을 발급하지 않으며 기존 사용자 위임을 해제하지 않습니다. 기존 사례 상세는 마지막 명시 선택 자료이며 새 조회가 자동으로 바꾸지 않습니다. 실제 AI·평가 분리·현재 교정·시험 실행은 별도입니다.'));
  container.replaceChildren(root);

  function render(value) {
    const fragment = doc.createDocumentFragment();
    fragment.append(el('h3', '', '마지막 성공 조회 조건'), fields(Object.entries(value.search.query).map(([key, value]) => [key, value === null ? '미지정 (null)' : value])));
    const search = el('section', 'fcc-lookup-search');
    search.append(el('h3', '', '기존 search 결과'), el('p', 'fcc-lookup-search-state', value.search.status), fields([['사유', value.search.reason_codes]]));
    const count = el('p', '', '반환 행 '); count.append(el('strong', 'fcc-lookup-search-count', String(value.search.matches.length))); search.append(count);
    search.append(el('p', 'fcc-lookup-note', '아래 model_relation을 그대로 확인하세요. related_family·unspecified를 exact_model 수로 합치지 않습니다. 후보가 있어도 실행 권한은 별도입니다.'));
    for (const match of value.search.matches) {
      const row = el('article', 'fcc-lookup-match'); row.dataset.modelRelation = match.model_relation;
      row.append(el('h4', '', match.preview.report_number ?? match.preview.case_id), fields([['case_id', match.preview.case_id], ['model_relation', match.model_relation]])); search.append(row);
    }
    fragment.append(search);
    const discovery = el('section', 'fcc-lookup-discovery'); discovery.append(el('h3', '', '검토할 자료'));
    const total = el('p', '', value.discovery.status + ' · 항목 '); total.append(el('strong', 'fcc-lookup-discovery-count', String(value.discovery.items.length)));
    discovery.append(total, fields([['발견 사유', value.discovery.reason_codes]]));
    if (value.discovery.status === 'insufficient_context') discovery.append(el('p', 'fcc-lookup-warning', '조회 조건이 부족합니다. 빈 모집단이나 제품 비지원이 확인된 것은 아닙니다.'));
    if (value.discovery.status === 'no_discovery_items') discovery.append(el('p', 'fcc-lookup-warning', '현재 연결 자료에서 이 조건의 검토 항목을 찾지 못했습니다. 전체 모집단·영구 비지원 판단이 아닙니다.'));
    for (const item of value.discovery.items) {
      const card = el('article', 'fcc-lookup-item'); card.dataset.caseId = item.preview.case_id; card.dataset.relation = item.relation;
      card.append(el('h4', '', item.preview.report_number ?? item.preview.case_id),
        el('p', 'fcc-lookup-relation', '제공한 조건의 문자 관계 · ' + item.relation),
        el('p', 'fcc-lookup-case-review', '사례 전체 검토 상태 · ' + item.preview.review_status),
        fields([['검토 유의', item.review_issues], ['기존 search 조건 충족', item.search_eligibility.eligible],
          ['기존 search 부적격 사유', item.search_eligibility.reason_codes], ['이 조회의 실행 권한 부여', item.execution_authorized]]));
      const open = el('button', 'fcc-lookup-open', '사례 근거 보기'); open.type = 'button'; open.dataset.caseId = item.preview.case_id; card.append(open);
      for (const [key, criterion] of Object.entries(item.criteria)) {
        const condition = el('details', 'fcc-lookup-condition'); condition.dataset.criterion = key; condition.dataset.state = criterion.status;
        condition.append(el('summary', '', labels[key] + ' · ' + criterion.status),
          fields([['요청 값', criterion.query === null ? '미지정 (null)' : criterion.query], ['조건 상태', criterion.status], ['검토된 문자열', criterion.reviewed_values], ['matched_claim_ids', criterion.matched_claim_ids]]));
        for (const claim of criterion.claims) {
          const claimNode = el('article', 'fcc-lookup-claim'); claimNode.dataset.claimId = claim.claim_id;
          claimNode.append(fields([['claim_id', claim.claim_id], ['원래 값', claim.value], ['원래 단위', claim.unit], ['원래 상태', claim.status], ['원래 근거 종류', claim.basis]]));
          for (const ref of claim.evidence_refs) {
            const node = el('section', 'fcc-lookup-ref');
            node.append(fields([['문서 ID', ref.document_id], ['원본 SHA-256', ref.source_sha256], ['파일 페이지', ref.file_page],
              ['retained SHA-256', ref.text_sha256], ['줄 시작/끝', [ref.line_start, ref.line_end]], ['literal_verified', ref.literal_verified]])); claimNode.append(node);
          }
          if (!claim.evidence_refs.length) claimNode.append(el('p', 'fcc-lookup-warning', '이 claim의 페이지 참조가 제공되지 않았습니다. 미기재·추출 실패·검토 상태를 확인하세요.'));
          condition.append(claimNode);
        }
        card.append(condition);
      }
      discovery.append(card);
    }
    fragment.append(discovery); return fragment;
  }

  async function submit(raw, {moveFocus = false} = {}) {
    if (!alive) return;
    controller?.abort(); controller = new AbortController(); const ticket = gate.begin(), current = ++generation;
    status.dataset.state = 'pending'; status.textContent = '조회 중입니다. 아래 내용이 있으면 이전 성공 조건의 결과입니다.';
    results.dataset.stale = 'true';
    const mayFocus = () => moveFocus && (form.contains(doc.activeElement) || doc.activeElement === status);
    try {
      const query = validateFccCaseLookupQuery(raw);
      const text = await readLookup(query, controller.signal);
      if (!alive || !gate.current(ticket)) return;
      const value = parseFccCaseLookupJson(text, summary);
      if (!Object.keys(labels).every(key => value.search.query[key] === query[key])) throw Error('invalid_fcc_case_lookup');
      const prepared = render(value);
      if (!alive || !gate.current(ticket)) return;
      const focus = mayFocus(); results.replaceChildren(prepared); results.dataset.generation = String(current); results.dataset.stale = 'false';
      status.dataset.state = 'success'; status.textContent = '고정된 자료의 조회 결과입니다. 후보·검토 상태·실행 권한을 따로 확인하세요.';
      if (focus) status.focus();
    } catch (error) {
      if (!alive || !gate.current(ticket)) return;
      const focus = mayFocus(), code = errors.has(error?.message) ? error.message : 'invalid_fcc_case_lookup';
      status.dataset.state = 'error'; status.textContent = '조회 실패 · ' + code + '. 이전 성공 조건·결과가 있으면 유지합니다. 빈 자료가 확인된 것은 아닙니다.';
      if (focus) status.focus();
    }
  }
  const onSubmit = event => { event.preventDefault(); void submit(Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value || null])), {moveFocus: true}); };
  const onClick = event => { const button = event.target.closest('.fcc-lookup-open'); if (button && root.contains(button) && alive) void selectCase(button.dataset.caseId); };
  form.addEventListener('submit', onSubmit); root.addEventListener('click', onClick);
  return Object.freeze({submit, root, destroy() { if (!alive) return; alive = false; controller?.abort(); gate.clear(); form.removeEventListener('submit', onSubmit); root.removeEventListener('click', onClick); root.inert = true; }});
}
