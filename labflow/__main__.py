import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .store import Store
from .intake import import_package
from .workflow import create_case,register_method,add_plan,record_run,evaluate,case_status,review_method,review_run
from .reporting import render_report
from .active_intake import register_source, scan_source, intake_status
from .intake_jobs import claim_job, complete_job, fail_job, respond, notifications


def main():
    # The CLI is a UTF-8 JSON boundary, including under Windows code pages.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Local FCC workflow core; reports are drafts')
    parser.add_argument('--workspace',default='data/labflow')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('documents');sub.add_parser('mcp')
    for name in ['import-package','create-case','register-method']:
        sub.add_parser(name).add_argument('file')
    artifact=sub.add_parser('import-artifact');artifact.add_argument('file');artifact.add_argument('--kind',required=True)
    provenance=artifact.add_mutually_exclusive_group(required=True)
    provenance.add_argument('--synthetic',action='store_true');provenance.add_argument('--real',action='store_true')
    plan=sub.add_parser('add-plan');plan.add_argument('case_id');plan.add_argument('file')
    run=sub.add_parser('record-run');run.add_argument('plan_id');run.add_argument('file');run.add_argument('--raw')
    for name in ['evaluate','status']:sub.add_parser(name).add_argument('id')
    report=sub.add_parser('report');report.add_argument('case_id');report.add_argument('--out',default='exports/reports')
    demo=sub.add_parser('demo');demo.add_argument('--out',default='exports/demo')
    for name in ['review-document','review-method','review-run']:
        p=sub.add_parser(name);p.add_argument('id');p.add_argument('--reviewer',required=True);p.add_argument('--note',required=True)
    source=sub.add_parser('intake-add-source')
    source.add_argument('source_id');source.add_argument('root');source.add_argument('--settle-seconds',type=float,default=5)
    provenance=source.add_mutually_exclusive_group(required=True)
    provenance.add_argument('--synthetic',action='store_true');provenance.add_argument('--real',action='store_true')
    sub.add_parser('intake-scan').add_argument('source_id')
    sub.add_parser('intake-status').add_argument('id',nargs='?')
    claim=sub.add_parser('intake-claim');claim.add_argument('worker_id');claim.add_argument('--lease-seconds',type=float,default=120)
    for name in ['intake-complete','intake-fail']:
        p=sub.add_parser(name);p.add_argument('job_id');p.add_argument('token')
        if name=='intake-complete':p.add_argument('file')
    response=sub.add_parser('intake-respond')
    response.add_argument('event_id');response.add_argument('action',choices=['proceed','defer','answer'])
    response.add_argument('--intake-id');response.add_argument('--answers')
    sub.add_parser('intake-notifications')
    args=parser.parse_args()
    try:
        store=Store(args.workspace);cmd=args.command
        def data():return json.loads(Path(args.file).read_text(encoding='utf-8-sig'))
        if cmd=='init':result={'workspace':str(store.root),'status':'initialized','hardware_connected':False,'official_release_available':False}
        elif cmd=='documents':result=store.documents()
        elif cmd=='import-package':result=import_package(store,args.file)
        elif cmd=='import-artifact':
            sha=store.import_artifact(args.file,args.kind,synthetic=args.synthetic)
            result={'sha256':sha,'synthetic':store.evidence_is_synthetic(sha)}
        elif cmd=='create-case':result=create_case(store,data())
        elif cmd=='register-method':result=register_method(store,data())
        elif cmd=='add-plan':result=add_plan(store,args.case_id,data())
        elif cmd=='record-run':result=record_run(store,args.plan_id,data(),args.raw)
        elif cmd=='evaluate':result=evaluate(store,args.id)
        elif cmd=='status':result=case_status(store,args.id)
        elif cmd=='report':result=render_report(store,args.case_id,args.out)
        elif cmd=='review-document':result=store.review_document(args.id,args.reviewer,args.note)
        elif cmd=='review-method':result=review_method(store,args.id,args.reviewer,args.note)
        elif cmd=='review-run':result=review_run(store,args.id,args.reviewer,args.note)
        elif cmd=='intake-add-source':result=register_source(store,args.source_id,args.root,synthetic=args.synthetic,settle_seconds=args.settle_seconds)
        elif cmd=='intake-scan':result=scan_source(store,args.source_id)
        elif cmd=='intake-status':result=intake_status(store,args.id)
        elif cmd=='intake-claim':result=claim_job(store,args.worker_id,lease_seconds=args.lease_seconds)
        elif cmd=='intake-complete':result=complete_job(store,args.job_id,args.token,data())
        elif cmd=='intake-fail':result=fail_job(store,args.job_id,args.token)
        elif cmd=='intake-respond':
            answers=json.loads(Path(args.answers).read_text(encoding='utf-8-sig')) if args.answers else None
            result=respond(store,args.event_id,args.action,intake_id=args.intake_id,answers=answers)
        elif cmd=='intake-notifications':result=notifications(store)
        elif cmd=='demo':
            from .demo import run_demo
            result=run_demo(store,args.out)
        elif cmd=='mcp':
            from .mcp_server import create_server
            create_server(store).run(transport='stdio');return 0
        print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2));return 0
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
