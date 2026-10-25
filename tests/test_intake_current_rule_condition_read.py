"""New authored synthetic current Store/condition examples; no private rules."""
import copy
from contextlib import ExitStack,redirect_stderr,redirect_stdout
import hashlib
import importlib
import importlib.util
import inspect
from io import StringIO
import os
from pathlib import Path
import tempfile
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from labflow.active_intake import register_source,scan_source
from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts
from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.intake_jobs import claim_job,complete_job
from labflow.intake_rule_condition_gate import evaluate_intake_rule_conditions
from labflow.intake_worker import SyntheticTextProvider
from labflow.store import Store,canonical
from labflow.ui_read_model import IntakeReadModel,ReadModelError
from test_intake_current_facts_plan import authored_pdf,METHOD


CONTEXT_FIELDS=('current_validity_approved','case_applicability_approved','metric_method_approved',
    'reference_plane_verified','correction_ledger_verified','conditional_limit_resolved',
    'uncertainty_decision_rule_approved','independent_holdout_available')
RF='frequency_hz: 913000000 Hz; on_average_power: -17 dBm; bandwidth_hz: 175000 Hz; duty_cycle: 30 %; modulation: LAB-ASK; crest_factor: 3.5 dB'


def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def authored_fixture(root,*,kind='text',duty='30 %',level=23):
    root=Path(root);folder=root/'inbox'/'authored';folder.mkdir(parents=True)
    values=dict(level=(level,'mV'))
    values.update({name:(True,'boolean') for name in CONTEXT_FIELDS})
    quotes={name:canonical(dict(field=name,value=value,unit=unit)) for name,(value,unit) in values.items()}
    text='product_type: lab_receiver\nmarket: US\npurpose: development\nfeatures: '+RF.replace('30 %',duty)+'\n'
    text+='\n'.join(quotes.values())+'\n'
    source=folder/('request.pdf' if kind=='pdf' else 'request.txt')
    source.write_bytes(authored_pdf(text) if kind=='pdf' else text.encode('utf-8'))
    store=Store(root/'state')
    try:
        register_source(store,'CURRENT-CONDITION-AUTHORED',root/'inbox',synthetic=True,settle_seconds=.001)
        scan_source(store,'CURRENT-CONDITION-AUTHORED',now=100)
        intake_id=scan_source(store,'CURRENT-CONDITION-AUTHORED',now=100.01)['accepted'][0]['intake_id']
        job=claim_job(store,'current-condition-fixture',now=101)
        context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
        analysis=SyntheticTextProvider().analyze(context)
        complete_job(store,job['job_id'],job['token'],analysis,now=102)
        raw_source=store.blob_path(context['documents'][0]['sha256'])
    finally:store.close()
    return dict(root=root,workspace=store.root,intake_id=intake_id,context=context,analysis=analysis,
        source=source,raw_source=raw_source,values=values,quotes=quotes)


def arguments(fixture,*,threshold=20):
    document=fixture['context']['documents'][0];entries={}
    for name,(value,unit) in fixture['values'].items():
        quote=fixture['quotes'][name]
        if document.get('format')=='pdf':
            page=document['pages'][0];text=page['text']
        else:text=document['text']
        line=next(i for i,line in enumerate(text.splitlines(),1) if quote in line)
        ref=dict(path=document['path'],sha256=document['sha256'],line_start=line,line_end=line,quote=quote,role='product')
        if fixture['analysis']['schema_version']==2:
            ref['kind']='pdf_page' if document.get('format')=='pdf' else 'text_line'
            if ref['kind']=='pdf_page':ref.update(extraction_id=document['extraction_id'],
                page_number=page['page_number'],text_sha256=page['text_sha256'])
        entries[name]=dict(value=value,unit=unit,status='explicit',evidence=[ref])
    payload=dict(rule_id='authored-current-level',declared_predicate=dict(operator='gte',input='level',value=threshold),
        input_types=dict(level='number'),units=dict(level='mV'))
    text=canonical(dict(rules=[payload]));sha=hashlib.sha256(text.encode('utf-8')).hexdigest()
    rule=dict(payload,source_ref=dict(source_id='authored-current-rule-text',sha256=sha,rule_index=0))
    return dict(method=copy.deepcopy(METHOD),rules=[rule],rule_sources=[dict(source_id='authored-current-rule-text',text=text,sha256=sha)],
        inputs=dict(level=entries['level']),execution_context={name:entries[name] for name in CONTEXT_FIELDS})


