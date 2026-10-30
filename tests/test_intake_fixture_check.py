"""Actual lead-owned acceptance; developer adapters must be integrated to pass."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from labflow.intake_fixture_check import run_fixture_flow


class IntakeFixtureCheckTests(unittest.TestCase):
    def test_existing_output_is_preserved_before_loading_executors(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'existing'
            folder.mkdir()
            marker = folder / 'marker'
            marker.write_bytes(b'preserve existing evidence')
            with self.assertRaises(ValueError):
                run_fixture_flow(folder)
            self.assertEqual(marker.read_bytes(), b'preserve existing evidence')
            self.assertEqual(list(folder.iterdir()), [marker])

    def test_actual_text_intake_to_single_fixture_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_fixture_flow(Path(temporary) / 'new-run', power_dbm=-4)
            summary = result['summary']
            self.assertEqual(summary['fixture_acceptance'], 'pass')
            self.assertEqual(summary['records'], 1)
            self.assertIs(summary['source_current'], True)
            self.assertIs(summary['historical'], False)
            self.assertIs(summary['intake_ready'], True)
            self.assertEqual(summary['current_revision'], summary['revision'])
            self.assertIs(summary['source_synthetic'], True)
            self.assertIs(summary['ai_model_called'], False)
            self.assertIs(summary['hardware_verified'], False)
            self.assertIs(summary['fixture_measurement_observed'], True)
            self.assertEqual(summary['task_outcome'], 'not_assessed')
            self.assertEqual(summary['cleanup_status'], 'not_assessed')
            saved = json.loads((result['output'] / 'public-summary.json').read_text(encoding='utf-8'))
            self.assertEqual(saved, summary)

    def test_completed_measurement_is_historical_after_defer_before_summary(self):
        from labflow.intake_fixture_bridge import run_fixture_worker
        from labflow.intake_jobs import respond

        def defer_after_execution(store, **kwargs):
            result = run_fixture_worker(store, **kwargs)
            with store.connection() as con:
                intake_id = con.execute('SELECT intake_id FROM intake_fixture_jobs').fetchone()[0]
            respond(store, 'FLOW-LATE-DEFER', 'defer', intake_id=intake_id)
            return result

        with tempfile.TemporaryDirectory() as temporary:
            with patch('labflow.intake_fixture_bridge.run_fixture_worker', side_effect=defer_after_execution):
                result = run_fixture_flow(Path(temporary) / 'new-run', power_dbm=-4)
            summary = result['summary']
            self.assertIs(summary.get('source_current'), False)
            self.assertIs(summary['historical'], True)
            self.assertIs(summary['intake_ready'], False)
            self.assertEqual(summary['current_revision'], summary['revision'])
            self.assertIs(summary['fixture_measurement_observed'], True)
            self.assertEqual(summary['execution_state'], 'completed')
            self.assertEqual(summary['fixture_acceptance'], 'fail')
            from labflow.ui_read_model import IntakeReadModel
            record = IntakeReadModel(result['workspace']).fixture_runs(summary['intake_id'])['records'][0]
            self.assertIs(record['source_current'], False)
            self.assertEqual(record['report']['assessment']['verdict'], 'pass')

    def test_actual_two_page_pdf_requires_and_preserves_page_citations(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_fixture_flow(Path(temporary) / 'new-pdf-run', document_kind='pdf')
            self.assertEqual(result['summary']['fixture_acceptance'], 'pass')
            from labflow.ui_read_model import IntakeReadModel
            intake = IntakeReadModel(result['workspace']).snapshot(result['summary']['intake_id'])['intake']
            self.assertEqual(intake['analysis']['submitted']['schema_version'], 2)
            facts = intake['analysis']['submitted']['facts']
            market = next(f for f in facts if f['field'] == 'market')
            self.assertEqual(market['evidence'][0]['kind'], 'pdf_page')
            self.assertEqual(market['evidence'][0]['page_number'], 2)


class ConductedWorkflowEntryTests(unittest.TestCase):
    def test_text_opt_in_is_explicitly_unsupported_without_runtime(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            result = run_conducted_flow(Path(temporary) / 'text', document_kind='text', measurement_ref='event:17')
            self.assertEqual(result['summary']['status'], 'unsupported')
            self.assertEqual(result['summary']['reason'], 'conducted_workflow_pdf_required')
            self.assertEqual(result['summary']['runtime_calls'], 0)
            self.assertIsNone(result['workspace'])

    def test_missing_explicit_measurement_ref_never_selects_last_measurement(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            result = run_conducted_flow(Path(temporary) / 'reference', document_kind='pdf', measurement_ref=None)
            self.assertEqual(result['summary']['status'], 'unsupported')
            self.assertEqual(result['summary']['reason'], 'conducted_workflow_measurement_ref_required')
            self.assertEqual(result['summary']['runtime_calls'], 0)
            self.assertIsNone(result['workspace'])

    def test_cli_serves_original_startup_bindings_and_closes_after_interrupt(self):
        from labflow.intake_fixture_check import main
        plan, snapshot = {'original': 'plan'}, {'original': 'result'}
        flow = {'summary': {'fixture_acceptance': 'pass', 'intake_id': 'I-MOCK'},
                'workspace': Path('owned-synthetic-state'),
                'server_options': {'conducted_plan_preview_inputs': plan, 'conducted_result_snapshot': snapshot}}
        with patch('labflow.intake_fixture_check.run_conducted_flow', create=True, return_value=flow), patch('labflow.ui_server.create_server') as create:
            server = create.return_value.__enter__.return_value
            server.server_port = 8123
            server.serve_forever.side_effect = KeyboardInterrupt
            code = main(['--conducted-workflow', '--document-kind', 'pdf', '--measurement-ref', 'event:17', '--port', '0'])
            self.assertEqual(code, 0)
            create.assert_called_once_with(flow['workspace'], port=0, **flow['server_options'])
            create.return_value.__exit__.assert_called_once_with(None, None, None)
            self.assertEqual(snapshot, {'original': 'result'})


class ConductedFailureScenarioTests(unittest.TestCase):
    def test_missing_duty_unit_blocks_from_original_pdf_with_partial_plan_and_no_runtime(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            result = run_conducted_flow(Path(temporary) / 'missing', measurement_ref='event:17',
                mock_model='gpt-6.1-sol', scenario='missing-duty-unit')
            self.assertEqual(result['summary']['status'], 'blocked')
            self.assertEqual(result['summary']['runtime_calls'], 0)
            self.assertEqual(result['summary']['draft_status'], 'not_run')
            original = json.loads((result['output'] / 'facts-plan-original.json').read_bytes())
            self.assertIsNone(original['plan_input']['plan']['source_settings']['duty_cycle'])
            self.assertIsNone(original['plan_input']['plan']['basis_refs']['duty_cycle'])
            self.assertEqual(result['server_options']['conducted_plan_preview_inputs']['source_settings'],
                             original['plan_input']['plan']['source_settings'])
            features = next(f for f in original['plan_input']['intake']['source_facts'] if f['field'] == 'features')
            self.assertIn('duty_cycle: 50;', features['value'])
            self.assertNotIn('duty_cycle: 50 %', features['evidence'][0]['quote'])
            self.assertFalse((result['output'] / 'x').exists())

    def test_invalid_new_mock_citation_preserves_strict_error_without_completing_analysis(self):
        from labflow.intake_fixture_check import run_conducted_flow
        from labflow.ui_read_model import IntakeReadModel
        with tempfile.TemporaryDirectory() as temporary:
            result = run_conducted_flow(Path(temporary) / 'citation', measurement_ref='event:17',
                mock_model='gpt-6.1-sol', scenario='invalid-citation')
            self.assertEqual(result['summary']['status'], 'rejected')
            self.assertEqual(result['summary']['reason'], 'analysis_response_invalid')
            self.assertEqual(result['summary']['runtime_calls'], 0)
            failure = json.loads((result['output'] / 'failure.json').read_bytes())
            self.assertEqual(failure['code'], 'analysis_response_invalid')
            self.assertEqual(failure['phase'], 'strict_scripted_analysis')
            self.assertIsNone(IntakeReadModel(result['workspace']).snapshot(result['summary']['intake_id'])['intake']['analysis'])
            self.assertTrue((result['output'] / 'analysis-MOCK-original.json').is_file())
            self.assertFalse((result['output'] / 'analysis-strict.json').exists())
            self.assertFalse((result['output'] / 'facts-plan-original.json').exists())
            self.assertFalse((result['output'] / 'x').exists())

    def test_link_state_scenarios_require_explicit_measurement_ref_before_store(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            for scenario in ('transport-error', 'recovery-failure'):
                with self.subTest(scenario=scenario):
                    result = run_conducted_flow(Path(temporary) / scenario, measurement_ref=None,
                        mock_model='gpt-6.1-sol', scenario=scenario)
                    self.assertEqual(result['summary']['status'], 'unsupported')
                    self.assertEqual(result['summary']['reason'], 'conducted_workflow_measurement_ref_required')
                    self.assertEqual(result['summary']['runtime_calls'], 0)
                    self.assertIsNone(result['workspace'])
                    self.assertEqual(result['summary']['draft_status'], 'not_run')
                    self.assertEqual(list(result['output'].iterdir()), [result['output'] / 'public-summary.json'])

    def test_unknown_scenario_is_rejected_before_output_creation(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'unknown'
            with self.assertRaisesRegex(ValueError, '^conducted_workflow_scenario_unsupported$'):
                run_conducted_flow(output, scenario='arbitrary-fault')
            self.assertFalse(output.exists())


DEMO_STARTUP_OBSERVATIONS=[]


class ConductedArtifactStartupTests(unittest.TestCase):
    """New native startup provenance examples, not a result-validity oracle."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='demo-startup-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def api(self):
        from labflow import intake_fixture_check as module
        self.assertTrue(hasattr(module,'_conducted_artifact_startup'),'assigned artifact startup helper is absent')
        return module._conducted_artifact_startup

    def values(self,status='recorded'):
        from hashlib import sha256
        from labflow.store import canonical
        from labflow.virtual_fleet.conducted_result_artifact import _verification
        plan=dict(status='ready_for_simulation',binding=dict(intake_id='I-original-current',revision=3,context_sha256='a'*64))
        method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output')
        result=dict(schema_version=1,kind='conducted_twin_result',status=status,
            binding=dict(run_id='authored-artifact-run',runtime_instance_id='authored-runtime',
                plan_input=dict(binding=dict(intake_id='I-do-not-copy',revision=97,context_sha256='d'*64))),
            raw_measurement=None,calculation=dict(corrected=None),gaps=[dict(code='authored-gap')])
        prefix='.local/conducted-result-artifacts/authored-artifact/'
        artifact=dict(schema_version=1,kind='conducted_result_artifact',artifact_name='authored-artifact',
            run_id='authored-artifact-run',runtime_instance_id='authored-runtime',result_status=status,
            storage=dict(status='complete',commit_marker=prefix+'manifest.json',bytes=1000,sha256='b'*64),
            files=[dict(path=prefix+'result.json',sha256=sha256((canonical(result)+'\n').encode()).hexdigest(),bytes=100),
                dict(path=prefix+'draft.md',sha256='c'*64,bytes=100)],verification=_verification('full_bound'),execution_authority=False)
        finalized=dict(status='stored',result=result,artifact=artifact,failure=None)
        return plan,method,finalized

    def test_native10_uses_original_current_plan_and_actual_finalizer_pins_not_file_LF_hash(self):
        from copy import deepcopy
        from hashlib import sha256
        from labflow.store import canonical
        api=self.api();plan,method,finalized=self.values();before=deepcopy((plan,method,finalized))
        selected=api(plan,method,finalized,self.root)
        self.assertEqual(set(selected),set('intake_id method expected_revision expected_context_sha256 artifact_workspace_root artifact_name expected_manifest_sha256 expected_result_sha256 run_id runtime_instance_id'.split()))
        self.assertEqual(selected,dict(intake_id='I-original-current',method=method,expected_revision=3,expected_context_sha256='a'*64,
            artifact_workspace_root=str(self.root),artifact_name='authored-artifact',expected_manifest_sha256='b'*64,
            expected_result_sha256=sha256(canonical(finalized['result']).encode()).hexdigest(),
            run_id='authored-artifact-run',runtime_instance_id='authored-runtime'))
        self.assertNotEqual(selected['expected_result_sha256'],finalized['artifact']['files'][0]['sha256'])
        self.assertEqual((plan,method,finalized),before);self.assertEqual(list(self.root.iterdir()),[])

    def test_stored_invalid_and_incomplete_remain_readable_but_held_blocked_and_null_have_no_selection(self):
        api=self.api()
        for status in ('recorded','incomplete','invalid'):
            with self.subTest(status=status):
                plan,method,finalized=self.values(status);selected=api(plan,method,finalized,self.root)
                self.assertIsNotNone(selected);self.assertEqual(finalized['result']['status'],status)
                self.assertIs(finalized['artifact']['execution_authority'],False)
        for field in ('held','blocked','no_result','no_artifact','incomplete_storage'):
            with self.subTest(field=field):
                plan,method,finalized=self.values()
                if field=='held':finalized['status']='held'
                elif field=='blocked':plan['status']='blocked'
                elif field=='no_result':finalized['result']=None
                elif field=='no_artifact':finalized['artifact']=None
                else:finalized['artifact']['storage']['status']='incomplete'
                self.assertIsNone(api(plan,method,finalized,self.root))

    def test_complete_metadata_contradictions_and_nonlocal_roots_fail_with_one_fixed_code(self):
        api=self.api()
        for field in ('result_status','version','authority','verification','manifest_sha','marker','manifest_bytes','revision','method_limit'):
            with self.subTest(field=field):
                plan,method,finalized=self.values();artifact=finalized['artifact']
                if field=='result_status':artifact['result_status']='invalid'
                elif field=='version':artifact['schema_version']=True
                elif field=='authority':artifact['execution_authority']=0
                elif field=='verification':artifact['verification']['hardware_verified']=0
                elif field=='manifest_sha':artifact['storage']['sha256']='PRIVATE-NOT-A-HASH'
                elif field=='marker':artifact['storage']['commit_marker']='PRIVATE-OTHER/manifest.json'
                elif field=='manifest_bytes':artifact['storage']['bytes']=0
                elif field=='revision':plan['binding']['revision']=True
                else:method['oversize']='x'*65537
                with self.assertRaises(ValueError) as caught:api(plan,method,finalized,self.root)
                self.assertEqual(str(caught.exception),'conducted_workflow_artifact_startup_invalid')
                self.assertIsNone(caught.exception.__context__)
        for root in ('relative/private',r'\\private\share',object()):
            with self.subTest(root_type=type(root).__name__):
                plan,method,finalized=self.values()
                with self.assertRaises(ValueError) as caught:api(plan,method,finalized,root)
                self.assertEqual(str(caught.exception),'conducted_workflow_artifact_startup_invalid')

    def test_startup_control_identity_is_not_normalized_or_used_for_approval(self):
        api=self.api()
        class Stop(BaseException):pass
        for error in (KeyboardInterrupt('original'),MemoryError('original'),SystemExit(61),GeneratorExit('original'),Stop('original')):
            with self.subTest(error=type(error).__name__):
                plan,method,finalized=self.values()
                with patch('labflow.ui_server._conducted_artifact_readback_selection',side_effect=error):
                    with self.assertRaises(type(error)) as caught:api(plan,method,finalized,self.root)
                self.assertIs(caught.exception,error)

    def test_first_flow_control_survives_a_later_failure_evidence_control(self):
        from labflow import intake_fixture_check as module
        first=KeyboardInterrupt('first authored flow control');late=SystemExit('late evidence publication')
        write=module._conducted_json
        def evidence(output,relative,value):
            if relative=='failure.json':raise late
            return write(output,relative,value)
        with patch.object(module,'_conducted_mock_compiler',return_value=self.root/'not-executed-compiler'),\
             patch('labflow.intake_jobs.claim_job',side_effect=first),patch.object(module,'_conducted_json',side_effect=evidence):
            with self.assertRaises(KeyboardInterrupt) as caught:
                module.run_conducted_flow(self.root/'first-control',measurement_ref='event:17',mock_model='gpt-6.1-sol')
        self.assertIs(caught.exception,first)

    def test_initial_blocked_plan_has_no_artifact_selection_and_never_compiles_or_executes(self):
        from labflow import intake_fixture_check as module
        with patch.object(module,'_compile_conducted_mock',side_effect=AssertionError('blocked compiled')) as compiler,\
             patch.object(module,'_conducted_artifact_startup',side_effect=AssertionError('blocked assembled artifact')) as helper:
            result=module.run_conducted_flow(self.root/'blocked',measurement_ref='event:17',mock_model='gpt-6.1-sol',scenario='missing-duty-unit')
        self.assertEqual(result['summary']['status'],'blocked');self.assertEqual(result['summary']['runtime_calls'],0)
        self.assertNotIn('conducted_artifact_readback_inputs',result['server_options'])
        compiler.assert_not_called();helper.assert_not_called()
        self.assertFalse((result['output']/'x').exists())
        original=json.loads((result['output']/'facts-plan-original.json').read_bytes())
        self.assertIsNone(original['plan_input']['plan']['source_settings']['duty_cycle'])

    def test_cli_forwards_the_original_three_options_and_retains_exit_and_close_behavior(self):
        import io
        from contextlib import redirect_stdout
        from labflow import intake_fixture_check as module
        plan,method,finalized=self.values('invalid');selection=self.api()(plan,method,finalized,self.root)
        preview,snapshot={'original':'preview'},{'original':'invalid-result'}
        options=dict(conducted_plan_preview_inputs=preview,conducted_result_snapshot=snapshot,conducted_artifact_readback_inputs=selection)
        flow=dict(summary=dict(fixture_acceptance='fail',intake_id='I-original-current'),workspace=self.root/'s',server_options=options)
        output=io.StringIO()
        with patch.object(module,'run_conducted_flow',return_value=flow),patch('labflow.ui_server.create_server') as create,redirect_stdout(output):
            server=create.return_value.__enter__.return_value;server.server_port=8123;server.serve_forever.side_effect=KeyboardInterrupt
            code=module.main(['--conducted-workflow','--document-kind','pdf','--measurement-ref','event:17','--mock-model','gpt-6.1-sol','--port','0'])
        self.assertEqual(code,1);create.assert_called_once_with(flow['workspace'],port=0,**options)
        create.return_value.__exit__.assert_called_once_with(None,None,None)
        self.assertEqual(json.loads(output.getvalue().splitlines()[0]),flow['summary'])
        self.assertIn('http://127.0.0.1:8123/#I-original-current',output.getvalue())
        self.assertEqual(snapshot,{'original':'invalid-result'})


