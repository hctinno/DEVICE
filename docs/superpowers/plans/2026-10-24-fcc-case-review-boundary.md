# FCC 사례 AI 경계025 실행 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 검수된021 사례의 bounded 문맥과 그 문맥에만 결합하는 strict 선택/근거 응답 경계를 구현한다.

**Architecture:** 021의 읽기 catalog를 재사용하고 prompt/context와 응답 decoder를 분리한다. 모델 호출·원문 읽기·실행/평가 권한을 추가하지 않는다.

**Tech Stack:** 기존 Python3.12/stdlib JSON·hashlib·unittest 및021 catalog.

**Spec:** [025 설계](../specs/2026-10-24-fcc-case-review-boundary-design.md).

## Global Constraints

공유 수집/원본은 읽기 전용이고 공개 Git에는 합성 코드/fixture만 넣는다. 개발2의 신규3파일만 소유한다.021/022 의미·정확 판본·partial/unknown·0/false를 보존한다. 실제 모델/송신/학습/평가·Store/SDK·물리/현장 실행은0이다.

## Review Focus

- 동일 claim ID라도 다른 case/document/SHA/페이지의 응답 참조를 거절한다.
- 표준 번호만 있는 근거와 reviewer inference가 report fact로 변하지 않는다.
- no-candidate/partial/HAC72미인용을 정상 상태로 보존한다.
- 큰 문맥/응답을 작업 예산 안에서 중단하고 private 내용을 오류에 넣지 않는다.
- 실제 private 입력+합성 응답과 실제 모델 평가/022 분할 승인을 구별한다.

## Task 1: 정확 문맥/응답 계약과 구현

**Files:** Create `labflow/fcc_case_review.py`, `tests/test_fcc_case_review.py`, `docs/fcc/fcc_case_review_usage.md`.

- [ ] 소유022 HEAD와 실제 검증 영수증을 보존하고 새025 branch를 만든다.
- [ ] 021 최종 커밋을 정확 확인하고 usage의 signature/정확 schema·예산·identity/오류를 총괄에 전달한다. 위 Review Focus5개를 수용 검사로 배치한다.
- [ ] missing module/문맥 불일치·근거 혼합/예산 초과의 RED를 기록한다.
- [ ] bounded 문맥과 strict decoder의 최소 구현 후 전용·기존021/022/모델 경계 검사를 실행한다.
- [ ] 실제021 B001을 private에서 구성해 문맥과 합성 응답 decoding을 실행하고 source 불변/모델·외부 송신0을 기록한다.
- [ ] 소유3파일만 커밋·푸시/원격 비교하고 candidate/검증 pins를 총괄에 준다.

## Task 2: 독립 검토·수정·총괄 통합

- [ ] 총괄은 정확 candidate의 독립 기능 리뷰를 배정한다. Important/Critical은 소유 RED/수정·재검토로 해소한다.
- [ ] 승인된 소유 커밋만 통합하고 관련/실제 private 검증·문서 무결성을 수행한다.
- [ ] 결과·범위·미검증과 다음 작은 단위를 기록하고 개발 브랜치 게시/원격 일치를 확인한다.
