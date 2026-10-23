import copy
import json
from pathlib import Path
import tempfile
import unittest

from labflow.virtual_fleet.catalog import CatalogError, catalog_summary, load_catalog, validate_catalog


def sample_catalog():
    return {'schema_version':1,'catalog_id':'synthetic-fleet',
            'source_basis':'provided_report_equipment',
            'profiles':[{'profile_id':'test-meter','profile_kind':'report_equipment','model':'SYNTH-METER','manufacturer':'DGM',
                         'role':'power_meter','variant':'single-channel',
                         'simulation_basis':'role_domain_model',
                         'capability_scope':'virtual_case_actions',
                         'simulation_parameters':{},
                         'ports':{'inputs':{'measurement':'measurement'},'outputs':{'data':'data'}},
                         'evidence_refs':[{'sha256':'a'*64,'kind':'docx_table','table':1,'row':2}]}]}


class CatalogTests(unittest.TestCase):
    def test_accepts_structural_catalog_without_claiming_hardware_support(self):
        catalog=sample_catalog()
        validated=validate_catalog(catalog)
        self.assertEqual(validated,catalog)
        summary=catalog_summary(catalog)
        self.assertEqual(summary['profiles'],1)
        self.assertFalse(summary['hardware_verified'])
        self.assertEqual(summary['execution_validation'],'not_performed_by_catalog_validation')

    def test_validation_returns_detached_copy(self):
        catalog=sample_catalog()
        validated=validate_catalog(catalog)
        validated['profiles'][0]['model']='changed'
        self.assertEqual(catalog['profiles'][0]['model'],'SYNTH-METER')

    def test_duplicate_identity_and_unknown_role_are_not_silently_dropped(self):
        for mutation in ('duplicate','unknown'):
            catalog=sample_catalog()
            if mutation=='duplicate':catalog['profiles'].append(copy.deepcopy(catalog['profiles'][0]))
            else:catalog['profiles'][0]['role']='unreviewed_device'
            with self.subTest(mutation=mutation),self.assertRaises(CatalogError):validate_catalog(catalog)

    def test_distinct_model_variants_remain_distinct_profiles(self):
        catalog=sample_catalog()
        variant=copy.deepcopy(catalog['profiles'][0]);variant.update(profile_id='test-meter-second',variant='second-range')
        catalog['profiles'].append(variant)
        self.assertEqual(catalog_summary(catalog)['profiles'],2)

    def test_original_hash_and_source_locator_are_required(self):
        for mutation in ({'sha256':'not-a-hash'},{'table':True},{'row':0},{'kind':'invented_page'}):
            catalog=sample_catalog();catalog['profiles'][0]['evidence_refs'][0].update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(CatalogError):validate_catalog(catalog)

    def test_missing_evidence_is_not_a_valid_report_profile(self):
        catalog=sample_catalog();catalog['profiles'][0]['evidence_refs']=[]
        with self.assertRaises(CatalogError):validate_catalog(catalog)

    def test_public_profile_does_not_accept_source_serial_or_measured_answer_fields(self):
        for field in ('serial','password','measured_power','expected_result'):
            catalog=sample_catalog();catalog['profiles'][0][field]='private-value'
            with self.subTest(field=field),self.assertRaises(CatalogError):validate_catalog(catalog)

    def test_nonfinite_parameters_are_rejected(self):
        catalog=sample_catalog();catalog['profiles'][0]['simulation_parameters']={'gain_db':float('inf')}
        with self.assertRaises(CatalogError):validate_catalog(catalog)

    def test_ports_require_declared_direction_and_supported_kind(self):
        for ports in ({'inputs':{},'output':{}},{'inputs':{'rf':'unknown'},'outputs':{}},
                      {'inputs':{'../unsafe':'rf'},'outputs':{}}):
            catalog=sample_catalog();catalog['profiles'][0]['ports']=ports
            with self.subTest(ports=ports),self.assertRaises(CatalogError):validate_catalog(catalog)

    def test_load_rejects_unknown_version_duplicate_json_keys_and_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'catalog.json'
            path.write_text('{"schema_version":1,"schema_version":2}',encoding='utf-8')
            with self.assertRaises(CatalogError):load_catalog(path)
            path.write_text(json.dumps({**sample_catalog(),'schema_version':99}),encoding='utf-8')
            with self.assertRaises(CatalogError):load_catalog(path)
            path.write_bytes(b' '*64)
            with self.assertRaises(CatalogError):load_catalog(path,max_bytes=32)

    def test_accepts_pdf_and_spreadsheet_locator_without_fabricating_page(self):
        catalog=sample_catalog()
        catalog['profiles'][0]['evidence_refs']=[{'sha256':'b'*64,'kind':'pdf_page','page':48},
                                               {'sha256':'c'*64,'kind':'workbook_cell','sheet':'Equipment','range':'A2:F2'}]
        self.assertEqual(validate_catalog(catalog),catalog)

    def test_shipped_catalog_preserves_reported_functional_variants(self):
        path=Path(__file__).resolve().parents[1]/'virtual_profiles/sm_a176u_unlicensed.json'
        profiles=load_catalog(path)['profiles']
        switches=[p for p in profiles if p['model']=='FBSM-01B']
        self.assertTrue(switches)
        for profile in switches:
            self.assertEqual(profile['role'],'rf_switch')
            self.assertIs(profile['simulation_parameters']['controller_only'],True)
            self.assertEqual(profile['ports'],{'inputs':{'control':'control'},'outputs':{'control':'control'}})
        splitters={p['model']:p for p in profiles if p['role']=='splitter'}
        self.assertEqual(set(splitters['4456-4']['ports']['outputs']),{'rf_1','rf_2','rf_3','rf_4'})
        self.assertEqual(set(splitters['11667B']['ports']['outputs']),{'rf_1','rf_2'})
        self.assertEqual({p['simulation_parameters']['function'] for p in profiles if p['role']=='dfs_system'},
                         {'generator','analyzer'})
        self.assertTrue(any(p['model']=='N1911A' and p['role']=='power_meter' for p in profiles))
        self.assertTrue(any(p['model']=='N1921A' and p['role']=='power_sensor' for p in profiles))

    def test_shipped_facility_ports_accept_explicit_power_and_position_control(self):
        profiles=load_catalog(Path(__file__).resolve().parents[1]/'virtual_profiles/sm_a176u_unlicensed.json')['profiles']
        for profile in profiles:
            with self.subTest(profile=profile['profile_id']):
                if profile['role']=='temperature_chamber':
                    self.assertEqual(profile['ports']['inputs']['power'],'power')
                if profile['role'] in ('position_controller','antenna_mast','turntable'):
                    self.assertEqual(profile['ports']['inputs'],{'power':'power','control':'control'})
                if profile['role']=='position_controller':
                    self.assertEqual(profile['ports']['outputs']['control'],'control')

    def test_shipped_context_and_auxiliary_are_explicitly_identified(self):
        profiles=load_catalog(Path(__file__).resolve().parents[1]/'virtual_profiles/sm_a176u_unlicensed.json')['profiles']
        for profile in profiles:
            expected=('dut_context' if profile['role']=='dut' else 'auxiliary'
                      if profile['role'] in ('inspection_microscope','network_analyzer') else 'report_equipment')
            self.assertEqual(profile['profile_kind'],expected)

    def test_reported_fixed_and_step_attenuators_keep_different_controls(self):
        profiles=load_catalog(Path(__file__).resolve().parents[1]/'virtual_profiles/sm_a176u_unlicensed.json')['profiles']
        nominal={'18B-03':3,'18N-20dB':20,'8493C':10}
        for profile in profiles:
            if profile['role']!='attenuator':continue
            parameters=profile['simulation_parameters']
            if 'Step Attenuator' in profile['variant']:
                self.assertEqual(parameters['attenuator_mode'],'step')
                self.assertNotIn('steps_db',parameters)  # No guessed manufacturer step table.
            else:
                self.assertEqual(parameters['attenuator_mode'],'fixed')
                self.assertEqual(parameters['attenuation_db'],nominal[profile['model']])


if __name__=='__main__':unittest.main()
