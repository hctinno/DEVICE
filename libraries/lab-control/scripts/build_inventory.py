"""Normalize report rows without discarding original data; render a reviewable coverage ledger."""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dgm_lab.analyzers import SpectrumAnalyzer, EmiReceiver
from dgm_lab.sources import SignalGenerator, PowerSupply
from dgm_lab.meters import UsbPowerSensor


def maker_name(value):
    key = re.sub(r'[^A-Z0-9]', '', value.upper())
    if any(s in key for s in ('KEYSIGHT', 'AGILENT')) or key == 'HP': return 'Keysight/Agilent/HP'
    if key.startswith('ROHDESCHWARZ') or key in ('RS','RSGMBHCO'): return 'Rohde & Schwarz'
    if key.startswith('ETSLINDGREN') or key == 'ETS': return 'ETS-Lindgren'
    if key.startswith('FISCHERCUSTOM'): return 'Fischer Custom Communications'
    if key.startswith('SONOMA'): return 'Sonoma'
    if key.startswith('PASTERNACK'): return 'Pasternack'
    if key.startswith('SUNOL'): return 'Sunol'
    if key.startswith('SORENSEN'): return 'Sorensen'
    if key in ('MINICIRCUITS',): return 'Mini-Circuits'
    if key == 'ELECTROMETRICS': return 'Electro-Metrics'
    if key.startswith('ASUS'): return 'ASUS'
    if key == 'ARA': return 'A.R.A.'
    return value.strip().upper()


def model_name(value):
    value = re.sub(r'\s+SN:.*$', '', value, flags=re.I).strip()
    value = re.sub(r'\s*-\s*', '-', value)
    value = re.sub(r'\b(CMW|SMB|ESR|ESW|ESCI|FSW)\s+(?=\d)', r'\1', value)
    value = re.sub(r'^(N9030[AB]|N1912A)-.*', r'\1', value)
    value = value.replace('E7515B UXM 5G', 'E7515B')
    if value == 'SMB100A03': value = 'SMB100A'
    return value.upper()


def capability(maker, model, descriptions):
    text = ' '.join(descriptions).lower()
    mappings = [(SpectrumAnalyzer.MODELS, 'SpectrumAnalyzer', '주파수 스윕·RBW/VBW·검파기·단일 측정·trace 수집·정지'),
                (EmiReceiver.MODELS, 'EmiReceiver', '단일 주파수·RBW·검파기·측정시간·dBuV 결과·정지'),
                (SignalGenerator.MODELS, 'SignalGenerator', 'CW 주파수·출력·RF ON/OFF·설정 재조회'),
                (PowerSupply.MODELS, 'PowerSupply', '전압·전류 제한·출력 ON/OFF·전압/전류 읽기'),
                (UsbPowerSensor.MODELS, 'UsbPowerSensor', '보정 주파수·평균 전력·측정 시작/정지')]
    # A model name alone is not sufficient; prevent passive/support rows borrowing a driver.
    if maker in ('Keysight/Agilent/HP','Rohde & Schwarz','KIKUSUI'):
        for mapping, driver, scope in mappings:
            if model in mapping:
                src = mapping[model]
                return 'implemented_uncommissioned', driver, scope, src[0] if isinstance(src,tuple) else src
        if model in ('N1911A','N1912A'):
            return 'implemented_uncommissioned','PSeriesPowerMeter','채널 A/B·보정 주파수·평균 전력·정지','keysight-power'
        if model=='437B':
            return 'implemented_uncommissioned','Hp437B','HP 고유 명령 FR/SE/LG·TR2 측정·TR0 대기. 센서 교정표 확인 필요','hp-437b'
        if model=='CMW500':
            return 'conditional','CmwLte','LTE FDD RMC 셀/연결·상태 대기·해제. 시험 SIM/라우팅/라이선스 필요','rs-cmw-lte'
        if model=='ZNLE6':
            return 'implemented_uncommissioned','VectorNetworkAnalyzer','S11 복소 trace·RF ON/OFF. 기존 교정 상태 확인','rs-znle'
        if model in ('N1921A','8481A'):
            return 'host_component','', '전력계 본체를 통해 제어하는 센서. 독립 SCPI 주소 없음','keysight-power' if model=='N1921A' else ''
    if maker=='COPPER MOUNTAIN TECHNOLOGIES' and model=='PLANAR R140':
        return 'conditional','VectorNetworkAnalyzer','RVNA 21.3.1+ PC TCP 서버·S11 복소 trace·RF ON/OFF','cmt-rvna'
    if maker=='ESPEC':
        return 'conditional','EspecController','P300/SCP220 장착 확인 후 온도 설정·CONSTANT/STANDBY. SH-642의 컨트롤러는 성적서로 확정 불가','espec-chamberconnect'
    if maker=='THERMOTRON INDUSTRIES':
        return 'conditional','Thermotron8800','8800 장착/개별 장비 매뉴얼 확인 후 SETP/PVAR·RUNM/STOP. SM-16C 컨트롤러 미확정','thermotron-8800'
    if maker in ('UL','UL-FR1') or model=='CSB':
        return 'vendor_required','','UL 자체 소프트웨어·RF 스위치/필터박스: 포트 맵, 명령/SDK, 상태 응답 필요',''
    if maker=='SPEAG':
        if any(w in model for w in ('DAE','EX3','EUMMW','CSAR','DAK','POWERSOURCE')):
            return 'vendor_required','','DASY/cSAR/DAK 본체·설치 SDK/라이선스 필요. R&D API와 SAR 적합성 모듈을 혼동하지 않음','speag-dasy8'
        return 'passive_or_fixture','','교정용 다이폴/지그: 교정값·배치·연결 정보 관리 대상',''
    if maker in ('TESCOM','TA ENGINEERING','CINCINNATI SUB ZERO','Sorensen'):
        return 'vendor_required','','설치 통신 옵션·컨트롤러·제조사 프로그래밍 문서 필요',''
    if model in ('CMX500','E7515B','EMC32','SCU-18','SCU-40A','RTP5008','NRP18A','437B','N5181A','E4440A','ESR'):
        return 'pending_protocol','','모델/앱/버전에 맞는 명령 또는 SDK 연결 검증 미완료. 실행 드라이버를 제공하지 않음',''
    if model in ('N5182BX',) or maker=='VDI':
        return 'host_component','','호스트 신호발생기/분석기의 확장 모듈. 별도 보정·고조파/LO 설정 필요',''
    if any(w in text for w in ('antenna','attenuator','coupler','cable','filter','lisn','preamplifier','pre-amplifier','amplifier','v-network','dipole','adapter','headset','headphone','keyboard','mouse','charger','speaker','display','tv','monitor','splitter','combiner','termination','transient limiter')):
        return 'passive_or_fixture','','연결·보정·전원/상태 확인 대상. 독립 원격 명령은 확인하지 않음',''
    if any(w in text for w in ('laptop','computer','notebook','macbook','companion','access point','router','phone','tablet','software')):
        return 'support_or_software','','지원 PC/통신 상대/소프트웨어. 별도 운영체제·앱·네트워크 설정 필요',''
    return 'review_required','','행 원문과 설치 장비의 역할/제어 인터페이스 추가 확인 필요',''


