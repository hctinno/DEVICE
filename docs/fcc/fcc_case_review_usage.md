# FCC 사례의 검토 문맥·응답 참조 경계025

2026-10-24 · Asia/Seoul. [구현](../../labflow/fcc_case_review.py)과 [전용 검사](../../tests/test_fcc_case_review.py)는021의 생성 완료 메모리 catalog를 읽고, 제공된 검토 근거에 응답을 결합한다. 기존 intake_model_boundary의 strict JSON·고정 system/data 분리·fingerprint 패턴을 참고한다. 모델 클라이언트·외부 송신·Store·장비·원본 PDF 읽기 기능은 추가하지 않는다.

## API와 실행 범위

```python
build_case_review_context(catalog, *, query, case_ids) -> dict
build_case_review_prompt(context, *, producer_name) -> dict
decode_case_review_response(response, context, *, producer_name) -> dict
```

catalog는 정확한021 FccReportCaseCatalog다. 신뢰된 caller가 생성 완료한 객체의 공식 summary/search/case 읽기 API를 사용하고 그 DTO를 검사한다. subclass/duck/경로/PDF bytes/사용자 callback을 받지 않는다. 하위 helper/code 교체 방어나 임의 코드 무결성 프레임워크는 추가하지 않는다. 고정 선행 소유 SHA는3c599fe976f860a2b6c7a8a3ea7a68326557e914이며021 독립 검토 상태는 별도 보존한다.

query는 정확한 product_family/rule/method/model 4키이며 각각 256자 이하의 공백 아닌 str 또는 null이다. case_ids는 명시적인 유일021 ID 배열이다. 비교는021의 trim/casefold literal이며 판본·모델 alias·규정·제품을 추측하거나 대체하지 않는다. case 선택은 search의 실제 candidates에 포함되어야 한다. query.model이 있으면 exact_model 사례만 선택한다. source status가 insufficient_evidence/no_match이면 case_ids=[]로 그 상태를 보존한다. 후보가 있는데 선택 배열이 비어 있으면 no_selected_cases다.

문맥은 공개 source DTO의 타입·키·문서/페이지/hash/line·권리·검토 상태를 대조한다. reviewed claim만 원래 basis/value/unit와 함께 담는다. 나머지는 claim_id/field/status/basis의 gap metadata로 남긴다. 0/0.0/false를 누락으로 바꾸지 않고 null/unknown/상충을 사실로 올리지 않는다. query의 family/model/rule/method에 대응하는 claim이 다른 literal만 담으면 selectable=false/query_literal_mismatch다. 이 검사는 문자 대응이며 모델 품질·구조화 해석 검증이 아니다.

원문 quote는 비공개 untrusted data다. prompt 생성은 외부 모델 사용 권한을 승인하지 않으며 documents.rights의 external_model_use_allowed=false와 source 범위를 유지한다. 실제 검증의 caller는 private packet+원문 bytes로 정확021 catalog를 먼저 구성한다. 이 준비 단계의 PDF 읽기/파싱을025 API의 메모리 조회와 별도 계상한다. private state 재구성이나 method 대체로 live 객체를 가장하지 않는다. DTO snapshot prompt/decoder replay는 별도 검사이며 실제 build_context 호출을 대신하지 않는다.

## 예산과 문맥 identity

| 항목 | 상한 |
|---|---|
| 개별021 source DTO | UTF-8 compact JSON 8 MiB/depth24/200,000 nodes |
| 선택 case / 전체 reviewed claim / 전체 evidence | 16 / 1,024 / 4,096 |
| context | 8 MiB/depth24/200,000 nodes |
| prompt wrapper | 17 MiB/depth24/200,000 nodes |
| response str 또는 UTF-8 bytes | 256 KiB/depth12/50,000 nodes |
| response references | 256개, 중복 불허 |
| validated response wrapper | 320 KiB/depth16/60,000 nodes |

