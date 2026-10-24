"""One synthetic stop delivery boundary over the existing exact virtual DUT."""
from dataclasses import dataclass
import hashlib
from inspect import getattr_static
import json
import math
import re
import threading
from types import FunctionType
from uuid import uuid4

from .virtual_fleet.core import VirtualFleet
from .virtual_fleet import rf, instruments, facility


_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_FAMILIES = {'ADB','OEM','GUI','AT','DIAG'}
_SCENARIOS = {'normal','disconnected','timeout_before','timeout_after_stop','partial_delivery',
              'ack_only','no_effect','stale_read','wrong_context'}
_REASONS = {'observed_stopped','transport_unavailable','permission_denied','model_firmware_mismatch',
    'transport_disconnected','deadline_exceeded','partial_acknowledgement','observation_missing',
    'stop_not_observed','context_mismatch','invalid_response','configuration_changed','runtime_error'}
_STATUSES = {'ok','pending','invalid','unsupported','error','disconnected'}
_STATES = {'idle','configured','unconfigured','transmitting','arming','waiting','settling','unavailable','awaiting_fresh_observation'}
_PACKET_LIMIT, _RECEIPT_LIMIT, _AUTHOR_LIMIT = 32*1024,96*1024,256*1024
_PACKET_DEPTH, _RECEIPT_DEPTH, _AUTHOR_DEPTH = 32,32,36
_FLEET_METHODS = {name:getattr(VirtualFleet,name) for name in ('execute','observations')}
_CLASS_BY_ROLE = {**dict.fromkeys(rf.ROLE_PORTS,rf.RFDevice),
    **dict.fromkeys(instruments.ROLE_PORTS,instruments._Instrument),**facility.DEVICE_FACTORIES}


def _members(kind):
    names = {name for base in kind.__mro__ for name,value in vars(base).items()
             if isinstance(value,(FunctionType,property,staticmethod,classmethod))}
    return {name:getattr_static(kind,name) for name in names}


def _codes(member):
    if isinstance(member,FunctionType): return (member.__code__,)
    if isinstance(member,(staticmethod,classmethod)): return _codes(member.__func__)
    if isinstance(member,property):
        return tuple(function.__code__ for function in (member.fget,member.fset,member.fdel) if function is not None)
    return ()


_MEMBER_PINS = {kind:{name:(member,_codes(member)) for name,member in _members(kind).items()}
                for kind in {VirtualFleet,*_CLASS_BY_ROLE.values()}}


def _check_members(instance,kind):
    current, expected = _members(kind),_MEMBER_PINS[kind]
    if set(current)!=set(expected): raise ValueError('dut_stop_fleet_invalid')
    data = object.__getattribute__(instance,'__dict__')
    for name,(member,codes) in expected.items():
        if name in data or current[name] is not member or _codes(current[name])!=codes:
            raise ValueError('dut_stop_fleet_invalid')


class _Unconfirmed(Exception):
    pass


def _copy(value,limit=_RECEIPT_LIMIT,*,max_depth=_RECEIPT_DEPTH):
    def walk(item,depth=0):
        if depth>max_depth: raise ValueError()
        if type(item) is dict:
            if any(type(key) is not str for key in item): raise ValueError()
            return {key:walk(child,depth+1) for key,child in item.items()}
        if type(item) is list: return [walk(child,depth+1) for child in item]
        if item is None or type(item) in (str,bool,int): return item
        if type(item) is float and math.isfinite(item): return item
        raise ValueError()
    data = json.dumps(walk(value),ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    if len(data)>limit: raise ValueError()
    return json.loads(data)


def _fingerprint(value):
    return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))


def _operator_envelope(value):
    result = _copy(value,_PACKET_LIMIT)
    result['values'].pop('reason',None)
    return result


def _identifier(value,error):
    if type(value) is not str or not _ID.fullmatch(value): raise ValueError(error)
    return value


