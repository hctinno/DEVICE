"""Public authored in-memory facts only; no actual sources, Store, or models."""
import copy
from decimal import Overflow as DecimalOverflow
import hashlib
import importlib
import importlib.util
import json
import socket
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input
from labflow.store import canonical
from test_intake_conducted_twin_plan import fixture


BLOCK='\n'.join(['frequency: 2412 MHz','on_average_power: -7 dBm','bandwidth: 20 MHz',
                 'duty_cycle: 50 %','modulation: CUSTOM-IQ','crest_factor: 4 dB'])

def H(value):return hashlib.sha256(value).hexdigest()

def authored(block=BLOCK):
    context,analysis,old=fixture()
    text='\n'.join(context['documents'][0]['text'].splitlines()[:3])+'\n'+block+'\n'
    document=context['documents'][0]
    document.update(text=text,bytes=len(text.encode('utf-8')),sha256=H(text.encode('utf-8')))
    for fact in analysis['facts']:
        for ref in fact['evidence']:ref['sha256']=document['sha256']
    ref=dict(path=document['path'],sha256=document['sha256'],line_start=4,
             line_end=3+len(block.splitlines()),quote=block,role='product')
    analysis['facts'].append(dict(field='features',value=block,status='explicit',evidence=[ref]))
    options=dict(expected_revision=context['revision'],expected_context_sha256=H(canonical(context).encode('utf-8')),method=old['method'])
    return context,analysis,options


