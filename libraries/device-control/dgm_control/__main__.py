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
    args = parser.parse_args()
    try:
        exit_code = 0
        if args.action == "list":
            output = [{key: row[key] for key in ("id", "kind", "status", "simulation_available", "physical_verified")} for row in devices(args.kind)]
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
        else:
            from .demo import run_demo
            output = run_demo(args.output_dir, inject_failure=args.inject_failure)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return exit_code
    except Exception as exc:
        parser.exit(2, json.dumps(error_details(exc), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
