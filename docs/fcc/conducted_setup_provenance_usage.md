# 실제 conducted setup 호출 근거

2026-10-26 Asia/Seoul. 수용된 [선언 source factory](plan_driven_conducted_twin_usage.md)와 [SensorTrial](plan_driven_sensor_trial_usage.md)에 선택 기록만 추가한다. 실제 가상 호출을 기록하며 새 bench·측정·보정값을 생성하지 않는다.

## API와 범위

- create_conducted_example(catalog, *, seed=0, source_settings=None, setup_records=None)
- prepare_sensor_trial(catalog, *, condition="normal", seed=0, power_dbm=12.5, source_settings=None, setup_records=None)
- SensorTrial(catalog, *, condition, seed, power_dbm, source_settings=None, setup_records=None)
- trial.setup_snapshot() -> 새 native list

setup_records는 None 또는 native 빈 list만 받는다. list subclass·비어 있지 않은 list·다른 타입은 factory 초기화/가상 명령 전에 ValueError로 거절한다. None은 미기록이며 기존 factory 반환 tuple·원 receipts·source None recipe·SensorTrial 관측/goal/author/evaluator 계약을 유지한다. 미기록 snapshot의 빈 list는 실제 setup이 없었다는 뜻이 아니다.

MAX_SETUP_RECORDS는 32다. 현재 factory는 실제 command/advance 23개, SensorTrial은 같은 factory 23개와 후속 DUT configure·sensor configure·DUT stop 3개를 합쳐 26개를 기록한다. 새로운 호출 전 cap을 확인한다. 최대값을 넘는 호출을 실행한 뒤 조용히 누락하지 않는다.

## 실제 call 경계의 record

각 record는 정확히 request_id, operation, device_id, action, parameters, receipt, tick, setup_revision 필드다. execute는 실제 device/action 및 전달한 parameters를 분리 복사한다. advance는 device_id/action이 null이고 parameters는 실제 ticks 인자를 담은 {"ticks": n}이다. 원래 execute parameters가 None이면 null을 보존한다. request_id는 실제 호출 ID와 같다.

호출 직전에 parameter snapshot과 receipt/tick/setup_revision=null인 항목을 기록하고, 반환되면 원 receipt를 분리 복사하며 그 receipt의 tick/setup_revision을 기록한다. 반환 receipt의 실패 status도 보존한다. 호출 자체가 예외를 내면 해당 항목의 receipt와 시점은 null이며 성공·무실행·0으로 추정하지 않는다. 이전 항목과 부분 실패 기록을 지우거나 rollback하지 않는다. 기존 오류와 초기화 실패를 성공으로 바꾸지 않는다.

factory 반환 receipts와 collector record는 서로 alias하지 않는다. SensorTrial은 제공 collector와 별도의 snapshot을 보존하고 setup_snapshot() 호출마다 새 복사본을 돌려준다. caller catalog/source/parameters는 수정하지 않는다.

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.evaluation import prepare_sensor_trial

catalog = load_catalog("virtual_profiles/sm_a176u_unlicensed.json")
source = {
    "frequency_hz": 2.412e9, "power_dbm": 11.0,
    "bandwidth_hz": 20e6, "duty_cycle": 0.5,
    "modulation": "OFDM", "crest_factor_db": 4.0,
}
records = []
trial = prepare_sensor_trial(
    catalog, power_dbm=source["power_dbm"],
    source_settings=source, setup_records=records,
)
setup = trial.setup_snapshot()
```

## 경로와 보정의 의미

record는 실제 DUT·attenuator·switch·coupler의 configure 인자와 반환 결과의 근거다. 측정값이나 private expected 값, 인접 power 차이, 고정 손실 합계에서 설정을 역추정하지 않는다. coupler through와 coupled 분기의 설정은 원 인자 그대로 구별한다.

전파 경로에서 loss가 이미 RF packet에 적용된 사실과, sensor_input의 값을 source_output 기준면으로 환산하는 역보상은 별개다. 이 단위는 역보상·계측기 보정·합계·결과를 계산하지 않는다. 이후 결과 연결은 같은 runtime/관측/시점/setup revision 및 각 보정의 출처·기준면·이미 적용 여부를 대조해야 한다. configure의 calibration_valid는 합성 선언이며 실제 교정 증명이나 규범 승인이 아니다.

getter는 host의 실제 설정 근거이며 author_record의 expected/seed/condition/fault schedule/oracle을 포함하지 않는다. policy context·goal·관측 DTO·public/private evaluator에 자동 주입하지 않는다. setup 후 runtime 행동과 author 단선/해제 기록은 이 고정 setup snapshot의 범위 밖이다.

## 검증 상태

소유 integration은 기존16+신규7=23/23, evaluation은 기존28+신규5=33/33을 각각 통과했다. 별도 RF41·instruments42·core22·harness39·method_adapter25·journal25=194/194 회귀는 합산하지 않는다. failure/error/skip은 모두0이다. 신규12논리의 RED는 missing keyword로 발생한 실패28항목(하위사례 포함)/error0이며 원 로그를 보존한다. 로컬 HTTP 회귀의 loopback 접속4와 실제 외부망·장비0을 구별한다. 총괄 독립 검토는 별도다. 실제 장비·Wi-Fi waveform/peak 규범·교정·불확도·기관 적합성은 미검증/not_assessed이며 새 규범 한계나 장비 권한은 추가하지 않는다. P01 reported_peak/null 근거를 다른 수치로 변환하지 않는다. 실제 AI provider·모델 인증·고객 원본·실장비 호출은 0이며 기존 Codex16/Vertex6/3072·무료크레딧전용 상태는 바꾸지 않는다.
