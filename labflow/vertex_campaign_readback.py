"""Pure comparison of supplied connection records, without authority or IO."""

import hashlib
import json
import math
import re

__all__ = ["build_vertex_connection_campaign_readback"]

_PAIR = dict(scenario_id="DGM-AI-CONNECTION-001", scenario_version=1,
             evaluator_id="connection-json-v1", evaluator_version=1,
             prompt_sha256="bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230",
             schema_sha256="a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9")
_MODELS = ("gemini-4-argon", "gemini-3.8-flash")
_LEVELS = ("LOW", "MEDIUM", "HIGH")
_ORIGINS = ("actual", "mock", "replay", "unknown")
_STATES = ("success", "failed", "not_run", "unknown")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z", re.ASCII)
_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z", re.ASCII)
_PROJECT = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_EXCHANGE = re.compile(r"vertex-exchange:[0-9a-f]{32}\Z", re.ASCII)
_META = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}\Z", re.ASCII)
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+09:00\Z", re.ASCII)
_INVALID = "vertex_campaign_readback_invalid_input"
_USAGE = tuple("prompt_token_count candidates_token_count total_token_count thoughts_token_count cached_content_token_count tool_use_prompt_token_count".split())
_SETTING_KEYS = "schema_version kind profile_id profile_revision provider service project_id location quota_project_id auth_profile_id model_id thinking_level max_output_tokens timeout_seconds profile_sha256 settings_sha256".split()
_ROW_KEYS = "schema_version kind batch_id run_id row_index binding settings execution_mode status reason_code receipt strict_decode assessment budget timing".split()
_BINDING_KEYS = tuple(_PAIR) + ("profile_sha256", "settings_sha256", "matrix_sha256")
_RECEIPT_KEYS = "schema_version kind exchange_ref status failure bindings settings client request attempts response usage cost timing cancellation cleanup artifacts verification".split()
_ARTIFACTS = dict(prompt="request.json", response_schema="response-schema.json", settings="settings.json",
                  provider_request="provider-request.json", provider_response="provider-response.bin", final_text="response-text.bin")
_VERTEX_ERRORS = tuple("vertex_response_" + x for x in "invalid_input invalid_settings credential_invalid credential_quota_mismatch dependency_unavailable evidence_error auth_failed http_error response_invalid incomplete blocked limit_exceeded timeout cancelled cleanup_failed internal_error".split())
_HOSTS = dict(global_="https://aiplatform.googleapis.com", us="https://us-aiplatform.googleapis.com", eu="https://eu-aiplatform.googleapis.com")


class _Problem(ValueError):
    pass


def _require(condition, code="source_shape_invalid"):
    if not condition:
        raise _Problem(code)


def _keys(value, names):
    _require(type(value) is dict and len(value) == len(names) and
             all(type(k) is str for k in value) and set(value) == set(names))


def _integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def _number(value, low=0, high=2**63 - 1):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def _matches(value, pattern):
    return type(value) is str and pattern.fullmatch(value) is not None


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _copy(value):
    return json.loads(_canonical(value))


def _header(value, kind):
    _require(type(value["schema_version"]) is int)
    _require(value["schema_version"] == 1, "unsupported_source_version")
    _require(type(value["kind"]) is str and value["kind"] == kind)


def _pairs(items):
    out = {}
    for key, value in items:
        _require(key not in out, "invalid_source_json")
        out[key] = value
    return out


def _json_float(value):
    result = float(value)
    _require(math.isfinite(result), "invalid_source_json")
    return result


def _no_constant(value):
    raise _Problem("invalid_source_json")


def _decode(raw):
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
                           parse_float=_json_float, parse_constant=_no_constant)
        _canonical(value)  # Also rejects lone escaped surrogates and excessive nesting.
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        pass
    raise _Problem("invalid_source_json")


