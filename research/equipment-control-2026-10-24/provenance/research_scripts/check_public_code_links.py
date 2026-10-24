from pathlib import Path
import json,urllib.request,urllib.parse,concurrent.futures,datetime,hashlib
ROOT=Path('/workspace/research/equipment-control-full-2026-10-24')
path=ROOT/'code_link_checks.json'
old=json.loads(path.read_text()) if path.exists() else []
known={r['source_url']:r for r in old};urls=set()
for p in ROOT.glob('results/*/results.json'):
 for r in json.loads(p.read_text()):
  for s in r.get('sources',[]):
   if s.get('kind')=='source_code' and urllib.parse.urlsplit(s.get('url','')).hostname in ('github.com','raw.githubusercontent.com'):
    urls.add(s['url'])
def check(u):
 p=urllib.parse.urlsplit(u);parts=p.path.strip('/').split('/')
 v=u.split('#')[0]
 if p.hostname=='github.com' and len(parts)>=5 and parts[2]=='blob':
  v='https://raw.githubusercontent.com/'+'/'.join(parts[:2]+parts[3:])
 result={'source_url':u,'checked_url':v,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'code_executed':False}
 try:
  req=urllib.request.Request(v,headers={'User-Agent':'Equipment-control-public-source-link-verification'})
  with urllib.request.urlopen(req,timeout=20) as resp:
   b=resp.read(1024*1024)
   result.update(http_status=resp.status,resolved_url=resp.geturl(),content_type=resp.headers.get('Content-Type'),bytes_read=len(b),body_prefix_sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:result.update(error=str(e))
 return result
todo=sorted(urls-set(known))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for r in ex.map(check,todo):known[r['source_url']]=r
path.write_text(json.dumps(list(known.values()),ensure_ascii=False,indent=2))
print(json.dumps({'checked_now':len(todo),'total':len(known),'http200':sum(r.get('http_status')==200 for r in known.values()),'errors':[{'url':r['source_url'],'error':r.get('error'),'status':r.get('http_status')} for r in known.values() if r.get('http_status')!=200]},ensure_ascii=False))

