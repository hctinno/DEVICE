# 가상 시험소 DUT·센서·RF 경로 사용법

[RF 모듈](../../labflow/virtual_fleet/rf.py)은 10개 역할의 설정, RF 전달, 취득, 고장과 복구를 계산한다. 숫자는 호출자가 선언하는 합성 정책이다. 실제 모델의 범위·정밀도·옵션·펌웨어·교정이나 실장비 운전을 검증한 구현으로 사용하지 않는다. 기존 문서 추출·접수·단일 장비 API는 변경하지 않는다.

## 공통 인터페이스

`DEVICE_FACTORIES[role](profile, seed)`로 생성한다. profile에는 `profile_id`, `model`, `role`, `ports`, 선택적인 `simulation_parameters`를 전달한다. 전체 catalog의 제조사·증거·프로파일 종류 검증과 실제 연결 구성은 공통 runtime의 책임이다. factory는 역할·포트·알려진 합성 정책을 검사하며, 알 수 없는 정책은 거절한다. 비어 있거나 불완전한 정책으로 만든 장치는 필요한 설정을 마칠 때까지 출력을 내지 않는다.

| 호출 | 동작 |
|---|---|
| `perform(action, parameters, *, tick, setup_revision, inputs)` | `{status, values, setup_changed}` 반환 |
| `advance(*, tick, setup_revision, inputs)` | 가상 시각의 입력을 반영하고 상태 전이, 반환값 없음 |
| `observation(*, tick, setup_revision)` | 마지막으로 계산한 `{status, values}`의 분리된 복사본 반환 |
| `author_control(fault, value)` | 작성자용 고장 주입·해제, 반환값 없음 |

tick과 setup_revision은 0 이상 정수이며 bool은 허용하지 않는다. 공통 runtime이 시계 진행·셋업 버전 증가·중복 요청·연결 순서·출처 envelope를 관리한다. RF 모듈은 입력의 임의 부가 필드를 출력에 복사하지 않는다. 같은 seed와 입력에는 같은 결과를 내며, 현재 확률 잡음은 없다. 역할 단독 결과에 실측 표시를 추가하지 않는다. runtime에서 `synthetic: true`, `hardware_verified: false`를 보존한다.

상태는 `ok`, `pending`, `invalid`, `unsupported`, `error`, `disconnected`다. 실패·대기 상태에는 정상 수치를 만들지 않고 `values.outputs`를 비운다. `observation`은 시간을 진행하지 않는다. 입력이 바뀌었으면 먼저 `advance`를 호출해야 하며, 셋업 버전이 다른 관측에서는 이전 출력을 제거한다.

## 역할과 포트

포트 종류는 rf, power, environment, control, measurement다. `values.outputs[출력 포트]`를 다음 장치의 `inputs[입력 포트]`에 연결한다. 물리 미연결은 입력 키 없음, 연결됐으나 upstream 출력 없음은 `{valid: false, reason: 'output_unavailable', ...}`다. 후자를 0으로 계산하지 않는다.

| 역할 | 입력 → 출력 | 합성 동작 |
|---|---|---|
| dut | power, environment, control → rf | 전원·환경·선택적 control gate 확인, 시작 지연 뒤 송신 |
| power_sensor | rf → measurement | 유효한 RF의 ON 구간 평균을 가상 취득 |
| attenuator | rf → rf | 고정 감쇠 또는 선언한 step 선택 |
| coupler | rf → rf, coupled | through 손실과 coupling을 각 출력에 한 번 적용 |
| splitter | rf → rf_1, rf_2 또는 rf_1…rf_4 | 출력마다 `입력 − 손실 − 10 log10(분기 수)` |
| antenna | rf → rf | 선언한 결합 경로의 gain − loss |
| amplifier | rf, power → rf | 전원 확인 후 gain 적용, 입력·출력 한계 초과는 error |
| filter | rf → rf | 전체 점유 대역이 선언한 통과 구간 안일 때 손실 적용 |
| rf_switch | rf_1…rf_N, control → rf | 선택 경로의 가상 settling 후 전달, 최대 16개 RF 입력 |
| lisn | rf, power → rf, power | RF 손실과 유효한 전원 전달을 구별 |

