"""Explicit, atomic imports of immutable completed PDF analysis origins."""
import hashlib
import hmac
import json
import math
import re
import sqlite3

from .intake_generation import validate_retained_analysis
from .store import canonical, identifier, utcnow


MAX_RESULT_BYTES = 8 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_INTEGER_MAX = (1 << 63) - 1
_PREFIX = 'intake_analysis_'
_G = _PREFIX + 'generations'
_H = _PREFIX + 'heads'
_R = _PREFIX + 'requests'
_E = _PREFIX + 'events'
_SHA_CHECK = "length({0})=64 AND {0} NOT GLOB '*[^0-9a-f]*'"


def _fail(code):
    raise ValueError(code)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _intake(value):
    try:
        identifier(value)
    except ValueError:
        _fail('generation_invalid_intake')


_SCHEMA = {
    _G: ('table', f'''CREATE TABLE {_G}(
 generation_id TEXT PRIMARY KEY NOT NULL CHECK({_SHA_CHECK.format('generation_id')}),
 intake_id TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>0),epoch INTEGER NOT NULL CHECK(epoch>=0),
 origin_kind TEXT NOT NULL CHECK(origin_kind IN ('completed_import','reanalysis')),
 origin_job_id TEXT NOT NULL REFERENCES intake_jobs(job_id),
 profile_id TEXT NOT NULL CHECK({_SHA_CHECK.format('profile_id')}),
 context_id TEXT NOT NULL CHECK({_SHA_CHECK.format('context_id')}),
 state TEXT NOT NULL CHECK(state IN ('queued','running','completed','failed','superseded')),
 worker_id TEXT,token_sha256 TEXT CHECK(token_sha256 IS NULL OR ({_SHA_CHECK.format('token_sha256')})),
 lease_until REAL,attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt>=0),
 result_sha256 TEXT CHECK(result_sha256 IS NULL OR ({_SHA_CHECK.format('result_sha256')})),result_json TEXT,
 snapshot_sha256 TEXT CHECK(snapshot_sha256 IS NULL OR ({_SHA_CHECK.format('snapshot_sha256')})),snapshot_json TEXT,
 snapshot_scope TEXT CHECK(snapshot_scope IS NULL OR snapshot_scope='migration_time'),
 synthetic INTEGER NOT NULL CHECK(synthetic IN (0,1)),origin_created_at REAL,origin_completed_at TEXT,
 imported_at TEXT NOT NULL,error_code TEXT,
 UNIQUE(intake_id,epoch),UNIQUE(intake_id,revision,generation_id,epoch),
 FOREIGN KEY(intake_id,revision) REFERENCES intake_revisions(intake_id,revision),
 CHECK(state!='completed' OR (result_json IS NOT NULL AND result_sha256 IS NOT NULL
 AND snapshot_json IS NOT NULL AND snapshot_sha256 IS NOT NULL AND snapshot_scope IS NOT NULL)))'''),
    _H: ('table', f'''CREATE TABLE {_H}(
 intake_id TEXT NOT NULL,revision INTEGER NOT NULL,generation_id TEXT NOT NULL,epoch INTEGER NOT NULL,
 PRIMARY KEY(intake_id,revision),FOREIGN KEY(intake_id,revision,generation_id,epoch)
 REFERENCES {_G}(intake_id,revision,generation_id,epoch))'''),
    _R: ('table', f'''CREATE TABLE {_R}(
 request_id TEXT PRIMARY KEY NOT NULL,request_fingerprint TEXT NOT NULL,receipt_json TEXT NOT NULL,
 intake_id TEXT NOT NULL,revision INTEGER NOT NULL,generation_id TEXT NOT NULL,epoch INTEGER NOT NULL,
 created_at TEXT NOT NULL,FOREIGN KEY(intake_id,revision,generation_id,epoch)
 REFERENCES {_G}(intake_id,revision,generation_id,epoch))'''),
    _E: ('table', f'''CREATE TABLE {_E}(
 event_id INTEGER PRIMARY KEY,generation_id TEXT NOT NULL REFERENCES {_G}(generation_id),
 kind TEXT NOT NULL,details_json TEXT NOT NULL,created_at TEXT NOT NULL)'''),
    _PREFIX+'origin_unique': ('index', f"CREATE UNIQUE INDEX {_PREFIX}origin_unique ON {_G}(origin_job_id) WHERE origin_kind='completed_import'"),
    _PREFIX+'import_event_unique': ('index', f"CREATE UNIQUE INDEX {_PREFIX}import_event_unique ON {_E}(generation_id) WHERE kind='origin_imported'"),
}
for _table in (_G, _R, _E):
    for _action in ('UPDATE', 'DELETE'):
        _name = _table + '_no_' + _action.lower()
        _when = " WHEN OLD.state='completed'" if _table == _G else ''
        _SCHEMA[_name] = ('trigger', f"CREATE TRIGGER {_name} BEFORE {_action} ON {_table}{_when} BEGIN SELECT RAISE(ABORT,'immutable_analysis_history'); END")


