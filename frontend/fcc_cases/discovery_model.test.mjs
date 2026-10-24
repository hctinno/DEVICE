import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {createContractBundle} = require('./browser_check.cjs');
const module = await import('./discovery_model.mjs').catch(() => null);
const clone = value => structuredClone(value);
const api = () => { assert.ok(module, '033 typed lookup model is not implemented'); return module; };

export function syntheticLookup() {
  const bundle = createContractBundle(), summary = clone(bundle.summary), detail = bundle.cases[0];
  const query = {product_family: 'smartphone', rule: '47 CFR 15.247', method: 'SYNTHETIC METHOD 2013', model: 'SYNTHETIC-MODEL-A'};
  const common = kind => Object.fromEntries(['schema_version', 'corpus_id', 'execution_mode', 'synthetic', 'validation_scope', 'verification'].map(key => [key, clone(summary[key])] ).concat([['kind', kind]]));
  const mapping = {product_family: 'product.family', rule: 'method.rules', method: 'method.references', model: 'product.models'};
  const criteria = {};
  for (const [key, field] of Object.entries(mapping)) {
    const claims = detail.case.claims.filter(claim => claim.field === field).map(claim => ({
      claim_id: claim.claim_id, status: claim.status, basis: claim.basis, value: clone(claim.value), unit: claim.unit,
      evidence_refs: claim.evidence.map(value => Object.fromEntries(['document_id', 'source_sha256', 'file_page', 'text_sha256', 'line_start', 'line_end', 'literal_verified'].map(k => [k, value[k]]))),
    }));
    criteria[key] = {query: query[key], status: 'matched', reviewed_values: Array.isArray(claims[0].value) ? clone(claims[0].value) : [claims[0].value], matched_claim_ids: claims.map(c => c.claim_id), claims};
  }
  const preview = clone(summary.case_previews[0]);
  const search = {...common('fcc_report_case_matches'), query: clone(query), status: 'candidates', reason_codes: [], intake_binding: null, matches: [{preview: clone(preview), model_relation: 'exact_model'}]};
  const discovery = {...common('fcc_report_case_discovery'), query: clone(query), status: 'review_items', reason_codes: [], items: [{preview, relation: 'criteria_matched', criteria, review_issues: ['official_mapping_unverified', 'rights_restricted', 'source_partial'], search_eligibility: {eligible: true, reason_codes: []}, execution_authorized: false}]};
  return {summary, lookup: {schema_version: 1, kind: 'fcc_report_case_lookup', search, discovery}, query};
}

test('valid exact nested DTOs are detached without replacing original metadata', () => {
  const {summary, lookup} = syntheticLookup(), model = api();
  const value = model.validateFccCaseLookup(lookup, summary);
  assert.deepEqual(value, lookup); value.discovery.items[0].criteria.model.claims[0].value.push('changed');
  assert.equal(lookup.discovery.items[0].criteria.model.claims[0].value.length, 1);
  assert.deepEqual(model.parseFccCaseLookupJson(JSON.stringify(lookup), summary), lookup);
});

test('query target uses exactly four encoded values with no inferred defaults or aliases', () => {
  const model = api(), query = {product_family: null, rule: null, method: null, model: 'SYNTHETIC + & 🧪'};
  const url = new URL(model.fccCaseLookupTarget(query), 'http://127.0.0.1:1');
  assert.equal(url.pathname, '/api/fcc-cases/lookup');
  assert.deepEqual([...url.searchParams.keys()], ['product_family', 'rule', 'method', 'model']);
  assert.equal(url.searchParams.get('model'), query.model); assert.equal(url.searchParams.get('rule'), '');
  assert.deepEqual(model.validateFccCaseLookupQuery(query), query);
  assert.doesNotThrow(() => model.validateFccCaseLookupQuery({...query, model: '🧪'.repeat(256)}));
  for (const invalid of [{}, {...query, x: null}, {...query, model: false}, {...query, model: '🧪'.repeat(257)}, {...query, model: '\ud800'}]) assert.throws(() => model.validateFccCaseLookupQuery(invalid), /fcc_case_invalid_query/);
});

