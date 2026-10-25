# Codex Virtual One Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task only after root fixes the exact base, ownership and GO. The design is accepted; product work still requires exact base and CORE-GO. No subagent dispatch.

**Goal:** fresh full64 가상 context의 첫 제안 한 건만 기존 FleetHarness 경계로 적용하고 전후 증거를 보존한다.

**Architecture:** 하나의 fresh trial과 하나의 live FleetHarness를 유지한다. 고정 private 정책이 genuine builder→concrete D2→strict decoder→host gate를 직접 결합한다. 첫 step 뒤 stop()+최대1 cleanup step으로 종료하며 다음 모델 판단은 없다.

**Tech Stack:** 기존 Python 3.12/stdlib, unittest, 기존 virtual_fleet와 concrete Codex D2. 새 framework/registry/SDK/DB는 없다.

**Spec:** [확정 설계](../specs/2026-10-25-codex-virtual-one-action-design.md). 닫힌 DTO와 파일 한도는 설계 §9/10을 따른다.

## Global Constraints

- 이 문서는 구현 전 계획이다. 공통 문서 게시·정확 base·독립 검증 조건 봉인·총괄 CORE-GO 전 core·테스트·RED·제품 import0이다.
- 기존 첫 판단 API의 capture 종료 후 dispatch0 의미, 원본·실패·검증 기록과 다른 담당의 소스를 보존한다.
- 확정 공개 API는 run_codex_virtual_one_action과 CodexVirtualOneActionError exact2, 신규3만이다. callback/provider/runtime/clock 인수와 공통 source 변경은0이다.
- scope rf_sensor_proposal_v1, full64 catalog/topology/observations, seed=0/power_dbm=12.5, single normal/restored_disconnect 및 single gpt-6.1-sol/gpt-6-astra다.
- host virtual_dispatch_authorized는 native true만 실행 위임이다. false는 factory/증거/D2 전 delegation_denied, 비bool은 invalid_input이다. 실제 모델/물리 실행 위임은 추가되지 않는다.
- 기존 outer cap8/wall60/cleanup reserve6을 늘리지 않는다. 하네스는 decisions1/logical_requests1/ticks1/wall30/transport_retries0으로 줄인다. 계획 producer1/decoder1/정책1/명령≤1, retry/reset/refund/fallback0이다.
- 첫 step 이전 보수적 anchor로 harness deadline30을 고정하고 producer timeout은 min(60,outer_remaining-6,harness_remaining-6)이다. 같은 runtime/harness를 재구성하지 않는다.
- 기존 schema3052B/SHA aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb, producer dgm-virtual-operator-v1을 유지한다.
- owner 검증은 fake D2/genuine fresh simulator만이다. 실제 subprocess/socket/ADC/auth/모델/livebudget/현장0, 과업 평가·score not_executed/null, closed_loop_complete=false다.

## Review Focus

1. producer 대기 중 current generation 또는 관측이 바뀜: 같은 trial UUID만으로 허용하지 않고 full observation/hash/tick/revision/source를 대조해 dispatch0이어야 한다.
2. 64개 profile의 넓은 role_actions와 좁은 위임의 혼동: goal DUT.start/sensor.acquire/read/advance1/stop 외 명령은 decoder나 host에서 거절해야 한다.
3. 정상 wire가30초 하네스 deadline 뒤 도착하거나 취소됨: trace를 보존하되 dispatch0, 재예약/환급0이어야 한다.
4. receipt 이후 후행 관측/저장 실패 및 상태 불변: intent/완료를 구별하고 uncertain/null 또는 unchanged를 기록하며 과업 성공을 만들면 안 된다.
5. cleanup stop 뒤 두 번째 정책·가상 명령, 내부 transport retry 또는 output-off 주장: 호출 수를 확인하고 최대1/0 retry와 정리 미검증 상태를 유지해야 한다.

## 제안 파일 구조와 공통 gate

Create: labflow/virtual_fleet/codex_virtual_one_action.py, tests/test_virtual_fleet_codex_virtual_one_action.py, docs/fcc/virtual_fleet_codex_virtual_one_action_usage.md.

기존 load_catalog/prepare_sensor_trial/get_role_actions/FleetHarness/build_operator_prompt/decode_operator_response/produce_codex_cli_response의 공개 API만 직접 사용한다. 기존 [harness](../../../labflow/virtual_fleet/harness.py)의 private _dispatch/_proposal/_boundary 호출과 first-decision _Batch/helper import는0이다. 확정 설계의 소스는 설계 참고 snapshot이며 후속 exact base를 대신하지 않는다. 공통 수정이 필요하면 구현을 확장하지 않고 총괄 소유 결정을 기다린다.