def _normal_sql(value):
    return ' '.join(value.strip().rstrip(';').split())


def _schema(con):
    tables = (_G, _H, _R, _E)
    rows = con.execute("SELECT name,type,tbl_name,sql FROM sqlite_master WHERE substr(name,1,?)=? "
                       "OR tbl_name IN (?,?,?,?)", (len(_PREFIX), _PREFIX, *tables)).fetchall()
    if not rows:
        return False
    actual = {}
    for row in rows:
        if row['type'] == 'index' and row['sql'] is None and row['name'].startswith('sqlite_autoindex_'):
            continue
        actual[row['name']] = (row['type'], _normal_sql(row['sql']) if type(row['sql']) is str else None)
    expected = {name: (kind, _normal_sql(sql)) for name, (kind, sql) in _SCHEMA.items()}
    if actual != expected:
        _fail('generation_ledger_schema_mismatch')
    return True


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('generation_invalid_analysis')
        result[key] = value
    return result


def _origin(con, intake_id, expected_revision, expected_sha):
    row = con.execute('SELECT i.intake_id,i.source_id,i.revision,r.fingerprint,r.synthetic,'
        'CASE WHEN length(CAST(r.files_json AS BLOB))<=4194304 THEN r.files_json END AS files_json,'
        'j.job_id,j.state,j.worker_id,j.lease_until,j.attempt,j.created_at,'
        'CASE WHEN typeof(j.token)=\'text\' AND length(CAST(j.token AS BLOB)) BETWEEN 1 AND 4096 THEN j.token END AS token,'
        'length(CAST(j.result_json AS BLOB)) AS result_bytes,'
        'CASE WHEN typeof(j.result_json)=\'text\' AND length(CAST(j.result_json AS BLOB))<=? THEN j.result_json END AS result_json '
        'FROM intakes i LEFT JOIN intake_revisions r ON r.intake_id=i.intake_id AND r.revision=i.revision '
        'LEFT JOIN intake_jobs j ON j.intake_id=i.intake_id AND j.revision=i.revision WHERE i.intake_id=?',
        (MAX_RESULT_BYTES, intake_id)).fetchone()
    if row is None:
        _fail('generation_intake_not_found')
    row = dict(row)
    if row['revision'] != expected_revision:
        _fail('generation_revision_changed')
    if row['state'] != 'completed':
        _fail('generation_analysis_not_completed')
    if row['result_bytes'] is not None and row['result_bytes'] > MAX_RESULT_BYTES:
        _fail('generation_result_limit')
    if type(row['result_json']) is not str or type(row['token']) is not str:
        _fail('generation_invalid_analysis')
    raw = row['result_json'].encode('utf-8')
    if _digest(raw) != expected_sha:
        _fail('generation_result_changed')
    try:
        identifier(row['source_id']); identifier(row['job_id'])
        if type(row['created_at']) not in (int, float) or not math.isfinite(row['created_at']):
            raise ValueError()
        parsed = json.loads(row['result_json'], object_pairs_hook=_unique)
        canonical(parsed)
    except (ValueError, TypeError, OverflowError, RuntimeError):
        _fail('generation_invalid_analysis')
    return row


def _validated(store, row):
    try:
        status, _, context_id, profile_id = validate_retained_analysis(store, row)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError):
        _fail('generation_invalid_analysis')
    if status != 'verified':
        _fail('generation_unbound_analysis')
    return context_id, profile_id


