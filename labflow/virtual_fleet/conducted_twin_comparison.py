"""One supplied on-average comparison; no execution, storage, or conformity claim."""
from fractions import Fraction

from .. import fcc_case_evaluation as _groups
from . import conducted_result_artifact as _artifact
from . import conducted_twin_result as _result
from .integration import _source_configuration

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 256 * 1024
MAX_CASES = 128
_REFERENCE = set("schema_version kind case_id revision split_id data_origin method source_settings measurement evidence_refs".split())
_POLICY = set("policy_id policy_version purpose tolerance_db".split())
_LINEAGE = set("schema_version kind split_id revisions cases calibration_case_ids independent_case_ids".split())
_ORIGINS = ("provided_synthetic", "provided_measured", "provided_replay", "unknown")
_COMPARISON = "twin_value_dbm reference_value_dbm signed_difference_db absolute_difference_db tolerance_db within_tolerance signed_difference_rational_db absolute_difference_rational_db".split()
_GROUP_CODES = frozenset("input_invalid budget_exceeded selection_invalid duplicate_selection duplicate_case_id unknown_case_id overlapping_selection cross_split_component partial_component ineligible_component".split())


class _Hold(ValueError):
    def __init__(self, code, field, detail=None):
        self.code, self.field, self.detail = code, field, detail


def _need(condition, code, field, detail=None):
    if not condition:
        raise _Hold(code, field, detail)


def _keys(value, expected, code, field):
    _need(type(value) is dict and set(value) == expected, code, field)


def _text(value, limit=128):
    return type(value) is str and 0 < len(value) <= limit and bool(value.strip()) and all(ord(c) >= 32 for c in value)


def _base():
    return dict(schema_version=1, kind="conducted_twin_comparison", status="not_assessed",
        bindings=dict(twin_result_sha256=None, reference_sha256=None, policy_sha256=None, lineage_sha256=None),
        scope=None, comparison=dict.fromkeys(_COMPARISON),
        independence=dict(status="not_assessed", split_sha256=None, case_count=None, reference_case_id=None),
        reference=dict(data_origin=None, authenticity_verified=False, rights_verified=False, uncertainty_db=None),
        reasons=[], conformity=dict(status="not_assessed", verdict=None),
        verification=dict(hardware_verified=False, physical_verified=False, uncertainty_assessed=False,
            model_execution_verified=False, method_approval="not_assessed", source_bytes="not_reopened",
            trust_scope="provided_values_and_group_metadata_only", execution_authority=False))


def _twin(value):
    _need(value is not None, "twin_result_missing", "twin_result")
    _need(type(value) is dict, "twin_result_invalid", "twin_result")
    _need(value.get("status") == "recorded", "twin_result_incomplete", "twin_result.status")
    binding = value.get("binding")
    _need(type(binding) is dict, "twin_binding_invalid", "twin_result.binding")
    try:
        # This existing validator is pure. The artifact writer is never invoked.
        value, _, scope = _artifact._input(value, "comparison", _result._sha(value),
                                         binding.get("run_id"), binding.get("runtime_instance_id"))
        _need(scope == "full_bound", "twin_binding_invalid", "twin_result.binding")
        _result._plan(value["binding"]["plan_input"])
    except _artifact.ConductedResultArtifactError:
        raise _Hold("twin_result_invalid", "twin_result") from None
    except _result._Failure:
        raise _Hold("twin_binding_invalid", "twin_result.binding") from None
    plan = value["binding"]["plan_input"]["plan"]
    _need(plan["metric"] == "on", "metric_mismatch", "twin_result.plan.metric")
    _need(all(type(gap) is dict and set(gap) == {"code", "field", "provided", "blocking"}
              and type(gap["blocking"]) is bool and not gap["blocking"] for gap in value["gaps"]),
          "twin_result_incomplete", "twin_result.gaps")
    raw, calculation = value["raw_measurement"], value["calculation"]
    _need(type(raw) is dict, "twin_measurement_invalid", "twin_result.raw_measurement")
    packet, quantity = raw["packet"], raw["quantity"]
    _keys(quantity, {"metric", "reference_plane", "loss_compensation_applied", "loss_compensation_sign"},
          "twin_measurement_invalid", "twin_result.raw_measurement.quantity")
    _need(type(packet) is dict and quantity["metric"] == "on"
          and ("quantity" not in packet or packet["quantity"] == "on_average"),
          "metric_mismatch", "twin_result.raw_measurement")
    _need(quantity["reference_plane"] == raw["reference_plane"] == calculation["raw_reference_plane"] == "sensor_input"
          and quantity["loss_compensation_applied"] is False
          and _result._number(quantity["loss_compensation_sign"]) and quantity["loss_compensation_sign"] == 1,
          "twin_measurement_invalid", "twin_result.raw_measurement.quantity")
    _need(packet.get("unit") == "dBm" and _result._number(packet.get("value")),
          "twin_measurement_invalid", "twin_result.raw_measurement.packet")
    _need(packet.get("status") == "ok" and packet.get("valid") is True and packet.get("source_id") == raw["device_id"]
          and _result._number(packet.get("power_dbm")) and packet["power_dbm"] == packet["value"]
          and all(_result._number(packet.get(key)) and packet[key] == plan["source_settings"][key]
                  for key in ("frequency_hz", "duty_cycle", "crest_factor_db")),
          "twin_measurement_invalid", "twin_result.raw_measurement.packet")
    _need(calculation["target_reference_plane"] == plan["reference_plane"] == "source_output",
          "reference_plane_mismatch", "twin_result.calculation.target_reference_plane")
    corrected = calculation["corrected"]
    _keys(corrected, {"value", "unit", "power_w"}, "twin_measurement_invalid", "twin_result.calculation.corrected")
    _need(corrected["unit"] == "dBm" and _result._number(corrected["value"])
          and _result._number(corrected["power_w"]) and corrected["power_w"] > 0,
          "twin_measurement_invalid", "twin_result.calculation.corrected")
    return plan, corrected["value"]


