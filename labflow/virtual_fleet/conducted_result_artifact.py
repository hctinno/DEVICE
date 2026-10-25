"""Write one provided synthetic result to a new private native artifact; no execution."""
import hashlib
import json
import re

from .. import control_packet_prepare as _native
from . import conducted_twin_result as _result
from .journal import _identifier
from .rf_signal_waveform_observation import _close_owned

MAX_RESULT_BYTES = 1024 * 1024
MAX_DRAFT_BYTES = 256 * 1024
MAX_MANIFEST_BYTES = 8 * 1024
MAX_FAILURE_BYTES = 4 * 1024
_PREFIX = "conducted_result_artifact_"
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_TOP = set("schema_version kind status binding raw_measurement setup_provenance calculation gaps failure verification".split())
_BINDING = set("plan_input run_report plan_input_sha256 setup_sha256 journal_file_sha256 journal_head_sha256 report_sha256 topology_sha256 run_id runtime_instance_id measurement_ref".split())
_CODES = frozenset(_PREFIX + suffix for suffix in (
    "invalid_argument", "result_input_invalid", "result_too_large", "result_hash_mismatch",
    "unbound_result", "run_binding_mismatch", "draft_too_large", "destination_exists",
    "path_invalid", "unsupported_platform", "write_failed", "publication_uncertain"))


class ConductedResultArtifactError(RuntimeError):
    """Fixed code and observed phase; no source path, body or native exception text."""
    def __init__(self, code, *, phase="preflight", publication_attempted=False):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + "write_failed"
        self.phase, self.publication_attempted = phase, bool(publication_attempted)
        super().__init__(self.code)


def _reject(condition, suffix):
    if not condition:
        raise ConductedResultArtifactError(_PREFIX + suffix)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _opaque(value):
    if type(value) is not str:
        return False
    try:
        return _identifier(value) == value
    except ValueError:
        return False


def _binding(result, run_id, runtime_id):
    binding = result["binding"]
    _reject(type(binding) is dict and set(binding) in ({"plan_input", "run_report"}, _BINDING),
            "unbound_result")
    plan, report = binding["plan_input"], binding["run_report"]
    _reject(type(plan) is dict and plan.get("kind") == "intake_conducted_twin_plan_input"
            and type(plan.get("schema_version")) is int and plan["schema_version"] == 1
            and type(plan.get("binding")) is dict and type(plan.get("plan")) is dict, "unbound_result")
    pins = plan["binding"]
    _reject(type(pins.get("intake_id")) is str and bool(pins["intake_id"])
            and type(pins.get("revision")) is int and pins["revision"] > 0
            and type(pins.get("plan_sha256")) is str and _HASH.fullmatch(pins["plan_sha256"])
            and pins["plan_sha256"] == _sha(_result._canonical(plan["plan"])), "unbound_result")
    _reject(type(report) is dict and _opaque(report.get("run_id"))
            and _opaque(report.get("runtime_instance_id")), "unbound_result")
    _reject(report["run_id"] == run_id and report["runtime_instance_id"] == runtime_id, "run_binding_mismatch")
    if set(binding) == {"plan_input", "run_report"}:
        _reject(result["status"] in ("incomplete", "invalid") and result["failure"] is not None, "unbound_result")
        return "report_ids_only"
    _reject(_opaque(binding["run_id"]) and _opaque(binding["runtime_instance_id"]), "unbound_result")
    _reject(binding["run_id"] == run_id and binding["runtime_instance_id"] == runtime_id, "run_binding_mismatch")
    hashes = ("plan_input_sha256", "setup_sha256", "journal_file_sha256", "journal_head_sha256",
              "report_sha256", "topology_sha256")
    _reject(all(type(binding[key]) is str and _HASH.fullmatch(binding[key]) for key in hashes)
            and _opaque(binding["measurement_ref"]), "result_input_invalid")
    _reject(binding["plan_input_sha256"] == _sha(_result._canonical(plan))
            and binding["report_sha256"] == _sha(_result._canonical(report)), "result_input_invalid")
    try:
        _result._harness_payload(report)
    except (ValueError, TypeError, OverflowError):
        raise ConductedResultArtifactError(_PREFIX + "result_input_invalid") from None
    return "full_bound"


