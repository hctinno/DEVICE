# 정확한 source 적분의 단일 구간 PSD 비교

2026-10-24 · Asia/Seoul. SPECTRUM-PSD-007 개발3. 기존 [명시 밀도 source](virtual_frequency_source_usage.md)의 정확한 3 kHz 적분을 사용하는 순수 계산 API다. 기존 [스칼라 PSD/BW API](virtual_spectrum_math_usage.md)·source·capture·역할·엔진·UI를 변경하지 않는다.

```python
from labflow.virtual_fleet.frequency_source import (
    generate_frequency_source, integrate_source_3khz,
)
from labflow.virtual_fleet.frequency_psd import analyze_source_psd

spec = {
    'schema_version': 1,
    'kind': 'synthetic_piecewise_density_source',
    'source_id': 'declared-psd-1',
    'declared_mode_id': 'declared-mode-1',
    'synthetic': True,
    'center_hz': 2450000000,
    'reference_plane': 'dut_output',
    'time_basis': 'on_interval',
    'power_method': 'on_mean',
    'interpolation': 'linear_mw_per_hz',
    'frequency_offsets_hz': [-5000, 0, 5000],
    'density_mw_per_hz': [1 / 1024, 1 / 1024, 1 / 1024],
}
generated = generate_frequency_source(spec)
band = integrate_source_3khz(spec, start_offset_hz=-1000)
result = analyze_source_psd(spec, start_offset_hz=-1000)
assert result['exact_power_ratio'] == {'numerator': '375', 'denominator': '128'}
assert result['exact_power_ratio'] == band['exact_power_ratio']
assert result['input_sha256'] == generated['input_sha256'] == band['input_sha256']
assert result['conditional_comparison'] == 'meets'
assert result['max_search_complete'] is False
```

`analyze_source_psd(spec, *, start_offset_hz) -> dict`는 기존 `integrate_source_3khz`를 정확히 한 번 호출한다. spec의 정확한 12키·형식·원래 int/float 값·완전한 구간 포함·정확 적분은 기존 source 계약을 그대로 사용한다. power_mw 표시를 다시 정확값으로 해석하거나, 생성된 trace의 dB 샘플을 전력으로 재적분하지 않는다. 생성·기존 스칼라 PSD 함수를 대신 호출하지 않는다.

## 정확한 비교와 별도 표시

양의 기약분수 전력 `P=a/b`의 단위는 mW다. 선언 한계는 **8 dBm/3 kHz**이며, `10 log10(P) <= 8`과 `a**5 <= 10000 * b**5`는 동치다. 이 정수 비교만으로 conditional_comparison을 고른다.

- `meets`: 해당 선언 구간의 전력이 8 dBm 이하
- `above`: 해당 선언 구간의 전력이 8 dBm 초과

float power_mw·표시 power_dbm·margin·epsilon은 이 비교에 사용하지 않는다. 이 enum은 단일 합성 구간의 조건부 비교이며 제품 적합 판정이나 최대 PSD 결과가 아니다.

power_dbm과 margin_db는 별도의 독립 Decimal 문맥에서 계산한다. 80/160/320/640/1280자리 정밀도로 나눗셈·log10·10배·`8−log값`의 상·하한을 인접 Decimal 값으로 감싼다. 두 경계가 같은 유한 float로 반올림되는 경우만 표시한다. margin은 표시 dBm에서 빼지 않고 원래 로그 구간에서 계산한다. 호출자의 precision/rounding/Emin/Emax/clamp/traps/flags를 변경하지 않는다.

정확히 1 mW인 경우 power_dbm=0.0, margin_db=8.0이다. 그 밖의 비영 dBm 또는 margin이 float에서 0으로 사라지거나, 표시를 최대 정밀도 내에서 확정하지 못하면 numeric_result_out_of_range다. 허용되지 않는 표현을 0·8·meets로 채우지 않는다.

실제 source 입력에서 평탄 밀도 `0.002103191148267311` mW/Hz와 그 바로 아래 인접 float는 모두 power_dbm 표시가 8.0이다. 전자는 above와 음수 margin, 후자는 meets와 양수 margin을 반환한다. 동일한 float power_mw까지 공유하는 서로 다른 정확 ratio도 정수 비교로 구분한다. 후자의 극단 경계 검사는 단위 테스트의 명시적인 source 반환 주입이며 실제 source 출력 증거와 구분한다.

## 정확한 반환 29키

```text
schema_version kind source_id declared_mode_id input_sha256
start_offset_hz stop_offset_hz reference_bandwidth_hz reference_plane time_basis power_method
power_mw exact_power_ratio source_coverage max_search_complete
synthetic hardware_verified ai_model_called method_approval regulatory_scope_complete
waveform_implemented oem_mode_verified
algorithm_id input_basis comparison_basis power_dbm maximum_dbm margin_db conditional_comparison
```

kind만 `synthetic_source_psd_band_result`로 바꾸고 source 적분의 나머지 21필드와 ratio 문자열을 그대로 보존한다. 다음 7필드를 추가한다.

