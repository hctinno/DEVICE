"""043 formal API on owned synthetic Stores; no collected/customer database."""
from contextlib import contextmanager
import gc
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
import weakref

from labflow import store as module
from labflow.store import Store
from labflow import control_packet_prepare as native
from labflow import intake_generation_ledger as gen
from labflow import intake_reference_ledger as refs

DB_ENTRIES = ('lab.sqlite3-wal', 'lab.sqlite3-shm', 'lab.sqlite3-journal')


class ConnectionFault:
    """Explicit storage failure double retaining a real SQLite connection."""
    def __init__(self, connection, *, close_failure=False, query_failure=None):
        object.__setattr__(self, 'connection', connection)
        object.__setattr__(self, 'close_failure', close_failure)
        object.__setattr__(self, 'query_failure', query_failure)

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __setattr__(self, name, value):
        setattr(self.connection, name, value)

    def execute(self, statement, *args, **kwargs):
        if self.query_failure is not None and 'sqlite_schema' in statement:
            raise self.query_failure
        return self.connection.execute(statement, *args, **kwargs)

    def close(self):
        self.connection.close()
        if self.close_failure:
            raise OSError('PRIVATE close failure')


class StoreOpenExistingTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(Store, 'open_existing', None)), '043 public Store.open_existing API is absent')
        self.assertEqual(os.name, 'nt', 'Windows-native product API contract')
        parent = Path(__file__).resolve().parents[1] / '.local' / 's043'
        parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=parent); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.legacy = Store(self.base / 'workspace')
        self.root, self.db = self.legacy.root, self.legacy.db

    def open(self, root=None):
        value = Store.open_existing(str(self.root) if root is None else root)
        self.addCleanup(value.close)
        return value

    def snapshot(self):
        return {p.relative_to(self.base).as_posix():
                (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_dev, p.stat().st_ino,
                 p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_mode)
                for p in self.base.rglob('*') if p.is_file()}

    def error(self, suffix, function=None, *, root=None):
        with self.assertRaises(ValueError) as caught:
            (function if function is not None else lambda: Store.open_existing(str(self.root) if root is None else root))()
        error = caught.exception; code = 'store_open_' + suffix
        self.assertIsInstance(error, module.StoreOpenError)
        self.assertEqual((error.code, str(error), error.args), (code, code, (code,)))
        self.assertIsNone(error.__context__); self.assertIsNone(error.__cause__)
        self.assertNotIn(str(self.base), repr(error)); self.assertNotIn('PRIVATE', repr(error))

    def extend(self, store, *, generation=False, reference=False):
        with store.connection() as con:
            if generation:
                for _, sql in gen._SCHEMA.values(): con.execute(sql)
            if reference:
                for _, _, sql in refs._DDL.values(): con.execute(sql)

    def test_exact_official_factory_skips_creating_constructor_mkdir_and_provenance_updates(self):
        with self.legacy.connection() as con:
            con.execute('INSERT INTO blobs(sha256,bytes,kind,synthetic) VALUES(?,?,?,?)', ('a' * 64, 1, 'synthetic_evidence', 0))
        before = self.snapshot(); original = sqlite3.connect; trace, connections = [], []
        def connect(path, **kwargs):
            self.assertTrue(kwargs.get('uri')); self.assertTrue(str(path).endswith('?mode=ro'))
            con = original(path, **kwargs); con.set_trace_callback(trace.append); connections.append(con); return con
        with mock.patch.object(Store, '__init__', side_effect=AssertionError('creating constructor')), \
                mock.patch.object(Path, 'mkdir', side_effect=AssertionError('mkdir')), \
                mock.patch.object(Store, 'event', side_effect=AssertionError('event')), \
                mock.patch.object(sqlite3, 'connect', side_effect=connect):
            value = self.open()
        self.assertIs(type(value), Store); self.assertEqual((value.root, value.db), (self.root, self.db))
        self.assertEqual(len(connections), 1)
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError): con.execute('SELECT 1')
        self.assertFalse(any(s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'ANALYZE', 'VACUUM')) for s in trace))
        self.assertEqual(self.snapshot(), before)
        with self.legacy.connection() as con:
            self.assertEqual(con.execute('SELECT synthetic FROM blobs').fetchone()[0], 0)

    def test_all_four_real_schema_profiles_are_accepted_and_metadata_reads_leave_bytes_unchanged(self):
        for generation, reference, tables in [(False, False, 20), (True, False, 24), (False, True, 23), (True, True, 27)]:
            legacy = Store(self.base / ('profile-' + str(generation) + '-' + str(reference)))
            self.extend(legacy, generation=generation, reference=reference)
            before = legacy.db.read_bytes()
            value = self.open(str(legacy.root))
            with value.connection() as con:
                self.assertEqual(con.execute("SELECT count(*) FROM sqlite_schema WHERE type='table'").fetchone()[0], tables)
                self.assertIs(type(con.execute('SELECT 1').fetchone()), sqlite3.Row)
            value.close(); self.assertEqual(legacy.db.read_bytes(), before)

    def test_optional_exact_stat1_is_accepted_without_running_analyze_again(self):
        self.extend(self.legacy, generation=True, reference=True)
        with self.legacy.connection() as con: con.execute('ANALYZE')
        before = self.snapshot(); trace = []; original = sqlite3.connect
        def connect(*args, **kwargs):
            con = original(*args, **kwargs); con.set_trace_callback(trace.append); return con
        with mock.patch.object(sqlite3, 'connect', side_effect=connect): value = self.open()
        value.close(); self.assertEqual(self.snapshot(), before)
        self.assertFalse(any('ANALYZE' in s.upper() for s in trace))

    def test_approved_lazy_extension_transition_is_allowed_in_later_connection(self):
        value = self.open()
        self.extend(value, generation=True, reference=True)
        with value.connection() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM intake_reference_records').fetchone()[0], 0)

    def test_exact_str_only_rejects_pathlike_subclass_and_callbacks_before_native_or_SQL(self):
        class Text(str): pass
        class Callback:
            def __fspath__(self): raise AssertionError('PathLike callback')
            def __str__(self): raise AssertionError('str callback')
        class Subclass(Store): pass
        with mock.patch.object(native, '_WindowsIO', side_effect=AssertionError('native')) as backend, \
                mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
            for value in [None, False, 0, self.root, Text(str(self.root)), Callback(), [], {}]:
                self.error('invalid_argument', lambda value=value: Store.open_existing(value))
            self.error('invalid_argument', lambda: Subclass.open_existing(str(self.root)))
        backend.assert_not_called(); connected.assert_not_called()

    def test_empty_controls_surrogate_and_utf8_budget_fail_before_native(self):
        for value in ['', ' ', ' ' + str(self.root), str(self.root) + ' ', str(self.root) + '\n',
                      str(self.root) + '\x00', str(self.root) + '\ud800', 'C:\\' + '가' * 6000]:
            with mock.patch.object(native, '_WindowsIO', side_effect=AssertionError('native')) as backend:
                self.error('invalid_argument', root=value)
            backend.assert_not_called()

    def test_raw_final_and_ancestor_dot_space_aliases_are_rejected_before_normalization(self):
        value = str(self.root)
        values = [value + '.', value + ' ', str(self.root.parent) + '.\\' + self.root.name,
                  str(self.root.parent) + ' \\' + self.root.name, str(self.root.parent) + '\\.\\' + self.root.name,
                  str(self.root.parent) + '\\..\\' + self.root.parent.name + '\\' + self.root.name]
        for raw in values:
            with mock.patch.object(native, '_local_path', wraps=native._local_path) as normalized, \
                    mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
                # Whole-string trailing whitespace is the invalid_argument text boundary.
                self.error('invalid_argument' if raw.endswith(' ') else 'path_invalid', root=raw)
            normalized.assert_not_called(); connected.assert_not_called()

    def test_relative_unc_device_reserved_and_mapped_drive_are_path_errors(self):
        for value in ['workspace', 'C:workspace', r'\\server\share\workspace', r'\\?\C:\workspace',
                      str(self.root / 'NUL'), str(self.root / 'child:stream')]:
            self.error('path_invalid', root=value)
        original = native._WindowsIO
        def remote():
            backend = original(); backend.kernel.GetDriveTypeW = lambda _: 4; return backend
        with mock.patch.object(native, '_WindowsIO', side_effect=remote): self.error('path_invalid')

    def test_normal_unicode_internal_spaces_and_uri_punctuation_are_genuine_success(self):
        legacy = Store(self.base / '합성 workspace #%')
        before = legacy.db.read_bytes(); value = self.open(str(legacy.root))
        with value.connection() as con: self.assertEqual(con.execute('PRAGMA foreign_keys').fetchone()[0], 1)
        value.close(); self.assertEqual(legacy.db.read_bytes(), before)

    def test_missing_root_blobs_or_database_never_creates_or_repairs_files(self):
        self.error('unavailable', root=str(self.base / 'missing'))
        (self.root / 'blobs').rename(self.root / 'retained-blobs')
        self.error('unavailable'); self.assertFalse((self.root / 'blobs').exists())
        (self.root / 'retained-blobs').rename(self.root / 'blobs')
        self.db.rename(self.root / 'retained.sqlite3')
        self.error('unavailable'); self.assertFalse(self.db.exists())

    def test_wrong_root_blobs_DB_kind_is_path_invalid(self):
        self.error('path_invalid', root=str(self.db))
        (self.root / 'blobs').rmdir(); (self.root / 'blobs').write_bytes(b'SYNTHETIC')
        self.error('path_invalid'); (self.root / 'blobs').unlink(); (self.root / 'blobs').mkdir()
        self.db.rename(self.root / 'retained.sqlite3'); self.db.mkdir()
        self.error('path_invalid')

    def test_hardlinked_database_is_rejected_and_both_names_preserved(self):
        other = self.root / 'database-alias'; os.link(self.db, other)
        before = self.snapshot(); self.error('path_invalid'); self.assertEqual(self.snapshot(), before)

    def test_root_ancestor_blobs_junctions_are_rejected_before_SQL(self):
        target = self.base / 'target'; target.mkdir(); Store(target / 'workspace')
        alias = self.base / 'alias'
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(target)], check=True, capture_output=True)
        with mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
            self.error('path_invalid', root=str(alias / 'workspace'))
        connected.assert_not_called()
        (self.root / 'blobs').rmdir()
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.root / 'blobs'), str(target)], check=True, capture_output=True)
        self.error('path_invalid')

    def test_all_fixed_sidecar_entries_are_rejected_before_SQL_without_cleanup(self):
        for name in DB_ENTRIES:
            path = self.root / name; path.write_bytes(b'SYNTHETIC NONJOURNAL')
            before = self.snapshot()
            with mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
                self.error('mode_unsupported')
            connected.assert_not_called(); self.assertEqual(self.snapshot(), before); path.unlink()
        path = self.root / 'lab.sqlite3-journal'; path.mkdir()
        self.error('mode_unsupported'); self.assertTrue(path.is_dir())

    def test_persisted_WAL_header_without_sidecars_is_rejected_before_SQL(self):
        with self.legacy.connection() as con:
            self.assertEqual(con.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
        self.assertTrue(all(not (self.root / name).exists() for name in DB_ENTRIES))
        before = self.snapshot()
        with mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
            self.error('mode_unsupported')
        connected.assert_not_called(); self.assertEqual(self.snapshot(), before)

    def test_zero_short_bad_magic_and_truncated_schema_fail_without_repair(self):
        original = self.db.read_bytes()
        for raw in [b'', b'PRIVATE' * 8, b'X' * 100, original[:100]]:
            self.db.write_bytes(raw); before = self.snapshot(); self.error('integrity_invalid')
            self.assertEqual(self.snapshot(), before)

    def test_partial_unknown_view_index_trigger_column_and_constraint_schema_are_rejected(self):
        changes = [
            'ALTER TABLE cases ADD COLUMN unknown TEXT',
            'CREATE TABLE unknown_application(value TEXT)',
            'CREATE INDEX unknown_index ON cases(synthetic)',
            "CREATE TRIGGER cases_private AFTER INSERT ON cases BEGIN UPDATE blobs SET synthetic=1; END",
            "DROP TABLE events; CREATE VIEW events AS SELECT 'PRIVATE' AS action",
            "DROP TABLE events; CREATE TABLE events(event_id INTEGER PRIMARY KEY,created_at TEXT,action TEXT NOT NULL,subject_id TEXT NOT NULL,details_json TEXT NOT NULL)",
            next(iter(gen._SCHEMA.values()))[1],
            next(iter(refs._DDL.values()))[2],
        ]
        for index, statement in enumerate(changes):
            legacy = Store(self.base / ('bad-schema-' + str(index)))
            with legacy.connection() as con: con.executescript(statement)
            before = legacy.db.read_bytes(); self.error('schema_mismatch', root=str(legacy.root))
            self.assertEqual(legacy.db.read_bytes(), before)

    def test_known_named_index_sort_direction_and_trigger_literal_changes_are_rejected(self):
        self.extend(self.legacy, reference=True)
        with self.legacy.connection() as con:
            con.execute('DROP INDEX intake_reference_records_intake_seq')
            con.execute('CREATE INDEX intake_reference_records_intake_seq ON intake_reference_records(intake_id,seq ASC)')
        self.error('schema_mismatch')
        other = Store(self.base / 'bad-trigger'); self.extend(other, generation=True)
        with other.connection() as con:
            con.execute('DROP TRIGGER intake_analysis_events_no_delete')
            con.execute("CREATE TRIGGER intake_analysis_events_no_delete BEFORE DELETE ON intake_analysis_events BEGIN SELECT RAISE(ABORT,'immutable  analysis_history'); END")
        self.error('schema_mismatch', root=str(other.root))

    def test_many_unknown_schema_objects_fail_boundedly_and_do_not_become_partial_success(self):
        with self.legacy.connection() as con:
            for index in range(130): con.execute('CREATE INDEX extra_' + str(index) + ' ON cases(synthetic)')
        before = self.snapshot(); self.error('schema_mismatch'); self.assertEqual(self.snapshot(), before)

    def test_optional_stat1_wrong_column_definition_is_rejected(self):
        with self.legacy.connection() as con:
            con.execute('ANALYZE'); con.execute('PRAGMA writable_schema=ON')
            con.execute("UPDATE sqlite_schema SET sql='CREATE TABLE sqlite_stat1(tbl,idx,stat,unknown)' WHERE name='sqlite_stat1'")
        self.error('schema_mismatch')

    def test_unread_data_page_is_not_falsely_reported_as_whole_database_integrity(self):
        with self.legacy.connection() as con:
            con.execute('INSERT INTO packages VALUES(?,?,?)', ('SYNTHETIC', 'a' * 64, 'SYNTHETIC' * 70000))
            page = con.execute("SELECT rootpage FROM sqlite_schema WHERE name='packages'").fetchone()[0]
            page_size = con.execute('PRAGMA page_size').fetchone()[0]
        raw = bytearray(self.db.read_bytes()); raw[(page - 1) * page_size] = 0
        self.db.write_bytes(raw); before = self.snapshot(); value = self.open()
        value.close(); self.assertEqual(self.snapshot(), before)
        self.assertFalse(hasattr(value, 'database_integrity_verified'))

    def test_new_mode_rw_URI_foreign_keys_commit_and_rollback_preserve_existing_protocol(self):
        value = self.open(); original = sqlite3.connect; modes = []; connections = []
        def connect(path, **kwargs):
            modes.append(str(path)); self.assertTrue(kwargs.get('uri')); self.assertEqual(kwargs.get('timeout'), 30)
            con = original(path, **kwargs); connections.append(con); return con
        with mock.patch.object(sqlite3, 'connect', side_effect=connect):
            with value.connection() as con:
                self.assertIs(con.row_factory, sqlite3.Row)
                self.assertEqual(con.execute('PRAGMA foreign_keys').fetchone()[0], 1)
                con.execute("INSERT INTO events(created_at,action,subject_id,details_json) VALUES('SYN','commit','SYN','{}')")
            with self.assertRaisesRegex(RuntimeError, 'SYNTHETIC business refusal'):
                with value.connection() as con:
                    con.execute("INSERT INTO events(created_at,action,subject_id,details_json) VALUES('SYN','rollback','SYN','{}')")
                    raise RuntimeError('SYNTHETIC business refusal')
        self.assertEqual(modes, [value.db.as_uri() + '?mode=rw'] * 2)
        with value.connection() as con:
            self.assertEqual([r[0] for r in con.execute('SELECT action FROM events')], ['commit'])
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError): con.execute('SELECT 1')

    def test_metadata_validation_does_not_reject_own_active_DML_rollback_journal(self):
        value = self.open()
        with value.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute("INSERT INTO events(created_at,action,subject_id,details_json) VALUES('SYN','write','SYN','{}')")
            self.assertTrue((self.root / 'lab.sqlite3-journal').exists())
        self.assertFalse((self.root / 'lab.sqlite3-journal').exists())

    def test_visible_new_sidecar_or_WAL_mode_is_rechecked_before_later_connection(self):
        value = self.open(); side = self.root / 'lab.sqlite3-journal'; side.write_bytes(b'SYNTHETIC')
        self.error('mode_unsupported', lambda: self.enter_connection(value)); side.unlink()
        with self.legacy.connection() as con: con.execute('PRAGMA journal_mode=WAL')
        self.error('mode_unsupported', lambda: self.enter_connection(value))

    def enter_connection(self, value):
        with value.connection() as con: con.execute('SELECT 1')

    def test_binding_root_or_db_attribute_change_fails_before_SQL(self):
        value = self.open()
        for field, replacement in [('root', self.base), ('db', self.root / 'another.sqlite3'), ('db', 'PRIVATE')]:
            original = getattr(value, field); setattr(value, field, replacement)
            with mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
                self.error('input_changed', lambda: self.enter_connection(value))
            connected.assert_not_called(); setattr(value, field, original)

    def test_binding_changed_during_body_is_rejected_before_implicit_commit(self):
        value = self.open()
        def changed():
            with value.connection() as con:
                con.execute("INSERT INTO events(created_at,action,subject_id,details_json) VALUES('SYN','uncommitted','SYN','{}')")
                value.db = self.root / 'different.sqlite3'
        try:
            self.error('input_changed', changed)
        finally:
            value.db = self.db
        with value.connection() as con: self.assertEqual(con.execute('SELECT count(*) FROM events').fetchone()[0], 0)

    def test_SQLite_body_error_is_sanitized_without_private_exception_context(self):
        value = self.open()
        def rejected():
            with value.connection() as con:
                con.execute("INSERT INTO documents(document_id,package_id,record_json,synthetic) VALUES('SYN','MISSING','{}',1)")
        self.error('unavailable', rejected)

    def test_fixed_errors_have_no_context_even_inside_a_callers_active_exception_handler(self):
        def checked(suffix, operation):
            try:
                raise RuntimeError('PRIVATE caller exception')
            except RuntimeError:
                self.error(suffix, operation)
        checked('invalid_argument', lambda: Store.open_existing(None))
        checked('unavailable', lambda: Store.open_existing(str(self.base / 'absent')))
        value = self.open()
        with value.connection(): checked('unavailable', value.close)
        descriptor = value._existing_binding.handles[-1]; original = os.close
        def close(number):
            if number == descriptor: raise OSError('PRIVATE native close')
            original(number)
        with mock.patch.object(os, 'close', side_effect=close): checked('unavailable', value.close)
        value.close()
        checked('closed', value.__enter__)
        checked('closed', lambda: self.enter_connection(value))

    def test_actual_busy_commit_is_fixed_and_rolls_back_without_losing_lifetime_pins(self):
        value = self.open(); original = sqlite3.connect
        reader = original(self.db.as_uri() + '?mode=ro', uri=True)
        self.addCleanup(reader.close)
        reader.execute('BEGIN'); reader.execute('SELECT count(*) FROM events').fetchone()
        def connect(*args, **kwargs):
            con = original(*args, **kwargs); con.execute('PRAGMA busy_timeout=0'); return con
        def blocked():
            with value.connection() as con:
                con.execute("INSERT INTO events(created_at,action,subject_id,details_json) VALUES('SYN','busy','SYN','{}')")
        with mock.patch.object(sqlite3, 'connect', side_effect=connect): self.error('unavailable', blocked)
        reader.rollback(); reader.close()
        with value.connection() as con: self.assertEqual(con.execute('SELECT count(*) FROM events').fetchone()[0], 0)
        self.assertFalse((self.root / 'lab.sqlite3-journal').exists())
        with self.assertRaises(OSError): self.db.rename(self.root / 'moved.sqlite3')
        self.evidence = {'kind': 'official043_sqlite_busy', 'fixed_error': 'store_open_unavailable', 'rolled_back': True}

    def test_actual_native_write_denial_is_not_a_successful_rw_permission_claim(self):
        value = self.open(); backend = native._WindowsIO(); self.addCleanup(backend.close)
        native._Tree(self.root, backend)
        descriptor = backend.open_read(self.db, pin=True)
        self.assertGreaterEqual(descriptor, 0)
        def denied():
            with value.connection() as con:
                con.execute("INSERT INTO events(created_at,action,subject_id,details_json) VALUES('SYN','denied','SYN','{}')")
        self.error('unavailable', denied)
        backend.close()
        with value.connection() as con: self.assertEqual(con.execute('SELECT count(*) FROM events').fetchone()[0], 0)
        self.evidence = {'kind': 'official043_write_denial', 'fixed_error': 'store_open_unavailable', 'stored_rows': 0}

    def test_stored_SQL_individual_and_total_budgets_fail_before_materializing_definitions(self):
        for single in (True, False):
            legacy = Store(self.base / ('sql-budget-' + str(single)))
            with legacy.connection() as con:
                con.execute('PRAGMA writable_schema=ON')
                if single:
                    con.execute("UPDATE sqlite_schema SET sql=sql||? WHERE name='events'", (' ' * (32 * 1024),))
                else:
                    con.execute("UPDATE sqlite_schema SET sql=sql||? WHERE type='table'", (' ' * 15000,))
                con.execute('PRAGMA writable_schema=OFF')
            before = legacy.db.read_bytes()
            with mock.patch.object(module, '_open_rows', side_effect=AssertionError('unbounded metadata fetch')):
                self.error('schema_mismatch', root=str(legacy.root))
            self.assertEqual(legacy.db.read_bytes(), before)

    def test_missing_required_metadata_function_is_backend_unavailable_without_fallback(self):
        original = sqlite3.connect
        for function in ('table_xinfo', 'foreign_key_list', 'index_list', 'index_xinfo'):
            failure = sqlite3.OperationalError('no such table: pragma_' + function)
            failure.sqlite_errorcode = sqlite3.SQLITE_ERROR
            class MissingFunction(ConnectionFault):
                def execute(self, statement, *args, **kwargs):
                    if 'FROM pragma_' + function + '(' in statement: raise failure
                    return super().execute(statement, *args, **kwargs)
            def connect(*args, **kwargs): return MissingFunction(original(*args, **kwargs))
            with mock.patch.object(sqlite3, 'connect', side_effect=connect): self.error('backend_unavailable')

    def test_genuine_synthetic_intake_snapshot_and_reference_append_use_exact_official_Store(self):
        from labflow.active_intake import register_source, scan_source
        from labflow.intake_jobs import claim_job, complete_job, respond
        from labflow.intake_worker import SyntheticTextProvider
        from labflow.intake_reference_snapshot import read_intake_reference_snapshot
        from labflow.intake_case_references import build_intake_case_reference_receipt
        from tests.test_document_extract import synthetic_pdf
        from tests.test_intake_case_references import catalog_fixture, context_for, response_for
        inbox = self.base / 'inbox'; (inbox / 'one').mkdir(parents=True)
        register_source(self.legacy, 'SYN-INBOX', inbox, synthetic=True, settle_seconds=1)
        (inbox / 'one' / 'request.pdf').write_bytes(synthetic_pdf([
            'product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A']))
        scan_source(self.legacy, 'SYN-INBOX', now=100); scan_source(self.legacy, 'SYN-INBOX', now=102)
        job = claim_job(self.legacy, 'SYN-WORKER', now=103)
        complete_job(self.legacy, job['job_id'], job['token'], SyntheticTextProvider().analyze(job), now=104)
        respond(self.legacy, 'SYN-PROCEED', 'proceed', intake_id=job['intake_id'])
        value = self.open(); self.assertIs(type(value), Store)
        with mock.patch.object(Store, '__init__', side_effect=AssertionError('creating constructor')):
            capture = read_intake_reference_snapshot(value, job['intake_id'])
            catalog = catalog_fixture(); context = context_for(catalog); response = response_for(context)
            receipt = build_intake_case_reference_receipt(capture['snapshot'], catalog, context, response,
                                                         producer_name=response['expected_producer']['name'])
            args = dict(expected_snapshot_id=capture['snapshot_id'], expected_head_record_id=None,
                        intake_snapshot=capture['snapshot'], catalog=catalog, case_context=context,
                        validated_response=response, reference_receipt=receipt,
                        producer_name=response['expected_producer']['name'])
            registered = refs.record_intake_reference(value, 'SYN-REQUEST-043', **args)
            history = refs.reference_history(value, job['intake_id'])
            current = refs.current_reference(value, job['intake_id'])
            replay = refs.record_intake_reference(value, 'SYN-REQUEST-043', **args)
        self.assertTrue(capture['readiness']['ready']); self.assertEqual(receipt['status'], 'bound')
        self.assertTrue(registered['stored']); self.assertTrue(replay['replayed'])
        self.assertEqual(registered['record_id'], replay['record_id']); self.assertEqual(len(history['records']), 1)
        self.assertEqual(current['status'], 'current')
        with value.connection() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM intake_reference_records').fetchone()[0], 1)
        self.evidence = {'kind': 'official043_synthetic_intake_034_038', 'exact_Store': True,
                         'snapshot_ready': True, 'append_rows': 1, 'replay_rows': 0,
                         'actual_customer_DB_or_PDF': 0, '042_executed': False}

    def test_unknown_later_schema_is_rejected_before_user_body(self):
        value = self.open()
        with self.legacy.connection() as con: con.execute('CREATE TABLE unsupported(value TEXT)')
        self.error('schema_mismatch', lambda: self.enter_connection(value))

    def test_lifetime_pins_block_db_blobs_root_parent_moves_then_release_after_close(self):
        value = self.open(); paths = [self.db, self.root / 'blobs', self.root, self.base]
        for path in paths:
            destination = path.with_name(path.name + '.moved')
            self.assertTrue(path.resolve().is_relative_to(self.base.parent.resolve()))
            self.assertTrue(destination.resolve().is_relative_to(self.base.parent.resolve()))
            with self.assertRaises(OSError): path.rename(destination)
        value.close()
        for path in paths:
            destination = path.with_name(path.name + '.moved'); path.rename(destination); destination.rename(path)
        self.evidence = {'kind': 'official043_native_lifetime', 'blocked_renames': 4, 'released_renames': 4,
                         'exact_Store': True, 'actual_customer_DB_or_PDF': 0}

    def test_close_and_context_exit_are_idempotent_and_later_connection_enter_are_closed(self):
        with Store.open_existing(str(self.root)) as value:
            self.assertIs(type(value), Store)
            self.assertIs(value.__enter__(), value)
        value.close(); value.close()
        self.error('closed', lambda: self.enter_connection(value))
        self.error('closed', value.__enter__)

    def test_active_context_close_is_rejected_and_does_not_close_connection_or_pins(self):
        value = self.open()
        with value.connection() as con:
            self.error('unavailable', value.close)
            self.assertEqual(con.execute('SELECT 1').fetchone()[0], 1)
            with self.assertRaises(OSError): self.db.rename(self.root / 'moved.sqlite3')
        value.close(); self.db.rename(self.root / 'moved.sqlite3')

    def test_setup_in_flight_is_counted_so_concurrent_close_cannot_release_pins(self):
        value = self.open(); entered, release = threading.Event(), threading.Event(); errors = []
        original = sqlite3.connect
        def connect(*args, **kwargs):
            entered.set(); self.assertTrue(release.wait(5)); return original(*args, **kwargs)
        def worker():
            try: self.enter_connection(value)
            except BaseException as error: errors.append(error)
        with mock.patch.object(sqlite3, 'connect', side_effect=connect):
            thread = threading.Thread(target=worker, daemon=True); thread.start()
            try:
                self.assertTrue(entered.wait(5)); self.error('unavailable', value.close)
            finally: release.set(); thread.join(5)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors, []); value.close()

    def test_partial_native_close_failure_keeps_resource_for_retry_and_new_connections_closed(self):
        original_relative = native._WindowsIO._relative; pin_fds = []
        def relative(backend, parent, name, **kwargs):
            fd = original_relative(backend, parent, name, **kwargs)
            if name == 'lab.sqlite3' and kwargs.get('share') == 3: pin_fds.append(fd)
            return fd
        with mock.patch.object(native._WindowsIO, '_relative', new=relative): value = self.open()
        self.assertEqual(len(pin_fds), 1); descriptor = pin_fds[0]; original_close = os.close; failed = []
        def close(fd):
            if fd == descriptor and not failed:
                failed.append(fd); raise OSError('PRIVATE native close')
            return original_close(fd)
        with mock.patch.object(os, 'close', side_effect=close): self.error('unavailable', value.close)
        self.error('closed', lambda: self.enter_connection(value))
        with self.assertRaises(OSError): self.db.rename(self.root / 'still-pinned')
        value.close(); self.db.rename(self.root / 'released'); (self.root / 'released').rename(self.db)

    def test_context_body_error_wins_over_secondary_native_close_failure_and_can_be_retried(self):
        value = self.open(); original = os.close; failed = []
        def close(fd):
            if not failed: failed.append(fd); raise OSError('PRIVATE native close')
            return original(fd)
        expected = RuntimeError('SYNTHETIC primary body')
        with mock.patch.object(os, 'close', side_effect=close):
            with self.assertRaises(RuntimeError) as caught:
                with value: raise expected
        self.assertIs(caught.exception, expected); value.close()

    def test_owned_SQLite_close_failure_is_sanitized_and_body_business_error_is_preserved(self):
        value = self.open(); original = sqlite3.connect
        def connect(*args, **kwargs): return ConnectionFault(original(*args, **kwargs), close_failure=True)
        with mock.patch.object(sqlite3, 'connect', side_effect=connect):
            self.error('unavailable', lambda: self.enter_connection(value))
            expected = RuntimeError('SYNTHETIC primary body')
            with self.assertRaises(RuntimeError) as caught:
                with value.connection(): raise expected
            self.assertIs(caught.exception, expected)
        with value.connection() as con: self.assertEqual(con.execute('SELECT 1').fetchone()[0], 1)

    def test_factory_SQLite_failure_releases_all_native_pins_and_returns_no_store(self):
        with mock.patch.object(sqlite3, 'connect', side_effect=sqlite3.OperationalError('PRIVATE ' + str(self.db))):
            self.error('unavailable')
        moved = self.root.with_name('after-failed-open'); self.root.rename(moved); moved.rename(self.root)

    def test_known_metadata_corrupt_and_unknown_query_errors_are_fixed_without_raw_context(self):
        original = sqlite3.connect
        for code, suffix in [(sqlite3.SQLITE_CORRUPT, 'integrity_invalid'), (sqlite3.SQLITE_NOTADB, 'integrity_invalid'),
                             (sqlite3.SQLITE_BUSY, 'unavailable'), (sqlite3.SQLITE_ERROR, 'unavailable')]:
            error = sqlite3.DatabaseError('PRIVATE ' + str(self.db)); error.sqlite_errorcode = code
            def connect(*args, **kwargs): return ConnectionFault(original(*args, **kwargs), query_failure=error)
            with mock.patch.object(sqlite3, 'connect', side_effect=connect): self.error(suffix)

    def test_backend_unavailable_has_no_SQL_or_creating_fallback(self):
        with mock.patch.object(native, '_WindowsIO', side_effect=RuntimeError('PRIVATE backend')), \
                mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQL')) as connected:
            self.error('backend_unavailable')
        connected.assert_not_called()

    def test_finalizer_is_fallback_and_does_not_keep_the_Store_alive(self):
        value = Store.open_existing(str(self.root)); reference = weakref.ref(value)
        del value; gc.collect(); self.assertIsNone(reference())
        self.db.rename(self.root / 'after-gc'); (self.root / 'after-gc').rename(self.db)

    def test_legacy_creating_Path_default_and_update_behaviour_remain_compatible(self):
        with self.legacy.connection() as con:
            con.execute('INSERT INTO blobs VALUES(?,?,?,?)', ('b' * 64, 1, 'synthetic_evidence', 0))
        legacy = Store(self.root)
        legacy.close()
        with legacy.connection() as con:
            self.assertEqual(con.execute('SELECT synthetic FROM blobs').fetchone()[0], 1)
        with legacy as entered: self.assertIs(entered, legacy)
        with legacy.connection() as con: self.assertEqual(con.execute('SELECT 1').fetchone()[0], 1)
