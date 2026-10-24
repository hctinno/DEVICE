# 선언 밀도 곡선의 연속 3 kHz 최대 PSD

2026-10-24 · Asia/Seoul. SOURCE-PSD-MAX-014 개발3. [명시 주파수 source](virtual_frequency_source_usage.md)의 선형 mW/Hz 곡선을 대상으로 하며 [단일 구간 PSD](virtual_frequency_psd_usage.md)의 public 계약을 변경하지 않는다.

```python
from labflow.virtual_fleet.frequency_psd_max import find_source_psd_maximum

spec = {
    'schema_version': 1, 'kind': 'synthetic_piecewise_density_source',
    'source_id': 'declared-maximum-1', 'declared_mode_id': 'declared-mode-1',
    'synthetic': True, 'center_hz': 2450000000,
    'reference_plane': 'dut_output', 'time_basis': 'on_interval',
    'power_method': 'on_mean', 'interpolation': 'linear_mw_per_hz',
    'frequency_offsets_hz': [-4000, 0, 6000],
    'density_mw_per_hz': [0.25, 1, 0.5],
}
result = find_source_psd_maximum(spec)
assert result['status'] == 'complete'
assert result['winning_interval']['start_offset_hz'] == {
    'numerator': '-12000', 'denominator': '13'}
assert result['winning_interval']['stop_offset_hz'] == {
    'numerator': '27000', 'denominator': '13'}
assert result['max_search_complete'] is True
assert result['regulatory_scope_complete'] is False
```

## 탐색 범위와 완전 후보

`find_source_psd_maximum(spec) -> dict`는 기존 source의 엄격 validation·독립 snapshot·Fraction 표현·원 spec fingerprint를 package 내부에서 재사용한다. 새 transport·Store·시간 파형·RF 관측을 만들지 않는다.

선언 knot가 `x_i`, 밀도가 `f`, 창 폭이 `W=3000`일 때 합법적인 창 시작은 `[x_0, x_last−W]`다. 이 범위 안의 `x_i`와 `x_i−W`, 범위 양끝을 정확한 유리수로 모은다. 서로 이웃한 breakpoint 사이에서 적분전력의 도함수 `f(t+W)−f(t)`는 affine 함수다. 부호가 바뀌면 그 정확한 영점을 추가한다. 끝점의 영점은 이미 후보이며, 도함수가 구간 전체에서 0인 plateau는 양끝으로 충분하다. 따라서 모든 breakpoint와 내부 영점은 전역 최대를 포함하는 완전한 유한 후보 집합이다.

밀도 segment의 slope와 누적 적분 prefix를 한 번 계산한다. 각 후보는 bisect로 segment를 찾고 두 누적 원시함수 값의 차로 정확하게 적분한다. 반복 전체 knot 적분이나 grid 탐색을 사용하지 않으며 탐색 구조는 O(n log n)이다. 후보는 Fraction으로 정렬·중복 제거하고 정확한 전력을 비교한다. 최대 전력이 같으면 가장 이른 **정확한** 시작을 선택한다. float·표시 반올림·epsilon으로 후보/승자/동률을 고르지 않는다.

승자의 정확한 양의 전력 `a/b` mW로 `a**5 <= 10000*b**5`만 비교한다. 이 경우 conditional_comparison=meets, 그 밖에는 above다. power_mw는 별도 유한 양수 float 표시다. 기존 PSD의 독립 Decimal80..1280자리 상·하한 helper로 power_dbm과 `margin_db=8−원래 로그값`의 안정 반올림을 확인한다. 표시 float에서 margin/비교를 재계산하지 않는다. 호출자의 Decimal precision/traps/flags를 보존한다.

## 끝점은 정확한 유리수

위치의 numerator는 부호 있는 정수 문자열, denominator는 양수 정수 문자열이다. 기약형이며 0은 `0/1`이다. 모든 공개 구간 위치는 이 객체를 사용한다. winning_interval의 stop−start는 정확히 3000이다.

binary64로 나타낼 수 없는 stationary 위치도 그대로 보존한다. Fraction을 float로 낮춰 기존 single-band API에 다시 넣지 않으며 위치 float를 함께 게시하지 않는다. 큰 주파수 이동으로 float 시작·끝이 같은 수로 합쳐져도 정확 구간은 유지된다.

## 정확한 반환 31키

```text
schema_version kind algorithm_id source_id declared_mode_id input_sha256
reference_plane time_basis power_method synthetic hardware_verified ai_model_called
method_approval regulatory_scope_complete waveform_implemented oem_mode_verified
reference_bandwidth_hz status reason_codes source_coverage max_search_complete
search_domain winning_interval candidate_count tie_break_policy
exact_power_ratio power_mw power_dbm maximum_dbm margin_db conditional_comparison
```

