"""Synthetic RF role acceptance; no real serials, traces, or report values."""
import copy
import importlib
import importlib.util
import json
import math
import unittest


PORTS = {
    'dut': {'inputs': {'power': 'power', 'environment': 'environment', 'control': 'control'}, 'outputs': {'rf': 'rf'}},
    'power_sensor': {'inputs': {'rf': 'rf'}, 'outputs': {'measurement': 'measurement'}},
    'attenuator': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf'}},
    'coupler': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf', 'coupled': 'rf'}},
    'splitter': {'inputs': {'rf': 'rf'}, 'outputs': {'rf_1': 'rf', 'rf_2': 'rf'}},
    'antenna': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf'}},
    'amplifier': {'inputs': {'rf': 'rf', 'power': 'power'}, 'outputs': {'rf': 'rf'}},
    'filter': {'inputs': {'rf': 'rf'}, 'outputs': {'rf': 'rf'}},
    'rf_switch': {'inputs': {'rf_1': 'rf', 'rf_2': 'rf', 'control': 'control'}, 'outputs': {'rf': 'rf'}},
    'lisn': {'inputs': {'rf': 'rf', 'power': 'power'}, 'outputs': {'rf': 'rf', 'power': 'power'}},
}


def signal(**changes):
    return {'status': 'ok', 'valid': True, 'frequency_hz': 1e9, 'power_dbm': 10.0,
            'bandwidth_hz': 1e6, 'duty_cycle': .25, 'crest_factor_db': 6.0,
            'modulation': 'QPSK', 'source_id': 'synthetic-source', **changes}


def power(**changes):
    return {'enabled': True, 'valid': True, 'voltage_v': 5.0, **changes}


def environment(**changes):
    return {'valid':True,'stable':True,'temperature_c':25.0,'humidity_percent':45.0,**changes}


class RFTestCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_fleet'), 'RF package has not been created')
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_fleet.rf'), 'RF roles are not implemented')
        self.rf = importlib.import_module('labflow.virtual_fleet.rf')

    def device(self, role, *, model='Synthetic', parameters=None, ports=None):
        profile = {'profile_id': 'fixture-'+role, 'model': model, 'manufacturer': 'SYNTHETIC',
                   'role': role, 'ports': copy.deepcopy(ports or PORTS[role]),
                   'simulation_parameters': parameters or {}, 'evidence_refs': ['synthetic-fixture']}
        return self.rf.DEVICE_FACTORIES[role](profile, 7)

    def perform(self, device, action, parameters=None, *, tick=0, revision=1, inputs=None):
        return device.perform(action, parameters or {}, tick=tick, setup_revision=revision, inputs=inputs or {})

    def observe(self, device, inputs, *, tick=1, revision=1):
        device.advance(tick=tick, setup_revision=revision, inputs=inputs)
        return device.observation(tick=tick, setup_revision=revision)


