"""Loopback-only evidence UI and explicit memory calculation. No lab controls."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import math
from pathlib import Path
import re
import threading
from urllib.parse import parse_qsl, unquote, urlsplit

from .ui_read_model import IntakeReadModel, ReadModelError

ASSETS = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
    '/model.mjs': ('model.mjs', 'text/javascript; charset=utf-8'),
    '/intake_flow_model.mjs': ('intake_flow_model.mjs', 'text/javascript; charset=utf-8'),
    '/virtual_fleet/harness_model.mjs': ('virtual_fleet/harness_model.mjs', 'text/javascript; charset=utf-8'),
    '/control-sources': ('control_sources/index.html', 'text/html; charset=utf-8'),
    '/control-sources/': ('control_sources/index.html', 'text/html; charset=utf-8'),
    '/control-sources/styles.css': ('control_sources/styles.css', 'text/css; charset=utf-8'),
    '/control-sources/app.js': ('control_sources/app.js', 'text/javascript; charset=utf-8'),
    '/control-sources/model.mjs': ('control_sources/model.mjs', 'text/javascript; charset=utf-8'),
    '/dut-controls': ('dut_controls/index.html', 'text/html; charset=utf-8'),
    '/dut-controls/': ('dut_controls/index.html', 'text/html; charset=utf-8'),
    '/dut-controls/styles.css': ('dut_controls/styles.css', 'text/css; charset=utf-8'),
    '/dut-controls/app.js': ('dut_controls/app.js', 'text/javascript; charset=utf-8'),
    '/dut-controls/model.mjs': ('dut_controls/model.mjs', 'text/javascript; charset=utf-8'),
    '/fcc-cases': ('fcc_cases/index.html', 'text/html; charset=utf-8'),
    '/fcc-cases/': ('fcc_cases/index.html', 'text/html; charset=utf-8'),
    '/fcc-cases/styles.css': ('fcc_cases/styles.css', 'text/css; charset=utf-8'),
    '/fcc-cases/app.js': ('fcc_cases/app.js', 'text/javascript; charset=utf-8'),
    '/fcc-cases/model.mjs': ('fcc_cases/model.mjs', 'text/javascript; charset=utf-8'),
    '/fcc-cases/view.mjs': ('fcc_cases/view.mjs', 'text/javascript; charset=utf-8'),
    '/fcc-cases/discovery_model.mjs': ('fcc_cases/discovery_model.mjs', 'text/javascript; charset=utf-8'),
    '/fcc-cases/discovery_view.mjs': ('fcc_cases/discovery_view.mjs', 'text/javascript; charset=utf-8'),
    '/fcc-cases/calculation_model.mjs': ('fcc_cases/calculation_model.mjs', 'text/javascript; charset=utf-8'),
    '/fcc-cases/calculation_view.mjs': ('fcc_cases/calculation_view.mjs', 'text/javascript; charset=utf-8'),
}
FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
_ID = re.compile(r'[A-Za-z0-9_.-]{1,150}', re.ASCII)
_SCOPES = {'included', 'excluded_passive', 'identity_unresolved', 'needs_scope_review'}
_FCC_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z', re.ASCII)
_FCC_CODES = frozenset({'fcc_case_invalid_packet', 'fcc_case_invalid_sources', 'fcc_case_limit_exceeded',
                        'fcc_case_pdf_invalid', 'fcc_case_extraction_unavailable', 'fcc_case_invalid_evidence',
                        'fcc_case_invalid_query', 'fcc_case_not_found', 'fcc_case_invalid_intake'})
_FCC_PRIVATE_PATH = re.compile(
    r'''(?:^|[\s"'(<])(?:[A-Za-z]:[\\/]|\\\\[^\\\s]+\\|file://|\.local[\\/])'''
    r'''|(?:^|[\s"'(<])/(?:Users|home|private|tmp|var|mnt|Volumes)/''', re.IGNORECASE)
_FCC_CALC_PATH = '/api/fcc-cases/calculations'
_FCC_CALC_CODES = _FCC_CODES | frozenset({
    'fcc_calc_invalid_case', 'fcc_calc_invalid_request', 'fcc_calc_limit_exceeded',
    'fcc_case_catalog_unconfigured', 'fcc_case_catalog_invalid', 'fcc_case_calculation_invalid_request',
    'fcc_case_calculation_limit_exceeded', 'fcc_case_catalog_unavailable', 'fcc_case_calculation_unavailable'})
_FCC_CALC_RESULT_KEYS = frozenset('schema_version kind corpus_id case_id calculator status reason_codes '
    'execution_mode synthetic validation_scope verification context source_page inputs reported_result '
    'calculation unit_conversion comparison_policy comparison interpretation_scope'.split())
_FCC_CALC_REASONS = frozenset('case_context_unconfirmed case_context_conflicting rule_mismatch method_mismatch '
    'claim_missing claim_unreviewed claim_basis_unconfirmed claim_role_mismatch claim_type_mismatch unit_mismatch '
    'evidence_unconfirmed source_page_mismatch source_row_mismatch row_evidence_unconfirmed context_source_mismatch '
    'corrections_already_applied numeric_representation_unavailable calculation_unavailable'.split())


def _fcc_calculation_body(blob):
    """Bound the raw decoder separately from the service's semantic request."""
    text = blob.decode('utf-8', errors='strict')
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if not escaped and char == '"':
                quoted = False
            escaped = not escaped and char == '\\'
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > 32:
                raise OverflowError()
        elif char in ']}':
            depth -= 1

    def pairs(items):
        value = {}
        for key, child in items:
            if key in value:
                raise ValueError()
            value[key] = child
        return value

    def constant(_):
        raise ValueError()

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    nodes = 0

    def visit(item, level=0):
        nonlocal nodes
        nodes += 1
        if level > 32 or nodes > 4096:
            raise OverflowError()
        if type(item) is str:
            item.encode('utf-8', errors='strict')
        elif type(item) is float and not math.isfinite(item):
            raise ValueError()
        elif type(item) is dict:
            for key, child in item.items():
                visit(key, level + 1)
                visit(child, level + 1)
        elif type(item) is list:
            for child in item:
                visit(child, level + 1)
    visit(value)
    return value


