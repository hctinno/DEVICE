# Conducted twin 순수 결과 초안

2026-10-26 Asia/Seoul. 공개 base c1a61e742969cd2bc2314fb1495d2202e55d3b65 위에 자기 setup 근거 후보6ca만 정상 cherry한 의존 소스를 사용한다. 6ca 독립 검토는 이 단위 시작 때 미완료였고 후행 qualified Yes를 인수했다. 원 독립 분모·불완전 관측 한계는 소유 증거에 보존하며 지정 base/cherry 원형은 유지한다. D2의 실제 source/setup/journal 접점 구현 완료를 가정하지 않는다. 이 모듈은 입력 snapshot만 계산하며 파일·Store·장비·모델 I/O를 하지 않는다.

## API와 경계

```python
from labflow.virtual_fleet.conducted_twin_result import build_conducted_twin_result

result = build_conducted_twin_result(
    plan_input, setup_snapshot, journal_read, run_report,
    measurement_ref=measurement_ref,
)
```

[수용 D1 plan](intake_conducted_twin_plan_usage.md), [같은 Trial의 실제 setup](conducted_setup_provenance_usage.md), 기존 read_operator_journal의 결과 exact8과 원 harness report exact15를 받는다. measurement_ref는 같은 journal의 observation event ID이며 원 report의 measurement_refs에도 있어야 한다. 원 파일 bytes를 다시 열지 않는다. journal의 기존 순수 header/event/hash-chain primitive로 제공 reader snapshot의 해시·순서·완료 상태를 재대조하고 기존 report wire validator를 사용한다.

native JSON 입력 합계 최대32MiB, 깊이32, nodes1,000,000, plan 최대8MiB, setup 최대32개, events 최대4096개, 출력 최대1MiB다. bool을 숫자로 취급하지 않는다. 비 native·순환·nonfinite·용량 초과는 정제 실패 코드이며 원 객체/exception을 문자열로 유출하지 않는다. MemoryError/KeyboardInterrupt 등 제어 예외는 전파한다. 같은 입력의 반환은 deterministic detached JSON이다. 저장·실행 권한은 만들지 않는다.

## 동일 실행의 host 접점

D2 host는 실제 Trial에서 setup_snapshot을 얻은 뒤 같은 journal header.provenance에 다음을 명시한다. 이것은 policy/goal에 private 정답을 넣는 접점이 아니다.

- plan_binding: D1 binding6 원형(intake_id/revision/analysis_context_id/context_sha256/analysis_sha256/plan_sha256)
- setup_sha256: SHA256(canonical(actual setup_snapshot))
- topology와 topology_sha256: 그 runtime의 실제 연결 선언 및 canonical SHA
- quantity: 아래 exact4 또는 미제공

quantity는 metric="on", reference_plane="sensor_input", loss_compensation_applied=false, loss_compensation_sign=1의 명시 합성 근거다. 누락·다른 quantity/plane/sign·bool 숫자·이미 보정됐다는 선언이면 역보상값은 null과 이유를 남긴다. already_applied=true를 다시 더하지 않는다. plan의 time/peak나 report_peak를 on으로 변환하지 않는다. raw dBm→W 단위 변환과 source_output 기준면 역보상은 별도다. calibration_valid와 이 host 선언은 교정·물리 진위·규범 승인이 아니다.

plan SHA와 source6, 실제 마지막 DUT configure·선택 관측의 source metadata, setup hash, journal/report의 run/runtime, topology hash, event 순서·취득 receipt·tick/revision·첫 관측 이후 freshness를 대조한다. report PASS/seed/expected/고정P−30.5로 값을 만들지 않는다. 복구 뒤 새 acquisition이 없거나 raw/node/path가 invalid면 계산으로 성공 처리하지 않는다. 선택 관측 이전에 경로 관련 configure/select_path가 새로 실행되면 이 첫 단위는 재구성하지 않고 post_setup_configuration 이유로 보류한다. 선택 관측 뒤의 stop은 그 당시 유효한 역사적 raw를 소급 변경하지 않는다.

