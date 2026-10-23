import hashlib
import http.client
import json
import tempfile
import threading
import unittest

from test_ui_read_model import IntakeFixture
from labflow.ui_server import create_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixture = IntakeFixture(self.tmp.name)
        self.server = create_server(self.fixture.store.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, method='GET', headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_http_reads_real_service_and_preserves_database(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        before = hashlib.sha256(self.fixture.store.db.read_bytes()).hexdigest()
        status, headers, body = self.request('/api/intakes/' + intake_id)
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result['intake']['bundle'], 'order')
        self.assertEqual(result['intake']['analysis']['facts']['market']['value'], 'EU')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(hashlib.sha256(self.fixture.store.db.read_bytes()).hexdigest(), before)

    def test_write_methods_and_external_hosts_are_rejected(self):
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            with self.subTest(method=method):
                self.assertEqual(self.request('/api/intakes', method)[0], 405)
        self.assertEqual(self.request('/api/intakes', headers={'Host': 'attacker.invalid'})[0], 403)
        self.assertEqual(self.request('/api/intakes', headers={'Origin': 'https://attacker.invalid'})[0], 403)
        self.assertEqual(self.request('/api/intakes', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        with self.assertRaises(ValueError):
            create_server(self.fixture.store.root, host='0.0.0.0', port=0)

    def test_unknown_ids_queries_and_file_traversal_are_not_data_access(self):
        self.assertEqual(self.request('/api/intakes/I-absent')[0], 404)
        for path in ['/../labflow/store.py', '/%2e%2e/labflow/store.py', '/labflow/store.py',
                     '/api/intakes?workspace=elsewhere', '/api/intakes/a%2fb', '/api/intakes/']:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_broken_store_returns_error_instead_of_empty_success(self):
        self.fixture.store.db.write_bytes(b'broken')
        status, _, body = self.request('/api/intakes')
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'error': {'code': 'store_unavailable'}})


if __name__ == '__main__':
    unittest.main()
