"""Loopback-only evidence UI and explicit memory calculation. No lab controls."""
import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timedelta
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import importlib
import json
import math
from pathlib import Path
import re
import secrets
import socket
import threading
import time
from urllib.parse import parse_qsl, unquote, urlsplit

from .ui_read_model import IntakeReadModel, ReadModelError

ASSETS = {
    '/ai-connections/panel.mjs': ('ai_connections/panel.mjs', 'text/javascript; charset=utf-8'),
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
    '/intake-references/model.mjs': ('intake_references/model.mjs', 'text/javascript; charset=utf-8'),
    '/intake-references/view.mjs': ('intake_references/view.mjs', 'text/javascript; charset=utf-8'),
    '/intake-references/transport.mjs': ('intake_references/transport.mjs', 'text/javascript; charset=utf-8'),
    '/intake-reference-actions/actions.mjs': ('intake_reference_actions/actions.mjs', 'text/javascript; charset=utf-8'),
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


_REFERENCE_ASSETS = frozenset('/intake-references/' + name + '.mjs' for name in ('model', 'view', 'transport')) | {'/intake-reference-actions/actions.mjs'}
_REFERENCE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z', re.ASCII)
_REFERENCE_SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
_REFERENCE_CODES = frozenset('intake_reference_ui_' + suffix for suffix in
    ('unconfigured', 'invalid_request', 'input_limit', 'access_denied', 'session_unavailable', 'unavailable'))
_REFERENCE_BINDINGS = frozenset('current_at_append historical_provided preparation_unverified head_conflict reference_unbound'.split())
_REFERENCE_REASONS = frozenset('analysis_not_completed legacy_analysis no_pdf_context expected_revision_changed '
    'expected_result_changed analysis_not_ready profile_changed delegation_missing intake_deferred '
    'delegation_evidence_missing required_questions_open unread_documents source_provenance_unconfirmed '
    'preparation_not_ready current_capture_unavailable no_reference_head reference_snapshot_stale'.split())
_REFERENCE_PARENT_SUFFIXES = {
    'IntakeReferenceReviewError': ('intake_reference_review_', 'invalid_argument store_invalid access_denied '
        'prepared_invalid review_state_changed parent_invalid input_limit unavailable'),
    'IntakeReferenceLedgerError': ('intake_reference_ledger_', 'invalid_argument store_invalid intake_not_found '
        'input_limit parent_invalid origin_invalid schema_mismatch request_conflict integrity_invalid storage_error'),
    'IntakeReferenceStateError': ('intake_reference_state_', 'invalid_argument store_invalid transaction_required '
        'intake_not_found input_limit source_integrity_invalid projection_inconsistent delegation_invalid storage_error')}
_REFERENCE_BASE_SHUTDOWN = ThreadingHTTPServer.shutdown
_DOCX_ERRORS = {'intake_docx_reference_' + suffix: status for suffix, status in {
    'invalid_argument': 400, 'store_invalid': 503, 'intake_not_found': 404,
    'intake_unavailable': 409, 'revision_changed': 409, 'document_not_found': 404,
    'source_integrity_invalid': 503, 'input_limit': 413, 'storage_error': 503}.items()}
_REFERENCE_ACTION_ERRORS = {'unconfigured': 503, 'invalid_request': 400, 'input_limit': 413,
    'access_denied': 403, 'review_input_unavailable': 503, 'prepared_unavailable': 410,
    'request_conflict': 409, 'unavailable': 503}
_REFERENCE_ACTION_PARENTS = {
    ('.store', 'StoreOpenError'): ('store_open_', 'invalid_argument path_invalid unavailable schema_mismatch '
        'input_changed integrity_invalid closed backend_unavailable mode_unsupported'),
    ('.intake_case_references', 'IntakeCaseReferencesError'): ('intake_case_references_',
        'catalog_invalid snapshot_invalid context_invalid response_invalid producer_invalid source_error limit_exceeded'),
    ('.fcc_case_review', 'FccCaseReviewError'): ('fcc_case_review_',
        'catalog_invalid query_invalid selection_invalid source_invalid source_error limit_exceeded '
        'context_invalid context_mismatch producer_invalid response_invalid reference_invalid')}
_REFERENCE_PREPARE_REASONS = frozenset('analysis_not_ready profile_changed delegation_missing intake_deferred '
    'delegation_evidence_missing required_questions_open unread_documents source_provenance_unconfirmed preparation_not_ready'.split())


class _ReferenceFailure(ValueError):
    def __init__(self, suffix, status=503):
        self.code = 'intake_reference_ui_' + suffix
        self.status = status
        super().__init__(self.code)


def _reference_fail(suffix='unavailable', status=503):
    try:
        raise _ReferenceFailure(suffix, status) from None
    except _ReferenceFailure as error:
        error.__context__ = error.__cause__ = None
        raise


def _reference_need(condition):
    if not condition:
        _reference_fail()


def _reference_keys(value, names):
    _reference_need(type(value) is dict and value.keys() == set(names.split()))


def _docx_binding(value):
    """Detach the existing exact5; does not inspect a Store or source file."""
    _reference_keys(value, 'source_id intake_id revision revision_fingerprint document')
    for key in ('source_id', 'intake_id'): _reference_id(value[key])
    _reference_int(value['revision'], 1, 2**53 - 1)
    _reference_sha(value['revision_fingerprint'])
    document = value['document']; _reference_keys(document, 'path sha256 bytes')
    path = document['path']
    _reference_need(type(path) is str and bool(path) and len(path) <= 1024
        and not path.startswith('/') and '\\' not in path and ':' not in path
        and not any(ord(c) < 32 or ord(c) == 127 for c in path)
        and all(part not in {'', '.', '..'} for part in path.split('/'))
        and path.lower().endswith('.docx'))
    try: _reference_need(len(path.encode('utf-8')) <= 1024)
    except UnicodeError: _reference_fail()
    _reference_sha(document['sha256']); _reference_int(document['bytes'], 0, 16 * 1024**2)
    return {key: value[key] for key in ('source_id', 'intake_id', 'revision', 'revision_fingerprint')} | {
        'document': {key: document[key] for key in ('path', 'sha256', 'bytes')}}


def _docx_json(value):
    """DOCX-only value-node/depth and canonical byte budgets; legacy unchanged."""
    cap = 2097152; nodes = size = 0
    def limit(): _reference_fail('input_limit', 413)
    def add(amount):
        nonlocal size
        size += amount
        if size > cap: limit()
    def string(item):
        if len(item) > cap: limit()
        try: return len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
        except (ValueError, UnicodeError): _reference_fail()
    def walk(item, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 200000 or depth > 64: limit()
        if item is None or type(item) is bool:
            add(len(json.dumps(item))); return item
        if type(item) is int:
            _reference_need(abs(item) <= 2**53 - 1)
            add(len(str(item))); return item
        if type(item) is str:
            add(string(item)); return item
        _reference_need(type(item) in (dict, list))
        if len(item) > 200000: limit()
        add(2 + max(0, len(item) - 1))
        if type(item) is list: return [walk(child, depth + 1) for child in item]
        copy = {}
        for key, child in item.items():
            _reference_need(type(key) is str)
            add(string(key) + 1)
            copy[key] = walk(child, depth + 1)
        return copy
    copy = walk(value)
    raw = json.dumps(copy, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > cap: limit()
    return copy, raw


def _docx_response(value, intake_id, *, selection=None):
    value, raw = _docx_json(value)
    _reference_keys(value, 'schema_version kind artifact_id artifact_bytes synthetic reference')
    def schema(item): _reference_need(type(item) is int and item == 1)
    def text(item, *, nonempty=False): _reference_need(type(item) is str and (not nonempty or bool(item)))
    def array(item): _reference_need(type(item) is list)
    def number(item, minimum=0): _reference_int(item, minimum, 2**53 - 1)
    schema(value['schema_version']); _reference_need(value['kind'] == 'intake_docx_reference_retained')
    _reference_sha(value['artifact_id']); _reference_int(value['artifact_bytes'], 1, 9 * 1024**2)
    _reference_need(type(value['synthetic']) is bool)
    reference = value['reference']; _reference_keys(reference, 'schema_version kind binding result')
    schema(reference['schema_version']); _reference_need(reference['kind'] == 'intake_docx_reference')
    binding = _docx_binding(reference['binding']); _reference_need(binding['intake_id'] == intake_id)
    if selection is not None:
        _reference_need(value['artifact_id'] == selection[0] and binding == selection[1])
    result = reference['result']
    _reference_keys(result, 'schema_version source reader status complete scope limits blocks text_sha256 issues statistics')
    schema(result['schema_version']); source = result['source']; _reference_keys(source, 'filename sha256 size_bytes')
    _reference_need(source == {'filename': binding['document']['path'], 'sha256': binding['document']['sha256'],
                               'size_bytes': binding['document']['bytes']}
                    and type(source['size_bytes']) is int)
    reader = result['reader']; _reference_keys(reader, 'name version')
    text(reader['name']); text(reader['version']); text(result['status'], nonempty=True)
    _reference_need(type(result['complete']) is bool); _reference_sha(result['text_sha256'])
    scope = result['scope']; _reference_keys(scope, 'profile part page_numbers')
    text(scope['profile']); _reference_need(scope['part'] is None or type(scope['part']) is str)
    _reference_need(scope['page_numbers'] == 'unavailable')
    for key in ('limits', 'statistics'): _reference_need(type(result[key]) is dict)
    def locator(item, *, nullable=False):
        if nullable and item is None: return
        _reference_keys(item, 'part path'); text(item['part']); array(item['path'])
        for step in item['path']:
            _reference_keys(step, 'kind element_index'); text(step['kind']); number(step['element_index'], 1)
    structures = 0
    def structure():
        nonlocal structures
        structures += 1
        if structures > 2000: _reference_fail('input_limit', 413)
    def blocks(items):
        array(items)
        for block in items:
            structure(); _reference_need(type(block) is dict)
            kind = block.get('kind')
            if kind == 'paragraph':
                _reference_keys(block, 'kind locator text text_sha256 complete breaks')
                locator(block['locator']); text(block['text']); _reference_sha(block['text_sha256'])
                _reference_need(type(block['complete']) is bool); array(block['breaks'])
                for br in block['breaks']:
                    _reference_keys(br, 'offset kind'); number(br['offset']); text(br['kind'], nonempty=True)
            elif kind == 'unsupported':
                _reference_keys(block, 'kind locator reason'); locator(block['locator']); text(block['reason'], nonempty=True)
            elif kind == 'table':
                _reference_keys(block, 'kind locator grid_columns rows'); locator(block['locator'])
                if block['grid_columns'] is not None: number(block['grid_columns'])
                array(block['rows'])
                for row in block['rows']:
                    structure(); _reference_keys(row, 'locator grid_before grid_after cells')
                    locator(row['locator']); number(row['grid_before']); number(row['grid_after']); array(row['cells'])
                    for cell in row['cells']:
                        structure(); _reference_keys(cell, 'locator grid_start grid_span v_merge merge_origin blocks')
                        locator(cell['locator']); number(cell['grid_start'], 1); number(cell['grid_span'], 1)
                        _reference_need(cell['v_merge'] in ('none', 'restart', 'continue'))
                        locator(cell['merge_origin'], nullable=True); blocks(cell['blocks'])
            else: _reference_fail()
    blocks(result['blocks']); array(result['issues'])
    if len(result['issues']) > 128: _reference_fail('input_limit', 413)
    for issue in result['issues']:
        _reference_keys(issue, 'code locator occurrences')
        text(issue['code'], nonempty=True); locator(issue['locator'], nullable=True); number(issue['occurrences'], 1)
    return raw


def _reference_int(value, minimum=1, maximum=2**63-1):
    _reference_need(type(value) is int and minimum <= value <= maximum)


def _reference_id(value, maximum=150):
    _reference_need(type(value) is str and len(value) <= maximum and _REFERENCE_ID.fullmatch(value) is not None)


def _reference_sha(value, nullable=False):
    _reference_need(nullable and value is None or type(value) is str and _REFERENCE_SHA.fullmatch(value) is not None)


def _reference_time(value):
    _reference_need(type(value) is str and len(value) <= 128)
    try:
        stamp = datetime.fromisoformat(value)
        valid = stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0)
    except (ValueError, TypeError):
        valid = False
    _reference_need(valid)


def _reference_flags(value, names, positive):
    _reference_keys(value, names)
    _reference_need(all(type(flag) is bool and flag is (key in positive) for key, flag in value.items()))


def _reference_plain(value, *, request=False):
    cap, depth_cap, node_cap = (16384, 8, 256) if request else (2097152, 20, 200000)
    nodes = size = 0
    def invalid(limit=False):
        _reference_fail('input_limit' if limit and request else 'invalid_request' if request else 'unavailable',
                        413 if limit and request else 400 if request else 503)
    def walk(item, depth=0):
        nonlocal nodes, size
        nodes += 1
        if nodes > node_cap or depth > depth_cap: invalid(True)
        if item is None or type(item) in (bool, int, str):
            if type(item) is str and len(item) > cap: invalid(True)
            try: size += len(json.dumps(item, ensure_ascii=False, allow_nan=False).encode('utf-8'))
            except (ValueError, UnicodeError): invalid()
            if size > cap: invalid(True)
            return item
        if type(item) not in (dict, list): invalid()
        size += 2 + max(0, len(item) - 1) + (len(item) if type(item) is dict else 0)
        if size > cap or len(item) > node_cap: invalid(True)
        if type(item) is list: return [walk(child, depth + 1) for child in item]
        result = {}
        for key, child in item.items():
            if type(key) is not str: invalid()
            walk(key, depth + 1); result[key] = walk(child, depth + 1)
        return result
    result = walk(value)
    raw = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > cap: invalid(True)
    return result, raw


def _reference_record(value):
    _reference_keys(value, 'record_id seq request_id revision origin_job_id reference_receipt_id binding_status '
                          'expected_snapshot_id append_observation source_modes created_at')
    for key in ('record_id', 'reference_receipt_id', 'expected_snapshot_id'): _reference_sha(value[key])
    for key in ('request_id', 'origin_job_id'): _reference_id(value[key])
    for key in ('seq', 'revision'): _reference_int(value[key])
    _reference_need(value['binding_status'] in _REFERENCE_BINDINGS); _reference_time(value['created_at'])
    a = value['append_observation']
    _reference_keys(a, 'expected_snapshot_id captured_snapshot_id head_before_record_id head_after_record_id '
                       'head_advanced preparation_ready observed_at')
    _reference_sha(a['expected_snapshot_id'])
    for key in ('captured_snapshot_id', 'head_before_record_id', 'head_after_record_id'): _reference_sha(a[key], True)
    _reference_need(type(a['head_advanced']) is bool and type(a['preparation_ready']) is bool)
    _reference_time(a['observed_at'])
    _reference_need(a['expected_snapshot_id'] == value['expected_snapshot_id'] and a['observed_at'] == value['created_at']
                    and a['head_advanced'] is (value['binding_status'] == 'current_at_append'))
    if a['head_advanced']:
        _reference_need(a['head_after_record_id'] == value['record_id'] and a['captured_snapshot_id'] == a['expected_snapshot_id'])
    else: _reference_need(a['head_after_record_id'] == a['head_before_record_id'])
    modes = value['source_modes']; _reference_keys(modes, 'intake_revision_synthetic catalog_synthetic intake_provenance_status')
    _reference_need(type(modes['intake_revision_synthetic']) is bool
                    and (modes['catalog_synthetic'] is None or type(modes['catalog_synthetic']) is bool)
                    and modes['intake_provenance_status'] in {'confirmed', 'unconfirmed', 'not_assessed'})


def _reference_response(value, intake_id, request):
    value, raw = _reference_plain(value)
    common = 'schema_version kind intake_id available '
    history = request['action'] == 'history'
    _reference_keys(value, common + ('records next_before_seq verification' if history else
        'status record reference_summary current_observation reason_codes verification'))
    _reference_need(type(value['schema_version']) is int and value['schema_version'] == 1
                    and value['kind'] == ('intake_reference_history' if history else 'intake_reference_review_current')
                    and value['intake_id'] == intake_id and type(value['available']) is bool)
    if history:
        rows = value['records']
        _reference_need(type(rows) is list and len(rows) <= request['limit'])
        for row in rows: _reference_record(row)
        seqs = [r['seq'] for r in rows]
        _reference_need(seqs == sorted(set(seqs), reverse=True)
                        and len({r['record_id'] for r in rows}) == len(rows)
                        and len({r['request_id'] for r in rows}) == len(rows)
                        and (value['available'] or not rows)
                        and (request['before_seq'] is None or all(seq < request['before_seq'] for seq in seqs)))
        cursor = value['next_before_seq']
        if cursor is not None:
            _reference_int(cursor); _reference_need(len(rows) == request['limit'] and cursor == seqs[-1])
        _reference_flags(value['verification'], 'record_metadata_verified payloads_reverified original_sources_reverified '
                         'database_currentness_verified', {'record_metadata_verified'} if value['available'] else set())
    else:
        status, record, reasons = value['status'], value['record'], value['reason_codes']
        _reference_need(status in {'current', 'stale', 'none', 'unavailable'} and type(reasons) is list
                        and all(type(r) is str and r in _REFERENCE_REASONS for r in reasons)
                        and reasons == sorted(set(reasons)))
        for state, reason in [('none','no_reference_head'), ('stale','reference_snapshot_stale'),
                              ('unavailable','current_capture_unavailable')]:
            _reference_need((status == state) == (reason in reasons))
        o = value['current_observation']; _reference_keys(o, 'snapshot_id head_record_id preparation_ready observed_at')
        _reference_sha(o['snapshot_id'], True); _reference_sha(o['head_record_id'], True)
        _reference_need(type(o['preparation_ready']) is bool); _reference_time(o['observed_at'])
        _reference_flags(value['verification'], 'record_hash_verified database_snapshot_observed '
                         'reference_source_currentness_verified operational_authority_granted model_execution_verified evaluation_executed',
                         {'database_snapshot_observed'} | ({'record_hash_verified'} if record is not None else set()))
        if record is None:
            _reference_need(value['reference_summary'] is None and o['head_record_id'] is None)
        else:
            _reference_record(record)
            _reference_need(value['available'] and record['record_id'] == o['head_record_id']
                            and record['binding_status'] == 'current_at_append')
            r = value['reference_summary']; _reference_keys(r, 'receipt_id status context_id selected_case_ids accepted_reference_count')
            _reference_sha(r['receipt_id']); _reference_sha(r['context_id'], True)
            _reference_need(r['receipt_id'] == record['reference_receipt_id'] and r['status'] in {'bound', 'insufficient_evidence'}
                            and type(r['selected_case_ids']) is list and len(r['selected_case_ids']) <= 16)
            for case in r['selected_case_ids']: _reference_id(case, 128)
            _reference_need(r['selected_case_ids'] == sorted(set(r['selected_case_ids'])))
            _reference_int(r['accepted_reference_count'], 0, 256)
            _reference_need(r['accepted_reference_count'] >= len(r['selected_case_ids'])
                            and (r['accepted_reference_count'] == 0) == (not r['selected_case_ids']))
        _reference_need((status == 'unavailable') == (o['snapshot_id'] is None)
                        and (status not in {'current', 'stale'} or record is not None)
                        and (status != 'none' or record is None))
        if status == 'current': _reference_need(record['expected_snapshot_id'] == o['snapshot_id'])
    return raw


def _reference_body(blob, action='current'):
    try:
        text = blob.decode('utf-8', errors='strict')
        depth = 0; quoted = escaped = False
        for char in text:
            if quoted:
                if not escaped and char == '"': quoted = False
                escaped = not escaped and char == '\\'
            elif char == '"': quoted = True
            elif char in '[{':
                depth += 1
                if depth > 8: _reference_fail('input_limit', 413)
            elif char in ']}': depth -= 1
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out: raise ValueError()
                out[key] = value
            return out
        def constant(_): raise ValueError()
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        value, _ = _reference_plain(value, request=True)
        fields = {'current': 'schema_version action', 'prepare': 'schema_version review_input_id replace_handle_id',
                  'append': 'schema_version handle_id intake_id request_id preparation_id expected_snapshot_id expected_head_record_id'}
        if (type(value) is not dict or value.keys() != set(fields[action].split())
                or type(value['schema_version']) is not int or value['schema_version'] != 1):
            raise ValueError()
        if action == 'current':
            if value['action'] not in ('current', 'docx_retained'): raise ValueError()
        else:
            for key in (('review_input_id', 'replace_handle_id') if action == 'prepare' else
                        ('handle_id', 'preparation_id', 'expected_snapshot_id', 'expected_head_record_id')):
                if value[key] is None and key in {'replace_handle_id', 'expected_head_record_id'}: continue
                if type(value[key]) is not str or _REFERENCE_SHA.fullmatch(value[key]) is None: raise ValueError()
            if action == 'append':
                for key in ('intake_id', 'request_id'):
                    if type(value[key]) is not str or _REFERENCE_ID.fullmatch(value[key]) is None: raise ValueError()
    except (ValueError, UnicodeError, RecursionError) as error:
        if type(error) is _ReferenceFailure: raise
        _reference_fail('invalid_request', 400)
    return value


def _reference_scope(scope):
    if not (type(scope) is str and scope == 'workspace' or type(scope) is tuple and len(scope) <= 100
            and all(type(value) is str and _REFERENCE_ID.fullmatch(value) for value in scope)
            and len(set(scope)) == len(scope)):
        _reference_fail('invalid_request', 400)
    return scope


def _reference_action_response(value, intake_id, request, action):
    """Validate only public046 wire values; private preparation stays in046."""
    value, raw = _reference_plain(value)
    _reference_int(value.get('schema_version'), maximum=1)
    if action == 'prepare':
        _reference_keys(value, 'schema_version kind handle_id append_request_id expires_in_seconds preview')
        _reference_need(value['kind'] == 'intake_reference_preparation_handle')
        _reference_sha(value['handle_id']); _reference_id(value['append_request_id'])
        _reference_int(value['expires_in_seconds'], 1, 900)
        _fcc_json_bytes(value, cap=65536, max_depth=16, max_nodes=10000, compact=True)
        preview = value['preview']
        _fcc_json_bytes(preview, cap=32768, max_depth=12, max_nodes=4096, compact=True)
        _reference_keys(preview, 'schema_version kind intake_id preparation_id observation preparation_ready reason_codes '
                        'review_status selection source_modes verification')
        _reference_int(preview['schema_version'], maximum=1)
        _reference_need(preview['kind'] == 'intake_reference_review_preview' and preview['intake_id'] == intake_id)
        _reference_id(preview['intake_id']); _reference_sha(preview['preparation_id'])
        observation = preview['observation']
        _reference_keys(observation, 'kind snapshot_id head_record_id observed_at')
        _reference_need(observation['kind'] == 'paired_public_reads')
        _reference_sha(observation['snapshot_id']); _reference_sha(observation['head_record_id'], True)
        _reference_time(observation['observed_at'])
        reasons = preview['reason_codes']
        _reference_need(type(reasons) is list and len(reasons) <= 9 and all(type(reason) is str and reason in _REFERENCE_PREPARE_REASONS for reason in reasons))
        _reference_need(reasons == sorted(set(reasons)) and preview['preparation_ready'] is (not reasons))
        _reference_need(preview['review_status'] in {'bound', 'insufficient_evidence'})
        selection = preview['selection']
        _reference_keys(selection, 'context_id corpus_id requested_case_ids status accepted_reference_count receipt_id')
        _reference_sha(selection['context_id'], True); _reference_sha(selection['receipt_id'])
        if selection['corpus_id'] is not None: _reference_id(selection['corpus_id'], 128)
        ids = selection['requested_case_ids']
        _reference_need(type(ids) is list and len(ids) <= 16)
        for ident in ids: _reference_id(ident, 128)
        _reference_need(len(ids) == len(set(ids)) and selection['status'] in {'selected', 'no_candidate', 'unknown'})
        _reference_int(selection['accepted_reference_count'], 0, 256)
        modes = preview['source_modes']
        _reference_keys(modes, 'intake_revision_synthetic catalog_synthetic intake_provenance_status')
        _reference_need(type(modes['intake_revision_synthetic']) is bool and (modes['catalog_synthetic'] is None or type(modes['catalog_synthetic']) is bool)
                        and modes['intake_provenance_status'] in {'confirmed', 'unconfirmed'})
        _reference_flags(preview['verification'], 'reference_receipt_validated retained_snapshot_observed '
            'reference_source_currentness_verified operational_authority_granted model_execution_verified evaluation_executed',
            {'reference_receipt_validated', 'retained_snapshot_observed'})
    else:
        _reference_keys(value, 'schema_version kind request_id record_id seq stored replayed binding_status append_observation verification')
        _reference_need(value['kind'] == 'intake_reference_registration' and value['request_id'] == request['request_id'] and value['stored'] is True)
        _reference_sha(value['record_id']); _reference_int(value['seq'])
        _reference_need(type(value['replayed']) is bool and value['binding_status'] in _REFERENCE_BINDINGS)
        observation = value['append_observation']
        _reference_keys(observation, 'expected_snapshot_id captured_snapshot_id head_before_record_id head_after_record_id '
                        'head_advanced preparation_ready observed_at')
        _reference_sha(observation['expected_snapshot_id'])
        for key in ('captured_snapshot_id', 'head_before_record_id', 'head_after_record_id'): _reference_sha(observation[key], True)
        _reference_time(observation['observed_at'])
        _reference_need(type(observation['preparation_ready']) is bool and observation['expected_snapshot_id'] == request['expected_snapshot_id']
                        and observation['head_advanced'] is (value['binding_status'] == 'current_at_append'))
        if observation['head_advanced']:
            _reference_need(observation['captured_snapshot_id'] == observation['expected_snapshot_id'] and observation['head_after_record_id'] == value['record_id'])
        else: _reference_need(observation['head_after_record_id'] == observation['head_before_record_id'])
        flags = value['verification']
        required = 'record_hash_verified parent_revalidated_at_append origin_revalidated_at_append operational_authority_granted '
        required += 'model_execution_verified evaluation_executed independent_evaluation_approved'
        _reference_need(type(flags) is dict and set(flags) in (set(required.split()), set(required.split()) | {'mutable_state_verified_at_append'}))
        if 'mutable_state_verified_at_append' in flags: _reference_need(type(flags['mutable_state_verified_at_append']) is bool)
        _reference_flags({key: flags[key] for key in required.split()}, required,
                         {'record_hash_verified', 'parent_revalidated_at_append', 'origin_revalidated_at_append'})
    return raw


def _reference_history_query(query):
    values = {'limit': 20, 'before_seq': None}
    try:
        if '%' in query or '+' in query: raise ValueError()
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True)
        if len(pairs) > 2 or len({p[0] for p in pairs}) != len(pairs): raise ValueError()
        for key, literal in pairs:
            if key not in values or not re.fullmatch('[1-9][0-9]{0,18}', literal, re.ASCII): raise ValueError()
            number = int(literal)
            if number > (100 if key == 'limit' else 2**63-1): raise ValueError()
            values[key] = number
    except ValueError: _reference_fail('invalid_request', 400)
    return {'schema_version': 1, 'action': 'history', **values}


class _ReferenceRuntime:
    def __init__(self, workspace, store, scope):
        module = importlib.import_module('.store', __package__)
        if type(store) is not module.Store or type(store.__dict__.get('_existing_binding')) is not module._ExistingBinding:
            _reference_fail('invalid_request', 400)
        binding = store._existing_binding
        try:
            path = module._existing_path(workspace) if type(workspace) is str else workspace
            if type(path) is not type(Path()) or path != binding.root:
                _reference_fail('invalid_request', 400)
        except Exception:
            _reference_fail('invalid_request', 400)
        self.store, self.binding, self.scope = store, binding, _reference_scope(scope)
        self.lock = threading.RLock(); self.changed = threading.Condition(self.lock)
        self.clock = time.monotonic
        self.host_epoch, self.scope_epoch = secrets.token_hex(32), secrets.token_hex(32)
        self.sessions, self.clients, self.worker_refs, self.workers, self.leases = {}, set(), set(), set(), {}
        self.active = 0; self.source_active = False; self.closing = self.closed = False
        self.loop_thread = None; self.loop_failure = False; self.close_lock = threading.Lock()
        self.actions = None; self.actions_closed = False; self.append_scope = ()
        self.docx_selection = self.docx_parent = self.docx_error_type = None
        self.action_methods = {}; self.action_errors = {}; self.action_error_type = None
        self.check_store()
        api = importlib.import_module('.intake_reference_review', __package__)
        self.parent = api.read_reference_review
        _reference_need(callable(self.parent))
        self.parent_errors = {getattr(api, name): frozenset(prefix + suffix for suffix in names.split())
                              for name, (prefix, names) in _REFERENCE_PARENT_SUFFIXES.items()}

    def configure_docx(self, selection):
        try:
            _reference_need(type(selection) is tuple and len(selection) == 2)
            artifact_id, supplied = selection; _reference_sha(artifact_id)
            binding = _docx_binding(supplied)
            _reference_need(self.allowed(binding['intake_id']))
        except Exception:
            _reference_fail('invalid_request', 400)
        try:
            module = importlib.import_module('.intake_docx_reference', __package__)
            parent, error_type = module.read_retained_intake_docx_reference, module.IntakeDocxReferenceError
            _reference_need(callable(parent) and type(error_type) is type and issubclass(error_type, ValueError))
        except Exception:
            _reference_fail()
        self.docx_selection, self.docx_parent, self.docx_error_type = (artifact_id, binding), parent, error_type

    def configure_actions(self, catalog, append_scope, review_inputs):
        self.append_scope = _reference_scope(append_scope)
        if type(review_inputs) is not tuple: _reference_fail('invalid_request', 400)
        if not review_inputs: return
        failure = None
        try:
            api = importlib.import_module('.intake_reference_review_host', __package__)
            self.action_error_type = api.IntakeReferenceReviewHostError
            self.action_errors = dict(self.parent_errors)
            self.action_errors[self.action_error_type] = frozenset('intake_reference_review_host_' + suffix for suffix in _REFERENCE_ACTION_ERRORS)
            for (module_name, name), (prefix, suffixes) in _REFERENCE_ACTION_PARENTS.items():
                module = importlib.import_module(module_name, __package__)
                self.action_errors[getattr(module, name)] = frozenset(prefix + suffix for suffix in suffixes.split())
            actions = api.create_reference_review_actions(self.store, catalog, host_epoch=self.host_epoch,
                scope_epoch=self.scope_epoch, runtime_lock=self.lock, read_scope=self.scope,
                append_scope=self.append_scope, review_inputs=review_inputs)
            _reference_need(type(actions) is api.ReferenceReviewActions)
            self.actions = actions
            self.action_methods = {name: getattr(api.ReferenceReviewActions, name) for name in
                                   ('capabilities', 'prepare', 'append', 'discard_session', 'close')}
        except Exception as error:
            code, status = self.action_failure(error)
            cls = type(error) if type(error) in self.action_errors and code in self.action_errors[type(error)] else _ReferenceFailure
            failure = cls(code, status=status) if cls is self.action_error_type else cls(code) if cls is not _ReferenceFailure else _ReferenceFailure('unavailable')
        if failure is not None:
            try: raise failure from None
            except ValueError as error:
                error.__context__ = error.__cause__ = None
                raise

    def action_failure(self, error):
        code = getattr(error, 'code', None) if type(error) in self.action_errors else None
        if type(code) is not str or code not in self.action_errors[type(error)]:
            return 'intake_reference_ui_unavailable', 503
        if type(error) is self.action_error_type:
            suffix = code.removeprefix('intake_reference_review_host_')
            status = _REFERENCE_ACTION_ERRORS[suffix]
            if suffix == 'unavailable' and type(error.status) is int and error.status == 429: status = 429
            return code, status
        status = 503
        for suffix, mapped in [('invalid_argument',400), ('access_denied',403), ('intake_not_found',404),
                               ('input_limit',413), ('limit_exceeded',413)]:
            if code.endswith('_' + suffix): status = mapped
        if code == 'intake_reference_ledger_request_conflict': status = 409
        return code, status

    def binding_for(self, sid):
        return {'host_epoch': self.host_epoch, 'session_id': sid, 'scope_epoch': self.scope_epoch}

    def discard_binding(self, binding):
        if self.actions is not None:
            self.action_methods['discard_session'](self.actions, binding)

    def action_headers(self, headers, sid, intake_id):
        binding = self.binding_for(sid) if sid is not None else None
        capabilities = (self.action_methods['capabilities'](self.actions, binding, intake_id) if self.actions is not None else
                        {'prepare_allowed': False, 'append_allowed': False, 'review_input_id': None})
        _reference_keys(capabilities, 'prepare_allowed append_allowed review_input_id')
        prepare, append, input_id = (capabilities[key] for key in ('prepare_allowed', 'append_allowed', 'review_input_id'))
        _reference_need(type(prepare) is bool and type(append) is bool and (not append or prepare))
        if prepare:
            _reference_need(binding is not None and any(name == 'X-Intake-Reference-CSRF' for name, _ in headers))
            _reference_sha(input_id)
        else: _reference_need(input_id is None)
        result = headers + [('X-Intake-Reference-Prepare-Allowed', 'true' if prepare else 'false'),
                            ('X-Intake-Reference-Append-Allowed', 'true' if append else 'false')]
        if prepare: result.append(('X-Intake-Reference-Review-Input', input_id))
        return result

    def check_store(self):
        try:
            with self.binding.lock:
                if self.store.__dict__.get('_existing_binding') is not self.binding: _reference_fail()
                type(self.store).__enter__(self.store)
                self.binding.check_identity()
        except BaseException:
            _reference_fail()

    def _binding_open(self):
        # No native I/O or binding-lock wait inside the runtime admission lock.
        try:
            if self.store.__dict__.get('_existing_binding') is not self.binding or self.binding.state != 'open':
                _reference_fail()
            self.binding.check_owner(self.store)
        except BaseException:
            _reference_fail()

    def allowed(self, intake_id):
        return self.scope == 'workspace' or intake_id in self.scope

    def expire(self):
        now = self.clock()
        for sid in [sid for sid, item in self.sessions.items() if now - item['last_seen'] >= 900]:
            self.discard_binding(self.binding_for(sid))
            del self.sessions[sid]
        return now

    def session(self, sid, *, touch=False):
        now = self.expire()
        item = self.sessions.get(sid) if type(sid) is str and _REFERENCE_SHA.fullmatch(sid) else None
        if item is not None and touch: item['last_seen'] = now
        return item

    def cookie(self, handler):
        headers = handler.headers.get_all('Cookie', [])
        if len(headers) > 1: _reference_fail('access_denied', 403)
        found = []
        for piece in (headers[0].split(';') if headers else []):
            key, equal, value = piece.strip().partition('=')
            if key == self.cookie_name:
                if not equal or not _REFERENCE_SHA.fullmatch(value): _reference_fail('access_denied', 403)
                found.append(value)
        if len(found) > 1: _reference_fail('access_denied', 403)
        return found[0] if found else None

    @property
    def cookie_name(self):
        return 'dgm_intake_reference_' + str(self.server.server_port)

    def authenticate(self, handler, intake_id, *, touch=False, append=False):
        if self.closing: _reference_fail()
        sid = self.cookie(handler); item = self.session(sid, touch=touch)
        tokens = handler.headers.get_all('X-Intake-Reference-CSRF', [])
        if (not self.allowed(intake_id) or append and not (self.append_scope == 'workspace' or intake_id in self.append_scope)
                or item is None or len(tokens) != 1
                or not _REFERENCE_SHA.fullmatch(tokens[0]) or not hmac.compare_digest(tokens[0], item['csrf'])):
            _reference_fail('access_denied', 403)
        return sid

    def history_headers(self, handler, intake_id):
        with self.lock:
            if self.closing: _reference_fail()
            sid = self.cookie(handler); item = self.session(sid)
            if sid is not None and item is None:
                self._binding_open()
                return self.action_headers([('X-Intake-Reference-Read-Allowed', 'false')], None, intake_id)
            headers = []
            if handler.command == 'GET':
                if item is None:
                    if len(self.sessions) >= 128: _reference_fail('session_unavailable')
                    sid = secrets.token_hex(32); item = {'csrf': secrets.token_hex(32), 'last_seen': self.clock()}
                    self.sessions[sid] = item
                    headers.append(('Set-Cookie', self.cookie_name + '=' + sid +
                                    '; HttpOnly; SameSite=Strict; Path=/api/intake-references/; Max-Age=900'))
                else: item['last_seen'] = self.clock()
            allowed = item is not None and self.allowed(intake_id)
            headers.append(('X-Intake-Reference-Read-Allowed', 'true' if allowed else 'false'))
            if allowed: headers.append(('X-Intake-Reference-CSRF', item['csrf']))
            if allowed and self.docx_selection is not None and self.docx_selection[1]['intake_id'] == intake_id:
                headers.append(('X-Intake-Reference-Docx-Selected', 'true'))
            return self.action_headers(headers, sid if allowed else None, intake_id)

    def action_binding(self, session_id):
        with self.lock:
            if self.closing or self.session(session_id) is None: return None
            return self.binding_for(session_id)

    @contextmanager
    def parent_call(self, *, source=False):
        with self._parent_lease(source=source):
            self.check_store()
            with self.lock:
                if self.closing: _reference_fail()
                self._binding_open()
            yield None

    @contextmanager
    def _request_call(self, handler, intake_id, *, source=False, action=None):
        def authenticate(*, touch=False):
            if source:
                if action == 'append': return self.authenticate(handler, intake_id, touch=touch, append=True)
                return self.authenticate(handler, intake_id, touch=touch)
            sid = self.cookie(handler)
            if sid is not None and self.session(sid) is None: _reference_fail('access_denied', 403)
            return sid
        with ExitStack() as lease:
            with self.lock:
                sid = authenticate()
                binding = self.binding_for(sid) if action is not None else None
                lease.enter_context(self._parent_lease(source=source))
            # The lease owns native validation too, without any runtime-lock depth.
            self.check_store()
            with self.lock:
                if self.closing: _reference_fail()
                self._binding_open()
                authenticate(touch=source)
            try: yield binding
            finally:
                if binding is not None:
                    with self.lock:
                        if self.closing or self.session(sid) is None:
                            self.discard_binding(binding)

    def check_preparation_session(self, binding):
        with self.lock:
            if self.closing:
                self.discard_binding(binding); _reference_fail()
            self._binding_open()
            if self.session(binding['session_id']) is None:
                self.discard_binding(binding); _reference_fail('access_denied', 403)

    def close_actions(self):
        if self.actions is not None and not self.actions_closed:
            result = self.action_methods['close'](self.actions)
            _reference_need(result is None)
            self.actions_closed = True

    @contextmanager
    def _parent_lease(self, *, source=False):
        if type(source) is not bool: _reference_fail('invalid_request', 400)
        ident = threading.get_ident()
        with self.lock:
            if self.closing: _reference_fail()
            self._binding_open()
            if source and self.source_active: _reference_fail('unavailable', 429)
            self.active += 1; self.source_active |= source
            self.leases[ident] = self.leases.get(ident, 0) + 1
        try: yield None
        finally:
            with self.lock:
                self.active -= 1
                if source: self.source_active = False
                self.leases[ident] -= 1
                if not self.leases[ident]: del self.leases[ident]
                self.changed.notify_all()


class _ReferenceHTTPServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, address, handler, runtime):
        self._reference_runtime = runtime; runtime.server = self
        super().__init__(address, handler)

    def _reference_action_binding(self, session_id):
        return self._reference_runtime.action_binding(session_id)

    def _reference_parent_call(self, *, source=False):
        return self._reference_runtime.parent_call(source=source)

    def get_request(self):
        client, address = super().get_request()
        rt = self._reference_runtime
        with rt.lock: rt.clients.add(client)
        try: client.settimeout(5)
        except BaseException:
            try: client.close()
            except BaseException: pass
            with rt.lock:
                if client.fileno() == -1: rt.clients.discard(client)
            raise
        return client, address

    def process_request(self, request, client_address):
        rt = self._reference_runtime
        with rt.lock:
            rt.clients.add(request)
            closing = rt.closing
        if closing:
            self.shutdown_request(request)
            with rt.lock: rt.clients.discard(request)
        else:
            try: super().process_request(request, client_address)
            except BaseException:
                self.shutdown_request(request)
                with rt.lock: rt.clients.discard(request)

    def process_request_thread(self, request, client_address):
        rt = self._reference_runtime; ident = threading.get_ident()
        with rt.lock:
            rt.workers.add(ident); rt.worker_refs.add(threading.current_thread())
        try:
            try: super().process_request_thread(request, client_address)
            except BaseException:
                try: self.shutdown_request(request)
                except BaseException: pass
        finally:
            with rt.lock:
                rt.workers.discard(ident)
                rt.worker_refs.discard(threading.current_thread())
                if request.fileno() == -1: rt.clients.discard(request)
                rt.changed.notify_all()

    def handle_error(self, request, client_address):
        pass

    def serve_forever(self, poll_interval=.5):
        rt = self._reference_runtime
        with rt.lock:
            if rt.closing or rt.loop_thread is not None: _reference_fail()
            rt.loop_thread = threading.current_thread()
        try:
            try: super().serve_forever(poll_interval=poll_interval)
            except KeyboardInterrupt: raise
            except BaseException:
                with rt.lock: rt.loop_failure = True
        finally:
            with rt.lock:
                rt.loop_thread = None; rt.changed.notify_all()

    def server_close(self):
        rt = self._reference_runtime; ident = threading.get_ident()
        with rt.lock:
            if ident in rt.workers or rt.leases.get(ident) or rt.loop_thread is threading.current_thread():
                _reference_fail()
        while True:
            try: rt.close_lock.acquire(); break
            except KeyboardInterrupt: continue
        failed = False
        def finish(action):
            nonlocal failed
            while True:
                try: action(); return
                except KeyboardInterrupt: continue
                except BaseException: failed = True; return
        try:
            while True:
                try:
                    with rt.lock:
                        if rt.closed: break
                        rt.closing = True; loop = rt.loop_thread
                        for sid in list(rt.sessions):
                            finish(lambda sid=sid: rt.discard_binding(rt.binding_for(sid)))
                    if loop is not None:
                        finish(self.shutdown)
                        if loop.is_alive(): finish(lambda: _REFERENCE_BASE_SHUTDOWN(self))
                    with rt.changed:
                        while rt.active:
                            try: rt.changed.wait(.1)
                            except KeyboardInterrupt: continue
                            except BaseException: failed = True
                        clients = list(rt.clients)
                        threads = getattr(self, '_threads', ())
                        if isinstance(threads, list): rt.worker_refs.update(threads)
                        workers = list(rt.worker_refs)
                        failed |= rt.loop_failure
                    # All admitted parents and their retirement finally have finished.
                    finish(rt.close_actions)
                    # Closing accepted sockets wakes incomplete headers and blocked writes.
                    for client in clients:
                        def disconnect():
                            try: client.shutdown(socket.SHUT_RDWR)
                            except OSError: pass
                        finish(disconnect); finish(client.close)
                    finish(super().server_close)
                    if self.socket.fileno() != -1: finish(self.socket.close)
                    for worker in workers:
                        if worker is not threading.current_thread(): finish(worker.join)
                    if loop is not None and loop is not threading.current_thread(): finish(loop.join)
                    with rt.lock:
                        rt.clients = {client for client in rt.clients if client.fileno() != -1}
                        rt.worker_refs = {worker for worker in rt.worker_refs if worker.is_alive()}
                        rt.sessions.clear()
                        rt.closed = (not rt.clients and not rt.worker_refs and self.socket.fileno() == -1 and rt.loop_thread is None
                                     and (rt.actions is None or rt.actions_closed))
                        failed |= not rt.closed
                    break
                except KeyboardInterrupt:
                    # A signal between cleanup phases must not return live resources.
                    continue
        finally: rt.close_lock.release()
        if failed: _reference_fail()


