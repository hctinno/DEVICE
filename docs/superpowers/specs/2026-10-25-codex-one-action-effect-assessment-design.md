# Codex 단일 가상행동의 별도 근거 평가 설계

2026-10-25, Asia/Seoul. DGM AutoLab.

고정 pure-memory trace effect 평가 A안을 확정한다. 제공 기록의 일관성·관측 효과·명령 결과를 평가하며 기존 full sensor/meter 과업 evaluator는 호출하지 않는다. 입력 packet9·반환 output14와 native/enum/nullable/size 규칙은 아래 기계 계약까지 같은 의미로 적용한다. 이 문서 게시가 제품 구현·실제 CLI·모델·인증·운영 예산·장비 실행 GO를 부여하지 않는다. [구현 계획](../plans/2026-10-25-codex-one-action-effect-assessment.md)을 함께 따른다.

## 1. 목적과 평가 경계

단일 행동의 허용 제안, 같은 run/runtime의 before/after, intent/receipt/causal observation과 최초 오류를 대조한다. 명령 ok/pending·실행 거절·후속 근거 부족을 분리하고 goal 문장·completed claim·host observed label만으로 과업 성공을 판정하지 않는다.

원 host exact12/producer18/wire5/legacy fixture·ai_model_called=false와 정책은 변경하지 않는다. 기존 단일 행동의 task evaluator0/score null을 소급해 평가완료로 바꾸지 않는다. 새 반환은 별도의 effect assessment이며 task status=not_evaluated/verdict=null/score=null/evaluator_called=false다. 실제 모델 품질·RF 수치 정확도·복구 완료·물리 정리 판정은 이 단위의 범위가 아니다.

## 2. 기존 공개 API와 직접 재사용의 경계

[가상 meter 복구 평가 사용법](../../fcc/virtual_fleet_meter_recovery_assessment_usage.md)과 [공개 소스](../../../labflow/virtual_fleet/meter_recovery_assessment.py)의 assess_meter_frequency_recovery(report, events, *, declaration)는 pure memory API다. declaration exact8에는 meter 복구용 goal exact6과 rf_basis가 필요하다. 현재 sensor goal에는 meter_id/allow_meter_frequency_reconfigure 등의 필수 항목이 없어 native shape 단계에서 거절될 수 있다. 그 항목을 채워도 goal.kind=acquire_fresh_rf_sensor_meter와 policy id=rf_meter_frequency_recovery_v1을 요구하므로 현재 goal=acquire_fresh_rf_sensor/policy id=codex_virtual_one_action의 평가 계약이 되지 않는다. meter·RF path·무잡음·위임을 만들거나 goal/policy를 바꾸어 호출하지 않는다. 호출하지 않은 API가 unsupported를 반환했다고 기록하지 않는다.

[sensor 평가 공개 소스](../../../labflow/virtual_fleet/evaluation.py)의 evaluate_sensor_run(trial, result, events)는 원 SensorTrial과 내부 profile/role/condition·새 취득 근거를 사용한다. [단일 행동 host](../../../labflow/virtual_fleet/codex_virtual_one_action.py)는 종료 때 trial/runtime/harness 참조를 해제하고 결과 dict만 반환한다. seed·catalog·UUID로 새 trial을 만들어 같은 원 trial이라 주장하지 않는다. 원 trial이 있어도 full completed/fresh-measurement 조건은 supervisor_stop으로 의도적으로 끝난 한 명령의 효과 평가와 의미가 다르다.

[공개 strict decoder](../../../labflow/virtual_fleet/model_operator_boundary.py)의 decode_operator_response(response: bytes, prompt: dict)는 원 wire 수용 근거가 있는 경우에만 직접 재사용한다. 두 과업 evaluator는 이 단위에서 호출0이다. 기존 meter 평가의 입력 불변·일관성/부족 분리·false assurance 원칙을 따르며 다른 goal의 task verdict를 재사용하지 않는다. 공개된 범용 one-action evidence validator가 있다고 가정하지 않고 부모 private _Run/_shape/_validated_events는 호출·상속하지 않는다.

