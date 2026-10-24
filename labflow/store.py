from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import sqlite3
import threading
import weakref

from . import control_packet_prepare as _open_native


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}',value):
        raise ValueError('Invalid identifier')
    return value


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class Store:
    @classmethod
    def open_existing(cls, root):
        """Open an existing, locally pinned Store; validate header/known schema only."""
        binding, failure, interrupted, result = None, None, None, None
        try:
            if cls is not Store:
                _open_fail('invalid_argument')
            path = _existing_path(root)
            binding = _ExistingBinding(path)
            binding.acquire()
            binding.validate_read_only()
            result = object.__new__(Store)
            result.root, result.db = path, binding.db
            result._existing_binding = binding
            binding.state = 'open'
        except Exception as error:
            failure = _open_code(error)
        except BaseException as error:
            interrupted = error
        if failure is not None or interrupted is not None:
            if binding is not None:
                try:
                    binding.close()
                except Exception:
                    pass
            if interrupted is not None:
                raise interrupted
            _raise_open_error(failure)
        return result

    def __init__(self,root):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        (self.root/'blobs').mkdir(exist_ok=True)
        self.db=self.root/'lab.sqlite3'
        with self.connection() as con:
            con.executescript(Path(__file__).with_name('schema.sql').read_text())
            if 'synthetic' not in {r['name'] for r in con.execute('PRAGMA table_info(blobs)')}:
                con.execute('ALTER TABLE blobs ADD COLUMN synthetic INTEGER NOT NULL DEFAULT 0')
            # Preserve provenance when opening stores created by the first core version.
            con.execute("UPDATE blobs SET synthetic=1 WHERE kind='synthetic_evidence' OR sha256 IN (SELECT sha256 FROM documents WHERE synthetic=1)")
            con.execute('UPDATE blobs SET synthetic=1 WHERE sha256 IN '
                        '(SELECT r.raw_sha256 FROM runs r JOIN plans p USING(plan_id) JOIN cases c USING(case_id) WHERE c.synthetic=1)')

    @contextmanager
    def connection(self):
        binding = self.__dict__.get('_existing_binding')
        if binding is not None:
            try:
                with binding.connection(self) as con:
                    yield con
            except StoreOpenError as error:
                # The outer generator receives the caller's original SQL exception.
                error.__context__ = None
                error.__cause__ = None
                raise
            return
        con=sqlite3.connect(self.db,timeout=30)
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:yield con
        finally:con.close()

    def close(self):
        binding = self.__dict__.get('_existing_binding')
        if binding is not None:
            binding.close()

    def __enter__(self):
        binding = self.__dict__.get('_existing_binding')
        if binding is not None:
            binding.enter(self)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is None:
            self.close()
        else:
            try:
                self.close()
            except Exception:
                pass
        return False

    def event(self,con,action,subject,details):
        con.execute('INSERT INTO events(created_at,action,subject_id,details_json) VALUES(?,?,?,?)',
                    (utcnow(),action,subject,canonical(details)))

    def blob_path(self,sha):
        if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Invalid SHA256')
        return self.root/'blobs'/sha

    def verify_blob(self,sha):
        path=self.blob_path(sha)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError('Missing or corrupted evidence: '+sha)
        return path

    def write_blob(self,payload):
        sha=hashlib.sha256(payload).hexdigest();path=self.blob_path(sha)
        try:
            with path.open('xb') as stream:stream.write(payload)
        except FileExistsError:self.verify_blob(sha)
        return sha

    def register_blob(self,con,sha,size,kind,synthetic=False):
        if not isinstance(synthetic,bool):raise ValueError('synthetic must be boolean')
        con.execute('INSERT INTO blobs(sha256,bytes,kind,synthetic) VALUES(?,?,?,?) '
                    'ON CONFLICT(sha256) DO UPDATE SET synthetic=MAX(blobs.synthetic,excluded.synthetic)',
                    (sha,size,kind,int(synthetic)))

    def evidence_is_synthetic(self,sha):
        if not sha:return False
        with self.connection() as con:
            row=con.execute('SELECT synthetic FROM blobs WHERE sha256=?',(sha,)).fetchone()
        return bool(row and row['synthetic'])

    def import_artifact(self,path,kind='raw',*,synthetic=False):
        if not isinstance(synthetic,bool):raise ValueError('synthetic must be boolean')
        path=Path(path)
        if not path.is_file() or path.stat().st_size>536870912:raise ValueError('Missing or oversized artifact')
        payload=path.read_bytes()
        if not payload:raise ValueError('Empty artifact')
        sha=self.write_blob(payload)
        with self.connection() as con:
            self.register_blob(con,sha,len(payload),kind,synthetic)
            self.event(con,'artifact.import',sha,{'kind':kind,'synthetic_declared':synthetic})
        return sha

    def document(self,document_id):
        with self.connection() as con:
            row=con.execute('SELECT * FROM documents WHERE document_id=?',(document_id,)).fetchone()
        if row is None:raise ValueError('Unknown document: '+str(document_id))
        return {**json.loads(row['record_json']),'sha256':row['sha256'],'review_status':row['review_status'],
                'synthetic':bool(row['synthetic']) or self.evidence_is_synthetic(row['sha256'])}

    def documents(self):
        with self.connection() as con:ids=[r[0] for r in con.execute('SELECT document_id FROM documents ORDER BY document_id')]
        return [self.document(i) for i in ids]

    def review_document(self,document_id,reviewer,note):
        if not str(reviewer).strip() or not str(note).strip():raise ValueError('Reviewer and technical review note required')
        doc=self.document(document_id)
        if doc['status']!='downloaded' or doc['representation']!='original' or doc['rights'] not in {'public','licensed_internal'}:
            raise ValueError('Only an acquired original with known usable rights can be reviewed')
        self.verify_blob(doc['sha256'])
        with self.connection() as con:
            con.execute("UPDATE documents SET review_status='reviewed' WHERE document_id=?",(document_id,))
            self.event(con,'document.review',document_id,{'reviewer':reviewer,'note':note})
        return self.document(document_id)

    def row(self,table,key):
        keys={'cases':'case_id','methods':'method_id','plans':'plan_id','runs':'run_id'}
        if table not in keys:raise ValueError('Unknown entity')
        with self.connection() as con:row=con.execute(f'SELECT * FROM {table} WHERE {keys[table]}=?',(key,)).fetchone()
        if row is None:raise ValueError(f'Unknown {table}: {key}')
        return {**dict(row),'data':json.loads(row['data_json'])}


