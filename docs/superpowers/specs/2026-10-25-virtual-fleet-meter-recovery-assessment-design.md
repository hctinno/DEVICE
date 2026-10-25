# 가상 meter 주파수 복구의 별도 근거 평가 계약 v2

2026-10-25, Asia/Seoul. DEV2-METER-RECOVERY-INDEPENDENT-ASSESSMENT-CONTRACT-20261025-001의 공개 설계 v2다. [계획](../plans/2026-10-25-virtual-fleet-meter-recovery-assessment.md)을 따른다. 사전 private 근거 지도·원문 pin과 실패 기록은 총괄 인수 영수증으로 보존한다. 최신 읽기 기준은 통합042 게시 `70533f8ac3fd15f2260b60473de80be4e8e7d8cc`/기능 `530b5306c82f02b6271584b72206a01a4d3cf3f2`이며 정책349a는 통합041에서 인수했다. 정확 구현 base/전용 branch·신규3은 공개 게시와 독립 기대 봉인 인수 뒤 별도 배정한다. 아직 새 제품/API/test/fixture 실행은0이다.

v1의 정적 No/I1은 advance에 없는 node identity/setup_changed를 요구한 계약 충돌이다. 원 v1 exact3·root intake·원 실패는 동결하고 이 sibling v2에서 receipt 규칙만 operation별로 나눈다. 나머지 계약과 새로운 source-blind 기대 봉인 절차는 유지한다. v2 독립 정적 delta는 Yes/C0I0M0이며 제품·가상 run 수용이나 새 기대 봉인 결과가 아니다.

## 1. 확인한 공백과 재사용

`RFMeterFrequencyRecoveryPolicy`의 completed는 fixture 주장이다. 기존 report15의 assessment/task_outcome/cleanup은 not_assessed다. 기본 `evaluate_sensor_run`은 SensorTrial·sensor goal4·전용 author 수치에 의존한다. 041 `evaluate_rf_signal_scenario`는 고정 policy/scenario·디스크 author/journal·고정 수치를 전제하므로 recovery goal6의 평가로 사용할 수 없다. **새 goal의 위임·충돌·제한 수정·양쪽 새 취득과 독립 scalar RF 산술을 대조하는 별도 결과가 실제 공백이다.**

| 경로 | 재사용 판단 |
|---|---|
| 기존 FleetHarness/report/events | report15·operator_event8/7종과 intent→receipt→cause observation을 그대로 소비. 원 필드·원본·engine pin·parent 프로토콜 변경 0 |
| `read_operator_journal` | 필요하면 caller가 기존 공개 reader를 함수 밖에서 호출해 events를 메모리로 제공. 새 API 내부의 파일/reader 호출 0 |
| 저장 `read_rf_signal_run` | 보관 hash·historical assessment·요약 DTO용. 새 recovery의 raw trace나 현재 평가 PASS를 대체하지 않음 |
| 기존 sensor/041 evaluator | 형식·행동 계약을 참고하되 호출·private helper import·숫자/수용 결과 재사용 0 |
| 인수한 정책 source/usage | 허용된 두 고정 파일만 읽어 목표·지원·출력 계약을 확인. owner tests/trace와 독립 봉인 oracle 본문은 미열람 |

원 report에 평가를 덮어쓰는 안은 원 not_assessed와 과거 의미를 바꾸므로 선택하지 않는다. **별도 순수 메모리 assessment API 1개**를 선택한다. wrapper/CLI/reader/registry/평가 framework를 추가하지 않는다. provider·모델 선택과 독립이며 계정·송신·과금은 필요 없다.

## 2. 최소 소유·공개 API

사전 소유안은 신규 `labflow/virtual_fleet/meter_recovery_assessment.py`, `tests/test_virtual_fleet_meter_recovery_assessment.py`, `docs/fcc/virtual_fleet_meter_recovery_assessment_usage.md`의 core1/test1/usage1이다. 지금 파일을 만들거나 base/branch를 바꾸지 않는다.

