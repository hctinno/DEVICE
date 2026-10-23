# Reference Readers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. 총괄이 기존 개발1·2 세션에 직접 배정하며 추가 세션을 만들지 않는다.

**Goal:** 사용자 제공 사례의 DOCX 구조와 XLSX/XLSM 셀 근거를 안전한 읽기 전용 함수로 보존한다.

**Architecture:** 독립 바이트 입력 파서 2개. 현재 공통 DB/접수/분석/작업자/가상환경/UI 계약은 변경하지 않는다.

**Tech Stack:** Python 3.12, 기존 의존성/표준 ZIP·XML, 필요 시 기존 openpyxl의 읽기 기능. Office/한컴 자동화와 매크로 실행 없음.

**Spec:** [설계](../specs/2026-10-23-reference-readers-design.md).

## Global Constraints

- 개발1은 `reference_docx.py`와 전용 검사/사용법, 개발2는 `reference_workbook.py`와 전용 검사/사용법만 수정한다.
- 실제 원본·추출문·수식/수치·시리얼을 공개 fixture/문서에 넣지 않는다.
- 현재 사용자 자료 감사 결과를 먼저 회신하고, 그 근거를 보존한 뒤 구현을 이어 간다.
- 각 담당은 전용 브랜치에 커밋/푸시하고 총괄에게 SHA와 실제 검증 범위를 보고한다.

## Review Focus

- 손상/암호화/지원하지 않는 구조·부분 처리를 완전 성공으로 표시하지 않는다.
- 출력 locator와 해시가 원본의 해당 문단/표/셀을 가리키며 임의 페이지를 만들지 않는다.
- 빈 셀/0/수식 캐시 누락/오류 값을 구별한다.
- 외부 참조·매크로·본문 명령·embedded object를 실행하지 않는다.
- ZIP 크기/멤버 수와 사용 셀 한도를 실제로 강제한다.

## 개발1 — DEV1-DOCX-002

Files: `labflow/reference_docx.py`, `tests/test_reference_docx.py`, `docs/fcc/reference_docx_usage.md`.

Interface: `read_docx(data: bytes, name: str, *, limits=None) -> dict`. limits의 정확한 키·기본값은 사용법에 고정하고 한도 미설정이 무제한을 뜻하지 않게 한다.

- [ ] 합성 문단/중첩 표·병합·한국어·빈 문서, hash/locator 재현, 외부 링크/embedded object, 손상/암호/ZIP·출력 한도의 실패 회귀를 먼저 작성한다.
- [ ] 검사 실패를 확인한 뒤 독립 읽기 함수를 구현하고 모든 누락/미지원 상태를 기록한다.
- [ ] UTF-8/링크·정적/단위 검사를 수행한다. 실제 의뢰/제품 DOCX의 private smoke를 수행하고 내용을 공개하지 않는다.
- [ ] 자기 브랜치에 커밋/푸시하고 통합 계약 제안과 실제 성공/부분/실패 수를 회신한다.

## 개발2 — DEV2-WORKBOOK-002

Files: `labflow/reference_workbook.py`, `tests/test_reference_workbook.py`, `docs/fcc/reference_workbook_usage.md`.

Interface: `read_workbook(data: bytes, name: str, *, limits=None) -> dict`. 기본/옵션 한도를 문서화한다.

- [ ] 합성 값/수식/저장 캐시·0/빈/오류·숨김/병합·외부 링크·매크로 표시·잘못된 used-range·암호화/손상·ZIP/셀 한도 회귀를 먼저 작성한다.
- [ ] 실패 확인 후 독립 읽기 함수를 구현하고 cached 값의 출처와 미재계산 상태를 출력한다.
- [ ] 기존 계산기의 재계산 기능을 임의로 붙이지 않는다. 실제 사례의 읽을 수 있는 계산표와 암호화 후보 private smoke를 수행한다.
- [ ] 정적·단위·문서 검증 뒤 자기 브랜치에 커밋/푸시한다. formula와 cached value의 차이를 포함한 한계를 총괄에 회신한다.

## 총괄 통합

소유 파일 범위/파서 출력 계약과 새 한도·지원 상태를 독립 검토한다. 관련 검사와 현재 공통 회귀를 실행한 뒤 개발 통합 브랜치에 반영한다. 파서 통과를 문서 의미 이해·측정 정확도·FCC 적합성으로 표시하지 않는다.
