# 가상 RF 정규화 I/Q envelope054 구현 계획

2026-10-25 Asia/Seoul. [고정 설계](../specs/2026-10-25-virtual-fleet-rf-signal-waveform-design.md)의 A/new3을 개발3이 직접 실행하는 계획이다. 새 하위 에이전트0. 공개 계약과 정확 base/신규3의 실제 배정 전 제품 코드·새 branch·054 수용검사는 미실행이다.

**Goal:** 정수 grid의 합성 CW·사각pulse 표본과 독립 전력·에너지 분석을 제공한다.

**Architecture:** 새 순수수학 모듈 하나의 함수2와 고정오류3을 사용하고 기존 RF/Fleet/journal/DTO와 연결하지 않는다.

**Tech Stack:** Python stdlib math/json/hashlib·unittest·독립 Decimal/Fraction 정답.

## 인터페이스와 소유

신규 `labflow/virtual_fleet/rf_signal_waveform.py`의 public은 `generate_rf_baseband_envelope(spec, *, seed) -> dict`, `analyze_rf_baseband_envelope(packet) -> dict`, `RfSignalWaveformError`다. 입력 exact6/seed31bit·Fs1..1e9·N/P1..4096·-120..60dBm·정수 gate/4위상·결과8/metrics10·body1MiB·error3은 계약 값을 그대로 따른다. 신규 test/usage 각1을 합쳐 소유3이며 기존 source 수정은0이다.

## 작업 순서와 미래 확인

1. **정확 배정 확인.** 공개 계약/계획/정적Yes의 raw pin과 새 실행 base·소유3을 확인한다. 기존 추적 파일·051 frozen96/40원본·RED를 비공개 baseline으로 고정한다. 현재 HEAD를 임의의054 base로 쓰지 않는다.
2. **generator RED→구현.** `test_cw_phase_and_rectangular_gate_on_declared_halfopen_grid`, `test_strict_request_and_budget_before_allocation`을 먼저 작성해 미구현/행동 실패를 보존한다. W01~W04·W08의 literal count/phase/경계와 exact6/4/8·flags/권한을 고정한 뒤 두 packet 생성 경로만 구현한다.
3. **analyzer RED→구현.** `test_independent_literal_IQ_energy_and_Decimal_Fraction_expectations`, `test_partial_window_zero_null_underflow_and_positive_subnormal`, `test_analysis_does_not_call_generator_or_read_author`를 먼저 작성한다. W05~W10의 literal I/Q·닫힌 count식·회전/부호/Fs 관계·수치/예산/입력 불변을 고정한 뒤 public packet만 분석한다. I1의 N=Fs=1/I2e-162/Q0와 N1/Fs1e9/I3e-154/Q0는 numeric_unavailable, zero·최소 normal m 경계·subnormal component+normal 결과는 기존 허용이라는 독립 기대 분류를 고정한다. 각 양의 p/S/mean/peak/energy의 표현가능성을 판정하며 반환값에만 기존 tolerance를 적용한다. 오류정제·byte budget·public-input hash도 검증한다.
4. **전용·관련 QA.** `.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s tests -p test_virtual_fleet_rf_signal_waveform.py -v`로 전용 실패·오류·skip0을 확인한다. 기존 RF/instruments/frequency_source/spectrum_math/041/harness/journal/048/051 관련 회귀와 field/source/false flag 불변을 대조한다. runtime I/O0와 test의 비공개 증거 I/O를 구분한다.
5. **전체·문서·게시.** 새 정확 base에 맞는 file-main-guard 전체 Python/Node·`python scripts/check_artifacts.py`와 신규 usage 링크/UTF8/AST 검사를 수행한다. owner QA·immutable raw 영수증→신규3만 commit/push/remote exact/clean→총괄의 독립 제품 리뷰→필요 소유 수정 순서다. 물리/규범·모델 호출·기존실행 연결은 별도 미실행이다.

## Review Focus

- N1의 창 길이를0으로 계산하지 않는지: energy1/Fs literal 검사를 작업3에 포함한다.
- P/K 경계·s offset·부분 주기에서 선언 duty를 관측값으로 복사하지 않는지: 닫힌 M_expected/zero 창을 작업2·3에 포함한다.
- generator output로 expected를 재구성해 같은 오류를 통과시키지 않는지: 독립 I/Q·Decimal/Fraction·회전 검사를 작업3에 포함한다.
- 양의 subnormal을 단지 nonzero라는 이유로 통과시키거나 component-only 검사로 거절하지 않는지: I1 두 사례·zero exact·m 경계·subnormal component+normal 결과와 numeric_unavailable을 작업3에 포함한다. tolerance 완화는 없다.
- seed/author/expected 누출 또는 기존3dB crest/flag를 고쳐 새모델 성공으로 표시하지 않는지: I/O0·sourcepins/flags 불변을 작업4에 포함한다.

## 자체 대조

W01~W04는 작업2, W05~W10은 작업3, W11은 작업1·4, W12는 작업5에 대응한다. 함수명/필드/숫자는 한 계약만 참조한다. 새 제조사 원문 필요0이며 연결용 공백은 총괄을 통해 다음 단위에서만 다룬다. 별도 하위 에이전트/수집자/사용자 질문은 없다.
