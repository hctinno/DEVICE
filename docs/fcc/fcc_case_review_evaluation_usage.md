# FCC 사례 참조 fixture 평가 게이트029

2026-10-24 Asia/Seoul. 총괄이 고정한 계약이다. 아래 실행 검사는 fixture 참조 선택 경계에 한정하며 실제 모델·현장 평가를 뜻하지 않는다.

## 소유권과 선행

- 신규 소유 파일은 `labflow/fcc_case_review_evaluation.py`, `tests/test_fcc_case_review_evaluation.py`, `docs/fcc/fcc_case_review_evaluation_usage.md` 세 개다.
- 선행 `e209d46bbebf0a046169be5056b77c4bcc510f42`를 보존하고 전용 브랜치 `codex/dev2-case-review-eval029-20261024`를 사용한다. 025 독립 리뷰는 Yes/Critical·Important 0건으로 인수됐다.
- 022 소스/사용법/실제 미배정 결과, 021·025 소스와 원래 실패/검증 원본은 수정하지 않는다. 다른 owner/P01 메시지·새 하위 에이전트·전체 브랜치 merge는 없다.
- 이번 단위는 순수 `fixture_reference_check`다. 모델/훈련/Store/파일/PDF/네트워크/장비/외부 송신 호출은 없다. 원문·그룹·기대 label의 진위를 새로 인증하지 않는다.

## 단일 API

```python
evaluate_case_review_references(
    split, context, validated_response, *, expectation, producer_name
) -> dict
```

`split`은 기존 022 출력 DTO, `context`는 025 context, `validated_response`는 025 decoder 출력이다. 경로·catalog·callable·임의 객체는 받지 않는다. JSON 기본 내장 타입을 제한 예산 안에서 복사하고 caller 입력을 수정하지 않는다. 모든 출력은 새 JSON 값이다.

`producer_name`은 025의 기대 producer 선언을 일치시키는 문자열이다. 실제 모델을 실행했다는 증거로 사용하지 않는다.

### expectation 정확 5키

```json
{
  "schema_version": 1,
  "kind": "fcc_case_review_expectation",
  "context_id": "<025 context_id>",
  "label_review_status": "reviewed",
  "references": []
}
```

`label_review_status`는 `reviewed|pending`이다. `pending`의 미확인 참조는 `null`로 남길 수 있다. `reviewed`의 비어 있는 집합도 자동 정답으로 만들지 않고 부족으로 둔다. 점수 대상 기대값은 caller가 명시적으로 검수했다고 선언한, 동일 ready context의 비어 있지 않은 선택 참조 집합이다. 기대 abstention·빈 정답의 평가는 이번 범위에 추가하지 않는다.

각 참조는 기존 025와 같은 정확 9키다: `case_id, claim_id, evidence_id, document_id, source_sha256, file_page, text_sha256, line_start, line_end`. 중복은 제거해서 통과시키지 않는다. 이 9키 외 정답 값·규격 판정·점수·fold·명령은 받지 않는다.

## 게이트 순서와 일관성

1. 입력 타입·정확 키·유한 수·문자열·깊이·바이트·노드를 검사한다. bool과 int를 동일하게 취급하지 않고, 사용자 정의 메서드·객체 변환을 실행하지 않는다.
2. 022의 각 case에서 원래 8키와 development/independent case 선택을 꺼내 **기존 공개 `build_case_evaluation_split`**을 다시 호출한다. 결과 전체와 전달된 split을 canonical JSON 바이트로 대조한다. component, group ID, 분모, eligible, fingerprint 또는 배정 label만 편집해도 점수 부족이다. 022에 새 사실 검수 기능을 추가하지 않는다.
3. 025 validated DTO의 정확 10키에서 기존 wire 7키를 재구성해 **기존 공개 `decode_case_review_response`**로 context와 response를 다시 검사한다. decoder 전체 결과와 validated DTO 전체가 같아야 한다. producer/corpus/source_binding/verification도 바꿀 수 없다. private helper 또는 새 source/code 무결성 체계는 쓰지 않는다.
4. expectation의 context_id가 정확히 같고 reviewed/nonempty인 경우, 같은 공개 decoder에 `selected`, 동일 producer, 기대 참조, 빈 reason_codes를 넣어 기대 참조가 모두 해당 context의 selectable evidence인지 확인한다. 정답을 추론하거나 임의 reference를 보충하지 않는다. 기대 label의 실제 정확성은 caller의 별도 책임으로 남긴다.
5. 아래 전체 노출 게이트를 수행한다. context가 `ready`가 아니거나 `synthetic`이 true가 아니면 점수 부족이다.
6. 모든 게이트가 통과했을 때만 기대/관측 참조의 **9키 전체의 순서 없는 정확 집합**을 비교한다. 일치하면 score=1, 다르면 score=0이다. 정상 검증된 `insufficient_evidence` 응답은 관측 참조가 비어 있으므로 이 비어 있지 않은 기대 집합과 비교하면 fixture score=0이다. 참조 자체가 잘못되면 0점으로 계산하지 않고 score=null이다.

