# 성적서 근거의 계산 대조 023 v1

2026-10-24 · Asia/Seoul. 공개 예제와 테스트는 합성 자료다. 실제 성적서·추출 본문·수치는 private에 보존한다. `labflow.fcc_report_calculation.check_report_calculation(case_detail, request) -> dict`는 파일·PDF bytes·네트워크·Store·SDK·콜백을 받지 않는 순수 함수다. 기존 `labflow.calculations.calculate`의 `rf_power`, `emc_field_strength`만 재사용한다. 새 RF/전원 엔진·규범 limit·법적 PASS·현재 DUT/FW 지원을 만들지 않는다.

021 producer가 검증한 원본 PDF와 retained literal을 이 함수에서 다시 읽거나 인증하지 않는다. 제공된 DTO의 타입·출처 일관성·claim/페이지 문맥을 검사하며 quote는 검수자의 구조화 value 해석이 정확하다는 증거로 바꾸지 않는다. 실제 P01/021 사례 실행은 합성 검사와 따로 기록한다.

## 입력과 한도

입력은 정확한 dict/list와 JSON scalar만 허용한다. dict/list/str/int subclass, bool 수치, callback/file-like/bytes/Path는 거절한다. 0과 false는 유효한 값이며 누락으로 바꾸지 않는다. JSON 문자열 입력 helper는 제공하지 않는다.

| 범위 | UTF-8 정규 JSON / root 깊이0 / 전체 node |
| --- | --- |
| case_detail | 8MiB / 16 / 50,000 |
| request | 16KiB / 8 / 256 |
| 반환 전체 포장 | 128KiB / 16 / 8,192 |

개별 문자열은 16,384자, quote는 8,192자, claim.value 깊이는 6이다. 정수는 절댓값 bit length 4096 이하, float는 finite다. 목록은 021 한도인 documents16, cases의 claims64, claim당 evidence8, document당 exhibits64/합계256, document당 page_index200/전체800, relations32/reuse IDs32를 적용한다. PDF 크기 metadata는 개별16MiB/합계64MiB다. 현재 DTO에는 PDF bytes가 없으므로 이 metadata가 실제 bytes와 같은지 재인증하지 않는다. 예산과 정확 타입을 객체 hook·계산 호출 전에 확인한다. 반환 포장에도 별도 예산을 적용하며 초과를 성공으로 바꾸지 않는다.

`case_detail`은 021의 정확 9키: `schema_version`, `kind`, `corpus_id`, `execution_mode`, `synthetic`, `validation_scope`, `verification`, `case`, `documents`다. schema_version은 정수1, kind는 `fcc_report_case`, 실행모드는 `report_derived`, validation_scope는 `source_bytes_and_retained_page_literals_only`이며 synthetic은 bool이다. verification의 정확5키 `hardware_verified`, `physical_verified`, `model_execution_verified`, `normative_compliance_verified`, `coverage_complete`는 모두 false다.

case는 정확7키 `case_id`, `report_group_id`, `document_ids`, `claims`, `relations`, `reuse_group_ids`, `preview`다. ID는 `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`, SHA는 소문자64hex다. preview의 정확17키는 `case_id`, `report_group_id`, `report_number`, `revision`, `issuer_class`, `issue_date`, `scope_status`, `fcc_ids`, `product_family`, `manufacturer`, `models`, `rules`, `methods`, `equipment_models`, `review_status`, `document_ids`, `evaluation_group`이며 문서/사례 ID 대응을 검사한다. evaluation_group은 `eligible`, `keys`, `missing` 3키다. 이 로컬 metadata를 평가 분리 승인으로 해석하지 않는다.

