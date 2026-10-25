# Codex 등록 합성 접수 1회 host/CLI 구현 계획

> **For agentic workers:** 사용자 지침에 따라 담당 세션에서 직접 실행(`superpowers:executing-plans`)한다. 하위 에이전트를 생성하지 않는다. 공통 게시·새 독립 검증 기준·정확 base·별도 CORE-GO 뒤에만 아래 noauth·유계 모의 구현을 시작한다. 실제 API GO는 별도다.

**Goal:** registered synthetic intake1/model1의 명시 입력과 noauth 경계를 구현하고, 기존 once 연결을 유계 합성 모의 검사로 검증한다. 실제 issuer가 OPEN인 동안 production 모델0을 유지한다.

**Architecture:** 공개 함수 `main(argv=None, *, authorization=None) -> int` 하나와 별도 CLI 신규3이다. public argv는 scenario/model 선택만 받고 native binding 형상/hash를 실제 권위로 승격하지 않는다. open_existing/finally.close·단일 예약 consumption·기존 once/result10 조립은 fake concrete D2/disposable Store에서 검증하며 실제 root issuer 연결은 별도 GO 뒤에만 활성화한다.

**Tech Stack:** 기존 Python 표준 라이브러리, 기존 Store·genuine builder·once. 의존성 설치0.

**Spec:** [고정 설계](../specs/2026-10-25-codex-intake-once-cli-design.md). 이 계획의 게시 자체는 제품 구현·DB·CLI·모델 실행 증거가 아니다.

## Global Constraints

- 기존 branch·미커밋·원 RED·proof를 보존한다. 기존 clone을 임의 merge/rebase/reset하지 않는다. 제품 base·전용 clone/branch·new3 소유는 총괄이 별도로 지정한다.
- 구현 GO와 실제 API GO를 분리한다. 실제 issuer·원자 선예약·trusted launch·등록↔working context 결합은 OPEN이며 production 모델0이다.
- 기존 누적 승인·한도·무료 크레딧 전용 정책을 유지한다. 새 framework/registry/DB schema/상시 worker/fixtureworker 수정·budget seed/reset/refund·자동 auth/refresh/loop0이다.
- 공개 argv는 scenario/model 각1, stdin/context/path/auth JSON 업로드0이다. 현재 issuer 부재 시 형상이 맞는 native binding도 실제 승인으로 취급하지 않는다.
- once/D2/Store는 수정하지 않는다. installed CLI·실모델·실budget·ADC/auth·망·원자료는 별도 실제 위임 전0이다.

## Review Focus

1. public JSON·ref/approved bool·native 형상/hash를 root issuer 인증으로 오인하면 안 된다: issuer 부재와 noauth의 Store/marker/once/auth0·unknown 기록을 고정한다.
2. 새 model/evidence/process 또는 경합으로 같은 선예약을 재사용하면 안 된다: 유계 모의 검사에서 결정적 marker의 배타 생성과 기존/partial 보존을 검증한다.
3. 등록 wire와 working job/context가 다를 때 ID 치환·재등록·다른 job 실행을 하면 안 된다: 전체 root scope와 genuine fresh context를 대조한다.
4. marker/complete 후 오류를 미실행으로 단정하면 안 된다: null 시도수·원 result10·unknown/첫 오류와 no-refund를 보존한다.
5. control·Store close·stdout 실패가 토큰/원문을 누출하거나 모델 재실행을 유발하면 안 된다: 관측 control 동일성·close1·frame1·모델≤1을 검증한다.

## Task 1: noauth·유계 모의 구현의 배정 경계 고정

**Files:** 제품 변경 없음. 공개 spec/plan을 기준으로 총괄이 정확 base·new3 소유를 지정한다. 실제 누적 장부 owner가 공개 tree에 없으므로 임의 파일명/API를 발명하지 않는다.

**Interfaces:** `main(argv=None, *, authorization=None) -> int`와 spec의 authorization exact5·reservation exact8을 명시 입력 검증 대상으로 사용한다. 형상 통과는 실제 권위가 아니다. 실제 root issuer가 없는 production 입력은 once/Store/marker 전에 중단한다.

