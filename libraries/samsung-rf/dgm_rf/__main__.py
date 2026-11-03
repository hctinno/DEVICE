import argparse
import json
from pathlib import Path
from .core import Catalog, Controller, Profile, ScriptedTransport, WlanTxConfig, RFError


def main():
    parser = argparse.ArgumentParser(prog="dgm-rf")
    sub = parser.add_subparsers(dest="action", required=True)
    search = sub.add_parser("list")
    search.add_argument("--radio", choices=["wlan", "bluetooth", "cellular", "nfc", "uwb"])
    search.add_argument("--query", default="")
    show = sub.add_parser("show")
    show.add_argument("id")
    render = sub.add_parser("render")
    render.add_argument("id")
    render.add_argument("--value")
    render.add_argument("--profile")
    demo = sub.add_parser("demo")
    demo.add_argument("--log", default="demo-log.json")
    export = sub.add_parser("export")
    export.add_argument("path")
    args = parser.parse_args()
    catalog = Catalog()
    try:
        if args.action == "list":
            for row in catalog.search(args.query, args.radio):
                print(f"{row['id']}\t{row['status']}\t{row['template'] or '-'}\t{row['name']}")
        elif args.action == "show":
            print(json.dumps(catalog.entries[args.id], ensure_ascii=False, indent=2))
        elif args.action == "render":
            profile = Profile.load(args.profile) if args.profile else None
            params = {} if args.value is None else {"value": args.value}
            print(catalog.build(args.id, profile=profile, **params).wire)
        elif args.action == "export":
            Path(args.path).write_text(json.dumps(catalog.data, ensure_ascii=False, indent=2), encoding="utf-8")
        elif args.action == "demo":
            # These are software fixture values, not a validated phone configuration.
            profile = Profile(model="SIMULATION", build="NO_DEVICE", simulation_only=True,
                argument_domains={
                    "wifitest_0_0_0": {"value": ["17"]},
                    "wifitest_0_0_3": {"value": ["0.0"]},
                    "wifitest_0_0_4": {"value": ["1000"]},
                    "wifitest_0_0_5": {"value": ["1000"]}})
            controller = Controller(ScriptedTransport(), profile)
            config = WlanTxConfig(3,9,17,15,1,5,1,"0.0",1000,1000)
            with controller.wlan_tx(config):
                print("SIMULATION: WLAN 6 GHz HE160 TX acknowledged; no phone or RF measurement.")
            controller.save_log(args.log)
            print(f"SIMULATION: cleanup acknowledged; {len(controller.log)} events; {args.log}")
    except (RFError, KeyError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
