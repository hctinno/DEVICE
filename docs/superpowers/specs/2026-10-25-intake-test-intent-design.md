# 규정·방법 공급: 제공 근거와 시험 의도 대조 제안

2026-10-25 Asia/Seoul. **독립 정적 Yes/C0I0M0를 확인한 B 방향의 공개 구현 계약이다.** 제공 근거를 대조하는 순수 검토 경계를 신규3 이내로 고정한다. 실제 소스 형상을 확인한 기준은 공개 c89e5c680e664916d3fe47cc5409a62255a71a46/9de812ca827d2c2e84ae90b4ed74385321e1c9fe이며 실제 구현은 별도 게시 base/소유 배정 뒤 착수한다. 현재성·실제 AI·규범/실행 승인을 부여하지 않는다.

## 기존 기능과 A/B 선택

| 재사용 접점 | 실제 범위와 남는 공백 |
|---|---|
| G01–G04: [validate_analysis](../../../labflow/intake_analysis.py#L56) · [project_analysis](../../../labflow/intake_analysis.py#L143) · [build_analysis_prompt](../../../labflow/intake_model_boundary.py#L250) · [decode_analysis_response](../../../labflow/intake_model_boundary.py#L291) | facts 허용10필드에 rule/method 없음. 원 text/PDF 인용·context/producer를 검증하지만 의미·source role은 분석자 선언이다. prompt/decoder는 모델을 호출하지 않는다. 기존 FIELDS나 facts에 rule/method를 끼워 넣지 않는다. |
| G05–G09: [claim_job](../../../labflow/intake_jobs.py#L58) · [complete_job](../../../labflow/intake_jobs.py#L162) · [probe_loopback_analysis](../../../labflow/intake_model_probe.py#L360) · [read_intake_reference_snapshot](../../../labflow/intake_reference_snapshot.py#L347) · [build_intake_case_reference_receipt](../../../labflow/intake_case_references.py#L194) | 수동 완료/보존과 supplied snapshot/참고 응답의 결합이다. 034 최소 projection은 product_type/market/model·질문 key뿐이고 원인용을 포함하지 않는다. worker는 fixture provider만 허용하며 probe도 synthetic loopback이다. |
| G10–G13: [FccReportCaseCatalog.match_intake](../../../labflow/fcc_report_cases.py#L1223) · [FccReportCaseCatalog.discover](../../../labflow/fcc_report_cases.py#L1190) · [build_case_review_context](../../../labflow/fcc_case_review.py#L338) · [decode_case_review_response](../../../labflow/fcc_case_review.py#L495) | nullable query exact4/값≤256와 명시 case_ids≤16을 소비한다. report literal/claim locator를 현재 규정·판본의 적용 판단으로 전환하지 않는다. |
| G14–G17: [register_method](../../../labflow/workflow.py#L55) · [add_plan](../../../labflow/workflow.py#L68) · [review_method](../../../labflow/workflow.py#L126) · [Store.document](../../../labflow/store.py#L161) | register_method는 F01–F20·calculator·source IDs·limit clause, add_plan은 명시 applicability/configuration/rationale를 받아 DB에 쓴다. review_method의 원본/권리/검토/해시 gate는 재사용 대상이나 접수 원문↔현재 규정 판본의 의미 대조는 없다. 지금 호출하지 않는다. |
| G18–G21: [page_citation](../../../labflow/document_extract.py#L329) · [FleetHarness.__init__](../../../labflow/virtual_fleet/harness.py#L119) · [FleetHarness._proposal (내부 검증)](../../../labflow/virtual_fleet/harness.py#L373) · [ControlSourceCatalog.find_items](../../../labflow/control_source_catalog.py#L300) | 제공된 추출 결과의 page/text hash/line/quote 일치 검사, 가상 execute/advance/stop, 장비 조사 metadata다. page_citation은 원본 진위·규범 판단을 인증하지 않는다. 장비/기관/source scope를 의뢰 적용성으로 대체하지 않는다. |

**A — 기존 caller 조립/신규 모듈0:** 이미 있는 validate_analysis와 page_citation으로 제공 인용을 확인하고 c89e 부분 query/discover 절차에 별도 검토 기록을 붙일 수 있다. 즉시 재사용 가능하나 rule/method의 출처·서로 다른 관측/판본·충돌·권한 보류를 함께 검증하는 공개 경계는 없으며 consumer마다 같은 판단을 반복한다.

**B — 권고:** 그 작은 공백만 별도 순수 함수로 고정한다. 후보 literal·출처 연결·제공 metadata의 모순을 비교하고 계속 `review_only`로 반환한다. 검색/선택/적용성 엔진·규정 registry를 만들지 않는다. 향후 소유 제안은 `labflow/intake_test_intent.py`, `tests/test_intake_test_intent.py`, `docs/fcc/intake_test_intent_usage.md` 신규3이다. 기존 analysis/jobs/034/025/032/Store/workflow/HTTP/UI/CLI 변경0이다.

## B의 제안 입력과 한도

제안 signature는 `build_intake_test_intent_review(intake, proposal, sources) -> dict` 한 개다. 기본 내장 JSON 타입만 받고 사본으로 처리한다. 모든 입력은 caller가 이미 보존한 값이며 파일/Store/모델을 새로 읽지 않는다.

- `intake` 정확4키: `context, analysis, projection, observation`. 앞3개는 원 분석 context/submission과 현재 full projection, observation은 이미 받은034 capture 또는 null이다. context의 intake_id/revision/synthetic/analysis_context_id와 analysis.context_id·제공 observation의 동일 필드를 대조한다. G01 `validate_analysis(analysis, context.documents, context.synthetic, context_id=...)`를 재사용해 원 인용을 재검사한다. 기존 허용 context 키/인용 schema를 확장하지 않는다. projection·원 질문/상태는 보존한다. observation만으로 인용을 복원하지 않으며 원 result_json bytes가 없으면 result_sha256의 재검증을 주장하지 않는다. 내부 ID 일치가 DB 현재성은 아니다.
- `proposal` 정확4키: `as_of, institution_scope, workflow_scope_id, fields`. 앞3개는 명시 ISO 날짜/null·기관 scope 문자열/null·기존 F01–F20/null이고 서로 대체하지 않는다. fields는 rule/method 정확2키이며 각각 후보 배열0~2개다. 후보 정확4키는 `literal, origin, intake_refs, basis_refs`; literal은 원문 그대로 비공백 UTF-8≤256자, origin은 `explicit_supplied|model_proposed`라는 caller 선언이다. producer나 실제 추론 증거를 새로 만들지 않는다. intake_refs는 원 analysis의 `{fact_index,evidence_index}`(0-based), basis_refs는 `{document_id,page_number,text_sha256,line_start,line_end}`다. 각 배열≤8이며 모르는 근거는 []다.
- `sources`는 제공 근거≤8개다. 각 정확12키는 `document_id, source_kind, representation, artifact_sha256, institution_scope, workflow_scope_ids, edition, effective_from, effective_to, review_status, rights_status, extraction`. source_kind=`regulation|guidance|standard|manufacturer|report|unknown`, representation=`original|extract|metadata|unknown`, review_status=`reviewed|unreviewed|unknown`, rights_status=`usable|restricted|unknown`이다. scope/edition/기간/해시는 제공되지 않았으면 null 또는 빈 scope 배열이다. extraction은 이미 제공된 document_extract 결과 또는 null이다. 유효 extraction은 G18 `page_citation(result,page_number,line_start,line_end)`로 검증하고 nonnull artifact_sha256과 source.sha256이 같을 때만 literal 연결을 인정한다. 해시가 미제공이면 basis_missing으로 보류한다. metadata/발췌 artifact 해시를 원본 해시로 승격하지 않는다.

기본 상한 제안: 전체 입력40MiB/depth32/노드2,000,000, context6MiB·analysis2MiB·projection8MiB·observation12MiB, proposal64KiB, sources 합계8MiB, 출력2MiB. source ID는 기존021 ASCII128/SHA64, 후보 literal256, institution_scope128·edition256, workflow_scope_ids≤20, 원 질문≤200을 사용한다. 기존 parent 인용/형식 조건은 그대로 적용한다. 초과/형식 오류는 고정 오류이며 절단/alias/일부 성공으로 고치지 않는다. 이 한도는 제안이며 현재 제품에 적용하지 않았다.

## 비교 결과와 보류

출력 정확9키 제안: `schema_version, kind, status, input_binding, fields, questions, reason_codes, verification, limits`. kind=`intake_test_intent_review`, status는 항상 `review_only`다. input_binding은 제공 입력의 canonical hash와 원 관측 식별/null을 구별하며 새 intake/revision/원본 해시를 발명하지 않는다. questions는 원 projection.questions를 보존하고 Store 질문/답변을 쓰지 않는다.

input_binding 정확11키는 `intake_id, revision, analysis_context_id, result_sha256, observation_snapshot_id, provided_context_sha256, provided_analysis_sha256, provided_projection_sha256, provided_proposal_sha256, provided_sources_sha256, provided_observation_sha256`다. 원 context의 식별과 제공 observation의 result/snapshot 식별을 복사하되 없는 값은 null이다. 제공값끼리 다르면 일치한 값으로 덮지 않고 mismatch 이유/원 입력을 보존한다. 제공 observation이 없으면 해당 hash도 null이다. 나머지 provided hash는 sort_keys/UTF-8/비유한수 금지 canonical JSON 해시이며 원 result_json 해시를 대체하지 않는다.

fields는 rule/method 정확2키다. 각 결과는 `{status,candidates,reason_codes}`, 각 candidate 결과는 `{literal,origin,intake_refs,basis_refs,literal_linked,period_checks,reason_codes}`다. refs는 입력 그대로이고 literal_linked는 실제 문자 대조 bool이며 period_checks는 참조 document별 `{document_id,status}`다. 후보0이면 missing, 서로 다른 literal≥2개면 conflicting, 단일 literal의 모든 후보가 I2 조건을 충족하면 literal_linked이고 그 외는 proposed다. origin의 명시/모델 순서로 후보를 선택하지 않는다. 모든 reason_codes는 아래 enum의 정렬/중복 없는 배열이며 top은 전체 확인 이유의 합집합이다.

fields.rule/method는 후보·origin·원 locator와 `missing|proposed|literal_linked|conflicting` 상태를 남긴다. `literal_linked`는 해당 제안 문자열이 제공된 유효 인용 quote에 그대로 있는 경우뿐이며 case/띄어쓰기/규정 표기 alias를 추정하지 않는다. 서로 다른 후보를 첫 값으로 고르지 않는다. request/product/reference 역할과 명시 literal·모델 제안을 구별한다. source_kind=report의 값은 현 의뢰의 규범 근거가 아니고 제조사 자료도 규정으로 승격하지 않는다.

기간은 명시 as_of와 제공 ISO 날짜를 비교한 `in_declared_window|outside_declared_window|unconfirmed|conflicting`까지만 기록한다. in_declared_window도 현행성 증명이 아니다. 기관 scope·F01–F20·판본/역할의 결손·모순, source 권리/원문/검토 미확인, identity/원 질문·인용 부족을 원 상태와 함께 남긴다. 정식 reason 제안은 `intake_binding_incomplete, intake_binding_mismatch, intake_questions_open, intent_missing, intent_conflicting, intake_ground_missing, basis_missing, literal_not_in_citation, source_not_normative, source_status_unconfirmed, institution_scope_unconfirmed, scope_conflicting, edition_unconfirmed, period_unconfirmed, period_conflicting, period_outside_declared_window, applicability_not_assessed`다. 구조/참조 타입 오류는 `test_intent_invalid_input`, 예산은 `test_intent_limit_exceeded`, parent 인용 실패는 `test_intent_source_error`로 구별하고 원 입력/실패는 caller가 별도 보존한다. 오류에 원문·경로를 덧붙이지 않는다.

계산 가능한 검사는 `intake_citations_checked`와 `basis_literals_checked`로만 표시한다. 다음은 항상 false: `projection_recomputed, result_projection_reverified, database_currentness_verified, source_authenticity_verified, normative_applicability_verified, institution_scope_verified, edition_currentness_verified, model_execution_verified, model_quality_verified, query_release_authorized, case_selection_authorized, execution_authorized`. 기존 답변/위임을 새로 계산해 원 projection을 대체하지 않는다. 출력에 완성 query/case_ids/등록/실행 명령을 만들지 않는다. 기존 A의 실제 query에서 rule/method=null과 discovery의 원 search_eligibility/authority false를 그대로 유지한다. 추후 의미·적용 근거가 승인된 별도 계약 없이 이 검토값을025의 완전 query로 복사하지 않는다.

## 기존 자료 재사용과 정확한 공백1

기존 `data/regulatory/fcc/catalog.json`은 원본/발췌/metadata·latest_verified를 구별한다. 이 고정본의24항목/원본0/KDB 전체 첨부0은 전체 최신 P01 corpus의 수치가 아니며, 이번에는 추출 본문을 열지 않았다. `fcc_scope_matrix.csv`의 F01–F20도 조사/지원 상태 표이지 적용 판정 API가 아니다. materials/README의 P01 검수·판본·권리·원본 구별을 유지한다.

**공백1은 현재 의뢰의 확인된 기능/요구와 특정 규정·방법 판본·기관 scope·유효기간을 연결한 기술 적용 검토 근거 행의 정식 공급이다.** 현재 API/metadata만으로 그 의미 판단을 생산하지 못한다. 먼저 root가 이미 인수한 자료/검토 기록에 이 행이 있는지 대조하고 없을 때 해당 행에 필요한 정확 locator/판본만 좁힌다. 지금 새 수집/사용자 자료 요청은0이고 P01/수집자에 직접 연락하지 않는다. 전체 원문 수집이나 실제 AI 공급 완료를 선행 완료로 가정하지 않는다.

실제 API는 위 표를 따르고, 중첩 형상·해시 의미는 다음 소스 접점을 근거로 한다. 아래 내부 함수는 기존 형상을 설명하는 근거이며 새 경계에서 직접 호출하는 API가 아니다. 정확 판정표는 이 문서의 I1–I3 본문에 모두 포함했으며 사적 파일에 위임하지 않는다. [구현 순서](../plans/2026-10-25-intake-test-intent.md)의 수용 사례는 개념적 기대 결과이고 실제 API/fixture 실행 결과가 아니다.

| 실제 형상 소스 | 이 문서의 근거 |
|---|---|
| [_refresh](../../../labflow/intake_jobs.py#L136) | submitted·intake_id/revision과 현재 full projection |
| [_context](../../../labflow/intake_model_boundary.py#L214) | model context의 정확 키와 V1/V2 선택 ID |
| [_unavailable](../../../labflow/intake_reference_snapshot.py#L230) | snapshot=null인034 제공 형상 |
| [_capture](../../../labflow/intake_reference_snapshot.py#L241) | origin/state·full/minimal hash와 현재 답변 구분 |
| [_inspect](../../../labflow/intake_generation.py#L208) | V1 legacy_analysis와 no_pdf_context 상태 |


## I1 — 정확 형상·결합·직렬화

아래는 입력 형상·참조·기간/metadata를 판정하는 제안 규칙이다. 부모 호출·DB/답변/위임 재계산·새 의미 판단을 추가하지 않는다. 규칙상 성공 DTO의 status는 항상 review_only다. missing/mismatch는 형식이 유효한 입력 사이의 연결 상태이며 형식 오류를 그 상태로 숨기지 않는다.

### 입력 형상

공통 기호: `ID150/ID128`은 ASCII `[A-Za-z0-9][A-Za-z0-9_.-]{0,n-1}`, `SHA`는 소문자 hex64, `N`은 bool이 아닌 정확 int≥0, `P`는 정확 int≥1이다. text는 정확 str/유효 UTF-8이고 nonempty는 strip 후 비어 있지 않다는 형식 검사만 한다. 값 자체는 trim/대소문자 변환하지 않는다. nullable은 null을 허용한다고 명시한 곳뿐이다. 아래 invalid_input/source_error/limit_exceeded는 앞에 test_intent_를 붙이는 원3코드의 약칭이다.

| 입력 | 정확 키/형식과 지원 범위 |
|---|---|
| intake | context, analysis, projection, observation 정확4키. observation만 null 허용. |
| context | job_id, intake_id, revision, synthetic, documents, analysis_contract, instructions 정확7키 + 선택 analysis_context_id. 앞 ID2는 ID150, revision=P, synthetic=정확 bool, instructions=str. analysis_context_id는 키가 있으면 SHA이며 null은 불가. 문서에 PDF가 있으면 이 키가 필수이고 텍스트 context에서는 없어도 된다. lease token/attempt/lease_until을 포함한 claim 전체 응답은 이 입력 형상이 아니다. |
| context.documents | 비어 있지 않은 배열, path 유일. text 기본 정확키는 path,sha256,bytes,text,parse_status; 확장 text는 이5+format,extraction_status,issues다. path는 기존 model boundary의 상대 POSIX 경로, sha256=SHA, bytes=N, text=str/null, parse_status=text/requires_parser. 확장 format=text/unsupported, extraction_status=str. PDF는 기본5+format,extraction_id,parser,limits,pages,issues,complete,total_pages,processed_pages 정확14키. format=pdf/text=null/extraction_id=SHA/complete=bool/total_pages=N 또는 null/processed_pages=N. parse_status는 기존 PDF enum을 따른다. parser는 name:str,version:str/null 정확2키, limits는 max_input_bytes,max_pages,max_output_chars,max_page_content_bytes 정확4키의 P다. |
| 문서의 pages/issues | page는 page_number:P,status,text:str,text_sha256:SHA,line_spans 정확5키. page status는 ok,truncated,empty,image_only,no_text,error,limit_exceeded다. line_spans는 line_number,start,end 정확3키의 N 배열이다. issue는 code:ID150 정확1키 또는 +page_number:P다. pages 번호 유일; 인용된 page의 실제 text/hash/line-spans 불일치는 부모의 source_error다. 인용하지 않은 page를 새로 재추출/전문 검증하지 않는다. |
| analysis_contract | 기존 jobs._analysis_contract descriptor만 지원한다. schema_version=정확1/2, producer(kind/name 문자열),identity 문자열,missing_fields(FIELDS 이름 배열),facts 배열 정확5키이고 schema2만 context_id:SHA를 추가한다. 문서에 PDF가 있으면 descriptor는2, 없으면1이다. fact descriptor는 field/value/status/evidence 정확4키, evidence descriptor의 키는 해당 버전의 기존 text/PDF 인용 키이며 값은 설명 문자열이다. 이를 실제 제출본이나 모델 실행 증거로 사용하지 않는다. |
| analysis | schema_version=정확1/2,producer,identity,facts,missing_fields 정확5키이며 schema2만 context_id:SHA를 추가한다. producer는 kind=model/manual/fixture,name:nonempty≤200 정확2키, identity=single/ambiguous/unknown. facts≤200, fact 정확키 field,value,status,evidence; field∈FIELDS, value nonempty≤4000, status=explicit/inferred/uncertain, evidence1..20. schema1 evidence는 path,sha256,line_start,line_end,quote,role 정확6키. schema2는 +kind=text_line/pdf_page, pdf_page만 +extraction_id,page_number,text_sha256. SHA/줄 P/quote≤262144문자/role=request,product,reference. 실제 인용·fixture/synthetic·schema2 context 일치는 validate_analysis로 검사하며 그 실패는 source_error다. schema1에 context_id를 덧붙이지 않는다. descriptor와 제출본 버전을 새로 동일시하지 않고 validate_analysis의 지원 범위를 따른다. |
| projection | facts,questions,next_action,measurement_support,verification,submitted,unread_documents 필수7키 + 선택 intake_id/revision. ID가 있으면 ID150 또는 null, revision은 P 또는 null. next_action=deferred/needs_information/prepare_plan/propose_start, measurement_support=unverified, verification=contract_only. submitted는 위 analysis 형상이며 original analysis와 별도 보존한다. facts의 키는 FIELDS의 부분집합; 각 값은 value/status 정확2키 또는 +event_id, value≤4000, status=explicit/inferred/uncertain/user_confirmed, event_id=ID150 또는 P이며 user_confirmed에는 필수다. unread_documents는 상대 경로 문자열 배열. 최소034 projection(facts/questions만)은 이 full 입력을 대신하지 못한다. |
| projection.questions | ≤200, 순서 그대로. 기존 union만 지원: missing_FIELD={key,field,message}, conflict_FIELD={key,field,values,message}, product_identity={key,message}, unread_documents={key,paths,message}. field∈FIELDS, key/field 일치, message=str, values는2..200개의 nonempty≤4000 문자열 배열, paths는 상대 경로 문자열 배열. 원 배열을 정렬/축약하지 않는다. |
| proposal/sources | 원 v1 정확키·enum·배열 한도를 유지한다. proposal.as_of와 source.effective_from/to는 아래 실제 달력 날짜 또는 null. institution_scope는 nonempty≤128/null, workflow_scope_id는 F01..F20/null, source.workflow_scope_ids는 중복 없는 F01..F20 배열≤20. document_id=ID128 유일, artifact_sha256=SHA/null, edition=nonempty≤256/null. 빈 문자열을 null로 바꾸지 않는다. |

PDF parse_status enum은 ok,partial,empty,encrypted,malformed_pdf,parser_error,parser_unavailable,image_only,no_text,limit_exceeded다. context 문서/descriptor의 위 형상은 기존 model boundary의 수용 형상이며 새 key/producer를 만들지 않는다. source.extraction은 null 또는 제공 JSON dict로서 기존 page_citation이 소비하는 schema_version=정확1/status:str/source/parser/pages를 포함한다. source는 filename:nonempty str와 sha256:SHA가 필수이며 기존 format/size_bytes 등 추가 metadata는 opaque JSON이다. parser는 정확2키 {name:str,version:str 또는 null}이며 parser 자체는 null이 아니다. pages는 위5키 page 배열이다. 추가 top 추출 metadata도 opaque 기본 JSON으로 보존하고 효과를 부여하지 않는다. 참조된 extraction의 실제 citable 상태·해시·줄은 부모 인용 검사에 맡기며 별도 파서를 만들지 않는다.

### observation 형상

null 외에는 기존034 capture의 정확13키 `schema_version,kind,status,reason_codes,snapshot_id,snapshot,origin,state,delegation,profile,readiness,verification,limits`다. schema_version=정확1, kind=intake_reference_snapshot_capture, status=observed/stale/unavailable다. reason_codes는 기존034 REASON_CODES의 중복 없는 문자열 배열이다. 제공 verification의 값으로 B의 권한/현재성 flag를 올리지 않는다.

| 중첩 값 | observed/stale | unavailable |
|---|---|---|
| snapshot_id/snapshot | snapshot_id=SHA. snapshot 정확13키는 기존032 형상(schema_version=1,kind=intake_case_reference_snapshot,snapshot_scope=caller_provided,intake_id,revision,revision_fingerprint,origin_job_id,analysis_context_id,result_sha256,readiness_fingerprint,synthetic,projection,projection_sha256). ID150/P/SHA/정확 bool이며 이 capture에서는 null 아님. projection은 product_type/market/model의 최소 facts와 {key} 질문 배열만. | 둘 다 null. |
| origin 정확5키 | source_id,origin_job_id는 ID150; result_sha256,analysis_context_id,raw_manifest_sha256는 SHA. | 5개 모두 null. |
| state 정확6키 | intake_status=nonempty str≤150, delegated/deferred=bool, projection_sha256/answers_sha256/questions_sha256=SHA. | 6개 모두 null. |
| delegation 정확3키 | event_id=ID150/null,history_sha256=SHA,verified=bool. | event_id/history_sha256/verified 모두 null. |
| profile 정확3키 | stored_profile_id,current_profile_id=SHA,matches=bool. | stored_profile_id/matches=null,current_profile_id=SHA. |
| readiness 정확5키 | kind=reference_preparation_v1,ready=bool,reason_codes=034 enum 배열,reference_state_fingerprint=SHA,delegation_event_id=ID150/null. | kind 동일,ready=false,reason_codes는 부모 부족 이유, 나머지2개 null. |
| verification 정확8키 | database_snapshot_observed,retained_analysis_verified,live_projection_recomputed,preparation_bound,source_integrity_observed,operational_authority_granted,model_execution_verified,evaluation_executed 모두 bool. | 같은 키/정확 bool. 이는 원 제공 capture의 선언이며 새 검증의 성과가 아니다. |
| limits 정확11키 | 기존034의 result_json_bytes=8MiB,analysis_context_bytes=4MiB,raw_manifest_bytes=4MiB,source_file_bytes=16MiB,projection_json_bytes=8MiB,state_category_json_bytes=8MiB,max_questions=10000,max_user_response_events=10000,max_answers=10,snapshot_json_bytes=9MiB,capture_json_bytes=12MiB. | 동일. |

snapshot의 facts/event_id는 기존032/034 최소 형상을 그대로 따른다. B의 full projection event_id 범위와 달리034 최소 user_confirmed 문자열 event_id는 ASCII128이다. 불지원/새 parent 버전은 형식 오류로 구별하고 값을 잘라 맞추지 않는다.

### 실제 비교 경로와 결과

일치=그 행의 추가 이유 없음, 부재=검증 불가인 `intake_binding_incomplete`, 값이 모두 있으나 다름=`intake_binding_mismatch`다. 단 부모 인용 거절은 아래 예외 행대로 source_error이고 정상 reason으로 바꾸지 않는다.

| 비교 | 규칙 |
|---|---|
| context.intake_id/revision ↔ projection.intake_id/revision | projection 쪽 키 부재/null이면 incomplete. 둘 다 있으면 정확 비교. context 필수값 부재/잘못된 타입은 invalid_input. |
| projection.submitted ↔ analysis | canonical 전체 JSON을 비교한다. 다르면 mismatch. 제출본이 없는 최소 projection은 invalid_input이다. 현재 facts를 analysis에서 새로 계산하지 않는다. |
| schema1 analysis/context | analysis에 context_id 없음은 정상이고 그 자체로 incomplete가 아니다. context.analysis_context_id는 선택 SHA이며 없어도 부모가 허용한다. context ID를 analysis에 채우지 않는다. |
| schema2 analysis.context_id ↔ context.analysis_context_id | context ID 필수 SHA. 실제 값 불일치는 validate_analysis의 거절이므로 source_error, 성공 DTO 없음. analysis가 schema2인데 text-only context이면 그 사실만으로 거절하지 않는다. |
| observation=null/unavailable | incomplete. unavailable의 원 reason_codes(legacy_analysis/no_pdf_context 등)는 원 capture에 보존하고 B의 다른 enum으로 위장하지 않는다. V1의034 정상 결과는 legacy_analysis/unavailable(snapshot=null)이다. V2도 no_pdf_context 등 unavailable일 수 있다. |
| observation=stale | 원 capture/식별을 보존하고 incomplete. 나머지 비교 가능한 값도 검사해 실제 mismatch가 있으면 함께 남긴다. observed라고 DB 현재성을 새로 검증한 것은 아니다. |
| schema1 + nonnull observed/stale snapshot | 현재034가 만들지 않는 조합이므로 mismatch. V1에 가상의 context/result binding을 만들지 않는다. |
| context.job_id/intake_id/revision/synthetic/analysis_context_id ↔ snapshot.origin_job_id/intake_id/revision/synthetic/analysis_context_id | 값이 있는 쌍은 정확 비교. 선택 context ID가 없으면 incomplete. 실제 bool과 int를 같은 값으로 보지 않는다. |
| snapshot.origin_job_id/analysis_context_id/result_sha256 ↔ origin의 같은 이름 | 중복 제공값 정확 비교. readiness_fingerprint ↔ readiness.reference_state_fingerprint도 비교. 불일치=mismatch. |
| state.projection_sha256 ↔ hash(full projection) | projection의 intake_id/revision이 모두 있는 경우에만 full JSON 전체 해시를 비교한다. 그 ID가 빠진 bare project_analysis 결과이면 incomplete로 남기며 ID를 주입해 해시를 만들지 않는다. |
| snapshot.projection/projection_sha256 ↔ 최소화(full projection)/그 해시 | facts는 원 product_type/market/model만, questions는 원 순서의 {key}만 복사한다. 값/event_id/순서를 바꾸지 않는다. 제공 최소 객체와 그 SHA를 각각 대조한다. 이 SHA를 state의 full SHA와 비교하지 않는다. |
| 검증 대상이 아닌 해시 | context의 canonical hash는 제공 model context hash이고 analysis_context_id는 보존 context blob ID다. 서로 같다고 요구하지 않는다. origin.result_sha256는 원 job result_json bytes의 해시이므로 analysis·current projection·옛 result.summary를 재직렬화해 대조하지 않는다. answers_sha256/questions_sha256/raw_manifest_sha256/revision_fingerprint는 원 제공값 보존만 하며 없는 DB 행/원 bytes를 재구성하지 않는다. |

current 답변/위임으로 facts/questions가 바뀌어도 submitted와 origin은 유지될 수 있다. 따라서 analysis.facts와 projection.facts를 동일시하지 않고 새 project_analysis/답변 basis/위임 계산을 하지 않는다. 기존 questions가 비어 있지 않으면 intake_questions_open을 남긴다.

input_binding의 intake_id/revision/analysis_context_id는 context의 값(선택 ID 부재는 null)에서만 복사한다. result_sha256는 observation.origin.result_sha256, observation_snapshot_id는 observation.snapshot_id에서 복사하며 null/unavailable은 null이다. 중복값 불일치에도 다른 값을 골라 수리하지 않는다. provided_observation_sha256는 observation 자체가 null일 때만 null이다. 나머지 provided_* hash는 이름에 해당하는 제공 객체 전체의 canonical hash다.

### 직렬화·오류 순서와 출력 limits

처리는 ①기본 JSON/UTF8/finite/depth/node ②canonical byte 예산 ③정확 schema/primitive/enum/달력 날짜·중복 ④index/문서 ID resolve·제공 binding 비교 ⑤근거 availability 기록 ⑥validate_analysis 및 가능한 page_citation/호출자 hash 비교 ⑦원 literal/metadata·기간 판정과 reason 합집합 ⑧출력 예산 순서다. 부족하다고 앞 단계 형식/부모 오류를 성공으로 바꾸지 않는다.

기본 내장 dict/list/str/int/float/bool/null만 받으며 subclass, cycle, 비문자 key, UTF-8 불가 surrogate, NaN/±Inf는 invalid_input이다. int 필드는 정확 int여야 한다. dict 키를 Unicode 순서로, 배열은 원 순서로 검사한다. root depth0, 각 key/value/list member 깊이+1; 각 container/scalar/key를 노드1로 세고 공유값도 출현마다 센다. 전체 예산 대상은 임시 {intake,proposal,sources} JSON 전체이며 각 section은 별도 canonical 크기도 잰다. canonical은 ensure_ascii=false/sort_keys=true/separators=(comma,colon)/allow_nan=false 후 strict UTF-8 bytes다. byte/문자 제한을 구별하고 초과는 limit_exceeded, 직렬화의 정수 자릿수 안전한도 초과도 limit_exceeded다. 오류 class는 IntakeTestIntentError(ValueError), code/str/args에는 원3코드만 남기고 원 예외·원문을 덧붙이지 않는다.

출력 schema_version=정확1, kind/status·정확9키·input_binding11·fields/candidate/period_checks 키는 본문 그대로다. verification 정확14키 중 `intake_citations_checked`는 참조 intake_ref가 1개 이상이고 validate_analysis가 성공했을 때만 true다. `basis_literals_checked`는 basis_ref가 1개 이상이고 모든 제공 basis_ref의 extraction/부모 인용·호출자 해시·문자 대조가 실제로 수행됐을 때만 true다(문자가 불일치한 검사도 수행한 검사다). 누락/null 근거 때문에 대조하지 못했으면 false이고 빈 all()로 true를 만들지 않는다. 다른12키는 항상 false다.

출력 limits는 아래 정확18키이며 값은 제공 입력으로 바꿀 수 없다. depth/node 상한은 입력·출력에 공통 적용한다.

```text
max_input_bytes=41943040, max_context_bytes=6291456,
max_analysis_bytes=2097152, max_projection_bytes=8388608,
max_observation_bytes=12582912, max_proposal_bytes=65536,
max_sources_bytes=8388608, max_output_bytes=2097152,
max_depth=32, max_nodes=2000000, max_source_documents=8,
max_candidates_per_field=2, max_refs_per_side=8, max_literal_chars=256,
max_institution_scope_chars=128, max_edition_chars=256,
max_workflow_scope_ids=20, max_questions=200
```

## I2 — 참조·literal 판정표

후보와 ref의 입력 순서는 보존한다. source.document_id 중복, 한 field 안 canonical 전체가 같은 candidate 중복, 한 candidate의 각 side 배열 안 같은 ref 중복은 invalid_input이다. 같은 literal이라도 origin/refs가 다르면 별도 후보로 유지한다. 다른 후보/field 사이 같은 ref 재사용은 허용하되 독립 근거 수로 승격하지 않는다. source workflow_scope_ids 중복도 invalid_input이다.

intake_ref의 fact_index/evidence_index는 0-based 정확 int이며 각각 해당 실제 배열 범위 안이어야 한다. basis_ref의 page_number/line_start/line_end는 정확 P, line_start≤line_end, text_sha256=SHA, document_id=ID128이다. 범위 밖 index/존재하지 않는 문서 ID는 invalid_input, 존재하는 extraction의 실제 page/line/source/text 불일치는 source_error다.

각 후보의 I는 intake_refs가 비어 있지 않고 **모든** ref가 explicit fact의 request-role 원 evidence.quote 안에 원 literal을 포함하며 parent 인용 검사에 성공한 경우다. inferred/uncertain 또는 product/reference-role은 원 상태를 보존하고 intake_ground_missing으로 두어 I=false다. 같은 줄의 다른 문자에만 literal이 있어도 원 evidence.quote에 없으면 I=false/literal_not_in_citation이다. 더 넓은 page_citation.quote로 원 quote를 교체하지 않는다. 이 role/status는 분석자 선언이며 실제 의미 검증 flag는 여전히 false다.

각 후보의 B는 basis_refs가 비어 있지 않고 **모든** ref에서 nonnull extraction과 artifact_sha256가 있고 page_citation이 성공하며, 반환 source_sha256=source.artifact_sha256 및 반환 text_sha256=ref.text_sha256, 반환 해당 line-range quote 안에 원 literal이 있는 경우다. source_kind/권리/검토/scope/기간은 아래 metadata 이유로 분리하며 문자 연결 bool을 규범 승인으로 사용하지 않는다. 각 ref를 조용히 버리거나 유효한 하나만 선택하지 않는다.

| 조건 | 고정 결과 |
|---|---|
| intake_refs=[] | I=false, intake_ground_missing. basis만 맞아도 연결 false. |
| basis_refs=[] | B=false, basis_missing. intake만 맞아도 연결 false. |
| 양쪽 없음 | 양쪽 부족 이유, literal_linked=false. |
| 존재하는 source의 extraction=null 또는 artifact_sha256=null | B=false/basis_missing. source metadata 이유는 별도로 합친다. 검사하지 않은 quote에 literal_not_in_citation을 붙이지 않는다. |
| caller text_sha256나 artifact SHA가 형식상 잘못됨 | invalid_input. |
| SHA 형식은 맞지만 반환 text/source SHA와 다름 | source_error, 성공 DTO 없음. page_citation만 호출하고 비교를 생략하지 않는다. |
| parent validate_analysis/page_citation 거절 | source_error. 근거 없음으로 downgrade하지 않는다. |
| 유효 인용이지만 literal이 원 quote에 없음 | 그 side=false/literal_not_in_citation. 문자열 대조는 case/공백 포함 원 literal의 정확 substring 검사다. |
| I=true, B=true, 제공 binding mismatch 없음 | candidate.literal_linked=true. incomplete만 있는 경우에도 문자 연결 자체는 표시할 수 있으나 incomplete 이유와 모든 false 권한을 유지한다. |
| I/B 중 하나 false 또는 binding mismatch | candidate.literal_linked=false. binding mismatch이면 해당 이유를 모든 candidate.reason_codes에도 넣어 field 합집합으로 보존한다. mismatch만으로 부모 호출/원 오류를 숨기지 않는다. |
| report/manufacturer/unknown·metadata·restricted/unreviewed source | 문자 대조와 별개인 I3 이유를 합친다. 문자 연결이 맞아도 normative/applicability/authority는 false다. |

field.status 우선순위는 후보0→missing(intent_missing), 서로 다른 원 literal≥2→conflicting(intent_conflicting), 나머지 단일 literal의 **모든** 후보 literal_linked=true→literal_linked, 그 외→proposed다. 동일 literal의2후보 중1개만 연결되면 proposed이며 실패 후보/이유도 보존한다. origin으로 승자를 고르지 않는다. field.reason_codes는 자기 후보/자기 missing/conflict의 합집합, top.reason_codes는 모든 field 이유+I1의 global 이유+항상 applicability_not_assessed의 정렬/중복 없는 합집합이다. 원 질문은 top.questions에 원 순서 그대로 남긴다.

## I3 — 날짜·제공 metadata 판정표

날짜는 정확 ASCII YYYY-MM-DD와 실제 달력 검증을 모두 통과해야 하며 잘못된 날짜/문자열은 invalid_input이다. 현재 날짜/시간대 기본값을 채우지 않는다. 유효 날짜 비교의 우선순위는 아래 순서다.

| 조건(먼저 일치하는 행) | period status / reason |
|---|---|
| from/to 모두 있고 from>to (as_of=null 포함) | conflicting / period_conflicting |
| as_of=null | unconfirmed / period_unconfirmed |
| 제공된 from보다 as_of가 작음 또는 제공된 to보다 큼 | outside_declared_window / period_outside_declared_window |
| from/to 중 하나라도 null | unconfirmed / period_unconfirmed. 누락을 무한대 경계로 해석하지 않는다. |
| from≤as_of≤to | in_declared_window / 추가 기간 이유 없음. 양 끝 모두 포함한다. |

따라서 as_of=from/to는 양쪽 경계가 있으면 in_declared_window, 한쪽만 제공돼 경계를 위반하지 않으면 unconfirmed다. 한쪽만 있어도 이미 제공된 경계를 위반하면 outside다. 기간 안이라는 제공 선언이 판본 현행성/실제 적용성을 증명하지 않는다.

다음 표는 **해당 후보가 참조한** source만 대상으로 모든 해당 이유를 합친다. ref가 없으면 period_checks=[]이며 source metadata 이유를 가상으로 만들지 않고 basis_missing만 남긴다. source 형식/중복 검사는 참조 여부와 무관하게 먼저 수행한다.

| 제공 상태 | 이유·literal/field 상태와의 관계 |
|---|---|
| source_kind=report/manufacturer/unknown | source_not_normative. regulation/guidance/standard는 추가 kind 이유만 없으며 규범 승인 아님. 문자 연결 bool을 변경하지 않는다. |
| representation=extract/metadata/unknown | source_status_unconfirmed. original은 이 추가 이유만 없음. 원본 진위 flag는 항상 false다. |
| review_status=unreviewed/unknown | source_status_unconfirmed. reviewed는 caller 선언이며 새 승인 아님. |
| rights_status=restricted/unknown | source_status_unconfirmed. usable도 권리의 새 판정/외부 전송 허가 아님. |
| proposal/source 기관 scope 중 하나 null | institution_scope_unconfirmed. 둘 다 nonnull 원 문자열이 다르면 scope_conflicting, 같으면 추가 이유 없음. trim/case/alias를 추정하지 않는다. 기관 scope verified는 항상 false. |
| proposal.workflow_scope_id=null | 새 enum을 추가하지 않고 항상 있는 applicability_not_assessed를 유지한다. 명시 scope를 추정하지 않는다. |
| 참조 source.workflow_scope_ids=[] | source_status_unconfirmed. nonnull proposal scope가 비어 있지 않은 제공 배열에 없으면 scope_conflicting. 일치도 제공 token 일치일 뿐이다. |
| edition=null 또는 문자열 제공 | 모두 edition_unconfirmed. proposal에 비교 가능한 별도 판본 피연산자가 없으므로 method literal을 edition parser로 해석하거나 서로 다른 문서의 edition을 비교하지 않는다. 값은 원 source에 보존한다. |
| 날짜 상태 | 위 period reason을 그대로 합친다. 다른 metadata 부족과 기간 역전은 한 이유로 덮지 않는다. |

period_checks는 각 후보의 basis_refs가 가리키는 존재하는 document_id의 유일 집합을 ASCII 순으로 정렬한 {document_id,status} 배열이다. extraction=null인 metadata source도 제공 기간은 비교할 수 있으므로 해당 문서의 period 상태를 기록한다. source/basis_ref가 없으면 []이고 가상 문서를 만들지 않는다. input refs/source 배열은 정렬하지 않는다. metadata/기간 사유는 field의 literal 개수/문자 연결 상태 우선순위를 바꾸지 않으며 top.status는 항상 review_only다.

검토의 대상은 제공 선언의 문자/형식/모순이며 institution_scope_verified/edition_currentness_verified/normative_applicability_verified/실제 모델·현재성·선택·실행 flag는 계속 false다. I1–I3 보완은 원 exact DTO/함수/한도·기존 reason enum을 넓히지 않는다.
