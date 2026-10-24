# SPECTRUM-004A 구현 계획

> For agentic workers: use superpowers:executing-plans for this owner task. 기존 개발3가 담당하고 추가 에이전트를 생성하지 않는다.

**Goal:** 명시한 합성 RF 주파수/3kHz 입력에서 BW6·PSD 조건부 계산과 거절조건을 구현한다.

**Spec:** [고정 설계](../specs/2026-10-24-synthetic-spectrum-math-design.md)

**Files:** 신규 `labflow/virtual_fleet/spectrum_math.py`, `tests/test_virtual_fleet_spectrum_math.py`, `docs/fcc/virtual_spectrum_math_usage.md`만 소유한다.

- [x] 입력 exact keys·단위·축·비유한·불변성 및 BW 경계/보간/잘림/복수lobe/plateau 실패 검사를 쓰고 RED를 확인한다.
- [x] canonical 입력 hash와 BW 순수 계산을 구현한다. 불충분 입력의 숫자/조건부 판정을 비운다.
- [x] PSD 두 명시 basis·0dBm·8dBm 경계·밀도 환산과 method/time/reference/중복보정 거절을 RED→GREEN으로 구현한다.
- [x] 큰 숫자의 중간 overflow·출력 JSON 유한성·부작용 0, 관련 가상 RF 회귀·UTF-8/링크를 검사한다.
- [x] 소유 codex 브랜치 commit/push·원격 SHA 대조, API·수용 범위·미실행을 보고한다.
- [x] 총괄이 독립 리뷰→소유 수정→인수/게시하고 다음 관측·하네스 연결을 배정한다.
