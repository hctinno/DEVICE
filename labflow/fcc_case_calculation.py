"""Memory-only binding of an explicit genuine case claim to existing arithmetic."""
import json
import math
import re

from .fcc_report_cases import FccReportCaseCatalog, FccReportCaseError
from . import fcc_report_calculation as report_checks

_REQUEST_KEYS = {'schema_version', 'case_id', 'calculation_request'}
_COMMAND_KEYS = {'calculator', 'rule', 'method', 'input_claim_ids',
                 'reported_result_claim_id', 'comparison_policy'}
_CASE_KEYS = {'schema_version', 'kind', 'corpus_id', 'execution_mode', 'synthetic',
              'validation_scope', 'verification', 'case', 'documents'}
_RESULT_KEYS = {
    'schema_version', 'kind', 'corpus_id', 'case_id', 'calculator', 'status', 'reason_codes',
    'execution_mode', 'synthetic', 'validation_scope', 'verification', 'context',
    'source_page', 'inputs', 'reported_result', 'calculation', 'unit_conversion',
    'comparison_policy', 'comparison', 'interpretation_scope'}
_VERIFY_KEYS = {'hardware_verified', 'physical_verified', 'model_execution_verified',
                'normative_compliance_verified', 'coverage_complete',
                'source_bytes_reverified', 'issuer_authenticity_verified', 'native_raw_observed'}
_LOCATOR_KEYS = {'document_id', 'source_sha256', 'file_page', 'text_sha256',
                 'line_start', 'line_end', 'table', 'row'}
_ANCHOR_KEYS = ('document_id', 'source_sha256', 'file_page', 'text_sha256')
_ROW_KEYS = {'basis', 'table', 'row', 'line_start', 'line_end'}
_CASE_CODES = frozenset({
    'fcc_case_invalid_packet', 'fcc_case_invalid_sources', 'fcc_case_limit_exceeded',
    'fcc_case_pdf_invalid', 'fcc_case_extraction_unavailable', 'fcc_case_invalid_evidence',
    'fcc_case_invalid_query', 'fcc_case_not_found', 'fcc_case_invalid_intake'})
_CALC_CODES = frozenset({'fcc_calc_invalid_case', 'fcc_calc_invalid_request', 'fcc_calc_limit_exceeded'})
_INVALID_REQUEST = frozenset({'fcc_case_calculation_invalid_request',
                              'fcc_calc_invalid_request', 'fcc_case_invalid_query'})
_REASONS = frozenset({
    'case_context_unconfirmed', 'case_context_conflicting', 'rule_mismatch', 'method_mismatch',
    'claim_missing', 'claim_unreviewed', 'claim_basis_unconfirmed', 'claim_role_mismatch',
    'claim_type_mismatch', 'unit_mismatch', 'evidence_unconfirmed', 'source_page_mismatch',
    'source_row_mismatch', 'row_evidence_unconfirmed', 'context_source_mismatch',
    'corrections_already_applied', 'numeric_representation_unavailable', 'calculation_unavailable'})
_UNKNOWN = {'unknown', 'unconfirmed', 'not_reported', 'n/a', '미확인', '불명', '-', '–', '—'}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z', re.ASCII)


class _Bad(Exception):
    pass


class _Limit(Exception):
    pass


def _need(condition):
    if not condition:
        raise _Bad()


def _keys(value, expected):
    _need(type(value) is dict and value.keys() == expected)


def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _copy(value, byte_limit, depth_limit, node_limit):
    nodes = 0
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > depth_limit or nodes > node_limit:
            raise _Limit()
        kind = type(item)
        if item is None or kind is bool:
            return
        if kind is str:
            if len(item) > 16384:
                raise _Limit()
        elif kind is int:
            if item.bit_length() > 4096:
                raise _Limit()
        elif kind is float:
            _need(math.isfinite(item))
        elif kind in (dict, list):
            if len(item) > node_limit - nodes:
                raise _Limit()
            children = item.items() if kind is dict else enumerate(item)
            for key, child in children:
                if kind is dict:
                    _need(type(key) is str)
                    visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise _Bad()
    visit(value, 0)
    try:
        chunks, size = [], 0
        for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                                      separators=(',', ':')).iterencode(value):
            data = chunk.encode('utf-8', errors='strict')
            size += len(data)
            if size > byte_limit:
                raise _Limit()
            chunks.append(data)
        return json.loads(b''.join(chunks).decode('utf-8'))
    except (UnicodeError, ValueError):
        raise _Bad() from None


