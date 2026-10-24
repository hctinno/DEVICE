# FCC 사례 실제 화면027 실행 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 검수 catalog를 명시 주입한 기존 제품 서버에서 사례 조회 화면을 사용한다.

**Architecture:** 주메뉴 링크와 별도 페이지/읽기 API2개를 추가하고021/024를 재사용한다.

**Tech Stack:** 기존 Python HTTP server/unittest, ES module/Node/Playwright.

**Spec:** [027 설계](../specs/2026-10-24-fcc-case-route-design.md).

## Global Constraints

소유8파일/전용branch만 변경한다. 기존 접수/장비/DUT·Store·원본/공유 폴더를 보존한다. 원문 파일/PDF/packet은 HTTP로 제공하지 않는다. 실제 모델·물리·현장 실행은0이고 자기 loopback0만 사용한다.

## Review Focus

미주입과 빈 corpus의 혼동, optional import/오류의 기존 화면 전파, source 경로의 HTTP 노출, 늦은 응답의 필터/선택 변경, 실제 catalog와 DTO replay의 혼동을 각각 RED로 고정한다.

## 소유 구현과 검토

- [ ] 024 소유 수정/실패를 보존하고 별도027 branch를 준비한다.021 의존성 인수와027 변경을 구분한다.
- [ ] 위8파일의 정확 interface/오류/예산/actual caller를 usage에 고정해 총괄에 전달한다.
- [ ] 미구성/정상 빈/타입·ID·메서드/오류 격리 RED 후 API·정적 화면의 최소 구현을 한다.
- [ ] 실제021 caller→제품서버→GET/DOM과 계약·390px/keyboard·기존 회귀를 별도로 실행하고 source/원문 불변을 기록한다.
- [ ] 소유 commit/push·원격 대조 후 독립 리뷰/소유 수정·총괄 통합/검증/게시와 다음 단위로 이어간다.