경로는 실제 topology의 DUT→센서 RF 연결과 실제 configure/select_path에서 추적한다. 이 단위는 기존 attenuator/rf_switch/coupler의 명시 loss 설정만 지원하며, coupler의 coupled와 through를 구별한다. 다른 경로·모호한 연결·설정 누락은 null/이유다. 기존 RF loss 선택 함수와 calculate("rf_power", ...)를 사용한다. 원 packet에 이미 반영된 전파 -loss와 source_output 환산 +loss는 별개 ledger 의미다. 필요한 명시 근거가 모두 맞을 때만 한 번 합산하며 인접 power 차이에서 loss를 추정하지 않는다.

## 반환 exact10

| 키 | 의미 |
| --- | --- |
| schema_version | 1 |
| kind | conducted_twin_result |
| status | recorded / incomplete / invalid; 적합 판정이 아님 |
| binding | D1 원 plan_input·원 report 및 canonical 해시, setup/journal/topology 해시, run/runtime·선택 event |
| raw_measurement | 원 packet·event ID/seq·device/tick/revision·선언 quantity/기준면; 없으면 null |
| setup_provenance | 원 setup list·topology·선택 경로의 configure 근거 |
| calculation | raw W, 별도 correction ledger·보정 dBm/W, target plane, 미평가 conformity |
| gaps | D1 원 gaps 순서·내용을 보존하고 이 단위의 부족 이유 추가 |
| failure | 정제 code/field 또는 null; 정보 부족·잘못된 결합·invalid를 구별 |
| verification | synthetic/미검증·caller snapshot/hash 신뢰 범위·실행권한false |

원 입력/부분 실패/원 report를 성공으로 덮어쓰지 않는다. 출력 한도를 넘으면 정제 output_limit 실패 DTO를 반환하며 부분 결과를 성공처럼 자르지 않는다. 공식판본·규범 한계·불확도 승인이 없으므로 conformity.status="not_assessed", verdict/numeric_limit_dbm/uncertainty_db=null이다. 실제 실측 예측력·현장/교정·전체 업무 완료를 주장하지 않는다. P01 실제 packet·고객 원문을 열거나 모델에 보내지 않는다.

소유24/24와 별도 관련284/284가 failure/error/skip0으로 통과했다. 관련 분모는 D1 plan34·integration23·evaluation33·RF41·instruments42·core22·harness39·method_adapter25·journal25다. 소유 검사는 genuine D1·같은 Trial의 setup·genuine harness/journal/report 및 독립 Decimal 수치 대조를 사용한다. malformed 중첩·receipt identity/clock·D1 authority/basis·지수문자·source power 결합의 추가 RED를 보존했다. 독립 검토와 실제 D2 통합은 별도다. 원 RED와 제한을 보존한다. 실제 provider/모델 인증/실장비/고객원본 호출0, 기존 Codex16/Vertex6/3072 상태 변경0이다.

## 중첩 DTO와 실패 시 보존형

`number`는 bool을 제외한 native 유한 int/float, `JSON`은 native JSON 재귀 값이다. 아래의 “정상”은 해당 검증을 통과한 형상이다. 검증 전에 복사하는 원입력 필드는 `invalid`에서도 원 JSON을 보존할 수 있다. consumer는 status/failure/gaps를 먼저 읽고 이 필드를 성공 자료로 단정하지 않는다. nullable은 숫자0이 아니며, 단계별 미생성 키와 null도 구별한다.

