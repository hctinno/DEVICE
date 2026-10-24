# GEN-004B1 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 기존 개발1이 자기 독립 clone에서 구현하며 추가 세션을 만들지 않는다.

**Goal:** 기존 완료 분석을 보존하면서 명시적 단건 수입·불변 이력 조회를 제품 API로 제공한다.

**Architecture:** 신규 companion ledger에만 기록한다. 다음 재분석 queue와 원자적 readiness fence의 기반이며 현재 worker/fixture 권한을 변경하지 않는다.

**Tech Stack:** 기존 Python/SQLite, 외부 의존성 추가 없음.

**Spec:** [고정 설계](../specs/2026-10-24-analysis-generation-ledger-design.md)

## Global Constraints

기존 row/token/result/UNIQUE·사용자 원본·공유 폴더 보존. 명시 단건만 수입. DDL과 최초 수입은 한 writer transaction. intake 전체에서 epoch 최초0·새 origin마다 max+1·UNIQUE(intake_id,epoch). result/snapshot 각 8MiB·context 4MiB. real/model/hardware/자동 Store hook 없음.

## Review Focus

동시 수입과 expectation 변경, DDL 중간 실패, stale 보존 profile/교차 인용, 과대 snapshot의 사전 제한, 공개 metadata의 token/원문 비노출을 우선 검토한다.

### Task 1: 완료 세대 수입과 이력 조회

**Files:** `labflow/intake_generation_ledger.py`, `tests/test_intake_generation_ledger.py`, `docs/fcc/intake_generation_ledger_usage.md`; 보존 validator 분리에 한해 `labflow/intake_generation.py`.

**Interfaces:** import_completed_generation / generation_history의 exact API와 receipt는 설계를 따른다.

- [ ] 실제 V2 완료+질문/답변/위임 seed, 일반/반복/동시 수입·무변경과 invalid/legacy/CAS/rollback/한도, R1/R2 origin·limit1 cursor·완료 event 부재 검사를 작성해 RED를 확인한다.
- [ ] transaction-safe additive DDL·검증·snapshot·immutable metadata·읽기 전용 pagination을 구현한다.
- [ ] 전용 검사와 기존 GEN/PDF/jobs/fixture 회귀를 실행하고 소스·DB·blob 경계 증거를 남긴다.
- [ ] 사용법/정적·문서 검사, 소유 branch commit/push·원격 SHA 확인을 마친다.
- [ ] 총괄 독립 리뷰→소유 수정→통합·게시 후 GEN-004B2 구현을 이어간다.
