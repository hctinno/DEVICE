"""Use only an independently commissioned OEM model/build profile. No latest-model defaults."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from dgm_lab import SpectrumAnalyzer, Sweep, JsonlLog, managed_run
from dgm_lab.registry import connect
from dgm_lab.phone import phone_serial, measure_during_phone_tx
from dgm_rf import WlanTxConfig


def main():
    p=argparse.ArgumentParser()
    for name in ('analyzer-profile','phone-profile','phone-port','wlan-config','sweep-config','output'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--baudrate',type=int,required=True)
    a=p.parse_args();read=lambda path:json.loads(Path(path).read_text(encoding='utf-8-sig'))
    wlan=WlanTxConfig(**read(a.wlan_config));sweep=Sweep(**read(a.sweep_config))
    target=Path(a.output)
    if target.exists(): raise FileExistsError('Preserve existing result; use a new output path')
    profile=read(a.analyzer_profile)
    sweep.validate(profile['parameters']['max_frequency_hz'])
    log=JsonlLog(str(target)+'.traffic.jsonl')
    try:
        with connect(profile,log=log) as analyzer:
            if not isinstance(analyzer,SpectrumAnalyzer): raise ValueError('SpectrumAnalyzer required')
            with phone_serial(port=a.phone_port,baudrate=a.baudrate,profile_path=a.phone_profile) as phone:
                try:
                    with managed_run(lambda:None,analyzer.stop):
                        trace=measure_during_phone_tx(phone=phone,config=wlan,acquire=lambda:analyzer.acquire(sweep))
                finally:
                    phone.save_log(str(target)+'.phone.json')
                result={'trace':asdict(trace),'wlan_requested':asdict(wlan),
                        'phone_profile':a.phone_profile,'phone_events':phone.log}
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(target.resolve())
    finally: log.close()


if __name__=='__main__': main()
