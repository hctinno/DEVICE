"""Synthetic reviewed metadata and synthetic responses; no model/provider calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import fcc_case_review as review
from labflow.fcc_report_cases import FccReportCaseCatalog
from tests.test_fcc_report_cases import fixture


PRODUCER='synthetic-reference-fixture'
QUERY={'product_family':'sensor_node','rule':'47 CFR 15.247','method':'ANSI C63.10-2020','model':'MODEL-A'}
CONTEXT_KEYS={'schema_version','kind','context_id','corpus_id','execution_mode','synthetic','query','requested_case_ids',
    'search_status','status','reason_codes','source_binding','source_scope','verification','limits','cases','excluded_candidates',
    'case_previews','documents'}
REFERENCE_KEYS={'case_id','claim_id','evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end'}
FLAGS={'source_dto_validated':True,'source_page_literals_reverified':False,'structured_interpretation_verified':False,
    'institution_identity_verified':False,'normative_compliance_verified':False,'model_execution_verified':False,
    'model_quality_verified':False,'independent_evaluation_approved':False,'training_executed':False,'evaluation_executed':False,
    'hardware_verified':False,'physical_verified':False}


def first_ref(context,*,case_index=0,field=None):
    case=context['cases'][case_index]
    claim=next(item for item in case['claims'] if item['selectable'] and (field is None or item['field']==field))
    evidence=claim['evidence'][0]
    return {'case_id':case['case_id'],'claim_id':claim['claim_id'],**{key:evidence[key] for key in
        ['evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end']}}


def wire(context,refs=None,*,status='selected',reasons=None):
    return {'schema_version':1,'kind':'fcc_case_review_response','context_id':context['context_id'],
        'producer':{'kind':'model','name':PRODUCER},'status':status,
        'references':[first_ref(context)] if refs is None else refs,'reason_codes':[] if reasons is None else reasons}


class FccCaseReviewTests(unittest.TestCase):
    def setUp(self):
        self.packet,self.sources,claim=fixture()
        claims=self.packet['cases'][0]['claims']
        claims.append(claim('result.zero',0,13,unit='dBm'))
        claims.append(claim('setting.enabled',False,14))
        claims.append(claim('setting.unreviewed','PRIVATE-SYNTHETIC',15,status='extracted'))
        claims.append({'claim_id':'GAP-A','field':'setting.unknown','value':None,'unit':None,
                       'status':'not_reported','basis':'report_fact','evidence':[]})
        self.catalog=FccReportCaseCatalog(self.packet,self.sources)

    def context(self,**kwargs):
        return review.build_case_review_context(kwargs.pop('catalog',self.catalog),query=kwargs.pop('query',QUERY),
            case_ids=kwargs.pop('case_ids',['CASE-A']),**kwargs)

    def decode(self,value,context=None):
        return review.decode_case_review_response(value if type(value) in (str,bytes) else json.dumps(value),
            self.context() if context is None else context,producer_name=PRODUCER)

    def error(self,code,operation):
        with self.assertRaises(review.FccCaseReviewError) as caught:operation()
        expected='fcc_case_review_'+code
        self.assertEqual(str(caught.exception),expected)
        self.assertEqual(caught.exception.code,expected)
        self.assertEqual(caught.exception.args,(expected,))
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn('PRIVATE-SYNTHETIC',repr(caught.exception))

    def test_exact_context_query_bindings_and_source_limits(self):
        context=self.context()
        self.assertEqual(set(context),CONTEXT_KEYS)
        self.assertEqual((context['schema_version'],context['kind'],context['execution_mode']),
            (1,'fcc_case_review_context','report_derived_case_review'))
        self.assertEqual(context['status'],'ready');self.assertEqual(context['verification'],FLAGS)
        self.assertEqual(context['query'],QUERY);self.assertEqual(context['requested_case_ids'],['CASE-A'])
        self.assertEqual(context['cases'][0]['source_case_sha256'],context['source_binding']['case_sha256s'][0]['sha256'])
        self.assertEqual(context['documents'][0]['extraction'],self.catalog.summary()['documents'][0]['extraction'])
        self.assertFalse(context['documents'][0]['rights']['external_model_use_allowed'])
        self.assertEqual(context['case_previews'],self.catalog.summary()['case_previews'])

    def test_identity_and_evidence_hashes_bind_complete_case_and_literal(self):
        context=self.context();payload={key:value for key,value in context.items() if key!='context_id'}
        encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(context['context_id'],hashlib.sha256(encoded).hexdigest())
        case=context['cases'][0];claim=case['claims'][0];evidence=claim['evidence'][0]
        original={key:value for key,value in evidence.items() if key!='evidence_id'}
        encoded=json.dumps({'case_id':case['case_id'],'claim_id':claim['claim_id'],'evidence':original},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(evidence['evidence_id'],hashlib.sha256(encoded).hexdigest())

    def test_zero_false_and_unknown_status_are_preserved_without_defaults(self):
        case=self.context()['cases'][0]
        self.assertIs(type(next(claim for claim in case['claims'] if claim['field']=='result.zero')['value']),int)
        self.assertEqual(next(claim for claim in case['claims'] if claim['field']=='result.zero')['value'],0)
        self.assertIs(next(claim for claim in case['claims'] if claim['field']=='setting.enabled')['value'],False)
        self.assertTrue(all(claim['status']=='reviewed' for claim in case['claims']))
        self.assertEqual(next(gap for gap in case['gaps'] if gap['claim_id']=='GAP-A')['status'],'not_reported')
        self.assertNotIn('PRIVATE-SYNTHETIC',json.dumps(case['gaps']))
        self.assertEqual(case['preview']['review_status'],'partial')

    def test_basis_is_preserved_and_not_promoted_to_report_fact(self):
        context=self.context();claims=context['cases'][0]['claims']
        self.assertEqual(next(claim for claim in claims if claim['field']=='issuer.classification')['basis'],'developer_inference')
        self.assertEqual(next(claim for claim in claims if claim['field']=='method.references')['basis'],'standard_reference_only')
        value=self.decode(wire(context,[first_ref(context,field='method.references')]),context)
        self.assertEqual(value['verification'],FLAGS)
        self.assertFalse(value['verification']['normative_compliance_verified'])

    def test_prompt_uses_fixed_system_and_untrusted_json_with_declared_producer(self):
        context=self.context();result=review.build_case_review_prompt(context,producer_name=PRODUCER)
        self.assertEqual(set(result),{'schema_version','kind','binding','expected_producer','messages','verification'})
        self.assertEqual([item['role'] for item in result['messages']],['system','user'])
        self.assertEqual(json.loads(result['messages'][1]['content']),context)
        self.assertEqual(result['expected_producer'],{'kind':'model','name':PRODUCER})
        self.assertEqual(result['verification'],FLAGS)
        self.assertNotIn('PRIVATE-SYNTHETIC',result['messages'][0]['content'])

    def test_strict_response_selects_only_bound_reference_and_no_score(self):
        context=self.context();value=self.decode(wire(context),context)
        self.assertEqual(set(value),{'schema_version','kind','context_id','corpus_id','status','reason_codes','references','expected_producer','source_binding','verification'})
        self.assertEqual(value['kind'],'validated_fcc_case_review')
        self.assertEqual(value['references'],[first_ref(context)])
        self.assertEqual(set(value['references'][0]),REFERENCE_KEYS)
        self.assertEqual(value['verification'],FLAGS)
        self.assertNotIn('score',value);self.assertNotIn('fold',value)

    def test_no_candidates_is_normal_and_cannot_select_reference(self):
        query={**QUERY,'product_family':'other_synthetic_product'}
        context=self.context(query=query,case_ids=[])
        self.assertEqual(context['search_status'],'no_match');self.assertEqual(context['status'],'no_candidates')
        value=self.decode(wire(context,[],status='no_candidate',reasons=['no_reviewed_case']),context)
        self.assertEqual(value['status'],'no_candidate')
        self.error('selection_invalid',lambda:self.context(query=query))

    def test_missing_query_and_exact_model_preserve_insufficient_state(self):
        for change in [{'method':None},{'model':'OTHER-MODEL'}]:
            with self.subTest(change=change):
                query={**QUERY,**change};context=self.context(query=query,case_ids=[])
                self.assertEqual(context['status'],'insufficient_evidence')
                self.decode(wire(context,[],status='insufficient_evidence',reasons=['query_insufficient']),context)
                self.error('selection_invalid',lambda:self.context(query=query))

    def test_candidates_without_selection_remain_unselected(self):
        context=self.context(case_ids=[])
        self.assertEqual(context['status'],'no_selected_cases');self.assertEqual(context['cases'],[])
        self.decode(wire(context,[],status='insufficient_evidence',reasons=['no_selected_cases']),context)
        self.error('response_invalid',lambda:self.decode(wire(context,[],status='no_candidate',reasons=['no_reviewed_case']),context))

    def test_wrong_edition_query_is_not_replaced(self):
        query={**QUERY,'method':'ANSI C63.10-2023'}
        context=self.context(query=query,case_ids=[])
        self.assertEqual(context['status'],'no_candidates')
        self.error('selection_invalid',lambda:self.context(query=query))

    def test_other_reviewed_edition_claim_is_not_selectable_for_query(self):
        packet,sources,make=fixture();packet['cases'][0]['claims'].append(make('method.references',['ANSI C63.10-2013'],10,basis='standard_reference_only'))
        context=self.context(catalog=FccReportCaseCatalog(packet,sources))
        case=context['cases'][0];claim=next(claim for claim in case['claims'] if claim['value']==['ANSI C63.10-2013'])
        self.assertFalse(claim['selectable']);self.assertEqual(claim['selection_reason'],'query_literal_mismatch')
        evidence=claim['evidence'][0];reference={'case_id':case['case_id'],'claim_id':claim['claim_id'],**{key:evidence[key] for key in REFERENCE_KEYS-{'case_id','claim_id'}}}
        self.error('reference_invalid',lambda:self.decode(wire(context,[reference]),context))

    def test_unknown_and_unreviewed_claim_ids_are_rejected(self):
        context=self.context();reference=first_ref(context)
        for claim_id in ['MISSING','GAP-A',next(claim['claim_id'] for claim in self.packet['cases'][0]['claims'] if claim['status']=='extracted')]:
            with self.subTest(claim_id=claim_id):self.error('reference_invalid',lambda:self.decode(wire(context,[{**reference,'claim_id':claim_id}]),context))

    def test_same_claim_id_cannot_mix_case_document_hash_page_or_lines(self):
        context=self.context();reference=first_ref(context)
        changes={'case_id':'OTHER-CASE','document_id':'OTHER-DOC','source_sha256':'1'*64,'text_sha256':'2'*64,
                 'file_page':2,'line_start':2,'line_end':2,'evidence_id':'3'*64}
        for field,value in changes.items():
            with self.subTest(field=field):self.error('reference_invalid',lambda:self.decode(wire(context,[{**reference,field:value}]),context))

    def test_same_claim_id_in_two_selected_cases_keeps_distinct_evidence_identity(self):
        packet=deepcopy(self.packet);packet['cases'].append({**deepcopy(packet['cases'][0]),'case_id':'CASE-B'})
        catalog=FccReportCaseCatalog(packet,self.sources)
        context=self.context(catalog=catalog,case_ids=['CASE-A','CASE-B'])
        first,second=first_ref(context),first_ref(context,case_index=1)
        self.assertEqual(first['claim_id'],second['claim_id'])
        self.assertNotEqual(first['evidence_id'],second['evidence_id'])
        self.assertEqual(len(self.decode(wire(context,[first,second]),context)['references']),2)
        self.error('reference_invalid',lambda:self.decode(wire(context,[{**first,'case_id':'CASE-B'}]),context))

    def test_reference_bool_integer_alias_is_rejected(self):
        context=self.context();reference=first_ref(context)
        for field in ['file_page','line_start','line_end']:
            with self.subTest(field=field):self.error('response_invalid',lambda:self.decode(wire(context,[{**reference,field:True}]),context))

    def test_context_tampering_and_stale_response_identity_are_rejected(self):
        context=self.context();bad=deepcopy(context);bad['cases'][0]['claims'][0]['value']='tampered'
        self.error('context_invalid',lambda:review.build_case_review_prompt(bad,producer_name=PRODUCER))
        self.error('context_invalid',lambda:self.decode(wire(context),bad))
        bad_wire=wire(context);bad_wire['context_id']='0'*64
        self.error('context_mismatch',lambda:self.decode(bad_wire,context))

    def test_response_producer_status_extra_fact_and_reference_shape_are_strict(self):
        context=self.context()
        for change in [{'producer':{'kind':'model','name':'other'}},{'status':'completed'},{'score':1},{'fold':'independent'},
                       {'tool_call':'run-device'},{'value':0},{'references':[]}]:
            with self.subTest(change=change):self.error('response_invalid',lambda:self.decode({**wire(context),**change},context))
        self.error('response_invalid',lambda:self.decode(wire(context,[{**first_ref(context),'quote':'invented'}]),context))

    def test_strict_json_duplicate_nonfinite_fences_trailing_and_unicode(self):
        context=self.context();text=json.dumps(wire(context))
        for bad in ['```json\n'+text+'\n```',text+' {}',text.replace('"schema_version": 1','"schema_version": 1, "schema_version": 1'),
                    text.replace('"selected"','NaN'),text.replace('"selected"','"\\ud800"'),b'\xff']:
            with self.subTest(kind=type(bad).__name__):self.error('response_invalid',lambda:self.decode(bad,context))
        self.error('response_invalid',lambda:review.decode_case_review_response(wire(context),context,producer_name=PRODUCER))

    def test_duplicate_reference_and_foreign_basis_value_fields_are_rejected(self):
        context=self.context();reference=first_ref(context)
        self.error('response_invalid',lambda:self.decode(wire(context,[reference,reference]),context))
        for field,value in [('basis','report_fact'),('value',False),('edition','2023')]:
            with self.subTest(field=field):self.error('response_invalid',lambda:self.decode(wire(context,[{**reference,field:value}]),context))

    def test_source_dto_literal_and_citable_flags_must_not_be_upgraded(self):
        for mutate in [lambda cat:cat._summary['verification'].update(coverage_complete=True),
                       lambda cat:cat._cases['CASE-A']['claims'][0]['evidence'][0].update(literal_verified=False),
                       lambda cat:cat._documents['DOC-A']['page_index'][0].update(citable=False)]:
            with self.subTest(mutate=mutate):
                catalog=FccReportCaseCatalog(self.packet,self.sources);mutate(catalog)
                self.error('source_invalid',lambda:self.context(catalog=catalog))

    def test_case_selection_query_and_catalog_types_are_explicit(self):
        for query in [{}, {**QUERY,'extra':'x'},{**QUERY,'method':False}]:
            self.error('query_invalid',lambda:self.context(query=query))
        for ids in [('CASE-A',),['CASE-A','CASE-A'],['UNKNOWN'],[True]]:
            self.error('selection_invalid',lambda:self.context(case_ids=ids))
        class Duck:
            def summary(self):raise AssertionError('must not call')
        self.error('catalog_invalid',lambda:self.context(catalog=Duck()))

    def test_subclass_and_callback_are_not_catalog_inputs(self):
        class Subclass(FccReportCaseCatalog):pass
        self.error('catalog_invalid',lambda:self.context(catalog=object.__new__(Subclass)))
        calls=[]
        def callback():calls.append('callback')
        self.error('catalog_invalid',lambda:self.context(catalog=callback))
        self.assertEqual(calls,[])

    def test_source_read_failure_is_sanitized_and_not_retried(self):
        self.catalog._cases.pop('CASE-A')
        self.error('source_error',lambda:self.context())

    def test_producer_names_and_wire_budgets_are_bounded(self):
        context=self.context()
        for name in ['',None,' '*3,'x'*201,'x\ud800']:
            self.error('producer_invalid',lambda:review.build_case_review_prompt(context,producer_name=name))
        self.error('limit_exceeded',lambda:self.decode('x'*(256*1024+1),context))
        self.error('limit_exceeded',lambda:self.decode(wire(context,[first_ref(context)]*257),context))
        big=deepcopy(context);big['over_limit']='x'*(8*1024*1024+1)
        self.error('limit_exceeded',lambda:review.build_case_review_prompt(big,producer_name=PRODUCER))

    def test_multibyte_context_limit_is_not_relabelled_as_invalid_data(self):
        context=self.context();context['over_limit']='한'*(3*1024*1024)
        self.error('limit_exceeded',lambda:review.build_case_review_prompt(context,producer_name=PRODUCER))

    def test_response_depth_and_node_limits_stop_before_schema_processing(self):
        context=self.context()
        self.error('limit_exceeded',lambda:self.decode('['*13+'0'+']'*13,context))
        self.error('limit_exceeded',lambda:self.decode('['+','.join('0' for _ in range(50001))+']',context))

    def test_insufficient_reason_cannot_claim_selection_is_missing_when_present(self):
        context=self.context()
        self.error('response_invalid',lambda:self.decode(wire(context,[],status='insufficient_evidence',reasons=['no_selected_cases']),context))
        self.decode(wire(context,[],status='insufficient_evidence',reasons=['additional_evidence_required']),context)

    def test_source_relation_and_search_row_shapes_are_checked(self):
        catalog=FccReportCaseCatalog(self.packet,self.sources)
        catalog._cases['CASE-A']['relations']=[{'relation_id':'REL','kind':'part_of','target_case_id':None,
            'external_target':'unconfirmed-parent','status':'unresolved','private_path':'PRIVATE-SYNTHETIC'}]
        self.error('source_invalid',lambda:self.context(catalog=catalog))
        catalog=FccReportCaseCatalog(self.packet,self.sources)
        catalog._summary['searches'][0]['extra']='PRIVATE-SYNTHETIC'
        self.error('source_invalid',lambda:self.context(catalog=catalog))

    def test_uncitable_other_page_and_partial_extraction_are_preserved(self):
        document=self.catalog._documents['DOC-A']
        document['extraction'].update(status='partial',complete=False)
        document['extraction']['issues'].append({'code':'page_resource_unavailable','file_page':2})
        document['page_index'][1].update(status='error',citable=False)
        context=self.context();self.assertEqual(context['status'],'ready')
        self.assertEqual(context['documents'][0]['extraction']['status'],'partial')
        self.assertFalse(context['documents'][0]['page_index'][1]['citable'])
        reference=first_ref(context);self.assertEqual(reference['file_page'],1)
        self.error('reference_invalid',lambda:self.decode(wire(context,[{**reference,'file_page':2}]),context))

    def test_sixteen_explicit_cases_fit_and_seventeenth_is_a_limit(self):
        packet=deepcopy(self.packet);template=packet['cases'][0]
        packet['cases']=[{**deepcopy(template),'case_id':'CASE-'+str(index).zfill(2)} for index in range(17)]
        catalog=FccReportCaseCatalog(packet,self.sources);ids=[case['case_id'] for case in packet['cases']]
        context=self.context(catalog=catalog,case_ids=list(reversed(ids[:16])))
        self.assertEqual(context['requested_case_ids'],ids[:16]);self.assertEqual(len(context['cases']),16)
        refs=[first_ref(context,case_index=index) for index in range(16)]
        self.assertEqual(len(self.decode(wire(context,refs),context)['references']),16)
        self.error('limit_exceeded',lambda:self.context(catalog=catalog,case_ids=ids))

    def test_legal_source_preview_lengths_and_lists_are_not_narrowed(self):
        for field,value in [('report.number','R'*300),('equipment.models',['SYNTHETIC-'+str(index) for index in range(129)])]:
            with self.subTest(field=field):
                packet=deepcopy(self.packet);claim=next(item for item in packet['cases'][0]['claims'] if item['field']==field);claim['value']=value
                context=self.context(catalog=FccReportCaseCatalog(packet,self.sources))
                self.assertEqual(context['status'],'ready')
                self.assertEqual(next(item for item in context['cases'][0]['claims'] if item['field']==field)['value'],value)

    def test_malformed_source_claim_value_keeps_021_depth_and_string_limits(self):
        nested='value'
        for _ in range(7):nested={'child':nested}
        for value in [nested,'x'*16385]:
            with self.subTest(kind=type(value).__name__):
                catalog=FccReportCaseCatalog(self.packet,self.sources)
                next(claim for claim in catalog._cases['CASE-A']['claims'] if claim['field']=='result.zero')['value']=value
                self.error('limit_exceeded',lambda:self.context(catalog=catalog))

    def test_context_and_results_are_detached_and_failed_input_is_unchanged(self):
        query=deepcopy(QUERY);before=self.catalog.case('CASE-A')
        context=self.context(query=query);original=deepcopy(context)
        context['cases'][0]['claims'][0]['value']='caller mutation';query['method']='changed'
        self.assertEqual(self.context(),original);self.assertEqual(self.catalog.case('CASE-A'),before)
        bad=wire(original);bad['context_id']='0'*64;saved=deepcopy(bad)
        self.error('context_mismatch',lambda:self.decode(bad,original));self.assertEqual(bad,saved)

    def test_build_prompt_decode_and_replays_add_no_io_parsing_or_model_client(self):
        with patch('builtins.open') as opens,patch.object(Path,'open') as files,patch('os.open') as osopen, \
             patch.object(socket,'socket') as sockets,patch.object(subprocess,'Popen') as processes, \
             patch('labflow.fcc_report_cases.extract_document') as parser:
            context=self.context();review.build_case_review_prompt(context,producer_name=PRODUCER)
            value=self.decode(wire(context),context);again=self.context()
        self.assertEqual(context,again);self.assertEqual(value['verification'],FLAGS)
        for mock in [opens,files,osopen,sockets,processes,parser]:mock.assert_not_called()


if __name__=='__main__':unittest.main()
