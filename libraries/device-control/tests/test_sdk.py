from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dgm_control import (devices, describe, profile_template, check_profile, doctor, open_device, error_details,
                         UnsupportedDevice, SessionError)
from dgm_control.demo import run_demo
from dgm_lab import InstrumentError
from dgm_rf import WlanTxConfig


class CatalogTests(unittest.TestCase):
    def test_all_descriptors_have_honest_status(self):
        rows = devices()
        self.assertEqual(len(rows), 21)
        self.assertEqual(len({row["id"] for row in rows}), 21)
        self.assertTrue(all(row["physical_verified"] is False and row["sdk_is_manufacturer_endorsed"] is False for row in rows))
        self.assertEqual(sum(row["simulation_available"] for row in rows), 3)

    def test_instrument_contracts_match_actual_drivers(self):
        from dgm_lab.registry import DRIVERS
        from dgm_control.session import LIFECYCLES
        for name, cls in DRIVERS.items():
            item = describe(name)
            self.assertTrue(item["sources"])
            for method in item["operations"]:
                self.assertTrue(callable(getattr(cls, method)))
            if name in LIFECYCLES:
                self.assertTrue(callable(getattr(cls, LIFECYCLES[name])))

    def test_catalog_returns_independent_data(self):
        row = describe("OdaEx")
        row["operations"].clear()
        self.assertIn("configure", describe("OdaEx")["operations"])

    def test_filter_and_unknown_device(self):
        self.assertTrue(all(row["kind"] == "facility" for row in devices("facility")))
        with self.assertRaises(ValueError): devices("other")
        with self.assertRaises(UnsupportedDevice): describe("Unknown")

    def test_reference_backends_cannot_be_opened_or_templated(self):
        for name in ("QualcommMyftm", "BroadcomWl", "AppleRF", "NfcProtectedService"):
            with self.assertRaises(UnsupportedDevice): profile_template(name)
            profile = {"schema_version": 1, "device_id": name, "mode": "hardware", "config": {}}
            self.assertFalse(check_profile(profile)["valid"])
            with self.assertRaises(UnsupportedDevice):
                with open_device(profile): pass

    def test_doctor_is_offline(self):
        with patch("socket.create_connection", side_effect=AssertionError("no network")):
            self.assertFalse(doctor()["connection_attempted"])


class ProfileTests(unittest.TestCase):
    def test_all_three_simulation_profiles_validate(self):
        for name in ("OdaEx", "Co3000", "PhoneAt"):
            report = check_profile(profile_template(name, "simulation"))
            self.assertTrue(report["valid"], report)
            self.assertFalse(report["connection_attempted"])

    def test_hardware_templates_require_real_site_values(self):
        for row in devices():
            if row["backend"]:
                self.assertFalse(check_profile(profile_template(row["id"]))["valid"], row["id"])

    def test_typo_schema_and_driver_mismatch_rejected(self):
        for key, value in [("schema_version", True), ("schema_version", 2), ("mode", "auto"), ("device_id", "Co3000")]:
            profile = profile_template("OdaEx", "simulation")
            profile[key] = value
            self.assertFalse(check_profile(profile)["valid"])
        profile = profile_template("OdaEx", "simulation")
        profile["mod"] = "hardware"
        self.assertFalse(check_profile(profile)["valid"])

    def test_simulation_cannot_hide_real_transport(self):
        profile = profile_template("OdaEx", "simulation")
        profile["config"]["transport"] = {"kind": "tcp", "host": "127.0.0.1", "port": 1}
        with patch("socket.create_connection", side_effect=AssertionError("must not connect")):
            self.assertFalse(check_profile(profile)["valid"])
            with self.assertRaises(ValueError):
                with open_device(profile): pass

    def test_profile_notes_agree_with_json_schema(self):
        profile = profile_template("OdaEx", "simulation")
        profile["config"]["notes"] = ["not a string"]
        self.assertFalse(check_profile(profile)["valid"])

    def test_unsupported_simulator_does_not_fake_success(self):
        with self.assertRaises(UnsupportedDevice): profile_template("SpectrumAnalyzer", "simulation")

    def test_phone_modes_and_allowlist_are_checked(self):
        profile = profile_template("PhoneAt", "simulation")
        profile["config"]["parameters"]["profile"]["simulation_only"] = "true"
        self.assertFalse(check_profile(profile)["valid"])
        profile = profile_template("PhoneAt", "simulation")
        profile["config"]["parameters"]["profile"]["allowed_commands"] = ["invented_tx"]
        self.assertFalse(check_profile(profile)["valid"])

    def test_invalid_hardware_never_opens_transport(self):
        from dgm_lab import registry
        with patch.object(registry, "open_transport", side_effect=AssertionError("must not open")):
            with self.assertRaises((ValueError, RuntimeError)):
                with open_device(profile_template("OdaEx")): pass

    def test_phone_argument_domains_reject_nonfinite_and_delimiters(self):
        for value in [float("nan"), "1,2", "1\rAT", True]:
            profile = profile_template("PhoneAt", "simulation")
            profile["config"]["parameters"]["profile"]["argument_domains"]["wifitest_0_0_3"] = {"value": [value]}
            self.assertFalse(check_profile(profile)["valid"])