021 ID/SHA/claim/evidence/value/quote·page_index의 예산과 exact type을 그대로 검사한다. 부모 wrapper 때문에 허용된 source의 value/evidence 깊이를 줄이지 않는다. 전체 예산을 초과하면 limit 오류이며 자동으로 claim/인용을 잘라내지 않는다. JSON은 읽으며 크기·깊이·node를 누적해 제한에서 중단한다.

source claim value는021의 depth6/개별 문자열16,384자 검증을 재사용한다. preview의 파생 문자열/목록은 source의 값·전체 예산을 따른다. 임의256자/128항목 같은 더 작은 preview 상한을 새로 만들지 않는다.

context_id는 아래 context exact19키 중 context_id를 뺀 canonical compact UTF-8 JSON SHA-256이다. 입력 순서가 다른 명시 case_ids는 정렬하고,021 query 결과의 trim 표기를 사용한다. source_binding은 전체 원래 DTO의 SHA를 담아 selected projection과 원래 source를 구별한다. hash는 제공된 snapshot identity이며 서명·원본 진위 인증이 아니다. prompt/decoder는 context를 다시 검증하고 identity를 재계산한다.

## 정확한 DTO

context의 exact19키는 schema_version=1, kind=fcc_case_review_context, context_id, corpus_id, execution_mode=report_derived_case_review, synthetic, query, requested_case_ids, search_status, status, reason_codes, source_binding, source_scope, verification, limits, cases, excluded_candidates, case_previews, documents다.

status는 ready/no_selected_cases/no_candidates/insufficient_evidence다. search_status는021의 candidates/no_match/insufficient_evidence다. reason_codes는021 search의 고정 reason code를 보존하며 선택 없음에는 no_selected_cases만 추가한다. source_scope는021 summary.scope 7키, case_previews는 원래17키 preview, documents는 원래 document DTO에서 exhibits만 제외한7키 document_id/sha256/size_bytes/physical_pages/rights/extraction/page_index다. retained 전체 text·PDF bytes·파일 경로는 넣지 않는다.

source_binding은 exact3키 summary_sha256/matches_sha256/case_sha256s다. 마지막은 case_id/sha256 2키의 정렬 배열이며 선택된 원래 case DTO hash다. context.limits는 max_context_bytes/max_depth/max_nodes/max_cases/max_claims/max_evidence/max_response_bytes/max_references/max_response_depth의 exact9키이며 위 고정값이다.

verification은 exact12키다. source_dto_validated만 true이며 source_page_literals_reverified/structured_interpretation_verified/institution_identity_verified/normative_compliance_verified/model_execution_verified/model_quality_verified/independent_evaluation_approved/training_executed/evaluation_executed/hardware_verified/physical_verified는 모두 false다.021의 literal_verified=true는 source 검수 선언으로 유지하며025의 새 literal 인증으로 바꾸지 않는다.

각 selected case의 exact8키는 case_id/report_group_id/document_ids/preview/model_relation/claims/gaps/source_case_sha256다. model_relation은 exact_model/unspecified다. claims는 원래7키에 selectable/selection_reason을 더한9키다. status는 reviewed, selection_reason은 reviewed_evidence/query_literal_mismatch다. evidence는021의 원래13키에 evidence_id를 더한14키다. evidence_id는 case_id/claim_id/원래13키 evidence의 canonical 객체 SHA다. 문서 SHA·파일페이지·text hash·line과 원래 quote/location·basis/value를 유지한다.

gaps는 claim_id/field/status/basis의 exact4키다. excluded_candidates는 case_id/model_relation/reason의 exact3키이며 reason은 not_selected/related_model/query_insufficient다. 미선택/미검토는 응답의 selectable 근거가 아니다. 전체 source preview/document의 partial·parser issues·citable=false도 보존하며 HAC의 미인용 페이지를 성공 근거로 만들지 않는다.