class FactsToPlanTests(unittest.TestCase):
    maxDiff=None
    def setUp(self):self.context,self.analysis,self.options=authored()

    def api(self):
        name='labflow.intake_facts_to_conducted_plan'
        self.assertIsNotNone(importlib.util.find_spec(name),'assigned pure facts adapter is absent')
        return importlib.import_module(name)

    def build(self):
        return self.api().build_conducted_plan_from_intake_facts(self.context,self.analysis,**self.options)

    def parent_oracle(self):
        settings=dict(frequency_hz=2412000000,power_dbm=-7,bandwidth_hz=20000000,
            duty_cycle=0.5,modulation='CUSTOM-IQ',crest_factor_db=4)
        quoted=dict(frequency_hz=(2412,'MHz'),power_dbm=(-7,'dBm'),bandwidth_hz=(20,'MHz'),
            duty_cycle=(50,'%'),modulation=('CUSTOM-IQ','label'),crest_factor_db=(4,'dB'))
        ref=copy.deepcopy(self.analysis['facts'][-1]['evidence'][0])
        basis={key:dict(kind='source_cited',value=value,unit=unit,evidence=[copy.deepcopy(ref)])
               for key,(value,unit) in quoted.items()}
        return build_conducted_twin_plan_input(self.context,self.analysis,source_settings=settings,basis=basis,**self.options)

    def test_closed_fact_and_same_quote_yield_exact_genuine_parent_without_manual_settings(self):
        original=copy.deepcopy((self.context,self.analysis,self.options))
        result=self.build()
        self.assertEqual(set(result),set('schema_version kind status plan_input assembly_gaps questions'.split()))
        self.assertEqual(result['schema_version'],1)
        self.assertEqual(result['kind'],'intake_facts_to_conducted_plan')
        self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan_input'],self.parent_oracle())
        self.assertEqual(result['assembly_gaps'],[]);self.assertEqual(result['questions'],[])
        self.assertEqual((self.context,self.analysis,self.options),original)
        self.assertIs(result['plan_input']['verification']['execution_authority'],False)

    def settings(self,result):return result['plan_input']['plan']['source_settings']

    def block(self,text):self.context,self.analysis,self.options=authored(text)

    def test_missing_field_is_null_and_only_that_field_is_asked(self):
        self.block(BLOCK.replace('duty_cycle: 50 %\n',''))
        result=self.build();self.assertEqual(result['status'],'blocked')
        self.assertIsNone(self.settings(result)['duty_cycle'])
        self.assertTrue(all(v is not None for k,v in self.settings(result).items() if k!='duty_cycle'))
        self.assertEqual([q['field'] for q in result['questions']],['source_settings.duty_cycle'])

    def test_uncited_context_values_and_legacy_fixture_values_are_not_defaults(self):
        self.analysis['facts'].pop()
        result=self.build()
        self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual(len(result['questions']),6)
        self.assertTrue(all(v is None for v in result['plan_input']['plan']['basis_refs'].values()))

    def test_explicit_zero_power_and_crest_are_preserved(self):
        self.block(BLOCK.replace('-7 dBm','0 dBm').replace('4 dB','0 dB'))
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(self.settings(result)['power_dbm'],0);self.assertEqual(self.settings(result)['crest_factor_db'],0)

    def test_explicit_unit_conversion_preserves_original_quote_unit_in_basis(self):
        self.block(BLOCK.replace('2412 MHz','2.412 GHz').replace('20 MHz','20000 kHz').replace('50 %','0.5 ratio'))
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual((self.settings(result)['frequency_hz'],self.settings(result)['bandwidth_hz'],self.settings(result)['duty_cycle']),
                         (2412000000,20000000,0.5))
        refs=result['plan_input']['plan']['basis_refs']
        self.assertEqual((refs['frequency_hz']['value'],refs['frequency_hz']['unit']),(2.412,'GHz'))
        self.assertEqual((refs['bandwidth_hz']['value'],refs['bandwidth_hz']['unit']),(20000,'kHz'))

    def test_normalized_duplicate_values_in_one_condition_are_not_conflicts(self):
        self.block(BLOCK+'\nfrequency: 2.412 GHz')
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(self.settings(result)['frequency_hz'],2412000000)
        self.assertEqual(result['assembly_gaps'],[]);self.assertEqual(result['questions'],[])
        self.assertIn('2.412 GHz',result['plan_input']['intake']['source_facts'][-1]['value'])

    def test_conflict_keeps_all_raw_candidates_and_nulls_only_affected_field(self):
        self.block(BLOCK+'\nfrequency: 2437 MHz')
        result=self.build();self.assertIsNone(self.settings(result)['frequency_hz'])
        gap=next(g for g in result['assembly_gaps'] if g['field']=='source_settings.frequency_hz')
        self.assertEqual(gap['code'],'source_value_conflict')
        self.assertTrue({'2412','2437'}<={m['raw_value'] for m in gap['provided']})
        self.assertEqual([q['field'] for q in result['questions']],['source_settings.frequency_hz'])
        self.assertIsNotNone(self.settings(result)['power_dbm'])

    def test_valid_literal_quote_with_different_fact_value_is_not_used(self):
        self.block(BLOCK.replace('2412 MHz','2437 MHz'))
        self.analysis['facts'][-1]['value']=BLOCK
        result=self.build();self.assertIsNone(self.settings(result)['frequency_hz'])
        self.assertEqual(result['assembly_gaps'][0]['code'],'source_quote_mismatch')

    def test_original_feature_projection_conflict_is_not_rewritten(self):
        fact=copy.deepcopy(self.analysis['facts'][-1]);fact['value']=BLOCK.replace('2412 MHz','2.412 GHz')
        self.analysis['facts'].append(fact);original=copy.deepcopy(self.analysis)
        result=self.build();self.assertEqual(result['status'],'blocked')
        self.assertEqual(self.settings(result)['frequency_hz'],2412000000)
        self.assertTrue(any(g['code']=='conflicting_intake_fact' for g in result['plan_input']['gaps']))
        self.assertEqual(result['plan_input']['intake']['source_facts'],original['facts'])
        self.assertEqual(self.analysis,original)

    def test_inferred_or_uncertain_facts_are_not_upgraded_to_source_basis(self):
        for status in ('inferred','uncertain'):
            with self.subTest(status=status):
                self.context,self.analysis,self.options=authored();self.analysis['facts'][-1]['status']=status
                result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
                self.assertEqual(len({q['field'] for q in result['questions']}),6)
                self.assertTrue(all(g['code']=='source_fact_unverified' for g in result['assembly_gaps']))

    def test_peak_time_average_and_quantity_unknown_power_do_not_become_on_average(self):
        for label in ('report_peak','reported_peak','power','time_average_power'):
            with self.subTest(label=label):
                self.block(BLOCK.replace('on_average_power',label));result=self.build()
                self.assertIsNone(self.settings(result)['power_dbm'])
                self.assertEqual([q['field'] for q in result['questions']],['source_settings.power_dbm'])
                self.assertIsNone(result['plan_input']['plan']['basis_refs']['power_dbm'])

    def test_supported_on_average_spellings_keep_metric_scope_separate(self):
        for label in ('on_average_power','on-average power','on average power'):
            for metric in ('on','time','peak'):
                with self.subTest(label=label,metric=metric):
                    self.block(BLOCK.replace('on_average_power',label));self.options['method']['metric']=metric
                    result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
                    self.assertEqual(result['plan_input']['plan']['metric'],metric)
                    self.assertEqual(self.settings(result)['power_dbm'],-7)

    def test_unsupported_units_lists_and_ranges_are_not_repaired(self):
        for statement in ('frequency: 2412 mhz','frequency: 2412, 2437 MHz','frequency: 2400-2483.5 MHz','frequency: < 2412 MHz'):
            with self.subTest(statement=statement):
                self.block(BLOCK.replace('frequency: 2412 MHz',statement));result=self.build()
                self.assertIsNone(self.settings(result)['frequency_hz'])
                self.assertEqual(len(result['questions']),1)

    def test_modulation_is_literal_without_MCS_or_enum_inference(self):
        self.block(BLOCK.replace('CUSTOM-IQ','"CUSTOM IQ"'))
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(self.settings(result)['modulation'],'CUSTOM IQ')
        self.block(BLOCK.replace('modulation: CUSTOM-IQ','modulation: OFDM / CCK'))
        result=self.build();self.assertIsNone(self.settings(result)['modulation'])
        self.assertEqual([q['field'] for q in result['questions']],['source_settings.modulation'])

    def test_separate_literal_rows_are_not_stitched_into_one_condition(self):
        doc=self.context['documents'][0];fact=self.analysis['facts'][-1]
        fact['evidence']=[dict(path=doc['path'],sha256=doc['sha256'],line_start=4+i,line_end=4+i,quote=line,role='product')
                          for i,line in enumerate(BLOCK.splitlines())]
        result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual(result['assembly_gaps'][0]['code'],'source_condition_unbound')
        self.assertEqual(len(result['questions']),1)
        self.assertEqual(result['questions'][0]['field'],'source_settings')

    def test_same_physical_quote_can_bind_features_and_power_target(self):
        feature=self.analysis['facts'][-1]
        feature['value']=BLOCK.replace('on_average_power: -7 dBm\n','')
        reference=copy.deepcopy(feature['evidence'][0]);reference['role']='reference'
        self.analysis['facts'].append(dict(field='power_target',value='on_average_power: -7 dBm',status='explicit',evidence=[reference]))
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        basis=result['plan_input']['plan']['basis_refs']
        self.assertEqual(basis['power_dbm']['evidence'][0]['role'],'reference')
        self.assertEqual(basis['frequency_hz']['evidence'][0]['role'],'product')

    def test_same_quote_text_from_another_source_cannot_supply_missing_fields(self):
        from labflow.intake_jobs import _analysis_contract
        feature=self.analysis['facts'][-1];feature['value']=BLOCK.replace('on_average_power: -7 dBm\n','')
        doc=copy.deepcopy(self.context['documents'][0]);doc.update(path='another.txt',text=BLOCK+'\n',
            sha256=H((BLOCK+'\n').encode()),bytes=len((BLOCK+'\n').encode()))
        self.context['documents'].append(doc)
        self.context['analysis_contract']=_analysis_contract(dict(documents=self.context['documents'],context_id=self.context['analysis_context_id']))
        ref=dict(path=doc['path'],sha256=doc['sha256'],line_start=1,line_end=6,quote=BLOCK,role='reference')
        self.analysis['facts'].append(dict(field='power_target',value='on_average_power: -7 dBm',status='explicit',evidence=[ref]))
        self.options['expected_context_sha256']=H(canonical(self.context).encode())
        result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual(result['questions'][0]['reason'],'source_condition_unbound')

    def test_condition_marker_or_free_text_inside_block_is_not_ignored(self):
        self.block('mode A\n'+BLOCK)
        result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertTrue(all(g['code']=='source_statement_unsupported' for g in result['assembly_gaps']))

    def test_channel_HT20_and_MCS_do_not_fill_physical_settings(self):
        self.block('channel: 1\nmode: HT20\nMCS: 6')
        result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual(result['status'],'blocked')

    def test_normative_minimum_maximum_facts_do_not_become_settings_or_norm_pass(self):
        self.block('minimum_6dB_bandwidth: 500 kHz\nmaximum_conducted_output_power: 1 W')
        result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertIsNone(result['plan_input']['plan']['numeric_limit_dbm'])
        self.assertEqual(result['plan_input']['plan']['assessment'],'not_assessed')
        self.assertEqual(result['plan_input']['verification']['regulatory'],'not_assessed')

    def test_unsupported_method_is_forwarded_without_source_or_method_default(self):
        for field,value in [('method_version',True),('metric','reported_peak'),('reference_plane','antenna_output'),('method_id','FCC-PASS')]:
            with self.subTest(field=field):
                self.context,self.analysis,self.options=authored();self.options['method'][field]=value
                result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
                self.assertEqual(result['questions'],[]);self.assertEqual(result['status'],'blocked')
                self.assertTrue(any(g['field']=='method.'+field for g in result['plan_input']['gaps']))

    def test_stale_revision_or_context_pin_never_derives_from_otherwise_good_facts(self):
        for change in [dict(expected_revision=2),dict(expected_context_sha256='0'*64)]:
            with self.subTest(change=change):
                self.context,self.analysis,self.options=authored();self.options.update(change)
                result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
                self.assertEqual(result['assembly_gaps'],[]);self.assertEqual(result['questions'],[])

    def test_invalid_literal_citation_is_rejected_by_genuine_validator(self):
        self.analysis['facts'][-1]['evidence'][0]['quote']='not actually in source'
        result=self.build();self.assertEqual(result['status'],'blocked')
        self.assertTrue(any(g['code']=='analysis_evidence_invalid' for g in result['plan_input']['gaps']))
        self.assertEqual(result['questions'],[])

    def test_parent_numeric_range_and_coupled_RF_domain_are_preserved(self):
        for old,new in [('duty_cycle: 50 %','duty_cycle: 0 %'),('crest_factor: 4 dB','crest_factor: -1 dB'),
                        ('frequency: 2412 MHz','frequency: 1 Hz')]:
            with self.subTest(new=new):
                self.block(BLOCK.replace(old,new));result=self.build();self.assertEqual(result['status'],'blocked')
                self.assertTrue(any(g['code'] in ('invalid_setting','invalid_rf_domain') for g in result['plan_input']['gaps']))
                self.assertTrue(result['questions'])

    def test_very_long_exponents_are_rejected_before_expensive_decimal_work(self):
        api=self.api();decimal=api.Decimal
        def guarded(token):
            self.assertNotIn('e'+'9'*120,token)
            return decimal(token)
        for token in ('1e'+'9'*125,'1e'+'0'*130+'1','1e401','1e-401','1e-400'):
            with self.subTest(token=token):
                self.block(BLOCK.replace('2412 MHz',token+' MHz'))
                with patch.object(api,'Decimal',side_effect=guarded):result=self.build()
                self.assertIsNone(self.settings(result)['frequency_hz'])
                self.assertEqual(result['status'],'blocked')

    def test_unrepresentable_precision_and_nonfinite_text_are_not_rounded(self):
        for token in ('0.12345678901234567890123456789','NaN','Infinity','1e309'):
            with self.subTest(token=token):
                self.block(BLOCK.replace('2412 MHz',token+' MHz'));result=self.build()
                self.assertIsNone(self.settings(result)['frequency_hz'])

    def test_segment_and_candidate_caps_fail_closed_without_partial_success(self):
        self.block('\n'.join(['frequency: 2412 MHz']*129))
        result=self.build();self.assertEqual(result['assembly_gaps'][0]['code'],'source_candidate_limit')
        self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.context,self.analysis,self.options=authored()
        feature=copy.deepcopy(self.analysis['facts'][-1]);feature['evidence']*=20
        self.analysis['facts']=self.analysis['facts'][:3]+[copy.deepcopy(feature) for _ in range(197)]
        result=self.build();self.assertEqual(result['assembly_gaps'][0]['code'],'source_candidate_limit')
        self.assertEqual(len(result['plan_input']['intake']['source_facts']),200)
        self.assertEqual(len(result['questions']),1)

    def test_schema2_normalized_pdf_quote_reuses_genuine_citation_validation(self):
        from labflow.intake_documents import _spans
        from labflow.intake_jobs import _analysis_contract
        text=BLOCK+'\n'
        document=dict(path='authored-only.pdf',sha256=H(b'authored PDF identity, not file bytes'),bytes=100,
            format='pdf',text=None,parse_status='ok',extraction_id=H(b'authored extraction'),parser=dict(name='authored',version='1'),
            limits=dict(max_input_bytes=10000,max_pages=2,max_output_chars=10000,max_page_content_bytes=10000),
            issues=[],complete=True,total_pages=1,processed_pages=1,
            pages=[dict(page_number=1,status='ok',text=text,text_sha256=H(text.encode()),line_spans=_spans(text))])
        self.context['documents'].append(document)
        self.context['analysis_contract']=_analysis_contract(dict(documents=self.context['documents'],context_id=self.context['analysis_context_id']))
        self.analysis.update(schema_version=2,context_id=self.context['analysis_context_id'])
        for fact in self.analysis['facts']:
            for ref in fact['evidence']:ref['kind']='text_line'
        self.analysis['facts'][-1]['evidence']=[dict(kind='pdf_page',path=document['path'],sha256=document['sha256'],
            extraction_id=document['extraction_id'],page_number=1,text_sha256=document['pages'][0]['text_sha256'],
            line_start=1,line_end=6,quote=BLOCK,role='reference')]
        self.options['expected_context_sha256']=H(canonical(self.context).encode())
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan_input']['plan']['basis_refs']['frequency_hz']['evidence'][0]['kind'],'pdf_page')

    def test_observed_controls_and_memory_errors_keep_the_original_object(self):
        api=self.api()
        for kind in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            control=kind('authored original control')
            with self.subTest(kind=kind.__name__),patch.object(api,'validate_analysis',side_effect=control):
                with self.assertRaises(kind) as caught:self.build()
                self.assertIs(caught.exception,control)
        memory=MemoryError('authored Decimal control')
        with patch.object(api,'Decimal',side_effect=memory):
            with self.assertRaises(MemoryError) as caught:self.build()
        self.assertIs(caught.exception,memory)

    def test_runtime_has_no_IO_and_result_is_detached_and_deterministic(self):
        api=self.api();original=copy.deepcopy((self.context,self.analysis,self.options))
        with patch('builtins.open',side_effect=AssertionError('I/O forbidden')), \
                patch.object(sqlite3,'connect',side_effect=AssertionError('DB forbidden')), \
                patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')), \
                patch.object(subprocess,'Popen',side_effect=AssertionError('child forbidden')):
            result=self.build()
        again=self.build();self.assertEqual(result,again)
        result['plan_input']['plan']['source_settings']['frequency_hz']=1
        result['plan_input']['intake']['source_facts'][0]['value']='caller mutation'
        self.assertEqual(self.build(),again);self.assertEqual((self.context,self.analysis,self.options),original)

    def test_decimal_error_rejects_values_instead_of_claiming_success(self):
        api=self.api()
        with patch.object(api,'Decimal',side_effect=DecimalOverflow('authored bounded arithmetic fault')):
            result=self.build()
        self.assertEqual(result['status'],'blocked')
        self.assertIsNone(self.settings(result)['frequency_hz'])
        self.assertTrue(any(g['code']=='source_number_unrepresentable' for g in result['assembly_gaps']))

    def test_native_snapshot_rejects_subclasses_without_executing_hooks(self):
        class Hooked(dict):
            def items(self):raise AssertionError('native subclass hook must not run')
            def __iter__(self):raise AssertionError('native subclass hook must not run')
            def __str__(self):raise AssertionError('native subclass hook must not run')
        self.context=Hooked(self.context)
        result=self.build();self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['questions'],[])
        self.assertTrue(any(g['code']=='native_input_invalid' for g in result['plan_input']['gaps']))

    def test_new_RF_fact_field_is_not_added_to_the_strict_analysis_schema(self):
        self.analysis['facts'][-1]['field']='frequency_hz'
        result=self.build();self.assertEqual(result['status'],'blocked')
        self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual(result['questions'],[])
        self.assertTrue(any(g['code']=='analysis_evidence_invalid' for g in result['plan_input']['gaps']))

    def test_explicit_on_average_input_is_not_replaced_by_separate_reported_peak(self):
        for fact_includes_peak in (True,False):
            with self.subTest(fact_includes_peak=fact_includes_peak):
                self.block(BLOCK+'\nreported_peak: 13.5 dBm')
                if not fact_includes_peak:self.analysis['facts'][-1]['value']=BLOCK
                self.options['method']['metric']='peak'
                result=self.build()
                self.assertEqual(result['status'],'ready_for_simulation')
                self.assertEqual(self.settings(result)['power_dbm'],-7)
                self.assertEqual(result['plan_input']['plan']['metric'],'peak')
                self.assertIn('reported_peak: 13.5 dBm',result['plan_input']['intake']['source_facts'][-1]['evidence'][0]['quote'])

    def test_unrecognized_text_retains_original_locations_without_inferring_a_quantity(self):
        self.block('2.412 GHz')
        result=self.build();self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual(result['plan_input']['intake']['source_facts'][-1]['value'],'2.412 GHz')
        for gap in result['assembly_gaps']:
            self.assertTrue(gap['provided'])
            location=gap['provided'][0]
            self.assertEqual((location['fact_index'],location['evidence_index']),(3,0))
            self.assertEqual(location['value_span'],[0,len('2.412 GHz')])
            self.assertIsNone(location['raw_value'])


