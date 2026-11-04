from contextlib import ExitStack, contextmanager
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from dgm_control import VirtualLab, HardwareLab, Scenario, Fault, WlanScan, measure_wlan, SessionError, profile_template
from dgm_control.virtual_recipe import run_virtual
from dgm_control.virtual_lab import VIRTUAL_MODELS
from dgm_lab.analyzers import Sweep


QUICK = WlanScan(heights_cm=(100,), angles_deg=(0,), polarizations=("H",))
SWEEP = Sweep(5.9e9, 6.3e9, 1e6, 1e6, 10, 10, points=101, sweep_seconds=.01)


@contextmanager
def connected(lab, *, tx=True, config=None):
    with ExitStack() as stack:
        devices = {name: stack.enter_context(lab.open(name)) for name in
                   ("OdaEx", "PhoneAt", "OspSwitch", "UsbPowerSensor", "SpectrumAnalyzer")}
        devices["OdaEx"].call("configure", voltage=5, current=1)
        stack.enter_context(devices["OdaEx"].active())
        stack.enter_context(devices["OspSwitch"].active(name="dut"))
        devices["UsbPowerSensor"].call("configure_average", frequency_hz=6.035e9)
        if tx:
            stack.enter_context(devices["PhoneAt"].active(config=config or QUICK.tx))
        yield devices


def watts_dbm(device):
    reading = device.call("read_power")
    return 10 * math.log10(reading.value) + 30


