# 057 제공 대조 데모 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 이 문서는 private v2 정적 Yes 뒤 공개한 구현 계약이다. 실제 실행은 총괄의 정확 게시 base·전용 branch·기존3 소유 실제 배정 후 담당이 직접 수행하며 하위 agent를 생성하지 않는다.

**Goal:** 기존057의 명시 `--intent-view` 실행에서 실제 합성 원입력→host→GET→제공 대조 구역을 확인하게 한다.

**Architecture:** 기본057 worker·CLI 출력·C2와 미공급 host를 유지한다. 옵션의 P0만 기존 public claim→concrete synthetic literal provider→complete→proceed→full projection/034를 보존하고 명시 수동 후보/빈 sources를 같은 host tuple1에 전달한다. 화면/API의 기존 검증·결합·수명을 재사용한다.

**Tech Stack:** 기존 Python/stdlib·ReportLab/pypdf·SQLite Store·기존 public jobs/034·기존 ui_server·실제 Chromium/Playwright. 새 의존성0.

**Spec:** [설계](../specs/2026-10-25-intake-test-intent-demo-connection-design.md). 비공개 `source-map.json`의 현재08856f4 관측은 구현 base 확정이 아니다. 기존088 화면과 공통 Store290은 별도 제품 인수이며 이 후속 기능은 정확 게시 base 실제 배정 전 제품 실행·변경0이다.

v2 정정: 원 v1의 No/Important1과 exact3는 보존한다. U2에서 소비할034 호출은 두 expected 인자를 모두 생략한다. paired gate를 소스에서 확인했으며 새 result SHA 생산·atomic/currentness 보증·다른 소유/수용 조건은 추가하지 않는다. 모든 구현 단계는 계속 미실행이다.

## Global Constraints

- 승인 소유권은 기존 `labflow/intake_reference_demo.py`, `tests/test_intake_reference_demo.py`, `docs/fcc/intake_reference_demo_usage.md` 정확3개다.
- 새 제품 파일/provider/loader/framework/endpoint/worker/schema/버튼/UI·CSS/CSP/ASSETS 변경0, 047·부모 API·Store·프런트 변경0.
- 기본 `()`는 intent import/API0·GET 키/구역0. ready8키·flags4·원고정오류·최초 1/2/130·borrowed Store 종료 순서를 유지한다.
- 명시 옵션의 원 context는 lease 정보 제외 정확7키+존재하는 analysis_context_id, intake 정확4키, proposal 정확4키, sources=[]다. 원 full projection과034 최소 snapshot을 혼동하지 않는다.
- 후보 rule=`DEMO-RULE-NONNORMATIVE`, method=`DEMO-METHOD-NONNORMATIVE-v1`, explicit_supplied, 양쪽 refs=[]다. 기대 proposed2/검사2 false/권한12 false이며 C2 query/권한을 산출하지 않는다.
- 새 output만 exclusive 생성하고 원자료/실패·이전 증거/refs를 보존한다. 새 후보의 모든 테스트 산출물은 `.local/INTENT-DEMO-CONNECTION-001/` 아래 새 UUID에 두고 기존057/088 증거 폴더에 새 실행을 섞지 않는다. 자료·SQL문/params·token/원7값·HAR를 외부 출력에 복사하지 않는다.
- 제품 구현은 직접 실행/총괄 독립 리뷰로 한다. 공유 폴더·동료/P01 쓰기·실장비·현장망·실제 모델 실행0.

## Review Focus

1. flag 중복/값/도움말 조합/부적절한 output: 기존 invalid_argument/2와 부작용0을 기대한다. U1 parser RED와 U5 회귀가 고정한다.
2. claim 전체/요약 대신 원 입력과 뒤바뀐 ID·synthetic: token 미공급, 실패 시 bind0와 원본 보존을 기대한다. U2/U4가 고정한다.
3. 같은 revision의 답변으로 full analysis가 바뀐 경우: 이전 구역 제거/API 재실행0을 기대한다. U3 native 관측이 고정한다.
4. 새 P0 분석 직후/Store close의 최초 KI·후행 오류·final flush: 최초 130/1/2와 P1 진입0을 기대한다. U4와 기존29 경계 assertion이 고정한다.
5. view와 별도 C2/재전송·미확인 host close: 단계별 read/write와 borrowed Store 소유 순서를 기대한다. U3/U4 native 관측이 고정한다.

---

## Task 1: 기존057의 명시 합성 대조 입력 한 단위

**Files:** Modify/Test `labflow/intake_reference_demo.py` / `tests/test_intake_reference_demo.py`; Modify `docs/fcc/intake_reference_demo_usage.md`. 현재 위치는 source-map의 AST anchors를 참고하고 확정 base에서 다시 대조한다. 새 제품 파일은 없다.

**Interfaces:**

