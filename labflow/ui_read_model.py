"""Read the existing intake contract without initializing or migrating a store."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sqlite3

from .active_intake import intake_status
from .intake_jobs import notifications
from .virtual_fleet_server import _harness_payload

try:
    from .intake_fixture_jobs import fixture_readiness
except ModuleNotFoundError as exc:
    if exc.name != __package__ + '.intake_fixture_jobs':
        raise
    fixture_readiness = None

_HASH = re.compile(r'[a-f0-9]{64}\Z')
_CODE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z')


def _text(value, maximum=128):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError('invalid_fixture_text')
    value.encode('utf-8')
    return value


def _hash(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ValueError('invalid_fixture_hash')
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_fixture_key')
        result[key] = value
    return result


def _public_fixture_record(row, revisions, current_revision, readiness_fingerprint):
    revision = row['revision']
    if type(revision) is not int or revision not in revisions or revision > current_revision:
        raise ValueError('invalid_fixture_revision')
    source = revisions[revision]
    if (row['revision_fingerprint'] != source['fingerprint']
            or row['source_synthetic'] not in (0, 1)
            or row['source_synthetic'] != source['synthetic']):
        raise ValueError('invalid_fixture_source')
    _text(row['request_id'], 150)
    if not _IDENTIFIER.fullmatch(row['request_id']):
        raise ValueError('invalid_fixture_request_id')
    _text(row['recipe_id'])
    _hash(row['readiness_fingerprint'])
    if row['state'] not in {'queued', 'running', 'completed', 'failed', 'uncertain', 'superseded'}:
        raise ValueError('invalid_fixture_state')
    run_id, instance_id = row['run_id'], row['runtime_instance_id']
    if (run_id is None) != (instance_id is None):
        raise ValueError('invalid_fixture_identity')
    if run_id is not None:
        _text(run_id)
        _text(instance_id)
    if row['state'] in {'running', 'completed', 'uncertain'} and run_id is None:
        raise ValueError('missing_fixture_identity')
    if row['error_code'] is not None and (type(row['error_code']) is not str or not _CODE.fullmatch(row['error_code'])):
        raise ValueError('invalid_fixture_error')
    report = None
    if row['result_json'] is not None:
        raw = row['result_json']
        if type(raw) is not str or len(raw.encode('utf-8')) > 280 * 1024:
            raise ValueError('fixture_result_too_large')
        result = json.loads(raw, object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_fixture_json')))
        if type(result) is not dict or set(result) != {'report', 'artifacts'}:
            raise ValueError('invalid_fixture_result')
        report = json.loads(_harness_payload(result['report']))['report']
        if (report is None or report['run_id'] != run_id or report['runtime_instance_id'] != instance_id
                or row['state'] in {'queued', 'running'}):
            raise ValueError('invalid_fixture_report_binding')
        artifacts = result['artifacts']
        if type(artifacts) is not list or len(artifacts) != 2:
            raise ValueError('invalid_fixture_artifacts')
        kinds = set()
        for artifact in artifacts:
            if type(artifact) is not dict or set(artifact) != {'kind', 'artifact_id', 'sha256', 'bytes'}:
                raise ValueError('invalid_fixture_artifact')
            kind = artifact['kind']
            if type(kind) is not str or kind not in {'result', 'operator_journal'} or kind in kinds:
                raise ValueError('invalid_fixture_artifact_kind')
            kinds.add(kind)
            if artifact['artifact_id'] != 'blob:' + _hash(artifact['sha256']):
                raise ValueError('invalid_fixture_artifact_identity')
            if type(artifact['bytes']) is not int or not 0 <= artifact['bytes'] <= 9007199254740991:
                raise ValueError('invalid_fixture_artifact_size')
    if row['state'] == 'completed' and report is None:
        raise ValueError('missing_fixture_report')
    return dict(request_id=row['request_id'], intake_id=row['intake_id'], revision=revision,
                readiness_fingerprint=row['readiness_fingerprint'], recipe_id=row['recipe_id'],
                run_id=run_id, runtime_instance_id=instance_id, state=row['state'],
                source_current=revision == current_revision and row['readiness_fingerprint'] == readiness_fingerprint,
                source_synthetic=bool(row['source_synthetic']), synthetic=True, hardware_verified=False,
                ai_model_called=False, resumable=False, case_id=None, plan_id=None,
                error_code=row['error_code'], report=report)


class ReadModelError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _SnapshotStore:
    """Only the connection interface required by the pure service readers."""
    def __init__(self, connection):
        self._connection = connection

    @contextmanager
    def connection(self):
        yield self._connection


class IntakeReadModel:
    def __init__(self, workspace):
        self.database = Path(workspace).resolve() / 'lab.sqlite3'

    def fixture_runs(self, intake_id):
        """One pure read transaction; no queue claim, blob resolver or evaluator."""
        if not self.database.is_file():
            raise ReadModelError('store_missing')
        con = None
        try:
            con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            intake = con.execute('SELECT revision FROM intakes WHERE intake_id=?', (intake_id,)).fetchone()
            if intake is None:
                raise ReadModelError('intake_not_found')
            revision = intake['revision']
            if type(revision) is not int or revision < 1:
                raise ValueError('invalid_current_revision')
            payload = dict(schema_version=1, intake_id=intake_id, current_revision=revision,
                           storage_available=False, records=[], more_available=False)
            table = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intake_fixture_jobs'").fetchone()
            if table is None or fixture_readiness is None:
                return payload
            readiness = fixture_readiness(_SnapshotStore(con), intake_id)
            if readiness['intake_id'] != intake_id or readiness['revision'] != revision:
                raise ValueError('invalid_current_readiness')
            fingerprint = _hash(readiness['readiness_fingerprint'])
            revisions = {r['revision']: r for r in con.execute(
                'SELECT revision,fingerprint,synthetic FROM intake_revisions WHERE intake_id=?', (intake_id,))}
            rows = con.execute('''SELECT request_id,intake_id,revision,readiness_fingerprint,
                revision_fingerprint,recipe_id,run_id,runtime_instance_id,state,source_synthetic,
                error_code,result_json FROM intake_fixture_jobs WHERE intake_id=?
                ORDER BY created_at DESC,request_id DESC LIMIT 21''', (intake_id,)).fetchall()
            payload.update(storage_available=True, more_available=len(rows) > 20,
                           records=[_public_fixture_record(row, revisions, revision, fingerprint) for row in rows[:20]])
            return payload
        except sqlite3.Error as exc:
            raise ReadModelError('store_unavailable') from exc
        except (ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError, OverflowError) as exc:
            raise ReadModelError('state_invalid') from exc
        finally:
            if con is not None:
                con.close()

    def snapshot(self, intake_id=None):
        if not self.database.is_file():
            raise ReadModelError('store_missing')
        con = None
        try:
            con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            store = _SnapshotStore(con)
            records = intake_status(store, intake_id)
            notices = notifications(store)
            result = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat()}
            if intake_id is None:
                result['intakes'] = records
            else:
                result['intake'] = records
                notices = [n for n in notices if n['intake_id'] == intake_id]
            result['notifications'] = notices
            return result
        except sqlite3.Error as exc:
            raise ReadModelError('store_unavailable') from exc
        except ValueError as exc:
            # Service readers distinguish a missing ID before decoding its state.
            code = 'intake_not_found' if str(exc) == 'Unknown intake' else 'state_invalid'
            raise ReadModelError(code) from exc
        except (TypeError, KeyError, IndexError) as exc:
            raise ReadModelError('state_invalid') from exc
        finally:
            if con is not None:
                con.close()
