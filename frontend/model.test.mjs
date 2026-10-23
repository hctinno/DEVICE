import test from 'node:test';
import assert from 'node:assert/strict';
import {describeState, factSources, filterIntakes, noticeContext} from './model.mjs';

test('queue, running, failure, deferral and unsupported states stay distinguishable', () => {
  const base = {status: 'awaiting_analysis', revision: 1, jobs: [{revision: 1, state: 'queued'}]};
  assert.equal(describeState(base).code, 'awaiting_analysis');
  assert.equal(describeState({...base, jobs: [{revision: 1, state: 'running'}]}).code, 'analyzing');
  assert.equal(describeState({...base, jobs: [{revision: 0, state: 'running'}]}).code, 'awaiting_analysis');
  assert.equal(describeState({...base, status: 'analysis_failed'}).code, 'analysis_failed');
  assert.equal(describeState({...base, deferred: true}).code, 'deferred');
  assert.equal(describeState({...base, status: 'new_state'}).code, 'unsupported');
  assert.equal(describeState({...base, jobs: [{revision: 1, state: 'new_job_state'}]}).code, 'unsupported');
});

test('analysis completion or plan request is never a completed test', () => {
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'prepare_plan'}}).code, 'plan_pending');
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'propose_start'}}).code, 'propose_start');
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'needs_information'}}).code, 'needs_information');
  assert.equal(describeState({status: 'analyzed', analysis: null}).code, 'invalid');
  assert.equal(describeState({status: 'analyzed', analysis: {next_action: 'future'}}).code, 'unsupported');
});

test('projected facts only cite matching candidates and never forge citations for user answers', () => {
  const citation = {path: 'request.txt', quote: '<script>alert(1)</script>'};
  const record = {analysis: {facts: {market: {value: 'EU', status: 'explicit'}}, submitted: {facts: [
    {field: 'market', value: 'EU', status: 'explicit', evidence: [citation]},
    {field: 'market', value: 'US', status: 'explicit', evidence: [{path: 'other.txt'}]},
    {field: 'market', value: 'EU', status: 'uncertain', evidence: [{path: 'uncertain.txt'}]},
  ]}}};
  assert.deepEqual(factSources(record, 'market'), [citation]);
  record.analysis.facts.market = {value: 'EU', status: 'user_confirmed', event_id: 'ANSWER-1'};
  assert.deepEqual(factSources(record, 'market'), []);
  assert.deepEqual(factSources({analysis: {facts: {model: {value: 'X', status: 'explicit'}}}}, 'model'), []);
});

test('Korean search combines with filters without hiding unsupported or failed work', () => {
  const records = [
    {bundle: '새 의뢰', source_id: 'INBOX', status: 'awaiting_analysis'},
    {bundle: '보류 의뢰', status: 'analyzed', deferred: true},
    {bundle: '실패 의뢰', status: 'analysis_failed'},
    {bundle: '알 수 없음', status: 'future'},
  ];
  assert.equal(filterIntakes(records, {query: '의뢰'}).length, 3);
  assert.equal(filterIntakes(records, {query: 'INBOX', filter: 'waiting'}).length, 1);
  assert.equal(filterIntakes(records, {filter: 'attention'}).length, 2);
  assert.equal(filterIntakes(records, {filter: 'deferred'}).length, 1);
  assert.equal(filterIntakes(records, {filter: 'failed'}).length, 1);
});

test('notifications remain creation-time records even on the same revision', () => {
  assert.equal(noticeContext({revision: 1}, {revision: 2}).code, 'previous_revision');
  assert.equal(noticeContext({revision: 2}, {revision: 2}).code, 'same_revision');
  assert.equal(noticeContext({revision: 3}, {revision: 2}).code, 'unknown_revision');
});

test('an expired lease is not presented as a currently running worker', () => {
  const record = {status: 'awaiting_analysis', revision: 1, jobs: [{revision: 1, state: 'running', lease_until: 100}]};
  assert.equal(describeState(record, 99).code, 'analyzing');
  assert.equal(describeState(record, 100).code, 'lease_expired');
  assert.equal(describeState(record, 101).code, 'lease_expired');
});
