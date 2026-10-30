"""Bounded N1911A SCPI subset over one existing in-memory VirtualFleet device.

No transport, clock loop, RF arithmetic, independent window cache, calibration
implementation or N1914A alias. Native Fleet receipts remain the authority.
"""
import json
import math
import re
import uuid

from labflow.virtual_fleet.core import VirtualFleet


_UNIT = re.compile(r'UNIT([1-4])?:POW(?:ER)?(?:\?| (DBM|W))')
_FETCH = re.compile(r'FETC(?:H)?([1-4])?(?::SCAL(?:AR)?)?(?::POW(?:ER)?:AC)?\?')
_TRIGGER = re.compile(r'TRIG(?:GER)?(?:1|:SEQ(?:UENCE)?1?)?:SOUR(?:CE)?(?:\?| (IMM(?:EDIATE)?|BUS))')
_SOURCE = {'document': 'N1912-90008', 'edition': 21, 'date': '2022-04-15',
           'sha256': 'c66464fa16689b8af26ad6fc9922d41334f11971bb012ded3eee8e620019e12f',
           'pdf_pages_1based': [70, 132, 133, 134, 265, 266, 516, 644, 648,
                                659, 660, 661, 679, 680, 681, 722, 723, 735, 736, 745]}


def _copy(value):
    return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))


