const STATUS = {
  ok: {label: '정상 관측', tone: 'good', symbol: '●'},
  pending: {label: '진행 대기', tone: 'info', symbol: '◷'},
  invalid: {label: '데이터 무효', tone: 'warning', symbol: '!'},
  unsupported: {label: '동작 미지원', tone: 'warning', symbol: '?'},
  error: {label: '실행 오류', tone: 'danger', symbol: '!'},
  disconnected: {label: '통신 끊김', tone: 'danger', symbol: '×'},
};

export function describeStatus(status) {
  return Object.hasOwn(STATUS, status) ? STATUS[status] : {label: '지원 미확인', tone: 'warning', symbol: '?'};
}

const TYPES = new Set(['number', 'integer', 'boolean', 'string', 'object', 'array']);
export function validateSnapshot(data) {
  const fail = path => {throw Object.assign(new Error('invalid_snapshot'), {path});};
  const object = (value, path) => {if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(path);};
  const text = (value, path) => {if (typeof value !== 'string' || !value.length) fail(path);};
  const integer = (value, path) => {if (!Number.isSafeInteger(value) || value < 0) fail(path);};
  const array = (value, path) => {if (!Array.isArray(value)) fail(path);};
  const provenance = (value, path) => {if (value.synthetic !== true || value.hardware_verified !== false) fail(path);};
  object(data, 'response');
  if (data.schema_version !== 1 || data.mode !== 'virtual') fail('schema_version');
  provenance(data, 'provenance');
  for (const field of ['csrf_token', 'session_id', 'runtime_kind', 'generated_at']) text(data[field], field);
  if (!Number.isFinite(new Date(data.generated_at).getTime())) fail('generated_at');
  object(data.catalog, 'catalog'); array(data.catalog.profiles, 'catalog.profiles');
  const profiles = new Map();
  for (const profile of data.catalog.profiles) {
    object(profile, 'profile');
    for (const key of ['profile_id', 'model', 'manufacturer', 'role']) text(profile[key], `profile.${key}`);
    if (profiles.has(profile.profile_id)) fail('duplicate_profile');
    object(profile.ports, 'profile.ports');
    for (const direction of ['inputs', 'outputs']) {
      object(profile.ports[direction], `profile.ports.${direction}`);
      for (const kind of Object.values(profile.ports[direction])) text(kind, 'port.kind');
    }
    if (profile.evidence_refs !== undefined) array(profile.evidence_refs, 'evidence_refs');
    profiles.set(profile.profile_id, profile);
  }
  object(data.topology, 'topology');
  array(data.topology.devices, 'topology.devices'); array(data.topology.connections, 'topology.connections');
  const devices = new Map();
  for (const device of data.topology.devices) {
    object(device, 'device'); text(device.id, 'device.id'); text(device.profile_id, 'device.profile_id');
    if (devices.has(device.id) || !profiles.has(device.profile_id)) fail('device.profile');
    devices.set(device.id, device);
  }
  for (const connection of data.topology.connections) {
    object(connection, 'connection'); text(connection.kind, 'connection.kind');
    for (const [end, direction] of [['source', 'outputs'], ['target', 'inputs']]) {
      object(connection[end], `connection.${end}`);
      const {device_id: id, port} = connection[end];
      text(id, 'connection.device_id'); text(port, 'connection.port');
      if (!devices.has(id)) fail('connection.device');
      const ports = profiles.get(devices.get(id).profile_id).ports[direction];
      if (!Object.hasOwn(ports, port) || ports[port] !== connection.kind) fail('connection.port');
    }
  }
  layoutTopology(data.topology); // A cyclic snapshot cannot be published as a usable map.
  object(data.role_actions, 'role_actions');
  for (const actions of Object.values(data.role_actions)) {
    object(actions, 'actions');
    for (const declaration of Object.values(actions)) {
      object(declaration, 'action'); object(declaration.parameters, 'action.parameters');
      if (declaration.completion !== undefined) text(declaration.completion, 'action.completion');
      for (const schema of Object.values(declaration.parameters)) {
        object(schema, 'parameter_schema');
        if (!TYPES.has(schema.type)) fail('parameter.type');
        if (schema.required !== undefined && typeof schema.required !== 'boolean') fail('parameter.required');
        if (schema.unit !== undefined && typeof schema.unit !== 'string') fail('parameter.unit');
        if (schema.enum !== undefined) array(schema.enum, 'parameter.enum');
      }
    }
  }
  object(data.observations, 'observations'); provenance(data.observations, 'observations.provenance');
  integer(data.observations.tick, 'tick'); integer(data.observations.setup_revision, 'setup_revision');
  object(data.observations.devices, 'observations.devices');
  if (Object.keys(data.observations.devices).length !== devices.size) fail('observations.devices.length');
  for (const [id, observation] of Object.entries(data.observations.devices)) {
    object(observation, 'observation'); provenance(observation, 'observation.provenance');
    if (!devices.has(id) || observation.profile_id !== devices.get(id).profile_id) fail('observation.profile');
    integer(observation.tick, 'observation.tick'); integer(observation.setup_revision, 'observation.setup_revision');
    text(observation.status, 'observation.status'); object(observation.values, 'observation.values');
    // state can be a structured role-specific public object, not just a label.
    if (observation.state !== undefined && typeof observation.state !== 'string') object(observation.state, 'observation.state');
  }
  if (data.coverage === null || typeof data.coverage !== 'object') fail('coverage');
  return data;
}