## 3. 확정 접근과 생성 예정 파일

고정 pure effect assessor가 caller 제공 native evidence만 읽는다. live trial 반환이나 평가 callback을 추가하는 방식은 기존 host 수명/API를 바꾸므로 이 단위에서 보류한다. meter 선언·goal·policy·completed claim을 강제로 만드는 방식은 채택하지 않는다.

생성 예정 신규3은 다음 경로이며 현재 존재나 구현 완료를 뜻하지 않는다.

- labflow/virtual_fleet/codex_one_action_assessment.py
- tests/test_virtual_fleet_codex_one_action_assessment.py
- docs/fcc/virtual_fleet_codex_one_action_assessment_usage.md

공통 source/host/producer/decoder/기존 evaluator/DB/registry 수정0이다. 새 runtime·framework·provider·callback·Store·reader를 만들지 않는다. [부모 단일 행동 설계](2026-10-25-codex-virtual-one-action-design.md)와 [사용법](../../fcc/virtual_fleet_codex_virtual_one_action_usage.md)을 유지한다.

## 4. 제안 공개 API와 입력

```python
def assess_codex_one_action_effects(
    packet: dict, *, caller_error_code: str | None = None,
) -> dict:
    ...
```

export는 위 함수와 CodexOneActionAssessmentError(ValueError) 정확2다. packet은 native dict exact9이며 각 key는 반드시 있고 값 None은 자료 미제공을 뜻한다.

| key | 허용 값 |
| --- | --- |
| host_result | 원 one-action exact12 또는 None |
| context8 | 원 공개 context8 또는 None |
| prompt | 원 genuine prompt exact5 또는 None |
| response_bytes | 원 수신 bytes 또는 None; bytes는 이 필드에서만 허용 |
| harness_report | 원 legacy report exact15 또는 None |
| harness_events | 원 event exact8의 list 또는 None |
| before | 원 공개 observation exact5/full64 또는 None |
| after | 원 공개 observation exact5/full64 또는 None |
| dispatch_receipt | 원 node/global receipt 또는 None |

파일 읽기는 caller 소유다. 이 API는 경로·reader·원 exception·runtime·clock·declaration factory를 받지 않는다. 원본 bytes나 JSON을 자동 탐색·로드하지 않고 native subclass/cycle/NaN/surrogate/bool-as-number를 거절한다. 알려지지 않은 key와 잘못된 타입은 고정 invalid_input이다. None과 빈 response bytes는 구별한다.

caller_error_code는 None 또는 고정 후보의 host12/producer11/boundary8 full code 중 하나인 native str다. 실제 예외의 repr/message/traceback은 입력으로 받지 않는다. host_result.failure가 있으면 code가 맞아야 하며 다르면 관측 모순이다. receipt 없는 preflight 거절은 caller code만 보존하고 stage=null/source=caller로 표시한다. 이를 실제 무파견이나 과업 PASS의 인증으로 올리지 않는다.

## 5. binding과 근거 대조

