# 접수 계획의 제공 조건 검토 gate

`labflow.intake_rule_condition_gate.evaluate_intake_rule_conditions`는 제공된 작은 조건식과 같은 현재 접수·계획 snapshot을 대조하는 순수 API다. 조건의 참은 `REVIEW_RULE_BRANCH`, 거짓은 `NOT_SELECTED`, 누락·상충·근거 불일치·미지원은 `HOLD`다. 이 결과는 검토할 분기를 표시하며 규범 적합성, 측정 PASS, 장비 운전이나 작업자 생성 권한을 부여하지 않는다.

2026-10-26 구현 기준이다. [facts→plan 사용법](intake_facts_to_conducted_plan_usage.md)의 wrapper와 [plan 입력 계약](intake_conducted_twin_plan_usage.md)의 원래 plan8을 그대로 보존한다. 기반 facts→plan 변경은 이 작업 시작 시 독립 인수 전 부모 의존성이다. 기존 registry7·worker·Store·generation 경계를 변경하거나 호출하지 않는다. 실모델, 설치 CLI, 로그인, 운영 DB, 실장비·현장 검증은 이 API의 범위 밖이다.

## 호출과 현재 계획 연결

```python
from labflow.intake_rule_condition_gate import evaluate_intake_rule_conditions

result = evaluate_intake_rule_conditions(
    intake_plan, current_plan,
    context=context, analysis=analysis,
    expected_revision=expected_revision,
    expected_context_sha256=expected_context_sha256,
    rules=rules, rule_sources=rule_sources,
    inputs=inputs, execution_context=execution_context,
)
```

`intake_plan`은 genuine facts builder의 exact6 반환값, `current_plan`은 그 안의 exact8 `plan_input`이다. `context`는 기존 public8, `analysis`는 그 context의 검증 가능한 분석이다. API는 제공된 method4로 genuine facts builder를 다시 호출하고 wrapper 전체·current plan 전체를 재구성값과 대조한다. revision은 bool이 아닌 양의 native int여야 하며, 제공 context SHA·analysis SHA·plan SHA도 일치해야 한다. 다른 revision, 바뀐 사실·질문·설정, 재계산한 해시만 붙인 변조도 `current_plan_mismatch`로 보류한다.

이 대조는 호출자가 제공한 현재 snapshot끼리의 일관성 검사다. Store의 실제 현재 버전을 조회하거나 원본 파일을 다시 열지 않는다. 유효한 동일 접수라도 RF 설정 부족으로 기존 plan이 `blocked`일 수 있다. 이때 충분한 별도 조건 입력이 있으면 검토 분기를 표시할 수 있지만, 원래 `blocked`, 질문, 미확정 설정·한계·불확도·`not_assessed` 및 권한 false는 `snapshots` 안에서 그대로 남는다. gate의 질문 목록으로 원래 질문을 대체하지 않는다.

## 제공 조건과 원문 snapshot

`rules`는 1~6개이며 각 rule은 다음 exact5다.

| 필드 | 계약 |
| --- | --- |
| `rule_id` | 비어 있지 않은 문자열, 최대 200자, 이번 묶음에서 유일 |
| `declared_predicate` | 아래의 유계 AST |
| `input_types` | 참조 input 이름별 `number` / `boolean` / `string` |
| `units` | 같은 input 이름별 명시 단위 문자열 |
| `source_ref` | exact3: `source_id`, `sha256`, `rule_index` |

`rule_sources`는 1~6개 exact3 `{source_id, sha256, text}`다. source ID는 최대 200자의 고유 문자열, SHA는 소문자 64자리 SHA-256, `text`는 최대 1 MiB의 제공 UTF-8 JSON 문자열이다. API는 `text.encode('utf-8')`의 해시를 실제 대조한다. 원문 JSON의 `rules` 배열은 1~6개여야 하며, `rule_index`는 bool이 아닌 0부터 시작하는 native int다. 해당 항목의 `rule_id`, `declared_predicate`, `input_types`, `units` 네 payload가 rule과 canonical JSON으로 일치해야 한다. AST·타입·단위·식별자를 변경하고 원래 SHA만 재사용할 수 없다. 원문 항목의 그 밖의 metadata는 판정하지 않으며 제공 원문 text를 보존한다.

