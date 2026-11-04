"""Validation and source-scoped SCPI sessions. No implicit reset or output enable."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re


class InstrumentError(RuntimeError):
    pass


class UnsupportedInstrument(InstrumentError):
    pass


def number(value, name, low=-1e30, high=1e30):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name}: expected finite number in [{low}, {high}], got {value!r}')
    return float(value)


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name}: expected integer in [{low}, {high}]')
    return value


def fmt(value):
    return format(value, '.12g')


def scalar(answer):
    try:
        value = float(answer)
    except (TypeError, ValueError) as exc:
        raise InstrumentError(f'Invalid numeric response: {answer!r}') from exc
    if not math.isfinite(value) or abs(value) >= 9e36:
        raise InstrumentError(f'Invalid/overrange numeric response: {answer!r}')
    return value


def switch(answer):
    value = answer.strip().upper()
    if value in ('1', 'ON'):
        return True
    if value in ('0', 'OFF'):
        return False
    raise InstrumentError(f'Invalid switch response: {answer!r}')


def close_enough(actual, requested, *, abs_tol=1e-6):
    if not math.isclose(actual, requested, rel_tol=1e-8, abs_tol=abs_tol):
        raise InstrumentError(f'Readback mismatch: requested {requested}, returned {actual}')


def normalized(value):
    return re.sub(r'[^A-Z0-9]', '', value.upper())


@dataclass(frozen=True)
class Identity:
    manufacturer: str
    model: str
    serial: str
    firmware: str
    raw: str


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str
    utc: str
    identity: Identity
    raw: str


class Scpi:
    def __init__(self, transport, *, model, manufacturers):
        self.io = transport
        self.expected_model = model
        self.manufacturers = tuple(manufacturers)
        self.identity = None

    def identify(self):
        self.identity = None
        if hasattr(self, 'configured'):
            self.configured = False
        if hasattr(self, 'configured_channel'):
            self.configured_channel = None
        if hasattr(self, 'plan'):
            self.plan = None
        answer = self.io.query('*IDN?')
        parts = answer.split(',', 3)
        if len(parts) != 4:
            raise UnsupportedInstrument(f'Malformed *IDN?: {answer!r}')
        manufacturer, model, serial, firmware = (p.strip() for p in parts)
        if normalized(manufacturer) not in {normalized(m) for m in self.manufacturers} or normalized(model) != normalized(self.expected_model):
            raise UnsupportedInstrument(f'Expected {self.manufacturers}/{self.expected_model}; got {answer}')
        self.identity = Identity(manufacturer, model, serial, firmware, answer)
        return self.identity

    def ready(self):
        if self.identity is None:
            raise UnsupportedInstrument('Call identify() and verify exact manufacturer/model before control')

    def errors(self, limit=16):
        integer(limit, 'error queue limit', 1, 256)
        errors = []
        with self.io.transaction():
            for _ in range(limit):
                answer = self.io.query('SYST:ERR?')
                try:
                    code = int(answer.split(',', 1)[0].strip())
                except ValueError as exc:
                    raise InstrumentError(f'Malformed error queue: {answer!r}') from exc
                if code == 0:
                    if errors:
                        raise InstrumentError('Instrument error queue: ' + ' | '.join(errors))
                    return
                errors.append(answer)
        raise InstrumentError('Error queue did not clear: ' + ' | '.join(errors))

    def opc(self):
        if self.io.query('*OPC?') not in ('1', '+1'):
            raise InstrumentError('Unexpected operation-complete response')

    def apply(self, commands):
        self.ready()
        with self.io.transaction():
            self.errors()  # preserve and reject pre-existing errors; never *CLS them away
            for command in commands:
                self.io.write(command)
            self.opc()
            self.errors()

    def measure(self, query, unit):
        self.ready()
        with self.io.transaction():
            self.errors()
            raw = self.io.query(query)
            value = scalar(raw)
            self.errors()
            return Measurement(value, unit, datetime.now(timezone.utc).isoformat(), self.identity, raw)


@contextmanager
def managed_run(start, stop):
    """Attempt stop even if start partially failed; preserve BOTH errors, including Ctrl-C."""
    primary = None
    try:
        start()
        yield
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            stop()
        except BaseException as cleanup:
            if primary is not None:
                raise BaseExceptionGroup('Operation and cleanup both failed; output state UNKNOWN', [primary, cleanup]) from None
            raise
