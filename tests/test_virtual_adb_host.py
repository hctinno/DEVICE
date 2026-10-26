"""Own loopback sockets only; optional pinned adbutils is a real wire client."""
from decimal import Decimal, localcontext
import importlib
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example

ROOT = Path(__file__).resolve().parents[1]
SOURCE = dict(frequency_hz=2450000000, power_dbm=12.5,
              bandwidth_hz=20000000, duty_cycle=0.25,
              modulation='OFDM', crest_factor_db=3)


class VirtualAdbHostTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_adb_host'),
                             'required ADB host implementation is missing')
        self.module = importlib.import_module('labflow.virtual_adb_host')
        catalog = load_catalog(ROOT / 'virtual_profiles/sm_a176u_unlicensed.json')
        self.fleet, _, _ = create_conducted_example(catalog)

    def wire(self, server, commands):
        with socket.create_connection(server.endpoint, timeout=2) as peer:
            result = b''
            for command in commands:
                data = command.encode()
                peer.sendall(f'{len(data):04x}'.encode() + data)
                status = peer.recv(4)
                if status != b'OKAY':
                    size = int(peer.recv(4), 16)
                    raise ValueError(peer.recv(size).decode())
            while data := peer.recv(32768):
                result += data
            return result.decode()

    def shell(self, server, command):
        return self.wire(server, ['host:transport:' + self.module.SERIAL, 'shell:' + command])

    def test_shared_fleet_configure_acquire_power_path_stop_and_decimal(self):
        with self.module.VirtualAdbHost(self.fleet, port=0) as server:
            for power, loss in [(12.5, .5), (16, 2)]:
                source = {**SOURCE, 'power_dbm': power}
                reply = json.loads(self.shell(server, 'dgm-twin rf configure ' + json.dumps(source)))
                self.assertEqual(reply['status'], 'ok')
                path = self.fleet.execute('test:path:' + str(power), 'switch', 'configure', {'loss_db': loss})
                self.assertEqual(path['status'], 'ok')
                self.shell(server, 'dgm-twin rf start')
                self.shell(server, 'dgm-twin advance 3')
                self.shell(server, 'dgm-twin measurement acquire')
                self.shell(server, 'dgm-twin advance 2')
                read = json.loads(self.shell(server, 'dgm-twin measurement read'))
                value = read['meter']['values']['outputs']['measurement']['value']
                with localcontext() as ctx:
                    ctx.prec = 40
                    expected = Decimal(str(power)) - 10 - Decimal(str(loss)) - 20 + 10 * Decimal('.25').log10()
                self.assertAlmostEqual(value, float(expected), places=9)
                self.assertEqual(read['sensor'], self.fleet.observations()['devices']['sensor'])
                self.assertFalse(read['meter']['hardware_verified'])
            self.shell(server, 'dgm-twin rf stop')
            self.shell(server, 'dgm-twin advance 2')
            stopped = json.loads(self.shell(server, 'dgm-twin rf status'))
            self.assertFalse(stopped['values'].get('outputs', {}).get('rf', {}).get('valid', False))
        self.assertEqual(server.resources()['active_connections'], 0)
        self.assertFalse(server.resources()['thread_alive'])

    def test_fail_closed_identity_and_unknown_inputs(self):
        with self.module.VirtualAdbHost(self.fleet, port=0) as server:
            self.assertEqual(self.shell(server, 'getprop ro.product.model'), 'DGM Virtual DUT\n')
            for command in ['getprop ro.kernel.qemu', 'getprop ro.product.manufacturer; whoami',
                            'dgm-twin rf configure {}', 'dgm-twin advance 10001',
                            'dgm-twin advance 17',
                            'dgm-twin advance true', 'dgm-twin rf stop extra', 'id',
                            'dgm-twin rf configure {"frequency_hz":1,"frequency_hz":2}']:
                with self.subTest(command=command), self.assertRaises(ValueError):
                    self.shell(server, command)
            for service in ['host:transport:OTHER', 'host:devices', 'host:connect:example.com:5555', 'shell:id']:
                with self.subTest(service=service), self.assertRaises(ValueError):
                    self.wire(server, [service])

    def test_malformed_truncated_timeout_peer_close_and_bounded_cleanup(self):
        with self.module.VirtualAdbHost(self.fleet, port=0, connection_timeout=.15) as server:
            for data in [b'ZZZZ', b'ffff', b'0000', b'0010x', b'00']:
                with socket.create_connection(server.endpoint, timeout=2) as peer:
                    peer.sendall(data)
                    peer.shutdown(socket.SHUT_WR)
                    self.assertEqual(peer.recv(4), b'FAIL')
            peer = socket.create_connection(server.endpoint, timeout=2)
            peer.sendall(b'00')
            self.assertEqual(peer.recv(4), b'FAIL')
            peer.close()
            with socket.create_connection(server.endpoint, timeout=2):
                pass
        self.assertEqual(server.resources()['active_connections'], 0)
        self.assertTrue(any(e['outcome'] == 'protocol_error' for e in server.trace()))
        with socket.socket() as probe:
            probe.bind(server.endpoint)

    def test_explicit_port_limits_and_lifecycle(self):
        for value in [5037, 5555, True, -1]:
            with self.assertRaises(ValueError):
                self.module.VirtualAdbHost(self.fleet, port=value)
        server = self.module.VirtualAdbHost(self.fleet, port=0, lifetime=.2)
        with server:
            time.sleep(.3)
        self.assertFalse(server.resources()['thread_alive'])
        with self.assertRaises(RuntimeError):
            server.__enter__()

    def test_action_budget_saturation_and_observation_only_after_budget(self):
        with self.module.VirtualAdbHost(self.fleet, port=0) as server:
            for _ in range(self.module.MAX_ACTIONS):
                self.shell(server, 'dgm-twin advance 1')
            with self.assertRaises(ValueError):
                self.shell(server, 'dgm-twin advance 1')
            self.assertEqual(json.loads(self.shell(server, 'dgm-twin rf status'))['device_id'], 'dut')
            self.assertEqual(server.resources()['actions_total'], self.module.MAX_ACTIONS)

    def test_connection_capacity_and_close_with_active_partial_peers(self):
        with self.module.VirtualAdbHost(self.fleet, port=0, connection_timeout=2) as server:
            peers = []
            try:
                for _ in range(self.module.MAX_ACTIVE):
                    peer = socket.create_connection(server.endpoint, timeout=2)
                    peer.sendall(b'00')
                    peers.append(peer)
                deadline = time.monotonic() + 1
                while server.resources()['active_connections'] < self.module.MAX_ACTIVE and time.monotonic() < deadline:
                    time.sleep(.005)
                with socket.create_connection(server.endpoint, timeout=2) as rejected:
                    self.assertEqual(rejected.recv(4), b'')
                self.assertEqual(server.resources()['active_connections'], self.module.MAX_ACTIVE)
                server.close()
                self.assertEqual(server.resources()['active_connections'], 0)
                self.assertEqual(server.resources()['active_workers'], 0)
            finally:
                for peer in peers:
                    peer.close()

    def test_author_disconnect_observation_has_no_author_fault_truth(self):
        self.fleet.author_control('author:disconnect', 'meter', 'disconnected', True)
        with self.module.VirtualAdbHost(self.fleet, port=0) as server:
            read = json.loads(self.shell(server, 'dgm-twin measurement read'))
            self.assertEqual(read['meter']['status'], 'disconnected')
            self.assertNotIn('author:disconnect', json.dumps(read))
            self.assertNotIn('faults', json.dumps(read))

    def test_cli_preserves_missing_source_failure_without_fallback(self):
        from labflow.virtual_adb_check import run_check
        with tempfile.TemporaryDirectory() as folder:
            result = run_check(Path(folder) / 'failure-run',
                               source_path=Path(folder) / 'missing-source',
                               deps_path=Path(folder) / 'missing-deps')
            self.assertEqual(result['status'], 'incomplete')
            self.assertEqual(result['error']['type'], 'FileNotFoundError')
            self.assertEqual(result['connections'], [])
            self.assertEqual(result['denied_operations'], [])
            self.assertFalse(result['resources_after_close']['thread_alive'])
            self.assertEqual(result['resources_after_close']['active_connections'], 0)
            self.assertTrue((Path(folder) / 'failure-run/result.json').is_file())

    @unittest.skipUnless(os.environ.get('DGM_ADBUTILS_SOURCE'), 'pinned source path opt-in required')
    def test_genuine_pinned_adbutils_wire_and_cli_artifacts(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_adb_check'),
                             'required genuine client demonstration is missing')
        from labflow.virtual_adb_check import run_check
        with tempfile.TemporaryDirectory() as folder:
            result = run_check(Path(folder) / 'new-run',
                               source_path=Path(os.environ['DGM_ADBUTILS_SOURCE']),
                               deps_path=Path(os.environ['DGM_ADBUTILS_DEPS']))
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(result['client'], 'pinned_adbutils_real_host_wire')
            self.assertEqual(result['state'], 'device')
            self.assertEqual(result['denied_operations'], [])
            self.assertFalse(result['sdk_verified'])
            self.assertFalse(result['hardware_verified'])
            trace = json.loads((Path(folder) / 'new-run/trace.json').read_text())
            self.assertTrue(any(e.get('service', '').startswith('shell:dgm-twin') for e in trace))
            with self.assertRaises(FileExistsError):
                run_check(Path(folder) / 'new-run', source_path=Path(os.environ['DGM_ADBUTILS_SOURCE']),
                          deps_path=Path(os.environ['DGM_ADBUTILS_DEPS']))

    @unittest.skipUnless(os.environ.get('DGM_ADBUTILS_SOURCE'), 'pinned source path opt-in required')
    def test_genuine_client_failures_and_fallback_process_guard(self):
        from labflow.virtual_adb_check import _pinned_client, own_wire_only
        import subprocess
        denied, connections = [], []
        with self.module.VirtualAdbHost(self.fleet, port=0) as server:
            with own_wire_only(server.endpoint, denied, connections):
                adbutils, _ = _pinned_client(Path(os.environ['DGM_ADBUTILS_SOURCE']),
                                            Path(os.environ['DGM_ADBUTILS_DEPS']))
                client = adbutils.AdbClient(host=server.endpoint[0], port=server.endpoint[1], socket_timeout=1)
                device = client.device(serial=self.module.SERIAL)
                self.assertEqual(device.get_state(), 'device')
                with client.make_connection() as connection:
                    connection.send_command('host:transport:OTHER')
                    with self.assertRaises(adbutils.AdbError):
                        connection.check_okay()
                with device.open_transport() as connection:
                    connection.send_command('shell:getprop ro.kernel.qemu')
                    with self.assertRaises(adbutils.AdbError):
                        connection.check_okay()
                # Use the public connection context on FAIL paths: the pinned
                # .shell implementation does not close if open_shell raises.
                with self.assertRaises(PermissionError):
                    subprocess.Popen(['dgm-never-executed'])
        self.assertEqual(denied, ['subprocess.Popen'])
        self.assertTrue(connections)
        self.assertEqual(server.resources()['active_connections'], 0)

    @unittest.skipUnless(os.environ.get('DGM_ADBUTILS_SOURCE'), 'pinned source path opt-in required')
    def test_genuine_client_power_path_delta_matches_decimal_on_same_fleet(self):
        from labflow.virtual_adb_check import _pinned_client, own_wire_only
        denied, connections = [], []
        with self.module.VirtualAdbHost(self.fleet, port=0) as server:
            with own_wire_only(server.endpoint, denied, connections):
                adbutils, _ = _pinned_client(Path(os.environ['DGM_ADBUTILS_SOURCE']),
                                            Path(os.environ['DGM_ADBUTILS_DEPS']))
                client = adbutils.AdbClient(host=server.endpoint[0], port=server.endpoint[1], socket_timeout=2)
                device = client.device(serial=self.module.SERIAL)
                for index, (power, loss) in enumerate([(9, .5), (18, 2)]):
                    configured = json.loads(device.shell('dgm-twin rf configure ' + json.dumps({**SOURCE, 'power_dbm': power})))
                    self.assertEqual(configured['status'], 'ok')
                    self.assertEqual(self.fleet.execute('genuine:path:' + str(index), 'switch',
                                                       'configure', {'loss_db': loss})['status'], 'ok')
                    for command in ['dgm-twin rf start', 'dgm-twin advance 3',
                                    'dgm-twin measurement acquire', 'dgm-twin advance 2']:
                        device.shell(command, timeout=2)
                    read = json.loads(device.shell('dgm-twin measurement read', timeout=2))
                    with localcontext() as ctx:
                        ctx.prec = 40
                        expected = Decimal(power) - 10 - Decimal(str(loss)) - 20 + 10 * Decimal('.25').log10()
                    actual = read['meter']['values']['outputs']['measurement']['value']
                    self.assertAlmostEqual(actual, float(expected), places=9)
                    self.assertEqual(read['sensor'], self.fleet.observations()['devices']['sensor'])
                device.shell('dgm-twin rf stop', timeout=2)
        self.assertEqual(denied, [])
        self.assertTrue(connections)


if __name__ == '__main__':
    unittest.main()