1. native tree와 자원 한도를 검증하고 분리 복사한다. 기록 읽기 전후 canonical component hash를 대조하며 바뀌면 고정 internal_error다. 이것은 두 번 관측한 입력 불변 확인이며 외부 동시 변경의 원자적 잠금이나 보관 진위 검증이 아니다.
2. host kind·고정1/1/1/30/0·outer8/60/여유6·no refund/reset/retry 선언, legacy false flags를 대조한다. 다른 host/goal/policy는 unsupported이며 변환하지 않는다. 같은 protocol 안의 모순은 별도 verdict로 남긴다.
3. host binding6, prompt binding/request hash, run/runtime IDs, context8에서 remaining_budget만 분리한 context7, before와 context.observations, event/report IDs 및 full64 profile/device/role 관계를 대조한다. hash/ID 일치는 제공된 그래프의 일관성만 뜻한다. 실제 fresh runtime이었다는 증명은 아니다.
4. wire_accepted=true 또는 원 wire가 제공된 경우 complete prompt/response가 있어야 strict 재대조를 수행한다. genuine decoder의 proposal과 원 host wire·policy_decision이 정확히 같고 scope는 DUT.start {}, sensor.acquire/read {}, advance1 또는 bounded stop이어야 한다. 불완전 source 오류의 출력에 decoder를 새로 적용해 원 host wire 수용 상태를 바꾸지 않는다. 자료가 없으면 unverified다.
5. event sequence는1..N, bounded ASCII ID는 고유하고 모든 report/event 참조가 일치해야 한다. event:N 접두를 강제하지 않는다. intent≤1, receipt≤1, transport retry0 및 logical/tick/decision 한도를 대조한다. request ID를 새로 만들거나 재파견하지 않는다.
6. receipt와 같은 request를 원인으로 한 후행 observation, 원 dispatch_receipt, after 및 host after hash를 함께 확인한다. execute는 tick 유지, advance는+1, revision은 비역행이다. command마다 revision+1을 강제하지 않는다. 원 status/reason과 public before/after를 보존하며 diagnostic 변화와 설정 성공을 혼동하지 않는다.
7. host failure의 code/stage와 events의 최초 error/실패 receipt refs, 후행 cleanup.secondary_errors를 구별한다. 후행 정리 실패나 caller code로 원 first error를 교체하지 않는다. 일치 여부를 표시하며 원 host를 수정하지 않는다.

stored artifact descriptor는 제공된 canonical 값과의 size/hash 일관성을 확인할 뿐 파일을 열어 보지 않는다. response_bytes는 원 bytes 자체의 hash를 쓴다. prefix/미완료·after 누락·unresolved·events 미제공은 자료 부족이다. 서로 다른 run/runtime·wire/request·원 receipt와 관측 모순·허용 밖 행동·명령2개·예산 모순은 확인된 contradiction이다. 일부 자료가 없어도 이미 확인된 모순을 지우지 않는다.

## 6. 정상·거절·불명 수용 조건

| 제공 근거 | effect / command | 별도 평가 |
| --- | --- | --- |
| 단일 허용 intent/receipt/causal after가 같은 binding이고 원 status ok | 실제 changed/unchanged, accepted | assessed/consistent; task 미평가 |
| 같은 근거에서 원 status pending | 실제 changed/unchanged, pending | assessed/consistent; 설정·취득 완료를 추정하지 않음 |
| 같은 근거에서 invalid/unsupported/error/disconnected | 실제 changed/unchanged, rejected | assessed/consistent 가능; 명령 거절과 평가 오류/업무 실패를 구별 |
| 유효 stop와 대응 terminal, intent0 | not_applicable, not_dispatched | assessed/consistent; completed claim도 task 미평가 |
| 원 host/D2/decoder 최초 오류와 complete terminal·intent0가 일치 | not_applicable, not_dispatched | assessed/consistent 가능; 원 wire 수용·실제 제공자 성공을 보충하지 않음 |
| caller preflight code만 있고 host/evidence 없음 | unknown, unknown | inconclusive/insufficient; reported refusal만 보존 |
| intent는 있으나 receipt/after/terminal·현재 연결이 미확보 | unknown, unknown | inconclusive/insufficient; count·값을0으로 채우지 않음 |
| 동일 protocol에서 확실한 binding/action/clock/count/hash 모순 | unknown, unknown | assessed/contradictory; 이것은 task fail 점수가 아님 |
| 다른 goal/host/policy 또는 이미 변환·재평가된 legacy 형상 | unknown, unknown | unsupported/null; 기존 과업 evaluator로 우회하지 않음 |

