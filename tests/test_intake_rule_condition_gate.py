"""New authored arithmetic/label examples; no private rules or actual approvals."""
import copy
import hashlib
import importlib
import importlib.util
import json
import socket
import sqlite3
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.store import canonical
from test_intake_facts_to_conducted_plan import authored


CONTEXT_FIELDS = (
    'current_validity_approved', 'case_applicability_approved', 'metric_method_approved',
    'reference_plane_verified', 'correction_ledger_verified', 'conditional_limit_resolved',
    'uncertainty_decision_rule_approved', 'independent_holdout_available',
)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fixture():
    context, analysis, options = authored()
    values = {'mode': ('LAB-C', 'label'), 'level': (17, 'mV'), 'enabled': (True, 'boolean')}
    values.update({name: (True, 'boolean') for name in CONTEXT_FIELDS})
    document = context['documents'][0]
    first_line = len(document['text'].splitlines()) + 1
    quotes = {name: canonical(dict(field=name, value=value, unit=unit)) for name, (value, unit) in values.items()}
    document['text'] += '\n'.join(quotes.values()) + '\n'
    document.update(bytes=len(document['text'].encode('utf-8')), sha256=sha(document['text']))
    for fact in analysis['facts']:
        for ref in fact['evidence']:
            ref['sha256'] = document['sha256']
    entries = {}
    for offset, (name, (value, unit)) in enumerate(values.items()):
        ref = dict(path=document['path'], sha256=document['sha256'], line_start=first_line+offset,
                   line_end=first_line+offset, quote=quotes[name], role='product')
        entries[name] = dict(value=value, unit=unit, status='explicit', evidence=[ref])
    options['expected_context_sha256'] = sha(canonical(context))
    wrapper = build_conducted_plan_from_intake_facts(context, analysis, **options)
    payload = dict(rule_id='authored-branch', declared_predicate=dict(operator='all', operands=[
        dict(operator='eq', input='mode', value='LAB-C'),
        dict(operator='in', input='mode', value=['LAB-B', 'LAB-C']),
        dict(operator='gt', input='level', value=12),
        dict(operator='gte', input='level', value=17),
        dict(operator='eq', input='enabled', value=True),
    ]), input_types=dict(mode='string', level='number', enabled='boolean'),
        units=dict(mode='label', level='mV', enabled='boolean'))
    text = canonical(dict(rules=[payload]))
    source = dict(source_id='authored-rule-source', text=text, sha256=sha(text))
    rule = dict(payload, source_ref=dict(source_id=source['source_id'], sha256=source['sha256'], rule_index=0))
    args = dict(context=context, analysis=analysis, expected_revision=options['expected_revision'],
        expected_context_sha256=options['expected_context_sha256'], rules=[rule], rule_sources=[source],
        inputs={name: entries[name] for name in ('mode', 'level', 'enabled')},
        execution_context={name: entries[name] for name in CONTEXT_FIELDS})
    return wrapper, copy.deepcopy(wrapper['plan_input']), args


class RuleConditionGateTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.wrapper, self.current, self.args = fixture()

    def api(self):
        name = 'labflow.intake_rule_condition_gate'
        self.assertIsNotNone(importlib.util.find_spec(name), 'assigned bounded rule gate is absent')
        return importlib.import_module(name).evaluate_intake_rule_conditions

    def build(self):
        return self.api()(self.wrapper, self.current, **self.args)

    def refresh_plan(self):
        self.args['expected_context_sha256'] = sha(canonical(self.args['context']))
        method = {k: self.current['plan'][k] for k in ('method_id', 'method_version', 'metric', 'reference_plane')}
        self.wrapper = build_conducted_plan_from_intake_facts(self.args['context'], self.args['analysis'],
            expected_revision=self.args['expected_revision'], expected_context_sha256=self.args['expected_context_sha256'],
            method=method)
        self.current = copy.deepcopy(self.wrapper['plan_input'])

    def entry(self, name, value):
        container = self.args['inputs'] if name in self.args['inputs'] else self.args['execution_context']
        item = container[name]
        old = item['evidence'][0]['quote']
        item['value'] = value
        quote = canonical(dict(field=name, value=value, unit=item['unit']))
        document = self.args['context']['documents'][0]
        document['text'] = document['text'].replace(old, quote)
        document.update(bytes=len(document['text'].encode('utf-8')), sha256=sha(document['text']))
        item['evidence'][0]['quote'] = quote
        for fact in self.args['analysis']['facts']:
            for ref in fact['evidence']:
                ref['sha256'] = document['sha256']
        for entries in (self.args['inputs'], self.args['execution_context']):
            for record in entries.values():
                for ref in record['evidence']:
                    ref['sha256'] = document['sha256']
        self.refresh_plan()

    def rule(self, predicate, kinds=None, units=None):
        rule = self.args['rules'][0]
        rule['declared_predicate'] = predicate
        if kinds is not None:
            rule['input_types'] = kinds
        if units is not None:
            rule['units'] = units
        self.resign()

    def resign(self):
        rule = self.args['rules'][0]
        payload = {k: rule[k] for k in ('rule_id', 'declared_predicate', 'input_types', 'units')}
        text = canonical(dict(rules=[payload]))
        self.args['rule_sources'][0].update(text=text, sha256=sha(text))
        rule['source_ref']['sha256'] = sha(text)

    def held(self, field=None):
        result = self.build()
        self.assertEqual(result['status'], 'HOLD')
        self.assertIsNone(result['normative_verdict'])
        self.assertTrue(result['questions'])
        if field is not None:
            self.assertIn(field, [q['field'] for q in result['questions']])
        for key in ('execution_authority', 'worker_generation_authority', 'physical_permission'):
            self.assertIs(result['verification'][key], False)
        return result

    def test_authored_five_operators_select_review_without_any_execution_or_verdict(self):
        before = copy.deepcopy((self.wrapper, self.current, self.args))
        result = self.build()
        self.assertEqual(result['status'], 'REVIEW_RULE_BRANCH')
        self.assertIs(result['rule_results'][0]['predicate_value'], True)
        self.assertEqual(result['questions'], [])
        self.assertIsNone(result['normative_verdict'])
        self.assertIs(result['verification']['execution_authority'], False)
        self.assertEqual(result['snapshots']['intake_plan'], self.wrapper)
        self.assertEqual(result['snapshots']['current_plan'], self.current)
        self.assertEqual((self.wrapper, self.current, self.args), before)

    def test_strict_and_inclusive_numeric_boundaries_and_native_zero(self):
        for operator, threshold, expected in [('gt', 17, False), ('gte', 17, True), ('eq', 17.0, True), ('gt', 16, True)]:
            with self.subTest(operator=operator, threshold=threshold):
                self.rule(dict(operator=operator, input='level', value=threshold), dict(level='number'), dict(level='mV'))
                result = self.build()
                self.assertIs(result['rule_results'][0]['predicate_value'], expected)
                self.assertEqual(result['status'], 'REVIEW_RULE_BRANCH' if expected else 'NOT_SELECTED')
        self.entry('level', 0)
        self.rule(dict(operator='gte', input='level', value=0), dict(level='number'), dict(level='mV'))
        self.assertEqual(self.build()['status'], 'REVIEW_RULE_BRANCH')

    def test_native_false_is_a_known_boolean_input_and_membership_is_exact(self):
        self.entry('enabled', False)
        self.rule(dict(operator='in', input='enabled', value=[False]), dict(enabled='boolean'), dict(enabled='boolean'))
        self.assertEqual(self.build()['status'], 'REVIEW_RULE_BRANCH')
        self.rule(dict(operator='in', input='mode', value=['LAB-A', 'LAB-B']), dict(mode='string'), dict(mode='label'))
        self.assertEqual(self.build()['status'], 'NOT_SELECTED')

    def test_missing_dominates_a_false_other_operand_and_asks_only_missing_input(self):
        self.args['rules'][0]['declared_predicate']['operands'][2]['value'] = 18
        self.resign()
        self.args['inputs']['enabled'] = None
        result = self.held('inputs.enabled')
        self.assertIsNone(result['rule_results'][0]['predicate_value'])
        self.assertEqual(len(result['questions']), 1)

    def test_missing_execution_context_even_with_true_predicate_is_held(self):
        self.args['execution_context'] = {name: None for name in CONTEXT_FIELDS}
        result = self.held()
        self.assertIs(result['rule_results'][0]['predicate_value'], True)
        self.assertEqual({q['field'] for q in result['questions']}, {'execution_context.'+name for name in CONTEXT_FIELDS})
        self.assertEqual(len(result['questions']), 8)

    def test_explicit_false_context_is_unconfirmed_and_never_a_grant(self):
        self.entry('current_validity_approved', False)
        result = self.held('execution_context.current_validity_approved')
        self.assertEqual(result['questions'][0]['reason'], 'execution_context_unconfirmed')
        self.assertEqual(result['verification']['approval'], 'caller_snapshot_only')

    def test_bare_approval_boolean_and_unknown_context_keys_do_not_authenticate(self):
        self.args['execution_context']['current_validity_approved'] = True
        self.held('execution_context.current_validity_approved')
        self.args['execution_context']['execution_authority'] = True
        self.held('execution_context')

    def test_conflicting_and_uncertain_inputs_are_preserved_and_held(self):
        for status in ('conflict', 'uncertain'):
            with self.subTest(status=status):
                self.args['inputs']['level']['status'] = status
                result = self.held('inputs.level')
                self.assertEqual(result['snapshots']['inputs']['level']['status'], status)
                self.assertEqual(len(result['questions']), 1)

    def test_bool_is_not_a_number_and_numeric_strings_are_not_coerced(self):
        for value in (True, '17'):
            with self.subTest(value=value):
                self.args['inputs']['level']['value'] = value
                result = self.held('inputs.level')
                self.assertEqual(result['questions'][0]['reason'], 'input_type_or_unit_mismatch')

    def test_units_are_required_exact_and_never_implicitly_converted(self):
        for unit in (None, '', 'V'):
            with self.subTest(unit=unit):
                self.args['inputs']['level']['unit'] = unit
                self.held('inputs.level')

    def test_bad_current_citation_sha_line_and_literal_are_not_evidence(self):
        original = copy.deepcopy(self.args['inputs']['level'])
        for change in ('sha', 'line', 'literal', 'empty'):
            with self.subTest(change=change):
                self.args['inputs']['level'] = copy.deepcopy(original)
                item = self.args['inputs']['level']
                if change == 'sha': item['evidence'][0]['sha256'] = '0'*64
                if change == 'line': item['evidence'][0].update(line_start=1, line_end=1)
                if change == 'literal': item['value'] = 18
                if change == 'empty': item['evidence'] = []
                result = self.held('inputs.level')
                self.assertEqual(result['questions'][0]['reason'], 'input_evidence_invalid')

    def test_source_snapshot_hash_and_rule_index_must_match(self):
        self.args['rule_sources'][0]['sha256'] = '0'*64
        self.held('rule_sources.0')
        self.wrapper, self.current, self.args = fixture()
        for index in (-1, True, 9):
            with self.subTest(index=index):
                self.args['rules'][0]['source_ref']['rule_index'] = index
                self.held('rules.0.source_ref')

    def test_source_binds_predicate_type_unit_and_rule_identity_not_just_sha(self):
        original = copy.deepcopy(self.args['rules'][0])
        for change in ('predicate', 'type', 'unit', 'id'):
            with self.subTest(change=change):
                self.args['rules'][0] = copy.deepcopy(original)
                rule = self.args['rules'][0]
                if change == 'predicate': rule['declared_predicate']['operands'][2]['value'] = 13
                if change == 'type': rule['input_types']['level'] = 'string'
                if change == 'unit': rule['units']['level'] = 'V'
                if change == 'id': rule['rule_id'] = 'different-authored-rule'
                self.held('rules.0.source_ref')

    def test_duplicate_json_keys_in_source_fail_closed(self):
        text = self.args['rule_sources'][0]['text'].replace('{"rules":', '{"rules":[],"rules":', 1)
        self.args['rule_sources'][0].update(text=text, sha256=sha(text))
        self.args['rules'][0]['source_ref']['sha256'] = sha(text)
        self.held('rule_sources.0')

    def test_other_revision_or_context_hash_and_recomputed_tampered_plan_are_held(self):
        self.args['expected_revision'] += 1
        self.held('current_plan')
        self.wrapper, self.current, self.args = fixture()
        self.args['expected_context_sha256'] = '0'*64
        self.held('current_plan')
        self.wrapper, self.current, self.args = fixture()
        self.current['plan']['source_settings']['power_dbm'] = -8
        self.current['binding']['plan_sha256'] = sha(canonical(self.current['plan']))
        self.wrapper['plan_input'] = copy.deepcopy(self.current)
        self.held('current_plan')

    def test_original_expected_pins_remain_visible_when_current_binding_is_rejected(self):
        self.args['expected_revision'] += 1
        self.args['expected_context_sha256'] = '0'*64
        result = self.held('current_plan')
        self.assertEqual(result['snapshots']['expected_revision'], self.args['expected_revision'])
        self.assertEqual(result['snapshots']['expected_context_sha256'], '0'*64)

    def test_unresolved_parent_questions_and_null_method_assessment_survive_review(self):
        self.args['analysis']['facts'][-1]['value'] = self.args['analysis']['facts'][-1]['value'].replace('duty_cycle: 50 %\n', '')
        self.refresh_plan()
        self.assertEqual(self.wrapper['status'], 'blocked')
        self.assertTrue(self.wrapper['questions'])
        result = self.build()
        self.assertEqual(result['status'], 'REVIEW_RULE_BRANCH')
        self.assertEqual(result['snapshots']['intake_plan'], self.wrapper)
        plan = result['snapshots']['current_plan']['plan']
        self.assertIsNone(plan['numeric_limit_dbm'])
        self.assertIsNone(plan['uncertainty_db'])
        self.assertEqual(plan['assessment'], 'not_assessed')
        self.assertIsNone(plan['source_settings']['duty_cycle'])

    def test_unsupported_operator_typed_literal_and_empty_all_are_held(self):
        cases = [dict(operator='or', operands=[]), dict(operator='all', operands=[]),
                 dict(operator='gt', input='level', value=True), dict(operator='in', input='level', value=[17, '17'])]
        for predicate in cases:
            with self.subTest(operator=predicate['operator']):
                self.rule(predicate, dict(level='number'), dict(level='mV'))
                self.held('rules.0.declared_predicate')

    def test_rules_ast_depth_operands_and_membership_are_bounded(self):
        self.args['rules'] *= 7
        self.held('rules')
        self.wrapper, self.current, self.args = fixture()
        leaf = dict(operator='eq', input='level', value=17)
        deep = leaf
        for _ in range(10): deep = dict(operator='all', operands=[deep])
        for predicate in (deep, dict(operator='all', operands=[leaf]*9), dict(operator='in', input='level', value=list(range(17)))):
            self.rule(predicate, dict(level='number'), dict(level='mV'))
            self.held('rules.0.declared_predicate')

    def test_duplicate_rules_and_shared_missing_field_have_no_silent_selection(self):
        self.args['rules'].append(copy.deepcopy(self.args['rules'][0]))
        result = self.held()
        self.assertTrue(all(item['status'] == 'HOLD' for item in result['rule_results']))
        self.wrapper, self.current, self.args = fixture()
        payload = {k: copy.deepcopy(self.args['rules'][0][k]) for k in ('rule_id', 'declared_predicate', 'input_types', 'units')}
        payload['rule_id'] = 'second-authored-branch'
        source = json.loads(self.args['rule_sources'][0]['text'])
        source['rules'].append(payload)
        text = canonical(source)
        self.args['rule_sources'][0].update(text=text, sha256=sha(text))
        self.args['rules'][0]['source_ref']['sha256'] = sha(text)
        self.args['rules'].append(dict(payload, source_ref=dict(source_id='authored-rule-source', sha256=sha(text), rule_index=1)))
        self.args['inputs']['mode'] = None
        result = self.held('inputs.mode')
        self.assertEqual(len(result['questions']), 1)
        self.assertEqual([len(item['questions']) for item in result['rule_results']], [1, 1])

    def test_non_native_cycles_and_non_finite_values_are_rejected_before_evaluation(self):
        cyclic = []
        cyclic.append(cyclic)
        class NotNative(dict): pass
        for bad in (float('nan'), float('inf'), cyclic, NotNative()):
            with self.subTest(kind=type(bad).__name__):
                self.args['inputs']['level'] = bad
                result = self.held('input')
                self.assertIsNone(result['snapshots'])

    def test_returned_snapshots_are_detached_and_keep_all_raw_refs(self):
        before = copy.deepcopy((self.wrapper, self.current, self.args))
        result = self.build()
        self.assertEqual(result['snapshots']['rule_sources'], self.args['rule_sources'])
        self.assertEqual(result['snapshots']['inputs'], self.args['inputs'])
        result['snapshots']['rules'][0]['declared_predicate']['operator'] = 'changed'
        result['binding']['revision'] = -1
        self.assertEqual((self.wrapper, self.current, self.args), before)

    def test_pure_gate_opens_no_files_store_sql_children_or_network(self):
        api = self.api()
        def forbidden(*args, **kwargs): raise AssertionError('unexpected I/O')
        with patch('builtins.open', forbidden), patch.object(Path, 'open', forbidden), patch.object(sqlite3, 'connect', forbidden), \
             patch.object(subprocess, 'Popen', forbidden), patch.object(socket, 'create_connection', forbidden), \
             patch('labflow.store.Store.__init__', forbidden):
            result = api(self.wrapper, self.current, **self.args)
        self.assertEqual(result['status'], 'REVIEW_RULE_BRANCH')

    def test_original_memory_and_control_exceptions_propagate(self):
        api = self.api()
        for error in (MemoryError('bounded-control'), KeyboardInterrupt('bounded-control'), SystemExit('bounded-control')):
            with self.subTest(kind=type(error).__name__):
                with patch('labflow.intake_rule_condition_gate._sources', side_effect=error):
                    with self.assertRaises(type(error)) as caught:
                        api(self.wrapper, self.current, **self.args)
                self.assertIs(caught.exception, error)


if __name__ == '__main__':
    unittest.main()