API는 `assess_meter_frequency_recovery(report, events, *, declaration) -> dict` 한 개와 고정 오류 `MeterRecoveryAssessmentError(ValueError)`다. 표준 라이브러리만 사용한다. runtime·policy·기존 evaluator·RF engine·journal reader를 import/호출하지 않고, caller의 native JSON 메모리를 검증·분리 복사해 계산한다. 디스크/DB/worker/UI/모델/장비 동작·UUID/시각 생성은 0이다.

### 입력 declaration exact8

| 필드 | 계약 |
|---|---|
| schema_version / kind | plain int 1 / `meter_frequency_recovery_declaration` |
| goal | 공개 goal exact6: kind=`acquire_fresh_rf_sensor_meter`, 서로 다른 dut_id/sensor_id/meter_id, plain 비음수 minimum_acquisition_tick, plain bool allow_meter_frequency_reconfigure |
| catalog | caller가 제공한 전체 native JSON catalog. profiles의 고유 profile_id/role/ports와 topology의 profile binding을 검사. 모델 이름으로 옵션/교정·현장 지원을 추정하지 않음 |
| topology | devices(id/profile_id)·connections(source/target device_id/port, kind)의 기존 선언. 선택 RF 경로와 sensor.measurement→meter.sensor 연결을 결합 |
| role_actions | 기존 역할별 action/parameters type·required 선언. 아래 허용 action과 frequency-only configure 형상을 대조 |
| budgets | decisions/logical_requests/ticks/wall_seconds/transport_retries exact5. 앞 셋은 plain 양수 int, retries는 plain 비음수 int, wall_seconds는 양수 유한수. 생략/default 상속 없음 |
| rf_basis | 아래 합성 산술의 사전 선언. 계산된 expected 결과·oracle·seed·author 객체는 받지 않음 |

catalog/topology/role_actions는 기존 metadata 중 필요한 identity/role/port/action과 연결을 검증한다. 관련 없는 native metadata는 한도 안에서 보존·hash하며 판단 근거로 승격하지 않는다. report는 기존 exact15, events는 기존 event exact8/7종의 배열이다. 관측 node와 execute receipt는 기존 node identity를, advance receipt는 아래 global envelope를 따른다. receipt 안에 없는 action/request_id나 advance의 node identity/setup_changed를 만들지 않고 해당 intent와 연결한다.

### rf_basis exact6와 지원 범위

필드는 `simulation_basis='declared_synthetic_policy'`, `source_signal`, `path`, `meter_noise_db`, `meter_gain_error_db`, `external_runtime_mutations`다. noise/gain error는 plain 유한수이고 v1 수치 지원은 둘 다 0일 때뿐이다. external_runtime_mutations는 정확 bool이며 v1은 False만 지원하고 True는 unsupported_target이다. 이 세 값은 관측되지 않은 상태에 대한 **caller 선언**이다. 비제로 수치는 native 형상 오류가 아니라 numeric 미지원으로 구별한다.

source_signal은 frequency_hz/power_dbm/bandwidth_hz/duty_cycle/crest_factor_db/modulation exact6다. 숫자는 bool을 제외한 유한수, frequency/bandwidth 양수, 0<duty<=1, crest>=0, modulation은 비공백 UTF8 문자열이다. DUT의 유효 현재 RF 출력과 각 값을 대조한다. 목표가 power/frequency를 직접 포함하지 않으므로 이 선언과 관측의 일치는 의뢰 요구 적합성을 증명하지 않는다.

path는 1…16개의 `{device_id,input_port,output_port,loss_db}` exact4 순서 배열이다. loss는 유한 비음수 dB다. DUT.rf부터 sensor.rf까지 topology의 실제 선언 edge와 순서·port kind를 결합하고, 중복/순환·누락·다른 분기 사용은 수용하지 않는다. v1은 attenuator·rf_switch·coupler의 상수 scalar 손실 경로를 지원한다. coupler.coupled에는 coupling 손실만 사용하고 through 손실을 더하지 않는다. 표·보간·antenna/splitter/filter/다중 활성 경로는 지원 밖이며 상수로 대체하지 않는다. 관련 catalog에 loss_table 등 동적 손실이 선언됐으면 unsupported numeric model로 남긴다.