class ConductedArtifactStartupGenuineTests(unittest.TestCase):
    """Two new authored native MOCK flows; no installed CLI or real model."""
    maxDiff=None

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cas-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def files(self,root):
        import os
        from hashlib import sha256
        observed={}
        for path in root.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:raw=stream.read();info=os.fstat(stream.fileno())
                observed[path.relative_to(root).as_posix()]=(sha256(raw).hexdigest(),info.st_size,info.st_ino,info.st_nlink,
                    info.st_mtime_ns,info.st_ctime_ns,getattr(info,'st_file_attributes',None))
        return observed

    def preserve(self,root,event):
        files={}
        for path in root.rglob('*'):
            if path.is_file():
                relative=path.relative_to(root)
                if relative.parts[0]=='s':continue  # Store bytes are observed, not exported as a second DB.
                files[relative.as_posix()]=path.read_bytes()
        total=sum(len(raw) for raw in files.values())
        existing=sum(len(raw) for item in DEMO_STARTUP_OBSERVATIONS for raw in item.get('files',{}).values())
        if len(files)>400 or total+existing>24*1024*1024:raise AssertionError('authored original capture limit')
        event['files']=files;DEMO_STARTUP_OBSERVATIONS.append(event)

    def exercise(self,scenario,expected_status,expected_acceptance):
        import http.client
        import importlib
        import threading
        from hashlib import sha256
        from labflow import intake_fixture_check as module
        from labflow.store import canonical
        from labflow.ui_server import create_server
        finalizer=importlib.import_module('labflow.conducted_execution_result_finalizer')
        original_finalize=finalizer.finalize_conducted_execution_result;calls=[]
        def finalize(*args,**kwargs):
            value=original_finalize(*args,**kwargs);calls.append((kwargs,value));return value
        helper=module._conducted_artifact_startup;output=self.root/'flow';event=dict(case=scenario,kind='new authored native MOCK flow')
        first=None
        try:
            with patch.object(finalizer,'finalize_conducted_execution_result',side_effect=finalize),\
                 patch.object(module,'_conducted_artifact_startup',wraps=helper) as assembled:
                flow=module.run_conducted_flow(output,measurement_ref='event:17',mock_model='gpt-6.1-sol',scenario=scenario)
            self.assertEqual(len(calls),1);self.assertEqual(assembled.call_count,1)
            options=flow['server_options'];selected=options['conducted_artifact_readback_inputs']
            original=calls[0][1];root=calls[0][0]['workspace_root']
            self.assertIs(assembled.call_args.args[3],root);self.assertEqual(root,flow['output'])
            self.assertEqual(selected['artifact_workspace_root'],str(root));self.assertTrue(Path(selected['artifact_workspace_root']).is_absolute())
            plan=json.loads((output/'facts-plan-original.json').read_bytes())['plan_input']
            self.assertEqual(selected['intake_id'],plan['binding']['intake_id'])
            self.assertEqual(selected['expected_revision'],plan['binding']['revision'])
            self.assertEqual(selected['expected_context_sha256'],plan['binding']['context_sha256'])
            self.assertEqual(selected['method'],options['conducted_plan_preview_inputs']['method'])
            self.assertEqual(selected['artifact_name'],original['artifact']['artifact_name'])
            self.assertEqual(selected['expected_manifest_sha256'],original['artifact']['storage']['sha256'])
            self.assertEqual(selected['expected_result_sha256'],sha256(canonical(original['result']).encode()).hexdigest())
            self.assertEqual((selected['run_id'],selected['runtime_instance_id']),(original['artifact']['run_id'],original['artifact']['runtime_instance_id']))
            row=next(row for row in original['artifact']['files'] if row['path'].endswith('/result.json'))
            raw_result=(output/row['path']).read_bytes();self.assertEqual(sha256(raw_result).hexdigest(),row['sha256'])
            self.assertNotEqual(selected['expected_result_sha256'],row['sha256'])
            self.assertEqual(sha256(raw_result[:-1]).hexdigest(),selected['expected_result_sha256']);self.assertTrue(raw_result.endswith(b'\n'))
            self.assertEqual(json.loads((output/'server-startup-original.json').read_bytes()),options)
            self.assertEqual(json.loads((output/'finalizer-original.json').read_bytes()),original)
            self.assertEqual(flow['summary']['result_status'],expected_status);self.assertEqual(flow['summary']['fixture_acceptance'],expected_acceptance)
            self.assertEqual(flow['summary']['storage_status'],'complete');self.assertFalse(flow['summary']['ai_model_called'])
            before=self.files(output);server=None;thread=None
            with patch('subprocess.Popen',side_effect=AssertionError('GET reran a child')),\
                 patch('labflow.store.Store.__init__',side_effect=AssertionError('GET initialized Store')):
                try:
                    server=create_server(flow['workspace'],port=0,**options)
                    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
                    address=server.server_address;connection=http.client.HTTPConnection(*address,timeout=5)
                    try:
                        connection.request('GET','/api/intakes/'+selected['intake_id']+'/conducted-artifact-readback',
                            headers={'Origin':'http://127.0.0.1:'+str(address[1]),'Sec-Fetch-Site':'same-origin'})
                        response=connection.getresponse();raw=response.read(12582914);value=json.loads(raw)
                        event.update(http_status=response.status,http_headers=dict(response.getheaders()),http_body=raw)
                    finally:connection.close()
                    self.assertEqual(response.status,200);self.assertEqual(raw,canonical(value).encode()+b'\n')
                    self.assertEqual(value['status'],'matched');self.assertEqual(value['relation']['recheck']['status'],'unchanged')
                    self.assertEqual(value['artifact']['result'],original['result']);self.assertEqual(value['artifact']['result']['status'],expected_status)
                    self.assertEqual(value['artifact']['storage']['status'],'manifest_payloads_verified')
                    self.assertIs(value['verification']['permanent_current_approval'],False);self.assertIs(value['verification']['execution_authority'],False)
                    if expected_status=='invalid':self.assertIsNone(value['artifact']['result']['calculation']['corrected'])
                finally:
                    if server is not None:
                        server.shutdown();server.server_close()
                        if thread is not None:thread.join(5);self.assertFalse(thread.is_alive())
                        self.assertEqual(server.socket.fileno(),-1)
            self.assertEqual(self.files(output),before)
            event.update(summary=flow['summary'],selection=selected,same_files_after_GET=True,known_server_closed=True)
        except BaseException as error:first=error
        finally:
            if output.exists():
                try:self.preserve(output,event)
                except BaseException as error:
                    DEMO_STARTUP_OBSERVATIONS.append(dict(case=scenario,capture_error=type(error).__name__))
                    if first is None:first=error
        if first is not None:raise first

    def test_new_normal_native_mock_flow_hands_actual_finalizer_artifact_to_genuine_GET(self):
        self.exercise('normal','recorded','pass')

    def test_new_measurement_invalid_native_mock_artifact_is_readable_without_promoting_fixture(self):
        self.exercise('measurement-invalid','invalid','fail')


