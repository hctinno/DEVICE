"""Synthetic intake snapshots and report references; no live Store or model."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import intake_case_references as receipt
from labflow.fcc_report_cases import FccReportCaseCatalog
from labflow.fcc_case_review import build_case_review_context,decode_case_review_response
from labflow.document_extract import extract_document,page_citation
from labflow.intake_analysis import validate_analysis,project_analysis
from tests.test_fcc_report_cases import fixture
from tests.test_fcc_case_review import QUERY,PRODUCER,first_ref,wire
from tests.test_document_extract import synthetic_pdf


def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()


def snapshot(*,family='sensor_node',market='FCC',model='MODEL-A'):
    values={'product_type':family,'market':market,'model':model,'purpose':'development fixture'}
    text='\n'.join(k+': '+v for k,v in values.items());sha=hashlib.sha256(text.encode()).hexdigest()
    document={'path':'request.txt','sha256':sha,'text':text,'format':'text','parse_status':'text'}
    analysis={'schema_version':1,'producer':{'kind':'fixture','name':'synthetic-intake032'},'identity':'single','missing_fields':[],
        'facts':[{'field':k,'value':v,'status':'explicit','evidence':[{'path':'request.txt','sha256':sha,
            'line_start':i,'line_end':i,'quote':k+': '+v,'role':'request'}]} for i,(k,v) in enumerate(values.items(),1)]}
    unread=validate_analysis(analysis,[document],True)
    projected=project_analysis(analysis,unread,{},delegated=True,deferred=False)
    projection={'facts':{k:v for k,v in projected['facts'].items() if k in {'product_type','market','model'}},
                'questions':[{'key':q['key']} for q in projected['questions']]}
    return {'schema_version':1,'kind':'intake_case_reference_snapshot','snapshot_scope':'caller_provided',
        'intake_id':'INTAKE-A','revision':1,'revision_fingerprint':sha,'origin_job_id':'JOB-A',
        'analysis_context_id':digest([document]),'result_sha256':digest({'submission':analysis,'summary':projected}),
        'readiness_fingerprint':None,'synthetic':True,'projection':projection,'projection_sha256':digest(projection)}


def catalog_fixture(*,two=False,shared=False,synthetic=True,long_values=False):
    packet,sources,_=fixture();packet['scope']['synthetic']=synthetic
    if long_values:
        next(x for x in packet['cases'][0]['claims'] if x['field']=='product.models')['value'] += ['MODEL-'+str(i) for i in range(300)]
        next(x for x in packet['cases'][0]['claims'] if x['field']=='report.number')['value']='SYN-'+('x'*1000)
    if two:
        case=deepcopy(packet['cases'][0]);case.update(case_id='CASE-B',report_group_id='REPORT-GROUP-B')
        if not shared:
            lines=[x['evidence'][0]['quote'] for x in case['claims']];lines[7]='Model MODEL-B';lines[0]='SYNTHETIC REPORT: SYN-002'
            data=synthetic_pdf(['\n'.join(lines),'Other synthetic page']);sha=hashlib.sha256(data).hexdigest()
            parsed=extract_document(data,'DOC-B.pdf');sources[sha]=data
            for claim in case['claims']:
                if claim['field']=='product.models':claim['value']=['MODEL-B']
                if claim['field']=='report.number':claim['value']='SYN-002'
                for evidence in claim['evidence']:
                    quoted=page_citation(parsed,1,evidence['line_start'],evidence['line_end'])
                    evidence.update(document_id='DOC-B',source_sha256=sha,text_sha256=quoted['text_sha256'],quote=quoted['quote'])
            document=deepcopy(packet['documents'][0]);document.update(document_id='DOC-B',sha256=sha,size_bytes=len(data))
            document['exhibits'][0]['exhibit_id']='EX-B';packet['documents'].append(document);case['document_ids']=['DOC-B']
        packet['cases'].append(case)
    return FccReportCaseCatalog(packet,sources)


def context_for(catalog,*,query=None,ids=None):
    return build_case_review_context(catalog,query=QUERY if query is None else query,case_ids=['CASE-A'] if ids is None else ids)


def response_for(context,*,refs=None,status='selected',reasons=None):
    return decode_case_review_response(json.dumps(wire(context,refs,status=status,reasons=reasons)),context,producer_name=PRODUCER)


OUTPUT={'schema_version','kind','receipt_id','execution_mode','status','reason_codes','intake_binding','case_binding',
        'intake_match','reference_selection','case_states','evaluation','verification','limits'}
ALWAYS_FALSE={'source_facts_reverified','result_projection_reverified','database_currentness_verified','operational_authority_granted',
    'model_execution_verified','model_quality_verified','independent_evaluation_approved','training_executed','evaluation_executed','hardware_verified','physical_verified'}
EVALUATION={'status':'not_executed','score':None,'actual_model_score':None,'scored_fixture_checks':0,
            'actual_model_checks':0,'independent_assignment_status':'not_assessed'}
CORE=['intake_id','revision','revision_fingerprint','origin_job_id','analysis_context_id','result_sha256','synthetic']


class IntakeCaseReferenceTests(unittest.TestCase):
    def setUp(self):
        self.s=snapshot();self.catalog=catalog_fixture();self.c=context_for(self.catalog);self.r=response_for(self.c)

    def call(self,s=None,catalog=None,c=None,r=None,**kwargs):
        return receipt.build_intake_case_reference_receipt(self.s if s is None else s,self.catalog if catalog is None else catalog,
            self.c if c is None else c,self.r if r is None else r,producer_name=kwargs.pop('producer_name',PRODUCER),**kwargs)

    def hold(self,reason,**kwargs):
        result=self.call(**kwargs);self.assertEqual(result['status'],'insufficient_evidence');self.assertIn(reason,result['reason_codes'])
        self.assertEqual(result['reference_selection']['accepted_references'],[]);self.assertEqual(result['evaluation'],EVALUATION)
        for key in ALWAYS_FALSE:self.assertIs(result['verification'][key],False)
        return result

    def error(self,code,operation):
        with self.assertRaises(receipt.IntakeCaseReferencesError) as caught:operation()
        e=caught.exception;expected='intake_case_references_'+code
        self.assertEqual((e.code,str(e),e.args),(expected,expected,(expected,)));self.assertIsNone(e.__context__)
        self.assertNotIn('PRIVATE-SYNTHETIC',repr(e))

    def edit_projection(self,s):s['projection_sha256']=digest(s['projection'])

    def test_exact_contract_selected_and_constant_authority_evaluation(self):
        x=self.call();self.assertEqual(set(x),OUTPUT);self.assertEqual(x['status'],'bound')
        self.assertEqual(x['kind'],'intake_case_reference_receipt');self.assertEqual(x['execution_mode'],'provided_snapshot_read_only')
        for key,count in [('intake_binding',11),('case_binding',10),('intake_match',5),('reference_selection',5),('verification',18),('limits',16)]:self.assertEqual(len(x[key]),count)
        self.assertEqual(x['evaluation'],EVALUATION);self.assertEqual(x['reference_selection']['status'],'selected')
        self.assertEqual(x['reference_selection']['accepted_references'],self.r['references'])
        self.assertEqual(x['receipt_id'],digest({k:v for k,v in x.items() if k!='receipt_id'}))
        for key,value in x['verification'].items():self.assertIs(value,key not in ALWAYS_FALSE)

    def test_each_null_core_is_explicit_incomplete_not_an_invented_origin(self):
        for key in CORE:
            with self.subTest(key=key):
                s=deepcopy(self.s);s[key]=None;x=self.hold('snapshot_binding_incomplete',s=s)
                self.assertEqual(x['intake_binding']['missing_fields'],[key]);self.assertIsNone(x['intake_binding'][key])

    def test_empty_snapshot_is_insufficient_while_source_selected_is_preserved(self):
        s=deepcopy(self.s)
        for key in CORE:s[key]=None
        s['projection']={'facts':{},'questions':[]};self.edit_projection(s)
        x=self.hold('snapshot_binding_incomplete',s=s)
        self.assertEqual(x['reference_selection']['source_response_status'],'selected')
        self.assertEqual(x['reference_selection']['status'],'unknown');self.assertIn('intake_product_unconfirmed',x['intake_match']['reason_codes'])

    def test_projection_hash_mismatch_does_not_run_intake_match(self):
        s=deepcopy(self.s);s['projection_sha256']='f'*64
        x=self.hold('projection_hash_mismatch',s=s);self.assertEqual(x['intake_match']['status'],'not_assessed')

    def test_origin_ids_150_are_valid_but_never_prove_currentness(self):
        s=deepcopy(self.s);s['intake_id']='I'*150;s['origin_job_id']='J'*150
        x=self.call(s=s);self.assertEqual(x['status'],'bound');self.assertFalse(x['verification']['database_currentness_verified'])
        s['intake_id']+='X';self.error('snapshot_invalid',lambda:self.call(s=s))

    def test_different_declared_revision_result_and_readiness_make_new_receipt(self):
        before=self.call()
        for key,value in [('revision',2),('result_sha256','b'*64),('readiness_fingerprint','c'*64)]:
            s=deepcopy(self.s);s[key]=value;x=self.call(s=s)
            self.assertEqual(x['status'],'bound');self.assertNotEqual(x['receipt_id'],before['receipt_id'])
            self.assertFalse(x['verification']['result_projection_reverified']);self.assertFalse(x['verification']['database_currentness_verified'])

    def test_non_us_market_and_conflicting_product_or_model_preserve_parent_reasons(self):
        for field,value,reason in [('market','EU','intake_market_not_fcc'),('product_type','other_product','intake_product_conflict'),('model','MODEL-B','intake_model_conflict')]:
            s=deepcopy(self.s);s['projection']['facts'][field]['value']=value;self.edit_projection(s)
            x=self.hold('intake_query_insufficient',s=s);self.assertIn(reason,x['intake_match']['reason_codes'])

    def test_inferred_uncertain_missing_and_identity_question_are_unconfirmed(self):
        for kind in ['inferred','uncertain','missing','identity']:
            s=deepcopy(self.s)
            if kind=='identity':s['projection']['questions']=[{'key':'product_identity'}]
            elif kind=='missing':del s['projection']['facts']['model']
            else:s['projection']['facts']['model']['status']=kind
            self.edit_projection(s);self.hold('intake_query_insufficient',s=s)

    def test_user_confirmed_event_is_required_and_preserved_only_as_status(self):
        s=deepcopy(self.s);s['projection']['facts']['model'].update(status='user_confirmed',event_id='EVENT-A');self.edit_projection(s)
        x=self.call(s=s);self.assertEqual(x['status'],'bound');self.assertEqual(x['intake_match']['fact_statuses']['model'],'user_confirmed')
        self.assertNotIn('EVENT-A',encoded(x).decode())
        del s['projection']['facts']['model']['event_id'];self.edit_projection(s);self.error('snapshot_invalid',lambda:self.call(s=s))

    def test_model_none_uses_intake_model_and_rejects_selected_related_case(self):
        catalog=catalog_fixture(two=True);c=context_for(catalog,query={**QUERY,'model':None},ids=['CASE-A','CASE-B'])
        r=response_for(c,refs=[first_ref(c,case_index=1)])
        x=self.hold('selected_reference_outside_intake_scope',catalog=catalog,c=c,r=r)
        b=next(v for v in x['case_states'] if v['case_id']=='CASE-B')
        self.assertEqual((b['context_model_relation'],b['intake_model_relation']),('unspecified','related_family'))
        self.assertEqual(b['selection_status'],'outside_intake_scope');self.assertIn('related_model',b['reason_codes'])

    def test_model_none_related_unselected_detail_does_not_block_correct_reference(self):
        catalog=catalog_fixture(two=True);c=context_for(catalog,query={**QUERY,'model':None},ids=['CASE-A','CASE-B']);r=response_for(c)
        x=self.call(catalog=catalog,c=c,r=r);self.assertEqual(x['status'],'bound')
        b=next(v for v in x['case_states'] if v['case_id']=='CASE-B');self.assertEqual(b['selection_status'],'outside_intake_scope')

    def test_model_absent_in_both_query_and_intake_stays_unspecified(self):
        c=context_for(self.catalog,query={**QUERY,'model':None});r=response_for(c);s=deepcopy(self.s)
        del s['projection']['facts']['model'];self.edit_projection(s)
        x=self.call(s=s,c=c,r=r);self.assertEqual(x['status'],'bound');self.assertEqual(x['case_states'][0]['intake_model_relation'],'unspecified')

    def test_partial_outside_scope_reference_set_is_not_silently_filtered(self):
        catalog=catalog_fixture(two=True);c=context_for(catalog,query={**QUERY,'model':None},ids=['CASE-A','CASE-B'])
        r=response_for(c,refs=[first_ref(c),first_ref(c,case_index=1)])
        x=self.hold('selected_reference_outside_intake_scope',catalog=catalog,c=c,r=r)
        self.assertEqual(x['reference_selection']['reported_reference_count'],2)

    def test_context_not_selected_is_caller_scope_and_response_absence_is_separate(self):
        catalog=catalog_fixture(two=True,shared=True);c=context_for(catalog);r=response_for(c)
        x=self.call(catalog=catalog,c=c,r=r);b=x['case_states'][1]
        self.assertEqual((b['context_inclusion'],b['context_exclusion_reason'],b['response_membership'],b['selection_status']),('preview_only','not_selected','not_referenced','unknown'))
        c=context_for(catalog,ids=['CASE-A','CASE-B']);r=response_for(c);x=self.call(catalog=catalog,c=c,r=r);b=x['case_states'][1]
        self.assertEqual(b['selection_status'],'not_selected_in_response');self.assertEqual(b['context_inclusion'],'detailed')

    def test_parent_related_exclusion_reason_is_preserved(self):
        catalog=catalog_fixture(two=True);c=context_for(catalog);x=self.call(catalog=catalog,c=c,r=response_for(c))
        b=x['case_states'][1];self.assertEqual(b['context_exclusion_reason'],'related_model');self.assertEqual(b['intake_model_relation'],'related_family')

    def test_valid_abstention_is_bound_but_unknown_and_not_response_rejection(self):
        r=response_for(self.c,refs=[],status='insufficient_evidence',reasons=['additional_evidence_required']);x=self.call(r=r)
        self.assertEqual(x['status'],'bound');self.assertEqual(x['reference_selection']['status'],'unknown')
        self.assertEqual(x['case_states'][0]['response_membership'],'not_assessed')

    def test_no_candidate_is_valid_provided_scope_absence_not_global_failure(self):
        c=context_for(self.catalog,query={**QUERY,'method':'OTHER-EDITION'},ids=[])
        r=response_for(c,refs=[],status='no_candidate',reasons=['no_reviewed_case']);x=self.call(c=c,r=r)
        self.assertEqual(x['status'],'bound');self.assertEqual(x['reference_selection']['status'],'no_candidate')
        self.assertEqual(x['intake_match']['status'],'no_match');self.assertEqual(x['evaluation'],EVALUATION)

    def test_no_requested_details_is_not_model_rejection(self):
        c=context_for(self.catalog,ids=[]);r=response_for(c,refs=[],status='insufficient_evidence',reasons=['no_selected_cases'])
        x=self.call(c=c,r=r);self.assertEqual(x['status'],'bound');self.assertEqual(x['case_states'][0]['selection_status'],'unknown')

    def test_context_full_preview_hash_metadata_or_other_catalog_mismatch_holds(self):
        for field in ['context_id','case_previews','source_binding']:
            c=deepcopy(self.c)
            if field=='context_id':c[field]='d'*64
            elif field=='case_previews':c[field][0]['manufacturer']='ALTERED'
            else:c[field]['summary_sha256']='d'*64
            x=self.hold('case_context_mismatch',c=c);self.assertEqual(x['case_states'],[]);self.assertIsNone(x['case_binding']['context_id'])
        self.hold('case_context_mismatch',catalog=catalog_fixture(two=True))

    def test_each_response_reference_field_and_metadata_binding_are_revalidated(self):
        for key in first_ref(self.c):
            r=deepcopy(self.r);v=r['references'][0][key];r['references'][0][key]=v+1 if type(v) is int else 'f'*64 if key.endswith('sha256') or key=='evidence_id' else 'OTHER'
            self.hold('case_response_not_bound',r=r)
        for key in ['corpus_id','source_binding','verification','expected_producer']:
            r=deepcopy(self.r)
            if key=='corpus_id':r[key]='OTHER'
            elif key=='source_binding':r[key]['summary_sha256']='e'*64
            elif key=='verification':r[key]['model_execution_verified']=True
            else:r[key]['name']='OTHER'
            self.hold('case_response_not_bound',r=r)

    def test_duplicate_response_refs_are_not_deduplicated(self):
        r=deepcopy(self.r);r['references']*=2;self.hold('case_response_not_bound',r=r)

    def test_mixed_actual_catalog_and_synthetic_intake_keep_separate_flags(self):
        catalog=catalog_fixture(synthetic=False);c=context_for(catalog);x=self.call(catalog=catalog,c=c,r=response_for(c))
        self.assertEqual(x['status'],'bound');self.assertTrue(x['intake_binding']['synthetic']);self.assertFalse(x['case_binding']['catalog_synthetic'])

    def test_long_parent_values_and_questions_are_not_arbitrarily_shortened(self):
        catalog=catalog_fixture(long_values=True);c=context_for(catalog);s=deepcopy(self.s)
        s['projection']['questions']=[{'key':'x'*300000}];self.edit_projection(s)
        self.assertEqual(self.call(s=s,catalog=catalog,c=c,r=response_for(c))['status'],'bound')

    def test_output_contains_no_quote_fact_value_message_basis_or_token(self):
        text=encoded(self.call()).decode()
        for private in ['PRIVATE-SYNTHETIC','sensor_node','MODEL-A','request.txt','value','quote','basis','token']:
            self.assertNotIn(private,text)

    def test_every_binding_hash_is_detached_and_receipt_is_deterministic(self):
        before=deepcopy([self.s,self.c,self.r]);a=self.call();b=self.call();self.assertEqual(a,b)
        self.assertEqual(a['intake_binding']['snapshot_sha256'],digest(self.s));self.assertEqual(a['case_binding']['provided_context_sha256'],digest(self.c))
        self.assertEqual(a['case_binding']['provided_response_sha256'],digest(self.r))
        a['case_states'][0]['case_id']='CHANGED';a['reference_selection']['accepted_references'][0]['case_id']='CHANGED'
        self.assertEqual([self.s,self.c,self.r],before);self.assertEqual(self.call(),b)

    def test_no_file_pdf_db_worker_socket_process_model_or_store_io(self):
        with patch('builtins.open',side_effect=AssertionError('IO')),patch.object(Path,'open',side_effect=AssertionError('IO')), \
             patch.object(os,'open',side_effect=AssertionError('IO')),patch.object(socket,'socket',side_effect=AssertionError('IO')), \
             patch.object(subprocess,'Popen',side_effect=AssertionError('IO')),patch('labflow.fcc_report_cases.extract_document',side_effect=AssertionError('PDF')), \
             patch('labflow.store.Store.__init__',side_effect=AssertionError('Store')),patch('labflow.intake_jobs.complete_job',side_effect=AssertionError('worker')):
            self.assertEqual(self.call()['status'],'bound')

    def test_exact_types_keysets_events_and_no_evaluation_argument(self):
        for name,arg in [('snapshot',self.s),('context',self.c),('response',self.r)]:
            value=deepcopy(arg);value['raw_token']='PRIVATE-SYNTHETIC'
            self.error(name+'_invalid',lambda:self.call(**{dict(snapshot='s',context='c',response='r')[name]:value}))
        for value in [Path('private.pdf'),lambda:None,object()]:self.error('catalog_invalid',lambda:self.call(catalog=value))
        self.error('producer_invalid',lambda:self.call(producer_name=''))
        with self.assertRaises(TypeError):self.call(evaluation={'score':1})
        s=deepcopy(self.s);s['projection']['facts']['model'].update(status='user_confirmed',event_id='E'*129);self.edit_projection(s)
        self.error('snapshot_invalid',lambda:self.call(s=s))

    def test_bool_int_nonfinite_and_non_json_objects_are_fixed_errors(self):
        for field,value in [('revision',True),('schema_version',True),('revision',float('nan')),('synthetic',1),('origin_job_id',object())]:
            s=deepcopy(self.s);s[field]=value;self.error('snapshot_invalid',lambda:self.call(s=s))

    def test_input_byte_depth_node_and_parent_reference_budgets_are_errors(self):
        s=deepcopy(self.s);s['extra']='x'*(9*1024*1024);self.error('limit_exceeded',lambda:self.call(s=s))
        s=deepcopy(self.s);tail=[];s['extra']=tail
        for _ in range(21):child=[];tail.append(child);tail=child
        self.error('limit_exceeded',lambda:self.call(s=s))
        s=deepcopy(self.s);s['extra']=[0]*500000;self.error('limit_exceeded',lambda:self.call(s=s))
        r=deepcopy(self.r);r['references']*=257;self.error('limit_exceeded',lambda:self.call(r=r))

    def test_unknown_snapshot_or_projection_fields_never_become_summary_data(self):
        s=deepcopy(self.s);s['projection']['facts']['purpose']={'value':'PRIVATE-SYNTHETIC','status':'explicit'};self.edit_projection(s)
        self.error('snapshot_invalid',lambda:self.call(s=s))
        s=deepcopy(self.s);s['projection']['questions']=[{'key':'unread_documents','message':'PRIVATE-SYNTHETIC'}];self.edit_projection(s)
        self.error('snapshot_invalid',lambda:self.call(s=s))

    def test_exact_256_reference_boundary_through_genuine_parent_objects(self):
        packet,sources,_=fixture();base=packet['cases'][0]
        for index in range(64-len(base['claims'])):
            claim=deepcopy(base['claims'][-1]);claim.update(claim_id='EXTRA-'+str(index),field='setting.reference'+str(index));base['claims'].append(claim)
        packet['cases']=[{**deepcopy(base),'case_id':'CASE-'+str(i)} for i in range(4)]
        catalog=FccReportCaseCatalog(packet,sources);c=context_for(catalog,ids=[v['case_id'] for v in packet['cases']]);refs=[]
        for case in c['cases']:
            for claim in case['claims']:
                if claim['selectable']:
                    for evidence in claim['evidence']:
                        refs.append({'case_id':case['case_id'],'claim_id':claim['claim_id'],**{k:evidence[k] for k in
                            ['evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end']}})
        self.assertEqual(len(refs),256);r=response_for(c,refs=refs);x=self.call(catalog=catalog,c=c,r=r)
        self.assertEqual(x['status'],'bound');self.assertEqual(len(x['reference_selection']['accepted_references']),256)

    def test_parent_projection_byte_limit_is_preserved_inside_larger_snapshot(self):
        s=deepcopy(self.s);s['projection']['questions']=[{'key':'x'*(1024*1024)} for _ in range(8)];self.edit_projection(s)
        self.assertLess(len(encoded(s)),9*1024*1024);self.error('limit_exceeded',lambda:self.call(s=s))

    def test_parent_wire_byte_limit_is_not_swallowed_as_binding_mismatch(self):
        r=deepcopy(self.r);r['references']=[{**r['references'][0],'line_start':10**1000,'line_end':10**1000} for _ in range(120)]
        self.assertGreater(len(encoded(r)),256*1024);self.assertLess(len(encoded(r)),320*1024)
        self.error('limit_exceeded',lambda:self.call(r=r))

    def test_genuine_catalog_read_failure_is_fixed_source_error(self):
        with patch.object(FccReportCaseCatalog,'summary',side_effect=RuntimeError('PRIVATE-SYNTHETIC')):
            self.error('source_error',lambda:self.call())


if __name__=='__main__':unittest.main()
