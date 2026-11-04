"""Render exact registered model extensions and their pinned official provenance."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dgm_lab.model_scope import model_rows
from dgm_lab.detectors import RECEIVER_RANGES

sources = {s['id']:s for s in json.loads((ROOT/'dgm_lab/data/sources.json').read_text(encoding='utf-8'))}
rows = model_rows()
for row in rows:
    source = sources[row['source_id']]
    if source['status'] != 'acquired': raise ValueError('Missing official manual: ' + row['source_id'])
    row['url'], row['sha256'] = source['url'], source['sha256']
    if row['source_id']=='rs-nrps':
        range_source=sources['rs-nrp-range']
        if range_source['status']!='acquired': raise ValueError('Missing NRP range reference')
        row.update(range_source_id='rs-nrp-range',range_url=range_source['url'],range_sha256=range_source['sha256'],range_reviewed_pdf_pages=[11,30,32])
    if row['driver']=='DigitalMultimeter': row['reviewed_pdf_pages'] = [201,202,239,240,241,246,248,350,370,374,379,382]
    if any(p>source['pages'] for p in row['reviewed_pdf_pages']): raise ValueError('Invalid PDF evidence page')
(ROOT/'dgm_lab/data/model-expansion.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
contracts_path = ROOT/'research/capability-contracts.json'
contracts = json.loads(contracts_path.read_text(encoding='utf-8'))
contracts['EmiReceiver']['operation_models']['read_verified_level'] = list(RECEIVER_RANGES)
contracts_path.write_text(json.dumps(contracts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines = ['# 확장 제어 모델·근거 목록','',
         '생성: scripts/build_model_expansion.py. 지원 상태는 implemented-uncommissioned이며 실장비 검증이 아닙니다. 기존 재고/성적서 목록은 변경하지 않습니다.',
         '',f'확장 manifest: {len(rows)}개 역할/모델 조합, {len({r["model"] for r in rows})}개 고유 모델명. 분석기·최종 검파 역할의 같은 모델을 별도 장비 수로 세지 않습니다.','',
         '| 제어 역할 | 제조사 / 모델 | 이번 실행 범위 | 공식 근거·PDF 페이지 |', '| --- | --- | --- | --- |']
for r in rows:
    pages = ','.join(map(str,r['reviewed_pdf_pages']))
    lines.append(f'| {r["driver"]} | {r["manufacturer"]} / {r["model"]} | {r["scope"]} | [{r["source_id"]}]({r["url"]}), pp.{pages} |')
lines += ['', 'NRP40/50/67/90 계열의 50 MHz 하한은 [제조사 모델·주파수 표]('+sources['rs-nrp-range']['url']+')를 함께 확인했습니다. 검색된 예전 사양서 URL은 HTTP 404로 원본을 확보하지 못해 현재 다운로드 가능한 공식 브로슈어를 pin했습니다.', '', '원본 PDF SHA-256·적용 모델·매뉴얼 펌웨어 범위는 [기계 판독 목록](../dgm_lab/data/model-expansion.json)에 있습니다. 매뉴얼의 펌웨어 범위는 설치 펌웨어 검증 결과가 아닙니다. 기존 단말/시설 제어 범위·교정/판정 한계는 그대로이며 수동 설치 검수가 필요합니다.','']
(ROOT/'docs/MODEL_EXPANSION.md').write_text('\n'.join(lines),encoding='utf-8')
print(f'{len(rows)} extension role/model rows, {len({r["model"] for r in rows})} distinct model names')
