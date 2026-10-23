"""Bounded discovery/analysis acceptance; real Store and trusted fixture providers."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job
from labflow.intake_worker import SyntheticTextProvider
from labflow.intake_supervisor import run_intake_supervisor
from labflow.store import Store


CANARY = 'PRIVATE_SUPERVISOR_EXCEPTION_CANARY'
TEXT = 'product_type: remote_control\nmarket: EU\npurpose: synthetic evaluation\nmodel: WATCH-FIXTURE\n'
FIELDS = {'schema_version', 'kind', 'mode', 'synthetic', 'hardware_verified', 'ai_model_called',
          'resumable', 'analysis_scope', 'cycles', 'scanned_sources', 'accepted_revisions', 'analyzed_jobs', 'stop_reason', 'error_code'}


class RaisingProvider(SyntheticTextProvider):
    def analyze(self, context):
        print(CANARY)
        raise RuntimeError(CANARY)


class InvalidProvider(SyntheticTextProvider):
    def validate_configuration(self):
        raise ValueError(CANARY)


class ModelProvider(SyntheticTextProvider):
    kind = 'model'


class BlockingProvider(SyntheticTextProvider):
    def analyze(self, context):
        time.sleep(10)
        return super().analyze(context)


class Clock:
    def __init__(self):
        self.now, self.sleeps = 0., []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def worker_result(*statuses, stop_reason=None):
    results = [{'job_id': 'J-'+str(n), 'intake_id': 'I-'+str(n), 'revision': 1, 'attempt': 1,
                'synthetic': True, 'status': status, 'reason': None, 'job_state': status}
               for n, status in enumerate(statuses, 1)]
    return {'worker_id': 'watch-worker', 'execution_mode': 'synthetic', 'verification': 'contract_only',
            'stop_reason': stop_reason or ('job_limit' if results else 'idle'),
            'attempted_jobs': len(results), 'results': results}


class SupervisorFixture(unittest.TestCase):
    def setUp(self):
        local = Path(__file__).resolve().parents[1]/'.local/supervisor-tests'
        local.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=local)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inbox = self.root/'inbox'
        self.inbox.mkdir()
        self.store = Store(self.root/'state')
        register_source(self.store, 'SYN', self.inbox, synthetic=True, settle_seconds=.001)

    def put(self, bundle='one', text=TEXT):
        folder = self.inbox/bundle
        folder.mkdir(exist_ok=True)
        (folder/'request.txt').write_text(text, encoding='utf-8')

    def run_supervisor(self, **kwargs):
        config = {'worker_id': 'watch-worker', 'poll_seconds': .02,
                  'provider_timeout_seconds': 3, 'lease_seconds': 5}
        config.update(kwargs)
        return run_intake_supervisor(self.store, ['SYN'], SyntheticTextProvider(), **config)

    def counts(self):
        with self.store.connection() as con:
            return {table: con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                    for table in ('intake_revisions', 'intake_notifications', 'cases', 'plans', 'intake_responses')}

    def assert_public(self, result):
        self.assertEqual(set(result), FIELDS)
        self.assertEqual(result['kind'], 'bounded_intake_supervisor')
        self.assertEqual(result['mode'], 'fixture_only')
        self.assertEqual(result['analysis_scope'], 'all_synthetic_jobs')
        self.assertIs(result['synthetic'], True)
        for key in ('hardware_verified', 'ai_model_called', 'resumable'):
            self.assertIs(result[key], False)
        for key in ('cycles', 'scanned_sources', 'accepted_revisions', 'analyzed_jobs'):
            self.assertIs(type(result[key]), int)
            self.assertGreaterEqual(result[key], 0)
        encoded = json.dumps(result)
        self.assertNotIn(CANARY, encoded)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn('token', encoded)


class SupervisorActualTests(SupervisorFixture):
    def test_two_actual_cycles_accept_and_analyze_labelled_text_without_authority(self):
        self.put()
        result = self.run_supervisor()
        self.assert_public(result)
        self.assertEqual((result['cycles'], result['scanned_sources'], result['accepted_revisions'], result['analyzed_jobs']),
                         (2, 2, 1, 1))
        self.assertEqual(result['stop_reason'], 'cycle_limit')
        self.assertIsNone(result['error_code'])
        with self.store.connection() as con:
            intake = dict(con.execute('SELECT * FROM intakes').fetchone())
            job = dict(con.execute('SELECT * FROM intake_jobs').fetchone())
        self.assertEqual(job['state'], 'completed')
        self.assertEqual(intake['status'], 'analyzed')
        self.assertEqual((intake['delegated'], intake['deferred']), (0, 0))
        self.assertEqual(self.counts(), {'intake_revisions': 1, 'intake_notifications': 1,
                                      'cases': 0, 'plans': 0, 'intake_responses': 0})

    def test_repeated_invocations_do_not_duplicate_revisions_jobs_or_notifications(self):
        self.put()
        self.run_supervisor()
        before = self.counts()
        result = self.run_supervisor()
        self.assertEqual((result['accepted_revisions'], result['analyzed_jobs']), (0, 0))
        self.assertEqual(self.counts(), before)
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM intake_jobs').fetchone()[0], 1)

    def test_new_bundle_during_wait_is_discovered_and_settles_next_cycle(self):
        self.put()
        written = []
        def sleep(seconds):
            if not written:
                self.put('two', TEXT.replace('WATCH-FIXTURE', 'SECOND-FIXTURE'))
                written.append(True)
            time.sleep(seconds)
        with patch('labflow.intake_supervisor.sleep', side_effect=sleep):
            result = self.run_supervisor(max_cycles=3)
        self.assertEqual((result['cycles'], result['accepted_revisions'], result['analyzed_jobs']), (3, 2, 2))
        self.assertEqual(self.counts()['intake_revisions'], 2)

    def test_settle_policy_is_preserved_instead_of_forcing_acceptance(self):
        second = self.root/'slow-inbox'
        second.mkdir()
        (second/'bundle').mkdir()
        (second/'bundle/request.txt').write_text(TEXT, encoding='utf-8')
        register_source(self.store, 'SLOW', second, synthetic=True, settle_seconds=60)
        result = run_intake_supervisor(self.store, ['SLOW'], SyntheticTextProvider(), worker_id='watch-worker',
                                      max_cycles=2, poll_seconds=.001)
        self.assertEqual((result['accepted_revisions'], result['analyzed_jobs']), (0, 0))
        self.assertEqual(self.counts()['intake_revisions'], 0)
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT settle_seconds FROM intake_sources WHERE source_id=?', ('SLOW',)).fetchone()[0], 60)

    def test_actual_queued_and_expired_running_real_jobs_are_unchanged(self):
        self.put()
        real = self.root/'real-inbox'
        (real/'real').mkdir(parents=True)
        (real/'real/request.txt').write_text(TEXT+'manufacturer: REAL-CANARY\n', encoding='utf-8')
        register_source(self.store, 'REAL', real, synthetic=False, settle_seconds=.001)
        scan_source(self.store, 'REAL', now=100)
        scan_source(self.store, 'REAL', now=101)
        def real_job():
            with self.store.connection() as con:
                return dict(con.execute('SELECT j.* FROM intake_jobs j JOIN intakes i USING(intake_id) WHERE i.source_id=?',
                                        ('REAL',)).fetchone())
        queued = real_job()
        self.assertEqual(self.run_supervisor()['analyzed_jobs'], 1)
        self.assertEqual(real_job(), queued)
        claimed = claim_job(self.store, 'real-owner', now=102, lease_seconds=1)
        self.assertEqual(claimed['job_id'], queued['job_id'])
        expired = real_job()
        self.run_supervisor()
        self.assertEqual(real_job(), expired)

    def test_existing_job_of_an_unselected_synthetic_source_is_in_analysis_scope(self):
        other = self.root/'other-synthetic'
        (other/'bundle').mkdir(parents=True)
        (other/'bundle/request.txt').write_text(TEXT+'manufacturer: OTHER-FIXTURE\n', encoding='utf-8')
        register_source(self.store, 'OTHER-SYN', other, synthetic=True, settle_seconds=.001)
        scan_source(self.store, 'OTHER-SYN', now=100)
        scan_source(self.store, 'OTHER-SYN', now=101)
        with patch('labflow.intake_supervisor.scan_source', wraps=scan_source) as scan:
            result = self.run_supervisor(max_cycles=1)
        self.assert_public(result)
        self.assertEqual((result['scanned_sources'], result['accepted_revisions'], result['analyzed_jobs']), (1, 0, 1))
        self.assertEqual([call.args[1] for call in scan.call_args_list], ['SYN'])
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT state FROM intake_jobs').fetchone()[0], 'completed')

    def test_provider_failure_stops_and_preserves_actual_attempt(self):
        self.put()
        result = run_intake_supervisor(self.store, ['SYN'], RaisingProvider(), worker_id='watch-worker',
                                      max_cycles=4, poll_seconds=.02, max_jobs_per_cycle=1)
        self.assert_public(result)
        self.assertEqual(result['stop_reason'], 'worker_error')
        self.assertEqual((result['cycles'], result['analyzed_jobs']), (2, 1))
        with self.store.connection() as con:
            row = dict(con.execute('SELECT * FROM intake_jobs').fetchone())
        self.assertEqual(row['attempt'], 1)
        self.assertEqual(row['error_code'], 'model_error')

    def test_pdf_pages_use_actual_integrated_provider_when_dependency_is_available(self):
        try:
            from labflow import intake_documents
        except ImportError:
            self.skipTest('PDF document/worker integration is supplied by the coordinator')
        self.assertIsNotNone(intake_documents)
        from reportlab.pdfgen import canvas
        folder = self.inbox/'pdf-bundle'
        folder.mkdir()
        pdf = canvas.Canvas(str(folder/'request.pdf'))
        for lines in [('product_type: remote_control', 'model: WATCH-PDF'),
                      ('market: EU', 'purpose: synthetic evaluation')]:
            text = pdf.beginText(40, 790)
            for line in lines:
                text.textLine(line)
            pdf.drawText(text)
            pdf.showPage()
        pdf.save()
        result = self.run_supervisor()
        self.assertEqual((result['accepted_revisions'], result['analyzed_jobs']), (1, 1))
        with self.store.connection() as con:
            submitted = json.loads(con.execute('SELECT result_json FROM intake_jobs').fetchone()[0])['submission']
        self.assertEqual(submitted['schema_version'], 2)
        market = next(item for item in submitted['facts'] if item['field'] == 'market')
        self.assertEqual(market['evidence'][0]['kind'], 'pdf_page')
        self.assertEqual(market['evidence'][0]['page_number'], 2)

    def test_actual_provider_child_timeout_ends_watch_without_resetting_attempt(self):
        self.put()
        started = time.monotonic()
        result = run_intake_supervisor(self.store, ['SYN'], BlockingProvider(), worker_id='watch-worker',
                                      max_cycles=3, poll_seconds=.02, provider_timeout_seconds=.08)
        self.assertLess(time.monotonic()-started, 3)
        self.assertEqual((result['stop_reason'], result['analyzed_jobs'], result['cycles']), ('worker_error', 1, 2))
        with self.store.connection() as con:
            row = dict(con.execute('SELECT * FROM intake_jobs').fetchone())
        self.assertEqual((row['attempt'], row['state'], row['error_code']), (1, 'queued', 'model_error'))


class SupervisorBoundaryTests(SupervisorFixture):
    def setUp(self):
        super().setUp()
        self.clock = Clock()
        self.addCleanup(patch.stopall)
        self.scan = patch('labflow.intake_supervisor.scan_source', return_value={
            'accepted': [], 'pending': [], 'issues': []}).start()
        self.worker = patch('labflow.intake_supervisor.run_worker', return_value=worker_result()).start()
        patch('labflow.intake_supervisor.monotonic', side_effect=self.clock.monotonic).start()
        patch('labflow.intake_supervisor.sleep', side_effect=self.clock.sleep).start()

    def test_invalid_limits_and_callback_reject_before_scan_and_claim(self):
        changes = [{'max_cycles': 0}, {'max_cycles': 1025}, {'max_cycles': True}, {'max_cycles': 1.5},
                   {'max_jobs_per_cycle': 101}, {'max_jobs_per_cycle': 0}, {'max_jobs_per_cycle': True},
                   {'max_run_seconds': 0}, {'max_run_seconds': 3601}, {'max_run_seconds': float('nan')},
                   {'provider_timeout_seconds': True}, {'provider_timeout_seconds': 3601},
                   {'poll_seconds': 0}, {'poll_seconds': 60.1}, {'poll_seconds': float('inf')},
                   {'lease_seconds': 0}, {'lease_seconds': 3601}, {'lease_seconds': True},
                   {'worker_id': '../'+CANARY}, {'can_continue': False}]
        for values in changes:
            with self.subTest(keys=list(values)), self.assertRaises(ValueError) as raised:
                self.run_supervisor(**values)
            self.assertNotIn(CANARY, str(raised.exception))
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_all_sources_are_validated_before_the_first_scan(self):
        real = self.root/'real'
        real.mkdir()
        register_source(self.store, 'REAL', real, synthetic=False, settle_seconds=1)
        for ids in [[], ['SYN', 'SYN'], ['SYN', 'UNKNOWN'], ['SYN', 'REAL'], 'SYN',
                    ['SYN']*9, ['../'+CANARY], {'SYN'}]:
            with self.subTest(kind=type(ids).__name__), self.assertRaises(ValueError) as raised:
                run_intake_supervisor(self.store, ids, SyntheticTextProvider(), worker_id='watch-worker')
            self.assertNotIn(CANARY, str(raised.exception))
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_unsupported_or_broken_provider_is_preflighted_without_scan(self):
        for provider in [object(), ModelProvider(), InvalidProvider()]:
            with self.subTest(kind=type(provider).__name__), self.assertRaises(ValueError) as raised:
                run_intake_supervisor(self.store, ['SYN'], provider, worker_id='watch-worker')
            self.assertNotIn(CANARY, str(raised.exception))
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_callback_false_exception_and_nonbool_latch_before_scan(self):
        for outcome in [False, None, 1, CANARY, RuntimeError(CANARY)]:
            calls = []
            def callback():
                calls.append(True)
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome if len(calls) == 1 else True
            result = self.run_supervisor(can_continue=callback)
            self.assert_public(result)
            self.assertEqual(result['stop_reason'], 'supervisor_stop')
            self.assertEqual((result['cycles'], result['scanned_sources'], len(calls)), (0, 0, 1))
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_callback_time_is_included_before_dispatch(self):
        def callback():
            self.clock.now += 2
            return True
        result = self.run_supervisor(max_run_seconds=1, can_continue=callback)
        self.assertEqual(result['stop_reason'], 'time_limit')
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_stop_between_sources_does_not_call_second_scan_or_worker(self):
        other = self.root/'other'
        other.mkdir()
        register_source(self.store, 'SECOND', other, synthetic=True, settle_seconds=1)
        result = run_intake_supervisor(self.store, ('SYN', 'SECOND'), SyntheticTextProvider(), worker_id='watch-worker',
                                      can_continue=lambda: self.scan.call_count == 0)
        self.assertEqual((result['cycles'], result['scanned_sources']), (1, 1))
        self.assertEqual(result['stop_reason'], 'supervisor_stop')
        self.worker.assert_not_called()

    def test_deadline_after_scan_prevents_worker_and_next_source(self):
        def scan(*args):
            self.clock.now = 1
            return {'accepted': [], 'pending': [], 'issues': []}
        self.scan.side_effect = scan
        result = self.run_supervisor(max_run_seconds=1)
        self.assertEqual(result['stop_reason'], 'time_limit')
        self.assertEqual(result['scanned_sources'], 1)
        self.worker.assert_not_called()

    def test_wait_is_sliced_and_false_callback_interrupts_it(self):
        result = self.run_supervisor(poll_seconds=1, can_continue=lambda: self.clock.now < .25)
        self.assertEqual(result['stop_reason'], 'supervisor_stop')
        self.assertEqual(self.clock.sleeps, [.25])
        self.assertEqual((result['cycles'], self.scan.call_count, self.worker.call_count), (1, 1, 1))

    def test_no_wait_after_last_cycle_and_no_deadline_overshoot_from_wait(self):
        self.run_supervisor(max_cycles=1)
        self.assertEqual(self.clock.sleeps, [])
        self.scan.reset_mock()
        self.worker.reset_mock()
        result = self.run_supervisor(max_cycles=10, poll_seconds=1, max_run_seconds=.6)
        self.assertEqual(result['stop_reason'], 'time_limit')
        self.assertAlmostEqual(sum(self.clock.sleeps), .6)
        self.assertTrue(all(0 < seconds <= .25 for seconds in self.clock.sleeps))
        self.assertEqual(result['cycles'], 1)

    def test_worker_receives_remaining_monotonic_budget_and_limits(self):
        def scan(*args):
            self.clock.now += 2
            return {'accepted': [], 'pending': [], 'issues': []}
        self.scan.side_effect = scan
        result = self.run_supervisor(max_cycles=1, max_run_seconds=10, max_jobs_per_cycle=7,
                                     provider_timeout_seconds=20, lease_seconds=30)
        self.assertEqual(result['stop_reason'], 'cycle_limit')
        kwargs = self.worker.call_args.kwargs
        self.assertEqual((kwargs['max_jobs'], kwargs['max_run_seconds'], kwargs['provider_timeout_seconds'],
                          kwargs['lease_seconds']), (7, 8, 8, 30))

    def test_source_exception_preserves_attempt_count_and_redacts_raw_error(self):
        self.scan.side_effect = OSError(CANARY)
        result = self.run_supervisor()
        self.assert_public(result)
        self.assertEqual((result['cycles'], result['scanned_sources'], result['accepted_revisions']), (1, 1, 0))
        self.assertEqual(result['stop_reason'], 'source_error')
        self.worker.assert_not_called()

    def test_worker_exception_stops_without_raw_error_or_retry(self):
        self.worker.side_effect = OSError(CANARY)
        result = self.run_supervisor(max_cycles=10)
        self.assert_public(result)
        self.assertEqual((result['cycles'], result['analyzed_jobs']), (1, 0))
        self.assertEqual(result['stop_reason'], 'worker_error')
        self.assertEqual(self.worker.call_count, 1)

    def test_failed_worker_attempt_is_counted_but_not_reported_as_completion(self):
        self.worker.return_value = worker_result('completed', 'failed')
        result = self.run_supervisor(max_jobs_per_cycle=2)
        self.assertEqual(result['analyzed_jobs'], 2)
        self.assertEqual(result['stop_reason'], 'worker_error')
        self.assertEqual(result['cycles'], 1)

    def test_malformed_worker_counts_and_scan_results_are_rejected(self):
        self.scan.return_value = {'accepted': [CANARY], 'pending': [], 'issues': []}
        result = self.run_supervisor()
        self.assert_public(result)
        self.assertEqual(result['stop_reason'], 'source_error')
        self.assertEqual(result['accepted_revisions'], 0)
        self.scan.return_value = {'accepted': [], 'pending': [], 'issues': []}
        self.worker.return_value = {**worker_result('completed'), 'attempted_jobs': 2}
        result = self.run_supervisor()
        self.assert_public(result)
        self.assertEqual(result['stop_reason'], 'worker_error')
        self.assertEqual(result['analyzed_jobs'], 0)

    def test_preflight_time_consumes_budget_before_first_scan(self):
        def preflight(*args):
            self.clock.now += 2
        with patch('labflow.intake_supervisor._preflight', side_effect=preflight):
            result = self.run_supervisor(max_run_seconds=1)
        self.assertEqual(result['stop_reason'], 'time_limit')
        self.assertEqual(result['cycles'], 0)
        self.scan.assert_not_called()

    def test_deadline_after_source_lookup_stops_before_scan_attempt(self):
        from labflow.intake_supervisor import _source_is_synthetic
        checks = []
        def delayed(*args):
            current = _source_is_synthetic(*args)
            checks.append(True)
            if len(checks) == 2:  # First is the whole-source preflight snapshot.
                self.clock.now += 2
            return current
        with patch('labflow.intake_supervisor._source_is_synthetic', side_effect=delayed):
            result = self.run_supervisor(max_run_seconds=1)
        self.assertEqual(result['stop_reason'], 'time_limit')
        self.assertEqual(result['scanned_sources'], 0)
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_source_loses_synthetic_scope_after_preflight_without_scanning_real_data(self):
        def callback():
            with self.store.connection() as con:
                con.execute('UPDATE intake_sources SET synthetic=0 WHERE source_id=?', ('SYN',))
            return True
        result = self.run_supervisor(can_continue=callback)
        self.assertEqual(result['stop_reason'], 'source_error')
        self.assertEqual(result['error_code'], 'source_scope_lost')
        self.scan.assert_not_called()
        self.worker.assert_not_called()

    def test_callback_stop_after_worker_does_not_wait_or_start_a_new_cycle(self):
        result = self.run_supervisor(can_continue=lambda: self.worker.call_count == 0)
        self.assertEqual(result['stop_reason'], 'supervisor_stop')
        self.assertEqual((result['cycles'], result['scanned_sources']), (1, 1))
        self.assertEqual(self.clock.sleeps, [])

    def test_source_and_worker_errors_preserve_preceding_confirmed_counts(self):
        other = self.root/'other'
        other.mkdir()
        register_source(self.store, 'SECOND', other, synthetic=True, settle_seconds=1)
        self.scan.side_effect = [{'accepted': [{'intake_id': 'I-one', 'revision': 1,
                                              'job_id': 'J-one', 'kind': 'new'}]}, OSError(CANARY)]
        result = run_intake_supervisor(self.store, ['SYN', 'SECOND'], SyntheticTextProvider(), worker_id='watch-worker')
        self.assert_public(result)
        self.assertEqual((result['cycles'], result['scanned_sources'], result['accepted_revisions']), (1, 2, 1))
        self.assertEqual(result['stop_reason'], 'source_error')
        self.worker.assert_not_called()

    def test_worker_state_error_and_scope_violation_are_not_hidden_as_idle(self):
        for report in [worker_result(stop_reason='state_error'), worker_result('completed')]:
            if report['results']:
                report['results'][0]['synthetic'] = False
            self.worker.return_value = report
            result = self.run_supervisor(max_cycles=10)
            self.assert_public(result)
            self.assertEqual(result['stop_reason'], 'worker_error')
            self.assertEqual(result['cycles'], 1)

    def test_wait_exception_is_sanitized_and_does_not_restart(self):
        with patch('labflow.intake_supervisor.sleep', side_effect=OSError(CANARY)):
            result = self.run_supervisor()
        self.assert_public(result)
        self.assertEqual((result['stop_reason'], result['error_code']), ('supervisor_stop', 'wait_interrupted'))
        self.assertEqual((self.scan.call_count, self.worker.call_count), (1, 1))


if __name__ == '__main__':
    unittest.main()
