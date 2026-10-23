# DEV4-UI-001 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 사용자가 지정한 개발4 세션에서 직접 구현하며 하위 에이전트는 만들지 않는다.

**Goal:** 기존 접수 상태와 출처/질문/알림을 읽는 실행 가능한 로컬 브라우저 화면.

**Architecture:** 기존 서비스 조회 함수를 읽기 전용 SQLite 스냅샷으로 연결한다. 고정 경로 HTTP API와 정적 ES module UI를 제공하고 별도 합성 fixture를 생성해 검증한다.

**Tech Stack:** Python 3.12 표준 라이브러리, HTML/CSS/JavaScript ES module, unittest, Node test runner, 브라우저.

**Spec:** [작업 설계](../specs/2026-10-23-dev4-intake-ui-design.md).

## Global Constraints

- 지정 독립 clone/브랜치만 변경. 기존 공통 DB·접수·CLI·의존성 파일 변경 금지.
- 서버는 `127.0.0.1`만 사용하며 읽기만 제공한다.
- 합성·제공 자료·미실측을 구분한다. 미구현 업로드/답변/실행 버튼 금지.
- 원문은 데이터이며 HTML/권한으로 실행하지 않는다. 한국어 UTF-8, 시각은 Asia/Seoul.
- 자동 AI·실장비·공식 발행 완료를 주장하지 않는다.

## Review Focus

- 없는/손상된 DB가 빈 접수 성공으로 보이지 않고 파일도 생성하지 않는가.
- 보완 revision과 과거 알림/작업이 현재 상태와 혼동되지 않는가.
- 미지 상태·없는 인용·사용자 답변에 성공 또는 거짓 출처를 붙이지 않는가.
- HTML 문자열, 특수문자/긴 파일명·한글, 새로고침 경합이 안전한가.
- 작은 화면과 키보드에서 목록→상세→출처 동선과 오류 재시도가 가능한가.

### Task 1: 읽기 계약과 로컬 API

**Files:** 신규 `labflow/ui_read_model.py`, `labflow/ui_server.py`, `tests/test_ui_read_model.py`, `tests/test_ui_server.py`.

**Interfaces:** 입력은 workspace 경로와 선택적 intake ID. `IntakeReadModel.snapshot(intake_id=None)`은 목록/상세 DTO를 반환한다. `create_server(workspace, host='127.0.0.1', port=8765)`는 HTTP 서버를 반환한다.

- [x] 기존 접수 함수로 실제 fixture를 만드는 테스트 작성: 빈 DB/없는 DB, 목록·상세와 알림 revision, 읽기 불변성, 쓰기 SQL 거절, 없는 ID.
- [x] `python -m unittest discover -s tests -p test_ui_read_model.py -v`에서 신규 모듈 부재로 실패 확인 후 구현·통과 확인.
- [x] HTTP 통합 테스트 작성: JSON 연결, 변경 메서드/외부 Host·Origin/경로 탐색 거절, 손상 DB의 명시적 오류.
- [x] `python -m unittest discover -s tests -p test_ui_server.py -v` 실패 확인 후 서버 구현·통과 확인.

### Task 2: 접수 화면과 재현 fixture

**Files:** 신규 `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`, `frontend/model.mjs`, `frontend/model.test.mjs`, `frontend/demo_fixture.py`.

**Interfaces:** Task 1 API를 소비한다. model module은 상태/출처/필터/알림 표시를 정의한다. fixture는 기존 접수 API로 새 합성 입력과 저장소를 생성한다.

- [x] Node 테스트 작성: 대기·실행 중·실패·보류·미지 상태, prepare_plan 구분, 사용자 답변 출처, conflict 후보, 알림 과거 revision, 한글 검색.
- [x] `node --test frontend/model.test.mjs` 신규 모듈 부재 실패 후 상태 모듈 구현·통과 확인.
- [x] 고정 셸·DOM 텍스트 렌더링·필터·상세·출처·작업·알림·오류 재시도 구현.
- [x] fixture로 실제 HTTP와 브라우저를 열고 빈 상태·전체 동선·HTML 문자열·모바일·키보드·오류 복구 확인. screenshot을 clone의 `.local/dev4/evidence/`에 저장.

