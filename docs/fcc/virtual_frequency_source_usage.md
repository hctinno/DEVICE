# 명시 주파수 밀도 source와 정확한 3 kHz 적분

2026-10-24, Asia/Seoul. SPECTRUM-SOURCE-005 개발3.

별도로 선언한 선형 전력밀도 함수를 생성·적분하는 순수 API다. 기존 RF scalar·공칭 대역폭·mode 이름·보고서 표에서 곡선을 만들지 않는다. 기존 rf/instruments/core/catalog/capture/math/harness/journal도 변경하지 않는다.

```python
from labflow.virtual_fleet.frequency_source import (
    generate_frequency_source, integrate_source_3khz,
)

spec = {
    "schema_version": 1,
    "kind": "synthetic_piecewise_density_source",
    "source_id": "declared-source-1",
    "declared_mode_id": "declared-mode-1",
    "synthetic": True,
    "center_hz": 2450000000,
    "reference_plane": "dut_output",
    "time_basis": "on_interval",
    "power_method": "on_mean",
    "interpolation": "linear_mw_per_hz",
    "frequency_offsets_hz": [-3000, 0, 6000],
    "density_mw_per_hz": [1 / 1024, 1 / 1024, 1 / 1024],
}
generated = generate_frequency_source(spec)
band = integrate_source_3khz(spec, start_offset_hz=-1000)
assert generated["trace"]["relative_levels_db"] == [0, 0, 0]
assert band["power_mw"] == 2.9296875
assert band["exact_power_ratio"] == {"numerator": "375", "denominator": "128"}
```

## 입력 exact 12키

