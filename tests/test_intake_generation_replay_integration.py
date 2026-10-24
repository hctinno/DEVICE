"""Lead-owned complete_job integration for retained completion replay."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from labflow import intake_documents, intake_generation_ledger
from labflow.intake_jobs import complete_job
import test_intake_generation_ledger as ledger_fixtures


class RetainedReplayCommonTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ledger_fixtures.GenerationLedgerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.store = self.fixture.store
        self.job = copy.deepcopy(self.fixture.job)
        self.analysis = copy.deepcopy(self.fixture.analysis)
        self.expected = json.loads(self.fixture._saved_result)['summary']

    def state(self):
        with self.store.connection() as con:
            dump = '\n'.join(con.iterdump())
        return {'dump': hashlib.sha256(dump.encode()).hexdigest(),
                'db': hashlib.sha256(self.store.db.read_bytes()).hexdigest(),
                'files': self.fixture.original_hashes()}

    def replay(self, analysis=None, token=None):
        return complete_job(self.store, self.job['job_id'], self.job['token'] if token is None else token,
                            self.analysis if analysis is None else analysis, now=999)

    def test_imported_completion_replays_under_new_profile_without_preparation_or_mutation(self):
        self.fixture.receipt()
        before = self.state()
        with patch.object(intake_documents.importlib.metadata, 'version', return_value='new-profile-root-probe'), \
             patch('labflow.intake_jobs._prepare', side_effect=AssertionError('replay_must_not_prepare')):
            actual = self.replay()
        self.assertEqual(actual, self.expected)
        self.assertEqual(self.state(), before)
        actual['submitted']['identity'] = 'unknown'
        self.assertEqual(self.replay(), self.expected)

    def test_old_revision_replays_original_summary_and_preserves_new_current_state(self):
        self.fixture.receipt()
        self.fixture.job, self.fixture.analysis = self.fixture.finish(revision=2)
        self.fixture.receipt()
        before = self.state()
        with patch.object(intake_documents.importlib.metadata, 'version', return_value='new-profile-root-probe'):
            actual = self.replay()
        self.assertEqual(actual, self.expected)
        self.assertEqual(actual['revision'], 1)
        self.assertEqual(self.state(), before)

    def test_absent_origin_preserves_existing_completed_retry(self):
        before = self.state()
        self.assertEqual(self.replay(), self.expected)
        self.assertEqual(self.state(), before)

    def test_helper_rejection_does_not_fall_back_to_legacy_success(self):
        self.fixture.receipt()
        before = self.state()
        with patch.object(intake_generation_ledger, 'replay_imported_completion', create=True,
                          side_effect=ValueError('generation_replay_rejected')):
            with self.assertRaisesRegex(ValueError, '^generation_replay_rejected$'):
                self.replay()
        self.assertEqual(self.state(), before)


if __name__ == '__main__':
    unittest.main()
