"""Create and validate a portable, vendor-cache-free offline SDK bundle."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "libraries/device-control"


def run(argv, cwd, env=None):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{argv!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    validation = json.loads((SDK / "docs/validation.json").read_text(encoding="utf-8"))
    if not validation["passed"]: raise RuntimeError("Run check_device_control.py successfully first")
    version = tomllib.loads((SDK / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    target = SDK / "dist"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dgm-sdk-package-") as temporary:
        temp = Path(temporary)
        bundle = temp / "bundle"
        wheels = bundle / "wheels"
        wheels.mkdir(parents=True)
        for package in [ROOT / "libraries/phone-rf", ROOT / "libraries/lab-control", SDK]:
            run([sys.executable, "-m", "pip", "--disable-pip-version-check", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels), str(package)], ROOT)
        if len(list(wheels.glob("*.whl"))) != 3: raise RuntimeError("Expected three wheels")
        with zipfile.ZipFile(next(wheels.glob("dgm_device_control-*.whl"))) as wheel:
            if json.loads(wheel.read("dgm_control/data/catalog.json"))["sdk_version"] != version:
                raise RuntimeError("Wheel catalog and package versions disagree")
        shutil.copyfile(SDK / "scripts/install_sdk.py", bundle / "install.py")
        shutil.copyfile(SDK / "OFFLINE_INSTALL.md", bundle / "README.md")
        shutil.copyfile(SDK / "VIRTUAL_LAB.md", bundle / "VIRTUAL_LAB.md")
        shutil.copyfile(SDK / "HARDWARE_RUN.md", bundle / "HARDWARE_RUN.md")
        shutil.copyfile(SDK / "MULTIRADIO.md", bundle / "MULTIRADIO.md")
        shutil.copyfile(SDK / "RADIO_SCAN.md", bundle / "RADIO_SCAN.md")
        shutil.copyfile(SDK / "CORRECTIONS.md", bundle / "CORRECTIONS.md")
        shutil.copyfile(SDK / "DETECTORS.md", bundle / "DETECTORS.md")
        (bundle / "dgm_control/data").mkdir(parents=True)
        shutil.copyfile(SDK / "dgm_control/data/detector-sources.json", bundle / "dgm_control/data/detector-sources.json")
        # Exercise the bundle's real installer in an isolated virtual environment.
        environment = temp / "venv"
        run([sys.executable, "-m", "venv", str(environment)], temp)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        clean_env = dict(os.environ)
        clean_env.pop("PYTHONPATH", None)
        clean_env["PYTHONIOENCODING"] = "utf-8"
        run([str(python), str(bundle / "install.py")], bundle, clean_env)
        result = json.loads(run([str(python), "-m", "dgm_control", "demo", "--output-dir", str(temp / "demo")], temp, clean_env))
        if not result["simulated"] or not all(result["fixture_cleanup"].values()):
            raise RuntimeError("Offline bundle demo failed")
        virtual = json.loads(run([str(python), "-m", "dgm_control", "virtual-run", "--output-dir", str(temp / "virtual")], temp, clean_env))
        if virtual["samples"] != 12 or virtual["final_simulated_state"]["phone"]["tx"]:
            raise RuntimeError("Offline virtual lab failed")
        radio_runs = []
        for radio in ("bluetooth", "cellular", "nfc", "uwb"):
            plan = temp / f"{radio}.json"
            run([str(python), "-m", "dgm_control", "radio-init", radio, "--scan", "--output", str(plan)], temp, clean_env)
            evaluation = temp / f"{radio}-evaluation.json"
            run([str(python), "-m", "dgm_control", "evaluation-init", "--workflow", "radio", "--plan", str(plan), "--output", str(evaluation)], temp, clean_env)
            answer = json.loads(run([str(python), "-m", "dgm_control", "radio-run", "--mode", "simulation", "--plan", str(plan), "--evaluation", str(evaluation), "--output-dir", str(temp / radio)], temp, clean_env))
            if answer["status"] != "completed" or not answer["simulated"]: raise RuntimeError("Offline radio run failed")
            if answer["assessment"]["verdict"] != "PASS": raise RuntimeError("Offline corrected comparison failed")
            if answer["samples"] != 12 or answer["peak"]["angle_deg"] != 90 or answer["peak"]["height_cm"] != 200 or answer["peak"]["polarization"] != "V":
                raise RuntimeError("Offline facility scan peak failed")
            radio_runs.append(radio)
        receiver_runs = []
        for radio, detector in (("wlan", "LINEAR_AVER"), ("bluetooth", "CISPR_AVER"), ("cellular", "LINEAR_AVER"), ("nfc", "QP"), ("uwb", "CISPR_AVER")):
            base = [str(python), "-m", "dgm_control"]
            args = ["--workflow", "wlan"] if radio == "wlan" else ["--workflow", "radio", "--plan", str(temp / f"{radio}.json")]
            mpath, epath = temp / f"{radio}-receiver.json", temp / f"{radio}-receiver-eval.json"
            run([*base, "measurement-init", *args, "--detector", detector, "--output", str(mpath)], temp, clean_env)
            run([*base, "evaluation-init", *args, "--measurement", str(mpath), "--output", str(epath)], temp, clean_env)
            command = ["virtual-run"] if radio == "wlan" else ["radio-run", "--mode", "simulation", "--plan", str(temp / f"{radio}.json")]
            answer = json.loads(run([*base, *command, "--measurement", str(mpath), "--evaluation", str(epath),
                                     "--output-dir", str(temp / f"{radio}-receiver")], temp, clean_env))
            if answer["status"] != "completed" or answer["assessment"]["verdict"] != "PASS":
                raise RuntimeError("Offline receiver-grid comparison failed")
            receiver_runs.append(dict(radio=radio, detector=detector, samples=answer["samples"], verdict="PASS"))
        archive = target / f"dgm-device-control-{version}-offline.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for path in sorted(bundle.rglob("*")):
                if path.is_file(): output.write(path, path.relative_to(bundle))
        with zipfile.ZipFile(archive) as check:
            if check.testzip() is not None: raise RuntimeError("ZIP integrity check failed")
        report = {"file": archive.name, "bytes": archive.stat().st_size, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                  "wheels": [path.name for path in sorted(wheels.glob("*.whl"))], "offline_installer_tested": True,
                  "fresh_venv_demo_passed": True, "fresh_venv_virtual_lab_passed": True,
                  "fresh_venv_radio_scans_passed": radio_runs, "radio_scan_samples_each": 12, "hardware_tests": 0}
        report["fresh_venv_corrected_radio_comparisons_passed"] = radio_runs
        report["fresh_venv_receiver_comparisons"] = receiver_runs
        (target / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (SDK / "docs/distribution-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
