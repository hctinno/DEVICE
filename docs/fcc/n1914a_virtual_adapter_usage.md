# N1914A 합성 어댑터 사용법

2026-10-24 · Asia/Seoul. METER-ADAPTER-006의 v1 계약이다. [고정 설계](../superpowers/specs/2026-10-24-n1914a-virtual-adapter-design.md)와 [실행 계획](../superpowers/plans/2026-10-24-n1914a-virtual-adapter.md)을 따른다. 기존 [VirtualLab](virtual_lab_usage.md)의 `n1914a-a-ascii-v1`을 순서대로 호출하며, 기존 엔진·주파수 source를 변경하지 않는다.

```python
from labflow.virtual_lab import VirtualLab
from labflow.n1914a_virtual_adapter import (
    N1914AVirtualAdapter, describe_virtual_n1914a_contract,
)

contract = describe_virtual_n1914a_contract(model='N1914A')  # I/O 없음
lab = VirtualLab(measurement_ticks=2)
# 아래 준비는 합성 시나리오 작성자의 작업이다.
lab.configure_dut('g', 6, 10)
lab.set_path(True, 3)
lab.start_tx()
adapter = N1914AVirtualAdapter(lab, model='N1914A')
receipt = adapter.measure('example.DBM', unit='DBM', timeout_ticks=20)
assert receipt['status'] == 'completed'
assert receipt['measurement']['value'] == 7.0
# 같은 ID/설정은 callback과 lab을 다시 실행하지 않고 같은 receipt를 반환한다.
assert adapter.measure('example.DBM') == receipt
watts = adapter.measure('example.W', unit='W')
```

`type(lab) is VirtualLab`만 받는다. `VirtualSession`, 하위 클래스, callable, 주소, 일반 transport는 받지 않는다. `model`은 정확한 문자열 `N1914A`만 허용한다. N1911A·P-Series·다른 철자 alias를 연결하지 않는다. 생성자와 descriptor는 lab을 호출하지 않는다. Python host와 `can_continue`는 신뢰되는 실행 주체이며, 임의 Python 코드에 대한 sandbox를 제공하는 계약이 아니다.

`request_id`는 `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`, `unit`은 정확히 `DBM` 또는 `W`, `timeout_ticks`는 bool을 제외한 int 1..1000이다. 기본값은 DBM/20이다. `can_continue`는 None 또는 인수 없는 callable이며 반환값이 **`True`인 경우만** 진행한다. 그 밖의 반환값이나 `Exception`은 `continuation_denied` 취소다. callback은 각 lab 호출 직전과 최종 결과 게시 직전에 검사하며, 한 번 거절되면 일반 명령을 더 실행하지 않는다. cleanup에는 다시 묻지 않는다. 합성 tick 대기만 제한하며 신뢰된 callback의 벽시계 실행 시간을 제한하지 않는다.

인스턴스마다 최대 128개의 불변 canonical receipt bytes를 보존한다. 같은 ID의 `(unit, timeout_ticks)`가 같으면 독립 사본을 재생한다. callback은 캐시 키에 포함하지 않는다. 실패·취소·timeout도 보존하므로 단절 복구 후 재취득하려면 새 ID가 필요하다. 다른 설정의 같은 ID는 충돌이며, 128개 이후 새 ID는 거절하고 기존 기록을 제거하지 않는다. 실행 중인 인스턴스의 모든 중첩·동시 요청은 `adapter_busy`다. ID/설정/인수 형식 검사는 cache 조회 전에 수행한다. 영속 저장·프로세스 재시작 후 중복 방지·자동 재개는 제공하지 않는다.

호출자는 measure 동안 같은 lab을 다른 실행 주체와 동시에 조작하지 않아야 한다. 잠금은 adapter 인스턴스별이며 다른 adapter·직접 lab 호출까지 잠그지 않는다.

## 고정 명령 순서와 유효성

1. `*IDN?`가 기존 합성 식별 `DGM Virtual,N1914A,SIM-001,SIM-1`인지 확인하고 `SYST:ERR?`를 한 번 소비한다.
2. `INIT1:CONT OFF`, `FORM:DATA ASCII`, `TRIG1:SOUR IMM`, `UNIT1:POW DBM|W`를 순서대로 보내며 각 명령 뒤 `SYST:ERR?`를 소비한다. `UNIT1:POW?`로 단위를 확인한다.
3. `INIT1` 뒤 오류를 확인하고 `*OPC?`를 조회한다. 앱 envelope의 `pending`이면 `advance(1)` 후 다시 조회한다. 최대 timeout_ticks번만 전진하며 마지막 허용 tick에서 완료된 결과는 허용한다. pending에 wire `'1'`이 붙은 응답은 형식 오류다.
4. 완료 뒤 `FETC1?`의 공개 metadata와 wire를 각각 확인한다. 마지막 `SYST:ERR?`와 continuation 게시 검사를 통과한 경우에만 `measurement`를 반환한다.

