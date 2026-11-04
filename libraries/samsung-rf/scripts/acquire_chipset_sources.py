"""Acquire public evidence only; never execute a vendor binary."""
from pathlib import Path
import base64
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "qualcomm-myftm": {
        "url": "https://qartifactory-edge.qualcomm.com/artifactory/qsc_releases/software/chip/component/wlan-service.qclinux.0.0/260825/prebuilt_resolute/ath6kl-utils_1.0.0_arm64.tar.gz",
        "file": "ath6kl-utils_1.0.0_arm64.tar.gz",
        "sha512": "386332a7e794167f73dc85c62a211b7997c9b3ee0e7ee431fc5ab4c589b74ad5c5ee4d94413ecef1ebb4d84c68a1a116cbcbc63657f404280a65e937ecb50070",
        "pin": "https://github.com/qualcomm-linux/pkg-rpm-myftm/blob/57d7155316f41d5bdd508dc1f0ad808ce2b8bac5/sources",
    },
    "infineon-an225347": {
        "url": "https://community.infineon.com/gfawx74859/attachments/gfawx74859/cnwifimcu/299/1/Infineon-AN225347_-_Infineon_Wi-Fi_CLM_regulatory_manual-ApplicationNotes-v03_00-EN.pdf",
        "file": "AN225347.pdf",
    },
    "infineon-wl-cli": {
        "url": "https://community.infineon.com/gfawx74859/attachments/gfawx74859/twwifibtcombo/869/1/wl_002-23156.pdf",
        "file": "wl_002-23156.pdf",
    },
    "android-bcm4389-chanspec": {
        "url": "https://android.googlesource.com/kernel/google-modules/wlan/bcmdhd/bcm4389/+/f4f47d23121928735adfe73a133a7c93542fe11f/bcmwifi_channels.c?format=TEXT",
        "file": "bcmwifi_channels.c",
        "encoding": "base64",
    },
    "android-bcm4389-channel-limits": {
        "url": "https://android.googlesource.com/kernel/google-modules/wlan/bcmdhd/bcm4389/+/f4f47d23121928735adfe73a133a7c93542fe11f/include/bcmwifi_channels.h?format=TEXT",
        "file": "bcmwifi_channels.h",
        "encoding": "base64",
    },
}


def main():
    target = ROOT / ".manual-cache" / "chipsets"
    target.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, source in SOURCES.items():
        path = target / source["file"]
        try:
            if path.exists():
                payload = path.read_bytes()
            else:
                request = urllib.request.Request(source["url"], headers={"User-Agent": "DGM-RF-source-audit/1.0"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = response.read(64 * 1024 * 1024 + 1)
                if len(payload) > 64 * 1024 * 1024:
                    raise ValueError("source exceeds 64 MiB")
                if source.get("encoding") == "base64":
                    payload = base64.b64decode(payload)
            if "sha512" in source and hashlib.sha512(payload).hexdigest() != source["sha512"]:
                raise ValueError("publisher SHA512 mismatch")
            path.write_bytes(payload)
            results[name] = {**source, "status": "acquired", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        except Exception as exc:
            results[name] = {**source, "status": "unavailable", "error": str(exc)}
        print(name, results[name]["status"], results[name].get("error", results[name].get("bytes")))
    (target / "acquisition.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    if any(row["status"] != "acquired" for row in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
