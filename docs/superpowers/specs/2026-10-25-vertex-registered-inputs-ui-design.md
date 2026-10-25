# Vertex 등록 입력7 보호 화면 설계

2026-10-25, Asia/Seoul. [계획](../plans/2026-10-25-vertex-registered-inputs-ui.md)을 따르는 공개 투영 초안이다. 공통 게시 전 private staging이며 제품 구현·실제 실행의 완료 증거가 아니다. 규범은 기존 vertex-intake-comparison 설계/계획(81e0)과 별도 vertex-intent-registry 설계/계획·vertex_intent_registry_contract.json(2b6ab7001db5af0c849453e2943688d9acd2ceee)이다.

현재 읽기전용 source 의존성은 cf12402c9898a10b5435356e4819d6da274d2c1f(기능abd7bece9f30a6b8392c9a7eea781a0cf12e5994/source276)이며 natural-nullable와 intent를 포함한다. D3 core/test/usage·UI·registry JSON의 전달 GitLF 핀을 대조했다. root64 PASS는 총괄 결과이고 문서 작성자의 기능 실행 결과가 아니다. 이 핀을 구현 GO로 취급하지 않는다.

## 등록과 원 pair

connection1·기존 접수 분석3·새 의뢰 이해 intent3을 같은 보호 화면의 선택기에 유지한다. 한 번에 한 case만 selected1 또는 matrix6으로 실행한다. 등록/선택/조회는 생성이나 다음 case 실행을 자동으로 만들지 않는다.

| scenario_id | evaluator_id | prompt bytes / SHA-256 | literal schema bytes / SHA-256 |
|---|---|---|---|
| DGM-AI-CONNECTION-001 | connection-json-v1 | 639 / bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230 | 321 / a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9 |
| intake-synthetic-s01 | intake-understanding-v1 | 4280 / 33d8aae6d0a19b6d884666d3937453dca1c88bb254a5552183858f0fd870eb4d | 1410 / ade0333e65ad87f0028e0f4f1fab6872b162664dc3accdf63b39d6a9721e984c |
| intake-synthetic-s02 | intake-understanding-v1 | 4380 / a357cd1443371cef1aefec6dd3c93877733a7bc21db4ba0f809c1685ef8d2bbe | 1410 / ade0333e65ad87f0028e0f4f1fab6872b162664dc3accdf63b39d6a9721e984c |
| intake-synthetic-s03 | intake-understanding-v1 | 4342 / b9874f59e1bf3d7c2520fb1fe3553f2db7da796daf6c860b0ced310121f5c5d4 | 1410 / ade0333e65ad87f0028e0f4f1fab6872b162664dc3accdf63b39d6a9721e984c |
| intent-synthetic-i01 | intake-test-intent-semantic-v1 | 4822 / a710b9573af8bd433e654da06a20269b9a312c233a0c29448e5cc694aad03238 | 2694 / 937b3b9fa423bbfea40116495dd7cbed3937a3839e17445f08f7a37e48faf83d |
| intent-synthetic-i02 | intake-test-intent-semantic-v1 | 6178 / d32141932ea3b06d5d7b1ed39166072ebabbc4228e35768c2d438e73c46271be | 2694 / 47bfac67fde55165684381d3c624a07566b2790916f148e7d3534e593ef1f75b |
| intent-synthetic-i03 | intake-test-intent-semantic-v1 | 4783 / 369f4bc2d816e821428c4acaacfe560bb885e42a15ce4b2a52884e12b65b5e7e | 2694 / 75e492477ac8d7bb8949143b46941aec089359522c1741d70f969a135434f806 |

scenario/evaluator version은 모두 native int1이다. 분석 pack c57-v1/producer SYN-PENDING-MODEL-RUN과 intent pack intent-input-v1/producer SYN-PENDING-INTENT-MODEL-RUN을 구별한다. intent2694 schema3은 request binding이 달라 각 SHA를 그대로 사용한다. C1 prompt와 literal schema의 원 bytes를 고치거나 공통 schema로 합치지 않는다.

## 기존 인터페이스와 genuine 경계

host config exact6와 scenario exact4, State12/scenario5/Run16/Cell17·route/body/capabilities·panel export/수명 API는 유지한다. version/family/decoded payload를 새 wire 키로 추가하지 않는다. 새 wrapper/module/registry API/callback은 없다. D3 public build/row/batch API3와 matrix11/selection4/row15/batch8/summary11/row.binding9/approval17/budget11/entry10/receipt18/settings16을 그대로 소비한다.