def files(root):
    result={}
    for path in Path(root).rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:raw=stream.read();info=os.fstat(stream.fileno())
            result[path.relative_to(root).as_posix()]=(hashlib.sha256(raw).hexdigest(),info.st_size,info.st_ino,
                info.st_nlink,info.st_mtime_ns,info.st_ctime_ns,getattr(info,'st_file_attributes',None))
    return result


def caller_values():
    from test_intake_rule_condition_gate import fixture
    wrapper,current,args=fixture()
    native=dict(context=args['context'],analysis=args['analysis'],facts_plan=wrapper)
    options={key:args[key] for key in ('rules','rule_sources','inputs','execution_context')}
    options['method']={key:current['plan'][key] for key in ('method_id','method_version','metric','reference_plane')}
    gate=evaluate_intake_rule_conditions(wrapper,current,**args)
    return native,options,gate


def advance(fixture):
    # A disposable external writer injected between review and post-read.
    fixture['source'].write_bytes(fixture['source'].read_bytes().replace(b'"value":23',b'"value":25'))
    store=Store(fixture['workspace'])
    try:
        scan_source(store,'CURRENT-CONDITION-AUTHORED',now=200)
        accepted=scan_source(store,'CURRENT-CONDITION-AUTHORED',now=200.01)['accepted']
        assert accepted and accepted[0]['revision']==2
        job=claim_job(store,'authored-concurrent-revision',now=201)
        context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
        complete_job(store,job['job_id'],job['token'],SyntheticTextProvider().analyze(context),now=202)
    finally:store.close()