JSON 중복 key와 비유한 수는 거절한다. 원문 해시 일치는 제공 snapshot의 내용 결합만 뜻한다. 발행 주체, 최신 유효성, 사용 권리, 실제 사례 적용성이나 생산자 인증을 검증하지 않는다. 조건 숫자·변조군·주파수·단위의 기본값이나 내장 규범 표는 없다. 아래와 테스트 파일의 값은 새로 작성한 합성 연산 예제다.

```json
{
  "operator": "all",
  "operands": [
    {"operator": "eq", "input": "mode", "value": "LAB-C"},
    {"operator": "in", "input": "mode", "value": ["LAB-B", "LAB-C"]},
    {"operator": "gt", "input": "level", "value": 12},
    {"operator": "gte", "input": "level", "value": 17},
    {"operator": "eq", "input": "enabled", "value": true}
  ]
}
```

이 예제의 타입은 `mode=string`, `level=number`, `enabled=boolean`, 단위는 각각 `label`, `mV`, `boolean`이다. `level=17 mV`이면 두 수치 비교는 참이며, `gt 17`로 바꾸면 거짓이다. 이 예제는 실제 규범 한계나 고객 수치가 아니다.

## AST와 값·근거 계약

leaf exact3는 `{operator, input, value}`, `all` exact2는 `{operator, operands}`다. 임의 경로 탐색, 함수, callback, 변환식, 문자열 수치 파싱은 없다.

| 연산 | 의미 |
| --- | --- |
| `eq` | 같은 선언 타입에서 native 값 비교 |
| `in` | 같은 선언 타입의 literal 목록에 포함되는지 비교 |
| `gt`, `gte` | `number`에서만 엄격 초과 / 이상 비교 |
| `all` | 모든 하위 조건이 참인지 비교 |

input 이름은 영문자로 시작하는 영문·숫자·밑줄 1~80자다. 선언은 rule당 1~32개이고 AST가 실제 사용하는 이름 집합과 정확히 같아야 한다. 단위는 제어문자 없는 1~40자 문자열이다. AST는 rule당 최대 128노드, root depth0에서 최대 depth8, `all`당 1~8개 operand, `in`당 1~16개 literal로 제한한다. 입력 전체는 부모의 native snapshot 한도인 8 MiB·depth32·100000노드 안이어야 한다.

`inputs`는 최대 64개 이름의 제공 snapshot이다. 사용되는 각 값은 exact4 `{value, unit, status, evidence}`다. `status='explicit'`이어야 한다. `None`이나 `value=null`은 누락, `conflict`는 상충, 그 밖의 status는 미확인으로 보류한다. 원래 제공값을 수정하지 않는다. 사용하지 않는 input은 추론에 쓰지 않고 snapshot으로만 남긴다.

`number`는 bool을 제외한 native int 또는 유한 float다. int의 출력 자릿수는 부호 포함 최대 128자다. `boolean`은 native bool, `string`은 1~200자 문자열이다. 숫자 문자열·bool을 숫자로 바꾸지 않는다. `0`과 `false`는 알려진 유효 값이다. 단위는 선언과 문자열이 정확히 같아야 하며 자동 변환이나 단위 추정은 하지 않는다. literal의 단위는 해당 input의 명시 `units` 선언을 따른다.

`evidence`는 1~16개의 기존 intake citation이다. genuine citation validator로 같은 context 문서의 SHA·위치·quote를 검사한다. 각 quote 자체는 다음 exact3 JSON이어야 하고, 모든 인용의 field·native value·unit이 제공 input과 canonical JSON으로 일치해야 한다. 임의 설명문에서 숫자나 승인을 추출하지 않는다.

```json
{"field":"level","value":17,"unit":"mV"}
```

API가 인용된 원본 바이트를 재개방한 것은 아니다. 일반 문장·PDF·XML에서 이 명시 값 snapshot을 조립하는 작업이나 다른 단위·시험방법 지원은 별도 검증이 필요하다. 근거가 다른 값·다른 줄·다른 SHA를 가리키면 참으로 처리하지 않는다.

## 실행 문맥과 결과

