# 가상 Fleet RF 신호 시나리오041 — 고정 설계

2026-10-24 Asia/Seoul. 총괄이 소유 v3 제안 전체와 독립 최종 정적 **Yes C0/I0**를 확인해 고정한 구현 계약이다. 개발3이 신규3파일을 맡는다. 현재019의 실제 코드 검증과 앞으로041의 합성 실행·평가를 구별한다. [구현 계획](../plans/2026-10-24-virtual-fleet-rf-signal-scenario.md)을 따른다.

기준 게시019는 `a028f8a8fc9165b6dde14c7cdd4de6d0b7046ac6`, 기능20b5185/전체1777Python·114Node/소스202다. v1의 catalog 변형 수용 I1과 v2의 저장후 manifest 실패 I2를 소유 계약 수정으로 닫았다. v1/v2/No/중단 기록을 보존하며 정적 Yes가 구현 수용·7시나리오 실행을 뜻하지 않는다. v3 제안 SHA는 `1d4e0ea99b17e51b0fdcbf17e5ce4374b8b5efbfdba80285b66b311522ff8bdb`, 별도 선언 데이터 SHA는 `62d34f8bd07621ac2aafe0d98f36adc13dbbff1ceff360962384be8f609a8ba6`, 독립 최종 영수증 SHA는 `f765c34bf0d22a0a08daa1c0c6fc263930294d465096f9492e3f8bc80f32aa11`다. 모두 합성 선언/계약이며 원문 보고서·실측값을 포함하지 않는다.

## 지원 catalog의 고정 범위

041 첫 버전은 현재 공개 [catalog](../../../virtual_profiles/sm_a176u_unlicensed.json)의 **validated canonical JSON fingerprint가 정확히 같은 입력만** 지원한다.

| 항목 | 고정 계약 |
| --- | --- |
| canonical | `json.dumps(validate_catalog(snapshot), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')` |
| SHA-256 | `6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff` |
| 기준 크기·구조 | canonical 56,970 bytes, 64 profiles, 키도 세는 node 4,590개, root=0 최대 depth5 |
| 확인 기준 | own036 HEAD `ea768900f105bbb925ce7624ada64355fe48a019` 및 총괄 commit `1880476e6d13e1198d104f22f6988e58e99a6eb0`의 catalog canonical 동일 |
| 동치 허용 | 객체 key 순서·JSON 공백만 달라도 canonical bytes가 같으면 허용 |
| 변환 금지 | 값/타입/int↔float/bool/문자열·Unicode/배열 순서/profile/port/noise/timing/기타 metadata를 정규화·정렬·부분 선택하지 않음 |
| 호출 순서 | exact plain-JSON bounded 사본 → 공개 metadata validation → 위 literal SHA 비교 → 같은 검증 사본을 기존 `create_conducted_example`에 전달 |
| 거절 | 구조/타입/예산 불량 또는 fingerprint 불일치는 모두 `rf_signal_scenario_unsupported_catalog`. helper/factory/Fleet 생성·가상 파견·출력 디렉터리 생성0 |

기준 SHA는 승인된 literal 상수로 제품 모듈에 고정하며 호출 때 바뀐 로컬 파일이나 caller 입력에서 기대 SHA를 얻지 않는다. 선택 profile만 맞거나 public validation만 통과한 catalog도 지원으로 인정하지 않는다. 역할 factory의 일반 지원 검증을 새로 복제하지 않는다. 새 catalog 지원은 별도 재검증 단위다.

metadata 검증 영수증(비공개 보존): noise/비선택 미지원 parameter/배열 순서/10.0→10/metadata 변경 5종이 공개 validation을 통과해도 모두 다른 SHA였다. 공백/key 순서 2종은 같은 SHA였다. 이 확인은 metadata validation 총18회(탐색9+기록9), factory/Fleet/RF/harness0이며 041 gate 구현 검사는 아직 아니다.

## API·선언·기존 goal4

소유 파일은 `labflow/virtual_fleet/rf_signal_scenario.py`, `tests/test_virtual_fleet_rf_signal_scenario.py`, `docs/fcc/virtual_fleet_rf_signal_scenario_usage.md`다.

