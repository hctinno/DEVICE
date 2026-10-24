# WATCH-004A 구현 계획

> For agentic workers: use superpowers:executing-plans. 개발2가 기존 독립 clone의 새 codex 브랜치에서 수행한다.

**Goal:** 등록된 합성 source의 발견·분석을 유한한 감독 루프로 연결한다.

**Spec:** [고정 설계](../specs/2026-10-24-bounded-intake-supervisor-design.md)

**Files:** 신규 `labflow/intake_supervisor.py`, `tests/test_intake_supervisor.py`, `docs/fcc/intake_supervisor_usage.md`만 소유한다.

리뷰 수정의 추가 허용 범위: `active_intake.py`의 scan_source에 optional synthetic_only=False를 넣고 실제 scan transaction 안에서 검사하는 공통 gate와 전용 회귀. 변경 이유·호환/범위는 설계를 따른다.

- [x] 잘못된 설정/real source가 scan 전 거절되고 real job이 claim되지 않는 검사를 RED로 확인한다.
- [x] 실제 Store·source·scan·기존 fixture provider/worker의 2-cycle 발견/분석을 구현한다.
- [x] monotonic/callback latch·분할 대기·예산 전달·source/worker 오류 보존과 정제된 공개 요약을 구현하고 검사한다.
- [x] 실제 TXT/PDF·새 자료·반복 중복 방지와 기존 worker/접수 회귀·문서/정적 검사를 수행한다.
- [x] 소유 commit/push·원격 SHA/API/한계 보고 후 총괄이 독립 리뷰·수정·통합/게시와 다음 배정을 이어간다.
