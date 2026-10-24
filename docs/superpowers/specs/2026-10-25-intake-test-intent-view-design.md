# 제공 규정·방법 대조 결과의 접수 화면 연결

2026-10-25 Asia/Seoul. private 계약의 독립 정적 Yes/C0I0M0 뒤 공개한 구현 계약이다. 총괄은 기존 host keyword-only 입력1과 기존 GET 선택 metadata1·아래 소유7 범위를 승인한다. 현재 제품 구현/fixture/API/HTTP/DOM 실행은0이며 정확 게시 base·전용 branch·실제 배정 뒤 개발4가 구현한다. 공급된 결과의 조건부 표시가 범위이며 실제 모델·동적 공급·규범 적용성은 별도다. [구현 계획](../plans/2026-10-25-intake-test-intent-view.md)을 따른다. 조사 기준155265b의 필요한 host/read model/main 접점은 현재 통합037 기능12ba7e에서도 바이트가 같고, 057 correction Yes는 별도 제품 검증이다.

## 확인한 공백과 한 가지 추천

인수된 `build_intake_test_intent_review(intake, proposal, sources)`는 원 context/analysis/full projection/제공034 관측과 명시 proposal/sources를 소비하는 순수 함수다. 현재 main GET은 저장 full projection과 원 submitted를 제공하지만 **원 context·제공 sources/proposal·새 review를 제공하지 않는다**. 034 capture의 최소 projection으로 이 원입력을 복원할 수 없다. 기존053 review_inputs/025/C2 preview에도 이 review9키는 없다.

추천은 **시작 때 명시 공급한 원입력 한 묶음을 기존 순수 API로 대조하고, 기존 접수 조회에 승인된 결과 원형을 선택 메타데이터로 붙여 실제 값만 읽기 전용으로 표시하는 단위**다. 기존 사실·질문·참고 준비/등록을 재구현하지 않는다. 현재 전송 경로가 이미 있다고 주장하지 않는다. 아래 kwarg/선택 키1은 이 공개 계약의 승인된 공통 변경 범위다. 정확 base·소유7 실제 배정 전 제품 변경은0이다. 새 endpoint·부모 review schema/enum·문서 parser·provider는 제안하지 않는다.

대안인 단순 ‘미연결’ 고정 안내는 이전056에서 변경0으로 결정됐고 그대로 보존한다. browser에 context/추출본문을 보내 새로 판정하는 안은 부모 검증을 복제하고 불필요한 원문 공급을 요구한다. 이번은 기존 API 결과9키를 소비하는 A만 추천한다. 자동 규정 검색/선정·대화 입력·동적 loader는 별도 단위다.

## 승인된 공통 변경 — 구현 전 접점

`create_server`의 마지막 keyword-only 인자 `intake_test_intent_inputs=()`를 제안한다. native tuple은 비어 있거나 `(intake, proposal, sources)`라는 기존 API 인자 tuple 1개만 담는다. 예시는 `((supplied_intake, supplied_proposal, supplied_sources),)`다. 새 입력 envelope/schema·callback·파일 경로를 받지 않는다. None·다른 타입·다수 묶음은 기존 `IntakeTestIntentError('test_intent_invalid_input')`로 bind 전에 거절한다.

- ()이면 API import/call0, 새로운 응답 키/화면0. 기존 main·Store=None/053 empty inputs·C2 capability는 같다.
- 명시1이면 bind 전에 공개 순수 API1회만 호출한다. context는 기존 허용7/선택 ID 형상이며 lease token/attempt/lease_until을 넣지 않는다. full projection은 제공 원형을 보존한다. 원입력을 main record/최소034/현재 답변에서 새로 만들지 않는다. 제공 관측 null·V1·stale와 부모 reason은 그대로다. 입력의 scope/기간·출처/rights는 공급 선언이며 자동 보완0이다.
- 순수 API의 원3코드는 그대로 caller에게 실패로 전달한다. 형식/예산/인용 오류를 미제공이나 빈 review로 바꾸지 않는다. parent output9키·review_only·14 verification·limits는 원형 그대로 캐시한다. input은 부모가 detached 검증하고 result를 canonical bytes로 고정해 caller의 후행 mutation을 전송하지 않는다. 별도 result 검증 API/새 parser를 만들지 않는다.
- 기존 `GET /api/intakes`와 기존 단건 GET의 성공 snapshot 뒤에만 **선택 top-level `intake_test_intent_reviews` 배열(최대1)**을 제안한다. 내부 항목은 승인된 review9키 원형이며 새 kind/status를 만들지 않는다. 미구성/현재 snapshot과 미결합이면 키 자체를 생략한다. fixture-runs·참고 history/current/prepare/append 경로는 그대로다. ASSETS/CSP/읽기 권한과 기존 응답 필수 키는 바꾸지 않는다.

현재 snapshot record의 intake_id/revision과 `input_binding`을 맞추고, **record.analysis 전체**를 기존 공개 `store.canonical` UTF8/SHA256으로 계산해 `provided_projection_sha256`와 비교한다. model.snapshot이 이미 반환한 메모리 객체만 소비하며 추가 SQL·blob/파일·034/worker 호출은0이다. ID/revision만으로 같은 revision의 답변·질문 변경을 놓치지 않는다. 비교는 전송 대상을 좁히는 기준이며 database_currentness_verified를 true로 바꾸는 검증이 아니다. full hash와 최소 snapshot hash·원 result bytes hash는 서로 대체하지 않는다. 일치하지 않는 결과를 다른 접수나 최신 결과로 표시하지 않는다.

