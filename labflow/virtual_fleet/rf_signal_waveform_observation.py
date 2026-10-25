"""Explicit CW mathematics bound to one stored synthetic RF read version."""
import errno
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re
import stat

from .. import control_packet_prepare as _native
from . import rf_signal_read as _reader, rf_signal_scenario as _scenario, rf_signal_waveform as _waveform


_PREFIX = "rf_signal_waveform_observation_"
_CODES = frozenset(_PREFIX + suffix for suffix in (
    "invalid_argument", "source_unavailable", "source_ineligible", "destination_exists",
    "dependency_changed", "math_unavailable", "write_failed", "publication_uncertain"))
_REQUEST = "schema_version run_name observation_name sample_rate_hz sample_count seed".split()
_SNAPSHOT = ("schema_version kind selection metadata storage historical_assessment measurement "
             "measurement_goal_succeeded outcome failure verification execution_authorized rerun_authorized error_code").split()
_FLAGS = dict(data_origin="authored_synthetic", synthetic=True, hardware_verified=False,
              physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
              method_approval="not_assessed", regulatory_scope_complete=False,
              model_scope="normalized_baseband_sample_math_v1")
_PINS = (
    ("read048", "labflow/virtual_fleet/rf_signal_read.py", 26249,
     "8cf602b50aac2cb56f1df7b807b19dcfebfdeff588dfe0904cef16a943581472"),
    ("describe041", "labflow/virtual_fleet/rf_signal_scenario.py", 44423,
     "f5471dde9786983152992e04fa2dade8b5ac927b1c25e5c0303c30bb664db1aa"),
    ("waveform054", "labflow/virtual_fleet/rf_signal_waveform.py", 7581,
     "7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d"),
    ("native_helper", "labflow/control_packet_prepare.py", 29100,
     "8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7"),
)
_READ_CODES = dict(zip(
    ("rf_signal_read_" + suffix for suffix in
     ("invalid_argument", "path_invalid", "not_found", "input_changed", "evidence_invalid", "unavailable")),
    ("invalid_argument", "source_unavailable", "source_unavailable", "dependency_changed",
     "source_unavailable", "source_unavailable")))
_SCENARIO_CODES = dict(zip(
    ("rf_signal_scenario_" + suffix for suffix in
     ("invalid_request", "unsupported_catalog", "output_unavailable", "execution_incomplete",
      "evidence_invalid", "evidence_unavailable")),
    ("source_ineligible", "source_unavailable", "source_unavailable", "source_unavailable",
     "source_unavailable", "source_unavailable")))
_WAVEFORM_CODES = {"rf_signal_waveform_" + suffix: "math_unavailable" for suffix in
                   ("invalid_argument", "budget_exceeded", "numeric_unavailable")}
_NATIVE_CODES = frozenset("packet_prepare_" + suffix for suffix in (
    "invalid_argument", "path_invalid", "destination_exists", "verification_failed", "copy_failed",
    "source_changed", "receipt_failed"))
_FALLBACK = dict(preflight="source_unavailable", read_source="source_unavailable",
                 compute_math="math_unavailable", dependency_pin="dependency_changed",
                 environment_preflight="source_unavailable", claim_destination="write_failed",
                 write_pending="write_failed", verify_pending="write_failed", publish="publication_uncertain",
                 verify_published="publication_uncertain", cleanup="write_failed")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z", re.ASCII)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class RfSignalWaveformObservationError(ValueError):
    """Only a fixed full code crosses the boundary."""
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else _PREFIX + "write_failed"
        super().__init__(self.code)


def _fail(suffix):
    raise RfSignalWaveformObservationError(_PREFIX + suffix) from None


def _require(condition, suffix):
    if not condition:
        _fail(suffix)


def _keys(value, keys, suffix):
    _require(type(value) is dict and len(value) == len(keys)
             and all(type(key) is str for key in value) and set(value) == set(keys), suffix)


def _integer(value, low, high, suffix):
    _require(type(value) is int and low <= value <= high, suffix)