def _selection(manifest, artifacts):
    _keys(manifest, "schema_version kind campaign_id pair axes sources replay_links".split())
    _header(manifest, "vertex_connection_campaign_selection")
    _require(_matches(manifest["campaign_id"], _ID))
    _keys(manifest["pair"], tuple(_PAIR))
    _require(all(type(manifest["pair"][k]) is type(v) and manifest["pair"][k] == v for k, v in _PAIR.items()))
    axes = manifest["axes"]
    _keys(axes, ("model_ids", "thinking_levels"))
    for key, expected in (("model_ids", _MODELS), ("thinking_levels", _LEVELS)):
        _require(type(axes[key]) is list and len(axes[key]) == len(expected) and
                 all(type(v) is str and v == e for v, e in zip(axes[key], expected)))
    _require(type(manifest["sources"]) is list and len(manifest["sources"]) <= 32)
    _require(type(manifest["replay_links"]) is list)
    _require(type(artifacts) is dict and all(type(k) is str for k in artifacts))
    sources = {}
    for source in manifest["sources"]:
        _keys(source, "source_id format bytes sha256 generation_origin affected_cells".split())
        name = source["source_id"]
        _require(_matches(name, _ID) and name not in sources)
        _require(type(source["format"]) is str and source["format"] in ("batch", "row", "receipt"))
        _require(_integer(source["bytes"], 1, 1048576) and _matches(source["sha256"], _SHA))
        _require(type(source["generation_origin"]) is str and source["generation_origin"] in _ORIGINS)
        cells = source["affected_cells"]
        _require(type(cells) is list and len(cells) == (6 if source["format"] == "batch" else 1) and
                 all(_integer(i, 0, 5) for i in cells) and len(set(cells)) == len(cells))
        if source["format"] == "batch":
            _require(set(cells) == set(range(6)))
        sources[name] = dict(source_id=name, format=source["format"], bytes=source["bytes"],
                             sha256=source["sha256"], generation_origin=source["generation_origin"],
                             affected_cells=sorted(cells))
    _require(set(artifacts) == set(sources))
    _require(all(v is None or type(v) is bytes for v in artifacts.values()))
    _require(sum(s["bytes"] for s in sources.values()) <= 8388608 and
             sum(len(v) for v in artifacts.values() if v is not None) <= 8388608 and
             all(v is None or len(v) <= 1048576 for v in artifacts.values()))
    return sources


def _links(values):
    names = "original_source_id original_source_sha256 original_row_sha256 replay_source_id receipt_source_id exchange_ref budget_id reservation_id prompt_sha256 schema_sha256 settings_sha256".split()
    for value in values:
        _keys(value, names)
        for name in names:
            item = value[name]
            if name == "receipt_source_id" and item is None:
                continue
            _require(_matches(item, _SHA if name.endswith("sha256") else _ID))
        yield dict(value)


def _settings(value):
    _keys(value, _SETTING_KEYS)
    _header(value, "ai_run_settings")
    _require(_matches(value["profile_id"], _LABEL) and _matches(value["auth_profile_id"], _LABEL) and
             _integer(value["profile_revision"], 0, 9007199254740991))
    _require(value["provider"] == "vertex_ai" and value["service"] == "aiplatform.googleapis.com" and
             _matches(value["project_id"], _PROJECT) and value["quota_project_id"] == value["project_id"])
    _require(type(value["location"]) is str and value["location"] in ("global", "us", "eu") and
             type(value["model_id"]) is str and value["model_id"] in _MODELS and
             type(value["thinking_level"]) is str and value["thinking_level"] in _LEVELS)
    _require(_integer(value["max_output_tokens"], 64, 8192) and _number(value["timeout_seconds"], 1, 120) and
             _matches(value["profile_sha256"], _SHA) and _matches(value["settings_sha256"], _SHA))
    without_hash = {k: v for k, v in value.items() if k != "settings_sha256"}
    _require(_hash(_canonical(without_hash)) == value["settings_sha256"], "binding_mismatch")
    return _MODELS.index(value["model_id"]) * 3 + _LEVELS.index(value["thinking_level"])


