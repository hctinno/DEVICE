"""Synthetic, local-only contract tests; no collected source payloads."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import types
import unittest
from unittest import mock
import zipfile

from labflow import control_packet_audit as audit


def digest(data):
    return hashlib.sha256(data).hexdigest()


def zip_bytes(*, compression=zipfile.ZIP_DEFLATED, name="sample.txt", data=b"sample"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        archive.writestr(name, data)
    return buffer.getvalue()


def central_extra(raw, extra, *, zip64_sizes=False):
    raw = bytearray(raw)
    central = raw.index(b"PK\x01\x02")
    end = raw.rindex(b"PK\x05\x06")
    name_length, old_extra_length = struct.unpack_from("<HH", raw, central + 28)
    insertion = central + 46 + name_length + old_extra_length
    struct.pack_into("<H", raw, central + 30, old_extra_length + len(extra))
    struct.pack_into("<I", raw, end + 12, struct.unpack_from("<I", raw, end + 12)[0] + len(extra))
    if zip64_sizes:
        struct.pack_into("<II", raw, central + 20, 0xFFFFFFFF, 0xFFFFFFFF)
    raw[insertion:insertion] = extra
    return bytes(raw)


class ControlPacketAuditTests(unittest.TestCase):
    def setUp(self):
        fixture_root = Path(__file__).resolve().parents[1] / ".local" / "CONTROL-PACKET-002-D1" / "fixtures"
        fixture_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=fixture_root)
        self.addCleanup(self.temp.cleanup)
        self.packet = Path(self.temp.name) / "packet"
        self.packet.mkdir()
        self.index = {
            "request_id": "DEV-CONTROL-SOURCES-008",
            "revision": "SYNTHETIC-v1",
            "source_code_executed": False,
            "runtime_or_hardware_support_confirmed": False,
            "public_export_allowed": False,
            "files": [],
            "observation": {"secret": "DO-NOT-RETURN", "serial": "PRIVATE-SERIAL"},
        }
        self.payload("readme.html", b"<html>synthetic only</html>")
        self.pin = self.save_index()

    def payload(self, path, data):
        destination = self.packet.joinpath(*path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        self.index["files"] = [row for row in self.index["files"] if row["path"] != path]
        self.index["files"].append({"path": path, "bytes": len(data), "sha256": digest(data)})
        return destination

    def save_index(self, raw=None):
        if raw is None:
            raw = json.dumps(self.index, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        (self.packet / "intake-v1.json").write_bytes(raw)
        self.pin = digest(raw)
        return self.pin

    def run_audit(self):
        return audit.audit_control_packet(self.packet, expected_index_sha256=self.pin)

    def error(self, code, action=None):
        with self.assertRaises(audit.ControlPacketAuditError) as caught:
            (action or self.run_audit)()
        error = caught.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.code, code)
        self.assertEqual(str(error), code)
        self.assertEqual(error.args, (code,))
        self.assertIsNone(error.__context__)
        for forbidden in (str(self.packet), "DO-NOT-RETURN", "PRIVATE-SERIAL", "readme.html"):
            self.assertNotIn(forbidden, repr(error))

    def test_mixed_success_exact_detached_summary_and_no_writes(self):
        self.payload("metadata/data.JSON", b'{"nested":[true,null,3.5]}')
        self.payload("source.py", b"raise RuntimeError('MUST NOT IMPORT')")
        self.payload("example.zip", zip_bytes(data=b"abc"))
        self.payload("other.zip", zip_bytes(compression=zipfile.ZIP_STORED, data=b"xy"))
        self.payload("opaque.tar.gz", b"opaque TAR.GZ is SHA-only, not a gzip validation")
        self.save_index()
        before = {p.relative_to(self.packet).as_posix(): p.read_bytes()
                  for p in self.packet.rglob("*") if p.is_file()}
        original_open = os.open

        def readonly_open(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            return original_open(path, flags, *args, **kwargs)

        with mock.patch.object(audit.os, "open", side_effect=readonly_open):
            result = self.run_audit()
        self.assertEqual(result, {
            "schema_version": 1,
            "kind": "control_packet_audit",
            "request_id": "DEV-CONTROL-SOURCES-008",
            "revision": "SYNTHETIC-v1",
            "index_sha256": self.pin,
            "payload_file_count": 6,
            "payload_bytes": sum(row["bytes"] for row in self.index["files"]),
            "json_file_count": 1,
            "zip_crc_checked_count": 2,
            "zip_entry_count": 2,
            "zip_uncompressed_bytes": 5,
            "zip_crc_status": "passed",
            "tar_gz_sha_only_count": 1,
            "read_verification_scope": "listed_bytes_json_zip_crc_at_read_time",
            "public_export_allowed": False,
            "source_code_executed": False,
            "runtime_or_hardware_support_confirmed": False,
            "hardware_verified": False,
            "state_mutations": 0,
        })
        self.assertEqual(before, {p.relative_to(self.packet).as_posix(): p.read_bytes()
                                  for p in self.packet.rglob("*") if p.is_file()})
        result["revision"] = "caller-change"
        self.assertEqual(self.run_audit()["revision"], "SYNTHETIC-v1")
        self.assertNotIn("DO-NOT-RETURN", json.dumps(result))

    def test_no_zip_status_and_unlisted_files_are_not_imported(self):
        (self.packet / "unlisted.py").write_bytes(b"raise Exception('unlisted')")
        result = self.run_audit()
        self.assertEqual(result["zip_crc_status"], "not_present")
        self.assertEqual(result["zip_crc_checked_count"], 0)
        self.assertEqual(result["payload_file_count"], 1)

    def test_invalid_arguments_before_filesystem_access(self):
        with mock.patch.object(audit.os, "lstat", side_effect=AssertionError("filesystem access")):
            for expected in (None, False, 42, "A" * 64, "a" * 63, "z" * 64):
                with self.subTest(expected=expected):
                    self.error("packet_invalid_argument", lambda: audit.audit_control_packet(
                        self.packet, expected_index_sha256=expected))
            for root in (None, b"bytes", "", "\\\\server\\share", "//server/share", "x\x00y"):
                with self.subTest(root=root):
                    self.error("packet_invalid_argument", lambda: audit.audit_control_packet(
                        root, expected_index_sha256=self.pin))

    def test_missing_packet_or_index_is_sanitized(self):
        self.error("packet_unavailable", lambda: audit.audit_control_packet(
            self.packet / "missing", expected_index_sha256=self.pin))
        (self.packet / "intake-v1.json").unlink()
        self.error("packet_unavailable")

    def test_index_hash_is_checked_before_parsing(self):
        (self.packet / "intake-v1.json").write_bytes(b"not JSON and PRIVATE-SERIAL")
        self.error("packet_index_mismatch")

    def test_index_strict_json(self):
        for raw in (b"\xff", b"{", b"{} trailing", b'{"x":1,"x":2}',
                    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e9999}', b"[]",
                    b"[" * 2000 + b"]" * 2000, b"\xef\xbb\xbf{}"):
            with self.subTest(raw=raw[:30]):
                self.save_index(raw)
                self.error("packet_index_invalid")

    def test_index_one_mib_cap(self):
        self.index["observation"] = "a" * (1024 * 1024)
        self.save_index()
        self.error("packet_limit_exceeded")

    def test_index_identity_and_flags(self):
        for key, values in {
            "request_id": ["OTHER", None, 1],
            "revision": [None, "", "..", "a/b", "한글", "a" * 151],
            "source_code_executed": [True, 0, None],
            "runtime_or_hardware_support_confirmed": [True, 0, None],
            "public_export_allowed": [True, 0, None],
        }.items():
            original = self.index[key]
            for value in values:
                with self.subTest(key=key, value=value):
                    self.index[key] = value
                    self.save_index()
                    self.error("packet_index_invalid")
            self.index[key] = original
        del self.index["public_export_allowed"]
        self.save_index()
        self.error("packet_index_invalid")

    def test_file_count_and_row_shape(self):
        for files in (None, {}, [], ["row"], [{"path": "x"}], self.index["files"] * 129):
            with self.subTest(shape=type(files).__name__, count=len(files) if files is not None else None):
                self.index["files"] = files
                self.save_index()
                self.error("packet_index_invalid" if not isinstance(files, list) or len(files) <= 128
                           else "packet_limit_exceeded")

    def test_declared_size_and_hash_types(self):
        row = self.index["files"][0]
        for key, values in {"bytes": [-1, True, 1.0, "1", None],
                            "sha256": [None, 1, "f" * 63, "A" * 64, "x" * 64]}.items():
            original = row[key]
            for value in values:
                with self.subTest(key=key, value=value):
                    row[key] = value
                    self.save_index()
                    self.error("packet_index_invalid")
            row[key] = original

    def test_declared_payload_and_total_caps_before_payload_open(self):
        self.index["files"][0]["bytes"] = 64 * 1024 * 1024 + 1
        self.save_index()
        self.error("packet_limit_exceeded")
        self.index["files"] = [{"path": f"file-{i}.bin", "bytes": 64 * 1024 * 1024,
                                 "sha256": "0" * 64} for i in range(3)]
        self.save_index()
        self.error("packet_limit_exceeded")

    def test_actual_oversized_file_is_rejected_before_open(self):
        with (self.packet / "readme.html").open("wb") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        self.error("packet_limit_exceeded")

    def test_manifest_path_rejections(self):
        for path in (None, "", "/outside", "C:/outside", "x:stream", "a\\b", "a//b", "./x",
                     "a/../x", "a/./x", "a/", "a\x00b", "a\nb", "NUL", "con.txt", "AUX.json",
                     "a/COM1", "Lpt9.zip", "com¹.txt", "CONIN$", "a. ", "x?y", "intake-v1.json"):
            with self.subTest(path=path):
                self.index["files"][0]["path"] = path
                self.save_index()
                self.error("packet_path_invalid")

    def test_duplicate_and_windows_case_alias_paths(self):
        for path in ("readme.html", "README.HTML"):
            with self.subTest(path=path):
                self.index["files"] = [self.index["files"][0], dict(self.index["files"][0], path=path)]
                self.save_index()
                self.error("packet_path_invalid")
                self.index["files"] = self.index["files"][:1]

    def test_payload_regular_file_is_checked_before_open(self):
        (self.packet / "readme.html").unlink()
        (self.packet / "readme.html").mkdir()
        original_open = os.open

        def reject_payload_open(path, *args, **kwargs):
            self.assertNotEqual(Path(path).name, "readme.html")
            return original_open(path, *args, **kwargs)

        with mock.patch.object(audit.os, "open", side_effect=reject_payload_open):
            self.error("packet_path_invalid")

    def test_reparse_leaf_ancestor_and_packet_root_are_rejected(self):
        original_lstat = os.lstat
        nested = self.payload("nested/data.txt", b"data")
        self.save_index()
        for target in (self.packet, nested.parent, nested, self.packet / "intake-v1.json"):
            with self.subTest(target=target.name):
                def reparse(path, *args, **kwargs):
                    result = original_lstat(path, *args, **kwargs)
                    if Path(path) == target:
                        return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                    return result
                with mock.patch.object(audit.os, "lstat", side_effect=reparse):
                    self.error("packet_path_invalid")

    def test_symlink_mode_is_rejected_without_following_target(self):
        original_lstat = os.lstat

        def symlink(path, *args, **kwargs):
            if Path(path) == self.packet / "readme.html":
                return types.SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_file_attributes=0)
            return original_lstat(path, *args, **kwargs)

        with mock.patch.object(audit.os, "lstat", side_effect=symlink):
            self.error("packet_path_invalid")

    def test_nonregular_device_mode_is_rejected_before_open(self):
        original_lstat = os.lstat

        def fifo(path, *args, **kwargs):
            if Path(path) == self.packet / "readme.html":
                return types.SimpleNamespace(st_mode=stat.S_IFIFO | 0o600, st_file_attributes=0)
            return original_lstat(path, *args, **kwargs)

        with mock.patch.object(audit.os, "lstat", side_effect=fifo):
            self.error("packet_path_invalid")

    def test_file_identity_change_during_open_is_rejected(self):
        original_fstat = os.fstat

        def changed(fd):
            result = original_fstat(fd)
            return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0,
                                         st_dev=result.st_dev, st_ino=result.st_ino + 1)

        with mock.patch.object(audit.os, "fstat", side_effect=changed):
            self.error("packet_path_invalid")

    def test_payload_missing_size_and_digest_mismatch(self):
        path = self.packet / "readme.html"
        path.write_bytes(b"changed")
        self.error("packet_payload_mismatch")
        row = self.index["files"][0]
        row["bytes"] = len(b"changed")
        self.save_index()
        self.error("packet_payload_mismatch")
        path.unlink()
        self.error("packet_unavailable")

    def test_json_payload_is_strict_and_bounded(self):
        for raw in (b"\xff", b"{", b'{"x":1,"x":2}', b'{"n":NaN}', b'{"n":1e9999}',
                    b"[" * 2000 + b"]" * 1999):
            with self.subTest(raw=raw[:30]):
                self.payload("payload.json", raw)
                self.save_index()
                self.error("packet_json_invalid")
        self.payload("payload.json", b'"' + b"a" * (8 * 1024 * 1024) + b'"')
        self.save_index()
        self.error("packet_limit_exceeded")

    def test_zero_byte_regular_payload_is_valid(self):
        self.payload("empty.bin", b"")
        self.save_index()
        self.assertEqual(self.run_audit()["payload_file_count"], 2)

    def test_zip_crc_corruption_even_with_matching_payload_hash(self):
        data = bytearray(zip_bytes(compression=zipfile.ZIP_STORED, data=b"UNIQUE-CONTENT"))
        data[data.index(b"UNIQUE-CONTENT")] ^= 1
        self.payload("corrupt.zip", bytes(data))
        self.save_index()
        self.error("packet_zip_invalid")

    def test_deflate_empty_and_multiple_output_chunks_are_valid(self):
        for data in (b"", b"A" * 200000, bytes(range(256)) * 600):
            with self.subTest(length=len(data)):
                self.payload("valid.zip", zip_bytes(data=data))
                self.save_index()
                self.assertEqual(self.run_audit()["zip_uncompressed_bytes"], len(data))

    def test_zip_entry_budget_is_packet_wide(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for i in range(1001):
                archive.writestr(str(i), b"")
        self.payload("first.zip", buffer.getvalue())
        self.payload("second.zip", buffer.getvalue())
        self.save_index()
        self.error("packet_limit_exceeded")

    def test_zip_malformed_unsupported_and_encrypted_fail_closed(self):
        encrypted = bytearray(zip_bytes())
        local_flags = encrypted.index(b"PK\x03\x04") + 6
        central_flags = encrypted.index(b"PK\x01\x02") + 8
        encrypted[local_flags] |= 1
        encrypted[central_flags] |= 1
        unsupported = bytearray(zip_bytes())
        struct.pack_into("<H", unsupported, unsupported.index(b"PK\x01\x02") + 10, 99)
        for raw in (b"not zip", zip_bytes()[:-10], bytes(encrypted), bytes(unsupported),
                    zip_bytes(compression=zipfile.ZIP_BZIP2), zip_bytes(compression=zipfile.ZIP_LZMA)):
            with self.subTest(size=len(raw)):
                self.payload("bad.zip", raw)
                self.save_index()
                self.error("packet_zip_invalid")

    def test_zip64_local_headers_and_extras_are_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            with archive.open("sample.txt", "w", force_zip64=True) as member:
                member.write(b"synthetic")
        variants = [buffer.getvalue()]
        for offset in (18, 22):
            raw = bytearray(zip_bytes())
            struct.pack_into("<I", raw, offset, 0xFFFFFFFF)
            variants.append(bytes(raw))
        # Even an unnecessary ZIP64 extra with ordinary sizes is unsupported.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("sample.txt")
            info.extra = struct.pack("<HH", 1, 0)
            archive.writestr(info, b"synthetic")
        variants.append(buffer.getvalue())
        for number, raw in enumerate(variants):
            with self.subTest(variant=number):
                self.payload("zip64-local.zip", raw)
                self.save_index()
                self.error("packet_zip_invalid")

    def test_zip64_central_fields_and_extras_rejected_before_allocation(self):
        base = zip_bytes(compression=zipfile.ZIP_STORED, data=b"synthetic")
        variants = [central_extra(base, struct.pack("<HHQQ", 1, 16, 9, 9), zip64_sizes=True),
                    central_extra(base, struct.pack("<HH", 1, 0))]
        for offset, format_, sentinel in ((20, "<I", 0xFFFFFFFF), (24, "<I", 0xFFFFFFFF),
                                          (42, "<I", 0xFFFFFFFF), (34, "<H", 0xFFFF)):
            raw = bytearray(base)
            struct.pack_into(format_, raw, raw.index(b"PK\x01\x02") + offset, sentinel)
            variants.append(bytes(raw))
        for number, raw in enumerate(variants):
            with self.subTest(variant=number):
                self.payload("zip64-central.zip", raw)
                self.save_index()
                with mock.patch.object(audit.zipfile, "ZipFile", side_effect=AssertionError("allocated ZIP64")):
                    self.error("packet_zip_invalid")

    def test_unknown_well_formed_zip_extra_remains_supported(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("sample.txt")
            info.extra = struct.pack("<HH", 0xCAFE, 3) + b"abc"
            archive.writestr(info, b"synthetic")
        self.payload("ordinary-extra.zip", buffer.getvalue())
        self.save_index()
        self.assertEqual(self.run_audit()["zip_uncompressed_bytes"], 9)

    def test_local_header_flags_and_method_must_be_supported_and_match(self):
        for offset, value in ((6, 1), (6, 0x40), (6, 0x2000), (6, 8), (6, 0x800),
                              (6, 2), (8, 99), (8, zipfile.ZIP_STORED)):
            with self.subTest(offset=offset, value=value):
                raw = bytearray(zip_bytes())
                struct.pack_into("<H", raw, offset, value)
                self.payload("local-mismatch.zip", bytes(raw))
                self.save_index()
                self.error("packet_zip_invalid")

    def test_unsupported_flags_in_both_headers_are_rejected(self):
        raw = bytearray(zip_bytes())
        for offset in (6, raw.index(b"PK\x01\x02") + 8):
            struct.pack_into("<H", raw, offset, 0x2000)
        self.payload("unsupported-flags.zip", bytes(raw))
        self.save_index()
        self.error("packet_zip_invalid")

    def test_supported_utf8_local_and_central_headers_are_valid(self):
        self.payload("utf8.zip", zip_bytes(name="synthetic-\uac00.txt"))
        self.save_index()
        self.assertEqual(self.run_audit()["zip_entry_count"], 1)

    def test_local_crc_and_sizes_match_central_without_data_descriptor(self):
        for offset in (14, 18, 22):
            with self.subTest(offset=offset):
                raw = bytearray(zip_bytes())
                value = struct.unpack_from("<I", raw, offset)[0]
                struct.pack_into("<I", raw, offset, value ^ 1)
                self.payload("local-metadata.zip", bytes(raw))
                self.save_index()
                self.error("packet_zip_invalid")

    def test_supported_data_descriptor_local_zero_fields_are_valid(self):
        class Unseekable(io.BytesIO):
            def seek(self, *args, **kwargs):
                raise io.UnsupportedOperation("synthetic streaming sink")

        buffer = Unseekable()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("streamed.txt", b"synthetic")
        raw = buffer.getvalue()
        self.assertTrue(struct.unpack_from("<H", raw, 6)[0] & 8)
        self.payload("descriptor.zip", raw)
        self.save_index()
        self.assertEqual(self.run_audit()["zip_uncompressed_bytes"], 9)

    def test_zip_entry_limit_preflight(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for i in range(2001):
                archive.writestr(str(i), b"")
        self.payload("many.zip", buffer.getvalue())
        self.save_index()
        self.error("packet_limit_exceeded")

    def test_forged_zip_count_is_bounded_before_directory_allocation(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for i in range(2001):
                archive.writestr(str(i), b"")
        raw = bytearray(buffer.getvalue())
        end = raw.rindex(b"PK\x05\x06")
        struct.pack_into("<HH", raw, end + 8, 1, 1)
        self.payload("forged-count.zip", bytes(raw))
        self.save_index()
        with mock.patch.object(audit.zipfile, "ZipFile", side_effect=AssertionError("allocated first")):
            self.error("packet_limit_exceeded")

    def test_zip_single_and_total_uncompressed_preflight(self):
        for sizes in ((64 * 1024 * 1024 + 1,), (64 * 1024 * 1024,) * 3):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                for i in range(len(sizes)):
                    archive.writestr(str(i), b"x")
            raw = bytearray(buffer.getvalue())
            position = 0
            for size in sizes:
                position = raw.index(b"PK\x01\x02", position)
                struct.pack_into("<I", raw, position + 24, size)
                position += 4
            self.payload("huge.zip", bytes(raw))
            self.save_index()
            self.error("packet_limit_exceeded")

    def test_forged_zip_size_cannot_hide_decompressed_bytes(self):
        raw = bytearray(zip_bytes(data=b"A" * 100000))
        local = raw.index(b"PK\x03\x04")
        central = raw.index(b"PK\x01\x02")
        import zlib
        for offset in (local + 14, central + 16):
            struct.pack_into("<I", raw, offset, zlib.crc32(b"A"))
        for offset in (local + 22, central + 24):
            struct.pack_into("<I", raw, offset, 1)
        self.payload("forged.zip", bytes(raw))
        self.save_index()
        self.error("packet_zip_invalid")

    def test_archive_internal_paths_links_are_never_extracted(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../must-not-exist", b"synthetic")
            link = zipfile.ZipInfo("link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, "../../must-not-follow")
        self.payload("internal.zip", buffer.getvalue())
        self.save_index()
        self.assertEqual(self.run_audit()["zip_entry_count"], 2)
        self.assertFalse((self.packet.parent / "must-not-exist").exists())
        self.assertFalse((self.packet / "link").exists())

    def test_index_changed_or_removed_during_payload_read(self):
        original_open = os.open
        for remove in (False, True):
            with self.subTest(remove=remove):
                self.save_index()
                def change_index(path, *args, **kwargs):
                    if Path(path).name == "readme.html":
                        if remove:
                            (self.packet / "intake-v1.json").unlink()
                        else:
                            (self.packet / "intake-v1.json").write_bytes(b"{}")
                    return original_open(path, *args, **kwargs)
                with mock.patch.object(audit.os, "open", side_effect=change_index):
                    self.error("packet_index_changed")

    def test_io_error_does_not_expose_raw_exception_or_path(self):
        with mock.patch.object(audit.os, "open", side_effect=PermissionError(
                "PRIVATE-SERIAL DO-NOT-RETURN " + str(self.packet))):
            self.error("packet_unavailable")


if __name__ == "__main__":
    unittest.main()
