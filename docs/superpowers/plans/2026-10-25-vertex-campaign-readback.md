# Vertex Connection Campaign Readback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 사용자 배정에 따라 native 실행하며 하위 에이전트는 생성하지 않는다.

**Goal:** 선택한 합성 연결 기록의 원 상태·row replay·출처·0/null을 보존하며 예약/exchange 중복을 제거하는 읽기 전용 비교 reader를 만든다.

**Architecture:** 단일 순수 함수가 호스트의 선택 manifest와 bytes map만 받아 분리된 결과를 반환한다. 기존 batch8/row15/receipt18을 사용하고 replay도 execution_mode=replay인 같은 row15로 외부 manifest에서 연결한다. basis=provided_records_only와 authorization/underlying 검증 false를 유지하며 기존 실행기·원장·DTO는 수정하지 않는다.

**Tech Stack:** Python 표준 라이브러리, unittest, 기존 공개 합성 fixture 패턴. 새 외부 의존성·DB·서버·UI 없음.

**Spec:** [Vertex 연결 캠페인 읽기 전용 비교 설계](../specs/2026-10-25-vertex-campaign-readback-design.md).

## Global Constraints

- 이 reader의 제품 구현·RED·실제 모델 호출은 미실행이다. 공통 수용·정확 게시 base·새 독립 검증 봉인·명시 CORE-GO 이후 실행한다.
- 생성 후보는 `labflow/vertex_campaign_readback.py`, `tests/test_vertex_campaign_readback.py`, `docs/fcc/vertex_campaign_readback_usage.md` 정확 3개다.
- 공개 함수는 build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict 하나다.
- 입력 한도는 source 32개, 파일당 1,048,576 bytes, 전체 8,388,608 bytes다. strict UTF-8/native 자료형과 raw SHA-256을 검사한다.
- 기존 batch8/row15/receipt18·실행 API는 유지한다. 새 재해석 DTO·wrapper·별도 권한 체계·DB·클라우드 수집은 추가하지 않는다.
- 원 unknown과 제공된 replay 해석을 함께 남긴다. 원본·원장 변경·완료된 LOW 재실행·예약 환불/reset은 없다.
- 같은 예약/exchange를 중복 집계하거나 row의 누적 budget 스냅샷을 더하지 않는다. 잔액/remaining은 null이다.
- basis=provided_records_only, root_authorization_verified=false, underlying_artifacts_verified=false를 고정한다. 의미 평가는 not_assessed/score null이다.
- 사용량·비용·generation의 명시 0과 null을 구별하고 불명 전체 합계를 0으로 만들지 않는다. 출처를 구별한다.
- 실제 ADC·원장·원 응답을 읽지 않고 자체 합성 자료를 쓴다. 문서·shape·기능·실제 모델·현장 검증은 구별한다.

## Review Focus

1. 동일 ID의 사본 일부가 변조되거나 origin이 다른 경우, 좋은 사본만 골라 unknown을 숨기지 않는다. Task 1의 사본/출처 검사.
2. 그럴듯한 모델명의 standalone receipt나 다른 예약의 exchange를 잘못 붙이지 않는다. Task 1의 식별 연결 검사.
3. 여러 selected1 batch의 not_selected가 앞선 성공을 덮거나 별도 시도가 사라지지 않는다. Task 1의 coverage/복수 시도 검사.
4. 제공된 replay가 원 unknown을 지우거나 권한/회계 반영으로 승격되지 않는다. Task 1의 row replay/assurance 검사.
5. 누적 예산·일부 null 사용량·known0 실패가 가짜 잔액·비용으로 바뀌지 않는다. Task 1의 집계 검사.

---

### Task 0: 공통 수용과 구현 시작 조건 확인

**Files:** 이 spec/plan. 제품 파일은 생성하지 않는다.

**Interfaces:**
- Consumes: 공통 수용된 읽기 전용 설계와 기존 [비교 core](../../../labflow/model_comparison.py)/[사용법](../../fcc/model_comparison_usage.md), 정확 게시 base·새 독립 검증 봉인·명시 CORE-GO.
- Produces: 신규3 소유와 검증 범위가 고정된 구현 시작 기록. 별도 재해석 DTO·신뢰 pin·허가 체계를 선행조건으로 만들지 않는다.

- [ ] **Step 1: 필수 검수 지적을 우선 반영하고 공개 설계와 계획의 의미 일치를 확인한다.** 기존 동결 원본/실패/검증 자료는 보존한다.
- [ ] **Step 2: 정확 게시 base와 신규3 소유·명시 CORE-GO·새 독립 검증 봉인을 확인한다.** 기존 후보를 변경하지 않는 별도 branch/clone에서 구현한다. 파일 이름과 공개 단일 함수가 설계와 같아야 한다.

### Task 1: 순수 reader·자체 합성 검사·사용법

**Files:**
- Create: `labflow/vertex_campaign_readback.py`
- Test/Create: `tests/test_vertex_campaign_readback.py`
- Create: `docs/fcc/vertex_campaign_readback_usage.md`