document의 정확8키는 `document_id`, `sha256`, `size_bytes`, `physical_pages`, `exhibits`, `rights`, `extraction`, `page_index`다. extraction은 `status`, `complete`, `total_pages`, `processed_pages`, `parser`, `issues` 6키이며 parser는 `name`, `version`, issue는 `code`, `file_page`다. page_index의 정확5키는 `file_page`, `status`, `text_sha256`, `line_count`, `citable`다. exhibit/rights/relation의 정확10/4/5키와 타입은 021 계약대로 검사하고 URL을 열지 않는다. 물리 고유 SHA와 document ID·페이지의 중복, 크기/페이지 metadata 불일치를 거절한다.

claim의 정확7키는 `claim_id`, `field`, `value`, `unit`, `status`, `basis`, `evidence`다. field는 021의 dotted 식별자, status/basis도 같은 고정 enum이다. 출력 evidence는 정확13키 `document_id`, `source_sha256`, `file_page`, `printed_page`, `table`, `row`, `column`, `footnotes`, `text_sha256`, `line_start`, `line_end`, `quote`, `literal_verified`다. 해당 case/document의 SHA·파일페이지·text hash·line 범위와 page_index를 대조한다. 사용하는 근거는 `literal_verified=true`, `status=ok`, `citable=true`여야 하며 해당 페이지/전역 parser warning·관측 불가·누락 form resource가 없어야 한다. 다른 페이지의 partial/이미지/한도 때문에 문서 전체가 partial이어도 사용 페이지 자체가 정상인 근거는 보존한다.

## 요청 6키와 입력 역할

request의 정확6키는 `calculator`, `rule`, `method`, `input_claim_ids`, `reported_result_claim_id`, `comparison_policy`다. calculator는 위 두 문자열뿐이다. rule/method는 각각 trim한 text(256)이며 reviewed preview와 trim/casefold literal로 일치해야 한다. 판본·정오표·단위·모델 alias를 치환하지 않는다. 경로/제어문자는 요청 문맥으로 받지 않는다.

숫자 입력과 보고 결과는 해당 case의 `reviewed`·`report_fact`여야 한다. 역할을 단위만으로 추측하지 않도록 다음 exact field를 고정한다. 순서는 아래 표 순서이며 caller dict 순서가 결과를 바꾸지 않는다.

| calculator / 역할 | exact claim.field | exact unit / value |
| --- | --- | --- |
| rf_power / reading | `result.rf_power_reading` | dBm / finite int 또는 float |
| rf_power / reported_result | `result.rf_power` | W 또는 mW / finite int 또는 float |
| emc_field_strength / reading | `result.emc_reading` | dBuV 또는 dBµV / finite int 또는 float |
| emc_field_strength / antenna_factor_db_per_m | `correction.antenna_factor_db_per_m` | dB/m / finite int 또는 float |
| emc_field_strength / cable_loss_db | `correction.cable_loss_db` | dB / finite int 또는 float |
| emc_field_strength / preamp_gain_db | `correction.preamp_gain_db` | dB / finite int 또는 float |
| emc_field_strength / instrument_corrections_applied | `correction.instrument_corrections_applied` | null / 정확 false |
| emc_field_strength / reported_result | `result.emc_field_strength` | dBuV/m / finite int 또는 float |

input_claim_ids는 rf_power의 `reading` 1키 또는 emc_field_strength의 위 입력 역할5키와 정확히 같다. 값은 ID다. 역할 간 또는 보고 결과와 같은 claim ID 재사용을 거절한다. true 보정 flag는 중복 보정 위험으로 계산하지 않고, null/unknown/추론 flag를 false로 가정하지 않는다.

사용 수치와 보고 결과에는 공통 `(document_id, source_sha256, file_page, text_sha256)` 페이지 근거가 최소 하나 있어야 한다. 같은 페이지의 다른 표·행도 합성하지 않는다. 모든 수치의 명시된 table/row가 같으면 그 표·행으로 결합한다. table/row가 불명인 항목이 있으면 공통 line 범위가 있어야 하며, 알려진 표·행끼리 상충하면 line이 겹쳐도 거절한다. null·unknown·unconfirmed·not_reported·n/a·미확인·불명·대시(`-`, `–` U+2013, `—`)는 불명 표식이며 같은 행으로 채우지 않는다. 표·행 annotation은 PDF 기하를 재인증한 결과가 아니다. 공통 페이지와 결합 근거는 안정 정렬해 첫 유효 후보를 명시한다. 행 후보 조합 작업은 최대65,536회이며 초과는 limit 오류다.

