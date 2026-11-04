"""Reusable WLAN workflow. The provider selects simulation or explicit site profiles."""
from contextlib import ExitStack, closing
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import uuid

from dgm_lab.analyzers import Sweep
from dgm_lab.core import InstrumentError, number
from dgm_lab.transport import JsonlLog
from dgm_rf import WlanTxConfig
from dgm_rf.core import wlan_tx_plan
from .errors import error_details
from .virtual_lab import VirtualLab
from .virtual_world import Scenario, Fault


@dataclass(frozen=True)
class WlanScan:
    center_hz: float = 6.035e9
    tx: WlanTxConfig = field(default_factory=lambda: WlanTxConfig(3, 9, 17, 15, 1, 5, 1, "0.0", 1000, 1000))
    heights_cm: tuple = (100.0, 200.0)
    angles_deg: tuple = (0.0, 90.0, 180.0)
    polarizations: tuple = ("H", "V")
    voltage: float = 5.0
    current: float = 1.0
    motion_timeout: float = 2.0

    def validate(self):
        number(self.center_hz, "center_hz", 120e6, 8.28e9)
        number(self.voltage, "voltage", 0, 5)
        number(self.current, "current", 0, 1)
        number(self.motion_timeout, "motion_timeout", 0.01, 3600)
        wlan_tx_plan(self.tx)
        for values, name, low, high in [(self.heights_cm, "height", 100, 400), (self.angles_deg, "angle", 0, 360)]:
            if not isinstance(values, (tuple, list)) or not values:
                raise ValueError("Nonempty scan grid required")
            for value in values:
                number(value, name, low, high)
                if abs(value * 10 - round(value * 10)) > 1e-6:
                    raise ValueError("Motion grid resolution is 0.1")
        if not self.polarizations or any(p not in {"H", "V"} for p in self.polarizations):
            raise ValueError("Polarization must be H or V")
        if len(self.heights_cm) * len(self.angles_deg) * len(self.polarizations) > 500:
            raise ValueError("Maximum 500 samples per scan")


def _dbm(measurement):
    if measurement.unit == "dBm":
        return measurement.value
    if measurement.unit == "W" and measurement.value > 0:
        return 10 * math.log10(measurement.value) + 30
    raise InstrumentError(f"Unsupported power result: {measurement}")


def measure_wlan(lab, plan=None, *, cancelled=None, on_sample=None):
    """Identical operation sequence for VirtualLab and HardwareLab.

    Caller owns hardware permits, profile validation, RF/position limits and logs.
    Values are raw instrument readings. No antenna correction or FCC verdict.
    on_sample runs inside cleanup scopes: an exception stops this run.
    """
    plan = plan or WlanScan()
    plan.validate()
    lab.validate_wlan(plan)
    check = cancelled.is_set if cancelled is not None else lambda: False
    def checkpoint():
        if check():
            raise InterruptedError("WLAN scan cancelled")
    checkpoint()  # already-cancelled run must perform no I/O
    samples = []
    sweep = Sweep(plan.center_hz - 120e6, plan.center_hz + 120e6, 1e6, 1e6, 10, 10, points=101, sweep_seconds=0.01)
    with ExitStack() as stack:
        sessions = {name: stack.enter_context(lab.open(name)) for name in
                    ("OdaEx", "Co3000", "OspSwitch", "SamsungAt", "SpectrumAnalyzer", "UsbPowerSensor")}
        power, motion, route, phone, analyzer, sensor = sessions.values()
        power.call("configure", voltage=plan.voltage, current=plan.current)
        sensor.call("configure_average", frequency_hz=plan.center_hz)
        for session in (power, motion, analyzer, sensor):
            stack.enter_context(session.active())
        stack.enter_context(route.active(name="dut"))
        off_before = sensor.call("read_power")
        with phone.active(config=plan.tx, cancelled=cancelled):
            for polarization in plan.polarizations:
                motion.call("polarize", axis="MA1", orientation=polarization, timeout=plan.motion_timeout, cancelled=check)
                for height in plan.heights_cm:
                    motion.call("move", axis="MA1", value=height, timeout=plan.motion_timeout, cancelled=check)
                    for angle in plan.angles_deg:
                        checkpoint()
                        motion.call("move", axis="DT1", value=angle, timeout=plan.motion_timeout, cancelled=check)
                        before = [motion.call("position", axis=axis) for axis in ("MA1", "DT1")]
                        trace = analyzer.call("acquire", config=sweep)
                        measured = sensor.call("read_power")
                        after = [motion.call("position", axis=axis) for axis in ("MA1", "DT1")]
                        checkpoint()
                        for states in (before, after):
                            if (any(s.busy for s in states) or abs(states[0].value - height) > 0.1
                                    or abs(states[1].value - angle) > 0.1 or states[0].polarization != "P" + polarization):
                                raise InstrumentError("Position changed or disagrees with requested sample")
                        sample = {"index": len(samples), "height_cm": after[0].value, "angle_deg": after[1].value,
                                  "polarization": polarization, "sensor": asdict(measured), "power_dbm": _dbm(measured),
                                  "trace": asdict(trace), "simulated": lab.simulated}
                        samples.append(sample)
                        if on_sample:
                            on_sample(deepcopy(sample))
            peak = max(samples, key=lambda sample: sample["power_dbm"])
            motion.call("polarize", axis="MA1", orientation=peak["polarization"], timeout=plan.motion_timeout, cancelled=check)
            motion.call("move", axis="MA1", value=peak["height_cm"], timeout=plan.motion_timeout, cancelled=check)
            motion.call("move", axis="DT1", value=peak["angle_deg"], timeout=plan.motion_timeout, cancelled=check)
        off_after = sensor.call("read_power")
        checkpoint()
        result = {"simulated": lab.simulated, "physical_verified": False, "fcc_verdict": None,
                  "plan": asdict(plan), "samples": samples, "sampled_peak_index": peak["index"],
                  "returned_to_sampled_peak": True, "off_before": asdict(off_before), "off_after": asdict(off_after),
                  "phone_log": phone.phone_log, "identities": {key: value.info for key, value in sessions.items()}}
    return result  # only after every cleanup scope succeeds


