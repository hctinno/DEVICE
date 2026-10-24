"""Synthetic tests; no instrument, vendor binary, or external transport."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import threading
import unittest
from unittest.mock import patch

from labflow import e3632a_virtual_readback as readback
from labflow.virtual_fleet import core, facility, instruments, rf
from labflow.virtual_fleet.integration import create_fleet, inventory_topology


IDS = ('e3632a-ba5f7c3ee5', 'e3632a-ebca10ffe2')
CATALOG = json.loads((Path(__file__).resolve().parents[1] /
                      'virtual_profiles/sm_a176u_unlicensed.json').read_text(encoding='utf-8'))


def fleet_for(identity=IDS[0], *, full=False):
    catalog = copy.deepcopy(CATALOG)
    if not full:
        catalog['profiles'] = [p for p in catalog['profiles'] if p['profile_id'] == identity]
    return create_fleet(catalog, inventory_topology(catalog), seed=0)


def setup(fleet, identity=IDS[0], *, voltage=12, limit=1, resistance=100, enabled=True):
    for name, action, parameters in (
            ('configure', 'configure', {'voltage_v': voltage, 'current_limit_a': limit}),
            ('load', 'set_load', {'resistance_ohm': resistance}),
            ('output', 'output', {'enabled': enabled})):
        assert fleet.execute('fixture:' + name, identity, action, parameters)['status'] == 'ok'


class E3632AReadbackTests(unittest.TestCase):
    def adapter(self, *, identity=IDS[0], full=False, enabled=True, **settings):
        fleet = fleet_for(identity, full=full)
        setup(fleet, identity, enabled=enabled, **settings)
        return fleet, readback.E3632AVirtualReadback(fleet, identity)

    def assert_error(self, code, function, *args):
        with self.assertRaises(ValueError) as caught:
            function(*args)
        self.assertEqual(caught.exception.args, (code,))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)

    def measure_history(self, fleet):
        return [r for r in fleet.history() if r.get('action') == 'measure']

    def test_both_original_profiles_and_exact_dto(self):
        expected = {'schema_version', 'kind', 'request_id', 'device_id', 'profile_id',
                    'manufacturer_as_recorded', 'model', 'profile_sha256', 'status',
                    'reason_codes', 'configured', 'output', 'measurement', 'initial_context',
                    'observation_context', 'measurement_context', 'observation_reads',
                    'observation_method', 'commands', 'simulation_basis', 'observation_scope',
                    'current_authority', 'verification', 'role_policy_defaults', 'resumable'}
        self.assertEqual(len(expected), 25)
        for identity, manufacturer in zip(IDS, ('Agilent', 'H.P')):
            with self.subTest(identity=identity):
                fleet, adapter = self.adapter(identity=identity)
                before = len(fleet.history())
                result = adapter.observe('first')
                self.assertEqual(set(result), expected)
                self.assertEqual(result['manufacturer_as_recorded'], manufacturer)
                self.assertEqual(result['profile_id'], identity)
                self.assertEqual(result['status'], 'observed_synthetic')
                self.assertEqual(result['reason_codes'], [])
                self.assertEqual(result['measurement']['voltage_v'], 12)
                self.assertEqual(result['measurement']['current_a'], .12)
                self.assertEqual(result['measurement']['mode'], 'constant_voltage')
                self.assertEqual(result['observation_reads'], 1)
                self.assertEqual(result['observation_method'], 'fleet.observations')
                self.assertEqual(len(result['commands']), 1)
                self.assertEqual(len(fleet.history()), before + 1)
                self.assertEqual(self.measure_history(fleet)[0]['device_id'], identity)
                self.assertEqual(result['initial_context'], result['observation_context'])
                self.assertEqual(result['measurement_context'], result['observation_context'])

    def test_cc_values_are_not_setpoints(self):
        fleet, adapter = self.adapter(voltage=12, limit=.5, resistance=2)
        result = adapter.observe('cc')
        self.assertEqual(result['configured'], {'voltage_setpoint_v': 12., 'current_limit_a': .5})
        self.assertEqual(result['measurement'], {'voltage_v': 1., 'current_a': .5,
                         'mode': 'constant_current', 'acquisition_tick': fleet._tick,
                         'acquisition_revision': fleet._revision})

    def test_off_zero_markers_are_never_measurements(self):
        fleet, adapter = self.adapter(enabled=False)
        before = fleet.history()
        result = adapter.observe('off')
        self.assertEqual(result['reason_codes'], ['output_disabled'])
        self.assertEqual(result['output'], {'enabled': False, 'valid': False, 'state': 'off'})
        self.assertIsNone(result['measurement'])
        self.assertEqual(result['commands'], [])
        self.assertEqual(fleet.history(), before)
        raw = adapter.author_record('off')['observation_frames'][0]['packet']
        self.assertEqual(raw['values']['outputs']['power']['voltage_v'], 0)

    def test_on_zero_is_valid_only_with_complete_enabled_measurement(self):
        for settings in ({'voltage': 0}, {'limit': 0}):
            with self.subTest(settings=settings):
                fleet, adapter = self.adapter(**settings)
                result = adapter.observe('zero')
                self.assertEqual(result['status'], 'observed_synthetic')
                self.assertEqual(result['measurement']['voltage_v'], 0)
                self.assertEqual(result['measurement']['current_a'], 0)
                self.assertEqual(len(self.measure_history(fleet)), 1)

    def test_protection_output_failure_and_disconnect_do_not_measure(self):
        for fault, reason in (('overcurrent', 'output_protected'),
                              ('output_failure', 'output_protected'),
                              ('communication_loss', 'device_unavailable')):
            with self.subTest(fault=fault):
                fleet, adapter = self.adapter()
                fleet.author_control('fixture:fault', IDS[0], fault, True)
                result = adapter.observe('fault')
                self.assertEqual(result['status'], 'unconfirmed')
                self.assertEqual(result['reason_codes'], [reason])
                self.assertIsNone(result['measurement'])
                self.assertEqual(self.measure_history(fleet), [])
                self.assertEqual(result['commands'], [])
                if fault == 'communication_loss':
                    self.assertIsNone(result['configured'])
                    self.assertIsNone(result['output'])
                self.assertNotIn(fault, json.dumps(result))

    def test_model_and_physical_boundaries_are_explicit(self):
        _, adapter = self.adapter()
        result = adapter.observe('limits')
        self.assertEqual(result['simulation_basis'], 'existing_role_domain_model')
        self.assertEqual(result['observation_scope'], 'historical_observation')
        self.assertIs(result['current_authority'], False)
        self.assertIs(result['resumable'], False)
        self.assertEqual(result['role_policy_defaults'], {
            'voltage_max_v': 60, 'current_max_a': 10,
            'scope': 'generic_role_policy_not_model_ratings'})
        self.assertEqual(result['verification'], {
            'synthetic': True, 'hardware_verified': False, 'ai_verified': False,
            'vendor_binary_executed': False, 'output_off_verified': False,
            'rf_off_verified': False, 'safe_state_verified': False,
            'model_limits': 'not_assessed', 'calibration': 'not_assessed',
            'oem_support': 'not_assessed', 'firmware_options': 'not_assessed',
            'physical_model': 'not_assessed'})

    def test_author_is_separate_selected_raw_and_detached(self):
        _, adapter = self.adapter(full=True)
        result = adapter.observe('author')
        author = adapter.author_record('author')
        self.assertEqual(set(author), {'schema_version', 'kind', 'request_id', 'scope',
                                     'operator_receipt', 'observation_frames',
                                     'command_frames', 'diagnostics'})
        self.assertEqual(author['operator_receipt'], result)
        self.assertEqual(author['scope'], 'trusted_author_only')
        self.assertNotIn('devices', author['observation_frames'][0]['packet'])
        self.assertEqual(len(author['command_frames']), 1)
        author['observation_frames'][0]['packet']['values'].clear()
        author['operator_receipt']['measurement']['voltage_v'] = 999
        self.assertEqual(adapter.author_record('author')['operator_receipt'], result)

    def test_id_replay_is_historical_with_no_observation_or_command(self):
        fleet, adapter = self.adapter()
        original = adapter.observe('same')
        fleet.execute('later:off', IDS[0], 'output', {'enabled': False})
        fleet.advance('later:tick', 1)
        before = fleet.history()
        # Historical replay does not touch a now-invalid live path.
        fleet.observations = lambda: self.fail('historical replay reobserved')
        self.assertEqual(adapter.observe('same'), original)
        self.assertEqual(fleet.history(), before)
        replay = adapter.observe('same')
        replay['measurement']['current_a'] = 99
        replay['commands'].clear()
        self.assertEqual(adapter.observe('same'), original)

    def test_128_receipts_no_eviction_and_no_command_on_saturation(self):
        fleet, adapter = self.adapter(enabled=False)
        first = adapter.observe('item0')
        for n in range(1, 128):
            adapter.observe('item' + str(n))
        before = fleet.history()
        self.assert_error('receipt_limit_reached', adapter.observe, 'item128')
        self.assertEqual(adapter.observe('item0'), first)
        self.assertEqual(fleet.history(), before)

    def test_invalid_ids_are_fixed_errors_without_object_hooks(self):
        class Trap:
            def __str__(self):
                raise AssertionError('called repr')
        fleet = fleet_for()
        for identity in (None, 1, True, '', '한글', 'a' * 129, 'x\n', Trap()):
            self.assert_error('invalid_device_id', readback.E3632AVirtualReadback, fleet, identity)
        _, adapter = self.adapter()
        for request in (None, 1, True, '', 'a b', 'a' * 129, '한글', Trap()):
            self.assert_error('invalid_request_id', adapter.observe, request)
            self.assert_error('invalid_request_id', adapter.author_record, request)
        self.assert_error('readback_record_not_found', adapter.author_record, 'missing')

    def test_duck_subclass_wrong_target_profile_and_factory_are_rejected(self):
        class Duck:
            def __getattr__(self, name):
                raise AssertionError('duck was inspected')
        class SubFleet(core.VirtualFleet):
            pass
        self.assert_error('invalid_virtual_fleet', readback.E3632AVirtualReadback, Duck(), IDS[0])
        self.assert_error('invalid_virtual_fleet', readback.E3632AVirtualReadback,
                          object.__new__(SubFleet), IDS[0])
        fleet = fleet_for(full=True)
        self.assert_error('unsupported_supply_profile', readback.E3632AVirtualReadback,
                          fleet, next(k for k in fleet._devices if k not in IDS))
        self.assert_error('unsupported_supply_profile', readback.E3632AVirtualReadback, fleet, 'unknown')
        fleet = fleet_for()
        class SubSupply(facility.PowerSupply):
            pass
        fleet._devices[IDS[0]].__class__ = SubSupply
        self.assert_error('unsafe_callpath', readback.E3632AVirtualReadback, fleet, IDS[0])

    def test_original_profile_metadata_cannot_be_extended_or_aliased(self):
        for field, value in (('manufacturer', 'Keysight'), ('model', 'E3632A '),
                             ('simulation_parameters', {'voltage_max_v': 99}),
                             ('evidence_refs', [])):
            with self.subTest(field=field):
                fleet = fleet_for()
                fleet._profiles[IDS[0]][field] = value
                self.assert_error('unsupported_supply_profile',
                                  readback.E3632AVirtualReadback, fleet, IDS[0])

    def test_instance_and_class_helpers_changed_before_call_are_not_invoked(self):
        for owner, name in ((core.VirtualFleet, 'observations'), (core, '_json_copy'),
                            (facility.PowerSupply, '_electrical'),
                            (facility._Facility, 'perform')):
            fleet = fleet_for()
            with patch.object(owner, name, side_effect=AssertionError('unsafe called')) as fake:
                self.assert_error('unsafe_callpath', readback.E3632AVirtualReadback, fleet, IDS[0])
                fake.assert_not_called()
        fleet = fleet_for()
        fleet._devices[IDS[0]].perform = lambda *a, **k: self.fail('unsafe instance')
        self.assert_error('unsafe_callpath', readback.E3632AVirtualReadback, fleet, IDS[0])

    def test_change_after_binding_is_frozen_failure_without_io(self):
        fleet, adapter = self.adapter()
        with patch.object(core.VirtualFleet, 'observations',
                          side_effect=AssertionError('must not call')) as fake:
            result = adapter.observe('unsafe')
            fake.assert_not_called()
        self.assertEqual(result['reason_codes'], ['unsafe_callpath'])
        self.assertEqual(result['observation_reads'], 0)
        self.assertEqual(result['commands'], [])
        self.assertEqual(adapter.observe('unsafe'), result)

    def test_unrelated_node_callback_is_rejected_before_propagation(self):
        fleet, adapter = self.adapter(full=True)
        other = next(k for k in fleet._devices if k not in IDS)
        fleet._devices[other].advance = lambda **kw: self.fail('unrelated callback')
        result = adapter.observe('unsafe-node')
        self.assertEqual(result['reason_codes'], ['unsafe_callpath'])
        self.assertEqual(result['observation_reads'], 0)
        self.assertEqual(self.measure_history(fleet), [])

    def test_function_code_replacement_is_detected(self):
        fleet, adapter = self.adapter()
        function = core.VirtualFleet.observations
        original = function.__code__
        def replacement(self):
            raise AssertionError('replaced code executed')
        try:
            function.__code__ = replacement.__code__
            result = adapter.observe('code')
        finally:
            function.__code__ = original
        self.assertEqual(result['reason_codes'], ['unsafe_callpath'])

    def test_profile_rebind_is_not_silently_followed(self):
        fleet, adapter = self.adapter(full=True)
        fleet._nodes[IDS[0]]['profile_id'] = IDS[1]
        result = adapter.observe('rebind')
        self.assertEqual(result['reason_codes'], ['binding_changed'])
        self.assertEqual(result['commands'], [])
        self.assertEqual(result['observation_reads'], 0)

    def test_stale_acquisition_tick_or_revision_is_unconfirmed(self):
        for key in ('acquisition_tick', 'acquisition_revision'):
            fleet, adapter = self.adapter()
            fleet._snapshots[IDS[0]]['values']['outputs']['power'][key] += 1
            result = adapter.observe('stale')
            self.assertEqual(result['reason_codes'], ['context_mismatch'])
            self.assertIsNone(result['measurement'])
            self.assertEqual(result['commands'], [])

    def test_partial_unknown_and_wrong_types_do_not_leak_to_policy(self):
        variants = (
            lambda p: p['values'].update(private_canary='DO_NOT_COPY'),
            lambda p: p['values'].pop('voltage_setpoint_v'),
            lambda p: p['values']['outputs']['power'].update(valid=1),
            lambda p: p['values']['outputs']['power'].update(voltage_v=True),
            lambda p: p['values']['outputs']['power'].pop('current_a'),
            lambda p: p['values']['outputs']['power'].update(mode='CV'),
        )
        for change in variants:
            fleet, adapter = self.adapter()
            change(fleet._snapshots[IDS[0]])
            result = adapter.observe('invalid')
            self.assertEqual(result['status'], 'unconfirmed')
            self.assertEqual(result['reason_codes'], ['observation_packet_invalid'])
            self.assertNotIn('DO_NOT_COPY', json.dumps(result))
            self.assertIsNone(result['measurement'])
            self.assertEqual(result['commands'], [])

    def test_canary_is_preserved_only_in_trusted_author(self):
        fleet, adapter = self.adapter()
        fleet._snapshots[IDS[0]]['values']['private_canary'] = 'DO_NOT_COPY'
        result = adapter.observe('canary')
        self.assertNotIn('DO_NOT_COPY', json.dumps(result))
        self.assertIn('DO_NOT_COPY', json.dumps(adapter.author_record('canary')))

    def test_stored_snapshot_cannot_replace_current_measurement(self):
        fleet, adapter = self.adapter()
        # Host-only corruption: snapshot remains 12V/.12A; actual role becomes 6V/.06A.
        fleet._devices[IDS[0]].voltage = 6.
        result = adapter.observe('changed')
        self.assertEqual(result['reason_codes'], ['measurement_mismatch'])
        self.assertIsNone(result['measurement'])
        self.assertEqual(len(result['commands']), 1)
        self.assertEqual(len(self.measure_history(fleet)), 1)
        self.assertEqual(adapter.author_record('changed')['command_frames'][0]['packet']
                         ['values']['voltage_v'], 6)

    def test_no_network_process_file_or_tick_io_during_observe(self):
        fleet, adapter = self.adapter(full=True)
        tick, revision = fleet._tick, fleet._revision
        with patch('builtins.open', side_effect=AssertionError('file I/O')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network I/O')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process I/O')):
            result = adapter.observe('pure')
            adapter.author_record('pure')
        self.assertEqual(result['status'], 'observed_synthetic')
        self.assertEqual((fleet._tick, fleet._revision), (tick, revision))
        self.assertEqual([r['action'] for r in self.measure_history(fleet)], ['measure'])

    def test_concurrent_same_or_other_ids_are_busy_without_second_dispatch(self):
        fleet, adapter = self.adapter()
        entered, release = threading.Event(), threading.Event()
        original = readback._validate_observation
        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise AssertionError('test worker timeout')
            return original(*args, **kwargs)
        outputs = []
        with patch.object(readback, '_validate_observation', side_effect=blocked):
            worker = threading.Thread(target=lambda: outputs.append(adapter.observe('same')))
            worker.start()
            try:
                self.assertTrue(entered.wait(5))
                for identity in ('same', 'other'):
                    self.assert_error('readback_busy', adapter.observe, identity)
                self.assert_error('readback_busy', adapter.author_record, 'same')
            finally:
                release.set()
                worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(adapter.observe('same'), outputs[0])
        self.assertEqual(len(self.measure_history(fleet)), 1)

    def test_different_adapters_do_not_replay_fleet_child_id(self):
        fleet, first = self.adapter()
        second = readback.E3632AVirtualReadback(fleet, IDS[0])
        a, b = first.observe('same'), second.observe('same')
        self.assertNotEqual(a['commands'][0]['request_id'], b['commands'][0]['request_id'])
        self.assertEqual(len(self.measure_history(fleet)), 2)

    def test_busy_fleet_lock_is_not_waited_on(self):
        fleet, adapter = self.adapter()
        entered, release = threading.Event(), threading.Event()
        def hold():
            with fleet._lock:
                entered.set()
                release.wait(5)
        worker = threading.Thread(target=hold)
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assert_error('readback_busy', adapter.observe, 'busy')
        finally:
            release.set()
            worker.join(5)
        self.assertEqual(adapter.observe('busy')['status'], 'observed_synthetic')

    def test_reachable_library_helpers_are_checked_before_use(self):
        for owner, name in ((readback.math, 'log10'), (readback.hashlib, 'sha256'),
                            (readback.copy, 'deepcopy')):
            fleet, adapter = self.adapter()
            with patch.object(owner, name, side_effect=AssertionError('unsafe helper')) as fake:
                result = adapter.observe('library')
                fake.assert_not_called()
            self.assertEqual(result['reason_codes'], ['unsafe_callpath'])
            self.assertEqual(result['observation_reads'], 0)

    def test_role_metadata_mutation_is_rejected(self):
        fleet, adapter = self.adapter()
        fleet._role_actions['power_supply']['measure']['parameters']['hidden'] = {'type': 'object'}
        result = adapter.observe('metadata')
        self.assertEqual(result['reason_codes'], ['unsafe_callpath'])
        self.assertEqual(result['commands'], [])

    def test_snapshot_provenance_partial_envelope_and_context_validators(self):
        fleet, adapter = self.adapter()
        snapshot = fleet.observations()
        context = {'tick': fleet._tick, 'setup_revision': fleet._revision}
        changes = (
            lambda s, p: s.update(synthetic=False),
            lambda s, p: s.update(hardware_verified=True),
            lambda s, p: s.update(extra='CANARY'),
            lambda s, p: p.update(device_id='other'),
            lambda s, p: p.update(profile_id=IDS[1]),
            lambda s, p: p.update(role='signal_generator'),
            lambda s, p: p.pop('status'),
            lambda s, p: p.update(hardware_verified=True),
            lambda s, p: p['values']['outputs']['power'].update(source_id='other'),
            lambda s, p: p['values'].update(current_limit_a=float('nan')),
        )
        for change in changes:
            broken = copy.deepcopy(snapshot)
            change(broken, broken['devices'][IDS[0]])
            with self.assertRaises(readback._Invalid):
                readback._validate_observation(broken, IDS[0], IDS[0], context)
        for level in ('root', 'device'):
            broken = copy.deepcopy(snapshot)
            (broken if level == 'root' else broken['devices'][IDS[0]])['tick'] += 1
            with self.assertRaises(readback._Stop) as caught:
                readback._validate_observation(broken, IDS[0], IDS[0], context)
            self.assertEqual(caught.exception.reason, 'context_mismatch')
        self.assertEqual(self.measure_history(fleet), [])

    def test_packet_and_whole_snapshot_budgets_are_separate(self):
        for full, target, size in ((False, IDS[0], 20000), (True, IDS[1], 270000)):
            fleet, adapter = self.adapter(full=full)
            fleet._snapshots[target]['values']['canary'] = 'z' * size
            result = adapter.observe('bytes')
            self.assertEqual(result['reason_codes'], ['observation_budget_exceeded'])
            self.assertEqual(result['observation_reads'], 1)
            self.assertEqual(result['commands'], [])
            self.assertIsNone(adapter.author_record('bytes')['observation_frames'][0]['packet'])
        fleet, adapter = self.adapter()
        nested = 1
        for _ in range(17):
            nested = [nested]
        fleet._snapshots[IDS[0]]['values']['nested'] = nested
        result = adapter.observe('depth')
        self.assertEqual(result['reason_codes'], ['observation_budget_exceeded'])
        self.assertEqual(result['commands'], [])

    def test_finite_json_types_bytes_depth_and_packed_author_boundaries(self):
        value = {'x': '한'}
        data = readback._pack(value, 100, 2)
        self.assertEqual(readback._pack(value, len(data), 2), data)
        with self.assertRaises(readback._Budget):
            readback._pack(value, len(data) - 1, 2)
        self.assertEqual(readback._pack([[0]], 100, 2), b'[[0]]')
        with self.assertRaises(readback._Budget):
            readback._pack([[0]], 100, 1)
        for invalid in ({1: 2}, {'x': float('inf')}, {'x': (1,)}, {'x': object()}):
            with self.assertRaises(readback._Invalid):
                readback._pack(invalid, 100, 4)
        with self.assertRaises(readback._Budget):
            readback._pack([0] * 100001, 1000000, 4)
        # Individually acceptable raw packet does not waive wrapper depth/byte limits.
        packet = {'x': 'a' * 16000}
        readback._pack(packet, 16384, 16)
        with self.assertRaises(readback._Budget):
            readback._seal({}, {'packets': [packet] * 5})
        nested = 1
        for _ in range(16):
            nested = [nested]
        readback._pack(nested, 16384, 16)
        for _ in range(9):
            nested = [nested]
        with self.assertRaises(readback._Budget):
            readback._seal({}, nested)

    def test_read_followed_by_exception_retains_attempt_and_original_frame(self):
        fleet, adapter = self.adapter()
        with patch.object(readback, '_validate_observation', side_effect=RuntimeError('PRIVATE ERROR')):
            result = adapter.observe('read-failure')
        self.assertEqual(result['reason_codes'], ['observation_packet_invalid'])
        self.assertEqual(result['observation_reads'], 1)
        self.assertEqual(result['commands'], [])
        author = adapter.author_record('read-failure')
        self.assertIsNotNone(author['observation_frames'][0]['packet'])
        self.assertNotIn('PRIVATE ERROR', json.dumps(author))
        self.assertEqual(adapter.observe('read-failure'), result)
        self.assertEqual(self.measure_history(fleet), [])

    def test_snapshot_exception_is_historical_without_retry(self):
        fleet, adapter = self.adapter()
        # Exact built-in observations raises on missing stored snapshot.
        del fleet._snapshots[IDS[0]]
        result = adapter.observe('snapshot-exception')
        self.assertEqual(result['reason_codes'], ['observation_exception'])
        self.assertEqual(result['observation_reads'], 1)
        self.assertEqual(result['commands'], [])
        fleet._propagate()
        self.assertEqual(adapter.observe('snapshot-exception'), result)
        self.assertIsNone(result['measurement'])

    def test_after_actual_measure_packet_exception_preserves_command_without_retry(self):
        for exception, reason in ((readback._Budget(), 'measurement_budget_exceeded'),
                                  (RuntimeError('PRIVATE'), 'measurement_packet_invalid')):
            fleet, adapter = self.adapter()
            original = readback._packet
            def fail_measure(value, *args):
                if type(value) is dict and 'setup_changed' in value:
                    raise exception
                return original(value, *args)
            with patch.object(readback, '_packet', side_effect=fail_measure):
                result = adapter.observe('measure-packet-failure')
            self.assertEqual(result['reason_codes'], [reason])
            self.assertEqual(len(result['commands']), 1)
            self.assertTrue(result['commands'][0]['attempted'])
            self.assertEqual(len(self.measure_history(fleet)), 1)
            self.assertIsNone(result['measurement'])
            self.assertEqual(adapter.observe('measure-packet-failure'), result)
            self.assertEqual(len(self.measure_history(fleet)), 1)
            author = adapter.author_record('measure-packet-failure')
            self.assertEqual(len(author['command_frames']), 1)
            self.assertEqual(author['command_frames'][0]['error'], reason)
            self.assertNotIn('PRIVATE', json.dumps(author))

    def test_execute_exception_after_perform_is_never_reported_as_not_attempted(self):
        fleet, adapter = self.adapter()
        # Exact built-in execute runs perform and propagate, then this malformed
        # author-owned accounting container raises before returning a packet.
        fleet._status_counts[IDS[0]] = []
        result = adapter.observe('execute-exception')
        self.assertEqual(result['reason_codes'], ['measure_exception'])
        self.assertIn('measure', fleet._exercised[IDS[0]])
        self.assertEqual(len(result['commands']), 1)
        self.assertEqual(self.measure_history(fleet), [])
        self.assertIsNone(result['measurement'])
        self.assertEqual(adapter.observe('execute-exception'), result)
        self.assertEqual(adapter.author_record('execute-exception')['command_frames'][0]['error'],
                         'measure_exception')

    def test_after_actual_measure_seal_failure_keeps_raw_and_attempt_prefix(self):
        fleet, adapter = self.adapter()
        with patch.object(readback, '_seal', side_effect=RuntimeError('PRIVATE PACK ERROR')):
            result = adapter.observe('seal-failure')
        self.assertEqual(result['status'], 'unconfirmed')
        self.assertEqual(result['reason_codes'], ['preservation_failed'])
        self.assertIsNone(result['measurement'])
        self.assertEqual(result['observation_reads'], 1)
        self.assertEqual(len(result['commands']), 1)
        self.assertEqual(len(self.measure_history(fleet)), 1)
        author = adapter.author_record('seal-failure')
        self.assertIsNotNone(author['command_frames'][0]['packet'])
        self.assertEqual(author['operator_receipt'], result)
        self.assertNotIn('PRIVATE PACK ERROR', json.dumps(author))
        self.assertEqual(adapter.observe('seal-failure'), result)
        self.assertEqual(len(self.measure_history(fleet)), 1)

    def test_measurement_reply_validation_rejects_partial_stale_wrong_profile_and_canary(self):
        fleet, adapter = self.adapter()
        good = adapter.observe('good')
        raw = adapter.author_record('good')['command_frames'][0]['packet']
        changes = (
            lambda p: p['values'].pop('current_a'),
            lambda p: p['values'].update(voltage_v=True),
            lambda p: p['values'].update(current_a=-1),
            lambda p: p['values'].update(current_a=float('inf')),
            lambda p: p['values'].update(mode='unknown'),
            lambda p: p.update(profile_id=IDS[1]),
            lambda p: p.update(synthetic=False),
            lambda p: p.update(canary='DO_NOT_COPY'),
        )
        for change in changes:
            broken = copy.deepcopy(raw)
            change(broken)
            with self.assertRaises(readback._Invalid):
                readback._validate_measurement(broken, IDS[0], IDS[0], good['observation_context'])
        for change in (lambda p: p.update(tick=p['tick'] + 1),
                       lambda p: p.update(setup_changed=True),
                       lambda p: p['values'].update(acquisition_revision=999)):
            broken = copy.deepcopy(raw)
            change(broken)
            with self.assertRaises(readback._Stop) as caught:
                readback._validate_measurement(broken, IDS[0], IDS[0], good['observation_context'])
            self.assertEqual(caught.exception.reason, 'context_mismatch')

    def test_context_change_during_measure_is_not_a_fresh_snapshot_or_safe_state(self):
        fleet, adapter = self.adapter()
        original = readback._packet
        def changed(value, *args):
            packet = original(value, *args)
            if type(value) is dict and 'setup_changed' in value:
                fleet._revision += 1
            return packet
        with patch.object(readback, '_packet', side_effect=changed):
            result = adapter.observe('revision-change')
        self.assertEqual(result['reason_codes'], ['context_mismatch'])
        self.assertIsNone(result['measurement'])
        self.assertEqual(len(self.measure_history(fleet)), 1)
        self.assertEqual(result['observation_reads'], 1)
        self.assertEqual(adapter.observe('revision-change'), result)

    def test_author_host_recovery_is_explicit_and_new_id_only(self):
        fleet, adapter = self.adapter()
        fleet.author_control('fault:on', IDS[0], 'overcurrent', True)
        first = adapter.observe('protected')
        fleet.author_control('fault:off', IDS[0], 'overcurrent', False)
        self.assertEqual(adapter.observe('still-protected')['reason_codes'], ['output_protected'])
        fleet.execute('fixture:recover', IDS[0], 'clear_trip', {})
        self.assertEqual(adapter.observe('recovered-off')['reason_codes'], ['output_disabled'])
        fleet.execute('fixture:reenable', IDS[0], 'output', {'enabled': True})
        self.assertEqual(adapter.observe('reenabled')['status'], 'observed_synthetic')
        self.assertEqual(adapter.observe('protected'), first)

    def test_valid_id_length_128_is_preserved_and_child_is_bounded(self):
        _, adapter = self.adapter()
        result = adapter.observe('X' * 128)
        self.assertEqual(result['request_id'], 'X' * 128)
        self.assertLessEqual(len(result['commands'][0]['request_id']), 128)

    def test_mutated_instance_data_never_executes_comparison_or_mapping_hooks(self):
        calls = []
        class Trap(dict):
            def __ne__(self, other):
                calls.append('comparison')
                return True
            def get(self, *args):
                calls.append('get')
                return super().get(*args)
        for field in ('policy', '_nodes'):
            fleet, adapter = self.adapter()
            if field == 'policy':
                fleet._devices[IDS[0]].policy = Trap()
            else:
                fleet._nodes = Trap(fleet._nodes)
            result = adapter.observe('typed')
            self.assertEqual(result['reason_codes'], ['unsafe_callpath'])
            self.assertEqual(calls, [])
            self.assertEqual(result['observation_reads'], 0)

    def test_library_alias_replacement_cannot_break_fixed_failure_serialization(self):
        for module, name in ((readback.json, 'dumps'), (readback.json, 'loads'),
                             (readback.math, 'isfinite')):
            fleet, adapter = self.adapter()
            with patch.object(module, name, side_effect=AssertionError('unsafe library')) as fake:
                result = adapter.observe('serialization')
                author = adapter.author_record('serialization')
                fake.assert_not_called()
            self.assertEqual(result['reason_codes'], ['unsafe_callpath'])
            self.assertEqual(result['observation_reads'], 0)
            self.assertEqual(author['operator_receipt'], result)

    def test_interrupt_after_measure_is_preserved_before_propagating_interrupt(self):
        fleet, adapter = self.adapter()
        original = readback._packet
        def interrupted(value, *args):
            if type(value) is dict and 'setup_changed' in value:
                raise KeyboardInterrupt
            return original(value, *args)
        with patch.object(readback, '_packet', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                adapter.observe('interrupt')
        result = adapter.observe('interrupt')
        self.assertEqual(result['reason_codes'], ['preservation_failed'])
        self.assertEqual(result['observation_reads'], 1)
        self.assertEqual(len(result['commands']), 1)
        self.assertEqual(len(self.measure_history(fleet)), 1)
        self.assertIsNone(result['measurement'])


if __name__ == '__main__':
    unittest.main()
