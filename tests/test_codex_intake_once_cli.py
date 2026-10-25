"""Authored synthetic/fake-only host tests; no actual issuer or CLI execution."""
from contextlib import redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source
from labflow.codex_cli_response import CodexCliResponseError, _receipt as d2_receipt, produce_codex_cli_response as _GENUINE_D2
from labflow.intake_jobs import claim_job
from labflow.store import Store, StoreOpenError, canonical
from labflow import codex_intake_once as once_module


MODULE = 'labflow.codex_intake_once_cli'
ARGV = ['--scenario-id', 'intake-synthetic-owner', '--model', 'gpt-6.1-sol']
ERROR_KEYS = {'schema_version', 'kind', 'status', 'phase', 'code',
              'authorization_status', 'model_process_attempts', 'secondary_codes'}
PUBLIC = ('job_id', 'intake_id', 'revision', 'synthetic', 'documents',
          'analysis_context_id', 'analysis_contract', 'instructions')


def C(value):
    return canonical(value).encode('utf-8')


def H(value):
    return hashlib.sha256(value).hexdigest()


def bind_scope(value):
    """Independent fixture C1 projection; never a real reservation issuer."""
    execution = copy.deepcopy(value['execution'])
    execution['context_sha256'] = H(C(execution.pop('approved_context')))
    for key in ('executable', 'evidence_root'):
        execution[key] = str(execution[key])
    scope = dict(authorization_ref=value['authorization_ref'], registered_intake=value['registered_intake'],
                 execution=execution, expires_at=value['expires_at'])
    value['reservation']['scope_sha256'] = H(C(scope))
    return value


def _run_synthetic_host_once(authorization, *, stdout, stderr):
    """TEST ONLY candidate seam: genuine Store/once, concrete D2 must be patched.

    No actual issuer is claimed. This is not imported/called by production main.
    Independent phase2 must bind its own fake D2 and candidate before testing.
    """
    if once_module.produce_codex_cli_response is _GENUINE_D2:
        raise AssertionError('test-only composition requires fake concrete D2')
    module = importlib.import_module(MODULE)
    store = result = first = control = None
    phase, attempts, exit_code, secondary = 'authorization', 0, 5, []
    try:
        binding = module._validate_authorization(authorization,
            authorization['registered_intake']['scenario_id'], authorization['execution']['requested_model'])
        module._check_paths(binding)
        execution = binding['execution']
        phase = 'open'
        store = Store.open_existing(execution['store_root'])
        phase = 'reservation'
        module._consume_reservation(binding)
        module._check_expiry(binding)
        phase, attempts = 'execute', None
        result = once_module.run_codex_intake_once(store, execution['approved_context'],
            worker_id=execution['worker_id'], producer_name=execution['producer_name'],
            executable=execution['executable'], requested_model=execution['requested_model'],
            evidence_root=execution['evidence_root'], authorization_ref=binding['authorization_ref'],
            timeout_seconds=execution['timeout_seconds'])
        attempts = result['attempts']['model_process_attempts']
        exit_code = {'completed': 0, 'idle': 3, 'failed': 4, 'unknown': 5}[result['status']]
    except module._CONTROL as error:
        control = error
        first = module._error(phase, module._PREFIX + 'internal_error', status='unknown', attempts=attempts)
    except module._Failure as error:
        first = module._error(phase, error.code, status=error.status, attempts=attempts)
        exit_code = error.exit_code
    except StoreOpenError as error:
        first = module._error(phase, error.code, attempts=attempts)
    except Exception:
        first = module._error(phase, module._PREFIX + 'internal_error', status='unknown', attempts=attempts)
    finally:
        if store is not None:
            try:
                store.close()
            except module._CONTROL as error:
                if control is None:
                    control = error
                secondary.append(module._PREFIX + 'internal_error')
            except Exception:
                secondary.append(module._PREFIX + 'internal_error')
    if secondary:
        if first is None:
            first = module._error('close', secondary.pop(0), status='unknown', attempts=attempts)
        first['status'] = 'unknown'
        first['secondary_codes'] = secondary[:2]
        exit_code = 5
    # Keep original once result10, even when host cleanup subsequently failed.
    try:
        if result is not None:
            module._write(stdout, module._json_frame(result, 65536))
        if first is not None:
            module._write(stderr, module._json_frame(first, 4096))
    except module._CONTROL as error:
        if control is None:
            control = error
    except Exception:
        exit_code = 5
    if control is not None:
        raise control
    return exit_code