export function parseParameters(schemas, raw) {
  const result = {};
  for (const [name, schema] of Object.entries(schemas)) {
    const value = raw[name] ?? '';
    if (value === '') {
      if (schema.required) throw new Error(`${name}: 필수 인수를 입력하세요.`);
      continue;
    }
    let parsed;
    if (schema.type === 'number' || schema.type === 'integer') {
      parsed = Number(value);
      if (!value.trim() || !Number.isFinite(parsed) || (schema.type === 'integer' && !Number.isSafeInteger(parsed))) throw new Error(`${name}: 유효한 ${schema.type === 'integer' ? '정수' : '숫자'}가 필요합니다.`);
      if ((schema.minimum !== undefined && parsed < schema.minimum) || (schema.maximum !== undefined && parsed > schema.maximum)) throw new Error(`${name}: 선언된 범위를 확인하세요.`);
    } else if (schema.type === 'boolean') {
      if (!['true', 'false'].includes(value)) throw new Error(`${name}: true 또는 false를 선택하세요.`);
      parsed = value === 'true';
    } else if (schema.type === 'object' || schema.type === 'array') {
      try {parsed = JSON.parse(value);} catch {throw new Error(`${name}: JSON 형식을 확인하세요.`);}
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed) !== (schema.type === 'array')) throw new Error(`${name}: ${schema.type} 형식이 필요합니다.`);
    } else parsed = value;
    if (schema.enum && !schema.enum.some(option => option === parsed)) throw new Error(`${name}: 선언된 선택값이 필요합니다.`);
    result[name] = parsed;
  }
  return result;
}

export function layoutTopology(topology) {
  const nodes = new Map(topology.devices.map(device => [device.id, {...device, column: 0, row: 0}]));
  const incoming = new Map([...nodes.keys()].map(id => [id, 0]));
  const outgoing = new Map([...nodes.keys()].map(id => [id, []]));
  for (const edge of topology.connections) {
    if (!nodes.has(edge.source.device_id) || !nodes.has(edge.target.device_id)) throw new Error('invalid_snapshot:edge');
    incoming.set(edge.target.device_id, incoming.get(edge.target.device_id) + 1);
    outgoing.get(edge.source.device_id).push(edge.target.device_id);
  }
  const queue = [...incoming].filter(([, count]) => count === 0).map(([id]) => id);
  for (let i = 0; i < queue.length; i++) {
    const source = queue[i];
    for (const target of outgoing.get(source)) {
      nodes.get(target).column = Math.max(nodes.get(target).column, nodes.get(source).column + 1);
      incoming.set(target, incoming.get(target) - 1);
      if (incoming.get(target) === 0) queue.push(target);
    }
  }
  if (queue.length !== nodes.size) throw new Error('invalid_snapshot:cycle');
  const rows = new Map();
  for (const node of nodes.values()) {
    node.row = rows.get(node.column) || 0;
    rows.set(node.column, node.row + 1);
  }
  return [...nodes.values()];
}

export function summarizeProfiles(data) {
  const deployed = new Set(data.topology.devices.map(device => device.profile_id));
  return {profiles: data.catalog.profiles.length, deployed: data.topology.devices.length,
    roles: new Set(data.catalog.profiles.map(profile => profile.role)).size,
    undeployed: data.catalog.profiles.filter(profile => !deployed.has(profile.profile_id)).length};
}

export const stringify = value => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
export function seoulTime(iso) {
  return new Intl.DateTimeFormat('ko-KR', {timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false}).format(new Date(iso));
}
