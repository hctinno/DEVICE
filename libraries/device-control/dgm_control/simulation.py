"""Bounded CO3000 protocol peer. Never opens a socket or serial port."""
from dgm_lab.transport import Transport
from dgm_lab.core import InstrumentError


class MotionPeer(Transport):
    def __init__(self, *, log=None, fail_command=None):
        super().__init__("simulation://co3000-no-hardware", log=log)
        self.selected = 0
        self.positions = [100.0, 0.0]
        self.target = 0.0
        self.polarization = "PH"
        self.moving = False
        self.events = []
        self.command = None
        self.fail_command = fail_command

    def _write(self, command):
        self.command = command
        self.events.append(command)

    def _read(self):
        command = self.command
        if command == self.fail_command:
            return "E - V"
        if command == "*IDN?":
            return "inncoCO3000/SIMULATION/v1.02.60"
        if command == "*OPT?":
            return "MA1,DT1," + ",".join(["0"] * 14)
        if command.startswith("STATUS "):
            axis = command.split()[1]
            if axis not in {"MA1", "DT1"}:
                raise InstrumentError("Unmodeled axis")
            index = 0 if axis == "MA1" else 1
            unit = "CM" if index == 0 else "DG"
            suffix = "," + self.polarization if index == 0 else ""
            return f"{axis},{int(self.moving)},{self.positions[index]} {unit}{suffix}"
        if command.startswith("LD ") and command.endswith(" DV"):
            self.selected = int(command.split()[1])
            if self.selected not in (0, 1):
                raise InstrumentError("Unmodeled device slot")
            return str(self.selected)
        if command in {"LL", "UL", "CL", "WL"}:
            return {"LL": "100", "UL": "400", "CL": "0", "WL": "360"}[command]
        if command.startswith("LD ") and command.endswith(" NP"):
            self.target = float(command.split()[1])
            return "1"
        if command == "GO":
            self.positions[self.selected] = self.target
            return "1"  # instantaneous fixture; production wait still verifies stable readback
        if command in {"PH", "PV"}:
            self.polarization = command
            return "1"
        if command == "ES":
            self.moving = False
            return "1"
        raise InstrumentError(f"Unmodeled simulation command: {command}")

    def _close(self):
        pass  # Closing does not pretend to stop motion.
