"""A bounded, in-memory adapter for the existing synthetic N1914A profile."""
import copy
import hashlib
import json
import math
import re
import threading

from labflow.virtual_lab import VirtualLab


_PROFILE = 'n1914a-a-ascii-v1'
_BASIS = 'documented_semantics_with_synthetic_response'
_IDENTITY = 'DGM Virtual,N1914A,SIM-001,SIM-1'
_BASE = {'status', 'response', 'synthetic', 'hardware_verified', 'profile_id',
         'response_basis', 'tick'}
_MEASUREMENT = {'measurement_id', 'setup_revision', 'completed_tick',
                'value', 'unit', 'synthetic'}
_STATUSES = {'ok', 'pending', 'no_data', 'invalid', 'unsupported',
             'disconnected', 'error', 'busy'}
_REASONS = {'configuration_changed', 'abort_before_trigger_change', 'invalid_command',
            'single_ascii_command_required', 'outside_virtual_profile'}
_ERRORS = {0: 'No error', -211: 'Trigger ignored', -213: 'INIT ignored', -350: 'Queue overflow'}
_NUMERIC = re.compile(r'[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?|NaN|Infinity|inf)')
_PREPARE = ('INIT1:CONT OFF', 'FORM:DATA ASCII', 'TRIG1:SOUR IMM')


def _model(model):
    if type(model) is not str or model != 'N1914A':
        raise ValueError('unsupported_model')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def describe_virtual_n1914a_contract(model='N1914A'):
    """Return detached scope metadata without observing or operating a lab."""
    _model(model)
    return {
        'schema_version': 1, 'model': model, 'profile_id': _PROFILE,
        'backend': 'existing_virtual_lab', 'synthetic': True, 'hardware_verified': False,
        'vendor_binary_executed': False, 'units': ['DBM', 'W'],
        'timeout_ticks': {'minimum': 1, 'maximum': 1000, 'default': 20},
        'receipt_limit': 128, 'receipt_scope': 'adapter_instance_memory',
        'window': 1, 'synthetic_input': 'A',
        'sensor_compatibility': 'not_assessed', 'calibration': 'not_assessed',
        'firmware': 'not_assessed', 'options': 'not_assessed', 'real_support': 'not_assessed',
        'current_setup_match': 'not_assessed', 'resumable': False,
        'rf_control_performed': False, 'rf_safe_verified': False,
        'commands': ['*IDN?', 'SYST:ERR?', *_PREPARE, 'UNIT1:POW DBM',
                     'UNIT1:POW W', 'UNIT1:POW?', 'INIT1', '*OPC?', 'FETC1?', 'ABOR1'],
        'source': {'document': 'N1913-90008.pdf', 'edition': 19, 'date': '2025-06-11',
                   'sha256': 'ecaf6faf71890f01289261087c13cd32b5b661edbd69a303cd0f636691fb28c2'},
    }


class _Stop(Exception):
    def __init__(self, code, status='failed'):
        self.code, self.status = code, status


def _public_reply(raw, command):
    """Copy only bounded, recognized public DTOs; reject unknown/private material."""
    if type(raw) is not dict or not _BASE <= raw.keys():
        raise ValueError
    if raw.keys() - (_BASE | {'reason', 'error_number', 'error_message', 'measurement'}):
        raise ValueError
    if type(raw['status']) is not str or raw['status'] not in _STATUSES:
        raise ValueError
    if type(raw['synthetic']) is not bool or type(raw['hardware_verified']) is not bool:
        raise ValueError
    if raw['profile_id'] != _PROFILE or raw['response_basis'] != _BASIS:
        raise ValueError
    if type(raw['tick']) is not int or raw['tick'] < 0:
        raise ValueError
    response = raw['response']
    if response is not None:
        if type(response) is not str or len(response) > 128 or not response.isascii():
            raise ValueError
        if command == '*IDN?':
            valid = re.fullmatch(r'DGM Virtual,[A-Z][A-Z0-9]{1,15},SIM-001,SIM-1', response)
        elif command == 'UNIT1:POW?':
            valid = response in ('DBM', 'W')
        elif command == 'SYST:ERR?':
            valid = response in {f'{code:+d},"{message}"' for code, message in _ERRORS.items()}
        else:
            valid = _NUMERIC.fullmatch(response)
        if not valid:
            raise ValueError
    if 'reason' in raw and (type(raw['reason']) is not str or raw['reason'] not in _REASONS):
        raise ValueError
    if 'error_number' in raw and (type(raw['error_number']) is not int
                                  or raw['error_number'] not in _ERRORS):
        raise ValueError
    if 'error_message' in raw and (type(raw['error_message']) is not str
                                   or raw['error_message'] not in _ERRORS.values()):
        raise ValueError
    if 'measurement' in raw:
        m = raw['measurement']
        if type(m) is not dict or m.keys() != _MEASUREMENT:
            raise ValueError
        if any(type(m[k]) not in (int, float, bool, type(None))
               for k in ('measurement_id', 'setup_revision', 'completed_tick', 'value')):
            raise ValueError
        if type(m['unit']) is not str or m['unit'] not in ('DBM', 'W'):
            raise ValueError
        if type(m['synthetic']) is not bool:
            raise ValueError
    data = _canonical(raw)
    if len(data) > 16384:
        raise ValueError
    return json.loads(data)