_PARTS = (
    ('intake', 'intakes', ('intake_id','source_id','bundle','revision','status','delegated','deferred','analysis_json'), 'intake_id', True),
    ('questions', 'intake_questions', ('intake_id','question_key','question_json','state','last_revision'), 'question_key', False),
    ('answers', 'intake_answers', ('intake_id','field','value','basis_json','event_id'), 'field', False),
    ('notifications', 'intake_notifications', ('notification_id','intake_id','revision','signature','payload_json'), 'notification_id', False),
    ('notice_state', 'intake_notice_state', ('intake_id','signature'), 'intake_id', False),
)


def _snapshot(con, intake_id):
    empty = {'schema_version': 1, 'scope': 'migration_time', **{key: {} if single else [] for key, _, _, _, single in _PARTS}}
    raw_total = len(canonical(empty).encode('utf-8'))
    stats = []
    for key, table, columns, order, single in _PARTS:
        # Raw byte and structural lower bounds prevent huge values/row counts
        # before SQLite builds any escaped JSON and before Python fetches rows.
        overhead = 2 + sum(len(column) + 3 for column in columns) + len(columns) - 1
        raw = '+'.join(f'COALESCE(length(CAST({column} AS BLOB)),4)' for column in columns)
        count, size = con.execute(f'SELECT count(*),COALESCE(sum({overhead}+{raw}),0) FROM {table} WHERE intake_id=?', (intake_id,)).fetchone()
        if single and count != 1:
            _fail('generation_invalid_snapshot')
        raw_total += size - 2 if single else size + max(0, count - 1)
        stats.append((key, table, columns, order, single, count))
    if raw_total > MAX_SNAPSHOT_BYTES:
        _fail('generation_snapshot_limit')
    encoded_total = len(canonical(empty).encode('utf-8'))
    for key, table, columns, order, single, count in stats:
        pairs = ','.join(f"'{column}',{column}" for column in columns)
        size = con.execute(f'SELECT COALESCE(sum(length(CAST(json_object({pairs}) AS BLOB))),0) FROM {table} WHERE intake_id=?', (intake_id,)).fetchone()[0]
        encoded_total += size - 2 if single else size + max(0, count - 1)
    if encoded_total > MAX_SNAPSHOT_BYTES:
        _fail('generation_snapshot_limit')
    snapshot = dict(empty)
    for key, table, columns, order, single, _ in stats:
        values = [dict(row) for row in con.execute(f'SELECT {",".join(columns)} FROM {table} WHERE intake_id=? ORDER BY {order}', (intake_id,))]
        snapshot[key] = values[0] if single else values
    payload = canonical(snapshot)
    if len(payload.encode('utf-8')) > MAX_SNAPSHOT_BYTES:
        _fail('generation_snapshot_limit')
    return payload


def _completion_time(con, intake_id, job_id):
    where = ("action='intake.analysis_completed' AND subject_id=? AND CASE "
             "WHEN length(CAST(details_json AS BLOB))<=? THEN CASE WHEN json_valid(details_json) "
             "THEN json_extract(details_json,'$.job_id') END END=?")
    count, size = con.execute('SELECT count(*),MAX(length(CAST(created_at AS BLOB))) FROM events WHERE '+where,
                             (intake_id, MAX_RESULT_BYTES, job_id)).fetchone()
    if count != 1:
        return None
    if size is None or size > 256:
        _fail('generation_invalid_completion_time')
    return con.execute('SELECT created_at FROM events WHERE '+where, (intake_id, MAX_RESULT_BYTES, job_id)).fetchone()[0]


_PUBLIC = 'intake_id,revision,generation_id,epoch,origin_job_id,context_id,profile_id,result_sha256,synthetic,snapshot_scope'


