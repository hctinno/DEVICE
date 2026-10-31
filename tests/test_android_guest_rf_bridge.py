"""Fixture-only guest controller and existing Fleet bridge; no SDK or OS run."""
import base64
import copy
from decimal import Decimal, localcontext
import hashlib
import inspect
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

from labflow import android_emulator_check as check
from labflow import android_guest_rf_bridge as bridge
from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input
from labflow.intake_jobs import _analysis_contract
from labflow.store import canonical


SCRIPT = '/data/local/tmp/dgm-rf-v1.sh'


def value_sha256(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def authored_plan(frequency_mhz=2412, power_dbm=-7):
    text = ('product_type: authored_radio\npurpose: engineering review\nmarket: EU\n'
            f'frequency: {frequency_mhz} MHz\non_average_power: {power_dbm} dBm\n'
            'bandwidth: 20 MHz\nduty_cycle: 50 %\nmodulation: OFDM\ncrest_factor: 4 dB\n')
    raw = text.encode('utf-8')
    document = dict(path='request.txt', sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                    text=text, parse_status='text', format='text', extraction_status='ok', issues=[])
    context_id = hashlib.sha256(b'authored guest source plan').hexdigest()
    context = dict(job_id='J-GUEST-SYN', intake_id='I-GUEST-SYN', revision=1, synthetic=True,
                   documents=[document], analysis_context_id=context_id,
                   analysis_contract=_analysis_contract(dict(documents=[document], context_id=context_id)),
                   instructions='Authored synthetic snapshot; no execution authority.')
    def ref(line):
        return dict(path='request.txt', sha256=document['sha256'], line_start=line, line_end=line,
                    quote=text.splitlines()[line-1], role='request')
    analysis = dict(schema_version=1, producer=dict(kind='fixture', name='AUTHORED-GUEST'), identity='single',
                    facts=[dict(field=field, value=value, status='explicit', evidence=[ref(line)])
                           for field, value, line in [('product_type', 'authored_radio', 1),
                                                     ('purpose', 'engineering review', 2), ('market', 'EU', 3)]],
                    missing_fields=[])
    source = dict(frequency_hz=frequency_mhz*1000000, power_dbm=power_dbm,
                  bandwidth_hz=20000000, duty_cycle=.5, modulation='OFDM', crest_factor_db=4)
    quoted = dict(frequency_hz=(frequency_mhz, 'MHz', 4), power_dbm=(power_dbm, 'dBm', 5),
                  bandwidth_hz=(20, 'MHz', 6), duty_cycle=(50, '%', 7),
                  modulation=('OFDM', 'label', 8), crest_factor_db=(4, 'dB', 9))
    basis = {key: dict(kind='source_cited', value=value, unit=unit, evidence=[ref(line)])
             for key, (value, unit, line) in quoted.items()}
    options = dict(expected_revision=1, expected_context_sha256=value_sha256(context))
    plan = build_conducted_twin_plan_input(context, analysis, source_settings=source, basis=basis,
        method=dict(method_id='conducted_synthetic', method_version=1, metric='on', reference_plane='source_output'),
        **options)
    if plan['status'] != 'ready_for_simulation':
        raise AssertionError(plan['gaps'])
    options['expected_plan_input_sha256'] = value_sha256(plan)
    return context, analysis, plan, options


def receipt(nonce, seq, state, revision, source_hash):
    prefix = f'DGM1|{nonce}|{seq}|{state}|{revision}|{source_hash}'
    return prefix + '|' + hashlib.sha256((prefix + '\n').encode('ascii')).hexdigest()


class FakeGuest:
    """A separate stateful AOSP shell fixture, not a production transport hook."""

    def __init__(self, *, bad_status=False, fail_start=False, fail_cleanup=False,
                 tamper=None, install_failure=None, preexisting_script=False,
                 config_failure=None, preexisting_state=False):
        self.calls = []
        self.bad_status = bad_status
        self.fail_start = fail_start
        self.fail_cleanup = fail_cleanup
        self.tamper = tamper
        self.install_failure = install_failure
        self.preexisting_script = preexisting_script
        self.config_failure = config_failure
        self.preexisting_state = preexisting_state
        self.script_hash = None
        self.state = None
        self.revision = 0
        self.source_hash = None
        self.sequence = 0

    def __call__(self, endpoint, server, service, deadline):
        self.calls.append(service)
        if not service.startswith('shell:') or endpoint.serial != 'emulator-5680':
            raise AssertionError('unowned guest service')
        if service.startswith('shell:test ! -e '):
            if self.install_failure and self.install_failure != 'bad_hash':
                raise check.BoundaryError(self.install_failure)
            encoded = service.split('printf %s ', 1)[1].split(' | base64 -d', 1)[0]
            script = base64.b64decode(encoded, validate=True)
            self.script_hash = hashlib.sha256(script).hexdigest()
            if self.install_failure == 'bad_hash':
                return '0' * 64 + '  ' + SCRIPT
            return self.script_hash + '  ' + SCRIPT
        if (service.startswith('shell:rm -f ')
                or service.startswith('shell:test -d /data/local/tmp/dgm-rf-')):
            self.preexisting_script = False
            if '/state' in service:
                self.preexisting_state = False
            if self.fail_cleanup:
                raise check.BoundaryError('adb_timeout')
            return 'DGM-CLEAN-OK'
        args = service.removeprefix('shell:sh ').split(' ')
        if args[0] != SCRIPT:
            raise AssertionError('arbitrary script')
        operation, nonce, seq_text = args[1:4]
        seq = int(seq_text)
        if operation == 'HELLO':
            self.sequence = seq
            return receipt(nonce, seq, 'HELLO', 0, self.script_hash)
        if seq != self.sequence + 1:
            raise AssertionError('sequence gap')
        self.sequence = seq
        if operation == 'CONFIG':
            if self.config_failure:
                raise check.BoundaryError(self.config_failure)
            source = args[4:10]
            calculated = hashlib.sha256(('|'.join(source) + '\n').encode('ascii')).hexdigest()
            if calculated != args[10]:
                raise AssertionError('source hash disagreement')
            self.source_hash = calculated
            self.state, self.revision = 'CONFIGURED', 1
        elif operation == 'START':
            if self.fail_start:
                raise check.BoundaryError('adb_timeout')
            self.state, self.revision = 'STARTED', 2
        elif operation == 'STOP':
            self.state, self.revision = 'STOPPED', 3
        elif operation != 'STATUS':
            raise AssertionError('unexpected operation')
        state = 'STARTED' if self.bad_status and operation == 'STATUS' and self.state == 'STOPPED' else self.state
        raw = receipt(nonce, seq, state, self.revision, self.source_hash)
        if self.tamper and operation == 'STATUS':
            parts = raw.split('|')
            index = {'nonce': 1, 'sequence': 2, 'revision': 4,
                     'source_hash': 5, 'receipt': 6}[self.tamper]
            parts[index] = ('0' * 32 if index == 1 else '99' if index in (2, 4)
                            else '0' * 64)
            raw = '|'.join(parts)
        return raw


class GuestBridgeFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = check.Report(Path(self.tmp.name) / 'proof')
        self.endpoint = check.Endpoint()
        self.report.data.update(android_os='booted', adb_verified=True,
                                identity={'serial': self.endpoint.serial, 'state': 'device',
                                          'properties': {'ro.kernel.qemu': '1', 'ro.hardware': 'ranchu',
                                                         'ro.product.model': 'AOSP fixture',
                                                         'sys.boot_completed': '1'}})
        self.server = mock.Mock()
        self.server.process.poll.return_value = None
        self.emulator = mock.Mock()
        self.emulator.process.poll.return_value = None
        resources = mock.patch.object(check, 'resources', return_value={'available_mib': 8192})
        resources.start()
        self.addCleanup(resources.stop)

    def run_bridge(self, guest):
        with mock.patch.object(bridge, '_exchange', side_effect=guest):
            return bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                                             deadline=bridge.time.monotonic() + 30,
                                             emulator_process=self.emulator)

    def test_real_guest_state_receipts_and_fresh_fleet_sensor_are_distinct(self):
        guest = FakeGuest()
        result = self.run_bridge(guest)
        self.assertTrue(result['valid'])
        self.assertEqual(result['guest_controller']['states'],
                         ['CONFIGURED', 'CONFIGURED', 'STARTED', 'STARTED', 'STOPPED', 'STOPPED'])
        self.assertEqual(result['guest_controller']['cleanup'], 'confirmed')
        host = result['host_rf_model']
        self.assertTrue(host['synthetic'])
        self.assertFalse(host['physical_verified'])
        self.assertEqual(host['source_settings'], bridge.SOURCE_SETTINGS)
        self.assertEqual(host['source_sha256'], guest.source_hash)
        self.assertEqual(host['sensor_on_average']['unit'], 'dBm')
        self.assertEqual(host['sensor_on_average']['source_id'], 'sensor')
        self.assertEqual(host['meter_time_average']['quantity'], 'time_average')
        self.assertEqual(host['analyzer_on_average']['quantity'], 'on_average')
        self.assertLess(host['meter_time_average']['value'], host['sensor_on_average']['value'])
        self.assertNotEqual(host['after_stop_sensor_status'], 'ok')
        self.assertNotEqual(host['after_stop_analyzer_status'], 'ok')
        self.assertEqual(self.report.data['rf_bridge'], result)
        self.assertEqual(self.report.data['rf_model'], 'synthetic_guest_bridge_verified')
        self.assertTrue(self.server.sample.called)
        self.assertTrue(self.emulator.sample.called)
        self.assertTrue(any(call.startswith('shell:sh ' + SCRIPT + ' CONFIG ') for call in guest.calls))
        self.assertTrue(any(call.startswith('shell:sh ' + SCRIPT + ' STOP ') for call in guest.calls))
        scope = '/data/local/tmp/dgm-rf-' + result['guest_controller']['nonce'] + '.d'
        self.assertTrue(any(scope + '/state' in call and 'rmdir ' + scope in call
                            for call in guest.calls))

    def test_status_mismatch_never_becomes_valid_and_cleanup_is_recorded(self):
        guest = FakeGuest(bad_status=True)
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertFalse(result['valid'])
        self.assertEqual(self.report.data['rf_model'], 'synthetic_guest_bridge_invalid')
        self.assertEqual(result['guest_controller']['cleanup'], 'confirmed')
        self.assertEqual(result['first_error']['code'], 'guest_receipt_mismatch')
        self.assertIn('fleet_stop', result['host_rf_model'])

    def test_unknown_start_and_cleanup_failure_preserve_first_error(self):
        guest = FakeGuest(fail_start=True, fail_cleanup=True)
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertFalse(result['valid'])
        self.assertEqual(result['first_error']['code'], 'adb_timeout')
        self.assertEqual(result['guest_controller']['cleanup'], 'unknown')
        self.assertTrue(result['cleanup_errors'])
        self.assertIn('fleet_stop', result['host_rf_model'])

    def test_wrong_nonce_sequence_revision_hash_or_receipt_never_passes(self):
        for field in ('nonce', 'sequence', 'revision', 'source_hash', 'receipt'):
            with self.subTest(field=field):
                report = check.Report(Path(self.tmp.name) / ('tamper-' + field))
                report.data.update(android_os='booted', adb_verified=True,
                                   identity=self.report.data['identity'])
                guest = FakeGuest(tamper=field)
                with mock.patch.object(bridge, '_exchange', side_effect=guest):
                    with self.assertRaises(check.BoundaryError):
                        bridge.run_guest_rf_check(self.endpoint, self.server, report,
                                                  deadline=time.monotonic() + 30,
                                                  emulator_process=self.emulator)
                self.assertFalse(report.data['rf_bridge']['valid'])
                self.assertEqual(report.data['rf_bridge']['first_error']['code'],
                                 'guest_receipt_mismatch')
                self.assertEqual(report.data['rf_bridge']['guest_controller']['cleanup'],
                                 'confirmed')

    def test_cleanup_failure_after_valid_sequence_is_not_success(self):
        with self.assertRaises(check.BoundaryError) as error:
            self.run_bridge(FakeGuest(fail_cleanup=True))
        self.assertEqual(error.exception.code, 'guest_cleanup_unknown')
        self.assertFalse(self.report.data['rf_bridge']['valid'])
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'],
                         'guest_cleanup_unknown')

    def test_preexisting_guest_script_is_preserved_when_install_rejects_it(self):
        guest = FakeGuest(install_failure='guest_adb_service_failure',
                          preexisting_script=True)
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertTrue(guest.preexisting_script)
        self.assertEqual(len(guest.calls), 1)
        self.assertFalse(result['valid'])
        self.assertEqual(result['first_error']['code'], 'guest_adb_service_failure')
        self.assertEqual(result['guest_controller']['cleanup'], 'unknown')
        self.assertIn('fleet_stop', result['host_rf_model'])

    def test_install_timeout_leaves_unconfirmed_guest_file_untouched(self):
        guest = FakeGuest(install_failure='adb_timeout')
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertEqual(len(guest.calls), 1)
        self.assertFalse(result['valid'])
        self.assertEqual(result['first_error']['code'], 'adb_timeout')
        self.assertEqual(result['guest_controller']['cleanup'], 'unknown')

    def test_unverified_partial_install_does_not_delete_guest_file(self):
        guest = FakeGuest(install_failure='bad_hash')
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertEqual(len(guest.calls), 1)
        self.assertFalse(result['valid'])
        self.assertEqual(result['first_error']['code'], 'guest_script_hash_mismatch')
        self.assertEqual(result['guest_controller']['cleanup'], 'unknown')

    def test_preexisting_nonce_state_survives_unacknowledged_config(self):
        guest = FakeGuest(config_failure='guest_adb_service_failure',
                          preexisting_state=True)
        with self.assertRaises(check.BoundaryError):
            self.run_bridge(guest)
        result = self.report.data['rf_bridge']
        self.assertTrue(guest.preexisting_state)
        self.assertFalse(result['valid'])
        self.assertEqual(result['first_error']['code'], 'guest_adb_service_failure')
        self.assertEqual(result['guest_controller']['cleanup'], 'unknown')
        self.assertIn('fleet_stop', result['host_rf_model'])

    def test_direct_bridge_rejects_custom_endpoint_before_guest_write(self):
        endpoint = check.Endpoint(adb_port=15038, console_port=5678, grpc_port=18554)
        report = check.Report(Path(self.tmp.name) / 'custom-endpoint')
        report.data.update(android_os='booted', adb_verified=True,
                           identity={'serial': endpoint.serial, 'state': 'device',
                                     'properties': {'ro.kernel.qemu': '1', 'ro.hardware': 'ranchu',
                                                    'ro.product.model': 'AOSP fixture',
                                                    'sys.boot_completed': '1'}})
        with mock.patch.object(bridge, '_exchange', side_effect=AssertionError('guest write')):
            with self.assertRaises(check.BoundaryError) as error:
                bridge.run_guest_rf_check(endpoint, self.server, report,
                                          deadline=time.monotonic() + 30,
                                          emulator_process=self.emulator)
        self.assertEqual(error.exception.code, 'rf_bridge_endpoint_invalid')
        self.assertNotIn('rf_bridge', report.data)

    def test_interrupt_during_cleanup_is_recorded_as_unknown(self):
        guest = FakeGuest()
        original = guest.__call__
        def interrupted(endpoint, server, service, deadline):
            if (service.startswith('shell:rm -f ')
                    or service.startswith('shell:test -d /data/local/tmp/dgm-rf-')):
                raise KeyboardInterrupt()
            return original(endpoint, server, service, deadline)
        with mock.patch.object(bridge, '_exchange', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                                          deadline=time.monotonic() + 30,
                                          emulator_process=self.emulator)
        self.assertFalse(self.report.data['rf_bridge']['valid'])
        self.assertEqual(self.report.data['rf_bridge']['guest_controller']['cleanup'], 'unknown')
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'], 'interrupted')

    def test_memory_emergency_during_bridge_is_not_valid(self):
        guest = FakeGuest()
        with mock.patch.object(bridge, '_exchange', side_effect=guest), \
             mock.patch.object(check, 'resources', return_value={'available_mib': 400}):
            with self.assertRaises(check.BoundaryError) as error:
                bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                                          deadline=time.monotonic() + 30,
                                          emulator_process=self.emulator)
        self.assertEqual(error.exception.code, 'memory_emergency_stop')
        self.assertFalse(self.report.data['rf_bridge']['valid'])
        self.assertEqual(self.report.data['rf_bridge']['guest_controller']['cleanup'], 'unknown')
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'],
                         'memory_emergency_stop')

    def test_wire_transport_uses_only_owned_loopback_and_exact_serial(self):
        observed = []
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(2)
            endpoint = check.Endpoint(adb_port=listener.getsockname()[1])
            def peer():
                with listener.accept()[0] as stream:
                    stream.settimeout(2)
                    for _ in range(2):
                        length = int(check._receive(stream, 4), 16)
                        observed.append(check._receive(stream, length).decode('ascii'))
                        stream.sendall(b'OKAY')
                    stream.sendall(b'DGM-CLEAN-OK\n')
            thread = threading.Thread(target=peer)
            thread.start()
            service = bridge._cleanup_service('a' * 32)
            try:
                self.assertEqual(bridge._exchange(endpoint, self.server, service,
                                                  time.monotonic() + 2), 'DGM-CLEAN-OK')
            finally:
                thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(observed, ['host:transport:emulator-5680', service])

    def test_source_is_exact_six_and_script_paths_are_fixed(self):
        source = bridge.SOURCE_SETTINGS
        self.assertEqual(set(source), {'frequency_hz', 'power_dbm', 'bandwidth_hz',
                                       'duty_cycle', 'modulation', 'crest_factor_db'})
        self.assertEqual(bridge.source_sha256(source), hashlib.sha256(
            b'2450000000|12.5|20000000|0.25|OFDM|3\n').hexdigest())
        for bad in ({**source, 'modulation': 'OFDM; reboot'},
                    {**source, 'frequency_hz': float('nan')},
                    {**source, 'extra': 1}):
            with self.subTest(bad=bad), self.assertRaises(check.BoundaryError):
                bridge.source_sha256(bad)
        nonce = 'a' * 32
        tokens = ('2450000000', '12.5', '20000000', '0.25', 'OFDM', '3')
        for operation, fields, digest in (
                ('CONFIG', ('1;reboot', *tokens[1:]), bridge.source_sha256(source)),
                ('CONFIG', tokens, '0' * 64),
                ('START', tokens, None)):
            with self.subTest(operation=operation, fields=fields), \
                 self.assertRaises(check.BoundaryError):
                bridge._command_service(operation, nonce, 1, fields, digest)


