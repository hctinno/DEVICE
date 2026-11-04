"""Report-based preparation API. Report conditions are not OEM wire arguments."""
from copy import deepcopy
from importlib.resources import files
import argparse
import json


class FccResearch:
    def __init__(self):
        self._data = json.loads(files('dgm_rf').joinpath('data/fcc-2026.json').read_text(encoding='utf-8'))

    def groups(self, device=None, radio=None):
        if device is not None and device not in self._data['devices']:
            raise ValueError(f'Unknown device: {device}')
        return deepcopy([g for g in self._data['groups']
                         if (device is None or g['device']==device) and (radio is None or g['radio']==radio)])

    def cases(self, group_id):
        self.group(group_id)
        return deepcopy([c for c in self._data['cases'] if c['group_id']==group_id])

    def group(self, group_id):
        for g in self._data['groups']:
            if g['id']==group_id:
                return deepcopy(g)
        raise KeyError(group_id)

    def prepare(self, group_id, *, model, firmware):
        g=self.group(group_id)
        device=self._data['devices'][g['device']]
        if model!=device['model']:
            raise ValueError(f'Model mismatch: expected {device["model"]}, got {model}')
        if not isinstance(firmware,str) or not firmware.strip():
            raise ValueError('Read and record the actual device firmware first')
        missing=list(g['missing'])
        report_fw=g['conditions'].get('software')
        if report_fw and report_fw!=firmware:
            missing.append(f'Firmware differs from report: {report_fw} -> {firmware}')
        return dict(group=g,device=device,observed_firmware=firmware,cases=self.cases(group_id),
                    ready=False,blockers=missing,
                    start_command=None,stop_command=None,
                    note='Preparation only. No DUT transport opened; no compatibility inferred from brand.')

    def wire_commands(self, group_id):
        g=self.group(group_id)
        raise RuntimeError(f'{group_id}: latest-model start/stop protocol is not validated; '
                           + '; '.join(g['missing']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device',choices=['fold8','duo'])
    p.add_argument('--radio')
    p.add_argument('--group')
    args=p.parse_args()
    db=FccResearch()
    result=dict(group=db.group(args.group),cases=db.cases(args.group)) if args.group else db.groups(args.device,args.radio)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
