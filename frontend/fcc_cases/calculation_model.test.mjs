import managedPaths from '../managed_paths.cjs';
//039 frozen typed contracts, 2026-10-24 Asia/Seoul.
// Synthetic DTOs; named Python regressions also construct a genuine synthetic catalog.
// No collected source, actual measurement, HTTP or operational authorization.
// Root frozen API; synthetic fixtures and original missingmodule evidence are separate.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import fixture from './browser_check.cjs';
import * as legacy from './model.mjs';

const target = new URL('./calculation_model.mjs', import.meta.url);
let model = null, missingModule = null;
try { model = await import(target.href); }
catch (error) {
  if (error.code !== 'ERR_MODULE_NOT_FOUND' || existsSync(target)) throw error;
  missingModule = error;
}
const clone = value => structuredClone(value);
const bytes = value => Buffer.byteLength(typeof value === 'string' ? value : JSON.stringify(value), 'utf8');
const invalid = action => assert.throws(action, /^Error: invalid_fcc_case_calculation$/);
const proposed = (name, run) => test(name, run);
const SHAPE9 = 'schema_version kind corpus_id case_id status request_context result error_code execution_authorized';
const SHAPE20 = 'schema_version kind corpus_id case_id calculator status reason_codes execution_mode synthetic validation_scope verification context source_page inputs reported_result calculation unit_conversion comparison_policy comparison interpretation_scope';
const REQUEST3 = 'schema_version case_id calculation_request';
const REQUEST6 = 'calculator rule method input_claim_ids reported_result_claim_id comparison_policy';
const expectedKeys = (value, keys) => assert.deepEqual(Object.keys(value).sort(), keys.split(' ').sort());

function synthetic() {
  const bundle = fixture.createContractBundle(), summary = clone(bundle.summary), detail = clone(bundle.cases[0]);
  detail.case.claims.find(claim => claim.field === 'method.references').basis = 'report_fact';
  const reading = clone(detail.case.claims.find(claim => claim.claim_id === 'zero'));
  Object.assign(reading, {claim_id: 'SYNTH-READING-039', field: 'result.rf_power_reading', value: 0, unit: 'dBm'});
  for (const evidence of reading.evidence) {
    evidence.table = 'SYNTH-TABLE-039'; evidence.row = 'SYNTH-ROW-039';
  }
  detail.case.claims.push(reading);
  summary.counts.reviewed_claim_count++;
  const request = {schema_version: 1, case_id: detail.case.case_id, calculation_request: {
    calculator: 'rf_power', rule: detail.case.preview.rules[0], method: detail.case.preview.methods[0],
    input_claim_ids: {reading: reading.claim_id}, reported_result_claim_id: null, comparison_policy: null,
  }};
  const sources = reading.evidence.map(evidence => Object.fromEntries(
    ['document_id', 'source_sha256', 'file_page', 'text_sha256', 'line_start', 'line_end', 'table', 'row']
      .map(key => [key, clone(evidence[key])])));
  const source = sources[0];
  const result = {
    schema_version: 1, kind: 'fcc_report_calculation_check', corpus_id: detail.corpus_id,
    case_id: request.case_id, calculator: 'rf_power', status: 'calculated', reason_codes: [],
    execution_mode: 'report_derived', synthetic: true,
    validation_scope: 'provided_case_dto_and_claim_source_consistency_only',
    verification: {...clone(detail.verification), source_bytes_reverified: false,
      issuer_authenticity_verified: false, native_raw_observed: false},
    context: {rule: request.calculation_request.rule, method: request.calculation_request.method,
      issuer_class: detail.case.preview.issuer_class, product_family: detail.case.preview.product_family},
    source_page: {document_id: source.document_id, source_sha256: source.source_sha256,
      file_page: source.file_page, text_sha256: source.text_sha256,
      row_binding: {basis: 'explicit_table_row', table: source.table, row: source.row,
        line_start: null, line_end: null}},
    inputs: [{role: 'reading', claim_id: reading.claim_id, field: reading.field,
      value: reading.value, unit: reading.unit, sources}],
    reported_result: null,
    // An explicit synthetic expected value, not an implementation of RF arithmetic.
    calculation: {value: 0.001, unit: 'W', native_result: {value: 0.001, unit: 'W'}},
    unit_conversion: null, comparison_policy: null, comparison: null,
    interpretation_scope: 'reviewer_structured_values_not_literal_semantic_certification',
  };
  const response = {schema_version: 1, kind: 'fcc_case_calculation', corpus_id: detail.corpus_id,
    case_id: request.case_id, status: result.status, request_context: clone(request), result,
    error_code: null, execution_authorized: false};
  return {summary, detail, request, response};
}

