"""Read a recorded CW math observation without producing or recalculating one."""
import errno
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re

from .. import control_packet_prepare as _native

__all__ = ["RfSignalWaveformObservationReadError", "read_rf_baseband_observation"]
_PREFIX = "rf_signal_waveform_observation_read_"
_SUFFIXES = frozenset("invalid_argument path_invalid not_found incomplete record_mismatch evidence_invalid input_changed unavailable".split())
_FLAGS = dict(data_origin="authored_synthetic", synthetic=True, hardware_verified=False,
              physical_verified=False, ai_model_called=False, normative_compliance_verified=False,
              method_approval="not_assessed", regulatory_scope_complete=False,
              model_scope="normalized_baseband_sample_math_v1")
_PINS = (
    ("read048", 25927, "3999ab598acdc86639d82f2e451295f378ebb3dc827f070c6d670f8cd2a59540"),
    ("describe041", 44423, "bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae"),
    ("waveform054", 7581, "7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d"),
    ("native_helper", 29100, "8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7"))
# A saved bundle names one coherent caller version, never a per-role mixture.
_CURRENT_PINS = (
    ("read048", 26249, "8cf602b50aac2cb56f1df7b807b19dcfebfdeff588dfe0904cef16a943581472"),
    ("describe041", 44423, "f5471dde9786983152992e04fa2dade8b5ac927b1c25e5c0303c30bb664db1aa"),
    ("waveform054", 7581, "7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d"),
    ("native_helper", 29100, "8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7"))
_MAX_BODY = 3 * 1048576
_MAX_FILE = _MAX_BODY + 1
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z", re.ASCII)
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z", re.ASCII)

class RfSignalWaveformObservationReadError(ValueError):
    """A fixed code, without supplier text, content or paths."""
    def __init__(self, code):
        self.code = code if type(code) is str and code in {_PREFIX+s for s in _SUFFIXES} else _PREFIX+"invalid_argument"
        super().__init__(self.code)

def _fail(suffix):
    raise RfSignalWaveformObservationReadError(_PREFIX+suffix) from None

def _require(condition, suffix="evidence_invalid"):
    if not condition:
        _fail(suffix)

def _keys(value, names, suffix="evidence_invalid"):
    names = names.split()
    _require(type(value) is dict and len(value) == len(names)
             and all(type(k) is str for k in value) and set(value) == set(names), suffix)

def _integer(value, low, high):
    _require(type(value) is int and low <= value <= high)