def _input(result, name, expected_hash, run_id, runtime_id):
    _reject(type(name) is str and _NAME.fullmatch(name) and _native._valid_segment(name), "invalid_argument")
    _reject(type(expected_hash) is str and _HASH.fullmatch(expected_hash)
            and _opaque(run_id) and _opaque(runtime_id), "invalid_argument")
    try:
        result = _result._snapshot(result)
    except MemoryError:
        raise
    except Exception:
        raise ConductedResultArtifactError(_PREFIX + "result_input_invalid") from None
    raw = _result._canonical(result)
    _reject(len(raw) <= MAX_RESULT_BYTES, "result_too_large")
    _reject(type(result) is dict and set(result) == _TOP and type(result["schema_version"]) is int
            and result["schema_version"] == 1 and result["kind"] == "conducted_twin_result"
            and type(result["status"]) is str and result["status"] in ("recorded", "incomplete", "invalid"),
            "result_input_invalid")
    template = _result._base()
    _reject(type(result["verification"]) is dict and result["verification"] == template["verification"]
            and all(result["verification"][key] is template["verification"][key]
                    for key in ("synthetic", "hardware_verified", "physical_verified", "execution_authority")),
            "result_input_invalid")
    calculation = result["calculation"]
    _reject(type(calculation) is dict and set(calculation) == set(template["calculation"])
            and type(calculation["correction_ledger"]) is list
            and type(calculation["conformity"]) is dict
            and calculation["conformity"] == template["calculation"]["conformity"]
            and all(calculation["conformity"][key] is None
                    for key in ("verdict", "numeric_limit_dbm", "uncertainty_db")), "result_input_invalid")
    setup, failure = result["setup_provenance"], result["failure"]
    _reject(type(setup) is dict and set(setup) == {"records", "topology", "path"}
            and type(setup["path"]) is list and type(result["gaps"]) is list, "result_input_invalid")
    _reject(failure is None or type(failure) is dict and set(failure) == {"code", "field"}
            and all(type(failure[key]) is str and bool(failure[key]) for key in failure), "result_input_invalid")
    _reject(result["status"] != "recorded" or failure is None, "result_input_invalid")
    _reject(result["raw_measurement"] is None or type(result["raw_measurement"]) is dict
            and set(result["raw_measurement"]) == {"packet", "event_id", "sequence", "device_id", "tick",
                "setup_revision", "quantity", "reference_plane"}, "result_input_invalid")
    _reject(_sha(raw) == expected_hash, "result_hash_mismatch")
    return result, raw + b"\n", _binding(result, run_id, runtime_id)


def _verification(scope):
    return dict(report_status="DRAFT", binding_scope=scope, data_origin="provided_synthetic_result",
                storage_hashes_verified=True, hardware_verified=False, physical_verified=False,
                method_approval="not_assessed", conformity_status="not_assessed",
                execution_authorized=False, rerun_authorized=False)


def _draft(result, result_hash, run_id, runtime_id, scope):
    binding = result["binding"]
    refs = {key: value for key, value in binding.items() if key not in ("plan_input", "run_report")}
    metadata = dict(result_status=result["status"], run_id=run_id, runtime_instance_id=runtime_id,
                    result_sha256=result_hash, binding_scope=scope, execution_authority=False)
    sections = (
        ("Provided result and run", metadata),
        ("Raw observation and references", dict(raw_measurement=result["raw_measurement"], binding_refs=refs)),
        ("Calculation and correction ledger", result["calculation"]),
        ("Gaps and failure", dict(gaps=result["gaps"], failure=result["failure"])),
        ("Validation scope", result["verification"]),
    )
    text = "# Conducted result DRAFT\n\nProvided synthetic snapshot. Storage completion is not conformity PASS.\n"
    text += "Full provided data is retained in result.json. No source references were opened.\n"
    for title, value in sections:
        # JSON escapes newlines inside strings; data cannot close a fence on its own line.
        body = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2)
        text += "\n## " + title + "\n\n```json\n" + body + "\n```\n"
    raw = text.encode("utf-8")
    _reject(len(raw) <= MAX_DRAFT_BYTES, "draft_too_large")
    return raw


def _verify_file(tree, path, descriptor, stamp, raw):
    if (_native._stamp(tree.backend.info(descriptor, directory=False)) != stamp
            or _native._stamp(tree.file_stat(path)) != stamp
            or _native._read_descriptor(descriptor, len(raw), "packet_prepare_receipt_failed") != raw
            or _native._stamp(tree.backend.info(descriptor, directory=False)) != stamp
            or _native._stamp(tree.file_stat(path)) != stamp):
        raise OSError("artifact verification failed")


def _persist(tree, folder, result_raw, draft_raw, manifest_raw, state):
    tree.directory(folder.parent, create=True)
    state["phase"] = "claim_destination"
    descriptor = tree.backend.directory(folder, create=True)
    state["leaf"] = (folder, descriptor, None)
    info = tree.backend.info(descriptor, directory=True)
    state["leaf"] = (folder, descriptor, (info.st_dev, info.st_ino))
    tree.directory(folder)
    published = []
    for name, raw in (("result", result_raw), ("draft", draft_raw), ("manifest", manifest_raw)):
        suffix = ".md" if name == "draft" else ".json"
        pending, final = folder / (name + ".pending" + suffix), folder / (name + suffix)
        state["phase"] = "write_" + name
        stamp = _native._write_bytes(tree, pending, raw, "packet_prepare_receipt_failed", sync=True)
        state["phase"] = "verify_" + name
        pinned = tree.backend.open_read(pending, pin=True)
        _verify_file(tree, pending, pinned, stamp, raw)
        if name == "manifest":
            for previous in published:
                _verify_file(tree, *previous)
            tree.directory(folder)
            state["publication_attempted"] = True
        state["phase"] = "publish_" + name
        tree.backend.link_receipt(pinned, final)
        state["phase"] = "verify_" + name
        final_fd = tree.backend.open_read(final, pin=True)
        _verify_file(tree, final, final_fd, stamp, raw)
        published.append((final, final_fd, stamp, raw))
        if name == "manifest":
            state["manifest_verified"] = True


