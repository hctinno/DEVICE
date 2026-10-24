"""Synthetic metadata only: grouping contracts do not execute an AI evaluation."""
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import time
import unittest
from unittest.mock import patch
import uuid

from labflow import fcc_case_evaluation as module


TOP_KEYS={'schema_version','kind','algorithm','status','input_fingerprint','scope','fact_review_verified',
    'model_execution_verified','training_executed','evaluation_executed','hardware_verified','independent_assignment_status',
    'case_count','component_count','eligible_component_count','ineligible_component_count','denominators',
    'cases','components','development','independent','unassigned'}
INPUT_KEYS={'case_id','product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids',
            'group_review_status','unresolved_relations'}
KEY_NAMES={'product_family_group_ids','fcc_ids','report_group_ids','original_sha256s','reuse_group_ids'}
PREFIX='fcc_case_evaluation_'


def digest(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()


def row(case_id,**changes):
    return {'case_id':case_id,'product_family_group_id':'family:'+case_id,'fcc_ids':['FCC-'+case_id.upper()],
        'report_group_id':'report:'+case_id,'original_sha256s':[digest('original:'+case_id)],'reuse_group_ids':[],
        'group_review_status':'reviewed','unresolved_relations':[],**changes}


def build(cases,dev=(),ind=()):
    return module.build_case_evaluation_split(cases,development_case_ids=list(dev),independent_case_ids=list(ind))


class CaseEvaluationTests(unittest.TestCase):
    def assert_error(self,code,cases,dev=(),ind=()):
        with self.assertRaisesRegex(ValueError,'^'+PREFIX+code+'$'):build(cases,dev,ind)

    def check(self,result):
        self.assertEqual(set(result),TOP_KEYS)
        self.assertEqual((result['schema_version'],result['kind'],result['algorithm'],result['status']),
            (1,'fcc_case_evaluation_split','namespaced_connected_components_v1','configured'))
        self.assertEqual(result['scope'],'provided_metadata_only')
        for key in ['fact_review_verified','model_execution_verified','training_executed','evaluation_executed','hardware_verified']:
            self.assertIs(result[key],False)
        self.assertRegex(result['input_fingerprint'],'^[0-9a-f]{64}$')
        self.assertFalse(any('score' in key for key in result))
        for case in result['cases']:
            self.assertEqual(set(case),INPUT_KEYS|{'group_id','eligible','case_ineligibility_reasons','component_ineligibility_reasons'})
        for component in result['components']:
            self.assertEqual(set(component),{'group_id','group_sha256','case_ids','keys','eligible','ineligibility_reasons','ineligible_case_ids'})
            self.assertEqual(set(component['keys']),KEY_NAMES)
            self.assertEqual(component['group_id'],'case-group:'+component['group_sha256'])
        for split in ['development','independent','unassigned']:self.assertEqual(set(result[split]),{'case_ids','group_ids'})
        self.assertEqual(set(result['denominators']),{'provided_cases','provided_components','eligible_cases','ineligible_cases',
            'eligible_components','ineligible_components','development_cases','independent_cases','unassigned_cases'})

    def test_empty_input_is_configuration_without_evaluation(self):
        value=build([]);self.check(value)
        self.assertEqual(value['case_count'],0);self.assertEqual(value['component_count'],0)
        self.assertEqual(value['independent_assignment_status'],'not_assigned')
        self.assertTrue(all(count==0 for count in value['denominators'].values()))

    def test_separate_groups_assign_exact_cases_and_preserve_unassigned(self):
        value=build([row('c'),row('a'),row('b')],['a'],['b']);self.check(value)
        self.assertEqual(value['case_count'],3);self.assertEqual(value['component_count'],3)
        self.assertEqual(value['development']['case_ids'],['a'])
        self.assertEqual(value['independent']['case_ids'],['b'])
        self.assertEqual(value['unassigned']['case_ids'],['c'])
        self.assertEqual(value['independent_assignment_status'],'assigned')
        self.assertEqual(value['denominators'],{'provided_cases':3,'provided_components':3,'eligible_cases':3,'ineligible_cases':0,
            'eligible_components':3,'ineligible_components':0,'development_cases':1,'independent_cases':1,'unassigned_cases':1})

    def test_each_relationship_namespace_joins_cases(self):
        for field,value in [('product_family_group_id','shared'),('fcc_ids',['FCC-SHARED']),('report_group_id','report-shared'),
                            ('original_sha256s',['1'*64]),('reuse_group_ids',['reused'])]:
            with self.subTest(field=field):
                cases=[row('a',**{field:value}),row('b',**{field:value})]
                result=build(cases,['b','a']);self.check(result)
                self.assertEqual(result['component_count'],1)
                self.assertEqual(result['components'][0]['case_ids'],['a','b'])
                self.assertEqual(result['development']['case_ids'],['a','b'])

    def test_same_string_in_different_namespaces_never_joins(self):
        fields=['product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids']
        for left,right in itertools.combinations(fields,2):
            with self.subTest(left=left,right=right):
                a,b=row('a'),row('b')
                for case,field in [(a,left),(b,right)]:case[field]=['1'*64] if field.endswith('s') else '1'*64
                result=build([a,b],['a'],['b'])
                self.assertEqual(result['component_count'],2)

    def test_transitive_relationships_use_every_input_case(self):
        cases=[row('a',fcc_ids=['BRIDGE']),row('b',fcc_ids=['BRIDGE'],reuse_group_ids=['middle']),
            row('c',reuse_group_ids=['middle'],original_sha256s=['2'*64]),row('d',original_sha256s=['2'*64])]
        result=build(cases);self.assertEqual(result['component_count'],1)
        self.assertEqual(result['components'][0]['case_ids'],['a','b','c','d'])
        self.assert_error('cross_split_component',cases,['a'],['d'])
        self.assert_error('partial_component',cases,['a'])

    def test_unselected_bridge_prevents_false_independence(self):
        cases=[row('dev',fcc_ids=['SHARED']),row('bridge',fcc_ids=['SHARED'],reuse_group_ids=['shared-reuse']),
               row('ind',reuse_group_ids=['shared-reuse'])]
        self.assert_error('cross_split_component',cases,['dev'],['ind'])

    def test_revision_parts_and_repeated_physical_sha_are_preserved(self):
        cases=[row('report-r0-part1',report_group_id='DECLARED-SERIES'),row('report-r1-part2',report_group_id='declared-series'),
               row('pdf-other-exhibit',original_sha256s=[digest('same-pdf')]),row('pdf-alternate-listing',original_sha256s=[digest('same-pdf')])]
        value=build(cases,['report-r0-part1','report-r1-part2'],['pdf-other-exhibit','pdf-alternate-listing'])
        self.assertEqual(value['case_count'],4);self.assertEqual(value['component_count'],2)
        self.assertEqual([case['case_id'] for case in value['cases']],sorted(case['case_id'] for case in cases))
        self.assertEqual(sum(len(group['keys']['original_sha256s']) for group in value['components']),3)

    def test_revision_and_part_strings_are_not_inferred_or_stripped(self):
        cases=[row('a',report_group_id='R-10 Rev 1 Part 1'),row('b',report_group_id='R-10 Rev 2 Part 2')]
        self.assertEqual(build(cases,['a'],['b'])['component_count'],2)

    def test_documented_normalization_and_array_order_are_deterministic(self):
        a=row('a',product_family_group_id=' Straße ',fcc_ids=[' abC-10 ',' z-2 '],report_group_id=' R-0 ',reuse_group_ids=[' ReUse-B ','a'])
        b=row('b',product_family_group_id='STRASSE')
        first=build([b,a],['b','a'])
        normalized=copy.deepcopy([a,b])
        normalized[0].update(product_family_group_id='strasse',fcc_ids=['Z-2','ABC-10'],report_group_id='r-0',reuse_group_ids=['a','reuse-b'])
        normalized[1]['product_family_group_id']='strasse'
        self.assertEqual(first,build(normalized,['a','b']))
        self.assertEqual(first['cases'][0]['fcc_ids'],['ABC-10','Z-2'])

    def test_fcc_trim_upper_connects_without_normalizing_case_ids(self):
        cases=[row('CaseA',fcc_ids=[' abc-10 ']),row('casea',fcc_ids=['ABC-10'])]
        value=build(cases,['casea','CaseA'])
        self.assertEqual(value['component_count'],1)
        self.assertEqual(value['development']['case_ids'],['CaseA','casea'])
        self.assert_error('unknown_case_id',cases,['CASEA'])

    def test_input_order_does_not_change_full_dto_or_error(self):
        cases=[row('c'),row('a'),row('b')]
        expected=build(cases,['a','c'],['b'])
        for order in itertools.permutations(cases):self.assertEqual(build(list(order),['c','a'],['b']),expected)

    def test_group_hash_uses_sorted_ids_and_namespaced_keys(self):
        value=build([row('b'),row('a',reuse_group_ids=['only-a'])])
        for group in value['components']:
            encoded=json.dumps({'schema_version':1,'case_ids':group['case_ids'],'keys':group['keys']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            self.assertEqual(group['group_sha256'],hashlib.sha256(encoded).hexdigest())
        canonical=[{key:case[key] for key in INPUT_KEYS} for case in value['cases']]
        encoded=json.dumps({'schema_version':1,'algorithm':'namespaced_connected_components_v1','cases':canonical,
            'development_case_ids':[],'independent_case_ids':[]},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(value['input_fingerprint'],hashlib.sha256(encoded).hexdigest())

    def test_review_change_updates_fingerprint_but_not_connectivity_hash(self):
        cases=[row('a'),row('b',product_family_group_id='family:a')]
        first=build(cases);cases[1]['group_review_status']='pending';second=build(cases)
        self.assertEqual(first['components'][0]['group_id'],second['components'][0]['group_id'])
        self.assertNotEqual(first['input_fingerprint'],second['input_fingerprint'])
        self.assertFalse(second['components'][0]['eligible'])

    def test_each_missing_or_unreviewed_fact_makes_component_ineligible(self):
        for change,reason in [({'product_family_group_id':None},'missing_product_family_group'),({'report_group_id':None},'missing_report_group'),
                ({'fcc_ids':[]},'missing_fcc_id'),({'original_sha256s':[]},'missing_source_sha256'),
                ({'group_review_status':'pending'},'group_review_pending'),({'unresolved_relations':['unknown']},'unresolved_relations')]:
            with self.subTest(reason=reason):
                cases=[row('healthy',reuse_group_ids=['shared']),row('incomplete',reuse_group_ids=['shared'],**change)]
                value=build(cases);component=value['components'][0]
                self.assertFalse(component['eligible']);self.assertEqual(component['ineligibility_reasons'],[reason])
                self.assertEqual(component['ineligible_case_ids'],['incomplete'])
                healthy=next(case for case in value['cases'] if case['case_id']=='healthy')
                self.assertEqual(healthy['case_ineligibility_reasons'],[])
                self.assertEqual(healthy['component_ineligibility_reasons'],[reason]);self.assertFalse(healthy['eligible'])
                self.assertEqual(value['denominators']['ineligible_cases'],2)
                self.assert_error('ineligible_component',cases,['healthy','incomplete'])

    def test_unknown_relationship_is_not_a_known_union_key(self):
        cases=[row('a',unresolved_relations=['Unknown-Link']),row('b',unresolved_relations=['unknown-link'])]
        value=build(cases);self.assertEqual(value['component_count'],2)
        self.assertTrue(all(not group['eligible'] for group in value['components']))

    def test_missing_keys_are_not_replaced_by_case_id(self):
        cases=[row(name,product_family_group_id=None,report_group_id=None,fcc_ids=[],original_sha256s=[]) for name in ['a','b']]
        value=build(cases);self.assertEqual(value['component_count'],2)
        self.assertTrue(all(all(not keys for keys in group['keys'].values()) for group in value['components']))
        self.assertEqual(value['unassigned']['case_ids'],['a','b'])
        self.assertTrue(all(not case['eligible'] for case in value['cases']))

    def test_reviewed_empty_reuse_is_distinct_from_pending_unknown(self):
        value=build([row('reviewed'),row('pending',group_review_status='pending')])
        self.assertEqual(value['eligible_component_count'],1);self.assertEqual(value['ineligible_component_count'],1)
        self.assertEqual(value['unassigned']['case_ids'],['pending','reviewed'])

    def test_selection_unknown_duplicates_overlap_partial_and_cross_are_fixed_errors(self):
        cases=[row('a'),row('b',product_family_group_id='family:a')]
        self.assert_error('unknown_case_id',cases,['missing'])
        self.assert_error('duplicate_selection',cases,['a','a'])
        self.assert_error('duplicate_selection',cases,[],['a','a'])
        self.assert_error('overlapping_selection',cases,['a'],['a'])
        self.assert_error('cross_split_component',cases,['a'],['b'])
        self.assert_error('partial_component',cases,['a'])
        self.assert_error('partial_component',cases,[],['b'])

    def test_no_implicit_expansion_and_inputs_unchanged_on_failure(self):
        cases=[row('a'),row('b',product_family_group_id='family:a')];before=copy.deepcopy(cases)
        self.assert_error('partial_component',cases,['a'])
        self.assertEqual(cases,before)

    def test_duplicate_case_id_rejected_without_discarding_pdf_relations(self):
        self.assert_error('duplicate_case_id',[row('same'),row('same')])
        value=build([row('a',original_sha256s=['3'*64]),row('b',original_sha256s=['3'*64])])
        self.assertEqual(value['case_count'],2);self.assertEqual(value['component_count'],1)

    def test_normalized_list_duplicates_and_invalid_hashes_are_input_errors(self):
        for change in [{'fcc_ids':['ABC',' abc ']},{'reuse_group_ids':['X','x']},{'unresolved_relations':['X',' x ']},
            {'original_sha256s':['1'*64,'1'*64]},{'original_sha256s':['A'*64]},{'original_sha256s':['0'*63]},
            {'original_sha256s':[' '+'0'*64]},{'product_family_group_id':' '},{'report_group_id':''}]:
            with self.subTest(change=change):self.assert_error('input_invalid',[row('a',**change)])

    def test_exact_row_shape_status_and_array_types(self):
        a=row('a');missing=copy.deepcopy(a);missing.pop('report_group_id')
        for value in [{**a,'source_path':'PRIVATE_PATH'},missing,None,[],{**a,'fcc_ids':None},{**a,'reuse_group_ids':()},
            {**a,'group_review_status':'assumed'},{**a,'case_id':'bad id'},{**a,'case_id':True},
            {**a,'report_group_id':False},{**a,'fcc_ids':[1]}]:
            with self.subTest(value_type=type(value).__name__):self.assert_error('input_invalid',[value])

    def test_exact_json_types_and_nonfinite_values_are_rejected(self):
        class HostileList(list):
            def __iter__(self):raise AssertionError('callback must not run')
        for value in [(),{},HostileList([row('a')]),[{'bad':object()}], [row('a',fcc_ids=[float('nan')])],
                      [row('a',report_group_id=float('inf'))],[row('a',report_group_id=1)], [row('a',report_group_id='x\ud800')]]:
            with self.subTest(value_type=type(value).__name__):self.assert_error('input_invalid',value)

    def test_selection_exact_type_ascii_ids_and_no_callbacks(self):
        for value in [(),None,'a',[1],[' a'],['bad id']]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'^'+PREFIX+'selection_invalid$'):
                    module.build_case_evaluation_split([row('a')],development_case_ids=value,independent_case_ids=[])

    def test_unicode_casefold_length_controls_and_no_extra_normalization(self):
        result=build([row('a',report_group_id='ß'*64)]);self.assertEqual(result['cases'][0]['report_group_id'],'ss'*64)
        self.assert_error('input_invalid',[row('a',report_group_id='ß'*65)])
        self.assert_error('input_invalid',[row('a',report_group_id='x\x00y')])
        self.assert_error('input_invalid',[row('a',report_group_id='x'*129)])
        value=build([row('a',product_family_group_id='é'),row('b',product_family_group_id='e\u0301')])
        self.assertEqual(value['component_count'],2)

    def test_case_and_per_row_array_count_boundaries(self):
        cases=[row('case:'+str(index)) for index in range(4096)]
        value=build(cases);self.assertEqual(value['case_count'],4096)
        self.assert_error('budget_exceeded',cases+[row('extra')])
        sixty_four=['FCC-'+str(index) for index in range(64)]
        self.assertEqual(len(build([row('a',fcc_ids=sixty_four)])['cases'][0]['fcc_ids']),64)
        self.assert_error('budget_exceeded',[row('a',fcc_ids=sixty_four+['overflow'])])
        self.assert_error('budget_exceeded',[row('a')],['x:'+str(index) for index in range(4097)])

    def test_deep_cycle_and_total_byte_budget_are_not_silently_truncated(self):
        nested='value'
        for _ in range(9):nested=[nested]
        self.assert_error('budget_exceeded',[row('a',reuse_group_ids=nested)])
        cycle=row('a');cycle['reuse_group_ids']=[cycle]
        self.assert_error('budget_exceeded',[cycle])
        long_ids=[str(index).zfill(4)+'x'*124 for index in range(64)]
        cases=[row('case:'+str(index),fcc_ids=long_ids,reuse_group_ids=long_ids,unresolved_relations=long_ids,
                   original_sha256s=[digest(str(item)) for item in range(64)]) for index in range(160)]
        self.assertGreater(len(json.dumps(cases,separators=(',',':')).encode()),4*1024*1024)
        self.assert_error('budget_exceeded',cases)

    def test_over_budget_prefix_stops_before_later_unsupported_data(self):
        oversized=row('a',report_group_id='x'*(4*1024*1024+1),reuse_group_ids=[object()])
        self.assert_error('budget_exceeded',[oversized])

    def test_graph_partitions_match_independent_pairwise_reachability(self):
        rng=random.Random(22)
        for attempt in range(40):
            cases=[row('case:'+str(index)) for index in range(14)]
            for case in cases:
                for field in ['product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids']:
                    if rng.random()<.3:
                        value='shared-'+str(rng.randrange(5))
                        if field=='original_sha256s':value=digest(value)
                        case[field]=[value] if field in ['fcc_ids','original_sha256s','reuse_group_ids'] else value
                if rng.random()<.1:case['group_review_status']='pending'
            def tokens(case):
                result=set()
                for field in ['product_family_group_id','fcc_ids','report_group_id','original_sha256s','reuse_group_ids']:
                    values=case[field] if type(case[field]) is list else [case[field]]
                    for value in values:
                        normalized=value.strip().upper() if field=='fcc_ids' else value.strip().casefold()
                        result.add((field,normalized))
                return result
            keys=[tokens(case) for case in cases]
            waiting=set(range(len(cases)));expected=[]
            while waiting:
                start=min(waiting);waiting.remove(start);component={start};frontier=[start]
                while frontier:
                    node=frontier.pop()
                    neighbors={other for other in waiting if keys[node]&keys[other]}
                    waiting-=neighbors;component|=neighbors;frontier.extend(neighbors)
                expected.append(component)
            dev,ind=[],[]
            for component in expected:
                if any(cases[index]['group_review_status']=='pending' for index in component):continue
                target=rng.randrange(3)
                if target<2:(dev if target==0 else ind).extend(cases[index]['case_id'] for index in component)
            value=build(list(reversed(cases)),dev,ind)
            actual={frozenset(group['case_ids']) for group in value['components']}
            self.assertEqual(actual,{frozenset(cases[index]['case_id'] for index in component) for component in expected},attempt)
            for group in value['components']:
                self.assertEqual(group['eligible'],not any(case['group_review_status']=='pending' for case in cases if case['case_id'] in group['case_ids']))

    def test_detached_output_and_input_are_preserved(self):
        cases=[row('a'),row('b')];before=copy.deepcopy(cases)
        value=build(cases,['a'],['b']);original=copy.deepcopy(value)
        value['cases'][0]['fcc_ids'].append('caller mutation')
        value['components'].clear();value['development']['case_ids'].clear()
        self.assertEqual(cases,before);self.assertEqual(build(cases,['a'],['b']),original)

    def test_pure_function_has_no_file_network_clock_random_process_or_writer_io(self):
        with patch.object(Path,'open') as files,patch('builtins.open') as opens,patch('os.open') as osopen, \
             patch.object(socket,'socket') as sockets,patch.object(subprocess,'Popen') as processes, \
             patch.object(time,'time') as clock,patch.object(time,'monotonic') as monotonic, \
             patch.object(random,'random') as rng,patch.object(uuid,'uuid4') as uuidgen:
            first=build([row('a'),row('b')],['a'],['b']);second=build([row('a'),row('b')],['a'],['b'])
        self.assertEqual(first,second)
        for mock in [files,opens,osopen,sockets,processes,clock,monotonic,rng,uuidgen]:mock.assert_not_called()


if __name__=='__main__':unittest.main()