현재 노출된 RF 관측에는 실행 전 경로의 모든 설정이 없다. path.loss_db는 caller의 사전 설정 선언이며 실제 사용된 물리/가상 설정의 독립 증명이 아니다. catalog의 profile/role/port와 지원을 확인해도 이 한계는 같다. 실행 중 경로 변경 action은 허용하지 않는다. full catalog의 meter noise_db(생략 시 공개 합성 기본값 0)가 0과 다르거나 선언 gain error가 0이 아니면 v1 절대 산술은 지원하지 않는다. 숨은 고장이 없었다는 실제 증명은 하지 않는다.

meter의 관측 설정은 on_average/dBm/window plain int 1/trigger_source immediate만 지원한다. 다른 최초 설정은 unsupported다. 이를 맞추기 위한 일반 설정·교정/reset/recover를 허용하지 않는다. 개별 sample의 다른 unit/window/quantity/source는 지원 확장이 아니라 선언과의 관측 모순이다.

## 3. 선언과 관측의 경계

| caller 미검증 선언 | 메모리 근거로 대조 가능한 것 | 끝까지 증명하지 않는 것 |
|---|---|---|
| goal·위임 bool·사전 봉인 시점 | 제공된 위임과 configure intent의 일관성 | 실제 기관/사용자 위임·사후 goal 변경 여부 |
| catalog·topology·역할·실행 전 RF 설정/무잡음·무bias | 제공 metadata와 관측 identity/연결, 독립 산술의 조건부 일치 | 제조사/FW 지원·실제 설정·교정·숨은 mutation 부재 |
| runtime/run ID·보관 상태 | report와 모든 event가 같은 ID이고 연속 관계인지 | 실제 동일 runtime/원 요청 ledger·파일 hash-chain의 진위 |
| budgets·elapsed_ms | 기록된 decision/intent/retry/tick 카운터와 한도 | 실제 wall clock·물리 송신 횟수·원격/실물 상태 |

H(x)는 exact native JSON을 UTF8/ensure_ascii=False/sort_keys=True/구분자 compact/allow_nan=False로 직렬화한 SHA256이다. 입력의 declaration/report/events 각각과 `{declaration,report,events}` 전체를 결합한다. 이 hash는 제공 메모리의 식별이며 보관 파일의 원 bytes/hash나 독립 봉인 증명이 아니다. owner oracle·제품 결과를 입력 expected로 받지 않는다.

## 4. 사건 결합·첫 오류·예산

