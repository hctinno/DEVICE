"""Strict in-memory peers for named driver dialects; no hardware transport imports."""
import re

from dgm_lab.core import InstrumentError
from dgm_lab.demo import DemoPowerSupply
from dgm_lab.transport import Transport
from dgm_rf.core import ScriptedTransport, RFError
from .simulation import MotionPeer


class SupplyPeer(DemoPowerSupply):
    def __init__(self, world, log):
        super().__init__(log=log)
        self.world = world
        for key, value in world.supply.items():
            setattr(self, key, value)

    def _write(self, command):
        with self.world.lock:
            fault = self.world.fault("OdaEx", command)
            if fault == "reject":
                raise InstrumentError("Injected power supply rejection")
            super()._write(command)
            if fault == "malformed":
                self.reply = "malformed"
            self.world.supply.update(output=self.output, voltage=self.voltage, current=self.current)
            if "?" not in command:
                self.world.changed()


class PositionerPeer(MotionPeer):
    def __init__(self, world, log):
        super().__init__(log=log)
        self.world = world
        self.positions = list(world.motion["positions"])
        self.polarization = world.motion["polarization"]
        self.moving = world.motion["moving"]
        self.speed_level = 1

    def _read(self):
        with self.world.lock:
            fault = self.world.fault("Co3000", self.command)
            if fault == "reject":
                return "E - V"
            if fault == "malformed":
                return "malformed"
            if fault == "stuck":
                self.moving = True
                answer = "1"
            elif self.command.startswith("LD ") and self.command.endswith(" SP"):
                self.speed_level = int(self.command.split()[1])
                answer = str(self.speed_level)
            elif self.command == "SP":
                answer = str(self.speed_level)
            else:
                answer = super()._read()
            self.world.motion.update(positions=list(self.positions), polarization=self.polarization, moving=self.moving)
            if self.command in {"GO", "ES", "PH", "PV"}:
                self.world.changed()
            return answer


class PhonePeer(ScriptedTransport):
    FIELDS = {"0,0,6": "band", "0,0,0": "channel", "0,7,0": "antenna", "0,0,1": "rate",
              "0,0,2": "gi", "0,0,5": "burst", "0,0,4": "payload", "0,0,7": "bandwidth",
              "0,1,5": "encoding", "0,0,3": "power"}

    def __init__(self, world, log):
        super().__init__()
        self.world, self.log = world, log

    def _record(self, direction, payload):
        if self.log:
            self.log({"resource": "simulation://SamsungAt", "direction": direction, "payload": payload,
                      "revision": self.world.revision, "simulated": True})

    def exchange(self, wire, timeout):
        with self.world.lock:
            if self.closed or self.desynchronized:
                raise RFError("Virtual phone transport unavailable")
            self.sent.append(wire)
            self._record("tx", wire)
            try:
                fault = self.world.fault("SamsungAt", wire)
            except Exception:
                self.desynchronized = True
                raise
            if fault in {"reject", "malformed"}:
                response = "ERROR" if fault == "reject" else "OK"
            else:
                response = self._apply(wire)
            self._record("rx", response)
            return response

    def _apply(self, wire):
        match = re.fullmatch(r"AT\+WIFITEST=(\d,\d,\d),([^,]+)", wire)
        if not match:
            return "ERROR"
        key, value = match.groups()
        phone = self.world.phone
        if key == "0,1,1" and value == "0":
            if phone["tx"]:
                return "ERROR"
            phone.update(test_mode=True, settings={})
        elif key == "0,2,0" and value == "0":
            phone["tx"] = False
        elif key == "0,1,0" and value == "0":
            phone.update(test_mode=False, tx=False)
        elif key in self.FIELDS and phone["test_mode"] and not phone["tx"]:
            phone["settings"][self.FIELDS[key]] = value
        elif key == "0,2,1" and value == "1":
            settings = phone["settings"]
            if (not phone["test_mode"] or set(settings) != set(self.FIELDS.values())
                    or settings["band"] != "3" or settings["bandwidth"] not in {"6", "7", "8", "9"}
                    or settings["channel"] not in self.world.scenario.channels_hz
                    or not self.world.supply["output"] or self.world.supply["voltage"] < 3
                    or self.world.supply["current"] < 0.1):
                return "ERROR"
            phone["tx"] = True
        else:
            return "ERROR"
        self.world.changed()
        return "+WIFITEST:0,OK\r\nOK"

    def emergency_write(self, wire):
        # Deliberately no delivery/side effect guarantee after a poisoned transport.
        super().emergency_write(wire)
        self._record("emergency_tx_unconfirmed", wire)


