# 능동 접수와 영속 분석 작업 — 첫 개발 단위

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. 기존 사용자 위임에 따라 이 세션에서 직접 구현하고 검증한다. 수집 공유 폴더는 읽기만 한다.

**Goal:** 안정된 제품 자료 묶음을 발견해 미확정 의뢰와 분석 작업을 보존하고, 근거 있는 분석 결과·누락·충돌·보류·재개를 연결한다.

**Architecture:** 기존 Python/SQLite Store에 독립 접수 테이블을 추가한다. 미확정 접수는 제조사·모델·FCC 범위를 요구하는 기존 측정 case와 분리하며, 확정 전 빈칸을 만들어 채우지 않는다. 폴더 스캔, 임대된 분석 작업, 분석 결과 적용을 별도 경계로 두어 실제 모델 연결을 추가할 수 있게 한다.

**Tech Stack:** Python 3.10+, sqlite3, hashlib, pathlib, unittest, 기존 MCP SDK. 문서 의미 추출은 교체 가능한 분석 계약으로 시작한다.

**Spec:** [상세 설계 A 및 수용 기준 1·2·11·14–18](../specs/2026-10-23-smartphone-wifi24-bgn-design.md), [개발 인수 지시](../../../DEVELOPER-START.md).

## Global Constraints

- 기준 커밋: `a799b0b2e769fefac2cb88d7a1f8ddaa43ca71a6`; 개발 브랜치: `codex/pipeline-dev-20261023-intake`.
- 수집 폴더 밖 독립 clone에서만 코드·가상환경·DB·Git을 변경한다.
- 스마트폰/FCC 기본값, 근거 없는 제조사/모델, 수집 문서의 자동 기술 승인, 실장비 실행은 추가하지 않는다.
- 자료는 입력이며 운영 위임이 아니다. 사용자 응답만 위임/보류를 변경한다.
- UTF-8 파일 I/O와 원본 해시, 이력 및 합성 표시를 보존한다.
- 현재 단위는 결정적 접수/상태/분석 응답 계약이다. 상시 모델 서비스·OCR·실제 AI 정확도·측정 방법 검증은 후속 단위로 명시한다.

## Review Focus

- 파일 복사가 잠시 멈추거나 스캔 중 바뀜: 묶음 단위 안정화와 읽기 전후 검증, 임시 파일이 있는 묶음 보류.
- 같은 원본이 서로 다른 의뢰에 들어옴: 원본 바이트만 공유하고 의뢰 참조는 각각 유지.
- 보완과 늦게 돌아온 AI 응답의 경합: 이전 revision 결과로 최신 상태를 덮어쓰지 않음.
- 참고 FCC 성적서·문서 내 운영 지시: 의뢰 시장과 위임으로 자동 승격하지 않음.
- 임대 만료/오류/재시작: 이전 작업자 결과 차단, 중복 결과·알림·사용자 응답은 멱등 처리.

## Task 0: 새 PC 기준 검증 복구

**Files:** `labflow/reporting.py`, 필요한 UTF-8 입출력 지점, `tests/test_labflow.py`.

- [x] 기존 48개 실행: 1 failure + 6 errors. 보고서의 cp949 인코딩 오류 확인.
- [x] 한글/비ASCII 보고서를 UTF-8로 왕복하는 회귀 사례를 추가하고 실패 확인.
- [x] 보고서 파일 입출력을 UTF-8로 지정.
- [x] `python -m unittest discover -s tests -q`: 49개 통과 후 수정 커밋.

## Task 1: 안정된 묶음 접수

**Files:** `labflow/active_intake.py`, `labflow/schema.sql`, `tests/test_active_intake.py`.

**Interfaces:** `register_source(store, source_id, root, *, synthetic, settle_seconds=5)`; `scan_source(store, source_id, *, now=None)`; `intake_status(store, intake_id=None)`.

