# 접수 snapshot과 참고 사례 응답032

2026-10-24 Asia/Seoul. 총괄이 고정한 순수 접수 snapshot/reference 결합 계약이다. 실행 권한·DB 현재성·모델 평가와 구별한다.

## 소유권·API·범위

선행은 029 `ec653603f9a2a95ed9be26fcf09ebeaaaee0c7f6`다. 독립 최종 Yes/C·I0, root 영수증 SHA `c1452da7e2a1fe866ff2ef3a792131ece1a5ad127a18b350c108e3b63dd3f2fc`를 별도로 보존했다. 02935/owner 관련167/실패·실제JSON·부모 pin은 그대로 유지한다. 총괄015 인수 여부는 별도이며 014 게시와 혼합하지 않는다.

전용 `codex/dev2-intake-case-references032-20261024`, 신규 소유 파일은 아래 3개만 소유한다.

- `labflow/intake_case_references.py`
- `tests/test_intake_case_references.py`
- `docs/fcc/intake_case_references_usage.md`

```python
build_intake_case_reference_receipt(
    intake_snapshot, catalog, case_context, validated_response, *, producer_name
) -> dict
```

정확 `FccReportCaseCatalog` 객체와 caller가 전달한 JSON DTO만 받는다. 경로/packet/Store/callback/subclass/duck 객체는 받지 않는다. catalog 구성과 자료 읽기는 caller 준비 단계다. 032 API는 021 `match_intake`, 025 context builder/decoder의 공개 API를 사용하며 파일/PDF/DB/네트워크/프로세스/모델/장비 I/O 0이다. private state/method 대체나 코드 무결성 프레임워크를 추가하지 않는다.

첫032는 **029 평가 입력/expectation/fold/score 계산 인수를 받지 않는다.** 평가 상태는 미실행/null로 고정한다. worker·Store·schema·queue·질문·알림·위임·fixture 권한은 변경하지 않는다.

## intake_snapshot — 정확 13키

```json
{
  "schema_version": 1,
  "kind": "intake_case_reference_snapshot",
  "snapshot_scope": "caller_provided",
  "intake_id": null,
  "revision": null,
  "revision_fingerprint": null,
  "origin_job_id": null,
  "analysis_context_id": null,
  "result_sha256": null,
  "readiness_fingerprint": null,
  "synthetic": null,
  "projection": {"facts": {}, "questions": []},
  "projection_sha256": "<canonical projection SHA256>"
}
```

핵심 출처 7개 `intake_id, revision, revision_fingerprint, origin_job_id, analysis_context_id, result_sha256, synthetic`와 projection 일관성을 검사한다. `readiness_fingerprint`는 선택적 추가 출처다. 핵심7 중 null이 있으면 `snapshot_binding_incomplete`로 유지한다. 기존 결과에 해당 정보가 없다고 ID/시각/revision을 새로 만들지 않는다.

- intake_id/origin_job_id는 null 또는 기존 Store identifier와 같은 ASCII `[A-Za-z0-9][A-Za-z0-9_.-]{0,149}`다. revision은 null 또는 bool 아닌 양의 int다.
- revision_fingerprint/analysis_context_id/result_sha256/readiness_fingerprint는 null 또는 소문자 hex SHA64다. synthetic은 null 또는 정확 bool이다.
- result_sha256은 기존 완료 job의 **원래 result_json UTF-8 bytes** 해시를 caller가 전달한다. 현재 summary를 다시 직렬화해 origin result 해시라고 하지 않는다.
- readiness_fingerprint가 null이어도 참고 읽기만을 막지는 않는다. 이 단위는 readiness/DB 현재성/실행 권한을 새로 검증하지 않는다.
- projection_sha256은 nonnull SHA64이며 아래 최소 projection 전체의 canonical JSON 해시와 같아야 한다. 일관성 해시이며 source result→projection 관계를 인증하지 않는다.
- 다른 revision의 같은 사실도 caller가 별도로 제시할 수 있다. receipt는 서로 다른 snapshot/receipt 해시로 구별한다. 이 순수 API는 어느 revision이 실제 DB의 current인지 판정할 수 없고, caller가 잘못 기재한 원본 메타데이터의 진위도 알아내지 않는다.

### projection 정확 2키

