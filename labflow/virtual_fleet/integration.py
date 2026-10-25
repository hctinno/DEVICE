"""Bind the report catalog to pure virtual roles and a synthetic example bench."""
from copy import deepcopy
import math

from .catalog import ROLES, validate_catalog
from .core import VirtualFleet


MAX_SETUP_RECORDS = 32


def _validate_setup_records(records):
    if records is not None and (type(records) is not list or records):
        raise ValueError('setup_records requires a native empty list or None')


def _begin_setup_record(records, request_id, operation, device_id, action, parameters):
    if records is None:
        return None
    if len(records) >= MAX_SETUP_RECORDS:
        raise ValueError('setup_records capacity exceeded')
    record = {'request_id': request_id, 'operation': operation,
              'device_id': device_id, 'action': action, 'parameters': deepcopy(parameters),
              'receipt': None, 'tick': None, 'setup_revision': None}
    records.append(record)
    return record


def _finish_setup_record(record, receipt):
    if record is not None:
        record['receipt'] = deepcopy(receipt)
        if type(receipt) is dict:
            record['tick'] = deepcopy(receipt.get('tick'))
            record['setup_revision'] = deepcopy(receipt.get('setup_revision'))


def _bindings():
    from . import facility, rf, instruments
    factories, actions = {}, {}
    for module in (facility, rf, instruments):
        supplied, declarations = module.DEVICE_FACTORIES, module.ROLE_ACTIONS
        if not isinstance(supplied, dict) or not isinstance(declarations, dict):
            raise ValueError('Role bindings must be maps')
        if set(supplied) != set(declarations) or not set(supplied) <= ROLES:
            raise ValueError('Factory and action roles must match known roles')
        if set(factories) & set(supplied):
            raise ValueError('Duplicate role bindings')
        if any(not callable(factory) for factory in supplied.values()):
            raise ValueError('Device factories must be callable')
        factories.update(supplied)
        actions.update(deepcopy(declarations))
    return factories, actions


def get_role_actions():
    """Return detached action metadata; support is not scenario validation."""
    return _bindings()[1]


def create_fleet(catalog, topology, *, seed=0):
    factories, actions = _bindings()
    return VirtualFleet(validate_catalog(catalog), topology,
                        factories=factories, role_actions=actions, seed=seed)


def inventory_topology(catalog):
    """Instantiate every profile with no inferred physical connections."""
    catalog=validate_catalog(catalog)
    return {'devices':[{'id':p['profile_id'],'profile_id':p['profile_id']}
                       for p in catalog['profiles']], 'connections':[]}


def _conducted_topology(catalog):
    # A declared example arrangement, not a reconstruction of a measured setup.
    selection={'supply':('power_supply','E3632A'),
               'environment':('temperature_chamber','SU-642'),
               'dut':('dut','SM-A176U'), 'attenuator':('attenuator','8493C'),
               'switch_controller':('rf_switch','FBSM-01B'),
               'switch':('rf_switch','OSP 120'), 'coupler':('coupler','87300B'),
               'sensor':('power_sensor','N1921A'), 'meter':('power_meter','N1911A'),
               'analyzer':('signal_analyzer','N9030A'),
               'software':('test_software','FCC WLAN Conducted')}
    devices=[]
    used=set()
    for identity,(role,model) in selection.items():
        candidates=sorted((p for p in catalog['profiles'] if p['role']==role and p['model']==model),
                          key=lambda p:p['profile_id'])
        if not candidates:raise ValueError(f'Example requires profile {role}/{model}')
        profile=candidates[0]
        used.add(profile['profile_id'])
        devices.append({'id':identity,'profile_id':profile['profile_id']})
    devices.extend({'id':'inventory:'+p['profile_id'],'profile_id':p['profile_id']}
                   for p in catalog['profiles'] if p['profile_id'] not in used)
    connections=[]
    def edge(source,out,target,port,kind):
        connections.append({'source':{'device_id':source,'port':out},
                            'target':{'device_id':target,'port':port},'kind':kind})
    for target in ('environment','dut','meter','analyzer'):
        edge('supply','power',target,'power','power')
    edge('environment','environment','dut','environment','environment')
    edge('dut','rf','attenuator','rf','rf')
    edge('attenuator','rf','switch','rf_1','rf')
    edge('switch_controller','control','switch','control','control')
    edge('switch','rf','coupler','rf','rf')
    edge('coupler','rf','analyzer','rf','rf')
    edge('coupler','coupled','sensor','rf','rf')
    edge('sensor','measurement','meter','sensor','measurement')
    edge('meter','measurement','software','measurement','measurement')
    return {'devices':devices,'connections':connections}


