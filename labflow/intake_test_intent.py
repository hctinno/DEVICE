"""Review only supplied intake/literal evidence; never read, select or execute.

Text consistency is not source authenticity, currentness, or applicability.
"""
from datetime import date
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from .document_extract import page_citation
from .intake_analysis import FIELDS, validate_analysis

_INVALID = 'test_intent_invalid_input'
_LIMIT = 'test_intent_limit_exceeded'
_SOURCE = 'test_intent_source_error'
_CODES = {_INVALID, _LIMIT, _SOURCE}
_LIMITS = dict(max_input_bytes=41943040, max_context_bytes=6291456,
               max_analysis_bytes=2097152, max_projection_bytes=8388608,
               max_observation_bytes=12582912, max_proposal_bytes=65536,
               max_sources_bytes=8388608, max_output_bytes=2097152,
               max_depth=32, max_nodes=2000000, max_source_documents=8,
               max_candidates_per_field=2, max_refs_per_side=8, max_literal_chars=256,
               max_institution_scope_chars=128, max_edition_chars=256,
               max_workflow_scope_ids=20, max_questions=200)
_FALSE = ('projection_recomputed result_projection_reverified database_currentness_verified '
          'source_authenticity_verified normative_applicability_verified institution_scope_verified '
          'edition_currentness_verified model_execution_verified model_quality_verified '
          'query_release_authorized case_selection_authorized execution_authorized').split()
_CAPTURE_LIMITS = dict(result_json_bytes=8388608, analysis_context_bytes=4194304,
                       raw_manifest_bytes=4194304, source_file_bytes=16777216,
                       projection_json_bytes=8388608, state_category_json_bytes=8388608,
                       max_questions=10000, max_user_response_events=10000, max_answers=10,
                       snapshot_json_bytes=9437184, capture_json_bytes=12582912)
_CAPTURE_REASONS = set(('analysis_not_completed legacy_analysis no_pdf_context expected_revision_changed '
    'expected_result_changed analysis_not_ready profile_changed delegation_missing intake_deferred '
    'delegation_evidence_missing required_questions_open unread_documents source_provenance_unconfirmed '
    'preparation_not_ready').split())
_CAPTURE_FLAGS = ('database_snapshot_observed retained_analysis_verified live_projection_recomputed '
                  'preparation_bound source_integrity_observed operational_authority_granted '
                  'model_execution_verified evaluation_executed').split()
_PAGE_STATUSES = set('ok truncated empty image_only no_text error limit_exceeded'.split())
_PDF_STATUSES = set(('ok partial empty encrypted malformed_pdf parser_error parser_unavailable '
                     'image_only no_text limit_exceeded').split())
_SCOPES = {f'F{i:02d}' for i in range(1, 21)}
_FACT_STATUSES = {'explicit', 'inferred', 'uncertain', 'user_confirmed'}
_TEXT_DOC = set('path sha256 bytes text parse_status'.split())
_PDF_DOC = _TEXT_DOC | set('format extraction_id parser limits pages issues complete total_pages processed_pages'.split())


