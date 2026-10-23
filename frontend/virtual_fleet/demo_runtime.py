"""Small synthetic UI fixture, separate from the shared device implementations.

This deliberately models six demo nodes only. Its numbers and transitions are
invented UI acceptance inputs, not report data or manufacturer specifications.
"""

import copy
import json


def _parameter(kind, unit="", required=True, **extra):
    return {"type": kind, "unit": unit, "required": required, **extra}


ROLE_ACTIONS = {
    "power_supply": {
        "configure": {"parameters": {"voltage_v": _parameter("number", "V", minimum=0, maximum=6)}, "completion": "immediate"},
        "set_output": {"parameters": {"enabled": _parameter("boolean")}, "completion": "immediate"}},
    "temperature_chamber": {
        "set_temperature": {"parameters": {"temperature_c": _parameter("number", "°C", minimum=0, maximum=60)}, "completion": "after_3_ticks"}},
    "dut": {
        "configure": {"parameters": {"frequency_mhz": _parameter("number", "MHz", minimum=100, maximum=6000),
                                      "power_dbm": _parameter("number", "dBm", minimum=-60, maximum=30)}, "completion": "immediate"},
        "set_transmit": {"parameters": {"enabled": _parameter("boolean")}, "completion": "requires_power_and_stable_environment"}},
    "attenuator": {
        "set_attenuation": {"parameters": {"loss_db": _parameter("number", "dB", minimum=0, maximum=100)}, "completion": "immediate"}},
    "rf_switch": {
        "select_path": {"parameters": {"route": _parameter("string", enum=["A", "B", "terminated"])}, "completion": "immediate"}},
    "power_meter": {
        "start": {"parameters": {}, "completion": "after_2_ticks"},
        "cancel": {"parameters": {}, "completion": "immediate"},
        "recover": {"parameters": {}, "completion": "immediate"}},
}


def create_demo():
    definitions = [
        ("supply", "power_supply", "DC 전원", {}, {"power": "power"}),
        ("chamber", "temperature_chamber", "항온 챔버", {}, {"environment": "environment"}),
        ("dut", "dut", "합성 스마트폰", {"power": "power", "environment": "environment"}, {"rf": "rf"}),
        ("pad", "attenuator", "가변 감쇠기", {"rf": "rf"}, {"rf": "rf"}),
        ("switch", "rf_switch", "RF 경로 제어기", {"rf": "rf"}, {"rf": "rf"}),
        ("meter", "power_meter", "가상 전력계", {"rf": "rf"}, {"measurement": "measurement"}),
    ]
    profiles = [{"profile_id": f"demo-{device}", "model": f"DGM Demo · {label}", "manufacturer": "DGM synthetic fixture",
                 "role": role, "variant": "UI acceptance fixture", "ports": {"inputs": inputs, "outputs": outputs},
                 "simulation_basis": "invented_UI_fixture_policy", "profile_kind": "fixture",
                 "capability_scope": "6개 합성 노드의 화면·상태 전이만 검증. 공유 장비 모델/제조사 정밀도 미검증.",
                 "evidence_refs": ["synthetic:VLAB-ALL-001-ui"]} for device, role, label, inputs, outputs in definitions]
    profiles.append({"profile_id": "demo-context", "model": "DGM Demo · 검사 현미경", "manufacturer": "DGM synthetic fixture",
                     "role": "inspection_microscope", "variant": "undeployed_context", "profile_kind": "context",
                     "ports": {"inputs": {}, "outputs": {}}, "evidence_refs": [],
                     "simulation_basis": "catalog_context_only", "capability_scope": "미배치 · 동작 미구현 · 실행 검증 없음"})
    catalog = {"schema_version": 1, "catalog_id": "synthetic-ui-fixture", "fixture": True,
               "source_basis": "synthetic_only", "profiles": profiles}
    topology = {"devices": [{"id": device, "profile_id": f"demo-{device}"} for device, *_ in definitions],
                "connections": [{"source": {"device_id": source, "port": source_port},
                                 "target": {"device_id": target, "port": target_port}, "kind": kind}
                                for source, source_port, target, target_port, kind in [
                                    ("supply", "power", "dut", "power", "power"),
                                    ("chamber", "environment", "dut", "environment", "environment"),
                                    ("dut", "rf", "pad", "rf", "rf"),
                                    ("pad", "rf", "switch", "rf", "rf"),
                                    ("switch", "rf", "meter", "rf", "rf")]]}
    return DemoRuntime(catalog), catalog, topology, copy.deepcopy(ROLE_ACTIONS)


