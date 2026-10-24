"""HTTP boundaries use a contract double until the catalog API is integrated."""
import http.client
import json
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from labflow.ui_server import create_server


class CatalogError(ValueError):
    def __init__(self, code):
        super().__init__('PRIVATE_PATH_CANARY')
        self.code = code


class CatalogDouble:
    created = 0
    broken = False
    delay = 0

    def __init__(self):
        type(self).created += 1
        time.sleep(type(self).delay)
        if type(self).broken:
            raise RuntimeError('PRIVATE_PATH_CANARY')
        self.ready = True

    def summary(self):
        assert self.ready
        return {'kind': 'control_source_summary', 'item_count': 3137}

    def find_items(self, *, query='', scope=None, model_id=None, equipment_id=None,
                   profile_id=None, offset=0, limit=25):
        return {'query': query, 'scope': scope, 'model_id': model_id,
                'equipment_id': equipment_id, 'profile_id': profile_id,
                'offset': offset, 'limit': limit}

    def detail(self, item_id):
        if item_id == 'missing':
            raise CatalogError('catalog_item_not_found')
        if item_id == 'broken':
            raise RuntimeError('PRIVATE_PATH_CANARY')
        if item_id == 'broken-code':
            class UnexpectedError(ValueError):
                @property
                def code(self):
                    raise RuntimeError('PRIVATE_ERROR_PROPERTY_CANARY')
            raise UnexpectedError()
        return {'item_id': item_id}


