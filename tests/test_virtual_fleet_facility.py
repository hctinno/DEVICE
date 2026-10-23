import copy
import math
import unittest


def profile(role, **policy):
    ports = {
        'power_supply': {'inputs': {}, 'outputs': {'power': 'power'}},
        'temperature_chamber': {'inputs': {'power': 'power'}, 'outputs': {'environment': 'environment'}},
        'position_controller': {'inputs': {'power': 'power', 'control': 'control'},
                                'outputs': {'position': 'position', 'control': 'control'}},
        'antenna_mast': {'inputs': {'power': 'power', 'control': 'control'}, 'outputs': {'position': 'position'}},
        'turntable': {'inputs': {'power': 'power', 'control': 'control'}, 'outputs': {'position': 'position'}},
        'inspection_microscope': {'inputs': {'power': 'power', 'sample': 'data'}, 'outputs': {'data': 'data'}},
    }
    return {'profile_id': 'synthetic-' + role, 'model': 'Synthetic acceptance fixture',
            'manufacturer': 'Simulation', 'role': role, 'variant': '', 'evidence_refs': [],
            'simulation_basis': 'explicit synthetic policy', 'capability_scope': 'state acceptance',
            'simulation_parameters': policy, 'ports': ports[role]}


class FacilityTests(unittest.TestCase):
    def setUp(self):
        from labflow.virtual_fleet.facility import DEVICE_FACTORIES, ROLE_ACTIONS
        from labflow.virtual_fleet.core import VirtualFleet
        self.factories, self.actions, self.fleet_type = DEVICE_FACTORIES, ROLE_ACTIONS, VirtualFleet

    def device(self, role, **policy):
        return self.factories[role](profile(role, **policy), 17)

    def perform(self, device, action, tick=0, revision=0, inputs=None, **parameters):
        return device.perform(action, parameters, tick=tick, setup_revision=revision, inputs=inputs or {})

    def advance(self, device, tick, revision=0, inputs=None):
        device.advance(tick=tick, setup_revision=revision, inputs=inputs or {})
        return device.observation(tick=tick, setup_revision=revision)

    def fleet(self, profiles, nodes=None, edges=None):
        nodes = nodes or [{'id': p['role'], 'profile_id': p['profile_id']} for p in profiles]
        return self.fleet_type({'profiles': profiles}, {'devices': nodes, 'connections': edges or []},
                               factories=self.factories, role_actions=self.actions, seed=17)

    def test_every_facility_role_exports_the_exact_device_interface_and_actions(self):
        roles = {'power_supply', 'temperature_chamber', 'position_controller', 'antenna_mast', 'turntable', 'inspection_microscope'}
        self.assertEqual(set(self.factories), roles)
        self.assertEqual(set(self.actions), roles)
        for role in roles:
            device = self.device(role)
            for method in ('perform', 'advance', 'observation', 'author_control'):
                self.assertTrue(callable(getattr(device, method)))
            self.assertEqual(self.perform(device, 'nonexistent')['status'], 'unsupported')

    def test_supply_calculates_constant_voltage_and_current_limits_from_load(self):
        device = self.device('power_supply')
        self.assertEqual(self.perform(device, 'measure')['status'], 'invalid')
        self.perform(device, 'configure', voltage_v=10, current_limit_a=1)
        self.perform(device, 'set_load', resistance_ohm=20)
        self.perform(device, 'output', enabled=True)
        result = self.perform(device, 'measure')
        self.assertEqual(result['values']['voltage_v'], 10)
        self.assertEqual(result['values']['current_a'], .5)
        self.assertEqual(result['values']['mode'], 'constant_voltage')
        self.perform(device, 'set_load', resistance_ohm=5)
        result = self.perform(device, 'measure')
        self.assertEqual(result['values']['voltage_v'], 5)
        self.assertEqual(result['values']['current_a'], 1)
        self.assertEqual(result['values']['mode'], 'constant_current')

    def test_supply_profile_limits_output_off_and_invalid_inputs_do_not_mutate(self):
        device = self.device('power_supply', voltage_max_v=12)
        for args in [{'voltage_v': 13, 'current_limit_a': 1}, {'voltage_v': True, 'current_limit_a': 1},
                     {'voltage_v': math.nan, 'current_limit_a': 1}, {'voltage_v': 1, 'current_limit_a': -1},
                     {'voltage_v': 1, 'current_limit_a': 1, 'extra': 2}]:
            self.assertEqual(self.perform(device, 'configure', **args)['status'], 'invalid')
        self.assertEqual(self.perform(device, 'set_load', resistance_ohm=0)['status'], 'invalid')
        self.assertEqual(self.perform(device, 'output', enabled='yes')['status'], 'invalid')
        self.assertFalse(self.advance(device, 0)['values']['outputs']['power']['valid'])

    def test_supply_protection_requires_fault_removal_and_explicit_recovery(self):
        device = self.device('power_supply')
        self.perform(device, 'configure', voltage_v=10, current_limit_a=1)
        self.perform(device, 'output', enabled=True)
        device.author_control('overcurrent', True)
        self.assertEqual(self.advance(device, 1)['status'], 'error')
        self.assertEqual(self.perform(device, 'clear_trip', tick=1)['status'], 'error')
        device.author_control('overcurrent', False)
        self.assertEqual(self.advance(device, 2)['status'], 'error')
        self.assertEqual(self.perform(device, 'clear_trip', tick=2)['status'], 'ok')
        self.assertEqual(self.perform(device, 'measure', tick=2)['status'], 'invalid')
        self.perform(device, 'output', tick=2, enabled=True)
        self.assertEqual(self.perform(device, 'measure', tick=2)['status'], 'ok')

    def test_supply_fault_is_a_symptom_and_never_a_false_zero_measurement(self):
        device = self.device('power_supply')
        self.perform(device, 'output', enabled=True)
        device.author_control('output_failure', True)
        observation = self.advance(device, 1)
        self.assertEqual(observation['status'], 'error')
        self.assertNotIn('voltage_v', self.perform(device, 'measure', tick=1)['values'])
        self.assertNotIn('output_failure', repr(observation))

    def test_environment_moves_over_ticks_and_requires_stable_dwell(self):
        device = self.device('temperature_chamber', initial_temperature_c=20, initial_humidity_percent=50,
                             temperature_rate_c_per_tick=2, humidity_rate_percent_per_tick=5, stable_ticks=2)
        self.perform(device, 'configure', temperature_c=24, humidity_percent=60)
        self.assertEqual(self.perform(device, 'start')['status'], 'pending')
        one = self.advance(device, 1)
        self.assertEqual(one['values']['temperature_c'], 22)
        self.assertFalse(one['values']['outputs']['environment']['valid'])
        self.assertEqual(self.advance(device, 2)['status'], 'pending')
        self.assertEqual(self.advance(device, 3)['status'], 'ok')
        self.assertEqual(self.perform(device, 'wait_stable', tick=3)['status'], 'ok')
        self.assertEqual(self.perform(device, 'sample', tick=3)['values']['temperature_c'], 24)

    def test_environment_configuration_change_restarts_stability_and_stop_cancels(self):
        device = self.device('temperature_chamber', stable_ticks=1)
        self.perform(device, 'start')
        self.advance(device, 1)
        self.assertEqual(self.perform(device, 'wait_stable', tick=1)['status'], 'ok')
        self.perform(device, 'configure', tick=1, temperature_c=30, humidity_percent=55)
        self.assertEqual(self.perform(device, 'wait_stable', tick=1)['status'], 'pending')
        self.perform(device, 'stop', tick=1)
        self.advance(device, 10)
        self.assertEqual(self.perform(device, 'wait_stable', tick=10)['status'], 'invalid')

    def test_environment_stall_timeout_sensor_failure_and_recovery(self):
        device = self.device('temperature_chamber', timeout_ticks=3)
        self.perform(device, 'configure', temperature_c=40, humidity_percent=70)
        device.author_control('stuck', True)
        self.perform(device, 'start')
        self.assertEqual(self.advance(device, 3)['status'], 'error')
        device.author_control('stuck', False)
        self.perform(device, 'reset', tick=3)
        self.perform(device, 'start', tick=3)
        self.assertEqual(self.advance(device, 4)['status'], 'pending')
        device.author_control('sensor_failure', True)
        result = self.advance(device, 5)
        self.assertEqual(result['status'], 'error')
        self.assertNotIn('temperature_c', result['values'])
        self.assertNotIn('sensor_failure', repr(result))
        device.author_control('sensor_failure', False)
        self.perform(device, 'reset', tick=5)
        self.assertEqual(self.perform(device, 'start', tick=5)['status'], 'pending')

    def test_environment_limits_and_infinite_policy_are_rejected(self):
        device = self.device('temperature_chamber')
        for temp, humidity in [(1000, 50), (20, 101), (True, 50), (math.inf, 50)]:
            self.assertEqual(self.perform(device, 'configure', temperature_c=temp, humidity_percent=humidity)['status'], 'invalid')
        with self.assertRaises(ValueError):
            self.device('temperature_chamber', temperature_rate_c_per_tick=0)
        with self.assertRaises(ValueError):
            self.device('temperature_chamber', stable_ticks=True)

    def test_motion_each_role_moves_and_stops_without_teleporting(self):
        for role, target, speed in [('turntable', 90, 30), ('position_controller', 90, 30), ('antenna_mast', 2.5, .5)]:
            device = self.device(role, speed_per_tick=speed)
            self.assertEqual(self.perform(device, 'move', position=target)['status'], 'pending')
            initial = self.advance(device, 0)['values']['position']
            middle = self.advance(device, 1)['values']['position']
            self.assertGreater(middle, initial)
            self.assertLess(middle, target)
            self.perform(device, 'stop', tick=1)
            self.assertEqual(self.advance(device, 10)['values']['position'], middle)

    def test_motion_completion_and_homing_use_declared_units_and_limits(self):
        for role, target in [('turntable', 90), ('antenna_mast', 2)]:
            device = self.device(role)
            self.perform(device, 'move', position=target)
            complete = self.advance(device, 10)
            self.assertEqual(complete['status'], 'ok')
            self.assertEqual(complete['values']['position'], target)
            self.assertEqual(complete['values']['unit'], 'm' if role == 'antenna_mast' else 'deg')
            self.perform(device, 'home', tick=10)
            self.assertEqual(self.advance(device, 30)['values']['position'], 1 if role == 'antenna_mast' else 0)

    def test_motion_out_of_range_invalid_speed_and_limits_leave_current_position(self):
        device = self.device('turntable')
        for position in [-1, 361, True, math.nan]:
            self.assertEqual(self.perform(device, 'move', position=position)['status'], 'invalid')
        self.assertEqual(self.perform(device, 'configure', speed_per_tick=0)['status'], 'invalid')
        self.assertEqual(self.advance(device, 3)['values']['position'], 0)
        with self.assertRaises(ValueError):
            self.device('turntable', position_min=3, position_max=2)

    def test_motion_interlock_jam_limit_and_reset_do_not_clear_author_fault(self):
        for fault in ['jammed', 'interlock_open', 'limit_switch']:
            device = self.device('turntable', timeout_ticks=3)
            device.author_control(fault, True)
            self.perform(device, 'move', position=90)
            self.assertEqual(self.advance(device, 4)['status'], 'error')
            self.assertEqual(self.perform(device, 'clear_trip', tick=4)['status'], 'error')
            self.perform(device, 'reset', tick=4)
            self.assertNotEqual(self.perform(device, 'move', tick=4, position=90)['status'], 'ok')
            device.author_control(fault, False)
            self.perform(device, 'clear_trip', tick=4)
            self.perform(device, 'move', tick=4, position=90)
            self.assertEqual(self.advance(device, 10)['values']['position'], 90)

    def test_communication_interruption_stops_motion_and_needs_new_command(self):
        device = self.device('turntable')
        self.perform(device, 'move', position=120)
        self.advance(device, 1)
        device.author_control('communication_loss', True)
        self.assertEqual(self.advance(device, 2)['status'], 'disconnected')
        self.assertEqual(self.perform(device, 'home', tick=2)['status'], 'disconnected')
        device.author_control('communication_loss', False)
        self.perform(device, 'clear_trip', tick=2)
        self.assertEqual(self.advance(device, 10)['values']['position'], 30)
        self.perform(device, 'move', tick=10, position=120)
        self.assertEqual(self.advance(device, 14)['values']['position'], 120)

    def test_error_queue_read_is_fifo_and_does_not_fix_an_active_condition(self):
        device = self.device('turntable')
        self.perform(device, 'move', position=-1)
        self.perform(device, 'configure', speed_per_tick=0)
        first = self.perform(device, 'read_errors')['values']['error']
        second = self.perform(device, 'read_errors')['values']['error']
        self.assertNotEqual(first['code'], '0')
        self.assertNotEqual(second['code'], '0')
        self.assertEqual(self.perform(device, 'read_errors')['values']['error']['code'], '0')

    def test_fault_validation_and_direct_api_validation_are_strict(self):
        for role in self.factories:
            device = self.device(role)
            with self.assertRaises(ValueError):
                device.author_control('unknown', True)
            with self.assertRaises(ValueError):
                device.author_control('communication_loss', 'true')
            self.assertEqual(device.perform('reset', {'unexpected': 1}, tick=0, setup_revision=0, inputs={})['status'], 'invalid')

    def test_supply_environment_connection_blocks_start_until_power_exists(self):
        supply = profile('power_supply')
        chamber = profile('temperature_chamber', requires_power=True, stable_ticks=1)
        edges = [{'source': {'device_id': 'power_supply', 'port': 'power'},
                  'target': {'device_id': 'temperature_chamber', 'port': 'power'}, 'kind': 'power'}]
        fleet = self.fleet([supply, chamber], edges=edges)
        self.assertEqual(fleet.execute('bad-start', 'temperature_chamber', 'start')['status'], 'invalid')
        fleet.execute('configure', 'power_supply', 'configure', {'voltage_v': 12, 'current_limit_a': 1})
        fleet.execute('power-on', 'power_supply', 'output', {'enabled': True})
        self.assertEqual(fleet.execute('start', 'temperature_chamber', 'start')['status'], 'pending')
        fleet.advance('settle', 1)
        self.assertEqual(fleet.observations()['devices']['temperature_chamber']['status'], 'ok')
        fleet.execute('power-off', 'power_supply', 'output', {'enabled': False})
        chamber_observation = fleet.observations()['devices']['temperature_chamber']
        self.assertEqual(chamber_observation['status'], 'invalid')
        self.assertFalse(chamber_observation['values']['outputs']['environment']['valid'])

    def test_controller_to_mast_is_a_control_edge_with_unit_validation(self):
        controller = profile('position_controller', position_unit='m', position_min=1, position_max=4,
                             initial_position=1, speed_per_tick=.5)
        mast = profile('antenna_mast', requires_control=True, speed_per_tick=.5)
        edge = {'source': {'device_id': 'position_controller', 'port': 'control'},
                'target': {'device_id': 'antenna_mast', 'port': 'control'}, 'kind': 'control'}
        fleet = self.fleet([controller, mast], edges=[edge])
        fleet.execute('move', 'position_controller', 'move', {'position': 2})
        fleet.advance('complete', 2)
        observation = fleet.observations()['devices']['antenna_mast']
        self.assertEqual(observation['values']['position'], 2)
        self.assertEqual(observation['status'], 'ok')
        fleet.execute('stop', 'position_controller', 'stop')
        self.assertFalse(fleet.observations()['devices']['antenna_mast']['values']['outputs']['position']['valid'])

    def test_facility_twin_runtime_reproduces_actions_fault_recovery_and_outputs(self):
        fleets = [self.fleet([profile('power_supply'), profile('turntable')]) for _ in range(2)]
        for fleet in fleets:
            fleet.execute('v', 'power_supply', 'configure', {'voltage_v': 7, 'current_limit_a': 1})
            fleet.execute('on', 'power_supply', 'output', {'enabled': True})
            fleet.execute('move', 'turntable', 'move', {'position': 90})
            fleet.advance('one', 1)
            fleet.author_control('hidden', 'turntable', 'interlock_open', True)
            fleet.author_control('recover', 'turntable', 'interlock_open', False)
            fleet.execute('clear', 'turntable', 'clear_trip')
            fleet.execute('again', 'turntable', 'move', {'position': 90})
            fleet.advance('done', 4)
        self.assertEqual(fleets[0].observations(), fleets[1].observations())
        self.assertEqual(fleets[0].history(), fleets[1].history())

    def test_microscope_acquires_only_a_synthetic_sample_after_virtual_completion(self):
        device = self.device('inspection_microscope')
        self.assertEqual(self.perform(device, 'acquire')['status'], 'invalid')
        self.perform(device, 'load_sample', sample_id='synthetic-wire', feature_size_um=15, surface_contrast=.8)
        self.assertEqual(self.perform(device, 'acquire')['status'], 'pending')
        self.advance(device, 1)
        self.assertEqual(self.perform(device, 'fetch', tick=1)['status'], 'pending')
        result = self.advance(device, 2)
        measurement = result['values']['measurement']
        self.assertEqual(measurement['feature_size_um'], 15)
        self.assertEqual(measurement['image_feature_size_um'], 150)
        self.assertEqual(measurement['acquisition_tick'], 2)
        self.assertTrue(measurement['synthetic_sample'])
        self.assertEqual(result['values']['image_interpretation'], 'not_performed')
        self.assertEqual(result['values']['scope'], 'auxiliary cable validation')
        self.assertNotIn('pass', repr(result).lower())
        self.assertTrue(result['values']['outputs']['data']['valid'])

    def test_microscope_configuration_and_revision_invalidate_pending_and_completed_acquisition(self):
        fleet = self.fleet([profile('inspection_microscope'), profile('power_supply')])
        fleet.execute('load', 'inspection_microscope', 'load_sample',
                      {'sample_id': 'synthetic-wire', 'feature_size_um': 12, 'surface_contrast': .9})
        fleet.execute('acquire', 'inspection_microscope', 'acquire')
        fleet.advance('finish', 2)
        self.assertEqual(fleet.execute('fetch', 'inspection_microscope', 'fetch')['status'], 'ok')
        fleet.execute('unrelated-change', 'power_supply', 'configure', {'voltage_v': 9, 'current_limit_a': 1})
        self.assertEqual(fleet.execute('stale', 'inspection_microscope', 'fetch')['status'], 'invalid')
        fleet.execute('again', 'inspection_microscope', 'acquire')
        fleet.execute('optics-change', 'inspection_microscope', 'configure',
                      {'magnification': 20, 'focus_um': 100, 'illumination_percent': 60})
        fleet.advance('finish-again', 3)
        self.assertEqual(fleet.execute('pending-invalidated', 'inspection_microscope', 'fetch')['status'], 'invalid')

    def test_microscope_blur_darkness_abort_and_fault_recovery_never_invent_a_reading(self):
        device = self.device('inspection_microscope', timeout_ticks=3)
        self.perform(device, 'load_sample', sample_id='synthetic', feature_size_um=10, surface_contrast=.9)
        self.perform(device, 'configure', magnification=20, focus_um=200, illumination_percent=50)
        self.perform(device, 'acquire')
        self.assertEqual(self.advance(device, 2)['status'], 'invalid')
        self.assertNotIn('measurement', self.perform(device, 'fetch', tick=2)['values'])
        self.perform(device, 'configure', tick=2, magnification=20, focus_um=100, illumination_percent=0)
        self.assertEqual(self.perform(device, 'acquire', tick=2)['status'], 'invalid')
        self.perform(device, 'configure', tick=2, magnification=20, focus_um=100, illumination_percent=50)
        self.perform(device, 'acquire', tick=2)
        self.perform(device, 'abort', tick=2)
        self.assertNotIn('measurement', self.advance(device, 5)['values'])
        device.author_control('acquisition_stall', True)
        self.perform(device, 'acquire', tick=5)
        self.assertEqual(self.advance(device, 8)['status'], 'error')
        device.author_control('acquisition_stall', False)
        self.perform(device, 'reset', tick=8)
        self.perform(device, 'acquire', tick=8)
        self.assertEqual(self.advance(device, 10)['status'], 'ok')
        device.author_control('optics_failure', True)
        self.assertEqual(self.advance(device, 11)['status'], 'error')
        self.assertNotIn('measurement', device.observation(tick=11, setup_revision=0)['values'])

    def test_microscope_sample_input_missing_invalid_and_changed_sample_are_explicit(self):
        device = self.device('inspection_microscope', requires_sample=True)
        self.assertEqual(self.perform(device, 'acquire')['status'], 'invalid')
        valid = {'sample': {'valid': True, 'sample_id': 'synthetic', 'feature_size_um': 11, 'surface_contrast': .8}}
        self.assertEqual(self.perform(device, 'acquire', inputs=valid)['status'], 'pending')
        self.assertEqual(self.advance(device, 2, inputs=valid)['status'], 'ok')
        changed = copy.deepcopy(valid); changed['sample']['feature_size_um'] = 12
        self.assertEqual(self.advance(device, 2, inputs=changed)['status'], 'invalid')
        invalid = {'sample': {'valid': False}}
        self.assertEqual(self.perform(device, 'acquire', tick=2, inputs=invalid)['status'], 'invalid')

    def test_facility_rejects_unknown_policy_or_port_instead_of_silently_ignoring_it(self):
        with self.assertRaises(ValueError):
            self.device('power_supply', unsupported_setting=123)
        p = profile('power_supply'); p['ports']['outputs']['mystery'] = 'power'
        with self.assertRaises(ValueError):
            self.factories['power_supply'](p, 0)

    def test_controller_stop_during_motion_is_cancellation_and_new_command_can_restart(self):
        controller, table = profile('position_controller'), profile('turntable', requires_control=True)
        edge = {'source': {'device_id': 'position_controller', 'port': 'control'},
                'target': {'device_id': 'turntable', 'port': 'control'}, 'kind': 'control'}
        fleet = self.fleet([controller, table], edges=[edge])
        fleet.execute('move', 'position_controller', 'move', {'position': 180})
        fleet.advance('moving', 1)
        fleet.execute('stop', 'position_controller', 'stop')
        self.assertNotEqual(fleet.observations()['devices']['turntable']['status'], 'error')
        fleet.advance('stopped', 3)
        self.assertEqual(fleet.observations()['devices']['turntable']['values']['position'], 30)
        fleet.execute('resume', 'position_controller', 'move', {'position': 90})
        fleet.advance('complete', 3)
        self.assertEqual(fleet.observations()['devices']['turntable']['values']['position'], 90)

    def test_microscope_unrepresentable_synthetic_feature_never_emits_infinite_measurement(self):
        device = self.device('inspection_microscope')
        self.perform(device, 'load_sample', sample_id='synthetic-large', feature_size_um=1e308, surface_contrast=.9)
        self.perform(device, 'acquire')
        result = self.advance(device, 2)
        self.assertEqual(result['status'], 'invalid')
        self.assertNotIn('measurement', result['values'])

    def test_microscope_local_sample_cannot_override_authoritative_connected_sample(self):
        for required in [False, True]:
            device = self.device('inspection_microscope', requires_sample=required)
            source = {'sample': {'valid': True, 'sample_id': 'upstream-a', 'feature_size_um': 11, 'surface_contrast': .9}}
            self.advance(device, 0, inputs=source)
            local = self.perform(device, 'load_sample', inputs=source, sample_id='local-b',
                                 feature_size_um=999, surface_contrast=.9)
            self.assertEqual(local['status'], 'invalid')
            self.perform(device, 'acquire', inputs=source)
            result = self.advance(device, 2, inputs=source)
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(result['values']['measurement']['feature_size_um'], 11)
        device = self.device('inspection_microscope', requires_sample=True)
        self.assertEqual(self.perform(device, 'load_sample', sample_id='local', feature_size_um=1,
                                      surface_contrast=.9)['status'], 'invalid')


if __name__ == '__main__':
    unittest.main()
