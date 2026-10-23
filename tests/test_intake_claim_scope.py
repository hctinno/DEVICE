from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest

from labflow.active_intake import intake_status, register_source, scan_source
from labflow.intake_jobs import claim_job
from labflow.store import Store


class IntakeClaimScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = Store(self.root / 'state')
        self.real_id = self.add_source('REAL', synthetic=False, now=10)
        self.synthetic_id = self.add_source('SYNTHETIC', synthetic=True, now=20)

    def add_source(self, name, *, synthetic, now):
        inbox = self.root / name
        bundle = inbox / 'order'
        bundle.mkdir(parents=True)
        (bundle / 'request.txt').write_text(f'Test fixture for {name}.', encoding='utf-8')
        register_source(self.store, name, inbox, synthetic=synthetic, settle_seconds=1)
        scan_source(self.store, name, now=now)
        scan_source(self.store, name, now=now + 1)
        return next(item['intake_id'] for item in intake_status(self.store)
                    if item['source_id'] == name)

    def real_state(self):
        with self.store.connection() as con:
            return {
                'intakes': [dict(row) for row in con.execute(
                    "SELECT * FROM intakes WHERE source_id LIKE 'REAL%' ORDER BY intake_id")],
                'jobs': [dict(row) for row in con.execute(
                    "SELECT j.* FROM intake_jobs j JOIN intakes i USING(intake_id) "
                    "WHERE i.source_id LIKE 'REAL%' ORDER BY job_id")],
                'events': [dict(row) for row in con.execute(
                    "SELECT e.* FROM events e JOIN intakes i ON e.subject_id=i.intake_id "
                    "WHERE i.source_id LIKE 'REAL%' ORDER BY e.rowid")],
            }

    def test_synthetic_claim_skips_older_real_job_without_side_effects(self):
        before = self.real_state()
        job = claim_job(self.store, 'fixture-worker', now=30, synthetic_only=True)
        self.assertEqual(job['intake_id'], self.synthetic_id)
        self.assertTrue(job['synthetic'])
        self.assertEqual(job['attempt'], 1)
        self.assertIsNone(claim_job(self.store, 'other-worker', now=31, synthetic_only=True))
        self.assertEqual(self.real_state(), before)

    def test_default_claim_preserves_unfiltered_behavior(self):
        job = claim_job(self.store, 'normal-worker', now=30)
        self.assertEqual(job['intake_id'], self.real_id)
        self.assertFalse(job['synthetic'])

    def test_scoped_maintenance_leaves_expired_and_failed_real_jobs_unchanged(self):
        failed_id = self.add_source('REAL_FAILED', synthetic=False, now=12)
        with self.store.connection() as con:
            con.execute("UPDATE intake_jobs SET state='running',attempt=3,lease_until=25 "
                        "WHERE intake_id=?", (self.real_id,))
            con.execute("UPDATE intake_jobs SET state='failed',attempt=3,error_code='model_error' "
                        "WHERE intake_id=?", (failed_id,))
        before = self.real_state()
        claim_job(self.store, 'fixture-worker', now=30, synthetic_only=True)
        self.assertEqual(self.real_state(), before)
        claim_job(self.store, 'normal-worker', now=31)
        self.assertEqual(intake_status(self.store, self.real_id)['status'], 'analysis_failed')
        self.assertEqual(intake_status(self.store, failed_id)['status'], 'analysis_failed')

    def test_synthetic_expired_attempts_are_still_cleaned(self):
        with self.store.connection() as con:
            con.execute("UPDATE intake_jobs SET state='running',attempt=3,lease_until=25 "
                        "WHERE intake_id=?", (self.synthetic_id,))
        before = self.real_state()
        self.assertIsNone(claim_job(self.store, 'fixture-worker', now=30, synthetic_only=True))
        item = intake_status(self.store, self.synthetic_id)
        self.assertEqual(item['status'], 'analysis_failed')
        self.assertEqual(item['jobs'][0]['error_code'], 'attempt_limit')
        self.assertEqual(self.real_state(), before)

    def test_invalid_scope_does_not_change_database(self):
        with self.store.connection() as con:
            before = list(con.iterdump())
        for invalid in (None, 0, 1, 'true', []):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                claim_job(self.store, 'fixture-worker', now=30, synthetic_only=invalid)
        with self.store.connection() as con:
            self.assertEqual(list(con.iterdump()), before)

    def test_concurrent_synthetic_workers_claim_once_and_never_fall_back_to_real(self):
        before = self.real_state()
        start = threading.Barrier(2)

        def run(worker):
            start.wait(timeout=5)
            return claim_job(self.store, worker, now=30, synthetic_only=True)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, ['fixture-a', 'fixture-b']))
        claimed = [result for result in results if result is not None]
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0]['intake_id'], self.synthetic_id)
        self.assertEqual(claimed[0]['attempt'], 1)
        self.assertEqual(self.real_state(), before)

    def test_out_of_scope_blob_is_not_read(self):
        real = intake_status(self.store, self.real_id)
        self.store.blob_path(real['files'][0]['sha256']).write_bytes(b'corrupted fixture')
        job = claim_job(self.store, 'fixture-worker', now=30, synthetic_only=True)
        self.assertEqual(job['intake_id'], self.synthetic_id)


if __name__ == '__main__':
    unittest.main()
