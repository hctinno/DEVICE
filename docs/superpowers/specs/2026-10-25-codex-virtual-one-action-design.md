# Codex 가상 첫 제안 한 건 적용 설계

2026-10-25, Asia/Seoul. DGM AutoLab.

총괄이 A 직접 결합, native bool virtual_dispatch_authorized, 하위 하네스 예산1/1/1/30/0 및 host receipt exact12를 확정했다. 이 문서는 구현 기준 설계이며 제품 구현·실제 CLI·모델·현장 실행 승인을 겸하지 않는다. 공통 문서 게시, 정확 구현 base, 독립 검증 조건 봉인과 총괄 CORE-GO 뒤에만 구현한다. [구현 계획](../plans/2026-10-25-codex-virtual-one-action.md)을 함께 따른다.

## 1. 목적과 경계

fresh full64 가상 trial의 공개 관측으로 concrete Codex D2에 첫 제안 한 건을 요청하고, genuine strict decoder가 허용한 제안만 같은 살아 있는 trial의 기존 FleetHarness를 통해 최대 한 번 적용한다. 전후 관측, 거절, 상태 불변, 반환 불확실성과 정리 상태를 별도 증거로 남긴다. 한 번의 가상 명령 관측을 연속 의사결정·전체 복구·과업 평가·폐루프 완료로 부르지 않는다.

기존 [첫 판단 사용법](../../fcc/virtual_fleet_codex_first_decision_usage.md)과 [부모 설계](2026-10-25-codex-first-decision-design.md)의 capture 종료 후 dispatch0 의미를 유지한다. 기존 함수를 재개·상속하거나 그 결과 뒤에 명령을 붙이지 않는다. 원본·실패 기록은 보존한다. legacy report의 fixture/ai_model_called=false/not_assessed는 원형으로 유지하고 transport 증거는 별도 host receipt에 귀속한다. OperatorJournal provenance와 DB schema를 바꾸지 않는다.

추가 실제 CLI·모델·ADC·auth·실장비·출력·이동·현장망 권한과 새 실제 호출 예산은 부여되지 않는다. owner 검사는 fake D2와 genuine fresh 합성 simulator만 사용한다. 비용과 관측하지 않은 실제 시도 수는 null이다. 실제 제공자 실행은 기존 위임과 잔량을 총괄이 별도로 확인한 범위에서만 수행할 수 있다.

## 2. 확정 접근과 기존 API

A 직접 결합을 사용한다. 한 fresh trial/runtime/FleetHarness를 독점 보유하고, 고정 private 정책 함수가 공개 context에서 genuine builder→concrete D2→strict decoder→host gate를 직접 결합한다. 통과한 wire.proposal을 그대로 반환하면 첫 step이 기존 intent/dispatch/receipt/후행 observation을 처리한다. 이어 stop() 후 step()을 최대 한 번 호출해 두 번째 정책 판단 없이 감독 정지한다.

capture 종료 뒤 다른 하네스를 만드는 B는 수명과 ledger를 분리하므로 사용하지 않는다. 새 submit_proposal/paused-runtime API를 추가하는 C는 이 단위에서 보류한다. 새 framework·registry·public callback·runtime wrapper·SDK·DB 또는 legacy 공통 소스 수정은0이다. 내부 정책 함수는 기존 callable seam의 고정 구현이며 외부 주입 API가 아니다.

직접 사용하는 공개 API는 [catalog loader](../../../labflow/virtual_fleet/catalog.py), [fresh trial factory](../../../labflow/virtual_fleet/evaluation.py), [role actions](../../../labflow/virtual_fleet/integration.py), [FleetHarness](../../../labflow/virtual_fleet/harness.py), [prompt builder/strict decoder](../../../labflow/virtual_fleet/model_operator_boundary.py), [concrete D2](../../../labflow/codex_cli_response.py)다. 부모 [구현 계획](../plans/2026-10-25-codex-first-decision.md)과 [producer 계약](../../fcc/codex_cli_response_contract.json)을 재사용한다. 기존 private _Batch/_dispatch/_proposal/_boundary/helper를 호출하거나 상속하지 않는다.