### 전체 노출 게이트

- 명시 노출 V는 `cases`, `requested_case_ids`, `case_previews`, `excluded_candidates`, source_binding의 case 항목에 등장한 모든 case ID의 합집합이다. 선택하지 않은 preview/excluded case도 포함한다.
- 문서 연계 D는 context의 **모든 documents SHA**를 original_sha256s에 가진 022 case 전체다. E=V∪D를 노출 범위로 기록한다. 새 case나 원문 관계를 생성하지 않는다.
- context의 모든 preview 문서 ID는 context.documents에 있어야 한다. 모든 context document는 적어도 한 preview에 연결되어야 한다. preview의 연결 SHA는 해당 동일 case의 022 original_sha256s에 포함되어야 한다. preview의 비어 있지 않은 report_group_id와 FCC ID 집합은 022와 기존 정규화 규칙으로 일치해야 한다. product_family 문자열을 canonical group ID로 추론하지 않으며 reuse 관계도 만들지 않는다.
- E의 모든 case가 022에 있어야 하고, 022 재계산 결과에서 eligible이며 independent로 배정되어야 한다. development/unassigned/ineligible case가 하나라도 있으면 부족이다.
- E가 건드린 모든 022 연결성분의 **전체 case가 context.case_previews에 명시**되어야 한다. 일부 case만 preview로 노출하고 같은 SHA 또는 재사용 연결을 통해 나머지를 숨겨 통과할 수 없다. 하나 이상의 연결성분 전체를 포함할 수 있으며, 노출하지 않은 독립 성분까지 모두 넣도록 요구하지 않는다.
- component의 group_review_status/reuse/canonical 사실은 022의 caller 검수 선언이다. 일관성을 확인한 것을 사실 검증 또는 독립 평가 승인으로 승격하지 않는다.

## 출력 정확 15키

```text
schema_version, kind, execution_mode, status, reason_codes, synthetic,
bindings, exposure, label_review_status, score, actual_model_score,
counts, reference_differences, verification, limits
```

- schema_version=1, kind=`fcc_case_review_reference_check`, execution_mode=`fixture_reference_check`.
- status=`checked|insufficient_evidence`. checked일 때만 score가 정수 0 또는 1이고 reason_codes=[]이다. 부족일 때 score=null이며 fixture 비교를 실행하지 않는다. `actual_model_score`는 언제나 null이다.
- synthetic은 025 context 재검증에 성공하면 원래 bool이며, context 자체를 재검증하지 못한 경우 null이다. label_review_status는 caller의 `reviewed|pending` 선언이다.
- bindings 정확 8키: `split_sha256, split_input_fingerprint, context_sha256, context_id, corpus_id, response_sha256, expectation_sha256, expected_producer`. 입력 4개 SHA는 각각 제한 복사한 전체 canonical JSON 해시다. 검증 실패한 fingerprint/context_id/corpus_id는 null이다. expected_producer는 기존 025 정확 2키 `{kind:model,name:producer_name}`이다.
- exposure 정확 4키: `case_ids, document_linked_case_ids, required_component_case_ids, component_ids`. 모두 정렬한 중복 없는 ID 배열이다. context/split 재검증 실패로 계산할 수 없으면 해당 배열은 빈 배열이며 status/verification으로 미실행을 구별한다.
- counts 정확 7키: `expected_references, observed_references, matched_references, missing_references, unexpected_references, scored_fixture_checks, actual_model_checks`. 처음 5개는 checked일 때만 집계하고 부족일 때 null이다. scored_fixture_checks는 checked일 때 1, 아니면 0이다. actual_model_checks는 언제나 0이다. 실제 사례의 미배정 수를 모델 분모에 넣지 않는다.
- reference_differences 정확 2키: `missing, unexpected`. checked일 때에만 정렬한 원래 9키 reference 배열이고, 부족일 때는 비교 미실행으로 각각 빈 배열이다. 원문 quote/value/basis를 결과에 복제하지 않는다.