def _reference(value, plan):
    _need(value is not None, "reference_missing", "reference")
    _keys(value, _REFERENCE, "reference_invalid", "reference")
    _need(type(value["schema_version"]) is int and value["schema_version"] == 1
          and value["kind"] == "provided_conducted_reference" and _artifact._opaque(value["case_id"])
          and _text(value["revision"]) and _artifact._opaque(value["split_id"]), "reference_invalid", "reference")
    _keys(value["method"], {"method_id", "method_version"}, "method_mismatch", "reference.method")
    method = value["method"]
    _need(type(method["method_id"]) is str and type(method["method_version"]) is int
          and all(method[key] == plan[key] for key in method), "method_mismatch", "reference.method")
    try:
        source = _source_configuration(value["source_settings"])
    except ValueError:
        raise _Hold("source_settings_invalid", "reference.source_settings") from None
    _need(source == plan["source_settings"], "source_settings_mismatch", "reference.source_settings")
    measurement = value["measurement"]
    _keys(measurement, {"value", "unit", "metric", "reference_plane"}, "measurement_invalid", "reference.measurement")
    _need(measurement["unit"] == "dBm", "unit_mismatch", "reference.measurement.unit")
    _need(measurement["metric"] == "on", "metric_mismatch", "reference.measurement.metric")
    _need(measurement["reference_plane"] == plan["reference_plane"], "reference_plane_mismatch", "reference.measurement.reference_plane")
    _need(_result._number(measurement["value"]), "measurement_invalid", "reference.measurement.value")
    origin = value["data_origin"]
    _need(type(origin) is str and origin in _ORIGINS,
          "reference_invalid", "reference.data_origin")
    _need(origin != "unknown", "origin_unknown", "reference.data_origin")
    refs = value["evidence_refs"]
    _need(type(refs) is list and 1 <= len(refs) <= 32 and all(_text(ref, 512) for ref in refs),
          "reference_invalid", "reference.evidence_refs")
    return measurement["value"]


def _policy(value):
    _need(value is not None, "policy_missing", "comparator_policy")
    _need(type(value) is dict and "tolerance_db" in value, "tolerance_missing", "comparator_policy.tolerance_db")
    _keys(value, _POLICY, "policy_invalid", "comparator_policy")
    _need(_artifact._opaque(value["policy_id"]) and type(value["policy_version"]) is int and value["policy_version"] > 0
          and value["purpose"] == "independent_validation", "policy_invalid", "comparator_policy")
    tolerance = value["tolerance_db"]
    _need(_result._number(tolerance) and tolerance >= 0, "tolerance_invalid", "comparator_policy.tolerance_db")
    return tolerance


