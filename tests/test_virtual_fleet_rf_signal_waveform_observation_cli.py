"""Explicit observation CLI contracts; unit wire fixtures are not publications."""
import builtins
from contextlib import ExitStack
from copy import deepcopy
from io import StringIO
import importlib
import importlib.util
from itertools import permutations
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

NAME = "labflow.virtual_fleet.rf_signal_waveform_observation_cli"
cli = importlib.import_module(NAME) if importlib.util.find_spec(NAME) else None
PREFIX = "rf_signal_waveform_observation_cli_"
_UNSET = object()
ARGS = ["--run-name", "run048", "--observation-name", "observe_cli", "--sample-rate-hz", "8",
        "--sample-count", "1", "--seed", "7"]


def unit_wire():
    """Literal public wire fixture, with no private artifact or publication claim."""
    return dict(schema_version=1, kind="synthetic_rf_baseband_observation", observation_name="observe_cli",
        storage=dict(state="published", path=".local/rf-waveform-observations/observe_cli/observation.json",
                     bytes=9876, sha256="1" * 64),
        source=dict(run_name="run048", run_id="unit-run", runtime_instance_id="unit-instance",
                    manifest_sha256="2" * 64, snapshot_sha256="3" * 64),
        math=dict(source_scenario_id="cw_peak", reference_plane="declared_dut_output",
                  binding_scope="declared_source_projection_only", spec_sha256="4" * 64,
                  packet_sha256="5" * 64, analysis_sha256="6" * 64),
        verification=dict(data_origin="authored_synthetic", synthetic=True, hardware_verified=False,
            physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
            regulatory_scope_complete=False, method_approval="not_assessed", model_scope="normalized_baseband_sample_math_v1"),
        execution_authorized=False, rerun_authorized=False)


class _Support(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cli, "explicit observation CLI public entry is absent")

    def invoke(self, arguments, *, stdout=None, stderr=None):
        out = StringIO() if stdout is None else stdout
        err = StringIO() if stderr is None else stderr
        with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            status = cli.main(arguments)
        self.assertFalse(out.closed)
        self.assertFalse(err.closed)
        return status, out, err

    def error(self, arguments, suffix, *, status=2):
        result, out, err = self.invoke(arguments)
        self.assertEqual((result, out.getvalue()), (status, ""))
        self.assertEqual(err.getvalue(), '{"error":{"code":"' + PREFIX + suffix + '"}}\n')


