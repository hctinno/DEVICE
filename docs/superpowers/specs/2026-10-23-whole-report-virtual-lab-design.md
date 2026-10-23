# 성적서 장비 전체를 연결하는 가상 시험소

2026-10-23, Asia/Seoul. 사용자는 SM-A176U 성적서에 있는 모든 장비 목록을 대상으로 가상환경 전체를 구현하도록 지시했다. 특정 전력계의 일부 프로필로 범위를 축소하지 않는다. 암호화 Excel은 사용자가 제공한 암호로 비공개 사본에서 분석하며 원본을 보존한다.

## 총괄 설계 결정

기존 `VirtualLab`/`VirtualSession`의 첫 프로필과 검증을 보존하면서, 다중 모델·역할·연결 토폴로지를 지원하는 별도 `virtual_fleet` 계층을 추가한다. 특정 모델 ID를 기존 N1914A 이름에 덮어쓰는 방식은 사용하지 않는다. 보고서의 모든 모델/변형/시험 소프트웨어를 출처와 연결한 catalog를 만들고 각각 실행 가능한 역할 구현과 연결한다.

대안은 기존 단일 장비를 계속 확장하는 방식, 장비별 독립 mock 서버, 공유 가상 시계/연결/유효성을 가진 다중 장비 런타임이었다. 총괄은 세 번째를 선택한다. 정상·고장·복구를 같은 가상 업무에서 검증하고 장비 간 설정 변경과 결과 무효화를 일관되게 처리할 수 있다. 실제 네트워크나 장비에 연결하는 fallback은 없다.

## 전체 목록과 완료 게이트

DOCX 52개의 장비표에서 1,118행과 모델/제조사 표기 91쌍을 후보로 추출했다. 이는 최종 정규화 수가 아니다. PDF 장비표, 최종 시험기록지/장비 Excel과 대조하고 공백·제조사 표기·옵션·복합 장비를 보존하여 정규화한다. 과거 serial/교정일·실측 수치/원문은 private mapping에 남기고 공개 catalog는 모델/역할/근거 식별과 가상 구성만 담는다.

각 catalog 항목은 `profile_id`, `model`, `manufacturer`, `role`, `variant`, `evidence_refs`, `simulation_basis`, `capability_scope`를 갖는다. 역할 구현 유무와 지원 action/정상·고장·복구 수용 결과를 coverage로 반환한다. 누락 모델, unknown role, 미실행 동작을 완료로 계산하지 않는다. 모델 이름을 나열하거나 고정 PASS/숫자를 반환하는 것만으로 구현 완료로 표시하지 않는다.

장비 전체 가상 구현은 모든 catalog 항목의 동작/상태/연결/단위/완료/오류·복구와 시험별 조합이 실행된 상태로 평가한다. 제조사 전체 펌웨어/옵션/프로토콜·물리 RF 정밀도와 동일하다는 주장은 별도의 실장비 비교 증거가 필요하다. 공식 명령이 미검토인 경우 추측한 SCPI를 만들지 않고 명시적인 가상 동작 API로 검증한다. catalog와 관측에 문서 기반/가상 모델 정책/미검증을 구분한다.

## 공통 실행 계약

package는 `labflow/virtual_fleet/`다. 각 역할 모듈은 `DEVICE_FACTORIES`를 export한다. 키는 아래 고정 role, 값은 `factory(profile: dict, seed: int) -> device`다. JSON 가능한 인수/응답만 허용한다.

device의 고정 인터페이스:

```python
perform(action: str, parameters: dict, *, tick: int, setup_revision: int, inputs: dict) -> dict
advance(*, tick: int, setup_revision: int, inputs: dict) -> None
observation(*, tick: int, setup_revision: int) -> dict
author_control(fault: str, value) -> None
```

`perform` 반환은 `status`(`ok/pending/invalid/unsupported/error/disconnected`), `values`(dict), `setup_changed`(bool)다. `observation`은 같은 `status/values`와 상태를 반환하고 `setup_changed`를 요구하지 않는다. 지원하지 않는 동작/인수는 명시적으로 거절하며 성공으로 바꾸지 않는다. 공통 runtime이 신뢰한 tick/revision/`synthetic=true`/`hardware_verified=false`/profile ID를 감싼다. 역할 구현은 이 provenance를 입력 데이터에서 받아 덮지 않는다.

