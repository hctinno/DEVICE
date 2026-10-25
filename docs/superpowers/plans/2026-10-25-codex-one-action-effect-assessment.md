# Codex One Action Effect Assessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans after root fixes ownership, public contract, exact base and CORE-GO. No subagent dispatch. This document is not an implementation GO.

**Goal:** 단일 행동의 제공 before/after와 허용 제안·최초 오류를 추적해 관측 효과·명령 결과·근거 부족을 분리한 별도 effect assessment를 반환한다.

**Architecture:** native packet9의 고정 pure-memory sidecar다. 원 host12/producer18/wire5/legacy를 보존하고 공개 strict decoder만 원 wire 재대조에 재사용한다. 기존 full sensor/meter task evaluator 호출0, task not_evaluated/verdict null/score null/evaluator_called false다.

**Tech Stack:** Python 3.12/stdlib, unittest, 기존 공개 decoder. 신규 SDK/DB/registry/runtime/reader/Store는 없다.

**Spec:** [확정 설계](../specs/2026-10-25-codex-one-action-effect-assessment-design.md). packet/output·enum·nullable·오류·size와 고정 수용 조건은 설계 §4~9의 같은 값을 따른다.

## Global Constraints

- 원 host12/producer18/wire5/legacyfalse와 정책·원본·실패 기록을 보존하고 현재 단일 행동을 소급해 과업 평가완료로 바꾸지 않는다.
- 이 단위는 공개 부모 소스와 공개 단일 행동 계약을 따른다. 다른 담당의 소유 파일·공통 API·기존 evaluator를 변경하지 않는다.
- 공통 계약·정확 base·신규3 소유·독립 검증 조건·별도 CORE-GO 전 제품/RED/test runtime/평가 API 실행을 시작하지 않는다.
- API는 assess_codex_one_action_effects(packet, *, caller_error_code=None)와 CodexOneActionAssessmentError exact2이며 생성 예정 core/test/usage3만 소유한다.
- packet exact9/output exact14/checks6/verification10/task4, nullable·enum·size 값은 설계 기계 계약과 동일하다.
- input8MiB/output64KiB/events16/각512KiB/총2MiB/depth32/nodes200000/signed64를 적용한다. 데이터 처리 한도를 모델·운영 예산으로 해석하거나 새 예산·seed/reset/refund를 만들지 않는다.
- 실제 installed CLI/모델/ADC/auth/livebudget/운영Store/외부망/실장비를 호출하지 않는다. 값과 그래프의 일관성을 실제 runtime/storage/권한 검증으로 올리지 않는다.

## Review Focus

1. 같은 값·UUID를 가진 재생과 실제 fresh runtime의 혼동: 그래프 일관성만 확인하고 runtime/storage/authority verification은 false여야 한다.
2. 정상 pending/unchanged 및 known rejection을 task 성공·실패로 올리는 경우: command와 effect를 별도 기록하고 score null을 보존해야 한다.
3. 후행 after/receipt/events가 빠진 prefix: intent를 실제 완료로 세지 않고 unknown/insufficient여야 한다.
4. 최초 source 오류와 caller code·후행 close의 충돌: 원 first error를 유지하고 모순을 지적하되 결과를 수선하지 않아야 한다.
5. 기존 evaluator에 goal/policy/선언을 만들어 강제로 넣는 경우: 해당 호출0·host 불변을 검증해야 한다.


## 생성 예정 파일과 API 경계

신규 경로는 labflow/virtual_fleet/codex_one_action_assessment.py, tests/test_virtual_fleet_codex_one_action_assessment.py, docs/fcc/virtual_fleet_codex_one_action_assessment_usage.md다. 생성 예정 파일의 존재를 가정한 링크를 만들지 않는다.

기존 meter 평가·sensor 평가·strict decoder의 실제 signature와 제약은 설계 §2에서 링크한 공개 부모 소스를 따른다. 호환되지 않는 full task evaluator를 호출하거나 trial을 재구성하지 않는다.

### Task 1: native packet·불변 hash·부족 근거

**Files:** 신규 core/test. **Consumes:** spec exact9 packet과 optional fixed caller_error_code. **Produces:** assess_codex_one_action_effects(packet: dict, *, caller_error_code: str | None=None) -> dict, 고정 error class 및 exact14 detached 결과.

- [ ] **Step 1: 후속 GO 확인.** 현재 후보 독립 수용·필수 수정 완료, 새 규범/정확 base/신규3 소유·독립 검증 조건·CORE-GO를 확인한다. 기존 clone을 reset/rebase/merge하지 않는다.
- [ ] **Step 2: RED 작성.** test_native_shape_and_resource_limits, test_none_is_not_empty_response, test_missing_after_is_unknown_not_zero, test_caller_only_refusal_is_not_task_assessment를 추가한다. unknown key/subclass/cycle/NaN/bool-as-number·8MiB/16events/depth/node 경계, exact10 component hash, absent/빈bytes 구별과 score null을 literal로 assert한다.
- [ ] **Step 3: RED 실행·보존.** python -B -X utf8 -m unittest tests.test_virtual_fleet_codex_one_action_assessment -v로 API 부재 실패를 확인한다. 현재 단계에서는 실행하지 않는다.
- [ ] **Step 4: 최소 구현.** bounded native 복사·고정 component hash·first error 보존·None 자료 부족·고정 code만 구현한다. 파일·runtime·부모 private validator·Store를 사용하지 않는다.
- [ ] **Step 5: GREEN과 커밋.** 같은 검사에서 실패/error/skip을 확인하고 입력 canonical 불변·원 객체 무참조를 검증해 소유 파일만 정상 커밋한다.

