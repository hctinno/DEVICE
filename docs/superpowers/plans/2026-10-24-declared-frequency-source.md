# SPECTRUM-SOURCE-005 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 기존 개발3의 독립 clone/새 codex branch에서 수행한다.

**Goal:** 명시 주파수 밀도 source·기존 BW용 knot trace와 정확한 3kHz 전력 적분을 구현한다.

**Architecture:** 기존 scalar 역할을 수정하지 않는 순수 source 모듈이다. 실제 JSON 숫자를 보존한 적분 ratio와 별도 dB knot projection을 구별한다.

**Tech Stack:** 기존 Python/JSON/Fraction/독립 Decimal, 외부 의존성 없음.

**Spec:** [고정 설계](../specs/2026-10-24-declared-frequency-source-design.md)

## Global Constraints

신규 source/test/usage 3파일만 소유. spec4MiB/depth32·3..4096점·양의 밀도·외삽0·파일/DB/시계/난수/네트워크/runtime/실제 모델·장비 호출0. 공통7 flags와 정확 ratio를 보존한다.

## Review Focus

3kHz 경계 clipping/외삽, float 비율 underflow·정밀도 상실, 모드/공칭 BW의 파형 추론, ratio의 float 반올림을 판정으로 사용, source/출력 caller alias를 우선 검토한다.

### Task 1: 선언 source와 제한 적분

**Files:** `labflow/virtual_fleet/frequency_source.py`, `tests/test_virtual_fleet_frequency_source.py`, `docs/fcc/virtual_frequency_source_usage.md`.

**Interfaces:** generate_frequency_source / integrate_source_3khz의 exact API/DTO는 설계를 따른다.

- [ ] exact schema·숫자/축·한도·입력 사본·함수부재 RED와 독립 Fraction oracle/invariants를 작성·실행한다.
- [ ] 원본 hash·독립 문맥의 log projection·정확 부분 구간 적분·유한 표기 guard를 구현한다.
- [ ] BW consumer 연결·incomplete 보존·밀도/dB 보간 차이·모드 추론0·전용/기존 RF/math/capture 회귀를 실행한다.
- [ ] usage·AST/UTF-8/링크·diff와 소유 commit/push·원격 SHA 확인을 마친다.
- [ ] 총괄 독립 리뷰→소유 수정→통합·게시 후 역할/frequency 출력·ratio PSD 연결을 실제 구현으로 배정한다.