def _receipt(value, setting=None):
    _keys(value, _RECEIPT_KEYS)
    _header(value, "vertex_response_receipt")
    _settings(value["settings"])
    if setting is not None:
        _require(_canonical(setting) == _canonical(value["settings"]), "binding_mismatch")
    setting = value["settings"]
    _require(_matches(value["exchange_ref"], _EXCHANGE) and value["status"] in ("complete", "failed"))
    complete = value["status"] == "complete"
    if complete:
        _require(value["failure"] is None)
    else:
        _keys(value["failure"], ("code", "phase"))
        _require(value["failure"]["code"] in _VERTEX_ERRORS and value["failure"]["phase"] in
                 "validation credentials evidence dependencies auth send collect extract cleanup".split())
    b = value["bindings"]
    _keys(b, ("prompt_sha256", "schema_sha256", "provider_payload_sha256", "settings_sha256"))
    for key, expected in (("prompt_sha256", _PAIR["prompt_sha256"]), ("schema_sha256", _PAIR["schema_sha256"]),
                          ("settings_sha256", setting["settings_sha256"])):
        _require((not complete and b[key] is None) or b[key] == expected, "binding_mismatch")
    _require(b["provider_payload_sha256"] is None or _matches(b["provider_payload_sha256"], _SHA))
    client = value["client"]
    _keys(client, ("transport", "api_version", "google_auth_version", "requests_version", "google_genai_used"))
    _require(client["transport"] == "REST" and client["api_version"] == "v1" and client["google_genai_used"] is False)
    for key, expected in (("google_auth_version", "2.62.0"), ("requests_version", "2.34.2")):
        _require(client[key] == expected or (not complete and client[key] is None))
    host = _HOSTS["global_" if setting["location"] == "global" else setting["location"]]
    request = dict(method="POST", url=host + "/v1/projects/" + setting["project_id"] + "/locations/" +
                   setting["location"] + "/publishers/google/models/" + setting["model_id"] + ":generateContent",
                   quota_project_id=setting["quota_project_id"], auth_profile_id=setting["auth_profile_id"])
    _keys(value["request"], tuple(request))
    _require(_canonical(value["request"]) == _canonical(request), "binding_mismatch")
    a = value["attempts"]
    _keys(a, "worker_process_attempts auth_refresh_attempts auth_http_attempts generation_post_attempts auth_refresh_completed auth_retry_blocked application_retries".split())
    counters = ("worker_process_attempts", "auth_refresh_attempts", "auth_http_attempts", "generation_post_attempts")
    _require(all(a[k] is None or _integer(a[k], 0, 1) for k in counters) and
             type(a["auth_refresh_completed"]) is bool and type(a["auth_retry_blocked"]) is bool and
             _integer(a["application_retries"], 0, 0))
    response = value["response"]
    _keys(response, "http_status auth_http_status finish_reason reported_model_version provider_response_id text_parts thought_parts".split())
    _require(all(response[k] is None or _integer(response[k], 100, 599) for k in ("http_status", "auth_http_status")))
    _require(all(response[k] is None or _integer(response[k]) for k in ("text_parts", "thought_parts")))
    _require(all(response[k] is None or _matches(response[k], _META) for k in ("reported_model_version", "provider_response_id")))
    _require(response["finish_reason"] is None or response["finish_reason"] in
             "STOP MAX_TOKENS SAFETY RECITATION OTHER BLOCKLIST PROHIBITED_CONTENT SPII MALFORMED_FUNCTION_CALL FINISH_REASON_UNSPECIFIED".split())
    if value["usage"] is not None:
        _keys(value["usage"], _USAGE)
        _require(all(v is None or _integer(v) for v in value["usage"].values()))
    cost = value["cost"]
    _keys(cost, ("kind", "amount", "currency", "price_version"))
    _require(_canonical(cost) == _canonical(dict(kind="not_applicable" if a["generation_post_attempts"] == 0 else "unknown",
                                                amount=None, currency=None, price_version=None)))
    timing = value["timing"]
    _keys(timing, ("timeout_seconds", "local_elapsed_seconds"))
    _require(type(timing["timeout_seconds"]) is float and timing["timeout_seconds"] == setting["timeout_seconds"] and
             (timing["local_elapsed_seconds"] is None or type(timing["local_elapsed_seconds"]) is float and
              _number(timing["local_elapsed_seconds"])))
    cancel = value["cancellation"]
    _keys(cancel, ("requested", "local_worker_stopped", "provider_completion", "remote_cancel_verified"))
    _require(type(cancel["requested"]) is bool and
             (cancel["local_worker_stopped"] is None or type(cancel["local_worker_stopped"]) is bool) and
             cancel["remote_cancel_verified"] is False and cancel["provider_completion"] in
             ("not_started", "observed_stop", "observed_incomplete", "observed_error", "unknown"))
    cleanup = value["cleanup"]
    _keys(cleanup, "worker_reaped worker_exit_code transport_handles_closed artifact_handles_closed secondary_errors remote_cancellation_verified".split())
    cleanup_flags = ("worker_reaped", "transport_handles_closed", "artifact_handles_closed")
    _require(all(cleanup[k] is None or type(cleanup[k]) is bool for k in cleanup_flags) and
             (cleanup["worker_exit_code"] is None or _integer(cleanup["worker_exit_code"], -(2**31), 2**32 - 1)) and
             cleanup["remote_cancellation_verified"] is False and type(cleanup["secondary_errors"]) is list and
             len(cleanup["secondary_errors"]) <= 16 and all(x in
             "terminate_failed kill_failed join_timeout transport_close_failed artifact_close_failed receipt_write_failed status_read_failed secondary_overflow".split()
             for x in cleanup["secondary_errors"]))
    v = value["verification"]
    _keys(v, "wire_complete credential_metadata_verified remote_identity_verified semantic_quality_verified credit_verified".split())
    _require(all(type(x) is bool for x in v.values()) and all(v[k] is False for k in
             ("remote_identity_verified", "semantic_quality_verified", "credit_verified")))
    if complete:
        _require(all(a[k] == 1 for k in counters) and a["auth_refresh_completed"] is True and
                 a["auth_retry_blocked"] is False and response["http_status"] == 200 and response["auth_http_status"] == 200 and
                 response["finish_reason"] == "STOP" and _integer(response["text_parts"], 1) and
                 cancel["requested"] is False and (cancel["local_worker_stopped"] is None or cancel["local_worker_stopped"] is True) and
                 cancel["provider_completion"] == "observed_stop" and all(cleanup[k] is True for k in cleanup_flags) and
                 cleanup["worker_exit_code"] == 0 and not cleanup["secondary_errors"] and
                 v["wire_complete"] is True and v["credential_metadata_verified"] is True)
    _keys(value["artifacts"], tuple(_ARTIFACTS))
    expected_hashes = dict(prompt=b["prompt_sha256"], response_schema=b["schema_sha256"],
                           settings=_hash(_canonical(setting)), provider_request=b["provider_payload_sha256"])
    for key, filename in _ARTIFACTS.items():
        d = value["artifacts"][key]
        _keys(d, ("path", "present", "bytes", "sha256", "complete", "overflow", "extent"))
        _require(d["path"] == filename and all(type(d[k]) is bool for k in ("present", "complete", "overflow")) and
                 d["extent"] in ("whole_file", "prefix", "absent"))
        if d["present"]:
            _require(_integer(d["bytes"], 0, 2097152) and _matches(d["sha256"], _SHA) and d["extent"] != "absent" and
                     (not d["complete"] or not d["overflow"] and d["extent"] == "whole_file"))
            expected_hash = expected_hashes.get(key)
            if expected_hash is not None:
                _require(d["sha256"] == expected_hash, "binding_mismatch")
            if key == "settings":
                _require(d["bytes"] == len(_canonical(setting)), "binding_mismatch")
        else:
            _require(_integer(d["bytes"], 0, 0) and d["sha256"] is None and d["complete"] is False and
                     d["overflow"] is False and d["extent"] == "absent")
        if complete:
            _require(d["present"] and d["complete"] and not d["overflow"] and d["extent"] == "whole_file")
    return value


