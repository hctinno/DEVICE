"""Owner tests: genuine fresh virtual capture, fake D2, then memory-only assessment."""
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    api = importlib.import_module('labflow.virtual_fleet.codex_one_action_assessment')
except ModuleNotFoundError as error:
    if error.name != 'labflow.virtual_fleet.codex_one_action_assessment':
        raise
    api = None

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
PROOF = LOCAL / 'CODEX-ONE-ACTION-ASSESSMENT-001/implementation-v1'
KEYS = 'host_result context8 prompt response_bytes harness_report harness_events before after dispatch_receipt'.split()
CHECKS = 'input_binding wire_scope same_run_evidence single_action effect_receipt error_and_cleanup'.split()


def C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def H(data):
    return hashlib.sha256(data).hexdigest()


def admit(path, size):
    """Check the entire owner's temporary tree before opening or extending a proof."""
    path = path.resolve()
    if not path.is_relative_to(LOCAL.resolve()):
        raise AssertionError('PROOF_OUTSIDE_OWNER_LOCAL')
    files = [p for p in LOCAL.rglob('*') if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    old = path.stat().st_size if path.exists() else 0
    if len(files) + int(not path.exists()) > 512 or total - old + size > 33554432:
        raise AssertionError('PROOF_ADMISSION_EXCEEDED')


class _Writer:
    def __init__(self, handle, path):
        self.handle, self.path = handle, path

    def write(self, data):
        size = len(data.encode('utf-8')) if type(data) is str else len(data)
        admit(self.path, max(self.path.stat().st_size, self.handle.tell() + size))
        return self.handle.write(data)

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.handle.__exit__(*args)


class EffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packets = {}
        if api is None:
            return
        from tests.test_virtual_fleet_codex_virtual_one_action import OneActionTests
        original_open = Path.open

        def bounded_open(path, mode='r', *args, **kwargs):
            if any(letter in mode for letter in 'wax+'):
                admit(path, path.stat().st_size if path.exists() else 0)
                return _Writer(original_open(path, mode, *args, **kwargs), path)
            return original_open(path, mode, *args, **kwargs)

        PROOF.mkdir(parents=True, exist_ok=True)
        records = Path(tempfile.mkdtemp(prefix='fixture-packets-', dir=PROOF))
        modes = [('normal', None, {}),
                 ('read', dict(kind='execute', device_id='sensor', action='read', parameters={}), {}),
                 ('rejection', None, dict(scenario='restored_disconnect')),
                 ('stop', dict(kind='stop', claim='completed', reason='bounded claim only'), {}),
                 ('advance', dict(kind='advance', ticks=1), {}),
                 ('decoder_error', None, {}), ('source_error', None, {})]
        with patch.object(Path, 'open', bounded_open):
            for name, proposal, options in modes:
                source = OneActionTests('test_same_live_trial_one_execute_then_supervisor_stop')
                source.setUp()
                try:
                    if proposal is not None:
                        source.proposal = proposal
                    mode = {'decoder_error': 'fence', 'source_error': 'producer_error'}.get(name, 'normal')
                    try:
                        host = source.call(mode, **options)
                    except importlib.import_module('labflow.virtual_fleet.codex_virtual_one_action').CodexVirtualOneActionError as error:
                        if name not in {'read', 'rejection', 'decoder_error', 'source_error'}:
                            raise
                        host = error.receipt
                    packet = dict.fromkeys(KEYS)
                    packet['host_result'] = copy.deepcopy(host)
                    for key, filename in dict(context8='context8.json', prompt='prompt.json',
                            harness_report='harness-report.json', harness_events='harness-events.json',
                            before='before.json', after='after.json', dispatch_receipt='dispatch-receipt.json').items():
                        file = source.evidence / filename
                        packet[key] = json.loads(file.read_bytes()) if file.is_file() else None
                    raw = source.evidence / 'producer/final-text.bin'
                    packet['response_bytes'] = raw.read_bytes() if raw.is_file() else None
                    cls.packets[name] = packet
                    record = copy.deepcopy(packet)
                    record['response_bytes'] = None if packet['response_bytes'] is None else packet['response_bytes'].hex()
                    (records / (name + '.json')).write_bytes(C(dict(response_encoding='hex', packet=record,
                        preparation=dict(actual_cli=0, actual_model=0, fake_d2_calls=len(source.calls),
                                         virtual_proposal_calls=len(source.runtime_calls)))))
                finally:
                    if not source.root.resolve().is_relative_to((LOCAL / 'one-action-test-scratch').resolve()):
                        raise AssertionError('SCRATCH_CLEANUP_OUTSIDE_OWNER')
                    source.doCleanups()

    def setUp(self):
        self.assertIsNotNone(api, 'Assigned pure-memory effect assessment API is absent')

    def packet(self, name='normal'):
        return copy.deepcopy(self.packets[name])

    def assess(self, packet, **kwargs):
        before = copy.deepcopy(packet)
        result = api.assess_codex_one_action_effects(packet, **kwargs)
        self.assertEqual(packet, before)
        self.assertEqual(set(result), set('schema_version kind status verdict bindings observed_effect command_outcome first_error task_assessment checks evidence_refs verification reason_codes limits'.split()))
        self.assertEqual(result['task_assessment'], dict(status='not_evaluated', verdict=None, score=None, evaluator_called=False))
        self.assertEqual(set(result['checks']), set(CHECKS))
        self.assertTrue(result['verification']['input_values_unchanged'])
        self.assertEqual(len(result['verification']), 10)
        self.assertTrue(all(v is False for k, v in result['verification'].items()
                            if k not in {'input_values_unchanged', 'supplied_graph_consistent'}))
        self.assertLessEqual(len(C(result)), 65536)
        return result

    def error(self, packet, code='invalid_input', **kwargs):
        with self.assertRaises(api.CodexOneActionAssessmentError) as got:
            api.assess_codex_one_action_effects(packet, **kwargs)
        error = got.exception
        expected = 'codex_one_action_assessment_' + code
        self.assertEqual((error.code, str(error), error.args), (expected, expected, (expected,)))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def test_native_shape_and_resource_limits(self):
        self.assertEqual(api.__all__, ['assess_codex_one_action_effects', 'CodexOneActionAssessmentError'])
        self.assertEqual(list(inspect.signature(api.assess_codex_one_action_effects).parameters), ['packet', 'caller_error_code'])
        for bad in [None, [], {**dict.fromkeys(KEYS), 'extra': None}]:
            self.error(bad)
        class Subdict(dict):
            pass
        self.error(Subdict.fromkeys(KEYS))
        for value in [float('nan'), '\ud800', b'wrong-place', {'self': None}]:
            p = dict.fromkeys(KEYS)
            if type(value) is dict:
                value['self'] = value
            p['context8'] = value
            self.error(p)
        p = self.packet(); p['before']['tick'] = True; self.error(p)
        p = dict.fromkeys(KEYS); p['response_bytes'] = b'x' * 65537; self.error(p, 'limit_exceeded')
        p = dict.fromkeys(KEYS); p['harness_events'] = [None] * 17; self.error(p, 'limit_exceeded')
        p = dict.fromkeys(KEYS); p['context8'] = [0] * 200001; self.error(p, 'limit_exceeded')
        p = dict.fromkeys(KEYS); value = None
        for _ in range(34):
            value = [value]
        p['context8'] = value; self.error(p, 'limit_exceeded')
        p = dict.fromkeys(KEYS); p['context8'] = 'x' * 1048577; self.error(p, 'limit_exceeded')
        p = dict.fromkeys(KEYS); p['context8'] = 2**63; self.error(p, 'limit_exceeded')
        self.error(dict.fromkeys(KEYS), caller_error_code='UNTRUSTED_EXCEPTION_TEXT')

    def test_none_is_not_empty_response(self):
        a = self.assess(dict.fromkeys(KEYS))
        p = dict.fromkeys(KEYS); p['response_bytes'] = b''
        b = self.assess(p)
        self.assertEqual(a['bindings']['components']['response_bytes'], dict(present=False, bytes=0, sha256=None))
        self.assertEqual(b['bindings']['components']['response_bytes'], dict(present=True, bytes=0, sha256=H(b'')))
        self.assertNotEqual(a['bindings']['input_sha256'], b['bindings']['input_sha256'])
        self.assertEqual(b['bindings']['input_sha256'], H(C(dict(schema_version=1,
            kind='codex_one_action_assessment_inputs', components=b['bindings']['components']))))

    def test_missing_after_is_unknown_not_zero(self):
        p = self.packet(); p['after'] = None
        r = self.assess(p)
        self.assertEqual((r['status'], r['verdict'], r['observed_effect'], r['command_outcome']),
                         ('inconclusive', 'insufficient', 'unknown', 'unknown'))

    def test_caller_only_refusal_is_not_task_assessment(self):
        r = self.assess(dict.fromkeys(KEYS), caller_error_code='operator_virtual_one_action_delegation_denied')
        self.assertEqual((r['status'], r['verdict']), ('inconclusive', 'insufficient'))
        self.assertEqual(r['first_error'], dict(code='operator_virtual_one_action_delegation_denied', stage=None, source='caller'))

    def test_same_run_binding_and_causal_after(self):
        p = self.packet(); r = self.assess(p)
        self.assertEqual((r['status'], r['verdict']), ('assessed', 'consistent'))
        self.assertTrue(r['verification']['supplied_graph_consistent'])
        mapping = {e['event_id']: 'renamed.' + str(i) for i, e in enumerate(p['harness_events'], 1)}
        def rename(value):
            if type(value) is str:
                return mapping.get(value, value)
            if type(value) is list:
                return [rename(x) for x in value]
            if type(value) is dict:
                return {k: rename(v) for k, v in value.items()}
            return value
        renamed = rename(p)
        self.repin(renamed, 'harness_events'); self.repin(renamed, 'harness_report')
        r2 = self.assess(renamed)
        self.assertEqual((r2['status'], r2['verdict']), ('assessed', 'consistent'))

    @staticmethod
    def repin(p, key):
        d = p['host_result']['step']['artifacts'][key]
        body = C(p[key]); d.update(bytes=len(body), sha256=H(body))

    def test_normal_pending_changed_is_only_command_pending(self):
        r = self.assess(self.packet())
        self.assertEqual((r['command_outcome'], r['observed_effect']), ('pending', 'changed'))

    def test_read_unchanged_is_not_failure(self):
        r = self.assess(self.packet('read'))
        self.assertEqual((r['verdict'], r['command_outcome'], r['observed_effect']), ('consistent', 'rejected', 'unchanged'))

    def test_known_rejection_preserves_first_error(self):
        p = self.packet('rejection'); r = self.assess(p, caller_error_code=p['host_result']['failure']['code'])
        self.assertEqual((r['verdict'], r['command_outcome']), ('consistent', 'rejected'))
        self.assertEqual(r['first_error'], dict(**p['host_result']['failure'], source='host_result'))

    def test_valid_completed_stop_has_no_task_score(self):
        r = self.assess(self.packet('stop'))
        self.assertEqual((r['verdict'], r['command_outcome'], r['observed_effect']), ('consistent', 'not_dispatched', 'not_applicable'))
        self.assertIn('stop_not_completion', r['reason_codes'])

    def test_cross_run_or_wrong_request_is_contradictory(self):
        for key in ['run_id', 'runtime_instance_id']:
            p = self.packet(); p['harness_events'][0][key] = 'other-run'
            self.assertEqual(self.assess(p)['verdict'], 'contradictory')
        p = self.packet(); next(e for e in p['harness_events'] if e['type'] == 'receipt')['payload']['request_id'] = 'other-request'
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')
        p['after'] = None
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')

    def test_extra_intent_or_retry_is_not_repaired(self):
        for kind in ['intent', 'transport_retry']:
            p = self.packet(); event = copy.deepcopy(next(e for e in p['harness_events'] if e['type'] == 'intent'))
            event.update(type=kind, event_id='extra-event', sequence=len(p['harness_events']) + 1)
            if kind == 'transport_retry':
                event['payload'] = dict(request_id=event['payload']['request_id'], retry=1)
            p['harness_events'].append(event)
            self.assertEqual(self.assess(p)['verdict'], 'contradictory')
        p = self.packet(); p['harness_report']['usage']['elapsed_ms'] = 30001
        self.assertIn('reported_budget_violation', self.assess(p)['reason_codes'])

    def test_unresolved_prefix_stays_insufficient(self):
        p = self.packet(); p['harness_events'] = p['harness_events'][:3]
        p['after'] = p['dispatch_receipt'] = p['harness_report'] = None
        p['host_result']['step']['artifacts']['harness_events'].update(complete=False, extent='prefix')
        r = self.assess(p)
        self.assertEqual((r['status'], r['verdict'], r['observed_effect']), ('inconclusive', 'insufficient', 'unknown'))

    def test_decoder_failure_does_not_upgrade_host(self):
        for name in ['decoder_error', 'source_error']:
            p = self.packet(name)
            with patch.object(api, 'decode_operator_response', side_effect=AssertionError('DO_NOT_REDECODE_ORIGINAL_REFUSAL')) as decoder:
                r = self.assess(p)
            self.assertEqual(decoder.call_count, 0)
            self.assertEqual((r['verdict'], r['command_outcome']), ('consistent', 'not_dispatched'))

    def test_cleanup_secondary_cannot_replace_first_error(self):
        p = self.packet('rejection'); p['host_result']['cleanup']['secondary_errors'].append('host_close_failed')
        r = self.assess(p, caller_error_code='operator_virtual_one_action_cleanup_failed')
        self.assertEqual(r['first_error']['code'], 'operator_virtual_one_action_runtime_rejected')
        self.assertEqual(r['verdict'], 'contradictory')
        self.assertIn('first_error_mismatch', r['reason_codes'])

    def test_meter_declaration_is_not_fabricated(self):
        with patch('labflow.virtual_fleet.meter_recovery_assessment.assess_meter_frequency_recovery', side_effect=AssertionError('METER_EVALUATOR_FORBIDDEN')):
            self.assertEqual(self.assess(self.packet())['verdict'], 'consistent')
        p = self.packet(); p['context8']['goal']['kind'] = 'acquire_fresh_rf_sensor_meter'
        self.assertEqual(self.assess(p)['status'], 'unsupported')

    def test_sensor_trial_is_not_reconstructed(self):
        with patch('labflow.virtual_fleet.evaluation.evaluate_sensor_run', side_effect=AssertionError('SENSOR_EVALUATOR_FORBIDDEN')), patch('labflow.virtual_fleet.evaluation.prepare_sensor_trial', side_effect=AssertionError('FACTORY_FORBIDDEN')):
            self.assertEqual(self.assess(self.packet())['verdict'], 'consistent')
        p = self.packet(); p['harness_report']['assessment']['status'] = 'assessed'
        self.assertEqual(self.assess(p)['status'], 'unsupported')

    def test_no_task_evaluator_or_runtime_IO(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for target in ['builtins.open', 'pathlib.Path.open', 'subprocess.Popen', 'socket.socket.connect',
                           'socket.getaddrinfo', 'time.time', 'time.monotonic',
                           'labflow.virtual_fleet.harness.FleetHarness',
                           'labflow.virtual_fleet.evaluation.prepare_sensor_trial',
                           'labflow.virtual_fleet.evaluation.evaluate_sensor_run',
                           'labflow.virtual_fleet.meter_recovery_assessment.assess_meter_frequency_recovery']:
                stack.enter_context(patch(target, side_effect=AssertionError('EFFECT_API_MUST_BE_MEMORY_ONLY')))
            self.assertEqual(self.assess(self.packet())['verdict'], 'consistent')

    def test_input_mutation_and_control_identity(self):
        original = api.decode_operator_response
        p = self.packet()
        def mutate(*args, **kwargs):
            p['host_result']['run_id'] = 'mutated-during-call'
            return original(*args, **kwargs)
        with patch.object(api, 'decode_operator_response', side_effect=mutate):
            self.error(p, 'internal_error')
        for control in [KeyboardInterrupt('CONTROL'), SystemExit(7), GeneratorExit('CONTROL'), MemoryError('CONTROL')]:
            with patch.object(api, 'decode_operator_response', side_effect=control):
                with self.assertRaises(type(control)) as got:
                    api.assess_codex_one_action_effects(self.packet())
            self.assertIs(got.exception, control)
        p = self.packet(); r = self.assess(p)
        r['bindings']['operator_binding']['run_id'] = 'output-mutation'
        self.assertNotEqual(p['host_result']['step']['binding']['run_id'], 'output-mutation')

    def test_advance_and_artifact_provenance_are_bounded(self):
        r = self.assess(self.packet('advance'))
        self.assertEqual((r['verdict'], r['command_outcome'], r['observed_effect']), ('consistent', 'accepted', 'changed'))
        p = self.packet(); p['host_result']['step']['artifacts']['after']['sha256'] = '0' * 64
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')
        p = self.packet(); p['host_result']['step']['artifacts']['after'].update(complete=False, extent='prefix')
        self.assertEqual(self.assess(p)['verdict'], 'insufficient')

    def test_original_shapes_reject_nested_unknowns_and_bool_numbers(self):
        p = self.packet(); p['host_result']['step']['wire']['extra'] = None
        self.error(p)
        p = self.packet(); p['host_result']['step']['transport']['receipt']['lifecycle']['tool_items'] = False
        self.error(p)
        class Key(str):
            pass
        p = dict.fromkeys(KEYS); p[Key('host_result')] = p.pop('host_result')
        self.error(p)
        p = self.packet(); p['harness_report']['policy']['id'] = []
        self.error(p)

    def test_reported_extra_dispatch_is_contradictory_without_events(self):
        p = self.packet(); p['harness_events'] = None
        p['host_result']['execution']['model_proposal_dispatches'] = 2
        r = self.assess(p)
        self.assertEqual(r['verdict'], 'contradictory')
        self.assertIn('single_action_violation', r['reason_codes'])

    def test_original_unknown_producer_usage_stays_unknown(self):
        p = self.packet(); t = p['host_result']['step']['transport']
        t['receipt']['usage'] = None; t['receipt_sha256'] = H(C(t['receipt']))
        self.assertEqual(self.assess(p)['verdict'], 'consistent')
        p = self.packet(); p['host_result']['step']['transport']['exchange_ref'] = 'codex-cli-exchange:' + '0' * 32
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')

    def test_host_terminal_status_is_bound_to_original_failure(self):
        p = self.packet('rejection'); p['host_result']['status'] = 'observed'
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')
        p = self.packet('source_error'); p['host_result']['step']['transport']['receipt']['failure']['code'] = 'codex_cli_response_spawn_failed'
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')

    def test_rejected_diagnostic_change_does_not_require_revision_increment(self):
        p = self.packet('read'); after = p['after']
        after['devices']['sensor']['values']['diagnostic_observed'] = True
        p['host_result']['step']['after']['sha256'] = H(C(after))
        p['host_result']['step']['dispatch']['effect'] = 'changed'
        next(e for e in p['harness_events'] if e['type'] == 'observation' and 'cause_request_id' in e['payload'])['payload']['observation'] = copy.deepcopy(after)
        self.repin(p, 'after'); self.repin(p, 'harness_events')
        r = self.assess(p)
        self.assertEqual((r['verdict'], r['command_outcome'], r['observed_effect']), ('consistent', 'rejected', 'changed'))

    def test_accepted_read_can_be_unchanged(self):
        p = self.packet('read'); h = p['host_result']
        h['failure'] = h['step']['failure'] = None; h['status'] = 'observed'; h['step']['stage'] = 'finalize'
        h['step']['dispatch']['receipt_status'] = 'ok'; h['verification']['source_inputs_unchanged'] = True
        p['dispatch_receipt']['status'] = 'ok'
        next(e for e in p['harness_events'] if e['type'] == 'receipt')['payload']['result']['status'] = 'ok'
        self.repin(p, 'dispatch_receipt'); self.repin(p, 'harness_events')
        r = self.assess(p)
        self.assertEqual((r['verdict'], r['command_outcome'], r['observed_effect']), ('consistent', 'accepted', 'unchanged'))

    def test_confirmed_first_error_conflict_survives_missing_events(self):
        p = self.packet('rejection'); p['harness_events'] = None
        r = self.assess(p, caller_error_code='operator_virtual_one_action_cleanup_failed')
        self.assertEqual(r['verdict'], 'contradictory')
        self.assertEqual(r['first_error']['code'], 'operator_virtual_one_action_runtime_rejected')
        self.assertIn('first_error_mismatch', r['reason_codes'])
        p = self.packet('source_error')
        next(e for e in p['harness_events'] if e['type'] == 'error')['payload']['code'] = 'unknown_harness_error'
        self.repin(p, 'harness_events')
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')

    def test_malformed_native_field_and_embedded_prompt_are_fixed(self):
        p = self.packet('source_error')
        p['host_result']['step']['transport']['receipt']['failure']['code'] = []
        self.error(p)
        p = self.packet()
        p['prompt']['messages'][1]['content'] = C(dict(request=dict(user_input=dict(public_context=dict(goal=[]))))).decode()
        self.assertEqual(self.assess(p)['verdict'], 'contradictory')


if __name__ == '__main__':
    unittest.main()