def _mapped(error, state):
    if isinstance(error, ConductedResultArtifactError):
        return error
    if state["publication_attempted"]:
        suffix = "publication_uncertain"
    elif isinstance(error, FileExistsError) and state["phase"] == "claim_destination":
        suffix = "destination_exists"
    elif isinstance(error, _native.ControlPacketPrepareError) and error.code == "packet_prepare_path_invalid":
        suffix = "path_invalid"
    else:
        suffix = "write_failed"
    return ConductedResultArtifactError(_PREFIX + suffix, phase=state["phase"],
                                        publication_attempted=state["publication_attempted"])


def _control(error):
    return not isinstance(error, Exception) or isinstance(error, MemoryError)


def _failure_marker(tree, state, primary, request):
    leaf = state["leaf"]
    if tree is None or leaf is None or leaf[2] is None:
        return
    try:
        folder, descriptor, identity = leaf
        if tree.backend.directories.get(folder) != descriptor:
            return
        info = tree.backend.info(descriptor, directory=True)
        if (info.st_dev, info.st_ino) != identity:
            return
        tree.directory(folder)
        value = dict(schema_version=1, kind="conducted_result_artifact_failure",
            status="interrupted" if _control(primary) else "failed", phase=state["phase"],
            error_code=None if _control(primary) else primary.code,
            publication_attempted=state["publication_attempted"], manifest_verified=state["manifest_verified"],
            run_id=request["run_id"], runtime_instance_id=request["runtime_instance_id"],
            result_sha256=request["result_sha256"], execution_authority=False)
        raw = _result._canonical(value) + b"\n"
        if len(raw) <= MAX_FAILURE_BYTES:
            _native._write_bytes(tree, folder / "failure.json", raw, "packet_prepare_receipt_failed", sync=True)
    except BaseException:
        # Secondary marker failures never replace the first observed outcome.
        pass


def write_conducted_result_artifact(result, *, workspace_root, artifact_name,
                                   expected_result_sha256, run_id, runtime_instance_id):
    """New-leaf only. Marker commits storage hashes, never measurement authority."""
    backend, tree, summary, primary = None, None, None, None
    state = dict(phase="preflight", leaf=None, publication_attempted=False, manifest_verified=False)
    request = dict(run_id=run_id, runtime_instance_id=runtime_instance_id, result_sha256=expected_result_sha256)
    try:
        result, result_raw, scope = _input(result, artifact_name, expected_result_sha256, run_id, runtime_instance_id)
        draft_raw = _draft(result, expected_result_sha256, run_id, runtime_instance_id, scope)
        files = [dict(path="result.json", bytes=len(result_raw), sha256=_sha(result_raw), media_type="application/json"),
                 dict(path="draft.md", bytes=len(draft_raw), sha256=_sha(draft_raw), media_type="text/markdown")]
        verification = _verification(scope)
        manifest = dict(schema_version=1, kind="conducted_result_artifact_manifest", artifact_name=artifact_name,
            run_id=run_id, runtime_instance_id=runtime_instance_id, result_sha256=expected_result_sha256,
            result_status=result["status"], files=files, verification=verification, execution_authority=False)
        manifest_raw = _result._canonical(manifest) + b"\n"
        _reject(len(manifest_raw) <= MAX_MANIFEST_BYTES, "result_input_invalid")
        root = _native._local_path(workspace_root)
        _reject(_native._WINDOWS_BACKEND_AVAILABLE, "unsupported_platform")
        state["phase"] = "environment_preflight"
        backend = _native._WindowsIO()
        tree = _native._Tree(root, backend)
        folder = root / ".local/conducted-result-artifacts" / artifact_name
        _persist(tree, folder, result_raw, draft_raw, manifest_raw, state)
        relative = folder.relative_to(root)
        summary = dict(schema_version=1, kind="conducted_result_artifact", artifact_name=artifact_name,
            run_id=run_id, runtime_instance_id=runtime_instance_id, result_status=result["status"],
            storage=dict(status="complete", commit_marker=(relative / "manifest.json").as_posix(),
                         bytes=len(manifest_raw), sha256=_sha(manifest_raw)),
            files=[{**row, "path": (relative / row["path"]).as_posix()} for row in files],
            verification=verification, execution_authority=False)
    except BaseException as error:
        primary = error if _control(error) else _mapped(error, state)
    finally:
        if backend is not None:
            if primary is not None:
                _failure_marker(tree, state, primary, request)
            else:
                state["phase"] = "cleanup"
            try:
                closing = _close_owned(backend)
            except BaseException as error:
                closing = error
            if primary is None and closing is not None:
                primary = closing if _control(closing) else _mapped(closing, state)
                _failure_marker(tree, state, primary, request)
    if primary is not None:
        raise primary from None
    return summary
