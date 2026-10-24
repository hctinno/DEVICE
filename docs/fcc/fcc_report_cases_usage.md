# HCT FCC 사례 조회 계약 021 v1

2026-10-24 · Asia/Seoul. `FCC-CASE-CATALOG-021`/화면024 공통 v1 계약이다. 총괄이 keyset을 승인하고 값/분류 의미를 명료화했다. 원본 PDF·추출 본문·실제 값은 private에 보관하며 공개 테스트는 합성 자료만 쓴다.

```python
from labflow.fcc_report_cases import FccReportCaseCatalog, FccReportCaseError

catalog = FccReportCaseCatalog(packet, pdf_sources)
summary = catalog.summary()
detail = catalog.case(case_id)
matches = catalog.search(query)
linked = catalog.match_intake(projected_summary, query)
review_material = catalog.discover(query)  # 028: 검토 자료 발견, 실행 위임 없음
# JSON text 입력에는 동일 strict decoder를 사용하는 아래 helper만 제공한다.
catalog2 = FccReportCaseCatalog.from_json(packet_json, pdf_sources)
# 030: caller가 이미 확인한 범위를 명시할 때만 선택 읽기를 사용한다.
scoped = FccReportCaseCatalog(packet, pdf_sources, page_scope=page_scope)
```

`packet`은 plain dict/list와 JSON scalar만, `pdf_sources`는 정확한 `{소문자SHA256: bytes}` plain dict만 받는다. bytes subclass/bytearray/file-like/path/콜백·사용자 객체는 거절한다. 생성 중 원본 hash·크기·PDF signature/strict parse·물리 페이지·추출 근거를 검사한다. 생성 후 네 조회는 I/O·파싱·Store 변경 없이 detached 메모리 사본을 반환한다. 입력 변경과 반환값 변경은 객체/다음 조회에 영향을 주지 않는다.

## 공통 표기와 예산

아래 목록은 **정확한 키 집합**이다. 별도 명시가 없으면 누락·추가 키를 거절한다. `ID`는 `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`, `SHA`는 소문자64hex, `text(N)`은 공백만으로 구성되지 않은 길이 N 이하 문자열이다. nullable은 `null`이며 0·빈 문자열 기본값을 넣지 않는다. 정수는 `bool`을 포함하지 않는다. 날짜는 유효한 `YYYY-MM-DD`, 시각은 초/선택적 소수초와 `+09:00`을 가진 ISO8601이다. URL은 userinfo/control 문자 없는 HTTP(S) 링크이며 자동 열람하지 않는다.

| 예산 | 상한 |
|---|---|
| packet UTF-8 JSON / 깊이 / 전체 node | 4 MiB / 16 / 50,000 |
| packet 개별 문자열 / claim value 깊이 | 16,384자 / 6 |
| searches / documents / cases | 128 / 16 / 128 |
| PDF 개별 / bytes 합계 | 16 MiB / 64 MiB |
| exhibit 관계 | 문서당64 / 전체256 |
| claims | 사례당64 / 전체1,024 |
| evidence | claim당8 / 전체4,096 |
| quote / 인용 line 범위 | 8,192자 / 40줄 |
| relations / reuse IDs | 사례당32 / 사례당32 |
| 추출 페이지 / retained chars | PDF당200·전체800 / PDF당1,000,000·전체4,000,000 |
| PDF 페이지 content stream | 기존 `ExtractionLimits`의 8 MiB |
| 접수 projection JSON / 깊이 / 개별 문자열 | 8 MiB / 16 / 1 MiB |
| 단일 반환 JSON | 8 MiB |

원본·JSON·목록·합계 한도와 evidence의 형식/quote·line·각주 한도는 파서 호출 전에 검사한다. 유일하다고 명시한 ID 배열의 중복은 거절하고, 일반 노트/각주 문자열 배열의 반복은 그대로 보존한다. 전체 추출 예산이 남지 않으면 새 PDF를 미검증 성공으로 넣지 않고 limit 오류를 낸다. PDF별 기존 추출 한도에 따른 partial은 상태를 보존한다. 작업 예산은 기존 추출기의 cooperative 한계이며 OS 격리·hard timeout 보증이 아니다.

## packet의 6 top-level 키

`schema_version`, `corpus_id`, `scope`, `searches`, `documents`, `cases`만 허용한다. `schema_version`은 정수1, `corpus_id`는 ID다. 빈 corpus는 `documents=[]`, `cases=[]`, `pdf_sources={}`로 표현할 수 있다. 전체 수집 완료를 뜻하지 않는다.

### scope — 7키

- `issue_date_from`: 정확한 `2025-01-01`.
- `cutoff_at`: 실제 조사 마감 +09:00 시각. 시작일 이후여야 한다. 시각의 실제성은 제공된 조사 기록이며 API가 새 조사를 인증하지 않는다.
- `timezone`: 정확한 `Asia/Seoul`.
- `population_status`: 정확한 `unconfirmed`.
- `search_scope_notes`: `text(2048)` 배열0..32.
- `unverified_ranges`: `text(2048)` 배열0..32.
- `synthetic`: bool. 합성 fixture와 실제 private 보고서 입력을 구분한다.

### searches의 각 행 — 12키

`search_id` ID(유일), `institution_scope`(`hct_korea|hct_america|mixed|unresolved`), `query` text(4096), `url` HTTP(S), `searched_at` +09:00 시각, `status`(`ok|partial|blocked|failed`), `page_start` 양의 정수|null, `page_end` 양의 정수|null, `result_limit` 양의 정수|null, `candidate_count` 0 이상 정수|null, `unverified_ranges` text(2048) 배열0..32, `notes` text(2048)|null이다. 페이지 범위는 둘 다 null이거나 start≤end다. 검색 시각은 cutoff를 넘지 않는다. blocked/failed를 성공으로 바꾸거나 여러 검색의 중복 가능 후보 수를 모집단으로 합산하지 않는다.

