# 명시 표준불확도 성분의 수학 합성

2026-10-26 Asia/Seoul. `DEV3-CONDUCTED-UNCERTAINTY-BUDGET-001`은 제공된 성분의 산술만 계산하는 순수 API다. 실제 불확도 성분의 확보·완전성·상관관계·교정성적서·현행 규범·물리 적합성을 검증하거나 승인하지 않는다. 새 값이 기존 결과·측정·보정·한계·uncertainty·verdict에 자동 적용되지 않는다.

```python
from labflow.virtual_fleet.conducted_uncertainty_budget import build_conducted_uncertainty_budget

budget = build_conducted_uncertainty_budget(result, components=components, policy=policy)
```

`result`는 기존 D3 native result snapshot이다. [기존 비교](conducted_twin_comparison_usage.md)의 순수 `_twin` 검증을 재사용하여 D3 C1, `recorded/full_bound`, 명시 `on/source_output/dBm` 및 원래 binding·quantity·보정 일관성을 확인한다. 비교 API·writer·측정 실행을 호출하지 않는다. result의 값은 수정하지 않으며 원본 파일·참조를 열지 않는다.

`components`는 1~16개 plain list이며 각 항목은 다음 exact8이다. `component_id`는 고유한 기존 opaque ID 형식, `standard_uncertainty_db`는 명시된 native int/float의 유한 값 ≥0이다. bool·문자 숫자·Decimal·Fraction을 입력 숫자로 받지 않는다. `method` exact2는 result와 같아야 한다. metric·quantity·plane·unit을 생략·추정하지 않는다. uncertainty 단위는 `dB`, 결과의 측정 단위는 `dBm`이다.

```json
{
  "component_id": "authored-u1",
  "standard_uncertainty_db": 0.3,
  "unit": "dB",
  "method": {"method_id": "conducted_synthetic", "method_version": 1},
  "metric": "on",
  "quantity": "on_average",
  "reference_plane": "source_output",
  "evidence_refs": ["authored:synthetic-standard-uncertainty"]
}
```

`policy`는 다음 exact6이다. coverage factor는 명시된 유한 native 숫자 >0이어야 한다. 근거 목록은 각각 1~8개의 비어 있지 않은 plain string, 항목당 512자 이하이며 제어문자를 허용하지 않는다. component의 근거도 같은 형식이다. `uncorrelated`와 그 근거가 명시되어야 제곱합을 계산한다. caller의 가정은 검증된 독립성·상관 0 인증이 아니다. 분포·divisor·기본 k·누락 0·감도계수·covariance를 만들거나 추정하지 않는다. 입력 표준불확도는 이미 해당 출력량의 dB 성분으로 제공되어야 한다.

```json
{
  "policy_id": "authored-policy",
  "policy_version": 1,
  "coverage_factor": 2,
  "coverage_factor_evidence_refs": ["authored:explicit-k"],
  "correlation_assumption": "uncorrelated",
  "correlation_evidence_refs": ["authored:assumption-only"]
}
```

각 숫자는 `Fraction(str(native_number))`의 유한 십진 표현으로 해석한다. `q = sum(u_i**2)`와 `k**2*q`는 정확 유리수로 계산한다. 4,096자리 Decimal context에서 terminating decimal 변환이 정확함을 확인하고, 80자리·`ROUND_HALF_EVEN`으로 `sqrt(q)`와 `sqrt(k**2*q)`를 각각 계산한다. 후자는 양수 k에 대한 `k*sqrt(q)`와 수학적으로 같으며, 반올림한 중간 표준불확도에 k를 다시 곱하는 이중 반올림을 피한다. 이 고정 정밀도는 수치 구현 설정이며 물리 유효 숫자·coverage probability·규범상 요구 정밀도가 아니다.

두 Decimal 결과를 native float로 투영한다. 유한하지 않거나 정확 양수 값이 0으로 투영되면 전체 산출을 `not_assessed`로 보류한다. 정확 제곱항·제곱합·k의 유리수 문자열, Decimal 값, 수식·반올림·정밀도 trace가 수치 근거다. float는 유한 근사값이며 Decimal trace가 우선한다. 예시 성분 0.3·0.4와 명시 k=2의 산술은 q=1/4, 표준 0.5 dB, 확장 1 dB다. 실제 시험소 불확도 값이 있다는 뜻은 아니다.

출력 exact10은 `schema_version/kind/status/bindings/scope/budget/trace/reasons/conformity/verification`이다. kind는 `conducted_uncertainty_budget`, status는 `calculated` 또는 `not_assessed`다. bindings exact3은 제공 result/components/policy의 canonical SHA-256이며 진위 인증이 아니다. scope는 method/version/metric/quantity/plane/measurement_unit/uncertainty_unit/source_settings의 exact8 또는 null이다.

budget exact2는 `combined_standard_uncertainty_db`, `expanded_uncertainty_db`다. unknown·누락·null·성분 없음·중복 ID·잘못된 숫자·근거 부족·범위 상충·미지원 단위/metric/plane·한도 초과에서는 둘 다 null이며 구체적인 고정 reason을 반환한다. 계산 도중 실패해도 이전 숫자를 남기지 않는다. trace의 bounded `provided_components/provided_policy`는 원 제공값과 가정이며 검증된 측정값이 아니다. 보류 시 계산 trace의 terms는 빈 목록, 제곱합/k/Decimal 값은 null이다. 원래 result 전체는 복사하지 않고 hash와 scope로 연결한다.

전체 입력 canonical은 2 MiB, components+policy canonical은 64 KiB, 출력은 256 KiB 이하다. 기존 native depth32/node bounds와 D3 1 MiB C1 한도도 유지한다. 초과 metadata는 본문을 trace에 복제하지 않는다. `KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit` 및 예상하지 못한 실행 오류는 성공·0·추정치로 바꾸지 않고 전파한다. 선언된 검증·수치 한계 오류만 판단 보류로 반환한다.

conformity는 항상 `not_assessed/null`, verification은 수학 합성만 true이고 물리·실장비·성분 완전성·상관 입증·근거 진위·기존 결과 적용·실행 권한은 false다. method 승인은 `not_assessed`, 원본 bytes는 `not_reopened`를 유지한다. 기준면·quantity·method의 제공 일치는 실제 모든 같은 조건의 적용성 입증이 아니다. 공개 합성 입력의 Fraction/Decimal 대조·원형 보존·유보·예외 검증만 수행하며, 실측 대조·현장·실제 불확도 해소는 미검증이다. IO·PDF·StoreSQL·AI·hardware·분포/covariance 엔진을 연결하지 않는다.

신규 검사 25개를 통과했다. 이 안에 독립 Fraction·Decimal 2,000자리 대조 14사례와 overflow·양수 underflow 보류 6사례를 포함한다. 명시 0과 최소 양수·아주 큰 값·혼합 scale·16성분, 누락·상충·범위·원형·예외·최종 출력 실패를 확인했다. caller의 Decimal 정밀도·반올림·지수 범위·대소문자 설정 및 변경된 DefaultContext trap에도 산술과 trace가 같으며 caller 상태는 유지된다. 순수 호출 중 파일 open/native backend/SQL/network/process를 차단한 검사도 통과했다. 기존 비교·CLI·RF 회귀 분모는 재실행·합산하지 않았다. 이는 실제 불확도 성분·교정성적서·같은 조건 실측을 확보한 증거가 아니다.