class IntakePlanGuestBridgeTests(unittest.TestCase):
    """Real public plan builder + real Fleet; only guest transport is FAKE."""

    def setUp(self):
        GuestBridgeFixtureTests.setUp(self)
        self.context, self.analysis, self.plan, self.options = authored_plan()

    def run_plan(self, guest):
        api = getattr(bridge, 'run_intake_plan_guest_rf_check', None)
        self.assertTrue(callable(api), 'public revalidating intake-to-guest wrapper is absent')
        with mock.patch.object(bridge, '_exchange', side_effect=guest):
            return api(self.context, self.analysis, self.plan, self.endpoint, self.server, self.report,
                       deadline=time.monotonic()+30, emulator_process=self.emulator, **self.options)

    def rehash_plan(self):
        self.options['expected_plan_input_sha256'] = value_sha256(self.plan)

    def test_shared_bundle_validator_is_pure_and_detached(self):
        validate = getattr(bridge, 'validate_intake_plan_bundle', None)
        self.assertTrue(callable(validate), 'shared pure plan bundle validation is absent')
        bundle = dict(context=self.context, analysis=self.analysis, plan_input=self.plan, **self.options)
        original = copy.deepcopy(bundle)
        guest = FakeGuest()
        with mock.patch.object(bridge, '_exchange', side_effect=guest):
            trace = validate(bundle)
        self.assertEqual(bundle, original)
        self.assertEqual(guest.calls, [])
        self.plan['plan']['source_settings']['power_dbm'] = 99
        self.context['synthetic'] = False
        self.assertEqual(trace['source_settings']['power_dbm'], -7)
        self.assertEqual(trace['plan_input'], original['plan_input'])
        self.assertIs(trace['verification']['execution_authority'], False)

    def rejected(self):
        guest = FakeGuest()
        with self.assertRaises(check.BoundaryError) as error:
            self.run_plan(guest)
        self.assertTrue(error.exception.code.startswith('guest_plan_'), error.exception.code)
        self.assertEqual(guest.calls, [])
        self.assertNotIn('rf_bridge', self.report.data)

    def test_two_cited_plans_drive_config_receipts_and_fresh_same_fleet_measurements(self):
        cases = [(2412, -7, -37.5, -18.75, ['2412000000', '-7', '20000000', '0.5', 'OFDM', '4']),
                 (2450, 4, -26.5, -7.75, ['2450000000', '4', '20000000', '0.5', 'OFDM', '4'])]
        for index, (freq, power, sensor, analyzer, tokens) in enumerate(cases):
            with self.subTest(frequency=freq, power=power):
                self.context, self.analysis, self.plan, self.options = authored_plan(freq, power)
                self.report = check.Report(Path(self.tmp.name) / ('cited-'+str(index)))
                self.report.data.update(android_os='booted', adb_verified=True,
                                       identity={'serial': self.endpoint.serial, 'state': 'device',
                                                 'properties': {'ro.kernel.qemu': '1', 'ro.hardware': 'ranchu',
                                                                'ro.product.model': 'AOSP fixture',
                                                                'sys.boot_completed': '1'}})
                original = copy.deepcopy((self.context, self.analysis, self.plan, self.options))
                guest = FakeGuest()
                result = self.run_plan(guest)
                self.assertTrue(result['valid'])
                command = next(call for call in guest.calls if ' CONFIG ' in call)
                self.assertEqual(command.removeprefix('shell:sh ').split(' ')[4:10], tokens)
                expected_hash = hashlib.sha256(('|'.join(tokens)+'\n').encode('ascii')).hexdigest()
                host = result['host_rf_model']
                self.assertEqual(host['source_sha256'], expected_hash)
                self.assertEqual(host['source_settings'], self.plan['plan']['source_settings'])
                self.assertEqual(host['dut_output']['frequency_hz'], freq*1000000)
                self.assertEqual(host['sensor_on_average']['value'], sensor)
                self.assertEqual(host['analyzer_on_average']['value'], analyzer)
                self.assertAlmostEqual(host['meter_time_average']['value'], sensor-3.010299956639812)
                for item in result['guest_controller']['receipts'][1:]:
                    self.assertEqual(item['source_sha256'], expected_hash)
                trace = result['intake_plan']
                self.assertEqual(trace['plan_input'], self.plan)
                self.assertEqual(trace['plan_input_sha256'], self.options['expected_plan_input_sha256'])
                self.assertEqual(trace['source_sha256'], expected_hash)
                self.assertEqual(trace['verification']['current_version'], 'caller_snapshot_only')
                self.assertEqual(trace['verification']['source_bytes'], 'not_reopened')
                self.assertIs(trace['verification']['execution_authority'], False)
                self.assertEqual((self.context, self.analysis, self.plan, self.options), original)

    def test_optional_source_snapshot_drives_direct_bridge_and_default_is_compatible(self):
        self.assertIn('source_settings', inspect.signature(bridge.run_guest_rf_check).parameters,
                      'optional source-six lifecycle input is absent')
        source = dict(self.plan['plan']['source_settings'])
        original = source.copy()
        guest = FakeGuest()
        def mutate_caller(endpoint, server, service, deadline):
            source['power_dbm'] = 99
            return guest(endpoint, server, service, deadline)
        with mock.patch.object(bridge, '_exchange', side_effect=mutate_caller):
            result = bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                deadline=time.monotonic()+30, emulator_process=self.emulator, source_settings=source)
        self.assertEqual(result['host_rf_model']['source_settings'], original)
        self.assertEqual(result['host_rf_model']['sensor_on_average']['value'], -37.5)
        self.assertIn('2412000000 -7 20000000 0.5 OFDM 4', next(s for s in guest.calls if ' CONFIG ' in s))

    def test_missing_extra_bool_nan_and_shell_source_never_write_guest(self):
        self.assertIn('source_settings', inspect.signature(bridge.run_guest_rf_check).parameters,
                      'optional source-six lifecycle input is absent')
        source = self.plan['plan']['source_settings']
        bad_inputs = [{k:v for k,v in source.items() if k!='power_dbm'}, {**source, 'ready': True},
                      {**source, 'power_dbm': True}, {**source, 'frequency_hz': float('nan')},
                      {**source, 'modulation': 'OFDM; reboot'}]
        for supplied in bad_inputs:
            with self.subTest(supplied=supplied):
                guest = FakeGuest()
                with mock.patch.object(bridge, '_exchange', side_effect=guest), self.assertRaises(check.BoundaryError):
                    bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                        deadline=time.monotonic()+30, emulator_process=self.emulator, source_settings=supplied)
                self.assertEqual(guest.calls, [])

    def test_caller_plan_mutation_during_guest_io_cannot_change_bound_config(self):
        original = copy.deepcopy(self.plan)
        guest = FakeGuest()
        def mutate_caller(endpoint, server, service, deadline):
            self.plan['plan']['source_settings']['power_dbm'] = 99
            self.context['synthetic'] = False
            return guest(endpoint, server, service, deadline)
        result = self.run_plan(mutate_caller)
        self.assertEqual(result['host_rf_model']['source_settings'], original['plan']['source_settings'])
        self.assertEqual(result['intake_plan']['plan_input'], original)
        self.assertEqual(result['host_rf_model']['sensor_on_average']['value'], -37.5)

    def test_bad_citation_and_forged_ready_approval_are_revalidated(self):
        self.analysis['facts'][0]['evidence'][0]['quote'] = 'invented product evidence'
        self.plan['status'] = 'ready_for_simulation'
        self.plan['verification']['execution_authority'] = True
        self.rehash_plan()
        self.rejected()

    def test_altered_source_and_rehashed_plan_cannot_bypass_basis_revalidation(self):
        self.plan['plan']['source_settings']['frequency_hz'] = 2450000000
        self.rehash_plan()
        self.rejected()

    def test_rehashed_ready_approval_or_binding_must_match_rebuilt_plan(self):
        original = copy.deepcopy(self.plan)
        for field in ('authority', 'binding', 'extra_approval'):
            with self.subTest(field=field):
                self.plan = copy.deepcopy(original)
                if field == 'authority':
                    self.plan['verification']['execution_authority'] = True
                elif field == 'binding':
                    self.plan['binding']['analysis_sha256'] = '0'*64
                else:
                    self.plan['approved'] = True
                self.rehash_plan()
                self.rejected()

    def test_changed_expected_context_or_plan_hash_and_bool_revision_never_enter_guest(self):
        original = self.options.copy()
        for key, value in [('expected_context_sha256', '0'*64), ('expected_plan_input_sha256', '0'*64),
                           ('expected_revision', True)]:
            with self.subTest(key=key):
                self.options = {**original, key: value}
                self.rejected()

    def test_missing_intake_information_never_uses_supplied_ready(self):
        self.analysis['facts'] = self.analysis['facts'][:2]
        self.analysis['missing_fields'] = ['market']
        self.rejected()

    def test_non_synthetic_snapshot_never_enters_guest(self):
        self.context['synthetic'] = False
        self.options['expected_context_sha256'] = value_sha256(self.context)
        self.rejected()

    def test_bool_nan_and_unsupported_method_in_supplied_plan_never_enter_guest(self):
        original = copy.deepcopy(self.plan)
        for change in ('bool', 'nan', 'method'):
            with self.subTest(change=change):
                self.plan = copy.deepcopy(original)
                if change == 'method':
                    self.plan['plan']['method_id'] = 'fcc_15_247'
                else:
                    self.plan['plan']['source_settings']['power_dbm'] = True if change=='bool' else float('nan')
                if change != 'nan':
                    self.rehash_plan()
                self.rejected()

    def test_plan_failure_keeps_binding_original_error_and_unknown_cleanup(self):
        guest = FakeGuest(fail_start=True, fail_cleanup=True)
        with self.assertRaises(check.BoundaryError) as error:
            self.run_plan(guest)
        self.assertEqual(error.exception.code, 'adb_timeout')
        self.assertEqual(self.report.data['rf_bridge']['first_error']['code'], 'adb_timeout')
        self.assertEqual(self.report.data['rf_bridge']['guest_controller']['cleanup'], 'unknown')
        self.assertEqual(self.report.data['intake_plan']['plan_input']['binding'], self.plan['binding'])
        self.assertEqual(self.report.data['intake_plan']['source_sha256'], guest.source_hash)

    def test_plan_wrapper_keeps_fixed_endpoint_gate_before_guest_write(self):
        self.endpoint = check.Endpoint(adb_port=15038, console_port=5678, grpc_port=18554)
        guest = FakeGuest()
        with self.assertRaises(check.BoundaryError) as error:
            self.run_plan(guest)
        self.assertEqual(error.exception.code, 'rf_bridge_endpoint_invalid')
        self.assertEqual(guest.calls, [])