def _unsafe_text(value):
    return (any(ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value
            or value.startswith('/') or bool(re.match(r'[A-Za-z]:[/\\]', value))
            or value.casefold().startswith(('file:', 'http:', 'https:')))


def _text(value, maximum=16384):
    return (type(value) is str and bool(value.strip()) and len(value) <= maximum
            and not _unsafe_text(value))


def _request(value):
    request = _copy(value, 32 * 1024, 10, 512)
    _keys(request, _REQUEST_KEYS)
    _need(type(request['schema_version']) is int and request['schema_version'] == 1)
    _need(_identifier(request['case_id']))
    command = _copy(request['calculation_request'], 16 * 1024, 8, 256)
    _keys(command, _COMMAND_KEYS)
    _need(type(command['calculator']) is str and command['calculator'] == 'rf_power')
    _need(all(_text(command[name], 256) for name in ('rule', 'method')))
    _keys(command['input_claim_ids'], {'reading'})
    _need(_identifier(command['input_claim_ids']['reading']))
    _need(command['reported_result_claim_id'] is None and command['comparison_policy'] is None)
    return request


def _rejected(code, request=None):
    if code in _INVALID_REQUEST:
        request = None
    return {'schema_version': 1, 'kind': 'fcc_case_calculation', 'corpus_id': None,
            'case_id': None if request is None else request['case_id'],
            'status': 'rejected', 'request_context': request, 'result': None,
            'error_code': code, 'execution_authorized': False}


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _label(value):
    return None if value is None or value.strip().casefold() in _UNKNOWN else value


def _row_witness(binding, source):
    _keys(binding, _ROW_KEYS)
    for name in ('table', 'row'):
        value = binding[name]
        _need(value is None or _text(value, 128) and _label(value) == value)
    if binding['basis'] == 'explicit_table_row':
        _need(binding['table'] is not None and binding['row'] is not None
              and binding['line_start'] is None and binding['line_end'] is None)
        return binding['table'] == _label(source['table']) and binding['row'] == _label(source['row'])
    _need(binding['basis'] == 'common_line_range')
    low, high = binding['line_start'], binding['line_end']
    _need(type(low) is int and type(high) is int and 1 <= low <= high)
    return (source['line_start'] <= low <= high <= source['line_end']
            and binding['table'] == _label(source['table'])
            and binding['row'] == _label(source['row']))


def _projection(value, detail, request):
    _keys(value, {'role', 'claim_id', 'field', 'value', 'unit', 'sources'})
    identity = request['calculation_request']['input_claim_ids']['reading']
    _need(value['role'] == 'reading' and value['claim_id'] == identity
          and value['field'] == 'result.rf_power_reading' and value['unit'] == 'dBm')
    claim = next((item for item in detail['case']['claims'] if item['claim_id'] == identity), None)
    _need(claim is not None and claim['status'] == 'reviewed' and claim['basis'] == 'report_fact'
          and claim['field'] == value['field'] and claim['unit'] == value['unit']
          and _same(claim['value'], value['value']))
    _need(type(value['value']) in (int, float))
    _need(type(value['sources']) is list and 1 <= len(value['sources']) <= 8)
    expected = [{key: evidence[key] for key in _LOCATOR_KEYS}
                for evidence in claim['evidence'] if evidence['literal_verified'] is True]
    expected.sort(key=lambda source: (source['document_id'], source['file_page'],
                                     source['line_start'], source['line_end'],
                                     source['table'] or '', source['row'] or ''))
    _need(_same(value['sources'], expected))
    for source in value['sources']:
        _keys(source, _LOCATOR_KEYS)
        _need(any(_same(source, candidate) for candidate in expected))
        _need(all(source[name] is None or _text(source[name], 128) for name in ('table', 'row')))


def _result(value, detail, request):
    result = _copy(value, 128 * 1024, 16, 8192)
    _keys(result, _RESULT_KEYS)
    _need(type(result['schema_version']) is int and result['schema_version'] == 1)
    _need(result['kind'] == 'fcc_report_calculation_check'
          and result['corpus_id'] == detail['corpus_id']
          and result['case_id'] == request['case_id'] and result['calculator'] == 'rf_power')
    _need(result['execution_mode'] == 'report_derived'
          and type(result['synthetic']) is bool and result['synthetic'] is detail['synthetic']
          and result['validation_scope'] == 'provided_case_dto_and_claim_source_consistency_only'
          and result['interpretation_scope'] == 'reviewer_structured_values_not_literal_semantic_certification')
    _keys(result['verification'], _VERIFY_KEYS)
    _need(all(flag is False for flag in result['verification'].values()))
    _need(result['status'] in ('calculated', 'insufficient_evidence'))
    _need(type(result['reason_codes']) is list)
    if result['status'] == 'calculated':
        _need(result['reason_codes'] == [])
    else:
        _need(len(result['reason_codes']) == 1 and result['reason_codes'][0] in _REASONS)
    command, preview = request['calculation_request'], detail['case']['preview']
    context = {'rule': command['rule'].strip(), 'method': command['method'].strip(),
               'issuer_class': preview['issuer_class'], 'product_family': preview['product_family']}
    empty = dict.fromkeys(context)
    _keys(result['context'], set(context))
    _need(_same(result['context'], empty) or _same(result['context'], context))
    if result['context'] != empty:
        _need(context['issuer_class'] in ('hct_korea', 'hct_america')
              and _text(context['product_family']))
    _need(type(result['inputs']) is list and len(result['inputs']) <= 1)
    for projection in result['inputs']:
        _projection(projection, detail, request)
    page = result['source_page']
    if page is not None:
        _keys(page, {*_ANCHOR_KEYS, 'row_binding'})
        _need(len(result['inputs']) == 1)
        sources = [source for source in result['inputs'][0]['sources']
                   if all(_same(page[key], source[key]) for key in _ANCHOR_KEYS)]
        _need(bool(sources) and any(_row_witness(page['row_binding'], source) for source in sources))
    _need(all(result[name] is None for name in
              ('reported_result', 'unit_conversion', 'comparison_policy', 'comparison')))
    calculation = result['calculation']
    if result['status'] == 'insufficient_evidence':
        _need(calculation is None)
    else:
        _need(_same(result['context'], context) and page is not None and len(result['inputs']) == 1)
        _keys(calculation, {'value', 'unit', 'native_result'})
        _keys(calculation['native_result'], {'value', 'unit'})
        _need(type(calculation['value']) in (int, float) and calculation['value'] > 0
              and math.isfinite(calculation['value']) and calculation['unit'] == 'W'
              and calculation['native_result']['unit'] == 'W'
              and _same(calculation['value'], calculation['native_result']['value']))
    return result


def calculate_case_claim(catalog, request):
    """Return a detached result; never construct a catalog or execute lab work."""
    try:
        command = _request(request)
    except _Limit:
        return _rejected('fcc_case_calculation_limit_exceeded')
    except Exception:
        return _rejected('fcc_case_calculation_invalid_request')
    if catalog is None:
        return _rejected('fcc_case_catalog_unconfigured', command)
    if type(catalog) is not FccReportCaseCatalog:
        return _rejected('fcc_case_catalog_invalid', command)
    try:
        detail = FccReportCaseCatalog.case(catalog, command['case_id'])
    except Exception as error:
        code = error.code if type(error) is FccReportCaseError else None
        return _rejected(code if type(code) is str and code in _CASE_CODES
                         else 'fcc_case_catalog_unavailable', command)
    try:
        detail = _copy(detail, 8 * 1024 * 1024, 16, 50000)
        _keys(detail, _CASE_KEYS)
        _need(type(detail['schema_version']) is int and detail['schema_version'] == 1
              and detail['kind'] == 'fcc_report_case' and _identifier(detail['corpus_id'])
              and type(detail['synthetic']) is bool and type(detail['case']) is dict
              and detail['case']['case_id'] == command['case_id'])
    except Exception:
        return _rejected('fcc_case_catalog_unavailable', command)
    try:
        result = report_checks.check_report_calculation(
            detail, _copy(command['calculation_request'], 16 * 1024, 8, 256))
    except Exception as error:
        code = error.code if type(error) is report_checks.FccReportCalculationError else None
        return _rejected(code if type(code) is str and code in _CALC_CODES
                         else 'fcc_case_calculation_unavailable', command)
    try:
        result = _result(result, detail, command)
        response = {'schema_version': 1, 'kind': 'fcc_case_calculation',
                    'corpus_id': detail['corpus_id'], 'case_id': command['case_id'],
                    'status': result['status'], 'request_context': command, 'result': result,
                    'error_code': None, 'execution_authorized': False}
        return _copy(response, 160 * 1024, 20, 10000)
    except Exception:
        return _rejected('fcc_case_calculation_unavailable', command)
