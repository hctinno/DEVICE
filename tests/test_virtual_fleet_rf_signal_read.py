"""048 read-only behavior; standalone serialized fixtures never run a Fleet."""
from contextlib import ExitStack
from copy import deepcopy
from io import StringIO
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from labflow import control_packet_prepare as native
from labflow import store
from labflow.virtual_fleet import catalog, integration, journal, rf_signal_cli, rf_signal_scenario
from labflow.virtual_fleet.harness import FleetHarness

reader = (importlib.import_module('labflow.virtual_fleet.rf_signal_read')
          if importlib.util.find_spec('labflow.virtual_fleet.rf_signal_read') else None)
ROOT = Path(__file__).resolve().parents[1]
ENGINE = ('__init__.py', '__main__.py', 'catalog.py', 'core.py', 'evaluation.py', 'facility.py',
          'frequency_psd.py', 'frequency_psd_max.py', 'frequency_source.py', 'harness.py',
          'harness_check.py', 'instruments.py', 'integration.py', 'journal.py', 'method_adapter.py',
          'policies.py', 'rf.py', 'spectrum_capture.py', 'spectrum_math.py')
ENGINE_SHA = '9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42'
CURRENT_ENGINE_SHA = '7816f87dcf8aa648d628935493f74dee3a54f993ba2bae87f9a1e102a8b4ccab'
CATALOG_SHA = '6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff'
SCENARIOS = ('pulsed_on_mean', 'pulsed_time_mean', 'pulsed_peak', 'cw_peak',
             'shifted_frequency', 'sensor_uncalibrated', 'meter_frequency_conflict')
VALUES = (-18.0, -24.020599913279625, -15.0, -18.0, -18.0, None, None)
MODES = ('on_average', 'time_average', 'peak', 'peak', 'on_average', 'on_average', 'on_average')
FLAGS = dict(data_origin='authored_synthetic', execution_mode='synthetic_virtual_execution', synthetic=True,
             hardware_verified=False, physical_verified=False, ai_model_called=False,
             normative_compliance_verified=False, method_approval='not_assessed',
             regulatory_scope_complete=False, waveform_implemented=False)
KEYS = set('schema_version kind selection metadata storage historical_assessment measurement '
           'measurement_goal_succeeded outcome failure verification execution_authorized '
           'rerun_authorized error_code'.split())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(folder):
    return {p.relative_to(folder).as_posix(): (digest(p.read_bytes()), p.stat().st_dev, p.stat().st_ino,
            p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_mode)
            for p in folder.rglob('*') if p.is_file()}


class RfSignalReadArgumentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(reader, '048 public read API is absent')

    def test_public_API_and_fixed_error_class(self):
        self.assertTrue(callable(reader.read_rf_signal_run))
        value = reader.RfSignalReadError('untrusted PRIVATE path')
        self.assertEqual((value.code, str(value)), ('rf_signal_read_unavailable', 'rf_signal_read_unavailable'))

    def test_invalid_names_rejected_before_IO_without_callbacks(self):
        class Hostile(str):
            def __str__(self): raise AssertionError('callback')
        values = [None, False, 7, [], {}, Path('x'), Hostile('x'), '', '.', '..', '-x', '_x',
                  'x/y', r'x\y', r'C:x', '/x', 'CON', 'aux', 'COM1', 'LPT9', 'NUL', 'x.',
                  'x ', ' x', '한글', 'x\n', '*', 'x' * 65]
        for value in values:
            with ExitStack() as stack:
                calls = [stack.enter_context(mock.patch.object(obj, name, side_effect=AssertionError('IO')))
                         for obj, name in [(native, '_WindowsIO'), (Path, 'open'), (journal, 'read_operator_journal')]]
                with self.assertRaises(reader.RfSignalReadError) as raised:
                    reader.read_rf_signal_run(value)
            self.assertEqual(raised.exception.code, 'rf_signal_read_invalid_argument')
            for call in calls: call.assert_not_called()


class RfSignalReadTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(reader, '048 public read API is absent')
        parent = ROOT / '.local/rf048-tests'; parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=parent); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.package = self.base / 'labflow/virtual_fleet'; self.package.mkdir(parents=True)
        for name in ENGINE: shutil.copyfile(ROOT / 'labflow/virtual_fleet' / name, self.package / name)
        shutil.copyfile(ROOT / 'labflow/control_packet_prepare.py', self.base / 'labflow/control_packet_prepare.py')
        self.module_path = self.package / 'rf_signal_read.py'
        self.namespace = self.base / '.local/rf-signal-runs'; self.name = 'run048'
        self.folder = self.namespace / self.name; self.backends = []

    def invoke(self, name=None, *, close_error=False):
        backend_type = native._WindowsIO; out, err = StringIO(), StringIO()
        def backend():
            value = backend_type(); self.backends.append(value); close = value.close
            def closing():
                close()
                if close_error: raise OSError('PRIVATE close')
            value.close = mock.Mock(side_effect=closing)
            return value
        with ExitStack() as stack:
            forbidden = [stack.enter_context(mock.patch.object(obj, method, side_effect=AssertionError('execution')))
                         for obj, method in [(rf_signal_scenario, 'run_rf_signal_scenario'),
                                             (rf_signal_scenario, 'evaluate_rf_signal_scenario'),
                                             (rf_signal_scenario, 'describe_rf_signal_scenario'),
                                             (integration, 'create_conducted_example'), (FleetHarness, 'run'),
                                             (rf_signal_cli, 'main'), (rf_signal_cli, '_completed'),
                                             (catalog, 'load_catalog'), (subprocess, 'Popen'),
                                             (sqlite3, 'connect'), (store, 'Store'), (socket, 'socket')]]
            stack.enter_context(mock.patch.object(reader, '__file__', str(self.module_path)))
            stack.enter_context(mock.patch.object(native, '_WindowsIO', side_effect=backend))
            stack.enter_context(mock.patch.object(sys, 'stdout', out)); stack.enter_context(mock.patch.object(sys, 'stderr', err))
            try:
                result = reader.read_rf_signal_run(self.name if name is None else name)
            finally:
                for call in forbidden: call.assert_not_called()
                for value in self.backends:
                    value.close.assert_called_once(); self.assertEqual((value.held, value.directories), ([], {}))
                self.assertFalse(out.closed); self.assertFalse(err.closed)
                self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        return result

    def assert_error(self, code, **kwargs):
        with self.assertRaises(reader.RfSignalReadError) as raised: self.invoke(**kwargs)
        self.assertEqual(raised.exception.code, 'rf_signal_read_' + code)
        self.assertEqual(str(raised.exception), raised.exception.code)
        self.assertNotIn(str(self.base), str(raised.exception))

    def fixture(self, sid='pulsed_peak', *, verdict='pass', prefix=False):
        """Authored serialized contract fixture, not a harness/Fleet execution."""
        index = SCENARIOS.index(sid); mode = MODES[index]
        self.folder.mkdir(parents=True); (self.folder / 'operator').mkdir()
        self.request = dict(schema_version=1, scenario_id=sid, seed=7)
        self.provenance = dict(runtime_origin='preinitialized', catalog_sha256=CATALOG_SHA,
                               engine_sha256=ENGINE_SHA, topology_sha256='0' * 64)
        self.ids = dict(run_id='fixture048:run', runtime_instance_id='fixture048:instance')
        self.events = []
        for number in range(2):
            outputs = {}
            if number and VALUES[index] is not None:
                outputs['measurement'] = dict(value=VALUES[index], unit='dBm', quantity=mode)
            self.events.append(dict(schema_version=1, kind='operator_event', **self.ids,
                                    event_id='fixture048:observation:' + str(number), sequence=number + 1,
                                    type='observation', payload={'observation': dict(
                                        tick=1, setup_revision=1, synthetic=True, hardware_verified=False,
                                        devices={'meter': {'values': {'outputs': outputs}}})}))
        self.events.append(dict(schema_version=1, kind='operator_event', **self.ids,
                                event_id='fixture048:termination', sequence=3, type='termination',
                                payload=dict(code='run_terminated', unresolved_request_ids=[])))
        self.write_journal([] if prefix else self.events)
        if prefix: return
        (self.folder / 'private').mkdir()
        (self.folder / 'private/author.json').write_bytes(b'\xff\x00opaque-not-JSON\n')
        claim = 'blocked' if index > 4 else 'completed'
        assessment = dict(status='completed', verdict=verdict, evaluator_id='rf_signal_scenario_v1',
                          evidence_refs=['fixture048:observation:1'],
                          summary_code=('expected_sensor_blocked' if index == 5 else
                                        'expected_meter_frequency_conflict' if index == 6 else
                                        'observed_signal_satisfied') if verdict == 'pass' else 'scenario_expectation_mismatch')
        report = dict(schema_version=1, kind='virtual_fleet_harness_result', **self.ids,
                      synthetic=True, hardware_verified=False, ai_model_called=False,
                      policy=dict(kind='fixture', id='rf_signal_scenario_v1'),
                      termination=dict(reason='policy_stop', policy_claim=claim), task_outcome='not_assessed',
                      cleanup=dict(status='not_assessed', evidence_refs=[]),
                      usage=dict(decisions=0, logical_requests=0, transport_retries=0, tick_delta=0,
                                 reserved_ticks=0, elapsed_ms=0),
                      evidence=dict(measurement_refs=['fixture048:observation:1'], operator_transcript_ref='artifact:operator_events'),
                      unresolved_request_ids=[], assessment=dict(status='not_assessed', verdict=None,
                      evaluator_id=None, evidence_refs=[], summary_code=None))
        self.outer = dict(schema_version=1, kind='virtual_rf_signal_scenario', scenario_id=sid,
                          status='executed', report=report, assessment=assessment,
                          artifacts=[dict(path='operator/events.jsonl', bytes=0, sha256='0' * 64, visibility='operator')],
                          error_code=None, verification=deepcopy(FLAGS),
                          declared_setup=dict(
                              source_signal=dict(frequency_hz=2450000000.0, power_dbm=12.5, bandwidth_hz=20000000.0,
                                                 duty_cycle=0.25, crest_factor_db=3.0, modulation='OFDM'),
                              sensor=dict(calibration_valid=index != 5, acquisition_policy='triggered'),
                              meter=dict(frequency_hz=2450000000.0, measurement_mode=mode, unit='dBm'),
                              reference_plane='sensor_input', basis='declared_synthetic_policy'))
        self.publish()

    def write_journal(self, events):
        path = self.folder / 'operator/events.jsonl'
        if path.exists(): path.unlink()  # Test-owned fixture only.
        with journal.OperatorJournal(path, **self.ids, provenance=self.provenance) as writer:
            for event in events: writer(event)

    def publish(self):
        journal_raw = (self.folder / 'operator/events.jsonl').read_bytes()
        self.outer['artifacts'] = [dict(path='operator/events.jsonl', bytes=len(journal_raw),
                                       sha256=digest(journal_raw), visibility='operator')]
        (self.folder / 'public-result.json').write_bytes(encoded(self.outer) + b'\n')
        self.reseal()

    def reseal(self):
        files = []
        for name in ('public-result.json', 'operator/events.jsonl', 'private/author.json'):
            raw = (self.folder / name).read_bytes()
            files.append(dict(path=name, bytes=len(raw), sha256=digest(raw),
                              visibility='evaluator_private' if name.startswith('private/') else 'operator'))
        manifest = dict(schema_version=1, kind='private_rf_signal_scenario_manifest', complete=True,
                        request=self.request, files=files, **{k: self.provenance[k]
                        for k in ('catalog_sha256', 'engine_sha256', 'topology_sha256')})
        (self.folder / 'private-manifest.json').write_bytes(encoded(manifest) + b'\n')

    def failure(self, **updates):
        value = dict(schema_version=1, kind='rf_signal_scenario_failure',
                     scenario_id=self.request['scenario_id'], error_code='rf_signal_scenario_evidence_unavailable',
                     phase='artifact_write', dispatched=True)
        value.update(updates); (self.folder / 'failure.json').write_bytes(encoded(value) + b'\n')

    def check_complete(self, value, sid='pulsed_peak', *, verdict='pass'):
        self.assertEqual(set(value), KEYS); self.assertEqual(value['kind'], 'virtual_rf_signal_run_read')
        self.assertEqual(value['schema_version'], 1); self.assertEqual(value['selection'], {'run_name': self.name})
        self.assertEqual(set(value['metadata']), {'request', 'run_id', 'runtime_instance_id', 'execution_status'})
        self.assertEqual(value['metadata'], dict(request=self.request, **self.ids, execution_status='executed'))
        self.assertEqual(set(value['storage']), {'status', 'manifest_sha256', 'verified_file_count', 'journal_status', 'binding_verified'})
        self.assertEqual((value['storage']['status'], value['storage']['verified_file_count'],
                          value['storage']['journal_status'], value['storage']['binding_verified']),
                         ('complete_verified', 3, 'complete', True))
        self.assertEqual(value['storage']['manifest_sha256'], digest((self.folder / 'private-manifest.json').read_bytes()))
        self.assertEqual(value['historical_assessment'], self.outer['assessment'])
        self.assertEqual(set(value['verification']), {'saved', 'current_scope', 'source_pins_verified',
                                                     'fresh_offline_evaluation_performed', 'producer_cli_exit_status'})
        self.assertEqual(value['verification'], dict(saved=FLAGS, current_scope='stored_hashes_and_public_journal',
                         source_pins_verified=True, fresh_offline_evaluation_performed=False, producer_cli_exit_status=None))
        index = SCENARIOS.index(sid); number = VALUES[index]
        self.assertEqual(value['measurement'], None if number is None else
                         dict(value=number, unit='dBm', quantity=MODES[index], reference_plane='sensor_input'))
        self.assertEqual(value['measurement_goal_succeeded'], verdict == 'pass' and number is not None)
        self.assertEqual(value['outcome'], 'assessment_failed' if verdict == 'fail' else
                         'expected_blocked' if number is None else 'measurement_observed')
        self.assertFalse(value['execution_authorized']); self.assertFalse(value['rerun_authorized'])
        self.assertIsNone(value['error_code']); self.assertIsNone(value['failure'])
        self.assertLessEqual(len(encoded(value)), 8192)
        self.assertNotIn(str(self.base), json.dumps(value))

    def check_withheld(self, value, status, outcome=None):
        self.assertEqual(set(value), KEYS); self.assertEqual(value['storage']['status'], status)
        if outcome: self.assertEqual(value['outcome'], outcome)
        self.assertIsNone(value['historical_assessment']); self.assertIsNone(value['measurement'])
        self.assertFalse(value['measurement_goal_succeeded']); self.assertFalse(value['execution_authorized'])
        self.assertFalse(value['rerun_authorized']); self.assertIsNone(value['verification']['saved'])

    def test_missing_namespace_and_folder_never_create_anything(self):
        before = fingerprint(self.base); self.assert_error('not_found')
        self.assertEqual(fingerprint(self.base), before); self.assertFalse(self.namespace.exists())

    def test_empty_existing_folder_is_truthful_incomplete_DTO14(self):
        self.folder.mkdir(parents=True); before = fingerprint(self.base); value = self.invoke()
        self.assertEqual(set(value), KEYS); self.assertEqual(value['storage']['status'], 'incomplete')
        self.assertEqual(value['metadata'], dict(request=None, run_id=None, runtime_instance_id=None, execution_status='unconfirmed'))
        self.assertIsNone(value['historical_assessment']); self.assertIsNone(value['measurement'])
        self.assertFalse(value['measurement_goal_succeeded']); self.assertIsNone(value['error_code'])
        self.assertFalse(value['execution_authorized']); self.assertFalse(value['rerun_authorized'])
        self.assertEqual(value['verification']['fresh_offline_evaluation_performed'], False)
        self.assertIsNone(value['verification']['producer_cli_exit_status'])
        self.assertEqual(fingerprint(self.base), before)

    def test_standalone_serialized_seven_cases_and_repeated_reads_are_unchanged(self):
        for sid in SCENARIOS:
            self.name = sid; self.folder = self.namespace / sid; self.fixture(sid)
            before = fingerprint(self.base); value = self.invoke(); self.check_complete(value, sid)
            self.assertEqual(self.invoke(), value); self.assertEqual(fingerprint(self.base), before)
            self.backends.clear()

    def test_explicit_current_and_legacy_stored_engines_are_readonly_without_reassessment(self):
        for label, engine in (('legacy', ENGINE_SHA), ('current', CURRENT_ENGINE_SHA)):
            with self.subTest(generation=label):
                self.name = label
                self.folder = self.namespace / label
                self.fixture()
                self.provenance['engine_sha256'] = engine
                self.write_journal(self.events)
                self.publish()
                before = fingerprint(self.base)
                try:
                    value = self.invoke()
                except reader.RfSignalReadError as error:
                    self.fail('supported live source blocked readonly generation: ' + error.code)
                self.check_complete(value)
                self.assertEqual(self.invoke(), value)
                self.assertEqual(fingerprint(self.base), before)
                self.backends.clear()

    def test_mixed_or_unknown_manifest_and_journal_engines_are_invalid_not_relabelled(self):
        self.fixture()
        pairs = ((ENGINE_SHA, CURRENT_ENGINE_SHA), (CURRENT_ENGINE_SHA, ENGINE_SHA),
                 ('0' * 64, ENGINE_SHA), (ENGINE_SHA, '0' * 64), ('0' * 64, '0' * 64))
        for manifest_engine, journal_engine in pairs:
            with self.subTest(manifest=manifest_engine, journal=journal_engine):
                self.provenance['engine_sha256'] = journal_engine
                self.write_journal(self.events)
                self.publish()
                path = self.folder / 'private-manifest.json'
                manifest = json.loads(path.read_bytes())
                manifest['engine_sha256'] = manifest_engine
                path.write_bytes(encoded(manifest) + b'\n')
                before = fingerprint(self.base)
                try:
                    value = self.invoke()
                except reader.RfSignalReadError as error:
                    self.fail('live source gate hid saved-hash validation: ' + error.code)
                self.check_withheld(value, 'invalid')
                self.assertEqual(fingerprint(self.base), before)
                self.backends.clear()

    def test_unknown_actual_source_hash_still_blocks_before_saved_context(self):
        self.fixture()
        path = self.package / 'rf.py'
        path.write_bytes(path.read_bytes() + b'\n# unapproved source\n')
        before = fingerprint(self.base)
        self.assert_error('input_changed')
        self.assertEqual(fingerprint(self.base), before)

    def test_genuine_current_cw_048_to_055_and_readonly_observation_reader(self):
        from labflow.virtual_fleet import rf_signal_waveform as waveform
        from labflow.virtual_fleet import rf_signal_waveform_observation as observer
        from labflow.virtual_fleet import rf_signal_waveform_observation_read as observation_reader
        self.name = 'genuine_current_cw'
        self.folder = self.namespace / self.name
        modules = ((reader, 'rf_signal_read.py'), (rf_signal_scenario, 'rf_signal_scenario.py'),
                   (waveform, 'rf_signal_waveform.py'), (observer, 'rf_signal_waveform_observation.py'),
                   (observation_reader, 'rf_signal_waveform_observation_read.py'))
        for module, name in modules:
            shutil.copyfile(ROOT / 'labflow/virtual_fleet' / name, self.package / name)
        profile = self.base / 'virtual_profiles/sm_a176u_unlicensed.json'
        profile.parent.mkdir()
        shutil.copyfile(ROOT / 'virtual_profiles/sm_a176u_unlicensed.json', profile)
        with ExitStack() as stack:
            for module, name in modules:
                stack.enter_context(mock.patch.object(module, '__file__', str(self.package / name)))
            stack.enter_context(mock.patch.object(native, '__file__', str(self.base / 'labflow/control_packet_prepare.py')))
            produced = rf_signal_scenario.run_rf_signal_scenario(
                catalog.load_catalog(profile), dict(schema_version=1, scenario_id='cw_peak', seed=7),
                self.folder, run_id='compat-current-run', runtime_instance_id='compat-current-runtime')
            self.assertEqual(produced['status'], 'executed')
            manifest = json.loads((self.folder / 'private-manifest.json').read_bytes())
            self.assertEqual(manifest['engine_sha256'], CURRENT_ENGINE_SHA)
            before = fingerprint(self.folder)
            for method in ('run_rf_signal_scenario', 'evaluate_rf_signal_scenario'):
                stack.enter_context(mock.patch.object(rf_signal_scenario, method, side_effect=AssertionError('RF rerun')))
            source = reader.read_rf_signal_run(self.name)
            self.assertEqual(source['measurement'], dict(value=-18.0, unit='dBm', quantity='peak', reference_plane='sensor_input'))
            summary = observer.record_rf_baseband_observation(dict(
                schema_version=1, run_name=self.name, observation_name='genuine_current_055',
                sample_rate_hz=8, sample_count=2, seed=7))
            for method in ('generate_rf_baseband_envelope', 'analyze_rf_baseband_envelope'):
                stack.enter_context(mock.patch.object(waveform, method, side_effect=AssertionError('stored math recalculation')))
            try:
                value = observation_reader.read_rf_baseband_observation('genuine_current_055', expected_summary=summary)
            except observation_reader.RfSignalWaveformObservationReadError as error:
                self.fail('new genuine 055 record rejected by reader: ' + error.code)
            self.assertEqual(value['historical_context']['historical_assessment'], source['historical_assessment'])
            self.assertEqual(value['source']['manifest_sha256'], source['storage']['manifest_sha256'])
            self.assertIs(value['execution_authorized'], False)
            self.assertIs(value['rerun_authorized'], False)
            self.assertEqual(fingerprint(self.folder), before)

    def test_historical_failed_assessment_keeps_raw_value_without_claiming_goal(self):
        self.fixture(verdict='fail'); self.check_complete(self.invoke(), verdict='fail')

    def test_I2_with_marker_hides_saved_PASS_and_without_marker_does_not_guess_failure(self):
        self.fixture(); (self.folder / 'private-manifest.json').unlink(); self.failure()
        before = fingerprint(self.base); value = self.invoke()
        self.check_withheld(value, 'incomplete', 'failure_recorded')
        self.assertEqual(value['metadata']['execution_status'], 'failed_recorded')
        self.assertEqual(value['failure']['error_code'], 'rf_signal_scenario_evidence_unavailable')
        self.assertIsNone(value['metadata']['request']); self.assertEqual(fingerprint(self.base), before)
        (self.folder / 'failure.json').unlink(); self.backends.clear()
        value = self.invoke(); self.check_withheld(value, 'incomplete', 'incomplete')
        self.assertEqual(value['metadata']['execution_status'], 'unconfirmed'); self.assertIsNone(value['failure'])

    def test_prefix_journal_preserves_only_known_pair_and_does_not_infer_interrupt(self):
        self.fixture(prefix=True); before = fingerprint(self.base); value = self.invoke()
        self.check_withheld(value, 'incomplete', 'incomplete')
        self.assertEqual(value['storage']['journal_status'], 'partial')
        self.assertEqual(value['metadata'], dict(request=None, **self.ids, execution_status='unconfirmed'))
        self.assertIsNone(value['verification']['producer_cli_exit_status'])
        self.assertEqual(fingerprint(self.base), before)

    def test_valid_failure_marker_overrides_complete_bytes_saved_PASS(self):
        self.fixture(); self.failure(); before = fingerprint(self.base); value = self.invoke()
        self.check_withheld(value, 'complete_verified', 'failure_recorded')
        self.assertEqual(value['storage']['verified_file_count'], 3)
        self.assertEqual(value['metadata']['execution_status'], 'failed_recorded')
        self.assertEqual(fingerprint(self.base), before)

    def test_missing_required_files_is_incomplete_not_corrupt_or_reexecuted(self):
        self.fixture()
        for relative in ('private/author.json', 'operator/events.jsonl', 'public-result.json'):
            path = self.folder / relative; raw = path.read_bytes(); path.unlink(); before = fingerprint(self.base)
            self.check_withheld(self.invoke(), 'incomplete', 'incomplete')
            self.assertEqual(fingerprint(self.base), before)
            path.write_bytes(raw); self.backends.clear()

    def test_present_malformed_manifest_public_marker_and_journal_are_invalid(self):
        self.fixture()
        for relative in ('private-manifest.json', 'public-result.json', 'failure.json', 'operator/events.jsonl'):
            path = self.folder / relative; original = path.read_bytes() if path.exists() else None
            path.write_bytes(b'{PRIVATE truncated'); before = fingerprint(self.base); value = self.invoke()
            self.check_withheld(value, 'invalid', 'invalid')
            self.assertEqual(value['error_code'], 'rf_signal_read_evidence_invalid')
            self.assertNotIn('PRIVATE', encoded(value).decode())
            self.assertEqual(fingerprint(self.base), before)
            if original is None: path.unlink()
            else: path.write_bytes(original)
            self.backends.clear()

    def test_regular_parent_namespace_and_run_files_are_path_invalid(self):
        for relative in ('.local', '.local/rf-signal-runs', '.local/rf-signal-runs/run048'):
            path = self.base / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'preserve')
            before = fingerprint(self.base); self.assert_error('path_invalid')
            self.assertEqual(fingerprint(self.base), before); path.unlink(); self.backends.clear()

    def test_raw_root_alias_UNC_device_and_drive_relative_are_rejected_before_native(self):
        for path in (r'\\server\share\labflow\virtual_fleet\rf_signal_read.py',
                     r'\\?\C:\x\labflow\virtual_fleet\rf_signal_read.py',
                     r'C:labflow\virtual_fleet\rf_signal_read.py',
                     str(self.base) + '.\\labflow\\virtual_fleet\\rf_signal_read.py',
                     str(self.base) + r'\\labflow\virtual_fleet\rf_signal_read.py'):
            self.module_path = path; self.assert_error('path_invalid'); self.assertEqual(self.backends, [])

    def test_selected_and_nested_reparse_entries_are_rejected(self):
        self.namespace.mkdir(parents=True); target = self.base / 'test-owned-target'; target.mkdir()
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.folder), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assert_error('path_invalid'); self.assertEqual(list(target.iterdir()), [])
        self.folder.rmdir(); self.backends.clear(); self.fixture()
        events = (self.folder / 'operator/events.jsonl').read_bytes()
        (self.folder / 'operator/events.jsonl').unlink(); (self.folder / 'operator').rmdir()
        (target / 'events.jsonl').write_bytes(events)
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.folder / 'operator'), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        before = fingerprint(target); self.assert_error('path_invalid'); self.assertEqual(fingerprint(target), before)

    def test_controlled_remote_drive_and_backend_unavailable_fail_closed(self):
        self.folder.mkdir(parents=True)
        directory = native._WindowsIO.directory
        def remote(backend, path, **kwargs):
            if path == Path(path.anchor):
                with mock.patch.object(backend.kernel, 'GetDriveTypeW', return_value=4):
                    return directory(backend, path, **kwargs)
            return directory(backend, path, **kwargs)
        with mock.patch.object(native._WindowsIO, 'directory', new=remote): self.assert_error('path_invalid')
        self.backends.clear()
        with mock.patch.object(native, '_WINDOWS_BACKEND_AVAILABLE', False): self.assert_error('unavailable')

    def test_source_engine_journal_and_helper_pin_drift_precedes_evidence_reader(self):
        self.fixture()
        for relative in ('labflow/virtual_fleet/rf.py', 'labflow/virtual_fleet/journal.py', 'labflow/control_packet_prepare.py'):
            path = self.base / relative; raw = path.read_bytes(); path.write_bytes(raw + b'\n')
            with mock.patch.object(journal, 'read_operator_journal', side_effect=AssertionError('evidence read')) as read:
                self.assert_error('input_changed')
            read.assert_not_called(); path.write_bytes(raw); self.backends.clear()

    def test_source_LF_equivalence_and_name_case_are_read_without_normalizing_selection(self):
        self.fixture(); path = self.package / 'rf.py'; path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        before = fingerprint(self.base); value = self.invoke(name='RUN048')
        self.assertEqual(value['selection']['run_name'], 'RUN048')
        self.assertEqual(value['metadata']['run_id'], self.ids['run_id']); self.assertEqual(fingerprint(self.base), before)

    def test_file_sharing_permission_and_unknown_reader_errors_are_sanitized_unavailable(self):
        self.fixture(); opening = native._WindowsIO.open_read
        def denied(backend, path, **kwargs):
            if path == self.folder / 'public-result.json': raise PermissionError('PRIVATE share ' + str(self.base))
            return opening(backend, path, **kwargs)
        with mock.patch.object(native._WindowsIO, 'open_read', new=denied): self.assert_error('unavailable')
        self.backends.clear()
        with mock.patch.object(journal, 'read_operator_journal', side_effect=RuntimeError('PRIVATE parser')):
            with self.assertRaises(reader.RfSignalReadError) as error: self.invoke()
        self.assertEqual(error.exception.code, 'rf_signal_read_unavailable')
        self.assertIsNone(error.exception.__cause__); self.assertIsNone(error.exception.__context__)

    def test_malformed_failure_unknown_code_phase_types_and_extra_secret_never_reveal_PASS(self):
        self.fixture()
        for update in (dict(error_code='PRIVATE secret'), dict(phase='PRIVATE /path'), dict(dispatched=False),
                       dict(schema_version=True), dict(scenario_id='unknown'), dict(extra='PRIVATE secret')):
            self.failure(**update); before = fingerprint(self.base); value = self.invoke()
            self.check_withheld(value, 'invalid', 'invalid')
            self.assertNotIn('PRIVATE', encoded(value).decode()); self.assertEqual(fingerprint(self.base), before)
            self.backends.clear()

    def test_all_parent_six_failure_codes_and_null_dispatched_are_retained_as_records(self):
        self.fixture(); (self.folder / 'private-manifest.json').unlink()
        for code in ('invalid_request', 'unsupported_catalog', 'output_unavailable',
                     'execution_incomplete', 'evidence_invalid', 'evidence_unavailable'):
            self.failure(error_code='rf_signal_scenario_' + code, dispatched=None, phase='bootstrap')
            value = self.invoke(); self.check_withheld(value, 'incomplete', 'failure_recorded')
            self.assertEqual(value['failure']['error_code'], 'rf_signal_scenario_' + code)
            self.assertIsNone(value['failure']['dispatched']); self.backends.clear()

    def test_manifest_binding_keys_rows_visibility_pins_request_and_hashes_are_strict(self):
        self.fixture(); path = self.folder / 'private-manifest.json'; original = path.read_bytes()
        mutations = [
            lambda value: value.update(complete=False),
            lambda value: value['request'].update(seed=True),
            lambda value: value['request'].update(seed=2147483648),
            lambda value: value['request'].update(extra='PRIVATE'),
            lambda value: value.update(catalog_sha256='0' * 64),
            lambda value: value.update(engine_sha256='0' * 64),
            lambda value: value.update(topology_sha256='1' * 64),
            lambda value: value['files'].__setitem__(1, deepcopy(value['files'][0])),
            lambda value: value['files'][0].update(path='../escape'),
            lambda value: value['files'][0].update(bytes=True),
            lambda value: value['files'][0].update(sha256='0' * 64),
            lambda value: value['files'][2].update(visibility='operator'),
            lambda value: value.update(extra='PRIVATE'),
        ]
        for mutate in mutations:
            value = json.loads(original); mutate(value); path.write_bytes(encoded(value) + b'\n')
            self.check_withheld(self.invoke(), 'invalid', 'invalid'); self.backends.clear()
        path.write_bytes(original)

    def test_artifact_corruption_never_uses_other_stored_meter_or_repairs_original(self):
        self.fixture()
        for name in ('public-result.json', 'operator/events.jsonl', 'private/author.json'):
            path = self.folder / name; raw = path.read_bytes(); path.write_bytes(raw + b'corrupt')
            before = fingerprint(self.base); self.check_withheld(self.invoke(), 'invalid', 'invalid')
            self.assertEqual(fingerprint(self.base), before); path.write_bytes(raw); self.backends.clear()

    def test_returned_fields_cannot_conflate_or_leak_saved_private_and_current_status(self):
        self.fixture(); original = deepcopy(self.outer)
        mutations = [
            lambda value: value['report'].update(run_id='other-run'),
            lambda value: value['report'].update(runtime_instance_id='other-instance'),
            lambda value: value['verification'].update(hardware_verified=True),
            lambda value: value['assessment'].update(summary_code='PRIVATE /source'),
            lambda value: value['assessment'].update(evidence_refs=['file:/PRIVATE']),
            lambda value: value['declared_setup'].update(reference_plane='dut_output'),
            lambda value: value.update(source_path='PRIVATE'),
            lambda value: value.update(kind='virtual_fleet_harness_suite'),
        ]
        for mutate in mutations:
            self.outer = deepcopy(original); mutate(self.outer); self.publish(); before = fingerprint(self.base)
            value = self.invoke(); self.check_withheld(value, 'invalid', 'invalid')
            self.assertNotIn('PRIVATE', encoded(value).decode()); self.assertEqual(fingerprint(self.base), before)
            self.backends.clear()

    def test_final_assessment_event_is_required_and_earlier_or_ambiguous_refs_are_invalid(self):
        self.fixture()
        for refs in (['fixture048:observation:0'], ['fixture048:observation:0', 'fixture048:observation:1'],
                     ['unknown-observation']):
            self.outer['assessment']['evidence_refs'] = refs; self.publish()
            self.check_withheld(self.invoke(), 'invalid', 'invalid'); self.backends.clear()

    def test_projection_finite_unit_quantity_and_nested_shapes_are_checked_without_RF_evaluation(self):
        self.fixture(); original = deepcopy(self.events)
        mutations = [
            lambda value: value.update(unit='W'),
            lambda value: value.update(quantity='time_average'),
            lambda value: value.update(value=True),
            lambda value: value.update(value='PRIVATE'),
        ]
        for mutate in mutations:
            self.events = deepcopy(original)
            sample = self.events[1]['payload']['observation']['devices']['meter']['values']['outputs']['measurement']
            mutate(sample); self.write_journal(self.events); self.publish()
            self.check_withheld(self.invoke(), 'invalid', 'invalid'); self.backends.clear()
        self.events = deepcopy(original)
        self.events[1]['payload']['observation']['devices']['meter']['values']['outputs'] = []
        self.write_journal(self.events); self.publish()
        self.check_withheld(self.invoke(), 'invalid', 'invalid')

    def test_journal_provenance_mixed_ID_and_complete_marker_are_not_interchangeable(self):
        self.fixture()
        self.provenance['engine_sha256'] = '0' * 64; self.write_journal(self.events); self.publish()
        self.check_withheld(self.invoke(), 'invalid', 'invalid'); self.backends.clear()
        self.provenance['engine_sha256'] = ENGINE_SHA; self.write_journal(self.events[:-1]); self.publish()
        self.check_withheld(self.invoke(), 'invalid', 'invalid')

    def test_new_marker_or_manifest_during_read_discards_mixed_snapshot(self):
        self.fixture(); original = journal.read_operator_journal
        def late_marker(path):
            value = original(path); self.failure(); return value
        with mock.patch.object(journal, 'read_operator_journal', side_effect=late_marker): self.assert_error('input_changed')
        (self.folder / 'failure.json').unlink(); (self.folder / 'private-manifest.json').unlink(); self.backends.clear()
        def late_manifest(path):
            value = original(path); self.reseal(); return value
        with mock.patch.object(journal, 'read_operator_journal', side_effect=late_manifest): self.assert_error('input_changed')

    def test_late_source_change_is_input_changed_and_no_new_runtime_or_repair(self):
        self.fixture(); original = journal.read_operator_journal
        def reading(path):
            value = original(path)
            with (self.package / 'rf.py').open('ab') as stream: stream.write(b'\n')
            return value
        with mock.patch.object(journal, 'read_operator_journal', side_effect=reading): self.assert_error('input_changed')

    def test_controlled_post_read_file_or_directory_identity_change_is_input_changed(self):
        self.fixture(); original_read = journal.read_operator_journal; original_stat = native._WindowsIO.stat_file
        for target in (self.folder, self.folder / 'public-result.json'):
            state = {'changed': False}
            def reading(path):
                value = original_read(path); state['changed'] = True; return value
            def changed(backend, path):
                value = original_stat(backend, path)
                if path == target and state['changed']:
                    fields = {key: getattr(value, key) for key in
                              ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_mode', 'st_file_attributes')}
                    fields['st_ino'] += 1; return SimpleNamespace(**fields)
                return value
            with mock.patch.object(journal, 'read_operator_journal', side_effect=reading), \
                    mock.patch.object(native._WindowsIO, 'stat_file', new=changed):
                self.assert_error('input_changed')
            self.backends.clear()

    def test_controlled_descriptor_byte_change_with_same_stamp_is_input_changed(self):
        self.fixture(); original_read = journal.read_operator_journal
        original_open = native._WindowsIO.open_read; original_os_read = os.read; paths = {}; state = {'changed': False}
        def opening(backend, path, **kwargs):
            descriptor = original_open(backend, path, **kwargs); paths[descriptor] = path; return descriptor
        def reading(path):
            value = original_read(path); state['changed'] = True; return value
        def altered(descriptor, count):
            value = original_os_read(descriptor, count)
            if value and state['changed'] and paths.get(descriptor) == self.folder / 'private/author.json':
                return value + b'controlled-difference'
            return value
        with mock.patch.object(native._WindowsIO, 'open_read', new=opening), \
                mock.patch.object(journal, 'read_operator_journal', side_effect=reading), \
                mock.patch.object(os, 'read', side_effect=altered):
            self.assert_error('input_changed')

    def test_pinned_source_files_cannot_be_written_renamed_or_deleted_while_reading(self):
        self.fixture(); original = journal.read_operator_journal; attempts = []
        def reading(path):
            value = original(path)
            for target in (self.folder / 'public-result.json', self.folder / 'private/author.json'):
                with self.assertRaises(OSError): target.write_bytes(b'forbidden write')
                with self.assertRaises(OSError): target.unlink()
                attempts.append(target.name)
            with self.assertRaises(OSError): self.folder.rename(self.folder.with_name('renamed'))
            return value
        before = fingerprint(self.base)
        with mock.patch.object(journal, 'read_operator_journal', side_effect=reading): self.check_complete(self.invoke())
        self.assertEqual(attempts, ['public-result.json', 'author.json']); self.assertEqual(fingerprint(self.base), before)
        # All pins are gone after the call; rename only this test-owned fixture, then restore.
        moved = self.folder.with_name('released'); self.folder.rename(moved); moved.rename(self.folder)

    def test_cleanup_failure_preserves_first_fixed_error_or_invalid_state(self):
        self.fixture()
        self.assert_error('unavailable', close_error=True); self.backends.clear()
        (self.folder / 'failure.json').write_bytes(b'PRIVATE invalid')
        self.check_withheld(self.invoke(close_error=True), 'invalid', 'invalid'); self.backends.clear()
        with (self.package / 'rf.py').open('ab') as stream: stream.write(b'\n')
        self.assert_error('input_changed', close_error=True)

    def test_DTO_is_detached_and_caller_cwd_streams_unchanged(self):
        self.fixture(); before = fingerprint(self.base); original_cwd = Path.cwd()
        with mock.patch.object(Path, 'cwd', side_effect=AssertionError('cwd lookup')):
            value = self.invoke()
        self.assertEqual(Path.cwd(), original_cwd)
        value['historical_assessment']['verdict'] = 'PRIVATE'
        value['metadata']['request']['seed'] = -99
        self.check_complete(self.invoke()); self.assertEqual(fingerprint(self.base), before)

    def test_all_five_artifact_caps_reject_oversized_files_without_reading_their_full_bytes(self):
        self.fixture(); limits = {'private-manifest.json': 65536, 'public-result.json': 327680,
                                 'operator/events.jsonl': 33554432, 'private/author.json': 1048576,
                                 'failure.json': 65536}
        original_read = journal.read_operator_journal
        for name, limit in limits.items():
            path = self.folder / name; original = path.read_bytes() if path.exists() else None
            with path.open('wb') as stream:
                stream.seek(limit); stream.write(b'x')
            stamp = path.stat().st_size, path.stat().st_mtime_ns
            with mock.patch.object(journal, 'read_operator_journal', wraps=original_read) as read:
                self.check_withheld(self.invoke(), 'invalid', 'invalid')
            if name == 'operator/events.jsonl': read.assert_not_called()
            self.assertEqual((path.stat().st_size, path.stat().st_mtime_ns), stamp)
            if original is None: path.unlink()
            else: path.write_bytes(original)
            self.backends.clear()

    def test_JSON_duplicate_keys_nonfinite_depth_and_string_budget_are_not_normalized(self):
        self.fixture()
        for name, key, value in [('private-manifest.json', 'complete', 'true'),
                                 ('public-result.json', 'status', '"executed"')]:
            path = self.folder / name; original = path.read_bytes()
            path.write_bytes(original.rstrip()[:-1] + (',"'+key+'":'+value+'}\n').encode())
            self.check_withheld(self.invoke(), 'invalid', 'invalid')
            path.write_bytes(original); self.backends.clear()
        self.failure(); path = self.folder / 'failure.json'; original = path.read_bytes()
        path.write_bytes(original.rstrip()[:-1] + b',"phase":"artifact_write"}\n')
        self.check_withheld(self.invoke(), 'invalid', 'invalid')
        path.unlink(); self.backends.clear()
        original_outer = deepcopy(self.outer)
        self.outer['declared_setup']['source_signal']['modulation'] = 'x' * 16384
        self.publish(); self.check_complete(self.invoke()); self.backends.clear()
        self.outer['declared_setup']['source_signal']['modulation'] += 'x'; self.publish()
        self.check_withheld(self.invoke(), 'invalid', 'invalid'); self.backends.clear()
        self.outer = deepcopy(original_outer); raw = encoded(self.outer).replace(b'12.5', b'Infinity')
        (self.folder / 'public-result.json').write_bytes(raw); self.reseal()
        self.check_withheld(self.invoke(), 'invalid', 'invalid'); self.backends.clear()
        self.outer = deepcopy(original_outer); raw = encoded(self.outer).rstrip()[:-1] + b',"extra":' + b'[' * 30 + b'0' + b']' * 30 + b'}'
        (self.folder / 'public-result.json').write_bytes(raw); self.reseal()
        self.check_withheld(self.invoke(), 'invalid', 'invalid')

    def test_JSON_node_budget_is_separate_from_byte_cap(self):
        self.fixture(); self.events[1]['event_id'] = 'o'
        self.outer['assessment']['evidence_refs'] = ['o']; self.write_journal(self.events)
        self.outer['report']['evidence']['measurement_refs'] = ['o'] * 16000
        self.publish(); self.check_complete(self.invoke()); self.backends.clear()
        self.outer['report']['evidence']['measurement_refs'] = ['o'] * 16400
        self.publish(); self.assertLess((self.folder / 'public-result.json').stat().st_size, 327680)
        self.check_withheld(self.invoke(), 'invalid', 'invalid')

    def test_opaque_author_bytes_are_not_JSON_decoded_and_unknown_neighbor_files_are_never_opened(self):
        self.fixture(); sentinel = self.folder / 'ignored-original.txt'; sentinel.write_bytes(b'PRIVATE')
        decode = json.loads; open_read = native._WindowsIO.open_read; seen = []
        def decoded(value, *args, **kwargs):
            self.assertNotIn('opaque-not-JSON', str(value))
            return decode(value, *args, **kwargs)
        def opening(backend, path, **kwargs):
            seen.append(path)
            self.assertNotEqual(path, sentinel)
            return open_read(backend, path, **kwargs)
        with mock.patch.object(json, 'loads', side_effect=decoded), \
                mock.patch.object(native._WindowsIO, 'open_read', new=opening):
            self.check_complete(self.invoke())
        self.assertEqual({path.relative_to(self.folder).as_posix() for path in seen},
                         {'private-manifest.json', 'public-result.json', 'operator/events.jsonl',
                          'private/author.json'})
        self.assertEqual(sentinel.read_bytes(), b'PRIVATE')

    def test_missing_entry_after_public_read_is_changed_not_a_new_incomplete_result(self):
        self.fixture(); original = journal.read_operator_journal; stat_file = native._WindowsIO.stat_file
        state = {'changed': False}
        def reading(path):
            value = original(path); state['changed'] = True; return value
        def disappeared(backend, path):
            if state['changed'] and path == self.folder / 'private/author.json':
                raise FileNotFoundError('PRIVATE controlled disappearance')
            return stat_file(backend, path)
        with mock.patch.object(journal, 'read_operator_journal', side_effect=reading), \
                mock.patch.object(native._WindowsIO, 'stat_file', new=disappeared):
            self.assert_error('input_changed')

    def test_failure_marker_scenario_conflict_is_invalid_not_an_override_to_different_run(self):
        self.fixture(); self.failure(scenario_id='cw_peak')
        self.check_withheld(self.invoke(), 'invalid', 'invalid')

    def test_coherent_test_owned_copy_is_selected_without_inventing_producer_name_or_exit(self):
        self.fixture(); before = fingerprint(self.folder)
        copied = self.namespace / 'coherent-copy'; shutil.copytree(self.folder, copied)
        value = self.invoke(name='coherent-copy')
        self.assertEqual(value['selection'], {'run_name': 'coherent-copy'})
        self.assertEqual(value['metadata']['run_id'], self.ids['run_id'])
        self.assertEqual(value['storage']['status'], 'complete_verified')
        self.assertIsNone(value['verification']['producer_cli_exit_status'])
        self.assertEqual(set(value), KEYS); self.assertEqual(fingerprint(self.folder), before)

    def test_journal_storage_error_with_disappeared_entry_is_changed_and_stable_error_unavailable(self):
        self.fixture(); original_stat = native._WindowsIO.stat_file; state = {'lost': False}
        def unavailable(path):
            state['lost'] = True
            raise journal.JournalStorageError('PRIVATE controlled read failure')
        def disappeared(backend, path):
            if state['lost'] and path == self.folder / 'operator/events.jsonl':
                raise FileNotFoundError('PRIVATE changed entry')
            return original_stat(backend, path)
        with mock.patch.object(journal, 'read_operator_journal', side_effect=unavailable), \
                mock.patch.object(native._WindowsIO, 'stat_file', new=disappeared):
            self.assert_error('input_changed')
        self.backends.clear()
        with mock.patch.object(journal, 'read_operator_journal', side_effect=journal.JournalStorageError('PRIVATE stable error')):
            self.assert_error('unavailable')

    def test_known_hash_damage_is_invalid_even_when_a_different_required_file_is_missing(self):
        self.fixture()
        for absent, damaged in [('private/author.json', 'public-result.json'),
                                 ('public-result.json', 'private/author.json'),
                                 ('operator/events.jsonl', 'private/author.json')]:
            absent_path, damaged_path = self.folder / absent, self.folder / damaged
            absent_raw, damaged_raw = absent_path.read_bytes(), damaged_path.read_bytes()
            absent_path.unlink(); damaged_path.write_bytes(damaged_raw + b'\n')
            try:
                with self.subTest(absent=absent, damaged=damaged):
                    before = fingerprint(self.base)
                    self.check_withheld(self.invoke(), 'invalid', 'invalid')
                    self.assertEqual(fingerprint(self.base), before)
            finally:
                absent_path.write_bytes(absent_raw); damaged_path.write_bytes(damaged_raw); self.backends.clear()

    def test_escaped_unpaired_surrogate_is_invalid_while_Unicode_scalar_text_is_preserved_as_opaque(self):
        self.fixture(); original = encoded(self.outer); path = self.folder / 'public-result.json'
        path.write_bytes(original.replace(b'"OFDM"', b'"\\ud83e\\uddea"')); self.reseal()
        self.check_complete(self.invoke()); self.backends.clear()
        path.write_bytes(original.replace(b'"OFDM"', b'"\\ud800"')); self.reseal()
        self.check_withheld(self.invoke(), 'invalid', 'invalid')


if __name__ == '__main__':
    unittest.main()
