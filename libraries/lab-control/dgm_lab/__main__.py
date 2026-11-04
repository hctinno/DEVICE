import argparse
from dataclasses import asdict
import json
from .registry import inventory, connect


def main():
    parser=argparse.ArgumentParser(description='DGM LabControl: inventory and explicit-address read-only identification')
    sub=parser.add_subparsers(dest='action', required=True)
    search=sub.add_parser('inventory');search.add_argument('query',nargs='?',default='')
    search.add_argument('--scope',choices=('legacy','hct-2026'),default='legacy')
    probe=sub.add_parser('probe');probe.add_argument('profile',help='JSON with explicit driver/parameters/transport')
    args=parser.parse_args()
    if args.action=='inventory':
        for row in inventory(args.query,scope=args.scope):
            print(json.dumps({k:row[k] for k in ('manufacturer','model','status','driver','scope_ko')},ensure_ascii=False))
    else:
        with open(args.profile,encoding='utf-8-sig') as f:
            profile=json.load(f)
        with connect(profile) as device:
            identity=getattr(device,'identity',None)
            print(json.dumps(asdict(identity) if identity else {'controller_identified':True},ensure_ascii=False))


if __name__=='__main__': main()
