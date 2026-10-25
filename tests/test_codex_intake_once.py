"""Disposable synthetic Stores and fake concrete D2; installed CLI/network0."""
import copy
import hashlib
import json
import io
from contextlib import redirect_stderr, redirect_stdout
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

    def test_unsupported_schema_is_rejected_before_claim(self):
        self.context['analysis_contract']['schema_version'] = 2
        with patch('labflow.codex_intake_once.claim_job') as claim, \
                patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
            result = self.run_once()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_unsupported_schema')
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

    def test_full_public8_and_PDF_boundary_are_checked_before_claim(self):
        missing_id = copy.deepcopy(self.context)
        missing_id.pop('analysis_context_id')
        pdf = copy.deepcopy(self.context)
        pdf['documents'][0]['format'] = 'pdf'
        for context, code in ((missing_id, 'invalid_input'), (pdf, 'unsupported_schema')):
            self.fresh_case()
            with self.subTest(code=code), patch('labflow.codex_intake_once.claim_job') as claim, \
                    patch('labflow.codex_intake_once.produce_codex_cli_response') as producer:
                result = run_codex_intake_once(self.store, context, **self.kwargs)
                self.assertEqual(result['errors'][0]['code'], 'codex_intake_once_' + code)
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


if __name__ == '__main__':
    unittest.main()
