# Vertex 합성 의뢰 이해 등록 설계

2026-10-25, Asia/Seoul. DEV3-VERTEX-INTENT-REGISTRY-CONTRACT-004의 독립 정적 Yes 뒤 총괄이 고정한 구현 계약이다. [계획](../plans/2026-10-25-vertex-intent-registry.md)과 [기계 판독 계약](../../fcc/vertex_intent_registry_contract.json)을 함께 사용한다. fde071a5의 source/원 proof와 inputpack004/005/006을 보존한다. 이번에는 정적 확인과 private exact3만 작성하며 root 공통 pin·정확 다음 base 전 제품 수정·새 검사·모델/인증/망/Store 호출은 0이다.

## 최소 구현 단위와 소유

권고는 개발3 기존 [runner](../../../labflow/model_comparison.py), tests/test_model_comparison.py, [사용 문서](../../fcc/model_comparison_usage.md) 3개 수정이다. 고정 I01~I03 wire/schema를 별도 intent 분기로 수용하고 기존 [genuine intent 경계](../../../labflow/intake_test_intent_model_boundary.py)의 builder/decoder를 직접 호출한다. 신규 module/wrapper/framework·registry API·callback·데이터 loader를 만들지 않는다.

접수 등록 S01~S03과 intent006은 별도의 합성 등록 입력이다. S01 strict 통과를 I01 자동 실행이나 실제 접수→계획의 end-to-end 증거로 바꾸지 않는다. 실제 이전 단계의 full intake/analysis/projection/source에서 view를 고르고 preimage를 검증하는 host 연결은 후속이다.

## 확인한 원 입력

root-intake.json은 root가 인수한25 opaque payload의 metadata이며 의미 기대가 아니다. owner index17409/SHA f75d3315139de405b829ceb0096e182a9aa8654537515b089353d5ff022f09cf와 manifest4393/SHA 0c96db53d155af2fab2f4411e99462e9791b0901e898d21016c477c4f43d30c2를 대조했다. owner 입력18개와 provenance3개를 원 bytes/SHA로 확인했고 root opaque object/과거 모델 응답/독립 semantic 기대/Store를 열지 않았다. synthetic-materials3과 index의 verification 결과 본문도 이 확인에 사용하지 않았다.

| case/후보 scenario | C1 wire bytes / SHA 앞8 | literal schema bytes / SHA 앞8 |
|---|---|---|
| I01 / intent-synthetic-i01 | 4822 / a710b957 | 2694 / 937b3b9f |
| I02 / intent-synthetic-i02 | 6178 / d3214193 | 2694 / 47bfac67 |
| I03 / intent-synthetic-i03 | 4783 / 369f4bc2 | 2694 / 75e49247 |

전체 핀은 source-map에 있다. producer는 정확 SYN-PENDING-INTENT-MODEL-RUN, evaluator 후보는 intake-test-intent-semantic-v1, pack revision 후보는 intent-input-v1이다. scenario/evaluator의 실행 record version은 native int1로 고정하며 pack revision 문자열을 공통 version 키에 넣지 않는다. 현재 scenario_registered/evaluator_connected는 false다. root가 등록/evaluator 의미와 원 wire 핀을 먼저 확정한다.

세 schema는 크기만 같고 request_sha256 enum 때문에 지문이 서로 다르다. 공통 schema로 합치거나 기존1410을 재사용하지 않는다. rule/method literal은 길이1~256 문자열이며 정답 enum/const가 없다. candidate origin의 model_proposed와 구조 제약은 진짜 rule/method 정답표가 아니다. schema나 prompt에 답을 추가하지 않는다.

## 현재 연결 공백