def _reference_guard(handler, *, source=False):
    port = handler.server.server_port
    hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    if port == 80: hosts |= {'127.0.0.1', 'localhost'}
    host = handler.headers.get_all('Host', [])
    origin = handler.headers.get_all('Origin', [])
    fetch = handler.headers.get_all('Sec-Fetch-Site', [])
    if (handler.client_address[0] != '127.0.0.1' or len(host) != 1 or host[0] not in hosts
            or len(origin) > 1 or origin and origin[0] != 'http://' + host[0]
            or len(fetch) > 1 or fetch and fetch[0] == 'cross-site'
            or source and (origin != ['http://' + host[0]] or fetch != ['same-origin'])):
        _reference_fail('access_denied', 403)


def _reference_dispatch(handler, runtime):
    handler._reference_headers = []; handler._reference_allow = None
    handler._reference_handling = handler._reference_response_started = False
    raw_target = handler.requestline.split()[1]
    try:
        parsed = urlsplit(handler.path)
        path = unquote(parsed.path, encoding='utf-8', errors='strict')
    except (ValueError, UnicodeError): return False
    asset = (path.startswith('/intake-references/') or path == '/intake-references'
             or path.startswith('/intake-reference-actions/') or path == '/intake-reference-actions')
    if not asset and not (path.startswith('/api/intake-references/') or path == '/api/intake-references'):
        return False
    handler._reference_handling = True
    handler.close_connection = True
    code, status, payload, action = None, None, None, None
    docx_request = False
    try:
        if len(raw_target.encode('utf-8')) > 1024: _reference_fail('input_limit', 413)
        if (parsed.scheme or parsed.netloc or parsed.fragment or raw_target != path + ('?' + parsed.query if '?' in raw_target else '')
                or '%' in parsed.path or '\\' in raw_target or '//' in parsed.path):
            handler.error(404, 'route_not_found'); return True
        if asset:
            if raw_target not in _REFERENCE_ASSETS:
                handler.error(404, 'route_not_found'); return True
            handler._reference_allow = 'GET, HEAD'
            if handler.command not in ('GET', 'HEAD'):
                handler.error(405, 'read_only'); return True
            _reference_guard(handler)
            filename, mime = ASSETS[path]
            try: body = (FRONTEND / filename).read_bytes()
            except FileNotFoundError:
                handler.error(404, 'route_not_found'); return True
            except OSError:
                handler.error(503, 'asset_unavailable'); return True
            handler.send_payload(200, body, mime); return True
        match = re.fullmatch(r'/api/intake-references/([^/]+)/(history|current|prepare|append)', path, re.ASCII)
        if match is None:
            handler.error(404, 'route_not_found'); return True
        intake_id, action = match.groups()
        if _REFERENCE_ID.fullmatch(intake_id) is None: _reference_fail('invalid_request', 400)
        handler._reference_allow = 'GET, HEAD' if action == 'history' else 'POST'
        if handler.command not in (('GET', 'HEAD') if action == 'history' else ('POST',)):
            if action in {'prepare', 'append'}: handler.send_payload(405, b'')
            else: handler.error(405, 'read_only')
            return True
        _reference_guard(handler)
        if runtime is None: _reference_fail('unconfigured')
        if action != 'history': _reference_guard(handler, source=True)
        if action == 'history':
            request = _reference_history_query(parsed.query)
            with runtime._request_call(handler, intake_id):
                value = runtime.parent(runtime.store, intake_id, request, allow_retained_reads=False)
                payload = _reference_response(value, intake_id, request)
                handler._reference_headers = runtime.history_headers(handler, intake_id)
        else:
            if '?' in raw_target: _reference_fail('invalid_request', 400)
            with runtime.lock:
                if action == 'append': runtime.authenticate(handler, intake_id, append=True)
                else: runtime.authenticate(handler, intake_id)
            if action in {'prepare', 'append'} and runtime.actions is None: _reference_fail('unconfigured')
            if handler.headers.get_all('Transfer-Encoding'):
                _reference_fail('invalid_request', 400)
            if handler.headers.get_all('Content-Encoding'): _reference_fail('invalid_request', 415)
            if handler.headers.get_all('Expect'): _reference_fail('invalid_request', 417)
            types = handler.headers.get_all('Content-Type', [])
            if len(types) != 1 or re.fullmatch(r'application/json(?:\s*;\s*charset\s*=\s*utf-8)?', types[0].strip(), re.I) is None:
                _reference_fail('invalid_request', 415)
            lengths = handler.headers.get_all('Content-Length', [])
            if not lengths: _reference_fail('invalid_request', 411)
            if len(lengths) != 1 or re.fullmatch('[0-9]+', lengths[0], re.ASCII) is None:
                _reference_fail('invalid_request', 400)
            literal = lengths[0].lstrip('0') or '0'
            if len(literal) > 5 or int(literal) > 16384: _reference_fail('input_limit', 413)
            try: blob = handler.rfile.read(int(literal))
            except (TimeoutError, OSError): _reference_fail('unavailable', 408)
            if len(blob) != int(literal): _reference_fail('invalid_request', 400)
            request = _reference_body(blob) if action == 'current' else _reference_body(blob, action)
            docx_request = action == 'current' and request['action'] == 'docx_retained'
            if action == 'append' and request['intake_id'] != intake_id: _reference_fail('invalid_request', 400)
            if action == 'current' and request['action'] == 'docx_retained' and (
                    runtime.docx_selection is None or runtime.docx_selection[1]['intake_id'] != intake_id):
                _reference_fail('unconfigured')
            with runtime._request_call(handler, intake_id, source=True, action=action if action != 'current' else None) as binding:
                if action == 'current':
                    if request['action'] == 'docx_retained':
                        if runtime.docx_selection is None or runtime.docx_selection[1]['intake_id'] != intake_id:
                            _reference_fail('unconfigured')
                        artifact_id, selected_binding = runtime.docx_selection
                        value = runtime.docx_parent(runtime.store, artifact_id, expected_binding=_docx_binding(selected_binding))
                        payload = _docx_response(value, intake_id, selection=runtime.docx_selection)
                    else:
                        value = runtime.parent(runtime.store, intake_id, request, allow_retained_reads=True)
                        payload = _reference_response(value, intake_id, request)
                else:
                    value = runtime.action_methods[action](runtime.actions, binding, intake_id, request)
                    payload = _reference_action_response(value, intake_id, request, action)
                    if action == 'prepare': runtime.check_preparation_session(binding)
    except BaseException as error:
        if handler._reference_response_started: return True
        code, status = 'intake_reference_ui_unavailable', 503
        if (type(error) is _ReferenceFailure and type(error.code) is str and error.code in _REFERENCE_CODES
                and type(error.status) is int and error.status in {400,403,408,411,413,415,417,429,503}):
            code, status = error.code, error.status
        elif runtime is not None and action in {'prepare', 'append'}:
            code, status = runtime.action_failure(error)
        elif runtime is not None and docx_request and type(error) is runtime.docx_error_type:
            candidate = getattr(error, 'code', None)
            if type(candidate) is str and candidate in _DOCX_ERRORS:
                code, status = candidate, _DOCX_ERRORS[candidate]
        elif runtime is not None and type(error) in runtime.parent_errors:
            candidate = getattr(error, 'code', None)
            if type(candidate) is str and candidate in runtime.parent_errors[type(error)]:
                code = candidate
                for suffix, mapped in [('invalid_argument',400), ('access_denied',403), ('intake_not_found',404), ('input_limit',413)]:
                    if candidate.endswith('_' + suffix): status = mapped
    try:
        if code is not None:
            handler._reference_headers = []
            handler.error(status, code)
        else: handler.send_payload(200, payload)
    except BaseException:
        # Delivery is unknown; a second error frame cannot repair a partial response.
        pass
    return True


