"""Synthetic RF bridge and a separate opt-in, read-only emulator identity path.

Android identity never configures RF. No AnyWay/OEM protocol is implemented.
The default RF bridge cannot launch a process or open a network connection.
"""
import math
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from labflow.n1914a_virtual_adapter import N1914AVirtualAdapter
from labflow.virtual_lab import VirtualLab


_READ_COMMANDS = (('shell', 'getprop', 'ro.kernel.qemu'),
                  ('shell', 'getprop', 'ro.hardware'), ('get-state',),
                  ('shell', 'getprop', 'ro.product.model'))


def _provenance():
    return {'hardware_verified': False, 'rf_control_performed': False,
            'anyway_oem_support': 'not_assessed'}


def _bounded_number(value, minimum, maximum, code):
    if (type(value) not in (int, float) or not minimum <= value <= maximum
            or not math.isfinite(value)):
        raise ValueError(code)
    return float(value)


class VirtualDUTBridge:
    """Borrow one exact VirtualLab; reuse its public controls and meter adapter.

    No DUT/path state is mirrored. Explicit correction is caller-supplied and is
    not evidence of calibration. Samples <= -90 dBm fail a synthetic signal gate:
    VirtualLab's -100 dBm floor plus its maximum possible +10 dB noise. This is
    a conservative demonstration policy, not an RF presence or conformity test.
    """
    def __init__(self, lab):
        if type(lab) is not VirtualLab:
            raise ValueError('virtual_lab_required')
        self._lab = lab
        self._meter = N1914AVirtualAdapter(lab)

    def configure(self, mode, channel, power_dbm):
        return {**self._lab.configure_dut(mode, channel, power_dbm), **_provenance(),
                'rf_source': 'existing_virtual_lab'}

    def set_path(self, connected, loss_db):
        return {**self._lab.set_path(connected, loss_db), **_provenance(),
                'rf_source': 'existing_virtual_lab'}

    def start(self):
        return {**self._lab.start_tx(), **_provenance(), 'rf_source': 'existing_virtual_lab'}

    def stop(self):
        return {**self._lab.stop_tx(), **_provenance(), 'rf_source': 'existing_virtual_lab'}

    def measure(self, *, correction_loss_db, timeout_ticks=20, can_continue=None):
        """Take a fresh DBM acquisition; preserve the full adapter failure receipt.

        Each call uses a new adapter request identity, preventing stale receipt
        replay. Existing adapter limits apply (128 attempts per bridge instance).
        The caller owns exclusive sequential access to the borrowed VirtualLab.
        """
        correction = _bounded_number(correction_loss_db, 0, 120, 'invalid_correction_loss_db')
        receipt = self._meter.measure('bridge-' + uuid.uuid4().hex, unit='DBM',
                                      timeout_ticks=timeout_ticks, can_continue=can_continue)
        status, code = receipt['status'], receipt['code']
        raw = corrected = None
        current = None
        if status == 'completed':
            # The adapter receipt is historical. Re-observe through the public
            # API in case a continuation changed setup after the adapter fetch.
            current = self._lab.meter('FETC1?')
            if current['status'] != 'ok':
                status, code = 'failed', 'meter_' + current['status']
            elif current['measurement'] != receipt['measurement']:
                status, code = 'failed', 'meter_observation_changed'
            else:
                raw = receipt['measurement']['value']
                if raw <= -90:
                    status, code = 'invalid', 'synthetic_signal_below_gate'
                else:
                    corrected = raw + correction
        return {'schema_version': 1, 'status': status, 'code': code,
                'synthetic': True, 'rf_source': 'existing_virtual_lab',
                **_provenance(), 'raw_dbm': raw, 'corrected_dbm': corrected,
                'correction_loss_db': correction, 'correction_basis': 'explicit_caller_input',
                'meter_receipt': receipt, 'current_observation': current}


