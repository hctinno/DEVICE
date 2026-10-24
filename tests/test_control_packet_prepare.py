"""Synthetic private-copy contracts; no collected payload fixtures or imports."""

from __future__ import annotations

import hashlib
import errno
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import types
import unittest
import zipfile
from unittest import mock

from labflow import control_packet_prepare as prepare
from labflow.control_packet_audit import audit_control_packet, ControlPacketAuditError


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ControlPacketPrepareTests(unittest.TestCase):
    def setUp(self):
        fixture_root = Path(__file__).resolve().parents[1] / ".local" / "CONTROL-PACKET-PREPARE-004-D1" / "fixtures"
        fixture_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=fixture_root)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "\ud569\uc131-PRIVATE-SOURCE"
        self.source.mkdir()
        self.workspace = self.base / "\ud569\uc131-private-workspace"
        self.workspace.mkdir()
        self.packet_id = "SYNTHETIC-PREPARE-v1"
        self.index = {
            "request_id": "DEV-CONTROL-SOURCES-008", "revision": "SYNTHETIC-v1",
            "source_code_executed": False, "runtime_or_hardware_support_confirmed": False,
            "public_export_allowed": False, "files": [],
            "observation": {"secret": "PRIVATE-SECRET", "serial": "PRIVATE-SERIAL"},
        }
        self.payload("metadata/data.json", b'{"synthetic":true,"secret":"PRIVATE-BODY"}')
        self.payload("originals/source.py", b"raise RuntimeError('MUST NOT IMPORT PRIVATE-SERIAL')")
        (self.source / "development-receipt.json").write_bytes(b'{"unlisted":"PRIVATE-SECRET"}')
        self.save_index()

    @property
    def destination(self):
        return self.workspace / ".local" / "control-packets" / self.packet_id

    def payload(self, path, data):
        file = self.source.joinpath(*path.split("/"))
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        self.index["files"] = [row for row in self.index["files"] if row["path"].casefold() != path.casefold()]
        self.index["files"].append({"path": path, "bytes": len(data), "sha256": sha(data)})

    def save_index(self):
        raw = json.dumps(self.index, ensure_ascii=True, separators=(",", ":")).encode("utf-8") + b"\n"
        (self.source / "intake-v1.json").write_bytes(raw)
        self.pin = sha(raw)

    def call(self, **overrides):
        options = {"expected_index_sha256": self.pin, "workspace_root": self.workspace,
                   "packet_id": self.packet_id}
        source = overrides.pop("source_dir", self.source)
        options.update(overrides)
        return prepare.prepare_control_packet(source, **options)

    def snapshot(self):
        return {p.relative_to(self.source).as_posix(): (p.read_bytes(), p.stat().st_size, p.stat().st_mtime_ns)
                for p in self.source.rglob("*") if p.is_file()}

    def error(self, code, **overrides):
        with self.assertRaises(prepare.ControlPacketPrepareError) as caught:
            self.call(**overrides)
        error = caught.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.code, code)
        self.assertEqual(str(error), code)
        self.assertEqual(error.args, (code,))
        self.assertIsNone(error.__context__)
        for forbidden in (str(self.source), str(self.workspace), "PRIVATE-SECRET", "PRIVATE-SERIAL", "PRIVATE-BODY"):
            self.assertNotIn(forbidden, repr(error))

    def incomplete(self):
        self.assertTrue(self.destination.is_dir())
        self.assertFalse((self.destination / "prepared-receipt.json").exists())

    def test_exact_private_copy_receipt_and_source_unchanged(self):
        before = self.snapshot()
        expected_audit = audit_control_packet(self.source, expected_index_sha256=self.pin)
        result = self.call()
        self.assertEqual(result, {
            "schema_version": 1, "kind": "control_packet_prepare", "packet_id": self.packet_id,
            "destination_relpath": ".local/control-packets/" + self.packet_id,
            "index_sha256": self.pin, "state": "complete", "audit_summary": expected_audit,
            "support_status": "not_assessed", "public_export_allowed": False,
            "source_code_executed": False, "runtime_or_hardware_support_confirmed": False,
            "hardware_verified": False,
        })
        self.assertEqual(before, self.snapshot())
        marker = self.destination / "prepared-receipt.json"
        self.assertEqual(json.loads(marker.read_bytes()), result)
        temporary = list(self.destination.glob(".prepared-receipt-*.tmp"))
        self.assertEqual(len(temporary), 1)
        self.assertEqual(temporary[0].read_bytes(), marker.read_bytes())
        expected_files = {row["path"] for row in self.index["files"]} | {"intake-v1.json"}
        actual_files = {p.relative_to(self.destination).as_posix()
                        for p in self.destination.rglob("*") if p.is_file()}
        self.assertEqual(actual_files - {"prepared-receipt.json", temporary[0].name}, expected_files)
        for relative in expected_files:
            self.assertEqual((self.destination / relative).read_bytes(), (self.source / relative).read_bytes())
        self.assertEqual(audit_control_packet(self.destination, expected_index_sha256=self.pin), expected_audit)
        self.assertNotIn("PRIVATE-", json.dumps(result))

    def test_return_is_detached_from_receipt_and_next_preparation(self):
        result = self.call()
        marker = self.destination / "prepared-receipt.json"
        original = marker.read_bytes()
        result["audit_summary"]["payload_bytes"] = -1
        result["state"] = "caller-change"
        self.assertEqual(marker.read_bytes(), original)
        result2 = self.call(packet_id="SYNTHETIC-PREPARE-v2")
        self.assertGreater(result2["audit_summary"]["payload_bytes"], 0)
        self.assertEqual(result2["state"], "complete")

    def test_archives_remain_opaque_copies_without_extraction_or_execution(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("../must_not_be_extracted.py", b"raise RuntimeError('MUST NOT EXECUTE')")
        self.payload("archives/source.zip", buffer.getvalue())
        self.payload("archives/source.tar.gz", b"opaque TAR.GZ is checked only by SHA/bytes")
        self.save_index()
        before = self.snapshot()
        result = self.call()
        self.assertEqual(result["audit_summary"]["zip_crc_checked_count"], 1)
        self.assertEqual(result["audit_summary"]["tar_gz_sha_only_count"], 1)
        self.assertEqual((self.destination / "archives/source.zip").read_bytes(), buffer.getvalue())
        self.assertFalse((self.destination.parent / "must_not_be_extracted.py").exists())
        self.assertEqual(before, self.snapshot())

    def test_invalid_argument_types_hash_and_packet_id_before_writes(self):
        for key, values in {
            "packet_id": [None, True, 1, "", ".", "..", "a/b", "C:x", "NUL", "con.txt", "COM1",
                          "a.", "a ", "a" * 81, "\ud55c\uae00"],
            "expected_index_sha256": [None, 1, self.pin.upper(), "x" * 64, "a" * 63],
            "workspace_root": [None, b"bytes"], "source_dir": [None, b"bytes"],
        }.items():
            for value in values:
                with self.subTest(key=key, value_type=type(value).__name__):
                    self.error("packet_prepare_invalid_argument", **{key: value})
        self.assertFalse((self.workspace / ".local").exists())

    def test_nonlocal_and_ambiguous_roots_are_rejected(self):
        for key in ("source_dir", "workspace_root"):
            for value in ("\\\\invalid\\PRIVATE-SECRET", "//invalid/PRIVATE-SECRET", "x\x00y", "../PRIVATE-SECRET"):
                with self.subTest(key=key, kind=value[:2]):
                    self.error("packet_prepare_path_invalid", **{key: value})
        self.assertFalse(self.destination.exists())

    def test_missing_or_non_directory_workspace_and_source_are_rejected(self):
        file = self.base / "PRIVATE-file"
        file.write_bytes(b"synthetic")
        for key in ("workspace_root", "source_dir"):
            for value in (self.base / "missing", file):
                with self.subTest(key=key, leaf=value.name):
                    self.error("packet_prepare_path_invalid", **{key: value})
        self.assertFalse(self.destination.exists())

    def test_existing_empty_nonempty_or_file_destination_is_never_changed(self):
        before = self.snapshot()
        parent = self.destination.parent
        parent.mkdir(parents=True)
        for suffix, kind in (("empty", "empty"), ("nonempty", "directory"), ("file", "file")):
            packet_id = self.packet_id + "-" + suffix
            target = parent / packet_id
            if kind == "file":
                target.write_bytes(b"foreign file")
            else:
                target.mkdir()
                if kind == "directory":
                    (target / "foreign.txt").write_bytes(b"foreign content")
            with self.subTest(kind=kind):
                self.error("packet_prepare_destination_exists", packet_id=packet_id)
                if kind == "file":
                    self.assertEqual(target.read_bytes(), b"foreign file")
                elif kind == "directory":
                    self.assertEqual((target / "foreign.txt").read_bytes(), b"foreign content")
                else:
                    self.assertEqual(list(target.iterdir()), [])
        self.assertEqual(before, self.snapshot())

    def test_source_as_destination_ancestor_is_rejected(self):
        before = self.snapshot()
        self.error("packet_prepare_path_invalid", workspace_root=self.source)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.source / ".local").exists())

    def test_same_source_and_destination_is_rejected(self):
        destination = self.destination
        destination.parent.mkdir(parents=True)
        self.source.rename(destination)
        self.source = destination
        before = self.snapshot()
        self.error("packet_prepare_path_invalid")
        self.assertEqual(before, self.snapshot())

    def test_source_inside_destination_is_rejected(self):
        self.destination.mkdir(parents=True)
        nested = self.destination / "source"
        self.source.rename(nested)
        self.source = nested
        before = self.snapshot()
        self.error("packet_prepare_path_invalid")
        self.assertEqual(before, self.snapshot())

    def test_manifest_completion_marker_collision_before_destination_creation(self):
        for path in ("prepared-receipt.json", "PREPARED-RECEIPT.JSON"):
            with self.subTest(path=path):
                self.payload(path, b"{}")
                self.save_index()
                self.error("packet_prepare_path_invalid")
                self.assertFalse(self.destination.exists())

    def test_manifest_completion_marker_directory_collision(self):
        self.payload("prepared-receipt.json/child.txt", b"synthetic")
        self.save_index()
        self.error("packet_prepare_path_invalid")
        self.assertFalse(self.destination.exists())

    def test_initial_audit_failure_makes_no_destination(self):
        before = self.snapshot()
        self.error("packet_prepare_verification_failed", expected_index_sha256="0" * 64)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.workspace / ".local").exists())

    def test_reparse_source_workspace_parent_and_leaf_are_rejected(self):
        parent = self.destination.parent
        parent.mkdir(parents=True)
        original_info, original_stat = prepare._WindowsIO.info, prepare._WindowsIO.stat_file
        for target in (self.source, self.workspace, parent, self.source / "metadata" / "data.json"):
            with self.subTest(target=target.name):
                def reparse_info(backend, descriptor, **kwargs):
                    result = original_info(backend, descriptor, **kwargs)
                    if backend.directories.get(target) == descriptor:
                        return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                    return result

                def reparse_stat(backend, path):
                    result = original_stat(backend, path)
                    if path == target:
                        return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                    return result

                with mock.patch.object(prepare._WindowsIO, "info", reparse_info), \
                        mock.patch.object(prepare._WindowsIO, "stat_file", reparse_stat):
                    self.error("packet_prepare_path_invalid")
        self.assertFalse(self.destination.exists())

    def test_opened_destination_identity_must_match_its_path(self):
        original_create, original_fstat = prepare._WindowsIO.create_file, os.fstat
        created = set()

        def track(backend, path):
            descriptor = original_create(backend, path)
            created.add(descriptor)
            return descriptor

        def changed(descriptor):
            info = original_fstat(descriptor)
            if descriptor in created:
                return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0,
                                             st_dev=info.st_dev, st_ino=info.st_ino + 1)
            return info

        with mock.patch.object(prepare._WindowsIO, "create_file", track), \
                mock.patch.object(prepare.os, "fstat", side_effect=changed):
            self.error("packet_prepare_path_invalid")
        self.incomplete()

    def test_unexpected_audit_shape_or_support_is_not_persisted(self):
        for mode in ("extra", "support", "schema"):
            def unexpected(path, **kwargs):
                result = audit_control_packet(path, **kwargs)
                if mode == "extra":
                    result["raw_source_path"] = str(self.source)
                elif mode == "support":
                    result["hardware_verified"] = True
                else:
                    result["schema_version"] = True
                return result
            with self.subTest(mode=mode), mock.patch.object(prepare, "audit_control_packet", side_effect=unexpected):
                self.error("packet_prepare_verification_failed", packet_id=self.packet_id + "-" + mode)
            self.assertFalse((self.destination.parent / (self.packet_id + "-" + mode)).exists())

    def test_real_private_parent_junction_does_not_receive_writes(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.workspace / ".local"
        if os.name == "nt":
            run = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                                 capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            run.check_returncode()
        else:
            link.symlink_to(outside, target_is_directory=True)
        try:
            self.error("packet_prepare_path_invalid")
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            if os.name == "nt":
                os.rmdir(link)
            else:
                link.unlink()

    def test_source_read_failure_after_creation_preserves_partial_copy(self):
        before = self.snapshot()
        original_read = os.read

        def failed(fd, size):
            if self.destination.exists():
                raise OSError("PRIVATE-SECRET read")
            return original_read(fd, size)

        with mock.patch.object(prepare.os, "read", side_effect=failed):
            self.error("packet_prepare_source_changed")
        self.incomplete()
        self.assertEqual(before, self.snapshot())

    def test_source_change_during_copy_is_not_completed(self):
        original_read = os.read
        changed = False

        def mutate(fd, size):
            nonlocal changed
            data = original_read(fd, size)
            if self.destination.exists() and not changed:
                changed = True
                (self.source / "originals" / "source.py").write_bytes(b"changed synthetic source")
            return data

        with mock.patch.object(prepare.os, "read", side_effect=mutate):
            self.error("packet_prepare_source_changed")
        self.incomplete()
        self.assertTrue(changed)

    def test_source_mtime_only_change_is_detected(self):
        original_read = os.read
        changed = False

        def mutate(fd, size):
            nonlocal changed
            data = original_read(fd, size)
            if self.destination.exists() and not changed:
                changed = True
                path = self.source / "metadata" / "data.json"
                info = path.stat()
                os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000000))
            return data

        with mock.patch.object(prepare.os, "read", side_effect=mutate):
            self.error("packet_prepare_source_changed")
        self.incomplete()

    def test_short_reads_and_positive_short_writes_are_completed(self):
        before = self.snapshot()
        original_read, original_write = os.read, os.write
        with mock.patch.object(prepare.os, "read", side_effect=lambda fd, size: original_read(fd, min(size, 7))), \
                mock.patch.object(prepare.os, "write", side_effect=lambda fd, data: original_write(fd, data[:5])):
            result = self.call()
        self.assertEqual(result["state"], "complete")
        self.assertEqual(before, self.snapshot())

    def test_zero_or_failed_destination_write_preserves_source_and_stage(self):
        original_id = self.packet_id
        for mode in ("zero", "exception"):
            self.packet_id = original_id + "-" + mode
            before = self.snapshot()
            fault = {"return_value": 0} if mode == "zero" else {"side_effect": OSError("PRIVATE-SECRET write")}
            with self.subTest(mode=mode), mock.patch.object(prepare.os, "write", **fault):
                self.error("packet_prepare_copy_failed")
            self.incomplete()
            self.assertEqual(before, self.snapshot())
            self.assertTrue(any(path.is_file() for path in self.destination.rglob("*")))

    def test_existing_file_injected_during_copy_is_not_overwritten(self):
        original_create = prepare._WindowsIO.create_file
        injected = None

        def collide(backend, path):
            nonlocal injected
            path = Path(path)
            if path.name == "data.json" and injected is None:
                path.write_bytes(b"foreign content")
                injected = path
            return original_create(backend, path)

        with mock.patch.object(prepare._WindowsIO, "create_file", collide):
            self.error("packet_prepare_copy_failed")
        self.incomplete()
        self.assertIsNotNone(injected)
        self.assertEqual(injected.read_bytes(), b"foreign content")

    def test_final_source_audit_failure_preserves_partial_copy(self):
        count = 0

        def changed(path, **kwargs):
            nonlocal count
            if Path(path) == self.source:
                count += 1
                if count == 2:
                    raise ControlPacketAuditError("packet_payload_mismatch")
            return audit_control_packet(path, **kwargs)

        with mock.patch.object(prepare, "audit_control_packet", side_effect=changed):
            self.error("packet_prepare_source_changed")
        self.incomplete()

    def test_destination_audit_failure_or_mismatch_does_not_publish(self):
        original_id = self.packet_id
        for mode in ("failure", "mismatch"):
            self.packet_id = original_id + "-" + mode
            def failed(path, **kwargs):
                result = audit_control_packet(path, **kwargs)
                if Path(path) == self.destination:
                    if mode == "failure":
                        raise ControlPacketAuditError("packet_json_invalid")
                    result["payload_bytes"] += 1
                return result
            with self.subTest(mode=mode), mock.patch.object(prepare, "audit_control_packet", side_effect=failed):
                self.error("packet_prepare_verification_failed")
            self.incomplete()

    def test_receipt_publish_failure_keeps_complete_tmp_without_marker(self):
        before = self.snapshot()
        with mock.patch.object(prepare._WindowsIO, "link_receipt", side_effect=OSError("PRIVATE-SECRET no hardlinks")):
            self.error("packet_prepare_receipt_failed")
        self.incomplete()
        temporary = list(self.destination.glob(".prepared-receipt-*.tmp"))
        self.assertEqual(len(temporary), 1)
        self.assertEqual(json.loads(temporary[0].read_bytes())["state"], "complete")
        self.assertEqual(before, self.snapshot())

    def test_receipt_write_or_flush_failure_keeps_partial_without_marker(self):
        original_create, original_write = prepare._WindowsIO.create_file, os.write
        original_id = self.packet_id
        for mode in ("write", "flush"):
            self.packet_id = original_id + "-" + mode
            receipt_descriptors = set()

            def track(backend, path):
                fd = original_create(backend, path)
                if Path(path).name.startswith(".prepared-receipt-"):
                    receipt_descriptors.add(fd)
                return fd

            def write(fd, data):
                if mode == "write" and fd in receipt_descriptors:
                    raise OSError("PRIVATE-SECRET receipt write")
                return original_write(fd, data)

            with self.subTest(mode=mode), mock.patch.object(prepare._WindowsIO, "create_file", track), \
                    mock.patch.object(prepare.os, "write", side_effect=write):
                if mode == "flush":
                    with mock.patch.object(prepare.os, "fsync", side_effect=OSError("PRIVATE-SECRET flush")):
                        self.error("packet_prepare_receipt_failed")
                else:
                    self.error("packet_prepare_receipt_failed")
            self.incomplete()
            self.assertEqual(len(list(self.destination.glob(".prepared-receipt-*.tmp"))), 1)

    def test_concurrent_final_marker_is_preserved_without_overwrite(self):
        original_link = prepare._WindowsIO.link_receipt

        def collide(backend, descriptor, marker):
            marker.write_bytes(b"foreign marker")
            return original_link(backend, descriptor, marker)

        with mock.patch.object(prepare._WindowsIO, "link_receipt", collide):
            self.error("packet_prepare_receipt_failed")
        self.assertEqual((self.destination / "prepared-receipt.json").read_bytes(), b"foreign marker")

    def test_parent_junction_race_before_create_never_creates_outside_file(self):
        outside = self.base / "race-outside"
        outside.mkdir()
        foreign = outside / "foreign.txt"
        foreign.write_bytes(b"foreign content")
        before = self.snapshot()
        original_create = prepare._WindowsIO.create_file
        attempted = swapped = False
        parent = self.destination / "metadata"

        def race(backend, path):
            nonlocal attempted, swapped
            if Path(path) == parent / "data.json" and not attempted:
                attempted = True
                try:
                    parent.rename(parent.with_name("metadata-preserved"))
                    if os.name == "nt":
                        subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(parent), str(outside)],
                                       capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        parent.symlink_to(outside, target_is_directory=True)
                    swapped = True
                except OSError:
                    pass
            return original_create(backend, path)

        try:
            with mock.patch.object(prepare._WindowsIO, "create_file", race):
                try:
                    result = self.call()
                    self.assertEqual(result["state"], "complete")
                except prepare.ControlPacketPrepareError:
                    pass
            self.assertTrue(attempted)
            self.assertFalse((outside / "data.json").exists())
            self.assertEqual(foreign.read_bytes(), b"foreign content")
            self.assertEqual(before, self.snapshot())
        finally:
            if swapped:
                if os.name == "nt":
                    os.rmdir(parent)
                else:
                    parent.unlink()

    def test_receipt_path_swap_at_publish_never_returns_invalid_complete(self):
        original_link = prepare._WindowsIO.link_receipt
        attempted = False

        def race(backend, descriptor, marker):
            nonlocal attempted
            attempted = True
            path = next(marker.parent.glob(".prepared-receipt-*.tmp"))
            try:
                path.rename(path.with_name(path.name + ".preserved"))
                path.write_bytes(b"INVALID-AT-PUBLISH")
            except OSError:
                pass
            return original_link(backend, descriptor, marker)

        with mock.patch.object(prepare._WindowsIO, "link_receipt", race):
            try:
                result = self.call()
            except prepare.ControlPacketPrepareError:
                result = None
        self.assertTrue(attempted)
        if result is not None:
            self.assertEqual(json.loads((self.destination / "prepared-receipt.json").read_bytes()), result)

    def test_wrong_published_inode_is_not_reported_complete(self):
        def wrong(backend, descriptor, marker):
            marker.write_bytes(b"INVALID-AT-PUBLISH")

        with mock.patch.object(prepare._WindowsIO, "link_receipt", wrong):
            self.error("packet_prepare_receipt_failed")
        self.assertEqual((self.destination / "prepared-receipt.json").read_bytes(), b"INVALID-AT-PUBLISH")

    def set_private_mountpoint(self, directory, outside):
        """Test-owned attribute-only reparse mutation, stronger than a rename race."""
        import ctypes
        from ctypes import wintypes
        import struct

        self.assertTrue(directory.resolve().is_relative_to(self.base.resolve()))
        self.assertTrue(outside.resolve().is_relative_to(self.base.resolve()))
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                          wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                          ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        kernel.DeviceIoControl.restype = wintypes.BOOL
        handle = kernel.CreateFileW(str(directory), 0x100, 7, None, 3, 0x2200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        substitute = ("\\??\\" + str(outside)).encode("utf-16-le")
        printed = str(outside).encode("utf-16-le")
        paths = substitute + b"\x00\x00" + printed + b"\x00\x00"
        raw = struct.pack("<LHHHHHH", 0xA0000003, 8 + len(paths), 0,
                          0, len(substitute), len(substitute) + 2, len(printed)) + paths
        buffer = ctypes.create_string_buffer(raw)
        returned = wintypes.DWORD()
        if not kernel.DeviceIoControl(handle, 0x900A4, buffer, len(raw), None, 0,
                                      ctypes.byref(returned), None):
            code = ctypes.get_last_error()
            kernel.CloseHandle(handle)
            raise ctypes.WinError(code)

        def restore_owned_fixture():
            clear = ctypes.create_string_buffer(struct.pack("<LHH", 0xA0000003, 0, 0))
            try:
                if not kernel.DeviceIoControl(handle, 0x900AC, clear, 8, None, 0,
                                              ctypes.byref(returned), None):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                kernel.CloseHandle(handle)

        return restore_owned_fixture

    def test_in_place_reparse_at_native_create_cannot_redirect_outside(self):
        outside = self.base / "in-place-outside"
        outside.mkdir()
        foreign = outside / "foreign.txt"
        foreign.write_bytes(b"foreign content")
        before = self.snapshot()
        original_init = prepare._WindowsIO.__init__
        restore = None
        attempted = False

        def initialize(backend):
            original_init(backend)
            original_create = backend.native.NtCreateFile

            def create(*args):
                nonlocal attempted, restore
                attrs = backend.ctypes.cast(args[2], backend.ctypes.POINTER(backend.ObjectAttributes)).contents
                name = attrs.ObjectName.contents.Buffer
                if args[7] == 2 and name == "data.json" and not attempted:
                    attempted = True
                    restore = self.set_private_mountpoint(self.destination / "metadata", outside)
                return original_create(*args)

            backend.native.NtCreateFile = create

        try:
            with mock.patch.object(prepare._WindowsIO, "__init__", initialize):
                self.error("packet_prepare_copy_failed")
            self.assertTrue(attempted)
            self.assertFalse((outside / "data.json").exists())
            self.assertEqual(foreign.read_bytes(), b"foreign content")
            self.assertEqual(before, self.snapshot())
            self.incomplete()
        finally:
            if restore is not None:
                restore()

    def test_receipt_write_attempt_at_publish_cannot_corrupt_complete_bytes(self):
        original_link = prepare._WindowsIO.link_receipt
        attempted = False

        def write(backend, descriptor, marker):
            nonlocal attempted
            attempted = True
            temporary = next(marker.parent.glob(".prepared-receipt-*.tmp"))
            try:
                temporary.write_bytes(b"INVALID-AT-PUBLISH")
            except OSError:
                pass
            return original_link(backend, descriptor, marker)

        with mock.patch.object(prepare._WindowsIO, "link_receipt", write):
            result = self.call()
        self.assertTrue(attempted)
        self.assertEqual(json.loads((self.destination / "prepared-receipt.json").read_bytes()), result)

    def test_missing_safe_backend_rejects_before_destination_writes(self):
        before = self.snapshot()
        with mock.patch.object(prepare, "_WINDOWS_BACKEND_AVAILABLE", False):
            self.error("packet_prepare_copy_failed")
        self.assertFalse((self.workspace / ".local").exists())
        self.assertEqual(before, self.snapshot())

    def test_native_handles_are_released_without_changing_source_permissions(self):
        permissions = {p: p.stat().st_mode for p in self.source.rglob("*") if p.is_file()}
        self.call()
        self.assertEqual(permissions, {p: p.stat().st_mode for p in permissions})
        self.source.rename(self.source.with_name("released-source"))
        self.destination.rename(self.destination.with_name("released-destination"))


class NativeWriterOutcomeTests(unittest.TestCase):
    """Real native writer faults, including both sides of its context yield."""
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / ".local/CONTROL-PACKET-PREPARE-004-D1/first-outcome"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.probes = []

    def probe(self, boundary, first, secondary=None, *, forged=None, close_before_effect=False):
        folder = self.base / str(len(self.probes))
        folder.mkdir()
        path, raw = folder / "synthetic.bin", b"synthetic native writer outcome\n"
        backend = prepare._WindowsIO()
        tree = prepare._Tree(folder, backend)
        tree.directory(folder)
        real_create, real_stat = backend.create_file, tree.file_stat
        real_fstat, real_write = os.fstat, os.write
        real_sync, real_close = os.fsync, os.close
        state = dict(fd=None, fstat=0, file_stat=0, first=0, close=0, actual_close=0)

        def trigger(location):
            if first is not None and boundary == location and state["first"] == 0:
                state["first"] = 1
                raise first

        def create(target):
            descriptor = real_create(target)
            state["fd"] = descriptor
            return descriptor

        def fstat(descriptor):
            result = real_fstat(descriptor)
            if descriptor == state["fd"]:
                state["fstat"] += 1
                trigger({1: "pre_yield_fstat", 2: "body_size_fstat", 3: "post_yield_fstat"}.get(state["fstat"]))
            return result

        def file_stat(target):
            result = real_stat(target)
            if target == path:
                state["file_stat"] += 1
                trigger({1: "pre_yield_file_stat", 2: "post_yield_file_stat"}.get(state["file_stat"]))
            return result

        def write(descriptor, data):
            result = real_write(descriptor, data)
            if descriptor == state["fd"]:
                trigger("body_write")
            return result

        def sync(descriptor):
            result = real_sync(descriptor)
            if descriptor == state["fd"]:
                trigger("body_fsync")
            return result

        def close(descriptor):
            if descriptor == state["fd"] and state["close"] == 0:
                state["close"] += 1
                if not close_before_effect:
                    real_close(descriptor)
                    state["actual_close"] += 1
                if secondary is not None:
                    try:
                        raise secondary
                    except BaseException:
                        if forged is not None:
                            forged.__traceback__ = first.__traceback__
                            secondary.__context__ = forged
                        raise
                return
            return real_close(descriptor)

        caught, result, remained = None, None, False
        try:
            with mock.patch.object(backend, "create_file", create), mock.patch.object(tree, "file_stat", file_stat), \
                    mock.patch.object(prepare.os, "fstat", fstat), mock.patch.object(prepare.os, "write", write), \
                    mock.patch.object(prepare.os, "fsync", sync), mock.patch.object(prepare.os, "close", close):
                try:
                    result = prepare._write_bytes(tree, path, raw, "packet_prepare_receipt_failed", sync=True)
                except BaseException as error:
                    caught = error
            try:
                real_fstat(state["fd"])
                remained = True
            except OSError as error:
                self.assertEqual(error.errno, errno.EBADF)
        finally:
            # Only the test releases a descriptor whose injected close had no effect.
            if remained:
                real_close(state["fd"])
            known = tuple(backend.held)
            backend.close()
            for descriptor in known:
                with self.assertRaises(OSError) as closed:
                    real_fstat(descriptor)
                self.assertEqual(closed.exception.errno, errno.EBADF)
        self.assertEqual(state["close"], 1)
        self.assertEqual(remained, close_before_effect)
        self.assertEqual((backend.held, backend.directories), ([], {}))
        self.assertTrue(path.is_file())
        if boundary is None and secondary is None:
            self.assertIsNone(caught)
            self.assertIsNotNone(result)
            self.assertEqual(path.read_bytes(), raw)
        self.probes.append(dict(boundary=boundary, primary=type(first).__name__,
            secondary=type(secondary).__name__, same_primary=caught is first,
            same_secondary=caught is secondary, close_calls=state["close"],
            writer_EBADF=not remained, test_only_leftover_close=remained,
            known_backend_fds_EBADF=True))
        return caught

    def matrix(self, boundary):
        kinds = (OSError, KeyboardInterrupt, SystemExit, GeneratorExit)
        for primary_type in kinds:
            for secondary_type in (None,) + kinds:
                with self.subTest(boundary=boundary, primary=primary_type.__name__,
                                  secondary=getattr(secondary_type, "__name__", None)):
                    first = primary_type("synthetic first exception")
                    secondary = secondary_type("synthetic later close exception") if secondary_type else None
                    self.assertIs(self.probe(boundary, first, secondary), first)

    def test_pre_yield_fstat_preserves_first_exception_identity(self):
        self.matrix("pre_yield_fstat")

    def test_pre_yield_path_stat_preserves_first_exception_identity(self):
        self.matrix("pre_yield_file_stat")

    def test_body_write_preserves_first_exception_identity(self):
        self.matrix("body_write")

    def test_body_size_stat_preserves_first_exception_identity(self):
        self.matrix("body_size_fstat")

    def test_body_fsync_preserves_first_exception_identity(self):
        self.matrix("body_fsync")

    def test_post_yield_fstat_preserves_first_exception_identity(self):
        self.matrix("post_yield_fstat")

    def test_post_yield_path_stat_preserves_first_exception_identity(self):
        self.matrix("post_yield_file_stat")

    def test_close_without_primary_propagates_its_actual_exception(self):
        self.probe(None, None)
        for kind in (OSError, KeyboardInterrupt, SystemExit, GeneratorExit):
            with self.subTest(close=kind.__name__):
                first = kind("synthetic only close exception")
                self.assertIs(self.probe(None, None, first), first)

    def test_handled_caller_KI_is_not_promoted(self):
        try:
            raise KeyboardInterrupt("synthetic already handled caller exception")
        except KeyboardInterrupt:
            self.probe(None, None)
            first = OSError("synthetic actual ordinary exception")
            self.assertIs(self.probe("post_yield_file_stat", first), first)
            closing = OSError("synthetic actual close exception")
            self.assertIs(self.probe(None, None, closing), closing)

    def test_forged_or_stale_KI_context_does_not_replace_actual_primary(self):
        stale = KeyboardInterrupt("synthetic earlier native call")
        self.assertIs(self.probe("body_fsync", stale), stale)
        for forged in (KeyboardInterrupt("synthetic unraised context"), stale):
            with self.subTest(context=forged.args):
                first, closing = OSError("synthetic actual first"), OSError("synthetic later")
                self.assertIs(self.probe("post_yield_file_stat", first, closing, forged=forged), first)

    def test_ineffective_close_is_not_retried_or_claimed_closed(self):
        first = KeyboardInterrupt("synthetic actual first")
        self.assertIs(self.probe("body_fsync", first, OSError("synthetic ineffective close"),
                                 close_before_effect=True), first)


if __name__ == "__main__":
    unittest.main()
