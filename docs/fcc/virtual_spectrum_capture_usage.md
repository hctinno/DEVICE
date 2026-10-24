# 선언 주파수 fixture와 현재 관측 문맥 결합

2026-10-24, Asia/Seoul. SPECTRUM-004B 개발3.

현재 signal_analyzer의 결과는 취득 시점이 있는 스칼라다. 이 bridge는 별도로 선언한 주파수 fixture를 host가 선택한 현재 operator 관측 문맥에 결합한 뒤 [BW 계산](virtual_spectrum_math_usage.md)을 호출한다. 결과의 trace_origin은 declared_frequency_fixture, binding_scope는 current_observation_context, rf_trace_observed는 false다.

scalar·시간 envelope·nominal bandwidth에서 spectrum을 만들지 않는다. 기존 역할/catalog/runtime/harness/journal과 공개 v1 result/measurement_refs를 변경하지 않는다. bridge 함수는 파일·DB·시계·네트워크·runtime·장비·모델을 호출하지 않는다.

## API와 기대 문맥

```python
from labflow.virtual_fleet.spectrum_capture import analyze_current_bandwidth_capture

result = analyze_current_bandwidth_capture(capture, current_event, context=trusted_context)
```

context는 host가 예약한 run/instance와 기존 topology에서 선택한 source/profile을 가진 정확한 5키다.

```text
run_id runtime_instance_id source_id profile_id minimum_acquisition_tick
```

capture 입력에서 이 기대값을 역으로 만들지 않는다. current_event는 host가 선택한 현재 type=observation의 기존 operator_event v1 한 건이다. raw core 관측에는 run/instance가 없으므로 event 전체를 전달한다. event의 event_id는 event:<sequence>와 같고 sequence는 양의 정수여야 한다. payload는 observation과 선택적인 cause_request_id만 받는다.

host는 최신 event를 선택하고 minimum_acquisition_tick을 정한다. 저장 journal을 쓴다면 host가 기존 reader로 무결성을 먼저 확인한다. bridge는 입력 snapshot 밖의 실제 현재 시각이나 실행 상태를 조회하지 않는다. hash는 원본 결합을 확인하며 외부 발신자 인증이나 서명을 대신하지 않는다.

## capture exact 15키

```text
schema_version=1
kind=synthetic_frequency_capture
capture_id
synthetic=true
capture_origin=declared_frequency_fixture
run_id
runtime_instance_id
source_id
profile_id
acquisition_tick
acquisition_setup_revision
observation_event_id
observation_sha256
trace_sha256
trace
```

trace는 기존 BW의 exact 주파수 입력 10키다. capture_id가 wrapper와 같아야 한다. 축·단위·상대 level·길이·유한성도 BW 계약에 맞아야 한다. 시간축·명목 대역폭·미상 필드로 대체하지 않는다.

trace_sha256는 원본 trace 전체, observation_sha256는 current_event 전체의 lowercase hex64 SHA-256이다. canonical JSON은 sorted keys, UTF-8, ensure_ascii=false, allow_nan=false, compact separators를 사용한다. capture_sha256는 반환 시 동일 방식으로 원본 capture 전체에 대해 계산한다. 입력의 0/0.0 같은 JSON 숫자 표현 차이를 보존한다.