class DemoRuntime:
    def __init__(self, catalog):
        self.catalog = copy.deepcopy(catalog)
        self.tick, self.revision, self.sequence = 0, 0, 0
        self.voltage, self.output, self.transmit = 3.8, False, False
        self.temperature, self.stable_at = 23.0, 0
        self.frequency, self.power, self.loss, self.route = 2440.0, 10.0, 6.0, "A"
        self.measurement = {"state": "idle"}
        self.receipts = {}

    def _envelope(self):
        return {"tick": self.tick, "setup_revision": self.revision, "synthetic": True, "hardware_verified": False}

    def _signal(self):
        if not self.output or self.voltage <= 0:
            return None, "power_unavailable"
        if self.tick < self.stable_at:
            return None, "environment_settling"
        if not self.transmit:
            return None, "dut_not_transmitting"
        if self.route == "terminated":
            return None, "rf_path_terminated"
        return self.power - self.loss - (0.5 if self.route == "B" else 0), None

    def _once(self, request_id, signature, operation):
        serialized = json.dumps(signature, sort_keys=True, allow_nan=False)
        if request_id in self.receipts:
            previous, result = self.receipts[request_id]
            if serialized != previous:
                return {**self._envelope(), "status": "error", "values": {"reason": "request_id_conflict"}}
            return copy.deepcopy(result)
        self.sequence += 1
        result = operation()
        self.receipts[request_id] = serialized, copy.deepcopy(result)
        return result

    def execute(self, request_id, device_id, action, parameters=None):
        parameters = parameters or {}
        def operation():
            changed, status, values = False, "ok", {}
            role = next((profile["role"] for profile in self.catalog["profiles"] if profile["profile_id"] == f"demo-{device_id}"), None)
            if action not in ROLE_ACTIONS.get(role, {}):
                return {**self._envelope(), "status": "unsupported", "values": {}, "setup_changed": False}
            if device_id == "supply":
                if action == "configure":
                    self.voltage = parameters["voltage_v"]
                else:
                    self.output = parameters["enabled"]
                changed = True
            elif device_id == "chamber":
                self.temperature = parameters["temperature_c"]
                self.stable_at = self.tick + 3
                status, changed = "pending", True
            elif device_id == "dut":
                if action == "configure":
                    self.frequency, self.power = parameters["frequency_mhz"], parameters["power_dbm"]
                else:
                    self.transmit = parameters["enabled"]
                changed = True
            elif device_id == "pad":
                self.loss, changed = parameters["loss_db"], True
            elif device_id == "switch":
                self.route, changed = parameters["route"], True
            elif action in ("cancel", "recover"):
                self.measurement = {"state": "cancelled" if action == "cancel" else "idle"}
            elif action == "start":
                power, reason = self._signal()
                self.measurement = {"state": "invalid" if reason else "pending", "acquired_setup_revision": self.revision,
                                    "started_tick": self.tick, "ready_tick": self.tick + 2}
                status = "invalid" if reason else "pending"
                if reason:
                    self.measurement["reason"] = reason
                    values["reason"] = reason
            if changed:
                self.revision += 1
                if self.measurement["state"] in ("pending", "completed"):
                    self.measurement.pop("power_dbm", None)
                    self.measurement.update(state="invalid", reason="setup_revision_changed")
            return {**self._envelope(), "status": status, "values": values, "setup_changed": changed}
        return self._once(request_id, ["execute", device_id, action, parameters], operation)

    def advance(self, request_id, ticks=1):
        def operation():
            self.tick += ticks
            if self.measurement["state"] == "pending" and self.tick >= self.measurement["ready_tick"]:
                power, reason = self._signal()
                if reason:
                    self.measurement.update(state="invalid", reason=reason)
                else:
                    self.measurement.update(state="completed", power_dbm=power, completed_tick=self.tick)
            return {**self._envelope(), "status": "ok", "values": {}, "setup_changed": False}
        return self._once(request_id, ["advance", ticks], operation)

    def observations(self):
        power, reason = self._signal()
        signal = {"frequency_mhz": self.frequency, "power_dbm": power, "synthetic": True} if power is not None else None
        rf_source = {"frequency_mhz": self.frequency, "power_dbm": self.power, "synthetic": True} if self.output and self.transmit and self.tick >= self.stable_at else None
        pending = self.measurement["state"] == "pending"
        meter_values = {key: value for key, value in self.measurement.items() if key != "state"}
        if pending:
            meter_values["remaining_ticks"] = max(0, self.measurement["ready_tick"] - self.tick)
        values = {
            "supply": ("ok", "output_on" if self.output else "output_off", {"voltage_v": self.voltage, "enabled": self.output, "outputs": {"power": {"voltage_v": self.voltage, "enabled": self.output}}}),
            "chamber": ("pending" if self.tick < self.stable_at else "ok", "settling" if self.tick < self.stable_at else "stable", {"temperature_c": self.temperature, "remaining_ticks": max(0, self.stable_at - self.tick), "outputs": {"environment": {"temperature_c": self.temperature, "stable": self.tick >= self.stable_at}}}),
            "dut": ("invalid" if self.transmit and reason else "ok", "transmitting" if rf_source else "standby", {"frequency_mhz": self.frequency, "configured_power_dbm": self.power, "transmit_requested": self.transmit, "reason": reason, "outputs": {"rf": rf_source} if rf_source else {}}),
            "pad": ("ok" if rf_source else "invalid", "connected" if rf_source else "input_missing", {"loss_db": self.loss, "outputs": {"rf": {**rf_source, "power_dbm": self.power - self.loss}} if rf_source else {}}),
            "switch": ("ok" if signal else "invalid", "routed" if signal else "no_signal", {"route": self.route, "outputs": {"rf": signal} if signal else {}}),
            "meter": ("pending" if pending else "invalid" if self.measurement["state"] == "invalid" else "ok", self.measurement["state"], meter_values),
        }
        return {**self._envelope(), "devices": {device: {**self._envelope(), "profile_id": f"demo-{device}", "status": status, "state": state, "values": data} for device, (status, state, data) in values.items()}}

    def coverage(self):
        return {"basis": "synthetic_UI_fixture_only", "hardware_verified": False,
                "profiles": [{"profile_id": profile["profile_id"], "implemented": profile["role"] in ROLE_ACTIONS,
                              "acceptance": "fixture_only" if profile["role"] in ROLE_ACTIONS else "not_run"} for profile in self.catalog["profiles"]]}
