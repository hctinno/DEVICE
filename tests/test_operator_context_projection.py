"""Pure public-context projection contracts; no producer or runtime calls."""
from copy import deepcopy
import importlib
import unittest

from labflow.virtual_fleet.model_operator_boundary import ModelOperatorBoundaryError
from labflow.virtual_fleet import codex_virtual_loop as loop

try:
    projection = importlib.import_module("labflow.virtual_fleet.operator_context_projection")
except ModuleNotFoundError as error:
    if error.name != "labflow.virtual_fleet.operator_context_projection":
        raise
    projection = None


def profile(identity, role, *, inputs=None, outputs=None):
    return {"profile_id": "profile:" + identity, "role": role,
            "ports": {"inputs": inputs or {}, "outputs": outputs or {}}}


def edge(source, target, kind, source_port, target_port):
    return {"source": {"device_id": source, "port": source_port},
            "target": {"device_id": target, "port": target_port}, "kind": kind}


def context():
    profiles = [
        profile("supply", "power_supply", outputs={"power": "power"}),
        profile("controller", "controller", outputs={"control": "control"}),
        profile("dut", "dut", inputs={"power": "power", "control": "control"},
                outputs={"rf": "rf"}),
        profile("sensor", "power_sensor", inputs={"rf": "rf"}),
        profile("spare", "spare", outputs={"unused": "rf"}),
    ]
    devices = [{"id": p["profile_id"].split(":", 1)[1], "profile_id": p["profile_id"]}
               for p in profiles]
    observations = {node["id"]: {"device_id": node["id"],
                                  "profile_id": node["profile_id"],
                                  "role": profiles[i]["role"], "status": "ok",
                                  "values": {"source_id": node["id"]}}
                    for i, node in enumerate(devices)}
    return {
        "schema_version": 1,
        "goal": {"kind": "acquire_fresh_rf_sensor", "dut_id": "dut",
                 "sensor_id": "sensor", "minimum_acquisition_tick": 1},
        "catalog": {"catalog_id": "synthetic", "profiles": profiles},
        "topology": {"devices": devices, "connections": [
            edge("supply", "dut", "power", "power", "power"),
            edge("controller", "dut", "control", "control", "control"),
            edge("dut", "sensor", "rf", "rf", "rf"),
        ]},
        "role_actions": {p["role"]: {"read": {"kind": "read"}} for p in profiles},
        "observations": {"tick": 2, "setup_revision": 3, "synthetic": True,
                         "hardware_verified": False, "devices": observations},
        "last_receipt": {"device_id": "sensor", "profile_id": "profile:sensor",
                         "role": "power_sensor", "status": "ok", "values": {"source_id": "dut"}},
    }


class OperatorContextProjectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(projection, "pure public-context projector is absent")

    def project(self, value):
        return projection.project_operator_context(value)

    def test_connected_component_preserves_all_rows_and_metadata(self):
        full = context()
        before = deepcopy(full)
        out = self.project(full)
        self.assertEqual(full, before)
        self.assertEqual(out["goal"], full["goal"])
        self.assertEqual(out["schema_version"], 1)
        self.assertEqual(out["catalog"]["catalog_id"], "synthetic")
        self.assertEqual([n["id"] for n in out["topology"]["devices"]],
                         ["supply", "controller", "dut", "sensor"])
        self.assertEqual(out["topology"]["connections"], full["topology"]["connections"])
        self.assertEqual(out["catalog"]["profiles"], full["catalog"]["profiles"][:4])
        self.assertEqual(set(out["role_actions"]),
                         {"power_supply", "controller", "dut", "power_sensor"})
        self.assertEqual(set(out["observations"]["devices"]),
                         {"supply", "controller", "dut", "sensor"})
        self.assertEqual(out["last_receipt"], full["last_receipt"])
        out["observations"]["devices"]["sensor"]["values"]["source_id"] = "changed"
        self.assertEqual(full, before)

    def test_receipt_and_selected_observation_reference_seed_other_component(self):
        full = context()
        full["last_receipt"]["device_id"] = "spare"
        full["last_receipt"]["profile_id"] = "profile:spare"
        full["last_receipt"]["role"] = "spare"
        self.assertEqual(set(self.project(full)["observations"]["devices"]),
                         {"supply", "controller", "dut", "sensor", "spare"})

    def test_known_advance_receipt_without_device_still_compacts(self):
        full = context()
        full["last_receipt"] = {"hardware_verified": False, "setup_revision": 3,
                                "status": "ok", "synthetic": True, "tick": 2,
                                "values": {"advanced_ticks": 1}}
        out = self.project(full)
        self.assertEqual(out["last_receipt"], full["last_receipt"])
        self.assertEqual(len(out["topology"]["devices"]), 4)
        full = context()
        full["observations"]["devices"]["sensor"]["values"]["source_id"] = "spare"
        self.assertEqual(set(self.project(full)["observations"]["devices"]),
                         {"supply", "controller", "dut", "sensor", "spare"})

    def test_ambiguous_or_dangling_topology_falls_back_to_detached_full_copy(self):
        for mutate in (
            lambda x: x["topology"]["connections"].append(edge("missing", "sensor", "rf", "rf", "rf")),
            lambda x: x["topology"]["devices"].append(deepcopy(x["topology"]["devices"][0])),
            lambda x: x["catalog"]["profiles"].append(deepcopy(x["catalog"]["profiles"][0])),
            lambda x: x["topology"].update(other="unknown"),
            lambda x: x["observations"]["devices"].pop("spare"),
        ):
            full = context()
            mutate(full)
            out = self.project(full)
            self.assertEqual(out, full)
            self.assertIsNot(out, full)

    def test_cycle_in_unselected_component_does_not_disappear(self):
        full = context()
        spare = full["catalog"]["profiles"][-1]
        spare["ports"]["inputs"]["feedback"] = "rf"
        full["topology"]["connections"].append(
            edge("spare", "spare", "rf", "unused", "feedback"))
        self.assertEqual(self.project(full), full)

    def test_invalid_or_private_in_omitted_profile_and_node_is_rejected_before_prune(self):
        for section, key in (("profile", "unknown"), ("profile", "remaining_budget"),
                             ("observation", "seed")):
            full = context()
            if section == "profile":
                full["catalog"]["profiles"][-1][key] = "forbidden"
            else:
                full["observations"]["devices"]["spare"][key] = "forbidden"
            with self.assertRaises(ModelOperatorBoundaryError) as caught:
                self.project(full)
            self.assertEqual(caught.exception.code, "model_operator_boundary_invalid_input")

    def test_original_full_is_never_rewritten_by_budget_or_output(self):
        full = context()
        full["remaining_budget"] = {"decisions": 1}
        with self.assertRaises(ModelOperatorBoundaryError):
            self.project(full)
        self.assertIn("remaining_budget", full)

    def test_missing_source_reference_keeps_detached_full_context(self):
        full = context()
        full["observations"]["devices"]["sensor"]["values"]["source_id"] = "missing-device"
        before = deepcopy(full)
        out = self.project(full)
        self.assertEqual(out, before)
        self.assertIsNot(out, full)
        self.assertEqual(len(out["topology"]["devices"]), 5)
        out["observations"]["devices"]["sensor"]["values"]["source_id"] = "changed"
        self.assertEqual(full, before)

    def test_unknown_explicit_reference_in_selected_payload_keeps_full_context(self):
        fields = ("device_id", "source_id", "input_source_id", "reference_source_id")
        for location in ("sensor", "receipt", "profile", "action"):
            for field in fields:
                with self.subTest(location=location, field=field):
                    full = context()
                    if location == "sensor":
                        payload = full["observations"]["devices"][location]["values"]
                    elif location == "receipt":
                        payload = full["last_receipt"]["values"]
                    elif location == "profile":
                        payload = {}
                        full["catalog"]["profiles"][2]["context"] = {"nested": [payload]}
                    else:
                        payload = {}
                        full["role_actions"]["dut"]["read"]["parameters"] = {"nested": [payload]}
                    payload[field] = "missing-device"
                    before = deepcopy(full)
                    out = self.project(full)
                    self.assertEqual(out, before)
                    self.assertIsNot(out, full)
                    self.assertIsNot(out["observations"]["devices"], full["observations"]["devices"])
                    self.assertEqual(full, before)

    def test_unselected_unknown_reference_does_not_prevent_compaction(self):
        for field in ("device_id", "source_id", "input_source_id", "reference_source_id"):
            for identity in ("missing-device", None):
                with self.subTest(field=field, identity=identity):
                    full = context()
                    full["observations"]["devices"]["spare"]["values"][field] = identity
                    full["catalog"]["profiles"][4]["context"] = {field: identity}
                    full["role_actions"]["spare"]["read"]["parameters"] = {field: identity}
                    before = deepcopy(full)
                    out = self.project(full)
                    self.assertEqual(len(out["topology"]["devices"]), 4)
                    self.assertNotIn("spare", out["observations"]["devices"])
                    self.assertEqual(full, before)

    def test_reference_added_to_closure_is_checked_before_pruning(self):
        full = context()
        extra = profile("extra", "extra")
        full["catalog"]["profiles"].append(extra)
        full["topology"]["devices"].append({"id": "extra", "profile_id": "profile:extra"})
        full["observations"]["devices"]["extra"] = {
            "device_id": "extra", "profile_id": "profile:extra", "role": "extra",
            "status": "ok", "values": {}}
        full["role_actions"]["extra"] = {"read": {"kind": "read"}}
        full["observations"]["devices"]["sensor"]["values"]["source_id"] = "spare"
        full["observations"]["devices"]["spare"]["values"]["source_id"] = "missing-device"
        out = self.project(full)
        self.assertEqual(len(out["topology"]["devices"]), 6)
        self.assertEqual(out, full)
        self.assertIsNot(out, full)

    def test_unresolved_source_value_types_keep_full_context(self):
        for field in ("source_id", "input_source_id", "reference_source_id"):
            for identity in (None, False, 0, "", [], {}):
                with self.subTest(field=field, identity=identity):
                    full = context()
                    full["observations"]["devices"]["sensor"]["values"][field] = identity
                    self.assertEqual(self.project(full), full)

    def test_known_explicit_references_keep_closure_and_normal_compaction(self):
        for field in ("device_id", "source_id", "input_source_id", "reference_source_id"):
            for identity, count in (("dut", 4), ("spare", 5)):
                with self.subTest(field=field, identity=identity):
                    full = context()
                    full["observations"]["devices"]["sensor"]["values"][field] = identity
                    out = self.project(full)
                    self.assertEqual(len(out["topology"]["devices"]), count)
                    self.assertEqual(out["observations"]["devices"]["sensor"],
                                     full["observations"]["devices"]["sensor"])

    def test_unrelated_text_and_other_id_domains_still_compact(self):
        full = context()
        full["catalog"]["profiles"][2]["context"] = {
            "description": "missing-device", "source": "missing-device",
            "profile_id": "external-profile", "reference": "missing-device"}
        out = self.project(full)
        self.assertEqual(len(out["topology"]["devices"]), 4)
        self.assertEqual(out["catalog"]["profiles"][2], full["catalog"]["profiles"][2])

    def test_original_host_prompt_cap_is_checked_before_compaction(self):
        full = context()
        full["catalog"]["profiles"][-1]["capability_scope"] = "x" * 270000
        ids = {"run_id": "r", "runtime_instance_id": "i", "decision_id": "d",
               "model_request_id": "m"}
        delegation = {"scope": "rf_sensor_proposal_v1",
                      "harness_budgets": {"decisions": 8, "logical_requests": 8,
                                          "ticks": 8, "wall_seconds": 30,
                                          "transport_retries": 0},
                      "outer_limits": {"wall_seconds": 30, "model_calls": 8}}
        compact = self.project(full)
        self.assertLess(len(loop._C(loop._build(compact, producer_name="p",
                                                 delegation=delegation, **ids))), 262144)
        self.assertGreater(len(loop._C(loop._build(full, producer_name="p",
                                                    delegation=delegation, **ids))), 262144)
        with self.assertRaises(loop._Fault) as caught:
            loop._validate_full_prompt(public=full, producer_name="p",
                                       delegation=delegation, ids=ids)
        self.assertEqual(caught.exception.code, "operator_virtual_loop_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
