# Intake Fixture Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 접수의 정확한 자료/준비 상태를 명시적 단일 합성 실행과 연결하고 같은 화면에서 과거 결과를 읽는다.

**Architecture:** 기존 분석 queue와 별도 fixture queue/attempt를 만들고 단일 가상 방법 adapter 및 bounded worker를 연결한다. PDF page 문맥/인용은 legacy TXT V1을 보존하는 V2로 추가한다. 쓰기 CLI와 순수 읽기 HTTP는 분리한다.

**Tech Stack:** 기존 Python 3.12·SQLite·unittest·pypdf 선택 의존성, ES modules/Node·Playwright.

**Spec:** [고정 설계](../specs/2026-10-24-intake-fixture-flow-design.md)

## Global Constraints

- 독립 clone/전용 codex 브랜치와 기존 완료·실패 기록 보존. 공유 수집·사용자 원본은 읽기 전용.
- synthetic=true/hardware_verified=false/ai_model_called=false/resumable=false, case/plan 자동 생성 없음.
- raw/Licensed 추가 암호/실제 모델·장비를 개발 선행조건으로 추가하지 않는다.
- 파일/함수/API/enum/한도는 spec을 따른다. 계약 변경은 총괄이 고정한 후 반영한다.
- 담당별 소유파일만 수정하고 관련 검증 후 자기 브랜치에 commit/push한다. 검토/연결 확인에서 멈추지 않는다.

## Review Focus

- 같은 revision의 답변·보류 변경을 놓쳐 이전 준비 상태로 실행하지 않는가.
- 완료 파일이 남은 채 lease/publication이 실패한 경우 새 runtime을 자동 실행하지 않는가.
- 다른 PDF page의 같은 quote, 다른 intake/run의 valid report를 잘못 결합하지 않는가.
- partial/empty 자료·지속 장애의 평가 pass·기술 종료를 정상 측정으로 표시하지 않는가.
- 읽기 GET이 migration/evaluation/실행을 발생시키거나 늦은 응답이 선택 문맥을 덮지 않는가.

## Task 1 — 개발1: 실제 PDF 문맥/인용 연결

Files: 신규 `labflow/intake_documents.py`, `tests/test_intake_documents.py`, usage; 기존 `intake_analysis.py`, `intake_jobs.py`, `intake_worker.py`의 연결과 필요한 관련 회귀.

- [ ] TXT V1 불변·실제 합성 2쪽 PDF claim→provider→complete·페이지 위조/partial/오래된 context의 실패 검사를 작성한다.
- [ ] 실패를 확인하고 준비/페이지 추출/서버 context binding을 구현한다. parsing은 DB write transaction 밖에서 수행하고 최종 lease/revision을 다시 확인한다.
- [ ] schema2 citation과 fixture 소비를 연결하고 V1·질문·답변/보류·중복 알림·real job 격리 회귀를 실행한다.
- [ ] 관련·문서 검사 및 자기 branch commit/push 후 SHA/API/한계/후속 generation 작업을 보고한다.

## Task 2 — 총괄: readiness·fixture queue

Files: 신규 `labflow/intake_fixture_jobs.py`, 전용 tests; `labflow/schema.sql`만 additive table.

- [ ] 실제 합성 접수/위임/분석 기반 준비 hash·동일 ID·동시 claim·lease 만료·CAS의 실패 검사를 작성한다.
- [ ] spec 고정 함수와 별도 상태/예약 ID를 구현한다. 만료 running은 uncertain이며 자동 재claim하지 않는다.
- [ ] 동일 revision 답변/보류와 R1/R2 fence, 오래된 성공 게시 거절·증거 보존, 읽기용 DTO 계약을 확인한다.
- [ ] 관련 검증·고정 API를 담당에게 제공하고 다음 통합까지 commit/push한다.

## Task 3 — 개발3: 단일 recipe adapter

Files: 신규 `labflow/virtual_fleet/method_adapter.py`, 전용 tests/usage.

- [ ] 명시적 recipe/model/settings 선택·미지원·새 폴더·실제 normal 단일 trial·변경 power 산술의 실패 검사를 작성한다.
- [ ] descriptor/실행 API를 구현하고 기존 policy/harness/journal/evaluator와 private author/공개 artifact 구분을 연결한다.
- [ ] can_continue와 미결/저장 실패, source/unit/revision/fresh, case/실물 격리·기존 파일 보존을 확인한다.
- [ ] 관련 검증·문서·자기 branch commit/push 후 SHA/API/미실행 범위를 보고한다.

## Task 4 — 개발2: bounded fixture worker

Files: 신규 `labflow/intake_fixture_bridge.py`, 전용 tests/usage.

- [ ] 고정 queue/adapter 대역으로 중복/lease 상실/파일·DB실패·잘못된 identity/hash와 정상 한 claim의 실패 검사를 작성한다.
- [ ] callback fence·새 run 폴더·증거 검증·CAS 게시를 구현한다. raw exception/token/private path를 공개하지 않는다.
- [ ] 전송 retry와 새 runtime 재개를 구별하고 uncertain 자동 재실행 0·역사 결과 보존을 검사한다.
- [ ] 관련 검증·문서·자기 branch commit/push 후 SHA/API를 총괄에 보고한다.

## Task 5 — 개발4: 접수 화면의 읽기 연결

Files: 소유 `ui_read_model.py`, `ui_server.py`, frontend/app.js와 snapshot 검증; 신규 intake_flow_model.mjs/전용 tests/browser/usage.

- [ ] 새 table 없는 DB·미연결/과거 revision·교차 binding·잘못된 report/private/XSS·읽기 부작용 0의 실패 검사를 작성한다.
- [ ] same-origin GET와 최소 기록 선택 카드를 구현하고 V1/V2 page 인용을 정확히 표시한다.
- [ ] Node·HTTP·browser에서 현재 문맥/늦은 응답/렌더 실패·20개 한도·모바일과 기존 접수 회귀를 확인한다.
- [ ] 관련 검증·문서·자기 branch commit/push 후 SHA/화면/한계를 보고한다.

## Task 6 — 총괄: 실제 연결·리뷰·게시

Files: 신규 `labflow/intake_fixture_check.py`, 통합 tests/usage/기록과 HANDOFF/PLAN 갱신.

- [ ] 각 최종 원격 커밋을 인수하고 source/hash/소유권을 확인한다. 사용자 원본/비공개 자료는 공개 Git에 넣지 않는다.
- [ ] 가상 접수/위임/분석→요청/worker→단일 sensor report→접수 UI를 실제 소스로 실행한다. 단순 대역 검사를 실제 연결 검증으로 세지 않는다.
- [ ] 소유별 독립 리뷰와 지적 수정 후 관련·전체 Python/Node·브라우저·UTF-8/문서/링크/Git 검사를 수행한다.
- [ ] 검증 범위·실패/미실행·남은 작업을 기록하고 총괄 개발 브랜치 commit/push·원격 대조 후 다음 작은 단위를 배정한다.