def _number(value, suffix):
    _require(type(value) in (int, float) and math.isfinite(value), suffix)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _snapshot(value, limit, suffix):
    """Bound plain nodes before copying/serializing; do not invoke subclasses."""
    nodes, remaining = 0, limit

    def spend(size):
        nonlocal remaining
        _require(size <= remaining, suffix)
        remaining -= size

    def string(item):
        _require(type(item) is str and len(item) <= 16384, suffix)
        spend(2)
        for char in item:
            point = ord(char)
            _require(not 0xD800 <= point <= 0xDFFF, suffix)
            if point < 32:
                spend(2 if point in (8, 9, 10, 12, 13) else 6)
            elif char in ('"', "\\"):
                spend(2)
            else:
                spend(1 if point < 128 else 2 if point < 2048 else 3 if point < 65536 else 4)

    def copy(item, depth):
        nonlocal nodes
        nodes += 1
        _require(nodes <= 32768 and depth <= 20, suffix)
        kind = type(item)
        if kind is dict:
            _require(len(item) <= 32768 - nodes, suffix)
            spend(2 + max(0, len(item) - 1))
            result = {}
            for key, child in item.items():
                string(key)
                spend(1)
                result[key] = copy(child, depth + 1)
            return result
        if kind is list:
            _require(len(item) <= 32768 - nodes, suffix)
            spend(2 + max(0, len(item) - 1))
            return [copy(child, depth + 1) for child in item]
        if kind is str:
            string(item)
        elif kind is int:
            _require(item.bit_length() <= limit * 4, suffix)
            spend(len(str(item)))
        elif kind is float:
            _number(item, suffix)
            spend(len(repr(item)))
        else:
            _require(item is None or kind is bool, suffix)
            spend(4 if item is None or item is True else 5)
        return item

    result = copy(value, 0)
    _require(len(_canonical(result)) == limit - remaining, suffix)
    return result


def _request(value):
    _keys(value, _REQUEST, "invalid_argument")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1, "invalid_argument")
    for name in ("run_name", "observation_name"):
        _require(type(value[name]) is str, "invalid_argument")
    name = value["observation_name"]
    _require(_NAME.fullmatch(name) is not None and _native._valid_segment(name), "invalid_argument")
    _integer(value["sample_rate_hz"], 1, 1_000_000_000, "invalid_argument")
    _integer(value["sample_count"], 1, 4096, "invalid_argument")
    _integer(value["seed"], 0, 2147483647, "invalid_argument")
    return dict(value)


def _module_root(module, levels):
    value = module.__file__
    _require(type(value) is str and Path(value).is_absolute(), "source_unavailable")
    tail = ntpath.splitdrive(value)[1]
    _require(not value.startswith(("\\\\", "//")) and re.search(r"[\\/]{2}", tail) is None
             and all(_native._valid_segment(part) for part in re.split(r"[\\/]", tail) if part),
             "source_unavailable")
    return _native._local_path(str(Path(value).absolute().parents[levels]))


def _root():
    # Use this module's lexical location and require the same loaded clone.
    value = __file__
    _require(type(value) is str and Path(value).is_absolute(), "source_unavailable")
    tail = ntpath.splitdrive(value)[1]
    _require(not value.startswith(("\\\\", "//")) and re.search(r"[\\/]{2}", tail) is None
             and all(_native._valid_segment(part) for part in re.split(r"[\\/]", tail) if part),
             "source_unavailable")
    root = _native._local_path(str(Path(value).absolute().parents[2]))
    for module, levels in ((_reader, 2), (_scenario, 2), (_waveform, 2), (_native, 1)):
        _require(_module_root(module, levels) == root, "source_unavailable")
    return root


def _identities(tree):
    for path, identity in tuple(tree.directories.items()):
        held = tree.backend.info(tree.backend.directories[path], directory=True)
        current = held if path == Path(path.anchor) else tree.backend.stat_file(path)
        _require(stat.S_ISDIR(current.st_mode)
                 and (held.st_dev, held.st_ino) == identity == (current.st_dev, current.st_ino),
                 "dependency_changed")


