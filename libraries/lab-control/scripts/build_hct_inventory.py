"""Build the HCT-only inventory from reviewed report table snapshots, offline."""
from pathlib import Path
import collections
import csv
import json
import re
from build_inventory import maker_name, model_name, capability

ROOT=Path(__file__).resolve().parents[1]


def canonical(maker, model):
    key=re.sub('[^A-Z0-9]','',maker.upper())
    if key.startswith('INNCO'): maker='Innco systems'
    elif key.startswith('HEWLETT') or key=='AGILLENT': maker='Keysight/Agilent/HP'
    elif key in ('TNMSYSTEM','TMSYSTEM'): maker='T&M/TNM system'
    elif key.startswith('SCHWARZBECK'): maker='Schwarzbeck'
    elif key.startswith('ANRITSU'): maker='Anritsu'
    elif key.startswith('HCTCO'): maker='HCT CO., LTD'
    else: maker=maker_name(maker)
    model=model_name(model).replace('SMW-200A','SMW200A')
    if maker=='ODA': model=model.replace('EX 60-40','EX60-40')
    if maker=='Schwarzbeck': model=re.sub(r'\s+','',model)
    if maker=='Rohde & Schwarz' and model.startswith('ZNB '): model=model.replace('ZNB ','ZNB')
    return maker,model


def support(maker, model, descriptions):
    text=' '.join(descriptions).lower()
    if maker=='ODA' and model=='EX60-40':
        return 'conditional','OdaEx','EX family 3필드 IDN + serial/firmware 결합·명판 확인 후 전압/전류·ON/OFF·측정. 범용 EX 문서와 EX60-40 사양 대조; 실물 미검증','oda-ex'
    if maker=='Rohde & Schwarz' and model=='CMU200':
        return 'implemented_uncommissioned','Cmu200Cw','RF_NSig CW 발생기만: secondary 1–29 검증·RF1/2/3·100kHz–2.7GHz·INIT/ABOR·상태조회. 셀룰러/BT signalling 미구현','rs-cmu-base'
    if maker=='Keysight/Agilent/HP' and model in ('E8267D','E4421B','E4433B'):
        return 'implemented_uncommissioned','SignalGenerator','CW 주파수·고정 출력·변조 OFF·RF ON/OFF와 재조회; 임의 변조/DFS 파형은 미구현','keysight-psg' if model=='E8267D' else 'keysight-esg-b'
    if model in ('OSP 120','OSP 150'):
        return ('implemented_uncommissioned' if model=='OSP 120' else 'controller_component'),'OspSwitch','OSP120/130 호스트의 B101/B102 릴레이 경로 선택·조회·현장 안전 경로 복귀. OSP150은 CAN 확장, 모듈 옵션 미확정','rs-osp'
    if maker=='Keysight/Agilent/HP' and model=='E4419B':
        return 'implemented_uncommissioned','EpmPowerMeter','입력 A/B·기존 센서 교정표·평균전력 읽기·ABOR1/2 정지','keysight-e4419b'
    if maker=='Rohde & Schwarz' and model in ('ZNB8','ZNB20'):
        return 'implemented_uncommissioned','VectorNetworkAnalyzer','S11 복소 trace·보정 상태·RF OFF; 포트 옵션/정확한 IDN과 기존 교정 필요','rs-znb'
    if model=='PWR800L':
        return 'controller_required','','TP-BUS 전원: PIA4810/4830/4850 설치 제어기 확인 필요. 직접 SCPI/LAN 모델 아님','kikusui-pwr-legacy'
    if model=='CBT':
        return 'pending_protocol','','전체 매뉴얼 PDF 취득 403. GPIB secondary address별 기능 그룹 분리; 설치 버전/주소와 명령 검토 필요','rs-cbt'
    if model in ('3025C','3035C'):
        return 'pending_protocol','','성적서는 ADLINK로 기재. VIAVI 제조사 문서의 동명 PXI 모듈과 제조사 불일치; 실제 모듈 명판/드라이버·DFS 옵션 확인 필요',''
    if model=='175-H1/THERMOMETER':
        return 'pending_protocol','','Testo USB/SD + ComSoft 경로 확인. 범용 SCPI 아님; 설치 SDK 또는 실제 export 형식 필요',''
    if model=='SAR SYSTEM CONTROL PC' or model=='EP-T2510':
        return 'support_or_software','','시험 지원 PC/전원 어댑터. 운영 환경과 연결 정보 관리',''
    if any(w in text for w in ('power divider','directional bridge','broadband lna')):
        return 'passive_or_fixture','','RF 경로·전원·교정 데이터 관리. 독립 원격 명령은 확인하지 않음',''
    if model in ('CMU200','E5515C','NY-THR18750','175-H1/THERMOMETER'):
        return 'pending_protocol','','정확한 통신 옵션·프로그램 명령과 설치 설정 확인 필요',''
    if model=='8310-202-F':
        return 'vendor_required','','프로그래머블 감쇠기: 실제 제어기/인터페이스·감쇠 숫자 맵 필요',''
    if maker=='Innco systems':
        if model=='CO3000':
            return 'implemented_uncommissioned','Co3000','축 발견·위치/편파·한계 조회·속도 1–8·이동·전체 ES 정지','innco-co3000'
        return 'controller_component','Co3000','CO3000의 실제 *OPT? 축 매핑 필요. 마스트 cm/테이블 degree; 직접 LAN 장비로 간주하지 않음','innco-co3000'
    if maker=='T&M/TNM system':
        return 'vendor_required','','스위치/필터 경로 맵·제어기 프로토콜·조회/정지 응답 미확보',''
    if maker=='HCT CO., LTD' or maker.startswith('HCT CO.'):
        return 'vendor_required','','HCT 내부 시험 소프트웨어: 설치 버전·외부 API·시험 레시피 필요',''
    if maker=='Anritsu' or maker=='STAUBLI' or model in ('CBT','3025C','3035C','EX60-40'):
        return 'pending_protocol','','장비표 확인. 해당 모델의 프로그래밍/SDK·설치 옵션과 명령 검토 필요',''
    if maker=='ETS-Lindgren' and model=='N/A':
        return 'model_required','','턴테이블 모델·컨트롤러 연결 미상. 인접 CO3000과의 연결을 추정하지 않음',''
    result=capability(maker,model,descriptions)
    if maker=='ESPEC':
        return 'conditional','EspecController','SU-642 장착 컨트롤러가 P300/SCP220인지 확인 후 온도·RUN/STANDBY 적용','espec-chamberconnect'
    return result


