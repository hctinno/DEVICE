# SPECTRUM-E2E-005 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 기존 개발4가 자기 clone/새 codex branch에서 진행한다.

**Goal:** 실제 Python BW/PSD 계산을 same-origin HTTP·브라우저 SVG/수치 표시에 연결해 재사용 가능한 종단 증거를 남긴다.

**Architecture:** 현재 clone의 pinned Python math producer→새 private JSON→자기 port0 메모리 server→검증된 ES 구성요소다. fixture browser 도구를 교체하지 않는다.

**Tech Stack:** 기존 Python/Node/Playwright, 추가 설치 없음.

**Spec:** [고정 설계](../specs/2026-10-24-spectrum-actual-browser-design.md)

## Global Constraints

신규 tool/usage 두 파일만 소유. -B·정확한 regular package/module import, 새 private 증거, 자기 loopback/자원만 사용. math/provider/역할/기존 UI/사용자 설정 변경 없음.

## Review Focus

정상 source 대신 fallback, model-only 검사를 browser로 오인, 작은 margin/비교 손실, 실패 뒤 기존 증거 덮기, 경로 루프/cleanup 실패를 우선 검토한다.

### Task 1: 실제 계산 브라우저 검사 도구

**Files:** `frontend/virtual_fleet/spectrum_actual_browser_check.cjs`, `docs/fcc/virtual_spectrum_actual_browser_check_usage.md`.

**Interfaces:** CLI/default/--self-test·SPECTRUM_PYTHON·증거 DTO는 설계를 따른다.

- [ ] source 없는/오염 import/잘못된 설정·새 증거 경계 self-test의 RED를 확인한다.
- [ ] 정식 math 의존을 인수하고 actual producer 5조건→same-origin GET→브라우저 rendering을 구현한다.
- [ ] 현재/잘못된 응답·강제 렌더 실패·모바일·작은 margin/표시 불가와 자원 정리·source 무변경을 실행해 증거를 남긴다.
- [ ] usage·정적·UTF-8/링크 검사와 소유 commit/push·원격 HEAD 확인을 마친다.
- [ ] 총괄 독립 리뷰→소유 수정→실제 실행·이미지 확인·인수/게시 후 제품 route 연결을 배정한다.
