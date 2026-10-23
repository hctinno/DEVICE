"""State and provenance acceptance for the lead-owned fixture queue."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job, complete_job, respond
from labflow.intake_fixture_jobs import (
    fixture_readiness, request_fixture_job, claim_fixture_job,
    fixture_lease_current, complete_fixture_job, fail_fixture_job,
)
from labflow.store import Store, canonical
from labflow.virtual_fleet.journal import OperatorJournal


class FixtureQueueTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inbox = self.root / 'inbox'
        self.inbox.mkdir()
        self.store = Store(self.root / 'state')
        self.intake_id = self.ready_intake()

    def ready_intake(self, *, synthetic=True, bundle='request', model='SM-A176U'):
        source = 'source-' + bundle
        inbox = self.inbox / source
        inbox.mkdir()
        folder = inbox / bundle
        folder.mkdir()
        lines = ['product_type: smartphone', 'market: US', 'purpose: certification', 'model: ' + model,
                 'request_source: ' + bundle]
        (folder / 'request.txt').write_text('\n'.join(lines), encoding='utf-8')
        register_source(self.store, source, inbox, synthetic=synthetic, settle_seconds=1)
        scan_source(self.store, source, now=100)
        intake_id = scan_source(self.store, source, now=101)['accepted'][0]['intake_id']
        job = claim_job(self.store, 'analysis', now=102)
        document = job['documents'][0]
        facts = [{'field': field, 'value': value, 'status': 'explicit', 'evidence': [{
            'path': document['path'], 'sha256': document['sha256'], 'line_start': n,
            'line_end': n, 'quote': lines[n - 1], 'role': 'request'}]}
            for n, (field, value) in enumerate(zip(
                ['product_type', 'market', 'purpose', 'model'],
                ['smartphone', 'US', 'certification', model]), 1)]
        complete_job(self.store, job['job_id'], job['token'], {
            'schema_version': 1, 'producer': {'kind': 'fixture' if synthetic else 'manual', 'name': 'queue-test'},
            'identity': 'single', 'facts': facts, 'missing_fields': []}, now=103)
        respond(self.store, 'proceed-' + bundle, 'proceed', intake_id=intake_id)
        return intake_id

    def request(self, request_id='REQ-1', intake_id=None):
        intake_id = intake_id or self.intake_id
        ready = fixture_readiness(self.store, intake_id)
        return request_fixture_job(self.store, request_id, intake_id, expected_revision=ready['revision'],
            expected_readiness_fingerprint=ready['readiness_fingerprint'],
            recipe_id='conducted_sensor_fixture_v1', settings={'power_dbm': -4})

    def stored(self, request_id='REQ-1'):
        with self.store.connection() as con:
            return dict(con.execute('SELECT * FROM intake_fixture_jobs WHERE request_id=?', (request_id,)).fetchone())

    def evidence(self, claim):
        report = {'schema_version': 1, 'kind': 'virtual_fleet_harness_result',
            'run_id': claim['run_id'], 'runtime_instance_id': claim['runtime_instance_id'],
            'synthetic': True, 'hardware_verified': False, 'ai_model_called': False,
            'policy': {'kind': 'fixture', 'id': 'rf_sensor_v1'},
            'termination': {'reason': 'policy_stop', 'policy_claim': 'blocked'},
            'task_outcome': 'not_assessed', 'cleanup': {'status': 'not_assessed', 'evidence_refs': []},
            'usage': {'decisions': 1, 'logical_requests': 0, 'transport_retries': 0,
                      'tick_delta': 0, 'reserved_ticks': 0, 'elapsed_ms': 1},
            'evidence': {'measurement_refs': [], 'operator_transcript_ref': 'artifact:operator_events'},
            'unresolved_request_ids': [], 'assessment': {'status': 'not_assessed', 'verdict': None,
                'evaluator_id': None, 'evidence_refs': [], 'summary_code': None}}
        folder = self.root / claim['run_id']
        folder.mkdir()
        journal_path = folder / 'operator.jsonl'
        with OperatorJournal(journal_path, run_id=claim['run_id'], runtime_instance_id=claim['runtime_instance_id'],
            provenance={'runtime_origin': 'preinitialized', 'catalog_sha256': 'a' * 64,
                        'topology_sha256': 'b' * 64, 'engine_sha256': 'c' * 64}) as journal:
            journal({'schema_version': 1, 'kind': 'operator_event', 'event_id': 'event:1',
                'run_id': claim['run_id'], 'runtime_instance_id': claim['runtime_instance_id'],
                'sequence': 1, 'type': 'termination',
                'payload': {'code': 'run_terminated', 'unresolved_request_ids': []}})
        result_path = folder / 'result.json'
        result_path.write_text(canonical(report), encoding='utf-8')
        artifacts = []
        for kind, path in [('result', result_path), ('operator_journal', journal_path)]:
            sha = self.store.import_artifact(path, 'fixture_' + kind, synthetic=True)
            artifacts.append({'kind': kind, 'artifact_id': 'blob:' + sha, 'sha256': sha, 'bytes': path.stat().st_size})
        return report, artifacts

    def test_readiness_reuses_actual_delegation_and_is_read_only(self):
        with self.store.connection() as con:
            before = con.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        a = fixture_readiness(self.store, self.intake_id)
        b = fixture_readiness(Store(self.store.root), self.intake_id)
        self.assertTrue(a['ready'])
        self.assertEqual(a['delegation_event_id'], 'proceed-request')
        self.assertEqual(a, b)
        self.assertRegex(a['readiness_fingerprint'], r'^[a-f0-9]{64}$')
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM events').fetchone()[0], before)

    def test_same_id_same_body_is_idempotent_changed_body_is_rejected(self):
        first = self.request()
        self.assertEqual(first['request_id'], self.request()['request_id'])
        ready = fixture_readiness(self.store, self.intake_id)
        with self.assertRaises(ValueError):
            request_fixture_job(self.store, 'REQ-1', self.intake_id, expected_revision=ready['revision'],
                expected_readiness_fingerprint=ready['readiness_fingerprint'],
                recipe_id='conducted_sensor_fixture_v1', settings={'power_dbm': 5})
        self.assertEqual(self.stored()['state'], 'queued')

    def test_bad_permission_and_selection_never_enqueue(self):
        ready = fixture_readiness(self.store, self.intake_id)
        for settings in [{'power_dbm': True}, {'power_dbm': float('nan')}, {'power_dbm': 21},
                         {'power_dbm': -4, 'seed': 17}, {'frequency_hz': 2.45e9}]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                request_fixture_job(self.store, 'BAD', self.intake_id, expected_revision=ready['revision'],
                    expected_readiness_fingerprint=ready['readiness_fingerprint'],
                    recipe_id='conducted_sensor_fixture_v1', settings=settings)
        respond(self.store, 'defer-request', 'defer', intake_id=self.intake_id)
        self.assertFalse(fixture_readiness(self.store, self.intake_id)['ready'])
        with self.assertRaises(ValueError):
            self.request()
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM intake_fixture_jobs').fetchone()[0], 0)

    def test_same_revision_answer_changes_snapshot_and_supersedes_queued_request(self):
        self.request()
        before = fixture_readiness(self.store, self.intake_id)
        respond(self.store, 'answer-request', 'answer', intake_id=self.intake_id, answers={'model': 'SM-A176U'})
        after = fixture_readiness(self.store, self.intake_id)
        self.assertEqual(before['revision'], after['revision'])
        self.assertNotEqual(before['readiness_fingerprint'], after['readiness_fingerprint'])
        self.assertIsNone(claim_fixture_job(self.store, 'worker', now=200))
        self.assertEqual(self.stored()['state'], 'superseded')

    def test_two_workers_cannot_claim_one_request(self):
        self.request()
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda n: claim_fixture_job(self.store, 'worker-' + str(n), now=200), [1, 2]))
        self.assertEqual(sum(value is not None for value in claims), 1)
        claim = next(value for value in claims if value is not None)
        self.assertTrue(fixture_lease_current(self.store, claim['request_id'], claim['token'], now=201))
        self.assertIsNotNone(claim['run_id'])
        self.assertIsNotNone(claim['runtime_instance_id'])

    def test_expired_running_request_becomes_uncertain_and_is_never_reclaimed(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200, lease_seconds=2)
        self.assertFalse(fixture_lease_current(self.store, 'REQ-1', claim['token'], now=202))
        self.assertIsNone(claim_fixture_job(Store(self.store.root), 'worker-new', now=202))
        self.assertEqual(self.stored()['state'], 'uncertain')
        self.assertIsNone(claim_fixture_job(self.store, 'worker-new', now=900))
        self.assertEqual(self.stored()['run_id'], claim['run_id'])

    def test_changed_readiness_during_execution_prevents_current_success(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200)
        report, artifacts = self.evidence(claim)
        respond(self.store, 'defer-request', 'defer', intake_id=self.intake_id)
        self.assertFalse(fixture_lease_current(self.store, 'REQ-1', claim['token'], now=201))
        result = complete_fixture_job(self.store, 'REQ-1', claim['token'], report, artifacts, now=201)
        self.assertEqual(result['state'], 'uncertain')
        self.assertNotEqual(self.stored()['state'], 'completed')
        for item in artifacts:
            self.assertTrue(self.store.verify_blob(item['sha256']).is_file())

    def test_valid_evidence_publication_is_idempotent_and_keeps_task_unassessed(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200)
        report, artifacts = self.evidence(claim)
        result = complete_fixture_job(self.store, 'REQ-1', claim['token'], report, artifacts, now=201)
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result, complete_fixture_job(self.store, 'REQ-1', claim['token'], report, artifacts, now=500))
        saved = json.loads(self.stored()['result_json'])
        self.assertEqual(saved['report']['task_outcome'], 'not_assessed')
        self.assertEqual(saved['report']['termination']['policy_claim'], 'blocked')
        self.assertIsNone(claim_fixture_job(self.store, 'other-worker', now=501))

    def test_wrong_report_or_artifact_identity_never_publishes(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200)
        report, artifacts = self.evidence(claim)
        variants = []
        other = deepcopy(report); other['run_id'] = 'another-run'; variants.append((other, artifacts))
        other = deepcopy(artifacts); other[0]['sha256'] = '0' * 64; variants.append((report, other))
        other = deepcopy(artifacts); other[0]['bytes'] += 1; variants.append((report, other))
        other = deepcopy(artifacts); other[0]['path'] = 'C:/private'; variants.append((report, other))
        for candidate, refs in variants:
            with self.subTest(candidate=candidate['run_id'], refs=refs), self.assertRaises(ValueError):
                complete_fixture_job(self.store, 'REQ-1', claim['token'], candidate, refs, now=201)
            self.assertEqual(self.stored()['state'], 'running')

    def test_source_provenance_and_virtual_provenance_are_independent(self):
        real = self.ready_intake(synthetic=False, bundle='real')
        request = self.request('REAL-1', intake_id=real)
        self.assertIs(request['source_synthetic'], False)
        claim = claim_fixture_job(self.store, 'worker', now=200)
        report, artifacts = self.evidence(claim)
        complete_fixture_job(self.store, 'REAL-1', claim['token'], report, artifacts, now=201)
        self.assertTrue(json.loads(self.stored('REAL-1')['result_json'])['report']['synthetic'])
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM cases').fetchone()[0], 0)

    def test_failure_records_preserve_dispatch_uncertainty_without_retry(self):
        for n, dispatched, expected in [(1, False, 'failed'), (2, True, 'uncertain')]:
            key = 'REQ-' + str(n)
            self.request(key)
            claim = claim_fixture_job(self.store, 'worker', now=200)
            result = fail_fixture_job(self.store, key, claim['token'], 'execution_failed', dispatched=dispatched, now=201)
            self.assertEqual(result['state'], expected)
            self.assertIsNone(claim_fixture_job(self.store, 'worker-new', now=202))

    def test_modified_source_blob_blocks_request_without_queue_write(self):
        with self.store.connection() as con:
            files = json.loads(con.execute('SELECT files_json FROM intake_revisions WHERE intake_id=?', (self.intake_id,)).fetchone()[0])
        self.store.blob_path(files[0]['sha256']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.request()
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM intake_fixture_jobs').fetchone()[0], 0)

    def test_caller_mutation_during_artifact_io_cannot_enter_saved_metadata(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200)
        report, artifacts = self.evidence(claim)
        original = deepcopy(artifacts)
        verify = self.store.verify_blob
        def mutate_caller(sha):
            artifacts[0]['sha256'] = '0' * 64
            artifacts[0]['path'] = 'C:/private-caller-mutation'
            return verify(sha)
        with patch.object(self.store, 'verify_blob', side_effect=mutate_caller):
            complete_fixture_job(self.store, 'REQ-1', claim['token'], report, artifacts, now=201)
        saved = json.loads(self.stored()['result_json'])['artifacts']
        self.assertEqual(saved, sorted(original, key=lambda item: item['kind']))

    def test_caller_report_mutation_cannot_replace_the_validated_report_identity(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200)
        other = {**claim, 'run_id': 'another-run', 'runtime_instance_id': 'another-instance'}
        report, artifacts = self.evidence(other)
        verify = self.store.verify_blob
        def mutate_caller(sha):
            report['run_id'], report['runtime_instance_id'] = claim['run_id'], claim['runtime_instance_id']
            return verify(sha)
        with patch.object(self.store, 'verify_blob', side_effect=mutate_caller), self.assertRaises(ValueError):
            complete_fixture_job(self.store, 'REQ-1', claim['token'], report, artifacts, now=201)
        self.assertEqual(self.stored()['state'], 'running')

    def test_lease_expiring_during_readiness_query_cannot_return_true(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200, lease_seconds=2)
        from labflow import intake_fixture_jobs as module
        current = module._current
        clock = [201]
        def slow_query(con, row):
            result = current(con, row)
            clock[0] = 203
            return result
        with patch.object(module, 'timestamp', side_effect=lambda value=None: clock[0]), \
                patch.object(module, '_current', side_effect=slow_query):
            self.assertFalse(fixture_lease_current(self.store, 'REQ-1', claim['token']))

    def test_lease_expiring_during_publication_readiness_cannot_complete(self):
        self.request()
        claim = claim_fixture_job(self.store, 'worker', now=200, lease_seconds=2)
        report, artifacts = self.evidence(claim)
        from labflow import intake_fixture_jobs as module
        current = module._current
        clock = [201]
        def slow_query(con, row):
            result = current(con, row)
            clock[0] = 203
            return result
        with patch.object(module, 'timestamp', side_effect=lambda value=None: clock[0]), \
                patch.object(module, '_current', side_effect=slow_query):
            result = complete_fixture_job(self.store, 'REQ-1', claim['token'], report, artifacts)
        self.assertEqual(result['state'], 'uncertain')
        self.assertEqual(result['error_code'], 'lease_expired')


if __name__ == '__main__':
    unittest.main()