## 3. 확정 API와 닫힌 입력

```python
def run_codex_virtual_one_action(
    *, catalog_path: Path, catalog_sha256: str,
    response_schema_bytes: bytes, executable: Path,
    requested_model: str, scenario: str,
    virtual_dispatch_authorized: bool,
    evidence_dir: Path, cancel_event: threading.Event | None = None,
) -> dict:
    ...
```

공개 export는 위 함수와 CodexVirtualOneActionError(RuntimeError) 정확2다. callback·provider·외부 runtime·clock·모델 목록을 받지 않는다. requested_model은 native str의 gpt-6.1-sol 또는 gpt-6-astra 한 개, scenario는 normal/restored_disconnect 한 개다. 한 호출에서 한 trial·한 모델 요청·한 decoder·최대 한 명령뿐이다. 행렬 비교와 다음 판단은 없다.

virtual_dispatch_authorized는 host가 전달하는 native bool이어야 한다. false는 delegation_denied로 evidence 생성·factory·D2 전 거절한다. bool 이외는 invalid_input이다. true가 뜻하는 범위는 이 dedicated API의 가상 한 건뿐이며 모델 출력·문서·이전 wire에서 true를 추론하지 않는다. 사용자의 기존 위임을 재사용하는 host 입력이지 매번 사용자 확인 창을 추가하라는 요구가 아니다. 이 값으로 실제 모델이나 실물 권한을 얻지 않는다.

경로·hash·schema 검증은 기존 첫 판단 계약의 native absolute Path, regular/no-reparse parent chain, catalog 최대1MiB/정확 lowerhex SHA256, absent evidence directory 규칙을 따른다. executable은 regular codex.exe이며 source를 임의 탐색하거나 설치·login하지 않는다. schema는 기존 literal3052B/SHA256 aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb 그대로다. producer_name도 dgm-virtual-operator-v1을 유지한다.

## 4. 생존 수명·binding·허용 범위

1. load_catalog/get_role_actions/prepare_sensor_trial을 직접 사용한다. 원 catalog를 고정하고 seed=0, power_dbm=12.5, 지정 condition의 fresh trial 하나를 만든다. trusted bootstrap 명령은 모델 명령 분모와 구별한다. author_record·_fleet·숨은 expected·기존 실제 응답을 읽지 않는다.
2. trial.runtime은 이 호출이 독점 보유하고 외부에 반환·공유하지 않는다. factory 이후부터 후행 관측과 감독 정지까지 같은 trial/runtime/harness를 유지한다. persistent resume·직렬화·새 runtime으로의 ledger 복구는0이다.
3. run_id/decision_id/model_request_id의 prefix는 각각 operator-one-run:, operator-one-decision:, operator-one-request:이며 각 뒤에 새 uuid4 hex32를 붙인다. runtime_instance_id는 fresh trial의 공개 속성 그대로다. 이전 호출의 ID나 wire를 재사용하지 않는다.
4. 기존 FleetHarness에 같은 catalog/topology/goal/actions/runtime/IDs를 전달한다. full catalog profile64, topology device64, observations device64 및 모든 profile→device→role 매핑이 일치해야 한다. 모든64를 보여 주는 것은64개 장비의 모든 명령을 허가하는 뜻이 아니다.
5. 첫 정책 진입에서 detached context8을 복사한다. 원 goal/topology/actions/profile IDs와 trial.runtime.observations()의 canonical 전체 값을 대조하고 before로 보존한다. context8에서 remaining_budget 한 필드만 분리해 context7을 만든다. genuine build_operator_prompt가 binding6/context hash/request hash를 생성한다.
6. decoder의 허용 scope는 rf_sensor_proposal_v1 그대로다. goal.dut_id의 start {}, goal.sensor_id의 acquire/read {}, advance ticks=1, 또는 기존 bounded stop만 허용한다. supply/position/다른64 profile·configure/reset/임의 parameters는 거절한다. 임의의 role action 메타데이터가 이 좁은 scope를 확장하지 않는다.
7. D2 반환·원 artifact/receipt 검증·genuine decode 후에 catalog/code pin, same runtime ID, 현재 tick/setup_revision 및 before 전체 관측 hash를 다시 확인한다. 살아 있는 runtime 관측이 달라졌다면 dispatch0으로 거절한다. decoder 통과 자체는 실행 위임이 아니다.
8. 마지막 gate는 host 위임, cancel/두 deadline, 남은 one-action fuel, binding과 변하지 않은 관측을 확인한다. 그 뒤 detached wire.proposal을 수정 없이 기존 정책 결과로 반환한다. request_id는 FleetHarness가 생성한다. host가 runtime.execute/advance를 직접 부르거나 원 request_id를 주입하지 않는다.

