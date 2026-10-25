"""Private artifact publication: genuine synthetic input, real native FS and named faults."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from labflow import control_packet_prepare as native
from labflow.virtual_fleet import conducted_twin_result as result_api

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifact_result_fixture", Path(__file__).with_name("test_virtual_fleet_conducted_twin_result.py"))
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
_UNSET = object()
PREFIX = "conducted_result_artifact_"


def sha(value):
    return hashlib.sha256(result_api._canonical(value)).hexdigest()


class ConductedResultArtifactTests(unittest.TestCase):
    def setUp(self):
        case = FIXTURE.ConductedTwinResultTests()
        self.addCleanup(case.doCleanups)
        self.args, self.ref = case.genuine()
        self.result = result_api.build_conducted_twin_result(*self.args, measurement_ref=self.ref)
        self.assertEqual(self.result["status"], "recorded")
        self.fixture = case
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.name = "artifact-one"
        self.leaf = self.root / ".local/conducted-result-artifacts" / self.name
        self.options = dict(workspace_root=self.root, artifact_name=self.name,
                            expected_result_sha256=sha(self.result),
                            run_id=self.result["binding"]["run_id"],
                            runtime_instance_id=self.result["binding"]["runtime_instance_id"])

    def module(self):
        name = "labflow.virtual_fleet.conducted_result_artifact"
        self.assertIsNotNone(importlib.util.find_spec(name), "thin artifact writer is absent")
        return importlib.import_module(name)

    def call(self, value=_UNSET, **overrides):
        return self.module().write_conducted_result_artifact(
            self.result if value is _UNSET else value, **{**self.options, **overrides})

    def reject(self, suffix, value=_UNSET, **overrides):
        module = self.module()
        with self.assertRaises(module.ConductedResultArtifactError) as raised:
            self.call(value, **overrides)
        self.assertEqual((raised.exception.code, str(raised.exception)), (PREFIX + suffix, PREFIX + suffix))
        return raised.exception

    def original_bytes(self):
        return result_api._canonical(self.result) + b"\n"

    def test_real_native_publish_binds_payloads_marker_DRAFT_and_not_conformity(self):
        original = deepcopy(self.result)
        summary = self.call()
        self.assertEqual(set(summary), {"schema_version", "kind", "artifact_name", "run_id", "runtime_instance_id",
                         "result_status", "storage", "files", "verification", "execution_authority"})
        self.assertEqual(summary["storage"]["status"], "complete")
        self.assertEqual(summary["result_status"], "recorded")
        self.assertEqual(summary["verification"]["report_status"], "DRAFT")
        self.assertEqual(summary["verification"]["binding_scope"], "full_bound")
        self.assertIs(summary["execution_authority"], False)
        self.assertEqual((self.leaf / "result.json").read_bytes(), self.original_bytes())
        manifest_raw = (self.leaf / "manifest.json").read_bytes()
        manifest = json.loads(manifest_raw)
        self.assertEqual(manifest["result_sha256"], self.options["expected_result_sha256"])
        self.assertEqual((manifest["run_id"], manifest["runtime_instance_id"]),
                         (self.options["run_id"], self.options["runtime_instance_id"]))
        self.assertEqual(len(manifest["files"]), 2)
        for row in manifest["files"]:
            raw = (self.leaf / row["path"]).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (row["bytes"], row["sha256"]))
        self.assertEqual(summary["storage"]["sha256"], hashlib.sha256(manifest_raw).hexdigest())
        draft = (self.leaf / "draft.md").read_text("utf-8")
        self.assertIn("DRAFT", draft)
        self.assertIn('"status": "not_assessed"', draft)
        self.assertIn('"verdict": null', draft)
        self.assertIn('"raw_measurement"', draft)
        self.assertIn('"correction_ledger"', draft)
        self.assertEqual(self.result, original)

    def test_input_snapshot_detaches_and_builder_or_calculator_are_not_reexecuted(self):
        module = self.module()
        original = deepcopy(self.result)
        write = native._write_bytes
        def mutate(tree, path, raw, code, **kwargs):
            self.result["raw_measurement"]["packet"]["value"] = 900
            return write(tree, path, raw, code, **kwargs)
        with patch.object(native, "_write_bytes", mutate), patch.object(
                result_api, "build_conducted_twin_result", side_effect=AssertionError("no rebuild")), patch.object(
                result_api, "calculate", side_effect=AssertionError("no calculation")):
            self.call()
        self.assertEqual(json.loads((self.leaf / "result.json").read_text("utf-8")), original)

    def test_invalid_raw_null_and_failure_are_preserved_with_complete_storage(self):
        args = deepcopy(self.args)
        def change(stored):
            event = next(e for e in stored["events"] if e["event_id"] == self.ref)
            event["payload"]["observation"]["devices"]["sensor"]["values"]["outputs"]["measurement"]["valid"] = False
        args[2] = self.fixture.repack(args[2], change)
        result = result_api.build_conducted_twin_result(*args, measurement_ref=self.ref)
        self.assertEqual(result["status"], "invalid")
        summary = self.call(result, expected_result_sha256=sha(result))
        stored = json.loads((self.leaf / "result.json").read_text("utf-8"))
        self.assertEqual(stored, result)
        self.assertIsNone(stored["calculation"]["corrected"])
        self.assertEqual(summary["result_status"], "invalid")
        self.assertEqual(summary["storage"]["status"], "complete")
        self.assertEqual(stored["calculation"]["conformity"]["status"], "not_assessed")

    def early_result(self):
        result = deepcopy(self.result)
        result["binding"] = {key: result["binding"][key] for key in ("plan_input", "run_report")}
        result["status"] = "incomplete"
        result["failure"] = dict(code="plan_blocked", field="plan_input")
        result["calculation"].update(corrected=None, correction_ledger=[])
        return result

    def test_report_ids_only_uses_both_original_IDs_without_inventing_D1_run_fields(self):
        result = self.early_result()
        before = deepcopy(result)
        summary = self.call(result, expected_result_sha256=sha(result))
        self.assertEqual(summary["verification"]["binding_scope"], "report_ids_only")
        stored = json.loads((self.leaf / "result.json").read_text("utf-8"))
        self.assertEqual(stored, before)
        self.assertNotIn("run_id", stored["binding"]["plan_input"]["binding"])
        self.assertNotIn("runtime_instance_id", stored["binding"]["plan_input"]["binding"])

    def test_unbound_or_missing_report_IDs_reject_before_native_storage(self):
        module = self.module()
        for field in ("binding", "run_id", "runtime_instance_id", "plan_input"):
            result = self.early_result()
            if field == "binding":
                result["binding"] = {}
            elif field == "plan_input":
                result["binding"]["plan_input"] = None
            else:
                del result["binding"]["run_report"][field]
            with self.subTest(field=field), patch.object(native, "_WindowsIO", side_effect=AssertionError("validate before IO")):
                self.reject("unbound_result", result, expected_result_sha256=sha(result))
        self.assertFalse(self.leaf.exists())

    def test_different_run_or_runtime_and_result_hash_reject_before_claim(self):
        for field in ("run_id", "runtime_instance_id"):
            with self.subTest(field=field), patch.object(native, "_WindowsIO", side_effect=AssertionError("validate before IO")):
                self.reject("run_binding_mismatch", **{field: "different-run"})
        with patch.object(native, "_WindowsIO", side_effect=AssertionError("validate before IO")):
            self.reject("result_hash_mismatch", expected_result_sha256="0" * 64)
        self.assertFalse(self.leaf.exists())

    def test_native_input_schema_authority_and_filename_bounds_are_preflight(self):
        class Result(dict):
            pass
        invalid = [None, True, Result(self.result), float("nan")]
        cycle = {}
        cycle["cycle"] = cycle
        invalid.append(cycle)
        for value in invalid:
            with self.subTest(kind=type(value).__name__), patch.object(native, "_WindowsIO", side_effect=AssertionError("no IO")):
                self.reject("result_input_invalid", value)
        for name in ("../escape", "a/b", "a\\b", "CON", ".", "a" * 65, " a", "a:other"):
            with self.subTest(name=name), patch.object(native, "_WindowsIO", side_effect=AssertionError("no IO")):
                self.reject("invalid_argument", artifact_name=name)
        forged = deepcopy(self.result)
        forged["calculation"]["conformity"]["verdict"] = "PASS"
        with patch.object(native, "_WindowsIO", side_effect=AssertionError("no IO")):
            self.reject("result_input_invalid", forged, expected_result_sha256=sha(forged))
        self.assertFalse(self.leaf.exists())

    def test_result_and_draft_caps_reject_without_silent_truncation_or_claim(self):
        for amount, code in ((1024 * 1024, "result_too_large"), (300000, "draft_too_large")):
            value = deepcopy(self.result)
            value["gaps"].append(dict(code="authored", field="input", provided="A" * amount, blocking=True))
            with self.subTest(amount=amount), patch.object(native, "_WindowsIO", side_effect=AssertionError("cap before IO")):
                self.reject(code, value, expected_result_sha256=sha(value))
        self.assertFalse(self.leaf.exists())

    def test_existing_partial_or_complete_artifact_is_never_reused(self):
        self.leaf.mkdir(parents=True)
        canary = self.leaf / "older.bin"
        canary.write_bytes(b"preserve prior partial bytes")
        before = canary.stat()
        self.reject("destination_exists")
        self.assertEqual(canary.read_bytes(), b"preserve prior partial bytes")
        self.assertEqual(canary.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(sorted(p.name for p in self.leaf.iterdir()), ["older.bin"])

    def test_second_run_cannot_overwrite_completed_artifact(self):
        self.call()
        before = {p.name: p.read_bytes() for p in self.leaf.iterdir()}
        other, ref = self.fixture.genuine()
        value = result_api.build_conducted_twin_result(*other, measurement_ref=ref)
        self.reject("destination_exists", value, expected_result_sha256=sha(value),
                    run_id=value["binding"]["run_id"], runtime_instance_id=value["binding"]["runtime_instance_id"])
        self.assertEqual({p.name: p.read_bytes() for p in self.leaf.iterdir()}, before)

    def test_actual_native_concurrent_claim_has_exactly_one_complete_winner(self):
        module = self.module()
        outcomes = []
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            try:
                outcomes.append(("ok", self.call()))
            except module.ConductedResultArtifactError as error:
                outcomes.append(("error", error.code))
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(kind for kind, value in outcomes), ["error", "ok"])
        self.assertEqual(next(value for kind, value in outcomes if kind == "error"), PREFIX + "destination_exists")
        self.assertTrue((self.leaf / "manifest.json").is_file())

    def test_native_reparse_attribute_signal_rejects_before_leaf_claim(self):
        info = native._WindowsIO.info
        def changed(backend, descriptor, **kwargs):
            actual = info(backend, descriptor, **kwargs)
            if kwargs.get("directory") and backend.directories.get(self.root) == descriptor:
                return SimpleNamespace(st_dev=actual.st_dev, st_ino=actual.st_ino, st_mode=actual.st_mode,
                    st_size=actual.st_size, st_mtime_ns=actual.st_mtime_ns,
                    st_file_attributes=actual.st_file_attributes | 0x400)
            return actual
        with patch.object(native._WindowsIO, "info", changed):
            self.reject("path_invalid")
        self.assertFalse(self.leaf.exists())

    def test_partial_native_write_retains_prefix_without_completion_marker(self):
        write = native._write_all
        first = True
        def broken(descriptor, data, code):
            nonlocal first
            if first:
                first = False
                os.write(descriptor, data[:17])
                raise OSError("injected first write detail")
            return write(descriptor, data, code)
        with patch.object(native, "_write_all", broken):
            error = self.reject("write_failed")
        self.assertEqual(error.phase, "write_result")
        self.assertEqual((self.leaf / "result.pending.json").read_bytes(), self.original_bytes()[:17])
        self.assertFalse((self.leaf / "manifest.json").exists())
        marker = json.loads((self.leaf / "failure.json").read_text("utf-8"))
        self.assertNotIn("injected first write detail", json.dumps(marker))
        self.assertEqual(marker["error_code"], PREFIX + "write_failed")

    def test_native_fsync_failure_keeps_written_prefix_and_no_success(self):
        fsync = native.os.fsync
        first = True
        def broken(descriptor):
            nonlocal first
            if first:
                first = False
                raise OSError("first fsync detail")
            return fsync(descriptor)
        with patch.object(native.os, "fsync", broken):
            self.reject("write_failed")
        self.assertEqual((self.leaf / "result.pending.json").read_bytes(), self.original_bytes())
        self.assertFalse((self.leaf / "manifest.json").exists())

    def test_marker_lost_ack_keeps_actual_marker_and_is_publication_uncertain(self):
        link = native._WindowsIO.link_receipt
        def lost(backend, descriptor, path):
            result = link(backend, descriptor, path)
            if path.name == "manifest.json":
                raise OSError("injected lost marker ack")
            return result
        with patch.object(native._WindowsIO, "link_receipt", lost):
            error = self.reject("publication_uncertain")
        self.assertTrue(error.publication_attempted)
        manifest = json.loads((self.leaf / "manifest.json").read_text("utf-8"))
        self.assertEqual(manifest["result_sha256"], self.options["expected_result_sha256"])
        self.assertEqual((self.leaf / "result.json").read_bytes(), self.original_bytes())

    def test_post_marker_verify_failure_preserves_marker_and_never_returns_success(self):
        module = self.module()
        verify = module._verify_file
        def broken(tree, path, descriptor, stamp, raw):
            verify(tree, path, descriptor, stamp, raw)
            if path.name == "manifest.json":
                raise OSError("injected published verify detail")
        with patch.object(module, "_verify_file", broken):
            self.reject("publication_uncertain")
        self.assertTrue((self.leaf / "manifest.json").is_file())
        self.assertTrue((self.leaf / "draft.md").is_file())

    def test_cleanup_after_marker_does_not_hide_failure_or_remove_completed_prefix(self):
        module = self.module()
        close = module._close_owned
        def broken(backend):
            close(backend)
            return OSError("injected cleanup detail")
        with patch.object(module, "_close_owned", broken):
            error = self.reject("publication_uncertain")
        self.assertEqual(error.phase, "cleanup")
        self.assertTrue((self.leaf / "manifest.json").is_file())
        self.assertEqual((self.leaf / "result.json").read_bytes(), self.original_bytes())

    def test_first_write_failure_is_not_replaced_by_secondary_marker_or_cleanup_failure(self):
        module = self.module()
        write = native._write_all
        close = module._close_owned
        first = True
        def broken_write(descriptor, data, code):
            nonlocal first
            if first:
                first = False
                os.write(descriptor, data[:11])
            raise OSError("write primary or marker secondary")
        def broken_close(backend):
            close(backend)
            return OSError("cleanup secondary")
        with patch.object(native, "_write_all", broken_write), patch.object(module, "_close_owned", broken_close):
            error = self.reject("write_failed")
        self.assertEqual(error.phase, "write_result")
        self.assertEqual((self.leaf / "result.pending.json").read_bytes(), self.original_bytes()[:11])
        self.assertFalse((self.leaf / "manifest.json").exists())

    def test_control_exception_identity_and_partial_prefix_survive_cleanup(self):
        module = self.module()
        for index, control in enumerate((KeyboardInterrupt("authored KI"), MemoryError("authored memory"))):
            leaf = self.root / ".local/conducted-result-artifacts" / ("control-" + str(index))
            write = native._write_all
            first = True
            def broken(descriptor, data, code):
                nonlocal first
                if first:
                    first = False
                    os.write(descriptor, data[:13])
                    raise control
                return write(descriptor, data, code)
            with self.subTest(control=type(control).__name__), patch.object(native, "_write_all", broken):
                with self.assertRaises(type(control)) as raised:
                    self.call(artifact_name=leaf.name)
                self.assertIs(raised.exception, control)
                self.assertEqual((leaf / "result.pending.json").read_bytes(), self.original_bytes()[:13])
                self.assertFalse((leaf / "manifest.json").exists())

    def test_pending_corruption_is_preserved_not_repaired_or_published(self):
        write = native._write_bytes
        first = True
        def corrupt(tree, path, raw, code, **kwargs):
            nonlocal first
            stamp = write(tree, path, raw, code, **kwargs)
            if first:
                first = False
                with path.open("r+b") as stream:
                    stream.write(b"[")
            return stamp
        with patch.object(native, "_write_bytes", corrupt):
            self.reject("write_failed")
        self.assertTrue((self.leaf / "result.pending.json").read_bytes().startswith(b"["))
        self.assertFalse((self.leaf / "manifest.json").exists())

    def test_raw_reference_paths_are_data_only_and_native_handles_close(self):
        module = self.module()
        result = deepcopy(self.result)
        private = self.root / "do-not-read.txt"
        private.write_bytes(b"authored private reference canary")
        result["gaps"].append(dict(code="source_gap", field="input", provided=str(private), blocking=True))
        before = private.stat()
        original = native._WindowsIO
        backends = []
        def create():
            backend = original()
            backends.append(backend)
            return backend
        path_open = Path.open
        def guarded_open(path, *args, **kwargs):
            if path == private:
                raise AssertionError("raw reference must not be opened")
            return path_open(path, *args, **kwargs)
        with patch.object(native, "_WindowsIO", side_effect=create), patch.object(Path, "open", guarded_open):
            self.call(result, expected_result_sha256=sha(result))
        self.assertEqual(private.read_bytes(), b"authored private reference canary")
        self.assertEqual(private.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(len(backends), 1)
        self.assertEqual((backends[0].held, backends[0].directories), ([], {}))
        self.assertEqual(json.loads((self.leaf / "result.json").read_text("utf-8")), result)


if __name__ == "__main__":
    unittest.main()
