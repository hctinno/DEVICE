"""Provider-compatible fixed operator profiles and lowering-only loop limits."""
import importlib
import copy
import hashlib
import inspect
import itertools
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from labflow.virtual_fleet import operator_response_schema as profile

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/fcc/codex_first_decision_contract.json').read_bytes())
LEGACY = CONTRACT['legacy_response_schema']['literal_utf8'].encode('utf-8')
CURRENT = profile.current_response_schema_bytes()


class SchemaCompatibilityTests(unittest.TestCase):
    def test_current_profile_uses_supported_union(self):
        helper = importlib.import_module('labflow.virtual_fleet.operator_response_schema')
        self.assertIn(b'"anyOf"', helper.current_response_schema_bytes())
        self.assertNotIn(b'"oneOf"', helper.current_response_schema_bytes())

    def test_exact_profiles_and_native_mutations(self):
        class Foreign(bytes):
            pass
        self.assertEqual(profile.SCHEMA_BYTES, 3052)
        self.assertEqual(len(CURRENT), 3052)
        self.assertEqual(hashlib.sha256(CURRENT).hexdigest(), profile.CURRENT_SCHEMA_SHA256)
        self.assertEqual(hashlib.sha256(LEGACY).hexdigest(), profile.LEGACY_SCHEMA_SHA256)
        self.assertEqual(CURRENT, CONTRACT['response_schema']['literal_utf8'].encode('utf-8'))
        self.assertTrue(profile.is_current_response_schema_bytes(CURRENT))
        self.assertTrue(profile.is_known_response_schema_bytes(CURRENT))
        self.assertTrue(profile.is_known_response_schema_bytes(LEGACY))
        self.assertFalse(profile.is_current_response_schema_bytes(LEGACY))
        for value in (None, CURRENT.decode(), Foreign(CURRENT), bytearray(CURRENT),
                      CURRENT + b'\n', CURRENT.replace(b'anyOf', b'oneOf'),
                      CURRENT.replace(b'"const": 1', b'"const": 2'),
                      json.dumps(json.loads(CURRENT)).encode()):
            if value == LEGACY and type(value) is bytes:
                continue
            self.assertFalse(profile.is_known_response_schema_bytes(value))
            self.assertFalse(profile.is_current_response_schema_bytes(value))

    def test_fixed_union_branches_are_pairwise_disjoint_and_equivalent(self):
        import jsonschema  # Existing interpreter dependency; never installed by this test.
        legacy, current = json.loads(LEGACY), json.loads(CURRENT)
        converted = copy.deepcopy(legacy)
        converted['properties']['proposal']['anyOf'] = converted['properties']['proposal'].pop('oneOf')
        self.assertEqual(converted, current)
        old = legacy['properties']['proposal']['oneOf']
        new = current['properties']['proposal']['anyOf']
        # A distinct const kind separates branches 2/3, and const device separates 0/1.
        def discriminator(branch):
            properties = branch['properties']
            return {key: properties[key]['const'] for key in ('kind', 'device_id') if key in properties}
        for left, right in itertools.combinations(old, 2):
            a, b = discriminator(left), discriminator(right)
            self.assertTrue(any(a[key] != b[key] for key in a.keys() & b.keys()))
        valid = [dict(kind='execute', device_id='dut', action='start', parameters={}),
                 dict(kind='execute', device_id='sensor', action='acquire', parameters={}),
                 dict(kind='execute', device_id='sensor', action='read', parameters={}),
                 dict(kind='advance', ticks=1)]
        valid += [dict(kind='stop', claim=claim, reason='observed') for claim in
                  ('completed', 'blocked', 'unsupported', 'failed')]
        candidates = list(valid)
        for value in valid:
            candidates.extend({k: v for k, v in value.items() if k != missing} for missing in value)
            candidates.append(dict(value, unexpected=True))
            for key in value:
                candidates.extend(dict(value, **{key: mutation}) for mutation in (None, True, 2, '', [], {}))
        for value in candidates:
            count_old = sum(jsonschema.Draft202012Validator(branch).is_valid(value) for branch in old)
            count_new = sum(jsonschema.Draft202012Validator(branch).is_valid(value) for branch in new)
            self.assertIn(count_old, (0, 1))
            self.assertEqual(count_old, count_new)
            self.assertEqual(jsonschema.Draft202012Validator({'oneOf': old}).is_valid(value),
                             jsonschema.Draft202012Validator({'anyOf': new}).is_valid(value))
        def closed_required(node):
            if isinstance(node, dict):
                if node.get('type') == 'object':
                    self.assertIs(node['additionalProperties'], False)
                    self.assertEqual(set(node['required']), set(node['properties']))
                for child in node.values():
                    closed_required(child)
            elif isinstance(node, list):
                for child in node:
                    closed_required(child)
        closed_required(current)

    def test_public_consumers_current_and_legacy_producer_zero(self):
        self.enterContext(patch.dict(sys.modules, {'tests.test_codex_cli_response':
                         importlib.import_module('test_codex_cli_response')}))
        cases = [('test_virtual_fleet_codex_first_decision', 'FirstDecisionTests',
                  'operator_first_decision_invalid_input'),
                 ('test_virtual_fleet_codex_virtual_one_action', 'OneActionTests', 'invalid_input'),
                 ('test_virtual_fleet_codex_virtual_loop', 'LoopTests', 'invalid_input')]
        for module, name, code in cases:
            with self.subTest(consumer=name):
                driver = getattr(importlib.import_module(module), name)('test_public_signature_and_exports')
                try:
                    driver.setUp()
                    if name == 'LoopTests':
                        driver.sequence = [dict(kind='stop', claim='blocked', reason='schema accepted')]
                    result = driver.call(response_schema_bytes=CURRENT)
                    self.assertIn(result['status'], ('complete', 'stopped', 'observed'))
                    if name == 'FirstDecisionTests':
                        before = len(driver.calls)
                    elif name == 'OneActionTests':
                        before = len(driver.calls)
                    else:
                        before = len(driver.driver.calls)
                    failure = driver.failure(code, response_schema_bytes=LEGACY)
                    self.assertIsNone(failure.receipt)
                    calls = driver.calls if name != 'LoopTests' else driver.driver.calls
                    self.assertEqual(len(calls), before)
                finally:
                    driver.doCleanups()