`{facts, questions}`다. Caller는 기존 `project_analysis` 또는 보존 `intake_status.analysis`의 projection에서 아래 최소 부분만 복사한다. 원본 full projection/result와 이 최소 복사본은 caller가 별도로 보존한다. submitted analysis·원문·인용·토큰을 snapshot에 덧붙이지 않는다.

- facts는 `product_type, market, model`의 부분집합만 갖는 dict(최대3)다. 모르는 fact는 생략한다. fact 정확키는 `{value,status}` 또는 `{value,status,event_id}`다. value는 nonempty text 최대4000자, status는 `explicit|inferred|uncertain|user_confirmed`다. user_confirmed는 event_id가 필수이며 event_id는 기존021 ID(ASCII128) 또는 bool 아닌 양의 int다. 값은 검증된 결과를 줄여 전달한 caller 입력이며 source facts의 재검증이 아니다.
- questions는 최대200개 `{key}` 정확1키 dict의 배열이다. key는 부모021 plain JSON 한도 안의 string(최대1MiB)을 그대로 받는다. question message/values/paths는 전달하지 않는다. `product_identity` 등 원래 key는 보존하며 이유를 임의로 해결하지 않는다.
- 시장·목적을 참고 성적서에서 추론하지 않는 기존 projection 경계는 유지한다. product_type/market/model의 explicit/user_confirmed만 기존021 `match_intake`가 사용하고 inferred/uncertain은 확인된 값이 되지 않는다.
- 이 최소 projection으로 전체 접수 준비 상태나 질문·답변의 원본 basis를 재구성했다고 주장하지 않는다.

## 부모 재검증과 결합 순서

1. JSON 기본 내장 타입·정확키·유한 수·byte/depth/node를 제한하고 snapshot/context/response 전체를 사본으로 분리한다. 원문이나 callback의 사용자 메서드를 실행하지 않는다. producer_name은 기존025와 같은 nonempty string≤200자다.
2. 정확 catalog에 025 공개 `build_case_review_context(catalog, query=case_context.query, case_ids=case_context.requested_case_ids)`를 호출한다. **전체 새 context와 전달된 context의 canonical bytes가 같아야 한다.** catalog/query/선택/preview/doc/source binding/검증 flags가 하나라도 다르면 `case_context_mismatch`이고 검증하지 않은 case/claim 내용을 결과로 복제하지 않는다. 부모의 정상 값/예산은 축소하지 않는다.
3. 전달된 validated response 정확10키를 기존025 wire7키로 재구성해 공개 decoder를 호출하고 전체 validated DTO와 대조한다. context/corpus/producer/source binding/flags/reference9키/중복/상태가 달라지면 `case_response_not_bound`다. parent limit 오류는 반드시 고정 limit 오류다.
4. projection 해시가 맞고 case context가 재결합됐으면 정확 catalog의 `match_intake(projection, case_context.query)`를 호출한다. 원래 status/reason_codes/model_relation을 보존한다. 이 호출이 snapshot의 DB 현재성/진위/권한을 보증하지는 않는다.
5. intake match status=`candidates`의 `exact_model|unspecified` case만 **이번 접수에서 reference로 결합할 수 있는 case 집합**으로 둔다. `related_family`는 제외하고 원래 이유를 남긴다. `no_match`는 해당 query/catalog에 후보가 없다는 유효한 읽기 결과다. `insufficient_evidence`는 `intake_query_insufficient`다.
6. source response=`selected`일 때 모든 reference의 case가 위 집합에 있어야 한다. 하나라도 밖이면 `selected_reference_outside_intake_scope`로 전체 결합을 보류하고 accepted references=[]다. 일부만 조용히 남기지 않는다. 미선택/preview 관련 사례가 있다는 이유만으로 올바른 다른 선택을 지우지는 않는다. 029 전체 평가 노출 게이트를 운영 참조 권한으로 재사용하지 않는다.
7. 모든 핵심 결합 조건을 만족하면 status=`bound`다. 이는 **provided snapshot과 참고 응답의 일치**이며 준비/실행 승인이 아니다. 유효한 no_candidate/보수적 insufficient 응답도 source와 snapshot 연결 자체는 bound일 수 있으며 선택 상태는 별도로 no_candidate/unknown이다. 이 경우에도 기존 업무를 complete/fail/진행시키지 않는다.

