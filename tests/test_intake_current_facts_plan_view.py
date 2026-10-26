"""Current-facts HTTP contract; authored setup is distinct from readonly reads."""
from copy import deepcopy
import hashlib
import http.client
import importlib
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from labflow.store import canonical
from labflow.ui_read_model import IntakeReadModel, ReadModelError
from labflow.ui_server import create_server, _conducted_preview_response
from test_ui_read_model import conducted_context_fixture

API = importlib.import_module('labflow.intake_current_facts_plan')
MODEL = importlib.import_module('labflow.ui_read_model')
PREFIX = 'intake_current_facts_plan_view_'
METHOD = dict(method_id='conducted_synthetic', method_version=1,
              metric='on', reference_plane='source_output')
VERIFICATION = dict(scope='two_readonly_current_snapshots', current_completion='not_assessed',
                    permanent_current_approval=False, method_approval='not_assessed',
                    regulatory='not_assessed', physical_verified=False,
                    execution_authority=False, rerun_authority=False, business_writes=False)


def selection(intake_id, revision=1):
    # Old manual settings/basis are deliberately unrelated; this view uses only method.
    return dict(intake_id=intake_id, revision=revision,
                source_settings={'ignored_manual_value': 999},
                basis={'ignored_manual_basis': 'not a source citation'}, method=deepcopy(METHOD))