- 유지: `main(argv=None) -> int`, `_execute(argv) -> (status, ready)`, 기존 fixed4오류·ready8키·호스트 scope·defaultworker/025 입력.
- 변경 private: `_arguments(argv) -> (Path | None, bool)`; flag 제거·중복 거절 후 기존 path 검증을 유지한다. `_prepare_demo(output: Path, *, intent_view=False) -> (Path, str, FccReportCaseCatalog, tuple, tuple)`; reference_inputs는 기존 index3, intent tuple0/1은 마지막이다.
- 소비: `claim_job(store, worker_id, *, synthetic_only=True)`, `SyntheticTextProvider().analyze(context)`, `complete_job(store, job_id, token, analysis)`, 기존 `respond(proceed)`, `intake_status(store, intake_id)['analysis']`, `read_intake_reference_snapshot(store, intake_id)`.
- 생산: `intent-input.json`의 수동 flags/원 intake/proposal/sources와 `create_server(..., intake_test_intent_inputs=intent_inputs)` 명시 인자. 새 API/loader/worker 또는 intent review 직접 재계산을 생산하지 않는다.

- [ ] **U0: 총괄의 실제 구현 계약을 먼저 확인한다.** 현재088 독립 finding과 공개 인수 여부·확정 base/branch/exact3·local dirty/ref·문서/기존 증거를 읽는다. scope 충돌 시 독립 가능한 정적 대조만 하고 제품 변경은 진행하지 않는다. 기존 후보/실패/증거를 삭제하거나 reset/rebase/amend/force push하지 않는다.

- [ ] **U1: 새 옵션과 기본 경로의 RED를 작성·실행한다.** 소유 test 파일에 `DemoIntentBoundaries`를 추가한다. `test_intent_flag_exact_grammar`는 기본/--output/flag와 두 순서 조합, duplicate/값/alias/--help 조합/native type을 고정한다. invalid는 status2/stdout0/dependency·reserve·prepare·factory0을 assert한다. `test_default_keeps_worker_and_intent_unconfigured`는 기본 run_worker1/intent import·API0/tuple()·ready exact8·추가 원입력 파일0을 assert한다. 현 소스의 옵션 거절/반환 부재로 RED임을 보존한다.

  Run: `.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -p test_intake_reference_demo.py -k DemoIntentBoundaries -v`. 새 테스트의 요구 행동 실패를 확인하고 환경 실패를 RED로 세지 않는다.

- [ ] **U2: 원입력 보존의 RED를 추가하고 최소 P0 분기를 구현한다.** `test_intent_genuine_original_inputs_and_missing_basis`는 새 전용 output에서 public API로 실제 완료한 원 claim context/submission/proceed 후 full projection/034를 비교한다. tuple1/inner3/intake4/원 context7(+존재 context_id)·token/lease/attempt 없음·원 full projection canonical 동일·originals2/기존 C2 정확4/empty catalog/no_candidate를 assert한다. `test_intent_rejects_wrong_claim_without_P1`은 없음/다른 ID/비합성에서 fixed unavailable/1와 bind0·원본 보존을 assert한다. source fixtures나 test helpers를 제품 코드에서 쓰지 않는다.

  `_arguments`의 결과를 `_execute`가 소비하고 `_prepare_demo`의 bool로 전달한다. 기본은 기존 run_worker, true만 기존 claim/synthetic analyze/complete를 직접 써서 원 context/analysis를 보존한다. proceed 뒤 full projection과034를 받고 기존 BaseException/finally로 P0를 닫는다. 후행 수동 proposal/빈 sources를 만들고 기존 `_save`로 intent-input.json을 exclusive 저장한다. `_PURPOSE/_LINES`와 C2 query/025 입력은 바꾸지 않는다. default 반환의 마지막 tuple은()로 고정한다. GREEN은 U1/U2의 assertion을 모두 유지한다.

- [ ] **U3: 명시 공급의 HTTP/DOM RED→GREEN과 단계 경계를 고정한다.** `_execute`의 기존 host 호출에 마지막 tuple을 전달한다. host API를 demo가 직접 호출하거나 리뷰를 파일에서 읽어 다시 공급하지 않는다. `test_intent_demo_real_DOM_and_C2_1440_390`는 실제 모듈 프로세스/새 output/정식 HTTP/실제 브라우저로 flag를 켜고 두 viewport를 검사한다. 공급 review9·ID/revision/full hash·literal2/proposed2/이유·검사2 false/권한12 false·quote/가짜 locator0을 assert한다. default는 API0/키·구역0이다. 모델/장비/외부 요청/다운로드·제품 JavaScript 오류0을 확인한다.

  source/PDF·034·parent 호출을 P0/startup/view/C2/replay/observer 단계로 구분해 센다. startup API1, GET/선택/펼침 API0·원문 read0·DB write0, 전체 SQL 상태 불변이다. C2는 기존 manual/no_candidate fixture로 prepare1→append1→replay1, source 읽기와 DDL/datawrite는 관측값을 보고한다. replay 원7 RAM 동일/rows1·1·1/새 write0을 assert하되 원7 값은 저장하지 않는다. 기존 현재 조회는 독립 명시 조작이며 자동 호출0이다.

  `test_intent_same_revision_answer_removes_stale_metadata`는 별도 테스트 observer가 자기 합성 접수에 public respond로 답변을 반영한 뒤 기존 GET에서 optional 키/구역 제거와 parent 재실행0을 확인한다. 생성한 원 tuple·파일을 새 currentness로 재작성하지 않는다. CLI에 답변 옵션/endpoint를 추가하지 않는다.

