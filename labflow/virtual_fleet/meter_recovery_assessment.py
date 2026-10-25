"""Conditional synthetic recovery grading from detached memory; no runtime or I/O."""
import hashlib
import json
import math
import re


_PREFIX='meter_recovery_assessment_'
_CODES={'invalid_input','limit_exceeded','internal_error'}
_LIMITS=dict(max_input_bytes=33554432,max_output_bytes=131072,max_events=4096,
    max_event_bytes=524288,max_depth=32,max_nodes=200000,max_path_terms=16,
    min_integer=-9223372036854775808,max_integer=9223372036854775807)
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z',re.ASCII)
_ESCAPE=re.compile(r'["\\\x00-\x1f]')
_STATUSES={'ok','pending','invalid','unsupported','error','disconnected'}
_TYPES={'policy_decision','intent','receipt','observation','transport_retry','error','termination'}
_REPORT=set('schema_version kind run_id runtime_instance_id synthetic hardware_verified ai_model_called policy termination task_outcome cleanup usage evidence unresolved_request_ids assessment'.split())
_EVENT=set('schema_version kind event_id run_id runtime_instance_id sequence type payload'.split())
_BASE=set('status values tick setup_revision synthetic hardware_verified'.split())
_SIGNAL=set('frequency_hz power_dbm bandwidth_hz duty_cycle crest_factor_db modulation'.split())
_SENSOR=set('status valid value unit source_id frequency_hz power_dbm duty_cycle crest_factor_db acquisition_tick acquisition_setup_revision'.split())
_METER=set('status valid value unit quantity source_id input_source_id frequency_hz duty_cycle crest_factor_db acquisition_tick acquisition_setup_revision configuration_revision simulation_basis window'.split())
_CHECKS='event_binding delegation_and_actions conflict_and_configure fresh_sensor fresh_meter budgets rf_arithmetic'.split()
_COUNT='events observations logical_requests transport_retry_markers configure_logical_attempts successful_configures sensor_acquire_intents sensor_read_intents meter_acquire_intents meter_fetch_intents'.split()
_TERMINATIONS=set('policy_stop supervisor_stop decision_budget request_budget tick_budget wall_deadline policy_error invalid_proposal runtime_error runtime_mutation_uncertain evidence_error'.split())


class MeterRecoveryAssessmentError(ValueError):
    def __init__(self,code):
        suffix=code.removeprefix(_PREFIX) if type(code) is str else 'invalid_input'
        self.code=_PREFIX+(suffix if suffix in _CODES else 'invalid_input')
        super().__init__(self.code)


def _fail(code='invalid_input'):
    raise MeterRecoveryAssessmentError(code)


def _fixed(code):
    try: raise MeterRecoveryAssessmentError(code) from None
    except MeterRecoveryAssessmentError as error:
        error.__context__=None; error.__cause__=None
        raise


