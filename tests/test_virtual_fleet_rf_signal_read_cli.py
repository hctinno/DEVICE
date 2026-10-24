"""051 thin CLI: controlled API/I/O doubles are separate from genuine children."""
from contextlib import ExitStack
from copy import deepcopy
from io import StringIO
import importlib
import importlib.util
import builtins
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from labflow import control_packet_prepare as native
from labflow.virtual_fleet import rf_signal_read as api
from tests import test_virtual_fleet_rf_signal_read as saved
from tests.test_virtual_fleet_rf_signal_read import FLAGS

cli = (importlib.import_module('labflow.virtual_fleet.rf_signal_read_cli')
       if importlib.util.find_spec('labflow.virtual_fleet.rf_signal_read_cli') else None)
KEYS = set('schema_version kind selection metadata storage historical_assessment measurement '
           'measurement_goal_succeeded outcome failure verification execution_authorized '
           'rerun_authorized error_code'.split())
ARGS = ['--run-name', 'query051']
DEFAULT = object()
ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def dto(status='complete_verified'):
    complete = status == 'complete_verified'
    return dict(schema_version=1, kind='virtual_rf_signal_run_read', selection=dict(run_name='query051'),
                metadata=dict(request=dict(schema_version=1, scenario_id='pulsed_time_mean', seed=7) if complete else None,
                              run_id='query051:run', runtime_instance_id='query051:instance',
                              execution_status='executed' if complete else 'unconfirmed'),
                storage=dict(status=status, manifest_sha256='a' * 64 if complete else None,
                             verified_file_count=3 if complete else 0,
                             journal_status='complete' if complete else 'partial' if status == 'incomplete' else 'invalid',
                             binding_verified=complete),
                historical_assessment=dict(status='completed', verdict='pass', evaluator_id='rf_signal_scenario_v1',
                                           evidence_refs=['event:1'], summary_code='observed_signal_satisfied') if complete else None,
                measurement=dict(value=-24.020599913279625, unit='dBm', quantity='time_average',
                                 reference_plane='sensor_input') if complete else None,
                measurement_goal_succeeded=complete,
                outcome='measurement_observed' if complete else 'incomplete' if status == 'incomplete' else 'invalid',
                failure=None, verification=dict(saved=deepcopy(FLAGS) if complete else None,
                current_scope='stored_hashes_and_public_journal' if complete else 'partial_metadata_only',
                source_pins_verified=True, fresh_offline_evaluation_performed=False, producer_cli_exit_status=None),
                execution_authorized=False, rerun_authorized=False,
                error_code='rf_signal_read_evidence_invalid' if status == 'invalid' else None)


class ProbeStream(StringIO):
    def __init__(self, *, write_error=None, short=False, flush_at=None, descriptor=7, before_write=None):
        super().__init__()
        self.write_error, self.short, self.flush_at = write_error, short, flush_at
        self.descriptor, self.before_write = descriptor, before_write
        self.flushes, self.configurations = 0, []

    def write(self, value):
        if self.before_write: self.before_write()
        if self.write_error: raise self.write_error
        if self.short:
            super().write(value[:5])
            return 5
        return super().write(value)

    def flush(self):
        self.flushes += 1
        if self.flush_at == self.flushes: raise OSError('PRIVATE flush')

    def reconfigure(self, **kwargs):
        self.configurations.append(kwargs)

    def fileno(self):
        return self.descriptor


class RfSignalReadCliTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cli, '051 public main module is absent')

    def invoke(self, args=ARGS, *, result=DEFAULT, effect=None, output=None, error_output=None):
        out, err = output if output is not None else StringIO(), error_output if error_output is not None else StringIO()
        with mock.patch.object(api, 'read_rf_signal_run', return_value=dto() if result is DEFAULT else result,
                               side_effect=effect) as read, \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err):
            value = cli.main(args)
            self.assertIs(sys.stdout, out); self.assertIs(sys.stderr, err)
        self.assertFalse(out.closed); self.assertFalse(err.closed)
        return value, out.getvalue(), err.getvalue(), read

    def assert_error(self, actual, code, status, calls):
        result, out, err, read = actual
        self.assertEqual((result, out, json.loads(err)), (status, '', {'error': {'code': code}}))
        self.assertEqual(read.call_count, calls)
        self.assertNotIn('PRIVATE', err)

    def test_public_main_is_callable(self):
        self.assertTrue(callable(cli.main))

    def test_static_help_and_strict_syntax_never_call_API_or_data_IO(self):
        invalid = [[], ['--run-name'], ARGS + ARGS, ['--run', 'x'], ['--run-name=x'], ['@file'],
                   ARGS + ['x'], ['--json'], ['--latest'], ['--help', '--run-name', 'x'], ['--help', '--help']]
        for args in [['--help'], *invalid]:
            with ExitStack() as stack:
                calls = [stack.enter_context(mock.patch.object(obj, method, side_effect=AssertionError('extra IO')))
                         for obj, method in [(Path, 'open'), (Path, 'read_bytes'), (native, '_WindowsIO'), (os, 'open')]]
                value, out, err, read = self.invoke(args)
            read.assert_not_called()
            for call in calls: call.assert_not_called()
            if args == ['--help']:
                self.assertEqual((value, err), (0, '')); self.assertIn('--run-name', out); self.assertIn('조회', out)
                self.assertGreaterEqual(len(out.splitlines()), 6); self.assertTrue(out.endswith('\n'))
                self.assertNotIn('\\n', out)
            else:
                self.assertEqual((value, out, json.loads(err)), (2, '', {'error': {'code': 'rf_signal_read_cli_invalid_argument'}}))

    def test_nonplain_argv_or_string_subclasses_are_rejected_without_callbacks(self):
        class Hostile(str):
            def __str__(self): raise AssertionError('callback')
        for args in [None, False, ' '.join(ARGS), {'--run-name': 'x'}, [Hostile('--help')],
                     [Hostile('--run-name'), 'x'], ['--run-name', Hostile('x')], ['--run-name', None]]:
            if args is None:
                with mock.patch.object(sys, 'argv', ['read-cli', '--bad']):
                    self.assert_error(self.invoke(args), 'rf_signal_read_cli_invalid_argument', 2, 0)
            else: self.assert_error(self.invoke(args), 'rf_signal_read_cli_invalid_argument', 2, 0)

    def test_original_DTO14_is_emitted_once_for_storage0_3_4_without_extra_IO(self):
        for state, expected in [('complete_verified', 0), ('incomplete', 3), ('invalid', 4)]:
            value = dto(state); before = deepcopy(value)
            with ExitStack() as stack:
                calls = [stack.enter_context(mock.patch.object(obj, method, side_effect=AssertionError('extra IO')))
                         for obj, method in [(Path, 'open'), (Path, 'read_bytes'), (native, '_WindowsIO'), (os, 'open')]]
                status, out, err, read = self.invoke(result=value)
            self.assertEqual((status, err), (expected, '')); self.assertEqual(out.encode(), encoded(value) + b'\n')
            self.assertEqual(json.loads(out), value); self.assertEqual(set(json.loads(out)), KEYS)
            self.assertEqual(value, before); read.assert_called_once_with('query051')
            for call in calls: call.assert_not_called()

    def test_past_fail_blocked_and_failure_recorded_complete_do_not_change_query_exit0(self):
        values = []
        failed = dto(); failed['historical_assessment']['verdict'] = 'fail'; failed['measurement_goal_succeeded'] = False
        failed['historical_assessment']['summary_code'] = 'scenario_expectation_mismatch'; failed['outcome'] = 'assessment_failed'
        values.append(failed)
        blocked = dto(); blocked.update(measurement=None, measurement_goal_succeeded=False, outcome='expected_blocked')
        values.append(blocked)
        marked = dto(); marked.update(historical_assessment=None, measurement=None, measurement_goal_succeeded=False,
                                     outcome='failure_recorded', failure=dict(scenario_id='pulsed_peak',
                                     error_code='rf_signal_scenario_evidence_unavailable', phase='artifact_write', dispatched=True))
        marked['metadata']['execution_status'] = 'failed_recorded'; marked['verification']['saved'] = None; values.append(marked)
        for value in values:
            status, out, err, read = self.invoke(result=value)
            self.assertEqual((status, err, json.loads(out)), (0, '', value)); read.assert_called_once()

    def test_parent_fixed6_exceptions_preserved_and_classified_selection2_operating1(self):
        for suffix in ('invalid_argument', 'path_invalid', 'not_found', 'input_changed', 'evidence_invalid', 'unavailable'):
            code = 'rf_signal_read_' + suffix
            self.assert_error(self.invoke(effect=api.RfSignalReadError(code)), code,
                              2 if suffix in ('invalid_argument', 'path_invalid', 'not_found') else 1, 1)

    def test_valid_syntax_delegates_even_domain_invalid_values_without_normalization(self):
        for name in ('', ' x', 'x ', 'CON', 'x/y', '한글', 'x' * 65):
            actual = self.invoke(('--run-name', name), effect=api.RfSignalReadError('rf_signal_read_invalid_argument'))
            self.assert_error(actual, 'rf_signal_read_invalid_argument', 2, 1)
            actual[3].assert_called_once_with(name)
        with mock.patch.object(sys, 'argv', ['module', *ARGS]):
            actual = self.invoke(None)
        self.assertEqual(actual[0], 0); actual[3].assert_called_once_with('query051')

    def test_unknown_parent_exception_type_or_code_is_unavailable_without_raw_context(self):
        class OtherError(api.RfSignalReadError): pass
        unknown = api.RfSignalReadError('rf_signal_read_not_found'); unknown.code = 'PRIVATE arbitrary code'
        for error in (OtherError('rf_signal_read_not_found'), unknown, ValueError('PRIVATE /secret/path')):
            self.assert_error(self.invoke(effect=error), 'rf_signal_read_cli_unavailable', 1, 1)

    def test_unknown_response_shape_version_and_storage_status_fail_before_stdout(self):
        values = [None, [], {}, dict(dto(), extra='PRIVATE'), dict(dto(), schema_version=True),
                  dict(dto(), schema_version=2), dict(dto(), kind='unknown')]
        missing = dto(); del missing['failure']; values.append(missing)
        for storage in (None, [], {}, dict(dto()['storage'], extra=1), dict(dto()['storage'], status='unknown'),
                        dict(dto()['storage'], status=False)):
            values.append(dict(dto(), storage=storage))
        for value in values:
            self.assert_error(self.invoke(result=value), 'rf_signal_read_cli_unavailable', 1, 1)

    def test_parent_import_failure_and_missing_callable_are_unavailable_with_no_fallback(self):
        original = builtins.__import__
        def importing(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 1 and fromlist and 'rf_signal_read' in fromlist:
                raise ImportError('PRIVATE unavailable source')
            return original(name, globals, locals, fromlist, level)
        with mock.patch.object(builtins, '__import__', side_effect=importing):
            self.assert_error(self.invoke(), 'rf_signal_read_cli_unavailable', 1, 0)
        out, err = StringIO(), StringIO()
        with mock.patch.object(api, 'read_rf_signal_run', None), mock.patch.object(sys, 'stdout', out), \
                mock.patch.object(sys, 'stderr', err):
            status = cli.main(ARGS)
        self.assertEqual((status, out.getvalue(), json.loads(err.getvalue())),
                         (1, '', {'error': {'code': 'rf_signal_read_cli_unavailable'}}))

    def test_exact_UTF8_body8192_plus_LF1_is_preserved_and_body8193_is_not_clipped(self):
        value = dto()
        value['metadata']['run_id'] += '보존'
        value['historical_assessment']['evidence_refs'] = ['event:2', 'event:1', None]
        padding = 8192 - len(encoded(value))
        value['metadata']['run_id'] += '가' * (padding // 3) + 'x' * (padding % 3)
        self.assertEqual(len(encoded(value)), 8192)
        status, out, err, read = self.invoke(result=value)
        self.assertEqual((status, err, len(out.encode('utf-8'))), (0, '', 8193))
        self.assertEqual(out.encode('utf-8'), encoded(value) + b'\n')
        self.assertEqual(json.loads(out), value); read.assert_called_once()
        value['metadata']['run_id'] += 'x'
        self.assert_error(self.invoke(result=value), 'rf_signal_read_cli_output_failed', 1, 1)
        self.assertEqual(len(encoded(value)), 8193)

    def test_unserializable_nonfinite_and_surrogate_values_are_output_failures_without_retry(self):
        for bad in (float('nan'), float('inf'), object(), '\ud800'):
            value = dto(); value['measurement']['value'] = bad
            self.assert_error(self.invoke(result=value), 'rf_signal_read_cli_output_failed', 1, 1)

    def test_write_exception_short_write_flush_and_closed_stderr_do_not_retry_or_close_callers(self):
        for out in (ProbeStream(write_error=OSError('PRIVATE output')), ProbeStream(short=True),
                    ProbeStream(flush_at=1)):
            status, text, err, read = self.invoke(output=out)
            self.assertEqual((status, json.loads(err)), (1, {'error': {'code': 'rf_signal_read_cli_output_failed'}}))
            self.assertLessEqual(len(text.splitlines()), 1); read.assert_called_once()
            self.assertEqual(out.configurations, [])
        err = ProbeStream(write_error=BrokenPipeError('PRIVATE stderr'))
        for effect, expected in ((api.RfSignalReadError('rf_signal_read_not_found'), 2),
                                 (KeyboardInterrupt(), 130), (ValueError('PRIVATE'), 1)):
            status, out, text, read = self.invoke(effect=effect, error_output=err)
            self.assertEqual((status, out, text), (expected, '', '')); read.assert_called_once()
        out, err = ProbeStream(), ProbeStream()
        self.assertEqual(self.invoke(output=out, error_output=err)[0], 0)
        self.assertEqual((out.configurations, err.configurations), ([], []))

    def test_keyboard_interrupt_after_parent_finally_is130_before_any_DTO(self):
        released = []
        def interrupted(name):
            try: raise KeyboardInterrupt()
            finally: released.append(name)
        out = ProbeStream(before_write=lambda: self.fail('no DTO after interrupt'))
        err = ProbeStream(before_write=lambda: self.assertEqual(released, ['query051']))
        self.assert_error(self.invoke(effect=interrupted, output=out, error_output=err),
                          'rf_signal_read_cli_interrupted', 130, 1)

    def test_process_final_flush_changes_observation0_3_4_and_preserves_prior1_2_130(self):
        for prior in (0, 3, 4, 1, 2, 130):
            for failing in ('stdout', 'stderr'):
                out = ProbeStream(flush_at=1 if failing == 'stdout' else None)
                err = ProbeStream(flush_at=1 if failing == 'stderr' else None, descriptor=8)
                with mock.patch.object(cli, 'main', return_value=prior) as main, \
                        mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err), \
                        mock.patch.object(os, 'open', return_value=900) as opened, \
                        mock.patch.object(os, 'dup2') as dup, mock.patch.object(os, 'close') as closed, \
                        mock.patch.object(os, '_exit') as exited:
                    status = cli._process_main()
                self.assertEqual(status, 1 if prior in (0, 3, 4) else prior); main.assert_called_once_with()
                opened.assert_called_once_with(os.devnull, os.O_WRONLY)
                dup.assert_called_once_with(900, 7 if failing == 'stdout' else 8)
                closed.assert_called_once_with(900); exited.assert_not_called()
                expected = {'error': {'code': 'rf_signal_read_cli_output_failed'}}
                self.assertEqual(err.getvalue(), (encoded(expected) + b'\n').decode() if prior in (0, 3, 4) else '')
                self.assertEqual(out.configurations, [dict(encoding='utf-8', errors='strict', newline='\n')])
                self.assertEqual(err.configurations, out.configurations)
                self.assertFalse(out.closed); self.assertFalse(err.closed)

    def test_process_sink_same_fd_and_failed_sink_do_not_leak_or_restore_success(self):
        for sink in (7, None):
            out, err = ProbeStream(flush_at=1), ProbeStream()
            with mock.patch.object(cli, 'main', return_value=3), mock.patch.object(sys, 'stdout', out), \
                    mock.patch.object(sys, 'stderr', err), \
                    mock.patch.object(os, 'open', return_value=sink, side_effect=OSError('PRIVATE') if sink is None else None), \
                    mock.patch.object(os, 'dup2') as dup, mock.patch.object(os, 'close') as closed, \
                    mock.patch.object(os, '_exit') as exited:
                self.assertEqual(cli._process_main(), 1)
            dup.assert_not_called(); closed.assert_not_called()
            if sink is None: exited.assert_called_once_with(1)
            else: exited.assert_not_called()

    def test_process_configuration_failure_reports_output1_without_API(self):
        out, err = ProbeStream(), ProbeStream()
        with mock.patch.object(out, 'reconfigure', side_effect=OSError('PRIVATE configure')), \
                mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', err), \
                mock.patch.object(cli, 'main') as main, mock.patch.object(api, 'read_rf_signal_run') as read:
            self.assertEqual(cli._process_main(), 1)
        self.assertEqual(json.loads(err.getvalue()), {'error': {'code': 'rf_signal_read_cli_output_failed'}})
        main.assert_not_called(); read.assert_not_called()


class RfSignalReadCliGenuineTests(unittest.TestCase):
    """Serialized fixtures and actual 048 calls; children never generate new RF runs."""
    def setUp(self):
        self.assertIsNotNone(cli)
        self.fixture = saved.RfSignalReadTests(methodName='runTest')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.base, self.package = self.fixture.base, self.fixture.package
        for relative in ('__init__.py', 'control_packet_audit.py'):
            shutil.copyfile(ROOT / 'labflow' / relative, self.base / 'labflow' / relative)
        for name in ('rf_signal_read.py', 'rf_signal_read_cli.py'):
            shutil.copyfile(ROOT / 'labflow/virtual_fleet' / name, self.package / name)
        self.working = self.base / 'working'; self.working.mkdir()
        self.backends = []

    def make_fixture(self, name='query051', sid='pulsed_peak', **kwargs):
        value = self.fixture
        value.name, value.folder = name, value.namespace / name
        value.fixture(sid, **kwargs)
        return value

    def invoke(self, name, *, journal_effect=None, output_failure=False):
        back_type = native._WindowsIO
        def backend():
            value = back_type(); self.backends.append(value)
            close = value.close; value.close = mock.Mock(side_effect=close)
            return value
        def released():
            self.assertEqual(len(self.backends), 1)
            for value in self.backends:
                value.close.assert_called_once()
                self.assertEqual((value.held, value.directories), ([], {}))
        out = ProbeStream(before_write=released, write_error=OSError('PRIVATE write') if output_failure else None)
        err = ProbeStream(before_write=released)
        before = saved.fingerprint(self.base)
        with ExitStack() as stack:
            # Only test fixture setup writes. Product paths below may only observe it.
            forbidden = [stack.enter_context(mock.patch.object(obj, method, side_effect=AssertionError('execution')))
                         for obj, method in [(saved.rf_signal_scenario, 'run_rf_signal_scenario'),
                                             (saved.rf_signal_scenario, 'evaluate_rf_signal_scenario'),
                                             (saved.FleetHarness, 'run'), (saved.rf_signal_cli, 'main'),
                                             (saved.catalog, 'load_catalog'), (saved.store, 'Store'),
                                             (saved.sqlite3, 'connect'), (saved.socket, 'socket'),
                                             (subprocess, 'Popen')]]
            stack.enter_context(mock.patch.object(api, '__file__', str(self.package / 'rf_signal_read.py')))
            stack.enter_context(mock.patch.object(native, '_WindowsIO', side_effect=backend))
            read = stack.enter_context(mock.patch.object(api, 'read_rf_signal_run', wraps=api.read_rf_signal_run))
            if journal_effect is not None:
                stack.enter_context(mock.patch.object(saved.journal, 'read_operator_journal', side_effect=journal_effect))
            stack.enter_context(mock.patch.object(sys, 'stdout', out)); stack.enter_context(mock.patch.object(sys, 'stderr', err))
            status = cli.main(['--run-name', name])
            for value in forbidden: value.assert_not_called()
        self.assertEqual(saved.fingerprint(self.base), before)
        read.assert_called_once_with(name); released()
        self.assertFalse(out.closed); self.assertFalse(err.closed)
        self.assertEqual((out.configurations, err.configurations), ([], []))
        self.backends.clear()
        return status, out.getvalue(), err.getvalue()

    def child(self, args, *, script=None, stdout_closed=False, stderr_closed=False):
        env = dict(os.environ, PYTHONPATH=str(self.base), PYTHONIOENCODING='cp949', PYTHONUTF8='0',
                   PYTHONDONTWRITEBYTECODE='1')
        command = [sys.executable, '-B', '-m', 'labflow.virtual_fleet.rf_signal_read_cli', *args]
        if script is not None: command = [sys.executable, '-B', '-c', script, *args]
        process = subprocess.Popen(command, cwd=self.working, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            if stdout_closed: process.stdout.close(); process.stdout = None
            if stderr_closed: process.stderr.close(); process.stderr = None
            out, err = process.communicate(timeout=20)
            return process.returncode, out or b'', err or b''
        finally:
            if process.poll() is None: process.kill(); process.wait(timeout=5)
            if process.stdout is not None and not process.stdout.closed: process.stdout.close()
            if process.stderr is not None and not process.stderr.closed: process.stderr.close()

    def test_actual_API_complete_five_measurements_and_two_expected_blocks_preserve_native_lifetime(self):
        for sid, number in zip(saved.SCENARIOS, saved.VALUES):
            self.make_fixture(sid, sid)
            status, out, err = self.invoke(sid)
            value = json.loads(out)
            self.assertEqual((status, err, value['storage']['status']), (0, '', 'complete_verified'))
            self.assertEqual(value['measurement']['value'] if value['measurement'] else None, number)
            self.assertEqual(value['outcome'], 'measurement_observed' if number is not None else 'expected_blocked')
            self.assertEqual(value['measurement_goal_succeeded'], number is not None)
            self.assertIsNone(value['verification']['producer_cli_exit_status'])
            self.assertEqual(out.encode(), encoded(value) + b'\n'); self.assertEqual(set(value), KEYS)
            self.assertFalse(value['execution_authorized']); self.assertFalse(value['rerun_authorized'])

    def test_actual_API_past_fail_and_complete_failure_sidecar_both_query0(self):
        item = self.make_fixture(verdict='fail')
        status, out, err = self.invoke(item.name)
        self.assertEqual((status, err, json.loads(out)['historical_assessment']['verdict']), (0, '', 'fail'))
        self.assertEqual(json.loads(out)['outcome'], 'assessment_failed')
        item.failure()
        status, out, err = self.invoke(item.name); value = json.loads(out)
        self.assertEqual((status, err, value['outcome']), (0, '', 'failure_recorded'))
        self.assertEqual(value['metadata']['execution_status'], 'failed_recorded')
        self.assertIsNone(value['measurement']); self.assertIsNone(value['historical_assessment'])

    def test_actual_API_incomplete_missing_manifest_and_partial_marker_remain_query3(self):
        item = self.make_fixture(); (item.folder / 'private-manifest.json').unlink()
        status, out, err = self.invoke(item.name); value = json.loads(out)
        self.assertEqual((status, err, value['outcome']), (3, '', 'incomplete'))
        self.assertEqual(value['metadata']['execution_status'], 'unconfirmed')
        item.failure()
        status, out, err = self.invoke(item.name); value = json.loads(out)
        self.assertEqual((status, err, value['outcome']), (3, '', 'failure_recorded'))
        self.assertIsNone(value['verification']['producer_cli_exit_status'])

    def test_actual_API_prefix_only_has_no_KI_or_liveness_inference(self):
        item = self.make_fixture(prefix=True)
        status, out, err = self.invoke(item.name); value = json.loads(out)
        self.assertEqual((status, err, value['storage']['status']), (3, '', 'incomplete'))
        self.assertIsNone(value['failure']); self.assertIsNone(value['measurement'])
        self.assertEqual(value['metadata']['execution_status'], 'unconfirmed')
        self.assertIsNone(value['verification']['producer_cli_exit_status'])

    def test_actual_API_invalid_bytes_return_original_invalid_DTO4(self):
        item = self.make_fixture()
        with (item.folder / 'public-result.json').open('ab') as stream: stream.write(b' ')
        status, out, err = self.invoke(item.name); value = json.loads(out)
        self.assertEqual((status, err, value['storage']['status']), (4, '', 'invalid'))
        self.assertEqual(value['error_code'], 'rf_signal_read_evidence_invalid')
        self.assertIsNone(value['measurement']); self.assertIsNone(value['historical_assessment'])

    def test_actual_parent_domain_errors_have_API1_but_native0(self):
        for name in ('', ' x', 'CON', 'x/y', '한글'):
            out, err = StringIO(), StringIO()
            with mock.patch.object(api, 'read_rf_signal_run', wraps=api.read_rf_signal_run) as read, \
                    mock.patch.object(native, '_WindowsIO') as backend, mock.patch.object(sys, 'stdout', out), \
                    mock.patch.object(sys, 'stderr', err):
                status = cli.main(['--run-name', name])
            self.assertEqual((status, out.getvalue(), json.loads(err.getvalue())),
                             (2, '', {'error': {'code': 'rf_signal_read_invalid_argument'}}))
            read.assert_called_once_with(name); backend.assert_not_called()

    def test_actual_parent_native_finally_precedes_output_failure_and_KI_error(self):
        item = self.make_fixture()
        status, out, err = self.invoke(item.name, output_failure=True)
        self.assertEqual((status, out, json.loads(err)), (1, '', {'error': {'code': 'rf_signal_read_cli_output_failed'}}))
        status, out, err = self.invoke(item.name, journal_effect=KeyboardInterrupt())
        self.assertEqual((status, out, json.loads(err)), (130, '', {'error': {'code': 'rf_signal_read_cli_interrupted'}}))

    def test_true_module_children_seven_saved_fixtures_arbitrary_cwd_cp949_and_UTF8_help(self):
        for sid, number in zip(saved.SCENARIOS, saved.VALUES):
            self.make_fixture(sid, sid)
            before = saved.fingerprint(self.base)
            status, out, err = self.child(['--run-name', sid]); value = json.loads(out)
            self.assertEqual((status, err), (0, b'')); self.assertEqual(set(value), KEYS)
            self.assertEqual(value['measurement']['value'] if value['measurement'] else None, number)
            self.assertEqual(out, encoded(value) + b'\n'); self.assertNotIn(b'\r', out)
            self.assertEqual(saved.fingerprint(self.base), before)
        status, out, err = self.child(['--help'])
        self.assertEqual((status, err), (0, b'')); self.assertIn('조회', out.decode('utf-8'))
        self.assertGreaterEqual(len(out.splitlines()), 6); self.assertNotIn(b'\r', out)
        self.assertEqual(list(self.working.iterdir()), [])

    def test_true_module_child_query3_query4_and_missing_selection2(self):
        item = self.make_fixture('partial051', prefix=True)
        status, out, err = self.child(['--run-name', item.name])
        self.assertEqual((status, err, json.loads(out)['storage']['status']), (3, b'', 'incomplete'))
        item = self.make_fixture('invalid051'); (item.folder / 'public-result.json').write_bytes(b'bad')
        status, out, err = self.child(['--run-name', item.name])
        self.assertEqual((status, err, json.loads(out)['storage']['status']), (4, b'', 'invalid'))
        before = saved.fingerprint(self.base)
        status, out, err = self.child(['--run-name', 'absent051'])
        self.assertEqual((status, out, json.loads(err)), (2, b'', {'error': {'code': 'rf_signal_read_not_found'}}))
        self.assertEqual(saved.fingerprint(self.base), before)

    def test_true_module_closed_pipes_keep_output1_or_syntax2_without_exit120(self):
        for name, state in (('complete051', 'complete'), ('partial051', 'partial'), ('invalid051', 'invalid')):
            item = self.make_fixture(name, prefix=state == 'partial')
            if state == 'invalid': (item.folder / 'public-result.json').write_bytes(b'bad')
            before = saved.fingerprint(self.base)
            for close_err in (False, True):
                status, out, err = self.child(['--run-name', name], stdout_closed=True, stderr_closed=close_err)
                self.assertEqual((status, out), (1, b''))
                if not close_err: self.assertEqual(json.loads(err), {'error': {'code': 'rf_signal_read_cli_output_failed'}})
            self.assertEqual(saved.fingerprint(self.base), before)
        for close_out in (False, True):
            status, out, err = self.child(['--bad'], stdout_closed=close_out, stderr_closed=True)
            self.assertEqual((status, out, err), (2, b'', b''))

    def test_true_module_unavailable_parent_is_fixed1_and_help_has_no_fallback(self):
        (self.package / 'rf_signal_read.py').unlink()
        before = saved.fingerprint(self.base)
        status, out, err = self.child(ARGS)
        self.assertEqual((status, out, json.loads(err)), (1, b'', {'error': {'code': 'rf_signal_read_cli_unavailable'}}))
        self.assertEqual(self.child(['--help'])[0], 0)
        self.assertEqual(saved.fingerprint(self.base), before)

    def test_instrumented_child_counts_API1_journal1_close1_no_run_or_evaluation(self):
        self.make_fixture()
        script = (
            "import json,runpy,sys\n"
            "counts=dict(api=0,journal=0,native_close=0,released=False,run=0,evaluation=0)\n"
            "def profile(frame,event,arg):\n"
            " p=frame.f_code.co_filename.replace(chr(92),'/');n=frame.f_code.co_name\n"
            " if event=='call':\n"
            "  for key,end,name in [('api','/rf_signal_read.py','read_rf_signal_run'),"
            "('journal','/journal.py','read_operator_journal'),"
            "('run','/rf_signal_scenario.py','run_rf_signal_scenario'),"
            "('evaluation','/rf_signal_scenario.py','evaluate_rf_signal_scenario')]:\n"
            "   if p.endswith(end) and n==name:counts[key]+=1\n"
            " if event=='return' and p.endswith('/control_packet_prepare.py') and n=='close':\n"
            "  counts['native_close']+=1;v=frame.f_locals['self'];counts['released']=not v.held and not v.directories\n"
            "sys.setprofile(profile);sys.argv=['rf_signal_read_cli']+sys.argv[1:]\n"
            "try:runpy.run_module('labflow.virtual_fleet.rf_signal_read_cli',run_name='__main__')\n"
            "finally:\n"
            " sys.setprofile(None);sys.stderr.write(json.dumps(counts)+'\\n');sys.stderr.flush()\n")
        before = saved.fingerprint(self.base)
        status, out, err = self.child(ARGS, script=script)
        self.assertEqual((status, set(json.loads(out))), (0, KEYS))
        self.assertEqual(json.loads(err), dict(api=1, journal=1, native_close=1, released=True, run=0, evaluation=0))
        self.assertEqual(saved.fingerprint(self.base), before)


if __name__ == '__main__':
    unittest.main()