setup_revision 하나를 세대 ID처럼 독립 사용하지 않는다. binding의 fresh runtime_instance_id와 context hash, tick/revision, 전체 관측 및 source pins를 함께 확인한다. 현재 execute API에는 expected_revision의 atomic compare-and-execute가 없다. 따라서 지원 범위는 이 host가 독점 소유하는 fresh in-process trial이다. 다른 thread/외부 소유자의 동시 변경을 원자적으로 막았다고 주장하지 않는다. 그런 입력은 받지 않으며 향후 공유 운전은 별도 공통 계약이다.

## 5. 고정 fuel과 시간

첫 판단의 외부 상한 model_calls=8/wall_seconds=60 및 producer 정리 여유6초를 늘리지 않는다. 8은 기존 한도 숫자의 재사용이며 신규8회 할당이나 소진된 root 실제 ledger의 reset이 아니다. 현재 실제 예약은0이다. 향후 실제 호출의 위임·잔량 확인은 총괄의 별도 GO가 필요하고 이 함수가 계정 전역 잔량을 인증하지 않는다.

이 단위의 계획된 producer 진입은 최대1이며 호출 전 예약하고 실패·거절·취소 후 환급하지 않는다. version/model process attempt와 host 예약은 구별한다. 원 receipt가 없으면 실제 시도 수는 null이다. 자동 재시도/fallback·다음 모델·재구성·ledger clear·budget refund는0이다.

기존 FleetHarness의 더 낮은 하위 한도를 명시한다: decisions=1, logical_requests=1, ticks=1, wall_seconds=30, transport_retries=0. 이는 새 fuel을 더하는 것이 아니라 기존 인수로 scope를 줄이는 확정값이다. prompt delegation의 harness_budgets도 이 실제 값과 같고 outer_limits는 기존8/60 그대로다. 첫 판단 API의64/64/32/30/2는 변경하지 않는다.

정책 context8을 받는 시점에는 현재 첫 decision이 이미 차감되어 remaining_budget.decisions=0이다. 이를 새 decision 부족으로 오해해 현재 제안을 거절하지 않는다. 원 remaining을 그대로 보존하고 full 선언1과 구별한다. 현재 정책 진입1·논리 명령 잔량1·advance용 tick 잔량1과 host 모델 예약≤1을 각각 검사한다. cleanup step은 이0 잔량을 reset하지 않고 stop boundary에서 끝나야 한다.

preflight 뒤 evidence 생성 전 outer monotonic 시작+60, 첫 step 직전의 보수적 anchor+30을 별도로 고정한다. 새 harness를 만들어 clock을 재시작하지 않는다. producer 직전 남은 두 시간 중 작은 값이6초를 초과해야 한다. timeout_seconds=min(60, outer_remaining-6, harness_remaining-6)을 준다. producer의 반환 지연이30초 하네스 경계를 넘었으면 wire가 유효해도 dispatch0이다. 54초짜리 요청을30초 하네스 안에 넣어 성공으로 보지 않는다.

