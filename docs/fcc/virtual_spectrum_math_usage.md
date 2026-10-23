# 합성 주파수 입력의 BW6·3 kHz PSD 계산

2026-10-24, Asia/Seoul. SPECTRUM-004A 개발3.

`labflow.virtual_fleet.spectrum_math`는 명시한 합성 입력만 계산한다. 기존 N1911A/N1921A 시간 envelope나 DUT·센서 스칼라에서 RF spectrum을 만들지 않는다. 파일·DB·네트워크·시계·장비·AI를 사용하지 않으며 입력 객체를 변경하지 않는다. 표준 라이브러리 외 의존성은 없다.

```python
from labflow.virtual_fleet.spectrum_math import (
    analyze_6db_bandwidth, analyze_psd_band,
)
```

## BW6 입력

```python
trace = {
    "schema_version": 1,
    "kind": "synthetic_frequency_spectrum",
    "capture_id": "synthetic-bw-1",
    "synthetic": True,
    "axis_domain": "frequency_offset_hz",
    "sample_unit": "dB",
    "amplitude_basis": "relative_to_peak",
    "selection_policy": "unique_peak_single_lobe_linear_db",
    "frequency_offsets_hz": [-250000, 0, 250000],
    "relative_levels_db": [-6, 0, -6],
}
result = analyze_6db_bandwidth(trace)
assert result["status"] == "complete"
assert result["bandwidth_hz"] == 500000
assert result["margin_hz"] == 0
assert result["conditional_comparison"] == "meets"
```

위 10개 키를 정확히 받는다. 배열은 같은 길이의 Python list이며 3~65536개의 유한한 int/float를 받는다. bool·문자열 수치·tuple·비유한 값은 받지 않는다. 주파수 offset은 입력 순서대로 엄격 증가해야 하고 최대 상대 level은 정확히 0이어야 한다. 자동 정렬·누락 삭제·최대값 정규화·시간축 변환을 수행하지 않는다.

capture_id는 ASCII 문자/숫자로 시작하는 최대 128자의 문자·숫자·`_.:-`다. 공개 ID만 사용하며 경로나 원본 문서를 넣지 않는다.

유일한 최대 peak를 포함하는 −6 dB 이상의 연결 성분을 찾는다. 그 성분의 좌우 끝이 정확히 −6 dB이면 해당 주파수를 그대로 쓴다. 아니면 인접한 바깥 bin과 dB 대 Hz의 선형 보간을 사용한다. 양 끝 bin이 정확히 −6 dB인 입력은 교차를 포함한 것으로 인정한다.

폭은 반올림하지 않은 우측 교차−좌측 교차, margin은 그 폭−500000 Hz다. 계산된 폭이 500000 Hz 이상일 때만 이 선언 경계의 conditional_comparison이 meets이고, 작으면 below다. complete는 계산 가능 상태이며 제품 적합 판정이 아니다.

모호성은 다음 순서로 reason_codes에 기록한다. 앞의 모호성 3종이 있으면 특정 성분을 선택하지 않고 반환한다.

| 코드 | 의미 |
|---|---|
| non_unique_peak | 최대 상대 level 0인 bin이 여러 개 |
| disconnected_lobes | −6 dB 이상인 성분이 분리됨 |
| threshold_plateau | 인접한 두 bin 이상이 정확히 −6 dB |
| left_crossing_missing | 선택 가능한 단일 성분의 좌측 교차가 잘림 |
| right_crossing_missing | 선택 가능한 단일 성분의 우측 교차가 잘림 |

incomplete이면 left_offset_hz, right_offset_hz, bandwidth_hz, margin_hz, conditional_comparison은 모두 null이다. 교차 하나만 있더라도 부분 수치를 게시하거나 외삽하지 않는다.

BW 반환 키는 정확히 다음 18개다.

```text
schema_version kind capture_id input_sha256 algorithm_id status reason_codes
left_offset_hz right_offset_hz bandwidth_hz minimum_bandwidth_hz margin_hz
conditional_comparison synthetic hardware_verified ai_model_called
method_approval regulatory_scope_complete
```

