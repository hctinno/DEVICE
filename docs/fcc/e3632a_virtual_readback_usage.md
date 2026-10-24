# E3632A 가상 설정·계측 조회

2026-10-24 · Asia/Seoul. [기존 Fleet](virtual_fleet_usage.md)의 내장 역할 모델을 읽는 메모리 API다. 실제 전원장치·SCPI·주소·transport·콜백을 받거나 실행하지 않는다. `labflow.e3632a_virtual_readback`의 공개 서명은 다음 세 개다.

```python
E3632AVirtualReadback(fleet, device_id)
adapter.observe(request_id)
adapter.author_record(request_id)
```

정확 내장 `VirtualFleet`과 내장 역할 객체만 받는다. 대상은 원래 프로필 `e3632a-ba5f7c3ee5`의 제조사 `Agilent`, `e3632a-ebca10ffe2`의 `H.P`이며 전체 프로필의 정규 JSON SHA-256을 고정한다. model은 `E3632A`, role은 `power_supply`다. 두 표기를 OEM alias나 실물 지원 승인으로 합치지 않는다. 인스턴스·클래스·관련 모듈 helper 교체와 다른 노드의 임의 객체를 호출 전에 거절한다. 이는 신뢰한 호스트에서의 무결성 검사이며 임의 Python 코드의 sandbox는 아니다.

`observe`는 정확 `fleet.observations()`를 한 번 읽는다. 이 논리 조회는 device command/history 발행이 아니므로 `observation_method`와 `observation_reads`로 기록한다. 공개 snapshot이 정상이며 enabled/valid와 장치·프로필·출처·tick/revision이 일치할 때만 기존 `fleet.execute(child_request_id, device_id, 'measure', {})`를 한 번 호출한다. 출력 OFF·보호·단절·부족한 관측에는 measure 명령이 0개이고 `measurement=null`이다. OFF의 0V/0A 표식을 측정으로 바꾸지 않는다. 정상 ON에서 실제 역할 응답이 0V/0A인 경우는 유효할 수 있다.

설정 전압과 전류 limit은 `configured`, 공개 enable/valid/state는 `output`, 단일 measure 응답의 전압·전류·CV/CC·취득 문맥은 `measurement`로 나눈다. snapshot과 measure의 문맥 또는 값이 달라지면 `unconfirmed`이며 재조회하지 않는다. 저항 부하/CV·CC 계산은 기존 역할만 수행한다. 이 API는 configure/output/start/stop/clear_trip, tick 진행, 오류 큐 조회, 자동 복구를 호출하지 않는다. 기존 execute 내부의 같은 tick 전파는 유지된다.

`observe` 반환은 아래 정확 25개 키다. 사용자 제공 원문·임의 packet 필드는 이 DTO에 복사하지 않는다.

| 키 | 값 |
| --- | --- |
| schema_version, kind | `1`, `e3632a_virtual_readback` |
| request_id, device_id, profile_id | 검증한 ASCII 식별자와 고정 프로필 |
| manufacturer_as_recorded, model, profile_sha256 | 원문 제조사, `E3632A`, 고정 정규 프로필 SHA |
| status, reason_codes | `observed_synthetic` 또는 `unconfirmed`, 아래 고정 이유 0~1개 |
| configured | null 또는 `voltage_setpoint_v`, `current_limit_a` |
| output | null 또는 `enabled`, `valid`, `state` |
| measurement | null 또는 `voltage_v`, `current_a`, `mode`, `acquisition_tick`, `acquisition_revision` |
| initial_context, observation_context, measurement_context | 각각 null 또는 `tick`, `setup_revision` |
| observation_reads, observation_method | 0 또는 1, `fleet.observations` |
| commands | 실제 시도한 measure 0~1개: `request_id`, `device_id`, `action='measure'`, `parameters={}`, `attempted=true` |
| simulation_basis | `existing_role_domain_model` |
| observation_scope, current_authority | `historical_observation`, `false` |
| verification | 아래 정확 12개 검증 경계 |
| role_policy_defaults | `voltage_max_v=60`, `current_max_a=10`, `scope='generic_role_policy_not_model_ratings'` |
| resumable | `false` |

`verification`은 `synthetic=true`, `hardware_verified=false`, `ai_verified=false`, `vendor_binary_executed=false`, `output_off_verified=false`, `rf_off_verified=false`, `safe_state_verified=false`와 `model_limits`, `calibration`, `oem_support`, `firmware_options`, `physical_model` 각각 `not_assessed`다. 기본 60V/10A는 역할 정책이며 E3632A 정격으로 사용하지 않는다. 실제 전압/전류·OFF·안전 정지·실제 AI를 검증하지 않는다.

