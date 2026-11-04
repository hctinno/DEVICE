"""Build the public manufacturer/model/function index from the actual driver catalogs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sdk = json.loads((ROOT / 'libraries/device-control/dgm_control/data/catalog.json').read_text(encoding='utf-8'))
    records = {}
    for item in sdk['devices']:
        if item.get('backend') != 'dgm_lab':
            continue
        for model in item.get('models', []) + item.get('report_models', []):
            key = (model['manufacturer'], model['model'], item['id'])
            equipment_type = item['equipment_type']
            if item['id'] == 'Co3000':
                equipment_type = ('안테나 마스트' if model['model'].startswith('MA') else
                                  '턴테이블' if model['model'].startswith('DS') else '모션 제어기')
            records[key] = {'manufacturer': model['manufacturer'], 'model': model['model'],
                            'equipment_type': equipment_type, 'driver': item['id'],
                            'operations': [operation for operation in item['operations']
                                if operation not in item.get('operation_models', {})
                                or model['model'] in item['operation_models'][operation]],
                            'status': model['status'], 'physical_verified': False}
    lines = ['# 제어 라이브러리 장비·설비 지원 목록', '',
             '제조사·모델·장비 종류·구현 API를 기준으로 정리합니다. 특정 기관의 보유 자산 목록이 아닙니다. '
             '지원은 명시한 기능과 모델/옵션 범위에 한정하며 실장비 검증은 미실행입니다.', '',
             '| 장비·설비 종류 | 제조사 | 모델 | 드라이버 | 제어 API | 상태 |',
             '| --- | --- | --- | --- | --- | --- |']
    for key, record in sorted(records.items()):
        operations = ', '.join(record['operations'])
        lines.append(f"| {record['equipment_type']} | {record['manufacturer']} | {record['model']} | {record['driver']} | {operations} | {record['status']} |")
    lines += ['', '## 단말 제어', '',
              '`PhoneAt`은 단말의 정확한 모델·build·허용 명령·숫자 인수를 담은 프로파일을 요구합니다. '
              '브랜드명을 제거해도 단말 호환 범위가 확대되지 않습니다. 모든 단말에 적용되는 범용 AT 표로 해석하지 않습니다.', '',
              '## 상태의 의미', '',
              '`implemented_uncommissioned` 또는 `implemented-uncommissioned`: 명시한 기능 구현·현장 미검증. `conditional`: 설치 옵션/컨트롤러 확인 후 사용. '
              '`controller_component`: 독립 접속 대상이 아닌 제어기에 연결된 구성품입니다.', '',
              '[설치·공통 API](libraries/device-control/README.md) · [가상 시험환경](libraries/device-control/VIRTUAL_LAB.md) · '
              '[모델별 상세 조건](libraries/lab-control/docs/EQUIPMENT_COVERAGE.md) · '
              '[QP·평균 검파 지원/미확인](libraries/device-control/DETECTORS.md) · '
              '[기계 판독 목록](libraries/device-control/dgm_control/data/supported-equipment.json)', '']
    (ROOT / 'SUPPORTED_EQUIPMENT.md').write_text('\n'.join(lines), encoding='utf-8')
    target = ROOT / 'libraries/device-control/dgm_control/data/supported-equipment.json'
    target.write_text(json.dumps(list(records.values()), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(records)} manufacturer/model/driver records rendered')


if __name__ == '__main__':
    main()
