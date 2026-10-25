"""Current authored PDF -> genuine plan/result/artifact -> readonly compound relation."""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from labflow import intake_current_facts_plan as current_api
from labflow.store import Store, canonical
from labflow.ui_read_model import IntakeReadModel, ReadModelError
from labflow.virtual_fleet import conducted_result_artifact as writer
from labflow.virtual_fleet import conducted_result_artifact_read as reader
from labflow.virtual_fleet import conducted_twin_result as result_api

MODULE = "labflow.intake_conducted_artifact_readback"
METHOD = dict(method_id="conducted_synthetic", method_version=1, metric="on", reference_plane="source_output")
ROOT = Path(__file__).resolve().parents[1]


def sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class CurrentArtifactSmokeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec(MODULE), "current artifact readback module is absent")


class CurrentArtifactReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = importlib.import_module(MODULE)
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.base = Path(directory.name)
        spec = importlib.util.spec_from_file_location("current_pdf_fixture", Path(__file__).with_name("test_intake_current_facts_plan.py"))
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        data = fixture.completed_fixture(cls.base / "authored")
        cls.source_state = data["store"].root
        cls.intake_id = data["intake_id"]
        native = IntakeReadModel(cls.source_state).current_conducted_plan_context(cls.intake_id)
        cls.pins = dict(method=METHOD, expected_revision=native["context"]["revision"], expected_context_sha256=sha(native["context"]))
        cls.current = current_api.read_current_conducted_plan_from_facts(cls.source_state, cls.intake_id, **cls.pins)
        plan_input = cls.current["facts_plan"]["plan_input"]
        if plan_input["status"] != "ready_for_simulation":
            raise AssertionError("authored current PDF facts did not build ready plan")
        from labflow.virtual_fleet.catalog import load_catalog
        from labflow.virtual_fleet.evaluation import prepare_sensor_trial
        from labflow.virtual_fleet.harness import FleetHarness
        from labflow.virtual_fleet.integration import get_role_actions
        from labflow.virtual_fleet.journal import OperatorJournal, read_operator_journal
        from labflow.virtual_fleet.policies import RFSensorFixturePolicy
        catalog = load_catalog(ROOT / "virtual_profiles/sm_a176u_unlicensed.json")
        settings = plan_input["plan"]["source_settings"]
        trial = prepare_sensor_trial(catalog, power_dbm=settings["power_dbm"], source_settings=settings, setup_records=[])
        setup = trial.setup_snapshot()
        journal = cls.base / "authored-events.jsonl"
        provenance = dict(runtime_origin="preinitialized", catalog_sha256=sha(catalog), topology_sha256=sha(trial.topology),
            engine_sha256=hashlib.sha256((ROOT / "labflow/virtual_fleet/rf.py").read_bytes()).hexdigest(), topology=trial.topology,
            plan_binding=plan_input["binding"], setup_sha256=sha(setup), quantity=dict(metric="on", reference_plane="sensor_input",
                loss_compensation_applied=False, loss_compensation_sign=1))
        with OperatorJournal(journal, run_id="current-artifact-fixture", runtime_instance_id=trial.runtime_instance_id, provenance=provenance) as sink:
            report = FleetHarness(trial.runtime, RFSensorFixturePolicy(), goal=trial.goal, catalog=catalog,
                topology=trial.topology, role_actions=get_role_actions(), event_sink=sink,
                run_id="current-artifact-fixture", runtime_instance_id=trial.runtime_instance_id).run()
        cls.result = result_api.build_conducted_twin_result(plan_input, setup, read_operator_journal(journal), report,
                                                           measurement_ref=report["evidence"]["measurement_refs"][-1])
        if cls.result["status"] != "recorded":
            raise AssertionError("current-plan same-run fixture did not record")
        cls.artifact_root = cls.base / "artifact";cls.artifact_root.mkdir()
        binding = cls.result["binding"]
        cls.artifact_pins = dict(artifact_name="current-one", expected_result_sha256=sha(cls.result),
            run_id=binding["run_id"], runtime_instance_id=binding["runtime_instance_id"])
        summary = writer.write_conducted_result_artifact(cls.result, workspace_root=cls.artifact_root, **cls.artifact_pins)
        cls.artifact_pins["expected_manifest_sha256"] = summary["storage"]["sha256"]
        cls.raw = {name: (cls.artifact_root / ".local/conducted-result-artifacts/current-one" / name).read_bytes()
                   for name in ("manifest.json", "result.json", "draft.md")}

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.workspace = self.root / "state"
        shutil.copytree(self.source_state, self.workspace)
        self.artifact = self.root / "artifact";self.artifact.mkdir()
        self.leaf = self.artifact / ".local/conducted-result-artifacts/current-one"
        self.leaf.mkdir(parents=True)
        for name, raw in self.raw.items():
            (self.leaf / name).write_bytes(raw)
        self.options = dict(deepcopy(self.pins), artifact_workspace_root=self.artifact, **self.artifact_pins)

    def call(self, **changes):
        return self.api.read_current_conducted_artifact(self.workspace, self.intake_id, **{**self.options, **changes})

    def files(self):
        values = {}
        for path in self.root.rglob("*"):
            if path.is_file():
                s = path.stat()
                values[path.relative_to(self.root).as_posix()] = (path.read_bytes(), s.st_size, s.st_ino, s.st_mtime_ns, s.st_nlink, s.st_file_attributes)
        return values

    def test_genuine_pdf_plan_artifact_matched_and_original_dtos(self):
        before = self.files()
        value = self.call()
        self.assertEqual(set(value), set("schema_version kind status current artifact relation verification".split()))
        self.assertEqual(value["status"], "matched")
        self.assertEqual(value["current"], self.current)
        self.assertEqual(value["artifact"]["result"], self.result)
        self.assertTrue(all(value["relation"]["fields"].values()))
        self.assertEqual(value["relation"]["recheck"]["status"], "unchanged")
        self.assertEqual(value["relation"]["current_binding"], self.current["facts_plan"]["plan_input"]["binding"])
        self.assertEqual(value["verification"]["current_completion"], "not_assessed")
        self.assertIs(value["verification"]["execution_authority"], False)
        self.assertEqual(self.files(), before)

    def test_exact_current_api_once_artifact_once_raw_post_once_and_original_identity(self):
        original, captured = IntakeReadModel.current_conducted_plan_context, []
        def raw(model, intake):
            output = original(model, intake);captured.append(output);return output
        with patch.object(IntakeReadModel, "current_conducted_plan_context", autospec=True, side_effect=raw) as post, patch.object(
                current_api, "read_current_conducted_plan_from_facts", wraps=current_api.read_current_conducted_plan_from_facts) as current, patch.object(
                reader, "read_conducted_result_artifact", wraps=reader.read_conducted_result_artifact) as artifact:
            value = self.call()
        self.assertEqual((current.call_count, artifact.call_count, post.call_count), (1, 1, 2))
        self.assertIs(value["current"]["context"], captured[0]["context"])
        self.assertEqual(current.call_args.kwargs, self.pins)
        self.assertEqual(artifact.call_args.kwargs, dict(workspace_root=self.artifact, **self.artifact_pins))

    def test_null_and_stale_pins_and_blocked_method_skip_artifact(self):
        cases = (dict(expected_revision=None), dict(expected_context_sha256=None), dict(expected_revision=999),
                 dict(expected_context_sha256="0" * 64), dict(method={**METHOD, "metric": "unsupported"}))
        for changes in cases:
            with self.subTest(changes=changes), patch.object(reader, "read_conducted_result_artifact", side_effect=AssertionError("blocked reader0")):
                value = self.call(**changes)
                self.assertEqual(value["status"], "blocked")
                self.assertIsNone(value["artifact"])
                self.assertTrue(all(v is None for v in value["relation"]["fields"].values()))
                self.assertTrue(value["relation"]["reasons"])

    def test_other_developer_method_is_different_plan_not_repaired(self):
        value = self.call(method={**METHOD, "metric": "time"})
        self.assertEqual(value["status"], "different_plan")
        self.assertIs(value["relation"]["fields"]["plan_sha256"], False)
        self.assertEqual(value["artifact"]["result"]["binding"]["plan_input"]["plan"]["metric"], "on")
        self.assertEqual(value["current"]["facts_plan"]["plan_input"]["plan"]["metric"], "time")

    def test_other_declared_intake_binding_is_not_copied_to_current(self):
        result = deepcopy(self.result)
        result["binding"]["plan_input"]["binding"]["intake_id"] = "I-OTHER-DECLARED"
        result["binding"]["plan_input_sha256"] = sha(result["binding"]["plan_input"])
        raw = canonical(result).encode("utf-8") + b"\n"
        (self.leaf / "result.json").write_bytes(raw)
        manifest = json.loads(self.raw["manifest.json"])
        manifest["result_sha256"] = sha(result)
        manifest["files"][0].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        raw_manifest = canonical(manifest).encode("utf-8") + b"\n"
        (self.leaf / "manifest.json").write_bytes(raw_manifest)
        value = self.call(expected_result_sha256=sha(result), expected_manifest_sha256=hashlib.sha256(raw_manifest).hexdigest())
        self.assertEqual(value["status"], "different_intake")
        self.assertEqual(value["relation"]["current_binding"]["intake_id"], self.intake_id)
        self.assertEqual(value["relation"]["artifact_binding"]["intake_id"], "I-OTHER-DECLARED")

    def test_valid_post_context_or_analysis_drift_is_stale(self):
        original = IntakeReadModel.current_conducted_plan_context
        for section in ("context", "analysis"):
            count = []
            def read(model, intake):
                value = original(model, intake);count.append(True)
                if len(count) == 2:
                    value = deepcopy(value)
                    if section == "context":value["context"]["instructions"] += " observed drift"
                    else:value["analysis"]["producer"]["name"] += "-observed-drift"
                return value
            with self.subTest(section=section), patch.object(IntakeReadModel, "current_conducted_plan_context", autospec=True, side_effect=read):
                value = self.call()
            self.assertEqual(value["status"], "stale")
            self.assertEqual(value["relation"]["recheck"]["status"], "changed")
            self.assertIsNotNone(value["artifact"])
            self.assertEqual(value["verification"]["current_completion"], "not_assessed")

    def test_actual_retained_bytes_drift_after_artifact_fails_post_read(self):
        original = reader.read_conducted_result_artifact
        def changed(**kwargs):
            value = original(**kwargs)
            retained = Store.blob_path(type("Root", (), {"root": self.workspace})(), self.current["context"]["documents"][0]["sha256"])
            raw = retained.read_bytes();retained.write_bytes(b"x" + raw[1:])
            return value
        with patch.object(reader, "read_conducted_result_artifact", side_effect=changed):
            with self.assertRaises(self.api.IntakeConductedArtifactReadbackError) as caught:
                self.call()
        self.assertEqual(caught.exception.code, "intake_conducted_artifact_readback_current_recheck_failed")

    def test_missing_current_or_artifact_errors_remain_parent_objects(self):
        for stage, error in (("current", ReadModelError("intake_not_found")),
                             ("artifact", reader.ConductedResultArtifactReadError("conducted_result_artifact_read_not_found"))):
            target = current_api if stage == "current" else reader
            name = "read_current_conducted_plan_from_facts" if stage == "current" else "read_conducted_result_artifact"
            with self.subTest(stage=stage), patch.object(target, name, side_effect=error):
                with self.assertRaises(type(error)) as caught:self.call()
                self.assertIs(caught.exception, error)

    def test_control_identity_at_current_artifact_and_post_read(self):
        for stage in ("current", "artifact", "post"):
            for error in (KeyboardInterrupt(), MemoryError(), SystemExit(0), GeneratorExit(), RuntimeError("unexpected")):
                original = IntakeReadModel.current_conducted_plan_context
                count = []
                def post(model, intake):
                    count.append(True)
                    if len(count) == 2:raise error
                    return original(model, intake)
                target = current_api if stage == "current" else reader if stage == "artifact" else IntakeReadModel
                name = "read_current_conducted_plan_from_facts" if stage == "current" else "read_conducted_result_artifact" if stage == "artifact" else "current_conducted_plan_context"
                with self.subTest(stage=stage, error=type(error).__name__), patch.object(target, name,
                        autospec=stage == "post", side_effect=post if stage == "post" else error):
                    with self.assertRaises(type(error)) as caught:self.call()
                    self.assertIs(caught.exception, error)

    def test_runtime_sql_is_ro_known_connections_bindings_close_and_no_business_writes(self):
        from labflow.store import _ExistingBinding
        connect, acquire = sqlite3.connect, _ExistingBinding.acquire
        connections, statements, bindings, connect_args = [], [], [], []
        def observed_connect(*args, **kwargs):
            connect_args.append((args, kwargs));con = connect(*args, **kwargs)
            con.set_trace_callback(statements.append);connections.append(con);return con
        def observed_acquire(binding):
            try:return acquire(binding)
            finally:bindings.append(binding)
        before = self.files()
        with ExitStack() as stack:
            for target in ("labflow.store.Store.__init__", "labflow.store.Store.connection", "labflow.store.Store.write_blob",
                           "labflow.store.Store.register_blob", "labflow.intake_jobs.claim_job", "labflow.intake_jobs.complete_job",
                           "labflow.active_intake.scan_source", "labflow.intake_documents.prepare_analysis_documents",
                           "labflow.intake_worker.SyntheticTextProvider.analyze", "labflow.document_extract.extract_document",
                           "labflow.virtual_fleet.conducted_result_artifact.write_conducted_result_artifact"):
                stack.enter_context(patch(target, side_effect=AssertionError("no business write/model/execution")))
            stack.enter_context(patch.object(sqlite3, "connect", side_effect=observed_connect))
            stack.enter_context(patch.object(_ExistingBinding, "acquire", observed_acquire))
            value = self.call()
        self.assertEqual(value["status"], "matched")
        self.assertEqual(self.files(), before)
        self.assertEqual(len(bindings), 2)
        self.assertTrue(all("?mode=ro" in args[0] and kwargs.get("uri") is True for args, kwargs in connect_args))
        writes = {"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "REPLACE", "VACUUM", "ATTACH", "DETACH"}
        self.assertTrue(all(sql.strip().split()[0].upper() not in writes for sql in statements))
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError):con.execute("SELECT 1")
        self.assertTrue(all(b.state == "closed" and b.active == 0 and not b.handles for b in bindings))

    def test_caps_and_parent_null_or_shape_conflicts_are_closed(self):
        for name in ("MAX_CURRENT_BYTES", "MAX_ARTIFACT_BYTES", "MAX_OUTPUT_BYTES"):
            with self.subTest(cap=name), patch.object(self.api, name, 1):
                with self.assertRaises(self.api.IntakeConductedArtifactReadbackError) as caught:self.call()
                self.assertEqual(caught.exception.code, "intake_conducted_artifact_readback_input_limit")
        wrong_kind = deepcopy(self.current)
        wrong_kind["facts_plan"]["plan_input"]["kind"] = "unknown-plan"
        wrong_authority = deepcopy(self.current)
        wrong_authority["facts_plan"]["plan_input"]["verification"]["execution_authority"] = True
        for target, name, value in ((current_api, "read_current_conducted_plan_from_facts", None),
                                   (current_api, "read_current_conducted_plan_from_facts", {**self.current, "extra": 1}),
                                   (current_api, "read_current_conducted_plan_from_facts", wrong_kind),
                                   (current_api, "read_current_conducted_plan_from_facts", wrong_authority),
                                   (reader, "read_conducted_result_artifact", None)):
            with self.subTest(parent=name, value=repr(value)[:40]), patch.object(target, name, return_value=value):
                with self.assertRaises(self.api.IntakeConductedArtifactReadbackError) as caught:self.call()
                self.assertEqual(caught.exception.code, "intake_conducted_artifact_readback_parent_invalid")