### documents의 각 행 — 6키

`document_id` ID(유일), `sha256` SHA(물리 고유·중복 행 거절), `size_bytes` 양의 정수, `physical_pages` 양의 정수≤100,000, `exhibits` 배열1..64, `rights` 객체다. `pdf_sources` 키 집합은 이 SHA 집합과 정확히 같아야 한다. 실제 bytes 크기/SHA·`%PDF-` signature·strict parser 물리 페이지가 모두 일치해야 한다. HTML/malformed/읽을 수 없는 암호화/parser unavailable은 constructor 오류다. 실제 parse 가능한 image/partial/no-text PDF는 추출 상태를 보존하며 읽지 못한 페이지를 성공 근거로 쓰지 않는다.

각 `exhibits` 행의 정확한 10키:

`exhibit_id` text(128), `fcc_id` text(128)|null, `application_id` text(256)|null, `exhibit_type` text(256)|null, `url` HTTP(S)|null, `source_kind`(`official|mirror|existing_user`), `accessed_at` +09:00 시각, `official_match_status`(`unverified|listing_only|pdf_hash_matched|blocked`), `official_url` HTTP(S)|null, `search_ids` 유일 search ID 배열0..32다. 동일 문서의 같은 exhibit_id/url 관계 중복은 거절한다. 여러 다른 등재 관계는 같은 SHA 아래 유지한다. official의 url과 official_url은 FCC.gov/subdomain이어야 한다. mirror/official의 url은 null일 수 없다. listing_only/pdf_hash_matched에는 FCC official_url이 필요하다. 이 상태는 제공 검수 기록이며 API가 네트워크로 새 공식 확인을 하지 않는다. mirror PDF의 hash 검증만으로 official 상태를 올리지 않는다.

`rights`의 정확한 4키는 `status`(`private_only|permission_recorded|unresolved`), `notes` text(2048)|null, `public_redistribution_allowed` false, `external_model_use_allowed` false다. 공개 열람과 Git 재배포/외부 모델 사용 허가는 별개이며 본 API는 이를 승인하지 않는다.

공식/미러 공개 exhibit가 있는 PDF가 기존 추출기에서 encrypted로 거절되면, 021 전용 경로에서 **원본 bytes를 직접** strict reader로 한 번 읽는다. 빈 user password의 인증 결과가 정확히 USER_PASSWORD=1인 공개 permission PDF만 허용한다. reader 생성 시 단 한 번의 빈 문자열 인증을 사용하고, 인증 상태를 읽어 확인하며 재인증하지 않는다. owner 결과2·비밀 user 암호·existing_user만 있는 입력·알 수 없는 인증 상태는 거절한다. 다른 암호 인자/추측·재시도·전역 패치·원본 재작성/복호 PDF 저장은 없다. 기존 `document_extract`와 일반 접수의 encrypted 거절은 그대로다.

이 경우 parser.name은 `pypdf-public-empty-user-password`, 진단 issue.code는 `public_empty_user_password_read`다. 진단 자체는 parser 경고가 아니며 citable을 차단하지 않는다. 실제 parser 경고·관측 불가·form 누락·페이지/내용/문자/합계 예산과 literal 검증은 기존 helper와 같은 조건을 적용한다. 인증 상태 확인은 현재 pypdf의 내부 상태에 의존하므로 호환되지 않는 상태에서는 성공으로 처리하지 않는다. 원본 SHA는 전달된 bytes의 SHA이며 다시 직렬화한 PDF의 SHA가 아니다. 위 추가 정책은 입력/출력 exact keyset을 바꾸지 않는다.

### cases의 각 행 — 6키

`case_id` ID(유일), `report_group_id` ID|null, `document_ids` 유일 document ID 배열1..16, `claims` 배열0..64, `relations` 배열0..32, `reuse_group_ids` 유일 ID 배열0..32다. report_group_id는 검수자가 확인한 계열이며 번호에서 추측 생성하지 않는다. unknown/빈 reuse ID 목록을 새 독립 그룹으로 꾸미지 않는다.

각 relation은 `relation_id` ID(사례 내 유일), `kind`(`revision_of|part_of|appendix_of|exhibit_of`), `target_case_id` ID|null, `external_target` text(256)|null, `status`(`resolved|unresolved`) 5키다. resolved는 존재하는 다른 case_id와 null external_target, unresolved는 null target_case_id와 미확인 외부 식별자 문자열을 가진다.

### claim — 7키, evidence — 입력 12키

claim 키는 `claim_id` ID(사례 내 유일), `field` text(128), `value` JSON value|null, `unit` text(64)|null, `status`, `basis`, `evidence`다. field는 `report|issuer|product|method|setting|equipment|correction|result|normative` 중 하나로 시작하는 dotted 식별자다. 나머지 segment는 소문자 영문/숫자/underscore이며 전체 최대4 segment다.

status는 `reviewed|extracted|not_reported|extraction_failed|ambiguous|conflicting`, basis는 `report_fact|government_rule|guidance|standard_reference_only|developer_inference|synthetic_policy`다. not_reported/extraction_failed는 value=null·evidence=[]다. reviewed/extracted는 value≠null·evidence≥1이며 root value의 빈/공백 문자열·빈 list/dict를 거절한다. **숫자0/0.0과 bool false는 유효한 원문 값**이며 누락으로 바꾸지 않는다. 그 밖의 JSON scalar와 비어 있지 않은 구조는 주어진 타입을 보존한다. ambiguous/conflicting은 null 또는 대안 값을 유지할 수 있다. reviewed는 제공된 검수 상태이며 기관 진위·과학·법률 판정을 API가 새로 인증한 결과가 아니다. 숫자/단위/판본은 변환하거나 PASS를 법적 요구로 올리지 않는다.

evidence의 정확한 12키:

