"""Read only one explicitly pinned fixed-three artifact; no execution or repair."""
import hashlib
import json
import os

from .. import control_packet_prepare as _native
from . import conducted_result_artifact as _writer
from . import conducted_twin_result as _result
from . import rf_signal_waveform_observation_read as _cleanup

MAX_RESULT_FILE_BYTES = _writer.MAX_RESULT_BYTES + 1
MAX_MANIFEST_BYTES = _writer.MAX_MANIFEST_BYTES
MAX_DRAFT_BYTES = _writer.MAX_DRAFT_BYTES
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
_PREFIX = "conducted_result_artifact_read_"
_CODES = frozenset(_PREFIX + code for code in (
    "invalid_argument", "path_invalid", "unsupported_platform", "not_found", "incomplete",
    "evidence_invalid", "binding_invalid", "input_changed", "unavailable"))
_MANIFEST = set("schema_version kind artifact_name run_id runtime_instance_id result_sha256 result_status files verification execution_authority".split())
_ROW = {"path", "bytes", "sha256", "media_type"}
_FILES = (("result.json", "application/json", MAX_RESULT_FILE_BYTES), ("draft.md", "text/markdown", MAX_DRAFT_BYTES))
_DRAFT_PREFIX = "# Conducted result DRAFT\n\nProvided synthetic snapshot. Storage completion is not conformity PASS.\n"


