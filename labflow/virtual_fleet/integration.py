"""Bind the report catalog to pure virtual roles and a synthetic example bench."""
from copy import deepcopy

from .catalog import ROLES, validate_catalog
from .core import VirtualFleet


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


def create_conducted_example(catalog, *, seed=0):
    """Create all catalog devices and initialize an explicit synthetic RF bench.

    The numeric recipe below is newly authored simulation input. No report
    answers, actual calibration, regulatory limit or hardware API is loaded.
    Remaining catalog devices stay unconnected; their acceptance is separate.
    """
    catalog=validate_catalog(catalog)
    topology=_conducted_topology(catalog)
    fleet=create_fleet(catalog,topology,seed=seed)
    receipts=[]
    def command(device,action,parameters=None):
        result=fleet.execute(f'example:action:{len(receipts)}',device,action,parameters)
        receipts.append(result)
        if result['status'] not in {'ok','pending'}:
            raise ValueError(f'Synthetic example initialization failed: {device}/{action}')
    def advance(ticks):
        result=fleet.advance(f'example:tick:{len(receipts)}',ticks)
        receipts.append(result)
        if result['status']!='ok':raise ValueError('Synthetic example clock failed')

    command('supply','configure',{'voltage_v':5,'current_limit_a':1})
    command('supply','set_load',{'resistance_ohm':50})
    command('supply','output',{'enabled':True})
    command('environment','configure',{'temperature_c':23,'humidity_percent':45})
    command('environment','start')
    command('dut','configure',{'frequency_hz':2.45e9,'power_dbm':12.5,'bandwidth_hz':20e6,
                               'duty_cycle':.25,'modulation':'OFDM','crest_factor_db':3})
    command('attenuator','configure',{'attenuation_db':10})
    command('switch_controller','configure',{'routes':['rf_1','rf_2']})
    command('switch_controller','select_path',{'input_port':'rf_1'})
    command('switch','configure',{'loss_db':.5})
    command('switch','select_path',{'input_port':'rf_1'})
    command('coupler','configure',{'through_loss_db':1.25,'coupling_db':20})
    command('sensor','configure',{'calibration_valid':True,'acquisition_policy':'continuous'})
    command('meter','configure',{'frequency_hz':2.45e9,'measurement_mode':'time_average','unit':'dBm'})
    command('analyzer','configure',{'frequency_hz':2.45e9,'measurement_mode':'on_average',
                                   'measurement':'power','bandwidth_hz':20e6,'rbw_hz':100e3,'detector':'rms'})
    advance(8)
    command('dut','start')
    advance(3)
    command('meter','acquire')
    command('analyzer','acquire')
    advance(2)
    command('meter','fetch')
    command('analyzer','fetch')
    return fleet,topology,receipts