def _fcc_calculation_response(value, request):
    """Pure transport validation; never reread a case or execute arithmetic."""
    raw = _fcc_json_bytes(value, cap=160 * 1024, max_depth=20, max_nodes=10000, compact=True)

    def need(condition):
        if not condition:
            raise ValueError('invalid_fcc_case_calculation')

    def keys(item, names):
        need(type(item) is dict and item.keys() == set(names.split()))

    def identifier(item):
        return type(item) is str and _FCC_ID.fullmatch(item) is not None

    def same(left, right):
        if type(left) is not type(right):
            return False
        if type(left) is dict:
            return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
        if type(left) is list:
            return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
        return left == right

    keys(value, 'schema_version kind corpus_id case_id status request_context result error_code execution_authorized')
    need(type(value['schema_version']) is int and value['schema_version'] == 1
         and value['kind'] == 'fcc_case_calculation' and value['execution_authorized'] is False)
    need(value['status'] in {'calculated', 'insufficient_evidence', 'rejected'})
    for name in ('case_id', 'corpus_id'):
        need(value[name] is None or identifier(value[name]))
    context = value['request_context']
    if context is not None:
        _fcc_json_bytes(context, cap=32768, max_depth=10, max_nodes=512, compact=True)
        keys(context, 'schema_version case_id calculation_request')
        need(type(context['schema_version']) is int and context['schema_version'] == 1
             and identifier(context['case_id']) and context['case_id'] == value['case_id'] and same(context, request))
        command = context['calculation_request']
        keys(command, 'calculator rule method input_claim_ids reported_result_claim_id comparison_policy')
        _fcc_json_bytes(command, cap=16384, max_depth=8, max_nodes=256, compact=True)
        need(command['calculator'] == 'rf_power' and command['reported_result_claim_id'] is None
             and command['comparison_policy'] is None)
        for name in ('rule', 'method'):
            need(type(command[name]) is str and 0 < len(command[name]) <= 256 and bool(command[name].strip()))
        keys(command['input_claim_ids'], 'reading')
        need(identifier(command['input_claim_ids']['reading']))
    if value['status'] == 'rejected':
        need(value['result'] is None and type(value['error_code']) is str and value['error_code'] in _FCC_CALC_CODES)
        if value['error_code'] in {'fcc_case_calculation_invalid_request', 'fcc_calc_invalid_request', 'fcc_case_invalid_query'}:
            need(context is None and value['case_id'] is None)
        return raw
    need(context is not None and value['corpus_id'] is not None and value['error_code'] is None)
    result = value['result']
    _fcc_json_bytes(result, cap=128 * 1024, max_depth=16, max_nodes=8192, compact=True)
    need(type(result) is dict and result.keys() == _FCC_CALC_RESULT_KEYS)
    need(type(result['schema_version']) is int and result['schema_version'] == 1
         and result['kind'] == 'fcc_report_calculation_check' and result['calculator'] == 'rf_power'
         and result['corpus_id'] == value['corpus_id'] and result['case_id'] == value['case_id']
         and result['status'] == value['status'] and type(result['synthetic']) is bool
         and result['execution_mode'] == 'report_derived'
         and result['validation_scope'] == 'provided_case_dto_and_claim_source_consistency_only'
         and result['interpretation_scope'] == 'reviewer_structured_values_not_literal_semantic_certification')
    keys(result['verification'], 'hardware_verified physical_verified model_execution_verified normative_compliance_verified '
         'coverage_complete source_bytes_reverified issuer_authenticity_verified native_raw_observed')
    need(all(flag is False for flag in result['verification'].values()))
    need(type(result['reason_codes']) is list)
    if value['status'] == 'calculated':
        need(result['reason_codes'] == [])
    else:
        need(len(result['reason_codes']) == 1 and result['reason_codes'][0] in _FCC_CALC_REASONS)
    keys(result['context'], 'rule method issuer_class product_family')
    if any(item is not None for item in result['context'].values()):
        need(result['context']['rule'] == command['rule'].strip()
             and result['context']['method'] == command['method'].strip()
             and result['context']['issuer_class'] in {'hct_korea', 'hct_america'}
             and type(result['context']['product_family']) is str and bool(result['context']['product_family'].strip()))
    need(type(result['inputs']) is list and len(result['inputs']) <= 1)
    for item in result['inputs']:
        keys(item, 'role claim_id field value unit sources')
        need(item['role'] == 'reading' and item['claim_id'] == command['input_claim_ids']['reading']
             and item['field'] == 'result.rf_power_reading' and item['unit'] == 'dBm'
             and type(item['value']) in (int, float))
        need(type(item['sources']) is list and len(item['sources']) <= 8)
        for source in item['sources']:
            keys(source, 'document_id source_sha256 file_page text_sha256 line_start line_end table row')
            need(identifier(source['document_id']))
            for name in ('source_sha256', 'text_sha256'):
                need(type(source[name]) is str and re.fullmatch('[0-9a-f]{64}', source[name]) is not None)
            for name in ('file_page', 'line_start', 'line_end'):
                need(type(source[name]) is int and source[name] > 0)
            need(source['line_start'] <= source['line_end'])
            for name in ('table', 'row'):
                need(source[name] is None or type(source[name]) is str and len(source[name]) <= 128)
    page = result['source_page']
    if page is not None:
        keys(page, 'document_id source_sha256 file_page text_sha256 row_binding')
        need(len(result['inputs']) == 1 and any(all(same(page[key], source[key]) for key in
             ('document_id', 'source_sha256', 'file_page', 'text_sha256')) for source in result['inputs'][0]['sources']))
        binding = page['row_binding']
        keys(binding, 'basis table row line_start line_end')
        need(binding['basis'] in {'explicit_table_row', 'common_line_range'})
        for name in ('table', 'row'):
            need(binding[name] is None or type(binding[name]) is str and len(binding[name]) <= 128)
        if binding['basis'] == 'explicit_table_row':
            need(binding['table'] is not None and binding['row'] is not None
                 and binding['line_start'] is None and binding['line_end'] is None)
        else:
            need(type(binding['line_start']) is int and type(binding['line_end']) is int
                 and 0 < binding['line_start'] <= binding['line_end'])
    need(all(result[name] is None for name in ('reported_result', 'unit_conversion', 'comparison_policy', 'comparison')))
    calculation = result['calculation']
    if value['status'] == 'insufficient_evidence':
        need(calculation is None)
    else:
        need(page is not None and len(result['inputs']) == 1 and any(item is not None for item in result['context'].values()))
        keys(calculation, 'value unit native_result')
        keys(calculation['native_result'], 'value unit')
        need(type(calculation['value']) in (int, float) and calculation['value'] > 0
             and calculation['unit'] == 'W' and calculation['native_result']['unit'] == 'W'
             and same(calculation['value'], calculation['native_result']['value']))
    return raw


