"""Bounded, synthetic-only intake analysis with a killable provider process.

Only the parent holds the Store and lease token. Provider classes are trusted
local code, not a sandbox for code supplied in intake documents.
"""
from abc import ABC, abstractmethod
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
import inspect
import json
import math
import multiprocessing
from multiprocessing.reduction import ForkingPickler
import os
from pathlib import Path
import sqlite3
import tempfile
import time

from .intake_analysis import FIELDS, REQUIRED_FIELDS
from .intake_jobs import claim_job, complete_job, fail_job
from .store import Store, canonical, identifier

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_CLEANUP_SECONDS = 0.25


class WorkerConfigurationError(ValueError):
    """A preflight error that must not consume a queued job."""


class AnalysisProvider(ABC):
    """Trusted, importable, spawn-pickleable, synchronous leaf-process adapter.

    This version admits fixture providers only. An adapter must not launch
    background work, subprocesses, external APIs, or hardware operations.
    """

    kind = 'fixture'
    name = ''

    def validate_configuration(self):
        """Validate local configuration without acquiring jobs or doing I/O."""

    @abstractmethod
    def analyze(self, context):
        """Return schema 1 text or context-bound schema 2 page analysis."""


@dataclass(frozen=True)
class SyntheticTextProvider(AnalysisProvider):
    """Read literal `field: value` lines in synthetic fixtures; never infer."""

    name: str = 'synthetic-labelled-text-v1'

    def analyze(self, context):
        if context.get('synthetic') is not True:
            raise ValueError('Synthetic context required')
        version = 2 if any(d.get('format') == 'pdf' for d in context['documents']) else 1
        facts = []
        for document in context['documents']:
            if document.get('format') == 'pdf':
                sources = [(page['text'], {'kind': 'pdf_page', 'extraction_id': document['extraction_id'],
                            'page_number': page['page_number'], 'text_sha256': page['text_sha256']})
                           for page in document['pages'] if document['parse_status'] in {'ok', 'partial'}
                           and page['status'] in {'ok', 'truncated'}]
            else:
                sources = [] if document['text'] is None else [(document['text'], {'kind': 'text_line'} if version == 2 else {})]
            for text, location in sources:
                for number, line in enumerate(text.splitlines(), 1):
                    field, separator, value = line.partition(':')
                    field, value = field.strip(), value.strip()
                    if not separator or field not in FIELDS or not value:
                        continue
                    facts.append({'field': field, 'value': value, 'status': 'explicit',
                                  'evidence': [{**location, 'path': document['path'], 'sha256': document['sha256'],
                                                'line_start': number, 'line_end': number,
                                                'quote': line, 'role': 'request'}]})
        products = {f['value'] for f in facts if f['field'] == 'product_type'}
        present = {f['field'] for f in facts}
        return {'schema_version': version, **({'context_id': context['analysis_context_id']} if version == 2 else {}),
                'producer': {'kind': self.kind, 'name': self.name},
                'identity': 'single' if len(products) == 1 else 'ambiguous' if products else 'unknown',
                'facts': facts, 'missing_fields': sorted(REQUIRED_FIELDS - present)}


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise WorkerConfigurationError(label + ' must be finite and positive')


def _preflight(provider, worker_id, max_jobs, max_run_seconds, provider_timeout_seconds, lease_seconds):
    try:
        identifier(worker_id)
    except ValueError:
        raise WorkerConfigurationError('Invalid worker identifier') from None
    if max_jobs is not None and (type(max_jobs) is not int or max_jobs <= 0):
        raise WorkerConfigurationError('max_jobs must be a positive integer')
    if max_run_seconds is not None:
        _positive(max_run_seconds, 'max_run_seconds')
    if max_jobs is None and max_run_seconds is None:
        raise WorkerConfigurationError('An explicit job or run-time limit is required')
    _positive(provider_timeout_seconds, 'provider_timeout_seconds')
    _positive(lease_seconds, 'lease_seconds')
    if lease_seconds > 3600:
        raise WorkerConfigurationError('lease_seconds must not exceed 3600')
    if not isinstance(provider, AnalysisProvider) or provider.kind != 'fixture':
        raise WorkerConfigurationError('Configure a supported local fixture provider')
    if not isinstance(provider.name, str) or not provider.name.strip() or len(provider.name) > 200:
        raise WorkerConfigurationError('A provider name of at most 200 characters is required')
    if type(provider).__module__ in {'__main__', '__mp_main__'} or '<locals>' in type(provider).__qualname__:
        raise WorkerConfigurationError('Provider class must be importable by a spawned process')
    try:
        provider.validate_configuration()
        ForkingPickler.dumps(provider)
    except Exception:
        raise WorkerConfigurationError('Provider configuration is invalid or not spawn-pickleable') from None
    try:
        parameter = inspect.signature(claim_job).parameters.get('synthetic_only')
    except (TypeError, ValueError):
        parameter = None
    if parameter is None or parameter.kind not in {inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}:
        raise WorkerConfigurationError('claim_job with atomic synthetic_only support is required')


