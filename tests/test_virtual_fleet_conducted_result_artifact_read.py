"""One genuine synthetic writer fixture; readonly fixed-three reader boundaries."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow import control_packet_prepare as native
from labflow.virtual_fleet import conducted_result_artifact as writer
from labflow.virtual_fleet import conducted_twin_result as result_api
from labflow.virtual_fleet import rf_signal_waveform_observation_read as known_close

MODULE = "labflow.virtual_fleet.conducted_result_artifact_read"
NAMES = ("manifest.json", "result.json", "draft.md")
PREFIX = "conducted_result_artifact_read_"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ArtifactReadSmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), "artifact reader is absent")


class ConductedArtifactReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = importlib.import_module(MODULE)
        spec = importlib.util.spec_from_file_location(
            "read_result_fixture", Path(__file__).with_name("test_virtual_fleet_conducted_twin_result.py"))
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        case = fixture.ConductedTwinResultTests()
        cls.addClassCleanup(case.doCleanups)
        args, ref = case.genuine()
        cls.original_result = result_api.build_conducted_twin_result(*args, measurement_ref=ref)
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        root = Path(directory.name)
        binding = cls.original_result["binding"]
        cls.pins = dict(artifact_name="read-one", expected_result_sha256=sha(canonical(cls.original_result)),
                        run_id=binding["run_id"], runtime_instance_id=binding["runtime_instance_id"])
        cls.writer_summary = writer.write_conducted_result_artifact(cls.original_result, workspace_root=root, **cls.pins)
        leaf = root / ".local/conducted-result-artifacts/read-one"
        cls.raw = {name: (leaf / name).read_bytes() for name in NAMES}
        cls.pins["expected_manifest_sha256"] = sha(cls.raw["manifest.json"])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.leaf = self.root / ".local/conducted-result-artifacts/read-one"
        self.leaf.mkdir(parents=True)
        for name, raw in self.raw.items():
            (self.leaf / name).write_bytes(raw)
        self.options = dict(self.pins, workspace_root=self.root)

    def call(self, **changes):
        return self.api.read_conducted_result_artifact(**{**self.options, **changes})

    def reject(self, code, **changes):
        with self.assertRaises(self.api.ConductedResultArtifactReadError) as caught:
            self.call(**changes)
        self.assertEqual((caught.exception.code, str(caught.exception)), (PREFIX + code, PREFIX + code))

    def manifest(self, change=None):
        value = json.loads((self.leaf / "manifest.json").read_bytes())
        if change is not None:
            change(value)
        raw = canonical(value) + b"\n"
        (self.leaf / "manifest.json").write_bytes(raw)
        self.options["expected_manifest_sha256"] = sha(raw)
        return value

    def result(self, change):
        value = json.loads((self.leaf / "result.json").read_bytes())
        change(value)
        raw = canonical(value) + b"\n"
        (self.leaf / "result.json").write_bytes(raw)
        self.options["expected_result_sha256"] = sha(raw[:-1])
        def update(manifest):
            manifest["result_sha256"] = self.options["expected_result_sha256"]
            manifest["result_status"] = value["status"]
            manifest["files"][0].update(bytes=len(raw), sha256=sha(raw))
        self.manifest(update)
        return value

    def test_genuine_result_manifest_draft_and_storage_scopes_unchanged(self):
        value = self.call()
        self.assertEqual(set(value), set("schema_version kind selection storage result manifest draft verification".split()))
        self.assertEqual(value["kind"], "conducted_result_artifact_read")
        self.assertEqual(value["result"], self.original_result)
        self.assertEqual(value["manifest"], json.loads(self.raw["manifest.json"]))
        self.assertEqual(value["draft"].encode("utf-8"), self.raw["draft.md"])
        self.assertEqual(value["storage"]["status"], "manifest_payloads_verified")
        self.assertEqual(value["storage"]["verified_file_count"], 3)
        self.assertEqual(value["storage"]["result_sha256"], self.pins["expected_result_sha256"])
        flags = value["verification"]
        self.assertEqual((flags["current_binding"], flags["source_references"]), ("caller_provided_hashes_and_ids_only", "not_opened"))
        self.assertEqual((flags["historical_publication_order"], flags["writer_outcome"]), ("not_verified", "not_verified"))
        self.assertIs(flags["physical_verified"], False)
        self.assertIs(flags["execution_authority"], False)
        value["result"]["status"] = "changed caller DTO"
        self.assertEqual((self.leaf / "result.json").read_bytes(), self.raw["result.json"])

    def test_only_fixed_three_native_reads_no_write_search_ref_or_reexecution(self):
        before = {name: ((self.leaf / name).read_bytes(), (self.leaf / name).stat().st_mtime_ns) for name in NAMES}
        original, opened = native._WindowsIO.open_read, []
        def open_read(backend, path, **kwargs):
            opened.append((path.name, kwargs))
            return original(backend, path, **kwargs)
        with patch.object(native._WindowsIO, "open_read", new=open_read), patch.object(
                native, "_write_bytes", side_effect=AssertionError("readonly")), patch.object(
                writer, "write_conducted_result_artifact", side_effect=AssertionError("no writer")), patch.object(
                result_api, "build_conducted_twin_result", side_effect=AssertionError("no rebuild")), patch.object(
                result_api, "calculate", side_effect=AssertionError("no calculation")), patch.object(
                Path, "read_bytes", side_effect=AssertionError("native only")), patch.object(
                Path, "rglob", side_effect=AssertionError("no search")), patch.object(Path, "iterdir", side_effect=AssertionError("no search")):
            self.call()
        self.assertEqual({name for name, kwargs in opened}, set(NAMES))
        self.assertTrue(all(kwargs == {"pin": True} for name, kwargs in opened))
        self.assertEqual({name: ((self.leaf / name).read_bytes(), (self.leaf / name).stat().st_mtime_ns) for name in NAMES}, before)

    def test_missing_marker_payload_and_artifact_never_return_partial_success(self):
        (self.leaf / "manifest.json").unlink()
        self.reject("not_found")
        (self.leaf / "manifest.json").write_bytes(self.raw["manifest.json"])
        (self.leaf / "draft.md").unlink()
        self.reject("incomplete")
        self.reject("not_found", artifact_name="missing-artifact")

    def test_hashes_and_other_run_bindings_close_without_mutation(self):
        self.reject("evidence_invalid", expected_manifest_sha256="0" * 64)
        self.reject("binding_invalid", expected_result_sha256="0" * 64)
        self.reject("binding_invalid", run_id="other-run")
        self.reject("binding_invalid", runtime_instance_id="other-runtime")
        (self.leaf / "draft.md").write_bytes(b"damaged")
        self.reject("evidence_invalid")

    def test_manifest_schema_fixed_paths_media_sizes_and_authority(self):
        mutations = (lambda m: m.update(extra=1), lambda m: m.update(schema_version=True),
            lambda m: m["files"][0].update(path="../other.json"), lambda m: m["files"][1].update(media_type="text/plain"),
            lambda m: m["files"][1].update(bytes=True), lambda m: m["files"].reverse(),
            lambda m: m["verification"].update(physical_verified=0), lambda m: m.update(execution_authority=0))
        for change in mutations:
            with self.subTest(change=repr(change)):
                (self.leaf / "manifest.json").write_bytes(self.raw["manifest.json"])
                self.manifest(change)
                self.reject("evidence_invalid")

    def test_canonical_json_bom_duplicates_nonfinite_and_single_lf(self):
        base = self.raw["manifest.json"]
        variants = (b"\xef\xbb\xbf" + base, base + b"\n", base[:-1], b" " + base,
                    base.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'), b"NaN\n", b"\xff\n")
        for raw in variants:
            with self.subTest(raw=raw[:50]):
                (self.leaf / "manifest.json").write_bytes(raw)
                self.options["expected_manifest_sha256"] = sha(raw)
                self.reject("evidence_invalid")

    def test_caps_and_unrecognized_payload_cannot_succeed(self):
        raw = b"x" * 8193
        (self.leaf / "manifest.json").write_bytes(raw)
        self.options["expected_manifest_sha256"] = sha(raw)
        self.reject("evidence_invalid")
        (self.leaf / "manifest.json").write_bytes(self.raw["manifest.json"])
        self.manifest(lambda m: m["files"][0].update(bytes=1048578))
        self.reject("evidence_invalid")

    def test_current_full_binding_rejects_report_only_and_internal_mixed_hash(self):
        self.result(lambda r: r["binding"].update(report_sha256="0" * 64))
        self.reject("binding_invalid")
        (self.leaf / "result.json").write_bytes(self.raw["result.json"])
        (self.leaf / "manifest.json").write_bytes(self.raw["manifest.json"])
        def early(r):
            r["binding"] = {key: r["binding"][key] for key in ("plan_input", "run_report")}
            r.update(status="incomplete", failure=dict(code="plan_blocked", field="plan_input"))
            r["calculation"].update(corrected=None, correction_ledger=[])
        self.result(early)
        self.reject("binding_invalid")

    def test_full_bound_invalid_result_is_preserved_and_never_promoted(self):
        def invalidate(r):
            r.update(status="invalid", failure=dict(code="invalid_data", field="raw_measurement"))
            r["calculation"]["corrected"] = None
        expected = self.result(invalidate)
        value = self.call()
        self.assertEqual(value["result"], expected)
        self.assertEqual(value["result"]["status"], "invalid")
        self.assertIsNone(value["result"]["calculation"]["conformity"]["verdict"])

    def test_genuine_writer_report_only_manifest_is_binding_insufficient(self):
        self.manifest(lambda m: m.update(verification=writer._verification("report_ids_only")))
        self.reject("binding_invalid")

    def test_draft_header_only_no_authority_or_numeric_interpretation(self):
        original = self.raw["draft.md"]
        for raw, good in ((b"# Other\n", False), (original + b'\n{"uncertainty_db":17,"verdict":"PASS"}\n', True), (b"\xff", False)):
            with self.subTest(good=good):
                (self.leaf / "draft.md").write_bytes(raw)
                self.manifest(lambda m: m["files"][1].update(bytes=len(raw), sha256=sha(raw)))
                if good:
                    value = self.call()
                    self.assertEqual(value["draft"].encode("utf-8"), raw)
                    self.assertEqual(value["verification"]["draft_content"], "not_interpreted")
                    self.assertIsNone(value["result"]["calculation"]["conformity"]["uncertainty_db"])
                else:
                    self.reject("evidence_invalid")

    def test_arguments_and_lexical_path_fail_before_native_backend(self):
        with patch.object(native, "_WindowsIO", side_effect=AssertionError("before IO")):
            for changes in (dict(artifact_name="../other"), dict(artifact_name="CON"), dict(expected_manifest_sha256="A" * 64), dict(run_id=None)):
                with self.subTest(changes=changes):
                    self.reject("invalid_argument", **changes)
            for value in ("\\\\server\\share", "C:relative", str(self.root) + ".", "..\\elsewhere"):
                with self.subTest(root=value):
                    self.reject("path_invalid", workspace_root=value)

    def test_native_platform_unavailable_has_no_fallback(self):
        with patch.object(native, "_WINDOWS_BACKEND_AVAILABLE", False):
            self.reject("unsupported_platform")

    def test_native_reparse_attribute_signal_is_rejected(self):
        original = native._not_reparse
        size = len(self.raw["result.json"])
        def reparse(info):
            if info.st_size == size:
                from types import SimpleNamespace
                info = SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return original(info)
        with patch.object(native, "_not_reparse", side_effect=reparse):
            self.reject("path_invalid")

    def test_actual_pins_block_write_and_rename_through_current_binding_check(self):
        original = result_api._plan
        def checking(value):
            for name in NAMES:
                path = self.leaf / name
                with self.assertRaises(PermissionError):
                    path.write_bytes(b"changed")
                with self.assertRaises(PermissionError):
                    path.rename(path.with_suffix(".moved"))
            return original(value)
        with patch.object(result_api, "_plan", side_effect=checking):
            self.call()

    def test_same_stamp_late_raw_change_withholds_dto(self):
        original, seen = native._read_descriptor, set()
        def drift(fd, limit, code):
            raw = original(fd, limit, code)
            if fd in seen:
                return b" " + raw[1:]
            seen.add(fd)
            return raw
        with patch.object(native, "_read_descriptor", side_effect=drift):
            self.reject("input_changed")

    def test_post_binding_native_stamp_change_withholds_dto(self):
        original, post = native._stamp, []
        plan = result_api._plan
        def checking(value):
            result = plan(value)
            post.append(True)
            return result
        def drift(info):
            stamp = original(info)
            return stamp[:3] + (stamp[3] + 1,) + stamp[4:] if post else stamp
        with patch.object(result_api, "_plan", side_effect=checking), patch.object(native, "_stamp", side_effect=drift):
            self.reject("input_changed")

    def test_control_identity_and_sanitized_unexpected_failure(self):
        for error in (KeyboardInterrupt(), MemoryError(), SystemExit(0), GeneratorExit(), RuntimeError("sensitive path")):
            with self.subTest(error=type(error).__name__), patch.object(writer, "_input", side_effect=error):
                if type(error) is RuntimeError:
                    self.reject("unavailable")
                else:
                    with self.assertRaises(type(error)) as caught:
                        self.call()
                    self.assertIs(caught.exception, error)

    def test_known_cleanup_no_open_descriptors_and_first_error_priority(self):
        original, held = known_close._close, []
        def close(backend):
            held.extend(backend.held)
            return original(backend)
        with patch.object(known_close, "_close", side_effect=close):
            self.call()
        for fd in held:
            with self.assertRaises(OSError):
                os.fstat(fd)
        for prior, error in ((False, KeyboardInterrupt()), (False, OSError()), (True, KeyboardInterrupt())):
            with self.subTest(prior=prior, error=type(error).__name__):
                def fail(backend):
                    original(backend)
                    raise error
                with patch.object(known_close, "_close", side_effect=fail):
                    if prior:
                        self.reject("evidence_invalid", expected_manifest_sha256="0" * 64)
                    elif type(error) is KeyboardInterrupt:
                        with self.assertRaises(KeyboardInterrupt) as caught:
                            self.call()
                        self.assertIs(caught.exception, error)
                    else:
                        self.reject("unavailable")
