import copy
from pathlib import Path
import tempfile
import unittest

from labflow.active_intake import register_source, scan_source, intake_status
from labflow.intake_jobs import claim_job, complete_job, fail_job, respond, notifications
from labflow.store import Store


class IntakeJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.inbox=self.root/'inbox'
        self.inbox.mkdir()
        self.store=Store(self.root/'state')
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=1)
        self.put('one','request.txt','Handheld device with voice calls and touchscreen.\nRequested market: US.\nPurpose: certification.\n')
        self.scan()

    def put(self,bundle,name,text):
        path=self.inbox/bundle/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8')

    def scan(self,now=100):
        scan_source(self.store,'INBOX',now=now)
        return scan_source(self.store,'INBOX',now=now+1)

    def analysis(self,job,market=True):
        document=next(d for d in job['documents'] if d['path']=='request.txt')
        def fact(field,value,line,status='explicit',role='request'):
            return {'field':field,'value':value,'status':status,'evidence':[{
                'path':document['path'],'sha256':document['sha256'],'line_start':line,'line_end':line,
                'quote':document['text'].splitlines()[line-1],'role':role}]}
        facts=[fact('product_type','smartphone',1,'inferred'),fact('purpose','certification',3)]
        if market:
            facts.append(fact('market','US',2))
        return {'schema_version':1,'producer':{'kind':'fixture','name':'contract-test'},
                'identity':'single','facts':facts,'missing_fields':['antenna_gain','power_target']}

    def finish(self,job=None,analysis=None,now=110):
        job=job or claim_job(self.store,'worker',now=102)
        return complete_job(self.store,job['job_id'],job['token'],analysis or self.analysis(job),now=now)

    def test_lease_excludes_other_workers_and_expiry_fences_old_result(self):
        first=claim_job(self.store,'worker-a',now=102,lease_seconds=10)
        self.assertIsNone(claim_job(self.store,'worker-b',now=105))
        second=claim_job(Store(self.store.root),'worker-b',now=112)
        self.assertEqual(second['job_id'],first['job_id'])
        self.assertNotEqual(second['token'],first['token'])
        with self.assertRaisesRegex(ValueError,'lease'):
            self.finish(first,now=113)
        self.finish(second,now=113)

    def test_analysis_preserves_inference_and_real_missing_fields(self):
        result=self.finish()
        self.assertEqual(result['facts']['product_type']['value'],'smartphone')
        self.assertEqual(result['facts']['product_type']['status'],'inferred')
        self.assertEqual(result['facts']['market']['value'],'US')
        self.assertEqual({q['key'] for q in result['questions']},{'missing_antenna_gain','missing_power_target'})
        self.assertEqual(result['next_action'],'needs_information')
        self.assertEqual(result['measurement_support'],'unverified')
        self.assertFalse(intake_status(self.store)[0]['delegated'])

    def test_reference_report_does_not_define_requested_market(self):
        job=claim_job(self.store,'worker',now=102)
        analysis=self.analysis(job)
        analysis['facts'][-1]['evidence'][0]['role']='reference'
        result=self.finish(job,analysis)
        self.assertNotIn('market',result['facts'])
        self.assertIn('missing_market',{q['key'] for q in result['questions']})

    def test_fabricated_or_cross_document_quotes_are_rejected_atomically(self):
        job=claim_job(self.store,'worker',now=102)
        for field,value in [('quote','not present'),('sha256','0'*64),('line_start',0),('line_end',999)]:
            analysis=self.analysis(job)
            analysis['facts'][0]['evidence'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.finish(job,analysis)
        self.assertIsNone(intake_status(self.store)[0]['analysis'])
        self.assertEqual(notifications(self.store),[])

    def test_duplicate_completion_is_idempotent_but_changed_result_is_rejected(self):
        job=claim_job(self.store,'worker',now=102)
        first=self.finish(job)
        self.assertEqual(self.finish(job,now=500),first)
        self.assertEqual(len(notifications(self.store)),1)
        changed=self.analysis(job)
        changed['identity']='ambiguous'
        with self.assertRaises(ValueError):
            self.finish(job,changed,now=500)

    def test_supplement_fences_old_revision_even_before_new_analysis(self):
        old=claim_job(self.store,'worker',now=102)
        self.put('one','extra.txt','New product information')
        self.scan(120)
        with self.assertRaises(ValueError):
            self.finish(old,now=122)
        new=claim_job(self.store,'worker',now=122)
        self.assertEqual(new['revision'],2)

    def test_model_failure_is_durable_and_retries_have_a_limit(self):
        for n in range(3):
            job=claim_job(Store(self.store.root),'worker',now=102+n)
            self.assertEqual(job['attempt'],n+1)
            fail_job(self.store,job['job_id'],job['token'],now=102+n)
        self.assertIsNone(claim_job(self.store,'worker',now=200))
        with self.store.connection() as con:
            row=con.execute('SELECT state,error_code FROM intake_jobs').fetchone()
        self.assertEqual(tuple(row),('failed','model_error'))

    def test_generic_instruction_is_resolved_once_and_reuses_delegation(self):
        result=respond(self.store,'USER-1','proceed')
        self.assertEqual(result,respond(Store(self.store.root),'USER-1','proceed'))
        self.assertTrue(intake_status(self.store)[0]['delegated'])
        job=claim_job(self.store,'worker',now=102)
        analysis=self.analysis(job)
        analysis['missing_fields']=[]
        self.assertEqual(self.finish(job,analysis)['next_action'],'prepare_plan')

    def test_multiple_requests_require_target_without_delegating_either(self):
        self.put('two','request.txt','Remote control.\nRequested market: EU.\nPurpose: compliance.\n')
        self.scan(120)
        result=respond(self.store,'USER-1','proceed')
        self.assertEqual(result['status'],'needs_target')
        self.assertEqual(len(result['candidates']),2)
        self.assertFalse(any(c['delegated'] for c in intake_status(self.store)))

    def test_defer_survives_reopen_and_unchanged_supplement_is_quiet(self):
        self.finish()
        intake=intake_status(self.store)[0]['intake_id']
        respond(self.store,'USER-1','defer',intake_id=intake)
        count=len(notifications(self.store))
        self.put('one','unrelated.txt','Additional photo description')
        self.scan(120)
        job=claim_job(Store(self.store.root),'worker',now=122)
        result=self.finish(job,now=125)
        self.assertEqual(result['next_action'],'deferred')
        self.assertEqual(len(notifications(self.store)),count)

    def test_answers_resolve_questions_and_resume_without_reasking(self):
        self.finish()
        intake=intake_status(self.store)[0]['intake_id']
        respond(self.store,'USER-1','proceed',intake_id=intake)
        respond(self.store,'USER-2','answer',intake_id=intake,answers={'antenna_gain':'2 dBi','power_target':'14 dBm'})
        current=intake_status(self.store,intake)['analysis']
        self.assertEqual(current['questions'],[])
        self.assertEqual(current['next_action'],'prepare_plan')
        self.put('one','unrelated.txt','Additional photo description')
        self.scan(120)
        job=claim_job(self.store,'worker',now=122)
        self.assertEqual(self.finish(job,now=125)['questions'],[])

    def test_conflicting_facts_and_changed_answer_basis_reopen_question(self):
        self.finish()
        intake=intake_status(self.store)[0]['intake_id']
        respond(self.store,'ANSWER','answer',intake_id=intake,answers={'market':'US'})
        self.put('one','other.txt','Requested market: EU.')
        self.scan(120)
        job=claim_job(self.store,'worker',now=122)
        analysis=self.analysis(job)
        doc=next(d for d in job['documents'] if d['path']=='other.txt')
        duplicate=copy.deepcopy(analysis['facts'][-1])
        duplicate['value']='EU'
        duplicate['evidence']=[{'path':doc['path'],'sha256':doc['sha256'],'line_start':1,'line_end':1,'quote':doc['text'],'role':'request'}]
        analysis['facts'].append(duplicate)
        result=self.finish(job,analysis,now=125)
        self.assertIn('conflict_market',{q['key'] for q in result['questions']})
        self.assertNotIn('market',result['facts'])

    def test_document_instruction_never_grants_authority_and_extra_keys_fail(self):
        job=claim_job(self.store,'worker',now=102)
        analysis=self.analysis(job)
        analysis['delegated']=True
        with self.assertRaises(ValueError):
            self.finish(job,analysis)
        self.assertFalse(intake_status(self.store)[0]['delegated'])

    def test_unsupported_document_remains_visible_as_parser_requirement(self):
        self.put('one','image.pdf','%PDF-not-a-parser-fixture')
        self.scan(120)
        job=claim_job(self.store,'worker',now=122)
        document=next(d for d in job['documents'] if d['path']=='image.pdf')
        self.assertEqual(document['parse_status'],'requires_parser')
        result=self.finish(job,now=125)
        self.assertIn('unread_documents',{q['key'] for q in result['questions']})

    def test_answered_state_is_not_announced_again_on_unrelated_supplement(self):
        self.finish()
        intake=intake_status(self.store)[0]['intake_id']
        respond(self.store,'ANSWER','answer',intake_id=intake,answers={'antenna_gain':'2 dBi','power_target':'14 dBm'})
        count=len(notifications(self.store))
        self.put('one','photo.txt','Unrelated description')
        self.scan(120)
        self.finish(claim_job(self.store,'worker',now=122),now=125)
        self.assertEqual(len(notifications(self.store)),count)

    def test_pending_changed_upload_blocks_both_claim_and_completion(self):
        old=claim_job(self.store,'worker',now=102)
        self.put('one','unfinished.part','partial')
        scan_source(self.store,'INBOX',now=110)
        with self.assertRaises(ValueError):
            self.finish(old,now=111)
        self.assertIsNone(claim_job(self.store,'second',now=500))

    def test_crashed_workers_exhaust_lease_attempts(self):
        for now in [102,112,122]:
            self.assertIsNotNone(claim_job(self.store,'worker',now=now,lease_seconds=10))
        self.assertIsNone(claim_job(self.store,'worker',now=132))
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT state FROM intake_jobs').fetchone()[0],'failed')

    def test_reusing_user_event_id_cannot_change_disposition(self):
        respond(self.store,'EVENT','defer')
        with self.assertRaises(ValueError):
            respond(self.store,'EVENT','proceed')
        self.assertTrue(intake_status(self.store)[0]['deferred'])

    def test_nonphone_eu_request_has_no_fcc_or_smartphone_default(self):
        self.put('one','request.txt','Infrared remote control.\nRequested market: EU.\nPurpose: development evaluation.\n')
        self.scan(120)
        job=claim_job(self.store,'worker',now=122)
        analysis=self.analysis(job)
        analysis['facts'][0]['value']='remote_control'
        analysis['facts'][1]['value']='development evaluation'
        analysis['facts'][2]['value']='EU'
        analysis['missing_fields']=[]
        result=self.finish(job,analysis,now=125)
        self.assertEqual(result['facts']['product_type']['value'],'remote_control')
        self.assertEqual(result['facts']['market']['value'],'EU')
        self.assertEqual(result['measurement_support'],'unverified')

    def test_failed_analysis_is_visible_in_intake_status(self):
        for n in range(3):
            job=claim_job(self.store,'worker',now=102+n)
            fail_job(self.store,job['job_id'],job['token'],now=102+n)
        status=intake_status(self.store)[0]
        self.assertEqual(status['status'],'analysis_failed')
        self.assertEqual(status['jobs'][-1]['error_code'],'model_error')

    def test_duplicate_completion_cannot_hide_corrupted_evidence(self):
        job=claim_job(self.store,'worker',now=102)
        analysis=self.analysis(job)
        self.finish(job,analysis)
        self.store.blob_path(job['documents'][0]['sha256']).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'corrupted'):
            self.finish(job,analysis,now=500)

    def test_analyzer_omission_cannot_silently_close_unresolved_questions(self):
        self.finish()
        self.put('one','extra.txt','Still waiting for antenna and power documents')
        self.scan(120)
        job=claim_job(self.store,'worker',now=122)
        analysis=self.analysis(job)
        analysis['missing_fields']=[]
        result=self.finish(job,analysis,now=125)
        self.assertEqual({q['key'] for q in result['questions']},{'missing_antenna_gain','missing_power_target'})


if __name__=='__main__':
    unittest.main()