### verification 정확 16키

```text
split_dto_recomputed
context_response_revalidated
expectation_references_validated
whole_independent_exposure_eligible
caller_label_review_declared
fixture_reference_check_executed
source_facts_reverified
group_facts_reverified
label_correctness_verified
model_execution_verified
model_quality_verified
independent_evaluation_approved
training_executed
evaluation_executed
hardware_verified
physical_verified
```

처음 6개만 해당 검사 결과/명시 선언에 따라 true가 될 수 있다. 나머지 10개는 항상 false다. expectation_references_validated는 label 사실 검수가 아니라 같은 context 참조 membership 확인이다. whole_independent_exposure_eligible도 입력 metadata에 한정한다. fixture 검사를 실행해도 evaluation_executed는 실제 모델 평가의 의미로 false를 유지한다.

## 예산 — limits 정확 14키

| 키 | 값 |
|---|---:|
| max_split_bytes | 16777216 |
| max_context_bytes | 8388608 |
| max_response_bytes | 327680 |
| max_expectation_bytes | 262144 |
| max_output_bytes | 4194304 |
| max_split_depth | 12 |
| max_context_depth | 24 |
| max_response_depth | 16 |
| max_expectation_depth | 12 |
| max_output_depth | 16 |
| max_nodes | 4500000 |
| max_split_cases | 4096 |
| max_exposed_cases | 4352 |
| max_references | 256 |

각 입력은 별도로 바이트/깊이를 제한하고 합계 노드는 4,500,000 이하로 제한한다. 기존 022/025의 유효 값·목록·긴 preview를 임의의 더 작은 제한으로 줄이지 않는다. context의 selected16/preview128/doc16 등 기존 제한은 025 공개 decoder가 확인한다. 노출 상한 4352는 022 최대4096과 025 preview/excluded 최대256의 합이다. parent의 limit 오류도 고정 limit_exceeded로 전달한다.

## 부족 reason_codes와 고정 오류

부족 reason_codes는 아래 enum의 정렬/중복 제거된 배열이다. 수행 가능한 게이트에서 확인된 이유만 기록하며 context/split 검증 실패 뒤 임의 구조를 신뢰해서 후속 성공을 만들지 않는다.

```text
split_not_consistent, context_not_validated, response_not_bound,
expected_context_mismatch, expected_references_not_bound,
label_review_pending, expected_references_missing, context_not_ready,
empty_exposure, unknown_exposed_case, unlinked_context_document,
document_source_mismatch, report_group_mismatch, fcc_id_mismatch,
partial_component_exposure, development_case_exposed,
unassigned_case_exposed, ineligible_component_exposed,
non_synthetic_context
```

JSON 기본 타입/정확키/원시 스칼라 형식/enum 등이 아닌 입력과 예산 초과는 `FccCaseReviewEvaluationError(ValueError)`로 거절한다. `.code`, str, args에는 아래 고정 코드만 남기고 원문/암호/경로/exception chaining을 내보내지 않는다.

```text
fcc_case_review_evaluation_input_invalid
fcc_case_review_evaluation_split_invalid
fcc_case_review_evaluation_context_invalid
fcc_case_review_evaluation_response_invalid
fcc_case_review_evaluation_expectation_invalid
fcc_case_review_evaluation_producer_invalid
fcc_case_review_evaluation_limit_exceeded
```

형식상 올바르지만 다른 context/claim/evidence/SHA/page/line을 가리키는 참조, pending label, 재계산 불일치 split, 게이트 미충족은 예외로 점수를 잃어버리게 하지 않고 부족 DTO와 score=null로 반환한다. raw 참조 중복도 부족이며 자동 중복 제거하지 않는다. 예산 오류는 부족으로 삼키지 않는다.

## RED와 수용 조건

