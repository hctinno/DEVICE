import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import importlib
import io
import os
from pathlib import Path
import socket
import sqlite3
import sys
import time
from unittest import mock

from test_ui_read_model import IntakeFixture
from labflow.ui_server import create_server
from labflow import ui_server as host_module
from labflow.store import Store


class ReferenceFixture:
    """Public synthetic setup; all writes/analysis precede049 read admission."""
    def __init__(self, root, *, registered=True):
        from labflow.active_intake import register_source, scan_source
        from labflow.intake_jobs import claim_job, complete_job, respond
        from labflow.intake_worker import SyntheticTextProvider
        from labflow.intake_reference_snapshot import read_intake_reference_snapshot
        from labflow.intake_case_references import build_intake_case_reference_receipt
        from labflow.intake_reference_ledger import record_intake_reference
        from tests.test_document_extract import synthetic_pdf
        from tests.test_intake_case_references import catalog_fixture, context_for, response_for
        self.root = Path(root); self.legacy = Store(self.root / 'state')
        inbox = self.root / 'inbox'; (inbox / 'one').mkdir(parents=True)
        register_source(self.legacy, 'SYN-INBOX', inbox, synthetic=True, settle_seconds=1)
        (inbox / 'one/request.pdf').write_bytes(synthetic_pdf([
            'product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A']))
        scan_source(self.legacy, 'SYN-INBOX', now=100); scan_source(self.legacy, 'SYN-INBOX', now=102)
        job = claim_job(self.legacy, 'SYN-WORKER', now=103)
        complete_job(self.legacy, job['job_id'], job['token'], SyntheticTextProvider().analyze(job), now=104)
        respond(self.legacy, 'SYN-PROCEED', 'proceed', intake_id=job['intake_id'])
        self.intake_id = job['intake_id']
        if not registered: return
        capture = read_intake_reference_snapshot(self.legacy, self.intake_id)
        catalog = catalog_fixture(); context = context_for(catalog); response = response_for(context)
        receipt = build_intake_case_reference_receipt(capture['snapshot'], catalog, context, response,
                                                    producer_name=response['expected_producer']['name'])
        record_intake_reference(self.legacy, 'SYN-REFERENCE', expected_snapshot_id=capture['snapshot_id'],
            expected_head_record_id=None, intake_snapshot=capture['snapshot'], catalog=catalog,
            case_context=context, validated_response=response, reference_receipt=receipt,
            producer_name=response['expected_producer']['name'])


class ReferenceHostTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.local'
        temporary = tempfile.TemporaryDirectory(prefix='r049-', dir=parent)
        self.addCleanup(temporary.cleanup)
        self.fixture = ReferenceFixture(temporary.name)
        self.store = Store.open_existing(str(self.fixture.legacy.root)); self.addCleanup(self.store.close)
        self.ident = self.fixture.intake_id

    def start(self, scope='workspace', *, store=None, workspace=None):
        server = create_server(self.store.root if workspace is None else workspace, port=0,
            intake_reference_store=self.store if store is None else store, intake_reference_read_scope=scope)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        thread.start()
        def stop():
            server.server_close(); thread.join(5); self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        return server

    def request(self, server, path, method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection(*server.server_address, timeout=6)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally: connection.close()

    def raw(self, server, path, method='POST', body=b'{}', headers=()):
        connection = http.client.HTTPConnection(*server.server_address, timeout=6)
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            connection.putheader('Host', '127.0.0.1:' + str(server.server_port))
            for key, value in headers: connection.putheader(key, value)
            connection.endheaders(body)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally: connection.close()

    def route(self, action='history', ident=None):
        return '/api/intake-references/' + (self.ident if ident is None else ident) + '/' + action

    def bootstrap(self, server, ident=None):
        status, headers, body = self.request(server, self.route(ident=ident))
        self.assertEqual(status, 200, body)
        return headers['Set-Cookie'].split(';')[0], headers.get('X-Intake-Reference-CSRF')

    def source_headers(self, server, cookie, csrf):
        return {'Origin': 'http://127.0.0.1:' + str(server.server_port), 'Sec-Fetch-Site': 'same-origin',
                'Content-Type': 'application/json; charset=utf-8', 'Cookie': cookie,
                'X-Intake-Reference-CSRF': csrf or '0' * 64}

    def current(self, server, cookie, csrf, **changes):
        headers = self.source_headers(server, cookie, csrf); headers.update(changes)
        return self.request(server, self.route('current'), 'POST', b'{"schema_version":1,"action":"current"}', headers)

    def snapshot(self):
        return {p.relative_to(self.fixture.root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns,
                hashlib.sha256(p.read_bytes()).hexdigest()) for p in self.fixture.root.rglob('*') if p.is_file()}

    def fixed(self, suffix, operation):
        try:
            raise RuntimeError('PRIVATE caller')
        except RuntimeError:
            with self.assertRaises(ValueError) as caught: operation()
        error = caught.exception; expected = 'intake_reference_ui_' + suffix
        self.assertEqual((str(error), error.args), (expected, (expected,)))
        self.assertIsNone(error.__context__); self.assertIsNone(error.__cause__)

    def test_reference_None_has_no_parent_import_or_creating_operation(self):
        original = host_module.importlib.import_module
        def imported(name, *args, **kwargs):
            self.assertNotIn('intake_reference', name); return original(name, *args, **kwargs)
        with mock.patch.object(host_module.importlib, 'import_module', side_effect=imported), \
             mock.patch.object(Store, '__init__', side_effect=AssertionError('creating')):
            server = create_server(self.store.root, port=0, intake_reference_store=None,
                                   intake_reference_read_scope=object())
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            self.assertIs(type(server), host_module.ThreadingHTTPServer)
            self.assertEqual(self.request(server, self.route())[0], 503)
            self.assertEqual(self.raw(server, self.route('current'), body=b'', headers=[('Content-Length','39')])[0], 503)
            self.assertEqual(self.request(server, '/api/intakes')[0], 200)
        finally: server.shutdown(); server.server_close(); thread.join(5)

    def test_reference_official_binding_workspace_scope_and_callbacks_rejected_before_bind(self):
        class Fake:
            def __fspath__(self): raise AssertionError('callback')
        for value in [self.fixture.legacy, Fake(), object()]:
            self.fixed('invalid_request', lambda: create_server(self.store.root, port=0, intake_reference_store=value))
        for scope in [None, True, [], ('A', 'A'), tuple('A' + str(i) for i in range(101)), ('_A',), ('A\n',), ('A' * 151,)]:
            self.fixed('invalid_request', lambda: create_server(self.store.root, port=0,
                       intake_reference_store=self.store, intake_reference_read_scope=scope))
        for root in [self.fixture.root, str(self.store.root) + '.', str(self.store.root.parent) + '/./state', Fake()]:
            self.fixed('invalid_request', lambda: create_server(root, port=0, intake_reference_store=self.store))

    def test_reference_closed_or_changed_official_binding_is_unavailable(self):
        root = self.store.root; self.store.root = self.fixture.root
        self.fixed('unavailable', lambda: create_server(root, port=0, intake_reference_store=self.store))
        self.store.root = root
        original = self.store.db; self.store.db = self.fixture.root / 'other.sqlite3'
        self.fixed('unavailable', lambda: create_server(self.store.root, port=0, intake_reference_store=self.store))
        self.store.db = original; self.store.close()
        self.fixed('unavailable', lambda: create_server(self.store.root, port=0, intake_reference_store=self.store))

    def test_reference_static_exact3_accepted_A1_bytes_and_future_transport404_in_None(self):
        server = create_server(self.store.root, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            observed = {}
            accepted = {'model': (12335, '93a6a2f2e45c9ed75e23fbc01399ae7ec3817c1a3ff2c97651198c97802a10d2'),
                        'view': (14712, 'c3e38b254cc346d0bd64dc12b5f1ebae6e426ce17662c6d8f533f3da457b7417')}
            for name in ('model', 'view'):
                route = '/intake-references/' + name + '.mjs'
                status, headers, body = self.request(server, route)
                self.assertEqual(status, 200); self.assertEqual(headers['Content-Type'], 'text/javascript; charset=utf-8')
                self.assertEqual(body, (host_module.FRONTEND / 'intake_references' / (name + '.mjs')).read_bytes())
                lf = body.replace(b'\r\n', b'\n')
                self.assertEqual((len(lf), hashlib.sha256(lf).hexdigest()), accepted[name])
                observed[name] = {'HTTP_bytes':len(body),'HTTP_sha256':hashlib.sha256(body).hexdigest(),
                                  'GitLF_bytes':len(lf),'GitLF_sha256':hashlib.sha256(lf).hexdigest()}
                self.assertEqual(self.request(server, route, 'HEAD')[2], b'')
                for alias in [route + '?x=1', route.replace(name, '%' + format(ord(name[0]), '02x') + name[1:], 1),
                              route.replace('/' + name, '//' + name), 'http://127.0.0.1:' + str(server.server_port) + route]:
                    self.assertEqual(self.request(server, alias)[0], 404)
                status, headers, _ = self.request(server, route, 'POST')
                self.assertEqual(status, 405); self.assertEqual(headers['Allow'], 'GET, HEAD')
            status, _, transport = self.request(server, '/intake-references/transport.mjs')
            path = host_module.FRONTEND / 'intake_references/transport.mjs'
            if path.is_file():
                self.assertEqual((status, transport), (200, path.read_bytes()))
            else: self.assertEqual(status, 404)
            self.evidence = {'kind':'049_None_static_A1_accepted_bytes','assets':observed,
                             'transport_status':status,'transport_genuine_acceptance':False,
                             'reference_runtime_created':False}
        finally: server.shutdown(); server.server_close(); thread.join(5)

    def test_reference_genuine_history_HEAD_current_preserve_inputs_no_parser_and_source_separation(self):
        from labflow import intake_reference_review as api
        before = self.snapshot(); calls, opened = [], []
        original, open_file = api.read_reference_review, Path.open
        def parent(*args, **kwargs): calls.append((args[2]['action'], kwargs)); return original(*args, **kwargs)
        def opened_file(path, *args, **kwargs):
            if path.parent == self.store.root / 'blobs': opened.append(path.name)
            return open_file(path, *args, **kwargs)
        with mock.patch.object(api, 'read_reference_review', side_effect=parent), \
             mock.patch('labflow.document_extract.extract_document', side_effect=AssertionError('parser')), \
             mock.patch('labflow.intake_documents.extract_document', side_effect=AssertionError('parser')), \
             mock.patch.object(Store, '__init__', side_effect=AssertionError('creating')), \
             mock.patch.object(Path, 'open', opened_file):
            server = self.start(); cookie, csrf = self.bootstrap(server)
            self.assertEqual(opened, []); self.assertEqual(calls[-1][0], 'history')
            status, head, body = self.request(server, self.route(), 'HEAD')
            self.assertEqual((status, body), (200, b'')); self.assertNotIn('Set-Cookie', head)
            self.assertEqual(opened, [])
            status, _, body = self.current(server, cookie, csrf)
            value = json.loads(body); self.assertEqual((status, value['status']), (200, 'current'))
            self.assertEqual(len(value), 10); self.assertGreater(len(opened), 0)
        self.assertEqual(self.snapshot(), before)
        self.evidence = {'kind': 'genuine049_HTTP_043_042_038_034', 'history_parent_calls': 2,
                         'history_retained_reads': 0, 'current_parent_calls': 1, 'current_retained_opens': len(opened),
                         'parsing_calls': 0, 'inputs_unchanged': True, 'actual_customer_DB_PDF': 0}

    def test_reference_default_empty_scope_metadata_is_allowed_and_source_denied(self):
        server = self.start(())
        status, headers, _ = self.request(server, self.route())
        self.assertEqual((status, headers['X-Intake-Reference-Read-Allowed']), (200, 'false'))
        self.assertNotIn('X-Intake-Reference-CSRF', headers)
        auth = self.source_headers(server, headers['Set-Cookie'].split(';')[0], None)
        self.assertEqual(self.raw(server, self.route('current'), body=b'', headers=list(auth.items())+[('Content-Length','39')])[0], 403)

    def test_reference_current_requires_exact_Origin_Fetch_CSRF_session_scope(self):
        server = self.start(); cookie, csrf = self.bootstrap(server)
        for changes in [{'Origin': 'null'}, {'Origin': 'http://attacker.invalid'}, {'Sec-Fetch-Site': 'cross-site'},
                        {'X-Intake-Reference-CSRF': '0' * 64}, {'Cookie': cookie + '; ' + cookie}]:
            invalid = self.source_headers(server, cookie, csrf); invalid.update(changes)
            self.assertEqual(self.raw(server, self.route('current'), body=b'', headers=list(invalid.items())+[('Content-Length','39')])[0], 403)
        headers = self.source_headers(server, cookie, csrf)
        for key in ('Origin', 'Sec-Fetch-Site', 'Cookie', 'X-Intake-Reference-CSRF'):
            changed = dict(headers); changed.pop(key)
            self.assertEqual(self.raw(server, self.route('current'), body=b'', headers=list(changed.items())+[('Content-Length','39')])[0], 403)
        other = self.start(('OTHER',)); other_cookie, other_csrf = self.bootstrap(other)
        invalid = self.source_headers(other, other_cookie, other_csrf)
        self.assertEqual(self.raw(other, self.route('current'), body=b'', headers=list(invalid.items())+[('Content-Length','39')])[0], 403)

    def test_reference_path_methods_queries_and_cursor63_are_exact(self):
        server = self.start()
        for path in [self.route() + '?limit=0', self.route() + '?limit=101', self.route() + '?limit=1&limit=1',
                     self.route() + '?before_seq=01', self.route() + '?before_seq=' + str(2**63),
                     self.route() + '?x=1', self.route('current') + '?x=1']:
            self.assertIn(self.request(server, path)[0], (400, 404, 405))
        self.assertEqual(self.request(server, self.route() + '?limit=100&before_seq=' + str(2**63 - 1))[0], 200)
        for method in ('GET', 'HEAD'):
            status, headers, body = self.request(server, self.route('current'), method)
            self.assertEqual(status, 405); self.assertEqual(headers['Allow'], 'POST')
            if method == 'HEAD': self.assertEqual(body, b'')
        for path in [self.route().replace(self.ident, '%49' + self.ident[1:]), self.route().replace('/history', '//history'),
                     self.route(ident='_A'), self.route(ident='A' * 151), self.route(ident='A%0a')]:
            self.assertIn(self.request(server, path)[0], (400, 404))

    def test_reference_strict_current_wire_rejects_extra_duplicate_BOM_nonfinite_depth(self):
        server = self.start(); cookie, csrf = self.bootstrap(server)
        headers = self.source_headers(server, cookie, csrf)
        for raw in [b'\xef\xbb\xbf{}', b'{"schema_version":1,"schema_version":1,"action":"current"}',
                    b'{"schema_version":1,"action":"current","allow_retained_reads":true}',
                    b'{"schema_version":NaN,"action":"current"}', b'[]', b'{} trailing',
                    b'{"schema_version":1,"action":"current","x":"\\ud800"}']:
            self.assertEqual(self.request(server, self.route('current'), 'POST', raw, headers)[0], 400)
        self.assertEqual(self.raw(server, self.route('current'), body=b'', headers=list(headers.items())+[('Content-Length','16385')])[0], 413)

    def test_reference_session_HEAD_no_creation_renewal_cookie_flags_and_stable_tokens(self):
        server = self.start(); rt = server._reference_runtime
        now = [1000.0]; rt.clock = lambda: now[0]
        status, headers, _ = self.request(server, self.route(), 'HEAD')
        self.assertEqual(status, 200); self.assertNotIn('Set-Cookie', headers); self.assertEqual(len(rt.sessions), 0)
        cookie, csrf = self.bootstrap(server); sid = cookie.split('=')[1]
        self.assertEqual(len(sid), 64); self.assertEqual(len(csrf), 64)
        now[0] += 899
        _, headers, _ = self.request(server, self.route(), headers={'Cookie': cookie})
        self.assertEqual(headers['X-Intake-Reference-CSRF'], csrf); self.assertNotIn('Set-Cookie', headers)
        stamp = rt.sessions[sid]['last_seen']; now[0] += 899
        self.request(server, self.route(), 'HEAD', headers={'Cookie': cookie})
        self.assertEqual(rt.sessions[sid]['last_seen'], stamp)
        now[0] += 1
        self.assertEqual(self.current(server, cookie, csrf)[0], 403)

    def test_reference_session128_full_is_not_silently_evicted_and_expired_slots_reclaimed(self):
        server = self.start(); rt = server._reference_runtime; now = [0.0]; rt.clock = lambda: now[0]
        for _ in range(128): self.assertEqual(self.request(server, self.route())[0], 200)
        self.assertEqual(len(rt.sessions), 128)
        self.assertEqual(self.request(server, self.route())[0], 503)
        now[0] = 900
        self.assertEqual(self.request(server, self.route())[0], 200); self.assertEqual(len(rt.sessions), 1)

    def test_reference_internal_binding_detached_hex64_no_session_or_idle_renewal(self):
        server = self.start(); cookie, _ = self.bootstrap(server); sid = cookie.split('=')[1]
        rt = server._reference_runtime; stamp = rt.sessions[sid]['last_seen']
        binding = server._reference_action_binding(sid)
        self.assertEqual(set(binding), {'host_epoch', 'session_id', 'scope_epoch'})
        self.assertTrue(all(type(v) is str and len(v) == 64 for v in binding.values()))
        binding['host_epoch'] = '0' * 64
        self.assertNotEqual(binding, server._reference_action_binding(sid))
        self.assertEqual(rt.sessions[sid]['last_seen'], stamp)
        self.assertIsNone(server._reference_action_binding('0' * 64))

    def test_reference_source_lease_busy_and_body_error_finally_preserves_protocol(self):
        server = self.start(); rt = server._reference_runtime
        with server._reference_parent_call(source=True):
            self.assertEqual(rt.active, 1)
            self.fixed('unavailable', lambda: server._reference_parent_call(source=True).__enter__())
            with server._reference_parent_call(): self.assertEqual(rt.active, 2)
        self.assertEqual(rt.active, 0)
        marker = RuntimeError('PRIVATE business')
        with self.assertRaises(RuntimeError) as caught:
            with server._reference_parent_call(source=True): raise marker
        self.assertIs(caught.exception, marker); self.assertEqual(rt.active, 0)
        self.fixed('invalid_request', lambda: server._reference_parent_call(source=1).__enter__())

    def test_reference_parent_block_allows_mutex_and_metadata_but_second_source429(self):
        from labflow import intake_reference_review as api
        original = api.read_reference_review; entered, release = threading.Event(), threading.Event()
        def parent(*args, **kwargs):
            if args[2]['action'] == 'current': entered.set(); self.assertTrue(release.wait(5))
            return original(*args, **kwargs)
        result = []
        with mock.patch.object(api, 'read_reference_review', side_effect=parent):
            server = self.start(); cookie, csrf = self.bootstrap(server)
            thread = threading.Thread(target=lambda: result.append(self.current(server, cookie, csrf)))
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                self.assertTrue(server._reference_runtime.lock.acquire(timeout=1)); server._reference_runtime.lock.release()
                self.assertEqual(self.request(server, self.route())[0], 200)
                self.assertEqual(self.current(server, cookie, csrf)[0], 429)
            finally: release.set(); thread.join(6)
        self.assertEqual(result[0][0], 200)

    def test_reference_server_close_waits_parent_then_workers_and_never_borrowed_close(self):
        server = self.start(); entered, release, stopped = threading.Event(), threading.Event(), threading.Event()
        def work():
            with server._reference_parent_call(source=True): entered.set(); release.wait(5)
        worker = threading.Thread(target=work); worker.start(); self.assertTrue(entered.wait(3))
        close = threading.Thread(target=lambda: (server.server_close(), stopped.set())); close.start()
        try:
            deadline = time.monotonic() + 3
            while not server._reference_runtime.closing and time.monotonic() < deadline: time.sleep(.005)
            self.assertFalse(stopped.wait(.05)); self.assertEqual(self.store._existing_binding.state, 'open')
            self.fixed('unavailable', lambda: server._reference_parent_call().__enter__())
        finally: release.set(); worker.join(5); close.join(5)
        self.assertTrue(stopped.is_set()); self.assertEqual(self.store._existing_binding.state, 'open')
        self.assertFalse(server._reference_runtime.clients)
        paths = [self.store.db, self.store.root / 'blobs', self.store.root, self.fixture.root]
        allowed = Path(__file__).resolve().parents[1] / '.local'
        for path in paths:
            moved = path.with_name(path.name + '.moved')
            self.assertTrue(path.resolve().is_relative_to(allowed.resolve()))
            self.assertTrue(moved.resolve().is_relative_to(allowed.resolve()))
            with self.assertRaises(OSError): path.rename(moved)
        self.store.close()
        for path in paths:
            moved = path.with_name(path.name + '.moved'); path.rename(moved); moved.rename(path)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); probe.bind(server.server_address)
        self.evidence = {'kind': '049_drain_native_release', 'parent_waited': True, 'borrowed_close_calls': 0,
                         'known_clients': 0, 'blocked_native_moves':4,'released_native_moves':4,'own_port_rebind':True}

    def test_reference_self_lease_close_rejected_without_poisoning_open_host(self):
        server = self.start()
        with server._reference_parent_call(): self.fixed('unavailable', server.server_close)
        self.assertFalse(server._reference_runtime.closing)
        self.assertEqual(self.request(server, self.route())[0], 200)

    def test_reference_not_started_close_and_repeated_close_never_shutdown_deadlock(self):
        server = create_server(self.store.root, port=0, intake_reference_store=self.store)
        with mock.patch.object(server, 'shutdown', side_effect=AssertionError('unstarted shutdown')):
            server.server_close(); server.server_close()
        self.assertEqual(server.socket.fileno(), -1)
        self.assertEqual(self.store._existing_binding.state, 'open')

    def test_reference_accepted_slow_headers_and_uncaught_handler_are_reclaimed_quietly(self):
        server = self.start(); connection = socket.create_connection(server.server_address, timeout=3)
        connection.sendall(b'GET / HTTP/1.1\r\nHost: ')
        try:
            with mock.patch('sys.stderr', new_callable=io.StringIO) as stderr:
                server.server_close()
                self.assertEqual(stderr.getvalue(), '')
        finally: connection.close()
        self.assertFalse(server._reference_runtime.clients)
        self.assertFalse(any(t.is_alive() for t in server._reference_runtime.worker_refs))

    def test_reference_all27_parent_errors_require_exact_class_and_code(self):
        from labflow import intake_reference_review as api
        from labflow.intake_reference_ledger import IntakeReferenceLedgerError
        from labflow.intake_reference_snapshot import IntakeReferenceStateError
        groups = [(api.IntakeReferenceReviewError, api._CODES),
                  (IntakeReferenceLedgerError, {'invalid_argument','store_invalid','intake_not_found','input_limit','parent_invalid','origin_invalid','schema_mismatch','request_conflict','integrity_invalid','storage_error'}),
                  (IntakeReferenceStateError, {'invalid_argument','store_invalid','transaction_required','intake_not_found','input_limit','source_integrity_invalid','projection_inconsistent','delegation_invalid','storage_error'})]
        for cls, suffixes in groups:
            for suffix in suffixes:
                error = cls(suffix)
                with mock.patch.object(api, 'read_reference_review', side_effect=error):
                    server = self.start(); status, _, body = self.request(server, self.route())
                expected = {'invalid_argument':400,'access_denied':403,'intake_not_found':404,'input_limit':413}.get(suffix,503)
                self.assertEqual((status, json.loads(body)), (expected, {'error': {'code': error.code}}))
                server.server_close()

    def test_reference_parent_unknown_or_malformed_DTO_is_fixed_not_success(self):
        from labflow import intake_reference_review as api
        valid = api.read_reference_review(self.store, self.ident, {'schema_version':1,'action':'history','limit':20,'before_seq':None})
        for payload in [{**valid, 'PRIVATE': 'PRIVATE'}, {**valid, 'available': 1},
                        {**valid, 'verification': {**valid['verification'], 'original_sources_reverified': True}}]:
            with mock.patch.object(api, 'read_reference_review', return_value=payload):
                server = self.start(); status, _, body = self.request(server, self.route())
            self.assertEqual((status, json.loads(body)), (503, {'error': {'code':'intake_reference_ui_unavailable'}}))
            server.server_close()

    def test_reference_maximum_scope_and_ID_are_accepted_not_silently_shrunk(self):
        maximum = 'A' * 150
        server = self.start((maximum,) + tuple('ID' + str(i) for i in range(99)))
        self.assertEqual(len(server._reference_runtime.scope), 100)
        self.assertEqual(self.request(server, self.route(ident=maximum))[0], 404)
        self.assertEqual(self.request(server, self.route(ident='A' * 151))[0], 400)

    def test_reference_static_IO_failure503_and_missing_HEAD404_without_fake_asset(self):
        server = self.start()
        original = Path.read_bytes
        def read(path):
            if path == host_module.FRONTEND / 'intake_references/model.mjs': raise PermissionError('PRIVATE asset')
            return original(path)
        with mock.patch.object(Path, 'read_bytes', read):
            status, _, body = self.request(server, '/intake-references/model.mjs')
        self.assertEqual((status, json.loads(body)), (503, {'error': {'code': 'asset_unavailable'}}))
        expected = 200 if (host_module.FRONTEND / 'intake_references/transport.mjs').is_file() else 404
        self.assertEqual(self.request(server, '/intake-references/transport.mjs', 'HEAD')[0::2], (expected, b''))

    def test_reference_duplicate_framing_content_and_auth_headers_precede_parent(self):
        from labflow import intake_reference_review as api
        original = api.read_reference_review; calls = []
        def parent(*args, **kwargs): calls.append(args[2]['action']); return original(*args, **kwargs)
        with mock.patch.object(api, 'read_reference_review', side_effect=parent):
            server = self.start(); cookie, csrf = self.bootstrap(server); calls.clear()
            raw = b'{"schema_version":1,"action":"current"}'
            auth = list(self.source_headers(server, cookie, csrf).items())
            cases = [([('Content-Length', str(len(raw))), ('Content-Length', str(len(raw)))],400),
                     ([('Content-Length','-1')],400), ([],411),
                     ([('Content-Length',str(len(raw))), ('Transfer-Encoding','chunked')],400),
                     ([('Content-Length',str(len(raw))), ('Content-Encoding','gzip')],415),
                     ([('Content-Length',str(len(raw))), ('Expect','100-continue')],417),
                     ([('Content-Length',str(len(raw))), ('Origin',auth[0][1])],403),
                     ([('Content-Length',str(len(raw))), ('X-Intake-Reference-CSRF',csrf)],403),
                     ([('Content-Length',str(len(raw))), ('Cookie',cookie)],403),
                     ([('Content-Length',str(len(raw))), ('Host','attacker.invalid')],403)]
            for extra, expected in cases:
                # These failures precede body reads; do not send ambiguous unread payload after bad framing.
                self.assertEqual(self.raw(server, self.route('current'), body=b'', headers=auth + extra)[0], expected)
            self.assertEqual(calls, [])

    def test_reference_body_read_timeout408_does_not_reserve_parent_or_source(self):
        server = self.start(); cookie, csrf = self.bootstrap(server)
        connection = http.client.HTTPConnection(*server.server_address, timeout=7)
        try:
            connection.putrequest('POST', self.route('current'))
            for key, value in self.source_headers(server, cookie, csrf).items(): connection.putheader(key, value)
            connection.putheader('Content-Length', '100'); connection.endheaders(b'{')
            response = connection.getresponse(); self.assertEqual(response.status, 408); response.read()
        finally: connection.close()
        self.assertEqual(server._reference_runtime.active, 0); self.assertFalse(server._reference_runtime.source_active)

    def test_reference_expiry_after_body_decode_is_rechecked_before_parent_lease(self):
        server = self.start(); rt = server._reference_runtime; now = [0.0]; rt.clock = lambda: now[0]
        cookie, csrf = self.bootstrap(server); original = host_module._reference_body
        def decoded(blob):
            result = original(blob); now[0] = 900; return result
        with mock.patch.object(host_module, '_reference_body', side_effect=decoded):
            self.assertEqual(self.current(server, cookie, csrf)[0], 403)
        self.assertEqual(rt.active, 0)

    def test_reference_self_worker_and_own_running_loop_close_are_fixed_not_deadlocks(self):
        from labflow import intake_reference_review as api
        original = api.read_reference_review; holder = {}; worker_rejected = []
        def parent(*args, **kwargs):
            self.fixed('unavailable', holder['server'].server_close); worker_rejected.append(True)
            return original(*args, **kwargs)
        with mock.patch.object(api, 'read_reference_review', side_effect=parent):
            server = self.start(); holder['server'] = server
            self.assertEqual(self.request(server, self.route())[0], 200)
        self.assertEqual(worker_rejected, [True]); self.assertFalse(server._reference_runtime.closing)
        seen = threading.Event()
        def action():
            if not seen.is_set(): self.fixed('unavailable', server.server_close); seen.set()
        server.service_actions = action
        self.assertTrue(seen.wait(3)); self.assertFalse(server._reference_runtime.closing)

    def test_reference_stopped_loop_close_never_calls_shutdown_again(self):
        server = self.start(); server.shutdown()
        deadline = time.monotonic() + 3
        while server._reference_runtime.loop_thread is not None and time.monotonic() < deadline: time.sleep(.005)
        with mock.patch.object(server, 'shutdown', side_effect=AssertionError('stopped shutdown')): server.server_close()
        self.assertEqual(server.socket.fileno(), -1)

    def test_reference_real_owned_port_collision_reclaims_unpublished_host(self):
        # Windows SO_REUSEADDR permits sharing; an owned exclusive listener gives a real collision.
        listener = socket.socket(); self.addCleanup(listener.close)
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'): listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(('127.0.0.1', 0)); listener.listen()
        self.fixed('unavailable', lambda: create_server(self.store.root, port=listener.getsockname()[1], intake_reference_store=self.store))
        server = self.start()
        self.assertEqual(self.request(server, self.route())[0], 200)
        self.assertEqual(self.store._existing_binding.state, 'open')

    def test_reference_shutdown_failure_and_repeated_interrupt_still_reclaim_known_resources(self):
        server = self.start()
        with mock.patch.object(server, 'shutdown', side_effect=OSError('PRIVATE shutdown')):
            self.fixed('unavailable', server.server_close)
        self.assertEqual(server.socket.fileno(), -1); self.assertFalse(server._reference_runtime.worker_refs)
        server.server_close()
        second = self.start(); original = host_module._REFERENCE_BASE_SHUTDOWN; attempts = []
        def interrupted(value):
            attempts.append(1)
            if len(attempts) < 3: raise KeyboardInterrupt()
            return original(value)
        with mock.patch.object(second, 'shutdown', side_effect=lambda: interrupted(second)):
            second.server_close()
        self.assertEqual(len(attempts), 3); self.assertEqual(second.socket.fileno(), -1)

    def test_reference_known_client_close_failure_is_quiet_retained_and_retryable(self):
        server = self.start(); client = socket.create_connection(server.server_address, timeout=3)
        client.sendall(b'GET / HTTP/1.1\r\nHost: ')
        deadline = time.monotonic() + 3
        while not server._reference_runtime.clients and time.monotonic() < deadline: time.sleep(.005)
        owned = next(iter(server._reference_runtime.clients)); original = socket.socket.close
        def close(value):
            if value is owned: raise OSError('PRIVATE client close')
            return original(value)
        try:
            with mock.patch.object(socket.socket, 'close', close), mock.patch('sys.stderr', new_callable=io.StringIO) as stderr:
                self.fixed('unavailable', server.server_close)
                self.assertEqual(stderr.getvalue(), '')
            self.assertIn(owned, server._reference_runtime.clients)
            server.server_close(); self.assertFalse(server._reference_runtime.clients)
        finally: client.close()

    def test_reference_normal_none_stale_and_unavailable_are_genuine200_not_transport_errors(self):
        from labflow.intake_jobs import respond
        from labflow.active_intake import scan_source
        from tests.test_document_extract import synthetic_pdf
        server = self.start(); cookie, csrf = self.bootstrap(server)
        respond(self.fixture.legacy, 'SYN-ANSWER-LATER', 'answer', intake_id=self.ident, answers={'model':'MODEL-A'})
        before = self.snapshot(); status, _, body = self.current(server, cookie, csrf)
        self.assertEqual((status, json.loads(body)['status']), (200, 'stale')); self.assertEqual(self.snapshot(), before)
        (self.fixture.root / 'inbox/one/request.pdf').write_bytes(synthetic_pdf(['product_type: sensor_node\nmarket: FCC\npurpose: development\nmodel: MODEL-A\nrevision: NEXT']))
        scan_source(self.fixture.legacy, 'SYN-INBOX', now=200); scan_source(self.fixture.legacy, 'SYN-INBOX', now=202)
        before = self.snapshot(); status, _, body = self.current(server, cookie, csrf)
        self.assertEqual((status, json.loads(body)['status']), (200, 'unavailable')); self.assertEqual(self.snapshot(), before)
        other = ReferenceFixture(self.fixture.root / 'no-ledger', registered=False)
        opened = Store.open_existing(str(other.legacy.root)); self.addCleanup(opened.close)
        no_ledger = self.start(store=opened, workspace=opened.root)
        c, token = self.bootstrap(no_ledger, other.intake_id)
        status, _, body = self.request(no_ledger, self.route('current', other.intake_id), 'POST',
                b'{"schema_version":1,"action":"current"}', self.source_headers(no_ledger, c, token))
        self.assertEqual((status, json.loads(body)['status']), (200, 'none'))

    def test_reference_unknown_HTTP_method_has_405_not_raw_HTML_or_wrong_status(self):
        server = self.start()
        for path, allow in [(self.route(), 'GET, HEAD'), (self.route('current'), 'POST'),
                            ('/intake-references/model.mjs', 'GET, HEAD')]:
            status, headers, body = self.request(server, path, 'TRACE')
            self.assertEqual((status, headers.get('Allow')), (405, allow))
            self.assertEqual(json.loads(body)['error']['code'], 'read_only')

    def test_reference_genuine_current_abort_then_close_waits_for_parent_finally(self):
        from labflow import intake_reference_review as api
        original = api.read_reference_review; entered, release = threading.Event(), threading.Event()
        calls = []
        def parent(*args, **kwargs):
            if args[2]['action'] == 'current':
                entered.set(); self.assertTrue(release.wait(5)); calls.append('current')
            return original(*args, **kwargs)
        with mock.patch.object(api, 'read_reference_review', side_effect=parent):
            server = self.start(); cookie, csrf = self.bootstrap(server); before = self.snapshot()
            payload = b'{"schema_version":1,"action":"current"}'
            lines = ['POST ' + self.route('current') + ' HTTP/1.1', 'Host: 127.0.0.1:' + str(server.server_port)]
            lines += [key + ': ' + value for key, value in self.source_headers(server, cookie, csrf).items()]
            lines += ['Content-Length: ' + str(len(payload)), '', '']
            client = socket.create_connection(server.server_address, timeout=3)
            client.sendall('\r\n'.join(lines).encode('ascii') + payload)
            try:
                self.assertTrue(entered.wait(3)); client.shutdown(socket.SHUT_RDWR); client.close()
                self.assertEqual(self.current(server, cookie, csrf)[0], 429)
                errors = []
                def stop():
                    try: server.server_close()
                    except BaseException as error: errors.append(error)
                supervisor = threading.Thread(target=stop)
                with mock.patch('sys.stderr', new_callable=io.StringIO) as stderr:
                    supervisor.start(); self.assertTrue(supervisor.is_alive())
                    self.assertEqual(self.store._existing_binding.state, 'open')
                    release.set(); supervisor.join(6)
                    self.assertEqual(stderr.getvalue(), '')
                self.assertFalse(supervisor.is_alive()); self.assertEqual(errors, [])
            finally:
                release.set(); client.close()
        self.assertEqual(calls, ['current']); self.assertEqual(self.snapshot(), before)
        self.assertEqual(server._reference_runtime.active, 0)
        self.assertFalse(server._reference_runtime.clients); self.assertFalse(server._reference_runtime.worker_refs)
        self.evidence = {'kind':'049_actual_current_abort_close', 'barrier_around_formal_parent': True,
                         'actual_042_calls':1, 'delivery':'unknown; client aborted', 'busy429':True,
                         'parent_finally_before_close':True, 'inputs_unchanged':True, 'known_clients_workers':0}

    def test_reference_failed_response_write_does_not_attempt_recursive_error_response(self):
        server = self.start(); cls = server.RequestHandlerClass; original = cls.send_response
        attempts = []
        def response(handler, status, message=None):
            if handler.path == '/intake-references/model.mjs':
                attempts.append(status); raise OSError('PRIVATE response write')
            return original(handler, status, message)
        with mock.patch.object(cls, 'send_response', response), mock.patch('sys.stderr', new_callable=io.StringIO) as stderr:
            with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError, ConnectionAbortedError)):
                self.request(server, '/intake-references/model.mjs')
            self.assertEqual(attempts, [200]); self.assertEqual(stderr.getvalue(), '')

    def test_reference_interrupt_between_close_phases_is_deferred_until_reclaimed(self):
        server = self.start(); rt = server._reference_runtime
        original = threading.Condition.__enter__; seen, errors = [], []
        def enter(condition):
            if condition is rt.changed and not seen:
                seen.append(True); raise KeyboardInterrupt()
            return original(condition)
        def stopped():
            try: server.server_close()
            except BaseException as error: errors.append(type(error).__name__)
        with mock.patch.object(threading.Condition, '__enter__', enter):
            thread = threading.Thread(target=stopped); thread.start(); thread.join(5)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])
        self.assertEqual(server.socket.fileno(), -1); self.assertFalse(rt.clients)

    def test_reference_second_loop_is_rejected_without_corrupting_running_loop(self):
        server = self.start(); self.assertEqual(self.request(server, self.route())[0], 200)
        first = server._reference_runtime.loop_thread
        try:
            with mock.patch.object(host_module.ThreadingHTTPServer, 'serve_forever', side_effect=AssertionError('second loop body')):
                self.fixed('unavailable', server.serve_forever)
            self.assertIs(server._reference_runtime.loop_thread, first)
        finally:
            server.shutdown()
            try: server.server_close()
            except ValueError: pass

    def test_reference_parent_import_failure_and_missing_callable_are_fixed_before_bind(self):
        from labflow import intake_reference_review as api
        original = host_module.importlib.import_module
        def imported(name, *args, **kwargs):
            if name == '.intake_reference_review': raise OSError('PRIVATE import')
            return original(name, *args, **kwargs)
        with mock.patch.object(host_module.ThreadingHTTPServer, 'server_bind', side_effect=AssertionError('bind reached')) as bind:
            with mock.patch.object(host_module.importlib, 'import_module', side_effect=imported):
                self.fixed('unavailable', lambda: create_server(self.store.root, port=0, intake_reference_store=self.store))
            with mock.patch.object(api, 'read_reference_review', None):
                self.fixed('unavailable', lambda: create_server(self.store.root, port=0, intake_reference_store=self.store))
            bind.assert_not_called()

    def test_reference_configured_host_and_port_types_rejected_without_callbacks_or_bind(self):
        class Host:
            def __eq__(self, other): raise AssertionError('host callback')
        with mock.patch.object(host_module.ThreadingHTTPServer, 'server_bind', side_effect=AssertionError('bind reached')) as bind:
            self.fixed('invalid_request', lambda: create_server(self.store.root, host=Host(), port=0, intake_reference_store=self.store))
            for value in [True, False, 1.0, '0', -1, 65536]:
                self.fixed('invalid_request', lambda: create_server(self.store.root, port=value, intake_reference_store=self.store))
            bind.assert_not_called()

    def _guard_boundary(self, change, method='GET'):
        server = self.start(); rt = server._reference_runtime; now = [0.0]; rt.clock = lambda: now[0]
        cookie, _ = self.bootstrap(server); parent, connect = rt.parent, sqlite3.connect
        info = self.store._existing_binding.backend.info; calls, sql, native = [], [], []
        def observed_parent(*args, **kwargs):
            calls.append(args[2]['action']); return parent(*args, **kwargs)
        def observed_sql(*args, **kwargs):
            sql.append(1); return connect(*args, **kwargs)
        def changed(*args, **kwargs):
            value = info(*args, **kwargs)
            if not native:
                native.append(1); change(rt, now)
            return value
        original_binding = self.store._existing_binding
        try:
            with mock.patch.object(rt, 'parent', observed_parent), mock.patch.object(sqlite3, 'connect', observed_sql), \
                    mock.patch.object(original_binding.backend, 'info', changed):
                status, _, body = self.request(server, self.route(), method, headers={'Cookie':cookie})
        finally: self.store._existing_binding = original_binding
        self.assertTrue(native)
        return status, body, calls, sql

    def test_reference_history_GET_expiry_during_native_guard_rejects_before_parent_or_SQL(self):
        def expire(rt, now): now[0] = 900.0
        status, body, calls, sql = self._guard_boundary(expire)
        self.assertEqual((status, json.loads(body)['error']['code']), (403, 'intake_reference_ui_access_denied'))
        self.assertEqual((calls, sql), ([], []))
        self.evidence = {'kind':'049_review_I1_expiry','method':'GET','status':403,'formal_parent_calls':0,'SQLite_connections':0}

    def test_reference_history_HEAD_expiry_during_native_guard_rejects_before_parent_or_SQL(self):
        def expire(rt, now): now[0] = 900.0
        status, body, calls, sql = self._guard_boundary(expire, 'HEAD')
        self.assertEqual((status, body), (403, b'')); self.assertEqual((calls, sql), ([], []))
        self.evidence = {'kind':'049_review_I1_expiry','method':'HEAD','status':403,'formal_parent_calls':0,'SQLite_connections':0}

    def test_reference_closing_during_native_guard_rejects_before_parent_or_SQL(self):
        def closing(rt, now):
            with rt.lock: rt.closing = True
        status, _, calls, sql = self._guard_boundary(closing)
        self.assertEqual(status, 503); self.assertEqual((calls, sql), ([], []))

    def test_reference_binding_replaced_during_native_guard_rejects_before_parent_or_SQL(self):
        def replaced(rt, now): self.store._existing_binding = object()
        status, _, calls, sql = self._guard_boundary(replaced)
        self.assertEqual(status, 503); self.assertEqual((calls, sql), ([], []))

    def _native_guard_mutex(self, action):
        server = self.start(); rt = server._reference_runtime
        cookie, csrf = self.bootstrap(server) if action == 'current' else (None, None)
        backend = self.store._existing_binding.backend; info = backend.info
        entered, release = threading.Event(), threading.Event(); results, errors = [], []
        def blocked(*args, **kwargs):
            if not entered.is_set():
                entered.set()
                if not release.wait(5): raise AssertionError('native guard test release missing')
            return info(*args, **kwargs)
        def work():
            try:
                if action == 'hook':
                    with server._reference_parent_call(): results.append(200)
                elif action == 'current': results.append(self.current(server, cookie, csrf)[0])
                else: results.append(self.request(server, self.route())[0])
            except BaseException as error: errors.append(type(error).__name__)
        acquired = False; active_during_native = source_during_native = None
        with mock.patch.object(backend, 'info', blocked):
            thread = threading.Thread(target=work); thread.start()
            try:
                self.assertTrue(entered.wait(3))
                acquired = rt.lock.acquire(timeout=.15)
                if acquired:
                    active_during_native, source_during_native = rt.active, rt.source_active
                    rt.lock.release()
            finally: release.set(); thread.join(6)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors, []); self.assertEqual(results, [200])
        self.assertTrue(acquired, 'native identity I/O held the runtime mutex')
        self.assertEqual(active_during_native, 1)
        self.assertIs(source_during_native, action == 'current')
        self.evidence = {'kind':'049_review_I3_native_mutex','action':action,'actual_backend_info':True,
                         'runtime_mutex_acquired_while_native_blocked':acquired,'active_during_native':active_during_native,
                         'source_during_native':source_during_native,'result':200}

    def test_reference_history_native_guard_releases_runtime_mutex(self):
        self._native_guard_mutex('history')

    def test_reference_current_native_guard_releases_runtime_mutex(self):
        self._native_guard_mutex('current')

    def test_reference_public_lease_native_guard_releases_runtime_mutex(self):
        self._native_guard_mutex('hook')

    def test_reference_completed_worker_refs_do_not_accumulate_during_host_lifetime(self):
        server = self.start(); rt = server._reference_runtime; cookie = None; observations = []
        for count in range(1, 22):
            status, headers, _ = self.request(server, self.route(), headers={'Cookie':cookie} if cookie else None)
            self.assertEqual(status, 200)
            if cookie is None: cookie = headers['Set-Cookie'].split(';')[0]
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                with rt.lock:
                    if not rt.workers and not rt.clients: break
                time.sleep(.005)
            with rt.lock:
                self.assertFalse(rt.workers); self.assertFalse(rt.clients); self.assertEqual(rt.active, 0)
                if count in (1, 11, 21):
                    observations.append({'HTTP_requests':count,'retained_terminated':sum(not t.is_alive() for t in rt.worker_refs),
                                         'retained_refs':len(rt.worker_refs),'sessions':len(rt.sessions)})
        self.assertTrue(all(row['retained_terminated'] == row['retained_refs'] == 0 for row in observations), observations)
        self.evidence = {'kind':'049_review_I2_worker_refs','observations':observations}

    def test_reference_close_joins_worker_after_runtime_finally_before_thread_return(self):
        server = self.start(); completed, release, stopped = threading.Event(), threading.Event(), threading.Event()
        original = server.process_request_thread; errors = []
        def after_finally(*args):
            try: original(*args)
            finally: completed.set(); release.wait(5)
        def close():
            try: server.server_close()
            except BaseException as error: errors.append(type(error).__name__)
            finally: stopped.set()
        with mock.patch.object(server, 'process_request_thread', after_finally):
            self.assertEqual(self.request(server, self.route())[0], 200); self.assertTrue(completed.wait(3))
            supervisor = threading.Thread(target=close); supervisor.start()
            try:
                self.assertFalse(stopped.wait(.1)); self.assertEqual(self.store._existing_binding.state, 'open')
            finally: release.set(); supervisor.join(6)
        self.assertFalse(supervisor.is_alive()); self.assertEqual(errors, [])
        self.assertFalse(server._reference_runtime.worker_refs)
        self.evidence = {'kind':'049_review_I2_worker_finally_join','close_waited_for_actual_thread_exit':True,
                         'borrowed_Store_remained_open':True,'known_worker_refs_after_close':0}

    def test_reference_close_waits_for_native_guard_owned_by_public_lease(self):
        server = self.start(); rt = server._reference_runtime; backend = self.store._existing_binding.backend
        original = backend.info; entered, release, stopped = threading.Event(), threading.Event(), threading.Event()
        body, errors, close_errors = [], [], []
        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(5): raise AssertionError('native release missing')
            return original(*args, **kwargs)
        def work():
            try:
                with server._reference_parent_call(source=True): body.append(1)
            except ValueError as error: errors.append(error.args)
        def close():
            try: server.server_close()
            except BaseException as error: close_errors.append(type(error).__name__)
            finally: stopped.set()
        waited = False
        with mock.patch.object(backend, 'info', blocked):
            worker = threading.Thread(target=work); worker.start(); self.assertTrue(entered.wait(3))
            supervisor = threading.Thread(target=close); supervisor.start()
            try:
                deadline = time.monotonic() + 3
                while not rt.closing and time.monotonic() < deadline: time.sleep(.005)
                self.assertTrue(rt.closing); waited = not stopped.wait(.1)
                self.assertEqual(self.store._existing_binding.state, 'open')
            finally: release.set(); worker.join(6); supervisor.join(6)
        self.assertFalse(worker.is_alive()); self.assertFalse(supervisor.is_alive())
        self.assertEqual(close_errors, []); self.assertTrue(waited, 'close returned during owned native I/O')
        self.assertEqual(body, []); self.assertEqual(errors, [('intake_reference_ui_unavailable',)])
        self.assertEqual(rt.active, 0); self.assertFalse(rt.source_active)
        self.evidence = {'kind':'049_review_I3_native_close','native_guard_owned_until_finally':True,
                         'close_waited':waited,'parent_body_calls':0,'borrowed_Store_closed':False}

    def test_reference_second_source429_precedes_native_IO_while_first_guard_is_blocked(self):
        server = self.start(); rt = server._reference_runtime; cookie, csrf = self.bootstrap(server)
        backend = self.store._existing_binding.backend; original = backend.info
        entered, release, second_done = threading.Event(), threading.Event(), threading.Event(); first, second = [], []
        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(5): raise AssertionError('native release missing')
            return original(*args, **kwargs)
        def current(result, done=None):
            try: result.append(self.current(server, cookie, csrf)[0])
            finally:
                if done is not None: done.set()
        fast = False
        with mock.patch.object(backend, 'info', blocked):
            one = threading.Thread(target=current, args=(first,)); one.start(); self.assertTrue(entered.wait(3))
            two = threading.Thread(target=current, args=(second,second_done)); two.start()
            try: fast = second_done.wait(.3)
            finally: release.set(); one.join(6); two.join(6)
        self.assertFalse(one.is_alive()); self.assertFalse(two.is_alive()); self.assertTrue(fast, 'second source waited behind native I/O')
        self.assertEqual((first, second), ([200], [429])); self.assertEqual(rt.active, 0); self.assertFalse(rt.source_active)
        self.evidence = {'kind':'049_review_I3_source_native_busy','second_source_before_native_release':429,
                         'first_current':200,'queue':0,'active_after':0}

    def test_reference_native_guard_failure_releases_source_and_parent_lease_quietly(self):
        server = self.start(); rt = server._reference_runtime; cookie, csrf = self.bootstrap(server)
        backend = self.store._existing_binding.backend
        for failure in (OSError('PRIVATE native path'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                with mock.patch.object(backend, 'info', side_effect=failure), \
                        mock.patch.object(rt, 'parent', wraps=rt.parent) as parent, \
                        mock.patch('sys.stderr', new_callable=io.StringIO) as stderr:
                    status, _, body = self.current(server, cookie, csrf)
                    self.assertEqual((status, json.loads(body)['error']['code']), (503, 'intake_reference_ui_unavailable'))
                    parent.assert_not_called(); self.assertEqual(stderr.getvalue(), '')
                self.assertEqual(rt.active, 0); self.assertFalse(rt.source_active); self.assertFalse(rt.leases)
                self.assertEqual(self.current(server, cookie, csrf)[0], 200)
        self.evidence = {'kind':'049_review_I3_native_failure_finally','faults':['OSError','KeyboardInterrupt'],
                         'failed_parent_calls':0,'active_source_leases_after_failure':0,'next_current':200}

    def _completion_expiry(self, method='GET', *, action='history', fault=None):
        server = self.start(); rt = server._reference_runtime; now = [0.0]; rt.clock = lambda: now[0]
        status, initial_headers, initial_body = self.request(server, self.route()); self.assertEqual(status, 200)
        cookie = initial_headers['Set-Cookie'].split(';')[0]; csrf = initial_headers['X-Intake-Reference-CSRF']
        sid = cookie.split('=')[1]; item = rt.sessions[sid]; binding = self.store._existing_binding
        parent, connect, opened, info = rt.parent, sqlite3.connect, Path.open, binding.backend.info
        calls, sql, retained = [], [], []; before = self.snapshot()
        def observed_parent(*args, **kwargs):
            calls.append(args[2]['action']); value = parent(*args, **kwargs); now[0] = 900.0
            if fault == 'closing':
                with rt.lock: rt.closing = True
            elif fault == 'binding': self.store._existing_binding = object()
            elif fault == 'typed': return {}
            elif fault == 'parent': raise ValueError('PRIVATE after parent')
            return value
        def observed_sql(*args, **kwargs):
            sql.append(kwargs.get('uri') is True and str(args[0]).endswith('?mode=ro'))
            return connect(*args, **kwargs)
        def observed_open(path, *args, **kwargs):
            if path.parent == self.store.root / 'blobs': retained.append(1)
            return opened(path, *args, **kwargs)
        def native_failed(*args, **kwargs):
            info(*args, **kwargs); now[0] = 900.0; raise OSError('PRIVATE native completion')
        stale_status = None
        try:
            with ExitStack() as patches:
                patches.enter_context(mock.patch.object(rt, 'parent', observed_parent))
                patches.enter_context(mock.patch.object(sqlite3, 'connect', observed_sql))
                patches.enter_context(mock.patch.object(Path, 'open', observed_open))
                if fault == 'native': patches.enter_context(mock.patch.object(binding.backend, 'info', native_failed))
                response = (self.current(server, cookie, csrf) if action == 'current' else
                            self.request(server, self.route(), method, headers={'Cookie':cookie}))
                if fault is None and action == 'history' and response[0] == 200:
                    stale_status = self.request(server, self.route(), headers={'Cookie':cookie})[0]
        finally: self.store._existing_binding = binding
        self.assertEqual(self.snapshot(), before); self.assertTrue(all(sql))
        self.assertEqual(rt.active, 0); self.assertFalse(rt.source_active); self.assertFalse(rt.leases)
        return {'server':server,'response':response,'initial_body':initial_body,'calls':calls,'sql':sql,
                'retained':len(retained),'old_last_seen':item['last_seen'],'sid':sid,'stale_status':stale_status}

    def _assert_completed_history_expiry(self, method):
        result = self._completion_expiry(method); status, headers, body = result['response']
        self.assertEqual(status, 200)
        self.assertEqual(headers['X-Intake-Reference-Read-Allowed'], 'false')
        self.assertFalse('X-Intake-Reference-CSRF' in headers); self.assertFalse('Set-Cookie' in headers)
        self.assertEqual(body, b'' if method == 'HEAD' else result['initial_body'])
        self.assertEqual(int(headers['Content-Length']), len(result['initial_body']))
        self.assertEqual((result['calls'], len(result['sql']), result['retained']), (['history'],1,0))
        self.assertEqual(result['old_last_seen'], 0.0); self.assertEqual(result['stale_status'], 403)
        rt = result['server']._reference_runtime; self.assertFalse(rt.sessions)
        self.assertIsNone(result['server']._reference_action_binding(result['sid']))
        self.evidence = {'kind':'049_I4_history_completed_expiry','method':method,'status':200,
                         'formal_parent_calls':1,'SQLite_ro_connections':1,'retained_opens':0,
                         'original_history_preserved':True,'Read_Allowed':False,'CSRF_SetCookie_new_session_idle_renewal':0,
                         'old_cookie_followup':403,'old_cookie_followup_parent_SQL':0,'binding_expired':True,
                         'HEAD_body0':method == 'HEAD','inputs_unchanged':True}

    def test_reference_history_GET_completed_expiry_keeps_metadata_and_drops_authority(self):
        self._assert_completed_history_expiry('GET')

    def test_reference_history_HEAD_completed_expiry_keeps_metadata_and_drops_authority(self):
        self._assert_completed_history_expiry('HEAD')

    def test_reference_admitted_current_completion_expiry_does_not_reauthenticate_or_renew(self):
        result = self._completion_expiry(action='current'); status, headers, body = result['response']
        self.assertEqual(status, 200); value = json.loads(body)
        self.assertEqual((len(value), value['status']), (10, 'current'))
        self.assertFalse('Set-Cookie' in headers); self.assertFalse('X-Intake-Reference-CSRF' in headers)
        self.assertEqual((result['calls'], len(result['sql'])), (['current'],1)); self.assertGreater(result['retained'], 0)
        self.assertEqual(result['old_last_seen'], 0.0)
        self.assertIsNone(result['server']._reference_action_binding(result['sid']))
        self.evidence = {'kind':'049_I4_current_completed_expiry','status':200,'formal_parent_calls':1,
                         'SQLite_ro_connections':1,'actual_retained_opens':result['retained'],
                         'post_parent_idle_renewal':0,'expired_binding':True,'inputs_unchanged':True}

    def test_reference_completion_expiry_does_not_promote_closing_binding_native_or_typed_failures(self):
        for fault in ('closing','binding','native','typed','parent'):
            with self.subTest(fault=fault):
                result = self._completion_expiry(fault=fault); status, headers, body = result['response']
                self.assertEqual((status, json.loads(body)['error']['code']), (503,'intake_reference_ui_unavailable'))
                self.assertFalse('Set-Cookie' in headers); self.assertFalse('X-Intake-Reference-CSRF' in headers)
                expected = 0 if fault == 'native' else 1
                self.assertEqual((len(result['calls']), len(result['sql']), result['retained']), (expected,expected,0))
                self.assertEqual(result['old_last_seen'], 0.0)
        self.evidence = {'kind':'049_I4_completion_expiry_failure_precedence',
                         'faults':['closing','binding','native','typed','parent'],'status':503,'authority_headers':0}



class ReferenceActionsHostTests(unittest.TestCase):
    """053 uses genuine025/043/046/042; HTTP owns session/source admission."""
    request = ReferenceHostTests.request
    raw = ReferenceHostTests.raw
    route = ReferenceHostTests.route
    bootstrap = ReferenceHostTests.bootstrap
    source_headers = ReferenceHostTests.source_headers
    fixed = ReferenceHostTests.fixed

    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.local'
        parent.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='r053-unit-', dir=parent)
        self.addCleanup(temporary.cleanup)
        self.fixture = ReferenceFixture(temporary.name, registered=False)
        self.store = Store.open_existing(str(self.fixture.legacy.root)); self.addCleanup(self.store.close)
        self.ident = self.fixture.intake_id
        from tests.test_intake_case_references import catalog_fixture, context_for, response_for
        self.catalog = catalog_fixture(); context = context_for(self.catalog); response = response_for(context)
        self.supplied = {'intake_id': self.ident, 'case_context': context, 'validated_response': response,
                         'producer_name': response['expected_producer']['name']}

    def start(self, *, enabled=True, **options):
        import inspect
        self.assertIn('intake_reference_review_inputs', inspect.signature(create_server).parameters)
        values = dict(fcc_case_catalog=self.catalog, intake_reference_store=self.store,
                      intake_reference_read_scope=(self.ident,), intake_reference_append_scope=(self.ident,),
                      intake_reference_review_inputs=(self.supplied,)) if enabled else {}
        values.update(options)
        server = create_server(self.store.root, port=0, **values)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        def stop():
            if type(server) is host_module.ThreadingHTTPServer: server.shutdown()
            server.server_close(); thread.join(6); self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        return server

    def prepare(self, server, cookie, csrf, input_id=None, replace=None):
        if input_id is None:
            status, headers, _ = self.request(server, self.route(), headers={'Cookie': cookie})
            self.assertEqual(status, 200); input_id = headers['X-Intake-Reference-Review-Input']
        return self.post(server, cookie, csrf, 'prepare',
                         {'schema_version': 1, 'review_input_id': input_id, 'replace_handle_id': replace})

    def post(self, server, cookie, csrf, action, value):
        return self.request(server, self.route(action), 'POST', json.dumps(value).encode('utf-8'),
                            self.source_headers(server, cookie, csrf))

    def append_request(self, envelope):
        preview = envelope['preview']
        return {'schema_version': 1, 'handle_id': envelope['handle_id'], 'intake_id': self.ident,
                'request_id': envelope['append_request_id'], 'preparation_id': preview['preparation_id'],
                'expected_snapshot_id': preview['observation']['snapshot_id'],
                'expected_head_record_id': preview['observation']['head_record_id']}

    def counts(self):
        with self.store.connection() as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            return tuple(connection.execute('SELECT count(*) FROM ' + table).fetchone()[0] if table in tables else 0
                         for table in ('intake_reference_records', 'intake_reference_events', 'intake_reference_heads'))

    def test_actions_defaults_and_empty_inputs_never_import046(self):
        import inspect
        self.assertIn('intake_reference_append_scope', inspect.signature(create_server).parameters)
        original = host_module.importlib.import_module
        def imported(name, *args, **kwargs):
            self.assertNotIn('intake_reference_review_host', name)
            return original(name, *args, **kwargs)
        with mock.patch.object(host_module.importlib, 'import_module', side_effect=imported):
            server = self.start(intake_reference_review_inputs=(), intake_reference_append_scope=())
            status, headers, _ = self.request(server, self.route())
            self.assertEqual(status, 200)
            for name in ('Prepare', 'Append'):
                self.assertEqual(headers['X-Intake-Reference-' + name + '-Allowed'], 'false')
            self.assertNotIn('X-Intake-Reference-Review-Input', headers)
            self.assertEqual(self.counts(), (0, 0, 0))
            empty = create_server(self.store.root, port=0, intake_reference_append_scope=(), intake_reference_review_inputs=())
            empty.server_close()

    def test_actions_None_nondefault_options_rejected_before_bind(self):
        import inspect
        self.assertIn('intake_reference_review_inputs', inspect.signature(create_server).parameters)
        for changes in ({'intake_reference_append_scope': (self.ident,)}, {'intake_reference_review_inputs': (self.supplied,)},
                        {'intake_reference_append_scope': None}, {'intake_reference_review_inputs': []}):
            with mock.patch.object(host_module.ThreadingHTTPServer, 'server_bind', side_effect=AssertionError('bind')):
                self.fixed('invalid_request', lambda: create_server(self.store.root, port=0, **changes))

    def test_actions_static_actual_C1_and_nonmutating_missing_boundary(self):
        server = self.start(enabled=False)
        route = '/intake-reference-actions/actions.mjs'
        status, headers, body = self.request(server, route)
        path = host_module.FRONTEND / 'intake_reference_actions/actions.mjs'
        self.assertEqual((status, body), (200, path.read_bytes()))
        self.assertEqual(headers['Content-Type'], 'text/javascript; charset=utf-8')
        self.assertEqual(self.request(server, route, 'HEAD')[2], b'')
        self.assertEqual(self.request(server, route, 'POST')[0], 405)
        for alias in (route + '?x=1', route.replace('/actions.', '//actions.'), route.replace('actions.mjs', '%61ctions.mjs')):
            self.assertEqual(self.request(server, alias)[0], 404)
        original = Path.read_bytes
        def missing(value):
            if value == path: raise FileNotFoundError()
            return original(value)
        with mock.patch.object(Path, 'read_bytes', missing):
            self.assertEqual(self.request(server, route)[0], 404)
        self.assertEqual(path.read_bytes(), body)

    def test_actions_genuine_prepare_append_and_original_replay(self):
        source = deepcopy(self.supplied); server = self.start(); cookie, csrf = self.bootstrap(server)
        status, headers, _ = self.request(server, self.route(), headers={'Cookie': cookie})
        self.assertEqual(status, 200)
        self.assertEqual(headers['X-Intake-Reference-Prepare-Allowed'], 'true')
        self.assertEqual(headers['X-Intake-Reference-Append-Allowed'], 'true')
        status, _, body = self.prepare(server, cookie, csrf, headers['X-Intake-Reference-Review-Input'])
        self.assertEqual(status, 200, body); envelope = json.loads(body)
        self.assertEqual(len(envelope), 6); self.assertEqual(len(envelope['preview']), 11)
        self.assertEqual(self.counts(), (0, 0, 0))
        request = self.append_request(envelope); original = deepcopy(request)
        status, _, body = self.post(server, cookie, csrf, 'append', request)
        self.assertEqual(status, 200, body); first = json.loads(body)
        self.assertEqual(first['binding_status'], 'current_at_append')
        self.assertIs(first['verification']['operational_authority_granted'], False)
        status, _, body = self.post(server, cookie, csrf, 'append', request)
        self.assertEqual(status, 200, body); self.assertEqual(json.loads(body), {**first, 'replayed': True})
        self.assertEqual(self.counts(), (1, 1, 1)); self.assertEqual(request, original); self.assertEqual(source, self.supplied)

    def test_actions_head_conflict_is_normal_stored_result_and_original_replay(self):
        server = self.start(); cookie, csrf = self.bootstrap(server)
        envelopes = []
        for _ in range(2):
            status, _, body = self.prepare(server, cookie, csrf)
            self.assertEqual(status, 200, body); envelopes.append(json.loads(body))
        requests = [self.append_request(envelope) for envelope in envelopes]
        status, _, body = self.post(server, cookie, csrf, 'append', requests[0]); self.assertEqual(status, 200, body)
        winner = json.loads(body)
        status, _, body = self.post(server, cookie, csrf, 'append', requests[1]); self.assertEqual(status, 200, body)
        conflict = json.loads(body); self.assertEqual(conflict['binding_status'], 'head_conflict')
        self.assertIs(conflict['stored'], True); self.assertIs(conflict['append_observation']['head_advanced'], False)
        self.assertEqual(conflict['append_observation']['head_after_record_id'], winner['record_id'])
        status, _, body = self.post(server, cookie, csrf, 'append', requests[1]); self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body), {**conflict, 'replayed': True}); self.assertEqual(self.counts(), (2, 2, 1))

    def test_actions_append_scope_default_denies_without_consuming_preparation(self):
        server = self.start(intake_reference_append_scope=()); cookie, csrf = self.bootstrap(server)
        _, headers, _ = self.request(server, self.route(), headers={'Cookie': cookie})
        self.assertEqual(headers['X-Intake-Reference-Prepare-Allowed'], 'true')
        self.assertEqual(headers['X-Intake-Reference-Append-Allowed'], 'false')
        status, _, body = self.prepare(server, cookie, csrf); self.assertEqual(status, 200, body)
        status, _, _ = self.post(server, cookie, csrf, 'append', self.append_request(json.loads(body)))
        self.assertEqual(status, 403); self.assertEqual(self.counts(), (0, 0, 0))

    def test_actions_history_late_expiry_inherits200_without_reissuing_capabilities(self):
        server = self.start(); rt = server._reference_runtime; now = [100.0]; rt.clock = lambda: now[0]
        cookie, csrf = self.bootstrap(server); sid = cookie.split('=', 1)[1]; original = rt.parent
        def late(*args, **kwargs):
            value = original(*args, **kwargs); now[0] += 901; return value
        with mock.patch.object(rt, 'parent', side_effect=late):
            status, headers, _ = self.request(server, self.route(), headers={'Cookie': cookie})
        self.assertEqual(status, 200)
        for name in ('Read', 'Prepare', 'Append'):
            self.assertEqual(headers['X-Intake-Reference-' + name + '-Allowed'], 'false')
        for name in ('Set-Cookie', 'X-Intake-Reference-CSRF', 'X-Intake-Reference-Review-Input'):
            self.assertNotIn(name, headers)
        self.assertNotIn(sid, rt.sessions)

    @contextmanager
    def paused_http(self, operation, function, *, event='call', observe=None):
        """Pause real code using the profiler; parent functions remain untouched."""
        code = getattr(function, '__wrapped__', function).__code__
        entered = threading.Event(); release = threading.Event(); results = []; returned = []
        previous = threading.getprofile()
        def profile(frame, kind, value):
            if observe is not None: observe(frame, kind, value)
            if frame.f_code is code:
                if kind == 'return' and type(value) is dict: returned.append(deepcopy(value))
                if kind == event and not entered.is_set():
                    entered.set()
                    if not release.wait(15): raise RuntimeError('053 test pause expired')
        def run():
            try: results.append(('result', operation()))
            except BaseException as error: results.append(('error', error))
        threading.setprofile(profile)
        worker = threading.Thread(target=run, daemon=True); worker.start()
        try:
            self.assertTrue(entered.wait(10)); yield results, release, returned
        finally:
            release.set(); worker.join(15); threading.setprofile(previous)
            self.assertFalse(worker.is_alive()); self.assertTrue(results)

    def test_actions_bad_config_is_fixed_before_bind_and_empty_inputs_remain_lazy(self):
        for options, suffix in [({'intake_reference_append_scope': []}, 'invalid_request'),
                                ({'intake_reference_append_scope': ('DUP', 'DUP')}, 'invalid_request'),
                                ({'intake_reference_review_inputs': []}, 'invalid_request')]:
            with mock.patch.object(host_module.ThreadingHTTPServer, 'server_bind', side_effect=AssertionError('bind')):
                self.fixed(suffix, lambda: create_server(self.store.root, port=0,
                    intake_reference_store=self.store, **options))
        from labflow import intake_reference_review_host as api
        for inputs, expected in [((self.supplied, self.supplied), 'invalid_request'),
                                 ((self.supplied,) * 101, 'input_limit')]:
            with self.assertRaises(api.IntakeReferenceReviewHostError) as caught:
                create_server(self.store.root, port=0, intake_reference_store=self.store,
                    fcc_case_catalog=self.catalog, intake_reference_read_scope=(self.ident,),
                    intake_reference_review_inputs=inputs)
            self.assertEqual(caught.exception.code, 'intake_reference_review_host_' + expected)
            self.assertIsNone(caught.exception.__context__); self.assertIsNone(caught.exception.__cause__)

    def test_actions_wire_limits_methods_auth_and_aliases_never_dispatch_core(self):
        server = self.start(); cookie, csrf = self.bootstrap(server)
        _, headers, _ = self.request(server, self.route(), headers={'Cookie': cookie})
        request = {'schema_version': 1, 'review_input_id': headers['X-Intake-Reference-Review-Input'], 'replace_handle_id': None}
        for action in ('prepare', 'append'):
            for method in ('GET', 'HEAD', 'PUT', 'OPTIONS'):
                status, fields, body = self.request(server, self.route(action), method)
                self.assertEqual((status, fields['Allow'], body), (405, 'POST', b''))
        for route in (self.route('prepare') + '?x=1', self.route('prepare').replace('/prepare', '/%70repare')):
            self.assertIn(self.request(server, route, 'POST', b'{}', self.source_headers(server, cookie, csrf))[0], (400, 404))
        invalid = [b'\xef\xbb\xbf{}', b'[]', b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}',
                   json.dumps({**request, 'schema_version': True}).encode(), json.dumps({**request, 'allow_append': True}).encode(),
                   json.dumps({**request, 'replace_handle_id': 'X' * 64}).encode(), b'{"a":"\\ud800"}']
        for body in invalid:
            status, _, _ = self.request(server, self.route('prepare'), 'POST', body, self.source_headers(server, cookie, csrf))
            self.assertEqual(status, 400, body)
        self.assertEqual(self.request(server, self.route('prepare'), 'POST', b'x' * 16385, self.source_headers(server, cookie, csrf))[0], 413)
        self.assertEqual(self.post(server, cookie, '0' * 64, 'prepare', request)[0], 403)
        self.assertEqual(self.post(server, '', csrf, 'prepare', request)[0], 403)
        self.assertEqual(self.counts(), (0, 0, 0))
        self.assertEqual(server._reference_runtime.active, 0)

    def test_actions_exact_error_allowlist68_and_parent_conflict_status(self):
        server = self.start(); rt = server._reference_runtime
        self.assertEqual(sum(len(values) for values in rt.action_errors.values()) + len(host_module._REFERENCE_CODES), 68)
        for cls, codes in rt.action_errors.items():
            for code in codes:
                error = cls(code)
                actual, status = rt.action_failure(error)
                self.assertEqual(actual, code)
                self.assertIn(status, {400, 403, 404, 409, 410, 413, 503})
            unknown = cls(next(iter(codes))); unknown.code = next(iter(codes)) + '_PRIVATE'
            self.assertEqual(rt.action_failure(unknown), ('intake_reference_ui_unavailable', 503))
            class Child(cls): pass
            self.assertEqual(rt.action_failure(Child(next(iter(codes)))), ('intake_reference_ui_unavailable', 503))
        from labflow.intake_reference_ledger import IntakeReferenceLedgerError
        self.assertEqual(rt.action_failure(IntakeReferenceLedgerError('intake_reference_ledger_request_conflict')),
                         ('intake_reference_ledger_request_conflict', 409))
        busy = rt.action_error_type('unavailable', status=429)
        self.assertEqual(rt.action_failure(busy), ('intake_reference_review_host_unavailable', 429))
        self.assertEqual(rt.action_failure(RuntimeError('PRIVATE SQL/path')), ('intake_reference_ui_unavailable', 503))

    def test_actions_other_session_frozen_request_replacement_and_capacity(self):
        server = self.start(); cookie, csrf = self.bootstrap(server)
        status, _, body = self.prepare(server, cookie, csrf); self.assertEqual(status, 200, body)
        old = json.loads(body); request = self.append_request(old)
        other_cookie, other_csrf = self.bootstrap(server)
        self.assertEqual(self.post(server, other_cookie, other_csrf, 'append', request)[0], 403)
        self.assertEqual(self.post(server, cookie, csrf, 'append', {**request, 'request_id': 'OTHER053'})[0], 409)
        status, _, body = self.prepare(server, cookie, csrf, replace=old['handle_id']); self.assertEqual(status, 200, body)
        new = json.loads(body)
        self.assertEqual(self.post(server, cookie, csrf, 'append', request)[0], 410)
        self.assertEqual(self.prepare(server, cookie, csrf)[0], 200)
        self.assertEqual(self.prepare(server, cookie, csrf)[0], 503)
        self.assertEqual(self.post(server, cookie, csrf, 'append', self.append_request(new))[0], 200)

    def test_actions_expiry_between_outer_admission_and_core_reservation_retires_new_handle(self):
        from labflow import intake_reference_review_host as api
        server = self.start(); rt = server._reference_runtime; now = [100.0]; rt.clock = lambda: now[0]
        cookie, csrf = self.bootstrap(server); sid = cookie.split('=', 1)[1]
        binding = server._reference_action_binding(sid)
        with self.paused_http(lambda: self.prepare(server, cookie, csrf), api.ReferenceReviewActions.prepare) as (results, release, returned):
            now[0] += 901
            self.assertEqual(self.request(server, self.route(), headers={'Cookie': cookie})[0], 403)
            release.set()
        self.assertEqual(results[0][0], 'result'); self.assertEqual(results[0][1][0], 403)
        self.assertEqual(len(returned), 1)
        with self.assertRaises(api.IntakeReferenceReviewHostError) as caught:
            rt.actions.append(binding, self.ident, self.append_request(returned[0]))
        self.assertEqual(caught.exception.status, 410)
        self.assertEqual(rt.active, 0); self.assertFalse(rt.source_active)

    def test_actions_prepare_parent_io_unlocks_mutex_and_source_is_shared_queue0(self):
        from labflow import intake_reference_review as api
        server = self.start(); rt = server._reference_runtime; cookie, csrf = self.bootstrap(server)
        status, _, body = self.prepare(server, cookie, csrf); self.assertEqual(status, 200, body)
        request = self.append_request(json.loads(body))
        with self.paused_http(lambda: self.prepare(server, cookie, csrf), api.prepare_reference_review) as (results, release, _):
            acquired = rt.lock.acquire(timeout=.5); self.assertTrue(acquired)
            if acquired: rt.lock.release()
            self.assertTrue(rt.source_active); self.assertEqual(rt.active, 1)
            self.assertEqual(self.prepare(server, cookie, csrf)[0], 429)
            self.assertEqual(self.post(server, cookie, csrf, 'append', request)[0], 429)
            self.assertEqual(ReferenceHostTests.current(self, server, cookie, csrf)[0], 429)
            release.set()
        self.assertEqual(results[0][1][0], 200); self.assertEqual(rt.active, 0)

    def test_actions_append_admitted_before_session_expiry_keeps_truthful_registration(self):
        from labflow import intake_reference_review as api
        server = self.start(); rt = server._reference_runtime; now = [100.0]; rt.clock = lambda: now[0]
        cookie, csrf = self.bootstrap(server)
        status, _, body = self.prepare(server, cookie, csrf); self.assertEqual(status, 200, body)
        request = self.append_request(json.loads(body))
        with self.paused_http(lambda: self.post(server, cookie, csrf, 'append', request), api.append_reference_review) as (results, release, _):
            now[0] += 901
            self.assertEqual(self.request(server, self.route(), headers={'Cookie': cookie})[0], 403)
            release.set()
        self.assertEqual(results[0][0], 'result'); self.assertEqual(results[0][1][0], 200)
        self.assertTrue(json.loads(results[0][1][2])['stored']); self.assertEqual(self.counts(), (1, 1, 1))
        self.assertEqual(self.post(server, cookie, csrf, 'append', request)[0], 403)

    def test_actions_close_waits_parent_finally_then_close_outside_mutex_and_borrowed_store(self):
        from labflow import intake_reference_review as parent
        from labflow import intake_reference_review_host as api
        server = self.start(); rt = server._reference_runtime; cookie, csrf = self.bootstrap(server)
        closed = threading.Event(); close_results = []; observed = []
        close_code = api.ReferenceReviewActions.close.__wrapped__.__code__
        def observe(frame, event, value):
            if event == 'call' and frame.f_code is close_code:
                observed.append((rt.active, rt.lock._is_owned()))
        def close():
            try: server.server_close(); close_results.append('closed')
            except BaseException as error: close_results.append(error)
            finally: closed.set()
        with self.paused_http(lambda: self.prepare(server, cookie, csrf), parent.prepare_reference_review, observe=observe) as (_, release, _):
            closer = threading.Thread(target=close); closer.start()
            deadline = time.monotonic() + 3
            while not rt.closing and time.monotonic() < deadline: time.sleep(.005)
            self.assertTrue(rt.closing); self.assertFalse(closed.is_set()); self.assertEqual(observed, [])
            self.assertTrue(rt.source_active); self.assertEqual(rt.active, 1)
            release.set(); closer.join(8); self.assertFalse(closer.is_alive())
        self.assertEqual(close_results, ['closed']); self.assertEqual(observed, [(0, False)])
        self.assertTrue(rt.closed); self.assertFalse(rt.workers); self.assertEqual(rt.active, 0)
        self.assertIs(self.store.__enter__(), self.store)

    def test_actions_committed_response_abort_preserves_original_replay(self):
        from labflow import intake_reference_review_host as api
        server = self.start(); rt = server._reference_runtime; cookie, csrf = self.bootstrap(server)
        status, _, body = self.prepare(server, cookie, csrf); self.assertEqual(status, 200, body)
        request = self.append_request(json.loads(body)); original = deepcopy(request)
        connection = http.client.HTTPConnection(*server.server_address, timeout=6)
        def send():
            connection.request('POST', self.route('append'), json.dumps(request).encode(), self.source_headers(server, cookie, csrf))
            try:
                response = connection.getresponse(); return response.status, response.read()
            except (OSError, http.client.HTTPException): return 'delivery_unknown'
            finally: connection.close()
        with self.paused_http(send, api.ReferenceReviewActions.append, event='return') as (_, release, _):
            self.assertEqual(self.counts(), (1, 1, 1)); self.assertTrue(rt.source_active)
            connection.close(); self.assertEqual(self.post(server, cookie, csrf, 'append', request)[0], 429)
            release.set()
        deadline = time.monotonic() + 3
        while rt.active and time.monotonic() < deadline: time.sleep(.005)
        status, _, body = self.post(server, cookie, csrf, 'append', request)
        self.assertEqual(status, 200, body); self.assertIs(json.loads(body)['replayed'], True)
        self.assertEqual(request, original); self.assertEqual(self.counts(), (1, 1, 1))

    def test_actions_typed_response_failure_preserves_fixed_error_and_no_authority(self):
        from labflow import intake_reference_review_host as api
        original = api.ReferenceReviewActions.prepare
        def corrupted(actions, *args, **kwargs):
            value = original(actions, *args, **kwargs)
            value['preview']['verification']['operational_authority_granted'] = True
            return value
        with mock.patch.object(api.ReferenceReviewActions, 'prepare', corrupted):
            server = self.start(); cookie, csrf = self.bootstrap(server)
            status, _, body = self.prepare(server, cookie, csrf)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'error': {'code': 'intake_reference_ui_unavailable'}})
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_actions_nonNone_close_is_not_confirmed_closed_after_worker_cleanup(self):
        server = self.start(); rt = server._reference_runtime
        original = rt.action_methods['close']
        def unconfirmed(actions):
            original(actions); return 'PRIVATE-unconfirmed'
        rt.action_methods['close'] = unconfirmed
        self.fixed('unavailable', server.server_close)
        self.assertEqual(server.socket.fileno(), -1); self.assertFalse(rt.workers)
        self.assertFalse(rt.actions_closed); self.assertFalse(rt.closed)
        rt.action_methods['close'] = original
        server.server_close(); self.assertTrue(rt.closed); self.assertTrue(rt.actions_closed)
        self.assertIs(self.store.__enter__(), self.store)


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
