"""055 source binding and real native publication; no hardware or RF control."""
from contextlib import ExitStack
from copy import deepcopy
from decimal import Decimal, localcontext
from io import StringIO
import hashlib
import importlib
import importlib.util
import json
import errno
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

from labflow import control_packet_prepare as native
from labflow.virtual_fleet import rf_signal_read as reader
from labflow.virtual_fleet import rf_signal_scenario as scenario
from labflow.virtual_fleet import rf_signal_waveform as waveform
from labflow.virtual_fleet import rf_signal_cli as cli
from tests import test_virtual_fleet_rf_signal_read as serialized_fixture

NAME = "labflow.virtual_fleet.rf_signal_waveform_observation"
observer = importlib.import_module(NAME) if importlib.util.find_spec(NAME) else None
ROOT = Path(__file__).resolve().parents[1]
PREFIX = "rf_signal_waveform_observation_"
_UNSET = object()
REQUEST = dict(schema_version=1, run_name="run048", observation_name="observe055",
               sample_rate_hz=8, sample_count=1, seed=7)
SUMMARY = set("schema_version kind observation_name storage source math verification "
              "execution_authorized rerun_authorized".split())
BUNDLE = set("schema_version kind request source_snapshot declared_setup recipe packet analysis provenance".split())
FLAGS = dict(data_origin="authored_synthetic", synthetic=True, hardware_verified=False,
             physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
             method_approval="not_assessed", regulatory_scope_complete=False,
             model_scope="normalized_baseband_sample_math_v1")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


