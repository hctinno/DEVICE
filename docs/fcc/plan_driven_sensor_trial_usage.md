# Plan 입력을 SensorTrial 평가까지 연결

2026-10-25 Asia/Seoul. [선행 합성 bench](plan_driven_conducted_twin_usage.md)의 caller 선언 source를 [SensorTrial/평가](../../labflow/virtual_fleet/evaluation.py)에 전달한다. 이 단위는 합성 RF 상태·경로·후행 측정·평가 연결이며 실제 Wi-Fi 측정이나 예측 성능 검증이 아니다.

## API

```python
prepare_sensor_trial(
    catalog, *, condition="normal", seed=0, power_dbm=12.5,
    source_settings=None,
)
SensorTrial(
    catalog, *, condition, seed, power_dbm,
    source_settings=None,
)
```

prepare_sensor_trial의 기본 condition/seed/power_dbm 및 SensorTrial의 기존 필수 keyword는 그대로다. None이면 factory에는 기존 seed만 전달하고, 기존 bootstrap·2450 MHz/20 MHz/OFDM/duty0.25/crest3 추가 DUT setup과 power_dbm 적용을 보존한다. 관측·goal·evaluator ID rf_sensor_fixture_v1·private author_record의 기존 필드 계약을 바꾸지 않는다.

제공 source_settings는 선행 factory가 검증하는 native exact6 `frequency_hz,power_dbm,bandwidth_hz,duty_cycle,modulation,crest_factor_db`다. 같은 입력을 한 번 분리 보관해 factory와 후속 DUT configure에 전달한다. meter/analyzer 설정은 factory가 같은 주파수·BW를 받으며, 후속 setup에서 legacy 주파수·duty·crest를 다시 넣지 않는다. trial당 fleet/runtime은 하나다.

## power를 암묵 선택하지 않는 호출

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.evaluation import prepare_sensor_trial

catalog = load_catalog("virtual_profiles/sm_a176u_unlicensed.json")
s = {
    "frequency_hz": 2.412e9,
    "power_dbm": 11.0,
    "bandwidth_hz": 20e6,
    "duty_cycle": 0.5,
    "modulation": "OFDM",
    "crest_factor_db": 4.0,
}
trial = prepare_sensor_trial(
    catalog, power_dbm=s["power_dbm"], source_settings=s,
)
runtime, goal = trial.runtime, trial.goal
```

제공 source의 power_dbm와 기존 power_dbm 인자는 같은 native 유한 numeric 값이어야 한다. 11과 11.0은 같지만 bool·문자열·NaN·Inf·float 범위를 벗어난 정수는 인정하지 않는다. 11인 source만 제공하고 기존 인자를 생략해 기본12.5와 충돌하면 ValueError다. constructor와 prepare 경로 모두 factory·가상 명령 전에 이 충돌을 거절하며 한쪽 값을 조용히 선택하지 않는다.

wrapper는 power 일치·유한성·native 선언을 선검사하고, exact6 및 나머지 native/range 검증은 수용된 create_conducted_example에 재위임한다. 별도 수치 범위·규격 한계·장비·방법·승인값을 만들지 않는다. factory의 형식·기본 RF 범위 거절과 이후 장치/profile 거절의 부작용 범위는 선행 usage와 같다. 뒤늦은 profile 실패에서는 일부 가상 초기화가 이미 일어났을 수 있고 rollback/모든 오류의 전역 무부작용을 보장하지 않는다. 완료하지 못한 Trial/runtime은 반환하지 않는다. caller catalog/source dict는 수정하지 않는다.

## 후행 측정·freshness·평가

sensor의 기존 합성 경로 기준은 선언 power_dbm에서 attenuator10·switch0.5·coupling20 dB를 한 번씩 뺀 `power_dbm - 30.5`다. duty나 crest를 빼서 reported peak를 다른 양으로 변환하지 않는다. parent bench의 meter time_average와 sensor의 송신 중 명목 RF 패킷 전력은 구별한다.

제공 source는 private snapshot으로만 평가 기준을 묶는다. 실제 후행 sensor value/power_dbm·coupled power와 새 source의 frequency/duty/crest, coupled bandwidth/modulation metadata가 맞는지 검사한다. 제공 metadata의 bool을 숫자로 보정하지 않는다. 관측 값을 읽어 private 예상 기준을 갱신하거나 policy claim만으로 성공 처리하지 않는다. None에는 기존 legacy 측정 predicate를 유지한다.

setup 이후 최소 acquisition tick, 현재 setup revision과 acquisition receipt, 측정의 후행 freshness 검사는 그대로다. 이전 run의 cached 측정·old receipt·ACK만으로 완료할 수 없다. runtime 하나에서 기존 trigger/stop과 단선 schedule을 유지한다. persistent_disconnect는 bounded noncompletion으로만 확인하고, restored_disconnect는 start_tick+4 해제 뒤 새 start/acquire와 후행 측정이 필요하다. 해제만 됐거나 복구·재획득에 실패하면 정상 완료로 평가하지 않는다.

## public context와 private 자료

policy에는 기존 FleetHarness context만 전달한다. 기존 공개 remaining_budget를 포함한 context8을 이 작업에서 바꾸지 않는다. 별도 operator prompt 경계의 context7 투영과 혼동하지 않는다. source_settings snapshot·expected_sensor_dbm·condition·seed·author_events를 새 정답 payload로 policy/goal/context에 추가하지 않는다. 장치의 실제 합성 관측에 정상 RF metadata가 나타나는 것과 private oracle 전달은 다르다.

author_record는 계속 host/evaluator 전용이며 source6 필드를 새로 추가하지 않는다. 공개 goal과 runtime facade는 author_control을 제공하지 않는다. host는 caller 선언을 자체 근거로 보존하고 policy에 private Trial 객체나 author_record를 주지 않는다. 현재 public evidence grading 계약·evaluator ID·author 필드는 유지한다.

## 검증 분모와 한계

[소유 검사](../../tests/test_virtual_fleet_evaluation.py)는 기존20+신규8=28개다. 동일 detached 설정·factory1회/runtime1개, power 충돌의 양 API 선거절, 일치한 int/float와 factory 범위 재사용, None 관측/goal/저자자료 회귀, 입력 불변, power-경로식과 metadata의 실제 후행 평가, 정상/영구단선/해제 후 복구/복구실패, stale/변조 metadata 거절과 public/private 분리를 검증한다. 별도 harness/RF/instruments/core144 회귀와 root 독립 분모는 합산하지 않는다.

경로식과 고정 합성 기대를 확인하는 것은 결정론적 구현 일관성 검사다. 독립 실측 예측 성능, 실제 SM-A176U·Wi-Fi 지원/firmware/PHY·waveform·peak 규범·계측 정밀도·교정·불확도·규격 적합성을 입증하지 않는다.

P01 첫 packet의 reported_peak는 기준면/보정/규범/raw가 null인 상태다. 이를 generic on_average나 source power_dbm으로 변환·추정하지 않는다. 이 예시 수치는 caller가 만든 합성 선언이며 실제 원본·실측값을 공개하거나 모델에 송신하지 않는다. 해당 입력 근거는 총괄을 통해 후속 보완한다.

실제 모델·인증·장비·외부망·고객 원본 호출은0이다. Vertex 기존6/3072 소진·무료크레딧전용 상태를 조회·seed/reset/refund하지 않는다. 이 unit은 source 입력 연결과 합성 평가를 확장하며 전체 시험소·실물 운전·업무 완료 권한을 만들지 않는다.