def main():
    tables=json.loads((ROOT/'research/hct-equipment-tables.json').read_text(encoding='utf-8'))
    rows=[];skips=[]
    for t in tables:
        header=[s.lower() for s in t['cells'][t['header_row']]]
        mi=next(i for i,s in enumerate(header) if 'manufactur' in s)
        mo=next(i for i,s in enumerate(header) if 'model' in s)
        de=next((i for i,s in enumerate(header) if s in ('equipment','type','device type')),None)
        se=next((i for i,s in enumerate(header) if 'serial' in s or s=='s/n'),None)
        for index,cells in enumerate(t['cells'][t['header_row']+1:],t['header_row']+1):
            if len(cells)<=max(mi,mo) or not cells[mi] or not cells[mo] or (de is not None and not cells[de]) or cells[0].startswith(('Note:','(Rev.','F-TP','TP22','22-03')):
                skips.append(dict(source_id=t['source_id'],pdf_page=t['pdf_page'],row=index,cells=cells,reason='blank/section/footer/note'))
                continue
            model=cells[mo]
            desc=cells[de] if de is not None else model
            if de is None and ' / ' in model:
                desc,model=model.rsplit(' / ',1)
            elif de is None and '/' in model and t['source_id']=='hct-a276-sar' and model.startswith('SIGNAL GENERATOR/'):
                desc,model=model.split('/',1)
            maker,model=canonical(cells[mi],model)
            rows.append(dict(manufacturer=maker,model=model,description=desc,manufacturer_raw=cells[mi],model_raw=cells[mo],
                serial=cells[se] if se is not None else '',cells=cells,row=index,
                **{k:t[k] for k in ('source_id','report','issue_date','pdf_page','table','source_url','source_sha256')}))
    groups={}
    for row in rows:
        groups.setdefault((row['manufacturer'],row['model']),[]).append(row)
    inventory=[]
    for (maker,model),members in sorted(groups.items()):
        descriptions=sorted({r['description'] for r in members})
        status,driver,scope,source=support(maker,model,descriptions)
        inventory.append(dict(manufacturer=maker,model=model,descriptions=descriptions,status=status,driver=driver,scope_ko=scope,source_id=source,
            physical_verified=False,occurrences=members))
    def save(path,data): (ROOT/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save('research/hct-equipment-rows.json',rows)
    save('research/hct-extraction-skips.json',skips)
    save('dgm_lab/data/hct-2026-instruments.json',inventory)
    reports=json.loads((ROOT/'research/hct-report-review.json').read_text(encoding='utf-8'))
    nr_pages=[p[0] for r in reports if r['included'] and r['report_candidate']=='HCT-RF-2604-FC051' for p in r['printed_page_numbers']]
    nr_complete=sorted(nr_pages)==list(range(1,372))
    stats=dict(qualified_pdf_parts=sum(r['included'] for r in reports),distinct_reports=len({r['report_candidate'] for r in reports if r['included']}),
        equipment_rows=len(rows),manufacturer_model_groups=len(inventory),status_counts=dict(collections.Counter(r['status'] for r in inventory)),physical_tests=0,
        exhaustive_hct_2026_population=False,nr_report_incomplete=not nr_complete,nr_printed_pages_verified=len(set(nr_pages)))
    save('research/hct-validation.json',stats)
    with (ROOT/'docs/hct-2026-equipment.csv').open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.writer(file);writer.writerow(['Manufacturer','Model','Role','Status','Driver','Scope','Report pages'])
        for r in inventory:
            refs=sorted({f"{o['report']} PDF p.{o['pdf_page']}" for o in r['occurrences']})
            writer.writerow([r['manufacturer'],r['model'],' / '.join(r['descriptions']),r['status'],r['driver'],r['scope_ko'],'; '.join(refs)])
    lines=['# HCT 2026 장비·설비 목록','',f"확보·발행일 확인 {stats['qualified_pdf_parts']} PDF 조각 / {stats['distinct_reports']} 보고서. 장비표 {len(rows)}행, 제조사·모델 {len(inventory)}그룹. HCT의 2026년 전체 발행 모집단을 확보한 결과는 아닙니다.",'',
        f"NR n66 371페이지 연속성 검사: {'통과' if nr_complete else '미완료'}. 2025년 발행·2026년 교정 만료 자료는 제외합니다. HCT Korea와 HCT America를 혼합하지 않습니다.",'',
        '[실행·명령표](HCT_CONTROL.md) · [CSV](hct-2026-equipment.csv) · [행별 원문·해시](../research/hct-equipment-rows.json) · [제외 행 감사](../research/hct-extraction-skips.json)','',
        '## 기준 원문','', '| 보고서 | 발행일 | PDF |','| --- | --- | --- |']
    for r in reports:
        if r['included']: lines.append(f"| {r['report_candidate']} | {r['issue_date']} | [{r['id']}]({r['url']}) ({r['pages']}p) |")
    lines+=['','## 제조사·모델별 제어 범위','','| 제조사 / 모델 | 역할 | 상태·드라이버 | 제공 범위 / 부족한 정보 | 근거 |','| --- | --- | --- | --- | --- |']
    for r in inventory:
        o=r['occurrences'][0]
        lines.append(f"| {r['manufacturer']} / {r['model']} | {' / '.join(r['descriptions'])} | {r['status']} / {r['driver']} | {r['scope_ko']} | [{o['report']} p.{o['pdf_page']}]({o['source_url']}) |")
    (ROOT/'docs/HCT_2026_EQUIPMENT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False))


if __name__=='__main__': main()
