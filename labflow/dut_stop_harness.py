"""One fixed in-memory fixture run followed by a separately recorded DUT stop."""
import hashlib
import threading

from . import dut_stop_simulation as dut
from .virtual_fleet import harness as fixture
from .virtual_fleet.policies import RFSensorFixturePolicy


_MIB = 1024*1024
_RESULT_LIMIT, _RESULT_DEPTH = 384*1024,36
_AUTHOR_LIMIT, _AUTHOR_DEPTH = 38*_MIB,40
_EVENT_LIMIT, _EVENT_BYTES, _EVENT_COUNT = 512*1024,32*_MIB,4096
_CONFIG_FIELDS = {'goal','catalog','topology','role_actions','run_id','runtime_instance_id'}
_STOP_FIELDS = {'transport_family','available','authorized','model_fw_matches'}
_HARNESS_KEYS = {'schema_version','kind','run_id','runtime_instance_id','synthetic','hardware_verified','ai_model_called',
    'policy','termination','task_outcome','cleanup','usage','evidence','unresolved_request_ids','assessment'}
_STOP_KEYS = {'schema_version','kind','execution_mode','synthetic','hardware_verified','physical_model_verified',
    'model_execution_verified','oem_support_status','request_id','transport_family','device_id','profile_id',
    'request_context','status','reason_code','acknowledgement','stop_response','read_observation','commands',
    'receipt_scope','current_stop_authority','observation_context'}
_TERMINATIONS = {'policy_stop','supervisor_stop','wall_deadline','decision_budget','request_budget','tick_budget',
    'evidence_error','runtime_mutation_uncertain','runtime_error','policy_error','invalid_proposal'}
_EVENT_PAYLOADS = {'observation':{'observation','cause_request_id'},'error':{'code'},
    'termination':{'code','unresolved_request_ids'},'policy_decision':{'proposal'},
    'intent':{'request_id','operation','body','logical_request'},'transport_retry':{'request_id','retry'},
    'receipt':{'request_id','result'}}
_CHILD_TYPES = (fixture.FleetHarness,RFSensorFixturePolicy,dut.SyntheticDutStopAdapter)
_HARNESS_TYPE, _POLICY_TYPE, _ADAPTER_TYPE = _CHILD_TYPES
_CHILD_PINS = {kind:{name:(member,dut._codes(member)) for name,member in dut._members(kind).items()}
               for kind in _CHILD_TYPES}
_HARNESS_RUN, _HARNESS_RESULT, _HARNESS_EVENTS = (getattr(fixture.FleetHarness,name) for name in ('run','result','events'))
_STOP_RUN, _STOP_AUTHOR = dut.SyntheticDutStopAdapter.stop,dut.SyntheticDutStopAdapter.author_record
_copy, _fingerprint = dut._copy,dut._fingerprint


def _check_class(kind,instance=None):
    if instance is not None and type(instance) is not kind: raise ValueError()
    current,pins = dut._members(kind),_CHILD_PINS[kind]
    if set(current)!=set(pins): raise ValueError()
    data = {} if instance is None else object.__getattribute__(instance,'__dict__')
    if any(name in data or current[name] is not member or dut._codes(current[name])!=codes
           for name,(member,codes) in pins.items()): raise ValueError()
    if kind is RFSensorFixturePolicy and kind.policy_id!='rf_sensor_v1': raise ValueError()


def _metadata(catalog,topology,actions):
    return {'catalog':fixture._public_catalog(catalog),'topology':fixture._copy(topology,project=True),
            'role_actions':fixture._copy(actions,project=True)}


def _exact(value,keys):
    if type(value) is not dict or set(value)!=keys: raise ValueError()


def _counter(value):
    return type(value) is int and value>=0


