"""Authored in-memory intake sources only; no Store, models, or equipment."""
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import unittest
from unittest.mock import patch

from labflow.intake_documents import _spans
from labflow.intake_jobs import _analysis_contract
from labflow.store import canonical


def H(value):
    return hashlib.sha256(value).hexdigest()


def fixture():
    text = 'product_type: test_radio\npurpose: engineering review\nmarket: EU\nfrequency: 2412 MHz\n'
    document = dict(path='request.txt', sha256=H(text.encode()), bytes=len(text.encode()),
                    text=text, parse_status='text', format='text', extraction_status='ok', issues=[])
    context_id = H(b'authored synthetic retained context')
    context = dict(job_id='J-TWIN-SYN', intake_id='I-TWIN-SYN', revision=1, synthetic=True,
        documents=[document], analysis_context_id=context_id,
        analysis_contract=_analysis_contract(dict(documents=[document], context_id=context_id)),
        instructions='Untrusted authored source. No operational authority.')
    def ref(line, role='request'):
        return dict(path=document['path'], sha256=document['sha256'], line_start=line, line_end=line,
                    quote=text.splitlines()[line-1], role=role)
    analysis = dict(schema_version=1, producer=dict(kind='fixture', name='AUTHORED-TWIN'), identity='single',
        facts=[dict(field=field, value=value, status='explicit', evidence=[ref(line)])
               for field, value, line in [('product_type','test_radio',1),('purpose','engineering review',2),('market','EU',3)]],
        missing_fields=[])
    settings = dict(frequency_hz=2412000000, power_dbm=-7.0, bandwidth_hz=20000000,
                    duty_cycle=0.5, modulation='OFDM', crest_factor_db=4.0)
    units = dict(frequency_hz='Hz', power_dbm='dBm', bandwidth_hz='Hz', duty_cycle='ratio',
                 modulation='label', crest_factor_db='dB')
    basis = {key:dict(kind='developer_declared_synthetic', value=value, unit=units[key], evidence=[])
             for key,value in settings.items()}
    method = dict(method_id='conducted_synthetic', method_version=1, metric='on', reference_plane='source_output')
    options = dict(expected_revision=1, expected_context_sha256=H(canonical(context).encode()),
                   source_settings=settings, basis=basis, method=method)
    return context, analysis, options


def pdf_source(context, analysis, options):
    document = dict(path='authored-report.pdf', sha256=H(b'authored PDF source identity'), bytes=100,
        format='pdf', text=None, parse_status='ok', extraction_id=H(b'authored normalized pages'),
        parser=dict(name='authored', version='1'), limits=dict(max_input_bytes=10000,max_pages=40,
        max_output_chars=10000,max_page_content_bytes=10000), issues=[], complete=True,total_pages=32,processed_pages=32,pages=[])
    for number in range(1,33):
        text = 'PASS; HT20; channel1; MCS6; frequency 2412 MHz\n' if number==32 else 'Authored synthetic page.\n'
        document['pages'].append(dict(page_number=number,status='ok',text=text,text_sha256=H(text.encode()),line_spans=_spans(text)))
    context['documents'].append(document)
    context['analysis_contract'] = _analysis_contract(dict(documents=context['documents'],context_id=context['analysis_context_id']))
    analysis.update(schema_version=2,context_id=context['analysis_context_id'])
    for fact in analysis['facts']:
        for ref in fact['evidence']:ref['kind']='text_line'
    page=document['pages'][-1]
    ref=dict(kind='pdf_page',path=document['path'],sha256=document['sha256'],extraction_id=document['extraction_id'],
             page_number=32,text_sha256=page['text_sha256'],line_start=1,line_end=1,quote=page['text'].strip(),role='reference')
    options['basis']['frequency_hz']=dict(kind='source_cited',value=2412,unit='MHz',evidence=[ref])
    options['expected_context_sha256']=H(canonical(context).encode())
    return ref