1. event schema1/kind operator_event·sequence/event_id의 연속·고유성, 동일 run_id/runtime_instance_id, 7종 payload를 검사한다. 마지막 termination은 최대 1회며 이후 event는 모순이다. 빈 목록/올바른 prefix의 termination 누락은 evidence incomplete다. 중복 ID·clock 역행·서로 다른 runtime은 관측 모순이다.
2. intent의 logical_request는 1부터 증가하고 고유 request_id를 가진다. 직전 policy_decision proposal과 operation/body가 같다. receipt는 미결 intent에 딱 한 번 결합하며, cause observation은 해당 receipt 뒤 같은 tick/revision을 대조한다. execute에만 receipt의 device/profile/role을 해당 node와 결합한다. advance는 global receipt이므로 receipt 자체에 node identity를 요구하지 않지만 cause observation의 각 node identity/clock은 종전대로 검증한다. 성공적인 완전 run은 intent/receipt/cause observation이 모두 닫혀야 한다.
3. 실행 허용은 DUT start, sensor acquire/read, meter acquire/fetch, meter configure(frequency_hz **단 한 parameter**), advance(ticks plain int 1), stop이다. role_actions가 지원해도 다른 action/parameter를 새 권한으로 보지 않는다.
4. retry marker는 미결 request_id와 증가하는 retry 번호에만 결합한다. 같은 ID/body의 marker는 새 configure logical intent로 세지 않는다. 실제 runtime dispatch/물리 전송 횟수는 event로 증명할 수 없으므로 그 횟수를 산출했다고 표시하지 않는다.
5. receipt 규칙은 아래처럼 operation별로 적용한다. 없는 필드를 False/None/node ID로 채우거나 공통 필수값을 생략하지 않는다.

   | operation | 실제 필수 receipt·tick/revision 규칙 |
   |---|---|
   | execute | 허용된 알려진 node의 device_id/profile_id/role binding과 plain bool setup_changed를 요구한다. tick은 intent 직전 tick, setup_revision은 직전 관측 revision+int(setup_changed)다. 기존 execute의 설정/관측 모순 판정은 유지한다. |
   | advance | global exact6은 status/values/tick/setup_revision/synthetic/hardware_verified다. status=ok, values exact1의 advanced_ticks는 plain int 1, synthetic=True/hardware_verified=False, tick은 직전 tick+1, setup_revision은 plain 비음수 int로 직전 관측 revision 이상이다. device_id/profile_id/role/setup_changed는 이 receipt의 필드가 아니다. |

   core.advance는 _propagate를 거친 뒤 global envelope를 만든다. 정상 대기에서는 revision이 같지만 새 quarantine으로 내부 revision이 증가할 수 있어 advance에 무조건 revision 불변 또는 가상의 setup_changed 증분을 요구하지 않는다. 증가 자체를 설정 권한/성공으로 해석하지 않는다. 같은 runtime·외부 mutation 없음의 이 선언 범위에서 cause observation은 해당 receipt의 tick/revision과 같아야 하며, 최신 node 상태·취득 revision·미결/오류 판정은 그대로 유지한다. 역행/잘못된 결합은 모순이고, 전파 오류·stale/불가 상태는 해당 근거에 따라 판정하며 advance envelope 수용만으로 완료를 내지 않는다.
6. report usage의 logical_requests/transport_retries/tick_delta/reserved_ticks를 intent/retry/초기·마지막 관측/미결 advance와 대조한다. 정상 완료의 decisions는 policy_decision 수와 같다. policy_call_error/invalid_proposal 등은 callback 이후 decision event가 없을 수 있으므로 usage가 1 더 큰 것을 곧바로 조작으로 판정하지 않는다. evidence_error·정확히 복원 못한 카운터는 inconclusive이며 PASS로 보완하지 않는다.
7. 선언 예산을 넘긴 관측은 fail이다. 적법한 budget 종료·supervisor_stop은 goal 완료를 입증하지 않아 inconclusive다. wall_deadline/elapsed_ms만으로 실제 시간 준수 PASS를 내지 않는다. runtime_mutation_uncertain·미결 intent·timeout은 inconclusive이며 재실행/복구/추측을 하지 않는다. completed claim과 미결 상태의 명시적 모순은 fail이다.
8. 원 error event·실패 receipt는 제거하지 않는다. 최초 error event ID와 최초 invalid/unsupported/error/disconnected receipt event ID를 각각 반환한다. 예상된 conflict invalid receipt도 후자에 남는다. 원 code/exception/string을 새 것으로 덮거나 raw로 복사하지 않는다.

report.evidence.measurement_refs는 관측 ID에만 연결하고 가능한 유효 sample의 관측인지 대조하되, 단순 measurement ref를 완료 증거로 쓰지 않는다. report termination claim은 최종 policy_decision stop과 대조한다. 원 report의 task_outcome/assessment/cleanup은 not_assessed 그대로여야 하며, 이미 평가된 report를 다시 현재 평가로 승격하지 않는다.

## 5. 복구·새 취득의 증거 조건

