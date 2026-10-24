# GEN-004A 구현 계획

> For agentic workers: use superpowers:executing-plans for this bounded owner task. 사용자 연속 개발 지시와 기존 개발1 소유 경계를 유지한다.

**Goal:** 보존 PDF 분석과 현재 추출 profile의 변경을 부작용 없이 탐지한다.

**Spec:** [고정 설계](../specs/2026-10-24-analysis-generation-inspection-design.md)

**Files:** 신규 `labflow/intake_generation.py`, `tests/test_intake_generation.py`, `docs/fcc/intake_generation_usage.md`; 기존 `intake_documents.py` 공개 profile helper만 허용.

- [x] 실제 V2 완료를 재사용한 current/stale/invalid/legacy/unavailable·교차 결합·무변경 검사를 작성하고 RED를 확인한다.
- [x] 하나의 DB 읽기 snapshot과 bounded context/source 검증, 고정 응답/정제 오류를 구현한다. 현재 parser를 실행하지 않는다.
- [x] parser/코드/한도 profile 변화와 기존 TXT/PDF 회귀를 검사한다. SQL/migration/알림/실행 부작용 0을 확인한다.
- [x] 문서·정적 검사와 소유 branch commit/push·원격 SHA 대조 후 총괄에 보고한다.
- [x] 총괄이 독립 리뷰→소유 수정→관련·통합 검증→인수/게시하고 다음 generation 이력/queue 단위를 배정한다.
