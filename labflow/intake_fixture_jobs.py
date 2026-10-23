"""Fixture-only requests, immutable intake bindings and conservative ownership.

The readiness reader never initializes storage. Analysis jobs and physical
workflow cases are not created, resumed, reviewed or completed by this module.
"""
import hashlib
import json
import math
import re
import uuid

from .active_intake import timestamp
from .store import canonical, identifier


RECIPE_ID = 'conducted_sensor_fixture_v1'
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_CODE = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')
_TERMINAL = {'completed', 'failed', 'uncertain', 'superseded'}


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate_json_key')
        value[key] = item
    return value


def _load(value, limit=4 * 1024 * 1024):
    if not isinstance(value, (str, bytes)) or len(value.encode('utf-8') if isinstance(value, str) else value) > limit:
        raise ValueError('invalid_fixture_json')
    result = json.loads(value, object_pairs_hook=_unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
    canonical(result)  # Reject JSON numbers that overflow to infinity.
    return result


def _hash(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _delegation(con, intake_id):
    for event in con.execute("SELECT details_json FROM events WHERE action='intake.user_response' "
                             'AND subject_id=? ORDER BY event_id DESC', (intake_id,)):
        details = _load(event['details_json'])
        if details.get('action') == 'defer':
            return None
        if details.get('action') != 'proceed':
            continue
        event_id = details.get('event_id')
        row = con.execute('SELECT request_json,result_json FROM intake_responses WHERE event_id=?', (event_id,)).fetchone()
        if row is None:
            return None
        request, result = _load(row['request_json']), _load(row['result_json'])
        if (request.get('action') == 'proceed' and request.get('intake_id') in (None, intake_id)
                and result.get('status') == 'recorded' and result.get('action') == 'proceed'
                and result.get('intake_id') == intake_id):
            return event_id
        return None
    return None


def _readiness(con, intake_id):
    row = con.execute('SELECT i.*,r.fingerprint,r.synthetic FROM intakes i JOIN intake_revisions r '
                      'ON r.intake_id=i.intake_id AND r.revision=i.revision WHERE i.intake_id=?', (intake_id,)).fetchone()
    if row is None:
        raise ValueError('fixture_intake_not_found')
    reasons = []
    analysis = _load(row['analysis_json']) if row['analysis_json'] else None
    if row['status'] != 'analyzed' or not isinstance(analysis, dict):
        reasons.append('analysis_not_ready')
    elif (analysis.get('questions') != [] or analysis.get('unread_documents') != []
          or analysis.get('next_action') != 'prepare_plan'):
        reasons.append('preparation_not_ready')
    if row['delegated'] != 1:
        reasons.append('delegation_missing')
    if row['deferred'] != 0:
        reasons.append('intake_deferred')
    delegation = _delegation(con, intake_id)
    if delegation is None:
        reasons.append('delegation_evidence_missing')
    facts = analysis.get('facts', {}) if isinstance(analysis, dict) else {}
    model_fact = facts.get('model', {}) if isinstance(facts, dict) else {}
    model = model_fact.get('value') if isinstance(model_fact, dict) else None
    if not isinstance(model, str) or not model.strip() or len(model) > 4000:
        model = None
        reasons.append('model_missing')
    for field in ('product_type', 'market', 'purpose'):
        fact = facts.get(field) if isinstance(facts, dict) else None
        if not isinstance(fact, dict) or not isinstance(fact.get('value'), str) or not fact['value'].strip():
            reasons.append('required_facts_missing')
            break
    if not _HASH.fullmatch(row['fingerprint']) or row['synthetic'] not in (0, 1):
        reasons.append('revision_invalid')
    answers = [dict(answer) for answer in con.execute(
        'SELECT field,value,basis_json,event_id FROM intake_answers WHERE intake_id=? ORDER BY field', (intake_id,))]
    basis = {'intake_id': intake_id, 'revision': row['revision'], 'revision_fingerprint': row['fingerprint'],
        'analysis': analysis, 'answers': answers, 'status': row['status'], 'delegated': row['delegated'],
        'deferred': row['deferred'], 'delegation_event_id': delegation, 'source_synthetic': row['synthetic']}
    return {'intake_id': intake_id, 'revision': row['revision'], 'revision_fingerprint': row['fingerprint'],
        'readiness_fingerprint': _hash(basis), 'source_synthetic': bool(row['synthetic']),
        'delegation_event_id': delegation, 'model': model, 'ready': not reasons, 'reason_codes': sorted(set(reasons))}


def fixture_readiness(store, intake_id):
    """Read current preparation in one DB snapshot without starting any work."""
    identifier(intake_id)
    with store.connection() as con:
        # Read models may already hold a read transaction on this connection.
        if not con.in_transaction:
            con.execute('BEGIN')
        return _readiness(con, intake_id)


def _record(row):
    result = dict(row)
    result['settings'] = _load(result['settings_json'])
    result['source_synthetic'] = bool(result['source_synthetic'])
    return result


def _row(con, request_id):
    row = con.execute('SELECT * FROM intake_fixture_jobs WHERE request_id=?', (request_id,)).fetchone()
    if row is None:
        raise ValueError('fixture_request_not_found')
    return row


def _settings(recipe_id, settings):
    if recipe_id != RECIPE_ID or type(settings) is not dict or set(settings) != {'power_dbm'}:
        raise ValueError('fixture_selection_unsupported')
    power = settings['power_dbm']
    if type(power) not in (int, float) or not math.isfinite(power) or not -30 <= power <= 20:
        raise ValueError('fixture_selection_unsupported')
    return {'power_dbm': power}


def _verify_sources(store, con, intake_id, revision):
    value = con.execute('SELECT files_json FROM intake_revisions WHERE intake_id=? AND revision=?',
                        (intake_id, revision)).fetchone()
    if value is None:
        raise ValueError('fixture_revision_missing')
    files = _load(value['files_json'])
    if not isinstance(files, list) or not files:
        raise ValueError('fixture_revision_invalid')
    for item in files:
        store.verify_blob(item['sha256'])


def request_fixture_job(store, request_id, intake_id, *, expected_revision,
                        expected_readiness_fingerprint, recipe_id, settings):
    identifier(request_id)
    identifier(intake_id)
    if type(expected_revision) is not int or expected_revision < 1 or not isinstance(expected_readiness_fingerprint, str) \
            or not _HASH.fullmatch(expected_readiness_fingerprint):
        raise ValueError('fixture_snapshot_invalid')
    settings = _settings(recipe_id, settings)
    body = {'intake_id': intake_id, 'revision': expected_revision,
        'readiness_fingerprint': expected_readiness_fingerprint, 'recipe_id': recipe_id, 'settings': settings}
    fingerprint = _hash(body)
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        old = con.execute('SELECT * FROM intake_fixture_jobs WHERE request_id=?', (request_id,)).fetchone()
        if old:
            if old['request_fingerprint'] != fingerprint:
                raise ValueError('fixture_request_conflict')
            return _record(old)
        ready = _readiness(con, intake_id)
        if (not ready['ready'] or ready['revision'] != expected_revision
                or ready['readiness_fingerprint'] != expected_readiness_fingerprint):
            raise ValueError('fixture_preparation_changed')
        if ready['model'] != 'SM-A176U':
            raise ValueError('fixture_model_unsupported')
        _verify_sources(store, con, intake_id, expected_revision)
        now = timestamp()
        con.execute('INSERT INTO intake_fixture_jobs(request_id,intake_id,revision,request_fingerprint,'
            'readiness_fingerprint,revision_fingerprint,delegation_event_id,recipe_id,settings_json,model,'
            'source_synthetic,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (request_id, intake_id, expected_revision, fingerprint, ready['readiness_fingerprint'],
             ready['revision_fingerprint'], ready['delegation_event_id'], recipe_id, canonical(settings),
             ready['model'], int(ready['source_synthetic']), 'queued', now, now))
        store.event(con, 'intake.fixture_requested', intake_id, {'request_id': request_id, 'revision': expected_revision})
        return _record(_row(con, request_id))


def _current(con, row):
    ready = _readiness(con, row['intake_id'])
    return (ready['ready'] and ready['revision'] == row['revision']
            and ready['readiness_fingerprint'] == row['readiness_fingerprint'])


def claim_fixture_job(store, worker_id, *, lease_seconds=120, now=None):
    identifier(worker_id)
    timestamp(lease_seconds)
    if not 0 < lease_seconds <= 3600:
        raise ValueError('fixture_lease_invalid')
    if now is not None:
        timestamp(now)
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        acquired_at = timestamp(now)
        expired = con.execute("SELECT request_id,intake_id FROM intake_fixture_jobs WHERE state='running' AND lease_until<=?",
                              (acquired_at,)).fetchall()
        for row in expired:
            con.execute("UPDATE intake_fixture_jobs SET state='uncertain',error_code='lease_expired',updated_at=? WHERE request_id=?",
                        (acquired_at, row['request_id']))
            store.event(con, 'intake.fixture_uncertain', row['intake_id'], {'request_id': row['request_id'], 'code': 'lease_expired'})
        pending = con.execute("SELECT * FROM intake_fixture_jobs WHERE state='queued' ORDER BY created_at,request_id LIMIT 100").fetchall()
        for row in pending:
            if not _current(con, row):
                con.execute("UPDATE intake_fixture_jobs SET state='superseded',error_code='preparation_changed',updated_at=? WHERE request_id=?",
                            (timestamp(now), row['request_id']))
                store.event(con, 'intake.fixture_superseded', row['intake_id'], {'request_id': row['request_id']})
                continue
            try:
                _verify_sources(store, con, row['intake_id'], row['revision'])
            except (ValueError, OSError, KeyError, TypeError):
                con.execute("UPDATE intake_fixture_jobs SET state='failed',error_code='source_evidence_invalid',updated_at=? WHERE request_id=?",
                            (timestamp(now), row['request_id']))
                store.event(con, 'intake.fixture_failed', row['intake_id'], {'request_id': row['request_id'], 'code': 'source_evidence_invalid'})
                continue
            claimed_at = timestamp(now)
            con.execute("UPDATE intake_fixture_jobs SET state='running',worker_id=?,token=?,lease_until=?,run_id=?,runtime_instance_id=?,updated_at=? WHERE request_id=?",
                (worker_id, uuid.uuid4().hex, claimed_at + lease_seconds, uuid.uuid4().hex,
                 uuid.uuid4().hex, claimed_at, row['request_id']))
            store.event(con, 'intake.fixture_claimed', row['intake_id'], {'request_id': row['request_id'], 'worker_id': worker_id})
            return _record(_row(con, row['request_id']))
        return None


def fixture_lease_current(store, request_id, token, *, now=None):
    identifier(request_id)
    identifier(token)
    if now is not None:
        timestamp(now)
    with store.connection() as con:
        if not con.in_transaction:
            con.execute('BEGIN')
        row = _row(con, request_id)
        if row['state'] != 'running' or row['token'] != token or row['lease_until'] <= timestamp(now):
            return False
        current = _current(con, row)
        return bool(current and row['lease_until'] > timestamp(now))


def _validated_evidence(store, report, artifacts):
    from .virtual_fleet.journal import read_operator_journal
    from .virtual_fleet_server import _harness_payload
    if type(report) is not dict:
        raise ValueError('fixture_report_invalid')
    report = _load(_harness_payload(report))['report']
    if type(artifacts) is not list or len(artifacts) != 2:
        raise ValueError('fixture_artifacts_invalid')
    artifacts = _load(canonical(artifacts))
    saved, kinds, journal = [], set(), None
    for item in artifacts:
        if type(item) is not dict or set(item) != {'kind', 'artifact_id', 'sha256', 'bytes'}:
            raise ValueError('fixture_artifact_invalid')
        kind, sha = item['kind'], item['sha256']
        if (kind not in {'result', 'operator_journal'} or kind in kinds or not isinstance(sha, str)
                or not _HASH.fullmatch(sha) or item['artifact_id'] != 'blob:' + sha
                or type(item['bytes']) is not int or item['bytes'] < 1):
            raise ValueError('fixture_artifact_invalid')
        maximum = 256 * 1024 if kind == 'result' else 32 * 1024 * 1024
        if item['bytes'] > maximum:
            raise ValueError('fixture_artifact_limit')
        path = store.verify_blob(sha)
        if path.stat().st_size != item['bytes'] or not store.evidence_is_synthetic(sha):
            raise ValueError('fixture_artifact_provenance')
        if kind == 'result':
            if canonical(_load(path.read_bytes(), maximum)) != canonical(report):
                raise ValueError('fixture_result_mismatch')
        else:
            journal = read_operator_journal(path)
        kinds.add(kind)
        saved.append(dict(item))
    if (not journal['complete'] or journal['unresolved_request_ids'] or report['unresolved_request_ids']
            or journal['header']['run_id'] != report['run_id']
            or journal['header']['runtime_instance_id'] != report['runtime_instance_id']):
        raise ValueError('fixture_journal_incomplete_or_mismatched')
    known_refs = {event['event_id'] for event in journal['events']} | {'artifact:operator_events'}
    refs = report['evidence']['measurement_refs'] + report['assessment']['evidence_refs'] + report['cleanup']['evidence_refs']
    if report['evidence']['operator_transcript_ref'] != 'artifact:operator_events' or any(ref not in known_refs for ref in refs):
        raise ValueError('fixture_reference_unknown')
    return {'report': report, 'artifacts': sorted(saved, key=lambda item: item['kind'])}


def complete_fixture_job(store, request_id, token, report, artifacts, *, now=None):
    identifier(request_id)
    identifier(token)
    if now is not None:
        timestamp(now)
    result = _validated_evidence(store, report, artifacts)
    report = result['report']
    serialized = canonical(result)
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        row = _row(con, request_id)
        if (row['token'] != token or report['run_id'] != row['run_id']
                or report['runtime_instance_id'] != row['runtime_instance_id']):
            raise ValueError('fixture_owner_or_identity_mismatch')
        if row['state'] in _TERMINAL:
            if row['result_json'] == serialized:
                return _record(row)
            raise ValueError('fixture_terminal_immutable')
        if row['state'] != 'running':
            raise ValueError('fixture_lease_lost')
        state, code = 'completed', None
        recorded_at = timestamp(now)
        if row['lease_until'] <= recorded_at:
            state, code = 'uncertain', 'lease_expired'
        else:
            current = _current(con, row)
            recorded_at = timestamp(now)
            if row['lease_until'] <= recorded_at:
                state, code = 'uncertain', 'lease_expired'
            elif not current:
                state, code = 'uncertain', 'preparation_changed'
            elif report['termination']['reason'] == 'runtime_mutation_uncertain':
                state, code = 'uncertain', 'runtime_mutation_uncertain'
        con.execute('UPDATE intake_fixture_jobs SET state=?,result_json=?,error_code=?,updated_at=? WHERE request_id=?',
                    (state, serialized, code, recorded_at, request_id))
        store.event(con, 'intake.fixture_' + state, row['intake_id'], {'request_id': request_id, 'code': code})
        return _record(_row(con, request_id))


def fail_fixture_job(store, request_id, token, code, *, dispatched=False, now=None):
    identifier(request_id)
    identifier(token)
    if type(dispatched) is not bool or not isinstance(code, str) or not _CODE.fullmatch(code):
        raise ValueError('fixture_failure_invalid')
    if now is not None:
        timestamp(now)
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE')
        row = _row(con, request_id)
        if row['token'] != token:
            raise ValueError('fixture_lease_lost')
        if row['state'] in _TERMINAL:
            return _record(row)
        if row['state'] != 'running':
            raise ValueError('fixture_lease_lost')
        state = 'uncertain' if dispatched or row['lease_until'] <= timestamp(now) else 'failed'
        con.execute('UPDATE intake_fixture_jobs SET state=?,error_code=?,updated_at=? WHERE request_id=?',
                    (state, code, timestamp(now), request_id))
        store.event(con, 'intake.fixture_' + state, row['intake_id'], {'request_id': request_id, 'code': code})
        return _record(_row(con, request_id))
