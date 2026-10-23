"""Deterministic synthetic RF bench; never opens device or network connections.

N1914A command semantics are a deliberately small, documented subset. Timing,
RF values, device identity, wire formatting and stale-data rejection are virtual
policies, not measured manufacturer behavior. See docs/fcc/virtual_lab_usage.md.
"""
from collections import deque
import math
import random
import re


def _number(value, minimum, maximum, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number')
    if not minimum <= value <= maximum or not math.isfinite(value):
        raise ValueError(f'{name} must be in [{minimum}, {maximum}]')
    return float(value)


def _integer(value, minimum, maximum, name):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer in [{minimum}, {maximum}]')
    return value


class VirtualLab:
    """One generic synthetic DUT, one RF path and one A-channel meter profile."""

    profile_id = 'n1914a-a-ascii-v1'

    def __init__(self, seed=0, measurement_ticks=2, noise_db=0.0):
        self._rng = random.Random(_integer(seed, 0, 2**32 - 1, 'seed'))
        self._latency = _integer(measurement_ticks, 1, 1000, 'measurement_ticks')
        self._noise = _number(noise_db, 0, 10, 'noise_db')
        self._tick = 0
        self._revision = 0
        self._configuration = None
        self._transmit_requested = False
        self._path = (False, 0.0)
        self._faults = {'tx_ignored': False, 'meter_disconnected': False,
                        'measurement_stuck': False, 'thermal_drop_db': 0.0}
        self._sequence = 0
        self._errors = deque()
        self._reset_meter()

    def _reset_meter(self):
        self._state = 'idle'
        self._remaining = 0
        self._acquisition_revision = None
        self._last = None
        self._unit = 'DBM'
        self._trigger = 'IMM'

    def _ack(self):
        return {'accepted': True, 'synthetic': True, 'hardware_verified': False}

    def configure_dut(self, mode, channel, power_dbm):
        if mode not in ('b', 'g', 'n'):
            raise ValueError('Synthetic DUT supports b, g and n only')
        channel = _integer(channel, 1, 11, 'channel')
        power = _number(power_dbm, -30, 30, 'power_dbm')
        configuration = (mode, channel, power)
        if configuration != self._configuration:
            self._configuration = configuration
            self._revision += 1
        return self._ack()

    def set_path(self, connected, loss_db):
        if type(connected) is not bool:
            raise ValueError('connected must be boolean')
        path = (connected, _number(loss_db, 0, 120, 'loss_db'))
        if path != self._path:
            self._path = path
            self._revision += 1
        return self._ack()

    def start_tx(self):
        if self._configuration is None:
            raise ValueError('Configure the synthetic DUT before starting TX')
        if not self._transmit_requested:
            self._transmit_requested = True
            self._revision += 1
        # A successful control response does not establish that RF is present.
        return self._ack()

    def stop_tx(self):
        if self._transmit_requested:
            self._transmit_requested = False
            self._revision += 1
        return self._ack()

    def inject_fault(self, name, value):
        """Scenario-author interface; not an operator/AI observation API."""
        if name not in self._faults:
            raise ValueError('Unknown virtual fault')
        if name == 'thermal_drop_db':
            value = _number(value, 0, 60, name)
        elif type(value) is not bool:
            raise ValueError('Fault switch must be boolean')
        if self._faults[name] != value:
            self._faults[name] = value
            if name in ('tx_ignored', 'thermal_drop_db'):
                self._revision += 1

    def _reply(self, status='ok', response=None, **extra):
        return {'status': status, 'response': response, 'synthetic': True,
                'hardware_verified': False, 'profile_id': self.profile_id,
                'response_basis': 'documented_semantics_with_synthetic_response',
                'tick': self._tick, **extra}

    def _error(self, code, message):
        if len(self._errors) < 30:
            self._errors.append((code, message))
        else:
            self._errors[-1] = (-350, 'Queue overflow')
        return self._reply('error', error_number=code, error_message=message)

    def _start_acquisition(self):
        self._state = 'acquiring'
        self._remaining = self._latency
        self._acquisition_revision = self._revision

    def advance(self, ticks):
        """Advance synthetic time, not wall-clock time or device time."""
        ticks = _integer(ticks, 0, 10000, 'ticks')
        for _ in range(ticks):
            self._tick += 1
            if self._state != 'acquiring' or self._faults['measurement_stuck']:
                continue
            self._remaining -= 1
            if self._remaining:
                continue
            self._sequence += 1
            dbm = None
            if self._revision == self._acquisition_revision:
                if self._transmit_requested and not self._faults['tx_ignored'] and self._path[0]:
                    dbm = self._configuration[2] - self._path[1] - self._faults['thermal_drop_db']
                    dbm = max(dbm, -100.0)
                else:
                    dbm = -100.0
                dbm += self._rng.uniform(-self._noise, self._noise)
            self._last = {'dbm': dbm, 'measurement_id': self._sequence,
                          'setup_revision': self._acquisition_revision, 'completed_tick': self._tick}
            self._state = 'idle'
        return self._reply()

    def _fetch(self):
        if self._state != 'idle':
            return self._reply('pending')
        if self._last is None:
            return self._reply('no_data')
        if self._last['dbm'] is None or self._last['setup_revision'] != self._revision:
            return self._reply('invalid', reason='configuration_changed')
        value = self._last['dbm']
        if self._unit == 'W':
            value = 10 ** ((value - 30) / 10)
        measurement = {key: value for key, value in self._last.items() if key != 'dbm'}
        measurement.update(value=value, unit=self._unit, synthetic=True)
        return self._reply(response=f'{value:+.9E}', measurement=measurement)

    def meter(self, command):
        """Execute one text command in the virtual subset; no real I/O fallback.

        Pending/invalid/unsupported are application envelopes, not invented SCPI
        wire replies. Only an `ok` reply may contain a response string.
        """
        if not isinstance(command, str) or not command.strip() or len(command) > 256:
            return self._reply('unsupported', reason='invalid_command')
        command = command.strip().upper()
        if not command.isascii() or any(char in command for char in ';\r\n'):
            return self._reply('unsupported', reason='single_ascii_command_required')
        if self._faults['meter_disconnected']:
            return self._reply('disconnected')
        parts = re.split(r'\s+', command.lstrip(':'), maxsplit=1)
        head, arg = parts[0], parts[1] if len(parts) == 2 else None
        if arg is None:
            if head == '*IDN?':
                return self._reply(response='DGM Virtual,N1914A,SIM-001,SIM-1')
            if head == '*RST':
                self._reset_meter()  # Error queue intentionally survives reset.
                return self._reply()
            if head == '*CLS':
                self._errors.clear()
                return self._reply()
            if head == '*OPC?':
                return self._reply(response='1') if self._state == 'idle' else self._reply('pending')
            if re.fullmatch(r'SYST(?:EM)?:ERR(?:OR)?\?', head):
                code, message = self._errors.popleft() if self._errors else (0, 'No error')
                return self._reply(response=f'{code:+d},"{message}"', error_number=code)
            if re.fullmatch(r'INIT(?:IATE)?1?(?::IMM(?:EDIATE)?)?', head):
                if self._state != 'idle':
                    return self._error(-213, 'INIT ignored')
                self._state = 'armed'
                if self._trigger == 'IMM':
                    self._start_acquisition()
                return self._reply()
            if head == '*TRG':
                if self._state != 'armed' or self._trigger != 'BUS':
                    return self._error(-211, 'Trigger ignored')
                self._start_acquisition()
                return self._reply()
            if re.fullmatch(r'ABOR(?:T)?1?', head):
                self._state, self._last, self._remaining = 'idle', None, 0
                return self._reply()
            if re.fullmatch(r'FETC(?:H)?1?(?::SCAL(?:AR)?)?(?::POW(?:ER)?:AC)?\?', head):
                return self._fetch()
        for pattern, allowed, current, attribute in [
            (r'UNIT1?:POW(?:ER)?', {'DBM': 'DBM', 'W': 'W'}, self._unit, '_unit'),
            (r'TRIG(?:GER)?(?::SEQ(?:UENCE)?)?1?:SOUR(?:CE)?',
             {'IMM': 'IMM', 'IMMEDIATE': 'IMM', 'BUS': 'BUS', 'HOLD': 'HOLD'}, self._trigger, '_trigger'),
            (r'INIT(?:IATE)?1?:CONT(?:INUOUS)?', {'0': '0', 'OFF': '0'}, '0', None),
            (r'FORM(?:AT)?(?::READ(?:INGS)?)?(?::DATA)?', {'ASC': 'ASCII', 'ASCII': 'ASCII'}, 'ASCII', None),
        ]:
            if arg is None and re.fullmatch(pattern + r'\?', head):
                return self._reply(response=current)
            if arg is not None and re.fullmatch(pattern, head) and arg in allowed:
                if attribute == '_trigger' and self._state != 'idle':
                    return self._reply('busy', reason='abort_before_trigger_change')
                if attribute:
                    setattr(self, attribute, allowed[arg])
                return self._reply()
        return self._reply('unsupported', reason='outside_virtual_profile')
