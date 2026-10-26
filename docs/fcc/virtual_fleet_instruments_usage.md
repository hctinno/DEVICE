# 가상 계측·통신·시험 소프트웨어 역할

2026-10-24, Asia/Seoul. VLAB-ALL-001 개발2의 [구현](../../labflow/virtual_fleet/instruments.py), [검사](../../tests/test_virtual_fleet_instruments.py), [계획](../superpowers/plans/2026-10-24-VLAB-ALL-001-D2.md).

이 모듈은 11개 역할을 입력·설정·가상 시간에 따라 실행한다. 실제 네트워크, 장비, SDK, 모델 API, Office, 매크로를 호출하지 않는다. 공개 예제와 검사는 독립 합성값을 사용한다. 실제 보고서의 수치·수식·시리얼·암호와 감사 결과는 공개 fixture에 포함하지 않는다.

## 계약과 연결

`DEVICE_FACTORIES[role](profile: dict, seed: int)`가 장치를 생성한다. `profile_id`, `role`, `simulation_parameters`를 사용하며 모델 이름에서 옵션·펌웨어·범위·교정 이력을 추정하지 않는다. `ROLE_ACTIONS`는 action별 인수의 type/required/unit 및 완료 의미, `ROLE_PORTS`는 입력/출력의 이름과 kind를 제공한다.

```python
device.perform(action, parameters, tick=tick, setup_revision=revision, inputs=ports)
device.advance(tick=tick, setup_revision=revision, inputs=ports)
device.observation(tick=tick, setup_revision=revision)
device.author_control(fault, value)  # 작성자 전용; 운영자/HTTP에 노출하지 않는다.
```

`perform`은 `{status, values, setup_changed}`, `observation`은 `{status, values}`를 반환한다. status는 `ok/pending/invalid/unsupported/error/disconnected`다. 가상 시간은 감소할 수 없고 실제 sleep을 사용하지 않는다. `values`에는 상태·이유·설정·설정 revision·`operation_complete`·교정 상태·`outputs`가 있다. runtime이 tick/revision/profile 및 `synthetic=true`, `hardware_verified=false`를 감싼다. 입력에 들어온 provenance나 숨은 고장 설정을 관측에 복사하지 않는다.

| 역할 | 입력 port:kind | 출력 port:kind |
|---|---|---|
| power_meter | sensor:measurement, power:power | measurement:measurement |
| signal_analyzer, emi_receiver | rf:rf, power:power | measurement:measurement |
| signal_generator | power:power | rf:rf |
| communication_tester, bluetooth_tester, wireless_ap | rf:rf, power:power | rf:rf, measurement:measurement, data:data |
| dfs_system | rf:rf, power:power | rf:rf, measurement:measurement |
| network_test_station | rf:rf, data:data, power:power | measurement:measurement, data:data |
| test_software | measurement:measurement, data:data | control:control, data:data |
| network_analyzer | reference:rf, test:rf, path:data, power:power | measurement:measurement |

출력은 `values.outputs[port]`에 객체로 들어간다. action에 필요한 port만 검사한다. TX 시작에 수신 RF를 요구하지 않으며, software는 전원 입력이 필요 없다. 입력이 없거나 `{valid:false, reason:'output_unavailable', ...}`이면 필요한 값을 정상 0으로 채우지 않는다. VNA에 무효 path가 연결됐으면 reference/test 입력으로 우회하지 않는다. software의 control 출력은 시험 완료 기록이며 RF 장비 제어 feedback 연결을 만들지 않는다. 제어는 외부 harness의 execute로 수행한다.

## 가상 정책

모든 기본값은 합성 정책이다. 실제 모델의 성능 사양이 아니다. 알 수 없는 키와 잘못된 타입은 factory가 거절한다.

| simulation_parameters | 기본값/범위 | 의미 |
|---|---|---|
| measurement_ticks | 2, 정수 1 이상 | 취득·내부 교정 완료 지연 |
| operation_timeout_ticks | 100, measurement_ticks 이상, 1,000,000 이하 | 트리거 대기·취득 정체의 deadline |
| noise_db | 0, 0~100 | 완료 때 한 번 샘플링하는 균일 잡음 ±dB |
| frequency_min_hz / frequency_max_hz | 1 / 100e9, 양수·증가 | 가상 입력·설정 범위 |
| maximum_input_dbm | 30, 유한수 | 입력 ON 평균 및 선택한 peak의 상한; TX 출력 상한에도 사용 |
| power_required | true, boolean | false인 명시적 정책만 전원 검사를 생략; software는 전원 불필요 |
| calibration_valid | true, VNA는 false | 최초 가상 교정 상태; 실제 교정 성적서와 무관 |
| accepted_sensor_ids | 생략, power_meter 전용 문자열 배열 | 센서 source ID 허용 목록, 최대 1,000개 |
| function | combined, dfs_system 전용 | analyzer / generator / combined |