class ConductedReadbackInputTests(unittest.TestCase):
    """Export original trusted pins; typed flow seams never launch a runtime."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='demo-readback-input-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def api(self):
        from labflow import intake_fixture_check as module
        self.assertTrue(hasattr(module,'_conducted_readback_inputs'),'assigned readback input export is absent')
        return module._conducted_readback_inputs

    def selection(self):
        return dict(intake_id='I-original-only',method=dict(method_id='authored-on',method_version=3,metric='on',reference_plane='source_output'),
            expected_revision=7,expected_context_sha256='a'*64,artifact_workspace_root=str(self.root/'original-artifact-root'),
            artifact_name='draft-original',expected_manifest_sha256='b'*64,expected_result_sha256='c'*64,
            run_id='run-original',runtime_instance_id='runtime-original')

    def test_export_preserves_all_nine_original_values_and_excludes_only_intake_id(self):
        from copy import deepcopy
        selection=self.selection();before=deepcopy(selection)
        self.api()(self.root,selection)
        raw=(self.root/'readback-inputs.json').read_bytes();value=json.loads(raw)
        self.assertEqual(value,dict(method=dict(method_id='authored-on',method_version=3,metric='on',reference_plane='source_output'),
            expected_revision=7,expected_context_sha256='a'*64,artifact_workspace_root=str(self.root/'original-artifact-root'),
            artifact_name='draft-original',expected_manifest_sha256='b'*64,expected_result_sha256='c'*64,
            run_id='run-original',runtime_instance_id='runtime-original'))
        self.assertEqual(selection,before);self.assertTrue(raw.endswith(b'\n'))
        self.assertEqual([p.name for p in self.root.iterdir()],['readback-inputs.json'])

    def test_none_selection_and_initial_blocked_or_unsupported_flows_create_no_readback_file(self):
        from labflow import intake_fixture_check as module
        self.api()(self.root,None);self.assertEqual(list(self.root.iterdir()),[])
        with patch.object(module,'_conducted_mock_compiler',return_value=self.root/'not-executed-compiler'):
            for scenario,kind,want in (('missing-duty-unit','pdf','blocked'),('normal','text','unsupported')):
                with self.subTest(scenario=scenario,kind=kind):
                    result=module.run_conducted_flow(self.root/(want+'-flow'),document_kind=kind,
                        measurement_ref='event:17',mock_model='gpt-6.1-sol',scenario=scenario)
                    self.assertEqual(result['summary']['status'],want)
                    self.assertFalse((result['output']/'readback-inputs.json').exists())
                    self.assertEqual(result['summary']['runtime_calls'],0)

    def test_existing_readback_file_and_its_metadata_are_never_overwritten(self):
        import os
        api=self.api();target=self.root/'readback-inputs.json';original=b'original partial evidence\x00\n'
        target.write_bytes(original)
        with target.open('rb') as stream:before=os.fstat(stream.fileno())
        with self.assertRaises(FileExistsError):api(self.root,self.selection())
        with target.open('rb') as stream:after=os.fstat(stream.fileno());self.assertEqual(stream.read(),original)
        self.assertEqual((before.st_size,before.st_ino,before.st_mtime_ns,before.st_ctime_ns),
            (after.st_size,after.st_ino,after.st_mtime_ns,after.st_ctime_ns))

    def test_projected_file_and_byte_caps_refuse_before_creating_the_new_file(self):
        from types import SimpleNamespace
        api=self.api()
        for count,size in ((512,0),(1,32*1024*1024)):
            with self.subTest(projected_count=count,projected_size=size):
                item=SimpleNamespace(is_file=lambda:True,stat=lambda:SimpleNamespace(st_size=size))
                with patch.object(Path,'rglob',return_value=[item]*count):
                    with self.assertRaises(ValueError) as caught:api(self.root,self.selection())
                self.assertEqual(str(caught.exception),'conducted_workflow_evidence_limit')
                self.assertEqual(list(self.root.iterdir()),[])

    def test_partial_write_and_original_controls_remain_without_retry_or_cleanup(self):
        api=self.api();open_original=Path.open
        class Stop(BaseException):pass
        for index,error in enumerate((OSError('first partial write'),KeyboardInterrupt('first'),MemoryError('first'),SystemExit(41),GeneratorExit('first'),Stop('first'))):
            with self.subTest(error=type(error).__name__):
                folder=self.root/str(index);folder.mkdir();target=folder/'readback-inputs.json';calls=[]
                class Partial:
                    def __enter__(inner):inner.stream=open_original(target,'xb');return inner
                    def __exit__(inner,*args):return inner.stream.__exit__(*args)
                    def write(inner,raw):calls.append(raw);inner.stream.write(raw[:17]);raise error
                def opened(path,*args,**kwargs):
                    return Partial() if path==target else open_original(path,*args,**kwargs)
                with patch.object(Path,'open',opened):
                    with self.assertRaises(type(error)) as caught:api(folder,self.selection())
                self.assertIs(caught.exception,error);self.assertEqual(len(calls),1)
                self.assertEqual(target.read_bytes(),calls[0][:17])

    def typed_flow(self,folder,*,held=False):
        from labflow import intake_fixture_check as module
        from labflow.virtual_fleet.conducted_result_artifact import _verification
        result=dict(schema_version=1,kind='conducted_twin_result',status='invalid',binding=dict(run_id='typed-run',runtime_instance_id='typed-runtime'),
            raw_measurement=None,calculation=dict(corrected=None),gaps=[dict(code='typed-invalid')])
        artifact=dict(schema_version=1,kind='conducted_result_artifact',artifact_name='draft-typed',run_id='typed-run',runtime_instance_id='typed-runtime',
            result_status='invalid',storage=dict(status='complete',commit_marker='.local/conducted-result-artifacts/draft-typed/manifest.json',bytes=1000,sha256='b'*64),
            files=[],verification=_verification('full_bound'),execution_authority=False)
        final=dict(status='held' if held else 'stored',result=None if held else result,artifact=None if held else artifact,failure=None)
        # Real PDF/current/plan/startup/writes; typed external execution/finalizer.
        execution=dict(kind='typed_no_runtime',execution=dict(trial_factory_calls=0,producer_calls_started=0))
        with patch.object(module,'_conducted_mock_compiler',return_value=self.root/'never-executed-compiler'),\
             patch.object(module,'_compile_conducted_mock',return_value=self.root/'never-executed-mock'),\
             patch('labflow.intake_plan_virtual_execution.run_intake_plan_virtual_execution',return_value=execution),\
             patch('labflow.conducted_execution_result_finalizer.finalize_conducted_execution_result',return_value=final):
            return module.run_conducted_flow(folder,measurement_ref='event:17',mock_model='gpt-6.1-sol')

    def test_typed_complete_flow_exports_saved_startup_values_while_held_null_creates_no_file(self):
        self.api()
        for held in (False,True):
            with self.subTest(held=held):
                flow=self.typed_flow(self.root/('held' if held else 'complete'),held=held)
                output=flow['output'];saved=json.loads((output/'server-startup-original.json').read_bytes())
                self.assertEqual(saved,flow['server_options']);self.assertEqual(flow['summary']['fixture_acceptance'],'fail')
                self.assertEqual(flow['summary']['runtime_calls'],0)
                self.assertNotIn('readback_inputs',flow['summary'])
                target=output/'readback-inputs.json'
                if held:
                    self.assertFalse(target.exists());self.assertNotIn('conducted_artifact_readback_inputs',saved)
                else:
                    selected=saved['conducted_artifact_readback_inputs'];exported=json.loads(target.read_bytes())
                    self.assertEqual(set(exported),set('method expected_revision expected_context_sha256 artifact_workspace_root artifact_name expected_manifest_sha256 expected_result_sha256 run_id runtime_instance_id'.split()))
                    self.assertEqual(dict(exported,intake_id=selected['intake_id']),selected)
                    self.assertEqual(flow['summary']['result_status'],'invalid');self.assertIsNone(flow['summary']['corrected'])

    def test_new_file_failure_keeps_original_startup_partial_bytes_and_first_error(self):
        from labflow import intake_fixture_check as module
        self.api();first=OSError('first readback publication');late=SystemExit('secondary failure evidence')
        output=self.root/'partial-flow';write=module._conducted_write
        def writing(folder,relative,raw):
            if relative=='readback-inputs.json':
                with (folder/relative).open('xb') as stream:stream.write(b'original partial\n')
                raise first
            if relative=='failure.json':raise late
            return write(folder,relative,raw)
        with patch.object(module,'_conducted_write',side_effect=writing):
            with self.assertRaises(OSError) as caught:self.typed_flow(output)
        self.assertIs(caught.exception,first);self.assertEqual((output/'readback-inputs.json').read_bytes(),b'original partial\n')
        startup=json.loads((output/'server-startup-original.json').read_bytes())
        self.assertIn('conducted_artifact_readback_inputs',startup)
        self.assertTrue((output/'finalizer-original.json').is_file())
        self.assertFalse((output/'public-summary.json').exists())




from hashlib import sha256
from labflow.store import canonical

WORKFLOW_EXPORT_OBSERVATIONS = []


class WorkflowReadbackExportTests(unittest.TestCase):
    """Provided native DTO/pin consistency only: no RF runtime or source file authentication."""
    @classmethod
    def setUpClass(cls):
        import importlib.util
        import sys
        from copy import deepcopy
        from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
        base=Path(__file__).parent
        spec=importlib.util.spec_from_file_location("export_plan_fixture",base/"test_intake_conducted_twin_plan.py")
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        authored_spec=importlib.util.spec_from_file_location("export_authored_facts",base/"test_intake_facts_to_conducted_plan.py")
        authored=importlib.util.module_from_spec(authored_spec)
        with patch.dict(sys.modules,{"test_intake_conducted_twin_plan":fixture}):
            authored_spec.loader.exec_module(authored)
        source_context,analysis,options=authored.authored()
        cls.source_plan=build_conducted_plan_from_intake_facts(source_context,analysis,**options)["plan_input"]
        context=deepcopy(source_context)
        context["instructions"]="Independent caller current readonly snapshot; provided test data, no execution authority."
        current_options={**options,"expected_context_sha256":sha256(canonical(context).encode()).hexdigest()}
        cls.method=options["method"]
        cls.current=dict(context=context,analysis=deepcopy(analysis),
            facts_plan=build_conducted_plan_from_intake_facts(context,analysis,**current_options))
        if cls.current["facts_plan"]["status"]!="ready_for_simulation":raise AssertionError("authored pure facts not ready")

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="workflow-export-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        from labflow import intake_fixture_check as module
        self.module=module

    def api(self):
        self.assertTrue(hasattr(self.module,"export_conducted_workflow_readback_inputs"),"public workflow export absent")
        return self.module.export_conducted_workflow_readback_inputs

    def frames(self,status="invalid",host_status="failed",selection=False):
        from copy import deepcopy
        from labflow.virtual_fleet import conducted_twin_result as dto
        from labflow.virtual_fleet.conducted_result_artifact import _verification
        result=dto._base();result["status"]=status
        result["binding"]=dict(run_id="provided-run",runtime_instance_id="provided-runtime",plan_input=deepcopy(self.source_plan))
        result["failure"]=dict(code="measurement_invalid",field="raw_measurement") if status=="invalid" else None
        result["gaps"]=[dict(code="provided-gap",field="raw_measurement",detail=None)]
        raw=canonical(result).encode()
        prefix=".local/conducted-result-artifacts/provided-draft/"
        artifact=dict(schema_version=1,kind="conducted_result_artifact",artifact_name="provided-draft",
            run_id="provided-run",runtime_instance_id="provided-runtime",result_status=status,
            storage=dict(status="complete",commit_marker=prefix+"manifest.json",bytes=1000,sha256="b"*64),
            files=[dict(path=prefix+"result.json",bytes=len(raw)+1,sha256=sha256(raw+b"\n").hexdigest(),media_type="application/json"),
                   dict(path=prefix+"draft.md",bytes=77,sha256="c"*64,media_type="text/markdown")],
            verification=_verification("full_bound"),execution_authority=False)
        execution=dict(schema_version=1,kind="intake_plan_virtual_execution_result",status="stopped",failure=None,
            binding=dict(run_id="provided-run",runtime_instance_id="provided-runtime"),plan_input=deepcopy(self.source_plan),
            loop=None,execution=None,artifacts={},verification=dict(execution_authority=False))
        final=dict(schema_version=1,kind="conducted_execution_result_finalizer",status="stored",execution_receipt=execution,
            input_files={},result=result,artifact=artifact,failure=result["failure"],secondary_errors=[],
            verification=dict(evidence_snapshot_verified=True,recording_mode="post_run_from_retained_events",origin_authenticated=False,
                ai_model_called=None,execution_rerun=False,source_bytes_reopened=False,physical_verified=False,hardware_verified=False,
                full_task_verified=False,method_approval="not_assessed"),
            execution_authority=False)
        if selection:final["measurement_selection"]=dict(schema_version=1,kind="conducted_measurement_selection",status="selected",result=deepcopy(result))
        return self.summary(final,host_status),final

    def summary(self,final,host_status="failed"):
        from copy import deepcopy
        def pin(value):
            raw=canonical(value).encode("utf-8")
            return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        execution=None if final is None else final["execution_receipt"]
        return dict(schema_version=1,kind="codex_registered_conducted_workflow_host_receipt",status=host_status,
            phase="finished",scenario_id="provided-scenario",requested_model="gpt-6.1-sol",history=None,reservation=None,
            execution=None if execution is None else dict(run_id=execution["binding"]["run_id"],
                runtime_instance_id=execution["binding"]["runtime_instance_id"],status=execution["status"],
                failure=deepcopy(execution["failure"]),receipt=pin(execution),producer_receipts=[]),
            finalization=None if final is None else dict(status=final["status"],
                result_status=None if final["result"] is None else final["result"]["status"],
                artifact=deepcopy(final["artifact"]),failure=deepcopy(final["failure"]),receipt=pin(final)),
            errors=[dict(phase="finalizer",code="provided-original-failure")],
            verification=dict(operator_scope="not_validated",execution_scope="one_registered_synthetic_conducted_workflow",
                origin_authenticated=False,remote_model_identity_verified=False,measurement="not_assessed",hardware_verified=False))

    def call(self,host=None,final=None,*,folder=None,current="default",method=None):
        if host is None and final is None:host,final=self.frames()
        return self.api()(self.root if folder is None else folder,host,final,
            current_facts_plan=self.current if current=="default" else current,
            method=self.method if method is None else method,artifact_workspace_root=str(self.root/"unread-artifact-root"))

    def test_public_export_uses_independent_current_and_original_lf_roles(self):
        from copy import deepcopy
        host,final=self.frames();before=deepcopy((host,final,self.current,self.method))
        startup=self.module._conducted_artifact_startup;write=self.module._conducted_readback_inputs;seen=[]
        def selected(*args):
            value=startup(*args);seen.append(value);return value
        with patch.object(self.module,"_conducted_artifact_startup",side_effect=selected) as assemble,patch.object(
                self.module,"_conducted_readback_inputs",wraps=write) as exported:
            value=self.call(host,final)
        self.assertEqual((assemble.call_count,exported.call_count),(1,1));self.assertIs(value,seen[0])
        raw=(self.root/"readback-inputs.json").read_bytes();saved=json.loads(raw)
        self.assertEqual(dict(saved,intake_id=value["intake_id"]),value)
        self.assertEqual(raw,(canonical(saved)+"\n").encode())
        self.assertEqual(value["expected_revision"],self.current["context"]["revision"])
        self.assertEqual(value["expected_context_sha256"],sha256(canonical(self.current["context"]).encode()).hexdigest())
        self.assertNotEqual(value["expected_context_sha256"],final["result"]["binding"]["plan_input"]["binding"]["context_sha256"])
        self.assertEqual(value["expected_result_sha256"],sha256(canonical(final["result"]).encode()).hexdigest())
        self.assertNotEqual(value["expected_result_sha256"],final["artifact"]["files"][0]["sha256"])
        self.assertEqual((host,final,self.current,self.method),before)
        self.assertEqual([p.name for p in self.root.iterdir()],["readback-inputs.json"])
        WORKFLOW_EXPORT_OBSERVATIONS.append(dict(kind="provided native source/pin consistency",selection=value,host=host,finalizer=final,
            current=self.current,export_hex=raw.hex(),inputs_unchanged=True,source_io=0,sql=0,rf=0,model=0))

    def test_failed_unknown_stored_invalid_incomplete_and_selection_evidence_are_preserved(self):
        from copy import deepcopy
        for index,(status,host_status,selection) in enumerate((("invalid","failed",False),("incomplete","unknown",True))):
            host,final=self.frames(status,host_status,selection);before=deepcopy((host,final))
            folder=self.root/str(index);folder.mkdir();value=self.call(host,final,folder=folder)
            self.assertIsNotNone(value);self.assertEqual((host,final),before)
            self.assertEqual(host["status"],host_status);self.assertEqual(final["result"]["status"],status)
            self.assertIsNone(final["result"]["calculation"]["corrected"]);self.assertIs(final["execution_authority"],False)
            WORKFLOW_EXPORT_OBSERVATIONS.append(dict(kind="provided failed/unknown DRAFT, not real execution",host_status=host_status,result_status=status,
                finalizer_selection_evidence=selection,selection=value,export_hex=(folder/"readback-inputs.json").read_bytes().hex(),inputs_unchanged=True))

    def test_none_unavailable_blocked_held_or_null_create_no_file(self):
        from copy import deepcopy
        host,final=self.frames()
        blocked=deepcopy(self.current);blocked["facts_plan"]["status"]="blocked";blocked["facts_plan"]["plan_input"]["status"]="blocked"
        held=deepcopy(final);held.update(status="held",result=None,artifact=None)
        cases=((host,final,None),(host,final,blocked),(self.summary(held),held,self.current),(self.summary(None,"not_run"),None,self.current))
        with patch.object(self.module,"_conducted_readback_inputs",side_effect=AssertionError("None output0")):
            for h,f,current in cases:
                self.assertIsNone(self.call(h,f,current=current))
        self.assertEqual(list(self.root.iterdir()),[])

    def test_wrong_serializer_pins_and_cross_source_contradictions_refuse_before_output(self):
        from copy import deepcopy
        for field in ("final_bytes","final_lf","exec_pin","execution_status","execution_failure","final_status","final_failure",
                      "artifact_summary","result_binding","file_lf_role","manifest_path","current_hash","method",
                      "result_scalar","artifact_name_type","result_authority","finalizer_physical"):
            host,final=self.frames();current=deepcopy(self.current);method=deepcopy(self.method)
            if field=="final_bytes":host["finalization"]["receipt"]["bytes"]+=1
            elif field=="final_lf":host["finalization"]["receipt"]["sha256"]=sha256((canonical(final)+"\n").encode()).hexdigest()
            elif field=="exec_pin":host["execution"]["receipt"]["sha256"]="0"*64
            elif field=="execution_status":host["execution"]["status"]="failed"
            elif field=="execution_failure":host["execution"]["failure"]=dict(code="other",stage="loop")
            elif field=="final_status":host["finalization"]["result_status"]="incomplete"
            elif field=="final_failure":host["finalization"]["failure"]=None
            elif field=="artifact_summary":host["finalization"]["artifact"]["storage"]["sha256"]="0"*64
            elif field=="result_binding":
                final["result"]["binding"]["runtime_instance_id"]="other";host=self.summary(final)
            elif field=="file_lf_role":
                final["artifact"]["files"][0]["sha256"]=sha256(canonical(final["result"]).encode()).hexdigest();host=self.summary(final)
            elif field=="manifest_path":
                final["artifact"]["storage"]["commit_marker"]="other/manifest.json";host=self.summary(final)
            elif field=="current_hash":current["facts_plan"]["plan_input"]["binding"]["context_sha256"]="d"*64
            elif field=="method":method["method_version"]+=1
            elif field=="result_scalar":
                final["result"]=[];host["finalization"]["result_status"]=None
                raw=canonical(final).encode();host["finalization"]["receipt"]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
            elif field=="artifact_name_type":final["artifact"]["artifact_name"]=7;host=self.summary(final)
            elif field=="result_authority":
                final["result"]["verification"]["execution_authority"]=True
                raw=canonical(final["result"]).encode()
                final["artifact"]["files"][0].update(bytes=len(raw)+1,sha256=sha256(raw+b"\n").hexdigest());host=self.summary(final)
            else:final["verification"]["physical_verified"]=True;host=self.summary(final)
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.call(host,final,current=current,method=method)
            self.assertEqual(list(self.root.iterdir()),[])

    def test_native_caps_and_foreign_inputs_refuse_before_file(self):
        from copy import deepcopy
        for field in ("host","final","current","foreign"):
            host,final=self.frames();current=deepcopy(self.current)
            if field=="host":host["errors"]=[dict(code="x"*69633)]
            elif field=="final":final["input_files"]["padding"]="x"*(2*1024*1024)
            elif field=="current":current["analysis"]["padding"]="x"*(8*1024*1024)
            else:current["analysis"]["foreign"]=object()
            with self.subTest(field=field),self.assertRaises(ValueError):self.call(host,final,current=current)
            self.assertEqual(list(self.root.iterdir()),[])
        oversized=dict(intake_id="x",method=dict(padding="x"*65536))
        with patch.object(self.module,"_conducted_artifact_startup",return_value=oversized),self.assertRaises(ValueError):self.call()
        self.assertEqual(list(self.root.iterdir()),[])

    def test_output_directory_is_explicit_native_local_and_reparse_fault_has_no_write(self):
        from labflow import control_packet_prepare as native
        for folder in ("relative",r"\\server\share",str(self.root/".."/"alias"),str(self.root/"missing")):
            with self.subTest(folder=folder),self.assertRaises((ValueError,OSError)):self.call(folder=folder)
        error=native.ControlPacketPrepareError("packet_prepare_path_invalid")
        with patch.object(native,"_Tree",side_effect=error),patch.object(
                self.module,"_conducted_readback_inputs",side_effect=AssertionError("native rejection write0")) as exported:
            with self.assertRaises(native.ControlPacketPrepareError) as caught:self.call()
        self.assertIs(caught.exception,error);self.assertEqual(exported.call_count,0);self.assertEqual(list(self.root.iterdir()),[])

    def test_existing_partial_file_is_never_overwritten(self):
        import os
        target=self.root/"readback-inputs.json";target.write_bytes(b"original partial\x00\n")
        before=target.stat()
        with self.assertRaises(FileExistsError):self.call()
        after=target.stat();self.assertEqual(target.read_bytes(),b"original partial\x00\n")
        self.assertEqual((before.st_size,before.st_ino,before.st_mtime_ns),(after.st_size,after.st_ino,after.st_mtime_ns))

    def test_partial_first_errors_and_controls_survive_cleanup_error_without_retry(self):
        from labflow.virtual_fleet import rf_signal_waveform_observation_read as cleanup
        opened=Path.open;close=cleanup._close
        for index,error in enumerate((OSError("first"),KeyboardInterrupt(),MemoryError(),SystemExit(7),GeneratorExit())):
            folder=self.root/str(index);folder.mkdir();target=folder/"readback-inputs.json";calls=[]
            class Partial:
                def __enter__(inner):inner.stream=opened(target,"xb");return inner
                def __exit__(inner,*args):return inner.stream.__exit__(*args)
                def write(inner,raw):calls.append(raw);inner.stream.write(raw[:17]);raise error
            def opening(path,*args,**kwargs):return Partial() if path==target else opened(path,*args,**kwargs)
            def closing(backend):close(backend);return RuntimeError("secondary")
            with self.subTest(error=type(error).__name__),patch.object(Path,"open",opening),patch.object(cleanup,"_close",side_effect=closing):
                with self.assertRaises(type(error)) as caught:self.call(folder=folder)
            self.assertIs(caught.exception,error);self.assertEqual(len(calls),1);self.assertEqual(target.read_bytes(),calls[0][:17])

    def test_existing_file_and_byte_budget_projection_refuses_before_write(self):
        from types import SimpleNamespace
        for count,size in ((512,0),(1,32*1024*1024)):
            item=SimpleNamespace(is_file=lambda:True,stat=lambda:SimpleNamespace(st_size=size))
            with patch.object(Path,"rglob",return_value=[item]*count):
                with self.assertRaises(ValueError):self.call()
            self.assertEqual(list(self.root.iterdir()),[])



EVIDENCE_FIRST_FAILURE_OBSERVATIONS = []


class ConductedEvidenceFirstFailureTests(unittest.TestCase):
    """The real writer must retain a write failure through a later close failure."""
    def exercise(self, first=None, last=None, *, existing=False, blocked_parent=False):
        import os
        from labflow import intake_fixture_check as module
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            target=folder/('block/readback-inputs.json' if blocked_parent else 'readback-inputs.json')
            selection=dict(intake_id='first-error-intake', expected_revision=3,
                expected_context_sha256='a'*64, artifact_workspace_root=str(folder/'artifact'),
                artifact_name='first-error-draft', expected_manifest_sha256='b'*64,
                expected_result_sha256='c'*64, run_id='first-error-run', runtime_instance_id='first-error-runtime',
                method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
            expected=dict(expected_revision=3,expected_context_sha256='a'*64,artifact_workspace_root=str(folder/'artifact'),
                artifact_name='first-error-draft',expected_manifest_sha256='b'*64,expected_result_sha256='c'*64,
                run_id='first-error-run',runtime_instance_id='first-error-runtime',
                method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output'))
            raw=(json.dumps(expected,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
            seed=folder/'block' if blocked_parent else target
            def metadata(path):
                value=path.stat()
                return dict(bytes=value.st_size,mtime_ns=value.st_mtime_ns,ctime_ns=value.st_ctime_ns,ino=value.st_ino)
            before=None
            if existing or blocked_parent:
                seed.write_bytes(b'original-native-file\n');before=metadata(seed)
            calls=dict(open=0,write=0,close=0,real_close=0)
            descriptors=[]
            opened_original=Path.open
            class NativeFaultStream:
                def __init__(inner,stream):
                    inner.stream=stream;descriptors.append(stream.fileno())
                def __enter__(inner):
                    return inner
                def write(inner,data):
                    calls['write']+=1
                    self.assertEqual(data,raw)
                    count=inner.stream.write(data[:19] if first is not None else data)
                    inner.stream.flush();os.fsync(inner.stream.fileno())
                    if first is not None:raise first
                    return count
                def close(inner):
                    calls['close']+=1
                    inner.stream.close();calls['real_close']+=1
                    if last is not None:raise last
                def __exit__(inner,*args):
                    inner.close()
            def opened(path,mode='r',*args,**kwargs):
                if path==target:
                    self.assertEqual(mode,'xb');calls['open']+=1
                    return NativeFaultStream(opened_original(path,mode,*args,**kwargs))
                return opened_original(path,mode,*args,**kwargs)
            caught=returned=None
            try:
                with patch.object(Path,'open',opened):
                    if blocked_parent:
                        returned=module._conducted_write(folder,'block/readback-inputs.json',raw)
                    else:
                        returned=module._conducted_readback_inputs(folder,selection)
            except BaseException as error:
                caught=error
            fd_closed=None
            if descriptors:
                try:os.fstat(descriptors[0])
                except OSError:fd_closed=True
                else:fd_closed=False
            actual=target.read_bytes() if target.is_file() else None
            after=metadata(seed) if before is not None else None
            row=dict(target=str(target),fault='native xb/write prefix+flush+fsync/real close, injected exceptions',
                first_type=type(first).__name__ if first is not None else None,
                close_type=type(last).__name__ if last is not None else None,
                observed_type=type(caught).__name__ if caught is not None else None,
                same_primary=first is not None and caught is first,same_secondary=last is not None and caught is last,
                context_is_primary=caught is not None and first is not None and caught.__context__ is first,
                calls=calls,fd_closed=fd_closed,partial_bytes=len(actual) if actual is not None else None,
                raw_hex=actual.hex() if actual is not None else None,
                expected_prefix_hex=raw[:19].hex(),expected_full_hex=raw.hex(),
                original_seed_unchanged=before==after if before is not None else None,
                before=before,after=after,existing=existing,blocked_parent=blocked_parent)
            EVIDENCE_FIRST_FAILURE_OBSERVATIONS.append(row)
            return caught,returned,row

    def test_real_19byte_write_memoryerror_survives_later_close_oserror(self):
        first,last=MemoryError('original native partial write'),OSError('secondary after real close')
        caught,returned,row=self.exercise(first,last)
        self.assertIs(caught,first)
        self.assertEqual(row['calls'],dict(open=1,write=1,close=1,real_close=1))
        self.assertTrue(row['fd_closed']);self.assertEqual(row['partial_bytes'],19)
        self.assertEqual(row['raw_hex'],row['expected_prefix_hex'])

    def test_ordinary_and_controls_keep_first_identity_after_close_controls(self):
        pairs=((ValueError('first'),OSError('close')),(ValueError('first'),KeyboardInterrupt('close')),
            (KeyboardInterrupt('first'),OSError('close')),(SystemExit(41),MemoryError('close')),
            (GeneratorExit('first'),SystemExit(42)),(OSError('first'),GeneratorExit('close')))
        for first,last in pairs:
            with self.subTest(first=type(first).__name__,close=type(last).__name__):
                caught,returned,row=self.exercise(first,last)
                self.assertIs(caught,first)
                self.assertEqual(row['calls'],dict(open=1,write=1,close=1,real_close=1))
                self.assertTrue(row['fd_closed']);self.assertEqual(row['partial_bytes'],19)
                self.assertEqual(row['raw_hex'],row['expected_prefix_hex'])

    def test_close_only_error_or_control_is_original_after_full_native_write(self):
        for last in (OSError('close'),KeyboardInterrupt('close'),MemoryError('close'),SystemExit(43),GeneratorExit('close')):
            with self.subTest(close=type(last).__name__):
                caught,returned,row=self.exercise(last=last)
                self.assertIs(caught,last)
                self.assertEqual(row['calls'],dict(open=1,write=1,close=1,real_close=1))
                self.assertTrue(row['fd_closed']);self.assertEqual(row['raw_hex'],row['expected_full_hex'])

    def test_success_closes_once_and_keeps_original_nine_field_lf_bytes(self):
        caught,returned,row=self.exercise()
        self.assertIsNone(caught);self.assertIsNone(returned)
        self.assertEqual(row['calls'],dict(open=1,write=1,close=1,real_close=1))
        self.assertTrue(row['fd_closed']);self.assertEqual(row['raw_hex'],row['expected_full_hex'])
        value=json.loads(bytes.fromhex(row['raw_hex']))
        self.assertEqual(len(value),9);self.assertNotIn('intake_id',value)

    def test_collision_and_parent_failure_never_open_a_stream_or_change_original(self):
        for existing,blocked in ((True,False),(False,True)):
            with self.subTest(existing=existing,blocked_parent=blocked):
                caught,returned,row=self.exercise(existing=existing,blocked_parent=blocked)
                self.assertIsInstance(caught,OSError)
                if existing:self.assertIsInstance(caught,FileExistsError)
                self.assertTrue(row['original_seed_unchanged'])
                self.assertEqual(row['calls'],dict(open=int(existing),write=0,close=0,real_close=0))
                self.assertIsNone(row['fd_closed'])



TRANSPORT_RECOVERY_OBSERVATIONS = []


class ConductedTransportRecoveryGenuineTests(unittest.TestCase):
    """New link-state faults must reach one real runtime, journal and stored DRAFT."""
    def exercise(self, scenario, ref, decisions, logical, ticks, expected_actions):
        import io
        from contextlib import redirect_stdout
        from hashlib import sha256
        from labflow import intake_fixture_check as module
        from labflow.virtual_fleet import codex_virtual_loop as loop
        from labflow.virtual_fleet.journal import read_operator_journal
        original_prepare=loop._prepare;trials=[]
        def prepare(*args,**kwargs):
            trial=original_prepare(*args,**kwargs);trials.append(trial);return trial
        with tempfile.TemporaryDirectory(prefix='ctr-') as temporary:
            output=Path(temporary)/'flow';stdout=io.StringIO()
            row=dict(case=scenario,ref=ref,origin='new native authored MOCK link-state flow; no real model',output=str(output))
            first=None
            try:
                with patch.object(loop,'_prepare',side_effect=prepare),redirect_stdout(stdout):
                    code=module.main(['--output',str(output),'--conducted-workflow','--document-kind','pdf',
                        '--mock-model','gpt-6.1-sol','--measurement-ref',ref,'--conducted-scenario',scenario])
                row.update(exit=code,stdout=stdout.getvalue(),actual_factory_calls=len(trials))
                summary=json.loads((output/'public-summary.json').read_bytes());row['summary']=summary
                self.assertEqual(summary['runtime_calls'],1)  # unsupported/exit1 is not a passing scenario.
                self.assertEqual(len(trials),1);self.assertEqual(code,1);self.assertEqual(json.loads(stdout.getvalue()),summary)
                self.assertEqual(summary['status'],'stored');self.assertEqual(summary['runtime_scenario'],'persistent_disconnect')
                self.assertEqual(summary['result_status'],'incomplete');self.assertEqual(summary['fixture_acceptance'],'fail')
                self.assertEqual(summary['storage_status'],'complete');self.assertEqual(summary['draft_status'],'DRAFT')
                self.assertIsNone(summary['corrected']);self.assertIs(summary['ai_model_called'],False)
                execution=json.loads((output/'execution-original.json').read_bytes());record=execution['loop']
                final=json.loads((output/'finalizer-original.json').read_bytes());result=final['result'];artifact=final['artifact']
                journal_path=output/'x/operator-journal.jsonl';stored=read_operator_journal(journal_path)
                header=stored['header'];events=stored['events']
                row.update(execution=execution,finalizer=final,journal_header=header,journal_integrity=stored['integrity'])
                self.assertEqual(record['declaration']['scenario'],'persistent_disconnect')
                self.assertEqual(record['status'],'stopped');self.assertEqual(record['termination']['reason'],'policy_stop')
                self.assertEqual(record['termination']['policy_claim'],'blocked')
                report=json.loads((output/'x/legacy-harness-report.json').read_bytes())
                self.assertEqual(report['usage']['decisions'],decisions);self.assertEqual(report['usage']['logical_requests'],logical)
                self.assertEqual(report['usage']['tick_delta'],ticks);self.assertEqual(report['usage']['transport_retries'],0)
                self.assertEqual(record['budget']['producer_calls_started'],decisions);self.assertTrue(stored['complete'])
                self.assertEqual(stored['unresolved_request_ids'],[])
                for bound in (execution['binding'],result['binding'],artifact):
                    self.assertEqual((bound['run_id'],bound['runtime_instance_id']),(header['run_id'],header['runtime_instance_id']))
                self.assertEqual(trials[0].runtime_instance_id,header['runtime_instance_id'])
                author=trials[0].author_record();row['author_state']=author
                self.assertEqual(author['condition'],'persistent_disconnect');self.assertIsNone(author['release_tick'])
                self.assertEqual([(x['device_id'],x['fault'],x['value']) for x in author['author_events']],[('dut','disconnect',True)])
                intents=[x for x in events if x['type']=='intent']
                actions=[('advance' if x['payload']['operation']=='advance' else
                    x['payload']['body']['device_id']+'.'+x['payload']['body']['action']) for x in intents]
                self.assertEqual(actions,expected_actions)
                receipts={x['payload']['request_id']:x['payload']['result'] for x in events if x['type']=='receipt'}
                starts=[x for x in intents if x['payload']['body'].get('device_id')=='dut']
                self.assertEqual(len(starts),1 if scenario=='transport-error' else 2)
                for intent in starts:
                    receipt=receipts[intent['payload']['request_id']]
                    self.assertEqual(receipt['status'],'disconnected');self.assertEqual(receipt['values']['reason'],'device_unavailable')
                selected=next(x for x in events if x['event_id']==ref);row['selected_observation']=selected
                self.assertEqual(selected['type'],'observation')
                before_final=next(x for x in intents if x['payload']['request_id']==selected['payload']['cause_request_id'])
                self.assertEqual(before_final['payload']['operation'],'advance')
                sensor=selected['payload']['observation']['devices']['sensor'];row['invalid_sensor_packet']=sensor
                self.assertEqual(sensor['status'],'invalid')
                self.assertEqual(sensor['values']['outputs'],{})  # original absence, never a fabricated valid measurement.
                if scenario=='recovery-failure':
                    earlier=next(x for x in events if x['event_id']=='event:17')
                    self.assertEqual(earlier['payload']['observation']['devices']['sensor']['status'],'invalid')
                    self.assertLess(earlier['sequence'],starts[1]['sequence'])
                    self.assertGreater(selected['sequence'],starts[1]['sequence'])
                self.assertEqual(result['status'],'incomplete');self.assertEqual(result['failure']['code'],'execution_incomplete')
                self.assertEqual(result['binding']['measurement_ref'],ref)
                self.assertIsNone(result['raw_measurement']);self.assertIsNone(result['calculation']['corrected'])
                self.assertIs(final['execution_authority'],False);self.assertIs(artifact['execution_authority'],False)
                self.assertIs(result['verification']['execution_authority'],False)
                self.assertEqual(result['binding']['journal_file_sha256'],sha256(journal_path.read_bytes()).hexdigest())
                manifest_path=output/artifact['storage']['commit_marker'];manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
                self.assertEqual((len(manifest_raw),sha256(manifest_raw).hexdigest()),
                    (artifact['storage']['bytes'],artifact['storage']['sha256']))
                self.assertEqual(manifest['result_status'],'incomplete')
                self.assertEqual((manifest['run_id'],manifest['runtime_instance_id']),(header['run_id'],header['runtime_instance_id']))
                for item in manifest['files']:
                    raw=(manifest_path.parent/item['path']).read_bytes()
                    self.assertEqual((len(raw),sha256(raw).hexdigest()),(item['bytes'],item['sha256']))
                actual_result=(manifest_path.parent/'result.json').read_bytes()
                self.assertEqual(json.loads(actual_result),result);self.assertTrue(actual_result.endswith(b'\n'))
                self.assertEqual(manifest['result_sha256'],sha256(actual_result[:-1]).hexdigest())
                self.assertIn('DRAFT',(manifest_path.parent/'draft.md').read_text(encoding='utf-8').splitlines()[0])
                startup=json.loads((output/'server-startup-original.json').read_bytes())['conducted_artifact_readback_inputs']
                exported=json.loads((output/'readback-inputs.json').read_bytes())
                self.assertEqual(exported,{key:value for key,value in startup.items() if key!='intake_id'})
                self.assertEqual(startup['expected_manifest_sha256'],artifact['storage']['sha256'])
                row.update(manifest=manifest,selection=startup,success_asserted=True)
            except BaseException as error:
                first=error;row.update(error_type=type(error).__name__,error=str(error),actual_factory_calls=len(trials),stdout=stdout.getvalue())
            finally:
                files={}
                if output.exists():
                    for path in output.rglob('*'):
                        if path.is_file():
                            data=path.read_bytes();info=path.stat()
                            files[path.relative_to(output).as_posix()]=dict(bytes=len(data),sha256=sha256(data).hexdigest(),
                                mtime_ns=info.st_mtime_ns,ino=info.st_ino)
                row['files']=files;TRANSPORT_RECOVERY_OBSERVATIONS.append(row)
            if first is not None:raise first

    def test_1_transport_link_state_unavailable_reaches_native_journal_and_incomplete_draft(self):
        self.exercise('transport-error','event:17',5,4,2,['dut.start','advance','sensor.acquire','advance'])

    def test_2_one_restart_and_remeasurement_stay_invalid_in_same_runtime_and_stored_draft(self):
        self.exercise('recovery-failure','event:29',8,7,3,
            ['dut.start','advance','sensor.acquire','advance','dut.start','sensor.acquire','advance'])



# Opt-in method names keep the existing default cohort unchanged.
_DECLARED_UNSET = object()
WORKFLOW_DECLARED_OBSERVATIONS = []


class WorkflowDeclaredUncertaintyTests(unittest.TestCase):
    def setUp(self):
        import copy
        self.copy = copy.deepcopy
        self.temp = tempfile.TemporaryDirectory(prefix='declared-workflow-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.observed = []
        self.sequence = 0
        self.inputs = dict(components=None, policy=None)

    def tearDown(self):
        from hashlib import sha256
        WORKFLOW_DECLARED_OBSERVATIONS.append(dict(name=self._testMethodName,
            observations=self.observed, provided_seams_only=True, actual_RF=0,
            actual_loop=0, actual_model=0, actual_SQL=0, actual_CLI=0, actual_budget=0,
            output_files=[dict(path=p.relative_to(self.root).as_posix(), bytes=p.stat().st_size,
                sha256=sha256(p.read_bytes()).hexdigest()) for p in sorted(self.root.rglob('*')) if p.is_file()]))

    def module(self):
        from labflow import intake_fixture_check
        return intake_fixture_check

    def legacy(self):
        import importlib.util
        import os
        import sys
        value = os.environ.get('DGM_WORKFLOW_LEGACY_SOURCE')
        self.assertTrue(value, 'Supply the pinned original workflow source for opt-in parity')
        spec = importlib.util.spec_from_file_location('labflow._declared_workflow_original', value)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        # Preserve the original project's schema/catalog locator for copied source.
        module.__file__ = str(Path(__file__).resolve().parents[1] / 'labflow/intake_fixture_check.py')
        return module

    def exercise(self, module=None, inputs=_DECLARED_UNSET, *, primary=None, secondary=None):
        from contextlib import ExitStack
        from hashlib import sha256
        from types import SimpleNamespace
        from labflow.store import canonical
        module = module or self.module()
        self.sequence += 1
        output = self.root / ('flow-' + str(self.sequence))
        plan, method, final = ConductedArtifactStartupTests.values(self, 'incomplete')
        plan['plan'] = dict(source_settings={}, basis_refs={})
        final['result']['calculation']['conformity'] = dict(status='not_assessed', uncertainty_db=None)
        final['result']['failure'] = None
        context = dict(job_id='provided-job', intake_id=plan['binding']['intake_id'], revision=3,
            synthetic=True, documents=[], analysis_context_id='provided-context',
            analysis_contract={}, instructions='Provided boundary only; no actual intake or PDF validation.')
        analysis = dict(schema_version=2, context_id='provided-context', facts=[], missing_fields=[])
        current = dict(context=context, analysis=analysis)
        execution = dict(kind='provided_no_runtime',
            execution=dict(trial_factory_calls=0, producer_calls_started=0))
        calls, passed = {}, []
        class ProvidedText:
            def setFont(self, *a):
                pass
            def textLine(self, *a):
                pass
        class ProvidedCanvas:
            def __init__(self, *a, **k):
                pass
            def beginText(self, *a):
                return ProvidedText()
            def drawText(self, *a):
                pass
            def showPage(self):
                pass
            def save(self):
                pass
        class ProvidedStore:
            def __init__(self, path):
                self.root = Path(path)
        copy = self.copy
        class ProvidedCurrent:
            def __init__(self, root):
                pass
            def current_conducted_plan_context(self, intake_id):
                return copy(current)
        native_json = module._conducted_json
        def evidence(folder, relative, value):
            if secondary is not None and relative == 'failure-original-receipt.json':
                module._conducted_write(folder, relative, b'{"provided-failure":true}\n'[:19])
                raise secondary
            return native_json(folder, relative, value)
        def finalized(original_execution, **options):
            self.assertIs(original_execution, execution)
            passed.append(options)
            folder = output / '.local/conducted-result-artifacts/authored-artifact'
            if primary is not None:
                module._conducted_write(output, folder.relative_to(output) / 'result.pending.json',
                    b'provided-partial-original-data'[:19])
                raise primary
            raw_result = (canonical(final['result']) + '\n').encode()
            raw_draft = b'DRAFT\nProvided finalizer payload; not a genuine writer or measurement.\n'
            raw_manifest = (canonical(dict(kind='provided_manifest', files=['result.json', 'draft.md'],
                result_sha256=sha256(raw_result).hexdigest(), draft_sha256=sha256(raw_draft).hexdigest(),
                applied_to_result=False)) + '\n').encode()
            artifact = final['artifact']
            artifact['storage'].update(bytes=len(raw_manifest), sha256=sha256(raw_manifest).hexdigest())
            artifact['files'] = [dict(path=(folder.relative_to(output) / leaf).as_posix(),
                bytes=len(raw), sha256=sha256(raw).hexdigest(), media_type=media)
                for leaf, raw, media in [('result.json', raw_result, 'application/json'),
                                        ('draft.md', raw_draft, 'text/markdown')]]
            for leaf, raw in [('result.json', raw_result), ('draft.md', raw_draft), ('manifest.json', raw_manifest)]:
                module._conducted_write(output, folder.relative_to(output) / leaf, raw)
            return final
        options = dict(measurement_ref='event:explicit-provided', mock_model='gpt-6.1-sol')
        if inputs is not _DECLARED_UNSET:
            options['uncertainty_inputs'] = inputs
        try:
            with ExitStack() as stack:
                patches = [
                    patch.object(module, '_conducted_mock_compiler', return_value=output / 'not-executed-compiler'),
                    patch.object(module, '_compile_conducted_mock', return_value=output / 'not-executed-mock'),
                    patch.object(module, 'Store', ProvidedStore),
                    patch.object(module, 'register_source'),
                    patch.object(module, 'scan_source', return_value=dict(accepted=[dict(intake_id=context['intake_id'], revision=3)])),
                    patch.object(module, 'respond'),
                    patch.object(module, '_scripted_pdf_analysis', return_value=analysis),
                    patch.object(module, '_conducted_json', side_effect=evidence),
                    patch.object(module.uuid, 'uuid4', return_value=SimpleNamespace(hex='1' * 32)),
                    patch('reportlab.pdfgen.canvas.Canvas', ProvidedCanvas),
                    patch('labflow.intake_jobs.claim_job', return_value=dict(context, token='provided-token')),
                    patch('labflow.intake_jobs.complete_job'),
                    patch('labflow.intake_jobs.fail_job'),
                    patch('labflow.intake_model_boundary.build_analysis_prompt', return_value=dict(kind='provided_prompt')),
                    patch('labflow.intake_model_boundary.decode_analysis_response', return_value=analysis),
                    patch('labflow.intake_facts_to_conducted_plan.build_conducted_plan_from_intake_facts',
                        return_value=dict(status='ready_for_simulation', plan_input=plan)),
                    patch('labflow.intake_plan_virtual_execution.run_intake_plan_virtual_execution', return_value=execution),
                    patch('labflow.conducted_execution_result_finalizer.finalize_conducted_execution_result', side_effect=finalized),
                    patch('labflow.ui_read_model.IntakeReadModel', ProvidedCurrent)]
                for item in patches:
                    stack.enter_context(item)
                result = module.run_conducted_flow(output, **options)
            return result, passed, output
        finally:
            self.observed.append(dict(folder=output.name, finalizer_calls=len(passed),
                finalizer_keywords=[list(value) for value in passed],
                forwarded=[self.copy(value.get('uncertainty_inputs')) for value in passed],
                primary=None if primary is None else type(primary).__name__,
                secondary=None if secondary is None else type(secondary).__name__,
                genuine_PDF_Store_plan_execution_finalizer=False))

    def declared_explicit_native_copy_reaches_original_finalizer_boundary(self):
        module = self.module()
        original = self.copy(self.inputs)
        with patch.object(module, '_conducted_export_frame', wraps=module._conducted_export_frame) as snapshot:
            try:
                result, passed, output = self.exercise(inputs=self.inputs)
            except TypeError as error:
                self.fail('Explicit uncertainty_inputs must reach the existing finalizer boundary: ' + str(error))
        self.assertEqual(snapshot.call_count, 1)
        self.assertEqual(snapshot.call_args.args[1], 262144)
        self.assertEqual(len(passed), 1)
        self.assertEqual(passed[0]['uncertainty_inputs'], original)
        self.assertIsNot(passed[0]['uncertainty_inputs'], self.inputs)
        passed[0]['uncertainty_inputs']['components'] = 'caller-alias-probe'
        self.assertEqual(self.inputs, original)
        self.assertEqual(result['summary']['result_status'], 'incomplete')
        self.assertEqual(result['summary']['fixture_acceptance'], 'fail')
        self.assertEqual(result['summary']['draft_status'], 'DRAFT')
        saved = json.loads((output / 'finalizer-original.json').read_bytes())
        self.assertIsNone(saved['result']['calculation']['conformity']['uncertainty_db'])
        self.assertEqual(set(p.name for p in (output / '.local/conducted-result-artifacts/authored-artifact').iterdir()),
            {'result.json', 'draft.md', 'manifest.json'})

    def declared_omitted_none_keep_original_kwargs_summary_and_provided_three_bytes(self):
        from labflow.store import canonical
        original, original_calls, original_root = self.exercise(self.legacy())
        expected = ['expected_execution_sha256', 'evidence_dir', 'measurement_ref', 'workspace_root', 'artifact_name']
        self.assertEqual(list(original_calls[0]), expected)
        prefix = '.local/conducted-result-artifacts/authored-artifact'
        for label, value in [('omitted', _DECLARED_UNSET), ('none', None)]:
            with self.subTest(mode=label):
                module = self.module()
                with patch.object(module, '_conducted_export_frame', wraps=module._conducted_export_frame) as snapshot:
                    result, calls, root = self.exercise(inputs=value)
                self.assertEqual(snapshot.call_count, 0)
                self.assertEqual(list(calls[0]), expected)
                self.assertEqual(canonical(result['summary']), canonical(original['summary']))
                self.assertEqual((root / 'public-summary.json').read_bytes(),
                    (original_root / 'public-summary.json').read_bytes())
                for leaf in ('result.json', 'draft.md', 'manifest.json'):
                    self.assertEqual((root / prefix / leaf).read_bytes(), (original_root / prefix / leaf).read_bytes())

    def declared_invalid_native_inputs_close_before_output_compiler_store_and_runtime(self):
        module = self.module()
        hooks = []
        class Foreign(dict):
            def __iter__(self):
                hooks.append('iter')
                raise AssertionError('foreign hook')
            def __deepcopy__(self, memo):
                hooks.append('deepcopy')
                raise AssertionError('foreign hook')
        cycle = {}
        cycle['cycle'] = cycle
        for label, value in [('foreign', Foreign()), ('cycle', cycle),
                             ('nonfinite', float('inf')), ('oversize', 'x' * 262145)]:
            with self.subTest(case=label):
                output = self.root / label
                with patch.object(module, '_conducted_mock_compiler') as compiler, patch.object(module, 'Store') as store, \
                        patch('labflow.intake_plan_virtual_execution.run_intake_plan_virtual_execution') as runtime, \
                        patch('labflow.conducted_execution_result_finalizer.finalize_conducted_execution_result') as finalizer:
                    with self.assertRaises(ValueError) as got:
                        module.run_conducted_flow(output, uncertainty_inputs=value)
                self.assertEqual(str(got.exception), 'conducted_workflow_readback_export_invalid')
                self.assertFalse(output.exists())
                for boundary in (compiler, store, runtime, finalizer):
                    self.assertEqual(boundary.call_count, 0)
        with patch.object(module, '_conducted_export_frame') as snapshot:
            with self.assertRaisesRegex(ValueError, '^conducted_workflow_scenario_unsupported$'):
                module.run_conducted_flow(self.root / 'scenario', scenario='unlisted', uncertainty_inputs=Foreign())
        self.assertEqual(snapshot.call_count, 0)
        control = MemoryError()
        with patch.object(module, '_conducted_export_frame', side_effect=control), \
                patch.object(module, '_conducted_mock_compiler') as compiler:
            with self.assertRaises(MemoryError) as got:
                module.run_conducted_flow(self.root / 'control', uncertainty_inputs=self.inputs)
        self.assertIs(got.exception, control)
        self.assertEqual(compiler.call_count, 0)
        self.assertFalse((self.root / 'control').exists())
        self.assertEqual(hooks, [])
        self.observed.append(dict(invalid=['foreign', 'cycle', 'nonfinite', 'oversize'],
            before_output_compiler_Store_runtime_finalizer=True, hooks=hooks, existing_scenario_error_first=True))

    def declared_finalizer_first_errors_controls_and_partial_are_preserved(self):
        module = self.module()
        for primary in (KeyboardInterrupt(), SystemExit(7), GeneratorExit(), MemoryError(), OSError('provided-first')):
            with self.subTest(primary=type(primary).__name__):
                primary.receipt = dict(kind='provided_finalizer_failure', status='held', result=None)
                primary.code = 'provided_finalizer_first_failure'
                secondary = MemoryError() if type(primary) is OSError else None
                before = self.sequence
                with self.assertRaises(type(primary)) as got:
                    self.exercise(inputs=self.inputs, primary=primary, secondary=secondary)
                self.assertIs(got.exception, primary)
                output = self.root / ('flow-' + str(before + 1))
                partial = output / '.local/conducted-result-artifacts/authored-artifact/result.pending.json'
                self.assertEqual(partial.read_bytes(), b'provided-partial-original-data'[:19])
                self.assertFalse((partial.parent / 'manifest.json').exists())
                self.assertEqual(len(list(partial.parent.iterdir())), 1)
                if secondary is None:
                    self.assertEqual(json.loads((output / 'failure-original-receipt.json').read_bytes()), primary.receipt)
                    self.assertEqual(json.loads((output / 'failure.json').read_bytes())['code'], primary.code)
                else:
                    self.assertEqual((output / 'failure-original-receipt.json').stat().st_size, 19)



class WorkflowUncertaintyAdmissionTests(WorkflowDeclaredUncertaintyTests):
    """Top-shape admission only; downstream execution remains provided, not RF."""

    def test_malformed_top_shapes_reject_before_output_resolution_and_boundaries(self):
        module = self.module()
        malformed = [[], ['components', 'policy'], '', 'native-but-not-a-budget',
            0, 1.25, True, False, {}, {'components': None}, {'policy': None},
            {'components': None, 'policy': None, 'extra': False}]
        for index, value in enumerate(malformed):
            with self.subTest(value=value):
                output = self.root / ('invalid-top-' + str(index))
                error = None
                with patch.object(module, 'Path', wraps=Path) as path, \
                        patch.object(module, '_conducted_mock_compiler', return_value=None) as compiler, \
                        patch.object(module, '_compile_conducted_mock') as compile_mock, \
                        patch.object(module, 'Store') as store, \
                        patch('labflow.intake_plan_virtual_execution.run_intake_plan_virtual_execution') as runtime, \
                        patch('labflow.conducted_execution_result_finalizer.finalize_conducted_execution_result') as finalizer:
                    try:
                        module.run_conducted_flow(output, uncertainty_inputs=value,
                            measurement_ref='event:explicit', mock_model='gpt-6.1-sol')
                    except ValueError as caught:
                        error = caught
                boundaries = dict(path=path.call_count, compiler=compiler.call_count,
                    compile=compile_mock.call_count, Store=store.call_count,
                    runtime=runtime.call_count, finalizer=finalizer.call_count)
                self.observed.append(dict(input=value, boundaries=boundaries,
                    output_exists=output.exists(), error=None if error is None else str(error)))
                self.assertEqual(None if error is None else str(error),
                    'conducted_workflow_readback_export_invalid')
                self.assertFalse(output.exists())
                self.assertEqual(boundaries, dict.fromkeys(boundaries, 0))

    def test_exact_two_deep_inputs_forward_once_without_semantic_repair(self):
        values = [dict(components=None, policy=None),
            dict(components=None, policy=dict(correlation_assumption='unsupported')),
            dict(components=[], policy=dict(correlation_assumption='correlated',
                coverage_factor_evidence_refs=[], correlation_evidence_refs=[]))]
        module = self.module()
        for value in values:
            with self.subTest(value=value):
                original = self.copy(value)
                with patch.object(module, '_conducted_export_frame', wraps=module._conducted_export_frame) as snapshot:
                    result, passed, output = self.exercise(inputs=value)
                self.assertEqual(snapshot.call_count, 1)
                self.assertEqual(snapshot.call_args.args[1], 262144)
                self.assertEqual(len(passed), 1)
                self.assertEqual(passed[0]['uncertainty_inputs'], original)
                self.assertIsNot(passed[0]['uncertainty_inputs'], value)
                self.assertEqual(value, original)
                saved = json.loads((output / 'finalizer-original.json').read_bytes())
                self.assertEqual(saved['result']['calculation']['conformity']['status'], 'not_assessed')
                self.assertIsNone(saved['result']['calculation']['conformity']['uncertainty_db'])
                self.assertEqual(result['summary']['result_status'], 'incomplete')
                self.assertEqual(result['summary']['fixture_acceptance'], 'fail')

    def test_scenario_and_malformed_input_precede_existing_output_check(self):
        module = self.module()
        output = self.root / 'retained-existing'
        output.mkdir()
        marker = output / 'original.txt'
        marker.write_bytes(b'original remains unchanged')
        with patch.object(module, '_conducted_export_frame') as snapshot, \
                patch.object(module, 'Path', wraps=Path) as path:
            with self.assertRaisesRegex(ValueError, '^conducted_workflow_scenario_unsupported$'):
                module.run_conducted_flow(output, scenario='unlisted', uncertainty_inputs=[])
        self.assertEqual(snapshot.call_count, 0)
        self.assertEqual(path.call_count, 0)
        with patch.object(module, 'Path', wraps=Path) as path, \
                patch.object(module, '_conducted_mock_compiler') as compiler:
            with self.assertRaisesRegex(ValueError, '^conducted_workflow_readback_export_invalid$'):
                module.run_conducted_flow(output, uncertainty_inputs=[])
        self.assertEqual(path.call_count, 0)
        self.assertEqual(compiler.call_count, 0)
        self.assertEqual(marker.read_bytes(), b'original remains unchanged')
        self.assertEqual(list(output.iterdir()), [marker])


if __name__ == '__main__':
    unittest.main()
