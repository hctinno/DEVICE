# 등록 합성 의뢰의 preclaim 컨텍스트 구현 계획

현재는 설계·계획 단계다. 계약 검토와 구현 기준·별도 착수 승인 후 아래 작업을 직접 수행한다. 실모델·운영 Store·현장 운전 권한은 포함하지 않는다.

**Goal:** root 등록 합성 선택1을 동일 working Store의 실제 queued preclaim full8과 결합하고, 기존 once의 첫 fresh canonical 비교에 그대로 넘긴다.

**Architecture:** 기존 intake_jobs에 public 함수1을 추가하고 기존 public8 조립을 private `_public_context`로 공유한다. SELECT snapshot→genuine 준비→SELECT 재확인/genuine verify→genuine builder의 detached8 순서이며 claim/업무 DML0이다. retained context blob/metadata 쓰기와 업무 상태 불변은 구별한다.

**Tech Stack:** 기존 Python/Store/intake_jobs/intake_documents/model boundary만 재사용한다.

**Spec:** [공통 설계와 기계 판독 규범](../specs/2026-10-25-intake-preclaim-context-design.md).

## Global Constraints

- 기존 구현·원 실패 기록·근거를 보존한다. 검수에서 확인된 필수 수정이 우선이다.
- G1/G2/G4/G5와 실제 issuer/account budget/launch/종료 API는 OPEN이다. noauth main 변경0·추가 한도/seed/reset/refund0이다.
- 등록 선택6은 source_id/intake_id/revision/job_id/revision_fingerprint/files다. 새 synthetic/approved bool·old context ID 치환·arbitrary public wire 입력을 추가하지 않는다.
- claim/UUID/token 발급·lease/attempt/job/event 업무 DML·새 Store/open/close·scan·completed snapshot 사용0이다.
- schema1만, stored PDF는 준비 전 거절한다. 실행 한도는 기존 context 및 once prompt256KiB를 따른다.
- 현재 model/CLI/auth/ADC/livebudget·고객/운영 Store·원자료·망/현장0이다. 향후 검증도 authored synthetic/disposable/fake D2만 사용한다.

## Review Focus

1. full8 입력을 먼저 요구하거나 preclaim을 호출하는 순환이 없는지: source 선택6과 실제 queued 상태에서 시작한다.
2. preparation의 retain을 전체 read-only로 오인하는지: blob metadata 쓰기와 업무 row 불변을 분리한다.
3. queued의 오래된 token/lease를 지우거나 running 만료를 reap하는지: 원값 보존·반환 금지, running 거절이다.
4. 준비 중 다른 worker/revision/원 blob이 바뀔 때 성공으로 보완하는지: 재확인/verify 실패와 retained 실패 보존이다.
5. 공유 helper 추출이 기존 claim의 계약·instructions·transaction을 바꾸는지: 기존 테스트와 별도 canonical oracle로 검증한다.

## Task 1: 정확 소유/API와 독립 기준 고정

**Files:** 실제 구현 대상은 다음 기존2개+신규1개다.

- Modify `labflow/intake_jobs.py`: `prepare_registered_synthetic_context`와 `_public_context` 추가; claim의 public8 dict 조립만 공유.
- Modify `tests/test_intake_jobs.py`: 기존 body 보존, G3 검사 추가.
- Create `docs/fcc/intake_preclaim_context_usage.md`.

**Interfaces:** `prepare_registered_synthetic_context(store, registered_intake, *, producer_name) -> dict` / registered selection6 / 반환 public8 / ValueError fixed prefix7이다.

- [ ] API·오류·source6·부작용/불변·기존 코드 수정 범위의 공통 계약 검토를 마치고 구현 기준 commit·별도 착수 승인을 확정한다.
- [ ] 별도 clone/작업 branch와 기존 source baseline을 고정한다. 확정한 기준을 임의 rebase/merge하지 않는다.

## Task 2: 기존 jobs의 G3 RED→최소 helper

**Consumes:** `_revision`, `_prepare`, `_verify`, `_analysis_contract`, `prepare_analysis_documents`, `verify_analysis_documents`, genuine builder/schema helper, borrowed Store.

**Produces:** 새 public API1과 공유 private `_public_context(job, revision, prepared)`; 다른 parent API/DTO는 그대로다.