def _number(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    _require(valid)

def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None

def _identifier(value):
    return type(value) is str and _ID.fullmatch(value) is not None

def _name(value, suffix):
    _require(type(value) is str and _NAME.fullmatch(value) is not None
             and _native._valid_segment(value), suffix)

def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _copy(value, limit, suffix="evidence_invalid"):
    """Bound plain nodes and encoded size before copying/serialization."""
    nodes, remaining = 0, limit
    def spend(size):
        nonlocal remaining
        _require(size <= remaining, suffix)
        remaining -= size
    def string(item):
        _require(type(item) is str and len(item) <= 16384, suffix)
        spend(2)
        for c in item:
            n = ord(c)
            _require(not 0xD800 <= n <= 0xDFFF, suffix)
            if n < 32:
                spend(2 if n in (8,9,10,12,13) else 6)
            elif c in ('"', "\\"):
                spend(2)
            else:
                spend(1 if n < 128 else 2 if n < 2048 else 3 if n < 65536 else 4)
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        _require(nodes <= 32768 and depth <= 20, suffix)
        kind = type(item)
        if kind is dict:
            _require(len(item) <= 32768-nodes, suffix)
            spend(2+max(0,len(item)-1)); result={}
            for k,v in item.items():
                string(k); spend(1); result[k]=visit(v,depth+1)
            return result
        if kind is list:
            _require(len(item) <= 32768-nodes, suffix)
            spend(2+max(0,len(item)-1))
            return [visit(v,depth+1) for v in item]
        if kind is str:
            string(item)
        elif kind is int:
            _require(item.bit_length() <= 1702, suffix)
            text=str(item); _require(len(text) <= 512, suffix); spend(len(text))
        elif kind is float:
            _require(math.isfinite(item), suffix); spend(len(repr(item)))
        else:
            _require(item is None or kind is bool, suffix)
            spend(4 if item is None or item is True else 5)
        return item
    result=visit(value,0)
    _require(len(_canonical(result)) == limit-remaining, suffix)
    return result

def _flags(value):
    _keys(value, " ".join(_FLAGS))
    _require(all(type(value[k]) is type(v) and value[k] == v for k,v in _FLAGS.items()))

def _summary(value, name):
    value=_copy(value,8192,"invalid_argument")
    try:
        _keys(value,"schema_version kind observation_name storage source math verification execution_authorized rerun_authorized")
        _require(type(value["schema_version"]) is int and value["schema_version"] == 1
                 and value["kind"] == "synthetic_rf_baseband_observation" and value["observation_name"] == name)
        storage=value["storage"]; _keys(storage,"state path bytes sha256")
        _require(storage["state"] == "published" and storage["path"] == f".local/rf-waveform-observations/{name}/observation.json")
        _integer(storage["bytes"],1,_MAX_FILE); _require(_hash(storage["sha256"]))
        source=value["source"]; _keys(source,"run_name run_id runtime_instance_id manifest_sha256 snapshot_sha256")
        _name(source["run_name"],"invalid_argument")
        _require(_identifier(source["run_id"]) and _identifier(source["runtime_instance_id"])
                 and source["run_id"] != source["runtime_instance_id"])
        _require(_hash(source["manifest_sha256"]) and _hash(source["snapshot_sha256"]))
        math_value=value["math"]; _keys(math_value,"source_scenario_id reference_plane binding_scope spec_sha256 packet_sha256 analysis_sha256")
        _require(math_value["source_scenario_id"] == "cw_peak" and math_value["reference_plane"] == "declared_dut_output"
                 and math_value["binding_scope"] == "declared_source_projection_only")
        _require(all(_hash(math_value[k]) for k in ("spec_sha256","packet_sha256","analysis_sha256")))
        _flags(value["verification"])
        _require(value["execution_authorized"] is False and value["rerun_authorized"] is False)
    except RfSignalWaveformObservationReadError:
        _fail("invalid_argument")
    return value

def _source(value, request):
    value=_copy(value,8192)
    _keys(value,"schema_version kind selection metadata storage historical_assessment measurement measurement_goal_succeeded outcome failure verification execution_authorized rerun_authorized error_code")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1 and value["kind"] == "virtual_rf_signal_run_read")
    _keys(value["selection"],"run_name")
    _require(value["selection"]["run_name"] == request["run_name"])
    metadata=value["metadata"]; _keys(metadata,"request run_id runtime_instance_id execution_status")
    q=metadata["request"]; _keys(q,"schema_version scenario_id seed")
    _require(type(q["schema_version"]) is int and q["schema_version"] == 1 and q["scenario_id"] == "cw_peak")
    _integer(q["seed"],0,2147483647); _require(q["seed"] == request["seed"])
    _require(_identifier(metadata["run_id"]) and _identifier(metadata["runtime_instance_id"])
             and metadata["run_id"] != metadata["runtime_instance_id"] and metadata["execution_status"] == "executed")
    storage=value["storage"]; _keys(storage,"status manifest_sha256 verified_file_count journal_status binding_verified")
    _require(storage["status"] == "complete_verified" and type(storage["verified_file_count"]) is int
             and storage["verified_file_count"] == 3 and storage["journal_status"] == "complete"
             and storage["binding_verified"] is True and _hash(storage["manifest_sha256"]))
    verification=value["verification"]
    _keys(verification,"saved current_scope source_pins_verified fresh_offline_evaluation_performed producer_cli_exit_status")
    saved=verification["saved"]
    _keys(saved,"data_origin execution_mode synthetic hardware_verified physical_verified ai_model_called normative_compliance_verified method_approval regulatory_scope_complete waveform_implemented")
    _require(saved["data_origin"] == "authored_synthetic" and saved["execution_mode"] == "synthetic_virtual_execution"
             and saved["synthetic"] is True and saved["method_approval"] == "not_assessed"
             and all(saved[k] is False for k in ("hardware_verified","physical_verified","ai_model_called",
                 "normative_compliance_verified","regulatory_scope_complete","waveform_implemented")))
    _require(verification["current_scope"] == "stored_hashes_and_public_journal" and verification["source_pins_verified"] is True
             and verification["fresh_offline_evaluation_performed"] is False and verification["producer_cli_exit_status"] is None)
    a=value["historical_assessment"]; _keys(a,"status verdict evaluator_id evidence_refs summary_code")
    _require(a["status"] == "completed" and a["verdict"] in ("pass","fail") and a["evaluator_id"] == "rf_signal_scenario_v1"
             and type(a["evidence_refs"]) is list and len(a["evidence_refs"]) == 1 and _identifier(a["evidence_refs"][0])
             and a["summary_code"] in ("observed_signal_satisfied","expected_sensor_blocked","expected_meter_frequency_conflict","scenario_expectation_mismatch"))
    measurement=value["measurement"]; _keys(measurement,"value unit quantity reference_plane")
    _number(measurement["value"])
    _require(measurement["unit"] == "dBm" and measurement["quantity"] == "peak" and measurement["reference_plane"] == "sensor_input")
    _require(type(value["measurement_goal_succeeded"]) is bool and value["outcome"] in ("assessment_failed","expected_blocked","measurement_observed")
             and value["failure"] is None and value["error_code"] is None
             and value["execution_authorized"] is False and value["rerun_authorized"] is False)
    return value

