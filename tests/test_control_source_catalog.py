"""Pinned research metadata, candidate ambiguity and read-only catalog DTOs."""
from contextlib import contextmanager
import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch


REPO=Path(__file__).resolve().parents[1]
FILES=('research/equipment-control-2026-10-24/deliverables/model_control_sources.json',
       'control_sources/registry_overlay.json','control_sources/source_url_index.json',
       'control_sources/prior_vendor_references.json','control_sources/review_notes.json')


def sha(payload):return hashlib.sha256(payload).hexdigest()


class ControlSourceCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw={name:(REPO/name).read_bytes() for name in FILES}
        cls.data={name:json.loads(raw.decode('utf-8')) for name,raw in cls.raw.items()}
        cls.research=cls.data[FILES[0]];cls.overlay=cls.data[FILES[1]]
        cls.by_id={row['item_id']:row for row in cls.research}
        cls.over_by_id={row['item_id']:row for row in cls.overlay['records']}

    @classmethod
    def tearDownClass(cls):
        for name,raw in cls.raw.items():
            if (REPO/name).read_bytes()!=raw:raise AssertionError('catalog input modified: '+name)

    def module(self):return importlib.import_module('labflow.control_source_catalog')

    def catalog(self):
        if not hasattr(self,'_catalog'):self._catalog=self.module().ControlSourceCatalog()
        return self._catalog

    @contextmanager
    def private_inputs(self):
        local=REPO/'.local';local.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='control-catalog-test-',dir=local) as temporary:
            root=Path(temporary)
            for name,raw in self.raw.items():
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            yield root

    def unavailable(self,root):
        module=self.module()
        with self.assertRaises(module.ControlSourceCatalogError) as caught:module.ControlSourceCatalog(root)
        self.assertIsInstance(caught.exception,ValueError);self.assertEqual(caught.exception.code,'catalog_unavailable')
        self.assertEqual(str(caught.exception),'catalog_unavailable');self.assertNotIn(str(root),str(caught.exception))

    @contextmanager
    def repinned(self,root,name,payload):
        module=self.module();(root/name).write_bytes(payload)
        entries=tuple((key,path,(sha(payload),) if path==name else hashes) for key,path,hashes in module._INPUTS)
        with patch.object(module,'_INPUTS',entries):yield

    def test_summary_exact_counts_and_unassessed_support_flags(self):
        value=self.catalog().summary()
        self.assertEqual(set(value),{'schema_version','kind','source_commit','catalog_state','item_count','model_count',
            'identity_item_count','equipment_id_count','scope_counts','source_association_count','research_unique_url_count',
            'prior_reference_unique_url_count','overlapping_url_count','unique_url_count','profile_count',
            'profile_candidate_counts','adapter_support_status','vendor_binary_executed','hardware_verified',
            'profile_binding_established','registry_snapshot'})
        self.assertEqual((value['item_count'],value['model_count'],value['identity_item_count'],value['equipment_id_count']),
                         (3137,2867,270,6470))
        self.assertEqual((value['source_association_count'],value['research_unique_url_count'],value['prior_reference_unique_url_count'],
                          value['overlapping_url_count'],value['unique_url_count'],value['profile_count']),(2260,1624,83,17,1690,64))
        self.assertEqual(value['scope_counts'],{'included':1433,'excluded_passive':1480,'identity_unresolved':176,'needs_scope_review':48})
        self.assertEqual(value['profile_candidate_counts'],{'normalized_label_candidates':37,'same_model_other_manufacturer_candidates':9,'no_text_candidate':18})
        self.assertEqual(value['source_commit'],'8dec2d783b99609b27fb37f82752f17146206f4d')
        self.assertEqual(value['registry_snapshot'],self.overlay['registry_snapshot'])
        self.assertEqual(value['adapter_support_status'],'not_assessed')
        for key in ('vendor_binary_executed','hardware_verified','profile_binding_established'):self.assertIs(value[key],False)

    def test_exact_list_dto_and_stable_complete_pagination(self):
        catalog=self.catalog();first=catalog.find_items();self.assertEqual(first['limit'],25)
        self.assertEqual(set(first),{'schema_version','kind','source_commit','total','offset','limit','next_offset','items'})
        self.assertEqual(first['next_offset'],25);self.assertEqual(first,catalog.find_items())
        self.assertEqual(set(first['items'][0]),{'item_id','model_id','manufacturer','model','scope','research_status','public_code_status',
            'source_count','equipment_id_count','registration_rows','candidate_virtual_profile_ids','adapter_support_status','vendor_binary_executed','hardware_verified'})
        ids=[];offset=0
        while True:
            page=catalog.find_items(offset=offset,limit=100);self.assertEqual(page['total'],3137)
            ids.extend(row['item_id'] for row in page['items'])
            if page['next_offset'] is None:break
            offset=page['next_offset']
        self.assertEqual(ids,sorted(self.by_id));self.assertEqual(len(set(ids)),3137)
        beyond=catalog.find_items(offset=1000000);self.assertEqual(beyond['items'],[]);self.assertIsNone(beyond['next_offset'])

    def test_unicode_casefold_and_per_field_substring_search(self):
        catalog=self.catalog()
        for query in ('KEYSIGHT','multi-gnss','N9030A','Power Sensor','Keysight N9030A'):
            folded=query.casefold()
            expected=sorted(row['item_id'] for row in self.research if any(folded in value.casefold()
                for value in [row['item_id'],row['model_id'] or '',row['manufacturer'],row['model'],*row['names']]))
            found=[];offset=0
            while True:
                page=catalog.find_items(query=query,offset=offset,limit=100);found.extend(r['item_id'] for r in page['items'])
                if page['next_offset'] is None:break
                offset=page['next_offset']
            self.assertEqual(found,expected)

    def test_filters_are_and_and_profile_includes_other_manufacturer_candidates(self):
        catalog=self.catalog();agilent=self.by_id['MOD-aecdf6d16380a2be'];keysight=self.by_id['MOD-c40c6c5f1b4e7ca9']
        profile='n9030a-49f214c7ff'
        both=catalog.find_items(profile_id=profile)
        self.assertEqual({r['item_id'] for r in both['items']},{agilent['item_id'],keysight['item_id']})
        one=catalog.find_items(query='n9030a',scope='included',model_id=keysight['model_id'],
            equipment_id=keysight['equipment_ids'][0],profile_id=profile)
        self.assertEqual(one['total'],1);self.assertEqual(one['items'][0]['item_id'],keysight['item_id'])
        self.assertEqual(one['items'][0]['candidate_virtual_profile_ids'],self.over_by_id[keysight['item_id']]['candidate_virtual_profile_ids'])
        self.assertEqual(catalog.find_items(model_id=agilent['model_id'],equipment_id=keysight['equipment_ids'][0])['total'],0)

    def test_every_detail_restores_original_seven_fields_and_all_source_associations(self):
        catalog=self.catalog();associations=0
        for item_id,original in self.by_id.items():
            value=catalog.detail(item_id)
            self.assertEqual(set(value),{'schema_version','kind','source_commit','catalog_state','record','profile_candidates','review_notes'})
            expected={'research_record':original,**{key:v for key,v in self.over_by_id[item_id].items() if key!='item_id'}}
            self.assertEqual(value['record'],expected);self.assertEqual(len(value['record']),7)
            associations+=len(value['record']['research_record']['sources'])
        self.assertEqual(associations,2260)

    def test_null_model_identity_is_not_created_or_merged_into_a_model(self):
        catalog=self.catalog();identity=next(row for row in self.research if row['model_id'] is None)
        record=catalog.detail(identity['item_id'])['record'];self.assertIsNone(record['research_record']['model_id'])
        self.assertIs(record['registry_reconciliation']['identity_record'],True)
        self.assertIs(record['registry_reconciliation']['automatic_new_model_creation_permitted'],False)
        result=catalog.find_items(equipment_id=identity['equipment_ids'][0]);self.assertEqual(result['total'],1)
        self.assertIsNone(result['items'][0]['model_id']);self.assertEqual(catalog.find_items(model_id=identity['item_id'])['items'],[])

    def test_all_profiles_preserve_multicandidates_and_direct_candidate_absence(self):
        catalog=self.catalog()
        for profile in self.overlay['profile_crosswalk']['profiles']:
            ids={c['item_id'] for name in ('normalized_label_candidates','same_model_other_manufacturer_candidates') for c in profile[name]}
            page=catalog.find_items(profile_id=profile['profile_id'],limit=100)
            self.assertEqual({r['item_id'] for r in page['items']},ids)
            for item_id in ids:self.assertIn(profile,catalog.detail(item_id)['profile_candidates'])
        other=next(p for p in self.overlay['profile_crosswalk']['profiles'] if len(p['same_model_other_manufacturer_candidates'])>1)
        self.assertGreater(self.catalog().find_items(profile_id=other['profile_id'])['total'],1)

    def test_n9030a_ivi_evidence_remains_distinct_from_n9030b_code_and_mcp_note(self):
        catalog=self.catalog();value=catalog.detail('MOD-c40c6c5f1b4e7ca9');record=value['record']
        self.assertTrue(any(s['kind']=='driver' and s['access']=='content_read' for s in record['research_record']['sources']))
        self.assertFalse(any(s['kind']=='source_code' for s in record['research_record']['sources']))
        self.assertEqual(record['adapter_support_status'],'not_assessed')
        self.assertEqual(value['review_notes'][0]['note_id'],'N9030A-IVI-IS-NOT-MCP-IDF')
        self.assertEqual(value['review_notes'][0]['evidence'][0]['pdf_pages_1based'],[41])
        b=catalog.detail('MOD-2a92045c7333f6d2')['record']['research_record']
        self.assertTrue(any(s['kind']=='source_code' and s['match_level']=='exact_model' for s in b['sources']))

    def test_dmm6500_manufacturers_and_per_source_licenses_are_not_merged(self):
        catalog=self.catalog();wrong=catalog.detail('MOD-4e1a45a25496a054');right=catalog.detail('MOD-ce43da835609baea')
        self.assertEqual(wrong['record']['research_record']['manufacturer'],'Keysight')
        self.assertEqual(wrong['record']['research_record']['scope'],'identity_unresolved')
        self.assertEqual(right['record']['research_record']['manufacturer'],'KEITHLEY')
        licenses=[s['license'] for s in right['record']['research_record']['sources'] if s['kind']=='source_code']
        self.assertEqual(licenses,['MIT (파일 헤더 원문 확인)','Apache-2.0 (LICENSE.md 원문 확인)','Tektronix Sample Source Code License Agreement (MIT 아님)'])
        self.assertEqual(wrong['review_notes'][0],right['review_notes'][0])

    def test_n1921a_excluded_classification_keeps_sensor_profile_relationships(self):
        value=self.catalog().detail('MOD-753eb28b11306834');research=value['record']['research_record']
        self.assertEqual(research['scope'],'excluded_passive');self.assertEqual(research['sources'],[])
        self.assertEqual(value['record']['candidate_virtual_profile_ids'],[])
        self.assertEqual(value['profile_candidates'][0]['role'],'power_sensor')
        self.assertIs(value['profile_candidates'][0]['simulation_profile_retained'],True)
        self.assertIs(value['profile_candidates'][0]['installed_equipment_binding_established'],False)
        self.assertEqual(value['review_notes'][0]['note_id'],'N1921A-SENSOR-RELATION-RETAINED')

    def test_bad_filters_have_exact_errors_and_normal_unknown_ids_are_empty(self):
        catalog=self.catalog();module=self.module()
        for kwargs in ({'query':None},{'query':'x'*201},{'scope':{}},{'scope':'supported'},
            {'model_id':''},{'equipment_id':'../file'},{'profile_id':'한글'},
            {'offset':True},{'offset':-1},{'offset':1000001},{'limit':False},{'limit':0},{'limit':101}):
            with self.subTest(kwargs=kwargs),self.assertRaises(module.ControlSourceCatalogError) as caught:catalog.find_items(**kwargs)
            self.assertEqual(caught.exception.code,'catalog_invalid_query')
        for key in ('model_id','equipment_id','profile_id'):
            result=catalog.find_items(**{key:'UNKNOWN'})
            self.assertEqual((result['total'],result['items'],result['next_offset']),(0,[],None))
        for item_id in (None,'','../file',[],True):
            with self.subTest(item=item_id),self.assertRaises(module.ControlSourceCatalogError) as caught:catalog.detail(item_id)
            self.assertEqual(caught.exception.code,'catalog_invalid_query')
        with self.assertRaises(module.ControlSourceCatalogError) as caught:catalog.detail('UNKNOWN')
        self.assertEqual(caught.exception.code,'catalog_item_not_found')

    def test_nested_results_are_detached_from_every_following_response(self):
        catalog=self.catalog();original=catalog.detail('MOD-c40c6c5f1b4e7ca9');changed=catalog.detail('MOD-c40c6c5f1b4e7ca9')
        changed['record']['research_record']['sources'][0]['license']='changed'
        changed['profile_candidates'][0]['normalized_label_candidates'].clear();changed['review_notes'][0]['evidence'].clear()
        self.assertEqual(catalog.detail('MOD-c40c6c5f1b4e7ca9'),original)
        summary=catalog.summary();summary['registry_snapshot']['sha256']='changed';summary['scope_counts'].clear()
        self.assertEqual(catalog.summary()['registry_snapshot'],self.overlay['registry_snapshot'])
        page=catalog.find_items(profile_id='n9030a-49f214c7ff');expected=copy.deepcopy(page)
        page['items'][0]['candidate_virtual_profile_ids'].append('changed')
        self.assertEqual(catalog.find_items(profile_id='n9030a-49f214c7ff'),expected)

    def test_only_reading_five_inputs_without_db_network_commands_or_writes(self):
        module=self.module();denied=AssertionError('catalog performed non-read operation')
        before={name:sha((REPO/name).read_bytes()) for name in FILES}
        db=REPO/'data/equipment.sqlite3';db_before=sha(db.read_bytes()) if db.exists() else None
        with patch('sqlite3.connect',side_effect=denied),patch('socket.socket',side_effect=denied),\
             patch('subprocess.Popen',side_effect=denied),patch.object(Path,'write_bytes',side_effect=denied),\
             patch.object(Path,'write_text',side_effect=denied),patch.object(Path,'mkdir',side_effect=denied):
            catalog=module.ControlSourceCatalog();catalog.summary();catalog.find_items();catalog.detail('MOD-c40c6c5f1b4e7ca9')
        self.assertEqual({name:sha((REPO/name).read_bytes()) for name in FILES},before)
        if db_before is not None:self.assertEqual(sha(db.read_bytes()),db_before)

    def test_snapshot_does_not_reread_inputs_after_construction(self):
        module=self.module()
        with self.private_inputs() as root:
            catalog=module.ControlSourceCatalog(root);expected=catalog.summary()
            (root/FILES[0]).unlink()
            with patch.object(Path,'open',side_effect=AssertionError('response reread input')):
                self.assertEqual(catalog.summary(),expected);self.assertEqual(catalog.find_items()['total'],3137)
                catalog.detail('MOD-c40c6c5f1b4e7ca9')
            self.unavailable(root)

    def test_every_missing_or_byte_modified_input_is_unavailable(self):
        for name in FILES:
            with self.subTest(file=name),self.private_inputs() as root:
                (root/name).unlink();self.unavailable(root)
            with self.subTest(tamper=name),self.private_inputs() as root:
                (root/name).write_bytes(self.raw[name]+b' ');self.unavailable(root)

    def test_strict_utf8_finite_json_and_duplicate_keys_before_structure(self):
        for payload in (b'\xef\xbb\xbf[]',b'\xff',b'{"x":1,"x":2}',b'NaN',b'1e999',b'"\\ud800"'):
            with self.subTest(payload=payload[:10]),self.private_inputs() as root:
                with self.repinned(root,FILES[0],payload):self.unavailable(root)

    def test_structural_ids_relationships_and_support_flags_fail_closed(self):
        cases=[('duplicate_item',0),('equipment_relation',0),('research_hardware',0),('overlay_model',1),
            ('adapter_support',1),('numeric_false',1),('installed_binding',1),('profile_candidate',1),
            ('source_index',2),('url_relation',2),('url_support',2),('prior_id',3),('review_item',4)]
        for case,index in cases:
            value=copy.deepcopy(self.data[FILES[index]])
            if case=='duplicate_item':value[1]['item_id']=value[0]['item_id']
            elif case=='equipment_relation':value[1]['equipment_ids'][0]=value[0]['equipment_ids'][0]
            elif case=='research_hardware':value[0]['hardware_verified']=True
            elif case=='overlay_model':value['records'][0]['registry_reconciliation']['model_id']='UNKNOWN'
            elif case=='adapter_support':value['records'][0]['adapter_support_status']='supported'
            elif case=='numeric_false':value['records'][0]['vendor_binary_executed']=0
            elif case=='installed_binding':value['profile_crosswalk']['profiles'][0]['installed_equipment_binding_established']=True
            elif case=='profile_candidate':value['profile_crosswalk']['profiles'][0]['same_model_other_manufacturer_candidates'][0]['item_id']='UNKNOWN'
            elif case=='source_index':next(row for row in value['sources'] if row['research_associations'])['research_associations'][0]['source_index']=True
            elif case=='url_relation':next(row for row in value['sources'] if row['research_associations'])['research_associations'][0]['item_id']='UNKNOWN'
            elif case=='url_support':value['sources'][0]['execution_and_hardware_verification']='hardware_verified'
            elif case=='prior_id':value['links'][1]['id']=value['links'][0]['id']
            else:value['notes'][0]['item_ids'][0]='UNKNOWN'
            payload=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            with self.subTest(case=case),self.private_inputs() as root:
                with self.repinned(root,FILES[index],payload):self.unavailable(root)

    def test_file_byte_cap_rejects_before_opening_oversized_payload(self):
        module=self.module()
        with self.private_inputs() as root:
            target=root/FILES[0]
            with target.open('wb') as stream:stream.truncate(32*1024*1024+1)
            opened=Path.open
            def guarded(path,*args,**kwargs):
                if path==target:raise AssertionError('oversized payload was opened before byte cap')
                return opened(path,*args,**kwargs)
            with patch.object(Path,'open',guarded):self.unavailable(root)

    def test_metadata_count_and_evidence_shapes_are_strict_after_pin_validation(self):
        for case,index in (('count_float',1),('profile_evidence',1),('review_evidence',4)):
            value=copy.deepcopy(self.data[FILES[index]])
            if case=='count_float':value['registry_snapshot']['identity_item_count']=270.0
            elif case=='profile_evidence':value['profile_crosswalk']['profiles'][0]['profile_evidence_refs']=['invalid']
            else:value['notes'][0]['evidence']=['invalid']
            payload=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            with self.subTest(case=case),self.private_inputs() as root:
                with self.repinned(root,FILES[index],payload):self.unavailable(root)

    def test_raw_pins_do_not_accept_crlf_or_mixed_newline_rewrites(self):
        for name in FILES:
            with self.subTest(file=name),self.private_inputs() as root:
                changed=self.raw[name].replace(b'\n',b'\r\n')
                self.assertNotEqual(changed,self.raw[name]);(root/name).write_bytes(changed);self.unavailable(root)


if __name__=='__main__':unittest.main()