**실제 기록된 충돌**은 새 meter.acquire intent → 그 request의 invalid receipt(reason sensor_frequency_setting_conflict) → 그 receipt의 cause observation에서 meter invalid/동일 reason/measurement 없음이 모두 있어야 한다. 같은 현재 revision의 유효 sensor가 있고 abs(meter configuration.frequency_hz−sensor.frequency_hz)>1Hz이어야 한다. bootstrap의 cached reason·configure ACK·정책 reason 문자열만으로 충돌을 인정하지 않는다.

| 분기 | 요구 근거 |
|---|---|
| 최초 주파수 차이 <=1Hz, 정상 취득 | configure logical 0. 새 sensor acquire/read와 새 meter acquire/fetch·최신 관측을 요구 |
| 충돌·위임 false | configure logical 0, completed 0, 관측 충돌과 blocked stop. 조건부 계약 pass일 수 있으나 observed_goal은 not_satisfied |
| 충돌·위임 true | 관측 sensor.frequency_hz를 **정확히 복사한** frequency-only configure logical 1. 1Hz 허용오차를 수정 target의 복사 오차로 사용하지 않음 |
| 수정 성공 | 해당 configure receipt ok/setup_changed true, global revision+1, meter configuration_revision+1, frequency 외 configuration 동일, receipt와 현재 meter 설정 일치·meter 옛 outputs 없음 |
| 수정 거절/응답 불명 | 새 logical configure 재시도 0. known rejection 뒤 blocked는 fail-closed 관측이며 거절 receipt와 cause observation에서 설정/config revision 불변·setup_changed false를 요구. 비성공인데 변경됐으면 모순이다. 응답 불명·미결은 inconclusive. ACK를 취득으로 취급하지 않음 |

configure 뒤 sensor의 옛 sample은 새 완료 근거에서 폐기한다. 새 sensor acquire/read는 configure 뒤 sequence이며 sample acquisition_tick은 자기 acquire intent tick보다 늦고, max(goal.minimum_acquisition_tick, configure receipt.tick+1) 이상이다. configure가 없으면 초기 관측 tick보다도 늦고 원 minimum 이상이어야 한다.

새 meter acquire intent는 선택한 새 sensor read/관측 뒤여야 한다. meter sample acquisition_tick은 자기 acquire intent tick과 sensor acquisition_tick보다 모두 늦다. sensor/meter sample은 그 취득 intent·최종 관측의 공통 최신 setup_revision과 같고, meter configuration_revision은 현재 설정·취득 receipt와 같다. configure 이후 DUT start 등이 global revision을 더 바꿀 수 있으므로 최종 revision을 configure 직후 숫자로 고정하지 않는다.

sensor sample은 source_id=sensor_id, unit=dBm, value=power_dbm이며 upstream RF packet·DUT 신호의 주파수/duty/crest와 결합한다. meter sample은 source_id=meter_id, input_source_id=sensor_id, unit=dBm, quantity=on_average, window=1, simulation_basis=declared_synthetic_policy이며 현재 meter frequency가 sensor의 1Hz 이내다. read/fetch receipt의 sample은 그 cause observation의 같은 signature와 같아야 한다. 최종 유효 관측·DUT RF·sensor·meter가 모두 있어야 완료를 인정한다.

동값의 old revision·다른 source/input source·unit/window·누락 fetch·수정 뒤 재사용된 옛 취득은 수용하지 않는다. 완전 transcript에 필수 action이 없으면 fail, 해당 구간이 없는 prefix/미결이면 inconclusive다. complete transcript의 근거 없는 completed·blocked 주장도 fail이다. 관측된 calibration/readiness block에 맞는 제한 정지는 조건부 계약 pass/goal not_satisfied로 구별한다. 이때 관련 요청의 실패 receipt와 cause observation의 불가 상태/이유가 맞아야 하며, 정책 stop의 reason 문자열만으로 block을 인정하지 않는다.

## 6. 독립 scalar 산술

