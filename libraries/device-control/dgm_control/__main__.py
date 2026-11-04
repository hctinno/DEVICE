import argparse
import json
from pathlib import Path
from . import devices, describe, profile_template, check_profile, load_profile, doctor, error_details


def main():
    parser = argparse.ArgumentParser(prog="dgm-control", description="DGM DeviceControl: explicit support, offline setup, reviewed lifecycle")
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser('equipment-list',help='Reviewed native equipment families/models, sources and operation signatures; no I/O')
    equipment_init = actions.add_parser('equipment-init',help='NEW bounded equipment job, including explicit profile and lifecycle')
    equipment_init.add_argument('device_id')
    equipment_init.add_argument('--model')
    equipment_init.add_argument('--mode',choices=['simulation','hardware'],default='simulation')
    equipment_init.add_argument('--output',required=True)
    equipment_check = actions.add_parser('equipment-check',help='Offline equipment job structure and method binding')
    equipment_check.add_argument('--job',required=True)
    equipment_run = actions.add_parser('equipment-run',help='Explicit simulated/REAL native equipment operations with evidence')
    equipment_run.add_argument('--job',required=True)
    equipment_run.add_argument('--output-dir',required=True)
    equipment_run.add_argument('--cancel-file')
    equipment_probe = actions.add_parser('equipment-probe',help='Explicit IDN/required-option query only; no automatic device discovery')
    equipment_probe.add_argument('--profile',required=True)
    equipment_probe.add_argument('--output-dir',required=True)
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
    virtual.add_argument("--evaluation", help="Explicit correction tables and declared criterion JSON")
    evaluation_init = actions.add_parser("evaluation-init", help="Write NEW synthetic correction/limit fixture, not a regulatory criterion")
    evaluation_init.add_argument("--workflow", required=True, choices=["radio", "wlan"])
    evaluation_init.add_argument("--plan", help="Required for radio; optional explicit WLAN plan")
    evaluation_init.add_argument("--output", required=True)
    actions.add_parser("detector-list", help="Model-specific verified workflow support, documented-only and unconfirmed states; no I/O")
    measurement_init = actions.add_parser("measurement-init", help="NEW synthetic receiver-grid fixture; not a regulatory test prescription")
    measurement_init.add_argument("--workflow", required=True, choices=["radio", "wlan"])
    measurement_init.add_argument("--plan", help="Required for radio; optional WLAN plan")
    measurement_init.add_argument("--detector", required=True, choices=["POS", "QP", "LINEAR_AVER", "CISPR_AVER"])
    measurement_init.add_argument("--output", required=True)
    from dgm_lab.detectors import RECEIVER_RANGES
    measurement_init.add_argument("--model", choices=sorted(RECEIVER_RANGES), default="ESW44")
    for action in (virtual, evaluation_init):
        action.add_argument("--measurement", help="Explicit receiver-grid measurement JSON; adds EmiReceiver")
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
        action.add_argument("--evaluation", help="Explicit correction tables and declared criterion JSON")
        action.add_argument("--measurement", help="Explicit receiver-grid measurement JSON; adds EmiReceiver")
        if name == "radio-run":
            action.add_argument("--output-dir", required=True)
            action.add_argument("--cancel-file")
            from .radio_run import FAULTS
            action.add_argument("--fault", choices=FAULTS)
    for name in ("hardware-check", "hardware-run"):
        hardware = actions.add_parser(name, help="Offline WLAN preflight" if name == "hardware-check" else "REAL WLAN output and motion using explicit site profiles")
        hardware.add_argument("--profiles-dir", required=True, help="Directory with six device-ID.json hardware profiles")
        hardware.add_argument("--plan", required=True, help="Fully specified commissioned WLAN plan JSON")
        hardware.add_argument("--evaluation", help="Explicit correction tables and declared criterion JSON")
        hardware.add_argument("--measurement", help="Explicit receiver-grid measurement JSON; adds EmiReceiver")
        if name == "hardware-run":
            hardware.add_argument("--output-dir", required=True, help="New private run directory; never overwritten")
            hardware.add_argument("--cancel-file", help="Stop at the next checkpoint when this file exists")
    args = parser.parse_args()
    try:
        exit_code = 0
        from .evaluation import Evaluation, evaluation_template, assessment_exit
        evaluation = load_profile(args.evaluation) if getattr(args, "evaluation", None) else None
        measurement_config = load_profile(args.measurement) if getattr(args, "measurement", None) else None
        if args.action.startswith('equipment-'):
            from .equipment import equipment_catalog, equipment_template, check_equipment, run_equipment, probe_equipment
            if args.action == 'equipment-list': output = equipment_catalog()
            elif args.action == 'equipment-init':
                value = equipment_template(args.device_id,args.model,mode=args.mode)
                with Path(args.output).open('x',encoding='utf-8') as handle:
                    json.dump(value,handle,ensure_ascii=False,indent=2,allow_nan=False)
                    handle.write('\n')
                output = dict(written=args.output,connection_attempted=False)
            elif args.action == 'equipment-check': output = check_equipment(load_profile(args.job))
            elif args.action == 'equipment-probe':
                output = probe_equipment(load_profile(args.profile),args.output_dir)
                exit_code = 0 if output['status']=='identified' else 2
            else:
                import threading
                from .hardware_run import cancellation_signals
                event = threading.Event()
                with cancellation_signals(event):
                    output = run_equipment(load_profile(args.job),args.output_dir,cancelled=event,cancel_file=args.cancel_file)
                exit_code = 0 if output['status']=='completed' else 130 if output['status']=='cancelled' else 2
        elif args.action == "detector-list":
            from .receiver_measurement import detector_catalog
            output = detector_catalog()
        elif args.action in ("evaluation-init", "measurement-init"):
            from .virtual_recipe import WlanScan
            from .hardware_run import plan_from_dict
            if args.workflow == "radio" and not args.plan: raise ValueError("Radio template requires --plan")
            plan = load_profile(args.plan) if args.plan else None
            if args.workflow == "wlan": plan = plan_from_dict(plan) if plan else WlanScan()
            if args.action == "measurement-init":
                from .receiver_measurement import measurement_template
                value = measurement_template(plan, args.detector, args.model)
            else:
                value = evaluation_template(plan, measurement_config)
            with Path(args.output).open("x", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
            output = {"written": args.output, "simulation_only": True, "connection_attempted": False}
        elif args.action.startswith("radio-"):
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
                    profiles = load_radio_profiles(plan, args.profiles_dir, measurement_config) if args.mode == "hardware" else None
                    output = check_radio(plan, args.mode, profiles, measurement_config)
                    if evaluation is not None: output["evaluation"] = Evaluation(evaluation, plan, simulated=args.mode == "simulation", measurement=measurement_config).preflight()
                else:
                    event = threading.Event()
                    with cancellation_signals(event):
                        output = run_radio(plan, args.mode, args.output_dir, profiles_dir=args.profiles_dir,
                                           cancelled=event, cancel_file=args.cancel_file, fault=args.fault, evaluation=evaluation, measurement_config=measurement_config)
                    exit_code = assessment_exit(output)
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
            output = run_virtual(args.output_dir, scenario=scenario, fault=faults.get(args.fault), evaluation=evaluation, measurement_config=measurement_config)
            exit_code = assessment_exit(output)
        elif args.action in ("hardware-check", "hardware-run"):
            import threading
            from .hardware_run import load_hardware_inputs, check_hardware, run_hardware, cancellation_signals
            profiles, plan = load_hardware_inputs(args.profiles_dir, args.plan, measurement_config)
            if args.action == "hardware-check":
                output = check_hardware(profiles, plan, measurement_config)
                if evaluation is not None: output["evaluation"] = Evaluation(evaluation, plan, simulated=False, measurement=measurement_config).preflight()
            else:
                event = threading.Event()
                with cancellation_signals(event):
                    output = run_hardware(profiles, plan, args.output_dir, cancelled=event, cancel_file=args.cancel_file, evaluation=evaluation, measurement_config=measurement_config)
                exit_code = assessment_exit(output)
        else:
            from .demo import run_demo
            output = run_demo(args.output_dir, inject_failure=args.inject_failure)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return exit_code
    except (Exception, BaseExceptionGroup) as exc:
        parser.exit(2, json.dumps(error_details(exc), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