class ScpiPeer(Transport):
    IDENTITIES = {"SpectrumAnalyzer": "Keysight Technologies,N9030B,SIMULATION,0",
                  "SignalGenerator": "Rohde&Schwarz,SMW200A,SIMULATION,0",
                  "UsbPowerSensor": "Rohde&Schwarz,NRP18S,SIMULATION,0",
                  "OspSwitch": "Rohde&Schwarz,OSP120,SIMULATION,0"}
    ANALYZER_CONSTANTS = {"ABOR", "INST:SEL SA", "CONF:SAN", "INIT:CONT OFF", "FORM:DATA ASC",
        "UNIT:POW DBM", "BAND:RES:AUTO OFF", "BAND:VID:AUTO OFF", "POW:ATT:AUTO OFF",
        "SWE:TIME:AUTO OFF", "TRAC1:TYPE WRIT", "TRAC1:UPD ON", "TRAC1:DISP ON",
        "TRIG:SOUR IMM", "DISP:WIND:TRAC:X:SPAC LIN", "AVER:TYPE RMS"}
    ANALYZER_NUMBERS = {"FREQ:STAR", "FREQ:STOP", "BAND:RES", "BAND:VID", "POW:ATT",
                        "DISP:WIND:TRAC:Y:RLEV", "SWE:POIN", "SWE:TIME"}
    ROUTES = {"(@F01A11(0101))": "isolated", "(@F01A11(0201))": "dut", "(@F01A11(0301))": "generator"}

    def __init__(self, device_id, world, log):
        super().__init__(f"simulation://{device_id}", log=log)
        self.device_id, self.world = device_id, world
        self.settings = world.instrument_settings.setdefault(device_id, {})
        self.reply = None
        self.trace = None

    def _write(self, command):
        with self.world.lock:
            fault = self.world.fault(self.device_id, command)
            if fault == "reject":
                raise InstrumentError("Injected command rejection")
            self.reply = None
            if fault == "malformed":
                self.reply = "malformed"
                return
            if command == "*IDN?":
                self.reply = self.IDENTITIES[self.device_id]
            elif command == "*OPC?":
                self.reply = "1"
            elif command == "SYST:ERR?":
                self.reply = '0,"No error"'
            elif self.device_id == "SpectrumAnalyzer":
                self._analyzer(command)
            elif self.device_id == "SignalGenerator":
                self._generator(command)
            elif self.device_id == "UsbPowerSensor":
                self._sensor(command)
            elif self.device_id == "OspSwitch":
                self._switch(command)
            else:
                raise InstrumentError(f"Unmodeled command {command}")

    def _numeric(self, command, allowed):
        if command.endswith("?") and command[:-1] in allowed:
            if command[:-1] not in self.settings:
                raise InstrumentError("Query before configuration")
            self.reply = str(self.settings[command[:-1]])
            return True
        key, separator, value = command.partition(" ")
        if separator and key in allowed:
            self.settings[key] = float(value)
            self.trace = None
            return True
        return False

    def _analyzer(self, command):
        if command in self.ANALYZER_CONSTANTS:
            if command == "ABOR":
                self.trace = None
            return
        if command in {"DET POS", "DET NEG", "DET SAMP", "DET AVER"}:
            self.settings["detector"] = command[4:]
            return
        if self._numeric(command, self.ANALYZER_NUMBERS):
            return
        if command == "UNIT:POW?":
            self.reply = "DBM"
        elif command == "INIT:IMM":
            s = self.settings
            count = int(s["SWE:POIN"])
            frequencies = [s["FREQ:STAR"] + i * (s["FREQ:STOP"] - s["FREQ:STAR"]) / (count - 1) for i in range(count)]
            values = [self.world.power(frequency, s["BAND:RES"]) for frequency in frequencies]
            self.trace = ",".join(format(value, ".12g") for value in values)
            self.world.observation(self.device_id, s, {"frequencies_hz": frequencies, "dbm": values})
        elif command == "TRAC:DATA? TRACE1" and self.trace is not None:
            self.reply = self.trace
        else:
            raise InstrumentError(f"Unmodeled analyzer command {command}")

    def _generator(self, command):
        state = self.world.generator
        if command in {"SOUR:MOD:ALL:STAT OFF", "SOUR:FREQ:MODE CW", "SOUR:POW:MODE FIX"}:
            return
        if command in {"OUTP ON", "OUTP OFF"}:
            state["output"] = command == "OUTP ON"
        elif command == "OUTP?":
            self.reply = str(int(state["output"]))
            return
        elif command == "SOUR:FREQ:CW?":
            self.reply = str(state["frequency_hz"])
            return
        elif command == "SOUR:POW?":
            self.reply = str(state["power_dbm"])
            return
        elif command.startswith("SOUR:FREQ:CW "):
            state["frequency_hz"] = float(command.split()[1])
        elif command.startswith("SOUR:POW ") and command.endswith("DBM"):
            state["power_dbm"] = float(command.split()[1][:-3])
        else:
            raise InstrumentError(f"Unmodeled source command {command}")
        self.world.changed()

    def _sensor(self, command):
        if command in {"ABOR", "INIT:CONT OFF", 'SENS:FUNC "POW:AVG"', 'CALC:FEED "POW:AVER"',
                       "UNIT:POW W", "FORM:DATA ASC", "BUFF:STAT OFF", "TRIG:COUN 1", "TRIG:SOUR IMM"}:
            return
        if self._numeric(command, {"SENS:FREQ"}):
            return
        if command == "UNIT:POW?":
            self.reply = "W"
        elif command == "INIT":
            value = self.world.power()  # broadband sensor; correction frequency is not a tuner
            self.trace = str(10 ** ((value - 30) / 10))
            self.world.observation(self.device_id, self.settings, {"dbm": value, "watts": float(self.trace)})
        elif command == "FETC?" and self.trace is not None:
            self.reply = self.trace
        else:
            raise InstrumentError(f"Unmodeled sensor command {command}")

    def _switch(self, command):
        if command == "ROUT:MOD:CAT?":
            self.reply = '"OSP-B102-F01A11"'
            return
        query = command.startswith("ROUT:CLOS? ")
        if query or command.startswith("ROUT:CLOS "):
            route = self.ROUTES.get(command.split(" ", 1)[1])
            if route is not None:
                if query:
                    self.reply = str(int(self.world.route == route))
                else:
                    self.world.route = route
                    self.world.changed()
                return
        raise InstrumentError(f"Unmodeled switch command {command}")

    def _read(self):
        if self.reply is None:
            raise InstrumentError("No modeled query response")
        return self.reply

    def _close(self):
        pass  # Transport close does not modify output or route state.