test('four matched criteria do not promote a conflicting case into search or execution permission', () => {
  const {summary, lookup} = syntheticLookup();
  const preview = summary.case_previews[0]; preview.review_status = 'conflicting'; preview.evaluation_group.eligible = false;
  preview.evaluation_group.missing = ['review_status']; summary.counts.independent_group_eligible_cases = 0;
  lookup.search.status = 'no_match'; lookup.search.reason_codes = ['no_reviewed_case']; lookup.search.matches = [];
  const item = lookup.discovery.items[0]; item.preview = clone(preview); item.search_eligibility = {eligible: false, reason_codes: ['case_conflicting']}; item.review_issues.push('case_conflicting');
  const value = api().validateFccCaseLookup(lookup, summary);
  assert.equal(value.discovery.items[0].relation, 'criteria_matched');
  assert.equal(value.discovery.items[0].preview.review_status, 'conflicting');
  assert.equal(value.search.matches.length, 0); assert.equal(value.discovery.items[0].execution_authorized, false);
});

test('related model and partial context remain distinct from exact model candidates', () => {
  for (const partial of [false, true]) {
    const {summary, lookup} = syntheticLookup(), item = lookup.discovery.items[0];
    lookup.search.status = 'insufficient_evidence'; lookup.search.reason_codes = [partial ? 'query_context_missing' : 'exact_model_case_missing'];
    lookup.search.matches = partial ? [] : [{preview: clone(item.preview), model_relation: 'related_family'}];
    item.search_eligibility = {eligible: false, reason_codes: [partial ? 'query_context_missing' : 'model_mismatch']};
    if (partial) {
      for (const key of ['product_family', 'rule', 'method']) {
        lookup.search.query[key] = lookup.discovery.query[key] = null;
        Object.assign(item.criteria[key], {query: null, status: 'not_requested', matched_claim_ids: []});
      }
    } else {
      lookup.search.query.model = lookup.discovery.query.model = 'SYNTHETIC-OTHER';
      Object.assign(item.criteria.model, {query: 'SYNTHETIC-OTHER', status: 'mismatched', matched_claim_ids: []}); item.relation = 'related_model';
    }
    const value = api().validateFccCaseLookup(lookup, summary);
    assert.equal(value.search.status, 'insufficient_evidence'); assert.equal(value.discovery.items[0].search_eligibility.eligible, false);
  }
});

test('all-null context is an explicit insufficient response and not an empty confirmed population', () => {
  const {summary, lookup} = syntheticLookup();
  for (const value of [lookup.search, lookup.discovery]) value.query = {product_family: null, rule: null, method: null, model: null};
  Object.assign(lookup.search, {status: 'insufficient_evidence', reason_codes: ['query_context_missing'], matches: []});
  Object.assign(lookup.discovery, {status: 'insufficient_context', reason_codes: ['discovery_context_missing'], items: []});
  assert.deepEqual(api().validateFccCaseLookup(lookup, summary), lookup);
});

test('claim projections preserve numeric zero boolean false null original basis and evidence refs', () => {
  const {summary, lookup} = syntheticLookup(), claims = lookup.discovery.items[0].criteria.model.claims;
  for (const [id, value, status] of [['SYNTH-ZERO', 0, 'extracted'], ['SYNTH-FALSE', false, 'extracted'], ['SYNTH-NULL', null, 'not_reported']]) {
    claims.push({...clone(claims[0]), claim_id: id, value, status, evidence_refs: value === null ? [] : clone(claims[0].evidence_refs)});
  }
  const value = api().validateFccCaseLookup(lookup, summary);
  assert.deepEqual(value.discovery.items[0].criteria.model.claims.slice(1).map(c => c.value), [0, false, null]);
});

test('wrong keys flags enum paired query preview and source page references are rejected', () => {
  const mutations = [
    x => { x.extra = true; }, x => { x.discovery.verification.coverage_complete = true; },
    x => { x.discovery.query.model = 'different'; }, x => { x.discovery.items[0].execution_authorized = true; },
    x => { x.discovery.items[0].relation = 'approved'; }, x => { x.search.matches[0].model_relation = 'approved'; },
    x => { x.discovery.items[0].preview.manufacturer = 'changed'; },
    x => { x.discovery.items[0].criteria.model.claims[0].evidence_refs[0].file_page = 2; },
    x => { x.discovery.items[0].criteria.model.claims[0].evidence_refs[0].source_sha256 = '0'.repeat(64); },
    x => { x.discovery.items[0].criteria.model.claims[0].evidence_refs[0].line_end = 10000; },
    x => { x.discovery.items[0].criteria.model.matched_claim_ids = ['missing']; },
    x => { x.discovery.items[0].criteria.model.claims[0].value = 'C:/private/source.pdf'; },
    x => { x.discovery.items[0].criteria.model.claims[0].value = Number.MAX_SAFE_INTEGER + 1; },
    x => { x.discovery.items[0].criteria.model.claims[0].claim_id += '\n'; x.discovery.items[0].criteria.model.matched_claim_ids[0] += '\n'; },
  ];
  const model = api();
  for (const mutate of mutations) { const {summary, lookup} = syntheticLookup(); mutate(lookup); assert.throws(() => model.validateFccCaseLookup(lookup, summary), /invalid_fcc_case_lookup/); }
});

