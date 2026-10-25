"""UI contracts use the real intake service and a separate synthetic store."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job, complete_job, respond
from labflow.store import Store
from labflow.ui_read_model import IntakeReadModel, ReadModelError


class IntakeFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.inbox = self.root / 'input'
        self.inbox.mkdir()
        self.store = Store(self.root / 'state')
        register_source(self.store, 'UI', self.inbox, synthetic=True, settle_seconds=1)

    def accept(self, name='order'):
        folder = self.inbox / name
        folder.mkdir(exist_ok=True)
        (folder / 'request.txt').write_text(
            'Remote control <script>window.pwned=true</script>\nMarket: EU\nPurpose: development\n', encoding='utf-8')
        scan_source(self.store, 'UI', now=100)
        return scan_source(self.store, 'UI', now=101)['accepted'][-1]['intake_id']

    def finish(self):
        job = claim_job(self.store, 'ui-fixture', now=102)
        doc = job['documents'][0]
        facts = []
        for field, value, line in [('product_type', 'remote_control', 1), ('market', 'EU', 2), ('purpose', 'development', 3)]:
            facts.append({'field': field, 'value': value, 'status': 'explicit', 'evidence': [{
                'path': doc['path'], 'sha256': doc['sha256'], 'line_start': line, 'line_end': line,
                'quote': doc['text'].splitlines()[line-1], 'role': 'request'}]})
        complete_job(self.store, job['job_id'], job['token'], {
            'schema_version': 1, 'producer': {'kind': 'fixture', 'name': 'ui-contract'},
            'identity': 'single', 'facts': facts, 'missing_fields': ['firmware']}, now=103)
        return job['intake_id']


class ReadModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixture = IntakeFixture(self.tmp.name)
        self.model = IntakeReadModel(self.fixture.store.root)

    def test_existing_empty_store_is_a_successful_empty_result(self):
        result = self.model.snapshot()
        self.assertEqual(result['intakes'], [])
        self.assertEqual(result['notifications'], [])
        self.assertEqual(result['schema_version'], 1)

    def test_missing_store_does_not_create_state_or_become_empty_success(self):
        missing = Path(self.tmp.name) / 'does-not-exist'
        with self.assertRaises(ReadModelError) as error:
            IntakeReadModel(missing).snapshot()
        self.assertEqual(error.exception.code, 'store_missing')
        self.assertFalse(missing.exists())

    def test_list_and_detail_retain_service_evidence_jobs_and_local_notices(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        result = self.model.snapshot(intake_id)
        self.assertEqual(result['intake']['intake_id'], intake_id)
        self.assertTrue(result['intake']['synthetic'])
        self.assertEqual(result['intake']['measurement_support'], 'unverified')
        self.assertEqual(result['intake']['jobs'][0]['state'], 'completed')
        self.assertNotIn('token', result['intake']['jobs'][0])
        self.assertEqual(result['notifications'][0]['revision'], 1)
        self.assertEqual(result['intake']['analysis']['questions'][0]['key'], 'missing_firmware')
        self.assertIn('<script>', result['intake']['analysis']['submitted']['facts'][0]['evidence'][0]['quote'])
        self.assertEqual(self.model.snapshot()['intakes'][0], result['intake'])

    def test_reading_never_initializes_migrates_or_changes_the_database(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        respond(self.fixture.store, 'DEFER-UI', 'defer', intake_id=intake_id)
        before = hashlib.sha256(self.fixture.store.db.read_bytes()).hexdigest()
        result = self.model.snapshot(intake_id)
        self.assertTrue(result['intake']['deferred'])
        self.assertEqual(result['intake']['analysis']['next_action'], 'deferred')
        self.assertEqual(hashlib.sha256(self.fixture.store.db.read_bytes()).hexdigest(), before)

    def test_unknown_intake_and_invalid_schema_are_explicit_errors(self):
        with self.assertRaises(ReadModelError) as error:
            self.model.snapshot('I-absent')
        self.assertEqual(error.exception.code, 'intake_not_found')
        self.fixture.store.db.write_bytes(b'not a sqlite database')
        with self.assertRaises(ReadModelError) as error:
            self.model.snapshot()
        self.assertEqual(error.exception.code, 'store_unavailable')

    def test_read_connection_blocks_an_accidental_mutating_query(self):
        self.fixture.accept()
        before = self.fixture.store.db.read_bytes()

        def unexpected_write(store, intake_id):
            with store.connection() as con:
                con.execute('UPDATE intakes SET delegated=1')

        with patch('labflow.ui_read_model.intake_status', side_effect=unexpected_write):
            with self.assertRaises(ReadModelError) as error:
                self.model.snapshot()
        self.assertEqual(error.exception.code, 'store_unavailable')
        self.assertEqual(self.fixture.store.db.read_bytes(), before)

    def test_new_revision_does_not_relabel_old_analysis_or_notices(self):
        intake_id = self.fixture.accept()
        self.fixture.finish()
        (self.fixture.inbox / 'order' / 'supplement.txt').write_text('Synthetic supplement', encoding='utf-8')
        scan_source(self.fixture.store, 'UI', now=120)
        scan_source(self.fixture.store, 'UI', now=121)
        result = self.model.snapshot(intake_id)
        self.assertEqual(result['intake']['revision'], 2)
        self.assertIsNone(result['intake']['analysis'])
        self.assertEqual(result['intake']['jobs'][0]['state'], 'completed')
        self.assertEqual(result['intake']['jobs'][1]['state'], 'queued')
        self.assertEqual(result['notifications'][0]['revision'], 1)


def conducted_context_fixture(root, *, kind='pdf', completed=True, synthetic=True):
    """Own fresh synthetic bytes through genuine retention/completion; no model."""
    from labflow.intake_fixture_check import _write_request
    from labflow.intake_worker import SyntheticTextProvider
    root=Path(root);inbox=root/'inbox';inbox.mkdir(parents=True)
    _write_request(inbox/'request',kind)
    store=Store(root/'state');register_source(store,'PLAN-PREVIEW-SYN',inbox,synthetic=synthetic,settle_seconds=.001)
    scan_source(store,'PLAN-PREVIEW-SYN',now=100)
    intake_id=scan_source(store,'PLAN-PREVIEW-SYN',now=100.01)['accepted'][0]['intake_id']
    job=claim_job(store,'plan-preview-fixture',now=101)
    context={key:job[key] for key in ('job_id','intake_id','revision','synthetic','documents','analysis_context_id','analysis_contract','instructions')}
    analysis=SyntheticTextProvider().analyze({**context,'synthetic':True})
    if not synthetic:analysis['producer']={'kind':'manual','name':'synthetic-test-data-only'}
    if completed:complete_job(store,job['job_id'],job['token'],analysis,now=102)
    return {'store':store,'intake_id':intake_id,'context':context,'analysis':analysis,'inbox':inbox}


class ConductedPlanContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='conducted-context-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def reader(self, fixture):
        model=IntakeReadModel(fixture['store'].root)
        self.assertTrue(callable(getattr(model,'current_conducted_plan_context',None)),'missing genuine RO conducted context getter')
        return model.current_conducted_plan_context

    def test_genuine_current_V2_PDF_returns_native_context_and_submission_without_replaying_a_prompt(self):
        from labflow.intake_model_boundary import build_analysis_prompt
        fixture=conducted_context_fixture(self.root/'valid');native=self.reader(fixture)(fixture['intake_id'])
        self.assertEqual(set(native),{'context','analysis'})
        self.assertEqual(native['analysis'],fixture['analysis']);self.assertEqual(native['context']['documents'],fixture['context']['documents'])
        self.assertEqual(native['context']['analysis_context_id'],fixture['context']['analysis_context_id'])
        self.assertNotEqual(native['context']['instructions'],fixture['context']['instructions'])
        prompt=build_analysis_prompt(native['context'],producer_name='current-readonly-plan')
        self.assertEqual(json.loads(prompt['messages'][1]['content']),native['context'])
        native['context']['documents'].clear()
        self.assertTrue(self.reader(fixture)(fixture['intake_id'])['context']['documents'])

    def test_RO_getter_never_initializes_claims_prepares_retains_or_runs_and_leaves_database_unchanged(self):
        fixture=conducted_context_fixture(self.root/'readonly');reader=self.reader(fixture);before=fixture['store'].db.read_bytes()
        with ExitStack() as stack:
            for target in ('labflow.store.Store.__init__','labflow.intake_jobs.claim_job','labflow.intake_documents.prepare_analysis_documents','labflow.intake_documents._retain','labflow.intake_worker.run_worker'):
                stack.enter_context(patch(target,side_effect=AssertionError('read-only preview entered '+target)))
            native=reader(fixture['intake_id'])
        self.assertEqual(native['context']['revision'],1);self.assertEqual(fixture['store'].db.read_bytes(),before)

    def test_TXT_V1_nonsynthetic_and_incomplete_are_explicit_unavailable(self):
        for index,options in enumerate(({'kind':'text'},{'synthetic':False},{'completed':False})):
            fixture=conducted_context_fixture(self.root/str(index),**options);reader=self.reader(fixture)
            with self.subTest(options=options),self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
            self.assertIn(error.exception.code,('intake_conducted_preview_v2_pdf_required','intake_conducted_preview_synthetic_required','intake_conducted_preview_analysis_unavailable'))

    def test_new_revision_and_changed_source_never_reuse_a_completed_native_context(self):
        fixture=conducted_context_fixture(self.root/'revision');reader=self.reader(fixture)
        self.assertEqual(reader(fixture['intake_id'])['context']['revision'],1)
        (fixture['inbox']/'request'/'supplement.txt').write_text('synthetic revision2',encoding='utf-8')
        scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120);scan_source(fixture['store'],'PLAN-PREVIEW-SYN',now=120.01)
        with self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
        self.assertEqual(error.exception.code,'intake_conducted_preview_analysis_unavailable')
        fixture=conducted_context_fixture(self.root/'source');reader=self.reader(fixture)
        blob=fixture['store'].blob_path(fixture['context']['documents'][0]['sha256']);blob.write_bytes(blob.read_bytes()+b'changed')
        with self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
        self.assertEqual(error.exception.code,'intake_conducted_preview_source_invalid')

    def test_control_exception_from_current_capture_is_not_changed_to_unavailable(self):
        fixture=conducted_context_fixture(self.root/'control');reader=self.reader(fixture)
        with patch('labflow.intake_reference_snapshot.capture_intake_reference_snapshot_in_transaction',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):
            reader(fixture['intake_id'])

    def test_unconfirmed_blob_provenance_cannot_become_a_synthetic_planning_context(self):
        fixture=conducted_context_fixture(self.root/'provenance');reader=self.reader(fixture)
        with fixture['store'].connection() as con:
            con.execute('UPDATE blobs SET synthetic=0 WHERE sha256=?',(fixture['context']['documents'][0]['sha256'],))
        with self.assertRaises(ReadModelError) as error:reader(fixture['intake_id'])
        self.assertEqual(error.exception.code,'intake_conducted_preview_synthetic_required')



def provided_result_fixture(fixture):
    """Typed public result snapshot, not a D3 builder/execution observation."""
    from copy import deepcopy
    model=IntakeReadModel(fixture['store'].root)
    settings=dict(frequency_hz=915000000,power_dbm=-4,bandwidth_hz=1000000,duty_cycle=1,modulation='CW-synthetic',crest_factor_db=0)
    basis={k:dict(kind='developer_declared_synthetic',value=v,unit=u,evidence=[]) for (k,v),u in zip(settings.items(),['Hz','dBm','Hz','ratio','label','dB'])}
    plan=model.conducted_plan_preview(fixture['intake_id'],dict(intake_id=fixture['intake_id'],revision=1,source_settings=settings,basis=basis,method=dict(method_id='conducted_synthetic',method_version=1,metric='on',reference_plane='source_output')))['plan_input']
    canonical=lambda value:hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    report=dict(schema_version=1,kind='virtual_fleet_harness_result',run_id='provided-run',runtime_instance_id='provided-runtime',synthetic=True,hardware_verified=False,ai_model_called=False,policy=dict(kind='fixture',id='typed-provided'),termination=dict(reason='policy_stop',policy_claim='completed'),task_outcome='not_assessed',cleanup=dict(status='not_assessed',evidence_refs=[]),usage=dict(decisions=0,logical_requests=0,transport_retries=0,tick_delta=0,reserved_ticks=0,elapsed_ms=0),evidence=dict(measurement_refs=['provided-event'],operator_transcript_ref='provided-journal'),unresolved_request_ids=[],assessment=dict(status='not_assessed',verdict=None,evaluator_id=None,evidence_refs=[],summary_code=None))
    edge=dict(source=dict(device_id='dut',port='rf_out'),target=dict(device_id='sensor',port='rf_in'),kind='rf')
    topology=dict(devices=[dict(id='dut',profile_id='provided-dut'),dict(id='sensor',profile_id='provided-sensor')],connections=[edge])
    packet=dict(status='ok',valid=True,value=-4,unit='dBm',frequency_hz=915000000,power_dbm=-4,duty_cycle=1,crest_factor_db=0,acquisition_tick=0,acquisition_setup_revision=0,source_id='sensor',provided_extra={'zero':0})
    result=dict(schema_version=1,kind='conducted_twin_result',status='recorded',binding=dict(plan_input=plan,run_report=report,plan_input_sha256=canonical(plan),setup_sha256=canonical([]),journal_file_sha256='a'*64,journal_head_sha256='b'*64,report_sha256=canonical(report),topology_sha256=canonical(topology),run_id='provided-run',runtime_instance_id='provided-runtime',measurement_ref='provided-event'),raw_measurement=dict(packet=packet,event_id='provided-event',sequence=1,device_id='sensor',tick=0,setup_revision=0,quantity=dict(metric='on',reference_plane='sensor_input',loss_compensation_applied=False,loss_compensation_sign=1),reference_plane='sensor_input'),setup_provenance=dict(records=[],topology=topology,path=[edge]),calculation=dict(raw_power_w=dict(value=0.00039810717055349735,unit='W'),raw_reference_plane='sensor_input',correction_ledger=[],target_reference_plane='source_output',corrected=dict(value=-4,unit='dBm',power_w=0.00039810717055349735),conformity=dict(status='not_assessed',verdict=None,numeric_limit_dbm=None,uncertainty_db=None)),gaps=[],failure=None,verification=dict(synthetic=True,hardware_verified=False,physical_verified=False,source_bytes='not_reopened',method_approval='not_assessed',trust_scope='provided_host_snapshots_and_hash_consistency',execution_authority=False))
    return dict(intake_id=fixture['intake_id'],revision=1,expected_current_binding=deepcopy(plan['binding']),result=result)


class ConductedResultReadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='provided-result-');self.addCleanup(self.temp.cleanup)
        self.fixture=conducted_context_fixture(Path(self.temp.name));self.model=IntakeReadModel(self.fixture['store'].root)
        self.snapshot=provided_result_fixture(self.fixture)

    def read(self):
        self.assertTrue(callable(getattr(self.model,'conducted_result_view',None)),'missing provided result readonly getter')
        return self.model.conducted_result_view(self.fixture['intake_id'],self.snapshot)

    def test_provided_snapshot_original_result_current_binding_and_zero_are_preserved(self):
        before=json.loads(json.dumps(self.snapshot));database=self.fixture['store'].db.read_bytes()
        value=self.read();self.assertEqual(value['source_kind'],'provided_snapshot');self.assertEqual(value['relation']['status'],'matched')
        self.assertEqual(value['result'],before['result']);self.assertEqual(value['expected_current_binding'],before['expected_current_binding'])
        self.assertEqual(value['result']['raw_measurement']['tick'],0);self.assertEqual(value['result']['calculation']['conformity']['verdict'],None)
        value['result']['raw_measurement']['packet']['value']=88
        self.assertEqual(self.read()['result'],before['result']);self.assertEqual(self.snapshot,before);self.assertEqual(self.fixture['store'].db.read_bytes(),database)

    def test_invalid_original_and_partial_generated_fields_remain_json_not_cast(self):
        result=self.snapshot['result'];result.update(status='invalid',binding={},failure=dict(code='measurement_invalid',field='observation.sensor'),gaps=[None,42,{'malformed':'original'}])
        result['raw_measurement']['packet']={'status':'bad','value':'-3e7','unit':None,'extra':[0,False]}
        result['raw_measurement']['quantity']=['malformed',0];result['raw_measurement']['tick']='kept'
        result['setup_provenance']['records']={'bad':'original'};result['setup_provenance']['topology']=['kept']
        result['calculation']['corrected']=None
        value=self.read();self.assertEqual(value['result'],result);self.assertEqual(value['relation']['status'],'blocked')
        self.assertIn('result_plan_binding_unavailable',value['relation']['reasons'])
        result.update(status='incomplete',binding={'plan_input':provided_result_fixture(self.fixture)['result']['binding']['plan_input'],'run_report':None},failure=dict(code='setup_partial',field='setup_snapshot'))
        result['gaps']=[dict(code='setup_partial',field='setup_snapshot',provided=None,blocking=True)]
        self.assertEqual(self.read()['result'],result)

    def test_unknown_normal_gap_or_failure_path_is_rejected_but_invalid_original_gaps_are_opaque(self):
        from copy import deepcopy
        original=deepcopy(self.snapshot)
        for fault in ['gap','d1_gap_path','failure_path','nested_failure_path','original_report_shape','topology']:
            self.snapshot=deepcopy(original)
            if fault=='gap':self.snapshot['result']['gaps']=[dict(code='future',field='quantity',provided=None,blocking=False)]
            elif fault=='d1_gap_path':self.snapshot['result']['gaps']=[dict(code='missing_setting',field='future_private_path',provided=None,blocking=False)]
            elif fault=='nested_failure_path':self.snapshot['result'].update(status='incomplete',failure=dict(code='setup_partial',field='plan_input.plan.future'))
            elif fault=='original_report_shape':self.snapshot['result']['binding']['run_report']={}
            elif fault=='failure_path':self.snapshot['result'].update(status='incomplete',failure=dict(code='setup_partial',field='future_private_path'))
            else:self.snapshot['result']['setup_provenance']['topology']={}
            with self.subTest(fault=fault),self.assertRaises(ReadModelError):self.read()

    def test_missing_expected_binding_revision_context_and_original_plan_hash_block_with_reasons(self):
        from copy import deepcopy
        original=deepcopy(self.snapshot)
        for fault in ['missing','revision','context','plan_hash','result_hash']:
            self.snapshot=deepcopy(original)
            if fault=='missing':self.snapshot['expected_current_binding']=None
            elif fault=='revision':self.snapshot['revision']=2
            elif fault=='context':self.snapshot['expected_current_binding']['context_sha256']='f'*64
            elif fault=='plan_hash':self.snapshot['result']['binding']['plan_input']['plan']['source_settings']['power_dbm']=0
            else:self.snapshot['result']['binding']['report_sha256']='f'*64
            with self.subTest(fault=fault):
                value=self.read();self.assertEqual(value['relation']['status'],'blocked');self.assertTrue(value['relation']['reasons']);self.assertEqual(value['result'],self.snapshot['result'])

    def test_unknown_contract_or_authority_never_publishes_and_original_source_is_rechecked(self):
        from copy import deepcopy
        original=deepcopy(self.snapshot)
        for fault in ['extra','authority','failure','conformity']:
            self.snapshot=deepcopy(original)
            if fault=='extra':self.snapshot['result']['extra']='future'
            elif fault=='authority':self.snapshot['result']['verification']['execution_authority']=True
            elif fault=='failure':self.snapshot['result'].update(status='invalid',failure={'code':'future','field':'input'})
            else:self.snapshot['result']['calculation']['conformity']['verdict']='pass'
            with self.subTest(fault=fault),self.assertRaises(ReadModelError):self.read()
        self.snapshot=original
        self.fixture['store'].blob_path(self.fixture['context']['documents'][0]['sha256']).write_bytes(b'changed')
        with self.assertRaises(ReadModelError):self.read()


if __name__ == '__main__':
    unittest.main()