비공개 `DEV-E3632A-READBACK-011 / S05-B0005-v1`의 6질문·9행 근거를 대조했다. 설정/limit/cache, 계측 쌍, 요청·조회 enable과 실제 보호, 취득 시점·완료·전송의 미확인을 구분한다. guide 표/단위의 상충과 source-only tracking getter의 정적 오류는 미해결로 보존하며 모델 정격·상수 응답·OEM 실행 코드로 채택하지 않는다. 새 원문은 0개이고 기존 자료는 실행하지 않았다. 원문·코드 본문·비공개 metadata를 공개 Git에 포함하지 않는다.

`unconfirmed` 이유는 `binding_changed`, `unsafe_callpath`, `observation_exception`, `observation_packet_invalid`, `observation_budget_exceeded`, `context_mismatch`, `output_disabled`, `output_protected`, `device_unavailable`, `observation_unavailable`, `measure_exception`, `measurement_packet_invalid`, `measurement_budget_exceeded`, `measurement_unavailable`, `measurement_mismatch`, `preservation_failed`다. 알 수 없는 상태·추가 키·nonfinite·bool 수치·부분 응답·불일치 출처는 성공으로 올리지 않는다. 검증 실패 시 측정은 null이고 설정·출력은 검증된 snapshot 범위에서만 보존한다.

`author_record`는 이미 저장된 결과만 반환하며 새 관측·명령을 수행하지 않는다. 정확 8개 키는 `schema_version=1`, `kind='e3632a_virtual_readback_author'`, `request_id`, `scope='trusted_author_only'`, `operator_receipt`, `observation_frames`, `command_frames`, `diagnostics`다. observation frame은 `method`, `attempted`, `packet`, `error`이며 packet에는 해당 장치 envelope만 보존한다. command frame은 commands의 5키와 `packet`, `error`다. 저장 가능한 원래 가상 packet을 보존하고, 크기/깊이 초과는 null과 고정 오류로 남긴다. 숨은 fault/seed/오류 큐를 읽어 진단이나 측정 근거로 만들지 않는다. 호스트는 이 API를 신뢰한 author에게만 제공해야 하며, 새 HTTP route나 인증 체계를 만들지 않는다.

각각 UTF-8 정규 JSON과 root 깊이 0 기준으로 제한한다. 전체 observations 입력은 256KiB/깊이32, 선택한 관측·measure 원래 packet은 각각 16KiB/깊이16, 정책 DTO는 16KiB/깊이16, author 전체 포장은 64KiB/깊이24다. 각 JSON 트리의 최대 항목은 100,000개다. 내부 typed 상태 무결성 검사는 최대 200,000개/깊이48이다. packet만 통과해도 포장 예산을 넘으면 성공이 아니다. 관측/명령 시도 표시는 호출 전에 저장하고, 예외나 포장 실패 뒤에도 실제 시도 prefix를 유지한 실패 영수증을 저장한다. 재호출로 명령을 재송신하지 않는다.

request/device ID는 정확 str이며 `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`이다. adapter별 최대 128개, 무축출 메모리 cache다. 같은 ID는 같은 역사 결과를 새 사본으로 반환하며 현재 상태 권한은 항상 false다. 서로 다른 adapter의 child ID는 프로세스 내 namespace로 분리한다. 재시작·영속 복구·현재 setup 일치·중단 후 재개는 지원하지 않는다. 일반 Fleet API와의 동시 조작은 기존 RLock으로 배제하고 adapter 동시 요청은 대기 없이 거절한다.

호출 전 오류는 `ValueError`의 고정 문자열 `invalid_virtual_fleet`, `invalid_device_id`, `unsupported_supply_profile`, `unsafe_callpath`, `invalid_request_id`, `readback_busy`, `receipt_limit_reached`, `readback_record_not_found`다. 오류에 원래 객체·주소·예외 메시지나 cause/context를 넣지 않는다. cache replay는 원래 결과만 복사하므로 이후 Fleet 변조·변경을 현재 검증으로 오인하지 않는다. 유효 신규 요청에서 발견한 변경/관측/측정 실패는 위의 `unconfirmed`로 저장한다.

검증은 `python -B -X utf8 -m unittest tests.test_e3632a_virtual_readback -v`로 실행한다. 기존 64프로필에서의 합성 실행과 raw/원본 전후 해시는 비공개 실행 기록에 별도로 보존한다. 이 결과는 실장비 비교·현장·교정·기관 적합성 또는 전체 무인시험소 완성을 증명하지 않는다.