`*OPC?`의 완료만으로 유효 데이터를 확정하지 않는다. measurement ID는 양의 int이고 이 adapter가 이전에 유효하게 확인한 ID보다 커야 한다. setup revision은 0 이상의 int이며 이전 유효 관측보다 뒤로 갈 수 없다. 준비하지 않은 새 lab의 revision0·합성 floor도 유효 합성 관측일 수 있다. 완료 tick은 INIT 때보다 크고 OPC 완료 관측·fetch 관측의 tick과 같아야 한다. meter 호출은 tick을 바꾸지 않으며, 성공한 advance 응답만 정확히 1 증가를 허용한다.

현재 setup revision을 별도 조회하거나 `_revision`, `_sequence`, `_faults`, seed, 정답을 읽지 않는다. 기존 lab의 `invalid/configuration_changed`를 거절하고 공개 metadata의 형식·관측 일관성만 확인한다. 현재 setup의 완전한 일치나 새 실제 RF 취득을 확정하지 않으므로 `current_setup_match=not_assessed`다.

measurement unit과 요청 unit이 같고 value가 bool이 아닌 유한 int/float여야 하며 W는 양수여야 한다. wire가 정확히 기존 `f'{value:+.9E}'` 결과인지 검사한다. metadata 원래 값을 유지하며 9자리 과학표기의 표시 반올림을 규격 pass margin으로 사용하지 않는다. 무결과·invalid·unsupported·단절·오류·잘못된 수치를 0이나 completed로 바꾸지 않는다.

첫 실패에서 중단한다. INIT 호출 직전부터 명령이 실행됐을 가능성을 보존한다. 공개 `pending`/`busy`도 취득 가능성으로 취급한다. 이후 실패·취소·timeout이면 허용된 `ABOR1`을 정확히 한 번 시도한다. callback이 거절해도 이 정리는 시도하며 정리 실패는 원래 실패와 별도로 기록한다. ABOR 응답 이후 오류 큐를 추가 소비하거나 재시도하지 않는다. `cleanup.status=completed`는 합성 ABOR ack와 tick 일관성을 확인했다는 뜻이다.

어댑터는 DUT TX·RF 출력·경로를 제어하지 않는다. `ABOR1`은 미터 취득 정리이며 RF 정지나 bench 안전의 증거가 아니다. `*CLS`, `*RST`, READ, MEASure, CAL:ALL?, 다른 채널/창, binary 형식은 명령 subset에 없다.

## 공개 receipt와 transcript

measure 반환은 다음 **26개 top-level key**로 고정한다. descriptor는 별도의 순수 계약 설명이며 command 목록·제한·근거를 독립 사본으로 반환한다.

| key | v1 의미 |
|---|---|
| `schema_version`, `request_id`, `model`, `profile_id`, `backend` | 1, 요청 ID, N1914A, n1914a-a-ascii-v1, existing_virtual_lab |
| `synthetic`, `hardware_verified`, `vendor_binary_executed` | true, false, false |
| `sensor_compatibility`, `calibration`, `firmware`, `options`, `real_support`, `current_setup_match` | 모두 not_assessed |
| `resumable`, `rf_control_performed`, `rf_safe_verified` | 모두 false |
| `request` | 정확히 `{unit, timeout_ticks}` |
| `status`, `code` | completed/failed/cancelled/timeout와 null 또는 아래 고정 코드 |
| `measurement` | completed에서만 `{measurement_id, setup_revision, completed_tick, value, unit, synthetic}`. 그 밖에는 null |
| `ticks` | `{start, end, advance_attempts}`. start/end는 검증된 공개 tick이며 관측 전에는 null. advance_attempts는 호출 시도 수 |
| `transcript`, `transcript_sha256` | 순서 기록과 그 canonical SHA-256 |
| `error_queue` | `{consuming: true, attempts}`. attempts는 SYST:ERR? 호출 시도 수이며 빈 큐/실패도 포함 |
| `cleanup` | `{status: not_needed/completed/failed, code: null 또는 고정 실패 코드}` |

transcript 행은 정확히 `{sequence, operation, command, ticks, reply, code}`다. sequence는 1부터 연속, operation은 meter/advance, command는 meter 명령 또는 null, ticks는 advance의 1 또는 null이다. reply는 원래 인식 가능한 공개 reply의 독립 사본이다. `code`는 해당 행의 거절 이유 또는 null이며, 명령 사이 continuation 취소는 새 가짜 명령 행을 만들지 않는다.

