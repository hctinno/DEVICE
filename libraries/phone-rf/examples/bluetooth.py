"""A fixed BLE preset example. No physical phone is connected."""
from dgm_rf import Controller, ScriptedTransport

phone = Controller(ScriptedTransport())
setup = [("fcbttest_0_0_0", {}), ("fcbttest_3_4_1", {}), ("fcbttest_0_5_0", {})]
cleanup = [("fcbttest_0_6_9", {}), ("fcbttest_0_2_0", {})]
with phone.session(setup, cleanup):
    print("SIMULATION: BLE 2M / Low preset; exact RF parameters require device validation")
phone.save_log("bluetooth-example-log.json")
