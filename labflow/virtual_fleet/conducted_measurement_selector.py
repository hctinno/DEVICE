"""Unique native acquire intent, first completion, one original result build."""
import json

from . import conducted_twin_result as _result

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_OUTPUT_BYTES = 2 * 1024 * 1024


class _Hold(ValueError):
    def __init__(self, code, field, detail=None):
        self.code, self.field, self.detail = code, field, detail


def _need(condition, code, field, detail=None):
    if not condition:
        raise _Hold(code, field, detail)


def _base():
    return dict(schema_version=1, kind="conducted_measurement_selection", status="blocked", candidate=None,
        measurement_ref=None, request_id=None, reasons=[], result=None,
        verification=dict(policy="unique_same_run_sensor_acquisition", scope="provided_snapshots_only",
            builder_calls=0, fallback_attempted=False, model_execution_verified=False, hardware_verified=False,
            physical_verified=False, method_approval="not_assessed", conformity="not_assessed", execution_authority=False))


def _structure(stored, report):
    _need(stored["complete"] is True and not stored["unresolved_request_ids"]
          and not report["unresolved_request_ids"] and report["usage"]["reserved_ticks"] == 0
          and report["termination"] == {"reason": "policy_stop", "policy_claim": "completed"}
          and not any(e["type"] == "error" for e in stored["events"]), "execution_incomplete", "journal/report")
    header = stored["header"]
    _need(report["run_id"] == header["run_id"] and report["runtime_instance_id"] == header["runtime_instance_id"],
          "run_binding_mismatch", "run_report")
    intents, receipts, acquisitions, positions = {}, {}, [], {}
    previous = None
    for event in stored["events"]:
        payload = event["payload"]
        if event["type"] == "observation":
            observation = payload["observation"]
            _need(_result._natural(observation.get("tick")) and _result._natural(observation.get("setup_revision")),
                  "clock_unknown", "journal_read")
            if previous is not None:
                _need(observation["tick"] >= previous["tick"] and observation["setup_revision"] >= previous["setup_revision"],
                      "clock_regression", "journal_read")
            previous = observation
            positions[event["event_id"]] = event["sequence"]
        elif event["type"] == "intent":
            _need(previous is not None, "intent_context_missing", "journal_read")
            intents[payload["request_id"]] = (event, previous)
            body = payload["body"]
            if payload["operation"] == "execute" and body["device_id"] == "sensor" and body["action"] == "acquire":
                acquisitions.append(payload["request_id"])
        elif event["type"] == "receipt":
            intent, before = intents[payload["request_id"]]
            receipt, operation = payload["result"], intent["payload"]["operation"]
            expected_tick = before["tick"] + (intent["payload"]["body"]["ticks"] if operation == "advance" else 0)
            _need(_result._natural(receipt.get("tick")) and _result._natural(receipt.get("setup_revision"))
                  and receipt["tick"] == expected_tick and receipt["setup_revision"] >= before["setup_revision"],
                  "receipt_clock_mismatch", "journal_read")
            receipts[payload["request_id"]] = event
    _need(report["usage"]["logical_requests"] == len(intents), "report_request_mismatch", "run_report")
    refs = report["evidence"]["measurement_refs"]
    _need(all(ref in positions for ref in refs), "report_reference_invalid", "run_report.evidence")
    order = [positions[ref] for ref in refs]
    _need(order == sorted(set(order)), "report_reference_invalid", "run_report.evidence")
    _need(bool(acquisitions), "acquisition_missing", "journal_read")
    _need(len(acquisitions) == 1, "acquisition_ambiguous", "journal_read")
    request_id = acquisitions[0]
    _need(request_id in receipts, "acquisition_unresolved", "journal_read")
    intent, before = intents[request_id]
    receipt_event = receipts[request_id]
    receipt = receipt_event["payload"]["result"]
    _need(receipt.get("status") in ("ok", "pending") and receipt.get("device_id") == "sensor"
          and receipt.get("role") == "power_sensor" and receipt.get("synthetic") is True
          and receipt.get("hardware_verified") is False and receipt["setup_revision"] == before["setup_revision"],
          "acquisition_receipt_invalid", "journal_read")
    return request_id, intent, receipt_event


