"""Owned AOSP guest state controller joined to one existing synthetic RF Fleet.

The guest proves only reception and persistence of typed control state. All RF
propagation, sensor readings and analyzer readings remain VirtualFleet synthetic.
No native adb client, SDK discovery, OEM interface, physical radio or user shell.
"""

import base64
import hashlib
import math
from pathlib import Path
import re
import socket
import time
import uuid

from . import android_emulator_check as check
from .virtual_fleet.catalog import load_catalog
from .virtual_fleet.integration import create_conducted_example


SOURCE_SETTINGS = {'frequency_hz': 2.45e9, 'power_dbm': 12.5,
                   'bandwidth_hz': 20e6, 'duty_cycle': .25,
                   'modulation': 'OFDM', 'crest_factor_db': 3}
_SCRIPT_PATH = '/data/local/tmp/dgm-rf-v1.sh'
_CATALOG = Path(__file__).resolve().parents[1] / 'virtual_profiles/sm_a176u_unlicensed.json'
_HEX = re.compile(r'[0-9a-f]{64}')
_NONCE = re.compile(r'[0-9a-f]{32}')
_MODULATION = re.compile(r'[A-Z][A-Z0-9_-]{0,31}')
_SCRIPT = r'''#!/system/bin/sh
set -eu
[ "$#" -ge 3 ] || exit 64
op=$1; nonce=$2; seq=$3; shift 3
case "$nonce" in ''|*[!0-9a-f]*) exit 64;; esac
[ "${#nonce}" -eq 32 ] || exit 64
case "$seq" in ''|*[!0-9]*) exit 64;; esac
[ "$seq" -le 16 ] || exit 64
state_file=/data/local/tmp/dgm-rf-${nonce}.state
temp_file=/data/local/tmp/dgm-rf-${nonce}.tmp
[ ! -L "$state_file" ] && [ ! -L "$temp_file" ] || exit 65
hash_line() { value=$(printf '%s\n' "$1" | sha256sum); printf '%s' "${value%% *}"; }
reply() {
    prefix="DGM1|$nonce|$seq|$state|$revision|$source_hash"
    receipt=$(hash_line "$prefix")
    printf '%s|%s\n' "$prefix" "$receipt"
}
save() {
    printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
        "$revision" "$seq" "$state" "$source_hash" \
        "$freq" "$power" "$bandwidth" "$duty" "$modulation" "$crest" > "$temp_file"
    mv -f "$temp_file" "$state_file"
}
if [ "$op" = HELLO ]; then
    [ "$#" -eq 0 ] && [ "$seq" -eq 0 ] || exit 64
    state=HELLO; revision=0
    source_hash=$(sha256sum "$0"); source_hash=${source_hash%% *}
    reply
    exit 0
fi
if [ "$op" = CONFIG ]; then
    [ "$#" -eq 7 ] && [ "$seq" -eq 1 ] && [ ! -e "$state_file" ] || exit 65
    freq=$1; power=$2; bandwidth=$3; duty=$4; modulation=$5; crest=$6
    source_hash=$7
    actual=$(hash_line "$freq|$power|$bandwidth|$duty|$modulation|$crest")
    [ "$actual" = "$source_hash" ] || exit 65
    state=CONFIGURED; revision=1
    save; reply
    exit 0
fi
[ "$#" -eq 0 ] && [ -f "$state_file" ] || exit 65
IFS='|' read -r revision previous state source_hash freq power bandwidth duty modulation crest < "$state_file"
[ "$seq" -eq "$((previous + 1))" ] || exit 65
actual=$(hash_line "$freq|$power|$bandwidth|$duty|$modulation|$crest")
[ "$actual" = "$source_hash" ] || exit 65
case "$op" in
    START) [ "$state" = CONFIGURED ] || exit 65; state=STARTED; revision=$((revision + 1));;
    STOP) [ "$state" = STARTED ] || exit 65; state=STOPPED; revision=$((revision + 1));;
    STATUS) :;;
    *) exit 64;;
esac
save; reply
'''
_SCRIPT_BYTES = _SCRIPT.encode('ascii')
_SCRIPT_SHA256 = hashlib.sha256(_SCRIPT_BYTES).hexdigest()


