"""Prepare a report-bound candidate for one fixed virtual fixture; never dispatch."""
from datetime import date, datetime, timedelta
from fractions import Fraction
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

from labflow.virtual_fleet import method_adapter


_CASE_BYTES, _REQUEST_BYTES, _DESCRIPTOR_BYTES, _OUTPUT_BYTES = 8 * 1024 * 1024, 32768, 32768, 131072
_ROW_WORK_LIMIT = 65536


class FccReportFixtureRecipeError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


# Standalone 021 v1 DTO validation; no dependency on another adapter private API.
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


_UNKNOWN = {'unknown', 'unconfirmed', 'not_reported', 'n/a', '미확인', '불명', '-', '–', '—'}


class _Fault(Exception):
    def __init__(self, code):
        self.code = code


class _Gap(Exception):
    def __init__(self, reason):
        self.reason = reason


def _need(condition, code='fcc_recipe_invalid_case'):
    if not condition:
        raise _Fault(code)


def _tree(value, max_depth, max_nodes, *, code, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    if depth > max_depth or count[0] > max_nodes:
        raise _Fault('fcc_recipe_limit_exceeded')
    kind = type(value)
    if value is None or kind is bool:
        return value
    if kind is str:
        if len(value) > 16384:
            raise _Fault('fcc_recipe_limit_exceeded')
        return value
    if kind is int:
        if value.bit_length() > 4096:
            raise _Fault('fcc_recipe_limit_exceeded')
        return value
    if kind is float:
        _need(math.isfinite(value), code)
        return value
    _need(kind in (dict, list), code)
    if len(value) > max_nodes - count[0]:
        raise _Fault('fcc_recipe_limit_exceeded')
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
                raise _Fault('fcc_recipe_limit_exceeded')
            chunks.append(chunk)
        data = b''.join(chunks)
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError):
        raise _Fault(code) from None
    return json.loads(data)


def _keys(value, keys):
    _need(type(value) is dict and value.keys() == set(keys))


def _text(value, maximum=16384, nullable=False):
    if type(value) is str and len(value) > maximum:
        raise _Fault('fcc_recipe_limit_exceeded')
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
        raise _Fault('fcc_recipe_limit_exceeded')
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
        raise _Fault('fcc_recipe_invalid_case') from None