prompt의 exact6키는 schema_version=1, kind=fcc_case_review_prompt, binding, expected_producer, messages, verification이다. binding은 context_id/context_sha256/corpus_id 3키다. messages는 고정 system 1개와 canonical context JSON인 user 1개다. expected_producer는 kind=model/name 2키이고 producer_name은 1~200자의 공백 아닌 UTF-8 문자열이다. producer 이름은 caller 선언이며 실행 증거가 아니다.

모델 response wire의 exact7키는 schema_version=1, kind=fcc_case_review_response, context_id, producer, status, references, reason_codes다. status는 selected/insufficient_evidence/no_candidate다. selected에는 ready context와 한 개 이상의 selectable reference가 필요하고 reason_codes=[]다. 나머지는 references=[]이며 부족 상태만 나타낸다. no_candidate는 no_candidates context에만 허용한다. insufficient_evidence의 고정 사유는 query_insufficient/no_selected_cases/no_reviewed_evidence/additional_evidence_required 중 하나 이상이다. no_candidate의 사유는 no_reviewed_case다.

query_insufficient/no_selected_cases는 각각 같은 context 상태에서만 허용하고, no_reviewed_evidence는 selectable reference가 없을 때만 허용한다. additional_evidence_required는 참조를 선택하지 않는 보수적 보류다. 근거가 실제로 있는 상태를 없는 상태로 바꿔 응답하지 않는다.

각 reference는 exact9키 case_id/claim_id/evidence_id/document_id/source_sha256/file_page/text_sha256/line_start/line_end다. 같은 context의 선택 case·selectable reviewed claim·source evidence와 모든 값·타입이 정확히 같아야 한다. 같은 claim ID라도 다른 case/문서/개정 SHA/페이지/line을 혼합할 수 없다. model이 value/quote/basis/판본/score/fold/tool call/새 사실을 추가하는 키는 거절한다. 중복 JSON 키·NaN/Infinity·surrogate·fence·추가 JSON 값도 거절한다.

decoder 반환의 exact10키는 schema_version=1, kind=validated_fcc_case_review, context_id, corpus_id, status, reason_codes, references, expected_producer, source_binding, verification이다. selected는 참조를 골랐다는 상태다. 사례 완성·규범 승인·AI 품질 승인이 아니다. reference 선택이 원래 claim의 basis를 report_fact로 바꾸거나022 성분/fold/score를 생성하지 않는다. source 문장·구조화 value의 의미나 모델의 과학적 정확도는 검증 범위가 아니다.

## 오류와 보존

FccCaseReviewError(ValueError)의 code/str/유일 args는 고정 코드다: fcc_case_review_catalog_invalid, fcc_case_review_query_invalid, fcc_case_review_selection_invalid, fcc_case_review_source_invalid, fcc_case_review_source_error, fcc_case_review_limit_exceeded, fcc_case_review_context_invalid, fcc_case_review_context_mismatch, fcc_case_review_producer_invalid, fcc_case_review_response_invalid, fcc_case_review_reference_invalid. private ID/quote/주소·원시 예외를 붙이지 않는다.

세 함수는 입력을 변경하지 않고 detached 결과를 반환한다. 실패한 source/context/원래 응답은 caller가 .local에 보관하며 경계는 자동수정·재요청·파일 저장을 하지 않는다. source DTO 검증·021 literal 대응·structured interpretation·모델 품질·독립 평가 승인을 각각 구별한다.

## 검증

공개 fixture는 합성 PDF/claim/context/응답만 사용한다. 정상/0/false/unknown·후보 없음/partial·잘못된 제품·판본·같은 claim ID의 출처 혼합·context 변조·JSON/예산·사본·무I/O를 검사한다. 실제021 B001은 caller의 별도 PDF2 읽기/파싱 준비 후025의 실제 build_context/prompt/decoder를 호출해 SAR 근거 참조와 HAC 충돌/미인용 페이지를 보존한다. 응답은 명시 합성 fixture다.025 API의 파일/PDF/네트워크 I/O·실제 모델 호출/송신·학습/평가·장비 실행은0이다. 원본/source SHA와022의 전체 미배정·부적격 상태를 보존한다.
