"""Compare reviewed report-derived numbers using existing arithmetic only."""
from datetime import date, datetime, timedelta
from fractions import Fraction
import json
import math
import re
from urllib.parse import urlsplit

from labflow import calculations


_CASE_BYTES, _REQUEST_BYTES, _OUTPUT_BYTES = 8 * 1024 * 1024, 16384, 128 * 1024
_ROW_WORK_LIMIT = 65536
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_FIELD = re.compile(r'(?:report|issuer|product|method|setting|equipment|correction|result|normative)(?:\.[a-z0-9_]+){1,3}\Z')
_VERIFICATION = dict.fromkeys(('hardware_verified', 'physical_verified', 'model_execution_verified',
                               'normative_compliance_verified', 'coverage_complete'), False)
_STATUSES = {'reviewed', 'extracted', 'not_reported', 'extraction_failed', 'ambiguous', 'conflicting'}
_BASES = {'report_fact', 'government_rule', 'guidance', 'standard_reference_only',
          'developer_inference', 'synthetic_policy'}
_EVIDENCE = {'document_id', 'source_sha256', 'file_page', 'printed_page', 'table', 'row',
             'column', 'footnotes', 'text_sha256', 'line_start', 'line_end', 'quote', 'literal_verified'}
_PREVIEW = {'case_id', 'report_group_id', 'report_number', 'revision', 'issuer_class', 'issue_date',
            'scope_status', 'fcc_ids', 'product_family', 'manufacturer', 'models', 'rules',
            'methods', 'equipment_models', 'review_status', 'document_ids', 'evaluation_group'}
_ROLES = {
    'rf_power': (('reading', 'result.rf_power_reading', ('dBm',)),),
    'emc_field_strength': (
        ('reading', 'result.emc_reading', ('dBuV', 'dBµV')),
        ('antenna_factor_db_per_m', 'correction.antenna_factor_db_per_m', ('dB/m',)),
        ('cable_loss_db', 'correction.cable_loss_db', ('dB',)),
        ('preamp_gain_db', 'correction.preamp_gain_db', ('dB',)),
        ('instrument_corrections_applied', 'correction.instrument_corrections_applied', (None,))),
}
_UNKNOWN = {'unknown', 'unconfirmed', 'not_reported', 'n/a', '미확인', '불명', '-', '–', '—'}


class FccReportCalculationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class _Fault(Exception):
    def __init__(self, code):
        self.code = code


class _Gap(Exception):
    def __init__(self, reason):
        self.reason = reason


def _need(condition, code='fcc_calc_invalid_case'):
    if not condition:
        raise _Fault(code)


def _tree(value, max_depth, max_nodes, *, code, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    if depth > max_depth or count[0] > max_nodes:
        raise _Fault('fcc_calc_limit_exceeded')
    kind = type(value)
    if value is None or kind is bool:
        return value
    if kind is str:
        if len(value) > 16384:
            raise _Fault('fcc_calc_limit_exceeded')
        return value
    if kind is int:
        if value.bit_length() > 4096:
            raise _Fault('fcc_calc_limit_exceeded')
        return value
    if kind is float:
        _need(math.isfinite(value), code)
        return value
    _need(kind in (dict, list), code)
    if len(value) > max_nodes - count[0]:
        raise _Fault('fcc_calc_limit_exceeded')
    children = value.items() if kind is dict else enumerate(value)
    result = {} if kind is dict else []
    for key, child in children:
        if kind is dict:
            _need(type(key) is str, code)
            _tree(key, max_depth, max_nodes, code=code, depth=depth + 1, count=count)
        copied = _tree(child, max_depth, max_nodes, code=code, depth=depth + 1, count=count)
        if kind is dict:
            result[key] = copied
        else:
            result.append(copied)
    return result


def _copy(value, byte_limit, depth_limit, node_limit, code):
    detached = _tree(value, depth_limit, node_limit, code=code)
    try:
        chunks, size = [], 0
        encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, allow_nan=False,
                                   separators=(',', ':'))
        for text in encoder.iterencode(detached):
            chunk = text.encode('utf-8')
            size += len(chunk)
            if size > byte_limit:
                raise _Fault('fcc_calc_limit_exceeded')
            chunks.append(chunk)
        data = b''.join(chunks)
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError):
        raise _Fault(code) from None
    return json.loads(data)


def _keys(value, keys):
    _need(type(value) is dict and value.keys() == set(keys))


