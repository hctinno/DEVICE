"""Disposable synthetic Stores and fake concrete D2; installed CLI/network0."""
import copy
import hashlib
import json
import io
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.active_intake import intake_status, register_source, scan_source
from labflow.codex_cli_response import CodexCliResponseError, _receipt as d2_receipt
from labflow.codex_intake_once import run_codex_intake_once
from labflow.intake_jobs import claim_job
from labflow.store import Store, canonical


PUBLIC = ('job_id', 'intake_id', 'revision', 'synthetic', 'documents',
          'analysis_context_id', 'analysis_contract', 'instructions')
TOP = {'schema_version', 'kind', 'status', 'phase', 'job', 'binding',
       'attempts', 'strict_decode', 'assessment', 'errors'}
NAME = 'SYN-ONCE-CALLER'


def C(value):
    return canonical(value).encode('utf-8')


def H(value):
    return hashlib.sha256(value).hexdigest()


class OnceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        inbox = self.root / 'inbox' / 'bundle'
        inbox.mkdir(parents=True)
        (inbox / 'request.txt').write_text('product_type: synthetic sample\npurpose: candidate review\n', encoding='utf-8')
        self.store = Store(self.root / 'state')
        self.addCleanup(self.store.close)
        register_source(self.store, 'ONCE-SYNTHETIC', inbox.parent, synthetic=True, settle_seconds=1)
        scan_source(self.store, 'ONCE-SYNTHETIC', now=100, synthetic_only=True)
        scan_source(self.store, 'ONCE-SYNTHETIC', now=101, synthetic_only=True)
        prepared = claim_job(self.store, 'fixture-prepare', now=102, lease_seconds=1, synthetic_only=True)
        self.context = {key: prepared[key] for key in PUBLIC}
        self.executable = self.root / 'codex.exe'
        self.executable.write_bytes(b'fake path only; never executed')
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.kwargs = dict(worker_id='once-worker', producer_name=NAME, executable=self.executable,
                           requested_model='gpt-6.1-sol', evidence_root=self.evidence,
                           authorization_ref='ROOT-SYNTHETIC-ONCE-001')
        self.fake_calls = []
        self.seed = {p.relative_to(self.store.root): p.read_bytes() for p in self.store.root.rglob('*') if p.is_file()}
        self.approved_seed = copy.deepcopy(self.context)
        self.extra = 0

    def fresh_case(self):
        self.store.close()
        self.extra += 1
        base = self.root / ('fresh-' + str(self.extra))
        state = base / 'state'
        state.mkdir(parents=True)
        for relative, payload in self.seed.items():
            path = state / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        self.store = Store.open_existing(str(state))
        self.addCleanup(self.store.close)
        self.context = copy.deepcopy(self.approved_seed)
        self.evidence = base / 'evidence'
        self.evidence.mkdir()
        self.kwargs['evidence_root'] = self.evidence
        self.fake_calls = []

    def fake_d2(self, prompt_bytes, schema_bytes, **kwargs):
        self.fake_calls.append((prompt_bytes, schema_bytes, copy.deepcopy(kwargs)))
        prompt = json.loads(prompt_bytes)
        analysis = dict(schema_version=1, producer=prompt['expected_producer'], identity='unknown',
                        facts=[], missing_fields=list(json.loads(schema_bytes)['properties']['missing_fields']['items']['enum']))
        response = C(analysis)
        directory = kwargs['evidence_dir']
        directory.mkdir()
        receipt = d2_receipt(kwargs['requested_model'], kwargs['timeout_seconds'],
                             'codex-cli-exchange:' + 'a' * 32, prompt['expected_producer'])
        receipt.update(status='complete', failure=None)
        contents = dict(prompt=prompt_bytes, response_schema=schema_bytes, invocation=b'{}',
                        version_stdout=b'codex-cli 0.163.0-alpha.11.2\n', version_stderr=b'',
                        stdout_jsonl=b'{"fake_fixture":true}\n', stderr=b'',
                        final_text=response, last_message=response)
        for key, payload in contents.items():
            desc = receipt['artifacts'][key]
            (directory / desc['path']).write_bytes(payload)
            desc.update(present=True, bytes=len(payload), sha256=H(payload), complete=True,
                        overflow=False, extent='whole_file')
        receipt['bindings'].update(prompt_sha256=H(prompt_bytes), schema_sha256=H(schema_bytes), invocation_sha256=H(b'{}'))
        receipt['attempts'].update(version_process_attempts=1, model_process_attempts=1)
        receipt['client']['observed_version'] = '0.163.0-alpha.11.2'
        receipt['model']['cli_thread_id'] = 'fake-thread'
        receipt['lifecycle'].update(model_process_started=True, exit_code=0, thread_started=1,
                                     turn_started=1, turn_completed=1, agent_messages=1,
                                     stdout_eof=True, stderr_eof=True)
        receipt['cleanup'].update(version_child_reaped=True, model_child_reaped=True,
                                   readers_joined=True, pipes_closed=True, artifacts_closed=True)
        receipt['controls']['observed'].update(argv_submitted=True, argv_exit0=True, empty_cwd_at_spawn=True, tool_items=0)
        receipt['verification']['wire_complete'] = True
        receipt['cost']['kind'] = 'unknown'
        (directory / 'receipt.json').write_bytes(C(receipt))
        return response, copy.deepcopy(receipt)

    def run_once(self, **changes):
        args = {**self.kwargs, **changes}
        return run_codex_intake_once(self.store, self.context, **args)

    def test_success_joins_exact_public_context_and_concrete_receipt_then_completes(self):
        before = copy.deepcopy(self.context)
        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=self.fake_d2) as producer:
            result = self.run_once()
        self.assertEqual(set(result), TOP)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['strict_decode'], 'accepted')
        self.assertEqual(result['job']['attempt'], 2)
        self.assertEqual(result['attempts'], dict(producer_invocations=1, version_process_attempts=1,
                                                 model_process_attempts=1, automatic_retries=0))
        self.assertEqual(result['assessment']['status'], 'not_assessed')
        self.assertEqual(result['errors'], [])
        self.assertEqual(self.context, before)
        self.assertEqual(producer.call_count, 1)
        prompt, schema, kwargs = self.fake_calls[0]
        self.assertEqual(json.loads(json.loads(prompt)['messages'][1]['content']), before)
        self.assertEqual(kwargs['evidence_dir'], self.evidence / 'exchange')
        self.assertEqual(result['binding']['prompt_sha256'], H(prompt))
        self.assertEqual(result['binding']['schema_sha256'], H(schema))
        self.assertEqual(json.loads((self.evidence / 'caller-receipt.json').read_bytes()), result)
        self.assertTrue((self.evidence / 'job-binding.json').is_file())
        self.assertEqual(intake_status(self.store, before['intake_id'])['jobs'][0]['state'], 'completed')

    def test_idle_does_not_invoke_D2_or_reclaim_twice(self):
        with patch('labflow.codex_intake_once.claim_job', return_value=None) as claim, \
                patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
            result = self.run_once()
        self.assertEqual(result['status'], 'idle')
        self.assertIsNone(result['job'])
        self.assertEqual(result['attempts']['model_process_attempts'], 0)
        self.assertEqual(claim.call_count, 1)
        self.assertEqual(claim.call_args.kwargs, dict(synthetic_only=True, lease_seconds=3600))
        producer.assert_not_called()

    def test_inconsistent_schema_contract_is_rejected_before_claim(self):
        self.context['analysis_contract']['schema_version'] = 2
        with patch('labflow.codex_intake_once.claim_job') as claim, \
                patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
            result = self.run_once()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'][0]['code'], 'analysis_context_invalid')
        claim.assert_not_called()
        producer.assert_not_called()

    def test_claim_exception_without_returned_lease_is_unknown_and_never_fail_job(self):
        with patch('labflow.codex_intake_once.claim_job', side_effect=RuntimeError('PRIVATE_CLAIM_CANARY')), \
                patch('labflow.codex_intake_once.fail_job') as fail, \
                patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
            result = self.run_once()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['phase'], 'claim')
        self.assertIsNone(result['job'])
        self.assertTrue((self.evidence / 'attempt-intent.json').is_file())
        self.assertNotIn('PRIVATE_CLAIM_CANARY', C(result).decode('utf-8'))
        fail.assert_not_called()
        producer.assert_not_called()

    def test_claim_can_commit_before_throwing_and_caller_still_does_not_finalize_without_token(self):
        from labflow import codex_intake_once as module
        real = module.claim_job

        def claim_then_raise(*args, **kwargs):
            real(*args, **kwargs)
            raise RuntimeError('PRIVATE_CLAIM_AFTER_COMMIT')

        with patch.object(module, 'claim_job', side_effect=claim_then_raise), \
                patch.object(module, 'fail_job') as fail, patch.object(module, 'produce_codex_cli_response') as producer:
            result = self.run_once()
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['job'])
        self.assertEqual(intake_status(self.store, self.context['intake_id'])['jobs'][0]['state'], 'running')
        fail.assert_not_called()
        producer.assert_not_called()

    def test_scope_mismatch_consumes_claim_attempt_without_model_or_retry(self):
        self.context['instructions'] += ' Explicitly different approved input.'
        with patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
            result = self.run_once()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_scope_mismatch')
        job = intake_status(self.store, self.context['intake_id'])['jobs'][0]
        self.assertEqual((job['state'], job['attempt'], job['error_code']), ('queued', 2, 'model_error'))
        producer.assert_not_called()

    def test_non_synthetic_flag_fixture_is_not_atomically_claimed(self):
        folder = self.root / 'non-synthetic-flag-fixture' / 'bundle'
        folder.mkdir(parents=True)
        (folder / 'request.txt').write_text('authored test fixture with synthetic=False flag only', encoding='utf-8')
        register_source(self.store, 'FLAG-FALSE', folder.parent, synthetic=False, settle_seconds=1)
        scan_source(self.store, 'FLAG-FALSE', now=100)
        scan_source(self.store, 'FLAG-FALSE', now=101)
        other = next(r for r in intake_status(self.store) if r['source_id'] == 'FLAG-FALSE')
        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=self.fake_d2):
            result = self.run_once()
        self.assertEqual(result['status'], 'completed')
        unchanged = intake_status(self.store, other['intake_id'])
        self.assertEqual(unchanged['jobs'], other['jobs'])

    def test_invalid_configuration_and_approved_input_never_claim(self):
        for changes in ({'worker_id': True}, {'worker_id': ''}, {'authorization_ref': ''},
                        {'requested_model': 'unapproved-model'}, {'timeout_seconds': True},
                        {'timeout_seconds': 0}, {'timeout_seconds': 61}, {'timeout_seconds': float('nan')},
                        {'executable': str(self.executable)}, {'executable': Path('relative/codex.exe')},
                        {'evidence_root': self.root / 'absent'}):
            with self.subTest(changes=repr(changes)), \
                    patch('labflow.codex_intake_once.claim_job') as claim, \
                    patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
                result = self.run_once(**changes)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_invalid_input')
                claim.assert_not_called()
                producer.assert_not_called()
        for bad in (None, {'synthetic': False}, {**self.context, 'token': 'PRIVATE_TOKEN'}):
            with self.subTest(context=type(bad).__name__), patch('labflow.codex_intake_once.claim_job') as claim:
                result = run_codex_intake_once(self.store, bad, **self.kwargs)
                self.assertEqual(result['status'], 'failed')
                claim.assert_not_called()
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_nonempty_root_cannot_overwrite_or_reuse_a_call(self):
        preserved = self.evidence / 'keep.bin'
        preserved.write_bytes(b'PRESERVE')
        with patch('labflow.codex_intake_once.claim_job') as claim:
            result = self.run_once()
        self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_invalid_input')
        self.assertEqual(preserved.read_bytes(), b'PRESERVE')
        claim.assert_not_called()

    def test_full_public8_and_malformed_PDF_shape_are_checked_before_claim(self):
        missing_id = copy.deepcopy(self.context)
        missing_id.pop('analysis_context_id')
        pdf = copy.deepcopy(self.context)
        pdf['documents'][0]['format'] = 'pdf'
        for context, code in ((missing_id, 'codex_intake_once_invalid_input'), (pdf, 'analysis_context_invalid')):
            self.fresh_case()
            with self.subTest(code=code), patch('labflow.codex_intake_once.claim_job') as claim, \
                    patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
                result = run_codex_intake_once(self.store, context, **self.kwargs)
                self.assertEqual(result['errors'][0]['code'], code)
                claim.assert_not_called()
                producer.assert_not_called()
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_unverified_claim_references_are_unknown_without_fail_or_private_values(self):
        from labflow import codex_intake_once as module
        real = module.claim_job
        for changes in ({'job_id': 'PRIVATE_MALFORMED\nJOB'}, {'intake_id': 'PRIVATE_MALFORMED\nINTAKE'},
                        {'revision': 0}, {'attempt': 0}, {'attempt': True}, {'token': None}):
            self.fresh_case()

            def invalid_claim(*args, **kwargs):
                value = real(*args, **kwargs)
                value.update(changes)
                return value

            with self.subTest(keys=list(changes)), patch.object(module, 'claim_job', side_effect=invalid_claim), \
                    patch.object(module, 'fail_job') as fail, patch.object(module, 'produce_codex_cli_response') as producer:
                result = self.run_once()
                self.assertEqual(result['status'], 'unknown')
                self.assertIsNone(result['job'])
                self.assertNotIn('PRIVATE_MALFORMED', C(result).decode())
                fail.assert_not_called()
                producer.assert_not_called()

    def test_genuine_boundary_order_and_single_call_counts(self):
        from labflow import codex_intake_once as module
        order = []
        real_claim, real_decode, real_complete = module.claim_job, module.decode_analysis_response, module.complete_job

        def claimed(*args, **kwargs):
            self.assertTrue((self.evidence / 'attempt-intent.json').is_file())
            order.append('claim')
            return real_claim(*args, **kwargs)

        def produced(*args, **kwargs):
            order.append('producer')
            return self.fake_d2(*args, **kwargs)

        def decoded(response, context, **kwargs):
            self.assertIs(type(response), bytes)
            self.assertEqual(response, (self.evidence / 'exchange' / 'final-text.bin').read_bytes())
            self.assertEqual(context, self.approved_seed)
            order.append('decode')
            return real_decode(response, context, **kwargs)

        def completed(*args, **kwargs):
            binding = json.loads((self.evidence / 'job-binding.json').read_bytes())
            self.assertEqual(set(binding['job']), {'job_id', 'intake_id', 'revision', 'attempt'})
            self.assertEqual(binding['binding']['response_sha256'], H((self.evidence / 'exchange' / 'final-text.bin').read_bytes()))
            order.append('complete')
            return real_complete(*args, **kwargs)

        with patch.object(module, 'claim_job', side_effect=claimed) as claim, \
                patch.object(module, 'produce_codex_cli_response', side_effect=produced) as producer, \
                patch.object(module, 'decode_analysis_response', side_effect=decoded) as decoder, \
                patch.object(module, 'complete_job', side_effect=completed) as complete, patch.object(module, 'fail_job') as fail:
            result = self.run_once()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(order, ['claim', 'producer', 'decode', 'complete'])
        self.assertEqual([call.call_count for call in (claim, producer, decoder, complete)], [1, 1, 1, 1])
        self.assertEqual(claim.call_args.kwargs, {'synthetic_only': True, 'lease_seconds': 3600})
        self.assertEqual(complete.call_args.kwargs, {})
        fail.assert_not_called()

    def test_borrowed_existing_store_remains_open_and_result_has_no_aliases(self):
        self.fresh_case()
        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=self.fake_d2):
            result = self.run_once(requested_model='gpt-6-astra')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.store._existing_binding.state, 'open')
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT 1').fetchone()[0], 1)
        saved = json.loads((self.evidence / 'caller-receipt.json').read_bytes())
        result['job']['attempt'] = 99
        result['binding']['producer_declaration']['name'] = 'MUTATED'
        self.assertEqual(json.loads((self.evidence / 'caller-receipt.json').read_bytes()), saved)
        self.assertEqual(self.context, self.approved_seed)

    def test_private_claim_token_lease_and_future_host_keys_never_leave_memory(self):
        from labflow import codex_intake_once as module
        real = module.claim_job
        secrets = []

        def capture_claim(*args, **kwargs):
            value = real(*args, **kwargs)
            secrets.extend((value['token'], str(value['lease_until'])))
            value['future_private_host_field'] = {'token': value['token']}
            return value

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(module, 'claim_job', side_effect=capture_claim), \
                patch.object(module, 'produce_codex_cli_response', side_effect=self.fake_d2), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            result = self.run_once()
        self.assertEqual(result['status'], 'completed')
        payloads = [C(result), stdout.getvalue().encode(), stderr.getvalue().encode()]
        payloads.extend(p.read_bytes() for p in self.evidence.rglob('*') if p.is_file())
        for secret in secrets:
            for payload in payloads:
                self.assertNotIn(secret.encode(), payload)
        self.assertNotIn(b'future_private_host_field', self.fake_calls[0][0])

    def test_caller_snapshot_survives_mutation_of_original_context_during_D2(self):
        original = copy.deepcopy(self.context)

        def mutate_after_wire(*args, **kwargs):
            self.context['documents'][0]['text'] = 'MUTATED_CALLER_ALIAS'
            return self.fake_d2(*args, **kwargs)

        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=mutate_after_wire):
            result = self.run_once()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(json.loads(json.loads(self.fake_calls[0][0])['messages'][1]['content']), original)

    def test_all_D2_fixed_failures_stop_before_decoder_and_preserve_attempts(self):
        for code in ('invalid_input', 'limit_exceeded', 'unsupported_client', 'evidence_error', 'spawn_failed',
                     'timeout', 'stream_invalid', 'process_failed', 'final_mismatch', 'cleanup_failed', 'internal_error'):
            self.fresh_case()
            receipt = d2_receipt(self.kwargs['requested_model'], 60, 'codex-cli-exchange:' + 'b' * 32,
                                 {'kind': 'model', 'name': NAME})
            receipt['attempts'].update(version_process_attempts=1, model_process_attempts=1)
            with self.subTest(code=code), \
                    patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=CodexCliResponseError(code, receipt)) as producer, \
                    patch('labflow.codex_intake_once.decode_analysis_response') as decoder, \
                    patch('labflow.codex_intake_once.complete_job') as complete:
                result = self.run_once()
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['errors'][0]['code'], 'codex_cli_response_' + code)
                self.assertEqual(result['attempts']['model_process_attempts'], 1)
                self.assertEqual(producer.call_count, 1)
                decoder.assert_not_called()
                complete.assert_not_called()

    def test_D2_failure_without_receipt_leaves_attempt_counts_unknown(self):
        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=CodexCliResponseError('timeout')):
            result = self.run_once()
        self.assertEqual(result['attempts'], dict(producer_invocations=1, version_process_attempts=None,
                                                 model_process_attempts=None, automatic_retries=0))

    def test_receipt_and_artifact_tamper_is_rejected_before_decode(self):
        mutations = {
            'failed_status': lambda r: r.update(status='failed'),
            'wire_incomplete': lambda r: r['verification'].update(wire_complete=False),
            'different_model': lambda r: r['model'].update(requested='gpt-6-astra'),
            'different_producer': lambda r: r['bindings']['producer_declaration'].update(name='OTHER'),
            'different_prompt_sha': lambda r: r['bindings'].update(prompt_sha256='0' * 64),
            'different_schema_sha': lambda r: r['bindings'].update(schema_sha256='0' * 64),
            'model_attempt_bool': lambda r: r['attempts'].update(model_process_attempts=True),
            'not_reaped': lambda r: r['cleanup'].update(model_child_reaped=False),
            'not_EOF': lambda r: r['lifecycle'].update(stdout_eof=False),
            'extra_tool': lambda r: r['lifecycle'].update(tool_items=1),
            'identity_promoted': lambda r: r['verification'].update(remote_identity_verified=True),
            'prefix_only': lambda r: r['artifacts']['final_text'].update(extent='prefix', complete=False),
            'escape_path': lambda r: r['artifacts']['final_text'].update(path='../outside.bin'),
            'missing_artifact': lambda r: r['artifacts'].pop('last_message'),
        }
        for case in (*mutations, 'receipt_bytes_changed', 'final_bytes_changed', 'last_bytes_changed', 'final_directory', 'wrong_tuple', 'bytearray'):
            self.fresh_case()

            def corrupt(*args, **kwargs):
                response, receipt = self.fake_d2(*args, **kwargs)
                directory = kwargs['evidence_dir']
                if case in mutations:
                    mutations[case](receipt)
                    (directory / 'receipt.json').write_bytes(C(receipt))
                elif case == 'receipt_bytes_changed':
                    with (directory / 'receipt.json').open('ab') as stream:
                        stream.write(b'\n')
                elif case == 'final_bytes_changed':
                    (directory / 'final-text.bin').write_bytes(b'CHANGED')
                elif case == 'last_bytes_changed':
                    (directory / 'last-message.bin').write_bytes(b'CHANGED')
                elif case == 'final_directory':
                    (directory / 'final-text.bin').unlink()
                    (directory / 'final-text.bin').mkdir()
                elif case == 'wrong_tuple':
                    return [response, receipt]
                elif case == 'bytearray':
                    return bytearray(response), receipt
                return response, receipt

            with self.subTest(case=case), patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=corrupt), \
                    patch('labflow.codex_intake_once.decode_analysis_response') as decoder, \
                    patch('labflow.codex_intake_once.complete_job') as complete:
                result = self.run_once()
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_receipt_binding_mismatch')
                decoder.assert_not_called()
                complete.assert_not_called()

    def test_decoder_rejection_preserves_parent_code_and_never_completes(self):
        from labflow import codex_intake_once as module

        def wrong_schema(*args, **kwargs):
            response, receipt = self.fake_d2(*args, **kwargs)
            response = b'{}'
            for key in ('final_text', 'last_message'):
                receipt['artifacts'][key].update(bytes=2, sha256=H(response))
                (kwargs['evidence_dir'] / receipt['artifacts'][key]['path']).write_bytes(response)
            (kwargs['evidence_dir'] / 'receipt.json').write_bytes(C(receipt))
            return response, receipt

        with patch.object(module, 'produce_codex_cli_response', side_effect=wrong_schema), patch.object(module, 'complete_job') as complete:
            result = self.run_once()
        self.assertEqual(result['strict_decode'], 'rejected')
        self.assertEqual(result['errors'][0]['code'], 'analysis_response_invalid')
        complete.assert_not_called()

    def test_job_binding_write_failure_prevents_completion_and_uses_evidence_code(self):
        from labflow import codex_intake_once as module
        write = module._write_new

        def fail_binding(path, value):
            if path.name == 'job-binding.json':
                raise OSError('PRIVATE_BINDING_WRITE_ERROR')
            return write(path, value)

        with patch.object(module, 'produce_codex_cli_response', side_effect=self.fake_d2), \
                patch.object(module, '_write_new', side_effect=fail_binding), patch.object(module, 'complete_job') as complete:
            result = self.run_once()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_evidence_error')
        complete.assert_not_called()

    def test_error_after_real_completion_is_unknown_and_never_failed_or_regenerated(self):
        from labflow import codex_intake_once as module
        complete = module.complete_job

        def commit_then_raise(*args, **kwargs):
            complete(*args, **kwargs)
            raise RuntimeError('PRIVATE_POST_COMMIT_CANARY')

        with patch.object(module, 'produce_codex_cli_response', side_effect=self.fake_d2) as producer, \
                patch.object(module, 'complete_job', side_effect=commit_then_raise) as completed, patch.object(module, 'fail_job') as fail:
            result = self.run_once()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_completion_unknown')
        self.assertEqual((producer.call_count, completed.call_count), (1, 1))
        fail.assert_not_called()
        self.assertEqual(intake_status(self.store, self.context['intake_id'])['jobs'][0]['state'], 'completed')

    def test_evidence_failure_after_completion_is_unknown_without_DB_retry(self):
        from labflow import codex_intake_once as module
        write = module._write_new

        def fail_final(path, value):
            if path.name == 'caller-receipt.json':
                raise OSError('PRIVATE_FINAL_WRITE_ERROR')
            return write(path, value)

        with patch.object(module, 'produce_codex_cli_response', side_effect=self.fake_d2), \
                patch.object(module, '_write_new', side_effect=fail_final), patch.object(module, 'fail_job') as fail:
            result = self.run_once()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['phase'], 'finalize')
        self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_evidence_error')
        self.assertTrue((self.evidence / 'job-binding.json').exists())
        self.assertEqual(intake_status(self.store, self.context['intake_id'])['jobs'][0]['state'], 'completed')
        fail.assert_not_called()

    def test_secondary_fail_and_evidence_errors_do_not_replace_first_D2_error(self):
        from labflow import codex_intake_once as module
        write = module._write_new

        def fail_final(path, value):
            if path.name == 'caller-receipt.json':
                raise OSError('PRIVATE_FINAL_WRITE_ERROR')
            return write(path, value)

        with patch.object(module, 'produce_codex_cli_response', side_effect=CodexCliResponseError('timeout')), \
                patch.object(module, 'fail_job', side_effect=RuntimeError('PRIVATE_DB_ERROR')), \
                patch.object(module, '_write_new', side_effect=fail_final):
            result = self.run_once()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual([e['code'] for e in result['errors']],
                         ['codex_cli_response_timeout', 'codex_intake_once_job_finalize_failed', 'codex_intake_once_evidence_error'])
        self.assertEqual([e['secondary'] for e in result['errors']], [False, True, True])

    def test_control_objects_propagate_without_additional_DB_finalize(self):
        from labflow import codex_intake_once as module
        for stage in ('claim_job', 'produce_codex_cli_response', 'decode_analysis_response', 'complete_job'):
            for cls in (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
                self.fresh_case()
                control = cls('PRIVATE_CONTROL_CANARY')
                with self.subTest(stage=stage, control=cls.__name__), \
                        patch.object(module, 'produce_codex_cli_response', side_effect=self.fake_d2), \
                        patch.object(module, stage, side_effect=control), patch.object(module, 'fail_job') as fail:
                    with self.assertRaises(cls) as caught:
                        self.run_once()
                    self.assertIs(caught.exception, control)
                    fail.assert_not_called()
                    saved = json.loads((self.evidence / 'caller-receipt.json').read_bytes())
                    self.assertEqual(saved['status'], 'unknown')
                    self.assertNotIn('PRIVATE_CONTROL_CANARY', C(saved).decode())
                    if stage == 'decode_analysis_response':
                        self.assertEqual(saved['strict_decode'], 'not_run')

    def test_control_in_fail_job_preserves_prior_error_in_available_receipt(self):
        control = KeyboardInterrupt('PRIVATE_FAIL_CONTROL')
        with patch('labflow.codex_intake_once.produce_codex_cli_response', side_effect=CodexCliResponseError('timeout')), \
                patch('labflow.codex_intake_once.fail_job', side_effect=control):
            with self.assertRaises(KeyboardInterrupt) as caught:
                self.run_once()
        self.assertIs(caught.exception, control)
        saved = json.loads((self.evidence / 'caller-receipt.json').read_bytes())
        self.assertEqual(saved['errors'][0]['code'], 'codex_cli_response_timeout')
        self.assertEqual(saved['status'], 'unknown')

    def test_artifact_IO_preserves_first_control_when_close_also_fails(self):
        from labflow import codex_intake_once as module
        path = self.root / 'io-fixture.bin'
        path.write_bytes(b'fixture')
        info = path.lstat()
        for operation in ('read', 'write'):
            for cls in (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
                control = cls('PRIVATE_IO_CONTROL')

                class Stream:
                    closes = 0

                    def fileno(self):
                        return -1

                    def read(self, limit):
                        raise control

                    def write(self, payload):
                        raise control

                    def close(self):
                        self.closes += 1
                        raise OSError('PRIVATE_SECONDARY_CLOSE')

                stream = Stream()
                with self.subTest(operation=operation, control=cls.__name__), \
                        patch.object(Path, 'open', return_value=stream), patch.object(module.os, 'fstat', return_value=info):
                    with self.assertRaises(cls) as caught:
                        if operation == 'read':
                            module._read(path, 65536)
                        else:
                            module._write_new(path, {'kind': 'fixture'})
                    self.assertIs(caught.exception, control)
                    self.assertEqual(stream.closes, 1)


SCHEMA_TWO_ONCE_OBSERVATIONS = []


class SchemaTwoOnceTests(unittest.TestCase):
    """Fresh own queued files and real G3/claim/strict/complete; authored D2 only."""

    def setUp(self):
        from labflow import codex_intake_once
        self.once = codex_intake_once
        self.temp = tempfile.TemporaryDirectory(prefix='once-schema2-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = []
        self.record = dict(case=self._testMethodName, actual_CLI=0, actual_models=0,
                           producer='local authored receipt fixture; receipt attempts are declarations')
        self.addCleanup(self.capture)

    def capture(self):
        files = {}
        for path in self.root.rglob('*'):
            if path.is_file() and ('inbox' in path.parts or 'blobs' in path.parts or
                                  any(part.startswith('evidence') for part in path.parts)):
                files[path.relative_to(self.root).as_posix()] = path.read_bytes()
        self.assertLessEqual(len(files), 192)
        self.assertLessEqual(sum(map(len, files.values())), 8 * 1024 * 1024)
        SCHEMA_TWO_ONCE_OBSERVATIONS.append(dict(self.record, files=files))

    def case(self, kind='mixed'):
        from reportlab.pdfgen import canvas
        from labflow.document_extract import ExtractionLimits
        from labflow.intake_jobs import prepare_registered_synthetic_context
        base = self.root / ('case-' + str(len(self.cases)))
        bundle = base / 'inbox' / 'bundle'
        bundle.mkdir(parents=True)
        if kind == 'text':
            (bundle/'request.TXT').write_text('product_type: industrial_sensor\nmodel: SYN-ONCE-PDF\n'
                                             'market: EU\npurpose: development evaluation\n', encoding='utf-8')
        elif kind == 'malformed':
            (bundle/'REQUEST.PDF').write_bytes(b'%PDF-1.7\nauthored malformed PDF fixture\n')
        else:
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, invariant=1)
            for lines in (('product_type: industrial_sensor', 'model: SYN-ONCE-PDF'),
                          ('market: EU', 'purpose: development evaluation')):
                text = pdf.beginText(48, 790)
                for line in lines:
                    text.textLine(line)
                pdf.drawText(text)
                pdf.showPage()
            pdf.save()
            (bundle/'REQUEST.PDF').write_bytes(buffer.getvalue())
            if kind == 'mixed':
                (bundle/'attachment.TXT').write_text('purpose: development evaluation\n', encoding='utf-8')
        initial = Store(base/'state')
        register_source(initial, 'ONCE-SCHEMA2-SYN', bundle.parent, synthetic=True, settle_seconds=1)
        scan_source(initial, 'ONCE-SCHEMA2-SYN', now=100, synthetic_only=True)
        item = scan_source(initial, 'ONCE-SCHEMA2-SYN', now=101, synthetic_only=True)['accepted'][0]
        with initial.connection() as con:
            revision = con.execute('SELECT * FROM intake_revisions WHERE intake_id=? AND revision=?',
                                   (item['intake_id'], item['revision'])).fetchone()
        selection = dict(source_id='ONCE-SCHEMA2-SYN', intake_id=item['intake_id'], revision=item['revision'],
                         job_id=item['job_id'], revision_fingerprint=revision['fingerprint'],
                         files=json.loads(revision['files_json']))
        initial.close()
        store = Store.open_existing(str(base/'state'))
        self.addCleanup(store.close)
        with ExitStack() as stack:
            if kind in ('limited', 'partial'):
                limits = ExtractionLimits(max_page_content_bytes=1) if kind == 'limited' else ExtractionLimits(max_pages=1)
                stack.enter_context(patch('labflow.intake_documents.EXTRACTION_LIMITS', limits))
            context = prepare_registered_synthetic_context(store, selection, producer_name=NAME)
        executable = base/'codex.exe'
        executable.write_bytes(b'authored path fixture only; never a child')
        evidence = base/'evidence'
        evidence.mkdir()
        case = dict(base=base, store=store, selection=selection, context=context, calls=[],
                    kwargs=dict(worker_id='schema2-once-worker', producer_name=NAME, executable=executable,
                                requested_model='gpt-6.1-sol', evidence_root=evidence,
                                authorization_ref='ROOT-SYNTHETIC-SCHEMA2-ONCE'))
        self.cases.append(case)
        self.record.setdefault('original_G3_contexts', []).append(copy.deepcopy(context))
        return case

    def preflight(self, context):
        function = getattr(self.once, 'preflight_codex_intake_once_inputs', None)
        self.assertTrue(callable(function), 'pure public once request preflight is missing')
        return function(context, producer_name=NAME)

    def job(self, case):
        with case['store'].connection() as con:
            row = con.execute('SELECT state,attempt FROM intake_jobs WHERE job_id=?', (case['selection']['job_id'],)).fetchone()
        return dict(row)

    def response(self, context, producer):
        from labflow.intake_analysis import FIELDS
        facts = []
        version = context['analysis_contract']['schema_version']
        for document in context['documents']:
            if document.get('format') == 'pdf':
                sources = [(page['text'], dict(kind='pdf_page', extraction_id=document['extraction_id'],
                            page_number=page['page_number'], text_sha256=page['text_sha256'])) for page in document['pages']]
            else:
                sources = [(document['text'], dict(kind='text_line') if version == 2 else {})]
            for text, location in sources:
                for number, line in enumerate(text.splitlines(), 1):
                    field, separator, value = line.partition(':')
                    if separator and field in ('product_type', 'model', 'market', 'purpose'):
                        facts.append(dict(field=field, value=value.strip(), status='explicit', evidence=[dict(location,
                            path=document['path'], sha256=document['sha256'], line_start=number, line_end=number,
                            quote=line, role='request')]))
        result = dict(schema_version=version, producer=copy.deepcopy(producer), identity='single', facts=facts,
                      missing_fields=[field for field in FIELDS if field not in {fact['field'] for fact in facts}])
        if version == 2:
            result['context_id'] = context['analysis_context_id']
        return result

    def producer(self, case, mutate=None):
        def authored(prompt_bytes, schema_bytes, **kwargs):
            prompt = json.loads(prompt_bytes)
            context = json.loads(prompt['messages'][1]['content'])
            analysis = self.response(context, prompt['expected_producer'])
            if mutate is not None:
                mutate(analysis)
            response = C(analysis)
            directory = kwargs['evidence_dir']
            directory.mkdir()
            receipt = d2_receipt(kwargs['requested_model'], kwargs['timeout_seconds'],
                                 'codex-cli-exchange:' + 'b' * 32, prompt['expected_producer'])
            receipt.update(status='complete', failure=None)
            contents = dict(prompt=prompt_bytes, response_schema=schema_bytes, invocation=b'{}',
                            version_stdout=b'codex-cli 0.163.0-alpha.11.2\n', version_stderr=b'',
                            stdout_jsonl=b'{"authored_fixture":true}\n', stderr=b'', final_text=response, last_message=response)
            for key, payload in contents.items():
                item = receipt['artifacts'][key]
                (directory/item['path']).write_bytes(payload)
                item.update(present=True, bytes=len(payload), sha256=H(payload), complete=True,
                            overflow=False, extent='whole_file')
            receipt['bindings'].update(prompt_sha256=H(prompt_bytes), schema_sha256=H(schema_bytes), invocation_sha256=H(b'{}'))
            receipt['attempts'].update(version_process_attempts=1, model_process_attempts=1)
            receipt['client']['observed_version'] = '0.163.0-alpha.11.2'
            receipt['model']['cli_thread_id'] = 'authored-synthetic-thread'
            receipt['lifecycle'].update(model_process_started=True, exit_code=0, thread_started=1, turn_started=1,
                                         turn_completed=1, agent_messages=1, stdout_eof=True, stderr_eof=True)
            receipt['cleanup'].update(version_child_reaped=True, model_child_reaped=True, readers_joined=True,
                                       pipes_closed=True, artifacts_closed=True)
            receipt['controls']['observed'].update(argv_submitted=True, argv_exit0=True, empty_cwd_at_spawn=True, tool_items=0)
            receipt['verification']['wire_complete'] = True
            receipt['cost']['kind'] = 'unknown'
            (directory/'receipt.json').write_bytes(C(receipt))
            case['calls'].append(dict(prompt=prompt, schema=json.loads(schema_bytes), analysis=analysis, receipt=copy.deepcopy(receipt)))
            return response, copy.deepcopy(receipt)
        return authored

    def run_case(self, case, context=None, **changes):
        result = run_codex_intake_once(case['store'], case['context'] if context is None else context,
                                       **{**case['kwargs'], **changes})
        self.record.setdefault('once_results', []).append(copy.deepcopy(result))
        return result

    def test_fresh_queued_uppercase_pdf_and_mixed_text_join_genuine_G3_strict_claim_complete(self):
        from jsonschema import Draft202012Validator
        from labflow.intake_model_boundary import decode_analysis_response
        for kind in ('pdf', 'mixed'):
            with self.subTest(kind=kind):
                case = self.case(kind)
                before = C(case['context'])
                source = {p.name: p.read_bytes() for p in (case['base']/'inbox/bundle').iterdir()}
                self.assertEqual(self.job(case), dict(state='queued', attempt=0))
                with patch.object(self.once, 'claim_job', wraps=self.once.claim_job) as claim, \
                        patch.object(self.once, 'complete_job', wraps=self.once.complete_job) as complete, \
                        patch.object(self.once, 'produce_codex_cli_response', side_effect=self.producer(case)) as producer:
                    result = self.run_case(case)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(result['strict_decode'], 'accepted')
                self.assertEqual(set(result), TOP)
                self.assertEqual(result['job']['attempt'], 1)
                self.assertEqual(result['attempts']['automatic_retries'], 0)
                self.assertEqual(self.job(case), dict(state='completed', attempt=1))
                self.assertEqual((claim.call_count, producer.call_count, complete.call_count), (1, 1, 1))
                call = case['calls'][0]
                self.assertEqual(call['schema']['properties']['schema_version']['enum'], [2])
                Draft202012Validator(call['schema']).validate(call['analysis'])
                self.assertEqual(decode_analysis_response(C(call['analysis']), case['context'], producer_name=NAME), call['analysis'])
                kinds = {fact['evidence'][0]['kind'] for fact in call['analysis']['facts']}
                self.assertEqual(kinds, {'text_line', 'pdf_page'} if kind == 'mixed' else {'pdf_page'})
                self.assertEqual(result['binding']['context_sha256'], H(before))
                self.assertEqual(result['binding']['prompt_sha256'], H(C(call['prompt'])))
                self.assertEqual(result['binding']['schema_sha256'], H(C(call['schema'])))
                self.assertEqual(result['assessment']['verdict'], None)
                self.assertIsNone(call['receipt']['cost']['amount'])
                self.assertEqual(C(case['context']), before)
                self.assertEqual(source, {p.name: p.read_bytes() for p in (case['base']/'inbox/bundle').iterdir()})
                self.record.setdefault('successful_calls', []).append(call)

    def test_pure_preflight_is_detached_pinned_and_grants_no_state_or_execution_authority(self):
        case = self.case()
        before = C(case['context'])
        with ExitStack() as stack:
            for name in ('builtins.open', 'pathlib.Path.open', 'sqlite3.connect', 'subprocess.Popen',
                         'socket.create_connection', 'labflow.codex_intake_once.claim_job',
                         'labflow.codex_intake_once.complete_job', 'labflow.codex_intake_once.produce_codex_cli_response'):
                stack.enter_context(patch(name, side_effect=AssertionError('pure preflight I/O')))
            prepared = self.preflight(case['context'])
        self.assertEqual(set(prepared), {'schema_version', 'kind', 'status', 'context', 'prompt',
                                        'response_schema', 'pins', 'failure', 'execution_authority'})
        self.assertEqual(prepared['kind'], 'codex_intake_once_preflight')
        self.assertEqual(prepared['schema_version'], 1)
        self.assertEqual(prepared['status'], 'validated')
        self.assertIs(prepared['execution_authority'], False)
        self.assertIsNone(prepared['failure'])
        self.assertEqual(prepared['pins'], dict(context_sha256=H(before), prompt_sha256=H(C(prepared['prompt'])),
                                               schema_sha256=H(C(prepared['response_schema']))))
        self.record['preflight'] = copy.deepcopy(prepared)
        next(d for d in prepared['context']['documents'] if d.get('format') == 'pdf')['pages'].clear()
        prepared['response_schema']['properties'].clear()
        self.assertEqual(C(case['context']), before)
        self.assertEqual(self.job(case), dict(state='queued', attempt=0))
        self.assertEqual(list(case['kwargs']['evidence_root'].iterdir()), [])
        for value, code in ((None, 'codex_intake_once_invalid_input'), ({'private': 'AUTHORED-CANARY'}, 'codex_intake_once_invalid_input')):
            rejected = self.preflight(value)
            self.assertEqual(rejected['status'], 'blocked')
            self.assertEqual(rejected['failure'], code)
            for key in ('context', 'prompt', 'response_schema', 'pins'):
                self.assertIsNone(rejected[key])
            self.assertIs(rejected['execution_authority'], False)
            self.assertNotIn('AUTHORED-CANARY', C(rejected).decode())

    def test_text_G3_preflight_keeps_original_schema_one_default_bytes(self):
        from labflow.intake_model_boundary import build_analysis_response_schema
        case = self.case('text')
        result = self.preflight(case['context'])
        self.assertEqual(result['status'], 'validated')
        self.assertEqual(C(result['response_schema']), C(build_analysis_response_schema(producer_name=NAME)))
        self.assertEqual(result['response_schema']['properties']['schema_version']['enum'], [1])
        self.assertNotIn('context_id', result['response_schema']['properties'])
        self.assertEqual(self.job(case), dict(state='queued', attempt=0))

    def test_execution_quality_blocks_partial_missing_reordered_or_unread_pages_before_claim(self):
        case = self.case()
        original = C(case['context'])
        cases = []
        for changes in ({'parse_status': 'partial'}, {'complete': False}, {'issues': [{'code': 'authored_issue'}]},
                        {'total_pages': None}, {'total_pages': 3}, {'processed_pages': 1}, {'pages': []}):
            context = copy.deepcopy(case['context'])
            next(d for d in context['documents'] if d.get('format') == 'pdf').update(changes)
            cases.append(context)
        context = copy.deepcopy(case['context'])
        next(d for d in context['documents'] if d.get('format') == 'pdf')['pages'].reverse()
        cases.append(context)
        context = copy.deepcopy(case['context'])
        next(d for d in context['documents'] if d.get('format') == 'pdf')['pages'][0]['status'] = 'truncated'
        cases.append(context)
        context = copy.deepcopy(case['context'])
        text = next(d for d in context['documents'] if d.get('format') != 'pdf')
        text.update(text=None, parse_status='requires_parser')
        cases.append(context)
        for changes in ({'format': 'unsupported'}, {'text': ' \n'}, {'issues': [{'code': 'authored_text_issue'}]}):
            context = copy.deepcopy(case['context'])
            next(d for d in context['documents'] if d.get('format') != 'pdf').update(changes)
            cases.append(context)
        context = copy.deepcopy(case['context'])
        page = next(d for d in context['documents'] if d.get('format') == 'pdf')['pages'][0]
        page.update(text=' \n', text_sha256=H(b' \n'), line_spans=[dict(line_number=1, start=0, end=1)])
        cases.append(context)
        for index, context in enumerate(cases):
            with self.subTest(index=index), patch.object(self.once, 'claim_job') as claim, \
                    patch.object(self.once, 'produce_codex_cli_response') as producer:
                before = C(context)
                prepared = self.preflight(context)
                self.assertEqual(prepared['status'], 'blocked')
                self.assertEqual(prepared['failure'], 'codex_intake_once_unsupported_schema')
                result = self.run_case(case, context=context)
                self.assertEqual(result['errors'][0]['code'], prepared['failure'])
                claim.assert_not_called()
                producer.assert_not_called()
                self.assertEqual(C(context), before)
                self.assertEqual(list(case['kwargs']['evidence_root'].iterdir()), [])
        self.assertEqual(C(case['context']), original)
        self.assertEqual(self.job(case), dict(state='queued', attempt=0))
        self.record['authored_quality_mutations'] = cases

    def test_genuine_G3_unread_malformed_and_partial_stay_visible_but_not_dispatchable(self):
        for kind in ('malformed', 'limited', 'partial'):
            with self.subTest(kind=kind):
                case = self.case(kind)
                before = C(case['context'])
                pdf = case['context']['documents'][0]
                self.assertEqual(case['context']['analysis_contract']['schema_version'], 2)
                self.assertIsNone(pdf['text'])
                self.assertNotEqual(pdf['parse_status'], 'ok')
                prepared = self.preflight(case['context'])
                self.assertEqual(prepared['status'], 'blocked')
                self.assertEqual(prepared['failure'], 'codex_intake_once_unsupported_schema')
                self.assertEqual(C(case['context']), before)
                self.assertEqual(self.job(case), dict(state='queued', attempt=0))
                self.record.setdefault('unread_preflights', []).append(prepared)

    def test_original_strict_decoder_rejects_quote_context_page_schema_and_hash_mutations(self):
        from labflow.intake_model_boundary import decode_analysis_response
        case = self.case('pdf')
        prepared = self.preflight(case['context'])
        self.assertEqual(prepared['status'], 'validated')
        analysis = self.response(case['context'], prepared['prompt']['expected_producer'])
        original = C(analysis)
        mutations = []
        for changes in ({'quote': 'authored wrong quote'}, {'page_number': 99}, {'sha256': '0' * 64},
                        {'text_sha256': '0' * 64}, {'extraction_id': '0' * 64}):
            bad = copy.deepcopy(analysis)
            bad['facts'][0]['evidence'][0].update(changes)
            mutations.append(bad)
        mutations.extend([{**copy.deepcopy(analysis), 'context_id': '0' * 64},
                          {**copy.deepcopy(analysis), 'schema_version': 1}])
        for index, bad in enumerate(mutations):
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, '^analysis_response_invalid$'):
                decode_analysis_response(C(bad), case['context'], producer_name=NAME)
        self.assertEqual(C(analysis), original)
        self.assertEqual(self.job(case), dict(state='queued', attempt=0))
        self.record['authored_rejected_responses'] = mutations

    def test_pdf_wrong_quote_at_once_boundary_fails_once_without_completion_or_retry(self):
        case = self.case('pdf')
        def wrong(analysis):
            analysis['facts'][0]['evidence'][0]['quote'] = 'authored wrong quote'
        with patch.object(self.once, 'produce_codex_cli_response', side_effect=self.producer(case, wrong)) as producer, \
                patch.object(self.once, 'complete_job') as complete, patch.object(self.once, 'fail_job', wraps=self.once.fail_job) as fail:
            result = self.run_case(case)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['strict_decode'], 'rejected')
        self.assertEqual(result['errors'][0]['code'], 'analysis_response_invalid')
        self.assertEqual((producer.call_count, complete.call_count, fail.call_count), (1, 0, 1))
        self.assertEqual(result['attempts']['automatic_retries'], 0)
        self.assertEqual(self.job(case), dict(state='queued', attempt=1))

    def test_post_claim_context_or_schema_change_rejects_before_producer_without_refund(self):
        from labflow.intake_model_boundary import build_analysis_response_schema
        for change in ('context', 'schema'):
            case = self.case('pdf')
            real_claim = self.once.claim_job
            calls = []
            def changed_claim(*args, **kwargs):
                result = real_claim(*args, **kwargs)
                if change == 'context':
                    result['instructions'] += ' authored fresh scope mismatch'
                return result
            def changed_schema(**kwargs):
                result = build_analysis_response_schema(**kwargs)
                calls.append(True)
                if change == 'schema' and len(calls) > 1:
                    result['description'] = 'authored fresh schema mismatch'
                return result
            with self.subTest(change=change), patch.object(self.once, 'claim_job', side_effect=changed_claim) as claim, \
                    patch.object(self.once, 'build_analysis_response_schema', side_effect=changed_schema), \
                    patch.object(self.once, 'produce_codex_cli_response') as producer:
                result = self.run_case(case)
                self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_scope_mismatch')
                self.assertEqual(claim.call_count, 1)
                producer.assert_not_called()
                self.assertEqual(self.job(case), dict(state='queued', attempt=1))

    def test_preflight_enforces_exact_utf8_prompt_and_schema_caps_without_authority(self):
        case = self.case('pdf')
        context = copy.deepcopy(case['context'])
        context['instructions'] = ''
        initial = self.preflight(context)
        self.assertEqual(initial['status'], 'validated')
        context['instructions'] = 'x' * (262144 - len(C(initial['prompt'])))
        exact = self.preflight(context)
        self.assertEqual(exact['status'], 'validated')
        self.assertEqual(len(C(exact['prompt'])), 262144)
        context['instructions'] += 'x'
        above = self.preflight(context)
        self.assertEqual(above['status'], 'blocked')
        self.assertEqual(above['failure'], 'codex_intake_once_invalid_input')
        schema = copy.deepcopy(initial['response_schema'])
        schema['description'] = ''
        schema['description'] = 'x' * (65536 - len(C(schema)))
        with patch.object(self.once, 'build_analysis_response_schema', return_value=schema):
            exact_schema = self.preflight(case['context'])
            self.assertEqual(exact_schema['status'], 'validated')
            self.assertEqual(len(C(exact_schema['response_schema'])), 65536)
            schema['description'] += 'x'
            above_schema = self.preflight(case['context'])
            self.assertEqual(above_schema['status'], 'blocked')
            self.assertEqual(above_schema['failure'], 'codex_intake_once_invalid_input')
        self.assertEqual(self.job(case), dict(state='queued', attempt=0))
        self.record['limit_results'] = dict(prompt_exact_bytes=262144, schema_exact_bytes=65536,
                                            prompt_above=above, schema_above=above_schema)

    def test_preflight_first_controls_escape_unchanged_before_claim_and_dispatch(self):
        case = self.case('pdf')
        for kind in (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
            error = kind('authored first control')
            with self.subTest(kind=kind.__name__), patch('labflow.intake_model_boundary._snapshot', side_effect=error), \
                    patch.object(self.once, 'claim_job') as claim, patch.object(self.once, 'fail_job') as fail, \
                    patch.object(self.once, 'produce_codex_cli_response') as producer:
                with self.assertRaises(kind) as direct:
                    self.preflight(case['context'])
                self.assertIs(direct.exception, error)
                with self.assertRaises(kind) as called:
                    self.run_case(case)
                self.assertIs(called.exception, error)
                self.assertEqual(vars(error), {})
                claim.assert_not_called()
                fail.assert_not_called()
                producer.assert_not_called()
        self.assertEqual(list(case['kwargs']['evidence_root'].iterdir()), [])
        self.assertEqual(self.job(case), dict(state='queued', attempt=0))

    def test_pdf_strict_memory_control_survives_late_receipt_failure_without_DB_finalize(self):
        case = self.case('pdf')
        error = MemoryError('authored strict first control')
        with patch.object(self.once, 'produce_codex_cli_response', side_effect=self.producer(case)) as producer, \
                patch('labflow.intake_model_boundary.validate_analysis', side_effect=error), \
                patch.object(self.once, '_finalize', side_effect=OSError('authored late receipt failure')), \
                patch.object(self.once, 'fail_job') as fail, patch.object(self.once, 'complete_job') as complete:
            with self.assertRaises(MemoryError) as observed:
                self.run_case(case)
        self.assertIs(observed.exception, error)
        self.assertEqual(vars(error), {})
        self.assertEqual(producer.call_count, 1)
        fail.assert_not_called()
        complete.assert_not_called()
        self.assertEqual(self.job(case), dict(state='running', attempt=1))
        self.assertTrue((case['kwargs']['evidence_root']/'attempt-intent.json').is_file())
        self.assertTrue((case['kwargs']['evidence_root']/'exchange/receipt.json').is_file())
        self.record['control'] = 'first strict MemoryError; late receipt OSError suppressed; job lease unchanged'

    def test_completed_call_cannot_reuse_evidence_or_reclaim_or_regenerate_with_a_fresh_root(self):
        from labflow.intake_jobs import prepare_registered_synthetic_context
        case = self.case('pdf')
        with patch.object(self.once, 'produce_codex_cli_response', side_effect=self.producer(case)) as producer:
            self.assertEqual(self.run_case(case)['status'], 'completed')
        self.assertEqual(producer.call_count, 1)
        with patch.object(self.once, 'claim_job') as claim, patch.object(self.once, 'produce_codex_cli_response') as producer:
            reused = self.run_case(case)
            self.assertEqual(reused['errors'][0]['code'], 'codex_intake_once_invalid_input')
            claim.assert_not_called()
            producer.assert_not_called()
        evidence = case['base']/'evidence-new'
        evidence.mkdir()
        with patch.object(self.once, 'claim_job', wraps=self.once.claim_job) as claim, \
                patch.object(self.once, 'produce_codex_cli_response') as producer:
            idle = self.run_case(case, evidence_root=evidence)
            self.assertEqual(idle['status'], 'idle')
            self.assertEqual(idle['attempts']['producer_invocations'], 0)
            self.assertEqual(claim.call_count, 1)
            producer.assert_not_called()
        with self.assertRaisesRegex(ValueError, '^intake_preclaim_context_not_ready$'):
            prepare_registered_synthetic_context(case['store'], case['selection'], producer_name=NAME)
        self.assertEqual(self.job(case), dict(state='completed', attempt=1))


if __name__ == '__main__':
    unittest.main()