class LoweringLimitTests(unittest.TestCase):
    def driver(self, module='test_virtual_fleet_codex_virtual_loop', name='LoopTests'):
        self.enterContext(patch.dict(sys.modules, {'tests.test_codex_cli_response':
                         importlib.import_module('test_codex_cli_response')}))
        result = getattr(importlib.import_module(module), name)('test_public_signature_and_exports')
        result._testMethodName = 'compat_' + self._testMethodName
        self.addCleanup(result.doCleanups)
        result.setUp()
        return result

    def test_public_lowering_signature_defaults(self):
        for module, name in [('labflow.virtual_fleet.codex_virtual_loop', 'run_codex_virtual_loop'),
                             ('labflow.intake_plan_virtual_execution', 'run_intake_plan_virtual_execution')]:
            parameters = inspect.signature(getattr(importlib.import_module(module), name)).parameters
            for key, default in [('model_process_limit', 8), ('wall_seconds_limit', 180)]:
                self.assertEqual(parameters[key].default, default)
                self.assertEqual(parameters[key].kind, inspect.Parameter.KEYWORD_ONLY)

    def test_lower_model_limit_stops_at_n_no_n_plus_one_attempt(self):
        driver = self.driver()
        driver.sequence = [dict(kind='advance', ticks=1)]
        result = driver.call(model_process_limit=2, wall_seconds_limit=30)
        self.assertEqual(result['budget']['limits']['model_calls'], 2)
        self.assertEqual(result['budget']['limits']['wall_seconds'], 30)
        self.assertEqual(result['budget']['producer_calls_started'], 2)
        self.assertEqual(result['budget']['reserved_model_calls'], 2)
        self.assertEqual(result['budget']['model_process_attempts'], 2)
        self.assertEqual(len(driver.prompts), 2)
        self.assertEqual(result['termination']['reason'], 'decision_budget')
        for index, prompt in enumerate(driver.prompts):
            delegation = json.loads(prompt['messages'][1]['content'])['request']['user_input']['delegation']
            self.assertEqual(delegation['outer_limits']['model_calls'], 2-index)
            self.assertLessEqual(delegation['outer_limits']['wall_seconds'], 30)
        self.assertFalse(result['budget']['new_budget_granted'])
        self.assertFalse(result['budget']['reservation_refunded'])

    def test_lower_wall_positive_and_too_small_producer_zero(self):
        driver = self.driver()
        driver.sequence = [dict(kind='stop', claim='blocked', reason='bounded')]
        result = driver.call(wall_seconds_limit=20)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['budget']['limits']['wall_seconds'], 20)
        before = len(driver.prompts)
        error = driver.failure('budget_exhausted', wall_seconds_limit=5)
        self.assertEqual(error.receipt['budget']['reserved_model_calls'], 0)
        self.assertEqual(error.receipt['budget']['producer_calls_started'], 0)
        self.assertEqual(len(driver.prompts), before)

    def test_lower_deadline_post_producer_keeps_spending(self):
        driver = self.driver()
        driver.sequence = [dict(kind='advance', ticks=1)]
        api = importlib.import_module('labflow.virtual_fleet.codex_virtual_loop')
        original = api._now
        offset = [0]
        driver.after_produce = lambda: offset.__setitem__(0, 31)
        with patch.object(api, '_now', side_effect=lambda: original() + offset[0]):
            error = driver.failure('timeout', wall_seconds_limit=30)
        self.assertEqual(error.receipt['budget']['reserved_model_calls'], 1)
        self.assertEqual(error.receipt['budget']['producer_calls_started'], 1)
        self.assertEqual(len(driver.prompts), 1)

    def test_invalid_lowering_precedes_files_and_runtime(self):
        driver = self.driver()
        api = importlib.import_module('labflow.virtual_fleet.codex_virtual_loop')
        class Foreign(int):
            pass
        with patch.object(api, '_preflight', side_effect=AssertionError('FILE_ADMISSION_FORBIDDEN')) as preflight:
            for value in (True, 0, 9, 1.0, Foreign(2), None):
                driver.failure('invalid_input', model_process_limit=value)
            for value in (True, 0, -1, 181, float('nan'), float('inf'), Foreign(3), '20', 10**1000):
                driver.failure('invalid_input', wall_seconds_limit=value)
        preflight.assert_not_called()
        self.assertEqual(driver.trials, [])
        self.assertEqual(driver.driver.calls, [])

    def test_adapter_forwards_lower_limits_and_rejects_invalid_before_loop(self):
        driver = self.driver('test_intake_plan_virtual_execution', 'IntakePlanExecutionTests')
        driver.driver.sequence = [dict(kind='advance', ticks=1)]
        result = driver.call(model_process_limit=1, wall_seconds_limit=30)
        self.assertEqual(result['loop']['budget']['producer_calls_started'], 1)
        self.assertEqual(result['loop']['budget']['limits']['model_calls'], 1)
        self.assertEqual(result['loop']['budget']['limits']['wall_seconds'], 30)
        before = driver.loop.call_count
        for options in (dict(model_process_limit=True), dict(model_process_limit=9),
                        dict(wall_seconds_limit=float('inf')), dict(wall_seconds_limit=True)):
            result = driver.call(**options)
            self.assertEqual(result['status'], 'blocked')
            self.assertFalse(result['execution']['loop_entered'])
        self.assertEqual(driver.loop.call_count, before)


