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
from .intake_conducted_twin_plan import build_conducted_twin_plan_input
from .store import canonical
from .virtual_fleet.catalog import load_catalog
from .virtual_fleet.conducted_measurement_selector import select_conducted_measurement
from .virtual_fleet.harness import FleetHarness
from .virtual_fleet.integration import (create_conducted_example, get_role_actions,
                                       _begin_setup_record, _finish_setup_record)
from .virtual_fleet.journal import OperatorJournal, read_operator_journal


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
umask 077
[ "$#" -ge 3 ] || exit 64
op=$1; nonce=$2; seq=$3; shift 3
case "$nonce" in ''|*[!0-9a-f]*) exit 64;; esac
[ "${#nonce}" -eq 32 ] || exit 64
case "$seq" in ''|*[!0-9]*) exit 64;; esac
[ "$seq" -le 16 ] || exit 64
scope=/data/local/tmp/dgm-rf-${nonce}.d
state_file=$scope/state
temp_file=$scope/tmp
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
    [ "$#" -eq 7 ] && [ "$seq" -eq 1 ] || exit 65
    freq=$1; power=$2; bandwidth=$3; duty=$4; modulation=$5; crest=$6
    source_hash=$7
    actual=$(hash_line "$freq|$power|$bandwidth|$duty|$modulation|$crest")
    [ "$actual" = "$source_hash" ] || exit 65
    mkdir "$scope" || exit 65
    state=CONFIGURED; revision=1
    save; reply
    exit 0
fi
[ "$#" -eq 0 ] && [ -d "$scope" ] && [ ! -L "$scope" ] && [ -f "$state_file" ] || exit 65
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


def _cleanup_service(nonce, *, state_owned=False):
    if _NONCE.fullmatch(nonce) is None:
        raise check.BoundaryError('guest_nonce_invalid')
    if type(state_owned) is not bool:
        raise check.BoundaryError('guest_cleanup_scope_invalid')
    if not state_owned:
        return (f'shell:rm -f {_SCRIPT_PATH} && test ! -e {_SCRIPT_PATH} && '
                'printf DGM-CLEAN-OK')
    scope = f'/data/local/tmp/dgm-rf-{nonce}.d'
    state, temporary = f'{scope}/state', f'{scope}/tmp'
    return (f'shell:test -d {scope} && test ! -L {scope} && '
            f'rm -f {_SCRIPT_PATH} {state} {temporary} && rmdir {scope} && '
            f'test ! -e {_SCRIPT_PATH} && test ! -e {scope} && printf DGM-CLEAN-OK')


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


