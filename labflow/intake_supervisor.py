"""Cooperative, bounded synthetic discovery and existing fixture analysis."""
import math
from time import monotonic, sleep

from .active_intake import scan_source
from .intake_worker import _preflight, run_worker
from .store import identifier


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _source_is_synthetic(con, source_id):
    row = con.execute('SELECT synthetic FROM intake_sources WHERE source_id=?', (source_id,)).fetchone()
    return row is not None and row['synthetic'] == 1


def _configuration(store, source_ids, provider, worker_id, max_cycles, max_run_seconds, poll_seconds,
                   max_jobs_per_cycle, provider_timeout_seconds, lease_seconds, can_continue):
    if (type(max_cycles) is not int or not 1 <= max_cycles <= 1024
            or type(max_jobs_per_cycle) is not int or not 1 <= max_jobs_per_cycle <= 100
            or not _finite(poll_seconds) or not .001 <= poll_seconds <= 60
            or any(not _finite(value) or not 0 < value <= 3600 for value in
                   (max_run_seconds, provider_timeout_seconds, lease_seconds))):
        raise ValueError('supervisor_configuration_invalid')
    if can_continue is not None and not callable(can_continue):
        raise ValueError('supervisor_callback_invalid')
    try:
        identifier(worker_id)
        if type(source_ids) not in (list, tuple) or not 1 <= len(source_ids) <= 8:
            raise ValueError()
        sources = tuple(source_ids)
        if any(type(source) is not str for source in sources) or len(set(sources)) != len(sources):
            raise ValueError()
        for source in sources:
            identifier(source)
    except BaseException:
        raise ValueError('supervisor_identity_invalid') from None
    try:
        _preflight(provider, worker_id, max_jobs_per_cycle, max_run_seconds, provider_timeout_seconds, lease_seconds)
    except BaseException:
        raise ValueError('supervisor_provider_invalid') from None
    try:
        with store.connection() as con:
            if not con.in_transaction:
                con.execute('BEGIN')
            if not all(_source_is_synthetic(con, source) for source in sources):
                raise ValueError()
    except BaseException:
        raise ValueError('supervisor_source_invalid') from None
    return sources


def _accepted_count(result):
    if type(result) is not dict or type(result.get('accepted')) is not list:
        raise ValueError()
    identities = set()
    for item in result['accepted']:
        if (type(item) is not dict or set(item) != {'intake_id', 'revision', 'job_id', 'kind'}
                or type(item['revision']) is not int or item['revision'] < 1
                or type(item['kind']) is not str or item['kind'] not in {'new', 'supplement'}):
            raise ValueError()
        identifier(item['intake_id'])
        identifier(item['job_id'])
        key = (item['intake_id'], item['revision'])
        if key in identities:
            raise ValueError()
        identities.add(key)
    return len(identities)


def _worker_attempts(result, maximum):
    if (type(result) is not dict or type(result.get('results')) is not list
            or type(result.get('attempted_jobs')) is not int
            or not 0 <= result['attempted_jobs'] <= maximum
            or result['attempted_jobs'] != len(result['results'])
            or type(result.get('stop_reason')) is not str
            or result['stop_reason'] not in {'idle', 'job_limit', 'time_limit', 'state_error'}):
        raise ValueError()
    for item in result['results']:
        if (type(item) is not dict or item.get('synthetic') is not True
                or type(item.get('status')) is not str
                or item['status'] not in {'completed', 'failed', 'lease_lost', 'revision_changed', 'state_error'}
                or type(item.get('revision')) is not int or item['revision'] < 1
                or type(item.get('attempt')) is not int or item['attempt'] < 1):
            raise ValueError()
        identifier(item.get('job_id'))
        identifier(item.get('intake_id'))
        if item['status'] == 'completed' and item.get('job_state') != 'completed':
            raise ValueError()
    return len(result['results'])