_OPEN_CODES = frozenset('store_open_' + suffix for suffix in (
    'invalid_argument', 'path_invalid', 'unavailable', 'schema_mismatch', 'input_changed',
    'integrity_invalid', 'closed', 'backend_unavailable', 'mode_unsupported'))
_OPEN_PROFILES = frozenset((
    '54038e1a02efa7ced5828fdf0b7e542cfda0c889723ea2f4419e18f901e9f0ff',
    'f49682fff98de95d9b14c35170c0c3ff340491457f45993a6b88b74b6bdc8120',
    '0e27d130b66fd3f7a52dca8d4e910fec965b2a8ac97d41e09e222844eecba8d8',
    '496f92f0d4f3dd773998ab97dffa0f10176c3142d24c4eda0cde42a908d40532'))
_OPEN_TABLES = frozenset(('blobs', 'packages', 'documents', 'cases', 'methods', 'plans', 'runs',
    'evaluations', 'events', 'intake_sources', 'intakes', 'intake_observations', 'intake_revisions',
    'intake_jobs', 'intake_questions', 'intake_answers', 'intake_responses', 'intake_notifications',
    'intake_notice_state', 'intake_fixture_jobs', 'intake_analysis_generations', 'intake_analysis_heads',
    'intake_analysis_requests', 'intake_analysis_events', 'intake_reference_records',
    'intake_reference_heads', 'intake_reference_events'))
_OPEN_PATH_TYPE = type(Path())


