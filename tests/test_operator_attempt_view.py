"""Authored, synthetic cases for a supplied operator attempt read view."""
import copy
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from labflow.store import canonical


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def supplied():
    sha = lambda letter: letter * 64
    context = dict(job_id='J-authored', intake_id='I-authored', revision=2,
                   analysis_context_id=sha('a'))
    analysis = {'facts': []}
    plan = {'method_id': 'conducted_synthetic', 'method_version': 1,
            'metric': 'on', 'reference_plane': 'source_output'}
    binding = dict(intake_id=context['intake_id'], revision=2,
                   analysis_context_id=context['analysis_context_id'],
                   context_sha256=digest(context), analysis_sha256=digest(analysis),
                   plan_sha256=digest(plan))
    plan_input = {'binding': binding, 'plan': plan}
    full = {**binding, 'plan_input_sha256': digest(plan_input),
            'run_id': 'operator-loop-run:authored', 'runtime_instance_id': 'runtime-authored'}
    calls = [dict(index=i, proposal={'kind': 'advance', 'ticks': 1}, before_tick=i,
                  after_tick=i + 1, receipt_status='ok', confirmed_dispatch_receipts=1,
                  cli_tool_items=0, requested_model='gpt-6.1-sol', remote_resolved_model=None)
             for i in range(1, 3)]
    execution = dict(kind='intake_plan_virtual_execution_result', status='bounded', binding=full,
                     execution=dict(mode='synthetic_only', origin_declaration='actual_cli',
                                    origin_authenticated=False, hardware_verified=False,
                                    producer_calls_started=2),
                     loop=dict(run_id=full['run_id'], status='bounded',
                               termination=dict(reason='decision_budget'),
                               steps=[dict(index=c['index'], binding=dict(run_id=full['run_id'],
                                   runtime_instance_id=full['runtime_instance_id']),
                                   dispatch=dict(receipt_status='ok', effect='changed', confirmed_receipts=1),
                                   wire=dict(proposal=c['proposal'])) for c in calls]),
                     plan_input=plan_input)
    finalizer = dict(kind='conducted_execution_result_finalizer', status='held',
                     execution_receipt=execution, result=None, artifact=None,
                     failure=dict(code='conducted_execution_result_finalizer_measurement_selection_blocked',
                                  stage='selection'), measurement_selection=dict(status='blocked',
                                  reasons=[dict(code='execution_incomplete')]),
                     verification=dict(hardware_verified=False))
    pins = {name: sha(key) for name, key in zip(
        ('evaluation', 'execution', 'finalizer', 'finished', 'handoff'), 'bcdef')}
    finished = dict(kind='same_case_manual_continuation_finished', status='failed',
                    local_model_processes=2, execution_receipt={'sha256': pins['execution']},
                    finalizer_receipt={'sha256': pins['finalizer']})
    handoff = dict(kind='codex_conducted_workflow_current_handoff',
                   execution_receipt={'sha256': pins['execution']},
                   finalizer_receipt={'sha256': pins['finalizer']},
                   current_facts_plan=dict(context=context, analysis=analysis,
                                           facts_plan={'status': 'ready_for_simulation',
                                                       'plan_input': plan_input}))
    evaluation = dict(kind='actual_ai_01_continuation_independent_evaluation',
                      binding={'execution': full}, model_calls=calls,
                      root_observation=dict(execution_status='bounded', finalization_status='held',
                          finished_status='failed', hardware_verified=False,
                          origin_authenticated=False, remote_model_identity_verified=False),
                      finalization=dict(status='held', result=None, artifact=None,
                          measurement_builder_calls=0, persistent_DRAFT_evidence=False,
                          measurement_selection_reasons=[dict(code='execution_incomplete')]),
                      journal=dict(run_id=full['run_id'], runtime_instance_id=full['runtime_instance_id'],
                                   explicit_stop_decision_count=0, terminal_reason='decision_budget',
                                   final_virtual_dut_state='transmitting'),
                      budget_and_usage=dict(cumulative_model_processes=25,
                                           maximum_cumulative_model_processes=25,
                                           remaining_model_processes=0, cost=None))
    return dict(evaluation=evaluation, execution=execution, finalizer=finalizer,
                finished=finished, handoff=handoff, source_pins=pins)


