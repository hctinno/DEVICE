from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.virtual_fleet.journal import read_operator_journal


def request(power=12.5):
    return {'request_id': 'fixture-request', 'intake_id': 'intake-1', 'revision': 1,
            'readiness_fingerprint': 'd' * 64, 'recipe_id': 'conducted_sensor_fixture_v1',
            'settings': {'power_dbm': power}, 'model': 'SM-A176U', 'source_synthetic': False}


class RuntimeSpy:
    def __init__(self, runtime, *, execute_error=False, lose_advance=False, corrupt=None):
        self.actual = runtime
        self.calls = []
        self.execute_error = execute_error
        self.lose_advance = lose_advance
        self.corrupt = corrupt

    def execute(self, request_id, device_id, action, parameters):
        self.calls.append(('execute', request_id, device_id, action, deepcopy(parameters)))
        result = self.actual.execute(request_id, device_id, action, parameters)
        if self.execute_error:
            raise RuntimeError('CANARY_RUNTIME_PRIVATE')
        return result

    def advance(self, request_id, ticks):
        self.calls.append(('advance', request_id, ticks))
        result = self.actual.advance(request_id, ticks)
        if self.lose_advance:
            from labflow.virtual_fleet.harness import RetryableTransportError
            self.lose_advance = False
            raise RetryableTransportError('CANARY_TRANSPORT_PRIVATE')
        return result

    def observations(self):
        result = self.actual.observations()
        packet = result['devices']['sensor']['values'].get('outputs', {}).get('measurement')
        if self.corrupt and packet and packet.get('valid') is True:
            packet.update(self.corrupt)
        return result