def _receipt(row):
    if (type(row['epoch']) is not int or row['epoch'] < 0 or type(row['revision']) is not int or row['revision'] < 1
            or row['synthetic'] not in (0, 1) or row['snapshot_scope'] != 'migration_time'
            or any(not _hash(row[name]) for name in ('generation_id', 'context_id', 'profile_id', 'result_sha256'))):
        _fail('generation_ledger_record_invalid')
    try:
        identifier(row['intake_id']); identifier(row['origin_job_id'])
    except ValueError:
        _fail('generation_ledger_record_invalid')
    basis = {key: row[key] for key in ('origin_job_id','intake_id','revision','profile_id','context_id','result_sha256')}
    if _digest(canonical(basis).encode('utf-8')) != row['generation_id']:
        _fail('generation_ledger_record_invalid')
    return {'schema_version': 1, 'kind': 'intake_analysis_generation_import',
            **{key: row[key] for key in _PUBLIC.split(',') if key != 'synthetic'}, 'synthetic': bool(row['synthetic'])}


def import_completed_generation(store, intake_id, *, expected_revision, expected_result_sha256):
    """Import one current completed V2 PDF origin; never overwrite live state."""
    _intake(intake_id)
    if type(expected_revision) is not int or expected_revision < 1 or not _hash(expected_result_sha256):
        _fail('generation_invalid_expectation')
    try:
        with store.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            row = _origin(con, intake_id, expected_revision, expected_result_sha256)
            context_id, profile_id = _validated(store, row)
            basis = {'origin_job_id': row['job_id'], 'intake_id': intake_id, 'revision': expected_revision,
                     'profile_id': profile_id, 'context_id': context_id, 'result_sha256': expected_result_sha256}
            generation_id = _digest(canonical(basis).encode('utf-8'))
            token_sha = _digest(row['token'].encode('utf-8'))
            present = _schema(con)
            if present:
                old = con.execute(f'SELECT {_PUBLIC},token_sha256,state FROM {_G} WHERE origin_job_id=? AND origin_kind=\'completed_import\'', (row['job_id'],)).fetchone()
                if old is not None:
                    if (old['generation_id'] != generation_id or old['token_sha256'] != token_sha
                            or old['state'] != 'completed' or any(old[key] != value for key, value in basis.items())):
                        _fail('generation_origin_changed')
                    if not con.execute(f'SELECT 1 FROM {_H} WHERE intake_id=? AND revision=?', (intake_id, expected_revision)).fetchone():
                        _fail('generation_ledger_record_invalid')
                    return _receipt(old)
                if con.execute(f'SELECT 1 FROM {_H} WHERE intake_id=? AND revision=?', (intake_id, expected_revision)).fetchone():
                    _fail('generation_origin_changed')
            snapshot = _snapshot(con, intake_id)
            completed_at = _completion_time(con, intake_id, row['job_id'])
            if not present:
                for _, sql in _SCHEMA.values():
                    con.execute(sql)
                _schema(con)
            maximum = con.execute(f'SELECT MAX(epoch) FROM {_G} WHERE intake_id=?', (intake_id,)).fetchone()[0]
            if maximum is not None and maximum >= _INTEGER_MAX:
                _fail('generation_epoch_exhausted')
            epoch = 0 if maximum is None else maximum + 1
            imported_at = utcnow()
            values = {**basis, 'generation_id': generation_id, 'epoch': epoch, 'origin_kind': 'completed_import',
                'state': 'completed', 'worker_id': row['worker_id'], 'token_sha256': token_sha,
                'lease_until': row['lease_until'], 'attempt': row['attempt'], 'result_json': row['result_json'],
                'snapshot_json': snapshot, 'snapshot_sha256': _digest(snapshot.encode('utf-8')),
                'snapshot_scope': 'migration_time', 'synthetic': row['synthetic'],
                'origin_created_at': row['created_at'], 'origin_completed_at': completed_at, 'imported_at': imported_at}
            columns = ','.join(values)
            con.execute(f'INSERT INTO {_G}({columns}) VALUES({",".join("?" for _ in values)})', tuple(values.values()))
            con.execute(f'INSERT INTO {_H} VALUES(?,?,?,?)', (intake_id, expected_revision, generation_id, epoch))
            receipt = _receipt(values)
            con.execute(f'INSERT INTO {_E}(generation_id,kind,details_json,created_at) VALUES(?,\'origin_imported\',?,?)',
                        (generation_id, canonical(receipt), imported_at))
            _validated(store, row)
            return receipt
    except sqlite3.Error:
        _fail('generation_ledger_storage_error')


