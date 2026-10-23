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


if __name__=='__main__':unittest.main()
