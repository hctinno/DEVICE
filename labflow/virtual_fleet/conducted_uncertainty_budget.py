"""Arithmetic of explicit supplied standard components; no physical approval or IO."""
from decimal import Context, Decimal, DecimalException, DivisionByZero, Inexact, InvalidOperation, Overflow, Rounded, ROUND_HALF_EVEN, localcontext
from fractions import Fraction

from . import conducted_twin_comparison as _comparison
from . import conducted_twin_result as _result

MAX_COMPONENTS = 16
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 256 * 1024
_COMPONENT = set("component_id standard_uncertainty_db unit method metric quantity reference_plane evidence_refs".split())
_POLICY = set("policy_id policy_version coverage_factor coverage_factor_evidence_refs correlation_assumption correlation_evidence_refs".split())
_COMPUTED = ("sum_of_squares_rational_db2", "coverage_factor_rational",
             "combined_standard_uncertainty_decimal_db", "expanded_uncertainty_decimal_db")


class _Hold(ValueError):
    def __init__(self, code, field, detail=None):
        self.code, self.field, self.detail = code, field, detail


def _need(condition, code, field):
    if not condition:
        raise _Hold(code, field)


def _base():
    trace = dict.fromkeys(_COMPUTED)
    trace.update(provided_components=None, provided_policy=None, terms=[],
        formula=dict(combined="sqrt(sum(u_i**2))", expanded="k * sqrt(sum(u_i**2))"),
        arithmetic=dict(inputs="Fraction(str(native_number))", sum="exact rational",
            square_root="Decimal.sqrt", sqrt_precision=80, exact_conversion_precision=4096,
            rounding="ROUND_HALF_EVEN", float_projection="finite; positive exact value must remain nonzero; Decimal trace authoritative"))
    return dict(schema_version=1, kind="conducted_uncertainty_budget", status="not_assessed",
        bindings=dict(result_sha256=None, components_sha256=None, policy_sha256=None), scope=None,
        budget=dict(combined_standard_uncertainty_db=None, expanded_uncertainty_db=None), trace=trace, reasons=[],
        conformity=dict(status="not_assessed", verdict=None),
        verification=dict(mathematical_combination_only=True, physical_verified=False, hardware_verified=False,
            components_complete=False, correlation_verified=False, evidence_authenticity_verified=False,
            method_approval="not_assessed", source_bytes="not_reopened", applied_to_result=False, execution_authority=False))


def _evidence(value, field):
    _need(type(value) is list and 1 <= len(value) <= 8 and all(
        type(item) is str and 0 < len(item) <= 512 and bool(item.strip())
        and all(ord(c) >= 32 and not 127 <= ord(c) <= 159 for c in item) for item in value),
        "evidence_missing", field)


def _nonfinite(components, policy):
    # Give an explicit field for nonfinite values, which cannot enter native JSON traces.
    if type(components) is list and len(components) <= MAX_COMPONENTS:
        for i, component in enumerate(components):
            if type(component) is dict:
                value = component.get("standard_uncertainty_db")
                _need(type(value) is not float or _result._number(value),
                      "component_value_invalid", f"components[{i}].standard_uncertainty_db")
    if type(policy) is dict:
        value = policy.get("coverage_factor")
        _need(type(value) is not float or _result._number(value), "coverage_factor_invalid", "policy.coverage_factor")


def _components(value, plan):
    _need(value is not None and value != [], "components_missing", "components")
    _need(type(value) is list, "components_invalid", "components")
    _need(1 <= len(value) <= MAX_COMPONENTS, "components_limit", "components")
    seen, terms, squared = set(), [], Fraction()
    for i, component in enumerate(value):
        field = f"components[{i}]"
        _need(type(component) is dict and set(component) == _COMPONENT, "component_invalid", field)
        identity = component["component_id"]
        _need(_comparison._artifact._opaque(identity), "component_invalid", field + ".component_id")
        _need(identity not in seen, "component_duplicate", field + ".component_id")
        seen.add(identity)
        number = component["standard_uncertainty_db"]
        _need(_result._number(number) and number >= 0, "component_value_invalid", field + ".standard_uncertainty_db")
        _need(component["unit"] == "dB", "unit_mismatch", field + ".unit")
        _need(component["metric"] == "on", "metric_mismatch", field + ".metric")
        _need(component["quantity"] == "on_average", "quantity_mismatch", field + ".quantity")
        _need(component["reference_plane"] == "source_output", "reference_plane_mismatch", field + ".reference_plane")
        method = component["method"]
        _need(type(method) is dict and set(method) == {"method_id", "method_version"}
              and type(method["method_id"]) is str and type(method["method_version"]) is int
              and all(method[key] == plan[key] for key in method), "method_mismatch", field + ".method")
        _evidence(component["evidence_refs"], field + ".evidence_refs")
        standard = Fraction(str(number))
        variance = standard ** 2
        squared += variance
        terms.append(dict(component_id=identity, standard_uncertainty_rational_db=str(standard),
                          variance_rational_db2=str(variance)))
    return terms, squared


