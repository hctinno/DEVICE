"""Observe AT transport without changing the source controller or wire dialect."""
from datetime import datetime, timezone
import uuid

from .errors import error_details


class PhoneTraffic:
    def __init__(self, transport, log):
        self.transport, self.log = transport, log

    @property
    def simulated(self):
        return self.transport.simulated

    @property
    def desynchronized(self):
        return self.transport.desynchronized

    @desynchronized.setter
    def desynchronized(self, value):
        self.transport.desynchronized = value

    def _invoke(self, operation, wire, *arguments):
        event = {"device_id": "PhoneAt", "operation": operation, "command": wire,
                 "exchange_id": str(uuid.uuid4()), "simulated": self.simulated,
                 "rf_measured": False}
        def emit(phase, **fields):
            self.log({**event, "utc": datetime.now(timezone.utc).isoformat(), "phase": phase, **fields})
        emit("attempted")  # durable intent before transmitting
        try:
            answer = getattr(self.transport, operation)(wire, *arguments)
        except BaseException as error:
            emit("failed", error=error_details(error))
            raise
        emit("response_received" if operation == "exchange" else "sent_unconfirmed",
             raw_response=answer)
        return answer

    def exchange(self, wire, timeout):
        return self._invoke("exchange", wire, timeout)

    def emergency_write(self, wire):
        return self._invoke("emergency_write", wire)

    def close(self):
        self.transport.close()