- [ ] 총괄이 공개 계약·독립 검증 기준·정확 base·전용 clone/branch·new3 소유·CORE-GO를 고정한다. 현재 작업이 이를 이미 받았다고 가정하지 않는다.
- [ ] root-controlled launch 및 실제 원자 선예약/확정 기록·등록↔working context 결합은 OPEN으로 유지한다. 이 gap을 noauth·유계 모의 구현 GO와 구별한다.
- [ ] fake/authoritative 권위를 구별하는 검증 조건과 실제 모델0을 고정한다. stub/approved bool/새 JSON 장부·production mock mode로 gap을 숨기지 않는다.

## Task 2: 단일 host/CLI 신규3의 RED→최소 구현

**Files:** Create `labflow/codex_intake_once_cli.py`, `tests/test_codex_intake_once_cli.py`, `docs/fcc/codex_intake_once_cli_usage.md`. 기존 일반 CLI·intake_serve 수정 예외0.

**Interfaces:** consumes `Store.open_existing(str)` / `build_analysis_prompt(context, *, producer_name)` / `run_codex_intake_once(store, approved_context, *, worker_id, producer_name, executable, requested_model, evidence_root, authorization_ref, timeout_seconds)`; produces `main(argv=None, *, authorization=None) -> int` 한 공개 함수. 실제 issuer 부재인 production과 전용 검사의 fake 조립을 구별한다.

- [ ] `test_noauth_never_opens_store_consumes_reservation_or_probes_auth` RED: valid scenario/model + authorization=None→exit3, stderr not_run/auth unknown/model0, stdin read/Store open/once/marker/auth0.
- [ ] `test_native_shape_and_hash_cannot_replace_missing_actual_issuer` RED: exact 형상·scope hash를 갖춘 synthetic binding도 실제 issuer 부재인 production에서 Store/marker/once0, not_run/auth unknown이다. native injection을 가짜 실제 승인으로 쓰지 않는다.
- [ ] `test_public_input_cannot_supply_authority_or_document_paths` RED: duplicate/equal/abbreviation/extra/positional·stdin JSON·`--approval`/`--workspace`/`--context`/`--budget` 거절, model default/fallback0. 도움말은 무실행이다.
- [ ] `test_root_binding_requires_registered_scope_and_confirmed_reservation` RED: exact5/중첩3·8·8, native 타입, SHA/ID, UTC 만료, reserved int1/state reserved, selected scenario/model 불일치·변조 scope를 검증한다. 이를 실제 권위/예약 성공으로 세지 않는다.
- [ ] `test_single_reservation_survives_new_evidence_model_and_process` RED: disposable marker의 budget/reservation 경로가 같고 배타 승자만1이다. 기존/partial bytes/ns 보존, 삭제/환불/새 marker fallback0. atomic helper 경합과 fake 호출 합계≤1을 별도 대조한다.
- [ ] `test_registered_and_working_context_must_not_be_rewritten` RED: 등록 provenance와 working public8 hash를 구별하고 old ID 치환/새 Store/scan/사전 claim0이다. 잘못된 fresh claim은 기존 once가 fake D2 호출 전에 막는다.
- [ ] 위 테스트 파일만 실행해 실제 실패를 보존한다. Run: `python -B -m unittest discover -s tests -p test_codex_intake_once_cli.py -v`. Expected: 신규 경계 부재의 RED, 설치 CLI/실모델0.
- [ ] parser·binding snapshot/scope·고정 noauth/issuer 부재 응답과 tokenless consumption·수명 조립을 최소 구현한다. actual issuer를 발명하거나 기본 True 검사를 넣지 않는다. parent budget/collector/cleanup loop를 복제하지 않는다.
- [ ] `test_real_once_with_fake_D2_preserves_call_counts_and_result10`을 통과시킨다: 전용 검사에서 authored disposable existing Store와 명시 synthetic reservation fixture, genuine once/strict/complete, fake concrete D2≤1을 연결한다. result10과 Store open1/close1을 확인한다. production 실제 연결 성공으로 세지 않으며 public mock selector/callback을 추가하지 않는다.
- [ ] `test_partial_marker_expiry_and_after_complete_errors_are_not_retried`를 통과시킨다: 모의 조립의 model0 또는 관측1/null을 구별하며 marker·원 caller evidence 보존, no refund/재claim/완료/모델 재호출이다.
- [ ] `test_first_control_close_and_output_failure_preserve_original_outcome`을 통과시킨다: 관측한 KI/SE/GE/MemoryError 동일 객체, Store close1, SQL/모델 추가 정리0, close/출력 후속 오류가 원 caller errors를 덮지 않음, frame≤1/quiet brokenpipe다.
- [ ] `test_token_lease_document_and_exception_text_never_reach_host_frames`를 통과시킨다. public main stream reconfigure/replace/close0, process wrapper UTF-8/LF·종료0/2/3/4/5와 KI130을 확인한다. 현재 production issuer 부재는 종료3/모델0이다.
- [ ] usage를 최종 signature·noauth·모의 검증/실제 OPEN·예산/marker/수명/unknown에 맞춰 작성한다. 신규 전용 suite GREEN 뒤 해당 new3만 normal commit한다.

