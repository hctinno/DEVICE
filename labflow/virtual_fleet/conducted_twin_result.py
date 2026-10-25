"""Pure draft result from provided synthetic plan and same-run public evidence."""
import hashlib
import json
import math
import re
from fractions import Fraction

from ..calculations import calculate
from ..intake_conducted_twin_plan import _UNITS, _quoted_value
from ..virtual_fleet_server import _harness_payload
from . import journal
from .core import STATUSES
from .integration import _source_configuration
from .rf import _at

MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_PLAN_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 1_000_000
MAX_SETUP_RECORDS = 32
MAX_EVENTS = 4096
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PLAN_KEYS = set("schema_version kind status binding intake plan gaps verification".split())
_BINDING_KEYS = set("intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256".split())
_METHOD_KEYS = set("schema_version method_id method_version metric reference_plane source_settings basis_refs numeric_limit_dbm uncertainty_db assessment".split())
_SETUP_KEYS = set("request_id operation device_id action parameters receipt tick setup_revision".split())


class _Failure(ValueError):
    def __init__(self, code, field, status="invalid"):
        self.code, self.field, self.status = code, field, status


def _need(condition, code, field, status="invalid"):
    if not condition:
        raise _Failure(code, field, status)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _natural(value):
    return type(value) is int and value >= 0


def _snapshot(value):
    ancestors, nodes = set(), 0
    def copy(item, depth):
        nonlocal nodes
        nodes += 1
        _need(depth <= MAX_DEPTH and nodes <= MAX_NODES, "input_limit", "input")
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        _need(type(item) in (dict, list) and id(item) not in ancestors, "native_input_invalid", "input")
        ancestors.add(id(item))
        try:
            if type(item) is dict:
                result = {}
                for key, child in item.items():
                    _need(type(key) is str, "native_input_invalid", "input")
                    result[copy(key, depth + 1)] = copy(child, depth + 1)
                return result
            return [copy(child, depth + 1) for child in item]
        finally:
            ancestors.remove(id(item))
    result = copy(value, 0)
    _need(len(_canonical(result)) <= MAX_INPUT_BYTES, "input_limit", "input")
    return result


def _base():
    return dict(schema_version=1, kind="conducted_twin_result", status="incomplete", binding={},
                raw_measurement=None, setup_provenance=dict(records=[], topology=None, path=[]),
                calculation=dict(raw_power_w=None, raw_reference_plane=None, correction_ledger=[],
                                 target_reference_plane=None, corrected=None,
                                 conformity=dict(status="not_assessed", verdict=None,
                                                 numeric_limit_dbm=None, uncertainty_db=None)),
                gaps=[], failure=None,
                verification=dict(synthetic=True, hardware_verified=False, physical_verified=False,
                                  source_bytes="not_reopened", method_approval="not_assessed",
                                  trust_scope="provided_host_snapshots_and_hash_consistency",
                                  execution_authority=False))


def _gap(result, code, field, *, blocking=True):
    result["gaps"].append(dict(code=code, field=field, provided=None, blocking=blocking))


def _finish(result):
    if len(_canonical(result)) > MAX_OUTPUT_BYTES:
        result = _base()
        result.update(status="invalid", failure=dict(code="output_limit", field="output"))
        _gap(result, "output_limit", "output")
    return result