class VirtualLabTests(unittest.TestCase):
    def assert_stopped(self, lab):
        state = lab.state
        self.assertFalse(state["phone"]["tx"])
        self.assertFalse(state["supply"]["output"])
        self.assertFalse(state["generator"]["output"])
        self.assertFalse(state["motion"]["moving"])
        self.assertEqual(state["route"], "isolated")
        self.assertEqual(lab.connections, [])

    def test_all_seven_peers_identify_without_network(self):
        lab = VirtualLab()
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            for name in VIRTUAL_MODELS:
                with lab.open(name) as device:
                    self.assertTrue(device.info["simulated"])
                    self.assertFalse(device.info["physical_verified"])
                    if name != "PhoneAt":
                        self.assertIsNotNone(device.info["identity"])
                self.assertTrue(device.closed)
        self.assert_stopped(lab)

    def test_tx_off_on_route_loss_and_total_power(self):
        lab = VirtualLab()
        with connected(lab, tx=False) as devices:
            sensor = devices["UsbPowerSensor"]
            self.assertAlmostEqual(watts_dbm(sensor), -100)
            with devices["PhoneAt"].active(config=QUICK.tx):
                # Fixture at 0deg/100cm/H: 20 cable + 6 azimuth + 2 height + 6 polarization.
                self.assertAlmostEqual(watts_dbm(sensor), -34, places=4)
                devices["OspSwitch"].call("select", name="isolated")
                self.assertAlmostEqual(watts_dbm(sensor), -100)
                devices["OspSwitch"].call("select", name="dut")
                self.assertGreater(watts_dbm(sensor), -35)
            self.assertAlmostEqual(watts_dbm(sensor), -100)
        self.assert_stopped(lab)

    def test_tx_power_and_path_loss_are_independent_controls(self):
        values = []
        for loss, power in [(20, "0.0"), (30, "0.0"), (20, "10.0")]:
            lab = VirtualLab(Scenario(path_loss_db=loss))
            with connected(lab, config=replace(QUICK.tx, power=power)) as devices:
                values.append(watts_dbm(devices["UsbPowerSensor"]))
        self.assertAlmostEqual(values[1] - values[0], -10, places=3)
        self.assertAlmostEqual(values[2] - values[0], 10, places=3)

    def test_frequency_change_moves_spectrum_not_sensor_tuning(self):
        lab = VirtualLab()
        spectra = []
        with connected(lab, tx=False) as devices:
            for channel in (17, 49):
                with devices["PhoneAt"].active(config=replace(QUICK.tx, channel_argument=channel)):
                    trace = devices["SpectrumAnalyzer"].call("acquire", config=SWEEP)
                    occupied = [hz for hz, dbm in zip(trace.frequencies_hz, trace.values_dbm) if dbm > -90]
                    spectra.append(sum(occupied) / len(occupied))
                    original = watts_dbm(devices["UsbPowerSensor"])
                    devices["UsbPowerSensor"].call("configure_average", frequency_hz=1e9)
                    self.assertAlmostEqual(watts_dbm(devices["UsbPowerSensor"]), original)
            self.assertGreater(spectra[1] - spectra[0], 150e6)

    def test_he_width_controls_spectrum_density_not_total_power(self):
        results = []
        for bandwidth in (6, 9):
            with connected(VirtualLab(), config=replace(QUICK.tx, bandwidth=bandwidth)) as devices:
                trace = devices["SpectrumAnalyzer"].call("acquire", config=SWEEP)
                results.append((max(trace.values_dbm), watts_dbm(devices["UsbPowerSensor"])))
        self.assertAlmostEqual(results[0][0] - results[1][0], 10 * math.log10(8), places=3)
        self.assertAlmostEqual(results[0][1], results[1][1])

    def test_motion_polarization_height_affect_measurement(self):
        lab = VirtualLab()
        with connected(lab) as devices, lab.open("Co3000") as motion, motion.active():
            sensor = devices["UsbPowerSensor"]
            before = watts_dbm(sensor)
            motion.call("move", axis="DT1", value=90, timeout=2)
            angle = watts_dbm(sensor)
            motion.call("move", axis="MA1", value=200, timeout=2)
            height = watts_dbm(sensor)
            motion.call("polarize", axis="MA1", orientation="V", timeout=2)
            self.assertAlmostEqual(angle - before, 6, places=3)
            self.assertAlmostEqual(height - angle, 2, places=3)
            self.assertAlmostEqual(watts_dbm(sensor) - height, 6, places=3)
        self.assert_stopped(lab)

    def test_generator_route_and_cleanup(self):
        lab = VirtualLab()
        with lab.open("SignalGenerator") as generator, lab.open("OspSwitch") as route, lab.open("UsbPowerSensor") as sensor:
            generator.call("configure_cw", frequency_hz=6.035e9, power_dbm=-10)
            sensor.call("configure_average", frequency_hz=6.035e9)
            with route.active(name="generator"), generator.active():
                self.assertAlmostEqual(watts_dbm(sensor), -30, places=4)
            self.assertAlmostEqual(watts_dbm(sensor), -100)
        self.assert_stopped(lab)

    def test_power_loss_suppresses_rf(self):
        lab = VirtualLab()
        with connected(lab) as devices:
            devices["OdaEx"].call("stop")
            self.assertAlmostEqual(watts_dbm(devices["UsbPowerSensor"]), -100)
        self.assert_stopped(lab)

    def test_model_is_deterministic_and_labs_are_isolated(self):
        first, second = VirtualLab(), VirtualLab()
        with connected(first) as devices:
            a = devices["SpectrumAnalyzer"].call("acquire", config=SWEEP)
            b = devices["SpectrumAnalyzer"].call("acquire", config=SWEEP)
            self.assertEqual(a.values_dbm, b.values_dbm)
            self.assertFalse(second.state["phone"]["tx"])
            self.assertGreater(first.observations[-1]["state"]["revision"], 0)
        snapshot = first.state
        snapshot["phone"]["tx"] = True
        self.assertFalse(first.state["phone"]["tx"])

    def test_resource_lease_released_after_identification_failure(self):
        lab = VirtualLab()
        lab.inject(Fault("SpectrumAnalyzer", "*IDN?", "malformed"))
        with self.assertRaises(Exception):
            with lab.open("SpectrumAnalyzer"): pass
        self.assertEqual(lab.connections, [])
        with lab.open("SpectrumAnalyzer"):
            with self.assertRaises(SessionError):
                with lab.open("SpectrumAnalyzer"): pass
        self.assertEqual(lab.connections, [])

    def test_close_does_not_fake_generator_off(self):
        # Deliberately exercise low-level lost ownership, not the normal public lifecycle.
        lab = VirtualLab()
        with lab.open("SignalGenerator") as generator:
            generator.call("configure_cw", frequency_hz=6e9, power_dbm=-20)
            with self.assertRaises(Exception):
                with generator.active():
                    lab.inject(Fault("SignalGenerator", "OUTP OFF"))
        self.assertTrue(lab.state["generator"]["output"])
        self.assertEqual(lab.connections, [])
        with lab.open("SignalGenerator") as recovery:
            recovery.call("stop")
        self.assertFalse(lab.state["generator"]["output"])

    def test_unknown_model_and_invalid_fault_rejected(self):
        lab = VirtualLab()
        with self.assertRaises(ValueError):
            with lab.open("CmwLte"): pass
        with self.assertRaises(ValueError): lab.inject(Fault("OdaEx", "GO", "stuck"))
        with self.assertRaises(ValueError): Scenario(path_loss_db=float("nan"))
        with self.assertRaises(ValueError): Scenario(channels_hz={17: 6e9})

    def test_hardware_provider_never_accepts_simulation_or_incomplete_templates(self):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            for mode in ("simulation", "hardware"):
                with self.assertRaises(ValueError): HardwareLab({"Co3000": profile_template("Co3000", mode)})

    def test_native_faults_preserve_cleanup_of_other_devices(self):
        for fault in (Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1"),
                      Fault("UsbPowerSensor", "FETC?", "malformed"),
                      Fault("UsbPowerSensor", "FETC?", "disconnect")):
            with self.subTest(fault=fault):
                lab = VirtualLab()
                with self.assertRaises(BaseException):
                    with connected(lab) as devices:
                        lab.inject(fault)
                        devices["SpectrumAnalyzer"].call("acquire", config=SWEEP)
                        devices["UsbPowerSensor"].call("read_power")
                self.assert_stopped(lab)

    def test_stuck_motion_times_out_and_stops(self):
        lab = VirtualLab()
        lab.inject(Fault("Co3000", "GO", "stuck"))
        with lab.open("Co3000") as motion:
            with self.assertRaises(TimeoutError):
                motion.call("move", axis="DT1", value=90, timeout=.02)
        self.assertFalse(lab.state["motion"]["moving"])
        self.assertEqual(lab.state["motion"]["positions"][1], 0)

    def test_phone_cleanup_timeout_keeps_unknown_state_honest(self):
        lab = VirtualLab()
        with self.assertRaises(Exception):
            with connected(lab):
                lab.inject(Fault("PhoneAt", "AT+WIFITEST=0,2,0,0"))
        self.assertTrue(lab.state["phone"]["tx"])  # model's retained command state; delivery unconfirmed
        self.assertFalse(lab.state["supply"]["output"])
        self.assertEqual(lab.state["route"], "isolated")

    def test_already_cancelled_and_bad_grid_do_not_connect(self):
        lab = VirtualLab()
        event = threading.Event(); event.set()
        with patch.object(lab, "open", side_effect=AssertionError("must not open")):
            with self.assertRaises(InterruptedError): measure_wlan(lab, QUICK, cancelled=event)
            with self.assertRaises(ValueError): measure_wlan(lab, replace(QUICK, angles_deg=(361,)))

    def test_cancellation_after_sample_cleans_up(self):
        lab, event = VirtualLab(), threading.Event()
        with self.assertRaises(InterruptedError):
            measure_wlan(lab, QUICK, cancelled=event, on_sample=lambda row: event.set())
        self.assert_stopped(lab)

    def test_mismatched_channel_and_unsupported_tx_rejected_before_io(self):
        lab = VirtualLab()
        with patch.object(lab, "open", side_effect=AssertionError("must not open")):
            with self.assertRaises(ValueError):
                measure_wlan(lab, replace(QUICK, center_hz=6.195e9))
            with self.assertRaises(Exception):
                measure_wlan(lab, replace(QUICK, tx=replace(QUICK.tx, power="12.0")))
            with self.assertRaises(ValueError):
                measure_wlan(lab, replace(QUICK, tx=replace(QUICK.tx, bandwidth=11)))

    def test_motion_stop_failure_is_not_hidden_by_close(self):
        lab = VirtualLab()
        lab.inject(Fault("Co3000", "GO", "stuck"))
        lab.inject(Fault("Co3000", "ES"))
        with self.assertRaises(ExceptionGroup) as raised:
            with lab.open("Co3000") as motion:
                motion.call("move", axis="DT1", value=90, timeout=.02)
        self.assertEqual(len(raised.exception.exceptions), 2)
        self.assertTrue(lab.state["motion"]["moving"])
        with lab.open("Co3000") as recovery:
            recovery.call("stop_all")
        self.assertFalse(lab.state["motion"]["moving"])

    def test_unmodeled_wire_commands_fail_closed(self):
        from dgm_control.virtual_peers import ScpiPeer, PhonePeer
        from dgm_control.virtual_world import World
        world = World()
        with ScpiPeer("SpectrumAnalyzer", world, None) as peer:
            with self.assertRaises(Exception): peer.query("MAGIC?")
            self.assertTrue(peer.poisoned)
        self.assertEqual(PhonePeer(world, None).exchange("AT+UNKNOWN=0", 1), "ERROR")

    def test_keyboard_interrupt_preserves_stopping(self):
        lab = VirtualLab()
        with self.assertRaises(KeyboardInterrupt):
            with connected(lab):
                raise KeyboardInterrupt()
        self.assert_stopped(lab)

    def test_manifest_virtual_models_match_factory(self):
        from dgm_control import describe
        for name, model in VIRTUAL_MODELS.items():
            self.assertEqual(describe(name)["integrated_virtual_model"], model)

    def test_end_to_end_evidence_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run"
            answer = run_virtual(path, plan=QUICK)
            result = json.loads((path / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(answer["samples"], 1)
            self.assertEqual(result["status"], "completed")
            self.assertIsNone(result["fcc_verdict"])
            self.assertTrue(result["cleanup_scope_succeeded"])
            self.assertFalse(result["final_simulated_state"]["phone"]["tx"])
            self.assertEqual(result["remaining_connections"], [])
            self.assertTrue((path / "traffic.jsonl").stat().st_size > 0)
            self.assertTrue((path / "observations.json").stat().st_size > 0)
            before = (path / "result.json").read_bytes()
            with self.assertRaises(FileExistsError): run_virtual(path, plan=QUICK)
            self.assertEqual((path / "result.json").read_bytes(), before)

    def test_failed_run_has_no_success_result_and_keeps_raw_observations(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run"
            with self.assertRaises(BaseException):
                run_virtual(path, plan=QUICK, fault=Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1"))
            self.assertFalse((path / "result.json").exists())
            result = json.loads((path / "failure.json").read_text(encoding="utf-8"))
            self.assertFalse(result["cleanup_scope_succeeded"])
            self.assertFalse(result["final_simulated_state"]["phone"]["tx"])
            raw = json.loads((path / "observations.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(raw["observations"]), 2)


if __name__ == "__main__":
    unittest.main()
