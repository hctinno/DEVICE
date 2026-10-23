"""D4 read contract. Queue SQL/readiness are doubles until lead integration."""
import http.client
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

from test_ui_read_model import IntakeFixture
from test_virtual_fleet_harness_report_ui import public_result
from labflow.ui_read_model import IntakeReadModel, ReadModelError
from labflow.ui_server import create_server


def install_queue_double(store):
    # Only test storage, never a production migration or queue implementation.
    with store.connection() as con:
        con.execute('DROP TABLE IF EXISTS intake_fixture_jobs')
        con.execute('''CREATE TABLE intake_fixture_jobs(
            request_id TEXT PRIMARY KEY,intake_id TEXT,revision INTEGER,
            request_fingerprint TEXT,readiness_fingerprint TEXT,revision_fingerprint TEXT,
            delegation_event_id TEXT,recipe_id TEXT,settings_json TEXT,model TEXT,
            source_synthetic INTEGER,state TEXT,worker_id TEXT,token TEXT,lease_until REAL,
            run_id TEXT,runtime_instance_id TEXT,result_json TEXT,error_code TEXT,
            created_at REAL,updated_at REAL)''')


def add_record(store, intake_id, request_id='REQ-UI-1', **changes):
    with store.connection() as con:
        revision = con.execute('SELECT * FROM intake_revisions WHERE intake_id=? ORDER BY revision DESC', (intake_id,)).fetchone()
        report = public_result()
        data = dict(request_id=request_id, intake_id=intake_id, revision=revision['revision'],
                    request_fingerprint='b'*64, readiness_fingerprint='c'*64,
                    revision_fingerprint=revision['fingerprint'], delegation_event_id='PROCEED-UI',
                    recipe_id='conducted_sensor_fixture_v1', settings_json='{"power_dbm":10}',
                    model='SM-A176U', source_synthetic=1, state='completed', worker_id='host-only',
                    token='private-token-canary', lease_until=300, run_id=report['run_id'],
                    runtime_instance_id=report['runtime_instance_id'], error_code=None,
                    result_json=json.dumps({'report': report, 'artifacts': [
                        {'kind': kind, 'artifact_id': 'blob:'+'a'*64, 'sha256': 'a'*64, 'bytes': 10}
                        for kind in ['result', 'operator_journal']]}), created_at=200, updated_at=201)
        data.update(changes)
        columns = ','.join(data)
        con.execute(f'INSERT INTO intake_fixture_jobs({columns}) VALUES({",".join("?" for _ in data)})', tuple(data.values()))
    return data


class FixtureReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixture = IntakeFixture(self.tmp.name)
        self.intake_id = self.fixture.accept()
        self.model = IntakeReadModel(self.fixture.store.root)
        with self.fixture.store.connection() as con:
            con.execute('DROP TABLE IF EXISTS intake_fixture_jobs')

    def readiness(self, store, intake_id):
        # The same query-only transaction is passed, with no Store features.
        self.assertFalse(hasattr(store, 'import_artifact'))
        with store.connection() as con:
            row = con.execute('SELECT revision FROM intakes WHERE intake_id=?', (intake_id,)).fetchone()
            self.assertEqual(con.execute('PRAGMA query_only').fetchone()[0], 1)
        return {'intake_id': intake_id, 'revision': row['revision'], 'readiness_fingerprint': 'c'*64}

    def read(self):
        with patch('labflow.ui_read_model.fixture_readiness', self.readiness, create=True):
            return self.model.fixture_runs(self.intake_id)

    def test_legacy_table_or_helper_absent_is_explicit_and_never_migrates(self):
        before = self.fixture.store.db.read_bytes()
        self.assertEqual(self.read(), dict(schema_version=1, intake_id=self.intake_id,
            current_revision=1, storage_available=False, records=[], more_available=False))
        self.assertEqual(self.fixture.store.db.read_bytes(), before)
        install_queue_double(self.fixture.store)
        with patch('labflow.ui_read_model.fixture_readiness', None, create=True):
            self.assertFalse(self.model.fixture_runs(self.intake_id)['storage_available'])

    def test_missing_store_and_unknown_intake_do_not_become_empty_success(self):
        for model, intake_id, code in [(IntakeReadModel(self.fixture.root / 'absent'), 'I-x', 'store_missing'),
                                      (self.model, 'I-absent', 'intake_not_found')]:
            with self.subTest(code=code), self.assertRaises(ReadModelError) as error:
                model.fixture_runs(intake_id)
            self.assertEqual(error.exception.code, code)
        self.assertFalse((self.fixture.root / 'absent').exists())

    def test_exact_public_projection_and_reading_has_no_writes_or_execution(self):
        install_queue_double(self.fixture.store)
        add_record(self.fixture.store, self.intake_id)
        before = self.fixture.store.db.read_bytes()
        with patch('labflow.store.Store.__init__', side_effect=AssertionError('no Store init')), \
             patch('labflow.workflow.evaluate', side_effect=AssertionError('no evaluator')), \
             patch('labflow.workflow.case_status', side_effect=AssertionError('no case status')):
            payload = self.read()
        self.assertEqual(self.fixture.store.db.read_bytes(), before)
        record = payload['records'][0]
        self.assertEqual(set(record), set('request_id intake_id revision readiness_fingerprint recipe_id run_id runtime_instance_id state source_current source_synthetic synthetic hardware_verified ai_model_called resumable case_id plan_id error_code report'.split()))
        self.assertTrue(record['source_current'])
        self.assertIsNone(record['case_id'])
        self.assertIsNone(record['plan_id'])
        self.assertFalse(record['resumable'])
        self.assertEqual(record['report'], public_result())
        self.assertNotIn('private-token-canary', json.dumps(payload))
        self.assertNotIn('settings_json', json.dumps(payload))

    def test_latest_twenty_and_other_intakes_are_excluded(self):
        install_queue_double(self.fixture.store)
        other = self.fixture.accept('other')
        for index in range(23):
            add_record(self.fixture.store, self.intake_id, f'Q-{index:02}', created_at=index)
        add_record(self.fixture.store, other, 'Q-other', created_at=1000)
        payload = self.read()
        self.assertEqual([r['request_id'] for r in payload['records']], [f'Q-{i:02}' for i in range(22, 2, -1)])
        self.assertTrue(payload['more_available'])
        with self.fixture.store.connection() as con:
            con.execute('DELETE FROM intake_fixture_jobs WHERE request_id IN (?,?,?)', ('Q-00', 'Q-01', 'Q-02'))
        self.assertFalse(self.read()['more_available'])

    def test_past_revision_and_same_revision_changed_readiness_remain_historical(self):
        install_queue_double(self.fixture.store)
        old = add_record(self.fixture.store, self.intake_id)
        with self.fixture.store.connection() as con:
            con.execute('UPDATE intake_fixture_jobs SET readiness_fingerprint=?', ('d'*64,))
        self.assertFalse(self.read()['records'][0]['source_current'])
        (self.fixture.inbox / 'order' / 'supplement.txt').write_text('Synthetic revision', encoding='utf-8')
        from labflow.active_intake import scan_source
        scan_source(self.fixture.store, 'UI', now=220)
        scan_source(self.fixture.store, 'UI', now=221)
        payload = self.read()
        self.assertEqual(payload['current_revision'], 2)
        self.assertEqual(payload['records'][0]['revision'], 1)
        self.assertEqual(payload['records'][0]['report']['run_id'], old['run_id'])
        self.assertFalse(payload['records'][0]['source_current'])

    def test_queued_failed_uncertain_and_superseded_do_not_invent_a_report(self):
        install_queue_double(self.fixture.store)
        for index, state in enumerate(['queued', 'running', 'failed', 'uncertain', 'superseded']):
            add_record(self.fixture.store, self.intake_id, state, state=state, result_json=None,
                       created_at=index, error_code='lease_lost' if state == 'uncertain' else None)
        self.assertTrue(all(record['report'] is None for record in self.read()['records']))

    def test_wrong_bindings_provenance_and_corrupt_public_json_are_rejected(self):
        install_queue_double(self.fixture.store)
        original = add_record(self.fixture.store, self.intake_id)
        invalid = [dict(revision=99), dict(revision_fingerprint='e'*64), dict(source_synthetic=0),
                   dict(readiness_fingerprint='not-a-hash'), dict(state='success'), dict(result_json=None),
                   dict(result_json='{"report":null,"artifacts":[]}'), dict(run_id='other-run'),
                   dict(result_json=original['result_json'].replace('"synthetic": true', '"synthetic": false')),
                   dict(result_json=original['result_json'].replace('"policy": {', '"policy": {"seed":1,')),
                   dict(result_json=original['result_json'].replace('"artifact_id": "blob:', '"artifact_id": "file:')),
                   dict(error_code='C:\\private\\secret.txt'), dict(result_json='{"report":{},"report":null,"artifacts":[]}')]
        for changes in invalid:
            with self.subTest(changes=list(changes)):
                with self.fixture.store.connection() as con:
                    con.execute('DELETE FROM intake_fixture_jobs')
                add_record(self.fixture.store, self.intake_id, **changes)
                with self.assertRaises(ReadModelError) as error:
                    self.read()
                self.assertEqual(error.exception.code, 'state_invalid')

    def test_request_id_keeps_the_queue_identifier_boundary(self):
        install_queue_double(self.fixture.store)
        add_record(self.fixture.store, self.intake_id, request_id='Q'*150)
        self.assertEqual(len(self.read()['records'][0]['request_id']),150)

    def test_oversized_report_and_private_result_fields_are_not_silently_filtered(self):
        install_queue_double(self.fixture.store)
        for mutate in [lambda v: v.update(private={'path':'C:/secret'}),
                       lambda v: v['report']['evidence'].update(measurement_refs=['event:'+'a'*1000]*300),
                       lambda v: v['artifacts'][0].update(path='private/author.json')]:
            with self.fixture.store.connection() as con:
                con.execute('DELETE FROM intake_fixture_jobs')
            data = add_record(self.fixture.store, self.intake_id)
            value = json.loads(data['result_json'])
            mutate(value)
            with self.fixture.store.connection() as con:
                con.execute('UPDATE intake_fixture_jobs SET result_json=?', (json.dumps(value),))
            with self.assertRaises(ReadModelError):
                self.read()

    def test_accidental_readiness_write_fails_closed(self):
        install_queue_double(self.fixture.store)
        before = self.fixture.store.db.read_bytes()
        def bad_helper(store, intake_id):
            with store.connection() as con:
                con.execute('UPDATE intakes SET delegated=1')
        with patch('labflow.ui_read_model.fixture_readiness', bad_helper, create=True):
            with self.assertRaises(ReadModelError) as error:
                self.model.fixture_runs(self.intake_id)
        self.assertEqual(error.exception.code, 'store_unavailable')
        self.assertEqual(self.fixture.store.db.read_bytes(), before)


