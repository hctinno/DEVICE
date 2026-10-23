# SPECTRUM-004A — 명시적 합성 주파수 입력의 BW6·PSD 계산

2026-10-24, Asia/Seoul. 사용자 연속 개발 위임에 따라 총괄이 고정한다. P01의 DEV-VIRTUAL-METHODS-004-EVIDENCE v1과 S01 보충 metadata를 해시 인수했다. 제한 원문·보고서 수치를 Git에 복제하지 않는다.

## 목적과 선택

기존 N1911A/N1921A 시간 envelope·스칼라를 RF spectrum으로 간주하지 않는다. 첫 단위는 **명시적 합성 주파수 입력의 순수 계산 API**다. 제조사 trace 명령을 추가하거나 기존 DUT scalar에서 존재하지 않는 spectrum을 생성하는 방법은 보유 계약을 넘으므로 선택하지 않는다. 다음 단위에서 별도 가상 관측·하네스와 연결한다.

개발3 소유 신규 `labflow/virtual_fleet/spectrum_math.py`, 전용 tests/usage만 변경한다. 기존 역할·catalog·runtime·sensor adapter·harness·공개 v1 result는 변경하지 않는다. 기능 통합 전용 새 codex 브랜치를 사용한다.

```python
analyze_6db_bandwidth(trace) -> dict
analyze_psd_band(sample) -> dict
```

두 함수는 파일/DB/네트워크/시각/장비/AI 부작용이 없는 순수 계산이다. 원본 입력 객체를 변경하지 않는다. 잘못된 schema/자료형/비유한/범위/미지원 입력은 정제된 ValueError로 거절한다. 유효한 입력의 잘린 교차·애매한 peak는 숫자를 추정해 채우지 않는다.

## BW6 입력과 계산

trace의 정확한 키:

`schema_version=1`, `kind="synthetic_frequency_spectrum"`, `capture_id`, `synthetic=true`, `axis_domain="frequency_offset_hz"`, `sample_unit="dB"`, `amplitude_basis="relative_to_peak"`, `selection_policy="unique_peak_single_lobe_linear_db"`, `frequency_offsets_hz`, `relative_levels_db`.

capture_id는 기존 128자 공개 ID 규칙, 두 배열은 같은 길이의 3~65536개 유한한 숫자(bool 제외)다. 축은 엄격 증가하며 max level=0이다. 시간축·스칼라·미상 단위·자동 정렬·삭제·외삽은 허용하지 않는다.

유일한 peak를 둘러싼 -6dB 이상의 연결 성분의 좌우 교차를 구한다. 두 교차가 bin 사이면 **dB 대 Hz의 선형 보간**을 사용한다. 정확한 -6dB 한 점은 교차로 쓴다. 유일하지 않은 최대 peak, 분리된 -6dB 이상 lobe 또는 -6dB plateau는 `incomplete`로 남기고 숫자를 비운다. trace 양끝까지 교차가 포함되지 않으면 `incomplete`다. 이 선택/보간 정책은 합성 모델이며 제조사 또는 현행 규범 방법 승인이 아니다.

결과 정확한 키: `schema_version=1`, `kind="synthetic_bandwidth_result"`, `capture_id`, `input_sha256`, `algorithm_id="peak6_linear_db_v1"`, `status="complete|incomplete"`, `reason_codes`, `left_offset_hz`, `right_offset_hz`, `bandwidth_hz`, `minimum_bandwidth_hz=500000`, `margin_hz`, `conditional_comparison="meets|below" 또는 null`, `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `method_approval="not_assessed"`, `regulatory_scope_complete=false`.

incomplete의 교차/폭/margin/comparison은 모두 null이다. complete의 폭은 우측−좌측이고 500000 이상일 때만 선언 경계 `meets`다. 입력 hash는 정렬 key·UTF-8·유한 JSON의 canonical SHA-256이다. 입력 변경을 숨기지 않는다.

incomplete reason_codes 순서는 `non_unique_peak`, `disconnected_lobes`, `threshold_plateau`, `left_crossing_missing`, `right_crossing_missing`로 고정한다. 유한 입력에서도 중간 연산/폭이 overflow하거나 양의 폭을 표현하지 못하면 정제된 `ValueError("numeric_result_out_of_range")`로 거절한다.

## PSD 입력과 계산

sample의 공통 정확한 키: `schema_version=1`, `kind="synthetic_psd_input"`, `capture_id`, `synthetic=true`, `reference_plane="dut_output"`, `time_basis="on_interval"`, `output_power_method`, `psd_power_method`, `path_correction_state="already_applied"`, `input_basis`와 아래 값 키 한 개다.

- `input_basis="band_power_3khz"`: `power_dbm` 유한 숫자 -300~100. 0dBm은 1mW이며 누락/무송신으로 취급하지 않는다.
- `input_basis="flat_density_mw_per_hz"`: `density_mw_per_hz`는 유한한 양수이며 3000Hz로 적분한 양도 유한한 양수여야 한다. 전체 선택 구간에서 일정한 밀도와 직사각형 적분 구간을 선언한 합성 모델에만 쓴다.

두 method는 같은 `on_mean` 또는 `peak`여야 한다. cycle/미상 duty·추가 duty 보정·미상 기준면·미적용 경로보정·SA amplitude/RBW·겹치는 bin·미상 ENBW는 이 API의 지원 입력이 아니다. 미지원 추가 키도 거절한다. 실제 trace에 `10log10(3000/RBW)`를 추정 적용하지 않는다.

결과 정확한 키: `schema_version=1`, `kind="synthetic_psd_band_result"`, `capture_id`, `input_sha256`, `algorithm_id="declared_3khz_power_v1"`, `input_basis`, `power_dbm`, `power_mw`, `reference_bandwidth_hz=3000`, `maximum_dbm=8`, `margin_db`, `conditional_comparison="meets|above"`, `source_coverage="single_declared_band"`, `max_search_complete=false`, `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `method_approval="not_assessed"`, `regulatory_scope_complete=false`.

밀도 입력은 P[mW]=밀도×3000, P[dBm]=10log10(P[mW])다. margin=8−P[dBm]이고 8 이하일 때 선언 경계 `meets`다. 한 구간의 수치 비교는 전대역 최대 탐색이나 제품 적합 판정이 아니다.

## 근거와 수용

500kHz/8dBm은 P01이 보유 2026-10-19 규정 snapshot과 연결한 조건부 비교값이다. KDB의 2013판 참조와 2020 상세 절차/정정/crosswalk 공백을 보존하며 현행 전체 방법을 승인했다고 표시하지 않는다.

BW 정확 경계·보간·clipping·복수 peak/lobe·plateau·축/단위/비유한 거절, PSD 0dBm·8dBm 경계·밀도 환산·method mismatch·cycle/중복보정·미상RBW 거절을 검사한다. 큰 숫자의 중간 overflow와 입력 불변성/공개 JSON 유한성도 확인한다. 담당 커밋→독립 리뷰/수정→총괄 인수 뒤 관측·하네스·화면 연결을 다음 작은 단위로 배정한다. 사용자 추가 준비물은 없다.
