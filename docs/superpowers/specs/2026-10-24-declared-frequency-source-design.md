# SPECTRUM-SOURCE-005 — 명시 주파수 전력밀도 source와 3kHz 적분

2026-10-24, Asia/Seoul. 현재 RF 역할은 전력/대역폭 scalar를 전달한다. 다음 실제 구현은 명시한 밀도 함수를 생성·적분하는 별도 순수 source다. 기존 scalar·공칭 bandwidth·mode 이름에서 주파수 곡선을 추정하지 않는다.

## 선택과 소유

공칭20MHz나 보고서 rate/MCS에서 파형을 만들어내는 방법은 현재 근거보다 강한 주장이다. 원본 실측 trace를 복사하면 합성 모델과 실측을 섞는다. 총괄은 호출자가 별도 선언한 **선형 전력밀도 곡선**을 source로 구현하고 실제 역할/경로/하네스 접속을 다음 단위로 분리한다.

개발3은 신규 `labflow/virtual_fleet/frequency_source.py`, `tests/test_virtual_fleet_frequency_source.py`, `docs/fcc/virtual_frequency_source_usage.md` 세 파일만 소유한다. 기존 rf/instruments/core/catalog/capture/math/harness/journal을 변경하지 않는다.

```python
generate_frequency_source(spec) -> dict
integrate_source_3khz(spec, *, start_offset_hz) -> dict
```

I/O·DB·clock·random·네트워크·runtime·장비·모델 호출이 없는 순수 API다. 입력을 독립 JSON snapshot으로 고정하고 출력도 별칭을 공유하지 않는다. UTF-8 canonical spec은 최대4MiB/기존 depth32 한도이며 유한 JSON만 허용한다. 식별자는 ASCII [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}이다.

## Source 입력

spec exact12키는 schema_version=1, kind=synthetic_piecewise_density_source, source_id, declared_mode_id, synthetic=true, center_hz, reference_plane=dut_output, time_basis=on_interval, power_method(on_mean|peak), interpolation=linear_mw_per_hz, frequency_offsets_hz, density_mw_per_hz다. 별도 암묵 필드는 없다. center_hz는 유한한 양수, 두 배열은 같은 길이의 3..4096 유한 int/float다. bool은 숫자로 허용하지 않는다. offset은 엄격 증가, density는 엄격한 양수, 각 center+offset도 표현 가능한 유한 양수여야 한다. 자동 정렬·noise floor·정규화·외삽은 없다. 정의 구간 밖 밀도를 0으로 가정하지 않는다.

declared_mode_id는 호출자가 선택한 별도 DUT mode 선언의 공개 참조다. DUT006의 Peak/PSD 대 Average rate·MCS·채널/중심주파수 같은행 결합과 미확정 null은 호출자/host에서 보존한다. source 모듈에 private 보고서 표를 내장하거나 ID에서 HT20/NSS/OEM/FW·곡선·전력을 도출하지 않는다. 현재 mode 이름이 실제 DSSS/OFDM 파형을 구현했다는 뜻은 아니다.

## 생성 출력

generate 결과 exact 키는 schema_version=1, kind=synthetic_frequency_source, source_id, declared_mode_id, input_sha256, center_hz, reference_plane, time_basis, power_method, density_interpolation=linear_mw_per_hz, trace_projection=knot_samples_linear_db, trace와 아래 공통7 flags다.

공통 flags는 synthetic=true, hardware_verified=false, ai_model_called=false, method_approval=not_assessed, regulatory_scope_complete=false, waveform_implemented=false, oem_mode_verified=false다. input_sha256는 원래 spec 전체의 canonical JSON SHA-256이다.

trace는 기존 synthetic_frequency_spectrum exact 입력이다. capture_id는 `fs:`+input_sha256, offset은 원래 knot 전부, relative_levels_db는 10log10(S/Smax)다. max는 정확한0, 나머지는 유한한 비양수이며 밀도 비를 먼저 float 나누어 underflow하지 않는다. 독립 Decimal 문맥으로 caller precision/traps/flags를 보존한다. 계산 불가·구별 소실은 고정 numeric_result_out_of_range로 거절하고 거짓0이나 임의 floor로 바꾸지 않는다. 여기서 BW6는 **knot 샘플의 dB 선형 보간** 결과이며 선형 밀도 함수의 해석적 폭이라고 표시하지 않는다. source 생성은 BW 판정을 호출하지 않는다.

## 3kHz 적분 출력

start_offset_hz는 bool 아닌 유한 숫자다. 실제 JSON int/float를 Fraction으로 보존하고 [start,start+3000]이 정의 구간 안에 완전히 포함될 때만 실행한다. 각 교차 구간에서 density를 선형 보간해 (S(a)+S(b))*(b-a)/2를 정확히 더한다. mean/peak·duty/crest·경로보정을 변환하지 않는다.

결과 exact 키는 schema_version=1, kind=synthetic_integrated_band_power, source_id, declared_mode_id, input_sha256, start_offset_hz, stop_offset_hz, reference_bandwidth_hz=3000, reference_plane, time_basis, power_method, power_mw, exact_power_ratio, source_coverage=single_declared_band, max_search_complete=false와 공통7 flags다. exact_power_ratio는 numerator/denominator의 양의 십진 정수 문자열이며 기약분수다. power_mw는 그 유한 양수 float 표기이며 정확 판정의 근거는 ratio다. stop의 표기로 3kHz가 붕괴하거나 공개 endpoint 차이가3000Hz의1ULP보다 다르면 numeric_result_out_of_range로 거절한다. 이는 표현 가능성 guard이며 pass 허용오차가 아니다.

이 단위는 PSD 비교 enum·dBm·전대역 최대값을 만들지 않는다. 다음 ratio-aware PSD 연결에서 반올림 전 정확 전력을 소비한다. 현재 analyze_psd_band의 임의 float 입력에 ratio를 몰래 끼워 넣지 않는다.

## 수용과 후속

독립 Fraction oracle로 평탄/삼각/비대칭, knot를 가로지르는3kHz·끝점 포함·부분 구간 가산성·구간 분할 불변·밀도 배율 비례·주파수 평행이동 불변을 검사한다. 입력/출력 별칭·hash/float표현·한도·overflow·context 보존·모드 ID에서 추론0·부작용0을 확인한다. generate→기존 BW 계산의 정상/복수 peak/잘림과 밀도 선형 대 dB 선형의 구별도 검증한다.

독립 검토/소유 수정/총괄 통합 뒤 실제 역할의 frequency 출력·경로 손실·ratio-aware PSD·하네스/화면으로 연결한다. 구현하는 것은 선언 밀도 함수와 제한 구간 적분이다. DSSS/OFDM I/Q·시간 파형·OEM 시험모드·계측기 RBW/ENBW 응답·물리/규범 방법 검증은 미구현이며 완료로 표시하지 않는다. 현재 사용자 추가 자료/계정은 없다.
