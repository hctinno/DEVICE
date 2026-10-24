"""Synthetic DTO contracts only; no PDF/source-byte verification is claimed."""
import copy
from fractions import Fraction
import json
import math
import socket
import subprocess
import unittest
from unittest.mock import patch

from labflow import calculations
from labflow import fcc_report_calculation as checks


DOC, SHA, TEXT = 'DOC-SYNTH-023', 'a' * 64, 'b' * 64
SECOND_TEXT = 'c' * 64
RULE, METHOD = '47 CFR §15.247', 'ANSI C63.10-2013'
VERIFY = dict.fromkeys(('hardware_verified', 'physical_verified', 'model_execution_verified',
                       'normative_compliance_verified', 'coverage_complete'), False)


def evidence(page=2, **changes):
    return dict({'document_id': DOC, 'source_sha256': SHA, 'file_page': page,
                 'printed_page': None, 'table': None, 'row': None, 'column': None,
                 'footnotes': [], 'text_sha256': TEXT if page == 1 else SECOND_TEXT,
                 'line_start': 1, 'line_end': 1, 'quote': 'Synthetic DTO evidence only.',
                 'literal_verified': True}, **changes)


def claim(identity, field, value, unit=None, *, page=2, **changes):
    return dict({'claim_id': identity, 'field': field, 'value': value, 'unit': unit,
                 'status': 'reviewed', 'basis': 'report_fact', 'evidence': [evidence(page)]}, **changes)


def fixture(calculator='rf_power', *, reported=None, result_unit=None, tolerance=0):
    context = [
        claim('issuer', 'issuer.classification', 'hct_korea', page=1, basis='developer_inference'),
        claim('legal', 'issuer.legal_name', 'Synthetic HCT organization', page=1),
        claim('address', 'issuer.address', 'Synthetic City', page=1),
        claim('date', 'report.issue_date', '2025-03-03', page=1),
        claim('family', 'product.family', 'synthetic radio', page=1),
        claim('rules', 'method.rules', [RULE], page=1),
        claim('methods', 'method.references', [METHOD], page=1),
    ]
    if calculator == 'rf_power':
        inputs = [claim('reading', 'result.rf_power_reading', 30, 'dBm')]
    else:
        inputs = [claim('reading', 'result.emc_reading', 30, 'dBuV'),
                  claim('af', 'correction.antenna_factor_db_per_m', 15, 'dB/m'),
                  claim('cable', 'correction.cable_loss_db', 3, 'dB'),
                  claim('gain', 'correction.preamp_gain_db', 20, 'dB'),
                  claim('corrected', 'correction.instrument_corrections_applied', False)]
    if reported is not None:
        context.append(claim('reported', 'result.rf_power' if calculator == 'rf_power'
                             else 'result.emc_field_strength', reported,
                             result_unit or ('W' if calculator == 'rf_power' else 'dBuV/m')))
    preview = {'case_id': 'CASE-SYNTH-023', 'report_group_id': None,
               'report_number': None, 'revision': None, 'issuer_class': 'hct_korea',
               'issue_date': '2025-03-03', 'scope_status': 'in_scope', 'fcc_ids': [],
               'product_family': 'synthetic radio', 'manufacturer': None, 'models': [],
               'rules': [RULE], 'methods': [METHOD], 'equipment_models': [],
               'review_status': 'reviewed', 'document_ids': [DOC],
               'evaluation_group': {'eligible': False,
                   'keys': ['family:synthetic radio', 'source:' + SHA],
                   'missing': ['fcc_ids', 'report_group_id', 'reuse_group_ids']}}
    document = {
        'document_id': DOC, 'sha256': SHA, 'size_bytes': 1000, 'physical_pages': 2,
        'exhibits': [{'exhibit_id': 'SYNTH-EXHIBIT', 'fcc_id': None,
                      'application_id': None, 'exhibit_type': None, 'url': None,
                      'source_kind': 'existing_user', 'accessed_at': '2026-10-24T10:00:00+09:00',
                      'official_match_status': 'unverified', 'official_url': None,
                      'search_ids': []}],
        'rights': {'status': 'private_only', 'notes': None,
                   'public_redistribution_allowed': False, 'external_model_use_allowed': False},
        'extraction': {'status': 'ok', 'complete': True, 'total_pages': 2,
                       'processed_pages': 2, 'parser': {'name': 'pypdf', 'version': 'synthetic'},
                       'issues': []},
        'page_index': [{'file_page': p, 'status': 'ok', 'text_sha256': TEXT if p == 1 else SECOND_TEXT,
                        'line_count': 20, 'citable': True} for p in (1, 2)],
    }
    detail = {'schema_version': 1, 'kind': 'fcc_report_case', 'corpus_id': 'CORPUS-SYNTH-023',
              'execution_mode': 'report_derived', 'synthetic': True,
              'validation_scope': 'source_bytes_and_retained_page_literals_only',
              'verification': dict(VERIFY), 'case': {'case_id': 'CASE-SYNTH-023',
                  'report_group_id': None, 'document_ids': [DOC], 'claims': context + inputs,
                  'relations': [], 'reuse_group_ids': [], 'preview': preview},
              'documents': [document]}
    request = {'calculator': calculator, 'rule': RULE, 'method': METHOD,
               'input_claim_ids': {'reading': 'reading'} if calculator == 'rf_power' else {
                   'reading': 'reading', 'antenna_factor_db_per_m': 'af', 'cable_loss_db': 'cable',
                   'preamp_gain_db': 'gain', 'instrument_corrections_applied': 'corrected'},
               'reported_result_claim_id': 'reported' if reported is not None else None,
               'comparison_policy': {'absolute_tolerance': tolerance, 'unit': result_unit or
                   ('W' if calculator == 'rf_power' else 'dBuV/m')} if reported is not None else None}
    return detail, request


