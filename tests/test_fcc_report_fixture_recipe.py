"""Synthetic case DTOs only; preparation never dispatches a fixture."""
import copy
import json
import math
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import fcc_report_fixture_recipe as preparation
from labflow.virtual_fleet import core, integration, method_adapter
from tests.test_fcc_report_calculation import claim, evidence, fixture as calculation_fixture, find


SETTING_ROWS = (
    ('power_dbm', 'setting.dut_power_dbm', 'dBm', -4),
    ('frequency_hz', 'setting.frequency', 'Hz', 2450000000),
    ('bandwidth_hz', 'setting.bandwidth', 'Hz', 20000000),
    ('modulation', 'setting.modulation', None, 'OFDM'),
    ('duty_cycle', 'setting.duty_cycle', 'ratio', .25),
    ('crest_factor_db', 'setting.crest_factor', 'dB', 3),
    ('attenuation_db', 'setting.path_attenuation', 'dB', 10),
    ('switch_loss_db', 'setting.switch_loss', 'dB', .5),
    ('coupling_db', 'setting.coupling', 'dB', 20),
    ('tested_model', 'setting.tested_model', None, 'SM-A176U'),
    ('supply_voltage_v', 'setting.supply_voltage', 'V', 5),
    ('supply_current_limit_a', 'setting.supply_current_limit', 'A', 1),
    ('supply_load_resistance_ohm', 'setting.supply_load_resistance', 'ohm', 50),
    ('chamber_temperature_c', 'setting.chamber_temperature', 'C', 23),
    ('chamber_humidity_percent', 'setting.chamber_humidity', '%', 45),
    ('selected_rf_input', 'setting.selected_rf_input', None, 'rf_1'),
)
QUANTITY_ROWS = (
    ('reference_plane', 'method.reference_plane', 'sensor_input'),
    ('metric', 'method.power_metric', 'on_mean_power'),
    ('quantity_unit', 'method.power_unit', 'dBm'),
)
POINT = ('power_dbm', 'frequency_hz', 'bandwidth_hz', 'modulation',
         'duty_cycle', 'crest_factor_db', 'tested_model')


def recipe_fixture(*, separate=False, power=-4, source_synthetic=True):
    detail, _ = calculation_fixture()
    detail.update(corpus_id='CORPUS-SYNTH-026', synthetic=source_synthetic)
    case = detail['case']
    case['case_id'] = case['preview']['case_id'] = 'CASE-SYNTH-026'
    case['claims'] = [c for c in case['claims'] if c['claim_id'] != 'reading']
    find(detail, 'family')['value'] = case['preview']['product_family'] = 'smartphone'
    case['preview']['models'] = ['SM-A176U']
    case['preview']['evaluation_group']['keys'] = ['family:smartphone', 'source:' + detail['documents'][0]['sha256']]
    case['claims'].append(claim('models', 'product.models', ['SM-A176U'], page=1))
    request = {'recipe_id': 'conducted_sensor_fixture_v1', 'model': 'SM-A176U',
               'rule': '47 CFR §15.247', 'method': 'ANSI C63.10-2013',
               'product_claim_ids': {'family': 'family', 'models': 'models'},
               'setting_claim_ids': {}, 'quantity_claim_ids': {}}
    for role, field, unit, default in SETTING_ROWS:
        identity = 'SETTING.' + role
        request['setting_claim_ids'][role] = identity
        item = claim(identity, field, power if role == 'power_dbm' else default, unit,
                     page=1 if separate and role not in POINT else 2)
        item['evidence'][0].update(table='SETUP' if separate and role not in POINT else 'RF-POINT',
                                   row='GLOBAL' if separate and role not in POINT else 'POINT-1')
        case['claims'].append(item)
    for role, field, value in QUANTITY_ROWS:
        identity = 'QUANTITY.' + role
        request['quantity_claim_ids'][role] = identity
        item = claim(identity, field, value, page=1 if separate else 2)
        item['evidence'][0].update(table='SETUP' if separate else 'RF-POINT',
                                   row='GLOBAL' if separate else 'POINT-1')
        case['claims'].append(item)
    if separate:
        case['claims'].append(binding_claim(request))
    return detail, request