첫 step 후 즉시 supervisor stop을 요청하고 step을 한 번 더 호출할 수 있다. 기존 _boundary가 stop을 정책 전에 확인하므로 두 번째 정책 판단·D2·execute/advance는0이어야 한다. run() 반복 호출은 사용하지 않는다. RetryableTransportError에서도 transport_retries=0이므로 실제 재파견0, 원 unresolved/uncertain을 보존한다.

## 6. 전후 관측·거절·효과

genuine strict decoder 이전에 실패하면 wire/dispatch는 없다. scope/binding/producer 오류는 원 code를 보존한다. 정책 내부 예외·control은 외부 최초 latch에 보존해 FleetHarness의 policy_error 흡수 뒤에도 producer·다음 동작을 열지 않는다.

유효 stop은 기존 policy_stop과 원 claim/reason을 보존하고 command0으로 끝난다. completed라는 문자열은 과업 완료가 아니다. execute/advance는 기존 intent→virtual call→receipt→cause_request_id 후행 observation 경계를 사용한다. 후행 관측은 read-only observations()로 대조하고 별도 저장한다. read를 추가 명령으로 보내거나 효과 확인용 advance를 덧붙이지 않는다.

intent는 실제 호출 완료의 증명이 아니다. complete receipt와 연결된 후행 observation을 확인하면 confirmed_receipts=1, runtime_call_attempts=1이다. intent 전 종료는0이다. intent 이후 receipt/관측이 불확실하면 actual attempt와 dispatch count는 null이고 upper bound1·unresolved를 보존한다. 재실행으로 확인하지 않는다.

receipt_status는 원 ok/pending/invalid/unsupported/error/disconnected를 저장한다. 뒤4개는 runtime_rejected이며 성공으로 반환하지 않는다. ok/pending도 과업 성공을 뜻하지 않는다. before/after canonical 관측을 비교한 effect는 changed/unchanged/unknown/not_applicable이다. 변하지 않은 read, 아직 pending인 start, 거절·단선·측정 없음은 별도 관측으로 남기며 신규 유효 측정이나 업무 진행을 만들어 내지 않는다. changed는 측정 정확도나 과업 적합성의 판정이 아니다.

advance이면 tick_delta=1, execute이면0을 기대한다. setup_revision은 감소하면 안 되지만 start/read/acquire마다 +1이라고 강제하지 않는다. 실제 source는 command에 따라 revision 변화와 상태 불변이 가능하다. full64 관측·원 receipt·event/request binding을 모두 보존한다. evaluate_sensor_run/author oracle은 호출하지 않고 task_assessment_status=not_executed, task_score=null, closed_loop_complete=false다.

## 7. 취소·정리와 첫 실패

cancel_event는 None 또는 native threading.Event이고 stage 사이에서만 관측한다. pre-set이면 모든 작업0이다. D2에는 in-flight cancel 인수가 없으므로 반환/timeout 후 관측하며 완료된 원 trace는 보존하되 decode/dispatch를 열지 않는다. 마지막 gate 뒤 취소가 발생하면 이미 한 번의 mutation이 있었을 수 있다. 관측된 사실과 불확실성을 기록하고 rollback·새 명령·remote cancellation을 주장하지 않는다.

호출 종료 때 stop()+최대1 cleanup step으로 하네스를 terminal 상태로 만들고 result/events를 원형 보존한다. SensorTrial/_OperatorRuntime에는 close나 output shutdown API가 없다. 새 DUT.stop/advance를 정리 명령으로 보내지 않는다. host 소유 파일 handle의 close는 기존 outer deadline 안에서 max(0,min(2,remaining))초 join으로 확인하고, 미회수는 cleanup_failed다. trial/runtime 참조를 외부에 남기지 않는다. 이것은 device output off·객체 GC 완료·실물 정리의 검증이 아니다. virtual_outputs_disabled=null, remote_cancel_verified=false다.