`document_id` ID, `source_sha256` SHA, `file_page` 1-based 정수, `printed_page` text(128)|null(unknown 허용), `table` text(128)|null, `row` text(128)|null, `column` text(128)|null, `footnotes` text(512) 배열0..16, `text_sha256` SHA, `line_start` 양의 정수, `line_end` 양의 정수, `quote` text(8192)다. document는 해당 case.document_ids 안에 있어야 한다.

같은 SHA의 실제 retained page와 `page_citation()` 결과에서 text hash·line 범위·**전체 선택 line quote**가 정확히 같아야 한다. citable은 page.status=ok이며 해당 페이지/전역의 parser 경고·관측 불가·누락 form resource가 없는 경우다. truncated/image/no-text/error/미처리 페이지는 거절한다. 문서가 다른 페이지/상한 때문에 partial이어도 이 조건을 통과한 페이지 literal만 사용할 수 있다. table/row/column/printed page/footnote는 제공된 위치 주석이며 PDF 기하·표 레이아웃을 새로 검증한 결과가 아니다. 구조화 value는 reviewer의 해석이고 literal 검증은 quote의 원문 대응이다. OCR·그래프 디지털화·native raw 변환은 하지 않는다.

## preview와 그룹 계약

preview의 정확한 **17키**: `case_id`, `report_group_id`, `report_number`, `revision`, `issuer_class`, `issue_date`, `scope_status`, `fcc_ids`, `product_family`, `manufacturer`, `models`, `rules`, `methods`, `equipment_models`, `review_status`, `document_ids`, `evaluation_group`이다. ID/nullable 필드는 입력 의미 그대로이며 문자열 목록은 중복 제거·안정 정렬한다.

정확한 preview 대응 field:

| preview | 검토된 claim field |
|---|---|
| report_number / revision / issue_date | `report.number` / `report.revision` / `report.issue_date` |
| issuer_class | `issuer.classification`, `issuer.legal_name`, `issuer.address` |
| fcc_ids | `report.fcc_ids` |
| product_family / manufacturer / models | `product.family` / `product.manufacturer` / `product.models` |
| rules / methods / equipment_models | `method.rules` / `method.references` / `equipment.models` |

scalar preview는 reviewed·report_fact인 단일 문자열만 사용하며 상충하면 null이다. 목록은 해당 조건의 문자열/문자열 배열만 쓴다. methods는 reviewed의 report_fact 또는 standard_reference_only도 허용한다. issue_date는 ISO 날짜다. issuer_class는 `hct_korea|hct_america|unknown`이다. **issuer.classification만** reviewed developer_inference도 허용하며, 각각 실제 페이지 근거를 가진 reviewed report_fact인 legal_name/address가 모두 있어야 알려진 분류로 표시한다. 검수 분류를 원문 report_fact로 위장하거나 HCT 단어 출현으로 분류하지 않는다.

scope_status는 `in_scope|pending|out_of_range|future`다. 미검토/상충/미기재 날짜는 pending, 시작일 이전은 out_of_range, cutoff 날짜 이후는 future다. summary/case는 이 상태를 모두 보존하고 검색 후보는 in_scope의 알려진 HCT 기관만 쓴다. review_status는 `reviewed|partial|unreviewed|conflicting`: 충돌 우선, 전 claim reviewed이면 reviewed, 일부 reviewed이면 partial, 없으면 unreviewed다. 필요한 preview가 상충해도 conflicting이다.

evaluation_group의 정확한 3키는 `eligible` bool, `keys` 문자열 배열, `missing` 고정 사유 배열이다. 알려진 family/FCC ID/report group/source SHA/reuse ID를 각각 `family:`, `fcc:`, `report:`, `source:`, `reuse:` prefix로 만든다. family/FCC ID만 trim/casefold하며 ID/SHA는 그대로 보존한다. missing은 `product_family|fcc_ids|report_group_id|reuse_group_ids|issuer_class|scope_status|review_status` 중 누락/미적격 항목이다. 모두 충족해야 eligible이다. **eligible은 제공 metadata의 로컬 조건**이며 022의 canonical family group·전체 연결 성분 평가 분리 승인이 아니다. 빈 reuse 목록은 불명으로 보수적으로 false를 유지한다. 현재 API는 train/eval 배정·점수·모델 실행을 하지 않는다.

## 모든 출력 wrapper와 document DTO

모든 wrapper의 공통 **7키**:

`schema_version` 정수1, `kind`, `corpus_id`, `execution_mode="report_derived"`, `synthetic` scope의 bool, `validation_scope="source_bytes_and_retained_page_literals_only"`, `verification`이다. verification은 정확한 5키 `hardware_verified`, `physical_verified`, `model_execution_verified`, `normative_compliance_verified`, `coverage_complete`가 모두 false다.

출력 document는 입력6키에 `extraction`, `page_index`를 더한 **8키**다. extraction은 `status`, `complete`, `total_pages`, `processed_pages`, `parser`, `issues` 6키이며 기존 추출 상태를 보존한다. parser는 `name`, `version` 2키, issue는 `code`, `file_page` 2키(전역이면 null)다. page_index의 각 행은 `file_page`, `status`, `text_sha256`, `line_count`, `citable` 5키다. 전체 retained text/PDF bytes·물리 파일 경로는 반환하지 않는다. case quote만 private 근거로 반환한다.

`summary()`는 common7 + `scope`, `searches`, `counts`, `documents`, `case_previews`의 **12 topkeys**다. scope/searches는 검증한 입력 사본, documents는 document DTO 배열, case_previews는 preview 배열이다.