class _MeasurementRun:
    def __init__(self, adapter, unit, timeout, continuation):
        self.adapter, self.lab = adapter, adapter._lab
        self.unit, self.timeout, self.continuation = unit, timeout, continuation
        self.transcript = []
        self.start_tick = self.tick = self.init_tick = self.complete_tick = None
        self.advance_attempts = self.error_attempts = 0
        self.may_have_started = False

    def gate(self):
        if self.continuation is None:
            return
        try:
            allowed = self.continuation() is True
        except Exception:
            allowed = False
        if not allowed:
            raise _Stop('continuation_denied', 'cancelled')

    def reject(self, code):
        self.transcript[-1]['code'] = code
        raise _Stop(code)

    def call(self, command=None, *, advance=False, cleanup=False):
        if not cleanup:
            self.gate()
        # Set before dispatch: an exception cannot tell us whether INIT executed.
        if command == 'INIT1':
            self.may_have_started = True
        if advance:
            self.advance_attempts += 1
        if command == 'SYST:ERR?':
            self.error_attempts += 1
        row = {'sequence': len(self.transcript) + 1,
               'operation': 'advance' if advance else 'meter',
               'command': command, 'ticks': 1 if advance else None,
               'reply': None, 'code': None}
        self.transcript.append(row)
        try:
            raw = self.lab.advance(1) if advance else self.lab.meter(command)
        except Exception:
            self.reject('emulator_exception')
        try:
            reply = _public_reply(raw, command)
        except Exception:
            self.reject('invalid_reply')
        row['reply'] = reply
        if reply['status'] in ('pending', 'busy'):
            self.may_have_started = True
        if reply['synthetic'] is not True or reply['hardware_verified'] is not False:
            self.reject('invalid_reply')
        if self.tick is not None and reply['tick'] != self.tick + int(advance):
            self.reject('tick_mismatch')
        if self.start_tick is None:
            self.start_tick = reply['tick']
        self.tick = reply['tick']
        status = reply['status']
        extra = set(reply) - _BASE
        expected = ({'error_number'} if command == 'SYST:ERR?' else
                    {'measurement'} if command == 'FETC1?' else set())
        if status == 'ok':
            if extra != expected:
                self.reject('invalid_reply')
        else:
            expected = ({'error_number', 'error_message'} if status == 'error' else
                        {'reason'} if status in ('invalid', 'unsupported', 'busy') else set())
            if extra != expected or reply['response'] is not None:
                self.reject('invalid_reply')
        return reply

    def ok(self, reply, *, ack=False):
        if reply['status'] != 'ok':
            self.reject('meter_' + reply['status'])
        if ack and reply['response'] is not None:
            self.reject('invalid_reply')
        return reply

    def error_check(self):
        reply = self.ok(self.call('SYST:ERR?'))
        code = reply['error_number']
        if reply['response'] != f'{code:+d},"{_ERRORS[code]}"':
            self.reject('invalid_reply')
        if code:
            self.reject('error_queue_nonzero')

    def fetch(self):
        reply = self.ok(self.call('FETC1?'))
        m = reply['measurement']
        if (type(m['measurement_id']) is not int or m['measurement_id'] <= 0
                or type(m['setup_revision']) is not int or m['setup_revision'] < 0
                or type(m['completed_tick']) is not int
                or type(m['value']) not in (int, float)
                or m['synthetic'] is not True):
            self.reject('invalid_measurement')
        try:
            finite = math.isfinite(m['value'])
        except (OverflowError, ValueError):
            finite = False
        if not finite or (self.unit == 'W' and m['value'] <= 0):
            self.reject('invalid_measurement')
        if m['unit'] != self.unit:
            self.reject('unit_mismatch')
        if (m['completed_tick'] <= self.init_tick
                or m['completed_tick'] != self.complete_tick
                or m['completed_tick'] != self.tick):
            self.reject('invalid_measurement')
        if m['measurement_id'] <= self.adapter._last_measurement_id:
            self.reject('measurement_id_not_fresh')
        if m['setup_revision'] < self.adapter._last_setup_revision:
            self.reject('setup_revision_reversed')
        if reply['response'] != f"{m['value']:+.9E}":
            self.reject('wire_value_mismatch')
        self.adapter._last_measurement_id = m['measurement_id']
        self.adapter._last_setup_revision = m['setup_revision']
        return copy.deepcopy(m)

    def execute(self):
        measurement = None
        cleanup = {'status': 'not_needed', 'code': None}
        try:
            identity = self.ok(self.call('*IDN?'))
            if identity['response'] != _IDENTITY:
                self.reject('identity_mismatch')
            self.error_check()
            for command in (*_PREPARE, 'UNIT1:POW ' + self.unit):
                self.ok(self.call(command), ack=True)
                self.error_check()
            if self.ok(self.call('UNIT1:POW?'))['response'] != self.unit:
                self.reject('unit_mismatch')
            self.ok(self.call('INIT1'), ack=True)
            self.init_tick = self.tick
            self.error_check()
            while True:
                reply = self.call('*OPC?')
                if reply['status'] == 'ok':
                    self.ok(reply)
                    if reply['response'] != '1':
                        self.reject('invalid_reply')
                    self.complete_tick = self.tick
                    break
                if reply['status'] != 'pending':
                    self.ok(reply)
                if self.advance_attempts >= self.timeout:
                    self.transcript[-1]['code'] = 'completion_timeout'
                    raise _Stop('completion_timeout', 'timeout')
                self.ok(self.call(advance=True), ack=True)
            measurement = self.fetch()
            self.error_check()
            self.gate()  # Publication fence, even after a valid fetch/error check.
            status, code = 'completed', None
        except _Stop as failure:
            status, code = failure.status, failure.code
            measurement = None
            if self.may_have_started:
                try:
                    self.ok(self.call('ABOR1', cleanup=True), ack=True)
                    cleanup = {'status': 'completed', 'code': None}
                except _Stop as abort_failure:
                    cleanup = {'status': 'failed', 'code': abort_failure.code}
        return {
            'status': status, 'code': code, 'measurement': measurement,
            'ticks': {'start': self.start_tick, 'end': self.tick,
                      'advance_attempts': self.advance_attempts},
            'transcript': self.transcript,
            'transcript_sha256': hashlib.sha256(_canonical(self.transcript)).hexdigest(),
            'error_queue': {'consuming': True, 'attempts': self.error_attempts},
            'cleanup': cleanup,
        }


