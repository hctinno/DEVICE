# 가상 meter 주파수 복구의 별도 근거 평가

2026-10-25, Asia/Seoul. [설계](../superpowers/specs/2026-10-25-virtual-fleet-meter-recovery-assessment-design.md)·[계획](../superpowers/plans/2026-10-25-virtual-fleet-meter-recovery-assessment.md)의 순수 메모리 API다. [복구 정책](virtual_fleet_meter_frequency_recovery_policy_usage.md)이 기록한 행동과 새 취득을 제공 합성 선언에 대조한다. 원 report의 assessment/task_outcome/cleanup을 덮어쓰지 않는다.

```python
from labflow.virtual_fleet.meter_recovery_assessment import (
    MeterRecoveryAssessmentError, assess_meter_frequency_recovery,
)
```

`assess_meter_frequency_recovery(report, events, *, declaration)`는 별도 dict 하나를 반환한다. 파일/DB/reader/runtime/policy/기존 evaluator·RF helper/clock/RNG/모델을 호출하지 않는다. 정확 native JSON만 분리 복사하고 declaration/report/events의 canonical SHA를 결합한다. 원 파일 bytes·보관 진위나 실제 위임을 검증하는 API가 아니다.

## 입력 준비와 직접 호출

report는 기존 FleetHarness의 exact15, events는 operator_event exact8/7종 배열이다. caller는 기존 `harness.result()`/`harness.events()` 또는 기존 공개 `read_operator_journal`의 events를 함수 밖에서 준비한다. 저장 조회 summary나 historical assessment를 raw events 대신 넣지 않는다.

declaration exact8은 schema_version=1, kind=meter_frequency_recovery_declaration, goal, catalog, topology, role_actions, budgets, rf_basis다. goal은 기존 recovery exact6이며 위임 bool이 필수다. budgets exact5는 decisions/logical_requests/ticks/wall_seconds/transport_retries를 모두 명시한다. 생략한 값을 이 API가 채우지 않는다.

rf_basis exact6은 simulation_basis=declared_synthetic_policy, source_signal, path, meter_noise_db, meter_gain_error_db, external_runtime_mutations다. source_signal의 ON 평균 power와 명시한 상수 손실 경로에서 독립 산술을 수행한다. path는 device_id/input_port/output_port/loss_db 순서 배열이다. v1 지원은 attenuator·rf_switch·coupler의 단일 scalar 경로, on_average/dBm/window1/immediate, noise/bias0, 외부 mutation 없음의 선언 범위다. 동적 표·다른 모드·미확인 데이터를 상수나 0으로 채우지 않는다.

다음 예제의 `folder`는 caller가 이미 확보한 합성 `report.json`, `events.json`, `declaration.json` 폴더의 Path 값이다. 파일 읽기는 평가 함수 밖에서 한다. 세 입력에는 복구 run의 원 report/events와 그때의 선언을 제공한다.

```python
from pathlib import Path
import json
from labflow.virtual_fleet.meter_recovery_assessment import assess_meter_frequency_recovery

packet = {
    name: json.loads((folder / (name + ".json")).read_text(encoding="utf-8"))
    for name in ("report", "events", "declaration")
}
result = assess_meter_frequency_recovery(
    packet["report"], packet["events"], declaration=packet["declaration"]
)
assert packet["report"]["assessment"]["status"] == "not_assessed"
assert packet["report"]["task_outcome"] == "not_assessed"
assert packet["report"]["cleanup"]["status"] == "not_assessed"
assert result["verification"]["input_values_unchanged"] is True
assert result["verification"]["model_quality_verified"] is False
print(result["status"], result["verdict"], result["observed_goal"])
```

새 API는 action/request ID를 생성하지 않는다. execute receipt는 해당 node의 device_id/profile_id/role·plain bool setup_changed를 결합한다. advance receipt는 실제 global6/status ok/advanced_ticks plain int1/tick+1/비역행 revision이다. advance에 node identity나 가상의 setup_changed를 추가하지 않는다. public core output의 source_id는 **device ID**이며 profile ID는 node의 별도 필드다.

event_id는 공개 journal의 유효 ASCII 식별자이며 `event:N` 접두를 강제하지 않는다. sequence 1..N·ID 고유성·동일 run/runtime과 모든 report 참조 결합은 유지한다. ID를 바꾼 자료는 report의 해당 참조도 같은 전단사 관계로 바꿔야 한다. meter.fetch는 빈 parameters 또는 현재 지원 설정과 같은 `{"window": 1}`을 받는다. window는 plain int여야 하며 bool·다른 창·다른 parameter/action·sample 불일치를 새 권한이나 지원으로 인정하지 않는다.

## 판정과 한계