def _row(value):
    _keys(value, _ROW_KEYS)
    _header(value, "vertex_comparison_row")
    _require(all(_matches(value[k], _ID) for k in ("batch_id", "run_id", "reason_code")) and
             _integer(value["row_index"], 0, 5) and value["execution_mode"] in ("actual", "replay") and value["status"] in _STATES)
    b = value["binding"]
    _keys(b, _BINDING_KEYS)
    _require(all(type(b[k]) is type(v) and b[k] == v for k, v in _PAIR.items()), "binding_mismatch")
    _require(_matches(b["profile_sha256"], _SHA) and _matches(b["matrix_sha256"], _SHA))
    s = value["settings"]
    if s is None:
        _require(value["reason_code"] == "not_selected" and value["status"] == "not_run" and b["settings_sha256"] is None)
    else:
        _require(_settings(s) == value["row_index"] and s["profile_sha256"] == b["profile_sha256"] and
                 s["settings_sha256"] == b["settings_sha256"], "binding_mismatch")
        _require(value["reason_code"] != "not_selected")
    budget = value["budget"]
    _keys(budget, ("budget_id", "reservation_id", "reserved_calls", "reserved_output_tokens", "generation_post_attempts"))
    _require(all(budget[k] is None or _matches(budget[k], _ID) for k in ("budget_id", "reservation_id")) and
             (budget["reserved_calls"] is None or _integer(budget["reserved_calls"], 0, 6)) and
             (budget["reserved_output_tokens"] is None or _integer(budget["reserved_output_tokens"], 0, 3072)) and
             (budget["generation_post_attempts"] is None or _integer(budget["generation_post_attempts"], 0, 1)))
    if budget["reservation_id"] is not None:
        _require(budget["budget_id"] is not None and s is not None and _integer(budget["reserved_calls"], 1, 6) and
                 _integer(budget["reserved_output_tokens"], s["max_output_tokens"], 3072) and
                 s["max_output_tokens"] <= 512 and s["timeout_seconds"] <= 60)
    if s is None:
        _require(value["receipt"] is None and budget["reservation_id"] is None and budget["generation_post_attempts"] == 0)
    strict = value["strict_decode"]
    _keys(strict, ("status", "evaluator_id", "error_code"))
    _require(strict["status"] in ("checked", "rejected", "not_run") and strict["evaluator_id"] == _PAIR["evaluator_id"] and
             strict["error_code"] == ("connection_response_invalid" if strict["status"] == "rejected" else None))
    _keys(value["assessment"], ("status", "verdict", "reason_code"))
    _require(_canonical(value["assessment"]) == _canonical(dict(status="not_assessed", verdict=None, reason_code="connection_only")))
    t = value["timing"]
    _keys(t, ("started_at", "finished_at", "elapsed_ms"))
    _require((t["started_at"] is None or _matches(t["started_at"], _STAMP)) and _matches(t["finished_at"], _STAMP) and _number(t["elapsed_ms"]))
    problems = set()
    rec = None
    if value["receipt"] is not None:
        try:
            _require(s is not None)
            rec = _receipt(value["receipt"], s)
            _require(rec["attempts"]["generation_post_attempts"] == budget["generation_post_attempts"], "binding_mismatch")
            if value["status"] == "success":
                _require(rec["status"] == "complete" and strict["status"] == "checked" and budget["reservation_id"] is not None)
            elif value["status"] == "failed":
                _require(budget["reservation_id"] is not None and rec["cleanup"]["worker_reaped"] is True and
                         budget["generation_post_attempts"] is not None and
                         (rec["status"] == "failed" or strict["status"] == "rejected"))
        except _Problem as error:
            problems.add(str(error))
            rec = None
    elif value["status"] in ("success", "failed") or budget["generation_post_attempts"] not in (None, 0):
        problems.add("source_shape_invalid")
    if value["status"] == "not_run" and (budget["generation_post_attempts"] != 0 or rec is not None or strict["status"] != "not_run"):
        problems.add("source_shape_invalid")
    return dict(row=value, receipt=rec, problems=problems)