## Task 3: 관련 회귀·소유 증거·총괄 인계

**Files:** 신규3만. 정확 허용 증거 위치는 CORE-GO 때 별도로 정하며 기존 proof는 재작성하지 않는다.

- [ ] 최종 base의 once/D2/boundary/jobs/fixtureworker/Store opener/intake_serve 관련 회귀를 fake/disposable 범위에서 실행하고 분모를 각각 기록한다. 과거 owner·독립·총괄 검사를 새 검사로 합산하지 않는다.
- [ ] SQLite/Store/native pin close 분모와 소유 외 source raw/hash/mtime_ns/ctime_ns 불변·compile·diff check를 확인한다. process 검사는 authored fake 실행 파일만 사용한다.
- [ ] `python scripts/check_artifacts.py`와 신규 usage의 UTF-8·marker·local link 검사를 실행한다. 문서 무결성과 기능·실물 적합성 검증을 구별한다.
- [ ] normal commit/push/remote exact와 bounded manifest/원 RED·실패/최종 new3 raw·GitLF pin을 총괄에 제출한다. 독립 리뷰의 필수 수정을 우선 회수한다.
- [ ] noauth·유계 모의 구현의 완료와 실제 issuer gap을 구별해 인계한다. 실제 API/모델 미실행을 명시한다.

## Task 4: 실제 API 연결의 별도 OPEN 조건

**Files:** 이 계획에서 실제 issuer/장부/launcher를 새로 구현하지 않는다. 해당 소유와 변경 범위는 총괄이 별도 공통 계약으로 고정한다.

- [ ] root가 기존 누적 장부의 실제 owner·원자 선예약·확정 record ref/hash·trusted issuer/launch·등록1↔working Store/full public8·고정 consumption root를 실제로 제공한다.
- [ ] root가 이 결합을 독립 검토하고 별도 실제 API GO를 발행한다. native 형상/hash·모의 fixture·정적 Yes·CORE-GO를 그 승인으로 대신하지 않는다.
- [ ] 실제 모델1은 기존 누적 권위가 허용할 때 별도 위임으로만 수행한다. 이 계획/구현 GO 자체로 신규 예산·추가 한도를 발급하지 않는다. 미충족이면 actual 불가·모델0을 유지한다.

Self-review: Review Focus 5종은 Task2의 구체 test에 대응한다. Task1/2/3은 noauth·유계 모의 구현·검증이며, Task4의 실제 권위/선예약/등록 결합과 실제 API GO는 별도 OPEN이다. 신규 framework 없이 기존 수명·once·collector를 재사용한다. 아직 실행하지 않은 체크를 완료로 표시하지 않는다.