def _policy(value):
    _need(value is not None, "policy_missing", "policy")
    _need(type(value) is dict and set(value) == _POLICY, "policy_invalid", "policy")
    _need(_comparison._artifact._opaque(value["policy_id"]) and type(value["policy_version"]) is int
          and value["policy_version"] > 0, "policy_invalid", "policy")
    factor = value["coverage_factor"]
    _need(_result._number(factor) and factor > 0, "coverage_factor_invalid", "policy.coverage_factor")
    _evidence(value["coverage_factor_evidence_refs"], "policy.coverage_factor_evidence_refs")
    _need(value["correlation_assumption"] == "uncorrelated", "correlation_unconfirmed", "policy.correlation_assumption")
    _evidence(value["correlation_evidence_refs"], "policy.correlation_evidence_refs")
    return Fraction(str(factor))


def _sqrt(value):
    context = Context(prec=4096, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                      capitals=1, clamp=0, flags=[], traps=[InvalidOperation, DivisionByZero, Overflow, Inexact, Rounded])
    with localcontext(context):
        exact = Decimal(value.numerator) / Decimal(value.denominator)
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                             capitals=1, clamp=0, flags=[], traps=[InvalidOperation, DivisionByZero, Overflow])):
        return exact.sqrt()


def _combine(squared, factor):
    try:
        standard, expanded = _sqrt(squared), _sqrt(squared * factor ** 2)
        standard_float, expanded_float = float(standard), float(expanded)
        _need(_result._number(standard_float) and _result._number(expanded_float)
              and (squared == 0 or standard_float > 0 and expanded_float > 0), "numeric_range", "budget")
    except (DecimalException, OverflowError, ValueError) as error:
        if type(error) is _Hold:
            raise
        raise _Hold("numeric_range", "budget") from None
    return standard, expanded, standard_float, expanded_float


def _withhold(output, code, field, detail=None):
    output["status"] = "not_assessed"
    output["budget"] = dict.fromkeys(output["budget"])
    output["trace"]["terms"] = []
    output["trace"].update(dict.fromkeys(_COMPUTED))
    output["reasons"].append(dict(code=code, field=field, detail=detail))


def build_conducted_uncertainty_budget(result, *, components, policy):
    """Combine supplied standard contributions only; never apply them to result."""
    output, stage = _base(), "input"
    try:
        _nonfinite(components, policy)
        copied = _result._snapshot(dict(result=result, components=components, policy=policy))
        _need(len(_result._canonical(copied)) <= MAX_INPUT_BYTES, "input_limit", "input")
        for key, value in copied.items():
            if value is not None:
                output["bindings"][key + "_sha256"] = _result._sha(value)
        result, components, policy = (copied[key] for key in ("result", "components", "policy"))
        _need(len(_result._canonical(dict(components=components, policy=policy))) <= MAX_METADATA_BYTES,
              "metadata_limit", "components/policy")
        output["trace"].update(provided_components=components, provided_policy=policy)
        stage = "result"
        plan, _ = _comparison._twin(result)
        output["scope"] = dict(method_id=plan["method_id"], method_version=plan["method_version"],
            metric="on", quantity="on_average", reference_plane="source_output", measurement_unit="dBm",
            uncertainty_unit="dB", source_settings=plan["source_settings"])
        stage = "components"
        terms, squared = _components(components, plan)
        stage = "policy"
        factor = _policy(policy)
        stage = "arithmetic"
        standard, expanded, standard_float, expanded_float = _combine(squared, factor)
        output["budget"] = dict(combined_standard_uncertainty_db=standard_float, expanded_uncertainty_db=expanded_float)
        output["trace"].update(terms=terms, sum_of_squares_rational_db2=str(squared),
            coverage_factor_rational=str(factor), combined_standard_uncertainty_decimal_db=format(standard, "G"),
            expanded_uncertainty_decimal_db=format(expanded, "G"))
        output["status"], stage = "calculated", "output"
        _need(len(_result._canonical(output)) <= MAX_OUTPUT_BYTES, "output_limit", "output")
    except _Hold as error:
        _withhold(output, error.code, error.field, error.detail)
    except _comparison._Hold as error:
        code = error.code.replace("twin_result_", "result_").replace("twin_binding_invalid", "result_binding_invalid")
        _withhold(output, code, error.field.replace("twin_result", "result"), error.detail)
    except _result._Failure as error:
        _withhold(output, "input_limit" if error.code == "input_limit" else "input_invalid", stage)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        _withhold(output, "output_invalid" if stage == "output" else "input_invalid", stage)
    return output