### Task 1: 위임·fresh capture·유효 stop

**Files:** 신규 core/test. **Interfaces:** 설계 §2에서 링크한 공개 부모 소스의 signature를 따른다. 생산 API는 spec §3의 keyword-only 함수와 고정 error2다. 이 task의 유효 결과는 stop wire/command0까지다.

- [ ] **Step 1: GO와 새 작업 위치 확인.** 총괄의 공개 규범·정확 base·신규3 소유·독립 검증 조건 봉인과 CORE-GO를 확인한다. 기존 첫 판단 API와 원본 기록을 보존한다. 실제 CLI/auth/model/socket 차단 guard와 자기 검증 작업공간을 테스트에 둔다. 설치·기존 공유 폴더 쓰기는 하지 않는다.
- [ ] **Step 2: 실패 검사 작성.** test_public_signature_and_exports, test_delegation_false_and_nonbool_preflight_zero, test_fresh64_capture_bound_stop_zero_dispatch를 작성한다. exact2 export/인수/native 타입, false와 1의 다른 code, factory/D2/증거0, profile/device64, ID 새로움/context7 및 schema/hash, genuine decoder stop/명령0/legacy false를 assert한다. 이미 차감된 context.remaining_budget.decisions=0과 full delegation.decisions=1을 각각 보존하고 현재 정책을 거절하거나 잔량을 reset하지 않음을 확인한다.
- [ ] **Step 3: RED 확인.** python -B -X utf8 -m unittest tests.test_virtual_fleet_codex_virtual_one_action -v를 독립 환경에서 실행하고 API 부재 실패를 원본/log/result로 남긴다. local tests namespace 충돌 시 부모 파일을 바꾸지 않고 실행 경로를 명시한다.
- [ ] **Step 4: 최소 구현.** spec의 native preflight와 고정 private 정책, 한 trial/하네스 lifetime, 외부 first-error/control latch, genuine builder/D2/decoder 및 유효 stop 보존만 추가한다. 실제 D2는 테스트에서만 fake로 치환한다. false 위임은 어떤 evidence도 만들기 전에 거절한다.
- [ ] **Step 5: GREEN과 커밋.** 같은 검사에서 fail/error/skip0과 stop command0을 확인한다. 소유 core/test만 정상 커밋한다. 기존 첫 판단 API는 재사용하거나 의미를 변경하지 않는다.

### Task 2: 같은 하네스의 명령 최대1과 전후 효과

**Files:** 신규 core/test. **Interfaces:** Task1의 함수만 확장한다. FleetHarness.step()에는 wire.proposal을 그대로 반환하고 request ID·dispatch·receipt·후행 observation은 기존 하네스에 맡긴다. 외부 runtime 인수나 새 dispatch API는 없다.

- [ ] **Step 1: RED 작성.** test_same_live_trial_one_execute_then_supervisor_stop, test_advance_exactly_one_tick_no_followup, test_sensor_read_unchanged_is_not_task_success를 추가한다. D2 fake 외에는 genuine runtime 동작을 사용하고 pass-through spy로 실제 public execute/advance 수를 관측한다. model 요청/decoder/정책1, logical1/가상call≤1, cleanup 정책0, full64 before/after, causal request binding, task score null을 assert한다.
- [ ] **Step 2: 거절·세대 RED 작성.** test_scope_cannot_expand_to_other64_actions, test_stale_binding_or_changed_observation_prevents_dispatch, test_current_source_changed_prevents_dispatch, test_runtime_rejected_or_uncertain_never_retries를 추가한다. wrong producer/hash/replayed IDs·DUT.configure/다른 profile·seed/author private key, fake D2 도중 current observation 변화, catalog/code pin 변화, RetryableTransportError를 주입한다. 원 code·dispatch0 또는 unresolved/null·실제 retry0을 assert한다. 실제 source 파일을 변조하지 말고 읽기 fault injection을 사용한다.
- [ ] **Step 3: RED 실행·보존.** 새 검사들을 실행하고 기대 실패와 현재 source snapshot을 기록한다. old expected를 고치거나 기준을 약하게 만들지 않는다.
- [ ] **Step 4: 최소 gate/observe 구현.** 하네스 하위 한도1/1/1/30/0, 원 context8와 source/current 비교, dispatch 전 필수 증거 저장을 적용한다. 첫 step 뒤 stop()+한 cleanup step만 호출한다. before/after effect와 receipt status를 분리하며 host가 runtime.execute/advance를 직접 호출하지 않는다. ready/pending/no-change를 과업 PASS로 바꾸지 않는다.
- [ ] **Step 5: GREEN과 커밋.** 동일 fresh simulator로 normal/restored_disconnect의 한 건씩 검증한다. recovery의 4tick 후 복구를 기다리거나 추가 tick을 보내지 않는다. source pins·기존 첫 판단 API 불변·실제 CLI/auth/model0을 확인하고 정상 커밋한다.