**중요한 model=None 경계:** 025 `search(query)`가 model 미지정으로 허용한 case라도 021 `match_intake`는 접수에서 확인된 model을 사용해 related_family로 분류할 수 있다. 이 경우 해당 reference를 current model용으로 결합하지 않는다. 반대로 query와 접수 모두 model 미지정이면 unspecified 범위를 그대로 두고 exact model 검증을 만들어내지 않는다.

## 출력 정확 14키

```text
schema_version, kind, receipt_id, execution_mode, status, reason_codes,
intake_binding, case_binding, intake_match, reference_selection,
case_states, evaluation, verification, limits
```

schema_version=1, kind=`intake_case_reference_receipt`, execution_mode=`provided_snapshot_read_only`, status=`bound|insufficient_evidence`다. receipt_id는 이 키 자체를 제외한 전체 output의 canonical SHA다. 입력 값이 같으면 결정적이며 반환/입력을 서로 수정해도 영향을 주지 않는다.

### intake_binding 정확 11키

```text
intake_id, revision, revision_fingerprint, origin_job_id,
analysis_context_id, result_sha256, readiness_fingerprint,
projection_sha256, snapshot_sha256, synthetic, missing_fields
```

앞의 출처 값은 caller 선언 그대로, snapshot_sha256은 전체 snapshot 해시다. missing_fields는 null인 핵심7 필드 이름만 정렬한 배열이다. source full result/DB에서 다시 확인했다고 하지 않는다.

### case_binding 정확 10키

```text
provided_context_sha256, provided_response_sha256, context_id, corpus_id,
source_binding, query_sha256, producer, catalog_synthetic,
context_status, search_status
```

provided 2개 SHA는 전체 입력의 해시, producer는 기존025 `{kind:model,name:producer_name}` 선언이다. context가 재결합됐을 때만 context_id/corpus_id/source_binding/query_sha256/catalog_synthetic/context_status/search_status를 채우고 아니면 null로 둔다. source_binding은 기존025 정확3키를 그대로 보존한다. query의 raw model/family/rule/method 값은 요약에 복사하지 않는다. intake synthetic과 catalog synthetic을 서로 승격하거나 하나로 합치지 않는다.

### intake_match 정확 5키

`status, reason_codes, matched_case_ids, admitted_case_ids, fact_statuses`다.

- status는 원래 `candidates|no_match|insufficient_evidence`, 미검사면 `not_assessed`다. 부모 원래 reason_codes를 정렬해 보존하고 원문 메시지는 붙이지 않는다.
- matched_case_ids는 원래 match의 전체 case ID, admitted_case_ids는 candidates 상태에서 exact_model/unspecified인 ID만 정렬한다. 이 admitted는 **독립 평가 eligible**라는 뜻이 아니다.
- fact_statuses는 `product_type,market,model` 정확3키의 원래 status 또는 null이다. 확인된 fact value는 출력하지 않는다. 미검사면 ID 배열/이유는 []이고 status 값은 모두 null이다.

### reference_selection 정확 5키

`status, source_response_status, source_reason_codes, accepted_references, reported_reference_count`다.

- status=`selected|unknown|no_candidate`. 전체 receipt가 bound이고 유효한 selected 응답이면 selected/정확9키 참조들을 반환한다. 유효한 no_candidate이면 no_candidate/[]다. 보수적 insufficient 또는 결합 부족이면 unknown/[]다.
- source_response_status/reason_codes는 재검증에 성공한 원래 응답의 상태/이유다. 실패면 null/[]다. 다른 이유를 모델이 말했다고 꾸미지 않는다.
- reported_reference_count는 재검증된 원래 응답의 수이며 실패면 null이다. accepted와 다를 수 있고 그것을 자동 모델 실패율로 집계하지 않는다.
- reference9키는 `case_id,claim_id,evidence_id,document_id,source_sha256,file_page,text_sha256,line_start,line_end` 그대로다. quote/value/unit/basis·도구·점수는 복제하지 않는다.

### case_states — 최대128행, 각 정확 8키

```text
case_id, context_inclusion, context_exclusion_reason, context_model_relation,
intake_model_relation, response_membership, selection_status, reason_codes
```

검증된 context의 모든 preview를 case_id 순서로 반환한다. context 자체가 불일치하면 []다.

