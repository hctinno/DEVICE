"""Compare four explicit supplied JSON snapshots once; no execution or storage."""
import json
import os
import sys

from .rf_signal_read_cli import _json, _write

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 256 * 1024
_PREFIX = "conducted_twin_comparison_cli_"
_FLAGS = ("--result-file", "--reference-file", "--policy-file", "--lineage-file")
_CODES = frozenset("invalid_argument path_invalid not_found input_limit json_invalid input_changed unavailable".split())
_HELP = ("보존 합성 conducted 비교: read four explicit snapshots and compare once.\n"
         "Usage: python -B -m labflow.virtual_fleet.conducted_twin_comparison_cli "
         "--result-file RESULT.json --reference-file REFERENCE.json "
         "--policy-file POLICY.json --lineage-file LINEAGE.json\n"
         "Each option once, separate value; Windows local regular files only.\n"
         "RESULT is the D3 result JSON, never an e3 manifest or automatic selection.\n"
         "Strict UTF-8/no BOM/duplicate/nonfinite; total raw input <=2MiB.\n"
         "Original DTO11 compact JSON once; <=256KiB including LF.\n"
         "Exit: compared 0 (within or outside tolerance), not_assessed 3, file/JSON 4; "
         "syntax 2, output 1, first KeyboardInterrupt 130.\n"
         "No Store/HTTP/AI/hardware/execution/reassessment/attestation.\n")


class _Failure(ValueError):
    pass


def _fail(code):
    raise _Failure(code)


def _arguments(argv):
    if type(argv) not in (list, tuple) or len(argv) != 8 or any(type(item) is not str for item in argv):
        _fail("invalid_argument")
    selected = {}
    for key, value in zip(argv[::2], argv[1::2]):
        if key not in _FLAGS or key in selected:
            _fail("invalid_argument")
        selected[key] = value
    if set(selected) != set(_FLAGS):
        _fail("invalid_argument")
    return [selected[key] for key in _FLAGS]


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("json_invalid")
        result[key] = value
    return result


def _constant(value):
    _fail("json_invalid")


def _parse(raw):
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail("json_invalid")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        _fail("json_invalid")


def _same(native, backend, pin):
    tree, path, descriptor, stamp, raw = pin
    if (native._stamp(tree.file_stat(path)) != stamp
            or native._stamp(backend.info(descriptor, directory=False)) != stamp):
        _fail("input_changed")


def _inputs(native, backend, paths, snapshot):
    pins, total = [], 0
    for path in paths:
        tree = native._Tree(path.parent, backend)
        stamp = native._stamp(tree.file_stat(path))
        if stamp[2] < 0 or stamp[2] > MAX_INPUT_BYTES - total:
            _fail("input_limit")
        descriptor = backend.open_read(path, pin=True)
        pin = (tree, path, descriptor, stamp, None)
        _same(native, backend, pin)
        raw = native._read_descriptor(descriptor, MAX_INPUT_BYTES - total, "packet_prepare_source_changed")
        if len(raw) != stamp[2]:
            _fail("input_changed")
        _same(native, backend, pin)
        total += len(raw)
        pins.append((tree, path, descriptor, stamp, raw))
    try:
        values = snapshot([_parse(pin[4]) for pin in pins])
    except Exception:
        _fail("json_invalid")
    return values, pins


def _recheck(native, backend, pins):
    for pin in pins:
        _same(native, backend, pin)
        raw = native._read_descriptor(pin[2], len(pin[4]), "packet_prepare_source_changed")
        if raw != pin[4]:
            _fail("input_changed")
        _same(native, backend, pin)


