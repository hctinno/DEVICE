"""Fixture-only guest controller and existing Fleet bridge; no SDK or OS run."""
import base64
import copy
import hashlib
import inspect
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


if __name__ == '__main__':
    unittest.main()