def _plan(value):
    _need(type(value) is dict and set(value) == _PLAN_KEYS, "plan_invalid", "plan_input")
    _need(type(value["schema_version"]) is int and value["schema_version"] == 1
          and value["kind"] == "intake_conducted_twin_plan_input", "plan_invalid", "plan_input")
    _need(len(_canonical(value)) <= MAX_PLAN_BYTES, "plan_limit", "plan_input")
    _need(type(value["plan"]) is dict and set(value["plan"]) == _METHOD_KEYS
          and type(value["binding"]) is dict and set(value["binding"]) == _BINDING_KEYS,
          "plan_invalid", "plan_input")
    _need(value["binding"]["plan_sha256"] == _sha(value["plan"]), "plan_hash_mismatch", "plan_input.binding")
    _need(type(value["gaps"]) is list and all(type(gap) is dict and set(gap) == {"code", "field", "provided", "blocking"}
          and type(gap["blocking"]) is bool for gap in value["gaps"]), "plan_invalid", "plan_input.gaps")
    if value["status"] == "blocked" or any(gap["blocking"] for gap in value["gaps"]):
        raise _Failure("plan_blocked", "plan_input", "incomplete")
    _need(value["status"] == "ready_for_simulation", "plan_invalid", "plan_input.status")
    _need(value["verification"] == dict(evidence="validated_in_memory", current_version="caller_snapshot_only",
          source_bytes="not_reopened", regulatory="not_assessed", measurement_prediction="not_assessed",
          execution_authority=False) and value["verification"]["execution_authority"] is False,
          "plan_verification_invalid", "plan_input.verification")
    intake = value["intake"]
    _need(type(intake) is dict and set(intake) == {"facts", "source_facts", "missing_fields", "follow_up_missing_fields", "questions"}
          and type(intake["facts"]) is dict and all(type(intake[key]) is list for key in
          ("source_facts", "missing_fields", "follow_up_missing_fields", "questions")), "plan_intake_invalid", "plan_input.intake")
    binding, plan = value["binding"], value["plan"]
    _need(type(binding["intake_id"]) is str and bool(binding["intake_id"])
          and type(binding["revision"]) is int and binding["revision"] > 0
          and all(type(binding[key]) is str and _SHA.fullmatch(binding[key])
                  for key in _BINDING_KEYS - {"intake_id", "revision"}), "plan_binding_invalid", "plan_input.binding")
    _need(type(plan["schema_version"]) is int and plan["schema_version"] == 1
          and plan["method_id"] == "conducted_synthetic" and type(plan["method_version"]) is int
          and plan["method_version"] == 1 and plan["metric"] in ("on", "time", "peak")
          and plan["reference_plane"] == "source_output" and plan["numeric_limit_dbm"] is None
          and plan["uncertainty_db"] is None and plan["assessment"] == "not_assessed",
          "plan_method_invalid", "plan_input.plan")
    source = _source_configuration(plan["source_settings"])
    _need(type(plan["basis_refs"]) is dict and set(plan["basis_refs"]) == set(source),
          "plan_basis_invalid", "plan_input.plan.basis_refs")
    for key, declared in source.items():
        basis = plan["basis_refs"][key]
        _need(type(basis) is dict and set(basis) == {"kind", "value", "unit", "evidence"},
              "plan_basis_invalid", "plan_input.plan.basis_refs")
        kind, value, unit, refs = (basis[field] for field in ("kind", "value", "unit", "evidence"))
        _need(type(kind) is str and kind in ("source_cited", "developer_declared_synthetic")
              and type(unit) is str and unit in _UNITS[key] and type(refs) is list and len(refs) <= 20
              and (bool(refs) if kind == "source_cited" else not refs),
              "plan_basis_invalid", "plan_input.plan.basis_refs")
        same = (type(value) is str and value == declared if key == "modulation" else
                _number(value) and Fraction(str(value)) * Fraction(str(_UNITS[key][unit])) == Fraction(str(declared)))
        _need(same, "plan_basis_invalid", "plan_input.plan.basis_refs")
        if kind == "source_cited":
            # Existing D1 quantity/quote rule; original source bytes remain upstream.
            try:
                quoted = (all(type(ref) is dict and type(ref.get("quote")) is str for ref in refs)
                          and _quoted_value(basis, key))
            except ArithmeticError:
                quoted = False
            _need(quoted, "plan_basis_invalid", "plan_input.plan.basis_refs")
    return source


