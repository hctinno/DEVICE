import test from 'node:test';
import assert from 'node:assert/strict';
import {validateSnapshot} from './model.mjs';

function fixture() {
  const analysis = {
    facts: {market: {value: 'US', status: 'explicit'}},
    questions: [{key: 'missing_firmware', field: 'firmware', message: '펌웨어가 필요합니다.'}],
    next_action: 'needs_information',
    submitted: {producer: {kind: 'fixture', name: 'synthetic test'}, facts: [
      {field: 'market', value: 'US', status: 'explicit', evidence: [
        {path: 'request.txt', sha256: 'a'.repeat(64), line_start: 1, line_end: 1, quote: 'Market US', role: 'request'},
      ]},
    ]},
    unread_documents: [],
  };
  return {schema_version: 1, generated_at: '2026-10-23T12:00:00Z', intakes: [{
    intake_id: 'I-1', source_id: 'S-1', bundle: '합성 의뢰', revision: 1, status: 'analyzed',
    synthetic: true, deferred: false, delegated: false, measurement_support: 'unverified', analysis,
    files: [], history: [{revision: 1, created_at: 1792756800, files: [], synthetic: 1}],
    jobs: [{job_id: 'J-1', revision: 1, state: 'completed', attempt: 1, error_code: null, lease_until: null}],
  }], notifications: [{notification_id: 1, intake_id: 'I-1', revision: 1, payload: structuredClone(analysis)}]};
}

test('valid snapshot preserves every field and unknown state without rewriting evidence', () => {
  const value = fixture();
  value.intakes[0].status = 'future_status';
  value.intakes[0].analysis.submitted.facts[0].evidence = [];
  const before = structuredClone(value);
  assert.equal(validateSnapshot(value), value);
  assert.deepEqual(value, before);
  value.intakes[0].analysis.submitted = undefined;
  assert.equal(validateSnapshot(value), value);
});

const invalid = [
  ['question key', 'intakes[0].analysis.questions[0].key', data => { delete data.intakes[0].analysis.questions[0].key; }],
  ['candidate value', 'intakes[0].analysis.submitted.facts[0].value', data => { data.intakes[0].analysis.submitted.facts[0].value = null; }],
  ['candidate object', 'intakes[0].analysis.submitted.facts[0]', data => { data.intakes[0].analysis.submitted.facts[0] = []; }],
  ['question array', 'intakes[0].analysis.questions', data => { data.intakes[0].analysis.questions = {}; }],
  ['facts object', 'intakes[0].analysis.facts', data => { data.intakes[0].analysis.facts = []; }],
  ['citation array', 'intakes[0].analysis.submitted.facts[0].evidence', data => { data.intakes[0].analysis.submitted.facts[0].evidence = 'path'; }],
  ['citation object', 'intakes[0].analysis.submitted.facts[0].evidence[0]', data => { data.intakes[0].analysis.submitted.facts[0].evidence = [null]; }],
  ['job state', 'intakes[0].jobs[0].state', data => { data.intakes[0].jobs[0].state = {}; }],
  ['file array', 'intakes[0].history[0].files', data => { data.intakes[0].history[0].files = {}; }],
  ['notification object', 'notifications[0]', data => { data.notifications[0] = null; }],
  ['notice question', 'notifications[0].payload.questions[0].message', data => { data.notifications[0].payload.questions[0].message = []; }],
];
for (const [name, path, mutate] of invalid) {
  test(`rejects malformed ${name} at its field boundary`, () => {
    const value = fixture();
    mutate(value);
    assert.throws(() => validateSnapshot(value), error => error.message === 'invalid_snapshot' && error.path === path);
  });
}

test('V2 text and PDF citations retain context and page-local coordinates while V1 remains valid', () => {
  const data = fixture();
  const submitted = data.intakes[0].analysis.submitted;
  submitted.schema_version = 2;
  submitted.context_id = 'context:synthetic-1';
  const source = submitted.facts[0].evidence[0];
  source.kind = 'text_line';
  assert.equal(validateSnapshot(data), data);
  Object.assign(source, {kind:'pdf_page', extraction_id:'extraction:synthetic-1', page_number:2, text_sha256:'b'.repeat(64)});
  assert.equal(validateSnapshot(data), data);
  assert.equal(source.page_number, 2);
  assert.equal(validateSnapshot(fixture()).schema_version, 1);
});

test('V2 requires context and exact typed citation fields with valid page line and extraction identities', () => {
  for (const mutate of [s => {delete s.context_id;}, s => {s.context_id = [];}, s => {s.schema_version = null;},
    s => {delete s.facts[0].evidence[0].extraction_id;}, s => {s.facts[0].evidence[0].page_number = 0;},
    s => {s.facts[0].evidence[0].kind = 'page';}, s => {s.facts[0].evidence[0].line_end = 0;},
    s => {s.facts[0].evidence[0].line_start = 3;}, s => {s.facts[0].evidence[0].text_sha256 = 'bad';},
    s => {s.facts[0].evidence[0].seed = 0;}, s => {s.facts[0].evidence[0].role = 'future';},
    s => {s.facts[0].evidence[0].sha256 += '\n';}, s => {s.facts[0].evidence[0].text_sha256 += '\n';}]) {
    const data = fixture(), submitted = data.intakes[0].analysis.submitted;
    Object.assign(submitted, {schema_version:2, context_id:'context:synthetic-1'});
    Object.assign(submitted.facts[0].evidence[0], {kind:'pdf_page', extraction_id:'extract:1', page_number:2, text_sha256:'b'.repeat(64)});
    mutate(submitted);
    assert.throws(() => validateSnapshot(data), /invalid_snapshot/);
  }
});