function replaceResult(response, rawResult) {
  const raw = JSON.stringify(response), marker = '"result":' + JSON.stringify(response.result);
  assert.equal(raw.split(marker).length, 2);
  return raw.replace(marker, '"result":' + rawResult);
}

function resultWire128(f = synthetic()) {
  const result = JSON.stringify(f.response.result), padding = 128 * 1024 - bytes(result);
  assert(padding > 0);
  const rawResult = '{' + ' '.repeat(padding) + result.slice(1);
  assert.equal(bytes(rawResult), 128 * 1024);
  return {...f, raw: replaceResult(f.response, rawResult), rawResult};
}

test('SYNTHETIC FIXTURE: static synthetic request3/inner6/response9/result20 and source anchors', () => {
  const f = synthetic();
  expectedKeys(f.request, REQUEST3); expectedKeys(f.request.calculation_request, REQUEST6);
  expectedKeys(f.response, SHAPE9); expectedKeys(f.response.result, SHAPE20);
  assert.deepEqual(legacy.validateFccCaseSummary(f.summary), f.summary);
  assert.deepEqual(legacy.validateFccCaseDetail(f.detail, f.request.case_id, f.summary), f.detail);
  assert.equal(f.response.result.synthetic, true);
  assert.equal(f.response.result.inputs[0].value, 0);
  assert.equal(f.detail.case.claims.find(claim => claim.claim_id === 'false').value, false);
  assert.equal(f.response.execution_authorized, false);
  assert(Object.values(f.response.result.verification).every(flag => flag === false));
});

test('SYNTHETIC FIXTURE: JSON whitespace makes a valid128KiB inner wire value plus request echo', () => {
  const f = resultWire128();
  assert(bytes(f.raw) > 128 * 1024 && bytes(f.raw) < 160 * 1024);
  assert(bytes(f.response.result) < 128 * 1024);
  assert.deepEqual(JSON.parse(f.raw), f.response);
});

test('039 product module presence: preserve missingmodule RED separately from fixture checks', () => {
  assert.ifError(missingModule);
  assert.ok(model);
});

proposed('exports distinguish service request/result/response budgets and wire request budget', () => {
  assert.equal(model.FCC_CASE_CALCULATION_REQUEST_MAX_BYTES, 32 * 1024);
  assert.equal(model.FCC_CASE_CALCULATION_WIRE_REQUEST_MAX_BYTES, 64 * 1024);
  assert.equal(model.FCC_CASE_CALCULATION_RESULT_MAX_BYTES, 128 * 1024);
  assert.equal(model.FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES, 160 * 1024);
});

proposed('request preserves exact3/6 keys, explicit IDs, zero client numeric fields and detached values', () => {
  const f = synthetic(), before = clone(f.request), value = model.validateFccCaseCalculationRequest(f.request);
  assert.deepEqual(value, before); expectedKeys(value, REQUEST3); expectedKeys(value.calculation_request, REQUEST6);
  value.calculation_request.rule = 'changed';
  assert.deepEqual(f.request, before);
});