def run_intake_supervisor(store, source_ids, provider, *, worker_id, max_cycles=2, max_run_seconds=30,
                          poll_seconds=1, max_jobs_per_cycle=1, provider_timeout_seconds=5,
                          lease_seconds=10, can_continue=None):
    """Scan only selected synthetic sources; analyze the Store's synthetic queue.

    Counts describe confirmed attempts/accepted revisions, not successful jobs.
    The synchronous scan/worker APIs are cooperative cancellation boundaries.
    """
    started = monotonic()
    sources = _configuration(store, source_ids, provider, worker_id, max_cycles, max_run_seconds, poll_seconds,
                             max_jobs_per_cycle, provider_timeout_seconds, lease_seconds, can_continue)
    deadline, denied = started+max_run_seconds, False
    result = {'schema_version': 1, 'kind': 'bounded_intake_supervisor', 'mode': 'fixture_only',
            'analysis_scope': 'all_synthetic_jobs', 'synthetic': True, 'hardware_verified': False,
            'ai_model_called': False, 'resumable': False, 'cycles': 0, 'scanned_sources': 0,
            'accepted_revisions': 0, 'analyzed_jobs': 0, 'stop_reason': 'cycle_limit', 'error_code': None}

    def finish(reason, code=None):
        result.update(stop_reason=reason, error_code=code)
        return result

    def boundary():
        nonlocal denied
        if denied:
            return 'supervisor_stop'
        if monotonic() >= deadline:
            return 'time_limit'
        if can_continue is not None:
            try:
                denied = can_continue() is not True
            except BaseException:
                denied = True
        if denied:
            return 'supervisor_stop'
        return 'time_limit' if monotonic() >= deadline else None

    for cycle in range(max_cycles):
        for index, source in enumerate(sources):
            reason = boundary()
            if reason:
                return finish(reason)
            if index == 0:
                result['cycles'] += 1
            try:
                with store.connection() as con:
                    if not _source_is_synthetic(con, source):
                        return finish('source_error', 'source_scope_lost')
            except BaseException:
                return finish('source_error', 'source_lookup_error')
            if monotonic() >= deadline:
                return finish('time_limit')
            result['scanned_sources'] += 1
            try:
                scanned = scan_source(store, source)
            except BaseException:
                return finish('source_error', 'source_scan_error')
            try:
                result['accepted_revisions'] += _accepted_count(scanned)
            except BaseException:
                return finish('source_error', 'source_result_invalid')
        reason = boundary()
        if reason:
            return finish(reason)
        remaining = deadline-monotonic()
        if remaining <= 0:
            return finish('time_limit')
        try:
            analysis = run_worker(store, provider, worker_id=worker_id, max_jobs=max_jobs_per_cycle,
                                  max_run_seconds=remaining, provider_timeout_seconds=min(provider_timeout_seconds, remaining),
                                  lease_seconds=lease_seconds)
        except BaseException:
            return finish('worker_error', 'worker_call_error')
        try:
            result['analyzed_jobs'] += _worker_attempts(analysis, max_jobs_per_cycle)
        except BaseException:
            return finish('worker_error', 'worker_result_invalid')
        if analysis['stop_reason'] == 'state_error':
            return finish('worker_error', 'worker_state_error')
        if any(item['status'] != 'completed' for item in analysis['results']):
            return finish('worker_error', 'worker_job_failed')
        reason = boundary()
        if reason:
            return finish(reason)
        if analysis['stop_reason'] == 'time_limit':
            return finish('time_limit')
        if cycle+1 == max_cycles:
            break
        wait_until = min(deadline, monotonic()+poll_seconds)
        while True:
            reason = boundary()
            if reason:
                return finish(reason)
            remaining = wait_until-monotonic()
            if remaining <= 0:
                break
            try:
                sleep(min(.25, remaining))
            except BaseException:
                return finish('supervisor_stop', 'wait_interrupted')
    return result
