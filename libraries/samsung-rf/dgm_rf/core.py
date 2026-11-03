"""Samsung RF control. Static command knowledge is separate from device support."""
from __future__ import annotations
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
from importlib.resources import files
import json
import math
import re
import threading
import time
import uuid


class RFError(Exception):
    pass


class CommandRejected(RFError):
    pass


class ResponseError(RFError):
    pass


class UncorrelatedResponse(ResponseError):
    pass


class CleanupError(RFError):
    def __init__(self, failures):
        self.failures = failures
        super().__init__("RF OFF unconfirmed; cleanup failures: " + repr(failures))


@dataclass(frozen=True)
class Profile:
    model: str
    build: str
    allowed_commands: frozenset[str] = frozenset()
    argument_domains: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    simulation_only: bool = True
    evidence_notes: str = ""

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8-sig") as fp:
            data = json.load(fp)
        data["allowed_commands"] = frozenset(data.get("allowed_commands", []))
        return cls(**data)


@dataclass(frozen=True)
class Command:
    id: str
    wire: str
    family: str
    first_arg: str
    response: str
    effect: str


def scalar(value, kind):
    if isinstance(value, bool):
        raise CommandRejected("Boolean is not an AT numeric argument")
    value = str(value)
    if len(value) > 128 or not re.fullmatch(r"[A-Za-z0-9_.:+-]+", value):
        raise CommandRejected("Invalid token or command delimiter in argument")
    if kind == "int" and not re.fullmatch(r"-?\d+", value):
        raise CommandRejected("Integer argument required")
    if kind == "number":
        try:
            if not Decimal(value).is_finite():
                raise CommandRejected("Finite number required")
        except InvalidOperation as exc:
            raise CommandRejected("Numeric argument required") from exc
    return value


class Catalog:
    def __init__(self):
        self.data = json.loads(files("dgm_rf").joinpath("data/catalog.json").read_text(encoding="utf-8"))
        self.entries = {entry["id"]: entry for entry in self.data["commands"]}

    def search(self, query="", radio=None):
        return [entry for entry in self.entries.values()
                if (radio is None or entry["radio"] == radio)
                and query.lower() in json.dumps(entry, ensure_ascii=False).lower()]

    def build(self, command_id, *, profile=None, **arguments):
        if command_id not in self.entries:
            raise CommandRejected("Unknown command: " + command_id)
        entry = self.entries[command_id]
        if entry["status"] not in ("static_ready", "needs_profile"):
            raise CommandRejected(command_id + ": " + entry["status"])
        specs = entry["parameters"]
        if set(arguments) != set(specs):
            raise CommandRejected(f"Expected parameters {sorted(specs)}, got {sorted(arguments)}")
        encoded = {}
        for name, spec in specs.items():
            value = scalar(arguments[name], spec["type"])
            if spec['type'] == 'int':
                for bound, comparison in [('minimum', lambda a,b: a < b), ('maximum', lambda a,b: a > b)]:
                    if spec.get(bound) is not None and comparison(int(value), spec[bound]):
                        raise CommandRejected(f"{command_id}.{name}: outside codec bounds")
            domain = spec["domain"]
            if domain is not None and value not in domain:
                raise CommandRejected(f"{command_id}.{name}: value outside source table")
            custom = (profile.argument_domains.get(command_id, {}) if profile else {}).get(name)
            if domain is None and not custom:
                raise CommandRejected(f"{command_id}.{name}: device-specific argument domain required")
            if custom is not None and value not in [str(x) for x in custom]:
                raise CommandRejected(f"{command_id}.{name}: value outside device profile")
            encoded[name] = value
        wire = entry["template"].format(**encoded)
        if "{" in wire or wire.count("=") != 1 or len(wire.split("=")[1].split(",")) != entry["arg_count"]:
            raise CommandRejected("Incomplete/invalid command template")
        return Command(command_id, wire, entry["family"], entry["fixed_args"][0], entry["response"], entry["effect"])


def parse_response(command, raw):
    """A trailing OK is a terminator, NOT proof of Samsung operation success."""
    lines = [line.strip() for line in raw.replace("\r", "\n").split("\n") if line.strip()]
    if not lines or lines[-1] != "OK":
        raise UncorrelatedResponse("Missing final OK or terminal ERROR: " + raw)
    if any(re.search(r"^(?:ERROR|\+CM[ES]\s*ERROR)", line, re.I) for line in lines):
        raise ResponseError("AT error: " + raw)
    expected = "+" + command.family + ":"
    results = [line[len(expected):].strip() for line in lines if line.upper().startswith(expected)]
    if len(results) != 1:
        raise UncorrelatedResponse("Missing or ambiguous family result: " + raw)
    first, separator, payload = results[0].partition(",")
    if not separator or first.strip() != command.first_arg:
        raise UncorrelatedResponse("Response argument mismatch: " + raw)
    payload = payload.strip()
    if not payload or re.search(r"(?:^|[, :])(NG|NA|FAIL|FAILED|ERROR|NOT_SUPPORT|NOT_SUPPORTED)(?:$|[, :])", payload, re.I) or re.search(r"(?:_FAILED|_ERROR)$", payload, re.I):
        raise ResponseError("Device rejected operation: " + raw)
    if command.response == "status" and payload.upper() not in ("OK", "PASS"):
        raise ResponseError("Unrecognized success status: " + raw)
    return payload