def _fcc_json_bytes(value, *, cap=8 * 1024**2, max_depth=20, max_nodes=200000, compact=False):
    """Check pure JSON before comparisons or headers; lookup has its own budget."""
    nodes = 0

    def visit(item, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            raise ValueError('invalid_fcc_case_response')
        kind = type(item)
        if kind is str:
            item.encode('utf-8', errors='strict')
            if _FCC_PRIVATE_PATH.search(item):
                raise ValueError('invalid_fcc_case_response')
        elif item is None or kind in (bool, int):
            pass
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError('invalid_fcc_case_response')
        elif kind is list:
            for child in item:
                visit(child, depth + 1)
        elif kind is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError('invalid_fcc_case_response')
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ValueError('invalid_fcc_case_response')

    visit(value)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False,
                     **({'separators': (',', ':')} if compact else {})).encode('utf-8')
    if len(raw) > cap:
        raise ValueError('invalid_fcc_case_response')
    return raw


def _fcc_response_bytes(value, method):
    common = {'schema_version', 'kind', 'corpus_id', 'execution_mode', 'synthetic',
              'validation_scope', 'verification'}
    kinds = {'summary': ('fcc_report_case_summary', {'scope', 'searches', 'counts', 'documents', 'case_previews'}),
             'case': ('fcc_report_case', {'case', 'documents'}),
             'search': ('fcc_report_case_matches', {'query', 'status', 'reason_codes', 'intake_binding', 'matches'}),
             'discover': ('fcc_report_case_discovery', {'query', 'status', 'reason_codes', 'items'})}
    compact = method in {'search', 'discover'}
    raw = _fcc_json_bytes(value, compact=compact, max_nodes=2000000 if compact else 200000)
    kind, fields = kinds[method]
    if type(value) is not dict or set(value) != common | fields:
        raise ValueError('invalid_fcc_case_response')
    verification = value['verification']
    if (type(value['schema_version']) is not int or value['schema_version'] != 1 or value['kind'] != kind
            or value['execution_mode'] != 'report_derived'
            or value['validation_scope'] != 'source_bytes_and_retained_page_literals_only'
            or type(value['synthetic']) is not bool
            or type(value['corpus_id']) is not str or not _FCC_ID.fullmatch(value['corpus_id'])
            or type(verification) is not dict or set(verification) != {
                'hardware_verified', 'physical_verified', 'model_execution_verified',
                'normative_compliance_verified', 'coverage_complete'}
            or any(flag is not False for flag in verification.values())):
        raise ValueError('invalid_fcc_case_response')
    return raw


