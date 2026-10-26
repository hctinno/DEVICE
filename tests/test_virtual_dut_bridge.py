"""Genuine in-memory RF execution; ADB subprocess boundary uses test doubles only."""
from decimal import Decimal
import importlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
import threading
import time
from unittest.mock import patch

from labflow.virtual_lab import VirtualLab


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_dut_bridge'),
                             'virtual DUT bridge API is missing')
        self.api = importlib.import_module('labflow.virtual_dut_bridge')
        self.lab = VirtualLab()
        self.bridge = self.api.VirtualDUTBridge(self.lab)

    def ready(self):
        self.bridge.configure('g', 6, 10)
        self.bridge.set_path(True, 3)
        self.bridge.start()

    def test_same_lab_power_and_path_changes_reach_meter_and_correction(self):
        self.ready()
        first = self.bridge.measure(correction_loss_db=3)
        self.assertEqual(first['status'], 'completed')
        self.assertEqual(Decimal(str(first['raw_dbm'])), Decimal('7'))
        self.assertEqual(Decimal(str(first['corrected_dbm'])), Decimal('10'))
        self.bridge.configure('n', 11, 16)
        second = self.bridge.measure(correction_loss_db=3)
        self.assertEqual(second['raw_dbm'], 13)
        # The caller's actual same instance, not an isolated bridge-owned twin.
        self.lab.set_path(True, 6)
        third = self.bridge.measure(correction_loss_db=6)
        self.assertEqual(third['raw_dbm'], 10)
        self.assertEqual(third['raw_dbm'] - second['raw_dbm'], -3)
        self.assertEqual(third['corrected_dbm'], second['corrected_dbm'])
        self.assertGreater(third['meter_receipt']['measurement']['measurement_id'],
                           second['meter_receipt']['measurement']['measurement_id'])
        self.assertTrue(third['synthetic'])
        self.assertFalse(third['hardware_verified'])
        self.assertEqual(third['rf_source'], 'existing_virtual_lab')
        self.assertEqual(third['anyway_oem_support'], 'not_assessed')

    def test_all_bgn_modes_use_existing_model(self):
        for mode in ('b', 'g', 'n'):
            with self.subTest(mode=mode):
                self.bridge.configure(mode, 1, 0)
                self.bridge.set_path(True, 0)
                self.bridge.start()
                self.assertEqual(self.bridge.measure(correction_loss_db=0)['raw_dbm'], 0)

    def test_synthetic_path_never_opens_process_or_network(self):
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden')), \
             patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            self.ready()
            self.assertEqual(self.bridge.measure(correction_loss_db=3)['corrected_dbm'], 10)
            self.bridge.stop()

    def test_start_before_configure_and_invalid_settings_fail_without_mutation(self):
        with self.assertRaises(ValueError):
            self.bridge.start()
        self.ready()
        for args in [('ac', 6, 10), ('g', True, 10), ('g', 12, 10),
                     ('g', 6, True), ('g', 6, float('nan')), ('g', 6, 31)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.bridge.configure(*args)
        for args in [(1, 3), (True, -1), (True, float('inf'))]:
            with self.assertRaises(ValueError):
                self.bridge.set_path(*args)
        self.assertEqual(self.bridge.measure(correction_loss_db=3)['raw_dbm'], 7)

    def test_stop_and_route_loss_do_not_publish_corrected_floor(self):
        self.ready()
        self.bridge.measure(correction_loss_db=3)
        self.bridge.stop()
        stopped = self.bridge.measure(correction_loss_db=3)
        self.assertEqual(stopped['status'], 'invalid')
        self.assertEqual(stopped['code'], 'synthetic_signal_below_gate')
        self.assertEqual(stopped['raw_dbm'], -100)
        self.assertIsNone(stopped['corrected_dbm'])
        self.bridge.start()
        self.bridge.set_path(False, 3)
        lost = self.bridge.measure(correction_loss_db=3)
        self.assertEqual(lost['status'], 'invalid')
        self.assertEqual(lost['raw_dbm'], -100)
        self.assertIsNone(lost['corrected_dbm'])

    def test_stale_change_during_acquisition_propagates_adapter_failure(self):
        self.ready()

        def change_on_fetch():
            if self.lab.meter('*OPC?')['response'] == '1':
                # During preflight FETC is no_data; only change after completion.
                if self.lab.meter('FETC1?')['status'] == 'ok':
                    self.lab.set_path(True, 6)
            return True

        result = self.bridge.measure(correction_loss_db=3, can_continue=change_on_fetch)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['code'], 'meter_invalid')
        self.assertIsNone(result['raw_dbm'])
        self.assertIsNone(result['corrected_dbm'])
        self.assertTrue(any(row['reply'] and row['reply']['status'] == 'invalid'
                            for row in result['meter_receipt']['transcript']))

    def test_timeout_and_meter_disconnect_are_not_success(self):
        self.ready()
        self.lab.inject_fault('measurement_stuck', True)
        result = self.bridge.measure(correction_loss_db=3, timeout_ticks=1)
        self.assertEqual(result['status'], 'timeout')
        self.assertIsNone(result['corrected_dbm'])
        self.lab.inject_fault('measurement_stuck', False)
        self.lab.inject_fault('meter_disconnected', True)
        result = self.bridge.measure(correction_loss_db=3)
        self.assertEqual(result['code'], 'meter_disconnected')
        self.assertIsNone(result['raw_dbm'])

    def test_post_fetch_change_cannot_publish_a_stale_completed_receipt(self):
        self.ready()
        fetched = False
        real_meter = self.lab.meter

        def observe_fetch(command):
            nonlocal fetched
            reply = real_meter(command)
            if command == 'FETC1?' and reply['status'] == 'ok':
                fetched = True
            return reply

        def stop_after_fetch():
            if fetched:
                self.lab.stop_tx()
            return True

        with patch.object(self.lab, 'meter', side_effect=observe_fetch):
            result = self.bridge.measure(correction_loss_db=3, can_continue=stop_after_fetch)
        self.assertEqual(result['meter_receipt']['status'], 'completed')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['code'], 'meter_invalid')
        self.assertIsNone(result['raw_dbm'])
        self.assertIsNone(result['corrected_dbm'])

    def test_bad_correction_rejected_before_acquisition(self):
        self.ready()
        for value in (True, None, '3', -1, 121, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.bridge.measure(correction_loss_db=value)
        self.assertEqual(self.lab.meter('FETC1?')['status'], 'no_data')

    def test_wrong_lab_rejected_without_io(self):
        for value in (None, object(), 'TCPIP::example'):
            with self.assertRaises(ValueError):
                self.api.VirtualDUTBridge(value)


class FakeStream(io.BytesIO):
    """Old identity doubles expose a fake descriptor to a mocked OS read boundary."""
    streams = {}

    def __init__(self, output):
        super().__init__(output)
        self.descriptor = id(self)
        self.streams[self.descriptor] = self

    def fileno(self):
        return self.descriptor

    def close(self):
        self.streams.pop(self.descriptor, None)
        super().close()


class FakeProcess:
    """Only the native subprocess boundary is replaced, never the RF model."""
    def __init__(self, output=b'', *, returncode=0, timeout=False):
        self.stdout = FakeStream(output)
        self.returncode = returncode
        self.timeout = timeout
        self.killed = False

    def wait(self, timeout=None):
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired('fake-adb', timeout)
        return self.returncode

    def kill(self):
        self.killed = True


class ADBIdentityTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_dut_bridge'),
                             'emulator-only identity transport is missing')
        self.api = importlib.import_module('labflow.virtual_dut_bridge')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.adb = Path(self.temp.name) / 'adb.exe'
        self.adb.write_bytes(b'test placeholder: never executable')
        # These are still byte-level identity doubles, not native lifecycle proof.
        block = patch.object(self.api.os, 'set_blocking')
        read = patch.object(self.api.os, 'read',
                            side_effect=lambda fd, count: FakeStream.streams[fd].read(count))
        block.start()
        read.start()
        self.addCleanup(FakeStream.streams.clear)
        self.addCleanup(block.stop)
        self.addCleanup(read.stop)

    def transport(self, **kwargs):
        return self.api.EmulatorADBIdentity(adb_executable=str(self.adb),
                                            emulator_serial='emulator-5554', **kwargs)

    def test_default_opt_out_and_serial_executable_gates_run_zero_commands(self):
        with patch.object(subprocess, 'Popen') as native:
            with self.assertRaisesRegex(ValueError, 'opt_in_required'):
                self.transport()
            for serial in ('R12345', '192.0.2.1:5555', '', 'emulator-5555',
                           'emulator-5554 -s R12345', 'emulator-5554\n', None):
                with self.subTest(serial=serial), self.assertRaises(ValueError):
                    self.api.EmulatorADBIdentity(adb_executable=str(self.adb),
                                                emulator_serial=serial, enabled=True)
            for executable in ('adb', 'missing/adb.exe', str(self.adb.parent),
                               '\\\\server\\share\\adb.exe'):
                with self.subTest(executable=executable), self.assertRaises(ValueError):
                    self.api.EmulatorADBIdentity(adb_executable=executable,
                                                emulator_serial='emulator-5554', enabled=True)
            native.assert_not_called()

    def test_exact_readonly_argv_and_identity_provenance(self):
        processes = [FakeProcess(x) for x in (b'1\r\n', b'ranchu\n', b'device\n', b'sdk_gphone64_x86_64\n')]
        with patch.object(subprocess, 'Popen', side_effect=processes) as native:
            result = self.transport(enabled=True).read_identity()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['model'], 'sdk_gphone64_x86_64')
        self.assertTrue(result['emulator_identity_confirmed'])
        self.assertFalse(result['rf_control_performed'])
        self.assertFalse(result['hardware_verified'])
        self.assertEqual(result['anyway_oem_support'], 'not_assessed')
        prefix = [str(self.adb), '-s', 'emulator-5554']
        self.assertEqual([call.args[0] for call in native.call_args_list], [
            prefix + ['shell', 'getprop', 'ro.kernel.qemu'],
            prefix + ['shell', 'getprop', 'ro.hardware'],
            prefix + ['get-state'],
            prefix + ['shell', 'getprop', 'ro.product.model'],
        ])
        for call in native.call_args_list:
            self.assertIs(call.kwargs['shell'], False)
            self.assertEqual(call.kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(call.kwargs['env']['ADB_SERVER_SOCKET'], 'tcp:127.0.0.1:5037')

    def test_unknown_qemu_or_hardware_fails_closed_before_model(self):
        for outputs, count in [([b'0\n'], 1), ([b'yes\n'], 1), ([b'1\n', b'physical_chip\n'], 2)]:
            with self.subTest(outputs=outputs), \
                 patch.object(subprocess, 'Popen', side_effect=[FakeProcess(x) for x in outputs]) as native:
                result = self.transport(enabled=True).read_identity()
            self.assertEqual(result['status'], 'failed')
            self.assertFalse(result['emulator_identity_confirmed'])
            self.assertIsNone(result['model'])
            self.assertEqual(native.call_count, count)

    def test_offline_and_multiple_line_responses_are_not_identity(self):
        for output in (b'offline\n', b'device\nextra\n', b'', b'\xff'):
            with self.subTest(output=output), patch.object(subprocess, 'Popen', side_effect=[
                FakeProcess(b'1\n'), FakeProcess(b'goldfish\n'), FakeProcess(output),
            ]):
                result = self.transport(enabled=True).read_identity()
            self.assertEqual(result['status'], 'failed')
            self.assertIsNone(result['model'])

    def test_timeout_kills_and_reaps_without_followup(self):
        process = FakeProcess(timeout=True)
        with patch.object(subprocess, 'Popen', return_value=process) as native:
            result = self.transport(enabled=True, timeout_seconds=0.1).read_identity()
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(result['code'], 'adb_timeout')
        self.assertTrue(process.killed)
        self.assertEqual(native.call_count, 1)

    def test_response_limit_kills_and_never_parses_partial_identity(self):
        process = FakeProcess(b'1' * 5000)
        with patch.object(subprocess, 'Popen', return_value=process) as native:
            result = self.transport(enabled=True).read_identity()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['code'], 'adb_response_limit')
        self.assertTrue(process.killed)
        self.assertEqual(native.call_count, 1)
        self.assertLessEqual(len(result['transcript'][0]['response']), 4096)

    def test_spawn_and_exit_failures_are_reported_not_success(self):
        with patch.object(subprocess, 'Popen', side_effect=OSError('not runnable')):
            self.assertEqual(self.transport(enabled=True).read_identity()['code'], 'adb_spawn_failed')
        with patch.object(subprocess, 'Popen', return_value=FakeProcess(b'device\n', returncode=1)):
            self.assertEqual(self.transport(enabled=True).read_identity()['code'], 'adb_nonzero_exit')

    def test_timeout_and_optin_are_strict(self):
        with patch.object(subprocess, 'Popen') as native:
            for enabled in (1, 'true', None):
                with self.assertRaises(ValueError):
                    self.transport(enabled=enabled)
            for timeout in (True, 0, -1, 31, float('inf'), float('nan')):
                with self.assertRaises(ValueError):
                    self.transport(enabled=True, timeout_seconds=timeout)
            native.assert_not_called()

    def test_subprocess_boundary_rejects_commands_outside_fixed_whitelist(self):
        transport = self.transport(enabled=True)
        forbidden = [('devices',), ('connect', '127.0.0.1:5555'), ('tcpip', '5555'),
                     ('forward', 'tcp:1', 'tcp:2'), ('install', 'x.apk'),
                     ('shell', 'setprop', 'x', '1'), ('shell', 'getprop'),
                     ('shell', 'getprop', 'ro.kernel.qemu; id'),
                     ('shell', 'getprop', 'ro.serialno')]
        with patch.object(subprocess, 'Popen', side_effect=OSError('forbidden dispatch')) as native:
            for command in forbidden:
                with self.subTest(command=command), self.assertRaisesRegex(ValueError, 'invalid_adb_command'):
                    transport._read(command)
            native.assert_not_called()


