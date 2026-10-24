# 의뢰 규정·방법 모델 입력·응답 경계

이미 메모리에 있는 **명시적 합성 view**를 prompt로 만들고, 제공된 raw JSON 응답의 request/producer·선택 주소를 확인한다. [공개 설계](../superpowers/specs/2026-10-25-intake-test-intent-model-boundary-design.md)와 [구현 계획](../superpowers/plans/2026-10-25-intake-test-intent-model-boundary.md)의 순수 API2다. 실제 모델·SDK·전송·학습·계정·키·과금 설정을 요구하거나 실행하지 않는다.

```text
build_intake_test_intent_prompt(intake_view, source_views, *, scope, producer_name)
decode_intake_test_intent_response(response, intake_view, source_views, *, scope, producer_name)
```

## 준비와 원본 관계

호출자는 원 full intake/source를 그대로 보관하고 메모리에서 view를 선택한다. intake_view의 정확6키는 synthetic=True, analysis_schema_version, origin_binding, facts, current_facts, questions다. fact_index/evidence_index는 원 analysis의0-based 주소이며 선택 배열 위치가 아니다. quote·질문 전체와 상대 순서를 보존하고 current_facts는 원 value/status만 복사한다. event_id/lease/위임/원 operator·전체 documents/원 binary·oracle/holdout을 prompt에 넣지 않는다. 선택된 source13은 원 metadata11과 extraction_status/pages이며 자동 loader나 문서 선택은 없다.

origin_binding4는 caller가 원 full intake/analysis/projection/sources 각각의 canonical SHA를 제공한 선언이다. 라이브러리는 원본 preimage를 받지 않으므로 origin_binding_verified는 false다. 실제 chain에서는 caller가 원본 hash와 선택 row/page/질문의 동일성을 먼저 대조한다. 날짜·권리·source status·기관/WF 충돌은 그대로 보존하며 현재 규범·권한으로 올리지 않는다.

scope의 as_of/institution_scope/workflow_scope_id는 모두 null을 허용하고 기본값을 넣지 않는다. producer_name은 유효 UTF-8/nonblank str≤200의 공개 label이며 실제 공급자·모델/계정 ID의 확인이 아니다. caller는 허용 정보만 제공한다. whitelist가 quote/name 안의 비밀 내용을 탐지·익명화하지는 않는다.

## B0/B1 순수 wire 예제

저장소 루트에서 실행하는 합성 예제다. zero origin SHA는 허구 선언이며 원본/현재성 증거가 아니다. 아래 request/response 기대값은 API 실행 전 공개 계약에 고정됐다. 모델을 호출해 응답을 만든 것이 아니다.

```python
import json
from labflow.intake_test_intent_model_boundary import (
    build_intake_test_intent_prompt, decode_intake_test_intent_response,
)

origin = {k: "0" * 64 for k in (
    "provided_intake_sha256", "provided_analysis_sha256",
    "provided_projection_sha256", "provided_sources_sha256",
)}
view = dict(synthetic=True, analysis_schema_version=1, origin_binding=origin,
            facts=[], current_facts={}, questions=[])
scope = dict(as_of=None, institution_scope=None, workflow_scope_id=None)
request_sha = "3d019cc2553ad6febff444fc0f722634003cc51fe3bf697f183c14271dd3cdd3"
response = dict(schema_version=1, kind="intake_test_intent_model_response",
                request_sha256=request_sha,
                producer={"kind": "model", "name": "wire-synthetic-v2"},
                fields={"rule": [], "method": []})
body = json.dumps(response, ensure_ascii=False, sort_keys=True,
                  separators=(",", ":"), allow_nan=False).encode("utf-8")
prompt = build_intake_test_intent_prompt(
    view, [], scope=scope, producer_name="wire-synthetic-v2")
assert prompt["binding"]["request_sha256"] == request_sha
decoded = decode_intake_test_intent_response(
    body, view, [], scope=scope, producer_name="wire-synthetic-v2")
assert decoded["proposal"] == dict(scope, fields={"rule": [], "method": []})
assert decoded["verification"]["reference_scope_checked"] is False
assert decoded["verification"]["model_execution_verified"] is False
print(decoded["kind"], decoded["proposal"])
```

이 예제의 실행 수는 builder1/decoder1·parent/evaluator0이다. 파일이나 원문을 읽지 않는다.

## 실제 합성 caller chain

다음 로컬 test helper는 새 합성 메모리 입력과 사전 wire/semantic oracle을 준비한다. 고객 자료나 모델을 사용하지 않는다. text 추출은 두 경계 함수 밖의 host 준비 단계다.