class OperatorAttemptViewTests(unittest.TestCase):
    def test_projects_bounded_held_attempt_without_result_or_private_fields(self):
        from labflow.operator_attempt_view import prepare_operator_attempt
        sources = supplied()
        sources['evaluation']['model_calls'][0]['secret_prompt'] = 'PRIVATE'
        payload = json.loads(prepare_operator_attempt(sources))
        self.assertEqual((payload['status'], payload['finalization'], payload['storage']),
                         ('bounded', 'held', 'not_created'))
        self.assertEqual(payload['binding']['job_id'], 'J-authored')
        self.assertEqual(payload['model']['process_count'], 2)
        self.assertEqual([step['action'] for step in payload['steps']], ['advance', 'advance'])
        self.assertEqual(payload['steps'][0]['receipt_status'], 'ok')
        self.assertEqual(payload['steps'][0]['effect'], 'changed')
        self.assertEqual(payload['model']['remote_resolved_model'], None)
        self.assertEqual(payload['virtual_dut_final_state'], 'transmitting')
        self.assertNotIn('PRIVATE', json.dumps(payload))
        self.assertNotIn('result', payload)
        self.assertFalse(payload['verification']['hardware_verified'])

    def test_rejects_cross_record_binding_and_false_success(self):
        from labflow.operator_attempt_view import OperatorAttemptViewError, prepare_operator_attempt
        for change in (
            lambda p: p['evaluation']['binding']['execution'].__setitem__('run_id', 'other'),
            lambda p: p['handoff']['current_facts_plan']['context'].__setitem__('job_id', 'OTHER'),
            lambda p: p['finalizer'].__setitem__('result', {'status': 'PASS'}),
            lambda p: p['finished']['execution_receipt'].__setitem__('sha256', '0' * 64),
            lambda p: p['evaluation']['model_calls'][0].__setitem__('cli_tool_items', 1),
            lambda p: p['evaluation']['model_calls'][0].__setitem__('requested_model', '<script>'),
        ):
            with self.subTest(change=change):
                packet = supplied(); change(packet)
                with self.assertRaises(OperatorAttemptViewError): prepare_operator_attempt(packet)

    def test_current_binding_requires_all_pins_and_never_promotes_stale(self):
        from labflow.operator_attempt_view import OperatorAttemptViewError, check_current_binding, prepare_operator_attempt
        packet = supplied(); prepared = json.loads(prepare_operator_attempt(packet))
        current = dict(status='available', recheck={'status': 'unchanged'},
                       current=copy.deepcopy(packet['handoff']['current_facts_plan']))
        self.assertIsNone(check_current_binding(prepared, current))
        for change in (
            lambda c: c['current']['context'].__setitem__('job_id', 'OTHER'),
            lambda c: c['current']['facts_plan']['plan_input']['binding'].__setitem__('plan_sha256', '0'*64),
            lambda c: c.__setitem__('status', 'stale'),
        ):
            with self.subTest(change=change):
                value = copy.deepcopy(current); change(value)
                with self.assertRaises(OperatorAttemptViewError): check_current_binding(prepared, value)

    def test_http_serves_only_current_supplied_cache_on_local_get(self):
        from labflow.ui_server import create_server
        from labflow import ui_server
        source = supplied()
        current = dict(status='available', recheck={'status': 'unchanged'},
                       current=copy.deepcopy(source['handoff']['current_facts_plan']))
        class Reader:
            def __init__(self, workspace): pass
            def conducted_current_facts_view(self, intake_id, selection):
                return current
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(ui_server, 'IntakeReadModel', Reader):
            server = create_server(Path(directory), port=0, operator_attempt_inputs=(source,))
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
            thread.start()
            self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(3)))
            route = '/api/intakes/I-authored/operator-attempt'
            def call(method='GET', path=route, headers=None):
                conn = http.client.HTTPConnection(*server.server_address, timeout=4)
                try:
                    conn.request(method, path, headers=headers or {})
                    response = conn.getresponse()
                    return response.status, dict(response.getheaders()), response.read()
                finally: conn.close()
            source['evaluation']['model_calls'][0]['secret_prompt'] = 'MUTATED PRIVATE'
            status, headers, body = call()
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['model']['process_count'], 2)
            self.assertNotIn(b'MUTATED PRIVATE', body)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
            self.assertEqual(call('HEAD')[0], 405)
            self.assertEqual(call('POST')[0], 405)
            self.assertEqual(call(path=route + '?path=secret')[0], 400)
            self.assertEqual(call(headers={'Origin':'https://other.test'})[0], 403)
            current['current']['context']['job_id'] = 'J-changed'
            status, _, body = call()
            self.assertEqual((status, json.loads(body)['error']['code']),
                             (503, 'operator_attempt_binding_mismatch'))
            self.assertEqual(call(path='/api/intakes/I-other/operator-attempt')[0], 503)


if __name__ == '__main__': unittest.main()
