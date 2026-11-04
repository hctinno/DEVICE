"""Download manufacturer documents, retain hashes and page-indexed text locally."""
from pathlib import Path
import json,hashlib,concurrent.futures,argparse,re
import requests,fitz
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.manual-cache'

def acquire(row):
    r=dict(row)
    try:
        target=CACHE/(r['id']+'.pdf')
        if not target.exists():
            response=requests.get(r['url'],timeout=(10,60));response.raise_for_status()
            if not response.content.startswith(b'%PDF') and 'keysight.com' in response.url:
                match=re.search(r'(/content/dam/keysight/en/doc/[^"<>]+?\.pdf)/jcr:content',response.text)
                if match:
                    # Public asset referenced by the manufacturer's landing page.
                    resolved='https://www.keysight.com'+match.group(1)
                    response=requests.get(resolved,timeout=(10,90));response.raise_for_status()
                    r['resolved_url']=resolved
            if not response.content.startswith(b'%PDF'): raise ValueError('Not a PDF')
            target.write_bytes(response.content)
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if r.get('sha256') and digest!=r['sha256']: raise ValueError('Pinned hash changed')
        with fitz.open(target) as d: pages=[p.get_text() for p in d]
        (CACHE/(r['id']+'.pages.json')).write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
        r.update(status='acquired',sha256=digest,pages=len(pages))
    except Exception as e: r.update(status='failed',error=str(e))
    return r

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ids',nargs='*');args=parser.parse_args()
    CACHE.mkdir(exist_ok=True)
    src=json.loads((ROOT/'research/manual-sources.json').read_text(encoding='utf-8'))
    path=ROOT/'research/manual-manifest.json'
    old={r['id']:r for r in json.loads(path.read_text(encoding='utf-8'))} if path.exists() else {}
    selected=[r for r in src if not args.ids or r['id'] in args.ids]
    for r in selected:
        if old.get(r['id'],{}).get('sha256'): r['sha256']=old[r['id']]['sha256']
        if old.get(r['id'],{}).get('resolved_url'): r['resolved_url']=old[r['id']]['resolved_url']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(acquire,selected):
            old[r['id']]=r;print(r['id'],r['status'],r.get('pages',r.get('error')),flush=True)
    path.write_text(json.dumps(list(old.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
