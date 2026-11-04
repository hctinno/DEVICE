"""Run from the project root: python -m examples.wlan_tx"""
from dgm_rf import Controller, Profile, ScriptedTransport, WlanTxConfig

profile = Profile.load("profiles/simulation.json")
phone = Controller(ScriptedTransport(), profile)
config = WlanTxConfig(
    band=3, bandwidth=9, channel_argument=17, rate=15,
    antenna=1, gi=5, encoding=1, power="0.0", burst=1000, payload=1000)
# Fixture values above are NOT validated settings for an actual phone.
try:
    with phone.wlan_tx(config):
        print("SIMULATION: instrument measurement callback belongs here")
finally:
    phone.save_log("wlan-example-log.json")