이 필드 추가는 **승인된 기존 wire의 선택 확장1**이며 구현은 별도 exact base 실제 배정 뒤다. 부모 schema/명시 source/proposal을 확장하는 안이 아니다. 총괄이 envelope 확장/host 소유를 허용하지 않으면 이를 몰래 다른 필드에 넣지 않고 이 계약을 반환한다. 정확 공개 계약·base·소유 배정 전 구현하지 않는다. 057 demo/047 CLI에 공급 fixture를 자동 주입하지 않는다.

## 실제 표시 범위

선택 record에 결합한 제공 review가 있을 때만 사실·기존 질문 앞에 **제공된 규정·방법 대조** 구역1개를 둔다. 미제공 상태에서 고정 안내를 반복하지 않는다. 설명은 ‘제공된 인용의 문자 연결을 대조한 결과입니다. 적용성·현재성·실행 권한은 확인하지 않습니다.’로 한다.

| 부모 값 | 화면 의미 |
|---|---|
| missing | 후보 미제공 |
| proposed | 제공 후보 · 인용 연결 미완료 |
| conflicting | 서로 다른 제공 후보 |
| literal_linked | 양쪽 인용의 문자 연결 · 적용성 미판정 |

rule/method 두 상태·원 literal·origin(제공자 선언)·reason_codes·period_checks를 그대로 표시한다. null/빈 배열/false를 b/g/n·FCC·스마트폰·최신 판본·확정 방법으로 채우지 않는다. `literal_linked=true`도 규범/기관/판본 승인으로 올리지 않는다. model_proposed는 과거 공급자 선언이며 이번 연결의 모델 호출 증거가 아니다.

원 결과의 `intake_refs`는 fact/evidence index, `basis_refs`는 document/page/text hash/line locator만 담고 **인용문은 담지 않는다**. 이 화면은 그 locator만 표시한다. 특히 원 analysis와 projection.submitted가 다른 mismatch 결과에서 현재 record의 다른 quote를 가져와 붙이지 않는다. 근거 extraction 본문이나 새 PDF 다운로드를 공급하지 않는다. 기존 facts 인용은 기존 관측으로 유지한다.

원 review.questions는 같은 제공 projection의 질문이다. 기존 질문 목록을 유지하고 이 구역에는 제공 질문 수와 결합 미확인 이유를 표시한다. 질문을 새로 생성·해결·답변하지 않는다. 인용 검사 수행2개와 항상 false인 다음12개는 서로 구분하고 false12는 접힌 장식 뒤에 숨기지 않는다:

`projection_recomputed`, `result_projection_reverified`, `database_currentness_verified`, `source_authenticity_verified`, `normative_applicability_verified`, `institution_scope_verified`, `edition_currentness_verified`, `model_execution_verified`, `model_quality_verified`, `query_release_authorized`, `case_selection_authorized`, `execution_authorized`.

화면은 ‘이번 제공 대조에서 모델 호출 없음 · 기존 분석의 모델 실행/품질 미검증’을 명시한다. 새 query/case_ids/prepare/append/동의·승인 버튼0이다. 기존 C2는 별도 명시 동작이며 이 결과가 가능 여부를 바꾸지 않는다.

## 화면 수명과 작은 소유안

기존 validateSnapshot의 구조 검사와 app의 off-DOM prepareView→publishView를 재사용한다. 승인된 DTO만 검사하며 새 JSON tokenizer/document parser나 부모 판정 알고리즘을 만들지 않는다. review가 있으면 exact9·review_only·14 verification 중12false·field/status/ref 형상과 parent 한도를 확인한다. 잘못된 DTO는 기존 invalid_snapshot으로 이번 조회 전체 적용을 거절하고 마지막 성공 snapshot 안내를 유지한다. 잘라서 성공시키지 않는다.

`renderTestIntentReview(record, review)`는 app.js의 private DOM 조립으로 제안한다. textContent·기존 section/metadata/source/details/상태 설명과 DESIGN 토큰을 재사용하며 CSS/index/새asset0이다. 선택·revision·성공 refresh에서 같은 snapshot의 result만 원자적으로 교체한다. 늦은 응답/request epoch·pagehide/BFcache/destroy·C2 bubbling guard를 그대로 유지하고 추가 setter/source/current/prepare/append·자동 focus/hash/storage0이다. 390/1440·키보드 summary를 확인한다.

승인 소유7: `labflow/ui_server.py`, **신규** `tests/test_intake_test_intent_view.py`, `frontend/model.mjs`, `frontend/model.test.mjs`, `frontend/app.js`, `frontend/intake_references/browser_check.cjs`, **신규** `docs/fcc/intake_test_intent_view_usage.md`. 기존 api/read_model/analysis/jobs/034/025/Store/057·C1/C2 모듈·CSS/CSP/ASSETS·schema/공유문서는 보호한다. shared host/app/model의 이 공통 범위는 승인하며 정확 게시 base·전용 branch의 실제 배정은 별도다.

수용은 [구현 계획](../plans/2026-10-25-intake-test-intent-view.md)의 U01~U06으로 분리한다. 지금은 static source 조사/문서 검사만이며 API/HTTP/DOM/fixture/모델·실장비 실행0, 원자료/사용자 준비 요청0이다. 전체 RF·EMC 업무·물리 무인화 목표는 유지하고 이 단위를 전체 의도 이해·현행 규범 검증으로 대체하지 않는다. 총괄이 동결한 private source-map과 옛056 원결정을 보존한다.
