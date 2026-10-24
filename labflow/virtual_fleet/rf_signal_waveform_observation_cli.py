"""One explicit stored CW observation; no RF execution or reassessment."""
import json
import os
import re
import sys

_PREFIX = "rf_signal_waveform_observation_cli_"
_OPTIONS = {"--run-name": "run_name", "--observation-name": "observation_name",
            "--sample-rate-hz": "sample_rate_hz", "--sample-count": "sample_count", "--seed": "seed"}
_NUMBERS = {"sample_rate_hz": (r"[1-9][0-9]{0,9}", 1, 1000000000, 10),
            "sample_count": (r"[1-9][0-9]{0,3}", 1, 4096, 4),
            "seed": (r"0|[1-9][0-9]{0,9}", 0, 2147483647, 10)}
_PARENT_CODES = frozenset("rf_signal_waveform_observation_" + suffix for suffix in (
    "invalid_argument", "source_unavailable", "source_ineligible", "destination_exists",
    "dependency_changed", "math_unavailable", "write_failed", "publication_uncertain"))
_SUMMARY = "schema_version kind observation_name storage source math verification execution_authorized rerun_authorized".split()
_VERIFICATION = dict(data_origin="authored_synthetic", synthetic=True, hardware_verified=False,
    physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
    regulatory_scope_complete=False, method_approval="not_assessed", model_scope="normalized_baseband_sample_math_v1")
_NAME = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"
_ID = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
_SHA = r"[0-9a-f]{64}"
_HELP = ("Explicit authored synthetic CW observation. No RF execution or reassessment.\n"
         "Usage: python -B -m labflow.virtual_fleet.rf_signal_waveform_observation_cli "
         "--run-name RUN --observation-name OBS --sample-rate-hz FS --sample-count N --seed SEED\n"
         "All five pairs are required once. Canonical ASCII FS=1..1000000000, N=1..4096, "
         "SEED=0..2147483647. Names are validated by the observation API.\n")


class _Invalid(ValueError):
    pass


def _require(condition):
    if not condition:
        raise _Invalid() from None


def _help(arguments):
    return (type(arguments) in (list, tuple) and len(arguments) == 1
            and type(arguments[0]) is str and arguments[0] == "--help")


def _arguments(arguments):
    _require(type(arguments) in (list, tuple) and len(arguments) == 10
             and all(type(value) is str for value in arguments))
    request = {"schema_version": 1}
    for index in range(0, 10, 2):
        flag, value = arguments[index], arguments[index + 1]
        _require(len(flag) <= 18 and flag in _OPTIONS)
        key = _OPTIONS[flag]
        _require(key not in request)
        if key in _NUMBERS:
            pattern, minimum, maximum, width = _NUMBERS[key]
            _require(len(value) <= width and value.isascii() and re.fullmatch(pattern, value, re.ASCII) is not None)
            value = int(value)
            _require(minimum <= value <= maximum)
        request[key] = value
    return request


def _write(stream, text):
    count = stream.write(text)
    _require(type(count) is int and count == len(text))
    stream.flush()


def _keys(value, keys):
    _require(type(value) is dict and len(value) == len(keys)
             and all(type(key) is str for key in value) and set(value) == set(keys))
    return value


def _equal(value, expected):
    _require(type(value) is type(expected) and value == expected)


def _text(value, width, pattern=None):
    _require(type(value) is str and len(value) <= width and value.isascii())
    if pattern is not None:
        _require(re.fullmatch(pattern, value, re.ASCII) is not None)


def _check_summary(value, run_name, observation_name):
    _keys(value, _SUMMARY)
    _equal(value["schema_version"], 1)
    _equal(value["kind"], "synthetic_rf_baseband_observation")
    _text(value["observation_name"], 64, _NAME)
    _require(value["observation_name"] == observation_name)
    _equal(value["execution_authorized"], False)
    _equal(value["rerun_authorized"], False)
    storage = _keys(value["storage"], ("state", "path", "bytes", "sha256"))
    _equal(storage["state"], "published")
    _text(storage["path"], 113)
    _require(storage["path"] == ".local/rf-waveform-observations/" + observation_name + "/observation.json")
    _require(type(storage["bytes"]) is int and 1 <= storage["bytes"] <= 3145729)
    _text(storage["sha256"], 64, _SHA)
    source = _keys(value["source"], ("run_name", "run_id", "runtime_instance_id", "manifest_sha256", "snapshot_sha256"))
    _text(source["run_name"], 64, _NAME)
    _require(source["run_name"] == run_name)
    for key in ("run_id", "runtime_instance_id"):
        _text(source[key], 128, _ID)
    _require(source["run_id"] != source["runtime_instance_id"])
    for key in ("manifest_sha256", "snapshot_sha256"):
        _text(source[key], 64, _SHA)
    math = _keys(value["math"], ("source_scenario_id", "reference_plane", "binding_scope",
                                "spec_sha256", "packet_sha256", "analysis_sha256"))
    for key, expected in (("source_scenario_id", "cw_peak"), ("reference_plane", "declared_dut_output"),
                          ("binding_scope", "declared_source_projection_only")):
        _equal(math[key], expected)
    for key in ("spec_sha256", "packet_sha256", "analysis_sha256"):
        _text(math[key], 64, _SHA)
    verification = _keys(value["verification"], _VERIFICATION)
    for key, expected in _VERIFICATION.items():
        _equal(verification[key], expected)


