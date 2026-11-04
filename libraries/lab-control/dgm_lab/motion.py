"""Innco CO3000 remote protocol v2.10, manufacturer manual PDF pp.41-54.

MA/MM and DT/DE/DS/CT/MR axes only. Every command has a reply, including ES.
Site limits are intersected with controller limits; no limit/reference writes.
"""
from dataclasses import dataclass
import re
import time
from .core import Identity, InstrumentError, UnsupportedInstrument, number, integer, scalar, managed_run


@dataclass(frozen=True)
class Position:
    axis: str
    busy: bool
    value: float
    unit: str
    polarization: str | None
    raw: str


class Co3000:
    source_id = 'innco-co3000'

    def __init__(self, transport, *, axes, motion_enabled=False, poll_seconds=0.2):
        self.io = transport
        self.identity = None
        self.devices = {}
        self.axes = {}
        if not isinstance(axes, dict) or not axes:
            raise ValueError('Explicit axis names and site limits required')
        for name, limits in axes.items():
            if not re.fullmatch(r'(?:MA|MM|DT|DE|DS|CT|MR)[1-9][0-9]*', name):
                raise ValueError(f'Unsupported axis {name!r}')
            unit = 'CM' if name.startswith(('MA', 'MM')) else 'DG'
            if limits.get('unit') != unit:
                raise ValueError(f'{name} requires {unit}')
            low = number(limits['min'], 'site minimum', 0, 100000)
            high = number(limits['max'], 'site maximum', low, 100000)
            if high <= low:
                raise ValueError('Site maximum must exceed minimum')
            self.axes[name] = dict(unit=unit, min=low, max=high)
        if type(motion_enabled) is not bool:
            raise ValueError('motion_enabled must be bool')
        self.motion_enabled = motion_enabled
        self.poll_seconds = number(poll_seconds, 'poll_seconds', 0.01, 10)

    def _query(self, command):
        if len(command.encode('ascii')) + 1 > 64:
            raise ValueError('CO3000 command exceeds 64 bytes with LF')
        reply = self.io.query(command).strip()
        if re.fullmatch(r'E\s*-\s*[PSVD]', reply):
            raise InstrumentError(f'CO3000 {command!r}: {reply}')
        return reply

    def _ack(self, command, expected='1'):
        reply = self._query(command)
        if reply != expected:
            raise InstrumentError(f'CO3000 {command!r}: expected {expected!r}, got {reply!r}')

    def identify(self):
        self.identity = None
        self.devices = {}
        raw = self._query('*IDN?')
        match = re.fullmatch(r'inncoCO3000/(.+)/v?(\d+)\.(\d+)\.(\d+)', raw)
        if not match or tuple(map(int, match.groups()[1:])) < (1, 2, 60):
            raise UnsupportedInstrument(f'Expected CO3000 firmware >=1.02.60: {raw!r}')
        options = self._query('*OPT?').split(',')
        if len(options) != 16:
            raise InstrumentError('Expected 16 CO3000 option slots')
        names = [x.strip() for x in options if x.strip() != '0']
        if len(names) != len(set(names)):
            raise InstrumentError('Duplicate CO3000 axis names')
        self.devices = {name.strip(): i for i, name in enumerate(options) if name.strip() != '0'}
        if not self.axes.keys() <= self.devices.keys():
            raise UnsupportedInstrument(f'Configured axes absent from *OPT?: {self.devices}')
        self.identity = Identity('innco systems', 'CO3000', match[1], '.'.join(match.groups()[1:]), raw)
        return self.identity

    def _ready(self, axis=None, movement=False):
        if self.identity is None:
            raise UnsupportedInstrument('Call identify() before control')
        if axis is not None and axis not in self.axes:
            raise ValueError(f'Axis outside site profile: {axis!r}')
        if movement and not self.motion_enabled:
            raise InstrumentError('Site profile has motion_enabled=false')

    def _select(self, axis):
        self._ready(axis)
        # Numeric selection has unambiguous ACK in both general and device tables.
        index = self.devices[axis]
        self._ack(f'LD {index} DV', str(index))

    def position(self, axis):
        self._ready(axis)
        raw = self._query(f'STATUS {axis} ?')
        match = re.fullmatch(r'([A-Z]+\d+)\s*,\s*([01])\s*,\s*([+-]?\d+(?:\.\d+)?)\s+(CM|DG)(?:\s*,\s*(PV|PH|P-))?', raw)
        if not match or match[1] != axis or match[4] != self.axes[axis]['unit']:
            raise InstrumentError(f'Invalid axis status: {raw!r}')
        return Position(axis, match[2] == '1', scalar(match[3]), match[4], match[5], raw)

    def limits(self, axis):
        with self.io.transaction():
            self._select(axis)
            low, high = ('LL', 'UL') if self.axes[axis]['unit'] == 'CM' else ('CL', 'WL')
            values = scalar(self._query(low)), scalar(self._query(high))
            if values[0] >= values[1]:
                raise InstrumentError(f'Invalid controller limits: {values}')
            return values

    def _target(self, axis, value):
        self._ready(axis, movement=True)
        limits = self.axes[axis]
        value = number(value, 'target', limits['min'], limits['max'])
        if abs(value * 10 - round(value * 10)) > 1e-7:
            raise ValueError('CO3000 target precision is at most one decimal place')
        return value

    def start(self, axis, value):
        value = self._target(axis, value)
        with self.io.transaction():
            low, high = self.limits(axis)
            if not low <= value <= high:
                raise ValueError(f'Target outside controller limits [{low}, {high}]')
            if self.position(axis).busy:
                raise InstrumentError('Axis already moving')
            self._ack(f'LD {value:.1f} {self.axes[axis]["unit"]} NP')
            self._ack('GO')

    def stop_all(self):
        """ES stops ALL attached devices, including axes outside this profile.

        ACK is not physical proof. An I/O timeout poisons the transport; independent
        hardware stopping remains necessary. LO is deliberately not used as STOP.
        """
        self._ready()
        self._ack('ES')

    def speed(self, axis, level):
        self._ready(axis, movement=True)
        integer(level, 'speed level', 1, 8)
        with self.io.transaction():
            self._select(axis)
            self._ack(f'LD {level} SP', str(level))
            self._ack('SP', str(level))

    def wait(self, axis, *, target=None, polarization=None, timeout=60, tolerance=0.1, cancelled=None):
        self._ready(axis)
        timeout = number(timeout, 'motion timeout', 0.01, 3600)
        tolerance = number(tolerance, 'position tolerance', 0, 10)
        if target is not None:
            target = number(target, 'target', 0, 100000)
        if polarization not in (None, 'PH', 'PV'):
            raise ValueError('polarization must be PH or PV')
        if target is None and polarization is None:
            raise ValueError('A target position or polarization is required')
        deadline = time.monotonic() + timeout
        stable_since = None
        while time.monotonic() < deadline:
            if cancelled is not None and cancelled():
                raise InterruptedError('Motion cancelled')
            state = self.position(axis)
            reached = not state.busy and (target is None or abs(state.value-target) <= tolerance)
            reached = reached and (polarization is None or state.polarization == polarization)
            # BU can initially be zero before the motor starts. Never accept idle alone.
            if reached:
                if stable_since is None:
                    stable_since = time.monotonic()
                if time.monotonic() - stable_since >= 0.5:
                    return state
            else:
                stable_since = None
            time.sleep(self.poll_seconds)
        raise TimeoutError(f'CO3000 target not confirmed: {axis}')

    def move(self, axis, value, *, timeout=60, tolerance=0.1, cancelled=None):
        self._target(axis, value)
        number(timeout, 'motion timeout', 0.01, 3600)
        number(tolerance, 'position tolerance', 0, 10)
        def start():
            if cancelled is not None and cancelled():
                raise InterruptedError('Motion cancelled before start')
            self.start(axis, value)
        with self.io.transaction(), managed_run(start, self.stop_all):
            return self.wait(axis, target=value, timeout=timeout, tolerance=tolerance, cancelled=cancelled)

    def polarize(self, axis, orientation, *, timeout=60, cancelled=None):
        self._ready(axis, movement=True)
        number(timeout, 'motion timeout', 0.01, 3600)
        if self.axes[axis]['unit'] != 'CM' or orientation not in ('H', 'V'):
            raise ValueError('Polarization requires mast axis and H or V')
        command = 'P' + orientation
        def start():
            if cancelled is not None and cancelled():
                raise InterruptedError('Polarization cancelled before start')
            self._select(axis)
            if self.position(axis).busy:
                raise InstrumentError('Mast already moving')
            self._ack(command)
        with self.io.transaction(), managed_run(start, self.stop_all):
            return self.wait(axis, polarization=command, timeout=timeout, cancelled=cancelled)