def _conducted_preview_json(value, cap, depth_limit=40):
    nodes = 0
    def visit(item,depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 100000 or depth > depth_limit: raise ValueError('preview_json_limit')
        kind = type(item)
        if kind is dict:
            for key,child in item.items():
                if type(key) is not str: raise ValueError('preview_json_type')
                visit(key,depth+1);visit(child,depth+1)
        elif kind is list:
            for child in item: visit(child,depth+1)
        elif kind is str: item.encode('utf-8','strict')
        elif item is None or kind in (bool,int): pass
        elif kind is float and math.isfinite(item): pass
        else: raise ValueError('preview_json_type')
    visit(value)
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>cap:raise ValueError('preview_json_limit')
    return raw


def _conducted_preview_selection(value):
    if value is None:return None
    try:
        if type(value) is not dict or set(value)!=set('intake_id revision source_settings basis method'.split()):raise ValueError()
        if type(value['intake_id']) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}',value['intake_id'],re.ASCII):raise ValueError()
        if type(value['revision']) is not int or value['revision']<1:raise ValueError()
        return _conducted_preview_json(value,65536,32)
    except (ValueError,TypeError,KeyError,UnicodeError,RecursionError,OverflowError):
        raise ValueError('intake_conducted_preview_invalid_input') from None