def _summary_text(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
    _require(type(text) is str and len(text.encode("utf-8", "strict")) <= 8192)
    return text + "\n"


def _diagnose(code):
    try:
        _write(sys.stderr, '{"error":{"code":"' + code + '"}}\n')
    except BaseException:
        pass


def main(argv=None) -> int:
    """Return a status without reconfiguring, replacing or closing caller streams."""
    code, status, phase, attempted = None, 0, "arguments", False
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if _help(arguments):
            phase = "help"
            _write(sys.stderr, _HELP)
        else:
            request = _arguments(arguments)
            run_name, observation_name = request["run_name"], request["observation_name"]
            phase = "entry"
            from . import rf_signal_waveform_observation as parent
            entry, parent_error = parent.record_rf_baseband_observation, parent.RfSignalWaveformObservationError
            _require(callable(entry) and isinstance(parent_error, type) and issubclass(parent_error, Exception))
            phase = "call"
            attempted = True
            try:
                value = entry(request)
            except KeyboardInterrupt:
                raise
            except BaseException as error:
                code, status = _PREFIX + "delivery_unconfirmed", 1
                try:
                    if type(error) is parent_error:
                        full = error.code
                        if type(full) is str and full in _PARENT_CODES:
                            code = full
                            status = 2 if full == "rf_signal_waveform_observation_invalid_argument" else 1
                except BaseException:
                    # Classification/diagnostic faults never replace the first API failure.
                    pass
            else:
                phase = "summary"
                _check_summary(value, run_name, observation_name)
                text = _summary_text(value)
                phase = "output"
                _write(sys.stdout, text)
    except KeyboardInterrupt:
        code, status = _PREFIX + ("interrupted_unconfirmed" if attempted else "interrupted"), 130
    except _Invalid:
        if phase == "arguments":
            code, status = _PREFIX + "invalid_argument", 2
        else:
            code, status = _PREFIX + ("delivery_unconfirmed" if attempted else "output_failed" if phase == "help" else "unavailable"), 1
    except BaseException:
        code, status = _PREFIX + ("delivery_unconfirmed" if attempted else "output_failed" if phase == "help" else "unavailable"), 1
    if code is not None:
        try:
            _diagnose(code)
        except BaseException:
            pass
    return status


def _quiet(stream, status):
    """This process only, after main/parent cleanup; never write again to the caller."""
    try:
        target = stream.fileno()
        sink = os.open(os.devnull, os.O_WRONLY)
        try:
            if sink != target:
                os.dup2(sink, target)
        finally:
            if sink != target:
                os.close(sink)
        # Drain only to the process-owned NUL sink, avoiding shutdown exit 120.
        stream.flush()
    except BaseException:
        os._exit(status)


def _process_main() -> int:
    """Freeze this process's route, configure UTF8 and preserve its first outcome."""
    streams = (sys.stdout, sys.stderr)
    code, status, help_route, arguments = None, 0, False, None
    try:
        arguments = sys.argv[1:]
        help_route = _help(arguments)
    except KeyboardInterrupt:
        code, status = _PREFIX + "interrupted", 130
    except BaseException:
        code, status = _PREFIX + "output_failed", 1
    for stream in streams:
        try:
            stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")
        except BaseException as error:
            if code is None:
                code, status = (_PREFIX + "interrupted", 130) if isinstance(error, KeyboardInterrupt) else (_PREFIX + "output_failed", 1)
    if code is None:
        try:
            status = main(arguments)
            _require(type(status) is int and status in (0, 1, 2, 130))
        except BaseException as error:
            code = _PREFIX + (("interrupted" if help_route else "interrupted_unconfirmed")
                              if isinstance(error, KeyboardInterrupt) else ("output_failed" if help_route else "delivery_unconfirmed"))
            status = 130 if isinstance(error, KeyboardInterrupt) else 1
    if code is not None:
        try:
            _diagnose(code)
        except BaseException:
            pass
    for stream in streams:
        if stream is None:
            continue
        try:
            stream.flush()
        except BaseException as error:
            if status == 0:
                code = _PREFIX + (("interrupted" if help_route else "interrupted_unconfirmed")
                                  if isinstance(error, KeyboardInterrupt) else ("output_failed" if help_route else "delivery_unconfirmed"))
                status = 130 if isinstance(error, KeyboardInterrupt) else 1
                try:
                    _diagnose(code)
                except BaseException:
                    pass
            _quiet(stream, status)
    return status


if __name__ == "__main__":
    raise SystemExit(_process_main())
