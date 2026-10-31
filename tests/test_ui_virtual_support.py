"""Actual fixed catalog -> owned HTTP cache, with no Store or bench execution."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from labflow.ui_server import create_server


class VirtualSupportHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name) / 'never-opened-store'
        self.server = create_server(self.workspace, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())

    def request(self, target='/api/virtual-support', method='GET', headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=10)
        try:
            connection.request(method, target, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_actual_catalog_to_cache_is_single_snapshot_without_store_writes(self):
        from labflow.virtual_support_view import build_virtual_support_view
        with patch('labflow.virtual_support_view.build_virtual_support_view', wraps=build_virtual_support_view) as builder:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: self.request(), range(4)))
            self.assertEqual(builder.call_count, 1)
        first = results[0]
        self.assertEqual(first[0], 200)
        self.assertTrue(all(r[0] == 200 and r[2] == first[2] for r in results))
        dto = json.loads(first[2])
        self.assertEqual(dto['profile_count'], 64)
        self.assertEqual(len(dto['adapter_contracts'][0]['commands']), 12)
        with patch('labflow.control_source_catalog._read', side_effect=AssertionError('cache_must_not_read')), \
             patch('labflow.virtual_support_view.build_virtual_support_view', side_effect=AssertionError('cache_must_not_rebuild')):
            self.assertEqual(self.request()[2], first[2])
        self.assertFalse(self.workspace.exists())

    def test_only_exact_routes_and_same_origin_reads_are_accepted(self):
        for target in ['/virtual-support', '/virtual-support/app.js', '/virtual-support/model.mjs']:
            self.assertEqual(self.request(target)[0], 200)
        for target in ['/api/virtual-support?x=1', '/api/virtual-support?', '/api/virtual-support/',
                       '/api/%76irtual-support', '//api/virtual-support', '/api/virtual-support#x',
                       '/virtual-support/browser_check.cjs', '/virtual-support/model.test.mjs']:
            with self.subTest(target=target):
                self.assertEqual(self.request(target)[0], 404)
        self.assertEqual(self.request(method='POST')[0], 405)
        self.assertEqual(self.request(headers={'Origin': 'https://external.invalid'})[0], 403)

    def test_metadata_failure_has_fixed_error_and_can_retry_before_first_success(self):
        with patch('labflow.virtual_support_view.build_virtual_support_view', side_effect=ValueError('PRIVATE_PATH_AUTH_CANARY')):
            response = self.request()
        self.assertEqual(response[0], 503)
        self.assertEqual(json.loads(response[2])['error']['code'], 'virtual_support_unavailable')
        self.assertNotIn(b'PRIVATE', response[2])
        self.assertEqual(self.request()[0], 200)


if __name__ == '__main__':
    unittest.main()
