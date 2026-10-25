# 현재 접수의 규칙 조건 읽기

`labflow.intake_current_rule_condition_read.read_current_rule_conditions`는 실제 현재 접수 읽기와 기존 조건 gate를 연결한다. 현재 facts API를 한 번 읽고, 그 원 문맥·분석·wrapper/plan을 gate에 한 번 전달한 다음 같은 workspace의 현재 문맥·분석을 읽기 전용으로 다시 대조한다. 원 gate가 검증하는 조건 원문·AST·단위·C1 규칙은 변경하지 않는다.

2026-10-26 기준 [구현](../../labflow/intake_current_rule_condition_read.py), [새 합성 검사](../../tests/test_intake_current_rule_condition_read.py), [현재 facts API](intake_current_facts_plan_usage.md), [기존 조건 gate](intake_rule_condition_gate_usage.md)를 함께 확인한다. TXT 부모 `16cfdd8`과 이 변경의 독립 인수는 별도 검수 결과를 따른다. 현재자료 CLI `7e2cd6a`는 이 함수의 의존성이 아니다.

## 호출

```python
from labflow.intake_current_rule_condition_read import read_current_rule_conditions

result = read_current_rule_conditions(
    workspace, intake_id,
    method=method,
    rules=rules,
    rule_sources=rule_sources,
    inputs=inputs,
    execution_context=execution_context,
    expected_revision=None,
    expected_context_sha256=None,
)
```

workspace, intake_id와 다섯 keyword 입력은 명시적으로 제공한다. 이 함수는 source_settings/basis나 RF 수치·단위, method/rule/승인 기본값을 만들지 않는다. workspace는 진입 시 한 번 절대 경로로 해석하며 두 읽기에 같은 경로를 사용한다. 중간에 caller의 작업 폴더가 바뀌어도 다른 Store를 선택하지 않는다. 기존 Store와 현재 완료된 synthetic 접수만 부모가 지원하며, 지원 text/PDF·provenance·파일/manifest·현재 분석의 검증도 부모 계약을 따른다.

`method`는 원 current facts API에 그대로 전달한다. `rules`, `rule_sources`, `inputs`, `execution_context`는 원 gate에 그대로 전달하며 규범이나 원문에서 새 값·조건을 추출하지 않는다. 제공 rule text의 UTF-8 SHA·해당 index의 payload·유계 AST·타입·단위·현재 citation·JSON literal 근거 검사는 기존 gate가 담당한다. 제공 승인 boolean, 보고서 PASS 또는 반복 설정만으로 검토/실행 승인을 만들지 않는다.

optional expected pin은 첫 current facts 읽기에 그대로 전달한다. None인 항목만 첫 실제 current context의 revision 또는 canonical UTF-8 SHA로 선택해 gate에 전달한다. 제공한 잘못된 pin을 다른 값으로 바꾸지 않는다. bool·다른 revision/C1·미지원 method 등은 부모의 원 blocked/HOLD/gaps를 따른다. 원 wrapper의 questions가 빈 경우도 그대로 보존하며 해당 plan gaps나 gate 질문을 확인한다.

## compound exact6

| 필드 | 의미 |
| --- | --- |
| `status` | 두 관측이 같으면 원 gate 상태. 달라지면 `HOLD`. |
| `context` | 첫 genuine current facts API가 반환한 원 public8 현재 문맥. |
| `analysis` | 첫 읽기와 결합된 원 분석. |
| `facts_plan` | 첫 읽기의 원 facts wrapper exact6. 내부 `plan_input`은 원 exact8. |
| `rule_conditions` | 같은 원 wrapper/plan/context/analysis로 평가한 기존 gate exact10. |
| `current_relation` | 후행 genuine 읽기와의 실제 관측 관계. 아래 exact4. |

원 context/analysis/facts wrapper와 원 gate DTO를 변경하거나 새 승인 표기로 감싸지 않는다. gate의 `verification.current_version='caller_snapshot_only'`도 그대로 남긴다. 실제 Store 읽기의 관계는 별도의 current_relation에 표시하며 기존 gate가 독립적으로 Store를 읽은 것으로 바꾸지 않는다. 원 `normative_verdict=null`, 규범/측정의 `not_assessed`, 실행·작업자 생성·물리 권한 false를 유지한다.

| current_relation 필드 | 의미 |
| --- | --- |
| `status` | `same_current_snapshot` 또는 `current_snapshot_changed`. |
| `before` | 첫 실제 읽기의 exact3 `{revision, context_sha256, analysis_sha256}`. |
| `after` | 후행 실제 읽기의 같은 exact3. |
| `questions` | 같으면 빈 목록. 변경이면 `current_relation`을 지목하는 고정 질문 하나. |

SHA는 원 current context와 analysis 각각의 canonical JSON UTF-8 바이트에서 계산한다. revision만 같아도 context 또는 analysis의 SHA가 달라지면 변경이다. 새 revision 완료, 현재 문맥 또는 분석 변경을 기존 완료 결과로 숨기지 않는다. 변경 시 compound status만 HOLD로 두며 첫 gate의 REVIEW_RULE_BRANCH/NOT_SELECTED/HOLD, 원 snapshot과 질문은 그대로 보존한다. after의 문맥이나 분석을 첫 결과에 덮어써서 재결합하지 않는다.