- [ ] `test_registered_source6_prepares_actual_public8_without_claim` RED: register/scan으로만 만든 queued attempt0 fixture에서 source6를 주면 exact8, genuine prepared context/contract, input alias 분리다. UUID/claim/once/complete/fail 호출0을 spy로 검증한다.
- [ ] `test_only_context_retain_changes_and_business_rows_unchanged` RED: job/intake/revisions/answers/questions/responses/events를 전후 대조한다. blobs/context manifest의 허용된 retain만 따로 센다. 전체 DB bytes 불변을 요구하지 않는다.
- [ ] `test_registered_selection_rejects_other_job_revision_source_and_files` RED: 다른 ID/현재 revision·fingerprint·files/순서·범위는 고정 실패이며 다른 queued job fallback0이다.
- [ ] `test_non_synthetic_pdf_running_and_attempt_limit_reject_before_prepare` RED: source/revision 비합성, stored PDF, running(만료 포함), attempt3, upload_incomplete, 대상 부재에서 원 bytes/prepare/claim0이다.
- [ ] `test_genuine_queued_failure_token_and_lease_are_preserved_and_private` RED: 이미 실패한 queued fixture의 token/lease/worker/attempt/result/error 원값 보존, 반환/오류/로그/prompt 비노출을 확인한다. 이 fixture 준비의 과거 claim과 helper claim0을 구별한다.
- [ ] `test_prepare_race_and_retained_tamper_do_not_return_success` RED: genuine prepare 뒤 test-only worker/revision 변화, 원 blob/manifest/profile 불일치를 주입한다. state_changed/preparation_failed·원 상태/retained evidence 보존·재조회/복구0이다.
- [ ] `test_controls_and_Store_lifetime_are_preserved` RED: 관측 control 동일 객체·새 속성0, closed Store 고정 code, helper borrowed close0·연결 회수를 확인한다.
- [ ] Run `python -B -m unittest discover -s tests -p test_intake_jobs.py -v`. 신규 API 부재 RED를 원문 보존한다. 현재는 실행하지 않는다.
- [ ] public8 조립만 공유 helper로 추출한다. 기존 claim의 선택/만료 정리/시각/토큰/SQL/event/한도는 바꾸지 않는다.
- [ ] 새 API에서 입력 snapshot·첫 SELECT·genuine prepare·두 번째 SELECT/genuine verify·shared public8/genuine builder를 구현한다. PDF metadata 거절, scope/type/한도·고정 오류7을 적용한다. 새 schema/registry/receipt/worker를 만들지 않는다.
- [ ] 위 전용 검사를 GREEN으로 만들고 원 RED·실패·수정 근거를 보존한다.

## Task 3: genuine fresh 비교와 once 유계 통합

**Files:** 동일 소유3만. 현재까지 모두 미실행이다.

- [ ] `test_separate_claim_oracle_matches_prepared_public8`을 fresh fixture에서 실행한다. G3 helper 뒤 최초 genuine claim의 public8 C1이 같고 attempt0→1이다. 이 oracle claim1을 helper claim0과 분리해 기록한다.
- [ ] `test_fresh_once_uses_preclaim_output_without_prior_claim`을 별도 fresh fixture에서 실행한다. G3 출력8→기존 once 첫 claim1→fake concrete D21→genuine strict/complete, DB attempt1을 확인한다. 앞 oracle fixture를 재사용하거나 now/lease를 조작하지 않는다.
- [ ] `test_once_rechecks_public_context_revision_and_claim_eligibility`를 별도 합성 fixture군에서 실행한다. 반환 후 fresh public8·prompt/current revision binding 불일치는 기존 scope 검사로 producer 전에 거절하고, 기존 eligibility로 claim이 없으면 idle·producer0임을 확인한다. 준비 중 whole-job 재SELECT와 반환 후 이 범위를 구별한다. private job 전체의 동결/과거 변화 검출은 기대하지 않는다. 별도 경계 fixture에서는 genuine claim→fail_job 뒤 attempt1 queued·동일 public8이면 다음 once가 attempt2로 비교를 통과할 수 있음을 fake D2로 확인한다. 이 경계 fixture의 선행 claim/fail은 앞의 fresh attempt0→1 통합과 별도 집계하며 clock/lease 조작을 하지 않는다. G3가 lease·예약·권위를 발급했다고 주장하지 않는다.
- [ ] 기존 test_intake_jobs의 모든 body/결과와 once/boundary/documents/active intake/worker/Store 관련 회귀를 수행한다. source 밖 raw/native/GitLF·private값 비노출·close 분모·UTF8/링크/diff를 검증한다.
- [ ] 신규 usage에 exact API6→8·schema1·retain 부작용·업무 불변·고정 오류·race/미실행 actual을 기록한다. `python scripts/check_artifacts.py`와 자체 링크 검사를 수행한다.
- [ ] 정상 commit/push/exactremote/clean과 parent/정확 소유3 raw·GitLF·원 RED/실패·새 통과/분모를 총괄에 제출한다. 필수 독립 수정 후 총괄 회귀/통합으로 잇는다.

## Task 4: G3 완료와 실제 실행 권위 구별

- [ ] 독립 수용은 등록 source6↔same Store 실제 preclaim8↔once fresh C1의 결합까지만이다. API 준비/합성 통합을 모델/계정 승인으로 이름 바꾸지 않는다.
- [ ] G1/G2/G4/G5·실제 API GO는 별도 OPEN으로 인계한다. noauth main과 기존 누적 한도는 그대로다.

Self-review: native source6 입력으로 full8 사전 요구의 순환을 없앴다. genuine 준비/검증/contract/instructions를 재사용하며 parent 변경은 public8 조립 공유뿐이다. 기존 fail_job이 queued에 token/lease를 남기는 실제 동작을 반영했다. 준비된 metadata 쓰기를 숨기거나 current snapshot을 lease로 승격하지 않는다.
