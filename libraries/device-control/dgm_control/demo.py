from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from . import open_device, profile_template, error_details


def run_demo(output_dir, *, inject_failure=False):
    """Three production driver paths with in-memory peers; no hardware I/O."""
    from dgm_rf import WlanTxConfig
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=False)
    events, measurements = [], []
    report = {"schema_version": 1, "run_id": str(uuid.uuid4()), "started_utc": datetime.now(timezone.utc).isoformat(),
              "simulated": True, "physical_verified": False, "status": "running", "devices": []}
    power = motion = phone = None
    try:
        with open_device(profile_template("OdaEx", "simulation"), log=events.append) as power:
            report["devices"].append(power.info)
            power.call("configure", voltage=5, current=1)
            with power.active():
                measurements.append(asdict(power.call("read_voltage")))
                measurements.append(asdict(power.call("read_current")))
        with open_device(profile_template("Co3000", "simulation"), log=events.append) as motion:
            report["devices"].append(motion.info)
            with motion.active():
                measurements.append(asdict(motion.call("move", axis="DT1", value=90, timeout=2)))
                measurements.append(asdict(motion.call("polarize", axis="MA1", orientation="V", timeout=2)))
        with open_device(profile_template("SamsungAt", "simulation")) as phone:
            report["devices"].append(phone.info)
            config = WlanTxConfig(3, 9, 17, 15, 1, 5, 1, "0.0", 1000, 1000)
            with phone.active(config=config):
                if inject_failure:
                    raise RuntimeError("Injected application failure while simulated phone TX is active")
            # No synthetic RF reading is generated: AT ACK is all this fixture supplies.
        report["status"] = "completed"
        report["measurements"] = measurements
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["error_details"] = error_details(exc)
        report["measurements"] = []
        raise
    finally:
        phone_events = phone.phone_log if phone else []
        (target / "phone-traffic.json").write_text(json.dumps(phone_events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "instrument-traffic.jsonl").write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")
        # Fixture observations, deliberately NOT physical measurement claims.
        report["fixture_cleanup"] = {
            "power_output_off": None if power is None else not power._driver.io.output,
            "motion_es_last": None if motion is None else motion._driver.io.events[-1] == "ES",
            "phone_cleanup_acknowledged": len(phone_events) >= 2 and [event["command_id"] for event in phone_events[-2:]] == ["wifitest_0_2_0", "wifitest_0_1_0"] and all(event["status"] == "acknowledged" for event in phone_events[-2:]),
            "connections_closed": all(item.closed for item in (power, motion, phone) if item is not None)}
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        filename = "result.json" if report["status"] == "completed" else "failure.json"
        (target / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