kind는 synthetic_bandwidth_result, algorithm_id는 peak6_linear_db_v1, minimum_bandwidth_hz는 500000이다.

## PSD 입력

이미 경로 보정한 DUT 출력의 ON 구간에서 명시한 3 kHz 구간 전력을 계산한다.

```python
sample = {
    "schema_version": 1,
    "kind": "synthetic_psd_input",
    "capture_id": "synthetic-psd-1",
    "synthetic": True,
    "reference_plane": "dut_output",
    "time_basis": "on_interval",
    "output_power_method": "on_mean",
    "psd_power_method": "on_mean",
    "path_correction_state": "already_applied",
    "input_basis": "band_power_3khz",
    "power_dbm": 0,
}
result = analyze_psd_band(sample)
assert result["power_mw"] == 1
assert result["margin_db"] == 8
assert result["conditional_comparison"] == "meets"
assert result["max_search_complete"] is False

flat = dict(sample)
del flat["power_dbm"]
flat["input_basis"] = "flat_density_mw_per_hz"
flat["density_mw_per_hz"] = 0.002
density_result = analyze_psd_band(flat)
assert density_result["power_mw"] == 6
# 7.781512503836437 dBm, 선언한 8 dBm 경계보다 낮음.
```

공통 10키와 basis별 값 키 하나만 받는다. output_power_method와 psd_power_method는 같은 on_mean 또는 같은 peak여야 한다.

| input_basis | 값 키·범위 | 계산 |
|---|---|---|
| band_power_3khz | power_dbm, 유한 숫자 −300~100 | P[mW] = 10^(P[dBm]/10) |
| flat_density_mw_per_hz | density_mw_per_hz, 유한 양수 | P[mW] = density×3000, P[dBm] = 10log10(P[mW]) |

0 dBm은 1 mW다. 누락이나 무송신으로 바꾸지 않는다. 밀도 basis는 선택한 3000 Hz 직사각형 구간 전체가 일정한 밀도라는 명시적 합성 모델이다. 적분 전력도 유한 양수여야 한다. 직접 전력 입력의 −300~100 dBm 범위는 밀도 입력의 계산 결과에 추가 적용하지 않는다.

margin_db는 표시 float로 반올림하기 전 계산 전력[dBm]을 8에서 뺀 값이다. 전력이 8 dBm 이하이면 meets, 초과하면 above다. 허용오차를 추가하거나 반올림한 표시값으로 경계를 비교하지 않는다.

cycle 평균·미상 duty·method 불일치·다른 기준면·미적용 보정·추가 duty/손실 보정은 받지 않는다. RBW·ENBW·SA amplitude·겹치는 bin·RF trace를 추가 키로 넣어도 거절한다. `10log10(3000/RBW)`를 추정 적용하지 않는다.

PSD 반환 키는 정확히 다음 19개다.

```text
schema_version kind capture_id input_sha256 algorithm_id input_basis power_dbm
power_mw reference_bandwidth_hz maximum_dbm margin_db conditional_comparison
source_coverage max_search_complete synthetic hardware_verified ai_model_called
method_approval regulatory_scope_complete
```

kind는 synthetic_psd_band_result, algorithm_id는 declared_3khz_power_v1, reference_bandwidth_hz는 3000, maximum_dbm은 8이다. source_coverage는 single_declared_band, max_search_complete는 false다. 한 구간의 비교로 전대역 최대 탐색을 완료했다고 표시하지 않는다.

## 출처·오류·수용 경계

두 결과는 schema_version=1, synthetic=true, hardware_verified=false, ai_model_called=false, method_approval=not_assessed, regulatory_scope_complete=false를 유지한다.

input_sha256는 원본 입력의 key 정렬·UTF-8·유한 JSON·공백 없는 구분자로 계산한 SHA-256이다. 객체 key 순서는 hash를 바꾸지 않지만 0과 0.0 같은 선언 표현 차이는 보존한다. 호출자가 반환 dict를 변경해도 입력이나 다음 호출 결과를 변경하지 않는다. 이 API는 입력을 저장하지 않으며 hash는 서명이나 실측 증명이 아니다.

