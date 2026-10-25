# 검증된 접수 사실 → conducted 계획 입력

```python
build_conducted_plan_from_intake_facts(
    context, analysis,
    expected_revision=expected_revision,
    expected_context_sha256=expected_context_sha256,
    method=method,
)
```

caller가 source_settings6/basis6를 일일이 조립하지 않도록, 제공한 structured fact와 literal source quote의 명시 값·단위를 기존 plan builder 입력으로 바꾸는 pure adapter다. Store·파일 재개방·원장·모델·권위·장비를 추가하지 않는다. 기존 context/strict analysis schema와 plan exact8은 바꾸지 않는다.

[구현](../../labflow/intake_facts_to_conducted_plan.py), [합성 검사](../../tests/test_intake_facts_to_conducted_plan.py), [기존 plan DTO](intake_conducted_twin_plan_usage.md)를 함께 확인한다.

## 실제 형상과 재사용

context는 public8, analysis는 기존 schema1/2다. fact는 field/value/status/evidence exact4이며 value는 string이다. 현재 FIELDS10에는 RF 전용 키가 없으므로 frequency_hz 등을 새 fact.field로 발명하지 않는다. 첫 범위는 features/power_target의 명시 RF 문장이다. genuine build_analysis_prompt/validate_analysis로 형상·인용을 재검증하고 기존 plan의 native snapshot·숫자/단위표·quote 검사와 RF domain을 재사용한다.

제품·목적·시장/원 facts·missing/questions는 기존 부모가 그대로 검증·보존한다. 서로 다른 features.value는 genuine projection에서 conflict_features가 될 수 있다. RF 정규값이 같아도 analysis를 합치거나 지워 원 충돌을 숨기지 않는다. expected revision/hash의 일치는 caller snapshot 대조이며 실제 DB current나 원 bytes 진위를 입증하지 않는다.

## 닫힌 문장과 동일 조건

문법은 줄 또는 세미콜론으로 나눈 `label: value unit` / `label = value unit` 문장의 전체 일치다. 주변 숫자를 검색해 첫 값을 선택하지 않는다. 숫자는 부호·소수·지수 표기를 받되, literal 최대128자·지수 절댓값400 이내에서 finite native int/float로 정확히 표현할 수 있어야 한다. 긴 지수/비유한/Decimal 오류는 유계 거절하고 원 MemoryError/control은 보존한다.

| 출력 키 | 지원 label | 명시 단위·범위 |
| --- | --- | --- |
| frequency_hz | frequency | Hz/kHz/MHz/GHz; positive number |
| power_dbm | on_average_power | dBm; finite number. 기존 on-average/on average 철자도 허용 |
| bandwidth_hz | bandwidth | Hz/kHz/MHz/GHz; positive number |
| duty_cycle | duty_cycle | ratio/%; 환산 결과 0<값≤1 |
| modulation | modulation | 명시 literal label≤200자; 별도 modulation enum 없음 |
| crest_factor_db | crest_factor | dB; number≥0 |

공개 authored 합성 문자열 예시다. 아래 값은 코드 기본값이나 실제 제품 조건이 아니다.

```text
frequency: 2412 MHz
on_average_power: -7 dBm
bandwidth: 20 MHz
duty_cycle: 50 %
modulation: CUSTOM-IQ
crest_factor: 4 dB
```

후보는 fact.value와 그 fact의 원 evidence.quote 양쪽의 같은 label·정규값에 결합돼야 한다. 명시 단위가 달라도 정확한 환산값이 같으면 비교할 수 있지만 basis의 value/unit은 원 quote 표기를 보존한다. unit 변환은 값의 동일성 검사이며 누락을 채우는 추정이 아니다. source_cited만 만들고 developer_declared_synthetic를 자동 발급하지 않는다.

usable 후보는 explicit인 사실과 literal quote에 의해 지지돼야 한다. 동일 정규 numeric 값의 반복만 일치로 묶는다. 추론/불확실·다른 값·지원 밖 문장/단위·범위/비교/다중 목록·quote 불일치가 있으면 해당 field는 null이다. 첫 값/마지막 값/평균을 고르지 않는다. modulation은 하나의 명시 literal을 보존하고 MCS/HT20 등에서 추정하지 않는다.

modulation의 공백 없는 단일 token 또는 escape 없는 큰따옴표 literal을 받는다. 예를 들어 `CUSTOM-IQ`와 `"CUSTOM IQ"`는 명시 label이며 `OFDM / CCK`에서 한 종류를 선택하지 않는다. 이 문법 제한은 RF modulation 지원 enum이 아니다.

현재 analysis에는 RF condition ID가 없다. 같은 제품이라는 사실만으로 다른 행·모드·조건·출처를 연결하지 않는다. 첫 범위는 동일 physical citation/quote의 명시 블록에서 얻는 부분 또는 전체 벡터다. 같은 quote를 참조하는 지원 사실은 그 안에서 대조할 수 있다. 한 블록이 이미 지지하는 값의 반복은 합칠 수 있으나, 서로 보완적인 별도 블록을 짜깁기해야만 입력이 성립하면 source_settings를 보류하고 조건 확인 질문1개를 둔다. 한 블록의 일부 값만 있으면 유효 값은 유지하고 빠진 field만 묻는다.