proposed('request accepts256 Unicode codepoints and preserves original explicit whitespace without aliasing', () => {
  const f = synthetic();
  f.request.calculation_request.rule = '𠮷'.repeat(256);
  f.request.calculation_request.method = '  SYNTHETIC METHOD 2013  ';
  assert.equal(Array.from(f.request.calculation_request.rule).length, 256);
  assert.deepEqual(model.validateFccCaseCalculationRequest(f.request), f.request);
  f.request.calculation_request.rule += '𠮷';
  invalid(() => model.validateFccCaseCalculationRequest(f.request));
});

proposed('request Python whitespace-only inputs, invalid IDs, client values and extra roles fail', () => {
  const variants = [
    value => { value.schema_version = true; }, value => { value.case_id += '\n'; },
    value => { value.calculation_request.rule = '\u0085'; },
    value => { value.calculation_request.method = ''; },
    value => { value.calculation_request.rule = 'https://private.invalid'; },
    value => { value.calculation_request.calculator = 'emc_field_strength'; },
    value => { value.calculation_request.input_claim_ids.reading = 0; },
    value => { value.calculation_request.input_claim_ids.extra = 'SYNTH-EXTRA'; },
    value => { value.calculation_request.reading = 0; },
    value => { value.calculation_request.reported_result_claim_id = 'SYNTH-RESULT'; },
    value => { value.calculation_request.comparison_policy = {absolute_tolerance: 0, unit: 'W'}; },
  ];
  for (const mutate of variants) { const f = synthetic(); mutate(f.request); invalid(() => model.validateFccCaseCalculationRequest(f.request)); }
});

proposed('summary and case are independently typed and retain detached original values', () => {
  const f = synthetic();
  const summary = model.parseFccCaseCalculationSummaryJson(JSON.stringify(f.summary));
  const detail = model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, summary);
  assert.deepEqual(summary, f.summary); assert.deepEqual(detail, f.detail);
  detail.case.claims[0].value = 'changed';
  assert.notDeepEqual(detail, f.detail);
});

proposed('parent16384-codepoint manufacturer and unrelated claim stay valid beyond UTF16 length', () => {
  const f = synthetic(), original = '𠮷'.repeat(16384);
  f.detail.case.claims.find(claim => claim.field === 'product.manufacturer').value = original;
  f.detail.case.preview.manufacturer = original;
  f.summary.case_previews.find(preview => preview.case_id === f.request.case_id).manufacturer = original;
  const summary = model.parseFccCaseCalculationSummaryJson(JSON.stringify(f.summary));
  const detail = model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, summary);
  assert.equal(detail.case.preview.manufacturer, original);
  assert.equal(detail.case.claims.find(claim => claim.field === 'product.manufacturer').value, original);
  assert.equal(original.length, 32768);
  f.detail.case.claims.find(claim => claim.field === 'product.manufacturer').value += '𠮷';
  invalid(() => model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, summary));
});

proposed('parent8192-codepoint quote is retained and8193 fails without changing024', () => {
  const f = synthetic(), evidence = f.detail.case.claims[0].evidence[0];
  evidence.quote = '𠮷'.repeat(4096) + '\n' + '𠮷'.repeat(4095);
  assert.equal(Array.from(evidence.quote).length, 8192);
  assert.equal(model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, f.summary)
    .case.claims[0].evidence[0].quote, evidence.quote);
  evidence.quote += '𠮷';
  invalid(() => model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, f.summary));
});

proposed('original zero false and null remain distinct case values', () => {
  const f = synthetic(), detail = model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, f.summary);
  assert.equal(detail.case.claims.find(claim => claim.claim_id === 'SYNTH-READING-039').value, 0);
  assert.equal(detail.case.claims.find(claim => claim.claim_id === 'false').value, false);
  assert.equal(detail.case.preview.revision, null);
});

proposed('normal calculated response remains exact9/20 detached and preserves verification8false', () => {
  const f = synthetic(), value = model.validateFccCaseCalculationResponse(f.response, f.request, f.detail);
  assert.deepEqual(value, f.response); expectedKeys(value, SHAPE9); expectedKeys(value.result, SHAPE20);
  value.result.inputs[0].sources[0].row = 'changed';
  assert.notDeepEqual(value, f.response);
});