### Task 2: 원 단일 행동과 공개 decoder의 근거 대조

**Files:** 신규 core/test. **Consumes:** 현재 host의 원 exact12와 context/prompt/response/report/events/before/after/receipt. **Uses:** decode_operator_response(response: bytes, prompt: dict) 공개 함수만 직접 재사용한다. **Produces:** spec의 effect/command/checks와 실제 refs다.

- [ ] **Step 1: RED 작성.** test_same_run_binding_and_causal_after, test_normal_pending_changed_is_only_command_pending, test_read_unchanged_is_not_failure, test_known_rejection_preserves_first_error, test_valid_completed_stop_has_no_task_score를 작성한다. 같은 IDs/hash/원 wire와 허용 DUT/sensor/advance1/stop, actual1/no retry, pending/거절/stop 별 분리 결과를 assert한다.
- [ ] **Step 2: 모순·누락 RED 작성.** test_cross_run_or_wrong_request_is_contradictory, test_extra_intent_or_retry_is_not_repaired, test_unresolved_prefix_stays_insufficient, test_decoder_failure_does_not_upgrade_host, test_cleanup_secondary_cannot_replace_first_error를 추가한다. 이벤트 ID 접두 대신 sequence/고유성/참조 결합을 검사한다.
- [ ] **Step 3: RED 보존 후 최소 구현.** 설계 §5/9의 고정 형상과 spec §5 순서대로 대조한다. 원 wire 수용이 있는 경우에만 genuine decoder로 재대조한다. after가 빠지면 fresh trial을 만들거나 이전 관측을 복사해 채우지 않는다. observed actual time·runtime 진위를 hash로 증명하지 않는다.
- [ ] **Step 4: GREEN.** 입력 순서·참조가 일관된 event ID 전단사 변경은 같은 평가를 유지하고 불일치 변경은 contradiction인지 확인한다. 원 report의 false/not_assessed·host task evaluator0와 score null·producer receipt18을 보존한다.
- [ ] **Step 5: 정상 커밋.** 신규3 범위를 유지하고 기존 host와 public evaluator 파일이 불변임을 확인한다.

### Task 3: 기존 API 호환 경계·자원·사용법과 제출

**Files:** 신규 core/test/usage. **Consumes:** Task1/2 API. **Produces:** bounded exact14 및 용도·공백을 설명하는 usage.

- [ ] **Step 1: RED 작성.** test_meter_declaration_is_not_fabricated, test_sensor_trial_is_not_reconstructed, test_no_task_evaluator_or_runtime_IO, test_input_mutation_and_control_identity를 작성한다. 기존 두 evaluator/runtime/factory/I/O/clock/Store/모델을 호출하면 실패하는 guard, 입력 불변·active control 동일 객체·고정 오류 context/cause None을 확인한다.
- [ ] **Step 2: 자료 결합 검증.** 총괄이 승인한 정확 현재 host 버전의 새 genuine full64+fake D2 한 건 결과를 test caller가 자기 공간에서 준비한다. 함수에는 복사한 native evidence만 제공한다. 정상·거절·prefix packet을 새로 만들며 독립 검증 자료나 기존 검증 증거를 fixture로 읽지 않는다. 준비 runtime과 평가 API의 실행 분모를 분리한다.
- [ ] **Step 3: 최소 구현·GREEN.** task evaluator 호출0·task 미평가, 실제 권한/보관/시간/모델/물리 verification false, data cap과 detached 반환을 확인한다. 입력을 재작성하거나 stale/누락을 수선하지 않는다.
- [ ] **Step 4: 관련 회귀·문서 검사.** 새로운 평가 검사와 변경 관련 공개 decoder/기존 assessment/원 host 회귀를 실행한다. source 불변·UTF8·새 usage link와 python scripts/check_artifacts.py를 확인한다. 실제 모델·인증·budget·장비는 실행하지 않는다.
- [ ] **Step 5: 제출.** 신규3만 정상 commit/push/remote exact/clean으로 부모·raw pins·원 RED/실패·최신 PASS 분모·bounded proof를 총괄에게만 전달한다. 독립 리뷰의 필수 수정을 우선한다. 실제 과업 평가·전체복구·폐루프 완료로 이름을 바꾸지 않는다.


## 검증 범위와 구현 진입

설계 §4/7/8/9는 Task1, §5/6은 Task2, §2의 공개 API 공백과 bound는 Task3로 연결된다. Review Focus 다섯 개를 named test에 배정했다. 현재 문서는 구현 전 계획이며 공통 계약 게시·정확 base·소유·독립 검증 조건·별도 CORE-GO를 고정하기 전 어떤 제품·RED·test runtime 단계도 시작하지 않는다.

부모 [단일 행동 계획](2026-10-25-codex-virtual-one-action.md)과 [기존 meter 평가 계획](2026-10-25-virtual-fleet-meter-recovery-assessment.md)의 공개 경계를 유지한다.