def _pin_sources(tree):
    result = []
    for role, relative, size, digest in _PINS:
        path = tree.root / relative
        before = _native._stamp(tree.file_stat(path))
        descriptor = tree.backend.open_read(path, pin=True)
        _require(_native._stamp(tree.backend.info(descriptor, directory=False)) == before, "dependency_changed")
        raw = _native._read_descriptor(descriptor, 65536, "packet_prepare_source_changed")
        normalized = raw.replace(b"\r\n", b"\n")
        _require((len(normalized), _sha(normalized)) == (size, digest)
                 and _native._stamp(tree.file_stat(path)) == before, "dependency_changed")
        result.append((path, descriptor, before, _sha(raw)))
    _identities(tree)
    return result


def _check_sources(tree, pins):
    for path, descriptor, stamp, digest in pins:
        _require(_native._stamp(tree.file_stat(path)) == stamp
                 and _native._stamp(tree.backend.info(descriptor, directory=False)) == stamp,
                 "dependency_changed")
        raw = _native._read_descriptor(descriptor, 65536, "packet_prepare_source_changed")
        _require(_sha(raw) == digest, "dependency_changed")
    _identities(tree)


def _source(value, request):
    suffix = "source_unavailable"
    _keys(value, _SNAPSHOT, suffix)
    value = _snapshot(value, 8192, suffix)
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and value["kind"] == "virtual_rf_signal_run_read", suffix)
    _keys(value["selection"], ["run_name"], suffix)
    _require(value["selection"]["run_name"] == request["run_name"], suffix)
    _keys(value["metadata"], "request run_id runtime_instance_id execution_status".split(), suffix)
    _keys(value["storage"], "status manifest_sha256 verified_file_count journal_status binding_verified".split(), suffix)
    _keys(value["verification"], "saved current_scope source_pins_verified fresh_offline_evaluation_performed "
          "producer_cli_exit_status".split(), suffix)
    storage, metadata, verification = value["storage"], value["metadata"], value["verification"]
    _require(storage["status"] in ("incomplete", "invalid", "complete_verified")
             and value["outcome"] in ("incomplete", "invalid", "failure_recorded", "assessment_failed",
                                      "expected_blocked", "measurement_observed")
             and metadata["execution_status"] in ("unconfirmed", "failed_recorded", "executed"), suffix)
    # Known noneligible views may legitimately have no metadata.request.
    _require(storage["status"] == "complete_verified" and storage["verified_file_count"] == 3
             and type(storage["verified_file_count"]) is int and storage["binding_verified"] is True
             and storage["journal_status"] == "complete" and metadata["execution_status"] == "executed"
             and value["failure"] is None and verification["source_pins_verified"] is True
             and value["outcome"] not in ("incomplete", "invalid", "failure_recorded"),
             "source_ineligible")
    source_request = metadata["request"]
    _require(source_request is not None, "source_ineligible")
    _keys(source_request, "schema_version scenario_id seed".split(), suffix)
    _require(type(source_request["schema_version"]) is int and source_request["schema_version"] == 1, suffix)
    _require(type(source_request["scenario_id"]) is str and source_request["scenario_id"] in (
        "pulsed_on_mean", "pulsed_time_mean", "pulsed_peak", "cw_peak", "shifted_frequency",
        "sensor_uncalibrated", "meter_frequency_conflict"), suffix)
    _require(source_request["scenario_id"] == "cw_peak", "source_ineligible")
    _integer(source_request["seed"], 0, 2147483647, suffix)
    _require(source_request["seed"] == request["seed"], "invalid_argument")
    for key in ("run_id", "runtime_instance_id"):
        _require(type(metadata[key]) is str and _ID.fullmatch(metadata[key]) is not None, suffix)
    _require(metadata["run_id"] != metadata["runtime_instance_id"], suffix)
    _require(type(storage["manifest_sha256"]) is str and _SHA.fullmatch(storage["manifest_sha256"]) is not None, suffix)
    saved = verification["saved"]
    _keys(saved, "data_origin execution_mode synthetic hardware_verified physical_verified ai_model_called "
          "normative_compliance_verified method_approval regulatory_scope_complete waveform_implemented".split(), suffix)
    _require(saved["synthetic"] is True and all(saved[key] is False for key in (
        "hardware_verified", "physical_verified", "ai_model_called", "normative_compliance_verified",
        "regulatory_scope_complete", "waveform_implemented")), "source_ineligible")
    _require(saved["data_origin"] == "authored_synthetic"
             and saved["execution_mode"] == "synthetic_virtual_execution"
             and saved["method_approval"] == "not_assessed"
             and type(value["measurement_goal_succeeded"]) is bool
             and value["error_code"] is None
             and verification["current_scope"] == "stored_hashes_and_public_journal", suffix)
    _keys(value["historical_assessment"], "status verdict evaluator_id evidence_refs summary_code".split(), suffix)
    assessment = value["historical_assessment"]
    refs = assessment["evidence_refs"]
    _require(assessment["status"] == "completed" and assessment["verdict"] in ("pass", "fail")
             and assessment["evaluator_id"] == "rf_signal_scenario_v1"
             and type(refs) is list and len(refs) == 1 and type(refs[0]) is str
             and _ID.fullmatch(refs[0]) is not None
             and assessment["summary_code"] in ("observed_signal_satisfied", "expected_sensor_blocked",
                                                "expected_meter_frequency_conflict", "scenario_expectation_mismatch"), suffix)
    _keys(value["measurement"], "value unit quantity reference_plane".split(), suffix)
    _number(value["measurement"]["value"], suffix)
    _require(value["measurement"]["unit"] == "dBm" and value["measurement"]["quantity"] == "peak"
             and value["measurement"]["reference_plane"] == "sensor_input", suffix)
    _require(value["execution_authorized"] is False and value["rerun_authorized"] is False
             and verification["fresh_offline_evaluation_performed"] is False
             and verification["producer_cli_exit_status"] is None, suffix)
    return value