전원 packet은 `{valid:true, enabled:true, voltage_v:양수}`여야 한다. 전원 손실 시 진행 작업과 송신을 멈추며 전원 복귀만으로 TX를 다시 시작하지 않는다. seed와 profile ID로 잡음 순서를 고정한다. 같은 취득의 fetch는 재측정하거나 잡음을 다시 샘플링하지 않는다.

## 동작과 상태

공통 동작은 `configure`, `reset`, `recover`, `read_error`, `abort`다. configure 인수는 아래 표의 선택 필드이며 잘못된 설정은 기존 설정을 바꾸지 않는다. 변경된 설정은 이전 취득·결과를 무효화하고 `setup_changed=true`를 반환한다. reset은 설정을 기본값으로 되돌리고 작업·출력을 멈춘다. reset으로 오류 FIFO를 지우지 않는다. read_error는 30개 한도의 FIFO에서 하나를 꺼내며 빈 큐는 `error:null`이다. 오류 문자열은 가상 API 코드이며 제조사 SCPI 오류 번호가 아니다.

전력계 전용 `set_display_unit({"unit":"W"})`은 현재 window의 표시만 바꾸는 명시 동작이며 dBm도 받는다. 같은 장치의 `configuration.unit`을 갱신하지만 `setup_changed=false`이며 setup/configuration revision과 원 취득·pending·BUS 대기·deadline을 보존한다. 출력 투영 단계에서 유효한 원 취득값만 변환하며 시간 진행·새 잡음 샘플·센서 재시작을 하지 않는다. stale/stop/path loss/단절 등 원 무효 상태는 그대로다. 이 action은 unit만 필수로 받고 mW·window·mode·추가 옵션을 거절한다. 일반 `configure(unit=...)`의 기존 무효화 계약과 configure의 mW 지원은 유지한다. 다른 역할에는 이 action이 없다.

측정 역할의 `acquire`와 software의 `run`은 pending을 반환한다. advance로 완료한 뒤 `fetch`로 현재 결과를 읽는다. BUS 대기는 별도 trigger가 필요하다. abort는 작업과 결과를 취소한다. recover는 통신·전원 원인이 해소됐는지 확인한 뒤 idle로 돌아가며 새 acquire/start_tx가 필요하다. 취득 중 중복 acquire는 진행 작업을 새 취득으로 대체하지 않는다. 요청 ID 재시도 처리는 공통 runtime이 담당한다.

진행 중 setup revision이나 입력이 바뀌면 취득을 무효화한다. 완료 결과도 현재 입력·전원·교정·source·revision이 유효할 때만 출력한다. 결과에 획득 tick/setup revision, 장치 설정 revision, source 및 단위·quantity를 남긴다.

start_tx/stop_tx로 실제 송신 상태가 바뀌면 진행 중 취득·완료 결과·입력 signature를 먼저 폐기하고 transmitting/idle로 전이한다. 새 setup revision의 응답에 이전 측정값을 섞지 않으며, 첫 start_tx부터 유효 RF 출력을 유지한다. 현재 송신 상태와 같은 동작을 반복하면 setup_changed=false이고 진행 중 취득/완료 결과와 상태를 보존한다.

| 역할 | configure 필드 | 추가 동작 |
|---|---|---|
| power_meter | frequency_hz, measurement_mode, unit, window, trigger_source | acquire/fetch, trigger, set_display_unit, calibrate, verify_calibration |
| signal_analyzer | frequency_hz, bandwidth_hz, rbw_hz, normalization_hz, measurement, measurement_mode, detector | acquire/fetch, calibrate, verify_calibration |
| emi_receiver | frequency_hz, bandwidth_hz, rbw_hz, measurement, measurement_mode, detector, impedance_ohm, antenna_factor_db_per_m | acquire/fetch, calibrate, verify_calibration |
| signal_generator | frequency_hz, bandwidth_hz, power_dbm, duty_cycle, crest_factor_db, modulation | start_tx/stop_tx |
| communication_tester, bluetooth_tester | 위 TX 필드와 offered_rate_mbps, noise_figure_db, minimum_snr_db | start_tx/stop_tx, acquire/fetch |
| wireless_ap | 위 통신 필드와 ssid | start_tx/stop_tx, acquire/fetch |
| dfs_system | frequency_hz, bandwidth_hz, power_dbm, detection_threshold_dbm, pulse_width_s, pulse_repetition_hz | analyzer는 acquire/fetch, generator는 start_tx/stop_tx, combined는 둘 다 |
| network_test_station | frequency_hz, bandwidth_hz, offered_rate_mbps, noise_figure_db, minimum_snr_db | acquire/fetch |
| test_software | criteria | run 또는 acquire, fetch |
| network_analyzer | start_hz, stop_hz, points | calibrate, acquire/fetch |