counts의 정확한 **15키**는 `candidate_count` null(중복 제거 모집단 미산정), `acquired_unique_pdfs`, `parsed_unique_pdfs`, `complete_text_pdfs`, `partial_text_pdfs`, `no_citable_text_pdfs`, `exhibit_relations`, `case_count`, `reviewed_claim_count`, `gap_or_unreviewed_claim_count`, `scope_counts`, `independent_group_eligible_cases`, `normative_comparison_completed_cases` null, `development_integrated_cases` null, `model_evaluated_cases` 정수0이다. 나머지 수는 이 packet 내 0 이상 정수이며 scope_counts는 `in_scope`, `pending`, `out_of_range`, `future` 4키다. 조사/추출/검토/규정 대조/개발/평가를 혼합 완료율로 만들지 않는다.

`case(case_id)`는 common7 + `case`, `documents`의 **9 topkeys**다. case는 입력 case6키에 preview를 더한 7키이며, 출력 evidence는 입력12키에 `literal_verified=true`를 더한 13키다. documents는 그 사례의 document DTO 배열이다. evidence status는 문자 대응 검증이며 규정 적합·표 구조·측정 정확도 인증이 아니다.

## search / match_intake — 같은 12 topkeys

query는 정확한 `product_family`, `rule`, `method`, `model` 4키이며 각 값은 text(256)|null이다. 비교는 trim/casefold literal 일치만 쓴다. method 판본·모델 alias·표기 차이를 자동 대체하지 않는다. product family/rule/정확 method 세 값이 없으면 insufficient_evidence다. preview의 reviewed 조건·in_scope·기관 분류를 통과한 사례만 후보로 사용한다.

두 함수의 출력은 common7 + `query`, `status`, `reason_codes`, `intake_binding`, `matches`의 **12키**다. status는 `candidates|no_match|insufficient_evidence`다. matches의 각 행은 `preview`, `model_relation` 2키이며 model_relation은 `exact_model|related_family|unspecified`다. 모델이 지정됐는데 같은 family의 다른 모델 사례만 있으면 관련 후보를 유지하되 status=insufficient_evidence·exact_model_case_missing이다. exact_model은 문자 식별자 일치이며 같은 실물/제조사/현재 지원 승인이 아니다. exact_model 우선 후 case_id로 정렬한다. 모델 미지정이면 unspecified다.

reason_codes는 중복 없는 고정 배열로 `query_context_missing`, `no_reviewed_case`, `exact_model_case_missing`, `intake_product_unconfirmed`, `intake_market_unconfirmed`, `intake_market_not_fcc`, `intake_model_unconfirmed`, `intake_product_conflict`, `intake_model_conflict`, `intake_identity_unresolved`만 쓴다. enough query인데 현재 packet의 사례가 없으면 no_match/no_reviewed_case이며 제품 비지원 판정이 아니다.

search의 intake_binding은 null이다. match_intake는 기존 `project_analysis`의 반환 dict를 읽는다. plain JSON projection의 다른 키는 보존 대상이 아니며 facts/questions만 판단에 사용한다. facts map은 최대64개이고 사용하는 product_type/market/model fact는 `value` text(4000), `status`(`explicit|inferred|uncertain|user_confirmed`), 선택적 `event_id`(ID 또는 양의 정수)만 허용한다. user_confirmed에는 event_id가 필요하다. explicit/user_confirmed 값만 쓰며 product_identity 질문이 남으면 insufficient_evidence다.

intake_binding은 정확한 `product_family`, `market`, `model`, `fact_statuses` 4키다. 값은 지원된 확정값 또는 null이고, fact_statuses는 `product_type`, `market`, `model` 3키(실제 status 또는 null)다. market의 미국/FCC literal 허용 집합은 trim/casefold 기준 `FCC`, `US`, `USA`, `United States`, `United States of America`, `미국`이다. 그 밖의 시장·missing/inferred는 FCC로 가정하지 않는다. query family와 확정 product_type, 지정 query model과 확정 model이 다르거나 부족하면 insufficient_evidence다. query model이 null이고 접수 model이 확정됐으면 해당 model을 관계 분류에만 사용하며 query를 바꾸지 않는다. 기존 질문/승인/current generation/Store는 수정하지 않는다.

## 고정 오류

`FccReportCaseError(ValueError)`의 `.code`, `str(error)`, 유일한 `.args` 값은 다음 **9코드**다. private value/quote/bytes/URL·원시 exception/context를 넣지 않는다.

| 코드 | 의미 |
|---|---|
| `fcc_case_invalid_packet` | JSON/6topkeys/하위 schema·ID·날짜·상태·관계 오류 |
| `fcc_case_invalid_sources` | SHA:bytes 타입/집합/원본 hash·크기 불일치 |
| `fcc_case_limit_exceeded` | 깊이/개수/크기/추출·응답 예산 초과 |
| `fcc_case_pdf_invalid` | signature·strict parse·물리 페이지·암호화 PDF 오류 |
| `fcc_case_extraction_unavailable` | 요구되는 기존 PDF parser를 사용할 수 없음 |
| `fcc_case_invalid_evidence` | SHA/페이지/retained hash·line·literal·citable 불일치 |
| `fcc_case_invalid_query` | query의 정확 키/값 또는 case_id 인자 형식 오류 |
| `fcc_case_not_found` | 유효 ID의 사례가 현재 packet에 없음 |
| `fcc_case_invalid_intake` | projection/facts/questions 형식 오류 |

최초 검출 오류를 반환한다. 근거 부족/다른 제품·판본·시장 등 정상적인 비일치는 matches 상태이며 예외·실물 비지원으로 바꾸지 않는다. 생성 실패는 객체를 게시하지 않는다. 합성 회귀와 실제 P01 B001의 원본/페이지/검색·접수 검증을 별도 기록하고 전수 완료·실제 AI·실물 검증을 주장하지 않는다.

## CASE-DISCOVERY028 추가 계약 v1 — 총괄 승인