class SyntheticDutStopHarnessRun:
    def __init__(self,fleet,dut_id,*,harness_config,stop_config):
        try:
            dut._integrity(fleet)
            for kind in _CHILD_TYPES:_check_class(kind)
        except BaseException:
            raise ValueError('dut_stop_harness_fleet_invalid') from None
        try:
            dut._identifier(dut_id,'invalid')
            if type(harness_config) is not dict or not _CONFIG_FIELDS<=set(harness_config) or set(harness_config)-_CONFIG_FIELDS-{'budgets'}:
                raise ValueError()
            config = {key:_copy(harness_config[key],_MIB,max_depth=32) for key in _CONFIG_FIELDS}
            for key in ('goal','catalog','topology','role_actions'):
                if type(config[key]) is not dict:raise ValueError()
            for key in ('run_id','runtime_instance_id'):dut._identifier(config[key],'invalid')
            if 'budgets' in harness_config:
                config['budgets']=_copy(harness_config['budgets'],_MIB,max_depth=32)
                if type(config['budgets']) is not dict:raise ValueError()
            goal=config['goal']
            _exact(goal,{'kind','dut_id','sensor_id','minimum_acquisition_tick'})
            if goal['kind']!='acquire_fresh_rf_sensor' or not _counter(goal['minimum_acquisition_tick']):raise ValueError()
            for key in ('dut_id','sensor_id'):dut._identifier(goal[key],'invalid')
            public=_metadata(config['catalog'],config['topology'],config['role_actions'])
        except BaseException:
            raise ValueError('dut_stop_harness_configuration_invalid') from None
        try:
            if type(stop_config) is not dict or not _STOP_FIELDS<=set(stop_config) or set(stop_config)-_STOP_FIELDS-{'scenario'}:raise ValueError()
            stop_config=_copy(stop_config,4096,max_depth=32)
            if (type(stop_config['transport_family']) is not str or stop_config['transport_family'] not in dut._FAMILIES
                    or any(type(stop_config[key]) is not bool for key in ('available','authorized','model_fw_matches'))
                    or type(stop_config.get('scenario','normal')) is not str or stop_config.get('scenario','normal') not in dut._SCENARIOS):raise ValueError()
        except BaseException:
            raise ValueError('dut_stop_harness_stop_configuration_invalid') from None
        if dut_id not in fleet._nodes or fleet._profiles[fleet._nodes[dut_id]['profile_id']]['role']!='dut':
            raise ValueError('dut_stop_harness_device_invalid')
        sensor=goal['sensor_id']
        try:
            if (goal['dut_id']!=dut_id or sensor==dut_id or sensor not in fleet._nodes
                    or fleet._profiles[fleet._nodes[sensor]['profile_id']]['role']!='power_sensor'
                    or _fingerprint(public)!=_fingerprint(_metadata(fleet.catalog,fleet.topology,fleet.role_actions))):raise ValueError()
        except BaseException:
            raise ValueError('dut_stop_harness_binding_invalid') from None
        config.update(public)
        try:
            self._adapter=_ADAPTER_TYPE(fleet,dut_id,**stop_config)
        except BaseException:
            raise ValueError('dut_stop_harness_device_invalid') from None
        try:
            self._harness=_HARNESS_TYPE(fleet,_POLICY_TYPE(),**config)
        except BaseException:
            raise ValueError('dut_stop_harness_configuration_invalid') from None
        self._fleet,self._device_id,self._profile_id=fleet,dut_id,fleet._nodes[dut_id]['profile_id']
        self._harness_config,self._stop_config=config,stop_config
        self._configuration_fingerprint=_fingerprint([config,stop_config])
        self._run_id,self._instance_id=config['run_id'],config['runtime_instance_id']
        self._stop_request_id='dut-stop-harness:'+hashlib.sha256(_fingerprint([self._run_id,self._instance_id]).encode('utf-8')).hexdigest()
        self._lock,self._started=threading.RLock(),False
        self._harness_dispatch,self._stop_dispatch='not_started','not_sent'
        self._harness_result=self._harness_return=self._stop_receipt=self._stop_return=self._stop_author=None
        self._harness_error=self._events_error=self._stop_error=self._record_error=None
        self._events,self._raw_events,self._diagnostic_errors=[],[],[]
        self._result,self._author=None,None
        try:self._children_intact()
        except BaseException:raise ValueError('dut_stop_harness_binding_invalid') from None

    def _children_intact(self):
        dut._integrity(self._fleet)
        _check_class(_HARNESS_TYPE,self._harness)
        _check_class(_POLICY_TYPE,self._harness._policy)
        _check_class(_ADAPTER_TYPE,self._adapter)
        config=self._harness_config
        if (_fingerprint([config,self._stop_config])!=self._configuration_fingerprint
                or self._harness._runtime is not self._fleet or self._adapter._fleet is not self._fleet
                or self._adapter._device_id!=self._device_id or self._adapter._profile_id!=self._profile_id
                or not self._adapter._configuration_valid()
                or self._adapter._configuration!={**self._stop_config,'scenario':self._stop_config.get('scenario','normal')}
                or self._harness._run_id!=self._run_id or self._harness._instance_id!=self._instance_id
                or self._harness._policy_id!='rf_sensor_v1'
                or _fingerprint(self._harness._limits)!=_fingerprint({**fixture._DEFAULTS,**config.get('budgets',{})})):raise ValueError()
        device=self._fleet._devices[self._device_id]
        if device.role!='dut' or device.profile_id!=self._profile_id:raise ValueError()
        expected={key:config[key] for key in ('catalog','topology','role_actions')}
        if _fingerprint(expected)!=_fingerprint(_metadata(self._fleet.catalog,self._fleet.topology,self._fleet.role_actions)):raise ValueError()
        actual={'goal':self._harness._goal,'catalog':self._harness._catalog,'topology':self._harness._topology,'role_actions':self._harness._actions}
        if _fingerprint(actual)!=_fingerprint({key:config[key] for key in actual}):raise ValueError()

    def _validate_harness(self,value):
        _exact(value,_HARNESS_KEYS)
        if _fingerprint(value)!=_fingerprint(self._harness._result):raise ValueError()
        if (type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='virtual_fleet_harness_result'
                or value['run_id']!=self._run_id or value['runtime_instance_id']!=self._instance_id
                or value['synthetic'] is not True or value['hardware_verified'] is not False or value['ai_model_called'] is not False
                or value['policy']!={'kind':'fixture','id':'rf_sensor_v1'} or value['task_outcome']!='not_assessed'
                or value['cleanup']!={'status':'not_assessed','evidence_refs':[]}
                or value['assessment']!={'status':'not_assessed','verdict':None,'evaluator_id':None,'evidence_refs':[],'summary_code':None}
                or not fixture._no_private(value)):raise ValueError()
        termination=value['termination'];_exact(termination,{'reason','policy_claim'})
        if termination['reason'] not in _TERMINATIONS:raise ValueError()
        if termination['reason']=='policy_stop':
            if termination['policy_claim'] not in {'completed','blocked','unsupported','failed'}:raise ValueError()
        elif termination['policy_claim'] is not None:raise ValueError()
        usage=value['usage'];_exact(usage,{'decisions','logical_requests','transport_retries','tick_delta','reserved_ticks','elapsed_ms'})
        if any(not _counter(usage[key]) for key in usage if key!='elapsed_ms') or not fixture._finite(usage['elapsed_ms']) or usage['elapsed_ms']<0:raise ValueError()
        evidence=value['evidence'];_exact(evidence,{'measurement_refs','operator_transcript_ref'})
        if evidence['operator_transcript_ref']!='artifact:operator_events':raise ValueError()
        for refs in (evidence['measurement_refs'],value['unresolved_request_ids']):
            if type(refs) is not list or any(type(ref) is not str for ref in refs):raise ValueError()
        return value

    def _validate_stop(self,value):
        _exact(value,_STOP_KEYS)
        if _fingerprint(value)!=_fingerprint(self._adapter._cache.get(self._stop_request_id)):raise ValueError()
        if (type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='synthetic_dut_stop_receipt'
                or value['execution_mode']!='virtual_fleet_dut_stop' or value['synthetic'] is not True
                or any(value[key] is not False for key in ('hardware_verified','physical_model_verified','model_execution_verified','current_stop_authority'))
                or value['oem_support_status']!='not_assessed' or value['receipt_scope']!='historical_observation'
                or value['request_id']!=self._stop_request_id or value['device_id']!=self._device_id or value['profile_id']!=self._profile_id
                or value['transport_family']!=self._stop_config['transport_family'] or value['status'] not in {'blocked','unconfirmed','confirmed_synthetic'}
                or value['reason_code'] not in dut._REASONS or not fixture._no_private(value)):raise ValueError()
        for name in ('request_context','observation_context'):
            if value[name] is not None:
                _exact(value[name],{'tick','setup_revision'});dut._clock(value[name])
        ack=value['acknowledgement'];_exact(ack,{'received','completion','origin'})
        if (type(ack['received']) is not bool or ack['completion'] not in {'not_sent','acknowledged','partial','unknown'}
                or ack['origin'] not in {'none','virtual_fleet','synthetic_delivery'}):raise ValueError()
        commands=value['commands']
        if type(commands) is not list or len(commands)>2:raise ValueError()
        actions=[]
        for command in commands:
            _exact(command,{'request_id','action'});action=command['action']
            if action not in {'stop','read'} or action in actions or command['request_id']!=self._adapter._id(self._stop_request_id,action):raise ValueError()
            actions.append(action)
        for name in ('stop_response','read_observation'):
            if value[name] is not None:self._adapter._envelope(value[name])
        if value['status']=='confirmed_synthetic':
            read=value['read_observation'];response=value['stop_response']
            if (actions!=['stop','read'] or ack!={'received':True,'completion':'acknowledged','origin':'virtual_fleet'}
                    or response is None or read is None or response['status']!='ok' or read['status']!='ok'
                    or read['values'].get('state')!='idle' or read['values'].get('configured') is not True or read['values']['outputs']!={}
                    or value['observation_context']!=dut._clock(read)):raise ValueError()
        return value

    def _invoke_harness(self):return _HARNESS_RUN(self._harness)
    def _read_harness_events(self):return _HARNESS_EVENTS(self._harness)
    def _invoke_stop(self):return _STOP_RUN(self._adapter,self._stop_request_id)

    def _capture_events(self):
        try:raw=self._read_harness_events()
        except BaseException:
            self._events_error='harness_events_error'
            raw=self._harness._events
        if type(raw) is not list:
            self._events_error=self._events_error or 'harness_events_invalid';return
        size=0
        for index,source in enumerate(raw):
            if index>=_EVENT_COUNT:
                self._events_error=self._events_error or 'harness_events_invalid';break
            try:
                event=_copy(source,_EVENT_LIMIT,max_depth=32)
                length=len(_fingerprint(event).encode('utf-8'))
            except BaseException:
                self._events_error=self._events_error or 'harness_events_invalid'
                if 'harness_event_unrecordable' not in self._diagnostic_errors:self._diagnostic_errors.append('harness_event_unrecordable')
                continue
            if size+length>_EVENT_BYTES:
                self._events_error=self._events_error or 'harness_events_invalid';break
            self._raw_events.append(event);size+=length
            try:
                _exact(event,{'schema_version','kind','event_id','run_id','runtime_instance_id','sequence','type','payload'})
                if (type(event['schema_version']) is not int or event['schema_version']!=1 or event['kind']!='operator_event'
                        or event['run_id']!=self._run_id or event['runtime_instance_id']!=self._instance_id
                        or type(event['sequence']) is not int or event['sequence']!=index+1 or event['event_id']!='event:'+str(index+1)
                        or event['type'] not in _EVENT_PAYLOADS or type(event['payload']) is not dict
                        or set(event['payload'])-_EVENT_PAYLOADS[event['type']] or not fixture._no_private(event)):raise ValueError()
                required=_EVENT_PAYLOADS[event['type']]-({'cause_request_id'} if event['type']=='observation' else set())
                if not required<=set(event['payload']):raise ValueError()
            except BaseException:
                self._events_error=self._events_error or 'harness_events_invalid'
            else:self._events.append(event)

    def _core_result(self):
        errors=(self._record_error,self._harness_error,self._events_error,self._stop_error)
        complete=self._harness_result is not None and self._stop_receipt is not None and not any(errors)
        return {'schema_version':1,'kind':'synthetic_dut_stop_harness_result','execution_mode':'virtual_fleet_fixture_then_dut_stop',
            'synthetic':True,'hardware_verified':False,'physical_model_verified':False,'model_execution_verified':False,
            'oem_support_status':'not_assessed','run_id':self._run_id,'runtime_instance_id':self._instance_id,
            'device_id':self._device_id,'profile_id':self._profile_id,'status':'recorded' if complete else 'partial',
            'reason_code':next((error for error in errors if error),'children_recorded' if complete else 'wrapper_record_error'),
            'harness_dispatch':self._harness_dispatch,'harness_result':self._harness_result,'harness_error':self._harness_error,
            'events_error':self._events_error,'dut_stop_request_id':self._stop_request_id,'stop_dispatch':self._stop_dispatch,
            'dut_stop_receipt':self._stop_receipt,'dut_stop_error':self._stop_error,'record_error':self._record_error,
            'receipt_scope':'historical_observation','current_stop_authority':False}

    def _compose_result(self):return self._core_result()

    def _core_author(self):
        return {'schema_version':1,'kind':'synthetic_dut_stop_harness_author_record',
            'harness_configuration':self._harness_config,'stop_configuration':self._stop_config,
            'harness_return':self._harness_return,'harness_events':self._raw_events,
            'dut_stop_return':self._stop_return,'dut_stop_author':self._stop_author,
            'diagnostic_errors':self._diagnostic_errors,'diagnostic_error':self._record_error,'result':self._result}

    def _compose_author(self):return self._core_author()

    def _freeze_progress(self):
        self._result=_copy(self._core_result(),_RESULT_LIMIT,max_depth=_RESULT_DEPTH)

    def _finish(self):
        try:
            candidate=_copy(self._compose_result(),_RESULT_LIMIT,max_depth=_RESULT_DEPTH)
            if _fingerprint(candidate)!=_fingerprint(self._core_result()):raise ValueError()
            self._result=candidate
        except BaseException:
            self._record_error='wrapper_record_error';self._freeze_progress()
        try:
            candidate=_copy(self._compose_author(),_AUTHOR_LIMIT,max_depth=_AUTHOR_DEPTH)
            if set(candidate)!=set(self._core_author()):raise ValueError()
            self._author=candidate
        except BaseException:
            self._record_error='wrapper_record_error';self._freeze_progress()
            self._author=_copy(self._core_author(),_AUTHOR_LIMIT,max_depth=_AUTHOR_DEPTH)
        return self.result()

    def run(self):
        with self._lock:
            if self._started:return self.result()
            self._started=True
            self._freeze_progress()
            try:self._children_intact()
            except BaseException:
                self._record_error='child_binding_changed';return self._finish()
            self._harness_dispatch='unknown';self._freeze_progress()
            try:raw=self._invoke_harness()
            except BaseException:
                self._harness_error='harness_execution_error'
                try:raw=_HARNESS_RESULT(self._harness)
                except BaseException:raw=self._harness._result
            else:self._harness_dispatch='returned'
            try:
                self._harness_return=_copy(raw,256*1024,max_depth=32)
                self._harness_result=self._validate_harness(self._harness_return)
            except BaseException:self._harness_error=self._harness_error or 'harness_result_invalid'
            self._capture_events();self._freeze_progress()
            try:self._children_intact()
            except BaseException:
                self._record_error='child_binding_changed';return self._finish()
            self._stop_dispatch='unknown';self._freeze_progress()
            try:raw=self._invoke_stop()
            except BaseException:self._stop_error='dut_stop_execution_error'
            else:
                self._stop_dispatch='returned'
                try:
                    self._stop_return=_copy(raw,96*1024,max_depth=32)
                    self._stop_receipt=self._validate_stop(self._stop_return)
                except BaseException:self._stop_error='dut_stop_receipt_invalid'
            self._freeze_progress()
            try:self._stop_author=_copy(_STOP_AUTHOR(self._adapter,self._stop_request_id),256*1024,max_depth=36)
            except BaseException:self._diagnostic_errors.append('dut_stop_author_error')
            return self._finish()

    def result(self):
        with self._lock:
            return None if self._result is None else _copy(self._result,_RESULT_LIMIT,max_depth=_RESULT_DEPTH)

    def events(self):
        with self._lock:return [_copy(event,_EVENT_LIMIT,max_depth=32) for event in self._events]

    def author_record(self):
        with self._lock:
            return None if self._author is None else _copy(self._author,_AUTHOR_LIMIT,max_depth=_AUTHOR_DEPTH)
