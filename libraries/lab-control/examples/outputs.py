"""Explicit, time-bounded RF CW or DC output with normal/error/Ctrl+C cleanup."""
import argparse
import json
from pathlib import Path
import time
from dgm_lab import SignalGenerator, PowerSupply, JsonlLog
from dgm_lab.core import number
from dgm_lab.registry import connect


def main():
    p=argparse.ArgumentParser()
    p.add_argument('profile');p.add_argument('--log',required=True)
    p.add_argument('--seconds',required=True,type=float)
    sub=p.add_subparsers(dest='mode',required=True)
    rf=sub.add_parser('cw');rf.add_argument('--frequency-hz',required=True,type=float);rf.add_argument('--power-dbm',required=True,type=float)
    dc=sub.add_parser('dc');dc.add_argument('--voltage',required=True,type=float);dc.add_argument('--current-limit',required=True,type=float)
    dc.add_argument('--range-name',choices=['P8V','P20V'])
    a=p.parse_args();number(a.seconds,'seconds',.001,3600)
    profile=json.loads(Path(a.profile).read_text(encoding='utf-8-sig'))
    log=JsonlLog(a.log)
    try:
        with connect(profile,log=log) as device:
            if a.mode=='cw':
                if not isinstance(device,SignalGenerator): raise ValueError('CW requires SignalGenerator profile')
                device.configure_cw(frequency_hz=a.frequency_hz,power_dbm=a.power_dbm)
                with device.emitting(): time.sleep(a.seconds)
            else:
                if not isinstance(device,PowerSupply): raise ValueError('DC requires PowerSupply profile')
                device.configure(voltage=a.voltage,current_limit=a.current_limit,range_name=a.range_name)
                with device.powering():
                    print(device.read_voltage());print(device.read_current())
                    time.sleep(a.seconds)
        print('Output OFF confirmed by device readback; independent RF/voltage check remains a site responsibility.')
    finally: log.close()


if __name__=='__main__': main()