명시 ID/evaluator 매핑으로 family를 구별하되 D3 private case dict를 import하지 않는다. 기존 public build가 등록 pair의 최종 검증을 수행한다. 잘못된 family/pair/schema/evaluator와 미지원 입력은 명시 거절하고 worker/예약/모델0이다. 현재 전역 metadata gate를 모든 선택 case의 승인으로 표현하지 않고 서버에서 선택한 case와 현재 approval의 정확 pair를 다시 결합한다.

분석은 기존 build_analysis_prompt/decode_analysis_response, intent는 별도 build_intake_test_intent_prompt/decode_intake_test_intent_response를 D3가 직접 호출한다. UI가 context·request·producer·주소 검증을 복제하지 않는다. intent의 prompt7/user2/request5/payload3, 각 schema·원 view/source/scope·zero origin·false flags를 유지한다. intent context SHA는 payload3 C1이며 분석 context SHA와 정의가 다르다.

| 입력군 | strict checked/success | strict rejected/failed | assessment |
|---|---|---|---|
| 연결 | connection_verified | connection_response_invalid | not_assessed/null/connection_only |
| 접수 분석 | intake_response_verified | intake_response_invalid | not_assessed/null/semantic_evaluator_not_connected |
| 의뢰 이해 intent | intent_response_verified | intent_response_invalid | not_assessed/null/semantic_evaluator_not_connected |

native version1/1과 strict/status/reason/error를 입력군에 정확히 결합하고 unknown reason은 거절한다. 기존 connection 운영 closedset·known0/unknown·자연 nullable·원 오류/receipt를 보존한다. 완결/STOP·artifact/settings/pair/회수 검증 후 final bytes만 decoder로 전달하며 실패/incomplete/cancel/unknown은 decoder0이다. intent65536/65537 경계와 원본 보존을 지킨다.

## 상태와 미지원 범위

HTTP·응답 완결·strict·semantic 미평가와 actual/mock/replay/미확인을 분리한다. quality=not_run·batch business not_assessed·nullable usage/cost를 유지한다. 상단은 인증 메타데이터 사전 점검이며 실제 접근/완결/strict는 행별 관측으로 확인한다. 이 사소 문구 변경이 auth DTO나 접근 판정을 바꾸지 않는다.

evaluator ID에 semantic이 있어도 의미평가 연결을 뜻하지 않는다. origin4 zero SHA와 genuine verification의 origin/grounding/권리/현행성/모델품질/권한 false를 유지한다. request/producer/주소 checked나 D2 actual 전송으로 이를 true로 만들지 않는다. 제공-input 평가·실제 semantic 점수로 승격하지 않는다.

strict 통과를 의뢰 확정·규칙/방법 정답·Store admission·다음 모델·계획/가상/실장비 실행·결과 설명 완료로 표시하지 않는다. 각 입력은 별도 합성 case이며 analysis→intent 자동 연쇄는 없다. raw context/final/thought·ADC/승인·artifact 경로는 UI에 노출하지 않는다.

## 승인·예산·검증 조건

선택 case의 승인17은 해당 ID/evaluator/각 pair/project/quota/auth/trial에 결합한다. 기존 scope ID 문법과 동일 호스트 누적 ledger/revision/entries/예약을 유지한다. 한도6/3072·행512/60·wall300·retry/continuation0이며 소진/active면 모든 case 생성0이다. 등록7·새 batch/profile/scenario/clone/승인은 reset/refund·추가 actual 권한이 아니다.

기존 UI I1~I4·원 negative/Origin/session/CSRF·자기run·late response/last-good/취소/종료를 보존한다. owned HTTP 검사는 정식 D1+D3+fake concrete D2로 분석3과 intent3 모두를 통과하고 cross-family/strictfail/transport decoder0/원 origin·한도도 검증한다. producer 전체fake나 별도.local 증거로 이 owned 회귀를 대신하지 않는다.

003 정적 Yes·공통 공개 뒤 정확 구현 root base/소유6 전달·새 source-blind 봉인·명시 GO 뒤 기존 소유6만 구현한다. 읽기권위cf124와 실제 구현 base/owner 실행 수를 구별하고 추정하지 않는다. 이 투영의 기능 구현/실 raw·budget·ADC/실제 인증·모델·장비 호출은0이다.
