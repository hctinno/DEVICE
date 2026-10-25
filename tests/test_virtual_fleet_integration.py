"""Whole catalog binding and connected synthetic measurement acceptance."""
import copy
from contextlib import redirect_stdout
import io
import json
import threading
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, Request, build_opener
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from labflow.virtual_fleet.catalog import CatalogError, ROLES, load_catalog
from labflow.virtual_fleet.integration import (
    create_fleet, create_conducted_example, get_role_actions, inventory_topology,
)

CATALOG=Path(__file__).resolve().parents[1]/'virtual_profiles/sm_a176u_unlicensed.json'


class FleetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.catalog=load_catalog(CATALOG)

    def test_every_catalog_profile_is_instantiated_without_claiming_scenario_acceptance(self):
        fleet=create_fleet(self.catalog,inventory_topology(self.catalog),seed=7)
        coverage=fleet.coverage()
        self.assertEqual(coverage['catalog_profiles'],len(self.catalog['profiles']))
        self.assertEqual(coverage['instantiated_devices'],len(self.catalog['profiles']))
        self.assertEqual(coverage['uninstantiated_profiles'],[])
        for device in coverage['devices'].values():
            self.assertTrue(device['available'])
            self.assertTrue(device['supported_actions'])
            self.assertEqual(device['scenario_validation'],'not_assessed')
        self.assertTrue(fleet.observations()['synthetic'])
        self.assertFalse(fleet.observations()['hardware_verified'])

    def test_bindings_cover_all_declared_roles_and_return_detached_metadata(self):
        actions=get_role_actions()
        self.assertEqual(set(actions),ROLES)
        actions['dut'].clear()
        self.assertTrue(get_role_actions()['dut'])

    def test_duplicate_role_factories_are_rejected_instead_of_shadowed(self):
        from labflow.virtual_fleet import facility
        duplicate={**facility.DEVICE_FACTORIES,'dut':next(iter(facility.DEVICE_FACTORIES.values()))}
        with patch.object(facility,'DEVICE_FACTORIES',duplicate),self.assertRaises(ValueError):
            get_role_actions()

    def test_uninstantiated_profiles_and_input_metadata_are_preserved(self):
        profile=next(p for p in self.catalog['profiles'] if p['role']=='power_supply')
        topology={'devices':[{'id':'supply','profile_id':profile['profile_id']}],'connections':[]}
        fleet=create_fleet(self.catalog,topology)
        self.catalog['profiles'][0]['model']='external edit'
        self.assertNotEqual(fleet.catalog['profiles'][0]['model'],'external edit')
        self.assertEqual(len(fleet.coverage()['uninstantiated_profiles']),63)

    def test_unknown_roles_are_not_mapped_to_a_generic_success_device(self):
        self.catalog['profiles'][0]['role']='generic_magic_device'
        with self.assertRaises(CatalogError):create_fleet(self.catalog,{'devices':[],'connections':[]})

    def test_connected_example_applies_each_loss_and_duty_correction_once(self):
        fleet,topology,receipts=create_conducted_example(self.catalog,seed=4)
        self.assertEqual(len(topology['devices']),64)
        self.assertTrue(receipts)
        observed=fleet.observations()['devices']
        meter=observed['meter']['values']['outputs']['measurement']
        analyzer=observed['analyzer']['values']['outputs']['measurement']
        self.assertAlmostEqual(meter['value'],12.5-10-.5-20+10*math.log10(.25),places=8)
        self.assertAlmostEqual(analyzer['value'],12.5-10-.5-1.25,places=8)
        self.assertEqual(meter['unit'],'dBm')
        self.assertEqual(meter['acquisition_setup_revision'],fleet.observations()['setup_revision'])
        self.assertFalse(fleet.observations()['hardware_verified'])

    def test_connected_example_is_reproducible(self):
        first,_,_=create_conducted_example(self.catalog,seed=9)
        second,_,_=create_conducted_example(copy.deepcopy(self.catalog),seed=9)
        self.assertEqual(first.observations(),second.observations())

    def test_no_output_invalidates_measurements_and_requires_fresh_acquisition(self):
        fleet,_,_=create_conducted_example(self.catalog)
        fleet.author_control('test:failure','dut','no_output',True)
        response=fleet.execute('test:stale','meter','fetch')
        self.assertNotEqual(response['status'],'ok')
        self.assertNotIn('measurement',response['values'].get('outputs',{}))
        fleet.author_control('test:restore','dut','no_output',False)
        fleet.execute('test:restart','dut','start')
        fleet.advance('test:restore-ticks',3)
        fleet.execute('test:acquire','meter','acquire')
        fleet.advance('test:measurement-ticks',2)
        recovered=fleet.execute('test:recovered','meter','fetch')
        self.assertEqual(recovered['status'],'ok')
        self.assertTrue(recovered['values']['outputs']['measurement']['valid'])

    def test_command_line_check_runs_real_role_models_without_opening_a_server(self):
        from labflow.virtual_fleet.__main__ import main
        output=io.StringIO()
        with redirect_stdout(output):result=main(['--catalog',str(CATALOG),'--example','conducted','--check'])
        self.assertEqual(result,0)
        receipt=json.loads(output.getvalue())
        self.assertEqual(receipt['catalog_profiles'],64)
        self.assertEqual(receipt['instantiated_devices'],64)
        self.assertEqual(receipt['example'],'conducted')
        self.assertTrue(receipt['synthetic'])
        self.assertFalse(receipt['hardware_verified'])
        self.assertTrue(receipt['measurements']['meter']['valid'])

    def test_http_actions_use_actual_models_and_retries_do_not_change_revision_twice(self):
        from labflow.virtual_fleet_server import create_server
        fleet,topology,_=create_conducted_example(self.catalog)
        with create_server(fleet,catalog=self.catalog,topology=topology,role_actions=get_role_actions(),port=0) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                origin=f'http://127.0.0.1:{server.server_port}'
                opener=build_opener(HTTPCookieProcessor(CookieJar()))
                with opener.open(origin+'/api/state',timeout=5) as response:state=json.load(response)
                self.assertEqual(len(state['catalog']['profiles']),64)
                self.assertEqual(len(state['observations']['devices']),64)
                self.assertEqual(state['runtime_kind'],'injected_virtual_runtime')
                self.assertNotIn('simulation_parameters',state['catalog']['profiles'][0])
                revision=state['observations']['setup_revision']
                data=json.dumps({'request_id':'http:configure','device_id':'analyzer','action':'configure',
                                 'parameters':{'frequency_hz':2.46e9}}).encode('utf-8')
                def post():
                    request=Request(origin+'/api/actions',data=data,method='POST',
                                    headers={'Content-Type':'application/json','Origin':origin,
                                             'X-CSRF-Token':state['csrf_token']})
                    with opener.open(request,timeout=5) as response:return json.load(response)
                first=post();second=post()
                self.assertFalse(first['replayed'])
                self.assertTrue(second['replayed'])
                self.assertEqual(first['result'],second['result'])
                with opener.open(origin+'/api/state',timeout=5) as response:changed=json.load(response)
                self.assertEqual(changed['observations']['setup_revision'],revision+1)
                self.assertNotIn('measurement',changed['observations']['devices']['meter']['values'].get('outputs',{}))
            finally:
                server.shutdown();thread.join(2)
            self.assertFalse(thread.is_alive())


    def twin_source(self):
        return dict(frequency_hz=2.412e9,power_dbm=11.0,bandwidth_hz=10e6,
                    duty_cycle=.5,modulation='OFDM',crest_factor_db=3.0)

    def test_plan_source_configures_three_devices_consistently(self):
        from labflow.virtual_fleet.core import VirtualFleet
        source=self.twin_source();before=copy.deepcopy(source);commands={}
        genuine=VirtualFleet.execute
        def record(fleet,request,device,action,parameters=None):
            if action=='configure' and device in {'dut','meter','analyzer'}:
                commands[device]=copy.deepcopy(parameters)
            return genuine(fleet,request,device,action,parameters)
        try:
            with patch.object(VirtualFleet,'execute',record):
                fleet,topology,receipts=create_conducted_example(self.catalog,seed=5,source_settings=source)
        except TypeError as error:
            self.fail('optional source_settings is unavailable: '+str(error))
        self.assertEqual(commands['dut'],before)
        self.assertEqual(commands['meter']['frequency_hz'],before['frequency_hz'])
        self.assertEqual(commands['analyzer']['frequency_hz'],before['frequency_hz'])
        self.assertEqual(commands['analyzer']['bandwidth_hz'],before['bandwidth_hz'])
        self.assertEqual(source,before);self.assertEqual(len(topology['devices']),64);self.assertTrue(receipts)
        observed=fleet.observations()
        signal=observed['devices']['dut']['values']['outputs']['rf']
        self.assertEqual(signal['frequency_hz'],before['frequency_hz'])
        self.assertEqual(signal['bandwidth_hz'],before['bandwidth_hz'])
        for name in ('meter','analyzer'):
            result=observed['devices'][name]['values']['outputs']['measurement']
            self.assertTrue(result['valid']);self.assertEqual(result['frequency_hz'],before['frequency_hz'])
        self.assertTrue(observed['synthetic']);self.assertFalse(observed['hardware_verified'])
        source['power_dbm']=99
        self.assertEqual(fleet.observations()['devices']['dut']['values']['outputs']['rf']['power_dbm'],before['power_dbm'])

    def test_none_source_preserves_original_recipe_and_return(self):
        first,top1,receipts1=create_conducted_example(self.catalog,seed=9)
        second,top2,receipts2=create_conducted_example(self.catalog,seed=9,source_settings=None)
        self.assertEqual(first.observations(),second.observations())
        self.assertEqual(top1,top2);self.assertEqual(receipts1,receipts2)
        source=first.observations()['devices']['dut']['values']['outputs']['rf']
        self.assertEqual((source['frequency_hz'],source['power_dbm'],source['bandwidth_hz'],
                          source['duty_cycle'],source['modulation'],source['crest_factor_db']),
                         (2.45e9,12.5,20e6,.25,'OFDM',3))

    def test_fresh_benches_track_three_db_source_change_and_path_math(self):
        low=self.twin_source();high={**low,'power_dbm':low['power_dbm']+3}
        a,_,_=create_conducted_example(self.catalog,seed=13,source_settings=low)
        b,_,_=create_conducted_example(copy.deepcopy(self.catalog),seed=13,source_settings=high)
        self.assertIsNot(a,b)
        for fleet,source in ((a,low),(b,high)):
            outputs=fleet.observations()['devices']
            meter=outputs['meter']['values']['outputs']['measurement']['value']
            analyzer=outputs['analyzer']['values']['outputs']['measurement']['value']
            # Declared synthetic paths: coupled sensor vs through analyzer.
            self.assertAlmostEqual(meter,source['power_dbm']-10-.5-20+10*math.log10(source['duty_cycle']),places=8)
            self.assertAlmostEqual(analyzer,source['power_dbm']-10-.5-1.25,places=8)
        for device in ('meter','analyzer'):
            get=lambda fleet:fleet.observations()['devices'][device]['values']['outputs']['measurement']['value']
            self.assertAlmostEqual(get(b)-get(a),3.0,places=8)
            self.assertAlmostEqual(10**((get(b)-get(a))/10),10**.3,places=8)

    def test_duty_changes_time_average_but_not_on_average(self):
        source=self.twin_source();continuous={**source,'duty_cycle':1.0}
        burst,_,_=create_conducted_example(self.catalog,source_settings=source)
        steady,_,_=create_conducted_example(self.catalog,source_settings=continuous)
        measure=lambda fleet,name:fleet.observations()['devices'][name]['values']['outputs']['measurement']['value']
        self.assertAlmostEqual(measure(burst,'meter')-measure(steady,'meter'),10*math.log10(.5),places=8)
        self.assertAlmostEqual(measure(burst,'analyzer'),measure(steady,'analyzer'),places=8)

    def test_bad_source_settings_rejected_before_fleet_without_defaults(self):
        from labflow.virtual_fleet import integration
        class Scalar(float):pass
        class Settings(dict):pass
        valid=self.twin_source();invalid=[{},[],True,Settings(valid),{**valid,'extra':1}]
        invalid += [{k:v for k,v in valid.items() if k!=missing} for missing in valid]
        for key in ('frequency_hz','power_dbm','bandwidth_hz','duty_cycle','crest_factor_db'):
            invalid += [{**valid,key:value} for value in (True,float('nan'),float('inf'),float('-inf'),'1',Scalar(1),10**400)]
        invalid += [{**valid,'frequency_hz':0},{**valid,'bandwidth_hz':0},{**valid,'duty_cycle':0},
                    {**valid,'duty_cycle':1.01},{**valid,'crest_factor_db':-1},
                    {**valid,'frequency_hz':1,'bandwidth_hz':3},
                    {**valid,'frequency_hz':1.7e308,'bandwidth_hz':1.7e308}]
        invalid += [{**valid,'modulation':v} for v in (None,1,False,'',' '*3,'x'*201)]
        for index,value in enumerate(invalid):
            with self.subTest(index=index),patch.object(integration,'create_fleet',side_effect=AssertionError('must validate first')):
                with self.assertRaises(ValueError):create_conducted_example(self.catalog,source_settings=value)

    def test_source_reconfigure_invalidates_stale_measurement_then_fresh_acquire(self):
        source=self.twin_source()
        fleet,_,_=create_conducted_example(self.catalog,source_settings=source)
        before=fleet.observations();old=before['devices']['meter']['values']['outputs']['measurement']
        changed=fleet.execute('plan:change','dut','configure',{**source,'power_dbm':source['power_dbm']+3})
        self.assertEqual(changed['status'],'ok')
        for device in ('meter','analyzer'):
            fetched=fleet.execute('plan:stale:'+device,device,'fetch')
            self.assertNotEqual(fetched['status'],'ok')
            self.assertNotIn('measurement',fetched['values'].get('outputs',{}))
        fleet.execute('plan:start','dut','start');fleet.advance('plan:settle',3)
        for device in ('meter','analyzer'):fleet.execute('plan:acquire:'+device,device,'acquire')
        fleet.advance('plan:wait',2)
        fresh=fleet.execute('plan:fresh','meter','fetch')
        self.assertEqual(fresh['status'],'ok')
        result=fresh['values']['outputs']['measurement']
        self.assertGreater(result['acquisition_setup_revision'],old['acquisition_setup_revision'])
        self.assertEqual(result['acquisition_setup_revision'],fleet.observations()['setup_revision'])
        self.assertAlmostEqual(result['value']-old['value'],3.0,places=8)


    def setup_bench(self, **kwargs):
        try:
            return create_conducted_example(self.catalog, **kwargs)
        except TypeError as error:
            self.fail('setup_records optional keyword unavailable: ' + str(error))

    def test_setup_records_match_each_actual_command_and_advance_once(self):
        from labflow.virtual_fleet.core import VirtualFleet
        records, actual = [], []
        execute, advance = VirtualFleet.execute, VirtualFleet.advance

        def command(fleet, request, device, action, parameters=None):
            before = copy.deepcopy(parameters)
            self.assertEqual(records[-1]['request_id'], request)
            self.assertIsNone(records[-1]['receipt'])
            result = execute(fleet, request, device, action, parameters)
            actual.append(dict(request_id=request, operation='execute',
                               device_id=device, action=action, parameters=before,
                               receipt=copy.deepcopy(result), tick=result['tick'],
                               setup_revision=result['setup_revision']))
            return result

        def tick(fleet, request, ticks=1):
            self.assertEqual(records[-1]['request_id'], request)
            self.assertIsNone(records[-1]['receipt'])
            result = advance(fleet, request, ticks)
            actual.append(dict(request_id=request, operation='advance',
                               device_id=None, action=None, parameters={'ticks': ticks},
                               receipt=copy.deepcopy(result), tick=result['tick'],
                               setup_revision=result['setup_revision']))
            return result

        with patch.object(VirtualFleet, 'execute', command), patch.object(VirtualFleet, 'advance', tick):
            returned = self.setup_bench(source_settings=self.twin_source(), setup_records=records)
        fleet, topology, receipts = returned
        self.assertEqual(len(returned), 3)
        self.assertEqual(len(records), 23)
        self.assertEqual(records, actual)
        self.assertEqual([row['receipt'] for row in records], receipts)
        self.assertEqual(len(topology['devices']), 64)
        self.assertTrue(fleet.observations()['devices']['sensor']['values']['outputs']['measurement']['valid'])
        self.assertEqual(json.loads(json.dumps(records, allow_nan=False)), records)

    def test_setup_records_none_preserves_existing_return_and_observations(self):
        for source in (None, self.twin_source()):
            plain, top_a, receipts_a = create_conducted_example(self.catalog, seed=9, source_settings=source)
            omitted, top_b, receipts_b = self.setup_bench(seed=9, source_settings=source, setup_records=None)
            recorded, top_c, receipts_c = self.setup_bench(seed=9, source_settings=source, setup_records=[])
            self.assertEqual(plain.observations(), omitted.observations())
            self.assertEqual(plain.observations(), recorded.observations())
            self.assertEqual(top_a, top_b)
            self.assertEqual(top_a, top_c)
            self.assertEqual(receipts_a, receipts_b)
            self.assertEqual(receipts_a, receipts_c)

    def test_setup_records_bad_collector_rejects_before_fleet_creation(self):
        from labflow.virtual_fleet import integration
        class Records(list):
            pass
        for supplied in ({}, (), True, 0, '', Records(), [None], [{'old': 'record'}]):
            with self.subTest(kind=type(supplied).__name__), patch.object(
                    integration, 'create_fleet', side_effect=AssertionError('no fleet on invalid collector')):
                with self.assertRaises(ValueError):
                    self.setup_bench(setup_records=supplied)

    def test_setup_records_detach_source_nested_parameters_and_original_receipts(self):
        records = []
        source = self.twin_source()
        before_catalog, before_source = copy.deepcopy(self.catalog), copy.deepcopy(source)
        fleet, _, receipts = self.setup_bench(source_settings=source, setup_records=records)
        original = copy.deepcopy(records)
        route = next(row for row in records if row['device_id'] == 'switch_controller'
                     and row['action'] == 'configure')
        route['parameters']['routes'].append('caller edit')
        self.assertNotIn('caller edit', next(row for row in original if row['request_id']
                                             == route['request_id'])['parameters']['routes'])
        receipts[0]['values']['caller_edit'] = True
        self.assertEqual(records[0], original[0])
        source['frequency_hz'] = 2.45e9
        self.assertEqual(next(row for row in records if row['device_id'] == 'dut'
                              and row['action'] == 'configure')['parameters'], before_source)
        self.assertEqual(self.catalog, before_catalog)
        self.assertEqual(fleet.observations()['devices']['dut']['values']['outputs']['rf']['frequency_hz'],
                         before_source['frequency_hz'])

    def test_setup_records_preserve_real_profile_failure_receipt_and_prefix(self):
        records = []
        source = {**self.twin_source(), 'frequency_hz': 1e12}
        original = copy.deepcopy(source)
        with self.assertRaises(ValueError):
            self.setup_bench(source_settings=source, setup_records=records)
        self.assertGreater(len(records), 1)
        self.assertEqual((records[-1]['device_id'], records[-1]['action']), ('meter', 'configure'))
        self.assertNotIn(records[-1]['receipt']['status'], {'ok', 'pending'})
        self.assertEqual(records[-1]['tick'], records[-1]['receipt']['tick'])
        self.assertEqual(records[-1]['setup_revision'], records[-1]['receipt']['setup_revision'])
        self.assertEqual([row['receipt']['status'] for row in records[:3]], ['ok', 'ok', 'ok'])
        self.assertEqual(source, original)

    def test_setup_records_keep_attempt_without_fabricating_receipt_on_exception(self):
        from labflow.virtual_fleet.core import VirtualFleet
        records = []
        execute = VirtualFleet.execute
        def command(fleet, request, device, action, parameters=None):
            if device == 'environment' and action == 'configure':
                raise RuntimeError('test transport has no returned receipt')
            return execute(fleet, request, device, action, parameters)
        with patch.object(VirtualFleet, 'execute', command), self.assertRaises(RuntimeError):
            self.setup_bench(setup_records=records)
        self.assertEqual(len(records), 4)
        self.assertEqual(records[-1]['parameters'], {'temperature_c': 23, 'humidity_percent': 45})
        self.assertIsNone(records[-1]['receipt'])
        self.assertIsNone(records[-1]['tick'])
        self.assertIsNone(records[-1]['setup_revision'])
        self.assertTrue(all(row['receipt']['status'] == 'ok' for row in records[:-1]))

    def test_setup_records_capacity_rejects_before_next_actual_command(self):
        from labflow.virtual_fleet import integration
        from labflow.virtual_fleet.core import VirtualFleet
        records, calls = [], []
        execute = VirtualFleet.execute
        def command(fleet, request, device, action, parameters=None):
            calls.append(request)
            return execute(fleet, request, device, action, parameters)
        # Lower the real guard to exercise exhaustion without adding fake setup commands.
        with patch.object(integration, 'MAX_SETUP_RECORDS', 2, create=True), patch.object(
                VirtualFleet, 'execute', command), self.assertRaises(ValueError):
            self.setup_bench(setup_records=records)
        self.assertEqual(calls, ['example:action:0', 'example:action:1'])
        self.assertEqual(len(records), 2)
        self.assertTrue(all(row['receipt']['status'] == 'ok' for row in records))


if __name__=='__main__':unittest.main()
