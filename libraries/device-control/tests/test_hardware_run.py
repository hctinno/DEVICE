"""Hardware boundary tests using native drivers and in-process protocol peers only."""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import signal
import tempfile
import threading
import unittest
from unittest.mock import patch

from dgm_control import VirtualLab, WlanScan, Fault, check_hardware, run_hardware, plan_from_dict
from dgm_control.hardware_run import RunEvidence, cancellation_signals
from dgm_control.virtual_lab import WLAN_DEVICES
from dgm_control.virtual_peers import SupplyPeer, PositionerPeer, ScpiPeer, PhonePeer
from dgm_control.__main__ import main
from dgm_rf.core import wlan_tx_plan

QUICK = WlanScan(heights_cm=(100,), angles_deg=(0,), polarizations=("H",))


def profiles_fixture():
    virtual = VirtualLab()
    profiles = {}
    for name in WLAN_DEVICES:
        parameters = virtual.configuration(name)
        if name == "PhoneAt":
            phone = parameters["profile"]
            phone.update(model="TEST-FIXTURE", build="TEST-BUILD", simulation_only=False,
                         evidence_notes="TEST ONLY: never a site profile",
                         allowed_commands=[key for key, _ in sum(wlan_tx_plan(QUICK.tx), [])])
            transport = {"kind": "serial", "port": "TEST-PHONE", "baudrate": 115200}
        else:
            transport = {"kind": "tcp", "host": name + ".invalid", "port": 5025, "timeout": 5}
        profiles[name] = {"schema_version": 1, "device_id": name, "mode": "hardware",
                          "config": {"driver": name, "parameters": parameters, "transport": transport}}
    return profiles