고정값은 schema_version=1, kind=synthetic_source_psd_maximum, algorithm_id=exact_continuous_3khz_density_max_v1, reference_bandwidth_hz=3000, maximum_dbm=8, tie_break_policy=earliest_exact_start다. source/mode/hash/reference_plane/time_basis/power_method와 기존 공통 7 flags를 보존한다. flags는 synthetic=true/hardware_verified=false/ai_model_called=false/method_approval=not_assessed/regulatory_scope_complete=false/waveform_implemented=false/oem_mode_verified=false다.

| 필드 | complete | incomplete |
|---|---|---|
| status | complete | incomplete |
| reason_codes | [] | [source_support_shorter_than_reference_bandwidth] |
| source_coverage | complete_declared_density_support | declared_density_support |
| max_search_complete | true | false |
| search_domain | 아래 정확한 최소/최대 시작과 empty=false | 최소 시작이 최대 시작보다 크며 empty=true |
| winning_interval | 정확한 start/stop 객체 | null |
| candidate_count | 실제 평가한 서로 다른 후보 수 | int0 |
| exact_power_ratio, power_mw, power_dbm, margin_db, conditional_comparison | 정확 ratio/표시/조건부 비교 | 모두 null |

search_domain은 정확히 `{minimum_start_offset_hz, maximum_start_offset_hz, empty}`다. 앞의 두 값은 각각 `x_0`, `x_last−3000`의 유리수 객체다. winning_interval은 정확히 `{start_offset_hz, stop_offset_hz}`다. exact_power_ratio도 같은 numerator/denominator 형식이며 전력이므로 numerator가 양수다.

지지폭이 정확히 3000이면 한 개 창을 평가한다. 그보다 짧으면 없는 창의 전력을 0으로 만들지 않는다. complete와 max_search_complete=true는 **선언된 선형 밀도 지지구간 안의 창**에만 적용되며 물리적 전대역 최대나 규범 적합성 완료를 뜻하지 않는다. 후보 목록·원시 source 배열·숨은 실측값은 결과에 나열하지 않는다.

## 한도와 오류

- 기존 source의 12키/JSON4MiB/깊이32/3..4096 knots/유한 int·float/양수 밀도/center+offset 조건을 그대로 따른다.
- 서로 다른 후보는 최대 16384개다. breakpoint 수와 구간당 최대 한 개 영점에서 도출되는 O(n) 후보이며 무한 plateau를 열거하지 않는다.
- 저장한 작업 Fraction의 분자 절댓값과 분모는 각각 최대8192bit다. slope·prefix·밀도·영점·적분의 각 계산 단계에서 확인한다.
- 공개 위치/전력 ratio는 각 정수 최대4096bit/절댓값1234자리다. 9자리 조각 변환으로 host의 큰 정수 문자열 설정에 의존하지 않는다. 이 한도를 확인한 뒤 power5 비교를 수행한다.
- 완성 DTO의 canonical 유한 UTF-8 JSON은16KiB 이하다. power_mw/log/margin 표시도 유한해야 한다. 정확1mW의0dBm 외 비영 log 또는 margin의 float0 소실, overflow, 안정 반올림 미확정은 거절한다.

잘못된 source는 고정 ValueError(invalid_frequency_source), 수치·후보·정수/표시/JSON 한도 초과는 ValueError(numeric_result_out_of_range)다. 수치 오류를 incomplete나 임의0/8/meets로 바꾸지 않는다. 입력·반환·반환 내부의 유리수 객체는 독립 사본이며 다음 호출에 영향을 주지 않는다.

[전용 검사](../../tests/test_virtual_fleet_frequency_psd_max.py)는 해석적 평탄/경사/삼각/다봉/plateau·knot 최대와 비표현 stationary 위치를 확인한다. 별도 Fraction 원시함수와 세 점의 정확 적분으로 맞춘 조각별 이차식 oracle, 고정밀 Decimal 로그를 대조하며 grid는 보조 검증으로만 사용한다. 기존 source29/PSD24/math37 회귀와 실제 source→새 최대 결과의 합성 실행 증거를 별도로 보존한다.

실제 RF I/Q/시간 파형·검파/RBW/ENBW·지지구간 밖의 방사·OEM mode/칩셋·실장비·현장·FCC 방법 승인/적합성·실제 AI 검증은 미실행이다. duty/crest/경로 보정이나 공칭 mode에서 밀도를 자동 생성하지 않는다.
