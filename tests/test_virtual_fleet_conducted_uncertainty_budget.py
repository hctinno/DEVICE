"""Explicit supplied standard components: independent arithmetic, holds and purity."""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import builtins
import io
import importlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from labflow.virtual_fleet import conducted_twin_comparison as comparison
from labflow.virtual_fleet import conducted_twin_result as result_api

MODULE = "labflow.virtual_fleet.conducted_uncertainty_budget"
KEYS = set("schema_version kind status bindings scope budget trace reasons conformity verification".split())


class UncertaintySmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), "uncertainty budget module is absent")


class ConductedUncertaintyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = importlib.import_module(MODULE)
        spec = importlib.util.spec_from_file_location(
            "uncertainty_result_fixture", Path(__file__).with_name("test_virtual_fleet_conducted_twin_result.py"))
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        case = fixture.ConductedTwinResultTests()
        cls.addClassCleanup(case.doCleanups)
        args, ref = case.genuine(power=-7)
        cls.genuine = result_api.build_conducted_twin_result(*args, measurement_ref=ref)
        if cls.genuine["status"] != "recorded":
            raise AssertionError("new genuine synthetic result fixture did not record")

    def setUp(self):
        self.result = deepcopy(self.genuine)
        self.components = [self.component("u1", .3), self.component("u2", .4)]
        self.policy = dict(policy_id="authored-policy", policy_version=1, coverage_factor=2,
            coverage_factor_evidence_refs=["authored:explicit-k"], correlation_assumption="uncorrelated",
            correlation_evidence_refs=["authored:assumption-only"])

    def component(self, identity, value):
        plan = self.result["binding"]["plan_input"]["plan"]
        return dict(component_id=identity, standard_uncertainty_db=value, unit="dB",
            method={key: plan[key] for key in ("method_id", "method_version")}, metric="on",
            quantity="on_average", reference_plane="source_output", evidence_refs=["authored:synthetic-u"])

    def call(self):
        return self.api.build_conducted_uncertainty_budget(
            self.result, components=self.components, policy=self.policy)

    def held(self, code=None):
        value = self.call()
        self.assertEqual(value["status"], "not_assessed")
        self.assertEqual(value["budget"], dict(combined_standard_uncertainty_db=None, expanded_uncertainty_db=None))
        self.assertEqual(value["trace"]["terms"], [])
        for key in ("sum_of_squares_rational_db2", "coverage_factor_rational",
                    "combined_standard_uncertainty_decimal_db", "expanded_uncertainty_decimal_db"):
            self.assertIsNone(value["trace"][key])
        self.assertTrue(value["reasons"])
        if code is not None:
            self.assertIn(code, [reason["code"] for reason in value["reasons"]])
        self.assertIsNone(value["conformity"]["verdict"])
        return value

    def test_known_pair_exact_trace_and_no_authority(self):
        value = self.call()
        self.assertEqual(set(value), KEYS)
        self.assertEqual((value["kind"], value["status"]), ("conducted_uncertainty_budget", "calculated"))
        self.assertEqual(value["budget"], dict(combined_standard_uncertainty_db=.5, expanded_uncertainty_db=1.0))
        self.assertEqual(value["trace"]["sum_of_squares_rational_db2"], "1/4")
        self.assertEqual(value["trace"]["coverage_factor_rational"], "2")
        self.assertEqual(value["trace"]["terms"], [
            dict(component_id="u1", standard_uncertainty_rational_db="3/10", variance_rational_db2="9/100"),
            dict(component_id="u2", standard_uncertainty_rational_db="2/5", variance_rational_db2="4/25")])
        self.assertEqual(value["trace"]["provided_components"], self.components)
        self.assertEqual(value["trace"]["provided_policy"], self.policy)
        self.assertEqual(value["conformity"], dict(status="not_assessed", verdict=None))
        flags = value["verification"]
        self.assertIs(flags["mathematical_combination_only"], True)
        for key in ("physical_verified", "hardware_verified", "components_complete", "correlation_verified",
                    "evidence_authenticity_verified", "applied_to_result", "execution_authority"):
            self.assertIs(flags[key], False)
        self.assertEqual((flags["method_approval"], flags["source_bytes"]), ("not_assessed", "not_reopened"))

    def test_fourteen_independent_fraction_decimal_numeric_cases(self):
        cases = (([3, 4], 2), ([.3, .4], 1.5), ([.1], 2), ([1, 1], 2),
                 ([1] * 16, 2), ([0] * 16, 1e308), ([5e-324], 1),
                 ([1e-300, 1e-300], 1.1), ([1e300, 1e300], 1.1),
                 ([1e300, 1e-300], 1), ([1.7976931348623157e308], 1),
                 ([.01, .02, .03, .04], .125), ([2, 3, 6], .5), ([-0.0, .25], 4))
        for inputs, k in cases:
            with self.subTest(inputs=inputs, k=k):
                self.components = [self.component("u" + str(i), u) for i, u in enumerate(inputs)]
                self.policy["coverage_factor"] = k
                value = self.call()
                self.assertEqual(value["status"], "calculated")
                q = sum((Fraction(Decimal(str(u))) ** 2 for u in inputs), Fraction())
                self.assertEqual(Fraction(value["trace"]["sum_of_squares_rational_db2"]), q)
                with localcontext() as context:
                    context.prec = 2000
                    squares = sum((Decimal(str(u)) ** 2 for u in inputs), Decimal(0))
                    standard = squares.sqrt()
                    expanded = Decimal(str(k)) * standard
                    for key, expected in (("combined_standard_uncertainty", standard), ("expanded_uncertainty", expanded)):
                        actual = Decimal(value["trace"][key + "_decimal_db"])
                        error = abs(actual - expected)
                        self.assertLessEqual(error, abs(expected) * Decimal("1e-78") if expected else Decimal(0))
                        self.assertEqual(value["budget"][key + "_db"], float(expected))

    def test_input_and_returned_trace_do_not_alias_or_rewrite_result(self):
        before = deepcopy((self.result, self.components, self.policy))
        value = self.call()
        self.assertEqual((self.result, self.components, self.policy), before)
        value["trace"]["provided_components"][0]["standard_uncertainty_db"] = 99
        value["trace"]["provided_policy"]["coverage_factor"] = 99
        self.assertEqual((self.result, self.components, self.policy), before)
        self.assertIsNone(self.result["calculation"]["conformity"]["uncertainty_db"])

    def test_pure_c1_reused_once_without_comparison_or_writer(self):
        from labflow.virtual_fleet import conducted_result_artifact as artifact
        with patch.object(comparison, "_twin", wraps=comparison._twin) as check, patch.object(
                comparison, "compare_conducted_twin_result", side_effect=AssertionError("no comparison")), patch.object(
                artifact, "write_conducted_result_artifact", side_effect=AssertionError("no writer")):
            self.assertEqual(self.call()["status"], "calculated")
        self.assertEqual(check.call_count, 1)

    def test_calculation_opens_no_files_native_backend_or_database(self):
        from labflow import control_packet_prepare as native
        import socket
        import sqlite3
        import subprocess
        blocked = AssertionError("no IO during pure calculation")
        with patch.object(builtins, "open", side_effect=blocked), patch.object(io, "open", side_effect=blocked), patch.object(
                Path, "read_bytes", side_effect=blocked), patch.object(native, "_WindowsIO", side_effect=blocked), patch.object(
                socket, "create_connection", side_effect=blocked), patch.object(sqlite3, "connect", side_effect=blocked), patch.object(
                subprocess, "Popen", side_effect=blocked):
            self.assertEqual(self.call()["status"], "calculated")

    def test_caller_decimal_context_cannot_change_math_or_get_modified(self):
        from decimal import Inexact, ROUND_FLOOR
        self.components = [self.component("u1", 1e100), self.component("u2", 1e100)]
        expected = self.call()
        with localcontext() as context:
            context.prec, context.rounding, context.Emax, context.Emin, context.capitals = 3, ROUND_FLOOR, 9, -9, 0
            context.traps[Inexact] = True
            before = (context.prec, context.rounding, context.Emax, context.Emin, context.capitals, dict(context.traps), dict(context.flags))
            self.assertEqual(self.call(), expected)
            self.assertEqual((context.prec, context.rounding, context.Emax, context.Emin, context.capitals, dict(context.traps), dict(context.flags)), before)

    def test_mutated_decimal_default_traps_do_not_change_calculation(self):
        from decimal import DefaultContext, Inexact, Rounded
        self.components = [self.component("u1", 1), self.component("u2", 1)]
        expected = self.call()
        saved = dict(DefaultContext.traps)
        try:
            DefaultContext.traps[Inexact] = DefaultContext.traps[Rounded] = True
            self.assertEqual(self.call(), expected)
        finally:
            DefaultContext.traps.update(saved)

    def test_hashes_scope_and_precision_contract(self):
        value = self.call()
        self.assertEqual(value["bindings"], dict(result_sha256=result_api._sha(self.result),
            components_sha256=result_api._sha(self.components), policy_sha256=result_api._sha(self.policy)))
        scope = value["scope"]
        self.assertEqual(set(scope), set("method_id method_version metric quantity reference_plane measurement_unit uncertainty_unit source_settings".split()))
        self.assertEqual((scope["metric"], scope["quantity"], scope["reference_plane"], scope["measurement_unit"], scope["uncertainty_unit"]),
                         ("on", "on_average", "source_output", "dBm", "dB"))
        arithmetic = value["trace"]["arithmetic"]
        self.assertEqual((arithmetic["sqrt_precision"], arithmetic["exact_conversion_precision"], arithmetic["rounding"]),
                         (80, 4096, "ROUND_HALF_EVEN"))

    def test_no_implicit_components_or_zero(self):
        for components in (None, [], {}, "unknown"):
            with self.subTest(components=components):
                self.components = components
                self.held("components_missing" if components in (None, []) else "components_invalid")

    def test_component_count_and_duplicate_identifier(self):
        self.components *= 9
        self.held("components_limit")
        self.components = [self.component("same", .3), self.component("same", .4)]
        self.held("component_duplicate")

    def test_component_numbers_missing_negative_bool_nonfinite_and_foreign(self):
        for value in (None, -.1, True, False, float("nan"), float("inf"), "0.3", Decimal("0.3"), Fraction(3, 10)):
            with self.subTest(value=repr(value)):
                self.components = [self.component("u1", value)]
                self.held()
        self.components = [self.component("u1", .3)]
        del self.components[0]["standard_uncertainty_db"]
        self.held("component_invalid")

    def test_component_scope_conflicts(self):
        for key, wrong, code in (("unit", "dBm", "unit_mismatch"), ("metric", "peak", "metric_mismatch"),
                                  ("quantity", "peak", "quantity_mismatch"),
                                  ("reference_plane", "sensor_input", "reference_plane_mismatch"),
                                  ("method", {"method_id": "other", "method_version": 1}, "method_mismatch")):
            with self.subTest(key=key):
                self.components = [self.component("u1", .3)]
                self.components[0][key] = wrong
                self.held(code)

    def test_missing_policy_and_k_never_default(self):
        self.policy = None
        self.held("policy_missing")
        self.setUp()
        del self.policy["coverage_factor"]
        self.held("policy_invalid")
        for k in (None, 0, -1, True, False, "2", float("inf")):
            with self.subTest(k=k):
                self.setUp()
                self.policy["coverage_factor"] = k
                self.held()

    def test_correlation_must_be_explicit_and_supported(self):
        for value in (None, "unknown", "independent", "correlated", 0, False):
            with self.subTest(value=value):
                self.setUp()
                self.policy["correlation_assumption"] = value
                self.held("correlation_unconfirmed")

    def test_all_three_evidence_lists_required_and_bounded(self):
        for name in ("component", "coverage_factor_evidence_refs", "correlation_evidence_refs"):
            for refs in (None, [], [""], [" "], ["a\nb"], ["x" * 513], ["x"] * 9, "ref", [0]):
                with self.subTest(name=name, refs=repr(refs)[:50]):
                    self.setUp()
                    if name == "component":
                        self.components[0]["evidence_refs"] = refs
                    else:
                        self.policy[name] = refs
                    self.held("evidence_missing")

    def test_extra_distribution_or_covariance_fields_not_interpreted(self):
        for target, key in (("component", "distribution"), ("policy", "covariance")):
            self.setUp()
            (self.components[0] if target == "component" else self.policy)[key] = "unknown"
            self.held("component_invalid" if target == "component" else "policy_invalid")

    def test_result_missing_incomplete_invalid_binding_and_metric(self):
        self.result = None
        self.held("result_missing")
        self.setUp()
        self.result["status"] = "incomplete"
        self.held("result_incomplete")
        self.setUp()
        self.result["binding"]["report_sha256"] = "0" * 64
        self.held("result_invalid")
        self.setUp()
        self.result["raw_measurement"]["quantity"]["metric"] = "peak"
        self.held("metric_mismatch")

    def test_overflow_and_positive_underflow_hold_both_numbers(self):
        for inputs, k in (([1.7976931348623157e308], 2), ([1e308, 1e308], 2),
                          ([5e-324], 5e-324), ([1e-300], 1e-300),
                          ([1e308] * 16, 1), ([1e300], 1e300)):
            with self.subTest(inputs=inputs, k=k):
                self.components = [self.component("u" + str(i), u) for i, u in enumerate(inputs)]
                self.policy["coverage_factor"] = k
                self.held("numeric_range")

    def test_whole_input_and_metadata_limits_preserve_nulls(self):
        self.components[0]["evidence_refs"] = ["x" * (2 * 1024 * 1024)]
        self.held("input_limit")
        self.setUp()
        self.policy["oversize"] = "x" * (64 * 1024)
        value = self.held("metadata_limit")
        self.assertIsNone(value["trace"]["provided_policy"])

    def test_native_cycle_depth_and_subclass_rejected(self):
        self.components.append(self.components)
        self.held("input_invalid")
        self.setUp()
        nested = 0
        for _ in range(40):
            nested = [nested]
        self.components[0]["extra"] = nested
        self.held("input_limit")
        self.setUp()
        class FakeFloat(float):
            pass
        self.components[0]["standard_uncertainty_db"] = FakeFloat(.3)
        self.held("input_invalid")

    def test_control_and_unexpected_runtime_errors_propagate_same_object(self):
        for error in (KeyboardInterrupt(), MemoryError(), SystemExit(0), GeneratorExit(), RuntimeError("not successful")):
            with self.subTest(error=type(error).__name__):
                with patch.object(comparison, "_twin", side_effect=error):
                    with self.assertRaises(type(error)) as caught:
                        self.call()
                self.assertIs(caught.exception, error)

    def test_late_output_failure_clears_computed_trace_and_estimates(self):
        original = result_api._canonical
        def fail(value):
            if type(value) is dict and value.get("kind") == "conducted_uncertainty_budget" and value.get("status") == "calculated":
                raise UnicodeError("late serialization")
            return original(value)
        with patch.object(result_api, "_canonical", side_effect=fail):
            self.held("output_invalid")

    def test_output_limit_after_math_does_not_publish_partial_estimates(self):
        with patch.object(self.api, "MAX_OUTPUT_BYTES", 1):
            self.held("output_limit")

    def test_returned_source_labels_and_refs_are_unattested_provided_claims(self):
        self.components[0]["evidence_refs"] = ["claimed:actual-calcert"]
        self.policy["correlation_evidence_refs"] = ["claimed:independent-physical"]
        value = self.call()
        self.assertEqual(value["status"], "calculated")
        self.assertEqual(value["trace"]["provided_components"][0]["evidence_refs"], ["claimed:actual-calcert"])
        self.assertIs(value["verification"]["evidence_authenticity_verified"], False)
        self.assertIs(value["verification"]["correlation_verified"], False)