```python
from labflow.intake_test_intent_model_boundary import (
    build_intake_test_intent_prompt, decode_intake_test_intent_response,
)
from labflow.intake_test_intent_evaluation import evaluate_intake_test_intent_case
from tests.test_intake_test_intent_model_boundary import chain_oracles, raw, sha

case = chain_oracles()["C1-normal"]  # 원본·선택·사전 기대 준비
params, original = case["params"], case["original"]
assert params["intake_view"]["origin_binding"]["provided_intake_sha256"] == sha(original["intake"])
prompt = build_intake_test_intent_prompt(**params)
decoded = decode_intake_test_intent_response(raw(case["wire"]), **params)
packet = dict(original, proposal=decoded["proposal"])
expectation = dict(schema_version=1, kind="intake_test_intent_case_expectation",
                   case_id="USAGE-PINE", case_group_id="SYN-PINE-GROUP",
                   input_sha256=sha(packet), label_review_status="reviewed",
                   expected=case["parent_expected"])
result = evaluate_intake_test_intent_case(**packet, expectation=expectation)
assert result["verdict"] == "pass"
assert result["counts"]["review_api_calls"] == 1
assert result["counts"]["actual_model_calls"] == 0
assert result["actual_model_score"] is None
print(result["status"], result["verdict"], result["counts"])
```

두 예제를 각각 실행한 총수는 builder2/decoder2/evaluator1/parent1이다. 원 semantic 기대는 먼저 준비하며 proposal 포함 input SHA는 응답 뒤 별도로 결합한다. 실제 모델 후보 선택 품질 점수로 해석하지 않는다. 실제 자료의 origin/선택 검토를 helper 하나가 자동 보증하는 운영 흐름은 아니다.

## 검증 범위와 오류

prompt7/binding5와 decoded7/binding6은 정확 DTO다. request SHA는 self-reference 없는 canonical R의 hash이고, response hash는 **제공 bytes 전체**(허용 공백 포함)의 SHA다. provider stream의 완결·출처 증명은 아니다. source/배열·quote/줄끝·scope null을 바꾸지 않는다.

decoder는 원주소 membership과 제공 page hash까지 확인한다. source text의 실제 hash/span/행범위·literal/role·날짜/규범 적용성은 기존 [근거 대조](intake_test_intent_usage.md)가 담당한다. wire가 통과해도 source_error나 미연결 검토가 나올 수 있다. 부모를 helper 내부에서 호출하지 않는다. [계약 평가](intake_test_intent_evaluation_usage.md)는 제공 proposal의 검토 계약을 비교하며 실제 AI 정답률을 재지 않는다.

고정 오류 class는 IntakeTestIntentModelBoundaryError다. code/str/args는 `intake_test_intent_model_` 뒤 아래 suffix를 붙인 고정 문자열만 가지며 원 입력·예외 context를 노출하지 않는다.

| suffix | 의미 |
|---|---|
| invalid_input | view/source/native JSON 형상·extra key·cycle/subclass·Unicode·중복 주소 오류 |
| input_not_synthetic | synthetic=False |
| scope_invalid / producer_invalid | caller scope 또는 producer 이름 오류 |
| response_invalid | raw UTF8/JSON·중복·NaN·wire 형상·origin 위장 오류 |
| response_binding_mismatch / response_producer_mismatch | 현재 인자로 재계산한 request/producer와 다름 |
| response_scope_mismatch | 선택하지 않은 fact/evidence·doc/page/hash |
| limit_exceeded | bytes/depth/nodes/signed64·구조 cap 초과 |
| internal_error | 예상 밖 구현 Exception |

한도8은 input/prompt 각8MiB, raw response64KiB, decoded128KiB, depth32(root0), nodes200000, signed64 min/max다. decoder node는 A+parsed wire를 누적하며 파생 output 사본은 별도로 제한한다. raw cap을 parsed JSON의 canonical 크기에 다시 적용하지 않는다. error/unknown을 fixture 응답으로 대체하거나 줄을 잘라 성공시키지 않는다. raw bytes와 실패·source/oracle hash는 caller의 새 private 경로에 보존하고 이 함수는 파일을 쓰지 않는다.

input_shape_checked·JSON/request/producer 결합은 해당 실제 검사만 표시한다. reference_scope_checked는 실제 refs 비교가1개 이상인 경우에만 true다. origin/grounding/source 진위·현재성/권리/model 실행·품질/외부송신·실행9 flags는 항상 false다. donor의 model_proposed/producer=model은 선언이다. 실제 모델·학습·계정/비밀환경·전송/과금·실장비와 독립 품질 평가는 이번 범위에서 미실행이다.

로컬 관련 검사는 `python -B -X utf8 -m unittest tests.test_intake_test_intent_model_boundary tests.test_intake_test_intent tests.test_intake_test_intent_evaluation -v`다. 현재 전용23+parent22+evaluator22=67이며 별도 실제 caller chain9·mock 반증·usage2와 중복 합산하지 않는다.
