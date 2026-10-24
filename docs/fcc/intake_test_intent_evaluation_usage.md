# 제공 규정·방법 검토의 계약 평가

`evaluate_intake_test_intent_case(intake, proposal, sources, *, expectation)`는 사전에 작성한 oracle과 [제공 근거 검토 API](intake_test_intent_usage.md)의 결과를 비교한다. 합성·명시 제공 입력의 계약 검사이며 실제 모델 이해도·규범 적용성·실장비 승인을 평가하지 않는다. [설계](../superpowers/specs/2026-10-25-intake-test-intent-evaluation-design.md)와 [구현 계획](../superpowers/plans/2026-10-25-intake-test-intent-evaluation.md)을 기준으로 한다.

## 준비와 호출 순서

1. 기존 권한으로 준비한 원 context/analysis, 현재 full projection과 제공 observation, proposal/sources를 메모리에 보관한다. 필요한 DB 관측·문서 추출은 호출자가 먼저 마친다. 함수는 파일·DB·PDF parser·network·process를 열지 않는다. 원 질문·현재 답변을 과거 analysis로 재계산하지 않는다.
2. API를 실행하기 전에 원 합성 문장·질문·계약 판정표에서 oracle을 작성한다. 원 `{"intake": intake, "proposal": proposal, "sources": sources}`를 UTF-8 canonical JSON(`sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, `allow_nan=False`)으로 직렬화한 SHA-256을 input_sha256으로 고정한다. API 결과나 기존 검사 결과를 정답으로 복사하지 않는다.
3. `expectation`의 schema_version=1, kind=intake_test_intent_case_expectation, case_id/case_group_id, input_sha256, label_review_status, expected를 제공한다. pending이면 expected=null이다. reviewed이면 expected는 outcome/error_code/review의 정확3키다. 정상 반환 기대에는 fields/reason_codes/calculation_flags를, parent 오류 기대에는 고정 오류3 중 하나와 review=null을 넣는다. 상세 후보·기간 형상은 설계를 따른다.
4. 한 case를 호출하고 status/verdict/outcome/counts를 함께 읽는다. 같은 입력에 parent API는 최대1회다. 입력과 oracle은 변경하지 않으며 반환은 detached다. reviewed는 호출자의 라벨 검토 선언이며 정답 정확성·독립 배정이 확인됐다는 뜻이 아니다.
5. 원 입력·oracle SHA, 현재 소유 source SHA, 실제 결과와 실패를 호출자 private 새 run 경로에 보존한다. 같은 run을 덮어쓰거나 실패 뒤 기대값만 바꿔 통과시키지 않는다. 함수는 증거 파일을 저장하지 않는다.

## 합성 로컬 예제

저장소 루트에서 Python을 실행한다. 아래 공개 test helper는 새 합성 문장·질문과 사전 라벨을 만들며 parent 검토 API를 실행하지 않는다. 실제 사용자 자료나 retained carrier를 읽지 않는다. SYN 식별자는 규정·방법 정답이 아니다.

```python
from copy import deepcopy
from labflow.intake_test_intent_evaluation import evaluate_intake_test_intent_case
from tests.test_intake_test_intent_evaluation import oracle_cases

cases = oracle_cases()  # 입력과 사전 라벨만 준비한다.
expected = {
    "E01-text": ("checked", "pass", 1),
    "E09-pending": ("not_executed", None, 0),
    "E09-binding": ("insufficient_evidence", None, 0),
    "E10-opposite": ("checked", "fail", 1),
    "E08-sha": ("checked", "pass", 1),
}
for name, wanted in expected.items():
    packet, oracle = deepcopy(cases[name])
    result = evaluate_intake_test_intent_case(**packet, expectation=oracle)
    observed = (result["status"], result["verdict"],
                result["counts"]["review_api_calls"])
    assert observed == wanted
    assert result["counts"]["actual_model_calls"] == 0
    assert result["actual_model_score"] is None
    print(name, observed, result["outcome"])
```

이 예제는 evaluator5회/parent3회다. E08-sha는 예상한 parent source_error와 일치한 계약 pass다. E10-opposite는 유효한 반대 라벨과 실제 결과의 불일치로 fail이다. 각 결과를 의뢰 적합성의 pass/fail로 해석하지 않는다.

로컬 회귀는 `python -B -X utf8 -m unittest tests.test_intake_test_intent_evaluation tests.test_intake_test_intent -v`로 실행한다. 현재 신규 전용22와 parent22의 합44이며 subcase/call/별도 witness 수와 더하지 않는다. 공개 합성 사례와 별도의 독립 reviewer 사례도 구별한다.

## 결과와 실패 읽기

| 상태 | 의미 | parent 호출/계약 분모 | verdict |
|---|---|---|---|
| not_executed | pending 라벨 | 0/0 | null |
| insufficient_evidence | oracle input SHA와 현재 입력 불일치 | 0/0 | null |
| checked | 실제 결과 또는 고정 parent 오류와 비교 완료 | 1/1 | pass 또는 fail |

`outcome.status`는 not_executed/returned/error다. parent 고정 오류는 `test_intent_invalid_input`, `test_intent_limit_exceeded`, `test_intent_source_error` 그대로 outcome.error_code에 남는다. 예상 outcome/code가 다르면 outcome_mismatch다. 질문 전체·후보와 refs 순서·입력 결합11·parent 한도18·검증14/권한12 false·사전 기대값이 다르면 review_mismatch다. parent가 받은 detached 입력을 바꾸면 input_changed와 fail이 남고 호출자 원 입력은 유지된다.

evaluator 자체 입력/예산 문제와 예상 밖 parent 예외는 `IntakeTestIntentEvaluationError`다. code/str/args에는 `intake_test_intent_evaluation_invalid_input`, `intake_test_intent_evaluation_limit_exceeded`, `intake_test_intent_evaluation_source_error` 중 고정 코드만 나오며 원 예외 본문·연결 context를 노출하지 않는다. 잘못된 oracle은 pending으로 흡수하지 않는다. 원문/수치/quote/oracle payload는 결과에 복사하지 않고 input/expectation/review SHA만 결합한다. 안전한 JSON으로 직렬화할 수 없는 parent 반환은 source_error다.

기본 한도는 입력48MiB, oracle256KiB, 반환256KiB, depth40, input+oracle 누적 nodes2,100,000, ID128자, 이유128자/512개다. 기본 native JSON만 허용하고 subclasses/cycles/surrogate/nonfinite를 거절한다. 바이트·깊이·노드 초과는 의미 검사 전에 한도 오류다. 입력 한도의 여유는 parent40MiB/depth32/nodes2,000,000 초과 오류를 비교하기 위한 것이며 parent 한도를 늘리지 않는다.

verification은 caller_label_review_declared/contract_comparison_executed/input_values_unchanged의 실제 검사 범위만 표시한다. 호출 전 branch에서는 input_values_unchanged도 false다. model_execution_verified/model_quality_verified는 항상 false다. context_synthetic과 proposal_origins는 제공자의 선언이다. synthetic 문장에 context_synthetic=false를 적어도 실제 retained 자료가 되지 않으며 model_proposed도 실제 모델 호출 증거가 아니다. 실제 모델 호출은 전 경우0, actual_model_score는 null이다.

원 의뢰 질문·모순과 규정/방법 partial query null은 유지된다. 날짜·기관/업무 scope·권리·edition 미확인을 최신 규범·기관 적용성·SDK 지원으로 승격하지 않는다. 보고서 issue/issuer/mirror와 복합 원필드·fact_id를 별도 규범 사실로 바꾸지 않는다. 실제 retained metadata/원문/실측값을 공개 fixture/usage/정답에 넣지 않는다. 독립 배정·실제 AI 품질·실물/현장·전체 시험소 검증은 별도 남은 범위다.
