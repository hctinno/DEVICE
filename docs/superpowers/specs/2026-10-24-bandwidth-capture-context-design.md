# SPECTRUM-004B — 선언 주파수 fixture와 현재 관측 문맥의 결합

2026-10-24, Asia/Seoul. 개발3의 현재 core/operator event 대조 제안을 인수해 총괄이 고정한다. [순수 계산](2026-10-24-synthetic-spectrum-math-design.md)의 수치 리뷰 수정 뒤 새 전용 브랜치에서 이어 구현한다.

## 범위

현재 signal_analyzer는 scalar와 취득 tick/revision을 생산하며 RF frequency trace/hash를 생산하지 않는다. 이 단위는 외부에서 명시한 frequency fixture와 host가 선택한 현재 관측 문맥을 결합한다. 결과에 `trace_origin="declared_frequency_fixture"`, `binding_scope="current_observation_context"`, `rf_trace_observed=false`를 고정한다. scalar·시간 envelope·nominal bandwidth를 RF spectrum으로 변환하지 않는다. 실제 가상 주파수 source/역할 출력과 하네스 완료 연결은 다음 단위다.

## 소유와 API

신규 `labflow/virtual_fleet/spectrum_capture.py`, `tests/test_virtual_fleet_spectrum_capture.py`, 전용 usage만 개발3 소유다. 기존 role/catalog/runtime/harness/journal/공개 v1 result는 변경하지 않는다.

```python
analyze_current_bandwidth_capture(capture, current_event, *, context) -> dict
```

파일·DB·clock·네트워크·장비·모델 호출 없는 순수 함수다. 입력은 독립 JSON 사본으로 고정하고 출력도 공유하지 않는다. capture/current_event는 각각 canonical UTF-8 JSON 4MiB 이하이며 기존 공개 JSON 유한성/식별자 규칙을 따른다. ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`, tick/revision은 bool 제외 비음수 정수다.

context exact5키는 `run_id`, `runtime_instance_id`, `source_id`, `profile_id`, `minimum_acquisition_tick`이다. 기대값은 host가 예약/선택한 값이며 capture에서 역으로 만들지 않는다. current_event는 기존 exact operator_event v1의 type=observation 한 건이다. 저장 journal의 무결성·현재 event 선택은 host 책임이며 hash가 외부 발신자 인증을 뜻하지 않는다.

capture exact15키는 `schema_version=1`, `kind="synthetic_frequency_capture"`, `capture_id`, `synthetic=true`, `capture_origin="declared_frequency_fixture"`, `run_id`, `runtime_instance_id`, `source_id`, `profile_id`, `acquisition_tick`, `acquisition_setup_revision`, `observation_event_id`, `observation_sha256`, `trace_sha256`, `trace`다. trace는 기존 BW exact 입력이며 capture_id가 같다. trace와 current_event 전체의 sorted-key/UTF-8/유한 compact JSON SHA-256을 대조한다.

## 계산 전 gate

1. host/context↔event↔capture의 run/instance/source/profile/event와 두 hash가 일치해야 한다. event의 kind/schema/sequence/공개 flags/payload는 기존 계약을 따른다.
2. 현재 core 관측·선택 node의 tick/setup revision·synthetic/hardware flags를 검증한다. 선택 node는 signal_analyzer/status=ok이며 source/profile이 host 기대와 같아야 한다.
3. outputs.measurement는 status=ok/valid=true/source_id=선택 node, finite value/unit=dBm, quantity=on_average 또는 peak여야 한다. scalar 숫자는 BW에 사용하지 않는다.
4. host minimum≤실제 acquisition_tick≤현재 tick, acquisition_setup_revision=현재 setup_revision이어야 하고 capture 값도 그 실제 packet과 같아야 한다. packet.configuration_revision=node.values.configuration_revision, operation_complete=true를 확인한다.
5. trace/hash/ID와 모든 문맥을 검증한 뒤 `analyze_6db_bandwidth`를 한 번 호출한다. 잘못된 문맥이면 계산 호출 전에 정제 ValueError로 거절한다. 유효 문맥의 incomplete/null은 그대로 보존한다.

반환 exact9키는 `schema_version=1`, `kind="synthetic_bandwidth_capture_result"`, `binding`, `bandwidth_result`, `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `method_approval="not_assessed"`, `regulatory_scope_complete=false`다.

binding exact18키는 `capture_id`, `run_id`, `runtime_instance_id`, `source_id`, `profile_id`, `role="signal_analyzer"`, `acquisition_tick`, `acquisition_setup_revision`, `configuration_revision`, `observation_event_id`, `current_tick`, `current_setup_revision`, `observation_sha256`, `trace_sha256`, `capture_sha256`, `trace_origin`, `binding_scope`, `rf_trace_observed`다. capture_sha256는 원본 capture 전체 hash다. raw trace/관측/scalar/private author/path는 반환하지 않는다. 이 결과를 v1 measurement_refs나 업무 완료로 승격하지 않는다.

## 수용

실제 VirtualFleet·signal_analyzer acquire/advance/fetch와 실제 operator observation event를 준비하고 별도 선언 trace를 붙여 계산한다. source/profile/role/run/instance/hash/event·stale/future/acquisition/setup/config drift·pending/disconnected/valid/unit·추가 키·bool/비유한 거절과 계산 호출0을 검사한다. 잘린/다중 peak/lobe/plateau는 유효 문맥이면 기존 incomplete를 유지한다. 입력/출력 별칭·부작용0·크기 한도·기존 계산/계측/하네스 회귀를 확인한 뒤 소유 commit/push→독립 리뷰/수정→총괄 실제 연결을 이어간다. 사용자 추가 자료는 없다.
