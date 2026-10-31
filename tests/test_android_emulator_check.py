"""Boundary fixtures and benign child processes; these are not Android OS proof."""

import hashlib
import copy
from contextlib import ExitStack, contextmanager
import inspect
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import zipfile

from labflow import android_emulator_check as check
from labflow import android_guest_rf_bridge as guest_bridge
from test_android_guest_rf_bridge import authored_plan, FakeGuest, value_sha256


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

    def test_rf_bridge_requires_explicit_boot_before_sdk_access(self):
        args = check.parser().parse_args(['--runtime', 'x', '--output', 'y',
                                          '--boot', '--rf-bridge-check'])
        self.assertTrue(args.rf_bridge_check)
        output = self.base / 'rf-option-proof'
        result = check.execute(self.base / 'absent-runtime', output, rf_bridge_check=True)
        self.assertEqual(result['first_failure']['code'], 'options_invalid')
        self.assertEqual(result['android_os'], 'not_run')
        self.assertEqual(result['rf_model'], 'not_assessed')

    def test_rf_bridge_rejects_custom_endpoint_before_runtime_or_native_access(self):
        endpoint = check.Endpoint(adb_port=15038, console_port=5678, grpc_port=18554)
        with mock.patch.object(check, 'validate_runtime', side_effect=AssertionError('SDK read')):
            result = check.execute(self.base / 'absent-runtime', self.base / 'rf-port-proof',
                                   boot=True, rf_bridge_check=True, endpoint=endpoint)
        self.assertEqual(result['first_failure']['code'], 'rf_bridge_endpoint_invalid')
        self.assertEqual(result['android_os'], 'not_run')
        self.assertEqual(result['adb_verified'], False)

    def test_direct_boot_bridge_rejects_custom_endpoint_before_boot_claim(self):
        endpoint = check.Endpoint(adb_port=15038, console_port=5678, grpc_port=18554)
        report = check.Report(self.base / 'rf-direct-port-proof')
        with mock.patch.object(check, 'claim_attempt', side_effect=AssertionError('boot claim')):
            with self.assertRaises(check.BoundaryError) as error:
                check.boot_runtime(self.base / 'runtime', report, {}, endpoint, 1, 'auto', '',
                                   rf_bridge_check=True)
        self.assertEqual(error.exception.code, 'rf_bridge_endpoint_invalid')

    def test_rf_bridge_hook_runs_only_after_exact_guest_identity_inside_owned_lifetime(self):
        from labflow import android_guest_rf_bridge as bridge
        report = check.Report(self.base / 'rf-hook-proof')
        runtime = self.base / 'runtime'
        runtime.mkdir()
        server = mock.MagicMock()
        emulator = mock.MagicMock()
        server.process.poll.return_value = None
        emulator.process.poll.return_value = None
        server.__enter__.return_value = server
        emulator.__enter__.return_value = emulator
        seen = []
        def guest_hook(endpoint, owner, current, *, deadline, emulator_process):
            self.assertIs(owner, server)
            self.assertIs(emulator_process, emulator)
            self.assertEqual(current.data['identity']['serial'], 'emulator-5680')
            self.assertEqual(current.data['identity']['properties']['sys.boot_completed'], '1')
            self.assertTrue(current.data['adb_verified'])
            seen.append(deadline)
            current.data['rf_bridge'] = {'valid': True, 'fixture': True}
        answers = ['device', 'device', '1', 'ranchu', 'AOSP fixture', '1']
        help_text = '-no-window -no-audio -no-snapshot -memory -port -grpc -gpu'
        with mock.patch.object(check, 'resources', return_value={'available_mib': 8192}), \
             mock.patch.object(check, 'assert_ports_free'), \
             mock.patch.object(check, 'create_avd', return_value=self.base / 'avd'), \
             mock.patch.object(check, 'claim_attempt'), \
             mock.patch.object(check, 'OwnedProcess', side_effect=[server, emulator]), \
             mock.patch.object(check, 'adb_read', side_effect=answers), \
             mock.patch.object(bridge, 'run_guest_rf_check', side_effect=guest_hook):
            check.boot_runtime(runtime, report, {}, check.Endpoint(), 1, 'auto',
                               help_text, rf_bridge_check=True)
        self.assertEqual(report.data['status'], 'rf_bridge_verified')
        self.assertEqual(json.loads((report.output / 'result.json').read_text('utf-8'))['status'],
                         'rf_bridge_verified')
        self.assertEqual(len(seen), 1)
        self.assertGreater(seen[0], time.monotonic())
        server.__exit__.assert_called_once()
        emulator.__exit__.assert_called_once()