`ROLE_PORTS`는 기본 선언이고 `ROLE_PORT_VARIANTS`는 controller-only와 4way 선언을 제공한다. splitter 출력 수와 `ways`가 일치해야 한다. controller-only는 RF 포트를 갖지 않으며 선택적인 control 입력과 control 출력만 갖는다. FBSM-01B controller, FMSR 계열 RF matrix, OSP 120의 역할을 한 장치 동작으로 합치지 않는다. 모델명만으로 실제 내부 구성이나 명령어를 추정하지 않는다.

## 설정과 action

모든 역할은 configure/read/reset을 제공한다. DUT를 제외한 역할은 `enable({'enabled': bool})`을 제공한다. DUT는 start/stop, 센서는 acquire, step attenuator는 set_attenuation, switch는 select_path를 추가한다. 실제 선언은 `ROLE_ACTIONS[role][action]`의 parameters·type·required·unit·completion을 사용한다.

configure는 기존 설정에 필드를 합친 후 한 번에 검증한다. 실패 시 기존 설정을 보존한다. 같은 설정은 `setup_changed: false`이며 완료된 센서 값을 지우지 않는다. 변경한 설정은 진행 중 활동과 취득값을 지운다. reset은 설정과 작성자 고장을 보존하고 송신·취득·선택 경로를 지운다. 고장 해제는 `author_control(..., False)`로 별도 수행한다. 이 reset을 실물 RF 안전 정지 명령으로 해석하지 않는다.

| 역할 | configure의 주요 필드 |
|---|---|
| dut | frequency_hz, power_dbm, bandwidth_hz, duty_cycle, modulation 필수; crest_factor_db, startup_ticks |
| power_sensor | calibration_valid 필수; expected_model, acquisition_ticks, acquisition_policy |
| attenuator | attenuation_db 필수; steps_db, loss_table |
| coupler | through_loss_db, coupling_db 필수 |
| splitter | ways 필수; loss_db 또는 loss_table |
| antenna | gain_db 필수; loss_db 또는 loss_table |
| amplifier | gain_db 또는 gain_table |
| filter | band_min_hz, band_max_hz 필수; loss_db 또는 loss_table |
| rf_switch | loss_db 또는 loss_table, settling_ticks; controller-only는 RF 손실 없이 routes 사용 |
| lisn | loss_db 또는 loss_table |

공통 configure 필드는 enabled, band_min_hz, band_max_hz, max_input_dbm, max_output_dbm이다. 주파수·대역폭은 Hz, 전력은 dBm, 이득·손실·crest는 dB, duty는 0 초과 1 이하 비율이다. 과부하 한계는 이 가상 모델의 ON 구간 평균 기준이다. 유한 숫자만 받으며 bool·NaN·무한대·표현 범위 밖 숫자·대역 계산 오버플로는 거절한다.

손실은 0 이상이다. 보정표는 주파수가 엄격히 증가하는 `[{frequency_hz, loss_db}]` 또는 `[{frequency_hz, gain_db}]`다. 구간 안에서 선형 보간하고 표 밖으로 외삽하지 않는다. 표와 scalar를 함께 선언하면 표가 해당 장치의 전체 손실·이득을 정하며 scalar를 다시 더하지 않는다. coupler는 두 출력의 선형 전력 합이 입력보다 커지는 정책을 거절한다. splitter의 loss는 이상적인 분기 손실에 추가되는 손실이다.

`simulation_parameters`에서만 지정하는 초기 정책:

| 정책 | 의미와 기본값 |
|---|---|
| requires_power | DUT·amplifier·LISN 기본 true. LISN은 전원 출력에도 유효 전원이 필요 |
| requires_environment | DUT 기본 true |
| requires_control | 기본 false. 선택적 포트라도 연결돼 있으면 유효한 gate 필요 |
| voltage_min_v / voltage_max_v | 전원을 사용하는 역할의 선언한 전압 구간 |
| temperature_min_c / temperature_max_c | DUT의 선언한 온도 구간 |
| assume_cw_crest_zero | 기본 false. 명시적으로 true인 CW에서만 누락 crest를 0으로 처리 |
| attenuator_mode | fixed 기본, 또는 step. step에는 steps_db와 그중 선택값이 필요 |
| controller_only | 기본 false. true이면 control 출력만 허용 |
| control_selects_route | 물리 RF matrix 기본 false. true이면 upstream selected_input을 따라 settling |

