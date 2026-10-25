"""UI contracts use the real intake service and a separate synthetic store."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job, complete_job, respond
from labflow.store import Store
from labflow.ui_read_model import IntakeReadModel, ReadModelError


class IntakeFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.inbox = self.root / 'input'
        self.inbox.mkdir()
        self.store = Store(self.root / 'state')
        register_source(self.store, 'UI', self.inbox, synthetic=True, settle_seconds=1)

    def accept(self, name='order'):
        folder = self.inbox / name
        folder.mkdir(exist_ok=True)
        (folder / 'request.txt').write_text(
            'Remote control <script>window.pwned=true</script>\nMarket: EU\nPurpose: development\n', encoding='utf-8')
        scan_source(self.store, 'UI', now=100)
        return scan_source(self.store, 'UI', now=101)['accepted'][-1]['intake_id']

    def finish(self):
        job = claim_job(self.store, 'ui-fixture', now=102)
        doc = job['documents'][0]
        facts = []
        for field, value, line in [('product_type', 'remote_control', 1), ('market', 'EU', 2), ('purpose', 'development', 3)]:
            facts.append({'field': field, 'value': value, 'status': 'explicit', 'evidence': [{
                'path': doc['path'], 'sha256': doc['sha256'], 'line_start': line, 'line_end': line,
                'quote': doc['text'].splitlines()[line-1], 'role': 'request'}]})
        complete_job(self.store, job['job_id'], job['token'], {
            'schema_version': 1, 'producer': {'kind': 'fixture', 'name': 'ui-contract'},
            'identity': 'single', 'facts': facts, 'missing_fields': ['firmware']}, now=103)
        return job['intake_id']


class ReadModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixture = IntakeFixture(self.tmp.name)
        self.model = IntakeReadModel(self.fixture.store.root)

    def test_existing_empty_store_is_a_successful_empty_result(self):
        result = self.model.snapshot()
        self.assertEqual(result['intakes'], [])
        self.assertEqual(result['notifications'], [])
        self.assertEqual(result['schema_version'], 1)

    def test_missing_store_does_not_create_state_or_become_empty_success(self):
        missing = Path(self.tmp.name) / 'does-not-exist'
        with self.assertRaises(ReadModelError) as error:
            IntakeReadModel(missing).snapshot()
        self.assertEqual(error.exception.code, 'store_missing')
        self.assertFalse(missing.exists())

    def test_list_and_detail_retain_service_evidence_jobs_and_local_notices(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        result = self.model.snapshot(intake_id)
        self.assertEqual(result['intake']['intake_id'], intake_id)
        self.assertTrue(result['intake']['synthetic'])
        self.assertEqual(result['intake']['measurement_support'], 'unverified')
        self.assertEqual(result['intake']['jobs'][0]['state'], 'completed')
        self.assertNotIn('token', result['intake']['jobs'][0])
        self.assertEqual(result['notifications'][0]['revision'], 1)
        self.assertEqual(result['intake']['analysis']['questions'][0]['key'], 'missing_firmware')
        self.assertIn('<script>', result['intake']['analysis']['submitted']['facts'][0]['evidence'][0]['quote'])
        self.assertEqual(self.model.snapshot()['intakes'][0], result['intake'])

    def test_reading_never_initializes_migrates_or_changes_the_database(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        respond(self.fixture.store, 'DEFER-UI', 'defer', intake_id=intake_id)
        before = hashlib.sha256(self.fixture.store.db.read_bytes()).hexdigest()
        result = self.model.snapshot(intake_id)
        self.assertTrue(result['intake']['deferred'])
        self.assertEqual(result['intake']['analysis']['next_action'], 'deferred')
        self.assertEqual(hashlib.sha256(self.fixture.store.db.read_bytes()).hexdigest(), before)

    def test_unknown_intake_and_invalid_schema_are_explicit_errors(self):
        with self.assertRaises(ReadModelError) as error:
            self.model.snapshot('I-absent')
        self.assertEqual(error.exception.code, 'intake_not_found')
        self.fixture.store.db.write_bytes(b'not a sqlite database')
        with self.assertRaises(ReadModelError) as error:
            self.model.snapshot()
        self.assertEqual(error.exception.code, 'store_unavailable')

    def test_read_connection_blocks_an_accidental_mutating_query(self):
        self.fixture.accept()
        before = self.fixture.store.db.read_bytes()

        def unexpected_write(store, intake_id):
            with store.connection() as con:
                con.execute('UPDATE intakes SET delegated=1')

        with patch('labflow.ui_read_model.intake_status', side_effect=unexpected_write):
            with self.assertRaises(ReadModelError) as error:
                self.model.snapshot()
        self.assertEqual(error.exception.code, 'store_unavailable')
        self.assertEqual(self.fixture.store.db.read_bytes(), before)

    def test_new_revision_does_not_relabel_old_analysis_or_notices(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        (self.fixture.inbox / 'order' / 'supplement.txt').write_text('Synthetic supplement', encoding='utf-8')
        scan_source(self.fixture.store, 'UI', now=120)
        scan_source(self.fixture.store, 'UI', now=121)
        result = self.model.snapshot(intake_id)
        self.assertEqual(result['intake']['revision'], 2)
        self.assertIsNone(result['intake']['analysis'])
        self.assertEqual(result['intake']['jobs'][0]['state'], 'completed')
        self.assertEqual(result['intake']['jobs'][1]['state'], 'queued')
        self.assertEqual(result['notifications'][0]['revision'], 1)


def conducted_context_fixture(root, *, kind='pdf', completed=True, synthetic=True):
    """Own fresh synthetic bytes through genuine retention/completion; no model."""
    from labflow.intake_fixture_check import _write_request
    from labflow.intake_worker import SyntheticTextProvider
    root=Path(root);inbox=root/'inbox';inbox.mkdir(parents=True)
    _write_request(inbox/'request',kind)
    store=Store(root/'state');register_source(store,'PLAN-PREVIEW-SYN',inbox,synthetic=synthetic,settle_seconds=.001)
    scan_source(store,'PLAN-PREVIEW-SYN',now=100)
    intake_id=scan_source(store,'PLAN-PREVIEW-SYN',now=100.01)['accepted'][0]['intake_id']
    job=claim_job(store,'plan-preview-fixture',now=101)
    context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
    analysis=SyntheticTextProvider().analyze({**context,'synthetic':True})
    if not synthetic:analysis['producer']={'kind':'manual','name':'synthetic-test-data-only'}
    if completed:complete_job(store,job['job_id'],job['token'],analysis,now=102)
    return {'store':store,'intake_id':intake_id,'context':context,'analysis':analysis,'inbox':inbox}


class ConductedPlanContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='conducted-context-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def reader(self, fixture):
        model=IntakeReadModel(fixture['store'].root)
        self.assertTrue(callable(getattr(model,'current_conducted_plan_context',None)),'missing genuine RO conducted context getter')
        return model.current_conducted_plan_context

    def test_genuine_current_V2_PDF_returns_native_context_and_submission_without_replaying_a_prompt(self):
        from labflow.intake_model_boundary import build_analysis_prompt
        fixture=conducted_context_fixture(self.root/'valid');native=self.reader(fixture)(fixture['intake_id'])
        self.assertEqual(set(native),{'context','analysis'})
        self.assertEqual(native['analysis'],fixture['analysis']);self.assertEqual(native['context']['documents'],fixture['context']['documents'])
        self.assertEqual(native['context']['analysis_context_id'],fixture['context']['analysis_context_id'])
        self.assertNotEqual(native['context']['instructions'],fixture['context']['instructions'])
        prompt=build_analysis_prompt(native['context'],producer_name='current-readonly-plan')
        self.assertEqual(json.loads(prompt['messages'][1]['content']),native['context'])
        native['context']['documents'].clear()
        self.assertTrue(self.reader(fixture)(fixture['intake_id'])['context']['documents'])

    def test_RO_getter_never_initializes_claims_prepares_retains_or_runs_and_leaves_database_unchanged(self):
        fixture=conducted_context_fixture(self.root/'readonly');reader=self.reader(fixture);before=fixture['store'].db.read_bytes()
        with ExitStack() as stack:
            for target in ('labflow.store.Store.__init__','labflow.intake_jobs.claim_job','labflow.intake_documents.prepare_analysis_documents','labflow.intake_documents._retain','labflow.intake_worker.run_worker'):
                stack.enter_context(patch(target,side_effect=AssertionError('read-only preview entered '+target)))
            native=reader(fixture['intake_id'])
        self.assertEqual(native['context']['revision'],1);self.assertEqual(fixture['store'].db.read_bytes(),before)

    def test_TXT_V1_nonsynthetic_and_incomplete_are_explicit_unavailable(self):
        for index,options in enumerate(({'kind':'text'},{'synthetic':False},{'completed':False})):
            fixture=conducted_context_fixture(self.root/str(index),**options);reader=self.reader(fixture)
            with self.subTest(options=options),self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
            self.assertIn(error.exception.code,('intake_conducted_preview_v2_pdf_required','intake_conducted_preview_synthetic_required','intake_conducted_preview_analysis_unavailable'))

    def test_new_revision_and_changed_source_never_reuse_a_completed_native_context(self):
        fixture=conducted_context_fixture(self.root/'revision');reader=self.reader(fixture)
        self.assertEqual(reader(fixture['intake_id'])['context']['revision'],1)
        (fixture['inbox']/'request'/'supplement.txt').write_text('synthetic revision2',encoding='utf-8')
        scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120);scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120.01)
        with self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
        self.assertEqual(error.exception.code,'intake_conducted_preview_analysis_unavailable')
        fixture=conducted_context_fixture(self.root/'source');reader=self.reader(fixture)
        blob=fixture['store'].blob_path(fixture['context']['documents'][0]['sha256']);blob.write_bytes(blob.read_bytes()+b'changed')
        with self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
        self.assertEqual(error.exception.code,'intake_conducted_preview_source_invalid')

    def test_control_exception_from_current_capture_is_not_changed_to_unavailable(self):
        fixture=conducted_context_fixture(self.root/'control');reader=self.reader(fixture)
        with patch('labflow.intake_reference_snapshot.capture_intake_reference_snapshot_in_transaction',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):
            reader(fixture['intake_id'])

    def test_unconfirmed_blob_provenance_cannot_become_a_synthetic_planning_context(self):
        fixture=conducted_context_fixture(self.root/'provenance');reader=self.reader(fixture)
        with fixture['store'].connection() as con:
            con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?',(fixture['context']['documents'][0]['sha256'],))
        with self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
        self.assertEqual(error.exception.code,'intake_conducted_preview_synthetic_required')


if __name__ == '__main__':
    unittest.main()
