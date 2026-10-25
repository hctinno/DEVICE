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

    def test_unavailable_fault_seams_are_unsupported_without_store_or_fake_device_result(self):
        from labflow.intake_fixture_check import run_conducted_flow
        with tempfile.TemporaryDirectory() as temporary:
            for scenario in ('transport-error', 'recovery-failure'):
                with self.subTest(scenario=scenario):
                    result = run_conducted_flow(Path(temporary) / scenario, measurement_ref='event:17',
                        mock_model='gpt-6.1-sol', scenario=scenario)
                    self.assertEqual(result['summary']['status'], 'unsupported')
                    self.assertEqual(result['summary']['runtime_calls'], 0)
                    self.assertIsNone(result['workspace'])
                    self.assertEqual(result['summary']['draft_status'], 'not_run')
                    self.assertIn('public_seam', result['summary'])
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


if __name__ == '__main__':
    unittest.main()
