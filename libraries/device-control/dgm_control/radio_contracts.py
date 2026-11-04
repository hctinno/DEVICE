"""Source-scoped multi-radio plans. No guessed vendor commands or hardware defaults."""
from copy import deepcopy
from dataclasses import asdict, fields

from dgm_lab.analyzers import Sweep
from dgm_lab.core import number, integer
from dgm_rf import Catalog, Profile, UwbTxConfig, uwb_tx_plan, NfcRequest, NfcProfile, AdbNfcTransport
from dgm_rf.cmw_lte import LteRmcConfig, lte_rmc_plan
from .catalog import ProfileError
from .profiles import require_profile, _phone_profile


class RadioBlocked(ProfileError):
    pass


RADIOS = {
    "bluetooth": {"backend": "ble_preset", "source_device": "PhoneAt",
        "scope": "BLE 1M/2M Low/Mid/High preset AT; exact RF settings need site evidence",
        "unconfirmed": ["BR/EDR recipe", "coded PHY", "preset channel/power/packet mapping", "latest model compatibility"],
        "sources": ["dgm_rf/data/catalog.json: fcbttest_0_0_0,3_4_0/1,0_5_0/1/2,0_6_9,0_2_0"]},
    "cellular": {"backend": "lte_rmc", "source_device": "CmwLte",
        "scope": "CMW500 LTE FDD PCC RMC signaling; callbox-mediated DUT control",
        "unconfirmed": ["direct modem TX arguments and stop pair", "NR", "CA/ENDC", "DUT modem diagnostic log capture"],
        "sources": ["dgm_lab/callbox.py", "dgm_rf/cmw_lte.py:SOURCES"]},
    "nfc": {"backend": "nfc_prbs", "source_device": "NfcPrbs",
        "scope": "Protected service PRBS 31/32; commissioned permission and transition bound plus RF-envelope checks",
        "unconfirmed": ["generic NFC AT", "TECH/RATE physical mapping", "CW output", "unprovisioned shell permission"],
        "sources": ["dgm_rf/data/nfc-prbs.json", "dgm_rf/nfc.py"]},
    "uwb": {"backend": "uwb_periodic", "source_device": "PhoneAt",
        "scope": "SM-S918N / S918NKSU1AWC8 source-limited periodic TX AT",
        "unconfirmed": ["other build compatibility", "power code to dBm", "timing physical units", "ranging measurements"],
        "sources": ["dgm_rf/data/uwb-rf-arguments.json", "dgm_rf/uwb.py"]},
}


def radio_catalog():
    return [{"radio": key, **deepcopy(value), "simulation_available": True,
             "hardware_status": "conditional_uncommissioned", "physical_verified": False,
             "measurement": "fixed-route or schema-2 motion/path scan with sampled-peak return; no FCC verdict"} for key, value in RADIOS.items()]


def exact(value, names, label):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError(f"{label} requires exactly {sorted(names)}")


def at_steps(plan):
    if plan["radio"] == "bluetooth":
        tx = plan["tx"]
        exact(tx, {"phy", "preset"}, "BLE tx")
        if tx["phy"] not in ("1m", "2m") or tx["preset"] not in ("low", "mid", "high"):
            raise RadioBlocked("Only source-confirmed BLE 1m/2m low/mid/high presets implemented")
        phy = ("1m", "2m").index(tx["phy"])
        channel = ("low", "mid", "high").index(tx["preset"])
        return ([("fcbttest_0_0_0", {}), (f"fcbttest_3_4_{phy}", {}), (f"fcbttest_0_5_{channel}", {})],
                [("fcbttest_0_6_9", {}), ("fcbttest_0_2_0", {})])
    exact(plan["tx"], {f.name for f in fields(UwbTxConfig)}, "UWB tx")
    return uwb_tx_plan(UwbTxConfig(**plan["tx"]))


def simulation_phone_profile(plan):
    # Domains are explicit fixture values, never copied into a hardware profile automatically.
    domains = {}
    for key, arguments in sum(at_steps(plan), []):
        domains[key] = {name: [str(value)] for name, value in arguments.items()}
    return Profile("SIMULATION", "fixture", argument_domains=domains)


