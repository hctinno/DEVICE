"""DUT HTTP binding/boundary tests use a contract double, not actual API evidence."""
import http.client
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from labflow.ui_server import create_server


class DutError(ValueError):
    def __init__(self, code):
        super().__init__('PRIVATE_DUT_PATH_CANARY')
        self.code = code


class DutDouble:
    created = 0
    broken = False
    delay = 0

    def __init__(self):
        type(self).created += 1
        time.sleep(type(self).delay)
        if type(self).broken:
            raise RuntimeError('PRIVATE_DUT_PATH_CANARY')
        self.ready = True

    def summary(self):
        assert self.ready
        return {'method': 'summary'}

    def routes(self):
        return [{'backend': 'adb'}]

    def route(self, backend):
        if backend == 'missing_route':
            raise DutError('dut_catalog_item_not_found')
        if backend == 'broken_route':
            class BrokenCode(ValueError):
                @property
                def code(self):
                    raise RuntimeError('PRIVATE_DUT_ERROR_CANARY')
            raise BrokenCode()
        return {'backend': backend}

    def source(self, source_id):
        if source_id == 'DUT-G99':
            raise DutError('dut_catalog_item_not_found')
        return {'source_id': source_id}

    def manufacturing_references(self):
        return {'method': 'manufacturing_references'}


class DutControlUiServerTests(unittest.TestCase):
    def setUp(self):
        DutDouble.created = 0
        DutDouble.broken = False
        DutDouble.delay = 0
        fake = types.ModuleType('labflow.dut_control_catalog')
        fake.DutControlCatalog = DutDouble
        fake.DutControlCatalogError = DutError
        self.module_patch = patch.dict(sys.modules, {'labflow.dut_control_catalog': fake})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = create_server(self.tmp.name, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())

    def request(self, target, method='GET', headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, target, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_only_allowlisted_static_assets_are_served_without_dut_initialization(self):
        for target in ['/dut-controls', '/dut-controls/', '/dut-controls/styles.css',
                       '/dut-controls/app.js', '/dut-controls/model.mjs', '/', '/control-sources']:
            with self.subTest(target=target):
                self.assertEqual(self.request(target)[0], 200)
        self.assertEqual(self.request('/dut-controls/browser_check.cjs')[0], 404)
        self.assertEqual(self.request('/dut-controls/model.test.mjs')[0], 404)
        self.assertEqual(DutDouble.created, 0)

    def test_all_five_get_bindings_and_head_lengths_match_the_api_methods(self):
        for target, expected in [('/summary', {'method': 'summary'}), ('/routes', [{'backend': 'adb'}]),
                                 ('/routes/adb', {'backend': 'adb'}), ('/sources/DUT-G01', {'source_id': 'DUT-G01'}),
                                 ('/manufacturing-references', {'method': 'manufacturing_references'})]:
            with self.subTest(target=target):
                status, headers, body = self.request('/api/dut-controls' + target)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), expected)
                head = self.request('/api/dut-controls' + target, 'HEAD')
                self.assertEqual(head[0], 200)
                self.assertEqual(head[1]['Content-Length'], str(len(body)))
                self.assertEqual(head[2], b'')
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertIn("connect-src 'self'", headers['Content-Security-Policy'])
                self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(DutDouble.created, 1)

    def test_raw_target_rejection_does_not_open_separators_queries_or_file_paths(self):
        for target in ['/dut-controls?query=x', '/api/dut-controls/summary?x=1',
                       '/api/dut-controls/routes//adb', '/api/dut-controls/routes%2Fadb',
                       '/api/dut-controls/routes/%61db%2Fextra', '/api/dut-controls/sources/DUT-G01%5Cfile',
                       '/api/dut-controls/routes/%', '/api/dut-controls/routes/%FF',
                       '/api/dut-controls/unknown', '/api/dut-controls/routes#fragment',
                       '/dut-controls/%2e%2e/labflow/store.py', 'http://example.invalid/api/dut-controls/summary']:
            with self.subTest(target=target):
                headers = {'Host': '127.0.0.1:' + str(self.server.server_port)}
                self.assertEqual(self.request(target, headers=headers)[0], 404)
        self.assertEqual(DutDouble.created, 0)

    def test_typed_ids_are_checked_before_loading_and_decoded_only_once(self):
        for target in ['/routes/ADB', '/routes/9adb', '/routes/', '/sources/DUT-X01',
                       '/sources/DUT-G1', '/sources/dut-g01', '/sources/', '/sources/DUT%252FG01']:
            with self.subTest(target=target):
                status, _, body = self.request('/api/dut-controls' + target)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(body), {'error': {'code': 'dut_catalog_invalid_query'}})
        self.assertEqual(DutDouble.created, 0)
        self.assertEqual(self.request('/api/dut-controls/sources/%44UT-G01')[0], 200)
        self.assertEqual(self.request('/api/dut-controls/routes/%61db')[0], 200)

    def test_known_missing_ids_and_unexpected_errors_are_sanitized_with_head_parity(self):
        for target, status, code in [('/routes/missing_route', 404, 'dut_catalog_item_not_found'),
                                    ('/sources/DUT-G99', 404, 'dut_catalog_item_not_found'),
                                    ('/routes/broken_route', 503, 'dut_catalog_unavailable')]:
            with self.subTest(target=target):
                get = self.request('/api/dut-controls' + target)
                head = self.request('/api/dut-controls' + target, 'HEAD')
                self.assertEqual(get[0], status)
                self.assertEqual(json.loads(get[2]), {'error': {'code': code}})
                self.assertEqual(head[0], status)
                self.assertEqual(head[1]['Content-Length'], str(len(get[2])))
                self.assertEqual(head[2], b'')

    def test_failed_lazy_load_can_retry_and_does_not_block_other_readers(self):
        from labflow.store import Store
        Store(self.tmp.name)
        DutDouble.broken = True
        failed = self.request('/api/dut-controls/summary')
        self.assertEqual(failed[0], 503)
        self.assertEqual(json.loads(failed[2]), {'error': {'code': 'dut_catalog_unavailable'}})
        self.assertEqual(self.request('/api/intakes')[0], 200)
        self.assertEqual(self.request('/api/control-sources/summary')[0], 200)
        self.assertEqual(self.request('/api/control-sources?query=DMM6500')[0], 200)
        DutDouble.broken = False
        self.assertEqual(self.request('/api/dut-controls/summary')[0], 200)

    def test_concurrent_first_requests_publish_only_one_complete_snapshot(self):
        DutDouble.delay = .1
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.request('/api/dut-controls/summary'), range(6)))
        self.assertEqual([response[0] for response in results], [200] * 6)
        self.assertEqual(DutDouble.created, 1)

    def test_origin_and_write_boundaries_stay_read_only(self):
        for headers in [{'Host': 'attacker.invalid'}, {'Origin': 'https://attacker.invalid'},
                        {'Sec-Fetch-Site': 'cross-site'}]:
            self.assertEqual(self.request('/api/dut-controls/summary', headers=headers)[0], 403)
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            self.assertEqual(self.request('/api/dut-controls/summary', method)[0], 405)
        self.assertEqual(DutDouble.created, 0)


if __name__ == '__main__':
    unittest.main()