def _journal(value):
    fields = {"schema_version", "kind", "header", "events", "integrity", "complete", "unresolved_request_ids", "resumable"}
    _need(type(value) is dict and set(value) == fields and type(value["schema_version"]) is int
          and value["schema_version"] == 1 and value["kind"] == "operator_journal_read"
          and value["resumable"] is False, "journal_invalid", "journal_read")
    events, header = value["events"], value["header"]
    _need(type(events) is list and len(events) <= MAX_EVENTS, "journal_limit", "journal_read.events")
    expected = journal._header(header["run_id"], header["runtime_instance_id"], header["provenance"])
    _need(_canonical(header) == _canonical(expected), "journal_header_invalid", "journal_read.header")
    state = journal._EventState(expected)
    record, line = journal._record("header", expected, journal._ZERO_HASH)
    file_hash, previous, size = hashlib.sha256(line), record["sha256"], len(line)
    for event in events:
        validated = state.validate(event)
        record, line = journal._record("event", validated, previous)
        state.apply(validated)
        file_hash.update(line)
        previous, size = record["sha256"], size + len(line)
    integrity = value["integrity"]
    _need(type(integrity) is dict and set(integrity) == {"status", "algorithm", "head_sha256", "file_sha256", "event_count"}
          and integrity["status"] == "verified" and integrity["algorithm"] == "sha256"
          and type(integrity["event_count"]) is int and integrity["event_count"] == len(events)
          and integrity["head_sha256"] == previous and integrity["file_sha256"] == file_hash.hexdigest()
          and size <= journal.MAX_FILE_BYTES, "journal_integrity_invalid", "journal_read.integrity")
    _need(type(value["complete"]) is bool and value["complete"] == (state.terminated and not state.pending)
          and value["unresolved_request_ids"] == list(state.pending), "journal_state_invalid", "journal_read")
    return header["provenance"]


def _setup(records):
    _need(type(records) is list and len(records) <= MAX_SETUP_RECORDS, "setup_limit", "setup_snapshot")
    _need(bool(records), "setup_missing", "setup_snapshot", "incomplete")
    requests, configurations, selections = set(), {}, {}
    tick = revision = 0
    for index, row in enumerate(records):
        field = "setup_snapshot." + str(index)
        _need(type(row) is dict and set(row) == _SETUP_KEYS, "setup_invalid", field)
        request = journal._identifier(row["request_id"])
        _need(request not in requests, "setup_duplicate_request", field)
        requests.add(request)
        _need(row["operation"] in ("execute", "advance"), "setup_invalid", field)
        receipt = row["receipt"]
        _need(receipt is not None, "setup_partial", field, "incomplete")
        _need(type(receipt) is dict and receipt.get("synthetic") is True
              and receipt.get("hardware_verified") is False and type(receipt.get("values")) is dict
              and _natural(row["tick"]) and _natural(row["setup_revision"])
              and type(receipt.get("tick")) is int and type(receipt.get("setup_revision")) is int
              and row["tick"] == receipt["tick"] and row["setup_revision"] == receipt["setup_revision"]
              and row["tick"] >= tick and row["setup_revision"] >= revision, "setup_receipt_invalid", field)
        _need(receipt.get("status") in ("ok", "pending"), "setup_failed", field, "incomplete")
        parameters = row["parameters"]
        if row["operation"] == "execute":
            _need(type(row["device_id"]) is str and type(row["action"]) is str
                  and receipt.get("device_id") == row["device_id"]
                  and (parameters is None or type(parameters) is dict), "setup_identity_invalid", field)
            if row["action"] == "configure":
                configurations[row["device_id"]] = (index, row)
            if row["action"] == "select_path":
                selections[row["device_id"]] = parameters
        else:
            _need(row["device_id"] is None and row["action"] is None and type(parameters) is dict
                  and set(parameters) == {"ticks"} and type(parameters["ticks"]) is int
                  and parameters["ticks"] > 0 and row["tick"] == tick + parameters["ticks"]
                  and receipt["values"].get("advanced_ticks") == parameters["ticks"], "setup_advance_invalid", field)
        tick, revision = row["tick"], row["setup_revision"]
    _need(records[-1]["device_id"] == "dut" and records[-1]["action"] == "stop",
          "setup_partial", "setup_snapshot", "incomplete")
    return configurations, selections