이 절은 021의 `search`/`match_intake`/평가 적격·실행 위임을 변경하지 않는 별도 읽기 API 계약이다. 기존 메모리 인덱스에 `catalog.discover(query)`를 추가한다. 별도 reader/새 packet/DB를 만들면 같은 원문 검증과 상태가 중복되므로, 검증된 객체의 조회만 확장한다. 소유 변경은 이 usage와 기존 모듈/테스트 3파일이다. 원본·기존 producer·source 권리를 보존한다.

목적은 정확한 방법·제품 사실이 있어도 다른 결과/절차의 충돌 때문에 기존 search에서 제외되는 사례, 부분 추출·미검토 사례를 **검토할 자료**로 찾는 것이다. 발견 결과는 진행 후보·지원 승인·실행 권한·평가 분리 승인이 아니다. 충돌을 reviewed로 바꾸거나 공백을 채워 넣지 않는다.

### 요청·한도·오류

요청은 기존 `query`의 정확4키/타입/trim/casefold 문자 일치를 그대로 사용한다. product_family/rule/method/model 중 하나 이상을 지정하면 부분 질의를 허용한다. 모두 null이면 `insufficient_context`/`discovery_context_missing`과 빈 items다. 경로/콜백/새 bytes·추출기·Store·외부 I/O를 받지 않는다.

생성자의 021 예산은 그대로다. 발견 조회는 사례128, 사례당 claim64, claim당 evidence8, packet 전체 evidence4096 범위만 읽으며 한 criterion의 서로 다른 reviewed_values는 최대128개다. 별도 응답 UTF-8 JSON은 기존8MiB를 적용한다. 초과하면 `fcc_case_limit_exceeded`이며 조용히 잘라낸 성공을 반환하지 않는다. 9개 고정 오류와 `FccReportCaseError`를 그대로 재사용하며 query 오류는 `fcc_case_invalid_query`다. 생성 후 조회의 입력/반환 사본·I/O0 조건도 같다.

### wrapper 정확11키

기존 common7 + `query`, `status`, `reason_codes`, `items`다. kind만 `fcc_report_case_discovery`이며 verification의 false5·report_derived·synthetic/source 검증 범위는 그대로다.

- status: `review_items|no_discovery_items|insufficient_context`.
- reason_codes: review_items이면 [], no_discovery_items이면 [`no_related_review_case`], insufficient_context이면 [`discovery_context_missing`]. 이는 현재 packet의 발견 결과이며 제품 부적합/비지원 판정이 아니다.
- query: 검증·trim한 기존4키 사본.
- items: 아래 객체 배열0..128. 숨겨진 pagination이나 truncation은 없다.

### item 정확6키

`preview`, `relation`, `criteria`, `review_issues`, `search_eligibility`, `execution_authorized`다.

preview는 기존17키/기존 값 그대로이며 충돌/partial/평가 그룹을 수정하지 않는다. execution_authorized는 항상 false다. 이는 발견 조회가 권한을 발급하지 않는다는 뜻이며 기존 사용자 위임·Store를 변경하지 않는다.

relation은 제공된 질의 조건에 한해 `criteria_matched|related_model|conflicting|unconfirmed`다. 관련 field 자체에 충돌이 있으면 conflicting, 미확인이 있으면 unconfirmed, 모두 확인됐고 모델만 다르면 related_model, 요청한 조건이 모두 일치하면 criteria_matched 순으로 정한다. 다른 field의 충돌이 있는 사례도 criteria_matched일 수 있으나 preview.review_status/검토 유의/기존 search 게이트는 충돌을 계속 표시한다. relation은 사례 전체의 검토 완료 상태가 아니다.

criteria는 정확 `product_family`, `rule`, `method`, `model`의 4키다. 각 criterion의 정확5키는 `query`, `status`, `reviewed_values`, `matched_claim_ids`, `claims`다.

- query는 해당 요청 문자열 또는 null.
- status는 `matched|conflicting|unconfirmed|mismatched|not_requested`다. null 질의에는 not_requested를 사용한다.
- reviewed_values는 해당 field의 검토된 문자열 값만 trim/casefold 중복 제거·안정 정렬한 배열0..128이다. 동등 값의 대표는 원래 문자열의 Python 문자 순서 정렬에서 처음 나온 값을 trim해 사용하고, 최종 목록은 trim/casefold 키로 정렬한다. family는 단일 문자열만, 나머지는 문자열 또는 문자열 배열만 쓴다. 숫자/false/null을 문자열로 바꾸지 않는다.
- matched_claim_ids는 요청 문자열을 문자 일치로 뒷받침하는 적격 reviewed claim ID의 유일 배열이다. 이 배열이 있어도 별도 충돌 상태를 무시하지 않는다.
- claims는 해당 field의 원래 모든 claim을 ID 순서로 보존한 아래 projection 배열0..64다. 미검토·다른 basis·충돌·숫자0/false/null도 삭제하거나 성공으로 변환하지 않는다.

field 대응은 product_family→product.family, rule→method.rules, method→method.references, model→product.models다. 확인된 문자열에는 reviewed report_fact만 사용하고 method.references만 기존처럼 reviewed standard_reference_only도 허용한다. 이는 보고서의 방법 참조이며 규범 적용 승인으로 해석하지 않는다. 다른 basis/상태/타입은 claims에 보존하되 적격 reviewed 문자열로 올리지 않는다.

claim projection의 정확6키는 `claim_id`, `status`, `basis`, `value`, `unit`, `evidence_refs`다. value/unit/status/basis는 입력의 원래 타입/값이며 field는 상위 criterion 대응으로 정한다. evidence_refs의 정확7키는 `document_id`, `source_sha256`, `file_page`, `text_sha256`, `line_start`, `line_end`, `literal_verified`다. 각 ref는 생성자에서 검증한 실제 evidence의 사본이며 마지막 값은 true다. ref는 앞의6개 위치 필드 순서의 tuple로 정렬해 입력 순서가 결과를 바꾸지 않게 한다. claim 원값과 중복을 허용하는 일반 노트/각주는 변경하지 않는다. quote·인쇄 페이지·표/행·각주는 기존 `case()`에서 확인한다. 발견 API가 원문을 재인용/재추출하거나 native raw를 만든다는 뜻이 아니다.