class _Support(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(observer, "055 public observation API is absent")
        self.fixture = serialized_fixture.RfSignalReadTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.base = self.fixture.base
        self.fixture.fixture("cw_peak")
        for relative in ("labflow/virtual_fleet/rf_signal_read.py",
                         "labflow/virtual_fleet/rf_signal_scenario.py",
                         "labflow/virtual_fleet/rf_signal_waveform.py"):
            shutil.copyfile(ROOT / relative, self.base / relative)
        self.destination = self.base / ".local/rf-waveform-observations/observe055"
        self.backends = []
        self.source_before = serialized_fixture.fingerprint(self.fixture.folder)

    def invoke(self, request=_UNSET, *, read_effect=None, describe_effect=None,
               generate_effect=None, analyze_effect=None, backend_effect=None):
        original_backend = native._WindowsIO

        def backend():
            value = original_backend()
            self.backends.append(value)
            if backend_effect is not None:
                backend_effect(value, len(self.backends))
            return value

        out, err = StringIO(), StringIO()
        with ExitStack() as stack:
            for module, relative in ((observer, "labflow/virtual_fleet/rf_signal_waveform_observation.py"),
                                     (reader, "labflow/virtual_fleet/rf_signal_read.py"),
                                     (scenario, "labflow/virtual_fleet/rf_signal_scenario.py"),
                                     (waveform, "labflow/virtual_fleet/rf_signal_waveform.py"),
                                     (native, "labflow/control_packet_prepare.py")):
                stack.enter_context(mock.patch.object(module, "__file__", str(self.base / relative)))
            stack.enter_context(mock.patch.object(native, "_WindowsIO", side_effect=backend))
            self.calls = []
            for module, method, effect in (
                (reader, "read_rf_signal_run", read_effect),
                (scenario, "describe_rf_signal_scenario", describe_effect),
                (waveform, "generate_rf_baseband_envelope", generate_effect),
                (waveform, "analyze_rf_baseband_envelope", analyze_effect),
            ):
                wrapped = getattr(module, method)
                call = stack.enter_context(mock.patch.object(module, method, wraps=wrapped) if effect is None
                                           else mock.patch.object(module, method, side_effect=effect))
                self.calls.append(call)
            forbidden = [stack.enter_context(mock.patch.object(module, method, side_effect=AssertionError("execution")))
                         for module, method in ((scenario, "run_rf_signal_scenario"),
                                                (scenario, "evaluate_rf_signal_scenario"), (cli, "main"),
                                                (native, "prepare_control_packet"))]
            stack.enter_context(mock.patch.object(sys, "stdout", out))
            stack.enter_context(mock.patch.object(sys, "stderr", err))
            try:
                return observer.record_rf_baseband_observation(REQUEST if request is _UNSET else request)
            finally:
                self.assertEqual((out.getvalue(), err.getvalue(), out.closed, err.closed), ("", "", False, False))
                for call in forbidden:
                    call.assert_not_called()
                for value in self.backends:
                    self.assertEqual((value.held, value.directories), ([], {}))
                self.assertEqual(serialized_fixture.fingerprint(self.fixture.folder), self.source_before)

    def rejection(self, suffix, request=_UNSET, **kwargs):
        with self.assertRaises(observer.RfSignalWaveformObservationError) as raised:
            self.invoke(request, **kwargs)
        self.assertEqual((raised.exception.code, str(raised.exception)), (PREFIX + suffix, PREFIX + suffix))
        return raised.exception

    def bundle(self, summary):
        raw = (self.base / summary["storage"]["path"]).read_bytes()
        self.assertEqual((len(raw), digest(raw)), (summary["storage"]["bytes"], summary["storage"]["sha256"]))
        value = json.loads(raw)
        self.assertEqual(raw, encoded(value) + b"\n")
        return value


class ObservationContractTests(_Support):
    def test_public_API_and_fixed_error_class(self):
        self.assertTrue(callable(observer.record_rf_baseband_observation))
        for value in ("PRIVATE/source/path", None, False, 8, []):
            error = observer.RfSignalWaveformObservationError(value)
            self.assertEqual((error.code, str(error)), (PREFIX + "write_failed", PREFIX + "write_failed"))

    def test_strict_exact_request_and_names_before_any_parent_or_IO(self):
        class Derived(dict):
            def __iter__(self):
                raise AssertionError("callback")
        class Text(str):
            def __str__(self):
                raise AssertionError("callback")
        bad = [None, False, [], Derived(REQUEST), {**REQUEST, "extra": 1},
               {key: value for key, value in REQUEST.items() if key != "seed"}]
        for key, values in (("schema_version", [True, 0, 2, 1.0]),
                            ("sample_rate_hz", [False, 0, 1_000_000_001, 8.0]),
                            ("sample_count", [False, 0, 4097, 1.0]),
                            ("seed", [False, -1, 2147483648, 7.0]),
                            ("run_name", [None, False, Text("run048")]),
                            ("observation_name", [None, Text("x"), "", "../x", "CON", "aux",
                                                  "LPT9", "x/y", "x ", "한글", "x" * 65])):
            bad.extend({**REQUEST, key: value} for value in values)
        for request in bad:
            with self.subTest(request_type=type(request).__name__):
                self.rejection("invalid_argument", request)
                self.assertEqual(self.backends, [])
                self.assertEqual([call.call_count for call in self.calls], [0, 0, 0, 0])
                self.assertFalse(self.destination.exists())

    def test_explicit_complete_cw_context_recipe_and_original_DTO(self):
        result = self.invoke()
        self.assertEqual(set(result), SUMMARY)
        self.assertEqual(result["kind"], "synthetic_rf_baseband_observation")
        self.assertEqual(result["verification"], FLAGS)
        self.assertIs(result["execution_authorized"], False)
        self.assertIs(result["rerun_authorized"], False)
        self.assertEqual([call.call_count for call in self.calls], [1, 1, 1, 1])
        value = self.bundle(result)
        self.assertEqual(set(value), BUNDLE)
        self.assertEqual(value["request"], REQUEST)
        self.assertEqual(len(value["source_snapshot"]), 14)
        self.assertEqual(value["source_snapshot"]["measurement"]["value"], -18.0)
        self.assertIsNone(value["source_snapshot"]["verification"]["producer_cli_exit_status"])
        self.assertIs(value["source_snapshot"]["verification"]["saved"]["waveform_implemented"], False)
        self.assertEqual(value["recipe"], dict(schema_version=1, signal_kind="cw", sample_rate_hz=8,
                                              sample_count=1, on_power_dbm=12.5, pulse=None))
        self.assertEqual(result["math"]["reference_plane"], "declared_dut_output")
        self.assertEqual(result["math"]["binding_scope"], "declared_source_projection_only")
        self.assertEqual(len(value["declared_setup"]), 5)
        self.assertEqual((len(value["packet"]), len(value["analysis"])), (8, 8))
        self.assertEqual(value["packet"]["grid"], dict(sample_rate_hz=8, sample_count=1, t0_seconds=0,
                                                      interpolation="zero_order_hold"))

    def test_independent_decimal_CW_power_energy_and_zero_origin_window(self):
        value = self.bundle(self.invoke())
        with localcontext() as context:
            context.prec = 80
            power = Decimal(10) ** (Decimal(5) / 4)
            amplitude = power.sqrt()
        self.assertEqual(value["packet"]["samples"][0][0], 0.0)
        self.assertAlmostEqual(value["packet"]["samples"][0][1], -float(amplitude), delta=1e-14)
        metrics = value["analysis"]["metrics"]
        self.assertEqual(metrics["window_seconds"], 1 / 8)
        self.assertAlmostEqual(metrics["time_mean_mw"], float(power), delta=1e-13)
        self.assertAlmostEqual(metrics["peak_mw"], float(power), delta=1e-13)
        self.assertAlmostEqual(metrics["energy_mw_s"], float(power / 8), delta=1e-14)
        self.assertEqual(metrics["observed_on_samples"], 1)

    def test_hash_relationships_fixed_pins_and_private_seed(self):
        result = self.invoke()
        value = self.bundle(result)
        source_sha, packet_sha = digest(encoded(value["source_snapshot"])), digest(encoded(value["packet"]))
        self.assertEqual(value["provenance"]["source_snapshot_sha256"], source_sha)
        self.assertEqual(value["provenance"]["packet_sha256"], packet_sha)
        self.assertEqual(value["analysis"]["input_sha256"], packet_sha)
        self.assertEqual(result["source"]["snapshot_sha256"], source_sha)
        self.assertEqual(result["math"]["packet_sha256"], packet_sha)
        self.assertEqual(result["math"]["analysis_sha256"], digest(encoded(value["analysis"])))
        self.assertEqual(result["math"]["spec_sha256"], digest(encoded(value["recipe"])))
        self.assertEqual(set(value["provenance"]), set("binding_scope reference_plane rf_manifest_sha256 "
                                                     "source_snapshot_sha256 packet_sha256 dependency_pins".split()))
        pins = value["provenance"]["dependency_pins"]
        self.assertEqual([row["role"] for row in pins], ["read048", "describe041", "waveform054", "native_helper"])
        self.assertEqual([row["lf_bytes"] for row in pins], [25927, 44423, 7581, 29100])
        self.assertEqual([row["lf_sha256"] for row in pins], [
            "3999ab598acdc86639d82f2e451295f378ebb3dc827f070c6d670f8cd2a59540",
            "bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae",
            "7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d",
            "8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7"])
        for row in pins:
            self.assertEqual(set(row), {"role", "lf_bytes", "lf_sha256"})
        for public in (result, value["recipe"], value["packet"], value["analysis"]):
            raw = encoded(public)
            for key in (b'"seed"', b'"oracle"', b'"expected"', b'"author"'):
                self.assertNotIn(key, raw)
        self.assertLessEqual(len(encoded(result)), 8192)

    def test_rejected_source_or_seed_never_creates_attempt(self):
        self.rejection("invalid_argument", {**REQUEST, "seed": 8})
        self.assertEqual([call.call_count for call in self.calls], [1, 0, 0, 0])
        self.assertFalse(self.destination.exists())
        for status, outcome in (("incomplete", "incomplete"), ("invalid", "invalid"),
                                ("complete_verified", "failure_recorded")):
            value = reader._base("run048")
            value["storage"]["status"], value["outcome"] = status, outcome
            value["metadata"]["request"] = None
            self.rejection("source_ineligible", read_effect=lambda name: deepcopy(value))
            self.assertEqual([call.call_count for call in self.calls], [1, 0, 0, 0])
            self.assertFalse(self.destination.exists())

    def test_unknown_source_shape_and_status_are_unavailable(self):
        for value in ({}, {"schema_version": 99}, {**reader._base("run048"), "extra": 3}):
            self.rejection("source_unavailable", read_effect=lambda name: deepcopy(value))
        value = reader._base("run048")
        value["storage"]["status"] = "future_status"
        self.rejection("source_unavailable", read_effect=lambda name: value)
        self.assertFalse(self.destination.exists())

    def test_parent_full_code_mapping_and_unknown_code_is_sanitized(self):
        for code, suffix in (("invalid_argument", "invalid_argument"), ("path_invalid", "source_unavailable"),
                             ("not_found", "source_unavailable"), ("input_changed", "dependency_changed"),
                             ("evidence_invalid", "source_unavailable"), ("unavailable", "source_unavailable")):
            self.rejection(suffix, read_effect=reader.RfSignalReadError("rf_signal_read_" + code))
        for code in ("invalid_argument", "budget_exceeded", "numeric_unavailable"):
            self.rejection("math_unavailable", generate_effect=waveform.RfSignalWaveformError("rf_signal_waveform_" + code))
        self.rejection("source_ineligible", describe_effect=scenario.RfSignalScenarioError("rf_signal_scenario_invalid_request"))
        self.rejection("source_unavailable", read_effect=RuntimeError("PRIVATE path"))
        self.assertFalse(self.destination.exists())

    def test_math_failure_and_hash_mismatch_never_create_attempt(self):
        self.rejection("math_unavailable", analyze_effect=RuntimeError("PRIVATE numeric value"))
        self.rejection("math_unavailable", generate_effect=lambda *args, **kwargs: {"unexpected": True})
        original = waveform.analyze_rf_baseband_envelope
        def wrong_hash(packet):
            result = original(packet)
            result["input_sha256"] = "0" * 64
            return result
        self.rejection("math_unavailable", analyze_effect=wrong_hash)
        self.assertFalse(self.destination.exists())


class ObservationStorageTests(_Support):
    def marker(self, phase, suffix, attempted, status="failed"):
        value = json.loads((self.destination / "failure.json").read_bytes())
        self.assertEqual(value, dict(schema_version=1, kind="rf_baseband_observation_failure",
                                     phase=phase, status=status, error_code=PREFIX + suffix if suffix else None,
                                     publication_attempted=attempted))

    def test_exclusive_attempt_and_held_object_atomic_publication(self):
        original = native._WindowsIO.link_receipt
        seen = []
        def linking(backend, descriptor, marker):
            self.assertFalse(marker.exists())
            pending = marker.with_name("observation.pending.json")
            self.assertTrue(pending.is_file())
            self.assertEqual(os.fstat(descriptor).st_ino, pending.stat().st_ino)
            seen.append(pending.read_bytes())
            return original(backend, descriptor, marker)
        with mock.patch.object(native._WindowsIO, "link_receipt", linking):
            result = self.invoke()
        raw = (self.destination / "observation.json").read_bytes()
        self.assertEqual(seen, [raw])
        self.assertEqual((self.destination / "observation.json").stat().st_ino,
                         (self.destination / "observation.pending.json").stat().st_ino)
        self.assertEqual(self.bundle(result)["kind"], "private_rf_baseband_math_observation")
        before = serialized_fixture.fingerprint(self.destination)
        self.rejection("destination_exists")
        self.assertEqual(serialized_fixture.fingerprint(self.destination), before)

    def test_existing_partial_leaf_is_never_adopted_or_modified(self):
        self.destination.mkdir(parents=True)
        (self.destination / "partial").write_bytes(b"keep")
        before = serialized_fixture.fingerprint(self.destination)
        self.rejection("destination_exists")
        self.assertEqual(serialized_fixture.fingerprint(self.destination), before)

    def test_fault_prefixes_preserved_and_post_link_is_uncertain(self):
        original = native._write_bytes
        def partial(tree, path, raw, code, *, sync=False):
            if path.name == "observation.pending.json":
                original(tree, path, raw[:19], code, sync=sync)
                raise OSError("PRIVATE write")
            return original(tree, path, raw, code, sync=sync)
        with mock.patch.object(native, "_write_bytes", partial):
            self.rejection("write_failed")
        self.assertEqual((self.destination / "observation.pending.json").stat().st_size, 19)
        self.assertFalse((self.destination / "observation.json").exists())
        self.marker("write_pending", "write_failed", False)

    def test_fsync_failure_preserves_pending_and_first_error_when_marker_fails(self):
        with mock.patch.object(native.os, "fsync", side_effect=OSError("PRIVATE flush")):
            self.rejection("write_failed")
        self.assertTrue((self.destination / "observation.pending.json").exists())
        self.assertFalse((self.destination / "observation.json").exists())
        self.assertFalse((self.destination / "failure.json").exists()
                         and (self.destination / "failure.json").stat().st_size == 0)

    def test_link_error_before_or_after_real_publication_is_always_uncertain(self):
        original = native._WindowsIO.link_receipt
        seen = []
        def after(backend, descriptor, marker):
            original(backend, descriptor, marker)
            seen.append(marker)
            raise OSError("PRIVATE after link")
        with mock.patch.object(native._WindowsIO, "link_receipt", after):
            self.rejection("publication_uncertain")
        self.assertEqual(len(seen), 1)
        self.assertEqual((self.destination / "observation.json").read_bytes(),
                         (self.destination / "observation.pending.json").read_bytes())
        self.marker("publish", "publication_uncertain", True)

    def test_prelink_error_has_no_final_and_only_one_attempt(self):
        with mock.patch.object(native._WindowsIO, "link_receipt", side_effect=OSError("PRIVATE before")) as link:
            self.rejection("publication_uncertain")
        self.assertEqual(link.call_count, 1)
        self.assertFalse((self.destination / "observation.json").exists())
        self.marker("publish", "publication_uncertain", True)

    def test_KeyboardInterrupt_is_preserved_with_interrupted_marker_and_handles_closed(self):
        original = native._write_bytes
        def interrupted(tree, path, raw, code, *, sync=False):
            if path.name == "observation.pending.json":
                raise KeyboardInterrupt()
            return original(tree, path, raw, code, sync=sync)
        with mock.patch.object(native, "_write_bytes", interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke()
        self.marker("write_pending", None, False, "interrupted")

    def test_unsupported_native_and_changed_dependency_are_closed_before_source(self):
        (self.base / "labflow/virtual_fleet/rf_signal_waveform.py").write_bytes(b"changed\n")
        self.rejection("dependency_changed")
        self.assertEqual([call.call_count for call in self.calls], [0, 0, 0, 0])
        self.assertFalse(self.destination.exists())

    def test_cleanup_interruption_before_real_close_closes_known_handles(self):
        def inject(backend, number):
            if number == 1:
                def interrupted():
                    backend.held.pop()
                    raise KeyboardInterrupt()
                backend.close = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.invoke(backend_effect=inject)

    def test_post_source_pin_change_cannot_publish(self):
        original_read = native._read_descriptor
        original_generate = waveform.generate_rf_baseband_envelope
        changed = [False]
        def generate(*args, **kwargs):
            result = original_generate(*args, **kwargs)
            changed[0] = True
            return result
        def read(descriptor, limit, code):
            raw = original_read(descriptor, limit, code)
            return raw + b"#changed" if changed[0] and code == "packet_prepare_source_changed" else raw
        with mock.patch.object(native, "_read_descriptor", read):
            self.rejection("dependency_changed", generate_effect=generate)
        self.assertFalse((self.destination / "observation.json").exists())
        self.marker("verify_pending", "dependency_changed", False)

    def test_pending_readback_failure_is_write_failed(self):
        original = native._read_descriptor
        def read(descriptor, limit, code):
            raw = original(descriptor, limit, code)
            return b"wrong" if code == "packet_prepare_receipt_failed" else raw
        with mock.patch.object(native, "_read_descriptor", read):
            self.rejection("write_failed")
        self.marker("verify_pending", "write_failed", False)
        self.assertFalse((self.destination / "observation.json").exists())

    def test_final_readback_failure_is_publication_uncertain(self):
        original = native._read_descriptor
        receipt_reads = [0]
        def read(descriptor, limit, code):
            raw = original(descriptor, limit, code)
            if code == "packet_prepare_receipt_failed":
                receipt_reads[0] += 1
                if receipt_reads[0] == 2:
                    return b"wrong"
            return raw
        with mock.patch.object(native, "_read_descriptor", read):
            self.rejection("publication_uncertain")
        self.marker("verify_published", "publication_uncertain", True)
        self.assertTrue((self.destination / "observation.json").is_file())

    def test_final_collision_during_single_link_does_not_overwrite(self):
        original = native._WindowsIO.link_receipt
        seen = []
        def race(backend, descriptor, marker):
            marker.write_bytes(b"other writer\n")
            seen.append(marker)
            return original(backend, descriptor, marker)
        with mock.patch.object(native._WindowsIO, "link_receipt", race):
            self.rejection("publication_uncertain")
        self.assertEqual(len(seen), 1)
        self.assertEqual((self.destination / "observation.json").read_bytes(), b"other writer\n")
        self.marker("publish", "publication_uncertain", True)

    def test_zero_write_preserves_raw_prefix_without_hanging_or_retry(self):
        with mock.patch.object(native.os, "write", return_value=0):
            self.rejection("write_failed")
        self.assertEqual((self.destination / "observation.pending.json").read_bytes(), b"")
        self.assertFalse((self.destination / "observation.json").exists())

    def test_post_publication_close_error_has_no_success_summary(self):
        def inject(backend, number):
            if number == 1:
                original = backend.close
                def closing():
                    original()
                    raise OSError("PRIVATE cleanup")
                backend.close = closing
        self.rejection("publication_uncertain", backend_effect=inject)
        self.assertTrue((self.destination / "observation.json").exists())

    def test_KI_after_real_link_keeps_both_links_and_first_interrupt(self):
        original = native._WindowsIO.link_receipt
        def interrupt(backend, descriptor, marker):
            original(backend, descriptor, marker)
            raise KeyboardInterrupt()
        with mock.patch.object(native._WindowsIO, "link_receipt", interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke()
        self.marker("publish", None, True, "interrupted")
        self.assertEqual((self.destination / "observation.json").read_bytes(),
                         (self.destination / "observation.pending.json").read_bytes())

    def test_marker_and_cleanup_KI_do_not_replace_first_write_error(self):
        def inject(backend, number):
            if number == 1:
                def closing():
                    raise KeyboardInterrupt()
                backend.close = closing
        with mock.patch.object(native, "_write_bytes", side_effect=OSError("PRIVATE first")):
            self.rejection("write_failed", backend_effect=inject)

    def test_native_unavailable_never_calls_source_or_creates_attempt(self):
        with mock.patch.object(native, "_WINDOWS_BACKEND_AVAILABLE", False):
            self.rejection("source_unavailable")
        self.assertEqual([call.call_count for call in self.calls], [0, 0, 0, 0])
        self.assertFalse(self.destination.exists())


class ObservationBoundaryTests(_Support):
    def test_unknown_analysis_kind_and_metric_shape_are_rejected(self):
        original = waveform.analyze_rf_baseband_envelope
        for number, edit in enumerate((
            lambda value: value.update(kind="future_analysis"),
            lambda value: value.update(schema_version=True),
            lambda value: value["metrics"].update(extra=1),
            lambda value: value["verification"].update(hardware_verified=0),
        )):
            def malformed(packet):
                value = original(packet)
                edit(value)
                return value
            self.rejection("math_unavailable", {**REQUEST, "observation_name": "bad" + str(number)},
                           analyze_effect=malformed)
        self.assertFalse(self.destination.parent.exists())

    def test_parent_errors_are_mapped_only_at_the_expected_call_site(self):
        self.rejection("math_unavailable", generate_effect=reader.RfSignalReadError("rf_signal_read_invalid_argument"))
        self.rejection("source_unavailable", read_effect=scenario.RfSignalScenarioError("rf_signal_scenario_invalid_request"))

    def test_malformed_declaration_nested_types_are_unavailable(self):
        original = scenario.describe_rf_signal_scenario("cw_peak")
        for key, value in (("calibration_valid", 1), ("acquisition_policy", [])):
            declared = deepcopy(original)
            declared["sensor"][key] = value
            self.rejection("source_unavailable", describe_effect=lambda sid: declared)
        self.assertFalse(self.destination.exists())

    def test_wrong_CW_duty_or_crest_is_ineligible(self):
        for key, value in (("modulation", "OFDM"), ("duty_cycle", 0.25), ("crest_factor_db", 3.0)):
            declared = scenario.describe_rf_signal_scenario("cw_peak")
            declared["source_signal"][key] = value
            self.rejection("source_ineligible", describe_effect=lambda sid: declared)
        self.assertFalse(self.destination.exists())

    def test_unknown_nested_source_shape_is_unavailable(self):
        original = reader.read_rf_signal_run
        def malformed(name):
            value = original(name)
            value["metadata"]["request"]["scenario_id"] = []
            return value
        self.rejection("source_unavailable", read_effect=malformed)

    def test_output_budgets_and_hostile_subclasses_fail_before_leaf(self):
        original = waveform.generate_rf_baseband_envelope
        def oversized(*args, **kwargs):
            value = original(*args, **kwargs)
            value["samples"] = [[0.0, 0.0]] * 40000
            return value
        self.rejection("math_unavailable", generate_effect=oversized)
        class Hostile(dict):
            def items(self):
                raise AssertionError("callback")
        self.rejection("source_unavailable", read_effect=lambda name: Hostile())
        self.assertFalse(self.destination.exists())

    def test_CRLF_source_normalization_preserves_exact_fixed_pins(self):
        path = self.base / "labflow/virtual_fleet/rf_signal_waveform.py"
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        value = self.bundle(self.invoke())
        self.assertEqual(value["provenance"]["dependency_pins"][2]["lf_sha256"],
                         "7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d")

    def test_maximum_grid_and_different_names_reproduce_math_hashes(self):
        request = {**REQUEST, "sample_rate_hz": 1_000_000_000, "sample_count": 4096}
        first = self.invoke(request)
        second = self.invoke({**request, "observation_name": "other055"})
        self.assertEqual(first["math"], second["math"])
        self.assertNotEqual(first["storage"]["sha256"], second["storage"]["sha256"])
        self.assertEqual(len(self.bundle(first)["packet"]["samples"]), 4096)

    def test_dependency_read_pin_prevents_actual_source_overwrite(self):
        original = waveform.generate_rf_baseband_envelope
        denied = []
        def generate(*args, **kwargs):
            try:
                (self.base / "labflow/virtual_fleet/rf_signal_waveform.py").write_bytes(b"tamper")
            except PermissionError:
                denied.append(True)
            return original(*args, **kwargs)
        self.invoke(generate_effect=generate)
        self.assertEqual(denied, [True])

    def test_unknown_nonplain_and_subclass_parent_codes_use_fixed_fallback(self):
        class Text(str):
            def __hash__(self):
                raise AssertionError("callback")
        class Derived(reader.RfSignalReadError):
            pass
        for code in ("rf_signal_read_future", [], Text("rf_signal_read_invalid_argument")):
            error = reader.RfSignalReadError("rf_signal_read_unavailable")
            error.code = code
            self.rejection("source_unavailable", read_effect=error)
        self.rejection("source_unavailable", read_effect=Derived("rf_signal_read_invalid_argument"))
        for suffix in ("unsupported_catalog", "output_unavailable", "execution_incomplete",
                       "evidence_invalid", "evidence_unavailable"):
            self.rejection("source_unavailable", describe_effect=scenario.RfSignalScenarioError(
                "rf_signal_scenario_" + suffix))

    def test_native_exact_seven_codes_are_context_mapped_without_passthrough(self):
        for suffix in ("invalid_argument", "path_invalid", "destination_exists", "verification_failed",
                       "copy_failed", "source_changed", "receipt_failed"):
            with mock.patch.object(native, "_read_descriptor",
                                   side_effect=native.ControlPacketPrepareError("packet_prepare_" + suffix)):
                self.rejection("dependency_changed")
        self.assertFalse(self.destination.exists())

    def test_every_known_native_descriptor_is_really_closed(self):
        descriptors = set()
        def track(backend, number):
            for name in ("directory", "open_read", "create_file"):
                original = getattr(backend, name)
                def wrapped(*args, _original=original, **kwargs):
                    descriptor = _original(*args, **kwargs)
                    descriptors.add(descriptor)
                    return descriptor
                setattr(backend, name, wrapped)
        self.invoke(backend_effect=track)
        self.assertGreater(len(descriptors), 10)
        for descriptor in descriptors:
            with self.assertRaises(OSError):
                os.fstat(descriptor)

    def test_historical_fail_stays_context_without_changing_old_verdict(self):
        original = reader.read_rf_signal_run
        def historical(name):
            value = original(name)
            value["historical_assessment"]["verdict"] = "fail"
            value["historical_assessment"]["summary_code"] = "scenario_expectation_mismatch"
            value["measurement_goal_succeeded"] = False
            value["outcome"] = "assessment_failed"
            return value
        value = self.bundle(self.invoke(read_effect=historical))
        self.assertEqual(value["source_snapshot"]["historical_assessment"]["verdict"], "fail")
        self.assertIs(value["source_snapshot"]["measurement_goal_succeeded"], False)
        self.assertEqual(value["source_snapshot"]["measurement"]["value"], -18.0)

    def test_oversized_source_is_rejected_before_serializing_the_whole_object(self):
        value = reader._base("run048")
        value["historical_assessment"] = {"a": "x" * 4096, "b": "x" * 4096}
        original = observer._canonical
        serialized = []
        def canonical(item):
            if type(item) is dict and item.get("kind") == "virtual_rf_signal_run_read":
                serialized.append(True)
            return original(item)
        with mock.patch.object(observer, "_canonical", canonical):
            self.rejection("source_unavailable", read_effect=lambda name: value)
        self.assertEqual(serialized, [])
        self.assertFalse(self.destination.exists())

    def test_UTF8_JSON_escape_budget_matches_independent_wire_size(self):
        for value in ({"text": "plain"}, {"text": "한글🙂"}, {"text": "\n\t\b\f\r\"\\"},
                      [None, True, False, -123, 1.25, -0.0], {"x": []}):
            raw = encoded(value)
            self.assertEqual(observer._snapshot(value, len(raw), "math_unavailable"), value)
            with self.assertRaises(observer.RfSignalWaveformObservationError):
                observer._snapshot(value, len(raw) - 1, "math_unavailable")

    def test_unknown_nested_assessment_ids_and_declared_policy_fail_closed(self):
        original = reader.read_rf_signal_run
        edits = (
            lambda value: value["historical_assessment"].update(verdict="future_verdict"),
            lambda value: value["historical_assessment"].update(evidence_refs=False),
            lambda value: value["historical_assessment"].update(status="pending"),
            lambda value: value["metadata"].update(runtime_instance_id=value["metadata"]["run_id"]),
        )
        for number, edit in enumerate(edits):
            with self.subTest(number=number):
                def malformed(name):
                    value = original(name)
                    edit(value)
                    return value
                self.rejection("source_unavailable", {**REQUEST, "observation_name": "unknown" + str(number)},
                               read_effect=malformed)
        declared = scenario.describe_rf_signal_scenario("cw_peak")
        declared["sensor"]["acquisition_policy"] = "future_policy"
        self.rejection("source_unavailable", describe_effect=lambda sid: declared)


class ObservationIntegrationTests(_Support):
    def test_genuine_045_preparation_and_separate_055_call(self):
        profile = self.base / "virtual_profiles/sm_a176u_unlicensed.json"
        profile.parent.mkdir()
        shutil.copyfile(ROOT / "virtual_profiles/sm_a176u_unlicensed.json", profile)
        out, err = StringIO(), StringIO()
        with mock.patch.object(cli, "__file__", str(self.base / "labflow/virtual_fleet/rf_signal_cli.py")), \
                mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            status = cli.main(["--scenario", "cw_peak", "--seed", "7", "--run-name", "genuine055"])
        self.assertEqual((status, err.getvalue()), (0, ""))
        folder = self.base / ".local/rf-signal-runs/genuine055"
        before = serialized_fixture.fingerprint(folder)
        result = self.invoke({**REQUEST, "run_name": "genuine055"})
        self.assertEqual([call.call_count for call in self.calls], [1, 1, 1, 1])
        self.assertEqual(serialized_fixture.fingerprint(folder), before)
        value = self.bundle(result)
        self.assertEqual(value["source_snapshot"]["measurement"]["value"], -18.0)
        self.assertIsNone(value["source_snapshot"]["verification"]["producer_cli_exit_status"])

    def test_retained_serialized_CW_copy_is_read_only_without_new_RF(self):
        # Self-contained serialized fixture; original owner evidence is a
        # separately counted private acceptance phase, never a test prerequisite.
        folder = self.base / ".local/rf-signal-runs/retained055"
        for name in ("private-manifest.json", "public-result.json", "operator/events.jsonl", "private/author.json"):
            source = self.fixture.folder / name
            relative = Path(name)
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = source.read_bytes()
            self.assertEqual(digest(raw), self.source_before[name][0])
            target.write_bytes(raw)
        before = serialized_fixture.fingerprint(folder)
        result = self.invoke({**REQUEST, "run_name": "retained055"})
        self.assertEqual(serialized_fixture.fingerprint(folder), before)
        self.assertEqual(self.bundle(result)["source_snapshot"]["storage"]["status"], "complete_verified")


class ObservationWriterOutcomeTests(_Support):
    def generator_fault(self, boundary, first, cofault):
        """Fault real pre/post-yield validation, then actually close its fd."""
        real_create, real_fstat = native._WindowsIO.create_file, native.os.fstat
        real_stat, real_close = native._Tree.file_stat, native.os.close
        state = dict(fd=None, fstat=0, file_stat=0, close=0)
        self.probes = getattr(self, "probes", [])
        name = "edge055_" + str(len(self.probes))

        def create(backend, path):
            descriptor = real_create(backend, path)
            if path.name == "observation.pending.json":
                state["fd"] = descriptor
            return descriptor

        def fstat(descriptor):
            result = real_fstat(descriptor)
            if descriptor == state["fd"] and state["close"] == 0:
                state["fstat"] += 1
                if (boundary == "pre_yield_fstat" and state["fstat"] == 1
                        or boundary == "post_yield_fstat" and state["fstat"] == 3):
                    raise first
            return result

        def file_stat(tree, path):
            result = real_stat(tree, path)
            if path.name == "observation.pending.json":
                state["file_stat"] += 1
                if (boundary == "pre_yield_file_stat" and state["file_stat"] == 1
                        or boundary == "post_yield_file_stat" and state["file_stat"] == 2):
                    raise first
            return result

        def close(descriptor):
            if descriptor == state["fd"] and state["close"] == 0:
                real_close(descriptor)
                state["close"] = 1
                if cofault:
                    raise OSError(errno.EIO, "synthetic error after actual generator close")
                return
            return real_close(descriptor)

        caught, result = None, None
        with mock.patch.object(native._WindowsIO, "create_file", create), \
                mock.patch.object(native.os, "fstat", fstat), mock.patch.object(native._Tree, "file_stat", file_stat), \
                mock.patch.object(native.os, "close", close):
            try:
                result = self.invoke({**REQUEST, "observation_name": name})
            except BaseException as error:
                caught = error
        folder = self.base / ".local/rf-waveform-observations" / name
        marker = json.loads((folder / "failure.json").read_bytes())
        self.assertIsNone(result)
        self.assertFalse((folder / "observation.json").exists())
        self.assertTrue((folder / "observation.pending.json").is_file())
        self.assertEqual([call.call_count for call in self.calls], [1, 1, 1, 1])
        self.assertEqual(len(self.backends), 2 * (len(self.probes) + 1))
        self.assertEqual(state["close"], 1)
        with self.assertRaises(OSError) as closed:
            real_fstat(state["fd"])
        self.assertEqual(closed.exception.errno, errno.EBADF)
        interrupted = isinstance(first, KeyboardInterrupt)
        self.probes.append(dict(kind="055_actual_native_generator", boundary=boundary, cofault=cofault,
            primary=type(first).__name__, same_primary=caught is first, writer_EBADF=True,
            backend2_per_call=True, parent4_each1=True, summary0_final0_pending_preserved=True))
        if interrupted:
            self.assertIs(caught, first)
        else:
            self.assertIs(type(caught), observer.RfSignalWaveformObservationError)
            self.assertEqual(caught.code, PREFIX + "write_failed")
        self.assertEqual(marker, dict(schema_version=1, kind="rf_baseband_observation_failure",
            phase="write_pending", status="interrupted" if interrupted else "failed",
            error_code=None if interrupted else PREFIX + "write_failed", publication_attempted=False))

    def generator_matrix(self, boundary):
        for kind in (KeyboardInterrupt, OSError):
            for cofault in (False, True):
                with self.subTest(boundary=boundary, primary=kind.__name__, cofault=cofault):
                    self.generator_fault(boundary, kind("synthetic real generator first exception"), cofault)

    def test_native_pre_yield_fstat_keeps_first_outcome_after_close(self):
        self.generator_matrix("pre_yield_fstat")

    def test_native_pre_yield_path_stat_keeps_first_outcome_after_close(self):
        self.generator_matrix("pre_yield_file_stat")

    def test_native_post_yield_fstat_keeps_first_outcome_after_close(self):
        self.generator_matrix("post_yield_fstat")

    def test_native_post_yield_path_stat_keeps_first_outcome_after_close(self):
        self.generator_matrix("post_yield_file_stat")

    def writer_fault(self, first, *, close_error=True, name="observe055", forge_context=False,
                     marker_error=False, cleanup_error=False):
        """Use the real pinned writer; only its actual fsync/close calls fault."""
        real_sync, real_close = native.os.fsync, native.os.close
        secondary = OSError(errno.EIO, "synthetic secondary writer close")
        forged = KeyboardInterrupt("synthetic unraised interrupt")
        state = dict(fd=None, sync=0, close=0)

        def sync(descriptor):
            if not state["sync"]:
                state["fd"], state["sync"] = descriptor, 1
                raise first
            if marker_error:
                raise OSError("synthetic marker flush")
            return real_sync(descriptor)

        def close(descriptor):
            if close_error and descriptor == state["fd"] and not state["close"]:
                state["close"] = 1
                real_close(descriptor)
                if forge_context:
                    forged.__traceback__ = first.__traceback__
                    try:
                        raise secondary
                    except OSError:
                        secondary.__context__ = forged
                        raise
                raise secondary
            return real_close(descriptor)

        def backend_effect(backend, number):
            if cleanup_error and number == 1:
                original = backend.close
                def closing():
                    original()
                    raise OSError("synthetic secondary backend cleanup")
                backend.close = closing

        caught, value = None, None
        with mock.patch.object(native.os, "fsync", sync), mock.patch.object(native.os, "close", close):
            try:
                value = self.invoke({**REQUEST, "observation_name": name}, backend_effect=backend_effect)
            except BaseException as error:
                caught = error
        self.assertIsNone(value)
        self.assertEqual([call.call_count for call in self.calls], [1, 1, 1, 1])
        folder = self.base / ".local/rf-waveform-observations" / name
        self.assertFalse((folder / "observation.json").exists())
        self.assertTrue((folder / "observation.pending.json").is_file())
        with self.assertRaises(OSError) as closed:
            os.fstat(state["fd"])
        self.assertEqual(closed.exception.errno, errno.EBADF)
        self.assertEqual((state["sync"], state["close"]), (1, int(close_error)))
        return caught, folder, secondary, forged

    def test_single_native_fsync_KI_keeps_the_same_interrupt_and_marker(self):
        first = KeyboardInterrupt("synthetic first interrupt")
        caught, folder, secondary, forged = self.writer_fault(first, close_error=False)
        self.assertIs(caught, first)
        ObservationStorageTests.marker(self, "write_pending", None, False, "interrupted")

    def test_native_fsync_KI_then_actual_writer_close_error_keeps_first_identity(self):
        first = KeyboardInterrupt("synthetic first interrupt")
        caught, folder, secondary, forged = self.writer_fault(first)
        self.assertIs(caught, first)
        ObservationStorageTests.marker(self, "write_pending", None, False, "interrupted")

    def test_recovered_first_KI_survives_marker_and_backend_cleanup_errors(self):
        first = KeyboardInterrupt("synthetic first interrupt")
        caught, folder, secondary, forged = self.writer_fault(first, marker_error=True, cleanup_error=True)
        self.assertIs(caught, first)
        value = json.loads((folder / "failure.json").read_bytes())
        self.assertEqual((value["status"], value["error_code"]), ("interrupted", None))

    def test_first_ordinary_writer_error_with_secondary_close_error_stays_failed(self):
        first = OSError(errno.EIO, "synthetic first ordinary failure")
        caught, folder, secondary, forged = self.writer_fault(first)
        self.assertIs(type(caught), observer.RfSignalWaveformObservationError)
        self.assertEqual(caught.code, PREFIX + "write_failed")
        ObservationStorageTests.marker(self, "write_pending", "write_failed", False)

    def test_forged_KI_context_even_with_current_native_traceback_is_not_first(self):
        first = OSError(errno.EIO, "synthetic actual first ordinary failure")
        caught, folder, secondary, forged = self.writer_fault(first, forge_context=True)
        self.assertIs(type(caught), observer.RfSignalWaveformObservationError)
        self.assertEqual(caught.code, PREFIX + "write_failed")
        ObservationStorageTests.marker(self, "write_pending", "write_failed", False)

    def test_unraised_KI_context_on_replacement_writer_is_not_promoted(self):
        forged = KeyboardInterrupt("synthetic never raised")
        original = native._write_bytes
        def replaced(tree, path, raw, code, *, sync=False):
            if path.name == "observation.pending.json":
                error = OSError("synthetic replacement writer")
                error.__context__ = forged
                raise error
            return original(tree, path, raw, code, sync=sync)
        with mock.patch.object(native, "_write_bytes", replaced):
            self.rejection("write_failed")
        ObservationStorageTests.marker(self, "write_pending", "write_failed", False)

    def test_stale_real_native_KI_traceback_from_other_invocation_is_not_promoted(self):
        first = KeyboardInterrupt("synthetic prior invocation")
        caught, folder, secondary, forged = self.writer_fault(first, close_error=False, name="prior055")
        self.assertIs(caught, first)
        original = native._write_bytes
        def replaced(tree, path, raw, code, *, sync=False):
            if path.name == "observation.pending.json":
                error = OSError("synthetic current ordinary failure")
                error.__context__ = first
                raise error
            return original(tree, path, raw, code, sync=sync)
        with mock.patch.object(native, "_write_bytes", replaced):
            self.rejection("write_failed")
        ObservationStorageTests.marker(self, "write_pending", "write_failed", False)

    def test_post_link_error_with_KI_context_remains_publication_uncertain(self):
        original = native._WindowsIO.link_receipt
        def linked(backend, descriptor, marker):
            original(backend, descriptor, marker)
            error = OSError("synthetic after link")
            error.__context__ = KeyboardInterrupt("synthetic never raised")
            raise error
        with mock.patch.object(native._WindowsIO, "link_receipt", linked):
            self.rejection("publication_uncertain")
        ObservationStorageTests.marker(self, "publish", "publication_uncertain", True)
