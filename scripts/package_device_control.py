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
    target = SDK / "dist"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dgm-sdk-package-") as temporary:
        temp = Path(temporary)
        bundle = temp / "bundle"
        wheels = bundle / "wheels"
        wheels.mkdir(parents=True)
        for package in [ROOT / "libraries/samsung-rf", ROOT / "libraries/lab-control", SDK]:
            run([sys.executable, "-m", "pip", "--disable-pip-version-check", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels), str(package)], ROOT)
        if len(list(wheels.glob("*.whl"))) != 3: raise RuntimeError("Expected three wheels")
        shutil.copyfile(SDK / "scripts/install_sdk.py", bundle / "install.py")
        shutil.copyfile(SDK / "OFFLINE_INSTALL.md", bundle / "README.md")
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
        version = tomllib.loads((SDK / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        archive = target / f"dgm-device-control-{version}-offline.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for path in sorted(bundle.rglob("*")):
                if path.is_file(): output.write(path, path.relative_to(bundle))
        with zipfile.ZipFile(archive) as check:
            if check.testzip() is not None: raise RuntimeError("ZIP integrity check failed")
        report = {"file": archive.name, "bytes": archive.stat().st_size, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                  "wheels": [path.name for path in sorted(wheels.glob("*.whl"))], "offline_installer_tested": True,
                  "fresh_venv_demo_passed": True, "hardware_tests": 0}
        (target / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (SDK / "docs/distribution-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