### 조건 판정·포함·정렬

관련 field의 explicit conflicting 상태 또는 family의 서로 다른 적격 reviewed scalar 값이 있으면 conflicting이다. ambiguous가 남으면 unconfirmed다. 그 밖에 요청과 일치하는 적격 reviewed 문자열이 있으면 matched, 적격 값이 없거나 검토되지 않은 관련 claim이 남으면 unconfirmed, 적격 값만 있고 모두 다르면 mismatched다. 요청 없는 field도 claims/알려진 값은 보존하되 status는 not_requested다.

제품군/rule/정확 method 중 **확정된 mismatched**가 있으면 해당 사례를 제외한다. 미확인·상충을 확정 불일치로 버리지 않는다. 모델이 mismatched이면 제품군/rule/method 세 조건을 모두 요청했고 모두 matched인 경우에만 related_model로 유지하며, 그 문맥이 없으면 제외한다. 모델만 지정한 질의에 임의의 다른 모델을 관련 제품으로 묶지 않는다. 따라서 미확인 사례는 넓은 질의에 unconfirmed로 발견될 수 있으나 그 조건의 일치 사례로 표시하지 않는다. 이는 기존 search의 후보 수/판정에 영향을 주지 않는다.

정렬은 relation의 criteria_matched, related_model, conflicting, unconfirmed 순서, 같은 relation 안에서는 요청한 matched criterion 수 내림차순, 마지막 case_id 오름차순이다. packet/claim/evidence 입력 순서가 발견 결과 순서를 바꾸지 않는다.

review_issues는 안정 정렬한 고정 문자열 배열이다: `case_conflicting`, `partial_review`, `unreviewed_case`, `issuer_unconfirmed`, `scope_pending`, `scope_out_of_range`, `scope_future`, `group_unconfirmed`, `source_partial`, `source_without_citable_pages`, `rights_restricted`, `official_mapping_unverified`만 쓴다. 이는 검토 유의 사항이며 실제 위반 판정이 아니다. 권리/공식 대응/추출 원래 metadata는 `case()`에서 확인한다.

search_eligibility는 정확 `eligible`, `reason_codes` 2키다. eligible은 이 **사례가 현재 query로 기존 search의 정확 후보가 될 조건**만 나타내며 match_intake·평가 그룹·실물 실행 권한을 대신하지 않는다. 기존 search가 요구하는 제품군/rule/method가 부족하거나 preview의 기관/범위/충돌 또는 정확 제품·방법/지정 모델 근거가 부족하면 false다. 지정 모델의 exact_model이 필요하며, 기존 search.matches에 related_family 행이 남았다는 사실만으로 true가 되지 않는다. 모델이 미지정이면 기존 search처럼 추가 모델 일치를 요구하지 않는다.

사유는 `query_context_missing`, `issuer_unconfirmed`, `scope_pending`, `scope_out_of_range`, `scope_future`, `case_conflicting`, `product_family_unconfirmed`, `rule_unconfirmed`, `method_unconfirmed`, `model_unconfirmed`, `product_family_mismatch`, `rule_mismatch`, `method_mismatch`, `model_mismatch`만 쓴다. 같은 사례의 기존 search 필터를 그대로 반영하고 부분 검토/그룹 불명 자체를 새로운 search 금지 조건으로 추가하지 않는다. eligible=true라도 execution_authorized는 false이며 접수 질문/승인/위임/Store를 쓰지 않는다.

### RED·실제 수용 순서

1. 기존38개/기존 인터페이스 상태를 보존하고 discover 부재와 상충 사례 발견·미확인/0false/null 보존·다른 rule/판본 제외·다른 모델 관련성·부분 질의/순서/사본·예산/I/O0를 RED로 기록한다.
2. 총괄이 승인한 정확 계약에 따라 검증된 메모리 조회만 최소 구현한다. 기존 search/match_intake/평가/실행 계약은 바꾸지 않는다.
3. 합성 발견 검사와 기존 추출·접수 회귀를 실행한다. 실제 S03 2사례와 S05 상충1사례를 각각 기존 pinned packet/원본으로 다시 생성하고 새 discover/기존 search·접수 결과·원본 불변을 대조한다. 이전 producer/실패 기록은 보존한다.
4. 소유3파일 UTF-8/정적/문서 무결성·정확 branch/remote SHA를 확인해 게시하고 총괄 독립 검토를 받는다. 023 두 경계 후속 검토가 도착하면 먼저 처리한다.

## PAGE-SCOPE030 — 선택 페이지 읽기 v1

`FccReportCaseCatalog(packet, pdf_sources, *, page_scope=None)`와 `from_json(packet_json, pdf_sources, *, page_scope=None)`의 keyword-only 정책이다. None은 기존021/028 경로·동작·producer와 동일하다. 명시 정책은 생성 전에 실제 source와 검증하며 전체 내용을 추출한 뒤 필터하지 않는다. reader/콜백/retained 결과·가짜 DTO를 주입하는 접점은 없다.

policy는 정확2키 `schema_version=1`, `sources`의 plain JSON dict다. sources는 원본 SHA를 키로 하는 plain dict이며 documents/pdf_sources의 SHA 집합과 정확히 같아야 한다. 빠진 source를 기본 전체 추출로 처리하지 않는다. 빈 corpus만 sources={}를 허용한다.