모든 ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`다. tick/revision은 bool을 제외한 비음수 정수다. capture와 current_event는 각각 canonical UTF-8 JSON 4 MiB 이하이며 정확히 한도인 값은 허용한다. 기존 공개 JSON 규칙대로 dict의 문자열 key, list, 문자열·bool·int·유한 float·null을 받고 깊이는 32 이하로 제한한다. tuple·비유한 수·순환·깨진 UTF-8·임의 Python 객체는 거절한다.

입력 전체를 독립 JSON 사본으로 고정한다. 계산기가 호출 중 원래 입력을 변경해도 선택한 문맥과 hash가 섞이지 않는다. 계산기에는 별도 trace 사본을 전달하고 반환한 BW 결과도 exact schema·자료형·ID/hash·공개 flag를 검사해 독립 사본으로 반환한다.

## 계산 전 gate

| 검사 | 조건 |
|---|---|
| 기대값 결합 | host↔capture↔event의 run/instance, 선택 source/profile, event ID와 두 hash 일치 |
| core 관측 | 현재 tick/setup revision 및 synthetic=true/hardware_verified=false |
| source 노드 | map ID/device_id/profile, role=signal_analyzer, status=ok, 현재 tick/revision·공개 flag 일치 |
| scalar packet | outputs.measurement, status=ok, valid=true, source_id=선택 node, finite value, unit=dBm, quantity=on_average 또는 peak |
| 취득 | host minimum≤acquisition_tick≤현재 tick, acquisition setup revision=현재 revision, capture와 실제 packet 값 일치 |
| 설정 | packet.configuration_revision=현재 node.values.configuration_revision, operation_complete=true |
| 주파수 fixture | exact trace schema·ID·canonical hash·엄격 증가 축·상대 level |

잘못된 문맥/trace는 BW 함수 호출 전에 거절한다. 모든 gate를 통과하면 analyze_6db_bandwidth를 한 번만 호출한다. scalar 값과 명목 대역폭은 BW 숫자를 만드는 데 쓰지 않는다. 유효 문맥에서 trace가 잘렸거나 peak/lobe/plateau가 모호하면 기존 BW의 incomplete/null을 유지한다. 수치 표현 오류도 기존 math 계약대로 거절하며 새 runtime이나 재시도로 바꾸지 않는다.

## 반환 exact 9키와 binding 18키

```text
schema_version=1 kind=synthetic_bandwidth_capture_result binding bandwidth_result
synthetic=true hardware_verified=false ai_model_called=false
method_approval=not_assessed regulatory_scope_complete=false
```

binding은 정확히 다음 18키다.

```text
capture_id run_id runtime_instance_id source_id profile_id role
acquisition_tick acquisition_setup_revision configuration_revision
observation_event_id current_tick current_setup_revision
observation_sha256 trace_sha256 capture_sha256 trace_origin binding_scope rf_trace_observed
```

role은 signal_analyzer, trace_origin은 declared_frequency_fixture, binding_scope는 current_observation_context, rf_trace_observed는 false다. bandwidth_result는 기존 math의 exact 결과를 유지한다.

원본 trace 배열·전체 관측·scalar 값·configuration·private author·경로를 결과에 복사하지 않는다. 반환 dict를 변경해도 입력·계산기의 반환 객체·다음 호출 결과를 변경하지 않는다.

입력/문맥/JSON 오류는 원시 데이터 없는 ValueError(invalid_bandwidth_capture), 계산기 결과 계약 위반은 ValueError(invalid_bandwidth_analysis)다. 알려진 math의 invalid_spectrum_input/numeric_result_out_of_range는 정제해 전달한다. 그 외 계산기 예외는 ValueError(bandwidth_analysis_failed)로 정제하며 재시도하지 않는다. 원시 예외 문자열을 결과나 오류에 넣지 않는다.

## 실제 가상 취득 기반 검사

[전용 검사](../../tests/test_virtual_fleet_spectrum_capture.py)는 기존 create_conducted_example의 실제 Fleet를 만든 뒤 FleetHarness가 analyzer acquire → advance(1) 두 번 → fetch → stop을 실행한다. 기존 하네스의 advance 제안은 한 tick만 허용한다. 별도로 손으로 명시한 trace를 마지막 operator observation event에 결합한다.

기본 예제의 host minimum은 14, 실제 취득/현재 tick은 15, setup revision은 15, configuration revision은 1이다. 별도 실제 peak acquisition도 검사한다. 이 숫자는 새 합성 fixture의 취득 경과이며 기존 보고서 실측값이 아니다.

```text
.venv\Scripts\python.exe -B -m unittest tests.test_virtual_fleet_spectrum_capture -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B scripts/check_artifacts.py
```

source/profile/run/instance/hash/event 불일치, stale/future/setup/config drift·상태/단위·추가 key·bool/비유한·JSON/크기 한도에서 계산 호출 0을 확인한다. 정상 단일 호출·불충분 BW 유지·입출력 별칭·private/raw 미포함·파일/DB/네트워크/clock/runtime 호출 부재도 검사한다.

현재 관측 문맥과 선언 trace의 결합만 검증한다. 실제 가상 frequency source 출력, RF trace 취득 증거, 하네스 목표 완료/업무 판정 연결, 실제 AI·실장비·현장·현행 전체 규범 방법 검증은 후속 단위다.