### Task 3: deadline·취소·증거·정리와 사용법

**Files:** 신규 core/test/usage. **Interfaces:** 함수와 exact12 host receipt는 그대로다. 설계 §9 receipt 중 transport 원18, legacy harness 결과와 wire5는 수정하지 않고 저장한다.

- [ ] **Step 1: 시간/취소 RED 작성.** test_tighter_harness_deadline_limits_producer_timeout, test_late_valid_wire_and_cancel_do_not_dispatch, test_cancellation_after_intent_preserves_uncertainty를 추가한다. producer 전 remaining≤6은 예약/호출0, postproducer30초 경계는 dispatch0, Event는 between-stages, intent 이후 실제 미확인은 null·refund0이어야 한다. fake 시간 관측은 테스트 도구이며 공개 clock 인수로 만들지 않는다.
- [ ] **Step 2: 저장/control RED 작성.** test_original_producer_artifacts_and_receipt_are_exact, test_short_read_or_final_mismatch_prevents_decoder, test_postdispatch_observation_failure_preserves_first_stage, test_bounded_close_and_control_identity_survive_secondary_error를 추가한다. 원 artifact9/receipt18·final bytes의 whole-file hash/size, truncated prefix 거절, 저장 후행 실패·unresolved·오류 우선순위, 원 control 동일 객체와 close join≤남은 outer/2초를 assert한다. cleanup을 DUT.stop 또는 추가 advance로 구현하면 실패해야 한다.
- [ ] **Step 3: RED 실행·보존 후 최소 구현.** 원 실패 code/stage/control을 latch하고 bounded exact-file 보존·source 전후 검사·취소/두 deadline·supervisor termination·host close를 닫는다. 원 오류를 finalize로 교체하지 않고 확인 못 한 attempt/cleanup은 null/false로 남긴다.
- [ ] **Step 4: GREEN 및 문서 확인.** owner 신규 검사, genuine harness/operator boundary/producer의 변경 관련 회귀와 기존 first-decision 회귀를 실행한다. 통과한 검사 반복은 새 수정·실패·미해결 우려가 있을 때만 한다. python -B -X utf8 scripts/check_artifacts.py와 새 usage link/코드블록을 확인한다. 새 사용법에는 가상1건·실제0·과업평가0·정리 미검증을 명시한다.
- [ ] **Step 5: 독립 검토 제출.** 소유 신규3만 정상 커밋·푸시하고 정확 parent/HEAD/raw pins/remote/clean, 원 RED/실패/통과 log, genuine fresh+fake D2 표본과 bounded proof를 봉인한다. 총괄에게만 반환하고 독립 C/I 필수 수정에 우선 대응한다. 실제 CLI·모델·현장 실행을 추가하지 않는다.

## 자기 검토와 현재 전달 범위

spec §3→Task1, §4/6→Task2, §5/7/8/9/10→Task3로 연결했다. Review Focus 5개를 Task2/3의 named test에 배정했다. symbol과 타입은 공개 부모 API에서 AST로 확인하며 실행하지 않는다. 세 task는 같은 신규3 단위를 단계적으로 검증하고, 별도 공통 owner나 DB 작업을 만들지 않는다.

이 계획의 구현 단계는 아직 시작하지 않았다. 총괄이 정확 base/소유/공개 규범/독립 검증 조건 봉인/CORE-GO를 고정하기 전에는 어떤 RED·core·테스트·제품 실행 단계도 시작하지 않는다.

부모 [첫 판단 계획](2026-10-25-codex-first-decision.md)과 [첫 판단 사용법](../../fcc/virtual_fleet_codex_first_decision_usage.md)의 기존 경계를 유지한다.