enabled 기본 true, startup/settling/acquisition_ticks 기본 1이며 1…1,000,000 정수만 허용한다. 센서는 acquisition_policy 기본 triggered, calibration_valid 기본 false, expected_model 기본 profile.model이다. 손실·이득·DUT 신호는 암묵적으로 0을 채우지 않는다.

fixed attenuator는 최초 설정 후 attenuation_db 변경을 거절한다. step은 명시한 정렬·중복 없는 steps_db 안에서만 선택하며 step과 loss_table 조합은 미지원이다. 이 step 목록이 해당 실장비의 실제 옵션이나 step 정밀도를 증명하지 않는다.

switch의 `select_path({'input_port': 'rf_1'})`는 즉시 RF를 연결하지 않는다. 기본 physical matrix는 로컬 선택과 control gate를 사용한다. `control_selects_route: true`일 때만 upstream selected_input이 선택을 바꾼다. 전환 완료 전에 현재 안정 경로로 선택을 되돌리면 미완료 전환과 기존 완료 시각을 취소한다. 이후 다른 경로를 선택하면 새 settling 시각을 적용하며, 같은 대기 경로를 반복 관측해도 시각을 연장하지 않는다. controller-only는 자신의 select_path를 사용하고 upstream은 승인 gate 역할만 한다. controller routes에서 이전 선택을 제거하면 새 선택 전까지 무출력이다. control payload는 `{status: 'ok', valid: true, enabled: true, selected_input, source_id}`다.

## DUT와 센서 취득

전원 입력은 `{enabled: true, valid: true, voltage_v}`다. 환경 입력은 `{valid: true, stable: bool, temperature_c, humidity_percent}`이며 습도는 0…100이다. DUT는 환경 안정화를 기다렸다가 startup_ticks를 센다. 전원·control·RF 유효성 상실 등으로 중단되면 새 start가 필요하다. stop은 즉시 가상 RF 출력을 지운다. 명령 수신·가상 송신을 실제 DUT 시험모드나 RF 출력 확인으로 표시하지 않는다.

RF frame은 `{status: 'ok', valid: true, frequency_hz, power_dbm, bandwidth_hz, duty_cycle, modulation, source_id, crest_factor_db}`다. power_dbm은 **ON 구간 평균**이다. crest가 누락되면 명시적인 CW 0 정책 외에는 무효다. 각 경로가 자신의 gain/loss를 한 번 적용하고 duty와 crest는 전달한다.

센서는 calibration_valid와 expected_model을 검사한다. 가상의 true는 실제 교정성적서 확인을 뜻하지 않는다. acquire 시 RF와 setup_revision을 고정하고 acquisition_ticks 뒤 완료한다. 입력 신호·출처나 셋업이 달라지면 진행 중/완료 취득을 지우며 triggered 모드는 새 acquire가 필요하다. continuous 모드는 새 조건으로 다시 취득한다. 고장 해제 후 이전 값을 되살리지 않는다.

measurement 출력에는 status, valid, value, unit, frequency_hz, power_dbm, duty_cycle, crest_factor_db, acquisition_tick, acquisition_setup_revision, source_id가 있다. value와 power_dbm은 입력 ON 평균을 그대로 유지하고 unit은 dBm이다. source_id는 센서 profile_id다. D2 power_meter의 sensor 입력으로 연결하며 시간 평균·peak 보정은 후속 meter가 한 번 적용한다. 센서에서 duty·crest를 다시 보정하지 않는다.

## 독립 실행 예

아래 숫자와 프로파일은 합성 입력이다. 저장소 루트에서 실행할 수 있다.