class N1911AVirtualSession:
    """Borrow an exact N1911A/power_meter binding; caller serializes Fleet use.

    UNIT/FETCH act only on the Fleet's currently configured measurement window.
    A different window is refused, never selected or reconstructed implicitly.
    INIT/TRIG/ABOR channel 1 is the N1911A's single physical measurement input.
    """
    def __init__(self, fleet, *, device_id):
        if type(fleet) is not VirtualFleet:
            raise ValueError('virtual_fleet_required')
        if type(device_id) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', device_id) is None:
            raise ValueError('explicit_device_id_required')
        node = next((item for item in fleet.topology['devices'] if item['id'] == device_id), None)
        if node is None:
            raise ValueError('unknown_device_id')
        profile = next(item for item in fleet.catalog['profiles'] if item['profile_id'] == node['profile_id'])
        if profile['model'] != 'N1911A' or profile['role'] != 'power_meter':
            raise ValueError('n1911a_power_meter_required')
        self._fleet, self._device_id, self._profile_id = fleet, device_id, profile['profile_id']
        self._namespace = 'n1911a:' + uuid.uuid4().hex
        self._sequence = 0

    def _request_id(self):
        self._sequence += 1
        return self._namespace + ':' + str(self._sequence)

    def _observe(self):
        return self._fleet.observations()['devices'][self._device_id]

    def _reply(self, command, observation, *, status='ok', code=None, response=None,
               receipt=None, measurement=None, error=None, error_source=None):
        return _copy({'schema_version': 1, 'command': command, 'status': status, 'code': code,
            'response': response, 'measurement': measurement, 'error': error, 'error_source': error_source,
            'device_id': self._device_id, 'profile_id': self._profile_id, 'model': 'N1911A',
            'role': 'power_meter', 'tick': observation['tick'], 'setup_revision': observation['setup_revision'],
            'synthetic': True, 'hardware_verified': False, 'physical_verified': False,
            'firmware_support': 'not_assessed', 'calibration_support': 'not_assessed',
            'response_basis': 'documented_subset_with_existing_fleet_synthetic_state',
            'numeric_format': 'synthetic_ascii_nr3_9dp', 'source_reference': _SOURCE,
            'fleet_receipt': receipt, 'observation': observation})

    def _action(self, command, action, parameters=None):
        receipt = self._fleet.execute(self._request_id(), self._device_id, action, parameters)
        observation = self._observe()
        status = receipt['status']
        options = dict(status=status, receipt=receipt)
        if status not in ('ok', 'pending'):
            options.update(code='fleet_action_failed', error_source='existing_virtual_fleet')
        return self._reply(command, observation, **options)

    def advance(self, ticks=1):
        """Advance this same Fleet explicitly; no command advances virtual time."""
        receipt = self._fleet.advance(self._request_id(), ticks)
        return self._reply(None, self._observe(), status=receipt['status'], receipt=receipt)

    def command(self, command):
        """Return application envelopes, not a VISA/GPIB wire-server emulation."""
        observation = self._observe()
        text = command if type(command) is str and len(command) <= 256 else None

        def refuse(code, status='unsupported', source='session_parser', receipt=None, current=None):
            return self._reply(text, current or observation, status=status, code=code,
                               receipt=receipt, error_source=source)

        if (text is None or not text.strip(' ') or not text.isascii()
                or any(ord(char) < 32 or ord(char) == 127 for char in text)):
            return refuse('invalid_single_ascii_command', 'invalid')
        if ';' in text:
            return refuse('single_command_required', 'invalid')
        normalized = re.sub(r' +', ' ', text.strip(' ').upper())
        if normalized.startswith(':*'):
            return refuse('outside_n1911a_subset')
        if normalized.startswith(':'):
            normalized = normalized[1:]
        if observation['status'] == 'disconnected':
            return refuse('fleet_disconnected', 'disconnected', 'existing_virtual_fleet')
        values = observation['values']
        if type(values.get('operation_complete')) is not bool or type(values.get('configuration')) is not dict:
            return refuse('fleet_observation_unavailable', 'invalid', 'existing_virtual_fleet')

        if normalized == '*IDN?':
            return self._reply(text, observation, response='DGM Virtual,N1911A,SYNTHETIC,SIM-1')
        if normalized == '*OPC?':
            # Completion does not certify a current valid measurement/calibration.
            complete = values['operation_complete']
            return self._reply(text, observation, status='ok' if complete else 'pending',
                               response='1' if complete else None)

        match = _UNIT.fullmatch(normalized)
        if match:
            window, unit = int(match[1] or '1'), match[2]
            if window != values['configuration']['window']:
                return refuse('window_not_current')
            if unit is None:
                configured = values['configuration']['unit']
                if configured not in ('dBm', 'W'):
                    return refuse('unit_outside_subset')
                return self._reply(text, observation, response='DBM' if configured == 'dBm' else 'W')
            return self._action(text, 'set_display_unit', {'unit': 'dBm' if unit == 'DBM' else 'W'})

        match = _TRIGGER.fullmatch(normalized)
        if match:
            source = match[1]
            if source is None:
                configured = values['configuration']['trigger_source']
                if configured not in ('immediate', 'bus'):
                    return refuse('trigger_source_outside_subset')
                return self._reply(text, observation, response='IMM' if configured == 'immediate' else 'BUS')
            return self._action(text, 'configure', {'trigger_source': 'bus' if source == 'BUS' else 'immediate'})

        if re.fullmatch(r'INIT(?:IATE)?1?(?::IMM(?:EDIATE)?)?', normalized):
            return self._action(text, 'acquire')
        if re.fullmatch(r'ABOR(?:T)?1?', normalized):
            return self._action(text, 'abort')
        if normalized == '*TRG':
            return self._action(text, 'trigger')

        match = _FETCH.fullmatch(normalized)
        if match:
            window = int(match[1] or '1')
            if window != values['configuration']['window']:
                return refuse('window_not_current')
            receipt = self._fleet.execute(self._request_id(), self._device_id, 'fetch', {'window': window})
            current = self._observe()
            if receipt['status'] != 'ok':
                return self._reply(text, current, status=receipt['status'], code='fleet_fetch_unavailable',
                    receipt=receipt, error_source='existing_virtual_fleet')
            measurement = receipt['values']['outputs'].get('measurement')
            if (type(measurement) is not dict or measurement.get('valid') is not True
                    or measurement.get('status') != 'ok' or measurement.get('window') != window
                    or measurement.get('unit') not in ('dBm', 'W')
                    or type(measurement.get('value')) not in (int, float)
                    or not math.isfinite(measurement['value'])):
                return refuse('measurement_outside_subset', 'invalid', 'existing_virtual_fleet', receipt, current)
            if (current['status'] != 'ok' or current['values']['outputs'].get('measurement') != measurement
                    or measurement['acquisition_setup_revision'] != current['setup_revision']):
                return refuse('measurement_not_current', 'invalid', 'existing_virtual_fleet', receipt, current)
            return self._reply(text, current, response=f"{measurement['value']:+.9E}",
                               receipt=receipt, measurement=measurement)

        if re.fullmatch(r'SYST(?:EM)?:ERR(?:OR)?\?', normalized):
            receipt = self._fleet.execute(self._request_id(), self._device_id, 'read_error')
            current = self._observe()
            if 'error' not in receipt['values'] or receipt['status'] == 'disconnected':
                status = receipt['status'] if receipt['status'] in ('error', 'disconnected') else 'invalid'
                return refuse('fleet_error_query_unavailable', status,
                              'existing_virtual_fleet', receipt, current)
            reason = receipt['values']['error']
            error = {'source': 'existing_virtual_fleet', 'reason': reason,
                     'vendor_number': None if reason is not None else 0, 'consuming': True}
            return self._reply(text, current, response=None if reason is not None else '+0,"No error"',
                               receipt=receipt, error=error)
        return refuse('outside_n1911a_subset')
