"""Validate common SDK, its three-device demo and clean wheel installation.

No physical addresses, vendor SDKs, ADB servers or lab interfaces are opened.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "libraries/device-control"
PACKAGES = [ROOT / "libraries/phone-rf", ROOT / "libraries/lab-control", SDK]


def run(argv, *, cwd=ROOT, env=None, expected=0):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != expected:
        raise RuntimeError(f"{argv!r} returned {result.returncode}, expected {expected}\n{result.stdout}\n{result.stderr}")
    return result


def main():
    started = time.monotonic()
    report = {"utc": datetime.now(timezone.utc).isoformat(), "passed": False, "physical_tests": 0, "phone_rf_tests": 0,
              "skipped": ["Real TCP/VISA/serial instruments", "Physical motion and independent stopping", "Phone firmware and RF ON/OFF", "FCC measurement/conformity"]}
    try:
        print(run([sys.executable, str(SDK / "scripts/build_sdk_catalog.py")]).stdout.strip(), flush=True)
        print(run([sys.executable, str(ROOT / "scripts/render_supported_equipment.py")]).stdout.strip(), flush=True)
        print(run([sys.executable, str(ROOT / "scripts/check_public_naming.py")]).stdout.strip(), flush=True)
        paths = [str(path) for path in PACKAGES]
        sys.path[:0] = paths
        suite = unittest.defaultTestLoader.discover(str(SDK / "tests"))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        report.update(unit_tests=result.testsRun, failures=len(result.failures), errors=len(result.errors))
        if not result.wasSuccessful(): raise RuntimeError("SDK unit tests failed")
        bad = [chr(63)*3, chr(0xfffd), chr(0x6fe1), chr(0x6e72), chr(0x907a), chr(0x5a9b), chr(0xf9e1)]
        count = 0
        for path in SDK.rglob("*"):
            if {"build", "dist", "__pycache__"}.intersection(path.relative_to(SDK).parts) or not path.is_file(): continue
            if path.suffix in {".py", ".md", ".json", ".toml"}:
                content = path.read_text(encoding="utf-8")
                if any(token in content for token in bad): raise ValueError(f"Encoding marker: {path}")
                if path.suffix == ".py": compile(content, str(path), "exec")
                if path.suffix == ".json": json.loads(content)
                count += 1
        report["utf8_source_files"] = count
        with tempfile.TemporaryDirectory(prefix="dgm-sdk-check-") as temporary:
            temp = Path(temporary)
            wheels, installed = temp / "wheels", temp / "installed"
            for package in PACKAGES:
                run([sys.executable, "-m", "pip", "--disable-pip-version-check", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels), str(package)])
            built = sorted(wheels.glob("*.whl"))
            if len(built) != 3: raise RuntimeError("Expected exactly three wheels")
            for wheel in built:
                with zipfile.ZipFile(wheel) as archive:
                    if archive.testzip() is not None: raise RuntimeError("Damaged wheel")
                    if any(".manual-cache" in name or ".fcc-cache" in name for name in archive.namelist()):
                        raise RuntimeError("Vendor cache leaked into wheel")
            run([sys.executable, "-m", "pip", "--disable-pip-version-check", "install", "--no-index", "--find-links", str(wheels), "--target", str(installed), "dgm-device-control==0.5.0"], cwd=temp)
            env = dict(os.environ, PYTHONPATH=str(installed), PYTHONIOENCODING="utf-8")
            base = [sys.executable, "-s", "-m", "dgm_control"]
            checks = []
            def command(*args, expected=0):
                answer = run([*base, *args], cwd=temp, env=env, expected=expected)
                checks.append({"args": list(args), "exit_code": answer.returncode})
                return answer
            listed = json.loads(command("list").stdout)
            if len(listed) != 21: raise RuntimeError("Installed catalog missing")
            detail = json.loads(command("show", "Co3000").stdout)
            if not detail["sources"]: raise RuntimeError("Installed provenance missing")
            diagnosed = json.loads(command("doctor").stdout)
            if diagnosed["packages"]["dgm-device-control"] != "0.5.0": raise RuntimeError("Installed SDK version mismatch")
            profile = temp / "simulation.json"
            command("init", "OdaEx", "--mode", "simulation", "--output", str(profile))
            command("check", str(profile))
            before = profile.read_bytes()
            command("init", "OdaEx", "--mode", "simulation", "--output", str(profile), expected=2)
            if profile.read_bytes() != before: raise RuntimeError("Existing profile overwritten")
            hardware = temp / "hardware.json"
            command("init", "Co3000", "--output", str(hardware))
            command("check", str(hardware), expected=2)
            ok = temp / "success"
            passed = json.loads(command("demo", "--output-dir", str(ok)).stdout)
            if not all(passed["fixture_cleanup"].values()): raise RuntimeError("Installed success cleanup failed")
            failed = temp / "failure"
            command("demo", "--output-dir", str(failed), "--inject-failure", expected=2)
            failure = json.loads((failed / "failure.json").read_text(encoding="utf-8"))
            if (failed / "result.json").exists() or not all(failure["fixture_cleanup"].values()): raise RuntimeError("Installed failure cleanup invalid")
            command("init", "AppleRF", "--output", str(temp / "apple.json"), expected=2)
            if (temp / "apple.json").exists(): raise RuntimeError("Blocked backend wrote a profile")
            virtual_info = json.loads(command("virtual-info").stdout)
            if len(virtual_info["models"]) != 7: raise RuntimeError("Virtual model manifest missing")
            virtual = json.loads(command("virtual-run", "--output-dir", str(temp / "virtual")).stdout)
            if virtual["samples"] != 12 or virtual["peak"]["angle_deg"] != 90 or virtual["peak"]["height_cm"] != 200 or virtual["peak"]["polarization"] != "V":
                raise RuntimeError("Installed virtual scan peak disagrees with known fixture")
            command("virtual-run", "--output-dir", str(temp / "virtual-failure"), "--fault", "analyzer-timeout", expected=2)
            failed_virtual = json.loads((temp / "virtual-failure/failure.json").read_text(encoding="utf-8"))
            if (temp / "virtual-failure/result.json").exists() or failed_virtual["final_simulated_state"]["phone"]["tx"]:
                raise RuntimeError("Virtual failed run evidence/cleanup incorrect")
            # Test-only complete profiles; pre-cancelled installed CLI must never connect.
            from test_hardware_run import profiles_fixture, QUICK
            from dataclasses import asdict
            site = temp / "test-only-site"
            site.mkdir()
            for name, site_profile in profiles_fixture().items():
                (site / f"{name}.json").write_text(json.dumps(site_profile), encoding="utf-8")
            plan_file = temp / "test-only-plan.json"
            plan_file.write_text(json.dumps(asdict(QUICK)), encoding="utf-8")
            cancel_file = temp / "cancel"
            cancel_file.touch()
            preflight = json.loads(command("hardware-check", "--profiles-dir", str(site), "--plan", str(plan_file)).stdout)
            if not preflight["valid"] or preflight["connection_attempted"]:
                raise RuntimeError("Installed hardware preflight is not offline")
            cancelled_run = json.loads(command("hardware-run", "--profiles-dir", str(site), "--plan", str(plan_file),
                "--output-dir", str(temp / "hardware-cancelled"), "--cancel-file", str(cancel_file), expected=130).stdout)
            if cancelled_run["status"] != "cancelled": raise RuntimeError("Installed cancellation was not preserved")
            cancelled_report = json.loads((temp / "hardware-cancelled/failure.json").read_text(encoding="utf-8"))
            if cancelled_report["connection_attempted"]: raise RuntimeError("Pre-cancelled hardware run tried I/O")
            radios = json.loads(command("radio-list").stdout)
            if len(radios) != 4: raise RuntimeError("Installed radio catalog missing")
            radio_runs = []
            for radio in ("bluetooth", "cellular", "nfc", "uwb"):
                radio_plan = temp / f"{radio}-plan.json"
                command("radio-init", radio, "--output", str(radio_plan))
                command("radio-check", "--mode", "simulation", "--plan", str(radio_plan))
                destination = temp / f"radio-{radio}"
                answer = json.loads(command("radio-run", "--mode", "simulation", "--plan", str(radio_plan), "--output-dir", str(destination)).stdout)
                if answer["status"] != "completed" or answer["samples"] != 3 or not answer["simulated"]:
                    raise RuntimeError("Installed radio run invalid")
                for filename in ("phone-log.json", "phone-traffic.jsonl", "observations.jsonl", "samples.jsonl"):
                    if not (destination / filename).stat().st_size: raise RuntimeError("Radio evidence missing")
                radio_runs.append(answer)
            command("radio-run", "--mode", "simulation", "--plan", str(temp / "bluetooth-plan.json"),
                    "--output-dir", str(temp / "radio-stop-failure"), "--fault", "stop-timeout", expected=2)
            command("radio-run", "--mode", "simulation", "--plan", str(temp / "uwb-plan.json"),
                    "--output-dir", str(temp / "radio-cancel"), "--fault", "cancel-after-sample", expected=130)
            blocked_plan = json.loads((temp / "cellular-plan.json").read_text(encoding="utf-8"))
            blocked_plan.update(backend="direct_modem_tx", simulation_only=False, simulation=None)
            blocked_path = temp / "blocked-plan.json"
            blocked_path.write_text(json.dumps(blocked_plan), encoding="utf-8")
            command("radio-run", "--mode", "hardware", "--plan", str(blocked_path),
                    "--output-dir", str(temp / "radio-blocked"), expected=2)
            blocked_report = json.loads((temp / "radio-blocked/failure.json").read_text(encoding="utf-8"))
            if blocked_report["status"] != "blocked" or blocked_report["connection_attempted"]:
                raise RuntimeError("Unsupported radio attempted I/O")
            command("radio-profile", "nfc", "--output", str(temp / "nfc-profile.json"))
            report["radio_runs"] = radio_runs
            # Verify actual imported modules originate in the isolated target directory.
            proof = run([sys.executable, "-s", "-c", "import dgm_control,dgm_lab,dgm_rf,json; print(json.dumps([dgm_control.__file__,dgm_lab.__file__,dgm_rf.__file__]))"], cwd=temp, env=env)
            if not all(Path(name).resolve().is_relative_to(installed.resolve()) for name in json.loads(proof.stdout)):
                raise RuntimeError("Imports escaped isolated installation")
            report.update(wheels_built_installed=3, installed_cli_checks=checks, installed_import_origin_verified=True,
                          three_device_demo=passed, injected_failure_demo=failure, vendor_cache_excluded=True,
                          integrated_virtual_run=virtual, integrated_failure_status=failed_virtual["status"])
        report["passed"] = True
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        (SDK / "docs").mkdir(exist_ok=True)
        (SDK / "docs/validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {report['unit_tests']} SDK tests; 3 isolated wheels; {len(report['installed_cli_checks'])} CLI checks; hardware NOT RUN")


if __name__ == "__main__":
    main()