### Task 3: 검사·문서·전달

**Files:** 신규 `docs/fcc/frontend_usage.md`, 위 설계/계획 진행 기록.

- [x] Python/Node 검사와 기존 접수 회귀 검사 실행. 정적 컴파일·diff 확인.
- [x] 사용법·합성 생성법·실제 검증 결과·미구현 범위 기록.
- [x] `python scripts/check_artifacts.py` 및 신규 문서 UTF-8/링크 검사 통과.
- [x] 자신의 변경만 커밋·전용 원격 브랜치 push. 원격 SHA 대조 후 총괄에게 결과 1회 보고.

## 실행 기록

2026-10-23: 설계·계획 작성. 공통 조회 함수와 `Store` 초기화 부작용 확인. 개발4의 직접 실행·추가 승인 불요·하위 에이전트 금지는 배정 지침을 우선한다. 검증 결과는 작업 완료 때 갱신한다.

2026-10-23 검증 완료: 전체 Python 118개(신규 UI 11개), Node 상태 6개, Chromium 수용 검사 9개 통과. 문서 무결성은 기존 루트 8개/124링크와 신규 4개/17링크를 별도로 확인했다. 컴파일·JavaScript 구문·diff 검사 통과. [화면 증거](../../../frontend/evidence/README.md)와 [사용법](../../fcc/frontend_usage.md)을 보존했다.

자체 검토: 사용자 지시로 하위 에이전트를 생성하지 않았다. 파일 소유권, API 조회 부작용, 상태/원본 출처, 빈 상태/실패, 좁은 화면·키보드 동선을 점검했다. 초기 환경의 의존성 부족은 전용 가상환경 설치로 해결했다. 임대 만료를 실행 중으로 계속 표시할 수 있는 문제는 실패하는 Node 회귀 검사를 먼저 확인하고 `lease_expired`로 구분해 해결했다. 보완 revision의 과거 알림/작업과 읽기 연결의 쓰기 거절도 별도 검사했다.

통합 방식은 배정 지침대로 전용 브랜치 커밋·푸시 후 총괄이 검토한다. 기존 공통 모듈·의존성 파일은 변경하지 않았고, 차단된 공통 계약 요청은 없다. 후속 답변/알림 전달·대량 조회·원본 뷰어 계약은 사용법에 기록했다. 실장비·실측·기관 검증은 미실행이다.

## 통합 리뷰 후속 수정 — 2026-10-23

총괄이 `fdb301b`에서 발견한 3건을 같은 브랜치에서 수정한다. 기존 커밋과 8765/8766 데모 서버는 보존한다.

- [x] 시장·목적 출처 필터가 서비스와 달라 참고/추론을 확정 근거로 붙이는 문제를 Node 검사로 재현하고 수정. 일반 필드·사용자 답변·제출 후보 보존 확인.
- [x] 질문 key/후보 value 누락과 배열/객체 경계 오류에서 목록·집계와 상세가 섞이는 문제를 브라우저로 재현. 중첩 필드 검증, 모든 패널·조회 시각의 사전 구성, 성공 후 상태 반영으로 수정. 정상 출처 누락·새 상태 코드는 계속 표시.
- [x] 첫 실패/로딩 중 검색·필터가 가짜 빈 상태를 만드는 문제를 브라우저로 재현하고 정상 조회 전 렌더링을 막음.
- [x] 정상/빈 응답의 렌더 예외를 주입해 마지막 성공 스냅샷 보존과 재시도 확인. Node 상태/계약 20개, 브라우저 리뷰 회귀 10개, 기존 브라우저 9개, Python 전체 118개 통과. 문서 검사(루트 8개/124링크, 전용 4개/21링크)와 JavaScript 구문·diff 검사도 통과.

변경 범위는 `frontend/`와 전용 사용법/계획 문서다. 공통 접수 규칙을 UI 쪽에 맞춰 변경하지 않는다. 실패 로그는 `.local/dev4/review-*-red.log`, 통과 로그는 `.local/dev4/review-*-green.log`에 보존한다. 새 기능이나 실장비 검증을 추가한 작업이 아니다.
