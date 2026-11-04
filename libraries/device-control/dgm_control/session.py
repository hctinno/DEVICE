"""One common connection/lifecycle entry; native reviewed drivers own wire I/O."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, is_dataclass
import inspect
import threading

from .catalog import UnsupportedDevice
from .profiles import require_profile, _phone_profile


LIFECYCLES = {"SignalGenerator": "emitting", "Cmu200Cw": "emitting", "PowerSupply": "powering", "OdaEx": "powering",
              "CmwLte": "connected", "Thermotron8800": "running", "EspecController": "running", "OspSwitch": "routed"}


class SessionError(RuntimeError):
    pass


class DeviceSession:
    def __init__(self, descriptor, driver, *, simulated):
        self._descriptor = deepcopy(descriptor)
        self._driver = driver
        self.simulated = simulated
        self.closed = False
        self._active = False
        self._lock = threading.RLock()

    def _check(self):
        if self.closed:
            raise SessionError("Session closed")

    @property
    def info(self):
        identity = getattr(self._driver, "identity", None)
        return {"device_id": self._descriptor["id"], "simulated": self.simulated, "physical_verified": False,
                "identity": asdict(identity) if is_dataclass(identity) else None,
                "identity_source": "instrument_response" if identity is not None else "profile_declared_not_readback",
                "connected": not self.closed, "active": self._active}

    @property
    def phone_log(self):
        return deepcopy(getattr(self._driver, "log", []))

    def call(self, operation, **kwargs):
        with self._lock:
            self._check()
            if operation == "start":
                raise SessionError("Use with device.active(): to pair start with cleanup")
            if operation not in self._descriptor["operations"]:
                raise UnsupportedDevice(f"Operation {operation!r} is not exposed for {self._descriptor['id']}")
            if operation == "select" and not self._active:
                raise SessionError("Use active(name=path) for an OSP route and safe-path cleanup")
            method = getattr(self._driver, operation)
            inspect.signature(method).bind(**kwargs)
            return method(**kwargs)

    @contextmanager
    def active(self, **kwargs):
        """Own a reviewed start/stop scope. Cleanup acknowledgement is not RF proof.

        CO3000 ES stops all attached axes, including axes outside the profile.
        OSP cleanup restores the configured safe route; it does not switch off RF.
        """
        from dgm_lab.core import managed_run
        with self._lock:
            self._check()
            if self._active:
                raise SessionError("Nested active scopes are not supported")
            device_id = self._descriptor["id"]
            if device_id == "SamsungAt":
                name = "wlan_tx" if "config" in kwargs else "session"
                method = getattr(self._driver, name)
                inspect.signature(method).bind(**kwargs)
                manager = method(**kwargs)
            elif device_id in LIFECYCLES:
                method = getattr(self._driver, LIFECYCLES[device_id])
                inspect.signature(method).bind(**kwargs)
                manager = method(**kwargs)
            else:
                if kwargs:
                    raise TypeError(f"{device_id}.active accepts no arguments")
                stop = self._driver.stop_all if device_id == "Co3000" else self._driver.stop
                manager = managed_run(lambda: None, stop)
            self._active = True
            try:
                with manager:
                    yield self
            finally:
                self._active = False


@contextmanager
def open_device(profile, *, log=None):
    """Open explicitly selected backend. No discovery, fallback, reset or TX.

    Use active() for owned output/motion/route scopes. Merely closing this context
    closes the transport; it cannot claim physical RF OFF or emergency stopping.
    """
    profile = deepcopy(profile)  # freeze validated configuration for this connection
    descriptor = require_profile(profile)
    config, mode = profile["config"], profile["mode"]
    device_id = descriptor["id"]
    if device_id == "SamsungAt":
        from dgm_rf import Controller, ScriptedTransport
        from dgm_rf.core import SerialTransport
        phone_profile = _phone_profile(config, mode)
        io = ScriptedTransport() if mode == "simulation" else SerialTransport(config["transport"]["port"], config["transport"]["baudrate"])
        session = DeviceSession(descriptor, Controller(io, phone_profile), simulated=mode == "simulation")
        try:
            yield session
        finally:
            session.closed = True
            io.close()
        return
    if mode == "hardware":
        from dgm_lab.registry import connect
        with connect(config, log=log) as driver:
            session = DeviceSession(descriptor, driver, simulated=False)
            try:
                yield session
            finally:
                session.closed = True
        return
    from dgm_lab.registry import DRIVERS
    if device_id == "OdaEx":
        from dgm_lab.demo import DemoPowerSupply
        io = DemoPowerSupply(log=log)
    elif device_id == "Co3000":
        from .simulation import MotionPeer
        io = MotionPeer(log=log)
    else:
        raise UnsupportedDevice(f"No simulator for {device_id}")
    with io:
        driver = DRIVERS[device_id](io, **config["parameters"])
        driver.identify()
        session = DeviceSession(descriptor, driver, simulated=True)
        try:
            yield session
        finally:
            session.closed = True
