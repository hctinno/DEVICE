"""Bounded intake-to-fixture bridge; never retries a new runtime or changes analysis jobs."""
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import stat

from .store import canonical, identifier
from .virtual_fleet.journal import read_operator_journal


_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,149}\Z')
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_REPORT_LIMIT = 256 * 1024
_JOURNAL_LIMIT = 32 * 1024 * 1024
_REQUEST_FIELDS = {'request_id', 'intake_id', 'revision', 'readiness_fingerprint',
                   'recipe_id', 'settings', 'model', 'source_synthetic'}
_REASONS = {'policy_stop', 'supervisor_stop', 'decision_budget', 'request_budget', 'tick_budget',
            'wall_deadline', 'policy_error', 'invalid_proposal', 'runtime_error',
            'runtime_mutation_uncertain', 'evidence_error'}


class _Failure(ValueError):
    def __init__(self, code):
        self.code = code


def _queue_api():
    return importlib.import_module('.intake_fixture_jobs', __package__)


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise _Failure('identity_invalid')
    return value


def _record(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        raise _Failure('report_invalid')


def _natural(value):
    return type(value) is int and 0 <= value <= 9007199254740991


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Failure('duplicate_json_key')
        result[key] = value
    return result


def _constant(value):
    raise _Failure('nonfinite_json')


def _json_copy(value):
    def walk(item, depth=0):
        if depth > 32:
            raise _Failure('json_depth')
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise _Failure('json_key')
            return {key: walk(child, depth+1) for key, child in item.items()}
        if type(item) is list:
            return [walk(child, depth+1) for child in item]
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        raise _Failure('json_type')
    result = walk(value)
    encoded = canonical(result).encode('utf-8')
    if len(encoded) > _REPORT_LIMIT:
        raise _Failure('json_limit')
    return json.loads(encoded)


def _refs(value):
    if type(value) is not list or len(value) > 4096:
        raise _Failure('references_invalid')
    for item in value:
        _id(item)


def _public_report(value, job):
    value = _json_copy(value)
    _record(value, 'schema_version kind run_id runtime_instance_id synthetic hardware_verified ai_model_called policy termination task_outcome cleanup usage evidence unresolved_request_ids assessment')
    if (type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'virtual_fleet_harness_result'
            or value['run_id'] != job['run_id'] or value['runtime_instance_id'] != job['runtime_instance_id']
            or value['synthetic'] is not True or value['hardware_verified'] is not False
            or value['ai_model_called'] is not False or value['task_outcome'] != 'not_assessed'):
        raise _Failure('report_identity_or_provenance')
    _record(value['policy'], 'kind id')
    if value['policy']['kind'] != 'fixture':
        raise _Failure('report_policy')
    _id(value['policy']['id'])
    _record(value['termination'], 'reason policy_claim')
    reason, claim = value['termination']['reason'], value['termination']['policy_claim']
    if type(reason) is not str or reason not in _REASONS:
        raise _Failure('report_termination')
    if (reason == 'policy_stop' and (type(claim) is not str or claim not in {'completed', 'blocked', 'unsupported', 'failed'})) or (reason != 'policy_stop' and claim is not None):
        raise _Failure('report_claim')
    _record(value['cleanup'], 'status evidence_refs')
    if value['cleanup']['status'] != 'not_assessed':
        raise _Failure('report_cleanup')
    _refs(value['cleanup']['evidence_refs'])
    _record(value['usage'], 'decisions logical_requests transport_retries tick_delta reserved_ticks elapsed_ms')
    for key, quantity in value['usage'].items():
        if key == 'elapsed_ms':
            if not _finite(quantity) or quantity < 0:
                raise _Failure('report_usage')
        elif not _natural(quantity):
            raise _Failure('report_usage')
    _record(value['evidence'], 'measurement_refs operator_transcript_ref')
    _refs(value['evidence']['measurement_refs'])
    if value['evidence']['operator_transcript_ref'] != 'artifact:operator_events':
        raise _Failure('report_transcript')
    _refs(value['unresolved_request_ids'])
    _record(value['assessment'], 'status verdict evaluator_id evidence_refs summary_code')
    assessment = value['assessment']
    if type(assessment['status']) is not str or assessment['status'] not in {'not_assessed', 'completed', 'failed'}:
        raise _Failure('report_assessment')
    if assessment['status'] == 'completed':
        if type(assessment['verdict']) is not str or assessment['verdict'] not in {'pass', 'fail', 'inconclusive'}:
            raise _Failure('report_assessment')
    elif assessment['verdict'] is not None:
        raise _Failure('report_assessment')
    for key in ('evaluator_id', 'summary_code'):
        if assessment[key] is not None:
            _id(assessment[key])
    _refs(assessment['evidence_refs'])
    if (reason in {'runtime_mutation_uncertain', 'evidence_error'} or value['unresolved_request_ids']
            or value['usage']['reserved_ticks']):
        raise _Failure('execution_unresolved')
    return value


def _plain(value):
    path = Path(value).absolute()
    if str(path).startswith(('\\\\', '//')):
        raise _Failure('network_path_forbidden')
    for current in (path, *path.parents):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
            raise _Failure('linked_path_forbidden')
    return path.resolve()


def _claim(job):
    if type(job) is not dict:
        raise _Failure('claim_invalid')
    for name in ('request_id', 'intake_id', 'run_id', 'runtime_instance_id', 'recipe_id'):
        _id(job.get(name))
    if len(job['run_id']) > 128 or len(job['runtime_instance_id']) > 128:
        raise _Failure('claim_invalid')
    if (type(job.get('revision')) is not int or job['revision'] < 1
            or type(job.get('token')) is not str or not job['token'] or len(job['token']) > 4096
            or not _finite(job.get('lease_until')) or type(job.get('source_synthetic')) is not bool
            or type(job.get('model')) is not str or not job['model'].strip()
            or type(job.get('readiness_fingerprint')) is not str
            or not _SHA.fullmatch(job['readiness_fingerprint']) or type(job.get('settings')) is not dict):
        raise _Failure('claim_invalid')
    return _json_copy({key: job[key] for key in _REQUEST_FIELDS})


def _folder(root, job):
    binding = canonical([job['request_id'], job['run_id']]).encode('utf-8')
    target = root/('run-'+hashlib.sha256(binding).hexdigest())
    # Include the final filenames and UTF-16 units in the Windows preflight.
    # Do this before creating directories or entering the adapter/bootstrap.
    if os.name == 'nt' and any(len(str(target/name).encode('utf-16-le'))//2 >= 260 for name in
            ('public-result.json', 'operator/events.jsonl', 'private/author.json',
             'private-manifest.json', 'failure.json')):
        raise _Failure('output_path_too_long')
    try:
        target = _plain(target)
        if target.parent != root:
            raise _Failure('output_path_invalid')
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise _Failure('output_path_unavailable') from None
    if target.exists():
        raise _Failure('output_exists')
    return target


def _file(record, expected, limit):
    _record(record, 'kind path sha256 bytes')
    if (type(record['path']) is not str and not isinstance(record['path'], Path)):
        raise _Failure('artifact_path')
    path = _plain(record['path'])
    if path != _plain(expected) or not path.is_file():
        raise _Failure('artifact_path')
    if (type(record['sha256']) is not str or not _SHA.fullmatch(record['sha256'])
            or type(record['bytes']) is not int or not 0 < record['bytes'] <= limit):
        raise _Failure('artifact_metadata')
    with path.open('rb') as stream:
        data = stream.read(limit+1)
    if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
        raise _Failure('artifact_hash_or_size')
    return path, data


def _validated(value, folder, job):
    _record(value, 'report artifacts')
    report = _public_report(value['report'], job)
    if type(value['artifacts']) is not list or len(value['artifacts']) != 2:
        raise _Failure('artifact_set')
    selected = {}
    for item in value['artifacts']:
        if type(item) is not dict or type(item.get('kind')) is not str or item['kind'] in selected:
            raise _Failure('artifact_set')
        _record(item, 'kind path sha256 bytes')
        # Freeze the returned descriptor before any file I/O or host callback.
        # Hash/size checks through publication must use this original snapshot.
        descriptor = dict(item)
        if isinstance(descriptor['path'], Path):
            descriptor['path'] = str(descriptor['path'])
        selected[descriptor['kind']] = descriptor
    if set(selected) != {'result', 'operator_journal'}:
        raise _Failure('artifact_set')
    result_path, result_bytes = _file(selected['result'], folder/'public-result.json', _REPORT_LIMIT)
    journal_path, _ = _file(selected['operator_journal'], folder/'operator/events.jsonl', _JOURNAL_LIMIT)
    saved = json.loads(result_bytes.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
    if canonical(_public_report(saved, job)) != canonical(report):
        raise _Failure('report_file_mismatch')
    journal = read_operator_journal(journal_path)
    header = journal['header']
    if (header['run_id'] != job['run_id'] or header['runtime_instance_id'] != job['runtime_instance_id']
            or journal['integrity']['status'] != 'verified'
            or journal['integrity']['file_sha256'] != selected['operator_journal']['sha256']
            or journal['complete'] is not True or journal['unresolved_request_ids'] or journal['resumable'] is not False):
        raise _Failure('journal_identity_or_incomplete')
    observations = {event['event_id'] for event in journal['events'] if event['type'] == 'observation'}
    refs = report['evidence']['measurement_refs']+report['assessment']['evidence_refs']+report['cleanup']['evidence_refs']
    if not set(refs) <= observations:
        raise _Failure('report_event_reference')
    intents = sum(event['type'] == 'intent' for event in journal['events'])
    retries = sum(event['type'] == 'transport_retry' for event in journal['events'])
    if report['usage']['logical_requests'] != intents or report['usage']['transport_retries'] != retries:
        raise _Failure('report_journal_usage')
    return report, [(selected['result'], result_path), (selected['operator_journal'], journal_path)]


def _public_identity(job):
    result = {}
    if type(job) is dict:
        for name in ('request_id', 'intake_id', 'run_id', 'runtime_instance_id'):
            value = job.get(name)
            if type(value) is str and _ID.fullmatch(value):
                result[name] = value
        if type(job.get('revision')) is int and job['revision'] > 0:
            result['revision'] = job['revision']
    return result


def _failed(api, store, job, code, dispatched):
    result = {**_public_identity(job), 'state': 'uncertain' if dispatched else 'failed', 'error_code': code}
    try:
        _id(job['request_id'])
        if type(job.get('token')) is not str or not job['token']:
            raise _Failure('claim_invalid')
        saved = api.fail_fixture_job(store, job['request_id'], job['token'], code, dispatched=dispatched)
        if type(saved) is not dict or saved.get('state') not in {'failed', 'uncertain', 'superseded'}:
            raise _Failure('failure_state_invalid')
        result['state'] = saved['state']
    except BaseException:
        result.update(state='uncertain', error_code='failure_record_error')
    return result


def _one(api, store, job, root, executor):
    dispatched, fence_failed = False, False

    def can_continue():
        nonlocal fence_failed
        if fence_failed:
            return False
        try:
            current = api.fixture_lease_current(store, job['request_id'], job['token'])
            if current is not True:
                fence_failed = True
        except BaseException:
            fence_failed = True
        return not fence_failed

    try:
        request = _claim(job)
        if not can_continue():
            raise _Failure('lease_or_readiness_lost')
        folder = _folder(root, job)
        if not can_continue():
            raise _Failure('lease_or_readiness_lost')
        dispatched = True
        value = executor(request, folder, run_id=job['run_id'], runtime_instance_id=job['runtime_instance_id'],
                         can_continue=can_continue)
        if not can_continue():
            raise _Failure('lease_or_readiness_lost')
        report, files = _validated(value, folder, job)
        public_artifacts = []
        for artifact, path in files:
            if not can_continue():
                raise _Failure('lease_or_readiness_lost')
            _plain(path)
            sha = store.import_artifact(path, kind='synthetic_evidence', synthetic=True)
            if sha != artifact['sha256'] or store.evidence_is_synthetic(sha) is not True:
                raise _Failure('imported_artifact_mismatch')
            stored = store.verify_blob(sha)
            data = stored.read_bytes()
            if len(data) != artifact['bytes'] or hashlib.sha256(data).hexdigest() != sha:
                raise _Failure('imported_artifact_mismatch')
            public_artifacts.append({'kind': artifact['kind'], 'artifact_id': 'blob:'+sha,
                                     'sha256': sha, 'bytes': artifact['bytes']})
        if not can_continue():
            raise _Failure('lease_or_readiness_lost')
        saved = api.complete_fixture_job(store, job['request_id'], job['token'], report, public_artifacts)
        if type(saved) is not dict or saved.get('state') != 'completed':
            raise _Failure('publication_not_completed')
        return {**_public_identity(job), 'state': 'completed', 'error_code': None}
    except BaseException as error:
        return _failed(api, store, job, error.code if isinstance(error, _Failure) else 'fixture_execution_error', dispatched)


def run_fixture_worker(store, *, worker_id, output_root, max_jobs=1, lease_seconds=120, executor=None):
    """Process each claim once, preserving every uncertain/failed run directory.

    Queue and executor implementations are trusted. They own readiness/CAS and
    runtime semantics respectively. No new-runtime retry or cleanup is done here.
    """
    identifier(worker_id)
    if type(max_jobs) is not int or max_jobs < 1:
        raise ValueError('max_jobs must be a positive integer')
    if not _finite(lease_seconds) or not 0 < lease_seconds <= 3600:
        raise ValueError('lease_seconds must be in (0,3600]')
    if executor is None:
        try:
            executor = importlib.import_module('.virtual_fleet.method_adapter', __package__).run_fixture_method
        except (ImportError, AttributeError):
            raise ValueError('fixture_executor_unavailable') from None
    if not callable(executor):
        raise ValueError('executor must be callable')
    try:
        root = _plain(output_root)
        if root.exists() and not root.is_dir():
            raise ValueError('output_root_invalid')
        api = _queue_api()
        if any(not callable(getattr(api, name, None)) for name in
               ('claim_fixture_job', 'fixture_lease_current', 'complete_fixture_job', 'fail_fixture_job')):
            raise ValueError('fixture_queue_unavailable')
    except (OSError, TypeError, ImportError, AttributeError):
        raise ValueError('fixture_configuration_invalid') from None
    results, stop_reason = [], 'job_limit'
    for _ in range(max_jobs):
        try:
            claimed = api.claim_fixture_job(store, worker_id, lease_seconds=lease_seconds)
        except BaseException:
            stop_reason = 'state_error'
            break
        if claimed is None:
            stop_reason = 'idle'
            break
        result = _one(api, store, claimed, root, executor)
        results.append(result)
        if result['state'] == 'uncertain':
            stop_reason = 'uncertain'
            break
    return {'schema_version': 1, 'worker_id': worker_id, 'execution_mode': 'fixture_only',
            'synthetic': True, 'hardware_verified': False, 'ai_model_called': False, 'resumable': False,
            'stop_reason': stop_reason, 'attempted_jobs': len(results), 'results': results}
