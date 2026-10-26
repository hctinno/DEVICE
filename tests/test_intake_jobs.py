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
        self.assertEqual(document['parse_status'],'malformed_pdf')
        self.assertIsNone(document['text'])
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


class PreclaimContextTests(unittest.TestCase):
    """Authored synthetic registration; no installed CLI, model, or hardware."""
    PUBLIC = ('job_id', 'intake_id', 'revision', 'synthetic', 'documents',
              'analysis_context_id', 'analysis_contract', 'instructions')
    NAME = 'SYN-PRECLAIM'

    def setUp(self):
        import json
        from labflow import intake_jobs
        self.jobs = intake_jobs
        self.tmp = tempfile.TemporaryDirectory(prefix='preclaim-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inbox = self.root / 'inbox'
        bundle = self.inbox / 'bundle'
        bundle.mkdir(parents=True)
        (bundle / 'request.txt').write_text('Synthetic sample for candidate review.\n', encoding='utf-8')
        initial = Store(self.root / 'state')
        register_source(initial, 'PRECLAIM-SYN', self.inbox, synthetic=True, settle_seconds=1)
        scan_source(initial, 'PRECLAIM-SYN', now=100, synthetic_only=True)
        receipt = scan_source(initial, 'PRECLAIM-SYN', now=101, synthetic_only=True)
        accepted = receipt['accepted'][0]
        with initial.connection() as con:
            revision = con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                                   (accepted['intake_id'], accepted['revision'])).fetchone()
            self.selection = dict(source_id='PRECLAIM-SYN', intake_id=accepted['intake_id'],
                revision=accepted['revision'], job_id=accepted['job_id'],
                revision_fingerprint=revision['fingerprint'], files=json.loads(revision['files_json']))
        initial.close()
        self.store = Store.open_existing(str(initial.root))
        self.addCleanup(self.store.close)
        self.fake_calls = []

    def prepare(self, selection=None, **kwargs):
        api = getattr(self.jobs, 'prepare_registered_synthetic_context', None)
        self.assertTrue(callable(api), 'approved public preclaim API is absent')
        return api(self.store, self.selection if selection is None else selection,
                   producer_name=kwargs.get('producer_name', self.NAME))

    def business(self):
        with self.store.connection() as con:
            names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name: sorted(tuple(r) for r in con.execute('SELECT * FROM "'+name+'"'))
                    for name in names if name != 'blobs'}

    def job(self):
        with self.store.connection() as con:
            return dict(con.execute('SELECT * FROM intake_jobs WHERE job_id=?',
                                    (self.selection['job_id'],)).fetchone())

    def error(self, suffix, call=None):
        with self.assertRaises(ValueError) as caught:
            (call or self.prepare)()
        error = caught.exception
        self.assertEqual(type(error), ValueError)
        self.assertEqual(error.args, ('intake_preclaim_context_'+suffix,))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        return error

    def rescan(self, name, payload):
        import json
        (self.inbox / 'bundle' / name).write_bytes(payload)
        scan_source(self.store, 'PRECLAIM-SYN', now=200, synthetic_only=True)
        item = scan_source(self.store, 'PRECLAIM-SYN', now=201, synthetic_only=True)['accepted'][0]
        with self.store.connection() as con:
            row = con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                              (item['intake_id'], item['revision'])).fetchone()
        self.selection = dict(source_id='PRECLAIM-SYN', intake_id=item['intake_id'],
            revision=item['revision'], job_id=item['job_id'],
            revision_fingerprint=row['fingerprint'], files=json.loads(row['files_json']))

    def once(self, context):
        from unittest.mock import patch
        from labflow.codex_intake_once import run_codex_intake_once
        from test_codex_intake_once import OnceTests
        executable = self.root / 'codex.exe'
        executable.write_bytes(b'fake path; never executed')
        evidence = self.root / 'once-evidence'
        evidence.mkdir()
        def fake(*args, **kwargs):
            return OnceTests.fake_d2(self, *args, **kwargs)
        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=fake) as d2, \
                patch('labflow.codex_intake_once.claim_job', wraps=self.jobs.claim_job) as claim:
            result = run_codex_intake_once(self.store, context, worker_id='preclaim-once',
                producer_name=self.NAME, executable=executable, requested_model='gpt-6.1-sol',
                evidence_root=evidence, authorization_ref='SYN-PRECLAIM-ONCE')
        self.assertEqual(claim.call_count, 1)
        return result, d2.call_count

    def test_registered_source6_prepares_actual_public8_without_claim(self):
        from unittest.mock import patch
        from labflow.store import canonical
        before, selection = self.business(), copy.deepcopy(self.selection)
        old_blobs = set((self.store.root / 'blobs').iterdir())
        with patch.object(self.jobs, 'claim_job') as claim, patch.object(self.jobs, 'complete_job') as complete, \
                patch.object(self.jobs, 'fail_job') as fail, patch.object(self.jobs.uuid, 'uuid4') as token, \
                patch.object(Store, 'close') as close:
            context = self.prepare()
        for call in (claim, complete, fail, token, close):
            call.assert_not_called()
        self.assertEqual(set(context), set(self.PUBLIC))
        self.assertEqual(context['job_id'], selection['job_id'])
        self.assertIs(context['synthetic'], True)
        self.assertEqual(context['analysis_contract']['schema_version'], 1)
        self.assertEqual(self.job()['attempt'], 0)
        self.assertEqual(before, self.business())
        self.assertEqual(self.selection, selection)
        self.assertEqual(len(set((self.store.root / 'blobs').iterdir()) - old_blobs), 1)
        context['documents'][0]['path'] = 'caller-mutated.txt'
        again = self.prepare()
        self.assertEqual(again['documents'][0]['path'], 'request.txt')
        self.assertNotIn('token', canonical(again))

    def test_separate_claim_oracle_matches_prepared_public8(self):
        from labflow.store import canonical
        context = self.prepare()
        claimed = self.jobs.claim_job(self.store, 'oracle', synthetic_only=True)
        self.assertEqual(claimed['attempt'], 1)
        self.assertEqual(canonical(context), canonical({k: claimed[k] for k in self.PUBLIC}))

    def test_fresh_once_uses_preclaim_output_without_prior_claim(self):
        context = self.prepare()
        self.assertEqual(self.job()['attempt'], 0)
        result, d2 = self.once(context)
        self.assertEqual((result['status'], result['strict_decode'], d2), ('completed', 'accepted', 1))
        self.assertEqual(result['job']['attempt'], 1)
        self.assertEqual(self.job()['attempt'], 1)
        self.assertEqual(self.job()['state'], 'completed')
        self.assertEqual(result['assessment']['status'], 'not_assessed')

    def test_once_rechecks_public_context_and_current_revision(self):
        context = self.prepare()
        self.rescan('request.txt', b'Changed synthetic request.\n')
        result, d2 = self.once(context)
        self.assertEqual(d2, 0)
        self.assertIn('codex_intake_once_scope_mismatch', [e['code'] for e in result['errors']])

    def test_once_retains_existing_claim_eligibility(self):
        context = self.prepare()
        held = self.jobs.claim_job(self.store, 'other-worker', synthetic_only=True)
        self.assertEqual(held['attempt'], 1)
        result, d2 = self.once(context)
        self.assertEqual((result['status'], d2), ('idle', 0))

    def test_once_can_accept_same_public8_after_genuine_claim_and_fail(self):
        context = self.prepare()
        held = self.jobs.claim_job(self.store, 'intervening-worker', synthetic_only=True)
        self.jobs.fail_job(self.store, held['job_id'], held['token'])
        self.assertEqual((self.job()['state'], self.job()['attempt']), ('queued', 1))
        result, d2 = self.once(context)
        self.assertEqual((result['status'], result['job']['attempt'], d2), ('completed', 2, 1))

    def test_genuine_queued_failure_private_fields_are_preserved(self):
        from labflow.store import canonical
        held = self.jobs.claim_job(self.store, 'prior-worker', synthetic_only=True)
        self.jobs.fail_job(self.store, held['job_id'], held['token'])
        before = self.business()
        context = self.prepare()
        self.assertEqual(before, self.business())
        self.assertEqual(self.job()['token'], held['token'])
        self.assertEqual(self.job()['attempt'], 1)
        self.assertNotIn(held['token'], canonical(context))
        self.assertNotIn('prior-worker', canonical(context))

    def test_native_selection_rejects_types_and_subclasses_without_hooks(self):
        from unittest.mock import patch
        class Dict(dict):
            def items(self):
                raise AssertionError('mapping hook must not run')
        class Text(str):
            def __eq__(self, other):
                raise AssertionError('string hook must not run')
            __hash__ = str.__hash__
        cases = [None, [], Dict(self.selection), {**self.selection, 'approved': True},
                 {**self.selection, 'revision': True}, {**self.selection, 'revision': 0},
                 {**self.selection, 'source_id': Text('PRECLAIM-SYN')},
                 {**self.selection, 'files': tuple(self.selection['files'])},
                 {**self.selection, 'files': [Dict(self.selection['files'][0])]},
                 {**self.selection, 'files': [{**self.selection['files'][0], 'bytes': True}]},
                 {**self.selection, 'files': [{**self.selection['files'][0], 'path': '../escape'}]},
                 {**self.selection, 'files': [{**self.selection['files'][0], 'path': '\ud800'}]}]
        keyed = {Text(k) if k == 'source_id' else k: v for k, v in self.selection.items()}
        cases.append(keyed)
        for value in cases:
            with self.subTest(kind=type(value).__name__), patch.object(self.jobs, '_prepare') as prepare:
                self.error('invalid_input', lambda: getattr(self.jobs, 'prepare_registered_synthetic_context')(
                    self.store, value, producer_name=self.NAME))
                prepare.assert_not_called()

    def test_invalid_producer_is_rejected_before_preparation(self):
        from unittest.mock import patch
        for producer in (None, '', ' ', 1, 'x'*201, '\ud800'):
            with self.subTest(producer=repr(producer)), patch.object(self.jobs, '_prepare') as prepare:
                self.error('invalid_input', lambda: self.prepare(producer_name=producer))
                prepare.assert_not_called()
        with self.assertRaises(TypeError):
            getattr(self.jobs, 'prepare_registered_synthetic_context')(self.store, self.selection)

    def test_wrong_registered_binding_has_no_fallback(self):
        from unittest.mock import patch
        cases = [{**self.selection, 'intake_id': 'I-OTHER'},
                 {**self.selection, 'source_id': 'OTHER'},
                 {**self.selection, 'revision': 2},
                 {**self.selection, 'revision_fingerprint': '0'*64}]
        for selection in cases:
            with self.subTest(selection=selection), patch.object(self.jobs, '_prepare') as prepare:
                self.error('scope_mismatch', lambda: self.prepare(selection))
                prepare.assert_not_called()
        self.error('not_ready', lambda: self.prepare({**self.selection, 'job_id': 'J-ABSENT'}))

    def test_files_order_is_not_sorted_or_repaired(self):
        import hashlib
        from labflow.store import canonical
        self.rescan('other.txt', b'Other authored synthetic file.\n')
        selection = copy.deepcopy(self.selection)
        selection['files'].reverse()
        selection['revision_fingerprint'] = hashlib.sha256(canonical(selection['files']).encode()).hexdigest()
        self.error('scope_mismatch', lambda: self.prepare(selection))

    def test_non_synthetic_source_and_revision_reject_before_prepare(self):
        from unittest.mock import patch
        for table in ('intake_sources', 'intake_revisions'):
            with self.subTest(table=table):
                with self.store.connection() as con:
                    con.execute('UPDATE '+table+' SET synthetic=0')
                with patch.object(self.jobs, '_prepare') as prepare, patch.object(Store, 'verify_blob') as raw:
                    self.error('not_ready')
                    prepare.assert_not_called(); raw.assert_not_called()
                with self.store.connection() as con:
                    con.execute('UPDATE '+table+' SET synthetic=1')

    def test_running_expired_states_attempt_limit_and_upload_reject(self):
        from unittest.mock import patch
        for state, attempt, lease in [('running', 0, 0), ('running', 1, 99999999999),
                                      ('completed', 1, None), ('failed', 3, None), ('queued', 3, None)]:
            with self.subTest(state=state, attempt=attempt):
                with self.store.connection() as con:
                    con.execute('UPDATE intake_jobs SET state=?,attempt=?,lease_until=?', (state, attempt, lease))
                with patch.object(self.jobs, '_prepare') as prepare:
                    self.error('not_ready'); prepare.assert_not_called()
        with self.store.connection() as con:
            con.execute("UPDATE intake_jobs SET state='queued',attempt=0,lease_until=NULL")
            con.execute("UPDATE intakes SET status='upload_incomplete'")
        self.error('not_ready')

    def test_malformed_pdf_remains_an_unread_schema2_context_without_claim(self):
        self.rescan('SOURCE.PDF', b'%PDF-authored-synthetic-no-parser\n')
        before = self.business()
        try:
            context = self.prepare()
        except ValueError as error:
            self.fail('PDF context is still categorically unsupported: '+str(error))
        document = next(item for item in context['documents'] if item['path']=='SOURCE.PDF')
        self.assertEqual(context['analysis_contract']['schema_version'],2)
        self.assertIsNone(document['text']);self.assertEqual(document['pages'],[])
        self.assertFalse(document['complete']);self.assertNotEqual(document['parse_status'],'ok')
        self.assertTrue(document['issues']);self.assertEqual(self.job()['state'],'queued')
        self.assertEqual(before, self.business())

    def test_unsupported_file_remains_visible_with_null_text(self):
        self.rescan('image.bin', b'authored unsupported synthetic content')
        context = self.prepare()
        document = next(d for d in context['documents'] if d['path']=='image.bin')
        self.assertIsNone(document['text'])
        self.assertEqual(document['parse_status'], 'requires_parser')

    def test_every_private_job_snapshot_field_is_rechecked(self):
        from unittest.mock import patch
        original = self.jobs._prepare
        for field, changed in [('state', 'running'), ('attempt', 1), ('token', 'PRIVATE-TOKEN'),
                               ('lease_until', 123.0), ('worker_id', 'PRIVATE-WORKER'),
                               ('result_json', '{"private":1}'), ('error_code', 'PRIVATE-ERROR'),
                               ('created_at', 222.0)]:
            before = self.job()
            def race(store, revision):
                prepared = original(store, revision)
                with store.connection() as con:
                    con.execute('UPDATE intake_jobs SET '+field+'=? WHERE job_id=?', (changed, before['job_id']))
                return prepared
            with self.subTest(field=field), patch.object(self.jobs, '_prepare', side_effect=race) as prepare:
                self.error('state_changed')
                self.assertEqual(prepare.call_count, 1)
            self.assertEqual(self.job()[field], changed)
            with self.store.connection() as con:
                con.execute('UPDATE intake_jobs SET '+field+'=? WHERE job_id=?', (before[field], before['job_id']))

    def test_source_and_current_revision_changes_during_prepare_are_rejected(self):
        from unittest.mock import patch
        original = self.jobs._prepare
        for sql, restore in [("UPDATE intake_sources SET synthetic=0", "UPDATE intake_sources SET synthetic=1"),
                             ("UPDATE intakes SET revision=2", "UPDATE intakes SET revision=1")]:
            def race(store, revision):
                prepared = original(store, revision)
                with store.connection() as con:
                    con.execute(sql)
                return prepared
            with self.subTest(sql=sql), patch.object(self.jobs, '_prepare', side_effect=race):
                self.error('state_changed')
            with self.store.connection() as con:
                con.execute(restore)

    def test_retained_tamper_failure_preserves_business_rows_and_failed_blob(self):
        from unittest.mock import patch
        before, original, retained = self.business(), self.jobs._prepare, []
        def tamper(store, revision):
            prepared = original(store, revision)
            path = store.blob_path(prepared['context_id'])
            path.write_bytes(b'preserved failed artifact')
            retained.append(path)
            return prepared
        with patch.object(self.jobs, '_prepare', side_effect=tamper):
            self.error('preparation_failed')
        self.assertEqual(before, self.business())
        self.assertEqual(retained[0].read_bytes(), b'preserved failed artifact')

    def test_genuine_profile_change_is_not_success(self):
        from unittest.mock import patch
        from labflow import intake_documents
        profile = intake_documents._profile()
        changed = {**profile, 'max_text_bytes': 0}
        with patch.object(intake_documents, '_profile', side_effect=[profile, changed]):
            self.error('preparation_failed')

    def test_existing_context_and_once_prompt_limits(self):
        from unittest.mock import patch
        from labflow import intake_documents
        with patch.object(intake_documents, 'MAX_CONTEXT_BYTES', 64):
            self.error('limit_exceeded')
        self.rescan('request.txt', b'x'*(256*1024))
        before = self.business()
        self.error('limit_exceeded')
        self.assertEqual(before, self.business())

    def test_controls_keep_the_same_object_without_new_attributes(self):
        from unittest.mock import patch
        for phase in ('_prepare', '_verify'):
            for kind in (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
                control = kind('control')
                before = dict(control.__dict__)
                with self.subTest(phase=phase, kind=kind.__name__), \
                        patch.object(self.jobs, phase, side_effect=control):
                    with self.assertRaises(kind) as caught:
                        self.prepare()
                    self.assertIs(caught.exception, control)
                    self.assertEqual(control.__dict__, before)
        self.assertEqual(self.store._existing_binding.active, 0)

    def test_fixed_failures_remove_raw_and_ambient_exception_context(self):
        from unittest.mock import patch
        try:
            raise RuntimeError('PRIVATE-AMBIENT')
        except RuntimeError:
            with patch.object(self.jobs, '_prepare', side_effect=OSError('PRIVATE-PATH-SQL')):
                self.error('preparation_failed')

    def test_closed_store_preserves_genuine_error_and_borrowed_close_is_zero(self):
        from unittest.mock import patch
        from labflow.store import StoreOpenError
        with patch.object(Store, 'close') as close:
            self.prepare()
            close.assert_not_called()
        self.store.close()
        with self.assertRaises(StoreOpenError) as caught:
            self.prepare()
        self.assertEqual(caught.exception.code, 'store_open_closed')

    def test_exact_store_type_rejects_untrusted_connection_hook(self):
        class OtherStore(Store):
            def connection(self):
                raise AssertionError('untrusted Store hook')
        for value in (None, str(self.store.root), object.__new__(OtherStore)):
            self.error('invalid_input', lambda: self.jobs.prepare_registered_synthetic_context(
                value, self.selection, producer_name=self.NAME))

    def test_input_alias_changes_do_not_replace_the_registered_snapshot(self):
        from unittest.mock import patch
        original = self.jobs._prepare
        expected = copy.deepcopy(self.selection)
        def mutate_input(store, revision):
            self.selection['files'][0]['path'] = 'caller-changed.txt'
            self.selection['job_id'] = 'J-CALLER-CHANGED'
            return original(store, revision)
        with patch.object(self.jobs, '_prepare', side_effect=mutate_input):
            context = self.prepare()
        self.assertEqual(context['job_id'], expected['job_id'])
        self.assertEqual(context['documents'][0]['path'], expected['files'][0]['path'])

    def test_original_retained_bytes_are_verified_and_failures_preserved(self):
        before = self.business()
        path = self.store.blob_path(self.selection['files'][0]['sha256'])
        path.write_bytes(b'authored corruption remains as failure evidence')
        self.error('preparation_failed')
        self.assertEqual(before, self.business())
        self.assertEqual(path.read_bytes(), b'authored corruption remains as failure evidence')

    def test_preparation_does_not_reopen_the_original_source_folder(self):
        import shutil
        shutil.rmtree(self.inbox)
        self.assertEqual(self.prepare()['documents'][0]['path'], 'request.txt')


G3_PDF_CONTEXT_OBSERVATIONS=[]


class PreclaimPDFContextTests(unittest.TestCase):
    """Fresh queued authored PDFs; public G3 only, no host/model/old Store."""
    NAME='SYN-G3-PDF-CONTEXT'
    PUBLIC=PreclaimContextTests.PUBLIC
    prepare=PreclaimContextTests.prepare
    business=PreclaimContextTests.business
    job=PreclaimContextTests.job
    error=PreclaimContextTests.error

    def setUp(self):
        import io
        import json
        from reportlab.pdfgen import canvas
        from labflow import intake_jobs
        self.jobs=intake_jobs;self.tmp=tempfile.TemporaryDirectory(prefix='g3-pdf-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.inbox=self.root/'inbox';bundle=self.inbox/'bundle';bundle.mkdir(parents=True)
        self.source=bundle/'REQUEST.PDF';buffer=io.BytesIO();pdf=canvas.Canvas(buffer)
        for lines in (('product_type: instrument','model: AUTHORED-G3-PDF'),
                      ('purpose: queued schema2 context check','features: authored simulation only')):
            text=pdf.beginText(48,790)
            for line in lines:text.textLine(line)
            pdf.drawText(text);pdf.showPage()
        pdf.save();self.source.write_bytes(buffer.getvalue())
        initial=Store(self.root/'state');register_source(initial,'G3-PDF-SYN',self.inbox,synthetic=True,settle_seconds=1)
        scan_source(initial,'G3-PDF-SYN',now=100,synthetic_only=True)
        item=scan_source(initial,'G3-PDF-SYN',now=101,synthetic_only=True)['accepted'][0]
        with initial.connection() as con:
            revision=con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',(item['intake_id'],item['revision'])).fetchone()
        self.selection=dict(source_id='G3-PDF-SYN',intake_id=item['intake_id'],revision=item['revision'],job_id=item['job_id'],
            revision_fingerprint=revision['fingerprint'],files=json.loads(revision['files_json']))
        initial.close();self.store=Store.open_existing(str(initial.root));self.addCleanup(self.store.close)
        self.record=dict(case=self._testMethodName,source='fresh own synthetic queued PDF')
        self.addCleanup(self.capture)

    def capture(self):
        files={}
        for path in self.root.rglob('*'):
            if path.is_file() and path.suffix not in ('.sqlite3',):
                files[path.relative_to(self.root).as_posix()]=path.read_bytes()
        self.assertLessEqual(len(files),192);self.assertLessEqual(sum(map(len,files.values())),8*1024*1024)
        G3_PDF_CONTEXT_OBSERVATIONS.append(dict(self.record,files=files))

    def source_pin(self):
        import hashlib
        import os
        with self.source.open('rb') as stream:raw=stream.read();info=os.fstat(stream.fileno())
        return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),ino=info.st_ino,nlink=info.st_nlink,mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns)

    def ready(self):
        try:return self.prepare()
        except ValueError as error:self.fail('queued PDF schema2 context support missing: '+str(error))

    def rescan(self,name,payload):
        import json
        (self.inbox/'bundle'/name).write_bytes(payload)
        scan_source(self.store,'G3-PDF-SYN',now=200,synthetic_only=True)
        item=scan_source(self.store,'G3-PDF-SYN',now=201,synthetic_only=True)['accepted'][0]
        with self.store.connection() as con:
            row=con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',(item['intake_id'],item['revision'])).fetchone()
        self.selection=dict(source_id='G3-PDF-SYN',intake_id=item['intake_id'],revision=item['revision'],job_id=item['job_id'],
            revision_fingerprint=row['fingerprint'],files=json.loads(row['files_json']))

    def test_queued_pdf_produces_retained_public8_schema2_without_business_DML_or_claim(self):
        import json
        import sqlite3
        from unittest.mock import patch
        before=self.business();source=self.source_pin();tables=set(before);attempts=[];connect=sqlite3.connect
        def observing(*args,**kwargs):
            con=connect(*args,**kwargs)
            def authorizer(action,one,two,database,trigger):
                if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and one in tables:
                    attempts.append(dict(action=action,table=one));return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            con.set_authorizer(authorizer);return con
        with patch.object(sqlite3,'connect',side_effect=observing),\
             patch.object(self.jobs,'claim_job',side_effect=AssertionError('G3 claimed')),\
             patch.object(self.jobs,'complete_job',side_effect=AssertionError('G3 completed')),\
             patch.object(self.jobs,'fail_job',side_effect=AssertionError('G3 failed job')),\
             patch.object(Store,'close',side_effect=AssertionError('G3 closed borrowed Store')):
            context=self.ready()
        self.assertEqual(attempts,[]);self.assertEqual(before,self.business());self.assertEqual(source,self.source_pin())
        self.assertEqual(set(context),set(self.PUBLIC));self.assertIs(context['synthetic'],True)
        self.assertEqual(context['analysis_contract']['schema_version'],2)
        self.assertEqual(context['analysis_contract']['context_id'],context['analysis_context_id'])
        document=context['documents'][0];self.assertEqual(document['format'],'pdf');self.assertTrue(document['complete'])
        self.assertEqual(document['total_pages'],2);self.assertEqual(len(document['pages']),2)
        manifest=json.loads(self.store.verify_blob(context['analysis_context_id']).read_bytes())
        extraction=json.loads(self.store.verify_blob(document['extraction_id']).read_bytes())
        self.assertEqual(manifest['documents'],context['documents']);self.assertEqual(extraction['result']['pages'],document['pages'])
        self.assertEqual((self.job()['state'],self.job()['attempt']),('queued',0))
        self.record.update(context=context,source_pin=source,business_DML=attempts,claim_calls=0,borrowed_close_calls=0)

    def test_mixed_text_pdf_prompt_and_strict_page_citations_remain_bound_to_original_context(self):
        import json
        from labflow.intake_model_boundary import build_analysis_prompt,decode_analysis_response
        from labflow.store import canonical
        self.rescan('notes.txt',b'manufacturer: Synthetic Vendor\n')
        before=self.business();context=self.ready();prompt=build_analysis_prompt(context,producer_name=self.NAME)
        self.assertEqual(json.loads(prompt['messages'][1]['content']),context)
        self.assertEqual(context['analysis_contract']['schema_version'],2)
        self.assertEqual(prompt['binding']['analysis_context_id'],context['analysis_context_id'])
        document=next(item for item in context['documents'] if item['format']=='pdf');page=document['pages'][0]
        evidence=dict(kind='pdf_page',path='REQUEST.PDF',sha256=document['sha256'],line_start=2,line_end=2,quote='model: AUTHORED-G3-PDF',
            role='request',extraction_id=document['extraction_id'],page_number=1,text_sha256=page['text_sha256'])
        analysis=dict(schema_version=2,context_id=context['analysis_context_id'],producer=dict(kind='model',name=self.NAME),identity='single',missing_fields=[],
            facts=[dict(field='model',value='AUTHORED-G3-PDF',status='explicit',evidence=[evidence])])
        decoded=decode_analysis_response(canonical(analysis).encode('utf-8'),context,producer_name=self.NAME)
        self.assertEqual(decoded,analysis)
        for field,value in (('quote','not present in original PDF'),('page_number',2),('extraction_id','0'*64),('text_sha256','0'*64)):
            bad=copy.deepcopy(analysis);bad['facts'][0]['evidence'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):decode_analysis_response(canonical(bad).encode(),context,producer_name=self.NAME)
        bad=copy.deepcopy(analysis);bad['context_id']='0'*64
        with self.assertRaises(ValueError):decode_analysis_response(canonical(bad).encode(),context,producer_name=self.NAME)
        self.assertEqual(before,self.business());self.record.update(context=context,prompt=prompt,analysis=decoded,new_model_calls=0)

    def test_pdf_preparation_rechecks_private_job_after_retention_and_preserves_the_race(self):
        from unittest.mock import patch
        original=self.jobs._prepare;retained=[]
        def race(store,revision):
            value=original(store,revision);retained.append(value)
            with store.connection() as con:con.execute("UPDATE intake_jobs SET token='AUTHORED-RACE' WHERE job_id=?",(self.selection['job_id'],))
            return value
        with patch.object(self.jobs,'_prepare',side_effect=race):self.error('state_changed')
        self.assertEqual(self.job()['token'],'AUTHORED-RACE');self.assertEqual(self.job()['attempt'],0)
        self.assertEqual(len(retained),1);self.assertTrue(self.store.blob_path(retained[0]['context_id']).is_file())
        self.record.update(retained=retained,fault='explicit test job-token race, not G3 business write')

    def test_pdf_extraction_tamper_rejects_and_keeps_original_failed_artifact(self):
        from unittest.mock import patch
        before=self.business();original=self.jobs._prepare;changed=[]
        def tamper(store,revision):
            value=original(store,revision);path=store.blob_path(value['documents'][0]['extraction_id'])
            path.write_bytes(b'preserved authored PDF extraction failure');changed.append(path);return value
        with patch.object(self.jobs,'_prepare',side_effect=tamper):self.error('preparation_failed')
        self.assertEqual(before,self.business());self.assertEqual(len(changed),1)
        self.assertEqual(changed[0].read_bytes(),b'preserved authored PDF extraction failure')
        self.record.update(fault='explicit test extraction corruption preserved')

    def test_pdf_public_context_limit_preserves_retained_prefix_and_business_state(self):
        from unittest.mock import patch
        from labflow.store import canonical
        before=self.business();old=set((self.store.root/'blobs').iterdir())
        self.assertLess(len(canonical(self.selection).encode('utf-8')),1024)
        with patch.object(self.jobs,'MAX_CONTEXT_BYTES',1024):self.error('limit_exceeded')
        self.assertEqual(before,self.business());self.assertGreater(len(set((self.store.root/'blobs').iterdir())-old),0)
        self.record.update(fault='explicit public-context limit1024 above selection size; original production cap unchanged')

    def test_first_observed_PDF_verify_controls_keep_identity_and_retained_prefix(self):
        from unittest.mock import patch
        before=self.business();source=self.source_pin()
        for error in (KeyboardInterrupt('first PDF verify'),MemoryError('first PDF verify')):
            with self.subTest(kind=type(error).__name__),patch.object(self.jobs,'_verify',side_effect=error):
                with self.assertRaises(type(error)) as caught:self.ready()
                self.assertIs(caught.exception,error);self.assertEqual(error.__dict__,{})
        self.assertEqual(before,self.business());self.assertEqual(source,self.source_pin())
        self.assertGreater(len(list((self.store.root/'blobs').iterdir())),1)
        self.record.update(fault='two first verify controls; no retry/cleanup of retained prefix')

    def test_inconsistent_schema2_context_binding_and_unknown_schema_do_not_return_success(self):
        from unittest.mock import patch
        before=self.business();original=self.jobs._public_context
        for mode,want in (('context_id','preparation_failed'),('schema3','unsupported_schema')):
            def changed(job,revision,prepared):
                value=original(job,revision,prepared)
                if mode=='context_id':value['analysis_contract']['context_id']='0'*64
                else:value['analysis_contract']['schema_version']=3
                return value
            with self.subTest(mode=mode),patch.object(self.jobs,'_public_context',side_effect=changed):self.error(want)
        self.assertEqual(before,self.business());self.record.update(fault='explicit wrong schema/context producer seam; original metadata retained')


if __name__=='__main__':
    unittest.main()