기존 trusted pure Python simulator의 동기 execute/observations 및 OS IO를 강제 중단하는 sandbox는 없다. bounded stage/정리 확인의 한계와 first-error/uncertain을 기록한다. 임의의 blocking runtime을 지원한다고 약속하거나 숨은 executor/process를 추가하지 않는다.

새 오류 prefix는 operator_virtual_one_action_이고 suffix는 invalid_input/delegation_denied/unsupported_source/capture_failed/budget_exhausted/cancelled/timeout/retention_failed/runtime_rejected/runtime_uncertain/cleanup_failed/internal_error다. 기존 producer11·boundary8 full code는 원형 보존한다. .code/str/args는 고정 code, cause/context=None, .receipt는 가능한 detached partial다. 최초 code/stage는 후행 close/finalize 오류로 덮지 않는다. 관측한 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 best-effort cleanup 뒤 동일 객체로 전파한다. 부모 안에서 이미 삼켜진 원 예외를 복원했다고 주장하지 않는다.

## 8. 최소 증거 형상

top exact12는 schema_version/kind/run_id/status/failure/declaration/budget/step/cancellation/cleanup/execution/verification이다. kind=codex_virtual_one_action_result. status는 observed/stopped/rejected/failed다. 반환 observed/stopped는 한 건의 증거 수집 범위만 뜻한다. runtime 거절은 rejected receipt를 가진 오류, 불확실성·저장·취소·timeout은 failed 오류다. task PASS 상태는 없다. 닫힌 nested key/type/value는 §9에 고정한다.

step은 stage/binding/before/after/transport/wire/dispatch/harness/artifacts/failure exact10이다. before/after는 full observation 파일의 metadata이며 full64 원본은 별도 보존한다. wire는 genuine wire5, transport는 원 D2 receipt18/exchange ref/hash를 유지한다. host report와 legacy harness report의 의미를 합치지 않는다.

고정 파일은 caller-request.json, response-schema.json, one-action-receipt.json 및 context8.json/public-context7.json/binding.json/prompt.json/before.json/after.json/wire.json/harness-report.json/harness-events.json/dispatch-receipt.json이다. producer/ 아래에는 원 D2 artifact9·receipt.json·work가 있다. 작성 전 absent를 확인하고 실패·partial·원본을 삭제/수선하지 않는다. prefix를 whole_file로 인증하지 않는다. 매 descriptor는 기존 path/present/bytes/sha256/complete/overflow/extent exact7이다.

host JSON은 UTF-8/BOM없음, ensure_ascii=False, sort_keys=True, allow_nan=False, compact separators, 마지막 LF없음으로 고정한다. context/request/observation hash는 이 canonical bytes의 SHA256이다. before/after metadata의 hash는 해당 전체 observation 파일과 같아야 한다. 원 producer의 JSONL·stderr·final bytes는 변환하지 않는다.

context8/context7/before/after 각1MiB, binding/wire/dispatch receipt 각64KiB, prompt/harness report/host request/host receipt 각256KiB, harness events2MiB, schema64KiB 한도를 적용한다. 원 D2 artifact cap은 바꾸지 않는다. source/catalog를 호출 전후 다시 확인하고, producer 반환 bytes/final-text/last-message/원 receipt 및 artifact9 literal·완전 크기·SHA를 검증한 뒤에만 decoder/dispatch로 진행한다. first-decision의 private helper를 import해 공통 소유를 숨기지 않는다. 필요한 유한 host 검사는 새 파일 내부의 고정 구현 범위다.

비용·identity·semantic quality·hardware 검증은 관측하지 않았으면 null/false다. 원격 hard cancel, CLI 내부 retry, 계정 전역 한도, 순간 disk quota, 전체64 장비 검증 또는 실제 시험소 무인화 완료를 이 증거로 올리지 않는다.


## 9. 닫힌 receipt의 키와 값

모든 DTO는 native JSON type만 허용하며 bool을 정수로 취급하지 않는다. hash는 lowerhex64, ID는 기존 bounded identifier 규칙을 따른다. 초기·실패 단계에서 생성하지 못한 step 자료는 null이고 artifact는 absent descriptor다. 임의 key나 원형 DTO의 보충·수선은 허용하지 않는다.

