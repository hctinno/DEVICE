"""Verified workspace CAS copies. Never deletes/moves sources or authorizes deletion.

Catalogs are pinned inputs, not archived bytes. Every copied source is reopened
without following a leaf reparse point, checked by native identity, streamed,
and checked again. Existing blobs are rehashed; resumptions never trust a name.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import collections
import base64
import ctypes
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import stat
import uuid

CHUNK = 1024 * 1024
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_DEVICE = re.compile(r"^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|CLOCK\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I)


class ArchiveError(ValueError):
    """A bounded error code; raw source contents are never included."""


def _fail(code):
    raise ArchiveError("workspace_archive_" + code)


def validate_relative_path(value, *, root=False):
    if root and value == ".":
        return ()
    if (type(value) is not str or not value or "\\" in value or value.startswith("/")
            or any(not part or part in (".", "..") or part.endswith((" ", "."))
                   or _DEVICE.match(part) or any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                   for part in value.split("/"))):
        _fail("relative_path")
    return tuple(value.split("/"))


def _absolute(value):
    if not isinstance(value, (str, os.PathLike)):
        _fail("absolute_path")
    text = os.fspath(value)
    if not isinstance(text, str) or not text or text.strip() != text or text.startswith(("\\\\", "//")):
        _fail("absolute_path")
    path = Path(text)
    if not path.is_absolute():
        _fail("absolute_path")
    tail = ntpath.splitdrive(text)[1] if os.name == "nt" else text
    if any(part in (".", "..") or (part and (part.endswith((" ", ".")) or _DEVICE.match(part)
            or any(ord(c) < 32 or c in '<>:"|?*' for c in part))) for part in re.split(r"[\\/]", tail)):
        _fail("absolute_path")
    return path


def _key(path):
    return os.path.normcase(str(path)).replace("/", "\\").rstrip("\\")


def _inside(path, parent):
    return _key(path) == _key(parent) or _key(path).startswith(_key(parent) + "\\")


def _extended(path):
    text = str(path)
    return "\\\\?\\" + text if os.name == "nt" and not text.startswith("\\\\?\\") else text


def _reparse(value):
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, "st_file_attributes", 0) & 0x400)


def _no_reparse(path, *, missing=False):
    for item in (*reversed(path.parents), path):
        try:
            value = os.lstat(_extended(item))
        except FileNotFoundError:
            if missing:
                continue
            _fail("path_missing")
        if _reparse(value) or (item != path and not stat.S_ISDIR(value.st_mode)):
            _fail("reparse_path")


def _digest(path):
    digest = hashlib.sha256()
    with open(_extended(path), "rb") as stream:
        while data := stream.read(CHUNK):
            digest.update(data)
    return digest.hexdigest()


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            _fail("duplicate_json_key")
        value[key] = item
    return value


def _json(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_constant=lambda _: _fail("json_constant"))
    except (json.JSONDecodeError, UnicodeError):
        _fail("json")


def load_archive_document(path, *, expected_sha256=None):
    """Bounded operator config/proof, not a source data-file decoder."""
    path = _absolute(path)
    _no_reparse(path)
    with _reader(path) as (stream, current, before):
        raw = stream.read(8 * CHUNK + 1)
        if len(raw) > 8 * CHUNK or before != current() or before["directory"]:
            _fail("document_size_or_unstable")
    if expected_sha256 is not None and (not _SHA.fullmatch(str(expected_sha256))
            or hashlib.sha256(raw).hexdigest() != expected_sha256):
        _fail("document_sha")
    try:
        return _json(raw.decode("utf-8-sig"))
    except UnicodeError:
        _fail("document_utf8")


def _rows(path, pin):
    if type(pin) is not str or not _SHA.fullmatch(pin):
        _fail("manifest_pin")
    _no_reparse(path)
    digest = hashlib.sha256()
    with open(_extended(path), "rb") as stream:
        while line := stream.readline(CHUNK + 1):
            if len(line) > CHUNK or not line.endswith(b"\n"):
                _fail("manifest_line")
            digest.update(line)
            try:
                row = _json(line.decode("utf-8"))
            except UnicodeError:
                _fail("manifest_utf8")
            if not isinstance(row, dict):
                _fail("manifest_row")
            yield row
    if digest.hexdigest() != pin:
        _fail("manifest_sha")


def _signature(value):
    return tuple(value.get(key) for key in ("st_dev", "st_ino", "bytes", "mtime_ns"))


def _valid_info(value):
    if not isinstance(value, dict) or any(type(value.get(key)) is not int or value[key] < 0
            for key in ("st_dev", "st_ino", "bytes", "mtime_ns")):
        _fail("identity_metadata")


def _stream_name(name):
    if (type(name) is not str or not name.startswith(":") or not name.endswith(":$DATA")
            or not name[1:-6] or any(ord(c) < 32 or c in '\\/:<>"|?*' for c in name[1:-6])):
        _fail("stream_name")
    return name


@dataclass
class ArchivePlan:
    spec: dict
    root: Path
    directories: dict
    reparse_info: dict
    paths: dict
    children: dict
    streams: dict
    unknown: set
    counts: dict
    mappings: tuple
    mtime_exceptions: set

    def summary(self):
        return dict(root=str(self.root), executed=False, deletion_authorized=False,
                    files=self.counts["files"], bytes=self.counts["bytes"],
                    ads_streams=sum(map(len, self.streams.values())),
                    unresolved_reparse=sorted(self.unknown),
                    base_sha256=self.spec["base_sha256"], ads_sha256=self.spec["ads_sha256"])

    def actual(self, relative):
        logical = self.root.joinpath(*validate_relative_path(relative, root=True))
        choices = [m for m in self.mappings if _inside(logical, m["from"])]
        if choices:
            mapping = max(choices, key=lambda m: len(_key(m["from"])))
            suffix = str(logical)[len(str(mapping["from"])):].lstrip("\\/")
            return mapping["to"] / suffix if suffix else mapping["to"]
        return logical

    def storage(self, relative):
        logical = self.root.joinpath(*validate_relative_path(relative, root=True))
        choices = [m for m in self.mappings if _inside(logical, m["from"])]
        return max(choices, key=lambda m: len(_key(m["from"])))["storage"] if choices else "copy"


def _pinned_document(reference):
    if not isinstance(reference, dict) or not _SHA.fullmatch(str(reference.get("sha256"))):
        _fail("evidence_pin")
    return load_archive_document(reference.get("path"), expected_sha256=reference["sha256"])


def _move_identity(value, plan, relative, original, actual):
    """Read pinned original coordinator reports; no link/SDK target is probed."""
    proof = _pinned_document(dict(path=value.get("evidence"), sha256=value.get("evidence_sha256")))
    if not isinstance(proof, dict):
        _fail("move_evidence")
    kind = value.get("evidence_kind", "normalized-native-move")
    reported_changes = None
    if kind == "normalized-native-move":
        if (proof.get("operation") != "native-move" or proof.get("status") != "complete"
                or _key(proof.get("from", "")) != _key(original) or _key(proof.get("to", "")) != _key(actual)
                or proof.get("before_identity") != proof.get("after_identity")):
            _fail("move_evidence")
        identity = proof.get("before_identity")
    elif kind == "native-reparse-report":
        matches = [row for row in proof.get("rows", []) if isinstance(row, dict)
                   and _key(row.get("source", "")) == _key(original)
                   and _key(row.get("destination", "")) == _key(actual)]
        if len(matches) != 1 or plan.paths[relative] != "reparse":
            _fail("reparse_move_row")
        row = matches[0]
        before, after = row.get("before"), row.get("after")
        if (not isinstance(before, dict) or before != after or row.get("relative") != relative
                or _key(row.get("root", "")) != _key(plan.root)
                or before.get("mtime_ns") != plan.reparse_info[relative]["mtime_ns"]
                or before.get("tag") != plan.reparse_info[relative].get("reparse_tag")
                or before.get("target") != plan.reparse_info[relative].get("target")
                or not _SHA.fullmatch(str(before.get("raw_sha256")))):
            _fail("reparse_move_content")
        try:
            raw = base64.b64decode(before["raw_base64"], validate=True)
        except (ValueError, KeyError, TypeError):
            _fail("reparse_move_buffer")
        if hashlib.sha256(raw).hexdigest() != before["raw_sha256"]:
            _fail("reparse_move_buffer")
        identity = dict(st_dev=before.get("device"), st_ino=before.get("inode"))
        reported_changes = set()
        for changed in row.get("changed_source_directories", []):
            path = changed.get("relative")
            expected = plan.directories.get(path)
            if (expected is None or (changed.get("device"), changed.get("inode"), changed.get("mtime_ns"))
                    != (expected["st_dev"], expected["st_ino"], expected["mtime_ns"])):
                _fail("reparse_parent_proof")
            reported_changes.add(path)
    elif kind == "native-sdk-move":
        before, after = _pinned_document(value.get("before_evidence")), _pinned_document(value.get("after_evidence"))
        if (not isinstance(before, dict) or not isinstance(after, dict)
                or _key(before.get("root", "")) != _key(original) or _key(after.get("root", "")) != _key(actual)
                or not isinstance(before.get("entries"), list) or not isinstance(after.get("entries"), list)):
            _fail("sdk_move_snapshots")
        before_rows = {row["path"]: row for row in before["entries"]}
        after_rows = {row["path"]: row for row in after["entries"]}
        if len(before_rows) != len(before["entries"]) or len(after_rows) != len(after["entries"]) or before_rows != after_rows or "." not in before_rows:
            _fail("sdk_move_snapshots")
        root = before_rows["."]
        identity = dict(st_dev=root.get("dev"), st_ino=root.get("ino"))
        files = [row for row in before_rows.values() if row.get("kind") == "file"]
        directories = [row for row in before_rows.values() if row.get("kind") == "directory"]
        matches = [row for row in proof.get("moves", []) if isinstance(row, dict)
                   and _key(row.get("source", "")) == _key(original) and _key(row.get("target", "")) == _key(actual)]
        if len(matches) != 1:
            _fail("sdk_move_row")
        move = matches[0]
        if (move.get("operation") != "same_volume_os_rename" or move.get("before_after_sha_native_id_mtime_equal") is not True
                or move.get("source_absent") is not True or move.get("target_present") is not True
                or move.get("files") != len(files) or move.get("directories") != len(directories)
                or move.get("bytes") != sum(row["bytes"] for row in files)
                or len(files) + len(directories) != len(before_rows)):
            _fail("sdk_move_attestation")
        reported_changes = {relative.rpartition("/")[0] or "."}
    else:
        _fail("move_evidence_kind")
    expected = plan.directories.get(relative, plan.reparse_info.get(relative))
    if identity != {key: expected[key] for key in ("st_dev", "st_ino")}:
        _fail("move_identity")
    return reported_changes


def prepare_workspace(spec, *, allow_roots, protected_roots=(), source_mappings=(), native_preserved_roots=()):
    """Validate pinned, complete coverage before any archive directory is created."""
    if not isinstance(spec, dict):
        _fail("source_spec")
    root = _absolute(spec.get("root"))
    if _key(root) not in {_key(_absolute(p)) for p in allow_roots}:
        _fail("source_not_allowed")
    if any(_inside(root, _absolute(p)) or _inside(_absolute(p), root) for p in protected_roots):
        _fail("protected_source")
    base_path, ads_path = _absolute(spec.get("base_manifest")), _absolute(spec.get("ads_manifest"))
    paths, directories, reparse_info, children = {}, {}, {}, collections.defaultdict(set)
    canonical_paths, identities = set(), {}
    counts = collections.Counter(files=0, directories=0, bytes=0, reparses=0)
    ends = set()
    header = footer = None
    for row in _rows(base_path, spec.get("base_sha256")):
        kind = row.get("record")
        if header is None and kind != "header":
            _fail("base_header_missing")
        if footer is not None:
            _fail("base_after_footer")
        if kind == "header":
            if header is not None or paths or row.get("schema") != "autolab-preservation-catalog-v1" or _key(row.get("root", "")) != _key(root):
                _fail("base_header")
            header = row
        elif kind == "entry":
            if header is None:
                _fail("base_header_missing")
            relative = row.get("path")
            validate_relative_path(relative, root=row.get("kind") == "directory")
            canonical = ntpath.normcase(relative.replace("/", "\\"))
            if canonical in canonical_paths or row.get("kind") not in ("file", "directory", "reparse"):
                _fail("base_entry")
            canonical_paths.add(canonical)
            _valid_info(row)
            paths[relative] = row["kind"]
            identities[relative] = (row["st_dev"], row["st_ino"])
            if relative != ".":
                parent, _, name = relative.rpartition("/")
                children[parent or "."].add(name)
            if row["kind"] == "directory":
                directories[relative] = {key: row[key] for key in ("st_dev", "st_ino", "bytes", "mtime_ns")}
                counts["directories"] += 1
            elif row["kind"] == "file":
                if not _SHA.fullmatch(str(row.get("sha256", ""))) or row.get("unstable") is not False or _signature(row) != _signature(row.get("after", {})):
                    _fail("base_file")
                counts["files"] += 1
                counts["bytes"] += row["bytes"]
            else:
                counts["reparses"] += 1
                reparse_info[relative] = {key: row[key] for key in ("st_dev", "st_ino", "bytes", "mtime_ns")}
                reparse_info[relative].update(reparse_tag=row.get("reparse_tag"), target=row.get("target"))
        elif kind == "directory_end":
            if row.get("unstable") is not False or row.get("path") in ends:
                _fail("directory_end")
            ends.add(row.get("path"))
        elif kind == "footer":
            footer = row
        else:
            _fail("base_record")
    if (header is None or footer is None or footer.get("complete") is not True
            or footer.get("errors") != 0 or footer.get("unstable") != 0
            or paths.get(".") != "directory" or ends != set(directories)
            or any(footer.get(key) != value for key, value in counts.items())):
        _fail("base_footer")
    for relative in paths:
        if relative != "." and (relative.rpartition("/")[0] or ".") not in directories:
            _fail("base_parent")
    streams, entry_streams, coverage, unknown, mismatches = collections.defaultdict(list), {}, set(), set(), set()
    header = footer = None
    stream_count = stream_bytes = 0
    for row in _rows(ads_path, spec.get("ads_sha256")):
        kind = row.get("record")
        if header is None and kind != "header":
            _fail("ads_header_missing")
        if footer is not None:
            _fail("ads_after_footer")
        if kind == "header":
            if header is not None or row.get("schema") != "autolab-preservation-ads-v1" or _key(row.get("logical_root", "")) != _key(root) or row.get("base_manifest_sha256") != spec["base_sha256"]:
                _fail("ads_header")
            header = row
        elif kind == "stream":
            relative, name = row.get("path"), _stream_name(row.get("name"))
            if relative not in paths or paths[relative] == "reparse" or any(s["name"] == name for s in streams[relative]):
                _fail("ads_stream")
            _valid_info(row.get("opened_before"))
            if (row.get("unstable") is not False or _signature(row["opened_before"]) != _signature(row.get("opened_after", {}))
                    or (row["opened_before"]["st_dev"], row["opened_before"]["st_ino"]) != identities[relative]
                    or type(row.get("bytes")) is not int or row["bytes"] < 0 or row["bytes"] != row.get("enumerated_bytes")
                    or row["bytes"] != row["opened_before"]["bytes"] or not _SHA.fullmatch(str(row.get("sha256", "")))):
                _fail("ads_stream")
            streams[relative].append(row)
            stream_count += 1
            stream_bytes += row["bytes"]
        elif kind == "entry":
            relative = row.get("path")
            if relative not in paths or relative in coverage or row.get("kind") != paths[relative]:
                _fail("ads_coverage")
            coverage.add(relative)
            if row.get("ads_status") == "unknown_reparse_not_followed" and paths[relative] == "reparse":
                unknown.add(relative)
            elif row.get("ads_status") not in ("no_named_ads_confirmed", "named_ads_hashed") or row.get("unstable") is not False:
                _fail("ads_unknown_data")
            entry_streams[relative] = {(s.get("name"), s.get("sha256"), s.get("bytes")) for s in row.get("streams", [])}
            if row.get("baseline_size_mtime_match") is False:
                mismatches.add(relative)
        elif kind == "footer":
            footer = row
        else:
            _fail("ads_record")
    if (header is None or footer is None or coverage != set(paths) or footer.get("entries") != len(paths)
            or footer.get("errors") != 0 or footer.get("unstable") != 0
            or footer.get("unknown") != len(unknown) or footer.get("reparse_unassessed") != len(unknown)
            or footer.get("baseline_mismatch") != len(mismatches)
            or footer.get("complete") is not (not unknown and not mismatches)
            or footer.get("named_streams") != stream_count or footer.get("named_stream_bytes") != stream_bytes):
        _fail("ads_footer")
    for relative in coverage:
        if entry_streams[relative] != {(s["name"], s["sha256"], s["bytes"]) for s in streams.get(relative, [])}:
            _fail("ads_stream_coverage")
        if (paths[relative] == "reparse") != (relative in unknown):
            _fail("ads_reparse")
    plan = ArchivePlan(dict(spec), root, directories, reparse_info, paths, dict(children), dict(streams), unknown,
                       dict(counts), (), set())
    mappings, exceptions = [], set()
    mapped_keys = set()
    for value in source_mappings:
        if not isinstance(value, dict) or any(key not in {"from", "to", "evidence", "evidence_sha256", "evidence_kind", "before_evidence", "after_evidence", "allow_directory_mtime", "storage"} for key in value):
            _fail("mapping_fields")
        original, actual = _absolute(value.get("from")), _absolute(value.get("to"))
        if not _inside(original, root):
            continue
        relative = original.relative_to(root).as_posix()
        if _key(original) in mapped_keys:
            _fail("duplicate_mapping")
        mapped_keys.add(_key(original))
        if (relative == "." or paths.get(relative) not in ("directory", "reparse")
                or value.get("storage", "copy") not in ("copy", "native-preserved")):
            _fail("mapping_source")
        if value.get("storage") == "native-preserved" and (paths[relative] != "directory"
                or _key(original) not in {_key(_absolute(p)) for p in native_preserved_roots}):
            _fail("native_preserved_not_allowed")
        evidence = _absolute(value.get("evidence"))
        pin = value.get("evidence_sha256")
        reported_changes = _move_identity(value, plan, relative, original, actual)
        allowed_changes = {relative.rpartition("/")[0] or "."}
        for changed in value.get("allow_directory_mtime", []):
            if changed not in directories or changed not in allowed_changes or (reported_changes is not None and changed not in reported_changes):
                _fail("mtime_exception_scope")
            exceptions.add(changed)
        mappings.append(dict(value, **{"from": original, "to": actual, "evidence": str(evidence), "storage": value.get("storage", "copy")}))
    if any(path not in exceptions or paths[path] != "directory" for path in mismatches):
        _fail("ads_baseline_mismatch")
    plan.mappings, plan.mtime_exceptions = tuple(mappings), exceptions
    return plan


if os.name == "nt":
    from ctypes import wintypes
    import msvcrt
    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class _FileId(ctypes.Structure):
        _fields_ = [("volume", ctypes.c_ulonglong), ("identifier", ctypes.c_ubyte * 16)]

    class _Basic(ctypes.Structure):
        _fields_ = [("created", ctypes.c_longlong), ("accessed", ctypes.c_longlong),
                    ("written", ctypes.c_longlong), ("changed", ctypes.c_longlong), ("attributes", wintypes.DWORD)]

    class _Standard(ctypes.Structure):
        _fields_ = [("allocation", ctypes.c_longlong), ("size", ctypes.c_longlong),
                    ("links", wintypes.DWORD), ("deleted", ctypes.c_ubyte), ("directory", ctypes.c_ubyte)]

    class _Stream(ctypes.Structure):
        _fields_ = [("size", ctypes.c_longlong), ("name", wintypes.WCHAR * 296)]

    _kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    _kernel.CreateFileW.restype = wintypes.HANDLE
    _kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel.CloseHandle.restype = wintypes.BOOL
    _kernel.FindFirstStreamW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(_Stream), wintypes.DWORD]
    _kernel.FindFirstStreamW.restype = wintypes.HANDLE
    _kernel.FindNextStreamW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Stream)]
    _kernel.FindNextStreamW.restype = wintypes.BOOL
    _kernel.FindClose.argtypes = [wintypes.HANDLE]
    _kernel.FindClose.restype = wintypes.BOOL
    _kernel.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    _kernel.MoveFileExW.restype = wintypes.BOOL


def _handle_info(handle):
    identifier, basic, standard = _FileId(), _Basic(), _Standard()
    for number, value in ((18, identifier), (0, basic), (1, standard)):
        if not _kernel.GetFileInformationByHandleEx(handle, number, ctypes.byref(value), ctypes.sizeof(value)):
            _fail("native_information")
    if basic.attributes & 0x400:
        _fail("native_reparse")
    return dict(st_dev=identifier.volume, st_ino=int.from_bytes(bytes(identifier.identifier), "little"),
                bytes=standard.size, mtime_ns=(basic.written - 116444736000000000) * 100,
                directory=bool(standard.directory), nlink=standard.links)


@contextmanager
def _reader(path, *, metadata=False, writable=False):
    if os.name == "nt":
        handle = _kernel.CreateFileW(_extended(path), 0x80 if metadata else (0xC0000000 if writable else 0x80000000), 7, None, 3,
                                    0x00200000 | 0x02000000 | (0 if metadata else 0x08000000), None)
        if handle == ctypes.c_void_p(-1).value:
            _fail("native_open")
        transferred = False
        try:
            before = _handle_info(handle)
            if metadata:
                yield None, lambda: _handle_info(handle), before
            else:
                descriptor = msvcrt.open_osfhandle(handle, (os.O_RDWR if writable else os.O_RDONLY) | os.O_BINARY)
                transferred = True
                with os.fdopen(descriptor, "r+b" if writable else "rb", buffering=CHUNK) as stream:
                    yield stream, lambda: _handle_info(msvcrt.get_osfhandle(stream.fileno())), before
        finally:
            if not transferred:
                _kernel.CloseHandle(handle)
    else:
        flags = (os.O_RDWR if writable else os.O_RDONLY) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        def snapshot():
            value = os.fstat(descriptor)
            return dict(st_dev=value.st_dev, st_ino=value.st_ino, bytes=value.st_size,
                        mtime_ns=value.st_mtime_ns, directory=stat.S_ISDIR(value.st_mode), nlink=value.st_nlink)
        try:
            before = snapshot()
            if metadata:
                yield None, snapshot, before
            else:
                with os.fdopen(descriptor, "r+b" if writable else "rb", closefd=False) as stream:
                    yield stream, snapshot, before
        finally:
            os.close(descriptor)


def _snapshot(path):
    with _reader(path, metadata=True) as (_, current, before):
        after = current()
        if before != after:
            _fail("metadata_unstable")
        return before


def _check_info(actual, expected, *, directory=False, mtime_exception=False):
    if (actual["st_dev"], actual["st_ino"]) != (expected["st_dev"], expected["st_ino"]) or actual["directory"] != directory:
        _fail("source_identity")
    if not mtime_exception and (actual["bytes"], actual["mtime_ns"]) != (expected["bytes"], expected["mtime_ns"]):
        _fail("source_size_mtime")
    if mtime_exception and actual["bytes"] != expected["bytes"]:
        _fail("directory_size")


def _named_streams(path):
    if os.name != "nt":
        return []
    value = _Stream()
    handle = _kernel.FindFirstStreamW(_extended(path), 0, ctypes.byref(value), 0)
    if handle == ctypes.c_void_p(-1).value:
        if ctypes.get_last_error() == 38:
            return []
        _fail("stream_enumeration")
    result = []
    try:
        while True:
            if value.name != "::$DATA":
                result.append((_stream_name(value.name), value.size))
            if not _kernel.FindNextStreamW(handle, ctypes.byref(value)):
                if ctypes.get_last_error() != 38:
                    _fail("stream_enumeration")
                break
    finally:
        _kernel.FindClose(handle)
    return sorted(result)


def _mkdir(path):
    _no_reparse(path, missing=True)
    os.makedirs(_extended(path), exist_ok=True)
    _no_reparse(path)
    if not stat.S_ISDIR(os.lstat(_extended(path)).st_mode):
        _fail("archive_directory")


def _verify_blob(path, digest, size):
    _no_reparse(path)
    with _reader(path) as (stream, current, before):
        calculated, count = hashlib.sha256(), 0
        while data := stream.read(CHUNK):
            calculated.update(data)
            count += len(data)
        if before != current() or count != size or before["bytes"] != size or calculated.hexdigest() != digest:
            _fail("blob_corrupt")


def _durable_file(path):
    _no_reparse(path)
    with _reader(path, writable=True) as (stream, current, before):
        os.fsync(stream.fileno())
        if before != current():
            _fail("blob_changed_during_flush")


def _publish(path, producer, digest, size):
    """Create-only publication; orphaned pending files remain diagnosable.

    Concurrent writers are verified on local Windows NTFS. Its same-directory
    WRITE_THROUGH rename has no REPLACE_EXISTING or COPY_ALLOWED flag and does
    not expose the link/unlink nlink transition to another verifier. Other
    platforms retain hardlink publication and require sequential archivers.
    """
    _mkdir(path.parent)
    if os.path.lexists(_extended(path)):
        producer(None)
        _verify_blob(path, digest, size)
        _durable_file(path)
        return False
    pending = path.parent / ("." + path.name + "." + uuid.uuid4().hex + ".pending")
    with open(_extended(pending), "xb") as output:
        producer(output)
        output.flush()
        os.fsync(output.fileno())
    _verify_blob(pending, digest, size)
    moved = False
    try:
        if os.name == "nt":
            # Same parent/volume; never replace, copy-delete or defer to reboot.
            if not _kernel.MoveFileExW(_extended(pending), _extended(path), 0x8):
                error = ctypes.get_last_error()
                if error in (80, 183):  # ERROR_FILE_EXISTS / ERROR_ALREADY_EXISTS
                    raise FileExistsError(error, "archive publication destination exists", str(path))
                raise ctypes.WinError(error)
            moved = True
        else:
            os.link(_extended(pending), _extended(path), follow_symlinks=False)
    except FileExistsError:
        _verify_blob(path, digest, size)
    _verify_blob(path, digest, size)
    _durable_file(path)
    if not moved:
        os.unlink(_extended(pending))
    if os.name != "nt":
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return True


def _copy_verified(source, destination, expected, digest, *, directory_stream=False, reference=False):
    verification = {}
    def producer(output):
        calculated, count = hashlib.sha256(), 0
        _no_reparse(source)
        with _reader(source) as (stream, current, before):
            _check_info(before, expected, directory=directory_stream)
            while data := stream.read(CHUNK):
                calculated.update(data)
                count += len(data)
                if output is not None:
                    output.write(data)
            after = current()
            if before != after or count != expected["bytes"] or calculated.hexdigest() != digest:
                _fail("source_sha_or_unstable")
        named_after = _snapshot(source)
        if _signature(named_after) != _signature(before):
            _fail("source_path_changed")
        verification.update(source_before=before, source_after=after, source_path_after=named_after,
                            bytes_verified=count, sha256_verified=calculated.hexdigest())
    if reference:
        producer(None)
    else:
        _publish(destination, producer, digest, expected["bytes"])
    return verification


def _copy_metadata(source, destination, digest):
    _no_reparse(source)
    value = _snapshot(source)
    _copy_verified(source, destination, value, digest)


def _physical_boundary(path):
    """Expand existing 8.3/case aliases without following a reparse leaf."""
    try:
        leaf_reparse = _reparse(os.lstat(_extended(path)))
    except FileNotFoundError:
        leaf_reparse = False
    probe = path.parent if leaf_reparse else path
    _no_reparse(probe, missing=True)
    result = os.path.realpath(_extended(probe))
    if os.name == "nt" and result.startswith("\\\\?\\"):
        result = result[4:]
    result = _absolute(result)
    return result / path.name if leaf_reparse else result


def _output_boundaries(output, *, allow_roots, protected_roots, source_mappings, archive_roots):
    if archive_roots is not None and _key(output) not in {_key(_absolute(path)) for path in archive_roots}:
        _fail("archive_destination_not_pinned")
    _no_reparse(output, missing=True)
    owned = [output / name for name in ("objects", "manifests", "receipts", "evidence")]
    allowed = [_absolute(path) for path in allow_roots]
    protected = [_absolute(path) for path in protected_roots]
    mapped = [_absolute(value.get("to")) for value in source_mappings]
    for physical in (False, True):
        transform = _physical_boundary if physical else lambda value: value
        destination = transform(output)
        sources = [transform(path) for path in allowed]
        boundaries = sources + [transform(path) for path in protected + mapped]
        if any(_inside(destination, source) or _inside(source, destination) for source in sources):
            _fail("archive_source_overlap")
        if any(_inside(destination, source) for source in boundaries):
            _fail("archive_protected_overlap")
        for namespace in owned:
            target = transform(namespace)
            if any(_inside(target, source) or _inside(source, target) for source in boundaries):
                _fail("archive_namespace_overlap")
    for namespace in owned:
        _no_reparse(namespace, missing=True)


def _directory_state(plan, relative, *, initial=None):
    actual = plan.actual(relative)
    _no_reparse(actual)
    before = _snapshot(actual)
    _check_info(before, plan.directories[relative], directory=True,
                mtime_exception=relative in plan.mtime_exceptions)
    if initial is not None and _signature(before) != initial:
        _fail("directory_changed_after_initial_observation")
    logical = plan.root.joinpath(*validate_relative_path(relative, root=True))
    removed = {mapping["from"].name for mapping in plan.mappings
               if _key(mapping["from"].parent) == _key(logical)
               and _key(mapping["to"]) != _key(actual / mapping["from"].name)}
    with os.scandir(_extended(actual)) as items:
        present = {entry.name for entry in items}
    if present != plan.children.get(relative, set()) - removed:
        _fail("current_directory_coverage")
    if _signature(before) != _signature(_snapshot(actual)):
        _fail("directory_unstable")
    return before


def _final_source_barrier(plan, base_manifest, output, directory_fingerprints):
    """Rehash all baseline bytes, then recheck path/ADS/native fingerprints.

    This is not a filesystem snapshot or a deletion permit. The coordinator
    must keep cold sources quiescent throughout capture and later disposition.
    """
    for relative in plan.directories:
        _directory_state(plan, relative, initial=directory_fingerprints[relative])
    files = streams = byte_count = 0
    for row in _rows(base_manifest, plan.spec["base_sha256"]):
        if row.get("record") != "entry" or row["kind"] == "reparse":
            continue
        relative, actual = row["path"], plan.actual(row["path"])
        expected_streams = sorted((stream["name"], stream["bytes"]) for stream in plan.streams.get(relative, []))
        if _named_streams(actual) != expected_streams:
            _fail("final_ads_coverage")
        if row["kind"] == "file":
            verified = _copy_verified(actual, output, row, row["sha256"], reference=True)
            files += 1
            byte_count += verified["bytes_verified"]
        for stream in plan.streams.get(relative, []):
            source = Path(str(actual) + stream["name"])
            verified = _copy_verified(source, output, stream["opened_before"], stream["sha256"],
                                      directory_stream=bool(_snapshot(source)["directory"]), reference=True)
            streams += 1
            byte_count += verified["bytes_verified"]
    # No relocation-mtime exception may hide a change after the first scan.
    for relative in plan.directories:
        _directory_state(plan, relative, initial=directory_fingerprints[relative])
    for row in _rows(base_manifest, plan.spec["base_sha256"]):
        if row.get("record") != "entry" or row["kind"] == "reparse":
            continue
        relative, actual = row["path"], plan.actual(row["path"])
        if row["kind"] == "file":
            _no_reparse(actual)
            _check_info(_snapshot(actual), row)
        if _named_streams(actual) != sorted((s["name"], s["bytes"]) for s in plan.streams.get(relative, [])):
            _fail("final_ads_changed")
        for stream in plan.streams.get(relative, []):
            path = Path(str(actual) + stream["name"])
            _no_reparse(path)
            if _signature(_snapshot(path)) != _signature(stream["opened_before"]):
                _fail("final_ads_fingerprint")
    return dict(files=files, ads_streams=streams, bytes_rehashed=byte_count,
                directories=len(plan.directories), native_id_size_mtime_sha_verified=True)


def archive_workspace(spec, archive_root, *, allow_roots, protected_roots=(), source_mappings=(),
                      native_preserved_roots=(), git_evidence=None, scope_evidence=None, archive_roots=None):
    """Copy only one explicit source; returns evidence, never deletion permission."""
    allow_roots, protected_roots, source_mappings = tuple(allow_roots), tuple(protected_roots), tuple(source_mappings)
    native_preserved_roots = tuple(native_preserved_roots)
    plan = prepare_workspace(spec, allow_roots=allow_roots, protected_roots=protected_roots,
                             source_mappings=source_mappings, native_preserved_roots=native_preserved_roots)
    output = _absolute(archive_root)
    _output_boundaries(output, allow_roots=allow_roots, protected_roots=protected_roots,
                       source_mappings=source_mappings, archive_roots=archive_roots)
    _mkdir(output)
    manifests = {kind: output / "manifests/sha256" / spec[kind + "_sha256"] for kind in ("base", "ads")}
    run_id = uuid.uuid4().hex
    journal = output / "receipts" / (run_id + ".jsonl")
    _mkdir(journal.parent)
    distinct, native_refs = set(), 0
    files = ads_count = default_bytes = ads_bytes = native_bytes = 0
    directory_fingerprints = {}
    receipt = dict(schema="workspace-cas-receipt-v1", root=str(plan.root), run_id=run_id,
                   base_sha256=spec["base_sha256"], ads_sha256=spec["ads_sha256"],
                   deletion_authorized=False, source_deleted=False, source_moved=False,
                   scope_evidence=scope_evidence,
                   git_evidence=git_evidence, git_preservation_status="external_report_attached_not_adjudicated" if git_evidence else "unverified",
                   mappings=[{**m, "from": str(m["from"]), "to": str(m["to"])} for m in plan.mappings])
    with open(_extended(journal), "x", encoding="utf-8", newline="\n") as log:
        def write(row):
            log.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
            log.flush()
        write(dict(record="header", **receipt))
        context = {}
        try:
            for kind, target in manifests.items():
                context = dict(phase="metadata", path=kind)
                _copy_metadata(_absolute(spec[kind + "_manifest"]), target, spec[kind + "_sha256"])
            external = [e for e in (git_evidence, scope_evidence) if e is not None]
            external += [dict(path=m["evidence"], sha256=m["evidence_sha256"]) for m in plan.mappings]
            external += [m[key] for m in plan.mappings for key in ("before_evidence", "after_evidence") if key in m]
            for evidence in external:
                context = dict(phase="external_evidence", path=evidence.get("path"))
                pin = evidence.get("sha256")
                if not _SHA.fullmatch(str(pin)):
                    _fail("external_evidence_pin")
                _copy_metadata(_absolute(evidence.get("path")), output / "evidence/sha256" / pin, pin)
            for relative, expected in plan.directories.items():
                context = dict(phase="directory", path=relative)
                actual = plan.actual(relative)
                before = _directory_state(plan, relative)
                directory_fingerprints[relative] = _signature(before)
                write(dict(record="directory", path=relative, actual_path=str(actual), native=before,
                           directory_mtime_exception=relative in plan.mtime_exceptions))
            for row in _rows(manifests["base"], spec["base_sha256"]):
                if row.get("record") != "entry" or row["kind"] == "reparse":
                    continue
                relative, actual = row["path"], plan.actual(row["path"])
                context = dict(phase="entry", path=relative)
                expected_streams = sorted((s["name"], s["bytes"]) for s in plan.streams.get(relative, []))
                if _named_streams(actual) != expected_streams:
                    _fail("current_ads_coverage")
                reference = plan.storage(relative) == "native-preserved"
                if row["kind"] == "file":
                    digest = row["sha256"]
                    target = output / "objects/sha256" / digest[:2] / digest
                    verification = _copy_verified(actual, target, row, digest, reference=reference)
                    files += 1
                    default_bytes += verification["bytes_verified"]
                    native_refs += int(reference)
                    native_bytes += verification["bytes_verified"] if reference else 0
                    if not reference:
                        distinct.add(digest)
                    write(dict(record="file", path=relative, sha256=digest, bytes=row["bytes"],
                               storage="native-preserved" if reference else "cas", actual_path=str(actual), **verification))
                for stream in plan.streams.get(relative, []):
                    context = dict(phase="stream", path=relative, name=stream["name"])
                    digest = stream["sha256"]
                    target = output / "objects/sha256" / digest[:2] / digest
                    stream_path = Path(str(actual) + stream["name"])
                    verification = _copy_verified(stream_path, target, stream["opened_before"], digest,
                                                  directory_stream=bool(_snapshot(stream_path)["directory"]), reference=reference)
                    ads_count += 1
                    ads_bytes += verification["bytes_verified"]
                    native_refs += int(reference)
                    native_bytes += verification["bytes_verified"] if reference else 0
                    if not reference:
                        distinct.add(digest)
                    write(dict(record="stream", path=relative, name=stream["name"], sha256=digest,
                               bytes=stream["bytes"], storage="native-preserved" if reference else "cas", **verification))
                if _named_streams(actual) != expected_streams:
                    _fail("ads_changed_during_copy")
            context = dict(phase="final-source-barrier")
            barrier = _final_source_barrier(plan, manifests["base"], output, directory_fingerprints)
            if barrier["files"] != files or barrier["ads_streams"] != ads_count or barrier["bytes_rehashed"] != default_bytes + ads_bytes:
                _fail("final_barrier_counts")
            receipt.update(files_verified=files, ads_streams_verified=ads_count, unique_data_blobs=len(distinct),
                           default_bytes_verified=default_bytes, ads_bytes_verified=ads_bytes,
                           native_reference_bytes=native_bytes,
                           native_reference_count=native_refs, unresolved_reparse=sorted(plan.unknown),
                           managed_development_required=native_refs > 0,
                           final_source_barrier=barrier, source_atomic_snapshot=False, source_quiescence_required=True,
                           data_complete=not plan.unknown and native_refs == 0,
                           cas_self_contained=not plan.unknown and native_refs == 0,
                           executed=True, journal_relative=str(journal.relative_to(output)).replace("\\", "/"))
            write(dict(record="footer", complete=receipt["data_complete"], **receipt))
            os.fsync(log.fileno())
        except (ArchiveError, OSError) as error:
            try:
                write(dict(record="failure", complete=False, deletion_authorized=False,
                           context=context, code=str(error) if isinstance(error, ArchiveError) else type(error).__name__))
                os.fsync(log.fileno())
            except OSError:
                pass
            if isinstance(error, ArchiveError):
                raise
            _fail("filesystem_failure")
    return receipt


def _archive_metadata_entry(path, pin, relative, *, stream_name=None):
    selected = None
    wanted = ntpath.normcase(relative.replace("/", "\\"))
    for row in _rows(path, pin):
        if ntpath.normcase(str(row.get("path", "")).replace("/", "\\")) != wanted:
            continue
        match = row.get("record") == "entry" if stream_name is None else row.get("record") == "stream" and row.get("name") == stream_name
        if match:
            if selected is not None:
                _fail("lookup_duplicate_metadata")
            selected = row
    return selected


def _receipt_mapping(root, relative, mappings):
    logical = root.joinpath(*validate_relative_path(relative, root=True))
    choices = []
    for mapping in mappings:
        original, actual = _absolute(mapping.get("from")), _absolute(mapping.get("to"))
        if _inside(logical, original):
            choices.append((len(_key(original)), original, actual, mapping))
    if not choices:
        return logical, None
    _, original, actual, mapping = max(choices, key=lambda item: item[0])
    suffix = str(logical)[len(str(original)):].lstrip("\\/")
    return (actual / suffix if suffix else actual), mapping


def lookup_archive(archive_root, original_ref, *, stream_name=None, manifest_sha256=None):
    """Metadata locator only; never reads payload bytes or grants execution.

