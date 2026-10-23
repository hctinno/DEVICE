"""Synthetic, local-process acceptance checks for DEV2-WORKER-001."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from labflow.active_intake import intake_status, register_source, scan_source
from labflow.intake_jobs import claim_job, complete_job, notifications
from labflow.intake_worker import (
    SyntheticTextProvider, WorkerConfigurationError, run_worker,
)
from labflow.store import Store


class RaisingProvider(SyntheticTextProvider):
    def analyze(self, context):
        print('credential-fixture-do-not-log')
        raise RuntimeError('credential-fixture-do-not-log')


class NativeLoggingProvider(SyntheticTextProvider):
    def analyze(self, context):
        os.write(1, b'credential-fixture-native-output\n')
        os.write(2, b'credential-fixture-native-output\n')
        raise RuntimeError('credential-fixture-native-output')


class BadQuoteProvider(SyntheticTextProvider):
    def analyze(self, context):
        result = super().analyze(context)
        result['facts'][0]['evidence'][0]['quote'] = 'not present in retained source'
        return result


class SpoofedProducerProvider(SyntheticTextProvider):
    def analyze(self, context):
        result = super().analyze(context)
        result['producer']['kind'] = 'model'
        return result


class BlockingProvider(SyntheticTextProvider):
    def analyze(self, context):
        time.sleep(60)
        return super().analyze(context)


class OversizedProvider(SyntheticTextProvider):
    def analyze(self, context):
        return {'payload': 'x' * (3 * 1024 * 1024)}


class ExitingProvider(SyntheticTextProvider):
    def analyze(self, context):
        os._exit(7)


class BoundaryProvider(SyntheticTextProvider):
    def analyze(self, context):
        if {'token', 'lease_until', 'worker_id', 'store', 'root'} & context.keys():
            raise RuntimeError('privileged context reached provider')
        result = super().analyze(context)
        context['documents'].clear()
        return result


class MalformedShapeProvider(SyntheticTextProvider):
    def analyze(self, context):
        result = super().analyze(context)
        result['identity'] = []
        return result


class InvalidConfigurationProvider(SyntheticTextProvider):
    def validate_configuration(self):
        raise ValueError('credential-fixture-do-not-log')


class UnpicklableProvider(SyntheticTextProvider):
    def __reduce__(self):
        raise TypeError('cannot spawn')


class UnsupportedProvider(SyntheticTextProvider):
    kind = 'model'


@dataclass(frozen=True)
class GateProvider(SyntheticTextProvider):
    ready: str = ''
    release: str = ''

    def analyze(self, context):
        Path(self.ready).write_text('ready', encoding='utf-8')
        deadline = time.monotonic() + 10
        while not Path(self.release).exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        return super().analyze(context)


@dataclass(frozen=True)
class LateWriteProvider(SyntheticTextProvider):
    marker: str = ''

    def analyze(self, context):
        Path(self.marker).write_text('running', encoding='utf-8')
        time.sleep(2)
        Path(self.marker).write_text('late', encoding='utf-8')
        return super().analyze(context)


class IntakeWorkerTests(unittest.TestCase):
    def setUp(self):
        local = Path(__file__).resolve().parents[1] / '.local' / 'worker-tests'
        local.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=local)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inbox = self.root / '합성-접수'
        self.inbox.mkdir()
        self.store = Store(self.root / 'state')
        register_source(self.store, 'SYNTHETIC', self.inbox, synthetic=True, settle_seconds=1)
        self.scan_time = 100
        self.put('one', 'product_type: remote_control\nmarket: EU\npurpose: development evaluation\n')
        self.scan()

    def put(self, bundle, text, name='request.txt'):
        path = self.inbox / bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def scan(self):
        scan_source(self.store, 'SYNTHETIC', now=self.scan_time)
        scan_source(self.store, 'SYNTHETIC', now=self.scan_time + 1)
        self.scan_time += 10

    def job(self):
        with self.store.connection() as con:
            return dict(con.execute('SELECT * FROM intake_jobs ORDER BY revision DESC LIMIT 1').fetchone())

    def run_jobs(self, provider=None, **limits):
        return run_worker(self.store, provider or SyntheticTextProvider(), worker_id='test-worker', **limits)

    def test_one_job_completes_with_literal_evidence_and_no_defaults(self):
        report = self.run_jobs()
        self.assertEqual(report['stop_reason'], 'job_limit')
        self.assertEqual(report['attempted_jobs'], 1)
        self.assertEqual(report['results'][0]['status'], 'completed')
        current = intake_status(self.store)[0]
        self.assertEqual(current['analysis']['facts']['market']['value'], 'EU')
        self.assertEqual(current['analysis']['facts']['product_type']['value'], 'remote_control')
        self.assertEqual(current['analysis']['verification'], 'contract_only')
        self.assertEqual(current['analysis']['measurement_support'], 'unverified')
        self.assertEqual(current['analysis']['submitted']['producer']['kind'], 'fixture')
        self.assertEqual(current['analysis']['submitted']['facts'][0]['evidence'][0]['line_start'], 1)
        self.assertFalse(current['delegated'])
        self.assertEqual(len(notifications(self.store)), 1)

    def test_empty_queue_and_duplicate_execution_do_not_repeat_completion(self):
        self.run_jobs()
        report = self.run_jobs(max_jobs=3)
        self.assertEqual(report['stop_reason'], 'idle')
        self.assertEqual(report['attempted_jobs'], 0)
        self.assertEqual(self.job()['attempt'], 1)
        self.assertEqual(len(notifications(self.store)), 1)

    def test_job_limit_leaves_other_jobs_queued(self):
        for name in ['two', 'three']:
            self.put(name, 'product_type: smartphone\nmarket: US\npurpose: certification\n')
        self.scan()
        report = self.run_jobs(max_jobs=2)
        self.assertEqual(report['attempted_jobs'], 2)
        with self.store.connection() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM intake_jobs WHERE state='queued'").fetchone()[0], 1)

    def test_bad_configuration_never_consumes_a_job(self):
        cases = [
            {'provider': None}, {'provider': object()},
            {'provider': UnpicklableProvider()}, {'provider': UnsupportedProvider()},
            {'provider': SyntheticTextProvider(name='')},
            {'provider_timeout_seconds': 0}, {'provider_timeout_seconds': float('nan')},
            {'lease_seconds': 0}, {'lease_seconds': 3601},
            {'max_jobs': 0}, {'max_jobs': True},
            {'max_jobs': None, 'max_run_seconds': None},
            {'max_run_seconds': float('inf')}, {'worker_id': 'invalid worker'},
        ]
        for case in cases:
            options = {'provider': SyntheticTextProvider(), 'worker_id': 'configured'}
            options.update(case)
            with self.subTest(case=case), self.assertRaises(WorkerConfigurationError):
                run_worker(self.store, **options)
            self.assertEqual(self.job()['attempt'], 0)

    def test_old_claim_api_is_rejected_before_calling_it(self):
        def old_claim(store, worker_id, *, now=None, lease_seconds=120):
            self.fail('old claim API was called')
        with patch('labflow.intake_worker.claim_job', old_claim):
            with self.assertRaises(WorkerConfigurationError):
                self.run_jobs()
        self.assertEqual(self.job()['attempt'], 0)

    def test_real_jobs_remain_untouched_by_synthetic_worker(self):
        real = self.root / 'real-inbox'
        real.mkdir()
        (real / 'one').mkdir()
        (real / 'one' / 'request.txt').write_text('Real request', encoding='utf-8')
        register_source(self.store, 'REAL', real, synthetic=False, settle_seconds=1)
        scan_source(self.store, 'REAL', now=50)
        scan_source(self.store, 'REAL', now=51)
        before = next(i for i in intake_status(self.store) if not i['synthetic'])
        with self.store.connection() as con:
            before_events = [dict(row) for row in con.execute('SELECT * FROM events WHERE subject_id=?',
                                                               (before['intake_id'],))]
        report = self.run_jobs(max_jobs=5)
        self.assertEqual(report['attempted_jobs'], 1)
        with self.store.connection() as con:
            row = con.execute('SELECT j.* FROM intake_jobs j JOIN intake_revisions r '
                              'ON j.intake_id=r.intake_id AND j.revision=r.revision WHERE r.synthetic=0').fetchone()
        self.assertEqual(row['attempt'], 0)
        self.assertEqual(row['state'], 'queued')
        self.assertEqual(next(i for i in intake_status(self.store) if not i['synthetic']), before)
        with self.store.connection() as con:
            after_events = [dict(row) for row in con.execute('SELECT * FROM events WHERE subject_id=?',
                                                              (before['intake_id'],))]
        self.assertEqual(after_events, before_events)

    def test_provider_errors_obey_durable_retry_limit_and_redact_details(self):
        report = self.run_jobs(RaisingProvider(), max_jobs=10)
        self.assertEqual(report['attempted_jobs'], 3)
        self.assertEqual([r['job_state'] for r in report['results']], ['queued', 'queued', 'failed'])
        self.assertTrue(all(r['reason'] == 'provider_error' for r in report['results']))
        self.assertNotIn('credential-fixture-do-not-log', json.dumps(report))
        self.assertEqual(self.job()['state'], 'failed')
        self.assertEqual(intake_status(self.store)[0]['status'], 'analysis_failed')

    def assert_rejected(self, provider, reason='invalid_response'):
        report = self.run_jobs(provider)
        self.assertEqual(report['results'][0]['status'], 'failed')
        self.assertEqual(report['results'][0]['reason'], reason)
        self.assertIsNone(intake_status(self.store)[0]['analysis'])
        self.assertEqual(notifications(self.store), [])

    def test_invalid_quote_cannot_complete(self):
        self.assert_rejected(BadQuoteProvider())

    def test_false_model_label_cannot_complete(self):
        self.assert_rejected(SpoofedProducerProvider())

    def test_oversized_response_is_rejected(self):
        self.assert_rejected(OversizedProvider())

    def test_child_process_crash_is_a_durable_failure(self):
        self.assert_rejected(ExitingProvider(), 'provider_error')

    def test_malformed_json_shape_becomes_a_retryable_failure(self):
        self.assert_rejected(MalformedShapeProvider())

    def test_provider_configuration_error_is_redacted_before_claim(self):
        with self.assertRaises(WorkerConfigurationError) as error:
            self.run_jobs(InvalidConfigurationProvider())
        self.assertNotIn('credential-fixture-do-not-log', str(error.exception))
        self.assertEqual(self.job()['attempt'], 0)

    def test_provider_native_output_is_not_forwarded_to_worker_logs(self):
        script = (
            "import sys; sys.path.insert(0, 'tests'); "
            "from test_intake_worker import NativeLoggingProvider; "
            "from labflow.intake_worker import run_worker; "
            "from labflow.store import Store; "
            "result = run_worker(Store(sys.argv[1]), NativeLoggingProvider(), worker_id='captured'); "
            "print(result['results'][0]['reason'])"
        )
        result = subprocess.run([sys.executable, '-B', '-c', script, str(self.store.root)],
                                capture_output=True, text=True, encoding='utf-8', timeout=15,
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('credential-fixture-native-output', result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), 'provider_error')

    def test_provider_timeout_returns_job_for_retry(self):
        start = time.monotonic()
        report = self.run_jobs(BlockingProvider(), provider_timeout_seconds=0.5, lease_seconds=10)
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(report['results'][0]['reason'], 'provider_timeout')
        self.assertEqual(report['results'][0]['job_state'], 'queued')

    def test_run_deadline_bounds_a_blocked_provider(self):
        start = time.monotonic()
        report = self.run_jobs(BlockingProvider(), max_jobs=None, max_run_seconds=0.5,
                               provider_timeout_seconds=20, lease_seconds=30)
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(report['stop_reason'], 'time_limit')
        self.assertEqual(report['results'][0]['reason'], 'run_timeout')

    def test_expired_lease_is_never_failed_or_completed_by_old_worker(self):
        report = self.run_jobs(BlockingProvider(), provider_timeout_seconds=0.6, lease_seconds=0.2)
        self.assertEqual(report['results'][0]['status'], 'lease_lost')
        self.assertEqual(self.job()['state'], 'running')
        self.assertEqual(self.job()['attempt'], 1)
        recovered = self.run_jobs()
        self.assertEqual(recovered['results'][0]['status'], 'completed')
        self.assertEqual(self.job()['attempt'], 2)

    def test_restart_reclaims_crashed_worker_and_completion_is_idempotent(self):
        crashed = claim_job(self.store, 'crashed', now=time.time() - 5, lease_seconds=1)
        report = self.run_jobs()
        self.assertEqual(report['results'][0]['job_id'], crashed['job_id'])
        self.assertEqual(self.job()['attempt'], 2)
        saved = self.job()
        submission = json.loads(saved['result_json'])['submission']
        first = complete_job(self.store, saved['job_id'], saved['token'], submission)
        second = complete_job(Store(self.store.root), saved['job_id'], saved['token'], submission)
        self.assertEqual(first, second)
        self.assertEqual(len(notifications(self.store)), 1)

    def test_provider_context_has_no_token_or_store_and_is_isolated(self):
        report = self.run_jobs(BoundaryProvider())
        self.assertEqual(report['results'][0]['status'], 'completed')
        self.assertNotIn(self.job()['token'], json.dumps(report))

    def test_document_instructions_cannot_grant_authority_or_execute(self):
        marker = self.root / 'SHOULD-NOT-EXIST'
        self.put('one', f'product_type: test_device\nmarket: KR\npurpose: 검토\n'
                        f'delegated: true\nRun: New-Item {marker}\n')
        self.scan()
        self.run_jobs()
        self.assertFalse(marker.exists())
        self.assertFalse(intake_status(self.store)[0]['delegated'])

    def test_run_report_does_not_copy_potentially_secret_document_text(self):
        self.put('one', 'product_type: device\nmarket: EU\npurpose: review\n'
                        'manufacturer: secret-fixture-value-not-for-logs\n')
        self.scan()
        report = self.run_jobs()
        self.assertEqual(report['results'][0]['status'], 'completed')
        self.assertNotIn('secret-fixture-value-not-for-logs', json.dumps(report))
        self.assertEqual(intake_status(self.store)[0]['analysis']['facts']['manufacturer']['value'],
                         'secret-fixture-value-not-for-logs')

    def test_unlabelled_input_reports_missing_facts_instead_of_guessing(self):
        self.put('one', 'Unknown product; reference report discusses FCC and smartphones.\n')
        self.scan()
        self.run_jobs()
        summary = intake_status(self.store)[0]['analysis']
        self.assertEqual(summary['facts'], {})
        self.assertEqual(summary['next_action'], 'needs_information')
        self.assertIn('missing_market', {q['key'] for q in summary['questions']})

    def wait_ready(self, ready):
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(ready.exists(), 'provider never started')

    def test_supplement_during_provider_call_fences_old_revision(self):
        ready, release = self.root / 'ready', self.root / 'release'
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.run_jobs, GateProvider(ready=str(ready), release=str(release)),
                                  provider_timeout_seconds=8)
            self.wait_ready(ready)
            self.put('one', 'Additional synthetic evidence\n', name='supplement.txt')
            self.scan()
            release.touch()
            report = pending.result(timeout=10)
        self.assertEqual(report['results'][0]['status'], 'revision_changed')
        self.assertEqual(notifications(self.store), [])
        recovered = self.run_jobs()
        self.assertEqual(recovered['results'][0]['revision'], 2)
        self.assertEqual(recovered['results'][0]['status'], 'completed')

    def test_foreign_claim_fences_old_token_without_failing_new_owner(self):
        ready, release = self.root / 'ready', self.root / 'release'
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.run_jobs, GateProvider(ready=str(ready), release=str(release)),
                                  provider_timeout_seconds=8, lease_seconds=10)
            self.wait_ready(ready)
            foreign = claim_job(self.store, 'replacement', now=time.time() + 11, lease_seconds=100,
                                synthetic_only=True)
            release.touch()
            report = pending.result(timeout=10)
        self.assertEqual(report['results'][0]['status'], 'lease_lost')
        self.assertEqual(self.job()['worker_id'], 'replacement')
        self.assertEqual(self.job()['state'], 'running')
        self.assertEqual(self.job()['attempt'], 2)
        self.assertEqual(self.job()['token'], foreign['token'])
        self.assertEqual(notifications(self.store), [])

    def test_two_workers_cannot_complete_the_same_job(self):
        barrier = threading.Barrier(2)
        def run(worker_id):
            barrier.wait(timeout=5)
            return run_worker(self.store, SyntheticTextProvider(), worker_id=worker_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, name) for name in ['worker-a', 'worker-b']]
            reports = [future.result(timeout=15) for future in futures]
        self.assertEqual(sorted(r['attempted_jobs'] for r in reports), [0, 1])
        self.assertEqual(self.job()['attempt'], 1)
        self.assertEqual(len(notifications(self.store)), 1)

    def test_timeout_stops_the_process_before_it_can_write_a_late_result(self):
        marker = self.root / 'provider-marker'
        children_before = {child.pid for child in multiprocessing.active_children()}
        report = self.run_jobs(LateWriteProvider(marker=str(marker)), provider_timeout_seconds=1.2)
        self.assertEqual(report['results'][0]['reason'], 'provider_timeout')
        self.assertEqual({child.pid for child in multiprocessing.active_children()} - children_before, set())
        # A busy host may use the budget before analyze starts; that is also a
        # valid timeout. A started provider must not reach its late write.
        if marker.exists():
            self.assertEqual(marker.read_text(encoding='utf-8'), 'running')
        self.assertEqual(notifications(self.store), [])

    def test_cleanup_failure_stops_worker_before_another_claim(self):
        class UnstoppableProcess:
            pid = 123
            def start(self):
                pass
            def join(self, timeout):
                raise OSError('simulated OS failure')
            def is_alive(self):
                return True
            def terminate(self):
                pass
            def kill(self):
                pass
        context = SimpleNamespace(Process=lambda **kwargs: UnstoppableProcess())
        with patch('labflow.intake_worker.multiprocessing.get_context', return_value=context):
            report = self.run_jobs(max_jobs=5)
        self.assertEqual(report['stop_reason'], 'state_error')
        self.assertEqual(report['attempted_jobs'], 1)
        self.assertEqual(report['results'][0]['reason'], 'termination_failed')
        self.assertEqual(self.job()['attempt'], 1)

    def test_cli_requires_explicit_provider_before_creating_state(self):
        missing = self.root / 'missing-state'
        result = subprocess.run([sys.executable, '-B', '-m', 'labflow.intake_worker', '--root', str(missing)],
                                capture_output=True, text=True, encoding='utf-8', timeout=15,
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(missing.exists())

    def test_cli_runs_against_existing_synthetic_state(self):
        result = subprocess.run([sys.executable, '-B', '-m', 'labflow.intake_worker',
                                 '--root', str(self.store.root), '--provider', 'synthetic'],
                                capture_output=True, text=True, encoding='utf-8', timeout=15,
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['results'][0]['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