class FirstOnPlanMeasurementTests(unittest.TestCase):
    """Genuine plan/Fleet/journal/calculation; only the owned guest is FAKE."""

    setUp = IntakePlanGuestBridgeTests.setUp
    run_plan = IntakePlanGuestBridgeTests.run_plan

    def first_on(self, result):
        self.assertTrue('first_on_measurement' in result,
                        'plan metric has no connected first-ON measurement result')
        return result['first_on_measurement']

    def new_report(self, name):
        identity = copy.deepcopy(self.report.data['identity'])
        self.report = check.Report(Path(self.tmp.name) / name)
        self.report.data.update(android_os='booted', adb_verified=True, identity=identity)

    def test_two_sources_use_original_packet_and_declared_ledger_decimal_oracle(self):
        # Catches dropped selector/math connection, expected-power substitution,
        # or conflation of a historical acquisition with current validity/storage.
        for index, (frequency, power, reading) in enumerate(((2412, -7, '-37.5'),
                                                            (2450, 4, '-26.5'))):
            with self.subTest(frequency=frequency):
                self.context, self.analysis, self.plan, self.options = authored_plan(frequency, power)
                self.new_report('first-on-'+str(index))
                result = self.run_plan(FakeGuest())
                first = self.first_on(result)
                self.assertEqual(first['kind'], 'owned_guest_first_on_measurement')
                self.assertEqual(first['source_kind'], 'owned_guest_fleet_harness')
                self.assertEqual(first['status'], 'recorded')
                self.assertEqual(first['storage_status'], 'not_run')
                self.assertIs(first['artifact_created'], False)
                selected = first['selection']
                self.assertEqual(selected['status'], 'selected')
                self.assertIs(selected['verification']['fallback_attempted'], False)
                native = selected['result']
                self.assertIs(first['result'], native)
                self.assertIsNone(first['first_failure'])
                self.assertEqual(set(native), set('schema_version kind status binding raw_measurement '
                    'setup_provenance calculation gaps failure verification'.split()))
                self.assertEqual(native['kind'], 'conducted_twin_result')
                self.assertEqual(native['status'], 'recorded')
                raw = native['raw_measurement']['packet']
                self.assertEqual(raw['value'], float(reading))
                self.assertIs(raw['valid'], True)
                self.assertEqual(raw, result['host_rf_model']['sensor_on_average'])
                math = native['calculation']
                self.assertEqual([row['loss_db'] for row in math['correction_ledger']], [10, .5, 20])
                for row in math['correction_ledger']:
                    setup = native['setup_provenance']['records'][row['record_index']]
                    self.assertEqual(setup['request_id'], row['request_id'])
                    self.assertEqual(setup['parameters'][row['setting']], row['loss_db'])
                    self.assertIs(row['already_applied'], False)
                with localcontext() as context:
                    context.prec = 50
                    corrected = Decimal(reading)+Decimal('10')+Decimal('0.5')+Decimal('20')
                    watts = Decimal(10)**((corrected-Decimal(30))/Decimal(10))
                    raw_watts = Decimal(10)**((Decimal(reading)-Decimal(30))/Decimal(10))
                self.assertEqual(Decimal(str(math['corrected']['value'])), corrected)
                self.assertAlmostEqual(math['corrected']['power_w']/float(watts), 1, places=12)
                self.assertAlmostEqual(math['raw_power_w']['value']/float(raw_watts), 1, places=12)
                self.assertEqual(math['conformity'], dict(status='not_assessed', verdict=None,
                    numeric_limit_dbm=None, uncertainty_db=None))
                self.assertEqual(math['target_reference_plane'], 'source_output')
                self.assertIs(native['verification']['execution_authority'], False)
                self.assertIs(native['verification']['physical_verified'], False)
                self.assertEqual(first['current_after_stop']['sensor']['status'], 'invalid')
                self.assertEqual(first['current_after_stop']['analyzer']['status'], 'invalid')
                self.assertEqual(first['binding']['source_sha256'], result['host_rf_model']['source_sha256'])
                self.assertEqual(first['binding']['acquisition_tick'], raw['acquisition_tick'])
                self.assertEqual(first['binding']['setup_revision'], raw['acquisition_setup_revision'])

    def test_every_post_setup_effect_has_same_live_harness_intent_receipt_and_first_completion(self):
        # Catches a bypass through the direct Fleet, omitted auxiliary/STOP calls,
        # fabricated reports/journals, or selection of a later successful reference.
        calls = []
        factory = bridge.create_conducted_example
        class ObservedFleet:
            def __init__(self, fleet): self.fleet = fleet
            def execute(self, request, device, action, parameters=None):
                calls.append(('execute', request, device, action, copy.deepcopy(parameters)))
                return self.fleet.execute(request, device, action, parameters)
            def advance(self, request, ticks):
                calls.append(('advance', request, ticks))
                return self.fleet.advance(request, ticks)
            def observations(self): return self.fleet.observations()
        def observed_factory(*args, **kwargs):
            fleet, topology, setup = factory(*args, **kwargs)
            return ObservedFleet(fleet), topology, setup
        with mock.patch.object(bridge, 'create_conducted_example', side_effect=observed_factory):
            result = self.run_plan(FakeGuest())
        first = self.first_on(result)
        self.assertEqual(first['status'], 'recorded')
        from labflow.virtual_fleet.journal import read_operator_journal
        stored = read_operator_journal(self.report.output / first['journal_file'])
        self.assertEqual(stored, first['journal_read'])
        self.assertIs(stored['complete'], True)
        report = first['run_report']
        self.assertEqual(report['termination'], dict(reason='policy_stop', policy_claim='completed'))
        self.assertEqual(report['task_outcome'], 'not_assessed')
        self.assertIs(report['ai_model_called'], False)
        self.assertEqual(report['policy']['kind'], 'fixture')
        for key in ('run_id', 'runtime_instance_id'):
            self.assertEqual(first['binding'][key], stored['header'][key])
            self.assertEqual(report[key], stored['header'][key])
            self.assertEqual(first['selection']['result']['binding'][key], report[key])
        setup = first['setup_snapshot']
        self.assertLessEqual(len(setup), 32)
        self.assertEqual((setup[-1]['device_id'], setup[-1]['action']), ('dut', 'stop'))
        setup_ids = {row['request_id'] for row in setup}
        effects = [row for row in calls if row[1] not in setup_ids]
        intents = [event for event in stored['events'] if event['type'] == 'intent']
        receipts = [event for event in stored['events'] if event['type'] == 'receipt']
        self.assertEqual([row[1] for row in effects], [e['payload']['request_id'] for e in intents])
        self.assertEqual([e['payload']['request_id'] for e in receipts], [row[1] for row in effects])
        acquires = [e for e in intents if e['payload']['body'].get('device_id') == 'sensor'
                    and e['payload']['body'].get('action') == 'acquire']
        self.assertEqual(len(acquires), 1)
        self.assertEqual(first['selection']['request_id'], acquires[0]['payload']['request_id'])
        selected = first['selection']['candidate']
        acquired = next(e for e in receipts if e['event_id'] == selected['receipt_ref'])
        self.assertEqual(first['acquisition_receipt'], acquired['payload']['result'])
        completions = [e for e in stored['events'] if e['type'] == 'observation'
            and e['sequence'] > acquired['sequence']
            and e['payload']['observation']['devices']['sensor']['values'].get('state') != 'acquiring']
        self.assertEqual(selected['measurement_ref'], completions[0]['event_id'])
        self.assertEqual(stored['header']['provenance']['source_sha256'], first['binding']['source_sha256'])
        for device, action in (('meter', 'fetch'), ('analyzer', 'fetch'), ('dut', 'stop'), ('sensor', 'read')):
            self.assertTrue(any(e['payload']['body'].get('device_id') == device
                and e['payload']['body'].get('action') == action for e in intents))

    def test_default_source_state_diagnostic_does_not_start_measurement_recorder(self):
        with (mock.patch.object(bridge, 'FleetHarness', create=True, side_effect=AssertionError('unexpected recorder')),
              mock.patch.object(bridge, 'OperatorJournal', create=True, side_effect=AssertionError('unexpected journal'))):
            with mock.patch.object(bridge, '_exchange', side_effect=FakeGuest()):
                result = bridge.run_guest_rf_check(self.endpoint, self.server, self.report,
                    deadline=time.monotonic()+30, emulator_process=self.emulator)
        self.assertTrue(result['valid'])
        self.assertNotIn('first_on_measurement', result)
        self.assertFalse((self.report.output / 'first-on.jsonl').exists())

    def test_time_and_peak_remain_unsupported_without_on_result_or_journal(self):
        for metric in ('time', 'peak'):
            with self.subTest(metric=metric):
                self.context, self.analysis, old, self.options = authored_plan()
                self.plan = build_conducted_twin_plan_input(self.context, self.analysis,
                    expected_revision=1, expected_context_sha256=self.options['expected_context_sha256'],
                    source_settings=old['plan']['source_settings'], basis=old['plan']['basis_refs'],
                    method=dict(method_id='conducted_synthetic', method_version=1,
                                metric=metric, reference_plane='source_output'))
                self.assertEqual(self.plan['status'], 'ready_for_simulation')
                self.options['expected_plan_input_sha256'] = value_sha256(self.plan)
                self.new_report('unsupported-'+metric)
                result = self.run_plan(FakeGuest())
                self.assertTrue(result['valid'])
                first = self.first_on(result)
                self.assertEqual(first['metric'], metric)
                self.assertEqual(first['status'], 'unsupported')
                self.assertIsNone(first['selection'])
                self.assertIsNone(first['result'])
                self.assertIsNone(first['run_report'])
                self.assertEqual(first['verification']['assessment'], 'not_assessed')
                self.assertFalse((self.report.output / 'first-on.jsonl').exists())

    def test_other_reference_plane_keeps_original_pre_io_rejection(self):
        self.plan['plan']['reference_plane'] = 'sensor_input'
        self.options['expected_plan_input_sha256'] = value_sha256(self.plan)
        guest = FakeGuest()
        with self.assertRaises(check.BoundaryError): self.run_plan(guest)
        self.assertEqual(guest.calls, [])
        self.assertFalse((self.report.output / 'first-on.jsonl').exists())

    def fault_factory(self, mode):
        factory = bridge.create_conducted_example
        class FaultObservationFleet:
            def __init__(self, fleet): self.fleet, self.active, self.changed = fleet, False, False
            def corrupt(self, packet):
                if mode in ('invalid', 'first_invalid'):
                    packet.update(status='invalid', valid=False)
                elif mode == 'stale': packet['acquisition_tick'] = 0
                elif mode == 'revision': packet['acquisition_setup_revision'] = 0
                elif mode == 'source': packet['source_id'] = 'analyzer'
                elif mode == 'frequency': packet['frequency_hz'] = 5800000000
            def execute(self, request, device, action, parameters=None):
                value = self.fleet.execute(request, device, action, parameters)
                if device == 'sensor' and action == 'acquire':
                    self.active = True
                    if mode == 'receipt': value['device_id'] = 'analyzer'
                if self.active and device == 'sensor' and action == 'read' and mode not in ('first_invalid', 'receipt'):
                    packet = value['values'].get('outputs', {}).get('measurement')
                    if type(packet) is dict: self.corrupt(packet)
                return value
            def advance(self, request, ticks): return self.fleet.advance(request, ticks)
            def observations(self):
                value = self.fleet.observations()
                sensor = value['devices']['sensor']
                packet = sensor['values'].get('outputs', {}).get('measurement')
                if self.active and type(packet) is dict and packet.get('valid') is True:
                    if mode != 'first_invalid' or not self.changed:
                        self.corrupt(packet);self.changed = True
                return value
        def create(*args, **kwargs):
            fleet, topology, setup = factory(*args, **kwargs)
            return FaultObservationFleet(fleet), topology, setup
        return create

    def test_invalid_stale_revision_source_and_typed_receipt_never_record(self):
        for mode in ('invalid', 'stale', 'revision', 'source', 'frequency', 'receipt'):
            with self.subTest(mode=mode):
                self.new_report('fault-'+mode)
                with mock.patch.object(bridge, 'create_conducted_example', side_effect=self.fault_factory(mode)):
                    try: result = self.run_plan(FakeGuest())
                    except check.BoundaryError: result = self.report.data['rf_bridge']
                first = self.first_on(result)
                self.assertNotEqual(first['status'], 'recorded')
                self.assertIs(first['artifact_created'], False)
                self.assertTrue((self.report.output / first['journal_file']).is_file())
                self.assertIsNotNone(first['journal_read'])
                if first['selection'] and first['selection']['result']:
                    self.assertIsNone(first['selection']['result']['calculation']['corrected'])

    def test_first_invalid_completion_has_no_fallback_to_later_valid_packet(self):
        with mock.patch.object(bridge, 'create_conducted_example', side_effect=self.fault_factory('first_invalid')):
            result = self.run_plan(FakeGuest())
        first = self.first_on(result)
        self.assertNotEqual(first['status'], 'recorded')
        self.assertEqual(first['selection']['status'], 'blocked')
        self.assertIs(first['selection']['verification']['fallback_attempted'], False)
        candidate = first['selection']['result']['raw_measurement']['packet']
        self.assertIs(candidate['valid'], False)
        self.assertIs(result['host_rf_model']['sensor_on_average']['valid'], True)
        self.assertIsNone(first['selection']['result']['calculation']['corrected'])

    def test_second_actual_acquire_is_ambiguous_without_later_success_fallback(self):
        action = bridge._fleet_action
        def twice(fleet, result, request, device, operation, parameters=None):
            receipt = action(fleet, result, request, device, operation, parameters)
            if request == 'sensor-read':
                fleet.execute('fixture-second-acquire', 'sensor', 'acquire')
                fleet.advance('fixture-second-wait', 3)
            return receipt
        with mock.patch.object(bridge, '_fleet_action', side_effect=twice): result = self.run_plan(FakeGuest())
        first = self.first_on(result)
        self.assertNotEqual(first['status'], 'recorded')
        self.assertEqual(first['selection']['status'], 'blocked')
        self.assertIs(first['selection']['verification']['fallback_attempted'], False)

    def test_different_actual_run_report_cannot_be_selected(self):
        other = self.first_on(self.run_plan(FakeGuest()))['run_report']
        self.new_report('other-run')
        from labflow.virtual_fleet.conducted_measurement_selector import select_conducted_measurement
        def swapped(plan, setup, stored, report):
            self.assertNotEqual(report['run_id'], other['run_id'])
            return select_conducted_measurement(plan, setup, stored, other)
        with mock.patch.object(bridge, 'select_conducted_measurement', create=True, side_effect=swapped):
            result = self.run_plan(FakeGuest())
        first = self.first_on(result)
        self.assertNotEqual(first['status'], 'recorded')
        self.assertEqual(first['selection']['status'], 'blocked')

    def test_control_unknown_cancel_and_failed_cleanup_keep_original_error_and_partial_journal(self):
        for mode in ('start', 'stop', 'cleanup', 'cancel', 'source_hash', 'receipt'):
            with self.subTest(mode=mode):
                self.new_report('control-'+mode)
                guest = FakeGuest(fail_start=mode == 'start', bad_status=mode == 'stop',
                    fail_cleanup=mode in ('start', 'cleanup'),
                    tamper=mode if mode in ('source_hash', 'receipt') else None)
                cancelled = KeyboardInterrupt('authored cancellation')
                def transport(*args):
                    if mode == 'cancel' and ' START ' in args[2]: raise cancelled
                    return guest(*args)
                with mock.patch.object(bridge, '_exchange', side_effect=transport):
                    with self.assertRaises((check.BoundaryError, KeyboardInterrupt)) as error:
                        bridge.run_intake_plan_guest_rf_check(self.context, self.analysis, self.plan,
                            self.endpoint, self.server, self.report, deadline=time.monotonic()+30,
                            emulator_process=self.emulator, **self.options)
                result = self.report.data['rf_bridge'];first = self.first_on(result)
                self.assertNotEqual(first['status'], 'recorded')
                self.assertIs(result['valid'], False)
                if mode == 'start': self.assertEqual(result['first_error']['code'], 'adb_timeout')
                if mode == 'cancel': self.assertIs(error.exception, cancelled)
                if first['run_report']:
                    self.assertNotEqual(first['run_report']['termination']['reason'], 'policy_stop')
                    self.assertIsNone(first['run_report']['termination']['policy_claim'])
                if mode in ('stop', 'cleanup'):
                    self.assertTrue(any(e['type'] == 'observation' and
                        e['payload']['observation']['devices']['sensor']['values'].get('outputs', {})
                        .get('measurement', {}).get('valid') is True for e in first['journal_read']['events']))

    def test_selection_failure_is_secondary_to_original_control_and_recovery_failure(self):
        with mock.patch.object(bridge, 'select_conducted_measurement', create=True,
                               side_effect=RuntimeError('authored selector failure')):
            with self.assertRaises(check.BoundaryError) as error:
                self.run_plan(FakeGuest(fail_start=True, fail_cleanup=True))
        self.assertEqual(error.exception.code, 'adb_timeout')
        result = self.report.data['rf_bridge'];first = self.first_on(result)
        self.assertEqual(result['first_error']['code'], 'adb_timeout')
        self.assertEqual(first['status'], 'incomplete')
        self.assertEqual([row['phase'] for row in first['secondary_errors']], ['selection'])
        self.assertEqual(first['run_report']['termination']['policy_claim'], None)

    def test_changed_genuine_journal_source_sha_is_not_attributed_to_the_plan(self):
        # The original parent knows the plan/setup source, but the new outer
        # source SHA is this bridge's contract and must also be checked.
        from labflow.virtual_fleet.journal import OperatorJournal
        def wrong_source(*args, **kwargs):
            kwargs['provenance'] = copy.deepcopy(kwargs['provenance'])
            kwargs['provenance']['source_sha256'] = '0'*64
            return OperatorJournal(*args, **kwargs)
        with mock.patch.object(bridge, 'OperatorJournal', create=True, side_effect=wrong_source):
            result = self.run_plan(FakeGuest())
        first = self.first_on(result)
        self.assertNotEqual(first['status'], 'recorded')
        self.assertIsNone(first['selection'])
        self.assertEqual(first['journal_read']['header']['provenance']['source_sha256'], '0'*64)
        self.assertTrue(any(row['phase'] == 'binding' for row in first['secondary_errors']))

    def test_journal_read_and_close_errors_are_secondary_without_masking_first_control_error(self):
        from labflow.virtual_fleet.journal import OperatorJournal
        close = OperatorJournal.close
        def bad_close(writer):
            close(writer)
            raise OSError('authored close uncertainty')
        for phase in ('journal_read', 'journal_close'):
            with self.subTest(phase=phase):
                self.new_report('secondary-'+phase)
                patch = (mock.patch.object(bridge, 'read_operator_journal', create=True,
                            side_effect=OSError('authored read failure')) if phase == 'journal_read'
                         else mock.patch.object(OperatorJournal, 'close', bad_close))
                with patch:
                    with self.assertRaises(check.BoundaryError) as error:
                        self.run_plan(FakeGuest(fail_start=True, fail_cleanup=True))
                self.assertEqual(error.exception.code, 'adb_timeout')
                result = self.report.data['rf_bridge'];first = self.first_on(result)
                self.assertEqual(result['first_error']['code'], 'adb_timeout')
                self.assertEqual(first['status'], 'incomplete')
                self.assertTrue(any(row['phase'] == phase for row in first['secondary_errors']))

    def test_cancellation_during_selection_is_preserved_after_evidence_cleanup(self):
        interrupted = KeyboardInterrupt('authored selection cancellation')
        with mock.patch.object(bridge, 'select_conducted_measurement', create=True, side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt) as error: self.run_plan(FakeGuest())
        self.assertIs(error.exception, interrupted)
        result = self.report.data['rf_bridge'];first = self.first_on(result)
        self.assertEqual(first['status'], 'incomplete')
        self.assertIs(result['valid'], False)
        self.assertEqual(result['first_error']['code'], 'interrupted')
        self.assertEqual(first['secondary_errors'][0]['phase'], 'selection')

    def test_rejected_selection_exposes_no_result_and_keeps_first_measurement_failure(self):
        with mock.patch.object(bridge, 'create_conducted_example', side_effect=self.fault_factory('first_invalid')):
            result = self.run_plan(FakeGuest())
        first = self.first_on(result)
        self.assertIn('result', first)
        self.assertIsNone(first['result'])
        self.assertEqual(first['first_failure']['phase'], 'selection')
        self.assertTrue(first['first_failure']['code'])
        self.assertEqual(first['run_report']['termination']['policy_claim'], 'completed')
        self.assertTrue(result['valid'])  # Local control diagnostic only.
        self.assertIn(first['status'], ('invalid', 'incomplete'))
        self.assertEqual(first['storage_status'], 'not_run')

    def test_existing_draft_writer_consumes_exact_genuine_result_only_in_fixture(self):
        first = self.first_on(self.run_plan(FakeGuest()))
        self.assertEqual(first['status'], 'recorded')
        native = first['selection']['result']
        from labflow.virtual_fleet.conducted_result_artifact import write_conducted_result_artifact
        root = Path(self.tmp.name) / 'draft-fixture';root.mkdir()
        artifact = write_conducted_result_artifact(native, workspace_root=root, artifact_name='first-on',
            expected_result_sha256=value_sha256(native), run_id=native['binding']['run_id'],
            runtime_instance_id=native['binding']['runtime_instance_id'])
        self.assertEqual(artifact['storage']['status'], 'complete')
        result_file = next(root / row['path'] for row in artifact['files'] if row['path'].endswith('/result.json'))
        self.assertEqual(json.loads(result_file.read_text(encoding='utf-8')), native)
        draft = next(root / row['path'] for row in artifact['files'] if row['path'].endswith('/draft.md'))
        self.assertIn('DRAFT', draft.read_text(encoding='utf-8'))
        self.assertEqual(first['storage_status'], 'not_run')
        self.assertIs(first['artifact_created'], False)


if __name__ == '__main__':
    unittest.main()