For directory/reparse metadata, sha identifies the pinned original catalog,
not a target stream. Ambiguous historical snapshots require a manifest pin.
"""
    output, reference = _absolute(archive_root), _absolute(original_ref)
    _no_reparse(output)
    if stream_name is not None:
        _stream_name(stream_name)
    if manifest_sha256 is not None and not _SHA.fullmatch(str(manifest_sha256)):
        _fail("lookup_manifest_pin")
    receipts = output / "receipts"
    _no_reparse(receipts)
    answers = {}
    with os.scandir(_extended(receipts)) as items:
        journals = [Path(entry.path) for entry in items if re.fullmatch(r"[0-9a-f]{32}\.jsonl", entry.name)]
    for journal in journals:
        _no_reparse(journal)
        with open(_extended(journal), "rb") as stream:
            first = stream.readline(CHUNK + 1)
        if len(first) > CHUNK or not first.endswith(b"\n"):
            continue
        header = _json(first.decode("utf-8"))
        if header.get("record") != "header" or header.get("schema") != "workspace-cas-receipt-v1":
            continue
        root = _absolute(header.get("root"))
        if not _inside(reference, root) or (manifest_sha256 is not None and header.get("base_sha256") != manifest_sha256):
            continue
        relative = reference.relative_to(root).as_posix()
        validate_relative_path(relative, root=True)
        wanted, candidate, last = ntpath.normcase(relative.replace("/", "\\")), None, None
        for row in _rows(journal, _digest(journal)):
            last = row
            same = ntpath.normcase(str(row.get("path", "")).replace("/", "\\")) == wanted
            if same and (row.get("record") == "file" if stream_name is None else row.get("record") == "stream" and row.get("name") == stream_name):
                if candidate is not None:
                    _fail("lookup_duplicate_receipt")
                candidate = row
        if (last is None or last.get("record") != "footer" or last.get("executed") is not True
                or last.get("deletion_authorized") is not False or last.get("run_id") != header.get("run_id")):
            continue
        pin = header.get("ads_sha256") if stream_name is not None else header.get("base_sha256")
        if not _SHA.fullmatch(str(pin)):
            _fail("lookup_catalog_pin")
        metadata_path = output / "manifests/sha256" / pin
        metadata = _archive_metadata_entry(metadata_path, pin, relative, stream_name=stream_name)
        if metadata is None:
            continue
        mapped, mapping = _receipt_mapping(root, relative, header.get("mappings", []))
        if stream_name is None and metadata.get("kind") == "directory":
            result_kind, digest, size, storage = "directory-metadata", pin, metadata["bytes"], metadata_path
        elif stream_name is None and metadata.get("kind") == "reparse":
            result_kind, digest, size, storage = "reparse-metadata-ads-unknown", pin, metadata["bytes"], metadata_path
            if mapping is not None and _key(mapping["from"]) == _key(reference):
                _no_reparse(mapped.parent)
                native = os.lstat(_extended(mapped))
                if not _reparse(native) or (native.st_dev, native.st_ino) != (metadata["st_dev"], metadata["st_ino"]):
                    _fail("lookup_reparse_changed")
                storage = mapped
        else:
            if candidate is None or candidate.get("sha256") != metadata.get("sha256") or candidate.get("bytes") != metadata.get("bytes"):
                _fail("lookup_receipt_metadata_mismatch")
            digest, size = metadata["sha256"], metadata["bytes"]
            if candidate.get("storage") == "cas":
                result_kind = "ads" if stream_name is not None else "file"
                storage = output / "objects/sha256" / digest[:2] / digest
                _no_reparse(storage)
                if _snapshot(storage)["bytes"] != size:
                    _fail("lookup_blob_size")
            elif candidate.get("storage") == "native-preserved" and mapping is not None and mapping.get("storage") == "native-preserved":
                result_kind = "native-preserved-ads" if stream_name is not None else "native-preserved-file"
                storage = Path(str(mapped) + stream_name) if stream_name is not None else mapped
                _no_reparse(storage)
                if _signature(_snapshot(storage)) != _signature(candidate.get("source_before", {})):
                    _fail("lookup_native_changed")
            else:
                _fail("lookup_storage_kind")
        answer = dict(original_ref=str(reference) + (stream_name or ""), kind=result_kind,
                      sha=digest, bytes=size, storage_path=str(storage), execution_authority=False)
        answers[(result_kind, digest, size, _key(storage))] = answer
    if not answers:
        _fail("lookup_not_found")
    if len(answers) != 1:
        _fail("lookup_ambiguous")
    return next(iter(answers.values()))
