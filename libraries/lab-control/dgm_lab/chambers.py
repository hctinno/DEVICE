"""Controller-scoped climate control. Chamber model alone does not identify its controller."""
from .core import UnsupportedInstrument, InstrumentError, number, integer, fmt, scalar, close_enough, managed_run


class Thermotron8800:
    source_id = 'thermotron-8800'

    def __init__(self, transport, *, channel, minimum, maximum, acknowledgement,
                 installed_controller_confirmed=False):
        if installed_controller_confirmed is not True:
            raise UnsupportedInstrument('Installed 8800 controller and equipment-specific manual must be confirmed')
        if type(acknowledgement) is not bool:
            raise ValueError('Specify the actual Send Acknowledgement setting')
        self.io = transport
        self.channel = integer(channel, 'process channel', 1, 8)
        self.minimum = number(minimum, 'minimum')
        self.maximum = number(maximum, 'maximum', self.minimum)
        self.acknowledgement = acknowledgement
        self.identified = False

    def identify(self):
        self.identified = False
        response = self.io.query('IDEN?')
        if response.strip().upper() != '8800 CHAMBER CONTROLLER':
            raise UnsupportedInstrument(f'Expected 8800 controller; got {response!r}')
        self.identified = True
        return response

    def _ready(self):
        if not self.identified:
            raise UnsupportedInstrument('Identify the controller first')

    def _command(self, command):
        self._ready()
        if self.acknowledgement:
            ack = self.io.query(command)
            if ack != '0':
                raise InstrumentError(f'8800 command rejected: {ack!r}')
        else:
            self.io.write(command)

    def _errors(self):
        errors = []
        for _ in range(9):
            raw = self.io.query('IERR?')
            try:
                code = int(raw)
            except ValueError as exc:
                raise InstrumentError(f'Invalid 8800 error: {raw!r}') from exc
            if code == 0:
                if errors:
                    raise InstrumentError(f'8800 errors: {errors}')
                return
            errors.append(code)
        raise InstrumentError(f'8800 error buffer not empty: {errors}')

    def start(self):
        self._ready()
        with self.io.transaction():
            self._errors()
            # Explicit operation: controller starts with its EXISTING manual setpoint.
            self._command('RUNM')
            if self.io.query('STAT?') != '16':
                raise InstrumentError('8800 did not enter manual run mode')
            self._errors()

    def setpoint(self, value):
        number(value, 'setpoint in configured controller units', self.minimum, self.maximum)
        self._ready()
        with self.io.transaction():
            if self.io.query('STAT?') not in ('16', '32'):
                raise InstrumentError('SETP requires manual mode; explicit start() is required')
            self._command(f'SETP{self.channel},{fmt(value)}')
            self._errors()
            close_enough(scalar(self.io.query(f'SETP{self.channel}?')), value, abs_tol=0.05)

    def read_process(self):
        self._ready()
        return scalar(self.io.query(f'PVAR{self.channel}?'))

    def stop(self):
        self._ready()
        with self.io.transaction():
            self._command('STOP')
            status = self.io.query('STAT?')
            if status != '0':
                raise InstrumentError(f'8800 stop not confirmed: {status!r}')
            self._errors()

    def running(self):
        return managed_run(self.start, self.stop)


class EspecController:
    """P300/SCP220 text protocol, no guessed SH-642 controller association.

    Implements the manufacturer's public ChamberConnectLibrary wire protocol.
    Serial address prefixes and RS485 multidrop are deliberately not supported.
    """
    source_id = 'espec-chamberconnect'

    def __init__(self, transport, *, expected_rom, minimum_c, maximum_c,
                 installed_controller_confirmed=False):
        if installed_controller_confirmed is not True or not expected_rom:
            raise UnsupportedInstrument('Confirm P300/SCP220 and provide exact ROM? response from your controller')
        self.io = transport
        self.expected_rom = expected_rom
        self.minimum = number(minimum_c, 'minimum_c')
        self.maximum = number(maximum_c, 'maximum_c', self.minimum)
        self.identified = False
        self.configured = False

    def _exchange(self, command):
        result = self.io.query(command)  # writes also produce acknowledgements
        if result.startswith('NA:'):
            raise InstrumentError(f'ESPEC rejected {command!r}: {result}')
        return result

    def identify(self):
        self.identified = False
        self.configured = False
        response = self._exchange('ROM?')
        if response != self.expected_rom:
            raise UnsupportedInstrument(f'ESPEC ROM mismatch: {response!r}')
        self.identified = True
        return response

    def _ready(self):
        if not self.identified:
            raise UnsupportedInstrument('Identify controller first')

    def temperature(self):
        self._ready()
        raw = self._exchange('TEMP?')
        values = raw.split(',')
        if len(values) != 4:
            raise InstrumentError(f'Unexpected TEMP? response: {raw!r}')
        return dict(zip(('process_c', 'setpoint_c', 'maximum_c', 'minimum_c'), map(scalar, values)))

    def configure(self, *, temperature_c):
        number(temperature_c, 'temperature_c', self.minimum, self.maximum)
        self._ready()
        self.configured = False
        with self.io.transaction():
            self.stop()
            current = self.temperature()
            number(temperature_c, 'installed controller range', current['minimum_c'], current['maximum_c'])
            self._exchange(f'TEMP, S{temperature_c:.1f}')
            close_enough(self.temperature()['setpoint_c'], temperature_c, abs_tol=0.051)
            self.configured = True

    def start(self):
        self._ready()
        if not self.configured:
            raise InstrumentError('configure() must succeed before constant operation')
        with self.io.transaction():
            self._exchange('MODE,CONSTANT')
            if self._exchange('MODE?') != 'CONSTANT':
                raise InstrumentError('ESPEC constant operation not confirmed')

    def stop(self):
        self._ready()
        with self.io.transaction():
            self._exchange('MODE,STANDBY')
            if self._exchange('MODE?') != 'STANDBY':
                raise InstrumentError('ESPEC standby not confirmed')

    def running(self):
        return managed_run(self.start, self.stop)
