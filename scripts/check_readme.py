"""Exercise README onboarding with installed packages; never connect to hardware.

Run with the newly installed virtualenv Python. Kept separate from driver tests:
this checks the public reader path, result artifacts and executable doc examples.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--report", help="Optional portable validation summary JSON")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = Path(args.output_dir or ROOT / "runs" / f"readme-check-{stamp}").resolve()
    target.mkdir(parents=True, exist_ok=False)
    report = {"passed": False, "utc": stamp, "python": sys.version,
              "commands": [], "physical_connections": 0,
              "skipped": ["Hardware code execution", "VISA/serial runtime and devices",
                          "Physical RF/motion and FCC conformity", "Linux/macOS execution"]}
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("PYTHONPATH", None)  # package must come from this interpreter's installation

    def run(arguments, expected=0):
        process = subprocess.run([sys.executable, "-I", "-X", "utf8", *arguments], cwd=target,
                                 env=env, capture_output=True, text=True,
                                 encoding="utf-8", timeout=120)
        index = len(report["commands"])
        (target / f"command-{index:02d}.log").write_text(
            process.stdout + "\nSTDERR:\n" + process.stderr, encoding="utf-8")
        report["commands"].append({"arguments": arguments, "exit_code": process.returncode,
                                   "expected": expected})
        if process.returncode != expected:
            raise RuntimeError(f"Unexpected exit {process.returncode}: {arguments}\n{process.stderr}")
        return process.stdout

    def cli(*arguments, expected=0):
        return run(["-m", "dgm_control", *arguments], expected)

    try:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```python\r?\n(.*?)```", readme, re.S)
        examples = {}
        for block in blocks:
            marker = re.search(r"^# readme-example: ([\w-]+)$", block, re.M)
            if not marker:
                raise ValueError("Every Python example needs an explicit execution classification")
            name = marker[1]
            compile(block, f"README:{name}", "exec")
            if name in examples:
                raise ValueError(f"Duplicate example: {name}")
            examples[name] = block
        if set(examples) != {"virtual", "connect-analyzer", "prepare-hardware"}:
            raise ValueError("Review execution policy for changed README examples")
        report["compiled_examples"] = sorted(examples)
        # Only the explicitly virtual example is executed. Hardware snippets are syntax-only.
        example = target / "virtual_example.py"
        example.write_text(examples["virtual"], encoding="utf-8")

        diagnosed = json.loads(cli("doctor"))
        expected_versions = {"dgm-device-control": "0.5.0", "dgm-lab-control": "0.4.0",
                             "dgm-rf-command-library": "0.5.0"}
        if diagnosed["packages"] != expected_versions or not diagnosed["supported_python"]:
            raise ValueError(f"Install README package versions first: {diagnosed['packages']}")
        report["packages"] = diagnosed["packages"]
        assert len(json.loads(cli("list"))) == 21
        for name in ("SpectrumAnalyzer", "Co3000", "PhoneAt"):
            assert json.loads(cli("show", name))["id"] == name
        assert len(json.loads(cli("virtual-info"))["models"]) == 7
        hardware = target / "analyzer-template.json"
        init = json.loads(cli("init", "SpectrumAnalyzer", "--mode", "hardware", "--output", str(hardware)))
        assert init["connection_attempted"] is False and init["check"]["valid"] is False
        assert json.loads(cli("check", str(hardware), expected=2))["valid"] is False
        before = hardware.read_bytes()
        cli("init", "SpectrumAnalyzer", "--output", str(hardware), expected=2)
        assert hardware.read_bytes() == before

        json_blocks = re.findall(r"```json\r?\n(.*?)```", readme, re.S)
        assert len(json_blocks) == 1
        profile = json.loads(json_blocks[0])
        example_profile = target / "analyzer-example.json"
        example_profile.write_text(json.dumps(profile), encoding="utf-8")
        assert json.loads(cli("check", str(example_profile), expected=2))["valid"] is False
        # Offline structural validation ONLY; never open this loopback address.
        profile["config"]["transport"]["host"] = "127.0.0.1"
        example_profile.write_text(json.dumps(profile), encoding="utf-8")
        check = json.loads(cli("check", str(example_profile)))
        assert check["valid"] is True and check["connection_attempted"] is False

        passed = json.loads(cli("virtual-run", "--output-dir", "virtual-001"))
        assert passed["status"] == "completed" and passed["samples"] == 12
        assert passed["peak"]["height_cm"] == 200 and passed["peak"]["angle_deg"] == 90
        assert passed["peak"]["polarization"] == "V" and abs(passed["peak"]["power_dbm"] + 20) < 0.01
        success = target / "virtual-001"
        result = json.loads((success / "result.json").read_text(encoding="utf-8"))
        assert result["simulated"] is True and result["physical_verified"] is False
        assert result["fcc_verdict"] is None and result["cleanup_scope_succeeded"] is True
        assert result["remaining_connections"] == []
        state = result["final_simulated_state"]
        assert state["phone"]["tx"] is False and state["supply"]["output"] is False
        assert state["motion"]["moving"] is False and state["route"] == "isolated"
        assert len((success / "samples.jsonl").read_text(encoding="utf-8").splitlines()) == 12
        for filename in ("traffic.jsonl", "observations.json"):
            assert (success / filename).stat().st_size > 0
        cli("virtual-run", "--output-dir", "virtual-001", expected=2)
        cli("virtual-run", "--output-dir", "failed-001", "--fault", "analyzer-timeout", expected=2)
        failed = target / "failed-001"
        failure = json.loads((failed / "failure.json").read_text(encoding="utf-8"))
        assert failure["status"] == "failed" and not (failed / "result.json").exists()
        assert (failed / "traffic.jsonl").stat().st_size > 0
        assert len(json.loads(cli("radio-list"))) == 4
        for radio in ("bluetooth", "cellular", "nfc", "uwb"):
            plan_path = target / f"{radio}-plan.json"
            cli("radio-init", radio, "--output", str(plan_path))
            assert json.loads(cli("radio-check", "--mode", "simulation", "--plan", str(plan_path)))["valid"]
            destination = target / f"radio-{radio}"
            answer = json.loads(cli("radio-run", "--mode", "simulation", "--plan", str(plan_path), "--output-dir", str(destination)))
            assert answer["status"] == "completed" and answer["samples"] == 3 and answer["simulated"]
            assert (destination / "phone-traffic.jsonl").stat().st_size > 0
        run([str(example)])
        report["passed"] = True
        print(f"PASS: {len(report['commands'])} installed-package commands; 3 compiled README examples; no hardware I/O")
    except BaseException as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        destination = target / "validation.json"
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.report:
            portable = json.dumps(report, ensure_ascii=False, indent=2)
            portable = portable.replace(json.dumps(str(target))[1:-1], "<run-dir>")
            Path(args.report).write_text(portable + "\n", encoding="utf-8")
        print(f"Evidence: {destination}")


if __name__ == "__main__":
    main()