각 source entry의 정확4키는 `pages`, `mode`, `basis_id`, `basis_sha256`이다. pages는 source당1..200개/전체800개 이하의 유일한 양의 정수 배열이며 bool·중복·빈 배열·원래 physical_pages 밖을 거절한다. 입력을 바꾸지 않고 오름차순 사본으로 처리한다. mode는 `native_text|accessibility`, basis_id는 기존 ID 문법128자 이내, basis_sha256은 소문자64hex다. basis는 caller가 보존한 기존 범위 근거의 추적 참조다. API가 그 외부 문서·권한·라이선스를 인증하거나 새로 승인하지 않는다.

policy 예산은 정규 UTF-8 JSON64KiB/깊이6/node4096/source16이다. 기존 source16MiB/합계64MiB·retained 문자 source100만/합계400만·선택 페이지 content8MiB 한도를 유지한다. 모든 policy/bytes·SHA·strict page-tree leaf 수/모순 Count·범위·mode와 permission integrity를 **모든 source의 첫 native 내용 처리 전** 검증한다. Count만 실제 물리 페이지 수로 믿지 않는다. 지원하지 않는/모호한 reader 구조는 실패로 남긴다. 제한은 기존과 같은 협력적 예산이며 OS 격리·강제 timeout 보증이 아니다.

선택 밖 페이지에는 content inspection·text·image decode·OCR·render를 실행하지 않는다. strict xref/page-tree metadata 검증은 전체 원문 내용을 읽었다는 뜻이 아니다. 암호화 source는 기존 official/mirror 공개출처 gate·빈 USER 단1회·결과1만 허용한다. owner/secret/private-only 암호 경계는 유지한다. 암호화된 명시 scope는 permission integrity가 정확 True여야 하며 native_text는 EXTRACT16, accessibility는 EXTRACT_TEXT_AND_GRAPHICS512를 확인한다. printtrue만으로 native 읽기를 허용하지 않는다. 비암호 source에는 PDF permission bit가 없으며 이를 관측된 권리 허가로 만들지 않는다. copyfalse/print/accessibility·rightsunknown/private와 footer는 그대로다. 권한 변경·복호 PDF 저장·본문 일괄 export·OCR 우회는 하지 않는다.

출력 키와 enum은 추가하지 않는다. total_pages는 원래 전체 물리 페이지, processed_pages는 실제 선택 페이지 시도 수이고 page_index에는 실제 시도한 원래 file_page만 둔다. 선택 밖은 미처리로 생략하며 empty/error/가짜 hash 또는 새 not_processed 행을 만들지 않는다. 부분 선택이면 partial/complete=false이고, 선택한 페이지의 실제 ok/image_only/no_text/truncated/error·경고/폼 누락을 보존한다. 모든 물리 페이지를 명시 선택한 경우에는 기존 추출 상태 규칙을 적용한다. partial 집계는 부분 처리 상태이며 사용 가능한 본문/전체 의미 검토의 성공 수가 아니다. 실제 인용 가능 페이지와 no_citable_text_pdfs도 함께 확인한다.

진단은 전역 `page_scope_applied`, 해당 mode의 `page_scope_native_text` 또는 `page_scope_accessibility`, 요청한 페이지마다 `page_scope_requested`/file_page, 부분 선택의 전역 `page_scope_outside_unprocessed`다. encrypted 읽기에는 기존 `public_empty_user_password_read`도 남긴다. 이는 실제 parser warning과 구별하며 정상 선택 페이지의 인용을 막지 않는다. parser.name은 일반 `pypdf-selected-pages`, 공개 암호화 native `pypdf-public-empty-user-password-selected-pages`, 공개 암호화 accessibility `pypdf-public-empty-user-password-accessibility-selected-pages`다. basis private 경로/hash를 진단 문자열에 넣지 않는다.

인용에는 실제 시도한 선택 페이지의 정상·비공백 retained text와 hash/전체 선택 line quote가 필요하다. 기존 전역/해당 페이지 parser 경고·관측 불가·form resource 누락/내용 한도/오류는 그대로 차단한다. 선택 자체는 citable 승인이 아니다. 미선택/미처리 페이지를 가리키는 evidence는 fcc_case_invalid_evidence다. source의 partial이나 범위 밖 사실을 reviewed로 채우지 않는다.

기존9오류를 재사용한다. 잘못된 policy/source key/page 범위·빈/중복/bool은 invalid_packet, 예산은 limit_exceeded, 원본 SHA/크기는 invalid_sources, strict 구조/leaf·Count·암호 읽기는 pdf_invalid, mode/permission integrity/가용성 부족은 extraction_unavailable, 미선택·미인용 근거는 invalid_evidence다. 앞의 접두사 fcc_case_와 고정 문자열/args/context 규칙이 그대로 적용된다.

caller는 private에 정규 policy/hash·기존 basis pin·실제 시도/retained/citable 페이지·권한 관측과 원본 identity/mtime/mode/bytes/SHA 불변 영수증을 보존한다. API는 파일을 쓰지 않고 전체 retained 본문을 반환하지 않는다. 기존 summary/case/search/match_intake/discover·평가·권한·consumer 키를 유지한다.

실제 S04는 P01의 확인된 accessibility16쪽만 사용하고 나머지24쪽을 미처리/의미 검토 공백으로 남긴다. 새 native text/hash는 해당 parser의 실제 결과로 생성하며 P01의 다른 parser hash를 재사용하지 않는다. S06은 visual/display-list와 text/OCR0을 보존한다. native scope를 발급하거나 None/빈 pages/허구 retained hash로 성공 case를 만들지 않고 metadata+미실행 gap으로 남긴다. 공개 예제/테스트에는 합성 PDF만 사용하며, S03/S05 default producer 원바이트와 수정 없는023/024 consumer 수용을 별도로 확인한다.

## CASE-PACKET035 — manifest에서 정식 입력 준비

