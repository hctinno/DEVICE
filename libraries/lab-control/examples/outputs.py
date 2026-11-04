"""Explicit, time-bounded RF CW or DC output with normal/error/Ctrl+C cleanup."""
import argparse
import json
from pathlib import Path
import time
from dgm_lab import SignalGenerator, PowerSupply, OdaEx, Cmu200Cw, JsonlLog
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
                if isinstance(device,Cmu200Cw):
                    device.configure(frequency_hz=a.frequency_hz,power_dbm=a.power_dbm)
                elif isinstance(device,SignalGenerator):
                    device.configure_cw(frequency_hz=a.frequency_hz,power_dbm=a.power_dbm)
                else: raise ValueError('CW requires SignalGenerator or Cmu200Cw profile')
                with device.emitting(): time.sleep(a.seconds)
            else:
                if isinstance(device,OdaEx):
                    if a.range_name is not None: raise ValueError('ODA does not accept range-name')
                    device.configure(voltage=a.voltage,current=a.current_limit)
                elif isinstance(device,PowerSupply):
                    device.configure(voltage=a.voltage,current_limit=a.current_limit,range_name=a.range_name)
                else: raise ValueError('DC requires PowerSupply or OdaEx profile')
                with device.powering():
                    print(device.read_voltage());print(device.read_current())
                    time.sleep(a.seconds)
        print('Output OFF confirmed by device readback; independent RF/voltage check remains a site responsibility.')
    finally: log.close()


if __name__=='__main__': main()