bool인 instrument_corrections_applied와 제품 family·rule/method·기관 legal_name/address/classification·issue_date의 검토 문맥도 같은 문서의 유효 근거가 필요하되 수치 페이지/행과 같을 필요는 없다. 다른 부분 파일의 문맥을 추측 연결하지 않는다.

known HCT issuer, in_scope, review_status reviewed/partial이 필요하다. product.family, issuer.legal_name/address, report.issue_date, method.rules/references는 reviewed report_fact와 preview가 일치해야 한다. issuer.classification만 021과 같이 reviewed developer_inference를 허용하며 legal_name/address의 report_fact를 대신하지 않는다. 표준 번호만 확인한 standard_reference_only·개발자 추론은 실제 사용 방법의 report_fact로 올리지 않는다. scope_status는 producer의 제공 판정이며 이 순수 함수는 현재 시각이나 보유하지 않은 cutoff를 만들어 재계산하지 않는다.

scalar 문맥의 동등성/상충은 021과 같은 trim/casefold로 대조한다. 예를 들어 `sensor_node`와 ` SENSOR_NODE `는 동등하며, 서로 다른 정규화 값은 부족 상태로 유지한다. 입력의 원문 value·source와 반환 preview 표기는 정규화 값으로 덮어쓰지 않는다.

reported_result_claim_id는 ID 또는 null이다. null이면 comparison_policy도 null이며 기본 출력 단위는 rf_power W, EMC dBuV/m이고 비교는 미실행이다. 보고 결과가 있으면 policy는 정확 `absolute_tolerance`, `unit` 2키로 caller가 finite 비음수 tolerance와 같은 결과 unit을 명시한다. 0 허용, bool 불허다. 이는 개발 비교 정책이며 FCC limit·측정불확도·보고서 decision rule이 아니다.

기존 계산 반환 수치가 기본 결과다. rf_power의 보고 단위가 mW이면 명시적인 W→mW 1000배만 수행해 provenance를 기록한다. 변환 표시값은 float이며 비교값은 `Fraction(native_W)*1000`이다. 원래 0.001W float를 표시용 1.0mW로 반올림해 tolerance0 일치를 만들지 않는다. 정확 변환값의 유리수도 함께 보존한다. float로 정확히 표현할 수 없는 정수 입력·overflow/underflow·nonfinite 결과·형식이 다른 기존 계산 응답은 계산 성공으로 올리지 않는다. tolerance 비교는 원래 계산 반환/정확 단위변환 결과·보고 수치·tolerance를 Fraction의 정확 유리수로 비교하며 반올림/epsilon을 넣지 않는다. 이는 기존 부동소수 계산 수식을 더 정확한 RF 수식으로 대체하는 것이 아니다.

## 반환 정확20키

