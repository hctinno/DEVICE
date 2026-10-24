# 기존 가상 DUT의 단일 정지 경계

2026-10-24 · Asia/Seoul. DUT-STOP-013의 [구현](../../labflow/dut_stop_simulation.py)과 [전용 검사](../../tests/test_dut_stop_simulation.py)다. 기존 정확한 VirtualFleet와 내장 RFDevice DUT의 stop/read를 재사용한다. 새 DUT/RF 상태 엔진이나 SDK·실물 transport는 없다.

## 고정 API

```python
SyntheticDutStopAdapter(fleet, dut_id, *, transport_family,
                        available, authorized, model_fw_matches,
                        scenario='normal')
adapter.stop(request_id) -> dict
adapter.author_record(request_id) -> dict  # trusted author의 비공개 진단용
```

운영자에게는 bound `stop` 호출과 반환 DTO만 제공한다. 생성 설정과 author_record는 신뢰된 host/시나리오 작성자가 보관한다. 가용성·권한·모델/FW 대응은 정확한 bool로 명시하며 실제 장비 상태를 자동 탐색하거나 제조사 지원을 확인한 것으로 표시하지 않는다. 생성 뒤 설정을 바꾸는 API는 없다.

transport_family는 정확히 `ADB`, `OEM`, `GUI`, `AT`, `DIAG` 중 하나다. 합성 전송 경계의 분류이며 catalog ID·설치 backend·모델/FW 지원 선언이 아니다. DIAG를 AT·USB/HID로 취급하지 않는다. 다른 family, firmware/bootloader/iOS, 임의 transport/명령/주소는 받지 않는다. 선택한 family의 gate가 실패해도 다른 family를 선택하거나 stop을 재송신하지 않는다.

fleet는 subclass/duck가 아닌 정확한 VirtualFleet이고 내장 RF·계측·시설 device로 구성돼야 한다. 대상은 기존 내장 RFDevice의 DUT다. execute/observations뿐 아니라 _request/_envelope 등 하위 경로와 device의 상속 helper/property까지 instance/class 교체를 검사하고 callback 실행 전에 거절한다. 이 검사는 신뢰된 host가 불러온 내장 Python 구현의 명시 callpath 무결성 검사이며 임의 Python 실행을 격리하는 sandbox가 아니다. 운영자에게 임의 transport/callback을 받지 않는다. 생성은 기존 관측을 읽되 DUT 명령은 실행하지 않는다.

## receipt와 정지 확인

반환 exact 키는 `schema_version=1`, `kind=synthetic_dut_stop_receipt`, `execution_mode=virtual_fleet_dut_stop`, `synthetic=true`, `hardware_verified=false`, `physical_model_verified=false`, `model_execution_verified=false`, `oem_support_status=not_assessed`, `request_id`, `transport_family`, `device_id`, `profile_id`, `request_context`, `status`, `reason_code`, `acknowledgement`, `stop_response`, `read_observation`, `commands`, `receipt_scope=historical_observation`, `current_stop_authority=false`, `observation_context`다.

request_context와 observation_context는 해당 시점의 tick/setup_revision이며 관측하지 못하면 None이다. acknowledgement의 exact 키는 `received`, `completion`, `origin`이며 completion은 `not_sent`, `acknowledged`, `partial`, `unknown`, origin은 `none`, `virtual_fleet`, `synthetic_delivery`다. commands는 실제 발행한 request_id/action 순서이며 최대 stop 1회와 read 1회다. 반환의 stop_response/read_observation은 검증한 같은 DUT의 가상 envelope 또는 None이다. ACK와 read는 각각 출처·원래 문맥을 유지한다.

| status | 의미 |
|---|---|
| blocked | 가용성/권한/모델FW gate 실패. DUT 명령 0 |
| unconfirmed | timeout·끊김·partial·ACK만 수신·정지 관측 부족·문맥/응답 오류·설정 변경. 자동 재송신 0 |
| confirmed_synthetic | 실제 같은 가상 DUT의 stop 성공 후 read에서 현재 idle/configured/빈 output과 일치하는 문맥 확인 |

stop/read의 device/profile/role, tick/setup_revision, 정확한 synthetic=True/hardware_verified=False를 확인한다. stop으로 인한 정상 revision 변화만 허용하고 외부 설정·tick 변화나 다른 DUT 관측은 확정으로 쓰지 않는다. 정상 stop ACK에 남은 RF 출력이나 오류 reason을 끼워 넣으면 거절한다. 원래 values.reason 진단 문자열은 author 기록에 보존하고 operator envelope에서는 제외한다. 빈 RF 출력 하나만으로 실물 정지를 추론하거나 RF 수치·정지 threshold를 만들지 않는다. 모든 receipt는 역사 관측이며 현재의 정지 권한이나 영구 정지 보장이 아니다.

