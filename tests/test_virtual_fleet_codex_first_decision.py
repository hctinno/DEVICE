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
    api = importlib.import_module('labflow.virtual_fleet.codex_first_decision')
except ModuleNotFoundError as error:
    if error.name != 'labflow.virtual_fleet.codex_first_decision':
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


class FirstDecisionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'Assigned concrete first-decision caller API is absent')
        scratch = ROOT / '.local/first-decision-test-scratch'
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

    def fake_produce(self, prompt_bytes, schema_bytes, **kwargs):
        from labflow.codex_cli_response import CodexCliResponseError
        self.calls.append(dict(prompt=prompt_bytes, schema=schema_bytes, **kwargs))
        prompt = json.loads(prompt_bytes)
        wire = dict(schema_version=1, kind='virtual_operator_response',
            request_sha256=prompt['binding']['request_sha256'], producer=prompt['expected_producer'],
            proposal=dict(kind='execute', device_id='dut', action='start', parameters={}))
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
        return response, copy.deepcopy(receipt)

    def call(self, mode='normal', **overrides):
        self.number += 1
        self.evidence = self.root / ('batch-'+str(self.number))
        self.mode = mode
        options = dict(catalog_path=self.catalog, catalog_sha256=H(self.catalog_bytes), response_schema_bytes=SCHEMA,
            executable=self.exe, requested_models=['gpt-6.1-sol'], scenarios=['normal'], evidence_dir=self.evidence)
        options.update(overrides)
        with patch.object(api, '_produce', side_effect=self.fake_produce):
            return api.run_codex_first_decisions(**options)

    def failure(self, code, mode='normal', **overrides):
        with self.assertRaises(api.CodexFirstDecisionError) as got:
            self.call(mode, **overrides)
        error = got.exception
        self.assertEqual((error.code, str(error), error.args), (code, code, (code,)))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn('FAKE_SECRET', str(error))
        self.assertNotIn(str(self.root), str(error))
        if error.receipt is not None:
            self.assertEqual(error.receipt['status'], 'failed')
            self.assertEqual(error.receipt['failure']['code'], code)
            self.assertFalse(error.receipt['verification']['wire_complete'])
            self.assertNotIn(str(self.root), json.dumps(error.receipt))
        return error

    def test_public_signature_and_exports(self):
        sig = inspect.signature(api.run_codex_first_decisions)
        self.assertEqual(list(sig.parameters), [p['name'] for p in CONTRACT['public_function']['parameters']])
        self.assertTrue(all(p.kind==inspect.Parameter.KEYWORD_ONLY for p in sig.parameters.values()))
        self.assertIsNone(sig.parameters['cancel_event'].default)
        self.assertEqual(api.__all__, ['run_codex_first_decisions', 'CodexFirstDecisionError'])

    def test_fullfresh_matrix_original_false_and_zero_model_dispatch(self):
        result = self.call(requested_models=['gpt-6.1-sol','gpt-6-astra'], scenarios=['normal','restored_disconnect'])
        self.assertEqual(set(result), set(CONTRACT['receipt']['exact_keys']['batch']))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual([(s['scenario'],s['requested_model']) for s in result['slots']],
            [('normal','gpt-6.1-sol'),('normal','gpt-6-astra'),('restored_disconnect','gpt-6.1-sol'),('restored_disconnect','gpt-6-astra')])
        self.assertEqual(result['execution'], dict(mode='native_cli_first_decision',model_proposal_dispatches=0,task_assessment_status='not_executed',task_score=None))
        self.assertEqual(result['budget']['reserved_slots'], 4)
        self.assertEqual(result['budget']['producer_calls_started'], 4)
        self.assertEqual(result['budget']['model_process_attempts'], 4)
        self.assertEqual(result['budget']['limits']['model_calls'], 8)
        self.assertEqual(result['budget']['limits']['wall_seconds'], 60.0)
        self.assertFalse(result['budget']['reset_used'])
        self.assertEqual(len({s['binding']['runtime_instance_id'] for s in result['slots']}),4)
        for slot in result['slots']:
            self.assertEqual(slot['capture']['profile_count'],64)
            self.assertEqual(slot['capture']['device_count'],64)
            self.assertFalse(slot['capture']['legacy_ai_model_called'])
            self.assertEqual(slot['capture']['model_proposal_dispatches'],0)
            self.assertEqual(slot['status'],'complete')
            self.assertEqual(slot['transport']['receipt'],self.receipts[slot['slot_index']-1])
            folder=self.evidence/('slot-'+str(slot['slot_index']).zfill(4))
            report=json.loads((folder/'capture-report.json').read_bytes())
            events=json.loads((folder/'capture-events.json').read_bytes())
            self.assertFalse(report['ai_model_called']);self.assertEqual(report['assessment']['status'],'not_assessed')
            self.assertEqual(report['policy']['kind'],'fixture');self.assertEqual(report['termination']['policy_claim'],'blocked')
            self.assertEqual([e['type'] for e in events],['observation','policy_decision','termination'])
        self.assertEqual(result,json.loads((self.evidence/'batch-receipt.json').read_bytes()))

    def test_prompt_is_full_canonical_bound_and_schema_literal(self):
        result=self.call(requested_models=['gpt-6.1-sol','gpt-6-astra'])
        self.assertEqual(len(self.calls),2)
        first,second=[json.loads(c['prompt']) for c in self.calls]
        self.assertNotEqual(first['binding']['run_id'],second['binding']['run_id'])
        self.assertEqual(first['binding']['context_sha256'],second['binding']['context_sha256'])
        self.assertNotEqual(self.calls[0]['prompt'],self.calls[1]['prompt'])
        for call in self.calls:
            p=json.loads(call['prompt']);self.assertEqual(C(p),call['prompt']);self.assertEqual(call['schema'],SCHEMA)
            context=json.loads(p['messages'][1]['content'])['request']['user_input']['public_context']
            self.assertNotIn('remaining_budget',context);self.assertEqual(len(context['catalog']['profiles']),64)
            self.assertGreater(len(call['prompt']),100000);self.assertLessEqual(len(call['prompt']),262144)
            self.assertEqual(p['expected_producer'],dict(kind='model',name='dgm-virtual-operator-v1'))
            self.assertGreater(call['timeout_seconds'],0);self.assertLess(call['timeout_seconds'],54)
        self.assertTrue(result['verification']['wire_complete'])

    def test_bad_scalar_list_and_subclass_inputs_have_no_call_or_evidence(self):
        class List(list):
            def __iter__(self):raise AssertionError('unexpected hook')
        class Bytes(bytes):pass
        for changes in [dict(requested_models=[]),dict(requested_models=['other']),dict(requested_models=['gpt-6.1-sol']*2),
            dict(requested_models=List(['gpt-6.1-sol'])),dict(scenarios=[]),dict(scenarios=['unknown']),dict(scenarios=['normal']*2),
            dict(response_schema_bytes=Bytes(SCHEMA)),dict(response_schema_bytes='schema'),dict(cancel_event=object())]:
            with self.subTest(changes=type(changes).__name__):
                error=self.failure('operator_first_decision_invalid_input',**changes)
                self.assertIsNone(error.receipt);self.assertFalse(self.evidence.exists())
        self.assertEqual(self.calls,[])

    def test_catalog_and_schema_pins_fail_before_virtual_prepare(self):
        with patch.object(api,'_prepare',side_effect=AssertionError('must not prepare')):
            self.failure('operator_first_decision_unsupported_source',catalog_sha256='0'*64)
            self.failure('operator_first_decision_invalid_input',response_schema_bytes=b'{}')
        self.assertEqual(self.calls,[])

    def test_paths_existing_output_and_reparse_are_rejected(self):
        for changes in [dict(catalog_path=str(self.catalog)),dict(executable=Path('codex.exe')),dict(evidence_dir=self.root)]:
            self.failure('operator_first_decision_invalid_input',**changes)
        original=Path.lstat
        def reparse(path,*args,**kwargs):
            info=original(path,*args,**kwargs)
            return types.SimpleNamespace(st_mode=info.st_mode,st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT) if path==self.catalog else info
        with patch.object(Path,'lstat',new=reparse):self.failure('operator_first_decision_invalid_input')
        self.assertEqual(self.calls,[])

    def test_first_source_error_preserved_no_refund_or_later_slots(self):
        error=self.failure('codex_cli_response_timeout','producer_error',requested_models=['gpt-6.1-sol','gpt-6-astra'],scenarios=['normal','restored_disconnect'])
        self.assertEqual(len(self.calls),1);r=error.receipt
        self.assertEqual(r['budget']['reserved_slots'],1);self.assertEqual(r['budget']['producer_calls_started'],1)
        self.assertEqual(r['budget']['model_process_attempts'],1)
        self.assertTrue(all(s['status']=='not_executed' for s in r['slots'][1:]))
        self.assertEqual(r['slots'][0]['transport']['receipt'],self.receipts[0])
        self.assertEqual(r['slots'][0]['transport']['receipt']['failure']['phase'],'collect')

    def test_source_receipt_absent_attempts_are_unknown(self):
        error=self.failure('codex_cli_response_spawn_failed','unknown_error',requested_models=['gpt-6.1-sol','gpt-6-astra'])
        self.assertEqual(error.receipt['budget']['reserved_slots'],1)
        self.assertIsNone(error.receipt['budget']['model_process_attempts'])
        self.assertEqual(len(self.calls),1)

    def test_retention_mismatch_prevents_genuine_decoder(self):
        for mode in ['missing_receipt','bad_path','tamper_final','bad_requested_model']:
            with self.subTest(mode=mode),patch.object(api,'_decode',side_effect=AssertionError('decoder must remain0')):
                self.failure('operator_first_decision_retention_failed',mode)

    def test_strict_decoder_original_binding_producer_scope_errors(self):
        for mode,suffix in [('wrong_binding','response_binding_mismatch'),('wrong_producer','response_producer_mismatch'),('forbidden','proposal_invalid'),('fence','response_invalid')]:
            with self.subTest(mode=mode):
                error=self.failure('model_operator_boundary_'+suffix,mode)
                self.assertIsNone(error.receipt['slots'][0]['wire'])
                self.assertEqual(error.receipt['slots'][0]['transport']['receipt']['status'],'complete')

    def test_preset_and_postproducer_event_cancel_keep_original_trace(self):
        event=threading.Event();event.set()
        error=self.failure('operator_first_decision_cancelled',cancel_event=event)
        self.assertIsNone(error.receipt);self.assertEqual(self.calls,[])
        event=threading.Event();self.event=event
        with patch.object(api,'_decode',side_effect=AssertionError('late cancel must not decode')):
            error=self.failure('operator_first_decision_cancelled','cancel_after',cancel_event=event,requested_models=['gpt-6.1-sol','gpt-6-astra'])
        self.assertEqual(len(self.calls),1);self.assertTrue(error.receipt['cancellation']['requested'])
        self.assertEqual(error.receipt['cancellation']['scope'],'between_stages_only')
        self.assertEqual(error.receipt['slots'][0]['transport']['receipt']['status'],'complete')

    def test_insufficient_remaining_wall_does_not_reserve_or_produce(self):
        original_prepare=api._prepare;original_clock=time.monotonic;offset=[0]
        def prepare(*args,**kwargs):
            trial=original_prepare(*args,**kwargs);offset[0]=55;return trial
        with patch.object(api,'_prepare',side_effect=prepare),patch.object(api.time,'monotonic',side_effect=lambda:original_clock()+offset[0]):
            error=self.failure('operator_first_decision_budget_exhausted')
        self.assertEqual(self.calls,[]);self.assertEqual(error.receipt['budget']['reserved_slots'],0)

    def test_postproducer_deadline_keeps_trace_and_decoder_zero(self):
        original_clock=time.monotonic;offset=[0];self.clock_jump=lambda:offset.__setitem__(0,61)
        with patch.object(api.time,'monotonic',side_effect=lambda:original_clock()+offset[0]),patch.object(api,'_decode',side_effect=AssertionError('deadline must block decoder')):
            error=self.failure('operator_first_decision_timeout')
        self.assertEqual(len(self.calls),1);self.assertEqual(error.receipt['slots'][0]['transport']['receipt']['status'],'complete')

    def test_parent_controls_after_reservation_keep_identity(self):
        for signal in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            original=signal('FAKE_SECRET_CONTROL')
            self.number+=1;directory=self.root/('control-'+str(self.number))
            with patch.object(api,'_produce',side_effect=original):
                with self.assertRaises(signal) as got:
                    api.run_codex_first_decisions(catalog_path=self.catalog,catalog_sha256=H(self.catalog_bytes),response_schema_bytes=SCHEMA,
                        executable=self.exe,requested_models=['gpt-6.1-sol'],scenarios=['normal'],evidence_dir=directory)
            self.assertIs(got.exception,original)

    def test_capture_callback_swallowed_control_is_latched_outside_harness(self):
        original_prepare=api._prepare;original=KeyboardInterrupt('FAKE_SECRET_CAPTURE');reached=[]
        def prepare(*args,**kwargs):
            trial=original_prepare(*args,**kwargs);runtime=trial.runtime
            class Observer:
                def execute(self,*args,**kwargs):return runtime.execute(*args,**kwargs)
                def advance(self,*args,**kwargs):return runtime.advance(*args,**kwargs)
                def observations(self):
                    reached.append('observe')
                    if len(reached)==2:raise original
                    return runtime.observations()
            trial.runtime=Observer();return trial
        with patch.object(api,'_prepare',side_effect=prepare):
            with self.assertRaises(KeyboardInterrupt) as got:self.call()
        self.assertIs(got.exception,original);self.assertGreaterEqual(len(reached),2);self.assertEqual(self.calls,[])

    def test_final_receipt_failure_keeps_source_first_error(self):
        original_open=Path.open
        def broken(path,*args,**kwargs):
            if path.name=='batch-receipt.json' and args and 'x' in args[0]:raise OSError('FAKE_SECRET_WRITE '+str(path))
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',new=broken):
            error=self.failure('codex_cli_response_timeout','producer_error')
        self.assertIn('receipt_write_failed',error.receipt['cleanup']['secondary_errors'])

    def test_host_receipt_failure_after_valid_wire_is_failed(self):
        original_open=Path.open
        def broken(path,*args,**kwargs):
            if path.name=='batch-receipt.json' and args and 'x' in args[0]:raise OSError('FAKE_SECRET_WRITE')
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',new=broken):self.failure('operator_first_decision_retention_failed')

    def test_same_condition_context_change_blocks_second_model(self):
        original_prepare=api._prepare;made=[]
        def prepare(*args,**kwargs):
            trial=original_prepare(*args,**kwargs);made.append(trial.runtime_instance_id)
            if len(made)==2:trial.catalog['title']='changed public metadata during synthetic fault test'
            return trial
        with patch.object(api,'_prepare',side_effect=prepare):
            error=self.failure('operator_first_decision_capture_failed',requested_models=['gpt-6.1-sol','gpt-6-astra'])
        self.assertEqual(len(set(made)),2);self.assertEqual(len(self.calls),1)
        self.assertEqual(error.receipt['failure']['slot_index'],2)

    def test_returned_receipt_detached_and_input_files_unchanged(self):
        models=['gpt-6.1-sol'];scenarios=['normal'];before=C(dict(models=models,scenarios=scenarios))
        result=self.call(requested_models=models,scenarios=scenarios)
        self.assertEqual(C(dict(models=models,scenarios=scenarios)),before)
        self.assertEqual(self.catalog.read_bytes(),self.catalog_bytes)
        self.assertEqual((self.evidence/'response-schema.json').read_bytes(),SCHEMA)
        stored=(self.evidence/'batch-receipt.json').read_bytes();result['slots'].clear()
        self.assertEqual((self.evidence/'batch-receipt.json').read_bytes(),stored)
        self.assertEqual(len(json.loads(stored)['slots']),1)

    def test_review_first_failure_slot_stage_is_not_replaced_by_finalization(self):
        error=self.failure('codex_cli_response_timeout','producer_error')
        self.assertEqual(error.receipt['failure']['stage'],'producer')
        self.assertEqual(error.receipt['slots'][0]['failure']['stage'],'producer')
        self.assertEqual(error.receipt['slots'][0]['stage'],'producer')

    def test_review_malformed_nested_and_upgraded_source_receipts_are_rejected(self):
        for mode in ['bad_nested_receipt','bad_verification','bad_exit']:
            with self.subTest(mode=mode),patch.object(api,'_decode',side_effect=AssertionError('invalid receipt decoder0')):
                self.failure('operator_first_decision_retention_failed',mode)

    def test_review_slow_host_close_is_bounded_without_model_call(self):
        original_open=Path.open;entered=threading.Event();release=threading.Event()
        class Slow:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def close(self):entered.set();release.wait(5);self.stream.close()
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return Slow(stream) if path.name=='response-schema.json' and args and args[0]=='xb' else stream
        start=time.monotonic()
        try:
            with patch.object(Path,'open',new=opened):error=self.failure('operator_first_decision_cleanup_failed')
            self.assertTrue(entered.is_set());self.assertLess(time.monotonic()-start,3.5)
            self.assertFalse(error.receipt['cleanup']['host_artifacts_closed']);self.assertEqual(self.calls,[])
        finally:
            release.set()
            for thread in threading.enumerate():
                if thread.name.startswith('codex-first-close-'):thread.join(3)

    def test_review_host_write_control_survives_later_close_error(self):
        original_open=Path.open
        for signal in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            original=signal('FAKE_SECRET_HOST_WRITE')
            class Broken:
                def __init__(self,stream):self.stream=stream
                def write(self,data):raise original
                def close(self):self.stream.close();raise OSError('FAKE_SECRET_CLOSE')
            def opened(path,*args,**kwargs):
                stream=original_open(path,*args,**kwargs)
                return Broken(stream) if path.name=='response-schema.json' and args and args[0]=='xb' else stream
            with patch.object(Path,'open',new=opened):
                with self.assertRaises(signal) as got:self.call()
            self.assertIs(got.exception,original)
        self.assertEqual(self.calls,[])

    def test_review_short_read_cannot_authenticate_a_prefix_as_whole_file(self):
        original_open=Path.open
        class Short:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def read(self,*args):return self.stream.read(*args)[:-5]
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return Short(stream) if path.name=='stdout.jsonl' and args and args[0]=='rb' else stream
        with patch.object(Path,'open',new=opened),patch.object(api,'_decode',side_effect=AssertionError('partial read decoder0')):
            self.failure('operator_first_decision_retention_failed','short_artifact')

    def test_review_source_pin_is_rechecked_after_producer_before_decoder(self):
        original_read=api._read;changed=[False];reached=[];self.clock_jump=lambda:changed.__setitem__(0,True)
        def read(path,*args,**kwargs):
            data=original_read(path,*args,**kwargs)
            if changed[0] and path.name=='harness.py':reached.append('source_changed');return data+b' '
            return data
        with patch.object(api,'_read',side_effect=read),patch.object(api,'_decode',side_effect=AssertionError('changed source decoder0')):
            error=self.failure('operator_first_decision_unsupported_source')
        self.assertEqual(reached,['source_changed']);self.assertEqual(len(self.calls),1)
        self.assertEqual(error.receipt['slots'][0]['transport']['receipt']['status'],'complete')


if __name__=='__main__':
    unittest.main()
