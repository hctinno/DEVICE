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


class _Tree:
    """Remember checked directory identities, including lexical root ancestors."""

    def __init__(self, root):
        self.root = root
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
                info = os.lstat(current)
            except FileNotFoundError:
                if create and current != self.root and current.is_relative_to(self.root):
                    try:
                        os.mkdir(current, 0o700)
                    except FileExistsError:
                        pass
                    info = os.lstat(current)
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
        info = os.lstat(path)
        _not_reparse(info)
        if not stat.S_ISREG(info.st_mode):
            _fail("packet_prepare_path_invalid")
        if path in self.owned_files and self.owned_files[path] != _identity(info):
            _fail("packet_prepare_path_invalid")
        return info


def _destination_exists(tree, destination):
    tree.directory(destination.parent, missing_ok=True)
    try:
        info = os.lstat(destination)
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
            descriptor = os.open(path, flags)
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


@contextmanager
def _new_file(tree, path):
    tree.directory(path.parent, create=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0)
    descriptor = os.open(path, flags, 0o600)
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
    code = "packet_prepare_invalid_argument"
    try:
        if (not isinstance(expected_index_sha256, str) or not _HASH.fullmatch(expected_index_sha256)
                or not isinstance(packet_id, str) or not _ID.fullmatch(packet_id)
                or not _valid_segment(packet_id)):
            _fail(code)
        source, workspace = _local_path(source_dir), _local_path(workspace_root)
        code = "packet_prepare_path_invalid"
        source_tree, workspace_tree = _Tree(source), _Tree(workspace)
        destination = workspace / ".local" / "control-packets" / packet_id
        exists = _destination_exists(workspace_tree, destination)
        # Resolve only after lexical ancestors have passed the reparse checks.
        canonical_source, canonical_destination = source.resolve(), destination.resolve()
        if (canonical_source.is_relative_to(canonical_destination)
                or canonical_destination.is_relative_to(canonical_source)):
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
            os.mkdir(destination, 0o700)
        except FileExistsError:
            _destination_exists(workspace_tree, destination)
            _fail("packet_prepare_destination_exists")
        workspace_tree.directory(destination)
        destination_tree = _Tree(destination)
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
        if _read_bytes(destination_tree, temporary, temporary_stamp, len(raw_receipt), code) != raw_receipt:
            _fail(code)
        destination_tree.directory(destination)
        if _stamp(destination_tree.file_stat(temporary)) != temporary_stamp:
            _fail(code)
        # Atomic no-replace file publication. Keep the completed temporary inode;
        # neither failed copies nor successful temporary evidence are deleted.
        os.link(temporary, destination / _MARKER, follow_symlinks=False)
        return detached
    except ControlPacketPrepareError as error:
        code = error.code
    except Exception:
        pass
    # No raw audit/I/O exception remains in the public exception's context.
    raise ControlPacketPrepareError(code) from None