def scan_positions(controller, axis, positions, measure, *, return_to_peak=True, cancelled=None, timeout=60):
    """Discrete sampled peak only. Callback returns finite scalar in one fixed unit.

    This is not a continuous maximum search or an FCC-compliant test recipe.
    Caller owns DUT TX, analyzer configuration, correction factors and RF shutdown.
    """
    values = [controller._target(axis, value) for value in positions]
    if not values or len(values) > 10000:
        raise ValueError('Expected 1..10000 positions')
    number(timeout, 'motion timeout', 0.01, 3600)
    rows = []
    with controller.io.transaction(), managed_run(lambda: None, controller.stop_all):
        for value in values:
            if cancelled is not None and cancelled():
                raise InterruptedError('Scan cancelled')
            state = controller.move(axis, value, timeout=timeout, cancelled=cancelled)
            reading = scalar(measure())
            observed = controller.position(axis)
            if observed.busy or abs(observed.value-state.value) > 0.1:
                raise InstrumentError('Axis moved during measurement')
            rows.append(dict(requested=value, actual=observed.value, unit=observed.unit, reading=reading))
        peak = max(rows, key=lambda row: row['reading'])
        if return_to_peak:
            controller.move(axis, peak['actual'], timeout=timeout, cancelled=cancelled)
        return dict(samples=rows, peak=peak, returned_to_peak=bool(return_to_peak))