def generation_history(store, intake_id, *, limit=20, before_epoch=None):
    """Read sanitized immutable metadata; an absent ledger remains absent."""
    _intake(intake_id)
    if (type(limit) is not int or not 1 <= limit <= 100
            or before_epoch is not None and (type(before_epoch) is not int or before_epoch < 0)):
        _fail('generation_invalid_history_limit')
    try:
        with store.connection() as con:
            con.execute('BEGIN')
            if con.execute('SELECT 1 FROM intakes WHERE intake_id=?', (intake_id,)).fetchone() is None:
                _fail('generation_intake_not_found')
            present = _schema(con)
            records = []
            if present:
                query = f'SELECT {_PUBLIC} FROM {_G} WHERE intake_id=? AND state=\'completed\''
                args = [intake_id]
                if before_epoch is not None and before_epoch <= _INTEGER_MAX:
                    query += ' AND epoch<?'; args.append(before_epoch)
                rows = con.execute(query+' ORDER BY epoch DESC LIMIT ?', (*args, limit + 1)).fetchall()
                records = [_receipt(row) for row in rows[:limit]]
                more = len(rows) > limit
            else:
                more = False
            return {'schema_version': 1, 'kind': 'intake_analysis_generation_history', 'intake_id': intake_id,
                    'available': present, 'records': records, 'next_before_epoch': records[-1]['epoch'] if more else None}
    except sqlite3.Error:
        _fail('generation_ledger_storage_error')


def _replay_input(analysis):
    try:
        if not isinstance(analysis, dict):
            raise ValueError()
        payload = canonical(analysis).encode('utf-8')
    except (ValueError, TypeError, OverflowError, RuntimeError, UnicodeError):
        _fail('generation_replay_invalid_analysis')
    if len(payload) > MAX_RESULT_BYTES:
        _fail('generation_replay_analysis_limit')
    try:
        return json.loads(payload)
    except (ValueError, RuntimeError):
        _fail('generation_replay_invalid_analysis')


def _replay_payload(payload, sha, code):
    try:
        if type(payload) is not str or not _hash(sha):
            raise ValueError()
        raw = payload.encode('utf-8')
        if len(raw) > MAX_RESULT_BYTES or _digest(raw) != sha:
            raise ValueError()
        parsed = json.loads(payload, object_pairs_hook=_unique)
        canonical(parsed).encode('utf-8')
        return parsed
    except (ValueError, TypeError, OverflowError, RuntimeError, UnicodeError):
        _fail(code)


def _replay_snapshot(snapshot, row):
    code = 'generation_replay_snapshot_invalid'
    if (type(snapshot) is not dict or set(snapshot) != {'schema_version', 'scope'} | {part[0] for part in _PARTS}
            or type(snapshot['schema_version']) is not int or snapshot['schema_version'] != 1
            or snapshot['scope'] != 'migration_time'):
        _fail(code)
    for key, _, columns, _, single in _PARTS:
        values = [snapshot[key]] if single else snapshot[key]
        if type(values) is not list:
            _fail(code)
        for value in values:
            if type(value) is not dict or set(value) != set(columns) or value['intake_id'] != row['intake_id']:
                _fail(code)
    intake = snapshot['intake']
    if (type(intake['revision']) is not int or intake['revision'] != row['revision']
            or intake['source_id'] != row['source_id']):
        _fail(code)