test('duplicates malformed JSON surrogates accessors sparse arrays and nonfinite values fail closed', () => {
  const model = api(), {summary, lookup} = syntheticLookup(), text = JSON.stringify(lookup);
  for (const invalid of ['\ufeff' + text, text.replace('"schema_version":1', '"schema_version":1,"schema_version":1'), text + 'x', text.replace('"schema_version":1', '"schema_version":NaN'), text.replace('"smartphone"', '"\\ud800"')]) assert.throws(() => model.parseFccCaseLookupJson(invalid, summary), /invalid_fcc_case_lookup/);
  let invoked = false; const value = clone(lookup); Object.defineProperty(value.discovery.items[0], 'relation', {enumerable: true, get() { invoked = true; return 'criteria_matched'; }});
  assert.throws(() => model.validateFccCaseLookup(value, summary), /invalid_fcc_case_lookup/); assert.equal(invoked, false);
  const sparse = clone(lookup); delete sparse.discovery.items[0]; assert.throws(() => model.validateFccCaseLookup(sparse, summary), /invalid_fcc_case_lookup/);
});

test('two valid large child DTOs retain 128 values and accept an envelope larger than8MiB', () => {
  const {summary, lookup} = syntheticLookup(), item = lookup.discovery.items[0];
  const methods = ['SYNTHETIC METHOD 2013', ...Array.from({length: 127}, (_, i) => 'SYNTHETIC-METHOD-' + i + '-' + 'X'.repeat(15950))];
  const models = ['SYNTHETIC-MODEL-A', ...Array.from({length: 39}, (_, i) => 'SYNTHETIC-MODEL-' + i + '-' + 'Y'.repeat(15950))];
  for (const preview of [summary.case_previews[0], lookup.search.matches[0].preview, item.preview]) { preview.methods = clone(methods); preview.models = clone(models); }
  for (const [key, values] of [['method', methods], ['model', models]]) { item.criteria[key].reviewed_values = clone(values); item.criteria[key].claims[0].value = clone(values); }
  const text = JSON.stringify(lookup), size = value => new TextEncoder().encode(JSON.stringify(value)).length;
  assert(size(lookup.search) < 8 * 1024**2); assert(size(lookup.discovery) < 8 * 1024**2); assert(size(lookup) > 8 * 1024**2);
  const value = api().parseFccCaseLookupJson(text, summary);
  assert.equal(value.discovery.items[0].criteria.method.reviewed_values.length, 128);
  assert.equal(value.discovery.items[0].preview.models.length, 40);
  assert.throws(() => api().parseFccCaseLookupJson(' '.repeat(16 * 1024**2 + 1025) + text, summary), /invalid_fcc_case_lookup/);
});

test('parent claim string limit counts16384 astral code points without truncation', () => {
  const {summary, lookup} = syntheticLookup(), item = lookup.discovery.items[0];
  const preview = summary.case_previews[0]; preview.review_status = 'partial';
  preview.evaluation_group.eligible = false; preview.evaluation_group.missing = ['review_status']; summary.counts.independent_group_eligible_cases = 0;
  lookup.search.matches[0].preview = clone(preview); item.preview = clone(preview); item.review_issues.push('partial_review');
  item.criteria.model.claims.push({...clone(item.criteria.model.claims[0]), claim_id: 'SYNTH-ASTRAL', status: 'extracted', value: '🧪'.repeat(16384)});
  const value = api().parseFccCaseLookupJson(JSON.stringify(lookup), summary);
  assert.equal([...value.discovery.items[0].criteria.model.claims[1].value].length, 16384);
});

test('raw child byte limit includes whitespace even when the outer envelope is small enough', () => {
  const {summary, lookup} = syntheticLookup();
  const raw = '{"schema_version":1,"kind":"fcc_report_case_lookup","search":' + ' '.repeat(8 * 1024**2)
    + JSON.stringify(lookup.search) + ',"discovery":' + JSON.stringify(lookup.discovery) + '}';
  assert(raw.length < 16 * 1024**2);
  assert.throws(() => api().parseFccCaseLookupJson(raw, summary), /invalid_fcc_case_lookup/);
});