def binding_claim(request):
    point_ids = [request['setting_claim_ids'][role] for role in POINT]
    contexts = [identity for role, identity in request['setting_claim_ids'].items() if role not in POINT]
    contexts.extend(request['quantity_claim_ids'].values())
    return claim('SETUP-BINDING', 'setting.setup_binding',
                 {'point_claim_ids': point_ids, 'context_claim_ids': contexts}, page=1)


def selected(detail, request, role):
    group = 'quantity_claim_ids' if role in {r[0] for r in QUANTITY_ROWS} else 'setting_claim_ids'
    return find(detail, request[group][role])


class FccReportFixtureRecipeTests(unittest.TestCase):
    def prepare(self, **kwargs):
        detail, request = recipe_fixture(**kwargs)
        return detail, request, preparation.prepare_report_fixture_recipe(detail, request)

    def assert_error(self, code, detail, request):
        with self.assertRaises(preparation.FccReportFixtureRecipeError) as caught:
            preparation.prepare_report_fixture_recipe(detail, request)
        error = caught.exception
        self.assertEqual(error.code, code)
        self.assertEqual(error.args, (code,))
        self.assertEqual(str(error), code)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def assert_gap(self, detail, request, reason, *, incompatible=False):
        result = preparation.prepare_report_fixture_recipe(detail, request)
        self.assertEqual(result['status'], 'incompatible_with_fixed_fixture' if incompatible
                         else 'insufficient_evidence')
        self.assertEqual(result['reason_codes'], [reason])
        self.assertIsNone(result['candidate'])
        self.assertIsNone(result['source_projection_sha256'])
        self.assertIs(result['authority']['execution_authorized'], False)
        return result

    def test_prepared_exact24_keys_candidate4_and_no_execution_authority(self):
        detail, request, result = self.prepare()
        self.assertEqual(set(result), {'schema_version', 'kind', 'corpus_id', 'case_id',
            'execution_mode', 'source_synthetic', 'target_synthetic', 'status', 'reason_codes',
            'request_context', 'verification', 'authority', 'method_approval', 'coverage',
            'source_binding', 'product_bindings', 'setting_bindings', 'quantity_bindings',
            'context_bindings', 'fixture_descriptor', 'bootstrap_policy', 'candidate',
            'source_projection_sha256', 'validation_scope'})
        self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
        self.assertEqual(result['reason_codes'], [])
        self.assertEqual(result['candidate'], {'recipe_id': request['recipe_id'], 'model': 'SM-A176U',
                         'settings': {'power_dbm': -4.}, 'source_synthetic': True})
        self.assertEqual(result['authority'], {'execution_authorized': False,
                         'current_authority': False, 'runtime_created': False, 'command_count': 0,
                         'readiness_scope': 'historical_report_context_only'})
        self.assertRegex(result['source_projection_sha256'], r'^[a-f0-9]{64}$')
        self.assertEqual(len(result['setting_bindings']), 16)
        self.assertEqual(len(result['quantity_bindings']), 3)
        self.assertEqual(len(result['product_bindings']), 2)
        self.assertEqual(result['method_approval'], 'not_assessed')
        self.assertTrue(all(v is False for v in result['verification'].values()))
        self.assertEqual(result['coverage'], {'regulatory_scope_complete': False,
                         'phy_coverage': 'not_assessed', 'report_reproduction_verified': False,
                         'bootstrap_calibration_verified': False})

    def test_reuses_readonly_descriptor_once_and_keeps_target_and_source_synthetic_separate(self):
        detail, request = recipe_fixture(source_synthetic=False)
        with patch.object(method_adapter, 'describe_fixture_method',
                          wraps=method_adapter.describe_fixture_method) as called:
            result = preparation.prepare_report_fixture_recipe(detail, request)
        called.assert_called_once_with(request['recipe_id'], model='SM-A176U', settings={'power_dbm': -4})
        self.assertIs(result['source_synthetic'], False)
        self.assertIs(result['target_synthetic'], True)
        self.assertIs(result['candidate']['source_synthetic'], False)
        self.assertEqual(result['fixture_descriptor']['quantity'],
                         {'reference_plane': 'sensor_input', 'metric': 'on_mean_power', 'unit': 'dBm'})

    def test_all_six_bootstrap_roles_need_explicit_source_and_stay_policy_not_ratings(self):
        _, _, good = self.prepare()
        self.assertEqual(good['bootstrap_policy'], {
            'basis': 'declared_synthetic_policy',
            'fixed_requirements': {'supply_voltage_v': 5, 'supply_current_limit_a': 1,
                'supply_load_resistance_ohm': 50, 'chamber_temperature_c': 23,
                'chamber_humidity_percent': 45, 'selected_rf_input': 'rf_1'},
            'unverified_assumptions': ['sensor_calibration_valid_true', 'triggered_sensor_acquisition',
                                       'auxiliary_meter_analyzer_bootstrap'],
            'verified': False})
        for role in [r[0] for r in SETTING_ROWS[-6:]]:
            detail, request = recipe_fixture()
            request['setting_claim_ids'][role] = 'MISSING'
            self.assert_gap(detail, request, 'claim_missing')

    def test_native_fixed_numeric_settings_are_exact_and_not_filled(self):
        for role, _, _, value in SETTING_ROWS:
            if type(value) not in (int, float) or role == 'power_dbm':
                continue
            detail, request = recipe_fixture()
            selected(detail, request, role)['value'] = float(value) + .125
            self.assert_gap(detail, request, 'setting_value_mismatch', incompatible=True)

    def test_power_limits_zero_and_original_numeric_types(self):
        for power in (-30, 20, 0, -0.0):
            with self.subTest(power=power):
                _, _, result = self.prepare(power=power)
                self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
                self.assertIs(type(result['setting_bindings'][0]['value']), type(power))
        for power in (math.nextafter(-30., -math.inf), math.nextafter(20., math.inf)):
            detail, request = recipe_fixture(power=power)
            self.assert_gap(detail, request, 'setting_value_mismatch', incompatible=True)
        detail, request = recipe_fixture()
        selected(detail, request, 'duty_cycle')['value'] = 0
        self.assert_gap(detail, request, 'setting_value_mismatch', incompatible=True)

    def test_false_is_not_a_numeric_setting_or_missing_value(self):
        detail, request = recipe_fixture()
        selected(detail, request, 'supply_voltage_v')['value'] = False
        self.assert_gap(detail, request, 'claim_type_mismatch')

    def test_wrong_native_units_never_convert_mhz_ghz_or_temperature_symbols(self):
        for role, unit in (('frequency_hz', 'MHz'), ('frequency_hz', 'GHz'),
                           ('supply_voltage_v', 'mV'), ('chamber_temperature_c', '°C')):
            detail, request = recipe_fixture()
            selected(detail, request, role)['unit'] = unit
            self.assert_gap(detail, request, 'unit_mismatch', incompatible=True)

    def test_measured_power_cannot_be_used_as_dut_setting(self):
        detail, request = recipe_fixture()
        selected(detail, request, 'power_dbm')['field'] = 'result.rf_power_reading'
        self.assert_gap(detail, request, 'claim_role_mismatch')

    def test_other_frequency_bandwidth_modulation_and_route_are_not_reclassified(self):
        for role, value in (('frequency_hz', 2437000000), ('bandwidth_hz', 22000000),
                             ('modulation', 'DSSS'), ('selected_rf_input', 'rf_2')):
            detail, request = recipe_fixture()
            selected(detail, request, role)['value'] = value
            self.assert_gap(detail, request, 'setting_value_mismatch', incompatible=True)

    def test_dut_output_peak_time_average_and_unit_do_not_become_sensor_on_mean(self):
        for role, value, reason in (('reference_plane', 'dut_output', 'reference_plane_mismatch'),
                                   ('metric', 'peak_power', 'power_metric_mismatch'),
                                   ('metric', 'time_average', 'power_metric_mismatch'),
                                   ('quantity_unit', 'W', 'quantity_unit_mismatch')):
            detail, request = recipe_fixture()
            selected(detail, request, role)['value'] = value
            self.assert_gap(detail, request, reason, incompatible=True)

    def test_rule_scope_other_model_recipe_and_method_edition_are_not_forced(self):
        for key, value, reason in (('recipe_id', 'another_recipe', 'recipe_mismatch'),
                                   ('model', 'OTHER', 'model_mismatch'),
                                   ('rule', '47 CFR 15.255', 'rule_scope_mismatch')):
            detail, request = recipe_fixture()
            request[key] = value
            self.assert_gap(detail, request, reason, incompatible=True)
        detail, request = recipe_fixture()
        request['method'] = 'ANSI C63.10-2020'
        self.assert_gap(detail, request, 'method_context_unconfirmed')

    def test_product_models_list_does_not_override_other_tested_model_row(self):
        detail, request = recipe_fixture()
        find(detail, 'models')['value'].append('OTHER')
        detail['case']['preview']['models'].append('OTHER')
        selected(detail, request, 'tested_model')['value'] = 'OTHER'
        self.assert_gap(detail, request, 'model_mismatch', incompatible=True)

    def test_product_context_aliases_are_only_trim_casefold_without_mutation(self):
        detail, request = recipe_fixture()
        find(detail, 'family')['value'] = ' Smartphone '
        find(detail, 'models')['value'] = [' sm-a176u ']
        selected(detail, request, 'tested_model')['value'] = ' sm-a176u '
        before = copy.deepcopy(detail)
        result = preparation.prepare_report_fixture_recipe(detail, request)
        self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
        self.assertEqual(result['product_bindings'][0]['value'], ' Smartphone ')
        self.assertEqual(detail, before)

    def test_equal_folded_general_context_is_not_a_false_conflict(self):
        detail, request = recipe_fixture()
        duplicate = copy.deepcopy(find(detail, 'family'))
        duplicate.update(claim_id='FAMILY-EQUAL', value=' SMARTPHONE ')
        detail['case']['claims'].append(duplicate)
        self.assertEqual(preparation.prepare_report_fixture_recipe(detail, request)['status'],
                         'prepared_for_fixed_virtual_fixture')
        duplicate['value'] = 'different device'
        self.assert_gap(detail, request, 'case_context_unconfirmed')

    def test_unreviewed_inferred_or_wrong_field_selected_claims_stay_insufficient(self):
        for changes, reason in (({'status': 'extracted'}, 'claim_unreviewed'),
                                ({'basis': 'developer_inference'}, 'claim_basis_unconfirmed'),
                                ({'field': 'setting.other_voltage'}, 'claim_role_mismatch'),
                                ({'value': '5'}, 'claim_type_mismatch')):
            detail, request = recipe_fixture()
            selected(detail, request, 'supply_voltage_v').update(changes)
            self.assert_gap(detail, request, reason)

    def test_source_context_conflict_unknown_issuer_and_out_of_scope_stay_unprepared(self):
        for key, value, reason in (('review_status', 'conflicting', 'case_context_conflicting'),
                                   ('issuer_class', 'unknown', 'case_context_unconfirmed'),
                                   ('scope_status', 'pending', 'case_context_unconfirmed'),
                                   ('scope_status', 'future', 'case_context_unconfirmed')):
            detail, request = recipe_fixture()
            detail['case']['preview'][key] = value
            self.assert_gap(detail, request, reason)

    def test_standard_reference_only_is_not_a_used_method_fact(self):
        detail, request = recipe_fixture()
        find(detail, 'methods')['basis'] = 'standard_reference_only'
        self.assert_gap(detail, request, 'method_context_unconfirmed')

    def test_point_model_and_other_point_fields_cannot_mix_rows_or_pages(self):
        detail, request = recipe_fixture()
        selected(detail, request, 'tested_model')['evidence'][0]['row'] = 'OTHER-POINT'
        self.assert_gap(detail, request, 'source_row_mismatch')
        detail, request = recipe_fixture()
        selected(detail, request, 'frequency_hz')['evidence'] = [evidence(1)]
        self.assert_gap(detail, request, 'source_page_mismatch')

    def test_unknown_en_dash_point_rows_require_and_preserve_shared_line_proof(self):
        detail, request = recipe_fixture()
        for line, role in enumerate(POINT, 1):
            selected(detail, request, role)['evidence'][0].update(row='–', line_start=line, line_end=line)
        self.assert_gap(detail, request, 'row_evidence_unconfirmed')
        for role in POINT:
            selected(detail, request, role)['evidence'][0].update(line_start=1, line_end=1)
        # Contexts must use the same unknown row identity too for direct linkage.
        for role in set(request['setting_claim_ids']) - set(POINT):
            selected(detail, request, role)['evidence'][0]['row'] = '–'
        for role in request['quantity_claim_ids']:
            selected(detail, request, role)['evidence'][0]['row'] = '–'
        result = preparation.prepare_report_fixture_recipe(detail, request)
        self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
        self.assertIsNone(result['source_binding']['row_binding']['row'])
        self.assertEqual(result['source_binding']['row_binding']['basis'], 'common_line_range')
        self.assertEqual(result['setting_bindings'][0]['sources'][0]['row'], '–')

    def test_separate_page_context_requires_explicit_whole_setup_binding(self):
        detail, request = recipe_fixture(separate=True)
        detail['case']['claims'] = [c for c in detail['case']['claims'] if c['claim_id'] != 'SETUP-BINDING']
        self.assert_gap(detail, request, 'setup_binding_missing')
        detail['case']['claims'].append(binding_claim(request))
        result = preparation.prepare_report_fixture_recipe(detail, request)
        self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
        self.assertEqual(result['source_binding']['setup_binding_claim_id'], 'SETUP-BINDING')

    def test_partial_or_unreviewed_setup_binding_cannot_join_context(self):
        for change in (lambda c: c.update(status='extracted'),
                       lambda c: c['value']['point_claim_ids'].pop(),
                       lambda c: c['value']['context_claim_ids'].pop()):
            detail, request = recipe_fixture(separate=True)
            change(find(detail, 'SETUP-BINDING'))
            self.assert_gap(detail, request, 'setup_binding_missing')

    def test_conflicting_setup_bindings_do_not_choose_the_convenient_one(self):
        detail, request = recipe_fixture(separate=True)
        other = copy.deepcopy(find(detail, 'SETUP-BINDING'))
        other['claim_id'] = 'SETUP-CONFLICT'
        other['value']['context_claim_ids'][-1] = 'UNUSED-CONTEXT'
        detail['case']['claims'].append(other)
        detail['case']['claims'].append(claim('UNUSED-CONTEXT', 'setting.other_context', 'other', page=1))
        self.assert_gap(detail, request, 'setup_binding_conflicting')

    def test_direct_row_proof_does_not_silence_explicit_conflicting_setup_bindings(self):
        detail, request = recipe_fixture()
        detail['case']['claims'].append(binding_claim(request))
        other = copy.deepcopy(find(detail, 'SETUP-BINDING'))
        other['claim_id'] = 'SETUP-CONFLICT'
        other['value']['context_claim_ids'][-1] = 'UNUSED-CONTEXT'
        detail['case']['claims'].append(other)
        detail['case']['claims'].append(claim('UNUSED-CONTEXT', 'setting.other_context', 'other', page=1))
        self.assert_gap(detail, request, 'setup_binding_conflicting')

    def test_setup_array_and_selector_order_do_not_change_fingerprint(self):
        detail, request = recipe_fixture(separate=True)
        original = preparation.prepare_report_fixture_recipe(detail, request)
        for key in ('product_claim_ids', 'setting_claim_ids', 'quantity_claim_ids'):
            request[key] = dict(reversed(list(request[key].items())))
        binding = find(detail, 'SETUP-BINDING')['value']
        binding['point_claim_ids'].reverse()
        binding['context_claim_ids'].reverse()
        self.assertEqual(preparation.prepare_report_fixture_recipe(detail, request), original)

    def test_noncitable_false_literal_and_parser_warning_are_not_ready(self):
        detail, request = recipe_fixture()
        selected(detail, request, 'power_dbm')['evidence'][0]['literal_verified'] = False
        self.assert_gap(detail, request, 'evidence_unconfirmed')
        detail, request = recipe_fixture()
        detail['documents'][0]['page_index'][1].update(status='truncated', citable=False)
        self.assert_gap(detail, request, 'evidence_unconfirmed')
        detail, request = recipe_fixture()
        detail['documents'][0]['extraction'].update(status='partial', complete=False,
            issues=[{'code': 'parser_warning', 'file_page': 2}])
        self.assert_gap(detail, request, 'evidence_unconfirmed')

    def test_wrong_sha_text_hash_line_range_and_unknown_keys_are_schema_errors(self):
        for change in (lambda d: d.update(extra=True),
                       lambda d: selected(d, recipe_fixture()[1], 'power_dbm')['evidence'][0]
                           .update(source_sha256='d' * 64),
                       lambda d: d['documents'][0]['page_index'][1].update(text_sha256='d' * 64),
                       lambda d: d['case']['preview'].update(document_ids=['OTHER'])):
            detail, request = recipe_fixture()
            change(detail)
            self.assert_error('fcc_recipe_invalid_case', detail, request)

    def test_exact_request_roles_unique_ids_and_no_path_callback_api(self):
        for change in (lambda r: r.update(extra='PRIVATE'),
                       lambda r: r['setting_claim_ids'].pop('supply_voltage_v'),
                       lambda r: r['quantity_claim_ids'].update(metric=r['quantity_claim_ids']['quantity_unit']),
                       lambda r: r.update(model='C:\\PRIVATE\\model'),
                       lambda r: r.update(method=lambda: None)):
            detail, request = recipe_fixture()
            change(request)
            self.assert_error('fcc_recipe_invalid_request', detail, request)

    def test_plain_types_only_never_call_mapping_or_repr_hooks(self):
        class Trap(dict):
            def items(self):
                raise AssertionError('mapping hook')
            def __repr__(self):
                raise AssertionError('repr hook')
        detail, request = recipe_fixture()
        self.assert_error('fcc_recipe_invalid_case', Trap(detail), request)
        self.assert_error('fcc_recipe_invalid_request', detail, Trap(request))
        detail['case']['claims'][0]['value'] = object()
        self.assert_error('fcc_recipe_invalid_case', detail, request)

    def test_descriptor_failure_is_one_attempt_with_bindings_retained_and_no_retry(self):
        detail, request = recipe_fixture()
        with patch.object(method_adapter, 'describe_fixture_method',
                          side_effect=RuntimeError('PRIVATE-HELPER-ERROR')) as called:
            result = self.assert_gap(detail, request, 'fixture_contract_unavailable')
        self.assertEqual(called.call_count, 1)
        self.assertEqual(len(result['setting_bindings']), 16)
        self.assertIsNone(result['fixture_descriptor'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_changed_or_extra_descriptor_fields_never_publish_a_candidate(self):
        for change in (lambda d: d['quantity'].update(reference_plane='dut_output'),
                       lambda d: d['synthetic_setup'].update(coupling_db=10),
                       lambda d: d.update(hardware_verified=True),
                       lambda d: d.update(extra='PRIVATE')):
            detail, request = recipe_fixture()
            descriptor = method_adapter.describe_fixture_method(
                request['recipe_id'], model='SM-A176U', settings={'power_dbm': -4})
            change(descriptor)
            with patch.object(method_adapter, 'describe_fixture_method', return_value=descriptor) as called:
                result = preparation.prepare_report_fixture_recipe(detail, request)
            self.assertEqual(result['status'], 'insufficient_evidence')
            self.assertIsNone(result['candidate'])
            self.assertIsNone(result['fixture_descriptor'])
            self.assertEqual(called.call_count, 1)
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_no_runtime_factory_execution_store_file_network_process_or_tick(self):
        detail, request = recipe_fixture()
        with patch('builtins.open', side_effect=AssertionError('file I/O')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network I/O')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process I/O')), \
                patch.object(method_adapter, 'run_fixture_method', side_effect=AssertionError('run')), \
                patch.object(method_adapter, 'prepare_sensor_trial', side_effect=AssertionError('trial')), \
                patch.object(method_adapter, 'FleetHarness', side_effect=AssertionError('harness')), \
                patch.object(integration, 'create_conducted_example', side_effect=AssertionError('factory')), \
                patch.object(core.VirtualFleet, 'execute', side_effect=AssertionError('execute')), \
                patch.object(core.VirtualFleet, 'advance', side_effect=AssertionError('advance')):
            self.assertEqual(preparation.prepare_report_fixture_recipe(detail, request)['status'],
                             'prepared_for_fixed_virtual_fixture')

    def test_original_inputs_and_returned_binding_values_are_detached(self):
        detail, request = recipe_fixture()
        before, request_before = copy.deepcopy(detail), copy.deepcopy(request)
        result = preparation.prepare_report_fixture_recipe(detail, request)
        result['candidate']['settings']['power_dbm'] = 999
        result['product_bindings'][1]['value'].append('OTHER')
        result['setting_bindings'][0]['sources'][0]['row'] = 'OTHER'
        result['fixture_descriptor']['quantity']['metric'] = 'OTHER'
        again = preparation.prepare_report_fixture_recipe(detail, request)
        self.assertEqual(again['candidate']['settings']['power_dbm'], -4.)
        self.assertEqual(detail, before)
        self.assertEqual(request, request_before)

    def test_projection_fingerprint_binds_case_corpus_and_source_origin(self):
        detail, request = recipe_fixture()
        original = preparation.prepare_report_fixture_recipe(detail, request)['source_projection_sha256']
        for mutate in (lambda d: d.update(corpus_id='OTHER-CORPUS'),
                       lambda d: (d['case'].update(case_id='OTHER-CASE'),
                                  d['case']['preview'].update(case_id='OTHER-CASE')),
                       lambda d: d.update(synthetic=False)):
            changed = copy.deepcopy(detail)
            mutate(changed)
            result = preparation.prepare_report_fixture_recipe(changed, request)
            self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
            self.assertNotEqual(result['source_projection_sha256'], original)

    def test_context_quote_and_file_path_never_leak_to_result_or_error(self):
        detail, request = recipe_fixture()
        selected(detail, request, 'power_dbm')['evidence'][0]['quote'] = 'PRIVATE-QUOTE'
        detail['documents'][0]['rights']['notes'] = 'C:\\PRIVATE-PATH'
        result = preparation.prepare_report_fixture_recipe(detail, request)
        self.assertEqual(result['status'], 'prepared_for_fixed_virtual_fixture')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_input_and_output_wrapper_budgets_are_enforced(self):
        detail, request = recipe_fixture()
        detail['documents'][0]['rights']['notes'] = 'x' * 16385
        self.assert_error('fcc_recipe_limit_exceeded', detail, request)
        detail, request = recipe_fixture()
        with patch.object(preparation, '_OUTPUT_BYTES', 1):
            self.assert_error('fcc_recipe_limit_exceeded', detail, request)


if __name__ == '__main__':
    unittest.main()
