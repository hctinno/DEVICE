# MODEL-004B Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 기존 개발2의 독립 clone/전용 branch에서 진행한다.

**Goal:** 의뢰 분석 모델의 공급자 독립 prompt와 현재 근거에 결합된 strict response decoder를 구현한다.

**Architecture:** 현재 worker의 공개 context와 validate_analysis를 소비하는 순수 신규 모듈이다. 실제 호출과 fixture worker 권한 확장은 별도 단위다.

**Tech Stack:** 기존 Python/JSON/SHA-256, 외부 의존성 없음.

**Spec:** [고정 설계](../specs/2026-10-24-model-analysis-boundary-design.md)

## Global Constraints

정확한 context·producer·분석 schema, context 6MiB/response 2MiB, strict UTF-8·중복 키/비유한 값 거절, I/O/네트워크/DB/실제 모델·실장비 호출 0. 기존 worker gate 변경 없음.

## Review Focus

문서 내 권한 지시의 system 승격, wrong context/producer/page 결합, nested caller alias 변조, strict decoder 우회, raw 오류 유출을 중점 검사한다.

### Task 1: 모델 분석 경계

**Files:** `labflow/intake_model_boundary.py`, `tests/test_intake_model_boundary.py`, `docs/fcc/intake_model_boundary_usage.md`.

**Interfaces:** build_analysis_prompt / decode_analysis_response의 exact API와 DTO는 설계를 따른다.

- [ ] 실제 TXT/PDF context와 정상·누락·충돌·다른 제품 raw JSON의 검사, malformed/quote/context/producer/한도/injection/alias의 RED를 작성·실행한다.
- [ ] 순수 snapshot·고정 prompt·엄격한 decoder와 기존 근거 검증을 구현한다.
- [ ] 전용 검사 및 기존 분석/worker 회귀, 네트워크·DB·원본 무변경과 오류 정제를 확인한다.
- [ ] usage·정적·문서 검사와 소유 branch commit/push·원격 SHA 대조를 마친다.
- [ ] 총괄 독립 리뷰·소유 수정·통합 뒤 다음 provider 연결 구현을 이어간다.