| 키 | 타입 / 값 |
| --- | --- |
| schema_version, kind | 정수1, `fcc_report_calculation_check` |
| corpus_id, case_id, calculator | 검증한 ID/요청 calculator |
| status | `calculated`, `within_tolerance`, `outside_tolerance`, `insufficient_evidence` |
| reason_codes | 계산/비교 성공에는 [], 부족에는 아래 고정 이유 1개 |
| execution_mode, synthetic | `report_derived`, 원래 scope bool |
| validation_scope | `provided_case_dto_and_claim_source_consistency_only` |
| verification | inherited false5키 + `source_bytes_reverified`, `issuer_authenticity_verified`, `native_raw_observed` false의 정확8키 |
| context | 정확 `rule`, `method`, `issuer_class`, `product_family`; 값은 검증한 문자열 또는 null |
| source_page | null 또는 `document_id`, `source_sha256`, `file_page`, `text_sha256`, `row_binding` 5키 |
| inputs | 아래 claim projection의 배열0..5, 고정 역할 순서 |
| reported_result | null 또는 아래 claim projection |
| calculation | null 또는 `value`, `unit`, `native_result` 3키; native_result는 기존 반환 `value`, `unit` 그대로 |
| unit_conversion | null 또는 `from='W'`, `to='mW'`, `factor=1000`, `basis='explicit_unit_conversion'`, `exact_value_ratio` 5키 |
| comparison_policy | 요청 policy 사본 또는 null |
| comparison | null 또는 `matched` bool, `absolute_difference`, `unit` 3키 |
| interpretation_scope | `reviewer_structured_values_not_literal_semantic_certification` |

claim projection은 정확6키 `role`, `claim_id`, `field`, `value`, `unit`, `sources`다. value는 검증한 원래 숫자/false 타입을 보존한다. sources는 `document_id`, `source_sha256`, `file_page`, `text_sha256`, `line_start`, `line_end`, `table`, `row`의 정확8키이며 원문 quote/URL/파일 경로는 반환하지 않는다. table/row의 경로·제어문자 annotation은 근거로 사용하지 않는다. row_binding은 정확5키 `basis`(`explicit_table_row|common_line_range`), `table`, `row`, `line_start`, `line_end`다. 명시 표·행이면 line 범위는 null, 공통 line이면 알려진 annotation 또는 null을 보존한다. absolute_difference와 exact_value_ratio는 기약 유리수의 십진 문자열 `numerator`, `denominator` 2키다. 각 정수는 4096bits/1234digits 이하이고 임의 float 0으로 표시하지 않는다. 모든 반환은 detached다.

두 유리수의 분자는 비음수, 분모는 양수이며 부호·선행0 없이 기약형으로 기록한다. 차이0은 정확 `"0"/"1"`이고 유효한 RF exact_value_ratio의 분자는 양수다. 음수나 bit/문자 한도 초과는 numeric_representation_unavailable이며 0으로 바꾸지 않는다. 이 숫자 대조는 개발 정책이며 인간/기관의 유효숫자 판정으로 승인하지 않는다.

부족 이유는 `case_context_unconfirmed`, `case_context_conflicting`, `rule_mismatch`, `method_mismatch`, `claim_missing`, `claim_unreviewed`, `claim_basis_unconfirmed`, `claim_role_mismatch`, `claim_type_mismatch`, `unit_mismatch`, `evidence_unconfirmed`, `source_page_mismatch`, `source_row_mismatch`, `row_evidence_unconfirmed`, `context_source_mismatch`, `corrections_already_applied`, `numeric_representation_unavailable`, `calculation_unavailable`다. 유효한 DTO의 미확인·다른 판본/단위/문맥은 정상적인 부족 상태다. 부족 시 계산/비교는 null이고 그때까지 확인한 원래 입력 projection만 보존한다.

`FccReportCalculationError(ValueError)`의 `.code`, `str`, 유일 args는 `fcc_calc_invalid_case`, `fcc_calc_invalid_request`, `fcc_calc_limit_exceeded` 중 하나다. 잘못된 타입/정확키/ID/고정 enum·metadata 대응은 오류이며 부족 근거를 채워 넣지 않는다. 원래 객체·quote·주소·raw exception/cause/context는 오류에 넣지 않는다. quote/literal_verified가 없거나 page_index와 출처가 일치하지 않으면 `fcc_calc_invalid_case`; literal_verified/citable=false 등 제공된 미확인은 `insufficient_evidence/evidence_unconfirmed`다.

검증은 `python -B -X utf8 -m unittest tests.test_fcc_report_calculation -v`로 실행한다. 합성 검증 수, 실제 021 producer의 private DTO 실행 수, 실제 모델/실장비/현장 검증 수를 구분한다.