class ConductedResultArtifactReadError(RuntimeError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + "unavailable"
        super().__init__(self.code)


def _need(condition, code):
    if not condition:
        raise ConductedResultArtifactReadError(_PREFIX + code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _hash(value):
    return type(value) is str and bool(_writer._HASH.fullmatch(value))


def _arguments(root, name, manifest_hash, result_hash, run_id, runtime_id):
    _need(type(name) is str and _writer._NAME.fullmatch(name) and _native._valid_segment(name)
          and _hash(manifest_hash) and _hash(result_hash) and _writer._opaque(run_id) and _writer._opaque(runtime_id),
          "invalid_argument")
    try:
        lexical = _native.Path(os.fspath(root))
        parts = lexical.parts[1:] if lexical.anchor else lexical.parts
        _need(all(_native._valid_segment(part) for part in parts), "path_invalid")
        return _native._local_path(root)
    except (TypeError, ValueError):
        raise ConductedResultArtifactReadError(_PREFIX + "path_invalid") from None


def _unique(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "evidence_invalid")
        value[key] = item
    return value


def _constant(value):
    _need(False, "evidence_invalid")


def _parse(raw):
    try:
        _need(not raw.startswith(b"\xef\xbb\xbf"), "evidence_invalid")
        value = _result._snapshot(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant))
        _need(raw == _result._canonical(value) + b"\n", "evidence_invalid")
        return value
    except (ValueError, TypeError, RecursionError, UnicodeError, _result._Failure):
        raise ConductedResultArtifactReadError(_PREFIX + "evidence_invalid") from None


def _same(tree, pin):
    path, descriptor, stamp, raw = pin
    _need(_native._stamp(tree.file_stat(path)) == stamp
          and _native._stamp(tree.backend.info(descriptor, directory=False)) == stamp, "input_changed")


def _open(tree, path, limit):
    stamp = _native._stamp(tree.file_stat(path))
    _need(0 <= stamp[2] <= limit, "evidence_invalid")
    descriptor = tree.backend.open_read(path, pin=True)
    pin = (path, descriptor, stamp, None)
    _same(tree, pin)
    raw = _native._read_descriptor(descriptor, limit, "packet_prepare_source_changed")
    _need(len(raw) == stamp[2], "input_changed")
    _same(tree, pin)
    return path, descriptor, stamp, raw


def _manifest(value, name, result_hash, run_id, runtime_id):
    _need(type(value) is dict and set(value) == _MANIFEST
          and type(value["schema_version"]) is int and value["schema_version"] == 1
          and value["kind"] == "conducted_result_artifact_manifest"
          and value["artifact_name"] == name and value["execution_authority"] is False
          and value["result_status"] in ("recorded", "incomplete", "invalid")
          and _result._canonical(value["verification"]) in (
              _result._canonical(_writer._verification("full_bound")),
              _result._canonical(_writer._verification("report_ids_only"))),
          "evidence_invalid")
    _need(value["verification"]["binding_scope"] == "full_bound", "binding_invalid")
    _need(value["result_sha256"] == result_hash and value["run_id"] == run_id
          and value["runtime_instance_id"] == runtime_id, "binding_invalid")
    _need(type(value["files"]) is list and len(value["files"]) == 2, "evidence_invalid")
    for row, (path, media, cap) in zip(value["files"], _FILES):
        _need(type(row) is dict and set(row) == _ROW and row["path"] == path and row["media_type"] == media
              and type(row["bytes"]) is int and 0 < row["bytes"] <= cap and _hash(row["sha256"]), "evidence_invalid")


def _post(tree, pins):
    for pin in pins:
        _same(tree, pin)
        _need(_native._read_descriptor(pin[1], len(pin[3]), "packet_prepare_source_changed") == pin[3], "input_changed")
        _same(tree, pin)


def _public(error, stage):
    if not isinstance(error, Exception) or isinstance(error, MemoryError):
        return error
    if type(error) is ConductedResultArtifactReadError:
        return error
    if stage == "post":
        code = "input_changed"
    elif type(error) is _native.ControlPacketPrepareError and error.code in ("packet_prepare_path_invalid", "packet_prepare_invalid_argument"):
        code = "path_invalid"
    elif isinstance(error, FileNotFoundError):
        code = "incomplete" if stage == "payload" else "not_found"
    elif isinstance(error, NotImplementedError):
        code = "unsupported_platform"
    elif stage == "binding" and type(error) in (_writer.ConductedResultArtifactError, _result._Failure, ValueError, TypeError, KeyError):
        code = "binding_invalid"
    else:
        code = "unavailable"
    return ConductedResultArtifactReadError(_PREFIX + code)


def read_conducted_result_artifact(*, workspace_root, artifact_name, expected_manifest_sha256,
                                  expected_result_sha256, run_id, runtime_instance_id):
    """Return file snapshots after verified readback and known native cleanup."""
    backend = tree = output = primary = None
    stage = "arguments"
    try:
        root = _arguments(workspace_root, artifact_name, expected_manifest_sha256,
                          expected_result_sha256, run_id, runtime_instance_id)
        _need(_native._WINDOWS_BACKEND_AVAILABLE, "unsupported_platform")
        stage = "environment"
        backend = _native._WindowsIO()
        tree = _native._Tree(root, backend)
        folder = root / ".local/conducted-result-artifacts" / artifact_name
        tree.directory(folder)
        stage = "marker"
        marker = _open(tree, folder / "manifest.json", MAX_MANIFEST_BYTES)
        _need(_sha(marker[3]) == expected_manifest_sha256, "evidence_invalid")
        manifest = _parse(marker[3])
        _manifest(manifest, artifact_name, expected_result_sha256, run_id, runtime_instance_id)
        pins = [marker]
        stage = "payload"
        for row, (name, media, cap) in zip(manifest["files"], _FILES):
            pin = _open(tree, folder / name, cap)
            _need(len(pin[3]) == row["bytes"] and _sha(pin[3]) == row["sha256"], "evidence_invalid")
            pins.append(pin)
        result = _parse(pins[1][3])
        stage = "binding"
        result, original_raw, scope = _writer._input(result, artifact_name, expected_result_sha256, run_id, runtime_instance_id)
        _need(scope == "full_bound" and original_raw == pins[1][3]
              and result["status"] == manifest["result_status"], "binding_invalid")
        _result._plan(result["binding"]["plan_input"])
        stage = "draft"
        try:
            draft = pins[2][3].decode("utf-8")
        except UnicodeError:
            raise ConductedResultArtifactReadError(_PREFIX + "evidence_invalid") from None
        _need(draft.startswith(_DRAFT_PREFIX), "evidence_invalid")
        stage = "post"
        _post(tree, pins)
        output = dict(schema_version=1, kind="conducted_result_artifact_read",
            selection=dict(artifact_name=artifact_name, expected_manifest_sha256=expected_manifest_sha256,
                expected_result_sha256=expected_result_sha256, run_id=run_id, runtime_instance_id=runtime_instance_id),
            storage=dict(status="manifest_payloads_verified", completion_marker="manifest.json",
                manifest_sha256=_sha(marker[3]), result_sha256=expected_result_sha256, draft_sha256=_sha(pins[2][3]),
                verified_file_count=3, binding_scope="full_bound"), result=result, manifest=manifest, draft=draft,
            verification=dict(source_references="not_opened", current_binding="caller_provided_hashes_and_ids_only",
                historical_publication_order="not_verified", writer_outcome="not_verified", draft_content="not_interpreted",
                hardware_verified=False, physical_verified=False, source_authenticity_verified=False,
                method_approval="not_assessed", conformity_status="not_assessed", issuance_approval="not_assessed",
                execution_authority=False, rerun_authority=False))
        stage = "output"
        _need(len(_result._canonical(output)) <= MAX_OUTPUT_BYTES, "evidence_invalid")
    except BaseException as error:
        primary = _public(error, stage)
    finally:
        if backend is not None:
            try:
                closing = _cleanup._close(backend)
            except BaseException as error:
                closing = error
            if primary is None and closing is not None:
                primary = _public(closing, "cleanup")
    if primary is not None:
        raise primary from None
    return output
