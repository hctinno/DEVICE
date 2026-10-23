"""Atomic scanner provenance gate and the supervisor's exact TOCTOU boundary."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from labflow import active_intake, intake_supervisor
from labflow.active_intake import register_source, scan_source
from labflow.intake_supervisor import run_intake_supervisor
from labflow.intake_worker import SyntheticTextProvider, run_worker
from labflow.store import Store


TABLES = ('intake_sources', 'blobs', 'intakes', 'intake_observations', 'intake_revisions',
          'intake_jobs', 'intake_questions', 'intake_answers', 'intake_notifications', 'events')
CANARY = 'PRIVATE_SCAN_SCOPE_CANARY'


class AtomicScanScopeTests(unittest.TestCase):
    def setUp(self):
        directory = Path(__file__).resolve().parents[1]/'.local/scan-scope-tests'
        directory.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = Store(self.root/'state')
        self.syn, self.real = self.root/'synthetic', self.root/'real-fixture'
        for name, inbox, synthetic in [('SYN', self.syn, True), ('REAL', self.real, False)]:
            inbox.mkdir()
            self.put(inbox, name)
            register_source(self.store, name, inbox, synthetic=synthetic, settle_seconds=1)

    def put(self, inbox, name):
        folder = inbox/name
        folder.mkdir()
        (folder/'request.txt').write_text('product_type: remote_control\nmarket: EU\n'
            'purpose: scope fixture\nmodel: '+name+'\n', encoding='utf-8')

    def snapshot(self):
        with self.store.connection() as con:
            return {table: [dict(row) for row in con.execute('SELECT * FROM '+table+' ORDER BY rowid')]
                    for table in TABLES}

    def originals(self):
        return {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for inbox in (self.syn, self.real) for path in inbox.rglob('*') if path.is_file()}

    def test_scope_flip_after_supervisor_lookup_never_reads_or_accepts_real_revision(self):
        scan_source(self.store, 'SYN', now=100)  # Stable observation; no revision yet.
        actual_scan = scan_source
        snapshots = []
        originals = self.originals()
        def racing_scan(store, source_id, **kwargs):
            with store.connection() as con:
                con.execute('UPDATE intake_sources SET synthetic=0 WHERE source_id=?', (source_id,))
            snapshots.append(self.snapshot())
            return actual_scan(store, source_id, now=101, **kwargs)
        with patch('labflow.intake_supervisor.scan_source', autospec=True, side_effect=racing_scan) as scan, \
             patch('labflow.active_intake._plain_path', wraps=active_intake._plain_path) as filesystem, \
             patch('labflow.intake_supervisor.run_worker', wraps=run_worker) as worker:
            result = run_intake_supervisor(self.store, ['SYN'], SyntheticTextProvider(),
                                          worker_id='scope-watch', max_cycles=1)
        diagnostic = 'accepted='+str(result['accepted_revisions'])
        with self.store.connection() as con:
            rows = con.execute('SELECT synthetic FROM intake_revisions').fetchall()
        diagnostic += ', revision.synthetic='+str([row['synthetic'] for row in rows])
        self.assertEqual(result['stop_reason'], 'source_error', diagnostic)
        self.assertEqual((result['accepted_revisions'], result['analyzed_jobs']), (0, 0))
        self.assertIs(scan.call_args.kwargs['synthetic_only'], True)
        filesystem.assert_not_called()
        worker.assert_not_called()
        self.assertEqual(self.snapshot(), snapshots[0])
        self.assertEqual(self.originals(), originals)

    def test_atomic_real_rejection_preserves_rows_originals_and_existing_notifications(self):
        scan_source(self.store, 'REAL', now=100)
        scan_source(self.store, 'REAL', now=101)
        scan_source(self.store, 'SYN', now=100)
        scan_source(self.store, 'SYN', now=101)
        run_worker(self.store, SyntheticTextProvider(), worker_id='fixture-analysis', max_jobs=1)
        self.put(self.real, 'NEW-REAL')
        before, originals = self.snapshot(), self.originals()
        self.assertTrue(before['intake_notifications'])
        with patch('labflow.active_intake._plain_path') as plain, \
             patch('labflow.active_intake._inventory') as inventory, \
             patch.object(Path, 'read_bytes') as read:
            with self.assertRaisesRegex(ValueError, '^synthetic_source_required$'):
                scan_source(self.store, 'REAL', now=102, synthetic_only=True)
            plain.assert_not_called()
            inventory.assert_not_called()
            read.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.originals(), originals)

    def test_nonbool_scope_option_is_rejected_before_db_or_filesystem(self):
        before = self.snapshot()
        with patch.object(self.store, 'connection') as connection, \
             patch('labflow.active_intake._plain_path') as filesystem:
            for value in [None, 0, 1, 'true', [], float('nan')]:
                with self.subTest(kind=type(value).__name__), self.assertRaisesRegex(ValueError, 'synthetic_only'):
                    scan_source(self.store, 'SYN', synthetic_only=value)
            connection.assert_not_called()
            filesystem.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_original_default_and_explicit_false_still_accept_real_sources(self):
        scan_source(self.store, 'REAL', now=100)
        first = scan_source(self.store, 'REAL', now=101)
        self.assertEqual(len(first['accepted']), 1)
        self.put(self.real, 'SECOND-REAL')
        scan_source(self.store, 'REAL', now=102, synthetic_only=False)
        second = scan_source(self.store, 'REAL', now=103, synthetic_only=False)
        self.assertEqual(len(second['accepted']), 1)
        with self.store.connection() as con:
            self.assertEqual([row['synthetic'] for row in con.execute('SELECT synthetic FROM intake_revisions')], [0, 0])

    def test_true_scope_accepts_synthetic_sources_and_preserves_original_content(self):
        originals = self.originals()
        scan_source(self.store, 'SYN', now=100, synthetic_only=True)
        accepted = scan_source(self.store, 'SYN', now=101, synthetic_only=True)
        self.assertEqual(len(accepted['accepted']), 1)
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT synthetic FROM intake_revisions').fetchone()[0], 1)
        self.assertEqual(self.originals(), originals)

    def test_sqlite_write_lock_holds_from_scope_gate_through_filesystem_access(self):
        scan_source(self.store, 'SYN', now=100)
        actual_plain = active_intake._plain_path
        locked = []
        def observe_lock(path):
            con = sqlite3.connect(self.store.db, timeout=0)
            try:
                with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                    con.execute('UPDATE intake_sources SET synthetic=0 WHERE source_id=?', ('SYN',))
                locked.append(True)
            finally:
                con.close()
            return actual_plain(path)
        with patch('labflow.active_intake._plain_path', side_effect=observe_lock):
            result = scan_source(self.store, 'SYN', now=101, synthetic_only=True)
        self.assertTrue(locked)
        self.assertEqual(len(result['accepted']), 1)
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT synthetic FROM intake_sources WHERE source_id=?', ('SYN',)).fetchone()[0], 1)
            self.assertEqual(con.execute('SELECT synthetic FROM intake_revisions').fetchone()[0], 1)

    def test_supervisor_rejects_legacy_or_generic_scanner_before_any_scan_or_worker(self):
        calls = []
        def legacy(store, source_id, *, now=None):
            calls.append(True)
            raise RuntimeError(CANARY)
        def generic(store, source_id, **kwargs):
            calls.append(True)
            raise RuntimeError(CANARY)
        for scanner in (legacy, generic):
            with patch.object(intake_supervisor, 'scan_source', scanner), \
                 patch.object(intake_supervisor, 'run_worker') as worker:
                with self.assertRaisesRegex(ValueError, '^supervisor_scanner_invalid$'):
                    run_intake_supervisor(self.store, ['SYN'], SyntheticTextProvider(), worker_id='scope-watch')
                worker.assert_not_called()
        self.assertFalse(calls)


if __name__ == '__main__':
    unittest.main()
