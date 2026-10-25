# 가상 meter 주파수 충돌 복구 정책

2026-10-25 Asia/Seoul. 공개 [설계](../superpowers/specs/2026-10-25-virtual-fleet-meter-frequency-recovery-policy-design.md)와 [계획](../superpowers/plans/2026-10-25-virtual-fleet-meter-frequency-recovery-policy.md)의 신규 행동 정책이다. 기존 [sensor 정책](../../labflow/virtual_fleet/policies.py)을 재사용하고, [FleetHarness](../../labflow/virtual_fleet/harness.py)가 같은 살아있는 가상 runtime에서 실행한다. 실제 장비·현장 네트워크·모델을 호출하지 않는다.

## API와 위임

```python
from labflow.virtual_fleet.meter_frequency_recovery_policy import RFMeterFrequencyRecoveryPolicy

policy = RFMeterFrequencyRecoveryPolicy()  # run마다 새 instance
```

생성자 인자는 없다. policy_id는 rf_meter_frequency_recovery_v1이고 기존 report.policy.kind는 fixture다. 입력은 기존 context8이며 goal은 아래 exact6이다.

```json
{
  "kind": "acquire_fresh_rf_sensor_meter",
  "dut_id": "dut",
  "sensor_id": "sensor",
  "meter_id": "meter",
  "minimum_acquisition_tick": 14,
  "allow_meter_frequency_reconfigure": true
}
```

세 ID는 서로 달라야 한다. minimum_acquisition_tick은 plain 비음수 int이고, allow_meter_frequency_reconfigure는 생략할 수 없는 plain bool이다. 실제 최소 tick은 caller의 초기 snapshot 이후로 지정한다. false이면 실제 새 meter 취득에서 충돌을 관측해도 설정을 변경하지 않고 blocked로 종료한다. true도 일반 설정 변경이나 물리 운전 권한을 뜻하지 않는다.

정책은 context를 수정하지 않으며 기존 execute4/advance2/stop3만 제안한다. 직접 장비 호출, request ID 생성, transport 재시도, 교정·reset·recover는 수행하지 않는다. DUT start, sensor acquire/read, meter acquire/fetch와 제한된 meter configure만 제안한다.

## 지원 조건과 행동

관측은 synthetic=true/hardware_verified=false여야 한다. catalog·topology·role_actions와 노드 identity, DUT에서 sensor로 이어지는 RF 경로, sensor.measurement에서 meter.sensor로 이어지는 연결을 확인한다. meter 설정은 on_average/dBm/window1/immediate만 지원한다. 주파수 외 설정을 바꿔 이 범위로 맞추지 않는다.

1. public RFSensorFixturePolicy에 exact4 파생 goal을 전달해 새 sensor 취득과 read를 요구한다. 원 top goal6은 유지한다.
2. 자기 meter.acquire 다음 flat receipt의 invalid와 현재 관측의 sensor_frequency_setting_conflict가 일치할 때만 복구를 검토한다. bootstrap의 cached reason만으로 configure하지 않는다.
3. 위임이 있으면 현재 sensor.frequency_hz를 그대로 복사한 frequency_hz 단일 파라미터 configure를 최대 한 번 제안한다.
4. receipt와 현재 설정·configuration_revision·global setup_revision을 결합한다. 변경 ACK는 완료 증거가 아니다. 새 child sensor 정책의 최소 tick을 max(원 최소 tick, 설정 receipt.tick+1)로 올리고 양쪽 옛 signature를 버린다.
5. 같은 runtime에서 sensor를 새로 취득·read한 뒤 meter를 새로 취득·fetch한다. meter acquisition_tick은 자기 acquire 제안 tick과 sensor acquisition_tick보다 모두 늦어야 한다.
6. 현재 DUT RF, sensor·meter의 source/input source, 주파수·unit·quantity·window, 현재 설정 revision·최신 global revision, declared_synthetic_policy와 fetch receipt의 동일한 signature를 확인한 후 completed를 제안한다.

이미 주파수가 일치하거나 기존 장비의 1Hz 허용 범위 안에서 유효 취득이 되면 configure는 0회다. on_average에서 meter.value와 새 sensor.power_dbm은 절대 1e-9dB 이내여야 한다. duty를 다시 곱하거나 crest를 더하지 않는다. 이 관계 검사는 독립 절대 산술 검증과 구별한다.

last_receipt는 action/request_id가 없는 flat envelope다. 정책이 자기 직전 제안을 기억하고 하네스·journal이 실제 intent/action/request ID를 결합한다. 설정 위치는 values.configuration 및 values.configuration_revision이다. 새 meter receipt의 설정도 현재 관측과 일치해야 한다. bool을 정수·측정값으로 수용하지 않는다.

run 동안 goal·위임·catalog·topology·role_actions는 고정한다. clock 역행, old revision, 동값의 stale sample, 다른 source·unit·설정, 빠진 fetch, 바뀐 목표 주파수는 완료 근거가 아니다. 알려진 잘못된 context/receipt는 failed, 지원 밖 선언·설정은 unsupported, 위임 부재·교정 불가·장비 실패는 blocked로 끝난다. 종료한 instance는 추가 장비 동작을 제안하지 않는다.

## 새 합성 실행 예

다음은 owner가 새로 작성한 입력이며 독립 봉인 oracle이 아니다. 제공 catalog의 모델 이름은 실물 옵션·제어 호환성 증거가 아니다. 선택 profile의 simulation_parameters와 현재 역할 기본값을 확인한 조건은 다음과 같다.