def run_virtual(output_dir, *, scenario=None, plan=None, fault=None, cancelled=None):
    """Persist one new simulation run; failures keep partial raw data, never a result.json."""
    plan = plan or WlanScan()
    plan.validate()
    if scenario is not None and not isinstance(scenario, Scenario):
        raise TypeError("scenario must be Scenario")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "run_id": str(uuid.uuid4()), "status": "running", "simulated": True,
              "physical_verified": False, "fcc_verdict": None, "requested": asdict(plan),
              "started_utc": datetime.now(timezone.utc).isoformat(), "model": "dgm-behavioral-rf-v1"}
    with closing(JsonlLog(target / "traffic.jsonl")) as logger:
        def log(record):
            logger({"run_id": report["run_id"], "simulated": True, **record})
        lab = VirtualLab(scenario, log=log)
        report["scenario"] = lab.scenario
        try:
            if fault:
                lab.inject(fault)
            with (target / "samples.jsonl").open("x", encoding="utf-8") as samples:
                def save_sample(row):
                    samples.write(json.dumps({"run_id": report["run_id"], **row}) + "\n")
                    samples.flush()
                report["measurement"] = measure_wlan(lab, plan, cancelled=cancelled, on_sample=save_sample)
            report["status"] = "completed"
        except BaseException as exc:
            report["status"] = "failed"
            report["error"] = error_details(exc)
            raise
        finally:
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report["final_simulated_state"] = lab.state
            report["remaining_connections"] = lab.connections
            # Internal model truth and driver acknowledgements are different evidence.
            report["cleanup_scope_succeeded"] = report["status"] == "completed"
            filename = "result.json" if report["status"] == "completed" else "failure.json"
            (target / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (target / "observations.json").write_text(json.dumps({"run_id": report["run_id"], "simulated": True,
                "observations": lab.observations, "events": lab.events}, indent=2) + "\n", encoding="utf-8")
    return {"run_id": report["run_id"], "status": report["status"], "simulated": True,
            "result": str((target / "result.json").resolve()), "samples": len(report["measurement"]["samples"]),
            "peak": {key: report["measurement"]["samples"][report["measurement"]["sampled_peak_index"]][key]
                     for key in ("height_cm", "angle_deg", "polarization", "power_dbm")},
            "final_simulated_state": lab.state}
