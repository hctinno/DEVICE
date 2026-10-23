import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
import subprocess
import sys
from unittest.mock import patch

from labflow.store import Store
from labflow.intake import import_package
from labflow.calculations import calculate
from labflow.workflow import create_case, register_method, add_plan, record_run, evaluate, case_status, review_method, review_run
from labflow.reporting import render_report


def package(path, payload=b'public regulation fixture', *, document_id='DOC-1', package_id='PKG-1', member='originals/source.txt', mutate=None, extras=None):
    record={'document_id':document_id,'request_ids':['FCC-PART-15'],'title':'Fixture source',
        'kind':'regulation','version':'fixture-1','status':'downloaded','rights':'public',
        'representation':'original','path':member,'sha256':hashlib.sha256(payload).hexdigest(),
        'bytes':len(payload),'media_type':'text/plain','source_url':'https://example.org/source',
        'download_url':'https://example.org/source.txt','retrieved_at':'2026-10-23T09:00:00Z'}
    manifest={'schema_version':1,'package_id':package_id,'created_at':'2026-10-23T09:00:00Z','documents':[record]}
    if mutate:mutate(manifest)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        archive.writestr(member,payload)
        for name,data in (extras or {}).items():archive.writestr(name,data)
    return path


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.store=Store(self.root/'store')

    def test_import_preserves_original_and_starts_unreviewed(self):
        result=import_package(self.store,package(self.root/'a.zip'))
        self.assertEqual(result['downloaded'],1)
        doc=self.store.document('DOC-1')
        self.assertEqual(doc['review_status'],'unreviewed')
        self.assertEqual(self.store.blob_path(doc['sha256']).read_bytes(),b'public regulation fixture')

    def test_repeat_package_is_idempotent(self):
        p=package(self.root/'a.zip')
        import_package(self.store,p)
        self.assertTrue(import_package(self.store,p)['already_imported'])
        self.assertEqual(len(self.store.documents()),1)

    def test_same_document_id_cannot_replace_original(self):
        import_package(self.store,package(self.root/'a.zip'))
        with self.assertRaises(ValueError):
            import_package(self.store,package(self.root/'b.zip',b'different bytes',package_id='PKG-2'))
        self.assertEqual(len(self.store.documents()),1)

    def test_hash_mismatch_rejects_whole_package(self):
        p=package(self.root/'a.zip',mutate=lambda m:m['documents'][0].update(sha256='0'*64))
        with self.assertRaises(ValueError):import_package(self.store,p)
        self.assertEqual(self.store.documents(),[])

    def test_traversal_is_rejected_without_writing_outside_store(self):
        for member in ['../escape.txt','/escape.txt','C:/escape.txt','originals/../escape.txt','originals\\escape.txt']:
            with self.subTest(member=member),self.assertRaises(ValueError):
                import_package(self.store,package(self.root/'a.zip',member=member))
        self.assertFalse((self.root/'escape.txt').exists())

    def test_error_html_cannot_be_registered_as_pdf(self):
        p=package(self.root/'a.zip',b'<html>Forbidden</html>',member='originals/a.pdf',mutate=lambda m:m['documents'][0].update(media_type='application/pdf'))
        with self.assertRaises(ValueError):import_package(self.store,p)

    def test_unlisted_file_is_rejected(self):
        with self.assertRaises(ValueError):import_package(self.store,package(self.root/'a.zip',extras={'unlisted.txt':b'not in manifest'}))

    def test_duplicate_zip_member_is_rejected(self):
        p=package(self.root/'a.zip')
        with zipfile.ZipFile(p,'a') as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                z.writestr('originals/source.txt',b'other')
        with self.assertRaises(ValueError):import_package(self.store,p)

    def test_unavailable_record_is_preserved_without_fake_file(self):
        p=self.root/'a.zip'
        record={'document_id':'MISSING','request_ids':['STD-001'],'title':'Licensed standard','kind':'standard','version':'2020','status':'purchase_required','rights':'unknown','representation':'metadata','notes':'Publisher purchase required'}
        with zipfile.ZipFile(p,'w') as z:z.writestr('manifest.json',json.dumps({'schema_version':1,'package_id':'P','created_at':'2026-10-23T09:00:00Z','documents':[record]}))
        result=import_package(self.store,p)
        self.assertEqual(result['unavailable'],1)
        self.assertIsNone(self.store.document('MISSING')['sha256'])

    def test_late_bad_document_leaves_no_partial_records(self):
        def mutate(m):
            m['documents'].append({**m['documents'][0],'document_id':'DOC-2','path':'originals/b.txt','sha256':'0'*64})
        p=package(self.root/'a.zip',mutate=mutate,extras={'originals/b.txt':b'public regulation fixture'})
        with self.assertRaises(ValueError):import_package(self.store,p)
        self.assertEqual(self.store.documents(),[])

    def test_corrupted_blob_is_detected_on_read(self):
        import_package(self.store,package(self.root/'a.zip'))
        sha=self.store.document('DOC-1')['sha256']
        self.store.blob_path(sha).write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.store.verify_blob(sha)

    def test_archive_size_limit_is_enforced_before_import(self):
        p=package(self.root/'a.zip')
        with patch('labflow.intake.MAX_EXPANDED_BYTES',64),self.assertRaises(ValueError):import_package(self.store,p)
        self.assertEqual(self.store.documents(),[])

    def test_symbolic_link_archive_member_is_rejected(self):
        p=package(self.root/'a.zip')
        info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16
        with zipfile.ZipFile(p,'a') as z:z.writestr(info,'originals/source.txt')
        with self.assertRaises(ValueError):import_package(self.store,p)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=Store(self.root/'store')
        import_package(self.store,package(self.root/'source.zip'))
        create_case(self.store,{'case_id':'CASE-1','authorization_route':'certification','product':{'manufacturer':'Example','model':'DUT','serial_number':'S1'},'scope_ids':['F02'],'synthetic':False})
        register_method(self.store,{'method_id':'METHOD-1','scope_id':'F02','calculator':'emc_field_strength','source_document_ids':['DOC-1'],'limit':{'value':30,'unit':'dBuV/m','operator':'<=','source_document_id':'DOC-1','clause':'fictional test fixture'}})
        add_plan(self.store,'CASE-1',{'plan_id':'PLAN-1','method_id':'METHOD-1','configuration':{'mode':'fixture'},'applicability':'applicable','rationale':'test fixture'})
        self.raw=self.root/'raw.json'
        self.raw.write_text(json.dumps({'reading':30,'unit':'dBuV','antenna_factor_db_per_m':10,'cable_loss_db':2,'preamp_gain_db':20,'instrument_corrections_applied':False}))
        evidence=self.root/'setup.txt';evidence.write_text('Synthetic test-only setup and calibration evidence')
        self.evidence=self.store.import_artifact(evidence,'setup')
        self.run={'run_id':'RUN-1','case_id':'CASE-1','started_at':'2026-10-23T09:00:00Z','ended_at':'2026-10-23T09:01:00Z','execution_status':'completed','settings':{'detector':'fixture'},'equipment_ids':['fixture-asset'],'environment':{'temperature_c':23},'setup_artifact_ids':[self.evidence],'calibration_artifact_ids':[self.evidence]}

    def record(self):return record_run(self.store,'PLAN-1',self.run,self.raw)

    def test_unicode_report_round_trips_as_utf8(self):
        product={'manufacturer':'시험 제조사 — µ','model':'제품 α'}
        create_case(self.store,{'case_id':'UTF8','authorization_route':'undetermined',
                               'product':product,'scope_ids':['F02'],'synthetic':True})
        result=render_report(self.store,'UTF8',self.root/'reports')
        payload=json.loads(Path(result['json']).read_text(encoding='utf-8'))
        self.assertEqual(payload['case']['product'],product)
        self.assertIn(product['manufacturer'],Path(result['html']).read_text(encoding='utf-8'))

    def test_utf8_measurement_metadata_does_not_block_calculation(self):
        raw=json.loads(self.raw.read_text(encoding='utf-8'))
        raw['note']='시험 기록 — µ'
        self.raw.write_text(json.dumps(raw,ensure_ascii=False),encoding='utf-8')
        self.record()
        result=evaluate(self.store,'RUN-1')
        self.assertEqual(len(result['calculations']),1)
        self.assertEqual(result['calculations'][0]['value'],22)

    def review(self):
        self.store.review_document('DOC-1','test reviewer','fixture source only')
        review_method(self.store,'METHOD-1','test reviewer','fixture procedure and limit only')
        review_run(self.store,'RUN-1','test reviewer','fixture evidence only')

    def test_calculation_is_available_but_missing_reviews_block_judgment(self):
        self.record();result=evaluate(self.store,'RUN-1')
        self.assertEqual(result['calculations'][0]['value'],22)
        self.assertEqual(result['decision'],'blocked')
        self.assertIn('method_unreviewed',result['blockers'])

    def test_reviewed_case_preserves_raw_input_and_preliminary_result(self):
        self.record();self.review();result=evaluate(self.store,'RUN-1')
        self.assertEqual(result['decision'],'pass')
        self.assertEqual(result['calculations'][0]['margin'],8)
        self.assertEqual(self.store.verify_blob(result['raw_sha256']).read_bytes(),self.raw.read_bytes())
        self.assertFalse(case_status(self.store,'CASE-1')['official_release_available'])

    def test_failed_execution_cannot_pass(self):
        self.run['execution_status']='error';self.record()
        self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'blocked')

    def test_cross_case_run_is_rejected(self):
        self.run['case_id']='OTHER'
        with self.assertRaises(ValueError):self.record()

    def test_reused_case_id_cannot_change_product_or_synthetic_flag(self):
        with self.assertRaises(ValueError):
            create_case(self.store,{'case_id':'CASE-1','authorization_route':'certification','product':{'manufacturer':'Example','model':'OTHER','serial_number':'S1'},'scope_ids':['F02'],'synthetic':True})

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            create_case(self.store,{'case_id':'BAD','authorization_route':'certification','product':{'manufacturer':'Example','model':'DUT','serial_number':'S1'},'scope_ids':['UNKNOWN'],'synthetic':False})

    def test_source_corruption_revokes_previously_computed_pass(self):
        self.record();self.review();self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'pass')
        self.store.blob_path(self.store.document('DOC-1')['sha256']).write_bytes(b'tampered')
        self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'blocked')

    def test_invalid_unit_or_nonfinite_data_never_pass(self):
        for bad in [{'reading':float('nan'),'unit':'dBuV'},{'reading':True,'unit':'dBuV'},{'reading':30,'unit':'dBm'}]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):calculate('emc_field_strength',{**json.loads(self.raw.read_text(encoding='utf-8')),**bad})

    def test_power_conversion_is_independently_known(self):
        self.assertEqual(calculate('rf_power',{'reading':30,'unit':'dBm'}),{'value':1.0,'unit':'W'})

    def test_instrument_corrections_cannot_be_applied_twice(self):
        data=json.loads(self.raw.read_text(encoding='utf-8'));data['instrument_corrections_applied']=True
        with self.assertRaises(ValueError):calculate('emc_field_strength',data)

    def test_missing_correction_state_is_not_assumed_uncorrected(self):
        data=json.loads(self.raw.read_text(encoding='utf-8'));del data['instrument_corrections_applied']
        with self.assertRaises(ValueError):calculate('emc_field_strength',data)

    def test_zero_margin_boundary_passes_without_rounding(self):
        data=json.loads(self.raw.read_text(encoding='utf-8'));data['reading']=38;self.raw.write_text(json.dumps(data))
        self.record();self.review();result=evaluate(self.store,'RUN-1')
        self.assertEqual(result['calculations'][0]['margin'],0)
        self.assertEqual(result['decision'],'pass')

    def test_latest_failed_attempt_blocks_prior_pass(self):
        self.record();self.review();self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'pass')
        self.run.update(run_id='RUN-2',execution_status='error');self.record()
        status=case_status(self.store,'CASE-1')
        self.assertEqual(status['results'][0]['run_id'],'RUN-2')
        self.assertEqual(status['results'][0]['decision'],'blocked')

    def test_empty_observations_are_blocked(self):
        self.raw.write_text('{"observations": []}');self.record()
        self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'blocked')

    def test_not_applicable_requires_reason_and_cannot_accept_run(self):
        with self.assertRaises(ValueError):add_plan(self.store,'CASE-1',{'plan_id':'NA','method_id':'METHOD-1','configuration':{},'applicability':'not_applicable','rationale':''})
        add_plan(self.store,'CASE-1',{'plan_id':'NA','method_id':'METHOD-1','configuration':{},'applicability':'not_applicable','rationale':'fixture exclusion needs review'})
        with self.assertRaises(ValueError):record_run(self.store,'NA',self.run,self.raw)
        self.assertIn('applicability_review_required:NA',case_status(self.store,'CASE-1')['blockers'])

    def test_synthetic_flag_reaches_decision(self):
        create_case(self.store,{'case_id':'SIM','authorization_route':'certification','product':{'manufacturer':'Example','model':'DUT','serial_number':'S1'},'scope_ids':['F02'],'synthetic':True})
        add_plan(self.store,'SIM',{'plan_id':'SIMPLAN','method_id':'METHOD-1','configuration':{'mode':'fixture'},'applicability':'applicable','rationale':'fixture'})
        self.run.update(run_id='SIMRUN',case_id='SIM');record_run(self.store,'SIMPLAN',self.run,self.raw)
        self.store.review_document('DOC-1','r','fixture');review_method(self.store,'METHOD-1','r','fixture');review_run(self.store,'SIMRUN','r','fixture')
        result=evaluate(self.store,'SIMRUN')
        self.assertTrue(result['synthetic']);self.assertEqual(result['decision'],'simulated_pass')

    def test_synthetic_package_evidence_cannot_be_reused_as_real_measurement(self):
        archive=package(self.root/'synthetic.zip',self.raw.read_bytes(),document_id='SYN-RAW',package_id='SYN-PKG',
            mutate=lambda m:m.update(synthetic=True))
        import_package(self.store,archive)
        self.record();self.review();result=evaluate(self.store,'RUN-1')
        self.assertTrue(result['synthetic'])
        self.assertEqual(result['decision'],'blocked')
        self.assertIn('synthetic_evidence_in_real_case',result['blockers'])
        report=render_report(self.store,'CASE-1',self.root/'reports')
        self.assertTrue(json.loads(Path(report['json']).read_text(encoding='utf-8'))['synthetic'])

    def test_explicit_artifact_provenance_survives_reimport_and_reopen(self):
        sha=self.store.import_artifact(self.raw,'raw',synthetic=True)
        self.store.import_artifact(self.raw,'raw',synthetic=False)
        self.store=Store(self.store.root)
        self.assertTrue(self.store.evidence_is_synthetic(sha))
        self.record();self.review()
        self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'blocked')

    def test_legacy_store_recovers_synthetic_run_provenance(self):
        create_case(self.store,{'case_id':'SIM','authorization_route':'certification','product':{'manufacturer':'Fixture','model':'Synthetic'},'scope_ids':['F02'],'synthetic':True})
        add_plan(self.store,'SIM',{'plan_id':'SIMPLAN','method_id':'METHOD-1','configuration':{'mode':'fixture'},'applicability':'applicable','rationale':'fixture'})
        run=record_run(self.store,'SIMPLAN',{**self.run,'run_id':'SIMRUN','case_id':'SIM'},self.raw)
        with self.store.connection() as con:con.execute('ALTER TABLE blobs DROP COLUMN synthetic')
        self.store=Store(self.store.root)
        self.assertTrue(self.store.evidence_is_synthetic(run['raw_sha256']))

    def test_report_labels_synthetic_evidence_in_previous_attempts(self):
        self.store.import_artifact(self.raw,'raw',synthetic=True)
        self.record();self.review()
        data=json.loads(self.raw.read_text(encoding='utf-8'));data['reading']=31;self.raw.write_text(json.dumps(data))
        record_run(self.store,'PLAN-1',{**self.run,'run_id':'CLEAN-RUN'},self.raw)
        review_run(self.store,'CLEAN-RUN','r','fixture')
        self.assertEqual(evaluate(self.store,'CLEAN-RUN')['decision'],'pass')
        report=render_report(self.store,'CASE-1',self.root/'reports')
        self.assertTrue(json.loads(Path(report['json']).read_text(encoding='utf-8'))['synthetic'])

    def test_synthetic_setup_and_calibration_each_block_real_case(self):
        fixture=self.root/'synthetic.txt';fixture.write_text('explicit synthetic evidence')
        archive=package(self.root/'synthetic.zip',fixture.read_bytes(),document_id='SYN-EVIDENCE',package_id='SYN-PKG',
            mutate=lambda m:m.update(synthetic=True))
        import_package(self.store,archive)
        sha=hashlib.sha256(fixture.read_bytes()).hexdigest()
        self.store.review_document('DOC-1','r','fixture');review_method(self.store,'METHOD-1','r','fixture')
        for field in ['setup_artifact_ids','calibration_artifact_ids']:
            with self.subTest(field=field):
                run={**self.run,'run_id':field,field:[sha]}
                record_run(self.store,'PLAN-1',run,self.raw);review_run(self.store,field,'r','fixture')
                result=evaluate(self.store,field)
                self.assertTrue(result['synthetic']);self.assertEqual(result['decision'],'blocked')

    def test_raw_identity_mismatches_block_single_observation_and_envelope(self):
        observation=json.loads(self.raw.read_text(encoding='utf-8'))
        self.store.review_document('DOC-1','r','fixture');review_method(self.store,'METHOD-1','r','fixture')
        for position in ['single','envelope','observation']:
            for field in ['case_id','plan_id','run_id']:
                with self.subTest(position=position,field=field):
                    run_id=position+'-'+field
                    if position=='single':raw={**observation,field:'OTHER'}
                    elif position=='envelope':raw={'observations':[observation],field:'OTHER'}
                    else:raw={'observations':[{**observation,field:'OTHER'}]}
                    self.raw.write_text(json.dumps(raw))
                    record_run(self.store,'PLAN-1',{**self.run,'run_id':run_id},self.raw)
                    review_run(self.store,run_id,'r','fixture');result=evaluate(self.store,run_id)
                    self.assertEqual(result['decision'],'blocked')
                    self.assertTrue(any('identity_mismatch:'+field in b for b in result['blockers']))

    def test_matching_raw_identity_is_accepted(self):
        self.raw.write_text(json.dumps({'case_id':'CASE-1','plan_id':'PLAN-1','run_id':'RUN-1',
            'observations':[json.loads(self.raw.read_text(encoding='utf-8'))]}))
        self.record();self.review()
        self.assertEqual(evaluate(self.store,'RUN-1')['decision'],'pass')

    def test_report_is_draft_and_contains_traceable_raw_evidence(self):
        self.record();result=render_report(self.store,'CASE-1',self.root/'reports')
        html=Path(result['html']).read_text(encoding='utf-8');data=json.loads(Path(result['json']).read_text(encoding='utf-8'))
        self.assertIn('DRAFT',html);self.assertIn('22',html)
        self.assertEqual(data['results'][0]['decision'],'blocked')
        self.assertTrue(Path(result['pdf']).read_bytes().startswith(b'%PDF-'))
        for rel in data['evidence_files'].values():self.assertTrue((Path(result['json']).parent/rel).is_file())

    def test_corrupted_report_evidence_never_exports_a_pass(self):
        self.record();self.review();evaluate(self.store,'RUN-1')
        self.store.blob_path(self.store.document('DOC-1')['sha256']).write_bytes(b'tampered')
        report=render_report(self.store,'CASE-1',self.root/'reports')
        self.assertEqual(json.loads(Path(report['json']).read_text(encoding='utf-8'))['results'][0]['decision'],'blocked')

    def test_product_markup_is_escaped_in_report(self):
        create_case(self.store,{'case_id':'HTML','authorization_route':'sdoc','product':{'manufacturer':'<script>alert(1)</script>','model':'DUT'},'scope_ids':['F02'],'synthetic':True})
        report=render_report(self.store,'HTML',self.root/'reports')
        text=Path(report['html']).read_text(encoding='utf-8')
        self.assertNotIn('<script>alert(1)</script>',text)
        self.assertIn('&lt;script&gt;',text)