def _extract(result, stored, ref):
    if type(stored) is not dict or type(stored.get("events")) is not list:
        return
    for event in stored["events"]:
        if type(event) is dict and event.get("event_id") == ref and event.get("type") == "observation":
            payload = event.get("payload")
            if type(payload) is not dict:
                return
            observation = payload.get("observation", {})
            devices = observation.get("devices", {}) if type(observation) is dict else {}
            sensor = devices.get("sensor", {}) if type(devices) is dict else {}
            values = sensor.get("values", {}) if type(sensor) is dict else {}
            if type(values) is not dict:
                return
            packet = values.get("outputs", {}).get("measurement") if type(values.get("outputs", {})) is dict else None
            if type(packet) is dict:
                header = stored.get("header")
                provenance = header.get("provenance") if type(header) is dict else None
                quantity = provenance.get("quantity") if type(provenance) is dict else None
                result["raw_measurement"] = dict(packet=packet, event_id=ref, sequence=event.get("sequence"),
                    device_id="sensor", tick=observation.get("tick"), setup_revision=observation.get("setup_revision"),
                    quantity=quantity, reference_plane=quantity.get("reference_plane") if type(quantity) is dict else None)
            return


def _node(observation, topology, identity):
    node = observation["devices"][identity]
    profile = next(item["profile_id"] for item in topology["devices"] if item["id"] == identity)
    _need(type(node) is dict and node.get("device_id") == identity and node.get("profile_id") == profile
          and node.get("status") == "ok" and node.get("synthetic") is True
          and node.get("hardware_verified") is False and type(node.get("tick")) is int
          and type(node.get("setup_revision")) is int and node["tick"] == observation["tick"]
          and node["setup_revision"] == observation["setup_revision"], "measurement_invalid", "observation." + identity)
    return node


def _path(observation, topology, selections, source):
    _need(type(topology) is dict and set(topology) == {"devices", "connections"}
          and type(topology["devices"]) is list and type(topology["connections"]) is list,
          "topology_invalid", "topology")
    ids = [node["id"] for node in topology["devices"]]
    _need(len(ids) == len(set(ids)) and "dut" in ids and "sensor" in ids, "topology_invalid", "topology")
    edges, current, visited = [], "sensor", set()
    while current != "dut":
        _need(current not in visited and len(visited) < 32, "path_ambiguous", "topology", "incomplete")
        visited.add(current)
        incoming = [edge for edge in topology["connections"] if edge["kind"] == "rf"
                    and edge["target"]["device_id"] == current]
        _need(len(incoming) == 1, "path_ambiguous", "topology", "incomplete")
        edge = incoming[0]
        edges.append(edge)
        current = edge["source"]["device_id"]
    edges.reverse()
    for edge in edges:
        identity = edge["source"]["device_id"]
        node = _node(observation, topology, identity)
        packet = node["values"]["outputs"][edge["source"]["port"]]
        _need(type(packet) is dict and packet.get("valid") is True and packet.get("status") == "ok"
              and packet.get("source_id") == identity and _number(packet.get("power_dbm")),
              "measurement_invalid", "observation." + identity)
        _need(identity != "dut" or packet["power_dbm"] == source["power_dbm"],
              "source_metadata_mismatch", "observation." + identity)
        for key in ("frequency_hz", "bandwidth_hz", "duty_cycle", "crest_factor_db"):
            _need(_number(packet.get(key)) and packet[key] == source[key],
                  "source_metadata_mismatch", "observation." + identity)
        _need(type(packet.get("modulation")) is str and packet["modulation"] == source["modulation"],
              "source_metadata_mismatch", "observation." + identity)
        target = _node(observation, topology, edge["target"]["device_id"])
        if target["role"] == "rf_switch":
            _need(selections.get(target["device_id"], {}).get("input_port") == edge["target"]["port"],
                  "path_selection_missing", "setup_snapshot", "incomplete")
    return edges


