import test from 'node:test';
import assert from 'node:assert/strict';
import {validateSnapshot, parseParameters, describeStatus, layoutTopology, summarizeProfiles} from './model.mjs';

const fixture = () => ({schema_version: 1, mode: 'virtual', synthetic: true, hardware_verified: false,
  runtime_kind: 'synthetic_fixture', session_id: 'session', csrf_token: 'csrf', generated_at: '2026-10-24T01:00:00+00:00',
  catalog: {profiles: [
    {profile_id: 'p', model: 'Demo', manufacturer: 'DGM', role: 'power_supply', variant: 'dc', ports: {inputs: {}, outputs: {power: 'power'}}, evidence_refs: []},
    {profile_id: 'context', model: 'Aux', manufacturer: 'DGM', role: 'inspection_microscope', variant: 'context', ports: {inputs: {}, outputs: {}}, evidence_refs: []},
  ]}, topology: {devices: [{id: 'supply', profile_id: 'p'}], connections: []},
  role_actions: {power_supply: {configure: {parameters: {voltage: {type: 'number', required: true, unit: 'V'}, enabled: {type: 'boolean', required: false, unit: ''}}, completion: 'immediate'}}},
  observations: {tick: 0, setup_revision: 0, synthetic: true, hardware_verified: false, devices: {
    supply: {profile_id: 'p', tick: 0, setup_revision: 0, synthetic: true, hardware_verified: false, status: 'ok', state: 'off', values: {voltage_v: 0}},
  }}, coverage: {profiles: [{profile_id: 'p', implemented: true, acceptance: 'not_run'}]}});

test('accepts undeployed context profiles without inventing their execution coverage', () => {
  const data = validateSnapshot(fixture());
  assert.deepEqual(summarizeProfiles(data), {profiles: 2, deployed: 1, roles: 2, undeployed: 1});
});

test('rejects wrong provenance missing observation and malformed action schemas', () => {
  for (const mutate of [s => {s.hardware_verified = true;}, s => {s.observations.synthetic = false;},
    s => {delete s.observations.devices.supply;}, s => {s.observations.devices.supply.values = null;},
    s => {s.observations.devices.supply.profile_id = 'absent';}, s => {s.observations.tick = -1;},
    s => {s.role_actions.power_supply.configure.parameters.voltage.type = 'file';},
    s => {s.topology.connections.push({source: {device_id: 'absent', port: 'power'}, target: {device_id: 'supply', port: 'power'}, kind: 'power'});},
    s => {s.catalog.profiles.push({...s.catalog.profiles[0]});}]) {
    const data = fixture(); mutate(data);
    assert.throws(() => validateSnapshot(data), /invalid_snapshot/);
  }
});

test('unknown and prototype-named statuses are visible as unrecognized instead of success', () => {
  for (const status of ['constructor', '__proto__', 'future_state']) {
    assert.equal(describeStatus(status).tone, 'warning');
    assert.equal(describeStatus(status).label, '지원 미확인');
  }
  assert.equal(describeStatus('invalid').label, '데이터 무효');
  assert.equal(describeStatus('pending').label, '진행 대기');
});

test('parses declared numeric boolean JSON and optional inputs without silent zero', () => {
  const schema = {voltage: {type: 'number', required: true}, count: {type: 'integer'}, enabled: {type: 'boolean'}, settings: {type: 'object'}, items: {type: 'array'}};
  assert.deepEqual(parseParameters(schema, {voltage: '3.8', count: '', enabled: 'false', settings: '{"channel":1}', items: '[1,2]'}), {voltage: 3.8, enabled: false, settings: {channel: 1}, items: [1, 2]});
  for (const values of [{voltage: ''}, {voltage: 'NaN'}, {voltage: '1e999'}, {voltage: '3', count: '1.1'}, {voltage: '3', enabled: 'yes'}, {voltage: '3', settings: '[]'}]) {
    assert.throws(() => parseParameters(schema, values));
  }
});

test('uses exact declared enum values and handles optional booleans explicitly', () => {
  const schema = {route: {type: 'string', required: true, enum: ['A', 'B']}, enabled: {type: 'boolean'}};
  assert.deepEqual(parseParameters(schema, {route: 'A', enabled: ''}), {route: 'A'});
  assert.throws(() => parseParameters(schema, {route: 'C', enabled: ''}));
});

test('DAG layout respects declared connections and includes disconnected devices', () => {
  const topology = {devices: [{id: 'meter'}, {id: 'dut'}, {id: 'supply'}, {id: 'chamber'}], connections: [
    {source: {device_id: 'supply'}, target: {device_id: 'dut'}, kind: 'power'},
    {source: {device_id: 'dut'}, target: {device_id: 'meter'}, kind: 'rf'},
  ]};
  const nodes = layoutTopology(topology);
  assert.equal(nodes.length, 4);
  const column = Object.fromEntries(nodes.map(n => [n.id, n.column]));
  assert.ok(column.supply < column.dut && column.dut < column.meter);
  assert.equal(column.chamber, 0);
  assert.equal(layoutTopology({devices: [], connections: []}).length, 0);
});