| 결과 | 의미 |
|---|---|
| assessed / pass / satisfied | 새 sensor acquire/read와 새 meter acquire/fetch, 현재 source/revision/tick/window/unit 및 선언 경로 산술을 모두 확인 |
| assessed / pass / not_satisfied | 실제 충돌과 위임 false의 차단 또는 관측된 준비 불가/설정 거절에 맞는 제한 종료. 목표 측정 완료가 아님 |
| assessed / fail | 위임 밖 configure·논리2회·다른 parameter/action·설정 변동·stale/다른 source·관측/보고 모순·산술 오답 등 확인된 위반 |
| assessed / inconclusive | 올바른 prefix·누락·미결/불명 실행·budget stop·wall time 미검증·미지원 수치 모델. PASS로 보완하지 않음 |
| unsupported / null | 다른 goal/policy/최초 meter 모드·외부 mutation 선언 또는 이미 평가된 report. 새 권한/지원으로 해석하지 않음 |

판정 우선순위는 fail > inconclusive > pass다. sensor/meter가 같은 오답이어도 선언 source ON power에서 선택 손실을 뺀 값과 다르면 fail이다. on_average에 duty/crest를 다시 적용하거나 coupler의 through 손실을 coupled 분기에 더하지 않는다. 허용오차는 절대 1e-9dB다.

설정 응답 `pending`과 같은 pending cause에서 설정이 그대로인 blocked 종료는 known rejection이 아니다. `inconclusive / unverified`로 남기며, completed claim과 미결 설정이 함께 있으면 fail이다. invalid/unsupported/error/disconnected의 알려진 실패는 receipt와 cause의 status·reason 및 설정/configuration revision 불변이 맞고 blocked로 끝났을 때에만 종전의 조건부 pass/not_satisfied가 가능하다. 새 logical configure 재시도는 허용하지 않는다.

기록된 `elapsed_ms > wall_seconds * 1000`은 `fail / budget_violation`이다. 예를 들어 선언 2.5초에 기록 2500.25ms는 초과다. 정확 경계 2500ms와 적법한 wall_deadline 종료는 실제 시계를 확인하지 못한 inconclusive로 구별한다. 한도 미만의 기록이나 종료 이유만으로 실제 시간 준수를 검증했다고 표시하지 않는다.

`observed_goal`은 verdict와 별도다. 완전·지원되는 최종 기록에서 값이 독립 산술과 확실히 다르거나 취득 revision이 실제로 오래됐음이 입증되면 fail/not_satisfied가 가능하다. prefix·pending 또는 run/runtime/event 결합 모순으로 동일 실행의 근거가 성립하지 않거나 수치를 확인할 수 없으면 unverified다. 이 예시는 모든 source/unit/window/stale 조합의 reason-to-goal 매핑을 열거한 표가 아니다. 개별 문구의 해석 차이 때문에 이미 확인한 fail을 완화하거나 모든 측정 실패를 일괄 unverified로 바꾸지 않는다.

결과 exact15에는 checks7/counts10, declaration/report/events/전체 입력 SHA와 run/runtime ID, 고정 reason_codes, 실제 event refs와 최초 error/실패 receipt refs가 있다. configure logical intent와 transport retry marker를 구별하며 실제 dispatch 횟수를 입증했다고 표시하지 않는다. 원 실패 receipt는 성공 후에도 참조로 남는다.

위임·실행 전 RF 설정·무잡음/무bias·숨은 mutation 부재는 caller 선언이다. 같은 ID/hash는 실제 runtime/요청 ledger·원 파일/보관 진위를 증명하지 않는다. elapsed_ms는 실제 wall clock의 독립 증명이 아니다. 결과 verification의 실제 위임/사전 설정/숨은 fault·보관/runtime 진위·AI 품질·physical cleanup·현행 source 권한 flag는 false다. AI 모델 호출이나 종합점수는 이 평가로 만들지 않는다.

## 오류와 자원 한도

`MeterRecoveryAssessmentError.code/str/args`는 `meter_recovery_assessment_invalid_input`, `meter_recovery_assessment_limit_exceeded`, `meter_recovery_assessment_internal_error` 중 고정 문자열 하나다. 원 입력·예외를 넣지 않고 활성 caller except 안에서도 context/cause를 None으로 정리한다. KeyboardInterrupt/SystemExit/GeneratorExit는 그대로 전파한다.

전체 입력 32MiB, 출력 128KiB, event4096/각512KiB, depth32/node200000/path16, signed64 정수 한도를 적용한다. subclass/cycle·surrogate/NaN·bool을 숫자로 쓰는 입력은 거절한다. native/필수 형상 오류와 관측 모순·근거 부족을 구별한다.

작성자 검증은 별도 owner 입력·변이/동등 입력·자원·예외 검사와 새 합성 metadata의 실제 가상 normal/configure0, recovery/configure1, denied/configure0 각1회다. 원 report/events는 보존하고 별도 평가를 호출했다. 이는 독립 reviewer의 사전 봉인/후행 평가와 구별한다. 실제 계측 정확도·교정·불확도·규범·실물/물리 정리·전체 시험소 무인화 및 AI 품질의 증거는 아니다.
