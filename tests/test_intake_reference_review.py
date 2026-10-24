"""Genuine synthetic042 workflow and hostile boundary DTOs; no customer/model."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

from labflow import intake_reference_review as review
from labflow import intake_reference_ledger as ledger
from labflow.intake_reference_snapshot import read_intake_reference_snapshot
from labflow.intake_jobs import respond
from labflow.store import Store,canonical
from tests import test_intake_reference_ledger as fixture038
from tests.test_intake_case_references import catalog_fixture,context_for,response_for


PREVIEW={'schema_version','kind','intake_id','preparation_id','observation','preparation_ready','reason_codes','review_status','selection','source_modes','verification'}
CURRENT={'schema_version','kind','intake_id','available','status','record','reference_summary','current_observation','reason_codes','verification'}
REASONS={'analysis_not_ready','profile_changed','delegation_missing','intake_deferred','delegation_evidence_missing','required_questions_open','unread_documents','source_provenance_unconfirmed','preparation_not_ready'}
ROOT=Path(__file__).resolve().parents[1]


class ReferenceReviewTests(unittest.TestCase):
    setUp=fixture038.ReferenceLedgerTests.setUp
    revision=fixture038.ReferenceLedgerTests.revision
    base=fixture038.ReferenceLedgerTests.base
    namespace=fixture038.ReferenceLedgerTests.namespace
    counts=fixture038.ReferenceLedgerTests.counts

    def prepare(self,**changes):
        kwargs={'case_context':self.context,'validated_response':self.response,
                'producer_name':self.response['expected_producer']['name'],'allow_retained_reads':True}
        kwargs.update(changes)
        return review.prepare_reference_review(self.store,self.catalog,self.intake,**kwargs)

    def request(self,preview,name='REQUEST-042'):
        return {'schema_version':1,'intake_id':self.intake,'request_id':name,'preparation_id':preview['preparation_id'],
                'expected_snapshot_id':preview['observation']['snapshot_id'],'expected_head_record_id':preview['observation']['head_record_id']}

    def append(self,prepared,preview,*,name='REQUEST-042',**changes):
        kwargs={'allow_retained_reads':True,'allow_append':True};kwargs.update(changes)
        return review.append_reference_review(self.store,self.catalog,prepared,self.request(preview,name),**kwargs)

    def read(self,action='current',**changes):
        request={'schema_version':1,'action':action}
        if action=='history':request.update(limit=20,before_seq=None)
        request.update(changes)
        return review.read_reference_review(self.store,self.intake,request,allow_retained_reads=True)

    def error(self,suffix,operation,prefix='intake_reference_review_'):
        with self.assertRaises(ValueError) as caught:operation()
        error=caught.exception;code=prefix+suffix
        self.assertEqual((getattr(error,'code',None),str(error),error.args),(code,code,(code,)))
        self.assertIsNone(error.__context__);self.assertIsNone(error.__cause__)
        self.assertNotIn(str(self.root),repr(error));self.assertNotIn('MODEL-A',repr(error))

    def test_real_prepare_append_history_current_exact_sanitized(self):
        before=self.base();prepared,p=self.prepare()
        self.assertIs(type(prepared),review.PreparedReferenceReview);self.assertEqual(set(p),PREVIEW)
        self.assertEqual(p['kind'],'intake_reference_review_preview');self.assertEqual(len(p['observation']),4)
        self.assertEqual(p['observation']['kind'],'paired_public_reads');self.assertTrue(p['preparation_ready'])
        self.assertEqual(p['reason_codes'],[]);self.assertEqual(p['review_status'],'bound')
        self.assertEqual(p['selection']['status'],'selected');self.assertEqual(p['selection']['accepted_reference_count'],1)
        for key in ['selection','source_modes','verification']:self.assertEqual(len(p[key]),{'selection':6,'source_modes':3,'verification':6}[key])
        self.assertEqual([v for v in p['verification'].values()].count(True),2)
        r=self.append(prepared,p);self.assertEqual(set(r),fixture038.REG);self.assertEqual(r['binding_status'],'current_at_append')
        h=self.read('history');self.assertEqual(set(h),fixture038.HISTORY);self.assertEqual(len(h['records']),1)
        c=self.read();self.assertEqual(set(c),CURRENT);self.assertEqual(c['kind'],'intake_reference_review_current')
        self.assertEqual(c['status'],'current');self.assertEqual(len(c['reference_summary']),5)
        self.assertEqual(c['reference_summary']['selected_case_ids'],['CASE-A']);self.assertNotIn('reference_receipt',c)
        self.assertEqual(self.counts(),(1,1,1));self.assertEqual(self.base(),before)
        for dto in [p,r,h,c]:
            encoded=canonical(dto)
            for private in ['MODEL-A','product.models','quote','source_sha256','file_page',str(self.root),'provided_context_sha256']:
                self.assertNotIn(private,encoded)

    def test_preparation_id_exact_eight_canonical_fields_and_timestamp_separation(self):
        capture=read_intake_reference_snapshot(self.store,self.intake);prepared,p=self.prepare()
        receipt=fixture038.build_intake_case_reference_receipt(capture['snapshot'],self.catalog,self.context,self.response,
                    producer_name=self.response['expected_producer']['name'])
        expected=fixture038.digest({'schema_version':1,'intake_id':self.intake,'snapshot_id':capture['snapshot_id'],'head_record_id':None,
            'case_context_sha256':fixture038.digest(self.context),'validated_response_sha256':fixture038.digest(self.response),
            'reference_receipt_sha256':fixture038.digest(receipt),'producer_name':self.response['expected_producer']['name']})
        self.assertEqual(p['preparation_id'],expected)
        _,again=self.prepare();self.assertEqual(p['preparation_id'],again['preparation_id'])
        self.assertNotIn('MODEL-A',repr(prepared));self.assertFalse(hasattr(prepared,'__dict__'))

    def test_default_read_gate_before_parent_and_retained_read(self):
        prepared,p=self.prepare()
        with patch.object(review,'read_intake_reference_snapshot',side_effect=AssertionError('parent')), \
             patch.object(review,'current_reference',side_effect=AssertionError('parent')), \
             patch.object(review,'record_intake_reference',side_effect=AssertionError('writer')):
            self.error('access_denied',lambda:self.prepare(allow_retained_reads=False))
            self.error('access_denied',lambda:review.read_reference_review(self.store,self.intake,{'schema_version':1,'action':'current'}))
            self.error('access_denied',lambda:review.append_reference_review(self.store,self.catalog,prepared,self.request(p)))
        self.assertEqual(self.namespace(),[])

    def test_write_gate_and_exact_bool_flags(self):
        prepared,p=self.prepare()
        with patch.object(review,'record_intake_reference',side_effect=AssertionError('writer')):
            self.error('access_denied',lambda:self.append(prepared,p,allow_append=False))
            for value in [0,1,None,'true',[],{}]:
                with self.subTest(value=value):
                    self.error('invalid_argument',lambda:self.prepare(allow_retained_reads=value))
                    self.error('invalid_argument',lambda:self.append(prepared,p,allow_append=value))

    def test_history_default_has_no_source_grant_and_no_parent_capture(self):
        with patch.object(review,'current_reference',side_effect=AssertionError('source')), \
             patch.object(review,'read_intake_reference_snapshot',side_effect=AssertionError('source')):
            h=review.read_reference_review(self.store,self.intake,{'schema_version':1,'action':'history','limit':20,'before_seq':None})
        self.assertFalse(h['available']);self.assertEqual(h['records'],[]);self.assertEqual(self.namespace(),[])

    def test_exact_store_catalog_and_prepared_types(self):
        class StoreProxy:pass
        class StoreSubclass(Store):pass
        for store in [None,StoreProxy(),object.__new__(StoreSubclass),object.__new__(Store)]:
            self.error('store_invalid',lambda:review.prepare_reference_review(store,self.catalog,self.intake,
                case_context=self.context,validated_response=self.response,producer_name='SYN',allow_retained_reads=True))
        self.error('invalid_argument',lambda:review.prepare_reference_review(self.store,object(),self.intake,
                case_context=self.context,validated_response=self.response,producer_name='SYN',allow_retained_reads=True))
        _,p=self.prepare()
        for prepared in [None,{},object()]:self.error('prepared_invalid',lambda:self.append(prepared,p))

    def test_small_request_exact_keys_ids_and_privilege_injection(self):
        prepared,p=self.prepare();request=self.request(p)
        for name in ['allow_append','permission','csrf','path','sql','extra']:
            changed=dict(request);changed[name]='PRIVATE'
            self.error('invalid_argument',lambda:review.append_reference_review(self.store,self.catalog,prepared,changed,allow_retained_reads=True,allow_append=True))
        for name,value in [('schema_version',True),('request_id','../x'),('expected_snapshot_id','bad')]:
            changed=dict(request);changed[name]=value
            self.error('invalid_argument',lambda:review.append_reference_review(self.store,self.catalog,prepared,changed,allow_retained_reads=True,allow_append=True))
        for request in [{'schema_version':True,'action':'history','limit':20,'before_seq':None},
                        {'schema_version':1,'action':'current','limit':1},
                        {'schema_version':1,'action':'history','limit':True,'before_seq':None},
                        {'schema_version':1,'action':'history','limit':101,'before_seq':None},
                        {'schema_version':1,'action':'history','limit':1,'before_seq':2**63}]:
            self.error('invalid_argument',lambda:review.read_reference_review(self.store,self.intake,request,allow_retained_reads=True))

    def test_prepared_mismatches_reject_before_writer(self):
        prepared,p=self.prepare();request=self.request(p)
        with patch.object(review,'record_intake_reference',side_effect=AssertionError('writer')):
            for name,value in [('intake_id','OTHER'),('preparation_id','a'*64),('expected_snapshot_id','b'*64),('expected_head_record_id','c'*64)]:
                changed=dict(request);changed[name]=value
                self.error('prepared_invalid',lambda:review.append_reference_review(self.store,self.catalog,prepared,changed,allow_retained_reads=True,allow_append=True))
            other=catalog_fixture()
            self.error('prepared_invalid',lambda:review.append_reference_review(self.store,other,prepared,request,allow_retained_reads=True,allow_append=True))

    def test_existing_db_identity_swap_rejects_before_writer(self):
        prepared,p=self.prepare();original=self.store.db
        self.store.db=self.root/'absent'/'lab.sqlite3'
        self.error('storage_error',lambda:self.prepare(),prefix='intake_reference_ledger_')
        self.assertFalse(self.store.db.parent.exists())
        self.store.db=original;replacement=Store(self.root/'other');self.store.db=replacement.db
        self.error('prepared_invalid',lambda:self.append(prepared,p));self.store.db=original

    def test_private_preparation_detaches_inputs_and_public_preview(self):
        prepared,p=self.prepare();original=deepcopy(p);self.context['query']['model']='PRIVATE-MUTATION'
        self.response['references'].clear();p['observation']['snapshot_id']='d'*64;p['reason_codes'].append('PRIVATE')
        result=self.append(prepared,original);self.assertEqual(result['binding_status'],'current_at_append')
        self.assertEqual(self.read()['reference_summary']['accepted_reference_count'],1)

    def test_gap_between_c1_and_c2_is_state_changed_without_retry(self):
        original=review.build_intake_case_reference_receipt
        def between(*args,**kwargs):
            result=original(*args,**kwargs);respond(self.store,'GAP','defer',intake_id=self.intake);return result
        with patch.object(review,'build_intake_case_reference_receipt',side_effect=between) as parent:
            self.error('review_state_changed',lambda:self.prepare());self.assertEqual(parent.call_count,1)
        self.assertEqual(self.namespace(),[])

    def test_unsupported_pending_capture_is_unavailable(self):
        self.revision('PENDING',finish=False)
        self.error('unavailable',lambda:self.prepare());self.assertEqual(self.namespace(),[])

    def test_deferred_and_no_delegation_preview_keeps_only_c1_reasons(self):
        respond(self.store,'DEFER','defer',intake_id=self.intake)
        capture=read_intake_reference_snapshot(self.store,self.intake);prepared,p=self.prepare()
        self.assertFalse(p['preparation_ready']);self.assertEqual(p['reason_codes'],capture['readiness']['reason_codes'])
        self.assertIn('intake_deferred',p['reason_codes']);self.assertNotIn('no_reference_head',p['reason_codes'])
        self.assertTrue(set(p['reason_codes'])<=REASONS);self.assertEqual(p['reason_codes'],sorted(set(p['reason_codes'])))
        self.assertEqual(self.append(prepared,p)['binding_status'],'current_at_append');self.assertEqual(self.read()['status'],'current')

    def test_genuine_undelegated_and_required_question_reasons_stay_visible(self):
        folder=self.inbox/'two';folder.mkdir()
        (folder/'request.pdf').write_bytes(fixture038.synthetic_pdf(['product_type: sensor_node\nmarket: FCC\nmodel: MODEL-A']))
        fixture038.scan_source(self.store,'INBOX',now=200);fixture038.scan_source(self.store,'INBOX',now=202)
        job=fixture038.claim_job(self.store,'WORKER',now=203)
        fixture038.complete_job(self.store,job['job_id'],job['token'],fixture038.SyntheticTextProvider().analyze(job),now=204)
        self.intake=job['intake_id'];_,undelegated=self.prepare()
        self.assertFalse(undelegated['preparation_ready']);self.assertIn('delegation_missing',undelegated['reason_codes'])
        self.assertIn('delegation_evidence_missing',undelegated['reason_codes'])
        respond(self.store,'PROCEED-2','proceed',intake_id=self.intake);prepared,questions=self.prepare()
        self.assertIn('required_questions_open',questions['reason_codes']);self.assertFalse(questions['preparation_ready'])
        self.assertEqual(self.append(prepared,questions)['binding_status'],'current_at_append')

    def test_virtual_profile_change_is_preparation_unverified_without_head(self):
        with patch('labflow.intake_reference_snapshot.current_extraction_profile_id',return_value='0'*64):
            prepared,p=self.prepare();self.assertIn('profile_changed',p['reason_codes']);self.assertFalse(p['preparation_ready'])
            result=self.append(prepared,p)
            self.assertEqual(result['binding_status'],'preparation_unverified');self.assertFalse(result['append_observation']['head_advanced'])
        self.assertEqual(self.counts(),(1,1,0))

    def test_unbound_response_and_nullable_catalog_are_normal(self):
        altered=deepcopy(self.context);altered['query']['model']='OTHER'
        prepared,p=self.prepare(case_context=altered)
        self.assertEqual(p['review_status'],'insufficient_evidence');self.assertEqual(p['selection']['status'],'unknown')
        self.assertIsNone(p['selection']['context_id']);self.assertIsNone(p['selection']['corpus_id'])
        self.assertIsNone(p['source_modes']['catalog_synthetic'])
        self.assertEqual(self.append(prepared,p)['binding_status'],'reference_unbound')

    def test_no_candidate_and_insufficient_response_are_preserved(self):
        for query,status,reasons in [({'product_family':'sensor_node','rule':'47 CFR 15.247','method':'OTHER-EDITION','model':'MODEL-A'},'no_candidate',['no_reviewed_case']),
                                    (None,'insufficient_evidence',['additional_evidence_required'])]:
            context=context_for(self.catalog,query=query,ids=[] if status=='no_candidate' else None)
            response=response_for(context,refs=[],status=status,reasons=reasons)
            _,p=self.prepare(case_context=context,validated_response=response)
            self.assertEqual(p['selection']['accepted_reference_count'],0)
            self.assertEqual(p['selection']['status'],'no_candidate' if status=='no_candidate' else 'unknown')

    def test_synthetic_intake_and_nonsynthetic_catalog_stay_separate(self):
        self.catalog=catalog_fixture(synthetic=False);self.context=context_for(self.catalog);self.response=response_for(self.context)
        _,p=self.prepare();self.assertIs(p['source_modes']['intake_revision_synthetic'],True)
        self.assertIs(p['source_modes']['catalog_synthetic'],False)

    def test_final_append_uses_once_parent_cas_after_head_change(self):
        prepared,p=self.prepare();other,second=self.prepare();self.append(other,second,name='FIRST')
        original=review.record_intake_reference
        with patch.object(review,'record_intake_reference',wraps=original) as parent:
            conflict=self.append(prepared,p,name='LATE');self.assertEqual(parent.call_count,1)
        self.assertEqual(conflict['binding_status'],'head_conflict');self.assertFalse(conflict['append_observation']['head_advanced'])
        self.assertEqual(self.counts(),(2,2,1))

    def test_old_prepared_after_answer_is_historical_without_new_expected(self):
        prepared,p=self.prepare();respond(self.store,'ANSWER','answer',intake_id=self.intake,answers={'purpose':'updated'})
        result=self.append(prepared,p);self.assertEqual(result['binding_status'],'historical_provided')
        self.assertFalse(result['append_observation']['head_advanced'])

    def test_replay_original_append_after_defer_and_fresh_current_separate(self):
        prepared,p=self.prepare();first=self.append(prepared,p);respond(self.store,'DEFER','defer',intake_id=self.intake)
        with patch.object(review,'read_intake_reference_snapshot',side_effect=AssertionError('reprepare')), \
             patch.object(review,'current_reference',side_effect=AssertionError('current')), \
             patch.object(review,'build_intake_case_reference_receipt',side_effect=AssertionError('rebuild')):
            replay=self.append(prepared,p)
        self.assertTrue(replay['replayed']);self.assertEqual(replay['append_observation'],first['append_observation'])
        self.assertEqual(self.read()['status'],'stale');self.assertEqual(self.counts(),(1,1,1))

    def test_same_request_different_preparation_is_parent_request_conflict(self):
        prepared,p=self.prepare();self.append(prepared,p)
        respond(self.store,'ANSWER','answer',intake_id=self.intake,answers={'purpose':'updated'})
        new,new_p=self.prepare();self.error('request_conflict',lambda:self.append(new,new_p),prefix='intake_reference_ledger_')
        self.assertEqual(self.counts(),(1,1,1))

    def test_stale_and_unavailable_current_retain_only_historical_summary(self):
        prepared,p=self.prepare();self.append(prepared,p);respond(self.store,'DEFER','defer',intake_id=self.intake)
        stale=self.read();self.assertEqual(stale['status'],'stale');self.assertIsNotNone(stale['reference_summary'])
        self.revision('PENDING',finish=False);unavailable=self.read();self.assertEqual(unavailable['status'],'unavailable')
        self.assertEqual(unavailable['reference_summary'],stale['reference_summary']);self.assertNotIn('reference_receipt',unavailable)

    def test_i1_malformed_preparation_reasons_are_never_normalized(self):
        capture=read_intake_reference_snapshot(self.store,self.intake)
        for reasons in [['PRIVATE'],['no_reference_head'],['legacy_analysis'],None,(),['profile_changed',False],
                        ['profile_changed','profile_changed'],['unread_documents','profile_changed']]:
            with self.subTest(reasons=reasons):
                changed=deepcopy(capture);changed['readiness']['reason_codes']=reasons
                with patch.object(review,'read_intake_reference_snapshot',return_value=changed):
                    self.error('parent_invalid',lambda:self.prepare())

    def test_i1_ready_and_reason_empty_consistency(self):
        capture=read_intake_reference_snapshot(self.store,self.intake)
        for ready,reasons in [(False,[]),(True,['profile_changed']),(1,[])]:
            changed=deepcopy(capture);changed['readiness'].update(ready=ready,reason_codes=reasons)
            with patch.object(review,'read_intake_reference_snapshot',return_value=changed):self.error('parent_invalid',lambda:self.prepare())

    def test_unknown_capture_and_receipt_fields_flags_status_hash_are_rejected(self):
        original=review.build_intake_case_reference_receipt
        for mutation in [lambda r:r.update(extra='PRIVATE'),lambda r:r.update(status='PRIVATE'),
                         lambda r:r['verification'].update(operational_authority_granted=True),
                         lambda r:r.update(receipt_id='0'*64),lambda r:r['case_binding'].update(extra='PRIVATE')]:
            def bad(*args,**kwargs):
                result=original(*args,**kwargs);mutation(result);return result
            with patch.object(review,'build_intake_case_reference_receipt',side_effect=bad):self.error('parent_invalid',lambda:self.prepare())

    def test_current_history_registration_parent_shape_and_authority_fail_closed(self):
        prepared,p=self.prepare();registration=self.append(prepared,p);current=ledger.current_reference(self.store,self.intake)
        history=ledger.reference_history(self.store,self.intake)
        for function,value,operation in [('current_reference',current,lambda:self.read()),('reference_history',history,lambda:self.read('history')),
                                          ('record_intake_reference',registration,lambda:self.append(prepared,p))]:
            changed=deepcopy(value);changed['extra']='PRIVATE'
            with patch.object(review,function,return_value=changed):self.error('parent_invalid',operation)
        changed=deepcopy(current);changed['verification']['operational_authority_granted']=True
        with patch.object(review,'current_reference',return_value=changed):self.error('parent_invalid',lambda:self.read())

    def test_parent_raw_and_unknown_errors_are_sanitized_without_context(self):
        for error in [RuntimeError('PRIVATE SQL '+str(self.root)),ValueError('MODEL-A')]:
            with patch.object(review,'read_intake_reference_snapshot',side_effect=error):self.error('parent_invalid',lambda:self.prepare())
        with patch.object(review,'current_reference',side_effect=ledger.IntakeReferenceLedgerError('integrity_invalid')):
            self.error('integrity_invalid',lambda:self.read(),prefix='intake_reference_ledger_')

    def test_missing_or_unknown_parent_error_code_is_sanitized(self):
        for value in ['PRIVATE',None,'MISSING-ATTRIBUTE']:
            error=ledger.IntakeReferenceLedgerError('storage_error')
            if value=='MISSING-ATTRIBUTE':del error.code
            else:error.code=value
            error.args=('PRIVATE SQL '+str(self.root),)
            with patch.object(review,'current_reference',side_effect=error):self.error('parent_invalid',lambda:self.read())

    def test_uninitialized_exact_prepared_is_a_prepared_error(self):
        _,p=self.prepare();malformed=object.__new__(review.PreparedReferenceReview)
        self.error('prepared_invalid',lambda:self.append(malformed,p))

    def test_unavailable_capture_still_rejects_malformed_metadata(self):
        self.revision('PENDING',finish=False);capture=read_intake_reference_snapshot(self.store,self.intake)
        changed=deepcopy(capture);changed['profile']['current_profile_id']='PRIVATE'
        with patch.object(review,'read_intake_reference_snapshot',return_value=changed):self.error('parent_invalid',lambda:self.prepare())

    def test_maximum_16_cases_256_references_and_150_identifiers(self):
        packet,sources,_=fixture038.report_fixture();original=packet['cases'][0]
        while len(original['claims'])<16:
            claim=deepcopy(original['claims'][0]);claim['claim_id']='EXTRA-'+str(len(original['claims']));original['claims'].append(claim)
        packet['corpus_id']='C'*128;packet['cases']=[]
        for i in range(16):
            case=deepcopy(original);case['case_id']='C'*126+f'{i:02}';packet['cases'].append(case)
        self.catalog=fixture038.FccReportCaseCatalog(packet,sources)
        self.context=context_for(self.catalog,ids=[c['case_id'] for c in packet['cases']])
        refs=[]
        for case in self.context['cases']:
            for claim in case['claims']:
                if not claim['evidence']:continue
                evidence=claim['evidence'][0]
                refs.append({'case_id':case['case_id'],'claim_id':claim['claim_id'],**{key:evidence[key] for key in
                    ['evidence_id','document_id','source_sha256','file_page','text_sha256','line_start','line_end']}})
        self.assertGreaterEqual(len(refs),256)
        wire=fixture038.response_wire(self.context,refs=refs[:256]);wire['producer']['name']='P'*150
        self.response=fixture038.decode_case_review_response(json.dumps(wire),self.context,producer_name='P'*150)
        prepared,p=self.prepare();self.assertEqual(len(p['selection']['requested_case_ids']),16)
        self.assertEqual(p['selection']['accepted_reference_count'],256)
        self.append(prepared,p,name='R'*150);self.assertEqual(self.read()['reference_summary']['accepted_reference_count'],256)

    def test_maximum_history100_from_genuine_wrapper_publications(self):
        prepared,p=self.prepare()
        for i in range(100):self.append(prepared,p,name='PUBLICATION-'+str(i))
        page=self.read('history',limit=100)
        self.assertEqual(len(page['records']),100);self.assertIsNone(page['next_before_seq'])
        self.assertEqual([row['seq'] for row in page['records']],list(range(100,0,-1)))
        self.assertEqual(self.counts(),(100,100,1))

    def test_api_no_store_creation_connection_writes_or_pdf_parser(self):
        before=self.base();forbidden=AssertionError('unexpected write/parser')
        with ExitStack() as stack:
            for name in ['__init__','connection','write_blob','register_blob','event']:
                stack.enter_context(patch.object(Store,name,side_effect=forbidden))
            for name in ['labflow.document_extract.extract_document','labflow.intake_documents.extract_document','labflow.intake_worker.SyntheticTextProvider.analyze']:
                stack.enter_context(patch(name,side_effect=forbidden))
            prepared,p=self.prepare();self.append(prepared,p);self.read();self.read('history')
        self.assertEqual(before,self.base())

    def test_bounded_plain_input_before_parent_capture(self):
        nested=[];nested.append(nested)
        for value,code in [({'padding':'x'*(8*1024*1024)},'input_limit'),(nested,'input_limit')]:
            with patch.object(review,'read_intake_reference_snapshot',side_effect=AssertionError('source')):
                self.error(code,lambda:self.prepare(case_context=value))
        self.error('invalid_argument',lambda:self.prepare(producer_name='x'*151))

    def test_strict_history_cursor_keeps_sqlite_integers_without_rounding(self):
        for cursor in [2**53+1,2**63-1]:self.assertEqual(self.read('history',before_seq=cursor)['records'],[])
        for cursor in [0,False,-1,1.5,'1']:self.error('invalid_argument',lambda:self.read('history',before_seq=cursor))

    def test_restart_can_read_history_current_without_reconstructing_prepared(self):
        prepared,p=self.prepare();self.append(prepared,p)
        script="""import json,sys
from pathlib import Path
from labflow.store import Store
from labflow.intake_reference_review import read_reference_review,append_reference_review
store=Store(Path(sys.argv[1]))
history=read_reference_review(store,sys.argv[2],{'schema_version':1,'action':'history','limit':20,'before_seq':None})
current=read_reference_review(store,sys.argv[2],{'schema_version':1,'action':'current'},allow_retained_reads=True)
print(json.dumps({'history':len(history['records']),'status':current['status'],'private':'reference_receipt' in current}))
"""
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',script,str(self.store.root),self.intake],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=60)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),{'history':1,'status':'current','private':False})
