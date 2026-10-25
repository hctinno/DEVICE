# 접수 근거 → conducted 합성 plan 입력

```python
from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input

build_conducted_twin_plan_input(
    context, analysis, *, expected_revision, expected_context_sha256,
    source_settings, basis, method,
) -> dict
```

pure adapter다. 기존 public context8과 analysis schema1/2를 받아 genuine `build_analysis_prompt`, `validate_analysis`, `project_analysis`로 형상·인용·제품/목적/시장·누락/충돌을 다시 검증한다. caller의 projection이나 `status='approved'`는 권위로 받지 않는다. Store·파일·모델·장비·장부에 접근하지 않는다.

[구현](../../labflow/intake_conducted_twin_plan.py)과 [합성 검사](../../tests/test_intake_conducted_twin_plan.py)를 함께 확인할 수 있다.

`expected_revision`은 positive native int, `expected_context_sha256`은 `SHA256(canonical(context).encode('utf-8'))`다. 두 값의 일치는 caller가 제공한 snapshot의 버전 대조이며 DB의 현재 버전 확인이 아니다. schema2 analysis의 context_id도 같은 context에 결합돼야 한다. 원본 파일 bytes를 재개방하지 않으므로 원본 진위·현장 최신성은 upstream 검증 책임이다.

`source_settings`는 다음 native dict exact6이며 값을 추정하지 않는다.

| 키 | 값·단위 |
| --- | --- |
| frequency_hz | finite number > 0, Hz |
| power_dbm | finite number, 합성 on-average source power, dBm |
| bandwidth_hz | finite number > 0, Hz |
| duty_cycle | finite number, 0 < 값 ≤ 1 |
| modulation | 기존 RF 경계의 nonempty text, 최대200자 |
| crest_factor_db | finite number ≥ 0, dB |

bool은 number가 아니다. 기존 genuine RF validator로 frequency−bandwidth/2 ≥ 0, frequency+bandwidth/2 finite도 검사한다. 누락·잘못된 값은 null과 blocking gap이다. `frequency_mhz` 같은 다른 키를 추정 변환하지 않는다. 2450/OFDM/.25/crest3 등 기본값은 없다. 이 수학 입력 범위는 규제 한계값이나 실제 장비 지원 범위가 아니다.

`basis`는 같은6키의 dict다. 각 항목은 `{kind, value, unit, evidence}` exact4다. kind는 `source_cited` 또는 `developer_declared_synthetic`다. 전자는 동일 context 문서에 대한 기존 analysis 인용 exact shape 목록이 필요하며 원 SHA·page/line·quote를 genuine validator로 검사한다. quote 안의 value/unit도 제공 설정값과 일치해야 한다. 후자는 evidence가 빈 목록이며 개발자가 선언한 합성 조건임을 그대로 남긴다.

주파수/대역폭은 Hz/kHz/MHz/GHz, 전력은 dBm, duty는 ratio/%, modulation은 label, crest는 dB를 명시한다. 단위 환산은 제공된 설정과 근거 값의 일치 검사에만 쓰며 누락 설정을 채우지 않는다. source_cited power는 같은 quote의 명시 `on_average_power: 값 dBm`(on-average/on average 표기도 허용)에 묶는다. report_peak나 양이 불명인 power는 이 방법의 on-average 입력으로 해석·환산하지 않고 blocked다. `source_cited`도 보고서 조건을 합성 입력으로 인용하는 것이며 보편 규정이나 요청 목적을 입증하지 않는다.

`method`는 `{method_id, method_version, metric, reference_plane}` exact4다. 첫 지원은 `conducted_synthetic` / native int `1`, metric은 `on`/`time`/`peak`, plane은 `source_output`이다. 다른 방법/버전/plane·알 수 없는 필드는 blocked와 명시 gap이며 기본 방법이나 plane을 넣지 않는다. 이 ID는 합성 입력 계약이며 FCC 시험방법 승인이 아니다.

반환 exact8은 `schema_version, kind, status, binding, intake, plan, gaps, verification`이다. schema_version은1, kind는 `intake_conducted_twin_plan_input`, status는 `ready_for_simulation` 또는 `blocked`다. `plan.source_settings`는 항상 exact6이며 `plan`에 method ID/version·metric·plane·basis_refs를 보존한다. numeric_limit_dbm/uncertainty_db는 null, assessment는 not_assessed다. binding에는 intake/revision/context/analysis/plan의 SHA 추적값을 남긴다.

제품·목적·시장과 모든 원 source facts/missing_fields/questions를 보존한다. 목적/시장은 genuine projection의 explicit request 근거이며 값도 quote에 나타나야 한다. report role=reference의 PASS/조건을 요청 목적/시장으로 올리지 않는다. 현재 지원 합성에 필요한 product_type/purpose/market 누락, identity 미정, 충돌, unread 문서는 blocking이다. 그 밖의 원 missing_fields는 후속 실물 준비 gap으로 명시해 남기며 삭제하지 않는다. source6 값/근거·method가 모두 명시돼야 simulation ready다.

같은 입력은 detached deterministic 결과를 반환하고 입력을 바꾸지 않는다. 입력은 plain native JSON이며 8MiB/깊이32/100,000 node 이내다. malformed input/잘못된 SHA·인용·버전·숫자·단위·키는 blocked다. observed control 예외는 전파한다. simulation ready는 규격 적합성·실측 예측력·전체 시험 완료·실제 실행 허가가 아니다. G1 issuer/G2 예약/G4 launch/G5 finish는 별도 연결 과제로 남는다.