// Literal expectations are independent of the JavaScript comparator. Python036/023
// produces every response from the public genuine synthetic constructor, unsorted input.
const sourceOrders = [
  {name: 'BMP before supplementary table',
    locators: [['SYNTHETIC-\u{10000}', 'ROW'], ['SYNTHETIC-\uE000', 'ROW']],
    expected: [['SYNTHETIC-\uE000', 'ROW'], ['SYNTHETIC-\u{10000}', 'ROW']]},
  {name: 'BMP before supplementary row',
    locators: [['TABLE', 'SYNTHETIC-\u{10000}'], ['TABLE', 'SYNTHETIC-\uE000']],
    expected: [['TABLE', 'SYNTHETIC-\uE000'], ['TABLE', 'SYNTHETIC-\u{10000}']]},
  {name: 'Korean common prefix and supplementary suffix',
    locators: [['표\u{10000}가', 'ROW'], ['표\uE000나', 'ROW'], ['표가나', 'ROW'],
      ['표나', 'ROW'], ['표가', 'ROW'], ['표', 'ROW']],
    expected: [['표', 'ROW'], ['표가', 'ROW'], ['표가나', 'ROW'], ['표나', 'ROW'],
      ['표\uE000나', 'ROW'], ['표\u{10000}가', 'ROW']]},
  {name: 'null table and row remain original nulls',
    locators: [[null, 'SYNTHETIC-\u{10000}'], ['SYNTHETIC-\u{10000}', null],
      [null, 'SYNTHETIC-\uE000'], ['SYNTHETIC-\uE000', null]],
    expected: [[null, 'SYNTHETIC-\uE000'], [null, 'SYNTHETIC-\u{10000}'],
      ['SYNTHETIC-\uE000', null], ['SYNTHETIC-\u{10000}', null]]},
  {name: 'decomposed Korean and common prefix stay unnormalized',
    locators: [['TABLE', '가나'], ['TABLE', '나'], ['TABLE', '가나나'],
      ['TABLE', '가'], ['TABLE', '가']],
    expected: [['TABLE', '가'], ['TABLE', '가'], ['TABLE', '가나'],
      ['TABLE', '가나나'], ['TABLE', '나']]},
  {name: 'ASCII prefixes retain Python lexical order',
    locators: [['A-A', 'ROW'], ['AA', 'ROW'], ['A-', 'ROW'], ['A', 'ROW']],
    expected: [['A', 'ROW'], ['A-', 'ROW'], ['A-A', 'ROW'], ['AA', 'ROW']]},
  {name: 'duplicate evidence retains original multiplicity',
    locators: [['SYNTHETIC-\u{10000}', 'ROW'], ['SYNTHETIC-\uE000', 'ROW'],
      ['SYNTHETIC-\u{10000}', 'ROW'], ['SYNTHETIC-\uE000', 'ROW']],
    expected: [['SYNTHETIC-\uE000', 'ROW'], ['SYNTHETIC-\uE000', 'ROW'],
      ['SYNTHETIC-\u{10000}', 'ROW'], ['SYNTHETIC-\u{10000}', 'ROW']]},
];
let pythonSourceCases;
function genuineSourceCases() {
  if (pythonSourceCases) return pythonSourceCases;
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const python = process.env.FCC_CASE_CALCULATION_PYTHON || managedPaths.python(root);
  const program = String.raw`
from copy import deepcopy
import json, sys, types
from pathlib import Path
root = Path.cwd()
package = types.ModuleType('tests'); package.__path__ = [str(root/'tests')]
sys.modules['tests'] = package
from tests.test_fcc_case_calculation import inputs
from labflow.fcc_case_calculation import calculate_case_claim
results = []
for vector in json.load(sys.stdin):
    def change(packet, reading):
        original = reading['evidence'][0]
        reading['evidence'] = [dict(deepcopy(original), table=table, row=row)
                               for table, row in vector['locators']]
    catalog, request, _, _ = inputs(change=change)
    response = calculate_case_claim(catalog, request)
    assert response['status'] == 'calculated'
    results.append(dict(name=vector['name'], summary=catalog.summary(),
                        detail=catalog.case(request['case_id']), request=request, response=response))
print(json.dumps(results, ensure_ascii=False, allow_nan=False))
`;
  const result = spawnSync(python, ['-X', 'utf8', '-B', '-c', program], {
    cwd: root, encoding: 'utf8', timeout: 30000, maxBuffer: 2 * 1024 * 1024,
    env: {...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1'},
    input: JSON.stringify(sourceOrders.map(({name, locators}) => ({name, locators}))),
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  pythonSourceCases = JSON.parse(result.stdout);
  assert.equal(pythonSourceCases.length, sourceOrders.length);
  return pythonSourceCases;
}

for (const [index, vector] of sourceOrders.entries()) {
  proposed('genuine Python036 source order: ' + vector.name, () => {
    const f = genuineSourceCases()[index];
    assert.equal(f.name, vector.name);
    const before = clone(f), summary = model.parseFccCaseCalculationSummaryJson(JSON.stringify(f.summary));
    const detail = model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, summary);
    assert.deepEqual(f.response.result.inputs[0].sources.map(source => [source.table, source.row]), vector.expected);
    assert.deepEqual(model.parseFccCaseCalculationJson(JSON.stringify(f.response), f.request, detail), f.response);
    assert.deepEqual(model.validateFccCaseCalculationResponse(f.response, f.request, detail), f.response);
    assert.deepEqual(f, before);
  });
}

proposed('genuine Python projection still rejects reversed missing added and duplicated sources', () => {
  const f = genuineSourceCases()[0];
  for (const mutate of [sources => sources.reverse(), sources => sources.pop(),
    sources => sources.push({...clone(sources[0]), row: 'EXTRA-ROW'}),
    sources => sources.push(clone(sources[0])), sources => { sources[0] = clone(sources[1]); }]) {
    const response = clone(f.response);
    mutate(response.result.inputs[0].sources);
    invalid(() => model.validateFccCaseCalculationResponse(response, f.request, f.detail));
  }
  const duplicates = genuineSourceCases().at(-1), response = clone(duplicates.response);
  response.result.inputs[0].sources.splice(0, 1);
  invalid(() => model.validateFccCaseCalculationResponse(response, duplicates.request, duplicates.detail));
});

proposed('genuine null locators cannot be replaced with empty strings or normalized Korean labels', () => {
  const nullable = genuineSourceCases()[3], response = clone(nullable.response);
  response.result.inputs[0].sources[0].table = '';
  invalid(() => model.validateFccCaseCalculationResponse(response, nullable.request, nullable.detail));
  const korean = genuineSourceCases()[4], normalized = clone(korean.response);
  normalized.result.inputs[0].sources[0].row = '가';
  invalid(() => model.validateFccCaseCalculationResponse(normalized, korean.request, korean.detail));
});

proposed('128KiB raw result plus valid request echo fits response160KiB rather than a narrowed128KiB cap', () => {
  const f = resultWire128();
  assert.deepEqual(model.parseFccCaseCalculationJson(f.raw, f.request, f.detail), f.response);
});

proposed('raw response exactly160KiB is accepted and one extra byte is refused', () => {
  const f = synthetic(), raw = JSON.stringify(f.response), padded = ' '.repeat(160 * 1024 - bytes(raw)) + raw;
  assert.equal(bytes(padded), 160 * 1024);
  assert.deepEqual(model.parseFccCaseCalculationJson(padded, f.request, f.detail), f.response);
  invalid(() => model.parseFccCaseCalculationJson(' ' + padded, f.request, f.detail));
});

proposed('maximum explicit rule/method256 codepoints preserve response echo and context', () => {
  const f = synthetic(), rule = '𠮷'.repeat(256), method = '𠮸'.repeat(256);
  for (const [key, field, value] of [['rule', 'method.rules', rule], ['method', 'method.references', method]]) {
    f.request.calculation_request[key] = value;
    f.detail.case.preview[key === 'rule' ? 'rules' : 'methods'] = [value];
    f.detail.case.claims.find(claim => claim.field === field).value = value;
    f.response.result.context[key] = value;
  }
  f.response.request_context = clone(f.request);
  assert.deepEqual(model.parseFccCaseCalculationJson(JSON.stringify(f.response), f.request, f.detail), f.response);
});

proposed('unsafe integer lexemes fail before Number rounding and safe integer remains exact', () => {
  const f = synthetic(), key = '"value":0';
  const raw = JSON.stringify(f.detail).replace(key, '"value":9007199254740993');
  assert.notEqual(raw, JSON.stringify(f.detail));
  invalid(() => model.parseFccCaseCalculationCaseJson(raw, f.request.case_id, f.summary));
  const result = JSON.stringify(f.response).replace(key, '"value":9007199254740993');
  invalid(() => model.parseFccCaseCalculationJson(result, f.request, f.detail));
  f.detail.case.claims.find(claim => claim.claim_id === 'SYNTH-READING-039').value = Number.MAX_SAFE_INTEGER;
  assert.equal(model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail), f.request.case_id, f.summary)
    .case.claims.find(claim => claim.claim_id === 'SYNTH-READING-039').value, Number.MAX_SAFE_INTEGER);
});

