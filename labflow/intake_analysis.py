"""Validate cited analysis and project facts without defaulting product or market.

Source roles and semantic interpretation remain analyzer assertions. This checks
the data contract and literal citations, not the truth of an AI interpretation.
"""
import hashlib
from pathlib import Path

from .store import canonical

FIELDS = {
    'product_type': '제품 종류', 'customer': '고객', 'manufacturer': '제조사',
    'model': '모델', 'market': '의뢰 시장', 'purpose': '의뢰 목적',
    'features': '기능', 'antenna_gain': '안테나 이득', 'power_target': '출력 목표',
    'firmware': '펌웨어',
}
REQUIRED_FIELDS = {'product_type', 'market', 'purpose'}
TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.tsv', '.json'}
MAX_TEXT_BYTES = 256 * 1024


def document_context(store, files):
    documents = []
    remaining = 2 * 1024 * 1024
    for item in files:
        payload = store.verify_blob(item['sha256']).read_bytes()
        if hashlib.sha256(payload).hexdigest() != item['sha256']:
            raise ValueError('Evidence changed during analysis read')
        text = None
        if Path(item['path']).suffix.lower() in TEXT_SUFFIXES and len(payload) <= min(MAX_TEXT_BYTES, remaining):
            try:
                text = payload.decode('utf-8-sig')
                remaining -= len(payload)
            except UnicodeError:
                pass
        documents.append({**item, 'text': text, 'parse_status': 'text' if text is not None else 'requires_parser'})
    return documents


def _keys(value, allowed, label):
    if not isinstance(value, dict) or set(value) != set(allowed):
        raise ValueError('Invalid '+label+' fields')


def _text(value, label, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('Invalid '+label)


def validate_analysis(analysis, documents, synthetic):
    _keys(analysis, {'schema_version', 'producer', 'identity', 'facts', 'missing_fields'}, 'analysis')
    if type(analysis['schema_version']) is not int or analysis['schema_version'] != 1:
        raise ValueError('Unsupported analysis schema')
    _keys(analysis['producer'], {'kind', 'name'}, 'producer')
    producer = analysis['producer']
    if producer['kind'] not in {'model', 'manual', 'fixture'}:
        raise ValueError('Unknown analyzer kind')
    if producer['kind'] == 'fixture' and not synthetic:
        raise ValueError('Fixture analysis requires synthetic intake')
    _text(producer['name'], 'analyzer name', 200)
    if analysis['identity'] not in {'single', 'ambiguous', 'unknown'}:
        raise ValueError('Invalid product identity state')
    facts = analysis['facts']
    if not isinstance(facts, list) or len(facts) > 200:
        raise ValueError('Invalid facts list')
    missing = analysis['missing_fields']
    if not isinstance(missing, list) or not all(isinstance(f, str) and f in FIELDS for f in missing):
        raise ValueError('Invalid missing fields')
    by_path = {d['path']: d for d in documents}
    for fact in facts:
        _keys(fact, {'field', 'value', 'status', 'evidence'}, 'fact')
        if not isinstance(fact['field'], str) or fact['field'] not in FIELDS:
            raise ValueError('Unknown fact field')
        _text(fact['value'], 'fact value')
        if fact['status'] not in {'explicit', 'inferred', 'uncertain'}:
            raise ValueError('Unknown fact status')
        if not isinstance(fact['evidence'], list) or not 1 <= len(fact['evidence']) <= 20:
            raise ValueError('Facts require source evidence')
        for evidence in fact['evidence']:
            _keys(evidence, {'path', 'sha256', 'line_start', 'line_end', 'quote', 'role'}, 'citation')
            if not isinstance(evidence['path'], str):
                raise ValueError('Invalid source path')
            doc = by_path.get(evidence['path'])
            if doc is None or doc['sha256'] != evidence['sha256'] or doc['text'] is None:
                raise ValueError('Citation requires a parsed source in this revision')
            if evidence['role'] not in {'request', 'product', 'reference'}:
                raise ValueError('Invalid source role')
            first, last = evidence['line_start'], evidence['line_end']
            lines = doc['text'].splitlines()
            if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(lines):
                raise ValueError('Invalid citation line range')
            _text(evidence['quote'], 'citation quote', MAX_TEXT_BYTES)
            if evidence['quote'] not in '\n'.join(lines[first-1:last]):
                raise ValueError('Citation quote does not match retained source')
    canonical(analysis)
    return [d['path'] for d in documents if d['text'] is None]


def answer_basis(analysis, field):
    related = {field, 'model', 'manufacturer', 'product_type'}
    return canonical({'identity': analysis['identity'], 'facts': sorted(
        (f['field'], f['value'], f['status']) for f in analysis['facts'] if f['field'] in related)})


def project_analysis(analysis, unread, answers, *, delegated, deferred):
    facts, questions = {}, []
    required = REQUIRED_FIELDS | set(analysis['missing_fields'])
    for field, label in FIELDS.items():
        candidates = [f for f in analysis['facts'] if f['field'] == field and f['status'] != 'uncertain']
        if field in {'market', 'purpose'}:
            candidates = [f for f in candidates if f['status'] == 'explicit' and
                          all(e['role'] == 'request' for e in f['evidence'])]
        values = sorted({f['value'].strip() for f in candidates})
        answer = answers.get(field)
        if answer and answer['basis_json'] == answer_basis(analysis, field):
            facts[field] = {'value': answer['value'], 'status': 'user_confirmed', 'event_id': answer['event_id']}
        elif len(values) > 1:
            questions.append({'key': 'conflict_'+field, 'field': field, 'values': values,
                              'message': label+' 정보가 서로 다릅니다. 적용할 값을 확인해 주세요.'})
        elif values:
            facts[field] = {'value': values[0], 'status': 'explicit' if any(f['status'] == 'explicit' for f in candidates) else 'inferred'}
        elif field in required:
            questions.append({'key': 'missing_'+field, 'field': field, 'message': label+' 정보가 필요합니다.'})
    if analysis['identity'] != 'single':
        questions.append({'key': 'product_identity', 'message': '자료 묶음의 제품·의뢰 대상을 확인해야 합니다.'})
    if unread:
        questions.append({'key': 'unread_documents', 'paths': unread, 'message': '추가 문서 해석기가 필요한 파일이 있습니다.'})
    next_action = 'deferred' if deferred else 'needs_information' if questions else 'prepare_plan' if delegated else 'propose_start'
    return {'facts': facts, 'questions': questions, 'next_action': next_action,
            'measurement_support': 'unverified', 'verification': 'contract_only',
            'submitted': analysis, 'unread_documents': unread}


def notification_signature(summary):
    # A new revision or repeat analysis alone must not repeat the same proposal.
    values = {field: {'value': fact['value'], 'status': fact['status']} for field, fact in summary['facts'].items()}
    return hashlib.sha256(canonical({'facts': values, 'questions': summary['questions']}).encode('utf-8')).hexdigest()
