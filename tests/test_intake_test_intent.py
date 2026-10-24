"""Provided synthetic evidence only; no actual model, regulation or current DB."""
from copy import deepcopy
import hashlib
import importlib
import json
import unittest
from unittest.mock import patch

from labflow.document_extract import extract_document, page_citation
from labflow.intake_analysis import project_analysis
from tests.test_document_extract import synthetic_pdf
from tests.test_intake_model_boundary import analysis as cited_analysis

try:
    api = importlib.import_module('labflow.intake_test_intent')
except ModuleNotFoundError as error:
    if error.name != 'labflow.intake_test_intent':
        raise
    api = None


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(value):
    return hashlib.sha256(raw(value)).hexdigest()


def fixture(*, pdf=False, literal='RULE-A', method='METHOD-A'):
    """Raw caller inputs using real extraction and the existing analysis helper."""
    text = f'product_type: sensor_node\nintent: {literal} {method}\nmarket: FCC\npurpose: development\nmodel: MODEL-A'
    payload = synthetic_pdf([text]) if pdf else text.encode('utf-8')
    result = extract_document(payload, 'request.pdf' if pdf else 'request.txt')
    source_sha = hashlib.sha256(payload).hexdigest()
    if pdf:
        doc = {'path': 'request.pdf', 'sha256': source_sha, 'bytes': len(payload), 'text': None,
               'format': 'pdf', 'parse_status': result['status'], 'extraction_id': 'a'*64,
               **{key: result[key] for key in ['parser', 'limits', 'pages', 'issues', 'complete', 'total_pages', 'processed_pages']}}
    else:
        doc = {'path': 'request.txt', 'sha256': source_sha, 'bytes': len(payload), 'text': text, 'parse_status': 'text'}
    version = 2 if pdf else 1
    evidence = {'path': 'document path', 'sha256': 'source hash', 'line_start': 'first line',
                'line_end': 'last line', 'quote': 'verbatim text', 'role': 'request|product|reference'}
    if pdf:
        evidence.update(kind='pdf_page', extraction_id='extraction hash', page_number='page', text_sha256='page hash')
    contract = {'schema_version': version, 'producer': {'kind': 'model|manual|fixture', 'name': 'name'},
                'identity': 'single|ambiguous|unknown', 'missing_fields': [],
                'facts': [{'field': 'product_type', 'value': 'value', 'status': 'explicit', 'evidence': [evidence]}]}
    if pdf:
        contract['context_id'] = 'a'*64
    context = {'job_id': 'JOB-INTENT', 'intake_id': 'INTAKE-INTENT', 'revision': 1,
               'synthetic': True, 'documents': [doc], 'analysis_contract': contract,
               'instructions': 'Synthetic untrusted document data', 'analysis_context_id': 'a'*64}
    analysis = cited_analysis(context)
    analysis['producer']['kind'] = 'fixture'
    analysis['facts'][0]['evidence'][0].update(line_end=2, quote='\n'.join(text.splitlines()[:2]))
    projection = project_analysis(analysis, [], {}, delegated=False, deferred=False)
    projection.update(intake_id=context['intake_id'], revision=context['revision'])
    intake = {'context': context, 'analysis': analysis, 'projection': projection, 'observation': None}
    basis = extract_document(f'{literal}\n{method}\nSynthetic provided text only'.encode(), 'basis.txt')
    source = {'document_id': 'BASIS-A', 'source_kind': 'standard', 'representation': 'extract',
              'artifact_sha256': basis['source']['sha256'], 'institution_scope': 'DECLARED-SCOPE',
              'workflow_scope_ids': ['F03'], 'edition': 'DECLARED-EDITION', 'effective_from': '2026-01-01',
              'effective_to': '2026-12-31', 'review_status': 'unreviewed', 'rights_status': 'unknown',
              'extraction': basis}
    def candidate(value, line):
        citation = page_citation(basis, 1, line, line)
        return {'literal': value, 'origin': 'explicit_supplied',
                'intake_refs': [{'fact_index': 0, 'evidence_index': 0}],
                'basis_refs': [{'document_id': 'BASIS-A', 'page_number': 1,
                                'text_sha256': citation['text_sha256'], 'line_start': line, 'line_end': line}]}
    proposal = {'as_of': '2026-10-25', 'institution_scope': 'DECLARED-SCOPE', 'workflow_scope_id': 'F03',
                'fields': {'rule': [candidate(literal, 1)], 'method': [candidate(method, 2)]}}
    return intake, proposal, [source]


