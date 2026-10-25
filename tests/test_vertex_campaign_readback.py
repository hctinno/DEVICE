"""Author-created shape claims; no producer, decoder, ADC, or model execution."""

import copy
import hashlib
import importlib
import json
import unittest
from unittest import mock


PAIR = dict(scenario_id="DGM-AI-CONNECTION-001", scenario_version=1,
            evaluator_id="connection-json-v1", evaluator_version=1,
            prompt_sha256="bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230",
            schema_sha256="a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9")
MODELS = ["gemini-4-argon", "gemini-3.8-flash"]
LEVELS = ["LOW", "MEDIUM", "HIGH"]
PROJECT = "project-a6310591-f8cc-487c-9e3"
USAGE = "prompt_token_count candidates_token_count total_token_count thoughts_token_count cached_content_token_count tool_use_prompt_token_count".split()
INVALID = "vertex_campaign_readback_invalid_input"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(manifest, artifacts):
    module = importlib.import_module("labflow.vertex_campaign_readback")
    return module.build_vertex_connection_campaign_readback(manifest, artifacts)


def settings(index):
    value = dict(schema_version=1, kind="ai_run_settings", profile_id="SHAPE-PROFILE",
                 profile_revision=1, provider="vertex_ai", service="aiplatform.googleapis.com",
                 project_id=PROJECT, location="global", quota_project_id=PROJECT,
                 auth_profile_id="DO-NOT-EXPOSE-AUTH-ID", model_id=MODELS[index // 3],
                 thinking_level=LEVELS[index % 3], max_output_tokens=256,
                 timeout_seconds=20.0, profile_sha256=sha(b"author-profile-shape"))
    value["settings_sha256"] = sha(canonical(value))
    return value


def receipt(setting, identity, generation=1):
    complete = generation == 1
    def artifact(name, size=17, digest=None):
        return dict(path=name, present=True, bytes=size,
                    sha256=digest or sha(name.encode()), complete=True,
                    overflow=False, extent="whole_file")
    value = dict(
        schema_version=1, kind="vertex_response_receipt",
        exchange_ref="vertex-exchange:" + sha(identity.encode())[:32],
        status="complete" if complete else "failed",
        failure=None if complete else dict(code="vertex_response_auth_failed", phase="auth"),
        bindings=dict(prompt_sha256=PAIR["prompt_sha256"], schema_sha256=PAIR["schema_sha256"],
                      provider_payload_sha256=sha(b"shape-provider-request"),
                      settings_sha256=setting["settings_sha256"]),
        settings=copy.deepcopy(setting),
        client=dict(transport="REST", api_version="v1", google_auth_version="2.62.0",
                    requests_version="2.34.2", google_genai_used=False),
        request=dict(method="POST", url="https://aiplatform.googleapis.com/v1/projects/" + PROJECT +
                     "/locations/global/publishers/google/models/" + setting["model_id"] + ":generateContent",
                     quota_project_id=PROJECT, auth_profile_id=setting["auth_profile_id"]),
        attempts=dict(worker_process_attempts=1, auth_refresh_attempts=1, auth_http_attempts=1,
                      generation_post_attempts=generation, auth_refresh_completed=True,
                      auth_retry_blocked=False, application_retries=0),
        response=dict(http_status=200 if complete else None, auth_http_status=200 if complete else 401,
                      finish_reason="STOP" if complete else None,
                      reported_model_version="SHAPE-REPORTED-VERSION", provider_response_id="DO-NOT-EXPOSE-RESPONSE-ID",
                      text_parts=1 if complete else None, thought_parts=0 if complete else None),
        usage=None, cost=dict(kind="unknown" if generation else "not_applicable",
                             amount=None, currency=None, price_version=None),
        timing=dict(timeout_seconds=20.0, local_elapsed_seconds=0.25),
        cancellation=dict(requested=False, local_worker_stopped=None,
                          provider_completion="observed_stop" if complete else "not_started",
                          remote_cancel_verified=False),
        cleanup=dict(worker_reaped=True, worker_exit_code=0, transport_handles_closed=True,
                     artifact_handles_closed=True, secondary_errors=[], remote_cancellation_verified=False),
        artifacts=dict(prompt=artifact("request.json", 639, PAIR["prompt_sha256"]),
                       response_schema=artifact("response-schema.json", 321, PAIR["schema_sha256"]),
                       settings=artifact("settings.json", len(canonical(setting)), sha(canonical(setting))),
                       provider_request=artifact("provider-request.json", 23, sha(b"shape-provider-request")),
                       provider_response=artifact("provider-response.bin"), final_text=artifact("response-text.bin")),
        verification=dict(wire_complete=complete, credential_metadata_verified=True,
                          remote_identity_verified=False, semantic_quality_verified=False, credit_verified=False))
    if not complete:
        for key in ("provider_response", "final_text"):
            value["artifacts"][key].update(present=False, bytes=0, sha256=None,
                                            complete=False, extent="absent")
    return value


def row(index=0, batch_id="BATCH-A", status="success", placeholder=False):
    setting = None if placeholder else settings(index)
    post = None if status == "unknown" else 0 if status != "success" else 1
    rec = None if placeholder or status in ("unknown", "not_run") else receipt(setting, batch_id + str(index), post)
    reserved = not placeholder and status != "not_run"
    return dict(
        schema_version=1, kind="vertex_comparison_row", batch_id=batch_id,
        run_id=batch_id + ":run:" + str(index), row_index=index,
        binding=dict(**PAIR, profile_sha256=sha(b"author-profile-shape"),
                     settings_sha256=None if setting is None else setting["settings_sha256"],
                     matrix_sha256=sha((batch_id + ":matrix").encode())),
        settings=setting, execution_mode="actual", status="not_run" if placeholder else status,
        reason_code="not_selected" if placeholder else "connection_verified" if status == "success" else
                    "receipt_invalid" if status == "unknown" else "cancelled" if status == "not_run" else "vertex_response_auth_failed",
        receipt=rec,
        strict_decode=dict(status="checked" if status == "success" and not placeholder else "not_run",
                           evaluator_id=PAIR["evaluator_id"], error_code=None),
        assessment=dict(status="not_assessed", verdict=None, reason_code="connection_only"),
        budget=dict(budget_id="BUDGET-A" if reserved else None,
                    reservation_id=batch_id + ":reservation:" + str(index) if reserved else None,
                    reserved_calls=index + 1 if reserved else None,
                    reserved_output_tokens=(index + 1) * 256 if reserved else None,
                    generation_post_attempts=0 if placeholder else post),
        timing=dict(started_at="2026-10-25T12:00:00.000+09:00" if reserved else None,
                    finished_at="2026-10-25T12:00:00.250+09:00", elapsed_ms=250.0 if reserved else 0))


def batch(rows):
    known = sum(r["budget"]["generation_post_attempts"] for r in rows if r["budget"]["generation_post_attempts"] is not None)
    unknown = sum(r["budget"]["generation_post_attempts"] is None for r in rows)
    return dict(schema_version=1, kind="vertex_comparison_batch", batch_id=rows[0]["batch_id"],
                matrix_sha256=rows[0]["binding"]["matrix_sha256"], execution_mode="actual", rows=rows,
                summary=dict(planned_rows=6, selected_rows=sum(r["settings"] is not None for r in rows),
                             success_rows=sum(r["status"] == "success" for r in rows),
                             failed_rows=sum(r["status"] == "failed" for r in rows),
                             not_run_rows=sum(r["status"] == "not_run" for r in rows),
                             unknown_rows=sum(r["status"] == "unknown" for r in rows),
                             cumulative_reserved_calls=6, cumulative_reserved_output_tokens=1536,
                             generation_post_attempts=None if unknown else known,
                             generation_post_attempts_known=known, generation_post_attempts_unknown_rows=unknown),
                business_assessment="not_assessed")


def selection(objects, origin="mock"):
    sources, artifacts = [], {}
    for name, obj in objects.items():
        raw = canonical(obj)
        kind = "batch" if obj["kind"] == "vertex_comparison_batch" else "row" if obj["kind"] == "vertex_comparison_row" else "receipt"
        index = obj.get("row_index")
        if kind == "receipt":
            index = MODELS.index(obj["settings"]["model_id"]) * 3 + LEVELS.index(obj["settings"]["thinking_level"])
        sources.append(dict(source_id=name, format=kind, bytes=len(raw), sha256=sha(raw),
                            generation_origin=origin, affected_cells=list(range(6)) if kind == "batch" else [index]))
        artifacts[name] = raw
    return dict(schema_version=1, kind="vertex_connection_campaign_selection", campaign_id="SHAPE-CAMPAIGN",
                pair=copy.deepcopy(PAIR), axes=dict(model_ids=MODELS[:], thinking_levels=LEVELS[:]),
                sources=sources, replay_links=[]), artifacts


def replace_bytes(manifest, artifacts, name, raw):
    source = next(s for s in manifest["sources"] if s["source_id"] == name)
    artifacts[name] = raw
    source.update(bytes=len(raw), sha256=sha(raw))


def replay_case():
    replay = row(4)
    original = copy.deepcopy(replay)
    original.update(status="unknown", reason_code="receipt_invalid", receipt=None)
    original["budget"]["generation_post_attempts"] = None
    original["strict_decode"]["status"] = "not_run"
    replay["execution_mode"] = "replay"
    manifest, artifacts = selection(dict(original=original, replay=replay, receipt=replay["receipt"]))
    manifest["replay_links"] = [dict(original_source_id="original", original_source_sha256=sha(artifacts["original"]),
        original_row_sha256=sha(canonical(original)), replay_source_id="replay", receipt_source_id="receipt",
        exchange_ref=replay["receipt"]["exchange_ref"], budget_id=replay["budget"]["budget_id"],
        reservation_id=replay["budget"]["reservation_id"], prompt_sha256=PAIR["prompt_sha256"],
        schema_sha256=PAIR["schema_sha256"], settings_sha256=replay["settings"]["settings_sha256"])]
    return manifest, artifacts


class CampaignReadbackTests(unittest.TestCase):
    def test_author_shape_fixture_precheck(self):
        r = row()
        self.assertEqual(len(r), 15)
        self.assertEqual(len(r["receipt"]), 18)
        self.assertEqual(len(batch([row(i) for i in range(6)])), 8)
        setting = copy.deepcopy(r["settings"])
        digest = setting.pop("settings_sha256")
        self.assertEqual(digest, sha(canonical(setting)))

    def test_complete_batch_and_exact_report_shape(self):
        manifest, artifacts = selection(dict(batch=batch([row(i) for i in range(6)])))
        out = read(manifest, artifacts)
        self.assertEqual(set(out), set("schema_version kind campaign_id pair cells totals sources issues assurance".split()))
        self.assertEqual(out["kind"], "vertex_connection_campaign_readback")
        self.assertEqual([c["status"] for c in out["cells"]], ["success"] * 6)
        self.assertEqual(set(out["cells"][0]), set("row_index model_id thinking_level status history not_run_observations issues".split()))
        self.assertEqual(out["assurance"], dict(basis="provided_records_only", root_authorization_verified=False,
                                               underlying_artifacts_verified=False))
        self.assertEqual(out["totals"]["generation_post_attempts"], 6)
        self.assertEqual(out["totals"]["new_actual_calls"], 0)

    def test_duplicate_batch_row_receipt_is_one_attempt(self):
        rows = [row(i, placeholder=i != 0) for i in range(6)]
        manifest, artifacts = selection(dict(batch=batch(rows), row=rows[0], copy=rows[0], receipt=rows[0]["receipt"]))
        out = read(manifest, artifacts)
        self.assertEqual(out["cells"][0]["status"], "success")
        self.assertEqual(len(out["cells"][0]["history"]), 1)
        self.assertEqual(out["totals"]["observed_reservations"], 1)
        self.assertEqual(out["totals"]["generation_post_attempts_known"], 1)

    def test_missing_tampered_partial_and_identity_conflict_stay_unknown(self):
        for corrupt in (None, b"changed", b'{"schema_version":'):
            with self.subTest(corrupt=corrupt):
                manifest, artifacts = selection(dict(row=row()))
                if corrupt is not None and corrupt.startswith(b"{"):
                    replace_bytes(manifest, artifacts, "row", corrupt)
                else:
                    artifacts["row"] = corrupt
                self.assertEqual(read(manifest, artifacts)["cells"][0]["status"], "unknown")
        first = row()
        other = copy.deepcopy(first)
        other["timing"]["elapsed_ms"] = 251.0
        manifest, artifacts = selection(dict(first=first, other=other))
        out = read(manifest, artifacts)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertIn("identity_conflict", {i["code"] for i in out["issues"]})

    def test_missing_expected_copy_is_not_hidden_by_good_copy(self):
        manifest, artifacts = selection(dict(good=row(), missing=row()))
        artifacts["missing"] = None
        out = read(manifest, artifacts)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertTrue(out["cells"][0]["history"])

    def test_cross_reservation_exchange_and_orphan_receipt_are_unknown(self):
        a, b = row(), row(batch_id="BATCH-B")
        b["receipt"] = copy.deepcopy(a["receipt"])
        manifest, artifacts = selection(dict(a=a, b=b))
        out = read(manifest, artifacts)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertEqual(out["totals"]["observed_reservations"], 2)
        self.assertLessEqual(out["totals"]["generation_post_attempts_known"], 1)
        manifest, artifacts = selection(dict(orphan=a["receipt"]))
        out = read(manifest, artifacts)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertIn("orphan_receipt", {i["code"] for i in out["issues"]})

    def test_not_selected_never_overwrites_attempt_in_any_order(self):
        placeholders = [row(i, "BATCH-B", placeholder=True) for i in range(6)]
        manifest, artifacts = selection(dict(success=row(), coverage=batch(placeholders)))
        first = read(manifest, artifacts)
        manifest["sources"].reverse()
        second = read(manifest, dict(reversed(list(artifacts.items()))))
        self.assertEqual(first, second)
        self.assertEqual(first["cells"][0]["status"], "success")
        self.assertEqual(first["cells"][1]["status"], "not_run")

    def test_distinct_attempts_in_one_cell_keep_all_history(self):
        manifest, artifacts = selection(dict(a=row(), b=row(batch_id="BATCH-B")))
        out = read(manifest, artifacts)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertEqual(len(out["cells"][0]["history"]), 2)
        self.assertEqual(out["totals"]["observed_reservations"], 2)

    def test_exact_row15_replay_keeps_original_unknown_without_new_call(self):
        manifest, artifacts = replay_case()
        before = copy.deepcopy((manifest, artifacts))
        out = read(manifest, artifacts)
        h = out["cells"][4]["history"]
        self.assertEqual(out["cells"][4]["status"], "success")
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["original_status"], "unknown")
        self.assertEqual(h[0]["effective_status"], "success")
        self.assertEqual(h[0]["interpretation_source"], "provided_row_replay")
        self.assertEqual(out["totals"]["observed_reservations"], 1)
        self.assertEqual(out["totals"]["generation_post_attempts_known"], 1)
        self.assertEqual((manifest, artifacts), before)

    def test_wrong_partial_unlinked_or_conflicting_row_replay_cannot_promote(self):
        for field in ("original_source_sha256", "original_row_sha256", "reservation_id", "exchange_ref", "settings_sha256"):
            with self.subTest(field=field):
                m, a = replay_case()
                m["replay_links"][0][field] = "0" * 64 if field.endswith("sha256") else "WRONG"
                self.assertEqual(read(m, a)["cells"][4]["status"], "unknown")
        for pointer in (None, "missing"):
            m, a = replay_case()
            m["replay_links"][0]["receipt_source_id"] = pointer
            self.assertEqual(read(m, a)["cells"][4]["status"], "unknown")
        m, a = replay_case()
        m["replay_links"] = []
        self.assertEqual(read(m, a)["cells"][4]["status"], "unknown")

    def test_all_copy_origin_conflicts_stay_unknown(self):
        m, a = replay_case()
        next(s for s in m["sources"] if s["source_id"] == "replay")["generation_origin"] = "actual"
        self.assertEqual(read(m, a)["cells"][4]["status"], "unknown")
        m, a = selection(dict(a=row(), b=row()))
        m["sources"][1]["generation_origin"] = "actual"
        out = read(m, a)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertIsNone(out["totals"]["by_generation_origin"]["actual"]["generation_post_attempts"])

    def test_receipt_alias_origin_conflict_marks_linked_attempt_unknown(self):
        m, a = replay_case()
        alias = copy.deepcopy(next(s for s in m["sources"] if s["source_id"] == "receipt"))
        alias.update(source_id="receipt-alias", generation_origin="actual")
        m["sources"].append(alias)
        a["receipt-alias"] = a["receipt"]
        out = read(m, a)
        history = out["cells"][4]["history"][0]
        self.assertEqual(out["cells"][4]["status"], "unknown")
        self.assertEqual(history["original_status"], "unknown")
        self.assertEqual(history["effective_status"], "unknown")
        self.assertEqual(history["generation_origin"], "unknown")

    def test_bad_row_replay_link_does_not_invalidate_other_batch_cells(self):
        m, a = replay_case()
        original = json.loads(a["original"])
        rows = [row(i) for i in range(6)]
        rows[4] = original
        objects = dict(original_batch=batch(rows), replay=json.loads(a["replay"]), receipt=json.loads(a["receipt"]))
        manifest, artifacts = selection(objects)
        link = copy.deepcopy(m["replay_links"][0])
        link.update(original_source_id="original_batch", original_source_sha256=sha(artifacts["original_batch"]),
                    original_row_sha256="0" * 64)
        manifest["replay_links"] = [link]
        out = read(manifest, artifacts)
        self.assertEqual([c["status"] for c in out["cells"]],
                         ["success", "success", "success", "success", "unknown", "success"])

    def test_cumulative_budget_snapshots_are_never_summed_or_refunded(self):
        r = row(3, status="failed")
        m, a = selection(dict(row=r))
        out = read(m, a)
        self.assertEqual(out["cells"][3]["status"], "failed")
        self.assertEqual(out["totals"]["observed_reservations"], 1)
        self.assertEqual(out["totals"]["reserved_output_tokens_known"], 256)
        self.assertEqual(out["totals"]["generation_post_attempts_known"], 0)
        self.assertIsNone(out["totals"]["ledger_balance"])
        self.assertIsNone(out["totals"]["remaining_capacity"])
        self.assertIsNone(out["totals"]["cost"]["amount"])

    def test_reserved_not_run_keeps_reservation(self):
        r = row(status="not_run")
        r["budget"].update(budget_id="BUDGET-A", reservation_id="RESERVED-BEFORE-CANCEL",
                           reserved_calls=1, reserved_output_tokens=256)
        m, a = selection(dict(row=r))
        out = read(m, a)
        self.assertEqual(out["cells"][0]["status"], "not_run")
        self.assertEqual(out["totals"]["observed_reservations"], 1)
        self.assertEqual(out["totals"]["reserved_output_tokens_known"], 256)

    def test_generation_usage_and_cost_preserve_zero_and_null(self):
        rows = [row(i) for i in range(6)]
        for r in rows:
            r["receipt"]["usage"] = dict.fromkeys(USAGE, 0)
        rows[0]["receipt"]["usage"]["total_token_count"] = 13
        rows[1]["receipt"]["usage"]["total_token_count"] = None
        m, a = selection(dict(batch=batch(rows)))
        out = read(m, a)
        metric = out["totals"]["usage"]["total_token_count"]
        self.assertEqual(metric["known_subtotal"], 13)
        self.assertEqual(metric["unknown_exchange_count"], 1)
        self.assertIsNone(metric["total"])
        self.assertEqual(out["totals"]["usage"]["cached_content_token_count"]["total"], 0)
        self.assertIsNone(out["totals"]["cost"]["amount"])

    def test_unknown_generation_is_not_zero(self):
        m, a = selection(dict(row=row(status="unknown")))
        out = read(m, a)
        self.assertEqual(out["cells"][0]["status"], "unknown")
        self.assertIsNone(out["totals"]["generation_post_attempts"])
        self.assertEqual(out["totals"]["observed_reservations"], 1)

    def test_pair_axis_version_types_and_input_caps_fail_closed(self):
        for mutate in (
            lambda m: m.update(schema_version=True),
            lambda m: m["pair"].update(scenario_version=True),
            lambda m: m["pair"].update(prompt_sha256="0" * 64),
            lambda m: m["axes"].update(thinking_levels=tuple(LEVELS)),
            lambda m: m["sources"][0].update(bytes=True),
            lambda m: m["sources"][0].update(affected_cells=[True]),
            lambda m: m["sources"][0].update(affected_cells=[0, 0]),
            lambda m: m.update(root_authorization_verified=True),
        ):
            m, a = selection(dict(row=row()))
            mutate(m)
            with self.assertRaisesRegex(ValueError, "^" + INVALID + "$"):
                read(m, a)
        m, a = selection(dict(row=row()))
        a["extra"] = b"do-not-expose"
        with self.assertRaisesRegex(ValueError, "^" + INVALID + "$"):
            read(m, a)

    def test_source_count_and_byte_boundaries(self):
        m, a = selection(dict(row=row()))
        raw = a["row"] + b" " * (1048576 - len(a["row"]))
        replace_bytes(m, a, "row", raw)
        self.assertEqual(read(m, a)["cells"][0]["status"], "success")
        replace_bytes(m, a, "row", raw + b" ")
        with self.assertRaisesRegex(ValueError, "^" + INVALID + "$"):
            read(m, a)
        m, a = selection({"row" + str(i): row() for i in range(33)})
        with self.assertRaisesRegex(ValueError, "^" + INVALID + "$"):
            read(m, a)

    def test_total_byte_boundary(self):
        m, a = selection({"row" + str(i): row() for i in range(8)})
        for name in a:
            replace_bytes(m, a, name, a[name] + b" " * (1048576 - len(a[name])))
        self.assertEqual(read(m, a)["cells"][0]["status"], "success")
        source = copy.deepcopy(m["sources"][0])
        source.update(source_id="extra", bytes=1, sha256=sha(b"0"))
        m["sources"].append(source)
        a["extra"] = b"0"
        with self.assertRaisesRegex(ValueError, "^" + INVALID + "$"):
            read(m, a)

    def test_source_json_is_strict_and_versions_are_unknown(self):
        for raw in (b'{"kind":1,"kind":2}', b'{"value":NaN}', b'{"value":1e999}',
                    b'{} {}', b'"\\ud800"'):
            m, a = selection(dict(row=row()))
            replace_bytes(m, a, "row", raw)
            self.assertEqual(read(m, a)["cells"][0]["status"], "unknown")
        for value in (True, 2, "1"):
            r = row()
            r["schema_version"] = value
            m, a = selection(dict(row=r))
            self.assertEqual(read(m, a)["cells"][0]["status"], "unknown")

    def test_native_receipt_forgery_is_unknown(self):
        for value in (False, 0, 1, "true"):
            r = row()
            r["receipt"]["cancellation"]["local_worker_stopped"] = value
            m, a = selection(dict(row=r))
            self.assertEqual(read(m, a)["cells"][0]["status"], "unknown")
        for value in (None, True):
            r = row()
            r["receipt"]["cancellation"]["local_worker_stopped"] = value
            m, a = selection(dict(row=r))
            self.assertEqual(read(m, a)["cells"][0]["status"], "success")

    def test_batch_summary_mismatch_and_declared_axis_mismatch_are_unknown(self):
        b = batch([row(i) for i in range(6)])
        b["summary"]["success_rows"] = 5
        m, a = selection(dict(batch=b, good=b["rows"][0]))
        self.assertTrue(all(c["status"] == "unknown" for c in read(m, a)["cells"]))
        m, a = selection(dict(row=row()))
        m["sources"][0]["affected_cells"] = [1]
        self.assertEqual(read(m, a)["cells"][1]["status"], "unknown")

    def test_report_is_detached_deterministic_and_contains_no_raw_content(self):
        m, a = replay_case()
        snapshot = copy.deepcopy((m, a))
        first = read(m, a)
        expected = copy.deepcopy(first)
        first["cells"][4]["history"].clear()
        self.assertEqual(read(m, a), expected)
        self.assertEqual((m, a), snapshot)
        m["sources"].reverse()
        self.assertEqual(read(m, dict(reversed(list(a.items())))), expected)
        encoded = json.dumps(expected)
        for marker in ("DO-NOT-EXPOSE-AUTH-ID", "DO-NOT-EXPOSE-RESPONSE-ID", "response-text.bin", "provider-response.bin"):
            self.assertNotIn(marker, encoded)

    def test_reported_version_namespace_is_metadata_and_absolute_path_is_redacted(self):
        namespace = "publishers/google/models/SHAPE-VERSION"
        r = row()
        r["receipt"]["response"]["reported_model_version"] = namespace
        m, a = selection(dict(row=r))
        out = read(m, a)
        self.assertEqual(out["cells"][0]["history"][0]["reported_model_version"], namespace)
        r["receipt"]["response"]["reported_model_version"] = "C:/private/credential.json"
        m, a = selection(dict(row=r))
        self.assertNotIn("C:/private/credential.json", json.dumps(read(m, a)))

    def test_reader_performs_no_io_execution_or_ledger_mutation(self):
        function = importlib.import_module("labflow.vertex_campaign_readback").build_vertex_connection_campaign_readback
        m, a = selection(dict(row=row()))
        with mock.patch("builtins.open", side_effect=AssertionError("unexpected file IO")), \
             mock.patch("io.open", side_effect=AssertionError("unexpected path IO")), \
             mock.patch("socket.socket", side_effect=AssertionError("unexpected network")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("unexpected process")), \
             mock.patch("time.time", side_effect=AssertionError("unexpected clock")), \
             mock.patch("time.monotonic", side_effect=AssertionError("unexpected clock")), \
             mock.patch("os.urandom", side_effect=AssertionError("unexpected random")):
            out = function(m, a)
        self.assertEqual(out["cells"][0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