class StoreOpenError(ValueError):
    """Fixed new-mode error; no path, raw storage message, or exception chaining."""
    def __init__(self, code):
        self.code = code if type(code) is str and code in _OPEN_CODES else 'store_open_invalid_argument'
        super().__init__(self.code)


def _raise_open_error(code):
    # A caller may already be handling an exception outside this function.
    try:
        raise StoreOpenError(code) from None
    except StoreOpenError as error:
        error.__context__ = None
        error.__cause__ = None
        raise


def _open_fail(suffix):
    raise StoreOpenError('store_open_' + suffix)


def _open_code(error):
    if isinstance(error, StoreOpenError):
        return error.code if type(error.code) is str and error.code in _OPEN_CODES else 'store_open_unavailable'
    if isinstance(error, _open_native.ControlPacketPrepareError):
        return 'store_open_path_invalid'
    if isinstance(error, (NotADirectoryError, IsADirectoryError)):
        return 'store_open_path_invalid'
    if isinstance(error, sqlite3.Error):
        try:
            code = getattr(error, 'sqlite_errorcode', None)
            if type(code) is int and code & 255 in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
                return 'store_open_integrity_invalid'
        except Exception:
            pass
    return 'store_open_unavailable'


def _existing_path(value):
    if (type(value) is not str or not value or value.strip() != value
            or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)):
        _open_fail('invalid_argument')
    try:
        size = len(value.encode('utf-8', errors='strict'))
    except UnicodeError:
        _open_fail('invalid_argument')
    if size > 16 * 1024:
        _open_fail('invalid_argument')
    drive, tail = ntpath.splitdrive(value)
    if (value.startswith(('\\\\', '//')) or not re.fullmatch('[A-Za-z]:', drive, re.ASCII)
            or not tail.startswith(('\\', '/'))
            or any(not _open_native._valid_segment(p) for p in re.split(r'[\\/]', tail) if p)):
        _open_fail('path_invalid')
    return _open_native._local_path(value)


def _open_rows(con, statement, parameters=()):
    try:
        return [dict(row) for row in con.execute(statement, parameters)]
    except sqlite3.OperationalError as error:
        missing = {('no such table: pragma_' + name,) for name in
                   ('table_xinfo', 'foreign_key_list', 'index_list', 'index_xinfo')}
        if getattr(error, 'sqlite_errorcode', None) == sqlite3.SQLITE_ERROR and error.args in missing:
            _open_fail('backend_unavailable')
        raise


def _existing_schema(con):
    # Count/measure before fetching SQL definitions from an unsupported database.
    row = con.execute("SELECT count(*) AS n,coalesce(sum(length(CAST(sql AS BLOB))),0) AS total,"
        "coalesce(max(length(CAST(sql AS BLOB))),0) AS largest,"
        "coalesce(sum(length(CAST(name AS BLOB))+length(CAST(type AS BLOB))+"
        "length(CAST(tbl_name AS BLOB))+coalesce(length(CAST(sql AS BLOB)),0)),0) AS bytes FROM sqlite_schema").fetchone()
    if row['n'] > 128 or row['total'] > 256 * 1024 or row['largest'] > 32 * 1024 or row['bytes'] > 2 * 1024 * 1024:
        _open_fail('schema_mismatch')
    objects = _open_rows(con, 'SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name')
    for row in objects:
        if (row['type'] not in ('table', 'index', 'trigger')
                or row['tbl_name'] not in _OPEN_TABLES | {'sqlite_stat1'}
                or (row['type'] == 'table' and row['name'] not in _OPEN_TABLES | {'sqlite_stat1'})):
            _open_fail('schema_mismatch')
    tables, count_columns, count_indexes, count_fks = {}, 0, 0, 0
    for row in objects:
        if row['type'] != 'table':
            continue
        name = row['name']
        columns = _open_rows(con, 'SELECT * FROM pragma_table_xinfo(?) ORDER BY cid LIMIT 514', (name,))
        keys = _open_rows(con, 'SELECT * FROM pragma_foreign_key_list(?) ORDER BY id,seq LIMIT 130', (name,))
        indexes = []
        for index in _open_rows(con, 'SELECT * FROM pragma_index_list(?) ORDER BY name LIMIT 66', (name,)):
            index.pop('seq', None)
            index['columns'] = _open_rows(con, 'SELECT * FROM pragma_index_xinfo(?) ORDER BY seqno LIMIT 514', (index['name'],))
            indexes.append(index)
        if name == 'sqlite_stat1':
            expected_columns = [{'cid': i, 'name': column, 'type': '', 'notnull': 0, 'dflt_value': None,
                                 'pk': 0, 'hidden': 0} for i, column in enumerate(('tbl', 'idx', 'stat'))]
            if (row != {'type': 'table', 'name': name, 'tbl_name': name, 'sql': 'CREATE TABLE sqlite_stat1(tbl,idx,stat)'}
                    or columns != expected_columns or keys or indexes
                    or any(other['name'] != name and other['tbl_name'] == name for other in objects)):
                _open_fail('schema_mismatch')
            continue
        count_columns += len(columns); count_indexes += len(indexes); count_fks += len(keys)
        if count_columns > 512 or count_indexes > 64 or count_fks > 128:
            _open_fail('schema_mismatch')
        tables[name] = {'columns': columns, 'foreign_keys': keys, 'indexes': indexes}
    value = {'objects': [row for row in objects if row['name'] != 'sqlite_stat1'], 'tables': tables}
    raw = canonical(value).encode('utf-8')
    if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() not in _OPEN_PROFILES:
        _open_fail('schema_mismatch')


