# 성적서 고정 recipe026 실행 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 검수 source와 현재 고정 합성 fixture의 호환성/부족을 명시해 실행 권한 없는 후보만 준비한다.

**Architecture:** 제공 case9 DTO와 명시 selector21개를 검사하고 기존 describe를 최대1회 재사용한다.

**Tech Stack:** Python3.12/stdlib/unittest, 기존 method descriptor.

**Spec:** [026 설계](../specs/2026-10-24-fcc-report-fixture-recipe-design.md).

## Global Constraints

신규 소유3파일/전용branch만 변경한다. source 원값/단위·현재 고정 RF/계측량 경계를 보존한다. source 누락은 default로 채우지 않는다. factory/trial/장비/Store/파일/PDF/모델·외부 실행0이다.

## Review Focus

설정과 측정값 혼합, 다른 표/행/모델 point 혼합, 별도 setup의 암묵 연결, native 단위/기준면·평균정의 자동 변환, descriptor 실패/포장 실패를 준비 성공으로 표시하는 경계를 각각 검사한다.

## 소유 구현·독립 검토

- [ ] 완료023/No2·실제 검증을 보존하고026 branch/정확 usage·33개 합성 RED 준비를 고정한다.
- [ ] missing module·앞의 Review Focus·필수 bootstrap 누락/0/false·한도 RED 후 최소 구현한다.
- [ ] 전용·기존 descriptor/시설/Fleet/023 회귀 및 실제 준비자료의 부족 처리를 별도 실행한다.
- [ ] protected source/원문·실패 불변, 문서/정적 검사 후 소유3파일 commit/push·원격 대조한다.
- [ ] 독립 리뷰/소유 수정·총괄 통합/검증·게시와 실제 자료에 필요한 다음 명시 확장으로 이어간다.
