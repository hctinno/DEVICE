# 다음 가상 하네스 단위 — meter 주파수 충돌 복구 정책

2026-10-25 Asia/Seoul. DEV3-VIRTUAL-HARNESS-NEXT-CONTRACT-20261025-001의 private 독립 정적 Yes/C0I0M0 뒤 공개한 구현 계약이다. 총괄은 선택 B의 새 행동 정책·아래 신규3을 승인한다. 선행 d269는 독립 제품 Yes 뒤 통합038 기능23fbf981에 인수했다. 정확 게시 base·전용 branch·실제 배정 뒤 개발3이 구현하며, 후보/owner test를 읽기 전 독립 기대 봉인을 선행한다. 이 후속 제품 import/API/fixture/DB/RF 실행·원 bundle/summary/capture 접근은0이다. [구현 계획](../plans/2026-10-25-virtual-fleet-meter-frequency-recovery-policy.md)을 따른다.

## 확인한 공백과 두 접근

| 접근 | 현재 근거와 실제 선행조건 | 판단 |
| --- | --- | --- |
| A. burst I/Q를 sensor/meter 취득 시간창에 결합 | 054는 CW/사각 pulse의 ZOH 격자 계산이고 RF engine은 scalar duty/crest와 논리 tick을 사용한다. 원점/phase·표본과 aperture 대응·기준면/경로 변환·취득 kernel을 먼저 정의해야 한다. RF engine 변경은048 engine20/source4 고정 판본과 기존 저장조회 호환 검토까지 넓어진다. 실제 장비 등가성에는 별도 자료/대조가 필요하다. | 실제 공백이지만 이번 최소 단위로 선택하지 않는다. N/Fs를 RF tick/window에 대응시키지 않는다. |
| B. meter 설정 충돌을 관측해 허용된 주파수 수정 후 같은 run에서 sensor→meter 새 취득 | 기존 instruments는 sensor_frequency_setting_conflict를 발생시키고 configure 시 configuration_revision/전역 setup_revision을 바꾸며 cached/pending 측정을 무효화한다. 그러나041 _MeterPolicy는 invalid/error 등을 만나면 blocked로 끝난다. 기존 RFSensorFixturePolicy의 복구는 sensor 중심이고 이 meter 수정·양쪽 재취득을 제안하지 않는다. 공개 context/설정·역할 동작과 명시 위임으로 구성할 수 있다. | 선택. 기존 장비 동작을 새 행동 정책으로 연결한다. |

reader/hash/DTO 검사나 CLI를 새로 포장하지 않는다. 핵심 새 행동은 **현재 관측의 주파수 충돌 → 제한된 configure → 무효화 관측 → 새 sensor acquire/read → 새 meter acquire/fetch → 최신 관측의 완료 주장**이다. 기존 scalar 엔진의 수치가 맞는다는 것만으로 이 행동 순서가 이미 검증됐다고 보지 않는다.

## 최소 소유와 공개 API 후보

승인 신규3은 labflow/virtual_fleet/meter_frequency_recovery_policy.py, tests/test_virtual_fleet_meter_frequency_recovery_policy.py, docs/fcc/virtual_fleet_meter_frequency_recovery_policy_usage.md다. 기존 policies/harness/core/rf/instruments/041/048/054/055/reader/journal·DB/CLI/UI를 수정하지 않는다. 새 registry/provider/평가 framework·시나리오 writer도 만들지 않는다.

공개 API는 `RFMeterFrequencyRecoveryPolicy()`와 그 callable `policy(context) -> proposal` 한 종류다. 생성자에 seed/author/정답/복구 일정·runtime을 받지 않는다. policy_id는 rf_meter_frequency_recovery_v1이며 기존 report.policy.kind=fixture다. 한 run에 한 instance를 사용한다.

입력은 기존 context8(schema_version/goal/catalog/topology/role_actions/observations/last_receipt/remaining_budget)이다. 공개 goal exact6은 다음과 같다.

- kind=acquire_fresh_rf_sensor_meter
- 서로 다른 dut_id/sensor_id/meter_id
- minimum_acquisition_tick: plain 비음수 int
- allow_meter_frequency_reconfigure: 명시 plain bool

출력은 기존 execute4/advance2/stop3 proposal만 사용한다. 허용 동작은 DUT start, sensor acquire/read, meter acquire/fetch, meter configure의 frequency_hz 단 한 파라미터, advance(ticks=1), stop이다. policy는 직접 runtime·장비·파일·모델을 호출하지 않고 tick/UUID/요청 ID를 만들지 않는다.

## 지원 범위와 선행조건

같은 살아있는 virtual runtime·그 원래 요청 ledger, synthetic=true/hardware_verified=false 관측, DUT→RF 경로→sensor→meter 결합을 요구한다. catalog/profile/role/action 선언과 노드 identity가 일치해야 한다. meter의 보이는 configuration은 on_average/dBm/window1/immediate trigger만 이번에 지원한다. 주파수 외 설정은 변경하지 않는다. calibration 실패를 설정 충돌로 해석하거나 검증/교정·reset/recover를 자동 실행하지 않는다.

