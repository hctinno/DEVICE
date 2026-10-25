"""Bounded Vertex connection comparison; no transport, credential storage or UI.

The host owns approval/ADC/budget paths. This module never seeds a budget or
refunds a reservation. Only the registered synthetic connection pair is admitted.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

__all__ = ["build_vertex_comparison_matrix", "run_vertex_comparison_row",
           "run_vertex_comparison_batch", "ModelComparisonError"]

_PROJECT = "project-a6310591-f8cc-487c-9e3"
_MODELS = ("gemini-4-argon", "gemini-3.8-flash")
_LEVELS = ("LOW", "MEDIUM", "HIGH")
_HOSTS = {"global":"https://aiplatform.googleapis.com",
          "us":"https://aiplatform.us.rep.googleapis.com",
          "eu":"https://aiplatform.eu.rep.googleapis.com"}
_SCENARIO, _EVALUATOR = "DGM-AI-CONNECTION-001", "connection-json-v1"
_PROMPT_SHA = "bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230"
_SCHEMA_SHA = "a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9"
_LIMITS = dict(generation_posts=6, max_output_tokens=512, reserved_output_tokens=3072,
               timeout_seconds=60, wall_seconds=300, retries=0, continuations=0)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_META = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}\Z", re.ASCII)
_PREFIX = "model_comparison_"
_CODES = frozenset(("invalid_input","limit_exceeded","state_error","dependency_unavailable"))
_VERTEX_CODES = frozenset("invalid_input invalid_settings credential_invalid credential_quota_mismatch dependency_unavailable evidence_error auth_failed http_error response_invalid incomplete blocked limit_exceeded timeout cancelled cleanup_failed internal_error".split())
_PROFILE_KEYS = set("schema_version profile_id provider project_id location quota_project_id auth_profile_id selected_model models revision".split())
_SETTINGS_KEYS = set("schema_version kind profile_id profile_revision provider service project_id location quota_project_id auth_profile_id model_id thinking_level max_output_tokens timeout_seconds profile_sha256 settings_sha256".split())
_MATRIX_KEYS = set("schema_version kind batch_id scenario_id evaluator_id profile binding limits rows selection matrix_sha256".split())
_APPROVAL_KEYS = set("schema_version kind approval_id scope_id budget_id project_id quota_project_id auth_profile_id scenario_id evaluator_id prompt_sha256 response_schema_sha256 execution_mode trial limits issued_at expires_at".split())
_BUDGET_KEYS = set("schema_version kind budget_id project_id revision call_limit output_token_limit reserved_calls reserved_output_tokens active_run_id entries".split())
_ENTRY_KEYS = set("reservation_id batch_id run_id row_index matrix_sha256 settings_sha256 output_tokens state record_ref receipt_ref".split())
_RECEIPT_KEYS = set("schema_version kind exchange_ref status failure bindings settings client request attempts response usage cost timing cancellation cleanup artifacts verification".split())
_ARTIFACTS = {"prompt":"request.json", "response_schema":"response-schema.json",
              "settings":"settings.json", "provider_request":"provider-request.json",
              "provider_response":"provider-response.bin", "final_text":"response-text.bin"}
_KST = timezone(timedelta(hours=9))


class ModelComparisonError(ValueError):
    def __init__(self, code):
        suffix = code.removeprefix(_PREFIX) if type(code) is str else "invalid_input"
        self.code = _PREFIX + (suffix if suffix in _CODES else "invalid_input")
        super().__init__(self.code)
        self.__suppress_context__ = True


def _fail(code="invalid_input"):
    try:
        raise ModelComparisonError(code) from None
    except ModelComparisonError as error:
        error.__context__ = error.__cause__ = None
        raise


def _C(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _H(raw):
    return hashlib.sha256(raw).hexdigest()


def _snapshot(value, cap=131072):
    nodes = used = 0
    active = set()
    def consume(amount):
        nonlocal used
        used += amount
        if used > cap:
            _fail("limit_exceeded")
    def string(v):
        if len(v)+2 > cap-used:
            _fail("limit_exceeded")
        consume(2)
        for c in v:
            point = ord(c)
            if 0xD800 <= point <= 0xDFFF:
                _fail()
            if c in '"\\\b\f\n\r\t':
                consume(2)
            elif point < 32:
                consume(6)
            else:
                consume(1 if point<128 else 2 if point<2048 else 3 if point<65536 else 4)
        return v
    def walk(v, depth):
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 200000:
            _fail("limit_exceeded")
        t = type(v)
        if t in (dict, list):
            if id(v) in active:
                _fail()
            if len(v)*(2 if t is dict else 1) > 200000 - nodes:
                _fail("limit_exceeded")
            active.add(id(v))
            try:
                consume(2+max(0,len(v)-1)+(len(v) if t is dict else 0))
                if t is list:
                    return [walk(x, depth+1) for x in v]
                if any(type(k) is not str for k in v):
                    _fail()
                return {walk(k, depth+1):walk(x, depth+1) for k,x in v.items()}
            finally:
                active.remove(id(v))
        if t is str:
            return string(v)
        elif t is int:
            if not -(2**63) <= v < 2**63:
                _fail("limit_exceeded")
        elif t is float:
            if not math.isfinite(v):
                _fail()
        elif t is not bool and v is not None:
            _fail()
        consume(len(_C(v)))
        return v
    result = walk(value, 0)
    if len(_C(result)) != used:
        _fail("state_error")
    return result


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _fail()


def _integer(v, low=0, high=2**63-1):
    return type(v) is int and low <= v <= high


def _identifier(v):
    return type(v) is str and _ID.fullmatch(v) is not None


def _hash(v):
    return type(v) is str and _SHA.fullmatch(v) is not None


def _number(v, low, high):
    return type(v) in (int,float) and math.isfinite(v) and low <= v <= high


def _dependency(name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name not in (name, name.split(".")[0]):
            raise
    _fail("dependency_unavailable")


def _pair(prompt, schema, scenario, evaluator):
    if (type(prompt) is not bytes or type(schema) is not bytes or
        len(prompt) != 639 or len(schema) != 321 or
        _H(prompt) != _PROMPT_SHA or _H(schema) != _SCHEMA_SHA or
        type(scenario) is not str or scenario != _SCENARIO or
        type(evaluator) is not str or evaluator != _EVALUATOR):
        _fail()


def _options(options):
    _keys(options, ("thinking_level","max_output_tokens","timeout_seconds"))
    if (options["thinking_level"] not in _LEVELS or
        not _integer(options["max_output_tokens"],64,8192) or
        not _number(options["timeout_seconds"],1,120)):
        _fail()


def _profile(value):
    p = _snapshot(value)
    _keys(p, _PROFILE_KEYS)
    if (type(p["schema_version"]) is not int or p["schema_version"] != 1 or
        p["provider"] != "vertex_ai" or p["project_id"] != _PROJECT or
        p["quota_project_id"] != _PROJECT or type(p["location"]) is not str or
        p["location"] not in _HOSTS or
        not _identifier(p["profile_id"]) or not _identifier(p["auth_profile_id"]) or
        p["selected_model"] not in _MODELS or not _integer(p["revision"])):
        _fail()
    _keys(p["models"], _MODELS)
    for options in p["models"].values():
        _options(options)
    return p


def _settings(value, p, model, overrides):
    s = _snapshot(value)
    _keys(s, _SETTINGS_KEYS)
    expected = dict(p["models"][model])
    expected.update({} if overrides is None else overrides)
    expected.update(schema_version=1,kind="ai_run_settings",profile_id=p["profile_id"],
        profile_revision=p["revision"],provider="vertex_ai",service="aiplatform.googleapis.com",
        project_id=_PROJECT,location=p["location"],quota_project_id=_PROJECT,
        auth_profile_id=p["auth_profile_id"],model_id=model,profile_sha256=_H(_C(p)))
    expected["settings_sha256"] = _H(_C(expected))
    if _C(expected) != _C(s):
        _fail("state_error")
    return s


def build_vertex_comparison_matrix(profile, prompt_bytes, response_schema_bytes, *,
        batch_id, scenario_id, evaluator_id, selection="matrix", model_id=None, overrides=None):
    _pair(prompt_bytes,response_schema_bytes,scenario_id,evaluator_id)
    if not _identifier(batch_id) or type(selection) is not str or selection not in ("matrix","selected"):
        _fail()
    p = _profile(profile)
    if model_id is not None and (type(model_id) is not str or model_id not in _MODELS):
        _fail()
    o = None if overrides is None else _snapshot(overrides)
    allowed = ("max_output_tokens","timeout_seconds") if selection == "matrix" else (
               "thinking_level","max_output_tokens","timeout_seconds")
    if o is not None and (type(o) is not dict or set(o)-set(allowed)):
        _fail()
    if selection == "matrix" and model_id is not None:
        _fail()
    if o is not None:
        for m in _MODELS:
            _options(dict(p["models"][m],**o))
    d1 = _dependency("labflow.ai_connection_profiles")
    rows = []
    selected = list(range(6))
    if selection == "selected":
        m = p["selected_model"] if model_id is None else model_id
        s = _settings(d1.resolve_run_settings(_snapshot(p),model_id=model_id,
                     overrides=None if o is None else _snapshot(o)),p,m,o)
        selected = [_MODELS.index(m)*3 + _LEVELS.index(s["thinking_level"])]
    for index in range(6):
        settings = None
        if selection == "matrix":
            m,level = _MODELS[index//3],_LEVELS[index%3]
            changes = dict({} if o is None else o,thinking_level=level)
            settings = _settings(d1.resolve_run_settings(_snapshot(p),model_id=m,
                                  overrides=changes),p,m,changes)
        elif index in selected:
            settings = _snapshot(s)
        run_id = "vertex-run:" + _H(_C(dict(batch_id=batch_id,row_index=index)))
        rows.append(dict(row_index=index,run_id=run_id,settings=settings))
    result = dict(schema_version=1,kind="vertex_comparison_matrix",batch_id=batch_id,
        scenario_id=scenario_id,evaluator_id=evaluator_id,profile=p,
        binding=dict(profile_sha256=_H(_C(p)),prompt_sha256=_H(prompt_bytes),
                     response_schema_sha256=_H(response_schema_bytes)),
        limits=dict(_LIMITS),rows=rows,
        selection=dict(mode=selection,model_id=model_id,overrides=o,row_indexes=selected))
    result["matrix_sha256"] = _H(_C(result))
    return _snapshot(result)


def _matrix(matrix, prompt, schema):
    m = _snapshot(matrix)
    _keys(m, _MATRIX_KEYS)
    _keys(m["selection"], ("mode","model_id","overrides","row_indexes"))
    expected = build_vertex_comparison_matrix(m["profile"],prompt,schema,
        batch_id=m["batch_id"],scenario_id=m["scenario_id"],evaluator_id=m["evaluator_id"],
        selection=m["selection"]["mode"],model_id=m["selection"]["model_id"],
        overrides=m["selection"]["overrides"])
    if _C(m) != _C(expected):
        _fail()
    return expected


def _path(path):
    if type(path) is not type(Path()) or not path.is_absolute():
        _fail()
    if os.name == "nt" and (len(path.drive) != 2 or path.drive[1] != ":"):
        _fail()
    for part in path.parts[1:]:
        if (part in (".","..") or "~" in part or ":" in part or part.endswith(("."," ")) or
            re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?",part,re.IGNORECASE)):
            _fail()
    for p in (path,*path.parents):
        try:
            s = p.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(s.st_mode) or
            getattr(s,"st_file_attributes",0) & getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",1024)):
            _fail()
        if stat.S_ISREG(s.st_mode) and s.st_nlink != 1:
            _fail()
    if os.path.normcase(str(path.resolve())) != os.path.normcase(str(path)):
        _fail()
    return path


def _read(path, cap):
    _path(path)
    flags = os.O_RDONLY | getattr(os,"O_BINARY",0) | getattr(os,"O_NOFOLLOW",0)
    with os.fdopen(os.open(path,flags),"rb") as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > cap:
            _fail("state_error")
        raw = f.read(cap+1)
    if len(raw) > cap:
        _fail("limit_exceeded")
    return raw


def _json(raw):
    def pairs(items):
        result = {}
        for k,v in items:
            if k in result:
                raise ValueError()
            result[k] = v
        return result
    try:
        value = json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError,ValueError,RecursionError):
        _fail()
    return _snapshot(value,1048576)


def _time(value):
    if type(value) is not str or len(value) > 64:
        _fail()
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        _fail()
    if result.tzinfo is None:
        _fail()
    return result


def _approval(path, matrix):
    a = _json(_read(path,16384))
    _keys(a, _APPROVAL_KEYS)
    p = matrix["profile"]
    if (type(a["schema_version"]) is not int or a["schema_version"] != 1 or
        a["kind"] != "vertex_comparison_approval" or
        not all(_identifier(a[k]) for k in ("approval_id","scope_id","budget_id")) or
        a["project_id"] != p["project_id"] or a["quota_project_id"] != p["quota_project_id"] or
        a["auth_profile_id"] != p["auth_profile_id"] or
        a["scenario_id"] != _SCENARIO or a["evaluator_id"] != _EVALUATOR or
        a["prompt_sha256"] != _PROMPT_SHA or a["response_schema_sha256"] != _SCHEMA_SHA or
        a["execution_mode"] != "actual" or _C(a["limits"]) != _C(_LIMITS)):
        _fail("state_error")
    trial = a["trial"]
    _keys(trial, ("status","source","observed_at","credit_amount","credit_currency","remaining_days"))
    if (trial["status"] != "confirmed" or trial["source"] != "root_console" or
        type(trial["credit_amount"]) is not str or len(trial["credit_amount"]) > 32 or
        re.fullmatch(r"[0-9]+(\.[0-9]+)?",trial["credit_amount"],re.ASCII) is None or
        not any(c in "123456789" for c in trial["credit_amount"]) or
        trial["credit_currency"] != "KRW" or not _integer(trial["remaining_days"],1,90)):
        _fail("state_error")
    issued,expires,observed = _time(a["issued_at"]),_time(a["expires_at"]),_time(trial["observed_at"])
    now = datetime.now(timezone.utc)
    if not (observed <= now and observed <= issued+timedelta(minutes=5) and
            issued <= now < expires and timedelta(0) < expires-issued <= timedelta(hours=24) and
            now-observed <= timedelta(hours=24)):
        _fail("state_error")
    return a


def _budget(path, approval):
    raw = _read(path,65536)
    b = _json(raw)
    _keys(b, _BUDGET_KEYS)
    if (type(b["schema_version"]) is not int or b["schema_version"] != 1 or
        b["kind"] != "vertex_comparison_budget" or b["budget_id"] != approval["budget_id"] or
        b["project_id"] != _PROJECT or not _integer(b["revision"]) or
        not _integer(b["call_limit"],6,6) or not _integer(b["output_token_limit"],3072,3072) or
        not _integer(b["reserved_calls"],0,6) or not _integer(b["reserved_output_tokens"],0,3072) or
        type(b["entries"]) is not list or len(b["entries"]) != b["reserved_calls"]):
        _fail("state_error")
    runs,reservations = set(),set()
    total = 0
    active = []
    for e in b["entries"]:
        _keys(e, _ENTRY_KEYS)
        if (not all(_identifier(e[k]) for k in ("reservation_id","batch_id","run_id")) or
            not _integer(e["row_index"],0,5) or
            not all(_hash(e[k]) for k in ("matrix_sha256","settings_sha256")) or
            not _integer(e["output_tokens"],64,512) or
            e["state"] not in ("reserved","complete","failed","unknown") or
            e["run_id"] in runs or e["reservation_id"] in reservations or
            any(v is not None and (type(v) is not str or len(v)>256)
                for v in (e["record_ref"],e["receipt_ref"]))):
            _fail("state_error")
        runs.add(e["run_id"]); reservations.add(e["reservation_id"]); total += e["output_tokens"]
        if e["state"] in ("reserved","unknown"):
            active.append(e["run_id"])
    if total != b["reserved_output_tokens"] or b["revision"] < len(b["entries"]):
        _fail("state_error")
    if (b["active_run_id"] is not None and not _identifier(b["active_run_id"]) or
        active != ([] if b["active_run_id"] is None else [b["active_run_id"]])):
        _fail("state_error")
    return b,raw


@contextmanager
def _locked(path):
    lock = path.with_name(path.name+".lock")
    _path(lock)
    fd = os.open(lock,os.O_RDWR|os.O_CREAT|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0),0o600)
    locked = False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail("state_error")
        if info.st_size == 0:
            os.write(fd,b"0"); os.fsync(fd)
        os.lseek(fd,0,0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            locked = True
        except OSError:
            _fail("state_error")
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)


def _replace_budget(path, b, original):
    raw = _C(b)
    if len(raw) > 65536 or _read(path,65536) != original:
        _fail("state_error")
    temp = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    with temp.open("xb") as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    # Compare under the same OS lock immediately before the replace.
    if _read(path,65536) != original:
        _fail("state_error")
    _path(path)
    os.replace(temp,path)
    if os.name != "nt":
        fd = os.open(path.parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _reserve(path, approval, matrix, row):
    with _locked(path):
        b,raw = _budget(path,approval)
        if any(e["run_id"] == row["run_id"] for e in b["entries"]):
            return None,"run_already_reserved",b
        if b["active_run_id"] is not None:
            return None,"budget_busy",b
        tokens = row["settings"]["max_output_tokens"]
        if b["reserved_calls"] >= 6 or b["reserved_output_tokens"]+tokens > 3072:
            return None,"budget_rejected",b
        e = dict(reservation_id="reserve:"+uuid.uuid4().hex,batch_id=matrix["batch_id"],
            run_id=row["run_id"],row_index=row["row_index"],matrix_sha256=matrix["matrix_sha256"],
            settings_sha256=row["settings"]["settings_sha256"],output_tokens=tokens,
            state="reserved",record_ref=None,receipt_ref=None)
        b["entries"].append(e)
        b.update(revision=b["revision"]+1,reserved_calls=b["reserved_calls"]+1,
                 reserved_output_tokens=b["reserved_output_tokens"]+tokens,active_run_id=row["run_id"])
        _replace_budget(path,b,raw)
    return e,None,b


def _finish(path, approval, reservation, record, record_hash):
    with _locked(path):
        b,raw = _budget(path,approval)
        found = [e for e in b["entries"] if e["reservation_id"] == reservation["reservation_id"]]
        if len(found) != 1 or found[0] != reservation or b["active_run_id"] != record["run_id"]:
            _fail("state_error")
        e = found[0]
        e["state"] = "complete" if record["status"] == "success" else (
                     "unknown" if record["status"] == "unknown" else "failed")
        e["record_ref"] = "sha256:"+record_hash
        e["receipt_ref"] = None if record["receipt"] is None else record["receipt"]["exchange_ref"]
        if e["state"] != "unknown":
            b["active_run_id"] = None
        b["revision"] += 1
        _replace_budget(path,b,raw)


def _credentials(value, settings):
    d = _snapshot(value)
    expected = dict(schema_version=1,kind="vertex_credentials_metadata",
        settings_sha256=settings["settings_sha256"],auth_profile_id=settings["auth_profile_id"],
        credential_type="authorized_user",quota_project_id=settings["quota_project_id"],
        token_endpoint="https://oauth2.googleapis.com/token",metadata_valid=True,
        refresh_attempted=False,model_access_verified=False,credit_status_verified=False)
    if _C(d) != _C(expected):
        _fail("state_error")


def _nullable_int(v):
    return v is None or _integer(v)


def _payload(prompt,schema,settings):
    wrapper = _C(dict(prompt_dto_utf8=prompt.decode("utf-8"),
                      response_schema_utf8=schema.decode("utf-8"))).decode("utf-8")
    return _C(dict(contents=[dict(role="user",parts=[dict(text=wrapper)])],
        generationConfig=dict(maxOutputTokens=settings["max_output_tokens"],
              thinkingConfig=dict(thinkingLevel=settings["thinking_level"]))))


def _receipt(value, settings, prompt, schema, directory, raw, success, error_code=None):
    if success and (type(raw) is not bytes or len(raw)>2097152):
        _fail()
    r = _snapshot(value,1048576)
    _keys(r,_RECEIPT_KEYS)
    if (type(r["schema_version"]) is not int or r["schema_version"] != 1 or
        r["kind"] != "vertex_response_receipt" or type(r["exchange_ref"]) is not str or
        re.fullmatch(r"vertex-exchange:[0-9a-f]{32}",r["exchange_ref"],re.ASCII) is None or
        r["status"] != ("complete" if success else "failed") or _C(r["settings"]) != _C(settings)):
        _fail()
    if success:
        if r["failure"] is not None:
            _fail()
    else:
        _keys(r["failure"],("code","phase"))
        if (r["failure"]["code"] != error_code or
            r["failure"]["phase"] not in "validation credentials evidence dependencies auth send collect extract cleanup".split()):
            _fail()
    _keys(r["bindings"],("prompt_sha256","schema_sha256","provider_payload_sha256","settings_sha256"))
    for key,expected in (("prompt_sha256",_H(prompt)),("schema_sha256",_H(schema)),
                         ("settings_sha256",settings["settings_sha256"])):
        if r["bindings"][key] != expected and (success or r["bindings"][key] is not None):
            _fail()
    if r["bindings"]["provider_payload_sha256"] is not None and not _hash(r["bindings"]["provider_payload_sha256"]):
        _fail()
    _keys(r["client"],("transport","api_version","google_auth_version","requests_version","google_genai_used"))
    c = r["client"]
    if (c["transport"] != "REST" or c["api_version"] != "v1" or c["google_genai_used"] is not False or
        any(c[k] is not None and c[k] != expected for k,expected in (
            ("google_auth_version","2.62.0"),("requests_version","2.34.2")))):
        _fail()
    _keys(r["request"],("method","url","quota_project_id","auth_profile_id"))
    url = _HOSTS[settings["location"]]+"/v1/projects/"+_PROJECT+"/locations/"+settings["location"]+"/publishers/google/models/"+settings["model_id"]+":generateContent"
    if _C(r["request"]) != _C(dict(method="POST",url=url,quota_project_id=_PROJECT,auth_profile_id=settings["auth_profile_id"])):
        _fail()
    a = r["attempts"]
    _keys(a,("worker_process_attempts","auth_refresh_attempts","auth_http_attempts","generation_post_attempts",
             "auth_refresh_completed","auth_retry_blocked","application_retries"))
    for key in ("worker_process_attempts","auth_refresh_attempts","auth_http_attempts","generation_post_attempts"):
        if a[key] is not None and not _integer(a[key],0,1):
            _fail()
    if (type(a["auth_refresh_completed"]) is not bool or type(a["auth_retry_blocked"]) is not bool or
        not _integer(a["application_retries"],0,0)):
        _fail()
    response = r["response"]
    _keys(response,("http_status","auth_http_status","finish_reason","reported_model_version",
                    "provider_response_id","text_parts","thought_parts"))
    for key in ("http_status","auth_http_status"):
        if response[key] is not None and not _integer(response[key],100,599):
            _fail()
    for key in ("text_parts","thought_parts"):
        if not _nullable_int(response[key]):
            _fail()
    for key in ("reported_model_version","provider_response_id"):
        if response[key] is not None and (type(response[key]) is not str or not _META.fullmatch(response[key])):
            _fail()
    if response["finish_reason"] is not None and response["finish_reason"] not in (
        "STOP","MAX_TOKENS","SAFETY","RECITATION","OTHER","BLOCKLIST","PROHIBITED_CONTENT",
        "SPII","MALFORMED_FUNCTION_CALL","FINISH_REASON_UNSPECIFIED"):
        _fail()
    if r["usage"] is not None:
        _keys(r["usage"],("prompt_token_count","candidates_token_count","total_token_count",
              "thoughts_token_count","cached_content_token_count","tool_use_prompt_token_count"))
        if any(not _nullable_int(v) for v in r["usage"].values()):
            _fail()
    _keys(r["cost"],("kind","amount","currency","price_version"))
    expected_cost = "not_applicable" if a["generation_post_attempts"] == 0 else "unknown"
    if _C(r["cost"]) != _C(dict(kind=expected_cost,amount=None,currency=None,price_version=None)):
        _fail()
    _keys(r["timing"],("timeout_seconds","local_elapsed_seconds"))
    t = r["timing"]
    if (type(t["timeout_seconds"]) is not float or t["timeout_seconds"] != settings["timeout_seconds"] or
        t["local_elapsed_seconds"] is not None and
        (type(t["local_elapsed_seconds"]) is not float or not _number(t["local_elapsed_seconds"],0,2**63-1))):
        _fail()
    _keys(r["cancellation"],("requested","local_worker_stopped","provider_completion","remote_cancel_verified"))
    cancel = r["cancellation"]
    if (type(cancel["requested"]) is not bool or cancel["local_worker_stopped"] is not None and
        type(cancel["local_worker_stopped"]) is not bool or cancel["remote_cancel_verified"] is not False or
        cancel["provider_completion"] not in ("not_started","observed_stop","observed_incomplete","observed_error","unknown")):
        _fail()
    cleanup = r["cleanup"]
    _keys(cleanup,("worker_reaped","worker_exit_code","transport_handles_closed","artifact_handles_closed",
                  "secondary_errors","remote_cancellation_verified"))
    if (any(cleanup[k] is not None and type(cleanup[k]) is not bool for k in (
        "worker_reaped","transport_handles_closed","artifact_handles_closed")) or
        cleanup["worker_exit_code"] is not None and not _integer(cleanup["worker_exit_code"],-(2**31),2**32-1) or
        cleanup["remote_cancellation_verified"] is not False or type(cleanup["secondary_errors"]) is not list or
        len(cleanup["secondary_errors"])>16 or any(x not in (
        "terminate_failed","kill_failed","join_timeout","transport_close_failed","artifact_close_failed",
        "receipt_write_failed","status_read_failed","secondary_overflow") for x in cleanup["secondary_errors"])):
        _fail()
    v = r["verification"]
    _keys(v,("wire_complete","credential_metadata_verified","remote_identity_verified",
             "semantic_quality_verified","credit_verified"))
    if (any(type(x) is not bool for x in v.values()) or
        any(v[k] is not False for k in ("remote_identity_verified","semantic_quality_verified","credit_verified"))):
        _fail()
    if success and (any(a[k] != 1 for k in ("worker_process_attempts","auth_refresh_attempts","auth_http_attempts","generation_post_attempts")) or
        a["auth_refresh_completed"] is not True or a["auth_retry_blocked"] is not False or
        response["http_status"] != 200 or response["auth_http_status"] != 200 or
        response["finish_reason"] != "STOP" or
        not _integer(response["text_parts"],1) or
        cancel["requested"] is not False or cancel["local_worker_stopped"] is not True or
        cancel["provider_completion"] != "observed_stop" or
        any(cleanup[k] is not True for k in ("worker_reaped","transport_handles_closed","artifact_handles_closed")) or
        cleanup["worker_exit_code"] != 0 or cleanup["secondary_errors"] != [] or
        v["wire_complete"] is not True or v["credential_metadata_verified"] is not True or
        c["google_auth_version"] != "2.62.0" or c["requests_version"] != "2.34.2"):
        _fail()
    _keys(r["artifacts"],_ARTIFACTS)
    expected_blobs = dict(prompt=prompt,response_schema=schema,settings=_C(settings),
                         provider_request=_payload(prompt,schema,settings))
    for key,filename in _ARTIFACTS.items():
        desc = r["artifacts"][key]
        _keys(desc,("path","present","bytes","sha256","complete","overflow","extent"))
        if (desc["path"] != filename or type(desc["present"]) is not bool or
            type(desc["complete"]) is not bool or type(desc["overflow"]) is not bool or
            desc["extent"] not in ("whole_file","prefix","absent")):
            _fail()
        if desc["present"]:
            if not _integer(desc["bytes"],0,2097152) or not _hash(desc["sha256"]):
                _fail()
            b = _read(directory/filename,2097152)
            if len(b) != desc["bytes"] or _H(b) != desc["sha256"]:
                _fail()
            if desc["extent"] == "absent" or desc["complete"] and (desc["overflow"] or desc["extent"] != "whole_file"):
                _fail()
            if key in expected_blobs and b != expected_blobs[key]:
                _fail()
            if key == "provider_request" and _H(b) != r["bindings"]["provider_payload_sha256"]:
                _fail()
            if success and key == "final_text" and b != raw:
                _fail()
        elif (not _integer(desc["bytes"],0,0) or desc["sha256"] is not None or
              desc["complete"] is not False or desc["overflow"] is not False or desc["extent"] != "absent"):
            _fail()
        if success and (desc["present"] is not True or desc["complete"] is not True or
                        desc["overflow"] is not False or desc["extent"] != "whole_file"):
            _fail()
    return r


def _decode(raw):
    value = _json(raw)
    _keys(value, ("schema_version","status","synthetic","equipment_authorized"))
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1 or
        type(value["status"]) is not str or value["status"] != "ok" or
        value["synthetic"] is not True or value["equipment_authorized"] is not False):
        _fail()


def _now():
    return datetime.now(_KST).isoformat(timespec="milliseconds")


def _row(matrix, slot, reason, *, status="not_run", receipt=None, reservation=None,
         budget=None, started=None, elapsed=0, decoded="not_run", attempts=0):
    settings = slot["settings"]
    return dict(schema_version=1,kind="vertex_comparison_row",batch_id=matrix["batch_id"],
        run_id=slot["run_id"],row_index=slot["row_index"],
        binding=dict(scenario_id=_SCENARIO,scenario_version=1,evaluator_id=_EVALUATOR,
            evaluator_version=1,prompt_sha256=matrix["binding"]["prompt_sha256"],
            schema_sha256=matrix["binding"]["response_schema_sha256"],
            profile_sha256=matrix["binding"]["profile_sha256"],
            settings_sha256=None if settings is None else settings["settings_sha256"],
            matrix_sha256=matrix["matrix_sha256"]),
        settings=None if settings is None else _snapshot(settings),execution_mode="actual",
        status=status,reason_code=reason,receipt=receipt,
        strict_decode=dict(status=decoded,evaluator_id=_EVALUATOR,
                           error_code="connection_response_invalid" if decoded=="rejected" else None),
        assessment=dict(status="not_assessed",verdict=None,reason_code="connection_only"),
        budget=dict(budget_id=None if budget is None else budget["budget_id"],
            reservation_id=None if reservation is None else reservation["reservation_id"],
            reserved_calls=None if budget is None else budget["reserved_calls"],
            reserved_output_tokens=None if budget is None else budget["reserved_output_tokens"],
            generation_post_attempts=attempts),
        timing=dict(started_at=started,finished_at=_now(),elapsed_ms=elapsed))


def _record(directory, row):
    raw = _C(row)
    if len(raw)>1048576:
        _fail("limit_exceeded")
    path = directory/("row-"+str(row["row_index"])+".record.json")
    try:
        _path(path)
        with path.open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
    except OSError:
        _fail("state_error")
    return _H(raw)


def _execute(matrix,index,prompt,schema,adc,directory,budget_path,approval_path,event,begin):
    slot = matrix["rows"][index]
    if index not in matrix["selection"]["row_indexes"]:
        return _row(matrix,slot,"not_selected")
    if event is not None and event.is_set():
        return _row(matrix,slot,"cancelled")
    settings = slot["settings"]
    if settings["max_output_tokens"]>512 or settings["timeout_seconds"]>60:
        return _row(matrix,slot,"budget_rejected")
    if time.monotonic()-begin + settings["timeout_seconds"]+6 > 300:
        return _row(matrix,slot,"wall_limit")
    try:
        approval = _approval(approval_path,matrix)
        budget,_ = _budget(budget_path,approval)
    except (ModelComparisonError,OSError):
        return _row(matrix,slot,"gate_rejected")
    try:
        d2 = _dependency("labflow.vertex_response")
    except ModelComparisonError:
        return _row(matrix,slot,"dependency_unavailable",budget=budget)
    try:
        _credentials(d2.inspect_vertex_credentials(adc,settings=_snapshot(settings)),settings)
    except d2.VertexResponseError as error:
        code = getattr(error,"code",None)
        if type(code) is not str or code.removeprefix("vertex_response_") not in _VERTEX_CODES:
            raise
        return _row(matrix,slot,code,budget=budget)
    except ModelComparisonError:
        return _row(matrix,slot,"credential_metadata_invalid",budget=budget)
    if event is not None and event.is_set():
        return _row(matrix,slot,"cancelled",budget=budget)
    if time.monotonic()-begin+settings["timeout_seconds"]+6 > 300:
        return _row(matrix,slot,"wall_limit",budget=budget)
    # Revalidate scope immediately before reserving, including expiry/revocation.
    try:
        if _C(_approval(approval_path,matrix)) != _C(approval):
            return _row(matrix,slot,"gate_rejected",budget=budget)
        reservation,reason,budget = _reserve(budget_path,approval,matrix,slot)
    except (ModelComparisonError,OSError):
        return _row(matrix,slot,"budget_unavailable",budget=budget)
    if reservation is None:
        return _row(matrix,slot,reason,budget=budget)
    started,clock = _now(),time.monotonic()
    record = None
    reason = None
    if event is not None and event.is_set():
        reason = "cancelled"
    elif time.monotonic()-begin+settings["timeout_seconds"]+6 > 300:
        reason = "wall_limit"
    else:
        try:
            if _C(_approval(approval_path,matrix)) != _C(approval):
                reason = "gate_rejected"
        except (ModelComparisonError,OSError):
            reason = "gate_rejected"
    if reason is not None:
        record = _row(matrix,slot,reason,reservation=reservation,budget=budget,
                      started=started,elapsed=max(0,(time.monotonic()-clock)*1000))
        digest = _record(directory,record)
        _finish_record(budget_path,approval,reservation,record,digest)
        return record
    transport_error = None
    try:
        result = d2.produce_vertex_response(prompt,schema,settings=_snapshot(settings),
            adc_path=adc,evidence_dir=directory/("row-"+str(index)),cancel_event=event)
    except d2.VertexResponseError as error:
        code = getattr(error,"code",None)
        if (type(code) is not str or not code.startswith("vertex_response_") or
            code.removeprefix("vertex_response_") not in _VERTEX_CODES):
            raise
        transport_error = error
        receipt = None
        if error.receipt is not None:
            try:
                receipt = _receipt(error.receipt,settings,prompt,schema,directory/("row-"+str(index)),
                                   None,False,code)
            except (ModelComparisonError,OSError):
                pass
        attempts = None if receipt is None else receipt["attempts"]["generation_post_attempts"]
        unknown = receipt is None or attempts is None or receipt["cleanup"]["worker_reaped"] is not True
        record = _row(matrix,slot,code,status="unknown" if unknown else "failed",receipt=receipt,
            reservation=reservation,budget=budget,started=started,
            elapsed=max(0,(time.monotonic()-clock)*1000),attempts=attempts)
    if record is None:
        receipt = None
        try:
            if type(result) is not tuple or len(result) != 2:
                _fail()
            raw,value = result
            receipt = _receipt(value,settings,prompt,schema,directory/("row-"+str(index)),raw,True)
        except (ModelComparisonError,OSError):
            record = _row(matrix,slot,"receipt_invalid",status="unknown",reservation=reservation,
                budget=budget,started=started,elapsed=max(0,(time.monotonic()-clock)*1000),attempts=None)
        else:
            try:
                _decode(raw)
                decoded,status,reason = "checked","success","connection_verified"
            except ModelComparisonError:
                decoded,status,reason = "rejected","failed","connection_response_invalid"
            record = _row(matrix,slot,reason,status=status,receipt=receipt,
                reservation=reservation,budget=budget,started=started,decoded=decoded,
                elapsed=max(0,(time.monotonic()-clock)*1000),
                attempts=receipt["attempts"]["generation_post_attempts"])
    persistence_failed = False
    try:
        digest = _record(directory,record)
        _finish_record(budget_path,approval,reservation,record,digest)
    except (ModelComparisonError,OSError):
        if transport_error is None:
            raise
        BaseException.add_note(transport_error,"model_comparison_persistence_failed")
        persistence_failed = True
    if persistence_failed:
        try:
            raise transport_error from None
        except d2.VertexResponseError:
            transport_error.__cause__ = transport_error.__context__ = None
            transport_error.__suppress_context__ = True
            raise
    return record


def _paths(adc,evidence,budget,approval,event):
    for p in (adc,evidence,budget,approval):
        _path(p)
    if event is not None and type(event) is not threading.Event:
        _fail()
    files = (adc,budget,approval)
    if len({os.path.normcase(str(p)) for p in files}) != 3 or any(p==evidence or evidence in p.parents for p in files):
        _fail()
    if not evidence.parent.is_dir():
        _fail()
    if evidence.exists():
        if not evidence.is_dir() or any(evidence.iterdir()):
            _fail("state_error")
    else:
        evidence.mkdir()


def _prepare_paths(adc,evidence,budget,approval,event):
    try:
        _paths(adc,evidence,budget,approval,event)
    except OSError:
        _fail("state_error")


def _finish_record(path,approval,reservation,record,digest):
    try:
        _finish(path,approval,reservation,record,digest)
    except OSError:
        _fail("state_error")


def run_vertex_comparison_row(matrix, row_index, prompt_bytes, response_schema_bytes, *,
        adc_path, evidence_dir, budget_path, approval_path, cancel_event=None):
    if not _integer(row_index,0,5):
        _fail()
    begin = time.monotonic()
    m = _matrix(matrix,prompt_bytes,response_schema_bytes)
    _prepare_paths(adc_path,evidence_dir,budget_path,approval_path,cancel_event)
    row = _execute(m,row_index,prompt_bytes,response_schema_bytes,adc_path,evidence_dir,
                   budget_path,approval_path,cancel_event,begin)
    if row["budget"]["reservation_id"] is None:
        _record(evidence_dir,row)
    return row


def run_vertex_comparison_batch(matrix, prompt_bytes, response_schema_bytes, *,
        adc_path, evidence_dir, budget_path, approval_path, cancel_event=None):
    begin = time.monotonic()
    m = _matrix(matrix,prompt_bytes,response_schema_bytes)
    _prepare_paths(adc_path,evidence_dir,budget_path,approval_path,cancel_event)
    rows,stopped = [],None
    for i,slot in enumerate(m["rows"]):
        if i not in m["selection"]["row_indexes"]:
            row = _row(m,slot,"not_selected")
        elif stopped is not None:
            row = _row(m,slot,"batch_stopped")
        else:
            row = _execute(m,i,prompt_bytes,response_schema_bytes,adc_path,evidence_dir,
                           budget_path,approval_path,cancel_event,begin)
            if row["status"] != "success":
                stopped = row["reason_code"]
        if row["budget"]["reservation_id"] is None:
            _record(evidence_dir,row)
        rows.append(row)
    cumulative = None
    try:
        cumulative,_ = _budget(budget_path,_approval(approval_path,m))
    except (ModelComparisonError,OSError):
        pass
    known = sum(r["budget"]["generation_post_attempts"] for r in rows
                if r["budget"]["generation_post_attempts"] is not None)
    unknown = sum(r["budget"]["generation_post_attempts"] is None for r in rows)
    summary = dict(planned_rows=6,selected_rows=len(m["selection"]["row_indexes"]),
        success_rows=sum(r["status"]=="success" for r in rows),
        failed_rows=sum(r["status"]=="failed" for r in rows),
        not_run_rows=sum(r["status"]=="not_run" for r in rows),
        unknown_rows=sum(r["status"]=="unknown" for r in rows),
        cumulative_reserved_calls=None if cumulative is None else cumulative["reserved_calls"],
        cumulative_reserved_output_tokens=None if cumulative is None else cumulative["reserved_output_tokens"],
        generation_post_attempts=None if unknown else known,generation_post_attempts_known=known,
        generation_post_attempts_unknown_rows=unknown)
    result = dict(schema_version=1,kind="vertex_comparison_batch",batch_id=m["batch_id"],
        matrix_sha256=m["matrix_sha256"],execution_mode="actual",rows=rows,summary=summary,
        business_assessment="not_assessed")
    raw = _C(result)
    if len(raw)>1048576:
        _fail("limit_exceeded")
    try:
        _path(evidence_dir/"batch.json")
        with (evidence_dir/"batch.json").open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
    except OSError:
        _fail("state_error")
    return result