reason_code는 `observed_stopped`, `transport_unavailable`, `permission_denied`, `model_firmware_mismatch`, `transport_disconnected`, `deadline_exceeded`, `partial_acknowledgement`, `observation_missing`, `stop_not_observed`, `context_mismatch`, `invalid_response`, `configuration_changed`, `runtime_error` 중 하나다. 형식/객체 오류의 ValueError는 `dut_stop_configuration_invalid`, `dut_stop_fleet_invalid`, `dut_stop_device_invalid`, `dut_stop_request_invalid`, `dut_stop_request_unknown`, `dut_stop_cache_full`이다. 원시 예외는 operator 결과에 복사하지 않는다.

## 합성 시나리오와 보존

작성자 scenario는 `normal`, `disconnected`, `timeout_before`, `timeout_after_stop`, `partial_delivery`, `ack_only`, `no_effect`, `stale_read`, `wrong_context`다. 선택과 고장 정답은 operator DTO에 넣지 않는다. timeout은 합성 delivery 실패이며 실제 wall-clock transport 측정이 아니다.

normal/ack_only/timeout_after_stop/stale_read/wrong_context는 기존 Fleet stop을 실행한다. ACK-only는 read를 보내지 않고, stop 후 timeout은 응답을 수신한 것으로 표시하지 않는다. partial_delivery/no_effect는 합성 delivery ACK와 실제 기존 DUT read를 연결하며 stop을 적용했다고 표시하지 않는다. 실제 DUT 상태를 별도로 만들거나 바꾸지 않는다. stale_read/wrong_context는 원래 Fleet 응답을 보존한 뒤 수신 문맥만 어긋나게 해 거절 경계를 검사한다. 어느 시나리오도 복구·취소·start·tick 진행·재부팅·서비스/FW 변경을 자동 실행하지 않는다.

host는 author_record로 최초 요청 문맥, 고정 author 설정, 원래 가상 응답·수신 응답·정제 실패와 operator receipt를 detached 사본으로 읽을 수 있다. 개별 packet은 depth 32/32 KiB, operator receipt는 depth 32/96 KiB, author wrapper는 depth 36/256 KiB의 별도 예산이다. author의 exchanges/event/raw_response 포장 때문에 이미 허용한 packet을 depth 32로 다시 거절하지 않는다. packet 예산 밖의 응답은 정제 invalid_response를 남기고 원래 command/context와 불확정 receipt를 cache한다. stop을 발행하기 직전 ACK completion을 unknown으로 바꾸며 적용 뒤 예외나 ACK 미확인은 not_sent로 되돌리지 않는다. 이 진단은 `.local/` 등 비공개 증거로 보존하고 operator에게 전달하지 않는다. 함수 자체는 파일·네트워크·외부 계정 I/O를 수행하지 않는다.

최대 4개의 raw/received packet과 operator receipt의 합은 224 KiB이며 나머지 32 KiB는 고정 metadata 포장 예산이다. 최종 author 포장의 직렬화가 실패하면 먼저 보관한 command/context/ACK를 유지하고 결과를 unconfirmed/runtime_error로 낮춘다. 유효한 예산 안의 원문은 고정 필드로 다시 보관하고 비공개 `diagnostic_error=author_record_invalid`를 남긴다. 잘못된 추가 포장 필드는 제외한다. 이 경우에도 최초 빈 cache로 돌아가거나 같은 ID를 재실행하지 않는다. 최대 크기 조합 검사는 직렬화 한계 fixture이며 실제 유효 DUT 응답으로 세지 않는다.

요청 ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`이다. adapter별 최대 128개 receipt/author 기록을 보관하며 축출하지 않는다. 같은 ID는 최초 receipt의 독립 사본을 그대로 반환하고 Fleet 명령을 다시 발행하지 않는다. DUT가 이후 다시 송신하거나 설정이 바뀌어도 역사 receipt를 현재 권한으로 올리지 않는다. 새 ID로 128개를 초과하면 명령 전에 거절한다. 설정 변경은 새 adapter가 필요하며 이전 cache를 초기화하거나 재사용하는 API는 없다. 재시작/영속 복구와 실물 취소·안전 정지는 지원하지 않는다.

## 검사

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_dut_stop_simulation.py -q
python -X utf8 -B -m unittest discover -s tests -p 'test_virtual_fleet*.py' -q
python scripts/check_artifacts.py
```

unit double의 응답 변조 검사와 실제 기존 Fleet→adapter 시나리오 증거를 구분한다. confirmed_synthetic은 가상 상태 확인이며 실제 ADB/OEM/GUI/AT/DIAG, 단말/FW, RF 물리·실제 AI·시험소 업무 완료의 검증이 아니다.
