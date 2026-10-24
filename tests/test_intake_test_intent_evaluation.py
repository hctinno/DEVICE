"""Independent synthetic contract oracle; no actual model or regulatory labels."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib
import json
import unittest
from unittest.mock import patch

from labflow.document_extract import extract_document, page_citation
from labflow.intake_test_intent import build_intake_test_intent_review
from tests.test_document_extract import synthetic_pdf
from tests.test_intake_model_boundary import analysis as cited_analysis
from tests.test_intake_test_intent import declared_capture

try:
    api = importlib.import_module('labflow.intake_test_intent_evaluation')
except ModuleNotFoundError as error:
    if error.name != 'labflow.intake_test_intent_evaluation':
        raise
    api = None


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(value):
    return hashlib.sha256(raw(value)).hexdigest()


def fixture(pdf=False):
    """Fresh source text and current questions; never runs the reviewed API."""
    text = ('product_type: evaluation_beacon\npurpose: compare SYN-RULE-ELM with SYN-METHOD-ELM\n'
            'model: EVAL-MODEL-19\nmarket: FCC')
    payload = synthetic_pdf([text]) if pdf else text.encode('utf-8')
    path = 'evaluation-request.pdf' if pdf else 'evaluation-request.txt'
    source_sha = hashlib.sha256(payload).hexdigest()
    if pdf:
        extraction = extract_document(payload, path)
        doc = dict(path=path, sha256=source_sha, bytes=len(payload), text=None, format='pdf',
                   extraction_id='a'*64, parse_status=extraction['status'],
                   **{k: extraction[k] for k in ('parser','limits','pages','issues','complete','total_pages','processed_pages')})
    else:
        doc = dict(path=path, sha256=source_sha, bytes=len(payload), text=text, parse_status='text')
    context = dict(job_id='EVAL-JOB-19', intake_id='EVAL-INTAKE-19', revision=3, synthetic=True,
                   documents=[doc], instructions='Synthetic request; no execution permission.',
                   analysis_contract=dict(schema_version=2 if pdf else 1, producer={'kind':'declared','name':'template'},
                                          identity='single', missing_fields=[], facts=[]))
    if pdf:
        context['analysis_context_id'] = 'a'*64
        context['analysis_contract']['context_id'] = 'a'*64
    analysis = cited_analysis(context)
    analysis['producer'] = {'kind':'fixture','name':'independent-evaluation-text-v1'}
    projection = dict(facts={'product_type':{'value':'evaluation_beacon','status':'explicit'}},
        questions=[{'key':'conflict_model','field':'model','values':['EVAL-LEFT','EVAL-RIGHT'],'message':'Keep both model choices.'},
                   {'key':'missing_market','field':'market','message':'Keep the current unanswered market question.'}],
        next_action='needs_information', measurement_support='unverified', verification='contract_only',
        submitted=deepcopy(analysis), unread_documents=[], intake_id=context['intake_id'], revision=3)
    intake = dict(context=context, analysis=analysis, projection=projection, observation=None)
    basis = extract_document(b'SYN-RULE-ELM\nSYN-METHOD-ELM\nSynthetic comparison text.', 'evaluation-basis.txt')
    source = dict(document_id='EVAL-BASIS', source_kind='standard', representation='original',
        artifact_sha256=basis['source']['sha256'], institution_scope='EVAL-SCOPE-A', workflow_scope_ids=['F03'],
        edition='SYN-EDITION-19', effective_from='2026-02-03', effective_to='2026-11-07',
        review_status='reviewed', rights_status='usable', extraction=basis)
    def candidate(literal, line):
        citation = page_citation(basis, 1, line, line)
        return dict(literal=literal, origin='explicit_supplied', intake_refs=[{'fact_index':1,'evidence_index':0}],
            basis_refs=[dict(document_id='EVAL-BASIS', page_number=1, text_sha256=citation['text_sha256'], line_start=line, line_end=line)])
    proposal = dict(as_of='2026-06-15', institution_scope='EVAL-SCOPE-A', workflow_scope_id='F03',
                    fields={'rule':[candidate('SYN-RULE-ELM',1)],'method':[candidate('SYN-METHOD-ELM',2)]})
    return dict(intake=intake, proposal=proposal, sources=[source])


def expected_review():
    # Written from the source sentences and published contract before API execution.
    fields = {name:dict(status='literal_linked', candidates=[dict(literal_linked=True,
        period_checks=[{'document_id':'EVAL-BASIS','status':'in_declared_window'}], reason_codes=['edition_unconfirmed'])],
        reason_codes=['edition_unconfirmed']) for name in ('rule','method')}
    return dict(fields=fields, reason_codes=['applicability_not_assessed','edition_unconfirmed','intake_binding_incomplete','intake_questions_open'],
                calculation_flags={'intake_citations_checked':True,'basis_literals_checked':True})


def add_reason(review, reason, fields=('rule','method')):
    review['reason_codes'] = sorted(set(review['reason_codes']) | {reason})
    for name in fields:
        row = review['fields'][name]
        row['reason_codes'] = sorted(set(row['reason_codes']) | {reason})
        for candidate in row['candidates']:
            candidate['reason_codes'] = sorted(set(candidate['reason_codes']) | {reason})


def expectation(packet, identity, review=None, error=None):
    return dict(schema_version=1, kind='intake_test_intent_case_expectation', case_id=identity,
        case_group_id='SYN-EVAL-GROUP-19', input_sha256=sha(packet), label_review_status='reviewed',
        expected=dict(outcome='error' if error else 'returned', error_code=error, review=None if error else deepcopy(review)))


def oracle_cases():
    """All labels are authored here without calling or reading API output."""
    cases = {}
    base = fixture()
    def put(name, packet, review=None, error=None):
        cases[name] = (packet, expectation(packet, name, review, error))
    put('E01-text', deepcopy(base), expected_review())
    put('E01-pdf', fixture(True), expected_review())
    for role in ('product','reference'):
        p, e = deepcopy(base), expected_review()
        p['intake']['analysis']['facts'][1]['evidence'][0]['role'] = role
        p['intake']['projection']['submitted'] = deepcopy(p['intake']['analysis'])
        for f in e['fields'].values():
            f['status']='proposed'; f['candidates'][0]['literal_linked']=False
        add_reason(e,'intake_ground_missing'); put('E02-'+role,p,e)
    p,e=deepcopy(base),expected_review()
    p['proposal']['fields']['rule'][0]['intake_refs']=[]
    e['fields']['rule']['status']='proposed'; e['fields']['rule']['candidates'][0]['literal_linked']=False
    add_reason(e,'intake_ground_missing',('rule',)); put('E02-basis-only',p,e)
    p,e=deepcopy(base),expected_review()
    p['proposal']['fields']['rule'][0]['literal']='outside-original-quote'
    e['fields']['rule']['status']='proposed'; e['fields']['rule']['candidates'][0]['literal_linked']=False
    add_reason(e,'literal_not_in_citation',('rule',)); put('E02-literal-missing',p,e)
    p,e=deepcopy(base),expected_review()
    p['proposal']['fields']['rule']=[]
    e['fields']['rule']={'status':'missing','candidates':[],'reason_codes':['intent_missing']}
    e['reason_codes']=sorted(set(e['reason_codes'])|{'intent_missing'}); put('E03-missing',p,e)
    for different in (False, True):
        p,e=deepcopy(base),expected_review()
        other=deepcopy(p['proposal']['fields']['rule'][0]); other['intake_refs']=[]
        if different: other['literal']='SYN-METHOD-ELM'
        p['proposal']['fields']['rule'].append(other)
        row=e['fields']['rule']; row['status']='conflicting' if different else 'proposed'
        second=deepcopy(row['candidates'][0]); second['literal_linked']=False
        second['reason_codes']=['edition_unconfirmed','intake_ground_missing']
        if different: second['reason_codes'].append('literal_not_in_citation')
        row['candidates'].append(second); row['reason_codes']=sorted(set(second['reason_codes'])|({'intent_conflicting'} if different else set()))
        e['reason_codes']=sorted(set(e['reason_codes'])|set(row['reason_codes']))
        put('E03-conflict' if different else 'E03-partial',p,e)
    p,e=deepcopy(base),expected_review()
    p['intake']['projection']['facts']['market']={'value':'NEW-CURRENT-ANSWER','status':'user_confirmed','event_id':'EVAL-ANSWER'}
    put('E04-current-answer',p,e)
    for status in ('observed','stale','mismatch'):
        p,e=deepcopy(cases['E01-pdf'][0]),expected_review()
        obs=declared_capture(p['intake'],status='stale' if status=='stale' else 'observed')
        p['intake']['observation']=obs
        if status!='stale': e['reason_codes'].remove('intake_binding_incomplete')
        if status=='mismatch':
            obs['state']['projection_sha256']='9'*64
            add_reason(e,'intake_binding_mismatch')
            for row in e['fields'].values(): row['status']='proposed'; row['candidates'][0]['literal_linked']=False
        put('E04-'+status,p,e)
    p,e=deepcopy(base),expected_review()
    obs=declared_capture(cases['E01-pdf'][0]['intake']); obs.update(status='unavailable',snapshot_id=None,snapshot=None,reason_codes=['legacy_analysis'])
    for key in ('origin','state','delegation'): obs[key]={k:None for k in obs[key]}
    obs['profile'].update(stored_profile_id=None,matches=None)
    obs['readiness'].update(ready=False,reference_state_fingerprint=None,delegation_event_id=None)
    p['intake']['observation']=obs; put('E04-unavailable',p,e)
    periods=[('start','2026-02-03','2026-02-03','2026-11-07','in_declared_window',None),
             ('end','2026-11-07','2026-02-03','2026-11-07','in_declared_window',None),
             ('outside','2026-11-08','2026-02-03','2026-11-07','outside_declared_window','period_outside_declared_window'),
             ('null-start','2026-06-15',None,'2026-11-07','unconfirmed','period_unconfirmed'),
             ('null-asof',None,'2026-02-03','2026-11-07','unconfirmed','period_unconfirmed'),
             ('reversed',None,'2026-11-07','2026-02-03','conflicting','period_conflicting')]
    for name,asof,start,end,status,reason in periods:
        p,e=deepcopy(base),expected_review(); p['proposal']['as_of']=asof
        p['sources'][0].update(effective_from=start,effective_to=end)
        for row in e['fields'].values(): row['candidates'][0]['period_checks'][0]['status']=status
        if reason: add_reason(e,reason)
        put('E05-'+name,p,e)
    for name,changes,reasons in [
        ('scope',{'institution_scope':'OTHER-SCOPE','workflow_scope_ids':['F04']},['scope_conflicting']),
        ('scope-null',{'institution_scope':None},['institution_scope_unconfirmed']),
        ('report',{'source_kind':'report'},['source_not_normative']),
        ('manufacturer',{'source_kind':'manufacturer'},['source_not_normative']),
        ('rights',{'representation':'extract','review_status':'unreviewed','rights_status':'unknown'},['source_status_unconfirmed'])]:
        p,e=deepcopy(base),expected_review(); p['sources'][0].update(changes)
        for reason in reasons: add_reason(e,reason)
        put('E06-'+name,p,e)
    p=deepcopy(base)
    for row in p['proposal']['fields'].values(): row[0]['origin']='model_proposed'
    put('E07-model-declared',p,expected_review())
    for name,change,code in [
        ('index',lambda p:p['proposal']['fields']['rule'][0]['intake_refs'][0].update(fact_index=99),'test_intent_invalid_input'),
        ('duplicate',lambda p:p['proposal']['fields']['rule'][0]['basis_refs'].append(deepcopy(p['proposal']['fields']['rule'][0]['basis_refs'][0])),'test_intent_invalid_input'),
        ('sha',lambda p:p['proposal']['fields']['rule'][0]['basis_refs'][0].update(text_sha256='0'*64),'test_intent_source_error'),
        ('source-sha',lambda p:p['sources'][0].update(artifact_sha256='0'*64),'test_intent_source_error'),
        ('literal-cap',lambda p:p['proposal']['fields']['rule'][0].update(literal='x'*257),'test_intent_limit_exceeded'),
        ('byte-cap',lambda p:p['intake']['context'].update(instructions='x'*(6*1024*1024)),'test_intent_limit_exceeded')]:
        p=deepcopy(base); change(p); put('E08-'+name,p,error=code)
    p=deepcopy(cases['E01-pdf'][0]); p['intake']['analysis']['context_id']='b'*64
    p['intake']['projection']['submitted']=deepcopy(p['intake']['analysis'])
    put('E08-context',p,error='test_intent_source_error')
    p=deepcopy(base); ex=expectation(p,'E09-pending',expected_review()); ex.update(label_review_status='pending',expected=None)
    cases['E09-pending']=(p,ex)
    p=deepcopy(base); ex=expectation(p,'E09-binding',expected_review()); ex['input_sha256']='0'*64
    cases['E09-binding']=(p,ex)
    p,e=deepcopy(base),expected_review(); e['fields']['rule']['status']='proposed'; e['fields']['rule']['candidates'][0]['literal_linked']=False
    put('E10-opposite',p,e)
    return cases


def additional_oracle_cases():
    """Coverage additions, frozen before their first calls; no API-derived labels."""
    cases={}; base=fixture()
    def put(name,p,e): cases[name]=(p,expectation(p,name,e))
    p=deepcopy(base)
    p['proposal']['fields']={'rule':[],'method':[]}
    e=dict(fields={f:dict(status='missing',candidates=[],reason_codes=['intent_missing']) for f in ('rule','method')},
        reason_codes=['applicability_not_assessed','intake_binding_incomplete','intake_questions_open','intent_missing'],
        calculation_flags={'intake_citations_checked':False,'basis_literals_checked':False})
    put('E03-all-missing',p,e)
    p,e=deepcopy(base),expected_review(); p['sources'][0].update(extraction=None,artifact_sha256=None)
    for row in e['fields'].values(): row['status']='proposed'; row['candidates'][0]['literal_linked']=False
    e['calculation_flags']['basis_literals_checked']=False; add_reason(e,'basis_missing'); put('E08-null-basis',p,e)
    p,e=deepcopy(base),expected_review()
    p['proposal']['fields']['rule'][0]['intake_refs'].append({'fact_index':0,'evidence_index':0})
    e['fields']['rule']['status']='proposed'; e['fields']['rule']['candidates'][0]['literal_linked']=False
    add_reason(e,'literal_not_in_citation',('rule',)); put('E02-one-of-all-refs',p,e)
    for status in ('inferred','uncertain'):
        p,e=deepcopy(base),expected_review(); p['intake']['analysis']['facts'][1]['status']=status
        p['intake']['projection']['submitted']=deepcopy(p['intake']['analysis'])
        for row in e['fields'].values(): row['status']='proposed'; row['candidates'][0]['literal_linked']=False
        add_reason(e,'intake_ground_missing'); put('E02-'+status,p,e)
    p,e=deepcopy(base),expected_review(); p['intake']['analysis']['facts'][1]['evidence'][0]['quote']='compare'
    p['intake']['projection']['submitted']=deepcopy(p['intake']['analysis'])
    for row in e['fields'].values(): row['status']='proposed'; row['candidates'][0]['literal_linked']=False
    add_reason(e,'literal_not_in_citation'); put('E02-outside-original-quote',p,e)
    p,e=deepcopy(base),expected_review(); p['intake']['context']['synthetic']=False
    p['intake']['analysis']['producer']['kind']='manual'; p['intake']['projection']['submitted']=deepcopy(p['intake']['analysis'])
    put('E07-nonsynthetic-declaration',p,e)
    return cases


class IntakeTestIntentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'Assigned evaluation API must exist')
        self.cases=oracle_cases()
        self.cases.update(additional_oracle_cases())

    def run_case(self,name):
        packet,ex=deepcopy(self.cases[name]); before=raw(packet)
        with patch.object(api,'build_intake_test_intent_review',wraps=build_intake_test_intent_review) as parent:
            result=api.evaluate_intake_test_intent_case(**packet,expectation=ex)
        self.assertEqual(result['counts']['review_api_calls'],parent.call_count)
        self.assertEqual(raw(packet),before)
        return result

    def test_e01_text_pdf_exact_contract_and_no_quality_authority(self):
        for name in ('E01-text','E01-pdf'):
            r=self.run_case(name)
            self.assertEqual((r['status'],r['verdict']),('checked','pass'))
            self.assertEqual(set(r),set('schema_version kind execution_mode status verdict case_id case_group_id bindings declarations outcome reason_codes counts actual_model_score verification limits'.split()))
            self.assertEqual(r['counts'],dict(review_api_calls=1,scored_contract_cases=1,actual_model_calls=0))
            self.assertIsNone(r['actual_model_score']); self.assertFalse(r['verification']['model_quality_verified'])
            self.assertFalse(r['verification']['model_execution_verified'])

    def test_e02_e03_grounding_conflicts_and_missing_are_contract_passes(self):
        for name in self.cases:
            if name.startswith(('E02-','E03-')):
                with self.subTest(name=name): self.assertEqual(self.run_case(name)['verdict'],'pass')

    def test_e04_original_questions_current_answer_and_unknown_binding(self):
        for name in self.cases:
            if name.startswith('E04-'):
                with self.subTest(name=name): self.assertEqual(self.run_case(name)['verdict'],'pass')

    def test_e05_e06_period_scope_and_unconfirmed_edition(self):
        for name in self.cases:
            if name.startswith(('E05-','E06-')):
                with self.subTest(name=name): self.assertEqual(self.run_case(name)['verdict'],'pass')

    def test_e07_declarations_are_not_actual_models(self):
        r=self.run_case('E07-model-declared')
        self.assertEqual(r['verdict'],'pass'); self.assertEqual(r['declarations']['proposal_origins'],['model_proposed'])
        self.assertEqual(r['counts']['actual_model_calls'],0); self.assertIsNone(r['actual_model_score'])

    def test_e08_parent_fixed_errors_are_compared_and_preserved(self):
        for name in self.cases:
            if name.startswith('E08-') and self.cases[name][1]['expected']['outcome']=='error':
                with self.subTest(name=name):
                    r=self.run_case(name); self.assertEqual(r['verdict'],'pass')
                    self.assertEqual(r['outcome']['error_code'],self.cases[name][1]['expected']['error_code'])
                    self.assertIsNone(r['bindings']['review_sha256'])

    def test_e09_pending_and_wrong_binding_never_call_parent_or_score(self):
        for name,status,reason in [('E09-pending','not_executed','label_pending'),('E09-binding','insufficient_evidence','input_binding_mismatch')]:
            r=self.run_case(name); self.assertEqual(r['status'],status); self.assertIsNone(r['verdict'])
            self.assertEqual(r['reason_codes'],[reason]); self.assertEqual(r['counts']['scored_contract_cases'],0)
            self.assertEqual(r['counts']['review_api_calls'],0); self.assertFalse(r['verification']['input_values_unchanged'])

    def test_e10_opposite_valid_label_is_checked_fail(self):
        r=self.run_case('E10-opposite'); self.assertEqual((r['status'],r['verdict']),('checked','fail'))
        self.assertEqual(r['reason_codes'],['review_mismatch'])

    def test_e10_mock_corruptions_never_become_passes(self):
        p,ex=deepcopy(self.cases['E01-text'])
        mutations=[lambda r:r['questions'].reverse(), lambda r:r['verification'].update(execution_authorized=True),
            lambda r:r['input_binding'].update(provided_sources_sha256='0'*64), lambda r:r.update(query={}),
            lambda r:r['limits'].update(max_depth=99), lambda r:r['fields']['rule']['candidates'][0]['intake_refs'].reverse(),
            lambda r:r['fields']['rule']['candidates'][0].update(literal='CHANGED'),lambda r:r.update(schema_version=True)]
        # Two refs make their ordering mutation observable, independently of parent results.
        p['proposal']['fields']['rule'][0]['intake_refs'].append({'fact_index':1,'evidence_index':0})
        # Use a second distinct valid reference instead of duplicate parent-invalid input.
        p['intake']['analysis']['facts'][1]['evidence'].append(deepcopy(p['intake']['analysis']['facts'][1]['evidence'][0]))
        p['proposal']['fields']['rule'][0]['intake_refs'][1]['evidence_index']=1
        p['intake']['projection']['submitted']=deepcopy(p['intake']['analysis']); ex['input_sha256']=sha(p)
        original=build_intake_test_intent_review(**p)
        for change in mutations:
            changed=deepcopy(original); change(changed)
            with patch.object(api,'build_intake_test_intent_review',return_value=changed):
                r=api.evaluate_intake_test_intent_case(**p,expectation=ex)
            self.assertEqual(r['verdict'],'fail')

    def test_e10_parent_input_mutation_is_fail_and_does_not_mutate_caller(self):
        p,ex=deepcopy(self.cases['E01-text']); before=raw(p)
        def changed(intake,proposal,sources):
            result=build_intake_test_intent_review(intake,proposal,sources)
            proposal['as_of']=None
            return result
        with patch.object(api,'build_intake_test_intent_review',side_effect=changed):
            r=api.evaluate_intake_test_intent_case(**p,expectation=ex)
        self.assertEqual(r['verdict'],'fail'); self.assertIn('input_changed',r['reason_codes'])
        self.assertFalse(r['verification']['input_values_unchanged']); self.assertEqual(raw(p),before)

    def test_unexpected_exception_has_fixed_code_without_source_context(self):
        p,ex=self.cases['E01-text']
        with patch.object(api,'build_intake_test_intent_review',side_effect=RuntimeError('PRIVATE-CANARY')):
            self.fixed_error('source_error',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))

    def fixed_error(self,code,call):
        with self.assertRaises(api.IntakeTestIntentEvaluationError) as caught: call()
        error=caught.exception; expected='intake_test_intent_evaluation_'+code
        self.assertEqual((error.code,str(error),error.args),(expected,expected,(expected,)))
        self.assertIsNone(error.__context__); self.assertIsNone(error.__cause__)

    def test_invalid_expectation_shapes_types_and_unsorted_reasons(self):
        p,base=self.cases['E01-text']
        mutations=[lambda e:e.update(extra=True),lambda e:e.update(schema_version=True),lambda e:e.update(case_id='bad/id'),
            lambda e:e.update(input_sha256='BAD'),lambda e:e.update(label_review_status='approved'),
            lambda e:e.update(expected=None),lambda e:e['expected'].update(outcome='returned',error_code='test_intent_source_error'),
            lambda e:e['expected']['review']['reason_codes'].reverse(),
            lambda e:e['expected']['review']['fields']['rule']['candidates'][0].update(literal_linked=1),
            lambda e:e['expected']['review']['fields']['rule']['candidates'].clear()]
        for change in mutations:
            ex=deepcopy(base); change(ex)
            with patch.object(api,'build_intake_test_intent_review') as parent:
                self.fixed_error('invalid_input',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))
            parent.assert_not_called()

    def test_native_json_cycles_surrogates_nonfinite_and_subclasses(self):
        p,ex=self.cases['E01-text']
        class Bad(dict): pass
        cycle=[]; cycle.append(cycle)
        for unsafe in (Bad(),cycle,'\ud800',float('nan'),float('inf'),10**5000):
            data=deepcopy(p); data['sources']=unsafe
            self.fixed_error('invalid_input',lambda:api.evaluate_intake_test_intent_case(**data,expectation=ex))

    def test_byte_depth_and_node_budgets_precede_semantic_validation(self):
        p,ex=self.cases['E01-text']
        data=deepcopy(p); data['proposal']='x'*(48*1024*1024)
        self.fixed_error('limit_exceeded',lambda:api.evaluate_intake_test_intent_case(**data,expectation={}))
        huge={'wrong':'x'*(256*1024)}
        self.fixed_error('limit_exceeded',lambda:api.evaluate_intake_test_intent_case(**p,expectation=huge))
        nested=None
        for _ in range(41): nested=[nested]
        data=deepcopy(p); data['sources']=nested
        self.fixed_error('limit_exceeded',lambda:api.evaluate_intake_test_intent_case(**data,expectation=ex))
        data=deepcopy(p); data['sources']=[None]*2100000
        self.fixed_error('limit_exceeded',lambda:api.evaluate_intake_test_intent_case(**data,expectation=ex))

    def test_no_evaluation_io_or_parser_and_oracle_not_passed_to_parent(self):
        p,ex=self.cases['E01-pdf']
        with ExitStack() as stack:
            for target in ('builtins.open','socket.socket','sqlite3.connect','subprocess.Popen','labflow.document_extract.extract_document'):
                stack.enter_context(patch(target,side_effect=AssertionError('Unexpected evaluator I/O')))
            parent=stack.enter_context(patch.object(api,'build_intake_test_intent_review',wraps=build_intake_test_intent_review))
            r=api.evaluate_intake_test_intent_case(**p,expectation=ex)
        self.assertEqual(r['verdict'],'pass'); self.assertEqual(len(parent.call_args.args),3)
        self.assertEqual(parent.call_args.kwargs,{})

    def test_deterministic_detached_receipt_hashes_without_private_payload(self):
        p,ex=deepcopy(self.cases['E01-text']); before=raw([p,ex])
        r=api.evaluate_intake_test_intent_case(**p,expectation=ex)
        self.assertEqual(r,api.evaluate_intake_test_intent_case(**p,expectation=ex))
        self.assertEqual(r['bindings']['input_sha256'],sha(p)); self.assertEqual(r['bindings']['expectation_sha256'],sha(ex))
        self.assertNotIn(b'SYN-RULE-ELM',raw(r)); self.assertNotIn(b'Keep both model',raw(r))
        r['declarations']['proposal_origins'].append('mutated')
        self.assertEqual(raw([p,ex]),before)

    def test_zero_checks_null_basis_and_all_reference_requirements(self):
        for name in additional_oracle_cases():
            with self.subTest(name=name): self.assertEqual(self.run_case(name)['verdict'],'pass')

    def test_actual_parent_error_code_and_outcome_mismatches_fail(self):
        for name,expected in [('E08-index',dict(outcome='error',error_code='test_intent_source_error',review=None)),
                              ('E08-sha',dict(outcome='returned',error_code=None,review=expected_review())),
                              ('E01-text',dict(outcome='error',error_code='test_intent_invalid_input',review=None))]:
            p,ex=deepcopy(self.cases[name]); ex['expected']=expected
            r=api.evaluate_intake_test_intent_case(**p,expectation=ex)
            self.assertEqual((r['status'],r['verdict']),('checked','fail'))
            self.assertIn('outcome_mismatch',r['reason_codes']); self.assertEqual(r['counts']['review_api_calls'],1)

    def test_reason_id_and_output_limits_do_not_turn_into_passes(self):
        p,ex=deepcopy(self.cases['E01-text']); ex['case_id']='I'*128
        self.assertEqual(api.evaluate_intake_test_intent_case(**p,expectation=ex)['verdict'],'pass')
        ex['case_id']='I'*129
        self.fixed_error('invalid_input',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))
        for reasons in (['R'*129],['R'+str(i).zfill(3) for i in range(513)]):
            ex=deepcopy(self.cases['E01-text'][1]); ex['expected']['review']['reason_codes']=reasons
            self.fixed_error('limit_exceeded',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))
        ex=deepcopy(self.cases['E01-text'][1])
        with patch.dict(api._LIMITS, max_output_bytes=1):
            self.fixed_error('limit_exceeded',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))

    def test_malformed_parent_json_and_sensitive_exception_are_fixed_failures(self):
        p,ex=self.cases['E01-text']
        class Bad(dict): pass
        for result in (Bad(), {'quote':'SECRET'*(400000)}, {'bad':float('nan')}):
            with patch.object(api,'build_intake_test_intent_review',return_value=result):
                self.fixed_error('source_error',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))

    def test_pending_invalid_oracle_is_not_accepted_as_missing_labels(self):
        p,ex=deepcopy(self.cases['E09-pending']); ex['expected']={'outcome':'error','error_code':'test_intent_invalid_input','review':None}
        with patch.object(api,'build_intake_test_intent_review') as parent:
            self.fixed_error('invalid_input',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))
        parent.assert_not_called()

    def test_unsafe_object_type_does_not_execute_metaclass_comparison(self):
        p,ex=deepcopy(self.cases['E01-text']); touched=[]
        class Meta(type):
            def __eq__(cls,other):
                touched.append('comparison')
                raise AssertionError('Object hooks must not run')
        class Unsafe(metaclass=Meta): pass
        p['sources']=Unsafe()
        self.fixed_error('invalid_input',lambda:api.evaluate_intake_test_intent_case(**p,expectation=ex))
        self.assertEqual(touched,[])


if __name__=='__main__': unittest.main()