def _wire(value, parent, dto):
    """Check the delivery contract without recalculating or repairing the DTO."""
    dto._snapshot(value)
    base = parent._base()
    if (type(value) is not dict or set(value) != set(base) or type(value["schema_version"]) is not int
            or value["schema_version"] != 1 or value["kind"] != base["kind"]
            or value["status"] not in ("compared", "not_assessed")
            or _json(value["verification"]) != _json(base["verification"])
            or _json(value["conformity"]) != _json(base["conformity"])):
        _fail("unavailable")
    reference, numbers = value["reference"], value["comparison"]
    if (type(reference) is not dict or set(reference) != set(base["reference"])
            or reference["authenticity_verified"] is not False or reference["rights_verified"] is not False
            or reference["uncertainty_db"] is not None
            or type(numbers) is not dict or set(numbers) != set(base["comparison"])):
        _fail("unavailable")
    if value["status"] == "not_assessed":
        if any(item is not None for item in numbers.values()):
            _fail("unavailable")
        status = 3
    else:
        if (type(numbers["within_tolerance"]) is not bool
                or not all(dto._number(numbers[key]) for key in (
                    "twin_value_dbm", "reference_value_dbm", "signed_difference_db",
                    "absolute_difference_db", "tolerance_db"))
                or not all(type(numbers[key]) is str and bool(numbers[key]) for key in (
                    "signed_difference_rational_db", "absolute_difference_rational_db"))):
            _fail("unavailable")
        status = 0
    raw = _json(value) + b"\n"
    if len(raw) > MAX_OUTPUT_BYTES:
        _fail("unavailable")
    return raw, status


def _error(error, phase, native=None):
    if isinstance(error, KeyboardInterrupt):
        return "interrupted", 130
    if phase == "output_failed":
        return phase, 1
    if type(error) is _Failure:
        code = error.args[0] if len(error.args) == 1 else None
        code = code if type(code) is str and code in _CODES else "unavailable"
        return code, 2 if code == "invalid_argument" else 4
    if phase == "input_changed":
        return phase, 4
    if isinstance(error, FileNotFoundError):
        return "not_found", 4
    if (native is not None and type(error) is native.ControlPacketPrepareError
            and error.code in ("packet_prepare_path_invalid", "packet_prepare_invalid_argument")):
        return "path_invalid", 4
    return phase if phase == "path_invalid" else "unavailable", 4


def _diagnose(code):
    try:
        _write(sys.stderr, _json({"error": {"code": _PREFIX + code}}) + b"\n")
    except BaseException:
        pass


def main(argv=None) -> int:
    """Keep caller streams and the first error; write only after known cleanup."""
    backend = cleanup = native = primary = raw = None
    status, phase = 0, "unavailable"
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if (type(arguments) in (list, tuple) and len(arguments) == 1
                and type(arguments[0]) is str and arguments[0] == "--help"):
            phase = "output_failed"
            _write(sys.stdout, _HELP.encode("utf-8"))
            return 0
        selected = _arguments(arguments)
        from .. import control_packet_prepare as native
        from . import conducted_twin_comparison as parent
        from . import conducted_twin_result as dto
        from . import rf_signal_waveform_observation_read as cleanup
        phase = "path_invalid"
        paths = []
        for value in selected:
            lexical = native.Path(value)
            parts = lexical.parts[1:] if lexical.anchor else lexical.parts
            if not all(native._valid_segment(part) for part in parts):
                _fail("path_invalid")
            paths.append(native._local_path(value))
        phase = "unavailable"
        backend = native._WindowsIO()
        values, pins = _inputs(native, backend, paths, dto._snapshot)
        result = parent.compare_conducted_twin_result(values[0], values[1],
                    comparator_policy=values[2], lineage=values[3])
        raw, status = _wire(result, parent, dto)
        phase = "input_changed"
        _recheck(native, backend, pins)
    except BaseException as error:
        primary = _error(error, phase, native)
    finally:
        if backend is not None:
            try:
                closing = cleanup._close(backend)
            except BaseException as error:
                closing = error
            if primary is None and closing is not None:
                primary = _error(closing, "unavailable", native)
    if primary is None:
        try:
            _write(sys.stdout, raw)
        except BaseException as error:
            primary = _error(error, "output_failed")
    if primary is not None:
        code, status = primary
        _diagnose(code)
    return status


def _process_main():
    """Configure process streams and prevent final flush from replacing failure."""
    primary = None
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")
        except BaseException as error:
            if primary is None:
                primary = _error(error, "output_failed")
    if primary is None:
        status = main()
    else:
        code, status = primary
        _diagnose(code)
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.flush()
        except BaseException as error:
            if status in (0, 3):
                code, status = _error(error, "output_failed")
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