def _batch(value):
    _keys(value, "schema_version kind batch_id matrix_sha256 execution_mode rows summary business_assessment".split())
    _header(value, "vertex_comparison_batch")
    _require(_matches(value["batch_id"], _ID) and _matches(value["matrix_sha256"], _SHA) and
             value["execution_mode"] == "actual" and value["business_assessment"] == "not_assessed" and
             type(value["rows"]) is list and len(value["rows"]) == 6)
    rows = [_row(r) for r in value["rows"]]
    _require({r["row"]["row_index"] for r in rows} == set(range(6)))
    _require(all(r["row"]["batch_id"] == value["batch_id"] and r["row"]["binding"]["matrix_sha256"] == value["matrix_sha256"] and
                 r["row"]["execution_mode"] == "actual" for r in rows), "binding_mismatch")
    summary = value["summary"]
    _keys(summary, "planned_rows selected_rows success_rows failed_rows not_run_rows unknown_rows cumulative_reserved_calls cumulative_reserved_output_tokens generation_post_attempts generation_post_attempts_known generation_post_attempts_unknown_rows".split())
    known = sum(r["row"]["budget"]["generation_post_attempts"] for r in rows if r["row"]["budget"]["generation_post_attempts"] is not None)
    unknown = sum(r["row"]["budget"]["generation_post_attempts"] is None for r in rows)
    expected = dict(planned_rows=6, selected_rows=sum(r["row"]["settings"] is not None for r in rows),
                    generation_post_attempts=None if unknown else known, generation_post_attempts_known=known,
                    generation_post_attempts_unknown_rows=unknown)
    expected.update({state + "_rows": sum(r["row"]["status"] == state for r in rows) for state in _STATES})
    _require(all(_canonical(summary[k]) == _canonical(v) for k, v in expected.items()))
    _require((summary["cumulative_reserved_calls"] is None or _integer(summary["cumulative_reserved_calls"], 0, 6)) and
             (summary["cumulative_reserved_output_tokens"] is None or _integer(summary["cumulative_reserved_output_tokens"], 0, 3072)))
    return rows


def _issue(state, code, names, cells):
    names = tuple(sorted(set(names) & set(state["sources"])))
    cells = tuple(sorted(set(cells)))
    state["issues"][(code, names, cells)] = dict(code=code, source_ids=list(names), affected_cells=list(cells))
    state["bad_cells"].update(cells)


def _node_origin(node):
    return next(iter(node["origins"])) if len(node["origins"]) == 1 else "unknown"