def _C(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def _H(value):
    return hashlib.sha256(_C(value)).hexdigest()


def _clone(value,limit):
    """Count escaped UTF8 bytes and native nodes before full serialization."""
    used=nodes=0; active=set(); event_starts=[]
    def consume(n):
        nonlocal used
        used+=n
        if used>limit or (event_starts and used-event_starts[-1]>_LIMITS['max_event_bytes']): _fail('limit_exceeded')
    def string(s):
        if len(s)+2>limit-used: _fail('limit_exceeded')
        consume(2)
        for start in range(0,len(s),16384):
            part=s[start:start+16384]
            try: size=len(part.encode('utf-8'))
            except UnicodeError: _fail()
            size+=sum(1 if m[0] in '"\\\b\f\n\r\t' else 5 for m in _ESCAPE.finditer(part))
            consume(size)
        return s
    def walk(x,depth,path):
        nonlocal nodes
        nodes+=1
        if nodes>_LIMITS['max_nodes'] or depth>_LIMITS['max_depth']: _fail('limit_exceeded')
        kind=type(x)
        if kind is str: return string(x)
        if kind is bool: consume(4 if x else 5); return x
        if x is None: consume(4); return None
        if kind is int:
            if not _LIMITS['min_integer']<=x<=_LIMITS['max_integer']: _fail('limit_exceeded')
            consume(len(str(x))); return x
        if kind is float:
            if not math.isfinite(x): _fail()
            consume(len(json.dumps(x,allow_nan=False))); return x
        if kind is not dict and kind is not list: _fail()
        identity=id(x)
        if identity in active: _fail()
        if kind is list and path==('events',) and len(x)>_LIMITS['max_events']: _fail('limit_exceeded')
        if kind is list and path==('declaration','rf_basis','path') and len(x)>_LIMITS['max_path_terms']: _fail('limit_exceeded')
        active.add(identity); consume(2)
        try:
            if kind is dict:
                result={}
                for i,(key,item) in enumerate(x.items()):
                    if type(key) is not str: _fail()
                    if i: consume(1)
                    cloned_key=walk(key,depth+1,path+('<key>',)); consume(1)
                    result[cloned_key]=walk(item,depth+1,path+(key,))
                return result
            result=[]
            for i,item in enumerate(x):
                if i: consume(1)
                event=path==('events',)
                if event: event_starts.append(used)
                try: result.append(walk(item,depth+1,path+(i,)))
                finally:
                    if event: event_starts.pop()
            return result
        finally: active.remove(identity)
    copied=walk(value,0,())
    encoded=_C(copied)
    if len(encoded)>limit: _fail('limit_exceeded')
    return copied,encoded


def _want(condition):
    if not condition: _fail()


def _obj(x,keys=None):
    _want(type(x) is dict and (keys is None or set(x)==set(keys)))


def _array(x):
    _want(type(x) is list)


def _int(x,minimum=0):
    _want(type(x) is int and x>=minimum)


def _num(x,minimum=None,strict=False):
    _want(type(x) in (int,float) and math.isfinite(x))
    if minimum is not None: _want(x>minimum if strict else x>=minimum)


def _text(x):
    _want(type(x) is str and bool(x.strip()))


def _identifier(x):
    _want(type(x) is str and _ID.fullmatch(x) is not None)


def _ids(x):
    _array(x)
    for value in x: _identifier(value)
    _want(len(set(x))==len(x))


def _port(port):
    if type(port) is str: return port
    _obj(port); _text(port.get('kind')); return port['kind']


def _environment(x,node=False):
    _obj(x); _want(_BASE<=set(x)); _text(x['status']); _want(x['status'] in _STATUSES)
    _obj(x['values']); _int(x['tick']); _int(x['setup_revision'])
    _want(x['synthetic'] is True and x['hardware_verified'] is False)
    if 'outputs' in x['values']:
        _obj(x['values']['outputs'])
        for p in x['values']['outputs'].values(): _obj(p)
    if node:
        for name in ('device_id','profile_id','role'): _identifier(x.get(name))


def _shape(packet):
    d,r,events=packet['declaration'],packet['report'],packet['events']
    _obj(d,'schema_version kind goal catalog topology role_actions budgets rf_basis'.split())
    _want(type(d['schema_version']) is int and d['schema_version']==1 and d['kind']=='meter_frequency_recovery_declaration')
    g=d['goal']; _obj(g,'kind dut_id sensor_id meter_id minimum_acquisition_tick allow_meter_frequency_reconfigure'.split())
    _text(g['kind'])
    for name in ('dut_id','sensor_id','meter_id'): _identifier(g[name])
    _want(len({g[n] for n in ('dut_id','sensor_id','meter_id')})==3)
    _int(g['minimum_acquisition_tick']); _want(type(g['allow_meter_frequency_reconfigure']) is bool)
    for key in ('catalog','topology','role_actions'): _obj(d[key])
    b=d['budgets']; _obj(b,'decisions logical_requests ticks wall_seconds transport_retries'.split())
    for key in ('decisions','logical_requests','ticks'): _int(b[key],1)
    _int(b['transport_retries']); _num(b['wall_seconds'],0,True)
    basis=d['rf_basis']; _obj(basis,'simulation_basis source_signal path meter_noise_db meter_gain_error_db external_runtime_mutations'.split())
    _want(basis['simulation_basis']=='declared_synthetic_policy'); _num(basis['meter_noise_db']); _num(basis['meter_gain_error_db'])
    _want(type(basis['external_runtime_mutations']) is bool)
    signal=basis['source_signal']; _obj(signal,_SIGNAL)
    for key in _SIGNAL-{'modulation'}: _num(signal[key])
    _want(signal['frequency_hz']>0 and signal['bandwidth_hz']>0 and 0<signal['duty_cycle']<=1 and signal['crest_factor_db']>=0); _text(signal['modulation'])
    _array(basis['path']); _want(bool(basis['path']))
    for term in basis['path']:
        _obj(term,'device_id input_port output_port loss_db'.split())
        for key in ('device_id','input_port','output_port'): _identifier(term[key])
        _num(term['loss_db'],0)
    _obj(r,_REPORT); _want(type(r['schema_version']) is int and r['schema_version']==1 and r['kind']=='virtual_fleet_harness_result')
    for key in ('run_id','runtime_instance_id'): _identifier(r[key])
    _want(r['synthetic'] is True and r['hardware_verified'] is False and r['ai_model_called'] is False)
    _obj(r['policy'],('kind','id')); _identifier(r['policy']['kind']); _identifier(r['policy']['id'])
    _obj(r['termination'],('reason','policy_claim')); _text(r['termination']['reason'])
    claim=r['termination']['policy_claim']
    _want(claim is None or (type(claim) is str and claim in {'completed','blocked','failed','unsupported'}))
    _obj(r['cleanup'],('status','evidence_refs')); _obj(r['assessment'],('status','verdict','evaluator_id','evidence_refs','summary_code'))
    _text(r['task_outcome']); _text(r['cleanup']['status']); _array(r['cleanup']['evidence_refs'])
    _obj(r['usage'],'decisions logical_requests transport_retries tick_delta reserved_ticks elapsed_ms'.split())
    for key in set(r['usage'])-{'elapsed_ms'}: _int(r['usage'][key])
    _num(r['usage']['elapsed_ms'],0)
    _obj(r['evidence'],('measurement_refs','operator_transcript_ref')); _ids(r['evidence']['measurement_refs']); _text(r['evidence']['operator_transcript_ref']); _ids(r['unresolved_request_ids'])
    _array(events)
    for event in events:
        _obj(event,_EVENT); _want(type(event['schema_version']) is int and event['schema_version']==1 and event['kind']=='operator_event')
        for key in ('event_id','run_id','runtime_instance_id'): _identifier(event[key])
        _int(event['sequence'],1); _text(event['type']); _want(event['type'] in _TYPES); p=event['payload']; _obj(p)
        kind=event['type']
        if kind=='intent':
            _obj(p,('request_id','operation','body','logical_request')); _identifier(p['request_id']); _int(p['logical_request'],1); _obj(p['body'])
            _text(p['operation']); _want(p['operation'] in {'execute','advance'})
            if p['operation']=='execute':
                _obj(p['body'],('device_id','action','parameters')); _identifier(p['body']['device_id']); _identifier(p['body']['action']); _obj(p['body']['parameters'])
            else: _obj(p['body'],('ticks',)); _int(p['body']['ticks'],1)
        elif kind=='receipt':
            _obj(p,('request_id','result')); _identifier(p['request_id']); _environment(p['result'])
        elif kind=='observation':
            _want({'observation'}<=set(p)<={'observation','cause_request_id'})
            if 'cause_request_id' in p: _identifier(p['cause_request_id'])
            o=p['observation']; _obj(o,('tick','setup_revision','synthetic','hardware_verified','devices')); _int(o['tick']); _int(o['setup_revision']); _obj(o['devices'])
            _want(o['synthetic'] is True and o['hardware_verified'] is False)
            for key,node in o['devices'].items(): _identifier(key); _environment(node,True)
        elif kind=='transport_retry':
            _obj(p,('request_id','retry')); _identifier(p['request_id']); _int(p['retry'],1)
        elif kind=='error': _identifier(p.get('code'))
        elif kind=='termination':
            _obj(p,('code','unresolved_request_ids')); _want(p['code']=='run_terminated'); _ids(p['unresolved_request_ids'])
        elif kind=='policy_decision':
            _obj(p.get('proposal')); proposal=p['proposal']; _text(proposal.get('kind'))
            if proposal['kind']=='stop':
                _obj(proposal,('kind','claim','reason')); _text(proposal['claim']); _want(proposal['claim'] in {'completed','blocked','failed','unsupported'}); _text(proposal['reason'])


class _Run:
    def __init__(self,p):
        self.p=p; self.d=p['declaration']; self.r=p['report']; self.events=p['events']; self.g=self.d['goal']; self.basis=self.d['rf_basis']
        self.dut,self.sensor,self.meter=(self.g[k] for k in ('dut_id','sensor_id','meter_id'))
        self.checks=dict.fromkeys(_CHECKS,'pass'); self.checks.update(fresh_sensor='inconclusive',fresh_meter='inconclusive',rf_arithmetic='inconclusive')
        self.counts=dict.fromkeys(_COUNT,0); self.counts['events']=len(self.events)
        self.reasons=set(); self.doubts=set(); self.refs={}; self.violations=[]; self.unsupported=None
        self.first_error=self.first_failed=None
        self.profiles={}; self.nodes={}; self.edges={}; self.expected={}; self.numeric=True
        self.initial=self.last=self.last_ref=self.proposal=None
        self.intents={}; self.receipted=set(); self.caused=set(); self.pending=set(); self.retries={}
        self.terminal=None; self.seen_ids=set(); self.decisions=0
        self.sensor_acq=self.sensor_read=self.meter_acq=self.meter_fetch=None
        self.conflict=self.configured=self.rejected=None; self.block_evidence=False
        self.meter_configuration=None
        self.observed_sensor=self.observed_meter=None
        self._metadata()
    def fail(self,check,code,ref=None):
        self.checks[check]='fail'; self.reasons.add(code)
        if ref and ref not in self.violations and len(self.violations)<8: self.violations.append(ref)
    def doubt(self,check,code):
        if self.checks[check]!='fail': self.checks[check]='inconclusive'
        self.reasons.add(code); self.doubts.add(code)
    def _metadata(self):
        _array(self.d['catalog'].get('profiles')); _want(bool(self.d['catalog']['profiles']))
        for profile in self.d['catalog']['profiles']:
            _obj(profile); _identifier(profile.get('profile_id')); _identifier(profile.get('role')); _obj(profile.get('ports'))
            _want(profile['profile_id'] not in self.profiles)
            for side in ('inputs','outputs'):
                _obj(profile['ports'].get(side))
                for name,port in profile['ports'][side].items(): _identifier(name); _text(_port(port))
            self.profiles[profile['profile_id']]=profile
        t=self.d['topology']; _array(t.get('devices')); _array(t.get('connections')); _want(bool(t['devices']))
        for node in t['devices']:
            _obj(node); _identifier(node.get('id')); _identifier(node.get('profile_id'))
            _want(node['id'] not in self.nodes and node['profile_id'] in self.profiles); self.nodes[node['id']]=self.profiles[node['profile_id']]
        for edge in t['connections']:
            _obj(edge,('source','target','kind')); _text(edge['kind'])
            for side,direction in [('source','outputs'),('target','inputs')]:
                endpoint=edge[side]; _obj(endpoint,('device_id','port')); _identifier(endpoint['device_id']); _identifier(endpoint['port'])
                _want(endpoint['device_id'] in self.nodes)
                ports=self.nodes[endpoint['device_id']]['ports'][direction]
                _want(endpoint['port'] in ports and _port(ports[endpoint['port']])==edge['kind'])
            target=(edge['target']['device_id'],edge['target']['port']); _want(target not in self.edges)
            self.edges[target]=(edge['source']['device_id'],edge['source']['port'],edge['kind'])
        needed=[(self.dut,'dut',('start',)),(self.sensor,'power_sensor',('acquire','read')),(self.meter,'power_meter',('acquire','fetch','configure'))]
        for identity,role,actions in needed:
            if identity not in self.nodes or self.nodes[identity]['role']!=role: self.unsupported='unsupported_target'; continue
            declarations=self.d['role_actions'].get(role)
            if type(declarations) is not dict or any(a not in declarations for a in actions): self.unsupported='unsupported_target'; continue
            for action in actions:
                declaration=declarations[action]; _obj(declaration); _obj(declaration.get('parameters'))
                for name,spec in declaration['parameters'].items():
                    _identifier(name); _obj(spec); _text(spec.get('type')); _want(type(spec.get('required',False)) is bool)
                    if spec.get('required',False) and not (action=='configure' and name=='frequency_hz'): self.unsupported='unsupported_target'
                if action=='configure' and declaration['parameters'].get('frequency_hz',{}).get('type')!='number': self.unsupported='unsupported_target'
        if self.g['kind']!='acquire_fresh_rf_sensor_meter' or self.basis['external_runtime_mutations']: self.unsupported='unsupported_target'
        if self.r['policy']!={'kind':'fixture','id':'rf_meter_frequency_recovery_v1'} or self.r['termination']['reason'] not in _TERMINATIONS: self.unsupported='unsupported_target'
        empty=dict(status='not_assessed',verdict=None,evaluator_id=None,evidence_refs=[],summary_code=None)
        if self.r['task_outcome']!='not_assessed' or self.r['cleanup']!={'status':'not_assessed','evidence_refs':[]} or self.r['assessment']!=empty: self.unsupported='report_already_assessed'
        if self.edges.get((self.sensor,'rf')) is None or self.edges.get((self.meter,'sensor'))!=(self.sensor,'measurement','measurement'):
            self.fail('event_binding','measurement_binding_mismatch')
        power=self.basis['source_signal']['power_dbm']; self.expected[(self.dut,'rf')]=power; previous=(self.dut,'rf'); visited={self.dut}
        for term in self.basis['path']:
            identity=term['device_id']
            if identity not in self.nodes or identity in visited:
                self.fail('event_binding','measurement_binding_mismatch'); continue
            visited.add(identity); profile=self.nodes[identity]
            if self.edges.get((identity,term['input_port']))!=(*previous,'rf'): self.fail('event_binding','measurement_binding_mismatch')
            if term['output_port'] not in profile['ports']['outputs'] or _port(profile['ports']['outputs'][term['output_port']])!='rf': self.fail('event_binding','measurement_binding_mismatch')
            if profile['role'] not in {'attenuator','rf_switch','coupler'} or (profile['role']=='coupler' and term['output_port']!='coupled'): self.numeric=False
            params=profile.get('simulation_parameters',{}); _obj(params)
            if any(key in params for key in ('loss_table','gain_table')): self.numeric=False
            if sum(1 for target,source in self.edges.items() if target[0]==identity and source[2]=='rf')>1: self.numeric=False
            try: power=math.fsum([power,-term['loss_db']]) if power is not None else None
            except (ValueError,OverflowError): self.numeric=False; power=None
            if power is not None and not math.isfinite(power): self.numeric=False; power=None
            previous=(identity,term['output_port']); self.expected[previous]=power
        if self.edges.get((self.sensor,'rf'))!=(*previous,'rf'): self.fail('event_binding','measurement_binding_mismatch')
        self.expected_power=power
        meter_parameters=self.nodes.get(self.meter,{}).get('simulation_parameters',{}); _obj(meter_parameters)
        noise=meter_parameters.get('noise_db',0); _num(noise)
        if noise!=0 or self.basis['meter_noise_db']!=0 or self.basis['meter_gain_error_db']!=0: self.numeric=False
        if not self.numeric: self.doubt('rf_arithmetic','unsupported_numeric_model')
    def _config(self,o):
        node=o['devices'].get(self.meter)
        if node is None: return None
        values=node['values']; cfg=values.get('configuration'); revision=values.get('configuration_revision')
        if cfg is None or revision is None: return None
        _obj(cfg); _int(revision)
        if 'frequency_hz' in cfg: _num(cfg['frequency_hz'],0,True)
        if 'window' in cfg: _int(cfg['window'],1)
        return cfg,revision
    def _supported_config(self,c):
        return c is not None and all(c[0].get(k)==v for k,v in [('measurement_mode','on_average'),('unit','dBm'),('window',1),('trigger_source','immediate')])
    def _sample(self,o,identity,fields,ref):
        node=o['devices'].get(identity)
        if node is None: return None
        sample=node['values'].get('outputs',{}).get('measurement')
        if sample is None or sample.get('valid') is not True or sample.get('status')!='ok': return None
        _want(fields<=set(sample))
        for name in ('value','frequency_hz','duty_cycle','crest_factor_db'): _num(sample[name])
        _int(sample['acquisition_tick']); _int(sample['acquisition_setup_revision']); _text(sample['unit']); _identifier(sample['source_id'])
        if node['status']!='ok': self.fail('fresh_sensor' if identity==self.sensor else 'fresh_meter','measurement_binding_mismatch',ref); return None
        return sample
    def _sensor_ok(self,o,ref):
        sample=self._sample(o,self.sensor,_SENSOR,ref)
        if sample is None: return None
        _num(sample['power_dbm']); self.observed_sensor=sample['value']
        good=(sample['source_id']==self.sensor and sample['unit']=='dBm' and sample['value']==sample['power_dbm'] and
              all(sample[k]==self.basis['source_signal'][k] for k in ('frequency_hz','duty_cycle','crest_factor_db')))
        if not good: self.fail('fresh_sensor','measurement_binding_mismatch',ref); return None
        if self.numeric and abs(sample['value']-self.expected_power)>1e-9: self.fail('rf_arithmetic','arithmetic_mismatch',ref)
        acquisition=self.sensor_acq
        if acquisition is None: return None
        receipt=acquisition.get('receipt'); before=acquisition['before']
        minimum=max(self.g['minimum_acquisition_tick'],self.initial['tick']+1,self.configured['receipt']['tick']+1 if self.configured else 0)
        if receipt is None or before is None: return None
        if (sample['acquisition_setup_revision']!=o['setup_revision'] or receipt['setup_revision']!=o['setup_revision'] or
            before['setup_revision']!=o['setup_revision'] or not max(before['tick']+1,minimum)<=sample['acquisition_tick']<=o['tick']):
            self.fail('fresh_sensor','stale_measurement',ref); return None
        dut=o['devices'].get(self.dut); source=o['devices'].get(self.basis['path'][-1]['device_id'])
        if dut is None or source is None or dut['status']!='ok' or source['status']!='ok' or not dut['values'].get('outputs',{}).get('rf',{}).get('valid') or not source['values'].get('outputs',{}).get(self.basis['path'][-1]['output_port'],{}).get('valid'):
            self.fail('fresh_sensor','measurement_binding_mismatch',ref); return None
        self.refs['sensor_acquire']=acquisition['event_id']; return sample
    def _meter_ok(self,o,sensor,ref):
        sample=self._sample(o,self.meter,_METER,ref)
        if sample is None: return None
        self.observed_meter=sample['value']; _identifier(sample['input_source_id']); _int(sample['configuration_revision']); _int(sample['window'],1)
        calibration=o['devices'][self.meter]['values'].get('calibration_state')
        good=(sample['source_id']==self.meter and sample['input_source_id']==self.sensor and sample['unit']=='dBm' and
            sample['quantity']=='on_average' and sample['window']==1 and sample['simulation_basis']=='declared_synthetic_policy' and
            (calibration is None or calibration=='valid'))
        if not good: self.fail('fresh_meter','measurement_binding_mismatch',ref); return None
        if self.numeric and abs(sample['value']-self.expected_power)>1e-9: self.fail('rf_arithmetic','arithmetic_mismatch',ref)
        if sensor is None or self.meter_acq is None: return None
        acquisition=self.meter_acq; before=acquisition['before']; receipt=acquisition.get('receipt'); cfg=self._config(o)
        if before is None or receipt is None or cfg is None: return None
        if (sample['acquisition_setup_revision']!=o['setup_revision'] or before['setup_revision']!=o['setup_revision'] or receipt['setup_revision']!=o['setup_revision'] or
            sample['configuration_revision']!=cfg[1] or receipt['values'].get('configuration_revision')!=cfg[1] or
            not max(before['tick'],sensor['acquisition_tick'])<sample['acquisition_tick']<=o['tick']):
            self.fail('fresh_meter','stale_measurement',ref); return None
        if (any(sample[k]!=sensor[k] for k in ('frequency_hz','duty_cycle','crest_factor_db')) or
            abs(cfg[0].get('frequency_hz',sample['frequency_hz']+2)-sensor['frequency_hz'])>1 or
            acquisition.get('sensor_signature')!=sensor or self.sensor_read is None or self.sensor_read['sequence']>=acquisition['sequence']):
            self.fail('fresh_meter','measurement_binding_mismatch',ref); return None
        if abs(sample['value']-sensor['power_dbm'])>1e-9: self.fail('rf_arithmetic','arithmetic_mismatch',ref)
        self.refs['meter_acquire']=acquisition['event_id']; return sample
    def _math(self,o,ref):
        for (identity,port),expected in self.expected.items():
            node=o['devices'].get(identity); packet=None if node is None else node['values'].get('outputs',{}).get(port)
            if packet is None or packet.get('valid') is not True or packet.get('status')!='ok': continue
            _want((_SIGNAL|{'status','valid','source_id'})<=set(packet))
            for k in _SIGNAL-{'modulation'}: _num(packet[k])
            if node['status']!='ok' or packet['source_id']!=identity or any(packet[k]!=self.basis['source_signal'][k] for k in _SIGNAL-{'power_dbm'}):
                self.fail('rf_arithmetic','measurement_binding_mismatch',ref)
            if self.numeric and expected is not None and abs(packet['power_dbm']-expected)>1e-9: self.fail('rf_arithmetic','arithmetic_mismatch',ref)
    def _intent(self,e):
        p=e['payload']; rid=p['request_id']; self.counts['logical_requests']+=1
        if rid in self.intents:
            self.fail('event_binding','event_order_mismatch',e['event_id']); return
        if p['logical_request']!=self.counts['logical_requests']: self.fail('event_binding','event_order_mismatch',e['event_id'])
        proposal=dict(kind=p['operation'],**p['body'])
        if self.proposal!=proposal: self.fail('event_binding','event_binding_mismatch',e['event_id'])
        rec=dict(p,before=self.last,event_id=e['event_id'],sequence=e['sequence'],receipt=None,cause=None)
        self.intents[rid]=rec; self.pending.add(rid)
        if self.last is None: self.doubt('event_binding','evidence_incomplete')
        if p['operation']=='advance':
            if p['body']['ticks']!=1: self.fail('delegation_and_actions','unexpected_action',e['event_id'])
            return
        body=p['body']; identity,action,params=body['device_id'],body['action'],body['parameters']
        allowed={(self.dut,'start'),(self.sensor,'acquire'),(self.sensor,'read'),(self.meter,'acquire'),(self.meter,'fetch'),(self.meter,'configure')}
        if (identity,action) not in allowed or (action!='configure' and params): self.fail('delegation_and_actions','unexpected_action',e['event_id'])
        if identity==self.sensor and action=='acquire': self.counts['sensor_acquire_intents']+=1
        if identity==self.sensor and action=='read': self.counts['sensor_read_intents']+=1
        if identity==self.meter and action=='acquire':
            self.counts['meter_acquire_intents']+=1
            sensor=self._sensor_ok(self.last,self.last_ref) if self.last is not None else None
            rec['sensor_signature']=sensor
            if self.sensor_read is None: self.fail('fresh_meter','missing_required_action',e['event_id'])
        if identity==self.meter and action=='fetch': self.counts['meter_fetch_intents']+=1
        if identity==self.meter and action=='configure':
            self.counts['configure_logical_attempts']+=1; self.refs['configure']=e['event_id']
            if self.counts['configure_logical_attempts']>1: self.fail('conflict_and_configure','configure_attempts_exceeded',e['event_id'])
            if not self.g['allow_meter_frequency_reconfigure']: self.fail('delegation_and_actions','reconfigure_without_delegation',e['event_id'])
            if set(params)!={'frequency_hz'}: self.fail('conflict_and_configure','configure_parameter_mismatch',e['event_id'])
            else:
                _num(params['frequency_hz'],0,True)
                if self.last is not None:
                    sensor=self._sensor_ok(self.last,self.last_ref)
                    if sensor is None or params['frequency_hz']!=sensor['frequency_hz']: self.fail('conflict_and_configure','configure_parameter_mismatch',e['event_id'])
            if self.conflict is None or self.last is None or self.conflict['revision']!=self.last['setup_revision']:
                self.fail('conflict_and_configure','conflict_not_observed',e['event_id'])
            rec['before_config']=None if self.last is None else self._config(self.last)
    def _receipt(self,e):
        p=e['payload']; rid=p['request_id']; receipt=p['result']; ref=e['event_id']
        if receipt['status'] in {'invalid','unsupported','error','disconnected'} and self.first_failed is None: self.first_failed=ref
        rec=self.intents.get(rid)
        if rec is None or rid in self.receipted:
            self.fail('event_binding','event_order_mismatch',ref); return
        self.receipted.add(rid); self.pending.discard(rid); rec['receipt']=receipt; rec['receipt_ref']=ref
        before=rec['before']
        if rec['operation']=='advance':
            _obj(receipt,_BASE); _obj(receipt['values'],('advanced_ticks',)); _int(receipt['values']['advanced_ticks'],1)
            if receipt['status']!='ok' or receipt['values']['advanced_ticks']!=1: self.fail('event_binding','event_binding_mismatch',ref)
            if before is not None and (receipt['tick']!=before['tick']+1 or receipt['setup_revision']<before['setup_revision']): self.fail('event_binding','event_order_mismatch',ref)
            return
        for key in ('device_id','profile_id','role'): _identifier(receipt.get(key))
        _want(type(receipt.get('setup_changed')) is bool)
        body=rec['body']; identity=body['device_id']; profile=self.nodes.get(identity)
        if profile is None or receipt['device_id']!=identity or receipt['profile_id']!=profile['profile_id'] or receipt['role']!=profile['role']:
            self.fail('event_binding','event_binding_mismatch',ref)
        if before is not None and (receipt['tick']!=before['tick'] or receipt['setup_revision']!=before['setup_revision']+int(receipt['setup_changed'])):
            self.fail('event_binding','event_order_mismatch',ref)
        if receipt['status'] in {'ok','pending'} and body['action']=='acquire':
            if identity==self.sensor: self.sensor_acq=rec; self.sensor_read=None
            if identity==self.meter: self.meter_acq=rec; self.meter_fetch=None
        if identity==self.meter and body['action']=='configure':
            old=rec.get('before_config'); values=receipt['values']; cfg=values.get('configuration'); revision=values.get('configuration_revision')
            if old is None: self.doubt('conflict_and_configure','evidence_incomplete'); return
            if receipt['status']=='ok':
                expected=dict(old[0],**body['parameters'])
                if not receipt['setup_changed'] or cfg!=expected or revision!=old[1]+1 or values.get('outputs')!={}: self.fail('conflict_and_configure','configure_revision_mismatch',ref)
                self.counts['successful_configures']+=1; self.configured=rec
                self.sensor_acq=self.sensor_read=self.meter_acq=self.meter_fetch=None
            else:
                if receipt['setup_changed'] or cfg!=old[0] or revision!=old[1]: self.fail('conflict_and_configure','configure_revision_mismatch',ref)
                self.rejected=rec
    def _observation(self,e):
        p=e['payload']; o=p['observation']; ref=e['event_id']; self.counts['observations']+=1
        if set(o['devices'])!=set(self.nodes):
            if set(o['devices'])-set(self.nodes): self.fail('event_binding','event_binding_mismatch',ref)
            else: self.doubt('event_binding','evidence_incomplete')
        for identity,node in o['devices'].items():
            profile=self.nodes.get(identity)
            if profile is None or node['device_id']!=identity or node['profile_id']!=profile['profile_id'] or node['role']!=profile['role'] or node['tick']!=o['tick'] or node['setup_revision']!=o['setup_revision']:
                self.fail('event_binding','event_binding_mismatch',ref)
        rec=None
        if self.initial is None:
            self.initial=o; self.refs['initial']=ref
            if 'cause_request_id' in p: self.fail('event_binding','event_order_mismatch',ref)
            cfg=self._config(o)
            self.meter_configuration=cfg
            if cfg is not None and not self._supported_config(cfg): self.unsupported='unsupported_target'
            if cfg is None: self.doubt('event_binding','evidence_incomplete')
        else:
            if o['tick']<self.last['tick'] or o['setup_revision']<self.last['setup_revision']: self.fail('event_binding','event_order_mismatch',ref)
            rid=p.get('cause_request_id'); rec=self.intents.get(rid)
            if rec is None or rec.get('receipt') is None or rid in self.caused: self.fail('event_binding','event_binding_mismatch',ref)
            else:
                self.caused.add(rid); rec['cause']=e
                if (o['tick'],o['setup_revision'])!=(rec['receipt']['tick'],rec['receipt']['setup_revision']): self.fail('event_binding','event_binding_mismatch',ref)
            current=self._config(o)
            configuring=rec is not None and rec['operation']=='execute' and rec['body']['device_id']==self.meter and rec['body']['action']=='configure'
            if current is None:
                self.doubt('conflict_and_configure','evidence_incomplete')
            elif configuring:
                self.meter_configuration=current
            elif self.meter_configuration is not None and current!=self.meter_configuration:
                self.fail('conflict_and_configure','configure_revision_mismatch',ref)
        self._math(o,ref)
        sensor=self._sensor_ok(o,ref); meter=self._meter_ok(o,sensor,ref)
        if rec is not None and rec.get('receipt') is not None and rec['operation']=='execute':
            receipt=rec['receipt']; body=rec['body']; identity=body['device_id']; node=o['devices'].get(identity)
            if node is not None:
                values=node['values']
                if identity==self.meter and (receipt['status'] in {'ok','pending'} or receipt['values'].get('reason')=='sensor_frequency_setting_conflict'):
                    if any(receipt['values'].get(k)!=values.get(k) for k in ('configuration','configuration_revision')): self.fail('conflict_and_configure','configure_revision_mismatch',ref)
                if body['action'] in {'read','fetch'} and receipt['status']=='ok':
                    if receipt['values'].get('outputs',{})!=values.get('outputs',{}): self.fail('event_binding','measurement_binding_mismatch',ref)
                    elif identity==self.sensor and sensor is not None: self.sensor_read=dict(sequence=e['sequence'],sample=sensor,event_id=ref); self.refs['sensor_read']=ref
                    elif identity==self.meter and meter is not None: self.meter_fetch=dict(sequence=e['sequence'],sample=meter,event_id=ref); self.refs['meter_fetch']=ref
                if identity==self.meter and body['action']=='acquire' and receipt['status']=='invalid' and receipt['values'].get('reason')=='sensor_frequency_setting_conflict':
                    cfg=self._config(o)
                    if (node['status']=='invalid' and values.get('reason')=='sensor_frequency_setting_conflict' and not values.get('outputs') and not receipt['values'].get('outputs') and
                        sensor is not None and self.sensor_read is not None and cfg is not None and abs(cfg[0].get('frequency_hz',sensor['frequency_hz'])-sensor['frequency_hz'])>1):
                        self.conflict=dict(revision=o['setup_revision'],event_id=ref); self.refs['conflict']=ref
                if receipt['status'] in {'invalid','error','disconnected','unsupported'} and body['action']=='acquire' and receipt['values'].get('reason')!='sensor_frequency_setting_conflict':
                    if node['status']==receipt['status'] and values.get('reason')==receipt['values'].get('reason') and values.get('reason') and not values.get('outputs'):
                        self.block_evidence=True; self.refs['readiness']=ref
                if identity==self.meter and body['action']=='configure':
                    if self.configured is rec:
                        if values.get('outputs')!={}: self.fail('conflict_and_configure','configure_revision_mismatch',ref)
                    elif self.rejected is rec:
                        old=rec.get('before_config')
                        if old is not None and self._config(o)!=old: self.fail('conflict_and_configure','configure_revision_mismatch',ref)
                        elif node['status']==receipt['status']: self.refs['rejection']=ref
        self.last=o; self.last_ref=ref; self.refs['final']=ref
    def scan(self):
        for i,e in enumerate(self.events,1):
            ref=e['event_id']; kind=e['type']; p=e['payload']
            if e['sequence']!=i or ref!=f'event:{i}' or ref in self.seen_ids: self.fail('event_binding','event_order_mismatch',ref)
            self.seen_ids.add(ref)
            if e['run_id']!=self.r['run_id'] or e['runtime_instance_id']!=self.r['runtime_instance_id']: self.fail('event_binding','event_binding_mismatch',ref)
            if self.terminal is not None: self.fail('event_binding','event_order_mismatch',ref)
            if kind=='policy_decision': self.decisions+=1; self.proposal=p['proposal']
            elif kind=='intent': self._intent(e)
            elif kind=='receipt': self._receipt(e)
            elif kind=='observation': self._observation(e)
            elif kind=='transport_retry':
                self.counts['transport_retry_markers']+=1; rid=p['request_id']
                if rid not in self.pending or p['retry']!=self.retries.get(rid,0)+1: self.fail('event_binding','event_order_mismatch',ref)
                self.retries[rid]=p['retry']
            elif kind=='error':
                if self.first_error is None: self.first_error=ref
                self.doubt('event_binding','execution_unresolved')
            elif kind=='termination':
                self.terminal=e; self.refs['termination']=ref
        return self.finish()
    def finish(self):
        complete=self.terminal is not None and bool(self.events) and self.events[-1] is self.terminal
        reason=self.r['termination']['reason']; claim=self.r['termination']['policy_claim']; usage=self.r['usage']; budgets=self.d['budgets']
        if not complete or self.initial is None: self.doubt('event_binding','evidence_incomplete')
        if complete:
            if set(self.r['unresolved_request_ids'])!=self.pending or set(self.terminal['payload']['unresolved_request_ids'])!=self.pending: self.fail('event_binding','report_transcript_mismatch',self.terminal['event_id'])
            if usage['logical_requests']!=self.counts['logical_requests'] or usage['transport_retries']!=self.counts['transport_retry_markers']: self.fail('budgets','report_transcript_mismatch')
            decision_ok=usage['decisions']==self.decisions
            callback=reason in {'policy_error','invalid_proposal','evidence_error'} and usage['decisions']==self.decisions+1
            if not decision_ok and not callback: self.fail('budgets','report_transcript_mismatch')
            if callback or reason=='evidence_error': self.doubt('budgets','evidence_incomplete')
            reserved=sum(self.intents[rid]['operation']=='advance' for rid in self.pending)
            if usage['reserved_ticks']!=reserved: self.fail('budgets','report_transcript_mismatch')
            if self.initial is not None and self.last is not None and usage['tick_delta']!=self.last['tick']-self.initial['tick']: self.fail('budgets','report_transcript_mismatch')
            if reason=='policy_stop' and (self.proposal is None or self.proposal.get('kind')!='stop' or self.proposal.get('claim')!=claim): self.fail('event_binding','report_transcript_mismatch')
        elif usage['logical_requests']<self.counts['logical_requests'] or usage['transport_retries']<self.counts['transport_retry_markers']: self.fail('budgets','report_transcript_mismatch')
        if self.pending:
            self.doubt('event_binding','execution_unresolved')
            if complete and claim=='completed': self.fail('event_binding','report_transcript_mismatch')
        if complete and set(self.intents)-self.caused:
            if claim=='completed': self.fail('event_binding','missing_required_action')
            else: self.doubt('event_binding','evidence_incomplete')
        for key,count in [('decisions',usage['decisions']),('logical_requests',max(usage['logical_requests'],self.counts['logical_requests'])),('transport_retries',max(usage['transport_retries'],self.counts['transport_retry_markers'])),('ticks',usage['tick_delta']+usage['reserved_ticks'])]:
            if count>budgets[key]: self.fail('budgets','budget_violation')
        if self.last is not None and self.initial is not None and self.last['tick']-self.initial['tick']>budgets['ticks']: self.fail('budgets','budget_violation')
        if reason in {'decision_budget','request_budget','tick_budget','supervisor_stop'}: self.doubt('budgets','budget_exhausted')
        if reason=='wall_deadline' or usage['elapsed_ms']>=budgets['wall_seconds']*1000: self.doubt('budgets','wall_time_unverified')
        if reason in {'runtime_error','runtime_mutation_uncertain','policy_error','invalid_proposal','evidence_error'}: self.doubt('event_binding','execution_unresolved')
        if claim=='completed' and self.r['unresolved_request_ids']: self.fail('event_binding','report_transcript_mismatch')
        if reason!='policy_stop' and claim is not None: self.fail('event_binding','report_transcript_mismatch')
        if self.r['evidence']['operator_transcript_ref']!='artifact:operator_events': self.fail('event_binding','report_transcript_mismatch')
        for ref in self.r['evidence']['measurement_refs']:
            matches=[e for e in self.events if e['event_id']==ref]
            if not matches:
                if complete: self.fail('event_binding','report_transcript_mismatch')
                else: self.doubt('event_binding','evidence_incomplete')
            elif matches[0]['type']!='observation': self.fail('event_binding','report_transcript_mismatch',ref)
            else:
                obs=matches[0]['payload']['observation']
                valid=False
                for identity,node in obs['devices'].items():
                    sample=node['values'].get('outputs',{}).get('measurement')
                    if sample is not None and node['status']=='ok' and sample.get('valid') is True and sample.get('status')=='ok' and sample.get('source_id')==identity:
                        tick=sample.get('acquisition_tick'); value=sample.get('value'); unit=sample.get('unit')
                        valid |= (type(value) in (int,float) and math.isfinite(value) and type(unit) is str and bool(unit) and
                                  type(tick) is int and 0<=tick<=obs['tick'] and sample.get('acquisition_setup_revision')==obs['setup_revision'])
                if not valid: self.fail('event_binding','report_transcript_mismatch',ref)
        sensor=self._sensor_ok(self.last,self.last_ref) if self.last is not None else None
        meter=self._meter_ok(self.last,sensor,self.last_ref) if self.last is not None else None
        sensor_read=sensor is not None and self.sensor_read is not None and self.sensor_read['sample']==sensor
        meter_fetch=meter is not None and self.meter_fetch is not None and self.meter_fetch['sample']==meter
        if sensor_read and self.checks['fresh_sensor']!='fail': self.checks['fresh_sensor']='pass'
        if meter_fetch and self.checks['fresh_meter']!='fail': self.checks['fresh_meter']='pass'
        arithmetic='unsupported' if not self.numeric else 'mismatched' if self.checks['rf_arithmetic']=='fail' else 'matched' if sensor is not None and meter is not None else 'not_available'
        if arithmetic=='matched': self.checks['rf_arithmetic']='pass'
        goal=complete and not self.pending and self.checks['event_binding']=='pass' and sensor_read and meter_fetch and arithmetic=='matched'
        denied=complete and reason=='policy_stop' and claim=='blocked' and self.conflict is not None and not self.g['allow_meter_frequency_reconfigure'] and self.counts['configure_logical_attempts']==0
        rejected=complete and reason=='policy_stop' and claim=='blocked' and self.rejected is not None and 'rejection' in self.refs and self.counts['configure_logical_attempts']==1
        readiness=complete and reason=='policy_stop' and claim=='blocked' and self.block_evidence
        blocked=denied or rejected or readiness
        if blocked:
            for key in ('fresh_sensor','fresh_meter','rf_arithmetic'):
                if self.checks[key]=='inconclusive' and self.numeric: self.checks[key]='not_applicable'
            self.reasons.add('declared_reconfiguration_denied' if denied else 'configuration_rejection_observed' if rejected else 'readiness_block_observed')
        if complete and reason=='policy_stop' and claim=='completed' and not goal:
            if not sensor_read or not meter_fetch:
                self.fail('fresh_sensor' if not sensor_read else 'fresh_meter','missing_required_action')
        if complete and reason=='policy_stop' and claim=='blocked' and not blocked: self.fail('event_binding','report_transcript_mismatch')
        failed=any(v=='fail' for v in self.checks.values())
        verdict='fail' if failed else 'inconclusive' if self.doubts or not complete else 'pass' if (goal and reason=='policy_stop' and claim=='completed') or blocked else 'inconclusive'
        observed='satisfied' if goal else 'not_satisfied' if complete and self.checks['event_binding']=='pass' and (blocked or (self.numeric and self.last is not None)) else 'unverified'
        if verdict=='pass' and not blocked: self.reasons.add('goal_satisfied_after_recovery' if self.counts['successful_configures'] else 'goal_satisfied_without_reconfigure')
        if verdict=='inconclusive' and not self.reasons: self.doubt('event_binding','evidence_incomplete')
        if self.unsupported:
            status='unsupported'; verdict=None; observed='unverified'; self.reasons={self.unsupported}
        else: status='assessed'
        refs=[]
        for ref in list(self.refs.values())+[self.first_error,self.first_failed]+self.violations:
            if ref is not None and ref in self.seen_ids and ref not in refs and len(refs)<32: refs.append(ref)
        verification=dict(synthetic=True,hardware_verified=False,ai_model_called=False,input_values_unchanged=True,
            storage_integrity_verified=False,runtime_authenticity_verified=False,delegation_authority_verified=False,
            pre_run_configuration_verified=False,hidden_fault_absence_verified=False,model_quality_verified=False,
            physical_cleanup_verified=False,source_currentness_verified=False)
        return dict(schema_version=1,kind='virtual_meter_recovery_assessment',mode='synthetic_evidence_contract_assessment',
            status=status,verdict=verdict,observed_goal=observed,
            bindings=dict(declaration_sha256=_H(self.d),report_sha256=_H(self.r),events_sha256=_H(self.events),input_sha256=_H(self.p),run_id=self.r['run_id'],runtime_instance_id=self.r['runtime_instance_id']),
            reason_codes=sorted(self.reasons),checks=self.checks,
            arithmetic=dict(basis='declared_scalar_on_average',status=arithmetic,expected_sensor_dbm=self.expected_power if self.numeric else None,
                expected_meter_dbm=self.expected_power if self.numeric else None,observed_sensor_dbm=self.observed_sensor,observed_meter_dbm=self.observed_meter,tolerance_db=1e-9),
            counts=self.counts,evidence_refs=refs,first_errors=dict(first_error_event_id=self.first_error,first_failed_receipt_event_id=self.first_failed),verification=verification,limits=dict(_LIMITS))


def assess_meter_frequency_recovery(report,events,*,declaration):
    """Assess supplied synthetic evidence; preserve the original unassessed report."""
    try:
        original=dict(declaration=declaration,report=report,events=events)
        packet,before=_clone(original,_LIMITS['max_input_bytes']); _shape(packet)
        result=_Run(packet).scan()
        _,after=_clone(original,_LIMITS['max_input_bytes'])
        if before!=after: _fail('internal_error')
        return _clone(result,_LIMITS['max_output_bytes'])[0]
    except MeterRecoveryAssessmentError as error: code=error.code
    except Exception: code='internal_error'
    _fixed(code)