class ScriptedTransport:
    """Simulation only. Script entries may be response strings or exceptions."""
    simulated = True

    def __init__(self, responses=None):
        self.responses = deque(responses or [])
        self.sent = []
        self.desynchronized = False
        self.closed = False

    def exchange(self, wire, timeout):
        if self.closed or self.desynchronized:
            raise RFError("Transport unavailable/desynchronized")
        self.sent.append(wire)
        if self.responses:
            result = self.responses.popleft()
            if isinstance(result, BaseException):
                if isinstance(result, TimeoutError):
                    self.desynchronized = True
                raise result
            return result
        family = wire.split("=")[0][3:]
        arg = wire.split("=")[1].split(",")[0]
        return f"\r\n+{family}:{arg},OK\r\n\r\nOK\r\n"

    def emergency_write(self, wire):
        if self.closed:
            raise RFError("Transport closed")
        self.sent.append(wire)

    def close(self):
        self.closed = True


class SerialTransport:
    """One port, one owner, CR terminated ASCII. No automatic retry/reconnect."""
    simulated = False

    def __init__(self, port, baudrate, *, serial_instance=None):
        if not port or isinstance(baudrate, bool) or not isinstance(baudrate, int) or baudrate <= 0:
            raise ValueError("Explicit port and positive baudrate required")
        if serial_instance is None:
            try:
                import serial
            except ImportError as exc:
                raise RFError('Install optional dependency: python -m pip install ".[serial]"') from exc
            serial_instance = serial.Serial(port=port, baudrate=baudrate, timeout=0.05, write_timeout=2)
        self.serial = serial_instance
        self.desynchronized = False
        self.closed = False
        self.lock = threading.Lock()

    def exchange(self, wire, timeout):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Positive finite timeout required")
        with self.lock:
            if self.closed or self.desynchronized:
                raise RFError("Transport unavailable/desynchronized; inspect device before a new connection")
            # Never discard pending bytes: they may be a delayed response.
            if self.serial.in_waiting:
                self.desynchronized = True
                raise RFError("Unconsumed serial input; cannot correlate next response")
            buffer = bytearray()
            try:
                encoded = (wire + "\r").encode("ascii")
                count = self.serial.write(encoded)
                if count != len(encoded):
                    raise OSError("Partial serial write")
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    chunk = self.serial.read(max(1, min(self.serial.in_waiting, 4096)))
                    buffer.extend(chunk)
                    if len(buffer) > 65536:
                        raise ResponseError("Response exceeded 64 KiB")
                    # Wait for trailing OK even after CME errors, which Samsung may follow with OK.
                    if re.search(rb"(?:^|[\r\n])OK(?:\r\n|\n)$", buffer):
                        return buffer.decode("ascii", errors="strict")
                    if re.search(rb"(?:^|[\r\n])ERROR(?:\r\n|\n)$", buffer):
                        self.desynchronized = True
                        return buffer.decode("ascii", errors="strict")
                raise TimeoutError("AT response timeout; partial=" + repr(bytes(buffer)))
            except BaseException:
                self.desynchronized = True
                raise

    def emergency_write(self, wire):
        with self.lock:
            if self.closed:
                raise RFError("Transport closed")
            self.desynchronized = True
            encoded = (wire + "\r").encode("ascii")
            if self.serial.write(encoded) != len(encoded):
                raise OSError("Partial emergency write")

    def close(self):
        self.serial.close()
        self.closed = True


