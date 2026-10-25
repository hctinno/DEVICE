"""Fresh genuine virtual capture; only concrete D2 is faked. Actual CLI/model0."""
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import stat
import tempfile
import threading
import time
import types
import unittest
import uuid
from unittest.mock import patch

try:
    api = importlib.import_module('labflow.virtual_fleet.codex_virtual_one_action')
except ModuleNotFoundError as error:
    if error.name != 'labflow.virtual_fleet.codex_virtual_one_action':
        raise
    api = None

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/fcc/codex_first_decision_contract.json').read_text(encoding='utf-8'))
CLI = json.loads((ROOT / 'docs/fcc/codex_cli_response_contract.json').read_text(encoding='utf-8'))['contracts']
SCHEMA = CONTRACT['response_schema']['literal_utf8'].encode('utf-8')


def C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def H(data):
    return hashlib.sha256(data).hexdigest()


class OneActionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'Assigned concrete first-decision caller API is absent')
        scratch = ROOT / '.local/one-action-test-scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        for target in ('subprocess.Popen', 'socket.socket.connect', 'socket.getaddrinfo'):
            guard = patch(target, side_effect=AssertionError('ACTUAL_CLI_OR_NETWORK_FORBIDDEN'))
            guard.start()
            self.addCleanup(guard.stop)
        self.root = Path(self.temp.name)
        self.catalog = self.root / 'catalog.json'
        self.catalog_bytes = (ROOT / 'virtual_profiles/sm_a176u_unlicensed.json').read_bytes()
        self.catalog.write_bytes(self.catalog_bytes)
        self.exe = self.root / 'codex.exe'
        self.exe.write_bytes(b'FAKE_NATIVE_CLI_ONLY_NEVER_EXECUTED')
        self.calls = []
        self.receipts = []
        self.mode = 'normal'
        self.number = 0
        self.event = None
        self.clock_jump = None
        self.proposal = dict(kind='execute',device_id='dut',action='start',parameters={})
        self.trials=[]; self.runtime_calls=[]; self.during_produce=None

    def fake_produce(self, prompt_bytes, schema_bytes, **kwargs):
        from labflow.codex_cli_response import CodexCliResponseError
        self.calls.append(dict(prompt=prompt_bytes, schema=schema_bytes, **kwargs))
        prompt = json.loads(prompt_bytes)
        wire = dict(schema_version=1, kind='virtual_operator_response',
            request_sha256=prompt['binding']['request_sha256'], producer=prompt['expected_producer'],
            proposal=copy.deepcopy(self.proposal))
        if self.mode == 'wrong_binding': wire['request_sha256'] = '0' * 64
        if self.mode == 'wrong_producer': wire['producer'] = dict(kind='model', name='different-neutral-producer')
        if self.mode == 'forbidden': wire['proposal'] = dict(kind='execute', device_id='sensor', action='configure', parameters={})
        response = C(wire) if self.mode != 'fence' else b'```json\n{}\n```'
        directory = kwargs['evidence_dir']
        directory.mkdir()
        work = directory / 'work'
        work.mkdir()
        reference = 'codex-cli-exchange:' + uuid.uuid4().hex
        argv = [str(kwargs['executable']), 'exec', '--ignore-user-config', '--ignore-rules', '--sandbox', 'read-only',
            '--ephemeral', '--skip-git-repo-check', '--color', 'never', '--json', '--model', kwargs['requested_model'],
            '--output-schema', str(directory/'response-schema.json'), '--output-last-message', str(directory/'last-message.bin'), '-']
        invocation = dict(schema_version=1, kind='codex_cli_invocation', exchange_ref=reference,
            executable=str(kwargs['executable']), cwd=str(work), version_argv=[str(kwargs['executable']), '--version'],
            model_argv=argv, requested_model=kwargs['requested_model'], supported_version='0.163.0-alpha.11.2',
            timeout_seconds=float(kwargs['timeout_seconds']), prompt_sha256=H(prompt_bytes), response_schema_sha256=H(schema_bytes))
        events = [dict(type='thread.started', thread_id='fake-thread'), dict(type='turn.started'),
            dict(type='item.completed', item=dict(id='a1', type='agent_message', text=response.decode())),
            dict(type='turn.completed')]
        data = dict(prompt=prompt_bytes, response_schema=schema_bytes, invocation=C(invocation),
            version_stdout=b'codex-cli 0.163.0-alpha.11.2\n', version_stderr=b'',
            stdout_jsonl=b''.join(C(event)+b'\n' for event in events), stderr=b'', final_text=response, last_message=response)
        artifacts = {}
        for key, name in CLI['artifact_layout'].items():
            # The contract stores a literal filename for each artifact.
            if type(name) is dict: name = name['path']
            body = data[key]
            (directory/name).write_bytes(body)
            artifacts[key] = dict(path=name, present=True, bytes=len(body), sha256=H(body), complete=True, overflow=False, extent='whole_file')
        receipt = dict(schema_version=1, kind='codex_cli_response_receipt', exchange_ref=reference, status='complete', failure=None,
            bindings=dict(prompt_sha256=H(prompt_bytes), schema_sha256=H(schema_bytes), invocation_sha256=H(data['invocation']), producer_declaration=prompt['expected_producer']),
            client=dict(name='codex_cli', supported_version='0.163.0-alpha.11.2', observed_version='0.163.0-alpha.11.2', binary_content_sha256=None),
            model=dict(requested=kwargs['requested_model'], resolved=None, cli_thread_id='fake-thread', remote_request_id=None),
            attempts=dict(version_process_attempts=1, model_process_attempts=1, application_retries=0, internal_network_requests=None, internal_network_retries=None),
            lifecycle=dict(model_process_started=True, exit_code=0, thread_started=1, turn_started=1, turn_completed=1, agent_messages=1,
                reasoning_items=0, tool_items=0, stdout_eof=True, stderr_eof=True),
            usage=dict(input_tokens=17, cached_input_tokens=0, cache_write_input_tokens=7, output_tokens=1, reasoning_output_tokens=None),
            cost=dict(kind='unknown', amount=None, currency=None, price_version=None),
            timing=dict(timeout_seconds=float(kwargs['timeout_seconds']), local_elapsed_seconds=.01),
            controls=dict(requested=dict(ignore_user_config=True, ignore_rules=True, sandbox='read-only', ephemeral=True, empty_cwd=True, model_local_attempt_cap=1, automatic_retries=0),
                documented=dict(ignore_user_config='config_toml_only', ignore_rules='execpolicy_rules_only', sandbox='model_command_policy', ephemeral='session_rollout_only'),
                observed=dict(argv_submitted=True, argv_exit0=True, empty_cwd_at_spawn=True, tool_items=0), unknown=CLI['controls_unknown_exact16']),
            cleanup=dict(version_child_reaped=True, model_child_reaped=True, readers_joined=True, pipes_closed=True, artifacts_closed=True, descendants_reaped=None, remote_cancelled=None, secondary_errors=[]),
            artifacts=artifacts, limits=CLI['limits'], verification=dict(wire_complete=True, remote_identity_verified=False, semantic_quality_verified=False, external_data_authority_verified=False, storage_authenticity_verified=False))
        if self.mode == 'producer_error':
            receipt['status'] = 'failed'
            receipt['failure'] = dict(code='codex_cli_response_timeout', phase='collect')
            receipt['verification']['wire_complete'] = False
        if self.mode == 'bad_path': receipt['artifacts']['final_text']['path'] = '../forbidden.bin'
        if self.mode == 'bad_requested_model': receipt['model']['requested'] = 'gpt-6-astra' if kwargs['requested_model']=='gpt-6.1-sol' else 'gpt-6.1-sol'
        if self.mode == 'bad_nested_receipt': receipt['model'] = []
        if self.mode == 'bad_verification': receipt['verification']['semantic_quality_verified'] = True
        if self.mode == 'bad_exit': receipt['lifecycle']['exit_code'] = 7
        if self.mode != 'missing_receipt': (directory/'receipt.json').write_bytes(C(receipt))
        self.receipts.append(copy.deepcopy(receipt))
        if self.mode == 'tamper_final': (directory/'final-text.bin').write_bytes(response+b' ')
        if self.mode == 'short_artifact':
            path=directory/'stdout.jsonl';path.write_bytes(path.read_bytes()+b'EXTRA')
        if self.mode == 'producer_error': raise CodexCliResponseError('timeout', copy.deepcopy(receipt))
        if self.mode == 'unknown_error': raise CodexCliResponseError('spawn_failed', None)
        if self.mode == 'cancel_after': self.event.set()
        if self.clock_jump is not None: self.clock_jump()
        if self.during_produce is not None: self.during_produce()
        return response, copy.deepcopy(receipt)

    def call(self, mode='normal', **overrides):
        self.number+=1; self.evidence=self.root/('run-'+str(self.number)); self.mode=mode
        options=dict(catalog_path=self.catalog,catalog_sha256=H(self.catalog_bytes),response_schema_bytes=SCHEMA,
            executable=self.exe,requested_model='gpt-6.1-sol',scenario='normal',virtual_dispatch_authorized=True,evidence_dir=self.evidence)
        options.update(overrides)
        real=api._prepare
        def prepare(*args,**kwargs):
            trial=real(*args,**kwargs); self.trials.append(trial)
            for name in ('execute','advance'):
                original=getattr(trial.runtime,name)
                def traced(*args,_name=name,_original=original,**kwargs):
                    self.runtime_calls.append((_name,args)); return _original(*args,**kwargs)
                setattr(trial.runtime,name,traced)
            return trial
        with patch.object(api,'_produce',side_effect=self.fake_produce),patch.object(api,'_prepare',side_effect=prepare):
            return api.run_codex_virtual_one_action(**options)

    def failure(self, suffix, mode='normal', **kwargs):
        code=suffix if suffix.startswith(('codex_cli_','model_operator_')) else 'operator_virtual_one_action_'+suffix
        with self.assertRaises(api.CodexVirtualOneActionError) as got: self.call(mode,**kwargs)
        e=got.exception
        self.assertEqual((e.code,str(e),e.args),(code,code,(code,)))
        self.assertIsNone(e.__cause__); self.assertIsNone(e.__context__)
        self.assertNotIn('FAKE_SECRET',str(e)); self.assertNotIn(str(self.root),str(e))
        if e.receipt is not None: self.assertEqual(e.receipt['failure']['code'],code)
        return e

    def assert_trace(self,r,status):
        self.assertEqual(set(r),set('schema_version kind run_id status failure declaration budget step cancellation cleanup execution verification'.split()))
        self.assertEqual(r['status'],status); self.assertEqual(r['kind'],'codex_virtual_one_action_result')
        self.assertEqual(r['execution']['task_assessment_status'],'not_executed')
        self.assertIsNone(r['execution']['task_score']); self.assertFalse(r['execution']['closed_loop_complete'])
        self.assertFalse(r['execution']['hardware_verified']); self.assertFalse(r['cleanup']['remote_cancel_verified'])
        self.assertIsNone(r['cleanup']['virtual_outputs_disabled'])
        self.assertEqual(len(r['step']),10); self.assertEqual(len(r['step']['dispatch']),8)
        self.assertEqual(r['budget']['reserved_model_calls'],1); self.assertFalse(r['budget']['reservation_refunded'])
        self.assertEqual(r['budget']['application_retries'],0); self.assertFalse(r['budget']['new_budget_granted'])
        report=json.loads((self.evidence/'harness-report.json').read_bytes())
        self.assertFalse(report['ai_model_called']); self.assertEqual(report['assessment']['status'],'not_assessed')
        events=json.loads((self.evidence/'harness-events.json').read_bytes())
        self.assertEqual(sum(e['type']=='policy_decision' for e in events),1)
        self.assertEqual(report['usage']['decisions'],1); self.assertEqual(report['usage']['transport_retries'],0)
        self.assertEqual(report['unresolved_request_ids'],[])

    def test_public_signature_and_exports(self):
        import inspect
        names=['catalog_path','catalog_sha256','response_schema_bytes','executable','requested_model','scenario','virtual_dispatch_authorized','evidence_dir','cancel_event']
        self.assertEqual(api.__all__,['run_codex_virtual_one_action','CodexVirtualOneActionError'])
        sig=inspect.signature(api.run_codex_virtual_one_action)
        self.assertEqual(list(sig.parameters),names)
        self.assertTrue(all(p.kind==p.KEYWORD_ONLY for p in sig.parameters.values()))

    def test_delegation_false_and_nonbool_preflight_zero(self):
        for value,suffix in [(False,'delegation_denied'),(1,'invalid_input'),(None,'invalid_input')]:
            self.failure(suffix,virtual_dispatch_authorized=value)
            self.assertFalse(self.evidence.exists()); self.assertEqual(self.trials,[]); self.assertEqual(self.calls,[])

    def test_fresh64_capture_bound_stop_zero_dispatch(self):
        self.proposal=dict(kind='stop',claim='completed',reason='bounded claim only')
        r=self.call(); self.assert_trace(r,'stopped'); self.assertEqual(self.runtime_calls,[])
        ctx=json.loads((self.evidence/'context8.json').read_bytes())
        self.assertEqual(len(ctx['observations']['devices']),64); self.assertEqual(len(ctx['catalog']['profiles']),64)
        self.assertEqual(ctx['remaining_budget']['decisions'],0)
        user=json.loads(json.loads(self.calls[-1]['prompt'])['messages'][1]['content'])['request']['user_input']
        self.assertNotIn('remaining_budget',user['public_context'])
        self.assertEqual(user['delegation']['harness_budgets'],dict(decisions=1,logical_requests=1,ticks=1,wall_seconds=30,transport_retries=0))
        self.assertEqual(r['execution']['model_proposal_dispatches'],0)
        self.assertEqual(r['step']['dispatch']['effect'],'not_applicable')

    def test_same_live_trial_one_execute_then_supervisor_stop(self):
        r=self.call(); self.assert_trace(r,'observed')
        self.assertEqual(len(self.trials),1); self.assertEqual([x[0] for x in self.runtime_calls],['execute'])
        self.assertEqual(r['step']['binding']['runtime_instance_id'],self.trials[0].runtime_instance_id)
        self.assertEqual(r['step']['dispatch']['confirmed_receipts'],1)
        self.assertEqual(r['step']['dispatch']['effect'],'changed')
        self.assertEqual(r['step']['harness']['termination']['reason'],'supervisor_stop')
        self.assertEqual(r['step']['before']['tick'],r['step']['after']['tick'])
        self.assertEqual(r['step']['dispatch']['receipt_status'],'pending')

    def test_advance_exactly_one_tick_no_followup(self):
        self.proposal=dict(kind='advance',ticks=1); r=self.call(); self.assert_trace(r,'observed')
        self.assertEqual([x[0] for x in self.runtime_calls],['advance'])
        self.assertEqual(r['step']['after']['tick']-r['step']['before']['tick'],1)
        self.assertEqual(len(self.calls),1)

    def test_sensor_read_unchanged_is_not_task_success(self):
        self.proposal=dict(kind='execute',device_id='sensor',action='read',parameters={})
        try: r=self.call()
        except api.CodexVirtualOneActionError as e: r=e.receipt
        self.assertEqual(len(self.runtime_calls),1); self.assertIsNone(r['execution']['task_score'])
        self.assertIn(r['step']['dispatch']['effect'],['changed','unchanged'])
        self.assertFalse(r['execution']['closed_loop_complete'])

    def test_scope_cannot_expand_to_other64_actions(self):
        for mode,suffix in [('forbidden','model_operator_boundary_proposal_invalid'),('wrong_binding','model_operator_boundary_response_binding_mismatch'),('wrong_producer','model_operator_boundary_response_producer_mismatch'),('fence','model_operator_boundary_response_invalid')]:
            self.failure(suffix,mode); self.assertEqual(self.runtime_calls,[])

    def test_stale_binding_or_changed_observation_prevents_dispatch(self):
        self.during_produce=lambda:self.trials[-1].runtime.advance('owner-injected-drift',1)
        e=self.failure('capture_failed'); self.assertEqual(e.receipt['execution']['model_proposal_dispatches'],0)
        self.assertEqual(len(self.runtime_calls),1) # injected external drift, no model command
        self.assertEqual(e.receipt['budget']['reserved_model_calls'],1)

    def test_current_source_changed_prevents_dispatch(self):
        original=api._read
        def read(path,*args,**kwargs):
            b=original(path,*args,**kwargs)
            return b+b'changed' if self.calls and path.name=='harness.py' else b
        with patch.object(api,'_read',side_effect=read): self.failure('unsupported_source')
        self.assertEqual(self.runtime_calls,[])

    def test_runtime_rejected_or_uncertain_never_retries(self):
        e=self.failure('runtime_rejected',scenario='restored_disconnect')
        self.assertEqual(e.receipt['status'],'rejected'); self.assertEqual(len(self.runtime_calls),1)
        self.assertEqual(e.receipt['step']['dispatch']['receipt_status'],'disconnected')
        from labflow.virtual_fleet.harness import RetryableTransportError
        self.runtime_calls=[]
        def fault():
            def execute(*a,**k):
                self.runtime_calls.append(('execute',a)); raise RetryableTransportError()
            self.trials[-1].runtime.execute=execute
        self.during_produce=fault; e=self.failure('runtime_uncertain')
        self.assertEqual(len(self.runtime_calls),1)
        self.assertIsNone(e.receipt['execution']['model_proposal_dispatches'])
        self.assertEqual(e.receipt['step']['dispatch']['confirmed_receipts'],0)

    def test_tighter_harness_deadline_limits_producer_timeout(self):
        self.call(); self.assertGreater(self.calls[-1]['timeout_seconds'],0)
        self.assertLessEqual(self.calls[-1]['timeout_seconds'],24.0)

    def test_late_valid_wire_and_cancel_do_not_dispatch(self):
        self.event=threading.Event(); e=self.failure('cancelled','cancel_after',cancel_event=self.event)
        self.assertEqual(self.runtime_calls,[]); self.assertTrue((self.evidence/'producer/final-text.bin').is_file())
        clock=[100.0]
        with patch.object(api,'time',types.SimpleNamespace(monotonic=lambda:clock[0])):
            self.clock_jump=lambda:clock.__setitem__(0,131.0)
            self.failure('timeout')
        self.assertEqual(self.runtime_calls,[])

    def test_cancellation_after_intent_preserves_uncertainty(self):
        self.event=threading.Event()
        def fault():
            original=self.trials[-1].runtime.execute
            def execute(*a,**k):
                result=original(*a,**k); self.event.set(); return result
            self.trials[-1].runtime.execute=execute
        self.during_produce=fault; e=self.failure('cancelled',cancel_event=self.event)
        self.assertEqual(len(self.runtime_calls),1); self.assertEqual(e.receipt['budget']['reserved_model_calls'],1)

    def test_original_producer_artifacts_and_receipt_are_exact(self):
        r=self.call(); self.assertEqual(r['step']['transport']['receipt'],self.receipts[-1])
        self.assertEqual(r['step']['transport']['receipt_sha256'],H((self.evidence/'producer/receipt.json').read_bytes()))
        self.assertEqual(len(r['step']['artifacts']),10)
        for d in r['step']['artifacts'].values():
            b=(self.evidence/d['path']).read_bytes(); self.assertEqual((len(b),H(b)),(d['bytes'],d['sha256']))
        self.assertEqual(json.loads((self.evidence/'one-action-receipt.json').read_bytes()),r)

    def test_short_read_or_final_mismatch_prevents_decoder(self):
        for mode in ['short_artifact','tamper_final','bad_path','missing_receipt','bad_nested_receipt','bad_verification']:
            with patch.object(api,'_decode',wraps=api._decode) as decode:
                self.failure('retention_failed',mode); self.assertEqual(decode.call_count,0)
        self.assertEqual(self.runtime_calls,[])

    def test_postdispatch_observation_failure_preserves_first_stage(self):
        def fault():
            runtime=self.trials[-1].runtime; original=runtime.execute
            def execute(*a,**k):
                result=original(*a,**k)
                runtime.observations=lambda: (_ for _ in ()).throw(OSError('FAKE_SECRET'))
                return result
            runtime.execute=execute
        self.during_produce=fault; e=self.failure('runtime_uncertain')
        self.assertEqual(len(self.runtime_calls),1); self.assertIsNone(e.receipt['step']['dispatch']['runtime_call_attempts'])
        self.assertIn(e.receipt['failure']['stage'],['dispatch','observe'])

    def test_bounded_close_and_control_identity_survive_secondary_error(self):
        control=KeyboardInterrupt('same object')
        def fault(): raise control
        self.during_produce=fault
        with self.assertRaises(KeyboardInterrupt) as got: self.call()
        self.assertIs(got.exception,control); self.assertEqual(self.runtime_calls,[])
        self.during_produce=None
        e=self.failure('codex_cli_response_timeout','producer_error')
        self.assertEqual(e.receipt['failure']['stage'],'producer')
        self.assertEqual(self.runtime_calls,[])

    def test_bad_native_paths_schema_and_no_reservation(self):
        for kw in [dict(requested_model=['gpt-6.1-sol']),dict(scenario=['normal']),dict(catalog_path=str(self.catalog)),dict(response_schema_bytes=b'{}'),dict(evidence_dir=self.root)]:
            self.failure('invalid_input',**kw)
        self.assertEqual(self.calls,[]); self.assertEqual(self.trials,[])

    def test_result_is_detached_and_fresh_runs_do_not_reuse_binding(self):
        first=self.call(); first['step']['wire']['proposal']['action']='bad'
        second=self.call()
        self.assertNotEqual(first['step']['binding']['runtime_instance_id'],second['step']['binding']['runtime_instance_id'])
        self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertEqual(second['step']['wire']['proposal']['action'],'start')
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.catalog.read_bytes(),self.catalog_bytes)

    def test_unknown_producer_attempts_stay_null(self):
        e=self.failure('codex_cli_response_spawn_failed','unknown_error')
        self.assertIsNone(e.receipt['budget']['model_process_attempts'])
        self.assertEqual(e.receipt['budget']['reserved_model_calls'],1)
        self.assertEqual(self.runtime_calls,[])

    def test_unreadable_events_after_dispatch_are_unknown_not_zero(self):
        with patch.object(api._Harness,'events',side_effect=OSError('FAKE_SECRET')):
            e=self.failure('runtime_uncertain')
        self.assertEqual(len(self.runtime_calls),1)
        self.assertIsNone(e.receipt['execution']['model_proposal_dispatches'])
        self.assertIsNone(e.receipt['step']['dispatch']['runtime_call_attempts'])

    def test_remaining_five_seconds_does_not_reserve_or_produce(self):
        clock=[100.0]; original=api._Run.phase
        def phase(owner,stage):
            original(owner,stage)
            if stage=='reserve': clock[0]=owner.harness_deadline-5
        with patch.object(api,'time',types.SimpleNamespace(monotonic=lambda:clock[0])),patch.object(api._Run,'phase',phase):
            e=self.failure('budget_exhausted')
        self.assertEqual(self.calls,[]); self.assertEqual(self.runtime_calls,[])
        self.assertEqual(e.receipt['budget']['reserved_model_calls'],0)

    def test_after_decoder_generation_change_is_rejected(self):
        original=api._decode
        def decode(*a,**k):
            wire=original(*a,**k)
            self.trials[-1].runtime.advance('postdecoder-external-drift',1)
            return wire
        with patch.object(api,'_decode',side_effect=decode): e=self.failure('capture_failed')
        self.assertTrue(e.receipt['verification']['wire_accepted'])
        self.assertEqual(e.receipt['execution']['model_proposal_dispatches'],0)
        self.assertEqual(len(self.runtime_calls),1) # injected drift only

    def test_slow_host_close_is_bounded_and_never_starts_factory(self):
        gate=threading.Event(); finished=threading.Event(); original=Path.open
        class Slow:
            def __init__(self,handle): self.handle=handle
            def write(self,data): return self.handle.write(data)
            def close(self):
                gate.wait(10)
                try: self.handle.close()
                finally: finished.set()
        def opening(path,*a,**k):
            handle=original(path,*a,**k)
            return Slow(handle) if path.name=='response-schema.json' and a and a[0]=='xb' else handle
        start=time.monotonic()
        try:
            with patch.object(Path,'open',opening): e=self.failure('cleanup_failed')
            self.assertLess(time.monotonic()-start,4.0)
            self.assertFalse(e.receipt['cleanup']['host_artifacts_closed'])
            self.assertEqual(self.trials,[]); self.assertEqual(self.calls,[])
        finally: gate.set(); self.assertTrue(finished.wait(2))

    def test_terminal_artifact_close_failure_is_cleanup_not_receipt_write(self):
        original=Path.open
        class BrokenClose:
            def __init__(self,handle): self.handle=handle
            def write(self,data): return self.handle.write(data)
            def close(self): self.handle.close(); raise OSError('FAKE_SECRET')
        def opening(path,*a,**k):
            handle=original(path,*a,**k)
            return BrokenClose(handle) if path.name=='harness-events.json' and a and a[0]=='xb' else handle
        with patch.object(Path,'open',opening): e=self.failure('cleanup_failed')
        self.assertEqual(len(self.runtime_calls),1)
        self.assertIn('artifact_close_failed',e.receipt['cleanup']['secondary_errors'])
        self.assertNotIn('receipt_write_failed',e.receipt['cleanup']['secondary_errors'])

    def test_runtime_rejection_precedes_terminal_close_failure(self):
        original=Path.open
        class BrokenClose:
            def __init__(self,handle): self.handle=handle
            def write(self,data): return self.handle.write(data)
            def close(self): self.handle.close(); raise OSError('FAKE_SECRET')
        def opening(path,*a,**k):
            handle=original(path,*a,**k)
            return BrokenClose(handle) if path.name=='harness-events.json' and a and a[0]=='xb' else handle
        with patch.object(Path,'open',opening): e=self.failure('runtime_rejected',scenario='restored_disconnect')
        self.assertEqual(e.receipt['failure']['stage'],'dispatch')
        self.assertEqual(len(self.runtime_calls),1)
        self.assertIn('artifact_close_failed',e.receipt['cleanup']['secondary_errors'])

    def test_observed_runtime_rejection_precedes_late_cancel(self):
        self.event=threading.Event()
        def fault():
            original=self.trials[-1].runtime.execute
            def execute(*a,**k):
                value=original(*a,**k); self.event.set(); return value
            self.trials[-1].runtime.execute=execute
        self.during_produce=fault
        e=self.failure('runtime_rejected',scenario='restored_disconnect',cancel_event=self.event)
        self.assertEqual(e.receipt['failure']['stage'],'dispatch')
        self.assertTrue(e.receipt['cancellation']['requested'])
        self.assertEqual(len(self.runtime_calls),1)

    def test_host_write_control_survives_secondary_close_failure(self):
        control=GeneratorExit('same control'); original=Path.open
        class Broken:
            def __init__(self,handle): self.handle=handle
            def write(self,data): raise control
            def close(self): self.handle.close(); raise OSError('FAKE_SECRET')
        def opening(path,*a,**k):
            handle=original(path,*a,**k)
            return Broken(handle) if path.name=='response-schema.json' and a and a[0]=='xb' else handle
        with patch.object(Path,'open',opening),self.assertRaises(GeneratorExit) as got: self.call()
        self.assertIs(got.exception,control); self.assertEqual(self.trials,[]); self.assertEqual(self.calls,[])

if __name__=='__main__': unittest.main()
