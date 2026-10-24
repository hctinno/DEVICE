# GEN-004B2 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 기존 개발1과 총괄의 고정 소유 경계를 유지한다.

**Goal:** 보존 profile의 완료 재전송을 원래 summary로 반환하고 현재 상태를 바꾸지 않는다.

**Architecture:** D1의 read-only imported replay API와 총괄 complete_job 호출 접점을 연결한다. 다음 head/queue authority는 이 단위에 노출하지 않는다.

**Tech Stack:** 기존 Python/SQLite/JSON/SHA-256.

**Spec:** [고정 설계](../specs/2026-10-24-retained-completion-replay-design.md)

## Global Constraints

result8MiB/context4MiB·최초 detached snapshot·읽기 DB snapshot·보존 profile 검증·동일 token/submission·None만 legacy fallback. DDL/원본/DB/상태/queue/model/hardware 변경0.

## Review Focus

손상 origin의 legacy fallback, profile 변경 뒤 새 파싱, caller nested alias, 원래와 현재 revision의 권한 혼합, result/snapshot/token 불일치를 우선 확인한다.

### Task 1: D1 보존 replay API

**Files:** `labflow/intake_generation_ledger.py`, `tests/test_intake_generation_replay.py`, `docs/fcc/intake_generation_ledger_usage.md`.

**Interfaces:** replay_imported_completion exact API/None/error 의미는 설계를 따른다.

- [ ] 실제 수입된 완료/stale/과거revision·일반/변조/부재/fallback/한도/alias/무변경의 RED를 작성·실행한다.
- [ ] 단일 읽기 snapshot·보존 검증·동일 token/submission·원래 detached summary를 구현한다.
- [ ] 전용/B1/GEN 회귀·parser/prepare/쓰기0·usage/정적을 검증해 소유 commit/push·원격 SHA를 보고한다.

### Task 2: 총괄 complete_job 실제 연결

**Files:** `labflow/intake_jobs.py`, `tests/test_intake_generation_replay_integration.py`.

**Interfaces:** 기존 complete_job 호출을 유지하고 새 helper dict/None/error를 소비한다.

- [x] 실제 stale completed replay·부재 legacy 호환·거절 fallback0의 RED를 private4조건으로 확인했다. 신규 성공과 현재상태 무변경은 helper 인수 뒤 GREEN으로 검증한다.
- [ ] 첫 snapshot 이후·현재 prepare 이전에 작은 접점을 구현한다.
- [ ] 독립 리뷰/소유 수정·관련/통합 회귀·문서/원격 게시 후 B3 queue+writer fence로 이어간다.