def replay_imported_completion(store, job_id, token, analysis):
    """Read an exact imported completion under its retained profile, or None.

    Only an absent ledger/import origin permits the caller's legacy fallback.
    This function never prepares documents or changes any current state.
    """
    submitted = _replay_input(analysis)
    try:
        identifier(job_id)
    except ValueError:
        _fail('generation_replay_invalid_job')
    token_sha = None
    if type(token) is str:
        try:
            raw_token = token.encode('utf-8')
            if 0 < len(raw_token) <= 4096:
                token_sha = _digest(raw_token)
        except UnicodeError:
            pass
    try:
        with store.connection() as con:
            con.execute('BEGIN')
            if not _schema(con):
                return None
            public = ','.join('g.' + column for column in _PUBLIC.split(','))
            row = con.execute(f'SELECT {public},g.state,g.token_sha256,g.snapshot_sha256,g.origin_created_at,'
                'CASE WHEN typeof(g.result_json)=\'text\' AND length(CAST(g.result_json AS BLOB))<=? THEN g.result_json END AS result_json,'
                'CASE WHEN typeof(g.snapshot_json)=\'text\' AND length(CAST(g.snapshot_json AS BLOB))<=? THEN g.snapshot_json END AS snapshot_json,'
                'j.job_id AS legacy_job_id,j.intake_id AS legacy_intake_id,j.revision AS legacy_revision,j.state AS legacy_state,'
                'CASE WHEN typeof(j.created_at) IN (\'integer\',\'real\') THEN j.created_at END AS legacy_created_at,'
                'CASE WHEN typeof(j.result_json)=\'text\' AND length(CAST(j.result_json AS BLOB))<=? THEN j.result_json END AS legacy_result_json,'
                'i.intake_id AS parent_intake_id,'
                'CASE WHEN typeof(i.source_id)=\'text\' AND length(CAST(i.source_id AS BLOB))<=150 THEN i.source_id END AS source_id,'
                'CASE WHEN length(CAST(r.files_json AS BLOB))<=4194304 THEN r.files_json END AS files_json,'
                'CASE WHEN length(CAST(r.fingerprint AS BLOB))=64 THEN r.fingerprint END AS fingerprint,'
                'r.synthetic AS revision_synthetic '
                f'FROM {_G} g LEFT JOIN intake_jobs j ON j.job_id=g.origin_job_id '
                'LEFT JOIN intake_revisions r ON r.intake_id=g.intake_id AND r.revision=g.revision '
                'LEFT JOIN intakes i ON i.intake_id=g.intake_id '
                "WHERE g.origin_job_id=? AND g.origin_kind='completed_import'",
                (MAX_RESULT_BYTES, MAX_SNAPSHOT_BYTES, MAX_RESULT_BYTES, job_id)).fetchone()
            if row is None:
                return None
            row = dict(row)
    except sqlite3.Error:
        _fail('generation_replay_storage_error')
    try:
        _receipt(row)
    except ValueError:
        _fail('generation_replay_origin_invalid')
    if (row['state'] != 'completed' or row['legacy_state'] != 'completed'
            or row['legacy_job_id'] != job_id or row['legacy_intake_id'] != row['intake_id']
            or row['legacy_revision'] != row['revision'] or row['parent_intake_id'] != row['intake_id']
            or type(row['legacy_created_at']) not in (int, float) or not math.isfinite(row['legacy_created_at'])
            or type(row['origin_created_at']) not in (int, float) or not math.isfinite(row['origin_created_at'])
            or row['legacy_created_at'] != row['origin_created_at']
            or row['revision_synthetic'] not in (0, 1) or row['revision_synthetic'] != row['synthetic']):
        _fail('generation_replay_origin_invalid')
    if token_sha is None or not _hash(row['token_sha256']) or not hmac.compare_digest(token_sha, row['token_sha256']):
        _fail('generation_replay_token_mismatch')
    result = _replay_payload(row['result_json'], row['result_sha256'], 'generation_replay_result_invalid')
    _replay_payload(row['legacy_result_json'], row['result_sha256'], 'generation_replay_origin_invalid')
    snapshot = _replay_payload(row['snapshot_json'], row['snapshot_sha256'], 'generation_replay_snapshot_invalid')
    _replay_snapshot(snapshot, row)
    if (type(result) is not dict or set(result) != {'submission', 'summary'}
            or type(result['summary']) is not dict
            or canonical(result['submission']) != canonical(submitted)):
        _fail('generation_replay_submission_mismatch')
    retained = {**row, 'synthetic': row['revision_synthetic']}
    try:
        context_id, profile_id = _validated(store, retained)
    except ValueError:
        _fail('generation_replay_binding_invalid')
    if context_id != row['context_id'] or profile_id != row['profile_id']:
        _fail('generation_replay_binding_invalid')
    return json.loads(canonical(result['summary']))
