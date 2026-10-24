/* 027 checks the real product server. Actual PDFs stay in the trusted Python caller. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createHash} = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {reserveEvidence} = require('../intake_fixture_browser_check.cjs');
const ROOT = fs.realpathSync(path.resolve(__dirname, '../..'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const save = (folder, name, value) => fs.writeFileSync(path.join(folder, name), JSON.stringify(value, null, 2) + '\n', {flag: 'wx'});
const wait = async (promise, ms = 30000) => {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(Error('route_check_timeout')), ms); })]); }
  finally { clearTimeout(timer); }
};

function parseOptions(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index], value = argv[index + 1];
    if (!['--mode', '--caller-config', '--sha256'].includes(key) || Object.hasOwn(values, key)
        || typeof value !== 'string' || value.length === 0) throw Error('invalid_configuration');
    values[key] = value;
  }
  const mode = values['--mode'], config = values['--caller-config'], sha256 = values['--sha256'];
  if (!['contract', 'actual'].includes(mode) || (mode === 'contract' && (config || sha256))
      || (mode === 'actual' && (!config || !sha256))) throw Error('invalid_configuration');
  if (config && (!path.isAbsolute(config) || path.extname(config).toLowerCase() !== '.json'
      || /[\0\r\n]/.test(config) || /^\\\\/.test(config))) throw Error('invalid_configuration');
  if (sha256 && !/^[a-f0-9]{64}$/.test(sha256)) throw Error('invalid_configuration');
  return {mode, config, sha256};
}

function readPinned(file, pin, cap) {
  if (!path.isAbsolute(file) || fs.lstatSync(file).isSymbolicLink()
      || path.relative(fs.realpathSync(file), path.resolve(file)) !== '') throw Error('invalid_input_file');
  const fd = fs.openSync(file, 'r');
  try {
    const before = fs.fstatSync(fd);
    if (!before.isFile() || before.size <= 0 || before.size > cap) throw Error('input_limit_exceeded');
    const bytes = Buffer.alloc(before.size + 1);
    let count = 0, size;
    while (count < bytes.length && (size = fs.readSync(fd, bytes, count, bytes.length - count, null))) count += size;
    const after = fs.fstatSync(fd), current = fs.statSync(file);
    if (count !== before.size || before.ino !== after.ino || before.mtimeMs !== after.mtimeMs
        || current.ino !== before.ino || current.mtimeMs !== before.mtimeMs || hash(bytes.subarray(0, count)) !== pin) {
      throw Error('input_pin_mismatch');
    }
    return bytes.subarray(0, count);
  } finally { fs.closeSync(fd); }
}

function sourceHashes() {
  const files = ['labflow/schema.sql', 'tests/test_fcc_case_ui_server.py', 'docs/fcc/fcc_case_route_usage.md'];
  const visit = (directory, extensions) => {
    for (const entry of fs.readdirSync(path.join(ROOT, directory), {withFileTypes: true})) {
      assert(!entry.isSymbolicLink(), 'linked_source');
      const name = directory + '/' + entry.name;
      if (entry.isDirectory() && !['__pycache__', 'evidence'].includes(entry.name)) visit(name, extensions);
      else if (entry.isFile() && extensions.includes(path.extname(name))) files.push(name);
    }
  };
  visit('labflow', ['.py']); visit('frontend', ['.js', '.mjs', '.cjs', '.html', '.css']);
  visit('control_sources', ['.json']); visit('virtual_profiles', ['.json']);
  if (fs.existsSync(path.join(ROOT, 'equipment.sqlite3'))) files.push('equipment.sqlite3');
  return Object.fromEntries(files.sort().map(name => {
    const file = path.join(ROOT, name), info = fs.statSync(file);
    return [name, {sha256: hash(fs.readFileSync(file)), dev: info.dev, ino: info.ino,
      bytes: info.size, mtime_ms: info.mtimeMs, mode: info.mode}];
  }));
}

const PYTHON_BOOT = String.raw`
from pathlib import Path
from io import BytesIO
from copy import deepcopy
import hashlib, json, math, os, re, stat, sys, threading, time, traceback

root = Path.cwd().resolve()
request = json.loads(sys.stdin.readline())
evidence = Path(request['evidence']).resolve()
if evidence.parent != root / '.local' or not evidence.is_dir():
    raise SystemExit(2)
servers, threads, inputs = [], [], {}
guard = False
blocked_original_opens = 0

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def identity(s):
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode]

def plain_json(blob, cap, depth_limit, node_limit):
    if len(blob) > cap or blob.startswith(b'\xef\xbb\xbf'):
        raise ValueError('input_limit_or_encoding')
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    def bad(value):
        raise ValueError('nonfinite_json')
    value = json.loads(blob.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=bad)
    nodes = 0
    def visit(item, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > node_limit or depth > depth_limit:
            raise ValueError('input_structure_limit')
        if type(item) is str:
            item.encode('utf-8', errors='strict')
        elif type(item) in (dict, list):
            for child in (list(item.keys()) + list(item.values()) if type(item) is dict else item):
                visit(child, depth + 1)
        elif type(item) is float and not math.isfinite(item):
            raise ValueError('nonfinite_json')
    visit(value)
    return value

def local_file(value, suffix):
    if type(value) is not str or any(c in value for c in '\x00\r\n'):
        raise ValueError('invalid_file')
    p = Path(value)
    if not p.is_absolute() or p.suffix.lower() != suffix or value.startswith(('\\\\', '//')):
        raise ValueError('invalid_file')
    for part in (p, *p.parents):
        info = part.lstat()
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('linked_file')
    return p

def read_file(p, size, sha, cap):
    if type(size) is not int or not 1 <= size <= min(cap, 9007199254740991):
        raise ValueError('invalid_size')
    if type(sha) is not str or re.fullmatch('[a-f0-9]{64}', sha, re.ASCII) is None:
        raise ValueError('invalid_pin')
    with p.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != size:
            raise ValueError('invalid_size')
        blob = stream.read(cap + 1)
        after = os.fstat(stream.fileno())
    if identity(before) != identity(after) or identity(before) != identity(p.stat()) or len(blob) != size or digest(blob) != sha:
        raise ValueError('input_changed')
    inputs[str(p)] = {'identity': identity(before), 'bytes': size, 'sha256': sha}
    return blob

def descriptor(value, suffix, cap):
    if type(value) is not dict or set(value) != {'path', 'sha256', 'bytes'}:
        raise ValueError('invalid_descriptor')
    return read_file(local_file(value['path'], suffix), value['bytes'], value['sha256'], cap)

def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(v, b[k]) for k, v in a.items())
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b

def synthetic_packet():
    from reportlab.pdfgen import canvas
    from labflow.document_extract import extract_document, page_citation
    stream = BytesIO()
    writer = canvas.Canvas(stream, invariant=1, pageCompression=0)
    lines = ['SYNTHETIC REPORT A', 'SYNTHETIC REPORT B', 'SYNTHETIC legal issuer', 'SYNTHETIC address',
             '2025-05-01', 'smartphone', 'router', 'SYNTHETIC manufacturer', 'SYNTHETIC model',
             '47 CFR 15.247', 'SYNTHETIC METHOD 2013', 'SYNTHETIC METHOD 2023', 'SYNTHETIC FCC',
             'SYNTHETIC meter', 'Power 0 dBm', 'Enabled False', '<script>window.routePwned=true</script>']
    for i, line in enumerate(lines):
        writer.drawString(40, 740 - 20 * i, line)
    writer.showPage(); writer.save()
    blob = stream.getvalue(); sha = digest(blob)
    extracted = extract_document(blob, 'synthetic027.pdf')
    def claim(cid, field, value, line, basis='report_fact', unit=None):
        citation = page_citation(extracted, 1, line, line)
        return {'claim_id': cid, 'field': field, 'value': value, 'unit': unit, 'status': 'reviewed', 'basis': basis,
                'evidence': [{'document_id': 'SYNTH-DOC-027', 'source_sha256': sha, 'file_page': 1,
                              'printed_page': 'unknown', 'table': None, 'row': None, 'column': None, 'footnotes': [],
                              'text_sha256': citation['text_sha256'], 'line_start': line, 'line_end': line, 'quote': citation['quote']}]}
    document = {'document_id': 'SYNTH-DOC-027', 'sha256': sha, 'size_bytes': len(blob), 'physical_pages': 1,
                'exhibits': [{'exhibit_id': 'SYNTH-EXHIBIT-027', 'fcc_id': 'SYNTHETIC-FCC', 'application_id': None,
                              'exhibit_type': 'synthetic report', 'url': 'https://example.invalid/report.pdf',
                              'source_kind': 'mirror', 'accessed_at': '2026-10-24T11:00:00+09:00',
                              'official_match_status': 'blocked', 'official_url': None, 'search_ids': []}],
                'rights': {'status': 'private_only', 'notes': 'Synthetic route only',
                           'public_redistribution_allowed': False, 'external_model_use_allowed': False}}
    cases = []
    for i, family in enumerate(['smartphone', 'router']):
        claims = [claim('number', 'report.number', 'SYNTHETIC REPORT ' + ('A' if i == 0 else 'B'), i + 1),
                  claim('class', 'issuer.classification', 'hct_korea', 3, 'developer_inference'),
                  claim('legal', 'issuer.legal_name', lines[2], 3), claim('address', 'issuer.address', lines[3], 4),
                  claim('date', 'report.issue_date', lines[4], 5), claim('family', 'product.family', family, 6 + i),
                  claim('maker', 'product.manufacturer', lines[7], 8), claim('model', 'product.models', [lines[8]], 9),
                  claim('rule', 'method.rules', [lines[9]], 10),
                  claim('method', 'method.references', [lines[10 + i]], 11 + i, 'standard_reference_only'),
                  claim('fcc', 'report.fcc_ids', ['SYNTHETIC-FCC'], 13),
                  claim('equipment', 'equipment.models', [lines[13]], 14),
                  claim('zero', 'result.power', 0, 15, unit='dBm'), claim('false', 'setting.enabled', False, 16),
                  claim('escaped', 'setting.note', lines[16], 17)]
        cases.append({'case_id': 'SYNTH-CASE-' + ('A' if i == 0 else 'B'), 'report_group_id': 'SYNTH-REPORT-' + str(i),
                      'document_ids': [document['document_id']], 'claims': claims, 'relations': [], 'reuse_group_ids': []})
    return {'schema_version': 1, 'corpus_id': 'SYNTHETIC-ROUTE027',
            'scope': {'issue_date_from': '2025-01-01', 'cutoff_at': '2026-10-24T12:00:00+09:00',
                      'timezone': 'Asia/Seoul', 'population_status': 'unconfirmed', 'synthetic': True,
                      'search_scope_notes': ['Synthetic route contract only'], 'unverified_ranges': ['Population unknown']},
            'searches': [], 'documents': [document], 'cases': cases}, {sha: blob}

def audit(event, args):
    global blocked_original_opens
    if guard and event == 'open' and type(args[0]) in (str, bytes):
        key = os.path.normcase(os.fsdecode(args[0]))
        if key in {os.path.normcase(p) for p in inputs}:
            blocked_original_opens += 1
            raise RuntimeError('request_time_original_io_forbidden')

try:
    from labflow.fcc_report_cases import FccReportCaseCatalog
    from labflow import fcc_report_cases, ui_server
    from labflow.store import Store
    import pypdf
    for module in [fcc_report_cases, ui_server]:
        if Path(module.__file__).resolve().parent != root / 'labflow':
            raise ValueError('wrong_source_module')
    mode = request['mode']; expected = None
    if mode == 'actual':
        p = local_file(request['config'], '.json')
        config = plain_json(read_file(p, p.stat().st_size, request['sha256'], 65536), 65536, 16, 50000)
        if (type(config) is not dict or set(config) != {'schema_version', 'kind', 'packet', 'pdf_sources', 'expected_bundle'}
                or type(config['schema_version']) is not int or config['schema_version'] != 1
                or config['kind'] != 'fcc_case_route_caller_input'):
            raise ValueError('invalid_config')
        packet = plain_json(descriptor(config['packet'], '.json', 4 * 1024**2), 4 * 1024**2, 16, 50000)
        rows = config['pdf_sources']
        if type(rows) is not list or not 1 <= len(rows) <= 16:
            raise ValueError('invalid_sources')
        sources = {}
        for row in rows:
            blob = descriptor(row, '.pdf', 16 * 1024**2)
            if row['sha256'] in sources or sum(map(len, sources.values())) + len(blob) > 64 * 1024**2:
                raise ValueError('invalid_sources')
            sources[row['sha256']] = blob
        expected = plain_json(descriptor(config['expected_bundle'], '.json', 32 * 1024**2), 32 * 1024**2, 20, 1000000)
        if type(expected) is not dict or set(expected) != {'schema_version', 'summary', 'cases'} or expected['schema_version'] != 1:
            raise ValueError('invalid_expected_bundle')
        if packet['scope']['synthetic'] is not False:
            raise ValueError('actual_requires_nonsynthetic_packet')
    elif mode == 'contract':
        packet, sources = synthetic_packet()
    else:
        raise ValueError('invalid_mode')
    started = time.monotonic()
    catalog = FccReportCaseCatalog(packet, sources)
    construction_seconds = time.monotonic() - started
    summary = catalog.summary()
    ids = [row['case_id'] for row in summary['case_previews']]
    if expected is not None:
        ordered_ids = [row['case']['case_id'] for row in expected['cases']]
        if len(set(ordered_ids)) != len(ordered_ids) or set(ordered_ids) != set(ids):
            raise ValueError('expected_case_set_mismatch')
    else:
        ordered_ids = ids
    bundle = {'schema_version': 1, 'summary': summary, 'cases': [catalog.case(cid) for cid in ordered_ids]}
    if expected is not None and not same(bundle, expected):
        raise ValueError('actual_expected_bundle_mismatch')
    for dto in [summary, *bundle['cases']]:
        if len(json.dumps(dto, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 8 * 1024**2:
            raise ValueError('response_limit')
    encoded = (json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
    (evidence / 'constructed-bundle.json').write_bytes(encoded)
    workspace = evidence / 'workspace'
    store = Store(workspace)
    db_before = digest(store.db.read_bytes())
    db_identity_before = identity(store.db.stat())
    ports = {}
    variants = [('unconfigured', None), ('configured', catalog)]
    if mode == 'contract':
        empty_packet = deepcopy(packet); empty_packet['documents'] = []; empty_packet['cases'] = []
        variants.append(('empty', FccReportCaseCatalog(empty_packet, {})))
    for name, value in variants:
        server = ui_server.create_server(workspace, port=0, fcc_case_catalog=value)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        servers.append(server); threads.append(thread); ports[name] = server.server_port
    receipt = {'actual_class_constructed': True, 'catalog_class': type(catalog).__name__, 'input_mode': mode,
               'source_module_sha256': digest(Path(fcc_report_cases.__file__).read_bytes()),
               'ui_server_sha256': digest(Path(ui_server.__file__).read_bytes()), 'pypdf_version': pypdf.__version__,
               'pypdf_module_sha256': digest(Path(pypdf.__file__).read_bytes()), 'construction_seconds': construction_seconds,
               'pdf_count': len(sources), 'pdf_bytes': sum(map(len, sources.values())),
               'physical_pages': sum(d['physical_pages'] for d in summary['documents']), 'case_count': len(ids),
               'expected_bundle_equal': expected is not None, 'constructed_bundle_sha256': digest(encoded),
               'expected_bundle_sha256': config['expected_bundle']['sha256'] if expected is not None else None,
               'source_before': inputs, 'workspace_db_before': db_before, 'workspace_db_identity_before': db_identity_before, 'ports': ports,
               'request_time_original_io_guard': True, 'pdf_or_plaintext_copy_written': False}
    (evidence / 'caller-startup.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sys.addaudithook(audit); guard = True
    print(json.dumps({'ready': True, 'ports': ports}), flush=True)
    for line in sys.stdin:
        if line.strip() == 'shutdown':
            break
except Exception:
    (evidence / 'caller-failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print(json.dumps({'error': 'fcc_case_route_caller_failed'}), flush=True)
finally:
    for server in servers:
        server.shutdown(); server.server_close()
    for thread in threads:
        thread.join(timeout=5)
    guard = False
    if servers:
        unchanged = all(identity(Path(p).stat()) == row['identity'] and digest(Path(p).read_bytes()) == row['sha256']
                        for p, row in inputs.items())
        final = {'server_closed': all(not t.is_alive() for t in threads), 'source_inputs_unchanged': unchanged,
                 'workspace_db_unchanged': digest(store.db.read_bytes()) == db_before and identity(store.db.stat()) == db_identity_before,
                 'request_time_original_open_attempts': blocked_original_opens}
        (evidence / 'caller-shutdown.json').write_text(json.dumps(final, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'closed': final['server_closed']}), flush=True)
`;

async function startCaller(options, evidence) {
  const executable = process.env.FCC_CASE_ROUTE_PYTHON || path.join(ROOT, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!path.isAbsolute(executable) || !fs.statSync(executable).isFile()) throw Error('invalid_python_executable');
  const child = spawn(executable, ['-X', 'utf8', '-B', '-c', PYTHON_BOOT], {
    cwd: ROOT, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
    env: {...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1', PYTHONNOUSERSITE: '1', PYTHONPATH: ROOT},
  });
  const stdout = [], stderr = [], outputCap = 1024 * 1024;
  let stdoutBytes = 0, stderrBytes = 0, pending = '', settled = false, exitCode = null, outputExceeded = false;
  let readyResolve, readyReject, closedResolve;
  const ready = new Promise((resolve, reject) => { readyResolve = resolve; readyReject = reject; });
  const closed = new Promise(resolve => { closedResolve = resolve; });
  child.stdout.on('data', bytes => {
    const retained = bytes.subarray(0, Math.max(0, outputCap - stdoutBytes));
    stdout.push(retained); stdoutBytes += bytes.length;
    if (stdoutBytes > outputCap) { outputExceeded = true; child.kill(); readyReject(Error('caller_output_limit')); return; }
    pending += retained.toString('utf8');
    let index;
    while ((index = pending.indexOf('\n')) >= 0) {
      const line = pending.slice(0, index); pending = pending.slice(index + 1);
      try {
        const value = JSON.parse(line);
        if (value.ready === true && !settled) { settled = true; readyResolve(value); }
        else if (value.error) readyReject(Error('fcc_case_route_caller_failed'));
      } catch { readyReject(Error('caller_invalid_output')); }
    }
  });
  child.stderr.on('data', bytes => {
    stderr.push(bytes.subarray(0, Math.max(0, outputCap - stderrBytes))); stderrBytes += bytes.length;
    if (stderrBytes > outputCap) { outputExceeded = true; child.kill(); readyReject(Error('caller_output_limit')); }
  });
  child.on('error', () => readyReject(Error('caller_start_failed')));
  child.on('close', code => { exitCode = code; if (!settled) readyReject(Error('caller_start_failed')); closedResolve(code); });
  child.stdin.on('error', () => {});
  child.stdin.write(JSON.stringify({mode: options.mode, config: options.config, sha256: options.sha256, evidence}) + '\n');
  const resource = {
    child, closed, outputLimitExceeded: () => outputExceeded,
    async close() {
      if (child.exitCode === null) { if (!child.killed) child.stdin.end('shutdown\n'); try { await wait(closed, 8000); } catch { child.kill(); await wait(closed, 5000); } }
      fs.writeFileSync(path.join(evidence, 'caller-stdout.jsonl'), Buffer.concat(stdout), {flag: 'wx'});
      fs.writeFileSync(path.join(evidence, 'caller-stderr.txt'), Buffer.concat(stderr), {flag: 'wx'});
      return exitCode;
    },
  };
  try { return {...resource, ...(await wait(ready, 30000)), python_executable_sha256: hash(fs.readFileSync(executable))}; }
  catch (error) { await resource.close(); throw error; }
}

function request(port, target, method = 'GET', headers = {}) {
  return new Promise((resolve, reject) => {
    const call = http.request({hostname: '127.0.0.1', port, path: target, method, headers}, response => {
      const chunks = []; let bytes = 0;
      response.on('data', chunk => { bytes += chunk.length; if (bytes > 8 * 1024 * 1024) { call.destroy(Error('http_response_limit')); return; } chunks.push(chunk); });
      response.on('end', () => resolve({status: response.statusCode, headers: response.headers, bytes: Buffer.concat(chunks)}));
    });
    call.setTimeout(8000, () => call.destroy(Error('http_timeout'))); call.on('error', reject); call.end();
  });
}

const literal = value => value === null ? '미확인 (null)' : typeof value === 'string' ? value : Object.is(value, -0) ? '-0' : JSON.stringify(value);
async function field(locator, key, expected) {
  const found = await locator.locator('dt').evaluateAll((nodes, needle) => nodes.filter(node => node.textContent === needle).map(node => node.nextElementSibling?.textContent), key);
  assert.deepEqual(found, [literal(expected)], 'field_' + key);
}
function emptySummary(summary) {
  return {...structuredClone(summary), documents: [], case_previews: [], counts: {
    candidate_count: null, acquired_unique_pdfs: 0, parsed_unique_pdfs: 0, complete_text_pdfs: 0,
    partial_text_pdfs: 0, no_citable_text_pdfs: 0, exhibit_relations: 0, case_count: 0,
    reviewed_claim_count: 0, gap_or_unreviewed_claim_count: 0, scope_counts: {in_scope: 0, pending: 0, out_of_range: 0, future: 0},
    independent_group_eligible_cases: 0, normative_comparison_completed_cases: null, development_integrated_cases: null, model_evaluated_cases: 0,
  }};
}

async function main(argv = process.argv.slice(2)) {
  const options = parseOptions(argv);
  if (options.mode === 'actual') readPinned(options.config, options.sha256, 65536);
  const evidence = reserveEvidence(ROOT), checks = [], sourceBefore = sourceHashes();
  let caller, browser, context, page, failure, timedOut = false;
  const jsErrors = [], external = [], requests = [], consoleErrors = [];
  const result = {
    schema_version: 1, kind: 'fcc_case_product_route_browser', input_mode: options.mode,
    contract_fixture: options.mode === 'contract', actual021_constructed: false, json_replay_used_as_catalog: false,
    caller_input_pin: options.sha256 || null, python_boot_sha256: hash(Buffer.from(PYTHON_BOOT)),
    source_unchanged: false, source_inputs_unchanged: false, workspace_db_unchanged: false,
    browser_closed: false, server_closed: false, child_closed: false,
    hardware_verified: false, physical_verified: false, model_execution_verified: false,
    normative_compliance_verified: false, population_complete: false, fault_injections: [], checks,
  };
  const overall = setTimeout(() => { timedOut = true; caller?.child.kill(); void browser?.close().catch(() => {}); }, 180000);
  const check = async (name, action) => {
    const started = Date.now();
    try { await wait(action(), 30000); checks.push({name, pass: true, elapsed_ms: Date.now() - started}); }
    catch (error) { checks.push({name, pass: false, elapsed_ms: Date.now() - started}); throw error; }
  };
  try {
    caller = await startCaller(options, evidence);
    const startup = JSON.parse(fs.readFileSync(path.join(evidence, 'caller-startup.json'), 'utf8'));
    result.actual021_constructed = startup.actual_class_constructed;
    result.runtime = {python_executable_sha256: caller.python_executable_sha256, pypdf_version: startup.pypdf_version,
      pypdf_module_sha256: startup.pypdf_module_sha256, catalog_source_sha256: startup.source_module_sha256,
      server_source_sha256: startup.ui_server_sha256};
    result.caller = {pdf_count: startup.pdf_count, pdf_bytes: startup.pdf_bytes, physical_pages: startup.physical_pages,
      case_count: startup.case_count, construction_seconds: startup.construction_seconds,
      expected_bundle_equal: startup.expected_bundle_equal, expected_bundle_sha256: startup.expected_bundle_sha256,
      constructed_bundle_sha256: startup.constructed_bundle_sha256};
    const model = await import(pathToFileURL(path.join(ROOT, 'frontend/fcc_cases/model.mjs')).href);
    const {FCC_CASE_VIEW_CSS} = await import(pathToFileURL(path.join(ROOT, 'frontend/fcc_cases/view.mjs')).href);
    const bytes = fs.readFileSync(path.join(evidence, 'constructed-bundle.json'));
    const bundle = model.parseFccCaseBundleJson(new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes));
    assert.equal(bundle.summary.synthetic, options.mode === 'contract');
    assert.equal(startup.source_module_sha256, sourceBefore['labflow/fcc_report_cases.py'].sha256);
    assert.equal(startup.ui_server_sha256, sourceBefore['labflow/ui_server.py'].sha256);
    const {configured, unconfigured, empty} = caller.ports;
    const origin = 'http://127.0.0.1:' + configured, summaryURL = origin + '/api/fcc-cases/summary';

    await check('actual021_pre_http_construction_and_expected_values', async () => {
      assert.equal(startup.actual_class_constructed, true);
      assert.equal(startup.catalog_class, 'FccReportCaseCatalog');
      assert.equal(startup.request_time_original_io_guard, true);
      assert.equal(startup.pdf_or_plaintext_copy_written, false);
      if (options.mode === 'actual') {
        assert.equal(startup.expected_bundle_equal, true);
        assert(startup.pdf_count > 0 && startup.pdf_bytes > 0);
      }
    });
    await check('exact_summary_cases_get_head_metadata_and_privacy_headers', async () => {
      const responses = [];
      for (const [target, expected] of [['/api/fcc-cases/summary', bundle.summary],
          ...bundle.cases.map(value => ['/api/fcc-cases/cases/' + encodeURIComponent(value.case.case_id), value])]) {
        const response = await request(configured, target), head = await request(configured, target, 'HEAD');
        assert.equal(response.status, 200); assert.deepEqual(model.parseFccCaseJson(response.bytes.toString('utf8')), expected);
        assert.equal(head.status, 200); assert.equal(head.bytes.length, 0);
        assert.equal(head.headers['content-length'], String(response.bytes.length));
        assert.equal(response.headers['cache-control'], 'no-store');
        assert(response.headers['content-security-policy'].includes("script-src 'self'"));
        assert(!response.headers['content-security-policy'].includes('unsafe-inline'));
        assert.equal(response.headers['access-control-allow-origin'], undefined);
        responses.push({target, status: response.status, headers: response.headers, bytes: response.bytes.toString('utf8')});
      }
      save(evidence, 'http-exact-responses.json', responses);
    });
    await check('unconfigured_api_is503_not_empty_and_head_matches', async () => {
      for (const target of ['/api/fcc-cases/summary', '/api/fcc-cases/cases/SYNTH-MISSING']) {
        const response = await request(unconfigured, target), head = await request(unconfigured, target, 'HEAD');
        assert.equal(response.status, 503); assert.deepEqual(JSON.parse(response.bytes), {error: {code: 'fcc_case_catalog_unconfigured'}});
        assert.equal(head.status, 503); assert.equal(head.headers['content-length'], String(response.bytes.length));
      }
    });
    await check('strict_raw_routes_ids_and_private_assets', async () => {
      for (const target of ['/fcc-cases?', '/fcc-cases#', '//fcc-cases', '//api/fcc-cases/summary',
          '/api/fcc-cases/summary?file=private', '/api/fcc-cases%2Fsummary', '/api/fcc-cases/cases/A%2FB',
          '/api/fcc-cases/cases/A%5CB', '/api/fcc-cases/cases/%ff', '/fcc-cases//app.js',
          '/fcc-cases/index.html', '/fcc-cases/route_browser_check.cjs', '/fcc-cases/browser_check.cjs',
          '/fcc-cases/model.test.mjs', '/fcc-cases/packet.json', '/fcc-cases/source.pdf']) {
        assert.equal((await request(configured, target)).status, 404, target);
      }
      for (const id of ['', '-bad', '%20bad', 'A'.repeat(129)]) assert.equal((await request(configured, '/api/fcc-cases/cases/' + id)).status, 400);
      const missing = await request(configured, '/api/fcc-cases/cases/SYNTH-MISSING');
      assert.equal(missing.status, 404); assert.deepEqual(JSON.parse(missing.bytes), {error: {code: 'fcc_case_not_found'}});
    });
    await check('read_only_origin_policy_and_existing_views', async () => {
      for (const method of ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']) assert.equal((await request(configured, '/api/fcc-cases/summary', method)).status, 405);
      for (const headers of [{Host: 'attacker.invalid'}, {Origin: 'https://attacker.invalid'}, {'Sec-Fetch-Site': 'cross-site'}]) {
        assert.equal((await request(configured, '/api/fcc-cases/summary', 'GET', headers)).status, 403);
      }
      for (const target of ['/', '/control-sources', '/dut-controls', '/api/intakes', '/api/control-sources/summary',
          '/api/dut-controls/summary', '/api/dut-controls/acquisitions/summary']) assert.equal((await request(unconfigured, target)).status, 200, target);
    });
    await check('static024_css_text_matches_without_runtime_style_injection', async () => {
      const response = await request(configured, '/fcc-cases/styles.css');
      assert.equal(response.status, 200);
      assert(response.bytes.toString('utf8').replace(/\r\n/g, '\n').includes(FCC_CASE_VIEW_CSS.replace(/\r\n/g, '\n')));
      result.css_sha256 = hash(response.bytes);
    });

    const {chromium} = require('playwright');
    browser = await chromium.launch({headless: true});
    context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const ports = new Set(Object.values(caller.ports));
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.protocol === 'http:' && url.hostname === '127.0.0.1' && ports.has(Number(url.port))) return route.continue();
      external.push(route.request().url()); return route.abort();
    });
    context.on('page', current => {
      current.on('pageerror', error => jsErrors.push(String(error)));
      current.on('request', call => requests.push({method: call.method(), url: call.url()}));
      current.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
      current.setDefaultTimeout(10000); current.setDefaultNavigationTimeout(30000);
    });
    page = await context.newPage();
    await check('main_menu_link_and_unconfigured_screen_have_no_fake_count_or_reader', async () => {
      await page.goto('http://127.0.0.1:' + unconfigured + '/');
      assert.equal(await page.locator('nav[aria-label="주 메뉴"] a[href="/fcc-cases"]').count(), 1);
      await page.locator('nav[aria-label="주 메뉴"] a[href="/fcc-cases"]').click();
      await page.locator('#fcc-route-state[data-state="unconfigured"]').waitFor();
      assert((await page.locator('#fcc-route-status').textContent()).includes('사례 자료 미구성'));
      assert.equal(await page.locator('.fcc-case-view').count(), 0);
      assert.equal(await page.locator('#fcc-reader').isHidden(), true);
      await page.screenshot({path: path.join(evidence, 'unconfigured-1440.png')});
    });
    if (options.mode === 'contract') {
      await check('genuine_empty_catalog_renders_success_separately', async () => {
        await page.goto('http://127.0.0.1:' + empty + '/fcc-cases/');
        await page.locator('.fcc-index-status[data-state="success"]').waitFor();
        assert.equal(await page.locator('.fcc-case-view').count(), 1);
        assert.equal(await page.locator('.fcc-case-select').count(), 0);
        assert.equal(await page.locator('#fcc-route-state').isHidden(), true);
        await page.screenshot({path: path.join(evidence, 'empty-1440.png')});
      });
      await check('late_initial_unconfigured_reply_cannot_replace_successful_retry_state', async () => {
        let release, firstStarted, count = 0;
        const held = new Promise(resolve => { release = resolve; });
        const started = new Promise(resolve => { firstStarted = resolve; });
        const fresh = await context.newPage();
        await fresh.addInitScript(() => {
          const original = window.fetch;
          window.fetch = (url, options) => {
            const copy = {...options}; delete copy.signal;
            return original(url, copy).then(async response => {
              await response.clone().text();
              window.__routeInitialReplies = (window.__routeInitialReplies || 0) + 1;
              return response;
            });
          };
        });
        await fresh.route(summaryURL, async route => {
          if (++count === 1) {
            firstStarted(); await held;
            await route.fulfill({status: 503, contentType: 'application/json', body: '{"error":{"code":"fcc_case_catalog_unconfigured"}}'});
          } else await route.continue();
        });
        try {
          await fresh.goto(origin + '/fcc-cases'); await wait(started, 8000);
          await fresh.locator('#fcc-route-retry').click();
          await fresh.locator('.fcc-index-status[data-state="success"]').waitFor();
          assert.equal(await fresh.locator('#fcc-route-state').isHidden(), true);
          release(); await fresh.waitForFunction(() => window.__routeInitialReplies === 2);
          await fresh.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          assert.equal(await fresh.locator('#fcc-route-state').isHidden(), true);
          assert.equal(await fresh.locator('.fcc-case-select').count(), bundle.cases.length);
        } finally { release(); await fresh.close(); }
      });
      result.fault_injections.push('late_initial_unconfigured_ignoring_abort');
      await check('initial_invalid_dto_remains_error_until_explicit_retry', async () => {
        let invalid = true;
        await page.route(summaryURL, route => invalid
          ? route.fulfill({status: 200, contentType: 'application/json', body: '{}'}) : route.continue());
        await page.goto(origin + '/fcc-cases');
        await page.locator('#fcc-route-state[data-state="error"]').waitFor();
        assert.equal(await page.locator('.fcc-case-view').count(), 0);
        invalid = false;
        await page.locator('#fcc-route-retry').click();
        await page.locator('.fcc-index-status[data-state="success"]').waitFor();
        await page.unroute(summaryURL);
      });
      result.fault_injections.push('initial_invalid_dto');
    }
    await check('actual_route_initial_summary_once_and_complete_scope_metadata', async () => {
      const before = requests.filter(call => call.url === summaryURL).length;
      await page.goto(origin + '/fcc-cases');
      await page.locator('.fcc-index-status[data-state="success"]').waitFor();
      assert.equal(requests.filter(call => call.url === summaryURL).length - before, 1);
      assert.equal(await page.locator('.fcc-case-select').count(), bundle.cases.length);
      assert.equal(await page.locator('style').count(), 0);
      assert.equal(await page.locator('[style]').count(), 0);
      const metadata = page.locator('.fcc-summary-meta > dl');
      for (const [key, value] of [['corpus_id', bundle.summary.corpus_id], ['발행 시작일', bundle.summary.scope.issue_date_from],
          ['실제 조사 마감 기록', bundle.summary.scope.cutoff_at], ['시간대', 'Asia/Seoul'], ['모집단', 'unconfirmed'],
          ['합성 입력', bundle.summary.synthetic], ['조사 범위', bundle.summary.scope.search_scope_notes],
          ['미확인 범위', bundle.summary.scope.unverified_ranges], ['기간별 사례 상태', bundle.summary.counts.scope_counts],
          ['검증 범위', bundle.summary.validation_scope]]) await field(metadata, key, value);
      await page.locator('.fcc-summary-meta > summary').click();
      await page.screenshot({path: path.join(evidence, 'configured-scope-1440.png')});
    });
    await check('all_actual_case_values_evidence_documents_rights_and_flags_reach_dom', async () => {
      for (const detail of bundle.cases) {
        await page.locator('button.fcc-case-select[data-case-id=' + JSON.stringify(detail.case.case_id) + ']').click();
        await page.waitForFunction(id => document.querySelector('.fcc-case-detail > article')?.dataset.caseId === id, detail.case.case_id);
        const article = page.locator('.fcc-case-detail > article');
        assert.equal(await article.locator('[data-focus="case-heading"]').textContent(), detail.case.preview.report_number ?? detail.case.case_id);
        assert.equal(await page.evaluate(() => document.activeElement?.dataset.focus), 'case-heading');
        for (const claim of detail.case.claims) {
          const card = article.locator('.fcc-claim[data-claim-id=' + JSON.stringify(claim.claim_id) + ']');
          const values = card.locator(':scope > dl');
          await field(values, 'claim_id', claim.claim_id);
          for (const [key, value] of [['원래 값', claim.value], ['원래 단위', claim.unit], ['검토·공백 상태', claim.status], ['근거 종류', claim.basis]]) await field(values, key, value);
          assert.deepEqual(await card.locator('.fcc-quote').allTextContents(), claim.evidence.map(value => value.quote));
          const notes = card.locator('.fcc-evidence');
          assert.equal(await notes.count(), claim.evidence.length);
          for (let i = 0; i < claim.evidence.length; i++) {
            const value = claim.evidence[i], fields = notes.nth(i).locator(':scope > dl');
            for (const [key, expected] of [['원본 문서 ID', value.document_id], ['원본 SHA-256', value.source_sha256], ['파일 페이지', value.file_page],
                ['인쇄 페이지', value.printed_page], ['표 / 행 / 열', [value.table, value.row, value.column]], ['각주', value.footnotes],
                ['retained text SHA-256', value.text_sha256], ['원문 줄 시작/끝', [value.line_start, value.line_end]], ['literal_verified', true]]) await field(fields, key, expected);
          }
        }
        for (const document of detail.documents) {
          const card = article.locator('.fcc-document[data-document-id=' + JSON.stringify(document.document_id) + ']'), values = card.locator(':scope > dl');
          for (const [key, value] of [['원본 SHA-256', document.sha256], ['원본 bytes', document.size_bytes], ['파일 물리 페이지', document.physical_pages],
              ['권리 상태', document.rights.status], ['권리 기록', document.rights.notes], ['공개 재배포 허용', false], ['외부 모델 이용 허용', false],
              ['텍스트 추출 상태', document.extraction.status], ['추출 complete', document.extraction.complete],
              ['전체/처리 페이지', [document.extraction.total_pages, document.extraction.processed_pages]],
              ['parser', document.extraction.parser], ['추출 이슈', document.extraction.issues]]) await field(values, key, value);
          assert.deepEqual(await card.locator('.fcc-page-index li').allTextContents(), document.page_index.map(value =>
            `파일 ${value.file_page} · ${value.status} · citable=${value.citable} · ${value.line_count}줄 · ${value.text_sha256}`));
          for (let i = 0; i < document.exhibits.length; i++) {
            const exhibit = document.exhibits[i], section = card.locator(':scope > section').nth(i);
            for (const [key, value] of [['FCC ID', exhibit.fcc_id], ['신청 ID', exhibit.application_id], ['등재 종류', exhibit.exhibit_type],
                ['출처 종류', exhibit.source_kind], ['열람 시각', exhibit.accessed_at], ['공식 대응 검수 기록', exhibit.official_match_status], ['관련 검색 ID', exhibit.search_ids]]) await field(section, key, value);
          }
        }
      }
      assert.equal(await page.evaluate(() => window.routePwned === true), false);
      await page.screenshot({path: path.join(evidence, 'configured-detail-1440.png')});
    });
    const currentId = await page.locator('.fcc-case-detail > article').getAttribute('data-case-id');
    await check('unknown_case_error_preserves_last_good_detail_and_selection', async () => {
      const form = page.locator('.fcc-case-find');
      await form.locator('input').fill('SYNTH-MISSING'); await form.locator('input').press('Enter');
      await page.locator('.fcc-detail-status[data-state="error"]').waitFor();
      assert.equal(await page.locator('.fcc-case-detail > article').getAttribute('data-case-id'), currentId);
      assert.equal(await page.locator('.fcc-case-select[aria-current="true"]').getAttribute('data-case-id'), currentId);
    });
    await check('summary_failure_retains_last_good_filters_selection_and_detail', async () => {
      const ids = await page.locator('.fcc-case-select').evaluateAll(nodes => nodes.map(node => node.dataset.caseId));
      await page.route(summaryURL, route => route.fulfill({status: 503, contentType: 'application/json', body: '{"error":{"code":"fcc_case_catalog_unavailable"}}'}));
      await page.locator('.fcc-case-refresh').click();
      await page.locator('.fcc-index-status[data-state="error"]').waitFor();
      assert.deepEqual(await page.locator('.fcc-case-select').evaluateAll(nodes => nodes.map(node => node.dataset.caseId)), ids);
      assert.equal(await page.locator('.fcc-case-detail > article').getAttribute('data-case-id'), currentId);
      await page.unroute(summaryURL);
    });
    result.fault_injections.push('summary_unavailable_after_success');
    await check('late_empty_summary_cannot_change_current_filter_internal_state', async () => {
      await page.locator('.fcc-case-refresh').click(); await page.locator('.fcc-index-status[data-state="success"]').waitFor();
      const filterKeys = {product: row => [row.product_family], issuer: row => [row.issuer_class], method: row => row.methods, equipment: row => row.equipment_models};
      let choice;
      for (const [key, values] of Object.entries(filterKeys)) {
        for (const value of [...new Set(bundle.summary.case_previews.flatMap(values))]) {
          const ids = bundle.summary.case_previews.filter(row => values(row).includes(value)).map(row => row.case_id);
          if (ids.length > 0 && ids.length < bundle.cases.length) { choice = {key, value, ids}; break; }
        }
        if (choice) break;
      }
      assert(choice, 'test_dataset_requires_distinguishing_filter');
      const emptyValue = model.validateFccCaseSummary(emptySummary(bundle.summary));
      let release, firstStarted, count = 0;
      const held = new Promise(resolve => { release = resolve; }), started = new Promise(resolve => { firstStarted = resolve; });
      const handler = async route => {
        if (++count === 1) { firstStarted(); await held; await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(emptyValue)}); }
        else await route.continue();
      };
      await page.evaluate(() => {
        window.__routeNativeFetch = window.fetch; window.__routeIgnoreSummaryAbort = true;
        window.fetch = (url, options) => {
          if (String(url).endsWith('/api/fcc-cases/summary') && window.__routeIgnoreSummaryAbort) {
            window.__routeIgnoreSummaryAbort = false;
            const copy = {...options}; delete copy.signal;
            return window.__routeNativeFetch(url, copy).then(async response => { await response.clone().text(); window.__routeOldResponseDone = true; return response; });
          }
          return window.__routeNativeFetch(url, options);
        };
      });
      await page.route(summaryURL, handler);
      try {
        await page.locator('.fcc-case-refresh').click(); await wait(started, 8000);
        await page.locator('.fcc-case-refresh').click(); await page.locator('.fcc-index-status[data-state="success"]').waitFor();
        await page.locator('[data-filter=' + JSON.stringify(choice.key) + ']').selectOption(JSON.stringify(choice.value));
        const before = await page.locator('.fcc-case-select').evaluateAll(nodes => nodes.map(node => node.dataset.caseId));
        assert.deepEqual(before, choice.ids);
        release(); await page.waitForFunction(() => window.__routeOldResponseDone === true);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const other = choice.key === 'product' ? 'method' : 'product';
        await page.locator('[data-filter=' + JSON.stringify(other) + ']').selectOption('');
        const after = await page.locator('.fcc-case-select').evaluateAll(nodes => nodes.map(node => node.dataset.caseId));
        assert.deepEqual(after, before);
        assert.equal(await page.locator('[data-filter=' + JSON.stringify(choice.key) + ']').inputValue(), JSON.stringify(choice.value));
        save(evidence, 'late-empty-filter.json', {filter: choice.key, before, after, old_response_delivered: true});
      } finally {
        release(); await page.unroute(summaryURL, handler);
        await page.evaluate(() => { window.fetch = window.__routeNativeFetch; });
      }
    });
    result.fault_injections.push('late_empty_summary_ignoring_abort');
    await check('390px_keyboard_detail_and_page_evidence_focus_without_overflow', async () => {
      await page.setViewportSize({width: 390, height: 844});
      for (const key of ['product', 'issuer', 'method', 'equipment']) await page.locator('[data-filter=' + JSON.stringify(key) + ']').selectOption('');
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
      await page.screenshot({path: path.join(evidence, 'configured-390.png')});
      const first = page.locator('.fcc-case-select').first(); await first.focus(); await first.press('Enter');
      await page.waitForFunction(() => document.activeElement?.dataset.focus === 'case-heading');
      const jump = page.locator('.fcc-page-links button').first(); await jump.focus(); await jump.press('Enter');
      assert((await page.evaluate(() => document.activeElement?.textContent)).startsWith('파일 페이지 '));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
      await page.screenshot({path: path.join(evidence, 'evidence-focus-390.png')});
    });
    await check('only_same_origin_get_assets_no_external_or_runtime_js_errors', async () => {
      assert.deepEqual(external, []); assert.deepEqual(jsErrors, []);
      assert(requests.every(call => call.method === 'GET'));
      const uiRequests = requests.map(call => new URL(call.url));
      assert(uiRequests.every(url => url.protocol === 'http:' && url.hostname === '127.0.0.1' && ports.has(Number(url.port))));
      save(evidence, 'browser-requests.json', requests);
    });
  } catch (error) {
    failure = error;
    fs.writeFileSync(path.join(evidence, 'failure-private.txt'), String(error.stack || error), {flag: 'wx'});
    if (page && !page.isClosed()) await page.screenshot({path: path.join(evidence, 'failure.png')}).catch(() => {});
  } finally {
    try { if (browser) await wait(browser.close(), 8000); result.browser_closed = !browser || !browser.isConnected(); }
    catch { result.browser_closed = false; }
    try {
      if (caller) {
        result.child_exit_ok = (await caller.close()) === 0;
        result.child_closed = caller.child.exitCode !== null || caller.child.signalCode !== null;
        result.caller_output_limit_exceeded = caller.outputLimitExceeded();
      }
      else result.child_closed = true;
      const file = path.join(evidence, 'caller-shutdown.json');
      if (fs.existsSync(file)) {
        const closed = JSON.parse(fs.readFileSync(file, 'utf8'));
        result.server_closed = closed.server_closed; result.source_inputs_unchanged = closed.source_inputs_unchanged;
        result.workspace_db_unchanged = closed.workspace_db_unchanged;
        result.request_time_original_open_attempts = closed.request_time_original_open_attempts;
      }
    } catch { result.child_closed = false; }
    try { result.source_unchanged = JSON.stringify(sourceBefore) === JSON.stringify(sourceHashes()); }
    catch { result.source_unchanged = false; }
    clearTimeout(overall);
    result.source_files = Object.keys(sourceBefore).length; result.source_before = sourceBefore;
    result.external_requests = external.length; result.runtime_js_errors = jsErrors.length; result.console_errors = consoleErrors.length;
    result.timed_out = timedOut; result.passed_checks = checks.filter(value => value.pass).length;
    result.pass = !failure && !timedOut && result.source_unchanged && result.source_inputs_unchanged && result.workspace_db_unchanged
      && result.browser_closed && result.server_closed && result.child_closed && result.child_exit_ok
      && !result.caller_output_limit_exceeded && result.request_time_original_open_attempts === 0;
    save(evidence, 'result.json', result);
  }
  const receipt = {pass: result.pass, mode: options.mode, checks: result.passed_checks, evidence: path.relative(ROOT, evidence).replace(/\\/g, '/')};
  console.log(JSON.stringify(receipt));
  if (!result.pass) throw Error('fcc_case_route_check_failed');
  return receipt;
}

module.exports = {parseOptions, readPinned, main};
if (require.main === module) main().catch(() => { console.error('fcc_case_route_check_failed'); process.exitCode = 1; });