class ControlSourceServerTests(unittest.TestCase):
    def setUp(self):
        CatalogDouble.created = 0
        CatalogDouble.broken = False
        CatalogDouble.delay = 0
        fake = types.ModuleType('labflow.control_source_catalog')
        fake.ControlSourceCatalog = CatalogDouble
        fake.ControlSourceCatalogError = CatalogError
        self.module_patch = patch.dict(sys.modules, {'labflow.control_source_catalog': fake})
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

    def test_static_page_assets_and_intake_do_not_initialize_catalog(self):
        for target in ['/control-sources', '/control-sources/', '/control-sources/styles.css',
                       '/control-sources/app.js', '/control-sources/model.mjs', '/']:
            with self.subTest(target=target):
                self.assertEqual(self.request(target)[0], 200)
        self.assertEqual(self.request('/api/intakes')[0], 503)
        self.assertEqual(CatalogDouble.created, 0)
        self.assertEqual(self.request('/control-sources/browser_check.cjs')[0], 404)

    def test_summary_list_detail_and_head_share_read_only_headers(self):
        for target in ['/api/control-sources/summary', '/api/control-sources',
                       '/api/control-sources/MOD-001']:
            with self.subTest(target=target):
                status, headers, body = self.request(target)
                self.assertEqual(status, 200)
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertIn("connect-src 'self'", headers['Content-Security-Policy'])
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertNotIn('Access-Control-Allow-Origin', headers)
                head = self.request(target, 'HEAD')
                self.assertEqual(head[0], status)
                self.assertEqual(head[1]['Content-Length'], str(len(body)))
                self.assertEqual(head[2], b'')
        self.assertEqual(CatalogDouble.created, 1)

    def test_bounded_utf8_query_is_typed_and_decoded_once(self):
        target = ('/api/control-sources?query=%ED%95%9C%EA%B8%80+N9030A&scope=included'
                  '&model_id=MOD-1&equipment_id=EQ-1&profile_id=fsv40&offset=25&limit=10')
        status, _, body = self.request(target)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'query': '한글 N9030A', 'scope': 'included',
            'model_id': 'MOD-1', 'equipment_id': 'EQ-1', 'profile_id': 'fsv40', 'offset': 25, 'limit': 10})
        self.assertEqual(self.request('/api/control-sources/%4dOD-1')[0], 200)
        self.assertEqual(self.request('/api/control-sources/MOD%252f1')[0], 400)

    def test_bad_query_forms_are_400_without_loading_catalog(self):
        queries = ['offset=', 'limit=', 'offset=true', 'offset=-1', 'offset=1.5', 'limit=0',
                   'limit=101', 'offset=1000001', 'limit=%2B1', 'unknown=x', 'scope=all',
                   'scope=', 'model_id=', 'model_id=a%2Fb', 'equipment_id=%FF',
                   'query=%', 'query=%xz', 'query=%C0%AF', 'query=%E3%81',
                   'query=a&%71uery=b', 'limit=1&limit=2', 'query', '=value',
                   'query=' + 'a' * 201, 'query=' + 'a' * 4096, '&'.join('q'+str(n)+'=x' for n in range(9))]
        for query in queries:
            with self.subTest(query=query[:100]):
                status, _, body = self.request('/api/control-sources?' + query)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(body), {'error': {'code': 'catalog_invalid_query'}})
        self.assertEqual(CatalogDouble.created, 0)

    def test_raw_request_target_bytes_must_be_utf8(self):
        def raw_request(target):
            with socket.create_connection(self.server.server_address, timeout=5) as connection:
                host = ('127.0.0.1:' + str(self.server.server_port)).encode('ascii')
                connection.sendall(b'GET ' + target + b' HTTP/1.1\r\nHost: ' + host + b'\r\nConnection: close\r\n\r\n')
                response = http.client.HTTPResponse(connection)
                response.begin()
                return response.status, response.read()
        self.assertEqual(raw_request(b'/api/control-sources?query=\xff')[0], 400)
        status, body = raw_request(b'/api/control-sources?query=' + '한글'.encode('utf-8'))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['query'], '한글')

    def test_query_and_traversal_remain_closed_on_other_routes(self):
        for target in ['/api/intakes?limit=1', '/?query=x', '/control-sources?query=x',
                       '/api/control-sources/summary?query=x', '/api/control-sources/MOD-1?query=x',
                       '/api/control-sources#fragment', 'http://example.invalid/api/control-sources',
                       '/control-sources/../store.py', '/control-sources/%2e%2e/store.py']:
            with self.subTest(target=target):
                headers = {'Host': '127.0.0.1:' + str(self.server.server_port)}
                self.assertEqual(self.request(target, headers=headers)[0], 404)

    def test_host_origin_and_write_boundaries_are_preserved(self):
        for headers in [{'Host': 'attacker.invalid'}, {'Origin': 'https://attacker.invalid'},
                        {'Sec-Fetch-Site': 'cross-site'}]:
            self.assertEqual(self.request('/api/control-sources', headers=headers)[0], 403)
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            self.assertEqual(self.request('/api/control-sources', method)[0], 405)
        self.assertEqual(CatalogDouble.created, 0)

    def test_catalog_errors_are_sanitized_and_unknown_id_is_404(self):
        for item, status, code in [('missing', 404, 'catalog_item_not_found'),
                                   ('broken', 503, 'catalog_unavailable'),
                                   ('broken-code', 503, 'catalog_unavailable')]:
            response = self.request('/api/control-sources/' + item)
            self.assertEqual(response[0], status)
            self.assertEqual(json.loads(response[2]), {'error': {'code': code}})
            self.assertNotIn(b'PRIVATE', response[2])

    def test_lazy_failure_is_retryable_and_does_not_break_intake(self):
        from labflow.store import Store
        Store(self.tmp.name)
        CatalogDouble.broken = True
        self.assertEqual(self.request('/api/control-sources/summary')[0], 503)
        self.assertIn(b'catalog_unavailable', self.request('/api/control-sources/summary')[2])
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/api/intakes')[0], 200)
        self.assertEqual(json.loads(self.request('/api/intakes')[2])['intakes'], [])
        CatalogDouble.broken = False
        self.assertEqual(self.request('/api/control-sources/summary')[0], 200)

    def test_concurrent_first_requests_share_only_a_complete_instance(self):
        CatalogDouble.delay = .1
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.request('/api/control-sources/summary'), range(6)))
        self.assertEqual([response[0] for response in results], [200] * 6)
        self.assertEqual(CatalogDouble.created, 1)

    def test_head_errors_have_get_status_length_and_no_body(self):
        for target in ['/api/control-sources/missing', '/api/control-sources/broken', '/api/control-sources?limit=0']:
            with self.subTest(target=target):
                get = self.request(target)
                head = self.request(target, 'HEAD')
                self.assertEqual(head[0], get[0])
                self.assertEqual(head[1]['Content-Length'], str(len(get[2])))
                self.assertEqual(head[2], b'')


if __name__ == '__main__':
    unittest.main()
