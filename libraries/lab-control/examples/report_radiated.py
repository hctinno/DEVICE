"""Run an explicit HCT-style discrete motion/receiver grid; DUT TX is externally owned."""
import argparse
from contextlib import ExitStack, closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dgm_lab import Co3000, EmiReceiver, JsonlLog, managed_run, scan_radiated_grid
from dgm_lab.registry import connect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job',help='Site JSON: motion profile, receiver profile, grid, measurement')
    parser.add_argument('output',help='New result JSON; existing files are refused')
    parser.add_argument('--execute',action='store_true',help='Operate explicitly configured laboratory equipment')
    args=parser.parse_args()
    job=json.loads(Path(args.job).read_text(encoding='utf-8-sig'))
    output=Path(args.output)
    log=Path(str(output)+'.traffic.jsonl')
    failure=Path(str(output)+'.failure.json')
    if any(p.exists() for p in (output,log,failure)):
        raise FileExistsError('Output/log/failure path already exists; use a new run path')
    if not args.execute:
        print(json.dumps(dict(executed=False,job=job),ensure_ascii=False,indent=2))
        return
    # This example does not assert ownership/control of DUT RF.
    if job.get('external_dut_tx_and_shutdown_owner_confirmed') is not True:
        raise ValueError('Explicit DUT TX/shutdown owner confirmation required in site job')
    run=dict(run_id=str(uuid4()),started_utc=datetime.now(timezone.utc).isoformat(),job=job,status='running')
    output.parent.mkdir(parents=True,exist_ok=True)
    try:
        with closing(JsonlLog(log)) as traffic, ExitStack() as stack:
            controller=stack.enter_context(connect(job['motion'],log=traffic))
            receiver=stack.enter_context(connect(job['receiver'],log=traffic))
            if not isinstance(controller,Co3000) or not isinstance(receiver,EmiReceiver):
                raise ValueError('Example requires Co3000 and EmiReceiver profiles')
            # Ensure receiver cleanup even if the first acquisition fails.
            stack.enter_context(managed_run(lambda:None,receiver.stop))
            result=scan_radiated_grid(controller,measure=lambda:receiver.read_level(**job['measurement']).value,
                unit='dBuV',**job['grid'])
            run.update(result=result,status='software_sequence_completed',physical_validation_record=False)
        run['finished_utc']=datetime.now(timezone.utc).isoformat()
        with output.open('x',encoding='utf-8') as file:
            json.dump(run,file,ensure_ascii=False,indent=2)
    except BaseException as exc:
        run.update(status='failed',error=repr(exc),finished_utc=datetime.now(timezone.utc).isoformat())
        # Never export a success result if stop or cleanup failed.
        run.pop('result',None)
        with failure.open('x',encoding='utf-8') as file:
            json.dump(run,file,ensure_ascii=False,indent=2)
        raise


if __name__=='__main__': main()