def _text(value, maximum=16384, nullable=False):
    if type(value) is str and len(value) > maximum:
        raise _Fault('fcc_calc_limit_exceeded')
    _need((nullable and value is None) or
          (type(value) is str and bool(value.strip()) and len(value) <= maximum))


def _id(value, nullable=False):
    _need((nullable and value is None) or (type(value) is str and _ID.fullmatch(value)))


def _sha(value, nullable=False):
    _need((nullable and value is None) or (type(value) is str and _SHA.fullmatch(value)))


def _integer(value, minimum=0, maximum=2 ** 63 - 1):
    _need(type(value) is int and minimum <= value <= maximum)


def _array(value, maximum, *, minimum=0, unique=False):
    _need(type(value) is list)
    _need(len(value) >= minimum)
    if len(value) > maximum:
        raise _Fault('fcc_calc_limit_exceeded')
    if unique:
        _need(all(type(v) is str for v in value) and len(set(value)) == len(value))


def _strings(value, maximum=50000, *, ids=False, width=16384):
    _array(value, maximum, unique=True)
    for item in value:
        _id(item) if ids else _text(item, width)


def _enum(value, allowed):
    _need(type(value) is str and value in allowed)


def _iso_date(value):
    _text(value, 10)
    _need(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value))
    try:
        date.fromisoformat(value)
    except ValueError:
        raise _Fault('fcc_calc_invalid_case') from None


