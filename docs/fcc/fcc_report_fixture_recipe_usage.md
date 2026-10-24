# 성적서에서 고정 가상 recipe 준비 026 v1

2026-10-24 · Asia/Seoul. `labflow.fcc_report_fixture_recipe.prepare_report_fixture_recipe(case_detail, request) -> dict`는 021의 제공 case DTO를 기존 `conducted_sensor_fixture_v1`의 고정 정책과 대조하는 순수 함수다. 준비 후보는 실행 권한이 아니다. 기존 `describe_fixture_method`만 최대1회 호출하며 runtime/factory/trial/하네스/queue/Store/장비·SDK·SCPI·파일·네트워크·외부 모델을 호출하지 않는다. 023의 private helper를 공개 API처럼 import하지 않는다.

원본 PDF bytes·retained literal의 검증은 021 producer의 역할이다. 여기서는 제공 DTO와 사용 claim의 출처/페이지/행 정합성만 재검사한다. 원본·기관 진위·구조화 값 해석·PDF 표 기하·규정 적합성을 새로 인증하지 않는다. 원문·실제 값은 private, 공개 테스트는 합성 자료다.

## 타입과 예산

정확 built-in dict/list와 JSON scalar만 받는다. subclass·Path·bytes·file-like·callback·임의 객체를 거절하며 객체 hook을 호출하지 않는다. int/float는 bool과 구분하고 float는 finite, 정수 절댓값은4096bits 이하다. 0/false는 누락이 아니다. JSON text helper는 없다. 먼저 detached typed snapshot을 만들고 streaming UTF-8 직렬화 중 bytes 상한을 확인한다.

| 범위 | bytes / root 깊이0 / 전체 node |
| --- | --- |
| case_detail | 8MiB / 16 / 50,000 |
| request | 32KiB / 8 / 1,024 |
| describe 응답 | 32KiB / 12 / 4,096 |
| 최종 반환 포장 | 128KiB / 16 / 8,192 |

개별 문자열16,384자, quote8,192자/40줄, claim.value 깊이6, documents16, claims64, evidence/claim8, exhibits/document64·전체256, page_index/document200·전체800, relations/reuse IDs32, PDF metadata 개별16MiB·합계64MiB다. 행 후보 작업은65,536회다. parser 경고/비관측/누락 form resource·partial의 불명 페이지를 성공으로 올리지 않는다. 숫자 표현/예산/포장 실패에 기본값을 채우지 않는다.

case_detail은 021의 exact9키 `schema_version`, `kind`, `corpus_id`, `execution_mode`, `synthetic`, `validation_scope`, `verification`, `case`, `documents`다. 정수 schema1, kind=`fcc_report_case`, execution_mode=`report_derived`, validation_scope=`source_bytes_and_retained_page_literals_only`, synthetic=bool, verification exact5키 hardware/physical/model_execution/normative_compliance/coverage_complete의 verified 표지는 모두 false여야 한다.

case7/preview17/document8/claim7/evidence13/page_index5/extraction6/parser2/issue2/exhibit10/rights4/relation5의 021 v1 정확 키·타입·ID 대응을 검사한다. claim ID와 document ID/SHA/페이지 중복, case 문서 집합·preview ID 불일치, sourceSHA/textSHA/line 범위 불일치는 잘못된 DTO다. ID는 `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`, SHA는 소문자64hex다. source literal/citable=false 등 제공된 미확인은 부족 상태다. URL은 문헌 metadata이며 열지 않는다.

## 요청 exact7키

`recipe_id`, `model`, `rule`, `method`, `product_claim_ids`, `setting_claim_ids`, `quantity_claim_ids`만 받는다. 앞4개는 비어 있지 않은 문자열이며 recipe/model128자, rule/method256자 이하다. 경로·제어문자를 받지 않는다. 각 selector는 아래 exact role 키의 ID map이고 21개 ID는 서로 달라야 한다. dict 순서로 결과가 달라지지 않는다.

recipe는 `conducted_sensor_fixture_v1`, 요청 model은 정확 `SM-A176U`만 이 첫 대상에 맞는다. 다른 유효 recipe/model은 부족한 근거를 채워서 맞추지 않고 incompatible로 반환한다. 범위 rule의 명시 허용 표기는 `47 CFR 15.247`, `47 CFR §15.247` 두 literal이다. 선택한 요청 표기와 source preview/claim은 trim/casefold로 일치해야 한다. 두 표기를 서로 치환하지 않는다. SAR/HAC/15.255를 이 범위로 재분류하지 않는다.

