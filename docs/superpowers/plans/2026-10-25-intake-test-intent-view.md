# 제공 규정·방법 대조 결과의 화면 연결 구현 계획

> 독립 정적 Yes 뒤 공개한 계획이다. 총괄이 공통 kwarg/선택 metadata·소유7을 승인하며 정확 게시 base·전용 branch 실제 배정 뒤 개발4가 직접 구현한다. 하위 agent0, 현재 이 연결의 제품/fixture/API/HTTP/DOM 실행0이다.

**Goal:** 실제 공급된 승인 review_only 결과를 기존 접수 화면에 읽기 전용으로 연결한다.

**Architecture:** 같은 host에 명시 원입력 tuple0/1을 받아 기존 순수 API1회·원 결과 캐시를 만든다. 기존 snapshot과 full projection hash가 일치할 때 기존 GET의 선택 metadata로 원 review9키를 전달한다. main은 같은 off-DOM publish에서 값/사유/질문과 false12를 표시한다.

**Tech Stack:** 기존 Python 순수 API·store.canonical/SQLite readonly snapshot·기존 main JS/Node·기존 브라우저 검사·DESIGN 토큰. 설치/새 parser/provider0.

**Spec:** [공개 설계](../specs/2026-10-25-intake-test-intent-view-design.md). source와 현재 없는 접점은 총괄이 동결한 private source-map에 구별했다.

## Global Constraints

- 공개 설계의 승인된 소유7만 구현한다. 정확 게시base·실제 배정 전 제품 변경0이며 공개 계약 자체는 runtime 실행 증거가 아니다. kwarg/응답 키는 구현할 접점으로 구별한다.
- 부모 `build_intake_test_intent_review(intake, proposal, sources)`·입력4/원 proposal/source 형상·원9키/enum/limits·verification14 중 false12를 변경하지 않는다. 원 context/analysis/full projection/관측 없이 UI record/최소034에서 복원0.
- 새 endpoint/schema/parser/provider/모델·파일loader·고객원문·동적 source 공급0. 유일 common 변경 제안은 기존 GET의 선택metadata1이며 별도 승인 gate다. 불허 시 다른 필드로 우회0.
- source/quote·scope·기간·판본 unknown/이유/충돌/질문 유지. 규정/방법/query/case_ids/준비·등록·실행 권한 자동승격0. 057/047·C1/C2/core/Store/ASSETS/CSP·shared docs 보호.
- (), 미결합이면 새key/UI0. 기존동작/원문/실패기록 보존. API설정1 외 GET의추가source/worker/034/API재호출0. metadata SQL은 기존snapshot의 실제동작이며0으로 주장하지 않는다.

## Review Focus

1. 같은 ID/revision의 답변 변경 → U02 full projection canonical hash 비교로 이전 결과를 숨김.
2. 원 analysis와 projection.submitted 불일치 → U03 현재 fact의 다른 quote로 index를 해석하지 않음.
3. literal_linked/model_proposed/검사수행을 승인으로 오독 → U03 12false·선언/실제호출0·적용성미판정.
4. 입력/DTO 예산 실패를 빈 성공으로 처리 → U01/U04 bind전원오류·조회적용거절·원입력불변.
5. async refresh·선택/종료·C2 event 중 불완전 새state publish → U05 기존 epoch/offDOM/guard 유지, 추가source/setter0.

## Task 1 — 실제 제공 결과 한 묶음의 host→main 연결

**Files:** Modify `labflow/ui_server.py`, `frontend/model.mjs`, `frontend/model.test.mjs`, `frontend/app.js`, `frontend/intake_references/browser_check.cjs`; create `tests/test_intake_test_intent_view.py`, `docs/fcc/intake_test_intent_view_usage.md`. 정확 게시base·전용 branch 실제 배정 뒤의 승인 소유 범위다.

**Interfaces:** 기존 `build_intake_test_intent_review(intake,proposal,sources)->dict`, `store.canonical(value)->str`, `IntakeReadModel.snapshot(intake_id=None)`를 재사용한다. 제안 host kwarg는 `intake_test_intent_inputs=()` 또는 `((supplied_intake,supplied_proposal,supplied_sources),)`만이다. 기존 GET 성공 envelope의 선택 `intake_test_intent_reviews`는 승인 review9키 배열 최대1이며 미구성/미결합은 키생략이다. 내부 app helper는 `renderTestIntentReview(record,review)`이고 공개 신규component/controller/route0이다.