class LifecycleTests(unittest.TestCase):
    def test_power_config_measure_and_cleanup(self):
        with open_device(profile_template("OdaEx", "simulation")) as session:
            self.assertFalse(session._driver.io.output)
            session.call("configure", voltage=5, current=1)
            with session.active():
                self.assertEqual(session.call("read_voltage").value, 4.99)
                self.assertTrue(session.info["active"])
            self.assertFalse(session._driver.io.output)
        self.assertTrue(session.closed)

    def test_body_failure_preserved_and_output_stopped(self):
        with open_device(profile_template("OdaEx", "simulation")) as session:
            session.call("configure", voltage=5, current=1)
            with self.assertRaisesRegex(RuntimeError, "body failed"):
                with session.active(): raise RuntimeError("body failed")
            self.assertFalse(session._driver.io.output)

    def test_keyboard_cancel_stops(self):
        with open_device(profile_template("OdaEx", "simulation")) as session:
            session.call("configure", voltage=5, current=1)
            with self.assertRaises(KeyboardInterrupt):
                with session.active(): raise KeyboardInterrupt()
            self.assertFalse(session._driver.io.output)

    def test_start_without_configuration_still_attempts_stop(self):
        events = []
        with open_device(profile_template("OdaEx", "simulation"), log=events.append) as session:
            with self.assertRaises(InstrumentError):
                with session.active(): pass
            self.assertTrue(any(event["payload"] == "OUTP OFF" for event in events))

    def test_cleanup_failure_and_original_are_both_preserved(self):
        with open_device(profile_template("OdaEx", "simulation")) as session:
            session.call("configure", voltage=5, current=1)
            with patch.object(session._driver, "stop", side_effect=RuntimeError("stop failed")):
                with self.assertRaises(BaseExceptionGroup) as caught:
                    with session.active(): raise RuntimeError("body failed")
            self.assertEqual(len(caught.exception.exceptions), 2)
            session.call("stop")  # restore fixture after intentional failure

    def test_raw_private_unknown_and_direct_start_are_rejected(self):
        with open_device(profile_template("OdaEx", "simulation")) as session:
            for name in ("_write", "apply", "execute", "invented"):
                with self.assertRaises(UnsupportedDevice): session.call(name)
            with self.assertRaises(SessionError): session.call("start")

    def test_nested_active_rejected_without_losing_outer_cleanup(self):
        with open_device(profile_template("OdaEx", "simulation")) as session:
            session.call("configure", voltage=5, current=1)
            with session.active():
                with self.assertRaises(SessionError):
                    with session.active(): pass
                self.assertTrue(session._driver.io.output)
            self.assertFalse(session._driver.io.output)

    def test_closed_session_rejected(self):
        with open_device(profile_template("OdaEx", "simulation")) as session: pass
        with self.assertRaises(SessionError): session.call("read_voltage")
        with self.assertRaises(SessionError):
            with session.active(): pass

    def test_bad_method_arguments_do_not_write(self):
        events = []
        with open_device(profile_template("OdaEx", "simulation"), log=events.append) as session:
            before = len(events)
            with self.assertRaises(TypeError): session.call("configure", voltages=5, current=1)
            self.assertEqual(before, len(events))

    def test_motion_move_readback_stop(self):
        with open_device(profile_template("Co3000", "simulation")) as session:
            with session.active():
                state = session.call("move", axis="DT1", value=90, timeout=2)
                self.assertEqual(state.value, 90)
                self.assertEqual(state.unit, "DG")
            self.assertEqual(session._driver.io.events[-1], "ES")

    def test_motion_target_error_and_cleanup(self):
        with open_device(profile_template("Co3000", "simulation")) as session:
            with self.assertRaises(ValueError):
                with session.active(): session.call("move", axis="DT1", value=361)
            self.assertEqual(session._driver.io.events[-1], "ES")

    def test_phone_cleanup_on_failure(self):
        with open_device(profile_template("PhoneAt", "simulation")) as session:
            self.assertEqual(session.info["identity_source"], "profile_declared_not_readback")
            with self.assertRaisesRegex(RuntimeError, "body failed"):
                with session.active(config=WlanTxConfig(3, 9, 17, 15, 1, 5, 1, "0.0", 1000, 1000)):
                    raise RuntimeError("body failed")
            self.assertEqual([row["command_id"] for row in session.phone_log[-2:]], ["wifitest_0_2_0", "wifitest_0_1_0"])
            self.assertTrue(all(row["status"] == "acknowledged" for row in session.phone_log[-2:]))

    def test_phone_requires_explicit_cleanup_before_commands(self):
        with open_device(profile_template("PhoneAt", "simulation")) as session:
            with self.assertRaises(Exception):
                with session.active(setup=[], cleanup=[]): pass
            self.assertEqual(session.phone_log, [])