- [ ] **U4: 새 경로의 최초 오류·수명 회귀를 실제 자원과 fault observer로 확인한다.** `test_intent_completed_analysis_first_KI_blocks_P1`은 진짜 complete_job 성공 후 KI→후행 close OSError를 주입해130/P1 opener·factory0/ready0/원본 보존을 assert한다. `test_intent_first_P0_close_KI_blocks_P1`은 close 최초 KI와 재시도에도 동일 결과를 assert한다. 기존 worker KI·P0 close·help final flush·이전1/2/130 우선순위 assertion을 지우거나 double 검증으로 교체하지 않는다.

  `test_intent_parent_error_and_output_failure_preserve_originals`는 parent fixed3오류/원입력 저장·ready stdout 실패/host bind 실패에서 빈 성공0·기존 fixed CLI code·보존 failure·원자료 불변을 확인한다. borrowed Store가 열린 경우 host 종료 확인 전 Store close0을 확인한다. 정상/부모 진행 중·반복 KI drain에서는 actions/core close1None→host closed→caller Store close, SQLite open/C-close 일치·native4 caller close 후 해제/sidecar0/자체 port 재bind를 실제 관측한다. 과거 close count를 새 관측의 정답으로 고정하지 않는다. 강제 종료는 정상 drain 분모에 넣지 않는다.

- [ ] **U5: 직접 관련된 기존057 회귀와 문서·정적 범위를 확인한다.** 기존 `DemoBoundaries`/`DemoFirstInterrupts`29개 경계 assertion 및 `DemoNative`8개 메서드의 기존 요구를 보존한다. 이37은 현재 AST 정적 개수이며 과거 실행32와 다르다. 기존 소유 test의 출력 경로만 이번 새 증거 영역으로 옮겨 원 증거 폴더를 보존한다. 전체 소유 test 파일은 이번 CLI 변경의 직접 회귀로 한 번 실행하고 실제 새 count/fail/error/skip을 기록한다. 부모 host/intent view의 no-supply·원 tuple/cache·stale full projection·종료 경계만 필요한 만큼 선정해 재실행한다. 전체 Python/Node/browser·다른057 외 old suites를 관례적으로 실행하지 않는다.

  Run: `.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -p test_intake_reference_demo.py -v`.

  usage에는 `.venv/Scripts/python.exe -X utf8 -B -m labflow.intake_reference_demo --intent-view`와 optional 새 output, 기존 ready URL/390·1440 읽기/후보 근거 미제공·false14/별도 C2 조작/기본 미공급·Ctrl+C/원본 보존을 설명한다. no-input UI·부모를 바꾸는 문서상 약속은 하지 않는다. `python scripts/check_artifacts.py`와 exact3 UTF-8/로컬 링크·소유외 raw/ref·원증거를 대조한다. 문서 무결성을 기능/규범 검증으로 보고하지 않는다.

- [ ] **U6: 실제 후보의 cold 재현과 총괄 독립 리뷰 인계를 준비한다.** 확정 base의 exact3만 일반 commit/push하고 원격 exact SHA/dirty0·변경3·raw/GitLF 쌍을 기록한다. 별도 깨끗한 candidate checkout의 새 output에서 동일 `--intent-view` 명령→ready→정식 GET/실제 DOM1440·390→Ctrl+C drain을 재현한다. owner warm/cold/선언 wire/독립 리뷰/총괄 인수 분모를 분리한다. 원 log·실패·스크린샷·sanitized phase/native receipt·source pins·입력 원자료의 private 위치를 보존하고 원본문/DB/원7/token을 외부 패키지로 복사하지 않는다. 총괄에게 exact SHA·3파일·검증과 미실행 범위를 인계하며 findings는 별도 normal commit으로 수정한다.

## 정적 준비와 실제 구현의 구별

이 plan의 U0~U6은 모두 미실행이다. 현재는 private spec.md/plan.md/source-map.json exact3를 작성하고 소스·기존 증거/refs 불변·문자·로컬 링크만 대조한다. 제품 import/API/fixture/DB/HTTP/browser/model/hardware 실행0, 기존 code/docs/branch/ref·공유 원본 변경0이다. 아래 실행은 정확 게시 base·전용 branch 실제 배정 뒤 시작하며 새 사용자 자료·승인을 중복 요청하지 않는다.