class Controller:
    def __init__(self, transport, profile=None, *, catalog=None):
        self.transport = transport
        self.profile = profile
        self.catalog = catalog or Catalog()
        self.log = []
        self.run_id = str(uuid.uuid4())
        self.lock = threading.RLock()

    def _authorize(self, command):
        if not self.transport.simulated:
            if not self.profile or self.profile.simulation_only or not self.profile.model or not self.profile.build:
                raise CommandRejected("A model/build-specific non-simulation profile is required")
            if command.id not in self.profile.allowed_commands:
                raise CommandRejected("Command not enabled in this device profile: " + command.id)
            scope = self.catalog.entries[command.id].get('device_scope')
            if scope and (self.profile.model != scope['model'] or self.profile.build != scope['build']):
                raise CommandRejected('Command restricted to source model/build: ' + repr(scope))

    def execute(self, command_id, *, timeout=15.0, **arguments):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Positive finite timeout required")
        with self.lock:
            cmd = self.catalog.build(command_id, profile=self.profile, **arguments)
            self._authorize(cmd)
            event = dict(run_id=self.run_id, command_id=cmd.id, command=cmd.wire, timestamp=time.time(),
                         simulated=self.transport.simulated, status="attempted")
            self.log.append(event)
            try:
                raw = self.transport.exchange(cmd.wire, timeout)
                event["raw_response"] = raw
                value = parse_response(cmd, raw)
                event.update(status="acknowledged", value=value, rf_measured=False)
                return value
            except BaseException as exc:
                if isinstance(exc, UncorrelatedResponse):
                    self.transport.desynchronized = True
                event.update(status="failed", error=repr(exc), rf_measured=False)
                raise

    def _cleanup(self, steps):
        failures = []
        for command_id, arguments in steps:
            try:
                cmd = self.catalog.build(command_id, profile=self.profile, **arguments)
                self._authorize(cmd)
                if self.transport.desynchronized:
                    self.transport.emergency_write(cmd.wire)
                    self.log.append(dict(run_id=self.run_id, command_id=cmd.id, command=cmd.wire,
                                         timestamp=time.time(), simulated=self.transport.simulated,
                                         status="cleanup_sent_unconfirmed", rf_measured=False))
                    failures.append(command_id + ": sent without a correlatable acknowledgement")
                else:
                    self.execute(command_id, **arguments)
            except BaseException as exc:
                failures.append(command_id + ": " + repr(exc))
        if failures:
            raise CleanupError(failures)

    @contextmanager
    def session(self, setup, cleanup, *, cancelled=None):
        """Validate whole plan before I/O; cleanup runs for failure and cancellation."""
        setup, cleanup = list(setup), list(cleanup)
        if not cleanup:
            raise CommandRejected("Explicit cleanup sequence required")
        with self.lock:
            for command_id, arguments in setup + cleanup:
                cmd = self.catalog.build(command_id, profile=self.profile, **arguments)
                self._authorize(cmd)
            original = None
            try:
                for command_id, arguments in setup:
                    if cancelled and cancelled.is_set():
                        raise InterruptedError("RF session cancelled")
                    self.execute(command_id, **arguments)
                yield self
            except BaseException as exc:
                original = exc
                raise
            finally:
                try:
                    self._cleanup(cleanup)
                except CleanupError as exc:
                    if original is not None:
                        raise BaseExceptionGroup("Operation failed and RF OFF is unconfirmed", [original, exc]) from None
                    raise

    @contextmanager
    def wlan_tx(self, config, *, cancelled=None):
        setup, cleanup = wlan_tx_plan(config)
        with self.session(setup, cleanup, cancelled=cancelled):
            yield self

    def save_log(self, path):
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(self.log, fp, ensure_ascii=False, indent=2)
            fp.write("\n")


@dataclass(frozen=True)
class WlanTxConfig:
    band: int
    bandwidth: int
    channel_argument: int
    rate: int
    antenna: int
    gi: int
    encoding: int
    power: str
    burst: int
    payload: int
    tx_mode: int = 1


def wlan_tx_plan(config):
    if config.band == 3 and config.bandwidth not in (6,7,8,9,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25):
        raise CommandRejected("6 GHz requires a HE/EHT selection in this profile")
    if config.band not in (1,2,3):
        raise CommandRejected("Unknown band")
    if config.band == 3 and config.bandwidth in (6,7,8,9,11,12):
        if not 15 <= config.rate <= 26:
            raise CommandRejected("6 GHz HE profile requires MCS0..11 codes 15..26")
        if config.gi not in (5,6,7):
            raise CommandRejected("HE GI must be 0.8/1.6/3.2 us (codes 5/6/7)")
    pairs = [
        ("0_1_1", 0), ("0_0_6", config.band), ("0_0_0", config.channel_argument),
        ("0_7_0", config.antenna), ("0_0_1", config.rate), ("0_0_2", config.gi),
        ("0_0_5", config.burst), ("0_0_4", config.payload), ("0_0_7", config.bandwidth),
        ("0_1_5", config.encoding), ("0_0_3", config.power), ("0_2_1", config.tx_mode)]
    return ([("wifitest_" + key, {"value": value}) for key,value in pairs],
            [("wifitest_0_2_0", {"value": 0}), ("wifitest_0_1_0", {"value": 0})])
