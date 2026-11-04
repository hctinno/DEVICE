"""Static, non-executing evidence extraction into ignored local cache."""
from pathlib import Path
import hashlib
import json
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".manual-cache" / "chipsets"


def main():
    archive = CACHE / "ath6kl-utils_1.0.0_arm64.tar.gz"
    inventory = []
    from acquire_chipset_sources import SOURCES
    if hashlib.sha512(archive.read_bytes()).hexdigest() != SOURCES["qualcomm-myftm"]["sha512"]:
        raise ValueError("publisher SHA512 mismatch")
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            stream = tar.extractfile(member)
            payload = stream.read()
            name = Path(member.name).name
            inventory.append({"member": member.name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
            if name.endswith(".h") or name in {"copyright", "NOTICE", "LICENSE.qcom-2"}:
                (CACHE / name).write_bytes(payload)
            if name == "myftm":
                strings = [f"0x{match.start():x}\t{match.group().decode('ascii')}" for match in re.finditer(rb"[\x20-\x7e\t\n]{5,}", payload)]
                (CACHE / "myftm.strings.txt").write_text("\n".join(strings), encoding="utf-8")
                (CACHE / "myftm.elf.json").write_text(json.dumps({"magic": payload[:4].hex(), "elf_class": payload[4], "endianness": payload[5], "machine": int.from_bytes(payload[18:20], "little")}, indent=2), encoding="utf-8")
    (CACHE / "members.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    header = (CACHE / "art_utf_common.h").read_text(encoding="utf-8")
    enum_names = {"TCMD_RATEBW", "TCMD_GI", "TCMD_CONT_TX_MODE", "TCMD_CONT_RX_ACT",
                  "TCMD_PPDU_TYPE", "TCMD_LINK_DIR", "PHY_RF_MODE", "PHY_RF_SUBMODE"}
    enums = {}
    for match in re.finditer(r"typedef enum\s*\{([^{}]+)\}\s*(\w+)\s*;", header):
        body, name = match.groups()
        if name not in enum_names:
            continue
        rows, value = [], -1
        for item in re.finditer(r"^\s*(\w+)\s*(?:=\s*(-?\d+))?\s*,?\s*$", body, re.MULTILINE):
            symbol, assigned = item.groups()
            value = int(assigned) if assigned is not None else value + 1
            line = header[:match.start(1) + item.start() + item.group().index(symbol)].count("\n") + 1
            rows.append({"symbol": symbol, "value": value, "line": line})
        enums[name] = rows
    # Commit factual identifiers/numbers and provenance, never vendor headers or binaries.
    snapshot = {"schema_version": 1, "observed_on": "2026-11-04", "sources": json.loads((CACHE / "acquisition.json").read_text(encoding="utf-8")),
                "qualcomm_members": inventory, "qualcomm_enums": enums,
                "qualcomm_help_offset": "0x23c78", "runtime": json.loads((CACHE / "myftm.elf.json").read_text(encoding="utf-8"))}
    output = ROOT / "research" / "chipsets" / "evidence.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    import fitz
    with fitz.open(CACHE / "AN225347.pdf") as pdf:
        for number in [34, 35]:
            pdf[number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(CACHE / f"AN225347-p{number + 1}.png")
        (CACHE / "AN225347.txt").write_text("\n".join(f"\nPDF PAGE {i + 1}\n" + page.get_text() for i, page in enumerate(pdf)), encoding="utf-8")
    print("Static evidence extracted; no executable invoked.")


if __name__ == "__main__":
    main()
