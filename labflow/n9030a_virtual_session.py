"""Bounded N9030A SCPI-like session over one existing synthetic VirtualFleet.

This is an application envelope, not a wire protocol or an instrument driver.
Only public Fleet topology, catalog, execute, advance and observations are used.
"""
from decimal import Decimal, InvalidOperation
import json
import math
import re
import uuid

from labflow.virtual_fleet.core import VirtualFleet


_SOURCE = {'document': 'N9060-90027', 'edition': 23, 'date': '2018-12',
           'sha256': '2429ceb7a23fd09391c414790764d0e08fe567d6181107fe975ce5b866369401',
           'pdf_pages_1based': [235, 236, 432, 636, 655, 919, 983, 984, 998, 999, 1063, 1064]}
_FREQ = r'(?:SENS(?:E)?:)?FREQ(?:UENCY)?:CENT(?:ER)?'
_SPAN = r'(?:SENS(?:E)?:)?FREQ(?:UENCY)?:SPAN'
_RBW = r'(?:SENS(?:E)?:)?(?:BAND(?:WIDTH)?|BWID(?:TH)?)(?::RES(?:OLUTION)?)?'
_DET = r'(?:SENS(?:E)?:)?DET(?:ECTOR)?(?::FUNC(?:TION)?)?'
_NUMBER = re.compile(r'([+]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)(?: ?(HZ|KHZ|MHZ|GHZ))?')
_SCALE = {'HZ': Decimal(1), 'KHZ': Decimal(1000),
          'MHZ': Decimal(1000000), 'GHZ': Decimal(1000000000)}


def _copy(value):
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))


def _hertz(argument):
    match = _NUMBER.fullmatch(argument)
    if match is None:
        return None
    try:
        value = Decimal(match[1]) * _SCALE[match[2] or 'HZ']
        result = float(value)
    except (InvalidOperation, OverflowError, ValueError):
        return None
    if not value.is_finite() or value <= 0 or not math.isfinite(result) or result <= 0:
        return None
    return result