| object | 실제 키·타입 | null·미생성·상태 |
| --- | --- | --- |
| binding | 초기 `{}` → `plan_input,run_report` exact2 → 아래 hash/ID9를 더한 exact11 | native snapshot 자체가 거절되면 빈 object. 첫2값은 원 `JSON`이며 정상은 D1 exact8/report exact15. 중간 실패에서 아직 생성하지 않은 hash/ID 키는 생략된다. |
| binding 추가9 | `plan_input_sha256,setup_sha256,journal_file_sha256,journal_head_sha256,report_sha256,topology_sha256`: SHA256 string; `run_id,runtime_instance_id,measurement_ref`: opaque string | 9키는 run·plan·setup·topology 결합 검사를 지난 뒤 함께 생성한다. plan/report hash는 canonical JSON, journal file/head는 검증한 원 canonical journal의 해시다. |
| raw_measurement | `packet,event_id,sequence,device_id,tick,setup_revision,quantity,reference_plane` exact8 | 전체가 null일 수 있다. `packet`은 원 object; device_id는 항상 `sensor`. 다른 원 metadata는 `JSON`이며 정상은 ID string·sequence/tick/revision int다. 잘못된 값도 실패 원형으로 남을 수 있다. |
| raw packet 정상 필수11 | `status="ok",valid=true,value:number,unit="dBm",frequency_hz:number,power_dbm:number,duty_cycle:number,crest_factor_db:number,acquisition_tick:int,acquisition_setup_revision:int,source_id="sensor"` | packet은 open object다. 추가 원키를 버리지 않는다. 정상 value=power_dbm이며 raw packet을 예상값으로 대체하지 않는다. invalid packet도 원형으로 남으므로 normal 타입을 강제 캐스팅하지 않는다. |
| raw quantity | 정상 exact4 `metric="on",reference_plane="sensor_input",loss_compensation_applied=false,loss_compensation_sign=1` | 미제공이면 null. 잘못된 선언은 원 `JSON`으로 보존한다. raw reference_plane은 이 선언의 원 값 또는 null이며 승인된 target plane을 뜻하지 않는다. |
| setup_provenance | `records,topology,path` exact3 | records는 제공 원 `JSON`(정상 Record[]≤32); topology는 null 또는 제공 원 `JSON`(정상 object); path는 선택 경로 Edge[]이며 아직 생성되지 않았으면 `[]`. |
| Record 정상8 | `request_id:string,operation:"execute"\|"advance",device_id:string\|null,action:string\|null,parameters:object\|null,receipt:object\|null,tick:int\|null,setup_revision:int\|null` | 실제 setup usage의 원 record다. advance 인자는 `{"ticks":int}`. 예외 시 null receipt/시점을 0이나 성공으로 바꾸지 않는다. 잘못된 records/row도 제공 원형으로 남을 수 있다. |
| topology 정상 | `devices,connections`; Node는 `id,profile_id` string; Edge는 `source,target,kind`, endpoint는 `device_id,port` string | 실제 원 topology를 보존한다. 선택 path의 kind는 `rf`이며 Edge/Node의 미사용 원키도 임의 삭제하지 않는다. path는 DUT부터 sensor까지 순서다. |
| calculation | `raw_power_w,raw_reference_plane,correction_ledger,target_reference_plane,corrected,conformity` exact6 | 모든 status에서 존재한다. raw_reference_plane은 원 선언 `JSON` 또는 null, target_reference_plane은 유효 plan의 `source_output` 또는 null. |
| raw_power_w | null 또는 `{value:number>0,unit:"W"}` exact2 | 원 dBm의 단위 변환이다. correction 근거가 없어도 존재할 수 있다. 실패가 이미 계산한 원 단위 변환을 지우지는 않는다. |
| correction_ledger | Ledger[] | 기본 `[]`. 전체 보정 근거·계산을 통과한 뒤에만 한 번 게시한다. 규범/교정 ledger가 아니다. |
| Ledger | `device_id,output_port,setting,loss_db,record_index,request_id,tick,setup_revision,propagation_db,already_applied,compensation_db` exact11 | 첫3·request_id는 string, loss/propagation/compensation은 number(dB), index/tick/revision은 int, already_applied는 false. record_index는 records의 0기준 위치. setting은 `attenuation_db,loss_db,coupling_db,through_loss_db` 중 실제 사용한 키다. propagation_db=−loss, compensation_db=+loss의 의미를 구별한다. |
| corrected | null 또는 `{value:number,unit:"dBm",power_w:number>0}` exact3 | target source_output 합성 계산이다. missing·already applied·wrong basis는 null이며 raw 숫자로 채우지 않는다. |
| conformity | `status:"not_assessed",verdict:null,numeric_limit_dbm:null,uncertainty_db:null` exact4 | 모든 status에서 고정. storage/record 완료와 적합 PASS를 구별한다. |
| gaps | 원 D1 gaps 순서 + 새 Gap[] | 정상 Gap은 `code:string,field:string,provided:JSON,blocking:bool` exact4. 새 행은 provided=null/blocking=true다. 제공 D1 gaps가 list이면 검증 전에 원소를 보존하므로 malformed 원소도 `JSON`일 수 있다. 원 D1 literal enum은 D1 usage를 따른다. |
| failure | null 또는 `{code:string,field:string}` exact2 | 원 exception/body를 담지 않는다. 정보 부족은 failure=null인 gap-only와 failure가 있는 중단을 구별한다. |
| verification | `synthetic:true,hardware_verified:false,physical_verified:false,source_bytes:"not_reopened",method_approval:"not_assessed",trust_scope:"provided_host_snapshots_and_hash_consistency",execution_authority:false` exact7 | 모든 DTO에서 같은 고정값. 실패 입력에 실측/권한 주장이 있어도 이를 승인하지 않는다. |