| 현재 공개 source | 현 동작 | 필요한 최소 변경 |
|---|---|---|
| _pair | connection 및 analysis 접수3의 pair만 허용 | 고정 intent3의 ID/evaluator·서로 다른 wire/schema 허용 목록 추가 |
| _intake_context | analysis prompt5와 user의 단일 context/schema1 처리 | 기존 analysis 코드는 유지하고 intent prompt7의 중첩 request/payload를 별도 검증 |
| _decode | decode_analysis_response만 호출 | 완결 transport 후 intent의 concrete decoder 명시 분기 |
| _row/실행 결과 | analysis 여부로 reason과 semantic 상태 선택 | intent strict 상태를 구별하되 assessment/business_assessment는 not_assessed |
| 예산·보존 | 누적6/3072, I1 known0, I2 원 오류 보존 | 변경 없이 새 분기에도 동일 적용 |

generic stage engine으로 합치는 방식보다 고정 private 상수와 명시 분기가 현재 코드의 작은 후속이다. 두 input 종류의 서로 다른 형상과 검증 의미를 유지한다.

## API·DTO·private metadata

public API3의 signature는 그대로다.

```python
build_vertex_comparison_matrix(profile, prompt_bytes, response_schema_bytes, *,
    batch_id, scenario_id, evaluator_id, selection="matrix", model_id=None, overrides=None) -> dict
run_vertex_comparison_row(matrix, row_index, prompt_bytes, response_schema_bytes, *,
    adc_path, evidence_dir, budget_path, approval_path, cancel_event=None) -> dict
run_vertex_comparison_batch(matrix, prompt_bytes, response_schema_bytes, *,
    adc_path, evidence_dir, budget_path, approval_path, cancel_event=None) -> dict
```

matrix11/selection4/row15/batch8/summary11/approval17/budget11/entry10/D2 receipt18과 row.binding9는 유지한다. request_sha256 등 intent의 세부 binding을 row/receipt에 새 키로 끼우지 않는다. 원 prompt/schema/final bytes와 genuine binding에서 추적할 수 있다.

private descriptor11의 키를 유지한다: scenario_id/scenario_version/evaluator_id/evaluator_version/pack_revision/input_bundle_sha256/registration_sha256/context_sha256/producer_name/prompt/response_schema. prompt/schema는 bytes/sha256 exact2다.

intent에 한해 context_sha256은 **공개 payload3(intake_evidence/sources/scope)의 C1 SHA**로 명시 정의한다. 기존 analysis의 context SHA 의미와 원 entry는 바꾸지 않는다. input_bundle_sha256은 genuine builder에 전달하는 **공개 caller packet4(intake_view/source_views/scope/producer_name)의 C1 SHA**, registration_sha256은006 index의 원 SHA로 정의한다. 이 private metadata 정의와 전체값을 동시 게시한 기계 판독 계약으로 고정했다. 원 full intake/analysis/projection/source의 preimage를 확인했다는 뜻이 아니다.

## genuine 경계의 직접 사용

```python
build_intake_test_intent_prompt(intake_view, source_views, *, scope, producer_name) -> dict
decode_intake_test_intent_response(
    response, intake_view, source_views, *, scope, producer_name
) -> dict
```

먼저 wire/schema 원 bytes·C1·case/evaluator 핀을 확인한다. intent prompt는 schema_version/kind/binding/expected_producer/messages/verification/limits의 exact7이다. user JSON exact2는 request_sha256/request, 내부 request exact5는 schema_version/kind/binding/expected_producer/payload, payload exact3는 intake_evidence/sources/scope다. array index나 빈값을 보정하지 않고 각 native view/source/scope와 producer를 분리한다.

공개 payload SHA와 component SHA3를 대조하고 genuine builder에 원 view/source/scope/producer를 직접 전달해 **전체 prompt7의 C1 bytes 동일**을 확인한다. request의 C1 SHA와 outer request_sha256도 보존한다. system policy·scope의 as_of/institution/workflow/null·origin의 zero SHA·원 fact_index/evidence_index·문서 page/text SHA·unsupported DOCX를 수선하지 않는다. source tuple/선택 배열을 원 index인 것처럼 재번호 매기지 않는다.

D2 complete/STOP·원 artifact readback/settings/input/회수 검증 뒤에만 원 final bytes를 genuine decoder에 전달한다. request/producer/선택 주소·literal 구조 검증을 runner에 복제하지 않는다. malformed/중복키/잘못된 UTF-8·버전·request·producer·범위·한도 초과를 genuine decoder가 거절하면 strict rejected로 남긴다. transport 불완결·auth/cancel/unknown이면 intent decoder0이다.

