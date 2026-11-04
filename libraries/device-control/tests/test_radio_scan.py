"""Facility scan integration, native protocol boundaries only; never physical I/O."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from dgm_control import radio_template, run_radio, check_radio
from dgm_control.radio_contracts import RADIOS
from dgm_control.radio_simulation import RadioWorld
from dgm_control.radio_adapters import RadioLab
from dgm_control.hardware_run import RunEvidence
from dgm_control.virtual_world import Fault
from dgm_control.virtual_peers import ScpiPeer
from test_radios import hardware_fixture, hardware_peers, read
from test_hardware_run import profiles_fixture


def quick(radio):
    plan = radio_template(radio, scan=True)
    plan["scan"].update(heights_cm=[200], angles_deg=[0, 90], polarizations=["H", "V"], motion_timeout=2)
    return plan


def scan_hardware(radio):
    synthetic = quick(radio)
    _, profiles, _ = hardware_fixture(radio)
    plan = deepcopy(synthetic)
    plan.update(simulation_only=False, simulation=None)
    plan["scan"].update(simulation=None, site_verified=True, evidence_notes="TEST FIXTURE ONLY")
    facilities = profiles_fixture()
    for name in ("Co3000", "OspSwitch"): profiles[name] = facilities[name]
    return plan, profiles, synthetic


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def assert_success(self, folder, expected=4):
        result = read(folder / "result.json")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["saved_samples"], expected)
        measurement = result["measurement"]
        peak = measurement["sampled_peak"]
        self.assertEqual((peak["height_cm"], peak["angle_deg"], peak["polarization"]), (200, 90, "V"))
        self.assertTrue(measurement["returned_to_sampled_peak"])
        self.assertTrue(measurement["peak_return_readback"]["route_matches"])
        final = measurement["final_facility_readback"]
        self.assertTrue(final["route_matches"])
        self.assertEqual(final["rf_path"], "isolated")
        self.assertFalse(any(s["busy"] for s in final["positions"]))
        self.assertFalse(result["physical_verified"])
        for line in (folder / "samples.jsonl").read_text().splitlines():
            sample = json.loads(line)
            self.assertTrue(sample["position_before"]["route_matches"])
            self.assertEqual(sample["position_before"]["positions"], sample["position_after"]["positions"])

    def test_all_radios_scan_and_confirm_peak_return_with_real_parsers(self):
        for radio in RADIOS:
            with self.subTest(radio=radio), patch("socket.create_connection", side_effect=AssertionError("no hardware")):
                folder = self.root / radio
                answer = run_radio(quick(radio), "simulation", folder)
                self.assertEqual(answer["status"], "completed", answer)
                self.assert_success(folder)
                state = read(folder / "simulation.json")["final_state"]
                self.assertFalse(state["source"]["tx"])
                self.assertEqual(state["route"], "isolated")
                self.assertEqual(state["motion"]["positions"], [200, 90])

    def test_all_native_hardware_adapters_include_motion_switch_and_source(self):
        for radio in RADIOS:
            plan, profiles, synthetic = scan_hardware(radio)
            with self.subTest(radio=radio), hardware_peers(synthetic) as (world, opened):
                result = run_radio(plan, "hardware", self.root / radio, profiles=profiles)
                self.assertEqual(result["status"], "completed", result)
                self.assertTrue({"Co3000", "OspSwitch", "SpectrumAnalyzer"} <= set(opened))
                self.assert_success(self.root / radio)
                self.assertFalse(world.source["tx"])
                self.assertEqual(world.route, "isolated")

    def test_multiple_paths_rank_globally_and_switch_only_after_source_stop(self):
        plan = quick("bluetooth")
        plan["scan"]["rf_paths"].append("generator")
        plan["scan"]["path_frequency_limits_hz"]["generator"] = [0, 50e9]
        plan["scan"]["simulation"]["route_loss_db"] = {"dut": 10, "generator": 0}
        original = ScpiPeer._switch
        switches = []
        def guard(peer, command):
            if command.startswith("ROUT:CLOS "):
                self.assertFalse(peer.world.source["tx"], command)
                switches.append(command)
            return original(peer, command)
        with patch.object(ScpiPeer, "_switch", guard):
            result = run_radio(plan, "simulation", self.root / "paths")
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["peak"]["rf_path"], "generator")
        self.assertGreaterEqual(len(switches), 5)
        self.assert_success(self.root / "paths", 8)
        events = read(self.root / "paths/phone-log.json")["events"]
        self.assertEqual({e["rf_path"] for e in events}, {"dut", "generator"})
        self.assertEqual({e["source_session"] for e in events}, {0, 1})

    def test_geometry_and_route_causally_change_trace(self):
        world = RadioWorld(quick("uwb")); world.source["tx"] = True
        self.assertEqual(world.signals(), [])  # isolated path
        world.route = "dut"
        world.motion.update(positions=[200, 90], polarization="PV")
        peak = world.power()
        world.motion["polarization"] = "PH"
        self.assertAlmostEqual(peak-world.power(), 6, places=3)
        world.motion.update(positions=[100, 270], polarization="PV")
        self.assertAlmostEqual(peak-world.power(), 14, places=3)

    def test_offline_site_and_plan_rejections_do_not_open_transports(self):
        plan, profiles, _ = scan_hardware("bluetooth")
        cases = []
        for key, value in (("site_verified", False), ("simulation", {}), ("rf_paths", ["isolated"]),
                           ("angles_deg", [360.1]), ("heights_cm", [200.01]), ("polarizations", ["X"]),
                           ("angles_deg", [0, 0]), ("path_frequency_limits_hz", {"dut": [0, 1e9]})):
            p = deepcopy(plan); p["scan"][key] = value; cases.append((p, profiles))
        for device, key, value in (("Co3000", "motion_enabled", False), ("OspSwitch", "switching_enabled", False)):
            s = deepcopy(profiles); s[device]["config"]["parameters"][key] = value; cases.append((plan, s))
        s = deepcopy(profiles); s["Co3000"]["config"]["parameters"]["axes"]["MA1"]["max"] = 150; cases.append((plan, s))
        s = deepcopy(profiles); s.pop("OspSwitch"); cases.append((plan, s))
        p = deepcopy(plan); p["sample_count"] = 500; cases.append((p, profiles))
        with patch("dgm_control.radio_run.RadioLab", side_effect=AssertionError("no I/O")):
            for index, (p, s) in enumerate(cases):
                result = run_radio(p, "hardware", self.root / str(index), profiles=s)
                self.assertEqual(result["status"], "failed", result)
                self.assertFalse(read(self.root / str(index) / "failure.json")["connection_attempted"])
        self.assertTrue(check_radio(plan, "hardware", profiles)["valid"])

    def test_cancellation_after_first_sample_cleans_all_radios(self):
        for radio in RADIOS:
            result = run_radio(quick(radio), "simulation", self.root / radio, fault="cancel-after-sample")
            self.assertEqual(result["status"], "cancelled", result)
            self.assertEqual(result["samples"], 1)
            state = read(self.root / radio / "simulation.json")["final_state"]
            self.assertFalse(state["source"]["tx"])
            self.assertFalse(state["motion"]["moving"])
            self.assertEqual(state["route"], "isolated")

    def test_position_drift_rejects_sample_but_keeps_trace_and_cleanup(self):
        original = RadioLab.acquire
        # Positioner peer holds its own position; alter status readback via driver instead.
        from dgm_lab.motion import Co3000
        original_position = Co3000.position
        shifted = threading.Event()
        def acquire(lab, analyzer, phase):
            result = original(lab, analyzer, phase)
            if phase == "sample": shifted.set()
            return result
        def position(driver, axis):
            from dataclasses import replace
            state = original_position(driver, axis)
            return replace(state, value=state.value+10) if shifted.is_set() and axis == "DT1" else state
        with patch.object(RadioLab, "acquire", acquire), patch.object(Co3000, "position", position):
            result = run_radio(quick("uwb"), "simulation", self.root / "drift")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["samples"], 0)
        self.assertIn('"phase": "sample"', (self.root / "drift/observations.jsonl").read_text())
        self.assertFalse(read(self.root / "drift/simulation.json")["final_state"]["source"]["tx"])

    def test_all_facility_faults_are_failures_and_do_not_publish_peak(self):
        for fault in ("motion-timeout", "motion-stop-timeout", "switch-timeout", "switch-stop-timeout"):
            plan = quick("bluetooth"); plan["scan"]["motion_timeout"] = .6
            result = run_radio(plan, "simulation", self.root / fault, fault=fault)
            self.assertEqual(result["status"], "failed", result)
            self.assertNotIn("peak", result)
            self.assertFalse((self.root / fault / "result.json").exists())
            state = read(self.root / fault / "simulation.json")["final_state"]
            self.assertFalse(state["source"]["tx"])

    def test_partial_samples_and_combined_measurement_cleanup_errors_survive(self):
        plan = quick("cellular"); world = RadioWorld(plan)
        world.faults.extend([Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1", occurrence=3),
                             Fault("OspSwitch", "ROUT:CLOS (@F01A11(0101))")])
        with patch("dgm_control.radio_run.RadioWorld", return_value=world):
            result = run_radio(plan, "simulation", self.root / "combined")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["samples"], 1)
        failure = read(self.root / "combined/failure.json")
        self.assertIn("SpectrumAnalyzer", json.dumps(failure["error"]))
        self.assertIn("OspSwitch", json.dumps(failure["error"]))
        self.assertFalse(world.source["tx"])

    def test_nfc_cancel_away_from_reference_does_not_claim_rf_off(self):
        event = threading.Event()
        original = RunEvidence.sample
        def cancel(sink, row):
            original(sink, row)
            if row["index"] == 1: event.set()
        with patch.object(RunEvidence, "sample", cancel):
            result = run_radio(quick("nfc"), "simulation", self.root / "nfc", cancelled=event)
        self.assertEqual(result["status"], "failed")
        self.assertIn("stop unconfirmed", json.dumps(result["error"]))
        log = read(self.root / "nfc/phone-log.json")
        self.assertEqual(log["events"][-1]["request_id"], 32)

    def test_recorder_failure_still_stops_source_and_facilities(self):
        original = RunEvidence.sample
        def fail(sink, row):
            sink.handles["samples.jsonl"].close()
            original(sink, row)
        with patch.object(RunEvidence, "sample", fail):
            result = run_radio(quick("bluetooth"), "simulation", self.root / "disk")
        self.assertEqual(result["status"], "failed")
        state = read(self.root / "disk/simulation.json")["final_state"]
        self.assertFalse(state["source"]["tx"])
        self.assertEqual(state["route"], "isolated")
        self.assertFalse(state["motion"]["moving"])

    def test_peak_return_failure_is_not_reported_as_success(self):
        plan = quick("bluetooth"); plan["scan"]["angles_deg"] = [90, 180]
        world = RadioWorld(plan)
        original = RunEvidence.sample
        def arm_failure(sink, row):
            original(sink, row)
            if row["index"] == 3: world.faults.append(Fault("Co3000", "GO"))
        with patch("dgm_control.radio_run.RadioWorld", return_value=world), patch.object(RunEvidence, "sample", arm_failure):
            result = run_radio(plan, "simulation", self.root / "return")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["samples"], 4)
        self.assertNotIn("peak", result)
        self.assertFalse(world.source["tx"])
        self.assertEqual(world.route, "isolated")

    def test_rf_route_drift_during_trace_is_rejected(self):
        original = RadioLab.acquire
        def drift(lab, analyzer, phase):
            row = original(lab, analyzer, phase)
            if phase == "sample": lab.world.route = "isolated"
            return row
        with patch.object(RadioLab, "acquire", drift):
            result = run_radio(quick("bluetooth"), "simulation", self.root / "route-drift")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["samples"], 0)
        self.assertIn("readback mismatch", json.dumps(result["error"]))

    def test_precancelled_hardware_scan_never_connects(self):
        event = threading.Event(); event.set()
        for radio in RADIOS:
            plan, profiles, _ = scan_hardware(radio)
            with patch("dgm_control.radio_run.RadioLab", side_effect=AssertionError("no I/O")):
                result = run_radio(plan, "hardware", self.root / radio, profiles=profiles, cancelled=event)
            self.assertEqual(result["status"], "cancelled")
            self.assertFalse(read(self.root / radio / "failure.json")["connection_attempted"])

    def test_nfc_multiple_paths_keep_both_service_sessions(self):
        plan = quick("nfc")
        plan["scan"].update(angles_deg=[90], polarizations=["V"], rf_paths=["dut", "generator"])
        plan["scan"]["path_frequency_limits_hz"]["generator"] = [0, 50e9]
        plan["scan"]["simulation"]["route_loss_db"]["generator"] = 3
        result = run_radio(plan, "simulation", self.root / "nfc-paths")
        self.assertEqual(result["status"], "completed", result)
        events = read(self.root / "nfc-paths/phone-log.json")["events"]
        self.assertEqual([e["request_id"] for e in events], [31, 32, 31, 32])
        self.assertEqual([e["rf_path"] for e in events], ["dut", "dut", "generator", "generator"])


if __name__ == "__main__": unittest.main()