공개 reply는 기존 base7키와 해당 응답 종류에 맞는 reason/error_number/error_message/measurement만 허용한다. 현재 엔진의 오류 0/-211/-213/-350, 고정 reason, DGM Virtual SIM 식별 문법, DBM/W, 수치 wire 문법을 사용한다. reply당 canonical 16KiB 이내, wire는 ASCII128 이내이며 JSON 비유한 수치·알 수 없는 키/중첩 자료·비공개 텍스트·새 프로필은 거절한다. 이런 reply와 emulator 예외는 `reply=null` 및 고정 코드로 시도만 남긴다. 이전에 검증된 prefix를 보존하며 원시 예외나 숨은 상태를 추가하지 않는다. 인식된 공개 reply의 잘못된 단위·숫자·상태는 원래 reply를 보존하고 실패한다. 성공 receipt의 measurement와 transcript의 measurement도 서로 독립 사본이다.

canonical digest는 **transcript list만** `json.dumps(transcript, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')`로 직렬화한 SHA-256 lowercase hex다. ABOR·advance·실패 행도 포함하고 top-level receipt, 벽시계, 자기 digest는 포함하지 않는다. 전송·응답 무결성 비교용이며 서명이나 장비 정확도 증거가 아니다.

advance가 실제 실행된 뒤 응답을 잃으면 시도 수만 증가하며 확인하지 못한 tick을 추정하지 않는다. 뒤의 ABOR reply가 마지막 검증 tick과 다르면 cleanup은 tick_mismatch로 실패한다. 이때도 ABOR는 한 번만 시도하고 primary 예외 코드를 유지한다.

| 경계 | 고정 코드 |
|---|---|
| I/O 전 ValueError | unsupported_model, virtual_lab_required, invalid_request_id, unsupported_unit, invalid_timeout_ticks, invalid_continuation, adapter_busy, request_conflict, receipt_limit_reached |
| 취소/대기 | continuation_denied → cancelled; completion_timeout → timeout |
| 식별/구조/관측 | identity_mismatch, invalid_reply, tick_mismatch, unit_mismatch, invalid_measurement, wire_value_mismatch, measurement_id_not_fresh, setup_revision_reversed |
| 큐/실행 | error_queue_nonzero, emulator_exception |
| 기존 앱 상태 | meter_pending, meter_no_data, meter_invalid, meter_unsupported, meter_disconnected, meter_error, meter_busy |

completed의 code는 null이며 취소·timeout 외의 반환 실패는 failed다. I/O 전 ValueError는 receipt를 생성하지 않는다. 유효 요청 이후 첫 callback 취소·명령 오류부터는 receipt를 cache에 남긴다. cleanup에는 위 실패 코드가 독립적으로 들어가며 primary status/code를 덮어쓰지 않는다.

## 근거와 적용 한계

명령 의미의 고정 출처는 N1913/14A Programming Guide **N1913-90008.pdf Edition19(2025-06-11)**, SHA `ecaf6faf71890f01289261087c13cd32b5b661edbd69a303cd0f636691fb28c2`다. 기존 명령 맵의 PDF FETCH137–138·오류517·ABORT546·INIT548–550·TRIG561–562·UNIT583–584·common595/597/599–600/605를 참조한다. 합성 시간, wire 정밀도, stale 정책, DGM identity는 기존 lab의 선언 정책이다.

추가 CTRL001 모델별 근거 검토는 EPM N1914A와 P-Series N1911A를 분리한다. 창1..4와 물리 입력 A/B·USB 옵션 C/D는 다르며, 현재 합성 A/window1에서 다른 입력·옵션을 활성화하지 않는다. READ는 새 측정, FETCH는 기존 데이터의 계산/출력, MEASure는 복합 동작이므로 서로 대체하지 않는다. UNIT의 relative/ratio 문맥을 현재 절대 합성 스칼라에 섞지 않는다. 현재 엔진에 없는 relative/ratio 상태·명령을 새로 만들거나 실제 장비의 상태를 확정하지 않는다.

OPC 완료, CAL 통과, 새 데이터 유효성, 현행 추적 교정은 각각 다른 근거가 필요하다. `CAL:ALL?`는 절차를 시작하므로 현재 subset에 추가하지 않는다. N1921A의 P-Series host 관계와 EEPROM·영점/교정 조건은 N1914A 호환의 근거가 아니다. sensor compatibility/교정/FW/옵션은 미평가다.

정확한 IVI 배포판 Readme/EULA/LICENSE/NOTICE·package bytes/SHA·모델별 API·runtime 요구는 확보·실행하지 않았다. index의 무료/지원 표시나 소개 HTML은 이를 대신하지 않는다. 원문·패킷 payload는 공개 재배포 권리가 확정되지 않아 private으로 유지한다. 이 문서는 원문을 복제하지 않고 현재 구현 경계만 기록한다.

검증은 실제 **기존 VirtualLab 실행을 사용한 합성 검증**이다. 제조사 Mock/SDK/VISA/바이너리·실장비·현장·계측 정확도·기관 적합성 검증은 미실행이다. completed는 위 합성 계약을 통과했다는 뜻이며 시험소 전체 구현 완료를 뜻하지 않는다.
