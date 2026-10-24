"""CLI boundary tests using synthetic packets, never collected originals."""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from labflow.control_packet_audit import audit_control_packet, ControlPacketAuditError


class ControlPacketCheckTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]
        parent = self.repo / ".local" / "CONTROL-PACKET-CHECK-D1" / "fixtures"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.packet = Path(self.temp.name) / "\ud569\uc131-PRIVATE-PACKET-PATH"
        self.packet.mkdir()
        self.payload = self.packet / "\ud569\uc131-PRIVATE-FILENAME.html"
        self.payload.write_bytes(b"synthetic body PRIVATE-BODY PRIVATE-SERIAL")
        index = {
            "request_id": "DEV-CONTROL-SOURCES-008",
            "revision": "SYNTHETIC-CLI-v1",
            "source_code_executed": False,
            "runtime_or_hardware_support_confirmed": False,
            "public_export_allowed": False,
            "observation": {"secret": "PRIVATE-SECRET"},
            "files": [{"path": self.payload.name, "bytes": self.payload.stat().st_size,
                       "sha256": hashlib.sha256(self.payload.read_bytes()).hexdigest()}],
        }
        raw = json.dumps(index, separators=(",", ":")).encode("utf-8")
        (self.packet / "intake-v1.json").write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()

    def invoke(self, *args):
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        return subprocess.run(
            [sys.executable, "-B", "-m", "labflow.control_packet_check", *map(str, args)],
            cwd=self.repo, capture_output=True, encoding="utf-8", timeout=20, **options,
        )

    def arguments(self):
        return ["--packet-dir", str(self.packet), "--index-sha256", self.pin]

    def snapshot(self):
        return {p.relative_to(self.packet).as_posix():
                (p.read_bytes(), p.stat().st_size, p.stat().st_mtime_ns)
                for p in self.packet.rglob("*") if p.is_file()}

    def assert_no_private_output(self, output):
        for value in (str(self.packet), self.packet.name, self.payload.name,
                      "PRIVATE-BODY", "PRIVATE-SERIAL", "PRIVATE-SECRET"):
            self.assertNotIn(value, output)

    def assert_failure(self, result, code, exit_code):
        self.assertEqual(result.returncode, exit_code)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr), {"error": code})
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assert_no_private_output(result.stderr)

    def in_process(self, module, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = module.main(argv)
        return subprocess.CompletedProcess([], result, stdout.getvalue(), stderr.getvalue())

    def test_explicit_packet_prints_exact_audit_summary_without_writes(self):
        before = self.snapshot()
        result = self.invoke(*self.arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), audit_control_packet(
            self.packet, expected_index_sha256=self.pin))
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assert_no_private_output(result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_audit_failure_reports_fixed_code_and_preserves_input(self):
        self.payload.write_bytes(b"changed synthetic body PRIVATE-BODY")
        before = self.snapshot()
        result = self.invoke(*self.arguments())
        self.assert_failure(result, "packet_payload_mismatch", 1)
        self.assertEqual(before, self.snapshot())

    def test_missing_empty_and_whitespace_arguments(self):
        for args in ([], ["--packet-dir", str(self.packet)], ["--index-sha256", self.pin],
                     ["--packet-dir", "--index-sha256", self.pin],
                     ["--packet-dir", "", "--index-sha256", self.pin],
                     ["--packet-dir", str(self.packet), "--index-sha256", ""],
                     ["--packet-dir=", "--index-sha256=" + self.pin],
                     ["--packet-dir=" + str(self.packet), "--index-sha256="],
                     ["--packet-dir", "  ", "--index-sha256", self.pin]):
            with self.subTest(args_count=len(args)):
                self.assert_failure(self.invoke(*args), "packet_cli_invalid_argument", 2)

    def test_duplicate_options_in_separated_and_equals_forms(self):
        for extra in (["--packet-dir", "PRIVATE-SECRET"], ["--packet-dir=PRIVATE-SECRET"],
                      ["--index-sha256", self.pin], ["--index-sha256=" + self.pin]):
            with self.subTest(option=extra[0].split("=")[0]):
                self.assert_failure(self.invoke(*self.arguments(), *extra), "packet_cli_invalid_argument", 2)

    def test_unknown_abbreviated_and_positional_arguments_do_not_echo(self):
        for args in ([*self.arguments(), "--PRIVATE-SECRET=\ud55c\uae00"],
                     [*self.arguments(), "PRIVATE-SECRET"],
                     ["--packet", str(self.packet), "--index-sha256", self.pin],
                     ["--packet-dir", str(self.packet), "--index-sha", self.pin],
                     [*self.arguments(), "--output", str(self.packet / "PRIVATE-SECRET")],
                     ["@PRIVATE-SECRET"], ["-h"]):
            with self.subTest(args_count=len(args)):
                self.assert_failure(self.invoke(*args), "packet_cli_invalid_argument", 2)
        self.assertFalse((self.packet / "PRIVATE-SECRET").exists())

    def test_only_standalone_help_is_successful(self):
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("labflow.control_packet_check", result.stdout)
        self.assertIn("--packet-dir", result.stdout)
        self.assertIn("--index-sha256", result.stdout)
        self.assert_no_private_output(result.stdout)
        for args in (["--help", "PRIVATE-SECRET"], [*self.arguments(), "--help"],
                     ["--help", "--help"], ["--help=PRIVATE-SECRET"]):
            with self.subTest(args_count=len(args)):
                self.assert_failure(self.invoke(*args), "packet_cli_invalid_argument", 2)

    def test_equals_form_for_both_required_options(self):
        result = self.invoke("--packet-dir=" + str(self.packet), "--index-sha256=" + self.pin)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["index_sha256"], self.pin)

    def test_explicit_wrong_pin_is_not_replaced_by_computed_hash(self):
        result = self.invoke("--packet-dir", str(self.packet), "--index-sha256", "0" * 64)
        self.assert_failure(result, "packet_index_mismatch", 1)

    def test_nonempty_hash_format_validation_is_delegated_to_audit(self):
        for pin in (self.pin.upper(), "x" * 64, "a" * 63, "PRIVATE-SECRET"):
            with self.subTest(length=len(pin)):
                self.assert_failure(self.invoke("--packet-dir", str(self.packet),
                                                "--index-sha256", pin), "packet_invalid_argument", 1)

    def test_nonlocal_path_values_fail_without_raw_output(self):
        for root in ("https://invalid.example/PRIVATE-SECRET", "//invalid/PRIVATE-SECRET",
                     "\\\\invalid\\PRIVATE-SECRET"):
            with self.subTest(kind=root[:2]):
                self.assert_failure(self.invoke("--packet-dir", root, "--index-sha256", self.pin),
                                    "packet_invalid_argument", 1)

    def test_missing_packet_is_audit_failure(self):
        result = self.invoke("--packet-dir", self.packet / "PRIVATE-SECRET", "--index-sha256", self.pin)
        self.assert_failure(result, "packet_unavailable", 1)

    def test_all_frozen_audit_error_codes_are_stderr_exit_one(self):
        module = importlib.import_module("labflow.control_packet_check")
        for code in ("packet_invalid_argument", "packet_unavailable", "packet_index_invalid",
                     "packet_index_mismatch", "packet_index_changed", "packet_path_invalid",
                     "packet_limit_exceeded", "packet_payload_mismatch", "packet_json_invalid",
                     "packet_zip_invalid"):
            with self.subTest(code=code), mock.patch.object(module, "audit_control_packet",
                                                           side_effect=ControlPacketAuditError(code)):
                self.assert_failure(self.in_process(module, self.arguments()), code, 1)

    def test_unexpected_exception_and_interrupt_are_sanitized(self):
        module = importlib.import_module("labflow.control_packet_check")
        for exception, code, status in (
            (RuntimeError("PRIVATE-SECRET " + str(self.packet)), "packet_cli_internal_error", 1),
            (KeyboardInterrupt("PRIVATE-SERIAL"), "packet_cli_interrupted", 130),
        ):
            with self.subTest(code=code), mock.patch.object(module, "audit_control_packet", side_effect=exception):
                self.assert_failure(self.in_process(module, self.arguments()), code, status)

    def test_module_entry_unexpected_and_interrupt_real_process_exit_codes(self):
        # Trusted test launcher injects faults without adding production switches.
        launcher = """
import runpy, sys
from unittest.mock import patch
import labflow.control_packet_audit as source
mode = sys.argv[1]
sys.argv = ['labflow.control_packet_check', *sys.argv[2:]]
error = KeyboardInterrupt('PRIVATE-SERIAL') if mode == 'interrupt' else RuntimeError('PRIVATE-SECRET')
with patch.object(source, 'audit_control_packet', side_effect=error):
    runpy.run_module('labflow.control_packet_check', run_name='__main__')
"""
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        for mode, code, status in (("unexpected", "packet_cli_internal_error", 1),
                                   ("interrupt", "packet_cli_interrupted", 130)):
            with self.subTest(mode=mode):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", launcher, mode, *self.arguments()],
                    cwd=self.repo, capture_output=True, encoding="utf-8", timeout=20, **options,
                )
                self.assert_failure(result, code, status)

    def test_unrecognized_or_invalid_audit_error_code_is_internal_error(self):
        module = importlib.import_module("labflow.control_packet_check")
        for code in ("PRIVATE-SECRET", ["PRIVATE-SECRET"]):
            error = ControlPacketAuditError("packet_unavailable")
            error.code = code
            with self.subTest(code_type=type(code).__name__), \
                    mock.patch.object(module, "audit_control_packet", side_effect=error):
                self.assert_failure(self.in_process(module, self.arguments()), "packet_cli_internal_error", 1)

    def test_invalid_arguments_do_not_call_audit(self):
        module = importlib.import_module("labflow.control_packet_check")
        for args in ([], [*self.arguments(), "PRIVATE-SECRET"],
                     [*self.arguments(), "--packet-dir=PRIVATE-SECRET"], ["--help", "PRIVATE-SECRET"]):
            with self.subTest(args_count=len(args)), mock.patch.object(module, "audit_control_packet") as checker:
                self.assert_failure(self.in_process(module, args), "packet_cli_invalid_argument", 2)
                checker.assert_not_called()

    def test_help_uses_static_program_name_without_audit_or_sys_argv_echo(self):
        module = importlib.import_module("labflow.control_packet_check")
        with mock.patch.object(sys, "argv", ["PRIVATE-SECRET", "--help"]), \
                mock.patch.object(module, "audit_control_packet") as checker:
            result = self.in_process(module, None)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("labflow.control_packet_check", result.stdout)
        self.assert_no_private_output(result.stdout)
        checker.assert_not_called()

    def closed_pipe_process(self, args, *, stdout_closed=False, stderr_closed=False, launcher=None):
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        command = [sys.executable, "-B"]
        command += ["-c", launcher] if launcher is not None else ["-m", "labflow.control_packet_check"]
        process = subprocess.Popen(
            [*command, *args],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", **options,
        )
        try:
            if stdout_closed:
                process.stdout.close()
                process.stdout = None
            if stderr_closed:
                process.stderr.close()
                process.stderr = None
            stdout, stderr = process.communicate(timeout=20)
            return subprocess.CompletedProcess([], process.returncode, stdout or "", stderr or "")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_closed_stdout_keeps_internal_error_exit_and_no_shutdown_diagnostic(self):
        before = self.snapshot()
        result = self.closed_pipe_process(self.arguments(), stdout_closed=True)
        self.assert_failure(result, "packet_cli_internal_error", 1)
        self.assertEqual(before, self.snapshot())

    def test_closed_help_stdout_is_internal_error_instead_of_success(self):
        result = self.closed_pipe_process(["--help"], stdout_closed=True)
        self.assert_failure(result, "packet_cli_internal_error", 1)

    def test_closed_stderr_keeps_invalid_argument_exit_and_empty_stdout(self):
        result = self.closed_pipe_process(["--PRIVATE-SECRET"], stderr_closed=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_both_closed_pipes_keep_internal_error_exit(self):
        result = self.closed_pipe_process(self.arguments(), stdout_closed=True, stderr_closed=True)
        self.assertEqual(result.returncode, 1)

    def test_failed_process_sink_repair_preserves_exit_without_shutdown_diagnostic(self):
        launcher = """
import os, runpy, sys
from unittest.mock import patch
original_open = os.open
def guarded_open(path, *args, **kwargs):
    if os.fspath(path) == os.devnull:
        raise OSError('PRIVATE-SECRET null sink unavailable')
    return original_open(path, *args, **kwargs)
sys.argv = ['labflow.control_packet_check', *sys.argv[1:]]
with patch.object(os, 'open', side_effect=guarded_open):
    runpy.run_module('labflow.control_packet_check', run_name='__main__')
"""
        result = self.closed_pipe_process(self.arguments(), stdout_closed=True, launcher=launcher)
        self.assert_failure(result, "packet_cli_internal_error", 1)

    def test_main_caller_keeps_ownership_of_failed_streams(self):
        module = importlib.import_module("labflow.control_packet_check")

        class FailedStream:
            closed = False

            def write(self, value):
                raise OSError("PRIVATE-SECRET stream write")

            def flush(self):
                raise OSError("PRIVATE-SECRET stream flush")

            def fileno(self):
                raise AssertionError("main must not access the caller's descriptor")

            def close(self):
                self.closed = True
                raise AssertionError("main must not close the caller's stream")

        failed = FailedStream()
        stderr = io.StringIO()
        with mock.patch.object(sys, "stdout", failed), redirect_stderr(stderr), \
                mock.patch.object(os, "dup2") as duplicate:
            self.assertEqual(module.main(self.arguments()), 1)
            self.assertIs(sys.stdout, failed)
            duplicate.assert_not_called()
        self.assertEqual(json.loads(stderr.getvalue()), {"error": "packet_cli_internal_error"})
        self.assertFalse(failed.closed)

        stdout = io.StringIO()
        with redirect_stdout(stdout), mock.patch.object(sys, "stderr", failed), \
                mock.patch.object(os, "dup2") as duplicate:
            self.assertEqual(module.main([]), 2)
            self.assertIs(sys.stderr, failed)
            duplicate.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(failed.closed)


if __name__ == "__main__":
    unittest.main()
