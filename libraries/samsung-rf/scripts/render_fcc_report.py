"""Render Korean inventories from checked-in UTF-8 data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    db=json.loads((ROOT/'dgm_rf/data/fcc-2026.json').read_text(encoding='utf-8'))
    rows=json.loads((ROOT/'research/fcc-2026/manifest.json').read_text(encoding='utf-8'))
    lines=['# FCC 확보 파일·시험 조건 목록','',
           '생성: `python scripts/render_fcc_report.py`. 페이지는 각 PDF 파일의 1부터 시작하는 위치입니다.',
           'PDF 수는 보고서 수와 다릅니다. 분할 파일·공유 모델 자료가 포함됩니다. 부분 확보 파일은 전체 성적서로 취급하지 않습니다.','',
           '## 시험 묶음','', '| ID | 기술 | 시험항목 | 원문·PDF 페이지 | 제어 상태 |','| --- | --- | --- | --- | --- |']
    for g in db['groups']:
        ev=' / '.join(f"[{e['exhibit_id']}]({e['pdf_url']}) p.{','.join(map(str,e['pdf_pages']))}" for e in g['evidence']) or 'RF 세부 원문 미확보'
        lines.append(f"| {g['id']} | {g['radio']} | {', '.join(g['test_items'])} | {ev} | 실물 차단·제조사 프로토콜 필요 |")
    lines+=['','## 확보 파일','', '| FCC ID | Exhibit | PDF 페이지 | 크기(bytes) | 신원 근거 |','| --- | --- | ---: | ---: | --- |']
    for r in rows:
        identity='표지 FCC ID' if r.get('identity_check')=='fcc_id_in_first_8_pages' else '표지 해시 + 전 페이지 보고서 번호'
        filing=f" (제출 경로 {r['filing_fcc_id']})" if r.get('filing_fcc_id') else ''
        lines.append(f"| {r['fcc_id']}{filing} | [{r['id']}]({r['pdf_url']}) | {r.get('pages','-')} | {r.get('bytes','-')} | {identity} |")
    lines+=['','전체 URL·SHA-256·다운로드 상태: [manifest.json](../research/fcc-2026/manifest.json).',
            '로컬 PDF는 `.fcc-cache/<exhibit_id>.pdf`에 보관합니다. 원문은 수정하거나 합치지 않습니다.','']
    (ROOT/'docs/FCC_INVENTORY.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__': main()
