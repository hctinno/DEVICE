import unittest

from frontend.virtual_fleet.demo_runtime import create_demo


class DemoRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime, self.catalog, self.topology, self.actions = create_demo()

    def run_action(self, device, action, parameters=None):
        return self.runtime.execute(f"step-{self.runtime.sequence}", device, action, parameters or {})

    def ready(self):
        self.run_action("supply", "set_output", {"enabled": True})
        self.run_action("dut", "set_transmit", {"enabled": True})

    def test_pending_measurement_completes_after_explicit_ticks_with_derived_power(self):
        self.ready()
        self.run_action("pad", "set_attenuation", {"loss_db": 7})
        self.assertEqual(self.run_action("meter", "start")["status"], "pending")
        self.assertEqual(self.runtime.observations()["devices"]["meter"]["status"], "pending")
        self.runtime.advance("advance-1", 2)
        meter = self.runtime.observations()["devices"]["meter"]
        self.assertEqual(meter["state"], "completed")
        self.assertEqual(meter["values"]["power_dbm"], 3)
        self.assertTrue(meter["synthetic"])
        self.assertFalse(meter["hardware_verified"])

    def test_configuration_change_invalidates_previous_measurement(self):
        self.ready()
        self.run_action("meter", "start")
        self.runtime.advance("advance-1", 2)
        self.run_action("pad", "set_attenuation", {"loss_db": 3})
        meter = self.runtime.observations()["devices"]["meter"]
        self.assertEqual(meter["status"], "invalid")
        self.assertNotIn("power_dbm", meter["values"])
        self.assertIn("acquired_setup_revision", meter["values"])

    def test_missing_power_is_invalid_and_operator_actions_recover_without_author_control(self):
        self.run_action("dut", "set_transmit", {"enabled": True})
        self.assertEqual(self.run_action("meter", "start")["status"], "invalid")
        self.ready()
        self.run_action("meter", "recover")
        self.run_action("meter", "start")
        self.runtime.advance("advance-1", 2)
        self.assertEqual(self.runtime.observations()["devices"]["meter"]["state"], "completed")


if __name__ == "__main__":
    unittest.main()
