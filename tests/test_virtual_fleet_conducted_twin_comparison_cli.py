"""Readonly CLI boundaries using disposable synthetic files and actual module children."""
from copy import deepcopy
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from labflow import control_packet_prepare as native
from labflow.virtual_fleet import conducted_twin_comparison as comparison
from labflow.virtual_fleet import rf_signal_waveform_observation_read as observation_read

MODULE = "labflow.virtual_fleet.conducted_twin_comparison_cli"
PREFIX = "conducted_twin_comparison_cli_"
ROOT = Path(__file__).resolve().parents[1]
FLAGS = ("--result-file", "--reference-file", "--policy-file", "--lineage-file")
KEYS = set("schema_version kind status bindings scope comparison independence reference reasons conformity verification".split())


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8") + b"\n"


class Stream(io.StringIO):
    def __init__(self, *, write_error=None, flush_error=None, short=False):
        super().__init__()
        self.writes = self.flushes = self.reconfigures = 0
        self.write_error, self.flush_error, self.short = write_error, flush_error, short

    def write(self, value):
        self.writes += 1
        if self.write_error is not None:
            raise self.write_error
        size = super().write(value)
        return size - 1 if self.short else size

    def flush(self):
        self.flushes += 1
        if self.flush_error is not None:
            raise self.flush_error

    def reconfigure(self, **kwargs):
        self.reconfigures += 1
        self.configuration = kwargs


class ComparisonCliSmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), "comparison CLI module is absent")


class ComparisonCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = importlib.import_module(MODULE)
        spec = importlib.util.spec_from_file_location(
            "cli_comparison_fixture", Path(__file__).with_name("test_virtual_fleet_conducted_twin_comparison.py"))
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        parent = fixture.ConductedTwinComparisonTests
        parent.setUpClass()
        cls.addClassCleanup(parent.doClassCleanups)
        case = parent()
        case.setUp()
        cls.inputs = (case.result, case.reference, case.policy, case.lineage)
        cls.expected = comparison.compare_conducted_twin_result(
            case.result, case.reference, comparator_policy=case.policy, lineage=case.lineage)
        if cls.expected["status"] != "compared":
            raise AssertionError("disposable genuine synthetic fixture did not compare")

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.values = list(deepcopy(self.inputs))
        self.paths = [self.folder / (name + ".json") for name in ("result", "reference", "policy", "lineage")]
        self.save()
        self.args = [value for flag, path in zip(FLAGS, self.paths) for value in (flag, str(path))]

    def save(self):
        for path, value in zip(self.paths, self.values):
            path.write_bytes(wire(value))

    def invoke(self, args=None, *, out=None, err=None, operation=None):
        out, err = (Stream() if out is None else out), (Stream() if err is None else err)
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err), patch.object(
                comparison, "compare_conducted_twin_result", wraps=operation or comparison.compare_conducted_twin_result) as api:
            status = self.cli.main(self.args if args is None else args)
        self.assertFalse(out.closed)
        self.assertFalse(err.closed)
        self.assertEqual((out.reconfigures, err.reconfigures), (0, 0))
        return status, out, err, api.call_count

    def error(self, result, status, suffix, calls):
        actual, out, err, count = result
        self.assertEqual((actual, count, out.getvalue(), out.writes), (status, calls, "", 0))
        self.assertEqual(json.loads(err.getvalue()), {"error": {"code": PREFIX + suffix}})
        self.assertEqual(err.writes, 1)

    def test_exact_parent_dto_once_and_inputs_native_unchanged(self):
        def stamp(path):
            s = path.stat()
            return path.read_bytes(), (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode, s.st_nlink)
        before = [stamp(path) for path in self.paths]
        status, out, err, count = self.invoke()
        self.assertEqual((status, count, out.writes, err.writes), (0, 1, 1, 0))
        self.assertEqual(out.getvalue().encode("utf-8"), wire(self.expected))
        self.assertEqual(set(json.loads(out.getvalue())), KEYS)
        self.assertEqual([stamp(path) for path in self.paths], before)

    def test_outside_tolerance_is_compared_exit_zero(self):
        self.values[1]["measurement"]["value"] = -8
        self.save()
        status, out, err, count = self.invoke()
        self.assertEqual((status, count, out.writes, err.writes), (0, 1, 1, 0))
        self.assertIs(json.loads(out.getvalue())["comparison"]["within_tolerance"], False)

    def test_semantic_absence_and_manifest_are_not_assessed_exit_three(self):
        for index, value in ((2, None), (2, {}), (0, {"kind": "conducted_result_artifact_manifest"}), (3, {})):
            with self.subTest(index=index, value=value):
                self.values = list(deepcopy(self.inputs))
                self.values[index] = value
                self.save()
                status, out, err, count = self.invoke()
                body = json.loads(out.getvalue())
                self.assertEqual((status, count, out.writes, err.writes, body["status"]), (3, 1, 1, 0, "not_assessed"))
                self.assertTrue(all(value is None for value in body["comparison"].values()))
                self.assertTrue(body["reasons"])

    def test_argument_errors_before_native_or_parent(self):
        invalid = ([], self.args[:-1], self.args + self.args[:2], ["--help", "x"],
                   ["--result-file=x", *self.args[1:]], ["@args.txt"], "--help",
                   [*self.args[:2], "--result-file", *self.args[3:]], [*self.args[:-1], Path("x")])
        with patch.object(native, "_WindowsIO", side_effect=AssertionError("no input IO")):
            for args in invalid:
                with self.subTest(args=repr(args)):
                    self.error(self.invoke(args), 2, "invalid_argument", 0)

    def test_help_uses_stdout_once_before_native_or_parent(self):
        with patch.object(native, "_WindowsIO", side_effect=AssertionError("no input IO")):
            status, out, err, count = self.invoke(["--help"])
        self.assertEqual((status, count, out.writes, err.writes), (0, 0, 1, 0))
        for flag in FLAGS:
            self.assertIn(flag, out.getvalue())

    def test_missing_file_and_directory_are_distinct_from_semantic_absence(self):
        self.paths[2].unlink()
        self.error(self.invoke(), 4, "not_found", 0)
        self.paths[2].mkdir()
        self.error(self.invoke(), 4, "path_invalid", 0)

    def test_local_path_restrictions(self):
        for bad in ("", "..\\policy.json", "C:policy.json", "\\\\server\\share\\policy.json",
                    "\\\\?\\C:\\policy.json", str(self.folder / "policy.json."), str(self.folder / "NUL.json")):
            with self.subTest(path=bad):
                args = list(self.args)
                args[5] = bad
                self.error(self.invoke(args), 4, "path_invalid", 0)

    def test_bom_duplicates_nonfinite_surrogate_and_utf8_rejected_before_api(self):
        for raw in (b"\xef\xbb\xbf{}", b'{"x":1,"x":2}', b'{"x":{"x":1,"x":2}}',
                    b"NaN", b"Infinity", b"-Infinity", b"1e999", b'"\\ud800"', b"\xff", b"{", b"{} {}", b""):
            with self.subTest(raw=raw):
                self.paths[2].write_bytes(raw)
                self.error(self.invoke(), 4, "json_invalid", 0)

    def test_depth_and_total_raw_limit_before_api(self):
        self.paths[2].write_bytes(b"[" * 40 + b"0" + b"]" * 40)
        self.error(self.invoke(), 4, "json_invalid", 0)
        self.paths[2].write_bytes(b" " * (2 * 1024 * 1024) + b"null")
        self.error(self.invoke(), 4, "input_limit", 0)

    def test_whitespace_order_and_single_explicit_relative_paths(self):
        self.paths[2].write_text(json.dumps(self.values[2], indent=2), encoding="utf-8")
        args = [value for flag, path in reversed(list(zip(FLAGS, self.paths))) for value in (flag, path.name)]
        before = Path.cwd()
        try:
            os.chdir(self.folder)
            status, out, err, count = self.invoke(args)
        finally:
            os.chdir(before)
        self.assertEqual((status, count, err.writes), (0, 1, 0))
        self.assertEqual(out.getvalue().encode("utf-8"), wire(self.expected))

    def test_windows_native_unavailable_has_no_portable_fallback(self):
        with patch.object(native, "_WindowsIO", side_effect=NotImplementedError):
            self.error(self.invoke(), 4, "unavailable", 0)

    def test_reparse_attribute_injection_is_rejected(self):
        original = native._not_reparse
        def reject(info):
            if info.st_size == self.paths[2].stat().st_size:
                from types import SimpleNamespace
                info = SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return original(info)
        with patch.object(native, "_not_reparse", side_effect=reject):
            self.error(self.invoke(), 4, "path_invalid", 0)

    def test_all_four_sources_pinned_during_exactly_one_parent_call(self):
        def operation(*args, **kwargs):
            for path in self.paths:
                with self.assertRaises(PermissionError):
                    path.write_bytes(b"changed")
                with self.assertRaises(PermissionError):
                    path.rename(path.with_suffix(".moved"))
            return self.expected
        self.assertEqual(self.invoke(operation=operation)[0], 0)
        for path in self.paths:
            self.assertTrue(path.is_file())

    def test_same_stamp_raw_drift_after_api_withholds_stdout(self):
        original = native._read_descriptor
        seen = set()
        def drift(fd, limit, code):
            raw = original(fd, limit, code)
            if fd in seen:
                return b" " + raw[1:]
            seen.add(fd)
            return raw
        with patch.object(native, "_read_descriptor", side_effect=drift):
            self.error(self.invoke(), 4, "input_changed", 1)

    def test_post_api_native_stamp_change_withholds_stdout(self):
        original, post = native._stamp, []
        def operation(*args, **kwargs):
            post.append(True)
            return self.expected
        def drift(info):
            value = original(info)
            return value[:3] + (value[3] + 1,) + value[4:] if post else value
        with patch.object(native, "_stamp", side_effect=drift):
            self.error(self.invoke(operation=operation), 4, "input_changed", 1)

    def test_parent_error_is_sanitized_and_no_retry(self):
        def operation(*args, **kwargs):
            raise RuntimeError("sensitive supplied path and value")
        self.error(self.invoke(operation=operation), 4, "unavailable", 1)

    def test_even_untrusted_private_error_has_fixed_diagnostic(self):
        def operation(*args, **kwargs):
            raise self.cli._Failure("sensitive supplied value")
        self.error(self.invoke(operation=operation), 4, "unavailable", 1)

    def test_total_raw_exact_limit_and_one_byte_above(self):
        others = sum(path.stat().st_size for path in self.paths if path != self.paths[2])
        policy = self.paths[2].read_bytes()
        self.paths[2].write_bytes(policy + b" " * (2 * 1024 * 1024 - others - len(policy)))
        self.assertEqual(sum(path.stat().st_size for path in self.paths), 2 * 1024 * 1024)
        status, out, err, count = self.invoke()
        self.assertEqual((status, count, err.writes), (0, 1, 0))
        self.assertEqual(out.getvalue().encode("utf-8"), wire(self.expected))
        self.paths[2].write_bytes(self.paths[2].read_bytes() + b" ")
        self.error(self.invoke(), 4, "input_limit", 0)

    def test_post_api_source_missing_is_input_changed(self):
        original, post = native._Tree.file_stat, []
        def operation(*args, **kwargs):
            post.append(True)
            return self.expected
        def missing(tree, path):
            if post:
                raise FileNotFoundError()
            return original(tree, path)
        with patch.object(native._Tree, "file_stat", new=missing):
            self.error(self.invoke(operation=operation), 4, "input_changed", 1)

    def test_keyboard_interrupt_first_and_memory_systemexit_are_not_success(self):
        for error, status, code in ((KeyboardInterrupt(), 130, "interrupted"),
                                    (MemoryError(), 4, "unavailable"), (SystemExit(0), 4, "unavailable")):
            def operation(*args, **kwargs):
                raise error
            with self.subTest(error=type(error).__name__):
                self.error(self.invoke(operation=operation), status, code, 1)

    def test_cleanup_before_output_and_known_handles_closed(self):
        original, held = observation_read._close, []
        def close(backend):
            held.extend(backend.held)
            return original(backend)
        with patch.object(observation_read, "_close", side_effect=close):
            self.assertEqual(self.invoke()[0], 0)
        self.assertTrue(held)
        for fd in held:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_cleanup_failure_and_first_error_priority(self):
        original = observation_read._close
        for prior, closing, status, code, calls in (
                (False, OSError(), 4, "unavailable", 1),
                (False, KeyboardInterrupt(), 130, "interrupted", 1),
                (True, KeyboardInterrupt(), 4, "not_found", 0),
                (True, MemoryError(), 4, "not_found", 0)):
            with self.subTest(prior=prior, closing=type(closing).__name__):
                self.save()
                if prior:
                    self.paths[2].unlink()
                def close(backend):
                    original(backend)
                    raise closing
                with patch.object(observation_read, "_close", side_effect=close):
                    self.error(self.invoke(), status, code, calls)

    def test_invalid_parent_shape_flags_and_nonfinite_fail_closed(self):
        bad = []
        for key, value in (("extra", 1), ("schema_version", True), ("status", "ok")):
            output = deepcopy(self.expected)
            output[key] = value
            bad.append(output)
        for section, key, value in (("verification", "execution_authority", True),
                                    ("verification", "hardware_verified", 0),
                                    ("reference", "authenticity_verified", 0),
                                    ("conformity", "verdict", "PASS"),
                                    ("comparison", "within_tolerance", 1),
                                    ("comparison", "twin_value_dbm", float("inf"))):
            output = deepcopy(self.expected)
            output[section][key] = value
            bad.append(output)
        for output in bad:
            with self.subTest(output=repr(output)[:200]):
                self.error(self.invoke(operation=lambda *a, **k: output), 4, "unavailable", 1)

    def test_output_byte_cap_includes_one_lf_without_truncation(self):
        base = deepcopy(self.expected)
        base["reasons"] = [{"code": "authored_boundary", "field": "input", "detail": ""}]
        room = 256 * 1024 - len(wire(base))
        base["reasons"][0]["detail"] = "x" * room
        self.assertEqual(len(wire(base)), 256 * 1024)
        status, out, err, count = self.invoke(operation=lambda *a, **k: base)
        self.assertEqual((status, count, len(out.getvalue().encode("utf-8"))), (0, 1, 256 * 1024))
        base["reasons"][0]["detail"] += "x"
        self.error(self.invoke(operation=lambda *a, **k: base), 4, "unavailable", 1)

    def test_stdout_broken_short_write_flush_and_no_retry(self):
        for out in (Stream(write_error=BrokenPipeError()), Stream(write_error=OSError()),
                    Stream(short=True), Stream(flush_error=OSError())):
            with self.subTest(kind=repr(out.__dict__)):
                status, out, err, count = self.invoke(out=out)
                self.assertEqual((status, count, out.writes, err.writes), (1, 1, 1, 1))
                self.assertEqual(json.loads(err.getvalue()), {"error": {"code": PREFIX + "output_failed"}})

    def test_first_output_interrupt_and_secondary_diagnostic_interrupt(self):
        status, out, err, count = self.invoke(out=Stream(write_error=KeyboardInterrupt()))
        self.assertEqual((status, count, out.writes), (130, 1, 1))
        self.assertEqual(json.loads(err.getvalue()), {"error": {"code": PREFIX + "interrupted"}})
        status, out, err, count = self.invoke([], err=Stream(write_error=KeyboardInterrupt()))
        self.assertEqual((status, count, out.writes, err.writes), (2, 0, 0, 1))

    def test_process_reconfigures_only_own_streams_and_calls_main_once(self):
        out, err = Stream(), Stream()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err), patch.object(self.cli, "main", return_value=3) as main:
            self.assertEqual(self.cli._process_main(), 3)
        self.assertEqual(main.call_count, 1)
        for stream in (out, err):
            self.assertEqual(stream.configuration, dict(encoding="utf-8", errors="strict", newline="\n"))

    def test_process_configuration_failure_prevents_main_and_retains_first(self):
        for first, second, expected in ((OSError(), KeyboardInterrupt(), 1),
                                       (KeyboardInterrupt(), OSError(), 130)):
            out, err = Stream(), Stream()
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err), patch.object(
                    out, "reconfigure", side_effect=first), patch.object(
                    err, "reconfigure", side_effect=second), patch.object(self.cli, "main") as main:
                self.assertEqual(self.cli._process_main(), expected)
                self.assertEqual(main.call_count, 0)
            code = "interrupted" if expected == 130 else "output_failed"
            self.assertEqual(json.loads(err.getvalue()), {"error": {"code": PREFIX + code}})

    def test_process_final_flush_preserves_earlier_failure_and_quiets(self):
        for initial, error, expected in ((4, KeyboardInterrupt(), 4), (2, OSError(), 2),
                                         (130, OSError(), 130), (0, OSError(), 1), (3, KeyboardInterrupt(), 130)):
            with self.subTest(initial=initial, error=type(error).__name__):
                out, err = Stream(flush_error=error), Stream()
                with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err), patch.object(
                        self.cli, "main", return_value=initial), patch.object(os, "_exit", side_effect=SystemExit) as immediate:
                    with self.assertRaises(SystemExit):
                        self.cli._process_main()
                self.assertEqual(immediate.call_args.args, (expected,))

    def child_environment(self, tag):
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="cp949")
        audit = None
        owner = os.environ.get("DEV3_COMPARISON_TEST_GUARD")
        if owner is not None:
            guard = Path(owner) / "child-guard"
            audit = self.folder / (tag + "-audit.json")
            env["PYTHONPATH"] = str(guard) + os.pathsep + str(ROOT)
            env["DEV3_COMPARISON_CHILD_AUDIT"] = str(audit)
            import guarded_io
            guarded_io.reserve_many({audit: 2048})
        return env, audit

    def child(self, tag, args):
        env, audit = self.child_environment(tag)
        run = subprocess.run([sys.executable, "-B", "-m", MODULE, *args], cwd=self.folder,
                             env=env, capture_output=True, timeout=30)
        proof = None if audit is None else json.loads(audit.read_bytes())
        if proof is not None:
            self.assertEqual((proof["utf8_stdout"], proof["utf8_stderr"]), ("utf-8", "utf-8"))
            self.assertEqual((proof["actual_model"], proof["network"], proof["store_sql"], proof["hardware"]), (0, 0, 0, 0))
        return run, proof

    def test_actual_module_children_exit_zero_three_four_and_utf8(self):
        args = [value for flag, path in zip(FLAGS, self.paths) for value in (flag, path.name)]
        for tag, expected, calls in (("compared", 0, 1), ("held", 3, 1), ("missing", 4, 0)):
            with self.subTest(tag=tag):
                if tag == "held":
                    self.paths[2].write_bytes(b"null")
                elif tag == "missing":
                    self.paths[2].unlink()
                run, audit = self.child(tag, args)
                self.assertEqual(run.returncode, expected, run.stderr.decode("utf-8"))
                if expected in (0, 3):
                    body = json.loads(run.stdout.decode("utf-8"))
                    self.assertEqual(set(body), KEYS)
                    self.assertEqual(run.stderr, b"")
                    self.assertEqual(run.stdout, wire(self.expected) if expected == 0 else wire(body))
                else:
                    self.assertEqual(run.stdout, b"")
                    self.assertEqual(json.loads(run.stderr), {"error": {"code": PREFIX + "not_found"}})
                if audit is not None:
                    self.assertEqual((audit["api"], audit["native_backend"], audit["known_cleanup"]), (calls, 1, 1))

    def test_actual_module_help_is_utf8_and_imports_no_comparison(self):
        run, audit = self.child("help", ["--help"])
        self.assertEqual((run.returncode, run.stderr), (0, b""))
        self.assertIn("합성".encode("utf-8"), run.stdout)
        if audit is not None:
            self.assertEqual((audit["api"], audit["native_backend"], audit["known_cleanup"]), (0, 0, 0))
            self.assertFalse(audit["comparison_imported"])

    def test_actual_module_closed_stdout_exits_one_without_interpreter_120(self):
        env, audit = self.child_environment("closed-stdout")
        with subprocess.Popen([sys.executable, "-B", "-m", MODULE, *self.args], cwd=self.folder,
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            process.stdout.close()
            process.stdout = None
            out, err = process.communicate(timeout=30)
        self.assertEqual((process.returncode, out), (1, None))
        self.assertEqual(json.loads(err), {"error": {"code": PREFIX + "output_failed"}})
        if audit is not None:
            proof = json.loads(audit.read_bytes())
            self.assertEqual((proof["api"], proof["known_cleanup"]), (1, 1))