class RFRoleTests(RFTestCase):
    def test_all_assigned_roles_export_real_action_and_port_contracts(self):
        self.assertEqual(set(self.rf.DEVICE_FACTORIES), set(PORTS))
        self.assertEqual(set(self.rf.ROLE_ACTIONS), set(PORTS))
        for role in PORTS:
            with self.subTest(role=role):
                self.assertIn('configure', self.rf.ROLE_ACTIONS[role])
                self.assertIn('read', self.rf.ROLE_ACTIONS[role])
                self.assertEqual(self.rf.ROLE_PORTS[role], PORTS[role])

    def test_fixed_attenuation_changes_power_once_and_rejects_reprogramming(self):
        device = self.device('attenuator', model='8493-SYNTHETIC')
        self.assertEqual(self.perform(device, 'configure', {'attenuation_db': 7})['status'], 'ok')
        result = self.observe(device, {'rf': signal()})
        self.assertEqual(result['values']['outputs']['rf']['power_dbm'], 3)
        self.assertEqual(self.perform(device, 'set_attenuation', {'attenuation_db': 5})['status'], 'unsupported')
        self.assertEqual(self.observe(device, {'rf': signal()})['values']['outputs']['rf']['power_dbm'], 3)

    def test_step_attenuation_only_accepts_declared_synthetic_steps(self):
        device = self.device('attenuator', model='8494-SYNTHETIC', parameters={'attenuator_mode': 'step'})
        self.assertEqual(self.perform(device, 'configure', {'attenuation_db': 2, 'steps_db': [0,2,4]})['status'], 'ok')
        self.assertEqual(self.perform(device, 'set_attenuation', {'attenuation_db': 3})['status'], 'invalid')
        self.assertEqual(self.perform(device, 'set_attenuation', {'attenuation_db': 4})['status'], 'ok')
        self.assertEqual(self.observe(device, {'rf': signal()})['values']['outputs']['rf']['power_dbm'], 6)

    def test_missing_loss_policy_never_becomes_ideal_zero_loss(self):
        device = self.device('attenuator')
        result = self.observe(device, {'rf': signal()})
        self.assertEqual(result['status'], 'invalid')
        self.assertNotIn('rf', result['values']['outputs'])

    def test_loss_table_interpolates_and_rejects_extrapolation(self):
        device = self.device('filter')
        config = {'loss_db': 0, 'band_min_hz': 1e8, 'band_max_hz': 2e9,
                  'loss_table': [{'frequency_hz':5e8,'loss_db':1},{'frequency_hz':1.5e9,'loss_db':3}]}
        self.assertEqual(self.perform(device,'configure',config)['status'],'ok')
        self.assertEqual(self.observe(device,{'rf':signal()})['values']['outputs']['rf']['power_dbm'],8)
        result=self.observe(device,{'rf':signal(frequency_hz=1.8e9)})
        self.assertEqual(result['status'],'invalid'); self.assertNotIn('rf',result['values']['outputs'])

    def test_invalid_tables_and_nonfinite_values_do_not_mutate_configuration(self):
        for bad in (True, float('nan'), float('inf'), -1):
            with self.subTest(value=bad):
                device=self.device('attenuator')
                self.assertEqual(self.perform(device,'configure',{'attenuation_db':bad})['status'],'invalid')
        device=self.device('filter')
        bad={'loss_db':1,'band_min_hz':1e8,'band_max_hz':2e9,
             'loss_table':[{'frequency_hz':1e9,'loss_db':1},{'frequency_hz':1e9,'loss_db':2}]}
        self.assertEqual(self.perform(device,'configure',bad)['status'],'invalid')

    def test_missing_and_invalid_rf_never_become_power_zero(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        self.assertEqual(self.observe(device,{})['status'],'disconnected')
        for packet in (signal(valid=False),signal(frequency_hz=True),signal(duty_cycle=0),signal(power_dbm=float('nan'))):
            result=self.observe(device,{'rf':packet})
            self.assertEqual(result['status'],'invalid'); self.assertNotIn('rf',result['values']['outputs'])

    def test_unrepresentable_rf_number_is_invalid_without_crashing_advance(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        result=self.observe(device,{'rf':signal(power_dbm=10**1000)})
        self.assertEqual(result['status'],'invalid'); self.assertFalse(result['values']['outputs'])

    def test_overflowing_occupied_band_is_not_accepted_as_finite_rf(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        result=self.observe(device,{'rf':signal(frequency_hz=1.7e308,bandwidth_hz=1.7e308)})
        self.assertEqual(result['status'],'invalid'); self.assertFalse(result['values']['outputs'])

    def test_two_and_four_way_splitters_conserve_power(self):
        for ways in (2,4):
            ports={'inputs':{'rf':'rf'},'outputs':{'rf_'+str(i):'rf' for i in range(1,ways+1)}}
            device=self.device('splitter',ports=ports)
            self.assertEqual(self.perform(device,'configure',{'ways':ways,'loss_db':1})['status'],'ok')
            outputs=self.observe(device,{'rf':signal()})['values']['outputs']
            self.assertEqual(set(outputs),set(ports['outputs']))
            self.assertAlmostEqual(sum(10**(v['power_dbm']/10) for v in outputs.values()),10**(.9))
            self.assertAlmostEqual(outputs['rf_1']['power_dbm'],9-10*math.log10(ways))

    def test_splitter_rejects_way_count_that_drops_declared_ports(self):
        device=self.device('splitter')
        self.assertEqual(self.perform(device,'configure',{'ways':4,'loss_db':1})['status'],'invalid')

    def test_coupler_outputs_are_distinct_and_do_not_create_energy(self):
        device=self.device('coupler')
        self.assertEqual(self.perform(device,'configure',{'through_loss_db':1,'coupling_db':10})['status'],'ok')
        outputs=self.observe(device,{'rf':signal()})['values']['outputs']
        self.assertEqual(outputs['rf']['power_dbm'],9); self.assertEqual(outputs['coupled']['power_dbm'],0)
        self.assertLessEqual(sum(10**(v['power_dbm']/10) for v in outputs.values()),10)

    def test_amplifier_needs_power_and_marks_overload_without_saturation_pass(self):
        device=self.device('amplifier')
        self.perform(device,'configure',{'gain_db':5,'max_input_dbm':15})
        self.assertEqual(self.observe(device,{'rf':signal()})['status'],'disconnected')
        good=self.observe(device,{'rf':signal(),'power':power()})
        self.assertEqual(good['values']['outputs']['rf']['power_dbm'],15)
        bad=self.observe(device,{'rf':signal(power_dbm=20),'power':power()})
        self.assertEqual(bad['status'],'error'); self.assertNotIn('rf',bad['values']['outputs'])
        self.perform(device,'reset')
        self.assertEqual(self.observe(device,{'rf':signal(),'power':power()})['values']['outputs']['rf']['power_dbm'],15)

    def test_antenna_has_explicit_gain_and_link_loss_policy(self):
        device=self.device('antenna'); self.perform(device,'configure',{'gain_db':3,'loss_db':1})
        self.assertEqual(self.observe(device,{'rf':signal()})['values']['outputs']['rf']['power_dbm'],12)

    def test_filter_rejects_out_of_band_signal_without_normal_zero_result(self):
        device=self.device('filter'); self.perform(device,'configure',{'loss_db':1,'band_min_hz':.8e9,'band_max_hz':1.2e9})
        result=self.observe(device,{'rf':signal(frequency_hz=2e9)})
        self.assertEqual(result['status'],'invalid'); self.assertNotIn('rf',result['values']['outputs'])

    def test_rf_switch_waits_then_routes_selected_input_and_recovers(self):
        device=self.device('rf_switch'); self.perform(device,'configure',{'loss_db':1,'settling_ticks':2})
        self.assertEqual(self.perform(device,'select_path',{'input_port':'rf_2'})['status'],'pending')
        inputs={'rf_1':signal(),'rf_2':signal(power_dbm=20)}
        self.assertEqual(self.observe(device,inputs,tick=1)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=2)['values']['outputs']['rf']['power_dbm'],19)
        device.author_control('disconnect',True)
        self.assertEqual(device.observation(tick=2,setup_revision=1)['status'],'disconnected')
        device.author_control('disconnect',False)
        self.assertEqual(self.observe(device,inputs,tick=3)['values']['outputs']['rf']['power_dbm'],19)

    def test_controller_only_never_invents_rf_carrier(self):
        ports={'inputs':{'control':'control'},'outputs':{'control':'control'}}
        device=self.device('rf_switch',model='FBSM-01B',ports=ports,parameters={'controller_only':True})
        self.perform(device,'configure',{'settling_ticks':1})
        self.perform(device,'select_path',{'input_port':'rf_1'})
        result=self.observe(device,{},tick=1)
        self.assertEqual(result['status'],'ok')
        self.assertEqual(set(result['values']['outputs']),{'control'})
        self.assertEqual(result['values']['outputs']['control']['selected_input'],'rf_1')
        self.assertNotIn('power_dbm',json.dumps(result))

    def test_removing_controller_route_invalidates_previous_selection(self):
        ports={'inputs':{'control':'control'},'outputs':{'control':'control'}}
        device=self.device('rf_switch',ports=ports,parameters={'controller_only':True})
        self.perform(device,'configure',{'routes':['rf_1','rf_2']})
        self.perform(device,'select_path',{'input_port':'rf_1'})
        self.assertEqual(self.observe(device,{},tick=1)['status'],'ok')
        self.assertEqual(self.perform(device,'configure',{'routes':['rf_2']},tick=1)['status'],'ok')
        result=self.observe(device,{},tick=2)
        self.assertEqual(result['status'],'invalid'); self.assertFalse(result['values']['outputs'])
        self.perform(device,'select_path',{'input_port':'rf_2'},tick=2)
        self.assertEqual(self.observe(device,{},tick=3)['values']['outputs']['control']['selected_input'],'rf_2')

    def test_lisn_keeps_power_and_rf_channels_distinct(self):
        device=self.device('lisn'); self.perform(device,'configure',{'loss_db':2})
        outputs=self.observe(device,{'power':power(),'rf':signal()})['values']['outputs']
        self.assertEqual(outputs['rf']['power_dbm'],8); self.assertEqual(outputs['power']['voltage_v'],5)
        self.assertEqual(self.observe(device,{'rf':signal()})['status'],'disconnected')

    def test_unknown_action_and_unknown_parameter_are_not_success(self):
        device=self.device('attenuator')
        self.assertEqual(self.perform(device,'SCPI_SEND',{'command':'*RST'})['status'],'unsupported')
        self.assertEqual(self.perform(device,'configure',{'attenuation_db':1,'unknown':True})['status'],'invalid')

    def test_unchanged_configuration_does_not_claim_setup_changed(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        self.assertFalse(self.perform(device,'configure',{'attenuation_db':1})['setup_changed'])

    def test_untrusted_extra_rf_fields_and_hidden_faults_are_not_echoed(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        result=self.observe(device,{'rf':signal(hidden_expected_answer='do not expose')})
        self.assertNotIn('hidden_expected_answer',json.dumps(result))
        device.author_control('no_output',True)
        result=self.observe(device,{'rf':signal()})
        self.assertNotIn('no_output',json.dumps(result)); self.assertNotIn('rf',result['values']['outputs'])
        device.author_control('no_output',False)
        self.assertEqual(self.observe(device,{'rf':signal()})['status'],'ok')

    def test_connected_upstream_without_output_is_invalid_not_zero_or_unconnected(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        result=self.observe(device,{'rf':{'valid':False,'reason':'output_unavailable','source_id':'fixture','upstream_status':'ok'}})
        self.assertEqual(result['status'],'invalid'); self.assertNotIn('rf',result['values']['outputs'])

    def test_invalid_clock_does_not_mutate_a_working_configuration(self):
        device=self.device('attenuator'); self.perform(device,'configure',{'attenuation_db':1})
        self.observe(device,{'rf':signal()})
        bad=self.perform(device,'configure',{'attenuation_db':2},tick=-1)
        self.assertEqual(bad['status'],'invalid')
        self.assertEqual(self.observe(device,{'rf':signal()},tick=2)['values']['outputs']['rf']['power_dbm'],9)
        with self.assertRaises(ValueError):device.observation(tick=2,setup_revision=True)

    def test_explicit_controller_selection_can_drive_a_physical_matrix(self):
        device=self.device('rf_switch',parameters={'requires_control':True,'control_selects_route':True})
        self.perform(device,'configure',{'loss_db':1,'settling_ticks':1})
        inputs={'control':{'valid':True,'enabled':True,'selected_input':'rf_2'},
                'rf_1':signal(),'rf_2':signal(power_dbm=20)}
        self.assertEqual(self.observe(device,inputs,tick=0)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=1)['values']['outputs']['rf']['power_dbm'],19)
        inputs['control']['selected_input']='rf_1'
        self.assertEqual(self.observe(device,inputs,tick=2,revision=2)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=3,revision=2)['values']['outputs']['rf']['power_dbm'],9)

    def test_controller_reversal_cancels_uncommitted_route_and_old_deadline(self):
        device=self.device('rf_switch',parameters={'requires_control':True,'control_selects_route':True})
        self.perform(device,'configure',{'loss_db':1,'settling_ticks':2})
        inputs={'control':{'valid':True,'enabled':True,'selected_input':'rf_1'},
                'rf_1':signal(),'rf_2':signal(power_dbm=20)}
        self.assertEqual(self.observe(device,inputs,tick=0)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=2)['values']['outputs']['rf']['power_dbm'],9)
        inputs['control']['selected_input']='rf_2'
        self.assertEqual(self.observe(device,inputs,tick=3)['status'],'pending')
        inputs['control']['selected_input']='rf_1'
        reversed_observation=self.observe(device,inputs,tick=4)
        self.assertEqual(self.observe(device,inputs,tick=5)['values']['outputs']['rf']['power_dbm'],9)
        self.assertEqual(reversed_observation['status'],'ok')
        self.assertEqual(reversed_observation['values']['outputs']['rf']['power_dbm'],9)
        inputs['control']['selected_input']='rf_2'
        self.assertEqual(self.observe(device,inputs,tick=6)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=7)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=8)['values']['outputs']['rf']['power_dbm'],19)