effect changed는 after가 before와 다르다는 public 관측일 뿐 유효 RF 측정·목표 충족을 뜻하지 않는다. sensor.read의 불변은 그 자체로 실패가 아니다. 거절도 diagnostic 변화가 있으면 changed일 수 있으므로 무조건 unchanged로 강제하지 않는다. 이후 새 취득/복구 근거가 없으면 목표 평가는 계속 미실행이다.

reported elapsed/usage가 선언 상한을 초과하면 contradiction이다. 기록이 상한 이하이거나 cleanup flag가 true여도 실제 wall clock·원격 회수·출력 차단을 검증한 것이 아니다. 평가 우선순위는 확인된 contradiction > 근거 부족 > consistent다. 실제 효과 값은 binding이 성립할 때만 changed/unchanged로 산출한다.

## 7. 반환과 hash

top exact14는 schema_version/kind/status/verdict/bindings/observed_effect/command_outcome/first_error/task_assessment/checks/evidence_refs/verification/reason_codes/limits다. kind=codex_one_action_effect_assessment, status=assessed/inconclusive/unsupported, verdict=consistent/contradictory/insufficient/null이다. status와 verdict의 조합은 §6 표를 따른다.

bindings exact3은 operator_binding/input_sha256/components다. operator_binding은 원 binding6 또는 null이다. components는 packet9와 caller_error_code의 정확10 key이며 각각 present/bytes/sha256 exact3다. None은 false/0/null, bytes는 원 bytes, 다른 값은 UTF8/BOM없음·sort_keys·compact·allow_nan=false·LF없음 canonical JSON을 해시한다. 빈 bytes는 true/0/SHA256(empty)라 None과 다르다. input_sha256은 {schema_version:1, kind:codex_one_action_assessment_inputs, components:위 정확10}의 canonical SHA다.

first_error는 null 또는 code/stage/source exact3이며 source=host_result/caller다. task_assessment exact4는 status=not_evaluated/verdict=null/score=null/evaluator_called=false다. checks exact6은 input_binding/wire_scope/same_run_evidence/single_action/effect_receipt/error_and_cleanup이고 값은 supported/contradicted/unverified다. supported는 해당 경로의 요건 충족을 뜻하며, 원 wire 미수용과 무파견이 일치하는 거절 경로도 포함한다. evidence_refs는 실제 제공 event ID와 고정 component:<key> 중 최대32개며 private 경로나 원 exception을 넣지 않는다.

verification exact10은 input_values_unchanged/supplied_graph_consistent/root_authority_verified/runtime_authenticity_verified/storage_integrity_verified/actual_wall_time_verified/model_quality_verified/hardware_verified/physical_cleanup_verified/task_goal_verified다. 앞2는 관측 결과 bool, 뒤8은 false다. observed_effect는 changed/unchanged/unknown/not_applicable, command_outcome은 accepted/pending/rejected/not_dispatched/unknown이다. task_assessment.evaluator_called는 기존 과업 evaluator의 호출 여부이며 별도 effect assessor 자체를 뜻하지 않는다. 숫자 score, 새 모델 usage·원가 합계 또는 실행 권한을 생성하지 않는다.

reason_codes는 §9 기계 계약의 닫힌 고정 code 최대32개다. native 형상/한도 오류는 CodexOneActionAssessmentError의 codex_one_action_assessment_invalid_input/limit_exceeded/internal_error로만 전달한다. .code/str/args는 code만이며 cause/context=None이다. 관측한 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 그대로 전파한다.

## 8. bound·정리·진입 조건

전체 입력8MiB, 출력64KiB, context8/before/after 각1MiB, prompt/report 각256KiB, response/dispatch receipt 각64KiB, events 총2MiB/최대16개/각512KiB, depth32/node200000, signed64 정수를 제안한다. 기존 meter32MiB/128KiB/4096event보다 scope를 줄인 데이터 처리 한도이며 실제 모델·운영 예산이 아니다.