def _grid(value, request):
    _keys(value,"sample_rate_hz sample_count t0_seconds interpolation")
    for k in ("sample_rate_hz","sample_count"):
        _require(type(value[k]) is int and value[k] == request[k])
    _require(type(value["t0_seconds"]) is int and value["t0_seconds"] == 0 and value["interpolation"] == "zero_order_hold")

def _bundle(value, summary, name):
    _keys(value,"schema_version kind request source_snapshot declared_setup recipe packet analysis provenance")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1 and value["kind"] == "private_rf_baseband_math_observation")
    req=value["request"]; _keys(req,"schema_version run_name observation_name sample_rate_hz sample_count seed")
    _require(type(req["schema_version"]) is int and req["schema_version"] == 1 and req["observation_name"] == name)
    _name(req["run_name"],"evidence_invalid")
    _integer(req["sample_rate_hz"],1,1000000000); _integer(req["sample_count"],1,4096); _integer(req["seed"],0,2147483647)
    source=_source(value["source_snapshot"],req)
    d=_copy(value["declared_setup"],8192); _keys(d,"source_signal sensor meter reference_plane basis")
    signal=d["source_signal"]; _keys(signal,"frequency_hz power_dbm bandwidth_hz duty_cycle crest_factor_db modulation")
    for k in ("frequency_hz","power_dbm","bandwidth_hz","duty_cycle","crest_factor_db"): _number(signal[k])
    _require(signal["modulation"] == "CW" and signal["duty_cycle"] == 1 and signal["crest_factor_db"] == 0)
    _keys(d["sensor"],"calibration_valid acquisition_policy"); _keys(d["meter"],"frequency_hz measurement_mode unit")
    _require(type(d["sensor"]["calibration_valid"]) is bool and d["sensor"]["acquisition_policy"] == "triggered")
    _number(d["meter"]["frequency_hz"])
    _require(d["meter"]["frequency_hz"] > 0 and d["meter"]["measurement_mode"] in ("on_average","time_average","peak")
             and d["meter"]["unit"] == "dBm" and d["reference_plane"] == "sensor_input" and d["basis"] == "declared_synthetic_policy")
    recipe=value["recipe"]; _keys(recipe,"schema_version signal_kind sample_rate_hz sample_count on_power_dbm pulse")
    _require(type(recipe["schema_version"]) is int and recipe["schema_version"] == 1 and recipe["signal_kind"] == "cw" and recipe["pulse"] is None)
    _require(all(type(recipe[k]) is int and recipe[k] == req[k] for k in ("sample_rate_hz","sample_count")))
    _number(recipe["on_power_dbm"])
    _require(-120 <= recipe["on_power_dbm"] <= 60 and type(recipe["on_power_dbm"]) is type(signal["power_dbm"])
             and recipe["on_power_dbm"] == signal["power_dbm"])
    packet=_copy(value["packet"],1048576); analysis=_copy(value["analysis"],1048576)
    _keys(packet,"schema_version kind grid sample_unit samples verification execution_authorized rerun_authorized")
    _keys(analysis,"schema_version kind grid input_sha256 metrics verification execution_authorized rerun_authorized")
    for obj,kind in ((packet,"synthetic_rf_baseband_envelope"),(analysis,"synthetic_rf_baseband_analysis")):
        _require(type(obj["schema_version"]) is int and obj["schema_version"] == 1 and obj["kind"] == kind
                 and obj["execution_authorized"] is False and obj["rerun_authorized"] is False)
        _grid(obj["grid"],req); _flags(obj["verification"])
    _require(packet["sample_unit"] == "sqrt_mW" and type(packet["samples"]) is list and len(packet["samples"]) == req["sample_count"])
    for row in packet["samples"]:
        _require(type(row) is list and len(row) == 2)
        for v in row:
            _number(v); _require(-1000 <= v <= 1000)
    metrics=analysis["metrics"]
    _keys(metrics,"window_seconds observed_on_samples observed_duty_cycle time_mean_mw on_mean_mw peak_mw energy_mw_s time_mean_dbm on_mean_dbm peak_dbm")
    _integer(metrics["observed_on_samples"],0,req["sample_count"])
    for k in ("window_seconds","observed_duty_cycle","time_mean_mw","peak_mw","energy_mw_s"): _number(metrics[k])
    for k in ("on_mean_mw","time_mean_dbm","on_mean_dbm","peak_dbm"):
        if metrics[k] is not None: _number(metrics[k])
    p=value["provenance"]; _keys(p,"binding_scope reference_plane rf_manifest_sha256 source_snapshot_sha256 packet_sha256 dependency_pins")
    _require(p["binding_scope"] == "declared_source_projection_only" and p["reference_plane"] == "declared_dut_output")
    _require(type(p["dependency_pins"]) is list and len(p["dependency_pins"]) == 4)
    pins=[]
    for actual in p["dependency_pins"]:
        _keys(actual,"role lf_bytes lf_sha256")
        _require(type(actual["role"]) is str and type(actual["lf_bytes"]) is int and type(actual["lf_sha256"]) is str)
        pins.append((actual["role"],actual["lf_bytes"],actual["lf_sha256"]))
    _require(tuple(pins) in (_PINS,_CURRENT_PINS))
    expected_source=summary["source"]; expected_math=summary["math"]
    _require(req["run_name"] == expected_source["run_name"]
             and all(source["metadata"][k] == expected_source[k] for k in ("run_id","runtime_instance_id")))
    _require(source["storage"]["manifest_sha256"] == p["rf_manifest_sha256"] == expected_source["manifest_sha256"])
    _require(_sha(_canonical(source)) == p["source_snapshot_sha256"] == expected_source["snapshot_sha256"])
    packet_sha=_sha(_canonical(packet))
    _require(packet_sha == p["packet_sha256"] == analysis["input_sha256"] == expected_math["packet_sha256"])
    _require(_sha(_canonical(recipe)) == expected_math["spec_sha256"] and _sha(_canonical(analysis)) == expected_math["analysis_sha256"])
    return dict(schema_version=1,kind="stored_rf_baseband_observation_read",observation_name=name,
        storage=dict(status="content_verified",bytes=summary["storage"]["bytes"],sha256=summary["storage"]["sha256"],
                     scope="current_file_matches_recorded_summary"),
        source=dict(expected_source),math=dict(recipe=recipe,packet=packet,analysis=analysis),
        historical_context={k:source[k] for k in ("historical_assessment","outcome","failure","measurement_goal_succeeded")}
            | dict(producer_cli_exit_status=source["verification"]["producer_cli_exit_status"]),
        verification=dict(_FLAGS),execution_authorized=False,rerun_authorized=False)

