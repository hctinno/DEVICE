"""Inspect retained PDF analysis generations without parsing or changing state."""
import hashlib
import json
from pathlib import PurePosixPath
import re
import sqlite3

from .document_extract import _line_spans
from .intake_analysis import validate_analysis
from .intake_documents import current_extraction_profile_id
from .store import canonical, identifier


MAX_CONTEXT_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_RESULT_BYTES = 2 * MAX_CONTEXT_BYTES
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.tsv', '.json'}
_PDF_STATUSES = {'ok', 'partial', 'empty', 'encrypted', 'malformed_pdf', 'parser_error',
                 'parser_unavailable', 'image_only', 'no_text', 'limit_exceeded'}
_LIMITS = {'max_input_bytes': MAX_SOURCE_BYTES, 'max_pages': 200,
           'max_output_chars': 1_000_000, 'max_page_content_bytes': 8 * 1024 * 1024}
REASON_CODES = frozenset({'profile_matches', 'profile_changed', 'analysis_not_completed',
                         'legacy_analysis', 'no_pdf_context', 'invalid_result', 'invalid_context',
                         'invalid_binding', 'invalid_profile', 'invalid_source',
                         'invalid_extraction', 'invalid_analysis'})


class _Invalid(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise _Invalid(code)


def _keys(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _json(payload, limit, code, *, canonical_bytes=False):
    try:
        if type(payload) is str:
            payload = payload.encode('utf-8')
        _require(type(payload) is bytes and len(payload) <= limit, code)
        value = json.loads(payload.decode('utf-8'))
        encoded = canonical(value).encode('utf-8')
        _require(not canonical_bytes or encoded == payload, code)
        return value
    except (ValueError, TypeError, OverflowError, RuntimeError, UnicodeError):
        raise _Invalid(code) from None


def _blob(store, sha, limit, code):
    _require(_hash(sha), code)
    try:
        path = store.blob_path(sha)
        _require(path.is_file() and path.stat().st_size <= limit, code)
        with path.open('rb') as stream:
            payload = stream.read(limit + 1)
        _require(len(payload) <= limit and hashlib.sha256(payload).hexdigest() == sha, code)
        return payload
    except (OSError, ValueError):
        raise _Invalid(code) from None


def _files(row):
    files = _json(row['files_json'], MAX_CONTEXT_BYTES, 'invalid_binding')
    _require(type(files) is list and _hash(row['fingerprint']) and _digest(files) == row['fingerprint'], 'invalid_binding')
    seen = set()
    for item in files:
        _keys(item, {'path', 'sha256', 'bytes'}, 'invalid_binding')
        path = item['path']
        _require(type(path) is str and path and '\\' not in path and ':' not in path
                 and not PurePosixPath(path).is_absolute()
                 and all(part not in {'', '.', '..'} for part in path.split('/'))
                 and path not in seen and _hash(item['sha256'])
                 and type(item['bytes']) is int and item['bytes'] >= 0, 'invalid_binding')
        seen.add(path)
    return files


def _profile(profile, stored_id):
    code = 'invalid_profile'
    _keys(profile, {'schema_version', 'parser', 'extractor_sha256', 'bridge_sha256', 'limits',
                    'max_text_bytes', 'max_total_text_bytes', 'max_context_bytes'}, code)
    _require(type(profile['schema_version']) is int and profile['schema_version'] == 1, code)
    _keys(profile['parser'], {'name', 'version'}, code)
    _require(profile['parser']['name'] == 'pypdf'
             and (profile['parser']['version'] is None or type(profile['parser']['version']) is str)
             and _hash(profile['extractor_sha256']) and _hash(profile['bridge_sha256']), code)
    _keys(profile['limits'], _LIMITS, code)
    for key, ceiling in _LIMITS.items():
        _require(type(profile['limits'][key]) is int and 0 < profile['limits'][key] <= ceiling, code)
    for key, ceiling in {'max_text_bytes': 256 * 1024, 'max_total_text_bytes': 2 * 1024 * 1024,
                          'max_context_bytes': MAX_CONTEXT_BYTES}.items():
        _require(type(profile[key]) is int and 0 < profile[key] <= ceiling, code)
    _require(_hash(stored_id) and _digest(profile) == stored_id, code)


def _issues(issues, code):
    _require(type(issues) is list, code)
    for issue in issues:
        _require(type(issue) is dict and set(issue) in ({'code'}, {'code', 'page_number'})
                 and type(issue['code']) is str and bool(issue['code']), code)
        if 'page_number' in issue:
            _require(type(issue['page_number']) is int and issue['page_number'] > 0, code)


def _pdf(store, item, document, profile, stored_id):
    code = 'invalid_extraction'
    fields = {'parser', 'limits', 'pages', 'issues', 'complete', 'total_pages', 'processed_pages'}
    _keys(document, set(item) | fields | {'format', 'text', 'parse_status', 'extraction_id'}, code)
    artifact = _json(_blob(store, document['extraction_id'], MAX_CONTEXT_BYTES, code),
                     MAX_CONTEXT_BYTES, code, canonical_bytes=True)
    _keys(artifact, {'schema_version', 'extraction_profile_id', 'result'}, code)
    _require(type(artifact['schema_version']) is int and artifact['schema_version'] == 1
             and artifact['extraction_profile_id'] == stored_id, code)
    result = artifact['result']
    _keys(result, fields | {'schema_version', 'source', 'status'}, code)
    _require(type(result['schema_version']) is int and result['schema_version'] == 1
             and result['source'] == {'filename': item['path'], 'sha256': item['sha256'],
                                      'size_bytes': item['bytes'], 'format': 'pdf'}
             and type(result['source'].get('size_bytes')) is int
             and result['limits'] == profile['limits'], code)
    expected = {**item, 'format': 'pdf', 'text': None, 'parse_status': result['status'],
                'extraction_id': document['extraction_id'], **{key: result[key] for key in fields}}
    _require(document == expected and type(result['status']) is str and result['status'] in _PDF_STATUSES
             and type(result['complete']) is bool and result['complete'] == (result['status'] in {'ok', 'empty'})
             and type(result['processed_pages']) is int
             and type(result['pages']) is list and result['processed_pages'] == len(result['pages'])
             and len(result['pages']) <= profile['limits']['max_pages']
             and (result['total_pages'] is None or type(result['total_pages']) is int and result['total_pages'] >= 0), code)
    if result['complete']:
        _require(type(result['total_pages']) is int and result['processed_pages'] == result['total_pages'], code)
    _keys(result['parser'], {'name', 'version'}, code)
    _require(type(result['parser']['name']) is str and result['parser']['name'] in {'pdf', 'pypdf'}
             and (result['parser']['version'] is None or type(result['parser']['version']) is str), code)
    if result['status'] == 'parser_unavailable':
        _require(result['parser'] == {'name': 'pypdf', 'version': None}
                 and not result['pages'] and result['total_pages'] is None, code)
    elif result['parser']['name'] == 'pdf':
        _require(result['parser']['version'] is None and result['status'] == 'limit_exceeded'
                 and item['bytes'] > profile['limits']['max_input_bytes']
                 and not result['pages'] and result['total_pages'] is None, code)
    else:
        _require(type(result['parser']['version']) is str and result['parser'] == profile['parser'], code)
    _issues(result['issues'], code)
    size, characters, previous = 0, 0, 0
    for page in result['pages']:
        _keys(page, {'page_number', 'status', 'text', 'text_sha256', 'line_spans'}, code)
        number, text = page['page_number'], page['text']
        _require(type(number) is int and previous < number <= profile['limits']['max_pages']
                 and (result['total_pages'] is None or number <= result['total_pages'])
                 and type(text) is str and type(page['status']) is str
                 and page['status'] in {'ok', 'truncated', 'empty', 'image_only', 'no_text', 'limit_exceeded', 'error'}
                 and _hash(page['text_sha256'])
                 and hashlib.sha256(text.encode('utf-8')).hexdigest() == page['text_sha256']
                 and page['line_spans'] == _line_spans(text), code)
        previous = number; size += len(text.encode('utf-8')); characters += len(text)
    _require(size <= profile['max_text_bytes'] and characters <= profile['limits']['max_output_chars'], code)
    return size


def _documents(store, files, documents, profile, stored_id):
    _require(type(documents) is list and len(documents) == len(files), 'invalid_context')
    total, pdfs = 0, 0
    for item, document in zip(files, documents):
        _require(type(document) is dict and all(document.get(key) == value for key, value in item.items()), 'invalid_binding')
        payload = _blob(store, item['sha256'], min(MAX_SOURCE_BYTES, item['bytes']), 'invalid_source')
        _require(len(payload) == item['bytes'], 'invalid_source')
        suffix = PurePosixPath(item['path']).suffix.lower()
        if suffix == '.pdf':
            _require(document.get('format') == 'pdf', 'invalid_context')
            total += _pdf(store, item, document, profile, stored_id); pdfs += 1
        else:
            code = 'invalid_context'
            _keys(document, set(item) | {'format', 'text', 'parse_status', 'extraction_status', 'issues'}, code)
            _require(document['format'] == ('text' if suffix in _TEXT_SUFFIXES else 'unsupported'), code)
            _issues(document['issues'], code)
            text = document['text']
            if text is not None:
                _require(type(text) is str and suffix in _TEXT_SUFFIXES
                         and len(payload) <= profile['max_text_bytes']
                         and document['parse_status'] == 'text'
                         and document['extraction_status'] == ('ok' if text.strip() else 'empty'), code)
                try:
                    _require(payload.decode('utf-8-sig') == text, code)
                except UnicodeError:
                    raise _Invalid(code) from None
                total += len(payload)
            else:
                _require(document['parse_status'] == 'requires_parser' and type(document['extraction_status']) is str
                         and document['extraction_status'] in {'limit_exceeded', 'invalid_encoding', 'unsupported_format'}, code)
    _require(total <= profile['max_total_text_bytes'], 'invalid_context')
    return pdfs


def _inspect(store, row):
    result = _json(row['result_json'], MAX_RESULT_BYTES, 'invalid_result')
    _keys(result, {'submission', 'summary'}, 'invalid_result')
    analysis = result['submission']
    _require(type(analysis) is dict and type(result['summary']) is dict
             and result['summary'].get('submitted') == analysis, 'invalid_result')
    version = analysis.get('schema_version')
    _require(type(version) is int and version in {1, 2}, 'invalid_analysis')
    if version == 1:
        _keys(analysis, {'schema_version', 'producer', 'identity', 'facts', 'missing_fields'}, 'invalid_analysis')
        return 'legacy_unbound', 'legacy_analysis', None, None
    context_id = analysis.get('context_id')
    payload = _blob(store, context_id, MAX_CONTEXT_BYTES, 'invalid_context')
    context = _json(payload, MAX_CONTEXT_BYTES, 'invalid_context', canonical_bytes=True)
    _keys(context, {'schema_version', 'binding', 'profile', 'extraction_profile_id', 'documents'}, 'invalid_context')
    _require(type(context['schema_version']) is int and context['schema_version'] == 1, 'invalid_context')
    files = _files(row)
    _require(context['binding'] == {'source_id': row['source_id'], 'intake_id': row['intake_id'],
                                   'revision': row['revision'], 'revision_fingerprint': row['fingerprint'], 'files': files}, 'invalid_binding')
    profile, stored_id = context['profile'], context['extraction_profile_id']
    _profile(profile, stored_id)
    _require(len(payload) <= profile['max_context_bytes'], 'invalid_context')
    pdfs = _documents(store, files, context['documents'], profile, stored_id)
    try:
        validate_analysis(analysis, context['documents'], bool(row['synthetic']), context_id=context_id)
    except (ValueError, TypeError, KeyError, OverflowError, RuntimeError):
        raise _Invalid('invalid_analysis') from None
    if not pdfs:
        return 'legacy_unbound', 'no_pdf_context', None, None
    return 'verified', None, context_id, stored_id


def validate_retained_analysis(store, stored_record):
    """Validate a retained revision/result under its stored profile, without writes.

    Callers may pass a row already fixed by their own read or writer transaction.
    The tuple is (verified|legacy_unbound, reason, context_id, profile_id).
    This does not compare current code or grant readiness/execution authority.
    """
    try:
        return _inspect(store, stored_record)
    except _Invalid:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RuntimeError, OSError):
        raise _Invalid('invalid_context') from None


def analysis_generation_status(store, intake_id):
    """Return only sanitized generation metadata from one DB read snapshot."""
    try:
        identifier(intake_id)
    except ValueError:
        raise ValueError('Invalid intake identifier') from None
    try:
        current_id = current_extraction_profile_id()
        if not _hash(current_id):
            raise ValueError()
    except (OSError, ValueError):
        raise ValueError('Current extraction profile unavailable') from None
    try:
        with store.connection() as con:
            con.execute('BEGIN')
            row = con.execute('SELECT i.intake_id,i.source_id,i.revision,r.fingerprint,'
                              'CASE WHEN length(CAST(r.files_json AS BLOB))<=? THEN r.files_json END AS files_json,r.synthetic,'
                              'j.state,CASE WHEN length(CAST(j.result_json AS BLOB))<=? THEN j.result_json END AS result_json FROM intakes i '
                              'LEFT JOIN intake_revisions r ON r.intake_id=i.intake_id AND r.revision=i.revision '
                              'LEFT JOIN intake_jobs j ON j.intake_id=i.intake_id AND j.revision=i.revision '
                              'WHERE i.intake_id=?', (MAX_CONTEXT_BYTES, MAX_RESULT_BYTES, intake_id)).fetchone()
            row = dict(row) if row is not None else None
    except sqlite3.Error:
        raise ValueError('Cannot read analysis generation') from None
    if row is None:
        raise ValueError('Unknown intake')
    response = {'schema_version': 1, 'kind': 'intake_analysis_generation', 'intake_id': intake_id,
                'revision': row['revision'], 'status': 'unavailable', 'reason_codes': ['analysis_not_completed'],
                'context_id': None, 'stored_profile_id': None, 'current_profile_id': current_id,
                'reanalysis_required': False}
    if row['state'] != 'completed':
        return response
    try:
        status, reason, context_id, stored_id = validate_retained_analysis(store, row)
    except _Invalid as error:
        status, reason, context_id, stored_id = 'invalid', str(error), None, None
    except (ValueError, TypeError, KeyError, OverflowError, RuntimeError):
        status, reason, context_id, stored_id = 'invalid', 'invalid_context', None, None
    if status == 'verified':
        status = 'current' if stored_id == current_id else 'stale'
        reason = 'profile_matches' if status == 'current' else 'profile_changed'
    response.update(status=status, reason_codes=[reason], context_id=context_id,
                    stored_profile_id=stored_id, reanalysis_required=status == 'stale')
    return response