@dataclass(frozen=True)
class _Configuration:
    transport_family: str
    available: bool
    authorized: bool
    model_fw_matches: bool
    scenario: str

    def payload(self):
        return {name:getattr(self,name) for name in ('transport_family','available','authorized','model_fw_matches','scenario')}


def _integrity(fleet):
    if type(fleet) is not VirtualFleet: raise ValueError('dut_stop_fleet_invalid')
    _check_members(fleet,VirtualFleet)
    if any(type(getattr(fleet,name,None)) is not dict for name in ('_devices','_profiles','_nodes')):
        raise ValueError('dut_stop_fleet_invalid')
    if set(fleet._devices)!=set(fleet._nodes): raise ValueError('dut_stop_fleet_invalid')
    for name,node in fleet._nodes.items():
        try:
            role = fleet._profiles[node['profile_id']]['role']
            device, expected = fleet._devices[name],_CLASS_BY_ROLE[role]
        except (KeyError,TypeError):
            raise ValueError('dut_stop_fleet_invalid') from None
        if type(device) is not expected: raise ValueError('dut_stop_fleet_invalid')
        _check_members(device,expected)


def _clock(value):
    if type(value) is not dict or any(type(value.get(key)) is not int or value[key]<0 for key in ('tick','setup_revision')):
        raise _Unconfirmed('invalid_response')
    return {key:value[key] for key in ('tick','setup_revision')}