def _snapshot_sha256(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _first_on_result(trace):
    plan = trace['plan_input']['plan']
    supported = (plan['method_id'] == 'conducted_synthetic' and plan['method_version'] == 1
                 and plan['metric'] == 'on' and plan['reference_plane'] == 'source_output')
    return dict(schema_version=1, kind='owned_guest_first_on_measurement',
        source_kind='owned_guest_fleet_harness', status='incomplete' if supported else 'unsupported',
        metric=plan['metric'], reference_plane=plan['reference_plane'],
        storage_status='not_run', artifact_created=False,
        binding=dict(source_sha256=trace['source_sha256'], plan_input_sha256=trace['plan_input_sha256']),
        setup_snapshot=[], journal_file=None, journal_read=None, run_report=None,
        acquisition_receipt=None, current_after_stop=None, selection=None, result=None,
        first_failure=None, secondary_errors=[],
        verification=dict(synthetic=True, ai_model_called=False, hardware_verified=False,
                          physical_verified=False, execution_authority=False,
                          assessment='not_assessed', identity_scope='local_provenance_only'))


class _FirstOnFleet:
    """Record actual setup calls, then dispatch every same-Fleet effect via Harness.

    The queued policy describes the existing local procedure. It is never an AI
    execution, a report reconstruction, or a physical measurement authority.
    """
    policy_id = 'owned_guest_first_on_local_v1'

    def __init__(self, fleet, catalog, topology, records, trace, result, report, deadline):
        self.fleet, self.catalog, self.topology = fleet, catalog, topology
        self.records, self.trace, self.output = records, trace, result['first_on_measurement']
        self.output['setup_snapshot'] = records
        self.path = report.output / 'first-on.jsonl'
        self.deadline = deadline
        self.run_id, self.instance_id = 'guest-rf:'+uuid.uuid4().hex, 'fleet:'+uuid.uuid4().hex
        self.output['binding'].update(run_id=self.run_id, runtime_instance_id=self.instance_id,
            guest_nonce=result['guest_controller']['nonce'], script_sha256=_SCRIPT_SHA256)
        self.harness = self.journal = None
        self.setup_closed = False
        self.proposal = self.last_receipt = None
        self.receipt_count = 0
        self.control_error = None

    def __call__(self, context):
        if self.proposal is None:
            raise ValueError('no local procedure decision')
        return self.proposal

    def _sink(self, event):
        self.journal(event)
        if event['type'] == 'receipt':
            self.last_receipt = event['payload']['result']
            self.receipt_count += 1

    def begin(self):
        self.setup_closed = True
        provenance = dict(runtime_origin='preinitialized', catalog_sha256=_snapshot_sha256(self.catalog),
            topology_sha256=_snapshot_sha256(self.topology), topology=self.topology,
            engine_sha256=hashlib.sha256((Path(__file__).parent / 'virtual_fleet/rf.py').read_bytes()).hexdigest(),
            plan_binding=self.trace['plan_input']['binding'], setup_sha256=_snapshot_sha256(self.records),
            source_sha256=self.trace['source_sha256'],
            guest_nonce=self.output['binding']['guest_nonce'], script_sha256=_SCRIPT_SHA256,
            quantity=dict(metric='on', reference_plane='sensor_input',
                          loss_compensation_applied=False, loss_compensation_sign=1))
        check.reject_links(self.path)
        self.provenance = _plan_snapshot(provenance)
        self.journal = OperatorJournal(self.path, run_id=self.run_id,
                                      runtime_instance_id=self.instance_id, provenance=_plan_snapshot(provenance))
        self.output['journal_file'] = self.path.name
        self.harness = FleetHarness(self.fleet, self, goal=dict(kind='owned_guest_first_on_local_procedure'),
            catalog=self.catalog, topology=self.topology, role_actions=get_role_actions(),
            budgets=dict(wall_seconds=min(30, check.remaining(self.deadline, 'guest_bridge_timeout'))),
            event_sink=self._sink, run_id=self.run_id, runtime_instance_id=self.instance_id)

    def _step(self, proposal):
        if self.harness is None:
            raise check.BoundaryError('guest_first_on_recorder_unavailable')
        self.proposal = proposal
        try:
            return self.harness.step()
        finally:
            self.proposal = None

    def _dispatch(self, proposal):
        before = self.receipt_count
        state = self._step(proposal)
        if state['state'] != 'running' or self.receipt_count != before + 1:
            raise check.BoundaryError('guest_first_on_runtime_incomplete')
        return self.last_receipt

    def execute(self, request, device, action, parameters=None):
        if not self.setup_closed:
            row = _begin_setup_record(self.records, request, 'execute', device, action, parameters)
            response = self.fleet.execute(request, device, action, parameters)
            _finish_setup_record(row, response)
            return response
        return self._dispatch(dict(kind='execute', device_id=device, action=action,
                                   parameters={} if parameters is None else parameters))

    def advance(self, request, ticks):
        # Harness's public advance proposal is one tick. Return the last actual
        # receipt, never an invented receipt aggregating several real calls.
        response = None
        for _ in range(ticks):
            response = self._dispatch(dict(kind='advance', ticks=1))
        return response

    def observations(self):
        return self.fleet.observations()

    def _secondary(self, phase, exc):
        failure = dict(phase=phase, code='guest_first_on_'+phase+'_failed', error_type=type(exc).__name__)
        self.output['secondary_errors'].append(failure)
        if self.output['first_failure'] is None:
            self.output['first_failure'] = failure
        if isinstance(exc, (KeyboardInterrupt, SystemExit)) and self.control_error is None:
            self.control_error = exc

    def finish(self, completed, result):
        """Preserve actual termination/journal, then reuse the original selector."""
        stops = result['host_rf_model'].get('stop_observations')
        if stops is not None:
            self.output['current_after_stop'] = dict(sensor=stops[0], analyzer=stops[1])
        try:
            if self.harness is not None:
                if completed:
                    self._step(dict(kind='stop', claim='completed',
                                    reason='owned guest local procedure STOP and cleanup confirmed'))
                else:
                    self.harness.stop()
                    self.harness.step()
                self.output['run_report'] = self.harness.result()
        except BaseException as exc:
            self._secondary('termination', exc)
        finally:
            if self.journal is not None:
                try:
                    self.journal.close()
                except BaseException as exc:
                    self._secondary('journal_close', exc)
        if self.output['journal_file'] is None:
            return
        try:
            stored = read_operator_journal(self.path)
            self.output['journal_read'] = stored
        except BaseException as exc:
            self._secondary('journal_read', exc)
            return
        # These are the new source-kind bindings. The original parent owns its
        # existing plan/setup/packet checks, but cannot know this live bridge's
        # allocated IDs or guest source-SHA provenance.
        header = stored['header']
        if (header['run_id'] != self.run_id or header['runtime_instance_id'] != self.instance_id
                or canonical(header['provenance']) != canonical(self.provenance)):
            self.output['status'] = 'invalid'
            self._secondary('binding', ValueError('local provenance mismatch'))
            return
        try:
            selected = select_conducted_measurement(self.trace['plan_input'], self.records,
                                                   stored, self.output['run_report'])
            self.output['selection'] = selected
            native = selected['result']
            if (completed and not self.output['secondary_errors'] and selected['status'] == 'selected'
                    and native is not None and native['status'] == 'recorded'):
                candidate = selected['candidate']
                receipt = next(e for e in stored['events'] if e['event_id'] == candidate['receipt_ref'])
                self.output['acquisition_receipt'] = receipt['payload']['result']
                packet = native['raw_measurement']['packet']
                self.output['binding'].update(request_id=selected['request_id'],
                    receipt_ref=candidate['receipt_ref'], measurement_ref=selected['measurement_ref'],
                    acquisition_tick=packet['acquisition_tick'], setup_revision=packet['acquisition_setup_revision'])
                self.output.update(status='recorded', result=native)
            else:
                self.output['status'] = 'invalid' if native is not None and native['status'] == 'invalid' else 'incomplete'
                if selected['status'] != 'selected' and self.output['first_failure'] is None:
                    failure = (native.get('failure') if native is not None else None) or selected['reasons'][0]
                    phase = 'calculation' if failure.get('field') == 'calculation' else 'selection'
                    self.output['first_failure'] = dict(phase=phase, **failure)
        except BaseException as exc:
            self.output['status'] = 'incomplete'
            self.output['result'] = None
            self._secondary('selection', exc)


def run_guest_rf_check(endpoint, server, report, *, deadline, emulator_process,
                       source_settings=None, measurement_bundle=None):
    """Run owned guest control and same-Fleet RF using one detached exact-six input.

    None retains the original fixed diagnostic. A caller declaration is synthetic
    input only; it does not authenticate intake evidence or grant an OS boot.
    """
    check._require_rf_bridge_endpoint(endpoint)
    _owned_identity(report, endpoint, server)
    if source_settings is not None and type(source_settings) is not dict:
        raise check.BoundaryError('source_six_required')
    source = dict(SOURCE_SETTINGS if source_settings is None else source_settings)
    tokens = _source_tokens(source)
    source_hash = source_sha256(source)
    trace = None if measurement_bundle is None else validate_intake_plan_bundle(measurement_bundle)
    if trace is not None and (trace['source_settings'] != source or trace['source_sha256'] != source_hash):
        raise check.BoundaryError('guest_plan_source_mismatch')
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
    if trace is not None:
        result['first_on_measurement'] = _first_on_result(trace)
    report.data['rf_bridge'] = result
    report.data['rf_model'] = 'synthetic_guest_bridge_attempted'
    report.save()
    fleet = None
    recorder = None
    failure = None
    install_attempted = False
    install_confirmed = False
    config_attempted = False
    config_confirmed = False

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
        kwargs = dict(seed=13, source_settings=dict(source))
        if trace is not None and result['first_on_measurement']['status'] != 'unsupported':
            kwargs['setup_records'] = []
        fleet, topology, setup = create_conducted_example(catalog, **kwargs)
        if 'setup_records' in kwargs:
            recorder = _FirstOnFleet(fleet, catalog, topology, kwargs['setup_records'],
                                     trace, result, report, deadline)
            fleet = recorder
        result['host_rf_model']['setup_receipts'] = setup
        _fleet_action(fleet, result, 'initial-stop', 'dut', 'stop')
        guard_owned()
        install_attempted = True
        installed = _exchange(endpoint, server, _install_service(), deadline)
        if installed != _SCRIPT_SHA256 + '  ' + _SCRIPT_PATH:
            raise check.BoundaryError('guest_script_hash_mismatch', installed[:256])
        install_confirmed = True
        result['guest_controller']['install_sha256'] = _SCRIPT_SHA256
        guest('HELLO', 0, 'HELLO', 0)
        config_attempted = True
        guest('CONFIG', 1, 'CONFIGURED', 1, config=True)
        config_confirmed = True
        guest('STATUS', 2, 'CONFIGURED', 1)
        _fleet_action(fleet, result, 'configure', 'dut', 'configure', dict(source))
        if recorder is not None:
            _fleet_action(fleet, result, 'sensor-triggered', 'sensor', 'configure',
                          dict(calibration_valid=True, acquisition_policy='triggered'))
            _fleet_action(fleet, result, 'setup-stop', 'dut', 'stop')
            recorder.begin()
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
        if install_confirmed:
            try:
                if getattr(failure, 'code', None) == 'memory_emergency_stop':
                    raise check.BoundaryError('cleanup_skipped_memory_emergency')
                cleaned = _exchange(endpoint, server, _cleanup_service(
                    nonce, state_owned=config_confirmed), deadline)
                if cleaned != 'DGM-CLEAN-OK':
                    raise check.BoundaryError('guest_cleanup_unconfirmed', cleaned[:256])
                result['guest_controller']['cleanup'] = ('unknown' if config_attempted
                                                        and not config_confirmed else 'confirmed')
                if result['guest_controller']['cleanup'] == 'unknown':
                    result['cleanup_errors'].append({'code': 'guest_state_effect_unknown',
                                                     'detail': 'CONFIG was not receipt-confirmed; nonce scope left intact'})
            except BaseException as cleanup_exc:
                result['guest_controller']['cleanup'] = 'unknown'
                result['cleanup_errors'].append({'code': getattr(cleanup_exc, 'code', 'guest_cleanup_error'),
                                                 'detail': str(cleanup_exc)})
                if failure is None:
                    failure = (cleanup_exc if isinstance(cleanup_exc, KeyboardInterrupt)
                               else check.BoundaryError('guest_cleanup_unknown'))
                    result['first_error'] = {'code': 'interrupted' if isinstance(failure, KeyboardInterrupt)
                                             else failure.code, 'detail': str(failure)}
        elif install_attempted:
            result['guest_controller']['cleanup'] = 'unknown'
            result['cleanup_errors'].append({'code': 'guest_install_effect_unknown',
                                             'detail': 'Install was not hash-confirmed; guest deletion skipped'})
        elif getattr(failure, 'code', None) == 'memory_emergency_stop':
            result['guest_controller']['cleanup'] = 'unknown'
        result['valid'] = failure is None and result['guest_controller']['cleanup'] == 'confirmed'
        if recorder is not None:
            recorder.finish(result['valid'], result)
            if failure is None and recorder.control_error is not None:
                failure = recorder.control_error
                result['valid'] = False
                result['first_error'] = dict(code='interrupted', detail=type(failure).__name__)
        report.data['rf_model'] = ('synthetic_guest_bridge_verified' if result['valid']
                                   else 'synthetic_guest_bridge_invalid')
        report.save()
    if failure is not None:
        raise failure
    return result


def _plan_snapshot(value):
    """Detach bounded native JSON data before checking or executing a plan."""
    ancestors, nodes = set(), 0
    def copy(item, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 100000 or depth > 32:
            raise ValueError('input_limit')
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        if type(item) not in (dict, list) or id(item) in ancestors:
            raise ValueError('native_input_required')
        ancestors.add(id(item))
        try:
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError('native_keys_required')
                return {key: copy(child, depth+1) for key, child in item.items()}
            return [copy(child, depth+1) for child in item]
        finally:
            ancestors.remove(id(item))
    try:
        detached = copy(value)
        if len(canonical(detached).encode('utf-8')) > 8*1024*1024:
            raise ValueError('input_limit')
        return detached
    except MemoryError:
        raise
    except Exception as exc:
        raise check.BoundaryError('guest_plan_input_invalid') from exc


def validate_intake_plan_bundle(bundle):
    """Pure shared validation; detached caller evidence is never an execution grant."""
    bundle = _plan_snapshot(bundle)
    fields = {'context', 'analysis', 'plan_input', 'expected_revision',
              'expected_context_sha256', 'expected_plan_input_sha256'}
    if type(bundle) is not dict or set(bundle) != fields:
        raise check.BoundaryError('guest_plan_input_invalid')
    context, analysis, supplied = (bundle[key] for key in ('context', 'analysis', 'plan_input'))
    revision, context_hash, plan_hash = (bundle[key] for key in
        ('expected_revision', 'expected_context_sha256', 'expected_plan_input_sha256'))
    if type(context) is not dict or context.get('synthetic') is not True:
        raise check.BoundaryError('guest_plan_non_synthetic')
    if (type(plan_hash) is not str or _HEX.fullmatch(plan_hash) is None
            or hashlib.sha256(canonical(supplied).encode('utf-8')).hexdigest() != plan_hash):
        raise check.BoundaryError('guest_plan_binding_mismatch')
    if type(supplied) is not dict or type(supplied.get('plan')) is not dict:
        raise check.BoundaryError('guest_plan_input_invalid')
    plan = supplied['plan']
    rebuilt = build_conducted_twin_plan_input(context, analysis,
        expected_revision=revision, expected_context_sha256=context_hash,
        source_settings=plan.get('source_settings'), basis=plan.get('basis_refs'),
        method={key: plan.get(key) for key in ('method_id', 'method_version', 'metric', 'reference_plane')})
    if rebuilt['status'] != 'ready_for_simulation' or canonical(rebuilt) != canonical(supplied):
        raise check.BoundaryError('guest_plan_revalidation_failed')
    source = dict(rebuilt['plan']['source_settings'])
    source_hash = source_sha256(source)
    return dict(plan_input=rebuilt, plan_input_sha256=plan_hash,
                source_settings=dict(source), source_sha256=source_hash,
                verification=dict(rebuilt['verification']))


def run_intake_plan_guest_rf_check(context, analysis, plan_input, endpoint, server, report, *,
        expected_revision, expected_context_sha256, expected_plan_input_sha256,
        deadline, emulator_process):
    """Revalidate caller snapshots and use the already-owned guest/Fleet lifecycle.

    Store current state and source bytes remain caller-only. This wrapper and
    runtime bundle preparation share one pure validation algorithm.
    """
    check._require_rf_bridge_endpoint(endpoint)
    bundle = _plan_snapshot(dict(context=context, analysis=analysis, plan_input=plan_input,
        expected_revision=expected_revision, expected_context_sha256=expected_context_sha256,
        expected_plan_input_sha256=expected_plan_input_sha256))
    trace = validate_intake_plan_bundle(bundle)
    # Save before guest I/O, so the original lifecycle failure still has its
    # caller-only plan lineage without a new finally/save masking that error.
    report.data['intake_plan'] = _plan_snapshot(trace)
    report.save()
    result = run_guest_rf_check(endpoint, server, report, deadline=deadline,
        emulator_process=emulator_process, source_settings=trace['source_settings'], measurement_bundle=bundle)
    result['intake_plan'] = trace
    report.save()
    return result