송신·RF 측정 전 frequency_hz 설정이 필요하다. meter는 센서 주파수를 사용하며 frequency_hz를 선택 설정하면 센서 주파수와 1 Hz 이내로 일치해야 한다. VNA는 시작/끝 주파수를 설정한다. 양수 bandwidth/RBW/정규화 대역·임피던스·트래픽 속도를 요구한다. 설정 JSON은 직렬화 32 KiB 이하이며 식별 문자열은 UTF-8 200 byte 이하다.

## 전력계·분석기·수신기

RF `power_dbm`은 ON 구간 평균이다. `0 < duty_cycle <= 1`, `crest_factor_db`는 ON 평균에서 peak까지의 dB 차다. 상위 경로의 감쇠·이득을 다시 적용하지 않는다.

- `measurement_mode`: on_average는 입력 ON 평균, time_average는 `ON + 10 log10(duty)`, peak는 `ON + crest`다. crest가 없는 비 CW 입력의 peak는 무효다. RF의 modulation이 명시적 CW일 때만 crest 누락을 0으로 허용한다. 센서 packet은 modulation을 보장하지 않으므로 crest 누락을 추정하지 않는다.
- meter의 unit은 dBm/W/mW다. `W = 10^(dBm/10)/1000`으로 변환한다. 원 취득값은 모드·잡음을 반영한 dBm으로 한 번 저장하고 출력에 `acquisition_value/acquisition_unit`으로 표시한다. `value/unit`은 현재 configuration.unit으로 투영하므로 dBm↔W 왕복도 원 값을 바꾸지 않는다. 최초 W/mW 설정으로 취득해도 원 취득 단위는 dBm인 합성 엔진 정책이며 제조사 내부 구현의 재현 주장이 아니다. 센서 packet은 status=ok, valid=true, unit=dBm, value=power_dbm, frequency_hz, duty_cycle, crest_factor_db(선택), acquisition_tick/setup_revision, source_id를 갖는다. 미래 tick·다른 revision·불일치 수치·허용되지 않은 센서는 거절한다.
- meter의 window는 1~4 측정 창이며 입력 센서는 한 port다. fetch의 선택 window 인수도 1~4다. 이 가상 정책은 창 선택을 포함한 설정 변경 뒤 이전 창의 결과를 재사용하지 않는다. 창 번호를 물리 센서 수로 해석하지 않는다.
- meter trigger_source는 immediate/bus다. configure로 bus를 선택하는 것만으로 arm되지 않는다. acquire→trigger_wait→trigger→acquiring→advance→complete 순서다. 대기·정체 timeout에는 측정값을 내지 않는다.
- analyzer/EMI의 detector는 rms/peak/quasi_peak다. peak는 ON+crest를 사용한다. quasi_peak는 시간 평균과 peak 사이의 tick 기반 합성 envelope이며 CISPR 응답을 재현한 검파기가 아니다. 두 경우 필요한 crest와 입력 상한을 확인한다.
- measurement=psd는 선언된 입력 bandwidth에 전력이 균일하다는 합성 정책이다. 결과 value는 `P - 10 log10(B)`와 dBm/Hz다. rbw_band_power_dbm과 normalization_hz에 대한 normalized_band_power_dbm을 별도로 기록한다. RBW를 정규화 단위로 바꾸거나 실제 trace 적분을 수행하지 않는다.
- analyzer의 measurement는 power/psd/voltage를 지원한다. field_strength 설정은 `error/unsupported_measurement`로 거절하며 기존 설정을 보존한다. EMI는 power/psd/voltage/field_strength를 지원한다.
- EMI 기본 measurement=voltage는 `dBuV = dBm + 90 + 10 log10(R)`이며 기본 R=50 ohm이다. EMI의 field_strength는 명시적 antenna_factor_db_per_m을 더해 dBuV/m으로 출력한다. 보정값이 없으면 무효다. analyzer의 voltage 변환은 고정 합성 50 ohm 정책이다.