genuine decoder의 원 response 한도는 **65536 bytes**, decoded 한도131072 bytes이며 depth32/nodes200000/int64다. D2의2MiB cap을 intent strict 허용 한도로 승격하지 않는다. 65537 bytes 등의 원본은 절단·repair·재요청하지 않고 D2가 보존한 bytes/receipt와 strict 거절을 구별한다. genuine 의존성 실패는 기존 고정 dependency 오류로 다룬다.

## origin과 semantic의 미검증 유지

각 intake-view.origin_binding의 provided_intake_sha256/provided_analysis_sha256/provided_projection_sha256/provided_sources_sha256는 네 개 모두64자리 zero SHA다. explicit fiction이며 원 preimage는 제공되지 않았다. 공개 view/payload의 계산 SHA와 이것들을 혼동하거나 zero를 새 SHA로 바꾸지 않는다.

builder/decoded의 origin_binding_verified, grounding_verified, source_authenticity_verified, source_currentness_verified, rights_verified, model_execution_verified, model_quality_verified, external_transmission_authorized, execution_authorized는 원 false를 유지한다. strict response_json/request/producer checked나 주소 membership 확인이 origin/grounding/권리·현행성·실제 모델 품질 검증을 뜻하지 않는다. D2의 actual provenance도 이 순수 decoder의 검증 flag를 true로 고치는 근거가 아니다.

runner는 genuine decoded7/binding6/proposal/verification을 재작성하거나 별도 decoded artifact를 만들지 않는다. 현재 raw artifacts로 후속 genuine 해석을 재현할 수 있다. first unit의 reason은 intent_response_verified/intent_response_invalid, assessment는 not_assessed/verdict=null/semantic_evaluator_not_connected, batch.business_assessment도 not_assessed다. evaluator ID에 semantic이 있어도 의미평가가 연결됐다는 뜻이 아니다.

[기존 제공-input 평가](../../../labflow/intake_test_intent_evaluation.py)의 actual_model_calls0/actual_model_score=null을 바꾸지 않는다. full intake/analysis/projection/source preimage가 없는006을 현재 workingStore에 입수하거나 parent review/독립 semantic 기대를 추측해 실행하지 않는다. 의미평가는 root가 별도로 작성·검토·봉인한 기대와 concrete 평가 범위가 있어야 한다.

## 승인·예산·후속

root 승인17은 intent의 정확 ID/evaluator·각 pair·project/quota/auth/trial에 결합한다. connection/analysis 승인·pack metadata bool로 intent를 호출할 수 없다. 기존 단일 누적 ledger의 entries/revision/reservation·한도6/3072·행512/60·wall300·retry/continuation0을 유지하며 새 batch/clone/scenario/승인으로 seed/reset/refund하지 않는다. 소진/active 상태면 호출0이다. 추가 유계 실행과 이력 보존 한도 변경은 root 별도 계약이다.

기존 connection/analysis S01~S03 등록·input004/005와 I1 exact absent bytes0/known0·I2 최초 D2 오류 객체/args/code/receipt·clean chain·고정 secondary note를 보존한다. intent I01~I03은 별도 등록이다. 모델 요청·사용량/비용 unknown·local 취소/원격 unknown·actual/mock/replay를 합치지 않는다.

순서는 현재51 회귀+새 intent 검사→root 독립 검수→명시 실제 실행 승인→후속 preimage 연결/semantic/계획·operator·결과 설명이다. strict 통과 뒤 다음 모델·가상 동작·Store 쓰기를 숨겨 실행하지 않는다. 전체 업무 하네스·실물/기관 적합성은 이 단위의 완료 범위가 아니다.

이 문서 게시 시점에 새 intent 제품 분기와 실제 모델 실행은 미완료다. 등록3 descriptor11의 전체값은 기계 판독 계약과 같으며, 실제 호출은 같은 누적 이력과 별도 명시 scope를 따른다.
