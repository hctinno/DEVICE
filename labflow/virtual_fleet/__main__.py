"""Local virtual-fleet launcher; never opens a device transport."""
import argparse
import json
from pathlib import Path

from .catalog import load_catalog
from .integration import create_conducted_example, create_fleet, get_role_actions, inventory_topology


def main(argv=None):
    parser=argparse.ArgumentParser(description='DGM AutoLab 가상 장비 시험대')
    parser.add_argument('--catalog',type=Path,default=Path(__file__).resolve().parents[2]/'virtual_profiles/sm_a176u_unlicensed.json')
    parser.add_argument('--example',choices=('inventory','conducted'),default='inventory')
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--port',type=int,default=8770)
    parser.add_argument('--check',action='store_true',help='가상 구성을 실행·요약하고 종료합니다. 서버를 열지 않습니다.')
    args=parser.parse_args(argv)
    try:
        catalog=load_catalog(args.catalog)
        if args.example=='conducted':
            fleet,topology,receipts=create_conducted_example(catalog,seed=args.seed)
        else:
            topology=inventory_topology(catalog)
            fleet=create_fleet(catalog,topology,seed=args.seed)
            receipts=[]
        observed=fleet.observations()
        if args.check:
            coverage=fleet.coverage()
            measurements={identity:node['values']['outputs']['measurement']
                          for identity,node in observed['devices'].items()
                          if 'measurement' in node['values'].get('outputs',{})}
            print(json.dumps({'synthetic':True,'hardware_verified':False,'example':args.example,
                              'catalog_profiles':coverage['catalog_profiles'],
                              'instantiated_devices':coverage['instantiated_devices'],
                              'example_receipts':len(receipts),'tick':observed['tick'],
                              'setup_revision':observed['setup_revision'],'measurements':measurements,
                              'validation_scope':'synthetic example; all-profile acceptance is a separate test'},
                             ensure_ascii=False,allow_nan=False))
            return 0
        from labflow.virtual_fleet_server import create_server
        with create_server(fleet,catalog=catalog,topology=topology,role_actions=get_role_actions(),port=args.port) as server:
            print(f'가상 시험소 · 실장비 미검증: http://127.0.0.1:{server.server_port}',flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass
        return 0
    except (OSError,ValueError):
        print(json.dumps({'error':'virtual_configuration_error','synthetic':True,'hardware_verified':False}))
        return 1


if __name__=='__main__':raise SystemExit(main())
