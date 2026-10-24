"""027 HTTP contracts: real synthetic021 catalogs; faults are explicitly injected."""
from copy import deepcopy
import hashlib
import http.client
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from reportlab.pdfgen import canvas

from labflow import ui_server
from labflow.document_extract import extract_document, page_citation
from labflow.fcc_report_cases import FccReportCaseCatalog, FccReportCaseError


def synthetic_catalog(*, empty=False):
    packet = {
        'schema_version': 1, 'corpus_id': 'SYNTHETIC-ROUTE027',
        'scope': {'issue_date_from': '2025-01-01', 'cutoff_at': '2026-10-24T12:00:00+09:00',
                  'timezone': 'Asia/Seoul', 'population_status': 'unconfirmed',
                  'search_scope_notes': ['Synthetic route contract only'],
                  'unverified_ranges': ['Population remains unknown'], 'synthetic': True},
        'searches': [], 'documents': [], 'cases': [],
    }
    if empty:
        return FccReportCaseCatalog(packet, {})
    stream = BytesIO()
    writer = canvas.Canvas(stream, invariant=1, pageCompression=0)
    writer.drawString(40, 740, 'SYNTHETIC report, power 0 dBm, enabled False')
    writer.showPage(); writer.save()
    blob = stream.getvalue()
    sha = hashlib.sha256(blob).hexdigest()
    extracted = extract_document(blob, 'synthetic.pdf')
    citation = page_citation(extracted, 1, 1, 1)
    evidence = {'document_id': 'SYN-DOC', 'source_sha256': sha, 'file_page': 1,
                'printed_page': 'unknown', 'table': None, 'row': None, 'column': None,
                'footnotes': [], 'text_sha256': citation['text_sha256'],
                'line_start': 1, 'line_end': 1, 'quote': citation['quote']}
    packet['documents'] = [{
        'document_id': 'SYN-DOC', 'sha256': sha, 'size_bytes': len(blob), 'physical_pages': 1,
        'exhibits': [{'exhibit_id': 'SYN-EXHIBIT', 'fcc_id': 'SYN-FCC', 'application_id': None,
                      'exhibit_type': 'synthetic', 'url': 'https://example.invalid/report.pdf',
                      'source_kind': 'mirror', 'accessed_at': '2026-10-24T11:00:00+09:00',
                      'official_match_status': 'blocked', 'official_url': None, 'search_ids': []}],
        'rights': {'status': 'private_only', 'notes': 'Synthetic contract, no redistribution',
                   'public_redistribution_allowed': False, 'external_model_use_allowed': False},
    }]
    packet['cases'] = [{
        'case_id': 'SYN-CASE-A', 'report_group_id': None, 'document_ids': ['SYN-DOC'],
        'claims': [{'claim_id': 'SYN-POWER', 'field': 'result.power', 'value': 0, 'unit': 'dBm',
                    'status': 'extracted', 'basis': 'report_fact', 'evidence': [deepcopy(evidence)]},
                   {'claim_id': 'SYN-ENABLED', 'field': 'setting.enabled', 'value': False, 'unit': None,
                    'status': 'extracted', 'basis': 'report_fact', 'evidence': [deepcopy(evidence)]}],
        'relations': [], 'reuse_group_ids': [],
    }]
    return FccReportCaseCatalog(packet, {sha: blob})


class FccCaseUiServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def start(self, catalog=None, *, explicit=False):
        try:
            server = (ui_server.create_server(self.tmp.name, port=0, fcc_case_catalog=catalog)
                      if explicit else ui_server.create_server(self.tmp.name, port=0))
        except TypeError as error:
            self.fail('Missing approved optional catalog injection: ' + str(error))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def close():
            server.shutdown(); server.server_close(); thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.addCleanup(close)
        return server

    def request(self, server, target, method='GET', headers=None):
        connection = http.client.HTTPConnection(*server.server_address, timeout=5)
        try:
            connection.request(method, target, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def error(self, server, target, status, code, **kwargs):
        actual, _, body = self.request(server, target, **kwargs)
        self.assertEqual(actual, status, target)
        self.assertEqual(json.loads(body), {'error': {'code': code}})
        self.assertNotIn(b'PRIVATE_CANARY', body)

    def test_unconfigured_is_explicit_503_and_does_not_import_optional021(self):
        original = ui_server.importlib.import_module

        def guarded(name, package=None):
            if name == '.fcc_report_cases':
                raise RuntimeError('PRIVATE_CANARY optional import')
            return original(name, package)
        with patch.object(ui_server.importlib, 'import_module', side_effect=guarded):
            server = self.start()
            self.error(server, '/api/fcc-cases/summary', 503, 'fcc_case_catalog_unconfigured')
            self.error(server, '/api/fcc-cases/cases/SYN-CASE-A', 503, 'fcc_case_catalog_unconfigured')
            for target in ['/', '/fcc-cases', '/fcc-cases/', '/control-sources', '/dut-controls']:
                self.assertEqual(self.request(server, target)[0], 200, target)
            self.error(server, '/api/intakes', 503, 'store_missing')

    def test_real_empty_catalog_is_success_with_null_population_and_zero_cases(self):
        server = self.start(synthetic_catalog(empty=True), explicit=True)
        status, _, body = self.request(server, '/api/fcc-cases/summary')
        self.assertEqual(status, 200)
        value = json.loads(body)
        self.assertEqual(value['counts']['case_count'], 0)
        self.assertIsNone(value['counts']['candidate_count'])
        self.assertEqual(value['case_previews'], [])
        self.assertEqual(value['scope']['population_status'], 'unconfirmed')

    def test_exact_real_api_get_and_head_preserve_false_zero_and_all_metadata(self):
        catalog = synthetic_catalog()
        summary, detail = catalog.summary(), catalog.case('SYN-CASE-A')
        server = self.start(catalog, explicit=True)
        for target, expected in [('/api/fcc-cases/summary', summary),
                                 ('/api/fcc-cases/cases/SYN-CASE-A', detail)]:
            with self.subTest(target=target):
                status, headers, body = self.request(server, target)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), expected)
                head = self.request(server, target, 'HEAD')
                self.assertEqual(head[0], 200)
                self.assertEqual(head[1]['Content-Length'], str(len(body)))
                self.assertEqual(head[2], b'')
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
                self.assertNotIn('unsafe-inline', headers['Content-Security-Policy'])
                self.assertNotIn('Access-Control-Allow-Origin', headers)
        claims = json.loads(self.request(server, '/api/fcc-cases/cases/SYN-CASE-A')[2])['case']['claims']
        self.assertEqual(type(claims[0]['value']), int)
        self.assertEqual(claims[0]['value'], 0)
        self.assertIs(claims[1]['value'], False)

    def test_invalid_injections_and_subclass_fail_with_fixed_error_before_bind(self):
        class Subclass(FccReportCaseCatalog):
            pass
        class Duck:
            def summary(self):
                raise AssertionError('PRIVATE_CANARY callback invoked')
        valid = synthetic_catalog(empty=True)
        child = object.__new__(Subclass)
        child.__dict__.update(valid.__dict__)
        for invalid in [str(Path(self.tmp.name) / 'PRIVATE_CANARY.pdf'), b'%PDF-PRIVATE_CANARY',
                        {}, [], lambda: valid, Duck(), child, 0, False]:
            with self.subTest(type=type(invalid).__name__), patch.object(ui_server, 'ThreadingHTTPServer') as bind:
                try:
                    ui_server.create_server(self.tmp.name, port=0, fcc_case_catalog=invalid)
                except Exception as error:
                    self.assertIs(type(error), ValueError)
                    self.assertEqual(error.args, ('fcc_case_catalog_invalid',))
                    self.assertIsNone(error.__context__)
                else:
                    self.fail('Invalid injection accepted')
                self.assertFalse(bind.called)

    def test_optional_import_failure_is_fixed_prebind_and_default_server_still_works(self):
        catalog = synthetic_catalog(empty=True)
        original = ui_server.importlib.import_module

        def broken(name, package=None):
            if name == '.fcc_report_cases':
                raise RuntimeError('PRIVATE_CANARY C:/private/source.pdf')
            return original(name, package)
        with patch.object(ui_server.importlib, 'import_module', side_effect=broken):
            try:
                ui_server.create_server(self.tmp.name, port=0, fcc_case_catalog=catalog)
            except Exception as error:
                self.assertIs(type(error), ValueError)
                self.assertEqual(error.args, ('fcc_case_catalog_invalid',))
                self.assertIsNone(error.__context__)
            else:
                self.fail('Import failure accepted')
            self.assertEqual(self.request(self.start(), '/')[0], 200)

    def test_requests_use_memory_without_pdf_or_packet_io_and_ignore_instance_callbacks(self):
        catalog = synthetic_catalog()
        catalog.summary = lambda: (_ for _ in ()).throw(AssertionError('PRIVATE_CANARY callback'))
        catalog.case = catalog.summary
        server = self.start(catalog, explicit=True)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('PRIVATE_CANARY disk read')):
            self.assertEqual(self.request(server, '/api/fcc-cases/summary')[0], 200)
            self.assertEqual(self.request(server, '/api/fcc-cases/cases/SYN-CASE-A')[0], 200)

    def test_raw_path_query_and_private_asset_selectors_are_not_routes(self):
        server = self.start()
        for target in ['/fcc-cases?', '/fcc-cases#', '/api/fcc-cases/summary?',
                       '/api/fcc-cases/summary?path=PRIVATE_CANARY',
                       '//fcc-cases', '//api/fcc-cases/summary', '/fcc-cases//app.js',
                       '/api/fcc-cases//summary', '/api/fcc-cases/cases/SYN-CASE-A/',
                       '/api/fcc-cases/cases/A/B', '/api/fcc-cases/cases/A%2FB',
                       '/api/fcc-cases%2Fsummary', '/api/fcc-cases/cases/A%5CB',
                       '/api/fcc-cases/cases/%', '/api/fcc-cases/cases/%ff',
                       '/fcc-cases/index.html', '/fcc-cases/route_browser_check.cjs',
                       '/fcc-cases/browser_check.cjs', '/fcc-cases/model.test.mjs',
                       '/fcc-cases/packet.json', '/fcc-cases/source.pdf',
                       '/fcc-cases/%2e%2e/packet.json']:
            with self.subTest(target=target):
                self.error(server, target, 404, 'route_not_found')
        self.error(server, f'http://127.0.0.1:{server.server_port}/fcc-cases', 404, 'route_not_found')

    def test_exact_id_validation_and_not_found_do_not_trim_or_alias(self):
        server = self.start(synthetic_catalog(), explicit=True)
        for identifier in ['', '-A', '.A', '_A', '%20SYN-CASE-A', 'SYN-CASE-A%20', '%ED%95%9C', 'A' * 129]:
            with self.subTest(identifier=identifier):
                self.error(server, '/api/fcc-cases/cases/' + identifier, 400, 'fcc_case_invalid_query')
        self.error(server, '/api/fcc-cases/cases/syn-case-a', 404, 'fcc_case_not_found')
        self.assertEqual(self.request(server, '/api/fcc-cases/cases/SYN%2DCASE-A')[0], 200)

    def test_static_allowlist_and_main_navigation_work_without_configuration(self):
        server = self.start()
        for target, mime in [('/fcc-cases', 'text/html'), ('/fcc-cases/', 'text/html'),
                             ('/fcc-cases/app.js', 'text/javascript'), ('/fcc-cases/styles.css', 'text/css'),
                             ('/fcc-cases/model.mjs', 'text/javascript'), ('/fcc-cases/view.mjs', 'text/javascript')]:
            status, headers, body = self.request(server, target)
            self.assertEqual(status, 200, target)
            self.assertTrue(headers['Content-Type'].startswith(mime))
            self.assertTrue(body)
        main = self.request(server, '/')[2].decode('utf-8')
        self.assertEqual(main.count('href="/fcc-cases"'), 1)

    def test_021_errors_are_whitelisted_and_unknown_errors_do_not_expose_details(self):
        catalog = synthetic_catalog(empty=True)
        for code, status in [('fcc_case_invalid_query', 400), ('fcc_case_not_found', 404),
                             ('fcc_case_invalid_packet', 503), ('fcc_case_invalid_sources', 503),
                             ('fcc_case_limit_exceeded', 503), ('fcc_case_pdf_invalid', 503),
                             ('fcc_case_extraction_unavailable', 503), ('fcc_case_invalid_evidence', 503),
                             ('fcc_case_invalid_intake', 503)]:
            with self.subTest(code=code), patch.object(FccReportCaseCatalog, 'summary', side_effect=FccReportCaseError(code)):
                server = self.start(catalog, explicit=True)
                self.error(server, '/api/fcc-cases/summary', status, code)
                self.assertEqual(self.request(server, '/dut-controls')[0], 200)

        class Hostile(ValueError):
            @property
            def code(self):
                raise AssertionError('PRIVATE_CANARY getter executed')
        for error in [RuntimeError('PRIVATE_CANARY C:/private/source.pdf'), Hostile('PRIVATE_CANARY')]:
            with patch.object(FccReportCaseCatalog, 'summary', side_effect=error):
                server = self.start(catalog, explicit=True)
                self.error(server, '/api/fcc-cases/summary', 503, 'fcc_case_catalog_unavailable')

    def test_response_limits_and_non_json_values_are_fixed503_before_headers(self):
        catalog = synthetic_catalog(empty=True)
        for value in [{'private': 'C:/private/PRIVATE_CANARY.pdf'}, {'value': float('nan')},
                      {'value': b'PRIVATE_CANARY'}, {'value': '\ud800'},
                      {'value': 'x' * (8 * 1024 * 1024)}, {'value': object()}]:
            payload = catalog.summary()
            payload['scope']['search_scope_notes'] = [next(iter(value.values()))]
            with self.subTest(value_type=type(next(iter(value.values()))).__name__), \
                    patch.object(FccReportCaseCatalog, 'summary', return_value=payload):
                server = self.start(catalog, explicit=True)
                self.error(server, '/api/fcc-cases/summary', 503, 'fcc_case_catalog_unavailable')
                self.assertEqual(self.request(server, '/')[0], 200)

    def test_read_only_and_origin_policy_apply_to_new_routes(self):
        server = self.start()
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            self.error(server, '/api/fcc-cases/summary', 405, 'read_only', method=method)
        for headers in [{'Host': 'attacker.invalid'}, {'Origin': 'https://attacker.invalid'},
                        {'Sec-Fetch-Site': 'cross-site'}]:
            self.error(server, '/api/fcc-cases/summary', 403, 'local_origin_required', headers=headers)


if __name__ == '__main__':
    unittest.main()
