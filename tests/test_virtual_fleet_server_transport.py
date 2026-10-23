"""Loopback rejection consumes bounded declared bytes before closing the wire."""
from copy import deepcopy
import http.client
import json
import socket
import threading
import time
import unittest
from unittest.mock import patch

from labflow.virtual_fleet_server import FleetHandler, create_server
from test_virtual_fleet_server import ACTIONS, CATALOG, TOPOLOGY, ContractRuntime


class RejectedBodyTransportTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ContractRuntime()
        self.server = create_server(self.runtime, catalog=deepcopy(CATALOG),
                                    topology=deepcopy(TOPOLOGY), role_actions=deepcopy(ACTIONS), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            client.request('GET', '/api/state')
            self.token = json.loads(client.getresponse().read())['csrf_token']
        finally:
            client.close()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def headers(self, path, overrides=None, length=2):
        values = {'Host': f'127.0.0.1:{self.server.server_port}', 'Origin': self.origin,
                  'X-CSRF-Token': self.token, 'Content-Type': 'application/json',
                  'Content-Length': str(length)}
        values.update(overrides or {})
        return (f'POST {path} HTTP/1.1\r\n' + ''.join(f'{key}: {value}\r\n' for key, value in values.items())
                + '\r\n').encode('latin1')

    def test_early_security_and_allowlist_errors_wait_for_declared_small_body(self):
        cases = [('/api/author_control', {}, 404),
                 ('/api/actions', {'X-CSRF-Token': 'wrong'}, 403),
                 ('/api/actions', {'X-CSRF-Token': 'é'}, 403),
                 ('/api/actions', {'Origin': self.origin + '/'}, 403),
                 ('/api/actions', {'Content-Type': 'text/plain'}, 415)]
        send, error = FleetHandler._send, FleetHandler._error
        for path, headers, expected in cases:
            entered, response_ready, body_sent = threading.Event(), threading.Event(), threading.Event()

            def observe_error(handler, issue):
                entered.set()
                return error(handler, issue)

            def gated_send(handler, *args, **kwargs):
                response_ready.set()
                body_sent.wait(1.5)
                return send(handler, *args, **kwargs)

            with self.subTest(path=path, headers=headers), \
                    patch.object(FleetHandler, '_error', observe_error), \
                    patch.object(FleetHandler, '_send', gated_send), \
                    socket.create_connection(('127.0.0.1', self.server.server_port), timeout=3) as wire:
                wire.sendall(self.headers(path, headers))
                try:
                    self.assertTrue(entered.wait(1.5))
                    sent_before_body = response_ready.wait(.05)
                    wire.sendall(b'{}')
                    body_sent.set()
                    response = http.client.HTTPResponse(wire)
                    response.begin()
                    self.assertEqual(response.status, expected)
                    self.assertIn('error', json.loads(response.read()))
                    self.assertFalse(sent_before_body, 'Closing before unread body can reset the Windows connection')
                finally:
                    body_sent.set()
            self.assertEqual(self.runtime.revision, 0)

    def test_rejected_short_body_has_a_total_drain_deadline(self):
        with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=2.5) as wire:
            started = time.monotonic()
            wire.sendall(self.headers('/api/author_control', length=5) + b'{')
            response = http.client.HTTPResponse(wire)
            response.begin()
            self.assertEqual(response.status, 404)
            response.read()
            self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(self.runtime.revision, 0)

    def test_fully_read_invalid_json_is_not_drained_again(self):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=.5)
        try:
            client.request('POST', '/api/actions', body=b'{', headers={
                'Origin': self.origin, 'X-CSRF-Token': self.token, 'Content-Type': 'application/json'})
            response = client.getresponse()
            self.assertEqual(response.status, 400)
            self.assertEqual(json.loads(response.read())['error']['code'], 'invalid_json')
        finally:
            client.close()
        self.assertEqual(self.runtime.revision, 0)


if __name__ == '__main__':
    unittest.main()
