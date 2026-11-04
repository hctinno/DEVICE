"""Verify committed research snapshots independently of the original APK files."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'evidence/manifest.json'


def digest(path):
    # Git may convert CRLF/LF on checkout; textual evidence uses canonical LF.
    return hashlib.sha256(path.read_text(encoding='utf-8-sig').replace('\r\n','\n').encode('utf-8')).hexdigest()


def freeze():
    paths=sorted((ROOT/'evidence').glob('*.java'))
    paths+=sorted((ROOT/'evidence').glob('*.xml'))
    paths+=sorted((ROOT/'evidence').glob('*-original.txt'))
    paths += [ROOT/'dgm_rf/data'/name for name in ['numeric-arguments.json','numeric-arguments.csv','NUMERIC_ARGUMENTS.md','channels-6ghz.csv']]
    manifest=dict(algorithm='sha256-utf8-lf-no-bom',files={p.relative_to(ROOT).as_posix():digest(p) for p in paths})
    if MANIFEST.exists():
        previous=json.loads(MANIFEST.read_text(encoding='utf-8'))
        if 'derived_documents' in previous:
            manifest['derived_documents']=previous['derived_documents']
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


def verify():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for relative,expected in manifest['files'].items():
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT) or digest(path)!=expected:
            raise ValueError('Research snapshot hash mismatch: '+relative)
    print(f"PASS: {len(manifest['files'])} research snapshot hashes; original APKs not checked")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true',help='Explicitly record a newly reviewed evidence snapshot')
    if parser.parse_args().freeze:
        freeze()
    verify()