def _provider_process(provider, context, output):
    # Do not forward provider print output or exception messages to the worker log.
    with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink), redirect_stderr(sink):
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
        try:
            analysis = provider.analyze(context)
        except BaseException:
            payload = {'status': 'error', 'reason': 'provider_error'}
        else:
            payload = {'status': 'ok', 'analysis': analysis}
        try:
            data = canonical(payload).encode('utf-8')
            if len(data) > MAX_RESPONSE_BYTES:
                data = canonical({'status': 'error', 'reason': 'invalid_response'}).encode('utf-8')
        except (TypeError, ValueError, OverflowError):
            data = canonical({'status': 'error', 'reason': 'invalid_response'}).encode('utf-8')
        Path(output).write_bytes(data)


def _stop_process(process):
    try:
        if process.is_alive():
            process.terminate()
            process.join(_CLEANUP_SECONDS)
        if process.is_alive():
            process.kill()
            process.join(_CLEANUP_SECONDS)
        return not process.is_alive()
    except (OSError, ValueError):
        return False


def _invoke(provider, context, root, timeout, timeout_reason):
    deadline = time.monotonic() + max(timeout, 0)
    if timeout <= 0:
        return None, timeout_reason, False
    with tempfile.TemporaryDirectory(prefix='worker-', dir=root) as temporary:
        output = Path(temporary) / 'response.json'
        process = multiprocessing.get_context('spawn').Process(
            target=_provider_process, args=(provider, context, str(output)), daemon=True)
        stopped = None
        try:
            process.start()
            # A timed process wait can return before the requested deadline
            # (for example, after platform timer rounding). Recheck the clock
            # instead of treating one early return as an expired lease.
            while process.is_alive():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                process.join(remaining)
            if process.is_alive() or time.monotonic() >= deadline:
                stopped = _stop_process(process)
                return None, timeout_reason if stopped else 'termination_failed', not stopped
            if process.exitcode != 0 or not output.is_file():
                return None, 'provider_error', False
            with output.open('rb') as stream:
                data = stream.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                return None, 'invalid_response', False
            payload = json.loads(data)
            if not isinstance(payload, dict):
                return None, 'invalid_response', False
            if payload.get('status') == 'ok':
                return payload.get('analysis'), None, False
            reason = payload.get('reason')
            return None, reason if reason in {'provider_error', 'invalid_response'} else 'invalid_response', False
        except (OSError, ValueError, TypeError, EOFError):
            stopped = process.pid is None or _stop_process(process)
            return None, 'provider_error' if stopped else 'termination_failed', not stopped
        finally:
            if process.pid is not None:
                if stopped is None:
                    stopped = _stop_process(process)
                if stopped:
                    process.close()


def _lease_issue(store, job):
    with store.connection() as con:
        current = con.execute('SELECT j.token,j.state,j.lease_until,j.revision,i.revision AS current_revision,'
                              'i.status FROM intake_jobs j JOIN intakes i USING(intake_id) WHERE j.job_id=?',
                              (job['job_id'],)).fetchone()
    if current is None:
        return 'lease_lost', 'lease_missing'
    if current['revision'] != current['current_revision'] or current['status'] == 'upload_incomplete':
        return 'revision_changed', 'revision_changed'
    if current['token'] != job['token'] or current['state'] != 'running':
        return 'lease_lost', 'lease_replaced'
    if current['lease_until'] <= time.time():
        return 'lease_lost', 'lease_expired'
    return None


def _failure(store, job, reason):
    issue = _lease_issue(store, job)
    if issue:
        return {'status': issue[0], 'reason': issue[1], 'job_state': None}
    if reason == 'lease_expired':
        # The monotonic execution budget can end before the wall-clock lease
        # expires. Relinquish this worker's attempt without a failure write;
        # another worker can reclaim it after the DB lease actually expires.
        return {'status': 'lease_lost', 'reason': 'lease_budget_elapsed', 'job_state': None}
    try:
        failed = fail_job(store, job['job_id'], job['token'])
    except ValueError:
        issue = _lease_issue(store, job)
        return {'status': issue[0] if issue else 'state_error',
                'reason': issue[1] if issue else 'failure_rejected', 'job_state': None}
    return {'status': 'failed', 'reason': reason, 'job_state': failed['state']}