class IntakeTestIntentError(ValueError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _INVALID
        super().__init__(self.code)


def _fail(code=_INVALID):
    raise IntakeTestIntentError(code)


def _dump(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, OverflowError):
        _fail(_LIMIT)


def _hash(value):
    return hashlib.sha256(_dump(value)).hexdigest()


def _plain(value):
    """Count every occurrence, with path-local cycle detection and bounded depth."""
    active, nodes = set(), 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > _LIMITS['max_nodes'] or depth > _LIMITS['max_depth']:
            _fail(_LIMIT)
        kind = type(item)
        if kind is dict or kind is list:
            identity = id(item)
            if identity in active:
                _fail()
            active.add(identity)
            if kind is dict:
                if any(type(key) is not str for key in item):
                    _fail()
                for key in sorted(item):
                    visit(key, depth + 1)
                    visit(item[key], depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
            active.remove(identity)
        elif kind is str:
            if len(item) > _LIMITS['max_input_bytes']:
                _fail(_LIMIT)
            try:
                item.encode('utf-8')
            except UnicodeError:
                _fail()
        elif kind is float:
            if not math.isfinite(item):
                _fail()
        elif kind not in (int, bool, type(None)):
            _fail()

    visit(value, 0)


def _keys(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        _fail()


def _text(value, maximum=None, *, nonempty=False, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or (nonempty and not value.strip()):
        _fail()
    if maximum is not None and len(value) > maximum:
        _fail(_LIMIT)


def _choice(value, choices):
    if type(value) is not str or value not in choices:
        _fail()


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        _fail()


def _boolean(value):
    if type(value) is not bool:
        _fail()


def _constant(value, expected):
    if type(value) is not type(expected) or value != expected:
        _fail()


def _identifier(value, maximum=150, *, nullable=False):
    if nullable and value is None:
        return
    _text(value, maximum)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value, re.ASCII):
        _fail()


def _sha(value, *, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value, re.ASCII):
        _fail()


def _array(value, maximum=None, minimum=0):
    if type(value) is not list or len(value) < minimum:
        _fail()
    if maximum is not None and len(value) > maximum:
        _fail(_LIMIT)


def _unique(items):
    if len({_dump(item) for item in items}) != len(items):
        _fail()


def _relative(value):
    _text(value, nonempty=True)
    if ('\\' in value or ':' in value or PurePosixPath(value).is_absolute()
            or any(part in {'', '.', '..'} for part in value.split('/'))):
        _fail()


def _date(value):
    if value is not None:
        if type(value) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value, re.ASCII):
            _fail()
        try:
            date.fromisoformat(value)
        except ValueError:
            _fail()


def _parser(value):
    _keys(value, {'name', 'version'})
    _text(value['name'])
    _text(value['version'], nullable=True)


def _pages(pages):
    _array(pages)
    numbers = set()
    for page in pages:
        _keys(page, {'page_number', 'status', 'text', 'text_sha256', 'line_spans'})
        _integer(page['page_number'], 1)
        if page['page_number'] in numbers:
            _fail()
        numbers.add(page['page_number'])
        _choice(page['status'], _PAGE_STATUSES)
        _text(page['text'])
        _sha(page['text_sha256'])
        _array(page['line_spans'])
        for span in page['line_spans']:
            _keys(span, {'line_number', 'start', 'end'})
            for number in span.values():
                _integer(number)


def _issues(issues):
    _array(issues)
    for issue in issues:
        _keys(issue, {'code'}, {'page_number'})
        _identifier(issue['code'])
        if 'page_number' in issue:
            _integer(issue['page_number'], 1)


def _context(context):
    _keys(context, {'job_id', 'intake_id', 'revision', 'synthetic', 'documents', 'analysis_contract', 'instructions'}, {'analysis_context_id'})
    _identifier(context['job_id']); _identifier(context['intake_id'])
    _integer(context['revision'], 1); _boolean(context['synthetic']); _text(context['instructions'])
    if 'analysis_context_id' in context:
        _sha(context['analysis_context_id'])
    _array(context['documents'], minimum=1)
    paths, pdf = set(), False
    for doc in context['documents']:
        if type(doc) is not dict:
            _fail()
        _relative(doc.get('path'))
        if doc['path'] in paths:
            _fail()
        paths.add(doc['path'])
        _sha(doc.get('sha256')); _integer(doc.get('bytes'))
        if doc.get('format') == 'pdf':
            pdf = True
            _keys(doc, _PDF_DOC)
            _constant(doc['text'], None); _choice(doc['parse_status'], _PDF_STATUSES)
            _sha(doc['extraction_id']); _boolean(doc['complete']); _parser(doc['parser'])
            _keys(doc['limits'], {'max_input_bytes', 'max_pages', 'max_output_chars', 'max_page_content_bytes'})
            for number in doc['limits'].values():
                _integer(number, 1)
            if doc['total_pages'] is not None:
                _integer(doc['total_pages'])
            _integer(doc['processed_pages']); _issues(doc['issues']); _pages(doc['pages'])
        else:
            if set(doc) != _TEXT_DOC:
                _keys(doc, _TEXT_DOC | {'format', 'extraction_status', 'issues'})
                _choice(doc['format'], {'text', 'unsupported'})
                _text(doc['extraction_status']); _issues(doc['issues'])
            if PurePosixPath(doc['path']).suffix.lower() == '.pdf':
                _fail()
            _text(doc['text'], nullable=True); _choice(doc['parse_status'], {'text', 'requires_parser'})
    contract = context['analysis_contract']
    version = 2 if pdf else 1
    _keys(contract, {'schema_version', 'producer', 'identity', 'missing_fields', 'facts'}, {'context_id'} if pdf else ())
    _constant(contract['schema_version'], version)
    if pdf:
        _sha(context.get('analysis_context_id')); _sha(contract.get('context_id'))
        _constant(contract['context_id'], context['analysis_context_id'])
    _keys(contract['producer'], {'kind', 'name'})
    for value in contract['producer'].values():
        _text(value)
    _text(contract['identity']); _array(contract['missing_fields']); _array(contract['facts'])
    if any(type(name) is not str or name not in FIELDS for name in contract['missing_fields']):
        _fail()
    for fact in contract['facts']:
        _keys(fact, {'field', 'value', 'status', 'evidence'})
        for key in ('field', 'value', 'status'):
            _text(fact[key])
        _array(fact['evidence'])
        for ref in fact['evidence']:
            keys = {'path', 'sha256', 'line_start', 'line_end', 'quote', 'role'}
            if version == 2:
                keys |= {'kind'}
                if type(ref) is dict and ref.get('kind') == 'pdf_page':
                    keys |= {'extraction_id', 'page_number', 'text_sha256'}
            _keys(ref, keys)
            for value in ref.values():
                _text(value)
            _relative(ref['path'])


def _analysis(analysis):
    if type(analysis) is not dict:
        _fail()
    version = analysis.get('schema_version')
    if type(version) is not int or version not in (1, 2):
        _fail()
    _keys(analysis, {'schema_version', 'producer', 'identity', 'facts', 'missing_fields'} | ({'context_id'} if version == 2 else set()))
    if version == 2:
        _sha(analysis['context_id'])
    _keys(analysis['producer'], {'kind', 'name'})
    _choice(analysis['producer']['kind'], {'model', 'manual', 'fixture'})
    _text(analysis['producer']['name'], 200, nonempty=True)
    _choice(analysis['identity'], {'single', 'ambiguous', 'unknown'})
    _array(analysis['missing_fields'])
    if any(type(field) is not str or field not in FIELDS for field in analysis['missing_fields']):
        _fail()
    _array(analysis['facts'], 200)
    for fact in analysis['facts']:
        _keys(fact, {'field', 'value', 'status', 'evidence'})
        _choice(fact['field'], FIELDS); _text(fact['value'], 4000, nonempty=True)
        _choice(fact['status'], {'explicit', 'inferred', 'uncertain'}); _array(fact['evidence'], 20, 1)
        for ref in fact['evidence']:
            keys = {'path', 'sha256', 'line_start', 'line_end', 'quote', 'role'}
            if version == 2:
                if type(ref) is not dict:
                    _fail()
                _choice(ref.get('kind'), {'text_line', 'pdf_page'})
                keys |= {'kind'}
                if ref['kind'] == 'pdf_page':
                    keys |= {'extraction_id', 'page_number', 'text_sha256'}
            _keys(ref, keys)
            _relative(ref['path']); _sha(ref['sha256'])
            _integer(ref['line_start'], 1); _integer(ref['line_end'], 1)
            _text(ref['quote'], 262144, nonempty=True); _choice(ref['role'], {'request', 'product', 'reference'})
            if ref.get('kind') == 'pdf_page':
                _sha(ref['extraction_id']); _sha(ref['text_sha256']); _integer(ref['page_number'], 1)


def _fact(fact, event_max=150):
    _keys(fact, {'value', 'status'}, {'event_id'})
    _text(fact['value'], 4000, nonempty=True); _choice(fact['status'], _FACT_STATUSES)
    if fact['status'] == 'user_confirmed' and 'event_id' not in fact:
        _fail()
    if 'event_id' in fact:
        if type(fact['event_id']) is int:
            _integer(fact['event_id'], 1)
        else:
            _identifier(fact['event_id'], event_max)


def _projection(projection):
    _keys(projection, {'facts','questions','next_action','measurement_support','verification','submitted','unread_documents'}, {'intake_id','revision'})
    if 'intake_id' in projection:
        _identifier(projection['intake_id'], nullable=True)
    if projection.get('revision') is not None:
        _integer(projection['revision'], 1)
    _choice(projection['next_action'], {'deferred','needs_information','prepare_plan','propose_start'})
    _constant(projection['measurement_support'], 'unverified'); _constant(projection['verification'], 'contract_only')
    _analysis(projection['submitted'])
    _keys(projection['facts'], (), FIELDS)
    for fact in projection['facts'].values():
        _fact(fact)
    _array(projection['unread_documents'])
    for path in projection['unread_documents']:
        _relative(path)
    _array(projection['questions'], 200)
    for q in projection['questions']:
        if type(q) is not dict:
            _fail()
        key = q.get('key')
        _text(key)
        if key == 'product_identity':
            _keys(q, {'key','message'})
        elif key == 'unread_documents':
            _keys(q, {'key','paths','message'}); _array(q['paths'])
            for path in q['paths']:
                _relative(path)
        else:
            conflict = key.startswith('conflict_')
            _keys(q, {'key','field','message'} | ({'values'} if conflict else set()))
            _choice(q['field'], FIELDS)
            _constant(key, ('conflict_' if conflict else 'missing_') + q['field'])
            if conflict:
                _array(q['values'], 200, 2)
                for value in q['values']:
                    _text(value, 4000, nonempty=True)
        _text(q['message'])


def _capture_reasons(value):
    _array(value); _unique(value)
    for reason in value:
        _choice(reason, _CAPTURE_REASONS)


def _observation(obs):
    if obs is None:
        return
    _keys(obs, {'schema_version','kind','status','reason_codes','snapshot_id','snapshot','origin','state',
                'delegation','profile','readiness','verification','limits'})
    _constant(obs['schema_version'], 1); _constant(obs['kind'], 'intake_reference_snapshot_capture')
    _choice(obs['status'], {'observed','stale','unavailable'}); _capture_reasons(obs['reason_codes'])
    unavailable = obs['status'] == 'unavailable'
    origin_keys = {'source_id','origin_job_id','result_sha256','analysis_context_id','raw_manifest_sha256'}
    state_keys = {'intake_status','delegated','deferred','projection_sha256','answers_sha256','questions_sha256'}
    _keys(obs['origin'], origin_keys); _keys(obs['state'], state_keys)
    _keys(obs['delegation'], {'event_id','history_sha256','verified'})
    _keys(obs['profile'], {'stored_profile_id','current_profile_id','matches'})
    _keys(obs['readiness'], {'kind','ready','reason_codes','reference_state_fingerprint','delegation_event_id'})
    _keys(obs['verification'], _CAPTURE_FLAGS)
    for value in obs['verification'].values():
        _boolean(value)
    _keys(obs['limits'], _CAPTURE_LIMITS)
    for key, value in obs['limits'].items():
        _constant(value, _CAPTURE_LIMITS[key])
    _constant(obs['readiness']['kind'], 'reference_preparation_v1'); _capture_reasons(obs['readiness']['reason_codes'])
    _sha(obs['profile']['current_profile_id'])
    if unavailable:
        _constant(obs['snapshot_id'], None); _constant(obs['snapshot'], None)
        for value in [*obs['origin'].values(), *obs['state'].values(), *obs['delegation'].values(),
                      obs['profile']['stored_profile_id'], obs['profile']['matches'],
                      obs['readiness']['reference_state_fingerprint'], obs['readiness']['delegation_event_id']]:
            _constant(value, None)
        _constant(obs['readiness']['ready'], False)
        return
    _sha(obs['snapshot_id'])
    for key in origin_keys:
        (_identifier if key in {'source_id','origin_job_id'} else _sha)(obs['origin'][key])
    _text(obs['state']['intake_status'], 150, nonempty=True)
    for key in ('delegated','deferred'):
        _boolean(obs['state'][key])
    for key in ('projection_sha256','answers_sha256','questions_sha256'):
        _sha(obs['state'][key])
    _identifier(obs['delegation']['event_id'], nullable=True); _sha(obs['delegation']['history_sha256'])
    _boolean(obs['delegation']['verified']); _sha(obs['profile']['stored_profile_id']); _boolean(obs['profile']['matches'])
    _boolean(obs['readiness']['ready']); _sha(obs['readiness']['reference_state_fingerprint'])
    _identifier(obs['readiness']['delegation_event_id'], nullable=True)
    s = obs['snapshot']
    _keys(s, {'schema_version','kind','snapshot_scope','intake_id','revision','revision_fingerprint','origin_job_id',
              'analysis_context_id','result_sha256','readiness_fingerprint','synthetic','projection','projection_sha256'})
    _constant(s['schema_version'], 1); _constant(s['kind'], 'intake_case_reference_snapshot')
    _constant(s['snapshot_scope'], 'caller_provided'); _identifier(s['intake_id']); _identifier(s['origin_job_id'])
    _integer(s['revision'], 1); _boolean(s['synthetic'])
    for key in ('revision_fingerprint','analysis_context_id','result_sha256','readiness_fingerprint','projection_sha256'):
        _sha(s[key])
    _keys(s['projection'], {'facts','questions'}); _keys(s['projection']['facts'], (), {'product_type','market','model'})
    for fact in s['projection']['facts'].values():
        _fact(fact, 128)
    _array(s['projection']['questions'], 200)
    for q in s['projection']['questions']:
        _keys(q, {'key'}); _text(q['key'], 1048576)


def _proposal_sources(proposal, sources):
    _keys(proposal, {'as_of','institution_scope','workflow_scope_id','fields'})
    _date(proposal['as_of']); _text(proposal['institution_scope'], 128, nonempty=True, nullable=True)
    if proposal['workflow_scope_id'] is not None:
        _choice(proposal['workflow_scope_id'], _SCOPES)
    _keys(proposal['fields'], {'rule','method'})
    for candidates in proposal['fields'].values():
        _array(candidates, 2); _unique(candidates)
        for candidate in candidates:
            _keys(candidate, {'literal','origin','intake_refs','basis_refs'})
            _text(candidate['literal'], 256, nonempty=True); _choice(candidate['origin'], {'explicit_supplied','model_proposed'})
            for side in ('intake_refs','basis_refs'):
                _array(candidate[side], 8); _unique(candidate[side])
            for ref in candidate['intake_refs']:
                _keys(ref, {'fact_index','evidence_index'})
                _integer(ref['fact_index']); _integer(ref['evidence_index'])
            for ref in candidate['basis_refs']:
                _keys(ref, {'document_id','page_number','text_sha256','line_start','line_end'})
                _identifier(ref['document_id'], 128); _sha(ref['text_sha256'])
                for key in ('page_number','line_start','line_end'):
                    _integer(ref[key], 1)
                if ref['line_start'] > ref['line_end']:
                    _fail()
    _array(sources, 8)
    ids = set()
    for source in sources:
        _keys(source, {'document_id','source_kind','representation','artifact_sha256','institution_scope','workflow_scope_ids',
                       'edition','effective_from','effective_to','review_status','rights_status','extraction'})
        _identifier(source['document_id'], 128)
        if source['document_id'] in ids:
            _fail()
        ids.add(source['document_id'])
        _choice(source['source_kind'], {'regulation','guidance','standard','manufacturer','report','unknown'})
        _choice(source['representation'], {'original','extract','metadata','unknown'})
        _choice(source['review_status'], {'reviewed','unreviewed','unknown'})
        _choice(source['rights_status'], {'usable','restricted','unknown'})
        _sha(source['artifact_sha256'], nullable=True); _text(source['institution_scope'], 128, nonempty=True, nullable=True)
        _text(source['edition'], 256, nonempty=True, nullable=True); _date(source['effective_from']); _date(source['effective_to'])
        _array(source['workflow_scope_ids'], 20); _unique(source['workflow_scope_ids'])
        for scope in source['workflow_scope_ids']:
            _choice(scope, _SCOPES)
        extraction = source['extraction']
        if extraction is not None:
            _keys(extraction, {'schema_version','status','source','parser','pages'},
                  set(extraction) if type(extraction) is dict else ())
            _constant(extraction['schema_version'], 1); _text(extraction['status'])
            _keys(extraction['source'], {'filename','sha256'},
                  set(extraction['source']) if type(extraction['source']) is dict else ())
            _text(extraction['source']['filename'], nonempty=True); _sha(extraction['source']['sha256'])
            _parser(extraction['parser']); _pages(extraction['pages'])


def _minimal(projection):
    return {'facts': {k: v for k, v in projection['facts'].items() if k in {'product_type','market','model'}},
            'questions': [{'key': q['key']} for q in projection['questions']]}


def _binding(intake):
    c, a, p, obs = (intake[k] for k in ('context','analysis','projection','observation'))
    reasons = set()
    complete = all(p.get(k) is not None for k in ('intake_id','revision'))
    if not complete:
        reasons.add('intake_binding_incomplete')
    for key in ('intake_id','revision'):
        if p.get(key) is not None and p[key] != c[key]:
            reasons.add('intake_binding_mismatch')
    if _dump(p['submitted']) != _dump(a):
        reasons.add('intake_binding_mismatch')
    if p['questions']:
        reasons.add('intake_questions_open')
    if obs is None or obs['status'] == 'unavailable':
        reasons.add('intake_binding_incomplete')
        return reasons
    if obs['status'] == 'stale':
        reasons.add('intake_binding_incomplete')
    s = obs['snapshot']
    if a['schema_version'] == 1:
        reasons.add('intake_binding_mismatch')
    for ck, sk in [('job_id','origin_job_id'), ('intake_id','intake_id'), ('revision','revision'),
                   ('synthetic','synthetic'), ('analysis_context_id','analysis_context_id')]:
        if c.get(ck) is None:
            reasons.add('intake_binding_incomplete')
        elif c[ck] != s[sk]:
            reasons.add('intake_binding_mismatch')
    for key in ('origin_job_id','analysis_context_id','result_sha256'):
        if s[key] != obs['origin'][key]:
            reasons.add('intake_binding_mismatch')
    if s['readiness_fingerprint'] != obs['readiness']['reference_state_fingerprint']:
        reasons.add('intake_binding_mismatch')
    minimal = _minimal(p)
    if (complete and _hash(p) != obs['state']['projection_sha256']
            or _dump(minimal) != _dump(s['projection']) or _hash(minimal) != s['projection_sha256']):
        reasons.add('intake_binding_mismatch')
    return reasons


def _period(as_of, source):
    start, end = source['effective_from'], source['effective_to']
    if start is not None and end is not None and start > end:
        return 'conflicting', 'period_conflicting'
    if as_of is None:
        return 'unconfirmed', 'period_unconfirmed'
    if start is not None and as_of < start or end is not None and as_of > end:
        return 'outside_declared_window', 'period_outside_declared_window'
    if start is None or end is None:
        return 'unconfirmed', 'period_unconfirmed'
    return 'in_declared_window', None


def _metadata(proposal, source):
    reasons = {'edition_unconfirmed'}
    if source['source_kind'] in {'report','manufacturer','unknown'}:
        reasons.add('source_not_normative')
    if (source['representation'] != 'original' or source['review_status'] != 'reviewed'
            or source['rights_status'] != 'usable' or not source['workflow_scope_ids']):
        reasons.add('source_status_unconfirmed')
    p_scope, s_scope = proposal['institution_scope'], source['institution_scope']
    if p_scope is None or s_scope is None:
        reasons.add('institution_scope_unconfirmed')
    elif p_scope != s_scope:
        reasons.add('scope_conflicting')
    if (proposal['workflow_scope_id'] is not None and source['workflow_scope_ids']
            and proposal['workflow_scope_id'] not in source['workflow_scope_ids']):
        reasons.add('scope_conflicting')
    period, reason = _period(proposal['as_of'], source)
    if reason:
        reasons.add(reason)
    return period, reasons


def _parent(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception:
        _fail(_SOURCE)


def _build(intake, proposal, sources):
    packet = {'intake': intake, 'proposal': proposal, 'sources': sources}
    _plain(packet)
    encoded = _dump(packet)
    if len(encoded) > _LIMITS['max_input_bytes']:
        _fail(_LIMIT)
    if type(intake) is dict:
        for key in ('context','analysis','projection','observation'):
            if key in intake and len(_dump(intake[key])) > _LIMITS['max_' + key + '_bytes']:
                _fail(_LIMIT)
    for key, value in [('proposal', proposal), ('sources', sources)]:
        if len(_dump(value)) > _LIMITS['max_' + key + '_bytes']:
            _fail(_LIMIT)
    _keys(intake, {'context','analysis','projection','observation'})
    packet = json.loads(encoded)
    intake, proposal, sources = (packet[k] for k in ('intake','proposal','sources'))
    _context(intake['context']); _analysis(intake['analysis']); _projection(intake['projection'])
    _observation(intake['observation']); _proposal_sources(proposal, sources)
    c, a, p, obs = (intake[k] for k in ('context','analysis','projection','observation'))
    if a['schema_version'] == 2:
        _sha(c.get('analysis_context_id'))
    by_id = {s['document_id']: s for s in sources}
    all_candidates = [candidate for field in ('rule','method') for candidate in proposal['fields'][field]]
    for candidate in all_candidates:
        for ref in candidate['intake_refs']:
            if ref['fact_index'] >= len(a['facts']) or ref['evidence_index'] >= len(a['facts'][ref['fact_index']]['evidence']):
                _fail()
        if any(ref['document_id'] not in by_id for ref in candidate['basis_refs']):
            _fail()
    reasons = _binding(intake)
    mismatch = 'intake_binding_mismatch' in reasons
    _parent(validate_analysis, a, c['documents'], c['synthetic'], context_id=c.get('analysis_context_id'))
    fields, basis_checks = {}, []
    for field in ('rule','method'):
        candidates, field_reasons = [], set()
        for candidate in proposal['fields'][field]:
            why, literal = set(), candidate['literal']
            intake_link = bool(candidate['intake_refs'])
            basis_link = bool(candidate['basis_refs'])
            if not intake_link:
                why.add('intake_ground_missing')
            if not basis_link:
                why.add('basis_missing')
            for ref in candidate['intake_refs']:
                fact = a['facts'][ref['fact_index']]
                evidence = fact['evidence'][ref['evidence_index']]
                if fact['status'] != 'explicit' or evidence['role'] != 'request':
                    intake_link = False; why.add('intake_ground_missing')
                if literal not in evidence['quote']:
                    intake_link = False; why.add('literal_not_in_citation')
            for ref in candidate['basis_refs']:
                source = by_id[ref['document_id']]
                if source['extraction'] is None or source['artifact_sha256'] is None:
                    basis_checks.append(False); basis_link = False; why.add('basis_missing')
                    continue
                citation = _parent(page_citation, source['extraction'], ref['page_number'], ref['line_start'], ref['line_end'])
                if citation['source_sha256'] != source['artifact_sha256'] or citation['text_sha256'] != ref['text_sha256']:
                    _fail(_SOURCE)
                basis_checks.append(True)
                if literal not in citation['quote']:
                    basis_link = False; why.add('literal_not_in_citation')
            periods = []
            for document_id in sorted({ref['document_id'] for ref in candidate['basis_refs']}):
                period, metadata_reasons = _metadata(proposal, by_id[document_id])
                periods.append({'document_id': document_id, 'status': period})
                why.update(metadata_reasons)
            if mismatch:
                why.add('intake_binding_mismatch')
            candidates.append({**candidate, 'literal_linked': intake_link and basis_link and not mismatch,
                               'period_checks': periods, 'reason_codes': sorted(why)})
            field_reasons.update(why)
        if not candidates:
            status = 'missing'; field_reasons.add('intent_missing')
        elif len({candidate['literal'] for candidate in candidates}) > 1:
            status = 'conflicting'; field_reasons.add('intent_conflicting')
        else:
            status = 'literal_linked' if all(candidate['literal_linked'] for candidate in candidates) else 'proposed'
        fields[field] = {'status': status, 'candidates': candidates, 'reason_codes': sorted(field_reasons)}
        reasons.update(field_reasons)
    reasons.add('applicability_not_assessed')
    binding = {'intake_id': c['intake_id'], 'revision': c['revision'], 'analysis_context_id': c.get('analysis_context_id'),
               'result_sha256': obs['origin']['result_sha256'] if obs is not None else None,
               'observation_snapshot_id': obs['snapshot_id'] if obs is not None else None,
               **{'provided_' + key + '_sha256': _hash(intake[key]) for key in ('context','analysis','projection')},
               'provided_proposal_sha256': _hash(proposal), 'provided_sources_sha256': _hash(sources),
               'provided_observation_sha256': _hash(obs) if obs is not None else None}
    output = {'schema_version': 1, 'kind': 'intake_test_intent_review', 'status': 'review_only',
              'input_binding': binding, 'fields': fields, 'questions': p['questions'], 'reason_codes': sorted(reasons),
              'verification': {**dict.fromkeys(_FALSE, False),
                               'intake_citations_checked': any(candidate['intake_refs'] for candidate in all_candidates),
                               'basis_literals_checked': bool(basis_checks) and all(basis_checks)},
              'limits': dict(_LIMITS)}
    _plain(output)
    if len(_dump(output)) > _LIMITS['max_output_bytes']:
        _fail(_LIMIT)
    return output


def build_intake_test_intent_review(intake, proposal, sources):
    """Return supplied-evidence review only; fixed errors never carry source text."""
    try:
        return _build(intake, proposal, sources)
    except IntakeTestIntentError as error:
        code = error.code
    except Exception:
        code = _INVALID
    raise IntakeTestIntentError(code) from None