**Interfaces:**
- Consumes: [입력 형상표](../specs/2026-10-25-vertex-campaign-readback-design.md#입력-형상)의 manifest7/pair6/axes2/source6와 기존 row replay link11, immutable bytes map, batch8/row15/receipt18. 원 source raw/C1 pin과 동일 예약/exchange/input/settings는 외부 link로 묶는다.
- Produces: build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict, [결과 형상표](../specs/2026-10-25-vertex-campaign-readback-design.md#결과-형상)의 report9/cell7/중첩 assurance3, 고정 invalid_input 오류/issue. 파일·네트워크·runner·원장 callback은 받지 않는다.

- [ ] **Step 1: 새 자체 합성 fixture와 아래 요구사항 검사를 작성한다.** [기존 비교 테스트](../../../tests/test_model_comparison.py)의 패턴을 참조해 genuine builder/runner에 합성 transport를 결합한 기록을 만든다. 출처는 mock으로 명시하고 shape 예시를 실제 전송·decoder·모델 실행 증거로 사용하지 않는다.

| 검사 이름 | 고정할 동작 |
|---|---|
| `test_duplicate_batch_row_receipt_is_one_attempt` | batch embedded row·독립 row·receipt 사본은 같은 시도/예약/exchange로 연결한다. |
| `test_missing_tampered_partial_and_identity_conflict_stay_unknown` | 누락·변조·부분·동일ID 다른 값은 unknown이며 원 이력을 남긴다. |
| `test_cross_reservation_exchange_and_orphan_receipt_are_unknown` | 다른 예약의 exchange와 연결되지 않은 receipt를 추정 병합하지 않는다. |
| `test_not_selected_never_overwrites_attempt_in_any_order` | 입력 순서에 관계없이 not_selected는 coverage이며 이전 시도를 덮지 않는다. |
| `test_distinct_attempts_in_one_cell_keep_all_history` | 같은 축의 독립 시도를 latest success로 축약하지 않는다. |
| `test_exact_row15_replay_keeps_original_unknown_without_new_call` | 원 receipt가 없는 경우의 명시 receipt 연결을 포함해 원 unknown과 제공 replay를 같이 보존한다. 새 호출/예약과 권한·원본 검증을 만들지 않는다. |
| `test_wrong_partial_unlinked_or_conflicting_row_replay_cannot_promote` | raw/C1 pin·축·origin·input/settings·예약/exchange·mode 불일치, link/필요 receipt 없음, 상충 replay를 unknown으로 둔다. |
| `test_cumulative_budget_snapshots_are_never_summed_or_refunded` | 관측 예약 참조/설정 cap 부분합과 누적 budget 스냅샷을 구별하고 차감·잔액 추정을 하지 않는다. |
| `test_generation_usage_and_cost_preserve_zero_and_null` | generation과 사용량 각 필드의 0/null·부분합·불명을 구별하고 비용 null을 유지한다. |
| `test_pair_axis_version_types_and_input_caps_fail_closed` | 다른 pair/축/버전·잘못된 native 자료형·JSON·선택집합·상한 경계를 거절한다. |
| `test_report_is_detached_deterministic_and_contains_no_raw_content` | 입력/결과 변이가 분리되고 순서 교체에도 결정적이며 민감 원문을 투영하지 않는다. |
| `test_reader_performs_no_io_execution_or_ledger_mutation` | 파일/network/subprocess/runner/시간/랜덤 접근을 차단한 상태에서 순수 비교만 수행한다. |

- [ ] **Step 2: 테스트를 실행하고 미구현 함수 때문에 실패하는 RED를 보존한다.** fixture 생성 실패와 기능 실패를 구별한다.

Run: `python -B -X utf8 -m unittest discover -s tests -p test_vertex_campaign_readback.py -v`

- [ ] **Step 3: 단일 함수와 필요한 private 순수 검증을 구현한다.** 선택 source를 검사하고 원/replay row15를 명시 연결한 뒤 같은 예약/exchange를 dedup한다. not_selected·origin 충돌·원 unknown을 보존하고 출처별 부분합/null을 만든다. 기존 runner의 IO helper나 새 재해석 DTO·wrapper를 가져오지 않는다.
- [ ] **Step 4: 같은 bounded 테스트를 실행해 GREEN을 확인한다.** 원 RED/실패 주입 기대를 보존한다. 새 변경·실패·미해결 우려 없이 검사를 불필요하게 반복하지 않는다.
- [ ] **Step 5: 사용법을 작성하고 새 모듈 정적 검사와 문서 검사를 수행한다.** 단일 API·제공 기록 한계·명시 연결·0/null·누적 예산 합산 금지·assurance false·실제 검증 미실행을 명시한다.

Run: `python -B -X utf8 scripts/check_artifacts.py`

새 문서의 UTF-8·비어 있지 않음·깨진 문자·로컬 링크도 별도로 확인한다. [문서 검사](../../../scripts/check_artifacts.py)는 reader 기능·실제 모델·현장 검증을 입증하지 않는다.

- [ ] **Step 6: 신규3 diff와 기존 tracked/source raw·LF·mtime 불변을 대조한다.** 정확 후보 pin·RED/GREEN·정적/문서 검사·검증 범위·미실행을 총괄에 제출한다. 지정된 파일만 정상 commit/push하고 다른 소유 파일을 stage하지 않는다.

### Task 2: 독립 검수와 인수

**Files:** Task 1의 신규3과 동결 검증 자료. 기존 원본/원장은 변경하지 않는다.

**Interfaces:**
- Consumes: 정확 후보·원격 pin·합성 검증 자료·보호 대조·총괄 독립 검수 결과.
- Produces: 인수한 기능 범위와 미실행 범위. 기존 모듈/과거 검사 수와 새 reader 검사 수를 합산하지 않는다.

- [ ] **Step 1: 필수 검수 지적을 신규3 범위에서 수정하고 원 실패·기대를 보존한다.** 수정 범위에 맞는 bounded 재검증을 수행한다.
- [ ] **Step 2: 정확 후보와 새 검증 결과를 재제출한다.** 제공 기록 비교와 실제 모델·원본·권한 검증을 구별한다. 원 unknown·0/null·중복 제거·무부작용 요구가 유지돼야 한다.
- [ ] **Step 3: 인수 범위와 남은 작업을 한국어로 보고한다.** 실제 기록 수집·UI 연결·모델 호출·현장 검증은 이 reader 구현의 완료에 포함하지 않는다.
