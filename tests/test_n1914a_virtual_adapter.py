"""Real VirtualLab executions; all values and faults in this file are synthetic."""
import copy
import hashlib
import json
import math
import threading
import unittest
from unittest.mock import patch

from labflow.virtual_lab import VirtualLab
from labflow.n1914a_virtual_adapter import (
    N1914AVirtualAdapter, describe_virtual_n1914a_contract,
)


def bench(**kwargs):
    lab = VirtualLab(**kwargs)
    lab.configure_dut('g', 6, 10)
    lab.set_path(True, 3)
    lab.start_tx()
    return lab


def commands(receipt):
    return [r['command'] for r in receipt['transcript'] if r['operation'] == 'meter']


class N1914AVirtualAdapterTests(unittest.TestCase):
    def assert_receipt(self, receipt):
        self.assertEqual(set(receipt), {
            'schema_version', 'request_id', 'model', 'profile_id', 'backend',
            'synthetic', 'hardware_verified', 'vendor_binary_executed',
            'sensor_compatibility', 'calibration', 'firmware', 'options', 'real_support',
            'current_setup_match', 'resumable', 'rf_control_performed', 'rf_safe_verified',
            'request', 'status', 'code', 'measurement', 'ticks', 'transcript',
            'transcript_sha256', 'error_queue', 'cleanup',
        })
        self.assertEqual(receipt['schema_version'], 1)
        self.assertEqual(receipt['model'], 'N1914A')
        self.assertEqual(receipt['profile_id'], 'n1914a-a-ascii-v1')
        self.assertEqual(receipt['backend'], 'existing_virtual_lab')
        self.assertIs(receipt['synthetic'], True)
        for key in ('hardware_verified', 'vendor_binary_executed', 'resumable',
                    'rf_control_performed', 'rf_safe_verified'):
            self.assertIs(receipt[key], False)
        for key in ('sensor_compatibility', 'calibration', 'firmware', 'options',
                    'real_support', 'current_setup_match'):
            self.assertEqual(receipt[key], 'not_assessed')
        raw = json.dumps(receipt['transcript'], sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.assertEqual(receipt['transcript_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(receipt['error_queue']['consuming'])
        self.assertEqual(receipt['error_queue']['attempts'],
                         commands(receipt).count('SYST:ERR?'))
        for i, row in enumerate(receipt['transcript'], 1):
            self.assertEqual(set(row), {'sequence', 'operation', 'command', 'ticks',
                                        'reply', 'code'})
            self.assertEqual(row['sequence'], i)
        forbidden = {'*RST', '*CLS', 'READ1?', 'MEAS1?', 'CAL:ALL?', '*TRG'}
        self.assertFalse(forbidden.intersection(commands(receipt)))

    def test_descriptor_is_detached_and_exact_model_only(self):
        x = describe_virtual_n1914a_contract()
        self.assertEqual(x['model'], 'N1914A')
        self.assertEqual(x['receipt_limit'], 128)
        self.assertEqual(x['units'], ['DBM', 'W'])
        self.assertEqual(x['timeout_ticks'], {'minimum': 1, 'maximum': 1000, 'default': 20})
        x['units'].append('DB')
        self.assertEqual(describe_virtual_n1914a_contract()['units'], ['DBM', 'W'])
        for model in ('N1911A', 'N9030A', 'n1914a', ' N1914A', None, ['N1914A']):
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, '^unsupported_model$'):
                describe_virtual_n1914a_contract(model)
            lab = bench()
            with patch.object(lab, 'meter', side_effect=AssertionError('must not execute')):
                with self.assertRaisesRegex(ValueError, '^unsupported_model$'):
                    N1914AVirtualAdapter(lab, model=model)

    def test_exact_virtual_lab_type_and_no_constructor_io(self):
        class OtherLab(VirtualLab):
            pass
        for value in (None, 'TCPIP::example', lambda c: {}, object(), OtherLab()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(ValueError, '^virtual_lab_required$'):
                    N1914AVirtualAdapter(value)
        lab = bench()
        with patch.object(lab, 'meter', side_effect=AssertionError('must not execute')):
            N1914AVirtualAdapter(lab)

    def test_invalid_requests_do_not_touch_lab_or_callback(self):
        lab = bench()
        adapter = N1914AVirtualAdapter(lab)
        bad = [
            ('', {}, 'invalid_request_id'), ('a' * 129, {}, 'invalid_request_id'),
            ('bad/id', {}, 'invalid_request_id'), ('가상', {}, 'invalid_request_id'),
            ('_a', {}, 'invalid_request_id'), (True, {}, 'invalid_request_id'),
            ('a', {'unit': 'dBm'}, 'unsupported_unit'),
            ('a', {'unit': ['DBM']}, 'unsupported_unit'),
            ('a', {'timeout_ticks': True}, 'invalid_timeout_ticks'),
            ('a', {'timeout_ticks': 0}, 'invalid_timeout_ticks'),
            ('a', {'timeout_ticks': 1001}, 'invalid_timeout_ticks'),
            ('a', {'timeout_ticks': 1.0}, 'invalid_timeout_ticks'),
            ('a', {'can_continue': False}, 'invalid_continuation'),
        ]
        with patch.object(lab, 'meter', side_effect=AssertionError('must not execute')):
            for request_id, kwargs, code in bad:
                with self.subTest(code=code, kwargs=kwargs):
                    with self.assertRaisesRegex(ValueError, '^' + code + '$'):
                        adapter.measure(request_id, **kwargs)

    def test_actual_dbm_and_w_preserve_original_wire_and_metadata(self):
        for unit, expected in [('DBM', 7.0), ('W', 10 ** ((7 - 30) / 10))]:
            with self.subTest(unit=unit):
                lab = bench()
                original = lab.meter
                seen = []
                def meter(command):
                    reply = original(command)
                    seen.append((command, copy.deepcopy(reply)))
                    return reply
                with patch.object(lab, 'meter', side_effect=meter):
                    receipt = N1914AVirtualAdapter(lab).measure('normal.' + unit, unit=unit)
                self.assert_receipt(receipt)
                self.assertEqual(receipt['status'], 'completed')
                self.assertIsNone(receipt['code'])
                self.assertEqual(receipt['measurement']['value'], expected)
                self.assertEqual(receipt['measurement']['unit'], unit)
                self.assertEqual(receipt['measurement']['measurement_id'], 1)
                self.assertEqual(receipt['ticks'], {'start': 0, 'end': 2, 'advance_attempts': 2})
                self.assertEqual(receipt['cleanup'], {'status': 'not_needed', 'code': None})
                self.assertEqual([(r['command'], r['reply']) for r in receipt['transcript']
                                  if r['operation'] == 'meter'], seen)
                fetch = next(r['reply'] for r in receipt['transcript'] if r['command'] == 'FETC1?')
                self.assertEqual(fetch['response'], f'{expected:+.9E}')
                self.assertEqual(fetch['measurement'], receipt['measurement'])
                self.assertEqual(commands(receipt)[:13], [
                    '*IDN?', 'SYST:ERR?', 'INIT1:CONT OFF', 'SYST:ERR?',
                    'FORM:DATA ASCII', 'SYST:ERR?', 'TRIG1:SOUR IMM', 'SYST:ERR?',
                    'UNIT1:POW ' + unit, 'SYST:ERR?', 'UNIT1:POW?', 'INIT1', 'SYST:ERR?',
                ])
                self.assertEqual(commands(receipt)[-2:], ['FETC1?', 'SYST:ERR?'])

    def test_no_dut_configuration_is_not_a_support_or_rf_presence_claim(self):
        receipt = N1914AVirtualAdapter(VirtualLab()).measure('floor')
        self.assert_receipt(receipt)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(receipt['measurement']['value'], -100.0)
        self.assertEqual(receipt['measurement']['setup_revision'], 0)

    def test_fifo_and_overflow_are_consumed_once_not_cleared(self):
        for overflow in (False, True):
            lab = bench()
            for _ in range(32 if overflow else 2):
                lab.meter('*TRG')
            if overflow:
                for _ in range(29):
                    self.assertEqual(lab.meter('SYST:ERR?')['error_number'], -211)
            receipt = N1914AVirtualAdapter(lab).measure('queue')
            self.assert_receipt(receipt)
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['code'], 'error_queue_nonzero')
            self.assertEqual(commands(receipt), ['*IDN?', 'SYST:ERR?'])
            self.assertEqual(receipt['transcript'][-1]['reply']['error_number'],
                             -350 if overflow else -211)
            self.assertEqual(lab.meter('SYST:ERR?')['error_number'], 0 if overflow else -211)

    def test_first_setup_error_stops_and_keeps_prefix(self):
        lab = bench()
        original = lab.meter
        def meter(command):
            reply = original(command)
            if command == 'FORM:DATA ASCII':
                original('*TRG')
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = N1914AVirtualAdapter(lab).measure('setup-error')
        self.assertEqual(receipt['code'], 'error_queue_nonzero')
        self.assertEqual(commands(receipt)[-2:], ['FORM:DATA ASCII', 'SYST:ERR?'])
        self.assertNotIn('INIT1', commands(receipt))

    def test_existing_busy_acquisition_is_observed_and_aborted_without_new_init(self):
        lab = bench()
        lab.meter('INIT1')
        receipt = N1914AVirtualAdapter(lab).measure('existing-busy')
        self.assert_receipt(receipt)
        self.assertEqual(receipt['code'], 'meter_busy')
        self.assertNotIn('INIT1', commands(receipt))
        self.assertEqual(commands(receipt)[-2:], ['TRIG1:SOUR IMM', 'ABOR1'])
        self.assertEqual(receipt['cleanup']['status'], 'completed')

    def test_post_fetch_error_keeps_value_in_prefix_without_publishing_it(self):
        lab = bench()
        original = lab.meter
        def meter(command):
            reply = original(command)
            if command == 'FETC1?':
                original('*TRG')
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = N1914AVirtualAdapter(lab).measure('fetch-error')
        self.assertEqual(receipt['code'], 'error_queue_nonzero')
        self.assertIsNone(receipt['measurement'])
        self.assertEqual(commands(receipt)[-3:], ['FETC1?', 'SYST:ERR?', 'ABOR1'])
        self.assertEqual(receipt['transcript'][-2]['reply']['error_number'], -211)
        self.assertEqual(next(r['reply']['measurement']['value'] for r in receipt['transcript']
                              if r['command'] == 'FETC1?'), 7.0)
        self.assert_receipt(receipt)

    def test_error_number_and_wire_disagreement_stops_without_further_consumption(self):
        lab = bench()
        lab.meter('*TRG')
        lab.meter('*TRG')
        original = lab.meter
        def meter(command):
            reply = original(command)
            if command == 'SYST:ERR?':
                reply['error_number'] = 0
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = N1914AVirtualAdapter(lab).measure('queue-mismatch')
        self.assertEqual(receipt['code'], 'invalid_reply')
        self.assertEqual(commands(receipt), ['*IDN?', 'SYST:ERR?'])
        self.assertEqual(lab.meter('SYST:ERR?')['error_number'], -211)

    def test_disconnect_recovery_requires_new_id_and_replays_original_failure(self):
        lab = bench()
        adapter = N1914AVirtualAdapter(lab)
        lab.inject_fault('meter_disconnected', True)
        first = adapter.measure('disconnect')
        self.assertEqual(first['code'], 'meter_disconnected')
        self.assertEqual(commands(first), ['*IDN?'])
        lab.inject_fault('meter_disconnected', False)
        with patch.object(lab, 'meter', side_effect=AssertionError('duplicate I/O')):
            self.assertEqual(adapter.measure('disconnect'), first)
        recovered = adapter.measure('recovery')
        self.assertEqual(recovered['status'], 'completed')
        self.assert_receipt(recovered)

    def test_timeout_is_bounded_and_one_shot_abort_allows_next_request(self):
        lab = bench()
        adapter = N1914AVirtualAdapter(lab)
        lab.inject_fault('measurement_stuck', True)
        receipt = adapter.measure('stuck', timeout_ticks=3)
        self.assert_receipt(receipt)
        self.assertEqual((receipt['status'], receipt['code']), ('timeout', 'completion_timeout'))
        self.assertIsNone(receipt['measurement'])
        self.assertEqual(receipt['ticks'], {'start': 0, 'end': 3, 'advance_attempts': 3})
        self.assertEqual(commands(receipt).count('*OPC?'), 4)
        self.assertEqual(commands(receipt).count('ABOR1'), 1)
        self.assertEqual(receipt['cleanup'], {'status': 'completed', 'code': None})
        lab.inject_fault('measurement_stuck', False)
        self.assertEqual(adapter.measure('after-timeout')['status'], 'completed')

    def test_timeout_boundary_completion_is_allowed(self):
        receipt = N1914AVirtualAdapter(bench(measurement_ticks=3)).measure('edge', timeout_ticks=3)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(receipt['ticks']['advance_attempts'], 3)

    def test_declared_maximum_tick_bound_uses_only_one_tick_advances(self):
        receipt = N1914AVirtualAdapter(bench(measurement_ticks=1000)).measure(
            'maximum', timeout_ticks=1000)
        self.assertEqual(receipt['status'], 'completed')
        advances = [r for r in receipt['transcript'] if r['operation'] == 'advance']
        self.assertEqual(len(advances), 1000)
        self.assertEqual({r['ticks'] for r in advances}, {1})
        self.assert_receipt(receipt)

    def test_denied_or_raising_continuation_is_latched_before_any_io(self):
        for result in (False, None, 1, 'yes', RuntimeError('private exception path')):
            calls = []
            def gate():
                calls.append(1)
                if isinstance(result, Exception):
                    raise result
                return result
            lab = bench()
            with patch.object(lab, 'meter', side_effect=AssertionError('must not execute')):
                receipt = N1914AVirtualAdapter(lab).measure('denied', can_continue=gate)
            self.assertEqual(receipt['status'], 'cancelled')
            self.assertEqual(receipt['code'], 'continuation_denied')
            self.assertEqual(receipt['transcript'], [])
            self.assertEqual(receipt['ticks'], {'start': None, 'end': None, 'advance_attempts': 0})
            self.assertEqual(len(calls), 1)
            self.assertNotIn('private exception', json.dumps(receipt))

    def test_cancel_after_init_aborts_without_asking_continuation_again(self):
        for raising in (False, True):
            lab = bench()
            original = lab.meter
            started = False
            gate_calls_after_start = []
            def meter(command):
                nonlocal started
                reply = original(command)
                if command == 'INIT1':
                    started = True
                return reply
            def gate():
                if started:
                    gate_calls_after_start.append(1)
                    if raising:
                        raise RuntimeError('private callback exception')
                    return False
                return True
            with patch.object(lab, 'meter', side_effect=meter):
                receipt = N1914AVirtualAdapter(lab).measure('cancel', can_continue=gate)
            self.assert_receipt(receipt)
            self.assertEqual(receipt['status'], 'cancelled')
            self.assertEqual(commands(receipt)[-2:], ['INIT1', 'ABOR1'])
            self.assertEqual(gate_calls_after_start, [1])
            self.assertEqual(receipt['cleanup']['status'], 'completed')

    def test_publication_fence_does_not_publish_fetched_value_on_cancel(self):
        lab = bench()
        original = lab.meter
        fetched = False
        checked = False
        def meter(command):
            nonlocal fetched, checked
            reply = original(command)
            if command == 'FETC1?':
                fetched = True
            elif fetched and command == 'SYST:ERR?':
                checked = True
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = N1914AVirtualAdapter(lab).measure('fence', can_continue=lambda: not checked)
        self.assertEqual(receipt['status'], 'cancelled')
        self.assertIsNone(receipt['measurement'])
        self.assertEqual(commands(receipt)[-3:], ['FETC1?', 'SYST:ERR?', 'ABOR1'])
        self.assertEqual(next(r['reply']['measurement']['value'] for r in receipt['transcript']
                              if r['command'] == 'FETC1?'), 7.0)

    def test_actual_configuration_change_returns_invalid_not_a_measurement(self):
        lab = bench()
        original = lab.meter
        def meter(command):
            reply = original(command)
            if command == 'INIT1':
                lab.configure_dut('g', 6, 9)
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = N1914AVirtualAdapter(lab).measure('stale')
        self.assertEqual(receipt['code'], 'meter_invalid')
        self.assertIsNone(receipt['measurement'])
        self.assertEqual(commands(receipt)[-2:], ['FETC1?', 'ABOR1'])
        self.assertEqual(receipt['transcript'][-2]['reply']['reason'], 'configuration_changed')

    def test_backend_exceptions_preserve_attempt_and_cleanup_uncertainty(self):
        for failing_command, after_call in [('*IDN?', False), ('INIT1', False), ('INIT1', True)]:
            with self.subTest(command=failing_command, after=after_call):
                lab = bench()
                original = lab.meter
                def meter(command):
                    if command == failing_command:
                        if after_call:
                            original(command)
                        raise RuntimeError('C:/private/secret canary')
                    return original(command)
                with patch.object(lab, 'meter', side_effect=meter):
                    receipt = N1914AVirtualAdapter(lab).measure('exception')
                self.assert_receipt(receipt)
                self.assertEqual(receipt['code'], 'emulator_exception')
                self.assertIsNone(receipt['measurement'])
                attempts = [r for r in receipt['transcript'] if r['command'] == failing_command]
                self.assertEqual(len(attempts), 1)
                self.assertIsNone(attempts[0]['reply'])
                self.assertEqual(attempts[0]['code'], 'emulator_exception')
                self.assertEqual(commands(receipt).count('ABOR1'), int(failing_command == 'INIT1'))
                self.assertNotIn('secret', json.dumps(receipt))

    def test_advance_exception_aborts_once_without_retry(self):
        lab = bench()
        original = lab.advance
        def advance(ticks):
            original(ticks)
            raise RuntimeError('private advance error')
        with patch.object(lab, 'advance', side_effect=advance):
            receipt = N1914AVirtualAdapter(lab).measure('advance-error')
        self.assertEqual(receipt['code'], 'emulator_exception')
        self.assertEqual(receipt['ticks']['advance_attempts'], 1)
        self.assertEqual(receipt['ticks']['end'], 0)
        self.assertEqual(receipt['cleanup']['code'], 'tick_mismatch')
        self.assertEqual(commands(receipt).count('ABOR1'), 1)
        self.assert_receipt(receipt)

    def test_advance_skip_or_repeated_tick_is_rejected_and_not_retried(self):
        for delta in (-1, 1):
            lab = bench()
            original = lab.advance
            def advance(ticks):
                reply = original(ticks)
                reply['tick'] += delta
                return reply
            with patch.object(lab, 'advance', side_effect=advance):
                receipt = N1914AVirtualAdapter(lab).measure('wrong-tick')
            self.assertEqual(receipt['code'], 'tick_mismatch')
            self.assertEqual(receipt['ticks']['advance_attempts'], 1)
            self.assertEqual(commands(receipt).count('ABOR1'), 1)
            self.assertIsNone(receipt['measurement'])
            self.assert_receipt(receipt)

    def test_cleanup_failure_is_separate_from_original_failure(self):
        for mode in ('disconnected', 'exception', 'bad_ack'):
            lab = bench()
            original = lab.meter
            started = False
            def meter(command):
                nonlocal started
                if command == 'ABOR1':
                    if mode == 'exception':
                        raise RuntimeError('private cleanup error')
                    if mode == 'disconnected':
                        lab.inject_fault('meter_disconnected', True)
                    reply = original(command)
                    if mode == 'bad_ack':
                        reply['response'] = '1'
                    return reply
                reply = original(command)
                if command == 'INIT1':
                    started = True
                return reply
            with patch.object(lab, 'meter', side_effect=meter):
                receipt = N1914AVirtualAdapter(lab).measure('cleanup', can_continue=lambda: not started)
            self.assertEqual((receipt['status'], receipt['code']), ('cancelled', 'continuation_denied'))
            self.assertEqual(receipt['cleanup']['status'], 'failed')
            self.assertIsNotNone(receipt['cleanup']['code'])
            self.assertEqual(commands(receipt).count('ABOR1'), 1)
            self.assert_receipt(receipt)

    def test_bad_identity_and_unit_stop_before_acquisition(self):
        for command, value, code in [
            ('*IDN?', 'DGM Virtual,N1911A,SIM-001,SIM-1', 'identity_mismatch'),
            ('UNIT1:POW?', 'W', 'unit_mismatch'),
        ]:
            lab = bench()
            original = lab.meter
            def meter(c):
                reply = original(c)
                if c == command:
                    reply['response'] = value
                return reply
            with patch.object(lab, 'meter', side_effect=meter):
                receipt = N1914AVirtualAdapter(lab).measure('bad-query')
            self.assertEqual(receipt['code'], code)
            self.assertEqual(commands(receipt)[-1], command)
            self.assertNotIn('INIT1', commands(receipt))

    def test_invalid_statuses_and_pending_wire_are_never_success(self):
        for status, response in [('pending', '1'), ('no_data', None), ('unsupported', None),
                                  ('disconnected', None), ('error', None), ('unknown', None)]:
            lab = bench()
            original = lab.meter
            def meter(command):
                reply = original(command)
                if command == '*OPC?':
                    reply.update(status=status, response=response)
                return reply
            with patch.object(lab, 'meter', side_effect=meter):
                receipt = N1914AVirtualAdapter(lab).measure('bad-status')
            self.assertNotEqual(receipt['status'], 'completed')
            self.assertIsNone(receipt['measurement'])
            self.assertNotIn('FETC1?', commands(receipt))
            self.assertEqual(commands(receipt).count('ABOR1'), 1)

    def test_bad_metadata_wire_and_provenance_fail_closed(self):
        mutations = [
            lambda r: r.update(response='+7.000000001E+00'),
            lambda r: r.update(response='NaN'),
            lambda r: r.update(response='Infinity'),
            lambda r: r.update(response='７.0'),
            lambda r: r.update(synthetic=False),
            lambda r: r.update(hardware_verified=True),
            lambda r: r.update(profile_id='other'),
            lambda r: r.update(tick=r['tick'] + 1),
            lambda r: r['measurement'].update(value=math.nan),
            lambda r: r['measurement'].update(value=True),
            lambda r: r['measurement'].update(unit='W'),
            lambda r: r['measurement'].update(measurement_id=0),
            lambda r: r['measurement'].update(measurement_id=True),
            lambda r: r['measurement'].update(setup_revision=-1),
            lambda r: r['measurement'].update(completed_tick=0),
            lambda r: r['measurement'].update(synthetic=False),
            lambda r: r['measurement'].update(private_note='PRIVATE_CANARY'),
            lambda r: r.update(private_note='PRIVATE_CANARY'),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(case=i):
                lab = bench()
                original = lab.meter
                def meter(command):
                    reply = original(command)
                    if command == 'FETC1?':
                        mutate(reply)
                    return reply
                with patch.object(lab, 'meter', side_effect=meter):
                    receipt = N1914AVirtualAdapter(lab).measure('bad-fetch')
                self.assertNotEqual(receipt['status'], 'completed')
                self.assertIsNone(receipt['measurement'])
                self.assertEqual(commands(receipt).count('ABOR1'), 1)
                self.assertNotIn('PRIVATE_CANARY', json.dumps(receipt))
                self.assert_receipt(receipt)

    def test_completed_opc_with_missing_data_is_not_success(self):
        lab = bench()
        original = lab.meter
        def meter(command):
            reply = original(command)
            if command == '*OPC?':
                reply.update(status='ok', response='1')
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = N1914AVirtualAdapter(lab).measure('false-complete')
        self.assertNotEqual(receipt['status'], 'completed')
        self.assertIsNone(receipt['measurement'])

    def test_actual_previous_measurement_id_and_revision_must_not_reverse(self):
        lab = bench()
        adapter = N1914AVirtualAdapter(lab)
        first = adapter.measure('first')
        self.assertEqual(first['status'], 'completed')
        original = lab.meter
        def meter(command):
            reply = original(command)
            if command == 'FETC1?':
                reply['measurement']['measurement_id'] = 1
            return reply
        with patch.object(lab, 'meter', side_effect=meter):
            replayed_data = adapter.measure('second')
        self.assertEqual(replayed_data['code'], 'measurement_id_not_fresh')
        def reversed_revision(command):
            reply = original(command)
            if command == 'FETC1?':
                reply['measurement']['setup_revision'] = 0
            return reply
        with patch.object(lab, 'meter', side_effect=reversed_revision):
            reversed_data = adapter.measure('third')
        self.assertEqual(reversed_data['code'], 'setup_revision_reversed')

    def test_duplicate_receipt_detachment_settings_conflict_and_callback_not_replayed(self):
        lab = bench()
        adapter = N1914AVirtualAdapter(lab)
        first = adapter.measure('same')
        expected = copy.deepcopy(first)
        first['measurement']['value'] = -1
        first['transcript'][0]['reply']['response'] = 'changed'
        with patch.object(lab, 'meter', side_effect=AssertionError('duplicate I/O')):
            replay = adapter.measure('same', can_continue=lambda: self.fail('duplicate callback'))
            self.assertEqual(replay, expected)
            for kwargs in ({'unit': 'W'}, {'timeout_ticks': 21}):
                with self.assertRaisesRegex(ValueError, '^request_conflict$'):
                    adapter.measure('same', **kwargs)
        replay['transcript'].clear()
        self.assertEqual(adapter.measure('same'), expected)

    def test_receipts_are_bounded_without_eviction(self):
        adapter = N1914AVirtualAdapter(bench(measurement_ticks=1))
        first = adapter.measure('r0')
        for n in range(1, 128):
            self.assertEqual(adapter.measure('r' + str(n))['status'], 'completed')
        with self.assertRaisesRegex(ValueError, '^receipt_limit_reached$'):
            adapter.measure('r128')
        self.assertEqual(adapter.measure('r0'), first)

    def test_concurrent_measure_is_busy_and_does_not_touch_lab(self):
        lab = bench()
        adapter = N1914AVirtualAdapter(lab)
        entered, release = threading.Event(), threading.Event()
        result, errors = [], []
        def gate():
            entered.set()
            if not release.wait(5):
                raise RuntimeError('test release missing')
            return True
        def work():
            try:
                result.append(adapter.measure('running', can_continue=gate))
            except Exception as exc:
                errors.append(type(exc).__name__)
        worker = threading.Thread(target=work)
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            with patch.object(lab, 'meter', side_effect=AssertionError('busy I/O')):
                for request_id in ('running', 'other'):
                    with self.assertRaisesRegex(ValueError, '^adapter_busy$'):
                        adapter.measure(request_id)
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result[0]['status'], 'completed')

    def test_returned_measurement_and_transcript_do_not_alias_backend_or_each_other(self):
        lab = bench()
        original = lab.meter
        replies = []
        def meter(command):
            reply = original(command)
            replies.append(reply)
            return reply
        adapter = N1914AVirtualAdapter(lab)
        with patch.object(lab, 'meter', side_effect=meter):
            receipt = adapter.measure('alias')
        frozen = copy.deepcopy(receipt)
        for reply in replies:
            reply.clear()
        self.assertEqual(receipt, frozen)
        receipt['measurement']['value'] = 123
        fetch = next(r['reply'] for r in receipt['transcript'] if r['command'] == 'FETC1?')
        self.assertEqual(fetch['measurement']['value'], 7.0)
        self.assertEqual(adapter.measure('alias'), frozen)

    def test_adapter_never_controls_rf_or_claims_calibration(self):
        for stuck in (False, True):
            lab = bench()
            lab.inject_fault('measurement_stuck', stuck)
            with patch.object(lab, 'start_tx', side_effect=AssertionError('RF control')), \
                 patch.object(lab, 'stop_tx', side_effect=AssertionError('RF control')), \
                 patch.object(lab, 'set_path', side_effect=AssertionError('path control')), \
                 patch.object(lab, 'configure_dut', side_effect=AssertionError('DUT control')):
                receipt = N1914AVirtualAdapter(lab).measure('rf', timeout_ticks=2)
            self.assert_receipt(receipt)
            self.assertEqual(receipt['status'], 'timeout' if stuck else 'completed')
        # ABOR leaves the caller's synthetic TX/path intact.
        lab.inject_fault('measurement_stuck', False)
        lab.meter('INIT1')
        lab.advance(2)
        self.assertEqual(lab.meter('FETC1?')['measurement']['value'], 7.0)


if __name__ == '__main__':
    unittest.main()