class ReviewFixes(unittest.TestCase):
    """Five review regressions; fake SDK bytes are never executed."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction boundary')
    def test_f1_resume_nested_junction_cannot_write_outside_or_change_marker(self):
        runtime = self.base / 'runtime'
        runtime.mkdir()
        outside = self.base / 'outside'
        outside.mkdir()
        original = outside / 'emulator.license.txt'
        original.write_bytes(b'outside original')
        junction = runtime / 'sources'
        escaped = lambda p: str(p).replace("'", "''")
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
            f"New-Item -ItemType Junction -Path '{escaped(junction)}' -Target '{escaped(outside)}' | Out-Null"],
            check=True, capture_output=True, timeout=10)
        self.addCleanup(junction.rmdir)
        for name in ('repository.xml', 'aosp-images.xml'):
            (outside / name).write_bytes(b'<fixture/>')
        specs = [dict(package=n, version='1', source=check.REPOSITORY,
                      url='https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip',
                      size=1, checksum_type='sha256', checksum=check.CLI_SHA256,
                      license_id='android-sdk-license', license_text='fixture terms')
                 for n in ('cmdline-tools;22.0', 'platform-tools', 'emulator', check.IMAGE_PACKAGE)]
        marker = runtime / check.OWNER_FILE
        check.write_json(marker, dict(runtime=str(runtime), completed=False,
            packages=[{k:v for k,v in s.items() if k != 'license_text'} for s in specs],
            downloads=[], downloaded_bytes=0))
        before_marker = marker.read_bytes()
        before_outside = {p.name:p.read_bytes() for p in outside.iterdir()}
        report = check.Report(self.base / 'proof')
        with mock.patch.object(check, 'select_package', side_effect=specs), \
             mock.patch.object(check, 'cached_archive', side_effect=check.BoundaryError('fixture_stop')):
            with self.assertRaises(check.BoundaryError) as error:
                check.install_runtime(runtime, report, True, resume=True)
        self.assertEqual('linked_path', error.exception.code)
        self.assertEqual(before_marker, marker.read_bytes())
        self.assertEqual(before_outside, {p.name:p.read_bytes() for p in outside.iterdir()})

    def fixture_runtime(self):
        runtime = self.base / 'runtime'
        names = ('platform-tools/adb.exe', 'emulator/emulator.exe',
                 'emulator/qemu/windows-x86_64/qemu-system-x86_64.exe',
                 'emulator/dependency.dll', 'system-images/android-36/default/x86_64/system.img')
        for name in names:
            path = runtime / 'sdk' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture original')
        digest = hashlib.sha256(b'fixture original').hexdigest()
        check.write_json(runtime / check.OWNER_FILE, dict(runtime=str(runtime), completed=True,
            executables={name:digest for name in names[:3]},
            file_inventory={name:digest for name in names}, inventory_version=2))
        return runtime

    def test_f2_changed_image_is_rejected_before_native_execution(self):
        runtime = self.fixture_runtime()
        check.validate_runtime(runtime)
        image = runtime / 'sdk/system-images/android-36/default/x86_64/system.img'
        image.write_bytes(b'changed image')
        with self.assertRaises(check.BoundaryError) as error:
            check.validate_runtime(runtime)
        self.assertEqual('runtime_file_changed', error.exception.code)
        self.assertIn('system.img', str(error.exception))

    def test_normal_inventory_preserves_owner_and_covers_native_dependency(self):
        runtime = self.fixture_runtime()
        marker = runtime / check.OWNER_FILE
        original = marker.read_bytes()
        result = check.validate_runtime(runtime)
        self.assertEqual(original, marker.read_bytes())
        self.assertIn('emulator/dependency.dll', result['file_inventory'])
        self.assertIn('system-images/android-36/default/x86_64/system.img', result['file_inventory'])

    def test_f3_server_exit_is_first_failure_and_stops_boot_immediately(self):
        report = check.Report(self.base / 'proof')
        runtime = self.base / 'runtime'
        runtime.mkdir()
        server = mock.MagicMock()
        server.process.pid = 12345
        server.process.poll.return_value = 7
        emulator = mock.MagicMock()
        emulator.process.poll.return_value = None
        server.__enter__.return_value = server
        server.__exit__.return_value = False
        emulator.__enter__.return_value = emulator
        emulator.__exit__.return_value = False
        help_text = '-no-window -no-audio -no-snapshot -memory -port -grpc -gpu'
        not_found = check.BoundaryError('adb_service_failure', "device 'emulator-5680' not found")
        with mock.patch.object(check, 'resources', return_value={'available_mib': 8192}), \
             mock.patch.object(check, 'assert_ports_free'), \
             mock.patch.object(check, 'OwnedProcess', side_effect=[server, emulator]), \
             mock.patch.object(check, 'adb_read', side_effect=[not_found,
                 check.BoundaryError('owned_adb_server_exited', 'pid=12345 exit_code=7')]):
            with self.assertRaises(check.BoundaryError) as error:
                check.boot_runtime(runtime, report, {}, check.Endpoint(), 1, 'auto', help_text)
        self.assertEqual('owned_adb_server_exited', error.exception.code)
        self.assertEqual('owned_adb_server_exited', report.data['first_failure']['code'])
        self.assertIn('exit_code=7', report.data['first_failure']['detail'])
        # The owner may also exit after connect, while the wire read is active.
        owner = mock.Mock()
        owner.process.pid = 12345
        owner.process.poll.side_effect = [None, 7]
        stream = mock.MagicMock()
        stream.__enter__.return_value = stream
        stream.recv.return_value = b''
        with mock.patch.object(check.socket, 'create_connection', return_value=stream):
            with self.assertRaises(check.BoundaryError) as mid_read:
                check.adb_read(check.Endpoint(), 'get-state', owner)
        self.assertEqual('owned_adb_server_exited', mid_read.exception.code)
        self.assertIn('exit_code=7', str(mid_read.exception))

    def test_f4_slow_get_state_obeys_whole_operation_deadline(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(2)
            endpoint = check.Endpoint(adb_port=listener.getsockname()[1])
            def peer():
                with listener.accept()[0] as stream:
                    stream.settimeout(1)
                    length = int(check._receive(stream, 4), 16)
                    check._receive(stream, length)
                    try:
                        for byte in b'OKAY0006device':
                            time.sleep(0.02)
                            stream.sendall(bytes([byte]))
                    except OSError:
                        pass  # Expected when the deadline closes our fixture peer.
            worker = threading.Thread(target=peer)
            worker.start()
            server = mock.Mock()
            server.process.poll.return_value = None
            started = time.monotonic()
            try:
                with self.assertRaises(check.BoundaryError) as error:
                    check.adb_read(endpoint, 'get-state', server, timeout=0.08)
                elapsed = time.monotonic() - started
                self.assertEqual('adb_timeout', error.exception.code)
                self.assertLess(elapsed, 0.25)
            finally:
                worker.join(2)
            self.assertFalse(worker.is_alive())

    def test_f5_zip_dot_alias_is_rejected_before_any_extraction(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            archive.writestr('pkg/tool.txt', b'first')
            archive.writestr('pkg/./tool.txt', b'second overwrite')
        target = self.base / 'extract'
        with self.assertRaises(check.BoundaryError):
            check.safe_extract(raw.getvalue(), target)
        self.assertFalse(target.exists())


class OwnedRuntimePlanBundleTests(unittest.TestCase):
    """Only authored JSON, genuine builder/Fleet, and fake owned processes/services."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.runtime = self.base / 'rt'
        self.runtime.mkdir()
        context, analysis, plan, options = authored_plan()
        self.bundle = dict(context=context, analysis=analysis, plan_input=plan, **options)
        self.raw = json.dumps(self.bundle, ensure_ascii=False).encode('utf-8')
        self.path = self.base / 'plan.json'
        self.path.write_bytes(self.raw)
        self.index = 0
        resources = mock.patch.object(check, 'resources', return_value={'available_mib': 8192})
        resources.start()
        self.addCleanup(resources.stop)

    def require_api(self):
        self.assertIn('intake_plan_bundle', inspect.signature(check.execute).parameters,
                      'owned runtime plan bundle option is absent')

    def execute(self, **kwargs):
        self.require_api()
        self.index += 1
        options = dict(boot=True, rf_bridge_check=True, intake_plan_bundle=self.path)
        options.update(kwargs)
        return check.execute(self.runtime, self.base / ('o'+str(self.index)), **options)

    def rejected(self, **kwargs):
        events = []
        def forbidden(label):
            def fail(*args, **options):
                events.append(label)
                raise AssertionError(label+' boundary entered')
            return fail
        with ExitStack() as stack:
            for name in ('validate_runtime', 'native', 'claim_attempt', 'OwnedProcess'):
                stack.enter_context(mock.patch.object(check, name, side_effect=forbidden(name)))
            stack.enter_context(mock.patch.object(guest_bridge, '_exchange', side_effect=forbidden('guest')))
            result = self.execute(**kwargs)
        self.assertEqual(events, [])
        self.assertIsNotNone(result['first_failure'])
        self.assertNotEqual(result['first_failure']['code'], 'unexpected_error')
        self.assertEqual(result['android_os'], 'not_run')
        self.assertFalse(result['adb_verified'])
        self.assertFalse((self.runtime / 'boot-attempt.json').exists())
        return result

    @contextmanager
    def fake_boot(self, *, mutate_file=False):
        events, owners, reads = [], [], []
        guest = FakeGuest()
        original_open = Path.open
        original_builder = guest_bridge.build_conducted_twin_plan_input
        help_text = '-no-window -no-audio -no-snapshot -memory -port -grpc -gpu'
        def read_once(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get('mode', 'r')
            if path == self.path and mode == 'rb':
                reads.append(str(path))
            return original_open(path, *args, **kwargs)
        def builder(*args, **kwargs):
            events.append('builder')
            return original_builder(*args, **kwargs)
        def sdk(*args, **kwargs):
            events.append('sdk-fixture')
            if mutate_file:
                self.path.write_bytes(b'changed after the validated read')
            return {'fixture': True}
        def native(*args, **kwargs):
            events.append('native-fixture')
            return help_text
        class Owner:
            def __init__(self, *args, **kwargs):
                self.process = mock.Mock()
                self.process.poll.return_value = None
                self.process.pid = 70000+len(owners)
                self.active = False
                owners.append(self)
            def __enter__(self):
                self.active = True
                events.append('owner-enter')
                return self
            def sample(self):
                pass
            def __exit__(self, *args):
                self.active = False
                events.append('owner-exit')
                return False
        def exchange(endpoint, server, service, deadline):
            self.assertEqual(len(owners), 2)
            self.assertTrue(all(owner.active for owner in owners))
            events.append('guest')
            return guest(endpoint, server, service, deadline)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(Path, 'open', read_once))
            stack.enter_context(mock.patch.object(guest_bridge, 'build_conducted_twin_plan_input', side_effect=builder))
            stack.enter_context(mock.patch.object(check, 'validate_runtime', side_effect=sdk))
            stack.enter_context(mock.patch.object(check, 'native', side_effect=native))
            stack.enter_context(mock.patch.object(check, 'assert_ports_free'))
            stack.enter_context(mock.patch.object(check, 'create_avd', return_value=self.base/'avd'))
            stack.enter_context(mock.patch.object(check, 'OwnedProcess', Owner))
            stack.enter_context(mock.patch.object(check, 'adb_read',
                side_effect=['device', 'device', '1', 'ranchu', 'AOSP fixture', '1']))
            stack.enter_context(mock.patch.object(guest_bridge, '_exchange', side_effect=exchange))
            yield dict(events=events, owners=owners, reads=reads, guest=guest)

    def test_strict_json_encoding_duplicate_nonfinite_and_surrogate_are_pre_sdk(self):
        duplicate = self.raw.replace(b'"expected_revision": 1', b'"expected_revision": 1, "expected_revision": 2', 1)
        nested = self.raw.replace(b'"synthetic": true', b'"synthetic": true, "synthetic": false', 1)
        surrogate = self.raw.replace(b'Authored synthetic snapshot; no execution authority.', b'\\ud800', 1)
        bad = [b'\xff', b'\xef\xbb\xbf'+self.raw, duplicate, nested, surrogate]
        bad += [self.raw.replace(b'"power_dbm": -7', b'"power_dbm": '+token, 1)
                for token in (b'NaN', b'Infinity', b'-Infinity', b'1e9999')]
        for index, raw in enumerate(bad):
            with self.subTest(case=index):
                self.assertNotEqual(raw, self.raw)
                self.path.write_bytes(raw)
                self.rejected()

    def test_exact_shape_types_depth_and_size_are_pre_sdk(self):
        variants = [[], None, {**self.bundle, 'ready': True},
                    {k:v for k,v in self.bundle.items() if k!='analysis'},
                    {**self.bundle, 'context': []}, {**self.bundle, 'analysis': True},
                    {**self.bundle, 'expected_revision': True},
                    {**self.bundle, 'expected_plan_input_sha256': 123}]
        deep = []
        for _ in range(40):
            deep = [deep]
        variants.append({**self.bundle, 'context': deep})
        for index, value in enumerate(variants):
            with self.subTest(case=index):
                self.path.write_text(json.dumps(value), encoding='utf-8')
                self.rejected()
        self.path.write_bytes(b' '*(8*1024*1024+1))
        self.assertEqual(self.rejected()['first_failure']['code'], 'intake_plan_bundle_too_large')

    def test_binding_non_synthetic_information_and_method_are_pre_sdk(self):
        for field in ('context_hash', 'plan_hash', 'synthetic', 'information', 'source', 'method'):
            with self.subTest(field=field):
                value = copy.deepcopy(self.bundle)
                if field == 'context_hash':value['expected_context_sha256'] = '0'*64
                elif field == 'plan_hash':value['expected_plan_input_sha256'] = '0'*64
                elif field == 'synthetic':value['context']['synthetic'] = False
                elif field == 'information':value['analysis']['facts'] = value['analysis']['facts'][:2]
                elif field == 'source':value['plan_input']['plan']['source_settings']['power_dbm'] = 99
                else:value['plan_input']['plan']['method_id'] = 'unsupported'
                if field in ('source', 'method'):
                    value['expected_plan_input_sha256'] = value_sha256(value['plan_input'])
                self.path.write_text(json.dumps(value), encoding='utf-8')
                self.rejected()

    def test_paired_flags_relative_path_and_other_endpoint_are_pre_sdk(self):
        for options in ({'boot': False, 'rf_bridge_check': False}, {'rf_bridge_check': False},
                        {'boot': False}, {'verify_only': True}, {'install': True},
                        {'intake_plan_bundle': Path('relative.json')},
                        {'endpoint': check.Endpoint(15038, 5678, 18554)}):
            with self.subTest(options=options):
                self.rejected(**options)

    def test_valid_file_is_read_once_frozen_before_sdk_and_reaches_same_fleet(self):
        with self.fake_boot(mutate_file=True) as observed:
            result = self.execute()
        self.assertIsNone(result['first_failure'])
        self.assertEqual(result['status'], 'rf_bridge_verified')
        self.assertEqual(len(observed['reads']), 1)
        self.assertLess(observed['events'].index('builder'), observed['events'].index('sdk-fixture'))
        self.assertFalse(any(owner.active for owner in observed['owners']))
        self.assertEqual(result['intake_plan_bundle']['raw_sha256'], hashlib.sha256(self.raw).hexdigest())
        host = result['rf_bridge']['host_rf_model']
        self.assertEqual(host['source_settings']['frequency_hz'], 2412000000)
        self.assertEqual(host['sensor_on_average']['value'], -37.5)
        self.assertEqual(host['analyzer_on_average']['value'], -18.75)
        self.assertEqual(host['source_sha256'], result['intake_plan_bundle']['source_sha256'])
        self.assertEqual(result['rf_bridge']['intake_plan']['plan_input'], self.bundle['plan_input'])
        self.assertIn('2412000000 -7 20000000 0.5 OFDM 4',
                      next(s for s in observed['guest'].calls if ' CONFIG ' in s))
        self.assertEqual(result['intake_plan']['verification']['current_version'], 'caller_snapshot_only')

    def test_reserved_dos_components_never_reach_filesystem_for_str_or_path(self):
        # First five are the independent 6da248a No, kept as literal inputs.
        paths = [r'C:\NUL', r'C:\x\NUL.txt', r'C:\x\CON', r'C:\x\AUX', r'C:\x\COM1',
                 r'C:\x\nUl.JsOn', r'C:\x\NUL .json', r'C:\x\NUL. ', r'C:\x\NUL..json',
                 r'C:\x\PRN.txt', r'C:\x\COM9.backup', r'C:\x\LPT1.json',
                 r'C:\x\COM¹.txt', r'C:\x\LPT².json', r'C:\x\CONIN$.json', r'C:\x\CONOUT$',
                 r'C:\NUL\normal.json', r'C:\aux.txt\normal.json', r'C:\x\CoM1. \normal.json']
        for text in paths:
            for supplied in (text, Path(text)):
                with self.subTest(path=text, kind=type(supplied).__name__):
                    probes = []
                    def forbidden(*args):
                        probes.append('filesystem probe')
                        raise AssertionError('reserved device entered filesystem boundary')
                    with mock.patch.object(check, 'reject_links', side_effect=forbidden):
                        with self.assertRaises(check.BoundaryError) as error:
                            check._read_intake_plan_bundle(supplied)
                    self.assertEqual(error.exception.code, 'intake_plan_bundle_path_invalid')
                    self.assertEqual(probes, [])

    def test_nonreserved_dos_lookalikes_remain_eligible_for_regular_file_read(self):
        paths = [r'C:\x\NULx.json', r'C:\x\xNUL', r'C:\x\CONsole.json', r'C:\x\AUXiliary.json',
                 r'C:\x\COM0.json', r'C:\x\COM10.json', r'C:\x\LPT0.json', r'C:\x\LPT10.json',
                 r'C:\x\.NUL', r'C:\NULx\normal.json']
        class EligibleForProbe(Exception):
            pass
        for text in paths:
            for supplied in (text, Path(text)):
                with self.subTest(path=text, kind=type(supplied).__name__):
                    with mock.patch.object(check, 'reject_links', side_effect=EligibleForProbe):
                        with self.assertRaises(EligibleForProbe):
                            check._read_intake_plan_bundle(supplied)

    def test_remote_device_and_ads_paths_are_rejected_without_filesystem_probe(self):
        original = check.reject_links
        probes = []
        def local_only(path):
            if (str(path).startswith('\\\\') or ':' in path.name or '\x00' in str(path)
                    or any(0xD800 <= ord(char) <= 0xDFFF for char in str(path))):
                probes.append(str(path))
                raise AssertionError('nonlocal/special path probe forbidden')
            return original(path)
        paths = [Path('\\\\remote.invalid\\share\\plan.json'), Path('\\\\.\\pipe\\plan'),
                 Path(str(self.path)+':stream'), Path(str(self.path)+'\x00'), Path(str(self.path)+'\ud800')]
        with mock.patch.object(check, 'reject_links', side_effect=local_only):
            for path in paths:
                with self.subTest(path=path):
                    self.assertEqual(self.rejected(intake_plan_bundle=path)['first_failure']['code'],
                                     'intake_plan_bundle_path_invalid')
        self.assertEqual(probes, [])

    def test_exact_raw_limit_accepts_valid_whitespace_without_new_plan_read(self):
        self.path.write_bytes(self.raw+b' '*(8*1024*1024-len(self.raw)))
        with self.fake_boot() as observed:
            result = self.execute()
        self.assertIsNone(result['first_failure'])
        self.assertEqual(result['intake_plan_bundle']['bytes'], 8*1024*1024)
        self.assertEqual(len(observed['reads']), 1)

    def test_existing_claim_is_never_reset_or_replaced(self):
        claim = self.runtime/'boot-attempt.json'
        original = b'{"fixture":"already consumed"}\n'
        claim.write_bytes(original)
        with self.fake_boot() as observed:
            result = self.execute()
        self.assertEqual(result['first_failure']['code'], 'boot_attempt_already_used')
        self.assertEqual(claim.read_bytes(), original)
        self.assertEqual(observed['owners'], [])
        self.assertEqual(observed['guest'].calls, [])

    def test_cli_selects_plan_and_flag_absence_keeps_original_fixed_source(self):
        self.assertIn('--intake-plan-bundle', check.parser()._option_string_actions,
                      'CLI intake plan bundle flag is absent')
        with self.fake_boot() as observed, mock.patch('sys.stdout', new=io.StringIO()):
            code = check.main(['--runtime', str(self.runtime), '--output', str(self.base/'cli'),
                               '--boot', '--rf-bridge-check', '--intake-plan-bundle', str(self.path)])
        self.assertEqual(code, 0)
        self.assertEqual(len(observed['reads']), 1)
        self.runtime = self.base/'rt-default'
        self.runtime.mkdir()
        with self.fake_boot() as observed:
            result = self.execute(intake_plan_bundle=None)
        self.assertIsNone(result['first_failure'])
        self.assertNotIn('intake_plan_bundle', result)
        self.assertEqual(result['rf_bridge']['host_rf_model']['source_settings'], guest_bridge.SOURCE_SETTINGS)
        self.assertNotIn('intake_plan', result['rf_bridge'])
        self.assertEqual(observed['reads'], [])

    def test_direct_boot_invalid_snapshot_is_rejected_before_claim_or_process(self):
        self.assertIn('intake_plan_snapshot', inspect.signature(check.boot_runtime).parameters,
                      'immutable plan snapshot hook is absent')
        report = check.Report(self.base/'direct')
        with (mock.patch.object(check, 'claim_attempt', side_effect=AssertionError('claim')),
              mock.patch.object(check, 'OwnedProcess', side_effect=AssertionError('process'))):
            with self.assertRaises(check.BoundaryError):
                check.boot_runtime(self.runtime, report, {}, check.Endpoint(), 1, 'auto', '',
                                   rf_bridge_check=True, intake_plan_snapshot=b'{"ready":true}')


if __name__ == '__main__':
    unittest.main()