`recorded`는 명시한 합성 target 계산까지 끝났다는 뜻이며 failure=null이다. nonblocking D1 gaps는 남을 수 있다. `incomplete`는 근거 부족·미완료/부분 setup·방법 불일치이며, `invalid`는 구조/결합/유효성/한계 거절이다. 두 상태 모두 이미 추출한 raw/report/원입력을 보존할 수 있으므로 “실패이면 모든 값 null”이라고 가정하지 않는다. output_limit은 원형을 성공처럼 자르지 않고 빈 기본 형상의 정제 invalid DTO로 대체한다.

## 이 builder가 추가하는 오류 literal 전체

아래62개는 원 D1 gaps의 enum과 별개다. `failure.field` 및 새 gap.field는 `input,output,plan_input`과 그 `binding,gaps,status,verification,intake,plan,plan.basis_refs`, `journal_read`와 그 `events,header,integrity`, `setup_snapshot`/`setup_snapshot.<0기준 index>`, `topology,run_report,measurement_ref,calculation,observation.<device_id>`를 사용한다. gap-only에서는 `quantity`/`quantity.metric`도 사용한다. 부모 validator·RF/계산 함수의 거절 중 별도 literal로 처리하지 않은 예외는 `invalid_evidence`로 정제하며 원 예외 text를 반환하지 않는다.

| status/failure | literal code 전체 |
| --- | --- |
| invalid / failure exact2 | `acquisition_invalid`, `evidence_context_missing`, `input_limit`, `invalid_evidence`, `journal_header_invalid`, `journal_integrity_invalid`, `journal_invalid`, `journal_limit`, `journal_state_invalid`, `measurement_invalid`, `measurement_path_conflict`, `measurement_stale`, `native_input_invalid`, `observation_clock_regression`, `observation_invalid`, `output_limit`, `plan_basis_invalid`, `plan_binding_invalid`, `plan_binding_mismatch`, `plan_hash_mismatch`, `plan_intake_invalid`, `plan_invalid`, `plan_limit`, `plan_method_invalid`, `plan_verification_invalid`, `receipt_advance_clock`, `receipt_identity_or_clock`, `receipt_invalid`, `report_invalid`, `run_binding_mismatch`, `setup_advance_invalid`, `setup_clock_mismatch`, `setup_duplicate_request`, `setup_hash_mismatch`, `setup_identity_invalid`, `setup_invalid`, `setup_limit`, `setup_receipt_invalid`, `source_metadata_mismatch`, `source_settings_mismatch`, `topology_hash_mismatch`, `topology_invalid` |
| incomplete / failure exact2 | `correction_overflow`, `execution_incomplete`, `journal_incomplete`, `measurement_missing`, `measurement_not_referenced`, `measurement_reference_missing`, `path_ambiguous`, `path_configuration_invalid`, `path_configuration_missing`, `path_selection_missing`, `plan_blocked`, `post_setup_configuration`, `setup_failed`, `setup_missing`, `setup_partial`, `unit_conversion_failed`, `unsupported_path_device` |
| incomplete / failure=null, gap-only | `correction_basis_invalid`, `correction_basis_missing`, `metric_mismatch` |

제어 예외 MemoryError/KeyboardInterrupt 등은 DTO로 바꾸지 않고 전파한다. 오류/정보 부족에서 원 값·실패 prefix·이력을 삭제하거나 도메인·규범 승인으로 승격하지 않는다. 이 절은 e8e의 실제 source를 정적으로 대조한 문서 계약이며 알고리즘·테스트 변경이나 제품 검사 재실행이 아니다.