- context_inclusion=`detailed|preview_only`. context_exclusion_reason은 원래 `not_selected|related_model|query_insufficient|null`을 보존한다. 원래 excluded의 not_selected는 **caller의 context 상세 선택**이다.
- context_model_relation/intake_model_relation은 각 원래 단계의 `exact_model|related_family|unspecified|null`이다. model=None에서 두 relation이 달라도 같은 값으로 덮지 않는다.
- response_membership=`referenced|not_referenced|not_assessed`. 유효한 source selected 응답의 참조 포함/부재만 가리키며, 응답 부족·미검증이면 not_assessed다. 부재는 거절 판정이 아니다.
- selection_status=`selected|not_selected_in_response|outside_intake_scope|unknown`. 전체 결합이 bound이고 해당 case가 admitted일 때 참조 포함은 selected, 상세 case에서 응답 미포함은 not_selected_in_response다. intake의 명시 related_family는 outside_intake_scope로 남긴다. preview만 있거나 문맥/접수/응답 미확인은 unknown이다. case별 상태가 시험 준비/적합/품질 점수가 되지 않는다.
- case reason enum은 `case_detail_not_requested,related_model,intake_match_insufficient,response_insufficient_evidence,response_no_candidate,source_context_unbound,snapshot_unbound,not_selected_in_response`다. 실제 확인한 이유만 배열에 넣고 기존 context 제외 이유와 source response 이유도 별도 필드로 유지한다.

### evaluation 정확 6키 — 항상 상수

```json
{
  "status": "not_executed",
  "score": null,
  "actual_model_score": null,
  "scored_fixture_checks": 0,
  "actual_model_checks": 0,
  "independent_assignment_status": "not_assessed"
}
```

원래022/029의 부적격·미배정 증거는 별도로 보존한다. 032는 평가 입력을 받지 않아 새로 평가하지 않으며 preview eligible를 보고 이 값을 채우지 않는다.

### verification 정확 18키

처음7개만 해당 검사의 실제 성공에 따라 true다.

```text
snapshot_dto_validated, projection_hash_verified, snapshot_metadata_complete,
catalog_context_matched, response_revalidated, intake_match_checked,
reference_scope_checked
```

다음11개는 항상 false다.

```text
source_facts_reverified, result_projection_reverified,
database_currentness_verified, operational_authority_granted,
model_execution_verified, model_quality_verified,
independent_evaluation_approved, training_executed, evaluation_executed,
hardware_verified, physical_verified
```

## limits 정확 16키

| 키 | 값 |
|---|---:|
| max_snapshot_bytes | 9437184 |
| max_projection_bytes | 8388608 |
| max_context_bytes | 8388608 |
| max_response_bytes | 327680 |
| max_output_bytes | 2097152 |
| max_snapshot_depth | 20 |
| max_projection_depth | 16 |
| max_context_depth | 24 |
| max_response_depth | 16 |
| max_output_depth | 16 |
| max_nodes | 500000 |
| max_cases | 128 |
| max_requested_cases | 16 |
| max_references | 256 |
| max_facts | 3 |
| max_questions | 200 |

입력3개의 합계 복사 노드500,000이며 projection은 snapshot 안에서 한 번만 센다. 부모 재검증의 반복 처리 횟수를 입력 노드 수로 합산하지 않는다. projection은 부모021 plain 8MiB/depth16/node50000/string1MiB를 그대로 적용하고 snapshot envelope 때문에 이를 줄이지 않도록 9MiB/depth20을 둔다. context의 reviewed value/depth6/string16384·preview50000 배열 등 부모 유효 범위는 임의 축소하지 않는다. public032는 input bytes/depth/nodes와 부모 limit을 모두 고정 limit 오류로 구별한다. 출력은 정제 metadata/참조만 담는다.

## 고정 부족 이유와 오류

top reason_codes는 다음6개 enum의 정렬/중복 없는 배열이다.

```text
snapshot_binding_incomplete, projection_hash_mismatch,
case_context_mismatch, case_response_not_bound,
intake_query_insufficient, selected_reference_outside_intake_scope
```

형식이 유효하지만 근거 결합이 부족하면 receipt/status=insufficient_evidence로 남긴다. snapshot 핵심 metadata 미확인, 해시 불일치, 다른 catalog/context·source SHA, 잘못된 참조·producer 결합, 현재 intake query 충돌을 성공으로 처리하지 않는다. parent no_match와 response no_candidate 자체는 구조 오류가 아니며 부모 원래 상태로 남긴다.

