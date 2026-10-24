import {validateFccCaseSummary} from './model.mjs';

export const FCC_CASE_LOOKUP_DTO_MAX_BYTES = 8 * 1024**2;
export const FCC_CASE_LOOKUP_MAX_BYTES = 16 * 1024**2 + 1024;
const QUERY = ['product_family', 'rule', 'method', 'model'];
const COMMON = 'schema_version kind corpus_id execution_mode synthetic validation_scope verification';
const STATUS = ['reviewed', 'extracted', 'not_reported', 'extraction_failed', 'ambiguous', 'conflicting'];
const BASIS = ['report_fact', 'government_rule', 'guidance', 'standard_reference_only', 'developer_inference', 'synthetic_policy'];
const SEARCH_REASONS = ['query_context_missing', 'no_reviewed_case', 'exact_model_case_missing', 'intake_product_unconfirmed', 'intake_market_unconfirmed', 'intake_market_not_fcc', 'intake_model_unconfirmed', 'intake_product_conflict', 'intake_model_conflict', 'intake_identity_unresolved'];
const ISSUES = ['case_conflicting', 'partial_review', 'unreviewed_case', 'issuer_unconfirmed', 'scope_pending', 'scope_out_of_range', 'scope_future', 'group_unconfirmed', 'source_partial', 'source_without_citable_pages', 'rights_restricted', 'official_mapping_unverified'];
const ELIGIBILITY = ['query_context_missing', 'issuer_unconfirmed', 'scope_pending', 'scope_out_of_range', 'scope_future', 'case_conflicting', 'product_family_unconfirmed', 'rule_unconfirmed', 'method_unconfirmed', 'model_unconfirmed', 'product_family_mismatch', 'rule_mismatch', 'method_mismatch', 'model_mismatch'];
const whitespace = /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g;
const strip = value => value.replace(whitespace, '');
const fail = () => { throw Error('invalid_fcc_case_lookup'); };
const need = value => { if (!value) fail(); };
const checked = action => { try { return action(); } catch { fail(); } };
const size = value => new TextEncoder().encode(value).length;
const exact = (value, keys) => need(value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).sort().join(' ') === (Array.isArray(keys) ? keys : keys.split(' ')).slice().sort().join(' '));
const list = (value, max) => need(Array.isArray(value) && value.length <= max);
const integer = (value, min = 0) => need(Number.isSafeInteger(value) && value >= min);
const oneOf = (value, options) => need(options.includes(value));
const id = value => need(typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value));
const text = (value, max = 16384) => need(typeof value === 'string' && [...value].length <= max && strip(value).length > 0);
const unique = values => need(new Set(values).size === values.length);
const enumList = (value, options) => { list(value, options.length); unique(value); value.forEach(item => oneOf(item, options)); };
function same(a, b) {
  if (Object.is(a, b)) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object' || Array.isArray(a) !== Array.isArray(b)) return false;
  const keys = Object.keys(a).sort();
  return keys.join('\0') === Object.keys(b).sort().join('\0') && keys.every(key => same(a[key], b[key]));
}
function stringBoundary(value) {
  need(!/[\uD800-\uDFFF]/u.test(value));
  need(!/(?:^|[\s"'(<])(?:[A-Za-z]:[\\/]|\\\\[^\\\s]+\\|file:\/\/|\.local[\\/])|(?:^|[\s"'(<])\/(?:Users|home|private|tmp|var|mnt|Volumes)\//i.test(value));
}
function clonePlain(input) {
  let nodes = 0;
  const copy = (value, depth) => {
    need(++nodes <= 2000000 && depth <= 22);
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'number') { need(Number.isFinite(value) && (!Number.isInteger(value) || Number.isSafeInteger(value))); return value; }
    if (typeof value === 'string') { need(value.length <= FCC_CASE_LOOKUP_MAX_BYTES); stringBoundary(value); return value; }
    need(value && typeof value === 'object');
    const array = Array.isArray(value), prototype = Object.getPrototypeOf(value), keys = Reflect.ownKeys(value);
    need(array ? prototype === Array.prototype && keys.length === value.length + 1 : prototype === Object.prototype || prototype === null);
    const output = array ? [] : {};
    if (array) for (let i = 0; i < value.length; i++) need(Object.hasOwn(value, i));
    for (const key of keys) {
      if (array && key === 'length') continue;
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      need(typeof key === 'string' && descriptor.enumerable && Object.hasOwn(descriptor, 'value'));
      if (!array) need(++nodes <= 2000000 && depth + 1 <= 22);
      stringBoundary(key);
      Object.defineProperty(output, key, {value: copy(descriptor.value, depth + 1), writable: true, enumerable: true, configurable: true});
    }
    return output;
  };
  const value = copy(input, 0); need(size(JSON.stringify(value)) <= FCC_CASE_LOOKUP_MAX_BYTES); return value;
}

export function validateFccCaseLookupQuery(input) {
  try {
    const value = clonePlain(input); exact(value, QUERY);
    for (const key of QUERY) {
      if (value[key] === null) continue;
      text(value[key], 256); value[key] = strip(value[key]);
    }
    return value;
  } catch { throw Error('fcc_case_invalid_query'); }
}
export function fccCaseLookupTarget(input) {
  const query = validateFccCaseLookupQuery(input), values = new URLSearchParams();
  QUERY.forEach(key => values.set(key, query[key] ?? ''));
  return '/api/fcc-cases/lookup?' + values;
}

function common(value, kind, summary, fields) {
  exact(value, COMMON + ' ' + fields); need(value.kind === kind);
  for (const key of COMMON.split(' ').filter(key => key !== 'kind')) need(same(value[key], summary[key]));
}
function validate(input, baseline) {
  const value = clonePlain(input), summary = validateFccCaseSummary(baseline);
  exact(value, 'schema_version kind search discovery'); need(value.schema_version === 1 && value.kind === 'fcc_report_case_lookup');
  const search = value.search, discovery = value.discovery;
  common(search, 'fcc_report_case_matches', summary, 'query status reason_codes intake_binding matches');
  common(discovery, 'fcc_report_case_discovery', summary, 'query status reason_codes items');
  need(size(JSON.stringify(search)) <= FCC_CASE_LOOKUP_DTO_MAX_BYTES && size(JSON.stringify(discovery)) <= FCC_CASE_LOOKUP_DTO_MAX_BYTES);
  const query = validateFccCaseLookupQuery(search.query);
  need(same(query, search.query) && same(query, discovery.query));
  need(search.intake_binding === null);
  oneOf(search.status, ['candidates', 'no_match', 'insufficient_evidence']); enumList(search.reason_codes, SEARCH_REASONS);
  list(search.matches, 128); list(discovery.items, 128);
  const byCase = new Map(summary.case_previews.map(preview => [preview.case_id, preview]));
  const byDocument = new Map(summary.documents.map(document => [document.document_id, document]));
  const preview = candidate => { need(candidate && same(candidate, byCase.get(candidate.case_id))); return candidate.case_id; };
  const seenSearch = new Set(), eligible = new Set();
  for (const match of search.matches) {
    exact(match, 'preview model_relation'); const key = preview(match.preview);
    need(!seenSearch.has(key)); seenSearch.add(key);
    oneOf(match.model_relation, ['exact_model', 'related_family', 'unspecified']);
    need(match.preview.scope_status === 'in_scope' && match.preview.issuer_class !== 'unknown' && match.preview.review_status !== 'conflicting');
    need(QUERY.slice(0, 3).every(key => query[key] !== null));
    need(query.model === null ? match.model_relation === 'unspecified' : match.model_relation !== 'unspecified');
    if (search.status === 'candidates' && match.model_relation !== 'related_family') eligible.add(key);
  }
  if (search.status === 'candidates') need(search.reason_codes.length === 0 && eligible.size > 0);
  if (search.status === 'no_match') need(search.matches.length === 0 && same(search.reason_codes, ['no_reviewed_case']));
  if (search.status === 'insufficient_evidence') need(search.reason_codes.length > 0);
  oneOf(discovery.status, ['review_items', 'no_discovery_items', 'insufficient_context']);
  need(same(discovery.reason_codes, discovery.status === 'review_items' ? [] :
    [discovery.status === 'no_discovery_items' ? 'no_related_review_case' : 'discovery_context_missing']));
  need(discovery.status === 'review_items' ? discovery.items.length > 0 : discovery.items.length === 0);
  need((discovery.status === 'insufficient_context') === QUERY.every(key => query[key] === null));
  let totalClaims = 0, totalRefs = 0, valueNodes = 0;
  function claimValue(value, depth = 0) {
    need(++valueNodes <= 50000 && depth <= 6);
    if (typeof value === 'string') need([...value].length <= 16384);
    if (value && typeof value === 'object') for (const [key, item] of Object.entries(value)) {
      need([...key].length <= 16384);
      if (!Array.isArray(value)) need(++valueNodes <= 50000);
      claimValue(item, depth + 1);
    }
  }
  const seenItems = new Set();
  for (const item of discovery.items) {
    exact(item, 'preview relation criteria review_issues search_eligibility execution_authorized');
    const caseId = preview(item.preview); need(!seenItems.has(caseId)); seenItems.add(caseId);
    need(item.execution_authorized === false); enumList(item.review_issues, ISSUES);
    exact(item.search_eligibility, 'eligible reason_codes'); need(typeof item.search_eligibility.eligible === 'boolean');
    enumList(item.search_eligibility.reason_codes, ELIGIBILITY);
    need(item.search_eligibility.eligible === (item.search_eligibility.reason_codes.length === 0));
    need(item.search_eligibility.eligible === eligible.has(caseId));
    exact(item.criteria, QUERY); const claimIds = new Set(); let itemClaims = 0;
    for (const key of QUERY) {
      const criterion = item.criteria[key]; exact(criterion, 'query status reviewed_values matched_claim_ids claims');
      need(criterion.query === query[key]); oneOf(criterion.status, ['matched', 'conflicting', 'unconfirmed', 'mismatched', 'not_requested']);
      need((criterion.status === 'not_requested') === (query[key] === null));
      list(criterion.reviewed_values, 128); unique(criterion.reviewed_values); criterion.reviewed_values.forEach(value => text(value));
      list(criterion.matched_claim_ids, 64); unique(criterion.matched_claim_ids); criterion.matched_claim_ids.forEach(id);
      list(criterion.claims, 64); const byClaim = new Map();
      for (const claim of criterion.claims) {
        exact(claim, 'claim_id status basis value unit evidence_refs'); id(claim.claim_id); need(!claimIds.has(claim.claim_id)); claimIds.add(claim.claim_id);
        need(++totalClaims <= 1024 && ++itemClaims <= 64); byClaim.set(claim.claim_id, claim);
        oneOf(claim.status, STATUS); oneOf(claim.basis, BASIS); claimValue(claim.value);
        if (claim.unit !== null) text(claim.unit, 128);
        list(claim.evidence_refs, 8);
        if (['not_reported', 'extraction_failed'].includes(claim.status)) need(claim.value === null && claim.evidence_refs.length === 0);
        if (['reviewed', 'extracted'].includes(claim.status)) need(claim.value !== null && claim.evidence_refs.length > 0);
        for (const ref of claim.evidence_refs) {
          need(++totalRefs <= 4096);
          exact(ref, 'document_id source_sha256 file_page text_sha256 line_start line_end literal_verified');
          id(ref.document_id); need(item.preview.document_ids.includes(ref.document_id));
          const document = byDocument.get(ref.document_id); need(document && document.sha256 === ref.source_sha256);
          integer(ref.file_page, 1); integer(ref.line_start, 1); integer(ref.line_end, ref.line_start);
          const page = document.page_index.find(page => page.file_page === ref.file_page);
          need(page?.citable === true && page.text_sha256 === ref.text_sha256 && ref.line_end <= page.line_count && ref.line_end - ref.line_start < 40 && ref.literal_verified === true);
        }
      }
      for (const id of criterion.matched_claim_ids) {
        const claim = byClaim.get(id); need(claim?.status === 'reviewed');
        need(claim.basis === 'report_fact' || key === 'method' && claim.basis === 'standard_reference_only');
        need(typeof claim.value === 'string' || key !== 'product_family' && Array.isArray(claim.value) && claim.value.every(value => typeof value === 'string'));
      }
      if (criterion.status === 'matched') need(criterion.matched_claim_ids.length > 0);
      if (['mismatched', 'not_requested'].includes(criterion.status)) need(criterion.matched_claim_ids.length === 0);
    }
    need(QUERY.slice(0, 3).every(key => item.criteria[key].status !== 'mismatched'));
    const modelMismatch = item.criteria.model.status === 'mismatched';
    if (modelMismatch) need(QUERY.slice(0, 3).every(key => item.criteria[key].status === 'matched'));
    const requested = QUERY.filter(key => query[key] !== null).map(key => item.criteria[key].status);
    const relation = requested.includes('conflicting') ? 'conflicting' : requested.includes('unconfirmed') ? 'unconfirmed' : modelMismatch ? 'related_model' : 'criteria_matched';
    need(item.relation === relation);
  }
  return value;
}
export const validateFccCaseLookup = (input, summary) => checked(() => validate(input, summary));

export function parseFccCaseLookupJson(input, summary) {
  return checked(() => {
    need(typeof input === 'string' && size(input) <= FCC_CASE_LOOKUP_MAX_BYTES);
    let position = 0, nodes = 0; const ranges = {};
    const space = () => { while (position < input.length && /[ \t\r\n]/.test(input[position])) position++; };
    const string = () => {
      const start = position++; let escaped = false;
      while (position < input.length) {
        const char = input[position++];
        if (!escaped && char === '"') { const value = JSON.parse(input.slice(start, position)); stringBoundary(value); return value; }
        if (!escaped && char === '\\') escaped = true; else escaped = false;
      }
      fail();
    };
    const value = depth => {
      need(depth <= 22 && ++nodes <= 2000000); space(); const char = input[position];
      if (char === '"') return string();
      if (char === '{' || char === '[') {
        position++; const object = char === '{', output = object ? {} : [], end = object ? '}' : ']';
        space(); if (input[position] === end) { position++; return output; }
        while (true) {
          space(); let key;
          if (object) { need(input[position] === '"' && ++nodes <= 2000000); key = string(); need(!Object.hasOwn(output, key)); space(); need(input[position++] === ':'); }
          const start = position, item = value(depth + 1);
          if (depth === 0 && ['search', 'discovery'].includes(key)) Object.defineProperty(ranges, key, {value: [start, position], enumerable: true});
          if (object) Object.defineProperty(output, key, {value: item, writable: true, enumerable: true, configurable: true}); else output.push(item);
          space(); const next = input[position++]; if (next === end) return output; need(next === ',');
        }
      }
      for (const [token, result] of [['true', true], ['false', false], ['null', null]]) if (input.slice(position, position + token.length) === token) { position += token.length; return result; }
      const number = /-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y; number.lastIndex = position;
      const match = number.exec(input); need(match); position = number.lastIndex;
      const result = Number(match[0]); need(Number.isFinite(result) && (!Number.isInteger(result) || Number.isSafeInteger(result))); return result;
    };
    const output = value(0); space(); need(position === input.length);
    for (const key of ['search', 'discovery']) { need(Object.hasOwn(ranges, key)); need(size(input.slice(...ranges[key])) <= FCC_CASE_LOOKUP_DTO_MAX_BYTES); }
    return validate(output, summary);
  });
}