proposed('response corpus case request rule/method and reading mismatches fail typed validation', () => {
  const variants = [
    value => { value.corpus_id = 'SYNTH-OTHER-CORPUS'; },
    value => { value.result.corpus_id = 'SYNTH-OTHER-CORPUS'; },
    value => { value.case_id = 'SYNTH-OTHER-CASE'; },
    value => { value.result.case_id = 'SYNTH-OTHER-CASE'; },
    value => { value.request_context.calculation_request.method += '-OTHER'; },
    value => { value.request_context.calculation_request.input_claim_ids.reading = 'SYNTH-OTHER-CLAIM'; },
    value => { value.result.context.rule += '-OTHER'; },
    value => { value.result.context.product_family = 'SYNTH-OTHER-FAMILY'; },
    value => { value.result.inputs[0].claim_id = 'SYNTH-OTHER-CLAIM'; },
    value => { value.result.inputs[0].value = 1; },
  ];
  for (const mutate of variants) { const f = synthetic(); mutate(f.response); invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail)); }
});

proposed('cross-document hash page line table row and binding mutations fail as source mismatches', () => {
  const variants = [
    value => { value.result.inputs[0].sources[0].document_id = 'SYNTH-OTHER-DOC'; },
    value => { value.result.inputs[0].sources[0].source_sha256 = 'e'.repeat(64); },
    value => { value.result.inputs[0].sources[0].text_sha256 = 'e'.repeat(64); },
    value => { value.result.inputs[0].sources[0].file_page = 2; },
    value => { value.result.inputs[0].sources[0].line_end = 3; },
    value => { value.result.inputs[0].sources[0].row = 'SYNTH-OTHER-ROW'; },
    value => { value.result.source_page.source_sha256 = 'e'.repeat(64); },
    value => { value.result.source_page.row_binding.table = 'SYNTH-OTHER-TABLE'; },
    value => { value.result.source_page.row_binding.line_start = 1; },
  ];
  for (const mutate of variants) { const f = synthetic(); mutate(f.response); invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail)); }
});