```python
from labflow.fcc_report_cases import prepare_fcc_case_packet

prepared = prepare_fcc_case_packet(
    manifest_bytes, {"packet.json": packet_bytes, "scope.json": scope_bytes},
    expected_manifest_sha256=trusted_manifest_sha256,
    packet_path="packet.json", page_scope_path="scope.json",
)
# 별도로 승인된 host가 원본 bytes와 범위를 결합해 실제 검증한다.
catalog = FccReportCaseCatalog(prepared["packet"], pdf_sources,
                               page_scope=prepared["page_scope"])
```

035는 고정 manifest와 명시한 canonical packet/scope JSON 두 개의 연결·입력 형식만 검사하는 메모리 API다. 원문 PDF·파일·network·DB·Store I/O, constructor/파서/추출/계산·모델·실행 호출은 0이다. 자동 경로 탐색·JSON pointer/평가식·reader/callback·출력 쓰기·CLI는 없다. 004의 CONTROL-SOURCES-008 검수/복제 영수증이나 검증된 producer로 표시하지 않는다. 권리·현재성·공식 대응·평가·실물 위임은 바뀌지 않는다.

manifest_json은 정확 bytes, expected_manifest_sha256은 별도 인수한 소문자64hex다. 실제 SHA를 JSON 해석 전에 대조하고 strict UTF-8·중복키·비유한 수치/사용자 객체를 거절한다. manifest는 request_id=`DEV-HCT-FCC-CORPUS-012`, 기존 ID128 문법의 revision, files를 필수로 갖는다. files는2..128행이고 각 행의 정확3키는 path/bytes/sha256다. path는 004의 lexical 상대 POSIX 규칙을 따르며 대소문자만 다른 중복도 거절한다. 실제 디스크·조상 안전 검증을 수행했다는 뜻은 아니다. bytes는 bool을 제외한 0 이상 정수, SHA는 소문자64hex다. 추가 top metadata는 한도 내 plain JSON으로만 받으며 지원/권리/현재성의 근거로 쓰지 않는다. source_code_executed/runtime_or_hardware_support_confirmed/public_export_allowed가 있으면 각각 정확 false여야 한다.

두 selector는 서로 다른 명시 JSON path다. json_files는 이 두 key와 정확 bytes 값만 갖는 plain dict다. 두 파일은 manifest에 있어야 하며 실제 크기/SHA가 일치해야 한다. 미소비 manifest payload까지 검수했다고 주장하지 않는다. packet은 기존021 top6/document6/claim7/**입력 evidence12**를 그대로 사용한다. 출력 evidence13의 literal_verified나 case9/producer는 입력으로 받지 않는다. scope는030 top2/source4를 그대로 사용하고 None/누락을 전체 선택으로 바꾸지 않는다. source 집합·물리 선언 범위/예산·선택 밖 근거를 metadata로 대조한다. 실제 source SHA/Count/permission integrity·본문 literal·basis 권리 검사는 이후021/030의 책임이다.

정규 bytes는 UTF-8·ensure_ascii=false·allow_nan=false·object key 정렬·compact separators·마지막 줄바꿈 없음이다. 배열 순서는 보존하고030 pages만 정렬 사본을 쓴다. trim/coercion·숫자 반올림·단위 변환·status/basis 승격은 없다. 입력/반환 사본은 격리된다.

반환 정확7키는 schema_version/kind/packet/page_scope/source_refs/provenance/verification이다. schema_version=1, kind=`fcc_case_packet_preparation`이며 packet/page_scope는 정규화한 입력 사본이다. source_refs는 document_id 순서의 정확 document_id/sha256/size_bytes/physical_pages 네 키를 갖는 선언 metadata다. 경로를 자동 만들거나 원본 대조 성공으로 쓰지 않는다. provenance의 정확4키는 manifest_sha256/consumed_files/packet_sha256/page_scope_sha256이다. consumed_files는 path순의 정확 path/bytes/sha256 두 행이고 뒤의 두 hash는 위 정규 bytes의 SHA다. verification은 정확5키이며 manifest_and_consumed_json_bytes_verified=true, source_pdf_bytes_verified=false, retained_literals_verified=false, authority_or_rights_verified=false, execution_authorized=false다.

예산은 manifest1MiB/depth16/node50000/files128, packet4MiB와 기존021 전 한도, scope64KiB/depth6/node4096, 두 blob 합계4MiB+64KiB, 반환8MiB다. PDF 선언은 source16·개별16MiB/합계64MiB·물리100000쪽 이하, 선택은 source200/총800을 실제 열지 않고 선확인한다. 협력적 예산이며 OS 격리·강제 timeout 보증은 아니다.

기존 FccReportCaseError의 네 코드만 발생시킨다: 형식/selector/path는 fcc_case_invalid_packet, 예상 manifest pin/두 blob 집합·누락·크기·SHA는 fcc_case_invalid_sources, 예산은 fcc_case_limit_exceeded, metadata 근거 상호참조/선택 밖 인용은 fcc_case_invalid_evidence다. 기존 고정 code/str/args/context와 첫 검출 오류 규칙을 유지하며 원시 경로/본문/예외를 노출하지 않는다. 기존021/030의 오류·None 경로·literal 검증은 그대로다.

P01의 서로 다른 fact 형식에서 field/value/status/basis/quote/line/textSHA를 추정하지 않는다. 같은 parser의 실제 인용이 없는 자료는 입력 미준비/gap으로 남긴다. 031의 derived outputs 영수증에는 과거 intake-v1이 없으므로 별도 metadata-only file index를 동결해 연결하며 P01/004 검수 사본으로 소급 표시하지 않는다. 실제 수용은 승인된 canonical JSON/index 재생과 원문 I/O0을 확인하며 새 PDF를 열지 않는다. 현재 인수10PDF/431쪽과 이전9/424쪽 snapshot을 구별하고 전수·전쪽 의미검토·적격10을 주장하지 않는다. UI는 metadata 준비와 기존024/033의 실제 검증 DTO를 구별하고 저장·현재성은 별도034 계약을 따른다.