def run_worker(store, provider, *, worker_id, max_jobs=1, max_run_seconds=None,
               provider_timeout_seconds=30, lease_seconds=120):
    """Process synthetic jobs until idle or a declared job/time limit is met.

    Provider execution is forcibly bounded; source preparation, synchronous DB
    calls and OS cleanup are outside the hard deadline. The run budget is checked
    again after preparation. Exceptions and tokens are not returned.
    """
    _preflight(provider, worker_id, max_jobs, max_run_seconds, provider_timeout_seconds, lease_seconds)
    deadline = None if max_run_seconds is None else time.monotonic() + max_run_seconds
    results = []
    stop_reason = 'idle'
    while max_jobs is None or len(results) < max_jobs:
        if deadline is not None and time.monotonic() >= deadline:
            stop_reason = 'time_limit'
            break
        try:
            job = claim_job(store, worker_id, lease_seconds=lease_seconds, synthetic_only=True)
        except (ValueError, OSError, sqlite3.Error):
            stop_reason = 'state_error'
            break
        if job is None:
            break
        result = {key: job[key] for key in ('job_id', 'intake_id', 'revision', 'attempt', 'synthetic')}
        if job['synthetic'] is not True:
            # A broken/incompatible core must never lead to real-work failure writes.
            result.update(status='state_error', reason='synthetic_scope_violation', job_state=None)
            results.append(result)
            stop_reason = 'state_error'
            break
        context = {key: job[key] for key in ('job_id', 'intake_id', 'revision', 'synthetic',
                                            'documents', 'analysis_contract', 'instructions')}
        if 'analysis_context_id' in job:
            context['analysis_context_id'] = job['analysis_context_id']
        budgets = [(provider_timeout_seconds, 'provider_timeout'),
                   (job['lease_until'] - time.time(), 'lease_expired')]
        if deadline is not None:
            budgets.append((deadline - time.monotonic(), 'run_timeout'))
        timeout, timeout_reason = min(budgets)
        analysis, error, fatal = _invoke(provider, context, store.root, timeout, timeout_reason)
        if error is None:
            if not isinstance(analysis, dict) or analysis.get('producer') != {'kind': provider.kind, 'name': provider.name}:
                error = 'invalid_response'
            else:
                try:
                    complete_job(store, job['job_id'], job['token'], analysis)
                    result.update(status='completed', reason=None, job_state='completed')
                except (ValueError, TypeError, KeyError, OverflowError):
                    error = 'invalid_response'
        if error is not None:
            result.update(_failure(store, job, error))
        results.append(result)
        if fatal or result['status'] == 'state_error':
            stop_reason = 'state_error'
            break
        if deadline is not None and time.monotonic() >= deadline:
            stop_reason = 'time_limit'
            break
    else:
        stop_reason = 'job_limit'
    return {'worker_id': worker_id, 'execution_mode': 'synthetic', 'verification': 'contract_only',
            'stop_reason': stop_reason, 'attempted_jobs': len(results), 'results': results}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='Run bounded synthetic intake analysis; no model or hardware API.')
    parser.add_argument('--root', required=True, help='Existing intake state directory')
    parser.add_argument('--provider', required=True, choices=['synthetic'])
    parser.add_argument('--worker-id', default='synthetic-worker')
    parser.add_argument('--max-jobs', type=int)
    parser.add_argument('--max-run-seconds', type=float)
    parser.add_argument('--provider-timeout-seconds', type=float, default=30)
    parser.add_argument('--lease-seconds', type=float, default=120)
    args = parser.parse_args(argv)
    limits = {'worker_id': args.worker_id, 'max_jobs': args.max_jobs,
              'max_run_seconds': args.max_run_seconds, 'provider_timeout_seconds': args.provider_timeout_seconds,
              'lease_seconds': args.lease_seconds}
    if args.max_jobs is None and args.max_run_seconds is None:
        limits['max_jobs'] = 1
    provider = SyntheticTextProvider()
    try:
        _preflight(provider, **limits)
        root = Path(args.root)
        if not (root / 'lab.sqlite3').is_file():
            raise WorkerConfigurationError('An existing intake state directory is required')
        report = run_worker(Store(root), provider, **limits)
    except WorkerConfigurationError as error:
        print(canonical({'error': 'configuration_error', 'message': str(error)}))
        return 2
    except (ValueError, OSError, sqlite3.Error):
        print(canonical({'error': 'state_error'}))
        return 1
    print(canonical(report))
    return int(report['stop_reason'] == 'state_error' or any(r['status'] != 'completed' for r in report['results']))


if __name__ == '__main__':
    # Keep provider classes/targets importable under Windows multiprocessing spawn.
    from labflow.intake_worker import main as entrypoint
    raise SystemExit(entrypoint())
