"""Genuine synthetic catalog to scalar arithmetic; no collected source or value."""
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
import socket
import sqlite3
import sys
import unittest
from unittest.mock import patch

from pypdf import PageObject
from labflow import calculations, document_extract
from labflow import fcc_report_calculation as report_checks
from labflow.fcc_report_cases import FccReportCaseCatalog, FccReportCaseError
from tests.test_fcc_report_cases import fixture as report_fixture

try:
    service = importlib.import_module('labflow.fcc_case_calculation')
except ModuleNotFoundError as error:
    if error.name != 'labflow.fcc_case_calculation':
        raise
    service = None

CASE, READING = 'CASE-A', 'SYNTHETIC-READING-036'
RESPONSE_KEYS = {
    'schema_version', 'kind', 'corpus_id', 'case_id', 'status', 'request_context',
    'result', 'error_code', 'execution_authorized'}
CASE_CODES = (
    'fcc_case_invalid_packet', 'fcc_case_invalid_sources', 'fcc_case_limit_exceeded',
    'fcc_case_pdf_invalid', 'fcc_case_extraction_unavailable', 'fcc_case_invalid_evidence',
    'fcc_case_invalid_query', 'fcc_case_not_found', 'fcc_case_invalid_intake')
CALC_CODES = ('fcc_calc_invalid_case', 'fcc_calc_invalid_request', 'fcc_calc_limit_exceeded')
CASE_CODE = FccReportCaseCatalog.case.__wrapped__.__code__


def inputs(*, change=None, power=0, family=None, copies=1, explicit=False):
    packet, sources, make_claim = report_fixture()
    for claim in packet['cases'][0]['claims']:
        if claim['field'] == 'method.references':
            # The synthetic PDF explicitly labels Method, rather than a normative approval.
            claim['basis'] = 'report_fact'
        if claim['field'] == 'product.family' and family is not None:
            claim['value'] = family
    reading = make_claim('result.rf_power_reading', power, 13, unit='dBm')
    reading['claim_id'] = READING
    reading['evidence'] *= copies
    if explicit:
        for evidence in reading['evidence']:
            evidence.update(table='SYNTHETIC-TABLE', row='SYNTHETIC-ROW')
    if change:
        change(packet, reading)
    packet['cases'][0]['claims'].append(reading)
    catalog = FccReportCaseCatalog(packet, sources)
    request = {'schema_version': 1, 'case_id': CASE, 'calculation_request': {
        'calculator': 'rf_power', 'rule': '47 CFR 15.247', 'method': 'ANSI C63.10-2020',
        'input_claim_ids': {'reading': READING},
        'reported_result_claim_id': None, 'comparison_policy': None}}
    return catalog, request, packet, sources


def observe(function):
    codes = {
        CASE_CODE: 'case',
        report_checks.check_report_calculation.__code__: 'check',
        calculations.calculate.__code__: 'math',
        document_extract.extract_document.__code__: 'source',
        PageObject.extract_text.__code__: 'native',
    }
    counts = dict.fromkeys(codes.values(), 0)
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code in codes:
            counts[codes[frame.f_code]] += 1
    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        return function(), counts
    finally:
        sys.setprofile(previous)


