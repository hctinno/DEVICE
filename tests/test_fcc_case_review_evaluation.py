"""Synthetic reference fixtures only; no actual model or equipment evaluation."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import fcc_case_review_evaluation as gate
from labflow.fcc_case_evaluation import build_case_evaluation_split
from labflow.fcc_case_review import build_case_review_context, decode_case_review_response
from labflow.fcc_report_cases import FccReportCaseCatalog
from labflow.document_extract import extract_document, page_citation
from tests.test_document_extract import synthetic_pdf
from tests.test_fcc_case_review import QUERY, PRODUCER, first_ref, wire
from tests.test_fcc_report_cases import fixture


CASE_FIELDS={'case_id','product_family_group_id','fcc_ids','report_group_id','original_sha256s',
             'reuse_group_ids','group_review_status','unresolved_relations'}
OUTPUT={'schema_version','kind','execution_mode','status','reason_codes','synthetic','bindings','exposure',
        'label_review_status','score','actual_model_score','counts','reference_differences','verification','limits'}
FALSE_FLAGS={'source_facts_reverified','group_facts_reverified','label_correctness_verified','model_execution_verified',
             'model_quality_verified','independent_evaluation_approved','training_executed','evaluation_executed',
             'hardware_verified','physical_verified'}


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def rehash(context):
    context['context_id']=hashlib.sha256(encoded({k:v for k,v in context.items() if k!='context_id'})).hexdigest()


def references(context):
    result=[]
    for case in context['cases']:
        for claim in case['claims']:
            if claim['selectable']:
                for evidence in claim['evidence']:
                    result.append({'case_id':case['case_id'],'claim_id':claim['claim_id'],**{k:evidence[k] for k in
                        ['evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end']}})
    return result


def inputs(*,two=False,shared=False,synthetic=True,long_values=False):
    packet,sources,_=fixture();packet['scope']['synthetic']=synthetic
    if long_values:
        next(c for c in packet['cases'][0]['claims'] if c['field']=='product.models')['value'] += ['MODEL-'+str(i) for i in range(300)]
        next(c for c in packet['cases'][0]['claims'] if c['field']=='report.number')['value']='SYN-'+('x'*1000)
    if two:
        second=deepcopy(packet['cases'][0]);second['case_id']='CASE-B';second['report_group_id']='REPORT-GROUP-B'
        if not shared:
            lines=[c['evidence'][0]['quote'] for c in second['claims']]
            values={'report.number':'SYN-002','product.family':'sensor_node_b','product.models':['MODEL-B'],'report.fcc_ids':['SYN-BB']}
            for index,text in [(0,'SYNTHETIC REPORT: SYN-002'),(5,'Product sensor_node_b'),(7,'Model MODEL-B'),(10,'FCC ID SYN-BB')]:lines[index]=text
            payload=synthetic_pdf(['\n'.join(lines),'Secondary synthetic page'])
            sha=hashlib.sha256(payload).hexdigest();sources[sha]=payload
            extracted=extract_document(payload,'DOC-B.pdf')
            for claim in second['claims']:
                if claim['field'] in values:claim['value']=values[claim['field']]
                for evidence in claim['evidence']:
                    citation=page_citation(extracted,evidence['file_page'],evidence['line_start'],evidence['line_end'])
                    evidence.update(document_id='DOC-B',source_sha256=sha,text_sha256=citation['text_sha256'],quote=citation['quote'])
            document=deepcopy(packet['documents'][0]);document.update(document_id='DOC-B',sha256=sha,size_bytes=len(payload))
            document['exhibits'][0].update(exhibit_id='EX-B',fcc_id='SYN-BB')
            packet['documents'].append(document);second['document_ids']=['DOC-B'];second['reuse_group_ids']=['REUSE-B']
        packet['cases'].append(second)
    catalog=FccReportCaseCatalog(packet,sources)
    context=build_case_review_context(catalog,query=QUERY,case_ids=['CASE-A'])
    metadata=[]
    docs={d['document_id']:d['sha256'] for d in packet['documents']}
    for case in packet['cases']:
        second=case['case_id']=='CASE-B' and not shared
        metadata.append({'case_id':case['case_id'],'product_family_group_id':'synthetic-canonical-b' if second else 'synthetic-canonical-a',
            'fcc_ids':['SYN-BB' if second else 'SYN-AA'],'report_group_id':case['report_group_id'],
            'original_sha256s':[docs[d] for d in case['document_ids']],'reuse_group_ids':case['reuse_group_ids'],
            'group_review_status':'reviewed','unresolved_relations':[]})
    split=build_case_evaluation_split(metadata,development_case_ids=[],independent_case_ids=[c['case_id'] for c in metadata])
    validated=decode_case_review_response(json.dumps(wire(context)),context,producer_name=PRODUCER)
    expectation={'schema_version':1,'kind':'fcc_case_review_expectation','context_id':context['context_id'],
                 'label_review_status':'reviewed','references':[first_ref(context)]}
    return [split,context,validated,expectation]


class FccCaseReviewEvaluationTests(unittest.TestCase):
    def setUp(self):self.args=inputs()

    def run_gate(self,args=None,**kwargs):
        s,c,r,e=self.args if args is None else args
        return gate.evaluate_case_review_references(s,c,r,expectation=e,producer_name=kwargs.pop('producer_name',PRODUCER),**kwargs)

    def insufficient(self,args,reason):
        result=self.run_gate(args)
        self.assertEqual(result['status'],'insufficient_evidence');self.assertIsNone(result['score'])
        self.assertIn(reason,result['reason_codes']);self.assertIsNone(result['actual_model_score'])
        self.assertEqual(result['counts']['scored_fixture_checks'],0);self.assertEqual(result['counts']['actual_model_checks'],0)
        self.assertTrue(all(result['counts'][k] is None for k in ['expected_references','observed_references','matched_references','missing_references','unexpected_references']))
        self.assertEqual(result['reference_differences'],{'missing':[],'unexpected':[]})
        self.assertFalse(result['verification']['fixture_reference_check_executed'])
        for flag in FALSE_FLAGS:self.assertIs(result['verification'][flag],False)
        return result

    def error(self,code,operation):
        with self.assertRaises(gate.FccCaseReviewEvaluationError) as caught:operation()
        error=caught.exception;expected='fcc_case_review_evaluation_'+code
        self.assertEqual((str(error),error.code,error.args),(expected,expected,(expected,)))
        self.assertIsNone(error.__context__);self.assertNotIn('PRIVATE-SYNTHETIC',repr(error))

    def resplit(self,args,*,dev=(),ind=(),change=None):
        rows=[{k:v for k,v in c.items() if k in CASE_FIELDS} for c in args[0]['cases']]
        if change:change(rows)
        args[0]=build_case_evaluation_split(rows,development_case_ids=list(dev),independent_case_ids=list(ind))

    def rebind(self,args):
        rehash(args[1]);args[2]=decode_case_review_response(json.dumps(wire(args[1])),args[1],producer_name=PRODUCER)
        args[3]['context_id']=args[1]['context_id'];args[3]['references']=[first_ref(args[1])]

    def test_exact_contract_and_true_flags_are_only_local_checks(self):
        r=self.run_gate();self.assertEqual(set(r),OUTPUT)
        self.assertEqual((r['kind'],r['execution_mode'],r['status'],r['score']),('fcc_case_review_reference_check','fixture_reference_check','checked',1))
        self.assertEqual(r['reason_codes'],[]);self.assertIs(r['synthetic'],True);self.assertIsNone(r['actual_model_score'])
        self.assertEqual(len(r['bindings']),8);self.assertEqual(len(r['exposure']),4)
        self.assertEqual(len(r['verification']),16);self.assertEqual(len(r['limits']),14);self.assertEqual(len(r['counts']),7)
        self.assertEqual(r['counts'],{'expected_references':1,'observed_references':1,'matched_references':1,'missing_references':0,'unexpected_references':0,'scored_fixture_checks':1,'actual_model_checks':0})
        for k,v in r['verification'].items():self.assertIs(v,k not in FALSE_FLAGS)

    def test_valid_different_reference_is_zero_and_retains_exact_differences(self):
        self.args[3]['references']=[references(self.args[1])[1]]
        r=self.run_gate();self.assertEqual(r['score'],0)
        self.assertEqual(r['reference_differences']['missing'],self.args[3]['references'])
        self.assertEqual(r['reference_differences']['unexpected'],self.args[2]['references'])

    def test_reference_order_is_irrelevant_but_all_nine_keys_bind(self):
        refs=references(self.args[1])[:2];self.args[3]['references']=refs
        self.args[2]=decode_case_review_response(json.dumps(wire(self.args[1],list(reversed(refs)))),self.args[1],producer_name=PRODUCER)
        self.assertEqual(self.run_gate()['score'],1)

    def test_valid_conservative_abstention_is_fixture_mismatch(self):
        self.args[2]=decode_case_review_response(json.dumps(wire(self.args[1],[],status='insufficient_evidence',reasons=['additional_evidence_required'])),self.args[1],producer_name=PRODUCER)
        r=self.run_gate();self.assertEqual(r['score'],0);self.assertEqual(r['counts']['missing_references'],1)

    def test_full_shared_component_with_unselected_preview_can_be_checked(self):
        r=self.run_gate(inputs(two=True,shared=True));self.assertEqual(r['score'],1)
        self.assertEqual(r['exposure']['case_ids'],['CASE-A','CASE-B'])

    def test_unselected_development_preview_blocks_score(self):
        args=inputs(two=True);self.resplit(args,dev=['CASE-B'],ind=['CASE-A'])
        self.insufficient(args,'development_case_exposed')

    def test_unselected_unassigned_preview_blocks_score(self):
        args=inputs(two=True);self.resplit(args,ind=['CASE-A']);self.insufficient(args,'unassigned_case_exposed')

    def test_unselected_pending_component_blocks_score(self):
        args=inputs(two=True)
        self.resplit(args,ind=['CASE-A'],change=lambda rows:rows[1].update(group_review_status='pending'))
        self.insufficient(args,'ineligible_component_exposed')

    def test_unknown_preview_case_blocks_score(self):
        args=inputs(two=True);args[0]=self.args[0]
        self.insufficient(args,'unknown_exposed_case')

    def test_each_group_namespace_and_transitive_hidden_case_blocks_partial_exposure(self):
        for namespace in ['product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids']:
            with self.subTest(namespace=namespace):
                args=deepcopy(self.args);a={k:v for k,v in args[0]['cases'][0].items() if k in CASE_FIELDS}
                b=deepcopy(a);b.update(case_id='CASE-B',product_family_group_id='other-family',fcc_ids=['OTHER-B'],
                    report_group_id='other-report',original_sha256s=['b'*64],reuse_group_ids=['other-reuse'])
                b[namespace]=a[namespace]
                c=deepcopy(b);c['case_id']='CASE-C';c['reuse_group_ids']=['transitive'];b['reuse_group_ids']=['transitive']
                if namespace=='reuse_group_ids':b['reuse_group_ids']=a['reuse_group_ids']+['transitive']
                args[0]=build_case_evaluation_split([a,b,c],development_case_ids=[],independent_case_ids=['CASE-A','CASE-B','CASE-C'])
                r=self.insufficient(args,'partial_component_exposure')
                self.assertEqual(r['exposure']['required_component_case_ids'],['CASE-A','CASE-B','CASE-C'])

    def test_document_linked_hidden_case_is_exposed_even_without_preview(self):
        args=deepcopy(self.args);a={k:v for k,v in args[0]['cases'][0].items() if k in CASE_FIELDS};b=deepcopy(a);b['case_id']='CASE-B'
        args[0]=build_case_evaluation_split([a,b],development_case_ids=[],independent_case_ids=['CASE-A','CASE-B'])
        r=self.insufficient(args,'partial_component_exposure');self.assertIn('CASE-B',r['exposure']['document_linked_case_ids'])

    def test_unknown_excluded_candidate_is_exposure(self):
        args=deepcopy(self.args);args[1]['excluded_candidates'].append({'case_id':'UNKNOWN','model_relation':'related_family','reason':'related_model'})
        self.rebind(args);self.insufficient(args,'unknown_exposed_case')

    def test_context_document_without_any_preview_link_is_blocked(self):
        args=deepcopy(self.args);args[1]['documents'].append(inputs(two=True)[1]['documents'][1]);self.rebind(args)
        self.insufficient(args,'unlinked_context_document')

    def test_nonselected_document_source_report_and_fcc_mismatches_block_score(self):
        for field,reason in [('sha','document_source_mismatch'),('report','report_group_mismatch'),('fcc','fcc_id_mismatch')]:
            with self.subTest(field=field):
                args=inputs(two=True)
                if field=='sha':args[1]['documents'][1]['sha256']='c'*64
                elif field=='report':args[1]['case_previews'][1]['report_group_id']='OTHER-REPORT'
                else:args[1]['case_previews'][1]['fcc_ids']=['OTHER-FCC']
                self.rebind(args);self.insufficient(args,reason)

    def test_split_component_and_fingerprint_flags_counts_cannot_be_edited(self):
        for field in ['input_fingerprint','eligible_component_count','fact_review_verified','components','independent']:
            with self.subTest(field=field):
                args=deepcopy(self.args)
                if field=='input_fingerprint':args[0][field]='c'*64
                elif field=='eligible_component_count':args[0][field]=0
                elif field=='fact_review_verified':args[0][field]=True
                elif field=='components':args[0][field][0]['eligible']=False
                else:args[0][field]['case_ids']=[]
                self.insufficient(args,'split_not_consistent')

    def test_partial_or_ineligible_assignment_is_not_trusted_from_split(self):
        args=inputs(two=True,shared=True);args[0]['independent']['case_ids']=['CASE-A']
        self.insufficient(args,'split_not_consistent')
        args=deepcopy(self.args);args[0]['cases'][0]['group_review_status']='pending'
        self.insufficient(args,'split_not_consistent')

    def test_pending_and_empty_expected_labels_do_not_create_answers(self):
        for pending in [True,False]:
            args=deepcopy(self.args);args[3].update(label_review_status='pending' if pending else 'reviewed',references=None if pending else [])
            self.insufficient(args,'label_review_pending' if pending else 'expected_references_missing')

    def test_expectation_context_and_each_reference_field_are_strict(self):
        args=deepcopy(self.args);args[3]['context_id']='c'*64;self.insufficient(args,'expected_context_mismatch')
        for field in first_ref(self.args[1]):
            with self.subTest(field=field):
                args=deepcopy(self.args);ref=args[3]['references'][0]
                ref[field]=ref[field]+1 if type(ref[field]) is int else 'c'*64 if field.endswith('sha256') or field=='evidence_id' else 'OTHER'
                self.insufficient(args,'expected_references_not_bound')

    def test_duplicate_expectation_and_response_references_are_not_deduplicated(self):
        for pos in [2,3]:
            args=deepcopy(self.args);args[pos]['references']*=2
            self.insufficient(args,'response_not_bound' if pos==2 else 'expected_references_not_bound')

    def test_response_context_corpus_producer_binding_flags_and_ref_must_revalidate(self):
        for field in ['context_id','corpus_id','expected_producer','source_binding','verification','references']:
            with self.subTest(field=field):
                args=deepcopy(self.args)
                if field=='context_id':args[2][field]='d'*64
                elif field=='corpus_id':args[2][field]='OTHER-CORPUS'
                elif field=='expected_producer':args[2][field]['name']='OTHER'
                elif field=='source_binding':args[2][field]['summary_sha256']='d'*64
                elif field=='verification':args[2][field]['model_execution_verified']=True
                else:args[2][field][0]['line_end']+=1
                self.insufficient(args,'response_not_bound')

    def test_context_hash_tampering_is_insufficient_and_cannot_claim_validation(self):
        args=deepcopy(self.args);args[1]['case_previews'][0]['manufacturer']='ALTERED'
        r=self.insufficient(args,'context_not_validated');self.assertIsNone(r['bindings']['context_id'])

    def test_nonsynthetic_context_never_gets_fixture_or_actual_model_score(self):
        self.insufficient(inputs(synthetic=False),'non_synthetic_context')

    def test_nonready_context_does_not_score_empty_expectation(self):
        packet,sources,_=fixture();c=build_case_review_context(FccReportCaseCatalog(packet,sources),query={**QUERY,'method':'OTHER-EDITION'},case_ids=[])
        r=decode_case_review_response(json.dumps(wire(c,[],status='no_candidate',reasons=['no_reviewed_case'])),c,producer_name=PRODUCER)
        args=[self.args[0],c,r,{'schema_version':1,'kind':'fcc_case_review_expectation','context_id':c['context_id'],'label_review_status':'reviewed','references':[]}]
        self.insufficient(args,'context_not_ready')

    def test_long_parent_valid_preview_and_claim_values_remain_accepted(self):
        self.assertEqual(self.run_gate(inputs(long_values=True))['score'],1)

    def test_pure_gate_does_no_file_pdf_socket_process_or_model_io(self):
        with patch('builtins.open',side_effect=AssertionError('IO')),patch.object(Path,'open',side_effect=AssertionError('IO')), \
             patch.object(os,'open',side_effect=AssertionError('IO')), \
             patch.object(socket,'socket',side_effect=AssertionError('IO')),patch.object(subprocess,'Popen',side_effect=AssertionError('IO')), \
             patch('labflow.fcc_report_cases.extract_document',side_effect=AssertionError('PDF')):
            self.assertEqual(self.run_gate()['score'],1)

    def test_input_and_output_are_detached_and_deterministic(self):
        original=deepcopy(self.args);a=self.run_gate();b=self.run_gate();self.assertEqual(encoded(a),encoded(b));self.assertEqual(self.args,original)
        a['exposure']['case_ids'].append('CHANGED');a['bindings']['expected_producer']['name']='CHANGED'
        self.assertEqual(self.args,original);self.assertEqual(self.run_gate(),b)

    def test_four_full_input_hashes_bind_without_copying_private_quotes(self):
        r=self.run_gate()
        for name,value in zip(['split_sha256','context_sha256','response_sha256','expectation_sha256'],self.args):
            self.assertEqual(r['bindings'][name],hashlib.sha256(encoded(value)).hexdigest())
        self.assertNotIn('PRIVATE-SYNTHETIC',encoded(r).decode());self.assertNotIn('quote',encoded(r).decode())

    def test_exact_keys_bad_enums_types_and_unsafe_objects_are_fixed_errors(self):
        for pos,name in enumerate(['split','context','response','expectation']):
            args=deepcopy(self.args);args[pos]['extra']='PRIVATE-SYNTHETIC'
            self.error(name+'_invalid',lambda:self.run_gate(args))
        for value in [Path('private.pdf'),lambda:None,object(),{'schema_version':True}]:
            self.error('split_invalid',lambda:self.run_gate([value,*self.args[1:]]))
        args=deepcopy(self.args);args[3]['label_review_status']='approved';self.error('expectation_invalid',lambda:self.run_gate(args))
        self.error('producer_invalid',lambda:self.run_gate(producer_name=''))

    def test_nonfinite_numbers_and_bool_schema_are_not_success(self):
        for value in [float('nan'),float('inf')]:
            args=deepcopy(self.args);args[0]['case_count']=value;self.error('split_invalid',lambda:self.run_gate(args))
        for pos,name in enumerate(['split','context','response','expectation']):
            args=deepcopy(self.args);args[pos]['schema_version']=True
            self.error(name+'_invalid',lambda:self.run_gate(args))

    def test_parent_reference_budget_excess_is_limit_error_not_insufficient(self):
        for pos in [2,3]:
            args=deepcopy(self.args);args[pos]['references']*=257
            self.error('limit_exceeded',lambda:self.run_gate(args))

    def test_context_byte_and_depth_budgets_reject_before_semantic_parsing(self):
        args=deepcopy(self.args);args[1]['extra']='x'*(8*1024*1024)
        self.error('limit_exceeded',lambda:self.run_gate(args))
        args=deepcopy(self.args);deep=[];args[1]['extra']=deep
        for _ in range(25):child=[];deep.append(child);deep=child
        self.error('limit_exceeded',lambda:self.run_gate(args))

    def test_large_integer_failure_has_no_original_exception_context(self):
        args=deepcopy(self.args);args[0]['case_count']=10**5000
        self.error('split_invalid',lambda:self.run_gate(args))

    def test_exact_256_reference_boundary_uses_genuine_parent_apis(self):
        packet,sources,_=fixture();base=packet['cases'][0]
        for index in range(64-len(base['claims'])):
            claim=deepcopy(base['claims'][-1]);claim.update(claim_id='EXTRA-'+str(index),field='setting.reference'+str(index))
            base['claims'].append(claim)
        packet['cases']=[{**deepcopy(base),'case_id':'CASE-'+str(i)} for i in range(4)]
        catalog=FccReportCaseCatalog(packet,sources);ids=[c['case_id'] for c in packet['cases']]
        c=build_case_review_context(catalog,query=QUERY,case_ids=ids);refs=references(c)
        self.assertEqual(len(refs),256)
        metadata={k:v for k,v in self.args[0]['cases'][0].items() if k in CASE_FIELDS}
        s=build_case_evaluation_split([{**metadata,'case_id':identity} for identity in ids],development_case_ids=[],independent_case_ids=ids)
        r=decode_case_review_response(json.dumps(wire(c,refs)),c,producer_name=PRODUCER)
        e={**self.args[3],'context_id':c['context_id'],'references':list(reversed(refs))}
        result=self.run_gate([s,c,r,e]);self.assertEqual(result['score'],1);self.assertEqual(result['counts']['matched_references'],256)

    def test_parent_split_input_budget_is_not_swallowed_as_inconsistency(self):
        args=deepcopy(self.args);base=args[0]['cases'][0]
        base['reuse_group_ids']=['R'+str(i).zfill(2)+'x'*125 for i in range(64)]
        args[0]['cases']=[{**base,'case_id':'CASE-'+str(i)} for i in range(600)]
        self.error('limit_exceeded',lambda:self.run_gate(args))

    def test_aggregate_node_budget_rejects_bounded_byte_payload(self):
        args=deepcopy(self.args);args[0]['extra']=[0]*4500000
        self.error('limit_exceeded',lambda:self.run_gate(args))


if __name__=='__main__':unittest.main()