class CommandTests(unittest.TestCase):
    def test_demo_reaches_pdf_without_claiming_real_compliance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run([sys.executable,'-m','labflow','--workspace',str(Path(tmp)/'store'),'demo','--out',str(Path(tmp)/'out')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout);report=json.loads(Path(data['report']['json']).read_text(encoding='utf-8'))
            self.assertTrue(report['synthetic']);self.assertEqual(report['results'][0]['calculations'][0]['value'],22)
            self.assertEqual(report['results'][0]['decision'],'blocked')
            self.assertTrue(Path(data['report']['pdf']).exists())


class MCPTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_client_can_complete_offline_draft_workflow(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=package(root/'source.zip',mutate=lambda m:m.update(synthetic=True))
            evidence=root/'setup.txt';evidence.write_text('synthetic setup/calibration')
            raw=root/'raw.json';raw.write_text(json.dumps({'case_id':'MCP-CASE','plan_id':'MCP-PLAN','run_id':'MCP-RUN',
                'reading':30,'unit':'dBm'}))
            parameters=StdioServerParameters(command=sys.executable,args=['-m','labflow','--workspace',str(root/'store'),'mcp'],
                cwd=str(Path(__file__).resolve().parents[1]))
            async with stdio_client(parameters) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    names={tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn('lab_import_artifact',names)
                    self.assertFalse(any('review' in name for name in names))
                    async def call(name,arguments=None):
                        result=await session.call_tool(name,arguments or {})
                        self.assertFalse(result.isError,result.content)
                        return result.structuredContent
                    capabilities=await call('lab_capabilities')
                    self.assertFalse(capabilities['live_hardware']);self.assertFalse(capabilities['official_release'])
                    await call('lab_import_package',{'zip_path':str(archive)})
                    imported=await call('lab_import_artifact',{'path':str(evidence),'kind':'setup','synthetic':True})
                    sha=imported['sha256']
                    await call('lab_create_case',{'data':{'case_id':'MCP-CASE','authorization_route':'certification',
                        'product':{'manufacturer':'Synthetic','model':'Fixture'},'scope_ids':['F03'],'synthetic':True}})
                    await call('lab_register_method',{'data':{'method_id':'MCP-METHOD','scope_id':'F03','calculator':'rf_power',
                        'source_document_ids':['DOC-1'],'limit':{'value':2,'unit':'W','operator':'<=','source_document_id':'DOC-1','clause':'fictional threshold'}}})
                    await call('lab_add_plan',{'case_id':'MCP-CASE','data':{'plan_id':'MCP-PLAN','method_id':'MCP-METHOD',
                        'applicability':'applicable','configuration':{'mode':'fixture'},'rationale':'Transport test only'}})
                    await call('lab_record_run',{'plan_id':'MCP-PLAN','raw_path':str(raw),'data':{'run_id':'MCP-RUN','case_id':'MCP-CASE',
                        'started_at':'2026-10-23T09:00:00Z','ended_at':'2026-10-23T09:01:00Z','execution_status':'completed',
                        'settings':{'mode':'fixture'},'environment':{'temperature_c':23},'equipment_ids':['SYNTHETIC'],
                        'setup_artifact_ids':[sha],'calibration_artifact_ids':[sha]}})
                    evaluated=await call('lab_evaluate',{'run_id':'MCP-RUN'})
                    self.assertEqual(evaluated['calculations'][0]['value'],1)
                    self.assertEqual(evaluated['decision'],'blocked');self.assertTrue(evaluated['synthetic'])
                    report=await call('lab_render_report',{'case_id':'MCP-CASE','output_dir':str(root/'reports')})
                    self.assertTrue(Path(report['pdf']).is_file())


if __name__=='__main__':unittest.main()