def _declaration(value):
    suffix = "source_unavailable"
    _keys(value, "source_signal sensor meter reference_plane basis".split(), suffix)
    value = _snapshot(value, 8192, suffix)
    source = value["source_signal"]
    _keys(source, "frequency_hz power_dbm bandwidth_hz duty_cycle crest_factor_db modulation".split(), suffix)
    for key in ("frequency_hz", "power_dbm", "bandwidth_hz", "duty_cycle", "crest_factor_db"):
        _number(source[key], suffix)
    _require(type(source["modulation"]) is str, suffix)
    _keys(value["sensor"], ["calibration_valid", "acquisition_policy"], suffix)
    _keys(value["meter"], ["frequency_hz", "measurement_mode", "unit"], suffix)
    _require(type(value["sensor"]["calibration_valid"]) is bool
             and value["sensor"]["acquisition_policy"] == "triggered", suffix)
    _number(value["meter"]["frequency_hz"], suffix)
    _require(value["meter"]["frequency_hz"] > 0
             and value["meter"]["measurement_mode"] in ("on_average", "time_average", "peak")
             and value["meter"]["unit"] == "dBm"
             and value["reference_plane"] == "sensor_input" and value["basis"] == "declared_synthetic_policy", suffix)
    _require(source["modulation"] == "CW" and source["duty_cycle"] == 1
             and source["crest_factor_db"] == 0, "source_ineligible")
    return value