문장/후보 개수도 유계다. 한 블록은 최대128개 segment, 전체 후보는4096개 이내다. 초과하면 일부만 골라 성공 처리하지 않는다. channel→frequency, HT20→BW, duty/crest/손실·기준면·수치 한계의 default/예제 추정은 없다. report_peak/reported_peak/양불명 power를 on-average source 입력으로 바꾸지 않는다. 규범의 최소 BW/최대 power나 XML6 fact를 제품 동작 설정 또는 norm PASS로 올리지 않는다. 자유문장·표 행/열 연결은 지원 범위가 아니다.

명시 on_average_power와 별도로 표기된 reported_peak/peak_power/time_average_power가 함께 있어도 그 다른 quantity를 입력으로 바꾸거나 평균내지 않는다. 이 경우 명시 source on-average만 사용하고 다른 원 값은 source_facts에 보존한다. on-average 자체가 없거나 단순 power/power_dbm처럼 양이 불명인 후보가 섞이면 power 입력은 계속 null이다.

## method와 반환

method exact4는 caller가 그대로 명시한다. 현재 conducted_synthetic/native version1/metric on,time,peak/reference_plane source_output 계약을 유지한다. source power의 명시 on-average 의미는 method metric과 별개다. 미지원 method/plane을 추정·교체하지 않으며 이 ID를 FCC 규범 방법 승인으로 해석하지 않는다.

| wrapper exact6 | 유형·의미 |
| --- | --- |
| schema_version | native int1 |
| kind | intake_facts_to_conducted_plan |
| status | ready_for_simulation / blocked; plan_input.status와 같음 |
| plan_input | genuine build_conducted_twin_plan_input의 원 exact8 |
| assembly_gaps | source 추출의 추가 Gap[]; 부모 gap은 plan_input.gaps에 보존 |
| questions | source 추출의 추가 Question[]; 부모 원 질문은 plan_input.intake.questions에 보존 |

추가 Gap은 code/field/provided/blocking exact4이며 blocking은 true다. field는 source_settings 또는 그 하위6키다. provided는 원 후보의 fact_index/evidence_index·raw token/unit·문장 위치 metadata 또는 null이다. 큰 quote를 복제하지 않고 plan_input.intake.source_facts의 원형과 index/위치로 연결한다. 부모가 수치 범위를 거절하면 그 원 제공값·gap을 그대로 남긴다.

| provided의 후보 metadata exact6 | 유형·위치 의미 |
| --- | --- |
| fact_index | source_facts의 0부터 시작하는 native int index |
| evidence_index | 해당 source fact의 evidence에서 0부터 시작하는 native int index |
| raw_value | 원 numeric token≤128자 또는 literal label≤200자; 형상/한도 거절로 token을 읽지 못하면 null |
| unit | 원 단위/label marker 또는 미확인 unit string≤16자; 읽지 못하면 null |
| value_span | fact.value 내 `[start, end]` 문자 index, end 미포함 |
| quote_span | 원 evidence.quote 내 같은 형식의 문자 index; PDF 파일/printed page 좌표로 추정하지 않음 |

matching 문장이 없으면 해당 span은 제공된 전체 value/quote를 가리킨다. 원문을 잘라 성공 처리하는 대신 index로 원 source_facts 전체를 유지한다. 현재 assembly code는 `source_fact_missing, source_fact_unverified, source_statement_unsupported, source_quote_mismatch, source_unit_unsupported, source_power_quantity_unsupported, source_value_conflict, source_condition_unbound, source_number_unrepresentable, source_candidate_limit`이다.

지원 label을 알아볼 수 없는 features 원문도 미확인 field의 provided에 위치를 남긴다. 그 위치가 있다는 사실은 해당 문자열을 특정 RF 값이나 quantity로 해석했다는 뜻이 아니다. 그런 원문에서 raw_value/unit은 null이며 원 value/quote 전체가 보존된다.

추가 Question은 key/field/reason/message exact4다. 평가 가능한 미확인 field당 최대1개, 조건 벡터 자체가 미결합이면 상위 조건 질문1개다. 입력 C1/strict analysis/인용이 무효하거나 method가 미지원이면 추출하지 않고 부모 blocked/gap을 보존하며 RF 질문을 불필요하게 늘리지 않는다.

key는 `source_`+6키 또는 source_condition/source_domain, field는 위 source 경로, reason은 해당 assembly code 또는 부모의 기존 숫자/domain gap code, message는 한국어 확인 문장이다. parent의 invalid_rf_domain은 주파수/BW 확인 질문1개로 묶는다. 원 parent 질문과 새 RF 질문은 서로 지우거나 덮어쓰지 않는다.

source6/basis는 검증된 항목만 전달하며 누락/상충/모호함은 null이다. numeric_limit_dbm와 uncertainty_db는 null, assessment/regulatory/measurement prediction은 not_assessed, execution_authority는 false다. 같은 입력은 deterministic/detached 결과를 내고 입력을 변경하지 않는다. 전체 입력은 기존 native JSON8MiB/깊이32/100000 node 한도를 따른다.

## 검증

공개 합성 context/analysis와 genuine 부모를 사용한다. schema1 text와 schema2의 이미 제공된 정규화 페이지·인용만 다루며 PDF 원 파일을 읽지 않는다. 정상6값/단위 환산·중복·상충·부족·range/peak·조건 미결합·context/quote/hash 변경·control 전파·입력 불변을 구분한다. 실제 모델·고객 실값·P01 원 packet·타 owner proof·hidden expected는 사용하지 않는다. 합성 통과는 실제 계측 정확도·전체 시험소·규범 적합성 검증이 아니다.