def _fcc_lookup_query(raw):
    blob = raw.encode('latin-1')
    if len(blob) > 16384:
        raise ValueError('fcc_case_invalid_query')
    text = blob.decode('utf-8', errors='strict')
    if re.search(r'%(?![0-9A-Fa-f]{2})', text):
        raise ValueError('fcc_case_invalid_query')
    result = dict.fromkeys(('product_family', 'rule', 'method', 'model'))
    seen = set()
    for key, value in parse_qsl(text, keep_blank_values=True, strict_parsing=True,
                               encoding='utf-8', errors='strict', max_num_fields=4):
        if key not in result or key in seen or len(value) > 256 or value and not value.strip():
            raise ValueError('fcc_case_invalid_query')
        seen.add(key)
        result[key] = value if value else None
    return result


def _catalog_query(raw):
    # BaseHTTPRequestHandler decodes request-target bytes as ISO-8859-1.
    raw_bytes = raw.encode('latin-1')
    if len(raw_bytes) > 4096:
        raise ValueError('catalog_invalid_query')
    raw = raw_bytes.decode('utf-8', errors='strict')
    if re.search(r'%(?![0-9A-Fa-f]{2})', raw):
        raise ValueError('catalog_invalid_query')
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True,
                      encoding='utf-8', errors='strict', max_num_fields=8)
    result = {}
    for key, value in pairs:
        if key in result or key not in {'query', 'scope', 'model_id', 'equipment_id', 'profile_id', 'offset', 'limit'}:
            raise ValueError('catalog_invalid_query')
        if key in {'offset', 'limit'}:
            if not re.fullmatch(r'[0-9]+', value, re.ASCII):
                raise ValueError('catalog_invalid_query')
            value = int(value)
            if (key == 'offset' and not 0 <= value <= 1000000) or (key == 'limit' and not 1 <= value <= 100):
                raise ValueError('catalog_invalid_query')
        elif key == 'query':
            if len(value) > 200:
                raise ValueError('catalog_invalid_query')
        elif key == 'scope':
            if value not in _SCOPES:
                raise ValueError('catalog_invalid_query')
        elif not _ID.fullmatch(value):
            raise ValueError('catalog_invalid_query')
        result[key] = value
    return result