def _measurement(stored, report, ref, records, topology, source, selections):
    _need(stored["complete"] and not stored["unresolved_request_ids"],
          "journal_incomplete", "journal_read", "incomplete")
    _need(not report["unresolved_request_ids"] and report["usage"]["reserved_ticks"] == 0
          and report["termination"] == {"reason": "policy_stop", "policy_claim": "completed"},
          "execution_incomplete", "run_report", "incomplete")
    acquisition, baseline, previous, selected = None, None, None, None
    intents = {}
    for event in stored["events"]:
        payload = event["payload"]
        if event["type"] == "intent":
            _need(previous is not None, "evidence_context_missing", "journal_read")
            intents[payload["request_id"]] = (payload, previous)
        elif event["type"] == "receipt":
            intent, before = intents[payload["request_id"]]
            receipt, body = payload["result"], intent["body"]
            _need(type(receipt) is dict and type(receipt.get("status")) is str
                  and receipt["status"] in STATUSES and type(receipt.get("values")) is dict
                  and receipt.get("synthetic") is True and receipt.get("hardware_verified") is False
                  and _natural(receipt.get("tick")) and _natural(receipt.get("setup_revision"))
                  and receipt["setup_revision"] >= before["setup_revision"], "receipt_invalid", "journal_read")
            if intent["operation"] == "execute":
                identity = body["device_id"]
                profile = next(node["profile_id"] for node in topology["devices"] if node["id"] == identity)
                _need(receipt.get("device_id") == identity and receipt.get("profile_id") == profile
                      and receipt.get("role") == before["devices"][identity]["role"]
                      and receipt["tick"] == before["tick"], "receipt_identity_or_clock", "journal_read")
                if identity == "sensor" and body["action"] == "acquire":
                    acquisition = None
            else:
                _need(receipt["tick"] == before["tick"] + body["ticks"]
                      and type(receipt["values"].get("advanced_ticks")) is int
                      and receipt["values"]["advanced_ticks"] == body["ticks"],
                      "receipt_advance_clock", "journal_read")
            if intent["operation"] == "execute" and receipt.get("status") in ("ok", "pending"):
                if body["action"] in ("configure", "select_path") and body["device_id"] in {
                        "dut", "sensor", "attenuator", "switch", "switch_controller", "coupler"}:
                    raise _Failure("post_setup_configuration", "journal_read", "incomplete")
                if body["device_id"] == "sensor" and body["action"] == "acquire":
                    _need(receipt.get("device_id") == "sensor" and receipt.get("role") == "power_sensor"
                          and receipt.get("synthetic") is True and receipt.get("hardware_verified") is False
                          and type(receipt.get("tick")) is int and type(receipt.get("setup_revision")) is int
                          and receipt["tick"] == before["tick"] and receipt["setup_revision"] == before["setup_revision"],
                          "acquisition_invalid", "journal_read")
                    acquisition = receipt
        elif event["type"] == "observation":
            observation = payload["observation"]
            _need(type(observation) is dict and _natural(observation.get("tick"))
                  and _natural(observation.get("setup_revision")) and observation.get("synthetic") is True
                  and observation.get("hardware_verified") is False and type(observation.get("devices")) is dict,
                  "observation_invalid", "journal_read")
            if previous is not None:
                _need(observation["tick"] >= previous["tick"] and observation["setup_revision"] >= previous["setup_revision"],
                      "observation_clock_regression", "journal_read")
            if baseline is None:
                baseline = observation["tick"]
                _need(baseline >= records[-1]["tick"] and observation["setup_revision"] >= records[-1]["setup_revision"],
                      "setup_clock_mismatch", "journal_read")
            previous = observation
            if event["event_id"] == ref:
                selected = observation
                break
    _need(selected is not None, "measurement_reference_missing", "measurement_ref", "incomplete")
    sensor = _node(selected, topology, "sensor")
    _need(sensor.get("role") == "power_sensor", "measurement_invalid", "observation.sensor")
    packet = sensor["values"]["outputs"].get("measurement")
    _need(type(packet) is dict, "measurement_missing", "measurement_ref", "incomplete")
    _need(ref in report["evidence"]["measurement_refs"], "measurement_not_referenced", "measurement_ref", "incomplete")
    _need(packet.get("valid") is True and packet.get("status") == "ok" and packet.get("source_id") == "sensor"
          and packet.get("unit") == "dBm" and _number(packet.get("value")) and _number(packet.get("power_dbm"))
          and packet["value"] == packet["power_dbm"], "measurement_invalid", "measurement_ref")
    _need(acquisition is not None and _natural(packet.get("acquisition_tick"))
          and type(packet.get("acquisition_setup_revision")) is int
          and packet["acquisition_setup_revision"] == selected["setup_revision"] == acquisition["setup_revision"]
          and max(baseline, acquisition["tick"]) < packet["acquisition_tick"] <= selected["tick"],
          "measurement_stale", "measurement_ref")
    for key in ("frequency_hz", "duty_cycle", "crest_factor_db"):
        _need(_number(packet.get(key)) and packet[key] == source[key], "source_metadata_mismatch", "measurement_ref")
    edges = _path(selected, topology, selections, source)
    last = edges[-1]["source"]
    upstream = selected["devices"][last["device_id"]]["values"]["outputs"][last["port"]]
    _need(packet["value"] == upstream["power_dbm"], "measurement_path_conflict", "measurement_ref")
    return packet, selected, edges


