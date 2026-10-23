"""All supplied model variants: normal output, disconnect, fresh recovery.

Only the public catalog and newly authored synthetic inputs are used. These
checks do not load reports, original workbooks, traces or real calibration.
"""
import copy
from pathlib import Path
import unittest

from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet import facility, rf, instruments

CATALOG=Path(__file__).resolve().parents[1]/'virtual_profiles/sm_a176u_unlicensed.json'


class AllProfileAcceptance(unittest.TestCase):
    def test_every_profile_produces_valid_output_then_disconnects_and_recovers(self):
        profiles=load_catalog(CATALOG)['profiles']
        seen=set()
        for original in profiles:
            with self.subTest(profile=original['profile_id'],role=original['role']):
                profile=copy.deepcopy(original)
                role=profile['role']
                module=next(m for m in (facility,rf,instruments) if role in m.DEVICE_FACTORIES)
                # A known synthetic VNA calibration, not a current asset claim.
                if role=='network_analyzer':profile['simulation_parameters']['calibration_valid']=True
                device=module.DEVICE_FACTORIES[role](profile,11)
                tick=0
                signal={'valid':True,'status':'ok','frequency_hz':2e9,'power_dbm':8,
                        'bandwidth_hz':1e6,'duty_cycle':.25,'modulation':'OFDM',
                        'crest_factor_db':2,'source_id':'fixture:rf'}
                sensor={'valid':True,'status':'ok','frequency_hz':2e9,'power_dbm':8,'value':8,
                        'unit':'dBm','duty_cycle':.25,'crest_factor_db':2,'source_id':'fixture:sensor',
                        'acquisition_tick':0,'acquisition_setup_revision':0}
                measurement={**sensor,'quantity':'on_average','source_id':'fixture:meter'}
                inputs={}
                for name,kind in profile['ports']['inputs'].items():
                    if kind=='rf':inputs[name]=copy.deepcopy(signal)
                    elif kind=='power':inputs[name]={'valid':True,'enabled':True,'voltage_v':5}
                    elif kind=='environment':inputs[name]={'valid':True,'stable':True,'temperature_c':23,'humidity_percent':45}
                    elif kind=='control' and module is not facility:
                        inputs[name]={'valid':True,'enabled':True,'selected_input':'rf_1','source_id':'fixture:control'}
                    elif kind=='measurement':inputs[name]=copy.deepcopy(sensor if name=='sensor' else measurement)
                if role=='network_analyzer':
                    inputs['path']={'valid':True,'source_id':'fixture:cable',
                                    'frequency_loss_db':[[1e9,1],[2e9,2],[3e9,3]]}
                if role=='dfs_system' and profile['simulation_parameters']['function']=='analyzer':
                    inputs['rf'].update(modulation='pulse',duty_cycle=.001,pulse_width_s=1e-6,pulse_repetition_hz=1000)

                def action(name,parameters=None):
                    response=device.perform(name,parameters or {},tick=tick,setup_revision=0,inputs=inputs)
                    self.assertIn(response['status'],{'ok','pending'},response)

                def normal():
                    nonlocal tick
                    if role=='power_supply':
                        action('configure',{'voltage_v':5,'current_limit_a':1})
                        action('set_load',{'resistance_ohm':50});action('output',{'enabled':True})
                    elif role=='temperature_chamber':
                        action('configure',{'temperature_c':23,'humidity_percent':45});action('start')
                    elif role in {'position_controller','antenna_mast','turntable'}:
                        action('configure',{'speed_per_tick':1});action('move',{'position':1})
                    elif role=='inspection_microscope':
                        action('configure',{'magnification':10,'focus_um':100,'illumination_percent':80})
                        action('load_sample',{'sample_id':'fixture:sample','feature_size_um':10,'surface_contrast':.9})
                        action('acquire')
                    elif role=='dut':
                        action('configure',{k:signal[k] for k in ('frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','crest_factor_db')})
                        action('start')
                    elif role=='power_sensor':
                        action('configure',{'calibration_valid':True});action('acquire')
                    elif role in rf.DEVICE_FACTORIES:
                        options={'attenuator':{'attenuation_db':profile['simulation_parameters'].get('attenuation_db',3)},
                                 'coupler':{'through_loss_db':1,'coupling_db':20},
                                 'splitter':{'ways':len(profile['ports']['outputs']),'loss_db':1},
                                 'antenna':{'gain_db':2,'loss_db':1},'amplifier':{'gain_db':3},
                                 'filter':{'loss_db':1,'band_min_hz':1e9,'band_max_hz':3e9},
                                 'rf_switch':({'routes':['rf_1','rf_2']} if profile['simulation_parameters'].get('controller_only') else {'loss_db':1}),
                                 'lisn':{'loss_db':1}}[role]
                        if role=='attenuator' and profile['simulation_parameters'].get('attenuator_mode')=='step':options['steps_db']=[0,3,6]
                        action('configure',options)
                        if role=='rf_switch':action('select_path',{'input_port':'rf_1'})
                    elif role=='network_analyzer':
                        action('configure',{'start_hz':1e9,'stop_hz':3e9,'points':3});action('acquire')
                    elif role=='test_software':
                        action('configure',{'criteria':[{'id':'fixture:criterion','unit':'dBm','quantity':'on_average','operator':'<=','limit':9}]})
                        action('run')
                    elif role=='dfs_system' and profile['simulation_parameters']['function']=='generator':
                        action('configure',{'frequency_hz':2e9,'power_dbm':8});action('start_tx')
                    else:
                        action('configure',{'frequency_hz':2e9});action('acquire')
                    for _ in range(8):
                        tick+=1
                        device.advance(tick=tick,setup_revision=0,inputs=inputs)
                    observed=device.observation(tick=tick,setup_revision=0)
                    self.assertEqual(observed['status'],'ok',observed)
                    outputs=observed['values']['outputs']
                    self.assertTrue(outputs,observed)
                    for payload in outputs.values():self.assertIs(payload.get('valid'),True,payload)
                    if role=='dut':self.assertEqual(outputs['rf']['power_dbm'],8)
                    if role=='attenuator':self.assertEqual(outputs['rf']['power_dbm'],8-options['attenuation_db'])
                    if role=='power_sensor':self.assertEqual(outputs['measurement']['value'],8)
                    if role in {'power_meter','signal_analyzer'}:self.assertEqual(outputs['measurement']['value'],8)
                    if role=='network_analyzer':self.assertEqual(outputs['measurement']['value'],[-1,-2,-3])
                    return outputs

                before=normal()
                fault=('communication_loss' if module is facility else 'disconnect' if module is rf else 'disconnected')
                device.author_control(fault,True)
                tick+=1;device.advance(tick=tick,setup_revision=0,inputs=inputs)
                disconnected=device.observation(tick=tick,setup_revision=0)
                self.assertEqual(disconnected['status'],'disconnected')
                self.assertFalse(disconnected['values']['outputs'])
                device.author_control(fault,False)
                if module is facility:action('reset')
                elif module is instruments:action('recover')
                after=normal()
                self.assertEqual(set(before),set(after))
                seen.add(profile['profile_id'])
        self.assertEqual(seen,{profile['profile_id'] for profile in profiles})


if __name__=='__main__':unittest.main()