1. 합성 genuine 021 catalog→025 공개 builder/decoder→022 공개 builder→029를 연결한다. 정확 일치1, 동일 context의 유효한 누락/추가 참조0, 참조 순서 변경 불변을 확인한다. 임의 live catalog private state/method 대체는 없다.
2. 022의 원문 SHA/FCC/report/canonical/reuse 전이 연결이 각기 dev case 또는 pending case로 이어지는 leak, partial independent 편집, eligible/그룹/분모/fingerprint 편집을 거절한다.
3. 선택 case는 independent여도 nonselected preview/excluded/document-linked case가 dev/unassigned/ineligible/unknown이면 score=null이다. preview 없는 문서·다른 SHA·report/FCC 불일치·일부 성분 노출을 각각 검사한다.
4. expectation pending/null/빈 목록, context_id 또는 9개 참조 필드 각각의 교체, 다른 case 같은 문서, 다른 claim 같은 줄, 중복 참조를 부족으로 유지한다. 원문 기반 임의 정답은 생성하지 않는다.
5. validated response의 context/corpus/producer/source_binding/flags를 바꾸거나 문맥의 hash/metadata/검토 상태가 달라지면 점수 부족이다. 정상 보수적 abstention은 fixture 불일치와 잘못된 참조를 구분한다.
6. 실제 022 S03/B001 미배정 결과와 025 보존 context/합성 response JSON을 **재생**한다. score=null/scored_fixture_checks0/actual_model_checks0/actual_model_score=null을 확인한다. 원문 PDF 새 읽기/복사/재파싱0이다. S05는 총괄이 고정 인계한 기존 JSON이 있을 때만 같은 부족 회귀에 추가하며 없는 metadata/label을 만들지 않는다.
7. 기본 타입 거절·정확키·NaN/Infinity·bool정수·깊이/노드/바이트/참조256 경계·기존025긴 preview/claim 값 보존·input/output detach·결정성·정적 구문·영문 고정 오류/원문 비노출을 확인한다. 파일/PDF/소켓/subprocess/모델 client 호출 spy0을 별도 기록한다.
8. 신규 전용 및 관련 021/022/025/intake_model_boundary 회귀, 문서 check_artifacts와 신규 usage UTF-8/링크 확인을 실행한다. 실패/RED/실제 재생 ledger를 private 새 경로에 보존한다. 실장비/현장/실제 모델 평가는 미실행으로 남긴다.
9. 승인된 소유 3파일만 commit/push/원격 full SHA 대조 뒤 독립 일반 데이터 기능 리뷰로 넘긴다. 최종 공통 통합/게시 권한은 총괄이다.

이 계약은 전체 무인시험소, 원문 해석 정확도, 독립 평가 모집단 또는 모델 품질의 검증 증거를 생성하지 않는다.

선행 계약: [022 연결성분/배정](fcc_case_evaluation_usage.md), [025 문맥/참조](fcc_case_review_usage.md).

## 소유 검증 결과

2026-10-24 전용 35개와 부모 관련 회귀를 합한 167개 검사가 13.685초에 통과했고 skip은 0개다. 256개 유효 참조, 참조 집합 차이, 전체 성분/비선택 사례 노출, 부모 예산 오류 전달, 450만 합계 노드 한도, 입력 사본/고정 오류/무I/O를 포함한다. 기존 021·022·025 소스 해시는 불변이다.

실제 S03의 보존 JSON 13파일을 읽어 6개 문맥을 재생했다. 2개 사례는 검수 대기·ineligible·전체 미배정을 유지하며 모든 결과의 score와 actual_model_score는 null, scored_fixture_checks와 actual_model_checks는 0이다. 기대 label은 pending/null을 유지했고 정답을 생성하지 않았다. 원본 해시·크기·수정 시각·mode가 불변이고 새 PDF 읽기/복사/파싱과 API 파일/PDF/소켓/프로세스 호출은 0이다. Caller의 JSON 준비·불변 대조 읽기 26회는 API 실행과 별도다. 이 재생은 기존 실제 자료에 대한 합성 응답 검사이며 실제 모델 평가가 아니다. S05는 이 단위에 고정 인계된 입력이 없어 재생하지 않았다.

독립 리뷰와 공통 통합 회귀는 소유 검증과 별도 단계다. 실제 모델 호출·훈련·평가·실장비·현장 검증은 미실행이다.