| 필드 | 값/의미 |
|---|---|
| algorithm_id | exact_source_3khz_psd_v1 |
| input_basis | exact_integrated_power_ratio |
| comparison_basis | exact_integer_fifth_power |
| power_dbm | 정확한 적분 전력의 로그를 별도 반올림한 유한 float |
| maximum_dbm | int 8 |
| margin_db | `8−정확 로그값`을 별도 반올림한 유한 float |
| conditional_comparison | meets 또는 above |

source_id/declared_mode_id/원 spec의 canonical input_sha256, start/stop의 원래 int·float 형식, reference_bandwidth_hz=3000, reference_plane=dut_output, time_basis=on_interval, power_method=on_mean 또는 peak를 보존한다. input_sha256은 원 spec의 hash이므로 같은 source의 여러 구간은 hash를 공유하며 구간은 start/stop으로 구별한다.

source_coverage=single_declared_band, max_search_complete=false다. 공통 7 flags는 synthetic=true, hardware_verified=false, ai_model_called=false, method_approval=not_assessed, regulatory_scope_complete=false, waveform_implemented=false, oem_mode_verified=false다. 성공은 계산 반환이며 별도의 status 필드를 추가하지 않는다.

입력·반환·적분 반환 객체는 독립 사본이다. 반환 ratio를 수정해도 source·다음 결과를 바꾸지 않는다. 원 spec을 변경하거나 내부 숨은 상태·실측 정답·원시 경로·예외를 결과에 추가하지 않는다.

## 한도와 고정 오류

기존 source의 JSON4MiB/깊이32/3..4096 knots/유한 int·float/양수 밀도/정확히 3000 Hz가 완전히 포함된 구간 조건을 먼저 따른다. 소비자는 다음 추가 한도를 적용한다.

- 적분 DTO는 정확히 기존 22키·공개 고정값과 형식이어야 하고 canonical 유한 UTF-8 compact JSON이 16KiB 이하여야 한다.
- ratio는 정확히 numerator/denominator의 양의 ASCII 십진 정수 문자열이다. 부호·공백·선행0·0·추가 키·약분되지 않은 분수는 거절한다.
- 각 정수는 최대 1234자리와 4096bit다. 9자리 이하 조각으로 읽고 bit 한도를 확인한 뒤에만 5제곱한다. 5제곱은 최대 20480bit, 우변의 10000배는 최대 20494bit다. 이 제한을 우회하려고 float로 낮추지 않는다.
- ratio의 float 표현은 양수·유한이어야 하고 기존 power_mw 표시와 정확히 일치해야 한다. 이는 출처 DTO 일관성 검사이며 8 dBm 비교 근거가 아니다.
- source의 start/stop은 둘 다 int이거나 둘 다 float여야 한다. 기존 endpoint 표시 guard처럼 공개 폭이 정확 3000 Hz와 그 값의 1 ULP를 넘게 다르면 거절한다. 이 guard는 표시 불일치의 거절 기준이며 PSD 한계의 허용오차가 아니다.
- 표시 로그의 독립 Decimal 정밀도는 최대 1280이다. 정확한 정수 비교가 가능해도 표시를 확정할 수 없으면 전체 계산을 거절한다.

| ValueError 코드 | 의미 |
|---|---|
| invalid_frequency_source | 기존 source 입력·JSON·선언 오류 |
| invalid_frequency_interval | 잘못된 start 또는 구간 전체 미포함 |
| invalid_integrated_power | 적분 반환의 공개 DTO·ratio 형식/기약성·출처 flags·power 표시 일관성 오류, 알 수 없는 source ValueError |
| numeric_result_out_of_range | 기존 source 계산/표시 불가, ratio 크기 초과, 정확 전력의 float 표현 불가, 로그·margin 표시 불가/비영 값의 0 소실 |

오류는 원시 입력을 포함하지 않는 고정 문자열이며 불량 응답을 자동 정규화·clip·외삽하지 않는다. source의 알려진 세 오류는 보존하고 알 수 없는 ValueError의 원문은 전달하지 않는다.

## 검증과 남은 범위

[전용 테스트](../../tests/test_virtual_fleet_frequency_psd.py)는 독립 Fraction 기울기/절편 원시함수·power5·별도 numerator/denominator 로그 oracle로 평탄/경사/여러 knot·밀도 배율·주파수 이동·끝점 포함·표시8 경계·극소/큰 유한값을 대조한다. 원 spec hash/별칭·4096 knots·JSON/ratio 한도·유한성·Decimal 환경·무I/O·표현 불가도 검사한다.

```text
.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_virtual_fleet_frequency_psd tests.test_virtual_fleet_frequency_source tests.test_virtual_fleet_spectrum_math -v
.venv\Scripts\python.exe -B -X utf8 scripts/check_artifacts.py
```

별도의 private 실행 증거는 실제 기존 source 생성→정확 적분→새 소비자를 실행한 합성 결과다. 단위 테스트의 고장/경계 주입을 이 실제 연결 증거로 세지 않는다. 전대역 최대 탐색·FFT/RBW/ENBW·RF 경로 손실·duty/crest 보정·I/Q/시간 파형·OEM mode·실제 AI/실장비/현장·규범 방법 승인/적합성 검증은 미실행이다. 보고서 수치·공칭 mode·대역폭에서 밀도를 만들거나 현재의 미확정 항목을 채우지 않는다.
