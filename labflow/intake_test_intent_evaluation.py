"""Pure provided-input contract checks; no model, I/O or authority approval."""
import hashlib
import json
import math
import re

from .intake_test_intent import IntakeTestIntentError, build_intake_test_intent_review


_LIMITS = dict(max_input_bytes=48*1024*1024, max_expectation_bytes=256*1024,
               max_output_bytes=256*1024, max_depth=40, max_nodes=2100000,
               max_id_chars=128, max_reason_chars=128, max_reason_codes=512)
_PARENT_LIMITS = dict(max_input_bytes=41943040, max_context_bytes=6291456,
    max_analysis_bytes=2097152, max_projection_bytes=8388608, max_observation_bytes=12582912,
    max_proposal_bytes=65536, max_sources_bytes=8388608, max_output_bytes=2097152,
    max_depth=32, max_nodes=2000000, max_source_documents=8, max_candidates_per_field=2,
    max_refs_per_side=8, max_literal_chars=256, max_institution_scope_chars=128,
    max_edition_chars=256, max_workflow_scope_ids=20, max_questions=200)
_FALSE = set(('projection_recomputed result_projection_reverified database_currentness_verified '
    'source_authenticity_verified normative_applicability_verified institution_scope_verified '
    'edition_currentness_verified model_execution_verified model_quality_verified '
    'query_release_authorized case_selection_authorized execution_authorized').split())
_CALCULATIONS = {'intake_citations_checked', 'basis_literals_checked'}
_FIELDS = {'rule', 'method'}
_SOURCE_KEYS = {'literal', 'origin', 'intake_refs', 'basis_refs'}
_PARENT_ERRORS = {'test_intent_invalid_input', 'test_intent_limit_exceeded', 'test_intent_source_error'}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
_SHA = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
_PREFIX = 'intake_test_intent_evaluation_'


class IntakeTestIntentEvaluationError(ValueError):
    def __init__(self, code):
        suffix = code.removeprefix(_PREFIX) if type(code) is str else 'invalid_input'
        self.code = _PREFIX + (suffix if suffix in {'invalid_input','limit_exceeded','source_error'} else 'invalid_input')
        super().__init__(self.code)


def _fail(code='invalid_input'):
    raise IntakeTestIntentEvaluationError(code)