class MethodAdapterTests(unittest.TestCase):
    def setUp(self):
        from labflow.virtual_fleet import method_adapter
        self.module = method_adapter
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'new-attempt'
        self.run_id, self.instance_id = 'reserved-run', 'reserved-instance'

    def run_method(self, data=None, output=None, **kwargs):
        return self.module.run_fixture_method(request() if data is None else data,
                  output or self.output, run_id=kwargs.pop('run_id', self.run_id),
                  runtime_instance_id=kwargs.pop('runtime_instance_id', self.instance_id), **kwargs)

    def spy_trial(self, **options):
        actual = self.module.prepare_sensor_trial
        holders = []
        def prepare(*args, **kwargs):
            trial = actual(*args, **kwargs)
            spy = RuntimeSpy(trial.runtime, **options)
            trial.runtime = spy
            holders.append((trial, spy))
            return trial
        return prepare, holders

    def evidence(self, bundle):
        entries = {item['kind']: item for item in bundle['artifacts']}
        self.assertEqual(set(entries), {'result', 'operator_journal'})
        for item in entries.values():
            self.assertEqual(set(item), {'kind', 'path', 'sha256', 'bytes'})
            path = Path(item['path'])
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.resolve().is_relative_to(self.root.resolve()))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'])
            self.assertEqual(path.stat().st_size, item['bytes'])
            self.assertNotIn('private', path.relative_to(self.root).parts)
        self.assertEqual(json.loads(Path(entries['result']['path']).read_text(encoding='utf-8')), bundle['report'])
        journal = read_operator_journal(entries['operator_journal']['path'])
        self.assertEqual(journal['header']['run_id'], self.run_id)
        self.assertEqual(journal['header']['runtime_instance_id'], self.instance_id)
        self.assertFalse(journal['resumable'])
        return journal

    def test_describe_supports_only_the_declared_synthetic_range_and_quantity(self):
        for power in [-30, -4, 20]:
            result = self.module.describe_fixture_method('conducted_sensor_fixture_v1', model='SM-A176U', settings={'power_dbm': power})
            self.assertTrue(result['supported'])
            self.assertEqual(result['reason_codes'], [])
            self.assertEqual(result['settings'], {'power_dbm': float(power)})
            self.assertEqual(result['quantity'], {'reference_plane': 'sensor_input', 'metric': 'on_mean_power', 'unit': 'dBm'})
            self.assertEqual(result['synthetic_setup']['coupling_db'], 20)
            self.assertEqual(result['synthetic_setup']['coupling_basis'], 'declared_synthetic_policy')
            self.assertTrue(result['synthetic'])
            self.assertFalse(result['hardware_verified'])
            self.assertFalse(result['ai_model_called'])
            self.assertFalse(result['resumable'])

    def test_unsupported_description_does_not_initialize_or_echo_private_inputs(self):
        cases = [('legacy_virtual_session', 'SM-A176U', {'power_dbm': 1}),
                 ('conducted_sensor_fixture_v1', 'different-model', {'power_dbm': 1})]
        cases += [('conducted_sensor_fixture_v1', 'SM-A176U', settings) for settings in
                  ({}, None, {'power_dbm': True}, {'power_dbm': '12'}, {'power_dbm': float('nan')},
                   {'power_dbm': float('inf')}, {'power_dbm': -30.01}, {'power_dbm': 20.01},
                   {'power_dbm': 1, 'seed': 'CANARY_DESCRIPTION_PRIVATE'})]
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=AssertionError('no runtime')):
            for recipe, model, settings in cases:
                result = self.module.describe_fixture_method(recipe, model=model, settings=settings)
                self.assertFalse(result['supported'])
                self.assertTrue(result['reason_codes'])
                self.assertNotIn('CANARY_DESCRIPTION_PRIVATE', json.dumps(result))

    def test_unsupported_execution_and_invalid_request_are_rejected_before_files_or_runtime(self):
        cases = []
        for changes in [{'recipe_id': 'unsupported'}, {'model': 'another'}, {'settings': {'power_dbm': 30}},
                        {'revision': True}, {'revision': 0}, {'readiness_fingerprint': 'bad'},
                        {'source_synthetic': 'false'}, {'case_id': 'not-created'}, {'request_id': '../bad'}]:
            data = request(); data.update(changes); cases.append(data)
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=AssertionError('no runtime')):
            for index, data in enumerate(cases):
                output = self.root / f'invalid-{index}'
                with self.assertRaises(ValueError):
                    self.run_method(data, output)
                self.assertFalse(output.exists())

    def test_reserved_ids_are_required_and_invalid_ids_do_not_initialize(self):
        for run_id, instance in [('bad/id', self.instance_id), (self.run_id, None), (True, self.instance_id)]:
            with self.assertRaises(ValueError):
                self.run_method(run_id=run_id, runtime_instance_id=instance)
        self.assertFalse(self.output.exists())

    def test_actual_single_normal_trial_keeps_reserved_identity_and_exact_public_report(self):
        original = request(); before = json.dumps(original, sort_keys=True)
        with patch.object(self.module, 'prepare_sensor_trial', wraps=self.module.prepare_sensor_trial) as prepare:
            bundle = self.run_method(original)
        self.assertEqual(json.dumps(original, sort_keys=True), before)
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(prepare.call_args.kwargs, {'condition': 'normal', 'seed': 0, 'power_dbm': 12.5})
        self.assertEqual(set(bundle), {'report', 'artifacts'})
        report = bundle['report']
        self.assertEqual(set(report), {'schema_version', 'kind', 'run_id', 'runtime_instance_id', 'synthetic',
                          'hardware_verified', 'ai_model_called', 'policy', 'termination', 'task_outcome',
                          'cleanup', 'usage', 'evidence', 'unresolved_request_ids', 'assessment'})
        self.assertEqual(report['run_id'], self.run_id)
        self.assertEqual(report['runtime_instance_id'], self.instance_id)
        self.assertEqual(report['termination'], {'reason': 'policy_stop', 'policy_claim': 'completed'})
        self.assertEqual(report['assessment']['verdict'], 'pass')
        self.assertEqual(report['task_outcome'], 'not_assessed')
        self.assertEqual(report['cleanup']['status'], 'not_assessed')
        self.assertTrue(report['synthetic'])
        self.assertFalse(report['hardware_verified'])
        self.assertFalse(report['ai_model_called'])
        journal = self.evidence(bundle)
        self.assertTrue(journal['complete'])
        self.assertTrue(report['evidence']['measurement_refs'])
        self.assertEqual(journal['header']['provenance']['runtime_origin'], 'preinitialized')
        self.assertEqual(len(journal['header']['provenance']['topology']['devices']), 64)
        author = json.loads((self.output / 'private/author.json').read_text(encoding='utf-8'))
        self.assertEqual(author['condition'], 'normal')
        self.assertEqual(author['seed'], 0)
        self.assertTrue((self.output / 'private-manifest.json').is_file())
        for item in (report, journal):
            text = json.dumps(item)
            for forbidden in ('expected_sensor_dbm', 'comparison_tolerance_db', 'author_events', 'source_path'):
                self.assertNotIn(forbidden, text)

    def test_changed_power_and_boundaries_use_sensor_on_mean_without_double_duty_or_loss(self):
        for index, power in enumerate([-30, -4, 20]):
            output = self.root / f'power-{index}'
            bundle = self.run_method(request(power), output)
            journal = self.evidence(bundle)
            refs = bundle['report']['evidence']['measurement_refs']
            observations = {e['event_id']: e['payload']['observation'] for e in journal['events'] if e['type'] == 'observation'}
            self.assertTrue(refs)
            for ref in refs:
                observed = observations[ref]
                sensor = observed['devices']['sensor']
                measurement = sensor['values']['outputs']['measurement']
                self.assertEqual(measurement['source_id'], 'sensor')
                self.assertEqual(measurement['unit'], 'dBm')
                self.assertAlmostEqual(measurement['value'], power - 10 - .5 - 20)
                self.assertEqual(measurement['acquisition_setup_revision'], observed['setup_revision'])
                self.assertLessEqual(measurement['acquisition_tick'], observed['tick'])
                self.assertEqual(measurement['duty_cycle'], .25)
                self.assertEqual(measurement['frequency_hz'], 2.45e9)
                self.assertEqual(sensor['profile_id'], 'n1921a-508b0b7652')

    def test_existing_output_and_failed_folder_are_never_reused(self):
        self.output.mkdir(); marker = self.output / 'failure.json'; marker.write_bytes(b'old failure')
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=AssertionError('no runtime')):
            with self.assertRaises(FileExistsError):
                self.run_method()
        self.assertEqual(marker.read_bytes(), b'old failure')
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_continuation_denied_before_initialization_creates_no_runtime_or_folder(self):
        for callback in [lambda: False, lambda: 1, lambda: (_ for _ in ()).throw(RuntimeError('CANARY_FENCE_PRIVATE'))]:
            with patch.object(self.module, 'prepare_sensor_trial', side_effect=AssertionError('no runtime')):
                with self.assertRaises(self.module.FixtureMethodError) as caught:
                    self.run_method(can_continue=callback)
            self.assertFalse(caught.exception.dispatched)
            self.assertNotIn('CANARY_FENCE_PRIVATE', str(caught.exception))
            self.assertFalse(self.output.exists())

    def test_continuation_denied_at_policy_boundary_records_supervisor_stop_without_dispatch(self):
        prepare, holders = self.spy_trial()
        calls = []
        def gate():
            calls.append(1); return len(calls) <= 2
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            bundle = self.run_method(can_continue=gate)
        self.assertEqual(holders[0][1].calls, [])
        self.assertEqual(bundle['report']['termination']['reason'], 'supervisor_stop')
        self.assertIsNone(bundle['report']['termination']['policy_claim'])
        journal = self.evidence(bundle)
        self.assertTrue(journal['complete'])
        self.assertFalse(any(e['type'] == 'intent' for e in journal['events']))
        self.assertEqual(len(calls), 3)
        self.assertTrue(any(e['type'] == 'observation' for e in journal['events']))

    def test_continuation_denied_immediately_after_initialization_never_calls_policy(self):
        prepare, holders = self.spy_trial()
        calls = []
        def gate():
            calls.append(1); return len(calls) == 1
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            bundle = self.run_method(can_continue=gate)
        self.assertEqual(len(calls), 2)
        self.assertEqual(holders[0][1].calls, [])
        self.assertEqual(bundle['report']['usage']['decisions'], 0)
        self.assertEqual(bundle['report']['termination']['reason'], 'supervisor_stop')
        self.assertTrue(self.evidence(bundle)['complete'])

    def test_dispatch_fence_failure_leaves_unresolved_intent_without_actual_call(self):
        prepare, holders = self.spy_trial()
        calls = []
        def gate():
            calls.append(1)
            if len(calls) == 4:
                raise RuntimeError('CANARY_FENCE_PRIVATE')
            return True
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            bundle = self.run_method(can_continue=gate)
        self.assertEqual(holders[0][1].calls, [])
        report = bundle['report']
        self.assertEqual(report['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertEqual(len(report['unresolved_request_ids']), 1)
        self.assertNotIn('CANARY_FENCE_PRIVATE', json.dumps(report))
        journal = self.evidence(bundle)
        self.assertFalse(journal['complete'])
        self.assertEqual(journal['unresolved_request_ids'], report['unresolved_request_ids'])

    def test_lease_loss_after_first_call_does_not_dispatch_cleanup_or_new_work(self):
        prepare, holders = self.spy_trial()
        def gate():
            return not holders or not holders[0][1].calls
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            bundle = self.run_method(can_continue=gate)
        self.assertEqual(len(holders[0][1].calls), 1)
        self.assertEqual(bundle['report']['termination']['reason'], 'supervisor_stop')
        self.assertEqual(bundle['report']['cleanup']['status'], 'not_assessed')
        self.assertEqual(bundle['report']['evidence']['measurement_refs'], [])

    def test_runtime_exception_after_mutation_is_not_retried_or_exposed(self):
        prepare, holders = self.spy_trial(execute_error=True)
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            bundle = self.run_method()
        self.assertEqual(len(holders), 1)
        self.assertEqual(len(holders[0][1].calls), 1)
        self.assertEqual(bundle['report']['termination']['reason'], 'runtime_mutation_uncertain')
        self.assertTrue(bundle['report']['unresolved_request_ids'])
        self.assertNotIn('CANARY_RUNTIME_PRIVATE', json.dumps(bundle['report']))
        self.assertFalse(self.evidence(bundle)['complete'])

    def test_retryable_lost_advance_uses_same_live_instance_id_and_one_tick(self):
        prepare, holders = self.spy_trial(lose_advance=True)
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            bundle = self.run_method()
        advances = [call for call in holders[0][1].calls if call[0] == 'advance']
        self.assertEqual(advances[0], advances[1])
        self.assertEqual(bundle['report']['usage']['transport_retries'], 1)
        self.assertEqual(bundle['report']['assessment']['verdict'], 'pass')
        self.assertTrue(self.evidence(bundle)['complete'])

    def test_wrong_source_unit_or_revision_cannot_become_a_completed_measurement(self):
        for index, corruption in enumerate([{'source_id': 'another'}, {'unit': 'W'}, {'acquisition_setup_revision': -1}]):
            prepare, holders = self.spy_trial(corrupt=corruption)
            with patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
                bundle = self.run_method(output=self.root / f'invalid-observation-{index}')
            self.assertNotEqual(bundle['report']['assessment']['verdict'], 'pass')
            self.assertEqual(bundle['report']['evidence']['measurement_refs'], [])
            self.evidence(bundle)

    def test_lost_journal_ack_is_preserved_and_never_returned_as_consistent_evidence(self):
        original = self.module.OperatorJournal
        class LostAck:
            def __init__(self, *args, **kwargs): self.actual = original(*args, **kwargs)
            def __call__(self, item):
                self.actual(item)
                if item['type'] == 'intent': raise OSError('CANARY_JOURNAL_PRIVATE')
            def close(self): self.actual.close()
        prepare, holders = self.spy_trial()
        with patch.object(self.module, 'OperatorJournal', LostAck), patch.object(self.module, 'prepare_sensor_trial', side_effect=prepare):
            with self.assertRaises(self.module.FixtureMethodError) as caught:
                self.run_method()
        self.assertTrue(caught.exception.dispatched)
        self.assertNotIn('CANARY_JOURNAL_PRIVATE', str(caught.exception))
        journal = read_operator_journal(self.output / 'operator/events.jsonl')
        self.assertTrue(journal['unresolved_request_ids'])
        self.assertEqual(holders[0][1].calls, [])
        self.assertTrue((self.output / 'failure.json').is_file())
        self.assertTrue((self.output / 'private/author.json').is_file())

    def test_public_result_write_failure_preserves_journal_author_and_failure_code(self):
        original = self.module._write_new
        def fail_result(path, value):
            if Path(path).name == 'public-result.json': raise OSError('CANARY_STORAGE_PRIVATE')
            return original(path, value)
        with patch.object(self.module, '_write_new', side_effect=fail_result):
            with self.assertRaises(self.module.FixtureMethodError) as caught:
                self.run_method()
        self.assertTrue(caught.exception.dispatched)
        self.assertNotIn('CANARY_STORAGE_PRIVATE', str(caught.exception))
        self.assertTrue(read_operator_journal(self.output / 'operator/events.jsonl')['complete'])
        self.assertTrue((self.output / 'private/author.json').is_file())
        self.assertTrue((self.output / 'failure.json').is_file())

    def test_initialization_failure_retains_new_attempt_and_never_falls_back_to_another_trial(self):
        with patch.object(self.module, 'prepare_sensor_trial', side_effect=RuntimeError('CANARY_INIT_PRIVATE')) as prepare:
            with self.assertRaises(self.module.FixtureMethodError) as caught:
                self.run_method()
        self.assertEqual(prepare.call_count, 1)
        self.assertTrue(caught.exception.dispatched)
        self.assertNotIn('CANARY_INIT_PRIVATE', str(caught.exception))
        self.assertTrue((self.output / 'failure.json').is_file())

    def test_invalid_evaluator_data_never_leaks_through_a_retained_public_result(self):
        def private_result(*args, **kwargs):
            return {'status': 'completed', 'verdict': 'pass', 'evaluator_id': 'rf_sensor_fixture_v1',
                    'evidence_refs': [], 'summary_code': 'observed_goal_satisfied',
                    'expected_sensor_dbm': 'CANARY_GRADER_PRIVATE'}
        with patch.object(self.module, 'evaluate_sensor_run', side_effect=private_result):
            with self.assertRaises(self.module.FixtureMethodError) as caught:
                self.run_method()
        self.assertNotIn('CANARY_GRADER_PRIVATE', str(caught.exception))
        for name in ['public-result.json', 'operator/events.jsonl', 'failure.json']:
            path = self.output / name
            if path.exists():
                self.assertNotIn(b'CANARY_GRADER_PRIVATE', path.read_bytes())

    def test_changed_catalog_during_load_cannot_produce_a_stale_public_fingerprint(self):
        actual = self.module.load_catalog
        with patch.object(self.module, 'load_catalog', side_effect=lambda path: dict(actual(path), title='changed in loader')):
            with self.assertRaises(self.module.FixtureMethodError):
                self.run_method()
        self.assertFalse(self.output.exists())

    def test_pass_without_measurement_refs_is_not_a_supported_completion(self):
        assessment = {'status': 'completed', 'verdict': 'pass', 'evaluator_id': 'rf_sensor_fixture_v1',
                      'evidence_refs': [], 'summary_code': 'observed_goal_satisfied'}
        with patch.object(self.module, 'evaluate_sensor_run', return_value=assessment):
            with self.assertRaises(self.module.FixtureMethodError):
                self.run_method()

    def test_output_creation_failure_is_sanitized_and_not_dispatched(self):
        with patch.object(Path, 'mkdir', side_effect=PermissionError('CANARY_OUTPUT_PRIVATE')):
            with patch.object(self.module, 'prepare_sensor_trial', side_effect=AssertionError('no runtime')):
                with self.assertRaises(self.module.FixtureMethodError) as caught:
                    self.run_method()
        self.assertFalse(caught.exception.dispatched)
        self.assertNotIn('CANARY_OUTPUT_PRIVATE', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
