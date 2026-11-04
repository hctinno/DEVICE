"""Numerical and native-peer correction/decision evidence. Never physical I/O."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dgm_control import WlanScan, run_hardware, run_radio
from dgm_control.evaluation import Evaluation, evaluation_template, CONVERSION_50_OHM, assessment_exit, interpolate
from dgm_control.virtual_recipe import run_virtual
from dgm_control.virtual_world import Fault
from test_radio_scan import quick, scan_hardware
from test_radios import hardware_peers, read
from test_hardware_run import QUICK, peers, profiles_fixture


def commissioned_fixture(config):
    """TEST ONLY declarations to exercise real adapter paths against native peers."""
    result = deepcopy(config)
    result["simulation_only"] = False
    result["setup"].update(site_verified=True, evidence_notes="TEST ONLY native protocol peer")
    result["criterion"]["provenance"] = "declared_standard"
    for path in result["paths"].values():
        for pol in path.values():
            for table in pol.values():
                if table: table.update(provenance="calibration_certificate", source_sha256="a"*64)
    return result


def sample(engine, value=-20, index=0):
    sweep = engine.sweep
    return {"index": index, "height_cm": 100, "angle_deg": 0, "polarization": "H", "rf_path": "dut",
            "trace": {"settings": deepcopy(sweep), "utc": datetime.now(timezone.utc).isoformat(),
                      "frequencies_hz": [sweep["start_hz"]+i*(sweep["stop_hz"]-sweep["start_hz"])/100 for i in range(101)],
                      "values_dbm": [value]*101}}


class NumericalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.plan = quick("bluetooth")
        self.config = evaluation_template(self.plan)

    def engine(self, config=None): return Evaluation(config or self.config, self.plan, simulated=True)

    def test_conversion_and_component_signs(self):
        for points in self.config["paths"]["dut"]["H"]["preamp_gain"]["points"]: points[1] = 10
        engine = self.engine(); row = sample(engine)
        result = engine.correct(row)
        self.assertAlmostEqual(CONVERSION_50_OHM, 106.98970004336019)
        self.assertAlmostEqual(result["peak"]["field_dbuv_m"], 99.98970004336019)
        self.assertEqual(row["trace"]["values_dbm"], [-20]*101)
        self.assertEqual(engine.summary(completed=True)["verdict"], "PASS")

    def test_interpolation_linear_log_and_no_extrapolation(self):
        self.assertEqual(interpolate(50, 10, 0, 100, 9, "linear_hz"), 4)
        self.assertAlmostEqual(interpolate(100, 10, 0, 1000, 20, "linear_log_hz"), 10)
        with self.assertRaises(ValueError): interpolate(1001, 10, 0, 1000, 20, "linear_log_hz")

    def test_corrected_peak_bin_changes(self):
        self.config["paths"]["dut"]["H"]["antenna_factor"]["points"][1][1] = 60
        engine = self.engine(); row = sample(engine)
        row["trace"]["values_dbm"][0] = 0
        result = engine.correct(row)
        self.assertEqual(result["peak"]["bin"], 100)
        self.assertEqual(row["trace"]["values_dbm"].index(max(row["trace"]["values_dbm"])), 0)

    def test_worst_margin_differs_from_maximum_field(self):
        s = self.config["criterion"]["segments"][0]
        s.update(start_dbuv_m=110, stop_dbuv_m=180, interpolation="linear_hz")
        engine = self.engine(); row = sample(engine)
        row["trace"]["values_dbm"][-1] = 0
        engine.correct(row); report = engine.summary(completed=True)
        self.assertEqual(report["maximum_field"]["bin"], 100)
        self.assertEqual(report["worst_margin"]["bin"], 0)

    def test_simple_and_guarded_boundaries_unrounded(self):
        threshold = -20 + CONVERSION_50_OHM + 23
        for rule, uncertainty, delta, expected in (("simple", 0, 0, "PASS"), ("simple", 0, -1e-9, "FAIL"),
                ("guarded", 2, 2, "PASS"), ("guarded", 2, -2, "INDETERMINATE"),
                ("guarded", 2, -2.001, "FAIL"), ("guarded", 2, 0, "INDETERMINATE")):
            with self.subTest(rule=rule, delta=delta):
                self.config["decision"].update(rule=rule, expanded_uncertainty_db=uncertainty)
                self.config["criterion"]["segments"][0].update(start_dbuv_m=threshold+delta, stop_dbuv_m=threshold+delta)
                engine = self.engine(); engine.correct(sample(engine))
                self.assertEqual(engine.summary(completed=True)["verdict"], expected)

    def test_shared_limit_boundary_uses_strictest(self):
        seg = self.config["criterion"]["segments"][0]
        middle = (seg["start_hz"]+seg["stop_hz"])/2
        self.config["criterion"]["segments"] = [{**seg, "stop_hz": middle},
            {**seg, "start_hz": middle, "start_dbuv_m": 100, "stop_dbuv_m": 100}]
        engine = self.engine(); result = engine.correct(sample(engine))
        self.assertEqual(result["bins"][50]["limit_dbuv_m"], 100)
        self.assertEqual(engine.summary(completed=True)["verdict"], "FAIL")

    def test_unsupported_conditions_never_pass(self):
        for change in ({"detector": "QP"}, {"detector": "AVER"}, {"rbw_hz": 100}, {"vbw_hz": 100},
                       {"distance_m": 10}, {"minimum_sweep_seconds": 100}):
            cfg = deepcopy(self.config); cfg["criterion"].update(change)
            engine = self.engine(cfg); engine.correct(sample(engine))
            self.assertEqual(engine.summary(completed=True)["verdict"], "NOT_EVALUATED")

    def test_limit_gap_even_between_bins_blocks_pass(self):
        seg = self.config["criterion"]["segments"][0]
        lo, hi = seg["start_hz"], seg["stop_hz"]
        self.config["criterion"]["segments"] = [{**seg, "stop_hz": lo+(hi-lo)*.501}, {**seg, "start_hz": lo+(hi-lo)*.502}]
        engine = self.engine(); engine.correct(sample(engine))
        self.assertEqual(engine.summary(completed=True)["verdict"], "NOT_EVALUATED")

    def test_absent_limit_bins_preserved_and_not_evaluated(self):
        self.config["criterion"]["segments"][0]["start_hz"] += 1
        engine = self.engine(); result = engine.correct(sample(engine))
        self.assertIsNone(result["bins"][0]["margin_db"])
        self.assertEqual(engine.summary(completed=True)["verdict"], "NOT_EVALUATED")

    def test_overlapping_limits_rejected(self):
        self.config["criterion"]["segments"].append(deepcopy(self.config["criterion"]["segments"][0]))
        with self.assertRaises(ValueError): self.engine()

    def test_bad_calibration_date_units_and_coverage_rejected(self):
        for change in ({"valid_until": "1999-01-01"}, {"valid_from": "2100-01-01"}, {"unit": "dB"},
                       {"points": [[1, 0], [2, 0]]}, {"points": [[1, 0], [1, 0]]}, {"source_sha256": "bad"},
                       {"interpolation": "guess"}, {"points": [[1, float("nan")], [10e9, 0]]}):
            cfg = deepcopy(self.config); cfg["paths"]["dut"]["H"]["antenna_factor"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.engine(cfg)

    def test_missing_path_polarization_and_unknown_fields_rejected(self):
        for field in ("dut",):
            cfg = deepcopy(self.config); cfg["paths"].pop(field)
            with self.assertRaises(ValueError): self.engine(cfg)
        cfg = deepcopy(self.config); cfg["paths"]["dut"].pop("V")
        with self.assertRaises(ValueError): self.engine(cfg)
        cfg = deepcopy(self.config); cfg["typo"] = 1
        with self.assertRaises(ValueError): self.engine(cfg)

    def test_hardware_synthetic_block_and_snapshot_hash(self):
        cfg = deepcopy(self.config)
        with self.assertRaises(ValueError): Evaluation(cfg, self.plan, simulated=False)
        cfg["simulation_only"] = False; cfg["setup"]["site_verified"] = True
        with self.assertRaises(ValueError): Evaluation(cfg, self.plan, simulated=False)
        engine = self.engine(); old = engine.sha256
        self.config["setup"]["distance_m"] = 9
        self.assertEqual(engine.config["setup"]["distance_m"], 3)
        self.assertNotEqual(self.engine().sha256, old)

    def test_bad_trace_grid_settings_nan_and_acquisition_date(self):
        engine = self.engine()
        for mutation in (lambda r: r["trace"]["settings"].update(rbw_hz=10),
                         lambda r: r["trace"]["values_dbm"].pop(),
                         lambda r: r["trace"]["values_dbm"].__setitem__(0, float("nan")),
                         lambda r: r["trace"]["frequencies_hz"].__setitem__(50, 3),
                         lambda r: r["trace"].update(utc="1990-01-01T00:00:00+00:00")):
            row = sample(engine); mutation(row)
            with self.assertRaises(ValueError): engine.correct(row)

    def test_failure_and_empty_never_pass(self):
        engine = self.engine()
        self.assertEqual(engine.summary(completed=True)["verdict"], "NOT_EVALUATED")
        engine.correct(sample(engine))
        self.assertEqual(engine.summary(completed=False)["verdict"], "NOT_EVALUATED")

    def test_exit_codes(self):
        for verdict, code in (("PASS", 0), ("FAIL", 4), ("INDETERMINATE", 5), ("NOT_EVALUATED", 3)):
            self.assertEqual(assessment_exit({"status": "completed", "assessment": {"verdict": verdict}}), code)
        self.assertEqual(assessment_exit({"status": "cancelled"}), 130)
        self.assertEqual(assessment_exit({"status": "failed"}), 2)

    def test_bind_blocks_mode_plan_and_engine_reuse(self):
        engine = self.engine()
        with self.assertRaises(ValueError): engine.bind(self.plan, False)
        other = deepcopy(self.plan); other["sweep"]["rbw_hz"] = 10
        with self.assertRaises(ValueError): engine.bind(other, True)
        engine.correct(sample(engine))
        with self.assertRaises(ValueError): engine.bind(self.plan, True)

    def test_no_preamp_and_no_magnetic_or_double_correction(self):
        self.config["paths"]["dut"]["H"]["preamp_gain"] = None
        engine = self.engine()
        self.assertEqual(engine.correct(sample(engine))["peak"]["components"]["preamp_gain"], 0)
        for change in ({"unit": "dBuA/m"}, {"quantity": "magnetic_field"}, {"impedance_ohm": 75},
                       {"receiver_corrections_disabled": False}):
            cfg = deepcopy(self.config); cfg["setup"].update(change)
            with self.assertRaises(ValueError): self.engine(cfg)


class EvaluationWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name)

    def test_all_radios_corrected_h_peak_overrides_raw_v_peak(self):
        for radio in ("bluetooth", "cellular", "nfc", "uwb"):
            plan = quick(radio); cfg = evaluation_template(plan)
            for point in cfg["paths"]["dut"]["H"]["antenna_factor"]["points"]: point[1] = 40
            folder = self.root / radio
            answer = run_radio(plan, "simulation", folder, evaluation=cfg)
            self.assertEqual(answer["status"], "completed", answer)
            self.assertEqual(answer["peak"]["polarization"], "H")
            result = read(folder / "result.json")
            self.assertEqual(result["assessment"]["maximum_field"]["polarization"], "H")
            self.assertEqual(result["measurement"]["peak_return_readback"]["positions"][0]["polarization"], "PH")
            self.assertIsNone(result["fcc_verdict"])
            self.assertEqual(read(folder / "inputs.json")["evaluation"], cfg)
            row = json.loads((folder / "samples.jsonl").read_text().splitlines()[0])
            self.assertEqual(len(row["evaluation"]["bins"]), 101)
            self.assertEqual(row["evaluation"]["config_sha256"], result["assessment"]["config_sha256"])

    def test_path_correction_changes_maximum_route(self):
        plan = quick("bluetooth")
        plan["scan"]["rf_paths"].append("generator")
        plan["scan"]["path_frequency_limits_hz"]["generator"] = [0, 50e9]
        plan["scan"]["simulation"]["route_loss_db"] = {"dut": 10, "generator": 0}
        cfg = evaluation_template(plan)
        for pol in cfg["paths"]["dut"].values():
            for point in pol["switch_loss"]["points"]: point[1] = 21
        answer = run_radio(plan, "simulation", self.root / "paths", evaluation=cfg)
        self.assertEqual(answer["status"], "completed", answer)
        self.assertEqual(answer["peak"]["rf_path"], "dut")

    def test_all_four_native_hardware_paths_persist_assessment(self):
        for radio in ("bluetooth", "cellular", "nfc", "uwb"):
            plan, profiles, synthetic = scan_hardware(radio)
            cfg = commissioned_fixture(evaluation_template(plan))
            with hardware_peers(synthetic):
                answer = run_radio(plan, "hardware", self.root / radio, profiles=profiles, evaluation=cfg)
            self.assertEqual(answer["status"], "completed", answer)
            self.assertFalse(answer["assessment"]["simulated"])
            self.assertFalse(answer["physical_verified"])

    def test_radio_stop_cancel_and_recording_failures_never_final_pass(self):
        plan = quick("bluetooth"); cfg = evaluation_template(plan)
        for fault in ("stop-timeout", "cancel-after-sample", "switch-timeout"):
            answer = run_radio(plan, "simulation", self.root / fault, evaluation=cfg, fault=fault)
            self.assertIn(answer["status"], ("failed", "cancelled"))
            self.assertEqual(answer["assessment"]["verdict"], "NOT_EVALUATED")
            self.assertFalse((self.root / fault / "result.json").exists())
        from dgm_control.hardware_run import RunEvidence
        with patch.object(RunEvidence, "sample", side_effect=OSError("test disk failure")):
            answer = run_radio(plan, "simulation", self.root / "disk", evaluation=cfg)
        self.assertEqual(answer["assessment"]["verdict"], "NOT_EVALUATED")

    def test_hardware_synthetic_fails_before_connection_with_logs(self):
        plan, profiles, _ = scan_hardware("bluetooth")
        answer = run_radio(plan, "hardware", self.root / "blocked", profiles=profiles, evaluation=evaluation_template(plan))
        self.assertEqual(answer["status"], "failed")
        self.assertFalse(read(self.root / "blocked/failure.json")["connection_attempted"])
        self.assertEqual(answer["assessment"]["verdict"], "NOT_EVALUATED")

    def test_wlan_virtual_corrected_ranking_and_return(self):
        plan = WlanScan(heights_cm=(100,), angles_deg=(0,), polarizations=("H", "V"))
        cfg = evaluation_template(plan)
        for point in cfg["paths"]["dut"]["H"]["antenna_factor"]["points"]: point[1] = 60
        answer = run_virtual(self.root / "wlan", plan=plan, evaluation=cfg)
        self.assertEqual(answer["peak"]["polarization"], "H")
        result = read(self.root / "wlan/result.json")
        self.assertEqual(result["measurement"]["peak_return_readback"][0]["polarization"], "PH")
        self.assertEqual(result["evaluation_input"], cfg)

    def test_wlan_hardware_evaluation_and_failure(self):
        cfg = commissioned_fixture(evaluation_template(QUICK))
        with peers(): answer = run_hardware(profiles_fixture(), QUICK, self.root / "ok", evaluation=cfg)
        self.assertEqual(answer["status"], "completed", answer)
        self.assertIn(answer["assessment"]["verdict"], ("PASS", "FAIL"))
        with peers(Fault("PhoneAt", "AT+WIFITEST=0,2,0,0")):
            answer = run_hardware(profiles_fixture(), QUICK, self.root / "failed", evaluation=cfg)
        self.assertEqual(answer["status"], "failed")
        self.assertEqual(answer["assessment"]["verdict"], "NOT_EVALUATED")

    def test_wlan_virtual_failure_preserves_incomplete_assessment(self):
        with self.assertRaises(Exception):
            run_virtual(self.root / "fail", plan=QUICK, evaluation=evaluation_template(QUICK),
                        fault=Fault("PhoneAt", "AT+WIFITEST=0,2,0,0"))
        self.assertEqual(read(self.root / "fail/failure.json")["assessment"]["verdict"], "NOT_EVALUATED")

    def test_final_result_storage_failure_downgrades_verdict(self):
        from dgm_control.hardware_run import atomic_json
        def failing_result(path, value):
            if path.name == "result.json": raise OSError("test final report storage failure")
            return atomic_json(path, value)
        plan = quick("bluetooth")
        with patch("dgm_control.radio_run.atomic_json", side_effect=failing_result):
            answer = run_radio(plan, "simulation", self.root / "radio", evaluation=evaluation_template(plan))
        self.assertEqual(answer["status"], "failed")
        self.assertEqual(answer["assessment"]["verdict"], "NOT_EVALUATED")
        with patch("dgm_control.hardware_run.atomic_json", side_effect=failing_result), self.assertRaises(OSError):
            run_virtual(self.root / "wlan", plan=QUICK, evaluation=evaluation_template(QUICK))
        self.assertEqual(read(self.root / "wlan/failure.json")["assessment"]["verdict"], "NOT_EVALUATED")
        self.assertFalse((self.root / "wlan/result.json").exists())


if __name__ == "__main__": unittest.main()