제공 source_signal의 ON 평균 P에서 선언된 선택 path의 각 손실을 순서대로 뺀다. 각 노드 출력의 예상 ON 평균과 최종 sensor/meter 값을 이 합에서 **독립 계산**한다. engine/기존 evaluator/정책의 계산 helper나 반환값을 expected로 사용하지 않는다. 모든 비교의 절대 허용오차는 1e-9dB다.

`P_sensor = P_source − Σ L_selected_path`, `P_meter(on_average,dBm,window1) = P_sensor`다. duty를 재곱하거나 crest/through loss를 더하지 않는다. 표준 PHY·I/Q·실제 취득 aperture·교정·불확도·안전/규범 판정은 이 수식의 범위 밖이다. 유효하지 않은 source/경로 선언·미지원 표/비제로 noise/bias·유한 결과를 못 내는 산술은 numeric inconclusive이며 상수 정답으로 채우지 않는다. metadata/위임/행동의 이미 확인된 모순은 이 산술 미지원으로 지우지 않는다.

sensor와 meter가 서로 같은 오답인 경우에도 독립 경로 합과 맞지 않으면 fail이다. 단순 상호대조 일치·fixture completed·과거 PASS를 산술 성공으로 상속하지 않는다. rf_basis의 실제 사용 여부는 caller 미검증 선언이므로 일치 결과는 제공 합성 모델에 대한 조건부 평가다.

## 7. 별도 결과와 판정 우선순위

출력 exact15는 schema_version=1, kind=`virtual_meter_recovery_assessment`, mode=`synthetic_evidence_contract_assessment`, status, verdict, observed_goal, bindings, reason_codes, checks, arithmetic, counts, evidence_refs, first_errors, verification, limits다.

| 필드 | 고정 의미 |
|---|---|
| status/verdict | status assessed이면 verdict pass/fail/inconclusive. 다른 goal/policy/최초 meter 모드 또는 이미 평가된 report는 status unsupported/verdict null. 지원 밖을 성공으로 만들지 않음 |
| observed_goal | satisfied / not_satisfied / unverified. 안전한 blocked의 계약 pass도 goal 완료는 아님 |
| bindings | declaration_sha256/report_sha256/events_sha256/input_sha256/run_id/runtime_instance_id exact6 |
| checks | event_binding/delegation_and_actions/conflict_and_configure/fresh_sensor/fresh_meter/budgets/rf_arithmetic exact7. 각 pass/fail/inconclusive/not_applicable |
| arithmetic | basis=`declared_scalar_on_average`, status matched/mismatched/not_available/unsupported, expected_sensor_dbm/expected_meter_dbm/observed_sensor_dbm/observed_meter_dbm은 유한수 또는 null, tolerance_db=1e-9 exact7 |
| counts | events/observations/logical_requests/transport_retry_markers/configure_logical_attempts/successful_configures/sensor_acquire_intents/sensor_read_intents/meter_acquire_intents/meter_fetch_intents exact10. 기록 건수이며 실제 dispatch 수가 아님 |
| evidence_refs | 실제 event ID의 고유 배열, 최대32. 선택 initial/conflict/configure/acquire/read/fetch/final/termination 및 최초 모순 ref를 우선하고 임의 ref를 만들지 않음 |
| first_errors | first_error_event_id / first_failed_receipt_event_id exact2, 각각 실제 ID 또는 null. 원 입력 오류는 수정하지 않음 |
| verification | 아래 exact12의 수행 범위. 임의 종합점수·모델 점수·원 report 교체 필드 없음 |

verification exact12는 synthetic=True, hardware_verified=False, ai_model_called=False, input_values_unchanged=True, storage_integrity_verified=False, runtime_authenticity_verified=False, delegation_authority_verified=False, pre_run_configuration_verified=False, hidden_fault_absence_verified=False, model_quality_verified=False, physical_cleanup_verified=False, source_currentness_verified=False다. input_values_unchanged는 actual detached copy만 사용하고 원 입력과의 canonical byte 전후 대조를 수행한 결과다. 항상 false인 권한/진위 flag를 단순 hash 일치로 true로 만들지 않는다.

