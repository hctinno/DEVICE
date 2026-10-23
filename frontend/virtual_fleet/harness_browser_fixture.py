"""Synthetic completed-record test data; this fixture never runs a harness/AI."""

import argparse

from frontend.virtual_fleet.demo_runtime import create_demo
from labflow.virtual_fleet_server import create_server


def completed_record():
    return {"schema_version": 1, "kind": "virtual_fleet_harness_result", "run_id": "ui-fixture:record-1", "runtime_instance_id": "ui-fixture:instance-1",
            "synthetic": True, "hardware_verified": False, "ai_model_called": False,
            "policy": {"kind": "fixture", "id": "ui_fixture_record"}, "termination": {"reason": "policy_stop", "policy_claim": "completed"},
            "task_outcome": "not_assessed", "cleanup": {"status": "not_assessed", "evidence_refs": []},
            "usage": {"decisions": 9, "logical_requests": 7, "transport_retries": 1, "tick_delta": 3, "reserved_ticks": 3, "elapsed_ms": 12.5},
            "evidence": {"measurement_refs": ["event:18"], "operator_transcript_ref": "artifact:synthetic_ui_operator_events"},
            "unresolved_request_ids": [],
            "assessment": {"status": "not_assessed", "verdict": None, "evaluator_id": None, "evidence_refs": [], "summary_code": None}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    runtime, catalog, topology, role_actions = create_demo()
    with create_server(runtime, catalog=catalog, topology=topology, role_actions=role_actions,
                       harness_report=completed_record(), port=args.port) as server:
        print(f"Synthetic UI record fixture: http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
