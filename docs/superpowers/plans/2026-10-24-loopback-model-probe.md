# MODEL-PROBE-005 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 기존 개발2의 독립 clone/새 codex branch에서 진행한다.

**Goal:** MODEL-004B prompt/decoder를 자기 HTTP 계약 서버·제한 child와 연결해 실제 전송/실패 증거를 만든다.

**Architecture:** preflight/snapshot→새 private 증거→단일 killable child POST→부모 strict decode·결과 보존이다. worker fixture gate와 실제 제공자 설정은 유지한다.

**Tech Stack:** 기존 Python HTTP/multiprocessing/JSON, 외부 의존성 없음.

**Spec:** [고정 설계](../specs/2026-10-24-loopback-model-probe-design.md)

## Global Constraints

신규 probe/test/usage3파일만 소유. 명시127.0.0.1/analysis·synthetic만 허용. 응답2MiB·상한60초·단일자기child·새private증거·실모델/외부API/하드웨어/Store/worker/jobs 변경0.

## Review Focus

DNS/proxy/redirect 우회, header/body의 slow stream 전체 deadline, child/원시 로그 유출·정리, 반환 producer/context/quote 결합, 기존 증거/설정오류 부작용을 중점 확인한다.

### Task 1: 로컬 계약 probe

**Files:** `labflow/intake_model_probe.py`, `tests/test_intake_model_probe.py`, `docs/fcc/intake_model_probe_usage.md`.

**Interfaces:** probe_loopback_analysis의 exact API/상태/flags·증거 한도는 설계를 따른다.

- [ ] 실제 TXT/PDF context와 port0 fake 서버·설정/decoder/과대/timeout/새증거 경계 RED를 작성·실행한다.
- [ ] importable child·정확 loopback POST·부모 전체 deadline·정제 결과/원본 증거·strict decoder를 구현한다.
- [ ] redirect/HTTP error/slow header/body/crash/cleanup·네트워크 범위·DB/worker 무변경과 기존 boundary 회귀를 확인한다.
- [ ] usage·정적/UTF-8/링크·diff와 소유 commit/push·원격 SHA 대조를 마친다.
- [ ] 총괄 독립 리뷰→소유 수정→실제 교환 인수/게시 후 provider/worker policy 단위를 이어간다.
