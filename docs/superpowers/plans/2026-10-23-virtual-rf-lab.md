# 가상 RF 시험소 첫 실행 환경 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans in this development session. Follow the user's independent-clone and P01-only coordination instructions. Steps use checkboxes; no additional agents are required.

**Goal:** 가상 스마트폰·RF 연결 경로·N1914A 문서 기반 부분 프로필로 정상과 장애 시나리오를 실행하고 재현 가능한 증거를 남긴다.

**Architecture:** Python 상태 모델과 명시적인 합성 RF 수치를 사용한다. 계측기 명령의 문서 근거와 실제로 측정하지 않은 가상 정책을 구분한다. 가상 시간은 호출자가 전진시키며, 시나리오의 기대 결과는 측정 모델과 별도로 정의한다. 기존 접수·하네스와 연결할 수 있는 라이브러리를 먼저 제공한다.

**Tech Stack:** 기존 Python 3.10+·unittest·CLI, 표준 라이브러리만 사용.

**Spec:** [기존 b/g/n 설계의 가상 실행 계약과 수용 기준](../specs/2026-10-23-smartphone-wifi24-bgn-design.md), [시스템 실행 계약](../../../IMPLEMENTATION.md), 사용자의 가상 시험소 선행 개발 방향. 본 계획은 그 중 첫 가상 실행 단위이며 전체 접수→자율 AI→성적서 또는 RF 물리 해석 완성을 뜻하지 않는다.

## Global Constraints

- 수집 공유 폴더는 읽기만 하고 독립 개발 복제본에서 구현·검사·커밋·푸시한다.
- 실장비 네트워크·SDK·외부 명령을 호출하는 경로를 추가하지 않는다.
- 모든 반환값과 저장 결과에 합성 출처를 표시한다. 실측 성적서 입력으로 자동 등록하지 않는다.
- 원문·매핑·자료 미확보 기록은 [개발 자료 요청](../../material-intake/2026-10-23-virtual-lab-requests.md)을 따른다.
- N1914A의 단일 A 채널, 단일 측정, ASCII 수치와 IMM/BUS/HOLD만 첫 부분 프로필로 다룬다. 실장비 호환성은 미검증이다.
- binary byte order·waveform·EXT 응답·INIT?·연속 측정·OEM RF 명령을 추정해 지원하지 않는다.

## Review Focus

- 성공 ACK만 있고 RF가 없는 경우: 별도 측정이 잡음 바닥을 보여야 한다.
- FETCH를 반복하면 새 측정이나 잡음 재생성이 없어야 한다.
- 대기 중 중복 INIT, 잘못된 BUS trigger, *RST 후 오류 큐를 검증한다.
- 측정 도중 또는 측정 후 셋업이 바뀌면 기존 결과가 유효하게 재사용되지 않아야 한다.
- NaN/무한대/불리언 수치, 복합 명령, 미지원 채널/기능을 명시적으로 거절한다.

## Task 1: 가상 상태 모델과 문서 기반 명령 부분집합

**Files:** Create `labflow/virtual_lab.py`, `tests/test_virtual_lab.py`.

**Interfaces:** `VirtualLab(seed=0, measurement_ticks=2, noise_db=0.0)`, `configure_dut(mode, channel, power_dbm)`, `set_path(connected, loss_db)`, `start_tx()`, `stop_tx()`, `inject_fault(name, value)`, `advance(ticks)`, `meter(command) -> dict`.

- [x] Write failing tests for 10 dBm source / 3 dB path → 7 dBm / approximately 0.005011872 W, pending completion, unchanged cached fetch, BUS trigger, duplicate-init FIFO errors, abort and reset.
- [x] Run `python -m unittest discover -s tests -p test_virtual_lab.py -v` and observe missing behavior.
- [x] Implement strict numeric bounds and monotonic setup/measurement identities. Mark synthetic timing, noise, identity and invalidation policies explicitly.
- [x] Add and run tests for silent TX, disconnected path/meter, stuck measurement, stale setup, deterministic noise, unsupported commands and error queue overflow.

## Task 2: 시나리오 실행과 독립 결과 검사

**Files:** Create `labflow/virtual_scenarios.py`; extend `tests/test_virtual_lab.py`.

**Interfaces:** `evaluate_virtual_observation(observation, minimum_dbm, maximum_dbm) -> str`; `run_virtual_scenarios(output_dir) -> dict`.

- [x] Write failing tests for normal, silent TX, cable open, thermal drop, stuck measurement and transport loss/recovery. The assessor checks observed status/value/identity against literal expectations, never a scenario-name success shortcut.
- [x] Implement six seeded runs and bounded polling. Keep before/after recovery observations and failure evidence.
- [x] Save each invocation under a new run directory with UTF-8 JSON transcripts and SHA-256 manifest. Repeated invocations preserve prior results.

## Task 3: CLI, documentation and complete verification

**Files:** Modify `labflow/__main__.py`, `HANDOFF.md`, `PLAN.md`, `IMPLEMENTATION.md`; create `docs/fcc/virtual_lab_usage.md`.

- [x] Write a subprocess test for `python -m labflow --workspace STATE virtual-check --out OUT`, including a non-ASCII path and artifact hash verification.
- [x] Add CLI and explain the partial profile, source pages, scenario expectations and remaining AI/MCP integration.
- [x] Run the full unittest suite, `python scripts/check_artifacts.py`, compile checks and `git diff --check`.
- [x] Review changes and update plan/verification results; commit and push the development branch and verify remote SHA.

## Implementation decisions

첫 단계는 상태 기반 행동 모델이다. 화면만 있는 mock은 명령·상태·결과의 불일치를 검증하지 못하고, RF 전자기장 전체 해석은 이 단계의 입력·검증 근거가 부족하다. 필요한 신호 모델은 추후 실측으로 보정한다. 오류 큐와 INIT/FETCH 등 확인된 문서 의미만 재현하고, 시간·RF 수치·연결 변경 무효화는 제품에 공개하는 합성 정책이다.

## 검증 기록 — 2026-10-23

- 전체 unittest 107개 통과, 생략 0개. 이 중 새 가상 환경 검사 21개다. 누락 구현으로 실패하는 검사를 먼저 실행한 뒤 모델·실행기·CLI를 구현했다.
- CLI 실실행: 6개 시나리오 통과, 실패 0개. 관측·평가 12개, summary, manifest를 새 실행 폴더에 저장했다. 측정 멈춤의 3회 대기·중단·무효화·재취득을 저장 결과에서 확인했다.
- 자체 코드 검토로 찾은 모순된 OPC 상태/응답과 과도하게 큰 정수 입력을 실패 검사로 재현한 뒤 보강했다. 독립 검토자나 실제 AI 모델의 평가로 표시하지 않는다.
- `check_artifacts.py`: 루트 문서 8개·링크 119개 통과. 변경한 문서 8개·링크 80개도 별도로 검사했다. compileall과 diff 검사 통과.
- 원문 v2의 3개 packet·22개 파일 검증, N1914A 원문 발췌·렌더링 대조를 수행했다. 실장비·현장·규격 적합성·실제 RF 물리·모델 학습은 미검증이다.
- 구현 커밋 `d1c7d9ecdfaa7ec795e536551c245a9ed578df38`을 전용 개발 브랜치 `codex/pipeline-dev-20261023-intake`에 푸시하고 원격 SHA 일치를 확인했다. P01에 v2 인수·구현·검증 결과와 남은 자료 공백을 직접 전달했다.