def _stamp(value):
    _text(value, 64)
    _need(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?\+09:00', value))
    try:
        _need(datetime.fromisoformat(value).utcoffset() == timedelta(hours=9))
    except ValueError:
        raise _Fault('fcc_calc_invalid_case') from None


def _url(value, *, official=False, nullable=True):
    if nullable and value is None:
        return
    _text(value, 16384)
    _need(not any(ord(c) <= 32 or ord(c) == 127 for c in value))
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
        _need(parts.scheme in ('http', 'https') and host and
              parts.username is None and parts.password is None and (port is None or port > 0))
        if official:
            _need(host == 'fcc.gov' or host.endswith('.fcc.gov'))
    except ValueError:
        raise _Fault('fcc_calc_invalid_case') from None


def _documents(values, case_ids):
    _array(values, 16, minimum=1)
    result, hashes, pages_total, exhibits_total, bytes_total = {}, set(), 0, 0, 0
    for doc in values:
        _keys(doc, ('document_id', 'sha256', 'size_bytes', 'physical_pages',
                    'exhibits', 'rights', 'extraction', 'page_index'))
        _id(doc['document_id'])
        _sha(doc['sha256'])
        _need(doc['document_id'] not in result and doc['sha256'] not in hashes)
        _integer(doc['size_bytes'], 1, 16 * 1024 * 1024)
        _integer(doc['physical_pages'], 1, 100000)
        bytes_total += doc['size_bytes']
        hashes.add(doc['sha256'])
        _array(doc['exhibits'], 64, minimum=1)
        exhibits_total += len(doc['exhibits'])
        exhibit_keys = set()
        for row in doc['exhibits']:
            _keys(row, ('exhibit_id', 'fcc_id', 'application_id', 'exhibit_type', 'url',
                        'source_kind', 'accessed_at', 'official_match_status', 'official_url', 'search_ids'))
            for name, limit in (('exhibit_id', 128), ('fcc_id', 128),
                                ('application_id', 256), ('exhibit_type', 256)):
                _text(row[name], limit, nullable=name != 'exhibit_id')
            _enum(row['source_kind'], {'official', 'mirror', 'existing_user'})
            _enum(row['official_match_status'], {'unverified', 'listing_only', 'pdf_hash_matched', 'blocked'})
            _stamp(row['accessed_at'])
            _url(row['url'], official=row['source_kind'] == 'official',
                 nullable=row['source_kind'] == 'existing_user')
            _url(row['official_url'], official=True,
                 nullable=row['official_match_status'] not in ('listing_only', 'pdf_hash_matched'))
            _strings(row['search_ids'], 32, ids=True)
            key = (row['exhibit_id'], row['url'])
            _need(key not in exhibit_keys)
            exhibit_keys.add(key)
        rights = doc['rights']
        _keys(rights, ('status', 'notes', 'public_redistribution_allowed', 'external_model_use_allowed'))
        _enum(rights['status'], {'private_only', 'permission_recorded', 'unresolved'})
        _text(rights['notes'], 2048, nullable=True)
        _need(rights['public_redistribution_allowed'] is False and rights['external_model_use_allowed'] is False)
        extract = doc['extraction']
        _keys(extract, ('status', 'complete', 'total_pages', 'processed_pages', 'parser', 'issues'))
        _enum(extract['status'], {'ok', 'empty', 'partial', 'image_only', 'no_text', 'limit_exceeded', 'parser_error'})
        _need(type(extract['complete']) is bool and extract['complete'] == (extract['status'] in ('ok', 'empty')))
        _integer(extract['total_pages'], 1, 100000)
        _integer(extract['processed_pages'], 0, 200)
        _need(extract['total_pages'] == doc['physical_pages'] and extract['processed_pages'] <= extract['total_pages'])
        _keys(extract['parser'], ('name', 'version'))
        _text(extract['parser']['name'], 128)
        _text(extract['parser']['version'], 128, nullable=True)
        _array(extract['issues'], 4096)
        for issue in extract['issues']:
            _keys(issue, ('code', 'file_page'))
            _text(issue['code'], 128)
            if issue['file_page'] is not None:
                _integer(issue['file_page'], 1, doc['physical_pages'])
        _array(doc['page_index'], 200)
        _need(len(doc['page_index']) == extract['processed_pages'])
        pages = {}
        for page in doc['page_index']:
            _keys(page, ('file_page', 'status', 'text_sha256', 'line_count', 'citable'))
            _integer(page['file_page'], 1, doc['physical_pages'])
            _need(page['file_page'] not in pages)
            _enum(page['status'], {'ok', 'empty', 'image_only', 'no_text', 'truncated', 'limit_exceeded', 'error'})
            _sha(page['text_sha256'], nullable=True)
            _integer(page['line_count'], 0, 1000000)
            _need(type(page['citable']) is bool)
            pages[page['file_page']] = page
        pages_total += len(pages)
        result[doc['document_id']] = (doc, pages)
    _need(set(result) == set(case_ids))
    if pages_total > 800 or exhibits_total > 256 or bytes_total > 64 * 1024 * 1024:
        raise _Fault('fcc_calc_limit_exceeded')
    return result


def _preview(preview, case):
    _keys(preview, _PREVIEW)
    _need(preview['case_id'] == case['case_id'] and preview['report_group_id'] == case['report_group_id'])
    _strings(preview['document_ids'], 16, ids=True)
    _need(set(preview['document_ids']) == set(case['document_ids']))
    for key in ('report_number', 'revision', 'product_family', 'manufacturer'):
        _text(preview[key], nullable=True)
    if preview['issue_date'] is not None:
        _iso_date(preview['issue_date'])
    _enum(preview['issuer_class'], {'hct_korea', 'hct_america', 'unknown'})
    _enum(preview['scope_status'], {'in_scope', 'pending', 'out_of_range', 'future'})
    _enum(preview['review_status'], {'reviewed', 'partial', 'unreviewed', 'conflicting'})
    for key in ('fcc_ids', 'models', 'rules', 'methods', 'equipment_models'):
        _strings(preview[key])
    evaluation = preview['evaluation_group']
    _keys(evaluation, ('eligible', 'keys', 'missing'))
    _need(type(evaluation['eligible']) is bool)
    _strings(evaluation['keys'])
    _strings(evaluation['missing'], 7)
    _need(set(evaluation['missing']) <= {'product_family', 'fcc_ids', 'report_group_id', 'reuse_group_ids',
                                        'issuer_class', 'scope_status', 'review_status'})


def _validate_case(detail):
    _keys(detail, ('schema_version', 'kind', 'corpus_id', 'execution_mode', 'synthetic',
                   'validation_scope', 'verification', 'case', 'documents'))
    _need(type(detail['schema_version']) is int and detail['schema_version'] == 1
          and detail['kind'] == 'fcc_report_case' and detail['execution_mode'] == 'report_derived'
          and detail['validation_scope'] == 'source_bytes_and_retained_page_literals_only'
          and type(detail['synthetic']) is bool)
    _id(detail['corpus_id'])
    _keys(detail['verification'], _VERIFICATION)
    _need(all(value is False for value in detail['verification'].values()))
    case = detail['case']
    _keys(case, ('case_id', 'report_group_id', 'document_ids', 'claims', 'relations', 'reuse_group_ids', 'preview'))
    _id(case['case_id'])
    _id(case['report_group_id'], nullable=True)
    _strings(case['document_ids'], 16, ids=True)
    _need(bool(case['document_ids']))
    _strings(case['reuse_group_ids'], 32, ids=True)
    _preview(case['preview'], case)
    _array(case['relations'], 32)
    relation_ids = set()
    for relation in case['relations']:
        _keys(relation, ('relation_id', 'kind', 'target_case_id', 'external_target', 'status'))
        _id(relation['relation_id'])
        _need(relation['relation_id'] not in relation_ids)
        relation_ids.add(relation['relation_id'])
        _enum(relation['kind'], {'revision_of', 'part_of', 'appendix_of', 'exhibit_of'})
        _enum(relation['status'], {'resolved', 'unresolved'})
        _id(relation['target_case_id'], nullable=True)
        _text(relation['external_target'], 256, nullable=True)
        _need((relation['status'] == 'resolved' and relation['target_case_id'] not in (None, case['case_id'])
               and relation['external_target'] is None) or
              (relation['status'] == 'unresolved' and relation['target_case_id'] is None
               and relation['external_target'] is not None))
    docs = _documents(detail['documents'], case['document_ids'])
    _array(case['claims'], 64)
    claims = {}
    for claim in case['claims']:
        _keys(claim, ('claim_id', 'field', 'value', 'unit', 'status', 'basis', 'evidence'))
        _id(claim['claim_id'])
        _need(claim['claim_id'] not in claims)
        _text(claim['field'], 128)
        _need(_FIELD.fullmatch(claim['field']))
        _enum(claim['status'], _STATUSES)
        _enum(claim['basis'], _BASES)
        _text(claim['unit'], 64, nullable=True)
        _tree(claim['value'], 6, 50000, code='fcc_calc_invalid_case')
        _array(claim['evidence'], 8)
        if claim['status'] in ('not_reported', 'extraction_failed'):
            _need(claim['value'] is None and not claim['evidence'])
        if claim['status'] in ('reviewed', 'extracted'):
            value = claim['value']
            _need(value is not None and bool(claim['evidence']))
            if type(value) in (dict, list, str):
                _need(bool(value) and (type(value) is not str or bool(value.strip())))
        for ev in claim['evidence']:
            _keys(ev, _EVIDENCE)
            _id(ev['document_id'])
            _need(ev['document_id'] in docs)
            doc, pages = docs[ev['document_id']]
            _sha(ev['source_sha256'])
            _need(ev['source_sha256'] == doc['sha256'])
            _integer(ev['file_page'], 1, doc['physical_pages'])
            _need(ev['file_page'] in pages)
            _sha(ev['text_sha256'])
            _need(ev['text_sha256'] == pages[ev['file_page']]['text_sha256'])
            _integer(ev['line_start'], 1)
            _integer(ev['line_end'], ev['line_start'], pages[ev['file_page']]['line_count'])
            _need(ev['line_end'] - ev['line_start'] < 40)
            _text(ev['quote'], 8192)
            for key in ('printed_page', 'table', 'row', 'column'):
                _text(ev[key], 128, nullable=True)
            _array(ev['footnotes'], 16)
            for note in ev['footnotes']:
                _text(note, 512)
            _need(type(ev['literal_verified']) is bool)
        claims[claim['claim_id']] = claim
    return docs, claims


def _unsafe_text(value):
    return (any(ord(c) < 32 or ord(c) == 127 for c in value)
            or '\\' in value or value.startswith('/') or bool(re.match(r'[A-Za-z]:[/\\]', value))
            or value.casefold().startswith(('file:', 'http:', 'https:')))


def _validate_request(request):
    code = 'fcc_calc_invalid_request'
    _need(type(request) is dict and request.keys() == {
        'calculator', 'rule', 'method', 'input_claim_ids', 'reported_result_claim_id', 'comparison_policy'}, code)
    calculator = request['calculator']
    _need(type(calculator) is str and calculator in _ROLES, code)
    for name in ('rule', 'method'):
        value = request[name]
        _need(type(value) is str and bool(value.strip()) and len(value) <= 256 and not _unsafe_text(value), code)
    inputs = request['input_claim_ids']
    _need(type(inputs) is dict and inputs.keys() == {r[0] for r in _ROLES[calculator]}, code)
    ids = list(inputs.values())
    reported = request['reported_result_claim_id']
    if reported is not None:
        ids.append(reported)
    _need(all(type(i) is str and _ID.fullmatch(i) for i in ids) and len(set(ids)) == len(ids), code)
    policy = request['comparison_policy']
    if reported is None:
        _need(policy is None, code)
    else:
        _need(type(policy) is dict and policy.keys() == {'absolute_tolerance', 'unit'}, code)
        value = policy['absolute_tolerance']
        _need(type(value) in (int, float) and value >= 0
              and (type(value) is int or math.isfinite(value)), code)
        _need(type(policy['unit']) is str and policy['unit'] in
              (('W', 'mW') if calculator == 'rf_power' else ('dBuV/m',)), code)


def _fold(value):
    return value.strip().casefold()


def _label(value):
    return None if value is None or _fold(value) in _UNKNOWN else value


def _sources(claim, docs):
    if not claim['evidence']:
        raise _Gap('evidence_unconfirmed')
    result = []
    for ev in claim['evidence']:
        doc, pages = docs[ev['document_id']]
        page = pages[ev['file_page']]
        blocked = any(issue['code'] in {
            'parser_warning', 'parser_warnings_unobservable', 'form_resources_missing', 'page_error',
            'content_limit', 'output_limit'} and issue['file_page'] in (None, ev['file_page'])
            for issue in doc['extraction']['issues'])
        if (doc['extraction']['status'] not in ('ok', 'partial')
                or ev['literal_verified'] is not True or page['status'] != 'ok'
                or page['citable'] is not True or blocked
                or any(ev[k] is not None and _unsafe_text(ev[k]) for k in ('table', 'row'))):
            raise _Gap('evidence_unconfirmed')
        result.append({k: ev[k] for k in ('document_id', 'source_sha256', 'file_page',
                                         'text_sha256', 'line_start', 'line_end', 'table', 'row')})
    return sorted(result, key=lambda e: (e['document_id'], e['file_page'], e['line_start'],
                                         e['line_end'], e['table'] or '', e['row'] or ''))


def _contexts(detail, request, claims, docs):
    p = detail['case']['preview']
    if p['review_status'] == 'conflicting':
        raise _Gap('case_context_conflicting')
    if (p['issuer_class'] == 'unknown' or p['scope_status'] != 'in_scope'
            or p['review_status'] not in ('reviewed', 'partial') or not p['product_family']
            or p['issue_date'] is None or p['issue_date'] < '2025-01-01'
            or _unsafe_text(p['product_family'])):
        raise _Gap('case_context_unconfirmed')
    if _fold(request['rule']) not in {_fold(v) for v in p['rules']}:
        raise _Gap('rule_mismatch')
    if _fold(request['method']) not in {_fold(v) for v in p['methods']}:
        raise _Gap('method_mismatch')
    groups = []
    requirements = (
        ('issuer.classification', p['issuer_class'], {'report_fact', 'developer_inference'}, False),
        ('issuer.legal_name', None, {'report_fact'}, False),
        ('issuer.address', None, {'report_fact'}, False),
        ('report.issue_date', p['issue_date'], {'report_fact'}, False),
        ('product.family', p['product_family'], {'report_fact'}, False),
        ('method.rules', request['rule'], {'report_fact'}, True),
        ('method.references', request['method'], {'report_fact'}, True),
    )
    for field, expected, bases, collection in requirements:
        matching, values = [], set()
        for claim in claims.values():
            if claim['field'] != field or claim['status'] != 'reviewed' or claim['basis'] not in bases:
                continue
            value = claim['value']
            values_list = value if collection and type(value) is list else [value]
            if not values_list or any(type(v) is not str or not v.strip() for v in values_list):
                continue
            if not collection:
                values.add(_fold(value))
            if expected is None or _fold(expected) in {_fold(v) for v in values_list}:
                matching.extend(_sources(claim, docs))
        if not matching or (not collection and len(values) != 1):
            raise _Gap('case_context_unconfirmed')
        groups.append(matching)
    return groups


def _selected(claims, docs, identity, role, field, units):
    claim = claims.get(identity)
    if claim is None:
        raise _Gap('claim_missing')
    if claim['status'] != 'reviewed':
        raise _Gap('claim_unreviewed')
    if claim['basis'] != 'report_fact':
        raise _Gap('claim_basis_unconfirmed')
    if claim['field'] != field:
        raise _Gap('claim_role_mismatch')
    value = claim['value']
    if role == 'instrument_corrections_applied':
        if type(value) is not bool:
            raise _Gap('claim_type_mismatch')
        if value:
            raise _Gap('corrections_already_applied')
    elif type(value) not in (int, float):
        raise _Gap('claim_type_mismatch')
    if claim['unit'] not in units:
        raise _Gap('unit_mismatch')
    return {'role': role, 'claim_id': identity, 'field': field, 'value': value,
            'unit': claim['unit'], 'sources': _sources(claim, docs)}


def _anchor(source):
    return tuple(source[k] for k in ('document_id', 'source_sha256', 'file_page', 'text_sha256'))


def _rows(lists, work):
    explicit = sorted({(_label(e['table']), _label(e['row'])) for sources in lists for e in sources
                       if _label(e['table']) is not None and _label(e['row']) is not None})
    for table, row in explicit:
        all_matched = True
        for sources in lists:
            matched = False
            for e in sources:
                work[0] += 1
                if work[0] > _ROW_WORK_LIMIT:
                    raise _Fault('fcc_calc_limit_exceeded')
                if _label(e['table']) == table and _label(e['row']) == row:
                    matched = True
                    break
            if not matched:
                all_matched = False
                break
        if all_matched:
            return {'basis': 'explicit_table_row', 'table': table, 'row': row,
                    'line_start': None, 'line_end': None}
    states = {(None, None, 1, 2 ** 63 - 1)}
    for sources in lists:
        next_states = set()
        for table, row, low, high in states:
            for e in sources:
                work[0] += 1
                if work[0] > _ROW_WORK_LIMIT:
                    raise _Fault('fcc_calc_limit_exceeded')
                et, er = _label(e['table']), _label(e['row'])
                if (table is not None and et is not None and table != et
                        or row is not None and er is not None and row != er):
                    continue
                left, right = max(low, e['line_start']), min(high, e['line_end'])
                if left <= right:
                    next_states.add((table if table is not None else et,
                                     row if row is not None else er, left, right))
        states = next_states
        if not states:
            return None
    table, row, low, high = min(states, key=lambda v: (v[0] or '', v[1] or '', v[2], v[3]))
    return {'basis': 'common_line_range', 'table': table, 'row': row, 'line_start': low, 'line_end': high}


def _source_page(numerics, context_groups):
    common = set.intersection(*({ _anchor(s) for s in p['sources']} for p in numerics))
    if not common:
        raise _Gap('source_page_mismatch')
    any_row, conflict, work = False, False, [0]
    for anchor in sorted(common):
        lists = [[s for s in p['sources'] if _anchor(s) == anchor] for p in numerics]
        row = _rows(lists, work)
        if row is None:
            conflict |= (len({_label(e['table']) for sources in lists for e in sources
                              if _label(e['table']) is not None}) > 1 or
                         len({_label(e['row']) for sources in lists for e in sources
                              if _label(e['row']) is not None}) > 1)
            continue
        any_row = True
        if all(any(s['document_id'] == anchor[0] for s in group) for group in context_groups):
            return dict(zip(('document_id', 'source_sha256', 'file_page', 'text_sha256'), anchor),
                        row_binding=row)
    if any_row:
        raise _Gap('context_source_mismatch')
    raise _Gap('source_row_mismatch' if conflict else 'row_evidence_unconfirmed')


def _representable(value):
    try:
        converted = float(value)
        return math.isfinite(converted) and (type(value) is float or Fraction(converted) == value)
    except (ValueError, OverflowError):
        return False


def _ratio(value):
    if (type(value) is not Fraction or value < 0
            or max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096):
        raise _Gap('numeric_representation_unavailable')
    numerator, denominator = str(value.numerator), str(value.denominator)
    if len(numerator) > 1234 or len(denominator) > 1234:
        raise _Gap('numeric_representation_unavailable')
    return {'numerator': numerator, 'denominator': denominator}


def _run(detail, request, docs, claims, result):
    context_groups = _contexts(detail, request, claims, docs)
    p = detail['case']['preview']
    result['context'] = {'rule': request['rule'].strip(), 'method': request['method'].strip(),
                         'issuer_class': p['issuer_class'], 'product_family': p['product_family']}
    calculator = request['calculator']
    for role, field, units in _ROLES[calculator]:
        result['inputs'].append(_selected(claims, docs, request['input_claim_ids'][role], role, field, units))
    if request['reported_result_claim_id'] is not None:
        result['reported_result'] = _selected(claims, docs, request['reported_result_claim_id'],
            'reported_result', 'result.rf_power' if calculator == 'rf_power' else 'result.emc_field_strength',
            ('W', 'mW') if calculator == 'rf_power' else ('dBuV/m',))
        if result['reported_result']['unit'] != request['comparison_policy']['unit']:
            raise _Gap('unit_mismatch')
    numerics = [v for v in result['inputs'] if v['role'] != 'instrument_corrections_applied']
    flags = [v['sources'] for v in result['inputs'] if v['role'] == 'instrument_corrections_applied']
    if result['reported_result'] is not None:
        numerics.append(result['reported_result'])
    result['source_page'] = _source_page(numerics, context_groups + flags)
    if not all(_representable(v['value']) for v in result['inputs']):
        raise _Gap('numeric_representation_unavailable')
    data = {v['role']: v['value'] for v in result['inputs']}
    data['unit'] = result['inputs'][0]['unit']
    try:
        native = calculations.calculate(calculator, data)
    except (ValueError, OverflowError):
        raise _Gap('numeric_representation_unavailable') from None
    except Exception:
        raise _Gap('calculation_unavailable') from None
    expected_unit = 'W' if calculator == 'rf_power' else 'dBuV/m'
    if (type(native) is not dict or native.keys() != {'value', 'unit'}
            or type(native['value']) not in (int, float) or not _representable(native['value'])
            or type(native['unit']) is not str or native['unit'] != expected_unit
            or calculator == 'rf_power' and native['value'] <= 0):
        raise _Gap('calculation_unavailable')
    value, unit, conversion, comparison = native['value'], native['unit'], None, None
    exact_value = Fraction(value)
    if result['reported_result'] is not None:
        unit = result['reported_result']['unit']
        if unit == 'mW':
            exact_value *= 1000
            value *= 1000
            if not _representable(value) or value <= 0:
                raise _Gap('numeric_representation_unavailable')
            conversion = {'from': 'W', 'to': 'mW', 'factor': 1000, 'basis': 'explicit_unit_conversion',
                          'exact_value_ratio': _ratio(exact_value)}
        difference = abs(exact_value - Fraction(result['reported_result']['value']))
        ratio = _ratio(difference)
        matched = difference <= Fraction(request['comparison_policy']['absolute_tolerance'])
        comparison = {'matched': matched, 'absolute_difference': ratio, 'unit': unit}
    result['calculation'] = {'value': value, 'unit': unit, 'native_result': dict(native)}
    result['unit_conversion'], result['comparison'] = conversion, comparison
    result['status'] = 'calculated' if comparison is None else (
        'within_tolerance' if comparison['matched'] else 'outside_tolerance')


def check_report_calculation(case_detail, request):
    """Return a detached comparison, never a legal or physical test verdict."""
    error, phase = None, 'fcc_calc_invalid_case'
    try:
        detail = _copy(case_detail, _CASE_BYTES, 16, 50000, phase)
        docs, claims = _validate_case(detail)
        phase = 'fcc_calc_invalid_request'
        command = _copy(request, _REQUEST_BYTES, 8, 256, phase)
        _validate_request(command)
        result = {
            'schema_version': 1, 'kind': 'fcc_report_calculation_check',
            'corpus_id': detail['corpus_id'], 'case_id': detail['case']['case_id'],
            'calculator': command['calculator'], 'status': 'insufficient_evidence', 'reason_codes': [],
            'execution_mode': 'report_derived', 'synthetic': detail['synthetic'],
            'validation_scope': 'provided_case_dto_and_claim_source_consistency_only',
            'verification': {**_VERIFICATION, 'source_bytes_reverified': False,
                             'issuer_authenticity_verified': False, 'native_raw_observed': False},
            'context': {'rule': None, 'method': None, 'issuer_class': None, 'product_family': None},
            'source_page': None, 'inputs': [], 'reported_result': None, 'calculation': None,
            'unit_conversion': None, 'comparison_policy': command['comparison_policy'], 'comparison': None,
            'interpretation_scope': 'reviewer_structured_values_not_literal_semantic_certification',
        }
        try:
            _run(detail, command, docs, claims, result)
        except _Gap as gap:
            result['reason_codes'] = [gap.reason]
        return _copy(result, _OUTPUT_BYTES, 16, 8192, 'fcc_calc_invalid_case')
    except _Fault as fault:
        error = fault.code
    except Exception:
        error = phase
    raise FccReportCalculationError(error)