method는 보고서가 사용했다고 검토된 정확 판본을 요청한다. preview와 reviewed report_fact인 `method.references`에 trim/casefold literal로 일치해야 한다. standard_reference_only·developer_inference를 사용 방법의 report_fact로 올리지 않으며 판본·정오표를 교체하지 않는다. 기존 fixture에는 ANSI 판본 승인이 없으므로 method_approval은 항상 not_assessed다.

product_claim_ids는 exact `family`, `models` 2키다. 각각 `product.family`, `product.models`의 reviewed report_fact를 선택한다. family는 scalar 문자열, models는 문자열 또는 문자열 배열이며 제공 preview와 일치해야 한다. 모델 목록에 요청 model이 있다는 것만으로 다른 모델의 설정 row를 사용하지 않는다. 해당 RF point의 tested_model이 별도로 필요하다. 제품군을 smartphone으로 새로 부여하거나 현재 DUT/HW/FW 지원을 승인하지 않는다.

## 설정 exact16 역할과 계측량 exact3 역할

모든 사용 claim은 reviewed report_fact다. 숫자는 finite int/float, text는 native literal이고 bool을 숫자로 해석하지 않는다. 숫자는 원래 타입을 보존하고 정확 값으로 대조하며 반올림·epsilon·단위 환산·loss/duty/crest 재계산을 하지 않는다. 입력과 fixture의 원래 값은 분리해 반환한다.

| setting_claim_ids 역할 | exact field | native unit | 요구 값 |
| --- | --- | --- | --- |
| power_dbm | setting.dut_power_dbm | dBm | -30..20, 명시된 DUT 설정 |
| frequency_hz | setting.frequency | Hz | 2450000000 |
| bandwidth_hz | setting.bandwidth | Hz | 20000000 |
| modulation | setting.modulation | null | OFDM |
| duty_cycle | setting.duty_cycle | ratio | 0.25 |
| crest_factor_db | setting.crest_factor | dB | 3 |
| attenuation_db | setting.path_attenuation | dB | 10 |
| switch_loss_db | setting.switch_loss | dB | 0.5 |
| coupling_db | setting.coupling | dB | 20 |
| tested_model | setting.tested_model | null | SM-A176U와 trim/casefold 동등한 scalar |
| supply_voltage_v | setting.supply_voltage | V | 5 |
| supply_current_limit_a | setting.supply_current_limit | A | 1 |
| supply_load_resistance_ohm | setting.supply_load_resistance | ohm | 50 |
| chamber_temperature_c | setting.chamber_temperature | C | 23 |
| chamber_humidity_percent | setting.chamber_humidity | % | 45 |
| selected_rf_input | setting.selected_rf_input | null | rf_1 |

quantity_claim_ids는 다음 exact3키다. claim.unit은 모두 null이고 claim.value는 아래 native literal이다.

| 역할 | exact field | 요구 value |
| --- | --- | --- |
| reference_plane | method.reference_plane | sensor_input |
| metric | method.power_metric | on_mean_power |
| quantity_unit | method.power_unit | dBm |

Hz 외 MHz/GHz, C 외 °C 등의 다른 표기/단위는 이 단위에서 자동 변환하지 않는다. result의 측정 전력만 있고 DUT 설정이 없으면 power_dbm으로 쓰지 않는다. DUT output 기준면·peak·time average를 센서 입력 ON 평균으로 바꾸지 않는다. OFDM fixture를 b/g/n 전체 PHY 검증으로 표시하지 않으며 다른 변조/폭/주파수·duty는 고정값 불일치다.

공급 전압/limit/load·온도/RH·선택 RF 입력 6개도 필수 source 설정이다. descriptor나 bootstrap의 값으로 누락을 채워 prepared로 올리지 않는다. target의5V/1A/50ohm/23C/45%/rf_1은 declared_synthetic_policy이며 실물 정격·현재 환경이 아니다. 보조 meter/analyzer 초기화와 취득, sensor calibration_valid=true·triggered acquisition은 별도 미검증 합성 정책으로만 표시한다. 과거 교정 기록을 현재 calibration_valid로 승격하지 않는다.

## point와 별도 문맥 연결