def _source_configuration(value):
    fields = {'frequency_hz','power_dbm','bandwidth_hz','duty_cycle','modulation','crest_factor_db'}
    if (type(value) is not dict or any(type(key) is not str for key in value) or
            set(value) != fields):
        raise ValueError('source_settings requires exactly six declared fields')
    for key in fields - {'modulation'}:
        if type(value[key]) not in {int, float}:
            raise ValueError('source_settings requires native finite numbers')
        try:
            finite = math.isfinite(value[key])
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError('source_settings requires native finite numbers')
    modulation = value['modulation']
    if type(modulation) is not str or not modulation.strip() or len(modulation) > 200:
        raise ValueError('source_settings requires bounded nonempty modulation text')
    frequency, bandwidth = value['frequency_hz'], value['bandwidth_hz']
    if (frequency <= 0 or bandwidth <= 0 or not 0 < value['duty_cycle'] <= 1 or
            value['crest_factor_db'] < 0 or frequency - bandwidth / 2 < 0 or
            not math.isfinite(frequency + bandwidth / 2)):
        raise ValueError('source_settings is outside the existing RF signal range')
    return dict(value)


def create_conducted_example(catalog, *, seed=0, source_settings=None, setup_records=None):
    """Create all catalog devices and initialize an explicit synthetic RF bench.

    The numeric recipe below is newly authored simulation input. No report
    answers, actual calibration, regulatory limit or hardware API is loaded.
    Remaining catalog devices stay unconnected; their acceptance is separate.
    source_settings is an exact6 caller declaration, never measured Wi-Fi data.
    None preserves the original generic recipe and return tuple.
    An optional native empty setup_records list captures actual call boundaries.
    """
    _validate_setup_records(setup_records)
    catalog=validate_catalog(catalog)
    source = ({'frequency_hz':2.45e9,'power_dbm':12.5,'bandwidth_hz':20e6,
               'duty_cycle':.25,'modulation':'OFDM','crest_factor_db':3}
              if source_settings is None else _source_configuration(source_settings))
    topology=_conducted_topology(catalog)
    fleet=create_fleet(catalog,topology,seed=seed)
    receipts=[]
    def command(device,action,parameters=None):
        request_id=f'example:action:{len(receipts)}'
        record=_begin_setup_record(setup_records,request_id,'execute',device,action,parameters)
        result=fleet.execute(request_id,device,action,parameters)
        _finish_setup_record(record,result)
        receipts.append(result)
        if result['status'] not in {'ok','pending'}:
            raise ValueError(f'Synthetic example initialization failed: {device}/{action}')
    def advance(ticks):
        request_id=f'example:tick:{len(receipts)}'
        record=_begin_setup_record(setup_records,request_id,'advance',None,None,{'ticks':ticks})
        result=fleet.advance(request_id,ticks)
        _finish_setup_record(record,result)
        receipts.append(result)
        if result['status']!='ok':raise ValueError('Synthetic example clock failed')

    command('supply','configure',{'voltage_v':5,'current_limit_a':1})
    command('supply','set_load',{'resistance_ohm':50})
    command('supply','output',{'enabled':True})
    command('environment','configure',{'temperature_c':23,'humidity_percent':45})
    command('environment','start')
    command('dut','configure',source)
    command('attenuator','configure',{'attenuation_db':10})
    command('switch_controller','configure',{'routes':['rf_1','rf_2']})
    command('switch_controller','select_path',{'input_port':'rf_1'})
    command('switch','configure',{'loss_db':.5})
    command('switch','select_path',{'input_port':'rf_1'})
    command('coupler','configure',{'through_loss_db':1.25,'coupling_db':20})
    command('sensor','configure',{'calibration_valid':True,'acquisition_policy':'continuous'})
    command('meter','configure',{'frequency_hz':source['frequency_hz'],'measurement_mode':'time_average','unit':'dBm'})
    command('analyzer','configure',{'frequency_hz':source['frequency_hz'],'measurement_mode':'on_average',
                                   'measurement':'power','bandwidth_hz':source['bandwidth_hz'],'rbw_hz':100e3,'detector':'rms'})
    advance(8)
    command('dut','start')
    advance(3)
    command('meter','acquire')
    command('analyzer','acquire')
    advance(2)
    command('meter','fetch')
    command('analyzer','fetch')
    return fleet,topology,receipts
