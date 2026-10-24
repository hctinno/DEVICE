"""027 HTTP contracts: real synthetic021 catalogs; faults are explicitly injected."""
from copy import deepcopy
import hashlib
import http.client
from io import BytesIO
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from reportlab.pdfgen import canvas

from labflow import ui_server
from labflow.document_extract import extract_document, page_citation
from labflow.fcc_report_cases import FccReportCaseCatalog, FccReportCaseError


def synthetic_catalog(*, empty=False, rich=False, large=False):
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
    if rich or large:
        rows = [('report.number', 'SYNTHETIC-REPORT'), ('issuer.classification', 'hct_korea'),
                ('issuer.legal_name', 'SYNTHETIC issuer'), ('issuer.address', 'SYNTHETIC address'),
                ('report.issue_date', '2025-05-01'), ('product.family', 'smartphone'),
                ('product.models', ['SYNTHETIC-MODEL']), ('method.rules', ['47 CFR 15.247']),
                ('method.references', ['SYNTHETIC METHOD 2020'])]
        for i, (field, value) in enumerate(rows):
            packet['cases'][0]['claims'].append({
                'claim_id': 'SYN-RICH-' + str(i), 'field': field, 'value': value, 'unit': None,
                'status': 'reviewed', 'basis': 'developer_inference' if field == 'issuer.classification'
                else 'standard_reference_only' if field == 'method.references' else 'report_fact',
                'evidence': [deepcopy(evidence)]})
        if large:
            for field, count, lead in [('method.references', 127, 'SYNTHETIC-METHOD-'),
                                       ('product.models', 39, 'SYNTHETIC-MODEL-')]:
                row = next(c for c in packet['cases'][0]['claims'] if c['field'] == field)
                row['value'] += [lead + str(i) + '-' + 'X' * 15950 for i in range(count)]
    return FccReportCaseCatalog(packet, {sha: blob})