잘못된 schema/자료형/값/범위/미지원 입력은 원시 입력을 포함하지 않는 ValueError(invalid_spectrum_input 또는 invalid_psd_input)로 거절한다. 계산 중간/결과가 overflow하거나 아래 수치 표현 조건을 만족하지 못하면 ValueError(numeric_result_out_of_range)다. 잘린 교차·모호한 peak의 incomplete/null과 숫자 표현 오류를 구별한다.

### 계산 정밀도

int와 Python float가 실제로 표현한 수를 정확한 유리수로 받아 BW 교차·폭·margin과 밀도 적분 전력을 계산한다. float를 문자열의 짧은 십진수로 다시 해석하지 않는다. 공개 수치는 유한한 int/float이며 내부의 정확한 수와 마지막 표시 반올림을 구별한다.

BW는 정확한 유리수 폭으로 경계를 비교한다. 공개 교차들의 차이가 정확한 폭과 폭 표시값의 1 ULP(인접 float 사이 간격)를 넘게 다르거나, 표시 교차/폭으로 비교한 경계가 정확한 비교와 달라지면 거절한다. 양의 폭 소실과 overflow도 거절한다. 이 1 ULP는 **출력 표현의 거절 기준**이며 경계에 허용하는 초과량이 아니다.

예를 들어 offset `[1e20-1048576, 1e20, 1e20+1048576]`과 level `[-25.17, 0, -25.17]`은 입력 float의 정확한 폭이 약 499917.0441 Hz다. 큰 절대 좌표를 float 교차로 표시하면 차이가 507904 Hz가 되므로 numeric_result_out_of_range로 거절한다. 숫자 크기를 줄인 같은 상대 형태는 below다.

밀도 PSD는 반올림하지 않은 적분 전력에 대해 독립된 Decimal 문맥에서 80~1280자리 유효숫자로 로그의 상·하한을 계산한다. 올바르게 반올림되는 연산과 인접 Decimal 값을 이용해 정확한 값을 포함하는 구간을 만들고, 그 구간이 8 dBm의 어느 쪽인지와 표시 전력·margin의 float 반올림이 확정될 때만 반환한다. 확정하지 못하면 숫자 표현 오류다. 계산은 호출자의 Decimal 정밀도·반올림·trap 설정에 영향을 받지 않으며 호출 후 기존 설정을 보존한다.

따라서 power_dbm 표시가 8.0이어도 unrounded 값이 8을 초과하면 margin_db는 음수이고 conditional_comparison은 above다. 밀도 `0.002103191148267311` mW/Hz가 그 예로, 입력 float에 대한 계산은 약 8.0000000000000005622 dBm이며 margin은 약 −5.6220e−16 dB다. 표시값 `8−8.0`으로 margin이나 비교를 재계산하지 않는다. 정확한 경계 예제는 직접 band_power_3khz의 power_dbm=8이며 margin=0/meets다.

500 kHz·8 dBm은 총괄이 인수한 규정 snapshot 근거와 연결한 조건부 비교값이다. 이 합성 보간·밀도 모델을 제조사 방법이나 현행 전체 규범 방법 승인으로 표시하지 않는다. 원문·보고서 실측값·제한 metadata는 복제하지 않았다. 기존 runtime/catalog/method adapter/harness/공개 v1 result도 변경하지 않았다.

```text
.venv\Scripts\python.exe -B -m unittest tests.test_virtual_fleet_spectrum_math -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B scripts/check_artifacts.py
```

전용 검사는 BW 경계·불규칙 bin 보간·잘림·복수 peak/lobe·plateau·65536 bin·큰 수·입력 불변성, PSD 0/8 dBm·범위·밀도 환산·불일치/중복 보정 거절·최소 양수·적분 overflow 및 함수 호출의 파일/DB/네트워크/시계 부작용 부재를 확인한다. 이 단계는 순수 계산이며 실제 RF 관측·가상 runtime 연결·AI·실장비·현장·현행 전체 방법 검증은 후속 범위다.
