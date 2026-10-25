# 단일 가상행동의 관측 효과 평가

2026-10-25, Asia/Seoul. DGM AutoLab.

제공된 단일 행동 기록의 결합, 관측 변화, 명령 결과를 메모리에서 평가한다. 정상 pending·거절·자료 부족을 구별하며, 스마트폰 시험이나 sensor 과업의 성공 점수는 계산하지 않는다. [설계와 기계 계약](../superpowers/specs/2026-10-25-codex-one-action-effect-assessment-design.md), [구현 계획](../superpowers/plans/2026-10-25-codex-one-action-effect-assessment.md), [공개 구현](../../labflow/virtual_fleet/codex_one_action_assessment.py), [소유 검사](../../tests/test_virtual_fleet_codex_one_action_assessment.py)를 함께 따른다.

## 공개 API

```python
from labflow.virtual_fleet.codex_one_action_assessment import (
    assess_codex_one_action_effects,
    CodexOneActionAssessmentError,
)

def assess_codex_one_action_effects(
    packet: dict, *, caller_error_code: str | None = None,
) -> dict:
    ...
```

공개 export는 함수와 오류 클래스 정확히 두 개다. 파일·경로·reader·clock·runtime·factory·provider·원 예외를 인자로 받지 않는다. 호출자가 자신의 권한으로 확보한 원 native 값을 제공한다. 함수는 파일을 탐색하거나 읽고 쓰지 않으며 장비·가상 runtime·Store·DB·모델을 호출하지 않는다.

## 입력 packet9

native dict의 다음 key 아홉 개가 모두 있어야 한다. 각 `None`은 명시적인 자료 미제공이다. 누락 key와 알 수 없는 key는 형상 오류다.

| key | 제공 값 |
| --- | --- |
| host_result | [원 단일 행동 host](virtual_fleet_codex_virtual_one_action_usage.md)의 exact12 dict 또는 None |
| context8 | remaining_budget을 포함한 원 공개 context8 또는 None |
| prompt | 원 genuine prompt exact5 또는 None |
| response_bytes | 원 응답 native bytes 또는 None; bytes는 이 필드에서만 허용 |
| harness_report | 원 legacy report exact15 또는 None |
| harness_events | 원 operator_event exact8의 native list 또는 None |
| before | 원 full64 공개 관측 exact5 또는 None |
| after | 원 full64 공개 관측 exact5 또는 None |
| dispatch_receipt | 원 node/global receipt 또는 None |

예를 들어 receipt가 없는 사전 거절은 다음처럼 전달한다.

```python
packet = dict(
    host_result=None, context8=None, prompt=None, response_bytes=None,
    harness_report=None, harness_events=None, before=None, after=None,
    dispatch_receipt=None,
)
assessment = assess_codex_one_action_effects(
    packet, caller_error_code='operator_virtual_one_action_delegation_denied',
)
assert assessment['status'] == 'inconclusive'
assert assessment['command_outcome'] == 'unknown'
assert assessment['first_error'] == dict(
    code='operator_virtual_one_action_delegation_denied', stage=None, source='caller',
)
assert assessment['task_assessment']['score'] is None
```

caller_error_code는 None 또는 확정 부모 host12·producer11·boundary8 원 full code 중 하나다. 임의 예외의 메시지·repr·traceback은 허용하지 않는다. host.failure가 있으면 원 code/stage/source=host_result를 유지한다. 다른 caller code를 제공하면 원 오류를 교체하지 않고 모순을 기록한다. 정리 secondary_errors도 최초 오류와 구별한다.

native subclass, cycle, NaN/Infinity, surrogate, 숫자 필드의 bool, 잘못된 타입은 거절한다. bool을 0/1로 변환하거나 빠진 count·after를 채우지 않는다. 이벤트 ID는 제한된 ASCII 문자열과 고유성·sequence·참조 결합을 검사하며 event:N 접두를 요구하지 않는다.

## 결과의 의미

top exact14는 schema_version, kind, status, verdict, bindings, observed_effect, command_outcome, first_error, task_assessment, checks, evidence_refs, verification, reason_codes, limits다. schema_version=1, kind=codex_one_action_effect_assessment다.

| 제공 근거 | status / verdict | effect / command |
| --- | --- | --- |
| 같은 실행의 허용 단일 intent·receipt·causal after, status ok | assessed / consistent | changed 또는 unchanged / accepted |
| 같은 근거, status pending | assessed / consistent | changed 또는 unchanged / pending |
| 같은 근거, invalid·unsupported·error·disconnected | assessed / consistent 가능 | changed 또는 unchanged / rejected |
| 유효 stop와 맞는 terminal, intent0 | assessed / consistent | not_applicable / not_dispatched |
| 원 host·source·decoder 최초 오류와 complete terminal, intent0 | assessed / consistent 가능 | not_applicable / not_dispatched |
| after·receipt·events 누락, prefix, unresolved, caller-only 거절 | inconclusive / insufficient | unknown / unknown |
| 같은 protocol의 확인된 ID·hash·action·count·clock 모순 | assessed / contradictory | unknown / unknown |
| 다른 host·goal·policy, 변환되거나 이미 평가된 legacy | unsupported / null | unknown / unknown |

같은 protocol에서는 확인된 모순이 자료 부족보다 우선한다. unchanged 자체를 실패로 취급하지 않는다. 거절 receipt가 diagnostic 변화와 연결되면 changed일 수 있다. revision이 매번 +1이어야 한다고 가정하지 않으며, execute의 tick 유지·advance1의 tick+1·revision 비역행을 대조한다. pending은 설정·취득 완료를 의미하지 않는다. completed stop claim도 과업 완료 증거가 아니다.

