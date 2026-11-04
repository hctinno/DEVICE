"""Replay every standalone SCPI model in an installed SDK. No hardware access."""
import argparse
import json
from pathlib import Path
import tempfile
from dgm_control import devices, equipment_template, run_equipment
from dgm_control.equipment_peer import SIMULATED_DRIVERS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report');args=parser.parse_args()
    rows=[]
    with tempfile.TemporaryDirectory(prefix='dgm-equipment-models-') as temporary:
        root=Path(temporary)
        for device in devices():
            if device['id'] not in SIMULATED_DRIVERS: continue
            for model in sorted({r['model'] for r in device['models']}):
                result=run_equipment(equipment_template(device['id'],model),root/str(len(rows)))
                if result['status']!='completed': raise RuntimeError(json.dumps(result))
                rows.append(dict(driver=device['id'],model=model,status='completed',
                                 operations_completed=result['operations_completed'],cleanup_scope_succeeded=result['cleanup_scope_succeeded']))
    report=dict(passed=True,role_model_count=len(rows),distinct_model_names=len({r['model'] for r in rows}),
                simulated=True,physical_tests=0,rows=rows)
    if args.report:
        Path(args.report).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__': main()
