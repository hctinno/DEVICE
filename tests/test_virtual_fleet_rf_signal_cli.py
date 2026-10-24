"""045 strict entry and genuine synthetic execution; fault doubles are explicit."""
from contextlib import ExitStack
from io import StringIO
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from labflow import control_packet_prepare as native
from labflow.virtual_fleet import catalog, integration, journal, rf_signal_scenario as scenario

cli = (importlib.import_module('labflow.virtual_fleet.rf_signal_cli')
       if importlib.util.find_spec('labflow.virtual_fleet.rf_signal_cli') else None)
SCENARIOS = ('pulsed_on_mean', 'pulsed_time_mean', 'pulsed_peak', 'cw_peak',
             'shifted_frequency', 'sensor_uncalibrated', 'meter_frequency_conflict')
ARGS = ['--scenario', 'pulsed_peak', '--seed', '7', '--run-name', 'test045']
ROOT = Path(__file__).resolve().parents[1]
SUMMARY_KEYS = set('schema_version kind request run_id status assessment measurement '
                   'measurement_goal_succeeded output manifest_verified verification '
                   'execution_authorized rerun_authorized error_code'.split())
VALUES = (-18.0, -24.020599913279625, -15.0, -18.0, -18.0, None, None)
QUANTITIES = ('on_average', 'time_average', 'peak', 'peak', 'on_average', None, None)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


class RfSignalCliArgumentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cli, '045 public main module is absent')

    def before_io(self, args, expected=2, code='rf_signal_cli_invalid_argument'):
        out, err = StringIO(), StringIO()
        with ExitStack() as stack:
            calls = [stack.enter_context(mock.patch.object(obj, name, side_effect=AssertionError('unexpected IO')))
                     for obj, name in [(Path, 'open'), (native, '_WindowsIO'), (catalog, 'load_catalog'),
                                       (scenario, 'run_rf_signal_scenario'), (integration, 'create_conducted_example')]]
            stack.enter_context(mock.patch.object(sys, 'stdout', out))
            stack.enter_context(mock.patch.object(sys, 'stderr', err))
            result = cli.main(args)
        self.assertEqual(result, expected)
        self.assertFalse(out.closed); self.assertFalse(err.closed)
        for call in calls: call.assert_not_called()
        if expected == 0:
            self.assertEqual(err.getvalue(), '')
            for word in ('--scenario', '--seed', '--run-name', *SCENARIOS, '가상'):
                self.assertIn(word, out.getvalue())
        else:
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(json.loads(err.getvalue()), {'error': {'code': code}})

    def test_public_main_is_callable(self):
        self.assertTrue(callable(cli.main))

    def test_static_help_performs_no_user_catalog_native_or_run_IO(self):
        self.before_io(['--help'], 0)

    def test_missing_duplicate_unknown_equal_atfile_positional_and_help_mix_rejected(self):
        for args in ([], ARGS[:-2], ARGS + ['--seed', '7'], ['--scen', *ARGS[1:]],
                     ['--scenario=pulsed_peak', *ARGS[2:]], ['@file'], ARGS + ['x'],
                     ARGS + ['--help'], ['--help', '--help'], ['--catalog', *ARGS[1:]]):
            with self.subTest(args=args): self.before_io(args)

    def test_only_plain_list_or_tuple_and_plain_strings_are_accepted(self):
        class Hostile(str):
            def __str__(self): raise AssertionError('callback')
        for args in (False, ' '.join(ARGS), dict(zip(ARGS[::2], ARGS[1::2])),
                     [Hostile('--scenario'), *ARGS[1:]], [Hostile('--help')], [*ARGS[:-1], None]):
            self.before_io(args)

    def test_seed_is_bounded_canonical_ASCII_without_normalization(self):
        for seed in ('', '-1', '+1', '00', '07', '2147483648', '1.0', ' 7', '7 ', '７', '٧', '7\n', '1' * 10000):
            args = ARGS[:]; args[3] = seed
            with self.subTest(seed=seed[:20]): self.before_io(args)

    def test_scenario_and_run_name_are_literal_and_path_free(self):
        for sid in ('PULSED_PEAK', 'pulsed_peak ', '', 'normal', '../pulsed_peak'):
            args = ARGS[:]; args[1] = sid; self.before_io(args)
        for name in ('', '.', '..', '../escape', r'a\b', '/abs', 'C:foo', 'CON', 'aux', 'LPT1', 'COM9',
                     'NUL', 'a.', 'a ', ' a', '-a', '_a', '한글', 'a' * 65, 'a\n'):
            args = ARGS[:]; args[-1] = name
            with self.subTest(name=name): self.before_io(args)


class RfSignalCliExecutionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cli, '045 public main module is absent')
        parent = ROOT / '.local' / 'rf045-tests'; parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=parent); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        shutil.copytree(ROOT / 'labflow', self.base / 'labflow', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.base / 'virtual_profiles').mkdir()
        shutil.copyfile(ROOT / 'virtual_profiles/sm_a176u_unlicensed.json',
                        self.base / 'virtual_profiles/sm_a176u_unlicensed.json')
        self.module_path = self.base / 'labflow/virtual_fleet/rf_signal_cli.py'
        self.namespace = self.base / '.local/rf-signal-runs'
        self.args = ARGS[:]
        self.backends = []

    def invoke(self, args=None, *, effect=None, output=None, close_error=False, use_sys_argv=False):
        out, err = output if output is not None else StringIO(), StringIO()
        original_backend = native._WindowsIO
        def backend():
            value = original_backend(); self.backends.append(value)
            close = value.close
            def closing():
                close()
                if close_error: raise OSError('PRIVATE cleanup')
            value.close = mock.Mock(side_effect=closing)
            return value
        with mock.patch.object(cli, '__file__', str(self.module_path)), \
                mock.patch.object(native, '_WindowsIO', side_effect=backend), \
                mock.patch.object(scenario, 'run_rf_signal_scenario', wraps=scenario.run_rf_signal_scenario,
                                  side_effect=effect) as run, \
                mock.patch.object(integration, 'create_conducted_example', wraps=integration.create_conducted_example) as factory, \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            status = cli.main(None if use_sys_argv else self.args if args is None else args)
        for value in self.backends:
            value.close.assert_called_once(); self.assertEqual(value.held, []); self.assertEqual(value.directories, {})
        self.assertFalse(out.closed); self.assertFalse(err.closed)
        return status, out.getvalue(), err.getvalue(), run, factory

    def assert_error(self, result, code, status=1, calls=0):
        actual, out, err, run, factory = result
        self.assertEqual((actual, out, json.loads(err)), (status, '', {'error': {'code': code}}))
        self.assertEqual(run.call_count, calls)
        if calls == 0: factory.assert_not_called()
        self.assertNotIn(str(self.base), err)

    def check_summary(self, raw, *, sid, seed=7, output=None):
        value = json.loads(raw)
        self.assertEqual(encoded(value) + b'\n', raw.encode('utf-8'))
        self.assertLessEqual(len(raw.encode('utf-8')), 8192)
        self.assertEqual(set(value), SUMMARY_KEYS)
        self.assertEqual(value['request'], dict(schema_version=1, scenario_id=sid, seed=seed))
        self.assertEqual(value['kind'], 'virtual_rf_signal_cli_result')
        self.assertEqual(value['status'], 'executed'); self.assertTrue(value['manifest_verified'])
        self.assertEqual(value['assessment']['verdict'], 'pass')
        self.assertFalse(value['execution_authorized']); self.assertFalse(value['rerun_authorized'])
        self.assertEqual(len(value['assessment']), 5); self.assertEqual(len(value['verification']), 10)
        folder = output if output is not None else self.base / value['output']
        manifest = json.loads((folder / 'private-manifest.json').read_bytes())
        outer = json.loads((folder / 'public-result.json').read_bytes())
        self.assertEqual(value['assessment'], outer['assessment']); self.assertEqual(value['verification'], outer['verification'])
        for row in manifest['files']:
            data = (folder / row['path']).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (row['bytes'], row['sha256']))
        stored = journal.read_operator_journal(folder / 'operator/events.jsonl')
        self.assertEqual(value['run_id'], stored['header']['run_id'])
        self.assertNotEqual(value['run_id'], stored['header']['runtime_instance_id'])
        observations = [e for e in stored['events'] if e['type'] == 'observation']
        self.assertEqual(value['assessment']['evidence_refs'], [observations[-1]['event_id']])
        packet = observations[-1]['payload']['observation']['devices']['meter']['values']['outputs'].get('measurement')
        index = SCENARIOS.index(sid)
        self.assertEqual(value['measurement_goal_succeeded'], index < 5)
        if packet is None:
            self.assertIsNone(value['measurement']); self.assertIsNone(VALUES[index])
        else:
            self.assertEqual(value['measurement'], dict(value=packet['value'], unit=packet['unit'],
                             quantity=packet['quantity'], reference_plane='sensor_input'))
            self.assertEqual((packet['value'], packet['quantity']), (VALUES[index], QUANTITIES[index]))
        self.assertNotIn(str(self.base), raw); self.assertNotIn('oracle', raw)
        return value

    def test_genuine_public_run_once_per_seven_scenarios_without_duplicate_factory(self):
        for sid in SCENARIOS:
            self.args = ['--scenario', sid, '--seed', '7', '--run-name', sid]
            status, out, err, run, factory = self.invoke()
            self.assertEqual((status, err), (0, '')); run.assert_called_once(); factory.assert_called_once()
            self.check_summary(out, sid=sid)
            self.backends.clear()

    def test_source_041_engine_and_native_helper_pins_fail_before_load_and_directory_creation(self):
        for relative in ('labflow/virtual_fleet/rf_signal_scenario.py', 'labflow/virtual_fleet/rf.py',
                         'labflow/control_packet_prepare.py'):
            path = self.base / relative; original = path.read_bytes(); path.write_bytes(original + b'\n')
            with mock.patch.object(catalog, 'load_catalog', side_effect=AssertionError('catalog called')) as loaded:
                self.assert_error(self.invoke(), 'rf_signal_cli_input_changed')
            loaded.assert_not_called(); self.assertFalse((self.base / '.local').exists())
            path.write_bytes(original); self.backends.clear()

    def test_catalog_canonical_change_rejected_and_key_whitespace_equivalence_accepted(self):
        path = self.base / 'virtual_profiles/sm_a176u_unlicensed.json'
        value = json.loads(path.read_bytes()); original = deepcopy(value)
        value['catalog_id'] = 'unexpected'
        path.write_bytes(encoded(value))
        self.assert_error(self.invoke(), 'rf_signal_cli_input_changed')
        self.assertFalse((self.base / '.local').exists()); self.backends.clear()
        path.write_text(json.dumps(original, ensure_ascii=False, sort_keys=True, indent=3), encoding='utf-8')
        status, out, err, run, factory = self.invoke()
        self.assertEqual((status, err), (0, '')); self.check_summary(out, sid='pulsed_peak')

    def test_existing_run_name_rejected_before_catalog_and_run_with_bytes_preserved(self):
        folder = self.namespace / 'test045'; folder.mkdir(parents=True); (folder / 'original').write_bytes(b'preserve')
        before = snapshot(folder)
        with mock.patch.object(catalog, 'load_catalog', side_effect=AssertionError('catalog called')) as loaded:
            self.assert_error(self.invoke(), 'rf_signal_cli_output_invalid', 2)
        loaded.assert_not_called(); self.assertEqual(snapshot(folder), before)

    def test_backend_unavailable_is_closed_failure_without_run_or_new_output(self):
        with mock.patch.object(cli, '__file__', str(self.module_path)), \
                mock.patch.object(native, '_WINDOWS_BACKEND_AVAILABLE', False):
            self.assert_error(self.invoke(), 'rf_signal_cli_unavailable')
        self.assertFalse((self.base / '.local').exists())

    def test_reparse_parent_and_lexical_trailing_dot_alias_are_output_invalid(self):
        target = self.base / 'target'; target.mkdir()
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.base / '.local'), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assert_error(self.invoke(), 'rf_signal_cli_output_invalid', 2)
        self.assertEqual(list(target.iterdir()), [])
        (self.base / '.local').rmdir(); self.backends.clear()
        self.module_path = str(self.base) + '.\\labflow\\virtual_fleet\\rf_signal_cli.py'
        self.assert_error(self.invoke(), 'rf_signal_cli_output_invalid', 2)

    def test_041_saved_executed_with_failed_manifest_or_sidecar_keeps_failed_return(self):
        original = scenario.run_rf_signal_scenario
        for sidecar_fails in (False, True):
            self.args[-1] = 'failed' + str(int(sidecar_fails)); captured = {}
            def execute(*args, **kwargs):
                opened = Path.open
                def opening(path, *values, **options):
                    if path.name == 'private-manifest.json' or sidecar_fails and path.name == 'failure.json':
                        raise OSError('PRIVATE controlled storage failure')
                    return opened(path, *values, **options)
                with mock.patch.object(Path, 'open', new=opening): result = original(*args, **kwargs)
                captured['folder'] = Path(args[2]); captured['before'] = snapshot(captured['folder'])
                captured['saved'] = json.loads((captured['folder'] / 'public-result.json').read_bytes())
                return result
            status, out, err, run, factory = self.invoke(effect=execute)
            value = json.loads(out)
            self.assertEqual((status, err, value['status']), (1, '', 'failed'))
            self.assertEqual(value['error_code'], 'rf_signal_scenario_evidence_unavailable')
            self.assertEqual(captured['saved']['status'], 'executed')
            self.assertEqual(captured['saved']['assessment']['verdict'], 'pass')
            self.assertFalse(value['manifest_verified']); self.assertFalse(value['measurement_goal_succeeded'])
            self.assertIsNone(value['measurement']); self.assertIsNone(value['assessment']['verdict'])
            self.assertEqual(snapshot(captured['folder']), captured['before'])
            run.assert_called_once(); factory.assert_called_once(); self.backends.clear()

    def test_post_run_source_change_is_input_changed_without_retry_or_evidence_deletion(self):
        original = scenario.run_rf_signal_scenario; captured = {}
        def execute(*args, **kwargs):
            result = original(*args, **kwargs); captured['folder'] = Path(args[2])
            captured['before'] = snapshot(captured['folder'])
            with (self.base / 'labflow/virtual_fleet/rf.py').open('ab') as stream: stream.write(b'\n')
            return result
        self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_input_changed', calls=1)
        self.assertEqual(snapshot(captured['folder']), captured['before'])

    def test_keyboard_interrupt_after_genuine_journal_creation_preserves_partial_and_closes(self):
        with mock.patch.object(scenario.FleetHarness, 'run', side_effect=KeyboardInterrupt):
            result = self.invoke()
        self.assert_error(result, 'rf_signal_cli_interrupted', 130, calls=1)
        folder = self.namespace / 'test045'; events = folder / 'operator/events.jsonl'
        self.assertTrue(events.is_file()); self.assertFalse((folder / 'private-manifest.json').exists())
        self.assertFalse(journal.read_operator_journal(events)['complete'])
        renamed = folder.with_name('retained-interrupt'); folder.rename(renamed); renamed.rename(folder)

    def test_tuple_reordered_options_seed_boundaries_and_sys_argv(self):
        for index, seed in enumerate(('0', '2147483647')):
            name = 'A' * 64 if index == 0 else 'COM10'
            args = ('--run-name', name, '--seed', seed, '--scenario', 'cw_peak')
            with mock.patch.object(sys, 'argv', ['rf_signal_cli', *args]):
                status, out, err, run, factory = self.invoke(args=args, use_sys_argv=bool(index))
            self.assertEqual((status, err), (0, ''))
            self.check_summary(out, sid='cw_peak', seed=int(seed))
            run.assert_called_once(); factory.assert_called_once(); self.backends.clear()

    def test_executed_manifest_or_any_of_three_artifacts_incomplete_never_summary_PASS(self):
        original = scenario.run_rf_signal_scenario
        for index, relative in enumerate(('private-manifest.json', 'public-result.json',
                                          'operator/events.jsonl', 'private/author.json')):
            self.args[-1] = 'incomplete' + str(index); captured = {}
            def execute(*args, **kwargs):
                result = original(*args, **kwargs); folder = Path(args[2])
                (folder / relative).write_bytes(b'partial synthetic fault')
                captured['folder'] = folder; captured['before'] = snapshot(folder)
                return result
            self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_output_failed', calls=1)
            self.assertEqual(snapshot(captured['folder']), captured['before']); self.backends.clear()

    def test_return_binding_flags_unknown_code_and_private_summary_text_fail_closed(self):
        original = scenario.run_rf_signal_scenario
        mutations = [
            lambda value: value['report'].update(run_id='other-run'),
            lambda value: value['report'].update(runtime_instance_id='other-instance'),
            lambda value: value['verification'].update(hardware_verified=True),
            lambda value: value.update(status='failed', error_code='PRIVATE ' + str(self.base)),
            lambda value: value['assessment'].update(summary_code='PRIVATE ' + str(self.base)),
            lambda value: value.update(extra='PRIVATE'),
        ]
        for index, mutate in enumerate(mutations):
            self.args[-1] = 'return' + str(index)
            def execute(*args, **kwargs):
                value = original(*args, **kwargs); mutate(value); return value
            self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_unavailable', calls=1)
            self.backends.clear()

    def test_public_journal_selection_must_match_explicit_latest_assessment_event(self):
        original = scenario.run_rf_signal_scenario
        def execute(*args, **kwargs):
            result = original(*args, **kwargs); folder = Path(args[2])
            observed = journal.read_operator_journal(folder / 'operator/events.jsonl')
            result['assessment']['evidence_refs'] = [observed['events'][0]['event_id']]
            self.publish_controlled_return(folder, result)
            return result
        self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_output_failed', calls=1)

    def publish_controlled_return(self, folder, value):
        # Offline fault injection, not a new evaluator or an actual RF execution.
        path = folder / 'public-result.json'; path.write_bytes(encoded(value) + b'\n')
        manifest_path = folder / 'private-manifest.json'; manifest = json.loads(manifest_path.read_bytes())
        row = next(row for row in manifest['files'] if row['path'] == 'public-result.json')
        raw = path.read_bytes(); row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest_path.write_bytes(encoded(manifest) + b'\n')

    def test_completed_assessment_fail_still_projects_original_value_and_exits_one(self):
        original = scenario.run_rf_signal_scenario
        def execute(*args, **kwargs):
            value = original(*args, **kwargs)
            value['assessment'].update(verdict='fail', summary_code='scenario_expectation_mismatch')
            self.publish_controlled_return(Path(args[2]), value)
            return value
        status, out, err, run, factory = self.invoke(effect=execute)
        value = json.loads(out)
        self.assertEqual((status, err, value['assessment']['verdict']), (1, '', 'fail'))
        self.assertTrue(value['manifest_verified']); self.assertEqual(value['measurement']['value'], -15.0)
        self.assertFalse(value['measurement_goal_succeeded'])
        run.assert_called_once(); factory.assert_called_once()

    def test_all_parent_fixed_six_failed_or_rejected_codes_preserved_without_saved_PASS_read(self):
        codes = ('invalid_request', 'unsupported_catalog', 'output_unavailable',
                 'execution_incomplete', 'evidence_invalid', 'evidence_unavailable')
        for index, code in enumerate(codes):
            self.args[-1] = 'parent' + str(index)
            def execute(*args, **kwargs):
                return dict(schema_version=1, kind='virtual_rf_signal_scenario', scenario_id='pulsed_peak',
                            status='rejected' if index < 3 else 'failed', declared_setup=None, report=None,
                            assessment=dict(status='not_assessed', verdict=None, evaluator_id=None,
                                            evidence_refs=[], summary_code=None), artifacts=[],
                            error_code='rf_signal_scenario_' + code,
                            verification=dict(data_origin='authored_synthetic', execution_mode='synthetic_virtual_execution',
                                              synthetic=True, hardware_verified=False, physical_verified=False,
                                              ai_model_called=False, normative_compliance_verified=False,
                                              method_approval='not_assessed', regulatory_scope_complete=False,
                                              waveform_implemented=False))
            with mock.patch.object(journal, 'read_operator_journal', side_effect=AssertionError('old PASS read')) as read:
                status, out, err, run, factory = self.invoke(effect=execute)
            value = json.loads(out); self.assertEqual((status, err, value['error_code']), (1, '', 'rf_signal_scenario_' + code))
            self.assertIsNone(value['measurement']); self.assertFalse(value['manifest_verified'])
            run.assert_called_once(); factory.assert_not_called(); read.assert_not_called(); self.backends.clear()

    def test_identity_change_after_run_is_input_changed_and_owned_handles_are_returned(self):
        original = scenario.run_rf_signal_scenario; state = {'returned': False}
        def execute(*args, **kwargs):
            value = original(*args, **kwargs); state['returned'] = True; return value
        stat_file = native._WindowsIO.stat_file
        def changed(backend, path):
            info = stat_file(backend, path)
            if state['returned'] and path == self.base / '.local':
                raise ValueError('PRIVATE changed native entry')
            return info
        with mock.patch.object(native._WindowsIO, 'stat_file', new=changed):
            self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_input_changed', calls=1)

    def test_std_stream_write_short_flush_and_closed_errors_are_one_without_rerun(self):
        class Failing(StringIO):
            def __init__(self, mode): super().__init__(); self.mode = mode
            def write(self, text):
                if self.mode == 'write': raise OSError('PRIVATE stdout')
                if self.mode == 'short': return len(text) - 1
                return super().write(text)
            def flush(self):
                if self.mode == 'flush': raise OSError('PRIVATE flush')
                return super().flush()
        for mode in ('write', 'short', 'flush'):
            self.args[-1] = mode
            status, out, err, run, factory = self.invoke(output=Failing(mode), close_error=True)
            self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'rf_signal_cli_output_failed'}}))
            run.assert_called_once(); factory.assert_called_once(); self.backends.clear()
            self.assertTrue((self.namespace / mode / 'private-manifest.json').is_file())

    def test_first_parent_failure_or_interrupt_is_not_replaced_by_cleanup_failure(self):
        with mock.patch.object(scenario.FleetHarness, 'run', side_effect=KeyboardInterrupt):
            self.assert_error(self.invoke(close_error=True), 'rf_signal_cli_interrupted', 130, calls=1)
        self.backends.clear(); self.args[-1] = 'unknown'
        self.assert_error(self.invoke(effect=ValueError('PRIVATE runtime'), close_error=True),
                          'rf_signal_cli_unavailable', calls=1)

    def child(self, args, *, script=None, stdout_closed=False, stderr_closed=False):
        env = {**os.environ, 'PYTHONPATH': str(self.base), 'PYTHONIOENCODING': 'cp949', 'PYTHONUTF8': '0'}
        working = self.base / 'working'; working.mkdir(exist_ok=True)
        command = [sys.executable, '-B', '-m', 'labflow.virtual_fleet.rf_signal_cli', *args]
        if script is not None: command = [sys.executable, '-B', '-c', script, *args]
        process = subprocess.Popen(command, cwd=working, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            if stdout_closed: process.stdout.close(); process.stdout = None
            if stderr_closed: process.stderr.close(); process.stderr = None
            out, err = process.communicate(timeout=20)
            return process.returncode, out or b'', err or b''
        finally:
            if process.poll() is None: process.kill(); process.wait(timeout=5)
            if process.stdout is not None and not process.stdout.closed: process.stdout.close()
            if process.stderr is not None and not process.stderr.closed: process.stderr.close()

    def test_true_module_children_seven_new_runs_under_different_cwd_and_cp949(self):
        ids = set()
        for sid in SCENARIOS:
            args = ['--scenario', sid, '--seed', '7', '--run-name', sid]
            status, out, err = self.child(args)
            self.assertEqual((status, err), (0, b''))
            value = self.check_summary(out.decode('utf-8'), sid=sid)
            self.assertNotIn(value['run_id'], ids); ids.add(value['run_id'])
            folder = self.base / value['output']; before = snapshot(folder)
            moved = folder.with_name(sid + '-renamed'); folder.rename(moved); moved.rename(folder)
            self.assertEqual(snapshot(folder), before)
        self.assertFalse((self.base / 'working/.local').exists())

    def test_true_children_help_error_closed_stdout_and_closed_stderr_do_not_exit120(self):
        status, out, err = self.child(['--help'])
        self.assertEqual((status, err), (0, b'')); self.assertIn('가상', out.decode('utf-8'))
        status, out, err = self.child(['--scenario', 'pulsed_peak'])
        self.assertEqual((status, out, json.loads(err)), (2, b'', {'error': {'code': 'rf_signal_cli_invalid_argument'}}))
        status, out, err = self.child(['--help'], stdout_closed=True)
        self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'rf_signal_cli_output_failed'}}))
        self.assertNotIn(b'Traceback', err)
        status, out, err = self.child(['--bad'], stderr_closed=True)
        self.assertEqual((status, out, err), (2, b'', b''))
        status, out, err = self.child(['--help'], stdout_closed=True, stderr_closed=True)
        self.assertEqual(status, 1)

    def test_true_child_controlled_interrupt_is_130_with_partial_journal_no_retry(self):
        # Test-owned injection at the genuine harness boundary; real entry/041 finally/native cleanup.
        script = ("import runpy,sys;from labflow.virtual_fleet.harness import FleetHarness;"
                  "exec('def interrupted(self):\\n raise KeyboardInterrupt');"
                  "FleetHarness.run=interrupted;sys.argv=['rf_signal_cli']+sys.argv[1:];"
                  "runpy.run_module('labflow.virtual_fleet.rf_signal_cli',run_name='__main__')")
        status, out, err = self.child(ARGS, script=script)
        self.assertEqual((status, out, json.loads(err)), (130, b'', {'error': {'code': 'rf_signal_cli_interrupted'}}))
        folder = self.namespace / 'test045'
        self.assertFalse(journal.read_operator_journal(folder / 'operator/events.jsonl')['complete'])
        self.assertFalse((folder / 'private-manifest.json').exists())

    def test_manifest_request_completion_rows_visibility_and_provenance_bindings_are_required(self):
        original = scenario.run_rf_signal_scenario
        mutations = [
            lambda manifest: manifest.update(complete=False),
            lambda manifest: manifest['request'].update(seed=8),
            lambda manifest: manifest.update(engine_sha256='0' * 64),
            lambda manifest: manifest.update(catalog_sha256='0' * 64),
            lambda manifest: manifest.update(topology_sha256='0' * 64),
            lambda manifest: manifest['files'].__setitem__(1, deepcopy(manifest['files'][0])),
            lambda manifest: manifest['files'][0].update(bytes=True),
            lambda manifest: manifest['files'][2].update(visibility='operator'),
            lambda manifest: manifest.update(extra='PRIVATE'),
        ]
        for index, mutate in enumerate(mutations):
            self.args[-1] = 'manifest' + str(index); captured = {}
            def execute(*args, **kwargs):
                value = original(*args, **kwargs); folder = Path(args[2]); path = folder / 'private-manifest.json'
                manifest = json.loads(path.read_bytes()); mutate(manifest); path.write_bytes(encoded(manifest) + b'\n')
                captured['folder'] = folder; captured['before'] = snapshot(folder)
                return value
            self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_output_failed', calls=1)
            self.assertEqual(snapshot(captured['folder']), captured['before']); self.backends.clear()

    def test_source_change_during_public_projection_is_caught_before_summary(self):
        read = journal.read_operator_journal
        def reading(path):
            value = read(path)
            with (self.base / 'labflow/control_packet_prepare.py').open('ab') as stream: stream.write(b'\n')
            return value
        # Inject only at CLI's second public read; parent's evaluation uses the same public reader.
        original = scenario.run_rf_signal_scenario
        def execute(*args, **kwargs):
            value = original(*args, **kwargs)
            journal.read_operator_journal = reading
            return value
        with mock.patch.object(journal, 'read_operator_journal', new=read):
            self.assert_error(self.invoke(effect=execute), 'rf_signal_cli_input_changed', calls=1)

    def test_native_ancestor_pins_block_rename_during_run_and_all_release_before_return(self):
        original = scenario.run_rf_signal_scenario
        def execute(*args, **kwargs):
            moved = self.namespace.with_name('moved')
            with self.assertRaises(OSError): self.namespace.rename(moved)
            return original(*args, **kwargs)
        status, out, err, run, factory = self.invoke(effect=execute)
        self.assertEqual((status, err), (0, ''))
        moved = self.namespace.with_name('moved'); self.namespace.rename(moved); moved.rename(self.namespace)
        moved_base = self.base.with_name(self.base.name + '-moved'); self.base.rename(moved_base); moved_base.rename(self.base)
        run.assert_called_once(); factory.assert_called_once()

    def test_regular_files_in_fixed_parent_positions_and_run_position_are_rejected(self):
        for relative in ('.local', '.local/rf-signal-runs', '.local/rf-signal-runs/test045'):
            path = self.base / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'preserve')
            self.assert_error(self.invoke(), 'rf_signal_cli_output_invalid', 2)
            self.assertEqual(path.read_bytes(), b'preserve'); path.unlink(); self.backends.clear()

    def test_UNC_device_drive_relative_and_raw_alias_root_are_rejected_before_native(self):
        for value in (r'\\server\share\labflow\virtual_fleet\rf_signal_cli.py',
                      r'\\?\C:\x\labflow\virtual_fleet\rf_signal_cli.py',
                      r'C:labflow\virtual_fleet\rf_signal_cli.py',
                      str(self.base) + r'\\labflow\virtual_fleet\rf_signal_cli.py',
                      str(self.base) + ' \\labflow\\virtual_fleet\\rf_signal_cli.py'):
            self.module_path = value
            with mock.patch.object(catalog, 'load_catalog', side_effect=AssertionError('catalog IO')):
                self.assert_error(self.invoke(), 'rf_signal_cli_output_invalid', 2)
            self.assertEqual(self.backends, [])

    def test_controlled_drive_type_remote_is_rejected_without_network_lookup(self):
        directory = native._WindowsIO.directory
        def local_only(backend, path, **kwargs):
            if path == Path(path.anchor):
                with mock.patch.object(backend.kernel, 'GetDriveTypeW', return_value=4):
                    return directory(backend, path, **kwargs)
            return directory(backend, path, **kwargs)
        with mock.patch.object(native._WindowsIO, 'directory', new=local_only):
            self.assert_error(self.invoke(), 'rf_signal_cli_output_invalid', 2)
        self.assertFalse((self.base / '.local').exists())

    def test_process_final_flush_failure_is_one_and_preserves_prior_syntax_status(self):
        class Stream(StringIO):
            def __init__(self, fail_at=None):
                super().__init__(); self.flushes = 0; self.fail_at = fail_at; self.configurations = []
            def reconfigure(self, **kwargs): self.configurations.append(kwargs)
            def flush(self):
                self.flushes += 1
                if self.flushes == self.fail_at: raise OSError('PRIVATE final flush')
            def fileno(self): return 7
        for args, expected, flush_at in ((['--help'], 1, 2), (['--bad'], 2, 1)):
            out, err = Stream(flush_at), Stream()
            with mock.patch.object(sys, 'argv', ['rf_signal_cli', *args]), \
                    mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err), \
                    mock.patch.object(os, 'open', return_value=900), mock.patch.object(os, 'dup2') as dup, \
                    mock.patch.object(os, 'close') as closed, mock.patch.object(os, '_exit') as exited:
                status = cli._process_main()
            self.assertEqual(status, expected); self.assertFalse(out.closed); self.assertFalse(err.closed)
            self.assertEqual(out.configurations, [dict(encoding='utf-8', errors='strict', newline='\n')])
            self.assertEqual(err.configurations, out.configurations)
            code = 'rf_signal_cli_output_failed' if expected == 1 else 'rf_signal_cli_invalid_argument'
            self.assertEqual(json.loads(err.getvalue()), {'error': {'code': code}})
            dup.assert_called_once_with(900, 7); closed.assert_called_once_with(900); exited.assert_not_called()

    def test_true_child_instrumentation_observes_one_public_run_factory_evaluation_and_native_close(self):
        script = (
            "import json,os,pathlib,runpy,sys\n"
            "counts={'run':0,'factory':0,'evaluation':0,'native_close':0,'native_released':False,'child_process':0}\n"
            "def profile(frame,event,arg):\n"
            " p=frame.f_code.co_filename.replace('\\\\','/');n=frame.f_code.co_name\n"
            " if event=='call':\n"
            "  for key,end,name in [('run','/virtual_fleet/rf_signal_scenario.py','run_rf_signal_scenario'),"
            "('factory','/virtual_fleet/integration.py','create_conducted_example'),"
            "('evaluation','/virtual_fleet/rf_signal_scenario.py','evaluate_rf_signal_scenario'),"
            "('child_process','/subprocess.py','__init__')]:\n"
            "   if p.endswith(end) and n==name:counts[key]+=1\n"
            " if event=='return' and p.endswith('/control_packet_prepare.py') and n=='close':\n"
            "  counts['native_close']+=1;v=frame.f_locals['self'];counts['native_released']=not v.held and not v.directories\n"
            "sys.setprofile(profile);sys.argv=['rf_signal_cli']+sys.argv[1:]\n"
            "try:runpy.run_module('labflow.virtual_fleet.rf_signal_cli',run_name='__main__')\n"
            "finally:\n"
            " sys.setprofile(None);pathlib.Path(os.environ['PYTHONPATH'],'child-metrics.json').write_text(json.dumps(counts),encoding='utf-8')\n")
        status, out, err = self.child(ARGS, script=script)
        self.assertEqual((status, err), (0, b'')); self.check_summary(out.decode('utf-8'), sid='pulsed_peak')
        self.assertEqual(json.loads((self.base / 'child-metrics.json').read_bytes()),
                         dict(run=1, factory=1, evaluation=1, native_close=1, native_released=True, child_process=0))


if __name__ == '__main__':
    unittest.main()
