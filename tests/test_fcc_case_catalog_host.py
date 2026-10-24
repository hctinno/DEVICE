"""Host037 contracts on test-owned synthetic files and Windows native handles."""
from copy import deepcopy
import hashlib
import http.client
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import types
import unittest
from unittest import mock

from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject
from pypdf.constants import UserAccessPermissions
from io import BytesIO

from labflow import control_packet_prepare as native
from labflow import fcc_report_cases as cases
from tests.test_fcc_report_cases import fixture
from tests.test_document_extract import synthetic_pdf

host = (importlib.import_module("labflow.fcc_case_catalog_host")
        if importlib.util.find_spec("labflow.fcc_case_catalog_host") else None)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FccCaseCatalogHostTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(host, "037 explicit host loader is absent")
        self.assertEqual(os.name, "nt", "These are Windows-native execution contracts")
        root = Path(__file__).resolve().parents[1] / ".local" / "CASE-CATALOG-HOST037-D1" / "fixtures"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.inputs = self.base / "inputs"; self.inputs.mkdir()
        self.packet, self.pdfs, _ = fixture()
        self.source = self.inputs / "synthetic.pdf"; self.source.write_bytes(next(iter(self.pdfs.values())))
        self.policy = {"schema_version": 1, "sources": {sha: {"pages": [1], "mode": "accessibility",
            "basis_id": "SYNTHETIC-HOST037", "basis_sha256": "e" * 64} for sha in self.pdfs}}
        self.packet_file, self.scope_file, self.manifest_file = [self.inputs / name for name in ["packet.json", "scope.json", "manifest.json"]]
        self.config_file = self.base / "config.json"
        self.save_metadata()

    def descriptor(self, path):
        raw = path.read_bytes()
        return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}

    def save_config(self):
        self.config_file.write_bytes(encoded(self.config)); self.config_sha = digest(self.config_file.read_bytes())

    def save_metadata(self):
        self.packet_file.write_bytes(encoded(self.packet)); self.scope_file.write_bytes(encoded(self.policy))
        self.manifest = {"request_id": "DEV-HCT-FCC-CORPUS-012", "revision": "SYNTHETIC-HOST037", "files": [
            {"path": p.name, "sha256": digest(p.read_bytes()), "bytes": len(p.read_bytes())} for p in [self.packet_file, self.scope_file]]}
        self.manifest_file.write_bytes(encoded(self.manifest))
        self.config = {"schema_version": 1, "kind": "fcc_case_catalog_host_input",
            "manifest": self.descriptor(self.manifest_file), "packet": self.descriptor(self.packet_file),
            "page_scope": self.descriptor(self.scope_file), "packet_path": "packet.json", "page_scope_path": "scope.json",
            "pdf_sources": [self.descriptor(self.source)] if self.packet["documents"] else []}
        self.save_config()

    def call(self, **kwargs):
        return host.load_fcc_case_catalog(kwargs.pop("config_path", self.config_file),
            expected_config_sha256=kwargs.pop("expected_config_sha256", self.config_sha), **kwargs)

    def error(self, code, *, dependency=False, **kwargs):
        error_type = cases.FccReportCaseError if dependency else host.FccCaseCatalogHostError
        with self.assertRaises(ValueError) as caught:
            self.call(**kwargs)
        error = caught.exception
        self.assertIsInstance(error, error_type)
        self.assertEqual((error.code, str(error), error.args), (code, code, (code,)))
        self.assertIsNone(error.__context__); self.assertIsNone(error.__cause__)
        for forbidden in [str(self.base), "PRIVATE", "Traceback"]: self.assertNotIn(forbidden, repr(error))

    def snapshot(self):
        return {str(p): (p.read_bytes(), p.stat().st_dev, p.stat().st_ino, p.stat().st_size,
                        p.stat().st_mtime_ns, p.stat().st_mode) for p in self.base.rglob("*") if p.is_file()}

    def encrypt(self, permissions):
        writer = PdfWriter(); writer.append(PdfReader(BytesIO(self.source.read_bytes())))
        writer.encrypt("", owner_password="SYNTHETIC-OWNER", permissions_flag=permissions)
        stream = BytesIO(); writer.write(stream); writer.close(); raw = stream.getvalue()
        self.source.write_bytes(raw); sha = digest(raw)
        document = self.packet["documents"][0]; old = document["sha256"]
        document.update(sha256=sha, size_bytes=len(raw)); self.policy["sources"][sha] = self.policy["sources"].pop(old)
        for case in self.packet["cases"]:
            for claim in case["claims"]:
                for evidence in claim["evidence"]: evidence["source_sha256"] = sha
        self.save_metadata()

    def test_exact_genuine_catalog_receipt_and_source_unchanged(self):
        before = self.snapshot(); catalog, receipt = self.call()
        self.assertIs(type(catalog), cases.FccReportCaseCatalog)
        self.assertEqual(set(receipt), {"schema_version", "kind", "config_sha256", "metadata_preparation", "inputs", "page_scopes", "construction", "verification"})
        self.assertEqual((receipt["schema_version"], receipt["kind"], receipt["config_sha256"]), (1, "fcc_case_catalog_host_load", self.config_sha))
        self.assertEqual(set(receipt["metadata_preparation"]), {"provenance", "verification"})
        self.assertFalse(receipt["metadata_preparation"]["verification"]["source_pdf_bytes_verified"])
        self.assertFalse(receipt["metadata_preparation"]["verification"]["retained_literals_verified"])
        self.assertEqual(receipt["verification"], dict.fromkeys(["authority_or_rights_verified", "hardware_verified", "normative_compliance_verified", "currentness_verified", "execution_authorized"], False))
        self.assertEqual(receipt["construction"], {"catalog_type_exact": True, "document_count": 1, "case_count": 1,
            "citable_page_count": 1, "verified_evidence_literal_count": 13})
        self.assertEqual(before, self.snapshot())
        self.assertNotIn(str(self.base), json.dumps(receipt)); self.assertNotIn("PRIVATE-SYNTHETIC", json.dumps(receipt))

    def test_windows_pin_hash2pass_native1pass_and_all_handles_closed(self):
        opened, backends, byte_count, text_pages = [], [], [], []
        init, open_read, read, extract = native._WindowsIO.__init__, native._WindowsIO.open_read, os.read, PageObject.extract_text
        pdf_identity = (self.source.stat().st_dev, self.source.stat().st_ino)
        def initialize(backend): init(backend); backends.append(backend)
        def opening(backend, path, **kwargs):
            self.assertIs(kwargs.get("pin"), True)
            fd = open_read(backend, path, **kwargs); opened.append(fd); return fd
        def reading(fd, size):
            info = os.fstat(fd); raw = read(fd, size)
            if (info.st_dev, info.st_ino) == pdf_identity: byte_count.append(len(raw))
            return raw
        def extracting(page, *args, **kwargs):
            text_pages.append(page.pdf.get_page_number(page) + 1); return extract(page, *args, **kwargs)
        with mock.patch.object(native._WindowsIO, "__init__", new=initialize), mock.patch.object(native._WindowsIO, "open_read", new=opening), \
                mock.patch("os.read", new=reading), mock.patch.object(PageObject, "extract_text", new=extracting):
            self.call()
        self.assertEqual(sum(byte_count), 2 * self.source.stat().st_size); self.assertEqual(text_pages, [1])
        self.assertEqual(len(opened), 5)
        for fd in opened:
            with self.assertRaises(OSError): os.fstat(fd)
        self.assertTrue(all(not backend.held and not backend.directories for backend in backends))

    def test_no_write_copy_rename_link_audit_server_database_or_network_from_loader(self):
        with mock.patch.object(native._WindowsIO, "create_file", side_effect=AssertionError("write")), \
                mock.patch.object(native._WindowsIO, "link_receipt", side_effect=AssertionError("link")), \
                mock.patch.object(native, "prepare_control_packet", side_effect=AssertionError("prepare")), \
                mock.patch.object(native, "audit_control_packet", side_effect=AssertionError("audit")), \
                mock.patch("os.rename", side_effect=AssertionError("rename")), \
                mock.patch("os.chmod", side_effect=AssertionError("permission")), \
                mock.patch("sqlite3.connect", side_effect=AssertionError("DB")), \
                mock.patch("socket.socket", side_effect=AssertionError("network")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("process")):
            self.assertIs(type(self.call()[0]), cases.FccReportCaseCatalog)

    def test_config_input_types_and_pin_format_fail_without_coercing_callbacks(self):
        class Callback:
            def __fspath__(self): raise AssertionError("callback")
        for path in [None, False, {}, Callback(), lambda: self.config_file]:
            self.error("fcc_case_host_invalid_argument", config_path=path)
        for pin in [None, True, "A" * 64, "e" * 63]: self.error("fcc_case_host_invalid_argument", expected_config_sha256=pin)
        self.assertIs(type(self.call(config_path=str(self.config_file))[0]), cases.FccReportCaseCatalog)

    def test_unsupported_backend_fails_before_open_or_constructor(self):
        with mock.patch.object(native, "_WINDOWS_BACKEND_AVAILABLE", False), \
                mock.patch.object(native._WindowsIO, "open_read", side_effect=AssertionError("input read")) as opened, \
                mock.patch.object(cases.FccReportCaseCatalog, "__init__", side_effect=AssertionError("constructor")) as constructor:
            self.error("fcc_case_host_backend_unavailable")
        opened.assert_not_called(); constructor.assert_not_called()

    def test_config_hash_is_checked_before_json_and_originals_are_not_opened(self):
        self.config_file.write_bytes(b"PRIVATE invalid JSON")
        self.error("fcc_case_host_pin_mismatch")
        self.config_sha = digest(self.config_file.read_bytes())
        self.error("fcc_case_host_invalid_argument")

    def test_strict_config_keys_types_duplicate_utf8_nonfinite_and_depth_caps(self):
        original = deepcopy(self.config)
        for changes in [{"schema_version": True}, {"kind": "other"}, {"extra": False}, {"pdf_sources": False}]:
            self.config = {**original, **changes}; self.save_config(); self.error("fcc_case_host_invalid_argument")
        for raw in [b'\xff', b'[]', b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}']:
            self.config_file.write_bytes(raw); self.config_sha = digest(raw); self.error("fcc_case_host_invalid_argument")
        raw = encoded(original) + b" " * 65536; self.config_file.write_bytes(raw); self.config_sha = digest(raw)
        self.error("fcc_case_limit_exceeded", dependency=True)

    def test_absolute_local_suffix_and_lexical_paths_are_explicit(self):
        for path in ["config.json", "C:config.json", "https://example.invalid/x.json", r"\\server\share\x.json", r"\\?\C:\x.json", str(self.base / "x.txt"), str(self.base / ".." / "config.json")]:
            self.error("fcc_case_host_path_invalid", config_path=path)
        self.error("fcc_case_host_unavailable", config_path=self.base / "missing.json")
        self.error("fcc_case_host_path_invalid", config_path=self.inputs)

    def test_all_metadata_descriptor_fields_and_raw_pins_are_validated(self):
        original = deepcopy(self.config)
        for role in ["manifest", "packet", "page_scope"]:
            for update in [{"bytes": True}, {"bytes": 0}, {"sha256": "A" * 64}, {"extra": False}]:
                self.config = deepcopy(original); self.config[role].update(update); self.save_config()
                self.error("fcc_case_host_invalid_argument")
            self.config = deepcopy(original); self.config[role]["sha256"] = "0" * 64; self.save_config()
            self.error("fcc_case_host_pin_mismatch")

    def test_missing_original_pin_size_mismatch_and_source_set_do_not_fallback(self):
        original = deepcopy(self.config)
        self.config["pdf_sources"] = []; self.save_config(); self.error("fcc_case_invalid_sources", dependency=True)
        self.config = deepcopy(original); self.config["pdf_sources"][0]["bytes"] += 1; self.save_config()
        self.error("fcc_case_invalid_sources", dependency=True)
        self.config = deepcopy(original); self.save_config(); self.source.write_bytes(self.source.read_bytes()[:-1] + b"x")
        self.error("fcc_case_host_pin_mismatch")

    def test_duplicate_source_sha_and_declared_count_or_total_limits_precede_reads(self):
        source = self.config["pdf_sources"][0]
        self.config["pdf_sources"] = [deepcopy(source), deepcopy(source)]; self.save_config()
        self.error("fcc_case_invalid_sources", dependency=True)
        self.config["pdf_sources"] = [deepcopy(source)] * 17; self.save_config(); self.error("fcc_case_limit_exceeded", dependency=True)
        self.config["pdf_sources"] = [{**source, "bytes": 16 * 1024 * 1024 + 1}]; self.save_config()
        self.error("fcc_case_limit_exceeded", dependency=True)

    def test_bad_035_scope_is_rejected_before_any_pdf_read(self):
        next(iter(self.policy["sources"].values()))["pages"] = [2]; self.save_metadata()
        original = native._WindowsIO.open_read
        def no_original(backend, path, **kwargs):
            self.assertNotEqual(path, self.source, "source opened before035 validation")
            return original(backend, path, **kwargs)
        with mock.patch.object(native._WindowsIO, "open_read", new=no_original):
            self.error("fcc_case_invalid_evidence", dependency=True)

    def test_explicit_scope_none_and_selector_collision_never_imply_full_native(self):
        self.scope_file.write_bytes(b"null")
        self.config["page_scope"] = self.descriptor(self.scope_file); self.save_config()
        self.error("fcc_case_invalid_sources", dependency=True)
        self.save_metadata(); self.config["page_scope_path"] = self.config["packet_path"]; self.save_config()
        self.error("fcc_case_invalid_packet", dependency=True)

    def test_selector_nonstring_types_and_config_structure_limits_are_safe_errors(self):
        original = deepcopy(self.config)
        for value in [[], {}, None, False]:
            self.config = {**original, "packet_path": value}; self.save_config()
            self.error("fcc_case_invalid_packet", dependency=True)
        deep = None
        for _ in range(10): deep = [deep]
        for value in [deep, [0] * 2049]:
            self.config = {**original, "ignored": value}; self.save_config()
            self.error("fcc_case_limit_exceeded", dependency=True)

    def test_accessibility_copyfalse_integrity_and_permission_fail_before_native(self):
        self.encrypt(UserAccessPermissions.PRINT | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS)
        catalog, receipt = self.call()
        self.assertEqual(receipt["page_scopes"][0]["mode"], "accessibility")
        self.assertEqual(receipt["page_scopes"][0]["extraction"]["parser"]["name"], "pypdf-public-empty-user-password-accessibility-selected-pages")
        self.assertFalse(catalog.case("CASE-A")["documents"][0]["rights"]["public_redistribution_allowed"])
        for known in [False, None]:
            with mock.patch.object(PdfReader, "are_permissions_valid", new_callable=mock.PropertyMock, return_value=known), \
                    mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native")) as text:
                self.error("fcc_case_extraction_unavailable", dependency=True)
            text.assert_not_called()

    def test_print_only_and_native_mode_cannot_use_accessibility_scope(self):
        self.encrypt(UserAccessPermissions.PRINT)
        with mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native")) as text:
            self.error("fcc_case_extraction_unavailable", dependency=True)
        text.assert_not_called()
        self.encrypt(UserAccessPermissions.PRINT | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS)
        next(iter(self.policy["sources"].values()))["mode"] = "native_text"; self.save_metadata()
        with mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("copy native")) as text:
            self.error("fcc_case_extraction_unavailable", dependency=True)
        text.assert_not_called()

    def test_wrong_literal_is_real_constructor_failure_not_metadata_success(self):
        self.packet["cases"][0]["claims"][0]["evidence"][0]["quote"] = "PRIVATE wrong literal"
        self.save_metadata(); self.error("fcc_case_invalid_evidence", dependency=True)

    def test_verified_evidence_entry_count_is_not_unique_page_or_measurement_count(self):
        other = deepcopy(self.packet["cases"][0]); other["case_id"] = "CASE-B"; self.packet["cases"].append(other); self.save_metadata()
        receipt = self.call()[1]
        self.assertEqual(receipt["construction"]["verified_evidence_literal_count"], 26)
        self.assertEqual(receipt["construction"]["citable_page_count"], 1)

    def test_receipt_nested_keys_stable_role_sha_order_and_detachment(self):
        catalog, receipt = self.call()
        self.assertEqual([(r["role"], r["sha256"]) for r in receipt["inputs"]], sorted((r["role"], r["sha256"]) for r in receipt["inputs"]))
        for row in receipt["inputs"]:
            self.assertEqual(set(row), {"role", "sha256", "bytes", "identity", "mtime_ns", "mode"})
            self.assertEqual(len(row["identity"]), 2)
        row = receipt["page_scopes"][0]
        self.assertEqual(set(row), {"document_id", "source_sha256", "mode", "basis_id", "basis_sha256", "requested_pages", "extraction", "page_index"})
        self.assertEqual(row["requested_pages"], [1]); self.assertEqual([p["file_page"] for p in row["page_index"]], [1])
        row["page_index"].clear(); receipt["metadata_preparation"]["verification"].clear()
        self.assertEqual(len(catalog.case("CASE-A")["documents"][0]["page_index"]), 1)
        self.assertEqual(len(self.call()[1]["page_scopes"][0]["page_index"]), 1)

    def test_genuine_constructor_invoked_exactly_once_and_no_extraction_result_injection(self):
        original = cases.FccReportCaseCatalog.__init__
        count = []
        def construct(catalog, *args, **kwargs):
            count.append(kwargs["page_scope"]); return original(catalog, *args, **kwargs)
        with mock.patch.object(cases.FccReportCaseCatalog, "__init__", new=construct): self.call()
        self.assertEqual(len(count), 1); self.assertEqual(count[0], self.policy)

    def test_short_reads_are_accumulated_and_premature_eof_is_not_success(self):
        read = os.read
        with mock.patch("os.read", side_effect=lambda fd, size: read(fd, min(size, 17))): self.call()
        with mock.patch("os.read", return_value=b""):
            self.error("fcc_case_host_input_changed")

    def test_final_same_handle_rehash_detects_changed_bytes_without_returning_catalog(self):
        read = os.read; positions = {}; source_id = (self.source.stat().st_dev, self.source.stat().st_ino)
        def changed(fd, size):
            info = os.fstat(fd); identity = (info.st_dev, info.st_ino); raw = read(fd, size)
            if identity == source_id:
                positions.setdefault(fd, 0)
                if not raw: positions[fd] += 1
                elif positions[fd] and raw: return b"X" + raw[1:]
            return raw
        with mock.patch("os.read", new=changed): self.error("fcc_case_host_input_changed")

    def test_final_identity_mtime_and_mode_changes_never_publish_catalog(self):
        original_init, original_open, original_info = cases.FccReportCaseCatalog.__init__, native._WindowsIO.open_read, native._WindowsIO.info
        for field in ["st_ino", "st_mtime_ns", "st_mode"]:
            phase = {"constructed": False, "source_fd": None}
            def opening(backend, path, **kwargs):
                fd = original_open(backend, path, **kwargs)
                if path == self.source: phase["source_fd"] = fd
                return fd
            def constructing(catalog, *args, **kwargs):
                original_init(catalog, *args, **kwargs); phase["constructed"] = True
            def changed(backend, fd, **kwargs):
                info = original_info(backend, fd, **kwargs)
                if fd == phase["source_fd"] and phase["constructed"]:
                    values = {key: getattr(info, key) for key in ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode"]}
                    values[field] += 1
                    return types.SimpleNamespace(**values)
                return info
            with self.subTest(field=field), mock.patch.object(cases.FccReportCaseCatalog, "__init__", new=constructing), \
                    mock.patch.object(native._WindowsIO, "open_read", new=opening), mock.patch.object(native._WindowsIO, "info", new=changed):
                self.error("fcc_case_host_input_changed")

    def test_total_pdf_declared64mib_limit_fails_before_any_original_read(self):
        row = self.config["pdf_sources"][0]
        self.config["pdf_sources"] = [{**row, "sha256": format(index, "064x"), "bytes": 16 * 1024 * 1024} for index in range(5)]
        self.save_config(); original = native._WindowsIO.open_read
        def no_original(backend, path, **kwargs):
            self.assertNotEqual(path, self.source)
            return original(backend, path, **kwargs)
        with mock.patch.object(native._WindowsIO, "open_read", new=no_original):
            self.error("fcc_case_limit_exceeded", dependency=True)

    def test_pinned_input_write_is_denied_while_constructor_runs(self):
        original = cases.FccReportCaseCatalog.__init__; denied = []
        def construct(catalog, *args, **kwargs):
            for path in [self.config_file, self.packet_file, self.source]:
                try:
                    with path.open("ab"): pass
                except OSError: denied.append(path)
                else: self.fail("037 did not pin against concurrent write")
            return original(catalog, *args, **kwargs)
        with mock.patch.object(cases.FccReportCaseCatalog, "__init__", new=construct): self.call()
        self.assertEqual(len(denied), 3)

    def test_held_parent_cannot_be_replaced_before_original_open(self):
        original = native._WindowsIO.open_read; attempts = []
        parked = self.base / "parked"
        self.assertTrue(self.inputs.resolve().is_relative_to(self.base.resolve()))
        self.assertTrue(parked.parent.resolve().is_relative_to(self.base.resolve()))
        def opening(backend, path, **kwargs):
            if path == self.source and not attempts:
                attempts.append(True)
                with self.assertRaises(OSError): os.rename(self.inputs, parked)
            return original(backend, path, **kwargs)
        with mock.patch.object(native._WindowsIO, "open_read", new=opening): self.call()
        self.assertTrue(attempts); self.assertFalse(parked.exists())

    def test_failure_closes_every_owned_handle_and_close_failure_is_never_success(self):
        original = native._WindowsIO.close; closed = []
        def close(backend):
            closed.append(list(backend.held)); original(backend); raise OSError("PRIVATE cleanup")
        with mock.patch.object(native._WindowsIO, "close", new=close): self.error("fcc_case_host_unavailable")
        self.assertTrue(closed)
        for fd in closed[0]:
            with self.assertRaises(OSError): os.fstat(fd)
        with mock.patch.object(native._WindowsIO, "close", new=close):
            self.error("fcc_case_host_pin_mismatch", expected_config_sha256="0" * 64)

    def test_initial_parent_junction_and_inplace_reparse_cannot_read_outside(self):
        from tests.test_control_packet_prepare import ControlPacketPrepareTests
        outside = self.base / "outside"; outside.mkdir(); (outside / "config.json").write_bytes(self.config_file.read_bytes())
        outside_pdf = outside / "synthetic.pdf"; outside_pdf.write_bytes(self.source.read_bytes())
        outside_identity = (outside_pdf.stat().st_dev, outside_pdf.stat().st_ino); outside_reads = []
        link = self.base / "linked"
        result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        result.check_returncode()
        try: self.error("fcc_case_host_path_invalid", config_path=link / "config.json")
        finally: os.rmdir(link)
        empty = self.base / "empty"; empty.mkdir(); restore = None; attempted = []
        self.config["pdf_sources"][0]["path"] = str(empty / "synthetic.pdf"); self.save_config()
        init, original_read = native._WindowsIO.__init__, os.read
        def reading(fd, size):
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) == outside_identity: outside_reads.append(True)
            return original_read(fd, size)
        def initialize(backend):
            init(backend); original = backend.native.NtCreateFile
            def opening(*args):
                nonlocal restore
                attrs = backend.ctypes.cast(args[2], backend.ctypes.POINTER(backend.ObjectAttributes)).contents
                if attrs.ObjectName.contents.Buffer == "synthetic.pdf" and not attempted:
                    attempted.append(True); restore = ControlPacketPrepareTests.set_private_mountpoint(self, empty, outside)
                return original(*args)
            backend.native.NtCreateFile = opening
        try:
            with mock.patch.object(native._WindowsIO, "__init__", new=initialize), mock.patch("os.read", new=reading):
                with self.assertRaises(host.FccCaseCatalogHostError) as caught: self.call()
                self.assertIn(caught.exception.code, {"fcc_case_host_unavailable", "fcc_case_host_path_invalid", "fcc_case_host_input_changed"})
            self.assertTrue(attempted)
            self.assertEqual(outside_reads, [])
        finally:
            if restore: restore()

    def test_empty_catalog_and_unconfigured_027_remain_distinct_after_handles_close(self):
        self.packet.update(documents=[], cases=[]); self.policy["sources"].clear(); self.save_metadata()
        catalog, receipt = self.call()
        self.assertEqual(receipt["construction"]["case_count"], 0); self.assertEqual(receipt["construction"]["verified_evidence_literal_count"], 0)
        self.assertEqual(receipt["page_scopes"], [])
        self.assertIsNone(catalog.summary()["counts"]["candidate_count"])

    def test_config_exact64k_and_source16_normal_boundaries_then_receipt_budget_failure(self):
        rows = self.config["pdf_sources"][:]
        template = deepcopy(self.packet["documents"][0])
        for index in range(1, 16):
            raw = synthetic_pdf(["SYNTHETIC HOST SOURCE " + str(index)]); sha = digest(raw)
            path = self.inputs / ("source-" + str(index) + ".pdf"); path.write_bytes(raw)
            document = deepcopy(template); document.update(document_id="DOC-" + str(index), sha256=sha, size_bytes=len(raw), physical_pages=1)
            self.packet["documents"].append(document)
            self.policy["sources"][sha] = {**deepcopy(next(iter(self.policy["sources"].values()))), "pages": [1]}
            rows.append(self.descriptor(path))
        self.save_metadata(); self.config["pdf_sources"] = rows; self.save_config()
        raw = self.config_file.read_bytes(); self.config_file.write_bytes(raw + b" " * (65536 - len(raw))); self.config_sha = digest(self.config_file.read_bytes())
        self.assertEqual(self.call()[1]["construction"]["document_count"], 16)
        with mock.patch.object(host, "_RECEIPT_BYTES", 1): self.error("fcc_case_limit_exceeded", dependency=True)

    def test_loaded_catalog_memory_and_existing027_http_never_reopen_inputs(self):
        from labflow import ui_server
        catalog, receipt = self.call(); expected = catalog.case("CASE-A")
        server = ui_server.create_server(self.base / "workspace", port=0, fcc_case_catalog=catalog)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with mock.patch.object(native._WindowsIO, "open_read", side_effect=AssertionError("input reopen")), \
                    mock.patch("builtins.open", side_effect=AssertionError("file")), \
                    mock.patch("pathlib.Path.open", side_effect=AssertionError("path")), \
                    mock.patch("pypdf.PdfReader", side_effect=AssertionError("parser")), \
                    mock.patch("sqlite3.connect", side_effect=AssertionError("database")):
                self.assertEqual(catalog.case("CASE-A"), expected)
                for target in ["/api/fcc-cases/summary", "/api/fcc-cases/cases/CASE-A"]:
                    connection = http.client.HTTPConnection(*server.server_address, timeout=5)
                    try:
                        connection.request("GET", target); response = connection.getresponse(); value = json.loads(response.read())
                        self.assertEqual(response.status, 200)
                        if target.endswith("CASE-A"): self.assertEqual(value, expected)
                    finally: connection.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5); self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
