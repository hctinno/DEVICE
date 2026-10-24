# 기존 fixture 하네스 뒤의 별도 합성 DUT 정지

2026-10-24 · Asia/Seoul. DUT-STOP-HARNESS-016의 [구현](../../labflow/dut_stop_harness.py)과 [전용 검사](../../tests/test_dut_stop_harness.py)다. 의존 DUT-STOP-013의 최종 독립 Yes 수정은 `b9f2e01e09df24e1eff8c9fd883e680224914d82`다. 동일한 기존 VirtualFleet의 고정 RFSensorFixturePolicy/FleetHarness 실행과 SyntheticDutStopAdapter를 연결한다.

## 고정 API와 입력

```python
SyntheticDutStopHarnessRun(fleet, dut_id, *, harness_config, stop_config)
run.run() -> dict
run.result() -> dict | None
run.events() -> list[dict]
run.author_record() -> dict | None  # trusted host의 비공개 진단
```

운영자는 bound run/result/events와 반환 사본만 사용한다. author_record와 생성 설정은 신뢰된 host가 보관한다. 외부 runtime/policy/transport/callback/주소·모델 제공자·파일 경로는 받지 않는다. 정확한 기존 VirtualFleet와 내장 DUT만 허용하며 기존 013의 하위 helper 무결성 검사와 고정 자식 구현 검사를 사용한다. 신뢰된 import/callpath 검사이며 임의 Python 실행을 격리하는 sandbox가 아니다.

harness_config의 정확한 필수 키는 `goal`, `catalog`, `topology`, `role_actions`, `run_id`, `runtime_instance_id`이며 optional 키는 `budgets`뿐이다. 앞의 네 필드는 각각 독립적인 유한 JSON dict다. 두 ID는 013과 같은 ASCII ID 규칙과 128자 한계를 따른다. budgets는 기존 하네스의 `decisions`, `logical_requests`, `ticks`, `wall_seconds`, `transport_retries`만 받으며 기존 기본값·형식·cooperative deadline을 그대로 사용한다. 임의 policy나 clock을 주입하지 않는다.

goal의 정확한 키는 `kind=acquire_fresh_rf_sensor`, `dut_id`, `sensor_id`, `minimum_acquisition_tick`이다. tick은 정확한 비음수 int이며 두 장치는 서로 달라야 한다. 목표 DUT는 명시 dut_id와 같고 해당 Fleet의 DUT 프로필/역할과 실제 내장 객체의 profile_id에 묶인다. sensor는 같은 Fleet의 power_sensor다. catalog/topology/role_actions는 기존 하네스의 공개 projection을 적용한 뒤 해당 Fleet의 host metadata와 일치해야 한다. private simulation_parameters나 고장 정답을 정책 context에 복사하지 않는다. 생성자는 관측과 metadata만 확인하며 DUT 명령을 실행하지 않는다.

stop_config의 정확한 필수 키는 `transport_family`, `available`, `authorized`, `model_fw_matches`이고 optional 키는 `scenario`뿐이다. 값과 gate는 013을 따른다. 이 gate는 하네스 뒤 합성 정지 단계만 조건화하며 전체 하네스·실장비 운전 권한을 뜻하지 않는다. 설정을 바꾸는 API는 없다.

생성 오류는 정제 ValueError `dut_stop_harness_configuration_invalid`, `dut_stop_harness_stop_configuration_invalid`, `dut_stop_harness_fleet_invalid`, `dut_stop_harness_device_invalid`, `dut_stop_harness_binding_invalid` 중 하나다. 원시 오류 문자열을 결과에 넣지 않는다.

## 단일 실행과 결과

run은 한 객체에서 한 번만 기존 fixture 하네스를 실행한다. terminal 결과·이벤트를 먼저 보관한 뒤 같은 Fleet의 013 adapter를 정확히 한 번 호출한다. 하네스 호출이 실패해도 조회 가능한 원래 결과·이벤트와 고정 오류를 먼저 남기고 후속 합성 정지를 별도로 요청한다. 하네스/자식의 binding이 바뀌어 호출 전에 거절한 경우에는 실행하지 않는다.

후속 stop의 ID는 `dut-stop-harness:`와 두 고정 ID의 JSON 배열을 SHA-256한 64자리 hex를 잇는다. 기존 하네스의 `request:` 명령 namespace와 다르다. run 시작을 명령 전에 예약하므로 동시·반복 호출은 최초 detached 결과만 반환한다. 자식 호출이 예외를 내도 재시도·fallback·cache 초기화는 없다. 새 객체/재시작의 전역 멱등·복구는 지원하지 않는다.

반환 exact 25키는 `schema_version=1`, `kind=synthetic_dut_stop_harness_result`, `execution_mode=virtual_fleet_fixture_then_dut_stop`, `synthetic=true`, `hardware_verified=false`, `physical_model_verified=false`, `model_execution_verified=false`, `oem_support_status=not_assessed`, `run_id`, `runtime_instance_id`, `device_id`, `profile_id`, `status`, `reason_code`, `harness_dispatch`, `harness_result`, `harness_error`, `events_error`, `dut_stop_request_id`, `stop_dispatch`, `dut_stop_receipt`, `dut_stop_error`, `record_error`, `receipt_scope=historical_observation`, `current_stop_authority=false`다.