def scan_radiated_grid(controller, *, mast_axis, table_axis, heights_cm, angles_deg, polarizations,
                       measure, unit, return_to_peak=True, cancelled=None, timeout=60):
    """Sample H/V × height × angle, with actual positions and peak return.

    Only samples the supplied grid. Does not claim a global/continuous RF maximum.
    The measurement callback owns all analyzer settings, settling and corrections.
    """
    controller._ready(mast_axis,movement=True)
    controller._ready(table_axis,movement=True)
    if controller.axes[mast_axis]['unit']!='CM' or controller.axes[table_axis]['unit']!='DG':
        raise ValueError('Mast must use CM and table must use DG')
    heights=[controller._target(mast_axis,x) for x in heights_cm]
    angles=[controller._target(table_axis,x) for x in angles_deg]
    pols=list(polarizations)
    if not heights or not angles or not pols or any(p not in ('H','V') for p in pols):
        raise ValueError('Nonempty heights/angles and H/V polarizations required')
    if len(heights)*len(angles)*len(pols)>10000:
        raise ValueError('Maximum 10000 grid points')
    if not isinstance(unit,str) or not unit.strip():
        raise ValueError('Measurement unit required')
    number(timeout,'motion timeout',.01,3600)
    rows=[]
    with controller.io.transaction(), managed_run(lambda:None,controller.stop_all):
        for pol in pols:
            controller.polarize(mast_axis,pol,timeout=timeout,cancelled=cancelled)
            for height in heights:
                controller.move(mast_axis,height,timeout=timeout,cancelled=cancelled)
                for angle in angles:
                    if cancelled is not None and cancelled():
                        raise InterruptedError('Grid scan cancelled')
                    controller.move(table_axis,angle,timeout=timeout,cancelled=cancelled)
                    before_mast=controller.position(mast_axis)
                    before_table=controller.position(table_axis)
                    if (before_mast.busy or before_table.busy or before_mast.polarization!='P'+pol
                            or abs(before_mast.value-height)>.1 or abs(before_table.value-angle)>.1):
                        raise InstrumentError('Grid position not stable before reading')
                    reading=scalar(measure())
                    mast=controller.position(mast_axis);table=controller.position(table_axis)
                    if mast.busy or table.busy or mast.polarization!='P'+pol or abs(mast.value-height)>.1 or abs(table.value-angle)>.1:
                        raise InstrumentError('Grid position changed during reading')
                    rows.append(dict(height_cm=mast.value,angle_deg=table.value,polarization=pol,reading=reading,unit=unit))
        peak=max(rows,key=lambda r:r['reading'])
        if return_to_peak:
            controller.polarize(mast_axis,peak['polarization'],timeout=timeout,cancelled=cancelled)
            controller.move(mast_axis,peak['height_cm'],timeout=timeout,cancelled=cancelled)
            controller.move(table_axis,peak['angle_deg'],timeout=timeout,cancelled=cancelled)
        return dict(samples=rows,peak=peak,returned_to_peak=bool(return_to_peak))