def _source_tokens(source):
    keys = ('frequency_hz', 'power_dbm', 'bandwidth_hz', 'duty_cycle',
            'modulation', 'crest_factor_db')
    if type(source) is not dict or set(source) != set(keys):
        raise check.BoundaryError('source_six_required')
    numbers = {}
    for key in keys:
        if key == 'modulation':
            continue
        value = source[key]
        if type(value) not in (int, float):
            raise check.BoundaryError('source_number_invalid', key)
        try:
            if not math.isfinite(value):
                raise check.BoundaryError('source_number_invalid', key)
        except OverflowError as exc:
            raise check.BoundaryError('source_number_invalid', key) from exc
        numbers[key] = float(value)
    if (numbers['frequency_hz'] <= 0 or numbers['bandwidth_hz'] <= 0
            or numbers['frequency_hz'] - numbers['bandwidth_hz'] / 2 < 0
            or not 0 < numbers['duty_cycle'] <= 1
            or numbers['crest_factor_db'] < 0
            or not math.isfinite(numbers['frequency_hz'] + numbers['bandwidth_hz'] / 2)):
        raise check.BoundaryError('source_range_invalid')
    if type(source['modulation']) is not str or _MODULATION.fullmatch(source['modulation']) is None:
        raise check.BoundaryError('source_modulation_invalid')
    return tuple(source[key] if key == 'modulation' else format(numbers[key], '.17g') for key in keys)


def source_sha256(source):
    """Hash six canonical ASCII fields as actually sent to the guest."""
    return hashlib.sha256(('|'.join(_source_tokens(source)) + '\n').encode('ascii')).hexdigest()


def _owned_identity(report, endpoint, server):
    identity = report.data.get('identity', {})
    if type(identity) is not dict:
        raise check.BoundaryError('guest_identity_required')
    props = identity.get('properties', {})
    if (report.data.get('android_os') != 'booted' or report.data.get('adb_verified') is not True
            or identity.get('serial') != endpoint.serial or identity.get('state') != 'device'
            or props.get('ro.kernel.qemu') != '1'
            or props.get('ro.hardware') not in ('ranchu', 'goldfish')
            or not props.get('ro.product.model') or props.get('sys.boot_completed') != '1'):
        raise check.BoundaryError('guest_identity_required')
    if server.process.poll() is not None:
        raise check.BoundaryError('owned_adb_server_exited')


def _exchange(endpoint, server, service, deadline):
    """One fixed shell request on the owned loopback server and exact serial."""
    if (type(service) is not str or not service.startswith('shell:') or not service.isascii()
            or len(service) > 16384 or any(ord(char) < 32 or ord(char) == 127 for char in service)):
        raise check.BoundaryError('guest_service_invalid')
    code = server.process.poll()
    if code is not None:
        raise check.BoundaryError('owned_adb_server_exited', f'pid={server.process.pid} exit_code={code}')
    deadline = min(deadline, time.monotonic() + 5)
    try:
        with socket.create_connection(('127.0.0.1', endpoint.adb_port),
                                      timeout=check.remaining(deadline)) as stream:
            for item in (f'host:transport:{endpoint.serial}', service):
                payload = item.encode('ascii')
                stream.settimeout(check.remaining(deadline))
                stream.sendall(f'{len(payload):04x}'.encode('ascii') + payload)
                status = check._receive(stream, 4, deadline)
                if status == b'FAIL':
                    size = int(check._receive(stream, 4, deadline), 16)
                    if size > 4096:
                        raise check.BoundaryError('guest_fail_limit')
                    reason = check._receive(stream, size, deadline).decode('utf-8', 'replace')
                    raise check.BoundaryError('guest_adb_service_failure', reason)
                if status != b'OKAY':
                    raise check.BoundaryError('guest_adb_invalid_status', repr(status))
            raw = bytearray()
            while len(raw) < 4096:
                stream.settimeout(check.remaining(deadline))
                block = stream.recv(min(1024, 4096 - len(raw)))
                check.remaining(deadline)
                if not block:
                    break
                raw.extend(block)
            else:
                raise check.BoundaryError('guest_response_limit')
            if not raw or any(byte > 127 or byte < 9 or 13 < byte < 32 for byte in raw):
                raise check.BoundaryError('guest_response_invalid')
            result = raw.decode('ascii').strip()
            if server.process.poll() is not None:
                raise check.BoundaryError('owned_adb_server_exited')
            return result
    except (OSError, ValueError) as exc:
        code = server.process.poll()
        if code is not None:
            raise check.BoundaryError('owned_adb_server_exited',
                                      f'pid={server.process.pid} exit_code={code}') from exc
        if isinstance(exc, TimeoutError):
            raise check.BoundaryError('adb_timeout') from exc
        raise check.BoundaryError('guest_adb_wire_error', str(exc)) from exc