| 객체 | 정확한 키 | 타입·고정값 |
| --- | --- | --- |
| top exact12 | schema_version/kind/run_id/status/failure/declaration/budget/step/cancellation/cleanup/execution/verification | schema_version=1, kind=codex_virtual_one_action_result, fresh run_id, status=observed/stopped/rejected/failed |
| failure exact2 | code/stage | null 또는 최초 고정 code와 stage; 후행 오류로 덮지 않음 |
| declaration exact7 | scenario/requested_model/producer_name/catalog_sha256/schema_sha256/virtual_dispatch_authorized/scope | 단일 허용 scenario/model, 중립 producer, 원 catalog/schema hash, native true, rf_sensor_proposal_v1 |
| budget exact9 | limits/reserved_model_calls/producer_calls_started/version_process_attempts/model_process_attempts/elapsed_seconds/reservation_refunded/application_retries/new_budget_granted | 예약·producer 진입0..1, 원 receipt로 관측한 process attempt0..1 또는 null, elapsed_seconds 유한 비음수, false/0/false |
| limits exact4 | model_calls/wall_seconds/producer_cleanup_allowance_seconds/harness_budgets | 기존8/60.0/6.0, 실제 하위 budgets1/1/1/30/0; 신규 할당 아님 |
| harness_budgets exact5 | decisions/logical_requests/ticks/wall_seconds/transport_retries | 1/1/1/30/0 |
| step exact10 | stage/binding/before/after/transport/wire/dispatch/harness/artifacts/failure | 단계별 detached 자료; 실패 전 생성하지 않은 값은 null |
| binding exact6 | run_id/runtime_instance_id/decision_id/model_request_id/context_sha256/request_sha256 | genuine builder 원형; 새 UUID ID와 canonical hash |
| before/after exact5 | tick/setup_revision/device_count/sha256/present | null 또는 native 비음수 tick/revision, device_count64, 전체 관측 canonical hash, present bool; 성공 증거는 present=true |
| transport exact3 | exchange_ref/receipt/receipt_sha256 | null 또는 원 D2 exchange ref/원형 receipt18/완전 보존이 확인된 hash; 미확인은 null |
| wire exact5 | schema_version/kind/request_sha256/producer/proposal | genuine decoder의 원 virtual_operator_response; 수정 없음 |
| dispatch exact8 | intent_seen/request_id/operation/reserved_logical_requests/confirmed_receipts/runtime_call_attempts/receipt_status/effect | intent bool, request ID 또는 null, execute/advance 또는 null, 예약/확인0..1; 실제 미확인 수는 null |
| harness exact3 | termination/unresolved_request_ids/legacy_ai_model_called | 원 reason/policy_claim exact2 또는 null, 원 미결 ID 배열, false |
| cancellation exact4 | requested/scope/observed_stage/remote_cancel_verified | bool/between_stages_only/stage 또는 null/false |
| cleanup exact6 | supervisor_stop_requested/terminal_report_observed/host_artifacts_closed/virtual_outputs_disabled/remote_cancel_verified/secondary_errors | stop·terminal 관측 bool, host close bool 또는 null, null/false, 고유 후행 code 최대8 |
| execution exact8 | mode/synthetic/model_proposal_dispatches/task_assessment_status/task_score/closed_loop_complete/hardware_verified/physical_cleanup_verified | virtual_one_action/true/확인된0 또는1 또는 null/not_executed/null/false/false/false |
| verification exact6 | wire_accepted/dispatch_trace_complete/source_inputs_unchanged/remote_identity_verified/semantic_quality_verified/hardware_verified | 앞3은 직접 관측한 bool, 뒤3은 false |

runtime_call_attempts와 model_proposal_dispatches는 intent 전 종료이면0, complete receipt와 causal after 관측 확인 시1, intent 뒤 미확인이면 null이다. 고정 소스·fuel에 따른 상한1과 실제 확인값을 구별한다. intent만 보고 실제 완료를 세지 않는다. 모델 stop은 command0/effect=not_applicable이다.

