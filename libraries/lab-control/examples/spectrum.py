"""python examples/spectrum.py SITE.json OUT.json --start-hz ... --stop-hz ...

No DUT RF commands. The source, path calibration and FCC recipe are separate.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from dgm_lab import Sweep, SpectrumAnalyzer, JsonlLog, managed_run
from dgm_lab.registry import connect


def main():
    p=argparse.ArgumentParser()
    p.add_argument('profile');p.add_argument('output')
    for name in ('start-hz','stop-hz','rbw-hz','vbw-hz','reference-dbm','attenuation-db','sweep-seconds'):
        p.add_argument('--'+name,type=float,required=True)
    p.add_argument('--points',type=int,default=1001)
    p.add_argument('--detector',choices=['POS','NEG','SAMP','RMS','AVER'],default='POS')
    a=p.parse_args()
    config=Sweep(a.start_hz,a.stop_hz,a.rbw_hz,a.vbw_hz,a.reference_dbm,a.attenuation_db,a.points,a.detector,a.sweep_seconds)
    profile=json.loads(Path(a.profile).read_text(encoding='utf-8-sig'))
    target=Path(a.output)
    if target.exists():
        raise FileExistsError('Choose a new output path; existing measurement evidence is preserved')
    log=JsonlLog(str(target)+'.traffic.jsonl')
    try:
        with connect(profile,log=log) as analyzer:
            if not isinstance(analyzer,SpectrumAnalyzer):
                raise ValueError('Profile must select SpectrumAnalyzer')
            with managed_run(lambda:None,analyzer.stop):
                trace=analyzer.acquire(config)
        target.write_text(json.dumps(asdict(trace),indent=2)+'\n',encoding='utf-8')
        print(target.resolve())
    finally:
        log.close()


if __name__=='__main__': main()