status는 `recorded` 또는 `partial`이다. recorded는 두 자식 기록과 transcript를 정제 오류 없이 보관했다는 뜻이다. 하네스의 시험 성공·합격·물리 cleanup을 뜻하지 않는다. gate blocked나 stop unconfirmed도 원래 값 그대로 별도 필드에 둔다. reason_code는 `children_recorded` 또는 아래 고정 오류다.

| 필드 | 값과 의미 |
|---|---|
| harness_dispatch / stop_dispatch | not_started / not_sent가 각각 초기값. 호출 직전 unknown, 반환을 받으면 returned. returned는 실제 DUT 명령·정지 성공을 뜻하지 않음 |
| harness_result | 검증된 기존 원래 결과 또는 None. termination/policy claim/task_outcome/cleanup/assessment를 덮어쓰지 않음 |
| dut_stop_receipt | 검증된 013의 22키 역사 receipt 또는 None |
| harness_error | None / harness_execution_error / harness_result_invalid |
| events_error | None / harness_events_error / harness_events_invalid |
| dut_stop_error | None / dut_stop_execution_error / dut_stop_receipt_invalid |
| record_error | None / child_binding_changed / wrapper_record_error |

adapter 예외는 receipt=None, dut_stop_execution_error, stop_dispatch=unknown으로 남긴다. 실제 명령이 실행되지 않았다고 추정하지 않는다. 기존 harness.stop()의 supervisor event, policy kind=stop의 종료 판단, 원래 cleanup=not_assessed는 바뀌지 않는다. 이 API에 supervisor stop/실물 취소·긴급정지 기능은 없다.

result는 실행 전 None, events는 빈 list다. 자식 결과는 같은 고정 자식이 보관한 원래 기록과도 대조해 외형상 유효한 claim/context 바꿔치기를 거절한다. 실행 뒤 events는 기존 operator transcript의 독립 사본이며 합성 정지 receipt는 transcript에 끼워 넣지 않는다. 정제 실패 이벤트는 제외하고 원래 sequence와 앞뒤의 유효 기록을 보존하며 events_error를 남긴다. author_record는 실행 전 None이며 실행 뒤 공개 설정 projection, 별도 private stop 설정, bounded 원래 자식 반환·JSON 이벤트·013 author 진단·고정 진단 오류와 결과의 사본을 제공한다. JSON으로 보관할 수 없는 이벤트는 private harness_event_unrecordable 오류를 남긴다. scenario/gate·raw/private 경로·원시 예외는 operator 결과나 policy context에 넣지 않는다.

## 자식·포장 예산과 실패 보존

입력의 네 JSON 구성요소는 각각 depth 32/1 MiB, stop 설정은 4 KiB다. 기존 하네스 결과는 depth 32/256 KiB, 각 이벤트는 depth 32/512 KiB이며 최대 4,096개·합계 32 MiB다. events를 한 번에 depth 32로 다시 검사하지 않고 이벤트별로 복사한다. 013 receipt는 depth 32/96 KiB, private author는 depth 36/256 KiB다.

새 operator wrapper는 depth 36/384 KiB다. 두 최대 자식 결과의 352 KiB와 고정 metadata를 수용한다. 새 private wrapper는 depth 40/38 MiB로 입력의 독립 네 구성요소, 최대 transcript, 원래 bounded 자식 반환, 013 author와 operator wrapper를 수용한다. 자식 기록을 먼저 독립 저장한 뒤 포장하므로 parent 깊이로 허용된 원문을 다시 거절하지 않는다.

최종 포장이 실패하면 고정 필드로 다시 구성해 partial/wrapper_record_error를 남긴다. 이미 보관한 자식 결과·이벤트·명령/ACK·dispatch 문맥은 유지하며 최초 빈 상태로 돌아가거나 run/stop을 다시 실행하지 않는다. 비공개 diagnostic_error와 고정 오류를 보존한다. 직렬화 한계용 최대 크기 fixture는 semantic DUT/하네스 결과나 실물 관측으로 세지 않는다.

## 검사와 범위

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_dut_stop_harness.py -q
python -X utf8 -B -m unittest discover -s tests -p test_dut_stop_simulation.py -q
python -X utf8 -B -m unittest discover -s tests -p 'test_virtual_fleet*.py' -q
python scripts/check_artifacts.py
```

공개 API는 기존 in-memory child만 호출하며 파일·네트워크·SDK·외부 계정 I/O를 추가하지 않는다. 기존 create_conducted_example→FleetHarness→013의 실제 가상 연결 증거와 labelled unit double/직렬화 fixture를 분리한다. 하네스 deadline은 cooperative다. 실제 ADB/OEM/GUI/AT/DIAG·단말/FW·RF 물리·실제 AI·시험소 전체 업무 완료는 검증하지 않는다.