def main():
    rows=json.loads((ROOT/'research/equipment-rows.json').read_text(encoding='utf-8'))
    groups={};review=[]
    for index,row in enumerate(rows):
        raw_maker,raw_model=row['manufacturer_raw'],row['model_raw']
        notes=[]
        if raw_maker in ('N9030A','ESW44') and maker_name(raw_model) in ('Keysight/Agilent/HP','Rohde & Schwarz'):
            raw_maker,raw_model=raw_model,raw_maker
            notes.append('원문 추출 제조사/모델 열 순서 교정')
        maker,model=maker_name(raw_maker),model_name(raw_model)
        if (maker=='ETS-Lindgren' and model=='84797') or model in ('TYPE','LENGTH (M)','(M)','# OF IDENTICAL PORTS'):
            review.append(dict(row_index=index,reason='숫자 자산번호/표 열 혼입 의심; 모델 추정 금지',**row))
            continue
        key=(maker,model)
        group=groups.setdefault(key,dict(manufacturer=maker,model=model,descriptions=[],source_rows=[],normalization_notes=[]))
        if row['description'] not in group['descriptions']: group['descriptions'].append(row['description'])
        for note in notes:
            if note not in group['normalization_notes']: group['normalization_notes'].append(note)
        group['source_rows'].append(dict(row_index=index,**row))
    inventory=[]
    for (maker,model),row in sorted(groups.items()):
        status,driver,scope,source=capability(maker,model,row['descriptions'])
        row.update(status=status,driver=driver,scope_ko=scope,source_id=source,
                   hardware_validated=False,report_calibration_is_current_site_evidence=False)
        inventory.append(row)
    out=ROOT/'dgm_lab/data';out.mkdir(parents=True,exist_ok=True)
    (out/'instruments.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'research/rows-needing-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    with (docs/'equipment-coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['제조사','모델','상태','드라이버','구현 범위/필요 정보','성적서 근거','실물 검증'])
        for r in inventory:
            refs='; '.join(sorted({f"{x['exhibit_id']}:PDF p.{x['pdf_page']}" for x in r['source_rows']}))
            writer.writerow([r['manufacturer'],r['model'],r['status'],r['driver'],r['scope_ko'],refs,'미실행'])
    counts=Counter(r['status'] for r in inventory)
    summary=dict(extracted_rows=len(rows),classified_rows=sum(len(r['source_rows']) for r in inventory),
                 review_rows=len(review),model_groups=len(inventory),statuses=dict(counts),
                 physical_equipment_tests=0,extraction_scope='Manufacturer/Model text-table candidates; not an exhaustive OCR audit')
    (ROOT/'research/inventory-validation.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    lines=['# 성적서 장비 제어 지원표','',f"추출 {len(rows)}행 → 정규화 {len(inventory)}개 제조사/모델 그룹. 모델 확인 대기 {len(review)}행. 실장비 검증 0건.",'',
           '성적서에 등장했다는 사실과 현장 보유·설치 옵션·교정 유효성을 구분합니다. 구현 상태는 아래 API 범위에 한하며 모든 장비 기능 또는 FCC 시험 전체 완료를 뜻하지 않습니다.', '',
           '자동 추출은 Manufacturer/Model 텍스트 표를 대상으로 합니다. 이미지 표·불완전한 셀·지원장비 본문은 추가 검토가 필요합니다. 원본 행과 PDF 페이지/URL/SHA-256을 JSON에 보존했습니다.', '',
           '| 제조사 | 모델 | 상태 | 드라이버 | 범위/조건 |','| --- | --- | --- | --- | --- |']
    for r in inventory:
        lines.append('| '+' | '.join(str(r[k]).replace('|','/') for k in ['manufacturer','model','status','driver','scope_ko'])+' |')
    lines += ['', '[기계 판독 목록](../dgm_lab/data/instruments.json) · [CSV](equipment-coverage.csv) · [검토 대기 원문](../research/rows-needing-review.json)', '']
    (docs/'EQUIPMENT_COVERAGE.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__': main()