meter/analyzer/EMI의 calibrate는 전원이 필요한 가상 내부 routine이며 외부 RF/POWER REF를 필수로 요구하지 않는다. 완료하면 operation_complete=true와 calibration_state=verification_required를 반환한다. verify_calibration에는 알려진 합성 reference_dbm과 양수 tolerance_db가 필요하며 현재 센서/RF와 비교한다. 완료 플래그만으로 교정 유효를 만들지 않는다. 중단된 교정은 재확인이 필요하다.

P-series 공식 자료에서 확인한 창·arm/trigger·취득/fetch·완료와 유효성의 구분을 참고했지만 이 모듈은 JSON 가상 동작만 제공한다. 미검토 raw SCPI, REAL/ASCII binary 직렬화, TRACe format, CAL:AUTO 모호한 동작, MRES 예제 차이, 실제 FW/options와 현재 교정 증명은 지원/검증으로 표시하지 않는다.

## 통신·DFS·시험 소프트웨어·VNA

통신/BT/AP/station의 수신 동작은 입력 bandwidth·수신 전력·잡음 지수로 잡음 바닥과 SNR을 계산한다. 합성 SNR threshold로 associated를 정하며 Shannon capacity와 offered rate 중 작은 값으로 throughput을 제한한다. 합성 BER도 SNR에 따라 바뀐다. 실제 링크 handshake·변조별 성능·Bluetooth/Wi-Fi/OEM 프로토콜을 검증한 모델이 아니다. AP는 설정 SSID를 출력 metadata로 남긴다. station에는 `{valid:true, offered_rate_mbps:양수}` data 입력이 추가로 필요하다.

DFS generator는 pulse_width_s×pulse_repetition_hz를 duty로 쓰는 pulse RF를 출력한다. analyzer는 pulse metadata의 일관성과 수신 전력 threshold로 detected를 계산한다. 무효 pulse나 generator/analyzer 용도에 맞지 않는 동작을 성공 처리하지 않는다. 규정의 DFS waveform 집합·통계·CAC/channel move 판정은 별도 구현 대상이다.

software의 criteria는 최대 128개, 고유 id/unit/operator/유한 limit와 선택 quantity를 갖는다. operator는 <=, <, >=, >, ==다. 한 조건은 measurement port에서, 여러 조건은 `{valid:true, measurements:{id:measurement_packet}}` data에서 받는다. 빈 조건·누락·unit/quantity 충돌·stale packet은 무효다. 조건별 source/acquisition/수치/단위/operator/limit/판정을 결과에 보존한다. 유효한 부적합은 status=ok, verdict=fail로 남으며 장치 장애로 바꾸지 않는다. authorized_for_issue=false이고 공식 성적서 발행 권한을 부여하지 않는다.

VNA 단일점은 같은 주파수 reference/test의 차에서 `S21_dB = test_dBm - reference_dBm`을 계산한다. sweep은 `{valid:true, source_id, frequency_loss_db:[[Hz,dB],...]}` path 곡선만 사용하며 선형 보간한다. 주파수 곡선은 양수·오름차순·최대 4,096점, sweep은 1~2,048점이다. 곡선 범위 밖 외삽을 하지 않는다. loss_db와 음수 부호의 s21_magnitude_db를 별도로 출력하며 phase_supported=false다. 양의 gain을 가진 명시적 곡선도 수학적으로 표현할 수 있다.

VNA의 첫 상태는 verification_required다. calibration_standard=true인 합성 표준 path에서 calibrate의 선택 standard_loss_db(기본 0)를 비교한다. 합성 허용차 0.05 dB 이내여야 valid가 된다. 일반 측정 곡선의 값은 이 validity 검사로 덮어쓰지 않는다. 설정 변경·reset 뒤에는 다시 검증해야 한다. 이는 magnitude 손실 정책이며 HP8753D 전체 명령·위상·실제 sweep 정밀도/교정 보정을 구현한 것이 아니다.

## 실행 예와 오류 복구

아래는 장치 단독 계약의 완전한 합성 예다. 통합할 때는 runtime의 execute/advance와 연결에서 입력·revision을 받는다.