proposed('every authority/verification flag is exactly false with no truthy or numeric substitutes', () => {
  for (const replacement of [true, null, 0, 'false']) {
    const f = synthetic(); f.response.execution_authorized = replacement;
    invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail));
  }
  for (const key of Object.keys(synthetic().response.result.verification)) {
    const f = synthetic(); f.response.result.verification[key] = true;
    invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail));
  }
});

proposed('null report conversion comparison and policy cannot be silently introduced', () => {
  for (const key of ['reported_result', 'unit_conversion', 'comparison_policy', 'comparison']) {
    const f = synthetic(); f.response.result[key] = {};
    invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail));
  }
  const f = synthetic(); f.response.result.calculation = null;
  invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail));
});

proposed('well-formed insufficient evidence preserves source projection with null calculation', () => {
  const f = synthetic();
  f.detail.case.claims.find(claim => claim.claim_id === 'SYNTH-READING-039').value = 4000;
  Object.assign(f.response.result, {status: 'insufficient_evidence', reason_codes: ['numeric_representation_unavailable'], calculation: null});
  f.response.result.inputs[0].value = 4000; f.response.status = 'insufficient_evidence';
  const value = model.validateFccCaseCalculationResponse(f.response, f.request, f.detail);
  assert.deepEqual(value, f.response);
  assert.equal(value.result.inputs[0].value, 4000);
  assert.equal(value.result.calculation, null);
});

