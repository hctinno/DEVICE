"""Deliver one explicit current/artifact readback; no execution or approval."""
import os
import sys

from . import control_packet_prepare as _native
from . import intake_conducted_artifact_readback as _parent
from .ui_read_model import ReadModelError
from .virtual_fleet import conducted_result_artifact_read as _reader
from .virtual_fleet import conducted_twin_result as _dto
from .virtual_fleet import conducted_twin_comparison_cli as _shared
from .virtual_fleet import rf_signal_waveform_observation_read as _cleanup
from .virtual_fleet.rf_signal_read_cli import _json, _write

MAX_INPUT_BYTES = 64 * 1024
MAX_INPUT_DEPTH = 8
MAX_INPUT_NODES = 2048
MAX_OUTPUT_BYTES = 12 * 1024 * 1024
_PREFIX = "intake_conducted_artifact_readback_cli_"
_FLAGS = ("--workspace", "--intake-id", "--readback-json")
_KEYS = frozenset("method expected_revision expected_context_sha256 artifact_workspace_root artifact_name "
                  "expected_manifest_sha256 expected_result_sha256 run_id runtime_instance_id".split())
_OUTPUT_KEYS = frozenset("schema_version kind status current artifact relation verification".split())
_STATUS = dict(matched=0, blocked=2, different_intake=2, different_plan=2, stale=2)
_CODES = frozenset("invalid_argument path_invalid not_found input_limit json_invalid input_changed unavailable output_failed interrupted".split())
_READ_MODEL_CODES = frozenset("store_missing store_unavailable intake_not_found "
    "intake_conducted_preview_invalid_request intake_conducted_preview_synthetic_required "
    "intake_conducted_preview_analysis_unavailable intake_conducted_preview_v2_pdf_required "
    "intake_conducted_preview_source_invalid".split())
_PARENT_ERRORS = ((_parent.IntakeConductedArtifactReadbackError, _parent._CODES),
                  (_reader.ConductedResultArtifactReadError, _reader._CODES),
                  (ReadModelError, _READ_MODEL_CODES))
_CONTROLS = (KeyboardInterrupt, MemoryError, SystemExit, GeneratorExit)
_HELP = ("\ubcf4\uc874 \uc800\uc7a5 \uc0ac\ubcf8 \uac80\uc218: one explicit current/artifact readback.\n"
    "Usage: python -B -m labflow.intake_conducted_artifact_readback_cli "
    "--workspace ABS_LOCAL_DIR --intake-id ID --readback-json ABS_LOCAL_JSON\n"
    "Each option once with a separate value; no defaults, equals syntax, UNC or relative paths.\n"
    "JSON exact9: method/expected_revision/expected_context_sha256/artifact_workspace_root/"
    "artifact_name/expected_manifest_sha256/expected_result_sha256/run_id/runtime_instance_id.\n"
    "Strict UTF-8 JSON <=64KiB, depth8/nodes2048. Original DTO7 body<=12MiB plus one LF.\n"
    "Exit: matched 0; blocked/different_intake/different_plan/stale 2; fixed typed unavailable 3; "
    "other 1; process KeyboardInterrupt 130.\n"
    "matched means a stored/current binding match, never measurement PASS or execution approval.\n"
    "No models, hardware, business writes, reruns, source repair or automatic current pin selection.\n")


class _Failure(ValueError):
    pass


def _fail(code):
    raise _Failure(code)


def _arguments(argv):
    if type(argv) not in (list, tuple) or len(argv) != 6 or any(type(item) is not str for item in argv):
        _fail("invalid_argument")
    values = {}
    for key, value in zip(argv[::2], argv[1::2]):
        if key not in _FLAGS or key in values or not value or value.startswith("--"):
            _fail("invalid_argument")
        values[key] = value
    if set(values) != set(_FLAGS):
        _fail("invalid_argument")
    return [values[key] for key in _FLAGS]


def _path(value):
    if type(value) is not str:
        _fail("path_invalid")
    lexical = _native.Path(value)
    if not lexical.is_absolute() or not all(_native._valid_segment(part) for part in lexical.parts[1:]):
        _fail("path_invalid")
    return _native._local_path(value)


def _bounded(value):
    nodes = 0
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > MAX_INPUT_DEPTH or nodes > MAX_INPUT_NODES:
            _fail("input_limit")
        if type(item) is dict:
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
    visit(value, 0)
    try:
        _dto._snapshot(value)
    except _dto._Failure:
        _fail("json_invalid")
    if type(value) is not dict or set(value) != _KEYS:
        _fail("json_invalid")
    _path(value["artifact_workspace_root"])
    return value