위 예제의 12키를 정확히 받는다. source_id와 declared_mode_id는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`다. power_method는 on_mean 또는 peak, 나머지 고정 문자열/flag는 예제와 같아야 한다.

center_hz는 유한 양수다. 두 배열은 같은 길이의 list이며 3~4096개의 유한 int/float를 받는다. bool·문자열 수치·tuple은 허용하지 않는다. offset은 이미 엄격 증가해야 하고 density는 모두 양수다. 각 center+offset도 유한 양수로 표현할 수 있어야 한다. 자동 정렬·noise floor·정규화·외삽은 수행하지 않으며 정의 구간 밖의 밀도를 0으로 가정하지 않는다.

spec은 key 정렬·UTF-8·유한 compact JSON의 독립 사본으로 고정한다. canonical 크기는 4 MiB 이하, 깊이는 기존 공개 JSON 규칙의 32 이하다. 문자열 key의 dict/list와 JSON scalar만 받고 순환·깨진 UTF-8·비유한 수·임의 Python 객체는 거절한다. 입력이나 반환 객체를 수정해도 서로 또는 다음 호출 결과를 변경하지 않는다.

declared_mode_id는 host가 별도로 선언한 DUT mode의 공개 참조다. 이 모듈은 ID를 속도·대역폭·NSS·파형·OEM/FW 지원으로 해석하지 않는다. 보고서의 같은행 mode/rate/MCS/channel/중심주파수 결합과 미확정 null은 host가 보존한다. source 제품에는 private 보고서 표나 실측값을 내장하지 않는다. 합성 대역폭·NSS·파형 선택도 보고 사실의 빈칸을 채우는 기본값으로 쓰지 않는다.

## 생성: dB knot projection

generate_frequency_source의 정확한 19키는 다음과 같다.

```text
schema_version kind source_id declared_mode_id input_sha256 center_hz
reference_plane time_basis power_method density_interpolation trace_projection trace
synthetic hardware_verified ai_model_called method_approval regulatory_scope_complete
waveform_implemented oem_mode_verified
```

kind는 synthetic_frequency_source, density_interpolation은 linear_mw_per_hz, trace_projection은 knot_samples_linear_db다.

trace는 [기존 BW 입력](virtual_spectrum_math_usage.md)의 exact 10키다. capture_id는 fs: 뒤에 원래 spec 전체의 canonical SHA-256을 붙인 값이다. offset은 원래 knot를 모두 보존하며 level은 10log10(S/Smax)다. 최대 밀도는 정확히 0 dB, 나머지는 유한 음수다.

실제 입력 int/float를 Fraction으로 보존한다. 밀도 비를 float로 먼저 나누지 않으므로 극단적인 비율의 underflow로 임의 floor를 만들지 않는다. 독립 Decimal 문맥에서 올바르게 반올림되는 연산과 인접 값으로 로그의 상·하한을 만들고, 양쪽이 같은 표시 float를 확정할 때 반환한다. 호출자의 precision/rounding/trap/flags를 보존한다.

서로 다른 정확한 밀도가 같은 표시 float level로 합쳐지면 numeric_result_out_of_range로 거절한다. 원래 같은 밀도의 반복/plateau는 허용한다. 비최대 밀도가 가짜 0 dB peak로 바뀌는 것도 허용하지 않는다.

생성은 BW 판단을 호출하지 않는다. 호출자가 생성 trace를 BW 함수로 전달할 수 있다. 이때 BW6는 **dB knot 샘플의 선형 보간**이다. 선형 밀도 함수의 해석적 −6 dB 폭과 같다고 표시하지 않는다.

예를 들어 offset `[-1000000, 0, 1000000]`, density `[0.1, 1, 0.1]`의 표시 knot level은 `[-10, 0, -10]`이며 기존 BW 계산은 1200000 Hz를 반환한다. 이 교차 위치의 선형 밀도는 약 0.46으로 −6 dB 밀도와 다르다. 평탄한 source나 잘린 구간의 BW incomplete도 그대로 유지한다.

## 적분: 정확한 한 구간 전력

integrate_source_3khz의 정확한 22키는 다음과 같다.

```text
schema_version kind source_id declared_mode_id input_sha256 start_offset_hz stop_offset_hz
reference_bandwidth_hz reference_plane time_basis power_method power_mw exact_power_ratio
source_coverage max_search_complete synthetic hardware_verified ai_model_called
method_approval regulatory_scope_complete waveform_implemented oem_mode_verified
```

kind는 synthetic_integrated_band_power, reference_bandwidth_hz는 3000, source_coverage는 single_declared_band, max_search_complete는 false다.

start_offset_hz는 bool을 제외한 유한 숫자다. 정확한 [start, start+3000] 전체가 정의 구간에 포함되어야 한다. 끝점은 포함하지만 작은 초과도 clipping·외삽하거나 밀도 0으로 채우지 않는다. 각 교차 segment에서 밀도를 선형 보간하고 `(S(a)+S(b))×(b−a)/2`를 Fraction으로 정확히 더한다.

exact_power_ratio는 양의 십진 정수 문자열 numerator/denominator를 가진 기약분수다. power_mw는 유한한 양수 float 표시다. 후속 정확 판정의 근거는 ratio이며 표시 power_mw를 다시 정확값으로 승격하지 않는다. 이 API는 PSD 비교 enum·dBm·전대역 최대값을 만들지 않는다.

start는 원래 JSON int/float를 보존한다. int의 stop은 정확한 int+3000이고, float의 stop은 정확한 Fraction endpoint를 float로 표시한다. 공개 endpoint도 Fraction으로 비교한다. 폭이 사라지거나 3000 Hz와의 차이가 3000의 1 ULP(인접 float 간격)를 넘으면 numeric_result_out_of_range다. 정수 endpoint를 float로 낮추지 않는다. 이 guard는 표현 오류의 거절 기준이며 비교를 통과시키는 허용오차가 아니다. 실제 적분은 항상 표시 전 정확한 endpoint를 사용한다.

mean/peak·duty/crest·경로 보정을 자동 변환하지 않는다. 현재 scalar PSD API에 ratio를 몰래 추가하지도 않는다. ratio-aware PSD 소비와 역할/경로 연결은 다음 단위다.

## 오류·출처·검사

두 결과는 synthetic=true, hardware_verified=false, ai_model_called=false, method_approval=not_assessed, regulatory_scope_complete=false, waveform_implemented=false, oem_mode_verified=false의 공통 7 flags를 유지한다.

입력/JSON/선언 범위 오류는 원시 값을 포함하지 않는 ValueError(invalid_frequency_source), 잘못된 start나 불완전한 포함 구간은 ValueError(invalid_frequency_interval)다. 계산·표시 불가/밀도 구별 소실·overflow는 ValueError(numeric_result_out_of_range)다. 원본 입력의 hash를 유지하며 caller 객체를 변경하지 않는다.

```text
.venv\Scripts\python.exe -B -m unittest tests.test_virtual_fleet_frequency_source -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B scripts/check_artifacts.py
```

[전용 검사](../../tests/test_virtual_fleet_frequency_source.py)는 독립 slope/intercept 원시함수 적분 oracle로 평탄/삼각/비대칭·knot 교차, 경계 포함/초과 거절, 구간 가산성·segment 분할·밀도 배율·주파수 이동 불변성을 확인한다. 비율 underflow/가짜 peak/표시 구별 소실·최소 양수·정수 endpoint/폭 소실·유한성/크기·hash/별칭·Decimal 문맥·부작용0도 검사한다.

새로 선언한 밀도 함수와 제한 구간 적분만 구현했다. DSSS/OFDM I/Q·시간 파형·OEM 시험모드·실제 역할의 frequency 출력·경로 손실·RBW/ENBW 응답·하네스/화면 연결·실장비/현장/규범 방법 검증은 후속 범위다.
