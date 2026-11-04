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
    sub.add_parser("chipset-catalog", help="Offline chipset evidence catalog; no device I/O")
    sub.add_parser("chipset-demo", help="Print uncommissioned command fragments; no device I/O")
    discovery = sub.add_parser("chipset-discovery", help="Print read-only ADB identification argv; do not execute")
    discovery.add_argument("--serial", required=True)
    args = parser.parse_args()
    catalog = Catalog()
    try:
        if args.action.startswith("chipset-"):
            from .chipset import catalog as chipset_catalog, android_discovery
            from .chipset import wl_6g_he_candidate, wl_tx_packets, wl_rx_packets, qualcomm_he_fields
            if args.action == "chipset-catalog":
                output = chipset_catalog()
            elif args.action == "chipset-discovery":
                output = {"executed": False, "argv": android_discovery(args.serial)}
            else:
                output = {"mode": "OFFLINE_ONLY", "physical_phone_verified": False,
                          "wl_channel_rate_candidate": wl_6g_he_candidate(1, 160, 0, 1).to_dict(),
                          "wl_tx_fragment": wl_tx_packets("00:11:22:33:44:55", gap_us=40, frame_bytes=1000, frame_count=0).to_dict(),
                          "wl_rx_fragment": wl_rx_packets("00:11:22:33:44:55", expected_packets=100, timeout_ms=1000).to_dict(),
                          "qualcomm_fields": qualcomm_he_fields(160, "TCMD_GI_LTF_MODE4_GI_3200", 1)}
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.action == "list":
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
