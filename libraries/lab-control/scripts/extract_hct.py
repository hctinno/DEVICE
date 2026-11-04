"""Extract full equipment tables without dropping empty cells or their provenance."""
from pathlib import Path
import json
import re
import fitz

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.fcc-cache/hct-2026'
GEOMETRY={
    ('hct-a276-emc',14): [70,183,268,351,428,469,525],
    ('hct-a276-emc',15): [70,183,268,351,428,469,525],
    ('hct-a276-dfs',19): [65,171,266,343,432,489,546],
    ('hct-a276-nfc',27): [65,172,257,336,418,480,538],
    ('hct-a276-nr',20): [32,174,299,372,452,510,560],
    ('hct-a276-sar',15): [75,135,307,378,425,479,527],
    ('hct-a276-sar',16): [75,135,307,378,425,479,527],
}


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def main():
    manifest=json.loads((ROOT/'research/hct-2026-manifest.json').read_text(encoding='utf-8'))
    tables=[]
    reports=[]
    for source in manifest:
        if source['status']!='acquired':
            continue
        pages=json.loads((CACHE/(source['id']+'.pages.json')).read_text(encoding='utf-8'))
        cover=' '.join(pages[:2])
        issued=re.search(r'DATE\s+OF\s+ISSUE\s+([A-Za-z]+\.?\s+\d+,?\s+20\d\d)',cover,re.I)
        if issued is None:
            qualified=source['id'] in ('hct-a276-nr-last','hct-a276-nr-p2','hct-a276-nr-p3','hct-a276-nr-p4') and source['report_candidate']=='HCT-RF-2604-FC051'
            date='April 27, 2026' if qualified else None
        else:
            date=issued[1]
            qualified=date.endswith('2026') and bool(re.search(r'HCT\s*CO\.',cover,re.I))
        report=dict(source,issue_date=date,issue_date_verified=qualified,
                    qualification='cover_reviewed' if issued else 'same_report_header_as_hct-a276-nr',
                    included=qualified)
        numbered=[]
        for text in pages:
            match=re.search(r'Page\s+(\d+)\s+of\s+(\d+)',text,re.I)
            if match: numbered.append([int(match[1]),int(match[2])])
            else:
                match=re.search(r'\b(\d+)\s*/\s*(\d+)\b',text)
                if match: numbered.append([int(match[1]),int(match[2])])
        report['printed_page_numbers']=numbered
        reports.append(report)
        if not qualified:
            continue
        with fitz.open(CACHE/(source['id']+'.pdf')) as doc:
            for i,page in enumerate(doc):
                text=pages[i]
                if not re.search('manufactur',text,re.I) or not re.search('model',text,re.I):
                    continue
                vertical=GEOMETRY.get((source['id'],i+1))
                found=page.find_tables(vertical_strategy='explicit',vertical_lines=vertical).tables if vertical else page.find_tables().tables
                for ti,table in enumerate(found):
                    cells=[[clean(c) for c in row] for row in table.extract()]
                    if vertical:
                        # Re-read whole words by centre: prevents clipping boundary letters.
                        words=page.get_text('words')
                        for ri,row in enumerate(table.rows):
                            bounds=next((b for b in row.cells if b and b[3]-b[1]<100),None)
                            if not bounds: continue
                            y0,y1=bounds[1],bounds[3]
                            cells[ri]=[clean(' '.join(w[4] for w in words if x0<=(w[0]+w[2])/2<x1 and y0<=(w[1]+w[3])/2<y1)) for x0,x1 in zip(vertical,vertical[1:])]
                    for ri,row in enumerate(cells):
                        lower=[c.lower() for c in row]
                        if any('manufactur' in c for c in lower) and any('model' in c for c in lower):
                            tables.append(dict(source_id=source['id'],report=source['report_candidate'],issue_date=date,
                                pdf_page=i+1,table=ti,header_row=ri,cells=cells,
                                source_url=source['url'],source_sha256=source['sha256']))
                            break
    (ROOT/'research/hct-equipment-tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'research/hct-report-review.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for t in tables:
        print(t['source_id'],t['pdf_page'],len(t['cells'])-t['header_row']-1,t['cells'][t['header_row']])


if __name__=='__main__': main()
