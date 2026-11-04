"""Extract table rows from the acquired FCC set; retain row/page provenance for review."""
from pathlib import Path
import json
import re
import fitz
import argparse

ROOT=Path(__file__).resolve().parents[1]
RF=ROOT.parent/'samsung-rf'

def clean(value): return re.sub(r'\s+',' ',value or '').strip()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rescan',action='store_true');args=parser.parse_args()
    manifest=json.loads((RF/'research/fcc-2026/manifest.json').read_text(encoding='utf-8'))
    rows=[];audit=[];tables=[]
    dest=ROOT/'research';dest.mkdir(exist_ok=True)
    table_cache=dest/'equipment-tables.json'
    if table_cache.exists() and not args.rescan:
        tables=json.loads(table_cache.read_text(encoding='utf-8'))
    else:
        tables=scan(manifest)
        table_cache.write_text(json.dumps(tables,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for table in tables:
        header=None;count=0
        for ri,row in enumerate(table['cells']):
            values=[clean(v) for v in row if clean(v)]
            low=[v.lower() for v in values]
            if any('manufacturer' in v for v in low) and any('model' in v for v in low):
                header=low
                continue
            if header is None: continue
            maker=next(i for i,v in enumerate(header) if 'manufacturer' in v)
            model=next(i for i,v in enumerate(header) if 'model' in v)
            desc=next((i for i,v in enumerate(header) if any(x in v for x in ['description','equipment','test instrument'])),None)
            if desc is None: desc=0
            if len(values)<=max(maker,model,desc) or len(values)>len(header)+1: continue
            if not values[model] or values[model].lower() in ['model','type/model']: continue
            if values[maker]==values[model]==values[desc]: continue
            if values[maker] in ['AC','USB','Ports','Port','RF In/Out']: continue
            rows.append(dict(description=values[desc],manufacturer_raw=values[maker],model_raw=values[model],
                             extra=values,exhibit_id=table['exhibit_id'],pdf_page=table['pdf_page'],
                             table=table['table'],row=ri,source_sha256=table['source_sha256'],source_url=table['source_url']))
            count+=1
        audit.append(dict(exhibit_id=table['exhibit_id'],page=table['pdf_page'],table=table['table'],extracted_rows=count))
    (dest/'equipment-rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dest/'extraction-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    models={}
    for r in rows:
        key=(r['manufacturer_raw'],r['model_raw'],r['description'])
        models.setdefault(key,[]).append(f"{r['exhibit_id']}:{r['pdf_page']}")
    for (maker,model,desc),refs in sorted(models.items()): print(f'{maker} | {model} | {desc} | {refs[0]}')
    print(f'{len(rows)} rows; {len(models)} distinct description/manufacturer/model tuples')

def scan(manifest):
    tables=[]
    for entry in manifest:
        eid=entry['id']
        pages=json.loads((RF/'.fcc-cache'/f'{eid}.pages.json').read_text(encoding='utf-8'))
        doc=None
        for i,text in enumerate(pages):
            if not (re.search(r'manufacturer',text,re.I) and re.search(r'model',text,re.I)):
                continue
            if doc is None: doc=fitz.open(RF/'.fcc-cache'/f'{eid}.pdf')
            for ti,table in enumerate(doc[i].find_tables().tables):
                cells=table.extract()
                joined=' '.join(clean(v) for row in cells for v in row)
                if not (re.search('manufacturer',joined,re.I) and re.search('model',joined,re.I)):
                    continue
                tables.append(dict(exhibit_id=eid,pdf_page=i+1,table=ti,cells=cells,
                                   source_sha256=entry['sha256'],source_url=entry['pdf_url']))
        if doc: doc.close()
    return tables

if __name__=='__main__': main()