receipt_status는 ok/pending/invalid/unsupported/error/disconnected 또는 null이다. 뒤4개는 runtime_rejected이며 rejected receipt를 가진 오류로 처리한다. effect는 changed/unchanged/unknown/not_applicable이다. unchanged나 pending을 유효한 측정 또는 과업 성공으로 올리지 않는다.

secondary_errors는 artifact_close_failed/receipt_write_failed/supervisor_termination_unconfirmed/secondary_overflow 중 고유 관측 순서 최대8이다. 저장·정리 확인이 부족하면 true로 채우지 않는다. step.failure도 null 또는 원 code/stage exact2다. stage는 preflight/setup/capture/prompt/reserve/producer/retain/decode/gate/dispatch/observe/cleanup/finalize 중 실제 최초 실패 단계다.

## 10. 파일 형상과 한도

caller-request.json은 schema_version/kind/run_id/execution/declaration/source_pins/limits exact7이며 execution은 catalog_path/executable exact2다. 이 실행 전용 메타데이터의 경로는 모델 공개 context로 보내지 않는다. binding.json은 binding/delegation/remaining_budget/catalog_sha256/schema_sha256 exact5다. 최종 host receipt는 one-action-receipt.json이다.

step.artifacts exact10은 아래 key를 사용한다. 각 descriptor는 path/present/bytes/sha256/complete/overflow/extent exact7이고 원 whole_file/prefix/absent 의미를 따른다. complete 성공에는 overflow=false와 파일 전체 size/hash 일치가 필요하다.

| key | 고정 파일 | 최대 bytes |
| --- | --- | ---: |
| context8 | context8.json | 1048576 |
| context7 | public-context7.json | 1048576 |
| binding | binding.json | 65536 |
| prompt | prompt.json | 262144 |
| before | before.json | 1048576 |
| after | after.json | 1048576 |
| wire | wire.json | 65536 |
| harness_report | harness-report.json | 262144 |
| harness_events | harness-events.json | 2097152 |
| dispatch_receipt | dispatch-receipt.json | 65536 |

catalog 최대1048576B, schema 최대65536B, caller-request/host receipt 각262144B다. response-schema.json은 부모의 고정 literal3052B를 변형 없이 보존한다. host가 새로 작성하는 JSON DTO의 canonical 규칙과 구별한다. producer/에는 원 artifact9/receipt.json/work를 그대로 두고 수집 cap을 바꾸지 않는다. 원 producer/final-text/last-message/반환 bytes와 원 receipt 및 artifact9의 고정 path·전체 크기·SHA를 확인한 뒤에만 decoder와 dispatch를 연다.

## 11. 구현 파일과 진입 조건

생성 예정 경로는 다음 신규3이며 현재 파일의 존재나 구현 완료를 뜻하지 않는다.

- labflow/virtual_fleet/codex_virtual_one_action.py
- tests/test_virtual_fleet_codex_virtual_one_action.py
- docs/fcc/virtual_fleet_codex_virtual_one_action_usage.md

공통 소스 수정이 필요해지면 이 범위를 넓히지 않고 총괄에게 소유와 정확 base 결정을 반환한다. 공통 문서 게시·정확 구현 base·독립 검증 조건 봉인·총괄 CORE-GO 전에는 제품 코드·RED·test runtime·D2·실제 CLI를 실행하지 않는다. 기존 clone의 reset/rebase/merge로 base를 맞추지 않는다.

검증은 [구현 계획](../plans/2026-10-25-codex-virtual-one-action.md)의 위임 거절, full64 같은 수명, strict scope/current binding, 명령 최대1, 전후 효과·거절·불확실성, 두 deadline·취소·정리·원 오류 보존을 따른다. 문서 무결성 통과는 가상 기능·실제 모델 품질·실장비·규범 적합성 검증과 구별한다.
