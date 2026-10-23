"""Policy contract doubles use public observations, never hidden fault answers."""
import copy
import importlib
import importlib.util
import json
import unittest

from labflow.virtual_fleet.rf import ROLE_ACTIONS


def rf_frame(source='dut'):
    return {'status':'ok','valid':True,'frequency_hz':1e9,'power_dbm':8.0,
            'bandwidth_hz':1e6,'duty_cycle':.25,'crest_factor_db':3.0,
            'modulation':'QPSK','source_id':source}


def context(*, tick=14, revision=3, dut_state='active', sensor_state='unavailable', sample=None):
    profiles=[{'profile_id':'profile-'+name,'role':role,'model':'SYNTHETIC',
               'manufacturer':'SYNTHETIC','ports':ports}
              for name,role,ports in (
                  ('dut','dut',{'inputs':{},'outputs':{'rf':'rf'}}),
                  ('sensor','power_sensor',{'inputs':{'rf':'rf'},'outputs':{'measurement':'measurement'}}))]
    def node(name,role,status,state,outputs):
        return {'status':status,'device_id':name,'profile_id':'profile-'+name,'role':role,
                'tick':tick,'setup_revision':revision,'synthetic':True,'hardware_verified':False,
                'values':{'configured':True,'state':state,'outputs':outputs}}
    dut=node('dut','dut','disconnected' if dut_state=='disconnected' else
             'pending' if dut_state=='arming' else 'ok',dut_state,
             {'rf':rf_frame()} if dut_state=='active' else {})
    sensor=node('sensor','power_sensor','ok' if sample is not None else
                'pending' if sensor_state=='acquiring' else 'invalid',sensor_state,
                {'measurement':copy.deepcopy(sample)} if sample is not None else {})
    return {'schema_version':1,
            'goal':{'kind':'acquire_fresh_rf_sensor','dut_id':'dut','sensor_id':'sensor','minimum_acquisition_tick':15},
            'catalog':{'profiles':profiles},
            'topology':{'devices':[{'id':p,'profile_id':'profile-'+p} for p in ('dut','sensor')],
                        'connections':[{'source':{'device_id':'dut','port':'rf'},
                                        'target':{'device_id':'sensor','port':'rf'},'kind':'rf'}]},
            'role_actions':copy.deepcopy(ROLE_ACTIONS),
            'observations':{'tick':tick,'setup_revision':revision,'synthetic':True,'hardware_verified':False,
                            'devices':{'dut':dut,'sensor':sensor}},
            'last_receipt':None,'remaining_budget':{'decisions':64,'ticks':32,'logical_requests':64}}


def measurement(tick=15, revision=3, **changes):
    return {'status':'ok','valid':True,'value':8.0,'unit':'dBm','power_dbm':8.0,'frequency_hz':1e9,
            'duty_cycle':.25,'crest_factor_db':3.0,'source_id':'sensor',
            'acquisition_tick':tick,'acquisition_setup_revision':revision,**changes}


class FixturePolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('labflow.virtual_fleet.policies'),
                             'Observation policy is not implemented')
        self.Policy=importlib.import_module('labflow.virtual_fleet.policies').RFSensorFixturePolicy

    def acquire(self,policy):
        self.assertEqual(policy(context()),{'kind':'execute','device_id':'sensor','action':'acquire','parameters':{}})

    def test_identity_has_no_private_constructor_arguments(self):
        self.assertEqual(self.Policy().policy_id,'rf_sensor_v1')
        with self.assertRaises(TypeError):self.Policy(seed=7)

    def test_normal_sequence_uses_observations_and_reads_before_completion(self):
        policy=self.Policy()
        self.assertEqual(policy(context(dut_state='idle'))['action'],'start')
        self.assertEqual(policy(context(dut_state='arming')),{'kind':'advance','ticks':1})
        self.acquire(policy)
        self.assertEqual(policy(context(sensor_state='acquiring')),{'kind':'advance','ticks':1})
        done=context(tick=15,sensor_state='complete',sample=measurement())
        self.assertEqual(policy(done),{'kind':'execute','device_id':'sensor','action':'read','parameters':{}})
        result=policy(copy.deepcopy(done))
        self.assertEqual(result['kind'],'stop'); self.assertEqual(result['claim'],'completed')

    def test_persistent_disconnect_waits_without_guessing_or_clearing_fault(self):
        policy=self.Policy()
        for tick in range(14,20):
            self.assertEqual(policy(context(tick=tick,dut_state='disconnected')),{'kind':'advance','ticks':1})

    def test_recovery_uses_same_goal_then_start_and_a_fresh_acquisition(self):
        policy=self.Policy()
        for tick in range(14,18):policy(context(tick=tick,dut_state='disconnected'))
        self.assertEqual(policy(context(tick=18,revision=4,dut_state='idle'))['action'],'start')
        self.assertEqual(policy(context(tick=19,revision=5))['action'],'acquire')
        ready=context(tick=20,revision=5,sensor_state='complete',sample=measurement(tick=20,revision=5))
        self.assertEqual(policy(ready)['action'],'read')
        self.assertEqual(policy(ready)['claim'],'completed')

    def test_stale_receipt_cannot_supply_missing_current_measurement(self):
        policy=self.Policy(); self.acquire(policy)
        value=context(tick=16,dut_state='disconnected')
        value['last_receipt']=context(tick=15,sample=measurement())['observations']['devices']['sensor']
        self.assertEqual(policy(value),{'kind':'advance','ticks':1})

    def test_wrong_measurement_units_sources_revision_or_numbers_never_complete(self):
        for change in ({'unit':'W'},{'source_id':'profile-sensor'},{'value':True},
                       {'value':float('nan')},{'value':float('inf')},{'value':9.0},
                       {'acquisition_tick':99},{'acquisition_tick':True},
                       {'acquisition_setup_revision':2},{'frequency_hz':2e9},
                       {'duty_cycle':.5},{'crest_factor_db':4}):
            with self.subTest(change=change):
                policy=self.Policy(); self.acquire(policy)
                result=policy(context(tick=15,sample=measurement(**change)))
                self.assertEqual(result['kind'],'stop'); self.assertNotEqual(result['claim'],'completed')

    def test_old_sample_requires_new_acquire_even_with_ok_receipt(self):
        policy=self.Policy()
        value=context(sample=measurement(tick=14))
        value['last_receipt']=value['observations']['devices']['sensor']
        self.assertEqual(policy(value)['action'],'acquire')

    def test_revision_change_invalidates_an_already_proposed_read(self):
        policy=self.Policy(); self.acquire(policy)
        self.assertEqual(policy(context(tick=15,sample=measurement()))['action'],'read')
        changed=context(tick=15,revision=4,sensor_state='acquiring')
        self.assertEqual(policy(changed),{'kind':'advance','ticks':1})

    def test_regressed_clock_and_changed_read_sample_cannot_complete(self):
        for change in ('clock','sample'):
            policy=self.Policy(); self.acquire(policy)
            ready=context(tick=15,sample=measurement())
            self.assertEqual(policy(ready)['action'],'read')
            if change=='clock':ready=context(tick=14,sample=measurement(tick=14))
            else:
                ready['observations']['devices']['dut']['values']['outputs']['rf']['power_dbm']=9
                ready['observations']['devices']['sensor']['values']['outputs']['measurement'].update(value=9,power_dbm=9)
            self.assertEqual(policy(ready)['claim'],'failed')

    def test_overflowing_rf_occupied_band_is_invalid_context(self):
        value=context()
        value['observations']['devices']['dut']['values']['outputs']['rf'].update(frequency_hz=1.7e308,bandwidth_hz=1.7e308)
        result=self.Policy()(value)
        self.assertEqual(result['kind'],'stop'); self.assertEqual(result['claim'],'failed')

    def test_equivalent_integer_and_float_measurements_survive_read_confirmation(self):
        policy=self.Policy(); self.acquire(policy)
        ready=context(tick=15,sample=measurement())
        self.assertEqual(policy(ready)['action'],'read')
        ready['observations']['devices']['sensor']['values']['outputs']['measurement'].update(value=8,power_dbm=8)
        self.assertEqual(policy(ready)['claim'],'completed')

    def test_malformed_json_metadata_types_are_safely_rejected(self):
        for field,bad in (('role_actions',[]),('catalog',None),('topology',None)):
            with self.subTest(field=field):
                value=context(); value[field]=bad
                self.assertEqual(self.Policy()(value)['claim'],'failed')

    def test_malformed_node_envelopes_are_safely_rejected(self):
        for identity in ('dut','sensor'):
            with self.subTest(identity=identity):
                value=context(); value['observations']['devices'][identity]=None
                self.assertEqual(self.Policy()(value)['claim'],'failed')

    def test_goal_and_capability_mutations_are_rejected_without_echo(self):
        for part in ('goal','catalog','topology','role_actions'):
            with self.subTest(part=part):
                policy=self.Policy(); self.acquire(policy); value=context(tick=15,sample=measurement())
                if part=='goal':value[part]['minimum_acquisition_tick']=0
                elif part=='catalog':value[part]['profiles'][1]['model']='CANARY'
                elif part=='topology':value[part]['connections']=[]
                else:value[part]['power_sensor'].pop('read')
                result=policy(value)
                self.assertEqual(result['kind'],'stop'); self.assertEqual(result['claim'],'failed')
                self.assertNotIn('CANARY',json.dumps(result))

    def test_input_and_proposal_do_not_alias_private_policy_state(self):
        policy=self.Policy(); value=context(); before=copy.deepcopy(value)
        first=policy(value); self.assertEqual(value,before)
        first['parameters']['seed']='CANARY'
        next_value=context(tick=15,sample=measurement())
        self.assertEqual(policy(next_value)['parameters'],{})

    def test_missing_capability_or_rf_connection_is_unsupported(self):
        for change in ('read','connection'):
            value=context()
            if change=='read':value['role_actions']['power_sensor'].pop('read')
            else:value['topology']['connections']=[]
            self.assertEqual(self.Policy()(value)['claim'],'unsupported')

    def test_wrong_envelope_or_rf_hop_provenance_is_rejected(self):
        for change in ('profile','revision','source'):
            value=context()
            if change=='profile':value['observations']['devices']['sensor']['profile_id']='other'
            elif change=='revision':value['observations']['devices']['dut']['setup_revision']=2
            else:value['observations']['devices']['dut']['values']['outputs']['rf']['source_id']='profile-dut'
            self.assertEqual(self.Policy()(value)['claim'],'failed')

    def test_unconfigured_sensor_is_blocked_without_inventing_calibration(self):
        value=context(); value['observations']['devices']['sensor']['values']['configured']=False
        self.assertEqual(self.Policy()(value)['claim'],'blocked')

    def test_non_json_private_or_invalid_clocks_are_rejected(self):
        for change in ('object','private','clock','goal','unknown'):
            value=context()
            if change=='object':value['last_receipt']=object()
            elif change=='private':value['remaining_budget']['fault']='CANARY'
            elif change=='clock':value['observations']['tick']=True
            elif change=='goal':value['goal']['minimum_acquisition_tick']=True
            else:value['runtime']=object()
            result=self.Policy()(value)
            self.assertEqual(result['claim'],'failed'); self.assertNotIn('CANARY',json.dumps(result))


if __name__=='__main__':unittest.main()