class DUTSensorTests(RFTestCase):
    def configure_dut(self,device,**changes):
        params={key:value for key,value in signal().items() if key in
                {'frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','crest_factor_db'}}
        params.update(changes)
        return self.perform(device,'configure',params)

    def test_dut_waits_for_startup_and_emits_configured_on_interval_power(self):
        device=self.device('dut',parameters={'startup_ticks':2})
        self.assertEqual(self.configure_dut(device)['status'],'ok')
        inputs={'power':power(),'environment':environment()}
        self.assertEqual(self.perform(device,'start',inputs=inputs)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=1)['status'],'pending')
        result=self.observe(device,inputs,tick=2)
        self.assertEqual(result['status'],'ok')
        packet=result['values']['outputs']['rf']
        self.assertEqual(packet['power_dbm'],10)
        self.assertEqual(packet['duty_cycle'],.25)
        self.assertEqual(packet['crest_factor_db'],6)
        self.assertEqual(packet['source_id'],'fixture-dut')

    def test_dut_power_loss_requires_a_new_start_after_recovery(self):
        device=self.device('dut'); self.configure_dut(device)
        inputs={'power':power(),'environment':environment()}
        self.assertEqual(self.perform(device,'start',inputs={'environment':environment()})['status'],'disconnected')
        self.perform(device,'start',inputs=inputs)
        self.assertIn('rf',self.observe(device,inputs,tick=1)['values']['outputs'])
        bad=self.observe(device,{'power':power(enabled=False),'environment':environment()},tick=2)
        self.assertNotIn('rf',bad['values']['outputs'])
        self.assertNotIn('rf',self.observe(device,inputs,tick=3)['values']['outputs'])
        self.perform(device,'start',inputs=inputs,tick=3)
        self.assertIn('rf',self.observe(device,inputs,tick=4)['values']['outputs'])

    def test_dut_environment_wait_has_no_implicit_rf_output(self):
        device=self.device('dut',parameters={'startup_ticks':2}); self.configure_dut(device)
        waiting={'power':power(),'environment':environment(stable=False)}
        self.assertEqual(self.perform(device,'start',inputs=waiting)['status'],'pending')
        self.assertEqual(self.observe(device,waiting,tick=10)['status'],'pending')
        ready={'power':power(),'environment':environment()}
        self.assertEqual(self.observe(device,ready,tick=11)['status'],'pending')
        self.assertIn('rf',self.observe(device,ready,tick=13)['values']['outputs'])

    def test_dut_control_gate_is_required_only_when_declared(self):
        device=self.device('dut',parameters={'requires_control':True}); self.configure_dut(device)
        inputs={'power':power(),'environment':environment()}
        self.assertEqual(self.perform(device,'start',inputs=inputs)['status'],'disconnected')
        inputs['control']={'valid':True,'enabled':True}
        self.assertEqual(self.perform(device,'start',inputs=inputs)['status'],'pending')
        self.assertIn('rf',self.observe(device,inputs,tick=1)['values']['outputs'])

    def test_invalid_duty_crest_and_numeric_types_are_rejected_before_start(self):
        for changes in ({'duty_cycle':0},{'duty_cycle':1.1},{'frequency_hz':True},{'power_dbm':float('nan')},
                        {'crest_factor_db':-1}):
            with self.subTest(changes=changes):
                self.assertEqual(self.configure_dut(self.device('dut'),**changes)['status'],'invalid')
        device=self.device('dut')
        params={key:value for key,value in signal().items() if key in
                {'frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation'}}
        self.assertEqual(self.perform(device,'configure',params)['status'],'invalid')

    def test_cw_zero_crest_requires_explicit_synthetic_policy(self):
        params={'frequency_hz':1e9,'power_dbm':0,'bandwidth_hz':1e3,'duty_cycle':1,'modulation':'CW'}
        self.assertEqual(self.perform(self.device('dut'),'configure',params)['status'],'invalid')
        device=self.device('dut',parameters={'assume_cw_crest_zero':True})
        self.assertEqual(self.perform(device,'configure',params)['status'],'ok')
        inputs={'power':power(),'environment':environment()}; self.perform(device,'start',inputs=inputs)
        self.assertEqual(self.observe(device,inputs)['values']['outputs']['rf']['crest_factor_db'],0)

    def test_sensor_acquisition_keeps_on_average_duty_crest_and_revision(self):
        device=self.device('power_sensor',model='SyntheticSensor')
        self.perform(device,'configure',{'calibration_valid':True,'acquisition_ticks':2})
        inputs={'rf':signal()}
        self.assertEqual(self.perform(device,'acquire',inputs=inputs,revision=7)['status'],'pending')
        self.assertEqual(self.observe(device,inputs,tick=1,revision=7)['status'],'pending')
        result=self.observe(device,inputs,tick=2,revision=7)['values']['outputs']['measurement']
        self.assertTrue(result['valid']); self.assertEqual(result['unit'],'dBm')
        self.assertEqual(result['value'],10); self.assertEqual(result['power_dbm'],10)
        self.assertEqual(result['duty_cycle'],.25); self.assertEqual(result['crest_factor_db'],6)
        self.assertEqual(result['acquisition_tick'],2); self.assertEqual(result['acquisition_setup_revision'],7)

    def test_sensor_inflight_revision_or_input_change_invalidates_capture(self):
        for changed,revision in ((signal(),8),(signal(power_dbm=11),7)):
            with self.subTest(revision=revision,power=changed['power_dbm']):
                device=self.device('power_sensor'); self.perform(device,'configure',{'calibration_valid':True,'acquisition_ticks':2})
                self.perform(device,'acquire',inputs={'rf':signal()},revision=7)
                result=self.observe(device,{'rf':changed},tick=2,revision=revision)
                self.assertEqual(result['status'],'invalid'); self.assertNotIn('measurement',result['values']['outputs'])

    def test_sensor_rejects_uncalibrated_and_mismatched_models(self):
        for config in ({'calibration_valid':False},{'calibration_valid':True,'expected_model':'OtherSensor'}):
            with self.subTest(config=config):
                device=self.device('power_sensor'); self.perform(device,'configure',config)
                self.assertEqual(self.perform(device,'acquire',inputs={'rf':signal()})['status'],'invalid')

    def test_sensor_continuous_policy_creates_fresh_samples(self):
        device=self.device('power_sensor'); self.perform(device,'configure',{'calibration_valid':True,'acquisition_policy':'continuous'})
        self.assertEqual(self.observe(device,{'rf':signal()},tick=0)['status'],'pending')
        first=self.observe(device,{'rf':signal()},tick=1)['values']['outputs']['measurement']
        later=self.observe(device,{'rf':signal()},tick=2)['values']['outputs']['measurement']
        self.assertEqual(first['acquisition_tick'],1); self.assertEqual(later['acquisition_tick'],2)

    def test_sensor_fault_recovery_needs_fresh_acquisition(self):
        device=self.device('power_sensor'); self.perform(device,'configure',{'calibration_valid':True})
        inputs={'rf':signal()}; self.perform(device,'acquire',inputs=inputs)
        self.assertEqual(self.observe(device,inputs,tick=1)['status'],'ok')
        device.author_control('measurement_invalid',True)
        self.assertNotIn('measurement',device.observation(tick=1,setup_revision=1)['values']['outputs'])
        device.author_control('measurement_invalid',False)
        self.assertNotIn('measurement',self.observe(device,inputs,tick=2)['values']['outputs'])
        self.perform(device,'acquire',inputs=inputs,tick=2)
        self.assertEqual(self.observe(device,inputs,tick=3)['values']['outputs']['measurement']['acquisition_tick'],3)

    def test_same_enable_value_preserves_completed_acquisition(self):
        device=self.device('power_sensor'); self.perform(device,'configure',{'calibration_valid':True})
        inputs={'rf':signal()}; self.perform(device,'acquire',inputs=inputs)
        self.observe(device,inputs,tick=1)
        self.assertFalse(self.perform(device,'enable',{'enabled':True},tick=1)['setup_changed'])
        self.assertEqual(self.observe(device,inputs,tick=1)['values']['outputs']['measurement']['acquisition_tick'],1)

    def test_stuck_switch_preserves_pending_request_until_recovery(self):
        device=self.device('rf_switch'); self.perform(device,'configure',{'loss_db':1})
        self.perform(device,'select_path',{'input_port':'rf_1'})
        device.author_control('stuck',True)
        self.assertEqual(self.observe(device,{'rf_1':signal()},tick=20)['status'],'pending')
        device.author_control('stuck',False)
        self.assertEqual(self.observe(device,{'rf_1':signal()},tick=21)['values']['outputs']['rf']['power_dbm'],9)

    def test_controller_gate_does_not_overwrite_operator_selected_path(self):
        ports={'inputs':{'control':'control'},'outputs':{'control':'control'}}
        device=self.device('rf_switch',ports=ports,parameters={'controller_only':True,'requires_control':True})
        self.perform(device,'configure',{})
        self.perform(device,'select_path',{'input_port':'rf_1'})
        self.assertEqual(self.observe(device,{},tick=1)['status'],'disconnected')
        result=self.observe(device,{'control':{'valid':True,'enabled':True,'selected_input':'rf_2'}},tick=2)
        self.assertEqual(result['values']['outputs']['control']['selected_input'],'rf_1')


if __name__=='__main__':unittest.main()
