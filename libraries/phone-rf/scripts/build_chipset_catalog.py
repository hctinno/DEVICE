"""Build an offline catalog from reviewed factual snapshots (no network)."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = json.loads((ROOT / "research/chipsets/evidence.json").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "research/chipsets/commands.json").read_text(encoding="utf-8"))
    catalog["sources"] = evidence["sources"]
    catalog["qualcomm_enums"] = evidence["qualcomm_enums"]
    catalog["provenance"] = {"observed_on": evidence["observed_on"], "qualcomm_members": evidence["qualcomm_members"],
                             "help_offset": evidence["qualcomm_help_offset"], "runtime": evidence["runtime"]}
    ids = [row["id"] for row in catalog["commands"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate command id")
    for row in catalog["commands"]:
        if row["evidence"] not in catalog["sources"]:
            raise ValueError(f"missing source: {row['id']}")
    verified = 0
    for source in catalog["sources"].values():
        path = ROOT / ".manual-cache/chipsets" / source["file"]
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"local source hash mismatch: {path.name}")
            verified += 1
    output = ROOT / "dgm_rf/data/chipset-commands.json"
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 칩셋 터미널 명령·숫자표", "", "자동 생성: `python scripts/build_chipset_catalog.py`. 원본은 `research/chipsets/`. 실폰 검증 0건. `argv`는 문법 참조이며 연결·초기화·시작·종료가 보장된 전체 시험 절차가 아닙니다.", "", "## 명령", "", "| ID | 인수 | 의미 | 상태·근거 |", "| --- | --- | --- | --- |"]
    for row in catalog["commands"]:
        argv = " ".join(row["argv"]) if row["argv"] else "미확정"
        lines.append(f"| {row['id']} | `{argv}` | {row['meaning']} | {row['status']}; {row['evidence']} {row['locator']} |")
    lines += ["", "## Qualcomm 헤더 enum", "", "아래는 공개 배포된 `art_utf_common.h`의 기호와 정수입니다. CLI dispatch/firmware 동작과 동일하다고 검증한 표가 아닙니다. `TCMD_CONT_TX_*`를 그대로 `-t`/`--txMode` 인수에 넣는 실행기는 제공하지 않습니다. INVALID는 sentinel입니다. `11AX_HE320` 등 vendor 기호는 표준 적합성이나 해당 칩 지원의 증명이 아닙니다."]
    for name, rows in catalog["qualcomm_enums"].items():
        lines += ["", f"### {name}", "", "| 기호 | 정수 | 헤더 줄 |", "| --- | ---: | ---: |"]
        lines += [f"| `{row['symbol']}` | {row['value']} | {row['line']} |" for row in rows]
    lines += ["", "## 출처", ""]
    for name, source in catalog["sources"].items():
        lines += [f"- [{name}]({source['url']}): SHA-256 `{source['sha256']}`; {source['bytes']} bytes."]
    (ROOT / "docs/CHIPSET_COMMANDS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"commands": len(ids), "enum_facts": sum(map(len, catalog["qualcomm_enums"].values())), "local_sources_verified": verified, "physical_phone_tests": 0}))


if __name__ == "__main__":
    main()
