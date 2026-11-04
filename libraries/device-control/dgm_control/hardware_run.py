"""Explicit hardware WLAN execution with incremental, run-scoped evidence."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, fields
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import threading
import uuid

from dgm_rf import WlanTxConfig
from .errors import error_details
from .profiles import load_profile
from .virtual_lab import HardwareLab, WLAN_DEVICES
from .virtual_recipe import WlanScan, measure_wlan
from .evaluation import Evaluation


def utc():
    return datetime.now(timezone.utc).isoformat()


def plan_from_dict(values):
    if not isinstance(values, dict) or set(values) != {f.name for f in fields(WlanScan)}:
        raise ValueError("Supply every WlanScan field explicitly; no hardware defaults")
    tx = values["tx"]
    if not isinstance(tx, dict) or set(tx) != {f.name for f in fields(WlanTxConfig)}:
        raise ValueError("Supply every WlanTxConfig field explicitly; no hardware defaults")
    plan = WlanScan(**{**deepcopy(values), "tx": WlanTxConfig(**tx)})
    plan.validate()
    return plan


def load_hardware_inputs(profiles_dir, plan_file, measurement_config=None):
    root = Path(profiles_dir)
    names = list(WLAN_DEVICES) + (["EmiReceiver"] if measurement_config is not None else [])
    return ({name: load_profile(root / f"{name}.json") for name in names},
            plan_from_dict(load_profile(plan_file)))


def check_hardware(profiles, plan, measurement_config=None):
    """Validate the current recipe and site limits without opening transports."""
    if not isinstance(plan, WlanScan):
        raise TypeError("Explicit WlanScan required")
    names = list(WLAN_DEVICES) + (["EmiReceiver"] if measurement_config is not None else [])
    if not isinstance(profiles, dict) or set(profiles) != set(names):
        raise ValueError("Exactly matching WLAN hardware profiles required: " + ", ".join(names))
    plan.validate()
    site = HardwareLab(profiles)
    site.validate_wlan(plan)
    receiver_check = None
    if measurement_config is not None:
        from .receiver_measurement import validate_measurement
        receiver_check = validate_measurement(measurement_config, plan, simulated=False, profile=profiles["EmiReceiver"])
        from .receiver_measurement import require_dedicated_receiver
        require_dedicated_receiver(profiles)
    parameters = {key: value["config"]["parameters"] for key, value in profiles.items()}
    motion = parameters["Co3000"]
    if motion.get("motion_enabled") is not True:
        raise ValueError("Recipe requires commissioned motion_enabled=true")
    for name, unit, targets in (("MA1", "CM", plan.heights_cm), ("DT1", "DG", plan.angles_deg)):
        axis = motion["axes"].get(name, {})
        if axis.get("unit") != unit or any(not axis["min"] <= n <= axis["max"] for n in targets):
            raise ValueError(f"Recipe requires {name}/{unit} and in-range targets")
    route = parameters["OspSwitch"]
    if route.get("switching_enabled") is not True or "dut" not in route["paths"]:
        raise ValueError("Recipe requires enabled OSP switching and commissioned dut path")
    power = parameters["OdaEx"]
    if plan.voltage > power["max_voltage"] or plan.current > power["max_current"]:
        raise ValueError("WLAN plan exceeds site power limits")
    if any(abs(v * 100 - round(v * 100)) > 1e-6 for v in (plan.voltage, plan.current)):
        raise ValueError("ODA voltage/current resolution is 0.01")
    if plan.center_hz + 120e6 > parameters["SpectrumAnalyzer"]["max_frequency_hz"]:
        raise ValueError("Sweep exceeds installed analyzer frequency range")
    return {"valid": True, "connection_attempted": False, "physical_verified": False,
            "devices": names, "plan": asdict(plan), "receiver_measurement": receiver_check,
            "remaining": ["Model/build and RF channel mapping", "Wiring and physical interlocks",
                          "Calibration, RF ON/OFF and independent stopping"]}


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class RunEvidence:
    """Recording failures stop the workflow, but never block cleanup wire writes."""
    def __init__(self, target, run_id, *, simulated=False):
        self.target, self.run_id = target, run_id
        self.simulated = simulated
        self.errors, self.handles = [], {}
        self.sample_count = 0
        self.lock = threading.RLock()

    def open(self):
        for filename in ("traffic.jsonl", "phone-traffic.jsonl", "samples.jsonl"):
            self.handles[filename] = (self.target / filename).open("x", encoding="utf-8")

    def _failure(self, filename, error):
        if not any(e["file"] == filename for e in self.errors):
            self.errors.append({"file": filename, "error": error_details(error)})

    def write(self, filename, value):
        with self.lock:
            try:
                handle = self.handles[filename]
                handle.write(json.dumps({**value, "run_id": self.run_id,
                                         "simulated": self.simulated, "recorded_utc": utc()},
                                        ensure_ascii=False, allow_nan=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            except Exception as error:
                self._failure(filename, error)

    def traffic(self, record):
        self.write("traffic.jsonl", record)
        if record.get("device_id") in {"PhoneAt", "NfcPrbs", "CmwLte"}:
            self.write("phone-traffic.jsonl", record)

    def sample(self, row):
        self.write("samples.jsonl", row)
        self.require_healthy()
        self.sample_count += 1

    def require_healthy(self):
        if self.errors:
            raise OSError("Evidence recording failed: " + json.dumps(self.errors, ensure_ascii=False))

    def close(self):
        for name, handle in self.handles.items():
            try:
                handle.close()
            except Exception as error:
                self._failure(name, error)


class Cancellation:
    def __init__(self, event=None, cancel_file=None, evidence=None):
        self.event = event if event is not None else threading.Event()
        self.cancel_file = Path(cancel_file) if cancel_file else None
        self.evidence = evidence

    def is_set(self):
        return self.requested() or bool(self.evidence and self.evidence.errors)

    def requested(self):
        return self.event.is_set() or (self.cancel_file is not None and self.cancel_file.exists())


@contextmanager
def cancellation_signals(event):
    """Defer interrupt/termination to checkpoints, including during cleanup."""
    previous = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, lambda *_: event.set())
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def only_cancellation(error):
    if isinstance(error, BaseExceptionGroup):
        return all(only_cancellation(child) for child in error.exceptions)
    return isinstance(error, (KeyboardInterrupt, InterruptedError))


class ObservedHardware:
    simulated = False

    def __init__(self, site, sessions, report):
        self.site, self.sessions, self.report = site, sessions, report

    def validate_wlan(self, plan):
        self.site.validate_wlan(plan)

    @contextmanager
    def open(self, device_id):
        self.report["connection_attempted"] = True
        with self.site.open(device_id) as session:
            self.sessions[device_id] = session
            yield session


def run_hardware(profiles, plan, output_dir, *, cancelled=None, cancel_file=None, evaluation=None, measurement_config=None):
    """Execute only explicit hardware profiles. Never substitute a simulator.

    Returns a summary after a durable result or failure. CLI maps failed to 2 and
    cancelled to 130. Invalid inputs are recorded if output_dir can be created.
    Kill/power loss may leave run.json=running; it is never a success marker.
    """
    profiles, plan = deepcopy(profiles), deepcopy(plan)
    evaluation = deepcopy(evaluation)
    measurement_config = deepcopy(measurement_config)
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=False)
    run_id = str(uuid.uuid4())
    report = {"schema_version": 1, "run_id": run_id, "status": "running", "simulated": False,
              "physical_verified": False, "fcc_verdict": None, "started_utc": utc(),
              "connection_attempted": False, "cleanup_scope_succeeded": False,
              "physical_shutdown_verified": False}
    atomic_json(target / "run.json", report)
    evidence = RunEvidence(target, run_id)
    token = Cancellation(cancelled, cancel_file, evidence)
    sessions, measurement, errors = {}, None, []
    evaluator = None
    if evaluation is not None:
        report["assessment"] = {"verdict": "NOT_EVALUATED", "reasons": ["Preflight or execution incomplete"]}
    try:
        evidence.open()
        evidence.handles["receiver-points.jsonl"] = (target / "receiver-points.jsonl").open("x", encoding="utf-8")
        atomic_json(target / "inputs.json", {"run_id": run_id, "profiles": profiles, "plan": asdict(plan), "evaluation": evaluation, "receiver_measurement": measurement_config})
        check_hardware(profiles, plan, measurement_config)
        if evaluation is not None: evaluator = Evaluation(evaluation, plan, simulated=False, measurement=measurement_config)
        if token.is_set():
            raise InterruptedError("Hardware run cancelled before connection")
        site = HardwareLab(profiles, log=evidence.traffic)
        observed = ObservedHardware(site, sessions, report)
        def save_point(row):
            evidence.write("receiver-points.jsonl", row)
            evidence.require_healthy()
        measurement = measure_wlan(observed, plan, cancelled=token, on_sample=evidence.sample, evaluation=evaluator,
                                   measurement_config=measurement_config, on_observation=save_point)
        report["cleanup_scope_succeeded"] = True
        evidence.require_healthy()
        if token.is_set():
            raise InterruptedError("Hardware run cancelled during final cleanup")
    except BaseException as error:
        errors.append(error)
    finally:
        # Sessions survive provider unwinding; native Controller logs remain readable.
        for filename, value in (
            ("phone-log.json", {"run_id": run_id, "simulated": False,
                                "session_opened": "PhoneAt" in sessions,
                                "events": sessions["PhoneAt"].phone_log if "PhoneAt" in sessions else []}),
            ("identity.json", {"run_id": run_id, "simulated": False,
                               "devices": {name: session.info for name, session in sessions.items()}})):
            try:
                atomic_json(target / filename, value)
            except Exception as error:
                evidence._failure(filename, error)
        evidence.close()
    if evidence.errors:
        errors.append(OSError("Evidence persistence failed: " + json.dumps(evidence.errors, ensure_ascii=False)))
    report.update(finished_utc=utc(), recording_errors=evidence.errors,
                  cancellation_requested=token.requested(),
                  opened_devices=list(sessions), saved_samples=evidence.sample_count)
    if errors:
        failure = errors[0] if len(errors) == 1 else BaseExceptionGroup("Run and recording failures", errors)
        report.update(status="cancelled" if only_cancellation(failure) else "failed", error=error_details(failure))
        filename = "failure.json"
    else:
        report.update(status="completed", measurement=measurement)
        filename = "result.json"
    if evaluator is not None: report["assessment"] = evaluator.summary(completed=not errors)
    # If final persistence fails, no successful result is published. Incremental files remain.
    try:
        atomic_json(target / filename, report)
    except Exception as error:
        if filename == "failure.json":
            raise BaseExceptionGroup("Run failed and failure report could not be persisted", [*errors, error]) from None
        report.pop("measurement", None)
        report.update(status="failed", error=error_details(error))
        if evaluator is not None: report["assessment"] = evaluator.summary(completed=False)
        filename = "failure.json"
        try:
            atomic_json(target / filename, report)
        except Exception as fallback_error:
            raise ExceptionGroup("Final result and failure report could not be persisted", [error, fallback_error]) from None
    return {"run_id": run_id, "status": report["status"], "simulated": False,
            "physical_verified": False, "report": str(target / filename),
            "samples": evidence.sample_count,
            **({"assessment": report["assessment"]} if "assessment" in report else {}),
            **({"error": report["error"]} if "error" in report else {})}
