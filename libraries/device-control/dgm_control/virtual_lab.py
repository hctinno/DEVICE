"""Shared virtual lab and explicit hardware provider with identical session APIs."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import math
import threading

from dgm_lab.registry import DRIVERS
from dgm_rf import Controller, Catalog
from dgm_rf.core import wlan_tx_plan
from .catalog import describe, profile_template, UnsupportedDevice
from .profiles import _phone_profile, require_profile
from .session import DeviceSession, SessionError, open_device
from .virtual_world import World, Scenario, Fault
from .virtual_peers import SupplyPeer, PositionerPeer, PhonePeer, ScpiPeer


VIRTUAL_MODELS = {"PhoneAt": "6GHz HE20/40/80/160 fixture", "SpectrumAnalyzer": "N9030B",
                  "UsbPowerSensor": "NRP18S", "SignalGenerator": "SMW200A", "OdaEx": "EX60-40",
                  "OspSwitch": "OSP120 + OSP-B102", "Co3000": "MA1 + DT1"}

WLAN_DEVICES = ("OdaEx", "Co3000", "OspSwitch", "PhoneAt", "SpectrumAnalyzer", "UsbPowerSensor")


def _check_phone_plan(profile, config):
    catalog = Catalog()
    setup, cleanup = wlan_tx_plan(config)
    for command, arguments in setup + cleanup:
        if not profile.simulation_only and command not in profile.allowed_commands:
            raise ValueError(f"Hardware profile does not authorize {command}")
        catalog.build(command, profile=profile, **arguments)


class VirtualLab:
    simulated = True

    def __init__(self, scenario=None, *, log=None):
        if scenario is not None and not isinstance(scenario, Scenario):
            raise TypeError("scenario must be Scenario")
        self._world = World(scenario)
        self._log = log
        self._leased = set()

    @property
    def scenario(self):
        return asdict(self._world.scenario)

    @property
    def state(self):
        return self._world.snapshot()

    @property
    def observations(self):
        return deepcopy(self._world.measurements)

    @property
    def events(self):
        return deepcopy(self._world.events)

    @property
    def connections(self):
        with self._world.lock:
            return sorted(self._leased)

    def inject(self, fault):
        if not isinstance(fault, Fault) or fault.device not in VIRTUAL_MODELS:
            raise ValueError("Fault requires an implemented virtual device")
        if fault.kind == "stuck" and (fault.device != "Co3000" or fault.command != "GO"):
            raise ValueError("stuck is defined only for Co3000 GO")
        if fault.kind == "malformed" and "?" not in fault.command and fault.device != "PhoneAt":
            raise ValueError("malformed requires a query or phone exchange")
        with self._world.lock:
            self._world.faults.append(deepcopy(fault))

    def configuration(self, device_id):
        """Immutable-by-copy fixture parameters. Never convert these into site evidence."""
        if device_id not in VIRTUAL_MODELS:
            raise UnsupportedDevice(f"No integrated virtual peer for {device_id}")
        if device_id in {"PhoneAt", "OdaEx", "Co3000"}:
            parameters = profile_template(device_id, "simulation")["config"]["parameters"]
            if device_id == "PhoneAt":
                domains = parameters["profile"]["argument_domains"]
                domains["wifitest_0_0_0"]["value"] = list(self._world.scenario.channels_hz)
                domains["wifitest_0_0_3"]["value"] = ["-10.0", "0.0", "10.0"]
            return parameters
        if device_id == "SpectrumAnalyzer":
            return {"model": "N9030B", "max_frequency_hz": 8.4e9}
        if device_id == "UsbPowerSensor":
            return {"model": "NRP18S"}
        if device_id == "SignalGenerator":
            return {"model": "SMW200A", "max_frequency_hz": 8e9, "max_power_dbm": 10}
        return {"model": "OSP120", "modules": {"F01A11": "OSP-B102"}, "switching_enabled": True,
                "paths": {name: [{"module": "F01A11", "relay": 1, "state": state}]
                          for name, state in [("isolated", 1), ("dut", 2), ("generator", 3)]}, "safe_path": "isolated"}

    def validate_wlan(self, plan):
        parameters = self.configuration("PhoneAt")
        profile = _phone_profile({"parameters": parameters, "transport": {"kind": "simulation"}}, "simulation")
        _check_phone_plan(profile, plan.tx)
        if plan.tx.band != 3 or plan.tx.bandwidth not in (6, 7, 8, 9) or plan.tx.tx_mode != 1:
            raise ValueError("Virtual WLAN peer implements 6GHz HE20/40/80/160 packet TX only")
        frequency = self._world.scenario.channels_hz.get(str(plan.tx.channel_argument))
        if frequency is None or not math.isclose(plan.center_hz, frequency, rel_tol=0, abs_tol=.1):
            raise ValueError("Analyzer center does not match the explicit virtual channel mapping")

    @contextmanager
    def open(self, device_id):
        parameters = self.configuration(device_id)
        with self._world.lock:
            if device_id in self._leased:
                raise SessionError(f"Virtual resource already leased: {device_id}")
            self._leased.add(device_id)
        io, session = None, None
        try:
            descriptor = describe(device_id)
            if device_id == "PhoneAt":
                profile = _phone_profile({"parameters": parameters, "transport": {"kind": "simulation"}}, "simulation")
                io = PhonePeer(self._world, self._log)
                driver = Controller(io, profile)
            else:
                if device_id == "OdaEx":
                    io = SupplyPeer(self._world, self._log)
                elif device_id == "Co3000":
                    io = PositionerPeer(self._world, self._log)
                else:
                    io = ScpiPeer(device_id, self._world, self._log)
                driver = DRIVERS[device_id](io, **parameters)
                driver.identify()
            session = DeviceSession(descriptor, driver, simulated=True)
            yield session
        finally:
            if session is not None:
                session.closed = True
            try:
                if io is not None:
                    io.close()
            finally:
                with self._world.lock:
                    self._leased.discard(device_id)


class HardwareLab:
    """No discovery or connection at construction. open() performs real I/O explicitly.

    Profiles, wiring, permits, interlocks and commissioning belong to the caller.
    No automatic execution, simulation fallback or fixture-profile conversion.
    """
    simulated = False

    def __init__(self, profiles, *, log=None):
        if not isinstance(profiles, dict) or not profiles:
            raise ValueError("Explicit device_id -> hardware profile mapping required")
        self._profiles = deepcopy(profiles)
        self._log = log
        self._lock = threading.RLock()
        self._leased = set()
        for device_id, profile in self._profiles.items():
            require_profile(profile)
            if profile["mode"] != "hardware" or profile["device_id"] != device_id:
                raise ValueError("HardwareLab requires matching explicit hardware profiles")

    def validate_wlan(self, plan):
        missing = set(WLAN_DEVICES) - set(self._profiles)
        if missing:
            raise ValueError(f"Missing hardware profiles: {sorted(missing)}")
        profile = _phone_profile(self._profiles["PhoneAt"]["config"], "hardware")
        _check_phone_plan(profile, plan.tx)

    @contextmanager
    def open(self, device_id):
        with self._lock:
            profile = self._profiles[device_id]
            if device_id in self._leased:
                raise SessionError(f"Hardware resource already leased: {device_id}")
            self._leased.add(device_id)
        try:
            with open_device(profile, log=self._log) as device:
                yield device
        finally:
            with self._lock:
                self._leased.discard(device_id)