`inputs`는 선언된 입력 port별 객체다. RF 신호는 `frequency_hz`, `power_dbm`, `bandwidth_hz`, `duty_cycle`, `modulation`, `source_id`를 명시하며 유한한 수·단위·양수 범위를 검사한다. 미연결/출력 꺼짐/과부하/대역 밖/유효하지 않은 upstream은 숫자 0이나 정상 측정으로 바꾸지 않는다. 여러 입력은 port별로 유지하고 선언 없이 전력을 더하지 않는다. 포트 값은 `values.outputs`에 JSON 객체로 전달한다.

runtime은 선언된 DAG의 연결 port를 가상 tick마다 순서대로 전달한다. 지원하지 않는 순환/port/role/profile·중복 ID는 구성 전에 거절한다. 제어 관계는 RF 신호 edge와 구분한다. 설정/연결 변경은 setup revision을 바꾸고 진행/완료 측정의 획득 revision을 기록한다. 이전 구성 결과를 새 구성 값처럼 사용하지 않는다.

운영자 요청의 같은 ID/같은 내용 재시도는 최초 결과를 반환하고 다른 내용은 충돌한다. 작성자 고장 주입 ID는 운영자 ID와 분리하고 고장 이름/정답·기대값을 운영자 관측에 노출하지 않는다. 실제 시간 sleep 대신 명시적인 가상 tick을 사용한다. 오류·취소·재시작·중복도 기록한다.

## 역할과 구현 분담

| 담당 | 소유 모듈 | 고정 role |
|---|---|---|
| 개발3 | `virtual_fleet/core.py`, `facility.py`, `__init__.py`, 공통 계약 사용법/검사 | `power_supply`, `temperature_chamber`, `position_controller`, `antenna_mast`, `turntable` |
| 개발1 | `virtual_fleet/rf.py`, 전용 검사/사용법 | `dut`, `power_sensor`, `attenuator`, `coupler`, `splitter`, `antenna`, `amplifier`, `filter`, `rf_switch`, `lisn` |
| 개발2 | `virtual_fleet/instruments.py`, 전용 검사/사용법 | `power_meter`, `signal_analyzer`, `emi_receiver`, `signal_generator`, `communication_tester`, `bluetooth_tester`, `wireless_ap`, `dfs_system`, `network_test_station`, `test_software` |
| 개발4 | `virtual_fleet_server.py`, `frontend/virtual_fleet/`, 전용 검사/사용법 | 가상 모드 UI·loopback API, 관측과 역할별 동작·진행·오류·지원/근거 조회 |
| 총괄 | `virtual_fleet/integration.py`, `virtual_profiles/` catalog, 통합 수용/coverage | factory 통합·전체 목록/시험별 토폴로지·근거/미지원 대조 |

새 역할이 필요한 실제 행은 기존 role에 억지로 넣지 않고 총괄에 제시한다. 세부 action은 각 담당이 `actions()` 같은 임의 공통 함수를 추가하는 대신 module의 `ROLE_ACTIONS` dict로 선언한다. 각 action의 인수/단위·완료/실패 의미를 사용법에 고정한다. 공통 runtime은 해당 선언을 조회하며 표준 API 외 내부 상태를 열람하지 않는다.

## UI와 수용

총괄의 통합 진입점은 `create_fleet(catalog: dict, topology: dict, *, seed=0)`다. 반환 runtime은 `execute(request_id, device_id, action, parameters=None)`, `advance(request_id, ticks=1)`, `observations()`, `coverage()`를 제공한다. 작성자 경계는 별도 `author_control(request_id, device_id, fault, value)`이며 HTTP/UI에서 공개하지 않는다.

가상 UI는 localhost에서 catalog/장비별 관측/연결/지원 action과 실행 이력·pending/완료/무효/오류·복구를 보여준다. 사용자 파일 경로/암호/고장 정답을 노출하지 않고 실제 장비 상태로 표시하지 않는다. 새 standalone 서버를 사용하고 기존 접수 UI/API를 동시에 변경하지 않는다. 데이터 로딩/오류/빈 상태와 마지막 성공 상태를 구별한다.

모든 모델의 정상/고장/복구 단위 수용과 전도·방사·AC·DFS/통신 관련 가상 조합을 실행한다. 같은 seed/입력의 재현, 설정 변경 중 측정 무효화, 미연결/시간 초과/센서 불일치/전원·환경/기계 한계·오류 큐를 확인한다. 실제 보고서 결과와 비교하는 회귀에서는 읽히는 raw/수식/단위/반올림·판본을 고정하고, 기대값/실측 원문을 운영자에게 정답으로 주지 않는다. 합성 검증·과거 기록 재생·실장비 비교를 각각 표시한다.