def _collect(sources, artifacts):
    state = dict(sources=sources, issues={}, bad_cells=set(), nodes={}, source_nodes={}, receipts={})
    for name, source in sorted(sources.items()):
        raw = artifacts[name]
        source["status"] = "valid"
        state["source_nodes"][name] = []
        try:
            _require(raw is not None, "missing_source")
            _require(len(raw) == source["bytes"] and _hash(raw) == source["sha256"], "source_pin_mismatch")
            value = _decode(raw)
            if source["format"] == "receipt":
                rec = _receipt(value)
                _require([_settings(rec["settings"])] == source["affected_cells"], "binding_mismatch")
                state["receipts"][name] = rec
                continue
            rows = _batch(value) if source["format"] == "batch" else [_row(value)]
            if source["format"] == "row":
                _require([rows[0]["row"]["row_index"]] == source["affected_cells"], "binding_mismatch")
            for record in rows:
                row = record["row"]
                digest = _hash(_canonical(row))
                key = (row["execution_mode"], row["batch_id"], row["run_id"], row["row_index"], digest)
                if key not in state["nodes"]:
                    state["nodes"][key] = dict(record, key=key, digest=digest, source_ids=set(), origins=set(), bad=False)
                node = state["nodes"][key]
                node["source_ids"].add(name)
                node["origins"].add(source["generation_origin"])
                state["source_nodes"][name].append(key)
                for code in node["problems"]:
                    node["bad"] = True
                    _issue(state, code, node["source_ids"], [row["row_index"]])
        except (_Problem, KeyError, TypeError, ValueError, RecursionError, OverflowError) as error:
            source["status"] = "missing" if raw is None else "invalid"
            code = str(error) if type(error) is _Problem else "source_shape_invalid"
            _issue(state, code, [name], source["affected_cells"])
    for node in state["nodes"].values():
        if len(node["origins"]) != 1:
            node["bad"] = True
            _issue(state, "binding_mismatch", node["source_ids"], [node["row"]["row_index"]])
    return state


def _connect_replays(state, links):
    targets, used = {}, set()
    nodes, sources = state["nodes"], state["sources"]
    for link in links:
        names = [link[k] for k in ("original_source_id", "replay_source_id", "receipt_source_id") if link[k] is not None]
        replay_scope = sources.get(link["replay_source_id"])
        if replay_scope is not None and replay_scope["format"] == "row":
            cells = set(replay_scope["affected_cells"])
        else:
            matched = [nodes[k]["row"]["row_index"] for k in state["source_nodes"].get(link["original_source_id"], ())
                       if nodes[k]["digest"] == link["original_row_sha256"]]
            cells = set(matched) if len(matched) == 1 else {
                i for name in names if name in sources for i in sources[name]["affected_cells"]}
        if not cells:
            cells = set(range(6))
        try:
            original_source = sources.get(link["original_source_id"])
            replay_source = sources.get(link["replay_source_id"])
            _require(original_source is not None and replay_source is not None)
            _require(original_source["status"] == "valid" and original_source["sha256"] == link["original_source_sha256"])
            originals = [nodes[k] for k in state["source_nodes"][link["original_source_id"]] if nodes[k]["digest"] == link["original_row_sha256"]]
            candidates = state["source_nodes"][link["replay_source_id"]]
            _require(len(originals) == 1 and replay_source["format"] == "row" and len(candidates) == 1)
            original, replay = originals[0], nodes[candidates[0]]
            a, b = original["row"], replay["row"]
            _require(not original["bad"] and not replay["bad"] and a["execution_mode"] == "actual" and b["execution_mode"] == "replay")
            _require(_node_origin(original) == _node_origin(replay) and original_source["generation_origin"] == replay_source["generation_origin"])
            _require(all(_canonical(a[k]) == _canonical(b[k]) for k in
                         ("schema_version", "kind", "batch_id", "run_id", "row_index", "binding", "settings", "assessment")))
            _require(all(a["budget"][k] == b["budget"][k] for k in ("budget_id", "reservation_id", "reserved_calls", "reserved_output_tokens")))
            _require(a["budget"]["reservation_id"] is not None and b["status"] != "not_run")
            _require(all(link[k] == a["budget"][k] for k in ("budget_id", "reservation_id")))
            _require(all(link[k] == a["binding"][k] for k in ("prompt_sha256", "schema_sha256", "settings_sha256")))
            rec = replay["receipt"]
            _require(rec is not None and rec["exchange_ref"] == link["exchange_ref"])
            if a["receipt"] is not None:
                _require(_canonical(a["receipt"]) == _canonical(rec))
            pointer = link["receipt_source_id"]
            _require(pointer is not None or a["receipt"] is not None)
            if pointer is not None:
                _require(pointer in state["receipts"] and sources[pointer]["generation_origin"] == _node_origin(original) and
                         sources[pointer]["affected_cells"] == [a["row_index"]] and
                         _canonical(state["receipts"][pointer]) == _canonical(rec))
            targets.setdefault(original["key"], set()).add(replay["key"])
            used.add(replay["key"])
        except _Problem:
            _issue(state, "replay_binding_mismatch", names, cells)
    for node in nodes.values():
        if node["row"]["execution_mode"] == "replay" and node["key"] not in used:
            _issue(state, "unlinked_replay", node["source_ids"], [node["row"]["row_index"]])
    for key, replay_keys in targets.items():
        if len(replay_keys) != 1:
            node = nodes[key]
            node["bad"] = True
            _issue(state, "identity_conflict", node["source_ids"] | set().union(*(nodes[k]["source_ids"] for k in replay_keys)), [node["row"]["row_index"]])
    return targets, used


