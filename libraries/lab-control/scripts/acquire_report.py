"""Acquire bounded report candidates; issue-year qualification is a separate reviewed step."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import re
import requests
import fitz

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.fcc-cache/report-2026'


def acquire(source):
    result=dict(source)
    try:
        target=CACHE/(source['id']+'.pdf')
        if not target.exists():
            r=requests.get(source['url'],timeout=(10,60));r.raise_for_status()
            if not r.content.startswith(b'%PDF'): raise ValueError('Response is not PDF')
            target.write_bytes(r.content)
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if source.get('sha256') and source['sha256']!=digest: raise ValueError('Pinned PDF SHA changed')
        with fitz.open(target) as doc: pages=[p.get_text() for p in doc]
        (CACHE/(source['id']+'.pages.json')).write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
        cover='\n'.join(pages[:3])
        report=re.search(r'HCT-(?:RF|EM|SR)-\d{4}-[A-Z0-9-]+',cover)
        dates=re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}',cover,re.I)
        interesting=[i+1 for i,p in enumerate(pages) if re.search(r'turn\s*table|antenna\s*(?:mast|position|tower)|CO3000|EM2090|EM1000|test equipment|list of equipment',p,re.I)]
        result.update(status='acquired',sha256=digest,pages=len(pages),bytes=target.stat().st_size,
                      report_candidate=report.group() if report else None,cover_dates=dates,
                      interesting_pages=interesting,issue_date_verified=False)
    except Exception as exc: result.update(status='failed',error=str(exc))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='*');a=p.parse_args()
    CACHE.mkdir(parents=True,exist_ok=True)
    path=ROOT/'research/report-2026-manifest.json'
    old={r['id']:r for r in json.loads(path.read_text(encoding='utf-8'))} if path.exists() else {}
    sources=json.loads((ROOT/'research/report-2026-sources.json').read_text(encoding='utf-8'))
    selected=[r for r in sources if not a.ids or r['id'] in a.ids]
    for source in selected:
        if old.get(source['id'],{}).get('sha256'): source['sha256']=old[source['id']]['sha256']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(acquire,selected):
            old[r['id']]=r
            print(r['id'],r['status'],r.get('pages'),r.get('report_candidate'),r.get('cover_dates',[])[:3],r.get('error',''),flush=True)
    path.write_text(json.dumps(list(old.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