def _convert(reading):
    try:
        value = calculate("rf_power", {"reading": reading, "unit": "dBm"})
        _need(type(value) is dict and set(value) == {"value", "unit"} and value["unit"] == "W"
              and _number(value["value"]) and value["value"] > 0, "unit_conversion_failed", "calculation", "incomplete")
        return value
    except (ValueError, TypeError, OverflowError):
        raise _Failure("unit_conversion_failed", "calculation", "incomplete") from None


def _correct(result, plan, quantity, packet, observation, edges, configurations):
    if quantity is None:
        _gap(result, "correction_basis_missing", "quantity")
        return
    keys = {"metric", "reference_plane", "loss_compensation_applied", "loss_compensation_sign"}
    if type(quantity) is not dict or set(quantity) != keys:
        _gap(result, "correction_basis_invalid", "quantity")
        return
    if plan["metric"] != "on" or quantity["metric"] != "on":
        _gap(result, "metric_mismatch", "quantity.metric")
        return
    if (quantity["reference_plane"] != "sensor_input" or type(quantity["loss_compensation_applied"]) is not bool
            or quantity["loss_compensation_applied"] is not False
            or not _number(quantity["loss_compensation_sign"]) or quantity["loss_compensation_sign"] != 1):
        _gap(result, "correction_basis_invalid", "quantity")
        return
    ledger = []
    for edge in edges[1:]:
        identity, port = edge["source"]["device_id"], edge["source"]["port"]
        role = observation["devices"][identity]["role"]
        field = ("attenuation_db" if role == "attenuator" else "loss_db" if role == "rf_switch"
                 else "coupling_db" if role == "coupler" and port == "coupled"
                 else "through_loss_db" if role == "coupler" and port == "rf" else None)
        _need(field is not None, "unsupported_path_device", "topology", "incomplete")
        configuration = configurations.get(identity)
        _need(configuration is not None and type(configuration[1]["parameters"]) is dict,
              "path_configuration_missing", "setup_snapshot", "incomplete")
        index, row = configuration
        settings = row["parameters"]
        _need(field in settings or role != "coupler" and "loss_table" in settings,
              "path_configuration_missing", "setup_snapshot", "incomplete")
        loss = settings[field] if role == "coupler" else _at(settings, field, "loss_table", packet["frequency_hz"])
        _need(_number(loss) and loss >= 0, "path_configuration_invalid", "setup_snapshot", "incomplete")
        ledger.append(dict(device_id=identity, output_port=port, setting=field, loss_db=loss,
                           record_index=index, request_id=row["request_id"], tick=row["tick"],
                           setup_revision=row["setup_revision"], propagation_db=-loss,
                           already_applied=False, compensation_db=loss))
    reading = math.fsum([packet["value"]] + [row["compensation_db"] for row in ledger])
    _need(_number(reading), "correction_overflow", "calculation", "incomplete")
    watts = _convert(reading)
    result["calculation"].update(correction_ledger=ledger,
        corrected=dict(value=reading, unit="dBm", power_w=watts["value"]))
    result["status"] = "recorded"