RF point7은 power_dbm/frequency_hz/bandwidth_hz/modulation/duty_cycle/crest_factor_db/tested_model이다. 같은 document/SHA/file_page/textSHA의 같은 명시 table/row 또는 공통 line 범위가 필요하다. 알려진 표·행끼리 상충하면 line이 겹쳐도 거절한다. null·unknown·unconfirmed·not_reported·n/a·미확인·불명·`-`/`–`/`—`는 불명 표식이고 표·행으로 채우지 않는다.

경로 loss3·bootstrap6·quantity3의 context12도 그 document의 유효 근거가 필요하다. 각각 point와 같은 표·행/공통 line으로 직접 결합할 수 있으면 추가 연결은 필요 없다. 하나라도 별도 page/row라면 case 안의 reviewed report_fact, unit=null, field=`setting.setup_binding`인 claim으로 명시 연결한다. request에는 새 selector를 추가하지 않는다.

setup_binding.value는 exact `point_claim_ids`, `context_claim_ids` 2키다. 중복 없는 ID 배열이며 각각 선택한 RF point7 ID 집합과 context12 ID 집합에 정확히 대응한다. 연결 claim도 같은 document의 citable/literal 근거를 가져야 한다. 이 관계는 검수자의 구조화 해석이지 PDF에 기계 ID가 문자 그대로 있다는 뜻이 아니다. 같은 point 집합에 서로 다른 reviewed 연결이 있으면 상충으로 거절한다. 연결을 찾지 못하거나 임의 포함 관계만 있으면 부족이다. 다른 부분 파일의 setup을 추측 연결하지 않는다.

known HCT·in_scope·reviewed/partial 및 기관 분류/법인명/주소·issue_date·rule/method의 검토된 문맥을 확인한다. issuer.classification만 021의 reviewed developer_inference를 허용하고 법인명/주소 report_fact를 대신하지 않는다. 이 일반 문맥은 같은 문서의 별도 페이지여도 된다. scalar 동등성/상충은 021처럼 trim/casefold로 대조하고 원래 value/provenance/preview 표기는 덮어쓰지 않는다. 서로 다른 정규화 값은 부족으로 남긴다.

## 반환 exact24키

| 키 | 값 / 타입 |
| --- | --- |
| schema_version, kind | 정수1, fcc_report_fixture_recipe |
| corpus_id, case_id | 검증한 ID |
| execution_mode | virtual_fixture_preparation_only |
| source_synthetic, target_synthetic | 원래 case bool, 항상 true |
| status | prepared_for_fixed_virtual_fixture / insufficient_evidence / incompatible_with_fixed_fixture |
| reason_codes | prepared이면 [], 그 밖은 아래 고정 이유1개 |
| request_context | recipe_id/model/rule/method exact4키의 검증한 요청 문자열 |
| verification | 023과 같은 false exact8키: hardware_verified/physical_verified/model_execution_verified/normative_compliance_verified/coverage_complete/source_bytes_reverified/issuer_authenticity_verified/native_raw_observed |
| authority | execution_authorized=false/current_authority=false/runtime_created=false/command_count=0/readiness_scope=historical_report_context_only exact5키 |
| method_approval | not_assessed |
| coverage | regulatory_scope_complete=false/phy_coverage=not_assessed/report_reproduction_verified=false/bootstrap_calibration_verified=false exact4키 |
| source_binding | null 또는 document_id/source_sha256/file_page/text_sha256/row_binding/setup_binding_claim_id exact6키 |
| product_bindings | family/models 순의 claim projection 배열0..2 |
| setting_bindings | 위 표 순의 claim projection 배열0..16 |
| quantity_bindings | 위 표 순의 claim projection 배열0..3 |
| context_bindings | field/claim_ids/sources exact3키의 일반 문맥·setup 연결 기록 배열0..8 |
| fixture_descriptor | null 또는 검증한 기존 describe의 exact15키 사본 |
| bootstrap_policy | basis=declared_synthetic_policy/fixed_requirements(위6역할값)/unverified_assumptions/verified=false exact4키 |
| candidate | null 또는 recipe_id/model/settings/source_synthetic exact4키 |
| source_projection_sha256 | null 또는 아래 준비 projection SHA |
| validation_scope | provided_case_dto_and_used_claim_source_consistency_only |