```python
from labflow.virtual_fleet.instruments import DEVICE_FACTORIES, ROLE_PORTS

profile = {"profile_id": "synthetic-meter", "role": "power_meter",
           "ports": ROLE_PORTS["power_meter"], "simulation_parameters": {}}
device = DEVICE_FACTORIES["power_meter"](profile, 123)
ports = {
    "power": {"enabled": True, "valid": True, "voltage_v": 12.0},
    "sensor": {"status": "ok", "valid": True, "value": 10.0, "power_dbm": 10.0,
               "unit": "dBm", "frequency_hz": 2.45e9, "duty_cycle": 0.25,
               "crest_factor_db": 4.0, "source_id": "synthetic-sensor",
               "acquisition_tick": 0, "acquisition_setup_revision": 0},
}
device.perform("configure", {"measurement_mode": "time_average"},
               tick=0, setup_revision=0, inputs=ports)
device.perform("acquire", {}, tick=0, setup_revision=0, inputs=ports)
device.advance(tick=2, setup_revision=0, inputs=ports)
result = device.observation(tick=2, setup_revision=0)
assert abs(result["values"]["outputs"]["measurement"]["value"] - 3.9794000867) < 1e-9
```

정상 조합 예는 전원 output→발생기 start_tx→분석기 acquire→2 tick→software run→2 tick→verdict다. 모든 장비 설정을 먼저 확정해 취득 중 global setup revision이 바뀌지 않게 한다. meter BUS 예는 configure(trigger_source=bus)→acquire→대기 관측→trigger→2 tick→fetch다. VNA는 sweep 설정→합성 through calibrate→2 tick→일반 손실 곡선 acquire→2 tick→S21/loss 배열이다. 추가 역할과 입력별 예는 검사 파일에 있다.

작성자 전용 고장은 모든 역할의 disconnected/drop_output, 측정 역할의 stuck, software 외 측정 역할의 gain_error_db(±100), 교정 역할의 invalid_calibration, meter의 sensor_mismatch다. boolean 고장에는 boolean만 허용하고 해당 역할에 없는 고장은 거절한다. 운영자 관측에 고장 이름·주입값·정답을 보내지 않는다. drop_output은 status=ok여도 출력이 없는 경우를 재현하며 공통 runtime은 하류에 output_unavailable 무효표식을 전달한다.

단절 복구 수용은 작성자 disconnected=true→운영자 disconnected/출력 없음→작성자 false→운영자 recover→새 acquire 또는 start_tx다. 취득 정체는 stuck=true→deadline 초과→error/출력 없음→작성자 false→recover→새 취득이다. 교정 무효는 원인 해소 후 합성 교정/기준 확인을 다시 수행한다. 실패와 취소는 성공 측정값으로 채우지 않는다.

## 검증 기록과 남은 범위

이 단위의 42개 검사는 계산·단위·모드·트리거·전원·센서·취득 중/완료 후 변경·시간 초과·복구·seed·FIFO·창·조건별 부적합·VNA 보간/표준/외삽 금지·출력 크기·중첩 인수·주파수 일치·작성자 경계·역할별 측정 지원 범위·송신 상태 전이와 중복 요청을 확인한다. 검사는 `python -m unittest discover -s tests -p test_virtual_fleet_instruments.py -v`로 실행한다.

추가 [표시 단위 검사](../../tests/test_n1911a_display_unit.py) 7개는 같은 엔진의 원 취득/표시 분리와 Decimal 수치 기준·잡음 샘플 순서·진행 취득·일반 configure 무효화 보존을 검증한다. [N1911A 세션](n1911a_virtual_session_usage.md)은 이 공개 action을 사용하며 RF 수학이나 측정 캐시를 복제하지 않는다.

고정 catalog commit `a548af3e5b7fa84e1a0c5ed93af064db689de371`, 파일 SHA-256 `037b92b4d32fc7c65d6e5ec0b518f5933c48745e3e5907c158b0317ab4923ea6`의 담당 16개 프로필 모두 factory/port 일치 및 합성 정상·통신 단절·복구 재취득을 실행했다. common core/facility와 연결한 전원→발생기→분석기→software DAG의 정상·미출력 무효 전파·재취득도 확인했다. 원본 감사 및 호환 script/coverage는 개발2의 비공개 작업 공간에 보존한다. 나머지 catalog 역할과 전체 UI/시험 조합 통합은 담당별 결과를 총괄이 인수한다.

이는 합성 계산·상태·연결 검증이다. RF waveform/trace·실제 throughput/DFS 응답·제조사 전체 명령·설치 옵션/FW·계측 정확도·실장비 비교·현장 운전·기관 적합성은 검증하지 않았다. 실제 RF·EMC 시험소의 전체 업무/물리 무인화 완료를 뜻하지 않는다. Workbook reader와 실제 모델 AI 평가 계약은 보존한 후속 작업이다.