LOOKUP_QUERY = {'product_family': 'smartphone', 'rule': '47 CFR 15.247',
                'method': 'SYNTHETIC METHOD 2020', 'model': 'SYNTHETIC-MODEL'}


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

    def test_lookup_uses_two_formal_methods_once_and_returns_exact_envelope_and_head(self):
        catalog = synthetic_catalog(rich=True)
        expected = {'schema_version': 1, 'kind': 'fcc_report_case_lookup',
                    'search': catalog.search(LOOKUP_QUERY), 'discovery': catalog.discover(LOOKUP_QUERY)}
        original_search, original_discover = FccReportCaseCatalog.search, FccReportCaseCatalog.discover
        calls = []
        def search(instance, query):
            calls.append(('search', deepcopy(query))); return original_search(instance, query)
        def discover(instance, query):
            calls.append(('discover', deepcopy(query))); return original_discover(instance, query)
        catalog.search = catalog.discover = lambda *_: (_ for _ in ()).throw(AssertionError('PRIVATE_CANARY callback'))
        with patch.object(FccReportCaseCatalog, 'search', search), patch.object(FccReportCaseCatalog, 'discover', discover):
            server = self.start(catalog, explicit=True)
            target = '/api/fcc-cases/lookup?' + urlencode(LOOKUP_QUERY)
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('PRIVATE_CANARY original read')):
                status, headers, body = self.request(server, target)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), expected)
            self.assertEqual(calls, [('search', LOOKUP_QUERY), ('discover', LOOKUP_QUERY)])
            head = self.request(server, target, 'HEAD')
            self.assertEqual(head[0], 200); self.assertEqual(head[2], b'')
            self.assertEqual(head[1]['Content-Length'], str(len(body)))
            self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_lookup_missing_blank_partial_and_unicode_queries_keep_original_statuses(self):
        server = self.start(synthetic_catalog(rich=True), explicit=True)
        for suffix in ['', '?', '?model=']:
            status, _, body = self.request(server, '/api/fcc-cases/lookup' + suffix)
            self.assertEqual(status, 200)
            value = json.loads(body)
            self.assertEqual(value['search']['status'], 'insufficient_evidence')
            self.assertEqual(value['discovery']['status'], 'insufficient_context')
        status, _, body = self.request(server, '/api/fcc-cases/lookup?model=SYNTHETIC-MODEL')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['discovery']['items'][0]['criteria']['rule']['status'], 'not_requested')
        query = {key: '\U0001f9ea' * 256 for key in LOOKUP_QUERY}
        target = '/api/fcc-cases/lookup?' + urlencode(query)
        self.assertGreater(len(target), 4096)
        status, _, body = self.request(server, target)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['discovery']['query'], query)

    def test_lookup_query_failures_are400_and_other_paths_stay_strict404(self):
        server = self.start()
        for query in ['unknown=x', 'model=A&model=B', 'model=%', 'model=%ff', 'model=++',
                      urlencode({'model': '\U0001f9ea' * 257}), 'model=' + 'a' * 16384,
                      'product_family=&rule=&method=&model=&x=1']:
            self.error(server, '/api/fcc-cases/lookup?' + query, 400, 'fcc_case_invalid_query')
        for target in ['/api/fcc-cases/lookup/', '//api/fcc-cases/lookup', '/api/fcc-cases/lookup%2F',
                       '/api/fcc-cases/lookup#', '/api/fcc-cases/summary?model=A', '/fcc-cases?model=A']:
            self.error(server, target, 404, 'route_not_found')
        self.error(server, '/api/fcc-cases/lookup', 503, 'fcc_case_catalog_unconfigured')

    def test_lookup_failure_never_publishes_partial_and_other_readers_remain_available(self):
        catalog = synthetic_catalog(rich=True)
        with patch.object(FccReportCaseCatalog, 'discover', side_effect=RuntimeError('PRIVATE_CANARY source')):
            server = self.start(catalog, explicit=True)
            self.error(server, '/api/fcc-cases/lookup?' + urlencode(LOOKUP_QUERY), 503, 'fcc_case_catalog_unavailable')
            self.assertEqual(self.request(server, '/api/fcc-cases/summary')[0], 200)
            self.assertEqual(self.request(server, '/api/fcc-cases/cases/SYN-CASE-A')[0], 200)
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            self.error(server, '/api/fcc-cases/lookup', 405, 'read_only', method=method)

    def test_lookup_accepts_real_parent_large_values_and_envelope_larger_than8mib(self):
        catalog = synthetic_catalog(large=True)
        search, discovery = catalog.search(LOOKUP_QUERY), catalog.discover(LOOKUP_QUERY)
        compact = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.assertLess(len(compact(search)), 8 * 1024**2)
        self.assertLess(len(compact(discovery)), 8 * 1024**2)
        expected = {'schema_version': 1, 'kind': 'fcc_report_case_lookup', 'search': search, 'discovery': discovery}
        self.assertGreater(len(compact(expected)), 8 * 1024**2)
        server = self.start(catalog, explicit=True)
        status, _, body = self.request(server, '/api/fcc-cases/lookup?' + urlencode(LOOKUP_QUERY))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), expected)
        self.assertLessEqual(len(body), 16 * 1024**2 + 1024)

    def test_lookup_rejects_invalid_inner_response_and_preserves_existing8mib_cap(self):
        catalog = synthetic_catalog(rich=True)
        invalid = catalog.discover(LOOKUP_QUERY); invalid['query']['model'] = 'X' * (8 * 1024**2)
        with patch.object(FccReportCaseCatalog, 'discover', return_value=invalid):
            server = self.start(catalog, explicit=True)
            self.error(server, '/api/fcc-cases/lookup?' + urlencode(LOOKUP_QUERY), 503, 'fcc_case_catalog_unavailable')
        for target in ['/fcc-cases/discovery_model.mjs', '/fcc-cases/discovery_view.mjs']:
            self.assertEqual(self.request(server, target)[0], 200)
        self.error(server, '/fcc-cases/discovery_model.test.mjs', 404, 'route_not_found')


