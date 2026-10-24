# 제공 시험 의도·근거 대조 사용법

2026-10-25 Asia/Seoul. `build_intake_test_intent_review`는 이미 제공받은 접수·rule/method 후보·추출 근거를 대조하는 순수 함수다. 결과는 항상 `review_only`이며 실제 AI 이해·규정 적용·최신 판본·기관 승인이나 실행 준비를 뜻하지 않는다. [공개 설계](../superpowers/specs/2026-10-25-intake-test-intent-design.md)의 정확 형상·판정표와 [구현 계획](../superpowers/plans/2026-10-25-intake-test-intent.md)을 따른다.

```python
from labflow.intake_test_intent import build_intake_test_intent_review

# supplied_*는 같은 관측의 원 입력과 명시 공급 근거다.
# 이 예제는 접수/분석/producer/규정·방법을 새로 만들지 않는다.
review = build_intake_test_intent_review(
    supplied_intake, supplied_proposal, supplied_sources
)
```

`intake`는 `context, analysis, projection, observation` 정확4키다. context는 lease token을 제외한 기존 분석 context, analysis는 원 submission, projection은 submitted/질문을 포함한 full projection, observation은 이미 받은034 capture 또는 null이다. V1 analysis에는 context_id가 없는 것이 정상이다. V1의 정식034 unavailable·null도 원 상태로 소비하며 가상의 snapshot/result 해시를 채우지 않는다. V2 context 불일치나 잘못된 원 인용은 부모 오류로 거절한다.

`proposal`은 명시 날짜/기관 scope/workflow scope와 rule/method 후보를 받는다. 후보의 `explicit_supplied|model_proposed`는 제공자의 선언이다. 후보별 intake_refs와 basis_refs를 명시하며 unknown을 스마트폰/FCC/b/g/n/규정 판본으로 채우지 않는다. `sources`는 이미 제공된 추출 결과와 선언 metadata다. 이 함수는 파일/PDF를 새로 읽거나 Store·모델·HTTP·장비를 호출하지 않는다. 자료 준비 I/O는 caller의 별도 단계다.

문자 연결은 양쪽 모두 필요하다. intake는 모든 ref의 explicit/request **원 evidence.quote**, basis는 모든 ref의 실제 반환 page/text/source hash와 지정 line-range quote를 대조한다. 원 quote 밖의 다른 줄 문자를 가져와 연결하지 않는다. 동일 literal2후보 중 하나만 연결되면 field는 `proposed`이고, 서로 다른 literal이면 `conflicting`이다. 원 refs 순서·후보·질문과 미해결 이유를 보존한다.

source_kind·권리·검토·scope·판본·기간 이유는 문자 연결과 별도다. 보고서 문자와 연결돼도 규범 근거/권한으로 승격하지 않는다. 날짜는 실제 달력의 YYYY-MM-DD를 받고 양 끝을 포함한다. 역전 기간은 as_of 부재보다 먼저 conflicting, 한쪽 날짜 부재는 무한대 경계로 해석하지 않는다. 비교할 판본 피연산자가 없으므로 edition은 미확인 상태를 유지한다.

결과의 `input_binding`은 제공 객체의 canonical hash와 원 관측 식별을 구별한다. 034의 state.projection_sha256은 **full projection**, snapshot.projection_sha256은 **최소 projection**의 해시다. 현재 답변으로 바뀐 facts를 원 job 결과와 동일시하거나 답변/위임을 새로 계산하지 않는다. 원 result_json bytes가 없으면 그 해시를 재생성했다고 하지 않는다.

출력 verification은 검사 수행 여부2개와 항상 false인12개다. `intake_citations_checked`/`basis_literals_checked`가 true여도 의미·출처 진위·현재성·기관/판본·모델 품질·query 확정·사례 선택·실행은 승인되지 않는다. 완성 query/case_ids/등록 명령을 출력하지 않으며 [기존 부분 query 절차](intake_case_references_usage.md)의 rule/method=null과 검색 적격성/실행 권한 false를 유지한다.

## 고정 오류와 caller 보존

`IntakeTestIntentError(ValueError)`의 code/str/args에는 아래3코드만 남는다. 원문·경로·내부 parent 예외를 오류 메시지에 복제하지 않는다.

- `test_intent_invalid_input`: 잘못된 형상/기본 타입·날짜·ID·ref 범위·중복.
- `test_intent_limit_exceeded`: 문자/byte·배열·depth/node·출력 상한 또는 정수 직렬화 안전한도 초과.
- `test_intent_source_error`: 부모 인용 거절 또는 형식상 유효한 caller text/source hash의 불일치.

부족한 근거는 review_only의 원 reason으로 남기고, 형식·예산·parent 실패는 빈 성공으로 바꾸지 않는다. 긴 값을 자르거나 alias/다른 literal로 재시도하지 않는다. caller는 원 요청·제공 관측·근거와 실패 기록을 별도 보존해야 한다. 오류 재전송이 새 사실/규정 공급을 만들지는 않는다.

## 소유 검증 범위

API 부재 RED 뒤 전용22개를 포함한 실제 부모 관련372개 검사가 skip0으로 통과했다. 원 quote와 전체 줄, caller hash·중복·범위·동일 literal의 일부 연결, V1/unavailable·full/minimal hash·현재 답변, 기간/null·source metadata, 문자/byte/depth/node·입력 불변과 I/O0을 확인했다. byte 예산보다 형상 검사가 먼저 거절하던 순서 문제는 별도 RED→GREEN으로 보존했다.

별도 합성 관측은 정식 jobs/034에서 얻은 현재 capture와 원 분석/full projection을 소비했다. 준비 Store를 닫은 뒤 새 API3회에서 review_only2회/예상 source_error1회를 확인했고, 요청 원 quote에 없는 rule/method를 채우지 않았다. 실제 parent 분석3회·basis 인용5회·분석 내부 PDF 인용12회를 구별했으며 API 구간 파일/SQL/socket/subprocess/새 파서 관측은0이다. fixture는 준비 단계의 합성 자료이고 원문 고객/수집 성적서를 사용하지 않았다.

전체 회귀·실제 AI/provider/규범 적용·외부 API/현장망·실장비/측정은 이번 검증에 포함하지 않았다. 소유 검증과 독립 제품 리뷰·총괄 인수는 별도다. 문서 무결성 검사는 UTF-8/링크만 확인하며 기능·계측·기관 적합성을 입증하지 않는다.
