"""Validate model coverage metadata; never establish hardware or simulation success."""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import re

ROLES=frozenset({
    'dut','power_sensor','attenuator','coupler','splitter','antenna','amplifier',
    'filter','rf_switch','lisn','power_meter','signal_analyzer','emi_receiver',
    'signal_generator','communication_tester','bluetooth_tester','wireless_ap',
    'dfs_system','network_test_station','test_software','power_supply',
    'temperature_chamber','position_controller','antenna_mast','turntable',
    'network_analyzer','inspection_microscope',
})
PROFILE_FIELDS=frozenset({'profile_id','profile_kind','model','manufacturer','role','variant',
                          'simulation_basis','capability_scope','simulation_parameters','evidence_refs','ports'})
IDENTIFIER=re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}\Z')
HASH=re.compile(r'[a-f0-9]{64}\Z')


class CatalogError(ValueError):
    pass


def _require(condition,where,message):
    if not condition:
        raise CatalogError(f'{where}: {message}')


def _json_values(value,where,depth=0):
    _require(depth<=20,where,'parameter nesting limit exceeded')
    if isinstance(value,dict):
        _require(len(value)<=1024,where,'too many parameter members')
        for key,item in value.items():
            _require(isinstance(key,str),where,'parameter keys must be strings')
            _json_values(item,where,depth+1)
    elif isinstance(value,list):
        _require(len(value)<=10000,where,'parameter list limit exceeded')
        for item in value:_json_values(item,where,depth+1)
    elif type(value) in (int,float):
        try:finite=math.isfinite(value)
        except (OverflowError,ValueError):finite=False
        _require(finite,where,'parameters must be finite')
    else:
        _require(value is None or type(value) in (str,bool),where,'parameter value is not JSON data')


def _reference(ref,where):
    _require(isinstance(ref,dict),where,'reference must be an object')
    _require(isinstance(ref.get('sha256'),str) and HASH.fullmatch(ref['sha256']),where,'invalid original hash')
    kind=ref.get('kind')
    allowed={'sha256','kind'}
    if kind=='docx_table':
        allowed.update({'table','row','part'})
        for key in ('table','row'):_require(type(ref.get(key)) is int and ref[key]>0,where,f'invalid {key} locator')
        if 'part' in ref:_require(isinstance(ref['part'],str) and bool(ref['part']),where,'invalid OOXML part')
    elif kind=='pdf_page':
        allowed.add('page')
        _require(type(ref.get('page')) is int and ref['page']>0,where,'invalid page locator')
    elif kind=='workbook_cell':
        allowed.update({'sheet','range'})
        _require(isinstance(ref.get('sheet'),str) and bool(ref['sheet']),where,'missing sheet locator')
        _require(isinstance(ref.get('range'),str) and re.fullmatch(r'[A-Z]+[1-9][0-9]*(?::[A-Z]+[1-9][0-9]*)?',ref['range']),where,'invalid cell locator')
    else:
        raise CatalogError(f'{where}: unsupported reference kind')
    _require(not set(ref)-allowed,where,'unexpected reference field')


def validate_catalog(catalog):
    _require(isinstance(catalog,dict),'catalog','must be an object')
    _require(set(catalog)=={'schema_version','catalog_id','source_basis','profiles'},'catalog','unexpected or missing top-level field')
    _require(type(catalog['schema_version']) is int and catalog['schema_version']==1,'catalog','unsupported schema version')
    _require(isinstance(catalog['catalog_id'],str) and IDENTIFIER.fullmatch(catalog['catalog_id']),'catalog','invalid catalog ID')
    _require(catalog['source_basis']=='provided_report_equipment','catalog','unsupported source basis')
    profiles=catalog['profiles']
    _require(isinstance(profiles,list) and 0<len(profiles)<=10000,'catalog','profiles must be a bounded nonempty array')
    seen=set()
    for index,profile in enumerate(profiles):
        where=f'profiles[{index}]'
        _require(isinstance(profile,dict) and set(profile)==PROFILE_FIELDS,where,'unexpected or missing profile field')
        identity=profile['profile_id']
        _require(isinstance(identity,str) and IDENTIFIER.fullmatch(identity),where,'invalid profile ID')
        _require(identity not in seen,where,'duplicate profile ID')
        seen.add(identity)
        _require(isinstance(profile['profile_kind'],str) and profile['profile_kind'] in
                 {'report_equipment','dut_context','auxiliary'},where,'unknown profile kind')
        for key in ('model','manufacturer','variant'):
            _require(isinstance(profile[key],str) and len(profile[key])<=1024 and (key=='variant' or profile[key].strip()),where,f'invalid {key}')
        _require(isinstance(profile['role'],str) and profile['role'] in ROLES,where,'unknown device role')
        _require(profile['simulation_basis']=='role_domain_model',where,'unsupported simulation basis')
        _require(profile['capability_scope']=='virtual_case_actions',where,'unsupported capability scope')
        _require(isinstance(profile['simulation_parameters'],dict),where,'simulation parameters must be an object')
        _json_values(profile['simulation_parameters'],where)
        ports=profile['ports']
        _require(isinstance(ports,dict) and set(ports)=={'inputs','outputs'},where,'ports require inputs and outputs')
        kinds={'rf','power','environment','position','control','measurement','data'}
        for direction in ('inputs','outputs'):
            _require(isinstance(ports[direction],dict),where,'port direction must be an object')
            for name,kind in ports[direction].items():
                _require(isinstance(name,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_:-]{0,63}',name),where,'invalid port name')
                _require(isinstance(kind,str) and kind in kinds,where,'unknown port kind')
        refs=profile['evidence_refs']
        _require(isinstance(refs,list) and 0<len(refs)<=10000,where,'source references are required')
        for ref_index,ref in enumerate(refs):_reference(ref,f'{where}.evidence_refs[{ref_index}]')
    return deepcopy(catalog)


def _unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise CatalogError('Duplicate JSON key')
        result[key]=value
    return result


def load_catalog(path,*,max_bytes=4*1024*1024):
    if type(max_bytes) is not int or max_bytes<1:raise CatalogError('Invalid catalog byte limit')
    with Path(path).open('rb') as stream:data=stream.read(max_bytes+1)
    if len(data)>max_bytes:raise CatalogError('Catalog byte limit exceeded')
    try:
        catalog=json.loads(data.decode('utf-8'),object_pairs_hook=_unique_object)
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as exc:
        raise CatalogError('Invalid catalog JSON') from exc
    return validate_catalog(catalog)


def catalog_summary(catalog):
    catalog=validate_catalog(catalog)
    profiles=catalog['profiles']
    return {'catalog_id':catalog['catalog_id'],'profiles':len(profiles),
            'roles':dict(sorted(Counter(profile['role'] for profile in profiles).items())),
            'source_hashes':len({ref['sha256'] for profile in profiles for ref in profile['evidence_refs']}),
            'synthetic':True,'hardware_verified':False,
            'execution_validation':'not_performed_by_catalog_validation'}
