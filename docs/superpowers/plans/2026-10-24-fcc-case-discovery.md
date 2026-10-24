# FCC 검토 사례 발견028 실행 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 상충·미확인 사례를 찾아 검토하면서 기존 진행 후보/권한을 유지한다.

**Architecture:** 생성 완료021 인덱스의 별도 discover 질의와 kind만 추가한다.

**Tech Stack:** 기존 Python3.12/stdlib/unittest 및021.

**Spec:** [028 설계](../specs/2026-10-24-fcc-case-discovery-design.md).

## Global Constraints

소유 기존3파일/전용branch만 변경한다. search/match_intake·사례 상태·원문/rights·평가/실행 권한은 불변이다. 생성 뒤 파일/PDF/네트워크/SDK/모델 읽기/실행0이다.

## Review Focus

상충과 명백한 불일치 혼동, related 모델의 exact 승격, 부분/빈 query를 확인된 일치로 표시, discovery와 진행 후보 혼합, 허용 JSON보다 작은 반환 포장 예산을 각각 회귀로 고정한다.

## 소유 구현과 검토

- [ ] 고정021부모/실패/기존 source를 보존하고028 branch를 만든다.
- [ ] 정확 DTO/상태·정렬·예산·오류·입력한도를 usage에 제시해 총괄에 전달한다.
- [ ] 앞의 Review Focus와 S05상충 조회/기존후보0 RED부터 실행한다.
- [ ] 별도 메모리 discovery의 최소 구현·기존021 회귀·실제S03/S05를 실행하고 source 불변을 기록한다.
- [ ] 소유 commit/push·원격 비교 후 독립 리뷰/수정·총괄 통합/검증/게시와 후속 배정으로 이어간다.