def _input(backend, path):
    tree = _native._Tree(path.parent, backend)
    stamp = _native._stamp(tree.file_stat(path))
    if not 0 <= stamp[2] <= MAX_INPUT_BYTES:
        _fail("input_limit")
    descriptor = backend.open_read(path, pin=True)
    pin = (tree, path, descriptor, stamp, None)
    _shared._same(_native, backend, pin)
    raw = _native._read_descriptor(descriptor, MAX_INPUT_BYTES, "packet_prepare_source_changed")
    if len(raw) != stamp[2]:
        _fail("input_changed")
    pin = (tree, path, descriptor, stamp, raw)
    _shared._same(_native, backend, pin)
    return _bounded(_shared._parse(raw)), pin


def _wire(value):
    _dto._snapshot(value)
    if (type(value) is not dict or set(value) != _OUTPUT_KEYS
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["kind"] != "intake_conducted_artifact_readback"
            or type(value["status"]) is not str or value["status"] not in _STATUS):
        _fail("unavailable")
    raw = _json(value)
    if len(raw) > MAX_OUTPUT_BYTES:
        _fail("output_failed")
    return raw + b"\n", _STATUS[value["status"]]


def _error(error, phase):
    if type(error) in (_Failure, _shared._Failure):
        code = error.args[0] if len(error.args) == 1 else None
        return (code if type(code) is str and code in _CODES else "unavailable"), 1
    if phase == "parent":
        for kind, codes in _PARENT_ERRORS:
            if type(error) is kind and type(error.code) is str and error.code in codes:
                return "unavailable", 3
    if phase == "output":
        return "output_failed", 1
    if isinstance(error, FileNotFoundError):
        return "not_found", 1
    if type(error) is _native.ControlPacketPrepareError and error.code == "packet_prepare_source_changed":
        return "input_changed", 1
    if (type(error) is _native.ControlPacketPrepareError
            and error.code in ("packet_prepare_path_invalid", "packet_prepare_invalid_argument")):
        return "path_invalid", 1
    return "unavailable", 1


def _diagnose(code):
    try:
        _write(sys.stderr, _json({"error": {"code": _PREFIX + code}}) + b"\n")
    except BaseException:
        pass


def main(argv=None) -> int:
    """Borrow streams; preserve the first control object after known cleanup."""
    backend = primary = raw = None
    phase = failed_phase = "input"
    status = 1
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if (type(arguments) in (list, tuple) and len(arguments) == 1
                and type(arguments[0]) is str and arguments[0] == "--help"):
            phase = "output"
            _write(sys.stdout, _HELP.encode("utf-8"))
            return 0
        workspace, intake_id, source = _arguments(arguments)
        _path(workspace)
        path = _path(source)
        backend = _native._WindowsIO()
        options, pin = _input(backend, path)
        phase = "parent"
        value = _parent.read_current_conducted_artifact(workspace, intake_id, **options)
        phase = "delivery"
        raw, status = _wire(value)
        _shared._recheck(_native, backend, [pin])
    except BaseException as error:
        primary, failed_phase = error, phase
    finally:
        if backend is not None:
            try:
                closing = _cleanup._close(backend)
            except BaseException as error:
                closing = error
            if primary is None and closing is not None:
                primary, failed_phase = closing, "cleanup"
    if primary is None:
        try:
            _write(sys.stdout, raw)
        except BaseException as error:
            primary, failed_phase = error, "output"
    if isinstance(primary, _CONTROLS):
        raise primary
    if primary is not None:
        code, status = _error(primary, failed_phase)
        _diagnose(code)
    return status


def _process_main():
    """Use the existing UTF-8/LF and quiet broken-pipe process boundary."""
    primary = None
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")
        except BaseException as error:
            if primary is None:
                primary = error
    if primary is None:
        try:
            status = main()
        except KeyboardInterrupt as error:
            primary = error
    if primary is not None:
        if isinstance(primary, KeyboardInterrupt):
            code, status = "interrupted", 130
        elif isinstance(primary, _CONTROLS):
            raise primary
        else:
            code, status = "output_failed", 1
        _diagnose(code)
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.flush()
        except BaseException as error:
            if status in (0, 2):
                if isinstance(error, KeyboardInterrupt):
                    code, status = "interrupted", 130
                elif isinstance(error, _CONTROLS):
                    raise error
                else:
                    code, status = "output_failed", 1
                _diagnose(code)
            try:
                target = stream.fileno()
                sink = os.open(os.devnull, os.O_WRONLY)
                try:
                    if sink != target:
                        os.dup2(sink, target)
                finally:
                    if sink != target:
                        os.close(sink)
            except BaseException:
                os._exit(status)
    return status


if __name__ == "__main__":
    raise SystemExit(_process_main())
