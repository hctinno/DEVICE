"""A complete synthetic example. Values are not FCC regulatory requirements."""
import hashlib
import json
from pathlib import Path
import uuid
import zipfile

from .intake import import_package
from .reporting import render_report
from .workflow import create_case,register_method,add_plan,record_run,evaluate
from .store import utcnow


def run_demo(store,output_dir):
    suffix=uuid.uuid4().hex[:10];case_id='DEMO-'+suffix
    inputs=store.root/'demo_inputs'/suffix;inputs.mkdir(parents=True)
    source=b'SYNTHETIC FIXTURE ONLY. This document is not an FCC rule or a standard.'
    doc_id='DEMO-SOURCE-'+suffix
    doc={'document_id':doc_id,'request_ids':['DEMO-NONNORMATIVE'],'title':'Synthetic arithmetic fixture, not a regulatory source','kind':'example','version':'demo-v1','status':'downloaded','rights':'public','representation':'original','path':'originals/fixture.txt','sha256':hashlib.sha256(source).hexdigest(),'bytes':len(source),'media_type':'text/plain','source_url':'https://example.invalid/synthetic','download_url':'https://example.invalid/synthetic.txt','retrieved_at':utcnow()}
    manifest={'schema_version':1,'package_id':'DEMO-PACKAGE-'+suffix,'created_at':utcnow(),'synthetic':True,'documents':[doc]}
    archive=inputs/'source_package.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('manifest.json',json.dumps(manifest));z.writestr(doc['path'],source)
    imported=import_package(store,archive)
    create_case(store,{'case_id':case_id,'authorization_route':'certification','product':{'manufacturer':'SYNTHETIC EXAMPLE','model':'Arithmetic demonstration only','serial_number':'NO-REAL-SAMPLE'},'scope_ids':['F02'],'synthetic':True})
    method_id='DEMO-METHOD-'+suffix
    register_method(store,{'method_id':method_id,'scope_id':'F02','calculator':'emc_field_strength','source_document_ids':[doc_id],
        'limit':{'value':30,'unit':'dBuV/m','operator':'<=','source_document_id':doc_id,'clause':'FICTIONAL arithmetic threshold; not an FCC limit'}})
    plan_id='DEMO-PLAN-'+suffix
    add_plan(store,case_id,{'plan_id':plan_id,'method_id':method_id,'configuration':{'mode':'synthetic'},'applicability':'applicable','rationale':'Software arithmetic fixture only'})
    raw=inputs/'raw.json';raw.write_text(json.dumps({'reading':30,'unit':'dBuV','antenna_factor_db_per_m':10,'cable_loss_db':2,'preamp_gain_db':20,'instrument_corrections_applied':False}))
    setup=inputs/'setup.txt';setup.write_text('SYNTHETIC setup/calibration placeholder. Not an actual laboratory record.')
    evidence=store.import_artifact(setup,'synthetic_evidence');run_id='DEMO-RUN-'+suffix
    record_run(store,plan_id,{'run_id':run_id,'case_id':case_id,'started_at':'2026-10-23T00:00:00Z','ended_at':'2026-10-23T00:01:00Z','execution_status':'completed',
        'settings':{'detector':'synthetic only'},'environment':{'temperature_c':23},'equipment_ids':['SYNTHETIC-ASSET'],'setup_artifact_ids':[evidence],'calibration_artifact_ids':[evidence]},raw)
    result=evaluate(store,run_id)
    return {'case_id':case_id,'intake':imported,'evaluation':result,'report':render_report(store,case_id,output_dir),'synthetic':True}