SUPPORT_BLOCK='\n'.join(['frequency_hz: 915000000 Hz','on_average_power: -11 dBm',
    'bandwidth_hz: 250000 Hz','duty_cycle: 25 %','modulation: LAB-PULSE','crest_factor: 2 dB'])


class CitedStatementSupportTests(unittest.TestCase):
    """Fresh synthetic grammar examples; original model response is not a golden."""
    maxDiff=None

    def setUp(self):self.case()

    def case(self,source=SUPPORT_BLOCK,value=None):
        self.context,self.analysis,self.options=authored(source)
        if value is not None:self.analysis['facts'][-1]['value']=value

    def build(self):
        from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
        return build_conducted_plan_from_intake_facts(self.context,self.analysis,**self.options)

    def settings(self,result):return result['plan_input']['plan']['source_settings']

    def oracle(self):
        settings=dict(frequency_hz=915000000,power_dbm=-11,bandwidth_hz=250000,
            duty_cycle=0.25,modulation='LAB-PULSE',crest_factor_db=2)
        literals=dict(frequency_hz=(915000000,'Hz'),power_dbm=(-11,'dBm'),bandwidth_hz=(250000,'Hz'),
            duty_cycle=(25,'%'),modulation=('LAB-PULSE','label'),crest_factor_db=(2,'dB'))
        refs=self.analysis['facts'][-1]['evidence']
        basis={key:dict(kind='source_cited',value=value,unit=unit,evidence=copy.deepcopy(refs))
               for key,(value,unit) in literals.items()}
        return build_conducted_twin_plan_input(self.context,self.analysis,source_settings=settings,basis=basis,**self.options)

    def split_case(self,missing_unit=False):
        feature='; '.join(line for line in SUPPORT_BLOCK.splitlines() if not line.startswith('on_average_power:'))
        if missing_unit:feature=feature.replace('25 %','25')
        power='on_average_power: -11 dBm'
        lines=['Source context for a synthetic example.','features: '+feature,
               'power_target: '+power,'Method and accuracy remain unverified.']
        self.case('\n'.join(lines),'Synthetic settings: '+feature)
        doc=self.context['documents'][0]
        def ref(index):
            return dict(path=doc['path'],sha256=doc['sha256'],line_start=4+index,line_end=4+index,
                        quote=lines[index],role='product')
        self.analysis['facts'][-1]['evidence']=[ref(0),ref(1)]
        self.analysis['facts'].append(dict(field='power_target',value='Invented setting: '+power+'; not a measurement',
            status='explicit',evidence=[ref(0),ref(2)]))
        self.analysis['facts'].append(dict(field='features',value=lines[3],status='uncertain',evidence=[ref(3)]))

    def test_explicit_hz_aliases_match_the_genuine_parent_and_keep_original_units(self):
        original=copy.deepcopy((self.context,self.analysis,self.options))
        result=self.build()
        self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan_input'],self.oracle())
        self.assertEqual((self.context,self.analysis,self.options),original)
        self.assertEqual(result['questions'],[])

    def test_closed_source_wrapper_and_supported_synthetic_description_preserve_raw_facts(self):
        value='Synthetic settings: '+SUPPORT_BLOCK+'; not a measurement'
        self.case('features: '+SUPPORT_BLOCK,value)
        result=self.build()
        self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan_input'],self.oracle())
        fact=result['plan_input']['intake']['source_facts'][-1]
        self.assertEqual(fact['value'],value)
        self.assertEqual(fact['evidence'][0]['quote'],'features: '+SUPPORT_BLOCK)
        self.assertIs(result['plan_input']['verification']['execution_authority'],False)

    def test_unitless_duty_is_not_defaulted_and_only_its_unit_is_asked(self):
        self.case(SUPPORT_BLOCK.replace('25 %','25'))
        result=self.build()
        self.assertEqual(result['status'],'blocked')
        self.assertIsNone(self.settings(result)['duty_cycle'])
        self.assertTrue(all(v is not None for k,v in self.settings(result).items() if k!='duty_cycle'))
        self.assertEqual([q['field'] for q in result['questions']],['source_settings.duty_cycle'])
        self.assertEqual(result['questions'][0]['reason'],'source_unit_missing')
        gap=next(g for g in result['assembly_gaps'] if g['field']=='source_settings.duty_cycle')
        self.assertEqual((gap['provided'][0]['raw_value'],gap['provided'][0]['unit']),('25',None))

    def test_split_explicit_candidates_keep_only_condition_and_missing_unit_questions(self):
        self.split_case(missing_unit=True)
        original=copy.deepcopy(self.analysis)
        result=self.build()
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual({q['field'] for q in result['questions']},{'source_settings','source_settings.duty_cycle'})
        self.assertEqual({q['reason'] for q in result['questions']},{'source_condition_unbound','source_unit_missing'})
        self.assertEqual(len(result['questions']),2)
        self.assertEqual(result['plan_input']['intake']['source_facts'],original['facts'])
        gap=next(g for g in result['assembly_gaps'] if g['code']=='source_condition_unbound')
        self.assertEqual({m['unit'] for m in gap['provided']},{'Hz','dBm','label','dB'})
        self.assertEqual({m['raw_value'] for m in gap['provided']},{'915000000','-11','250000','LAB-PULSE','2'})
        self.assertTrue(any(g['code']=='uncertain_intake_fact' and g['blocking'] is False for g in result['plan_input']['gaps']))

    def test_complete_but_separate_physical_quotes_still_require_condition_binding(self):
        self.split_case()
        result=self.build()
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertEqual([q['reason'] for q in result['questions']],['source_condition_unbound'])
        self.assertEqual(len(result['assembly_gaps']),1)

    def test_both_field_wrappers_in_one_physical_quote_can_support_the_genuine_parent(self):
        feature='; '.join(line for line in SUPPORT_BLOCK.splitlines() if not line.startswith('on_average_power:'))
        power='on_average_power: -11 dBm'
        source='features: '+feature+'\npower_target: '+power
        self.case(source,'Synthetic setting: '+feature)
        ref=copy.deepcopy(self.analysis['facts'][-1]['evidence'][0])
        self.analysis['facts'].append(dict(field='power_target',value='Invented settings: '+power,
            status='explicit',evidence=[ref]))
        result=self.build()
        self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan_input'],self.oracle())
        self.assertEqual(result['assembly_gaps'],[])
        self.assertEqual(result['questions'],[])

    def test_only_closed_synthetic_qualifiers_are_supported_without_general_narrative_stripping(self):
        for prefix in ('Synthetic setting: ','Invented settings: ','Synthetic simulator settings, not measurements: '):
            with self.subTest(prefix=prefix):
                self.case('features: '+SUPPORT_BLOCK,prefix+SUPPORT_BLOCK+'; not measurements or product capabilities')
                result=self.build()
                self.assertEqual(result['status'],'ready_for_simulation')
                self.assertEqual(result['plan_input'],self.oracle())
        for prefix,suffix in [('Do not use: ',''),('Synthetic settings 9: ',''),('Example explanation: ',''),
                             ('Synthetic settings: ','; if another mode is selected'),('Synthetic settings: ','; not on-average power')]:
            with self.subTest(prefix=prefix,suffix=suffix):
                self.case('features: '+SUPPORT_BLOCK,prefix+SUPPORT_BLOCK+suffix)
                result=self.build()
                self.assertEqual(result['status'],'blocked')
                self.assertTrue(all(v is None for v in self.settings(result).values()))

    def test_negated_ambiguous_source_wrappers_are_not_repaired_from_good_fact_values(self):
        for source in ('not features: '+SUPPORT_BLOCK,'limits: '+SUPPORT_BLOCK,
                       'features: not '+SUPPORT_BLOCK,'features: '+SUPPORT_BLOCK+'\nmode: second'):
            with self.subTest(source=source.splitlines()[0]):
                self.case(source,'Synthetic settings: '+SUPPORT_BLOCK)
                result=self.build()
                self.assertEqual(result['status'],'blocked')
                self.assertTrue(all(v is None for v in self.settings(result).values()))

    def test_hz_alias_requires_explicit_hz_and_never_uses_the_key_as_a_unit_default(self):
        for statement,code in [('frequency_hz: 915000000','source_unit_missing'),
                               ('frequency_hz: 915 MHz','source_unit_unsupported'),
                               ('frequency_hz: 915000000 Hz MHz','source_statement_unsupported')]:
            with self.subTest(statement=statement):
                self.case(SUPPORT_BLOCK.replace('frequency_hz: 915000000 Hz',statement))
                result=self.build()
                self.assertIsNone(self.settings(result)['frequency_hz'])
                gap=next(g for g in result['assembly_gaps'] if g['field']=='source_settings.frequency_hz')
                self.assertEqual(gap['code'],code)
                self.assertEqual([q['field'] for q in result['questions']],['source_settings.frequency_hz'])
        self.case(SUPPORT_BLOCK.replace('frequency_hz: 915000000 Hz','frequency: 915 MHz'))
        self.assertEqual(self.build()['status'],'ready_for_simulation')

    def test_supported_descriptions_cannot_override_mismatch_conflict_or_unverified_status(self):
        self.case('features: '+SUPPORT_BLOCK,'Synthetic settings: '+SUPPORT_BLOCK.replace('915000000','916000000'))
        result=self.build()
        self.assertIsNone(self.settings(result)['frequency_hz'])
        self.assertTrue(any(g['code']=='source_quote_mismatch' for g in result['assembly_gaps']))
        self.case('features: '+SUPPORT_BLOCK+'\nfrequency_hz: 916000000 Hz',
                  'Synthetic settings: '+SUPPORT_BLOCK+'\nfrequency_hz: 916000000 Hz')
        result=self.build()
        self.assertIsNone(self.settings(result)['frequency_hz'])
        self.assertTrue(any(g['code']=='source_value_conflict' for g in result['assembly_gaps']))
        self.case('features: '+SUPPORT_BLOCK,'Synthetic settings: '+SUPPORT_BLOCK)
        self.analysis['facts'][-1]['status']='uncertain'
        result=self.build()
        self.assertTrue(all(v is None for v in self.settings(result).values()))
        self.assertTrue(all(g['code']=='source_fact_unverified' for g in result['assembly_gaps']))

    def test_metadata_spans_address_original_qualified_value_and_wrapped_quote(self):
        self.split_case(missing_unit=True)
        original=copy.deepcopy(self.analysis)
        result=self.build()
        for gap in result['assembly_gaps']:
            self.assertEqual(set(gap),{'code','field','provided','blocking'})
            for item in gap['provided']:
                self.assertEqual(set(item),{'fact_index','evidence_index','raw_value','unit','value_span','quote_span'})
                fact=original['facts'][item['fact_index']]
                quote=fact['evidence'][item['evidence_index']]['quote']
                left,right=item['value_span'];qleft,qright=item['quote_span']
                self.assertTrue(0<=left<=right<=len(fact['value']))
                self.assertTrue(0<=qleft<=qright<=len(quote))
                self.assertIn(item['raw_value'],fact['value'][left:right])
                self.assertIn(item['raw_value'],quote[qleft:qright])
        self.assertEqual(self.analysis,original)
        self.assertIsNone(result['plan_input']['plan']['numeric_limit_dbm'])
        self.assertIsNone(result['plan_input']['plan']['uncertainty_db'])
        self.assertEqual(result['plan_input']['plan']['assessment'],'not_assessed')

    def test_qualifier_path_preserves_control_objects_and_performs_no_IO(self):
        from labflow import intake_facts_to_conducted_plan as module
        self.case('features: '+SUPPORT_BLOCK,'Synthetic settings: '+SUPPORT_BLOCK)
        for error in (MemoryError('qualifier-control'),KeyboardInterrupt('qualifier-control'),SystemExit('qualifier-control')):
            with self.subTest(kind=type(error).__name__):
                with patch.object(module,'_quantity',side_effect=error):
                    with self.assertRaises(type(error)) as caught:self.build()
                self.assertIs(caught.exception,error)
        def forbidden(*args,**kwargs):raise AssertionError('unexpected I/O')
        with patch('builtins.open',forbidden),patch.object(sqlite3,'connect',forbidden),\
             patch.object(subprocess,'Popen',forbidden),patch.object(socket,'socket',forbidden):
            result=self.build()
        self.assertEqual(result['status'],'ready_for_simulation')

    def test_alias_source_still_requires_genuine_current_context_and_exact_citation(self):
        self.options['expected_revision']+=1
        result=self.build()
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['assembly_gaps'],[])
        self.assertEqual(result['questions'],[])
        self.case('features: '+SUPPORT_BLOCK,'Synthetic settings: '+SUPPORT_BLOCK)
        self.analysis['facts'][-1]['evidence'][0]['sha256']='0'*64
        result=self.build()
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['questions'],[])
        self.assertTrue(any(g['code']=='analysis_evidence_invalid' for g in result['plan_input']['gaps']))


if __name__=='__main__':unittest.main()