class ConductedTwinPlanTests(unittest.TestCase):
    def setUp(self):
        self.context,self.analysis,self.options=fixture()

    def module(self):
        name='labflow.intake_conducted_twin_plan'
        self.assertIsNotNone(importlib.util.find_spec(name),'pure conducted intake adapter is absent')
        return importlib.import_module(name)

    def build(self):
        return self.module().build_conducted_twin_plan_input(self.context,self.analysis,**self.options)

    def blocked(self, field=None):
        result=self.build();self.assertEqual(result['status'],'blocked')
        self.assertTrue(any(g['blocking'] for g in result['gaps']))
        if field:self.assertTrue(any(g['field']==field for g in result['gaps']),result['gaps'])
        self.assertIsNone(result['plan']['numeric_limit_dbm']);self.assertIsNone(result['plan']['uncertainty_db'])
        return result

    def test_complete_explicit_synthetic_input_is_ready(self):
        result=self.build()
        self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(set(result),{'schema_version','kind','status','binding','intake','plan','gaps','verification'})
        self.assertEqual(result['plan']['source_settings'],self.options['source_settings'])
        self.assertEqual(result['intake']['facts']['market']['value'],'EU')
        self.assertEqual(result['intake']['facts']['product_type']['value'],'test_radio')
        self.assertEqual(result['verification']['regulatory'],'not_assessed')
        self.assertIs(result['verification']['execution_authority'],False)

    def test_same_input_detached_deterministic_and_original_unchanged(self):
        original=copy.deepcopy((self.context,self.analysis,self.options));a=self.build();b=self.build()
        self.assertEqual(canonical(a),canonical(b));self.assertEqual((self.context,self.analysis,self.options),original)
        a['plan']['basis_refs']['frequency_hz']['value']=1
        a['intake']['source_facts'][0]['value']='mutated'
        self.assertEqual(self.build(),b)

    def test_genuine_parent_validators_are_really_called(self):
        m=self.module()
        with patch.object(m,'build_analysis_prompt',wraps=m.build_analysis_prompt) as prompt, \
                patch.object(m,'validate_analysis',wraps=m.validate_analysis) as validate, \
                patch.object(m,'project_analysis',wraps=m.project_analysis) as project:
            self.assertEqual(self.build()['status'],'ready_for_simulation')
        self.assertGreaterEqual(prompt.call_count,1);self.assertGreaterEqual(validate.call_count,1);self.assertEqual(project.call_count,1)

    def test_missing_each_source_setting_is_null_and_blocked_without_defaults(self):
        original=copy.deepcopy(self.options)
        for key in original['source_settings']:
            with self.subTest(key=key):
                self.options=copy.deepcopy(original);del self.options['source_settings'][key]
                result=self.blocked('source_settings.'+key);self.assertIsNone(result['plan']['source_settings'][key])

    def test_missing_each_basis_blocks(self):
        original=copy.deepcopy(self.options)
        for key in original['basis']:
            with self.subTest(key=key):
                self.options=copy.deepcopy(original);del self.options['basis'][key];self.blocked('basis.'+key)

    def test_all_missing_fields_are_preserved_and_followup_is_distinguished(self):
        self.analysis['missing_fields']=['antenna_gain','firmware','power_target']
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['intake']['missing_fields'],self.analysis['missing_fields'])
        self.assertEqual(result['intake']['follow_up_missing_fields'],self.analysis['missing_fields'])
        self.assertEqual(len([g for g in result['gaps'] if not g['blocking']]),3)

    def test_missing_product_purpose_and_market_block(self):
        original=copy.deepcopy(self.analysis)
        for field in ('product_type','purpose','market'):
            with self.subTest(field=field):
                self.analysis=copy.deepcopy(original);self.analysis['facts']=[f for f in self.analysis['facts'] if f['field']!=field]
                self.analysis['missing_fields']=[field];self.blocked('intake.'+field)

    def test_conflicting_request_facts_block(self):
        extra=copy.deepcopy(self.analysis['facts'][-1]);extra['value']='different market'
        self.analysis['facts'].append(extra);self.blocked('intake.market')

    def test_ambiguous_identity_blocks(self):
        self.analysis['identity']='ambiguous';self.blocked('intake.identity')

    def test_report_reference_is_not_request_purpose_or_market(self):
        ref=pdf_source(self.context,self.analysis,self.options)
        for fact in self.analysis['facts']:
            if fact['field'] in ('purpose','market'):fact['evidence']=[copy.deepcopy(ref)]
        result=self.blocked();self.assertNotIn('purpose',result['intake']['facts']);self.assertNotIn('market',result['intake']['facts'])

    def test_explicit_purpose_value_must_appear_in_quote(self):
        self.analysis['facts'][1]['value']='certification';self.blocked('intake.purpose')

    def test_caller_approved_status_does_not_authorize(self):
        self.analysis['status']='approved';self.blocked('analysis')

    def test_bad_analysis_SHA_quote_or_line_blocks(self):
        original=copy.deepcopy(self.analysis)
        for key,value in [('sha256','0'*64),('quote','not in source'),('line_end',999)]:
            with self.subTest(key=key):
                self.analysis=copy.deepcopy(original);self.analysis['facts'][0]['evidence'][0][key]=value;self.blocked('analysis')

    def test_revision_and_context_hash_changes_block(self):
        self.options['expected_revision']=2;self.blocked('binding.revision')
        self.options['expected_revision']=1;self.options['expected_context_sha256']='0'*64;self.blocked('binding.context_sha256')

    def test_matching_pins_still_do_not_claim_DB_current(self):
        result=self.build();self.assertEqual(result['verification']['current_version'],'caller_snapshot_only')
        self.assertEqual(result['verification']['source_bytes'],'not_reopened')

    def test_source_cited_MHz_value_is_verified_not_injected(self):
        doc=self.context['documents'][0]
        ref=dict(path=doc['path'],sha256=doc['sha256'],line_start=4,line_end=4,quote='frequency: 2412 MHz',role='reference')
        self.options['basis']['frequency_hz']=dict(kind='source_cited',value=2412,unit='MHz',evidence=[ref])
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan']['basis_refs']['frequency_hz']['kind'],'source_cited')
        self.assertEqual(result['plan']['source_settings']['frequency_hz'],2412000000)

    def test_bad_basis_SHA_quote_and_numeric_association_block(self):
        doc=self.context['documents'][0];ref=dict(path=doc['path'],sha256=doc['sha256'],line_start=4,line_end=4,quote='frequency: 2412 MHz',role='reference')
        good=dict(kind='source_cited',value=2412,unit='MHz',evidence=[ref])
        for key,value in [('sha256','0'*64),('quote','wrong quote')]:
            with self.subTest(key=key):
                basis=copy.deepcopy(good);basis['evidence'][0][key]=value;self.options['basis']['frequency_hz']=basis;self.blocked('basis.frequency_hz')
        self.options['basis']['frequency_hz']={**good,'value':2413};self.options['source_settings']['frequency_hz']=2413000000
        self.blocked('basis.frequency_hz')

    def test_synthetic_pdf_page32_is_bound_and_PASS_is_not_a_verdict(self):
        pdf_source(self.context,self.analysis,self.options)
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan']['basis_refs']['frequency_hz']['evidence'][0]['page_number'],32)
        self.assertEqual(result['plan']['assessment'],'not_assessed');self.assertIsNone(result['plan']['numeric_limit_dbm'])

    def test_pdf_page_hash_extraction_or_number_mismatch_blocks(self):
        pdf_source(self.context,self.analysis,self.options);original=copy.deepcopy(self.options['basis']['frequency_hz'])
        for key,value in [('text_sha256','0'*64),('extraction_id','0'*64),('page_number',99),('line_start',2)]:
            with self.subTest(key=key):
                self.options['basis']['frequency_hz']=copy.deepcopy(original);self.options['basis']['frequency_hz']['evidence'][0][key]=value
                self.blocked('basis.frequency_hz')

    def test_analysis_context_id_mismatch_blocks(self):
        pdf_source(self.context,self.analysis,self.options);self.analysis['context_id']='0'*64;self.blocked('analysis')

    def test_numeric_type_range_and_nonfinite_misuse_blocks(self):
        original=copy.deepcopy(self.options)
        for key,value in [('frequency_hz',True),('frequency_hz','2412 MHz'),('power_dbm',float('inf')),
                          ('bandwidth_hz',0),('duty_cycle',0),('duty_cycle',1.1),('crest_factor_db',-1),('power_dbm',float('nan'))]:
            with self.subTest(key=key,value=str(value)):
                self.options=copy.deepcopy(original);self.options['source_settings'][key]=value;self.blocked()

    def test_wrong_unit_extra_key_empty_modulation_and_basis_kind_block(self):
        self.options['basis']['power_dbm']['unit']='W';self.blocked('basis.power_dbm')
        self.options=fixture()[2];self.options['source_settings']['frequency_mhz']=2412;self.blocked('source_settings.frequency_mhz')
        self.options=fixture()[2];self.options['source_settings']['modulation']='';self.blocked('source_settings.modulation')
        self.options=fixture()[2];self.options['basis']['power_dbm']['kind']='approved';self.blocked('basis.power_dbm')

    def test_unsupported_method_version_metric_and_plane_do_not_fallback(self):
        original=copy.deepcopy(self.options)
        for key,value in [('method_id','FCC-15.247-approved'),('method_version',2),('metric','regulatory_PASS'),('reference_plane','antenna_far_field')]:
            with self.subTest(key=key):
                self.options=copy.deepcopy(original);self.options['method'][key]=value;self.blocked('method.'+key)

    def test_on_time_peak_are_explicit_and_no_metric_is_defaulted(self):
        for metric in ('on','time','peak'):
            self.options['method']['metric']=metric;self.assertEqual(self.build()['plan']['metric'],metric)
        del self.options['method']['metric'];result=self.blocked('method.metric');self.assertIsNone(result['plan']['metric'])

    def test_bool_version_and_unknown_method_key_block(self):
        self.options['method']['method_version']=True;self.blocked('method.method_version')
        self.options['method']['method_version']=1;self.options['method']['approved']=True;self.blocked('method.approved')

    def test_pure_runtime_does_not_open_Store_DB_or_files(self):
        with patch('sqlite3.connect',side_effect=AssertionError('DB forbidden')), \
                patch('builtins.open',side_effect=AssertionError('file forbidden')):
            self.assertEqual(self.build()['status'],'ready_for_simulation')

    def test_observed_controls_are_not_converted_to_ready_or_blocked(self):
        m=self.module()
        for kind in (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):
            control=kind('control')
            with self.subTest(kind=kind.__name__),patch.object(m,'validate_analysis',side_effect=control):
                with self.assertRaises(kind) as caught:self.build()
                self.assertIs(caught.exception,control)

    def test_existing_rf_domain_rejects_negative_lower_edge_and_overflow(self):
        original=copy.deepcopy(self.options)
        for frequency,bandwidth in [(1,3),(1.7e308,1.7e308)]:
            self.options=copy.deepcopy(original)
            for key,value in [('frequency_hz',frequency),('bandwidth_hz',bandwidth)]:
                self.options['source_settings'][key]=value;self.options['basis'][key]['value']=value
            self.blocked('source_settings')

    def test_nonempty_modulation_text_is_preserved_without_invented_enum(self):
        self.options['source_settings']['modulation']='CUSTOM-IQ'
        self.options['basis']['modulation']['value']='CUSTOM-IQ'
        result=self.build();self.assertEqual(result['status'],'ready_for_simulation')
        self.assertEqual(result['plan']['source_settings']['modulation'],'CUSTOM-IQ')

    def power_evidence(self, label):
        doc=self.context['documents'][0];line=label+': -7 dBm'
        doc['text']+=line+'\n';doc['bytes']=len(doc['text'].encode());doc['sha256']=H(doc['text'].encode())
        for fact in self.analysis['facts']:
            for ref in fact['evidence']:ref['sha256']=doc['sha256']
        self.options['expected_context_sha256']=H(canonical(self.context).encode())
        ref=dict(path=doc['path'],sha256=doc['sha256'],line_start=5,line_end=5,quote=line,role='reference')
        self.options['basis']['power_dbm']=dict(kind='source_cited',value=-7,unit='dBm',evidence=[ref])

    def test_report_peak_does_not_become_synthetic_on_average_power(self):
        self.power_evidence('report_peak');self.blocked('basis.power_dbm')

    def test_explicit_source_cited_on_average_power_can_be_used(self):
        self.power_evidence('on_average_power');self.assertEqual(self.build()['status'],'ready_for_simulation')

    def test_real_synthetic_intake_completion_connects_to_plan_without_consuming_job(self):
        from pathlib import Path
        import tempfile
        from labflow.active_intake import register_source,scan_source,intake_status
        from labflow.intake_jobs import claim_job,complete_job
        from labflow.store import Store
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'inbox'/'one';bundle.mkdir(parents=True)
            (bundle/'request.txt').write_bytes(self.context['documents'][0]['text'].encode('utf-8'))
            store=Store(root/'state')
            try:
                register_source(store,'AUTHORED-TWIN',bundle.parent,synthetic=True,settle_seconds=1)
                scan_source(store,'AUTHORED-TWIN',now=100,synthetic_only=True)
                scan_source(store,'AUTHORED-TWIN',now=101,synthetic_only=True)
                claimed=claim_job(store,'authored-fixture-worker',synthetic_only=True)
                context={key:claimed[key] for key in self.context}
                complete_job(store,claimed['job_id'],claimed['token'],self.analysis)
                saved=intake_status(store,context['intake_id'])['analysis']['submitted']
                self.options['expected_context_sha256']=H(canonical(context).encode())
                result=self.module().build_conducted_twin_plan_input(context,saved,**self.options)
                self.assertEqual(result['status'],'ready_for_simulation')
                self.assertEqual(result['binding']['analysis_context_id'],claimed['analysis_context_id'])
                self.assertEqual(result['intake']['source_facts'],saved['facts'])
                with store.connection() as con:
                    job=con.execute('SELECT state,attempt FROM intake_jobs WHERE job_id=?',(claimed['job_id'],)).fetchone()
                self.assertEqual(tuple(job),('completed',1))
            finally:
                store.close()

    def test_unverified_basis_holds_back_only_its_setting_and_preserves_provided_value(self):
        original=copy.deepcopy(self.options)
        for key,value in original['source_settings'].items():
            with self.subTest(key=key):
                self.options=copy.deepcopy(original);self.options['basis'][key]=None
                result=self.blocked('basis.'+key)
                self.assertIsNone(result['plan']['basis_refs'][key])
                self.assertIsNone(result['plan']['source_settings'][key])
                self.assertTrue(any(g['field']=='basis.'+key and g['provided']==value for g in result['gaps']))
                for other,provided in original['source_settings'].items():
                    if other!=key:self.assertEqual(result['plan']['source_settings'][other],provided)

    def test_rejected_basis_variants_never_leave_an_execution_value(self):
        original=copy.deepcopy(self.options)
        doc=self.context['documents'][0]
        good=dict(kind='source_cited',value=2412,unit='MHz',evidence=[dict(path=doc['path'],sha256=doc['sha256'],
            line_start=4,line_end=4,quote='frequency: 2412 MHz',role='reference')])
        invalid_refs=[]
        for field,value in [('sha256','0'*64),('line_end',999),('quote','not in source')]:
            item=copy.deepcopy(good);item['evidence'][0][field]=value;invalid_refs.append(item)
        wrong_quote_quantity=copy.deepcopy(good);wrong_quote_quantity.update(value=2412000000,unit='Hz')
        cases=[None,{},dict(kind='approved',value=2412,unit='MHz',evidence=[]),
               dict(kind='developer_declared_synthetic',value=2413,unit='MHz',evidence=[]),
               dict(kind='developer_declared_synthetic',value=2412,unit='wrong',evidence=[]),wrong_quote_quantity,*invalid_refs]
        for item in cases:
            with self.subTest(item=item):
                self.options=copy.deepcopy(original);self.options['basis']['frequency_hz']=item
                result=self.blocked('basis.frequency_hz')
                self.assertIsNone(result['plan']['source_settings']['frequency_hz'])
                self.assertIsNone(result['plan']['basis_refs']['frequency_hz'])
                self.assertTrue(any(g['field']=='basis.frequency_hz' and g['provided']==2412000000 for g in result['gaps']))
        self.options=copy.deepcopy(original);self.options['basis']=None
        result=self.blocked('basis');self.assertTrue(all(v is None for v in result['plan']['source_settings'].values()))
        self.assertTrue(any(g['field']=='basis' and g['provided']==original['source_settings'] for g in result['gaps']))


if __name__=='__main__':
    unittest.main()