observed_goal=satisfied는 완전하고 결합 가능한 최종 근거에서 새 양쪽 취득/read/fetch와 독립 수치가 모두 입증될 때만 사용한다. 이 값은 정책 claim과 분리하므로 목표 값이 있어도 위임/행동 위반의 verdict는 fail일 수 있다. not_satisfied는 완전·지원되는 최종 상태에서 필수 목표 증거가 실제로 없거나 관측된 fail-closed block이 있을 때다. prefix/미결/진위 결합 모순·수치 미확인·지원 밖에서는 unverified를 사용한다. unsupported 결과는 observed_goal=unverified다.

판정은 **확인된 fail > 근거 부족/inconclusive > pass** 순서다. pass는 정상 새 취득·산술·행동을 모두 만족했거나 관측된 위임 거절/준비 불가/설정 거절에 맞게 fail-closed 종료한 경우다. 후자는 수행 불가 측정 check를 not_applicable로 남기며 goal은 not_satisfied다. 예산/일반 중단/미결·누락은 pass가 아니다. 처음부터 지원 밖인 대상은 unsupported/null이며 선언/입력 형상 오류와 구별한다.

reason_codes는 다음 고정 ASCII 집합의 중복 없는 정렬 배열(최대32)이다: goal_satisfied_without_reconfigure, goal_satisfied_after_recovery, declared_reconfiguration_denied, readiness_block_observed, configuration_rejection_observed, evidence_incomplete, execution_unresolved, budget_exhausted, wall_time_unverified, numeric_basis_unavailable, event_binding_mismatch, event_order_mismatch, unexpected_action, reconfigure_without_delegation, conflict_not_observed, configure_parameter_mismatch, configure_attempts_exceeded, configure_revision_mismatch, stale_measurement, measurement_binding_mismatch, missing_required_action, arithmetic_mismatch, report_transcript_mismatch, budget_violation, unsupported_target, unsupported_numeric_model, report_already_assessed. 첫 error/실패 receipt의 원 시간순 참조와 이 정렬 결과는 서로 다른 것이다.

## 8. 자원·native 형상·고정 오류

limits exact9는 max_input_bytes=33554432, max_output_bytes=131072, max_events=4096, max_event_bytes=524288, max_depth=32, max_nodes=200000, max_path_terms=16, min_integer=−9223372036854775808, max_integer=9223372036854775807이다. 모든 입력 합/중간 JSON 변환에 점진적 byte·node·depth 한도를 적용하며 output도 검사한다. 기존 harness/journal 상한을 새 평가의 무제한 메모리 허용으로 사용하지 않는다.

native는 정확 dict/list/str/int/float/bool/None만 허용한다. subclass·cycle·비UTF8 surrogate·비유한 float·범위 밖 int·object hook/callback은 실행하지 않고 거절한다. 식별자는 기존 harness ASCII 문법 `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`을 따른다. 사건 수·경로 수·큰 metadata도 복사/직렬화 전에 제한한다.

오류 code/str/args는 `meter_recovery_assessment_` 뒤 invalid_input/limit_exceeded/internal_error 중 하나, 같은 문자열, (같은 문자열,)이다. 원 값/경로/exception을 넣지 않는다. public wrapper는 활성 caller except 안에서도 __context__/__cause__가 None이 되도록 실제 raise/catch 후 정리·같은 bare rethrow로 경계를 닫는다. KeyboardInterrupt/SystemExit/GeneratorExit 등 BaseException 제어 신호를 정제 오류로 삼키지 않는다.

검증 순서는 declaration→report→events의 native 복사/총 자원 한도, declaration 고정 shape/type, report/event 필수 envelope shape/type, 대상 지원, 사건 결합/행동/측정/산술 순서다. 형상·native 위반은 invalid_input, 최초 도달 자원 위반은 limit_exceeded, 예상 밖 구현 Exception은 internal_error다. 유효 형상의 누락 prefix·관측 모순·미지원은 앞 절 결과로 반환한다. malformed 반환/원본 변경/예외를 success로 대체하지 않는다.