def _open_sql(path, mode):
    con = sqlite3.connect(path.as_uri() + '?mode=' + mode, uri=True, timeout=30)
    try:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        if con.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
            _open_fail('unavailable')
    except BaseException:
        try:
            con.close()
        except Exception:
            pass
        raise
    return con


def _finalize_open_handles(handles):
    # Holds the descriptor list, never its Store/Binding owner.
    for descriptor in list(reversed(handles)):
        try:
            os.close(descriptor)
        except OSError:
            pass


class _ExistingBinding:
    def __init__(self, root):
        self.root, self.db = root, root / 'lab.sqlite3'
        self.backend, self.tree, self.descriptor, self.identity = None, None, None, None
        self.handles, self.lock = [], threading.RLock()
        self.state, self.active = 'opening', 0
        self.finalizer = weakref.finalize(self, _finalize_open_handles, self.handles)

    def acquire(self):
        try:
            self.backend = _open_native._WindowsIO()
        except Exception:
            _open_fail('backend_unavailable')
        self.backend.held = self.handles
        self.tree = _open_native._Tree(self.root, self.backend)
        self.tree.directory(self.root / 'blobs')
        before = self.tree.file_stat(self.db)
        descriptor = self.backend._relative(self.backend.directories[self.root], self.db.name,
                                            directory=False, access=0x100081, share=3)
        self.handles.append(descriptor); self.descriptor = descriptor
        self.identity = _open_native._identity(os.fstat(descriptor))
        if self.identity != _open_native._identity(before):
            _open_fail('input_changed')

    def check_owner(self, owner):
        if (type(owner.__dict__.get('root')) is not _OPEN_PATH_TYPE or type(owner.__dict__.get('db')) is not _OPEN_PATH_TYPE
                or owner.root != self.root or owner.db != self.db):
            _open_fail('input_changed')

    def check_identity(self):
        with self.lock:
            try:
                self.tree.directory(self.root / 'blobs')
                info = self.backend.info(self.descriptor, directory=False)
                path_info = self.tree.file_stat(self.db)
            except (_open_native.ControlPacketPrepareError, NotADirectoryError, IsADirectoryError):
                _open_fail('input_changed')
            if _open_native._identity(info) != self.identity or _open_native._identity(path_info) != self.identity:
                _open_fail('input_changed')
            if info.st_nlink != 1:
                _open_fail('path_invalid')
            return info

    def admission(self):
        with self.lock:
            info = self.check_identity()
            for suffix in ('-wal', '-shm', '-journal'):
                try:
                    self.backend.stat_file(self.db.with_name(self.db.name + suffix))
                except FileNotFoundError:
                    continue
                except _open_native.ControlPacketPrepareError:
                    _open_fail('mode_unsupported')
                _open_fail('mode_unsupported')
            if info.st_size < 100:
                _open_fail('integrity_invalid')
            os.lseek(self.descriptor, 0, os.SEEK_SET)
            header = bytearray()
            while len(header) < 100:
                block = os.read(self.descriptor, 100 - len(header))
                if not block:
                    _open_fail('integrity_invalid')
                header.extend(block)
            if header[:16] != b'SQLite format 3\x00':
                _open_fail('integrity_invalid')
            if header[18:20] != b'\x01\x01':
                _open_fail('mode_unsupported')

    def validate_read_only(self):
        con, failure, interrupted = None, None, None
        try:
            self.admission()
            con = _open_sql(self.db, 'ro')
            con.execute('PRAGMA query_only=ON'); con.execute('BEGIN')
            _existing_schema(con)
            self.admission()
        except Exception as error:
            failure = _open_code(error)
        except BaseException as error:
            interrupted = error
        finally:
            if con is not None:
                try:
                    if con.in_transaction:
                        con.rollback()
                except Exception:
                    if failure is None and interrupted is None:
                        failure = 'store_open_unavailable'
                try:
                    con.close()
                except Exception:
                    if failure is None and interrupted is None:
                        failure = 'store_open_unavailable'
        if interrupted is not None:
            raise interrupted
        if failure is not None:
            _raise_open_error(failure)

    def enter(self, owner):
        failure = None
        try:
            with self.lock:
                if self.state != 'open':
                    _open_fail('closed')
                self.check_owner(owner)
        except Exception as error:
            failure = _open_code(error)
        if failure is not None:
            _raise_open_error(failure)

    @contextmanager
    def connection(self, owner):
        con, failure, body_error, reserved = None, None, None, False
        try:
            with self.lock:
                if self.state != 'open':
                    _open_fail('closed')
                self.active += 1; reserved = True
            self.check_owner(owner); self.admission()
            con = _open_sql(self.db, 'rw')
            con.execute('PRAGMA query_only=ON'); con.execute('BEGIN')
            _existing_schema(con); self.admission()
            con.rollback(); con.execute('PRAGMA query_only=OFF')
            try:
                yield con
            except BaseException as error:
                if isinstance(error, sqlite3.Error):
                    failure = _open_code(error)
                else:
                    body_error = error
            if failure is not None or body_error is not None:
                if con.in_transaction:
                    try:
                        con.rollback()
                    except Exception:
                        pass
            else:
                # Check identity without rejecting this connection's own journal.
                self.check_owner(owner); self.check_identity()
                con.commit()
                self.check_owner(owner); self.check_identity()
        except Exception as error:
            if failure is None and body_error is None:
                failure = _open_code(error)
        except BaseException as error:
            if body_error is None:
                body_error = error
        finally:
            if con is not None:
                if failure is not None or body_error is not None:
                    try:
                        if con.in_transaction:
                            con.rollback()
                    except Exception:
                        pass
                try:
                    con.close()
                except Exception:
                    if failure is None and body_error is None:
                        failure = 'store_open_unavailable'
            if reserved:
                with self.lock:
                    self.active -= 1
        if body_error is not None:
            raise body_error
        if failure is not None:
            _raise_open_error(failure)

    def close(self):
        failure = None
        with self.lock:
            if self.active:
                failure = 'store_open_unavailable'
            else:
                self.state = 'closing'
                for descriptor in list(reversed(self.handles)):
                    try:
                        os.close(descriptor)
                    except OSError:
                        failure = 'store_open_unavailable'
                        try:
                            os.fstat(descriptor)
                        except OSError:
                            self.handles.remove(descriptor)
                    else:
                        self.handles.remove(descriptor)
                if self.backend is not None:
                    self.backend.directories = {p: fd for p, fd in self.backend.directories.items() if fd in self.handles}
                self.state = 'closed'
                if not self.handles:
                    self.finalizer.detach()
        if failure is not None:
            _raise_open_error(failure)
