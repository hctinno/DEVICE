# 의뢰 규정·방법 검토의 최소 평가 단위

2026-10-25 Asia/Seoul. [제공 근거 대조](2026-10-25-intake-test-intent-design.md)의 소유 후보64df는 독립 제품 Yes 뒤 기능8e4ed143에 인수했고 [통합035](../../../handoff/development/INTEGRATION-035.md)의155265b9로 게시했다. 이 평가 계약은 private v1의 독립 정적 Yes/C0I0M0를 공개한 것이며 평가 제품·fixture·실행은 아직0이다. 정확 개발 base와 신규3 소유는 별도 실제 배정에서 고정한다. 구현은 [계획](../plans/2026-10-25-intake-test-intent-evaluation.md)을 따른다.

## 한 가지 추천과 실제 접점

신규3 이내의 **순수 case 평가 함수 1개**를 추천한다. 기존 `build_intake_test_intent_review(intake, proposal, sources)`를 최대 한 번 호출하고, API 실행 전에 별도로 작성·고정한 기대값과 계약 불변식을 비교한다. `FleetHarness`의 장비 action이나 분석 provider를 늘리지 않는다.

읽은 근거와 raw/LF SHA·줄·함수는 총괄 private source-map에 고정한다. 기존 `FleetHarness._proposal`은 execute/advance/stop만 받고 가상 runtime을 호출한다. `evaluate_sensor_run`은 장비 intent/receipt/observation과 author trial을 평가한다. `evaluate_case_review_references`는 FCC split/context/response/인용9키의 정확 형상을 요구한다. `build_intake_case_reference_receipt`의 evaluation은 not_executed다. 어느 것도 의뢰 검토의 규정·방법 후보/질문/기간 DTO를 직접 평가하지 않는다. 따라서 기존 평가 API만으로 신규 제품 모듈0 재사용은 부족하다. FCC evaluator의 private helper나 다른 kind의 DTO를 재해석하지 않는다.

재사용 범위는 새 검토 API의 공개 진입점과 표준 라이브러리뿐이다. 기존 평가기의 oracle 분리·고정 오류·미실행 분모는 설계 선례로만 참조한다. 기존 worker는 fixture provider만 허용하고 Store/lease/자식 process를 사용하므로 이번 평가에서 호출하지 않는다. model boundary의 prompt/decode는 분석 facts용이고 모델 호출이 아니므로 규정·방법 응답 생산기로 취급하지 않는다.

## 제안 소유와 호출 수명

향후 소유 제안은 `labflow/intake_test_intent_evaluation.py`, `tests/test_intake_test_intent_evaluation.py`, `docs/fcc/intake_test_intent_evaluation_usage.md` 신규3뿐이다. API 초안은 `evaluate_intake_test_intent_case(intake, proposal, sources, *, expectation)`이다. provider/framework/registry/DB/CLI/HTTP/UI/FIELDS/parent 변경은 0이다.

호출자는 기존 권한으로 확보한 context·원 analysis·현재 full projection·제공 observation과 proposal/sources를 메모리에 제공한다. 필요했던 Store/capture/extraction 수명은 호출자 측에서 끝낸다. 평가 함수는 파일·PDF parser·Store·network·process를 열지 않는다. API의 validate_analysis/page_citation 계산은 그대로 사용한다. 원 projection을 project_analysis로 다시 만들거나 현재 답변을 원 제출 당시 값으로 되돌리지 않는다.

평가 순서는 (1) 순수 JSON·예산·oracle 형상 검사, (2) 원 입력과 oracle 결합·검토 상태 검사, (3) 자격이 있는 한 case에서 API 1회, (4) 정상 결과 또는 고정 parent 오류와 독립 기대값 비교, (5) 입력 사후 동일성·고정 불변식 확인, (6) 작은 detached 평가 결과 반환이다. pending oracle/다른 입력 binding은 API 0회·미실행이고 점수를 만들지 않는다. 반환·오류·실제 호출 수를 구별한다.

## 독립 oracle

oracle은 API 호출 전에 원 합성 문장·원 질문·공개 계약의 판정표에서 사람이 작성하고 SHA를 고정한다. API 결과를 저장해 기대값으로 되읽거나 parent의 private 판정 함수/상수를 import하여 정답을 계산하지 않는다. 기존22개 unit의 결과를 새 독립 정답으로 복사하지 않는다. 합성 source 작성자는 API가 보는 문장과 평가자가 보관하는 기대값을 분리한다. product 함수에는 oracle을 전달하지 않는다.

