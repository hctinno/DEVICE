# Un-licensed 전체 장비 가상 프로필

2026-10-24, Asia/Seoul. `sm_a176u_unlicensed.json`은 제공된 SM-A176U Un-licensed 성적서의 장비 목록을 실행 역할에 연결하는 catalog다. 실측값·시리얼·암호·원문은 포함하지 않는다.

- 최종 6종의 장비 사용 181행과 대안 UNII 판본 37행, 총 218행을 모델·제조사·용도별 61프로필에 연결했다. 모델 표기는 55개이며 같은 모델의 용도·제조사 표기 차이를 보존했다.
- DUT 1프로필, 보조 케이블 검증 보고서의 HP8753D·NH32-ZTX-E 2프로필을 더해 총 64프로필/24역할이다. 프로필 수는 실물 장비 대수나 실행 검증 완료 수가 아니다.
- 장비 master의 66행도 대조했으며 보고서 55개 모델 표기 밖의 추가 모델은 없었다. 과거 자산의 중복/표기 차이를 현재 실물 동일성으로 확정하지 않는다.
- 원본 DOCX 근거 219곳의 해시·표/행과 모델 문자열을 대조했다. 보조 PDF 장비표는 3쪽을 시각 확인했다. 전체 판본·시리얼별 연결은 비공개 인수 기록에 보존한다.

FBSM-01B는 RF 경로 스위치 제어 역할이며 위치 제어기로 표시하지 않는다. PXI S/G와 S/A는 generator/analyzer 변형으로 나눈다. 2/4분기기와 N1911A 전력계/N1921A 센서를 분리한다. 이 구분은 장비 전체 제조사 프로토콜이나 펌웨어 검증을 의미하지 않는다.

장비표가 고정 감쇠기라고 밝힌 3/10/20 dB는 공칭값으로 보존하고 운전 중 임의 변경을 거절한다. Step Attenuator는 별도 가변 정책으로 표시하되 제조사의 단계표를 추측하지 않는다. 공칭 표기와 실제 경로 교정값은 다르며, 명시적 가상 단계표·손실과 실측 보정은 각각 구분한다.

`simulation_parameters`는 명시적 가상 정책의 자리다. 비어 있는 설정에 실제 교정값·손실·물리 한계를 추측해서 넣지 않는다. 역할 구현이 요구하는 정책은 가상 시험 구성에서 명시한다. `evidence_refs`의 표/행/쪽은 1부터 시작하며 DOCX 표는 본문의 최상위 표 순서다.

`profile_kind`는 `report_equipment`, `dut_context`, `auxiliary`를 명시한다. 화면은 모델명/variant로 이 분류를 추측하지 않는다.

구조 검사는 다음과 같다.

```powershell
python -m unittest tests.test_virtual_fleet_catalog -q
```

`load_catalog`/`validate_catalog`는 JSON·역할·포트·근거 위치의 구조를 검사하고 분리된 복사본을 반환한다. `catalog_summary`는 항상 `synthetic=true`, `hardware_verified=false`, `execution_validation=not_performed_by_catalog_validation`을 반환한다. 원문 해시의 실제 일치, 동작·고장·복구 실행과 전체 시험 조합은 별도 검증한다.

실행·분담 계약은 [VLAB-ALL-001](../handoff/development/VLAB-ALL-001.md)을 따른다. 원시데이터 미확보나 Licensed 암호 확인은 이 Un-licensed 가상 개발의 선행조건이 아니다.