claim projection은 role/claim_id/field/value/unit/sources exact6키다. source locator는 document_id/source_sha256/file_page/text_sha256/line_start/line_end/table/row exact8키이며 원문 quote/URL/파일 경로는 반환하지 않는다. value는 원래 타입/값이다. context_bindings에는 원문 value·quote 대신 claim ID와 source locator만 담는다. 안전하지 않은 경로/제어문자 annotation은 근거로 쓰지 않는다. row_binding은 basis(`explicit_table_row|common_line_range`)/table/row/line_start/line_end exact5키이며 명시 표·행이면 line 범위는 null, 공통 line이면 알려진 annotation 또는 null이다.

기존 descriptor15키는 schema_version/kind/recipe_id/model/supported/reason_codes/settings/quantity/synthetic_setup/method_approval/regulatory_scope_complete/resumable/synthetic/hardware_verified/ai_model_called다. quantity3키와 synthetic_setup9키·고정 literal, synthetic=true/hardware_verified=false/ai_model_called=false/승인미확인·재개불가까지 검사한다. 성공적인 준비에서 describe는 정확1회다. 예외·잘못된 응답·변경된 정책이면 descriptor=null/candidate=null로 거절하고 재호출하지 않으며 그때까지 검증한 binding을 유지한다.

prepared의 candidate.settings는 정확 `power_dbm` 한 키이고 source_synthetic은 원래 source bool이다. 실패/불일치 candidate와 준비 SHA는 null이다. source_projection_sha256은 corpus_id/case_id/source_synthetic/request_context/사용 binding/source_binding/검증한 descriptor/bootstrap_policy의 정규 JSON 사본을 SHA-256 한 준비 기록이다. 같은 원값·selector dict 순서는 같은 결과이며 바뀐 사례/원본 구분/source/provenance는 다른 기록이다. 이는 Store의 readiness_fingerprint·현재 revision·위임·lease를 대신하지 않는다.

unverified_assumptions는 정확한 고정 배열 `sensor_calibration_valid_true`, `triggered_sensor_acquisition`, `auxiliary_meter_analyzer_bootstrap`다. run/instance/intake/revision/lease/token/output_dir/callback/실행용8키 요청을 생성하지 않는다. 다음 실행 단위가 현재 위임·readiness/lease·engine/descriptor·증거 보존을 다시 확인해야 한다. 이 함수의 준비 결과는 역사 보고서 문맥에 한정되고 실물 전원/RF OFF·안전 정지·실측·실제 AI·FCC/ANSI 승인이 아니다.

## 상태와 고정 오류

부족 이유는 case_context_unconfirmed/case_context_conflicting/method_context_unconfirmed/claim_missing/claim_unreviewed/claim_basis_unconfirmed/claim_role_mismatch/claim_type_mismatch/evidence_unconfirmed/source_page_mismatch/source_row_mismatch/row_evidence_unconfirmed/context_source_mismatch/setup_binding_missing/setup_binding_conflicting/fixture_contract_unavailable/fixture_contract_changed다.

불일치 이유는 recipe_mismatch/model_mismatch/rule_scope_mismatch/setting_value_mismatch/unit_mismatch/reference_plane_mismatch/power_metric_mismatch/quantity_unit_mismatch다. 입력값이0/false인 불일치를 missing으로 바꾸지 않는다. 모든 값·출처/행을 확인하기 전에는 준비를 완료하지 않는다.

`FccReportFixtureRecipeError(ValueError)`의 code/str/유일 args는 `fcc_recipe_invalid_case`, `fcc_recipe_invalid_request`, `fcc_recipe_limit_exceeded` 중 하나다. 잘못된 타입/정확 키/ID/고정 enum·metadata 대응은 오류이며 정상적인 근거 부족·고정 fixture 불일치와 구분한다. raw exception/원문/주소/cause/context를 오류에 넣지 않는다. 예외·출처·포장 실패를 prepared나 기본값으로 바꾸지 않는다. 모든 반환은 detached다.

전용 검사는 `python -B -X utf8 -m unittest tests.test_fcc_report_fixture_recipe -v`다. 합성 정상/거절과 실제021 DTO의 부족 처리, 기존 method adapter/facility/Fleet/023 회귀 및 문서 무결성을 따로 기록한다. 실제 적용 가능한 RF 설정이 미확보이면 실제 recipe 준비 성공은 미실행으로 남기고 SAR/HAC/15.255 사례를 가짜 성공으로 만들지 않는다.