class CLIArgumentTests(_Support):
    def no_parent(self):
        original = builtins.__import__
        def guarded(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "labflow.virtual_fleet.rf_signal_waveform_observation" or "rf_signal_waveform_observation" in (fromlist or ()):
                raise AssertionError("055 import before validated record path")
            return original(name, globals, locals, fromlist, level)
        return mock.patch.object(builtins, "__import__", guarded)

    def test_help_is_stderr_only_without_parent_import(self):
        for arguments in (["--help"], ("--help",)):
            with self.subTest(container=type(arguments).__name__), self.no_parent():
                status, out, err = self.invoke(arguments)
            self.assertEqual((status, out.getvalue()), (0, ""))
            self.assertIn("Usage:", err.getvalue())
            for flag in ARGS[::2]:
                self.assertIn(flag, err.getvalue())
            self.assertTrue(err.getvalue().endswith("\n"))
            self.assertNotIn("run048", err.getvalue())

    def test_exact_plain_containers_and_strings_only(self):
        class Derived(list):
            def __iter__(self):
                raise AssertionError("caller callback")
        class Text(str):
            def __str__(self):
                raise AssertionError("caller callback")
        values = [None, "--help", {}, False, Path("x"), Derived(ARGS), [Text("--help")],
                  [*ARGS[:-1], Text("7")], [*ARGS[:-1], 7]]
        for arguments in values[1:]:
            with self.subTest(type=type(arguments).__name__), self.no_parent():
                self.error(arguments, "invalid_argument")
        with self.no_parent(), mock.patch.object(sys, "argv", ["module", "--seed", "7"]):
            self.error(None, "invalid_argument")

    def test_missing_duplicate_unknown_and_nonpair_syntax_rejects_before_import(self):
        values = [[], ["--help", "x"], ARGS[:-1], ARGS + ["--help"], ARGS + ["--x", "v"],
                  ["--run-name=x", *ARGS[2:]], ["--run", *ARGS[1:]],
                  ["@arguments", *ARGS[1:]], ["x" * 10000, *ARGS[1:]],
                  [*ARGS[:-2], "--sample-count", "7"]]
        for arguments in values:
            with self.subTest(arguments=arguments[:2]), self.no_parent():
                self.error(arguments, "invalid_argument")

    def test_numeric_grammar_and_bounds_are_checked_before_import(self):
        for index, values in [(5, ["0", "1000000001", "9999999999", "8" * 10000]),
                              (7, ["0", "4097", "10000"]), (9, ["-1", "2147483648", "9" * 10000])]:
            for value in values + ["+1", "01", " 1", "1 ", "1.0", "1_0", "1e0", "１", "١", "--help", ""]:
                arguments = list(ARGS); arguments[index] = value
                with self.subTest(index=index, value=value[:16]), self.no_parent():
                    self.error(arguments, "invalid_argument")

    def test_main_never_configures_or_closes_caller_streams(self):
        class Tracked(StringIO):
            def reconfigure(self, **kwargs):
                raise AssertionError("caller reconfigure")
            def close(self):
                self.close_calls += 1
                super().close()
        out, err = Tracked(), Tracked()
        out.close_calls = err.close_calls = 0
        status, _, _ = self.invoke(["--help"], stdout=out, stderr=err)
        self.assertEqual((status, out.close_calls, err.close_calls), (0, 0, 0))


class _ParentSupport(_Support):
    def setUp(self):
        super().setUp()
        from labflow.virtual_fleet import rf_signal_waveform_observation
        self.parent = rf_signal_waveform_observation

    def call(self, arguments=ARGS, *, value=_UNSET, effect=None, stdout=None, stderr=None):
        value = unit_wire() if value is _UNSET else value
        with mock.patch.object(self.parent, "record_rf_baseband_observation",
                               side_effect=effect, return_value=value) as called:
            result = self.invoke(arguments, stdout=stdout, stderr=stderr)
        self.called = called
        return result

    def own_failure(self, *, value=_UNSET, effect=None, suffix="delivery_unconfirmed", status=1):
        result, out, err = self.call(value=value, effect=effect)
        self.assertEqual((result, out.getvalue()), (status, ""))
        self.assertEqual(err.getvalue(), '{"error":{"code":"' + PREFIX + suffix + '"}}\n')
        self.called.assert_called_once()


class CLIParentSummaryTests(_ParentSupport):
    def test_all_pair_orders_forward_exact_request_once_and_preserve_wire(self):
        pairs = list(zip(ARGS[::2], ARGS[1::2]))
        for ordered in permutations(pairs):
            arguments = [part for pair in ordered for part in pair]
            value = unit_wire(); before = deepcopy(value)
            result, out, err = self.call(arguments, value=value)
            self.assertEqual((result, err.getvalue()), (0, ""))
            self.called.assert_called_once_with(dict(schema_version=1, run_name="run048", observation_name="observe_cli",
                sample_rate_hz=8, sample_count=1, seed=7))
            expected = json.dumps(before, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n"
            self.assertEqual(out.getvalue(), expected)
            self.assertEqual(value, before)
            self.assertLessEqual(len(out.getvalue().encode("utf-8")), 8193)

    def test_numeric_boundaries_and_original_names_are_parent_owned(self):
        for fs, count, seed in [("1", "1", "0"), ("1000000000", "4096", "2147483647")]:
            arguments = list(ARGS); arguments[5], arguments[7], arguments[9] = fs, count, seed
            result, out, err = self.call(arguments)
            self.assertEqual((result, err.getvalue()), (0, ""))
            request = self.called.call_args.args[0]
            self.assertEqual((request["sample_rate_hz"], request["sample_count"], request["seed"]), (int(fs), int(count), int(seed)))
            self.assertTrue(all(type(request[key]) is int for key in ("schema_version", "sample_rate_hz", "sample_count", "seed")))
        for name in ("", "../PRIVATE", "CON", "--help", "x" * 10000):
            arguments = list(ARGS); arguments[1] = name
            error = self.parent.RfSignalWaveformObservationError("rf_signal_waveform_observation_invalid_argument")
            result, out, err = self.call(arguments, effect=error)
            self.assertEqual((result, out.getvalue()), (2, ""))
            self.assertEqual(self.called.call_args.args[0]["run_name"], name)
            self.assertNotIn("PRIVATE", err.getvalue())

    def test_only_exact_parent_codes_at_actual_call_are_passed_through(self):
        for suffix in ["invalid_argument", "source_unavailable", "source_ineligible", "destination_exists",
                       "dependency_changed", "math_unavailable", "write_failed", "publication_uncertain"]:
            code = "rf_signal_waveform_observation_" + suffix
            result, out, err = self.call(effect=self.parent.RfSignalWaveformObservationError(code))
            self.called.assert_called_once()
            self.assertEqual((result, out.getvalue()), (2 if suffix == "invalid_argument" else 1, ""))
            self.assertEqual(err.getvalue(), '{"error":{"code":"' + code + '"}}\n')

    def test_unknown_subclass_nonplain_and_non_KI_BaseExceptions_are_unconfirmed(self):
        class Derived(self.parent.RfSignalWaveformObservationError):
            pass
        class Text(str):
            def __eq__(self, other):
                raise AssertionError("error code callback")
        errors = [RuntimeError("PRIVATE detail"), Derived("rf_signal_waveform_observation_write_failed"),
                  SystemExit(0), GeneratorExit("PRIVATE detail")]
        for value in [False, None, [], "rf_signal_waveform_observation_unknown", Text("x")]:
            error = self.parent.RfSignalWaveformObservationError("rf_signal_waveform_observation_write_failed")
            error.code = value; errors.append(error)
        for error in errors:
            with self.subTest(type=type(error).__name__):
                self.own_failure(effect=error)
        self.own_failure(effect=KeyboardInterrupt(), suffix="interrupted_unconfirmed", status=130)

    def test_import_or_entry_failures_are_unavailable_without_API_attempt(self):
        original = builtins.__import__
        for failure in [RuntimeError("PRIVATE import"), SystemExit(0), KeyboardInterrupt()]:
            def importing(name, globals=None, locals=None, fromlist=(), level=0):
                if "rf_signal_waveform_observation" in (fromlist or ()):
                    raise failure
                return original(name, globals, locals, fromlist, level)
            with mock.patch.object(builtins, "__import__", importing), mock.patch.object(self.parent, "record_rf_baseband_observation") as called:
                result, out, err = self.invoke(ARGS)
            called.assert_not_called()
            expected = "interrupted" if isinstance(failure, KeyboardInterrupt) else "unavailable"
            self.assertEqual((result, out.getvalue()), (130 if expected == "interrupted" else 1, ""))
            self.assertEqual(err.getvalue(), '{"error":{"code":"' + PREFIX + expected + '"}}\n')
        for method, replacement in [("record_rf_baseband_observation", None), ("RfSignalWaveformObservationError", None),
                                    ("RfSignalWaveformObservationError", str)]:
            with mock.patch.object(self.parent, method, replacement):
                result, out, err = self.invoke(ARGS)
            self.assertEqual((result, out.getvalue()), (1, ""))
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "unavailable")

    def test_exact_nested_keys_types_literals_and_ASCII_bounds_precede_json(self):
        class Mapping(dict):
            def __iter__(self):
                raise AssertionError("mapping callback")
        class Text(str):
            def __eq__(self, other):
                raise AssertionError("text callback")
            __hash__ = str.__hash__
        bad = [None, [], Mapping(unit_wire()), {**unit_wire(), "extra": 1}]
        for section in [None, "storage", "source", "math", "verification"]:
            value = unit_wire(); target = value if section is None else value[section]
            for key in list(target):
                changed = deepcopy(value); item = changed if section is None else changed[section]
                del item[key]; bad.append(changed)
            changed = deepcopy(value); item = changed if section is None else changed[section]
            item[Text("bad-key")] = 0; bad.append(changed)
        edits = [(None, "schema_version", True), (None, "kind", Text("synthetic_rf_baseband_observation")),
            (None, "observation_name", "other"), (None, "execution_authorized", 0), (None, "rerun_authorized", True),
            ("storage", "state", "pending"), ("storage", "path", "../PRIVATE"), ("storage", "bytes", True),
            ("storage", "sha256", "A" * 64), ("source", "run_name", "other"),
            ("source", "run_id", "x" * 129), ("source", "runtime_instance_id", "unit-run"),
            ("source", "manifest_sha256", "x" * 64), ("math", "source_scenario_id", "pulse"),
            ("math", "reference_plane", "sensor_input"), ("math", "packet_sha256", None),
            ("verification", "synthetic", 1), ("verification", "hardware_verified", True),
            ("verification", "method_approval", "approved"), ("verification", "model_scope", "unknown")]
        for section, key, replacement in edits:
            changed = unit_wire(); target = changed if section is None else changed[section]
            target[key] = replacement; bad.append(changed)
        for value in bad:
            with self.subTest(kind=type(value).__name__), mock.patch.object(cli.json, "dumps", side_effect=AssertionError("must reject before JSON")) as dumps:
                self.own_failure(value=value)
                dumps.assert_not_called()

    def test_large_keysets_and_deep_or_giant_values_do_not_serialize(self):
        huge = {str(index): None for index in range(10000)}
        deep = unit_wire(); deep["storage"]["path"] = [deepcopy(unit_wire())]
        giant = unit_wire(); giant["source"]["run_id"] = "x" * 100000
        for value in [huge, deep, giant]:
            with mock.patch.object(cli.json, "dumps", side_effect=AssertionError("unbounded serialization")) as dumps:
                self.own_failure(value=value)
                dumps.assert_not_called()

    def test_bundle_byte_budget_is_distinct_from_summary_byte_budget(self):
        for size in [8193, 3145729]:
            value = unit_wire(); value["storage"]["bytes"] = size
            result, out, err = self.call(value=value)
            self.assertEqual((result, err.getvalue()), (0, ""))
            self.assertEqual(json.loads(out.getvalue())["storage"]["bytes"], size)
        for size in [0, -1, 3145730]:
            value = unit_wire(); value["storage"]["bytes"] = size
            self.own_failure(value=value)

    def test_serializer_failures_do_not_become_parent_error_passthrough(self):
        errors = [ValueError("PRIVATE serializer"), self.parent.RfSignalWaveformObservationError("rf_signal_waveform_observation_invalid_argument")]
        for error in errors:
            with mock.patch.object(cli.json, "dumps", side_effect=error):
                self.own_failure()
        with mock.patch.object(cli.json, "dumps", return_value="x" * 8193):
            self.own_failure()

    def test_original_names_survive_parent_mutation_of_request(self):
        def mutate(request):
            request["run_name"], request["observation_name"] = "changed", "changed"
            return unit_wire()
        result, out, err = self.call(effect=mutate)
        self.assertEqual((result, err.getvalue()), (0, ""))
        def wrong_names(request):
            mutate(request); value = unit_wire()
            value["source"]["run_name"] = value["observation_name"] = "changed"
            value["storage"]["path"] = ".local/rf-waveform-observations/changed/observation.json"
            return value
        self.own_failure(effect=wrong_names)


class _Stream(StringIO):
    def __init__(self, *, write_error=None, flush_error=None, flush_at=1, config_error=None, short=_UNSET):
        super().__init__()
        self.write_error, self.flush_error, self.config_error = write_error, flush_error, config_error
        self.flush_at, self.short = flush_at, short
        self.writes = self.flushes = 0
        self.configurations = []

    def write(self, text):
        self.writes += 1
        if self.short is not _UNSET:
            super().write(text[:3])
            return self.short
        if self.write_error is not None:
            raise self.write_error
        return super().write(text)

    def flush(self):
        self.flushes += 1
        if self.flush_error is not None and self.flushes == self.flush_at:
            raise self.flush_error
        return super().flush()

    def reconfigure(self, **options):
        self.configurations.append(options)
        if self.config_error is not None:
            raise self.config_error


class _ProcessExit(BaseException):
    pass


class CLIDeliveryLifetimeTests(_ParentSupport):
    def process(self, arguments, out, err, *, effect=None):
        self.assertTrue(callable(getattr(cli, "_process_main", None)), "module process entry is absent")
        exits = []
        def exiting(status):
            exits.append(status)
            raise _ProcessExit(status)
        with mock.patch.object(sys, "argv", ["module", *arguments]), mock.patch.object(sys, "stdout", out), \
                mock.patch.object(sys, "stderr", err), mock.patch.object(cli.os, "_exit", exiting), \
                mock.patch.object(self.parent, "record_rf_baseband_observation", side_effect=effect, return_value=unit_wire()) as called:
            try:
                result = cli._process_main()
            except _ProcessExit as stopped:
                result = stopped.args[0]
        self.called = called
        self.assertFalse(out.closed)
        self.assertFalse(err.closed)
        return result, exits

    def test_single_write_and_short_write_never_loop_or_repeat_parent(self):
        for count in (None, 0, 3, True, -1):
            out = _Stream(short=count)
            result, out, err = self.call(stdout=out)
            self.assertEqual(result, 1)
            self.assertEqual((out.writes, out.getvalue()), (1, '{"e'))
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "delivery_unconfirmed")
            self.called.assert_called_once()
        out = _Stream()
        result, out, err = self.call(stdout=out)
        self.assertEqual((result, out.writes, out.flushes, err.getvalue()), (0, 1, 1, ""))

    def test_stdout_write_flush_parent_type_and_fake_context_keep_delivery_failure(self):
        fake = OSError("PRIVATE write")
        fake.__context__ = KeyboardInterrupt("PRIVATE unraised")
        typed = self.parent.RfSignalWaveformObservationError("rf_signal_waveform_observation_invalid_argument")
        for out in [_Stream(write_error=fake), _Stream(write_error=typed),
                    _Stream(flush_error=OSError("PRIVATE flush")), _Stream(flush_error=typed),
                    _Stream(write_error=SystemExit(0)), _Stream(flush_error=GeneratorExit())]:
            result, out, err = self.call(stdout=out)
            self.assertEqual((result, out.writes), (1, 1))
            self.called.assert_called_once()
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "delivery_unconfirmed")
            self.assertNotIn("PRIVATE", err.getvalue())

    def test_actual_pre_and_post_attempt_KI_have_different_codes(self):
        with mock.patch.object(cli, "_arguments", side_effect=KeyboardInterrupt()), \
                mock.patch.object(self.parent, "record_rf_baseband_observation") as called:
            result, out, err = self.invoke(ARGS)
        called.assert_not_called()
        self.assertEqual((result, out.getvalue()), (130, ""))
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "interrupted")
        for out in [_Stream(write_error=KeyboardInterrupt()), _Stream(flush_error=KeyboardInterrupt())]:
            result, _, err = self.call(stdout=out)
            self.assertEqual(result, 130)
            self.called.assert_called_once()
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "interrupted_unconfirmed")

    def test_diagnostic_BaseExceptions_never_replace_first_API_or_argument_outcome(self):
        for first, expected in [(self.parent.RfSignalWaveformObservationError("rf_signal_waveform_observation_invalid_argument"), 2),
                                (OSError("PRIVATE first"), 1), (KeyboardInterrupt(), 130)]:
            for later in [OSError("PRIVATE later"), KeyboardInterrupt(), SystemExit(0), GeneratorExit()]:
                err = _Stream(write_error=later)
                result, out, err = self.call(effect=first, stderr=err)
                self.assertEqual((result, out.getvalue(), err.writes), (expected, "", 1))
                self.called.assert_called_once()
        with mock.patch.object(self.parent, "record_rf_baseband_observation") as called:
            result, out, err = self.invoke([], stderr=_Stream(flush_error=KeyboardInterrupt()))
        self.assertEqual((result, out.getvalue()), (2, ""))
        called.assert_not_called()

    def test_process_configures_only_its_streams_and_failure_prevents_main_API(self):
        out, err = _Stream(), _Stream()
        result, exits = self.process(["--help"], out, err)
        self.assertEqual((result, exits, out.getvalue()), (0, [], ""))
        for stream in (out, err):
            self.assertEqual(stream.configurations, [dict(encoding="utf-8", errors="strict", newline="\n")])
        self.called.assert_not_called()
        for failure, expected, suffix in [(OSError("PRIVATE config"), 1, "output_failed"),
                                          (KeyboardInterrupt(), 130, "interrupted"), (SystemExit(0), 1, "output_failed")]:
            out, err = _Stream(config_error=failure), _Stream()
            result, exits = self.process(ARGS, out, err)
            self.assertEqual((result, out.getvalue()), (expected, ""))
            self.called.assert_not_called()
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + suffix)

    def test_final_flush_classifies_help_record_and_retains_first_failure(self):
        for arguments in (["--help"], ARGS):
            for failure in [OSError("PRIVATE final"), KeyboardInterrupt(), SystemExit(0)]:
                out = _Stream(flush_error=failure, flush_at=1 if arguments == ["--help"] else 2)
                err = _Stream()
                result, exits = self.process(arguments, out, err)
                expected = 130 if isinstance(failure, KeyboardInterrupt) else 1
                self.assertEqual((result, exits), (expected, [expected]))
                suffix = ("interrupted" if arguments == ["--help"] else "interrupted_unconfirmed") if expected == 130 else (
                    "output_failed" if arguments == ["--help"] else "delivery_unconfirmed")
                self.assertTrue(err.getvalue().endswith('{"error":{"code":"' + PREFIX + suffix + '"}}\n'))
        first = self.parent.RfSignalWaveformObservationError("rf_signal_waveform_observation_invalid_argument")
        result, exits = self.process(ARGS, _Stream(flush_error=KeyboardInterrupt()), _Stream(), effect=first)
        self.assertEqual((result, exits), (2, [2]))

    def test_route_is_frozen_and_parent_finally_precedes_forced_exit(self):
        state = {"finally": False}
        def parent(request):
            try:
                sys.argv[:] = ["module", "--help"]
                return unit_wire()
            finally:
                state["finally"] = True
        out, err = _Stream(flush_error=OSError(), flush_at=2), _Stream()
        result, exits = self.process(ARGS, out, err, effect=parent)
        self.assertEqual((result, exits, state["finally"]), (1, [1], True))
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "delivery_unconfirmed")
        self.called.assert_called_once()

    def test_quiet_sink_open_dup_close_and_drain_faults_keep_first_status(self):
        class DescriptorStream(_Stream):
            def fileno(self):
                return 1
        class DrainStream(DescriptorStream):
            def flush(self):
                super().flush()
                if self.flushes >= 3:
                    raise KeyboardInterrupt()
        for boundary in ("open", "dup2", "close", "drain", "none"):
            out = (DrainStream if boundary == "drain" else DescriptorStream)(flush_error=OSError(), flush_at=2)
            err = _Stream()
            with mock.patch.object(cli.os, "open", return_value=777, side_effect=KeyboardInterrupt() if boundary == "open" else None) as opened, \
                    mock.patch.object(cli.os, "dup2", side_effect=SystemExit(0) if boundary == "dup2" else None) as duplicated, \
                    mock.patch.object(cli.os, "close", side_effect=GeneratorExit() if boundary == "close" else None) as closed:
                result, exits = self.process(ARGS, out, err)
            self.assertEqual((result, exits), (1, [] if boundary == "none" else [1]))
            self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "delivery_unconfirmed")
            self.called.assert_called_once()
            self.assertEqual(out.writes, 1)
            opened.assert_called_once_with(os.devnull, os.O_WRONLY)
            if boundary != "open":
                duplicated.assert_called_once_with(777, 1)
                closed.assert_called_once_with(777)

    def test_real_module_help_and_syntax_are_utf8_and_do_not_import_parent(self):
        self.assertTrue(callable(getattr(cli, "_process_main", None)), "module process entry is absent")
        script = """import builtins,sys
original=builtins.__import__
def guarded(name,globals=None,locals=None,fromlist=(),level=0):
 if 'rf_signal_waveform_observation' in (fromlist or ()):raise AssertionError('parent import')
 return original(name,globals,locals,fromlist,level)
builtins.__import__=guarded
from labflow.virtual_fleet import rf_signal_waveform_observation_cli as module
main=module.main
def checked(args):
 assert sys.stdout.encoding.lower().replace('-','')=='utf8' and sys.stderr.errors=='strict'
 return main(args)
module.main=checked
sys.argv=['module','--help']
raise SystemExit(module._process_main())
"""
        env = dict(os.environ, PYTHONIOENCODING="ascii:strict")
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", script], capture_output=True, env=env, timeout=20)
        self.assertEqual((result.returncode, result.stdout), (0, b""), result.stderr)
        self.assertIn(b"Usage:", result.stderr)
        self.assertNotIn(b"\r\n", result.stderr)
        result = subprocess.run([sys.executable, "-B", "-m", NAME, "--help", "bad"], capture_output=True, timeout=20)
        self.assertEqual((result.returncode, result.stdout), (2, b""), result.stderr)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], PREFIX + "invalid_argument")

    def test_real_closed_pipes_preserve_exit_and_fake_parent_finally_witness(self):
        self.assertTrue(callable(getattr(cli, "_process_main", None)), "module process entry is absent")
        root = Path(__file__).resolve().parents[1]
        parent = root / ".local/rf-observation-cli-tests"; parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent); self.addCleanup(temporary.cleanup)
        script = """import json,sys
from pathlib import Path
from tests.test_virtual_fleet_rf_signal_waveform_observation_cli import ARGS,unit_wire
from labflow.virtual_fleet import rf_signal_waveform_observation_cli as cli,rf_signal_waveform_observation as parent
witness,kind=sys.argv[1:]
def record(request):
 try:
  if kind=='KI':raise KeyboardInterrupt()
  if kind=='invalid':raise parent.RfSignalWaveformObservationError('rf_signal_waveform_observation_invalid_argument')
  return unit_wire()
 finally:Path(witness).write_text(json.dumps({'calls':1,'finally':True}),encoding='utf-8')
parent.record_rf_baseband_observation=record
sys.argv=['module']+ARGS
raise SystemExit(cli._process_main())
"""
        for kind, expected in [("normal", 1), ("invalid", 2), ("KI", 130)]:
            for both in (False, True):
                witness = Path(temporary.name) / (kind + str(both) + ".json")
                process = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-c", script, str(witness), kind],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                process.stdout.close()
                if both:
                    process.stderr.close(); error = b""
                else:
                    error = process.stderr.read(); process.stderr.close()
                status = process.wait(timeout=20)
                self.assertEqual(status, expected, error)
                self.assertEqual(json.loads(witness.read_bytes()), {"calls": 1, "finally": True})
                if not both:
                    code = json.loads(error)["error"]["code"]
                    self.assertEqual(code, "rf_signal_waveform_observation_invalid_argument" if kind == "invalid" else PREFIX + (
                        "interrupted_unconfirmed" if kind == "KI" else "delivery_unconfirmed"))


