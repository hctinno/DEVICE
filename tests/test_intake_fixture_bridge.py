"""Synthetic queue/adapter/store contracts; no real intake or equipment."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from labflow.intake_fixture_bridge import run_fixture_worker
from labflow.virtual_fleet.journal import OperatorJournal


SECRET = 'PRIVATE_BRIDGE_EXCEPTION_CANARY'


def job(**changes):
    value = {'request_id': 'Q-synthetic', 'intake_id': 'I-synthetic', 'revision': 2,
             'readiness_fingerprint': 'a'*64, 'revision_fingerprint': 'b'*64,
             'delegation_event_id': 'proceed-synthetic', 'recipe_id': 'conducted_sensor_fixture_v1',
             'settings': {'power_dbm': 5.5}, 'model': 'SM-A176U', 'source_synthetic': True,
             'run_id': 'run-synthetic', 'runtime_instance_id': 'instance-synthetic',
             'token': 'PRIVATE_LEASE_CANARY', 'lease_until': 9999999999.0}
    value.update(changes)
    return value


def report(run_id, instance_id):
    return {'schema_version': 1, 'kind': 'virtual_fleet_harness_result', 'run_id': run_id,
            'runtime_instance_id': instance_id, 'synthetic': True, 'hardware_verified': False,
            'ai_model_called': False, 'policy': {'kind': 'fixture', 'id': 'synthetic'},
            'termination': {'reason': 'policy_stop', 'policy_claim': 'blocked'},
            'task_outcome': 'not_assessed', 'cleanup': {'status': 'not_assessed', 'evidence_refs': []},
            'usage': {'decisions': 1, 'logical_requests': 0, 'transport_retries': 0,
                      'tick_delta': 0, 'reserved_ticks': 0, 'elapsed_ms': 1.25},
            'evidence': {'measurement_refs': [], 'operator_transcript_ref': 'artifact:operator_events'},
            'unresolved_request_ids': [], 'assessment': {'status': 'not_assessed', 'verdict': None,
                'evaluator_id': None, 'evidence_refs': [], 'summary_code': None}}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode('utf-8')


def metadata(kind, path):
    data = path.read_bytes()
    return {'kind': kind, 'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def padded_output_root(base, minimum_length=100):
    length = max(minimum_length, len(str(base))+16)
    return base/('runs-'+('x'*(length-len(str(base))-6)))


def artifacts(result, folder):
    path = folder/'public-result.json'
    path.write_bytes(json_bytes(result['report']))
    result['artifacts'] = [metadata('result', path), metadata('operator_journal', folder/'operator/events.jsonl')]
    return result


def produce(request, output_dir, *, run_id, runtime_instance_id, can_continue=None,
            journal_instance=None, complete=True):
    assert can_continue is not None and can_continue() is True
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'operator').mkdir()
    provenance = {'runtime_origin': 'preinitialized', 'catalog_sha256': '1'*64,
                  'topology_sha256': '2'*64, 'engine_sha256': '3'*64}
    with OperatorJournal(folder/'operator/events.jsonl', run_id=run_id,
                         runtime_instance_id=journal_instance or runtime_instance_id, provenance=provenance) as journal:
        base = {'schema_version': 1, 'kind': 'operator_event', 'run_id': run_id,
                'runtime_instance_id': journal_instance or runtime_instance_id}
        journal({**base, 'event_id': 'event:1', 'sequence': 1, 'type': 'observation',
                 'payload': {'observation': {'tick': 0, 'setup_revision': 0, 'synthetic': True,
                             'hardware_verified': False, 'devices': {}}}})
        if complete:
            journal({**base, 'event_id': 'event:2', 'sequence': 2, 'type': 'termination',
                     'payload': {'code': 'run_terminated', 'unresolved_request_ids': []}})
    result = {'report': report(run_id, runtime_instance_id), 'artifacts': []}
    return artifacts(result, folder)


class Queue:
    def __init__(self, *jobs):
        self.jobs = [copy.deepcopy(value) for value in jobs]
        self.current = True
        self.claims, self.checks, self.completed, self.failed = [], [], [], []
        self.complete_error = self.fail_error = self.claim_error = False

    def claim_fixture_job(self, store, worker_id, *, lease_seconds=120, now=None):
        self.claims.append((worker_id, lease_seconds))
        if self.claim_error:
            raise OSError(SECRET)
        return self.jobs.pop(0) if self.jobs else None

    def fixture_lease_current(self, store, request_id, token, *, now=None):
        self.checks.append((request_id, token))
        return self.current

    def complete_fixture_job(self, store, request_id, token, public_report, public_artifacts, *, now=None):
        self.completed.append((request_id, token, copy.deepcopy(public_report), copy.deepcopy(public_artifacts)))
        if self.complete_error:
            raise OSError(SECRET)
        return {'state': 'completed'}

    def fail_fixture_job(self, store, request_id, token, code, *, dispatched=False, now=None):
        self.failed.append((request_id, token, code, dispatched))
        if self.fail_error:
            raise OSError(SECRET)
        return {'state': 'uncertain' if dispatched else 'failed'}


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir()
        self.imports, self.flags = [], {}
        self.import_error = False

    def import_artifact(self, path, kind='raw', *, synthetic=False):
        self.imports.append((str(path), kind, synthetic))
        if self.import_error:
            raise OSError(SECRET)
        data = Path(path).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        destination = self.root/sha
        if not destination.exists():
            destination.write_bytes(data)
        self.flags[sha] = synthetic
        return sha

    def verify_blob(self, sha):
        path = self.root/sha
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(SECRET)
        return path

    def evidence_is_synthetic(self, sha):
        return self.flags.get(sha, False)


class IntakeFixtureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = Store(self.root/'blobs')
        self.queue = Queue(job())
        self.calls = []

    def executor(self, request, output_dir, **kwargs):
        self.calls.append((copy.deepcopy(request), Path(output_dir), kwargs))
        return produce(request, output_dir, **kwargs)

    def run_worker(self, executor=None, **kwargs):
        with patch('labflow.intake_fixture_bridge._queue_api', return_value=self.queue):
            return run_fixture_worker(self.store, worker_id='worker-synthetic', output_root=self.root/'runs',
                                      executor=executor or self.executor, **kwargs)

    def assert_uncertain(self, result):
        self.assertEqual(result['results'][0]['state'], 'uncertain')
        self.assertFalse(self.queue.completed)
        self.assertTrue(self.queue.failed[-1][3])
        encoded = json.dumps(result)
        self.assertNotIn(SECRET, encoded)
        self.assertNotIn('PRIVATE_LEASE_CANARY', encoded)
        self.assertNotIn(str(self.root), encoded)

    def test_one_claim_one_executor_validated_synthetic_blobs_and_cas_metadata(self):
        result = self.run_worker()
        self.assertEqual(result['results'][0]['state'], 'completed')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(set(self.calls[0][0]), {'request_id', 'intake_id', 'revision', 'readiness_fingerprint',
                                              'recipe_id', 'settings', 'model', 'source_synthetic'})
        self.assertNotIn('token', self.calls[0][0])
        self.assertTrue(self.calls[0][1].is_dir())
        self.assertEqual(len(self.store.imports), 2)
        self.assertTrue(all(item[2] is True for item in self.store.imports))
        published = self.queue.completed[0][3]
        self.assertEqual({value['kind'] for value in published}, {'result', 'operator_journal'})
        for value in published:
            self.assertEqual(set(value), {'kind', 'artifact_id', 'sha256', 'bytes'})
            self.assertEqual(value['artifact_id'], 'blob:'+value['sha256'])
        self.assertFalse(self.queue.failed)
        self.assertNotIn('token', json.dumps(result))
        self.assertIs(result['synthetic'], True)
        self.assertIs(result['hardware_verified'], False)

    def test_blocked_or_unassessed_report_is_technical_completion_not_measurement_pass(self):
        result = self.run_worker()
        saved = self.queue.completed[0][2]
        self.assertEqual(saved['termination']['policy_claim'], 'blocked')
        self.assertEqual(saved['assessment']['status'], 'not_assessed')
        self.assertNotIn('measurement_success', json.dumps(result))

    def test_idle_has_no_runtime_or_output_creation(self):
        self.queue.jobs.clear()
        result = self.run_worker()
        self.assertEqual(result['attempted_jobs'], 0)
        self.assertFalse(self.calls)

    def test_invalid_configuration_does_not_claim(self):
        for changes in [{'max_jobs': 0}, {'max_jobs': True}, {'lease_seconds': 0},
                        {'lease_seconds': float('inf')}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_worker(**changes)
        self.assertFalse(self.queue.claims)

    def test_lease_lost_before_executor_records_predispatch_failure(self):
        self.queue.current = False
        result = self.run_worker()
        self.assertFalse(self.calls)
        self.assertFalse(self.queue.failed[0][3])
        self.assertFalse(self.queue.completed)
        self.assertIn(result['results'][0]['state'], {'failed', 'uncertain', 'superseded'})

    def test_callback_fence_is_latched_and_ignored_executor_cannot_publish(self):
        def executor(request, output_dir, **kwargs):
            value = produce(request, output_dir, **kwargs)
            self.queue.current = False
            self.assertIs(kwargs['can_continue'](), False)
            self.queue.current = True
            self.assertIs(kwargs['can_continue'](), False)
            return value
        self.assert_uncertain(self.run_worker(executor))

    def test_callback_queue_exception_stops_without_raw_exception(self):
        original = self.queue.fixture_lease_current
        def executor(request, output_dir, **kwargs):
            value = produce(request, output_dir, **kwargs)
            def broken(*args, **options):
                raise OSError(SECRET)
            self.queue.fixture_lease_current = broken
            self.assertIs(kwargs['can_continue'](), False)
            self.queue.fixture_lease_current = original
            return value
        self.assert_uncertain(self.run_worker(executor))

    def test_executor_exception_preserves_partial_folder_and_never_starts_next_job(self):
        self.queue.jobs.append(job(request_id='Q-next', run_id='run-next'))
        captured = []
        def executor(request, output_dir, **kwargs):
            kwargs['can_continue']()
            folder = Path(output_dir)
            folder.mkdir(parents=True)
            (folder/'partial.txt').write_text('synthetic failure', encoding='utf-8')
            captured.append(folder)
            raise RuntimeError(SECRET)
        self.assert_uncertain(self.run_worker(executor, max_jobs=2))
        self.assertEqual(len(captured), 1)
        self.assertTrue((captured[0]/'partial.txt').exists())
        self.assertEqual(len(self.queue.jobs), 1)

    def test_existing_run_folder_is_not_reused_or_overwritten(self):
        self.run_worker()
        folder = self.calls[0][1]
        before = (folder/'public-result.json').read_bytes()
        self.queue.jobs.append(job())
        second = self.run_worker()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((folder/'public-result.json').read_bytes(), before)
        self.assertFalse(self.queue.failed[-1][3])
        self.assertIn(second['results'][0]['state'], {'failed', 'uncertain'})

    def test_report_identity_provenance_and_unknown_fields_are_rejected(self):
        for change in [{'run_id': 'other'}, {'runtime_instance_id': 'other'}, {'synthetic': False},
                       {'hardware_verified': True}, {'ai_model_called': True}, {'seed': SECRET}]:
            with self.subTest(change=change):
                self.queue = Queue(job(request_id='Q-'+str(len(self.calls)), run_id='run-'+str(len(self.calls))))
                def executor(request, output_dir, **kwargs):
                    value = self.executor(request, output_dir, **kwargs)
                    value['report'].update(change)
                    return artifacts(value, Path(output_dir))
                self.assert_uncertain(self.run_worker(executor))

    def test_declared_hash_size_and_kind_sets_are_checked(self):
        for mutation in ['hash', 'bytes', 'duplicate', 'missing', 'unknown']:
            with self.subTest(mutation=mutation):
                self.queue = Queue(job(request_id='Q-'+mutation, run_id='run-'+mutation))
                def executor(request, output_dir, **kwargs):
                    value = self.executor(request, output_dir, **kwargs)
                    if mutation == 'hash': value['artifacts'][0]['sha256'] = '0'*64
                    elif mutation == 'bytes': value['artifacts'][0]['bytes'] += 1
                    elif mutation == 'duplicate': value['artifacts'][1] = copy.deepcopy(value['artifacts'][0])
                    elif mutation == 'missing': value['artifacts'].pop()
                    else: value['artifacts'][0]['extra'] = SECRET
                    return value
                self.assert_uncertain(self.run_worker(executor))

    def test_report_file_must_equal_returned_report(self):
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            value['report']['termination']['policy_claim'] = 'failed'
            return value
        self.assert_uncertain(self.run_worker(executor))

    def test_other_run_or_private_artifact_path_is_never_imported(self):
        for target in ['outside', 'private']:
            with self.subTest(target=target):
                self.queue = Queue(job(request_id='Q-'+target, run_id='run-'+target))
                previous = len(self.store.imports)
                def executor(request, output_dir, **kwargs):
                    value = self.executor(request, output_dir, **kwargs)
                    alternate = self.root/'outside.json' if target == 'outside' else Path(output_dir)/'private/author.json'
                    alternate.parent.mkdir(parents=True, exist_ok=True)
                    alternate.write_bytes(json_bytes(value['report']))
                    value['artifacts'][0] = metadata('result', alternate)
                    return value
                self.assert_uncertain(self.run_worker(executor))
                self.assertEqual(len(self.store.imports), previous)

    def test_journal_instance_and_incomplete_state_are_checked(self):
        for mutation in ['instance', 'incomplete', 'corrupt']:
            with self.subTest(mutation=mutation):
                self.queue = Queue(job(request_id='Q-'+mutation, run_id='run-'+mutation))
                def executor(request, output_dir, **kwargs):
                    if mutation == 'instance': kwargs['journal_instance'] = 'wrong-instance'
                    if mutation == 'incomplete': kwargs['complete'] = False
                    value = produce(request, output_dir, **kwargs)
                    if mutation == 'corrupt':
                        path = Path(output_dir)/'operator/events.jsonl'
                        path.write_bytes(path.read_bytes()[:-4])
                        value['artifacts'][1] = metadata('operator_journal', path)
                    return value
                self.assert_uncertain(self.run_worker(executor))

    def test_uncertain_or_unresolved_report_is_not_published_as_completed(self):
        for mutation in ['reason', 'pending']:
            self.queue = Queue(job(request_id='Q-'+mutation, run_id='run-'+mutation))
            def executor(request, output_dir, **kwargs):
                value = self.executor(request, output_dir, **kwargs)
                if mutation == 'reason':
                    value['report']['termination'] = {'reason': 'runtime_mutation_uncertain', 'policy_claim': None}
                else:
                    value['report']['unresolved_request_ids'] = ['request:pending']
                return artifacts(value, Path(output_dir))
            self.assert_uncertain(self.run_worker(executor))

    def test_import_or_cas_failure_keeps_files_and_stops_uncertain(self):
        for failure in ['import', 'publish']:
            self.queue = Queue(job(request_id='Q-'+failure, run_id='run-'+failure))
            self.store.import_error = failure == 'import'
            self.queue.complete_error = failure == 'publish'
            result = self.run_worker()
            self.assertEqual(result['results'][0]['state'], 'uncertain')
            self.assertTrue((self.calls[-1][1]/'public-result.json').exists())
            self.assertTrue(self.queue.failed[-1][3])

    def test_failed_failure_record_is_redacted_and_does_not_retry_execution(self):
        self.queue.fail_error = True
        def executor(*args, **kwargs):
            raise RuntimeError(SECRET)
        result = self.run_worker(executor)
        self.assertEqual(result['results'][0]['state'], 'uncertain')
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(len(self.queue.failed), 1)

    def test_claim_exception_is_state_error_and_no_executor(self):
        self.queue.claim_error = True
        result = self.run_worker()
        self.assertEqual(result['attempted_jobs'], 0)
        self.assertEqual(result['stop_reason'], 'state_error')
        self.assertFalse(self.calls)
        self.assertNotIn(SECRET, json.dumps(result))

    def test_real_input_flag_is_not_relabelled_but_outputs_are_synthetic(self):
        self.queue = Queue(job(source_synthetic=False))
        self.run_worker()
        self.assertIs(self.calls[0][0]['source_synthetic'], False)
        self.assertTrue(all(item[2] is True for item in self.store.imports))

    def test_two_distinct_claims_use_distinct_new_runtime_folders(self):
        self.queue.jobs.append(job(request_id='Q-next', run_id='run-next', runtime_instance_id='instance-next'))
        result = self.run_worker(max_jobs=2)
        self.assertEqual(result['attempted_jobs'], 2)
        self.assertEqual([value['state'] for value in result['results']], ['completed', 'completed'])
        self.assertNotEqual(self.calls[0][1], self.calls[1][1])
        self.assertEqual(len(self.calls), 2)

    def test_missing_or_malformed_claim_never_calls_executor(self):
        for key, value in [('run_id', '../escape'), ('runtime_instance_id', None),
                           ('run_id', 'x'*129), ('runtime_instance_id', 'y'*129),
                           ('revision', True), ('readiness_fingerprint', 'bad'),
                           ('source_synthetic', 1), ('settings', {'power_dbm': float('nan')})]:
            with self.subTest(key=key):
                self.queue = Queue(job(**{key: value}))
                result = self.run_worker()
                self.assertFalse(self.calls)
                self.assertFalse(self.queue.failed[-1][3])
                self.assertNotEqual(result['results'][0]['state'], 'completed')

    def test_state_returned_by_failure_cas_is_not_overwritten(self):
        self.queue.current = False
        with patch.object(self.queue, 'fail_fixture_job', return_value={'state': 'superseded'}):
            result = self.run_worker()
        self.assertEqual(result['results'][0]['state'], 'superseded')
        self.assertFalse(self.calls)

    def test_imported_bytes_must_still_match_validated_adapter_artifact(self):
        original = self.store.import_artifact
        def changing(path, kind='raw', *, synthetic=False):
            Path(path).write_bytes(b'changed synthetic output')
            return original(path, kind, synthetic=synthetic)
        with patch.object(self.store, 'import_artifact', side_effect=changing):
            self.assert_uncertain(self.run_worker())
        self.assertEqual(len(self.store.imports), 1)

    def test_retained_adapter_metadata_changes_cannot_replace_validated_import_descriptors(self):
        retained = []
        original = self.store.import_artifact
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            retained.append(value)
            return value
        def mutate_metadata(path, kind='raw', *, synthetic=False):
            for artifact in retained[0]['artifacts']:
                artifact.update(kind='changed', path=str(self.root/'other'), sha256='0'*64, bytes=1)
            return original(path, kind, synthetic=synthetic)
        with patch.object(self.store, 'import_artifact', side_effect=mutate_metadata):
            result = self.run_worker(executor)
        self.assertEqual(result['results'][0]['state'], 'completed')
        published = self.queue.completed[0][3]
        self.assertEqual({item['kind'] for item in published}, {'result', 'operator_journal'})
        self.assertTrue(all(item['sha256'] != '0'*64 and item['bytes'] > 1 for item in published))

    def test_lease_lost_during_import_never_reaches_publication(self):
        original = self.store.import_artifact
        def losing(*args, **kwargs):
            value = original(*args, **kwargs)
            self.queue.current = False
            return value
        with patch.object(self.store, 'import_artifact', side_effect=losing):
            self.assert_uncertain(self.run_worker())
        self.assertEqual(len(self.store.imports), 1)

    def test_unknown_observation_reference_or_forged_usage_is_rejected(self):
        for mutation in ['reference', 'usage']:
            self.queue = Queue(job(request_id='Q-'+mutation, run_id='run-'+mutation))
            def executor(request, output_dir, **kwargs):
                value = self.executor(request, output_dir, **kwargs)
                if mutation == 'reference':
                    value['report']['evidence']['measurement_refs'] = ['event:999']
                else:
                    value['report']['usage']['logical_requests'] = 3
                return artifacts(value, Path(output_dir))
            self.assert_uncertain(self.run_worker(executor))

    def test_duplicate_key_result_file_is_rejected_even_with_matching_hash(self):
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            path = Path(output_dir)/'public-result.json'
            encoded = json_bytes(value['report'])
            encoded = encoded.replace(b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,', 1)
            path.write_bytes(encoded)
            value['artifacts'][0] = metadata('result', path)
            return value
        self.assert_uncertain(self.run_worker(executor))

    def test_default_executor_is_lazily_loaded_without_changing_queue_contract(self):
        with patch('labflow.intake_fixture_bridge._queue_api', return_value=self.queue), \
             patch('labflow.intake_fixture_bridge.importlib.import_module',
                   return_value=SimpleNamespace(run_fixture_method=self.executor)):
            result = run_fixture_worker(self.store, worker_id='worker-synthetic', output_root=self.root/'runs')
        self.assertEqual(result['results'][0]['state'], 'completed')
        self.assertEqual(len(self.calls), 1)

    def test_actual_store_registers_only_synthetic_public_blobs(self):
        from labflow.store import Store as RealStore
        self.store = RealStore(self.root/'actual-state')
        result = self.run_worker()
        self.assertEqual(result['results'][0]['state'], 'completed')
        for item in self.queue.completed[0][3]:
            self.assertIs(self.store.evidence_is_synthetic(item['sha256']), True)
            self.assertTrue(self.store.verify_blob(item['sha256']).is_file())

    def test_reparse_file_metadata_is_rejected_before_any_artifact_import(self):
        original = Path.lstat
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            target = Path(output_dir)/'public-result.json'
            def linked(path):
                info = original(path)
                if path == target:
                    return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=1024)
                return info
            self.link_patch = patch.object(Path, 'lstat', linked)
            self.link_patch.start()
            return value
        try:
            self.assert_uncertain(self.run_worker(executor))
            self.assertFalse(self.store.imports)
        finally:
            if hasattr(self, 'link_patch'):
                self.link_patch.stop()

    def test_output_root_file_is_configuration_error_without_claim(self):
        path = self.root/'occupied'
        path.write_bytes(b'preserved synthetic marker')
        with patch('labflow.intake_fixture_bridge._queue_api', return_value=self.queue), self.assertRaises(ValueError):
            run_fixture_worker(self.store, worker_id='worker', output_root=path, executor=self.executor)
        self.assertEqual(path.read_bytes(), b'preserved synthetic marker')
        self.assertFalse(self.queue.claims)

    def test_typical_nested_output_root_keeps_actual_journal_path_below_windows_limit(self):
        output = padded_output_root(self.root)
        self.assertGreaterEqual(len(str(output)), 100)
        with patch('labflow.intake_fixture_bridge._queue_api', return_value=self.queue):
            result = run_fixture_worker(self.store, worker_id='worker', output_root=output, executor=self.executor)
        self.assertEqual(result['results'][0]['state'], 'completed')
        journal = self.calls[0][1]/'operator/events.jsonl'
        self.assertTrue(journal.is_file())
        self.assertLess(len(str(journal).encode('utf-16-le'))//2, 260)

    @unittest.skipUnless(os.name == 'nt', 'Windows filesystem path preflight')
    def test_impossible_windows_output_root_fails_before_executor_with_explicit_code(self):
        output = padded_output_root(self.root, 190)
        with patch('labflow.intake_fixture_bridge._queue_api', return_value=self.queue):
            result = run_fixture_worker(self.store, worker_id='worker', output_root=output, executor=self.executor)
        self.assertEqual(result['results'][0]['state'], 'failed')
        self.assertEqual(result['results'][0]['error_code'], 'output_path_too_long')
        self.assertFalse(self.calls)
        self.assertFalse(self.queue.failed[0][3])
        self.assertFalse(output.exists())


class IntakeFixtureBridgeDatabaseTests(unittest.TestCase):
    """Actual queue/Store transitions with a synthetic executor, without a model."""

    def setUp(self):
        from labflow.active_intake import register_source, scan_source
        from labflow.intake_jobs import claim_job, complete_job, respond
        from labflow import intake_fixture_jobs
        from labflow.store import Store as RealStore
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = RealStore(self.root/'state')
        self.queue = intake_fixture_jobs
        self.calls = []
        inbox = self.root/'inbox'
        folder = inbox/'request'
        folder.mkdir(parents=True)
        pairs = [('product_type', 'smartphone'), ('market', 'US'),
                 ('purpose', 'certification'), ('model', 'SM-A176U')]
        lines = [key+': '+value for key, value in pairs]
        (folder/'request.txt').write_text('\n'.join(lines), encoding='utf-8')
        register_source(self.store, 'synthetic-source', inbox, synthetic=True, settle_seconds=1)
        scan_source(self.store, 'synthetic-source', now=100)
        self.intake_id = scan_source(self.store, 'synthetic-source', now=101)['accepted'][0]['intake_id']
        claim = claim_job(self.store, 'analysis-fixture', now=102)
        document = claim['documents'][0]
        facts = [{'field': key, 'value': value, 'status': 'explicit', 'evidence': [{
            'path': document['path'], 'sha256': document['sha256'], 'line_start': n,
            'line_end': n, 'quote': lines[n-1], 'role': 'request'}]}
            for n, (key, value) in enumerate(pairs, 1)]
        complete_job(self.store, claim['job_id'], claim['token'], {
            'schema_version': 1, 'producer': {'kind': 'fixture', 'name': 'bridge-db-test'},
            'identity': 'single', 'facts': facts, 'missing_fields': []}, now=103)
        respond(self.store, 'synthetic-proceed', 'proceed', intake_id=self.intake_id)
        ready = self.queue.fixture_readiness(self.store, self.intake_id)
        self.assertIs(ready['ready'], True)
        self.request_kwargs = {'expected_revision': ready['revision'],
            'expected_readiness_fingerprint': ready['readiness_fingerprint'],
            'recipe_id': 'conducted_sensor_fixture_v1', 'settings': {'power_dbm': -4}}
        self.enqueue()

    def enqueue(self):
        return self.queue.request_fixture_job(self.store, 'fixture-request', self.intake_id, **self.request_kwargs)

    def executor(self, request, output_dir, **kwargs):
        self.calls.append((copy.deepcopy(request), Path(output_dir)))
        return produce(request, output_dir, **kwargs)

    def run_worker(self, executor=None):
        return run_fixture_worker(self.store, worker_id='fixture-worker', output_root=self.root/'runs',
                                  max_jobs=2, executor=executor or self.executor)

    def stored(self):
        with self.store.connection() as con:
            return dict(con.execute('SELECT * FROM intake_fixture_jobs WHERE request_id=?',
                                    ('fixture-request',)).fetchone())

    def test_actual_queue_publishes_exact_synthetic_blobs_once_without_cases_or_plans(self):
        result = self.run_worker()
        self.assertEqual(result['results'][0]['state'], 'completed')
        record = self.stored()
        saved = json.loads(record['result_json'])
        self.assertEqual(set(saved), {'report', 'artifacts'})
        self.assertEqual(saved['report']['run_id'], record['run_id'])
        self.assertEqual(saved['report']['runtime_instance_id'], record['runtime_instance_id'])
        for item in saved['artifacts']:
            self.assertIs(self.store.evidence_is_synthetic(item['sha256']), True)
            self.assertEqual(self.store.verify_blob(item['sha256']).stat().st_size, item['bytes'])
        self.assertEqual(self.enqueue()['state'], 'completed')
        self.assertEqual(self.run_worker()['attempted_jobs'], 0)
        self.assertEqual(len(self.calls), 1)
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM cases').fetchone()[0], 0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM plans').fetchone()[0], 0)

    def test_actual_normal_adapter_runs_under_typical_nested_output_root(self):
        try:
            from labflow.virtual_fleet.method_adapter import run_fixture_method
        except ModuleNotFoundError as error:
            if error.name == 'labflow.virtual_fleet.method_adapter':
                self.skipTest('normal D3 adapter is an integration dependency')
            raise
        output = padded_output_root(self.root)
        result = run_fixture_worker(self.store, worker_id='fixture-worker', output_root=output,
                                    executor=run_fixture_method)
        self.assertEqual(result['results'][0]['state'], 'completed')
        saved = json.loads(self.stored()['result_json'])
        self.assertEqual(saved['report']['termination'], {'reason': 'policy_stop', 'policy_claim': 'completed'})
        self.assertEqual(saved['report']['assessment']['verdict'], 'pass')
        journals = list(output.rglob('events.jsonl'))
        self.assertEqual(len(journals), 1)
        self.assertLess(len(str(journals[0]).encode('utf-16-le'))//2, 260)

    def test_actual_readiness_change_after_dispatch_is_uncertain_and_not_reclaimed(self):
        from labflow.intake_jobs import respond
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            respond(self.store, 'synthetic-defer', 'defer', intake_id=self.intake_id)
            return value
        self.assertEqual(self.run_worker(executor)['stop_reason'], 'uncertain')
        self.assertEqual(self.stored()['state'], 'uncertain')
        self.assertIsNone(self.stored()['result_json'])
        self.assertTrue((self.calls[0][1]/'public-result.json').is_file())
        self.assertEqual(self.run_worker()['attempted_jobs'], 0)
        self.assertEqual(len(self.calls), 1)

    def test_actual_expired_lease_after_dispatch_is_uncertain_and_preserves_output(self):
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            with self.store.connection() as con:
                con.execute('UPDATE intake_fixture_jobs SET lease_until=0 WHERE request_id=?', ('fixture-request',))
            return value
        self.assertEqual(self.run_worker(executor)['stop_reason'], 'uncertain')
        self.assertEqual(self.stored()['state'], 'uncertain')
        self.assertTrue((self.calls[0][1]/'operator/events.jsonl').is_file())
        self.assertEqual(self.run_worker()['attempted_jobs'], 0)
        self.assertEqual(len(self.calls), 1)

    def test_actual_preclaim_readiness_change_supersedes_without_executor(self):
        from labflow.intake_jobs import respond
        respond(self.store, 'synthetic-answer', 'answer', intake_id=self.intake_id, answers={'model': 'SM-A176U'})
        self.assertEqual(self.run_worker()['attempted_jobs'], 0)
        self.assertEqual(self.stored()['state'], 'superseded')
        self.assertFalse(self.calls)
        self.assertFalse((self.root/'runs').exists())

    def test_actual_final_cas_lease_loss_preserves_uncertain_result_without_second_execution(self):
        original = self.queue.complete_fixture_job
        def expire_then_complete(*args, **kwargs):
            with self.store.connection() as con:
                con.execute('UPDATE intake_fixture_jobs SET lease_until=0 WHERE request_id=?', ('fixture-request',))
            return original(*args, **kwargs)
        with patch.object(self.queue, 'complete_fixture_job', side_effect=expire_then_complete):
            result = self.run_worker()
        self.assertEqual(result['stop_reason'], 'uncertain')
        record = self.stored()
        self.assertEqual(record['state'], 'uncertain')
        self.assertEqual(record['error_code'], 'lease_expired')
        self.assertEqual(len(json.loads(record['result_json'])['artifacts']), 2)
        self.assertEqual(self.run_worker()['attempted_jobs'], 0)
        self.assertEqual(len(self.calls), 1)

    def test_actual_store_rejects_journal_and_retained_descriptor_changed_after_validation(self):
        retained = []
        replacement = self.root/'replacement-events.jsonl'
        original = self.store.import_artifact
        changed = []
        def executor(request, output_dir, **kwargs):
            value = self.executor(request, output_dir, **kwargs)
            retained.append(value)
            base = {'schema_version': 1, 'kind': 'operator_event', 'run_id': kwargs['run_id'],
                    'runtime_instance_id': kwargs['runtime_instance_id']}
            with OperatorJournal(replacement, run_id=kwargs['run_id'],
                    runtime_instance_id=kwargs['runtime_instance_id'],
                    provenance={'runtime_origin': 'preinitialized', 'catalog_sha256': '1'*64,
                                'topology_sha256': '2'*64, 'engine_sha256': '3'*64}) as journal:
                journal({**base, 'event_id': 'event:1', 'sequence': 1, 'type': 'intent', 'payload': {
                    'request_id': 'request:replacement:1', 'operation': 'execute', 'logical_request': 1,
                    'body': {'device_id': 'sensor', 'action': 'acquire', 'parameters': {}}}})
                journal({**base, 'event_id': 'event:2', 'sequence': 2, 'type': 'receipt', 'payload': {
                    'request_id': 'request:replacement:1', 'result': {'status': 'ok'}}})
                journal({**base, 'event_id': 'event:3', 'sequence': 3, 'type': 'termination',
                         'payload': {'code': 'run_terminated', 'unresolved_request_ids': []}})
            return value
        def replace_journal_and_descriptor(path, kind='raw', *, synthetic=False):
            if not changed:
                artifact = next(item for item in retained[0]['artifacts'] if item['kind'] == 'operator_journal')
                journal_path = Path(artifact['path'])
                journal_path.write_bytes(replacement.read_bytes())
                artifact.update(metadata('operator_journal', journal_path))
                changed.append(True)
            return original(path, kind, synthetic=synthetic)
        with patch.object(self.store, 'import_artifact', side_effect=replace_journal_and_descriptor):
            result = self.run_worker(executor)
        self.assertTrue(changed)
        row = self.stored()
        diagnostic = ''
        if row['result_json']:
            from labflow.virtual_fleet.journal import read_operator_journal
            published = json.loads(row['result_json'])
            artifact = next(item for item in published['artifacts'] if item['kind'] == 'operator_journal')
            journal = read_operator_journal(self.store.verify_blob(artifact['sha256']))
            diagnostic = 'published logical_requests='+str(published['report']['usage']['logical_requests'])
            diagnostic += ', journal intents='+str(sum(item['type'] == 'intent' for item in journal['events']))
        self.assertEqual(result['results'][0]['state'], 'uncertain', diagnostic)
        self.assertEqual(row['state'], 'uncertain')
        self.assertIsNone(row['result_json'])
        self.assertEqual(result['results'][0]['error_code'], 'imported_artifact_mismatch')
        self.assertTrue((self.calls[0][1]/'operator/events.jsonl').is_file())
        self.assertEqual(self.run_worker()['attempted_jobs'], 0)
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__':
    unittest.main()
