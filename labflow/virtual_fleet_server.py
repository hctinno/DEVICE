"""Loopback HTTP boundary for an injected, trusted, purely virtual fleet.

The runtime owns simulation semantics. This module only uses its public operator
interface and never imports hardware adapters, customer files or author controls.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
from typing import Any


_STATIC = Path(__file__).resolve().parents[1] / "frontend" / "virtual_fleet"
_ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
           "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
           "/model.mjs": ("model.mjs", "text/javascript; charset=utf-8"),
           "/styles.css": ("styles.css", "text/css; charset=utf-8")}
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_TYPES = {"number", "integer", "boolean", "string", "object", "array"}
_PRIVATE_KEYS = {"author_control", "author", "hidden", "hidden_fault", "expected", "expected_values",
                 "expected_result", "password", "secret", "credential", "credentials", "source_path",
                 "file_path", "decrypted_path", "serial", "serial_number", "simulation_parameters"}
_INPUT_KEYS = _PRIVATE_KEYS | {"fault", "address", "host", "ip", "path", "url", "command", "script"}
_PROFILE_FIELDS = {"profile_id", "model", "manufacturer", "role", "ports", "variant", "evidence_refs",
                   "simulation_basis", "capability_scope", "profile_kind", "classification", "context", "auxiliary"}


class RequestError(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code


def _safe_json(value: Any, *, depth: int = 0) -> Any:
    """Copy public JSON data; refuse non-JSON and discard reserved private fields."""
    if depth > 32:
        raise ValueError("nested_value")
    if isinstance(value, dict):
        return {key: _safe_json(item, depth=depth + 1) for key, item in value.items()
                if isinstance(key, str) and key.lower() not in _PRIVATE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item, depth=depth + 1) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        # json.dumps below rejects non-finite floats, including nested values.
        return value
    raise ValueError("non_json_value")


def _public_catalog(catalog: dict) -> dict:
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("catalog_profiles")
    result = {key: _safe_json(catalog[key]) for key in ("schema_version", "catalog_id", "source_basis", "title", "scope", "fixture") if key in catalog}
    result["profiles"] = [{key: _safe_json(value) for key, value in profile.items() if key in _PROFILE_FIELDS} for profile in profiles]
    return result


def _input_json(value: Any, depth: int = 0) -> bool:
    if depth > 12:
        return False
    if isinstance(value, dict):
        return len(value) <= 256 and all(isinstance(key, str) and key.lower() not in _INPUT_KEYS
                                        and _input_json(item, depth + 1) for key, item in value.items())
    if isinstance(value, list):
        return len(value) <= 1024 and all(_input_json(item, depth + 1) for item in value)
    return value is None or isinstance(value, (str, bool, int, float))


def _typed(value: Any, schema: dict) -> bool:
    kind = schema["type"]
    valid = {"number": lambda: type(value) in (int, float),
             "integer": lambda: type(value) is int,
             "boolean": lambda: type(value) is bool,
             "string": lambda: isinstance(value, str) and len(value) <= 4096,
             "object": lambda: isinstance(value, dict),
             "array": lambda: isinstance(value, list)}[kind]()
    if not valid or not _input_json(value):
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if kind in ("number", "integer"):
        if "minimum" in schema and value < schema["minimum"]:
            return False
        if "maximum" in schema and value > schema["maximum"]:
            return False
    return True


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


class VirtualFleetServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, runtime, *, catalog, topology, role_actions, host, port):
        if host not in ("127.0.0.1", "localhost"):
            raise ValueError("loopback_only")
        self.runtime = runtime
        self.catalog = _public_catalog(copy.deepcopy(catalog))
        self.topology = _safe_json(copy.deepcopy(topology))
        self.role_actions = copy.deepcopy(role_actions)
        self.profiles = {}
        for profile in self.catalog["profiles"]:
            for key in ("profile_id", "model", "manufacturer", "role"):
                if not isinstance(profile.get(key), str) or not profile[key]:
                    raise ValueError("invalid_profile")
            if profile["profile_id"] in self.profiles:
                raise ValueError("duplicate_profile")
            self.profiles[profile["profile_id"]] = profile
        self.devices = {}
        for device in self.topology["devices"]:
            if not isinstance(device.get("id"), str) or not device["id"] or device["id"] in self.devices or device["profile_id"] not in self.profiles:
                raise ValueError("invalid_device")
            self.devices[device["id"]] = device
        for role, actions in self.role_actions.items():
            if not isinstance(role, str) or not isinstance(actions, dict):
                raise ValueError("invalid_actions")
            for action, declaration in actions.items():
                if action.lower() in _INPUT_KEYS or not isinstance(declaration.get("parameters"), dict):
                    raise ValueError("invalid_action")
                for name, schema in declaration["parameters"].items():
                    if name.lower() in _INPUT_KEYS or schema.get("type") not in _TYPES:
                        raise ValueError("invalid_parameter_schema")
        self.csrf_token = secrets.token_urlsafe(32)
        self.session_id = secrets.token_hex(16)
        self.lock = threading.RLock()
        self.receipts: dict[str, tuple[str, int, dict]] = {}
        super().__init__(("127.0.0.1", port), FleetHandler)

    def snapshot(self) -> dict:
        with self.lock:
            observations = _safe_json(self.runtime.observations())
            coverage = _safe_json(self.runtime.coverage())
            if not isinstance(coverage, (dict, list)):
                raise ValueError("invalid_coverage")
            if not isinstance(observations, dict) or not isinstance(observations.get("devices"), dict):
                raise ValueError("invalid_observations")
            for key in ("tick", "setup_revision"):
                if type(observations.get(key)) is not int or observations[key] < 0:
                    raise ValueError("invalid_revision")
            if observations.get("synthetic") is not True or observations.get("hardware_verified") is not False:
                raise ValueError("invalid_provenance")
            if set(observations["devices"]) != set(self.devices):
                raise ValueError("observation_device_mismatch")
            for device_id, observation in observations["devices"].items():
                if not isinstance(observation, dict) or not isinstance(observation.get("status"), str) or not isinstance(observation.get("values"), dict):
                    raise ValueError("invalid_device_observation")
                if observation.get("synthetic") is not True or observation.get("hardware_verified") is not False:
                    raise ValueError("invalid_device_provenance")
                if observation.get("profile_id") != self.devices[device_id]["profile_id"]:
                    raise ValueError("invalid_observation_profile")
                for key in ("tick", "setup_revision"):
                    if type(observation.get(key)) is not int or observation[key] < 0:
                        raise ValueError("invalid_device_revision")
                if "state" in observation and not isinstance(observation["state"], (str, dict)):
                    raise ValueError("invalid_device_state")
            return {"schema_version": 1, "mode": "virtual", "synthetic": True, "hardware_verified": False,
                    "runtime_kind": "synthetic_fixture" if self.catalog.get("fixture") is True else "injected_virtual_runtime",
                    "session_id": self.session_id, "csrf_token": self.csrf_token,
                    "generated_at": datetime.now(timezone.utc).isoformat(), "catalog": self.catalog,
                    "topology": self.topology, "role_actions": self.role_actions,
                    "observations": observations, "coverage": coverage}

    def validate_request(self, path, payload):
        if not isinstance(payload, dict):
            raise RequestError(400, "invalid_request")
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
            raise RequestError(400, "invalid_request_id")
        if path == "/api/advance":
            if set(payload) != {"request_id", "ticks"} or type(payload["ticks"]) is not int or not 1 <= payload["ticks"] <= 1000:
                raise RequestError(400, "invalid_ticks")
            return
        if set(payload) != {"request_id", "device_id", "action", "parameters"}:
            raise RequestError(400, "invalid_request_fields")
        device_id, action = payload["device_id"], payload["action"]
        if not isinstance(device_id, str) or device_id not in self.devices or not isinstance(action, str):
            raise RequestError(400, "unknown_device_or_action")
        role = self.profiles[self.devices[device_id]["profile_id"]]["role"]
        declaration = self.role_actions.get(role, {}).get(action)
        if declaration is None:
            raise RequestError(400, "unsupported_action")
        parameters, schemas = payload["parameters"], declaration["parameters"]
        if not isinstance(parameters, dict) or set(parameters) - set(schemas):
            raise RequestError(400, "invalid_parameters")
        for name, schema in schemas.items():
            if name not in parameters:
                if schema.get("required", False):
                    raise RequestError(400, "missing_parameter")
            elif not _typed(parameters[name], schema):
                raise RequestError(400, "invalid_parameter_type")

    def mutate(self, path: str, payload: dict) -> tuple[int, dict]:
        self.validate_request(path, payload)
        request_id = payload["request_id"]
        signature = path + "\n" + json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self.lock:
            if request_id in self.receipts:
                original, status, receipt = self.receipts[request_id]
                if original != signature:
                    raise RequestError(409, "request_id_conflict")
                return status, {**copy.deepcopy(receipt), "replayed": True}
            # Never evict an old ID and silently execute its retry for a second time.
            if len(self.receipts) >= 4096:
                raise RequestError(503, "request_cache_full")
            try:
                if path == "/api/actions":
                    result = self.runtime.execute(request_id, payload["device_id"], payload["action"], payload["parameters"])
                else:
                    result = self.runtime.advance(request_id, payload["ticks"])
                result = _safe_json(result)
                if not isinstance(result, dict):
                    raise ValueError("invalid_runtime_result")
                receipt = {"request_id": request_id, "session_id": self.session_id, "replayed": False,
                           "synthetic": True, "hardware_verified": False, "result": result}
                json.dumps(receipt, ensure_ascii=False, allow_nan=False).encode("utf-8")
                status = 200
            except Exception:
                # A call may have changed state before raising: keep the ID reserved.
                status = 503
                receipt = {"request_id": request_id, "session_id": self.session_id, "replayed": False,
                           "error": {"code": "runtime_mutation_uncertain"}}
            self.receipts[request_id] = signature, status, copy.deepcopy(receipt)
            return status, receipt


class FleetHandler(BaseHTTPRequestHandler):
    server_version = "DGMVirtualFleet"

    def log_message(self, *args):
        pass

    def _guard(self, *, mutation=False):
        hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        supplied = self.headers.get_all("Host", [])
        if len(supplied) != 1 or supplied[0] not in hosts:
            raise RequestError(403, "local_host_required")
        origin = self.headers.get_all("Origin", [])
        expected = "http://" + supplied[0]
        if (mutation and origin != [expected]) or (origin and origin != [expected]):
            raise RequestError(403, "same_origin_required")
        fetch_site = self.headers.get("Sec-Fetch-Site")
        if fetch_site is not None and fetch_site not in (("same-origin",) if mutation else ("same-origin", "none")):
            raise RequestError(403, "same_origin_required")
        if mutation:
            tokens = self.headers.get_all("X-CSRF-Token", [])
            if len(tokens) != 1 or not secrets.compare_digest(tokens[0].encode("utf-8"), self.server.csrf_token.encode("utf-8")):
                raise RequestError(403, "csrf_required")

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, error):
        self._send(error.status, {"error": {"code": error.code}})

    def do_GET(self):
        try:
            self._guard()
            if self.path == "/api/state":
                try:
                    snapshot = self.server.snapshot()
                    encoded = json.dumps(snapshot, ensure_ascii=False, allow_nan=False).encode("utf-8")
                except Exception:
                    raise RequestError(503, "runtime_unavailable")
                self._send(200, encoded)
            elif self.path in _ASSETS:
                name, mime = _ASSETS[self.path]
                try:
                    self._send(200, (_STATIC / name).read_bytes(), mime)
                except OSError:
                    raise RequestError(503, "ui_unavailable")
            else:
                raise RequestError(404, "not_found")
        except RequestError as error:
            self._error(error)

    def _body(self):
        if self.headers.get_content_type() != "application/json":
            raise RequestError(415, "json_required")
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isdigit():
            raise RequestError(400, "invalid_content_length")
        length = int(lengths[0])
        if length > 65536:
            # Bounded drain keeps a normal oversize client from losing the 413
            # response to a Windows TCP reset when unread request bytes remain.
            self.connection.settimeout(1)
            remaining = min(length, 1048576)
            try:
                while remaining:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except (OSError, TimeoutError):
                pass
            raise RequestError(413, "request_too_large")
        if length == 0:
            raise RequestError(400, "empty_body")
        self.connection.settimeout(5)
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("short_body")
            payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non_finite")))
            json.dumps(payload, allow_nan=False)  # Also rejects finite syntax such as 1e999 overflowing to infinity.
            return payload
        except (ValueError, RecursionError, TimeoutError, OSError):
            raise RequestError(400, "invalid_json")

    def do_POST(self):
        try:
            self._guard(mutation=True)
            if self.path not in ("/api/actions", "/api/advance"):
                raise RequestError(404, "not_found")
            status, receipt = self.server.mutate(self.path, self._body())
            self._send(status, receipt)
        except RequestError as error:
            self._error(error)

    def _method_not_allowed(self):
        try:
            self._guard()
            raise RequestError(405, "method_not_allowed")
        except RequestError as error:
            self._error(error)

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_HEAD = _method_not_allowed


def create_server(runtime, *, catalog: dict, topology: dict, role_actions: dict,
                  host: str = "127.0.0.1", port: int = 8770) -> VirtualFleetServer:
    """Return an unstarted server. The caller owns serve_forever/shutdown/close.

    Catalog/topology/schema are fixed for this server lifetime. Runtime mutations
    must pass through this server's lock if a consistent HTTP snapshot is needed.
    """
    return VirtualFleetServer(runtime, catalog=catalog, topology=topology,
                              role_actions=role_actions, host=host, port=port)


def main(argv=None):
    parser = argparse.ArgumentParser(description="DGM 가상 시험소 UI — 합성 fixture 전용 실행기")
    parser.add_argument("--demo", action="store_true", required=True, help="합성 fixture를 실행합니다")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args(argv)
    from frontend.virtual_fleet.demo_runtime import create_demo
    runtime, catalog, topology, role_actions = create_demo()
    with create_server(runtime, catalog=catalog, topology=topology, role_actions=role_actions, port=args.port) as server:
        print(f"합성 fixture · 실장비 미검증: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