def create_server(workspace, host='127.0.0.1', port=8765, *, fcc_case_catalog=None):
    if host != '127.0.0.1':
        raise ValueError('The UI server only accepts the loopback host 127.0.0.1')
    fcc_summary = fcc_case = fcc_search = fcc_discover = fcc_error_type = fcc_calculate = None
    if fcc_case_catalog is not None:
        invalid = False
        try:
            module = importlib.import_module('.fcc_report_cases', __package__)
            if type(fcc_case_catalog) is not module.FccReportCaseCatalog:
                invalid = True
            else:
                # Capture formal class methods, never arbitrary instance callbacks.
                fcc_summary = module.FccReportCaseCatalog.summary
                fcc_case = module.FccReportCaseCatalog.case
                fcc_search = getattr(module.FccReportCaseCatalog, 'search', None)
                fcc_discover = getattr(module.FccReportCaseCatalog, 'discover', None)
                fcc_error_type = module.FccReportCaseError
        except Exception:
            invalid = True
        if invalid:
            # Raise outside the exception handler so no private context is retained.
            raise ValueError('fcc_case_catalog_invalid')
        try:
            fcc_calculate = importlib.import_module('.fcc_case_calculation', __package__).calculate_case_claim
        except Exception:
            # New optional capability must not prevent existing readers starting.
            fcc_calculate = None
    model = IntakeReadModel(workspace)
    catalog_instance = None
    catalog_lock = threading.Lock()
    dut_instance = None
    dut_lock = threading.Lock()
    delta_instance = None
    delta_lock = threading.Lock()

    def catalog():
        nonlocal catalog_instance
        with catalog_lock:
            if catalog_instance is None:
                module = importlib.import_module('.control_source_catalog', __package__)
                # Publish only a successfully constructed immutable snapshot.
                catalog_instance = module.ControlSourceCatalog()
            return catalog_instance

    def dut_catalog():
        nonlocal dut_instance
        with dut_lock:
            if dut_instance is None:
                module = importlib.import_module('.dut_control_catalog', __package__)
                dut_instance = module.DutControlCatalog()
            return dut_instance

    def delta_catalog():
        nonlocal delta_instance
        with delta_lock:
            if delta_instance is None:
                module = importlib.import_module('.dut_manufacturer_delta', __package__)
                delta_instance = module.DutManufacturerDeltaCatalog()
            return delta_instance

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # No document names or source text in the web-server log.
            pass

        def send_payload(self, status, content, content_type='application/json; charset=utf-8'):
            if not isinstance(content, bytes):
                content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            if getattr(self, '_fcc_post_only', False):
                self.send_header('Allow', 'POST')
            if getattr(self, '_fcc_close', False):
                self.send_header('Connection', 'close')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; img-src 'self'; font-src 'self'; "
                             "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)

        def error(self, status, code):
            self.send_payload(status, {'error': {'code': code}})

        def allowed_request(self):
            server_port = self.server.server_port
            hosts = {f'127.0.0.1:{server_port}', f'localhost:{server_port}'}
            if server_port == 80:
                hosts.update({'127.0.0.1', 'localhost'})
            return (self.headers.get('Host') in hosts
                    and self.headers.get('Origin') in {None, *(f'http://{name}' for name in hosts)}
                    and self.headers.get('Sec-Fetch-Site') != 'cross-site')

        def do_GET(self):
            self._fcc_post_only = False
            if not self.allowed_request():
                return self.error(403, 'local_origin_required')
            try:
                parsed = urlsplit(self.path)
                if re.search(r'%(?![0-9A-Fa-f]{2})', parsed.path):
                    raise ValueError('invalid_path')
                path = unquote(parsed.path, encoding='utf-8', errors='strict')
            except ValueError:
                return self.error(404, 'route_not_found')
            if parsed.fragment or parsed.scheme or parsed.netloc or ('?' in self.path and path not in {
                    '/api/control-sources', '/api/fcc-cases/lookup'}):
                return self.error(404, 'route_not_found')
            fcc_target = (path == '/fcc-cases' or path.startswith('/fcc-cases/')
                          or path == '/api/fcc-cases' or path.startswith('/api/fcc-cases/'))
            raw_target = self.requestline.split()[1]
            if fcc_target and (('?' in raw_target and path != '/api/fcc-cases/lookup') or '#' in raw_target or '//' in parsed.path
                               or raw_target.startswith('//') or '\\' in path
                               or re.search(r'%(?:2f|5c)', parsed.path, re.IGNORECASE)):
                return self.error(404, 'route_not_found')
            if path == _FCC_CALC_PATH:
                if raw_target != _FCC_CALC_PATH:
                    return self.error(404, 'route_not_found')
                self._fcc_post_only = True
                return self.error(405, 'read_only')
            if path == '/api/fcc-cases/lookup':
                try:
                    query = _fcc_lookup_query(parsed.query)
                except (ValueError, UnicodeError):
                    return self.error(400, 'fcc_case_invalid_query')
                return self.read_fcc_lookup(query)
            if path == '/api/fcc-cases/summary':
                return self.read_fcc_cases('summary')
            if path.startswith('/api/fcc-cases/cases/'):
                case_id = path[len('/api/fcc-cases/cases/'):]
                if '/' in case_id:
                    return self.error(404, 'route_not_found')
                if not _FCC_ID.fullmatch(case_id):
                    return self.error(400, 'fcc_case_invalid_query')
                return self.read_fcc_cases('case', case_id)
            dut_target = (path == '/dut-controls' or path.startswith('/dut-controls/')
                          or path == '/api/dut-controls' or path.startswith('/api/dut-controls/'))
            if dut_target and ('//' in parsed.path or '\\' in path
                               or re.search(r'%(?:2f|5c)', parsed.path, re.IGNORECASE)):
                return self.error(404, 'route_not_found')
            if path == '/api/dut-controls/acquisitions/summary':
                return self.read_dut_delta('summary')
            if path == '/api/dut-controls/acquisitions/records':
                return self.read_dut_delta('records')
            if path.startswith('/api/dut-controls/acquisitions/references/'):
                reference_id = path[len('/api/dut-controls/acquisitions/references/'):]
                if '/' in reference_id:
                    return self.error(404, 'route_not_found')
                if not re.fullmatch(r'[a-z][a-z0-9_]{0,95}', reference_id, re.ASCII):
                    return self.error(400, 'dut_delta_invalid_query')
                return self.read_dut_delta('reference', reference_id)
            if path == '/api/dut-controls/summary':
                return self.read_dut_catalog('summary')
            if path == '/api/dut-controls/routes':
                return self.read_dut_catalog('routes')
            if path == '/api/dut-controls/manufacturing-references':
                return self.read_dut_catalog('manufacturing_references')
            if path.startswith('/api/dut-controls/routes/'):
                backend = path[len('/api/dut-controls/routes/'):]
                if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', backend, re.ASCII):
                    return self.error(400, 'dut_catalog_invalid_query')
                return self.read_dut_catalog('route', backend)
            if path.startswith('/api/dut-controls/sources/'):
                source_id = path[len('/api/dut-controls/sources/'):]
                if not re.fullmatch(r'DUT-[AGS][0-9]{2}', source_id, re.ASCII):
                    return self.error(400, 'dut_catalog_invalid_query')
                return self.read_dut_catalog('source', source_id)
            if path == '/api/control-sources':
                try:
                    filters = _catalog_query(parsed.query)
                except (ValueError, UnicodeError):
                    return self.error(400, 'catalog_invalid_query')
                return self.read_catalog('find_items', **filters)
            if path == '/api/control-sources/summary':
                return self.read_catalog('summary')
            if path.startswith('/api/control-sources/'):
                item_id = path[len('/api/control-sources/'):]
                if not _ID.fullmatch(item_id):
                    return self.error(400, 'catalog_invalid_query')
                return self.read_catalog('detail', item_id)
            if path in ASSETS:
                filename, content_type = ASSETS[path]
                try:
                    return self.send_payload(200, (FRONTEND / filename).read_bytes(), content_type)
                except OSError:
                    return self.error(503, 'asset_unavailable')
            if path == '/api/intakes':
                intake_id = None
                fixture_runs = False
            else:
                match = re.fullmatch(r'/api/intakes/([A-Za-z0-9][A-Za-z0-9_.-]{0,149})(/fixture-runs)?', path)
                if match is None:
                    return self.error(404, 'route_not_found')
                intake_id = match[1]
                fixture_runs = bool(match[2])
            try:
                self.send_payload(200, model.fixture_runs(intake_id) if fixture_runs else model.snapshot(intake_id))
            except ReadModelError as exc:
                self.error(404 if exc.code == 'intake_not_found' else 503, exc.code)
            except (OSError, ValueError):
                self.error(503, 'store_unavailable')

        def read_fcc_lookup(self, query):
            if fcc_case_catalog is None:
                return self.error(503, 'fcc_case_catalog_unconfigured')
            try:
                search = fcc_search(fcc_case_catalog, query)
                discovery = fcc_discover(fcc_case_catalog, query)
                _fcc_response_bytes(search, 'search')
                _fcc_response_bytes(discovery, 'discover')
                for key in ['schema_version', 'corpus_id', 'execution_mode', 'synthetic', 'validation_scope',
                            'verification', 'query']:
                    if search[key] != discovery[key]:
                        raise ValueError('invalid_fcc_case_response')
                payload = {'schema_version': 1, 'kind': 'fcc_report_case_lookup',
                           'search': search, 'discovery': discovery}
                raw = _fcc_json_bytes(payload, cap=16 * 1024**2 + 1024, max_depth=22,
                                      max_nodes=2000000, compact=True)
            except Exception as exc:
                code = exc.code if type(exc) is fcc_error_type else None
                if type(code) is not str or code not in _FCC_CODES:
                    code = 'fcc_case_catalog_unavailable'
                return self.error(400 if code == 'fcc_case_invalid_query' else
                                  404 if code == 'fcc_case_not_found' else 503, code)
            return self.send_payload(200, raw)

        def read_fcc_cases(self, method, *args):
            if fcc_case_catalog is None:
                return self.error(503, 'fcc_case_catalog_unconfigured')
            try:
                operation = fcc_summary if method == 'summary' else fcc_case
                payload = operation(fcc_case_catalog, *args)
                raw = _fcc_response_bytes(payload, method)
            except Exception as exc:
                code = exc.code if type(exc) is fcc_error_type else None
                if type(code) is not str or code not in _FCC_CODES:
                    code = 'fcc_case_catalog_unavailable'
                return self.error(400 if code == 'fcc_case_invalid_query' else
                                  404 if code == 'fcc_case_not_found' else 503, code)
            return self.send_payload(200, raw)

        def read_catalog(self, method, *args, **kwargs):
            try:
                payload = getattr(catalog(), method)(*args, **kwargs)
                return self.send_payload(200, payload)
            except Exception as exc:
                try:
                    code = getattr(exc, 'code', None) if isinstance(exc, ValueError) else None
                except Exception:
                    code = None
                if type(code) is not str:
                    code = None
                if code == 'catalog_item_not_found':
                    return self.error(404, code)
                if code == 'catalog_invalid_query':
                    return self.error(400, code)
                return self.error(503, 'catalog_unavailable')

        def read_dut_catalog(self, method, *args):
            try:
                return self.send_payload(200, getattr(dut_catalog(), method)(*args))
            except Exception as exc:
                try:
                    code = getattr(exc, 'code', None) if isinstance(exc, ValueError) else None
                except Exception:
                    code = None
                if type(code) is not str:
                    code = None
                if code == 'dut_catalog_invalid_query':
                    return self.error(400, code)
                if code == 'dut_catalog_item_not_found':
                    return self.error(404, code)
                return self.error(503, 'dut_catalog_unavailable')

        def read_dut_delta(self, method, *args):
            try:
                return self.send_payload(200, getattr(delta_catalog(), method)(*args))
            except Exception as exc:
                try:
                    code = getattr(exc, 'code', None) if isinstance(exc, ValueError) else None
                except Exception:
                    code = None
                if type(code) is not str:
                    code = None
                if code == 'dut_delta_invalid_query':
                    return self.error(400, code)
                if code == 'dut_delta_item_not_found':
                    return self.error(404, code)
                return self.error(503, 'dut_delta_unavailable')

        do_HEAD = do_GET

        def reject_write(self):
            self.error(405, 'read_only')

        def do_POST(self):
            raw_target = self.requestline.split()[1]
            if self.path != _FCC_CALC_PATH or raw_target != _FCC_CALC_PATH:
                return self.reject_write()
            self.close_connection = True
            self._fcc_close = True
            self._fcc_post_only = False
            origin = self.headers.get('Origin')
            if (not self.allowed_request() or len(self.headers.get_all('Host', [])) != 1
                    or len(self.headers.get_all('Origin', [])) > 1
                    or len(self.headers.get_all('Sec-Fetch-Site', [])) > 1
                    or origin is not None and origin != 'http://' + self.headers.get('Host', '')
                    or self.headers.get('Sec-Fetch-Site') not in {None, 'same-origin', 'none'}):
                return self.error(403, 'local_origin_required')
            invalid = 'fcc_case_calculation_invalid_request'
            if self.headers.get_all('Expect'):
                return self.error(417, invalid)
            if self.headers.get_all('Transfer-Encoding'):
                return self.error(400, invalid)
            content_type = self.headers.get_all('Content-Type', [])
            if (len(content_type) != 1 or not re.fullmatch(
                    r'application/json(?:\s*;\s*charset\s*=\s*utf-8)?', content_type[0].strip(), re.IGNORECASE)
                    or self.headers.get_all('Content-Encoding')):
                return self.error(415, invalid)
            lengths = self.headers.get_all('Content-Length', [])
            if not lengths:
                return self.error(411, invalid)
            if len(lengths) != 1 or not re.fullmatch('[0-9]+', lengths[0], re.ASCII):
                return self.error(400, invalid)
            # Avoid arbitrarily large decimal conversion before applying the wire cap.
            literal = lengths[0].lstrip('0') or '0'
            if len(literal) > 5 or int(literal) > 65536:
                return self.error(413, 'fcc_case_calculation_limit_exceeded')
            length = int(literal)
            previous = self.connection.gettimeout()
            try:
                self.connection.settimeout(5)
                blob = self.rfile.read(length)
            except (TimeoutError, OSError):
                return self.error(408, 'fcc_case_calculation_unavailable')
            finally:
                self.connection.settimeout(previous)
            if len(blob) != length:
                return self.error(400, invalid)
            try:
                request = _fcc_calculation_body(blob)
            except OverflowError:
                return self.error(413, 'fcc_case_calculation_limit_exceeded')
            except (ValueError, UnicodeError, RecursionError):
                return self.error(400, invalid)
            if fcc_case_catalog is None:
                return self.error(503, 'fcc_case_catalog_unconfigured')
            if fcc_calculate is None:
                return self.error(503, 'fcc_case_calculation_unavailable')
            try:
                raw = _fcc_calculation_response(fcc_calculate(fcc_case_catalog, request), request)
            except Exception:
                return self.error(503, 'fcc_case_calculation_unavailable')
            return self.send_payload(200, raw)

        do_PUT = do_PATCH = do_DELETE = do_OPTIONS = reject_write

    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, help='Existing labflow state directory')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    server = create_server(args.workspace, port=args.port)
    print(f'DGM AutoLab intake UI: http://127.0.0.1:{server.server_port} (read only)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
