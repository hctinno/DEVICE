"""Bridge a matched current/artifact readback to the existing supplied comparison."""
from . import intake_conducted_artifact_readback as _readback
from .virtual_fleet import conducted_twin_comparison as _comparison
from .virtual_fleet import conducted_twin_comparison_cli as _delivery
from .virtual_fleet import conducted_twin_result as _native

__all__ = ["compare_current_conducted_artifact", "IntakeConductedArtifactComparisonError"]
MAX_READBACK_BYTES = _readback.MAX_OUTPUT_BYTES
MAX_COMPARISON_BYTES = _comparison.MAX_OUTPUT_BYTES
MAX_OUTPUT_BYTES = 13 * 1024 * 1024
_PREFIX = "intake_conducted_artifact_comparison_"
_CODES = frozenset(_PREFIX + code for code in ("parent_invalid", "output_limit"))
_READBACK_KEYS = frozenset("schema_version kind status current artifact relation verification".split())
_RELATION_KEYS = frozenset("status current_binding artifact_binding fields recheck reasons".split())
_READBACK_STATUS = ("matched", "blocked", "different_intake", "different_plan", "stale")


class IntakeConductedArtifactComparisonError(RuntimeError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + "parent_invalid"
        super().__init__(self.code)


def _need(condition, code="parent_invalid"):
    if not condition:
        raise IntakeConductedArtifactComparisonError(_PREFIX + code)


def _checked_readback(value):
    """Validate only a returned parent DTO; never catch the parent call itself."""
    try:
        _readback._raw(value, MAX_READBACK_BYTES)
        _need(type(value) is dict and set(value) == _READBACK_KEYS
              and type(value["schema_version"]) is int and value["schema_version"] == 1
              and value["kind"] == "intake_conducted_artifact_readback"
              and type(value["status"]) is str and value["status"] in _READBACK_STATUS)
        relation, verification = value["relation"], value["verification"]
        _need(type(relation) is dict and set(relation) == _RELATION_KEYS
              and relation["status"] == value["status"] and type(relation["reasons"]) is list
              and type(verification) is dict and all(verification.get(key) is False for key in (
                  "execution_authority", "rerun_authority", "physical_verified", "business_writes", "permanent_current_approval")))
        if value["status"] == "matched":
            _need(type(value["artifact"]) is dict and type(value["artifact"].get("result")) is dict)
    except (_readback.IntakeConductedArtifactReadbackError, ValueError, TypeError, KeyError,
            UnicodeError, RecursionError, OverflowError):
        raise IntakeConductedArtifactComparisonError(_PREFIX + "parent_invalid") from None


def _checked_comparison(value):
    """Reuse the existing original comparison delivery contract and cap."""
    try:
        raw, _ = _delivery._wire(value, _comparison, _native)
        _need(len(raw) - 1 <= MAX_COMPARISON_BYTES)
    except (_delivery._Failure, _native._Failure, ValueError, TypeError, KeyError,
            UnicodeError, RecursionError, OverflowError):
        raise IntakeConductedArtifactComparisonError(_PREFIX + "parent_invalid") from None


def compare_current_conducted_artifact(workspace, intake_id, *, method, expected_revision, expected_context_sha256,
        artifact_workspace_root, artifact_name, expected_manifest_sha256, expected_result_sha256, run_id,
        runtime_instance_id, reference=None, comparator_policy=None, lineage=None):
    """Keep original parents; no reference/default/lineage creation or retry."""
    readback = _readback.read_current_conducted_artifact(workspace, intake_id, method=method,
        expected_revision=expected_revision, expected_context_sha256=expected_context_sha256,
        artifact_workspace_root=artifact_workspace_root, artifact_name=artifact_name,
        expected_manifest_sha256=expected_manifest_sha256, expected_result_sha256=expected_result_sha256,
        run_id=run_id, runtime_instance_id=runtime_instance_id)
    _checked_readback(readback)
    comparison = None
    status = "blocked"
    if readback["status"] == "matched":
        comparison = _comparison.compare_conducted_twin_result(readback["artifact"]["result"], reference,
            comparator_policy=comparator_policy, lineage=lineage)
        _checked_comparison(comparison)
        status = comparison["status"]
    output = dict(schema_version=1, kind="intake_conducted_artifact_comparison", status=status,
        readback=readback, comparison=comparison,
        reasons=dict(readback=readback["relation"]["reasons"], comparison=None if comparison is None else comparison["reasons"]),
        verification=dict(scope="current_readback_and_provided_comparison_only", readback_calls=1,
            comparison_calls=0 if comparison is None else 1, metadata_authenticity="unknown",
            method_approval="not_assessed", regulatory="not_assessed", hardware_verified=False,
            physical_verified=False, model_execution_verified=False, execution_authority=False, rerun_authority=False))
    _need(len(_native._canonical(output)) <= MAX_OUTPUT_BYTES, "output_limit")
    return output