def validate_plan(plan):
    if not isinstance(plan, dict): raise ValueError("Radio plan must be an object")
    version = plan.get("schema_version")
    if type(version) is not int or version not in (1, 2): raise ValueError("Radio schema_version must be integer 1 or 2")
    exact(plan, {"schema_version", "radio", "backend", "simulation_only", "tx", "sweep", "sample_count",
                 "settle_seconds", "state_timeout", "verification", "simulation"} | ({"scan"} if version == 2 else set()), "radio plan")
    radio = plan["radio"]
    if radio not in RADIOS or plan["backend"] != RADIOS[radio]["backend"]:
        raise RadioBlocked("Unsupported radio/backend: no verified start/stop implementation")
    if type(plan["simulation_only"]) is not bool:
        raise ValueError("simulation_only must be Boolean")
    exact(plan["sweep"], {f.name for f in fields(Sweep)}, "sweep")
    sweep = Sweep(**plan["sweep"])
    sweep.validate(1e12)
    integer(plan["sample_count"], "sample_count", 1, 500)
    number(plan["settle_seconds"], "settle_seconds", 0, 30)
    number(plan["state_timeout"], "state_timeout", 0.1, 3600)
    if radio in ("bluetooth", "uwb"):
        profile = simulation_phone_profile(plan)
        for key, args in sum(at_steps(plan), []):
            Catalog().build(key, profile=profile, **args)
    elif radio == "cellular":
        exact(plan["tx"], {f.name for f in fields(LteRmcConfig)}, "LTE RMC tx")
        lte_rmc_plan(LteRmcConfig(**plan["tx"]))
    else:
        exact(plan["tx"], {"tech_index", "rate_index"}, "NFC tx")
        NfcRequest(31, **plan["tx"])
    if radio != "nfc" and plan["verification"] is not None:
        raise ValueError("verification is only defined for NFC")
    if radio == "nfc":
        v = plan["verification"]
        exact(v, {"on_threshold_dbm", "off_threshold_dbm", "quiet_seconds", "poll_seconds"}, "NFC verification")
        for key in ("on_threshold_dbm", "off_threshold_dbm"):
            number(v[key], key, -150, 40)
        if v["off_threshold_dbm"] >= v["on_threshold_dbm"]:
            raise ValueError("OFF threshold must be below ON threshold")
        number(v["quiet_seconds"], "quiet_seconds", .01, 300)
        number(v["poll_seconds"], "poll_seconds", .005, 10)
    if plan["simulation_only"]:
        m = plan["simulation"]
        exact(m, {"center_hz", "bandwidth_hz", "tx_dbm", "path_loss_db", "noise_dbm"}, "synthetic model")
        number(m["center_hz"], "center_hz", 1, 1e12)
        number(m["bandwidth_hz"], "bandwidth_hz", 1, 2e9)
        number(m["tx_dbm"], "tx_dbm", -100, 40)
        number(m["path_loss_db"], "path_loss_db", 0, 200)
        number(m["noise_dbm"], "noise_dbm", -200, -20)
        if not sweep.start_hz <= m["center_hz"] <= sweep.stop_hz:
            raise ValueError("Synthetic source center must lie inside sweep")
    elif plan["simulation"] is not None:
        raise ValueError("Hardware plan must remove synthetic model (simulation=null)")
    if version == 2:
        from .radio_scan_contracts import validate_scan
        validate_scan(plan)
    return sweep


def radio_template(radio, *, scan=False):
    if radio not in RADIOS:
        raise RadioBlocked("Unknown radio")
    tx = {"bluetooth": {"phy": "2m", "preset": "low"},
          "uwb": asdict(UwbTxConfig(9, 0, 2000, 750, 1000, power_code=0)),
          "cellular": asdict(LteRmcConfig(1, 18000, 20, 50)),
          "nfc": {"tech_index": 0, "rate_index": 0}}[radio]
    center, width = {"bluetooth": (2.44e9, 2e6), "cellular": (1.95e9, 20e6),
                     "nfc": (13.56e6, 1e6), "uwb": (8e9, 500e6)}[radio]
    span = width * 2
    plan = {"schema_version": 1, "radio": radio, "backend": RADIOS[radio]["backend"], "simulation_only": True,
            "tx": tx, "sweep": asdict(Sweep(center-span/2, center+span/2, 1e6, 1e6, 10, 10, points=101, sweep_seconds=.01)),
            # Verification includes durable per-command logging; slow disks need margin.
            "sample_count": 3, "settle_seconds": .01, "state_timeout": 15,
            "verification": {"on_threshold_dbm": -70, "off_threshold_dbm": -90, "quiet_seconds": .02, "poll_seconds": .01} if radio == "nfc" else None,
            "simulation": {"center_hz": center, "bandwidth_hz": width, "tx_dbm": 0, "path_loss_db": 20, "noise_dbm": -100}}
    if scan:
        from .radio_scan_contracts import scan_template
        plan.update(schema_version=2, sample_count=1, scan=scan_template())
    return plan