def build_conducted_twin_result(plan_input, setup_snapshot, journal_read, run_report, *, measurement_ref):
    """Return bounded evidence/calculation; host declarations are no physical attestation."""
    result = _base()
    try:
        plan_input, records, stored, report, ref = _snapshot(
            [plan_input, setup_snapshot, journal_read, run_report, measurement_ref])
        result["binding"].update(plan_input=plan_input, run_report=report)
        result["setup_provenance"]["records"] = records
        if type(plan_input) is dict and type(plan_input.get("gaps")) is list:
            result["gaps"] = plan_input["gaps"][:]
        _extract(result, stored, ref)
        source = _plan(plan_input)
        result["calculation"]["target_reference_plane"] = plan_input["plan"]["reference_plane"]
        report = json.loads(_harness_payload(report))["report"]
        _need(report is not None, "report_invalid", "run_report")
        provenance = _journal(stored)
        journal._identifier(ref)
        header = stored["header"]
        _need(report["run_id"] == header["run_id"] and report["runtime_instance_id"] == header["runtime_instance_id"],
              "run_binding_mismatch", "run_report")
        _need(provenance.get("plan_binding") == plan_input["binding"], "plan_binding_mismatch", "journal_read")
        _need(provenance.get("setup_sha256") == _sha(records), "setup_hash_mismatch", "setup_snapshot")
        topology = provenance.get("topology")
        _need(topology is not None and provenance.get("topology_sha256") == _sha(topology),
              "topology_hash_mismatch", "topology")
        result["setup_provenance"]["topology"] = topology
        result["binding"].update(plan_input_sha256=_sha(plan_input), setup_sha256=_sha(records),
            journal_file_sha256=stored["integrity"]["file_sha256"], journal_head_sha256=stored["integrity"]["head_sha256"],
            report_sha256=_sha(report), topology_sha256=_sha(topology), run_id=header["run_id"],
            runtime_instance_id=header["runtime_instance_id"], measurement_ref=ref)
        configurations, selections = _setup(records)
        dut = configurations.get("dut")
        _need(dut is not None and _source_configuration(dut[1]["parameters"]) == source,
              "source_settings_mismatch", "setup_snapshot")
        packet, observation, edges = _measurement(stored, report, ref, records, topology, source, selections)
        result["setup_provenance"]["path"] = edges
        quantity = provenance.get("quantity")
        result["calculation"]["raw_reference_plane"] = quantity.get("reference_plane") if type(quantity) is dict else None
        result["calculation"]["raw_power_w"] = _convert(packet["value"])
        _correct(result, plan_input["plan"], quantity, packet, observation, edges, configurations)
    except _Failure as error:
        result["status"] = error.status
        result["failure"] = dict(code=error.code, field=error.field)
        _gap(result, error.code, error.field)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError, StopIteration):
        result["status"] = "invalid"
        result["failure"] = dict(code="invalid_evidence", field="input")
        _gap(result, "invalid_evidence", "input")
    return _finish(result)
