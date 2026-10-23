"""Prepare retained PDF page evidence outside analysis write transactions."""
import copy
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import re

from . import document_extract
from .document_extract import ExtractionLimits, extract_document
from .store import canonical, identifier


TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.tsv', '.json'}
MAX_TEXT_BYTES = 256 * 1024
MAX_TOTAL_TEXT_BYTES = 2 * 1024 * 1024
MAX_CONTEXT_BYTES = 4 * 1024 * 1024
EXTRACTION_LIMITS = ExtractionLimits()
PDF_STATUSES = {'ok', 'partial', 'empty', 'encrypted', 'malformed_pdf', 'parser_error',
                'parser_unavailable', 'image_only', 'no_text', 'limit_exceeded'}
_HASH = re.compile(r'[a-f0-9]{64}\Z')


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _encoded(value):
    return canonical(value).encode('utf-8')


def _profile():
    try:
        parser_version = importlib.metadata.version('pypdf')
    except importlib.metadata.PackageNotFoundError:
        parser_version = None
    return {'schema_version': 1, 'parser': {'name': 'pypdf', 'version': parser_version},
            'extractor_sha256': _hash(Path(document_extract.__file__).read_bytes().replace(b'\r\n', b'\n')),
            'bridge_sha256': _hash(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
            'limits': asdict(EXTRACTION_LIMITS), 'max_text_bytes': MAX_TEXT_BYTES,
            'max_total_text_bytes': MAX_TOTAL_TEXT_BYTES, 'max_context_bytes': MAX_CONTEXT_BYTES}


def current_extraction_profile_id():
    """Identify current parser/code/limits without parsing or retaining data."""
    return _hash(_encoded(_profile()))


def _spans(text):
    result, start = [], 0
    for number, part in enumerate(text.splitlines(keepends=True), 1):
        content = part.splitlines()[0]
        result.append({'line_number': number, 'start': start, 'end': start + len(content)})
        start += len(part)
    return result


def _files(files):
    if type(files) is not list:
        raise ValueError('Document list required')
    seen = set()
    for item in files:
        if type(item) is not dict or set(item) != {'path', 'sha256', 'bytes'}:
            raise ValueError('Invalid retained document fields')
        path = item['path']
        if (type(path) is not str or not path or '\\' in path or ':' in path
                or PurePosixPath(path).is_absolute() or any(part in {'', '.', '..'} for part in path.split('/'))
                or path in seen or type(item['sha256']) is not str or not _HASH.fullmatch(item['sha256'])
                or type(item['bytes']) is not int or item['bytes'] < 0):
            raise ValueError('Invalid retained document identity')
        seen.add(path)


def _binding(files, source_id, intake_id, revision, revision_fingerprint):
    _files(files); identifier(source_id); identifier(intake_id)
    if type(revision) is not int or revision < 1 or revision_fingerprint != _hash(_encoded(files)):
        raise ValueError('Invalid revision binding')
    return {'source_id': source_id, 'intake_id': intake_id, 'revision': revision,
            'revision_fingerprint': revision_fingerprint, 'files': copy.deepcopy(files)}


def _retain(store, value, synthetic):
    payload = _encoded(value)
    with store.connection() as con:
        # Serialize retained artifact writers, after parsing has finished.
        con.execute('BEGIN IMMEDIATE')
        sha = store.write_blob(payload)
        store.register_blob(con, sha, len(payload), 'analysis_context', synthetic)
    return sha


def _pdf_document(item, result, extraction_id):
    return {**item, 'format': 'pdf', 'text': None, 'parse_status': result['status'],
            'extraction_id': extraction_id, **{name: copy.deepcopy(result[name]) for name in
                ('parser', 'limits', 'pages', 'issues', 'complete', 'total_pages', 'processed_pages')}}


def _bounded_pdf(result, item, budget):
    result = copy.deepcopy(result)
    if (result['source'] != {'filename': item['path'], 'sha256': item['sha256'],
                             'size_bytes': item['bytes'], 'format': 'pdf'}
            or result['status'] not in PDF_STATUSES):
        raise ValueError('Extraction identity mismatch')
    remaining, changed, seen = min(MAX_TEXT_BYTES, budget), False, set()
    for page in result['pages']:
        number, text = page['page_number'], page['text']
        if (type(number) is not int or number < 1 or number in seen or type(text) is not str
                or page['text_sha256'] != _hash(text.encode('utf-8')) or page['line_spans'] != _spans(text)):
            raise ValueError('Invalid extracted page')
        seen.add(number)
        encoded = text.encode('utf-8')
        if len(encoded) > remaining:
            text = encoded[:remaining].decode('utf-8', errors='ignore')
            page.update(text=text, text_sha256=_hash(text.encode('utf-8')),
                        line_spans=_spans(text), status='truncated')
            result['issues'].append({'code': 'utf8_output_limit', 'page_number': number})
            changed = True
        remaining -= len(text.encode('utf-8'))
    if changed:
        result.update(status='partial' if any(p['text'].strip() for p in result['pages']) else 'limit_exceeded', complete=False)
    return result, min(MAX_TEXT_BYTES, budget) - remaining


def prepare_analysis_documents(store, files, *, source_id, intake_id, revision, revision_fingerprint):
    """Return retained, deterministic page context; callers must hold no write txn."""
    binding = _binding(files, source_id, intake_id, revision, revision_fingerprint)
    profile = _profile(); profile_id = _hash(_encoded(profile))
    documents, pdf_results, remaining, synthetic = [], {}, MAX_TOTAL_TEXT_BYTES, False
    for item in files:
        payload = store.verify_blob(item['sha256']).read_bytes()
        if len(payload) != item['bytes'] or _hash(payload) != item['sha256']:
            raise ValueError('Evidence changed during preparation')
        is_synthetic = store.evidence_is_synthetic(item['sha256'])
        synthetic = synthetic or is_synthetic
        suffix = PurePosixPath(item['path']).suffix.lower()
        if suffix == '.pdf':
            result = extract_document(payload, item['path'], limits=EXTRACTION_LIMITS)
            result, used = _bounded_pdf(result, item, remaining); remaining -= used
            pdf_results[len(documents)] = (result, is_synthetic)
            document = _pdf_document(item, result, '0' * 64)
        else:
            text, status, issues = None, 'unsupported_format', [{'code': 'unsupported_format'}]
            if suffix in TEXT_SUFFIXES:
                status, issues = 'limit_exceeded', [{'code': 'text_byte_limit'}]
                if len(payload) <= min(MAX_TEXT_BYTES, remaining):
                    try:
                        text = payload.decode('utf-8-sig'); remaining -= len(payload)
                        status, issues = 'ok' if text.strip() else 'empty', []
                    except UnicodeError:
                        status, issues = 'invalid_encoding', [{'code': 'invalid_utf8'}]
            document = {**item, 'format': 'text' if suffix in TEXT_SUFFIXES else 'unsupported',
                        'text': text, 'parse_status': 'text' if text is not None else 'requires_parser',
                        'extraction_status': status, 'issues': issues}
        documents.append(document)
    manifest = {'schema_version': 1, 'binding': binding, 'profile': profile,
                'extraction_profile_id': profile_id, 'documents': documents}
    # Page line maps can exceed the context budget even with bounded UTF-8.
    # Keep that as an explicit unread PDF failure instead of poisoning the job.
    while len(_encoded(manifest)) > MAX_CONTEXT_BYTES:
        candidates = [index for index, (result, _) in pdf_results.items() if result['pages']]
        if not candidates:
            raise ValueError('Analysis context metadata exceeds byte limit')
        index = max(candidates, key=lambda number: len(_encoded(documents[number])))
        result, flag = pdf_results[index]
        result.update(status='limit_exceeded', complete=False, pages=[], processed_pages=0)
        result['issues'].append({'code': 'context_byte_limit'})
        documents[index] = _pdf_document(files[index], result, '0' * 64)
    for index, (result, flag) in pdf_results.items():
        extraction_id = _retain(store, {'schema_version': 1, 'extraction_profile_id': profile_id,
                                        'result': result}, flag)
        documents[index] = _pdf_document(files[index], result, extraction_id)
    context_id = _retain(store, manifest, synthetic)
    prepared = {'context_id': context_id, 'extraction_profile_id': profile_id, 'documents': documents}
    if len(_encoded(prepared)) > MAX_CONTEXT_BYTES:
        raise ValueError('Analysis context exceeds byte limit')
    return prepared


def verify_analysis_documents(store, prepared, files, *, source_id, intake_id, revision, revision_fingerprint):
    """Recheck prepared immutable artifacts and current code without PDF parsing."""
    binding = _binding(files, source_id, intake_id, revision, revision_fingerprint)
    profile = _profile(); profile_id = _hash(_encoded(profile))
    if set(prepared) != {'context_id', 'extraction_profile_id', 'documents'} or prepared['extraction_profile_id'] != profile_id:
        raise ValueError('Analysis extraction profile changed')
    manifest = json.loads(store.verify_blob(prepared['context_id']).read_bytes())
    if manifest != {'schema_version': 1, 'binding': binding, 'profile': profile,
                     'extraction_profile_id': profile_id, 'documents': prepared['documents']}:
        raise ValueError('Analysis context changed')
    if len(files) != len(prepared['documents']):
        raise ValueError('Analysis documents changed')
    for item, document in zip(files, prepared['documents']):
        payload = store.verify_blob(item['sha256']).read_bytes()
        if len(payload) != item['bytes'] or _hash(payload) != item['sha256']:
            raise ValueError('Evidence changed during validation')
        if document.get('format') == 'pdf':
            artifact = json.loads(store.verify_blob(document['extraction_id']).read_bytes())
            if (artifact.get('schema_version') != 1 or artifact.get('extraction_profile_id') != profile_id
                    or _pdf_document(item, artifact['result'], document['extraction_id']) != document):
                raise ValueError('Retained page extraction changed')
    return True
