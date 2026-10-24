"""Preserve verified CTRL008 bytes in one new host-authorized private packet."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from .control_packet_audit import audit_control_packet, ControlPacketAuditError


_INDEX = "intake-v1.json"
_MARKER = "prepared-receipt.json"
_INDEX_LIMIT = 1024 * 1024
_CHUNK = 64 * 1024
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_DEVICES = {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}
_CODES = frozenset({
    "packet_prepare_invalid_argument", "packet_prepare_path_invalid",
    "packet_prepare_destination_exists", "packet_prepare_verification_failed",
    "packet_prepare_copy_failed", "packet_prepare_source_changed",
    "packet_prepare_receipt_failed",
})
_AUDIT_COUNTERS = frozenset({
    "schema_version", "payload_file_count", "payload_bytes", "json_file_count",
    "zip_crc_checked_count", "zip_entry_count", "zip_uncompressed_bytes",
    "tar_gz_sha_only_count", "state_mutations",
})
_AUDIT_FLAGS = frozenset({
    "public_export_allowed", "source_code_executed",
    "runtime_or_hardware_support_confirmed", "hardware_verified",
})
_AUDIT_FIELDS = _AUDIT_COUNTERS | _AUDIT_FLAGS | {
    "kind", "request_id", "revision", "index_sha256", "zip_crc_status", "read_verification_scope",
}
_WINDOWS_BACKEND_AVAILABLE = os.name == "nt"


class ControlPacketPrepareError(ValueError):
    """Fixed public code without path/content or underlying exception context."""

    def __init__(self, code):
        self.code = code if isinstance(code, str) and code in _CODES else "packet_prepare_invalid_argument"
        super().__init__(self.code)


def _fail(code):
    raise ControlPacketPrepareError(code)


def _identity(info):
    return info.st_dev, info.st_ino


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode


def _not_reparse(info):
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        _fail("packet_prepare_path_invalid")


def _valid_segment(value):
    return (bool(value) and value not in (".", "..") and not value.endswith((".", " "))
            and not any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*\\' for c in value)
            and value.split(".", 1)[0].rstrip(" ").upper() not in _DEVICES)


def _local_path(value):
    if not isinstance(value, (str, os.PathLike)):
        _fail("packet_prepare_invalid_argument")
    value = os.fspath(value)
    if not isinstance(value, str):
        _fail("packet_prepare_invalid_argument")
    if not value or "\x00" in value or value.startswith(("\\\\", "//")):
        _fail("packet_prepare_path_invalid")
    path = Path(value)
    if ".." in path.parts or (path.drive and not path.is_absolute()):
        _fail("packet_prepare_path_invalid")
    path = Path(os.path.abspath(path))
    if not all(_valid_segment(part) for part in path.parts[1:]):
        _fail("packet_prepare_path_invalid")
    return path


class _WindowsIO:
    """One-component, handle-relative NT file operations; never a path-write fallback.

    Directory handles exclude delete sharing for name stability. Relative opens
    also protect against in-place reparse changes, which sharing alone cannot
    exclude. Receipt read pins exclude write/delete sharing until final readback.
    """

    def __init__(self):
        if not _WINDOWS_BACKEND_AVAILABLE:
            raise NotImplementedError("safe private-write backend unavailable")
        import ctypes
        from ctypes import wintypes
        import msvcrt

        self.ctypes, self.types, self.crt = ctypes, wintypes, msvcrt
        self.directories, self.held = {}, []
        c, w = ctypes, wintypes

        class UnicodeString(c.Structure):
            _fields_ = [("Length", w.USHORT), ("MaximumLength", w.USHORT), ("Buffer", w.LPWSTR)]

        class ObjectAttributes(c.Structure):
            _fields_ = [("Length", w.ULONG), ("RootDirectory", w.HANDLE),
                        ("ObjectName", c.POINTER(UnicodeString)), ("Attributes", w.ULONG),
                        ("SecurityDescriptor", c.c_void_p), ("SecurityQualityOfService", c.c_void_p)]

        class IOStatus(c.Structure):
            _fields_ = [("Status", c.c_void_p), ("Information", c.c_size_t)]

        class LinkInformation(c.Structure):
            _fields_ = [("ReplaceIfExists", c.c_ubyte), ("RootDirectory", w.HANDLE),
                        ("FileNameLength", w.ULONG), ("FileName", w.WCHAR * 1)]

        class FileInformation(c.Structure):
            _fields_ = [("Attributes", w.DWORD), ("CreationTime", w.FILETIME),
                        ("AccessTime", w.FILETIME), ("WriteTime", w.FILETIME),
                        ("VolumeSerial", w.DWORD), ("SizeHigh", w.DWORD), ("SizeLow", w.DWORD),
                        ("Links", w.DWORD), ("IndexHigh", w.DWORD), ("IndexLow", w.DWORD)]

        self.UnicodeString, self.ObjectAttributes = UnicodeString, ObjectAttributes
        self.IOStatus, self.LinkInformation, self.FileInformation = IOStatus, LinkInformation, FileInformation
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.native = c.WinDLL("ntdll")
        self.kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p,
                                           w.DWORD, w.DWORD, w.HANDLE]
        self.kernel.CreateFileW.restype = w.HANDLE
        self.kernel.GetDriveTypeW.argtypes = [w.LPCWSTR]
        self.kernel.GetDriveTypeW.restype = w.UINT
        self.kernel.GetFileInformationByHandle.argtypes = [w.HANDLE, c.POINTER(FileInformation)]
        self.kernel.GetFileInformationByHandle.restype = w.BOOL
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.native.NtCreateFile.argtypes = [c.POINTER(w.HANDLE), w.DWORD, c.POINTER(ObjectAttributes),
                                           c.POINTER(IOStatus), c.c_void_p, w.ULONG, w.ULONG,
                                           w.ULONG, w.ULONG, c.c_void_p, w.ULONG]
        self.native.NtCreateFile.restype = w.LONG
        self.native.NtSetInformationFile.argtypes = [w.HANDLE, c.POINTER(IOStatus),
                                                   c.c_void_p, w.ULONG, w.ULONG]
        self.native.NtSetInformationFile.restype = w.LONG
        self.native.RtlNtStatusToDosError.argtypes = [w.LONG]
        self.native.RtlNtStatusToDosError.restype = w.ULONG

    def _status(self, status):
        if status != 0:
            raise self.ctypes.WinError(self.native.RtlNtStatusToDosError(status))

    def info(self, descriptor, *, directory=None):
        native_info = self.FileInformation()
        if not self.kernel.GetFileInformationByHandle(
                self.crt.get_osfhandle(descriptor), self.ctypes.byref(native_info)):
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        if native_info.Attributes & 0x400:
            _fail("packet_prepare_path_invalid")
        result = os.fstat(descriptor)
        _not_reparse(result)
        if directory is True and not stat.S_ISDIR(result.st_mode):
            _fail("packet_prepare_path_invalid")
        if directory is False and not stat.S_ISREG(result.st_mode):
            _fail("packet_prepare_path_invalid")
        return result

    def _descriptor(self, handle, *, directory, writable=False):
        try:
            flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_BINARY | os.O_NOINHERIT
            descriptor = self.crt.open_osfhandle(int(handle), flags)
        except Exception:
            self.kernel.CloseHandle(handle)
            raise
        try:
            self.info(descriptor, directory=directory)
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    def _relative(self, parent, name, *, directory, create=False, access=0x100081, share=7):
        self.info(parent, directory=True)
        if not _valid_segment(name) or "/" in name:
            _fail("packet_prepare_path_invalid")
        c, w = self.ctypes, self.types
        encoded = name.encode("utf-16-le")
        if len(encoded) > 65532:
            _fail("packet_prepare_path_invalid")
        buffer = c.create_string_buffer(encoded + b"\x00\x00")
        unicode = self.UnicodeString(len(encoded), len(encoded) + 2, c.cast(buffer, w.LPWSTR))
        attrs = self.ObjectAttributes(c.sizeof(self.ObjectAttributes), self.crt.get_osfhandle(parent),
                                      c.pointer(unicode), 0x40, None, None)
        result, io = w.HANDLE(), self.IOStatus()
        # OPEN_REPARSE_POINT + synchronous I/O; enforce object type when known.
        options = 0x200020 | (1 if directory is True else 0x40 if directory is False else 0)
        status = self.native.NtCreateFile(
            c.byref(result), access, c.byref(attrs), c.byref(io), None,
            0x10 if directory is True else 0x80, share, 2 if create else 1, options, None, 0)
        self._status(status)
        if create and io.Information != 2:  # FILE_CREATED; no open/replace disposition accepted.
            self.kernel.CloseHandle(result)
            _fail("packet_prepare_copy_failed")
        return self._descriptor(result.value, directory=directory, writable=create and directory is False)

    def directory(self, path, *, create=False):
        if path in self.directories:
            if create:
                raise FileExistsError()
            descriptor = self.directories[path]
            self.info(descriptor, directory=True)
            return descriptor
        if path == Path(path.anchor):
            if create or self.kernel.GetDriveTypeW(str(path)) not in (2, 3, 5, 6):
                _fail("packet_prepare_path_invalid")
            handle = self.kernel.CreateFileW(str(path), 0x1000A1, 3, None, 3, 0x2200000, None)
            if handle == self.ctypes.c_void_p(-1).value:
                raise self.ctypes.WinError(self.ctypes.get_last_error())
            descriptor = self._descriptor(handle, directory=True)
        else:
            descriptor = self._relative(self.directories[path.parent], path.name, directory=True,
                                        create=create, access=0x1000A1, share=3)
        self.directories[path] = descriptor
        self.held.append(descriptor)
        return descriptor

    def create_file(self, path):
        return self._relative(self.directories[path.parent], path.name, directory=False,
                              create=True, access=0xC0100000, share=1)

    def open_read(self, path, *, pin=False):
        descriptor = self._relative(self.directories[path.parent], path.name, directory=False,
                                    share=1 if pin else 7)
        if pin:
            self.held.append(descriptor)
        return descriptor

    def stat_file(self, path):
        descriptor = self._relative(self.directories[path.parent], path.name, directory=None,
                                    access=0x100080)
        try:
            return self.info(descriptor)
        finally:
            os.close(descriptor)

    def link_receipt(self, descriptor, marker):
        self.info(descriptor, directory=False)
        parent = self.directories[marker.parent]
        self.info(parent, directory=True)
        c = self.ctypes
        encoded = marker.name.encode("utf-16-le")
        buffer = c.create_string_buffer(self.LinkInformation.FileName.offset + len(encoded))
        info = c.cast(buffer, c.POINTER(self.LinkInformation)).contents
        info.ReplaceIfExists = 0
        info.RootDirectory = self.crt.get_osfhandle(parent)
        info.FileNameLength = len(encoded)
        c.memmove(c.addressof(buffer) + self.LinkInformation.FileName.offset, encoded, len(encoded))
        io = self.IOStatus()
        self._status(self.native.NtSetInformationFile(
            self.crt.get_osfhandle(descriptor), c.byref(io), buffer, len(buffer), 11))

    def close(self):
        failure = None
        while self.held:
            descriptor = self.held.pop()
            try:
                os.close(descriptor)
            except OSError as error:
                failure = error
        self.directories.clear()
        if failure is not None:
            raise failure


class _Tree:
    """Remember checked directory identities, including lexical root ancestors."""

    def __init__(self, root, backend=None):
        self.root = root
        self.backend = backend
        self.directories = {}
        self.owned_files = {}
        self.directory(root)

    def directory(self, path, *, create=False, missing_ok=False):
        if not path.is_relative_to(self.root):
            _fail("packet_prepare_path_invalid")
        current = Path(path.anchor)
        for part in (None, *path.parts[1:]):
            if part is not None:
                current /= part
            try:
                info = (self.backend.info(self.backend.directory(current), directory=True)
                        if self.backend else os.lstat(current))
            except FileNotFoundError:
                if create and current != self.root and current.is_relative_to(self.root):
                    try:
                        if self.backend:
                            self.backend.directory(current, create=True)
                        else:
                            _fail("packet_prepare_copy_failed")
                    except FileExistsError:
                        pass
                    info = (self.backend.info(self.backend.directory(current), directory=True)
                            if self.backend else os.lstat(current))
                elif missing_ok:
                    return
                else:
                    raise
            _not_reparse(info)
            if not stat.S_ISDIR(info.st_mode):
                _fail("packet_prepare_path_invalid")
            identity = _identity(info)
            if current in self.directories and self.directories[current] != identity:
                _fail("packet_prepare_path_invalid")
            self.directories[current] = identity

    def file_stat(self, path):
        if not path.is_relative_to(self.root):
            _fail("packet_prepare_path_invalid")
        self.directory(path.parent)
        info = self.backend.stat_file(path) if self.backend else os.lstat(path)
        _not_reparse(info)
        if not stat.S_ISREG(info.st_mode):
            _fail("packet_prepare_path_invalid")
        if path in self.owned_files and self.owned_files[path] != _identity(info):
            _fail("packet_prepare_path_invalid")
        return info


def _destination_exists(tree, destination):
    tree.directory(destination.parent, missing_ok=True)
    try:
        if tree.backend and destination.parent not in tree.backend.directories:
            return False
        info = tree.backend.stat_file(destination) if tree.backend else os.lstat(destination)
    except FileNotFoundError:
        return False
    _not_reparse(info)
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        _fail("packet_prepare_path_invalid")
    return True


def _source_stat(tree, path):
    try:
        return tree.file_stat(path)
    except OSError:
        _fail("packet_prepare_source_changed")


@contextmanager
def _checked_read(tree, path, expected_stamp, code):
    descriptor = None
    try:
        try:
            before = tree.file_stat(path)
            if _stamp(before) != expected_stamp:
                _fail(code)
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOINHERIT", 0)
            descriptor = tree.backend.open_read(path) if tree.backend else os.open(path, flags)
            opened = os.fstat(descriptor)
            _not_reparse(opened)
            if not stat.S_ISREG(opened.st_mode) or _stamp(opened) != expected_stamp:
                _fail(code)
            if _stamp(tree.file_stat(path)) != expected_stamp:
                _fail(code)
        except OSError:
            _fail(code)
        yield descriptor
        try:
            if _stamp(os.fstat(descriptor)) != expected_stamp or _stamp(tree.file_stat(path)) != expected_stamp:
                _fail(code)
        except OSError:
            _fail(code)
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_chunk(descriptor, size, code):
    try:
        return os.read(descriptor, size)
    except OSError:
        _fail(code)


def _read_bytes(tree, path, expected_stamp, limit, code):
    data = bytearray()
    with _checked_read(tree, path, expected_stamp, code) as descriptor:
        while True:
            chunk = _read_chunk(descriptor, min(_CHUNK, limit - len(data) + 1), code)
            if not chunk:
                return bytes(data)
            data.extend(chunk)
            if len(data) > limit:
                _fail(code)


def _read_descriptor(descriptor, limit, code):
    os.lseek(descriptor, 0, os.SEEK_SET)
    data = bytearray()
    while True:
        chunk = _read_chunk(descriptor, min(_CHUNK, limit - len(data) + 1), code)
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        if len(data) > limit:
            _fail(code)


@contextmanager
def _new_file(tree, path):
    tree.directory(path.parent, create=True)
    if tree.backend is None:
        _fail("packet_prepare_copy_failed")
    descriptor = tree.backend.create_file(path)
    try:
        info = os.fstat(descriptor)
        _not_reparse(info)
        if not stat.S_ISREG(info.st_mode):
            _fail("packet_prepare_path_invalid")
        tree.owned_files[path] = _identity(info)
        tree.file_stat(path)
        yield descriptor
        if _identity(os.fstat(descriptor)) != tree.owned_files[path]:
            _fail("packet_prepare_path_invalid")
        tree.file_stat(path)
    finally:
        os.close(descriptor)


def _write_all(descriptor, data, code):
    view, position, checksum = memoryview(data), 0, hashlib.sha256()
    while position < len(view):
        written = os.write(descriptor, view[position:position + _CHUNK])
        if type(written) is not int or written <= 0 or written > min(_CHUNK, len(view) - position):
            _fail(code)
        checksum.update(view[position:position + written])
        position += written
    return checksum.hexdigest()


def _copy_payload(source_tree, destination_tree, relative, expected_stamp, size, expected_hash):
    source = source_tree.root.joinpath(*relative)
    destination = destination_tree.root.joinpath(*relative)
    length, checksum = 0, hashlib.sha256()
    with _checked_read(source_tree, source, expected_stamp, "packet_prepare_source_changed") as reader:
        with _new_file(destination_tree, destination) as writer:
            while True:
                chunk = _read_chunk(reader, _CHUNK, "packet_prepare_source_changed")
                if not chunk:
                    break
                length += len(chunk)
                if length > size:
                    _fail("packet_prepare_source_changed")
                checksum.update(chunk)
                if _write_all(writer, chunk, "packet_prepare_copy_failed") != hashlib.sha256(chunk).hexdigest():
                    _fail("packet_prepare_copy_failed")
            if length != size or checksum.hexdigest() != expected_hash:
                _fail("packet_prepare_source_changed")
            if os.fstat(writer).st_size != size:
                _fail("packet_prepare_copy_failed")
    return _stamp(destination_tree.file_stat(destination))


def _write_bytes(tree, path, raw, code, *, sync=False):
    with _new_file(tree, path) as descriptor:
        if _write_all(descriptor, raw, code) != hashlib.sha256(raw).hexdigest():
            _fail(code)
        if os.fstat(descriptor).st_size != len(raw):
            _fail(code)
        if sync:
            os.fsync(descriptor)
    return _stamp(tree.file_stat(path))


def _audit_snapshot(summary, expected_hash, code):
    if (type(summary) is not dict or set(summary) != _AUDIT_FIELDS
            or any(type(summary[key]) is not int or summary[key] < 0 for key in _AUDIT_COUNTERS)
            or any(summary[key] is not False for key in _AUDIT_FLAGS)
            or summary["schema_version"] != 1 or summary["state_mutations"] != 0
            or summary["kind"] != "control_packet_audit"
            or summary["request_id"] != "DEV-CONTROL-SOURCES-008"
            or summary["index_sha256"] != expected_hash
            or not isinstance(summary["revision"], str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,149}", summary["revision"], re.ASCII)
            or summary["zip_crc_status"] not in ("passed", "not_present")
            or summary["read_verification_scope"] != "listed_bytes_json_zip_crc_at_read_time"):
        _fail(code)
    return json.loads(json.dumps(summary, ensure_ascii=True, allow_nan=False))


def prepare_control_packet(source_dir, *, expected_index_sha256, workspace_root, packet_id) -> dict:
    """Create a new private copy; valid complete receipt is the completion marker.

    Existing destinations/files and failed partial copies are never overwritten
    or removed. The host must authorize the independent development workspace.
    """
    code, backend = "packet_prepare_invalid_argument", None
    try:
        if (not isinstance(expected_index_sha256, str) or not _HASH.fullmatch(expected_index_sha256)
                or not isinstance(packet_id, str) or not _ID.fullmatch(packet_id)
                or not _valid_segment(packet_id)):
            _fail(code)
        source, workspace = _local_path(source_dir), _local_path(workspace_root)
        code = "packet_prepare_copy_failed"
        backend = _WindowsIO()
        code = "packet_prepare_path_invalid"
        source_tree, workspace_tree = _Tree(source, backend), _Tree(workspace, backend)
        destination = workspace / ".local" / "control-packets" / packet_id
        exists = _destination_exists(workspace_tree, destination)
        # Compare both lexical paths and held object identities, without resolving
        # names again through a possibly changed namespace or short-name alias.
        source_identity = source_tree.directories[source]
        destination_identity = (_identity(backend.stat_file(destination)) if exists else None)
        if (source.is_relative_to(destination) or destination.is_relative_to(source)
                or source_identity in workspace_tree.directories.values()
                or (exists and destination_identity in source_tree.directories.values())):
            _fail("packet_prepare_path_invalid")
        if exists:
            _fail("packet_prepare_destination_exists")

        code = "packet_prepare_verification_failed"
        try:
            initial = audit_control_packet(source, expected_index_sha256=expected_index_sha256)
        except ControlPacketAuditError as error:
            if error.code == "packet_path_invalid":
                _fail("packet_prepare_path_invalid")
            raise
        initial = _audit_snapshot(initial, expected_index_sha256, code)
        code = "packet_prepare_source_changed"
        index_path = source / _INDEX
        source_stamps = {index_path: _stamp(_source_stat(source_tree, index_path))}
        raw_index = _read_bytes(source_tree, index_path, source_stamps[index_path], _INDEX_LIMIT, code)
        if hashlib.sha256(raw_index).hexdigest() != expected_index_sha256:
            _fail(code)
        # These exact pinned bytes have already passed audit's strict JSON contract.
        index = json.loads(raw_index.decode("utf-8"))
        rows = []
        for row in index["files"]:
            relative = tuple(row["path"].split("/"))
            if relative[0].casefold() == _MARKER:
                _fail("packet_prepare_path_invalid")
            path = source.joinpath(*relative)
            source_stamps[path] = _stamp(_source_stat(source_tree, path))
            rows.append((relative, row["bytes"], row["sha256"]))

        code = "packet_prepare_copy_failed"
        workspace_tree.directory(destination.parent, create=True)
        try:
            backend.directory(destination, create=True)
        except FileExistsError:
            _destination_exists(workspace_tree, destination)
            _fail("packet_prepare_destination_exists")
        workspace_tree.directory(destination)
        destination_tree = _Tree(destination, backend)
        # Keep workspace/parent identities, not only the new packet's directory.
        destination_tree.directories.update(workspace_tree.directories)
        destination_stamps = {}
        for relative, size, checksum in rows:
            original = source.joinpath(*relative)
            copied = destination.joinpath(*relative)
            destination_stamps[copied] = _copy_payload(
                source_tree, destination_tree, relative, source_stamps[original], size, checksum)
        copied_index = destination / _INDEX
        destination_stamps[copied_index] = _write_bytes(destination_tree, copied_index, raw_index, code)

        code = "packet_prepare_source_changed"
        final_source = _audit_snapshot(
            audit_control_packet(source, expected_index_sha256=expected_index_sha256), expected_index_sha256, code)
        if final_source != initial:
            _fail(code)
        for path, expected in source_stamps.items():
            if _stamp(_source_stat(source_tree, path)) != expected:
                _fail(code)
        code = "packet_prepare_verification_failed"
        destination_tree.directory(destination)
        final_destination = _audit_snapshot(
            audit_control_packet(destination, expected_index_sha256=expected_index_sha256), expected_index_sha256, code)
        if final_destination != initial:
            _fail(code)
        for path, expected in destination_stamps.items():
            if _stamp(destination_tree.file_stat(path)) != expected:
                _fail(code)

        code = "packet_prepare_receipt_failed"
        receipt = {
            "schema_version": 1, "kind": "control_packet_prepare", "packet_id": packet_id,
            "destination_relpath": ".local/control-packets/" + packet_id,
            "index_sha256": expected_index_sha256, "state": "complete", "audit_summary": initial,
            "support_status": "not_assessed", "public_export_allowed": False,
            "source_code_executed": False, "runtime_or_hardware_support_confirmed": False,
            "hardware_verified": False,
        }
        raw_receipt = (json.dumps(receipt, ensure_ascii=True, allow_nan=False,
                                  sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        detached = json.loads(raw_receipt)
        temporary = destination / (".prepared-receipt-" + uuid.uuid4().hex + ".tmp")
        temporary_stamp = _write_bytes(destination_tree, temporary, raw_receipt, code, sync=True)
        pinned = backend.open_read(temporary, pin=True)
        if _stamp(backend.info(pinned, directory=False)) != temporary_stamp:
            _fail(code)
        if _read_descriptor(pinned, len(raw_receipt), code) != raw_receipt:
            _fail(code)
        destination_tree.directory(destination)
        if _stamp(destination_tree.file_stat(temporary)) != temporary_stamp:
            _fail(code)
        marker = destination / _MARKER
        # FileLinkInformation binds the held validated file object to the held
        # parent directory with ReplaceIfExists=False; no pathname source lookup.
        backend.link_receipt(pinned, marker)
        published = backend.open_read(marker)
        try:
            if _stamp(backend.info(published, directory=False)) != temporary_stamp:
                _fail(code)
            if _read_descriptor(published, len(raw_receipt), code) != raw_receipt:
                _fail(code)
            if _stamp(destination_tree.file_stat(marker)) != temporary_stamp:
                _fail(code)
        finally:
            os.close(published)
        backend.close()
        backend = None
        return detached
    except ControlPacketPrepareError as error:
        code = error.code
    except Exception:
        pass
    finally:
        if backend is not None:
            try:
                backend.close()
            except Exception:
                # An operation already failed; do not expose a secondary native
                # cleanup exception or turn that failure into completion.
                pass
    # No raw audit/I/O exception remains in the public exception's context.
    raise ControlPacketPrepareError(code) from None