class NoRead:
    def read(self, *args, **kwargs):
        raise AssertionError('stdin must not be read')


class ObservedStream(io.StringIO):
    def __init__(self):
        super().__init__()
        self.writes = self.flushes = self.reconfigures = self.closes = 0
        self.options = []

    def write(self, text):
        self.writes += 1
        return super().write(text)

    def flush(self):
        self.flushes += 1
        return super().flush()

    def reconfigure(self, **kwargs):
        self.reconfigures += 1
        self.options.append(kwargs)

    def close(self):
        self.closes += 1
        return super().close()


class EntrypointTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), 'new host CLI module is absent')
        return importlib.import_module(MODULE)

    def invoke(self, argv, **kwargs):
        module = self.module()
        stdout, stderr = ObservedStream(), ObservedStream()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(sys, 'stdin', NoRead()):
            status = module.main(argv, **kwargs)
        self.assertEqual((stdout.reconfigures, stdout.closes, stderr.reconfigures, stderr.closes), (0, 0, 0, 0))
        return status, stdout, stderr

    def test_noauth_never_opens_store_consumes_reservation_or_probes_auth(self):
        self.module()
        for model in ('gpt-6.1-sol', 'gpt-6-astra'):
            with self.subTest(model=model), \
                    patch('labflow.store.Store.open_existing', side_effect=AssertionError('Store forbidden')), \
                    patch('labflow.codex_intake_once.run_codex_intake_once', side_effect=AssertionError('once forbidden')), \
                    patch('pathlib.Path.open', side_effect=AssertionError('file/marker forbidden')), \
                    patch('subprocess.Popen', side_effect=AssertionError('child/auth forbidden')):
                status, stdout, stderr = self.invoke(['--scenario-id', 'intake-synthetic-owner', '--model', model])
            self.assertEqual(status, 3)
            self.assertEqual(stdout.getvalue(), '')
            record = json.loads(stderr.getvalue())
            self.assertEqual(set(record), ERROR_KEYS)
            self.assertEqual((record['status'], record['phase'], record['code']),
                             ('not_run', 'authorization', 'codex_intake_host_not_authorized'))
            self.assertEqual((record['authorization_status'], record['model_process_attempts']), ('unknown', 0))
            self.assertEqual(record['secondary_codes'], [])
            self.assertEqual((stderr.writes, stderr.flushes), (1, 1))

    def test_public_input_cannot_supply_authority_or_document_paths(self):
        self.module()
        cases = [[], ['--help', 'extra'], ['--scenario-id', 'only'], '--help',
                 ARGV + ['--approval', 'ANY'], ARGV + ['--workspace', 'ANY'],
                 ARGV + ['--context', 'ANY'], ARGV + ['--budget', 'ANY'],
                 ARGV + ['--mock', 'true'], ARGV + ['--model', 'gpt-6-astra'],
                 ['--scenario-id=intake-synthetic-owner', '--model', 'gpt-6.1-sol'],
                 ['--scenario', 'intake-synthetic-owner', '--model', 'gpt-6.1-sol'],
                 ['--scenario-id', '../outside', '--model', 'gpt-6.1-sol'],
                 ['--scenario-id', 'intake-synthetic-owner', '--model', 'OTHER'],
                 ['--scenario-id', True, '--model', 'gpt-6.1-sol']]
        for argv in cases:
            with self.subTest(argv=argv):
                status, stdout, stderr = self.invoke(argv)
                self.assertEqual(status, 2)
                self.assertEqual(stdout.getvalue(), '')
                record = json.loads(stderr.getvalue())
                self.assertEqual(record['code'], 'codex_intake_host_invalid_input')
                self.assertEqual((record['phase'], record['model_process_attempts']), ('arguments', 0))

    def test_help_is_one_unconfigured_frame_without_activity(self):
        status, stdout, stderr = self.invoke(['--help'])
        self.assertEqual(status, 0)
        self.assertIn('--scenario-id', stdout.getvalue())
        self.assertIn('--model', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual((stdout.writes, stdout.flushes), (1, 1))

    def test_short_or_failed_error_output_is_quiet_exit5_once(self):
        module = self.module()
        for behavior in ('short', 'raise', 'flush'):
            stream = ObservedStream()
            if behavior == 'short':
                stream.write = lambda text: (setattr(stream, 'writes', stream.writes + 1) or len(text) - 1)
            elif behavior == 'raise':
                def failed_write(text):
                    stream.writes += 1
                    raise BrokenPipeError('PRIVATE_OUTPUT_CANARY')
                stream.write = failed_write
            else:
                def failed_flush():
                    stream.flushes += 1
                    raise OSError('PRIVATE_FLUSH_CANARY')
                stream.flush = failed_flush
            with self.subTest(behavior=behavior), redirect_stderr(stream), redirect_stdout(io.StringIO()):
                status = module.main(ARGV)
            self.assertEqual(status, 5)
            self.assertEqual(stream.writes, 1)
            self.assertNotIn('PRIVATE_', stream.getvalue())

    def test_control_during_frame_write_propagates_same_object(self):
        module = self.module()
        for cls in (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
            stream = ObservedStream()
            control = cls('PRIVATE_CONTROL_CANARY')

            def failed_write(text):
                stream.writes += 1
                raise control

            stream.write = failed_write
            with self.subTest(control=cls.__name__), redirect_stderr(stream):
                with self.assertRaises(cls) as caught:
                    module.main(ARGV)
            self.assertIs(caught.exception, control)
            self.assertEqual(stream.writes, 1)
            self.assertEqual(control.__dict__, {})

    def test_module_process_noauth_and_argument_results_are_utf8_LF(self):
        root = Path(__file__).resolve().parents[1]
        for argv, expected in ((ARGV, 3), (['--help'], 0), (ARGV + ['--mock', 'true'], 2)):
            with self.subTest(argv=argv):
                result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-m', MODULE, *argv],
                    cwd=root, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, expected)
                self.assertNotIn(b'\r', result.stdout + result.stderr)
                self.assertNotIn(b'Traceback', result.stderr)
                if expected:
                    self.assertEqual(result.stdout, b'')
                    self.assertEqual(json.loads(result.stderr)['model_process_attempts'], 0)

    def test_process_wrapper_maps_controls_and_configures_only_process_streams(self):
        module = self.module()
        self.assertTrue(callable(getattr(module, '_process_main', None)), 'process wrapper is absent')
        for cls, expected in ((KeyboardInterrupt, 130), (SystemExit, 5), (GeneratorExit, 5), (MemoryError, 5)):
            stdout, stderr = ObservedStream(), ObservedStream()
            control = cls('PRIVATE_PROCESS_CONTROL')
            with self.subTest(control=cls.__name__), redirect_stdout(stdout), redirect_stderr(stderr), \
                    patch.object(module, 'main', side_effect=control):
                status = module._process_main()
            self.assertEqual(status, expected)
            self.assertEqual(stdout.getvalue() + stderr.getvalue(), '')
            self.assertEqual(stdout.options, [dict(encoding='utf-8', errors='strict', newline='\n')])
            self.assertEqual(stderr.options, stdout.options)
            self.assertEqual(control.__dict__, {})

    def test_process_final_flush_failure_exits_quietly_without_second_frame(self):
        module = self.module()
        self.assertTrue(callable(getattr(module, '_process_main', None)), 'process wrapper is absent')

        class ImmediateExit(BaseException):
            pass

        stdout, stderr = ObservedStream(), ObservedStream()

        def failed_flush():
            stdout.flushes += 1
            raise OSError('PRIVATE_FINAL_FLUSH')

        stdout.flush = failed_flush
        with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(module, 'main', return_value=3), \
                patch('os._exit', side_effect=ImmediateExit) as terminate:
            with self.assertRaises(ImmediateExit):
                module._process_main()
        terminate.assert_called_once_with(5)
        self.assertEqual((stdout.writes, stderr.writes, stdout.flushes), (0, 0, 1))


class SyntheticHostTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module(MODULE)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        inbox = self.root / 'inbox' / 'bundle'
        inbox.mkdir(parents=True)
        content = b'product_type: authored synthetic device\npurpose: test only\n'
        (inbox / 'request.txt').write_bytes(content)
        store = Store(self.root / 'state')
        try:
            register_source(store, 'HOST-SYNTHETIC-OWNER', inbox.parent, synthetic=True, settle_seconds=1)
            scan_source(store, 'HOST-SYNTHETIC-OWNER', now=100, synthetic_only=True)
            scan_source(store, 'HOST-SYNTHETIC-OWNER', now=101, synthetic_only=True)
            claimed = claim_job(store, 'fixture-prepare', now=102, lease_seconds=1, synthetic_only=True)
        finally:
            store.close()
        self.context = {key: claimed[key] for key in PUBLIC}
        self.executable = self.root / 'codex.exe'
        self.executable.write_bytes(b'fake fixture path; never execute')
        self.evidence, self.consumption = self.root / 'evidence', self.root / 'consumption'
        self.evidence.mkdir()
        self.consumption.mkdir()
        self.authorization = bind_scope(dict(authorization_ref='SYNTHETIC-HOST-ONLY',
            registered_intake=dict(scenario_id='intake-synthetic-owner', registration_sha256=H(b'owner registration'),
                                   input_bundle_sha256=H(content)),
            execution=dict(store_root=str(self.root / 'state'), approved_context=self.context,
                worker_id='host-owner', producer_name='SYN-HOST-OWNER', executable=self.executable,
                requested_model='gpt-6.1-sol', evidence_root=self.evidence, timeout_seconds=60.0),
            expires_at='2099-01-01T00:00:00Z',
            reservation=dict(budget_id='SYNTHETIC-BUDGET', reservation_id='SYNTHETIC-SLOT',
                reservation_record_ref='SYNTHETIC-RECORD', reservation_record_sha256=H(b'not a real reservation'),
                scope_sha256='0' * 64, reserved_model_attempts=1, state='reserved', consumption_root=self.consumption)))
        self.fake_calls = []

    def require(self, name):
        self.assertTrue(callable(getattr(self.module, name, None)), name + ' is absent')
        return getattr(self.module, name)

    def validated(self, value=None):
        return self.require('_validate_authorization')(self.authorization if value is None else value,
                                                       'intake-synthetic-owner', 'gpt-6.1-sol')

    def invoke_composition(self, value=None):
        stdout, stderr = ObservedStream(), ObservedStream()
        with patch.object(once_module, 'produce_codex_cli_response', side_effect=self.fake_d2):
            status = _run_synthetic_host_once(self.authorization if value is None else value, stdout=stdout, stderr=stderr)
        return status, stdout, stderr

    def fake_d2(self, prompt_bytes, schema_bytes, **kwargs):
        self.fake_calls.append((prompt_bytes, schema_bytes, kwargs.copy()))
        prompt = json.loads(prompt_bytes)
        response = C(dict(schema_version=1, producer=prompt['expected_producer'], identity='unknown', facts=[],
            missing_fields=json.loads(schema_bytes)['properties']['missing_fields']['items']['enum']))
        directory = kwargs['evidence_dir']
        directory.mkdir()
        receipt = d2_receipt(kwargs['requested_model'], kwargs['timeout_seconds'],
                             'codex-cli-exchange:' + 'c' * 32, prompt['expected_producer'])
        receipt.update(status='complete', failure=None)
        contents = dict(prompt=prompt_bytes, response_schema=schema_bytes, invocation=b'{}',
            version_stdout=b'codex-cli 0.163.0-alpha.11.2\n', version_stderr=b'',
            stdout_jsonl=b'{"synthetic_fixture":true}\n', stderr=b'', final_text=response, last_message=response)
        for key, payload in contents.items():
            desc = receipt['artifacts'][key]
            (directory / desc['path']).write_bytes(payload)
            desc.update(present=True, bytes=len(payload), sha256=H(payload), complete=True,
                        overflow=False, extent='whole_file')
        receipt['bindings'].update(prompt_sha256=H(prompt_bytes), schema_sha256=H(schema_bytes), invocation_sha256=H(b'{}'))
        receipt['attempts'].update(version_process_attempts=1, model_process_attempts=1)
        receipt['client']['observed_version'] = '0.163.0-alpha.11.2'
        receipt['model']['cli_thread_id'] = 'synthetic-host-thread'
        receipt['lifecycle'].update(model_process_started=True, exit_code=0, thread_started=1,
            turn_started=1, turn_completed=1, agent_messages=1, stdout_eof=True, stderr_eof=True)
        receipt['cleanup'].update(version_child_reaped=True, model_child_reaped=True,
            readers_joined=True, pipes_closed=True, artifacts_closed=True)
        receipt['controls']['observed'].update(argv_submitted=True, argv_exit0=True, empty_cwd_at_spawn=True, tool_items=0)
        receipt['verification']['wire_complete'] = True
        receipt['cost']['kind'] = 'unknown'
        (directory / 'receipt.json').write_bytes(C(receipt))
        return response, copy.deepcopy(receipt)

    def test_native_shape_and_hash_cannot_replace_missing_actual_issuer(self):
        before = copy.deepcopy(self.authorization)
        stdout, stderr = ObservedStream(), ObservedStream()
        with redirect_stdout(stdout), redirect_stderr(stderr), \
                patch('labflow.store.Store.open_existing', side_effect=AssertionError('no Store')), \
                patch('pathlib.Path.open', side_effect=AssertionError('no file')), \
                patch.object(once_module, 'run_codex_intake_once', side_effect=AssertionError('no once')):
            status = self.module.main(ARGV, authorization=self.authorization)
        self.assertEqual(status, 3)
        record = json.loads(stderr.getvalue())
        self.assertEqual((record['code'], record['authorization_status'], record['model_process_attempts']),
                         ('codex_intake_host_not_authorized', 'unknown', 0))
        self.assertEqual(self.authorization, before)
        self.assertEqual(list(self.consumption.iterdir()), [])

    def test_root_binding_requires_registered_scope_and_confirmed_reservation(self):
        validate = self.require('_validate_authorization')
        cases = {
            'extra_top': lambda b: b.update(approved=True),
            'extra_registration': lambda b: b['registered_intake'].update(issuer='root'),
            'extra_execution': lambda b: b['execution'].update(token='PRIVATE_TOKEN'),
            'extra_reservation': lambda b: b['reservation'].update(remaining=99),
            'model_bool': lambda b: b['execution'].update(requested_model=True),
            'attempt_bool': lambda b: b['reservation'].update(reserved_model_attempts=True),
            'attempt2': lambda b: b['reservation'].update(reserved_model_attempts=2),
            'not_reserved': lambda b: b['reservation'].update(state='pending'),
            'bad_sha': lambda b: b['registered_intake'].update(input_bundle_sha256='A' * 64),
            'bad_reference': lambda b: b['reservation'].update(reservation_record_ref='../outside'),
            'bad_timeout': lambda b: b['execution'].update(timeout_seconds=True),
            'string_path': lambda b: b['execution'].update(executable=str(self.executable)),
            'relative_path': lambda b: b['execution'].update(evidence_root=Path('relative')),
            'missing_context_id': lambda b: b['execution']['approved_context'].pop('analysis_context_id'),
            'claim_token': lambda b: b['execution']['approved_context'].update(token='PRIVATE_TOKEN'),
            'not_synthetic': lambda b: b['execution']['approved_context'].update(synthetic=False),
            'schema2': lambda b: b['execution']['approved_context']['analysis_contract'].update(schema_version=2),
            'nonUTC': lambda b: b.update(expires_at='2099-01-01T09:00:00+09:00'),
            'invalid_date': lambda b: b.update(expires_at='2099-02-30T00:00:00Z'),
            'scope_changed': lambda b: b['reservation'].update(scope_sha256='0' * 64),
        }
        for name, mutate in cases.items():
            value = copy.deepcopy(self.authorization)
            mutate(value)
            with self.subTest(case=name), self.assertRaises(ValueError) as caught:
                validate(value, 'intake-synthetic-owner', 'gpt-6.1-sol')
            self.assertEqual(caught.exception.code, 'codex_intake_host_invalid_input')
            self.assertNotIn('PRIVATE_', str(caught.exception))
        for scenario, model in (('different', 'gpt-6.1-sol'), ('intake-synthetic-owner', 'gpt-6-astra')):
            with self.assertRaises(ValueError) as caught:
                validate(self.authorization, scenario, model)
            self.assertEqual(caught.exception.code, 'codex_intake_host_not_authorized')

    def test_validated_snapshot_and_scope_have_no_input_alias(self):
        original = copy.deepcopy(self.authorization)
        binding = self.validated()
        self.assertEqual(binding, original)
        self.authorization['execution']['approved_context']['documents'][0]['text'] = 'PRIVATE_ALIAS_MUTATION'
        self.authorization['reservation']['reservation_id'] = 'CHANGED'
        self.assertEqual(binding, original)

    def test_context_key_subclass_is_rejected_before_custom_comparison(self):
        events = []

        class Key(str):
            __hash__ = str.__hash__

            def __eq__(self, other):
                events.append('comparison')
                raise AssertionError('non-native context key comparison')

        value = copy.deepcopy(self.authorization)
        context = value['execution']['approved_context']
        job = context.pop('job_id')
        context[Key('job_id')] = job
        events.clear()
        with self.assertRaises(ValueError) as caught:
            self.validated(value)
        self.assertEqual(caught.exception.code, 'codex_intake_host_invalid_input')
        self.assertEqual(events, [])

    def test_single_reservation_survives_new_evidence_model_and_process(self):
        consume = self.require('_consume_reservation')
        binding = self.validated()
        path = consume(binding)
        expected = self.consumption / (H(C(['SYNTHETIC-BUDGET', 'SYNTHETIC-SLOT'])) + '.json')
        self.assertEqual(path, expected)
        raw, info = path.read_bytes(), path.stat()
        marker = json.loads(raw)
        self.assertEqual(set(marker), {'schema_version', 'kind', 'authorization_ref', 'budget_id',
                                      'reservation_id', 'scope_sha256', 'evidence_ref'})
        self.assertEqual(marker['evidence_ref'], H(str(self.evidence).encode('utf-8')))
        self.assertEqual(raw, C(marker))
        changed = copy.deepcopy(binding)
        changed['execution'].update(requested_model='gpt-6-astra', evidence_root=self.root / 'new-evidence')
        changed['authorization_ref'] = 'NEW-REF'
        for candidate in (binding, changed):
            with self.assertRaises(ValueError) as caught:
                consume(candidate)
            self.assertEqual(caught.exception.code, 'codex_intake_host_reservation_unavailable')
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_ctime_ns),
                         (raw, info.st_mtime_ns, info.st_ctime_ns))

    def test_atomic_marker_has_one_winner_and_preserves_partial(self):
        consume = self.require('_consume_reservation')
        binding = self.validated()

        def race():
            try:
                consume(binding)
                return 'created'
            except ValueError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: race(), range(2)))
        self.assertCountEqual(outcomes, ['created', 'codex_intake_host_reservation_unavailable'])
        path = next(self.consumption.iterdir())
        path.write_bytes(b'{"partial":')
        before = path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_ctime_ns
        with self.assertRaises(ValueError):
            consume(binding)
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_ctime_ns), before)

    def test_marker_write_failure_is_unknown_and_cannot_refund(self):
        consume = self.require('_consume_reservation')
        binding = self.validated()
        with patch('os.fsync', side_effect=OSError('PRIVATE_FSYNC_FAILURE')):
            with self.assertRaises(ValueError) as caught:
                consume(binding)
        self.assertEqual((caught.exception.code, caught.exception.status, caught.exception.exit_code),
                         ('codex_intake_host_evidence_error', 'unknown', 5))
        path = next(self.consumption.iterdir())
        preserved = path.read_bytes()
        with self.assertRaises(ValueError):
            consume(binding)
        self.assertEqual(path.read_bytes(), preserved)

    def test_real_once_with_fake_D2_preserves_call_counts_and_result10(self):
        self.require('_validate_authorization')
        opened, closed = [], []
        real_open, real_close = Store.open_existing, Store.close

        def open_existing(*args):
            value = real_open(*args)
            opened.append(value)
            return value

        def close(value):
            closed.append(value)
            return real_close(value)

        with patch.object(Store, 'open_existing', side_effect=open_existing) as opener, \
                patch.object(Store, 'close', close), \
                patch.object(once_module, 'run_codex_intake_once', wraps=once_module.run_codex_intake_once) as once:
            status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 0)
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual((opener.call_count, once.call_count, len(closed), len(self.fake_calls)), (1, 1, 1, 1))
        self.assertIs(closed[0], opened[0])
        self.assertEqual(opened[0]._existing_binding.state, 'closed')
        result = json.loads(stdout.getvalue())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result, json.loads((self.evidence / 'caller-receipt.json').read_bytes()))
        self.assertEqual(len(result), 10)
        self.assertEqual((stdout.writes, stdout.flushes), (1, 1))

    def test_mock_receipt_preserves_unknown_cost_and_usage(self):
        status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 0)
        receipt = json.loads((self.evidence / 'exchange' / 'receipt.json').read_bytes())
        self.assertEqual(receipt['cost']['kind'], 'unknown')
        self.assertIsNone(receipt['cost']['amount'])
        self.assertIsNone(receipt['usage'])

    def test_test_only_seam_refuses_genuine_D2(self):
        with self.assertRaises(AssertionError):
            _run_synthetic_host_once(self.authorization, stdout=io.StringIO(), stderr=io.StringIO())

    def test_expired_reservation_is_not_run(self):
        self.require('_validate_authorization')
        value = copy.deepcopy(self.authorization)
        value['expires_at'] = '2000-01-01T00:00:00Z'
        bind_scope(value)
        with patch.object(Store, 'open_existing') as opener:
            status, stdout, stderr = self.invoke_composition(value)
        self.assertEqual(status, 3)
        self.assertEqual(json.loads(stderr.getvalue())['model_process_attempts'], 0)
        opener.assert_not_called()
        self.assertEqual(list(self.consumption.iterdir()), [])

    def test_nonempty_evidence_is_preserved_before_store_open(self):
        self.require('_validate_authorization')
        path = self.evidence / 'preserve.bin'
        path.write_bytes(b'PRESERVE')
        with patch.object(Store, 'open_existing') as opener:
            status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 2)
        opener.assert_not_called()
        self.assertEqual(path.read_bytes(), b'PRESERVE')

    def test_registered_and_working_context_must_not_be_rewritten(self):
        value = copy.deepcopy(self.authorization)
        value['execution']['approved_context']['instructions'] += ' different approved context'
        bind_scope(value)
        status, stdout, stderr = self.invoke_composition(value)
        self.assertEqual(status, 4)
        self.assertEqual(json.loads(stdout.getvalue())['errors'][0]['code'], 'codex_intake_once_scope_mismatch')
        self.assertEqual(self.fake_calls, [])
        self.assertEqual(len(list(self.consumption.iterdir())), 1)

    def test_expiry_after_open_closes_once_without_marker_or_once(self):
        now = [datetime(2026, 10, 25, tzinfo=timezone.utc)]
        original_open, original_close = Store.open_existing, Store.close
        closed = []

        def open_and_expire(*args):
            value = original_open(*args)
            now[0] = datetime(2100, 1, 1, tzinfo=timezone.utc)
            return value

        def close(value):
            closed.append(value)
            return original_close(value)

        with patch.object(self.module, '_utc_now', side_effect=lambda: now[0]), \
                patch.object(Store, 'open_existing', side_effect=open_and_expire), patch.object(Store, 'close', close), \
                patch.object(once_module, 'run_codex_intake_once') as once:
            status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 3)
        self.assertEqual(len(closed), 1)
        once.assert_not_called()
        self.assertEqual(list(self.consumption.iterdir()), [])

    def test_expiry_after_marker_cannot_refund_or_call_once(self):
        now = [datetime(2026, 10, 25, tzinfo=timezone.utc)]
        fsync = os.fsync

        def sync_and_expire(fd):
            fsync(fd)
            now[0] = datetime(2100, 1, 1, tzinfo=timezone.utc)

        with patch.object(self.module, '_utc_now', side_effect=lambda: now[0]), patch('os.fsync', side_effect=sync_and_expire), \
                patch.object(once_module, 'run_codex_intake_once') as once:
            status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 3)
        once.assert_not_called()
        self.assertEqual(len(list(self.consumption.iterdir())), 1)
        self.assertEqual(json.loads(stderr.getvalue())['model_process_attempts'], 0)

    def test_store_failure_retains_fixed_parent_code_and_model0(self):
        with patch.object(Store, 'open_existing', side_effect=StoreOpenError('store_open_schema_mismatch')) as opener:
            status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 5)
        self.assertEqual(opener.call_count, 1)
        result = json.loads(stderr.getvalue())
        self.assertEqual((result['code'], result['model_process_attempts']), ('store_open_schema_mismatch', 0))
        self.assertEqual(list(self.consumption.iterdir()), [])

    def test_first_once_error_survives_close_failure(self):
        real_close = Store.close
        closed = []

        def close_then_raise(value):
            closed.append(value)
            real_close(value)
            raise OSError('PRIVATE_HOST_CLOSE')

        stdout, stderr = ObservedStream(), ObservedStream()
        with patch.object(Store, 'close', close_then_raise), \
                patch.object(once_module, 'produce_codex_cli_response', side_effect=CodexCliResponseError('timeout')):
            status = _run_synthetic_host_once(self.authorization, stdout=stdout, stderr=stderr)
        self.assertEqual(status, 5)
        self.assertEqual(len(closed), 1)
        caller = json.loads(stdout.getvalue())
        self.assertEqual(caller['errors'][0]['code'], 'codex_cli_response_timeout')
        self.assertIsNone(caller['attempts']['model_process_attempts'])
        self.assertEqual(json.loads(stderr.getvalue())['status'], 'unknown')
        self.assertNotIn('PRIVATE_', stdout.getvalue() + stderr.getvalue())

    def test_once_control_preserves_identity_when_close_also_fails(self):
        real_close = Store.close
        control = MemoryError('PRIVATE_FIRST_CONTROL')
        closed = []

        def close_then_raise(value):
            closed.append(value)
            real_close(value)
            raise OSError('PRIVATE_SECONDARY_CLOSE')

        stdout, stderr = ObservedStream(), ObservedStream()
        with patch.object(Store, 'close', close_then_raise), \
                patch.object(once_module, 'produce_codex_cli_response', side_effect=self.fake_d2), \
                patch.object(once_module, 'run_codex_intake_once', side_effect=control):
            with self.assertRaises(MemoryError) as caught:
                _run_synthetic_host_once(self.authorization, stdout=stdout, stderr=stderr)
        self.assertIs(caught.exception, control)
        self.assertEqual(len(closed), 1)
        self.assertIsNone(json.loads(stderr.getvalue())['model_process_attempts'])
        self.assertEqual(control.__dict__, {})
        self.assertNotIn('PRIVATE_', stderr.getvalue())

    def test_marker_body_control_is_preserved_when_close_also_fails(self):
        binding = self.validated()
        real_open = Path.open
        for index, cls in enumerate((KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError)):
            value = copy.deepcopy(binding)
            value['reservation']['reservation_id'] = 'SYN-CONTROL-' + str(index)
            control = cls('PRIVATE_MARKER_CONTROL')
            closes = []

            class Broken:
                def __init__(self, stream):
                    self.stream = stream

                def write(self, payload):
                    self.stream.write(payload[:7])
                    raise control

                def close(self):
                    self.stream.close()
                    closes.append(True)
                    raise OSError('PRIVATE_MARKER_CLOSE')

            def open_marker(path, mode='r', *args, **kwargs):
                stream = real_open(path, mode, *args, **kwargs)
                return Broken(stream) if mode == 'xb' else stream

            with self.subTest(control=cls.__name__), patch.object(Path, 'open', open_marker):
                with self.assertRaises(cls) as caught:
                    self.module._consume_reservation(value)
            self.assertIs(caught.exception, control)
            self.assertEqual(len(closes), 1)
            path = self.consumption / (H(C(['SYNTHETIC-BUDGET', value['reservation']['reservation_id']])) + '.json')
            self.assertEqual(len(path.read_bytes()), 7)

    def test_output_failure_after_complete_does_not_rerun_or_rewrite_DB(self):
        stdout, stderr = ObservedStream(), ObservedStream()

        def fail_write(text):
            stdout.writes += 1
            raise BrokenPipeError('PRIVATE_OUTPUT_AFTER_COMPLETE')

        stdout.write = fail_write
        with patch.object(once_module, 'produce_codex_cli_response', side_effect=self.fake_d2), \
                patch.object(once_module, 'run_codex_intake_once', wraps=once_module.run_codex_intake_once) as once, \
                patch.object(once_module, 'fail_job', wraps=once_module.fail_job) as fail:
            status = _run_synthetic_host_once(self.authorization, stdout=stdout, stderr=stderr)
        self.assertEqual(status, 5)
        self.assertEqual((once.call_count, len(self.fake_calls), stdout.writes), (1, 1, 1))
        fail.assert_not_called()
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(json.loads((self.evidence / 'caller-receipt.json').read_bytes())['status'], 'completed')

    def test_token_lease_document_and_exception_text_never_reach_host_frames(self):
        claim = once_module.claim_job
        secrets = []

        def capture(*args, **kwargs):
            value = claim(*args, **kwargs)
            secrets.extend((value['token'], str(value['lease_until'])))
            value['future_host_secret'] = 'PRIVATE_FUTURE_HOST_SECRET'
            return value

        with patch.object(once_module, 'claim_job', side_effect=capture):
            status, stdout, stderr = self.invoke_composition()
        self.assertEqual(status, 0)
        frames = stdout.getvalue() + stderr.getvalue()
        marker = next(self.consumption.iterdir()).read_bytes().decode('utf-8')
        for secret in (*secrets, 'PRIVATE_FUTURE_HOST_SECRET', 'authored synthetic device'):
            self.assertNotIn(secret, frames + marker)


if __name__ == '__main__':
    unittest.main()
