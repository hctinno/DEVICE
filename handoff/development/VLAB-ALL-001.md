# 전체 성적서 장비 가상화 — VLAB-ALL-001

사용자의 2026-10-23 전체 장비 가상환경 구축 지시에 따른 총괄의 구현 배정이다. [고정 설계/인터페이스](../../docs/superpowers/specs/2026-10-23-whole-report-virtual-lab-design.md)를 먼저 읽는다. 기존 개발1~4 채팅과 독립 clone·전용 branch를 유지한다.

## 공통

- 기존 실제 자료 감사의 해시/coverage/결론을 private로 먼저 회신하고 담당 신규 모듈을 구현한다. 감사 미완료를 숨기지 않는다.
- DOCX/Workbook reader의 후속 구현은 계획과 현재 변경을 보존한 뒤 이 전체 가상화 단위보다 뒤로 둔다. 다른 기능을 reset/삭제하지 않는다.
- 기존 `virtual_lab.py`, `virtual_session.py`, Store/DB/접수/하네스/기존 UI와 requirements를 변경하지 않는다. 필요한 공통 변경은 총괄에 제시한다.
- 신뢰된 순수 Python 가상 모델만 사용한다. 실장비/현장망·ADB·펌웨어·매크로를 실행하지 않는다.
- 실제 시리얼/원문·복호문·수치/수식·암호는 공개 fixture/catalog에 넣지 않는다. 합성 수용 자료와 공개가 가능한 모델 이름/역할만 사용한다.

## 개발3 — CORE/FACILITY

- 소유: `labflow/virtual_fleet/core.py`, `facility.py`, `__init__.py`, `tests/test_virtual_fleet_core.py`, `tests/test_virtual_fleet_facility.py`, `docs/fcc/virtual_fleet_core_usage.md` 및 작업ID 전용 계획.
- factory를 주입받는 runtime, 공통 envelope, profile/role/port/DAG 검증, 가상 tick·setup revision, 요청 ID 재시도/충돌·작성자 제어 분리를 구현한다.
- 인터페이스를 사용법에 고정하고 즉시 총괄에게 전달한다. 다른 역할 모듈이 도착하기 전 합성 test double로 검증한다.
- 전원/전류 제한·출력, 온도/습도 setpoint와 안정 대기, 이동/한계·정지·인터록·통신 끊김/복구를 실제 상태 전이로 구현한다. 선언하지 않은 물리 정밀도/임계값을 제조사 스펙으로 표시하지 않는다.

## 개발1 — DUT/SENSOR/RF PATH

- 소유: `labflow/virtual_fleet/rf.py`, `tests/test_virtual_fleet_rf.py`, `docs/fcc/virtual_fleet_rf_usage.md` 및 작업ID 전용 계획.
- 설계의 factory와 role/action 계약에 맞춰 DUT 송신·환경/전원 전제, 센서 연결/일치·유효성, 감쇠/결합/분기·안테나/증폭/필터·RF경로 전환·LISN을 구현한다.
- 신호/단위/대역/포트, 설정 변경·무효 입력·과부하·주파수별 보정과 누락 처리, 정상/미연결/고장/복구를 합성 TDD로 확인한다. 손실/보정표 없는 경우 임의 실측 보정값을 넣지 않는다.
- 정확한 `ROLE_ACTIONS`를 먼저 총괄과 개발3 경유로 공유하고 다른 모듈의 내부 API를 추측하지 않는다.

## 개발2 — MEASUREMENT/COMMUNICATION/SOFTWARE

- 소유: `labflow/virtual_fleet/instruments.py`, `tests/test_virtual_fleet_instruments.py`, `docs/fcc/virtual_fleet_instruments_usage.md` 및 작업ID 전용 계획.
- 전력계·분석기/수신기·신호발생·통신/BT 테스터·AP/DFS·복합 통신시험 시스템·시험 소프트웨어의 구성→실행→대기/완료/취소→유효 관측/오류 복구를 구현한다.
- 관측 수치는 입력 신호/설정·명시적 가상 정책에서 계산하며 고정 PASS나 보고서 정답을 복사하지 않는다. 단위/검파·대역·트리거/센서/구성 revision을 확인한다.
- 공식 미검토 SCPI는 만들지 않는다. `ROLE_ACTIONS`와 관측/지원 한계를 고정하고 모든 고정 role의 합성 수용을 제공한다. 기준 보고서의 불일치는 별도 private 회귀로 보존한다.

## 개발4 — VIRTUAL LAB UI

- 소유: `labflow/virtual_fleet_server.py`, `frontend/virtual_fleet/`, `tests/test_virtual_fleet_server.py`, `docs/fcc/virtual_fleet_ui_usage.md` 및 작업ID 전용 계획.
- runtime을 주입받는 loopback 전용 서버와 가상 전용 화면을 구현한다. 현재 접수 화면/서버는 변경하지 않는다.
- catalog·토폴로지·모든 장비의 상태/action/관측과 진행/무효/오류·근거/지원 범위를 표시한다. 운영자 action/advance만 노출하고 author_control은 노출하지 않는다. 데이터 로딩·오류·빈 상태를 구별한다.
- 임의 source 경로/실장비 주소·암호·고장 정답 입력을 받지 않는다. 변경 요청은 same-origin/CSRF·엄격한 JSON·request ID와 동작 제한을 적용한다.
- 총괄 통합 진입점 전에는 합성 runtime 대역으로 개발하고 그 사실을 명시한다. 실제 통합 후 전체 모델 조회/동작·화면/실패 수용을 총괄과 확인한다.

## 보고·통합

각 담당은 설계 기준의 TDD/정적·관련 회귀·문서 검증 후 자기 branch에 커밋·푸시하고 SHA·고정 API·실행 예·역할별 완료/미지원·가상 검증 결과를 총괄에게 보고한다. 총괄이 catalog의 모든 항목·변형을 factory/토폴로지/수용 검사에 연결한 뒤 통합한다. 사용자에게 '전체 완료'를 보고하려면 미연결 모델/미실행 역할이 없어야 하며, 실장비 정밀도·제조사 전체 프로토콜 검증과는 구별한다.
