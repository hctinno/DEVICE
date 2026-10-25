"""Relate current provided facts to one pinned stored artifact, then reread current."""
import hashlib

from . import intake_current_facts_plan as _current
from . import intake_conducted_twin_plan as _plan
from .store import canonical
from .ui_read_model import IntakeReadModel, ReadModelError
from .virtual_fleet import conducted_result_artifact_read as _reader
from .virtual_fleet import conducted_twin_result as _dto

__all__ = ["read_current_conducted_artifact", "IntakeConductedArtifactReadbackError"]
MAX_CURRENT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 12 * 1024 * 1024
_BINDING = "intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256".split()
_PREFIX = "intake_conducted_artifact_readback_"
_CODES = frozenset(_PREFIX + code for code in ("parent_invalid", "input_limit", "current_recheck_failed"))


class IntakeConductedArtifactReadbackError(RuntimeError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + "parent_invalid"
        super().__init__(self.code)


def _need(condition, code="parent_invalid"):
    if not condition:
        raise IntakeConductedArtifactReadbackError(_PREFIX + code)


def _raw(value, limit):
    try:
        _dto._snapshot(value)
        raw = canonical(value).encode("utf-8")
    except _dto._Failure as error:
        _need(False, "input_limit" if error.code == "input_limit" else "parent_invalid")
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        _need(False)
    _need(len(raw) <= limit, "input_limit")
    return raw


def _sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _binding(value):
    _need(type(value) is dict and set(value) == set(_BINDING))
    _need(type(value["intake_id"]) is str and bool(value["intake_id"])
          and type(value["revision"]) is int and value["revision"] > 0
          and all(type(value[key]) is str and _plan._SHA.fullmatch(value[key]) for key in _BINDING[2:]))
    return {key: value[key] for key in _BINDING}


def _current_value(value, intake_id):
    _raw(value, MAX_CURRENT_BYTES)
    _need(type(value) is dict and set(value) == {"context", "analysis", "facts_plan"}
          and type(value["context"]) is dict and set(value["context"]) == _plan._PUBLIC
          and type(value["analysis"]) is dict and value["context"]["intake_id"] == intake_id)
    facts = value["facts_plan"]
    _need(type(facts) is dict and set(facts) == {"schema_version", "kind", "status", "plan_input", "assembly_gaps", "questions"}
          and type(facts["schema_version"]) is int and facts["schema_version"] == 1
          and facts["kind"] == "intake_facts_to_conducted_plan" and facts["status"] in ("ready_for_simulation", "blocked"))
    plan = facts["plan_input"]
    _need(type(plan) is dict and set(plan) == set(_plan._result()) and plan["status"] == facts["status"]
          and type(plan["schema_version"]) is int and plan["schema_version"] == 1
          and plan["kind"] == "intake_conducted_twin_plan_input"
          and type(plan["verification"]) is dict and plan["verification"].get("execution_authority") is False
          and type(plan["binding"]) is dict and set(plan["binding"]) == set(_BINDING))
    binding = {key: plan["binding"][key] for key in _BINDING}
    if facts["status"] == "ready_for_simulation":
        _binding(binding)
        _need(binding["intake_id"] == intake_id and binding["revision"] == value["context"]["revision"]
              and binding["analysis_context_id"] == value["context"]["analysis_context_id"]
              and binding["context_sha256"] == _sha(value["context"])
              and binding["analysis_sha256"] == _sha(value["analysis"])
              and binding["plan_sha256"] == _sha(plan["plan"]))
    return binding


def _artifact_value(value, selection):
    _raw(value, MAX_ARTIFACT_BYTES)
    _need(type(value) is dict and set(value) == {"schema_version", "kind", "selection", "storage", "result", "manifest", "draft", "verification"}
          and type(value["schema_version"]) is int and value["schema_version"] == 1
          and value["kind"] == "conducted_result_artifact_read" and canonical(value["selection"]) == canonical(selection)
          and type(value["storage"]) is dict and value["storage"].get("status") == "manifest_payloads_verified"
          and value["storage"].get("binding_scope") == "full_bound"
          and type(value["verification"]) is dict and value["verification"].get("execution_authority") is False
          and value["verification"].get("physical_verified") is False)
    try:
        return _binding(value["result"]["binding"]["plan_input"]["binding"])
    except (KeyError, TypeError):
        _need(False)


def read_current_conducted_artifact(workspace, intake_id, *, method, expected_revision, expected_context_sha256,
        artifact_workspace_root, artifact_name, expected_manifest_sha256, expected_result_sha256, run_id, runtime_instance_id):
    """Binding relation only; original parents retained, no current-completion grant."""
    current = _current.read_current_conducted_plan_from_facts(workspace, intake_id, method=method,
        expected_revision=expected_revision, expected_context_sha256=expected_context_sha256)
    current_binding = _current_value(current, intake_id)
    before_context = _sha(current["context"])
    before_analysis = _sha(current["analysis"])
    artifact = artifact_binding = None
    fields = dict.fromkeys(_BINDING)
    reasons = []
    status = "matched"
    if expected_revision is None or expected_context_sha256 is None:
        reasons.append("current_pin_missing")
        status = "blocked"
    if current["facts_plan"]["status"] != "ready_for_simulation":
        reasons.append("current_plan_blocked")
        status = "blocked"
    if status != "blocked":
        _need(type(expected_revision) is int and expected_revision == current_binding["revision"]
              and type(expected_context_sha256) is str and expected_context_sha256 == before_context)
        selection = dict(artifact_name=artifact_name, expected_manifest_sha256=expected_manifest_sha256,
            expected_result_sha256=expected_result_sha256, run_id=run_id, runtime_instance_id=runtime_instance_id)
        artifact = _reader.read_conducted_result_artifact(workspace_root=artifact_workspace_root, **selection)
        artifact_binding = _artifact_value(artifact, selection)
        fields = {key: canonical(current_binding[key]) == canonical(artifact_binding[key]) for key in _BINDING}
        reasons.extend("artifact_" + key + "_mismatch" for key in _BINDING if not fields[key])
        if not fields["intake_id"]:
            status = "different_intake"
        elif not all(fields.values()):
            status = "different_plan"
    try:
        post = IntakeReadModel(workspace).current_conducted_plan_context(intake_id)
    except ReadModelError:
        raise IntakeConductedArtifactReadbackError(_PREFIX + "current_recheck_failed") from None
    _raw(post, MAX_CURRENT_BYTES)
    _need(type(post) is dict and set(post) == {"context", "analysis"}
          and type(post["context"]) is dict and set(post["context"]) == _plan._PUBLIC and type(post["analysis"]) is dict)
    after_context, after_analysis = _sha(post["context"]), _sha(post["analysis"])
    if after_context != before_context:
        reasons.append("current_context_changed")
        status = "stale"
    if after_analysis != before_analysis:
        reasons.append("current_analysis_changed")
        status = "stale"
    output = dict(schema_version=1, kind="intake_conducted_artifact_readback", status=status, current=current, artifact=artifact,
        relation=dict(status=status, current_binding=current_binding, artifact_binding=artifact_binding, fields=fields,
            recheck=dict(status="unchanged" if after_context == before_context and after_analysis == before_analysis else "changed",
                context_sha256_before=before_context, context_sha256_after=after_context,
                analysis_sha256_before=before_analysis, analysis_sha256_after=after_analysis), reasons=reasons),
        verification=dict(scope="two_readonly_current_snapshots_and_provided_artifact_pins", current_completion="not_assessed",
            permanent_current_approval=False, method_approval="not_assessed", regulatory="not_assessed", physical_verified=False,
            execution_authority=False, rerun_authority=False, business_writes=False, artifact_history="reader_scope_only"))
    _need(len(canonical(output).encode("utf-8")) <= MAX_OUTPUT_BYTES, "input_limit")
    return output