def _connect_receipts(state):
    for name, rec in sorted(state["receipts"].items()):
        matches = [n for n in state["nodes"].values() if n["receipt"] is not None and _canonical(n["receipt"]) == _canonical(rec)]
        if not matches:
            _issue(state, "orphan_receipt", [name], state["sources"][name]["affected_cells"])
        for node in matches:
            if _node_origin(node) != state["sources"][name]["generation_origin"]:
                node["bad"] = True
                _issue(state, "binding_mismatch", node["source_ids"] | {name}, [node["row"]["row_index"]])
            node["origins"].add(state["sources"][name]["generation_origin"])
            node["source_ids"].add(name)


def _reservation(node):
    budget = node["row"]["budget"]
    return (budget["budget_id"], budget["reservation_id"]) if budget["reservation_id"] is not None else None


def _conflicts(state, originals, effective):
    groups = {}
    for node in originals:
        row = node["row"]
        groups.setdefault(("row", row["batch_id"], row["run_id"], row["row_index"]), []).append(node)
        reservation = _reservation(node)
        if reservation:
            groups.setdefault(("reservation",) + reservation, []).append(node)
        rec = effective[node["key"]]["receipt"]
        if rec is not None:
            groups.setdefault(("exchange", rec["exchange_ref"]), []).append(node)
    for key, group in groups.items():
        if len(group) < 2:
            continue
        for node in group:
            node["bad"] = True
        _issue(state, "identity_conflict", set().union(*(n["source_ids"] for n in group)), [n["row"]["row_index"] for n in group])
    receipt_groups = {}
    for node in state["nodes"].values():
        if node["receipt"] is not None:
            receipt_groups.setdefault(node["receipt"]["exchange_ref"], []).append((node["receipt"], node["source_ids"], node["row"]["row_index"]))
    for name, rec in state["receipts"].items():
        receipt_groups.setdefault(rec["exchange_ref"], []).append((rec, {name}, state["sources"][name]["affected_cells"][0]))
    for group in receipt_groups.values():
        if len({_hash(_canonical(rec)) for rec, names, index in group}) > 1:
            names = set().union(*(names for rec, names, index in group))
            cells = {index for rec, names, index in group}
            _issue(state, "identity_conflict", names, cells)
            for node in originals:
                if node["source_ids"] & names:
                    node["bad"] = True


def _attempt_key(node):
    return ("reservation",) + _reservation(node) if _reservation(node) else ("row",) + node["key"][1:4]


def _metadata(node, effective):
    row, final = node["row"], effective["row"]
    rec = None if node["bad"] else effective["receipt"]
    status = "unknown" if node["bad"] else final["status"]
    version = None if rec is None else rec["response"]["reported_model_version"]
    if version is not None and (re.match(r"[A-Za-z]:/", version) or version.lower().startswith("file:")):
        version = None
    return dict(source_ids=sorted(node["source_ids"] | effective["source_ids"]), batch_id=row["batch_id"], run_id=row["run_id"],
                original_status=row["status"], effective_status=status, reason_code=row["reason_code"],
                interpretation_source="provided_row_replay" if effective is not node else "original",
                original_execution_mode=row["execution_mode"], replay_execution_mode=None if effective is node else "replay",
                generation_origin=_node_origin(node), requested_model_id=None if row["settings"] is None else row["settings"]["model_id"],
                reported_model_version=version, budget_id=row["budget"]["budget_id"], reservation_id=row["budget"]["reservation_id"],
                exchange_ref=None if rec is None else rec["exchange_ref"], original_generation_post_attempts=row["budget"]["generation_post_attempts"],
                generation_post_attempts=None if node["bad"] else final["budget"]["generation_post_attempts"],
                budget_snapshots=[dict(source_ids=sorted(node["source_ids"]), reserved_calls=row["budget"]["reserved_calls"],
                                       reserved_output_tokens=row["budget"]["reserved_output_tokens"])],
                usage=None if rec is None else _copy(rec["usage"]),
                cost=dict(kind="unknown", amount=None, currency=None, price_version=None) if rec is None else _copy(rec["cost"]))