class FixtureReadHTTPTests(unittest.TestCase):
    def test_same_origin_get_head_and_no_new_mutation_or_path_resolver(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = IntakeFixture(folder)
            intake_id = fixture.accept()
            with fixture.store.connection() as con:
                con.execute('DROP TABLE IF EXISTS intake_fixture_jobs')
            with create_server(fixture.store.root, port=0) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                def request(path, method='GET', headers=None):
                    con = http.client.HTTPConnection(*server.server_address, timeout=3)
                    try:
                        con.request(method, path, headers=headers or {})
                        response = con.getresponse()
                        return response.status, dict(response.getheaders()), response.read()
                    finally:
                        con.close()
                try:
                    route = f'/api/intakes/{intake_id}/fixture-runs'
                    status, headers, body = request(route)
                    self.assertEqual(status, 200)
                    self.assertFalse(json.loads(body)['storage_available'])
                    self.assertEqual(headers['Cache-Control'], 'no-store')
                    self.assertNotIn('Access-Control-Allow-Origin', headers)
                    self.assertEqual(request(route, 'HEAD')[2], b'')
                    self.assertEqual(request(route, headers={'Origin':'https://outside.invalid'})[0], 403)
                    self.assertEqual(request(route, 'POST')[0], 405)
                    for suffix in ['?path=private', '/raw', '/start', '/resume']:
                        self.assertEqual(request(route+suffix)[0], 404)
                    self.assertEqual(request('/api/intakes/absent/fixture-runs')[0], 404)
                    for asset in ['/intake_flow_model.mjs', '/virtual_fleet/harness_model.mjs']:
                        self.assertEqual(request(asset)[0], 200)
                finally:
                    server.shutdown()
                    thread.join(timeout=3)


class ActualQueueReadTests(unittest.TestCase):
    def test_actual_queue_publication_and_readiness_changes_are_purely_readable(self):
        import test_intake_fixture_jobs as queue_tests
        from labflow.intake_fixture_jobs import claim_fixture_job, complete_fixture_job
        from labflow.intake_jobs import respond
        from labflow.active_intake import scan_source

        fixture = queue_tests.FixtureQueueTests(methodName='runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.request()
        model = IntakeReadModel(fixture.store.root)
        self.assertEqual(model.fixture_runs(fixture.intake_id)['records'][0]['state'],'queued')
        claim = claim_fixture_job(fixture.store,'read-ui-worker',now=200)
        self.assertEqual(model.fixture_runs(fixture.intake_id)['records'][0]['state'],'running')
        report,artifacts = fixture.evidence(claim)
        complete_fixture_job(fixture.store,'REQ-1',claim['token'],report,artifacts,now=201)
        before = fixture.store.db.read_bytes()
        with patch('labflow.store.Store.__init__',side_effect=AssertionError('GET Store init')), \
             patch('labflow.workflow.evaluate',side_effect=AssertionError('GET evaluate')), \
             patch('labflow.workflow.case_status',side_effect=AssertionError('GET case_status')):
            record = model.fixture_runs(fixture.intake_id)['records'][0]
        self.assertEqual(fixture.store.db.read_bytes(),before)
        self.assertEqual(record['report'],report)
        self.assertTrue(record['source_current'])
        respond(fixture.store,'read-ui-defer','defer',intake_id=fixture.intake_id)
        self.assertFalse(model.fixture_runs(fixture.intake_id)['records'][0]['source_current'])
        folder=fixture.inbox/'source-request'/'request'
        (folder/'revision.txt').write_text('Synthetic read-model revision',encoding='utf-8')
        scan_source(fixture.store,'source-request',now=300)
        scan_source(fixture.store,'source-request',now=301)
        payload=model.fixture_runs(fixture.intake_id)
        self.assertEqual(payload['current_revision'],2)
        self.assertEqual(payload['records'][0]['revision'],1)
        self.assertEqual(payload['records'][0]['report'],report)
        self.assertFalse(payload['records'][0]['source_current'])


if __name__ == '__main__':
    unittest.main()
