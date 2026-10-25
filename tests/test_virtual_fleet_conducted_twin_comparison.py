"""One supplied comparison: independent decimal arithmetic and real metadata grouping."""
from copy import deepcopy
from decimal import Decimal, localcontext
import importlib
import importlib.util
from pathlib import Path
import socket
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from labflow import calculations, fcc_case_evaluation
from labflow.virtual_fleet import conducted_twin_result as result_api

SPEC = importlib.util.spec_from_file_location(
    "comparison_result_fixture", Path(__file__).with_name("test_virtual_fleet_conducted_twin_result.py"))
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
UNSET = object()
FIELDS = set("twin_value_dbm reference_value_dbm signed_difference_db absolute_difference_db tolerance_db "
             "within_tolerance signed_difference_rational_db absolute_difference_rational_db".split())


def group(identity, family, fcc, sha):
    return dict(case_id=identity, product_family_group_id=family, fcc_ids=[fcc],
                report_group_id="report:" + identity, original_sha256s=[sha],
                reuse_group_ids=["reuse:" + identity], group_review_status="reviewed", unresolved_relations=[])


class ConductedTwinComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        case = FIXTURE.ConductedTwinResultTests()
        cls.addClassCleanup(case.doCleanups)
        args, ref = case.genuine(power=-7)
        cls.genuine_result = result_api.build_conducted_twin_result(*args, measurement_ref=ref)
        if cls.genuine_result["status"] != "recorded":
            raise AssertionError("genuine same-run result fixture did not record")
        if cls.genuine_result["calculation"]["corrected"]["value"] != -7:
            raise AssertionError("independent fixture power was not -7 dBm")

    def setUp(self):
        self.result = deepcopy(self.genuine_result)
        method = self.result["binding"]["plan_input"]["plan"]
        self.reference = dict(schema_version=1, kind="provided_conducted_reference", case_id="ref-one",
            revision="rev-2", split_id="split-first", data_origin="provided_synthetic",
            method={k: method[k] for k in ("method_id", "method_version")},
            source_settings=deepcopy(method["source_settings"]),
            measurement=dict(value=-7.1, unit="dBm", metric="on", reference_plane="source_output"),
            evidence_refs=["authored:known-pair"])
        self.policy = dict(policy_id="bench-predeclared", policy_version=1,
                           purpose="independent_validation", tolerance_db=0.1)
        self.lineage = dict(schema_version=1, kind="conducted_comparison_lineage", split_id="split-first",
            cases=[group("cal-one", "CalibrationDevice", "ABCCAL001", "a" * 64),
                   group("ref-one", "ValidationDevice", "ABCREF002", "b" * 64)],
            revisions={"cal-one": "rev-1", "ref-one": "rev-2"},
            calibration_case_ids=["cal-one"], independent_case_ids=["ref-one"])

    def module(self):
        name = "labflow.virtual_fleet.conducted_twin_comparison"
        self.assertIsNotNone(importlib.util.find_spec(name), "pure comparison module is absent")
        return importlib.import_module(name)

    def call(self, result=UNSET, reference=UNSET, policy=UNSET, lineage=UNSET):
        return self.module().compare_conducted_twin_result(
            self.result if result is UNSET else result,
            self.reference if reference is UNSET else reference,
            comparator_policy=self.policy if policy is UNSET else policy,
            lineage=self.lineage if lineage is UNSET else lineage)

    def withheld(self, *, reason=None, **kwargs):
        value = self.call(**kwargs)
        self.assertEqual(value["status"], "not_assessed")
        self.assertEqual(set(value["comparison"]), FIELDS)
        self.assertTrue(all(x is None for x in value["comparison"].values()))
        self.assertTrue(value["reasons"])
        if reason is not None:
            self.assertIn(reason, [x["code"] for x in value["reasons"]])
        self.assertIsNone(value["conformity"]["verdict"])
        return value

    def test_genuine_result_known_pair_is_only_comparison_not_FCC_or_physical_PASS(self):
        value = self.call()
        self.assertEqual(set(value), set("schema_version kind status bindings scope comparison independence "
                                        "reference reasons conformity verification".split()))
        self.assertEqual(value["kind"], "conducted_twin_comparison")
        self.assertEqual(value["status"], "compared")
        self.assertEqual(value["comparison"], dict(twin_value_dbm=-7.0, reference_value_dbm=-7.1,
            signed_difference_db=0.1, absolute_difference_db=0.1, tolerance_db=0.1,
            within_tolerance=True, signed_difference_rational_db="1/10", absolute_difference_rational_db="1/10"))
        self.assertEqual(value["scope"]["reference_plane"], "source_output")
        self.assertEqual(value["independence"]["status"], "provided_metadata_disjoint")
        self.assertEqual(value["reference"]["data_origin"], "provided_synthetic")
        self.assertIs(value["reference"]["authenticity_verified"], False)
        self.assertIs(value["reference"]["rights_verified"], False)
        self.assertIsNone(value["reference"]["uncertainty_db"])
        self.assertEqual(value["conformity"], dict(status="not_assessed", verdict=None))
        for field in ("hardware_verified", "physical_verified", "model_execution_verified", "uncertainty_assessed", "execution_authority"):
            self.assertIs(value["verification"][field], False)
        self.assertEqual(value["verification"]["method_approval"], "not_assessed")

    def test_signed_difference_and_inclusive_decimal_boundary_use_independent_Decimal(self):
        cases = [(-7.1, 0.1), (-6.9, 0.1), (-7.1000000001, 0.1), (-6.8999999999, 0.1),
                 (-7, 0), (0, 7), (-18.0001, 11.0001), (1e-10, 7.0000000001), (1e308, 1e308)]
        for reading, tolerance in cases:
            with self.subTest(reference=reading, tolerance=tolerance), localcontext() as context:
                context.prec = 1000
                self.reference["measurement"]["value"] = reading
                self.policy["tolerance_db"] = tolerance
                difference = Decimal("-7") - Decimal(str(reading))
                value = self.call()
                self.assertEqual(value["status"], "compared")
                numbers = value["comparison"]
                self.assertEqual(numbers["signed_difference_db"], float(difference))
                self.assertEqual(numbers["absolute_difference_db"], float(abs(difference)))
                self.assertEqual(numbers["within_tolerance"], abs(difference) <= Decimal(str(tolerance)))
                if reading == 1e308:
                    self.assertIs(numbers["within_tolerance"], False)

    def test_zero_tolerance_requires_exact_equality(self):
        self.reference["measurement"]["value"] = -7
        self.policy["tolerance_db"] = 0
        self.assertIs(self.call()["comparison"]["within_tolerance"], True)
        self.reference["measurement"]["value"] = -7.000000000000001
        self.assertIs(self.call()["comparison"]["within_tolerance"], False)

    def test_missing_reference_policy_tolerance_or_lineage_never_gets_default_numbers(self):
        for args in (dict(reference=None), dict(policy=None), dict(lineage=None)):
            with self.subTest(args=args): self.withheld(**args)
        del self.policy["tolerance_db"]
        self.withheld(reason="tolerance_missing")

    def test_tolerance_native_bool_nonfinite_negative_and_subclasses_are_rejected(self):
        class Derived(int): pass
        class Floating(float): pass
        for item in (True, False, -1, float("nan"), float("inf"), None, "0.1", Derived(1), Floating(0.1)):
            self.policy["tolerance_db"] = item
            with self.subTest(value=type(item).__name__): self.withheld()

    def test_reference_value_is_native_finite_number_without_bool_or_type_coercion(self):
        class Derived(float): pass
        for item in (True, None, "-7.1", float("nan"), float("inf"), Derived(-7.1), 10 ** 500):
            self.reference["measurement"]["value"] = item
            with self.subTest(value=type(item).__name__): self.withheld()

    def test_unit_metric_and_reference_plane_mismatch_are_withheld_without_conversion(self):
        for field, item, reason in (("unit", "W", "unit_mismatch"), ("metric", "peak", "metric_mismatch"),
                                    ("metric", "time", "metric_mismatch"),
                                    ("reference_plane", "sensor_input", "reference_plane_mismatch"),
                                    ("reference_plane", None, "reference_plane_mismatch")):
            before = deepcopy(self.reference)
            self.reference["measurement"][field] = item
            with self.subTest(field=field, value=item): self.withheld(reason=reason)
            self.reference = before

    def test_method_id_version_and_bool_version_cannot_be_assumed_matching(self):
        for method in (dict(method_id="other", method_version=1), dict(method_id="conducted_synthetic", method_version=2),
                       dict(method_id="conducted_synthetic", method_version=True), {}):
            self.reference["method"] = method
            with self.subTest(method=method): self.withheld()

    def test_all_six_source_conditions_must_match_and_stay_native(self):
        changes = {"frequency_hz": 2460000000, "power_dbm": -6, "bandwidth_hz": 10000000,
                   "duty_cycle": 0.25, "crest_factor_db": 3, "modulation": "CW"}
        original = deepcopy(self.reference["source_settings"])
        for key, item in changes.items():
            self.reference["source_settings"] = {**original, key: item}
            with self.subTest(field=key): self.withheld(reason="source_settings_mismatch")
        self.reference["source_settings"] = {**original, "frequency_hz": True}
        self.withheld()

    def test_incomplete_unbound_or_changed_result_is_not_comparable(self):
        for change in (lambda r:r.update(status="incomplete"), lambda r:r.update(binding={}),
                       lambda r:r["binding"].update(report_sha256="0"*64),
                       lambda r:r["verification"].update(hardware_verified=True)):
            self.result = deepcopy(self.genuine_result); change(self.result)
            with self.subTest(change=change): self.withheld()

    def test_unknown_twin_quantity_plane_or_non_numeric_corrected_value_cannot_pass(self):
        for change in (lambda r:r["raw_measurement"]["quantity"].update(metric="peak"),
                       lambda r:r["raw_measurement"]["quantity"].update(reference_plane=None),
                       lambda r:r["raw_measurement"]["packet"].update(quantity="peak"),
                       lambda r:r["raw_measurement"]["packet"].update(valid=False),
                       lambda r:r["raw_measurement"]["packet"].update(status="unavailable"),
                       lambda r:r["raw_measurement"]["packet"].update(source_id="other-device"),
                       lambda r:r["raw_measurement"]["packet"].update(power_dbm=999),
                       lambda r:r["raw_measurement"]["packet"].update(frequency_hz=2460000000),
                       lambda r:r["calculation"]["corrected"].update(value=True)):
            self.result = deepcopy(self.genuine_result); change(self.result)
            with self.subTest(change=change): self.withheld()

    def test_claimed_measured_or_replay_origin_does_not_authenticate_measurement_or_rights(self):
        for origin in ("provided_measured", "provided_replay"):
            self.reference["data_origin"] = origin
            value = self.call()
            self.assertEqual(value["status"], "compared")
            self.assertEqual(value["reference"]["data_origin"], origin)
            self.assertIs(value["reference"]["authenticity_verified"], False)
            self.assertIs(value["reference"]["rights_verified"], False)
        self.reference["data_origin"] = "unknown"
        value = self.withheld(reason="origin_unknown")
        self.assertEqual(value['reference']['data_origin'], 'unknown')

    def test_each_group_namespace_overlap_blocks_independent_validation(self):
        for key in ("product_family_group_id", "fcc_ids", "report_group_id", "original_sha256s", "reuse_group_ids"):
            original = deepcopy(self.lineage)
            self.lineage["cases"][1][key] = deepcopy(self.lineage["cases"][0][key])
            with self.subTest(namespace=key): self.withheld(reason="lineage_overlap")
            self.lineage = original

    def test_group_normalization_does_not_make_case_or_space_aliases_independent(self):
        self.lineage["cases"][1]["product_family_group_id"] = " CALIBRATIONDEVICE "
        self.withheld(reason="lineage_overlap")
        self.lineage["cases"][1]["product_family_group_id"] = "ValidationDevice"
        self.lineage["cases"][1]["fcc_ids"] = [" abccal001 "]
        self.withheld(reason="lineage_overlap")

    def test_transitive_same_data_relation_cannot_cross_split_through_unselected_bridge(self):
        bridge = group("bridge", "CalibrationDevice", "OTHERFCC", "b" * 64)
        self.lineage["cases"].append(bridge)
        self.lineage["revisions"]["bridge"] = "rev-bridge"
        self.withheld(reason="lineage_overlap")

    def test_partial_component_or_unreviewed_unresolved_metadata_remains_unconfirmed(self):
        for change in (lambda c:c.update(group_review_status="pending"),
                       lambda c:c.update(unresolved_relations=["same-data-revision-unconfirmed"]),
                       lambda c:c.update(product_family_group_id=None),
                       lambda c:c.update(original_sha256s=[])):
            original = deepcopy(self.lineage); change(self.lineage["cases"][1])
            with self.subTest(change=change): self.withheld(reason="lineage_unconfirmed")
            self.lineage = original
        bridge = group("bridge", "DifferentFamily", "OTHERFCC", "b" * 64)
        self.lineage["cases"].append(bridge); self.lineage["revisions"]["bridge"] = "rev-bridge"
        self.withheld(reason="lineage_unconfirmed")

    def test_revision_and_split_labels_cannot_override_same_original_data(self):
        self.lineage["cases"][1]["original_sha256s"] = ["a" * 64]
        self.reference["revision"] = self.lineage["revisions"]["ref-one"] = "rev-unrelated-name"
        self.reference["split_id"] = self.lineage["split_id"] = "another-split-label"
        self.withheld(reason="lineage_overlap")

    def test_revision_split_or_independent_selection_mismatch_is_not_assessed(self):
        original = deepcopy(self.lineage)
        for change in (lambda l:l.update(split_id="other-split"),
                       lambda l:l["revisions"].update({"ref-one":"other-revision"}),
                       lambda l:l.update(independent_case_ids=["cal-one"]),
                       lambda l:l.update(calibration_case_ids=["cal-one", "ref-one"]),
                       lambda l:l.update(calibration_case_ids=["missing-id"])):
            self.lineage = deepcopy(original); change(self.lineage)
            with self.subTest(change=change): self.withheld()

    def test_explicit_empty_calibration_selection_is_only_a_provided_metadata_claim(self):
        self.lineage["calibration_case_ids"] = []
        value = self.call()
        self.assertEqual(value["status"], "compared")
        self.assertEqual(value["verification"]["trust_scope"], "provided_values_and_group_metadata_only")
        self.assertIs(value["verification"]["physical_verified"], False)

    def test_input_and_returned_nested_data_are_detached_without_modifying_raw_values(self):
        before = deepcopy((self.result,self.reference,self.policy,self.lineage))
        value = self.call()
        self.assertEqual((self.result,self.reference,self.policy,self.lineage), before)
        value["scope"]["source_settings"]["power_dbm"] = 999
        self.assertEqual((self.result,self.reference,self.policy,self.lineage), before)
        self.assertEqual(value["bindings"]["twin_result_sha256"], result_api._sha(self.result))
        self.assertEqual(value["bindings"]["reference_sha256"], result_api._sha(self.reference))

    def test_no_IO_models_storage_rawref_follow_rebuild_or_unit_conversion(self):
        module = self.module()
        from contextlib import ExitStack
        from labflow.virtual_fleet import conducted_result_artifact as artifact
        with ExitStack() as stack:
            for obj,name in ((Path,"open"),(socket,"create_connection"),(sqlite3,"connect"),(subprocess,"Popen"),
                             (artifact._native,"_WindowsIO"),(result_api,"build_conducted_twin_result"),
                             (result_api,"calculate"),(calculations,"calculate")):
                stack.enter_context(patch.object(obj,name,side_effect=AssertionError("pure comparison boundary")))
            value = module.compare_conducted_twin_result(self.result,self.reference,comparator_policy=self.policy,lineage=self.lineage)
        self.assertEqual(value["status"], "compared")

    def test_control_exceptions_from_snapshot_and_real_group_dependency_keep_identity(self):
        self.module()
        for dependency,name in ((result_api,"_snapshot"),(fcc_case_evaluation,"build_case_evaluation_split")):
            for kind in (KeyboardInterrupt, MemoryError, SystemExit, GeneratorExit):
                error = kind("controlled comparison interruption")
                with self.subTest(boundary=name, control=kind.__name__), patch.object(dependency,name,side_effect=error):
                    with self.assertRaises(kind) as raised: self.call()
                    self.assertIs(raised.exception,error)

    def test_native_containers_only_and_cycles_do_not_execute_callbacks(self):
        class Hostile(dict):
            def items(self): raise AssertionError("callback")
        for item in (Hostile(self.reference), [], "reference", {**self.reference, "extra":1}):
            with self.subTest(type=type(item).__name__): self.withheld(reference=item)
        cyclic = {};cyclic["self"] = cyclic
        self.withheld(reference=cyclic)

    def test_case_count_and_byte_limits_withhold_instead_of_truncating(self):
        self.lineage["cases"] *= 65
        self.withheld()
        self.withheld(reference={**self.reference,"evidence_refs":["x"*(2*1024*1024)]})

    def test_numeric_overflow_does_not_become_zero_infinity_or_a_tolerance_success(self):
        self.result["calculation"]["corrected"]["value"] = -1e308
        self.reference["measurement"]["value"] = 1e308
        self.policy["tolerance_db"] = 1e308
        self.withheld(reason="numeric_range")

    def test_late_serialization_failure_clears_numbers_and_cannot_return_compared(self):
        self.module()
        canonical = result_api._canonical
        def fail(value):
            if type(value) is dict and value.get('kind') == 'conducted_twin_comparison':
                raise ValueError('PRIVATE late serialization error')
            return canonical(value)
        with patch.object(result_api, '_canonical', side_effect=fail):
            value = self.withheld()
        self.assertNotIn('PRIVATE', str(value['reasons']))
