"""UI contracts use the real intake service and a separate synthetic store."""
import hashlib
from pathlib import Path
import tempfile
import unittest
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


if __name__ == '__main__':
    unittest.main()
