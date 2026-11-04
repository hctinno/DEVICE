import argparse
import json
from pathlib import Path
from . import devices, describe, profile_template, check_profile, load_profile, doctor, error_details


def main():
    parser = argparse.ArgumentParser(prog="dgm-control", description="DGM DeviceControl: explicit support, offline setup, reviewed lifecycle")
    actions = parser.add_subparsers(dest="action", required=True)
    listing = actions.add_parser("list", help="List SDK families and support states; no I/O")
    listing.add_argument("--kind", choices=["instrument", "facility", "smartphone"])
    show = actions.add_parser("show", help="Methods, source URLs and remaining site requirements")
    show.add_argument("device_id")
    init = actions.add_parser("init", help="Create a NEW profile file; no I/O")
    init.add_argument("device_id")
    init.add_argument("--mode", choices=["simulation", "hardware"], default="hardware")
    init.add_argument("--output", required=True)
    check = actions.add_parser("check", help="Offline structural validation, not hardware commissioning")
    check.add_argument("profile")
    actions.add_parser("doctor", help="Local Python/module diagnostics; no device discovery")
    demo = actions.add_parser("demo", help="Hardware-free power + motion + smartphone demo")
    demo.add_argument("--output-dir", required=True)
    demo.add_argument("--inject-failure", action="store_true")
    virtual = actions.add_parser("virtual-run", help="Coupled virtual WLAN lab; never opens hardware")
    virtual.add_argument("--output-dir", required=True)
    virtual.add_argument("--scenario", help="JSON Scenario fields; synthetic model parameters only")
    virtual.add_argument("--fault", choices=["analyzer-timeout", "malformed", "stuck-motion", "phone-stop"], help="Inject a reproducible failure")
    actions.add_parser("virtual-info", help="Integrated virtual device models and limitations")
    actions.add_parser("radio-list", help="Radio backends, source scopes and unconfirmed commands")
    radio_init = actions.add_parser("radio-init", help="Create a simulation-only radio plan, never a site configuration")
    radio_init.add_argument("radio", choices=["bluetooth", "cellular", "nfc", "uwb"])
    radio_init.add_argument("--output", required=True)
    radio_init.add_argument("--scan", action="store_true", help="Create schema-2 turntable/mast/RF-path scan plan")
    nfc_profile = actions.add_parser("radio-profile", help="Create incomplete protected NFC hardware profile")
    nfc_profile.add_argument("radio", choices=["nfc"])
    nfc_profile.add_argument("--output", required=True)
    for name in ("radio-check", "radio-run"):
        action = actions.add_parser(name, help="Offline radio preflight" if name == "radio-check" else "Explicit virtual or REAL radio execution with evidence")
        action.add_argument("--mode", required=True, choices=["simulation", "hardware"])
        action.add_argument("--plan", required=True)
        action.add_argument("--profiles-dir")
        if name == "radio-run":
            action.add_argument("--output-dir", required=True)
            action.add_argument("--cancel-file")
            from .radio_run import FAULTS
            action.add_argument("--fault", choices=FAULTS)
    for name in ("hardware-check", "hardware-run"):
        hardware = actions.add_parser(name, help="Offline WLAN preflight" if name == "hardware-check" else "REAL WLAN output and motion using explicit site profiles")
        hardware.add_argument("--profiles-dir", required=True, help="Directory with six device-ID.json hardware profiles")
        hardware.add_argument("--plan", required=True, help="Fully specified commissioned WLAN plan JSON")
        if name == "hardware-run":
            hardware.add_argument("--output-dir", required=True, help="New private run directory; never overwritten")
            hardware.add_argument("--cancel-file", help="Stop at the next checkpoint when this file exists")
    args = parser.parse_args()
    try:
        exit_code = 0
        if args.action.startswith("radio-"):
            import threading
            from .radio_contracts import radio_catalog, radio_template, nfc_profile_template, check_radio
            from .radio_run import load_radio_profiles, run_radio
            from .hardware_run import cancellation_signals
            if args.action == "radio-list": output = radio_catalog()
            elif args.action in ("radio-init", "radio-profile"):
                value = radio_template(args.radio, scan=args.scan) if args.action == "radio-init" else nfc_profile_template()
                with Path(args.output).open("x", encoding="utf-8") as handle:
                    json.dump(value, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                output = {"written": args.output, "connection_attempted": False}
            else:
                plan = load_profile(args.plan)
                if args.mode == "simulation" and args.profiles_dir is not None:
                    raise ValueError("Simulation must not use site profiles")
                if args.action == "radio-check":
                    profiles = load_radio_profiles(plan, args.profiles_dir) if args.mode == "hardware" else None
                    output = check_radio(plan, args.mode, profiles)
                else:
                    event = threading.Event()
                    with cancellation_signals(event):
                        output = run_radio(plan, args.mode, args.output_dir, profiles_dir=args.profiles_dir,
                                           cancelled=event, cancel_file=args.cancel_file, fault=args.fault)
                    exit_code = {"completed": 0, "failed": 2, "blocked": 2, "cancelled": 130}[output["status"]]
        elif args.action == "list":
            output = [{key: row[key] for key in ("id", "kind", "equipment_type", "manufacturers", "status", "simulation_available", "integrated_virtual_model", "physical_verified")} for row in devices(args.kind)]
        elif args.action == "show":
            output = describe(args.device_id)
        elif args.action == "doctor":
            output = doctor()
        elif args.action == "init":
            profile = profile_template(args.device_id, args.mode)
            with Path(args.output).open("x", encoding="utf-8") as handle:
                json.dump(profile, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            output = {"profile_written": args.output, "connection_attempted": False, "check": check_profile(profile)}
        elif args.action == "check":
            output = check_profile(load_profile(args.profile))
            exit_code = 0 if output["valid"] else 2
        elif args.action == "virtual-info":
            from .virtual_lab import VIRTUAL_MODELS
            output = {"models": VIRTUAL_MODELS, "model": "dgm-behavioral-rf-v1", "simulated": True,
                      "physical_verified": False, "radios": ["WLAN 6GHz HE20/40/80/160"],
                      "scope": "Legacy WLAN motion scan; other radios use radio-run",
                      "radio_run_available": ["bluetooth", "cellular", "nfc", "uwb"],
                      "not_implemented": ["waveform physics", "FCC conformity"]}
        elif args.action == "virtual-run":
            from .virtual_recipe import run_virtual
            from .virtual_world import Scenario, Fault
            faults = {"analyzer-timeout": Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1"),
                      "malformed": Fault("UsbPowerSensor", "FETC?", "malformed", 2),
                      "stuck-motion": Fault("Co3000", "GO", "stuck"),
                      "phone-stop": Fault("PhoneAt", "AT+WIFITEST=0,2,0,0")}
            scenario = Scenario(**load_profile(args.scenario)) if args.scenario else None
            output = run_virtual(args.output_dir, scenario=scenario, fault=faults.get(args.fault))
        elif args.action in ("hardware-check", "hardware-run"):
            import threading
            from .hardware_run import load_hardware_inputs, check_hardware, run_hardware, cancellation_signals
            profiles, plan = load_hardware_inputs(args.profiles_dir, args.plan)
            if args.action == "hardware-check":
                output = check_hardware(profiles, plan)
            else:
                event = threading.Event()
                with cancellation_signals(event):
                    output = run_hardware(profiles, plan, args.output_dir, cancelled=event, cancel_file=args.cancel_file)
                exit_code = {"completed": 0, "failed": 2, "cancelled": 130}[output["status"]]
        else:
            from .demo import run_demo
            output = run_demo(args.output_dir, inject_failure=args.inject_failure)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return exit_code
    except (Exception, BaseExceptionGroup) as exc:
        parser.exit(2, json.dumps(error_details(exc), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