def _preflight_json(text):
    """Lexical limits before json.loads allocates its object graph."""
    i=nodes=0; stack=[]; size=len(text)
    def node():
        nonlocal nodes
        nodes+=1; _require(nodes <= 32768)
    while i < size:
        c=text[i]
        if c.isspace():
            i+=1; continue
        if c in "{[":
            node(); _require(len(stack) <= 20); stack.append(c); i+=1; continue
        if c in "}]":
            _require(bool(stack) and stack.pop() == ("{" if c == "}" else "["))
            i+=1; continue
        if c in ",:":
            i+=1; continue
        if c == '"':
            i+=1; count=0
            while i < size and text[i] != '"':
                if text[i] == "\\":
                    i+=1; _require(i < size)
                    if text[i] == "u":
                        _require(i+4 < size); i+=4
                count+=1; _require(count <= 16384); i+=1
            _require(i < size); i+=1; j=i
            while j < size and text[j].isspace(): j+=1
            if j == size or text[j] != ":": node()
            continue
        if c in "-0123456789":
            j=i
            while i < size and text[i] in "-+0123456789.eE": i+=1
            _require(i-j <= 512); node(); continue
        if c in "tfn":
            j=i
            while i < size and text[i].isalpha(): i+=1
            _require(text[j:i] in ("true","false","null")); node(); continue
        _fail("evidence_invalid")
    _require(not stack)