`IntakeCaseReferencesError(ValueError)`의 `.code/str/args`에는 아래 고정7개만 남긴다. 오류의 __context__·원문·경로·토큰·부모 예외 내용을 내보내지 않는다.

```text
intake_case_references_catalog_invalid
intake_case_references_snapshot_invalid
intake_case_references_context_invalid
intake_case_references_response_invalid
intake_case_references_producer_invalid
intake_case_references_source_error
intake_case_references_limit_exceeded
```

기본 타입/정확키/schema/원시 scalar/enum 형식 오류는 해당 invalid다. genuine catalog의 읽기 오류/불명 DTO는 source_error로 거절한다. 모든 parent 예산 오류는 limit_exceeded이며 부족으로 삼키지 않는다. parent helper/code 교체 방어·인증 체계를 추가하지 않는다. 원래 caller가 보존한 실패 입력은 덮어쓰지 않는다.

## 실제 입력 준비와 검증 표기

1. **정상 합성:** 기존 genuine021 fixture catalog와 실제 `project_analysis` 출력에서 최소 projection을 caller가 준비한다. 합성 origin metadata는 명시 synthetic fixture의 JSON/문서/결과 해시로 만들고 실제 접수 DB origin이라고 하지 않는다. 025 공개 builder/decoder→032를 연결한다.
2. **실제 catalog 준비:** 025가 사용한 고정 S03 packet/original 2PDF/producer를 그대로 재사용한다. Caller가 원문 bytes로 genuine021 객체를 먼저 구성하고 공개 summary/case DTO가 고정 producer와 같은지 확인한다. 이 준비의 PDF unique2 읽기/추출·권한 처리·후대조 읽기를 **032 바깥 별도 실측 카운트**로 기록한다. 032 자체는 해당 live 객체의 공개 읽기 API만 호출하며 PDF I/O0이다. DTO로 private state를 만들거나 method를 대체하지 않는다.
3. **실제 intake 부족을 그대로 시험:** 이 배정에는 확정된 실제 current intake snapshot이 아직 인계되지 않았다. 기존 실제 보고서에서 고객 시장·제품·현재 intake ID/revision/결과 해시를 뽑아 접수 사실로 만들지 않는다. caller 미제공 snapshot(핵심 metadata null/빈 projection/정확한 빈 projection 해시)과 보존025 actual context/합성 response를 사용하면 부족 receipt/accepted refs0/평가null을 기대한다. 이는 **실제 자료 + 미제공 접수 snapshot + 합성 응답** 검사이며 실제 접수 종단 검증이 아니다.
4. **선택적 혼합 fixture:** 실제 catalog에 명시적으로 만든 synthetic 접수 요청/완료 projection을 붙여 선택 경계를 검사할 수 있다. 이때 intake synthetic=true/catalog synthetic=false를 구별하고 “실제 고객 접수/모델 결과”로 집계하지 않는다. 기존 실제 snapshot 인계가 오면 원래 bytes/receipt 해시를 대조해 그 입력으로 별도 기록하며 DB를 새로 열거나 currentness를 주장하지 않는다.
5. 기존 S03 6개 context와 producer·실패·original 해시/크기/mtime/mode를 보존하고 all API I/O spy0을 확인한다. 현재022/029 ineligible/미배정/null과 모델 평가0은 별도 원본 그대로 남긴다. S08-B0011의13JSON/9descriptor·7SHA+반복2·그룹 unknown/HAC annotation을 읽었다는 이유로 기존 catalog/평가/규범 적격을 바꾸지 않는다. 이 배정은 그 metadata의 새 catalog 인수/해석도 포함하지 않는다.

## RED/수용 묶음