def _receipt(raw, *, nonce, sequence, state, revision, source_hash):
    if type(raw) is not str or len(raw) > 256 or not raw.isascii():
        raise check.BoundaryError('guest_receipt_mismatch')
    parts = raw.split('|')
    if (len(parts) != 7 or parts[:6] != ['DGM1', nonce, str(sequence), state,
                                        str(revision), source_hash]
            or _HEX.fullmatch(parts[6]) is None):
        raise check.BoundaryError('guest_receipt_mismatch', raw[:256])
    expected = hashlib.sha256(('|'.join(parts[:6]) + '\n').encode('ascii')).hexdigest()
    if parts[6] != expected:
        raise check.BoundaryError('guest_receipt_mismatch', raw[:256])
    return {'raw': raw, 'sequence': sequence, 'state': state, 'revision': revision,
            'source_sha256': source_hash, 'receipt_sha256': parts[6]}


def _install_service():
    encoded = base64.b64encode(_SCRIPT_BYTES).decode('ascii')
    return ('shell:test ! -e ' + _SCRIPT_PATH + ' && test ! -L ' + _SCRIPT_PATH
            + ' && printf %s ' + encoded
            + ' | base64 -d > ' + _SCRIPT_PATH + ' && sha256sum ' + _SCRIPT_PATH)


def _command_service(operation, nonce, sequence, source_tokens=(), source_hash=None):
    if operation not in ('HELLO', 'CONFIG', 'START', 'STOP', 'STATUS') or _NONCE.fullmatch(nonce) is None:
        raise check.BoundaryError('guest_command_invalid')
    if type(sequence) is not int or not 0 <= sequence <= 16:
        raise check.BoundaryError('guest_sequence_invalid')
    if operation == 'CONFIG':
        if (type(source_tokens) is not tuple or len(source_tokens) != 6
                or any(type(item) is not str for item in source_tokens)
                or type(source_hash) is not str or _HEX.fullmatch(source_hash) is None):
            raise check.BoundaryError('guest_command_invalid')
        try:
            candidate = dict(zip(('frequency_hz', 'power_dbm', 'bandwidth_hz',
                                  'duty_cycle', 'modulation', 'crest_factor_db'),
                                 (float(source_tokens[0]), float(source_tokens[1]),
                                  float(source_tokens[2]), float(source_tokens[3]),
                                  source_tokens[4], float(source_tokens[5]))))
        except ValueError as exc:
            raise check.BoundaryError('guest_command_invalid') from exc
        if _source_tokens(candidate) != source_tokens or source_sha256(candidate) != source_hash:
            raise check.BoundaryError('guest_command_invalid')
    elif source_tokens != () or source_hash is not None:
        raise check.BoundaryError('guest_command_invalid')
    tail = (' ' + ' '.join(source_tokens) + ' ' + source_hash) if operation == 'CONFIG' else ''
    return f'shell:sh {_SCRIPT_PATH} {operation} {nonce} {sequence}{tail}'


def _cleanup_service(nonce):
    if _NONCE.fullmatch(nonce) is None:
        raise check.BoundaryError('guest_nonce_invalid')
    state = f'/data/local/tmp/dgm-rf-{nonce}.state'
    temporary = f'/data/local/tmp/dgm-rf-{nonce}.tmp'
    return (f'shell:rm -f {_SCRIPT_PATH} {state} {temporary} && '
            f'test ! -e {_SCRIPT_PATH} && test ! -e {state} && '
            f'test ! -e {temporary} && printf DGM-CLEAN-OK')


def _fleet_action(fleet, result, request, device, action, parameters=None):
    response = fleet.execute('guest-rf:' + request, device, action, parameters)
    result['host_rf_model']['action_receipts'].append(response)
    if response['status'] not in ('ok', 'pending'):
        raise check.BoundaryError('fleet_action_failed', f'{device}:{action}:{response["status"]}')
    return response