`expectation`의 정확7키는 `schema_version=1`, `kind=intake_test_intent_case_expectation`, `case_id`, `case_group_id`, `input_sha256`, `label_review_status`, `expected`다. ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`, SHA는 소문자 hex64다. input SHA는 원 `{"intake": intake, "proposal": proposal, "sources": sources}`의 UTF-8 canonical JSON(sort_keys/compact/ensure_ascii=False/allow_nan=False)이다. 두 ID와 reviewed 선언은 독립 배정·자료 신원·정답 정확성의 검증이 아니다.

`label_review_status`는 pending/reviewed다. pending이면 expected는 null이다. reviewed이면 expected의 정확3키는 outcome(returned/error), error_code, review다. returned는 error_code=null과 review 객체, error는 review=null과 `test_intent_invalid_input`, `test_intent_limit_exceeded`, `test_intent_source_error` 중 하나를 요구한다. 빈 expectation·알 수 없는 키/enum·비정상 조합은 고정 평가 입력 오류다. input binding 불일치는 insufficient_evidence/API0이고 pending은 not_executed/API0이다.

반환 기대 `review`는 정확3키 fields/reason_codes/calculation_flags다. fields는 정확 rule/method이며 각각 status/candidates/reason_codes다. status는 missing/proposed/literal_linked/conflicting다. candidates는 원 후보 순서·개수와 같고 각 기대 행은 literal_linked(bool), period_checks, reason_codes만 갖는다. period_checks는 parent 계약대로 document_id/status의 고유 document_id 정렬 배열이며 status는 conflicting/unconfirmed/outside_declared_window/in_declared_window다. 이유 배열은 완전한 정렬·고유 배열을 직접 고정하고 subset 통과를 허용하지 않는다. calculation_flags는 intake_citations_checked/basis_literals_checked의 정확 bool2다.

oracle 밖의 고정 불변식도 매 반환에서 검사한다. 출력 정확9키/kind/schema/review_only, fields·후보 형상, 원 후보 literal/origin/intake_refs/basis_refs의 값과 순서 보존, 원 full projection.questions의 전체 값·순서 보존, 독립 계산한 입력 결합11, 공개 계약의 한도18, verification 정확14를 확인한다. 권한12는 항상 false여야 한다: projection_recomputed/result_projection_reverified/database_currentness_verified/source_authenticity_verified/normative_applicability_verified/institution_scope_verified/edition_currentness_verified/model_execution_verified/model_quality_verified/query_release_authorized/case_selection_authorized/execution_authorized. calculation true를 일치·적합성·권한 승인으로 바꾸지 않는다.

V1 analysis의 context_id 부재와 034 legacy_analysis/unavailable(snapshot=null)은 정상 unknown이다. V2 context 불일치의 parent source_error, full projection hash와 minimal snapshot hash의 구별, observation 미제공/stale/unavailable의 불완전 결합을 각각 별도 oracle로 둔다. original question·conflict와 partial query의 규정/방법 null을 보존한다. query/case 선택·등록·실행 결과를 생성하지 않는다.

## 최소 case 묶음과 반증

향후 새 테스트의 공개 합성 oracle 묶음은 다음 10그룹으로 고정한다. 이는 아직 실행 횟수가 아니다. 모든 정상 반환은 공통 불변식을 함께 검사한다.

| 그룹 | 사전에 정하는 의미와 반증 |
|---|---|
| E01 | 원 의뢰 quote와 basis 양쪽에 같은 SYN-RULE/SYN-METHOD가 있는 text/PDF. 원 질문은 남고 review_only, 권한 false. |
| E02 | basis만 일치/원 quote 밖에만 literal/추론·product·reference 인용. literal_linked=false. 모든 refs 중 하나라도 틀리면 실패 연결. |
| E03 | 후보0, 서로 다른 literal2, 같은 literal2 중 한쪽 미결합. missing/conflicting/proposed를 구별하고 질문 전체 보존. |
| E04 | V1/미제공·unavailable/stale/관측 DTO mismatch/현재 답변이 바뀐 projection. unknown을 성공이나 원 답변 재계산으로 바꾸지 않음. |
| E05 | 날짜 양끝 포함·바깥·일방 null·as_of null·역전+as_of null. 역전 우선 conflicting, null 경계는 무한 기간 아님. |
| E06 | 기관/업무 scope 다름·미제공, report/manufacturer/extract/rights unknown/unreviewed. literal 비교와 메타데이터 이유를 별도로 보존, edition_unconfirmed 유지. |
| E07 | 명시 model_proposed와 explicit_supplied의 동일 문장. 계약 판정이 같아도 actual model 호출/품질/점수는0/null. |
| E08 | 잘못된 ref index/중복·누락/틀린 source/text SHA와 부모 분석 결합 오류. 정확 parent 오류3과 정상 불완전 반환을 구별. |
| E09 | pending/틀린 oracle input hash/의뢰 정답으로 검토되지 않은 retained metadata. 서지 검수가 있어도 API0·미실행 분모0. 기대값만 바꿔 통과시키지 않음. |
| E10 | 유효한 반대 기대값이면 checked+fail. mock으로만 주입한 질문 삭제/권한true/조작 binding/extra query/입력 변경/예상 밖 예외를 거절. 이 mock 반증은 실제 parent 실행 분모에서 제외. |

공개 합성 oracle은 계약 회귀다. 독립 reviewer는 다른 합성 문장/질문/날짜로 별도 private oracle을 먼저 고정한 뒤 실제 API를 실행하고 자기 분모를 남긴다. 같은 문장·보고서/원 SHA·case_group_id를 바꿔 적은 복제는 독립 사례가 아니다. 독립 배정은 root의 실제 배정·리뷰 증거로만 기록하며 이 함수가 검증했다고 표시하지 않는다. 기존 FCC split은 다른 데이터 형상이므로 자동 재사용하지 않는다.

## 결과·예산·실패

제안 결과 정확15키: schema_version/kind/execution_mode/status/verdict/case_id/case_group_id/bindings/declarations/outcome/reason_codes/counts/actual_model_score/verification/limits. kind는 intake_test_intent_case_check, mode는 provided_input_contract_check다. status는 checked/insufficient_evidence/not_executed, verdict는 pass/fail/null이다. checked는 실제 비교 실행을 뜻하며 pass와 동의어가 아니다.

bindings는 input_sha256/expectation_sha256/review_sha256(미반환이면 null)이다. declarations는 context_synthetic(bool 또는 null)/proposal_origins(원 origin 고유 정렬 또는 비정상 입력이면 null)이며 자체 증명이 아니다. outcome은 status(not_executed/returned/error)/error_code(null 또는 parent 고정3)다. counts는 review_api_calls(0/1)/scored_contract_cases(0/1)/actual_model_calls(항상0)다. 실제 비교가 이루어졌으면 parent 오류의 예상 일치/불일치도 계약 case 1건이다. actual_model_score는 항상 null이다.

verification의 정확5키는 caller_label_review_declared, contract_comparison_executed, input_values_unchanged, model_execution_verified, model_quality_verified다. 앞3은 해당 실제 검사 범위에서만 true가 가능하고 뒤2는 항상 false다. API를 호출하기 전 branch에서는 input_values_unchanged=true를 만들지 않고 false다. 입력 사후 불변식 실패는 checked+fail이며 다른 통과로 상쇄하지 않는다. raw quote·본문·실측값·oracle payload·원 예외 문자열을 결과에 복사하지 않는다. reason_codes는 고정된 label_pending/input_binding_mismatch/outcome_mismatch/review_mismatch/input_changed 집합의 정렬 고유 배열이며 조합은 상태와 맞아야 한다.

형상·예산 검사는 basic native JSON(dict/list/str/int/finite float/bool/null)만 허용하고 subclasses/cycles/surrogate/nonfinite를 거절한다. 제안 evaluator 한도는 input canonical48MiB, expectation256KiB, output256KiB, depth40, nodes2,100,000, ID128, reason128자/512개다. 이는 parent40MiB/depth32/nodes2,000,000의 초과 오류도 실제 parent 오류로 비교할 작은 여유이며 parent 한도를 완화하지 않는다. 바이트/깊이/노드 초과는 의미 검사 전에 fixed limit 오류다. 오류 outcome을 비교하기 위한 parent-invalid native JSON과 evaluator 자체 unsafe JSON 거절을 구별한다.

평가 오류는 별도 ValueError subclass의 고정 invalid_input/limit_exceeded/source_error 코드로만 외부에 나온다. parent 고정3은 그대로 outcome에 기록하고, 예상 밖 예외는 통과·insufficient로 흡수하지 않는다. 원 실패·수정 전/후 stdout/stderr와 source/hash를 호출자 private run별 append 불가 새 경로에 보존한다. 이 보존은 evaluator의 I/O 기능이 아니다.

## 출처와 현재 분모

synthetic는 원 context의 선언, retained는 제공된 보유 artifact의 관측 출처, model_proposed는 후보의 선언, actual model은 실제 provider 호출 증거로 구별한다. 이번 함수는 실제 provider를 호출하지 않으므로 전 경우 actual_model_calls=0/actual_model_score=null이다. owner/독립/총괄, case/call/반환/오류/mock, 과거/현재 run을 서로 더하지 않는다.

기존 검수 metadata 재사용은 별도 읽기 전용 인수와 ACK로 관리한다. metadata만으로 원 의뢰 quote/분석·projection·extraction 결합이 없는 자료를 최종 API 입력이나 positive oracle로 자동 변환하지 않는다. 보고서의 issue date/issuer/mirror·권리 unknown/null과 workflow scope를 규정 유효성·기관 적용성·SDK 지원으로 승격하지 않는다. 복합 원필드와 fact_id는 실제 의미를 유지한다. 실제 retained carrier/원문/실측값을 공개 테스트·usage·Git에 넣지 않고 합성 계약은 그런 자료 없이 실행 가능하게 한다.

공개 평가 계약의 제품 생성/실행·새 fixture·실제 모델/API/학습·고객/수집 원문·전체 Python/Node/실물은 현재0이다. 과거 근거 대조22/관련372(22포함)·genuine API3와 독립/총괄 결과는 이전 run으로 보존하며 이 평가 단위의 새 분모에 더하지 않는다. 정적 Yes는 구현·실제 AI 품질·규범 적용성·운영 권한·전체 시험소 완료를 입증하지 않는다.
