# Vertex 접수 비교 등록과 엄격 해석

2026-10-25, Asia/Seoul. 기존 [Vertex 연결 설계](2026-10-25-vertex-ai-connection-design.md)에 추가하는 작은 업무 연결 계약이다. [계획](../plans/2026-10-25-vertex-intake-comparison.md)을 따르며 개발3의 기존 [비교 실행기](../../../labflow/model_comparison.py), 전용 검사와 사용 문서 3개만 수정한다. 이 문서는 구현·실제 호출의 완료 증거가 아니다.

## 범위와 소유

기존 connection pair/evaluator와 API3, matrix11/selection4/row15/batch8/summary11, approval17/budget11/entry10 및 D2 receipt18을 유지한다. 신규 adapter/module/plugin/registry API/callback을 만들지 않는다. 준비된 합성 접수 S01~S03만 고정 private 상수와 명시 분기로 연결한다. 브라우저가 임의 context·경로·evaluator·payload를 설치하지 않는다.

개발1은 원 입력과 명시 wire를 준비했고, 개발2의 [REST producer](../../../labflow/vertex_response.py)는 원 canonical prompt와 literal schema를 수송한다. 개발3은 기존 [접수 builder/decoder](../../../labflow/intake_model_boundary.py)를 직접 사용한다. 화면의 등록 입력 선택·업무 상태 표시는 개발4의 별도 후속 소유다. 제공-input 계약 평가를 실제 모델 의미평가로 바꾸지 않는다.

## 원 artifact와 전송 bytes

동일 case의 모든 모델/추론 모드는 아래 명시 C1 wire와 같은 schema를 사용한다. C1은 UTF-8/ensure_ascii=False/sort_keys=True/allow_nan=False/compact comma·colon/no newline이다. 원 pretty JSON artifact는 별도로 보존하며 원 SHA와 wire SHA를 구별한다. caller가 원 pretty bytes를 보내면 자동 변환하거나 수리하지 않는다.

| scenario_id | 명시 wire bytes | 명시 wire SHA-256 |
|---|---:|---|
| intake-synthetic-s01 | 4280 | 33d8aae6d0a19b6d884666d3937453dca1c88bb254a5552183858f0fd870eb4d |
| intake-synthetic-s02 | 4380 | a357cd1443371cef1aefec6dd3c93877733a7bc21db4ba0f809c1685ef8d2bbe |
| intake-synthetic-s03 | 4342 | b9874f59e1bf3d7c2520fb1fe3553f2db7da796daf6c860b0ced310121f5c5d4 |

원 prompt artifact의 4423/4523/4485 bytes와 b01309a4/6733cf11/6fb729af로 시작하는 원 SHA는 input-pack manifest에서 별도 추적한다. 원 user context를 genuine builder에 주어 만든 DTO를 명시 C1으로 기록한 값이며, 총괄이 과거 Codex 접수 정책 회귀의 실제 stdin metadata와 세 wire를 정확 대조했다. 과거 원 응답·독립 기대는 새 prompt에 넣지 않는다.

공통 literal schema는 1410 bytes, SHA-256 `ade0333e65ad87f0028e0f4f1fab6872b162664dc3accdf63b39d6a9721e984c`다. 논리 producer는 정확 `SYN-PENDING-MODEL-RUN`이며 실제 모델 신원으로 취급하지 않는다. scenario/evaluator version은 native 정수1, pack revision은 별도 `c57-v1`, evaluator는 `intake-understanding-v1`이다.

private case descriptor exact11은 scenario_id/scenario_version/evaluator_id/evaluator_version/pack_revision/input_bundle_sha256/registration_sha256/context_sha256/producer_name/prompt/response_schema다. prompt와 response_schema는 bytes/sha256 exact2, context_sha256은 C1 context의 SHA다. 원 raw context/export SHA는 별도 manifest에 남긴다. descriptor는 새 공개 DTO나 실제 호출 권한이 아니다.

## 기존 경계의 직접 연결

public API3의 signature는 바꾸지 않는다. build_vertex_comparison_matrix, run_vertex_comparison_row, run_vertex_comparison_batch가 기존 profile/모델별 저장값·selected/matrix·override를 사용한다.

허용 prompt의 user message에서 native context를 기존 한도 내 strict JSON으로 읽고 고정 context SHA·synthetic=True·schema1을 확인한다. 고정 producer와 genuine build_analysis_prompt를 호출하여 전체 제공 prompt DTO와 C1 값이 같은지 검증한다. identity/binding/system policy를 새로 조립하거나 context를 요약하지 않는다. DOCX text=null/unsupported/requires_parser도 그대로 보존한다.

D2 완결 receipt와 기존 artifact/STOP/회수/settings/input 검증을 통과한 경우에만 원 final bytes를 genuine decode_analysis_response에 전달한다. 미완결·인증 실패·취소·unknown에서는 접수 decoder와 의미평가를 호출하지 않는다. 인용·producer·분류·불확실성 validation을 복제하지 않는다. 의존성 실패는 기존 고정 dependency 오류로 드러낸다.

strict 통과는 연결/형상 검증이다. 첫 구현의 assessment는 not_assessed/verdict=null/reason_code=semantic_evaluator_not_connected, batch.business_assessment는 not_assessed를 유지한다. 실제 의미평가는 총괄이 별도 고정한 독립 평가에서만 판정한다. 신규 decoded artifact나 Store admission은 이번 범위가 아니다. 후속 평가는 동일 context와 원 final bytes를 genuine decoder로 다시 확인할 수 있다.

## 승인·예산·실패의 보존

approval17은 실제 등록 scenario/evaluator·명시 wire pair·project/quota/auth/trial에 결합한다. 준비 묶음이나 UI bool은 승인 대신 쓸 수 없다. 첫 connection 승인으로 업무 입력을 호출할 수 없으며 이번 등록 자체는 추가 모델 호출 승인이 아니다.

기존 단일 누적 ledger와 entries/revision/reservation을 유지한다. 한도6/3072·행512/60·wall300·retry/continuation0을 바꾸지 않고, 새 scenario/profile/batch/clone/승인에서 초기화·환불하지 않는다. connection6 뒤 소진되면 업무 호출0이다. 추가 실행은 동일 이력을 보존하는 별도 유계 한도 계약과 총괄 승인이 먼저 필요하다.

부재 artifact native bytes0·known generation0, 최초 D2 오류 객체/args/code/receipt·clean chain·고정 secondary note와 active 미회수를 유지한다. 새 분기도 control 예외·unknown·no-refund·사용량/비용 null·actual/mock/replay를 구별한다. 실장비·현장망·Office·제출 권한은 추가하지 않는다.

## 검증과 후속

기존41 회귀와 신규 등록3/교차입력·producer/schema/version·변조·불완결 decoder0·누적 소진·저장 실패를 검증한다. 담당은 원 기대/응답/실패와 소유 외 source를 보존하고 독립 clone/전용 branch에서 정상 commit/push한다. 독립 검수 후 총괄이 정확 소유3·실제 의존성 결합·관련 회귀와 원격 일치를 확인한다. 합성 native/fake 검증과 실제 모델 실행은 별도다.

이후 접수 의미평가→의뢰/계획 후보→순수 operator→허용 가상 동작→기존 별도 assessment→결과 설명을 각각의 입력·실행·독립 평가 근거로 잇는다. fixture의 ai_model_called=false를 바꾸거나 transport 성공을 업무/실물 성공으로 합산하지 않는다. 전체 AI 하네스·실제 시험소 완료는 별도다.
