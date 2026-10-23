"""Synthetic session durability checks; no real equipment is used."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]


def seal(document):
    body = {key: value for key, value in document.items() if key != 'sha256'}
    encoded = json.dumps(body, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    return dict(body, sha256=hashlib.sha256(encoded).hexdigest())


class VirtualSessionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_session'),
                             'virtual session not implemented')
        self.module = importlib.import_module('labflow.virtual_session')
        self.Session = self.module.VirtualSession
        (REPO / '.local').mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='session-test-', dir=REPO / '.local')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def create(self, name='case', **settings):
        session = self.Session.create(name, storage_root=self.root, **settings)
        self.addCleanup(session.close)
        return session

    def reopen(self, session, name='case'):
        session.close()
        session = self.Session.open(name, storage_root=self.root)
        self.addCleanup(session.close)
        return session

    def connected(self, name='case', **settings):
        session = self.create(name, **settings)
        session.execute('configure', 'configure_dut', mode='g', channel=6, power_dbm=10.0)
        session.execute('path', 'set_path', connected=True, loss_db=3.0)
        session.execute('tx', 'start_tx')
        return session

    def read_file(self, name='case'):
        return (self.root / (name + '.session.json')).read_bytes()

    def write_document(self, document):
        (self.root / 'case.session.json').write_text(
            json.dumps(document, ensure_ascii=False, allow_nan=False), encoding='utf-8')

    def process(self, body):
        source = ("import json, os, sys\n"
                  "from labflow.virtual_session import VirtualSession\n"
                  "root = sys.argv[1]\n" + body)
        result = subprocess.run([sys.executable, '-B', '-c', source, str(self.root)],
                                cwd=REPO, capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_pending_measurement_resumes_in_new_process_with_same_noise_and_ids(self):
        from labflow.virtual_lab import VirtualLab
        reference = VirtualLab(seed=41, measurement_ticks=3, noise_db=0.2)
        reference.configure_dut('g', 6, 10.0)
        reference.set_path(True, 3.0)
        reference.start_tx()
        expected = []
        for _ in range(2):
            reference.meter('INIT')
            reference.advance(3)
            expected.append(reference.meter('FETC?'))
        session = self.connected(seed=41, measurement_ticks=3, noise_db=0.2)
        session.execute('init', 'meter', command='INIT')
        session.execute('tick-one', 'advance', ticks=1)
        session.close()
        output = json.loads(self.process(
            "with VirtualSession.open('case', storage_root=root) as session:\n"
            "    pending = session.execute('pending', 'meter', command='FETC?')\n"
            "    session.execute('finish', 'advance', ticks=2)\n"
            "    first = session.execute('fetch', 'meter', command='FETC?')\n"
            "    session.execute('init-next', 'meter', command='INIT')\n"
            "    session.execute('finish-next', 'advance', ticks=3)\n"
            "    second = session.execute('fetch-next', 'meter', command='FETC?')\n"
            "    print(json.dumps([pending, first, second]))\n"))
        self.assertEqual(output[0]['status'], 'pending')
        self.assertEqual(output[1:], expected)

    def test_completed_fetch_and_duplicate_mutation_do_not_repeat(self):
        session = self.connected(seed=17, noise_db=0.2)
        session.execute('init', 'meter', command='INIT')
        tick = session.execute('advance', 'advance', ticks=2)
        first = session.execute('fetch', 'meter', command='FETC?')
        session = self.reopen(session)
        before = self.read_file()
        self.assertEqual(session.execute('fetch', 'meter', command='FETC?'), first)
        self.assertEqual(session.execute('advance', 'advance', ticks=2), tick)
        self.assertEqual(self.read_file(), before)
        self.assertEqual(session.execute('again', 'meter', command='FETC?'), first)
        session.execute('later', 'advance', ticks=30)
        self.assertEqual(session.execute('fetch', 'meter', command='FETC?'), first)
        self.assertEqual(session.execute('now', 'meter', command='FETC?')['measurement'],
                         first['measurement'])

    def test_conflict_is_rejected_without_overwrite_or_motion(self):
        session = self.create()
        session.execute('same', 'advance', ticks=3)
        before = self.read_file()
        for action, arguments in [('advance', {'ticks': 4}), ('stop_tx', {})]:
            with self.assertRaises(self.module.RequestConflictError):
                session.execute('same', action, **arguments)
            self.assertEqual(self.read_file(), before)
        self.assertEqual(session.execute('clock', 'advance', ticks=0)['tick'], 3)

    def test_observation_and_result_are_detached_copies(self):
        session = self.create()
        result = session.execute('id', 'meter', command='*IDN?')
        result['synthetic'] = False
        export = session.observations()
        export['events'][0]['arguments']['command'] = 'INIT'
        export['events'][0]['observation']['synthetic'] = False
        self.assertTrue(session.execute('id', 'meter', command='*IDN?')['synthetic'])
        self.assertEqual(session.observations()['events'][0]['arguments']['command'], '*IDN?')

    def test_invalid_actions_and_arguments_leave_no_accepted_event(self):
        session = self.create()
        before = self.read_file()
        invalid = [
            ('', 'advance', {'ticks': 1}), ('id', '__dict__', {}),
            ('id', 'inject_fault', {'name': 'tx_ignored', 'value': True}),
            ('id', 'advance', {'ticks': True}), ('id', 'advance', {'ticks': float('nan')}),
            ('id', 'advance', {'ticks': 10**400}),
            ('id', 'advance', {'ticks': 1, 'extra': 1}),
            ('id', 'configure_dut', {'mode': 'bad', 'channel': 6, 'power_dbm': 10}),
            ('id', 'set_path', {'connected': 1, 'loss_db': 3}),
            ('id', 'start_tx', {}),
        ]
        for request_id, action, arguments in invalid:
            with self.subTest(action=action, arguments=str(arguments)[:80]):
                with self.assertRaises(ValueError):
                    session.execute(request_id, action, **arguments)
                self.assertEqual(self.read_file(), before)
        self.assertEqual(session.execute('id', 'advance', ticks=1)['tick'], 1)

    def test_changed_setup_and_abort_do_not_restore_stale_data(self):
        session = self.connected()
        session.execute('init', 'meter', command='INIT')
        session.execute('move', 'set_path', connected=True, loss_db=5.0)
        session = self.reopen(session)
        session.execute('done', 'advance', ticks=2)
        self.assertEqual(session.execute('fetch', 'meter', command='FETC?')['status'], 'invalid')
        session.execute('again', 'meter', command='INIT')
        session.execute('abort', 'meter', command='ABOR')
        session = self.reopen(session)
        session.execute('wait', 'advance', ticks=10)
        self.assertEqual(session.execute('empty', 'meter', command='FETC?')['status'], 'no_data')

    def test_bus_trigger_and_error_queue_survive_and_are_not_consumed_twice(self):
        session = self.connected()
        session.execute('trigger', 'meter', command='*TRG')
        session.execute('bus', 'meter', command='TRIG:SOUR BUS')
        session.execute('init', 'meter', command='INIT')
        session.execute('duplicate-init', 'meter', command='INIT')
        first = session.execute('first-error', 'meter', command='SYST:ERR?')
        self.assertEqual(first['error_number'], -211)
        session = self.reopen(session)
        self.assertEqual(session.execute('first-error', 'meter', command='SYST:ERR?'), first)
        self.assertEqual(session.execute('second-error', 'meter', command='SYST:ERR?')
                         ['error_number'], -213)
        session.execute('go', 'meter', command='*TRG')
        session.execute('ticks', 'advance', ticks=2)
        self.assertEqual(session.execute('fetch', 'meter', command='FETC?')
                         ['measurement']['value'], 7.0)

    def test_six_scenarios_hide_controls_and_recover_after_reopen(self):
        for name, fault, value, expected in [
            ('normal', None, None, 7.0), ('silent', 'tx_ignored', True, -100.0),
            ('open', 'set_path', False, -100.0), ('thermal', 'thermal_drop_db', 6.0, 1.0),
            ('stuck', 'measurement_stuck', True, 'pending'),
            ('lost', 'meter_disconnected', True, 'disconnected'),
        ]:
            with self.subTest(name=name):
                session = self.connected(name)
                if fault == 'set_path':
                    session.scenario_control('secret-control', 'set_path',
                                             connected=False, loss_db=3.0)
                elif fault:
                    self.assertIsNone(session.scenario_control(
                        'secret-control', 'inject_fault', name=fault, value=value))
                session.execute('init', 'meter', command='INIT')
                session.execute('wait', 'advance', ticks=2)
                session = self.reopen(session, name)
                observed = session.execute('fetch', 'meter', command='FETC?')
                if isinstance(expected, str):
                    self.assertEqual(observed['status'], expected)
                else:
                    self.assertEqual(observed['measurement']['value'], expected)
                if name in ('stuck', 'lost'):
                    session.scenario_control('secret-clear', 'inject_fault',
                                             name=fault, value=False)
                    session.execute('abort', 'meter', command='ABOR')
                    session.execute('init-again', 'meter', command='INIT')
                    session.execute('wait-again', 'advance', ticks=2)
                    self.assertEqual(session.execute('fetch-again', 'meter', command='FETC?')
                                     ['measurement']['value'], 7.0)
                text = json.dumps(session.observations())
                for hidden in ['secret-control', 'secret-clear', 'inject_fault', 'expected',
                               'thermal_drop_db', 'tx_ignored', 'measurement_stuck',
                               'meter_disconnected', '"seed"', '"config"', '"controls"']:
                    self.assertNotIn(hidden, text)
                self.assertTrue(session.observations()['synthetic'])
                self.assertFalse(session.observations()['hardware_verified'])

    def test_hidden_request_id_cannot_return_through_operator_api(self):
        session = self.create()
        session.scenario_control('private', 'inject_fault', name='tx_ignored', value=True)
        with self.assertRaises(self.module.RequestConflictError):
            session.execute('private', 'advance', ticks=0)
        with self.assertRaises(ValueError):
            session.scenario_control('bad', '__dict__')
        self.assertEqual(session.observations()['events'], [])

    def test_same_process_second_writer_is_rejected_and_close_releases_lock(self):
        session = self.create()
        before = self.read_file()
        with self.assertRaises(self.module.SessionLockedError):
            self.Session.open('case', storage_root=self.root)
        self.assertEqual(self.read_file(), before)
        session = self.reopen(session)
        self.assertEqual(session.execute('id', 'meter', command='*IDN?')['status'], 'ok')

    def test_other_process_cannot_write_while_owner_holds_lock(self):
        session = self.create()
        before = self.read_file()
        self.assertEqual(self.process(
            "from labflow.virtual_session import SessionLockedError\n"
            "try:\n"
            "    VirtualSession.open('case', storage_root=root)\n"
            "except SessionLockedError:\n"
            "    print('locked')\n"), 'locked')
        self.assertEqual(self.read_file(), before)
        session.close()
        self.assertEqual(self.process(
            "with VirtualSession.open('case', storage_root=root) as session:\n"
            "    print(session.execute('id', 'meter', command='*IDN?')['status'])\n"), 'ok')

    def test_process_crash_releases_lock_and_retains_pending_measurement(self):
        self.process(
            "session = VirtualSession.create('case', storage_root=root)\n"
            "session.execute('configure', 'configure_dut', mode='g', channel=6, power_dbm=10)\n"
            "session.execute('path', 'set_path', connected=True, loss_db=3)\n"
            "session.execute('tx', 'start_tx')\n"
            "session.execute('init', 'meter', command='INIT')\n"
            "session.execute('one', 'advance', ticks=1)\n"
            "os._exit(0)\n")
        session = self.Session.open('case', storage_root=self.root)
        self.addCleanup(session.close)
        self.assertEqual(session.execute('pending', 'meter', command='FETC?')['status'], 'pending')
        session.execute('finish', 'advance', ticks=1)
        result = session.execute('fetch', 'meter', command='FETC?')
        self.assertEqual(result['tick'], 2)
        self.assertEqual(result['measurement']['measurement_id'], 1)

    def test_threads_using_one_owner_are_serialized(self):
        session = self.create()
        with ThreadPoolExecutor(max_workers=6) as workers:
            results = list(workers.map(
                lambda number: session.execute('tick-' + str(number), 'advance', ticks=1),
                range(24)))
        self.assertEqual(sorted(item['tick'] for item in results), list(range(1, 25)))
        session = self.reopen(session)
        self.assertEqual(session.execute('clock', 'advance', ticks=0)['tick'], 24)

    def test_truncation_invalid_utf8_and_duplicate_json_keys_preserve_file(self):
        session = self.create()
        original = self.read_file()
        session.close()
        for damaged in [original[:len(original)//2], b'\xff', b'', b'[]',
                        b'{"schema_version":1,"schema_version":2}', b'{"value":NaN}']:
            with self.subTest(damaged=damaged[:20]):
                (self.root / 'case.session.json').write_bytes(damaged)
                with self.assertRaises(self.module.SessionCorruptError):
                    self.Session.open('case', storage_root=self.root)
                self.assertEqual(self.read_file(), damaged)

    def test_tampered_config_fails_checksum_and_preserves_source(self):
        session = self.create(seed=123)
        document = json.loads(self.read_file())
        session.close()
        document['config']['seed'] = 124
        self.write_document(document)
        before = self.read_file()
        with self.assertRaises(self.module.SessionCorruptError):
            self.Session.open('case', storage_root=self.root)
        self.assertEqual(self.read_file(), before)

    def test_resealed_invented_result_fails_replay(self):
        session = self.create()
        session.execute('tick', 'advance', ticks=2)
        document = json.loads(self.read_file())
        session.close()
        document['events'][0]['result']['tick'] = 3
        self.write_document(seal(document))
        before = self.read_file()
        with self.assertRaises(self.module.SessionCorruptError):
            self.Session.open('case', storage_root=self.root)
        self.assertEqual(self.read_file(), before)

    def test_unknown_format_and_engine_versions_preserve_source(self):
        session = self.create()
        original = json.loads(self.read_file())
        session.close()
        for field in ['schema', 'engine']:
            document = json.loads(json.dumps(original))
            if field == 'schema':
                document['schema_version'] = 999
            else:
                document['engine']['source_sha256'] = '0' * 64
            self.write_document(seal(document))
            before = self.read_file()
            with self.assertRaises(self.module.SessionVersionError):
                self.Session.open('case', storage_root=self.root)
            self.assertEqual(self.read_file(), before)

    def test_resealed_bad_sequence_duplicate_id_and_actions_fail_validation(self):
        session = self.create()
        session.execute('one', 'advance', ticks=1)
        original = json.loads(self.read_file())
        session.close()
        for mutation in ['sequence', 'duplicate', 'action', 'kind', 'session', 'extra']:
            document = json.loads(json.dumps(original))
            if mutation == 'sequence':
                document['events'][0]['sequence'] = 2
            elif mutation == 'duplicate':
                document['events'].append(dict(document['events'][0], sequence=2))
            elif mutation in ('action', 'kind'):
                document['events'][0][mutation] = '__dict__'
            elif mutation == 'session':
                document['session_id'] = 'different'
            else:
                document['expected'] = 7
            with self.subTest(mutation=mutation):
                self.write_document(seal(document))
                before = self.read_file()
                with self.assertRaises(self.module.SessionCorruptError):
                    self.Session.open('case', storage_root=self.root)
                self.assertEqual(self.read_file(), before)

    def test_existing_checkpoint_is_not_replaced_and_missing_is_not_created(self):
        session = self.create()
        before = self.read_file()
        session.close()
        with self.assertRaises(FileExistsError):
            self.Session.create('case', storage_root=self.root, seed=2)
        self.assertEqual(self.read_file(), before)
        with self.assertRaises(self.module.SessionStorageError):
            self.Session.open('missing', storage_root=self.root)
        self.assertFalse((self.root / 'missing.session.json').exists())

    def test_outside_private_root_and_unsafe_session_ids_are_rejected(self):
        for root in [REPO, REPO / '.local' / '..' / 'exports', REPO.parent / 'outside-session']:
            with self.subTest(root=root), self.assertRaises(ValueError):
                self.Session.create('unsafe', storage_root=root)
            self.assertFalse((root / 'unsafe.session.json').exists())
        for value in ['', '..', '../outside', 'a/b', 'a\\b', 'CON', 'aux', 'NUL',
                      'COM1', 'LPT9', 'a.', 'a ', 'x' * 65, 123]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.Session.create(value, storage_root=self.root)

    def test_external_file_change_is_not_overwritten(self):
        session = self.create()
        damaged = self.read_file() + b'\n '
        (self.root / 'case.session.json').write_bytes(damaged)
        with self.assertRaises(self.module.SessionCorruptError):
            session.execute('id', 'advance', ticks=1)
        self.assertEqual(self.read_file(), damaged)

    def test_replace_failure_preserves_checkpoint_and_failed_candidate(self):
        session = self.create()
        before = self.read_file()
        with patch.object(self.module.os, 'replace', side_effect=OSError('write failed')):
            with self.assertRaises(self.module.SessionStorageError):
                session.execute('advance', 'advance', ticks=2)
        self.assertEqual(self.read_file(), before)
        self.assertTrue(list(self.root.glob('*.tmp')))
        with self.assertRaises(self.module.SessionError):
            session.execute('other', 'advance', ticks=1)
        session = self.reopen(session)
        self.assertEqual(session.execute('advance', 'advance', ticks=2)['tick'], 2)

    def test_failure_after_replace_reopens_committed_id_without_double_execution(self):
        session = self.create()
        replace = os.replace

        def replace_then_fail(source, target):
            replace(source, target)
            raise OSError('reply lost after replace')

        with patch.object(self.module.os, 'replace', side_effect=replace_then_fail):
            with self.assertRaises(self.module.SessionStorageError):
                session.execute('advance', 'advance', ticks=2)
        session = self.reopen(session)
        before = self.read_file()
        self.assertEqual(session.execute('advance', 'advance', ticks=2)['tick'], 2)
        self.assertEqual(self.read_file(), before)

    def test_fsync_failure_keeps_checkpoint_and_candidate(self):
        session = self.create()
        before = self.read_file()
        with patch.object(self.module.os, 'fsync', side_effect=OSError('disk full')):
            with self.assertRaises(self.module.SessionStorageError):
                session.execute('advance', 'advance', ticks=1)
        self.assertEqual(self.read_file(), before)
        self.assertTrue(list(self.root.glob('*.tmp')))
        session = self.reopen(session)
        self.assertEqual(session.execute('advance', 'advance', ticks=1)['tick'], 1)

    def test_limits_and_closed_owner_reject_without_mutating(self):
        session = self.create()
        with patch.object(self.module, 'MAX_EVENTS', 1):
            session.execute('first', 'advance', ticks=1)
            before = self.read_file()
            with self.assertRaises(self.module.SessionError):
                session.execute('second', 'advance', ticks=1)
            self.assertEqual(self.read_file(), before)
        session.close()
        with patch.object(self.module, 'MAX_FILE_BYTES', len(before) - 1):
            with self.assertRaises(self.module.SessionCorruptError):
                self.Session.open('case', storage_root=self.root)
        self.assertEqual(self.read_file(), before)
        session.close()
        with self.assertRaises(self.module.SessionError):
            session.execute('id', 'advance', ticks=0)
        with self.assertRaises(self.module.SessionError):
            session.observations()

    def test_offline_synthetic_provenance(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            with self.Session.create('offline', storage_root=self.root) as session:
                result = session.execute('id', 'meter', command='*IDN?')
                self.assertTrue(result['synthetic'])
                self.assertFalse(result['hardware_verified'])
                self.assertIn('SIM', result['response'])


if __name__ == '__main__':
    unittest.main()
