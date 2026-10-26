"""Boundary fixtures and benign child processes; these are not Android OS proof."""

import hashlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import threading
import unittest
from unittest import mock
import zipfile

from labflow import android_emulator_check as check


class RuntimeBoundaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def test_default_preflight_preserves_missing_runtime_and_raw_result(self):
        runtime, output = self.base / 'missing', self.base / 'proof'
        result = check.execute(runtime, output)
        self.assertEqual('not_run', result['android_os'])
        self.assertEqual('runtime_missing', result['first_failure']['code'])
        self.assertFalse(runtime.exists())
        self.assertFalse(result['adb_verified'])
        self.assertEqual('not_assessed', result['rf_model'])
        self.assertEqual(result, json.loads((output / 'result.json').read_text('utf-8')))

    def test_new_output_is_required_and_never_overwritten(self):
        output = self.base / 'proof'
        output.mkdir()
        (output / 'prior.txt').write_text('original', encoding='utf-8')
        with self.assertRaises(check.BoundaryError):
            check.execute(self.base / 'runtime', output)
        self.assertEqual('original', (output / 'prior.txt').read_text('utf-8'))

    def test_unowned_or_nested_or_symlink_runtime_is_rejected(self):
        runtime = self.base / 'runtime'
        runtime.mkdir()
        for output in [self.base / 'proof', runtime / 'proof']:
            with self.subTest(output=output):
                result = check.execute(runtime, output)
                self.assertEqual('runtime_unowned', result['first_failure']['code'])

    def test_endpoint_never_default_server_or_arbitrary_serial(self):
        endpoint = check.Endpoint(15037, 5680, 18554)
        self.assertEqual('emulator-5680', endpoint.serial)
        self.assertEqual('tcp:127.0.0.1:15037', endpoint.server_socket)
        for args in [(5037, 5680, 18554), (15037, 5681, 18554),
                     (15037, 5552, 18554), (15037, 5680, 15037),
                     (5681, 5680, 18554), (True, 5680, 18554)]:
            with self.subTest(args=args), self.assertRaises(check.BoundaryError):
                check.Endpoint(*args)

    def test_private_environment_removes_external_adb_keys_and_disables_scan(self):
        runtime, output = self.base / 'runtime', self.base / 'proof'
        env = check.private_environment(runtime, output, check.Endpoint(),
            {'PATH': 'unchanged', 'HOME': 'user', 'ADB_VENDOR_KEYS': 'userkeys',
             'ANDROID_ADB_SERVER_PORT': '5037', 'ADB_SERVER_SOCKET': 'tcp:other:5037'})
        self.assertEqual('unchanged', env['PATH'])
        self.assertEqual('0', env['ADB_USB'])
        self.assertEqual('0', env['ADB_EMU'])
        self.assertEqual('0', env['ADB_MDNS'])
        self.assertEqual('0', env['ADB_LOCAL_TRANSPORT_MAX_PORT'])
        self.assertEqual('tcp:127.0.0.1:15037', env['ADB_SERVER_SOCKET'])
        self.assertNotIn('userkeys', str(env))
        self.assertNotEqual('user', env['HOME'])

    def test_memory_guard_requires_official_guest_minimum_and_headroom(self):
        self.assertFalse(check.memory_gate(2300)['allowed'])
        gate = check.memory_gate(3584)
        self.assertTrue(gate['allowed'])
        self.assertEqual(3584, gate['required_available_mib'])
        with self.assertRaises(check.BoundaryError):
            check.memory_gate(8192, guest_mib=512)

    def test_claim_attempt_survives_new_output_and_does_not_overwrite(self):
        runtime = self.base / 'runtime'
        runtime.mkdir()
        check.claim_attempt(runtime, self.base / 'proof')
        original = (runtime / 'boot-attempt.json').read_bytes()
        with self.assertRaises(check.BoundaryError):
            check.claim_attempt(runtime, self.base / 'second')
        self.assertEqual(original, (runtime / 'boot-attempt.json').read_bytes())

    def test_first_failure_survives_cleanup_failure(self):
        report = check.Report(self.base / 'proof')
        report.fail('native_exit', 'original error')
        report.fail('cleanup_error', 'later error')
        report.save()
        self.assertEqual('native_exit', report.data['first_failure']['code'])
        self.assertEqual(2, len(report.data['failures']))

    def test_zip_rejects_traversal_absolute_drive_backslash_and_links(self):
        for name in ['../escape', '/absolute', 'C:/absolute', 'a\\..\\escape', 'a:stream']:
            with self.subTest(name=name):
                raw = io.BytesIO()
                with zipfile.ZipFile(raw, 'w') as archive:
                    archive.writestr(name, b'bad')
                target = self.base / hashlib.sha256(name.encode()).hexdigest()
                with self.assertRaises(check.BoundaryError):
                    check.safe_extract(raw.getvalue(), target, 1024)
                self.assertFalse(target.exists())
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            info = zipfile.ZipInfo('link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b'target')
        with self.assertRaises(check.BoundaryError):
            check.safe_extract(raw.getvalue(), self.base / 'link', 1024)

    def test_zip_expansion_cap_checked_before_writing(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('big', b'x' * 2048)
        with self.assertRaises(check.BoundaryError):
            check.safe_extract(raw.getvalue(), self.base / 'big', 1024)
        self.assertFalse((self.base / 'big').exists())

    def test_zip_valid_archive_is_preserved_and_extracted(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            archive.writestr('tool/source.properties', b'Pkg.Revision=1')
        count = check.safe_extract(raw.getvalue(), self.base / 'valid', 1024)
        self.assertEqual(14, count)
        self.assertTrue((self.base / 'valid/tool/source.properties').is_file())

    def test_metadata_selects_stable_windows_not_preview_or_other_os(self):
        xml = b'''<repository><license id="sdk">terms</license>
        <remotePackage path="emulator"><revision><major>99</major></revision>
        <channelRef ref="channel-3"/><uses-license ref="sdk"/>
        <archives><archive><host-os>windows</host-os><complete><size>7</size>
        <checksum type="sha1">1111111111111111111111111111111111111111</checksum>
        <url>preview.zip</url></complete></archive></archives></remotePackage>
        <remotePackage path="emulator"><revision><major>37</major><minor>2</minor></revision>
        <channelRef ref="channel-0"/><uses-license ref="sdk"/>
        <archives><archive><host-os>windows</host-os><complete><size>7</size>
        <checksum type="sha1">2222222222222222222222222222222222222222</checksum>
        <url>stable.zip</url></complete></archive></archives></remotePackage></repository>'''
        package = check.select_package(xml, 'emulator', check.REPOSITORY)
        self.assertEqual('37.2', package['version'])
        self.assertTrue(package['url'].endswith('/stable.zip'))
        self.assertEqual('terms', package['license_text'])
        for bad in [xml.replace(b'stable.zip', b'../escape.zip'),
                    xml.replace(b'stable.zip', b'https://evil.example/tool.zip'),
                    xml.replace(b'<size>7</size>', b'<size>9999999999</size>')]:
            with self.assertRaises(check.BoundaryError):
                check.select_package(bad, 'emulator', check.REPOSITORY)

    def test_download_checksum_failure_preserves_partial_and_budget(self):
        response = mock.MagicMock()
        response.read.side_effect = [b'actual', b'']
        response.headers = {'Content-Length': '6'}
        response.geturl.return_value = 'https://dl.google.com/android/repository/test.zip'
        response.__enter__.return_value = response
        package = dict(url=response.geturl(), size=6, checksum='0' * 64, checksum_type='sha256')
        budget = check.DownloadBudget(100)
        opener = mock.MagicMock()
        opener.open.return_value = response
        with mock.patch.object(check.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(check.BoundaryError):
                check.download(package, self.base / 'tool.zip', budget)
        self.assertEqual(b'actual', (self.base / 'tool.zip.partial').read_bytes())
        self.assertEqual(6, budget.used)

    def test_metadata_stream_failure_preserves_partial_and_consumed_budget(self):
        response = mock.MagicMock()
        response.geturl.return_value = check.REPOSITORY
        response.read.side_effect = [b'original partial', OSError('interrupted stream')]
        response.__enter__.return_value = response
        opener = mock.MagicMock()
        opener.open.return_value = response
        budget = check.DownloadBudget(100)
        with mock.patch.object(check.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(OSError):
                check.metadata(check.REPOSITORY, self.base / 'meta.xml', budget)
        self.assertEqual(b'original partial', (self.base / 'meta.xml.partial').read_bytes())
        self.assertEqual(16, budget.used)

    @unittest.skipUnless(os.name == 'nt', 'Windows owned process RSS')
    def test_owned_process_samples_tree_rss_and_preserves_owner_pids(self):
        report = check.Report(self.base / 'proof')
        with check.OwnedProcess([sys.executable, '-c', 'import time; time.sleep(10)'],
             os.environ.copy(), report, 'rss', memory_limit_mib=256) as process:
            process.sample()
            sample = process.record['snapshots'][-1]
            self.assertIn(process.process.pid, sample['pids'])
            self.assertGreater(sample['tree_rss_mib'], 0)
        self.assertTrue(process.record['closed'])

    def test_memory_rejection_never_claims_attempt_or_starts_process(self):
        report = check.Report(self.base / 'proof')
        runtime = self.base / 'runtime'
        runtime.mkdir()
        with mock.patch.object(check, 'resources', return_value={'available_mib': 2200}):
            with self.assertRaises(check.BoundaryError) as error:
                check.boot_runtime(runtime, report, {}, check.Endpoint(), 180, 'auto', '')
        self.assertEqual('memory_headroom_insufficient', error.exception.code)
        self.assertEqual([], report.data['processes'])
        self.assertFalse((runtime / 'boot-attempt.json').exists())

    def test_cached_archive_is_verified_without_new_download_or_budget_reset(self):
        archive = self.base / 'cached.zip'
        archive.write_bytes(b'original')
        spec = dict(size=8, checksum=hashlib.sha256(b'original').hexdigest(),
                    checksum_type='sha256', url=check.REPOSITORY)
        budget = check.DownloadBudget(100)
        budget.used = 73
        proof = check.cached_archive(spec, archive, budget)
        self.assertTrue(proof['reused'])
        self.assertEqual(73, budget.used)
        archive.write_bytes(b'changed!')
        with self.assertRaises(check.BoundaryError):
            check.cached_archive(spec, archive, budget)

    def test_package_publish_preserves_staging_and_rejects_existing_change(self):
        staging = self.base / 'stage'
        staging.mkdir()
        (staging / 'tool').write_bytes(b'original')
        destination = self.base / 'sdk/tool'
        check.publish_package(staging, destination)
        self.assertEqual(b'original', (staging / 'tool').read_bytes())
        check.publish_package(staging, destination)
        (destination / 'tool').write_bytes(b'changed')
        with self.assertRaises(check.BoundaryError):
            check.publish_package(staging, destination)
        self.assertEqual(b'changed', (destination / 'tool').read_bytes())

    def test_resume_requires_an_existing_incomplete_owned_runtime(self):
        report = check.Report(self.base / 'proof')
        runtime = self.base / 'runtime'
        with self.assertRaises(check.BoundaryError):
            check.install_runtime(runtime, report, True, resume=True)
        self.assertFalse(runtime.exists())

    def test_download_cap_prevents_request(self):
        with mock.patch.object(check.urllib.request, 'urlopen') as opened:
            with self.assertRaises(check.BoundaryError):
                check.download(dict(url=check.REPOSITORY, size=101), self.base / 'x', check.DownloadBudget(100))
            opened.assert_not_called()

    def test_owned_process_timeout_keeps_logs_and_stops_only_child(self):
        report = check.Report(self.base / 'proof')
        env = os.environ.copy()
        process = check.OwnedProcess([sys.executable, '-c',
            "import time; print('first',flush=True); time.sleep(30)"], env,
            report, 'benign', memory_limit_mib=256)
        with process:
            with self.assertRaises(check.BoundaryError):
                process.wait(0.3)
        self.assertIsNotNone(process.process.poll())
        self.assertIn(b'first', (report.output / 'benign.stdout.log').read_bytes())
        self.assertTrue(report.data['processes'][0]['closed'])

    def test_owned_process_error_does_not_discard_original_exit(self):
        report = check.Report(self.base / 'proof')
        with check.OwnedProcess([sys.executable, '-c',
             "import sys; print('raw failure',file=sys.stderr); sys.exit(7)"],
             os.environ.copy(), report, 'benign-exit', memory_limit_mib=256) as process:
            self.assertEqual(7, process.wait(5))
        self.assertIn(b'raw failure', (report.output / 'benign-exit.stderr.log').read_bytes())
        self.assertEqual(7, report.data['processes'][0]['exit_code'])

    def test_wire_command_whitelist_and_explicit_serial(self):
        endpoint = check.Endpoint()
        self.assertEqual('host-serial:emulator-5680:get-state',
                         check.wire_services(endpoint, 'get-state')[0])
        self.assertEqual(['host:transport:emulator-5680', 'shell:getprop ro.kernel.qemu'],
                         check.wire_services(endpoint, 'ro.kernel.qemu'))
        for value in ['devices', 'connect', 'shell rm -rf /', 'ro.serialno', 'sys.boot_completed;reboot']:
            with self.subTest(value=value), self.assertRaises(check.BoundaryError):
                check.wire_services(endpoint, value)

    def test_busy_owned_port_rejected_without_connection_or_discovery(self):
        with socket.socket() as held:
            held.bind(('127.0.0.1', 0))
            port = held.getsockname()[1]
            with self.assertRaises(check.BoundaryError):
                check.assert_ports_free([port])

    def test_wire_reads_only_exact_owned_serial_and_property(self):
        observed = []
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(3)
            endpoint = check.Endpoint(adb_port=listener.getsockname()[1])
            def peer():
                with listener.accept()[0] as stream:
                    stream.settimeout(3)
                    for _ in range(2):
                        length = int(check._receive(stream, 4), 16)
                        observed.append(check._receive(stream, length).decode())
                        stream.sendall(b'OKAY')
                    stream.sendall(b'1\r\n')
            worker = threading.Thread(target=peer)
            worker.start()
            server = mock.Mock()
            server.process.poll.return_value = None
            try:
                self.assertEqual('1', check.adb_read(endpoint, 'sys.boot_completed', server))
            finally:
                worker.join(4)
            self.assertFalse(worker.is_alive())
        self.assertEqual(['host:transport:emulator-5680', 'shell:getprop sys.boot_completed'], observed)

    def test_dead_owned_server_never_connects_or_autostarts(self):
        server = mock.Mock()
        server.process.poll.return_value = 7
        with mock.patch.object(check.socket, 'create_connection') as connect:
            with self.assertRaises(check.BoundaryError) as error:
                check.adb_read(check.Endpoint(), 'get-state', server)
        self.assertEqual('owned_adb_server_exited', error.exception.code)
        connect.assert_not_called()

    def test_cli_invalid_options_are_rejected(self):
        with self.assertRaises(SystemExit):
            check.parser().parse_args(['--runtime', 'x', '--output', 'y', '--boot-timeout', '181'])


if __name__ == '__main__':
    unittest.main()