class ComparisonProfileTests(unittest.TestCase):
    def driver(self):
        module = importlib.import_module('test_model_comparison')
        result = module.ComparisonTests('test_operator_fixed_pair_requires_registration')
        self.addCleanup(result.doCleanups)
        result.setUp()
        return result

    def test_historical_matrix_read_preserved_but_execution_is_rejected(self):
        from labflow import model_comparison as comparison
        driver = self.driver()
        _, prompt, legacy = driver.operator_material()
        self.assertEqual(legacy, LEGACY)
        matrix = driver.operator_matrix(selection='selected')
        self.assertEqual(comparison._matrix(matrix, prompt, legacy), matrix)
        options = dict(adc_path=driver.adc, evidence_dir=driver.evidence,
                       budget_path=driver.budget, approval_path=driver.approval)
        with patch.object(comparison, '_prepare_paths', side_effect=AssertionError('FILE_ADMISSION_FORBIDDEN')) as paths:
            for callback in (lambda: comparison.run_vertex_comparison_batch(matrix, prompt, legacy, **options),
                             lambda: comparison.run_vertex_comparison_row(matrix, 0, prompt, legacy, **options)):
                with self.assertRaises(comparison.ModelComparisonError):
                    callback()
        paths.assert_not_called()
        self.assertEqual(driver.calls, [])

    def test_current_comparison_executes_public_double_without_changing_history(self):
        from labflow import model_comparison as comparison
        module = importlib.import_module('test_model_comparison')
        driver = self.driver()
        _, prompt, _ = driver.operator_material()
        matrix = comparison.build_vertex_comparison_matrix(driver.p, prompt, CURRENT,
            batch_id='compat-current-1', scenario_id='operator-synthetic-o01',
            evaluator_id='virtual-operator-wire-v1', selection='selected')
        driver.edit(driver.approval, lambda value: value.update(scenario_id='operator-synthetic-o01',
            evaluator_id='virtual-operator-wire-v1', prompt_sha256=module.sha(prompt),
            response_schema_sha256=profile.CURRENT_SCHEMA_SHA256))
        driver.response = driver.operator_response()
        output = comparison.run_vertex_comparison_batch(matrix, prompt, CURRENT,
            adc_path=driver.adc, evidence_dir=driver.evidence, budget_path=driver.budget,
            approval_path=driver.approval)
        self.assertEqual(len(driver.calls), 1)
        self.assertEqual(matrix['binding']['response_schema_sha256'], profile.CURRENT_SCHEMA_SHA256)
        self.assertIn('rows', output)


if __name__ == '__main__':
    unittest.main()
