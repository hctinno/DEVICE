# 접수 화면의 제공 규정·방법 대조

2026-10-25 Asia/Seoul. 이미 공급받은 의뢰·후보·근거를 기존 순수 API로 대조하고, 그 결과를 접수 상세에 읽기 전용으로 표시한다. 이 연결은 모델을 호출하지 않는다. 실제 의뢰 해석·규정 적용·현재 판본·기관 적합성·실장비 또는 전체 시험소 무인화 검증은 별도다.

기존 caller가 같은 관측의 원입력을 확보한 뒤 host를 명시 구성한다. 새 입력 파일 loader나 endpoint는 없다.

```python
from labflow.ui_server import create_server

# supplied_*는 caller가 이미 보존한 원입력이다. 여기서 생성·추론하지 않는다.
server = create_server(
    workspace, host='127.0.0.1', port=0,
    intake_test_intent_inputs=((supplied_intake, supplied_proposal, supplied_sources),),
)
try:
    print(f'http://127.0.0.1:{server.server_port}/')
    server.serve_forever()
finally:
    server.server_close()
```

기존 `intake_reference_store`를 함께 빌려 준 caller는 host를 완전히 닫은 뒤 자신의 Store를 닫는다. 초기화 실패도 caller의 Store를 임의로 닫지 않는다. 기존 준비·등록 범위와 권한 설정은 별개이며 이 대조 결과가 권한을 늘리지 않는다.

`intake_test_intent_inputs`의 기본값은 `()`이며, 이때 새 API import/call·응답 키·화면 구역은 없다. 공급할 때는 `(intake, proposal, sources)`인 native tuple 하나를 바깥 tuple에 넣는다. None·list·여러 묶음은 허용하지 않는다. [부모 API 사용법](intake_test_intent_usage.md)의 원 context/analysis/full projection/제공034 observation과 명시 proposal/sources를 그대로 쓴다. lease token 등이 포함된 claim 전체 응답이나 034의 최소 projection을 원입력 대신 쓰지 않는다. V1·unavailable·null·미확인 이유를 원상태로 보존한다.

host는 bind 전에 부모 API를 한 번 호출하고 원 review9키를 고정한다. caller가 이후 입력을 바꿔도 이미 구성된 결과를 바꾸지 않는다. 입력 형상·예산·원 인용 오류는 부모의 `test_intent_invalid_input`, `test_intent_limit_exceeded`, `test_intent_source_error`로 전달하며 빈 성공으로 바꾸지 않는다.

기존 `/api/intakes`와 단건 조회는 현재 snapshot의 ID/revision 및 **전체 record.analysis** canonical hash가 공급 결과와 맞을 때만 선택 `intake_test_intent_reviews`를 포함한다. 같은 revision에서 답변·질문이 바뀌어도 이전 결과를 현재 결과로 붙이지 않는다. 미공급·미결합이면 키와 화면을 생략한다. 조회가 새 원문·034 관측·모델·worker나 대조 API를 다시 호출하지는 않는다. 기존 snapshot 조회의 SQL 읽기는 존재한다.

브라우저에서는 다음 순서로 읽는다.

1. 접수를 선택하고 **제공된 규정·방법 대조** 구역을 확인한다. 구역이 없다는 사실만으로 원 의뢰에 규정·방법이 없다고 판단하지 않는다. 기존 047/057 CLI는 이 입력을 자동 공급하지 않는다.
2. 규정과 시험방법의 원 상태·후보 literal·제공자 선언과 사유 코드를 읽는다. `missing`은 후보 미제공, `proposed`는 연결 미완료, `conflicting`은 서로 다른 후보, `literal_linked`는 양쪽 인용의 문자 연결이다. 마지막 상태도 적용성 승인이나 query 확정이 아니다.
3. 후보의 펼침 항목에서 제공 기간 대조와 인용 위치를 확인한다. Tab/Enter로 조작할 수 있으며 펼침은 추가 네트워크 동작을 만들지 않는다. 부모 결과에는 원 인용문·추출 본문이 없으므로 이 구역이 다른 현재 fact의 quote를 가져와 붙이지 않는다.
4. 제공 관측의 질문 수와 기존 질문 목록을 함께 확인한다. 질문을 자동 생성·해결·답변하지 않는다. 원인용 검사 수행2개와 미검증·미승인12개는 다르다. model_proposed는 제공자의 선언이며 실제 모델 실행 증거가 아니다.

원 literal·origin·status·reason/period/locator·null/빈 배열/false를 그대로 유지한다. unknown을 FCC·b/g/n·스마트폰·최신 판본·규정/방법으로 보완하지 않는다. 화면은 이번 모델 호출 없음과 이전 분석의 실행/품질 미검증을 명시하고, 원 verification의12 false를 펼침 안에 숨기지 않는다. 새 query/case_ids·동의·준비·등록·실행 버튼은 없다. 기존 C2는 독립된 명시 조작으로 계속 동작한다.

잘못된 선택 DTO는 새 조회 전체를 거절하고 마지막 성공 조회 안내와 화면을 유지한다. 선택·revision·늦은 응답·조회 실패·종료 시 기존 off-DOM 게시와 수명을 따른다. 새 자동 focus·hash 변경·로컬 저장·다운로드를 만들지 않는다. 이 단계에서 의도 공급자를 새로 운영하거나 규정 적용성을 판정하지 않는다.

검증은 [공개 설계](../superpowers/specs/2026-10-25-intake-test-intent-view-design.md)와 [계획](../superpowers/plans/2026-10-25-intake-test-intent-view.md)의 U01~U06을 따른다. 선언 wire 검사와 정식 jobs/034→순수 API→기존 GET→실제 DOM의 합성 관측, P0 준비와 P1 메타데이터 읽기·별도 C2 source 읽기, native 정리와 실제 모델/장비 검증은 구분한다. UTF-8·링크 검사는 기능·계측·기관 적합성의 증거가 아니다.