class CLIIntegrationTests(_Support):
    def setUp(self):
        super().setUp()
        from tests import test_virtual_fleet_rf_signal_waveform_observation as observation_tests
        self.saved = observation_tests
        self.case = observation_tests._Support("runTest")
        self.case.setUp(); self.addCleanup(self.case.doCleanups)
        self.base, self.backends, self.closed = self.case.base, [], []
        self.parent = observation_tests.observer
        self.native = observation_tests.native

    def call(self, arguments=ARGS, *, stdout=None, stderr=None):
        saved, native = self.saved, self.native
        actual_backend = native._WindowsIO
        def backend():
            value = actual_backend(); self.backends.append(value)
            close = value.close
            def closing():
                known = tuple(value.held)
                close()
                for descriptor in known:
                    with self.assertRaises(OSError) as closed:
                        os.fstat(descriptor)
                    self.assertEqual(closed.exception.errno, errno.EBADF)
                self.closed.append(len(known))
            value.close = closing
            return value
        before = saved.serialized_fixture.fingerprint(self.case.fixture.folder)
        with ExitStack() as stack:
            for module, relative in [(self.parent, "labflow/virtual_fleet/rf_signal_waveform_observation.py"),
                (saved.reader, "labflow/virtual_fleet/rf_signal_read.py"), (saved.scenario, "labflow/virtual_fleet/rf_signal_scenario.py"),
                (saved.waveform, "labflow/virtual_fleet/rf_signal_waveform.py"), (native, "labflow/control_packet_prepare.py")]:
                stack.enter_context(mock.patch.object(module, "__file__", str(self.base / relative)))
            stack.enter_context(mock.patch.object(native, "_WindowsIO", side_effect=backend))
            self.api = stack.enter_context(mock.patch.object(self.parent, "record_rf_baseband_observation", wraps=self.parent.record_rf_baseband_observation))
            self.parents = [stack.enter_context(mock.patch.object(module, method, wraps=getattr(module, method)))
                for module, method in [(saved.reader, "read_rf_signal_run"), (saved.scenario, "describe_rf_signal_scenario"),
                    (saved.waveform, "generate_rf_baseband_envelope"), (saved.waveform, "analyze_rf_baseband_envelope")]]
            forbidden = [stack.enter_context(mock.patch.object(module, method, side_effect=AssertionError("unexpected RF execution")))
                for module, method in [(saved.scenario, "run_rf_signal_scenario"), (saved.scenario, "evaluate_rf_signal_scenario"),
                    (saved.cli, "main"), (native, "prepare_control_packet")]]
            result = self.invoke(arguments, stdout=stdout, stderr=stderr)
            for method in forbidden:
                method.assert_not_called()
        self.api.assert_called_once()
        self.assertEqual(len(self.closed), len(self.backends))
        self.assertTrue(all(not value.held and not value.directories for value in self.backends))
        self.assertEqual(saved.serialized_fixture.fingerprint(self.case.fixture.folder), before)
        return result

    def normal_counts(self):
        self.assertEqual([method.call_count for method in self.parents], [1, 1, 1, 1])
        self.assertEqual(len(self.backends), 2)

    def test_real_parent_summary_roundtrip_and_source_stays_read_only(self):
        result, out, err = self.call()
        self.assertEqual((result, err.getvalue()), (0, ""))
        self.normal_counts()
        summary = json.loads(out.getvalue())
        self.assertEqual(set(summary), set(unit_wire()))
        self.assertEqual(summary["verification"], unit_wire()["verification"])
        self.assertEqual(out.getvalue(), json.dumps(summary, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n")
        final = self.base / summary["storage"]["path"]
        raw = final.read_bytes()
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (summary["storage"]["bytes"], summary["storage"]["sha256"]))
        self.assertEqual(final.stat().st_ino, final.with_name("observation.pending.json").stat().st_ino)

    def test_retained_CW_raw_copy_is_observed_without_new_RF(self):
        folder = self.base / ".local/rf-signal-runs/retained_cli"
        for relative in ["private-manifest.json", "public-result.json", "operator/events.jsonl", "private/author.json"]:
            target = folder / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((self.case.fixture.folder / relative).read_bytes())
        before = self.saved.serialized_fixture.fingerprint(folder)
        arguments = list(ARGS); arguments[1], arguments[3] = "retained_cli", "retained_cli"
        result, out, err = self.call(arguments)
        self.assertEqual((result, err.getvalue()), (0, ""))
        self.normal_counts()
        self.assertEqual(json.loads(out.getvalue())["source"]["run_name"], "retained_cli")
        self.assertEqual(self.saved.serialized_fixture.fingerprint(folder), before)

    def test_stale_source_pin_rejects_before_parent_read_or_publication(self):
        helper = self.base / "labflow/control_packet_prepare.py"
        helper.write_bytes(helper.read_bytes() + b"\n# stale source cut\n")
        result, out, err = self.call()
        self.assertEqual((result, out.getvalue()), (1, ""))
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], "rf_signal_waveform_observation_dependency_changed")
        self.assertEqual([method.call_count for method in self.parents], [0, 0, 0, 0])
        self.assertEqual(len(self.backends), 1)
        self.assertFalse((self.base / ".local/rf-waveform-observations/observe_cli").exists())

    def test_actual_postlink_failure_is_parent_publication_uncertain(self):
        actual, links = self.native._WindowsIO.link_receipt, []
        def linked(backend, descriptor, path):
            actual(backend, descriptor, path); links.append(path)
            raise OSError("synthetic after actual link")
        with mock.patch.object(self.native._WindowsIO, "link_receipt", linked):
            result, out, err = self.call()
        self.assertEqual((result, out.getvalue(), len(links)), (1, "", 1))
        self.normal_counts()
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], "rf_signal_waveform_observation_publication_uncertain")
        folder = self.base / ".local/rf-waveform-observations/observe_cli"
        self.assertEqual({p.name for p in folder.iterdir()}, {"observation.json", "observation.pending.json", "failure.json"})
        marker = json.loads((folder / "failure.json").read_bytes())
        self.assertEqual((marker["phase"], marker["publication_attempted"]), ("publish", True))

    def test_real_pending_KI_close_cofault_finishes_before_CLI_diagnostic(self):
        native = self.native
        create, sync, close = native._WindowsIO.create_file, os.fsync, os.close
        first = KeyboardInterrupt("synthetic real writer first interrupt")
        state = dict(fd=None, first=False, closed=False)
        def creating(backend, path):
            descriptor = create(backend, path)
            if path.name == "observation.pending.json": state["fd"] = descriptor
            return descriptor
        def syncing(descriptor):
            if descriptor == state["fd"] and not state["first"]:
                state["first"] = True; raise first
            return sync(descriptor)
        def closing(descriptor):
            if descriptor == state["fd"] and not state["closed"]:
                close(descriptor); state["closed"] = True
                raise OSError("synthetic after actual writer close")
            return close(descriptor)
        owner = self
        class Diagnostic(StringIO):
            def write(self, text):
                owner.assertTrue(state["closed"])
                owner.assertTrue(all(not item.held and not item.directories for item in owner.backends))
                return super().write(text)
        with mock.patch.object(native._WindowsIO, "create_file", creating), mock.patch.object(native.os, "fsync", syncing), \
                mock.patch.object(native.os, "close", closing):
            result, out, err = self.call(stderr=Diagnostic())
        self.assertEqual((result, out.getvalue(), state["first"], state["closed"]), (130, "", True, True))
        self.normal_counts()
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "interrupted_unconfirmed")
        with self.assertRaises(OSError) as closed:
            os.fstat(state["fd"])
        self.assertEqual(closed.exception.errno, errno.EBADF)
        folder = self.base / ".local/rf-waveform-observations/observe_cli"
        self.assertFalse((folder / "observation.json").exists())
        marker = json.loads((folder / "failure.json").read_bytes())
        self.assertEqual((marker["phase"], marker["status"], marker["error_code"]), ("write_pending", "interrupted", None))

    def test_delivery_failure_keeps_successful_parent_publication_without_retry(self):
        result, out, err = self.call(stdout=_Stream(flush_error=OSError("synthetic output flush")))
        self.assertEqual(result, 1)
        self.normal_counts()
        self.assertEqual(json.loads(err.getvalue())["error"]["code"], PREFIX + "delivery_unconfirmed")
        summary = json.loads(out.getvalue())
        folder = (self.base / summary["storage"]["path"]).parent
        self.assertEqual({p.name for p in folder.iterdir()}, {"observation.json", "observation.pending.json"})
        self.assertEqual(summary["storage"]["state"], "published")

    def test_genuine045_preparation_and_cli055_observation_counts_are_separate(self):
        saved = self.saved
        profile = self.base / "virtual_profiles/sm_a176u_unlicensed.json"; profile.parent.mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / "virtual_profiles/sm_a176u_unlicensed.json", profile)
        out, err = StringIO(), StringIO()
        with mock.patch.object(saved.cli, "__file__", str(self.base / "labflow/virtual_fleet/rf_signal_cli.py")), \
                mock.patch.object(saved.scenario, "run_rf_signal_scenario", wraps=saved.scenario.run_rf_signal_scenario) as run, \
                mock.patch.object(saved.scenario, "evaluate_rf_signal_scenario", wraps=saved.scenario.evaluate_rf_signal_scenario) as evaluate, \
                mock.patch.object(self.parent, "record_rf_baseband_observation", wraps=self.parent.record_rf_baseband_observation) as observe, \
                mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            status = saved.cli.main(["--scenario", "cw_peak", "--seed", "7", "--run-name", "genuine_cli"])
        self.assertEqual((status, err.getvalue(), run.call_count, evaluate.call_count, observe.call_count), (0, "", 1, 1, 0))
        folder = self.base / ".local/rf-signal-runs/genuine_cli"
        before = saved.serialized_fixture.fingerprint(folder)
        arguments = list(ARGS); arguments[1] = "genuine_cli"
        result, out, err = self.call(arguments)
        self.assertEqual((result, err.getvalue()), (0, ""))
        self.normal_counts()
        self.assertEqual(saved.serialized_fixture.fingerprint(folder), before)


if __name__ == "__main__":
    unittest.main()