class CaseCalculationTests(unittest.TestCase):
    def call(self, catalog, request):
        self.assertIsNotNone(service, '036 must implement the public case calculation service')
        return service.calculate_case_claim(catalog, request)

    def rejected(self, result, code, *, invalid=False):
        self.assertEqual(set(result), RESPONSE_KEYS)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['error_code'], code)
        self.assertIsNone(result['result'])
        self.assertFalse(result['execution_authorized'])
        if invalid:
            self.assertIsNone(result['case_id'])
            self.assertIsNone(result['request_context'])

    def test_genuine_catalog_zero_reading_uses_existing_arithmetic_once(self):
        catalog, request, _, _ = inputs()
        result, counts = observe(lambda: self.call(catalog, request))
        self.assertEqual(set(result), RESPONSE_KEYS)
        self.assertEqual(result['status'], 'calculated')
        self.assertIsNone(result['error_code'])
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['case_id'], CASE)
        self.assertEqual(result['corpus_id'], 'SYNTHETIC-CORPUS-021')
        self.assertEqual(result['request_context'], request)
        self.assertEqual(result['result']['inputs'][0]['value'], 0)
        self.assertEqual(result['result']['calculation'],
                         {'value': 0.001, 'unit': 'W', 'native_result': {'value': 0.001, 'unit': 'W'}})
        self.assertIsNone(result['result']['comparison'])
        self.assertIsNone(result['result']['reported_result'])
        self.assertEqual(counts, {'case': 1, 'check': 1, 'math': 1, 'source': 0, 'native': 0})

    def test_request_phase_has_no_file_database_socket_or_native_IO(self):
        catalog, request, _, _ = inputs()
        failure = AssertionError('request phase performed I/O')
        with patch('builtins.open', side_effect=failure), patch.object(Path, 'read_bytes', side_effect=failure), \
                patch.object(sqlite3, 'connect', side_effect=failure), \
                patch.object(socket, 'socket', side_effect=failure):
            result, counts = observe(lambda: self.call(catalog, request))
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(counts['source'], 0)
        self.assertEqual(counts['native'], 0)

    def test_only_formal_class_case_method_runs_not_instance_callback(self):
        catalog, request, _, _ = inputs()
        catalog.case = lambda *args: (_ for _ in ()).throw(AssertionError('instance callback'))
        self.assertEqual(self.call(catalog, request)['status'], 'calculated')

    def test_none_is_unconfigured_and_valid_request_is_detached(self):
        _, request, _, _ = inputs()
        result = self.call(None, request)
        self.rejected(result, 'fcc_case_catalog_unconfigured')
        self.assertEqual(result['request_context'], request)
        request['calculation_request']['rule'] = 'CHANGED'
        self.assertEqual(result['request_context']['calculation_request']['rule'], '47 CFR 15.247')

    def test_raw_DTO_subclass_duck_path_and_callback_are_not_catalogs(self):
        catalog, request, _, _ = inputs()
        class Derived(FccReportCaseCatalog):
            pass
        class Duck:
            @property
            def case(self):
                raise AssertionError('duck property invoked')
        for candidate in (catalog.case(CASE), object.__new__(Derived), Duck(),
                          Path('private-source.pdf'), b'%PDF-', lambda: catalog):
            with self.subTest(kind=type(candidate).__name__):
                result, counts = observe(lambda: self.call(candidate, request))
                self.rejected(result, 'fcc_case_catalog_invalid')
                self.assertEqual(counts['case'], 0)
                self.assertEqual(counts['math'], 0)

    def test_invalid_requests_are_not_echoed_and_never_read_case(self):
        catalog, request, _, _ = inputs()
        candidates = [None, 'not JSON object', [], dict(request, schema_version=True),
                      dict(request, schema_version=2), dict(request, case_id=' bad '),
                      dict(request, extra=False)]
        for changes in (
            {'calculator': 'emc_field_strength'}, {'rule': ''}, {'method': ' '},
            {'method': 'x' * 257}, {'rule': 'C:\\PRIVATE\\source'}, {'rule': 'https://private.invalid'},
            {'input_claim_ids': {'reading': 'bad/id'}},
            {'input_claim_ids': {'reading': READING, 'extra': READING}},
            {'reported_result_claim_id': 'INVENTED-W'},
            {'comparison_policy': {'absolute_tolerance': 0, 'unit': 'W'}},
        ):
            variant = deepcopy(request)
            variant['calculation_request'].update(changes)
            candidates.append(variant)
        for variant in candidates:
            with self.subTest(variant=type(variant).__name__):
                result, counts = observe(lambda: self.call(catalog, variant))
                self.rejected(result, 'fcc_case_calculation_invalid_request', invalid=True)
                self.assertEqual(counts['case'], 0)
                self.assertEqual(counts['check'], 0)

    def test_nonplain_objects_are_refused_without_running_hooks(self):
        catalog, request, _, _ = inputs()
        class Hostile(dict):
            def items(self):
                raise AssertionError('custom items')
        class Text(str):
            def encode(self, *args, **kwargs):
                raise AssertionError('custom encode')
        for variant in (Hostile(request), dict(request, case_id=Text(CASE)),
                        dict(request, calculation_request={'bad': object()})):
            result = self.call(catalog, variant)
            self.rejected(result, 'fcc_case_calculation_invalid_request', invalid=True)

    def test_nonfinite_and_invalid_unicode_are_refused_without_raw_data(self):
        catalog, request, _, _ = inputs()
        for value in (math.inf, math.nan, '\ud800'):
            variant = dict(request, extra=value)
            result = self.call(catalog, variant)
            self.rejected(result, 'fcc_case_calculation_invalid_request', invalid=True)
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_tree_and_encoded_request_budgets_stop_before_case(self):
        catalog, request, _, _ = inputs()
        deep = None
        for _ in range(12):
            deep = [deep]
        variants = [dict(request, extra=[None] * 600), dict(request, extra=deep),
                    dict(request, extra='😀' * 10000), dict(request, extra=2 ** 4096)]
        inner = deepcopy(request)
        inner['calculation_request']['extra'] = 'x' * 16300
        variants.append(inner)
        for variant in variants:
            result, counts = observe(lambda: self.call(catalog, variant))
            self.rejected(result, 'fcc_case_calculation_limit_exceeded', invalid=True)
            self.assertEqual(counts['case'], 0)

    def test_missing_case_preserves_parent_code_and_explicit_case_ID(self):
        catalog, request, _, _ = inputs()
        request['case_id'] = 'SYNTHETIC-MISSING'
        result, counts = observe(lambda: self.call(catalog, request))
        self.rejected(result, 'fcc_case_not_found')
        self.assertEqual(result['case_id'], 'SYNTHETIC-MISSING')
        self.assertIsNone(result['corpus_id'])
        self.assertEqual(counts['case'], 1)
        self.assertEqual(counts['check'], 0)

    def test_literal_matching_keeps_original_echo_and_parent_trim_casefold(self):
        catalog, request, _, _ = inputs()
        request['calculation_request'].update(rule='  47 cfr 15.247  ', method=' ansi c63.10-2020 ')
        result = self.call(catalog, request)
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(result['request_context'], request)
        self.assertEqual(result['result']['context']['rule'], '47 cfr 15.247')
        self.assertEqual(result['result']['context']['method'], 'ansi c63.10-2020')

    def test_wrong_units_role_review_basis_false_and_missing_are_insufficient(self):
        for changes, reason in (
            ({'unit': 'mW'}, 'unit_mismatch'),
            ({'field': 'result.rf_power'}, 'claim_role_mismatch'),
            ({'status': 'extracted'}, 'claim_unreviewed'),
            ({'basis': 'developer_inference'}, 'claim_basis_unconfirmed'),
            ({'value': False}, 'claim_type_mismatch'),
        ):
            catalog, request, _, _ = inputs(change=lambda p, r: r.update(changes))
            result, counts = observe(lambda: self.call(catalog, request))
            self.assertEqual(result['status'], 'insufficient_evidence')
            self.assertIsNone(result['error_code'])
            self.assertEqual(result['result']['reason_codes'], [reason])
            self.assertIsNone(result['result']['calculation'])
            self.assertEqual(counts['math'], 0)
        catalog, request, _, _ = inputs()
        request['calculation_request']['input_claim_ids']['reading'] = 'SYNTHETIC-MISSING'
        result = self.call(catalog, request)
        self.assertEqual(result['result']['reason_codes'], ['claim_missing'])

    def test_standard_citation_and_conflicting_case_stay_parent_insufficient(self):
        def citation(packet, reading):
            for claim in packet['cases'][0]['claims']:
                if claim['field'] == 'method.references':
                    claim['basis'] = 'standard_reference_only'
        def conflicting(packet, reading):
            for claim in packet['cases'][0]['claims']:
                if claim['field'] == 'product.family':
                    claim['status'] = 'conflicting'
        for change, reason in ((citation, 'case_context_unconfirmed'),
                               (conflicting, 'case_context_conflicting')):
            catalog, request, _, _ = inputs(change=change)
            result = self.call(catalog, request)
            self.assertEqual(result['status'], 'insufficient_evidence')
            self.assertEqual(result['result']['reason_codes'], [reason])

    def test_unrepresentable_value_keeps_confirmed_projection_and_source_page(self):
        catalog, request, _, _ = inputs(power=2 ** 53 + 1)
        result, counts = observe(lambda: self.call(catalog, request))
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['result']['reason_codes'], ['numeric_representation_unavailable'])
        self.assertEqual(result['result']['inputs'][0]['value'], 9007199254740993)
        self.assertEqual(result['result']['source_page']['file_page'], 1)
        self.assertEqual(counts['math'], 0)

    def test_partial_selected_source_and_explicit_row_are_not_discarded(self):
        catalog, request, packet, sources = inputs(explicit=True)
        identity = next(iter(sources))
        policy = {'schema_version': 1, 'sources': {identity: {
            'pages': [1], 'mode': 'native_text', 'basis_id': 'SYNTHETIC-036',
            'basis_sha256': 'a' * 64}}}
        selected = FccReportCaseCatalog(packet, sources, page_scope=policy)
        self.assertEqual(selected.case(CASE)['documents'][0]['extraction']['status'], 'partial')
        result = self.call(selected, request)
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(result['result']['source_page']['row_binding']['row'], 'SYNTHETIC-ROW')

    def test_large_legal_parent_context_is_not_truncated_to_a_smaller_UI_budget(self):
        # Parent evaluation_group adds the literal "family:" prefix to this text.
        family = '😀' * 16377
        catalog, request, _, _ = inputs(family=family, copies=8, explicit=True)
        expected = report_checks.check_report_calculation(catalog.case(CASE), request['calculation_request'])
        self.assertEqual(expected['status'], 'calculated')
        self.assertGreater(len(json.dumps(expected, ensure_ascii=False).encode('utf-8')), 65536)
        result = self.call(catalog, request)
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(result['result'], expected)
        self.assertEqual(len(result['result']['context']['product_family']), 16377)
        self.assertEqual(len(result['result']['inputs'][0]['sources']), 8)

    def test_wrapper_result_request_and_catalog_inputs_are_detached(self):
        catalog, request, packet, sources = inputs()
        before = deepcopy((request, packet, sources, catalog.case(CASE)))
        first = self.call(catalog, request)
        first['request_context']['calculation_request']['rule'] = 'CHANGED'
        first['result']['inputs'][0]['sources'][0]['row'] = 'CHANGED'
        first['result']['calculation']['native_result']['value'] = -999
        second = self.call(catalog, request)
        self.assertEqual((request, packet, sources, catalog.case(CASE)), before)
        self.assertEqual(second['result']['calculation']['value'], 0.001)
        self.assertIsNone(second['result']['inputs'][0]['sources'][0]['row'])

    def test_fixed_parent_error_codes_survive_without_exception_payloads(self):
        catalog, request, _, _ = inputs()
        for code in CASE_CODES:
            with self.subTest(code=code), patch.object(FccReportCaseCatalog, 'case',
                                                     side_effect=FccReportCaseError(code)):
                result = self.call(catalog, request)
                self.rejected(result, code, invalid=code == 'fcc_case_invalid_query')
        for code in CALC_CODES:
            with self.subTest(code=code), patch.object(report_checks, 'check_report_calculation',
                                                     side_effect=report_checks.FccReportCalculationError(code)):
                result = self.call(catalog, request)
                self.rejected(result, code, invalid=code == 'fcc_calc_invalid_request')

    def test_unknown_parent_failures_never_return_private_exception_or_code(self):
        catalog, request, _, _ = inputs()
        for target, name, code in ((FccReportCaseCatalog, 'case', 'fcc_case_catalog_unavailable'),
                                   (report_checks, 'check_report_calculation',
                                    'fcc_case_calculation_unavailable')):
            with patch.object(target, name, side_effect=RuntimeError('C:\\PRIVATE\\secret value')):
                result = self.call(catalog, request)
            self.rejected(result, code)
            self.assertNotIn('PRIVATE', json.dumps(result))
        with patch.object(report_checks, 'check_report_calculation',
                          side_effect=report_checks.FccReportCalculationError('PRIVATE-CODE')):
            result = self.call(catalog, request)
        self.rejected(result, 'fcc_case_calculation_unavailable')

    def test_wrong_case_identity_is_rejected_before_023(self):
        catalog, request, _, _ = inputs()
        detail = catalog.case(CASE)
        detail['case']['case_id'] = 'OTHER-CASE'
        with patch.object(FccReportCaseCatalog, 'case', return_value=detail):
            result, counts = observe(lambda: self.call(catalog, request))
        self.rejected(result, 'fcc_case_catalog_unavailable')
        self.assertEqual(counts['check'], 0)

    def test_full_parent_result_validation_refuses_inconsistent_or_extra_data(self):
        catalog, request, _, _ = inputs()
        golden = report_checks.check_report_calculation(catalog.case(CASE), request['calculation_request'])
        variants = []
        for key, value in (
            ('corpus_id', 'OTHER'), ('case_id', 'OTHER'), ('calculator', 'emc_field_strength'),
            ('status', 'within_tolerance'), ('synthetic', False), ('comparison_policy', {}),
            ('comparison', False), ('reported_result', {}), ('unit_conversion', {}),
            ('PRIVATE', 'C:\\PRIVATE\\source')):
            item = deepcopy(golden); item[key] = value; variants.append(item)
        item = deepcopy(golden); del item['kind']; variants.append(item)
        item = deepcopy(golden); item['verification']['hardware_verified'] = True; variants.append(item)
        item = deepcopy(golden); item['context']['method'] = 'OTHER'; variants.append(item)
        item = deepcopy(golden); item['inputs'][0]['claim_id'] = 'OTHER'; variants.append(item)
        item = deepcopy(golden); item['inputs'][0]['value'] = False; variants.append(item)
        item = deepcopy(golden); item['inputs'][0]['sources'][0]['text_sha256'] = 'f' * 64; variants.append(item)
        item = deepcopy(golden); item['source_page']['row_binding']['line_end'] = 14; variants.append(item)
        item = deepcopy(golden); item['calculation']['unit'] = 'mW'; variants.append(item)
        item = deepcopy(golden); item['calculation']['native_result']['value'] = 1; variants.append(item)
        item = deepcopy(golden); item['calculation']['value'] = math.nan; variants.append(item)
        for index, item in enumerate(variants):
            with self.subTest(mutation=index):
                with patch.object(report_checks, 'check_report_calculation', return_value=item):
                    result = self.call(catalog, request)
                self.rejected(result, 'fcc_case_calculation_unavailable')
                self.assertNotIn('PRIVATE', json.dumps(result))

    def test_bad_component_tree_or_excessive_output_is_not_a_partial_success(self):
        catalog, request, _, _ = inputs()
        golden = report_checks.check_report_calculation(catalog.case(CASE), request['calculation_request'])
        for item in (None, {'result': object()}, dict(golden, context={'private': 'x' * 140000})):
            with patch.object(report_checks, 'check_report_calculation', return_value=item):
                result = self.call(catalog, request)
            self.rejected(result, 'fcc_case_calculation_unavailable')

    def test_component_cannot_duplicate_or_drop_confirmed_source_alternatives(self):
        for count, duplicate in ((1, True), (2, False)):
            catalog, request, _, _ = inputs(copies=count)
            golden = report_checks.check_report_calculation(catalog.case(CASE), request['calculation_request'])
            changed = deepcopy(golden)
            sources = changed['inputs'][0]['sources']
            if duplicate:
                sources.append(deepcopy(sources[0]))
            else:
                sources.pop()
            with patch.object(report_checks, 'check_report_calculation', return_value=changed):
                result = self.call(catalog, request)
            self.rejected(result, 'fcc_case_calculation_unavailable')


if __name__ == '__main__':
    unittest.main()
