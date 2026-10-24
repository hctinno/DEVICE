# FCC 사례 참조 fixture 평가029 실행 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전체 eligible independent 노출과 동일context 참조를 만족한 합성 fixture만 비교한다.

**Architecture:** 022 전체 재계산과025 공개 decoder 재검증을 사용하며 actual model score는 만들지 않는다.

**Tech Stack:** Python3.12/stdlib/unittest 및022/025 공개API.

**Spec:** [029 설계](../specs/2026-10-24-fcc-case-review-evaluation-design.md).

## Global Constraints

소유 신규3파일/전용branch만 변경한다. group/label 검수 선언과 사실 인증을 구별한다. 실제 model/훈련/평가/Store/파일/PDF/네트워크/장비 실행0이다. actual_model_score는 항상null이다.

## Review Focus

개발용 비선택preview 노출, 동일SHA/재사용 전이성분의 숨긴case, split/response/기대값의일부변조, pending/빈label을정답으로채움, 실제case를fixture나모델점수로승격하는경계를 각각검사한다.

## 소유 구현과 검토

- [ ] 완료025/022/실제미배정·실패를보존하고029 branch/정확usage를준비한다.
- [ ] 제안9수용묶음과위 Review Focus의RED 후최소게이트를구현한다.
- [ ] 전용·부모관련회귀/실제보존JSON score-null 재생·source불변/무I/O를별도기록한다.
- [ ] 문서/정적검사·소유3파일commit/push/원격대조후독립리뷰·수정·총괄통합/검증·게시와후속배정으로이어간다.