def _measurement(receipt, device, revision, after_tick):
    value = receipt.get('values', {}).get('outputs', {}).get('measurement')
    if (receipt['status'] != 'ok' or type(value) is not dict or value.get('valid') is not True
            or value.get('status') != 'ok' or value.get('unit') != 'dBm'
            or type(value.get('value')) not in (int, float) or not math.isfinite(value['value'])
            or value.get('source_id') != device or value.get('acquisition_setup_revision') != revision
            or type(value.get('acquisition_tick')) is not int or value['acquisition_tick'] <= after_tick):
        raise check.BoundaryError('fleet_measurement_not_fresh', device)
    return value


def run_guest_rf_check(endpoint, server, report, *, deadline, emulator_process):
    """Run one fixed guest control lifecycle and one same-Fleet RF observation."""
    _owned_identity(report, endpoint, server)
    source = dict(SOURCE_SETTINGS)
    tokens = _source_tokens(source)
    source_hash = source_sha256(source)
    nonce = uuid.uuid4().hex
    result = {'schema_version': 1, 'valid': False,
              'guest_controller': {'kind': 'aosp_shell_state_controller', 'nonce': nonce,
                                   'script_sha256': _SCRIPT_SHA256, 'receipts': [],
                                   'states': [], 'cleanup': 'not_attempted'},
              'host_rf_model': {'synthetic': True, 'physical_verified': False,
                                'seed': 13, 'source_settings': source,
                                'source_sha256': source_hash, 'action_receipts': []},
              'first_error': None, 'cleanup_errors': [], 'oem_rf': 'not_assessed',
              'physical_rf': 'not_assessed'}
    report.data['rf_bridge'] = result
    report.data['rf_model'] = 'synthetic_guest_bridge_attempted'
    report.save()
    fleet = None
    failure = None

    def guard_owned():
        if server.process.poll() is not None:
            raise check.BoundaryError('owned_adb_server_exited')
        if emulator_process.process.poll() is not None:
            raise check.BoundaryError('emulator_exited')
        server.sample()
        emulator_process.sample()
        if check.resources()['available_mib'] < 512:
            raise check.BoundaryError('memory_emergency_stop')
        check.remaining(deadline, 'guest_bridge_timeout')

    def guest(operation, sequence, state, revision, *, config=False):
        guard_owned()
        service = _command_service(operation, nonce, sequence, tokens if config else (),
                                   source_hash if config else None)
        raw = _exchange(endpoint, server, service, deadline)
        parsed = _receipt(raw, nonce=nonce, sequence=sequence, state=state,
                          revision=revision,
                          source_hash=_SCRIPT_SHA256 if operation == 'HELLO' else source_hash)
        result['guest_controller']['receipts'].append(dict(operation=operation, **parsed))
        if operation != 'HELLO':
            result['guest_controller']['states'].append(state)
        report.save()

    try:
        catalog = load_catalog(_CATALOG)
        fleet, _, setup = create_conducted_example(catalog, seed=13,
                                                    source_settings=dict(source))
        result['host_rf_model']['setup_receipts'] = setup
        _fleet_action(fleet, result, 'initial-stop', 'dut', 'stop')
        guard_owned()
        installed = _exchange(endpoint, server, _install_service(), deadline)
        if installed != _SCRIPT_SHA256 + '  ' + _SCRIPT_PATH:
            raise check.BoundaryError('guest_script_hash_mismatch', installed[:256])
        result['guest_controller']['install_sha256'] = _SCRIPT_SHA256
        guest('HELLO', 0, 'HELLO', 0)
        guest('CONFIG', 1, 'CONFIGURED', 1, config=True)
        guest('STATUS', 2, 'CONFIGURED', 1)
        _fleet_action(fleet, result, 'configure', 'dut', 'configure', dict(source))
        guest('START', 3, 'STARTED', 2)
        guest('STATUS', 4, 'STARTED', 2)
        started = _fleet_action(fleet, result, 'start', 'dut', 'start')
        start_tick = started['tick']
        fleet.advance('guest-rf:startup', 3)
        guard_owned()
        output = fleet.observations()['devices']['dut']['values']['outputs'].get('rf')
        if (type(output) is not dict or output.get('valid') is not True
                or output.get('source_id') != 'dut'
                or any(output.get(key) != source[key] for key in source)):
            raise check.BoundaryError('fleet_dut_output_not_current')
        result['host_rf_model']['dut_output'] = output
        _fleet_action(fleet, result, 'sensor-acquire', 'sensor', 'acquire')
        _fleet_action(fleet, result, 'analyzer-acquire', 'analyzer', 'acquire')
        fleet.advance('guest-rf:measurement', 3)
        guard_owned()
        revision = fleet.observations()['setup_revision']
        sensor = _fleet_action(fleet, result, 'sensor-read', 'sensor', 'read')
        analyzer = _fleet_action(fleet, result, 'analyzer-fetch', 'analyzer', 'fetch')
        sensor_value = _measurement(sensor, 'sensor', revision, start_tick)
        analyzer_value = _measurement(analyzer, 'analyzer', revision, start_tick)
        if analyzer_value.get('quantity') != 'on_average':
            raise check.BoundaryError('fleet_analyzer_quantity_mismatch')
        _fleet_action(fleet, result, 'meter-acquire', 'meter', 'acquire')
        fleet.advance('guest-rf:meter', 2)
        guard_owned()
        meter = _fleet_action(fleet, result, 'meter-fetch', 'meter', 'fetch')
        meter_value = _measurement(meter, 'meter', revision, start_tick)
        if meter_value.get('quantity') != 'time_average':
            raise check.BoundaryError('fleet_meter_quantity_mismatch')
        result['host_rf_model'].update(sensor_on_average=sensor_value,
                                       analyzer_on_average=analyzer_value,
                                       meter_time_average=meter_value)
        guest('STOP', 5, 'STOPPED', 3)
        guest('STATUS', 6, 'STOPPED', 3)
        _fleet_action(fleet, result, 'stop', 'dut', 'stop')
        after_sensor = fleet.execute('guest-rf:after-stop-sensor', 'sensor', 'read')
        after_analyzer = fleet.execute('guest-rf:after-stop-analyzer', 'analyzer', 'fetch')
        result['host_rf_model'].update(after_stop_sensor_status=after_sensor['status'],
                                       after_stop_analyzer_status=after_analyzer['status'],
                                       stop_observations=[after_sensor, after_analyzer])
        if after_sensor['status'] == 'ok' or after_analyzer['status'] == 'ok':
            raise check.BoundaryError('fleet_stop_not_invalidated')
    except BaseException as exc:
        failure = exc
        result['first_error'] = {'code': getattr(exc, 'code', 'unexpected_error'), 'detail': str(exc)}
        result['guest_controller']['uncertain_after'] = result['guest_controller']['receipts'][-1]['operation'] if result['guest_controller']['receipts'] else 'install'
        result['guest_controller']['control_state_after_failure'] = 'unknown_until_owned_emulator_cleanup'
        if fleet is not None:
            try:
                stopped = fleet.execute('guest-rf:failure-stop', 'dut', 'stop')
                result['host_rf_model']['fleet_stop'] = stopped
            except Exception as stop_exc:
                result['cleanup_errors'].append({'code': 'fleet_stop_error', 'detail': repr(stop_exc)})
    finally:
        try:
            if getattr(failure, 'code', None) == 'memory_emergency_stop':
                raise check.BoundaryError('cleanup_skipped_memory_emergency')
            cleaned = _exchange(endpoint, server, _cleanup_service(nonce), deadline)
            if cleaned != 'DGM-CLEAN-OK':
                raise check.BoundaryError('guest_cleanup_unconfirmed', cleaned[:256])
            result['guest_controller']['cleanup'] = 'confirmed'
        except BaseException as cleanup_exc:
            result['guest_controller']['cleanup'] = 'unknown'
            result['cleanup_errors'].append({'code': getattr(cleanup_exc, 'code', 'guest_cleanup_error'),
                                             'detail': str(cleanup_exc)})
            if failure is None:
                failure = (cleanup_exc if isinstance(cleanup_exc, KeyboardInterrupt)
                           else check.BoundaryError('guest_cleanup_unknown'))
                result['first_error'] = {'code': 'interrupted' if isinstance(failure, KeyboardInterrupt)
                                         else failure.code, 'detail': str(failure)}
        result['valid'] = failure is None and result['guest_controller']['cleanup'] == 'confirmed'
        report.data['rf_model'] = ('synthetic_guest_bridge_verified' if result['valid']
                                   else 'synthetic_guest_bridge_invalid')
        report.save()
    if failure is not None:
        raise failure
    return result