`execution_context`에는 다음 8개 developer policy 문맥을 제공한다. 각각 inputs와 같은 exact4 형식이며 native boolean·단위 `boolean`·현재 접수의 JSON literal 근거가 필요하다.

- `current_validity_approved`
- `case_applicability_approved`
- `metric_method_approved`
- `reference_plane_verified`
- `correction_ledger_verified`
- `conditional_limit_resolved`
- `uncertainty_decision_rule_approved`
- `independent_holdout_available`

검토 상태를 선택하려면 8개 모두 근거가 일치하는 제공 `true`여야 한다. false·누락·미확인·상충·형식 오류는 HOLD다. bare `true`만 전달해도 승인이 되지 않는다. 이 목록은 개발 gate의 검토 정책이며 새로운 규범 의무가 아니다. 근거가 붙은 true조차 독립 검증된 승인 권위로 해석하지 않는다.

반환 exact10은 `schema_version`, `kind`, `status`, `binding`, `rule_results`, `gaps`, `questions`, `snapshots`, `normative_verdict`, `verification`이다. `binding`은 대조 성공 시 원래 plan binding6 사본이고 실패하면 null이다. `snapshots`에는 원래 wrapper/current plan/context/analysis/rules/rule_sources/inputs/execution_context와 제공 expected revision/context SHA까지 exact10으로 분리 보존한다. 반환 사본을 바꿔도 입력은 바뀌지 않는다. native 입력 자체를 안전하게 복제할 수 없으면 snapshots와 binding을 null로 두고 보류한다.

rule 결과 exact6은 `rule_id`, `status`, `predicate_value`, `source_ref`, `gaps`, `questions`다. `predicate_value`는 완전한 조건 입력에서만 bool이다. 실행 문맥이 빠져도 별도로 계산 가능한 predicate bool은 남길 수 있지만 status는 HOLD다. AST 전체의 입력을 검사하므로 다른 operand가 거짓이어도 누락·상충을 거짓으로 숨기지 않는다. 공통 문맥 오류는 모든 rule을 HOLD로 만든다. 개별 rule 오류는 그 rule을 HOLD로 남긴다.

전체 상태는 어느 공백이라도 있으면 HOLD, 공백 없이 참인 rule이 있으면 REVIEW_RULE_BRANCH, 모두 거짓이면 NOT_SELECTED다. 전체 HOLD 안에 개별 검토 결과가 있어도 실행 권한으로 쓸 수 없다. `gaps`는 공통 공백, 각 rule의 `gaps`는 해당 공백이다. gap exact3는 `code`, `field`, `blocking=true`다. top-level 질문은 공통·개별 공백의 field마다 하나로 합치며 exact4 `key`, `field`, `reason`, `message`를 반환한다. 원래 plan의 미해결 질문과 raw refs는 snapshots에 그대로 남는다. 질문은 필요한 값·단위·근거를 구체적으로 지목하며 불필요한 성공 기본값을 넣지 않는다.

`normative_verdict`는 항상 null이다. `verification` exact8은 현재/승인의 `caller_snapshot_only`, 원문의 `provided_text_hash_only`, 규범/측정의 `not_assessed`, `execution_authority=false`, `worker_generation_authority=false`, `physical_permission=false`다. MemoryError·KeyboardInterrupt·SystemExit 같은 원래 중단은 성공 결과로 바꾸지 않고 전파한다. 파일·Store·SQL·자식 process·네트워크·장비 I/O는 없다.

## 검증 범위

새 합성 테스트는 5연산, 엄격/포함 경계·0/false, 누락 우선·8개 문맥, 상충·타입·단위, 현재 citation·원문 payload 결합, 다른 revision·변조 계획, 부모 미해결 질문 보존, 한도·native 거절·복제·중단 전파·I/O 금지를 검증한다. 이전 facts/plan 전체 suite를 이 변경의 새 검증 수로 합산하지 않는다. 별도 제공 비공개 조건의 적용 기록은 로컬 proof에서 관리하며 공개 코드·테스트·문서에 원문·조건 수치·경로·locator·고객 측정값을 넣지 않는다.

문서 무결성은 `python scripts/check_artifacts.py`로 확인한다. 이 검사와 합성 테스트 통과는 실장비 정확도·규범 적합성·실제 업무나 전체 무인시험소 완료를 입증하지 않는다.