```python
from labflow.virtual_fleet.rf import DEVICE_FACTORIES, ROLE_PORTS

def make(role):
    return DEVICE_FACTORIES[role]({
        'profile_id': 'example-' + role, 'role': role, 'model': 'SYNTHETIC',
        'ports': ROLE_PORTS[role], 'simulation_parameters': {},
    }, 7)

attenuator = make('attenuator')
assert attenuator.perform('configure', {'attenuation_db': 2},
    tick=0, setup_revision=1, inputs={})['status'] == 'ok'
rf = {'status': 'ok', 'valid': True, 'frequency_hz': 1e9,
      'power_dbm': 10, 'bandwidth_hz': 1e6, 'duty_cycle': .25,
      'modulation': 'QPSK', 'crest_factor_db': 6, 'source_id': 'example-source'}
attenuator.advance(tick=1, setup_revision=1, inputs={'rf': rf})
output = attenuator.observation(tick=1, setup_revision=1)['values']['outputs']['rf']
assert output['power_dbm'] == 8

sensor = make('power_sensor')
assert sensor.perform('configure', {'calibration_valid': True},
    tick=1, setup_revision=1, inputs={})['status'] == 'ok'
assert sensor.perform('acquire', {}, tick=1, setup_revision=1,
    inputs={'rf': output})['status'] == 'pending'
sensor.advance(tick=2, setup_revision=1, inputs={'rf': output})
measurement = sensor.observation(tick=2, setup_revision=1)['values']['outputs']['measurement']
assert measurement['value'] == 8
assert measurement['duty_cycle'] == .25
assert measurement['crest_factor_db'] == 6
assert measurement['acquisition_tick'] == 2
assert measurement['acquisition_setup_revision'] == 1
```

## 고장과 검증 범위

공통 author fault는 disconnect, fault, no_output이다. rf_switch는 stuck, power_sensor는 measurement_invalid, model_mismatch를 추가 지원한다. 값은 bool이며 다른 이름·형식은 거절한다. 작성자 고장 이름·값을 운영 관측에 넣지 않는다. stuck switch는 pending을 유지하고 해제 후 가상 시계로 전환을 완료한다. DUT 고장 해제는 새 start, triggered sensor는 새 acquire가 필요하다.

[전용 검사](../../tests/test_virtual_fleet_rf.py)는 정상 계산, 전력 보존, 대역·표·과부하·입력 검증, 변형, 지연, 취득 무효화, 고장·복구를 확인한다.

```powershell
python -B -m unittest discover -s tests -p test_virtual_fleet_rf.py
python -B -m unittest discover -s tests
python -B scripts/check_artifacts.py
```

2026-10-24 Asia/Seoul 기준, private Un-licensed catalog 64개 중 담당 10역할·38프로파일에서 명시적 합성 정책을 사용해 생성·정상·disconnect·복구를 실행했다. catalog SHA-256은 `48ed0cb0be2cf1a4ae7a32f4cb570dc7805ee21b1bfc218efcec7a04e33f96bf`다. 이 수는 실물 장비 대수나 모델별 제조사 정밀도 검증 수가 아니다. 원문 수치·시리얼·원시 데이터는 이 코드·문서·검사에 포함하지 않았다.

이 분기의 RF 전용 40개와 전체 회귀 187개가 통과했다. 별도 private 복제본에서 총괄의 공통·시설·계측기 코드와 연결한 preview 10개도 통과했다. 수용 검사에서는 고정 감쇠기 공칭값을 보존하고, 미확보 제조사 step 대신 개발용 목록을 명시했다. 연결 preview의 통과를 전체 catalog의 시험 시나리오 완료나 총괄 최종 인수로 표시하지 않는다.

실장비 비교, 실제 DUT/OEM 도구, SCPI/VISA/네트워크 명령, 필터 notch 응답·증폭기 비선형·실제 안테나 전계·LISN 임피던스/잡음, 실제 RF 안전 인터록은 미구현·미검증이다. OSP 모듈·옵션·동기화·reset과 물리 RF 차단을 동일시하지 않는다. Licensed 원시·추가 암호 확인은 별도 보류이며 현재 가상 역할 실행의 선행 조건이 아니다.