checks exact6은 input_binding, wire_scope, same_run_evidence, single_action, effect_receipt, error_and_cleanup이며 각각 supported·contradicted·unverified다. supported는 해당 경로의 제공 근거가 맞는다는 의미다. 원 wire를 수용하지 않은 거절 경로가 일치해도 supported일 수 있으며 새 모델 성공을 뜻하지 않는다.

evidence_refs는 실제 제공 event ID 또는 고정 component:<key> 최대32개다. 원 예외나 경로를 반환하지 않는다. reason_codes는 설계 §9의 닫힌20개 후보에서 최대32개만 반환한다.

## 원 wire·legacy·과업 평가 보존

host의 원 wire_accepted=true 또는 원 step.wire가 있고 prompt와 response가 모두 제공된 경우에만 공개 [strict decoder](../../labflow/virtual_fleet/model_operator_boundary.py)를 재사용한다. genuine decoded wire, 원 host wire, policy_decision, 허용 DUT.start/sensor.acquire/read/advance1/stop를 대조한다. 원 source·decoder 실패에 decoder를 새로 적용해 수용 상태를 올리지 않는다.

원 host12, producer receipt18, wire5, legacy fixture·ai_model_called=false·not_assessed는 수정하지 않는다. task_assessment는 항상 다음 exact4다.

```json
{"status":"not_evaluated","verdict":null,"score":null,"evaluator_called":false}
```

evaluator_called는 기존 full task evaluator의 호출 여부다. [meter 과업 평가](virtual_fleet_meter_recovery_assessment_usage.md)는 다른 goal·policy·선언을 요구한다. 그 선언을 만들거나 goal을 바꾸어 호출하지 않는다. [sensor evaluator](../../labflow/virtual_fleet/evaluation.py)는 원 live trial과 full completed/fresh-measurement를 요구하므로 trial을 재구성하거나 호출하지 않는다. 두 과업 evaluator의 실제 호출은0이다.

## Hash와 확인 범위

bindings exact3은 operator_binding, input_sha256, components다. 원 binding6 또는 null을 보존한다. components는 packet9와 caller_error_code의 정확10 key이며, 각각 present/bytes/sha256 exact3다.

- None: false / 0 / null.
- response_bytes: 원 bytes의 크기와 SHA256. 빈 bytes는 true / 0 / SHA256(empty)로 None과 다르다.
- 그 밖의 제공 값: ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')의 UTF-8·BOM 없음·끝 LF 없는 canonical JSON 크기와 SHA256.
- input_sha256: canonical `{schema_version:1, kind:"codex_one_action_assessment_inputs", components:위 exact10}`의 SHA256.

원 입력을 전후 두 번 snapshot하여 component hash를 대조한다. 관측된 변경은 fixed internal_error다. 외부 동시 변경을 원자적으로 잠그거나 디스크 보관 진위를 검증하는 기능은 아니다. 결과는 분리 복사되어 입력 객체의 mutable 참조를 남기지 않는다.

verification exact10 중 input_values_unchanged와 supplied_graph_consistent는 관측한 bool이다. root_authority_verified, runtime_authenticity_verified, storage_integrity_verified, actual_wall_time_verified, model_quality_verified, hardware_verified, physical_cleanup_verified, task_goal_verified의 여덟 값은 항상 false다. UUID·hash가 맞는 재생 기록을 실제 fresh runtime으로 인증하지 않는다. artifact descriptor도 제공 값의 size/hash와 whole_file 범위만 대조하며 원 파일을 열지 않는다.

## 자원·오류·검증

| 데이터 처리 한도 | 값 |
| --- | --- |
| 전체 입력 / 출력 | 8MiB / 64KiB |
| host_result / prompt / report | 각256KiB |
| context8 / before / after | 각1MiB |
| response_bytes / dispatch_receipt | 각64KiB |
| events | 최대16개, 각512KiB, 총2MiB |
| native depth / nodes | 32 / 200000; alias도 다시 계산 |
| 정수 | -9223372036854775808 ~ 9223372036854775807 |

데이터 처리 한도는 모델·운영 예산이 아니다. 원 harness 1/1/1/30/0과 outer8/60/cleanup 여유6 선언을 대조하며 새 승인·예산·retry·reset·refund를 만들지 않는다.

CodexOneActionAssessmentError(ValueError)의 코드는 codex_one_action_assessment_invalid_input, codex_one_action_assessment_limit_exceeded, codex_one_action_assessment_internal_error 세 가지다. code·str·args에는 고정 code만 있고 cause/context=None이다. 관측한 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파한다. 함수가 소유하는 파일·runtime·process·worker·network 자원은 없다.

소유 검사는 새 genuine full64 가상 기록과 fake D2만 준비한 뒤 순수 메모리 호출을 검증한다. 원 RED·준비 오류·중간 실패는 별도 보존한다. 자료 준비의 가상 호출과 평가 호출은 분모를 분리한다. 관련 decoder·meter assessment·원 host 회귀와 scripts/check_artifacts.py는 소프트웨어·문서 검사이며, 실제 모델 품질·계측 정확도·현장 무인화·기관 적합성의 증거가 아니다. 실제 CLI·모델·계정 인증·ADC·운영 Store·실장비는 실행하지 않았다.
