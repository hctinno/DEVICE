"""Native source adapters and RF-envelope verification, shared by real/virtual runs."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import time
import uuid

from dgm_lab import SpectrumAnalyzer, CmwLte
from dgm_lab.analyzers import Sweep
from dgm_rf import Controller, NfcPrbsController, AdbNfcTransport, NfcProfile
from dgm_rf.cmw_lte import LteRmcConfig
from .catalog import describe
from .session import DeviceSession, open_device
from .phone_logging import PhoneTraffic
from .errors import error_details
from .hardware_run import utc
from .radio_contracts import RADIOS, at_steps, simulation_phone_profile
from .radio_simulation import RadioAtPeer, RadioLtePeer, RadioNfcPeer
from .virtual_peers import ScpiPeer


def checkpoint(token):
    if token.is_set(): raise InterruptedError("Radio measurement cancelled")


def pause(seconds, token=None):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if token is not None: checkpoint(token)
        time.sleep(min(.02, max(0, deadline-time.monotonic())))


class LoggedNfc:
    def __init__(self, transport, log):
        self.transport, self.log = transport, log
        self.simulated = transport.simulated

    def dispatch(self, request, timeout):
        event = {"device_id": "NfcPrbs", "exchange_id": str(uuid.uuid4()), "request": asdict(request),
                 "nci_payload_only": request.nci_payload.hex(), "simulated": self.simulated}
        self.log({**event, "utc": utc(), "phase": "attempted"})
        try:
            answer = self.transport.dispatch(request, timeout)
        except BaseException as error:
            self.log({**event, "utc": utc(), "phase": "failed", "error": error_details(error)})
            raise
        self.log({**event, "utc": utc(), "phase": "dispatched_unconfirmed", "raw_response": answer})
        return answer


class RadioLab:
    def __init__(self, plan, profiles, evidence, world=None):
        self.plan, self.profiles, self.evidence, self.world = plan, profiles, evidence, world
        self.simulated = world is not None
        self.sessions, self.nfc = {}, None
        self.connection_attempted = False
        self.cellular_events = []

    def log(self, name, record):
        row = {**record, "device_id": name}
        self.evidence.traffic(row)
        if name == "CmwLte": self.cellular_events.append(deepcopy(row))

    @contextmanager
    def open(self, name):
        self.connection_attempted = True
        logger = lambda row: self.log(name, row)
        if not self.simulated:
            with open_device(self.profiles[name], log=logger) as session:
                self.sessions[name] = session
                yield session
            return
        if name == "PhoneAt":
            io = PhoneTraffic(RadioAtPeer(self.world), logger)
            driver = Controller(io, simulation_phone_profile(self.plan))
        elif name == "SpectrumAnalyzer":
            io = ScpiPeer(name, self.world, logger)
            driver = SpectrumAnalyzer(io, model="N9030B", max_frequency_hz=50e9)
        else:
            io = RadioLtePeer(self.world, logger)
            driver = CmwLte(io, site_profile_confirmed=True)
        session = None
        try:
            if name != "PhoneAt": driver.identify()
            session = DeviceSession(describe(name), driver, simulated=True)
            self.sessions[name] = session
            yield session
        finally:
            if session is not None: session.closed = True
            io.close()

    def acquire(self, analyzer, phase):
        trace = analyzer.call("acquire", config=Sweep(**self.plan["sweep"]))
        row = {"phase": phase, "trace": asdict(trace), "peak_dbm": max(trace.values_dbm),
               "simulated": self.simulated}
        if self.world is not None: row["source_state"] = self.world.snapshot()
        self.evidence.write("observations.jsonl", row)
        # Persistence failure still allows cleanup reads; the runner fails on recorder errors.
        return row

    def nfc_verify(self, analyzer, started, budget, token):
        v = self.plan["verification"]
        began = time.monotonic()
        deadline = began + budget
        bound = .01 if self.simulated else self.profiles["NfcPrbs"]["config"]["transition_bound_seconds"]
        quiet_since = None
        while time.monotonic() < deadline:
            if started: checkpoint(token)
            level = self.acquire(analyzer, "nfc-start-verification" if started else "nfc-stop-verification")["peak_dbm"]
            now = time.monotonic()
            if now > deadline: return False
            if started and level >= v["on_threshold_dbm"]: return True
            if not started:
                if now - began >= bound and level <= v["off_threshold_dbm"]:
                    quiet_since = now if quiet_since is None else quiet_since
                    if now - quiet_since >= v["quiet_seconds"]: return True
                else: quiet_since = None
            pause(v["poll_seconds"], token if started else None)
        return False

    @contextmanager
    def active_source(self, analyzer, token):
        radio = self.plan["radio"]
        checkpoint(token)
        if radio == "nfc":
            if self.simulated:
                transport = RadioNfcPeer(self.world)
            else:
                c = self.profiles["NfcPrbs"]["config"]
                transport = AdbNfcTransport(c["serial"], NfcProfile(c["model"], c["build"], c["apk_sha256"], c["sender_permission_verified"]))
            self.nfc = NfcPrbsController(LoggedNfc(transport, lambda row: self.log("NfcPrbs", row)))
            self.connection_attempted = True
            with self.nfc.session(**self.plan["tx"], timeout=self.plan["state_timeout"], cancelled=token,
                    verify_started=lambda budget: self.nfc_verify(analyzer, True, budget, token),
                    verify_stopped=lambda budget: self.nfc_verify(analyzer, False, budget, token)):
                yield
        else:
            source = RADIOS[radio]["source_device"]
            with self.open(source) as device:
                if radio == "cellular":
                    try:
                        device.call("configure", config=LteRmcConfig(**self.plan["tx"]))
                    except BaseException as error:
                        try: device.call("stop")
                        except BaseException as stop_error:
                            raise BaseExceptionGroup("LTE configuration and stop failed", [error, stop_error]) from None
                        raise
                    with device.active(timeout=self.plan["state_timeout"], cancelled=token): yield
                else:
                    setup, cleanup = at_steps(self.plan)
                    with device.active(setup=setup, cleanup=cleanup, cancelled=token): yield

    def phone_log(self):
        radio = self.plan["radio"]
        if radio == "nfc":
            return {"scope": "protected_service_dispatch_and_rf_envelope_checks", "session_opened": self.nfc is not None,
                    "events": deepcopy(self.nfc.log) if self.nfc else []}
        if radio == "cellular":
            return {"scope": "callbox_mediated_not_modem_diagnostic", "session_opened": "CmwLte" in self.sessions,
                    "events": deepcopy(self.cellular_events)}
        return {"scope": "native_at_controller", "session_opened": "PhoneAt" in self.sessions,
                "events": self.sessions["PhoneAt"].phone_log if "PhoneAt" in self.sessions else []}

    def identities(self):
        identities = {name: device.info for name, device in self.sessions.items()}
        if self.nfc is not None:
            c = self.profiles["NfcPrbs"]["config"] if not self.simulated else {"model": "SIMULATION", "build": "fixture"}
            identities["NfcPrbs"] = {"model": c["model"], "build": c["build"], "simulated": self.simulated,
                                     "identity_source": "profile_declared_not_readback", "physical_verified": False}
        return identities