def _conducted_preview_response(value):
    def keys(item,names):
        if type(item) is not dict or set(item)!=set(names.split()):raise ValueError('preview_contract')
    keys(value,'schema_version kind intake_id revision context_sha256 context_scope selection_status plan_input')
    if (type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='intake_conducted_plan_preview'
            or value['context_scope']!='current_provided_context' or value['selection_status'] not in ('matched','not_provided','other_intake','revision_changed')):raise ValueError('preview_contract')
    report=value['plan_input'];keys(report,'schema_version kind status binding intake plan gaps verification')
    if type(report['schema_version']) is not int or report['schema_version']!=1 or report['kind']!='intake_conducted_twin_plan_input' or report['status'] not in ('ready_for_simulation','blocked'):raise ValueError('preview_contract')
    keys(report['binding'],'intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256')
    for key in ('intake_id','revision','context_sha256'):
        if report['binding'][key] is not None and report['binding'][key]!=value[key]:raise ValueError('preview_binding')
    keys(report['verification'],'evidence current_version source_bytes regulatory measurement_prediction execution_authority')
    verification=report['verification']
    if (verification['execution_authority'] is not False or verification['current_version']!='caller_snapshot_only'
            or verification['source_bytes']!='not_reopened' or verification['regulatory']!='not_assessed'
            or verification['measurement_prediction']!='not_assessed'):raise ValueError('preview_verification')
    keys(report['plan'],'schema_version method_id method_version metric reference_plane source_settings basis_refs numeric_limit_dbm uncertainty_db assessment')
    if report['plan']['numeric_limit_dbm'] is not None or report['plan']['uncertainty_db'] is not None or report['plan']['assessment']!='not_assessed':raise ValueError('preview_assessment')
    if type(report['gaps']) is not list:raise ValueError('preview_gaps')
    for gap in report['gaps']:
        keys(gap,'code field provided blocking')
        if type(gap['blocking']) is not bool:raise ValueError('preview_gaps')
    ready=report['status']=='ready_for_simulation'
    if ready!=(not any(gap['blocking'] for gap in report['gaps'])):raise ValueError('preview_status')
    if verification['evidence']!=('validated_in_memory' if ready else 'not_validated') or ready and value['selection_status']!='matched':raise ValueError('preview_status')
    return _conducted_preview_json(value,262144)