def _dump(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        _fail()


def _hash(value):
    return hashlib.sha256(_dump(value)).hexdigest()


def _copy(value, limit, nodes):
    """Account for exact compact JSON bytes before any semantic validation."""
    used, active = 0, set()
    def consume(amount):
        nonlocal used
        used += amount
        if used > limit:
            _fail('limit_exceeded')
    def walk(item, depth):
        nodes[0] += 1
        if nodes[0] > _LIMITS['max_nodes'] or depth > _LIMITS['max_depth']:
            _fail('limit_exceeded')
        kind = type(item)
        if kind is dict or kind is list:
            identity = id(item)
            if identity in active:
                _fail()
            active.add(identity)
            consume(2 + max(0, len(item)-1) + (len(item) if kind is dict else 0))
            try:
                if kind is dict:
                    for key, child in item.items():
                        if type(key) is not str:
                            _fail()
                        walk(key, depth+1)
                        walk(child, depth+1)
                else:
                    for child in item:
                        walk(child, depth+1)
            finally:
                active.remove(identity)
        elif item is None or kind is str or kind is int or kind is bool or kind is float and math.isfinite(item):
            consume(len(_dump(item)))
        else:
            _fail()
    walk(value, 0)
    encoded = _dump(value)
    if len(encoded) > limit:
        _fail('limit_exceeded')
    return json.loads(encoded), encoded


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _fail()


def _choice(value, choices):
    if type(value) is not str or value not in choices:
        _fail()


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        _fail()


def _reasons(value):
    if type(value) is not list:
        _fail()
    if len(value) > _LIMITS['max_reason_codes']:
        _fail('limit_exceeded')
    for reason in value:
        if type(reason) is not str or not reason.strip():
            _fail()
        if len(reason) > _LIMITS['max_reason_chars']:
            _fail('limit_exceeded')
    if value != sorted(set(value)):
        _fail()


def _review_summary(review):
    _keys(review, {'fields','reason_codes','calculation_flags'})
    _keys(review['fields'], _FIELDS)
    _reasons(review['reason_codes'])
    _keys(review['calculation_flags'], _CALCULATIONS)
    if any(type(flag) is not bool for flag in review['calculation_flags'].values()):
        _fail()
    for row in review['fields'].values():
        _keys(row, {'status','candidates','reason_codes'})
        _choice(row['status'], {'missing','proposed','literal_linked','conflicting'})
        _reasons(row['reason_codes'])
        if type(row['candidates']) is not list or len(row['candidates']) > 2:
            _fail()
        for candidate in row['candidates']:
            _keys(candidate, {'literal_linked','period_checks','reason_codes'})
            if type(candidate['literal_linked']) is not bool:
                _fail()
            _reasons(candidate['reason_codes'])
            periods = candidate['period_checks']
            if type(periods) is not list or len(periods) > 8:
                _fail()
            ids = []
            for period in periods:
                _keys(period, {'document_id','status'})
                _id(period['document_id'])
                _choice(period['status'], {'conflicting','unconfirmed','outside_declared_window','in_declared_window'})
                ids.append(period['document_id'])
            if ids != sorted(set(ids)):
                _fail()


def _expectation(value, packet):
    _keys(value, {'schema_version','kind','case_id','case_group_id','input_sha256','label_review_status','expected'})
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        _fail()
    _choice(value['kind'], {'intake_test_intent_case_expectation'})
    _id(value['case_id']); _id(value['case_group_id'])
    if type(value['input_sha256']) is not str or not _SHA.fullmatch(value['input_sha256']):
        _fail()
    _choice(value['label_review_status'], {'pending','reviewed'})
    expected = value['expected']
    if value['label_review_status'] == 'pending':
        if expected is not None:
            _fail()
        return
    _keys(expected, {'outcome','error_code','review'})
    _choice(expected['outcome'], {'returned','error'})
    if expected['outcome'] == 'error':
        _choice(expected['error_code'], _PARENT_ERRORS)
        if expected['review'] is not None:
            _fail()
    else:
        if expected['error_code'] is not None:
            _fail()
        _review_summary(expected['review'])
        try:
            for name in _FIELDS:
                if type(packet['proposal']['fields'][name]) is not list or len(expected['review']['fields'][name]['candidates']) != len(packet['proposal']['fields'][name]):
                    _fail()
        except (KeyError, TypeError):
            _fail()


def _binding(intake, proposal, sources):
    context, obs = intake['context'], intake['observation']
    return dict(intake_id=context['intake_id'], revision=context['revision'],
        analysis_context_id=context.get('analysis_context_id'),
        result_sha256=obs['origin']['result_sha256'] if obs is not None else None,
        observation_snapshot_id=obs['snapshot_id'] if obs is not None else None,
        **{'provided_'+key+'_sha256':_hash(intake[key]) for key in ('context','analysis','projection')},
        provided_proposal_sha256=_hash(proposal), provided_sources_sha256=_hash(sources),
        provided_observation_sha256=_hash(obs) if obs is not None else None)


def _matches(review, packet, expected):
    """Check public invariants independently of parent private helpers/constants."""
    try:
        _keys(review, {'schema_version','kind','status','input_binding','fields','questions','reason_codes','verification','limits'})
        if type(review['schema_version']) is not int or review['schema_version'] != 1:
            return False
        if review['kind'] != 'intake_test_intent_review' or review['status'] != 'review_only':
            return False
        if _dump(review['limits']) != _dump(_PARENT_LIMITS):
            return False
        _keys(review['verification'], _FALSE | _CALCULATIONS)
        if any(type(v) is not bool for v in review['verification'].values()):
            return False
        if any(review['verification'][key] is not False for key in _FALSE):
            return False
        if _dump(review['input_binding']) != _dump(_binding(**packet)):
            return False
        if _dump(review['questions']) != _dump(packet['intake']['projection']['questions']):
            return False
        _keys(review['fields'], _FIELDS)
        summary = dict(fields={}, reason_codes=review['reason_codes'],
                       calculation_flags={key:review['verification'][key] for key in _CALCULATIONS})
        for name in _FIELDS:
            row = review['fields'][name]
            _keys(row, {'status','candidates','reason_codes'})
            original = packet['proposal']['fields'][name]
            if type(row['candidates']) is not list or len(row['candidates']) != len(original):
                return False
            candidates = []
            for candidate, supplied in zip(row['candidates'], original):
                _keys(candidate, _SOURCE_KEYS | {'literal_linked','period_checks','reason_codes'})
                if _dump({key:candidate[key] for key in _SOURCE_KEYS}) != _dump(supplied):
                    return False
                candidates.append({key:candidate[key] for key in ('literal_linked','period_checks','reason_codes')})
            summary['fields'][name] = dict(status=row['status'], candidates=candidates, reason_codes=row['reason_codes'])
        _review_summary(summary)
        return _dump(summary) == _dump(expected)
    except (IntakeTestIntentEvaluationError, KeyError, TypeError, ValueError):
        return False


def _declarations(packet):
    context = packet['intake'].get('context') if type(packet['intake']) is dict else None
    synthetic = context.get('synthetic') if type(context) is dict else None
    if type(synthetic) is not bool:
        synthetic = None
    origins = None
    proposal = packet['proposal']
    if type(proposal) is dict and type(proposal.get('fields')) is dict and set(proposal['fields']) == _FIELDS:
        rows = [proposal['fields'][name] for name in _FIELDS]
        if all(type(row) is list for row in rows):
            candidates = [candidate for row in rows for candidate in row]
            if all(type(c) is dict and type(c.get('origin')) is str and c['origin'] in {'explicit_supplied','model_proposed'} for c in candidates):
                origins = sorted({c['origin'] for c in candidates})
    return dict(context_synthetic=synthetic, proposal_origins=origins)


def _evaluate(intake, proposal, sources, expectation):
    nodes = [0]
    packet, encoded = _copy(dict(intake=intake, proposal=proposal, sources=sources), _LIMITS['max_input_bytes'], nodes)
    expectation, _ = _copy(expectation, _LIMITS['max_expectation_bytes'], nodes)
    _expectation(expectation, packet)
    input_sha = hashlib.sha256(encoded).hexdigest()
    reviewed = expectation['label_review_status'] == 'reviewed'
    reasons, called, unchanged, review_sha, verdict = set(), False, False, None, None
    outcome = dict(status='not_executed', error_code=None)
    status = 'checked'
    if not reviewed:
        status = 'not_executed'; reasons.add('label_pending')
    elif expectation['input_sha256'] != input_sha:
        status = 'insufficient_evidence'; reasons.add('input_binding_mismatch')
    else:
        working = json.loads(encoded)
        called = True
        try:
            review = build_intake_test_intent_review(working['intake'], working['proposal'], working['sources'])
            outcome['status'] = 'returned'
        except IntakeTestIntentError as error:
            if type(error.code) is not str or error.code not in _PARENT_ERRORS:
                _fail('source_error')
            outcome = dict(status='error', error_code=error.code)
        except Exception:
            _fail('source_error')
        try:
            _, after = _copy(working, _LIMITS['max_input_bytes'], [0])
            unchanged = after == encoded
        except IntakeTestIntentEvaluationError:
            unchanged = False
        if not unchanged:
            reasons.add('input_changed')
        expected = expectation['expected']
        if outcome['status'] != expected['outcome'] or outcome['error_code'] != expected['error_code']:
            reasons.add('outcome_mismatch')
        if outcome['status'] == 'returned':
            try:
                review, _ = _copy(review, _PARENT_LIMITS['max_output_bytes'], [0])
            except IntakeTestIntentEvaluationError:
                _fail('source_error')
            review_sha = _hash(review)
            if not _matches(review, packet, expected['review']):
                reasons.add('review_mismatch')
        verdict = 'fail' if reasons else 'pass'
    result = dict(schema_version=1, kind='intake_test_intent_case_check', execution_mode='provided_input_contract_check',
        status=status, verdict=verdict, case_id=expectation['case_id'], case_group_id=expectation['case_group_id'],
        bindings=dict(input_sha256=input_sha, expectation_sha256=_hash(expectation), review_sha256=review_sha),
        declarations=_declarations(packet), outcome=outcome, reason_codes=sorted(reasons),
        counts=dict(review_api_calls=int(called), scored_contract_cases=int(called), actual_model_calls=0),
        actual_model_score=None, verification=dict(caller_label_review_declared=reviewed,
            contract_comparison_executed=called, input_values_unchanged=unchanged,
            model_execution_verified=False, model_quality_verified=False), limits=dict(_LIMITS))
    return _copy(result, _LIMITS['max_output_bytes'], [0])[0]


def evaluate_intake_test_intent_case(intake, proposal, sources, *, expectation):
    """Compare one provided case with a pre-authored oracle; model calls remain 0."""
    try:
        return _evaluate(intake, proposal, sources, expectation)
    except IntakeTestIntentEvaluationError as error:
        code = error.code
    except Exception:
        code = _PREFIX + 'source_error'
    raise IntakeTestIntentEvaluationError(code) from None
