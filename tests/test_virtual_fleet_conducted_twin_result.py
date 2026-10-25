"""Genuine synthetic plan/setup/journal/report; no provider or hardware."""
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input
from labflow.intake_jobs import _analysis_contract
from labflow.store import canonical
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.evaluation import prepare_sensor_trial
from labflow.virtual_fleet.harness import FleetHarness
from labflow.virtual_fleet.integration import get_role_actions
from labflow.virtual_fleet.journal import OperatorJournal, read_operator_journal
from labflow.virtual_fleet.policies import RFSensorFixturePolicy


ROOT = Path(__file__).resolve().parents[1]


def sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def plan_fixture(power=-7, metric="on"):
    text = "product_type: test_radio\npurpose: engineering review\nmarket: EU\n"
    document = dict(path="request.txt", sha256=hashlib.sha256(text.encode()).hexdigest(),
                    bytes=len(text.encode()), text=text, parse_status="text", format="text",
                    extraction_status="ok", issues=[])
    context_id = hashlib.sha256(b"authored result context").hexdigest()
    context = dict(job_id="J-RESULT-SYN", intake_id="I-RESULT-SYN", revision=1, synthetic=True,
                   documents=[document], analysis_context_id=context_id,
                   analysis_contract=_analysis_contract(dict(documents=[document], context_id=context_id)),
                   instructions="Authored synthetic input; no operational authority.")
    facts = []
    for line, field, value in ((1, "product_type", "test_radio"),
                               (2, "purpose", "engineering review"), (3, "market", "EU")):
        ref = dict(path=document["path"], sha256=document["sha256"], line_start=line, line_end=line,
                   quote=text.splitlines()[line - 1], role="request")
        facts.append(dict(field=field, value=value, status="explicit", evidence=[ref]))
    analysis = dict(schema_version=1, producer=dict(kind="fixture", name="RESULT-SYN"),
                    identity="single", facts=facts, missing_fields=[])
    settings = dict(frequency_hz=2412000000, power_dbm=power, bandwidth_hz=20000000,
                    duty_cycle=.5, modulation="OFDM", crest_factor_db=4)
    units = dict(frequency_hz="Hz", power_dbm="dBm", bandwidth_hz="Hz",
                 duty_cycle="ratio", modulation="label", crest_factor_db="dB")
    basis = {key: dict(kind="developer_declared_synthetic", value=value, unit=units[key], evidence=[])
             for key, value in settings.items()}
    options = dict(expected_revision=1, expected_context_sha256=sha(context), source_settings=settings,
                   basis=basis, method=dict(method_id="conducted_synthetic", method_version=1,
                                            metric=metric, reference_plane="source_output"))
    return context, analysis, options