후속 실행에서 현재 catalog의 선택 profile·범위/latency·주파수별 경로 loss_table과 meter noise/bias를 먼저 고정한다. 아래 고정 숫자 예시는 해당 주파수의 손실이 선언값과 같고 noise_db=0/gain_error_db=0인 합성 조건에서만 사용한다. 미확인 profile에 무잡음이나 일정 손실을 가정하지 않는다. 기존 전도 예제의 bootstrap 완료 뒤 caller가 선언한 DUT 출력·sensor triggered·meter initial frequency를 시험 시작 전에 준비하고, bootstrap의 옛 측정을 새 측정으로 쓰지 않는다. sensor에는 frequency configure를 보내지 않는다. caller가 initial snapshot 이후의 최소 tick과 위임을 goal에 명시한다. 이번 준비에서는 이 setup/fixture를 만들거나 호출하지 않는다.

## 정책 상태와 제어

| 단계 | 요구 관측과 다음 제안 |
| --- | --- |
| sensor_before | 공개 RFSensorFixturePolicy를 exact4의 파생 sensor goal로 호출한다. 새 acquire/read와 유효 최신 관측까지 기존 정책을 따른다. top goal6과 원 context는 수정하지 않는다. |
| meter_before | meter acquire를 제안한다. pending은 advance1, 유효 결과는 fetch와 최신 관측을 확인한다. 현재 meter 설정이 sensor 주파수의1Hz 이내인 기존 장비 허용 범위이고 유효 취득이 되면 configure0으로 완료할 수 있다. 수정 target은 관측 주파수의 정확 사본이다. |
| conflict | 본 정책이 새 meter.acquire를 제안한 뒤 다음 flat receipt의 해당 meter invalid와 현재 관측의 sensor_frequency_setting_conflict가 일치할 때만 수정 후보가 된다. bootstrap의 cached reason만으로 수정하지 않는다. 현재 sensor도 유효해야 한다. allow=false는 blocked, true는 관측 sensor.frequency_hz를 그대로 meter.configure에 제안한다. 수정 시도는 반환 전에 기록한다. |
| configure_receipt | 직전 자기 제안과 flat receipt·현재 meter configuration을 대조한다. 주파수만 변경, configuration_revision 증가, 전역 revision 증가를 확인한다. ACK는 측정 완료가 아니다. missing/불명 응답은 새 configure로 재시도하지 않는다. |
| sensor_after | 옛 sensor/meter signature를 버린다. 동일 runtime에서 새 sensor 정책 instance와 파생 minimum_tick=max(원 최소 tick, configure receipt.tick+1)로 새 acquire/read를 요구한다. 이 reset은 runtime 재생성/재개가 아니다. |
| meter_after | sensor가 새 revision에서 취득된 뒤 새 meter acquire/대기/fetch를 요구한다. configuration_revision·acquisition_setup_revision·source_id/input_source_id·unit/quantity/frequency/window·simulation_basis를 현재 관측과 결합한다. 이번 on_average/dBm 합성 범위에서는 meter.value와 새 sensor.power_dbm이 절대1e-9dB 이내로 일치해야 한다. 이는 독립 절대 정답과 별도의 공개 값 상호대조이며 duty/crest를 재적용하지 않는다. |
| terminal | fresh sensor와 meter, 자기 제안 이후의 취득, 후속 fetch 응답과 같은 최신 signature가 있어야 completed다. 종료 후 추가 configure/장비 동작을 제안하지 않는다. |

last_receipt는 status/values/tick/setup_revision/device/profile/role 등의 **flat envelope**다. action/request_id 필드를 만들어 읽지 않는다. 정책은 자기 제안 phase를 기억하고, 실제 intent/request ID/action 결합은 기존 하네스·journal과 독립 수용 검토에서 확인한다. 현재 설정 위치는 values.configuration과 values.configuration_revision이다.

top goal/catalog/topology/role_actions의 binding은 run 중 고정하고 clock은 비감소여야 한다. caller의 위임 변경·identity/설정/취득 모순을 조용히 수용하지 않는다. 수정 target과 다른 주파수가 새로 나타나면 재튜닝 루프로 가지 않는다. configure 최대1은 논리 intent 수다. 응답 유실의 동일 runtime/동일 ID/body 전송 재시도는 기존 하네스만 담당한다.

## 상태·오류와 한도

새 공개 예외/DTO를 추가하지 않는다. known 잘못된 JSON/clock/binding/receipt/측정은 stop(failed, invalid_public_context 또는 meter_context_changed), 지원하지 않는 role/action/설정은 unsupported, 수정 위임 부재·설정 실패·다른 meter 오류는 blocked다. 제안 이유는 고정 공개 문자열로 제한하고 raw exception/hidden fault/경로를 출력하지 않는다. 정상 외 BaseException은 기존 하네스의 policy_error 경계로 전달하며 성공으로 바꾸지 않는다.

