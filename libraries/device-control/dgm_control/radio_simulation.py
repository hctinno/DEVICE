"""Coupled synthetic source and analyzer peers; not waveform or conformance physics."""
from copy import deepcopy
import math

from dgm_lab.transport import Transport
from dgm_lab.core import InstrumentError
from dgm_rf import Catalog, ScriptedTransport, NfcRequest
from dgm_rf.cmw_lte import LteRmcConfig, lte_rmc_plan
from .virtual_world import World, Scenario, Fault
from .radio_contracts import at_steps, simulation_phone_profile


class RadioWorld(World):
    def __init__(self, plan):
        super().__init__(Scenario(noise_floor_dbm=plan["simulation"]["noise_dbm"]))
        self.plan = deepcopy(plan)
        self.source = {"tx": False, "configured": False, "kind": plan["radio"], "requested_tx": deepcopy(plan["tx"])}

    def signals(self):
        m = self.plan["simulation"]
        if not self.source["tx"]: return []
        loss = m["path_loss_db"]
        if self.plan["schema_version"] == 2:
            model = self.plan["scan"]["simulation"]
            if self.route not in model["route_loss_db"]: return []
            loss += model["route_loss_db"][self.route]
            loss += 6 * (1-math.cos(math.radians(self.motion["positions"][1]-model["peak_angle_deg"])))
            loss += .02 * abs(self.motion["positions"][0]-model["peak_height_cm"])
            if self.motion["polarization"] != "P"+model["peak_polarization"]:
                loss += model["cross_polar_loss_db"]
        return [(m["center_hz"], m["tx_dbm"]-loss, m["bandwidth_hz"])]

    def snapshot(self):
        return deepcopy({"simulated": True, "physical_verified": False, "source": self.source,
                         "revision": self.revision, "synthetic_assumptions": self.plan["simulation"],
                         "motion": self.motion, "route": self.route, "scan_assumptions": self.plan.get("scan", {}).get("simulation")})

    def inject(self, name):
        facilities = {"motion-timeout": Fault("Co3000", "GO", "stuck"),
                      "motion-stop-timeout": Fault("Co3000", "ES"),
                      "switch-timeout": Fault("OspSwitch", "ROUT:CLOS (@F01A11(0201))"),
                      "switch-stop-timeout": Fault("OspSwitch", "ROUT:CLOS (@F01A11(0101))")}
        if name in facilities:
            self.faults.append(facilities[name])
            return
        if name == "measure-timeout":
            self.faults.append(Fault("SpectrumAnalyzer", "TRAC:DATA? TRACE1", occurrence=2))
            return
        if name not in ("start-timeout", "stop-timeout"):
            return
        start = name == "start-timeout"
        radio = self.plan["radio"]
        occurrence = 1
        if radio in ("bluetooth", "uwb"):
            setup, cleanup = at_steps(self.plan)
            key, args = setup[-1] if start else cleanup[0]
            command = Catalog().build(key, profile=simulation_phone_profile(self.plan), **args).wire
            device = "PhoneAt"
            if radio == "uwb" and not start:
                occurrence = 2  # same OFF also starts setup
        elif radio == "cellular":
            p = lte_rmc_plan(LteRmcConfig(**self.plan["tx"]))
            command, device = (p["start"][-1] if start else p["cleanup"][-1]), "CmwLte"
            if not start:
                occurrence = 2
        else:
            command, device = ("31" if start else "32"), "NfcPrbs"
        self.faults.append(Fault(device, command, occurrence=occurrence))


class RadioAtPeer(ScriptedTransport):
    def __init__(self, world):
        super().__init__()
        self.world = world
        profile, catalog = simulation_phone_profile(world.plan), Catalog()
        setup, cleanup = at_steps(world.plan)
        self.setup = [catalog.build(key, profile=profile, **args).wire for key, args in setup]
        self.cleanup = [catalog.build(key, profile=profile, **args).wire for key, args in cleanup]
        self.index = 0

    def exchange(self, wire, timeout):
        if self.closed or self.desynchronized:
            raise InstrumentError("Virtual AT session unavailable")
        try:
            self.world.fault("PhoneAt", wire)
        except BaseException:
            self.desynchronized = True
            raise
        if self.index < len(self.setup) and wire == self.setup[self.index]:
            self.index += 1
            self.world.source["configured"] = True
            self.world.source["tx"] = self.index == len(self.setup)
        elif wire in self.cleanup:
            self.world.source["tx"] = False
        else:
            return "ERROR"
        self.world.changed()
        return super().exchange(wire, timeout)


class RadioLtePeer(Transport):
    def __init__(self, world, log):
        super().__init__("simulation://CmwLte", log=log)
        self.world = world
        self.plan = lte_rmc_plan(LteRmcConfig(**world.plan["tx"]))
        self.cell, self.connected, self.reply = False, False, None

    def _write(self, command):
        self.world.fault("CmwLte", command)
        self.reply = None
        if command == "*IDN?": self.reply = "Rohde&Schwarz,CMW500,SIMULATION,0"
        elif command == "SYST:ERR?": self.reply = '0,"No error"'
        elif command == "*OPC?": self.reply = "1"
        elif command == self.plan["start"][0]: self.cell = True
        elif command == self.plan["start"][1] and self.cell:
            self.connected = True
            self.world.source["tx"] = True
        elif command in self.plan["cleanup"]:
            self.connected = False
            self.world.source["tx"] = False
            if command == self.plan["cleanup"][-1]: self.cell = False
        elif command in self.plan["configure"]:
            self.world.source["configured"] = True
        elif command == self.plan["off_query"]:
            self.reply = "ON,ADJ" if self.cell else "OFF,ADJ"
        elif command == self.plan["checkpoints"][-1]["query"]:
            self.reply = "CEST" if self.connected else "ATT" if self.cell else "OFF"
        else:
            raise InstrumentError("Unmodeled LTE command: " + command)
        self.world.source.update(cell_output=self.cell, connection_established=self.connected)
        self.world.changed()

    def _read(self):
        if self.reply is None: raise InstrumentError("No LTE query response")
        return self.reply

    def _close(self):
        pass  # closing a poisoned link does not switch RF off


class RadioNfcPeer:
    simulated = True

    def __init__(self, world):
        self.world = world

    def dispatch(self, request, timeout):
        if not isinstance(request, NfcRequest): raise ValueError("NfcRequest required")
        self.world.fault("NfcPrbs", str(request.request_id))
        self.world.source.update(configured=True, tx=request.request_id == 31)
        self.world.changed()
        return "SIMULATED_DISPATCH_ONLY"
