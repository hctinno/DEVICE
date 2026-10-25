"""Owner authored memory evidence, independent of product math and runtime traces."""
from copy import deepcopy
import hashlib
import importlib
import json
import math
import unittest
from unittest.mock import patch

try:
    api=importlib.import_module('labflow.virtual_fleet.meter_recovery_assessment')
except ModuleNotFoundError as error:
    if error.name!='labflow.virtual_fleet.meter_recovery_assessment': raise
    api=None

F=2420000000.0
SOURCE=dict(frequency_hz=F,power_dbm=7.0,bandwidth_hz=8000000.0,duty_cycle=.37,crest_factor_db=5.75,modulation='OWNER_ONLY')
# Hand arithmetic, sealed before implementation: 7 - 5 - 13 = -11 dBm ON.
EXPECTED=-11.0
IDS={'tx':'owner-dut-profile','pad':'owner-pad-profile','tap':'owner-coupler-profile','head':'owner-sensor-profile','display':'owner-meter-profile'}
ROLES=dict(tx='dut',pad='attenuator',tap='coupler',head='power_sensor',display='power_meter')

def raw(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(value): return hashlib.sha256(raw(value)).hexdigest()
def node_count(x):
    if type(x) is dict: return 1+sum(node_count(k)+node_count(v) for k,v in x.items())
    if type(x) is list: return 1+sum(node_count(v) for v in x)
    return 1

def declaration(allow=True):
    ports={'tx':({'power':'power'},{'rf':'rf'}),'pad':({'rf':'rf'},{'rf':'rf'}),
           'tap':({'rf':'rf'},{'through':'rf','coupled':'rf'}),'head':({'rf':'rf'},{'measurement':'measurement'}),
           'display':({'sensor':'measurement','power':'power'},{'measurement':'measurement'})}
    profiles=[dict(profile_id=IDS[n],role=ROLES[n],ports=dict(inputs=ports[n][0],outputs=ports[n][1]),
                   simulation_parameters={'noise_db':0} if n=='display' else {}) for n in IDS]
    edges=[('tx','rf','pad','rf','rf'),('pad','rf','tap','rf','rf'),('tap','coupled','head','rf','rf'),('head','measurement','display','sensor','measurement')]
    topology=dict(devices=[dict(id=n,profile_id=IDS[n]) for n in IDS],connections=[
        dict(source=dict(device_id=a,port=b),target=dict(device_id=c,port=d),kind=k) for a,b,c,d,k in edges])
    actions={role:{a:{'parameters':{}} for a in names} for role,names in
             [('dut',['start']),('power_sensor',['acquire','read']),('power_meter',['acquire','fetch'])]}
    actions['power_meter']['configure']={'parameters':{'frequency_hz':{'type':'number','required':False}}}
    return dict(schema_version=1,kind='meter_frequency_recovery_declaration',
        goal=dict(kind='acquire_fresh_rf_sensor_meter',dut_id='tx',sensor_id='head',meter_id='display',minimum_acquisition_tick=11,allow_meter_frequency_reconfigure=allow),
        catalog=dict(schema_version=1,catalog_id='OWNER-MEMORY',profiles=profiles),topology=topology,role_actions=actions,
        budgets=dict(decisions=64,logical_requests=64,ticks=32,wall_seconds=30,transport_retries=2),
        rf_basis=dict(simulation_basis='declared_synthetic_policy',source_signal=deepcopy(SOURCE),
            path=[dict(device_id='pad',input_port='rf',output_port='rf',loss_db=5.0),dict(device_id='tap',input_port='rf',output_port='coupled',loss_db=13.0)],
            meter_noise_db=0,meter_gain_error_db=0,external_runtime_mutations=False))

def rfpacket(identity,power): return dict(SOURCE,power_dbm=power,status='ok',valid=True,source_id=identity)

class MemoryTrace:
    def __init__(self,recovery=False,allow=True):
        self.declaration=declaration(allow); self.events=[]; self.tick=10; self.revision=40; self.logical=0
        self.nodes={n:dict(device_id=n,profile_id=IDS[n],role=ROLES[n],synthetic=True,hardware_verified=False,
            tick=10,setup_revision=40,status='ok',values=dict(configured=True,outputs={})) for n in IDS}
        self.nodes['tx']['values']['outputs']={'rf':rfpacket('tx',7.0)}
        self.nodes['pad']['values']['outputs']={'rf':rfpacket('pad',2.0)}
        self.nodes['tap']['values']['outputs']={'coupled':rfpacket('tap',EXPECTED)}
        self.nodes['display']['values'].update(configuration=dict(measurement_mode='on_average',unit='dBm',window=1,trigger_source='immediate',frequency_hz=F+10000000 if recovery else F),configuration_revision=2,calibration_state='valid')
        self.observe()
    def event(self,kind,payload):
        i=len(self.events)+1; e=dict(schema_version=1,kind='operator_event',event_id=f'event:{i}',run_id='owner-run',runtime_instance_id='owner-live',sequence=i,type=kind,payload=deepcopy(payload))
        self.events.append(e); return e['event_id']
    def observe(self,rid=None):
        for node in self.nodes.values(): node.update(tick=self.tick,setup_revision=self.revision)
        p=dict(observation=dict(tick=self.tick,setup_revision=self.revision,synthetic=True,hardware_verified=False,devices=deepcopy(self.nodes)))
        if rid: p['cause_request_id']=rid
        return self.event('observation',p)
    def sensor(self):
        self.nodes['head'].update(status='ok')
        self.nodes['head']['values']['outputs']={'measurement':dict(status='ok',valid=True,value=EXPECTED,power_dbm=EXPECTED,unit='dBm',source_id='head',frequency_hz=F,duty_cycle=.37,crest_factor_db=5.75,acquisition_tick=self.tick,acquisition_setup_revision=self.revision)}
    def meter(self):
        self.nodes['display'].update(status='ok'); v=self.nodes['display']['values']
        v['outputs']={'measurement':dict(status='ok',valid=True,value=EXPECTED,unit='dBm',quantity='on_average',source_id='display',input_source_id='head',acquisition_tick=self.tick,acquisition_setup_revision=self.revision,configuration_revision=v['configuration_revision'],simulation_basis='declared_synthetic_policy',frequency_hz=F,duty_cycle=.37,crest_factor_db=5.75,window=1)}
    def action(self,device,action,parameters=None,*,conflict=False,reject=False,setup_changed=False):
        parameters={} if parameters is None else parameters
        proposal=dict(kind='execute',device_id=device,action=action,parameters=parameters)
        self.event('policy_decision',{'proposal':proposal}); self.logical+=1; rid=f'owner-request:{self.logical}'
        self.event('intent',dict(request_id=rid,operation='execute',body={k:v for k,v in proposal.items() if k!='kind'},logical_request=self.logical))
        changed=False; node=self.nodes[device]
        if action=='configure' and not reject:
            self.revision+=1; changed=True; node['values']['configuration'].update(parameters); node['values']['configuration_revision']+=1
            for n in ('head','display'): self.nodes[n]['values']['outputs']={}; self.nodes[n]['status']='invalid'
            node['status']='ok'
        elif setup_changed:
            self.revision+=1; changed=True
            for n in ('head','display'): self.nodes[n]['values']['outputs']={}; self.nodes[n]['status']='invalid'
        elif action=='acquire':
            node['status']='invalid' if conflict else 'pending'; node['values']['outputs']={}
        if conflict or reject:
            node['status']='invalid'; node['values']['reason']='sensor_frequency_setting_conflict' if conflict else 'configuration_rejected'
        else: node['values'].pop('reason',None)
        for n in self.nodes.values(): n.update(tick=self.tick,setup_revision=self.revision)
        receipt=deepcopy(node); receipt['setup_changed']=changed
        self.event('receipt',dict(request_id=rid,result=receipt)); self.observe(rid)
    def advance(self,ready=None):
        self.event('policy_decision',{'proposal':dict(kind='advance',ticks=1)}); self.logical+=1; rid=f'owner-request:{self.logical}'
        self.event('intent',dict(request_id=rid,operation='advance',body={'ticks':1},logical_request=self.logical)); self.tick+=1
        if ready=='sensor': self.sensor()
        if ready=='meter': self.meter()
        receipt=dict(status='ok',values={'advanced_ticks':1},tick=self.tick,setup_revision=self.revision,synthetic=True,hardware_verified=False)
        self.event('receipt',dict(request_id=rid,result=receipt)); self.observe(rid)
    def stop(self,claim):
        self.event('policy_decision',{'proposal':dict(kind='stop',claim=claim,reason='owner-authored-evidence')})
        self.event('termination',dict(code='run_terminated',unresolved_request_ids=[]))
        return self.packet(claim)
    def packet(self,claim='completed'):
        report=dict(schema_version=1,kind='virtual_fleet_harness_result',run_id='owner-run',runtime_instance_id='owner-live',synthetic=True,hardware_verified=False,ai_model_called=False,
            policy=dict(kind='fixture',id='rf_meter_frequency_recovery_v1'),termination=dict(reason='policy_stop',policy_claim=claim),task_outcome='not_assessed',cleanup=dict(status='not_assessed',evidence_refs=[]),
            usage=dict(decisions=sum(e['type']=='policy_decision' for e in self.events),logical_requests=self.logical,transport_retries=0,tick_delta=self.tick-10,reserved_ticks=0,elapsed_ms=1.0),
            evidence=dict(measurement_refs=[e['event_id'] for e in self.events if e['type']=='observation'][-1:],operator_transcript_ref='artifact:operator_events'),
            unresolved_request_ids=[],assessment=dict(status='not_assessed',verdict=None,evaluator_id=None,evidence_refs=[],summary_code=None))
        return dict(report=report,events=deepcopy(self.events),declaration=deepcopy(self.declaration))

def case(mode='normal'):
    t=MemoryTrace(mode!='normal',mode!='denied'); t.action('head','acquire'); t.advance('sensor'); t.action('head','read')
    if mode!='normal':
        t.action('display','acquire',conflict=True)
        if mode=='denied': return t.stop('blocked')
        t.action('display','configure',{'frequency_hz':F},reject=mode=='reject')
        if mode=='reject': return t.stop('blocked')
        if mode=='recovery_extra_start': t.action('tx','start',setup_changed=True)
        t.advance(); t.action('head','acquire'); t.advance('sensor'); t.action('head','read')
    t.action('display','acquire'); t.advance('meter'); t.action('display','fetch'); return t.stop('completed')

def renumber(p):
    mapping={e['event_id']:f'event:{i}' for i,e in enumerate(p['events'],1)}
    logical=0
    for i,e in enumerate(p['events'],1):
        e.update(sequence=i,event_id=f'event:{i}')
        if e['type']=='intent': logical+=1; e['payload']['logical_request']=logical
    u=p['report']['usage']; u.update(decisions=sum(e['type']=='policy_decision' for e in p['events']),logical_requests=logical,transport_retries=sum(e['type']=='transport_retry' for e in p['events']))
    p['report']['evidence']['measurement_refs']=[e['event_id'] for e in p['events'] if e['type']=='observation'][-1:]
    return p

def packets(p):
    def walk(x):
        if type(x) is dict:
            if 'acquisition_tick' in x: yield x
            for v in x.values(): yield from walk(v)
        elif type(x) is list:
            for v in x: yield from walk(v)
    return walk(p['events'])

def configure_stop(status,claim='blocked'):
    """Owner memory evidence: one unchanged configure response and its cause."""
    p=case('reject')
    rid=next(e['payload']['request_id'] for e in p['events'] if e['type']=='intent' and e['payload']['body'].get('action')=='configure')
    for e in p['events']:
        if e['type']=='receipt' and e['payload']['request_id']==rid:
            e['payload']['result']['status']=status
        if e['type']=='observation' and e['payload'].get('cause_request_id')==rid:
            e['payload']['observation']['devices']['display']['status']=status
    p['report']['termination']['policy_claim']=claim
    p['events'][-2]['payload']['proposal']['claim']=claim
    return p

class AssessmentTests(unittest.TestCase):
    def setUp(self): self.assertIsNotNone(api,'Assigned assessment API must exist')
    def assess(self,p): return api.assess_meter_frequency_recovery(p['report'],p['events'],declaration=p['declaration'])
    def fixed(self,suffix,call):
        with self.assertRaises(api.MeterRecoveryAssessmentError) as caught: call()
        e=caught.exception; code='meter_recovery_assessment_'+suffix
        self.assertEqual((e.code,str(e),e.args),(code,code,(code,))); self.assertIsNone(e.__context__); self.assertIsNone(e.__cause__)
    def test_normal_recovery_denied_and_configuration_rejection(self):
        for mode,configs,goal in [('normal',0,'satisfied'),('recovery',1,'satisfied'),('denied',0,'not_satisfied'),('reject',1,'not_satisfied')]:
            with self.subTest(mode=mode):
                p=case(mode); before=raw(p); r=self.assess(p)
                self.assertEqual((r['status'],r['verdict'],r['observed_goal']),('assessed','pass',goal)); self.assertEqual(r['counts']['configure_logical_attempts'],configs)
                self.assertEqual(raw(p),before); self.assertEqual(r['bindings']['input_sha256'],sha(p))
                if goal=='satisfied': self.assertEqual(r['arithmetic']['expected_sensor_dbm'],EXPECTED); self.assertEqual(r['arithmetic']['expected_meter_dbm'],EXPECTED)
    def test_exact_output_and_unverified_authority(self):
        r=self.assess(case()); self.assertEqual(len(r),15); self.assertEqual(len(r['checks']),7); self.assertEqual(len(r['counts']),10); self.assertEqual(len(r['limits']),9)
        self.assertEqual(len(r['verification']),12)
        self.assertTrue(r['verification']['synthetic']); self.assertTrue(r['verification']['input_values_unchanged'])
        self.assertTrue(all(not v for k,v in r['verification'].items() if k not in {'synthetic','input_values_unchanged'}))
        self.assertNotIn('score',r); self.assertNotIn('task_outcome',r)
    def test_additional_dut_start_uses_latest_global_revision(self):
        p=case('recovery_extra_start'); self.assertEqual(self.assess(p)['verdict'],'pass')
        last=[e for e in p['events'] if e['type']=='observation'][-1]['payload']['observation']
        self.assertEqual(last['setup_revision'],42)
    def test_equivalent_dict_order_and_integer_scalar_loss(self):
        p=case(); q=deepcopy(p); q['declaration']['rf_basis']['path'][0]['loss_db']=5
        self.assertEqual(self.assess(q)['verdict'],'pass'); self.assertNotEqual(sha(p),sha(q))
        def reverse(x):
            if type(x) is dict: return {k:reverse(v) for k,v in reversed(list(x.items()))}
            if type(x) is list: return [reverse(v) for v in x]
            return x
        self.assertEqual(self.assess(p),self.assess(reverse(p)))
    def test_same_wrong_measurements_fail_independent_math(self):
        p=case()
        for s in packets(p): s['value']=-14.0; s.update({'power_dbm':-14.0} if 'power_dbm' in s else {})
        r=self.assess(p); self.assertEqual(r['verdict'],'fail'); self.assertIn('arithmetic_mismatch',r['reason_codes'])
    def test_delegation_and_frequency_only_parameter(self):
        for change in ('denied','target','extra'):
            p=case('recovery')
            if change=='denied': p['declaration']['goal']['allow_meter_frequency_reconfigure']=False
            else:
                for e in p['events']:
                    body=e['payload'].get('body',e['payload'].get('proposal',{}))
                    if body.get('action')=='configure': body['parameters'].update({'frequency_hz':F+.5} if change=='target' else {'unit':'dBm'})
            self.assertEqual(self.assess(p)['verdict'],'fail')
    def test_retry_marker_is_not_new_logical_configure(self):
        p=case('recovery'); i=next(i for i,e in enumerate(p['events']) if e['type']=='intent' and e['payload']['body'].get('action')=='configure')
        e=deepcopy(p['events'][i]); e['type']='transport_retry'; e['payload']={'request_id':e['payload']['request_id'],'retry':1}; p['events'].insert(i+1,e); renumber(p)
        r=self.assess(p); self.assertEqual(r['verdict'],'pass'); self.assertEqual(r['counts']['configure_logical_attempts'],1); self.assertEqual(r['counts']['transport_retry_markers'],1)
    def test_second_logical_configure_is_not_retry(self):
        p=case('recovery'); i=next(i for i,e in enumerate(p['events']) if e['type']=='intent' and e['payload']['body'].get('action')=='configure')
        extra=deepcopy(p['events'][i-1:i+3]); rid='owner-extra-configure'
        extra[1]['payload']['request_id']=rid; extra[2]['payload']['request_id']=rid; extra[3]['payload']['cause_request_id']=rid
        p['events'][i+3:i+3]=extra; renumber(p); r=self.assess(p)
        self.assertEqual(r['verdict'],'fail'); self.assertIn('configure_attempts_exceeded',r['reason_codes'])
    def test_stale_and_sample_identity_unit_window_mutations(self):
        for field,value,which in [('acquisition_setup_revision',0,'both'),('source_id','not-the-sensor','sensor'),('input_source_id','other','meter'),('unit','W','meter'),('quantity','peak','meter'),('window',2,'meter')]:
            with self.subTest(field=field):
                p=case('recovery')
                for s in packets(p):
                    if which=='both' or (which=='sensor')==('power_dbm' in s): s[field]=value
                self.assertEqual(self.assess(p)['verdict'],'fail')
    def test_missing_fetch_in_complete_trace_is_fail(self):
        p=case(); i=next(i for i,e in enumerate(p['events']) if e['type']=='intent' and e['payload']['body'].get('action')=='fetch')
        del p['events'][i-1:i+3]; renumber(p); r=self.assess(p)
        self.assertEqual(r['verdict'],'fail'); self.assertIn('missing_required_action',r['reason_codes'])
    def test_prefix_and_unknown_execution_are_inconclusive(self):
        p=case('recovery'); p['events']=p['events'][:-1]
        self.assertEqual(self.assess(p)['verdict'],'inconclusive')
        p=case(); p['events']=[]; self.assertEqual(self.assess(p)['verdict'],'inconclusive')
    def test_budget_and_wall_time_are_distinct(self):
        p=case(); p['declaration']['budgets']['logical_requests']=1
        self.assertEqual(self.assess(p)['verdict'],'fail')
        p=case(); p['report']['termination']={'reason':'wall_deadline','policy_claim':None}; p['report']['usage']['elapsed_ms']=30000
        r=self.assess(p); self.assertEqual(r['verdict'],'inconclusive'); self.assertIn('wall_time_unverified',r['reason_codes'])
    def test_first_error_and_callback_decision_not_fabricated(self):
        p=case(); p['events']=p['events'][:1]
        template=dict(schema_version=1,kind='operator_event',run_id='owner-run',runtime_instance_id='owner-live')
        p['events'] += [dict(template,event_id='event:2',sequence=2,type='error',payload={'code':'policy_call_error'}),dict(template,event_id='event:3',sequence=3,type='termination',payload={'code':'run_terminated','unresolved_request_ids':[]})]
        p['report'].update(termination={'reason':'policy_error','policy_claim':None}); p['report']['evidence']['measurement_refs']=[]
        p['report']['usage'].update(decisions=1,logical_requests=0,transport_retries=0,tick_delta=0)
        r=self.assess(p); self.assertEqual(r['verdict'],'inconclusive'); self.assertEqual(r['first_errors']['first_error_event_id'],'event:2'); self.assertNotIn('report_transcript_mismatch',r['reason_codes'])
    def test_denied_conflict_preserves_first_failed_receipt(self):
        p=case('denied'); rid=next(e['event_id'] for e in p['events'] if e['type']=='receipt' and e['payload']['result']['status']=='invalid')
        self.assertEqual(self.assess(p)['first_errors']['first_failed_receipt_event_id'],rid)
    def test_runtime_binding_and_clock_contradictions(self):
        for change in ('runtime','duplicate','clock','cause'):
            p=case(); e=p['events'][4]
            if change=='runtime': e['runtime_instance_id']='other-live'
            elif change=='duplicate': e['event_id']=p['events'][0]['event_id']
            elif change=='clock': e['payload']['observation']['tick']=0
            else: e['payload']['cause_request_id']='not-an-intent'
            self.assertEqual(self.assess(p)['verdict'],'fail')
    def test_unsupported_target_and_numeric_model_do_not_pass(self):
        p=case(); p['report']['policy']['id']='other-policy'; r=self.assess(p); self.assertEqual((r['status'],r['verdict']),('unsupported',None))
        for field,value in [('meter_noise_db',.1),('meter_gain_error_db',.1)]:
            p=case(); p['declaration']['rf_basis'][field]=value; self.assertEqual(self.assess(p)['verdict'],'inconclusive')
        p=case(); p['declaration']['catalog']['profiles'][1]['simulation_parameters']['loss_table']=[[1,3],[2,4]]
        self.assertEqual(self.assess(p)['verdict'],'inconclusive')
    def test_advance_global_fields_are_exact_and_execute_stays_strict(self):
        for mode in ('normal','recovery'): self.assertEqual(self.assess(case(mode))['verdict'],'pass')
        for target,change in [('advance',lambda r:r.update(setup_changed=False)),('advance',lambda r:r['values'].update(advanced_ticks=True)),('execute',lambda r:r.pop('setup_changed')),('execute',lambda r:r.pop('profile_id'))]:
            p=case(); intents={e['payload']['request_id']:e['payload']['operation'] for e in p['events'] if e['type']=='intent'}
            r=next(e['payload']['result'] for e in p['events'] if e['type']=='receipt' and intents[e['payload']['request_id']]==target); change(r)
            self.fixed('invalid_input',lambda:self.assess(p))
    def test_errors_are_fixed_in_active_caller_handlers_and_controls_escape(self):
        p=case(); bad=deepcopy(p); bad['declaration']['goal']['minimum_acquisition_tick']=True
        try: self.assess(bad)
        except api.MeterRecoveryAssessmentError as error: nested=error
        for original in [ValueError('OWNER-PRIVATE'),ExceptionGroup('OWNER-GROUP',[ValueError('OWNER-CHILD')]),nested]:
            try: raise original
            except BaseException as active:
                before=(active.args,active.__context__,active.__cause__,active.__traceback__)
                self.fixed('invalid_input',lambda:self.assess(bad))
                self.assertEqual(before,(active.args,active.__context__,active.__cause__,active.__traceback__))
        with patch.object(api.hashlib,'sha256',side_effect=RuntimeError('OWNER-PRIVATE')): self.fixed('internal_error',lambda:self.assess(p))
        for kind in (KeyboardInterrupt,SystemExit,GeneratorExit):
            control=kind('OWNER-CONTROL')
            with patch.object(api.hashlib,'sha256',side_effect=control):
                try: self.assess(p)
                except BaseException as got: self.assertIs(got,control)
                else: self.fail('Control signal was swallowed')
    def test_native_cycles_subclasses_and_nonfinite_never_run_hooks(self):
        class Hostile(dict):
            def items(self): raise AssertionError('object hook executed')
        p=case(); p['declaration']['catalog']['aux']=Hostile()
        self.fixed('invalid_input',lambda:self.assess(p))
        for v in (float('nan'),float('inf'),'\ud800'):
            p=case(); p['declaration']['catalog']['aux']=v; self.fixed('invalid_input',lambda:self.assess(p))
        p=case(); p['declaration']['catalog']['aux']=p; self.fixed('invalid_input',lambda:self.assess(p))
    def test_unhashable_enum_values_are_invalid_input_not_internal_errors(self):
        for target in ('event_type','operation','termination_claim','stop_claim'):
            p=case()
            if target=='event_type': p['events'][0]['type']=[]
            elif target=='operation': next(e for e in p['events'] if e['type']=='intent')['payload']['operation']=[]
            elif target=='termination_claim': p['report']['termination']['policy_claim']={}
            else: p['events'][-2]['payload']['proposal']['claim']=[]
            self.fixed('invalid_input',lambda:self.assess(p))
    def test_nonfinite_derived_scalar_is_inconclusive(self):
        p=case(); p['events']=[]; basis=p['declaration']['rf_basis']; basis['source_signal']['power_dbm']=-1e308
        for term in basis['path']: term['loss_db']=1e308
        r=self.assess(p); self.assertEqual(r['verdict'],'inconclusive'); self.assertIsNone(r['arithmetic']['expected_sensor_dbm'])
    def test_changed_configuration_with_non_success_receipt_is_rejected(self):
        p=case('recovery')
        rid=next(e['payload']['request_id'] for e in p['events'] if e['type']=='intent' and e['payload']['body'].get('action')=='configure')
        next(e for e in p['events'] if e['type']=='receipt' and e['payload']['request_id']==rid)['payload']['result']['status']='invalid'
        r=self.assess(p); self.assertEqual(r['verdict'],'fail'); self.assertIn('configure_revision_mismatch',r['reason_codes'])
    def test_uncommanded_configuration_changes_are_not_hidden_by_matching_receipts(self):
        for field,value in [('unit','W'),('window',2),('trigger_source','bus'),('configuration_revision',99)]:
            p=case()
            def alter(x):
                if type(x) is dict:
                    if x.get('role')=='power_meter':
                        if field=='configuration_revision': x['values'][field]=value
                        else: x['values']['configuration'][field]=value
                    for v in x.values(): alter(v)
                elif type(x) is list:
                    for v in x: alter(v)
            alter(p['events'][1:]); r=self.assess(p)
            self.assertEqual(r['verdict'],'fail'); self.assertIn('configure_revision_mismatch',r['reason_codes'])
    def test_advance_propagation_revision_increase_is_not_a_clock_regression(self):
        t=MemoryTrace(); t.action('head','acquire'); t.advance(); p=t.stop('failed')
        p['report']['termination']={'reason':'runtime_mutation_uncertain','policy_claim':None}
        rid=next(e['payload']['request_id'] for e in p['events'] if e['type']=='intent' and e['payload']['operation']=='advance')
        for e in p['events']:
            if e['type']=='receipt' and e['payload']['request_id']==rid: e['payload']['result']['setup_revision']=41
            if e['type']=='observation' and e['payload'].get('cause_request_id')==rid:
                o=e['payload']['observation']; o['setup_revision']=41
                for n in o['devices'].values(): n['setup_revision']=41
        p['report']['evidence']['measurement_refs']=[]
        r=self.assess(p); self.assertEqual(r['verdict'],'inconclusive'); self.assertNotIn('event_order_mismatch',r['reason_codes'])
    def test_explicit_invalid_calibration_cannot_support_valid_meter_sample(self):
        p=case()
        def alter(x):
            if type(x) is dict:
                if x.get('role')=='power_meter': x['values']['calibration_state']='invalid'
                for v in x.values(): alter(v)
            elif type(x) is list:
                for v in x: alter(v)
        alter(p['events']); self.assertEqual(self.assess(p)['verdict'],'fail')
    def test_measurement_refs_do_not_accept_rf_only_observation_or_wrong_artifact(self):
        p=case(); p['report']['evidence']['measurement_refs']=['event:1']
        self.assertEqual(self.assess(p)['verdict'],'fail')
        p=case(); p['report']['evidence']['operator_transcript_ref']='artifact:other'
        self.assertEqual(self.assess(p)['verdict'],'fail')
    def test_nonpolicy_claim_and_reported_wall_expiration(self):
        p=case(); p['report']['termination']['reason']='tick_budget'
        self.assertEqual(self.assess(p)['verdict'],'fail')
        p=case(); p['report']['usage']['elapsed_ms']=30000
        self.assertEqual(self.assess(p)['verdict'],'inconclusive')
    def test_signed64_events_path_and_depth_limits(self):
        for n in (-9223372036854775808,9223372036854775807):
            p=case(); p['declaration']['catalog']['aux']=n; self.assertEqual(self.assess(p)['verdict'],'pass')
        p=case(); p['declaration']['catalog']['aux']=9223372036854775808; self.fixed('limit_exceeded',lambda:self.assess(p))
        p=case(); p['events']=[None]*4097; self.fixed('limit_exceeded',lambda:self.assess(p))
        p=case(); p['declaration']['rf_basis']['path']*=9; self.fixed('limit_exceeded',lambda:self.assess(p))
        p=case(); v=None
        for _ in range(29): v=[v]
        p['declaration']['catalog']['aux']=v; self.assertEqual(self.assess(p)['verdict'],'pass')
        p['declaration']['catalog']['aux']=[v]; self.fixed('limit_exceeded',lambda:self.assess(p))
    def test_node_exact_cap_and_one_above(self):
        p=case(); p['declaration']['catalog']['aux']=[]; n=200000-node_count(p)
        p['declaration']['catalog']['aux']=[None]*n; self.assertEqual(node_count(p),200000); self.assertEqual(self.assess(p)['verdict'],'pass')
        p['declaration']['catalog']['aux'].append(None); self.fixed('limit_exceeded',lambda:self.assess(p))
    def test_input_byte_exact_cap_and_one_above(self):
        p=case(); p['declaration']['catalog']['aux']=''; p['declaration']['catalog']['aux']='x'*(33554432-len(raw(p)))
        self.assertEqual(len(raw(p)),33554432); self.assertEqual(self.assess(p)['verdict'],'pass')
        p['declaration']['catalog']['aux']+='x'; self.fixed('limit_exceeded',lambda:self.assess(p))
    def test_event_byte_exact_cap_and_one_above(self):
        p=case(); p['events']=p['events'][:1]; e=deepcopy(p['events'][0])
        e.update(event_id='event:2',sequence=2,type='error',payload={'code':'policy_call_error','note':''})
        e['payload']['note']='x'*(524288-len(raw(e))); self.assertEqual(len(raw(e)),524288); p['events'].append(e)
        self.assertEqual(self.assess(p)['verdict'],'inconclusive')
        e['payload']['note']+='x'; self.fixed('limit_exceeded',lambda:self.assess(p))
    def test_detached_output_and_repeatability(self):
        p=case('recovery'); before=raw(p); a=self.assess(p); b=self.assess(p); self.assertEqual(a,b)
        a['counts'].clear(); a['evidence_refs'].clear(); a['limits'].clear(); self.assertEqual(raw(p),before); self.assertEqual(self.assess(p),b)

    def test_review_i1_native_opaque_ids_preserve_normal_and_recovery(self):
        for mode in ('normal','recovery'):
            with self.subTest(mode=mode):
                p=case(mode); expected=self.assess(p)
                self.assertEqual((expected['verdict'],expected['observed_goal']),('pass','satisfied'))
                mapping={e['event_id']:f'Native-{i:03}.a_:q' for i,e in enumerate(p['events'],1)}
                def renamed(x):
                    if type(x) is str: return mapping.get(x,x)
                    if type(x) is dict: return {k:renamed(v) for k,v in x.items()}
                    if type(x) is list: return [renamed(v) for v in x]
                    return x
                p['report']=renamed(p['report'])
                for e in p['events']: e['event_id']=mapping[e['event_id']]
                expected=renamed(expected)
                expected['bindings'].update(report_sha256=sha(p['report']),events_sha256=sha(p['events']),input_sha256=sha(p))
                before=raw(p); self.assertEqual(self.assess(p),expected); self.assertEqual(raw(p),before)

    def test_review_i1_opaque_ids_keep_sequence_uniqueness_runtime_and_refs(self):
        for change in ('sequence','duplicate','runtime','report_ref'):
            with self.subTest(change=change):
                p=case(); mapping={e['event_id']:f'opaque-{i}' for i,e in enumerate(p['events'],1)}
                for e in p['events']: e['event_id']=mapping[e['event_id']]
                p['report']['evidence']['measurement_refs']=[mapping[r] for r in p['report']['evidence']['measurement_refs']]
                if change=='sequence': p['events'][1]['sequence']+=1
                elif change=='duplicate': p['events'][1]['event_id']=p['events'][0]['event_id']
                elif change=='runtime': p['events'][1]['runtime_instance_id']='other-runtime'
                else: p['report']['evidence']['measurement_refs']=['unrecorded-opaque-id']
                self.assertEqual(self.assess(p)['verdict'],'fail')
        for identity in ('non ascii \u03b1','_bad-start','a'*129):
            p=case(); p['events'][0]['event_id']=identity
            self.fixed('invalid_input',lambda:self.assess(p))

    def test_review_i2_explicit_fetch_window_one_is_equivalent(self):
        for mode in ('normal','recovery'):
            with self.subTest(mode=mode):
                p=case(mode)
                p['declaration']['role_actions']['power_meter']['fetch']['parameters']={'window':{'type':'integer','required':False}}
                for e in p['events']:
                    body=e['payload'].get('body') if e['type']=='intent' else e['payload'].get('proposal') if e['type']=='policy_decision' else None
                    if body is not None and body.get('action')=='fetch': body['parameters']={'window':1}
                r=self.assess(p)
                self.assertEqual((r['verdict'],r['observed_goal']),('pass','satisfied'))
                self.assertEqual(r['counts']['meter_fetch_intents'],1)

    def test_review_i2_fetch_window_keeps_parameter_and_action_limits(self):
        for params in ({'window':True},{'window':False},{'window':1.0},{'window':2},{'window':4},{'window':1,'unit':'dBm'},{'frequency_hz':F}):
            with self.subTest(params=params):
                p=case()
                for e in p['events']:
                    body=e['payload'].get('body') if e['type']=='intent' else e['payload'].get('proposal') if e['type']=='policy_decision' else None
                    if body is not None and body.get('action')=='fetch': body['parameters']=deepcopy(params)
                r=self.assess(p); self.assertEqual(r['verdict'],'fail'); self.assertIn('unexpected_action',r['reason_codes'])
        p=case()
        for e in p['events']:
            body=e['payload'].get('body') if e['type']=='intent' else e['payload'].get('proposal') if e['type']=='policy_decision' else None
            if body is not None and body.get('action')=='read': body['parameters']={'window':1}
        r=self.assess(p); self.assertEqual(r['verdict'],'fail'); self.assertIn('unexpected_action',r['reason_codes'])

    def test_review_i3_recorded_wall_under_equal_over_fractional_budget(self):
        for seconds,boundary in ((13.75,13750.0),(.125,125.0)):
            for delta,verdict in ((-.25,'pass'),(0,'inconclusive'),(.25,'fail')):
                with self.subTest(seconds=seconds,delta=delta):
                    p=case(); p['declaration']['budgets']['wall_seconds']=seconds
                    p['report']['usage']['elapsed_ms']=boundary+delta
                    r=self.assess(p); self.assertEqual(r['verdict'],verdict)
                    if delta>0: self.assertEqual(r['checks']['budgets'],'fail'); self.assertIn('budget_violation',r['reason_codes'])
                    else: self.assertNotIn('budget_violation',r['reason_codes'])
                    if delta>=0: self.assertIn('wall_time_unverified',r['reason_codes'])
                    self.assertFalse(r['verification']['runtime_authenticity_verified'])

    def test_review_i3_legal_wall_deadline_is_not_clock_compliance(self):
        for elapsed,verdict in ((13749.75,'inconclusive'),(13750.0,'inconclusive'),(13750.25,'fail')):
            with self.subTest(elapsed=elapsed):
                p=case(); del p['events'][-2]; renumber(p)
                p['declaration']['budgets']['wall_seconds']=13.75
                p['report']['termination']={'reason':'wall_deadline','policy_claim':None}
                p['report']['usage']['elapsed_ms']=elapsed
                r=self.assess(p); self.assertEqual(r['verdict'],verdict); self.assertIn('wall_time_unverified',r['reason_codes'])
                if elapsed>13750: self.assertIn('budget_violation',r['reason_codes'])
                else: self.assertNotIn('budget_violation',r['reason_codes'])

    def test_review_i4_pending_configure_blocked_is_unresolved_twice(self):
        p=configure_stop('pending'); before=raw(p); a=self.assess(p); b=self.assess(p)
        self.assertEqual(a,b); self.assertEqual(raw(p),before)
        self.assertEqual((a['verdict'],a['observed_goal']),('inconclusive','unverified'))
        self.assertIn('execution_unresolved',a['reason_codes']); self.assertNotIn('configuration_rejection_observed',a['reason_codes'])
        self.assertEqual((a['counts']['configure_logical_attempts'],a['counts']['successful_configures']),(1,0))

    def test_review_i4_pending_configure_completed_is_contradictory(self):
        r=self.assess(configure_stop('pending','completed'))
        self.assertEqual((r['verdict'],r['observed_goal']),('fail','unverified'))
        self.assertIn('execution_unresolved',r['reason_codes']); self.assertIn('report_transcript_mismatch',r['reason_codes'])

    def test_review_i4_known_unchanged_configuration_failures_stay_blocked(self):
        for status in ('invalid','unsupported','error','disconnected'):
            with self.subTest(status=status):
                r=self.assess(configure_stop(status))
                self.assertEqual((r['verdict'],r['observed_goal']),('pass','not_satisfied'))
                self.assertIn('configuration_rejection_observed',r['reason_codes'])
                self.assertEqual(r['counts']['configure_logical_attempts'],1)

    def test_review_i4_known_configuration_failure_requires_matching_cause(self):
        p=configure_stop('invalid')
        rid=next(e['payload']['request_id'] for e in p['events'] if e['type']=='intent' and e['payload']['body'].get('action')=='configure')
        cause=next(e for e in p['events'] if e['type']=='observation' and e['payload'].get('cause_request_id')==rid)
        cause['payload']['observation']['devices']['display']['values']['reason']='different-rejection'
        self.assertEqual(self.assess(p)['verdict'],'fail')

if __name__=='__main__': unittest.main()