_STANDARD_POPEN = subprocess.Popen
CLEANUP_OBSERVATIONS = []


class ADBCleanupTests(unittest.TestCase):
    """Owned standard Python children/pipes only, never a real adb executable."""
    def setUp(self):
        self.api = importlib.import_module('labflow.virtual_dut_bridge')
        self.temp = tempfile.TemporaryDirectory(prefix='bridge-cleanup-')
        self.addCleanup(self.temp.cleanup)
        self.adb = Path(self.temp.name) / 'adb.exe'
        self.adb.write_bytes(b'placeholder only; never executed')
        self.children = []
        self.writers = []
        self.initial_threads = set(threading.enumerate())
        self.addCleanup(self.observer_cleanup)

    def transport(self, timeout=0.5):
        return self.api.EmulatorADBIdentity(adb_executable=str(self.adb),
            emulator_serial='emulator-5554', enabled=True, timeout_seconds=timeout)

    def spawn(self, script, *, held_writer=False, wait_error=None, close_error=None,
              cleanup_wait_error=None):
        output = subprocess.PIPE
        if held_writer:
            read_fd, write_fd = os.pipe()
            self.writers.append(write_fd)
            output = write_fd
        child = _STANDARD_POPEN([sys.executable, '-X', 'utf8', '-c', script],
            stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
            bufsize=0, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if held_writer:
            child.stdout = os.fdopen(read_fd, 'rb', buffering=0)
        record = dict(child=child, wait=child.wait, kill=child.kill,
                      original_stream=child.stdout, read_fd=child.stdout.fileno(),
                      wait_calls=0, kill_calls=0)
        self.children.append(record)

        def wait(timeout=None):
            record['wait_calls'] += 1
            if wait_error is not None and record['wait_calls'] == 1:
                raise wait_error
            if cleanup_wait_error is not None and record['wait_calls'] == 2:
                record['wait'](timeout=timeout)
                raise cleanup_wait_error
            return record['wait'](timeout=timeout)

        def kill():
            record['kill_calls'] += 1
            return record['kill']()

        child.wait, child.kill = wait, kill
        if close_error is not None:
            stream = child.stdout
            class CloseErrorStream:
                @property
                def closed(self):
                    return stream.closed
                def fileno(self):
                    return stream.fileno()
                def close(self):
                    stream.close()
                    raise close_error
            child.stdout = CloseErrorStream()
        return child

    def observe(self, label):
        rows = []
        for record in self.children:
            try:
                os.fstat(record['read_fd'])
                fd_closed = False
            except OSError:
                fd_closed = True
            rows.append(dict(pid=record['child'].pid, alive=record['child'].poll() is None,
                returncode=record['child'].returncode, stdout_closed=record['original_stream'].closed,
                read_fd_closed=fd_closed, product_wait_calls=record['wait_calls'],
                product_kill_calls=record['kill_calls']))
        threads = [thread for thread in threading.enumerate()
                   if thread not in self.initial_threads and thread.is_alive()]
        value = dict(case=self._testMethodName, label=label, children=rows,
                     reader_threads_alive=len(threads))
        CLEANUP_OBSERVATIONS.append(value)
        return value

    def observer_cleanup(self):
        # Deliberately after product observations; this is never product success.
        for writer in self.writers:
            os.close(writer)
        self.writers.clear()
        for record in self.children:
            if record['child'].poll() is None:
                record['kill']()
            record['wait'](timeout=2)
        for thread in threading.enumerate():
            if thread not in self.initial_threads:
                thread.join(timeout=2)
        for record in self.children:
            record['original_stream'].close()
        state = self.observe('after_observer_cleanup')
        self.assertEqual(state['reader_threads_alive'], 0)
        self.assertTrue(all(not row['alive'] and row['stdout_closed'] for row in state['children']))

    def assert_product_clean(self, state):
        self.assertEqual(state['reader_threads_alive'], 0)
        self.assertTrue(all(not row['alive'] and row['stdout_closed'] and row['read_fd_closed']
                            for row in state['children']))

    def test_wait_control_keeps_identity_after_product_child_pipe_reader_cleanup(self):
        first = KeyboardInterrupt('owned standard child wait control')
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import time; time.sleep(30)', wait_error=first)):
            with self.assertRaises(KeyboardInterrupt) as caught:
                self.transport().read_identity()
        self.assertIs(caught.exception, first)
        state = self.observe('at_control_propagation')
        self.assert_product_clean(state)

    def test_held_external_writer_does_not_leave_product_reader_or_stream(self):
        started = time.monotonic()
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('print("device", flush=True)', held_writer=True)):
            result = self.transport().read_identity()
        elapsed = time.monotonic() - started
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['code'], 'adb_response_unreadable')
        self.assertLess(elapsed, 3)
        os.fstat(self.writers[0])  # Product owns only its read-end, not this writer.
        state = self.observe('at_api_return_external_writer_still_open')
        self.assert_product_clean(state)

    def test_success_eof_reaps_child_and_closes_native_read_fd(self):
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('print("device", flush=True)')):
            result = self.transport()._read(('get-state',))
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['response'], 'device' + os.linesep)
        self.assertEqual(result['cleanup']['status'], 'completed')
        self.assert_product_clean(self.observe('at_success_return'))

    def test_combined_real_stdout_stderr_cap_kills_reaps_and_closes(self):
        script = 'import os,time; os.write(1,b"A"*3000); os.write(2,b"B"*3000); time.sleep(30)'
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k: self.spawn(script)):
            result = self.transport()._read(('get-state',))
        self.assertEqual(result['code'], 'adb_response_limit')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['response']), 4096)
        self.assertEqual(result['response'].count('A'), 3000)
        self.assertEqual(result['response'].count('B'), 1096)
        self.assert_product_clean(self.observe('at_cap_return'))

    def test_real_timeout_closes_resources_and_preserves_first_failure_over_close_error(self):
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import time; time.sleep(30)', close_error=OSError('after native close'))):
            result = self.transport(timeout=0.1)._read(('get-state',))
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(result['code'], 'adb_timeout')
        self.assertEqual(result['cleanup']['status'], 'completed_with_errors')
        self.assertEqual(result['cleanup']['errors'], [{'operation': 'close', 'type': 'OSError'}])
        self.assert_product_clean(self.observe('at_timeout_return'))

    def test_spawn_failure_and_original_ordinary_wait_error_are_distinct(self):
        with patch.object(subprocess, 'Popen', side_effect=OSError('provided spawn failure')):
            result = self.transport()._read(('get-state',))
        self.assertEqual(result['code'], 'adb_spawn_failed')
        self.assertEqual(result['cleanup']['status'], 'not_started')
        first = OSError('provided original wait error')
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import time; time.sleep(30)', wait_error=first)):
            with self.assertRaises(OSError) as caught:
                self.transport()._read(('get-state',))
        self.assertIs(caught.exception, first)
        self.assert_product_clean(self.observe('at_ordinary_wait_error'))

    def test_first_control_survives_cleanup_wait_and_close_errors(self):
        first = KeyboardInterrupt('first wait control')
        second = MemoryError('after native cleanup wait')
        third = OSError('after native close')
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import time; time.sleep(30)', wait_error=first,
                                     cleanup_wait_error=second, close_error=third)):
            with self.assertRaises(KeyboardInterrupt) as caught:
                self.transport()._read(('get-state',))
        self.assertIs(caught.exception, first)
        self.assertEqual(first.virtual_dut_cleanup['status'], 'completed_with_errors')
        self.assertIs(first.virtual_dut_cleanup_errors[0], second)
        self.assertIs(first.virtual_dut_cleanup_errors[1], third)
        self.assert_product_clean(self.observe('at_original_control_with_secondary_errors'))

    def test_other_standard_controls_keep_identity_after_native_cleanup(self):
        for first in (SystemExit(17), GeneratorExit('first'), MemoryError('first')):
            with self.subTest(control=type(first).__name__):
                with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                                  self.spawn('import time; time.sleep(30)', wait_error=first)):
                    with self.assertRaises(type(first)) as caught:
                        self.transport()._read(('get-state',))
                self.assertIs(caught.exception, first)
                self.assertEqual(first.virtual_dut_cleanup['status'], 'completed')
                self.assert_product_clean(self.observe('at_' + type(first).__name__))

    def test_real_nonzero_exit_is_not_identity_and_is_reaped(self):
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import sys; print("device", flush=True); sys.exit(7)')):
            result = self.transport()._read(('get-state',))
        self.assertEqual(result['code'], 'adb_nonzero_exit')
        self.assertEqual(result['returncode'], 7)
        self.assert_product_clean(self.observe('at_nonzero_exit_return'))

    def test_public_identity_closes_each_owned_standard_child_before_next_query(self):
        observed_prior = []
        outputs = iter(('1', 'ranchu', 'device', 'owned-standard-python-fixture'))

        def spawn_next(*args, **kwargs):
            # Before every subsequent spawn, earlier product-owned resources ended.
            if self.children:
                observed_prior.append(self.observe('before_next_public_query'))
            value = next(outputs)
            return self.spawn('print(' + repr(value) + ', flush=True)')

        with patch.object(subprocess, 'Popen', side_effect=spawn_next):
            result = self.transport().read_identity()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(result['transcript']), 4)
        self.assertTrue(all(row['cleanup']['status'] == 'completed' for row in result['transcript']))
        for state in observed_prior:
            self.assert_product_clean(state)
        self.assert_product_clean(self.observe('at_public_identity_return'))

    def test_control_immediately_after_spawn_is_inside_cleanup_boundary(self):
        first = KeyboardInterrupt('before collector clock initialization')
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import time; time.sleep(30)')), \
                patch.object(self.api.time, 'monotonic', side_effect=first):
            with self.assertRaises(KeyboardInterrupt) as caught:
                self.transport()._read(('get-state',))
        self.assertIs(caught.exception, first)
        self.assert_product_clean(self.observe('at_immediate_post_spawn_control'))

    def test_nonzero_exit_response_survives_secondary_close_error(self):
        script = 'import os,sys; os.write(1,b"device\\n"); sys.exit(7)'
        for close_error in (None, OSError('secondary after native close')):
            with self.subTest(close_error=type(close_error).__name__):
                result = caught = None
                with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                                  self.spawn(script, close_error=close_error)):
                    try:
                        result = self.transport()._read(('get-state',))
                    except OSError as error:
                        caught = error
                state = self.observe('at_exit7_close_' + type(close_error).__name__)
                state.update(row_returned=result is not None, close_error_raised=caught is close_error and caught is not None)
                self.assert_product_clean(state)
                self.assertIsNone(caught, 'Observed exit7 must retain its row before secondary cleanup errors')
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['code'], 'adb_nonzero_exit')
                self.assertEqual(result['returncode'], 7)
                self.assertEqual(result['response'], 'device\n')
                self.assertEqual(result['cleanup']['errors'], [] if close_error is None else
                                 [{'operation': 'close', 'type': 'OSError'}])

    def test_successful_exit_still_propagates_its_first_cleanup_error(self):
        first = OSError('first failure is after successful native close')
        with patch.object(subprocess, 'Popen', side_effect=lambda *a, **k:
                          self.spawn('import os; os.write(1,b"device\\n")', close_error=first)):
            with self.assertRaises(OSError) as caught:
                self.transport()._read(('get-state',))
        self.assertIs(caught.exception, first)
        self.assertEqual(first.virtual_dut_cleanup['status'], 'completed_with_errors')
        self.assert_product_clean(self.observe('at_exit0_first_cleanup_error'))


if __name__ == '__main__':
    unittest.main()