@contextmanager
def peers(fault=None):
    virtual = VirtualLab()
    if fault:
        virtual.inject(fault)
    world = virtual._world
    opened = []
    def connect(config, log=None):
        name = config["host"].split(".")[0]
        opened.append(name)
        if name == "OdaEx":
            return SupplyPeer(world, log)
        if name == "Co3000":
            return PositionerPeer(world, log)
        return ScpiPeer(name, world, log)
    def phone(*args):
        opened.append("PhoneAt")
        peer = PhonePeer(world, None)
        # Exercise the real profile authorization path against a test peer.
        peer.simulated = False
        return peer
    with patch("socket.create_connection", side_effect=AssertionError("physical I/O forbidden")), \
         patch("dgm_lab.registry.open_transport", side_effect=connect), \
         patch("dgm_rf.core.SerialTransport", side_effect=phone):
        yield virtual, opened


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class HardwareRunTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / "run"
        self.profiles = profiles_fixture()

    def test_strict_plan_and_offline_preflight(self):
        with patch("socket.create_connection", side_effect=AssertionError("no I/O")):
            self.assertTrue(check_hardware(self.profiles, plan_from_dict(asdict(QUICK)))["valid"])
        for key in ("voltage", "tx"):
            value = asdict(QUICK)
            value.pop(key)
            with self.assertRaises(ValueError): plan_from_dict(value)
        value = asdict(QUICK)
        value["tx"].pop("tx_mode")
        with self.assertRaises(ValueError): plan_from_dict(value)

    def test_preflight_rejects_wrong_topology_limits_and_simulation(self):
        variations = []
        for name, change in (
            ("Co3000", {"motion_enabled": False}),
            ("OdaEx", {"max_voltage": 1}),
            ("SpectrumAnalyzer", {"max_frequency_hz": 6e9}),
            ("OspSwitch", {"switching_enabled": False}),
        ):
            profile = deepcopy(self.profiles)
            profile[name]["config"]["parameters"].update(change)
            variations.append(profile)
        profile = deepcopy(self.profiles)
        profile["Co3000"]["config"]["parameters"]["axes"]["MA1"]["min"] = 150
        variations.append(profile)
        profile = deepcopy(self.profiles)
        profile["PhoneAt"]["mode"] = "simulation"
        variations.append(profile)
        for profile in variations:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                check_hardware(profile, QUICK)

    def test_success_retains_inputs_identities_all_streams_and_native_phone_log(self):
        with peers() as (lab, opened):
            answer = run_hardware(self.profiles, QUICK, self.output)
            self.assertFalse(lab.state["phone"]["tx"])
            self.assertFalse(lab.state["supply"]["output"])
        self.assertEqual(answer["status"], "completed")
        self.assertEqual(set(opened), set(WLAN_DEVICES))
        result = read(self.output / "result.json")
        self.assertTrue(result["cleanup_scope_succeeded"])
        self.assertFalse(result["physical_shutdown_verified"])
        self.assertFalse(result["physical_verified"])
        self.assertEqual(result["saved_samples"], 1)
        self.assertEqual(read(self.output / "inputs.json")["plan"], asdict(QUICK) | {
            "heights_cm": [100], "angles_deg": [0], "polarizations": ["H"]})
        phone = read(self.output / "phone-log.json")
        self.assertEqual(phone["events"][-1]["command"], "AT+WIFITEST=0,1,0,0")
        self.assertTrue(all(not row["connected"] for row in read(self.output / "identity.json")["devices"].values()))
        for name in ("traffic.jsonl", "phone-traffic.jsonl", "samples.jsonl"):
            rows = [json.loads(line) for line in (self.output / name).read_text(encoding="utf-8").splitlines()]
            self.assertTrue(rows)
            self.assertTrue(all(row["run_id"] == answer["run_id"] for row in rows))
        self.assertFalse((self.output / "failure.json").exists())
        self.assertEqual(read(self.output / "run.json")["status"], "running")  # immutable start marker

    def test_phone_attempt_is_saved_before_wire_send(self):
        exchange = PhonePeer.exchange
        def observed(peer, wire, timeout):
            lines = (self.output / "phone-traffic.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(json.loads(lines[-1])["phase"], "attempted")
            self.assertEqual(json.loads(lines[-1])["command"], wire)
            return exchange(peer, wire, timeout)
        with peers(), patch.object(PhonePeer, "exchange", observed):
            self.assertEqual(run_hardware(self.profiles, QUICK, self.output)["status"], "completed")

    def test_measurement_failure_keeps_phone_cleanup_log(self):
        with peers(Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1")) as (lab, _):
            answer = run_hardware(self.profiles, QUICK, self.output)
            self.assertFalse(lab.state["phone"]["tx"])
        self.assertEqual(answer["status"], "failed")
        self.assertFalse((self.output / "result.json").exists())
        self.assertEqual(read(self.output / "phone-log.json")["events"][-1]["status"], "acknowledged")

    def test_phone_start_and_stop_timeout_keep_emergency_attempts(self):
        for index, command in enumerate(("AT+WIFITEST=0,2,1,1", "AT+WIFITEST=0,2,0,0")):
            output = self.root / str(index)
            with peers(Fault("PhoneAt", command)):
                answer = run_hardware(self.profiles, QUICK, output)
            self.assertEqual(answer["status"], "failed")
            phone = read(output / "phone-log.json")["events"]
            self.assertTrue(any(row["status"] == "failed" for row in phone))
            self.assertTrue(any(row["status"] == "cleanup_sent_unconfirmed" for row in phone))
            raw = (output / "phone-traffic.jsonl").read_text(encoding="utf-8")
            self.assertIn('"operation": "emergency_write"', raw)
            self.assertIn('"phase": "failed"', raw)

    def test_rejected_at_response_is_retained_even_when_transport_received_it(self):
        with peers(Fault("PhoneAt", "AT+WIFITEST=0,0,6,3", "reject")):
            answer = run_hardware(self.profiles, QUICK, self.output)
        self.assertEqual(answer["status"], "failed")
        self.assertIn('"raw_response": "ERROR"', (self.output / "phone-traffic.jsonl").read_text())
        self.assertTrue(any(e["status"] == "failed" for e in read(self.output / "phone-log.json")["events"]))

    def test_cancel_with_cleanup_failure_remains_failed(self):
        event = threading.Event()
        original = RunEvidence.sample
        def cancel(sink, row):
            original(sink, row)
            event.set()
        with peers(Fault("PhoneAt", "AT+WIFITEST=0,2,0,0")), patch.object(RunEvidence, "sample", cancel):
            answer = run_hardware(self.profiles, QUICK, self.output, cancelled=event)
        self.assertEqual(answer["status"], "failed")
        self.assertTrue(read(self.output / "failure.json")["cancellation_requested"])

    def test_partial_samples_survive_next_measurement_failure(self):
        with peers() as (lab, _):
            original = RunEvidence.sample
            def save(sink, row):
                original(sink, row)
                lab.inject(Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1"))
            with patch.object(RunEvidence, "sample", save):
                answer = run_hardware(self.profiles, replace(QUICK, angles_deg=(0, 90)), self.output)
        self.assertEqual(answer["status"], "failed")
        self.assertEqual(answer["samples"], 1)
        self.assertEqual(len((self.output / "samples.jsonl").read_text().splitlines()), 1)

    def test_pre_cancel_and_invalid_profile_never_open(self):
        event = threading.Event(); event.set()
        with peers() as (_, opened):
            answer = run_hardware(self.profiles, QUICK, self.output, cancelled=event)
            self.assertEqual(opened, [])
        self.assertEqual(answer["status"], "cancelled")
        self.assertFalse(read(self.output / "phone-log.json")["session_opened"])
        self.assertFalse(read(self.output / "failure.json")["connection_attempted"])
        self.profiles["PhoneAt"]["config"]["parameters"]["profile"]["allowed_commands"] = []
        with peers() as (_, opened):
            answer = run_hardware(self.profiles, QUICK, self.root / "invalid")
            self.assertEqual(opened, [])
        self.assertEqual(answer["status"], "failed")

    def test_cancel_file_created_after_sample_stops_and_saves(self):
        cancel_file = self.root / "cancel"
        original = RunEvidence.sample
        def save(sink, row):
            original(sink, row)
            cancel_file.touch()
        with peers() as (lab, _), patch.object(RunEvidence, "sample", save):
            answer = run_hardware(self.profiles, QUICK, self.output, cancel_file=cancel_file)
            self.assertFalse(lab.state["phone"]["tx"])
        self.assertEqual(answer["status"], "cancelled")
        self.assertEqual(answer["samples"], 1)
        self.assertGreater(len(read(self.output / "phone-log.json")["events"]), 12)

    def test_keyboard_interrupt_inside_phone_exchange_preserves_cleanup(self):
        exchange = PhonePeer.exchange
        def interrupted(peer, wire, timeout):
            if wire == "AT+WIFITEST=0,0,6,3":
                raise KeyboardInterrupt()
            return exchange(peer, wire, timeout)
        with peers(), patch.object(PhonePeer, "exchange", interrupted):
            answer = run_hardware(self.profiles, QUICK, self.output)
        self.assertEqual(answer["status"], "cancelled")
        self.assertIn("KeyboardInterrupt", (self.output / "phone-traffic.jsonl").read_text())

    def test_signal_handlers_set_event_and_restore(self):
        event = threading.Event()
        previous = signal.getsignal(signal.SIGINT)
        with cancellation_signals(event):
            signal.raise_signal(signal.SIGINT)
            self.assertTrue(event.is_set())
        self.assertEqual(signal.getsignal(signal.SIGINT), previous)

    def test_disk_write_failure_does_not_prevent_phone_cleanup(self):
        original = RunEvidence.sample
        def fail(sink, row):
            sink.handles["samples.jsonl"].close()  # actual write raises ValueError
            original(sink, row)
        with peers() as (lab, _), patch.object(RunEvidence, "sample", fail):
            answer = run_hardware(self.profiles, QUICK, self.output)
            self.assertFalse(lab.state["phone"]["tx"])
            self.assertFalse(lab.state["supply"]["output"])
        self.assertEqual(answer["status"], "failed")
        self.assertTrue(read(self.output / "failure.json")["recording_errors"])
        self.assertFalse(read(self.output / "failure.json")["cancellation_requested"])
        self.assertEqual(read(self.output / "phone-log.json")["events"][-1]["status"], "acknowledged")

    def test_phone_log_sink_failure_still_attempts_cleanup(self):
        original = RunEvidence.sample
        def fail(sink, row):
            original(sink, row)
            sink.handles["phone-traffic.jsonl"].close()
        with peers() as (lab, _), patch.object(RunEvidence, "sample", fail):
            answer = run_hardware(self.profiles, QUICK, self.output)
            self.assertFalse(lab.state["phone"]["tx"])
        self.assertEqual(answer["status"], "failed")
        self.assertIn("AT+WIFITEST=0,1,0,0", (self.output / "traffic.jsonl").read_text())

    def test_existing_folder_never_touched(self):
        self.output.mkdir()
        marker = self.output / "keep"; marker.write_text("original")
        with peers() as (_, opened), self.assertRaises(FileExistsError):
            run_hardware(self.profiles, QUICK, self.output)
        self.assertEqual(marker.read_text(), "original")
        self.assertEqual(opened, [])

    def test_result_commit_failure_never_reports_success(self):
        from dgm_control.hardware_run import atomic_json
        def fail(path, value):
            if path.name == "result.json":
                raise OSError("test result write failure")
            return atomic_json(path, value)
        with peers(), patch("dgm_control.hardware_run.atomic_json", fail):
            answer = run_hardware(self.profiles, QUICK, self.output)
        self.assertEqual(answer["status"], "failed")
        self.assertFalse((self.output / "result.json").exists())
        self.assertIn("test result write failure", read(self.output / "failure.json")["error"]["message"])

    def test_failure_report_storage_error_keeps_original_exception(self):
        from dgm_control.hardware_run import atomic_json
        def fail(path, value):
            if path.name == "failure.json":
                raise OSError("test disk unavailable")
            return atomic_json(path, value)
        with peers(Fault("PhoneAt", "AT+WIFITEST=0,2,0,0")), \
             patch("dgm_control.hardware_run.atomic_json", fail), self.assertRaises(BaseExceptionGroup) as failure:
            run_hardware(self.profiles, QUICK, self.output)
        self.assertEqual(len(failure.exception.exceptions), 2)
        self.assertTrue((self.output / "phone-log.json").exists())
        self.assertFalse((self.output / "result.json").exists())

    def test_cli_offline_and_precancelled_exit_codes(self):
        site = self.root / "site"; site.mkdir()
        for name, profile in self.profiles.items():
            (site / f"{name}.json").write_text(json.dumps(profile), encoding="utf-8")
        plan = self.root / "plan.json"; plan.write_text(json.dumps(asdict(QUICK)), encoding="utf-8")
        cancel_file = self.root / "cancel"; cancel_file.touch()
        common = ["--profiles-dir", str(site), "--plan", str(plan)]
        with peers() as (_, opened), redirect_stdout(io.StringIO()):
            with patch("sys.argv", ["dgm-control", "hardware-check", *common]):
                self.assertEqual(main(), 0)
            with patch("sys.argv", ["dgm-control", "hardware-run", *common, "--output-dir", str(self.output), "--cancel-file", str(cancel_file)]):
                self.assertEqual(main(), 130)
            self.assertEqual(opened, [])

    def test_cli_success_signal_cancel_and_cleanup_failure_exit_codes(self):
        site = self.root / "site"; site.mkdir()
        for name, profile in self.profiles.items():
            (site / f"{name}.json").write_text(json.dumps(profile), encoding="utf-8")
        plan = self.root / "plan.json"; plan.write_text(json.dumps(asdict(QUICK)), encoding="utf-8")
        original = RunEvidence.sample
        def interrupt(sink, row):
            original(sink, row)
            signal.raise_signal(signal.SIGINT)
        for label, expected, fault in (("success", 0, None), ("cancel", 130, None),
                                       ("cleanup-error", 2, Fault("PhoneAt", "AT+WIFITEST=0,2,0,0"))):
            argv = ["dgm-control", "hardware-run", "--profiles-dir", str(site), "--plan", str(plan),
                    "--output-dir", str(self.root / label)]
            with peers(fault), patch("sys.argv", argv), redirect_stdout(io.StringIO()):
                with patch.object(RunEvidence, "sample", interrupt if label == "cancel" else original):
                    self.assertEqual(main(), expected)

    def test_cli_reports_interrupt_plus_persistence_failure_as_exit_two(self):
        argv = ["dgm-control", "hardware-run", "--profiles-dir", "unused", "--plan", "unused",
                "--output-dir", str(self.output)]
        error = BaseExceptionGroup("Cancellation and disk failure", [KeyboardInterrupt(), OSError("disk failed")])
        stderr = io.StringIO()
        with patch("sys.argv", argv), redirect_stderr(stderr), \
             patch("dgm_control.hardware_run.load_hardware_inputs", return_value=(self.profiles, QUICK)), \
             patch("dgm_control.hardware_run.run_hardware", side_effect=error), self.assertRaises(SystemExit) as exited:
            main()
        self.assertEqual(exited.exception.code, 2)
        detail = json.loads(stderr.getvalue())
        self.assertEqual(detail["code"], "MULTIPLE_FAILURES")
        self.assertEqual(len(detail["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