def radio_devices(plan, measurement_config=None):
    required = {"SpectrumAnalyzer", RADIOS[plan["radio"]]["source_device"]}
    if plan["schema_version"] == 2:
        from .radio_scan_contracts import FACILITIES
        required |= FACILITIES
    if measurement_config is not None: required.add("EmiReceiver")
    return required


def nfc_profile_template():
    return {"schema_version": 1, "device_id": "NfcPrbs", "mode": "hardware", "config": {
        "model": "", "build": "", "serial": "", "apk_sha256": "", "sender_permission_verified": False,
        "transition_bound_verified": False, "transition_bound_seconds": 0, "evidence_notes": ""}}


def validate_nfc_profile(profile):
    exact(profile, {"schema_version", "device_id", "mode", "config"}, "NFC profile")
    if type(profile["schema_version"]) is not int or profile["schema_version"] != 1 or profile["device_id"] != "NfcPrbs" or profile["mode"] != "hardware":
        raise ValueError("NfcPrbs hardware schema 1 required")
    c = profile["config"]
    exact(c, set(nfc_profile_template()["config"]), "NFC config")
    if c["transition_bound_verified"] is not True or not isinstance(c["evidence_notes"], str) or not c["evidence_notes"].strip():
        raise RadioBlocked("NFC requires commissioned asynchronous transition bound and evidence")
    number(c["transition_bound_seconds"], "transition_bound_seconds", .01, 300)
    for key in ("model", "build", "apk_sha256", "serial"):
        if not isinstance(c[key], str) or not c[key].strip():
            raise ValueError(f"Explicit NFC {key} required")
    # Constructor validates hash/permission/serial but does not launch ADB.
    AdbNfcTransport(c["serial"], NfcProfile(c["model"], c["build"], c["apk_sha256"], c["sender_permission_verified"]))


def check_radio(plan, mode, profiles=None, measurement_config=None):
    sweep = validate_plan(plan)
    if mode not in ("simulation", "hardware") or plan["simulation_only"] != (mode == "simulation"):
        raise ValueError("Explicit execution mode must match simulation_only")
    source = RADIOS[plan["radio"]]["source_device"]
    required = radio_devices(plan, measurement_config)
    receiver_check = None
    if measurement_config is not None:
        from .receiver_measurement import validate_measurement
        receiver_check = validate_measurement(measurement_config, plan, simulated=mode == "simulation",
            profile=profiles.get("EmiReceiver") if isinstance(profiles, dict) and mode == "hardware" else None)
    if mode == "simulation":
        if profiles:
            raise ValueError("Simulation must not accept site profiles")
    else:
        exact(profiles, required, "site profiles")
        for name, profile in profiles.items():
            if name == "NfcPrbs":
                validate_nfc_profile(profile)
            else:
                require_profile(profile)
                if profile["device_id"] != name or profile["mode"] != "hardware":
                    raise ValueError("Matching hardware-only profiles required")
        analyzer = profiles["SpectrumAnalyzer"]["config"]
        sweep.validate(analyzer["parameters"]["max_frequency_hz"])
        if sweep.sweep_seconds >= analyzer["transport"].get("timeout", 10):
            raise ValueError("Analyzer timeout must exceed sweep duration")
        if source == "PhoneAt":
            profile = _phone_profile(profiles[source]["config"], "hardware")
            for key, args in sum(at_steps(plan), []):
                if key not in profile.allowed_commands:
                    raise RadioBlocked(f"Phone profile does not authorize {key}")
                Catalog().build(key, profile=profile, **args)
        if source == "NfcPrbs":
            minimum = (profiles[source]["config"]["transition_bound_seconds"] + plan["verification"]["quiet_seconds"]
                       + analyzer["transport"].get("timeout", 10))
            if plan["state_timeout"] <= minimum:
                raise ValueError("NFC timeout must exceed transition bound + quiet window + analyzer I/O timeout")
        if plan["schema_version"] == 2:
            from .radio_scan_contracts import check_scan_site
            check_scan_site(plan, profiles)
    return {"valid": True, "radio": plan["radio"], "backend": plan["backend"], "mode": mode,
            "connection_attempted": False, "physical_verified": False, "required_profiles": sorted(required),
            "scope": deepcopy(RADIOS[plan["radio"]]), "receiver_measurement": receiver_check}