class N9030AVirtualSession:
    """Bind one explicit N9030A signal analyzer; caller serializes Fleet use."""

    def __init__(self, fleet, *, device_id):
        if type(fleet) is not VirtualFleet:
            raise ValueError('virtual_fleet_required')
        if type(device_id) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', device_id) is None:
            raise ValueError('explicit_device_id_required')
        node = next((item for item in fleet.topology['devices'] if item['id'] == device_id), None)
        if node is None:
            raise ValueError('unknown_device_id')
        profile = next(item for item in fleet.catalog['profiles'] if item['profile_id'] == node['profile_id'])
        if profile['model'] != 'N9030A' or profile['role'] != 'signal_analyzer':
            raise ValueError('n9030a_signal_analyzer_required')
        self._fleet, self._device_id, self._profile_id = fleet, device_id, profile['profile_id']
        self._namespace = 'n9030a:' + uuid.uuid4().hex
        self._sequence = 0

    def _request_id(self):
        self._sequence += 1
        return self._namespace + ':' + str(self._sequence)

    def _observe(self):
        return self._fleet.observations()['devices'][self._device_id]

    def _reply(self, command, observation, *, status='ok', code=None, response=None,
               receipt=None, measurement=None, error=None, error_source=None, basis=None):
        return _copy({'schema_version': 1, 'command': command, 'status': status,
            'code': code, 'response': response, 'measurement': measurement,
            'error': error, 'error_source': error_source, 'device_id': self._device_id,
            'profile_id': self._profile_id, 'model': 'N9030A', 'role': 'signal_analyzer',
            'tick': observation['tick'], 'setup_revision': observation['setup_revision'],
            'synthetic': True, 'hardware_verified': False, 'physical_verified': False,
            'firmware_support': 'not_assessed', 'options_support': 'not_assessed',
            'calibration_support': 'not_assessed',
            'response_basis': basis or 'documented_subset_over_existing_fleet_synthetic_state',
            'source_reference': _SOURCE, 'fleet_receipt': receipt, 'observation': observation})

    def _action(self, command, action, parameters=None):
        receipt = self._fleet.execute(self._request_id(), self._device_id, action, parameters)
        current = self._observe()
        return self._reply(command, current, status=receipt['status'],
                           code=None if receipt['status'] in ('ok', 'pending') else 'fleet_action_failed',
                           receipt=receipt,
                           error_source=None if receipt['status'] in ('ok', 'pending') else 'existing_virtual_fleet')

    def advance(self, ticks=1):
        """Advance the same Fleet explicitly, with no wall-clock implication."""
        receipt = self._fleet.advance(self._request_id(), ticks)
        return self._reply(None, self._observe(), status=receipt['status'], receipt=receipt)

    def fetch_current_scalar(self):
        """Fleet-native scalar fetch; deliberately not a vendor CHPower SCPI response."""
        receipt = self._fleet.execute(self._request_id(), self._device_id, 'fetch')
        current = self._observe()
        if receipt['status'] != 'ok':
            return self._reply(None, current, status=receipt['status'], code='fleet_fetch_unavailable',
                               receipt=receipt, error_source='existing_virtual_fleet', basis='fleet_native_scalar')
        measurement = receipt['values'].get('outputs', {}).get('measurement')
        if (type(measurement) is not dict or measurement.get('status') != 'ok'
                or measurement.get('valid') is not True or measurement.get('unit') != 'dBm'
                or measurement.get('quantity') not in ('on_average', 'time_average', 'peak')
                or type(measurement.get('value')) not in (int, float)
                or not math.isfinite(measurement['value'])
                or current['status'] != 'ok'
                or current['values'].get('outputs', {}).get('measurement') != measurement
                or measurement.get('acquisition_setup_revision') != current['setup_revision']):
            return self._reply(None, current, status='invalid', code='measurement_not_current_or_outside_scalar_subset',
                               receipt=receipt, error_source='existing_virtual_fleet', basis='fleet_native_scalar')
        return self._reply(None, current, response=format(measurement['value'], '+.17E'),
                           receipt=receipt, measurement=measurement, basis='fleet_native_scalar')

    def command(self, command):
        """Return structured application envelopes for one ASCII command at a time."""
        observation = self._observe()
        text = command if type(command) is str and len(command) <= 256 else None

        def refuse(code, status='unsupported', source='session_parser'):
            return self._reply(text, observation, status=status, code=code, error_source=source)

        if (text is None or not text.strip(' ') or not text.isascii()
                or any(ord(char) < 32 or ord(char) == 127 for char in text)):
            return refuse('invalid_single_ascii_command', 'invalid')
        if ';' in text:
            return refuse('single_command_required', 'invalid')
        normalized = re.sub(r' +', ' ', text.strip(' ').upper())
        if normalized.startswith(':*'):
            return refuse('outside_n9030a_subset')
        if normalized.startswith(':'):
            normalized = normalized[1:]
        if observation['status'] == 'disconnected':
            return refuse('fleet_disconnected', 'disconnected', 'existing_virtual_fleet')
        values = observation['values']
        if type(values.get('operation_complete')) is not bool or type(values.get('configuration')) is not dict:
            return refuse('fleet_observation_unavailable', 'invalid', 'existing_virtual_fleet')
        config = values['configuration']

        if normalized == '*IDN?':
            return self._reply(text, observation, response='DGM Virtual,N9030A,SYNTHETIC,SIM-1')
        if normalized == '*OPC?':
            complete = values['operation_complete']
            return self._reply(text, observation, status='ok' if complete else 'pending',
                               response='1' if complete else None)

        for header, key in ((_FREQ, 'frequency_hz'), (_SPAN, 'bandwidth_hz'), (_RBW, 'rbw_hz')):
            if re.fullmatch(header + r'\?', normalized):
                value = config.get(key)
                if type(value) not in (int, float) or not math.isfinite(value):
                    return refuse('setting_unavailable', 'invalid', 'existing_virtual_fleet')
                return self._reply(text, observation, response=format(value, '+.17E'))
            match = re.fullmatch(header + r' (.+)', normalized)
            if match:
                number = _hertz(match[1])
                if number is None:
                    return refuse('invalid_frequency_quantity', 'invalid')
                if key in ('frequency_hz', 'bandwidth_hz'):
                    center = number if key == 'frequency_hz' else config.get('frequency_hz')
                    span = number if key == 'bandwidth_hz' else config.get('bandwidth_hz')
                    if (type(center) not in (int, float) or type(span) not in (int, float)
                            or not math.isfinite(center) or not math.isfinite(span)
                            or center - span / 2 < 0):
                        return refuse('span_outside_synthetic_window', 'invalid')
                return self._action(text, 'configure', {key: number})

        if re.fullmatch(_DET + r'\?', normalized):
            selected = config.get('detector')
            if selected not in ('rms', 'peak'):
                return refuse('detector_outside_scalar_subset')
            return self._reply(text, observation, response='AVER' if selected == 'rms' else 'POS')
        match = re.fullmatch(_DET + r' (RMS|POS(?:ITIVE)?)', normalized)
        if match:
            return self._action(text, 'configure', {'detector': 'rms' if match[1] == 'RMS' else 'peak'})
        if re.fullmatch(r'INIT(?:IATE)?:IMM(?:EDIATE)?', normalized):
            return self._action(text, 'acquire')
        if re.fullmatch(r'ABOR(?:T)?', normalized):
            return self._action(text, 'abort')
        if re.fullmatch(r'SYST(?:EM)?:ERR(?:OR)?(?::NEXT)?\?', normalized):
            receipt = self._fleet.execute(self._request_id(), self._device_id, 'read_error')
            current = self._observe()
            if 'error' not in receipt['values'] or receipt['status'] == 'disconnected':
                return self._reply(text, current, status=receipt['status'], code='fleet_error_query_unavailable',
                                   receipt=receipt, error_source='existing_virtual_fleet')
            reason = receipt['values']['error']
            return self._reply(text, current, response='+0,"No error"' if reason is None else None,
                               error={'source': 'existing_virtual_fleet', 'reason': reason,
                                      'vendor_number': None, 'consuming': True}, receipt=receipt)
        if normalized.startswith(('FETC', 'TRAC')):
            return refuse('vendor_channel_power_or_trace_semantics_unavailable')
        return refuse('outside_n9030a_subset')