def _parent_call(call, error_type, codes, fallback, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except Exception as error:
        code = error.code if type(error) is error_type else None
        _fail(codes.get(code, fallback) if type(code) is str else fallback)


def _math_metadata(value, kind, recipe):
    suffix = "math_unavailable"
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and type(value["kind"]) is str and value["kind"] == kind
             and value["execution_authorized"] is False and value["rerun_authorized"] is False, suffix)
    _keys(value["verification"], list(_FLAGS), suffix)
    for key, expected in _FLAGS.items():
        _require(type(value["verification"][key]) is type(expected)
                 and value["verification"][key] == expected, suffix)
    grid = value["grid"]
    _keys(grid, "sample_rate_hz sample_count t0_seconds interpolation".split(), suffix)
    for key in ("sample_rate_hz", "sample_count"):
        _require(type(grid[key]) is int and grid[key] == recipe[key], suffix)
    _require(type(grid["t0_seconds"]) is int and grid["t0_seconds"] == 0
             and grid["interpolation"] == "zero_order_hold", suffix)


def _math(recipe, seed):
    suffix = "math_unavailable"
    packet = _parent_call(_waveform.generate_rf_baseband_envelope, _waveform.RfSignalWaveformError,
                          _WAVEFORM_CODES, suffix, recipe, seed=seed)
    _keys(packet, "schema_version kind grid sample_unit samples verification execution_authorized rerun_authorized".split(), suffix)
    packet = _snapshot(packet, 1048576, suffix)
    _math_metadata(packet, "synthetic_rf_baseband_envelope", recipe)
    _require(packet["sample_unit"] == "sqrt_mW", suffix)
    analysis = _parent_call(_waveform.analyze_rf_baseband_envelope, _waveform.RfSignalWaveformError,
                            _WAVEFORM_CODES, suffix, packet)
    _keys(analysis, "schema_version kind grid input_sha256 metrics verification execution_authorized rerun_authorized".split(), suffix)
    analysis = _snapshot(analysis, 1048576, suffix)
    _math_metadata(analysis, "synthetic_rf_baseband_analysis", recipe)
    _require(type(analysis["input_sha256"]) is str
             and analysis["input_sha256"] == _sha(_canonical(packet)), suffix)
    metrics = analysis["metrics"]
    _keys(metrics, "window_seconds observed_on_samples observed_duty_cycle time_mean_mw on_mean_mw "
          "peak_mw energy_mw_s time_mean_dbm on_mean_dbm peak_dbm".split(), suffix)
    _integer(metrics["observed_on_samples"], 0, recipe["sample_count"], suffix)
    for key in ("window_seconds", "observed_duty_cycle", "time_mean_mw", "peak_mw", "energy_mw_s"):
        _number(metrics[key], suffix)
    for key in ("on_mean_mw", "time_mean_dbm", "on_mean_dbm", "peak_dbm"):
        if metrics[key] is not None:
            _number(metrics[key], suffix)
    return packet, analysis


def _bundle(request, source, declared, packet, analysis, recipe):
    provenance = dict(binding_scope="declared_source_projection_only", reference_plane="declared_dut_output",
                      rf_manifest_sha256=source["storage"]["manifest_sha256"],
                      source_snapshot_sha256=_sha(_canonical(source)), packet_sha256=_sha(_canonical(packet)),
                      dependency_pins=[dict(role=role, lf_bytes=size, lf_sha256=digest)
                                       for role, path, size, digest in _PINS])
    value = dict(schema_version=1, kind="private_rf_baseband_math_observation", request=request,
                 source_snapshot=source, declared_setup=declared, recipe=recipe,
                 packet=packet, analysis=analysis, provenance=provenance)
    return _snapshot(value, 3 * 1048576, "math_unavailable")


def _mapped(error, operation, attempted=False):
    if attempted:
        return RfSignalWaveformObservationError(_PREFIX + "publication_uncertain")
    if type(error) is RfSignalWaveformObservationError:
        return RfSignalWaveformObservationError(error.code)
    suffix = _FALLBACK[operation]
    code = error.code if type(error) is _native.ControlPacketPrepareError else None
    if operation == "claim_destination" and (type(error) is FileExistsError or
            (type(error) is _native.ControlPacketPrepareError and type(code) is str
             and code in _NATIVE_CODES and code == "packet_prepare_destination_exists")):
        suffix = "destination_exists"
    return RfSignalWaveformObservationError(_PREFIX + suffix)


