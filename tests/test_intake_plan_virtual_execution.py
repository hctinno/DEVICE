"""Authored native intake DTO + genuine D1/loop; actual provider and Store0."""
import copy
import importlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    api = importlib.import_module('labflow.intake_plan_virtual_execution')
except ModuleNotFoundError as error:
    if error.name != 'labflow.intake_plan_virtual_execution':
        raise
    api = None

from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input
from test_intake_conducted_twin_plan import fixture, pdf_source
from test_virtual_fleet_codex_virtual_loop import C, H


class IntakePlanExecutionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, 'Assigned intake plan virtual execution API is absent')
        from test_virtual_fleet_codex_virtual_loop import LoopTests
        self.driver = LoopTests('test_public_signature_and_exports')
        self.driver._testMethodName = 'adapter_' + self._testMethodName
        self.addCleanup(self.driver.doCleanups)
        self.driver.setUp()
        self.context, self.analysis, self.plan_options = fixture()
        self.plan = self.build_plan()
        self.assertEqual(self.plan['status'], 'ready_for_simulation')
        self.loop_results = []
        self.loop_files = []
        self.calls = 0
        def run(**options):
            result = self.driver.call(**options)
            self.loop_results.append(result)
            folder = options['evidence_dir']
            self.loop_files.append({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()})
            return result
        self.loop = self.enterContext(patch.object(api, '_run_loop', side_effect=run))

    def build_plan(self):
        return build_conducted_twin_plan_input(self.context, self.analysis, **self.plan_options)

    def call(self, **changes):
        self.calls += 1
        context = changes.pop('context', self.context)
        analysis = changes.pop('analysis', self.analysis)
        plan = changes.pop('plan_input', self.plan)
        plan_pin = changes.pop('expected_plan_input_sha256') if 'expected_plan_input_sha256' in changes else H(C(plan))
        options = dict(self.driver.options, expected_revision=self.plan_options['expected_revision'],
            expected_context_sha256=self.plan_options['expected_context_sha256'],
            expected_plan_input_sha256=plan_pin,
            evidence_dir=self.driver.driver.root / ('adapter-' + str(self.calls)))
        options.update(changes)
        return api.run_intake_plan_virtual_execution(context, analysis, plan, **options)

    def shape(self, result):
        self.assertEqual(set(result), set('schema_version kind status failure binding plan_input loop execution artifacts verification'.split()))
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['kind'], 'intake_plan_virtual_execution_result')
        self.assertFalse(result['execution']['origin_authenticated'])
        self.assertIsNone(result['execution']['ai_model_called'])
        self.assertFalse(result['execution']['intake_native_host_connected'])
        self.assertFalse(result['artifacts']['outer_receipt_retained'])
        for field in ('source_bytes_reopened', 'current_store_revision_observed', 'execution_authority_verified',
                      'full_task_verified', 'quantity_basis_verified'):
            self.assertFalse(result['verification'][field])

    def blocked(self, **changes):
        result = self.call(**changes); self.shape(result)
        self.assertEqual(result['status'], 'blocked')
        self.assertIsNone(result['loop'])
        self.assertFalse(result['execution']['loop_entered'])
        self.assertEqual(result['execution']['trial_factory_calls'], 0)
        self.assertEqual(result['execution']['producer_calls_started'], 0)
        self.assertEqual(self.loop.call_count, 0)
        self.assertEqual(self.driver.trials, []); self.assertEqual(self.driver.driver.calls, [])
        return result

    def test_public_signature_and_exports(self):
        self.assertEqual(api.__all__, ['run_intake_plan_virtual_execution', 'IntakePlanVirtualExecutionError'])
        signature = inspect.signature(api.run_intake_plan_virtual_execution)
        expected = 'context analysis plan_input expected_revision expected_context_sha256 expected_plan_input_sha256 catalog_path catalog_sha256 response_schema_bytes executable requested_model scenario evidence_dir execution_origin cancel_event quantity'.split()
        self.assertEqual(list(signature.parameters), expected)
        self.assertTrue(all(p.kind == inspect.Parameter.KEYWORD_ONLY for p in list(signature.parameters.values())[3:]))
        self.assertTrue(issubclass(api.IntakePlanVirtualExecutionError, RuntimeError))

    def test_original_blocked_withheld_values_never_enter_loop(self):
        del self.plan_options['basis']['frequency_hz']
        self.plan = self.build_plan(); original = C(self.plan)
        self.assertEqual(self.plan['status'], 'blocked')
        self.assertIsNone(self.plan['plan']['source_settings']['frequency_hz'])
        with patch.object(Path, 'open', side_effect=AssertionError('BLOCKED_NATIVE_IO_FORBIDDEN')):
            result = self.blocked()
        self.assertEqual(C(result['plan_input']), original)
        self.assertEqual(C(self.plan), original)
        self.assertFalse(result['verification']['ready_plan_revalidated'])

    def test_changed_binding_or_pins_never_enter_loop(self):
        changed = copy.deepcopy(self.context); changed['revision'] = 2
        cases = [dict(expected_revision=True), dict(expected_revision=2),
                 dict(expected_context_sha256='0'*64), dict(expected_plan_input_sha256='0'*64),
                 dict(expected_plan_input_sha256=H(C(self.plan)).upper()),
                 dict(context=changed, expected_revision=2, expected_context_sha256=H(C(changed)))]
        changed_analysis = copy.deepcopy(self.analysis)
        changed_analysis['facts'][0]['value'] = 'different authored product'
        cases.append(dict(analysis=changed_analysis))
        for case in cases:
            with self.subTest(fields=sorted(case)):
                self.blocked(**case)

    def test_ready_requires_original_genuine_D1_output(self):
        variants = []
        changed = copy.deepcopy(self.plan); changed['verification']['execution_authority'] = True; variants.append(changed)
        changed = copy.deepcopy(self.plan); changed['plan']['source_settings']['power_dbm'] = -9; variants.append(changed)
        changed = copy.deepcopy(self.plan); changed['plan']['source_settings']['power_dbm'] = -7; variants.append(changed)
        changed = copy.deepcopy(self.plan); changed['gaps'].append(dict(code='invented', field='input', provided=None, blocking=False)); variants.append(changed)
        changed = copy.deepcopy(self.plan); changed['extra'] = 'must not be dropped'; variants.append(changed)
        for value in variants:
            with self.subTest(fields=sorted(value)):
                result = self.blocked(plan_input=value, expected_plan_input_sha256=H(C(value)))
                self.assertEqual(C(result['plan_input']), C(value))

    def test_non_synthetic_and_unsupported_method_are_blocked(self):
        changed = copy.deepcopy(self.context); changed['synthetic'] = False
        self.blocked(context=changed, expected_context_sha256=H(C(changed)))
        for field, value in [('method_id','fcc-approved'), ('method_version',True), ('metric','reported_peak'),
                             ('reference_plane','sensor_input')]:
            plan = copy.deepcopy(self.plan); plan['plan'][field] = value
            plan['binding']['plan_sha256'] = H(C(plan['plan']))
            self.blocked(plan_input=plan, expected_plan_input_sha256=H(C(plan)))

    def test_native_and_bounded_inputs_cannot_launch(self):
        class DictSubclass(dict):
            pass
        cycle = []; cycle.append(cycle)
        variants = [True, 'serialized DTO is not native input', DictSubclass(self.plan), cycle,
                    {**self.plan, 'extra': float('nan')}, {**self.plan, 'extra': 'x' * (8*1024*1024)}]
        for value in variants:
            with self.subTest(value_type=type(value).__name__):
                self.blocked(plan_input=value, expected_plan_input_sha256=H(b'fixed rejected-input pin'))
        for origin in (True, None, 'UNRECOGNIZED_ORIGIN'):
            result = self.blocked(execution_origin=origin)
            self.assertIsNone(result['execution']['origin_declaration'])

    def test_ready_uses_one_genuine_trial_and_preserves_loop(self):
        before = C([self.context, self.analysis, self.plan])
        result = self.call(); self.shape(result)
        self.assertEqual(C([self.context, self.analysis, self.plan]), before)
        self.assertEqual(self.loop.call_count, 1)
        self.assertEqual(len(self.driver.trials), 1)
        self.assertEqual(C(self.loop.call_args.kwargs['source_settings']), C(self.plan['plan']['source_settings']))
        self.assertEqual(C(result['loop']), C(self.loop_results[0]))
        self.assertTrue(result['loop']['evidence_assessment']['goal_observed'])
        self.assertEqual(result['status'], result['loop']['status'])
        for field, value in self.plan['binding'].items():self.assertEqual(result['binding'][field], value)
        self.assertEqual(result['binding']['plan_input_sha256'], H(C(self.plan)))
        self.assertEqual(result['binding']['run_id'], result['loop']['run_id'])
        self.assertEqual(result['binding']['runtime_instance_id'], result['loop']['execution']['runtime_instance_id'])
        self.assertTrue(result['verification']['ready_plan_revalidated'])
        self.assertTrue(result['verification']['setup_journal_connected'])
        folder = self.loop.call_args.kwargs['evidence_dir']
        self.assertEqual({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}, self.loop_files[0])

    def test_schema2_cited_basis_is_preserved_in_original_units(self):
        pdf_source(self.context, self.analysis, self.plan_options)
        self.plan = self.build_plan(); original = C(self.plan)
        self.driver.sequence = [dict(kind='stop', claim='blocked', reason='cited source only')]
        result = self.call(); self.shape(result)
        self.assertEqual(self.analysis['schema_version'], 2)
        self.assertEqual(C(result['plan_input']), original)
        self.assertEqual(result['plan_input']['plan']['basis_refs']['frequency_hz']['unit'], 'MHz')
        self.assertEqual(self.loop.call_args.kwargs['source_settings']['frequency_hz'], self.plan['plan']['source_settings']['frequency_hz'])

    def test_noncompletion_and_detached_receipts_are_preserved(self):
        self.plan_options['method']['metric'] = 'time'; self.plan = self.build_plan()
        original = C(self.plan)
        self.driver.sequence = [dict(kind='stop', claim='completed', reason='claim without fresh measurement')]
        result = self.call(); self.shape(result)
        self.assertEqual(result['status'], 'stopped')
        self.assertFalse(result['loop']['evidence_assessment']['goal_observed'])
        self.assertEqual(result['plan_input']['plan']['metric'], 'time')
        self.assertEqual(C(result['loop']), C(self.loop_results[0]))
        self.assertIsNone(result['loop']['evidence_assessment']['score'])
        result['plan_input']['plan']['source_settings']['power_dbm'] = 500
        result['loop']['budget']['reserved_model_calls'] = 999
        self.assertEqual(C(self.plan), original)
        self.assertNotEqual(self.loop_results[0]['budget']['reserved_model_calls'], 999)

    def test_original_producer_failure_code_receipt_and_consumption(self):
        self.driver.producer_mode = 'nonzero'
        with self.assertRaises(api.IntakePlanVirtualExecutionError) as got:self.call()
        error = got.exception
        self.assertEqual(error.code, 'codex_cli_response_process_failed')
        self.assertEqual((str(error), error.args), (error.code, (error.code,)))
        self.assertIsNone(error.__cause__); self.assertIsNone(error.__context__)
        self.shape(error.receipt)
        self.assertEqual(error.receipt['loop']['failure']['code'], error.code)
        self.assertEqual(error.receipt['loop']['budget']['reserved_model_calls'], 1)
        self.assertFalse(error.receipt['loop']['budget']['reservation_refunded'])
        self.assertEqual(self.loop.call_count, 1)

    def test_control_identity_without_automatic_resume(self):
        for value in [KeyboardInterrupt('CONTROL'), SystemExit(7), GeneratorExit('CONTROL'), MemoryError('CONTROL')]:
            self.loop.side_effect = value
            with self.assertRaises(type(value)) as got:self.call()
            self.assertIs(got.exception, value)
        self.assertEqual(self.loop.call_count, 4)
        self.assertEqual(self.driver.trials, [])

    def test_unknown_loop_output_and_exception_stay_unknown(self):
        for value in [None, {}, {'kind':'codex_virtual_loop_result','status':'stopped'}, OSError('FAKE_SECRET_IO')]:
            self.loop.side_effect = value if isinstance(value, BaseException) else None
            self.loop.return_value = value
            with self.assertRaises(api.IntakePlanVirtualExecutionError) as got:self.call()
            self.assertNotIn('FAKE_SECRET', str(got.exception))
            result = got.exception.receipt; self.shape(result)
            self.assertEqual(result['status'], 'failed')
            self.assertTrue(result['execution']['loop_entered'])
            self.assertIsNone(result['execution']['trial_factory_calls'])
            self.assertIsNone(result['execution']['producer_calls_started'])

    def test_caller_quantity_is_forwarded_unchanged(self):
        quantity = dict(metric='peak', reference_plane='source_output', loss_compensation_applied=True, loss_compensation_sign=False)
        self.driver.sequence = [dict(kind='stop', claim='blocked', reason='explicit quantity')]
        result = self.call(quantity=quantity); self.shape(result)
        self.assertEqual(C(self.loop.call_args.kwargs['plan_binding']), C(self.plan['binding']))
        self.assertEqual(C(self.loop.call_args.kwargs['quantity']), C(quantity))
        self.assertEqual(C(result['loop']['execution']['host_evidence']['quantity']), C(quantity))
        self.assertTrue(result['verification']['setup_journal_connected'])
        self.assertFalse(result['verification']['quantity_basis_verified'])

    def test_quantity_omission_stays_missing_in_actual_journal(self):
        from labflow.virtual_fleet.journal import read_operator_journal
        self.driver.sequence = [dict(kind='stop', claim='blocked', reason='no quantity supplied')]
        result = self.call(); self.shape(result)
        path = self.loop.call_args.kwargs['evidence_dir'] / 'operator-journal.jsonl'
        journal = read_operator_journal(path)
        self.assertNotIn('quantity', journal['header']['provenance'])
        self.assertIsNone(result['loop']['execution']['host_evidence']['quantity'])


if __name__ == '__main__':
    unittest.main()