- genuine021/025와 synthetic projection을 연결해 selected, 같은 context의 유효 미포함, 보수적 insufficient/no_candidate, snapshot 부족을 각각 검사한다. source status와 accepted selection을 섞지 않는다.
- explicit/user_confirmed+event와 inferred/uncertain/missing/identity 질문/미국 아닌 시장·제품/모델 충돌·판본 차이를 기존 match_intake 이유 그대로 확인한다. query model=None+접수 model known에서 related reference가 선택되지 않는 경계를 반드시 포함한다.
- snapshot core null/타입·ID150/event128·projection hash/이상 key·NaN/bool 정수·사본·결정성·byte/depth/node 한도, 새 snapshot/revision은 새 receipt 해시가 되지만 DB currentness는 항상false임을 확인한다.
- catalog/context/preview/doc/source binding·same case/claim/evidence/SHA/page/line/producer·validated flags/중복/다른 context를 각각 섞어 성공으로 바꾸지 못하게 한다. 원문/claim의 quote/value/basis·raw lease token·임의score/fold를 snapshot의 추가 입력으로 받거나 요약에 복제하지 않는다. match_intake에 필요한 최소 projected fact value와 원문 claim 값은 구별한다.
- requested 상세 선택, excluded not_selected, related_model, source 응답 미포함/미확인 상태를 독립적으로 보존한다. source context와 intake model_relation이 다를 때 원래 값을 덮지 않는다. preview_only를 검토 완료 case로 올리지 않는다.
- 부모 유효 긴 preview/value·reference256·parent 예산 오류 전달, type/API만 사용·source 오류 고정·입출력 alias 불변을 확인한다.
- caller PDF 준비와 actual032 실행을 분리해 계수한다. API 내 open/Path.open/os.open/PDF/parser/socket/subprocess/Store/worker queue/model spy0, 실제 자료 불변, 평가6키 상수/verification11 false를 확인한다.
- 전용과021/025/029/intake_model_boundary 관련 회귀·정적검사·문서 check_artifacts/usage UTF-8·링크를 실행한다. 기능 검증/합성 fixture/실제 catalog+미제공 snapshot/혼합 fixture/실제 접수는 별도 분모로 기록한다. 실물·실제 모델/훈련·DB 현재성·전체 업무 검증은 미실행이다.

고정 뒤 소유3파일만 commit/push·원격 full SHA 비교하고 독립 일반 데이터 기능 리뷰/수정·총괄 통합으로 넘긴다. 독립 리뷰와 공통 통합 검증은 소유 검증과 별도다.

선행 읽기 계약: [021 사례](../../docs/fcc/fcc_report_cases_usage.md), [025 참조 경계](../../docs/fcc/fcc_case_review_usage.md), [접수 projection](../../labflow/intake_analysis.py#L143).

## 소유 검증 결과

2026-10-24 전용34개를 포함한 관련235개 검사 PASS, skip0, 22.626초다. genuine021·025 공개 API, 실제 project_analysis를 사용한 합성 projection, model=None/접수 모델의 related_family 구분, 부분 참조 전체 보류, 상세 미포함/응답 미포함/미확인, 정확256참조, 부모 projection/wire 예산 전달, 사본/결정성/고정 오류·요약 비노출을 확인했다. 021·025·029와 기존 worker/jobs/Store/분석 코어 소스는 불변이다. unit fixture의 synthetic flag 조합 검사는 실제 원문 검증과 별도다.

실제 S03은 보존 packet과 원문2PDF(4,559,516bytes)로 caller가 genuine021 catalog를 준비했다. 준비 단계의 추출 시도2·공개 permission 읽기2와 PDF 파일 읽기4회(초기2+불변 대조2)는 032 API 바깥이다. 원문 PDF를 새 파일로 복사하지 않았다. 공개 producer DTO가 기존 고정본과 같고 원본/metadata의 해시·크기·mtime·mode가 불변이다.

실제 catalog+미제공 접수 snapshot+보존 합성 응답의6개 문맥은 모두 부족/accepted references0/평가미실행·null을 유지했다. 핵심 출처는 null로 남겼다. 별도의 명시 synthetic intake+실제 catalog 혼합 fixture1건은 참고 선택 결합을 통과했으며 intake synthetic=true와 catalog synthetic=false를 유지했다. 032 API의 open/Path.open/os.open/PDF/parser/socket/subprocess/Store/complete_job 감시9종은 모두0회다. 실제 current intake/DB 현재성·운영 권한·실제 모델/훈련/평가·실장비·현장·규정 적합성은 미검증이다.

독립 리뷰와 공통 통합은 소유 검증과 별도 단계로 진행한다. 문서 무결성 검사는 UTF-8·링크만 확인하며 기능/계측/적합성을 입증하지 않는다.