def _lineage(value, reference):
    _need(value is not None, "lineage_missing", "lineage")
    _keys(value, _LINEAGE, "lineage_invalid", "lineage")
    _need(type(value["schema_version"]) is int and value["schema_version"] == 1
          and value["kind"] == "conducted_comparison_lineage", "lineage_invalid", "lineage")
    _need(value["split_id"] == reference["split_id"], "split_mismatch", "lineage.split_id")
    cases, revisions = value["cases"], value["revisions"]
    _need(type(cases) is list and 1 <= len(cases) <= MAX_CASES, "lineage_limit", "lineage.cases")
    _need(all(type(case) is dict and type(case.get("case_id")) is str for case in cases), "lineage_invalid", "lineage.cases")
    ids = [case["case_id"] for case in cases]
    _need(len(set(ids)) == len(ids) and type(revisions) is dict and set(revisions) == set(ids)
          and all(_text(revision) for revision in revisions.values()), "lineage_invalid", "lineage.revisions")
    _need(reference["case_id"] in revisions and revisions[reference["case_id"]] == reference["revision"],
          "revision_mismatch", "lineage.revisions")
    _need(type(value["independent_case_ids"]) is list and value["independent_case_ids"] == [reference["case_id"]],
          "lineage_invalid", "lineage.independent_case_ids")
    _need(type(value["calibration_case_ids"]) is list and len(value["calibration_case_ids"]) <= MAX_CASES,
          "lineage_invalid", "lineage.calibration_case_ids")
    try:
        split = _groups.build_case_evaluation_split(cases, development_case_ids=value["calibration_case_ids"],
                                                   independent_case_ids=value["independent_case_ids"])
    except ValueError as error:
        # Only the parent's fixed codes are exposed; never arbitrary exception text.
        known = {"fcc_case_evaluation_" + code: code for code in _GROUP_CODES}
        code = known.get(str(error))
        reason = ("lineage_overlap" if code in ("cross_split_component", "overlapping_selection") else
                  "lineage_unconfirmed" if code in ("partial_component", "ineligible_component") else "lineage_invalid")
        raise _Hold(reason, "lineage", code) from None
    _need(type(split) is dict and split.get("status") == "configured" and split.get("scope") == "provided_metadata_only"
          and split.get("fact_review_verified") is False
          and split.get("independent", {}).get("case_ids") == [reference["case_id"]], "lineage_invalid", "lineage")
    return dict(status="provided_metadata_disjoint", split_sha256=_result._sha(split),
                case_count=len(cases), reference_case_id=reference["case_id"])


def _difference(twin, reference, tolerance):
    signed = Fraction(str(twin)) - Fraction(str(reference))
    absolute = abs(signed)
    try:
        projected, projected_abs = float(signed), float(absolute)
    except OverflowError:
        raise _Hold("numeric_range", "comparison") from None
    _need(_result._number(projected) and _result._number(projected_abs)
          and (signed == 0 or projected != 0), "numeric_range", "comparison")
    return dict(twin_value_dbm=twin, reference_value_dbm=reference, signed_difference_db=projected,
        absolute_difference_db=projected_abs, tolerance_db=tolerance,
        within_tolerance=absolute <= Fraction(str(tolerance)), signed_difference_rational_db=str(signed),
        absolute_difference_rational_db=str(absolute))


def compare_conducted_twin_result(twin_result, reference=None, *, comparator_policy=None, lineage=None):
    """Compare one provided pair; missing evidence never receives a numeric default."""
    output = _base()
    try:
        copied = _result._snapshot(dict(twin_result=twin_result, reference=reference,
                                       comparator_policy=comparator_policy, lineage=lineage))
        _need(len(_result._canonical(copied)) <= MAX_INPUT_BYTES, "input_limit", "input")
        for name, key in (("twin_result", "twin_result_sha256"), ("reference", "reference_sha256"),
                          ("comparator_policy", "policy_sha256"), ("lineage", "lineage_sha256")):
            if copied[name] is not None:
                output["bindings"][key] = _result._sha(copied[name])
        twin_result, reference, comparator_policy, lineage = (copied[name] for name in
            ("twin_result", "reference", "comparator_policy", "lineage"))
        if type(reference) is dict and type(reference.get("data_origin")) is str and reference["data_origin"] in _ORIGINS:
            output["reference"]["data_origin"] = reference["data_origin"]
        plan, twin_value = _twin(twin_result)
        reference_value = _reference(reference, plan)
        tolerance = _policy(comparator_policy)
        output["independence"] = _lineage(lineage, reference)
        output["scope"] = dict(method_id=plan["method_id"], method_version=plan["method_version"], metric="on",
                               reference_plane=plan["reference_plane"], unit="dBm", source_settings=plan["source_settings"])
        output["comparison"] = _difference(twin_value, reference_value, tolerance)
        output["status"] = "compared"
        _need(len(_result._canonical(output)) <= MAX_OUTPUT_BYTES, "output_limit", "output")
    except _Hold as error:
        output["status"] = "not_assessed"
        output["comparison"] = dict.fromkeys(_COMPARISON)
        output["reasons"].append(dict(code=error.code, field=error.field, detail=error.detail))
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        output["status"] = "not_assessed"
        output["comparison"] = dict.fromkeys(_COMPARISON)
        output["reasons"].append(dict(code="input_invalid", field="input", detail=None))
    return output