- `describe_rf_signal_scenario(scenario_id) -> declared_setup`: 아래 source_signal6/sensor2/meter3/reference_plane/basis **exact5** 고정 합성 선언의 사본. oracle·seed·작성자 조건을 운영 정책에 전달하지 않는다.
- `run_rf_signal_scenario(catalog, request, output_dir, *, run_id, runtime_instance_id) -> execution_record`. request exact3=`schema_version(정수1), scenario_id(아래7 enum), seed(bool 제외 정수0..2147483647)`. ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`. output은 새 디렉터리만, ID pair는 새 runtime마다 별개다. 주입 runtime/factory/callback/동적 설정/보고서 claim 입력은 없다.
- `evaluate_rf_signal_scenario(request, declared_setup, report, output_dir) -> assessment`. 입력은 각각 exact3/5/15이며 최상위 assessment를 입력하지 않는다. 고정 경로의 실제 journal bytes/SHA를 확인하고 공개 `read_operator_journal`로 읽어 별도 literal oracle와 대조한다. caller가 제공한 read-summary dict의 integrity 문자열만 신뢰하지 않으며 연산 모델을 재호출해 정답을 만들지 않는다.
- 부모 정책에 전달하는 goal **exact4**: `kind='acquire_fresh_rf_sensor'`, `dut_id='dut'`, `sensor_id='sensor'`, `minimum_acquisition_tick=시나리오 setup 완료 tick+1`. wrapper 정책의 ID는 `rf_signal_scenario_v1`. 부모 completed 뒤 meter phase만 이어 가고 다른 stop은 보존한다.

`RfSignalScenarioError(ValueError)`의 code/str/단일 args는 아래 고정6 코드 중 하나다. describe의 잘못된 ID는 invalid_request, 별도 evaluator의 읽기 불능은 evidence_unavailable 예외로 정제한다. evaluator의 유효 증거/기대 불일치는 completed/fail, 잘못된 증거는 failed/null assessment로 구분하고, run은 해당 고정 실패를 실행 기록으로 포장한다.

각 숫자의 아래 표기 타입까지 고정한다. source_signal exact6=`frequency_hz/power_dbm/bandwidth_hz/duty_cycle/crest_factor_db/modulation`, sensor exact2=`calibration_valid/acquisition_policy`, meter exact3=`frequency_hz/measurement_mode/unit`다. sensor에는 frequency configure를 보내지 않는다.

| scenario_id | signal `(Hz,dBm,Hz,ratio,dB,text)` | sensor `(calibration,policy)` | meter `(Hz,mode,unit)` | private oracle `(sensor dBm,meter dBm)` |
| --- | --- | --- | --- | --- |
| pulsed_on_mean | `(2450000000.0,12.5,20000000.0,0.25,3.0,'OFDM')` | `(true,'triggered')` | `(2450000000.0,'on_average','dBm')` | `(-18.0,-18.0)` |
| pulsed_time_mean | 첫 OFDM 행과 같음 | `(true,'triggered')` | `(2450000000.0,'time_average','dBm')` | `(-18.0,-24.020599913279625)` |
| pulsed_peak | 첫 OFDM 행과 같음 | `(true,'triggered')` | `(2450000000.0,'peak','dBm')` | `(-18.0,-15.0)` |
| cw_peak | `(2450000000.0,12.5,20000000.0,1.0,0.0,'CW')` | `(true,'triggered')` | `(2450000000.0,'peak','dBm')` | `(-18.0,-18.0)` |
| shifted_frequency | `(2460000000.0,12.5,20000000.0,0.25,3.0,'OFDM')` | `(true,'triggered')` | `(2460000000.0,'on_average','dBm')` | `(-18.0,-18.0)` |
| sensor_uncalibrated | pulsed_on_mean과 같음 | `(false,'triggered')` | pulsed_on_mean과 같음 | `(null,null)`; 관측 `calibration_unavailable`, 부모 blocked/`sensor_not_ready` |
| meter_frequency_conflict | pulsed_on_mean과 같음 | `(true,'triggered')` | `(2460000000.0,'on_average','dBm')` | `(-18.0,null)`; meter invalid/`sensor_frequency_setting_conflict` 뒤 blocked |

표의 “같음”은 선언값을 명시 복사한다는 뜻이며 상속·누락 기본값을 만들지 않는다. reference_plane은 모두 `sensor_input`, basis=`declared_synthetic_policy`다. source_signal.power_dbm은 DUT output 설정이고 sensor/meter 목표 값과 구분한다. 기존 path의 attenuation10.0/switch0.5/coupling20.0 및 bootstrap 5V/1A/50ohm/23C/45%/rf_1을 그대로 사용한다. coupler through loss1.25를 coupled sensor 경로에 다시 차감하지 않는다.

oracle와 허용차는 기존 공개 합성 모델의 ON/time-average/peak 정책에 대한 고정 합성 기대이다. 새 수식이 아니고 현재 7종 수치 실행은 미실행이다. 숫자 대조는 **절대오차 ≤1e-9 dB**, 주파수·duty·crest·unit·quantity·ID·tick/revision·enum은 tolerance 없이 정확 대조한다. 1 Hz는 기존 meter의 주파수 충돌 기준이며 새 비교 허용차로 재사용하지 않는다.

## 정확 반환과 nested 키

모든 소유 DTO는 plain JSON detached 사본이고 아래 키 외에는 거절한다. parent report의 내부 assessment를 덮어쓰지 않고 최상위 assessment로 별도 평가한다.

| 객체 | 정확 키와 제약 |
| --- | --- |
| execution_record exact10 | `schema_version,kind,scenario_id,status,declared_setup,report,assessment,artifacts,error_code,verification`; schema1/kind=`virtual_rf_signal_scenario`; status=`executed/rejected/failed` |
| declared_setup exact5 또는 null | `source_signal,sensor,meter,reference_plane,basis`; 하위6/2/3키와 literal은 위 표. runtime origin/해시는 journal·private provenance에 별도 보존 |
| report exact15 또는 null | 기존 `schema_version,kind,run_id,runtime_instance_id,synthetic,hardware_verified,ai_model_called,policy,termination,task_outcome,cleanup,usage,evidence,unresolved_request_ids,assessment`; 원래 harness 계약 그대로 보존 |
| report.policy exact2 | `kind='fixture',id='rf_signal_scenario_v1'` |
| report.termination exact2 | `reason,policy_claim`; 기존 enum/불확실 종료 의미 보존 |
| report.cleanup exact2 | `status='not_assessed',evidence_refs=[]` |
| report.usage exact6 | `decisions,logical_requests,transport_retries,tick_delta,reserved_ticks,elapsed_ms`; 유한 비음수, elapsed_ms 외 정수 |
| report.evidence exact2 | `measurement_refs`(event ID 배열), `operator_transcript_ref='artifact:operator_events'` |
| report.assessment / top assessment exact5 | `status,verdict,evaluator_id,evidence_refs,summary_code`; 내부는 기존 not_assessed/null/null/[]/null, 최상위는 아래 평가 enum |
| artifact 각 exact4 | `path,bytes,sha256,visibility`; executed는 journal 1개, 상대 path=`operator/events.jsonl`, visibility=`operator`; bytes는 bool 아닌 비음수 정수, SHA는 lowercase64 hex. public-result 자체 hash는 private manifest에만 저장 |
| verification exact10 | `data_origin='authored_synthetic',execution_mode='synthetic_virtual_execution',synthetic=true,hardware_verified=false,physical_verified=false,ai_model_called=false,normative_compliance_verified=false,method_approval='not_assessed',regulatory_scope_complete=false,waveform_implemented=false` |

executed는 report15·declared_setup5·status=completed인 최상위 assessment5·journal artifact1과 error_code=null을 요구하며, 정상/의도된 미완료 모두 포함한다. rejected는 runtime 전 거절이며 report/declared_setup=null, artifacts=[], 최상위 assessment=not_assessed다. failed는 완료된 검증 사본/부분 증거를 보존하되 숫자를 새로 만들지 않고 고정 오류를 반환한다. invalid request의 scenario_id는 null이며 유효한 enum 확인 후의 거절은 해당 ID를 보존한다. report의 kind=`virtual_fleet_harness_result`, schema1·synthetic=true·hardware_verified/ai_model_called=false·task_outcome=not_assessed를 유지한다.

최상위 assessment의 status=`completed/failed/not_assessed`, verdict=`pass/fail/null`이다. completed/failed의 evaluator_id는 `rf_signal_scenario_v1`, 미평가는 null이다. summary_code는 `observed_signal_satisfied/expected_sensor_blocked/expected_meter_frequency_conflict/scenario_expectation_mismatch/operator_evidence_invalid/null`만 허용한다. completed는 pass/fail, failed는 null+operator_evidence_invalid, 미평가는 verdict/summary_code=null 및 refs=[]다. negative pass는 의도한 미완료의 검증이며 측정 성공·FCC PASS가 아니다.

## 저장·phase·예산·오류

| 항목 | 고정 계약 |
| --- | --- |
| 실행 phase | 기존 example bootstrap23 receipt → `dut.stop,dut.configure(source_signal6),sensor.configure(sensor2),meter.configure(meter3)` setup4 receipt → 한 bounded harness의 부모 sensor acquire/read→meter acquire/advance(1)/fetch→최신 관측 → journal close/read → 별도 평가 |
| catalog 입력 예산 | canonical UTF-8 ≤1MiB/depth8/node8192(키 포함)/문자열1024자. root depth0. plain dict/list/str/bool/int/finite float/null만, subclass/순환/비 JSON/잘못된 Unicode 거절 |
| request 입력 예산 | canonical ≤1KiB/depth4/node32, seed 범위 위와 같음. 숫자 bool·타입 coercion·trim/casefold 없음 |
| harness 예산 exact5 | `decisions=64,logical_requests=64,ticks=32,wall_seconds=30,transport_retries=2`; 기존 bounded retry 정책만 사용하며 known invalid/blocked를 재시도하지 않음 |
| 기타 한도 | parent report256KiB, outer response320KiB/depth20/node16384; 기존 journal512KiB/line·32MiB/file·4096events·depth32; private author1MiB/manifest64KiB. 30초는 harness 구간의 cooperative deadline이며 bootstrap/setup/파일 I/O/평가 전체의 OS hard timeout이 아님 |
| preflight 순서 | request/ID/예산 → catalog 구조·fingerprint → output 미존재 확인/원자적 새 디렉터리 생성 → runtime 초기화. catalog 거절은 디렉터리·factory·파견0 |
| rejected error_code | `rf_signal_scenario_invalid_request`(schema/ID/seed/enum/요청 예산), `rf_signal_scenario_unsupported_catalog`(catalog 타입/예산/validation/SHA), `rf_signal_scenario_output_unavailable`(기존 경로·생성 실패) |
| failed error_code | `rf_signal_scenario_execution_incomplete`(초기화/실행 미완료), `rf_signal_scenario_evidence_invalid`(chain/구조/의미 모순), `rf_signal_scenario_evidence_unavailable`(증거 쓰기·close·read 실패) |

부모의 known blocked/invalid·bounded 종료는 report에 그대로 남기며 자동 재시도·0·completed로 바꾸지 않는다. 파견 뒤 불확실 종료는 unresolved IDs/예약 tick을 보존하고 추가 파견을 막는다. raw 예외·주소·경로·cause/traceback을 공개 오류로 복사하지 않는다.

`public-result.json`과 반환 execution_record의 exact10 동일성은 **complete manifest와 3개 파일 해시를 읽어 검증한 성공 반환에 한해서** 보장한다. executed outer를 저장한 뒤 manifest 기록/검증이 실패하면 saved executed를 보존하고 failed를 반환하며, 두 객체가 같다고 주장하지 않는다. artifacts에는 journal만 있어 자기참조가 없다. `private/author.json` exact8=`schema_version,kind,scenario_id,seed,phases,initial_context,provenance,oracle`; schema1/kind=`private_rf_signal_scenario_author`. phases exact2=`bootstrap,scenario_setup`에 genuine 부모 receipt 원본 배열을 보존하며 운영자 입력으로 넣지 않는다. setup 뒤 initial_context exact2=`tick,setup_revision`은 비음수 정수이며 미도달이면 null이다. helper가 중간 실패해 반환하지 못한 bootstrap receipt는 unknown(null)이며 생성됐다고 추정하지 않는다.

oracle exact6=`expected_outcome,expected_reason,sensor_dbm,meter_dbm,meter_quantity,tolerance_db`이고 위7행의 고정 기대만 사용한다. expected_outcome=`measured/sensor_blocked/meter_blocked`; 정상 expected_reason=null/meter_quantity=선택 mode, 미완료 reason은 위 관측 코드/meter_quantity=null이다. `private-manifest.json` exact8=`schema_version,kind,complete,request,catalog_sha256,topology_sha256,engine_sha256,files`; schema1/kind=`private_rf_signal_scenario_manifest`, files는 artifact와 같은 exact4이며 public-result/journal/author3개를 해시한다(자기 manifest 제외, author visibility=`evaluator_private`). SHA 필드는 모두 lowercase64 hex이며 아직 계산할 수 없는 실패 phase에서는 null을 보존한다.

성공 저장 순서는 journal close → private author 작성 → evaluator의 actual journal/author 읽기 → assessment와 journal artifact를 포함한 outer10 작성 → complete manifest 새 기록 → manifest와 지정 3파일을 실제 읽어 complete/키/행 집합/각 bytes·SHA·binding 검증 → 저장 outer10과 동일한 성공 반환이다. evaluator는 private oracle도 내장된 고정 표와 정확히 대조하며 그 파일 값을 임의 정답으로 신뢰하지 않는다. 이 순서로 평가 결과를 다시 입력하는 순환 의존과 파일 자기해시를 피한다.

실패 기록 `failure.json` exact6=`schema_version,kind,scenario_id,error_code,phase,dispatched`를 가능한 범위에서 남긴다. schema1/kind=`rf_signal_scenario_failure`, phase=`preflight/bootstrap/setup/harness/journal_close/journal_read/evaluation/artifact_write`, dispatched는 bool 또는 파견 여부 미확정인 null이다. 이미 생성된 실패·부분 파일을 덮어쓰거나 지우지 않는다.

## I2: 의미 평가와 저장 완료를 분리

evaluator의 completed/pass는 actual journal+author의 신호·fresh 취득·oracle 검토 결과다. 공개 outer나 manifest가 아직 없어도 이 평가 단계에는 도달할 수 있으므로 폴더 인수 완료를 뜻하지 않는다. 저장 완료는 후속의 별도 관측이다.

완료 gate는 실제 `private-manifest.json`의 exact8/`complete=true`, 정확히 한 번씩 있는 3개 relative path 행(`public-result.json`, `operator/events.jsonl`, `private/author.json`), 각 실제 파일의 bytes·SHA, request/catalog/topology/engine binding을 모두 검증해야 통과한다. manifest에는 자신·failure.json을 해시하지 않고 public outer artifacts에는 journal만 유지한다. `complete` 문자열이나 outer.status=executed 하나만으로 폴더를 인수하지 않는다. 저장 gate를 통과한 executed/assessment=completed-fail도 증거 게시 완료일 수 있으며 측정 성공과는 구분한다.

executed outer 저장 후 manifest 쓰기·읽기·검증이 실패하면 다음 원칙을 적용한다.

- saved outer와 journal·author·부분/완성 manifest를 바이트 그대로 보존한다. executed 파일을 failed로 다시 쓰거나 삭제하지 않는다.
- 기존 fixed6 중 I/O 불능은 `rf_signal_scenario_evidence_unavailable`, 구조/해시/binding 모순은 `rf_signal_scenario_evidence_invalid`로 정제한다. 실패 phase는 기존 `artifact_write`를 사용한다.
- 새 `failure.json`을 exclusive 생성하는 최선의 기록을 시도한다. 이미 있거나 쓰기 불능이면 추가 덮어쓰기·저장 재시도 없이 기존 실패를 반환한다. failure sidecar가 없다는 이유로 성공 처리하지 않는다.
- 반환 outer10은 `status=failed`, 해당 고정 error, 검증을 마친 report/declared_setup만 보존한다. 최상위 assessment는 `not_assessed/verdict=null/evaluator_id=null/evidence_refs=[]/summary_code=null`, artifacts=[]로 두어 저장 완료에 실패한 반환에 PASS를 싣지 않는다. saved executed 안의 이전 의미 평가를 사후 수정하지 않는다.
- 현재 시도의 폴더는 미완료/미확인으로 남기며 새 runtime·새 시나리오·재실행·manifest retry로 실패를 숨기지 않는다. 나중의 읽기 검토는 별도 관측이며 이전 failed 반환을 성공으로 바꾸거나 outer 동일성을 소급 주장하지 않는다.

| 수용 경로 | 저장된 public-result | 최종 반환 | 폴더 인수·보존 기대 |
| --- | --- | --- | --- |
| 정상 의미 평가→outer→manifest→3파일 검증 성공 | executed | 동일한 executed exact10 | 완료 gate 통과; measurement 성공/미완료 verdict는 별도 |
| preflight catalog/출력 경로 거절 | 없음/기존 파일 불변 | rejected, 기존 고정 코드 | 새 Fleet0, 기존 폴더 인수·수정 없음 |
| bootstrap/setup/harness 미완료 또는 불확실 | 미작성 또는 이미 생성한 부분 파일 | failed/execution_incomplete | known receipt·unresolved·부분 trace 보존, 미완료 |
| journal close/read·author 쓰기 실패 | executed outer 작성 전 | failed/evidence_unavailable | 의미 평가 PASS·폴더 완료 미주장, 원파일 보존 |
| 의미 증거의 chain/구조/신호 모순 | executed outer 작성 전 | failed/evidence_invalid | 기존 증거 보존, 미완료; 유효 증거의 기대 불일치 completed/fail과 구분 |
| public outer 쓰기 실패 | 없거나 부분 파일 | failed/evidence_unavailable | 부분 outer 보존, 완료 manifest 미주장 |
| **executed outer 쓰기 성공→manifest 쓰기 실패** | **saved executed 그대로** | **failed/evidence_unavailable** | **I2 필수 경로: absent/부분 manifest·원본3파일 보존, 미완료 폴더, 재실행·retry0** |
| manifest 쓰기 성공→읽기/파일 읽기 불능 | saved executed 그대로 | failed/evidence_unavailable | 저장 완료 관측 미완료, 원본·manifest 보존 |
| manifest/3파일의 키·complete·행 집합·bytes/SHA/binding 불일치 | saved executed 그대로 | failed/evidence_invalid | `complete=true`라도 gate 실패, 미완료 폴더 |
| 위 저장 실패 뒤 failure.json도 기록 불능 | saved executed/다른 기존 파일 그대로 | 최초 고정 실패 반환 유지 | sidecar 부재는 성공이 아님; 추가 파견·재시도·덮어쓰기0 |

이 표는 **미실행 수용 계획**이다. 특히 굵은 최소 경로는 manifest 쓰기만 실패시키는 미래 검사에서 saved executed/failed return/원파일 bytes 불변/폴더 미완료/새 실행·retry0을 각각 관측해야 한다. v3 문서 작성에서 이 경로를 실제 실행하거나 통과했다고 세지 않는다.

journal header와 private author의 provenance는 기존 exact4 `runtime_origin,catalog_sha256,topology_sha256,engine_sha256`를 사용한다. runtime_origin=`preinitialized`/resumable=false를 유지한다. catalog SHA는 위 validated canonical, topology는 canonical JSON, engine은 frozen base의 Fleet Python 파일을 filename+NUL+Git-LF bytes+NUL로 정렬해 해시한다. 이는 빌드 코드 관측 digest이고 서명/실물 attestation이 아니다. journal header/event/read DTO·receipt/snapshot은 기존 부모 계약으로 저장·검증하며 임의 소유 DTO 키를 끼우지 않는다.

별도 meter evaluator는 actual journal chain/complete/no unresolved, request와 private seed/선언 binding, report/header run·instance, catalog/topology/engine provenance, unique intent/receipt와 operation/device/profile/role/tick/revision을 대조한다. 마지막 fetch 뒤 최신 DUT/coupled RF의 signal6, 센서의 value/power/unit/frequency/duty/crest/acquisition/source, meter native quantity와 source_id=meter/input_source_id=sensor를 확인한다. 센서 packet에 없는 quantity/bandwidth/modulation을 만들지 않는다. wrapper는 child completed를 그대로 반환하지 않으며 fresh meter acquire/fetch까지 같은 harness 안에서 이어 가고, 종료 뒤 외부 execute로 보완하지 않는다.

## 수용 분모와 남은 경계

주 수용은 고유7종×1실행/7평가행(정상5·의도된 미완료2)이다. 기존 v1의 offline 변조8군은 hash-chain을 유효하게 재계산한 의미 변조도 거절해야 하며 chain 파손만 검사한 것을 semantic 검증으로 세지 않는다. 별도로 catalog gate와 위 저장 실패 수용 경로를 검사한다. I2 최소 경로는 주7종·의미 변조8군과 별도 분모로 기록하고, 같은 시나리오 재실행을 실패 시도의 성공으로 대체하지 않는다. catalog의 noise/timing/profile/port/metadata/native 숫자 타입/배열 차이 거절 및 key·공백 동치 허용은 helper/factory0을 관측한다. 반복성·회귀·독립 리뷰 분모는 별도 기록한다. 현재는 모두 제품 미구현/가상 미실행이며 metadata 검증18회를 여기에 합산하지 않는다.

source는 기존 DUT RF frame이며 density/waveform/관측 spectrum을 새로 만들지 않는다. 실제 031/036 peak 한 셀·026 준비 결과를 설정/oracle/지원 승인으로 사용하지 않는다. report_derived·합성 실행·실측을 구별하며 현재물리/기관/방법 승인·실제 RF 정확도는 확인하지 않았다. 추가 사용자 준비사항은 없다. 아래 계획과 총괄이 전달하는 정확 게시 base에서 개발3이 구현한다.

전사 오류를 줄이기 위한 동결 후보 데이터(비공개 보존)도 별도로 보존한다. 이는 선언·키·한도·enum의 비공개 제안 JSON이며 제품 모듈이나 실행 결과가 아니다.


## 총괄의 base·소유권·digest 고정

실제 구현 branch는 총괄이 이 spec/plan을 게시한 정확 SHA에서 `codex/dev3-rf-signal041-20261024`로 만든다. 기존036/031·증거·미커밋은 보존하고 새3파일만 커밋한다. Store/schema·기존 Fleet·RF 수식·센서 정책·journal/harness·frontend/HTTP·다른 owner를 수정하지 않는다. 현 API로 맞지 않는 구체 공백은 총괄에게 근거와 최소 수정안을 반환하며 성공을 위조하지 않는다.

engine digest의 입력 집합은 위019 게시에 존재하는 `labflow/virtual_fleet/*.py` **19파일**로 고정한다. basename의 UTF-8 사전순으로 각 `basename + NUL + Git-LF bytes + NUL`을 연결해 SHA-256을 구한다. root의 고정 계산값은 `9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42`다. 새041 모듈을 이 부모 digest에 넣지 않으며 private 인수에서 새3파일 GitLF 핀을 별도로 기록한다. 이는 부모 코드 관측 digest이고 전체 앱/041 코드 attestation이 아니다. manifest/journal의 같은 field에는 이 범위의 같은 digest를 쓴다. 파일별19pin은 비공개 총괄 영수증에 보존한다.

사용자 승인·추가 원시자료를 기다리는 단계가 아니다. 개발3은 위 계약의 RED→최소 구현→관련 회귀·합성7/별도평가7·변조8군·저장10경로→소유 commit/push→독립 리뷰/수정→총괄 통합을 이어간다. 기존 보유 actual031/036의 값이나 원문을 새 합성 입력·oracle로 가져오지 않는다. 실제모델·학습·하드웨어·현장망·출력/이동·외부 제출은 이번 범위가 아니다.