def _summary(bundle, raw, relative):
    source, provenance, request = bundle["source_snapshot"], bundle["provenance"], bundle["request"]
    result = dict(
        schema_version=1, kind="synthetic_rf_baseband_observation",
        observation_name=request["observation_name"],
        storage=dict(state="published", path=relative, bytes=len(raw), sha256=_sha(raw)),
        source=dict(run_name=request["run_name"], run_id=source["metadata"]["run_id"],
                    runtime_instance_id=source["metadata"]["runtime_instance_id"],
                    manifest_sha256=provenance["rf_manifest_sha256"],
                    snapshot_sha256=provenance["source_snapshot_sha256"]),
        math=dict(source_scenario_id="cw_peak", reference_plane="declared_dut_output",
                  binding_scope="declared_source_projection_only", spec_sha256=_sha(_canonical(bundle["recipe"])),
                  packet_sha256=provenance["packet_sha256"], analysis_sha256=_sha(_canonical(bundle["analysis"]))),
        verification=dict(_FLAGS), execution_authorized=False, rerun_authorized=False)
    return _snapshot(result, 8192, "math_unavailable")


def _persist(tree, pins, bundle, state):
    raw = _canonical(bundle) + b"\n"
    folder = tree.root / ".local/rf-waveform-observations" / bundle["request"]["observation_name"]
    pending, final = folder / "observation.pending.json", folder / "observation.json"
    result = _summary(bundle, raw, final.relative_to(tree.root).as_posix())
    state.update(phase="claim_destination", operation="claim_destination")
    tree.directory(folder.parent, create=True)
    owned = tree.backend.directory(folder, create=True)
    # Ownership begins only when the exclusive native creation returns.
    state["leaf"] = (folder, owned, None)
    info = tree.backend.info(owned, directory=True)
    state["leaf"] = (folder, owned, (info.st_dev, info.st_ino))
    tree.directory(folder)
    state.update(phase="write_pending", operation="write_pending")
    stamp = _native._write_bytes(tree, pending, raw, "packet_prepare_receipt_failed", sync=True)
    state.update(phase="verify_pending", operation="verify_pending")
    pinned = tree.backend.open_read(pending, pin=True)
    _verify_file(tree, pending, pinned, stamp, raw)
    state["operation"] = "dependency_pin"
    _check_sources(tree, pins)
    state.update(phase="publish", operation="publish")
    state["attempted"] = True
    tree.backend.link_receipt(pinned, final)
    state.update(phase="verify_published", operation="verify_published")
    published = tree.backend.open_read(final, pin=True)
    _verify_file(tree, final, published, stamp, raw)
    return result


def _verify_file(tree, path, descriptor, stamp, raw):
    _require(_native._stamp(tree.backend.info(descriptor, directory=False)) == stamp
             and _native._stamp(tree.file_stat(path)) == stamp, "write_failed")
    _require(_native._read_descriptor(descriptor, len(raw), "packet_prepare_receipt_failed") == raw, "write_failed")
    _require(_native._stamp(tree.backend.info(descriptor, directory=False)) == stamp
             and _native._stamp(tree.file_stat(path)) == stamp, "write_failed")


def _marker(tree, state, primary):
    leaf = state["leaf"]
    if tree is None or leaf is None or leaf[2] is None:
        return
    try:
        folder, descriptor, identity = leaf
        _require(tree.backend.directories.get(folder) == descriptor, "write_failed")
        info = tree.backend.info(descriptor, directory=True)
        _require((info.st_dev, info.st_ino) == identity, "write_failed")
        _identities(tree)
        interrupted = isinstance(primary, KeyboardInterrupt)
        value = dict(schema_version=1, kind="rf_baseband_observation_failure", phase=state["phase"],
                     status="interrupted" if interrupted else "failed",
                     error_code=None if interrupted else primary.code, publication_attempted=state["attempted"])
        _native._write_bytes(tree, folder / "failure.json", _canonical(value) + b"\n",
                             "packet_prepare_receipt_failed", sync=True)
    except (Exception, KeyboardInterrupt):
        # A marker is best effort and never replaces the first outcome.
        pass