함수는 순수 메모리만 소유하므로 close할 파일·runtime·process·worker·network·Store가 없다. input 참조를 결과에 남기지 않고 detached 요약만 반환한다. cleanup을 위해 execute/advance/stop·재구성·재평가·파일 삭제를 하지 않는다. 원 host cleanup·output off null·remote false를 고치지 않는다.

실제 모델·설치CLI·ADC·운영Store·livebudget·외부망·실장비 권한과 새승인·seed/reset/refund를 부여하지 않는다. 이 계약의 게시를 제품·평가 API·test runtime·가상 factory 실행 GO로 해석하지 않는다.

## 9. 기계 계약

아래 객체는 승인된 입력·출력·오류·한도·수용 조건을 같은 값으로 명시한다. 실제 반환 enum과 status/verdict 조합은 output에 정의한다. acceptance는 조건부 수용 설명이며 그 절의 “consistent possible”은 새 반환 enum이 아니다. 설명과 기계 계약 모두 과업 점수·실행 권한·보관 진위를 생성하지 않는다.

```json
{
  "acceptance": [
    {
      "case": "complete allowed action status ok with causal after",
      "command": "accepted",
      "effect": "compare actual supplied before/after",
      "status": "assessed",
      "verdict": "consistent"
    },
    {
      "case": "same, status pending",
      "command": "pending",
      "effect": "changed or unchanged; no completion inferred",
      "status": "assessed",
      "verdict": "consistent"
    },
    {
      "case": "same, known invalid/unsupported/error/disconnected",
      "command": "rejected",
      "effect": "changed or unchanged; rejection may alter diagnostics",
      "status": "assessed",
      "verdict": "consistent possible"
    },
    {
      "case": "valid stop and matching terminal, no intent",
      "command": "not_dispatched",
      "effect": "not_applicable",
      "status": "assessed",
      "verdict": "consistent"
    },
    {
      "case": "original host/source/decoder error plus complete matching terminal/no intent",
      "command": "not_dispatched",
      "effect": "not_applicable; no accepted wire invented",
      "status": "assessed",
      "verdict": "consistent possible"
    },
    {
      "case": "caller-only preflight code or missing causal after/receipt/events",
      "command": "unknown",
      "effect": "unknown",
      "status": "inconclusive",
      "verdict": "insufficient"
    },
    {
      "case": "confirmed same-protocol binding/action/hash/count/clock contradiction",
      "command": "unknown",
      "effect": "unknown",
      "status": "assessed",
      "verdict": "contradictory"
    },
    {
      "case": "other host/goal/policy or already transformed/evaluated legacy protocol",
      "command": "unknown",
      "effect": "unknown",
      "status": "unsupported",
      "verdict": null
    }
  ],
  "binding_rules": [
    "deep bounded native clone and canonical before/after component comparison",
    "host fixed kind/limits/legacy flags without changing input",
    "context8 minus only remaining_budget matches original prompt context and before observation",
    "full64 device/profile/role and same provided run/runtime/request bindings",
    "genuine strict decoder only when original wire acceptance exists and inputs complete",
    "unique bounded ASCII event IDs, sequence1..N and all references; no event:N prefix requirement",
    "single intent/receipt, zero retry, advance tick+1/execute same tick and nondecreasing revision",
    "causal after/request and dispatch receipt match original host metadata",
    "original first code/stage retained; caller discrepancy and cleanup secondary identified"
  ],
  "common_changes": [],
  "errors": {
    "bad_native_shape": "fixed error; no partial task verdict",
    "cause_context": null,
    "code_str_args_fixed_only": true,
    "controls_preserved": [
      "KeyboardInterrupt",
      "SystemExit",
      "GeneratorExit",
      "MemoryError"
    ],
    "prefix": "codex_one_action_assessment_",
    "suffixes": [
      "invalid_input",
      "limit_exceeded",
      "internal_error"
    ],
    "well_shaped_observed_contradiction": "separate assessed/contradictory result, not invalid_input"
  },
  "hash_contract": {
    "None": {
      "bytes": 0,
      "present": false,
      "sha256": null
    },
    "canonical_JSON": {
      "UTF8_without_BOM": true,
      "allow_nan": false,
      "ensure_ascii": false,
      "separators": [
        ",",
        ":"
      ],
      "sort_keys": true,
      "trailing_LF": false
    },
    "component_exact3": [
      "present",
      "bytes",
      "sha256"
    ],
    "component_keys_exact10": [
      "host_result",
      "context8",
      "prompt",
      "response_bytes",
      "harness_report",
      "harness_events",
      "before",
      "after",
      "dispatch_receipt",
      "caller_error_code"
    ],
    "concurrent_input_change": "fixed internal_error; no atomic/global immutability claim",
    "input_hash": "SHA256(canonical {schema_version:1,kind:codex_one_action_assessment_inputs,components:exact10})",
    "other_components": "SHA256 of complete canonical native JSON values",
    "raw_response": "SHA256 of original bytes; empty bytes has present=true/bytes0/SHA256(empty)"
  },
  "limits": {
    "max_context_or_observation_bytes": 1048576,
    "max_depth": 32,
    "max_dispatch_receipt_bytes": 65536,
    "max_event_bytes": 524288,
    "max_events": 16,
    "max_events_bytes": 2097152,
    "max_host_result_bytes": 262144,
    "max_input_bytes": 8388608,
    "max_integer": 9223372036854775807,
    "max_nodes": 200000,
    "max_output_bytes": 65536,
    "max_prompt_bytes": 262144,
    "max_report_bytes": 262144,
    "max_response_bytes": 65536,
    "min_integer": -9223372036854775808
  },
  "new_framework_registry_callback_DB_Store_runtime": false,
  "output": {
    "bindings_exact3": [
      "operator_binding",
      "input_sha256",
      "components"
    ],
    "check_values": [
      "supported",
      "contradicted",
      "unverified"
    ],
    "checks_exact6": [
      "input_binding",
      "wire_scope",
      "same_run_evidence",
      "single_action",
      "effect_receipt",
      "error_and_cleanup"
    ],
    "command_outcome": [
      "accepted",
      "pending",
      "rejected",
      "not_dispatched",
      "unknown"
    ],
    "evaluator_called_means": "full task evaluators only; does not deny that this effect function was invoked",
    "evidence_refs": "provided valid event IDs and component:<known-key>; no paths or exceptions",
    "evidence_refs_max": 32,
    "first_error_exact3": [
      "code",
      "stage",
      "source"
    ],
    "first_error_source": [
      "host_result",
      "caller"
    ],
    "kind": "codex_one_action_effect_assessment",
    "observed_effect": [
      "changed",
      "unchanged",
      "unknown",
      "not_applicable"
    ],
    "operator_binding": "original binding6 or null",
    "schema_version": 1,
    "status_verdict_pairs": [
      [
        "assessed",
        "consistent"
      ],
      [
        "assessed",
        "contradictory"
      ],
      [
        "inconclusive",
        "insufficient"
      ],
      [
        "unsupported",
        null
      ]
    ],
    "supported_on_refusal": "requirements for that no-dispatch path are satisfied, not a new wire/model success",
    "task_assessment": {
      "evaluator_called": false,
      "score": null,
      "status": "not_evaluated",
      "verdict": null
    },
    "task_assessment_exact4": [
      "status",
      "verdict",
      "score",
      "evaluator_called"
    ],
    "top_exact14": [
      "schema_version",
      "kind",
      "status",
      "verdict",
      "bindings",
      "observed_effect",
      "command_outcome",
      "first_error",
      "task_assessment",
      "checks",
      "evidence_refs",
      "verification",
      "reason_codes",
      "limits"
    ],
    "verification_exact10": [
      "input_values_unchanged",
      "supplied_graph_consistent",
      "root_authority_verified",
      "runtime_authenticity_verified",
      "storage_integrity_verified",
      "actual_wall_time_verified",
      "model_quality_verified",
      "hardware_verified",
      "physical_cleanup_verified",
      "task_goal_verified"
    ],
    "verification_values": {
      "all_other8": false,
      "input_values_unchanged": "observed bool",
      "supplied_graph_consistent": "observed bool"
    }
  },
  "packet": {
    "caller_error_code": "None or native string in fixed current host12/producer11/boundary8 full-code whitelist",
    "caller_error_stage_without_receipt": null,
    "exact9": [
      "host_result",
      "context8",
      "prompt",
      "response_bytes",
      "harness_report",
      "harness_events",
      "before",
      "after",
      "dispatch_receipt"
    ],
    "no_exception_message_repr_or_traceback": true,
    "no_original_file_or_runtime_authentication": true,
    "types": {
      "after": "original full64 public observation exact5 or None",
      "before": "original full64 public observation exact5 or None",
      "context8": "original public exact8 dict or None",
      "dispatch_receipt": "original node/global receipt dict or None",
      "harness_events": "native list of exact8 events or None",
      "harness_report": "original exact15 dict or None",
      "host_result": "original exact12 dict or None",
      "prompt": "original genuine exact5 dict or None",
      "response_bytes": "exact native bytes <=65536 or None; bytes only allowed here"
    }
  },
  "priority": "confirmed contradiction > missing evidence > consistent; never a task pass/fail score",
  "proposed_owned_new3": [
    "labflow/virtual_fleet/codex_one_action_assessment.py",
    "tests/test_virtual_fleet_codex_one_action_assessment.py",
    "docs/fcc/virtual_fleet_codex_one_action_assessment_usage.md"
  ],
  "public_function": {
    "error_class": "CodexOneActionAssessmentError(ValueError)",
    "exports_exact2": [
      "assess_codex_one_action_effects",
      "CodexOneActionAssessmentError"
    ],
    "external_runtime_reader_path_clock_provider_parameters": false,
    "input": "native packet exact9; each field mandatory, None is explicitly not provided",
    "name": "assess_codex_one_action_effects",
    "signature": "assess_codex_one_action_effects(packet: dict, *, caller_error_code: str | None = None) -> dict"
  },
  "reason_codes": [
    "unsupported_protocol",
    "task_evaluator_inapplicable",
    "evidence_missing",
    "execution_unresolved",
    "caller_refusal_only",
    "binding_mismatch",
    "wire_scope_mismatch",
    "wire_evidence_missing",
    "receipt_observation_mismatch",
    "host_summary_mismatch",
    "single_action_violation",
    "reported_budget_violation",
    "first_error_mismatch",
    "cleanup_unverified",
    "effect_observed",
    "command_rejected_observed",
    "command_pending_observed",
    "stop_not_completion",
    "host_error_before_dispatch",
    "supplied_provenance_only"
  ],
  "reason_codes_max": 32,
  "resources_cleanup": {
    "data_limits_are_not_model_or_operating_fuel": true,
    "execute_advance_stop_reconstruct_refund_reset": 0,
    "input_references_retained_in_output": false,
    "input_values_mutated": false,
    "original_host_output_off_null_remote_false_unchanged": true,
    "owned_files_runtime_workers_process_network_Store_clock": 0,
    "pure_memory_only": true
  }
}
```

공통 계약의 게시, 정확 base·신규3 소유, 독립 검증 조건 봉인과 별도 CORE-GO 뒤에만 제품·RED·test runtime·평가 API 구현을 시작한다. 현재 문서의 무결성 대조를 기능·모델·현장 검증으로 올리지 않는다.
