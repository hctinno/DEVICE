# Virtual Fleet Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 원시데이터 없이 전체 가상환경에서 관측 기반 제한 실행과 정상·장애·복구 평가·증거 저장·완료 기록 조회를 연결한다.

**Architecture:** 기존 VirtualFleet의 운영 API만 사용하는 별도 fixture 실행기를 만든다. 운영 journal과 작성자/평가 정보를 분리하며 CLI 완료 결과만 기존 가상 화면에 주입한다. 기존 접수/VirtualSession/core와 실제 모델·장비는 변경하지 않는다.

**Tech Stack:** Python 3.12 표준 라이브러리·unittest, 기존 loopback HTTP, ES modules·Node tests·Playwright.

**Spec:** [고정 설계](../specs/2026-10-24-virtual-fleet-harness-design.md)

## Global Constraints

- 기준 `890ae269e10a108e93d8e09daa8f209a270c7bc6`; 각 독립 clone/작업 브랜치와 원본을 보존한다.
- Un-licensed catalog 64프로필/24역할. `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`.
- 실제 모델/장비/현장망·매크로 실행 없음. raw/Licensed 암호 추가 요청 없음.
- 기존 core·역할·접수·가상 세션 변경 금지. 인터페이스 수정은 총괄에 먼저 보고한다.
- 같은 ID/instance/body의 제한 재시도, 협력식 wall deadline, 1 tick advance. 강제 취소·재시작 재개를 지원했다고 표시하지 않는다.
- 모든 담당은 자기 소유 파일만 수정하고 코드·검사·문서·검증 결과를 자기 브랜치에 commit/push해 총괄에 전달한다.

## Review Focus

- 응답 유실 후 advance를 다시 적용하거나 새 runtime에서 재시작하는 입력은 불확실로 보존해야 한다.
- policy가 context·receipt를 변경해도 runtime/다음 문맥/운영 증거가 변하지 않아야 한다.
- intent 저장 뒤 receipt가 없는 파일은 완료나 재개 가능으로 표시하면 안 된다.
- 종료 후 바뀐 revision과 취득 당시 revision을 혼동하거나 과거 receipt를 새 측정으로 판정하면 안 된다.
- UI의 미평가/평가기 오류/판정 fail/조회 실패·완료 기록을 서로 덮지 않아야 한다.

## Task 1 — 개발2: 제한된 관측 실행기

Files: create `labflow/virtual_fleet/harness.py`, `tests/test_virtual_fleet_harness.py`, `docs/fcc/virtual_fleet_harness_usage.md`.

- [ ] 설계의 constructor/context/proposal/result/event 계약을 읽고 예산·격리·같은 ID 유실재시도·저장 실패·늦은 응답의 실패 검사를 작성한다.
- [ ] 실패를 실행해 확인하고 최소 `FleetHarness`/`RetryableTransportError`를 구현한다. policy와 runtime 객체를 분리하고 raw exception을 공개하지 않는다.
- [ ] memory event sink로 source/단위/revision 판정과 stop/unsupported/uncertain 구분을 확인한다.
- [ ] 관련 검사·문서 검사를 통과한 뒤 소스 SHA/API/한계와 함께 commit/push한다.

## Task 2 — 개발3: 운영 증거 journal

Files: create `labflow/virtual_fleet/journal.py`, `tests/test_virtual_fleet_journal.py`, `docs/fcc/virtual_fleet_journal_usage.md`.

- [ ] schema/sequence/hash/중복키·부분 쓰기·저장 실패·private canary·기존 파일 보존의 실패 검사를 작성하고 실행한다.
- [ ] `OperatorJournal` callback/context manager와 reader를 구현한다. intent/receipt의 미결 ID를 반환하고 `resumable=false`를 고정한다.
- [ ] UTF-8/LF·fsync/한도·preinitialized provenance를 검사하며 초기화부터 replay/복구했다고 주장하지 않는다.
- [ ] 관련 검사·문서 검사를 통과한 뒤 소스 SHA/API/한계와 함께 commit/push한다.

## Task 3 — 개발1: 관측 기반 fixture policy

Files: create `labflow/virtual_fleet/policies.py`, `tests/test_virtual_fleet_policies.py`, `docs/fcc/virtual_fleet_policy_usage.md`.

- [ ] 실제 공개 RF 관측 모양으로 새 취득/단절/대기/원인 제거 후 시작/잘못된 unit/source/revision의 실패 검사를 작성·실행한다.
- [ ] `RFSensorFixturePolicy`를 구현한다. 정답·fault·seed·경로·라벨이나 runtime 객체를 생성자/문맥으로 받지 않는다.
- [ ] sensor read와 meter fetch를 구별하고 새 요청 ID는 실행기에 맡긴다. context 변조와 stale receipt가 완료를 만들지 않는지 확인한다.
- [ ] 관련 검사·문서 검사를 통과한 뒤 소스 SHA/API/한계와 함께 commit/push한다.

## Task 4 — 개발4: 완료 결과 조회

Files: modify owned `labflow/virtual_fleet_server.py`, `frontend/virtual_fleet/{index.html,app.mjs,styles.css}`; create `frontend/virtual_fleet/harness_model.mjs`, `.test.mjs`, 전용 browser check; add own HTTP tests and usage.

- [ ] optional report 주입/없음/잘못된 JSON·private field·호출자 변조의 HTTP 실패 검사를 작성·실행한다.
- [ ] 설계의 read-only GET와 완료 기록 panel을 구현한다. 기존 state/명령·CSRF·유실재시도를 변경하지 않는다.
- [ ] Node/브라우저에서 평가 상태 분리·늦은 응답/렌더 실패·XSS·모바일을 확인한다. 기존 실제 64프로필 브라우저도 통과시킨다.
- [ ] 관련 검사·문서 검사를 통과한 뒤 소스 SHA/API/한계와 함께 commit/push한다.

## Task 5 — 총괄: 분리 평가·CLI 통합

Files: create `labflow/virtual_fleet/evaluation.py`, `harness_check.py`, `tests/test_virtual_fleet_evaluation.py`, 통합 사용법/기록.

- [ ] 위 계약을 stub 기반으로 먼저 검사하고 D2/D3/D1의 고정 API를 인수한다.
- [ ] 같은 공개 목표의 정상/지속 장애/상대 tick 4 복구를 별도 작성자 wrapper로 준비한다. 운영 policy context에 작성자 정보가 없는지 검사한다.
- [ ] 현재 snapshot의 source/unit/새 취득/revision과 독립 합성 산술로 평가하고 별도 평가 결과를 공개 result에 붙인다. 원시 정답은 private 파일에만 저장한다.
- [ ] 새 출력 폴더 CLI·journal/result/author/manifest와 선택적 완료 보고서 화면을 연결한다. 기존 파일·실패 로그를 보존한다.
- [ ] 관련·전체 Python, Node, 실제 브라우저, UTF-8/문서/링크·공백 검사와 독립 리뷰를 실행한다. 통과 범위만 기록하고 commit/push·원격 SHA를 대조한다.
