# SPECTRUM-004B 구현 계획

> For agentic workers: use superpowers:executing-plans. 개발3가 math 수치 수정 게시 뒤 새 codex 브랜치에서 이어 구현한다.

**Goal:** 선언 frequency fixture와 현재 signal_analyzer 관측 문맥을 정확히 결합한다.

**Spec:** [고정 설계](../specs/2026-10-24-bandwidth-capture-context-design.md)

**Files:** 신규 `labflow/virtual_fleet/spectrum_capture.py`, `tests/test_virtual_fleet_spectrum_capture.py`, `docs/fcc/virtual_spectrum_capture_usage.md`만 소유한다.

- [x] 실제 Fleet 취득/operator event·별도 주파수 fixture·host 기대값의 정상/잘림 및 source/run/hash/tick/revision 불일치 검사를 RED로 작성한다.
- [x] exact 입력·독립 사본·크기/유한성·현재 문맥 gate와 단일 BW 호출을 구현한다.
- [x] origin/scope/rf_trace_observed=false의 정확한 결과와 private/raw 비포함·출력 독립성·잘못된 문맥의 계산 호출0을 검증한다.
- [x] 관련 계산/계측/하네스·문서/정적 검사 후 소유 commit/push·원격 SHA를 보고한다.
- [x] 총괄이 독립 리뷰/소유 수정→실제 연결/인수·게시→실제 주파수 source/하네스 후속을 배정한다.
