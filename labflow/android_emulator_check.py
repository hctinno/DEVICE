"""Isolated official Android SDK installation and bounded, explicit OS proof.

Default execution is preflight. Native ADB clients are never used for transport:
the exact owned foreground server is queried over its loopback wire protocol,
so an unavailable server cannot trigger adb's implicit start-server fallback.
No RF/OEM/physical-device capability is asserted by an Android OS boot.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import signal
import socket
import stat
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


REPOSITORY = 'https://dl.google.com/android/repository/repository2-3.xml'
IMAGES = 'https://dl.google.com/android/repository/sys-img/android/sys-img2-3.xml'
CLI_SHA256 = '90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a'
IMAGE_PACKAGE = 'system-images;android-36;default;x86_64'
MIB = 1024 * 1024
DOWNLOAD_CAP = 3 * 1024 * MIB
ARCHIVE_CAP = 2 * 1024 * MIB
EXTRACT_CAP = 12 * 1024 * MIB
OWNER_FILE = 'dgm-runtime-owner.json'
PROPERTIES = ('ro.kernel.qemu', 'ro.hardware', 'ro.product.model', 'sys.boot_completed')
NATIVE_PATHS = ('platform-tools/adb.exe', 'emulator/emulator.exe',
                'emulator/qemu/windows-x86_64/qemu-system-x86_64.exe')


class BoundaryError(RuntimeError):
    def __init__(self, code: str, detail: str = ''):
        self.code = code
        super().__init__(detail or code)


def now() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat()


def write_json(path: Path, value: object) -> None:
    reject_links(path)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha_file(path: Path, algorithm: str = 'sha256', deadline: float | None = None) -> str:
    digest = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(MIB), b''):
            if deadline is not None:
                remaining(deadline, 'runtime_integrity_timeout')
            digest.update(block)
    if deadline is not None:
        remaining(deadline, 'runtime_integrity_timeout')
    return digest.hexdigest()


def reject_links(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            attributes = getattr(part.lstat(), 'st_file_attributes', 0)
        except FileNotFoundError:
            attributes = 0
        if (attributes & 0x400 or part.is_symlink()
                or (hasattr(part, 'is_junction') and part.is_junction())):
            raise BoundaryError('linked_path', str(part))


def reject_tree_links(root: Path) -> None:
    """Walk only after rejecting each entry; never recurse into a reparse point."""
    pending = [root]
    while pending:
        current = pending.pop()
        reject_links(current)
        if current.is_dir():
            with os.scandir(current) as entries:
                for entry in entries:
                    child = Path(entry.path)
                    reject_links(child)
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(child)


@dataclass(frozen=True)
class Endpoint:
    adb_port: int = 15037
    console_port: int = 5680
    grpc_port: int = 18554

    def __post_init__(self):
        values = (self.adb_port, self.console_port, self.grpc_port)
        if any(type(v) is not int or not 1024 <= v <= 65535 for v in values):
            raise BoundaryError('endpoint_invalid')
        if (self.adb_port == 5037 or self.grpc_port == 5037
                or not 5554 <= self.console_port <= 5682 or self.console_port % 2
                or len(set((*values, self.console_port + 1))) != 4):
            raise BoundaryError('endpoint_invalid')

    @property
    def serial(self):
        return f'emulator-{self.console_port}'

    @property
    def server_socket(self):
        return f'tcp:127.0.0.1:{self.adb_port}'


def _require_rf_bridge_endpoint(endpoint: Endpoint):
    if type(endpoint) is not Endpoint or endpoint != Endpoint(15037, 5680, 18554):
        raise BoundaryError('rf_bridge_endpoint_invalid')


def private_environment(runtime: Path, output: Path, endpoint: Endpoint,
                        base: dict | None = None) -> dict:
    env = dict(os.environ if base is None else base)
    # Remove inherited SDK/key/proxy/trace configuration, retaining the user's PATH.
    for key in list(env):
        if key.startswith(('ADB_', 'ANDROID_', 'QEMU_')) or key.upper() in (
                'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'JAVA_HOME', '_JAVA_OPTIONS'):
            env.pop(key)
    home = str(output / 'home')
    env.update(HOME=home, USERPROFILE=home, ANDROID_USER_HOME=str(output / 'home/.android'),
               ANDROID_EMULATOR_HOME=str(output / 'home/.android'),
               ANDROID_SDK_HOME=home, ANDROID_AVD_HOME=str(output / 'avd'),
               ANDROID_HOME=str(runtime / 'sdk'), ANDROID_SDK_ROOT=str(runtime / 'sdk'),
               ADB_VENDOR_KEYS=str(output / 'keys'), ANDROID_SERIAL=endpoint.serial,
               ANDROID_ADB_SERVER_PORT=str(endpoint.adb_port),
               ADB_SERVER_SOCKET=endpoint.server_socket, ADB_USB='0', ADB_EMU='0',
               ADB_MDNS='0', ADB_MDNS_AUTO_CONNECT='', ADB_LOCAL_TRANSPORT_MAX_PORT='0',
               ANDROID_EMULATOR_DISABLE_METRICS='1',
               TMP=str(output / 'tmp'), TEMP=str(output / 'tmp'))
    return env


def memory_gate(available_mib: int | float, guest_mib: int = 1536) -> dict:
    if type(guest_mib) is not int or not 1536 <= guest_mib <= 8192:
        raise BoundaryError('guest_memory_invalid', 'Official CLI range is 1536..8192 MiB')
    required = guest_mib + 1024 + 1024
    return dict(allowed=available_mib >= required, available_mib=available_mib,
                guest_mib=guest_mib, host_overhead_mib=1024, reserve_mib=1024,
                required_available_mib=required)


def resources() -> dict:
    if os.name == 'nt':
        class Memory(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
                (name, ctypes.c_ulonglong) for name in
                ('total', 'available', 'total_page', 'available_page', 'total_virtual',
                 'available_virtual', 'extended')]
        data = Memory()
        data.length = ctypes.sizeof(data)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(data)):
            raise BoundaryError('memory_observation_failed')
        total, available = data.total, data.available
    else:
        total = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
        available = os.sysconf('SC_AVPHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
    return dict(observed_at=now(), total_mib=round(total / MIB, 2),
                available_mib=round(available / MIB, 2),
                disk_free_bytes=shutil.disk_usage(Path.cwd()).free)


class Report:
    def __init__(self, output: Path):
        reject_links(output)
        try:
            output.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise BoundaryError('output_exists', str(output)) from exc
        self.output = output
        self.data = dict(schema_version=1, started_at=now(), output=str(output),
                         status='not_run', android_os='not_run', adb_verified=False,
                         rf_model='not_assessed', oem='not_assessed',
                         anyway='not_assessed', physical='not_assessed',
                         first_failure=None, failures=[], phases=[], processes=[])
        self.save()

    def fail(self, code: str, detail: str):
        failure = dict(code=code, detail=detail, observed_at=now())
        if self.data['first_failure'] is None:
            self.data['first_failure'] = failure
        self.data['failures'].append(failure)
        self.save()

    def save(self):
        write_json(self.output / 'result.json', self.data)


class DownloadBudget:
    def __init__(self, limit: int = DOWNLOAD_CAP):
        self.limit, self.used = limit, 0


def official_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme == 'https' and parsed.hostname == 'dl.google.com'
            and parsed.port is None and parsed.path.startswith('/android/repository/')
            and not parsed.query and not parsed.fragment
            and not parsed.username and '..' not in parsed.path.split('/'))


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official_url(newurl):
            raise BoundaryError('download_redirect_rejected', newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(package: dict, target: Path, budget: DownloadBudget,
             total_timeout: float = 600) -> dict:
    reject_links(target)
    reject_links(target.with_suffix(target.suffix + '.partial'))
    size, url = package['size'], package['url']
    if (type(size) is not int or size <= 0 or size > ARCHIVE_CAP
            or size + budget.used > budget.limit or not official_url(url)):
        raise BoundaryError('download_boundary', url)
    if target.exists() or target.with_suffix(target.suffix + '.partial').exists():
        raise BoundaryError('download_target_exists', str(target))
    partial = target.with_suffix(target.suffix + '.partial')
    started, received = time.monotonic(), 0
    # A redirect handler validates every hop, not only the final response URL.
    opener = urllib.request.build_opener(OfficialRedirect())
    try:
        with opener.open(url, timeout=30) as response, partial.open('xb') as stream:
            if not official_url(response.geturl()):
                raise BoundaryError('download_redirect_rejected', response.geturl())
            header_size = response.headers.get('Content-Length')
            if header_size is not None and int(header_size) != size:
                raise BoundaryError('download_size_header_mismatch', str(header_size))
            while True:
                if time.monotonic() - started > total_timeout:
                    raise BoundaryError('download_timeout', url)
                block = response.read(min(MIB, size - received + 1))
                if not block:
                    break
                stream.write(block)
                received += len(block)
                budget.used += len(block)
                if received > size or budget.used > budget.limit:
                    raise BoundaryError('download_stream_cap', url)
        if received != size:
            raise BoundaryError('download_size_mismatch', f'{received} != {size}')
        algorithm = package.get('checksum_type', 'sha256')
        if sha_file(partial, algorithm) != package['checksum']:
            raise BoundaryError('download_checksum_mismatch', url)
        digest = sha_file(partial)
        partial.rename(target)
        return dict(url=url, bytes=received, sha256=digest,
                    metadata_checksum=package['checksum'], checksum_type=algorithm,
                    elapsed_seconds=round(time.monotonic() - started, 3))
    finally:
        # .partial is deliberately retained on failure, with consumed byte budget.
        pass


def metadata(url: str, target: Path, budget: DownloadBudget) -> bytes:
    reject_links(target)
    reject_links(target.with_suffix(target.suffix + '.partial'))
    if not official_url(url):
        raise BoundaryError('metadata_url_invalid')
    opener = urllib.request.build_opener(OfficialRedirect())
    partial = target.with_suffix(target.suffix + '.partial')
    started, received = time.monotonic(), 0
    with opener.open(url, timeout=30) as response, partial.open('xb') as stream:
        if not official_url(response.geturl()):
            raise BoundaryError('download_redirect_rejected', response.geturl())
        while True:
            if time.monotonic() - started > 60:
                raise BoundaryError('metadata_timeout')
            block = response.read(min(65536, 2 * MIB - received + 1))
            if not block:
                break
            stream.write(block)
            received += len(block)
            budget.used += len(block)
            if received > 2 * MIB or budget.used > budget.limit:
                raise BoundaryError('metadata_cap')
    partial.rename(target)
    return target.read_bytes()


def select_package(raw: bytes, name: str, source: str) -> dict:
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise BoundaryError('metadata_entity_rejected')
    root = ET.fromstring(raw)
    choices = []
    for node in root.findall('remotePackage'):
        channel = node.find('channelRef')
        if (node.get('path') != name or node.find('obsolete') is not None
                or (channel is not None and channel.get('ref') != 'channel-0')):
            continue
        revision = node.find('revision')
        if revision is None or revision.find('preview') is not None:
            continue
        version = tuple(int(c.text) for c in revision)
        license_ref = node.find('uses-license')
        if license_ref is None:
            raise BoundaryError('package_license_missing', name)
        license_id = license_ref.get('ref')
        license_node = next((v for v in root.findall('license') if v.get('id') == license_id), None)
        if license_node is None:
            raise BoundaryError('package_license_missing', name)
        for archive in node.findall('archives/archive'):
            if archive.findtext('host-os') not in (None, 'windows'):
                continue
            urlpart = archive.findtext('complete/url', '')
            if ('/' in urlpart or '\\' in urlpart or ':' in urlpart or urlpart.startswith('.')):
                raise BoundaryError('package_url_rejected', urlpart)
            checksum = archive.find('complete/checksum')
            if checksum is None:
                raise BoundaryError('package_checksum_missing', name)
            algorithm = checksum.get('type', 'sha1')
            digest = checksum.text or ''
            size = int(archive.findtext('complete/size', '0'))
            if (algorithm not in ('sha1', 'sha256') or len(digest) != {'sha1': 40, 'sha256': 64}[algorithm]
                    or any(c not in '0123456789abcdef' for c in digest)
                    or not 0 < size <= ARCHIVE_CAP):
                raise BoundaryError('package_metadata_invalid', name)
            choices.append((version, dict(package=name, version='.'.join(map(str, version)),
                source=source, url=urllib.parse.urljoin(source, urlpart), size=size,
                checksum_type=algorithm, checksum=digest, license_id=license_id,
                license_text=''.join(license_node.itertext()))))
    if not choices:
        raise BoundaryError('package_unavailable', name)
    return max(choices, key=lambda c: c[0])[1]


def archive_members(archive: zipfile.ZipFile, limit: int = EXTRACT_CAP) -> list:
    infos = archive.infolist()
    if sum(i.file_size for i in infos) > limit or len(infos) > 100000:
        raise BoundaryError('extract_cap')
    names = set()
    for info in infos:
        name = info.filename
        # PurePosixPath/extractall collapse ./ and repeated separators. Reject
        # those raw segments before deriving a path or creating any directory.
        parts = name[:-1].split('/') if name.endswith('/') else name.split('/')
        canonical = '/'.join(parts).casefold()
        mode = info.external_attr >> 16
        if (not name or name.startswith(('/', '\\')) or '\\' in name or ':' in name
                or any(p in ('', '.', '..') or p.rstrip(' .') != p for p in parts)
                or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                or info.flag_bits & 1 or canonical in names):
            raise BoundaryError('archive_member_rejected', name)
        if any(p.split('.')[0].upper() in {'CON', 'NUL', 'AUX', 'PRN',
               *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))} for p in parts):
            raise BoundaryError('archive_member_rejected', name)
        names.add(canonical)
    return infos


def safe_extract(source: bytes | Path, target: Path, limit: int = EXTRACT_CAP) -> int:
    reject_links(target)
    if target.exists():
        raise BoundaryError('extract_target_exists', str(target))
    with zipfile.ZipFile(io.BytesIO(source) if isinstance(source, bytes) else source) as archive:
        infos = archive_members(archive, limit)
        total = sum(i.file_size for i in infos)
        target.mkdir(parents=True, exist_ok=False)
        archive.extractall(target)
    return total


class _WindowsJob:
    """Own a suspended process and its descendants before any child can execute."""
    def __init__(self, limit_mib: int):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                        wintypes.DWORD, ctypes.c_void_p]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('minimum', ctypes.c_size_t),
                        ('maximum', ctypes.c_size_t), ('active', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                        ('scheduling', wintypes.DWORD)]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', ctypes.c_ulonglong * 6),
                        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                        ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.extended = Extended
        info = Extended()
        info.basic.flags = 0x2000 | 0x200  # kill descendants on close; whole-job memory cap
        info.job_memory = limit_mib * MIB
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise BoundaryError('process_job_unavailable', str(ctypes.get_last_error()))

    def assign_resume(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            raise BoundaryError('process_job_assignment_failed', str(ctypes.get_last_error()))
        ntdll = ctypes.WinDLL('ntdll')
        ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        if ntdll.NtResumeProcess(wintypes.HANDLE(int(process._handle))) != 0:
            raise BoundaryError('process_resume_failed')

    def snapshot(self):
        info = self.extended()
        if not self.kernel.QueryInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info), None):
            raise BoundaryError('process_job_query_failed')
        # JOBOBJECT_BASIC_PROCESS_ID_LIST, bounded to at most 128 owned descendants.
        class Pids(ctypes.Structure):
            _fields_ = [('assigned', wintypes.DWORD), ('count', wintypes.DWORD),
                        ('ids', ctypes.c_size_t * 128)]
        pids = Pids()
        if not self.kernel.QueryInformationJobObject(self.handle, 3, ctypes.byref(pids), ctypes.sizeof(pids), None):
            raise BoundaryError('process_tree_query_failed')
        owner_pids = list(pids.ids[:pids.count])
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('peak_rss', 'rss', 'peak_paged',
                 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        rss, unreadable = 0, []
        for pid in owner_pids:
            handle = self.kernel.OpenProcess(0x0400 | 0x0010, False, pid)
            if not handle:
                unreadable.append(pid)  # May have exited between the two snapshots.
                continue
            try:
                counts = Counters()
                counts.cb = ctypes.sizeof(counts)
                if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counts), counts.cb):
                    rss += counts.rss
                else:
                    unreadable.append(pid)
            finally:
                self.kernel.CloseHandle(handle)
        return dict(pids=owner_pids, tree_rss_mib=round(rss / MIB, 2),
                    unreadable_rss_pids=unreadable,
                    peak_committed_mib=round(info.peak_job / MIB, 2))

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class OwnedProcess:
    def __init__(self, command: list[str], env: dict, report: Report, label: str,
                 memory_limit_mib: int = 512):
        self.command, self.env, self.report, self.label = command, env, report, label
        self.memory_limit_mib = memory_limit_mib
        self.job, self.process = None, None
        self.streams = []

    def __enter__(self):
        self.record = dict(label=self.label, command=self.command, started_at=now(),
                           memory_limit_mib=self.memory_limit_mib, closed=False, snapshots=[])
        self.report.data['processes'].append(self.record)
        try:
            self.streams = [(self.report.output / f'{self.label}.{kind}.log').open('xb')
                            for kind in ('stdout', 'stderr')]
            if os.name == 'nt':
                self.job = _WindowsJob(self.memory_limit_mib)
            flags = 0x08000000 | 0x00000004 if os.name == 'nt' else 0
            self.process = subprocess.Popen(self.command, env=self.env, cwd=self.report.output,
                stdin=subprocess.DEVNULL, stdout=self.streams[0], stderr=self.streams[1],
                creationflags=flags, start_new_session=os.name != 'nt')
            self.record['pid'] = self.process.pid
            self.report.save()
            if self.job:
                self.job.assign_resume(self.process)
            self.sample()
            return self
        except BaseException:
            self.close()
            raise

    def sample(self):
        sample = self.job.snapshot() if self.job else {'pids': [self.process.pid]}
        sample['at'] = now()
        self.record['snapshots'].append(sample)
        self.report.save()
        if sample.get('tree_rss_mib', 0) > self.memory_limit_mib:
            raise BoundaryError('process_tree_rss_limit', self.label)

    def wait(self, timeout: float) -> int:
        deadline = time.monotonic() + timeout
        while self.process.poll() is None:
            if time.monotonic() >= deadline:
                raise BoundaryError('process_timeout', self.label)
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        self.record['exit_code'] = self.process.returncode
        self.sample()
        return self.process.returncode

    def close(self):
        if self.process:
            self.record['exit_code_before_cleanup'] = self.process.poll()
        if self.job:
            self.job.close()
        if self.process and self.process.poll() is None:
            if os.name == 'nt':
                # Assignment failure leaves only our suspended, never-run child.
                self.process.kill()
            else:
                os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name != 'nt':
                    os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        for stream in self.streams:
            stream.close()
        if hasattr(self, 'record'):
            self.record['closed'] = self.process is None or self.process.poll() is not None
            self.record['exit_code'] = self.process.poll() if self.process else None
            self.record['closed_at'] = now()
            self.report.save()

    def __exit__(self, kind, value, traceback):
        if value is not None:
            self.report.fail(getattr(value, 'code', 'process_exception'), str(value))
        try:
            self.close()
        except Exception as exc:
            self.report.fail('cleanup_error', repr(exc))
            if value is None:
                raise


def native(command: list[str], env: dict, report: Report, label: str,
           timeout: float = 30, allow_nonzero: bool = False) -> str:
    with OwnedProcess(command, env, report, label) as child:
        code = child.wait(timeout)
        if code and not allow_nonzero:
            raise BoundaryError('native_exit', f'{label}: exit {code}')
    return (report.output / f'{label}.stdout.log').read_text('utf-8', errors='replace')


def assert_ports_free(ports: list[int]) -> None:
    sockets = []
    try:
        for port in ports:
            bound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets.append(bound)
            if os.name == 'nt':
                bound.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            bound.bind(('127.0.0.1', port))
    except OSError as exc:
        raise BoundaryError('owner_port_busy', str(port)) from exc
    finally:
        for bound in sockets:
            bound.close()


def claim_attempt(runtime: Path, output: Path):
    try:
        with (runtime / 'boot-attempt.json').open('x', encoding='utf-8') as stream:
            json.dump(dict(claimed_at=now(), output=str(output), max_attempts=1), stream)
    except FileExistsError as exc:
        raise BoundaryError('boot_attempt_already_used') from exc


def wire_services(endpoint: Endpoint, name: str) -> list[str]:
    if name == 'get-state':
        return [f'host-serial:{endpoint.serial}:get-state']
    if name not in PROPERTIES:
        raise BoundaryError('adb_command_not_allowed', name)
    return [f'host:transport:{endpoint.serial}', f'shell:getprop {name}']


def remaining(deadline: float, code: str = 'adb_timeout') -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise BoundaryError(code)
    return left


def _receive(stream: socket.socket, count: int, deadline: float | None = None) -> bytes:
    result = b''
    while len(result) < count:
        if deadline is not None:
            stream.settimeout(remaining(deadline))
        chunk = stream.recv(count - len(result))
        if deadline is not None:
            remaining(deadline)
        if not chunk:
            raise BoundaryError('adb_short_response')
        result += chunk
    return result


def adb_read(endpoint: Endpoint, name: str, server: OwnedProcess, timeout: float = 2,
             deadline: float | None = None) -> str:
    code = server.process.poll()
    if code is not None:
        raise BoundaryError('owned_adb_server_exited', f'pid={server.process.pid} exit_code={code}')
    services = wire_services(endpoint, name)
    deadline = min(time.monotonic() + timeout, deadline) if deadline is not None else time.monotonic() + timeout
    # This is the only transport connect: one explicitly owned loopback endpoint.
    try:
        with socket.create_connection(('127.0.0.1', endpoint.adb_port), timeout=remaining(deadline)) as stream:
            for service in services:
                encoded = service.encode('ascii')
                stream.settimeout(remaining(deadline))
                stream.sendall(f'{len(encoded):04x}'.encode() + encoded)
                remaining(deadline)
                status = _receive(stream, 4, deadline)
                if status == b'FAIL':
                    length = int(_receive(stream, 4, deadline), 16)
                    reason = _receive(stream, length, deadline).decode('utf-8', errors='replace')
                    raise BoundaryError('adb_service_failure', reason)
                if status != b'OKAY':
                    raise BoundaryError('adb_invalid_status', repr(status))
            if name == 'get-state':
                return _receive(stream, int(_receive(stream, 4, deadline), 16), deadline).decode().strip()
            raw = bytearray()
            while len(raw) < 65536:
                stream.settimeout(remaining(deadline))
                block = stream.recv(min(4096, 65536 - len(raw)))
                remaining(deadline)
                if not block:
                    return raw.decode('utf-8', errors='replace').strip()
                raw.extend(block)
            raise BoundaryError('adb_response_limit')
    except (BoundaryError, OSError, ValueError) as exc:
        code = server.process.poll()
        if code is not None:
            raise BoundaryError('owned_adb_server_exited',
                f'pid={server.process.pid} exit_code={code}; wire_error={exc}') from exc
        if isinstance(exc, TimeoutError):
            raise BoundaryError('adb_timeout', f'{name}: absolute deadline reached') from exc
        if isinstance(exc, ValueError):
            raise BoundaryError('adb_invalid_length', str(exc)) from exc
        raise


def boot_retryable(exc: BoundaryError, endpoint: Endpoint) -> bool:
    return exc.code == 'adb_service_failure' and str(exc) in (
        f"device '{endpoint.serial}' not found", 'device offline')


def cached_archive(spec: dict, target: Path, budget: DownloadBudget) -> dict:
    reject_links(target)
    if not target.is_file():
        return download(spec, target, budget)
    if (target.stat().st_size != spec['size']
            or sha_file(target, spec['checksum_type']) != spec['checksum']):
        raise BoundaryError('cached_archive_changed', str(target))
    return dict(url=spec['url'], bytes=spec['size'], sha256=sha_file(target), reused=True)


def publish_package(source: Path, destination: Path) -> None:
    """Copy verified extraction without rename or overwriting a prior byte."""
    reject_links(source)
    reject_links(destination)
    source_paths = {p.relative_to(source) for p in source.rglob('*')}
    if destination.exists():
        extras = {p.relative_to(destination) for p in destination.rglob('*')} - source_paths
        if extras:
            raise BoundaryError('package_existing_change', str(sorted(map(str, extras))[:5]))
    destination.mkdir(parents=True, exist_ok=True)
    for relative in sorted(source_paths):
        current, target = source / relative, destination / relative
        reject_links(current)
        reject_links(target)
        if current.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif target.exists():
            if not target.is_file() or sha_file(current) != sha_file(target):
                raise BoundaryError('package_existing_change', str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with current.open('rb') as incoming, target.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing, MIB)


def install_runtime(runtime: Path, report: Report, accept_license: bool,
                    resume: bool = False) -> dict:
    if not accept_license:
        raise BoundaryError('sdk_license_not_accepted', 'Pass --accept-sdk-license after reviewing official terms')
    reject_links(runtime)
    reject_tree_links(runtime)
    if resume:
        marker = runtime / OWNER_FILE
        if not marker.is_file():
            raise BoundaryError('resume_requires_owned_runtime')
        manifest = json.loads(marker.read_text('utf-8'))
        if (manifest.get('runtime') != str(runtime) or manifest.get('completed')
                or manifest.get('resume_claimed') or not manifest.get('packages')):
            raise BoundaryError('resume_unavailable')
        manifest['resume_claimed'] = now()
        manifest.setdefault('previous_outputs', []).append(str(report.output))
    else:
        if runtime.exists():
            raise BoundaryError('install_requires_new_runtime')
        runtime.mkdir(parents=True, exist_ok=False)
        manifest = dict(schema_version=1, runtime=str(runtime), created_at=now(),
                        completed=False, packages=[], downloads=[], downloaded_bytes=0)
    write_json(runtime / OWNER_FILE, manifest)
    sources, archives, sdk = runtime / 'sources', runtime / 'archives', runtime / 'sdk'
    for folder in (sources, archives, sdk):
        folder.mkdir(exist_ok=resume)
    budget = DownloadBudget()
    budget.used = manifest['downloaded_bytes']
    if not 0 <= budget.used <= DOWNLOAD_CAP:
        raise BoundaryError('resume_budget_invalid')
    # Conservatively include both the recorded count and retained staging. Older
    # interrupted installs may have moved successful stages into sdk/ before
    # failing, or extracted a failed stage before recording its byte count.
    extracted = (manifest.get('extracted_bytes', 0) + sum(
        p.stat().st_size for directory in runtime.glob('extract-*')
        for p in directory.rglob('*') if p.is_file())) if resume else 0
    deadline = time.monotonic() + 1200
    try:
        repo = ((sources / 'repository.xml').read_bytes() if resume
                else metadata(REPOSITORY, sources / 'repository.xml', budget))
        images = ((sources / 'aosp-images.xml').read_bytes() if resume
                  else metadata(IMAGES, sources / 'aosp-images.xml', budget))
        specs = [select_package(repo, name, REPOSITORY)
                 for name in ('cmdline-tools;22.0', 'platform-tools', 'emulator')]
        specs.append(select_package(images, IMAGE_PACKAGE, IMAGES))
        pinned = specs[0]
        if not pinned['url'].endswith('/commandlinetools-win-15859902_latest.zip'):
            raise BoundaryError('pinned_cli_changed', pinned['url'])
        pinned['checksum_type'], pinned['checksum'] = 'sha256', CLI_SHA256
        selected = [{k: v for k, v in spec.items() if k != 'license_text'} for spec in specs]
        if resume and selected != manifest['packages']:
            raise BoundaryError('resume_packages_changed')
        manifest['packages'] = selected
        for spec in specs:
            if spec['license_id'] != 'android-sdk-license':
                raise BoundaryError('new_license_review_required', spec['license_id'])
            license_path = sources / f"{spec['package'].replace(';', '-')}.license.txt"
            reject_links(license_path)
            if license_path.exists():
                if license_path.read_text('utf-8') != spec['license_text']:
                    raise BoundaryError('license_source_changed', str(license_path))
            else:
                with license_path.open('x', encoding='utf-8') as stream:
                    stream.write(spec['license_text'])
        manifest['license_acceptance'] = dict(at=now(), scope='local development only',
            license_id='android-sdk-license', source=REPOSITORY,
            redistribution='not granted by this runner; keep binaries, images and terms outside Git')
        write_json(runtime / OWNER_FILE, manifest)
        for index, spec in enumerate(specs):
            if time.monotonic() >= deadline:
                raise BoundaryError('install_deadline')
            target = archives / spec['url'].rsplit('/', 1)[-1]
            proof = cached_archive(spec, target, budget) if resume else download(
                spec, target, budget, min(600, deadline - time.monotonic()))
            if proof.get('reused'):
                manifest.setdefault('reused_archives', []).append(proof)
            else:
                manifest['downloads'].append(proof)
            manifest['downloaded_bytes'] = budget.used
            write_json(runtime / OWNER_FILE, manifest)
            staging = runtime / f"extract-{index}{'-resume' if resume else ''}"
            extracted += safe_extract(target, staging, EXTRACT_CAP - extracted)
            manifest['extracted_bytes'] = extracted
            write_json(runtime / OWNER_FILE, manifest)
            if index == 0:
                destination = sdk / 'cmdline-tools/22.0'
                publish_package(staging / 'cmdline-tools', destination)
            elif index in (1, 2):
                name = 'platform-tools' if index == 1 else 'emulator'
                publish_package(staging / name, sdk / name)
            else:
                destination = sdk / 'system-images/android-36/default/x86_64'
                publish_package(staging / 'x86_64', destination)
            manifest['extracted_bytes'] = extracted
            write_json(runtime / OWNER_FILE, manifest)
        inventory, proof = archive_inventory(runtime, manifest, deadline)
        validate_sdk_inventory(sdk, inventory, deadline)
        manifest.update(file_inventory=inventory, inventory_version=2,
                        inventory_source=proof)
        manifest['executables'] = {name: inventory[name] for name in NATIVE_PATHS}
        manifest['completed'] = True
        manifest['finished_at'] = now()
        return manifest
    finally:
        manifest['downloaded_bytes'] = budget.used
        write_json(runtime / OWNER_FILE, manifest)
        report.data['installation'] = manifest
        report.save()


def archive_inventory(runtime: Path, manifest: dict, deadline: float) -> tuple[dict, dict]:
    """Derive expected bytes from preserved official archives, never SDK bytes."""
    reject_tree_links(runtime)
    sources = runtime / 'sources'
    repo = (sources / 'repository.xml').read_bytes()
    images = (sources / 'aosp-images.xml').read_bytes()
    specs = [select_package(repo, name, REPOSITORY)
             for name in ('cmdline-tools;22.0', 'platform-tools', 'emulator')]
    specs.append(select_package(images, IMAGE_PACKAGE, IMAGES))
    if not specs[0]['url'].endswith('/commandlinetools-win-15859902_latest.zip'):
        raise BoundaryError('pinned_cli_changed')
    specs[0]['checksum_type'], specs[0]['checksum'] = 'sha256', CLI_SHA256
    if [{k:v for k,v in s.items() if k != 'license_text'} for s in specs] != manifest.get('packages'):
        raise BoundaryError('runtime_archive_metadata_changed')
    recorded = {d['url']:d for d in manifest.get('downloads', [])}
    roots = ('cmdline-tools', 'platform-tools', 'emulator', 'x86_64')
    destinations = ('cmdline-tools/22.0', 'platform-tools', 'emulator',
                    'system-images/android-36/default/x86_64')
    inventory, proofs, expanded = {}, [], 0
    for spec, prefix, destination in zip(specs, roots, destinations):
        remaining(deadline, 'runtime_integrity_timeout')
        archive_path = runtime / 'archives' / spec['url'].rsplit('/', 1)[-1]
        reject_links(archive_path)
        record = recorded.get(spec['url'], {})
        if (not archive_path.is_file() or archive_path.stat().st_size != spec['size']
                or record.get('bytes') != spec['size'] or not record.get('sha256')):
            raise BoundaryError('runtime_archive_proof_missing', spec['package'])
        digest = sha_file(archive_path, deadline=deadline)
        if (digest != record['sha256'] or sha_file(archive_path, spec['checksum_type'], deadline) != spec['checksum']):
            raise BoundaryError('runtime_archive_changed', spec['package'])
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive_members(archive, EXTRACT_CAP - expanded)
            expanded += sum(info.file_size for info in infos)
            count = 0
            for info in infos:
                remaining(deadline, 'runtime_integrity_timeout')
                parts = PurePosixPath(info.filename).parts
                if not parts or parts[0] != prefix:
                    raise BoundaryError('runtime_archive_layout', info.filename)
                if info.is_dir():
                    continue
                name = '/'.join((destination, *parts[1:]))
                if len(parts) < 2 or name in inventory:
                    raise BoundaryError('runtime_archive_layout', info.filename)
                expected = hashlib.sha256()
                with archive.open(info) as incoming:
                    for block in iter(lambda: incoming.read(MIB), b''):
                        remaining(deadline, 'runtime_integrity_timeout')
                        expected.update(block)
                inventory[name] = expected.hexdigest()
                count += 1
        proofs.append(dict(package=spec['package'], url=spec['url'], sha256=digest,
                           bytes=spec['size'], files=count))
    return inventory, dict(kind='verified_preserved_archives', archives=proofs,
        metadata_sha256={'repository.xml':hashlib.sha256(repo).hexdigest(),
                         'aosp-images.xml':hashlib.sha256(images).hexdigest()},
        expanded_bytes=expanded)


def validate_sdk_inventory(sdk: Path, inventory: dict, deadline: float) -> None:
    reject_tree_links(sdk)
    if not isinstance(inventory, dict) or not inventory:
        raise BoundaryError('runtime_inventory_missing')
    for name, digest in inventory.items():
        parts = PurePosixPath(name).parts
        if (not parts or name != '/'.join(parts) or ':' in name or '\\' in name
                or any(p in ('.', '..', '') for p in parts) or name.startswith('/')
                or not isinstance(digest, str) or len(digest) != 64):
            raise BoundaryError('runtime_inventory_invalid', name)
    actual = {p.relative_to(sdk).as_posix() for p in sdk.rglob('*') if p.is_file()}
    if actual != set(inventory):
        raise BoundaryError('runtime_file_set_changed', str(sorted(actual ^ set(inventory))[:10]))
    for name, digest in inventory.items():
        remaining(deadline, 'runtime_integrity_timeout')
        path = sdk / name
        reject_links(path)
        if sha_file(path, deadline=deadline) != digest:
            raise BoundaryError('runtime_file_changed', name)


def validate_runtime(runtime: Path) -> dict:
    deadline = time.monotonic() + 600
    reject_links(runtime)
    if not runtime.exists():
        raise BoundaryError('runtime_missing', str(runtime))
    marker = runtime / OWNER_FILE
    reject_links(marker)
    if not marker.is_file():
        raise BoundaryError('runtime_unowned', str(runtime))
    manifest = json.loads(marker.read_text('utf-8'))
    if manifest.get('runtime') != str(runtime) or not manifest.get('completed'):
        raise BoundaryError('runtime_incomplete', str(marker))
    if set(manifest.get('executables', {})) != set(NATIVE_PATHS):
        raise BoundaryError('runtime_inventory_missing')
    for name, digest in manifest['executables'].items():
        path = runtime / 'sdk' / name
        reject_links(path)
        if not path.is_file() or sha_file(path, deadline=deadline) != digest:
            raise BoundaryError('runtime_executable_changed', name)
    if manifest.get('inventory_version') == 2 and manifest.get('file_inventory'):
        inventory = manifest['file_inventory']
    else:
        # Legacy owner records remain untouched. The expected inventory is
        # reconstructed only from archives matching the original download proof.
        inventory, proof = archive_inventory(runtime, manifest, deadline)
        manifest = dict(manifest, inventory_version=2, file_inventory=inventory,
                        inventory_source=proof, integrity_owner_record_unchanged=True)
    validate_sdk_inventory(runtime / 'sdk', inventory, deadline)
    return manifest


def create_avd(runtime: Path, output: Path):
    avd = output / 'avd'
    avd.mkdir()
    data = avd / 'dgm_owned.avd'
    data.mkdir()
    (avd / 'dgm_owned.ini').write_text(f'avd.ini.encoding=UTF-8\npath={data}\ntarget=android-36\n', encoding='utf-8')
    image = runtime / 'sdk/system-images/android-36/default/x86_64'
    config = dict(AvdId='dgm_owned', **{'avd.ini.encoding': 'UTF-8', 'abi.type': 'x86_64',
        'hw.cpu.arch': 'x86_64', 'hw.cpu.ncore': '2', 'hw.ramSize': '1536',
        'hw.gpu.enabled': 'yes', 'hw.gpu.mode': 'swiftshader', 'hw.lcd.width': '480',
        'hw.lcd.height': '800', 'hw.lcd.density': '160', 'hw.keyboard': 'no',
        'hw.audioInput': 'no', 'hw.audioOutput': 'no', 'hw.camera.back': 'none',
        'hw.camera.front': 'none', 'hw.gps': 'no', 'disk.dataPartition.size': '2G',
        'image.sysdir.1': str(image), 'tag.id': 'default', 'tag.display': 'Default',
        'PlayStore.enabled': 'false', 'showDeviceFrame': 'no'})
    (data / 'config.ini').write_text(''.join(f'{k}={v}\n' for k, v in config.items()), encoding='utf-8')
    return data


def boot_runtime(runtime: Path, report: Report, env: dict, endpoint: Endpoint,
                 timeout: int, acceleration: str, help_text: str,
                 rf_bridge_check: bool = False):
    if rf_bridge_check:
        _require_rf_bridge_endpoint(endpoint)
    if acceleration not in ('auto', 'off'):
        raise BoundaryError('acceleration_invalid')
    if acceleration == 'off':
        # Current official docs call CPU software emulation unsupported; do not
        # force ANDROID_I_WANT_MY_TCG or silently pick an older emulator/image.
        raise BoundaryError('software_cpu_unsupported', 'Current official emulator documentation labels -accel off unsupported')
    gate = memory_gate(resources()['available_mib'])
    report.data['memory_gate'] = gate
    report.save()
    if not gate['allowed']:
        raise BoundaryError('memory_headroom_insufficient', json.dumps(gate))
    for option in ('-no-window', '-no-audio', '-no-snapshot', '-memory', '-port', '-grpc', '-gpu'):
        if option not in help_text:
            raise BoundaryError('native_option_unconfirmed', option)
    assert_ports_free([endpoint.adb_port, endpoint.console_port, endpoint.console_port + 1, endpoint.grpc_port])
    data = create_avd(runtime, report.output)
    report.data['avd'] = str(data)
    adb, emulator = runtime / 'sdk/platform-tools/adb.exe', runtime / 'sdk/emulator/emulator.exe'
    command = [str(emulator), '-avd', 'dgm_owned', '-no-window', '-no-audio',
        '-no-boot-anim', '-no-snapshot', '-gpu', 'swiftshader', '-accel', 'auto',
        '-memory', '1536', '-cores', '2', '-port', str(endpoint.console_port),
        '-grpc', str(endpoint.grpc_port), '-grpc-use-token', '-camera-back', 'none',
        '-camera-front', 'none', '-netdelay', 'none', '-netspeed', 'full',
        '-no-metrics', '-verbose']
    report.data['boot_command'] = command
    report.save()
    # Claim survives Ctrl+C, process failure, and a later new output directory.
    claim_attempt(runtime, report.output)
    with OwnedProcess([str(adb), '-L', endpoint.server_socket, 'server', 'nodaemon'],
                      env, report, 'owned-adb', 256) as server:
        # Readiness is tested with exact serial get-state; no devices/scan/connect.
        ready_deadline = time.monotonic() + 5
        while True:
            try:
                adb_read(endpoint, 'get-state', server, 0.5, deadline=ready_deadline)
                break
            except BoundaryError as exc:
                if boot_retryable(exc, endpoint):
                    break  # Own server is ready; emulator has not been launched.
                raise
            except OSError:
                code = server.process.poll()
                if code is not None:
                    raise BoundaryError('owned_adb_server_exited', f'pid={server.process.pid} exit_code={code}')
                if time.monotonic() >= ready_deadline:
                    raise BoundaryError('owned_adb_not_ready')
                time.sleep(min(0.1, remaining(ready_deadline)))
        # Check again immediately before the heavy process is allowed to run.
        gate = memory_gate(resources()['available_mib'])
        report.data['memory_gate_immediate'] = gate
        if not gate['allowed']:
            raise BoundaryError('memory_headroom_changed', json.dumps(gate))
        deadline = time.monotonic() + timeout
        with OwnedProcess(command, env, report, 'owned-emulator', 2560) as emulator_process:
            while time.monotonic() < deadline:
                server.sample()
                emulator_process.sample()
                if emulator_process.process.poll() is not None:
                    raise BoundaryError('emulator_exited', str(emulator_process.process.returncode))
                if resources()['available_mib'] < 512:
                    raise BoundaryError('memory_emergency_stop')
                try:
                    state = adb_read(endpoint, 'get-state', server, deadline=deadline)
                    values = {key: adb_read(endpoint, key, server, deadline=deadline) for key in PROPERTIES} if state == 'device' else {}
                    remaining(deadline, 'android_boot_timeout')
                    report.data['identity'] = dict(serial=endpoint.serial, state=state, properties=values)
                    report.save()
                    if (state == 'device' and values.get('ro.kernel.qemu') == '1'
                            and values.get('ro.hardware') in ('ranchu', 'goldfish')
                            and values.get('ro.product.model') and values.get('sys.boot_completed') == '1'):
                        report.data.update(android_os='booted', adb_verified=True, status='verified')
                        report.save()
                        if rf_bridge_check:
                            from .android_guest_rf_bridge import run_guest_rf_check
                            run_guest_rf_check(endpoint, server, report,
                                               deadline=time.monotonic() + 30,
                                               emulator_process=emulator_process)
                            report.data['status'] = 'rf_bridge_verified'
                            report.save()
                        return
                except (BoundaryError, OSError) as exc:
                    fatal = not isinstance(exc, BoundaryError) or not boot_retryable(exc, endpoint)
                    if fatal:
                        report.fail(getattr(exc, 'code', 'adb_socket_error'), str(exc))
                    with (report.output / 'adb-observations.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(dict(at=now(), error=str(exc), code=getattr(exc, 'code', 'socket_error'))) + '\n')
                    if fatal:
                        raise
                time.sleep(min(2, max(0, deadline - time.monotonic())))
            raise BoundaryError('android_boot_timeout', str(timeout))


def execute(runtime: Path, output: Path, *, install: bool = False, boot: bool = False,
            resume_install: bool = False,
            verify_only: bool = False,
            accept_sdk_license: bool = False, endpoint: Endpoint | None = None,
            boot_timeout: int = 180, acceleration: str = 'auto',
            rf_bridge_check: bool = False) -> dict:
    runtime, output = Path(runtime).absolute(), Path(output).absolute()
    reject_links(runtime)
    report = Report(output)
    endpoint = endpoint or Endpoint()
    report.data.update(runtime=str(runtime), mode='verify-only' if verify_only else 'boot' if boot else 'install' if install else 'preflight',
        endpoint=dict(host='127.0.0.1', adb_port=endpoint.adb_port, serial=endpoint.serial,
                      console_port=endpoint.console_port, grpc_port=endpoint.grpc_port))
    try:
        if (type(boot_timeout) is not int or not 1 <= boot_timeout <= 180
                or acceleration not in ('auto', 'off') or (install and boot)
                or (resume_install and not install) or (verify_only and (install or boot))
                or type(rf_bridge_check) is not bool or (rf_bridge_check and not boot)):
            raise BoundaryError('options_invalid')
        if rf_bridge_check:
            _require_rf_bridge_endpoint(endpoint)
        report.data['resources_before'] = resources()
        if runtime == output or output in runtime.parents:
            raise BoundaryError('runtime_output_overlap')
        if install:
            if runtime in output.parents:
                raise BoundaryError('runtime_output_overlap')
            install_runtime(runtime, report, accept_sdk_license, resume=resume_install)
        manifest = validate_runtime(runtime)
        report.data['runtime_inventory'] = manifest
        if runtime in output.parents:
            raise BoundaryError('runtime_output_overlap')
        write_json(report.output / 'runtime-integrity.json', manifest)
        if verify_only:
            report.data.update(status='runtime_integrity_verified',
                               not_run_reason='Integrity-only; native tools and Android OS were not executed')
            return report.data
        if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
            raise BoundaryError('unsupported_host', 'This installer is pinned to Windows x86_64')
        env = private_environment(runtime, output, endpoint)
        for folder in ('home/.android', 'keys', 'tmp'):
            (output / folder).mkdir(parents=True, exist_ok=True)
        adb, emulator = runtime / 'sdk/platform-tools/adb.exe', runtime / 'sdk/emulator/emulator.exe'
        observations = [('adb-version', [str(adb), 'version']),
                        ('adb-help', [str(adb), 'help']),
                        ('emulator-version', [str(emulator), '-version']),
                        ('emulator-help', [str(emulator), '-help-all']),
                        ('emulator-environment', [str(emulator), '-help-environment']),
                        ('emulator-accel-check', [str(emulator), '-accel-check'])]
        outputs = {}
        for label, command in observations:
            outputs[label] = native(command, env, report, label, allow_nonzero=label == 'emulator-accel-check')
        report.data['native_versions'] = {k: outputs[k].strip() for k in ('adb-version', 'emulator-version')}
        report.data['acceleration_observation'] = outputs['emulator-accel-check'].strip()
        report.data['memory_gate'] = memory_gate(resources()['available_mib'])
        report.data['status'] = 'runtime_ready'
        report.save()
        if boot:
            boot_runtime(runtime, report, env, endpoint, boot_timeout, acceleration,
                         outputs['emulator-help'], rf_bridge_check=rf_bridge_check)
        else:
            report.data['not_run_reason'] = 'OS boot requires explicit --boot; preflight is not Android OS proof'
    except KeyboardInterrupt:
        report.fail('interrupted', 'Ctrl+C; owned process job is drained')
        report.data['status'] = 'interrupted'
    except Exception as exc:
        report.fail(getattr(exc, 'code', 'unexpected_error'), str(exc))
        report.data['status'] = 'blocked' if boot else 'not_run'
    finally:
        report.data['finished_at'] = now()
        try:
            report.data['resources_after'] = resources()
        except Exception as exc:
            report.fail('resource_observation_error', repr(exc))
        report.save()
    return report.data


def _boot_seconds(raw: str) -> int:
    value = int(raw)
    if not 1 <= value <= 180:
        raise argparse.ArgumentTypeError('boot timeout must be 1..180 seconds')
    return value


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--runtime', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True, help='New result directory; never overwritten')
    modes = cli.add_mutually_exclusive_group()
    modes.add_argument('--install', action='store_true', help='Download fixed official SDK packages into a new runtime')
    modes.add_argument('--boot', action='store_true', help='One lifetime headless OS attempt for this runtime')
    modes.add_argument('--verify-only', action='store_true',
                       help='Verify all SDK files against preserved official archives without native execution')
    cli.add_argument('--accept-sdk-license', action='store_true')
    cli.add_argument('--resume-install', action='store_true',
                     help='One explicit resume of incomplete owned runtime, preserving byte budget')
    cli.add_argument('--adb-port', type=int, default=15037)
    cli.add_argument('--console-port', type=int, default=5680)
    cli.add_argument('--grpc-port', type=int, default=18554)
    cli.add_argument('--boot-timeout', type=_boot_seconds, default=180)
    cli.add_argument('--rf-bridge-check', action='store_true',
                     help='Run fixed AOSP guest state and synthetic Fleet check during the same owned boot')
    cli.add_argument('--acceleration', choices=('auto', 'off'), default='auto')
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        endpoint = Endpoint(args.adb_port, args.console_port, args.grpc_port)
        result = execute(args.runtime, args.output, install=args.install, boot=args.boot,
            resume_install=args.resume_install,
            verify_only=args.verify_only,
            accept_sdk_license=args.accept_sdk_license, endpoint=endpoint,
            boot_timeout=args.boot_timeout, acceleration=args.acceleration,
            rf_bridge_check=args.rf_bridge_check)
    except BoundaryError as exc:
        print(json.dumps(dict(status='not_run', code=exc.code, detail=str(exc)), ensure_ascii=False))
        return 2
    print(json.dumps(dict(status=result['status'], android_os=result['android_os'],
                         adb_verified=result['adb_verified'], first_failure=result['first_failure'],
                         result=str(Path(result['output']) / 'result.json')), ensure_ascii=False))
    return 0 if result['first_failure'] is None else 2


if __name__ == '__main__':
    raise SystemExit(main())