gate의 참은 `REVIEW_RULE_BRANCH`, 거짓은 `NOT_SELECTED`, 조건 입력/근거의 부족·충돌·미지원은 `HOLD`다. **RF plan 준비 상태와 규칙 검토 분기는 별개다.** RF 설정의 단위가 부족해 plan이 blocked여도 충분한 별도 조건 근거는 원 gate의 검토 분기로 표시될 수 있다. 이때 source/basis의 null, 원 facts 질문과 plan gaps를 지우지 않는다. 호출자는 compound/current_relation, facts_plan.status와 원 gate 결과를 함께 읽어야 한다. REVIEW_RULE_BRANCH는 시험 준비나 실제 실행 권한을 뜻하지 않는다.

## 관측과 실패 경계

순서는 genuine `read_current_conducted_plan_from_facts` 1회 → 원 `evaluate_intake_rule_conditions` 1회 → genuine `IntakeReadModel.current_conducted_plan_context` 후행 1회다. gate가 재구성하는 기존 facts 비교와 각 reader 내부의 검증은 해당 부모 계약이며 새 source parser나 별도 rule engine은 없다.

각 current reader는 실제 이미 보존된 source/manifest와 현재 Store의 read transaction을 검증하고 SQL/native 수명을 정리한다. 이 함수는 부모의 transaction을 이어 붙이거나 두 읽기 사이의 lease/claim을 획득하지 않는다. 같은 값이라는 결론은 두 관측 snapshot의 일치다. 그 사이 또는 반환 뒤의 모든 변화·ABA를 검출하거나 미래 실행 시점의 현재 버전을 고정하지 않는다. 아직 등록/scan되지 않은 inbox 변경을 직접 감시하는 함수도 아니다. 다음 실행의 C1·현재 버전·안전 검증을 대체하지 않는다.

첫 읽기·gate·후행 읽기의 원 오류 객체와 KeyboardInterrupt·MemoryError·SystemExit·그 밖의 BaseException은 그대로 전파한다. 후행 읽기나 정리가 실패하면 오래된 compound를 성공 반환하지 않는다. SQL/native 정리 중 두 번째 오류가 나도 부모가 보존한 첫 오류를 새 예외나 HOLD payload로 대체하지 않는다. 이 함수는 별도 handle/connection을 소유하지 않으며 실패한 자원의 상태를 알 수 없으면 모두 닫혔다고 주장하지 않는다.

새 반환 경계만 기존 strict native JSON helper로 확인한다. compound는 canonical JSON 기준 **16777216바이트 이하**, depth48·400000노드 이하이며 비유한 수·surrogate·비native 값을 거절한다. native 검사를 통과한 원 객체를 유지하고 parent method/rule/source 검증을 다시 구현하지 않는다. 잘못된 자체 결과 형태/권한 표기는 고정 `ReadModelError('intake_current_rule_condition_read_result_invalid')`, 크기·깊이·노드 한도는 `ReadModelError('intake_current_rule_condition_read_result_limit')`다. 이 자체 오류 메시지에 경로·입력·원문·내부 exception text를 넣지 않는다. 부모 예외의 원형 보존은 별도 계약이며 CLI 출력/로깅 경계는 이 함수에 없다.

schema1 text 원 분석의 context_id 부재/None, 실제 stored manifest의 current analysis_context_id locator, 원 provider prompt와 다른 current context SHA도 부모의 원 의미를 유지한다. 원 prompt를 복원하거나 원 분석에 context binding을 사후 삽입하지 않는다. 제공 원문 해시와 caller execution_context 근거가 맞아도 독립 규범 유효성·판본·기관 승인으로 승격하지 않는다.

## 검증과 남은 범위

새 작성자 검사 14개에서 genuine TXT/PDF true/false, 새 revision의 후행 drift, 보존 source 변조의 원 오류, RF blocked/null/질문, pin/method/gate 공백, 첫/gate/후행 controls와 첫 정리 오류, 반환 한도, 상대 workspace 고정, 읽기 전용 SQL/native 정리를 확인했다. 일부 경계 검사는 제공 snapshot/mock을 사용하며 genuine Store 관측과 구별한다. drift/변조 주입은 이 검사를 위해 새로 만든 disposable 합성 자료에만 수행했다.

최종 새 suite의 SQL 관측은 합성 준비와 실제 읽기를 합쳐 229개 생성/229개 닫힘이다. Store binding probe는 36개, closed2/collected34·active0·남은 descriptor slot0이며 전역 native handle 잔여 +40/모듈 load 뒤 +25는 미귀속 관측으로 남긴다. 별도 runtime 금지 검사에서 두 current reader의 실제 읽기 전용 연결과 native binding 정리, 업무 DML/생성/claim/parser/AI/네트워크/자식 process 미호출을 확인했다. 이 수치를 이전 2개/13개 중간 실행이나 부모·CLI·독립 검수의 분모와 합치지 않는다. 원 실패 기록은 별도로 보존했다.

문서 무결성은 `python scripts/check_artifacts.py`와 이 문서의 UTF-8/로컬 링크로 확인한다. 이 구현과 합성 검사는 실제 규격의 자동 확정, 실모델 운영, 실장비 정확도·현장 업무나 전체 무인시험소 완료를 입증하지 않는다. 실제 모델·규범 전수·장비·현장 검증은 미실행이다.