- [x] 두 번의 관측·묶음 안정 시간, 임시/빈 파일 보류, 출력/링크 제외, 신규·보완·삭제 이력·중복 및 별도 의뢰 동일 해시 테스트를 작성하고 실패 확인.
- [x] 지정 입력 폴더의 직계 하위 폴더를 별도 자료 묶음으로 관리. 루트의 분류되지 않은 파일은 대상 확인 필요로 보고한다. 같은 묶음의 보완은 같은 intake ID와 새 revision으로 연결한다.
- [x] 원본 바이트 저장과 revision/분석 작업 생성을 하나의 DB 트랜잭션으로 연결. 부분 실패는 성공 처리하지 않는다.
- [x] 기능 테스트 12개 포함 전체 61개 통과 후 `53adc51` 커밋. Windows 링크 검사는 실제 정션으로 검증했다.

## Task 2: 분석 계약·영속 작업·사용자 응답

**Files:** `labflow/intake_jobs.py`, `labflow/intake_analysis.py`, `labflow/schema.sql`, `tests/test_intake_jobs.py`.

**Interfaces:** `claim_job(store, worker_id, *, now=None, lease_seconds=120)`; `complete_job(store, job_id, token, analysis, *, now=None)`; `fail_job(store, job_id, token, *, now=None)`; `respond(store, event_id, action, *, intake_id=None)`; `notifications(store)`.

- [x] 임대 만료/오류/재시작/중복 완료/오래된 revision, 출처 없는 사실/다른 자료 인용, 시장·목적 누락/충돌, 다중 의뢰 대상, 보류·보완·위임 재사용 사례를 작성하고 실패 확인.
- [x] 분석 결과는 제품 사실(명시/추론/미확정)과 원본 hash/인용 위치, 미해결 질문으로 보존. 시장/목적은 명시된 의뢰 자료 또는 사용자 답변에만 연결. 측정 지원은 계속 미검증.
- [x] 작업자 임대 token으로 중복/늦은 결과 차단. 사실 충돌/누락은 질문 상태로, 위임/보류는 별도 사용자 이벤트로 기록. 해결된 질문과 동일 알림은 반복 생성하지 않는다.
- [x] 전체 80개 통과 후 `06e8683` 커밋. 이후 통합 검토에서 실패 가시성·중복 완료의 원본 검증·누락 질문 보존 회귀를 추가했다.

## Task 3: CLI/MCP·인수 기록·게시

**Files:** `labflow/__main__.py`, `labflow/mcp_server.py`, `docs/fcc/active_intake_usage.md`, `docs/material-intake/2026-10-23-development-intake.md`, `HANDOFF.md`, `PLAN.md`.

- [x] CLI와 MCP에 스캔/상태/분석 작업/결과를 연결하고 실제 stdio 인수 검증. 입력 경로 등록/사용자 응답은 신뢰된 CLI 경계에만 둔다.
- [x] P01 게시 SHA `371c993b62b9e054f61cbd1d0db57815a9a0e62e`의 5개 ZIP과 manifest를 개발 전용 비공개 공간에서 누적 검증. 수집 폴더의 진행 중 파일을 패키징하지 않는다.
- [x] 합성 자료만으로 첫 흐름을 실행하고 모델 정확도 검증과 구분. 실행 가능한 사용법, 실패·검사 결과, 남은 실제 입력을 기록.
- [x] `python scripts/check_artifacts.py` 8개 문서/109개 링크, 변경 Markdown 7개/55개 링크 별도 검사, 전체 unittest 86개, 정적 컴파일, `git diff --check` 통과.
- [ ] 전용 개발 브랜치에 커밋·push하고 원격 SHA 일치 확인.

## 범위 및 결정 기록

- 첫 단위에서 모델 공급자·OCR·문서 파서를 한꺼번에 고정하지 않는다. 파일 및 분석 작업 계약을 먼저 사용할 수 있게 만들고, 실제 AI 호출/문서 이해 수용 검증은 다음 작업으로 이어 간다.
- 입력의 하위 폴더는 업로드 묶음일 뿐 동일 제품의 증명이 아니다. 분석이 복수 제품/모호함을 발견하면 동일성 질문으로 보류한다.
- 설계/목표/역할은 사용자가 이미 위임했다. 새 승인 라운드나 필수 다중 에이전트 실행을 추가하지 않는다.
- 최종 코드는 작성자가 별도 검토했다. 독립 검토자를 추가 실행하지 않았다. 실제 AI API·다형식 파서·상시 서비스·실장비 검증은 이 단위의 통과 항목에 포함하지 않는다.
