import copy
from contextlib import contextmanager
import http.client
import json
import threading
import unittest
from unittest.mock import patch

from labflow.virtual_fleet_server import create_server


CATALOG = {"profiles": [{"profile_id": "ui-fixture", "model": "DGM UI fixture", "manufacturer": "DGM", "role": "dut",
                         "ports": {"inputs": {}, "outputs": {}}, "evidence_refs": []}]}
TOPOLOGY = {"devices": [{"id": "dut", "profile_id": "ui-fixture"}], "connections": []}


def public_result():
    return {"schema_version": 1, "kind": "virtual_fleet_harness_result", "run_id": "run:ui-1", "runtime_instance_id": "instance:ui-1",
            "synthetic": True, "hardware_verified": False, "ai_model_called": False,
            "policy": {"kind": "fixture", "id": "rf_sensor_v1"},
            "termination": {"reason": "policy_stop", "policy_claim": "completed"}, "task_outcome": "not_assessed",
            "cleanup": {"status": "not_assessed", "evidence_refs": []},
            "usage": {"decisions": 9, "logical_requests": 7, "transport_retries": 1, "tick_delta": 3, "reserved_ticks": 3, "elapsed_ms": 12.5},
            "evidence": {"measurement_refs": ["event:18"], "operator_transcript_ref": "artifact:operator_events"},
            "unresolved_request_ids": [],
            "assessment": {"status": "not_assessed", "verdict": None, "evaluator_id": None, "evidence_refs": [], "summary_code": None}}


class NoExecutionRuntime:
    def execute(self, *args):
        raise AssertionError("report query cannot execute a runtime")

    advance = observations = coverage = execute


class HarnessReportHTTPTests(unittest.TestCase):
    @contextmanager
    def serving(self, report=None):
        with create_server(NoExecutionRuntime(), catalog=CATALOG, topology=TOPOLOGY, role_actions={}, harness_report=report, port=0) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield server
            finally:
                server.shutdown()
                thread.join(timeout=3)

    def request(self, server, path="/api/harness-result", method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_absent_report_is_explicit_null_without_querying_runtime(self):
        with self.serving() as server:
            status, headers, body = self.request(server)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"schema_version": 1, "report": None})
            self.assertEqual(headers["Cache-Control"], "no-store")

    def test_report_is_a_wire_safe_copy_and_caller_mutation_cannot_change_it(self):
        report = public_result()
        expected = copy.deepcopy(report)
        with self.serving(report) as server:
            report["run_id"] = "mutated"
            report["assessment"]["verdict"] = "pass"
            report["evidence"]["measurement_refs"].append({"seed": "private"})
            for _ in range(2):
                status, _, body = self.request(server)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body.decode("utf-8", errors="strict")), {"schema_version": 1, "report": expected})
                self.assertNotIn(b"private", body)

    def test_non_policy_termination_keeps_null_claim_and_unresolved_ids(self):
        report = public_result()
        report["termination"] = {"reason": "runtime_mutation_uncertain", "policy_claim": None}
        report["unresolved_request_ids"] = ["operator:pending:7"]
        with self.serving(report) as server:
            status, _, body = self.request(server)
            self.assertEqual(status, 200)
            actual = json.loads(body)["report"]
            self.assertIsNone(actual["termination"]["policy_claim"])
            self.assertEqual(actual["unresolved_request_ids"], ["operator:pending:7"])

    def test_caller_mutation_during_encoding_cannot_bypass_public_validation(self):
        report = public_result()
        expected = copy.deepcopy(report)
        encode = json.dumps
        def mutate_caller(value, *args, **kwargs):
            if type(value) is dict and value.get("kind") == "virtual_fleet_harness_result":
                report["policy"]["seed"] = "private-race-canary"
            return encode(value, *args, **kwargs)
        with patch("labflow.virtual_fleet_server.json.dumps", side_effect=mutate_caller):
            with self.serving(report) as server:
                status, _, body = self.request(server)
                self.assertEqual(status, 200)
                self.assertNotIn(b"private-race-canary", body)
                self.assertEqual(json.loads(body)["report"], expected)

    def test_public_result_rejects_unknown_nested_private_and_non_json_data(self):
        bad = []
        for container, key in [(None, "seed"), ("policy", "fault"), ("assessment", "expected"), ("usage", "source_path"), ("evidence", "author")]:
            report = public_result()
            (report if container is None else report[container])[key] = "private-canary"
            bad.append(report)
        for mutate in [lambda r: r.update(hardware_verified=True), lambda r: r.update(ai_model_called=True),
                       lambda r: r["usage"].update(decisions=True), lambda r: r["usage"].update(elapsed_ms=float("nan")),
                       lambda r: r["usage"].update(tick_delta=-1), lambda r: r["policy"].update(id="\ud800"),
                       lambda r: r["evidence"].update(measurement_refs=[{"password": "private-canary"}]),
                       lambda r: r.update(unresolved_request_ids={"not-json-set"}),
                       lambda r: r.update(termination={"reason": "supervisor_stop", "policy_claim": "completed"}),
                       lambda r: r.update(assessment={"status": "not_assessed", "verdict": "pass", "evaluator_id": None, "evidence_refs": [], "summary_code": None})]:
            report = public_result()
            mutate(report)
            bad.append(report)
        for report in [*bad, b"{}", "{}", [], 1]:
            with self.subTest(report_type=type(report).__name__):
                with self.assertRaises(ValueError):
                    create_server(NoExecutionRuntime(), catalog=CATALOG, topology=TOPOLOGY, role_actions={}, harness_report=report, port=0)

    def test_oversize_report_is_rejected_before_it_can_be_served(self):
        report = public_result()
        refs = ["artifact:" + "x" * 240 + str(index) for index in range(1000)]
        report["evidence"]["measurement_refs"] = refs
        report["assessment"]["evidence_refs"] = refs
        with self.assertRaises(ValueError):
            create_server(NoExecutionRuntime(), catalog=CATALOG, topology=TOPOLOGY, role_actions={}, harness_report=report, port=0)

    def test_existing_origin_path_and_method_boundaries_apply_to_report(self):
        with self.serving(public_result()) as server:
            for headers in [{"Host": "attacker.invalid"}, {"Origin": "https://attacker.invalid"}, {"Sec-Fetch-Site": "cross-site"}]:
                self.assertEqual(self.request(server, headers=headers)[0], 403)
            for path in ["/api/harness-result?path=private", "/api/harness-result/", "/api/harness-result?seed=1"]:
                self.assertEqual(self.request(server, path)[0], 404)
            for method in ["PUT", "PATCH", "DELETE"]:
                self.assertEqual(self.request(server, method=method)[0], 405)


if __name__ == "__main__":
    unittest.main()
