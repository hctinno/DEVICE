# 접수 근거 → conducted 합성 plan 입력

```python
from labflow.intake_conducted_twin_plan import build_conducted_twin_plan_input

build_conducted_twin_plan_input(
    context, analysis,
    expected_revision=expected_revision,
    expected_context_sha256=expected_context_sha256,
    source_settings=source_settings, basis=basis, method=method,
)
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

`plan.source_settings`의 각 항목은 수치/문자와 해당 basis가 모두 유효할 때만 제공값을 유지한다. 근거 누락·잘못된 종류/단위/값·인용 거절이면 해당 실행 값과 `basis_refs`는 모두 null이며 원 제공값은 해당 `gap.provided`에만 남긴다. basis 전체가 dict가 아니면 source6은 모두 null이고 `field='basis'` gap의 provided에 기존 수치/문자 검사를 통과한 제공값 map을 남긴다. 수치/문자 검사 자체가 거절한 원 값은 기존 source_settings gap에 남는다. 다른 항목의 유효 값은 유지하며 basis로 누락 값을 채우지 않는다.

## 반환 DTO 전체 계약

아래 표는 구현의 `_result`, `_intake`, `_source_settings`, `_method`, `_basis`, `_finish`와 기존 `validate_analysis`/`project_analysis`를 대조한 공개 출력 계약이다. 반환 object는 exact8이고 아래 고정 object의 키도 항상 존재한다. 표의 nullable은 키 생략이 아니라 JSON null이다. 가변 field map과 question/citation 변형의 키는 별도 표를 따른다. `number`는 bool을 제외한 native int 또는 finite float이며 자동 기본값은 없다. `SHA256`은 소문자 hex64 문자열이다. `JSON`은 null/bool/int/finite float/string/list/object의 재귀 값이다.

| 경로 | 유형·고정값/enum | null·빈 값 의미 |
| --- | --- | --- |
| schema_version | int `1` | null 없음 |
| kind | string `intake_conducted_twin_plan_input` | null 없음 |
| status | string `ready_for_simulation` / `blocked` | blocking gap이 하나라도 있으면 blocked |
| binding | object exact6 | 아래 표 |
| intake | object exact5 | 아래 표 |
| plan | object exact10 | 아래 표 |
| gaps | Gap[] | 없음은 `[]`; nonblocking gap만 있어도 ready 가능 |
| verification | object exact6 | 아래 표 |

| binding 내부 키 | 유형 | 의미 |
| --- | --- | --- |
| intake_id | string 또는 null | 정규화된 caller context의 ID; context 검증 전 실패면 null |
| revision | positive int 또는 null | caller context의 revision; expected pin의 대조 성공을 뜻하지 않음 |
| analysis_context_id | SHA256 또는 null | caller context 결합값; context 검증 전 실패면 null |
| context_sha256 | SHA256 또는 null | genuine prompt가 정규화한 context의 canonical SHA; context 검증 전 실패면 null |
| analysis_sha256 | SHA256 또는 null | 제공 analysis 전체의 canonical SHA; evidence 검증 실패에도 기록될 수 있음 |
| plan_sha256 | SHA256 | 반환 plan 전체의 canonical SHA; blocked에서도 존재하며 실행 허가가 아님 |

| intake 내부 키 | 유형 | 의미 |
| --- | --- | --- |
| facts | field → ProjectedFact map | genuine 표시용 projection; 미확정/충돌 field는 키 생략, 초기 실패면 `{}` |
| source_facts | SourceFact[] | 검증된 analysis.facts 원 목록·순서·값·인용을 보존; 초기 실패면 `[]` |
| missing_fields | field[] | analysis의 원 누락 목록·순서를 보존; 초기 실패면 `[]` |
| follow_up_missing_fields | field[] | 위 목록 중 product_type/market/purpose 이외 항목; 삭제·해소 의미 아님 |
| questions | Question[] | genuine projection의 질문; 초기 실패/질문 없음은 `[]` |

`field` enum은 `product_type, customer, manufacturer, model, market, purpose, features, antenna_gain, power_target, firmware`다. `intake`는 raw analysis 전체가 아니다. producer/identity/context_id를 별도 표시 필드로 추가하지 않으며 원 facts와 표시용 facts를 구분한다. 이 adapter는 answers를 빈 map으로 전달하므로 `user_confirmed`/event_id를 생성하지 않는다.

| 중첩 object | exact 키·유형 | enum·보존 규칙 |
| --- | --- | --- |
| ProjectedFact | value: string, status: string | status `explicit` / `inferred`; value는 genuine projection의 trim된 단일 값 |
| SourceFact | field: field, value: string, status: string, evidence: Citation[] | status `explicit` / `inferred` / `uncertain`; value는 원문 값, 인용 1~20개; 원 facts 최대200개 |
| Question: 충돌 | key: string, field: field, values: string[], message: string | key `conflict_` + field; values는 trim·중복 제거·정렬된 상충 값 |
| Question: 누락 | key: string, field: field, message: string | key `missing_` + field |
| Question: 대상 확인 | key: string, message: string | key `product_identity` |
| Question: 해석 미완료 | key: string, paths: string[], message: string | key `unread_documents`; paths는 caller context 문서 경로 |

| Citation 변형 | exact 키 | 유형·의미 |
| --- | --- | --- |
| analysis schema1 텍스트 | path, sha256, line_start, line_end, quote, role (6) | path/quote string, sha256 SHA256, line_start/line_end positive int, role `request` / `product` / `reference` |
| schema2 text_line | 위6 + kind (7) | kind `text_line`; 같은 context 텍스트의 1부터 시작하는 행 범위 |
| schema2 pdf_page | 위6 + kind, extraction_id, page_number, text_sha256 (10) | kind `pdf_page`, extraction_id/text_sha256 SHA256, page_number positive int; 정규화된 PDF 파일 내 페이지·그 페이지의 행 범위 |

모든 citation은 literal quote와 원 SHA/행 범위가 해당 context에 결합된다. PDF는 extraction_id·페이지 text SHA도 일치해야 한다. printed page label이나 다른 위치 정보를 새 키로 추정하지 않는다. citation 변형은 source_facts와 아래 basis_refs에 동일하게 적용한다.

| plan 내부 키 | 유형·고정값/enum | null 의미 |
| --- | --- | --- |
| schema_version | int `1` | null 없음 |
| method_id | string `conducted_synthetic` 또는 null | 누락/미지원 |
| method_version | int `1` 또는 null | 누락/미지원; bool 거절 |
| metric | string `on` / `time` / `peak` 또는 null | 누락/미지원 |
| reference_plane | string `source_output` 또는 null | 누락/미지원 |
| source_settings | object exact6 | 아래 source6; 개별 값·근거 검사를 모두 통과한 항목만 유지 |
| basis_refs | object exact6 | source6과 같은 키; Basis 또는 null, 거절·미제공 값에는 null |
| numeric_limit_dbm | null | 규제 한계값 미평가; 0이 아님 |
| uncertainty_db | null | 불확도 미평가; 0이 아님 |
| assessment | string `not_assessed` | 판정 미수행 |

| source6의 키 | source_settings의 유형·범위 | basis_refs의 value·허용 unit |
| --- | --- | --- |
| frequency_hz | number > 0 또는 null | number; `Hz` / `kHz` / `MHz` / `GHz` |
| power_dbm | number 또는 null | number; `dBm`; 합성 on-average 입력 |
| bandwidth_hz | number > 0 또는 null | number; `Hz` / `kHz` / `MHz` / `GHz` |
| duty_cycle | number, 0 < 값 ≤ 1 또는 null | number; `ratio` / `%` |
| modulation | nonempty string, 최대200자 또는 null | 같은 string; `label`; 별도 modulation enum 없음 |
| crest_factor_db | number ≥ 0 또는 null | number; `dB` |

source_settings는 원 제공 타입·값·위 표의 기준 단위를 유지한다. basis_refs는 검증된 원 Basis의 값·단위·인용을 유지하며 환산된 값으로 덮어쓰지 않는다. 두 object의6키는 초기 실패에도 모두 null로 존재한다. 기존 RF domain 검사에서 하단 주파수 음수/상단 overflow가 발생하면 frequency_hz와 bandwidth_hz를 모두 null로 보류한다. 한 항목의 gap이 다른 유효 항목을 null로 바꾸지는 않는다.

| Basis 내부 키 | 유형·enum | 규칙 |
| --- | --- | --- |
| kind | string `source_cited` / `developer_declared_synthetic` | 이 두 종류만 허용 |
| value | number 또는 string | 위 source6별 타입; unit 환산 후 제공 설정과 정확히 일치해야 함 |
| unit | string | 위 source6별 허용 단위만 사용 |
| evidence | Citation[] | source_cited는 1~20개, developer_declared_synthetic는 `[]` |

| Gap 내부 키 (exact4) | 유형 | 의미 |
| --- | --- | --- |
| code | string | 아래 코드 목록; 미확인 값의 성공 처리를 허용하지 않음 |
| field | string | `input`, `context`, `analysis`, `binding.*`, `intake.*`, `source_settings[.*]`, `method[.*]`, `basis[.*]` 중 대상 경로 |
| provided | JSON | 거절한 원 설정·method 값/상충 값 목록/검사 중 제공값 map 또는 null; 저장 정보이며 실행 값으로 복원하면 안 됨 |
| blocking | bool | true면 status blocked; 후속 누락·불확정 중 비필수 field는 false 가능 |

현재 code enum은 `native_input_invalid, analysis_invalid, context_invalid, expected_revision_changed_or_invalid, expected_context_changed_or_invalid, analysis_evidence_invalid, conflicting_intake_fact, missing_intake_field, follow_up_missing_field, product_identity, unread_documents, uncertain_intake_fact, intent_value_not_in_request_quote, invalid_source_settings, unknown_source_field, missing_setting, unsupported_modulation, invalid_setting, invalid_rf_domain, invalid_method, unknown_method_field, unsupported_method_field, missing_method_field, invalid_basis, unknown_basis_field, missing_or_invalid_basis, unsupported_or_invalid_basis, basis_value_mismatch, basis_quote_value_mismatch, basis_evidence_invalid`다. gaps는 `(field, code, canonical(provided))` 순으로 정렬한다. provided=null은 보존할 값이 없거나 해당 검사가 값을 복사하지 않았다는 뜻이며 해소를 뜻하지 않는다.

| verification 내부 키 (exact6) | 유형·enum | 의미 |
| --- | --- | --- |
| evidence | string `validated_in_memory` / `not_validated` | blocking gap이 없을 때만 전자; 원본 재확인·계측 검증과 구별 |
| current_version | string `caller_snapshot_only` | 현재 DB를 관측하지 않음 |
| source_bytes | string `not_reopened` | 원 bytes 재개방 없음 |
| regulatory | string `not_assessed` | 규제 적합성 미평가 |
| measurement_prediction | string `not_assessed` | 실측 예측력 미평가 |
| execution_authority | bool `false` | ready/blocked 모두 실행권한 없음 |

예를 들어 공개 합성 입력 frequency_hz=2412000000에 해당 basis만 누락하면 status는 blocked, `plan.source_settings.frequency_hz`와 `plan.basis_refs.frequency_hz`는 null이다. `code='missing_or_invalid_basis', field='basis.frequency_hz', provided=2412000000, blocking=true` gap에 원 수치가 남으며 다른 유효 source5는 유지된다.

제품·목적·시장과 모든 원 source facts/missing_fields/questions를 보존한다. 목적/시장은 genuine projection의 explicit request 근거이며 값도 quote에 나타나야 한다. report role=reference의 PASS/조건을 요청 목적/시장으로 올리지 않는다. 현재 지원 합성에 필요한 product_type/purpose/market 누락, identity 미정, 충돌, unread 문서는 blocking이다. 그 밖의 원 missing_fields는 후속 실물 준비 gap으로 명시해 남기며 삭제하지 않는다. source6 값/근거·method가 모두 명시돼야 simulation ready다.

같은 입력은 detached deterministic 결과를 반환하고 입력을 바꾸지 않는다. 입력은 plain native JSON이며 8MiB/깊이32/100,000 node 이내다. malformed input/잘못된 SHA·인용·버전·숫자·단위·키는 blocked다. observed control 예외는 전파한다. simulation ready는 규격 적합성·실측 예측력·전체 시험 완료·실제 실행 허가가 아니다. G1 issuer/G2 예약/G4 launch/G5 finish는 별도 연결 과제로 남는다.