def _close_owned(backend):
    """Supervise known descriptors even if native.close pops then interrupts."""
    first, known = None, {}
    directories = dict(backend.directories)
    for descriptor in tuple(backend.held):
        try:
            info = os.fstat(descriptor)
            known[descriptor] = (info.st_dev, info.st_ino, info.st_mode)
        except (Exception, KeyboardInterrupt) as error:
            if first is None:
                first = error
    try:
        backend.close()
    except (Exception, KeyboardInterrupt) as error:
        if first is None:
            first = error
    remaining = []
    for descriptor, identity in known.items():
        # A single interrupted/failed close may leave the descriptor open.
        # Recheck the same owned object before bounded cleanup; never reopen.
        for attempt in range(2):
            try:
                current = os.fstat(descriptor)
                if (current.st_dev, current.st_ino, current.st_mode) != identity:
                    if first is None:
                        first = RfSignalWaveformObservationError(_PREFIX + "write_failed")
                    break
                os.close(descriptor)
                break
            except OSError as error:
                if error.errno == errno.EBADF:
                    break
                if first is None:
                    first = error
            except (Exception, KeyboardInterrupt) as error:
                if first is None:
                    first = error
        try:
            current = os.fstat(descriptor)
            if (current.st_dev, current.st_ino, current.st_mode) == identity:
                remaining.append(descriptor)
                if first is None:
                    first = RfSignalWaveformObservationError(_PREFIX + "write_failed")
        except OSError as error:
            if error.errno != errno.EBADF and first is None:
                first = error
        except (Exception, KeyboardInterrupt) as error:
            if first is None:
                first = error
    # Do not report an empty ownership list if a persistent close failure remains.
    backend.held[:] = remaining
    backend.directories.clear()
    backend.directories.update({path: fd for path, fd in directories.items() if fd in remaining})
    return first


def record_rf_baseband_observation(request) -> dict:
    """Record one opt-in projection; never run or reassess the stored RF attempt."""
    backend, tree, result, primary = None, None, None, None
    state = dict(phase=None, operation="preflight", attempted=False, leaf=None)
    try:
        request = _request(request)
        state["operation"] = "environment_preflight"
        root = _root()
        backend = _native._WindowsIO()
        tree = _native._Tree(root, backend)
        state["operation"] = "dependency_pin"
        pins = _pin_sources(tree)
        state["operation"] = "read_source"
        returned = _parent_call(_reader.read_rf_signal_run, _reader.RfSignalReadError,
                                _READ_CODES, "source_unavailable", request["run_name"])
        source = _source(returned, request)
        returned = _parent_call(_scenario.describe_rf_signal_scenario, _scenario.RfSignalScenarioError,
                                _SCENARIO_CODES, "source_unavailable", "cw_peak")
        declared = _declaration(returned)
        recipe = dict(schema_version=1, signal_kind="cw", sample_rate_hz=request["sample_rate_hz"],
                      sample_count=request["sample_count"], on_power_dbm=declared["source_signal"]["power_dbm"], pulse=None)
        state["operation"] = "compute_math"
        packet, analysis = _math(recipe, request["seed"])
        bundle = _bundle(request, source, declared, packet, analysis, recipe)
        result = _persist(tree, pins, bundle, state)
    except KeyboardInterrupt as error:
        primary = error
    except Exception as error:
        primary = _mapped(error, state["operation"], state["attempted"])
    finally:
        if backend is not None:
            if primary is not None:
                _marker(tree, state, primary)
            else:
                state.update(phase="cleanup", operation="cleanup")
            error = _close_owned(backend)
            if primary is None and error is not None:
                primary = error if isinstance(error, KeyboardInterrupt) else _mapped(error, "cleanup", state["attempted"])
                _marker(tree, state, primary)
    if primary is not None:
        raise primary from None
    return result