부모 sensor 정책의 지속 단절 대기 등은 기존 decisions64/requests64/ticks32/wall30s/transport retries2의 유한 한도에 맡긴다. known invalid 응답을 전송 재시도로 바꾸지 않는다. unresolved/timeout/budget 종료를 completed로 쓰지 않는다. fixture 종료는 RF/전원/물리 정리 확인이 아니며 cleanup은 not_assessed다.

## 작업 전 고정할 독립 기대

아래는 **새 합성 기대 제안**이며 실행·독립 봉인 완료가 아니다. 원 bundle/summary/capture나 기존 owner oracle를 읽어 정답으로 쓰지 않는다. 총괄이 구현/owner test를 보기 전 독립 reviewer에게 metadata 지원 범위의 다른 입력·기대를 먼저 봉인하게 해야 한다.

예시 declared case는 DUT10.0dBm, 기존 attenuator10dB/switch0.5dB/coupled path20dB, sensor2.45GHz와 meter2.46GHz다. 새 on_average 기대는 sensor/meter 모두 -20.5dBm(절대1e-9dB 이내)이며, duty를 다시 곱하거나 crest를 더하지 않는다. 이는 authored scalar 정책의 산술이고 실측/표준 PHY·교정 정답이 아니다. profile 지원 확인이 안 되면 이 입력을 검증된 조건으로 표시하지 않는다.

수치가 맞더라도 다음 독립 이벤트 조건이 없으면 수용 실패다.

- 충돌에서 measurement가 비어 있고 위임true이면 configure 논리1회, false이면0회다. actor가 하네스 밖에서 복구 명령을 실행하면 실패다.
- 주파수 외 configuration은 같다. 전역 setup revision과 meter configuration revision을 구별한다. 이후 DUT start 등으로 전역 revision이 더 바뀌면 최종 공통 최신 revision을 기준으로 검증한다.
- 수정 뒤 새 sensor acquire/read, 그 sensor 취득보다 늦은 새 meter acquire/measurement/fetch가 같은 run/instance와 새 논리 request로 결합된다. 설정 ACK만으로 완료할 수 없다.
- meter acquisition tick은 자기 acquire intent tick과 사용 sensor 취득 tick보다 늦고, acquisition_setup_revision은 최종 관측 revision, configuration_revision은 현재 meter 설정 revision이다.
- 같은 수치의 옛 revision/다른 source·unit·configuration, missing fetch, 위임 변경, 교정 불가·계속 단절·configure 실패는 완료가 아니다.

## 검증과 파이프라인 접점

신규 테스트는 독립 기대를 먼저 봉인한 뒤 정책 제안을 기존 FleetHarness와 새 합성 bench에서 실제 가상 실행하여 검증한다. policy가 configure/acquire/fetch를 제안하도록 해야 하며 host가 그 순서를 대신 실행해 성공시키지 않는다. normal/복구/위임없음/설정실패·stale/예산·응답유실을 분리한다. 지금은 모든 실행0이다.

기존 report15/context8/journal event8·7종 형식을 유지한다. 기존 sensor evaluator는 meter 복구를 평가하지 않고041 evaluator는 원 고정 policy/scenario 전제라 이 새 goal의 승인 수단으로 쓰지 않는다. 이번 단위의 수용 증거는 독립 기대와 event trace 대조이며 report의 policy completed와 assessment/task_outcome/cleanup not_assessed를 구별한다. 새 runtime 평가 서비스는 이번에 만들지 않는다.

새 policy source는 기존 engine20 hash에 포함되지 않는다. caller의 private 실행 영수증에 그 policy source pin을 별도로 고정하고, 기존 engine hash가 새 정책까지 인증한다고 표시하지 않는다.

[현재 정책](../../../labflow/virtual_fleet/policies.py) · [현재041 meter 정책](../../../labflow/virtual_fleet/rf_signal_scenario.py) · [장비 동작](../../../labflow/virtual_fleet/instruments.py) · [하네스](../../../labflow/virtual_fleet/harness.py) · [로드맵](../../fcc/wifi24_delivery_roadmap.md) · [후속 계획](../plans/2026-10-25-virtual-fleet-meter-frequency-recovery-policy.md)을 따른다.

의뢰/방법 준비 → 가상 DUT/장비 셋업 → 공개 관측 기반 하네스 행동 → 실패 관측/제한 설정 수정/새 취득 → journal·독립 수용 → 원시 데이터/성적서/AI 리뷰의 접점이다. 의뢰 큐·모델 운영·durable 재시작·최종 운영 평가/성적서 연결, burst 공통 시간창·불확도/보정/방법 승인·실제AI·현장/물리 작업 무인화는 남는다. 전체 시험소 목표를 이 fixture policy 완료로 축소하지 않는다.

추가 원문은 이 합성 행동 계약의 현재 선행조건이 아니다. 실장비 연결로 확장할 때 필요한 모델/FW별 configure 의미·범위/settling·취득/trigger·교정·실측 자료는 이번에 확인하지 않았다. 총괄이 이미 인수한 source metadata를 먼저 대조하고 실제 누락만 P01 창구로 요청한다. 개발3은 수집/P01/다른 담당에 직접 연락하지 않는다.