class CurrentRuleConditionReadTests(unittest.TestCase):
    maxDiff=None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='current-condition-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def api(self):
        name='labflow.intake_current_rule_condition_read'
        self.assertIsNotNone(importlib.util.find_spec(name),'assigned current condition read is absent')
        return importlib.import_module(name).read_current_rule_conditions

    def check(self,result):
        self.assertEqual(set(result),{'status','context','analysis','facts_plan','rule_conditions','current_relation'})
        gate=result['rule_conditions'];relation=result['current_relation']
        self.assertEqual(set(gate),{'schema_version','kind','status','binding','rule_results','gaps','questions','snapshots','normative_verdict','verification'})
        self.assertIsNone(gate['normative_verdict'])
        for field in ('execution_authority','worker_generation_authority','physical_permission'):
            self.assertIs(gate['verification'][field],False)
        self.assertEqual(gate['verification']['current_version'],'caller_snapshot_only')
        self.assertEqual(set(relation),{'status','before','after','questions'})
        for key in ('before','after'):
            self.assertEqual(set(relation[key]),{'revision','context_sha256','analysis_sha256'})
        self.assertIs(result['facts_plan']['plan_input']['verification']['execution_authority'],False)

    def test_genuine_txt_one_facts_one_gate_then_current_postread_preserves_original_objects(self):
        api=self.api();module=importlib.import_module(api.__module__)
        fixture=authored_fixture(self.root/'txt');options=arguments(fixture);unchanged=copy.deepcopy(options)
        before=files(fixture['root']);captured=[]
        def first(*args,**kwargs):
            value=read_current_conducted_plan_from_facts(*args,**kwargs);captured.append(value);return value
        reader=IntakeReadModel.current_conducted_plan_context
        with patch.object(module,'read_current_conducted_plan_from_facts',side_effect=first) as facts,\
             patch.object(module,'evaluate_intake_rule_conditions',wraps=evaluate_intake_rule_conditions) as gate,\
             patch.object(IntakeReadModel,'current_conducted_plan_context',autospec=True,side_effect=reader) as current:
            result=api(fixture['workspace'],fixture['intake_id'],**options)
        self.assertEqual(facts.call_count,1);self.assertEqual(gate.call_count,1);self.assertEqual(current.call_count,2)
        self.assertEqual(list(inspect.signature(api).parameters),['workspace','intake_id','method','rules','rule_sources',
            'inputs','execution_context','expected_revision','expected_context_sha256'])
        self.check(result);self.assertEqual(result['status'],'REVIEW_RULE_BRANCH')
        for key in ('context','analysis','facts_plan'):self.assertIs(result[key],captured[0][key])
        expected=evaluate_intake_rule_conditions(result['facts_plan'],result['facts_plan']['plan_input'],
            context=result['context'],analysis=result['analysis'],expected_revision=result['context']['revision'],
            expected_context_sha256=digest(result['context']),**{key:options[key] for key in ('rules','rule_sources','inputs','execution_context')})
        self.assertEqual(result['rule_conditions'],expected)
        self.assertEqual(result['current_relation'],dict(status='same_current_snapshot',before=dict(revision=1,
            context_sha256=digest(result['context']),analysis_sha256=digest(result['analysis'])),
            after=dict(revision=1,context_sha256=digest(result['context']),analysis_sha256=digest(result['analysis'])),questions=[]))
        self.assertEqual(result['facts_plan']['status'],'ready_for_simulation')
        self.assertEqual(options,unchanged);self.assertEqual(files(fixture['root']),before)

    def test_genuine_pdf_false_predicate_keeps_original_schema2_and_not_selected_without_authority(self):
        api=self.api();fixture=authored_fixture(self.root/'pdf',kind='pdf');options=arguments(fixture,threshold=24)
        before=files(fixture['root']);result=api(fixture['workspace'],fixture['intake_id'],**options)
        self.check(result);self.assertEqual(result['status'],'NOT_SELECTED')
        self.assertEqual(result['rule_conditions']['status'],'NOT_SELECTED')
        self.assertIs(result['rule_conditions']['rule_results'][0]['predicate_value'],False)
        self.assertEqual(result['analysis']['schema_version'],2);self.assertEqual(result['analysis'],fixture['analysis'])
        self.assertEqual(result['current_relation']['status'],'same_current_snapshot')
        self.assertEqual(files(fixture['root']),before)

    def test_genuine_completed_revision_drift_holds_compound_and_retains_original_selected_gate(self):
        api=self.api();module=importlib.import_module(api.__module__)
        fixture=authored_fixture(self.root/'drift');options=arguments(fixture);reviews=[]
        def review(*args,**kwargs):
            value=evaluate_intake_rule_conditions(*args,**kwargs);reviews.append(value);advance(fixture);return value
        with patch.object(module,'evaluate_intake_rule_conditions',side_effect=review) as gate:
            result=api(fixture['workspace'],fixture['intake_id'],**options)
        self.check(result);self.assertEqual(gate.call_count,1)
        self.assertEqual(result['status'],'HOLD');self.assertIs(result['rule_conditions'],reviews[0])
        self.assertEqual(result['rule_conditions']['status'],'REVIEW_RULE_BRANCH')
        self.assertEqual(result['context']['revision'],1)
        relation=result['current_relation'];self.assertEqual(relation['status'],'current_snapshot_changed')
        self.assertEqual(relation['before']['revision'],1);self.assertEqual(relation['after']['revision'],2)
        self.assertNotEqual(relation['before']['context_sha256'],relation['after']['context_sha256'])
        self.assertNotEqual(relation['before']['analysis_sha256'],relation['after']['analysis_sha256'])
        self.assertEqual([q['field'] for q in relation['questions']],['current_relation'])

    def test_genuine_postread_retained_source_mismatch_propagates_original_error_without_a_compound(self):
        api=self.api();module=importlib.import_module(api.__module__)
        fixture=authored_fixture(self.root/'changed');options=arguments(fixture);errors=[]
        current=IntakeReadModel.current_conducted_plan_context
        def read(model,intake_id):
            try:return current(model,intake_id)
            except BaseException as error:errors.append(error);raise
        def review(*args,**kwargs):
            value=evaluate_intake_rule_conditions(*args,**kwargs)
            fixture['raw_source'].write_bytes(fixture['raw_source'].read_bytes()+b'authored retained source mismatch\n')
            return value
        with patch.object(module,'evaluate_intake_rule_conditions',side_effect=review),\
             patch.object(IntakeReadModel,'current_conducted_plan_context',autospec=True,side_effect=read):
            with self.assertRaises(ReadModelError) as caught:api(fixture['workspace'],fixture['intake_id'],**options)
        self.assertEqual(len(errors),1);self.assertIs(caught.exception,errors[0])
        self.assertEqual(caught.exception.code,'intake_conducted_preview_source_invalid')

    def test_genuine_blocked_rf_plan_keeps_missing_unit_null_questions_beside_separate_rule_review(self):
        api=self.api();fixture=authored_fixture(self.root/'blocked',duty='30');options=arguments(fixture)
        before=files(fixture['root']);result=api(fixture['workspace'],fixture['intake_id'],**options)
        self.check(result);self.assertEqual(result['facts_plan']['status'],'blocked')
        self.assertEqual(result['rule_conditions']['status'],'REVIEW_RULE_BRANCH')
        self.assertEqual(result['status'],'REVIEW_RULE_BRANCH')
        plan=result['facts_plan']['plan_input']['plan']
        self.assertIsNone(plan['source_settings']['duty_cycle']);self.assertIsNone(plan['basis_refs']['duty_cycle'])
        self.assertIsNone(plan['numeric_limit_dbm']);self.assertIsNone(plan['uncertainty_db'])
        self.assertEqual([q['reason'] for q in result['facts_plan']['questions']],['source_unit_missing'])
        self.assertEqual(result['rule_conditions']['snapshots']['intake_plan'],result['facts_plan'])
        self.assertEqual(result['analysis'],fixture['analysis']);self.assertNotIn('context_id',result['analysis'])
        self.assertEqual(files(fixture['root']),before)

    def test_genuine_expected_pin_and_method_gaps_are_delegated_without_replacement(self):
        api=self.api();fixture=authored_fixture(self.root/'pins');base=arguments(fixture);before=files(fixture['root'])
        for pins in (dict(expected_revision=2),dict(expected_revision=True),dict(expected_context_sha256='f'*64),
                     dict(method=dict(METHOD,metric='unsupported-authored'))):
            with self.subTest(pins=pins):
                options=copy.deepcopy(base);options.update(pins)
                result=api(fixture['workspace'],fixture['intake_id'],**options);self.check(result)
                self.assertEqual(result['status'],'HOLD');self.assertEqual(result['facts_plan']['status'],'blocked')
                self.assertTrue(result['facts_plan']['plan_input']['gaps'])
                expected=build_conducted_plan_from_intake_facts(result['context'],result['analysis'],method=options['method'],
                    expected_revision=options.get('expected_revision',result['context']['revision']),
                    expected_context_sha256=options.get('expected_context_sha256',digest(result['context'])))
                self.assertEqual(result['facts_plan'],expected)
                self.assertEqual(result['current_relation']['status'],'same_current_snapshot')
                snapshots=result['rule_conditions']['snapshots']
                if 'expected_revision' in pins:self.assertEqual(snapshots['expected_revision'],pins['expected_revision'])
                if 'expected_context_sha256' in pins:self.assertEqual(snapshots['expected_context_sha256'],pins['expected_context_sha256'])
                self.assertEqual(snapshots['intake_plan'],result['facts_plan'])
        self.assertEqual(files(fixture['root']),before)

    def test_genuine_missing_units_bare_approvals_and_source_ast_mismatch_remain_gate_holds(self):
        api=self.api();fixture=authored_fixture(self.root/'gaps');base=arguments(fixture);before=files(fixture['root'])
        for change in ('missing','unit','approval','source','operator'):
            with self.subTest(change=change):
                options=copy.deepcopy(base)
                if change=='missing':options['inputs']['level']=None
                elif change=='unit':options['inputs']['level']['unit']='V'
                elif change=='approval':options['execution_context']={name:True for name in CONTEXT_FIELDS}
                elif change=='source':options['rule_sources'][0]['sha256']='0'*64
                else:
                    options['rules'][0]['declared_predicate']['operator']='lt'
                    payload={key:options['rules'][0][key] for key in ('rule_id','declared_predicate','input_types','units')}
                    text=canonical(dict(rules=[payload]));sha=hashlib.sha256(text.encode('utf-8')).hexdigest()
                    options['rule_sources'][0].update(text=text,sha256=sha);options['rules'][0]['source_ref']['sha256']=sha
                original=copy.deepcopy(options);result=api(fixture['workspace'],fixture['intake_id'],**options)
                self.check(result);self.assertEqual(result['status'],'HOLD');self.assertTrue(result['rule_conditions']['questions'])
                self.assertEqual(result['current_relation']['status'],'same_current_snapshot')
                self.assertEqual(options,original);self.assertEqual(result['facts_plan']['status'],'ready_for_simulation')
        self.assertEqual(files(fixture['root']),before)

    def test_first_gate_and_postread_errors_and_controls_propagate_identity_without_output(self):
        api=self.api();module=importlib.import_module(api.__module__)
        class Stop(BaseException):pass
        for phase in ('first','gate','post'):
            for error in (ReadModelError('PRIVATE-CURRENT-ERROR'),RuntimeError('private-runtime'),KeyboardInterrupt('first-control'),
                          MemoryError('first-memory'),SystemExit(73),GeneratorExit('first-generator'),Stop('custom-control')):
                with self.subTest(phase=phase,error=type(error).__name__):
                    native,options,gate=caller_values();output,stderr=StringIO(),StringIO()
                    model=SimpleNamespace(current_conducted_plan_context=Mock(return_value={key:native[key] for key in ('context','analysis')}))
                    first=Mock(return_value=native);review=Mock(return_value=gate)
                    if phase=='first':first.side_effect=error
                    elif phase=='gate':review.side_effect=error
                    else:model.current_conducted_plan_context.side_effect=error
                    with redirect_stdout(output),redirect_stderr(stderr),\
                         patch.object(module,'read_current_conducted_plan_from_facts',first),\
                         patch.object(module,'evaluate_intake_rule_conditions',review),patch.object(module,'IntakeReadModel',return_value=model):
                        with self.assertRaises(type(error)) as caught:api('unused-boundary','authored',**options)
                    self.assertIs(caught.exception,error);self.assertEqual((output.getvalue(),stderr.getvalue()),('',''))
                    self.assertEqual(first.call_count,1);self.assertEqual(review.call_count,0 if phase=='first' else 1)
                    self.assertEqual(model.current_conducted_plan_context.call_count,1 if phase=='post' else 0)

    def test_postread_analysis_or_context_drift_is_separate_from_unchanged_parent_gate_dto(self):
        api=self.api();module=importlib.import_module(api.__module__)
        for change in ('analysis','context'):
            with self.subTest(change=change):
                native,options,gate=caller_values();post=copy.deepcopy({key:native[key] for key in ('context','analysis')})
                if change=='analysis':post['analysis']['producer']['name']='authored-later-analysis'
                else:post['context']['instructions']='authored-later-context'
                model=SimpleNamespace(current_conducted_plan_context=Mock(return_value=post))
                with patch.object(module,'read_current_conducted_plan_from_facts',return_value=native),\
                     patch.object(module,'evaluate_intake_rule_conditions',return_value=gate),patch.object(module,'IntakeReadModel',return_value=model):
                    result=api('unused-boundary','authored',**options)
                self.check(result);self.assertEqual(result['status'],'HOLD');self.assertIs(result['rule_conditions'],gate)
                self.assertEqual(gate['status'],'REVIEW_RULE_BRANCH')
                relation=result['current_relation'];self.assertEqual(relation['before']['revision'],relation['after']['revision'])
                key=change+'_sha256';self.assertNotEqual(relation['before'][key],relation['after'][key])

    def test_native_result_guards_and_compound_cap_have_only_fixed_local_error_codes(self):
        api=self.api();module=importlib.import_module(api.__module__)
        self.assertEqual(module._BYTES,16777216)
        for bad in (None,{'PRIVATE-RESULT':'private-path'}, {'context':{'revision':True},'analysis':{},'facts_plan':{}},
                    {'context':{'revision':1,'text':'\ud800'},'analysis':{},'facts_plan':{}}):
            native,options,gate=caller_values()
            with patch.object(module,'read_current_conducted_plan_from_facts',return_value=bad):
                with self.assertRaises(ReadModelError) as caught:api('unused-boundary','authored',**options)
            self.assertEqual(caught.exception.code,'intake_current_rule_condition_read_result_invalid')
            self.assertEqual(str(caught.exception),caught.exception.code)
        native,options,gate=caller_values();post={key:native[key] for key in ('context','analysis')}
        limit=max(len(canonical(value).encode('utf-8')) for value in (native,gate,post))+64
        model=SimpleNamespace(current_conducted_plan_context=Mock(return_value=post))
        with patch.object(module,'_BYTES',limit),patch.object(module,'read_current_conducted_plan_from_facts',return_value=native),\
             patch.object(module,'evaluate_intake_rule_conditions',return_value=gate),patch.object(module,'IntakeReadModel',return_value=model):
            with self.assertRaises(ReadModelError) as caught:api('unused-boundary','authored',**options)
        self.assertEqual(model.current_conducted_plan_context.call_count,1)
        self.assertEqual(caught.exception.code,'intake_current_rule_condition_read_result_limit')

        for part in ('gate','post'):
            native,options,gate=caller_values();post={key:native[key] for key in ('context','analysis')}
            if part=='gate':gate['verification']['execution_authority']=True
            else:post['context']={'revision':False}
            with patch.object(module,'read_current_conducted_plan_from_facts',return_value=native),\
                 patch.object(module,'evaluate_intake_rule_conditions',return_value=gate),\
                 patch.object(module,'IntakeReadModel',return_value=SimpleNamespace(current_conducted_plan_context=Mock(return_value=post))):
                with self.assertRaises(ReadModelError) as caught:api('unused-boundary','authored',**options)
            self.assertEqual(caught.exception.code,'intake_current_rule_condition_read_result_invalid')

    def test_runtime_uses_two_current_reads_and_closes_known_query_only_sql_native_bindings_without_services(self):
        api=self.api();fixture=authored_fixture(self.root/'readonly');options=arguments(fixture);before=files(fixture['root'])
        from labflow.store import _ExistingBinding
        connect=sqlite3.connect;acquire=_ExistingBinding.acquire;connections=[];bindings=[];statements=[];connect_args=[]
        def observe_connect(*args,**kwargs):
            con=connect(*args,**kwargs);con.set_trace_callback(statements.append);connections.append(con);connect_args.append((args,kwargs));return con
        def observe_acquire(binding):
            try:return acquire(binding)
            finally:bindings.append(binding)
        def forbidden(*args,**kwargs):raise AssertionError('current condition read entered a write/model/network service')
        with ExitStack() as stack:
            for target in ('labflow.store.Store.__init__','labflow.store.Store.connection','labflow.store.Store.write_blob',
                'labflow.store.Store.register_blob','labflow.store.Store.event','labflow.intake_jobs.claim_job',
                'labflow.intake_jobs.complete_job','labflow.intake_jobs.respond','labflow.active_intake.scan_source',
                'labflow.intake_documents.prepare_analysis_documents','labflow.intake_documents._retain',
                'labflow.intake_worker.run_worker','labflow.intake_worker.SyntheticTextProvider.analyze',
                'labflow.document_extract.extract_document','labflow.intake_documents.extract_document','subprocess.Popen','socket.socket'):
                stack.enter_context(patch(target,side_effect=forbidden))
            stack.enter_context(patch.object(sqlite3,'connect',side_effect=observe_connect))
            stack.enter_context(patch.object(_ExistingBinding,'acquire',observe_acquire))
            result=api(fixture['workspace'],fixture['intake_id'],**options)
        self.assertEqual(result['status'],'REVIEW_RULE_BRANCH');self.assertEqual(files(fixture['root']),before)
        self.assertEqual(len(bindings),2);self.assertTrue(connections)
        self.assertTrue(all('?mode=ro' in args[0] and kwargs.get('uri') is True for args,kwargs in connect_args))
        writes={'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP','REPLACE','VACUUM','ATTACH','DETACH','REINDEX'}
        self.assertTrue(all(sql.strip().split()[0].upper() not in writes for sql in statements))
        self.assertEqual(sum(sql.strip().upper()=='PRAGMA QUERY_ONLY=ON' for sql in statements),len(connections))
        for con in connections:
            with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')
        self.assertTrue(all(binding.state=='closed' and binding.active==0 and not binding.handles for binding in bindings))

    def test_genuine_postread_first_control_and_close_only_failure_return_no_current_compound(self):
        api=self.api()
        from labflow.store import _ExistingBinding
        from labflow import ui_read_model
        for primary in (True,False):
            with self.subTest(primary=primary):
                fixture=authored_fixture(self.root/('primary' if primary else 'close'));options=arguments(fixture)
                before=files(fixture['root']);original_close=_ExistingBinding.close;original_manifest=ui_read_model._current_text_manifest
                first=KeyboardInterrupt('postread-primary');late=SystemExit('later-close') if primary else MemoryError('close-only')
                bindings=[];calls=[]
                def manifest(*args,**kwargs):
                    calls.append(True)
                    if len(calls)==2 and primary:raise first
                    return original_manifest(*args,**kwargs)
                def close(binding):
                    original_close(binding);bindings.append(binding)
                    if len(bindings)==2:raise late
                with patch.object(ui_read_model,'_current_text_manifest',side_effect=manifest),patch.object(_ExistingBinding,'close',close):
                    with self.assertRaises(type(first if primary else late)) as caught:api(fixture['workspace'],fixture['intake_id'],**options)
                self.assertIs(caught.exception,first if primary else late);self.assertEqual(len(bindings),2)
                self.assertTrue(all(binding.state=='closed' and binding.active==0 and not binding.handles for binding in bindings))
                self.assertEqual(files(fixture['root']),before)

    def test_real_missing_workspace_is_unavailable_without_creating_any_store(self):
        api=self.api();workspace=self.root/'missing'
        with self.assertRaises(ReadModelError) as caught:
            api(workspace,'authored',method=METHOD,rules=[],rule_sources=[],inputs={},execution_context={})
        self.assertEqual(caught.exception.code,'store_missing');self.assertFalse(workspace.exists())

    def test_relative_workspace_is_anchored_once_even_if_caller_cwd_changes_during_review(self):
        api=self.api();module=importlib.import_module(api.__module__)
        fixture=authored_fixture(self.root/'anchored');options=arguments(fixture);before=files(fixture['root'])
        elsewhere=self.root/'elsewhere';elsewhere.mkdir();original_cwd=Path.cwd()
        def review(*args,**kwargs):
            value=evaluate_intake_rule_conditions(*args,**kwargs);os.chdir(elsewhere);return value
        try:
            os.chdir(fixture['root'])
            with patch.object(module,'evaluate_intake_rule_conditions',side_effect=review):
                result=api(Path('state'),fixture['intake_id'],**options)
        finally:os.chdir(original_cwd)
        self.check(result);self.assertEqual(result['status'],'REVIEW_RULE_BRANCH')
        self.assertEqual(result['current_relation']['status'],'same_current_snapshot')
        self.assertEqual(files(fixture['root']),before);self.assertFalse((elsewhere/'state').exists())