## 9. source-blind 사전 기대와 후속 수용

현재 문서의 규칙·owner 제안은 독립 정답이 아니다. 총괄이 새 assessment 구현·정책 후보 source/owner test/trace 및 원 독립 oracle를 보지 않은 reviewer에게 **다른 metadata 입력·사건 기대·수학 oracle**를 먼저 작성/봉인하도록 배정한다. 허용 공개 계약·역할 metadata를 제공하되 owner 수치 예시/출력은 정답 자료에서 분리한다. 후보 출력·기존 fixture 숫자를 expected 생성에 사용하지 않는다. oracle의 값은 손계산/별도 독립 계산과 units·tolerance·입력/hash로 확인한다. 이 설계 작성자의 허용 source 검토는 독립 reviewer의 source-blind 봉인을 대신하지 않는다.

봉인은 두 층이다. (1) 구현·첫 호출 전, 원인별 test case 입력/판정 규칙·독립 scalar 산술 및 reference/counter 기대를 봉인한다. (2) 후속 실제 가상 run의 무수정 report/events가 생기면 그 입력 hash를 append하고 기존 기대의 어떤 항목을 적용했는지 연결한다. 예상과 다른 제품 결과에 맞춰 기존 oracle/label을 덮지 않는다. missing/지원 밖을 PASS로 바꾸지 않는다.

기대에는 정상 configure0, 위임true 충돌/논리1회, false block/0회, 설정 실패·미결, 동값 stale revision·source/window/unit/fetch 누락, retry marker와 새 logical2의 구분, 예산·wall time, 같은 오답의 sensor/meter, 표/비제로 noise 미지원, context-free 오류/제어 신호와 입력 불변을 포함한다. 과거 PASS·owner 수·독립 수·실제 가상 호출·실물·모델을 합산하지 않는다.

I1의 정적 사전 수용 case는 아래와 같다. **현재 모두 미실행이며 독립 oracle 봉인이 아니다.** 기존 API 오류/결과 범주와 fail 우선순위는 유지한다.

| case | 닫을 기대 |
|---|---|
| ADV1 정상 global | 실제 exact6, plain advanced_ticks=1, tick+1/동일 revision, cause 관측 일치. identity/setup_changed 없이 receipt 단계 수용; 전체 목표 PASS를 뜻하지 않음 |
| ADV2 내부 전파 revision 증가 | global receipt의 revision이 직전보다 크고 cause 관측은 그 최신 revision. advance 불변 가정으로 거절하지 않으며 새 node 오류·미결·최신 sample 요건을 그대로 판단 |
| ADV3 필수값·타입/값 위반 | status/values/tick/revision/flags 또는 advanced_ticks 누락·타입 위반은 기존 invalid_input, 유효 형상의 status/advanced_ticks 값 모순은 fail. bool True를 정수1로 수용하지 않음 |
| ADV4 잘못된 clock/cause | tick+1 위반·revision 역행·완전 trace의 잘못된 cause는 기존 fail. cause 구간 없는 올바른 prefix는 기존 inconclusive |
| ADV5 가짜 node/boolean | advance에 node identity/setup_changed를 덧붙여 정상화하지 않으며 실제 exact6 밖의 필드는 invalid_input. 원 입력 수정0 |
| EXEC1 면제 전파 금지 | execute의 실제 node identity·plain bool/증분 규칙은 그대로다. advance 면제를 execute에 적용하거나 필수 필드 누락을 포괄 허용하지 않음 |

이 공개 계약에 앞선 private v2의 검증은 UTF8/JSON/로컬 링크·선택 source pin·정적 일관성 및 `python scripts/check_artifacts.py`뿐이다. 실제 구현/test fixture/정책·runtime·evaluator/API 실행, DB/모델/실물 검증은 미실행이다. 별도 synthetic assessment PASS도 AI 품질·cleanup·실장비·규범·전체 RF·EMC 시험소 완료를 뜻하지 않는다.