proposed('context insufficiency may keep all-null context and zero projections rather than fake zero input', () => {
  const f = synthetic(); f.detail.case.preview.scope_status = 'pending';
  f.detail.case.preview.evaluation_group.eligible = false;
  f.detail.case.preview.evaluation_group.missing = ['scope_status'];
  Object.assign(f.response.result, {status: 'insufficient_evidence', reason_codes: ['case_context_unconfirmed'],
    context: {rule: null, method: null, issuer_class: null, product_family: null}, source_page: null, inputs: [], calculation: null});
  f.response.status = 'insufficient_evidence';
  assert.deepEqual(model.validateFccCaseCalculationResponse(f.response, f.request, f.detail), f.response);
});

proposed('service rejected stays a valid200 business envelope with validated context and null result', () => {
  const f = synthetic(); Object.assign(f.response, {corpus_id: null, status: 'rejected', result: null, error_code: 'fcc_case_not_found'});
  assert.deepEqual(model.validateFccCaseCalculationResponse(f.response, f.request, f.detail), f.response);
});

proposed('invalid-request service rejection has null case and context without echoing raw input', () => {
  const f = synthetic(); Object.assign(f.response, {corpus_id: null, case_id: null, status: 'rejected', request_context: null,
    result: null, error_code: 'fcc_case_calculation_invalid_request'});
  assert.deepEqual(model.validateFccCaseCalculationResponse(f.response, f.request, f.detail), f.response);
  f.response.case_id = f.request.case_id;
  invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail));
});

proposed('transport error/code is not a service response and unknown private error strings are refused', () => {
  const f = synthetic();
  invalid(() => model.parseFccCaseCalculationJson('{"error":{"code":"fcc_case_catalog_unconfigured"}}', f.request, f.detail));
  Object.assign(f.response, {corpus_id: null, status: 'rejected', result: null, error_code: 'C:/PRIVATE/source.pdf'});
  invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail));
});

proposed('BOM duplicate keys trailing text surrogates nonfinite and malformed JSON fail closed', () => {
  const f = synthetic(), raw = JSON.stringify(f.response);
  const variants = ['\ufeff' + raw, raw + 'x', raw.replace('"schema_version":1', '"schema_version":1,"schema_version":1'),
    raw.replace('"value":0', '"value":NaN'), raw.replace('"value":0', '"value":1e999'),
    raw.replace('smartphone', '\\ud800')];
  for (const value of variants) invalid(() => model.parseFccCaseCalculationJson(value, f.request, f.detail));
});

proposed('accessor sparse arrays exotic prototypes and cycles are refused without invoking hooks', () => {
  const f = synthetic(); let invoked = 0;
  const getter = clone(f.response);
  Object.defineProperty(getter, 'status', {enumerable: true, get() { invoked++; return 'calculated'; }});
  invalid(() => model.validateFccCaseCalculationResponse(getter, f.request, f.detail));
  assert.equal(invoked, 0);
  const sparse = clone(f.response); delete sparse.result.inputs[0];
  invalid(() => model.validateFccCaseCalculationResponse(sparse, f.request, f.detail));
  const cyclic = clone(f.response); cyclic.result.inputs.push(cyclic);
  invalid(() => model.validateFccCaseCalculationResponse(cyclic, f.request, f.detail));
  const exotic = clone(f.response); Object.setPrototypeOf(exotic, {private: 'not plain'});
  invalid(() => model.validateFccCaseCalculationResponse(exotic, f.request, f.detail));
});