class ConductedTwinResultTests(unittest.TestCase):
    def module(self):
        name = "labflow.virtual_fleet.conducted_twin_result"
        self.assertIsNotNone(importlib.util.find_spec(name), "pure result builder is absent")
        return importlib.import_module(name)

    def genuine(self, *, power=-7, metric="on", quantity=True, condition="normal", policy=None):
        context, analysis, options = plan_fixture(power, metric)
        plan = build_conducted_twin_plan_input(context, analysis, **options)
        self.assertEqual(plan["status"], "ready_for_simulation")
        catalog = load_catalog(ROOT / "virtual_profiles/sm_a176u_unlicensed.json")
        records = []
        trial = prepare_sensor_trial(catalog, condition=condition, power_dbm=power,
                                     source_settings=options["source_settings"], setup_records=records)
        setup = trial.setup_snapshot()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "events.jsonl"
        provenance = dict(runtime_origin="preinitialized", catalog_sha256=sha(catalog),
                          topology_sha256=sha(trial.topology),
                          engine_sha256=hashlib.sha256((ROOT / "labflow/virtual_fleet/rf.py").read_bytes()).hexdigest(),
                          topology=trial.topology, plan_binding=plan["binding"], setup_sha256=sha(setup))
        if quantity:
            provenance["quantity"] = dict(metric="on", reference_plane="sensor_input",
                                          loss_compensation_applied=False, loss_compensation_sign=1)
        with OperatorJournal(path, run_id="result-run", runtime_instance_id=trial.runtime_instance_id,
                             provenance=provenance) as writer:
            harness = FleetHarness(trial.runtime, policy or RFSensorFixturePolicy(), goal=trial.goal,
                                   catalog=catalog, topology=trial.topology, role_actions=get_role_actions(),
                                   event_sink=writer, run_id="result-run", runtime_instance_id=trial.runtime_instance_id)
            report = harness.run()
        stored = read_operator_journal(path)
        refs = report["evidence"]["measurement_refs"]
        observations = [e for e in stored["events"] if e["type"] == "observation"]
        ref = refs[-1] if refs else observations[-1]["event_id"]
        return [plan, setup, stored, report], ref

    def repack(self, stored, change):
        value = deepcopy(stored)
        change(value)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "negative-events.jsonl"
        with OperatorJournal(path, run_id=value["header"]["run_id"],
                             runtime_instance_id=value["header"]["runtime_instance_id"],
                             provenance=value["header"]["provenance"]) as writer:
            for event in value["events"]:
                writer(event)
        return read_operator_journal(path)

    def build(self, args, ref):
        return self.module().build_conducted_twin_result(*args, measurement_ref=ref)

    def codes(self, result):
        return {gap["code"] for gap in result["gaps"]}

    def packet(self, args, ref):
        event = next(e for e in args[2]["events"] if e["event_id"] == ref)
        return event["payload"]["observation"]["devices"]["sensor"]["values"]["outputs"].get("measurement")

    def test_genuine_raw_and_correction_match_independent_decimal_arithmetic(self):
        args, ref = self.genuine()
        original = deepcopy(args)
        result = self.build(args, ref)
        self.assertEqual(set(result), {"schema_version", "kind", "status", "binding", "raw_measurement",
                         "setup_provenance", "calculation", "gaps", "failure", "verification"})
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["raw_measurement"]["packet"], self.packet(args, ref))
        self.assertEqual(result["binding"]["run_report"], args[3])
        self.assertEqual(result["binding"]["plan_input"], args[0])
        configured = {(r["device_id"], r["action"]): r["parameters"]
                      for r in args[1] if r["operation"] == "execute"}
        with localcontext() as ctx:
            ctx.prec = 50
            raw = Decimal(str(self.packet(args, ref)["value"]))
            target = (raw + Decimal(str(configured["attenuator", "configure"]["attenuation_db"]))
                      + Decimal(str(configured["switch", "configure"]["loss_db"]))
                      + Decimal(str(configured["coupler", "configure"]["coupling_db"])))
            watts = Decimal(10) ** ((raw - Decimal(30)) / Decimal(10))
            corrected_watts = Decimal(10) ** ((target - Decimal(30)) / Decimal(10))
        self.assertAlmostEqual(result["calculation"]["raw_power_w"]["value"], float(watts), delta=float(watts)*1e-12)
        self.assertAlmostEqual(result["calculation"]["corrected"]["value"], float(target), places=9)
        self.assertAlmostEqual(result["calculation"]["corrected"]["power_w"], float(corrected_watts),
                               delta=float(corrected_watts)*1e-12)
        self.assertEqual([r["setting"] for r in result["calculation"]["correction_ledger"]],
                         ["attenuation_db", "loss_db", "coupling_db"])
        self.assertEqual(result["calculation"]["conformity"],
                         dict(status="not_assessed", verdict=None, numeric_limit_dbm=None, uncertainty_db=None))
        self.assertEqual(args, original)
        self.assertFalse(result["verification"]["execution_authority"])

    def test_existing_calculator_is_used_for_raw_and_target_and_inputs_are_detached(self):
        args, ref = self.genuine()
        from labflow.calculations import calculate
        module = self.module()
        with patch.object(module, "calculate", wraps=calculate) as calculator:
            result = self.build(args, ref)
        self.assertEqual([call.args[0] for call in calculator.call_args_list], ["rf_power", "rf_power"])
        self.assertEqual(calculator.call_args_list[0].args[1]["reading"], self.packet(args, ref)["value"])
        self.assertEqual(result, self.build(args, ref))
        result["binding"]["run_report"]["termination"]["reason"] = "caller edit"
        result["setup_provenance"]["records"][0]["parameters"]["caller"] = True
        self.assertNotEqual(result, self.build(args, ref))

    def test_actual_three_db_change_changes_raw_and_target_without_using_plan_as_measurement(self):
        low, low_ref = self.genuine(power=-7)
        high, high_ref = self.genuine(power=-4)
        a, b = self.build(low, low_ref), self.build(high, high_ref)
        self.assertAlmostEqual(b["raw_measurement"]["packet"]["value"] - a["raw_measurement"]["packet"]["value"], 3)
        self.assertAlmostEqual(b["calculation"]["corrected"]["value"] - a["calculation"]["corrected"]["value"], 3)
        self.assertAlmostEqual(b["calculation"]["raw_power_w"]["value"] / a["calculation"]["raw_power_w"]["value"],
                               float(Decimal(10) ** (Decimal(3)/Decimal(10))), places=10)

    def test_missing_quantity_preserves_raw_conversion_but_not_target_correction(self):
        args, ref = self.genuine(quantity=False)
        result = self.build(args, ref)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["raw_measurement"]["packet"], self.packet(args, ref))
        self.assertIsNotNone(result["calculation"]["raw_power_w"])
        self.assertIsNone(result["calculation"]["corrected"])
        self.assertIn("correction_basis_missing", self.codes(result))

    def test_wrong_plane_metric_sign_and_already_applied_never_add_loss(self):
        original, ref = self.genuine()
        for key, value in (("reference_plane", "source_output"), ("metric", "peak"),
                           ("loss_compensation_sign", -1), ("loss_compensation_sign", True),
                           ("loss_compensation_applied", 0), ("loss_compensation_applied", True)):
            args = deepcopy(original)
            args[2] = self.repack(args[2], lambda s: s["header"]["provenance"]["quantity"].update({key: value}))
            with self.subTest(key=key, value=value):
                result = self.build(args, ref)
                self.assertEqual(result["status"], "incomplete")
                self.assertIsNone(result["calculation"]["corrected"])
                self.assertEqual(result["calculation"]["correction_ledger"], [])
                self.assertIsNotNone(result["calculation"]["raw_power_w"])

    def test_time_or_peak_plan_does_not_transform_on_average_packet(self):
        for metric in ("time", "peak"):
            args, ref = self.genuine(metric=metric)
            result = self.build(args, ref)
            self.assertEqual(result["status"], "incomplete")
            self.assertIsNone(result["calculation"]["corrected"])
            self.assertIn("metric_mismatch", self.codes(result))
            self.assertEqual(result["raw_measurement"]["packet"], self.packet(args, ref))

    def test_original_D1_blocking_gaps_and_null_settings_are_preserved(self):
        args, ref = self.genuine()
        context, analysis, options = plan_fixture()
        del options["basis"]["frequency_hz"]
        blocked = build_conducted_twin_plan_input(context, analysis, **options)
        args[0] = blocked
        result = self.build(args, ref)
        self.assertEqual(result["gaps"][:len(blocked["gaps"])], blocked["gaps"])
        self.assertEqual(result["binding"]["plan_input"], blocked)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["calculation"]["corrected"])
        self.assertEqual(result["failure"]["code"], "plan_blocked")

    def test_plan_setup_and_topology_hash_mismatch_cannot_bind(self):
        original, ref = self.genuine()
        for field in ("plan_binding", "setup_sha256", "topology_sha256"):
            args = deepcopy(original)
            def change(stored):
                p = stored["header"]["provenance"]
                if field == "plan_binding":
                    p[field]["revision"] += 1
                else:
                    p[field] = "0" * 64
            args[2] = self.repack(args[2], change)
            with self.subTest(field=field):
                result = self.build(args, ref)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["calculation"]["raw_power_w"])
                self.assertIsNotNone(result["failure"])

    def test_plan_hash_and_setup_source_settings_mismatch_cannot_bind(self):
        original, ref = self.genuine()
        plan = deepcopy(original)
        plan[0]["plan"]["source_settings"]["power_dbm"] += 1
        self.assertEqual(self.build(plan, ref)["failure"]["code"], "plan_hash_mismatch")
        setup = deepcopy(original)
        setup[1][-3]["parameters"]["frequency_hz"] = 2450000000
        setup[2] = self.repack(setup[2], lambda s: s["header"]["provenance"].update(setup_sha256=sha(setup[1])))
        result = self.build(setup, ref)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["failure"]["code"], "source_settings_mismatch")

    def test_cross_runtime_report_or_events_and_corrupt_hash_never_bind(self):
        original, ref = self.genuine()
        for case in ("report", "event", "hash"):
            args = deepcopy(original)
            if case == "report":
                args[3]["runtime_instance_id"] = "different-runtime"
            elif case == "event":
                args[2]["events"][0]["runtime_instance_id"] = "different-runtime"
            else:
                args[2]["integrity"]["file_sha256"] = "0" * 64
            with self.subTest(case=case):
                result = self.build(args, ref)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["calculation"]["raw_power_w"])

    def test_freshness_and_native_measurement_validation_survive_recomputed_chain(self):
        original, ref = self.genuine()
        for key, value in (("acquisition_tick", 0), ("acquisition_setup_revision", 0),
                           ("unit", "W"), ("source_id", "meter"), ("value", True), ("valid", False)):
            args = deepcopy(original)
            def change(stored):
                for event in stored["events"]:
                    if event["event_id"] == ref:
                        event["payload"]["observation"]["devices"]["sensor"]["values"]["outputs"]["measurement"][key] = value
            args[2] = self.repack(args[2], change)
            with self.subTest(key=key):
                result = self.build(args, ref)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["calculation"]["raw_power_w"])
                self.assertEqual(result["raw_measurement"]["packet"][key], value)

    def test_path_invalid_and_source_metadata_conflict_propagate(self):
        original, ref = self.genuine()
        for case in ("path_invalid", "frequency", "power"):
            args = deepcopy(original)
            def change(stored):
                event = next(e for e in stored["events"] if e["event_id"] == ref)
                devices = event["payload"]["observation"]["devices"]
                if case == "path_invalid":
                    devices["switch"]["status"] = "invalid"
                elif case == "frequency":
                    devices["dut"]["values"]["outputs"]["rf"]["frequency_hz"] = 2450000000
                else:
                    devices["dut"]["values"]["outputs"]["rf"]["power_dbm"] += 1
            args[2] = self.repack(args[2], change)
            result = self.build(args, ref)
            self.assertEqual(result["status"], "invalid")
            self.assertIsNone(result["calculation"]["corrected"])

    def test_partial_setup_and_unresolved_or_incomplete_execution_are_not_results(self):
        original, ref = self.genuine()
        for case in ("setup", "journal", "report"):
            args = deepcopy(original)
            if case == "setup":
                args[1][-1].update(receipt=None, tick=None, setup_revision=None)
                args[2] = self.repack(args[2], lambda s: s["header"]["provenance"].update(setup_sha256=sha(args[1])))
            elif case == "journal":
                # A genuine reader snapshot is partial when its termination marker is absent.
                args[2] = self.repack(args[2], lambda s: s["events"].pop())
            else:
                args[3]["unresolved_request_ids"] = ["unknown-request"]
            with self.subTest(case=case):
                result = self.build(args, ref)
                self.assertNotEqual(result["status"], "recorded")
                self.assertIsNone(result["calculation"]["corrected"])

    def test_failed_recovery_cannot_use_report_completion_or_bootstrap_measurements(self):
        steps = ([{"kind": "advance", "ticks": 1}] * 4
                 + [{"kind": "execute", "device_id": "dut", "action": "start", "parameters": {}},
                    {"kind": "advance", "ticks": 1},
                    {"kind": "execute", "device_id": "sensor", "action": "acquire", "parameters": {}},
                    {"kind": "advance", "ticks": 1},
                    {"kind": "stop", "claim": "completed", "reason": "authored failed recovery"}])
        def policy(context):
            return steps.pop(0)
        args, ref = self.genuine(condition="persistent_disconnect", policy=policy)
        result = self.build(args, ref)
        self.assertEqual(args[3]["termination"]["policy_claim"], "completed")
        self.assertNotEqual(result["status"], "recorded")
        self.assertIsNone(result["calculation"]["raw_power_w"])
        self.assertIsNone(result["calculation"]["corrected"])

    def test_report_PASS_does_not_replace_missing_or_invalid_raw(self):
        args, ref = self.genuine()
        args[3]["assessment"] = dict(status="completed", verdict="pass", evaluator_id="fixture",
                                    evidence_refs=[ref], summary_code="authored-claim")
        def change(stored):
            event = next(e for e in stored["events"] if e["event_id"] == ref)
            event["payload"]["observation"]["devices"]["sensor"]["values"]["outputs"].clear()
        args[2] = self.repack(args[2], change)
        result = self.build(args, ref)
        self.assertNotEqual(result["status"], "recorded")
        self.assertIsNone(result["raw_measurement"])
        self.assertIsNone(result["calculation"]["corrected"])

    def test_missing_path_configuration_never_uses_fixed_loss_or_power_difference(self):
        args, ref = self.genuine()
        next(r for r in args[1] if r["device_id"] == "attenuator" and r["action"] == "configure")["parameters"] = {}
        args[2] = self.repack(args[2], lambda s: s["header"]["provenance"].update(setup_sha256=sha(args[1])))
        result = self.build(args, ref)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNotNone(result["calculation"]["raw_power_w"])
        self.assertIsNone(result["calculation"]["corrected"])
        self.assertIn("path_configuration_missing", self.codes(result))

    def test_parent_unit_conversion_failure_stays_null(self):
        args, ref = self.genuine()
        module = self.module()
        with patch.object(module, "calculate", side_effect=ValueError("private arithmetic detail")):
            result = self.build(args, ref)
        self.assertNotEqual(result["status"], "recorded")
        self.assertIsNone(result["calculation"]["raw_power_w"])
        self.assertNotIn("private arithmetic detail", json.dumps(result))

    def test_native_depth_size_record_event_and_output_bounds_are_fail_closed(self):
        args, ref = self.genuine()
        module = self.module()
        for name, value in (("MAX_INPUT_BYTES", 100), ("MAX_NODES", 3), ("MAX_DEPTH", 2),
                            ("MAX_PLAN_BYTES", 100), ("MAX_EVENTS", 2), ("MAX_SETUP_RECORDS", 2),
                            ("MAX_OUTPUT_BYTES", 2048)):
            with self.subTest(limit=name), patch.object(module, name, value):
                result = self.build(args, ref)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNotNone(result["failure"])
                self.assertIsNone(result["calculation"]["corrected"])
        for value in (True, object(), float("nan"), {"cycle": None}):
            bad = deepcopy(args)
            if type(value) is dict:
                value["cycle"] = value
            bad[1] = value
            result = self.build(bad, ref)
            self.assertEqual(result["status"], "invalid")

    def test_control_exceptions_propagate_and_builder_has_no_IO(self):
        args, ref = self.genuine()
        module = self.module()
        import builtins
        import socket
        import subprocess
        with patch.object(builtins, "open", side_effect=AssertionError("no IO")), patch.object(
                socket, "create_connection", side_effect=AssertionError("no network")), patch.object(
                subprocess, "Popen", side_effect=AssertionError("no process")):
            self.assertEqual(self.build(args, ref)["status"], "recorded")
        with patch.object(module, "calculate", side_effect=MemoryError):
            with self.assertRaises(MemoryError):
                self.build(args, ref)


    def test_malformed_nested_maps_return_invalid_instead_of_raising(self):
        original, ref = self.genuine()
        for case in ("payload", "observation", "devices", "values", "header"):
            args = deepcopy(original)
            event = next(e for e in args[2]["events"] if e["event_id"] == ref)
            if case == "payload":
                event["payload"] = None
            elif case == "observation":
                event["payload"]["observation"] = None
            elif case == "devices":
                event["payload"]["observation"]["devices"] = None
            elif case == "values":
                event["payload"]["observation"]["devices"]["sensor"]["values"] = None
            else:
                args[2]["header"] = None
            with self.subTest(case=case):
                try:
                    result = self.build(args, ref)
                except (AttributeError, TypeError, KeyError) as error:
                    self.fail("nested native evidence escaped validation: " + type(error).__name__)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["calculation"]["raw_power_w"])

    def test_receipt_profile_and_advance_clock_must_match_actual_intent(self):
        original, ref = self.genuine()
        for case in ("profile_id", "advance_tick", "advanced_ticks"):
            args = deepcopy(original)
            def change(stored):
                intents = {e["payload"]["request_id"]: e["payload"] for e in stored["events"] if e["type"] == "intent"}
                for event in stored["events"]:
                    if event["type"] != "receipt":
                        continue
                    intent = intents[event["payload"]["request_id"]]
                    receipt = event["payload"]["result"]
                    if case == "profile_id" and intent["body"].get("action") == "acquire":
                        receipt["profile_id"] = "wrong-profile"
                        return
                    if case != "profile_id" and intent["operation"] == "advance":
                        if case == "advance_tick":
                            receipt["tick"] += 100
                        else:
                            receipt["values"]["advanced_ticks"] += 1
                        return
            args[2] = self.repack(args[2], change)
            with self.subTest(case=case):
                result = self.build(args, ref)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["calculation"]["raw_power_w"])

    def test_D1_ready_claim_cannot_hide_missing_basis_or_execution_authority(self):
        original, ref = self.genuine()
        for case in ("authority", "intake", "basis", "peak_quote", "exponent_quote"):
            args = deepcopy(original)
            plan = args[0]
            if case == "authority":
                plan["verification"]["execution_authority"] = True
            elif case == "intake":
                plan["intake"] = None
            elif case == "basis":
                plan["plan"]["basis_refs"]["frequency_hz"] = None
            else:
                plan["plan"]["basis_refs"]["power_dbm"] = dict(kind="source_cited", value=-7, unit="dBm",
                    evidence=[dict(path="authored-report.txt", sha256="a"*64, line_start=1, line_end=1,
                                   quote=("reported_peak: -7 dBm" if case == "peak_quote" else "on_average_power: 1e999999999999999999999999999999 dBm"), role="reference")])
            plan["binding"]["plan_sha256"] = sha(plan["plan"])
            args[2] = self.repack(args[2], lambda s: s["header"]["provenance"].update(plan_binding=plan["binding"]))
            with self.subTest(case=case):
                try:
                    result = self.build(args, ref)
                except ArithmeticError as error:
                    self.fail("native basis quote escaped validation: " + type(error).__name__)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["calculation"]["raw_power_w"])


    def scripted(self, *, configure=False, stop=False):
        source = plan_fixture()[2]["source_settings"]
        steps = []
        if configure:
            steps.append(dict(kind="execute", device_id="dut", action="configure", parameters=source))
        steps += [dict(kind="execute", device_id="dut", action="start", parameters={}),
                  dict(kind="advance", ticks=1), dict(kind="advance", ticks=1),
                  dict(kind="execute", device_id="sensor", action="acquire", parameters={}),
                  dict(kind="advance", ticks=1),
                  dict(kind="execute", device_id="sensor", action="read", parameters={})]
        if stop:
            steps.append(dict(kind="execute", device_id="dut", action="stop", parameters={}))
        steps.append(dict(kind="stop", claim="completed", reason="authored sequence"))
        return lambda context: steps.pop(0)

    def test_actual_post_setup_configure_is_reported_as_unreconstructed(self):
        args, ref = self.genuine(policy=self.scripted(configure=True))
        result = self.build(args, ref)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["failure"]["code"], "post_setup_configuration")
        self.assertIsNone(result["calculation"]["corrected"])

    def test_actual_later_stop_preserves_selected_fresh_historical_packet(self):
        args, ref = self.genuine(policy=self.scripted(stop=True))
        result = self.build(args, ref)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["raw_measurement"]["packet"], self.packet(args, ref))
        final = [e for e in args[2]["events"] if e["type"] == "observation"][-1]
        self.assertNotIn("measurement", final["payload"]["observation"]["devices"]["sensor"]["values"]["outputs"])


if __name__ == "__main__":
    unittest.main()
