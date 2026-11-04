"""Deterministic behavioral RF model. No waveform, calibration or compliance claim."""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import math
import threading

from dgm_lab.core import number
from dgm_lab.transport import CommunicationError


@dataclass(frozen=True)
class Scenario:
    path_loss_db: float = 20.0
    noise_floor_dbm: float = -100.0
    peak_angle_deg: float = 90.0
    peak_height_cm: float = 200.0
    cross_polar_loss_db: float = 6.0
    # Explicit fixture association, NOT a universal OEM channel argument table.
    channels_hz: dict = field(default_factory=lambda: {"17": 6.035e9, "49": 6.195e9})

    def __post_init__(self):
        for name, low, high in [("path_loss_db", 0, 200), ("noise_floor_dbm", -200, -30),
                                ("peak_angle_deg", 0, 360), ("peak_height_cm", 100, 400),
                                ("cross_polar_loss_db", 0, 60)]:
            number(getattr(self, name), name, low, high)
        if not isinstance(self.channels_hz, dict) or not self.channels_hz:
            raise ValueError("channels_hz requires explicit fixture channel arguments")
        for key, value in self.channels_hz.items():
            if not isinstance(key, str) or not key.isdecimal():
                raise ValueError("channel arguments must be decimal strings")
            number(value, "fixture frequency", 5.925e9, 7.125e9)


@dataclass
class Fault:
    device: str
    command: str
    kind: str = "timeout"
    occurrence: int = 1

    def __post_init__(self):
        if self.kind not in {"timeout", "disconnect", "malformed", "reject", "stuck"}:
            raise ValueError("Unknown fault kind")
        if type(self.occurrence) is not int or self.occurrence < 1:
            raise ValueError("occurrence must be positive integer")
        if not isinstance(self.command, str) or not self.command:
            raise ValueError("Exact command required")


class World:
    def __init__(self, scenario=None):
        self.scenario = deepcopy(scenario or Scenario())
        self.lock = threading.RLock()
        self.revision = 0
        self.phone = {"test_mode": False, "tx": False, "settings": {}}
        self.supply = {"output": False, "voltage": 0.0, "current": 0.0}
        self.generator = {"output": False, "frequency_hz": 6.035e9, "power_dbm": -20.0}
        self.motion = {"positions": [100.0, 0.0], "polarization": "PH", "moving": False}
        self.route = "isolated"
        self.faults = []
        self.events = []
        self.measurements = []
        self.instrument_settings = {}

    def changed(self):
        self.revision += 1

    def snapshot(self):
        with self.lock:
            return deepcopy({"simulated": True, "physical_verified": False, "revision": self.revision,
                             "phone": self.phone, "supply": self.supply, "generator": self.generator,
                             "motion": self.motion, "route": self.route})

    def fault(self, device, command):
        with self.lock:
            for index, rule in enumerate(self.faults):
                if rule.device != device or rule.command != command:
                    continue
                rule.occurrence -= 1
                if rule.occurrence:
                    return None
                self.faults.pop(index)
                self.events.append({"event": "fault", **asdict(rule), "revision": self.revision})
                if rule.kind == "timeout":
                    raise TimeoutError(f"Injected timeout: {device} {command}")
                if rule.kind == "disconnect":
                    raise CommunicationError(f"Injected disconnect: {device} {command}")
                return rule.kind
            return None

    def signals(self):
        """(center Hz, total received dBm, occupied width Hz). CW width is zero."""
        signals = []
        powered = self.supply["output"] and self.supply["voltage"] >= 3.0 and self.supply["current"] >= 0.1
        if self.route == "dut" and self.phone["tx"] and powered:
            values = self.phone["settings"]
            azimuth = self.motion["positions"][1]
            height = self.motion["positions"][0]
            loss = self.scenario.path_loss_db + 6 * (1 - math.cos(math.radians(azimuth - self.scenario.peak_angle_deg)))
            loss += 0.02 * abs(height - self.scenario.peak_height_cm)
            if self.motion["polarization"] == "PH":
                loss += self.scenario.cross_polar_loss_db
            signals.append((self.scenario.channels_hz[values["channel"]], float(values["power"]) - loss,
                            {"6": 20e6, "7": 40e6, "8": 80e6, "9": 160e6}[values["bandwidth"]]))
        if self.route == "generator" and self.generator["output"]:
            signals.append((self.generator["frequency_hz"], self.generator["power_dbm"] - self.scenario.path_loss_db, 0))
        return signals

    def power(self, frequency_hz=None, rbw_hz=None):
        """Broadband sensor or rectangular WLAN/gaussian CW display model."""
        with self.lock:
            milliwatts = 10 ** (self.scenario.noise_floor_dbm / 10)
            for center, dbm, bandwidth in self.signals():
                fraction = 1.0
                if frequency_hz is not None:
                    if bandwidth:
                        fraction = min(1.0, rbw_hz / bandwidth) if abs(frequency_hz - center) <= bandwidth / 2 else 0.0
                    else:
                        fraction = math.exp(-min(1000, ((frequency_hz - center) / rbw_hz) ** 2))
                milliwatts += 10 ** (dbm / 10) * fraction
            return 10 * math.log10(milliwatts)

    def observation(self, device, settings, values):
        self.measurements.append({"sequence": len(self.measurements) + 1, "device": device,
                                  "settings": deepcopy(settings), "values": deepcopy(values),
                                  "state": self.snapshot()})