def _totals(originals, effective, incomplete):
    reservations = {}
    known = 0
    exchanges = {}
    unknown_records = 0
    for node in originals:
        setting = node["row"]["settings"]
        res = _reservation(node)
        if res and setting is not None:
            reservations.setdefault(res, set()).add(setting["max_output_tokens"])
        final = effective[node["key"]]
        rec = final["receipt"]
        count = None if node["bad"] else final["row"]["budget"]["generation_post_attempts"]
        if count is None:
            unknown_records += 1
        elif not node["bad"]:
            known += count
        if rec is not None:
            exchanges[rec["exchange_ref"]] = None if node["bad"] else rec["usage"]
    usage = {}
    for field in _USAGE:
        values = [None if item is None else item[field] for item in exchanges.values()]
        subtotal = sum(v for v in values if v is not None)
        unknown = sum(v is None for v in values)
        usage[field] = dict(known_subtotal=subtotal, unknown_exchange_count=unknown,
                            total=None if incomplete or unknown_records or unknown or not exchanges else subtotal)
    return dict(observed_attempts=len({_attempt_key(n) for n in originals}), observed_reservations=len(reservations),
                reserved_output_tokens_known=sum(next(iter(caps)) for caps in reservations.values() if len(caps) == 1),
                generation_post_attempts_known=known, generation_post_attempts_unknown_records=unknown_records,
                generation_post_attempts=None if incomplete or unknown_records else known, usage=usage,
                cost=dict(kind="unknown", amount=None, currency=None, price_version=None), ledger_balance=None, remaining_capacity=None)


def build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict:
    """Compare supplied snapshots; never read files or verify execution authority."""
    invalid = False
    try:
        sources = _selection(manifest, artifacts)
        # Validate the flat link shape before interpreting any source.
        for unused in _links(manifest["replay_links"]):
            pass
    except (_Problem, KeyError, TypeError, ValueError, RecursionError, OverflowError):
        invalid = True
    if invalid:
        raise ValueError(_INVALID) from None
    state = _collect(sources, artifacts)
    targets, linked = _connect_replays(state, _links(manifest["replay_links"]))
    _connect_receipts(state)
    originals = sorted((n for n in state["nodes"].values() if n["row"]["execution_mode"] == "actual"), key=lambda n: n["key"])
    effective = {n["key"]: state["nodes"][next(iter(targets[n["key"]]))] if len(targets.get(n["key"], ())) == 1 else n for n in originals}
    for original in originals:
        final = effective[original["key"]]
        original["origins"].update(final["origins"])
        if final["bad"]:
            original["bad"] = True
    _conflicts(state, originals, effective)
    cells = []
    attempted = []
    for index in range(6):
        history, coverage, attempts = [], [], []
        for node in originals:
            row = node["row"]
            if row["row_index"] != index:
                continue
            if row["status"] == "not_run" and _reservation(node) is None and row["receipt"] is None:
                coverage.append(dict(source_ids=sorted(node["source_ids"]), batch_id=row["batch_id"], run_id=row["run_id"],
                                     reason_code=row["reason_code"], generation_origin=_node_origin(node)))
            else:
                attempts.append(node)
                history.append(_metadata(node, effective[node["key"]]))
        attempted.extend(attempts)
        if len({_attempt_key(n) for n in attempts}) > 1:
            _issue(state, "multiple_attempts", set().union(*(n["source_ids"] for n in attempts)), [index])
        for node in sorted(state["nodes"].values(), key=lambda n: n["key"]):
            if node["row"]["row_index"] == index and node["row"]["execution_mode"] == "replay" and node["key"] not in linked:
                history.append(dict(source_ids=sorted(node["source_ids"]), original_status=None,
                                    effective_status="unknown", interpretation_source="provided_row_replay",
                                    generation_origin=_node_origin(node), replay_execution_mode="replay"))
        if index in state["bad_cells"]:
            status = "unknown"
        elif len(history) == 1:
            status = history[0]["effective_status"]
        elif coverage and not history:
            status = "not_run"
        else:
            status = "unknown"
        if not history and not coverage and index not in state["bad_cells"]:
            _issue(state, "absent_cell", [], [index])
        cells.append(dict(row_index=index, model_id=_MODELS[index // 3], thinking_level=_LEVELS[index % 3],
                          status=status, history=history, not_run_observations=coverage, issues=[]))
    issues = [state["issues"][k] for k in sorted(state["issues"])]
    for cell in cells:
        cell["issues"] = [i for i in issues if cell["row_index"] in i["affected_cells"]]
    incomplete = any(c["status"] == "unknown" for c in cells)
    totals = _totals(attempted, effective, incomplete)
    totals["new_actual_calls"] = 0
    unknown_origin = any(_node_origin(n) == "unknown" for n in attempted)
    totals["by_generation_origin"] = {origin: _totals([n for n in attempted if _node_origin(n) == origin], effective,
                                                      incomplete or unknown_origin) for origin in _ORIGINS}
    return dict(schema_version=1, kind="vertex_connection_campaign_readback", campaign_id=manifest["campaign_id"],
                pair=dict(_PAIR), cells=cells, totals=totals,
                sources=[_copy(sources[k]) for k in sorted(sources)], issues=issues,
                assurance=dict(basis="provided_records_only", root_authorization_verified=False, underlying_artifacts_verified=False))
