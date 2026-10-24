"""Read-only, bounded verification of a host-selected control-source packet.

This module imports no collected source and grants no runtime/hardware support.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import zipfile
import zlib


_INDEX_NAME = "intake-v1.json"
_REQUEST_ID = "DEV-CONTROL-SOURCES-008"
_INDEX_LIMIT = 1024 * 1024
_FILE_LIMIT = 64 * 1024 * 1024
_TOTAL_LIMIT = 128 * 1024 * 1024
_JSON_LIMIT = 8 * 1024 * 1024
_FILE_COUNT = 128
_ZIP_ENTRIES = 2000
_CHUNK = 64 * 1024
_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_REVISION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z", re.ASCII)
_DEVICES = {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"} | {
    prefix + suffix for prefix in ("COM", "LPT") for suffix in "123456789¹²³"
}
_ERROR_CODES = frozenset({
    "packet_invalid_argument", "packet_unavailable", "packet_index_invalid",
    "packet_index_mismatch", "packet_index_changed", "packet_path_invalid",
    "packet_limit_exceeded", "packet_payload_mismatch", "packet_json_invalid",
    "packet_zip_invalid",
})


class ControlPacketAuditError(ValueError):
    """A fixed public code, without source content, paths or chained I/O errors."""

    def __init__(self, code):
        self.code = code if code in _ERROR_CODES else "packet_invalid_argument"
        super().__init__(self.code)


def _fail(code):
    raise ControlPacketAuditError(code)


def _segment_valid(segment):
    return (bool(segment) and segment not in (".", "..")
            and not segment.endswith((".", " "))
            and not any(ord(char) < 32 or ord(char) == 127 or char in '<>:"|?*\\'
                        for char in segment)
            and segment.split(".", 1)[0].rstrip(" ").upper() not in _DEVICES)


def _packet_root(value):
    if not isinstance(value, (str, os.PathLike)):
        _fail("packet_invalid_argument")
    value = os.fspath(value)
    if (not isinstance(value, str) or not value or "\x00" in value
            or value.startswith(("\\\\", "//"))):
        _fail("packet_invalid_argument")
    path = Path(value)
    if (path.drive and not path.is_absolute()) or ".." in path.parts:
        _fail("packet_invalid_argument")
    path = Path(os.path.abspath(path))
    if not all(_segment_valid(part) for part in path.parts[1:]):
        _fail("packet_invalid_argument")
    return path


def _manifest_path(value):
    if (not isinstance(value, str) or value.startswith("/") or "\\" in value
            or not all(_segment_valid(part) for part in value.split("/"))
            or value.casefold() == _INDEX_NAME):
        _fail("packet_path_invalid")
    return tuple(value.split("/"))


def _not_reparse(info):
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & 0x400):
        _fail("packet_path_invalid")


def _checked_stat(root, parts):
    # Do not resolve(): it would hide a symlink/junction in the lexical chain.
    current = Path(root.anchor)
    for part in (None, *root.parts[1:], *parts[:-1]):
        if part is not None:
            current /= part
        info = os.lstat(current)
        _not_reparse(info)
        if not stat.S_ISDIR(info.st_mode):
            _fail("packet_path_invalid")
    current /= parts[-1]
    info = os.lstat(current)
    _not_reparse(info)
    if not stat.S_ISREG(info.st_mode):
        _fail("packet_path_invalid")
    return current, info


def _identity(info):
    return info.st_dev, info.st_ino


@contextmanager
def _open_read(root, parts, limit):
    path, before = _checked_stat(root, parts)
    if before.st_size > limit:
        _fail("packet_limit_exceeded")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOINHERIT", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        _not_reparse(opened)
        if not stat.S_ISREG(opened.st_mode) or _identity(before) != _identity(opened):
            _fail("packet_path_invalid")
        _, checked = _checked_stat(root, parts)
        if _identity(opened) != _identity(checked):
            _fail("packet_path_invalid")
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            yield stream
            _, after = _checked_stat(root, parts)
            if _identity(opened) != _identity(after):
                _fail("packet_path_invalid")
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _bounded_bytes(stream, limit):
    data = bytearray()
    while True:
        chunk = stream.read(min(_CHUNK, limit - len(data) + 1))
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        if len(data) > limit:
            _fail("packet_limit_exceeded")


def _strict_json(raw, code):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite number")
        return number

    def nonfinite(_):
        raise ValueError("nonfinite constant")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_float=finite, parse_constant=nonfinite)
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        _fail(code)


def _index_rows(index):
    if (not isinstance(index, dict) or index.get("request_id") != _REQUEST_ID
            or not isinstance(index.get("revision"), str)
            or not _REVISION.fullmatch(index["revision"])
            or any(index.get(key) is not False for key in (
                "source_code_executed", "runtime_or_hardware_support_confirmed",
                "public_export_allowed"))):
        _fail("packet_index_invalid")
    rows = index.get("files")
    if not isinstance(rows, list) or not rows:
        _fail("packet_index_invalid")
    if len(rows) > _FILE_COUNT:
        _fail("packet_limit_exceeded")
    seen, total, validated = set(), 0, []
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("bytes")) is not int
                or row["bytes"] < 0 or not isinstance(row.get("sha256"), str)
                or not _HEX.fullmatch(row["sha256"])):
            _fail("packet_index_invalid")
        parts = _manifest_path(row.get("path"))
        key = row["path"].casefold()
        if key in seen:
            _fail("packet_path_invalid")
        seen.add(key)
        total += row["bytes"]
        limit = _JSON_LIMIT if parts[-1].lower().endswith(".json") else _FILE_LIMIT
        if row["bytes"] > limit or total > _TOTAL_LIMIT:
            _fail("packet_limit_exceeded")
        validated.append((parts, row["bytes"], row["sha256"]))
    return validated


def _zip_supported_header(flags, method):
    # Deflate options, data descriptor and UTF-8 are the supported v1 flags.
    if (flags & ~0x080E or method not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            or (method == zipfile.ZIP_STORED and flags & 6)):
        _fail("packet_zip_invalid")


def _zip_extra_without_zip64(raw):
    position = 0
    while position < len(raw):
        if position + 4 > len(raw):
            _fail("packet_zip_invalid")
        field, length = struct.unpack_from("<HH", raw, position)
        position += 4
        if field == 1 or position + length > len(raw):
            _fail("packet_zip_invalid")
        position += length


def _zip_directory_preflight(stream, entry_budget):
    # Bound directory allocation before ZipFile builds its list of ZipInfo objects.
    stream.seek(0, os.SEEK_END)
    length = stream.tell()
    stream.seek(max(0, length - 65557))
    tail = stream.read(65557)
    position = tail.rfind(b"PK\x05\x06")
    if position < 0 or len(tail) - position < 22:
        _fail("packet_zip_invalid")
    _, disk, directory_disk, on_disk, count, size, offset, comment = struct.unpack_from(
        "<4s4H2IH", tail, position)
    if count > entry_budget:
        _fail("packet_limit_exceeded")
    if (disk or directory_disk or on_disk != count or count == 65535
            or size == 0xFFFFFFFF or offset == 0xFFFFFFFF
            or position + 22 + comment != len(tail)):
        _fail("packet_zip_invalid")
    end_offset = length - len(tail) + position
    if size > length or offset + size > length or size > end_offset:
        _fail("packet_zip_invalid")
    if end_offset >= 20:
        stream.seek(end_offset - 20)
        if stream.read(4) == b"PK\x06\x07":
            _fail("packet_zip_invalid")
    # The EOCD count itself can lie. Walk fixed headers with bounded reads before
    # ZipFile allocates even one ZipInfo or decodes attacker-controlled names.
    position, actual_count = end_offset - size, 0
    while position < end_offset:
        if position + 46 > end_offset:
            _fail("packet_zip_invalid")
        stream.seek(position)
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            _fail("packet_zip_invalid")
        flags, method = struct.unpack_from("<HH", header, 8)
        _zip_supported_header(flags, method)
        compressed, uncompressed = struct.unpack_from("<II", header, 20)
        disk_start = struct.unpack_from("<H", header, 34)[0]
        local_offset = struct.unpack_from("<I", header, 42)[0]
        if 0xFFFFFFFF in (compressed, uncompressed, local_offset) or disk_start == 0xFFFF:
            _fail("packet_zip_invalid")
        actual_count += 1
        if actual_count > entry_budget:
            _fail("packet_limit_exceeded")
        lengths = struct.unpack_from("<HHH", header, 28)
        next_position = position + 46 + sum(lengths)
        if next_position > end_offset:
            _fail("packet_zip_invalid")
        stream.seek(position + 46 + lengths[0])
        _zip_extra_without_zip64(stream.read(lengths[1]))
        position = next_position
    if actual_count != count:
        _fail("packet_zip_invalid")
    return count


def _zip_member_crc(stream, member):
    stream.seek(member.header_offset)
    header = stream.read(30)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        _fail("packet_zip_invalid")
    flags, method = struct.unpack_from("<HH", header, 6)
    _zip_supported_header(flags, method)
    if flags != member.flag_bits or method != member.compress_type:
        _fail("packet_zip_invalid")
    local_crc, local_compressed, local_uncompressed = struct.unpack_from("<III", header, 14)
    if 0xFFFFFFFF in (local_compressed, local_uncompressed):
        _fail("packet_zip_invalid")
    if not flags & 8 and (local_crc != member.CRC or local_compressed != member.compress_size
                          or local_uncompressed != member.file_size):
        _fail("packet_zip_invalid")
    name_length, extra_length = struct.unpack_from("<HH", header, 26)
    stream.seek(member.header_offset + 30 + name_length)
    extra = stream.read(extra_length)
    if len(extra) != extra_length:
        _fail("packet_zip_invalid")
    _zip_extra_without_zip64(extra)
    remaining, produced, crc = member.compress_size, 0, 0
    decoder = zlib.decompressobj(-zlib.MAX_WBITS) if member.compress_type == zipfile.ZIP_DEFLATED else None
    while remaining:
        compressed = stream.read(min(_CHUNK, remaining))
        if not compressed:
            _fail("packet_zip_invalid")
        remaining -= len(compressed)
        while True:
            if decoder is None:
                output = compressed
            else:
                output = decoder.decompress(compressed, min(_CHUNK, member.file_size - produced + 1))
            produced += len(output)
            crc = zlib.crc32(output, crc)
            if produced > _FILE_LIMIT:
                _fail("packet_limit_exceeded")
            if produced > member.file_size:
                _fail("packet_zip_invalid")
            if decoder is None:
                break
            if decoder.eof:
                if decoder.unused_data or remaining:
                    _fail("packet_zip_invalid")
                break
            compressed = decoder.unconsumed_tail
            if not compressed:
                break
    if (produced != member.file_size or crc & 0xFFFFFFFF != member.CRC
            or (decoder is not None and not decoder.eof)):
        _fail("packet_zip_invalid")
    return produced


def _zip_crc(stream, entry_budget, byte_budget):
    declared_count = _zip_directory_preflight(stream, entry_budget)
    with zipfile.ZipFile(stream) as archive:
        members = archive.infolist()
        if len(members) != declared_count:
            _fail("packet_zip_invalid")
        if len(members) > entry_budget:
            _fail("packet_limit_exceeded")
        expanded = 0
        for member in members:
            expanded += member.file_size
            if member.file_size > _FILE_LIMIT or expanded > byte_budget:
                _fail("packet_limit_exceeded")
            if (member.flag_bits & 1 or member.compress_type not in (
                    zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or member.compress_size < 0 or member.compress_size > _FILE_LIMIT):
                _fail("packet_zip_invalid")
        for member in members:
            # Validate local header/name/overlap/encryption without decompressing.
            with archive.open(member):
                pass
            _zip_member_crc(stream, member)
        return len(members), expanded


def _audit(root, expected):
    with _open_read(root, (_INDEX_NAME,), _INDEX_LIMIT) as stream:
        raw = _bounded_bytes(stream, _INDEX_LIMIT)
    if hashlib.sha256(raw).hexdigest() != expected:
        _fail("packet_index_mismatch")
    index = _strict_json(raw, "packet_index_invalid")
    rows = _index_rows(index)
    total = json_count = zip_count = zip_entries = zip_bytes = tar_count = 0
    for parts, expected_bytes, expected_sha in rows:
        name = parts[-1].lower()
        is_json = name.endswith(".json")
        json_data = bytearray() if is_json else None
        length, checksum = 0, hashlib.sha256()
        with _open_read(root, parts, _JSON_LIMIT if is_json else _FILE_LIMIT) as stream:
            while True:
                chunk = stream.read(_CHUNK)
                if not chunk:
                    break
                length += len(chunk)
                if length > (_JSON_LIMIT if is_json else _FILE_LIMIT) or total + length > _TOTAL_LIMIT:
                    _fail("packet_limit_exceeded")
                checksum.update(chunk)
                if json_data is not None:
                    json_data.extend(chunk)
            if length != expected_bytes or checksum.hexdigest() != expected_sha:
                _fail("packet_payload_mismatch")
            if is_json:
                _strict_json(bytes(json_data), "packet_json_invalid")
                json_count += 1
            if name.endswith(".zip"):
                try:
                    entries, expanded = _zip_crc(stream, _ZIP_ENTRIES - zip_entries,
                                                 _TOTAL_LIMIT - zip_bytes)
                except ControlPacketAuditError:
                    raise
                except (OSError, ValueError, EOFError, RuntimeError, NotImplementedError,
                        zipfile.BadZipFile, zlib.error, struct.error):
                    _fail("packet_zip_invalid")
                zip_count += 1
                zip_entries += entries
                zip_bytes += expanded
            if name.endswith((".tar.gz", ".tgz")):
                tar_count += 1
        total += length
    # Recheck the exact original index after payload work; no filesystem snapshot claim.
    try:
        with _open_read(root, (_INDEX_NAME,), _INDEX_LIMIT) as stream:
            final_raw = _bounded_bytes(stream, _INDEX_LIMIT)
    except (ControlPacketAuditError, OSError, ValueError):
        _fail("packet_index_changed")
    if final_raw != raw or hashlib.sha256(final_raw).hexdigest() != expected:
        _fail("packet_index_changed")
    return {
        "schema_version": 1, "kind": "control_packet_audit", "request_id": _REQUEST_ID,
        "revision": index["revision"], "index_sha256": expected,
        "payload_file_count": len(rows), "payload_bytes": total, "json_file_count": json_count,
        "zip_crc_checked_count": zip_count, "zip_entry_count": zip_entries,
        "zip_uncompressed_bytes": zip_bytes, "zip_crc_status": "passed" if zip_count else "not_present",
        "tar_gz_sha_only_count": tar_count,
        "read_verification_scope": "listed_bytes_json_zip_crc_at_read_time",
        "public_export_allowed": False, "source_code_executed": False,
        "runtime_or_hardware_support_confirmed": False, "hardware_verified": False,
        "state_mutations": 0,
    }


def audit_control_packet(packet_dir, *, expected_index_sha256):
    """Verify listed local bytes and return a detached, content-free summary.

    ZIP v1 supports STORED/DEFLATED, without encryption or ZIP64. Archive member
    paths/links are byte-checked only; nothing is imported, executed or extracted.
    """
    try:
        if not isinstance(expected_index_sha256, str) or not _HEX.fullmatch(expected_index_sha256):
            _fail("packet_invalid_argument")
        return _audit(_packet_root(packet_dir), expected_index_sha256)
    except ControlPacketAuditError as error:
        code = error.code
    except (OSError, ValueError, TypeError, OverflowError):
        code = "packet_unavailable"
    # Raise outside the handler so even __context__ contains no original exception.
    raise ControlPacketAuditError(code) from None