def _parse(raw):
    try:
        text=raw.decode("utf-8")
        _preflight_json(text)
        def unique(pairs):
            result={}
            for k,v in pairs:
                _require(k not in result); result[k]=v
            return result
        def bad(_): _fail("evidence_invalid")
        value=json.loads(text,object_pairs_hook=unique,parse_constant=bad)
        value=_copy(value,_MAX_BODY)
        _require(_canonical(value)+b"\n" == raw)
        return value
    except (ValueError,UnicodeError,RecursionError,OverflowError):
        _fail("evidence_invalid")

def _root():
    def location(value,levels):
        _require(type(value) is str and Path(value).is_absolute(),"path_invalid")
        tail=ntpath.splitdrive(value)[1]
        _require(not value.startswith(("\\\\","//")) and re.search(r"[\\/]{2}",tail) is None
                 and all(_native._valid_segment(p) for p in re.split(r"[\\/]",tail) if p),"path_invalid")
        return _native._local_path(str(Path(value).absolute().parents[levels]))
    root=location(__file__,2)
    _require(location(_native.__file__,1) == root,"path_invalid")
    return root

def _read(fd,limit,suffix):
    os.lseek(fd,0,os.SEEK_SET); data=bytearray()
    while True:
        part=os.read(fd,min(65536,limit-len(data)+1))
        if not part: return bytes(data)
        data.extend(part); _require(len(data) <= limit,suffix)

def _open(tree,path):
    tree.directory(path.parent)
    try: fd=tree.backend.open_read(path,pin=True)
    except FileNotFoundError: return None
    info=tree.backend.info(fd,directory=False)
    return dict(path=path,fd=fd,stamp=_native._stamp(info))

def _directories(tree):
    for path,identity in tuple(tree.directories.items()):
        info=tree.backend.info(tree.backend.directories[path],directory=True)
        _require((info.st_dev,info.st_ino) == identity,"input_changed")

def _recheck(tree,entry):
    current=_open(tree,entry["path"])
    _require(current is not None and current["stamp"] == entry["stamp"],"input_changed")
    _require(_native._stamp(tree.backend.info(entry["fd"],directory=False)) == entry["stamp"],"input_changed")

def _close(backend):
    """Keep the first surfaced failure; close only still-owned known objects."""
    first=None; known={}; unknown=[]; directories=dict(backend.directories)
    def remember(error):
        nonlocal first
        if first is None: first=error
    for fd in tuple(backend.held):
        try:
            s=os.fstat(fd); known[fd]=(s.st_dev,s.st_ino,s.st_mode)
        except BaseException as error:
            remember(error); unknown.append(fd)
    try: backend.close()
    except BaseException as error: remember(error)
    remaining=[]
    for fd,identity in known.items():
        for _ in range(2):
            try:
                s=os.fstat(fd)
                if (s.st_dev,s.st_ino,s.st_mode) != identity:
                    remember(RfSignalWaveformObservationReadError(_PREFIX+"unavailable")); break
                os.close(fd); break
            except OSError as error:
                if error.errno == errno.EBADF: break
                remember(error)
            except BaseException as error: remember(error)
        try:
            s=os.fstat(fd)
            if (s.st_dev,s.st_ino,s.st_mode) == identity:
                remaining.append(fd); remember(RfSignalWaveformObservationReadError(_PREFIX+"unavailable"))
        except OSError as error:
            if error.errno != errno.EBADF: remember(error)
        except BaseException as error:
            remaining.append(fd); remember(error)
    for fd in unknown:
        try: os.fstat(fd); remaining.append(fd)
        except OSError as error:
            if error.errno != errno.EBADF: remaining.append(fd)
        except BaseException: remaining.append(fd)
    backend.held[:]=remaining
    backend.directories.clear()
    backend.directories.update({p:fd for p,fd in directories.items() if fd in remaining})
    return first