- [ ] **Step 1: base/공통 gate와 실제 source를 다시 대조한다.** 승인된 정확base/소유7·kwarg/선택key를 확인하고 057 correction/옛056 및 원 refs·dirty·stash/실패를 pin한다. 현재 source-map과 차이는 root에 반환하며 임의 적용0이다.
- [ ] **Step 2: U01/U02 backend RED를 얻는다.** 새 test에서 실제 parent API를 쓴 명시 원입력으로 configure1/GET후call추가0·()결과미주입·오류전파·same-revision full hash 변화·다른ID/버전/단건/fixture-runs를 단언한다. 기존 코드의 미지원 kwarg/미제공metadata가 RED여야 하며 이번 문서 작성에서는 실행하지 않는다.
- [ ] **Step 3: host의 명시 조립만 구현한다.** ()에서 import/call0. 하나의 native triple만 bind전에 parent1회로 검증·detach하고 canonical result bytes를 캐시한다. model.snapshot 원record의 ID/revision/full analysis hash와 맞을 때만 선택field를 추가한다. API3고정 오류를 빈결과로 수리하지 않고 raw예외/원문 logging0이다. store.canonical 재사용이며 parentprivate helper를 호출하지 않는다.
- [ ] **Step 4: U03~U05 JS/DOM RED를 얻는다.** 기존 main wire checker에 승인 DTO와 원필드/미결합/invalid 응답을 공급하고 실제 표시·본문주입/다른인용0·질문보존·선택/late/guard/destroy·390/1440을 단언한다. wire 선언과 genuine API/HTTP 검증을 구분한다. 새 JSON parser/부모 알고리즘 복제0이다.
- [ ] **Step 5: 기존 model/app의 작은 읽기 표시를 구현한다.** validateSnapshot의 기존 primitive 검사에 승인DTO9키/상태/14검증/한도를 추가하고 잘못된 추가field는 invalid_snapshot으로 전체조회거절한다. 성공 snapshot state에만 reviews를 넣어 prepareView/buildDetail에서 같은ID/revision 제공결과 구역1을 textContent로 조립한다. missing/proposed/conflicting/literal_linked와 원 literal/origin/reasons/period/locator·기존질문수·false12를 표시한다. ()/no-match구역0·인용문 복원/새동작0이다.
- [ ] **Step 6: U06 genuine end-to-end를 별도 검증한다.** 실제 기존 public jobs/034에서 이미 공급한 원 context/submission/full projection/capture와 명시 proposal/sources를 재사용한다. 테스트 준비와 P1 순수API1/metadata조회 구간을 분리해 원입력/DB·blob 불변·추가I/O0/기존SQL존재·실제 HTTP/DOM·부모false12/부분query불변·정상host/Store/port회수를 관측한다. 선언capture/임의 성공DTO를 genuine으로 세지 않는다. 제품에 test import/hook/envadapter0이다.
- [ ] **Step 7: 실제 사용과 정확 소유를 게시한다.** usage에 명시 공급·기본미구성·locator만전달·이번모델0/이전분석미검증·현재성/권한false를 적는다. 변경에 맞는 전용 Python·model Node·기존 main/C2 관련 회귀만 실행하고 전체/Node/browser 반복은 root 지정·실제 영향에 따른다. UTF8/링크·check_artifacts·소유외raw/ref 보존·정확diff/정상commitpush/remoteexact/필요cold→root독립검토를 분리한다.

## 미래 수용 — 현재 전부 미실행

| ID | 통과해야 할 실제 결과 |
|---|---|
| U01 | () API0/응답동일/구역0, 명시native triple1만 API1회/bind전 처리, None/type/다수/부모error3 거절. 입력불변·외부I/O0·기존053 scope/None변경0. |
| U02 | ID/revision와 full projection 모두일치만 전송. 같은revision 답변·질문변경·다른ID/revision·null analysis는 no-match키생략. 최소/원result hash대체·현재성true0. |
| U03 | 부모field4상태·원literal/origin/reasons/period·locator/null/빈값·원질문 보존, 인용수행2와false12 구분. analysis/submitted mismatch에서도다른quote자동연결0·query/준비/등록승격0·모델호출0. |
| U04 | 잘못된9키/true권한/unsafe number·한도/상태·refs/누락 DTO는 invalid_snapshot/마지막조회유지, 성공으로truncate0·raw오류/HTML주입/storage/download0. |
| U05 | 기존 성공 offDOM 원자교체·선택/검색/late/refresh 실패/pagehide/BFcache/destroy/C2guard 유지. 자동focus/hash변경/추가setter·source/current/prepare/append0, 390/1440 overflow0·키보드읽기순서. |
| U06 | 실제pureAPI→동일host기존GET→main DOM, P0준비/제공값·P1메타구간 분리·원입력/DB불변·추가source API/I/O0·기존SQL계수, capability/부분query/기존부모불변과 실제정리/자기port회수. wire/mock·genuine·실제AI/현장 분모 구별. |

자체검토: UI에없는 quote를 결과에있는 것처럼 만들지 않고, source/proposal producer 공백을 자동 로더로 메우지 않았다. 기능범위는제공된대조결과의조건부표시한단위다. 공통 wire 확장/host소유는 이 공개 계약의 범위이며 새사용자원문/수집요청0이다. 정확 게시base·전용 branch 실제 배정 뒤 구현하고 독립 제품리뷰·총괄 회귀/통합을 이어간다.