| 항목 | 이 예의 선언/확인 |
| --- | --- |
| DUT SM-A176U | 2.44GHz, ON 평균 9dBm, bandwidth 10MHz, duty 0.4, crest 4.5dB, 가상 startup 1tick |
| attenuator 8493C | fixed 10dB, loss_table 없음 |
| OSP 120 경로 | loss 0.5dB, loss_table 없음, settling 1tick |
| coupler 87300B | coupled 20dB, 별도 through 1.25dB는 이 sensor 분기에 가산하지 않음 |
| sensor N1921A | 교정 유효로 명시, triggered, 취득 1tick, 별도 noise/bias 주입 없음 |
| meter N1911A | initial 2.46GHz, on_average/dBm/window1/immediate, 취득 2tick, timeout 100tick |
| meter 합성 범위 | 기본 1Hz~100GHz, maximum_input 30dBm, noise_db=0, 초기 gain_error_db=0 |

RF 역할에는 이 catalog에서 추가 band/max_output 한계가 선언되어 있지 않다. 이 사실은 제조사 지원 대역이나 실측 정확도를 확인한 것이 아니다. 새 profile·옵션·FW·loss_table·noise를 사용할 때 지원과 수치 조건을 다시 확인해야 한다.

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example, get_role_actions
from labflow.virtual_fleet.harness import FleetHarness
from labflow.virtual_fleet.meter_frequency_recovery_policy import RFMeterFrequencyRecoveryPolicy

catalog = load_catalog("virtual_profiles/sm_a176u_unlicensed.json")
runtime, topology, bootstrap_receipts = create_conducted_example(catalog, seed=19)
# 다음 준비는 harness의 초기 snapshot 전에만 수행한다.
preparation = [
    ("dut", "stop", {}),
    ("dut", "configure", {
        "frequency_hz": 2.44e9, "power_dbm": 9.0, "bandwidth_hz": 10e6,
        "duty_cycle": .4, "modulation": "owner_synthetic", "crest_factor_db": 4.5,
    }),
    ("sensor", "configure", {"calibration_valid": True, "acquisition_policy": "triggered"}),
    ("meter", "configure", {
        "frequency_hz": 2.46e9, "measurement_mode": "on_average",
        "unit": "dBm", "window": 1, "trigger_source": "immediate",
    }),
]
setup_receipts = []
for index, (device, action, parameters) in enumerate(preparation):
    receipt = runtime.execute(f"prepare:{index}", device, action, parameters)
    setup_receipts.append(receipt)
    if receipt["status"] not in {"ok", "pending"}:
        raise ValueError("virtual preparation failed")

initial = runtime.observations()
goal = {
    "kind": "acquire_fresh_rf_sensor_meter",
    "dut_id": "dut", "sensor_id": "sensor", "meter_id": "meter",
    "minimum_acquisition_tick": initial["tick"] + 1,
    "allow_meter_frequency_reconfigure": True,
}
events = []
runner = FleetHarness(
    runtime, RFMeterFrequencyRecoveryPolicy(), goal=goal, catalog=catalog,
    topology=topology, role_actions=get_role_actions(), event_sink=events.append,
)
report = runner.run()
```

bootstrap 측정은 새 관측으로 세지 않는다. 초기 snapshot 이후 host가 복구 명령을 대신 실행하지 않는다. 이 입력의 직접 산술은 9−10−0.5−20=−21.5dBm이다. 위 코드의 events·receipt·현재 관측과 독립적으로 대조해야 하며 숫자 하나의 일치만으로 복구 행동을 수용하지 않는다.

## 검증과 결과 해석

[전용 테스트](../../tests/test_virtual_fleet_meter_frequency_recovery_policy.py)는 새 실제 FleetHarness 합성 실행으로 복구·이미 일치·위임 없음·교정 불가·지속 단절·stuck·응답 유실을 확인한다. 거절/모순 receipt와 공용 context 변조는 명시한 경계 double 또는 detached JSON 반사실 검사이며 실물 실패를 재현한 것으로 표시하지 않는다.

한 논리 configure와 물리 전송 횟수는 다르다. 응답 유실 시 기존 하네스만 같은 runtime/ID/body로 유계 재전송한다. 기본 예산은 decisions64/requests64/ticks32/wall30s/transport_retries2다. 재전송 소진의 runtime_mutation_uncertain·unresolved intent, budget/timeout 종료는 completed가 아니다.

result15/context8/journal event8·7종 계약은 유지한다. report의 completed는 fixture 주장이다. assessment·task_outcome·cleanup은 계속 not_assessed이며 fixture stop은 RF/전원/물리 정리 증거가 아니다. 기존 sensor/041 evaluator를 이 goal의 전체 승인으로 사용하지 않는다. 기존041 _MeterPolicy의 meter_frequency_conflict는 여전히 blocked가 기대다.

새 policy는 기존 engine20 hash 범위 밖이다. 실행 증거에는 기존 engine 판본과 별도로 이 정책 소스 SHA를 남겨야 한다. owner 테스트/산술·실행 trace와 총괄이 선봉인한 독립 기대의 제품 수용을 구별한다. 실제 모델 품질, 표준 PHY, burst 공통 시간창·교정·불확도·실장비 비교·현장 검증은 이번 검증에 포함하지 않는다. 전체 시험소의 실제 업무·물리 무인화는 후속 목표로 남는다.