def files(root):
    return {p.relative_to(root).as_posix():
            (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


class CurrentFactsViewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='current-facts-view-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.fixture = conducted_context_fixture(self.root / 'input')
        self.workspace = self.fixture['store'].root
        self.intake_id = self.fixture['intake_id']
        self.model = IntakeReadModel(self.workspace)
        self.selected = selection(self.intake_id)

    def view(self, selected='default'):
        method = getattr(self.model, 'conducted_current_facts_view', None)
        self.assertTrue(callable(method), 'missing assigned current-facts read-model method')
        return method(self.intake_id, self.selected if selected == 'default' else selected)

    def start(self, selected='default', workspace=None):
        server = create_server(self.workspace if workspace is None else workspace, port=0,
            conducted_plan_preview_inputs=self.selected if selected == 'default' else selected)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
        thread.start()
        def stop():
            address = server.server_address
            server.shutdown(); server.server_close(); thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(server.socket.fileno(), -1)
            with socket.socket() as probe:
                probe.bind(address)
        self.addCleanup(stop)
        return server

    def read(self, server, *, method='GET', suffix='', headers=None, body=None, path=None):
        address = server.server_address
        connection = http.client.HTTPConnection(*address, timeout=5)
        try:
            endpoint = path or '/api/intakes/' + self.intake_id + '/conducted-current-facts' + suffix
            connection.request(method, endpoint, body=body,
                headers={'Origin': 'http://127.0.0.1:' + str(address[1]),
                         'Sec-Fetch-Site': 'same-origin', **(headers or {})})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_genuine_model_preserves_native_wrapper_and_rechecks_without_manual_settings(self):
        before = files(self.root)
        observed = []
        genuine = API.read_current_conducted_plan_from_facts
        def native(*args, **kwargs):
            result = genuine(*args, **kwargs)
            observed.append((deepcopy(kwargs), deepcopy(result)))
            return result
        reads = []
        genuine_read = IntakeReadModel.current_conducted_plan_context
        def current(model, intake_id):
            result = genuine_read(model, intake_id)
            reads.append(deepcopy(result))
            return result
        with mock.patch.object(API, 'read_current_conducted_plan_from_facts', side_effect=native), \
             mock.patch.object(IntakeReadModel, 'current_conducted_plan_context', current):
            value = self.view()
        self.assertEqual(len(observed), 1)
        self.assertEqual(len(reads), 2)
        self.assertEqual(observed[0][0], dict(method=METHOD, expected_revision=1,
                                            expected_context_sha256=None))
        self.assertEqual(value['current'], observed[0][1])
        self.assertEqual(value['status'], 'available')
        self.assertEqual(value['reasons'], [])
        self.assertEqual(value['verification'], VERIFICATION)
        self.assertEqual(value['recheck']['status'], 'unchanged')
        self.assertEqual(value['recheck']['before'], value['recheck']['after'])
        self.assertEqual(set(value['current']), {'context', 'analysis', 'facts_plan'})
        self.assertEqual(value['recheck']['before']['context_sha256'],
            hashlib.sha256(canonical(reads[0]['context']).encode('utf-8')).hexdigest())
        self.assertEqual(files(self.root), before)

    def test_none_foreign_and_invalid_method_are_rejected_before_native_or_store(self):
        bad = deepcopy(self.selected); bad['method']['method_version'] = True
        foreign = selection('I-foreign')
        for selected, code in [(None, 'not_provided'), (foreign, 'other_intake'),
                               (bad, 'selection_invalid')]:
            with self.subTest(code=code), \
                 mock.patch.object(API, 'read_current_conducted_plan_from_facts',
                                   side_effect=AssertionError('must not read Store')):
                with self.assertRaises(ReadModelError) as caught:
                    self.view(selected)
                self.assertEqual(caught.exception.code, PREFIX + code)

    def test_expected_revision_mismatch_is_unavailable_not_a_new_current_plan(self):
        with self.assertRaises(ReadModelError) as caught:
            self.view(selection(self.intake_id, 99))
        self.assertEqual(caught.exception.code, PREFIX + 'revision_changed')

    def test_named_typed_recheck_change_keeps_first_observation_and_never_claims_store_drift(self):
        before = files(self.root)
        genuine = IntakeReadModel.current_conducted_plan_context
        calls = []
        def typed_recheck(model, intake_id):
            result = genuine(model, intake_id)
            calls.append(deepcopy(result))
            if len(calls) == 2:
                result['context']['instructions'] += '\nNamed typed recheck change only.'
            return result
        with mock.patch.object(IntakeReadModel, 'current_conducted_plan_context', typed_recheck):
            value = self.view()
        self.assertEqual(value['status'], 'stale')
        self.assertEqual(value['reasons'], ['current_changed'])
        self.assertEqual(value['recheck']['status'], 'changed')
        self.assertNotEqual(value['recheck']['before'], value['recheck']['after'])
        self.assertEqual(value['current']['context'], calls[0]['context'])
        self.assertEqual(value['verification'], VERIFICATION)
        self.assertEqual(files(self.root), before)

    def test_post_read_failure_is_not_invented_changed_and_first_controls_propagate(self):
        genuine = IntakeReadModel.current_conducted_plan_context
        calls = []
        def unavailable(model, intake_id):
            calls.append(1)
            if len(calls) == 2:
                raise ReadModelError('store_unavailable')
            return genuine(model, intake_id)
        with mock.patch.object(IntakeReadModel, 'current_conducted_plan_context', unavailable):
            with self.assertRaises(ReadModelError) as caught:
                self.view()
        self.assertEqual(caught.exception.code, PREFIX + 'recheck_failed')
        for first in [MemoryError('private-first'), KeyboardInterrupt('private-first'),
                      SystemExit('private-first'), GeneratorExit('private-first')]:
            with self.subTest(control=type(first).__name__), \
                 mock.patch.object(API, 'read_current_conducted_plan_from_facts', side_effect=first):
                with self.assertRaises(type(first)) as caught:
                    self.view()
                self.assertIs(caught.exception, first)

    def test_genuine_reader_first_control_survives_later_sql_close_control(self):
        self.assertTrue(callable(getattr(self.model, 'conducted_current_facts_view', None)),
                        'missing assigned current-facts read-model method')
        genuine = sqlite3.connect
        first, later = MemoryError('first-read-control'), KeyboardInterrupt('later-close-control')
        closed = []
        class Connection:
            def __init__(self, connection):
                object.__setattr__(self, 'connection', connection)
                object.__setattr__(self, 'poisoned', False)
            def __getattr__(self, name): return getattr(self.connection, name)
            def __setattr__(self, name, value):
                if name == 'poisoned': object.__setattr__(self, name, value)
                else: setattr(self.connection, name, value)
            def execute(self, sql, *args, **kwargs):
                if 'SELECT i.revision,r.synthetic' in sql:
                    self.poisoned = True
                    raise first
                return self.connection.execute(sql, *args, **kwargs)
            def close(self):
                self.connection.close()
                if self.poisoned:
                    closed.append(True)
                    raise later
        def connect(*args, **kwargs): return Connection(genuine(*args, **kwargs))
        with mock.patch.object(MODEL.sqlite3, 'connect', connect):
            with self.assertRaises(MemoryError) as caught:
                self.view()
        self.assertIs(caught.exception, first)
        self.assertEqual(closed, [True])

    def test_current_binding_tamper_and_non_native_or_overlimit_are_not_success(self):
        self.assertTrue(callable(getattr(self.model, 'conducted_current_facts_view', None)),
                        'missing assigned current-facts read-model method')
        original = API.read_current_conducted_plan_from_facts(
            self.workspace, self.intake_id, method=METHOD)
        bad = deepcopy(original)
        bad['facts_plan']['plan_input']['binding']['analysis_sha256'] = '0' * 64
        with mock.patch.object(API, 'read_current_conducted_plan_from_facts', return_value=bad):
            with self.assertRaises(ReadModelError) as caught:
                self.view()
        self.assertEqual(caught.exception.code, PREFIX + 'current_invalid')
        encode = getattr(MODEL, '_current_facts_json', None)
        self.assertTrue(callable(encode), 'missing bounded native current-facts serializer')
        class Subclass(dict): pass
        for data, code in [(Subclass(), 'current_invalid'), ({'x': float('nan')}, 'current_invalid'),
                           ({'x': '\ud800'}, 'current_invalid'), ([None] * 400001, 'input_limit')]:
            with self.subTest(code=code), self.assertRaises(ReadModelError) as caught:
                encode(data, 9 * 1024 * 1024)
            self.assertEqual(caught.exception.code, PREFIX + code)
        deep = None
        for unused in range(49): deep = [deep]
        with self.assertRaises(ReadModelError) as caught: encode(deep, 9 * 1024 * 1024)
        self.assertEqual(caught.exception.code, PREFIX + 'input_limit')
        self.assertEqual(encode('x', 3), b'"x"')
        with self.assertRaises(ReadModelError) as caught: encode('xx', 3)
        self.assertEqual(caught.exception.code, PREFIX + 'input_limit')
        huge = deepcopy(original); huge['context']['instructions'] = 'x' * (8 * 1024 * 1024)
        with mock.patch.object(API, 'read_current_conducted_plan_from_facts', return_value=huge):
            with self.assertRaises(ReadModelError) as caught: self.view()
        self.assertEqual(caught.exception.code, PREFIX + 'input_limit')

    def test_genuine_GET_supplies_native_wrapper_without_artifact_configuration(self):
        before = files(self.root)
        actual = []
        genuine = API.read_current_conducted_plan_from_facts
        def observe(*args, **kwargs):
            value = genuine(*args, **kwargs); actual.append(deepcopy(value)); return value
        server = self.start()
        with mock.patch.object(API, 'read_current_conducted_plan_from_facts', side_effect=observe):
            status, headers, raw = self.read(server)
        self.assertEqual(status, 200)
        value = json.loads(raw)
        self.assertEqual(set(value), set('schema_version kind status current recheck reasons verification'.split()))
        self.assertEqual(value['kind'], 'intake_current_facts_plan_view')
        self.assertEqual(value['status'], 'available')
        self.assertEqual(value['current'], actual[0])
        self.assertEqual(len(actual), 1)
        self.assertEqual(value['verification'], VERIFICATION)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(int(headers['Content-Length']), len(raw))
        self.assertLessEqual(len(raw), 9 * 1024 * 1024)
        self.assertEqual(files(self.root), before)

    def test_HTTP_S0_and_origin_framing_write_guards_do_not_call_current_API(self):
        with mock.patch.object(API, 'read_current_conducted_plan_from_facts',
                               side_effect=AssertionError('guard must precede current read')):
            for selected, code in [(None, 'not_provided'), (selection('I-foreign'), 'other_intake')]:
                server = self.start(selected)
                status, _, raw = self.read(server)
                self.assertEqual(status, 503)
                self.assertEqual(json.loads(raw), {'error': {'code': PREFIX + code}})
            server = self.start()
            for kwargs, expected in [({'headers': {'Origin': 'https://outside.invalid'}}, 403),
                                     ({'headers': {'Sec-Fetch-Site': 'cross-site'}}, 403),
                                     ({'body': b'x'}, 400), ({'suffix': '?x=1'}, 400),
                                     ({'method': 'HEAD'}, 405), ({'method': 'POST'}, 405),
                                     ({'method': 'PUT'}, 405), ({'method': 'PATCH'}, 405),
                                     ({'method': 'DELETE'}, 405), ({'method': 'OPTIONS'}, 405)]:
                with self.subTest(kwargs=kwargs): self.assertEqual(self.read(server, **kwargs)[0], expected)

    def test_actual_uncompleted_and_nonsynthetic_parents_remain_unavailable(self):
        for name, kwargs, code in [
                ('uncompleted', {'completed': False}, 'analysis_unavailable'),
                ('nonsynthetic', {'synthetic': False}, 'synthetic_required')]:
            with self.subTest(parent=name):
                fixture = conducted_context_fixture(self.root / name, **kwargs)
                before = files(self.root)
                server = self.start(selection(fixture['intake_id']), workspace=fixture['store'].root)
                status, _, raw = self.read(server, path='/api/intakes/' + fixture['intake_id'] + '/conducted-current-facts')
                self.assertEqual(status, 503)
                self.assertEqual(json.loads(raw), {'error': {'code': 'intake_conducted_preview_' + code}})
                self.assertEqual(files(self.root), before)

    def test_old_preview_None_exact8_bytes_are_unchanged(self):
        before = _conducted_preview_response(self.model.conducted_plan_preview(self.intake_id, None))
        server = self.start(None)
        status, _, raw = self.read(server, path='/api/intakes/' + self.intake_id + '/conducted-plan-preview')
        self.assertEqual(status, 200)
        self.assertEqual(raw, before)
        self.assertEqual(len(json.loads(raw)), 8)

    def test_HTTP_response_guard_rejects_tamper_and_private_errors_as_fixed_errors(self):
        valid = self.view()
        server = self.start()
        bad = deepcopy(valid); bad['verification']['execution_authority'] = True
        overlimit = deepcopy(valid); overlimit['current']['context']['instructions'] = 'x' * (9 * 1024 * 1024)
        for result in [bad, {**valid, 'extra': 'private-path'}, {**valid, 'schema_version': True}, overlimit]:
            with mock.patch.object(IntakeReadModel, 'conducted_current_facts_view', return_value=result):
                status, _, raw = self.read(server)
            self.assertEqual(status, 503)
            self.assertEqual(json.loads(raw), {'error': {'code': PREFIX + 'invalid_response'}})
            self.assertNotIn(b'private-path', raw)
        for error in [ReadModelError('private-path'), ValueError('private-path')]:
            with mock.patch.object(IntakeReadModel, 'conducted_current_facts_view', side_effect=error):
                status, _, raw = self.read(server)
            self.assertEqual(status, 503)
            self.assertEqual(json.loads(raw), {'error': {'code': PREFIX + 'unavailable'}})
            self.assertNotIn(b'private-path', raw)

    def test_factory_lock_serializes_only_named_current_read_handler_seam(self):
        self.assertTrue(callable(getattr(IntakeReadModel, 'conducted_current_facts_view', None)),
                        'missing assigned current-facts read-model method')
        genuine = IntakeReadModel.conducted_current_facts_view
        entered, release, second_client, overlap = (threading.Event() for unused in range(4))
        active = []; maximum = []; results = []; faults = []
        def held(model, *args):
            active.append(1); maximum.append(len(active))
            if len(active) > 1: overlap.set()
            try:
                if not entered.is_set():
                    entered.set()
                    if not release.wait(3): raise AssertionError('bounded release was not signalled')
                return genuine(model, *args)
            finally: active.pop()
        server = self.start()
        def client(second=False):
            if second: second_client.set()
            try: results.append(self.read(server)[0])
            except BaseException as error: faults.append(error)
        with mock.patch.object(IntakeReadModel, 'conducted_current_facts_view', held):
            one = threading.Thread(target=client); two = threading.Thread(target=client, args=(True,))
            one.start()
            try:
                self.assertTrue(entered.wait(3)); two.start(); self.assertTrue(second_client.wait(3))
                self.assertFalse(overlap.wait(.15), 'current reads overlapped before first was released')
            finally:
                release.set(); one.join(5)
                if two.ident is not None: two.join(5)
            self.assertFalse(one.is_alive()); self.assertFalse(two.is_alive())
        self.assertEqual(faults, []); self.assertEqual(results, [200, 200])
        self.assertEqual(max(maximum), 1)


if __name__ == '__main__':
    unittest.main()
