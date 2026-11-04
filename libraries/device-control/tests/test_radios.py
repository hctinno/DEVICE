"""Radio source + analyzer integration. Hardware boundaries are replaced, never connected."""
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from dgm_control import radio_template, check_radio, run_radio, nfc_profile_template
from dgm_control.radio_contracts import RADIOS, RadioBlocked, at_steps, simulation_phone_profile
from dgm_control.radio_simulation import RadioWorld, RadioAtPeer, RadioLtePeer, RadioNfcPeer
from dgm_control.virtual_peers import ScpiPeer, PositionerPeer
from dgm_control.virtual_world import Fault
from dgm_control.hardware_run import RunEvidence
from dgm_control.__main__ import main
from dgm_rf import nfc_prbs_spec


def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def hardware_fixture(radio):
    synthetic = radio_template(radio)
    plan = deepcopy(synthetic)
    plan.update(simulation_only=False, simulation=None)
    profiles = {"SpectrumAnalyzer": {"schema_version": 1, "device_id": "SpectrumAnalyzer", "mode": "hardware",
        "config": {"driver": "SpectrumAnalyzer", "parameters": {"model": "N9030B", "max_frequency_hz": 50e9},
                   "transport": {"kind": "tcp", "host": "SpectrumAnalyzer.invalid", "port": 5025, "timeout": .1}}}}
    name = RADIOS[radio]["source_device"]
    if name == "PhoneAt":
        fixture = simulation_phone_profile(synthetic)
        model, build = ("SM-S918N", "S918NKSU1AWC8") if radio == "uwb" else ("TEST-FIXTURE", "TEST-BUILD")
        profiles[name] = {"schema_version": 1, "device_id": name, "mode": "hardware", "config": {
            "driver": name, "parameters": {"profile": {"model": model, "build": build, "simulation_only": False,
                "evidence_notes": "TEST ONLY; never site evidence", "allowed_commands": [key for key, _ in sum(at_steps(plan), [])],
                "argument_domains": fixture.argument_domains}}, "transport": {"kind": "serial", "port": "TEST-ONLY", "baudrate": 115200}}}
        # UWB OFF appears twice; profile IDs must be unique.
        p = profiles[name]["config"]["parameters"]["profile"]
        p["allowed_commands"] = list(dict.fromkeys(p["allowed_commands"]))
    elif name == "CmwLte":
        profiles[name] = {"schema_version": 1, "device_id": name, "mode": "hardware", "config": {"driver": name,
            "parameters": {"site_profile_confirmed": True},
            "transport": {"kind": "tcp", "host": "CmwLte.invalid", "port": 5025, "timeout": .1}}}
    else:
        profile = nfc_profile_template()
        profile["config"].update(model="TEST", build="TEST", serial="TEST-ONLY", apk_sha256=nfc_prbs_spec()["apk_sha256"],
            sender_permission_verified=True, transition_bound_verified=True, transition_bound_seconds=.01, evidence_notes="TEST ONLY")
        profiles[name] = profile
    return plan, profiles, synthetic


@contextmanager
def hardware_peers(synthetic, fault=None):
    world = RadioWorld(synthetic)
    world.inject(fault)
    opened = []
    def instrument(config, log=None):
        name = config["host"].split(".")[0]
        opened.append(name)
        if name == "Co3000": return PositionerPeer(world, log)
        return ScpiPeer(name, world, log) if name in {"SpectrumAnalyzer", "OspSwitch"} else RadioLtePeer(world, log)
    def phone(*args):
        opened.append("PhoneAt")
        peer = RadioAtPeer(world); peer.simulated = False
        return peer
    def nfc(*args):
        opened.append("NfcPrbs")
        peer = RadioNfcPeer(world); peer.simulated = False
        return peer
    with patch("socket.create_connection", side_effect=AssertionError("no hardware socket")), \
         patch("subprocess.run", side_effect=AssertionError("no ADB process")), \
         patch("dgm_lab.registry.open_transport", side_effect=instrument), \
         patch("dgm_rf.core.SerialTransport", side_effect=phone), \
         patch("dgm_control.radio_adapters.AdbNfcTransport", side_effect=nfc):
        yield world, opened


class RadioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_all_virtual_radios_couple_tx_to_trace_and_keep_evidence(self):
        for radio in RADIOS:
            with self.subTest(radio=radio), patch("socket.create_connection", side_effect=AssertionError("no network")), \
                 patch("subprocess.run", side_effect=AssertionError("no adb")):
                target = self.root / radio
                result = run_radio(radio_template(radio), "simulation", target)
                self.assertEqual(result["status"], "completed", result)
                report = read(target / "result.json")
                self.assertFalse(report["physical_verified"])
                self.assertTrue(report["simulated"])
                self.assertTrue(report["cleanup_scope_succeeded"])
                self.assertGreater(report["measurement"]["peak_trace_dbm"], report["measurement"]["before"]["peak_dbm"] + 20)
                self.assertAlmostEqual(report["measurement"]["before"]["peak_dbm"], report["measurement"]["after"]["peak_dbm"])
                self.assertFalse(read(target / "simulation.json")["final_state"]["source"]["tx"])
                for name in ("samples.jsonl", "phone-traffic.jsonl", "observations.jsonl"):
                    rows = [json.loads(row) for row in (target / name).read_text().splitlines()]
                    self.assertTrue(rows)
                    self.assertTrue(all(r["simulated"] and r["run_id"] == result["run_id"] for r in rows))
                self.assertTrue(read(target / "phone-log.json")["events"])

    def test_all_hardware_adapters_use_native_protocols_and_explicit_profiles(self):
        for radio in RADIOS:
            with self.subTest(radio=radio):
                plan, profiles, synthetic = hardware_fixture(radio)
                with hardware_peers(synthetic) as (world, opened):
                    self.assertTrue(check_radio(plan, "hardware", profiles)["valid"])
                    self.assertEqual(opened, [])
                    result = run_radio(plan, "hardware", self.root / radio, profiles=profiles)
                    self.assertEqual(result["status"], "completed", result)
                    self.assertFalse(world.source["tx"])
                    self.assertEqual(set(opened), {"SpectrumAnalyzer", RADIOS[radio]["source_device"]})
                self.assertFalse(result["simulated"])
                self.assertFalse((self.root / radio / "simulation.json").exists())

    def test_all_radios_start_measure_stop_failure_and_cancellation(self):
        for radio in RADIOS:
            for fault in ("start-timeout", "measure-timeout", "stop-timeout", "cancel-after-sample"):
                with self.subTest(radio=radio, fault=fault):
                    target = self.root / f"{radio}-{fault}"
                    answer = run_radio(radio_template(radio), "simulation", target, fault=fault)
                    self.assertEqual(answer["status"], "cancelled" if fault == "cancel-after-sample" else "failed", answer)
                    self.assertFalse((target / "result.json").exists())
                    self.assertTrue((target / "phone-log.json").exists())
                    self.assertTrue((target / "phone-traffic.jsonl").stat().st_size)
                    if fault == "cancel-after-sample": self.assertEqual(answer["samples"], 1)

    def test_native_hardware_failures_preserve_phone_and_callbox_logs(self):
        for radio in RADIOS:
            plan, profiles, synthetic = hardware_fixture(radio)
            with self.subTest(radio=radio), hardware_peers(synthetic, "stop-timeout"):
                answer = run_radio(plan, "hardware", self.root / radio, profiles=profiles)
                self.assertEqual(answer["status"], "failed", answer)
                self.assertTrue(read(self.root / radio / "phone-log.json")["events"])

    def test_unsupported_direct_cellular_and_nr_are_blocked_before_io(self):
        for backend in ("direct_tx", "nr_signaling", "guessed_at"):
            plan = radio_template("cellular"); plan["backend"] = backend
            target = self.root / backend
            with patch("dgm_control.radio_run.RadioLab", side_effect=AssertionError("must not open")):
                answer = run_radio(plan, "simulation", target)
            self.assertEqual(answer["status"], "blocked")
            self.assertFalse(read(target / "failure.json")["connection_attempted"])

    def test_simulation_profiles_and_faults_cannot_become_hardware(self):
        plan = radio_template("uwb")
        with self.assertRaises(ValueError): check_radio(plan, "hardware", {})
        real, profiles, synthetic = hardware_fixture("uwb")
        with hardware_peers(synthetic) as (_, opened):
            result = run_radio(real, "hardware", self.root / "fault", profiles=profiles, fault="start-timeout")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(opened, [])
        with self.assertRaises(ValueError): check_radio(plan, "simulation", profiles)

    def test_uwb_model_scope_and_allowlist_are_not_bypassed(self):
        plan, profiles, synthetic = hardware_fixture("uwb")
        phone = profiles["PhoneAt"]["config"]["parameters"]["profile"]
        for field, value in (("build", "NEW-BUILD"), ("allowed_commands", [])):
            changed = deepcopy(profiles)
            changed["PhoneAt"]["config"]["parameters"]["profile"][field] = value
            with self.assertRaises(Exception): check_radio(plan, "hardware", changed)

    def test_nfc_requires_hash_permission_and_transition_evidence(self):
        plan, profiles, _ = hardware_fixture("nfc")
        for field, value in (("apk_sha256", "0" * 64), ("sender_permission_verified", False),
                             ("transition_bound_verified", False), ("evidence_notes", "")):
            changed = deepcopy(profiles); changed["NfcPrbs"]["config"][field] = value
            with self.subTest(field=field), self.assertRaises(Exception): check_radio(plan, "hardware", changed)
        plan["state_timeout"] = .1
        with self.assertRaises(ValueError): check_radio(plan, "hardware", profiles)

    def test_nfc_dispatch_ack_does_not_confirm_rf_start(self):
        from dgm_control.radio_simulation import RadioNfcPeer
        original = RadioNfcPeer.dispatch
        def no_tx(peer, request, timeout):
            if request.request_id == 31: return "Broadcast completed: result=0"
            return original(peer, request, timeout)
        plan = radio_template("nfc"); plan["state_timeout"] = .12
        with patch.object(RadioNfcPeer, "dispatch", no_tx):
            result = run_radio(plan, "simulation", self.root / "nfc")
        self.assertEqual(result["status"], "failed")
        log = read(self.root / "nfc" / "phone-log.json")
        self.assertEqual(log["events"][0]["status"], "dispatched_unconfirmed")
        self.assertEqual(log["events"][-1]["request_id"], 32)

    def test_nfc_stop_ack_without_rf_quiet_is_a_cleanup_failure(self):
        original = RadioNfcPeer.dispatch
        def keep_tx(peer, request, timeout):
            if request.request_id == 32: return "Broadcast completed: result=0"
            return original(peer, request, timeout)
        plan = radio_template("nfc"); plan["state_timeout"] = .12
        with patch.object(RadioNfcPeer, "dispatch", keep_tx):
            result = run_radio(plan, "simulation", self.root / "nfc")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(read(self.root / "nfc" / "simulation.json")["final_state"]["source"]["tx"])

    def test_precancel_records_without_opening_any_source(self):
        event = threading.Event(); event.set()
        for radio in RADIOS:
            with patch("dgm_control.radio_run.RadioLab", side_effect=AssertionError("no I/O")):
                result = run_radio(radio_template(radio), "simulation", self.root / radio, cancelled=event)
            self.assertEqual(result["status"], "cancelled")
            self.assertFalse(read(self.root / radio / "phone-log.json")["session_opened"])

    def test_partial_measurements_survive_later_error(self):
        plan = radio_template("bluetooth")
        world = RadioWorld(plan)
        world.faults.append(Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1", occurrence=3))
        with patch("dgm_control.radio_run.RadioWorld", return_value=world):
            result = run_radio(plan, "simulation", self.root / "partial")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["samples"], 1)
        self.assertFalse(world.source["tx"])

    def test_recorder_failure_still_cleans_up_all_radio_sources(self):
        original = RunEvidence.sample
        def fail(sink, row):
            sink.handles["samples.jsonl"].close()
            original(sink, row)
        for radio in RADIOS:
            with patch.object(RunEvidence, "sample", fail):
                result = run_radio(radio_template(radio), "simulation", self.root / radio)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(read(self.root / radio / "simulation.json")["final_state"]["source"]["tx"])
            self.assertTrue(read(self.root / radio / "phone-log.json")["events"])

    def test_source_loss_changes_trace_without_changing_wire_plan(self):
        values = []
        for index, loss in enumerate((20, 30)):
            plan = radio_template("uwb"); plan["simulation"]["path_loss_db"] = loss
            run_radio(plan, "simulation", self.root / str(index))
            values.append(read(self.root / str(index) / "result.json")["measurement"]["peak_trace_dbm"])
        self.assertAlmostEqual(values[0] - values[1], 10, places=3)

    def test_strict_plans_reject_bad_enums_unknown_fields_and_nan(self):
        variants = []
        plan = radio_template("bluetooth"); plan["tx"]["phy"] = "coded"; variants.append(plan)
        plan = radio_template("nfc"); plan["tx"]["rate_index"] = 3; variants.append(plan)
        plan = radio_template("uwb"); plan["tx"]["power_code"] = 128; variants.append(plan)
        plan = radio_template("cellular"); plan["tx"]["band"] = 999; variants.append(plan)
        plan = radio_template("bluetooth"); plan["sample_count"] = True; variants.append(plan)
        plan = radio_template("bluetooth"); plan["sweep"]["rbw_hz"] = float("nan"); variants.append(plan)
        plan = radio_template("bluetooth"); plan["typo"] = 1; variants.append(plan)
        for plan in variants:
            with self.assertRaises(Exception): check_radio(plan, "simulation")

    def test_existing_output_is_untouched(self):
        target = self.root / "exists"; target.mkdir()
        keep = target / "keep"; keep.write_text("original")
        with self.assertRaises(FileExistsError): run_radio(radio_template("bluetooth"), "simulation", target)
        self.assertEqual(keep.read_text(), "original")

    def test_cli_blocked_hardware_attempt_is_recorded_without_profiles(self):
        plan = radio_template("cellular"); plan.update(backend="direct_tx", simulation_only=False, simulation=None)
        path = self.root / "plan.json"; path.write_text(json.dumps(plan))
        argv = ["dgm-control", "radio-run", "--mode", "hardware", "--plan", str(path), "--output-dir", str(self.root / "run")]
        with patch("sys.argv", argv), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 2)
        self.assertEqual(read(self.root / "run" / "failure.json")["status"], "blocked")


if __name__ == "__main__": unittest.main()