class EmulatorADBIdentity:
    """Opt-in native ADB identity probe for a conventional local emulator serial.

    Construction performs filesystem validation only. read_identity() executes
    four fixed read-only commands, stopping on the first unknown/error response.
    QEMU and hardware markers must match before querying state/model. These are
    identity observations, not cryptographic authentication or RF-mode support.
    Only a trusted native adb binary and a prepared local ADB server are suitable.
    """
    _RESPONSE_LIMIT = 4096
    _EXIT_DRAIN_SECONDS = 1.0
    _CLEANUP_WAIT_SECONDS = 1.0

    def __init__(self, *, adb_executable, emulator_serial, enabled=False, timeout_seconds=5):
        if enabled is not True:
            raise ValueError('opt_in_required')
        if (type(emulator_serial) is not str
                or re.fullmatch(r'emulator-[0-9]{4}', emulator_serial) is None):
            raise ValueError('emulator_serial_required')
        port = int(emulator_serial.removeprefix('emulator-'))
        if port % 2 or not 5554 <= port <= 5682:
            raise ValueError('emulator_serial_required')
        if (type(adb_executable) is not str or not adb_executable
                or adb_executable.startswith(('\\\\', '//'))):
            raise ValueError('explicit_local_adb_executable_required')
        executable = Path(adb_executable)
        if (not executable.is_absolute() or not executable.is_file()
                or executable.name.lower() not in ('adb', 'adb.exe')):
            raise ValueError('explicit_local_adb_executable_required')
        resolved = executable.resolve()
        if str(resolved).startswith(('\\\\', '//')):
            raise ValueError('explicit_local_adb_executable_required')
        self._executable = str(resolved)
        self._serial = emulator_serial
        self._timeout = _bounded_number(timeout_seconds, 0.05, 30, 'invalid_timeout_seconds')

    def _read(self, command):
        if type(command) is not tuple or command not in _READ_COMMANDS:
            raise ValueError('invalid_adb_command')
        # Never inherit alternate ADB server/device-selection variables or PATH.
        env = {key: value for key, value in os.environ.items()
               if key.upper() in {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE',
                                  'HOMEDRIVE', 'HOMEPATH', 'LOCALAPPDATA'}}
        env['ADB_SERVER_SOCKET'] = 'tcp:127.0.0.1:5037'
        argv = [self._executable, '-s', self._serial, *command]
        cleanup = {'status': 'not_started', 'child_reaped': None, 'stdout_closed': None,
                   'reader': 'not_created', 'errors': []}
        row = {'argv': argv, 'status': 'failed', 'code': None, 'response': '',
               'returncode': None, 'cleanup': cleanup}
        output = bytearray()
        primary = None
        secondary = []
        reaped = eof = False
        process = stream = None
        exit_drain_deadline = None

        def cleanup_error(operation, error):
            cleanup['errors'].append({'operation': operation, 'type': type(error).__name__})
            secondary.append(error)

        try:
            try:
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, shell=False, env=env, bufsize=0,
                                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except OSError:
                row['code'] = 'adb_spawn_failed'
                return row
            stream = process.stdout
            deadline = time.monotonic() + self._timeout
            try:
                descriptor = stream.fileno()
                os.set_blocking(descriptor, False)
            except (OSError, ValueError):
                row['code'] = 'adb_response_unreadable'
            while row['code'] is None:
                try:
                    while not eof:
                        try:
                            chunk = os.read(descriptor, min(256, self._RESPONSE_LIMIT + 1 - len(output)))
                        except BlockingIOError:
                            break
                        if not chunk:
                            eof = True
                            break
                        output.extend(chunk)
                        if len(output) > self._RESPONSE_LIMIT:
                            row['code'] = 'adb_response_limit'
                            break
                except OSError:
                    row['code'] = 'adb_response_unreadable'
                if row['code'] is not None:
                    break
                if not reaped:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        row['status'], row['code'] = 'timeout', 'adb_timeout'
                        break
                    try:
                        row['returncode'] = process.wait(timeout=min(0.05, remaining))
                    except subprocess.TimeoutExpired:
                        continue
                    reaped = True
                    exit_drain_deadline = time.monotonic() + self._EXIT_DRAIN_SECONDS
                if eof:
                    break
                remaining = exit_drain_deadline - time.monotonic()
                if remaining <= 0:
                    row['code'] = 'adb_response_unreadable'
                    break
                time.sleep(min(0.01, remaining))
        except BaseException as error:
            primary = error
        finally:
            # No blocking reader exists. Retry only this owned child's kill/wait
            # after cleanup exceptions; every wait has its own finite deadline.
            if process is not None:
                stream = process.stdout if stream is None else stream
                for _ in range(2):
                    if reaped:
                        break
                    try:
                        process.kill()
                    except BaseException as error:
                        cleanup_error('kill', error)
                    try:
                        row['returncode'] = process.wait(timeout=self._CLEANUP_WAIT_SECONDS)
                        reaped = True
                    except BaseException as error:
                        cleanup_error('wait', error)
                for _ in range(2):
                    if stream.closed:
                        break
                    try:
                        stream.close()
                    except BaseException as error:
                        cleanup_error('close', error)
                cleanup.update(child_reaped=reaped, stdout_closed=stream.closed)
                cleanup['status'] = ('completed_with_errors' if secondary else 'completed') if (
                    reaped and stream.closed) else 'incomplete'
        if primary is None and row['code'] is None and secondary:
            primary = secondary[0]
        if primary is not None:
            # Never replace the first ordinary/control exception with cleanup.
            try:
                primary.virtual_dut_cleanup = cleanup
                primary.virtual_dut_cleanup_errors = tuple(secondary)
            except BaseException:
                pass
            raise primary
        row['response'] = bytes(output[:self._RESPONSE_LIMIT]).decode('ascii', errors='replace')
        if row['code'] is not None:
            return row
        if cleanup['status'] == 'incomplete':
            row['code'] = 'adb_cleanup_incomplete'
        elif row['returncode'] != 0:
            row['code'] = 'adb_nonzero_exit'
        else:
            row['status'] = 'completed'
        return row

    def read_identity(self):
        """No discovery, connect, installation, forwarding, arbitrary shell or RF."""
        transcript = []
        model = None
        checks = [(('shell', 'getprop', 'ro.kernel.qemu'), lambda value: value == '1'),
                  (('shell', 'getprop', 'ro.hardware'), lambda value: value in ('ranchu', 'goldfish')),
                  (('get-state',), lambda value: value == 'device'),
                  (('shell', 'getprop', 'ro.product.model'),
                   lambda value: re.fullmatch(r'[ -~]{1,128}', value) is not None)]
        status, code = 'completed', None
        for command, accepts in checks:
            row = self._read(command)
            transcript.append(row)
            if row['status'] != 'completed':
                status, code = row['status'], row['code']
                break
            # A single ASCII line only; never accept a known prefix with extra text.
            value = row['response'].removesuffix('\n').removesuffix('\r')
            if not accepts(value):
                row['status'], row['code'] = 'failed', 'adb_unknown_response'
                status, code = row['status'], row['code']
                break
            if command[-1] == 'ro.product.model':
                model = value
        return {'schema_version': 1, 'status': status, 'code': code,
                'transport': 'opt_in_adb_emulator_identity', 'serial': self._serial,
                'emulator_identity_confirmed': status == 'completed', 'model': model,
                'rf_source': None, **_provenance(), 'transcript': transcript}