def find(detail, identity):
    return next(c for c in detail['case']['claims'] if c['claim_id'] == identity)


class FccReportCalculationTests(unittest.TestCase):
    def run_check(self, calculator='rf_power', **kwargs):
        detail, request = fixture(calculator, **kwargs)
        return detail, request, checks.check_report_calculation(detail, request)

    def assert_error(self, code, detail, request):
        with self.assertRaises(checks.FccReportCalculationError) as caught:
            checks.check_report_calculation(detail, request)
        error = caught.exception
        self.assertEqual(error.code, code)
        self.assertEqual(str(error), code)
        self.assertEqual(error.args, (code,))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def assert_insufficient(self, detail, request, reason):
        with patch.object(calculations, 'calculate', wraps=calculations.calculate) as called:
            result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['reason_codes'], [reason])
        self.assertIsNone(result['calculation'])
        self.assertIsNone(result['comparison'])
        self.assertEqual(called.call_count, 0)
        return result

    def test_exact_result_wrapper_and_reused_rf_calculator(self):
        detail, request = fixture()
        with patch.object(calculations, 'calculate', wraps=calculations.calculate) as called:
            result = checks.check_report_calculation(detail, request)
        called.assert_called_once_with('rf_power', {'reading': 30, 'unit': 'dBm'})
        self.assertEqual(set(result), {'schema_version', 'kind', 'corpus_id', 'case_id', 'calculator',
            'status', 'reason_codes', 'execution_mode', 'synthetic', 'validation_scope', 'verification',
            'context', 'source_page', 'inputs', 'reported_result', 'calculation', 'unit_conversion',
            'comparison_policy', 'comparison', 'interpretation_scope'})
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(result['calculation'], {'value': 1., 'unit': 'W',
                         'native_result': {'value': 1., 'unit': 'W'}})
        self.assertIsNone(result['reported_result'])
        self.assertIsNone(result['comparison'])
        self.assertIsNone(result['unit_conversion'])
        self.assertEqual(result['execution_mode'], 'report_derived')
        self.assertEqual(result['verification'], {**VERIFY, 'source_bytes_reverified': False,
                          'issuer_authenticity_verified': False, 'native_raw_observed': False})

    def test_emc_pair_reuses_existing_calculator_and_explicit_false(self):
        detail, request = fixture('emc_field_strength', reported=28)
        with patch.object(calculations, 'calculate', wraps=calculations.calculate) as called:
            result = checks.check_report_calculation(detail, request)
        called.assert_called_once_with('emc_field_strength', {'reading': 30, 'unit': 'dBuV',
            'antenna_factor_db_per_m': 15, 'cable_loss_db': 3, 'preamp_gain_db': 20,
            'instrument_corrections_applied': False})
        self.assertEqual(result['status'], 'within_tolerance')
        self.assertEqual(result['calculation']['value'], 28.)
        self.assertIs(result['inputs'][4]['value'], False)
        self.assertEqual(result['comparison']['absolute_difference'], {'numerator': '0', 'denominator': '1'})

    def test_explicit_milliwatt_conversion_preserves_native_result_and_original(self):
        _, _, result = self.run_check(reported=1000, result_unit='mW')
        self.assertEqual(result['status'], 'within_tolerance')
        self.assertEqual(result['calculation'], {'value': 1000., 'unit': 'mW',
                          'native_result': {'value': 1., 'unit': 'W'}})
        self.assertEqual(result['unit_conversion'], {'from': 'W', 'to': 'mW', 'factor': 1000,
                                                   'basis': 'explicit_unit_conversion',
                                                   'exact_value_ratio': {'numerator': '1000', 'denominator': '1'}})
        self.assertIs(type(result['reported_result']['value']), int)

    def test_zero_reading_reported_zero_and_zero_tolerance_are_not_missing(self):
        detail, request = fixture('emc_field_strength', reported=0)
        for identity in ('reading', 'af', 'cable', 'gain'):
            find(detail, identity)['value'] = 0
        result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['status'], 'within_tolerance')
        self.assertEqual(result['calculation']['value'], 0.)
        self.assertIs(type(result['inputs'][0]['value']), int)
        self.assertIs(type(result['comparison_policy']['absolute_tolerance']), int)
        detail, request = fixture()
        find(detail, 'reading')['value'] = 0.
        result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['calculation']['value'], .001)
        self.assertIs(type(result['inputs'][0]['value']), float)

    def test_rounding_never_creates_numeric_match_and_tolerance_is_explicit(self):
        reported = math.nextafter(1., math.inf)
        _, _, result = self.run_check(reported=reported, tolerance=0)
        self.assertEqual(result['status'], 'outside_tolerance')
        self.assertEqual(result['comparison']['absolute_difference'],
                         {'numerator': '1', 'denominator': str(2 ** 52)})
        _, _, result = self.run_check(reported=reported, tolerance=2 ** -52)
        self.assertEqual(result['status'], 'within_tolerance')
        _, _, result = self.run_check(reported=reported, tolerance=math.nextafter(2 ** -52, 0))
        self.assertEqual(result['status'], 'outside_tolerance')

    def test_rule_method_edition_match_only_trim_and_casefold(self):
        detail, request = fixture()
        request.update(rule=' 47 cfr §15.247 ', method=' ansi c63.10-2013 ')
        self.assertEqual(checks.check_report_calculation(detail, request)['status'], 'calculated')
        request['method'] = 'ANSI C63.10-2020'
        self.assert_insufficient(detail, request, 'method_mismatch')
        request.update(method=METHOD, rule='47 CFR §15.209')
        self.assert_insufficient(detail, request, 'rule_mismatch')

    def test_unknown_out_of_scope_conflicting_or_unreviewed_context_never_calculates(self):
        for key, value in (('issuer_class', 'unknown'), ('scope_status', 'pending'),
                           ('scope_status', 'future'), ('scope_status', 'out_of_range'),
                           ('review_status', 'unreviewed')):
            detail, request = fixture()
            detail['case']['preview'][key] = value
            self.assert_insufficient(detail, request, 'case_context_unconfirmed')
        detail, request = fixture()
        detail['case']['preview']['review_status'] = 'conflicting'
        self.assert_insufficient(detail, request, 'case_context_conflicting')

    def test_preview_alone_is_not_reviewed_product_method_or_issuer_evidence(self):
        for identity in ('family', 'legal', 'address', 'date', 'rules', 'methods'):
            detail, request = fixture()
            find(detail, identity)['status'] = 'extracted'
            self.assert_insufficient(detail, request, 'case_context_unconfirmed')
        detail, request = fixture()
        find(detail, 'methods')['basis'] = 'standard_reference_only'
        self.assert_insufficient(detail, request, 'case_context_unconfirmed')
        detail, request = fixture()
        find(detail, 'family')['value'] = 'different product'
        self.assert_insufficient(detail, request, 'case_context_unconfirmed')

    def test_selected_claim_missing_review_basis_role_and_numeric_type(self):
        for mutate, reason in (
            (lambda c, r: r['input_claim_ids'].update(reading='missing'), 'claim_missing'),
            (lambda c, r: c.update(status='extracted'), 'claim_unreviewed'),
            (lambda c, r: c.update(basis='developer_inference'), 'claim_basis_unconfirmed'),
            (lambda c, r: c.update(field='setting.unknown_number'), 'claim_role_mismatch'),
            (lambda c, r: c.update(value=True), 'claim_type_mismatch'),
            (lambda c, r: c.update(value='30'), 'claim_type_mismatch'),
        ):
            detail, request = fixture()
            mutate(find(detail, 'reading'), request)
            self.assert_insufficient(detail, request, reason)

    def test_units_are_explicit_and_correction_roles_cannot_be_swapped(self):
        for calculator, identity, unit in (('rf_power', 'reading', 'mW'),
                ('emc_field_strength', 'reading', 'dBm'), ('emc_field_strength', 'af', 'dB'),
                ('emc_field_strength', 'cable', 'dB/m')):
            detail, request = fixture(calculator)
            find(detail, identity)['unit'] = unit
            self.assert_insufficient(detail, request, 'unit_mismatch')
        detail, request = fixture('emc_field_strength')
        request['input_claim_ids'].update(cable_loss_db='gain', preamp_gain_db='cable')
        self.assert_insufficient(detail, request, 'claim_role_mismatch')
        detail, request = fixture('emc_field_strength')
        find(detail, 'reading')['unit'] = 'dBµV'
        self.assertEqual(checks.check_report_calculation(detail, request)['status'], 'calculated')

    def test_corrections_already_applied_or_unknown_never_become_false(self):
        for value, reason in ((True, 'corrections_already_applied'), (0, 'claim_type_mismatch'),
                              ('unknown', 'claim_type_mismatch')):
            detail, request = fixture('emc_field_strength')
            find(detail, 'corrected')['value'] = value
            self.assert_insufficient(detail, request, reason)

    def test_same_source_page_required_for_all_selected_numeric_claims(self):
        detail, request = fixture('emc_field_strength')
        find(detail, 'gain')['evidence'] = [evidence(1)]
        self.assert_insufficient(detail, request, 'source_page_mismatch')
        detail, request = fixture(reported=1)
        find(detail, 'reported')['evidence'] = [evidence(1)]
        self.assert_insufficient(detail, request, 'source_page_mismatch')

    def test_unconfirmed_literal_image_truncated_and_warning_never_calculate(self):
        detail, request = fixture()
        find(detail, 'reading')['evidence'][0]['literal_verified'] = False
        self.assert_insufficient(detail, request, 'evidence_unconfirmed')
        for status in ('image_only', 'truncated', 'no_text', 'error'):
            detail, request = fixture()
            detail['documents'][0]['page_index'][1].update(status=status, citable=False)
            self.assert_insufficient(detail, request, 'evidence_unconfirmed')
        for page in (None, 2):
            detail, request = fixture()
            detail['documents'][0]['extraction'].update(status='partial', complete=False)
            detail['documents'][0]['extraction']['issues'] = [{'code': 'parser_warning', 'file_page': page}]
            self.assert_insufficient(detail, request, 'evidence_unconfirmed')

    def test_different_bad_page_does_not_erase_good_page_of_partial_document(self):
        detail, request = fixture()
        for item in detail['case']['claims']:
            item['evidence'] = [evidence(2)]
        doc = detail['documents'][0]
        doc['extraction'].update(status='partial', complete=False,
                                 issues=[{'code': 'ocr_required', 'file_page': 1}])
        doc['page_index'][0].update(status='image_only', citable=False)
        self.assertEqual(checks.check_report_calculation(detail, request)['status'], 'calculated')

    def test_source_sha_text_hash_page_range_and_literal_metadata_mismatch_is_invalid(self):
        for key, value in (('source_sha256', 'd' * 64), ('text_sha256', 'd' * 64),
                           ('document_id', 'OTHER'), ('file_page', 3), ('line_end', 21)):
            detail, request = fixture()
            find(detail, 'reading')['evidence'][0][key] = value
            self.assert_error('fcc_calc_invalid_case', detail, request)

    def test_numeric_overflow_underflow_and_integer_rounding_are_unconfirmed(self):
        for value in (10000, -10000, 2 ** 53 + 1):
            detail, request = fixture()
            find(detail, 'reading')['value'] = value
            result = checks.check_report_calculation(detail, request)
            self.assertEqual(result['status'], 'insufficient_evidence')
            self.assertEqual(result['reason_codes'], ['numeric_representation_unavailable'])
            self.assertIsNone(result['calculation'])
            self.assertEqual(result['inputs'][0]['value'], value)

    def test_unexpected_existing_calculator_failure_or_reply_is_sanitized(self):
        detail, request = fixture()
        with patch.object(calculations, 'calculate', side_effect=RuntimeError('PRIVATE CALC FAILURE')):
            result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['reason_codes'], ['calculation_unavailable'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        for reply in ({'value': 0., 'unit': 'W'}, {'value': True, 'unit': 'W'},
                      {'value': math.inf, 'unit': 'W'}, {'value': 1., 'unit': 'mW'},
                      {'value': 1., 'unit': 'W', 'secret': 'PRIVATE'}):
            with patch.object(calculations, 'calculate', return_value=reply):
                result = checks.check_report_calculation(detail, request)
            self.assertEqual(result['status'], 'insufficient_evidence')
            self.assertIsNone(result['calculation'])
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_request_exact_keys_policy_id_and_no_implicit_tolerance(self):
        for change in (lambda r: r.update(extra='PRIVATE'),
                       lambda r: r.pop('method'),
                       lambda r: r.update(calculator='unknown'),
                       lambda r: r.update(rule='C:\\private\\report.pdf'),
                       lambda r: r.update(reported_result_claim_id='reported'),
                       lambda r: r.update(comparison_policy={'absolute_tolerance': 0, 'unit': 'W'}),
                       lambda r: r['input_claim_ids'].update(reading=True)):
            detail, request = fixture()
            change(request)
            self.assert_error('fcc_calc_invalid_request', detail, request)
        for tolerance in (False, -1, math.nan, math.inf):
            detail, request = fixture(reported=1, tolerance=tolerance)
            self.assert_error('fcc_calc_invalid_request', detail, request)

    def test_duplicate_selected_id_and_extra_input_roles_are_invalid_requests(self):
        detail, request = fixture('emc_field_strength')
        request['input_claim_ids']['preamp_gain_db'] = 'cable'
        self.assert_error('fcc_calc_invalid_request', detail, request)
        detail, request = fixture()
        request['input_claim_ids']['hidden'] = 'reading'
        self.assert_error('fcc_calc_invalid_request', detail, request)

    def test_exact_keys_verification_flags_duplicates_and_user_objects_are_invalid(self):
        changes = (lambda d: d.update(extra='PRIVATE'), lambda d: d.update(schema_version=True),
                   lambda d: d.update(kind='fcc_report_case_summary'),
                   lambda d: d['verification'].update(hardware_verified=True),
                   lambda d: d['case']['claims'].append(copy.deepcopy(d['case']['claims'][0])),
                   lambda d: d['documents'].append(copy.deepcopy(d['documents'][0])),
                   lambda d: d['case']['preview'].update(document_ids=['OTHER']))
        for change in changes:
            detail, request = fixture()
            change(detail)
            self.assert_error('fcc_calc_invalid_case', detail, request)
        class Trap(dict):
            def items(self):
                raise AssertionError('object hook')
        detail, request = fixture()
        self.assert_error('fcc_calc_invalid_case', Trap(detail), request)
        self.assert_error('fcc_calc_invalid_request', detail, Trap(request))

    def test_input_order_detached_result_and_no_private_body_path_or_url_output(self):
        detail, request = fixture('emc_field_strength', reported=28)
        find(detail, 'reading')['evidence'][0]['quote'] = 'PRIVATE_BODY_CANARY'
        detail['documents'][0]['rights']['notes'] = 'C:\\PRIVATE_PATH'
        detail['documents'][0]['exhibits'][0]['url'] = 'https://example.invalid/PRIVATE_URL'
        before, original_request = copy.deepcopy(detail), copy.deepcopy(request)
        result = checks.check_report_calculation(detail, request)
        request['input_claim_ids'] = dict(reversed(list(request['input_claim_ids'].items())))
        self.assertEqual(result, checks.check_report_calculation(detail, request))
        self.assertEqual(detail, before)
        self.assertNotIn('PRIVATE', json.dumps(result))
        result['inputs'][0]['sources'][0]['file_page'] = 999
        result['calculation']['native_result']['value'] = 999
        self.assertEqual(checks.check_report_calculation(detail, original_request)['calculation']['value'], 28.)

    def test_no_file_process_network_or_external_model_io(self):
        detail, request = fixture()
        with patch('builtins.open', side_effect=AssertionError('file I/O')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network I/O')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process I/O')):
            self.assertEqual(checks.check_report_calculation(detail, request)['status'], 'calculated')

    def test_explicit_other_table_or_row_cannot_be_combined_even_on_same_line(self):
        for table, row in (('T2', 'R1'), ('T1', 'R2')):
            detail, request = fixture('emc_field_strength')
            for item in detail['case']['claims']:
                item['evidence'][0].update(table='T1', row='R1')
            find(detail, 'gain')['evidence'][0].update(table=table, row=row)
            self.assert_insufficient(detail, request, 'source_row_mismatch')

    def test_explicit_same_table_row_allows_nonoverlapping_wrapped_lines(self):
        detail, request = fixture('emc_field_strength', reported=28)
        for index, identity in enumerate(('reading', 'af', 'cable', 'gain', 'reported'), 1):
            find(detail, identity)['evidence'][0].update(table='T1', row='R1',
                                                      line_start=index, line_end=index)
        result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['status'], 'within_tolerance')
        self.assertEqual(result['source_page']['row_binding'], {
            'basis': 'explicit_table_row', 'table': 'T1', 'row': 'R1',
            'line_start': None, 'line_end': None})

    def test_unknown_row_without_shared_lines_is_insufficient_not_a_filled_default(self):
        for label in (None, 'unknown', '미확인', '-'):
            detail, request = fixture('emc_field_strength')
            for index, identity in enumerate(('reading', 'af', 'cable', 'gain'), 1):
                find(detail, identity)['evidence'][0].update(table=label, row=label,
                                                          line_start=index, line_end=index)
            self.assert_insufficient(detail, request, 'row_evidence_unconfirmed')

    def test_common_line_proof_preserves_unknown_row_and_flag_can_be_other_page(self):
        detail, request = fixture('emc_field_strength', reported=28)
        find(detail, 'corrected')['evidence'] = [evidence(1)]
        result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['status'], 'within_tolerance')
        self.assertEqual(result['source_page']['row_binding'], {
            'basis': 'common_line_range', 'table': None, 'row': None, 'line_start': 1, 'line_end': 1})

    def test_numeric_integer_input_is_not_silently_rounded_by_existing_float_coercion(self):
        detail, request = fixture('emc_field_strength')
        find(detail, 'reading')['value'] = 2 ** 53 + 1
        self.assert_insufficient(detail, request, 'numeric_representation_unavailable')

    def test_whole_input_node_string_depth_and_packed_result_budgets(self):
        detail, request = fixture()
        detail['documents'][0]['rights']['notes'] = 'x' * 16385
        self.assert_error('fcc_calc_limit_exceeded', detail, request)
        detail, request = fixture()
        nested = 'synthetic'
        for _ in range(7):
            nested = [nested]
        find(detail, 'reading')['value'] = nested
        self.assert_error('fcc_calc_limit_exceeded', detail, request)
        detail, request = fixture()
        with patch.object(checks, '_OUTPUT_BYTES', 1):
            self.assert_error('fcc_calc_limit_exceeded', detail, request)

    def test_empty_document_list_is_schema_error_and_quote_has_its_own_byte_limit(self):
        detail, request = fixture()
        detail['documents'] = []
        self.assert_error('fcc_calc_invalid_case', detail, request)
        detail, request = fixture()
        find(detail, 'reading')['evidence'][0]['quote'] = 'q' * 8193
        self.assert_error('fcc_calc_limit_exceeded', detail, request)

    def test_whole_case_byte_budget_stops_before_calculator(self):
        detail, request = fixture()
        detail['case']['claims'].append(claim('large', 'setting.large_projection',
                                             ['z' * 16384] * 513))
        with patch.object(calculations, 'calculate') as called:
            self.assert_error('fcc_calc_limit_exceeded', detail, request)
        called.assert_not_called()

    def test_global_unavailable_extraction_never_becomes_citable_success(self):
        for status, complete in (('empty', True), ('parser_error', False), ('limit_exceeded', False)):
            detail, request = fixture()
            detail['documents'][0]['extraction'].update(status=status, complete=complete)
            self.assert_insufficient(detail, request, 'evidence_unconfirmed')

    def test_numeric_proof_and_context_must_share_document_without_merging_parts(self):
        detail, request = fixture()
        other = copy.deepcopy(detail['documents'][0])
        other.update(document_id='DOC-OTHER', sha256='d' * 64)
        detail['documents'].append(other)
        detail['case']['document_ids'].append('DOC-OTHER')
        detail['case']['preview']['document_ids'].append('DOC-OTHER')
        ev = find(detail, 'reading')['evidence'][0]
        ev.update(document_id='DOC-OTHER', source_sha256='d' * 64)
        self.assert_insufficient(detail, request, 'context_source_mismatch')

    def test_alternative_reviewed_page_and_row_evidence_is_selected_stably(self):
        detail, request = fixture('emc_field_strength')
        for identity in ('reading', 'af', 'cable', 'gain'):
            ev = find(detail, identity)['evidence']
            ev[0].update(table='T', row='R')
            ev.append(evidence(1, table='OTHER', row=identity))
        a = checks.check_report_calculation(detail, request)
        for item in detail['case']['claims']:
            item['evidence'].reverse()
        b = checks.check_report_calculation(detail, request)
        self.assertEqual(a, b)
        self.assertEqual(a['source_page']['file_page'], 2)
        self.assertEqual(a['status'], 'calculated')

    def test_reported_unit_mismatch_and_unreviewed_result_do_not_run_calculation(self):
        detail, request = fixture(reported=1)
        find(detail, 'reported')['unit'] = 'dBm'
        self.assert_insufficient(detail, request, 'unit_mismatch')
        detail, request = fixture(reported=1)
        find(detail, 'reported')['status'] = 'extracted'
        self.assert_insufficient(detail, request, 'claim_unreviewed')

    def test_row_search_budget_and_output_wrapper_are_enforced_before_success(self):
        detail, request = fixture('emc_field_strength')
        with patch.object(checks, '_ROW_WORK_LIMIT', 1), patch.object(calculations, 'calculate') as called:
            self.assert_error('fcc_calc_limit_exceeded', detail, request)
        called.assert_not_called()

    def test_milliwatt_display_rounding_never_creates_a_zero_tolerance_match(self):
        detail, request = fixture(reported=1, result_unit='mW')
        find(detail, 'reading')['value'] = 0
        result = checks.check_report_calculation(detail, request)
        exact = Fraction(.001) * 1000
        self.assertEqual(result['calculation']['value'], 1.)
        self.assertEqual(result['status'], 'outside_tolerance')
        self.assertEqual(result['comparison']['absolute_difference'],
                         {'numerator': '3', 'denominator': '144115188075855872'})
        self.assertEqual(result['unit_conversion']['exact_value_ratio'], {
            'numerator': str(exact.numerator), 'denominator': str(exact.denominator)})
        request['comparison_policy']['absolute_tolerance'] = float(exact - 1)
        self.assertEqual(checks.check_report_calculation(detail, request)['status'], 'within_tolerance')
        request['comparison_policy']['absolute_tolerance'] = math.nextafter(float(exact - 1), 0)
        self.assertEqual(checks.check_report_calculation(detail, request)['status'], 'outside_tolerance')

    def test_ratio_sign_zero_and_4096_bit_boundaries_are_explicit(self):
        self.assertEqual(checks._ratio(Fraction(0)), {'numerator': '0', 'denominator': '1'})
        accepted = checks._ratio(Fraction(2 ** 4096 - 1))
        self.assertLessEqual(len(accepted['numerator']), 1234)
        accepted = checks._ratio(Fraction(1, 2 ** 4095))
        self.assertLessEqual(len(accepted['denominator']), 1234)
        for value in (Fraction(-1), Fraction(2 ** 4096), Fraction(1, 2 ** 4096)):
            with self.assertRaises(checks._Gap) as caught:
                checks._ratio(value)
            self.assertEqual(caught.exception.reason, 'numeric_representation_unavailable')

    def test_en_dash_row_marker_requires_shared_lines(self):
        detail, request = fixture('emc_field_strength')
        for line, identity in enumerate(('reading', 'af', 'cable', 'gain'), 1):
            find(detail, identity)['evidence'][0].update(table='T1', row='–',
                                                      line_start=line, line_end=line)
        self.assert_insufficient(detail, request, 'row_evidence_unconfirmed')

    def test_en_dash_row_with_shared_lines_preserves_unknown_identity(self):
        detail, request = fixture('emc_field_strength')
        for identity in ('reading', 'af', 'cable', 'gain'):
            find(detail, identity)['evidence'][0].update(table='T1', row='–')
        result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(result['source_page']['row_binding'], {
            'basis': 'common_line_range', 'table': 'T1', 'row': None, 'line_start': 1, 'line_end': 1})
        self.assertEqual(result['inputs'][0]['sources'][0]['row'], '–')

    def test_equivalent_scalar_context_uses_021_fold_and_preserves_original_values(self):
        detail, request = fixture()
        for identity in ('family', 'legal', 'address'):
            duplicate = copy.deepcopy(find(detail, identity))
            duplicate['claim_id'] += '-equivalent'
            duplicate['value'] = ' ' + duplicate['value'].swapcase() + ' '
            detail['case']['claims'].append(duplicate)
        before = copy.deepcopy(detail)
        with patch.object(calculations, 'calculate', wraps=calculations.calculate) as called:
            result = checks.check_report_calculation(detail, request)
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(called.call_count, 1)
        self.assertEqual(result['context']['product_family'], before['case']['preview']['product_family'])
        self.assertEqual(detail, before)
        self.assertEqual(find(detail, 'family-equivalent')['value'], ' SYNTHETIC RADIO ')

    def test_different_folded_scalar_context_remains_unconfirmed(self):
        detail, request = fixture()
        duplicate = copy.deepcopy(find(detail, 'family'))
        duplicate.update(claim_id='family-conflict', value=' A Different Product ')
        detail['case']['claims'].append(duplicate)
        self.assert_insufficient(detail, request, 'case_context_unconfirmed')


if __name__ == '__main__':
    unittest.main()
