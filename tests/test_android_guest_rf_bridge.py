"""Fixture-only guest controller and existing Fleet bridge; no SDK or OS run."""
import base64
import hashlib
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

from labflow import android_emulator_check as check
from labflow import android_guest_rf_bridge as bridge


SCRIPT = '/data/local/tmp/dgm-rf-v1.sh'


def receipt(nonce, seq, state, revision, source_hash):
    prefix = f'DGM1|{nonce}|{seq}|{state}|{revision}|{source_hash}'
    return prefix + '|' + hashlib.sha256((prefix + '\n').encode('ascii')).hexdigest()


class FakeGuest:
    """A separate stateful AOSP shell fixture, not a production transport hook."""

    def __init__(self, *, bad_status=False, fail_start=False, fail_cleanup=False,
                 tamper=None):
        self.calls = []
        self.bad_status = bad_status
        self.fail_start = fail_start
        self.fail_cleanup = fail_cleanup
        self.tamper = tamper
        self.script_hash = None
        self.state = None
        self.revision = 0
        self.source_hash = None
        self.sequence = 0

    def __call__(self, endpoint, server, service, deadline):
        self.calls.append(service)
        if not service.startswith('shell:') or endpoint.serial != 'emulator-5680':
            raise AssertionError('unowned guest service')
        if service.startswith('shell:test ! -e '):
            encoded = service.split('printf %s ', 1)[1].split(' | base64 -d', 1)[0]
            script = base64.b64decode(encoded, validate=True)
            self.script_hash = hashlib.sha256(script).hexdigest()
            return self.script_hash + '  ' + SCRIPT
        if service.startswith('shell:rm -f '):
            if self.fail_cleanup:
                raise check.BoundaryError('adb_timeout')
            return 'DGM-CLEAN-OK'
        args = service.removeprefix('shell:sh ').split(' ')
        if args[0] != SCRIPT:
            raise AssertionError('arbitrary script')
        operation, nonce, seq_text = args[1:4]
        seq = int(seq_text)
        if operation == 'HELLO':
            self.sequence = seq
            return receipt(nonce, seq, 'HELLO', 0, self.script_hash)
        if seq != self.sequence + 1:
            raise AssertionError('sequence gap')
        self.sequence = seq
        if operation == 'CONFIG':
            source = args[4:10]
            calculated = hashlib.sha256(('|'.join(source) + '\n').encode('ascii')).hexdigest()
            if calculated != args[10]:
                raise AssertionError('source hash disagreement')
            self.source_hash = calculated
            self.state, self.revision = 'CONFIGURED', 1
        elif operation == 'START':
            if self.fail_start:
                raise check.BoundaryError('adb_timeout')
            self.state, self.revision = 'STARTED', 2
        elif operation == 'STOP':
            self.state, self.revision = 'STOPPED', 3
        elif operation != 'STATUS':
            raise AssertionError('unexpected operation')
        state = 'STARTED' if self.bad_status and operation == 'STATUS' and self.state == 'STOPPED' else self.state
        raw = receipt(nonce, seq, state, self.revision, self.source_hash)
        if self.tamper and operation == 'STATUS':
            parts = raw.split('|')
            index = {'nonce': 1, 'sequence': 2, 'revision': 4,
                     'source_hash': 5, 'receipt': 6}[self.tamper]
            parts[index] = ('0' * 32 if index == 1 else '99' if index in (2, 4)
                            else '0' * 64)
            raw = '|'.join(parts)
        return raw


class GuestBridgeFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = check.Report(Path(self.tmp.name) / 'proof')
        self.endpoint = check.Endpoint()
        self.report.data.update(android_os='booted', adb_verified=True,
                                identity={'serial': self.endpoint.serial, 'state': 'device',
                                          'properties': {'ro.kernel.qemu': '1', 'ro.hardware': 'ranchu',
                                                         'ro.product.model': 'AOSP fixture',
                                                         'sys.boot_completed': '1'}})
        self.server = mock.Mock()
        self.server.process.poll.return_value = None
        self.emulator = mock.Mock()
        self.emulator.process.poll.return_value = None
        resources = mock.patch.object(check, 'resources', return_value={'available_mib': 8192})
        resources.start()
        self.addCleanup(resources.stop)

    def run_bridge(self, guest):
        with mock.patch.object(bridge, '_exchange', side_effect=guest):
            return bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                                             deadline=bridge.time.monotonic() + 30,
                                             emulator_process=self.emulator)

    def test_real_guest_state_receipts_and_fresh_fleet_sensor_are_distinct(self):
        guest = FakeGuest()
        result = self.run_bridge(guest)
        self.assertTrue(result['valid'])
        self.assertEqual(result['guest_controller']['states'],
                         ['CONFIGURED', 'CONFIGURED', 'STARTED', 'STARTED', 'STOPPED', 'STOPPED'])
        self.assertEqual(result['guest_controller']['cleanup'], 'confirmed')
        host = result['host_rf_model']
        self.assertTrue(host['synthetic'])
        self.assertFalse(host['physical_verified'])
        self.assertEqual(host['source_settings'], bridge.SOURCE_SETTINGS)
        self.assertEqual(host['source_sha256'], guest.source_hash)
        self.assertEqual(host['sensor_on_average']['unit'], 'dBm')
        self.assertEqual(host['sensor_on_average']['source_id'], 'sensor')
        self.assertEqual(host['meter_time_average']['quantity'], 'time_average')
        self.assertEqual(host['analyzer_on_average']['quantity'], 'on_average')
        self.assertLess(host['meter_time_average']['value'], host['sensor_on_average']['value'])
        self.assertNotEqual(host['after_stop_sensor_status'], 'ok')
        self.assertNotEqual(host['after_stop_analyzer_status'], 'ok')
        self.assertEqual(self.report.data['rf_bridge'], result)
        self.assertEqual(self.report.data['rf_model'], 'synthetic_guest_bridge_verified')
        self.assertTrue(self.server.sample.called)
        self.assertTrue(self.emulator.sample.called)
        self.assertTrue(any(call.startswith('shell:sh ' + SCRIPT + ' CONFIG ') for call in guest.calls))
        self.assertTrue(any(call.startswith('shell:sh ' + SCRIPT + ' STOP ') for call in guest.calls))

    def test_status_mismatch_never_becomes_valid_and_cleanup_is_recorded(self):
        guest = FakeGuest(bad_status=True)
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertFalse(result['valid'])
        self.assertEqual(self.report.data['rf_model'], 'synthetic_guest_bridge_invalid')
        self.assertEqual(result['guest_controller']['cleanup'], 'confirmed')
        self.assertEqual(result['first_error']['code'], 'guest_receipt_mismatch')
        self.assertIn('fleet_stop', result['host_rf_model'])

    def test_unknown_start_and_cleanup_failure_preserve_first_error(self):
        guest = FakeGuest(fail_start=True, fail_cleanup=True)
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertFalse(result['valid'])
        self.assertEqual(result['first_error']['code'], 'adb_timeout')
        self.assertEqual(result['guest_controller']['cleanup'], 'unknown')
        self.assertTrue(result['cleanup_errors'])
        self.assertIn('fleet_stop', result['host_rf_model'])

    def test_wrong_nonce_sequence_revision_hash_or_receipt_never_passes(self):
        for field in ('nonce', 'sequence', 'revision', 'source_hash', 'receipt'):
            with self.subTest(field=field):
                report = check.Report(Path(self.tmp.name) / ('tamper-' + field))
                report.data.update(android_os='booted', adb_verified=True,
                                   identity=self.report.data['identity'])
                guest = FakeGuest(tamper=field)
                with mock.patch.object(bridge, '_exchange', side_effect=guest):
                    with self.assertRaises(check.BoundaryError):
                        bridge.run_guest_rf_check(self.endpoint, self.server, report,
                                                  deadline=time.monotonic() + 30,
                                                  emulator_process=self.emulator)
                self.assertFalse(report.data['rf_bridge']['valid'])
                self.assertEqual(report.data['rf_bridge']['first_error']['code'],
                                 'guest_receipt_mismatch')
                self.assertEqual(report.data['rf_bridge']['guest_controller']['cleanup'],
                                 'confirmed')

    def test_cleanup_failure_after_valid_sequence_is_not_success(self):
        with self.assertRaises(check.BoundaryError) as error:
            self.run_bridge(FakeGuest(fail_cleanup=True))
        self.assertEqual(error.exception.code, 'guest_cleanup_unknown')
        self.assertFalse(self.report.data['rf_bridge']['valid'])
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'],
                         'guest_cleanup_unknown')

    def test_interrupt_during_cleanup_is_recorded_as_unknown(self):
        guest = FakeGuest()
        original = guest.__call__
        def interrupted(endpoint, server, service, deadline):
            if service.startswith('shell:rm -f '):
                raise KeyboardInterrupt()
            return original(endpoint, server, service, deadline)
        with mock.patch.object(bridge, '_exchange', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                                          deadline=time.monotonic() + 30,
                                          emulator_process=self.emulator)
        self.assertFalse(self.report.data['rf_bridge']['valid'])
        self.assertEqual(self.report.data['rf_bridge']['guest_controller']['cleanup'], 'unknown')
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'], 'interrupted')

    def test_memory_emergency_during_bridge_is_not_valid(self):
        guest = FakeGuest()
        with mock.patch.object(bridge, '_exchange', side_effect=guest), \
             mock.patch.object(check, 'resources', return_value={'available_mib': 400}):
            with self.assertRaises(check.BoundaryError) as error:
                bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                                          deadline=time.monotonic() + 30,
                                          emulator_process=self.emulator)
        self.assertEqual(error.exception.code, 'memory_emergency_stop')
        self.assertFalse(self.report.data['rf_bridge']['valid'])
        self.assertEqual(self.report.data['rf_bridge']['guest_controller']['cleanup'], 'unknown')
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'],
                         'memory_emergency_stop')

    def test_wire_transport_uses_only_owned_loopback_and_exact_serial(self):
        observed = []
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(2)
            endpoint = check.Endpoint(adb_port=listener.getsockname()[1])
            def peer():
                with listener.accept()[0] as stream:
                    stream.settimeout(2)
                    for _ in range(2):
                        length = int(check._receive(stream, 4), 16)
                        observed.append(check._receive(stream, length).decode('ascii'))
                        stream.sendall(b'OKAY')
                    stream.sendall(b'DGM-CLEAN-OK\n')
            thread = threading.Thread(target=peer)
            thread.start()
            service = bridge._cleanup_service('a' * 32)
            try:
                self.assertEqual(bridge._exchange(endpoint, self.server, service,
                                                  time.monotonic() + 2), 'DGM-CLEAN-OK')
            finally:
                thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(observed, ['host:transport:emulator-5680', service])

    def test_source_is_exact_six_and_script_paths_are_fixed(self):
        source = bridge.SOURCE_SETTINGS
        self.assertEqual(set(source), {'frequency_hz', 'power_dbm', 'bandwidth_hz',
                                       'duty_cycle', 'modulation', 'crest_factor_db'})
        self.assertEqual(bridge.source_sha256(source), hashlib.sha256(
            b'2450000000|12.5|20000000|0.25|OFDM|3\n').hexdigest())
        for bad in ({**source, 'modulation': 'OFDM; reboot'},
                    {**source, 'frequency_hz': float('nan')},
                    {**source, 'extra': 1}):
            with self.subTest(bad=bad), self.assertRaises(check.BoundaryError):
                bridge.source_sha256(bad)
        nonce = 'a' * 32
        tokens = ('2450000000', '12.5', '20000000', '0.25', 'OFDM', '3')
        for operation, fields, digest in (
                ('CONFIG', ('1;reboot', *tokens[1:]), bridge.source_sha256(source)),
                ('CONFIG', tokens, '0' * 64),
                ('START', tokens, None)):
            with self.subTest(operation=operation, fields=fields), \
                 self.assertRaises(check.BoundaryError):
                bridge._command_service(operation, nonce, 1, fields, digest)


if __name__ == '__main__':
    unittest.main()
