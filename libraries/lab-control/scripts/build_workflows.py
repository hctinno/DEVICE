"""Attach available building blocks to every previously extracted FCC test group."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parent/'phone-rf/dgm_rf/data/fcc-2026.json'
groups=json.loads(source.read_text(encoding='utf-8'))['groups']
result=[]
for g in groups:
    radio=g['radio']
    blocks=['SpectrumAnalyzer.acquire','PSeriesPowerMeter.read_power','UsbPowerSensor.read_power']
    missing=['모델/빌드별 DUT 시험모드·숫자 인수·TX ON/OFF',
             '현장 경로/안테나/손실/교정과 시험별 설정·후처리·판정',
             '기구 위치/회전/높이 제어와 독립 종료 검증']
    if radio=='cellular':
        blocks+=['CmwLte.connected (LTE FDD RMC만)','SignalGenerator.configure_cw','EspecController.running (조건부)']
        missing+=['NR/FR2/NTN/CA 및 CMX/UXM 전용 SDK·파형·connection recipe']
    elif radio in ('wlan','bluetooth'):
        blocks+=['SignalGenerator.configure_cw']
        missing+=['DFS/CBP/TPC 전용 파형·타이밍/동반기·측정 알고리즘; CW로 대체 불가']
    elif radio=='emc':
        blocks=['EmiReceiver.read_level','SpectrumAnalyzer.acquire']
        missing+=['LISN/line selector·CISPR filter·scan/최대값 탐색·QP 재측정']
    elif radio=='exposure':
        blocks=['VectorNetworkAnalyzer.acquire_s11','PSeriesPowerMeter.read_power']
        missing+=['SPEAG licensed SAR/PD/TAS SDK·robot/probe/DAE·실제 scan/results']
    elif radio in ('uwb','nfc','wpt','ieee802154','narrowband'):
        blocks+=['EmiReceiver.read_level']
        missing+=['펄스/루프/장측정·상대기·기술별 trigger/integration 설정']
    result.append(dict(group_id=g['id'],radio=radio,device=g['device'],test_items=g['test_items'],
                       report_evidence=g['evidence'],available_building_blocks=blocks,
                       missing=list(dict.fromkeys(g.get('missing',[])+missing)),
                       end_to_end_ready=False,hardware_validated=False,
                       note='Building-block mapping only; does not assign a particular report asset to a site address.'))
(ROOT/'dgm_lab/data/fcc-workflows.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# FCC 항목과 설비 API 연결','',
       f'기존 조사에서 선정한 {len(groups)}개 시험 묶음을 빠짐없이 매핑합니다. 시험 조건의 전체 조합이나 FCC 규정 전체를 추출했다는 뜻은 아닙니다. 모든 묶음의 end_to_end_ready는 False입니다.', '',
       '장비를 제어하는 기본 API와 완성된 시험 recipe를 구분합니다. trace 수집만으로 OBW/PSD/EIRP/대역경계/DFS/SAR 판정이 완성되지 않습니다. 최신 단말의 DUT 제어와 현장 보정·기구 동작·규격별 알고리즘이 연결돼야 합니다.', '',
       '| 성적서 묶음 | 항목 | 사용 가능한 구현 요소 | 주요 미완성 조건 |','| --- | --- | --- | --- |']
for r in result:
    lines.append('| '+' | '.join([r['group_id'],', '.join(r['test_items']),'; '.join(r['available_building_blocks']),'; '.join(r['missing'])]).replace('\n',' ')+' |')
lines += ['', '[근거 페이지를 포함한 JSON](../dgm_lab/data/fcc-workflows.json) · [성적서 원래 조건](../../phone-rf/docs/FCC_LATEST_MODELS.md) · [장비별 지원표](EQUIPMENT_COVERAGE.md)', '']
(ROOT/'docs/FCC_WORKFLOWS.md').write_text('\n'.join(lines),encoding='utf-8')
print(f'{len(result)} workflow groups mapped; fully executable FCC workflows: 0')