proposed('extra fields missing keys nested mismatched status and unknown codes cannot pass', () => {
  const variants = [value => { value.extra = false; }, value => { delete value.result.context; },
    value => { value.result.status = 'insufficient_evidence'; }, value => { value.result.synthetic = false; },
    value => { value.result.calculation.native_result.value = 1; },
    value => { value.result.inputs[0].sources[0].quote = 'SYNTHETIC EXTRA QUOTE'; },
    value => { value.result.reason_codes = ['made_up_reason']; }, value => { value.error_code = 'made_up_error'; }];
  for (const mutate of variants) { const f = synthetic(); mutate(f.response); invalid(() => model.validateFccCaseCalculationResponse(f.response, f.request, f.detail)); }
});

proposed('separate calculation tickets reject an older response even when requests use the same case', () => {
  const gate = model.createFccCaseCalculationGate(), older = gate.begin(), newer = gate.begin();
  assert.equal(gate.current(older), false); assert.equal(gate.current(newer), true);
});

proposed('inputchange clear invalidates current ticket without waiting for the next submit', () => {
  const gate = model.createFccCaseCalculationGate(), ticket = gate.begin();
  assert.equal(gate.current(ticket), true); gate.clear(); assert.equal(gate.current(ticket), false);
  const next = gate.begin(); assert.equal(gate.current(next), true); assert.equal(gate.current(ticket), false);
});

proposed('calculation generation is independent from summary/detail reader generations', () => {
  const calculation = model.createFccCaseCalculationGate(), detail = model.createFccCaseCalculationGate();
  const calculationTicket = calculation.begin(), detailTicket = detail.begin();
  detail.clear(); assert.equal(calculation.current(calculationTicket), true); assert.equal(detail.current(detailTicket), false);
  calculation.clear(); assert.equal(calculation.current(calculationTicket), false);
});

test('039 browser CLI has exact modes and descriptor pin options without overrides', async () => {
  const tool=await import('./calculation_browser_check.cjs').catch(()=>null);
  assert.ok(tool,'039 dedicated browser checker must exist');
  assert.deepEqual(tool.default.parseOptions(['--mode','contract']),{mode:'contract',descriptor:undefined,sha256:undefined});
  for(const argv of [[],['--mode','actual'],['--mode','contract','--descriptor','C:/private/input.json'],
    ['--mode','actual','--descriptor','relative.json','--sha256','a'.repeat(64)],
    ['--mode','actual','--descriptor','C:/private/input.json','--sha256','a'.repeat(64)+'\n'],
    ['--mode','contract','--output','somewhere'],['--mode','contract','--mode','actual']])
    assert.throws(()=>tool.default.parseOptions(argv),/^Error: invalid_configuration$/);
});

test('claim dotted fields have a complete match and nested value keys obey16384 codepoints',()=>{
  const f=synthetic();f.detail.case.claims[0].field+='\n';
  invalid(()=>model.parseFccCaseCalculationCaseJson(JSON.stringify(f.detail),f.request.case_id,f.summary));
  const normal=synthetic(),claim=normal.detail.case.claims.find(value=>value.claim_id==='calibration');
  claim.value={['𠮷'.repeat(16384)]:false};
  assert.deepEqual(model.parseFccCaseCalculationCaseJson(JSON.stringify(normal.detail),normal.request.case_id,normal.summary).case.claims.find(value=>value.claim_id==='calibration').value,claim.value);
  claim.value={['𠮷'.repeat(16385)]:false};
  invalid(()=>model.parseFccCaseCalculationCaseJson(JSON.stringify(normal.detail),normal.request.case_id,normal.summary));
});
