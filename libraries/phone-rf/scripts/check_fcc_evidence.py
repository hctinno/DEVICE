"""Verify portable evidence metadata; optionally verify local PDF bytes and page coverage."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--pdfs',action='store_true');args=p.parse_args()
    sources=json.loads((ROOT/'research/fcc-2026/sources.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'research/fcc-2026/manifest.json').read_text(encoding='utf-8'))
    rows={r['id']:r for r in manifest}
    assert len(rows)==len(manifest)==len(sources)
    for source in sources:
        r=rows[source['id']]
        assert r['status']=='acquired',r
        assert r['pdf_url']==source['pdf_url'] and r['fcc_id']==source['fcc_id']
        assert re.fullmatch('[0-9a-f]{64}',r['sha256'])
        if r.get('identity_parent'):
            assert r['identity_parent_sha256']==rows[r['identity_parent']]['sha256']
        if args.pdfs:
            raw=(ROOT/'.fcc-cache'/f"{r['id']}.pdf").read_bytes()
            assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],r['id']
    db=json.loads((ROOT/'dgm_rf/data/fcc-2026.json').read_text(encoding='utf-8'))
    for g in db['groups']:
        for e in g['evidence']:
            r=rows[e['exhibit_id']]
            assert e['sha256']==r['sha256']
            assert r['fcc_id']==db['devices'][g['device']]['fcc_id']
            assert all(type(n) is int and 1<=n<=r['pages'] for n in e['pdf_pages'])
    coverage={}
    if args.pdfs:
        families={
            'fold8_6ghz':('S-4792147575-E13V4',161,[str(n) for n in range(9312879,9312886)]),
            'duo_6ghz_conducted':('16064952-E12V3',778,['9564181','9564182','9564195']+
                                  [str(n) for n in range(9564197,9564210)])}
        for name,(report,total,ids) in families.items():
            seen=[]
            for exhibit in ids:
                pages=json.loads((ROOT/'.fcc-cache'/f'{exhibit}.pages.json').read_text(encoding='utf-8'))
                for page_index,page in enumerate(pages):
                    assert report in page,(name,exhibit)
                    match=re.search(r'Page\s+(\d+)\s+of\s+'+str(total),page,re.I)
                    if exhibit=='9312879' and page_index==0 and 'CERTIFICATION TEST REPORT' in page:
                        # This reviewed cover has no printed page number; page 2 follows.
                        assert not match
                        seen.append(1)
                        continue
                    assert match,(name,exhibit,'page label')
                    seen.append(int(match[1]))
            assert sorted(seen)==list(range(1,total+1)),(name,'missing/duplicate pages')
            coverage[name]=dict(expected_pages=total,verified_pages=len(seen),complete=True)
    result=dict(status='PASS',pdf_files=len(rows),pdf_pages=sum(r['pages'] for r in rows.values()),
                pdf_bytes=sum(r['bytes'] for r in rows.values()),groups=len(db['groups']),cases=len(db['cases']),
                local_pdf_bytes_verified=args.pdfs,complete_reports=coverage,hardware_tests=0)
    if args.pdfs:
        (ROOT/'research/fcc-2026/validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
