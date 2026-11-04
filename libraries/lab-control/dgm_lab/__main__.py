import argparse
from dataclasses import asdict
import json
from .registry import inventory, connect
from .capabilities import capabilities, validate_profile


def main():
    parser=argparse.ArgumentParser(description='DGM LabControl: offline discovery; explicit probe enters remote mode and may affect state')
    sub=parser.add_subparsers(dest='action', required=True)
    search=sub.add_parser('inventory');search.add_argument('query',nargs='?',default='')
    search.add_argument('--scope',choices=('legacy','hct-2026'),default='legacy')
    probe=sub.add_parser('probe');probe.add_argument('profile',help='JSON with explicit driver/parameters/transport')
    caps=sub.add_parser('capabilities');caps.add_argument('driver',nargs='?')
    check=sub.add_parser('check-profile');check.add_argument('profile')
    demo=sub.add_parser('demo');demo.add_argument('--output-dir',required=True)
    demo.add_argument('--inject-failure',action='store_true')
    args=parser.parse_args()
    if args.action=='inventory':
        for row in inventory(args.query,scope=args.scope):
            print(json.dumps({k:row[k] for k in ('manufacturer','model','status','driver','scope_ko')},ensure_ascii=False))
    elif args.action=='capabilities':
        print(json.dumps(capabilities(args.driver),ensure_ascii=False,indent=2))
    elif args.action=='demo':
        from .demo import run_demo
        print(json.dumps(run_demo(args.output_dir,inject_failure=args.inject_failure),indent=2))
    else:
        with open(args.profile,encoding='utf-8-sig') as f:
            profile=json.load(f)
        if args.action=='check-profile':
            try:
                print(json.dumps(validate_profile(profile),ensure_ascii=False,indent=2))
            except (ValueError,TypeError,RuntimeError) as exc:
                print(json.dumps(dict(offline_valid=False,connection_attempted=False,error=str(exc)),ensure_ascii=False))
                raise SystemExit(2)
            return
        with connect(profile) as device:
            identity=getattr(device,'identity',None)
            print(json.dumps(asdict(identity) if identity else {'controller_identified':True},ensure_ascii=False))


if __name__=='__main__': main()