def create_server(workspace, host='127.0.0.1', port=8765, *, fcc_case_catalog=None,
                  intake_reference_store=None, intake_reference_read_scope=(),
                  intake_reference_append_scope=(), intake_reference_review_inputs=(),
                  intake_test_intent_inputs=(), intake_docx_reference_selection=None, ai_connections=None,
                  ai_connection_campaign_readback=None, conducted_plan_preview_inputs=None):
    conducted_selection = _conducted_preview_selection(conducted_plan_preview_inputs)
    ai_runtime = ai_server_wrapper = None
    if ai_connections is not None or ai_connection_campaign_readback is not None:
        ai_module = importlib.import_module('.ai_connection_ui', __package__)
        ai_runtime = ai_module.AIConnectionRuntime(ai_connections, campaign_readback=ai_connection_campaign_readback)
        ai_server_wrapper = ai_module.wrap_ai_server

    readback_only = ai_connections is None and ai_connection_campaign_readback is not None

    def ai_dispatch(handler):
        if readback_only and not handler.path.startswith('/api/ai-connections/') and handler.path not in ASSETS:
            # A supplied-record host must not fall through to workspace/DB reads,
            # including percent-encoded aliases of the ordinary intake routes.
            handler.close_connection = True
            handler.error(503, 'ai_connection_ui_unconfigured')
            return True
        if not handler.path.startswith('/api/ai-connections/'):
            return False
        if ai_runtime is None:
            handler.close_connection = True
            handler.error(503, 'ai_connection_ui_unconfigured')
            return True
        return ai_runtime.dispatch(handler)
    intent_review = None
    if (type(intake_test_intent_inputs) is not tuple or len(intake_test_intent_inputs) > 1
            or intake_test_intent_inputs and (type(intake_test_intent_inputs[0]) is not tuple
                or len(intake_test_intent_inputs[0]) != 3)):
        module = importlib.import_module('.intake_test_intent', __package__)
        raise module.IntakeTestIntentError('test_intent_invalid_input')
    if intake_test_intent_inputs:
        module = importlib.import_module('.intake_test_intent', __package__)
        from .store import canonical as intent_canonical
        review = module.build_intake_test_intent_review(*intake_test_intent_inputs[0])
        binding = review['input_binding']
        intent_binding = (binding['intake_id'], binding['revision'], binding['provided_projection_sha256'])
        intent_review = intent_canonical(review).encode('utf-8')

    def with_intent_review(payload):
        if intent_review is None:
            return payload
        records = payload['intakes'] if 'intakes' in payload else [payload['intake']]
        for record in records:
            if (record['intake_id'] == intent_binding[0] and record['revision'] == intent_binding[1]
                    and record['analysis'] is not None
                    and hashlib.sha256(intent_canonical(record['analysis']).encode('utf-8')).hexdigest() == intent_binding[2]):
                payload['intake_test_intent_reviews'] = [json.loads(intent_review)]
                break
        return payload

    if intake_reference_store is None and (intake_docx_reference_selection is not None or not (
            type(intake_reference_append_scope) is tuple and not intake_reference_append_scope
            and type(intake_reference_review_inputs) is tuple and not intake_reference_review_inputs)):
        _reference_fail('invalid_request', 400)
    if intake_reference_store is not None and (type(host) is not str or host != '127.0.0.1'
            or type(port) is not int or not 0 <= port <= 65535):
        _reference_fail('invalid_request', 400)
    if host != '127.0.0.1':
        raise ValueError('The UI server only accepts the loopback host 127.0.0.1')
    reference, setup_failure = None, None
    if intake_reference_store is not None:
        try:
            reference = _ReferenceRuntime(workspace, intake_reference_store, intake_reference_read_scope)
        except _ReferenceFailure as error:
            setup_failure = (error.code.removeprefix('intake_reference_ui_'), error.status)
        except Exception:
            setup_failure = ('unavailable', 503)
    if setup_failure is not None: _reference_fail(*setup_failure)
    if reference is not None:
        if intake_docx_reference_selection is not None: reference.configure_docx(intake_docx_reference_selection)
        reference.configure_actions(fcc_case_catalog, intake_reference_append_scope, intake_reference_review_inputs)
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
            if getattr(self, '_reference_handling', False): self._reference_response_started = True
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            if getattr(self, '_fcc_post_only', False):
                self.send_header('Allow', 'POST')
            if getattr(self, '_fcc_close', False):
                self.send_header('Connection', 'close')
            if getattr(self, '_reference_allow', None):
                self.send_header('Allow', self._reference_allow)
            for key, value in getattr(self, '_reference_headers', ()):
                self.send_header(key, value)
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

        def send_error(self, code, message=None, explain=None):
            if code == 501 and _reference_dispatch(self, reference): return
            if reference is None:
                return super().send_error(code, message, explain)
            self.close_connection = True
            self.error(413 if code == 431 else 400, 'intake_reference_ui_input_limit' if code == 431
                       else 'intake_reference_ui_invalid_request')

        def handle_expect_100(self):
            if reference is None: return super().handle_expect_100()
            self.close_connection = True
            self.error(417, 'intake_reference_ui_invalid_request')
            return False

        def allowed_request(self):
            server_port = self.server.server_port
            hosts = {f'127.0.0.1:{server_port}', f'localhost:{server_port}'}
            if server_port == 80:
                hosts.update({'127.0.0.1', 'localhost'})
            return (self.headers.get('Host') in hosts
                    and self.headers.get('Origin') in {None, *(f'http://{name}' for name in hosts)}
                    and self.headers.get('Sec-Fetch-Site') != 'cross-site')

        def do_GET(self):
            if ai_dispatch(self): return
            self._fcc_post_only = False
            if _reference_dispatch(self, reference): return
            if not self.allowed_request():
                return self.error(403, 'local_origin_required')
            try:
                parsed = urlsplit(self.path)
                if re.search(r'%(?![0-9A-Fa-f]{2})', parsed.path):
                    raise ValueError('invalid_path')
                path = unquote(parsed.path, encoding='utf-8', errors='strict')
            except ValueError:
                return self.error(404, 'route_not_found')
            preview_match = re.fullmatch(r'/api/intakes/([A-Za-z0-9][A-Za-z0-9_.-]{0,149})/conducted-plan-preview',path)
            if preview_match:
                return self.read_conducted_preview(preview_match[1],parsed,path)
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
                payload = model.fixture_runs(intake_id) if fixture_runs else with_intent_review(model.snapshot(intake_id))
                self.send_payload(200, payload)
            except ReadModelError as exc:
                self.error(404 if exc.code == 'intake_not_found' else 503, exc.code)
            except (OSError, ValueError):
                self.error(503, 'store_unavailable')

        def read_conducted_preview(self,intake_id,parsed,path):
            try:
                return Handler._read_conducted_preview(self,intake_id,parsed,path)
            except (OSError,TimeoutError):
                # A retired client may disconnect during either success or error
                # publication. Never append a second response or retry the read.
                self.close_connection=True

        def _read_conducted_preview(self,intake_id,parsed,path):
            self.close_connection=True
            self.connection.settimeout(5)
            if self.command!='GET':
                self._reference_allow='GET'
                return self.error(405,'intake_conducted_preview_read_only')
            lengths=self.headers.get_all('Content-Length',[])
            framed=(not self.headers.get_all('Transfer-Encoding') and not self.headers.get_all('Content-Encoding')
                    and not self.headers.get_all('Expect') and len(lengths)<=1 and
                    (not lengths or re.fullmatch('0+',lengths[0],re.ASCII)))
            if not framed or parsed.query or parsed.fragment or self.path!=path:
                if len(lengths)==1 and re.fullmatch(r'[0-9]{1,5}',lengths[0],re.ASCII) and int(lengths[0])<=32768 and not self.headers.get_all('Transfer-Encoding'):
                    try:self.rfile.read(int(lengths[0]))
                    except (OSError,TimeoutError):pass
                return self.error(400,'intake_conducted_preview_invalid_request')
            if len(self.headers.get_all('Host',[]))!=1 or len(self.headers.get_all('Origin',[]))>1 or len(self.headers.get_all('Sec-Fetch-Site',[]))>1:
                return self.error(403,'local_origin_required')
            try:
                selection=json.loads(conducted_selection) if conducted_selection is not None else None
                value=model.conducted_plan_preview(intake_id,selection)
                raw=_conducted_preview_response(value)
            except ReadModelError as error:
                return self.error(404 if error.code=='intake_not_found' else 503,error.code)
            except (ValueError,TypeError,KeyError,IndexError,UnicodeError,RecursionError,OverflowError):
                return self.error(503,'intake_conducted_preview_invalid_response')
            except (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
                raise
            except Exception:
                return self.error(503,'intake_conducted_preview_unavailable')
            return self.send_payload(200,raw)

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
            if ai_dispatch(self): return
            if _reference_dispatch(self, reference): return
            self.error(405, 'read_only')

        def do_POST(self):
            if ai_dispatch(self): return
            if _reference_dispatch(self, reference): return
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

    if reference is None:
        server_type = ai_server_wrapper(ThreadingHTTPServer, ai_runtime) if ai_runtime is not None else ThreadingHTTPServer
        return server_type((host, port), Handler)
    try:
        server_type = ai_server_wrapper(_ReferenceHTTPServer, ai_runtime) if ai_runtime is not None else _ReferenceHTTPServer
        server = server_type((host, port), Handler, reference)
    except Exception:
        server = None
    if server is None: _reference_fail()
    return server


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