def _stamp(value):
    _text(value, 64)
    _need(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?\+09:00', value))
    try:
        _need(datetime.fromisoformat(value).utcoffset() == timedelta(hours=9))
    except ValueError:
        raise _Fault('fcc_recipe_invalid_case') from None


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
        raise _Fault('fcc_recipe_invalid_case') from None


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
        raise _Fault('fcc_recipe_limit_exceeded')
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
        _tree(claim['value'], 6, 50000, code='fcc_recipe_invalid_case')
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
                    raise _Fault('fcc_recipe_limit_exceeded')
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
                    raise _Fault('fcc_recipe_limit_exceeded')
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


_RECIPE, _MODEL = 'conducted_sensor_fixture_v1', 'SM-A176U'
_RULES = {'47 cfr 15.247', '47 cfr §15.247'}
_SETTINGS = (
    ('power_dbm', 'setting.dut_power_dbm', 'dBm', None),
    ('frequency_hz', 'setting.frequency', 'Hz', 2450000000),
    ('bandwidth_hz', 'setting.bandwidth', 'Hz', 20000000),
    ('modulation', 'setting.modulation', None, 'OFDM'),
    ('duty_cycle', 'setting.duty_cycle', 'ratio', .25),
    ('crest_factor_db', 'setting.crest_factor', 'dB', 3),
    ('attenuation_db', 'setting.path_attenuation', 'dB', 10),
    ('switch_loss_db', 'setting.switch_loss', 'dB', .5),
    ('coupling_db', 'setting.coupling', 'dB', 20),
    ('tested_model', 'setting.tested_model', None, _MODEL),
    ('supply_voltage_v', 'setting.supply_voltage', 'V', 5),
    ('supply_current_limit_a', 'setting.supply_current_limit', 'A', 1),
    ('supply_load_resistance_ohm', 'setting.supply_load_resistance', 'ohm', 50),
    ('chamber_temperature_c', 'setting.chamber_temperature', 'C', 23),
    ('chamber_humidity_percent', 'setting.chamber_humidity', '%', 45),
    ('selected_rf_input', 'setting.selected_rf_input', None, 'rf_1'),
)
_QUANTITIES = (
    ('reference_plane', 'method.reference_plane', 'sensor_input', 'reference_plane_mismatch'),
    ('metric', 'method.power_metric', 'on_mean_power', 'power_metric_mismatch'),
    ('quantity_unit', 'method.power_unit', 'dBm', 'quantity_unit_mismatch'),
)
_POINT = ('power_dbm', 'frequency_hz', 'bandwidth_hz', 'modulation',
          'duty_cycle', 'crest_factor_db', 'tested_model')
_BOOTSTRAP = {r: expected for r, _, _, expected in _SETTINGS[-6:]}
_FIXED_QUANTITY = {'reference_plane': 'sensor_input', 'metric': 'on_mean_power', 'unit': 'dBm'}
_FIXED_SETUP = {
    'frequency_hz': 2.45e9, 'bandwidth_hz': 20e6, 'modulation': 'OFDM',
    'duty_cycle': .25, 'crest_factor_db': 3, 'attenuation_db': 10, 'switch_loss_db': .5,
    'coupling_db': 20, 'coupling_basis': 'declared_synthetic_policy',
}
_ASSUMPTIONS = ('sensor_calibration_valid_true', 'triggered_sensor_acquisition',
                'auxiliary_meter_analyzer_bootstrap')
_INCOMPATIBLE = {'recipe_mismatch', 'model_mismatch', 'rule_scope_mismatch',
                 'setting_value_mismatch', 'unit_mismatch', 'reference_plane_mismatch',
                 'power_metric_mismatch', 'quantity_unit_mismatch'}


def _request(value):
    code = 'fcc_recipe_invalid_request'
    _need(type(value) is dict and value.keys() == {
        'recipe_id', 'model', 'rule', 'method', 'product_claim_ids', 'setting_claim_ids',
        'quantity_claim_ids'}, code)
    for key, maximum in (('recipe_id', 128), ('model', 128), ('rule', 256), ('method', 256)):
        item = value[key]
        _need(type(item) is str and item.strip() and len(item) <= maximum and not _unsafe_text(item), code)
    all_ids = []
    for key, roles in (('product_claim_ids', {'family', 'models'}),
                       ('setting_claim_ids', {r[0] for r in _SETTINGS}),
                       ('quantity_claim_ids', {r[0] for r in _QUANTITIES})):
        selector = value[key]
        _need(type(selector) is dict and selector.keys() == roles, code)
        all_ids.extend(selector.values())
    _need(all(type(i) is str and _ID.fullmatch(i) for i in all_ids)
          and len(set(all_ids)) == len(all_ids), code)


def _base(detail, request):
    return {
        'schema_version': 1, 'kind': 'fcc_report_fixture_recipe', 'corpus_id': detail['corpus_id'],
        'case_id': detail['case']['case_id'], 'execution_mode': 'virtual_fixture_preparation_only',
        'source_synthetic': detail['synthetic'], 'target_synthetic': True,
        'status': 'insufficient_evidence', 'reason_codes': [],
        'request_context': {k: request[k] for k in ('recipe_id', 'model', 'rule', 'method')},
        'verification': {**_VERIFICATION, 'source_bytes_reverified': False,
                         'issuer_authenticity_verified': False, 'native_raw_observed': False},
        'authority': {'execution_authorized': False, 'current_authority': False,
                      'runtime_created': False, 'command_count': 0,
                      'readiness_scope': 'historical_report_context_only'},
        'method_approval': 'not_assessed',
        'coverage': {'regulatory_scope_complete': False, 'phy_coverage': 'not_assessed',
                     'report_reproduction_verified': False, 'bootstrap_calibration_verified': False},
        'source_binding': None, 'product_bindings': [], 'setting_bindings': [], 'quantity_bindings': [],
        'context_bindings': [], 'fixture_descriptor': None,
        'bootstrap_policy': {'basis': 'declared_synthetic_policy',
                             'fixed_requirements': dict(_BOOTSTRAP),
                             'unverified_assumptions': list(_ASSUMPTIONS), 'verified': False},
        'candidate': None, 'source_projection_sha256': None,
        'validation_scope': 'provided_case_dto_and_used_claim_source_consistency_only',
    }


def _claim(claims, identity, field):
    value = claims.get(identity)
    if value is None:
        raise _Gap('claim_missing')
    if value['status'] != 'reviewed':
        raise _Gap('claim_unreviewed')
    if value['basis'] != 'report_fact':
        raise _Gap('claim_basis_unconfirmed')
    if value['field'] != field:
        raise _Gap('claim_role_mismatch')
    return value


def _projection(claim, docs, role):
    return {'role': role, 'claim_id': claim['claim_id'], 'field': claim['field'],
            'value': claim['value'], 'unit': claim['unit'], 'sources': _sources(claim, docs)}


def _safe_text(value):
    return type(value) is str and bool(value.strip()) and not _unsafe_text(value.strip())


def _context_groups(detail, request, docs, claims):
    preview = detail['case']['preview']
    if preview['review_status'] == 'conflicting':
        raise _Gap('case_context_conflicting')
    if (preview['issuer_class'] == 'unknown' or preview['scope_status'] != 'in_scope'
            or preview['review_status'] not in ('reviewed', 'partial')
            or preview['product_family'] is None or preview['issue_date'] is None
            or preview['issue_date'] < '2025-01-01'):
        raise _Gap('case_context_unconfirmed')
    if (_fold(request['rule']) not in {_fold(s) for s in preview['rules']}
            or _fold(request['method']) not in {_fold(s) for s in preview['methods']}):
        raise _Gap('method_context_unconfirmed')
    groups = []
    for field, expected, bases, collection in (
        ('issuer.classification', preview['issuer_class'], {'report_fact', 'developer_inference'}, False),
        ('issuer.legal_name', None, {'report_fact'}, False),
        ('issuer.address', None, {'report_fact'}, False),
        ('report.issue_date', preview['issue_date'], {'report_fact'}, False),
        ('product.family', preview['product_family'], {'report_fact'}, False),
        ('method.rules', request['rule'], {'report_fact'}, True),
        ('method.references', request['method'], {'report_fact'}, True),
    ):
        matched, values, sources = [], set(), []
        for item in claims.values():
            if item['field'] != field or item['status'] != 'reviewed' or item['basis'] not in bases:
                continue
            value = item['value']
            strings = value if collection and type(value) is list else [value]
            if not strings or any(type(s) is not str or not s.strip() for s in strings):
                continue
            if not collection:
                values.add(_fold(value))
            if expected is None or _fold(expected) in {_fold(s) for s in strings}:
                matched.append(item['claim_id'])
                sources.extend(_sources(item, docs))
        if not matched or (not collection and len(values) != 1):
            reason = 'method_context_unconfirmed' if field.startswith('method.') else 'case_context_unconfirmed'
            raise _Gap(reason)
        groups.append({'field': field, 'claim_ids': sorted(matched),
                       'sources': sorted(sources, key=lambda s: (_anchor(s), s['line_start'],
                                                                 s['line_end'], s['table'] or '', s['row'] or ''))})
    return groups


def _products(detail, request, docs, claims, result):
    preview = detail['case']['preview']
    for role, field in (('family', 'product.family'), ('models', 'product.models')):
        item = _claim(claims, request['product_claim_ids'][role], field)
        if item['unit'] is not None:
            raise _Gap('unit_mismatch')
        value = item['value']
        if role == 'family':
            if not _safe_text(value):
                raise _Gap('claim_type_mismatch')
            if _fold(value) != _fold(preview['product_family']):
                raise _Gap('case_context_unconfirmed')
        else:
            models = value if type(value) is list else [value]
            if not models or any(not _safe_text(s) for s in models):
                raise _Gap('claim_type_mismatch')
            normalized = {_fold(s) for s in models}
            if (not normalized <= {_fold(s) for s in preview['models']}
                    or _fold(request['model']) not in normalized):
                raise _Gap('model_mismatch')
        result['product_bindings'].append(_projection(item, docs, role))


def _settings_and_quantities(request, docs, claims, result):
    for role, field, unit, expected in _SETTINGS:
        item = _claim(claims, request['setting_claim_ids'][role], field)
        if item['unit'] != unit:
            raise _Gap('unit_mismatch')
        value = item['value']
        if type(expected) is str:
            if not _safe_text(value):
                raise _Gap('claim_type_mismatch')
            if role == 'tested_model':
                if _fold(value) != _fold(request['model']):
                    raise _Gap('model_mismatch')
            elif value != expected:
                raise _Gap('setting_value_mismatch')
        else:
            if type(value) not in (int, float):
                raise _Gap('claim_type_mismatch')
            number = Fraction(value)
            if (role == 'power_dbm' and not Fraction(-30) <= number <= Fraction(20)
                    or role != 'power_dbm' and number != Fraction(expected)):
                raise _Gap('setting_value_mismatch')
        result['setting_bindings'].append(_projection(item, docs, role))
    for role, field, expected, reason in _QUANTITIES:
        item = _claim(claims, request['quantity_claim_ids'][role], field)
        if item['unit'] is not None:
            raise _Gap('unit_mismatch')
        if not _safe_text(item['value']):
            raise _Gap('claim_type_mismatch')
        if item['value'] != expected:
            raise _Gap(reason)
        result['quantity_bindings'].append(_projection(item, docs, role))


def _binding_claim(claims, docs, point_ids, context_ids, document_id):
    signatures, candidates = set(), []
    for item in sorted(claims.values(), key=lambda c: c['claim_id']):
        if (item['field'] != 'setting.setup_binding' or item['status'] != 'reviewed'
                or item['basis'] != 'report_fact' or item['unit'] is not None):
            continue
        value = item['value']
        if type(value) is not dict or value.keys() != {'point_claim_ids', 'context_claim_ids'}:
            continue
        point, context = value['point_claim_ids'], value['context_claim_ids']
        if (type(point) is not list or type(context) is not list
                or not all(type(i) is str and _ID.fullmatch(i) for i in point + context)
                or len(point) != 7 or len(context) != 12
                or len(set(point + context)) != 19 or set(point) != point_ids
                or not set(point + context) <= claims.keys()):
            continue
        sources = _sources(item, docs)
        if not any(s['document_id'] == document_id for s in sources):
            continue
        signature = tuple(sorted(context))
        signatures.add(signature)
        if set(context) == context_ids:
            candidates.append({'field': item['field'], 'claim_ids': [item['claim_id']], 'sources': sources})
    if len(signatures) > 1:
        raise _Gap('setup_binding_conflicting')
    if not candidates:
        raise _Gap('setup_binding_missing')
    return candidates[0]


def _source_binding(request, docs, claims, result):
    settings = {b['role']: b for b in result['setting_bindings']}
    points = [settings[role] for role in _POINT]
    contexts = [b for b in result['setting_bindings'] if b['role'] not in _POINT] + result['quantity_bindings']
    anchors = set.intersection(*({_anchor(s) for s in p['sources']} for p in points))
    if not anchors:
        raise _Gap('source_page_mismatch')
    work, any_row, conflict, context_missing, link_missing = [0], False, False, False, False
    for anchor in sorted(anchors):
        lists = [[s for s in p['sources'] if _anchor(s) == anchor] for p in points]
        row = _rows(lists, work)
        if row is None:
            conflict |= (len({_label(e['table']) for group in lists for e in group
                              if _label(e['table']) is not None}) > 1 or
                         len({_label(e['row']) for group in lists for e in group
                              if _label(e['row']) is not None}) > 1)
            continue
        any_row = True
        required = result['context_bindings'] + result['product_bindings'] + contexts
        if not all(any(s['document_id'] == anchor[0] for s in p['sources']) for p in required):
            context_missing = True
            continue
        context_lists = [[s for s in item['sources'] if _anchor(s) == anchor] for item in contexts]
        joint_row = _rows(lists + context_lists, work) if all(context_lists) else None
        direct = joint_row is not None
        if direct:
            row = joint_row
        binding = None
        # Direct row evidence does not erase a reviewed contradictory setup.
        try:
            binding = _binding_claim(claims, docs, {p['claim_id'] for p in points},
                                     {p['claim_id'] for p in contexts}, anchor[0])
        except _Gap as gap:
            if gap.reason != 'setup_binding_missing':
                raise
            if not direct:
                link_missing = True
                continue
        result['source_binding'] = dict(zip(
            ('document_id', 'source_sha256', 'file_page', 'text_sha256'), anchor),
            row_binding=row, setup_binding_claim_id=None if binding is None else binding['claim_ids'][0])
        if binding is not None:
            result['context_bindings'].append(binding)
        return
    if link_missing:
        raise _Gap('setup_binding_missing')
    if context_missing or any_row:
        raise _Gap('context_source_mismatch')
    raise _Gap('source_row_mismatch' if conflict else 'row_evidence_unconfirmed')


def _descriptor(request, power):
    try:
        raw = method_adapter.describe_fixture_method(request['recipe_id'], model=request['model'],
                                                       settings={'power_dbm': power})
    except Exception:
        raise _Gap('fixture_contract_unavailable') from None
    try:
        reply = _copy(raw, _DESCRIPTOR_BYTES, 12, 4096, 'fcc_recipe_invalid_case')
    except Exception:
        raise _Gap('fixture_contract_unavailable') from None
    expected = {
        'schema_version': 1, 'kind': 'virtual_fixture_method', 'recipe_id': _RECIPE, 'model': _MODEL,
        'supported': True, 'reason_codes': [], 'settings': {'power_dbm': float(power)},
        'quantity': dict(_FIXED_QUANTITY), 'synthetic_setup': dict(_FIXED_SETUP),
        'method_approval': 'not_assessed', 'regulatory_scope_complete': False, 'resumable': False,
        'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
    }
    # Typed JSON equality keeps booleans/numbers and unknown/private fields separate.
    if json.dumps(reply, sort_keys=True, separators=(',', ':')) != json.dumps(expected, sort_keys=True, separators=(',', ':')):
        raise _Gap('fixture_contract_changed')
    return reply


def _prepare(detail, request, docs, claims, result):
    if request['recipe_id'] != _RECIPE:
        raise _Gap('recipe_mismatch')
    if request['model'] != _MODEL:
        raise _Gap('model_mismatch')
    if _fold(request['rule']) not in _RULES:
        raise _Gap('rule_scope_mismatch')
    result['context_bindings'] = _context_groups(detail, request, docs, claims)
    _products(detail, request, docs, claims, result)
    _settings_and_quantities(request, docs, claims, result)
    _source_binding(request, docs, claims, result)
    power = result['setting_bindings'][0]['value']
    descriptor = _descriptor(request, power)
    result['fixture_descriptor'] = descriptor
    result['candidate'] = {'recipe_id': _RECIPE, 'model': _MODEL,
                           'settings': dict(descriptor['settings']), 'source_synthetic': detail['synthetic']}
    projection = {k: result[k] for k in ('corpus_id', 'case_id', 'source_synthetic',
        'request_context', 'product_bindings', 'setting_bindings',
        'quantity_bindings', 'context_bindings', 'source_binding', 'fixture_descriptor', 'bootstrap_policy')}
    # Projection is bounded independently and the whole response is bounded again.
    bounded = _copy(projection, _OUTPUT_BYTES, 16, 8192, 'fcc_recipe_invalid_case')
    canonical = json.dumps(bounded, sort_keys=True, ensure_ascii=False, allow_nan=False,
                           separators=(',', ':')).encode('utf-8')
    result['source_projection_sha256'] = hashlib.sha256(canonical).hexdigest()
    result['status'] = 'prepared_for_fixed_virtual_fixture'


def prepare_report_fixture_recipe(case_detail, request):
    """Prepare historical source bindings; never grant permission or create a runtime."""
    error, phase = None, 'fcc_recipe_invalid_case'
    try:
        detail = _copy(case_detail, _CASE_BYTES, 16, 50000, phase)
        docs, claims = _validate_case(detail)
        phase = 'fcc_recipe_invalid_request'
        command = _copy(request, _REQUEST_BYTES, 8, 1024, phase)
        _request(command)
        result = _base(detail, command)
        try:
            _prepare(detail, command, docs, claims, result)
        except _Gap as gap:
            result['status'] = ('incompatible_with_fixed_fixture' if gap.reason in _INCOMPATIBLE
                                else 'insufficient_evidence')
            result['reason_codes'] = [gap.reason]
            result['candidate'] = result['source_projection_sha256'] = None
        return _copy(result, _OUTPUT_BYTES, 16, 8192, 'fcc_recipe_invalid_case')
    except _Fault as fault:
        error = fault.code
    except Exception:
        error = phase
    raise FccReportFixtureRecipeError(error)