def _public(error,stage):
    if not isinstance(error,Exception): return error
    if type(error) is RfSignalWaveformObservationReadError: return error
    suffix="invalid_argument" if stage == "arguments" else "unavailable"
    if type(error) is _native.ControlPacketPrepareError and error.code == "packet_prepare_path_invalid":
        suffix="input_changed" if stage == "post" else "path_invalid"
    return RfSignalWaveformObservationReadError(_PREFIX+suffix)

def read_rf_baseband_observation(observation_name, *, expected_summary, workspace_root=None) -> dict:
    """Read only an explicitly named stored version, bound to original summary."""
    backend=result=primary=None; stage="arguments"
    try:
        _name(observation_name,"invalid_argument")
        summary=_summary(expected_summary,observation_name)
        stage="environment"
        root=_root(); backend=_native._WindowsIO(); source_tree=_native._Tree(root,backend)
        helper=_open(source_tree,root/"labflow/control_packet_prepare.py")
        _require(helper is not None and helper["stamp"][2] <= 65536,"unavailable")
        helper_raw=_read(helper["fd"],65536,"unavailable")
        normalized=helper_raw.replace(b"\r\n",b"\n")
        _require((len(normalized),_sha(normalized)) == (_PINS[3][1],_PINS[3][2]),"unavailable")
        _require(_native._stamp(backend.info(helper["fd"],directory=False)) == helper["stamp"],"input_changed")
        from ..managed_artifact_workspace import artifact_local_root
        local=artifact_local_root(workspace_root=workspace_root)
        stage="storage"
        tree=_native._Tree(local,backend)
        folder=local/"rf-waveform-observations"/observation_name
        try: tree.directory(folder)
        except FileNotFoundError: _fail("not_found")
        marker=folder/"failure.json"
        _require(_open(tree,marker) is None,"incomplete")
        pending=_open(tree,folder/"observation.pending.json")
        final=_open(tree,folder/"observation.json")
        if pending is None and final is None: _fail("not_found")
        _require(pending is not None and final is not None,"incomplete")
        _require(pending["stamp"][:2] == final["stamp"][:2] and pending["stamp"] == final["stamp"],"incomplete")
        _require(final["stamp"][2] <= _MAX_FILE,"evidence_invalid")
        raw=_read(final["fd"],_MAX_FILE,"evidence_invalid")
        _require(_native._stamp(backend.info(final["fd"],directory=False)) == final["stamp"]
                 and len(raw) == final["stamp"][2],"input_changed")
        _require(len(raw) == summary["storage"]["bytes"] and _sha(raw) == summary["storage"]["sha256"],"record_mismatch")
        stage="validation"
        value=_parse(raw); result=_bundle(value,summary,observation_name)
        result=_copy(result,_MAX_BODY)
        stage="post"
        _directories(tree); _recheck(tree,pending); _recheck(tree,final)
        _require(_read(final["fd"],_MAX_FILE,"input_changed") == raw,"input_changed")
        _require(_native._stamp(backend.info(final["fd"],directory=False)) == final["stamp"],"input_changed")
        _require(_open(tree,marker) is None,"input_changed")
        _recheck(source_tree,helper)
        _require(_read(helper["fd"],65536,"input_changed") == helper_raw,"input_changed")
        _require(_native._stamp(backend.info(helper["fd"],directory=False)) == helper["stamp"],"input_changed")
        _directories(tree)
        _directories(source_tree)
    except BaseException as error:
        primary=_public(error,stage)
    finally:
        if backend is not None:
            try:
                error=_close(backend)
            except BaseException as caught:
                error=caught
            if primary is None and error is not None: primary=_public(error,"cleanup")
    if primary is not None: raise primary from None
    return result
