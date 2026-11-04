"""Run-scoped evidence and cancellation for source-scoped radio measurements."""
from copy import deepcopy
from pathlib import Path
import threading
import uuid

from .hardware_run import RunEvidence, Cancellation, atomic_json, only_cancellation, utc
from .errors import error_details
from .profiles import load_profile
from .radio_contracts import RADIOS, RadioBlocked, check_radio, validate_plan, radio_devices
from .radio_scan_contracts import SCAN_FAULTS
from .radio_simulation import RadioWorld
from .radio_adapters import RadioLab, checkpoint, pause
from .evaluation import Evaluation

FAULTS = ("start-timeout", "measure-timeout", "stop-timeout", "cancel-after-sample") + SCAN_FAULTS


def load_radio_profiles(plan, directory):
    validate_plan(plan)
    if directory is None:
        raise ValueError("Hardware requires an explicit profiles directory")
    names = sorted(radio_devices(plan))
    return {name: load_profile(Path(directory) / (name + ".json")) for name in names}


def run_radio(plan, mode, output_dir, *, profiles=None, profiles_dir=None, cancelled=None, cancel_file=None, fault=None, evaluation=None):
    if mode not in ("simulation", "hardware"):
        raise ValueError("Explicit simulation/hardware mode required")
    plan, profiles = deepcopy(plan), deepcopy(profiles)
    evaluation = deepcopy(evaluation)
    simulated = mode == "simulation"
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "run_id": str(uuid.uuid4()), "status": "running", "mode": mode,
              "simulated": simulated, "physical_verified": False, "physical_shutdown_verified": False,
              "fcc_verdict": None, "started_utc": utc(), "connection_attempted": False,
              "cleanup_scope_succeeded": False, "requested_plan": plan}
    atomic_json(target / "run.json", report)
    evidence = RunEvidence(target, report["run_id"], simulated=simulated)
    event = cancelled if cancelled is not None else threading.Event()
    token = Cancellation(event, cancel_file, evidence)
    world, lab, measurement, errors = None, None, None, []
    evaluator = None
    if evaluation is not None:
        report["assessment"] = {"verdict": "NOT_EVALUATED", "reasons": ["Preflight or execution incomplete"]}
    try:
        evidence.open()
        evidence.handles["observations.jsonl"] = (target / "observations.jsonl").open("x", encoding="utf-8")
        validate_plan(plan)
        if profiles_dir is not None:
            if profiles is not None or simulated:
                raise ValueError("profiles_dir is exclusive to hardware and explicit profile objects")
            profiles = load_radio_profiles(plan, profiles_dir)
        atomic_json(target / "inputs.json", {"run_id": report["run_id"], "plan": plan, "profiles": profiles, "evaluation": evaluation})
        report["preflight"] = check_radio(plan, mode, profiles)
        if evaluation is not None:
            evaluator = Evaluation(evaluation, plan, simulated=simulated)
            report["evaluation_preflight"] = evaluator.preflight()
        if fault is not None and (not simulated or fault not in FAULTS):
            raise ValueError("Fault injection requires a supported simulation-only fault")
        if fault in SCAN_FAULTS and plan["schema_version"] != 2:
            raise ValueError("Facility faults require a schema-2 scan plan")
        checkpoint(token)
        world = RadioWorld(plan) if simulated else None
        if world is not None: world.inject(fault)
        lab = RadioLab(plan, profiles, evidence, world)
        if plan["schema_version"] == 2:
            from .radio_scan import measure_radio_scan
            measurement = measure_radio_scan(lab, token, event, fault, evaluator)
        else:
            measurement = measure_fixed(lab, token, event, fault)
        report["cleanup_scope_succeeded"] = True
        evidence.require_healthy()
        checkpoint(token)
    except BaseException as error:
        errors.append(error)
    finally:
        snapshots = {
            "phone-log.json": lab.phone_log() if lab else {"session_opened": False, "events": [], "scope": "no_source_opened"},
            "identity.json": {"devices": lab.identities() if lab else {}}}
        if world is not None:
            snapshots["simulation.json"] = {"model": "dgm-radio-envelope-v1", "final_state": world.snapshot(), "faults": world.events}
        for filename, value in snapshots.items():
            try:
                atomic_json(target / filename, {**value, "run_id": report["run_id"], "simulated": simulated})
            except Exception as error:
                evidence._failure(filename, error)
        evidence.close()
    if evidence.errors:
        errors.append(OSError("Evidence persistence failed: " + repr(evidence.errors)))
    report.update(finished_utc=utc(), saved_samples=evidence.sample_count, recording_errors=evidence.errors,
                  cancellation_requested=token.requested(), connection_attempted=bool(lab and lab.connection_attempted))
    if errors:
        failure = errors[0] if len(errors) == 1 else BaseExceptionGroup("Radio and recording failures", errors)
        report.update(status="blocked" if isinstance(failure, RadioBlocked) else "cancelled" if only_cancellation(failure) else "failed",
                      error=error_details(failure))
        filename = "failure.json"
    else:
        report.update(status="completed", measurement=measurement)
        filename = "result.json"
    if evaluator is not None: report["assessment"] = evaluator.summary(completed=not errors)
    try:
        atomic_json(target / filename, report)
    except Exception as error:
        if errors:
            raise BaseExceptionGroup("Radio failed and final report could not be saved", [*errors, error]) from None
        report.pop("measurement", None)
        report.update(status="failed", error=error_details(error))
        if evaluator is not None: report["assessment"] = evaluator.summary(completed=False)
        filename = "failure.json"
        try: atomic_json(target / filename, report)
        except Exception as fallback:
            raise ExceptionGroup("Result and failure report storage failed", [error, fallback]) from None
    return {"run_id": report["run_id"], "status": report["status"], "simulated": simulated,
            "report": str(target / filename), "samples": evidence.sample_count, "physical_verified": False,
            **({"peak": measurement["sampled_peak"]} if report["status"] == "completed" and measurement and "sampled_peak" in measurement else {}),
            **({"assessment": report["assessment"]} if "assessment" in report else {}),
            **({"error": report["error"]} if "error" in report else {})}


def measure_fixed(lab, token, event, fault):
    plan, evidence = lab.plan, lab.evidence
    peaks = []
    with lab.open("SpectrumAnalyzer") as analyzer, analyzer.active():
        before = lab.acquire(analyzer, "before-source")
        evidence.require_healthy()
        if plan["radio"] == "nfc" and before["peak_dbm"] > plan["verification"]["off_threshold_dbm"]:
            raise RuntimeError("NFC baseline is not quiet; cannot attribute PRBS start")
        with lab.active_source(analyzer, token):
            pause(plan["settle_seconds"], token)
            for index in range(plan["sample_count"]):
                checkpoint(token)
                row = lab.acquire(analyzer, "sample")
                row.update(index=index, radio=plan["radio"], backend=plan["backend"])
                evidence.sample(row)
                peaks.append(row["peak_dbm"])
                if fault == "cancel-after-sample": event.set()
                checkpoint(token)
        after = lab.acquire(analyzer, "after-source")
        checkpoint(token)
        measurement = {"radio": plan["radio"], "backend": plan["backend"], "sample_count": len(peaks),
                       "peak_trace_dbm": max(peaks), "before": before, "after": after,
                       "note": "Raw swept-spectrum levels; no correction, modulation verification or conformity verdict"}
    return measurement