class SyntheticDutStopAdapter:
    def __init__(self,fleet,dut_id,*,transport_family,available,authorized,model_fw_matches,scenario='normal'):
        if (type(transport_family) is not str or transport_family not in _FAMILIES
                or any(type(value) is not bool for value in (available,authorized,model_fw_matches))
                or type(scenario) is not str or scenario not in _SCENARIOS):
            raise ValueError('dut_stop_configuration_invalid')
        _identifier(dut_id,'dut_stop_device_invalid')
        _integrity(fleet)
        if dut_id not in fleet._nodes or type(fleet._devices[dut_id]) is not rf.RFDevice:
            raise ValueError('dut_stop_device_invalid')
        profile_id = fleet._nodes[dut_id]['profile_id']
        if fleet._profiles[profile_id]['role']!='dut' or fleet._devices[dut_id].role!='dut':
            raise ValueError('dut_stop_device_invalid')
        self._fleet, self._device_id, self._profile_id = fleet,dut_id,profile_id
        self._config = _Configuration(transport_family,available,authorized,model_fw_matches,scenario)
        self._configuration_fingerprint = _fingerprint(self._config.payload())
        self._namespace = uuid4().hex
        self._lock = threading.RLock()
        self._cache, self._authors = {},{}
        try:
            self._snapshot()
        except (ValueError,_Unconfirmed):
            raise ValueError('dut_stop_fleet_invalid') from None

    @property
    def _configuration(self):
        return json.loads(self._configuration_fingerprint)

    def _configuration_valid(self):
        try:
            return type(self._config) is _Configuration and _fingerprint(self._config.payload())==self._configuration_fingerprint
        except (ValueError,TypeError,RecursionError,OverflowError):
            return False

    def _snapshot(self):
        _integrity(self._fleet)
        source = _copy(_FLEET_METHODS['observations'](self._fleet),1024*1024)
        if (type(source) is not dict or set(source)!={'tick','setup_revision','synthetic','hardware_verified','devices'}
                or source['synthetic'] is not True or source['hardware_verified'] is not False
                or type(source['devices']) is not dict or self._device_id not in source['devices']):
            raise _Unconfirmed('invalid_response')
        context = _clock(source)
        row = source['devices'][self._device_id]
        self._envelope(row,setup=False)
        if _clock(row)!=context: raise _Unconfirmed('context_mismatch')
        return context,row

    def _envelope(self,value,*,setup=True):
        value = _copy(value,_PACKET_LIMIT)
        required = {'status','values','tick','setup_revision','synthetic','hardware_verified','device_id','profile_id','role'}
        if setup: required.add('setup_changed')
        if (type(value) is not dict or not required<=set(value) or set(value)-required-{'state'}
                or type(value['status']) is not str or value['status'] not in _STATUSES
                or type(value['values']) is not dict
                or value['synthetic'] is not True or value['hardware_verified'] is not False):
            raise _Unconfirmed('invalid_response')
        if (value['device_id']!=self._device_id or value['profile_id']!=self._profile_id or value['role']!='dut'):
            raise _Unconfirmed('context_mismatch')
        _clock(value)
        if setup and type(value['setup_changed']) is not bool: raise _Unconfirmed('invalid_response')
        data = value['values']
        if (set(data)-{'state','outputs','configured','reason','controller_only'} or type(data.get('outputs')) is not dict
                or set(data['outputs'])-{'rf'} or 'configured' in data and type(data['configured']) is not bool
                or 'state' in data and (type(data['state']) is not str or data['state'] not in _STATES)
                or 'controller_only' in data and type(data['controller_only']) is not bool
                or 'reason' in data and (type(data['reason']) is not str or len(data['reason'])>128)):
            raise _Unconfirmed('invalid_response')
        if value['status']=='ok' and 'reason' in data: raise _Unconfirmed('invalid_response')
        if 'state' in value and (type(value['state']) is not str or value['state'] not in _STATES):
            raise _Unconfirmed('invalid_response')
        if 'rf' in data['outputs']:
            signal = data['outputs']['rf']
            allowed = {'status','valid','frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','source_id','crest_factor_db'}
            if (type(signal) is not dict or set(signal)-allowed or signal.get('source_id')!=self._device_id):
                raise _Unconfirmed('invalid_response')
        return value

    def _command(self,request_id,action):
        return _FLEET_METHODS['execute'](self._fleet,request_id,self._device_id,action,{})

    def _id(self,request_id,action):
        digest = hashlib.sha256(_fingerprint([self._namespace,self._device_id,request_id,action]).encode('utf-8')).hexdigest()
        return 'dut-stop:'+digest+':'+action

    def _base(self,request_id):
        return {'schema_version':1,'kind':'synthetic_dut_stop_receipt','execution_mode':'virtual_fleet_dut_stop',
            'synthetic':True,'hardware_verified':False,'physical_model_verified':False,'model_execution_verified':False,
            'oem_support_status':'not_assessed','request_id':request_id,
            'transport_family':self._configuration['transport_family'],'device_id':self._device_id,'profile_id':self._profile_id,
            'request_context':None,'status':'unconfirmed','reason_code':'runtime_error',
            'acknowledgement':{'received':False,'completion':'not_sent','origin':'none'},
            'stop_response':None,'read_observation':None,'commands':[],'receipt_scope':'historical_observation',
            'current_stop_authority':False,'observation_context':None}

    def _exchange(self,request_id,action,receipt,author):
        command_id = self._id(request_id,action)
        receipt['commands'].append({'request_id':command_id,'action':action})
        event = {'request_id':command_id,'action':action,'raw_response':None,'received_response':None,'error_code':None}
        author['exchanges'].append(event)
        if action=='stop':
            receipt['acknowledgement'] = {'received':False,'completion':'unknown','origin':'none'}
        try:
            raw = self._command(command_id,action)
        except BaseException:
            event['error_code'] = 'runtime_error'
            raise
        try:
            packet = _copy(raw,_PACKET_LIMIT,max_depth=_PACKET_DEPTH)
        except (ValueError,TypeError,RecursionError,OverflowError):
            event['error_code'] = 'invalid_response'
            raise _Unconfirmed('invalid_response') from None
        event['raw_response'] = packet
        return packet,event

    def _checkpoint(self,context,read=None):
        if not self._configuration_valid(): raise _Unconfirmed('configuration_changed')
        current,row = self._snapshot()
        if context!=current: raise _Unconfirmed('context_mismatch')
        if read is not None:
            compared = {key:value for key,value in read.items() if key!='setup_changed'}
            if _fingerprint(compared)!=_fingerprint(row): raise _Unconfirmed('context_mismatch')

    def _read(self,request_id,context,receipt,author):
        raw,event = self._exchange(request_id,'read',receipt,author)
        wire = _copy(raw,_PACKET_LIMIT)
        scenario = self._configuration['scenario']
        if scenario=='stale_read': wire['setup_revision'] = wire['setup_revision']-1
        elif scenario=='wrong_context': wire['device_id'] = 'other-dut'
        event['received_response'] = _copy(wire,_PACKET_LIMIT)
        packet = self._envelope(wire)
        if _clock(packet)!=context or packet['setup_changed'] is not False: raise _Unconfirmed('context_mismatch')
        self._checkpoint(context,packet)
        receipt['read_observation'],receipt['observation_context'] = _operator_envelope(packet),_clock(packet)
        return packet

    def _finish(self,request_id,receipt,author):
        if not self._configuration_valid(): receipt.update(status='unconfirmed',reason_code='configuration_changed')
        if receipt['reason_code'] not in _REASONS: receipt.update(status='unconfirmed',reason_code='runtime_error')
        stored = _copy(receipt)
        # Keep the attempted commands/context before composing private diagnostics.
        self._cache[request_id] = stored
        author['receipt'] = _copy(stored)
        try:
            diagnostic = _copy(author,_AUTHOR_LIMIT,max_depth=_AUTHOR_DEPTH)
        except (ValueError,TypeError,RecursionError,OverflowError):
            stored.update(status='unconfirmed',reason_code='runtime_error')
            diagnostic = self._recover_author(request_id,stored,author)
        self._authors[request_id] = diagnostic
        return _copy(stored)

    def _recover_author(self,request_id,receipt,author):
        # Four bounded packets + one receipt use at most 224 KiB. Rebuild only
        # fixed metadata/events so an invalid wrapper cannot discard those packets.
        diagnostic = {'schema_version':1,'kind':'synthetic_dut_stop_author_record','request_id':request_id,
            'configuration':self._configuration,'request_context':_copy(receipt['request_context']),
            'exchanges':[],'receipt':_copy(receipt),'diagnostic_error':'author_record_invalid'}
        candidates = author.get('exchanges')
        if type(candidates) is not list: candidates = []
        for index,command in enumerate(receipt['commands']):
            event = {**command,'raw_response':None,'received_response':None,'error_code':None}
            candidate = candidates[index] if index<len(candidates) else None
            if (type(candidate) is not dict or candidate.get('request_id')!=command['request_id']
                    or candidate.get('action')!=command['action']):
                event['error_code'] = 'invalid_response'
            else:
                error = candidate.get('error_code')
                event['error_code'] = error if error in (None,'runtime_error','invalid_response') else 'invalid_response'
                for field in ('raw_response','received_response'):
                    try:
                        event[field] = _copy(candidate.get(field),_PACKET_LIMIT,max_depth=_PACKET_DEPTH)
                    except (ValueError,TypeError,RecursionError,OverflowError):
                        event['error_code'] = 'invalid_response'
            diagnostic['exchanges'].append(event)
        return _copy(diagnostic,_AUTHOR_LIMIT,max_depth=_AUTHOR_DEPTH)

    def stop(self,request_id):
        _identifier(request_id,'dut_stop_request_invalid')
        with self._lock:
            if request_id in self._cache: return _copy(self._cache[request_id])
            if len(self._cache)>=128: raise ValueError('dut_stop_cache_full')
            receipt = self._base(request_id)
            author = {'schema_version':1,'kind':'synthetic_dut_stop_author_record','request_id':request_id,
                'configuration':_copy(self._configuration),'request_context':None,'exchanges':[],'receipt':None}
            # Reserve the ID before a possibly state-changing command.
            self._cache[request_id] = _copy(receipt)
            try:
                if not self._configuration_valid(): raise _Unconfirmed('configuration_changed')
                context,_ = self._snapshot()
                receipt['request_context'],author['request_context'] = _copy(context),_copy(context)
                for gate,reason in (('available','transport_unavailable'),('authorized','permission_denied'),
                                    ('model_fw_matches','model_firmware_mismatch')):
                    if not self._configuration[gate]:
                        receipt.update(status='blocked',reason_code=reason)
                        return self._finish(request_id,receipt,author)
                scenario = self._configuration['scenario']
                if scenario in {'disconnected','timeout_before'}:
                    receipt['reason_code'] = 'transport_disconnected' if scenario=='disconnected' else 'deadline_exceeded'
                    return self._finish(request_id,receipt,author)
                if scenario in {'partial_delivery','no_effect'}:
                    receipt['acknowledgement'] = {'received':True,'origin':'synthetic_delivery',
                        'completion':'partial' if scenario=='partial_delivery' else 'acknowledged'}
                    self._read(request_id,context,receipt,author)
                    receipt['reason_code'] = 'partial_acknowledgement' if scenario=='partial_delivery' else 'stop_not_observed'
                    return self._finish(request_id,receipt,author)
                raw,event = self._exchange(request_id,'stop',receipt,author)
                if scenario=='timeout_after_stop':
                    receipt['acknowledgement'] = {'received':False,'completion':'unknown','origin':'none'}
                    receipt['reason_code'] = 'deadline_exceeded'
                    return self._finish(request_id,receipt,author)
                event['received_response'] = _copy(raw,_PACKET_LIMIT)
                if not self._configuration_valid(): raise _Unconfirmed('configuration_changed')
                response = self._envelope(raw)
                values = response['values']
                if (values['outputs'] or response['status']=='ok' and (type(values.get('configured')) is not bool
                        or values.get('state')!=('configured' if values['configured'] else 'unconfigured'))):
                    raise _Unconfirmed('invalid_response')
                expected = {'tick':context['tick'],'setup_revision':context['setup_revision']+int(response['setup_changed'])}
                if _clock(response)!=expected: raise _Unconfirmed('context_mismatch')
                self._checkpoint(expected)
                receipt['stop_response'] = _operator_envelope(response)
                receipt['acknowledgement'] = {'received':True,'origin':'virtual_fleet',
                    'completion':'acknowledged' if response['status']=='ok' else 'unknown'}
                if response['status']!='ok':
                    receipt['reason_code'] = 'transport_disconnected' if response['status']=='disconnected' else 'stop_not_observed'
                    return self._finish(request_id,receipt,author)
                if scenario=='ack_only':
                    receipt['reason_code'] = 'observation_missing'
                    return self._finish(request_id,receipt,author)
                observed = self._read(request_id,expected,receipt,author)
                values = observed['values']
                if observed['status']=='ok' and values.get('state')=='idle' and values.get('configured') is True and values['outputs']=={}:
                    receipt.update(status='confirmed_synthetic',reason_code='observed_stopped')
                else:
                    receipt['reason_code'] = 'stop_not_observed'
            except _Unconfirmed as error:
                receipt.update(status='unconfirmed',reason_code=str(error) if str(error) in _REASONS else 'invalid_response')
            except BaseException:
                receipt.update(status='unconfirmed',reason_code='runtime_error')
            return self._finish(request_id,receipt,author)

    def author_record(self,request_id):
        _identifier(request_id,'dut_stop_request_invalid')
        with self._lock:
            if request_id not in self._authors: raise ValueError('dut_stop_request_unknown')
            return _copy(self._authors[request_id],_AUTHOR_LIMIT,max_depth=_AUTHOR_DEPTH)