class N1914AVirtualAdapter:
    """Sequential existing-VirtualLab calls; no transport or real I/O fallback."""
    def __init__(self, lab, *, model='N1914A'):
        _model(model)
        if type(lab) is not VirtualLab:
            raise ValueError('virtual_lab_required')
        self._lab = lab
        self._lock = threading.Lock()
        self._receipts = {}
        self._last_measurement_id = 0
        self._last_setup_revision = 0

    def measure(self, request_id, *, unit='DBM', timeout_ticks=20, can_continue=None):
        if (type(request_id) is not str
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', request_id)):
            raise ValueError('invalid_request_id')
        if type(unit) is not str or unit not in ('DBM', 'W'):
            raise ValueError('unsupported_unit')
        if type(timeout_ticks) is not int or not 1 <= timeout_ticks <= 1000:
            raise ValueError('invalid_timeout_ticks')
        if can_continue is not None and not callable(can_continue):
            raise ValueError('invalid_continuation')
        settings = (unit, timeout_ticks)
        if not self._lock.acquire(blocking=False):
            raise ValueError('adapter_busy')
        try:
            if request_id in self._receipts:
                previous_settings, frozen = self._receipts[request_id]
                if previous_settings != settings:
                    raise ValueError('request_conflict')
                return json.loads(frozen)
            if len(self._receipts) >= 128:
                raise ValueError('receipt_limit_reached')
            receipt = {
                'schema_version': 1, 'request_id': request_id,
                'model': 'N1914A', 'profile_id': _PROFILE,
                'backend': 'existing_virtual_lab', 'synthetic': True,
                'hardware_verified': False, 'vendor_binary_executed': False,
                'sensor_compatibility': 'not_assessed', 'calibration': 'not_assessed',
                'firmware': 'not_assessed', 'options': 'not_assessed',
                'real_support': 'not_assessed', 'current_setup_match': 'not_assessed',
                'resumable': False, 'rf_control_performed': False, 'rf_safe_verified': False,
                'request': {'unit': unit, 'timeout_ticks': timeout_ticks},
                **_MeasurementRun(self, unit, timeout_ticks, can_continue).execute(),
            }
            frozen = _canonical(receipt)
            self._receipts[request_id] = (settings, frozen)
            return json.loads(frozen)
        finally:
            self._lock.release()