def _first_completion(stored, acquisition, output):
    request_id, intent, receipt_event = acquisition
    receipt = receipt_event["payload"]["result"]
    for event in stored["events"]:
        if event["type"] != "observation" or event["sequence"] <= receipt_event["sequence"]:
            continue
        observation = event["payload"]["observation"]
        devices = observation.get("devices")
        _need(type(devices) is dict and type(devices.get("sensor")) is dict, "completion_identity_unknown", "journal_read")
        sensor = devices["sensor"]
        values = sensor.get("values")
        _need(type(values) is dict, "completion_identity_unknown", "journal_read")
        if values.get("state") != "complete":
            continue
        candidate = dict(request_id=request_id, intent_ref=intent["event_id"], receipt_ref=receipt_event["event_id"],
                         measurement_ref=event["event_id"], sequence=event["sequence"])
        output["candidate"] = candidate
        outputs = values.get("outputs")
        packet = outputs.get("measurement") if type(outputs) is dict else None
        _need(type(packet) is dict and _result._natural(packet.get("acquisition_tick"))
              and _result._natural(packet.get("acquisition_setup_revision"))
              and packet["acquisition_setup_revision"] == observation["setup_revision"] == receipt["setup_revision"],
              "completion_identity_unknown", "journal_read")
        # No numeric/valid/unit/PASS/ref-membership filtering; the original parent owns those checks.
        return candidate
    raise _Hold("completion_missing", "journal_read")


def select_conducted_measurement(plan_input, setup_snapshot, journal_read, run_report):
    """Select only a unique acquisition's first completion; never try a later ref."""
    output, stage = _base(), "input"
    try:
        plan, setup, stored, report = _result._snapshot([plan_input, setup_snapshot, journal_read, run_report])
        _need(len(_result._canonical([plan, setup, stored, report])) <= MAX_INPUT_BYTES, "input_limit", "input")
        _need(type(setup) is list and len(setup) <= _result.MAX_SETUP_RECORDS, "input_limit", "setup_snapshot")
        stage = "plan_input"
        _result._plan(plan)
        stage = "journal_read"
        _result._journal(stored)
        stage = "run_report"
        validated = json.loads(_result._harness_payload(report))["report"]
        _need(validated is not None, "report_invalid", "run_report")
        stage = "selection"
        acquisition = _structure(stored, validated)
        candidate = _first_completion(stored, acquisition, output)
        stage = "builder"
        output["verification"]["builder_calls"] = 1
        result = _result.build_conducted_twin_result(plan, setup, stored, report, measurement_ref=candidate["measurement_ref"])
        _result._snapshot(result)
        _need(type(result) is dict and set(result) == set(_result._base())
              and type(result["schema_version"]) is int and result["schema_version"] == 1
              and result["kind"] == "conducted_twin_result" and result["status"] in ("recorded", "incomplete", "invalid")
              and len(_result._canonical(result)) <= _result.MAX_OUTPUT_BYTES, "builder_contract_invalid", "result")
        output["result"] = result
        _need(result["status"] == "recorded", "builder_" + result["status"], "result")
        output.update(status="selected", measurement_ref=candidate["measurement_ref"], request_id=candidate["request_id"])
        stage = "output"
        _need(len(_result._canonical(output)) <= MAX_OUTPUT_BYTES, "output_limit", "output")
    except _Hold as error:
        output.update(status="blocked", measurement_ref=None, request_id=None)
        output["reasons"].append(dict(code=error.code, field=error.field, detail=error.detail))
    except _result._Failure as error:
        output.update(status="blocked", measurement_ref=None, request_id=None)
        output["reasons"].append(dict(code="input_limit" if error.code in ("input_limit", "journal_limit", "plan_limit")
                                    else "input_invalid" if stage == "input" else "parent_validation",
                                    field=error.field, detail=dict(code=error.code)))
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError, StopIteration):
        output.update(status="blocked", measurement_ref=None, request_id=None)
        output["reasons"].append(dict(code="output_invalid" if stage == "output" else "input_invalid", field=stage, detail=None))
    return output