def declared_capture(intake, *, status='observed'):
    """Untrusted shape input, NOT evidence that a 034 DB capture ran."""
    c, p = intake['context'], intake['projection']
    minimal = {'facts': {key: value for key, value in p['facts'].items() if key in {'product_type', 'market', 'model'}},
               'questions': [{'key': q['key']} for q in p['questions']]}
    origin = {'source_id': 'SYNTHETIC', 'origin_job_id': c['job_id'], 'result_sha256': 'b'*64,
              'analysis_context_id': c['analysis_context_id'], 'raw_manifest_sha256': 'c'*64}
    snapshot = {'schema_version': 1, 'kind': 'intake_case_reference_snapshot', 'snapshot_scope': 'caller_provided',
                'intake_id': c['intake_id'], 'revision': c['revision'], 'revision_fingerprint': 'd'*64,
                'origin_job_id': c['job_id'], 'analysis_context_id': c['analysis_context_id'], 'result_sha256': 'b'*64,
                'readiness_fingerprint': 'e'*64, 'synthetic': c['synthetic'], 'projection': minimal,
                'projection_sha256': sha(minimal)}
    return {'schema_version': 1, 'kind': 'intake_reference_snapshot_capture', 'status': status,
            'reason_codes': [], 'snapshot_id': 'f'*64, 'snapshot': snapshot, 'origin': origin,
            'state': {'intake_status': 'analyzed', 'delegated': False, 'deferred': False,
                      'projection_sha256': sha(p), 'answers_sha256': '0'*64, 'questions_sha256': '1'*64},
            'delegation': {'event_id': None, 'history_sha256': '2'*64, 'verified': False},
            'profile': {'stored_profile_id': '3'*64, 'current_profile_id': '3'*64, 'matches': True},
            'readiness': {'kind': 'reference_preparation_v1', 'ready': False, 'reason_codes': [],
                          'reference_state_fingerprint': 'e'*64, 'delegation_event_id': None},
            'verification': {key: False for key in ['database_snapshot_observed','retained_analysis_verified',
                            'live_projection_recomputed','preparation_bound','source_integrity_observed',
                            'operational_authority_granted','model_execution_verified','evaluation_executed']},
            'limits': {'result_json_bytes': 8388608, 'analysis_context_bytes': 4194304, 'raw_manifest_bytes': 4194304,
                       'source_file_bytes': 16777216, 'projection_json_bytes': 8388608, 'state_category_json_bytes': 8388608,
                       'max_questions': 10000, 'max_user_response_events': 10000, 'max_answers': 10,
                       'snapshot_json_bytes': 9437184, 'capture_json_bytes': 12582912}}


class IntakeTestIntentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'API absent: labflow.intake_test_intent')
        self.i, self.p, self.s = fixture()

    def call(self):
        return api.build_intake_test_intent_review(self.i, self.p, self.s)

    def rule(self, result):
        return result['fields']['rule']['candidates'][0]

    def error(self, code):
        with self.assertRaises(api.IntakeTestIntentError) as caught:
            self.call()
        e = caught.exception
        self.assertEqual((e.code, str(e), e.args), (code, code, (code,)))
        self.assertIsNone(e.__context__)
        self.assertNotIn('PRIVATE', repr(e))

    def test_g01_text_pdf_real_parents_detachment_and_false_authority(self):
        for pdf in (False, True):
            with self.subTest(pdf=pdf):
                self.i, self.p, self.s = fixture(pdf=pdf)
                before = deepcopy((self.i, self.p, self.s))
                with patch.object(api, 'validate_analysis', wraps=api.validate_analysis) as analysis_parent, \
                     patch.object(api, 'page_citation', wraps=api.page_citation) as page_parent:
                    r = self.call()
                self.assertEqual(r['status'], 'review_only')
                self.assertEqual(r['fields']['rule']['status'], 'literal_linked')
                self.assertTrue(self.rule(r)['literal_linked'])
                self.assertEqual(analysis_parent.call_count, 1)
                self.assertEqual(page_parent.call_count, 2)
                self.assertEqual((self.i, self.p, self.s), before)
                flags = r['verification']
                self.assertEqual(len(flags), 14)
                self.assertTrue(flags['intake_citations_checked'] and flags['basis_literals_checked'])
                self.assertFalse(any(v for k, v in flags.items() if k not in {'intake_citations_checked','basis_literals_checked'}))
                self.assertEqual(len(r['input_binding']), 11)
                self.assertEqual(len(r['limits']), 18)
                r['fields']['rule']['candidates'][0]['intake_refs'][0]['fact_index'] = 999
                self.assertEqual((self.i, self.p, self.s), before)

    def test_g02_inferred_uncertain_product_reference_do_not_become_request_literals(self):
        for attr, value in [('status','inferred'), ('status','uncertain'), ('role','product'), ('role','reference')]:
            with self.subTest(attr=attr, value=value):
                self.i, self.p, self.s = fixture()
                fact = self.i['analysis']['facts'][0]
                (fact if attr == 'status' else fact['evidence'][0])[attr] = value
                self.i['projection']['submitted'] = deepcopy(self.i['analysis'])
                self.p['fields']['rule'][0]['origin'] = 'model_proposed'
                r = self.call()
                self.assertFalse(self.rule(r)['literal_linked'])
                self.assertIn('intake_ground_missing', self.rule(r)['reason_codes'])
                self.assertEqual(self.rule(r)['origin'], 'model_proposed')

    def test_g03_conflicts_questions_and_same_literal_partial_candidate(self):
        question = {'key':'product_identity','message':'Synthetic unresolved target'}
        self.i['projection']['questions'] = [question]
        other = deepcopy(self.p['fields']['rule'][0]); other['literal'] = 'OTHER'
        self.p['fields']['rule'].append(other)
        r = self.call()
        self.assertEqual(r['fields']['rule']['status'], 'conflicting')
        self.assertEqual(r['questions'], [question])
        self.assertIn('intake_questions_open', r['reason_codes'])
        self.p['fields']['rule'][1]['literal'] = 'RULE-A'
        self.p['fields']['rule'][1]['intake_refs'] = []
        r = self.call()
        self.assertEqual(r['fields']['rule']['status'], 'proposed')
        self.assertEqual([x['literal_linked'] for x in r['fields']['rule']['candidates']], [True, False])

    def test_g04_v1_missing_context_id_is_normal_and_v2_capture_hashes_are_distinct(self):
        self.i['context'].pop('analysis_context_id')
        r = self.call()
        self.assertIsNone(r['input_binding']['analysis_context_id'])
        self.assertIn('intake_binding_incomplete', r['reason_codes'])
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['observation'] = declared_capture(self.i)
        r = self.call()
        self.assertNotIn('intake_binding_mismatch', r['reason_codes'])
        self.assertNotIn('intake_binding_incomplete', r['reason_codes'])
        self.i['observation']['state']['projection_sha256'] = self.i['observation']['snapshot']['projection_sha256']
        r = self.call()
        self.assertIn('intake_binding_mismatch', r['reason_codes'])
        self.assertFalse(self.rule(r)['literal_linked'])

    def test_g04_submitted_mismatch_stale_and_parent_context_failure(self):
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['projection']['submitted'] = deepcopy(self.i['analysis'])
        self.i['projection']['submitted']['identity'] = 'unknown'
        r = self.call()
        self.assertIn('intake_binding_mismatch', self.rule(r)['reason_codes'])
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['observation'] = declared_capture(self.i, status='stale')
        self.assertIn('intake_binding_incomplete', self.call()['reason_codes'])
        self.i['analysis']['context_id'] = '0'*64
        self.error('test_intent_source_error')

    def test_g04_unavailable_capture_and_optional_projection_ids_preserve_unknown(self):
        cap = declared_capture(self.i)
        cap.update(status='unavailable', snapshot=None, snapshot_id=None, reason_codes=['legacy_analysis'])
        for key in ('origin','state','delegation'):
            cap[key] = dict.fromkeys(cap[key])
        cap['profile'].update(stored_profile_id=None, matches=None)
        cap['readiness'].update(ready=False, reason_codes=['legacy_analysis'],
                                reference_state_fingerprint=None, delegation_event_id=None)
        cap['verification']['operational_authority_granted'] = True  # Untrusted caller declaration.
        self.i['observation'] = cap
        self.i['context'].pop('analysis_context_id')
        r = self.call()
        self.assertIsNone(r['input_binding']['result_sha256'])
        self.assertIsNone(r['input_binding']['observation_snapshot_id'])
        self.assertEqual(r['input_binding']['provided_observation_sha256'], sha(cap))
        self.assertFalse(r['verification']['execution_authorized'])
        self.assertIn('intake_binding_incomplete', r['reason_codes'])
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['observation'] = declared_capture(self.i)
        self.i['projection'].pop('revision')
        r = self.call()
        self.assertIn('intake_binding_incomplete', r['reason_codes'])
        self.assertNotIn('intake_binding_mismatch', r['reason_codes'])
        self.assertNotIn('revision', self.i['projection'])

    def test_g04_nested_capture_mismatch_and_v1_nonnull_snapshot_are_not_repaired(self):
        self.i['observation'] = declared_capture(self.i)
        self.assertIn('intake_binding_mismatch', self.call()['reason_codes'])
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['observation'] = declared_capture(self.i)
        self.i['observation']['origin']['result_sha256'] = '9'*64
        r = self.call()
        self.assertIn('intake_binding_mismatch', self.rule(r)['reason_codes'])
        self.assertEqual(r['input_binding']['result_sha256'], '9'*64)

    def test_g04_current_answer_projection_is_not_recomputed_from_submission(self):
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['projection']['facts']['model'] = {'value':'ANSWER-MODEL','status':'user_confirmed','event_id':'ANSWER'}
        self.i['observation'] = declared_capture(self.i)
        r = self.call()
        self.assertNotIn('intake_binding_mismatch', r['reason_codes'])
        self.assertEqual(r['input_binding']['result_sha256'], 'b'*64)
        self.assertEqual(r['input_binding']['provided_projection_sha256'], sha(self.i['projection']))

    def test_g05_both_sides_all_references_and_original_quote(self):
        for side in ['intake_refs','basis_refs']:
            with self.subTest(side=side):
                self.i, self.p, self.s = fixture()
                self.p['fields']['rule'][0][side] = []
                self.assertFalse(self.rule(self.call())['literal_linked'])
        self.i, self.p, self.s = fixture(pdf=True)
        self.i['analysis']['facts'][0]['evidence'][0]['quote'] = 'product_type: sensor_node'
        self.i['projection']['submitted'] = deepcopy(self.i['analysis'])
        r = self.call()
        self.assertFalse(self.rule(r)['literal_linked'])
        self.assertIn('literal_not_in_citation', self.rule(r)['reason_codes'])

    def test_g05_wrong_hash_dangling_duplicate_and_null_source(self):
        mutations = [
            ('test_intent_source_error', lambda: self.p['fields']['rule'][0]['basis_refs'][0].update(text_sha256='0'*64)),
            ('test_intent_source_error', lambda: self.s[0].update(artifact_sha256='0'*64)),
            ('test_intent_invalid_input', lambda: self.p['fields']['rule'][0]['intake_refs'][0].update(fact_index=True)),
            ('test_intent_invalid_input', lambda: self.p['fields']['rule'][0]['intake_refs'][0].update(evidence_index=999)),
            ('test_intent_invalid_input', lambda: self.p['fields']['rule'][0]['basis_refs'][0].update(document_id='MISSING')),
            ('test_intent_invalid_input', lambda: self.s.append(deepcopy(self.s[0]))),
            ('test_intent_invalid_input', lambda: self.p['fields']['rule'][0]['basis_refs'].append(deepcopy(self.p['fields']['rule'][0]['basis_refs'][0]))),
            ('test_intent_invalid_input', lambda: self.p['fields']['rule'].append(deepcopy(self.p['fields']['rule'][0]))),
        ]
        for code, mutate in mutations:
            with self.subTest(code=code, mutation=mutate):
                self.i, self.p, self.s = fixture(); mutate(); self.error(code)
        self.i, self.p, self.s = fixture(); self.s[0]['extraction'] = None
        r = self.call()
        self.assertFalse(self.rule(r)['literal_linked'])
        self.assertFalse(r['verification']['basis_literals_checked'])
        self.assertIn('basis_missing', self.rule(r)['reason_codes'])

    def test_g05_each_reference_matters_and_checked_does_not_mean_matching(self):
        self.p['fields']['rule'][0]['intake_refs'].append({'fact_index':1,'evidence_index':0})
        self.assertFalse(self.rule(self.call())['literal_linked'])
        self.i, self.p, self.s = fixture()
        other = deepcopy(self.p['fields']['rule'][0]['basis_refs'][0])
        other.update(line_start=2, line_end=2)
        self.p['fields']['rule'][0]['basis_refs'].append(other)
        r = self.call()
        self.assertFalse(self.rule(r)['literal_linked'])
        self.assertTrue(r['verification']['basis_literals_checked'])
        self.s[0]['extraction']['pages'][0]['line_spans'][0]['end'] += 1
        self.error('test_intent_source_error')

    def test_g05_no_references_do_not_skip_invalid_parent_analysis(self):
        self.p['fields'] = {'rule': [], 'method': []}
        r = self.call()
        self.assertEqual(r['fields']['rule']['status'], 'missing')
        self.assertFalse(r['verification']['intake_citations_checked'])
        self.assertFalse(r['verification']['basis_literals_checked'])
        self.i['analysis']['facts'][0]['evidence'][0]['quote'] = 'PRIVATE-ABSENT'
        self.error('test_intent_source_error')

    def test_g06_report_rights_review_do_not_grant_normative_authority(self):
        self.s[0].update(source_kind='report', representation='metadata', rights_status='restricted')
        r = self.call()
        self.assertTrue(self.rule(r)['literal_linked'])
        self.assertTrue({'source_not_normative','source_status_unconfirmed','edition_unconfirmed'} <= set(self.rule(r)['reason_codes']))
        self.assertFalse(r['verification']['normative_applicability_verified'])

    def test_g07_period_priority_and_inclusive_boundaries(self):
        rows = [('2026-01-01','2026-01-01','2026-12-31','in_declared_window'),
                ('2026-12-31','2026-01-01','2026-12-31','in_declared_window'),
                (None,'2026-12-31','2026-01-01','conflicting'),
                (None,'2026-01-01','2026-12-31','unconfirmed'),
                ('2026-10-25','2026-01-01',None,'unconfirmed'),
                ('2026-01-01',None,'2026-12-31','unconfirmed'),
                ('2025-12-31','2026-01-01',None,'outside_declared_window'),
                ('2027-01-01',None,'2026-12-31','outside_declared_window')]
        for as_of, start, end, want in rows:
            with self.subTest(row=(as_of,start,end)):
                self.p['as_of'] = as_of; self.s[0].update(effective_from=start, effective_to=end)
                self.assertEqual(self.rule(self.call())['period_checks'], [{'document_id':'BASIS-A','status':want}])
        self.p['as_of'] = '2026-02-30'; self.error('test_intent_invalid_input')

    def test_g07_scope_metadata_missing_and_literal_comparisons(self):
        self.p['institution_scope'] = None; self.s[0]['workflow_scope_ids'] = []
        r = self.call()
        self.assertIn('institution_scope_unconfirmed', self.rule(r)['reason_codes'])
        self.assertIn('source_status_unconfirmed', self.rule(r)['reason_codes'])
        self.p['institution_scope'] = 'OTHER'; self.s[0]['workflow_scope_ids'] = ['F02']
        self.assertIn('scope_conflicting', self.rule(self.call())['reason_codes'])

    def test_g07_period_docs_are_unique_sorted_while_refs_keep_order(self):
        other = deepcopy(self.s[0]); other['document_id'] = 'BASIS-Z'
        self.s.append(other)
        ref = deepcopy(self.p['fields']['rule'][0]['basis_refs'][0]); ref['document_id'] = 'BASIS-Z'
        self.p['fields']['rule'][0]['basis_refs'].insert(0, ref)
        r = self.call()
        self.assertEqual([x['document_id'] for x in self.rule(r)['period_checks']], ['BASIS-A','BASIS-Z'])
        self.assertEqual([x['document_id'] for x in self.rule(r)['basis_refs']], ['BASIS-Z','BASIS-A'])

    def test_g08_array_caps_and_output_budget_have_observable_effect(self):
        evidence = deepcopy(self.i['analysis']['facts'][0]['evidence'][0])
        self.i['analysis']['facts'][0]['evidence'] = [deepcopy(evidence) for _ in range(8)]
        self.i['projection']['submitted'] = deepcopy(self.i['analysis'])
        self.p['fields']['rule'][0]['intake_refs'] = [{'fact_index':0,'evidence_index':n} for n in range(8)]
        self.assertTrue(self.rule(self.call())['literal_linked'])
        self.p['fields']['rule'][0]['intake_refs'].append({'fact_index':0,'evidence_index':0})
        self.error('test_intent_limit_exceeded')
        self.i, self.p, self.s = fixture()
        for n in range(7):
            other = deepcopy(self.s[0]); other['document_id'] = f'EXTRA-{n}'; self.s.append(other)
        self.assertTrue(self.rule(self.call())['literal_linked'])
        other = deepcopy(self.s[0]); other['document_id'] = 'EXTRA-8'; self.s.append(other)
        self.error('test_intent_limit_exceeded')
        self.i, self.p, self.s = fixture()
        self.i['projection']['questions'] = [{'key':'product_identity','message':'Q'*2097152}]
        self.error('test_intent_limit_exceeded')

    def test_g08_native_subclasses_boolean_indices_and_oversized_integer_are_rejected(self):
        class Hostile(dict):
            def items(self):
                raise AssertionError('must not invoke caller code')
        self.i['context'] = Hostile(self.i['context'])
        self.error('test_intent_invalid_input')
        self.i, self.p, self.s = fixture(); self.i['context']['revision'] = True
        self.error('test_intent_invalid_input')
        self.i, self.p, self.s = fixture(); self.p['extra'] = 10**5000
        self.error('test_intent_limit_exceeded')

    def test_g08_character_array_byte_depth_node_and_native_json_limits(self):
        self.i, self.p, self.s = fixture(literal='X'*256)
        self.assertTrue(self.rule(self.call())['literal_linked'])
        self.p['fields']['rule'][0]['literal'] += 'X'; self.error('test_intent_limit_exceeded')
        for value in [float('nan'), float('inf'), '\ud800']:
            self.i, self.p, self.s = fixture(); self.p['extra'] = value
            self.error('test_intent_invalid_input')
        self.i, self.p, self.s = fixture(); self.p['extra'] = []
        self.p['extra'].append(self.p['extra']); self.error('test_intent_invalid_input')
        self.i, self.p, self.s = fixture(); deep = None
        for _ in range(31): deep = [deep]
        self.p['extra'] = deep; self.error('test_intent_limit_exceeded')
        self.i, self.p, self.s = fixture(); self.p['extra'] = [None]*2000001
        self.error('test_intent_limit_exceeded')

    def test_g08_section_byte_budget_precedes_invalid_schema(self):
        self.i['extra'] = 'invalid schema after budgets'
        self.p['extra'] = 'B'*65536
        self.error('test_intent_limit_exceeded')
        self.i, self.p, self.s = fixture(); self.s[0]['extraction']['opaque'] = 'Z'*8388608
        self.error('test_intent_limit_exceeded')

    def test_g09_no_complete_query_selection_registration_or_authority_output(self):
        r = self.call()
        self.assertEqual(set(r), {'schema_version','kind','status','input_binding','fields','questions','reason_codes','verification','limits'})
        self.assertIn('applicability_not_assessed', r['reason_codes'])
        self.assertFalse(r['verification']['query_release_authorized'])
        self.assertFalse(r['verification']['case_selection_authorized'])
        self.assertFalse(r['verification']['execution_authorized'])

    def test_g10_api_uses_no_file_parser_database_network_or_process(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('pathlib.Path.open', side_effect=AssertionError('path')), \
             patch('os.open', side_effect=AssertionError('native file')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')), \
             patch('socket.socket', side_effect=AssertionError('socket')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('labflow.document_extract.extract_document', side_effect=AssertionError('parser')):
            r = self.call()
        self.assertTrue(self.rule(r)['literal_linked'])


if __name__ == '__main__':
    unittest.main()
