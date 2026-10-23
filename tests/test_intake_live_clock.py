"""Lease validity at real SQLite lock and validation boundaries."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from labflow import intake_jobs
from labflow.active_intake import register_source, scan_source, timestamp
from labflow.store import Store


class TracedStore:
    def __init__(self, store, begin):
        self.store, self.begin = store, begin

    def __getattr__(self, name):
        return getattr(self.store, name)

    @contextmanager
    def connection(self):
        with self.store.connection() as con:
            con.set_trace_callback(lambda sql: self.begin.set()
                                   if sql.strip().upper() == 'BEGIN IMMEDIATE' else None)
            yield con


class IntakeLiveClockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.store = Store(root / 'state')
        inbox = root / 'input'
        bundle = inbox / 'case'
        bundle.mkdir(parents=True)
        (bundle / 'request.txt').write_text('product_type: device\nmarket: EU\npurpose: development\n', encoding='utf-8')
        register_source(self.store, 'CLOCK', inbox, synthetic=True, settle_seconds=1)
        scan_source(self.store, 'CLOCK', now=1)
        scan_source(self.store, 'CLOCK', now=2)
        self.clock = 10
        clock = patch('labflow.intake_jobs.timestamp', side_effect=lambda value=None:
                      self.clock if value is None else timestamp(value))
        clock.start()
        self.addCleanup(clock.stop)

    def claim(self):
        return intake_jobs.claim_job(self.store, 'clock-worker', lease_seconds=5, synthetic_only=True)

    def analysis(self, job):
        document = job['documents'][0]
        lines = document['text'].splitlines()
        facts = []
        for number, line in enumerate(lines, 1):
            field, value = line.split(': ', 1)
            facts.append({'field': field, 'value': value, 'status': 'explicit', 'evidence': [{
                'path': document['path'], 'sha256': document['sha256'], 'role': 'request',
                'line_start': number, 'line_end': number, 'quote': line}]})
        return {'schema_version': 1, 'producer': {'kind': 'fixture', 'name': 'clock-test'},
                'identity': 'single', 'facts': facts, 'missing_fields': []}

    def snapshot(self):
        with self.store.connection() as con:
            return list(con.iterdump())

    def blocked(self, operation, *, advance_to=16):
        begin = threading.Event()
        store = TracedStore(self.store, begin)
        blocker = sqlite3.connect(self.store.db)
        blocker.execute('BEGIN IMMEDIATE')
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(operation, store)
                try:
                    self.assertTrue(begin.wait(timeout=5), 'operation never attempted its write transaction')
                    self.clock = advance_to
                finally:
                    blocker.rollback()
                return future.result(timeout=5)
        finally:
            blocker.close()

    def test_live_claim_starts_lease_after_acquiring_write_lock(self):
        job = self.blocked(lambda store: intake_jobs.claim_job(
            store, 'clock-worker', lease_seconds=5, synthetic_only=True))
        self.assertEqual(job['lease_until'], 21)
        self.assertEqual(job['attempt'], 1)

    def test_live_claim_does_not_spend_lease_while_reading_source_documents(self):
        original = intake_jobs.document_context
        def read_documents(*args, **kwargs):
            result = original(*args, **kwargs)
            self.clock = 16
            return result
        with patch('labflow.intake_jobs.document_context', side_effect=read_documents):
            job = self.claim()
        self.assertEqual(job['lease_until'], 21)

    def test_live_completion_after_lock_wait_rejects_expired_lease_without_writes(self):
        job = self.claim()
        analysis = self.analysis(job)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'expired analysis lease'):
            self.blocked(lambda store: intake_jobs.complete_job(store, job['job_id'], job['token'], analysis))
        self.assertEqual(self.snapshot(), before)

    def test_live_failure_after_lock_wait_does_not_requeue_an_expired_lease(self):
        job = self.claim()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'expired analysis lease'):
            self.blocked(lambda store: intake_jobs.fail_job(store, job['job_id'], job['token']))
        self.assertEqual(self.snapshot(), before)

    def test_live_completion_rechecks_lease_after_validation(self):
        job = self.claim()
        analysis = self.analysis(job)
        before = self.snapshot()
        original = intake_jobs.validate_analysis
        def validate(*args, **kwargs):
            result = original(*args, **kwargs)
            self.clock = 16
            return result
        with patch('labflow.intake_jobs.validate_analysis', side_effect=validate):
            with self.assertRaisesRegex(ValueError, 'expired analysis lease'):
                intake_jobs.complete_job(self.store, job['job_id'], job['token'], analysis)
        self.assertEqual(self.snapshot(), before)

    def test_expiry_during_projection_rolls_back_questions_notices_and_analysis(self):
        job = self.claim()
        analysis = self.analysis(job)
        analysis['facts'] = [fact for fact in analysis['facts'] if fact['field'] != 'market']
        before = self.snapshot()
        original = intake_jobs._refresh
        def refresh(*args, **kwargs):
            result = original(*args, **kwargs)
            self.assertGreater(args[1].execute('SELECT COUNT(*) FROM intake_questions').fetchone()[0], 0)
            self.clock = 16
            return result
        with patch('labflow.intake_jobs._refresh', side_effect=refresh):
            with self.assertRaisesRegex(ValueError, 'expired analysis lease'):
                intake_jobs.complete_job(self.store, job['job_id'], job['token'], analysis)
        self.assertEqual(self.snapshot(), before)

    def test_explicit_time_remains_a_deterministic_override_and_completion_is_idempotent(self):
        self.clock = 1000
        job = intake_jobs.claim_job(self.store, 'clock-worker', now=10, lease_seconds=5, synthetic_only=True)
        analysis = self.analysis(job)
        result = intake_jobs.complete_job(self.store, job['job_id'], job['token'], analysis, now=11)
        before = self.snapshot()
        self.assertEqual(intake_jobs.complete_job(self.store, job['job_id'], job['token'], analysis, now=12), result)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
