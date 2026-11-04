"""Package reviewed metadata/templates, not vendor executables or manuals."""
from pathlib import Path
import json
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = ROOT.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    lab, rf = LIBRARIES / "lab-control", LIBRARIES / "phone-rf"
    sources = {s["id"]: s for s in read(lab / "dgm_lab/data/sources.json")}
    legacy = read(lab / "dgm_lab/data/instruments.json")
    descriptors, templates = [], {}
    for item in read(lab / "dgm_lab/data/capabilities.json"):
        device_id = item["driver"]
        # Report-only metadata misses implemented drivers from the earlier inventory.
        matches = [row for row in legacy if row["driver"] == device_id]
        source_ids = sorted(set(item["source_ids"]) | {row["source_id"] for row in matches if row["source_id"]})
        if not source_ids:
            raise ValueError(f"Missing driver provenance: {device_id}")
        kind = "facility" if device_id in {"Co3000", "OspSwitch", "EspecController", "Thermotron8800"} else "instrument"
        descriptors.append({**item, "id": device_id, "kind": kind, "backend": "dgm_lab", "status": "implemented_uncommissioned",
                            "simulation_available": device_id in {"OdaEx", "Co3000"},
                            "source_ids": source_ids, "sources": [sources[key] for key in source_ids],
                            "models": [{key: row[key] for key in ("manufacturer", "model", "status")} for row in matches],
                            "sdk_is_manufacturer_endorsed": False})
        templates[device_id] = {"schema_version": 1, "device_id": device_id, "mode": "hardware",
                                "config": read(lab / item["profile_path"])}
    descriptors.append({"id": "PhoneAt", "driver": "PhoneAt", "kind": "smartphone", "backend": "dgm_rf",
                        "status": "implemented_uncommissioned", "simulation_available": True, "physical_verified": False,
                        "sdk_is_manufacturer_endorsed": False,
                        "operations": [], "methods": {}, "lifecycle": "active(config=WlanTxConfig) or active(setup=..., cleanup=...)",
                        "source_ids": ["phone-static-catalog"],
                        "sources": [{"id": "phone-static-catalog", "kind": "static_analysis_not_official_sdk", "url": "https://github.com/hctinno/DEVICE/blob/main/libraries/phone-rf/README.md"}],
                        "site_requirements": ["exact model/build and OEM test environment", "validated AT serial port", "per-command allowlist and argument domains", "measured RF ON/OFF"],
                        "excludes": ["latest OEM blanket support", "iPhone", "NFC protected-service transport", "Qualcomm/Broadcom shell execution", "cellular TX without verified commands"]})
    templates["PhoneAt"] = {"schema_version": 1, "device_id": "PhoneAt", "mode": "hardware",
        "config": {"driver": "PhoneAt", "parameters": {"profile": read(rf / "profiles/device-template.json")},
                   "transport": {"kind": "serial", "port": "", "baudrate": 0}, "notes": "Hardware template is intentionally incomplete."}}
    chipset = read(rf / "dgm_rf/data/chipset-commands.json")
    for name, source_ids, reason in [
        ("QualcommMyftm", ["qualcomm-myftm"], "Linux/glibc package; Android build and complete TX/RX CLI mapping missing"),
        ("BroadcomWl", ["infineon-an225347", "infineon-wl-cli", "android-bcm4389-chanspec"], "CLI fragments and driver encoding only; no commissioned phone executor"),
        ("AppleRF", [], "OEM test SDK/firmware and RF start/stop interface missing"),
        ("NfcProtectedService", [], "No generic serial executor; use conditional radio-run nfc_prbs with commissioned NfcPrbs profile")]:
        descriptors.append({"id": name, "kind": "smartphone", "backend": None, "status": "reference_only" if source_ids else "blocked",
                            "simulation_available": False, "physical_verified": False, "sdk_is_manufacturer_endorsed": False,
                            "operations": [], "methods": {}, "lifecycle": None, "source_ids": source_ids,
                            "sources": [{"id": key, **chipset["sources"][key]} for key in source_ids],
                            "site_requirements": [reason], "excludes": ["live control"]})
        if name == "NfcProtectedService":
            descriptors[-1]["excludes"] = ["generic serial control; conditional protected-service path is separate in radio-run"]
    simulation = {}
    for device_id, parameters in {
        "OdaEx": {"model": "EX60-40", "expected_serial": "SIMULATION-ONLY", "expected_firmware": "SIMULATION", "max_voltage": 5, "max_current": 1, "installed_model_confirmed": True},
        "Co3000": {"axes": {"MA1": {"unit": "CM", "min": 100, "max": 400}, "DT1": {"unit": "DG", "min": 0, "max": 360}}, "motion_enabled": True, "poll_seconds": 0.01},
        "PhoneAt": {"profile": read(rf / "profiles/simulation.json")},
    }.items():
        simulation[device_id] = {"schema_version": 1, "device_id": device_id, "mode": "simulation",
            "config": {"driver": device_id, "parameters": parameters, "transport": {"kind": "simulation"}, "notes": "SIMULATION ONLY. Values are fixture data, not a site configuration."}}
    virtual_models = {"PhoneAt": "6GHz HE20/40/80/160 fixture", "SpectrumAnalyzer": "N9030B", "UsbPowerSensor": "NRP18S",
                      "SignalGenerator": "SMW200A", "OdaEx": "EX60-40", "OspSwitch": "OSP120 + OSP-B102", "Co3000": "MA1 + DT1"}
    for descriptor in descriptors:
        descriptor["integrated_virtual_model"] = virtual_models.get(descriptor["id"])
        descriptor["equipment_type"] = {
            "SpectrumAnalyzer": "스펙트럼 분석기", "EmiReceiver": "EMI 수신기", "SignalGenerator": "RF 신호발생기",
            "PowerSupply": "DC 전원공급기", "OdaEx": "DC 전원공급기", "PSeriesPowerMeter": "전력계",
            "UsbPowerSensor": "USB 파워센서", "VectorNetworkAnalyzer": "벡터 네트워크 분석기", "CmwLte": "통신 테스트 장비",
            "Thermotron8800": "환경 챔버 제어기", "EspecController": "환경 챔버 제어기", "Hp437B": "전력계",
            "Co3000": "턴테이블·안테나 마스트 제어기", "OspSwitch": "RF 스위치 제어기", "EpmPowerMeter": "전력계",
            "Cmu200Cw": "통신 테스터 CW 발생 기능", "PhoneAt": "프로파일 기반 단말 AT 제어"
        }.get(descriptor["id"], "단말 제어 인터페이스")
        descriptor["manufacturers"] = sorted({row["manufacturer"] for row in descriptor.get("models", []) + descriptor.get("report_models", [])})
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    payload = {"schema_version": 1, "sdk_version": version, "devices": descriptors, "hardware_templates": templates, "simulation_templates": simulation}
    target = ROOT / "dgm_control/data/catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SDK: {len(descriptors)} descriptors, {len(templates)} hardware templates, {len(simulation)} simulators")


if __name__ == "__main__":
    main()