class DemoTests(unittest.TestCase):
    def test_success_has_three_devices_and_no_rf_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run"
            result = run_demo(path)
            self.assertTrue(result["simulated"])
            self.assertFalse(result["physical_verified"])
            self.assertEqual(len(result["devices"]), 3)
            self.assertTrue(all(result["fixture_cleanup"].values()))
            self.assertEqual(len(result["measurements"]), 4)
            self.assertFalse((path / "failure.json").exists())

    def test_failure_does_not_publish_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run"
            with self.assertRaisesRegex(RuntimeError, "Injected"):
                run_demo(path, inject_failure=True)
            result = json.loads((path / "failure.json").read_text(encoding="utf-8"))
            self.assertFalse((path / "result.json").exists())
            self.assertEqual(result["measurements"], [])
            self.assertTrue(all(result["fixture_cleanup"].values()))

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run"
            path.mkdir()
            sentinel = path / "result.json"
            sentinel.write_text("previous", encoding="utf-8")
            with self.assertRaises(FileExistsError): run_demo(path)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "previous")


class ErrorTests(unittest.TestCase):
    def test_multiple_errors_retained(self):
        result = error_details(ExceptionGroup("both", [ValueError("argument"), TimeoutError("link")]))
        self.assertEqual(result["code"], "MULTIPLE_FAILURES")
        self.assertEqual([item["code"] for item in result["errors"]], ["ARGUMENT", "COMMUNICATION"])
        self.assertFalse(result["automatic_retry"])

    def test_cleanup_and_cancellation_are_distinct(self):
        from dgm_rf.core import CleanupError
        self.assertEqual(error_details(CleanupError(["OFF uncertain"]))["code"], "CLEANUP_UNCONFIRMED")
        self.assertEqual(error_details(KeyboardInterrupt())["code"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
