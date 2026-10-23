import copy
import http.client
import json
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from labflow.virtual_fleet_server import create_server


CATALOG = {"profiles": [{
    "profile_id": "psu-demo", "model": "Synthetic supply", "manufacturer": "DGM fixture",
    "role": "power_supply", "variant": "dc", "ports": {"inputs": {}, "outputs": {"power": "power"}},
    "evidence_refs": ["synthetic:server-contract"], "simulation_basis": "합성 상태 검사",
    "capability_scope": {"supported": ["전원 상태"], "unverified": ["실장비 정밀도"]},
    "simulation_parameters": {"hidden_fault": "private-author-value"},
    "source_path": "C:/private/source.xlsx", "serial_number": "PRIVATE-SERIAL",
}]}
TOPOLOGY = {"devices": [{"id": "psu", "profile_id": "psu-demo"}], "connections": []}
ACTIONS = {"power_supply": {
    "set_output": {"parameters": {"enabled": {"type": "boolean", "required": True, "unit": ""}}, "completion": "immediate"},
    "configure": {"parameters": {"voltage": {"type": "number", "required": True, "unit": "V"}}, "completion": "immediate"},
    "recover": {"parameters": {}, "completion": "immediate"},
}}


class ContractRuntime:
    """Only the public runtime contract; the shared implementation is a separate deliverable."""

    def __init__(self):
        self.tick = 0
        self.revision = 0
        self.enabled = False
        self.voltage = 0
        self.broken = False

    def observations(self):
        if self.broken:
            raise RuntimeError("C:/private/failure with secret")
        envelope = {"tick": self.tick, "setup_revision": self.revision, "synthetic": True,
                    "hardware_verified": False}
        return {**envelope, "devices": {"psu": {**envelope, "profile_id": "psu-demo",
                "status": "ok", "state": "on" if self.enabled else "off",
                "values": {"voltage_v": self.voltage, "enabled": self.enabled,
                           "outputs": {"power": {"voltage_v": self.voltage, "enabled": self.enabled}}}}}}

    def coverage(self):
        return {"profiles": [{"profile_id": "psu-demo", "implemented": True,
                              "acceptance": "not_run"}], "hardware_verified": False}

    def execute(self, request_id, device_id, action, parameters=None):
        if action == "set_output":
            self.enabled = parameters["enabled"]
        elif action == "configure":
            self.voltage = parameters["voltage"]
        elif action == "recover":
            self.broken = False
        self.revision += 1
        return {"request_id": request_id, "status": "ok", "values": {"enabled": self.enabled},
                "setup_changed": True, "tick": self.tick, "setup_revision": self.revision,
                "synthetic": True, "hardware_verified": False}

    def advance(self, request_id, ticks=1):
        time.sleep(0.005)  # Expose lost duplicate protection in concurrent HTTP requests.
        self.tick += ticks
        return {"request_id": request_id, "status": "ok", "tick": self.tick,
                "setup_revision": self.revision, "synthetic": True, "hardware_verified": False}


class VirtualFleetServerTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ContractRuntime()
        self.server = create_server(self.runtime, catalog=copy.deepcopy(CATALOG),
                                    topology=copy.deepcopy(TOPOLOGY), role_actions=copy.deepcopy(ACTIONS), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)
        status, _, body = self.request("/api/state")
        self.assertEqual(status, 200)
        self.token = json.loads(body)["csrf_token"]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path, method="GET", payload=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        actual = dict(headers or {})
        if method == "POST":
            actual.setdefault("Origin", self.origin)
            actual.setdefault("Content-Type", "application/json")
            actual.setdefault("X-CSRF-Token", getattr(self, "token", ""))
        body = raw if raw is not None else json.dumps(payload).encode("utf-8") if payload is not None else None
        try:
            connection.request(method, path, body=body, headers=actual)
            result = connection.getresponse()
            return result.status, dict(result.getheaders()), result.read()
        finally:
            connection.close()

    def state(self):
        status, _, body = self.request("/api/state")
        self.assertEqual(status, 200)
        return json.loads(body)

    def test_snapshot_exposes_operator_contract_and_removes_private_catalog_fields(self):
        snapshot = self.state()
        self.assertEqual(snapshot["observations"]["devices"]["psu"]["state"], "off")
        self.assertEqual(snapshot["role_actions"]["power_supply"]["configure"]["parameters"]["voltage"]["unit"], "V")
        self.assertEqual(snapshot["catalog"]["profiles"][0]["evidence_refs"], ["synthetic:server-contract"])
        self.assertEqual(snapshot["coverage"]["profiles"][0]["acceptance"], "not_run")
        raw = json.dumps(snapshot)
        for private in ["PRIVATE-SERIAL", "C:/private", "private-author-value", "simulation_parameters", "author_control"]:
            self.assertNotIn(private, raw)
        self.assertTrue(snapshot["synthetic"])
        self.assertFalse(snapshot["hardware_verified"])

    def test_action_and_advance_change_observable_runtime_state(self):
        status, _, body = self.request("/api/actions", "POST", {
            "request_id": "output-1", "device_id": "psu", "action": "set_output", "parameters": {"enabled": True}})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["result"]["status"], "ok")
        self.assertEqual(self.state()["observations"]["devices"]["psu"]["state"], "on")
        self.assertEqual(self.request("/api/advance", "POST", {"request_id": "tick-1", "ticks": 3})[0], 200)
        self.assertEqual(self.state()["observations"]["tick"], 3)

    def test_request_id_retries_return_original_receipt_without_second_mutation(self):
        payload = {"request_id": "once", "ticks": 2}
        first = self.request("/api/advance", "POST", payload)
        second = self.request("/api/advance", "POST", payload)
        self.assertEqual(first[0], 200)
        self.assertEqual(second[0], 200)
        self.assertEqual(json.loads(first[2])["result"], json.loads(second[2])["result"])
        self.assertTrue(json.loads(second[2])["replayed"])
        self.assertEqual(self.state()["observations"]["tick"], 2)
        self.assertEqual(self.request("/api/advance", "POST", {"request_id": "once", "ticks": 4})[0], 409)
        self.assertEqual(self.request("/api/actions", "POST", {"request_id": "once", "device_id": "psu",
                          "action": "recover", "parameters": {}})[0], 409)

    def test_concurrent_duplicate_requests_advance_only_once(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            responses = list(pool.map(lambda _: self.request("/api/advance", "POST", {"request_id": "parallel", "ticks": 1}), range(6)))
        self.assertTrue(all(response[0] == 200 for response in responses))
        self.assertEqual(self.state()["observations"]["tick"], 1)

    def test_changes_require_exact_origin_csrf_and_local_host(self):
        payload = {"request_id": "forbidden", "ticks": 1}
        for headers in [{"Origin": "https://attacker.invalid"}, {"Origin": "null"}, {"Origin": ""},
                        {"X-CSRF-Token": "wrong"}, {"X-CSRF-Token": "\u00e9"}, {"Sec-Fetch-Site": "same-site"},
                        {"Host": "attacker.invalid"}, {"Origin": self.origin + "/"}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/advance", "POST", payload, headers=headers)[0], 403)
        self.assertEqual(self.state()["observations"]["tick"], 0)
        self.assertEqual(self.request("/api/state", headers={"Host": "attacker.invalid"})[0], 403)
        self.assertEqual(self.request("/api/state", headers={"Origin": "https://attacker.invalid"})[0], 403)
        with self.assertRaises(ValueError):
            create_server(self.runtime, catalog=CATALOG, topology=TOPOLOGY, role_actions=ACTIONS, host="0.0.0.0", port=0)

    def test_strict_requests_reject_bad_json_unknown_fields_types_and_undeclared_actions(self):
        base = {"request_id": "bad", "device_id": "psu", "action": "configure", "parameters": {"voltage": 3.8}}
        bad = [dict(base, request_id=""), dict(base, request_id=12), dict(base, request_id="a" * 129),
               dict(base, device_id="unknown"), dict(base, action="author_control"),
               dict(base, source_path="C:/private"), dict(base, parameters={"voltage": True}),
               dict(base, parameters={}), dict(base, parameters={"voltage": 3, "password": "no"}),
               dict(base, parameters={"voltage": "3.8"}), dict(base, parameters=None)]
        for payload in bad:
            with self.subTest(payload=payload):
                self.assertEqual(self.request("/api/actions", "POST", payload)[0], 400)
        for raw in [b'{"request_id":"a","request_id":"b","ticks":1}', b'{"request_id":"nan","ticks":NaN}',
                    b'[]', b'null', b'"text"', b'{', b'{"request_id":"utf8","ticks":1,"x":"\xff"}']:
            with self.subTest(raw=raw):
                self.assertEqual(self.request("/api/advance", "POST", raw=raw)[0], 400)
        for ticks in [True, 0, -1, 1001, 1.2, "1"]:
            self.assertEqual(self.request("/api/advance", "POST", {"request_id": "bad-tick", "ticks": ticks})[0], 400)
        self.assertEqual(self.request("/api/advance", "POST", {"request_id": "bad-type", "ticks": 1}, headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("/api/advance", "POST", raw=b" " * 70000)[0], 413)
        self.assertEqual(self.state()["observations"]["setup_revision"], 0)

    def test_static_allowlist_and_methods_never_open_paths_or_author_controls(self):
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"charset=\"utf-8\"", body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        for path in ["/../labflow/store.py", "/%2e%2e/labflow/store.py", "/api/state?path=private",
                     "/api/author_control", "/demo_runtime.py", "/.local/", "/api/state/"]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        for method in ["PUT", "DELETE", "PATCH", "OPTIONS", "TRACE"]:
            self.assertEqual(self.request("/api/state", method)[0], 405)
        self.assertEqual(self.request("/api/author_control", "POST", {"fault": "wrong"})[0], 404)

    def test_snapshot_failure_is_not_empty_success_and_recovery_remains_available(self):
        self.runtime.broken = True
        status, _, body = self.request("/api/state")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"]["code"], "runtime_unavailable")
        self.assertNotIn(b"secret", body)
        status, _, _ = self.request("/api/actions", "POST", {"request_id": "recover", "device_id": "psu", "action": "recover", "parameters": {}})
        self.assertEqual(status, 200)
        self.assertEqual(self.state()["observations"]["devices"]["psu"]["status"], "ok")

    def test_numeric_overflow_is_rejected_before_runtime_mutation(self):
        raw = b'{"request_id":"overflow","device_id":"psu","action":"configure","parameters":{"voltage":1e999}}'
        self.assertEqual(self.request("/api/actions", "POST", raw=raw)[0], 400)
        self.assertEqual(self.state()["observations"]["setup_revision"], 0)

    def test_exception_after_mutation_reserves_request_id_and_never_repeats_it(self):
        def partial_failure(request_id, ticks):
            self.runtime.tick += ticks
            raise RuntimeError("private failure detail")
        self.runtime.advance = partial_failure
        payload = {"request_id": "uncertain", "ticks": 2}
        for replayed in (False, True):
            status, _, body = self.request("/api/advance", "POST", payload)
            self.assertEqual(status, 503)
            receipt = json.loads(body)
            self.assertEqual(receipt["error"]["code"], "runtime_mutation_uncertain")
            self.assertEqual(receipt["replayed"], replayed)
            self.assertNotIn("private", str(receipt))
        self.assertEqual(self.state()["observations"]["tick"], 2)

    def test_snapshot_with_missing_device_is_error_instead_of_partial_success(self):
        original = self.runtime.observations
        def partial():
            result = original()
            result["devices"] = {}
            return result
        self.runtime.observations = partial
        self.assertEqual(self.request("/api/state")[0], 503)

    def test_malformed_device_envelope_and_coverage_cannot_be_successful_snapshot(self):
        original = self.runtime.observations
        for mutate in [lambda data: data["devices"]["psu"].update(tick=None),
                       lambda data: data["devices"]["psu"].update(setup_revision=-1),
                       lambda data: data["devices"]["psu"].update(state=[]),
                       lambda data: data["devices"]["psu"].update(hardware_verified=True)]:
            data = original()
            mutate(data)
            self.runtime.observations = lambda: data
            with self.subTest(data=data):
                self.assertEqual(self.request("/api/state")[0], 503)
        self.runtime.observations = original
        self.runtime.coverage = lambda: None
        self.assertEqual(self.request("/api/state")[0], 503)

    def test_virtual_port_enum_is_allowed_without_accepting_hardware_address(self):
        actions = copy.deepcopy(ACTIONS)
        actions["power_supply"]["select_port"] = {"parameters": {"port": {"type": "string", "required": True, "enum": ["A", "B"]}}, "completion": "immediate"}
        with create_server(self.runtime, catalog=CATALOG, topology=TOPOLOGY, role_actions=actions, port=0) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                headers = {"Origin": f"http://127.0.0.1:{server.server_port}", "X-CSRF-Token": server.csrf_token, "Content-Type": "application/json"}
                for parameters, expected in [({"port": "A"}, 200), ({"port": "A", "address": "hardware.invalid"}, 400)]:
                    payload = {"request_id": "select-port", "device_id": "psu", "action": "select_port", "parameters": parameters}
                    connection.request("POST", "/api/actions", body=json.dumps(payload), headers=headers)
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                connection.close()
            finally:
                server.shutdown()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