class FccCaseCalculationUiServerTests(unittest.TestCase):
    """039 genuine synthetic service versus bounded transport; collected source0."""
    setUp = FccCaseUiServerTests.setUp
    start = FccCaseUiServerTests.start
    request = FccCaseUiServerTests.request
    error = FccCaseUiServerTests.error

    def inputs(self, **kwargs):
        from tests.test_fcc_case_calculation import inputs
        return inputs(**kwargs)[:2]

    def post(self, server, body=b'{}', *, headers=None, target='/api/fcc-cases/calculations', short=False):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
        if headers is None:
            headers = [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))]
        connection = http.client.HTTPConnection(*server.server_address, timeout=8)
        try:
            # One packet avoids a Windows race: the intentionally invalid header
            # can be rejected before http.client sends its separate body packet.
            connection.connect()
            rows = ['POST ' + target + ' HTTP/1.1',
                    'Host: 127.0.0.1:' + str(server.server_port)]
            rows += [key + ': ' + value for key, value in headers]
            connection.sock.sendall(('\r\n'.join(rows) + '\r\n\r\n').encode('ascii') + body)
            if short:
                connection.sock.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(connection.sock)
            response.begin()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_none_fresh_process_keeps021036_import0_and_static503(self):
        program = '''
import http.client,json,sys,tempfile,threading
from labflow.ui_server import create_server
with tempfile.TemporaryDirectory() as workspace:
 server=create_server(workspace,port=0)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  connection=http.client.HTTPConnection(*server.server_address,timeout=5)
  connection.request('POST','/api/fcc-cases/calculations',body=b'{}',headers={'Content-Type':'application/json'})
  response=connection.getresponse();status=response.status;body=json.loads(response.read());connection.close()
  print(json.dumps({'status':status,'body':body,'021':'labflow.fcc_report_cases' in sys.modules,'036':'labflow.fcc_case_calculation' in sys.modules}))
 finally:
  server.shutdown();server.server_close();thread.join(5)
  assert not thread.is_alive()
'''
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-c', program],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
        self.assertEqual(json.loads(result.stdout), {'status': 503,
            'body': {'error': {'code': 'fcc_case_catalog_unconfigured'}}, '021': False, '036': False})

    def test_genuine_post_exact036_once_and_no_store_or_execution_authority(self):
        from labflow import fcc_case_calculation as service
        catalog, command = self.inputs()
        expected = service.calculate_case_claim(catalog, command)
        with patch.object(service, 'calculate_case_claim', wraps=service.calculate_case_claim) as observed:
            server = self.start(catalog, explicit=True)
            status, headers, body = self.post(server, command)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), expected)
        self.assertEqual(observed.call_count, 1)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['Content-Length'], str(len(body)))
        self.assertFalse(expected['execution_authorized'])
        self.assertEqual(expected['result']['inputs'][0]['value'], 0)

    def test_insufficient_and_service_rejected_are200_and_invalid_context_is_null(self):
        catalog, command = self.inputs()
        server = self.start(catalog, explicit=True)
        wrong_rule = deepcopy(command); wrong_rule['calculation_request']['rule'] += '-OTHER'
        status, _, body = self.post(server, wrong_rule)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['status'], 'insufficient_evidence')
        self.assertIsNone(json.loads(body)['result']['calculation'])
        invalid = deepcopy(command); invalid['schema_version'] = True
        status, _, body = self.post(server, invalid)
        value = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(value['error_code'], 'fcc_case_calculation_invalid_request')
        self.assertEqual(value['status'], 'rejected')
        self.assertIsNone(value['request_context']); self.assertIsNone(value['case_id'])
        missing = deepcopy(command); missing['case_id'] = 'SYNTH-MISSING'
        status, _, body = self.post(server, missing)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['error_code'], 'fcc_case_not_found')
        self.assertEqual(json.loads(body)['request_context'], missing)

    def test_calculation_get_head_post_only_and_other405_policies_preserved(self):
        catalog, command = self.inputs(); server = self.start(catalog, explicit=True)
        get_status, headers, get_body = self.request(server, '/api/fcc-cases/calculations')
        self.assertEqual(get_status, 405); self.assertEqual(headers['Allow'], 'POST')
        head_status, head_headers, head_body = self.request(server, '/api/fcc-cases/calculations', method='HEAD')
        self.assertEqual(head_status, 405); self.assertEqual(head_body, b'')
        self.assertEqual(head_headers['Content-Length'], str(len(get_body)))
        for target in ['/', '/api/fcc-cases/summary', '/api/fcc-cases/lookup',
                       '/api/fcc-cases/calculations?x=1', '/api/fcc-cases//calculations',
                       '/api/fcc-cases/%63alculations', '/api/fcc-cases/calculations/']:
            status, _, body = self.post(server, command, target=target)
            self.assertEqual(status, 405, target)
            self.assertEqual(json.loads(body), {'error': {'code': 'read_only'}})
        for method in ['PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            self.assertEqual(self.request(server, '/api/fcc-cases/calculations', method=method)[0], 405)
        for target in ['/api/fcc-cases/summary', '/api/fcc-cases/cases/' + command['case_id']]:
            self.assertEqual(self.request(server, target)[0], 200)

    def test_wire_headers_json_depth_nodes_are_bounded_before_service(self):
        from labflow import fcc_case_calculation as service
        catalog, _ = self.inputs()
        variants = [
            (b'{}', [('Content-Type', 'application/json')], 411, 'fcc_case_calculation_invalid_request'),
            (b'{}', [('Content-Type', 'text/plain'), ('Content-Length', '2')], 415, 'fcc_case_calculation_invalid_request'),
            (b'{}', [('Content-Type', 'application/json'), ('Content-Length', '2'), ('Content-Length', '2')], 400, 'fcc_case_calculation_invalid_request'),
            (b'{}', [('Content-Type', 'application/json'), ('Content-Length', '2'), ('Transfer-Encoding', 'chunked')], 400, 'fcc_case_calculation_invalid_request'),
            (b'{}', [('Content-Type', 'application/json'), ('Content-Length', '2'), ('Expect', '100-continue')], 417, 'fcc_case_calculation_invalid_request'),
            (b'', [('Content-Type', 'application/json'), ('Content-Length', '-1')], 400, 'fcc_case_calculation_invalid_request'),
            (b'', [('Content-Type', 'application/json'), ('Content-Length', '65537')], 413, 'fcc_case_calculation_limit_exceeded'),
            (b'{}', [('Content-Type', 'application/json'), ('Content-Length', '2'), ('Content-Encoding', 'gzip')], 415, 'fcc_case_calculation_invalid_request'),
        ]
        for body in [b'\xef\xbb\xbf{}', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":"\\ud800"}', b'{}x']:
            variants.append((body, [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))], 400, 'fcc_case_calculation_invalid_request'))
        for body in [('[' * 33 + '0' + ']' * 33).encode(), ('[' + ','.join(['null'] * 4096) + ']').encode()]:
            variants.append((body, [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))], 413, 'fcc_case_calculation_limit_exceeded'))
        with patch.object(service, 'calculate_case_claim', side_effect=AssertionError('PRIVATE_CANARY')) as observed:
            server = self.start(catalog, explicit=True)
            for body, headers, expected_status, code in variants:
                with self.subTest(status=expected_status, body_bytes=len(body)):
                    status, response_headers, raw = self.post(server, body, headers=headers)
                    self.assertEqual(status, expected_status)
                    self.assertEqual(json.loads(raw), {'error': {'code': code}})
                    self.assertEqual(response_headers['Cache-Control'], 'no-store')
                    self.assertNotIn(b'PRIVATE_CANARY', raw)
            self.assertEqual(observed.call_count, 0)

    def test_new_post_same_origin_is_strict_without_relaxing_existing_guards(self):
        catalog, command = self.inputs(); server = self.start(catalog, explicit=True)
        for origin in ['https://example.invalid', 'http://localhost:' + str(server.server_port)]:
            raw = json.dumps(command).encode()
            status, _, body = self.post(server, raw, headers=[('Content-Type', 'application/json'),
                ('Content-Length', str(len(raw))), ('Origin', origin)])
            self.assertEqual(status, 403)
            self.assertEqual(json.loads(body), {'error': {'code': 'local_origin_required'}})
        for site in ['cross-site', 'same-site']:
            status, _, _ = self.post(server, b'{}', headers=[('Content-Type', 'application/json'),
                ('Content-Length', '2'), ('Sec-Fetch-Site', site)])
            self.assertEqual(status, 403)

    def test_short_and_timed_out_body_fail_closed_before_service(self):
        from labflow import fcc_case_calculation as service
        catalog, _ = self.inputs()
        with patch.object(service, 'calculate_case_claim', side_effect=AssertionError('PRIVATE_CANARY')) as observed:
            server = self.start(catalog, explicit=True)
            headers = [('Content-Type', 'application/json'), ('Content-Length', '10')]
            status, _, body = self.post(server, b'{}', headers=headers, short=True)
            self.assertEqual(status, 400)
            self.assertEqual(json.loads(body), {'error': {'code': 'fcc_case_calculation_invalid_request'}})
            status, _, body = self.post(server, b'{}', headers=headers)
            self.assertEqual(status, 408)
            self.assertEqual(json.loads(body), {'error': {'code': 'fcc_case_calculation_unavailable'}})
            self.assertEqual(observed.call_count, 0)

    def test_genuine_long_parent_result_and_echo_not_narrowed_and_bad_output_sanitized(self):
        from labflow import fcc_case_calculation as service
        catalog, command = self.inputs(family='𠮷' * 16370, copies=8, explicit=True)
        expected = service.calculate_case_claim(catalog, command)
        self.assertEqual(expected['status'], 'calculated')
        self.assertGreater(len(json.dumps(expected['result'], ensure_ascii=False).encode('utf-8')), 65536)
        server = self.start(catalog, explicit=True)
        status, _, body = self.post(server, command)
        self.assertEqual(status, 200); self.assertEqual(json.loads(body), expected)
        bad = deepcopy(expected); bad['execution_authorized'] = True
        with patch.object(service, 'calculate_case_claim', return_value=bad):
            other = self.start(catalog, explicit=True)
            status, _, body = self.post(other, command)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'error': {'code': 'fcc_case_calculation_unavailable'}})

    def test_optional036_failure_keeps_old_get_and_only_new_assets_are_served(self):
        catalog, command = self.inputs(); original = ui_server.importlib.import_module
        def fault(name, package=None):
            if name == '.fcc_case_calculation':
                raise RuntimeError('PRIVATE_CANARY')
            return original(name, package)
        with patch.object(ui_server.importlib, 'import_module', side_effect=fault):
            server = self.start(catalog, explicit=True)
            self.assertEqual(self.request(server, '/api/fcc-cases/summary')[0], 200)
            status, _, body = self.post(server, command)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'error': {'code': 'fcc_case_calculation_unavailable'}})
        for target in ['/fcc-cases/calculation_model.mjs', '/fcc-cases/calculation_view.mjs']:
            self.assertEqual(self.request(server, target)[0], 200)
        for target in ['/fcc-cases/calculation_model.test.mjs', '/fcc-cases/calculation_browser_check.cjs']:
            self.assertEqual(self.request(server, target)[0], 404)


if __name__ == '__main__':
    unittest.main()
