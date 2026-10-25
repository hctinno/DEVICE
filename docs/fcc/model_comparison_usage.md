# Vertex 연결 비교 실행

2026-10-25, Asia/Seoul. [공통 설계](../superpowers/specs/2026-10-25-vertex-ai-connection-design.md)와 [공식 모델 카탈로그](vertex_ai_connection_catalog.json)를 따르는 작은 연결 실행 경계다. [구현](../../labflow/model_comparison.py)은 프로필/설정 담당 모듈과 REST 응답 담당 모듈을 직접 연결한다. 담당 자연 완료 호환54개와 별도 intent61개를 인수한 총괄 통합 [가상 단위 검사](../../tests/test_model_comparison.py)는64개다. 담당 검증의 실제 ADC 읽기·인증 갱신·네트워크·Vertex 생성은 모두0이며, 총괄의 별도 실제 연결6회와 실패·재생 구분은 후속 통합050 기록에 기록한다.

## API와 선택

```python
build_vertex_comparison_matrix(
    profile, prompt_bytes, response_schema_bytes, *,
    batch_id, scenario_id, evaluator_id,
    selection="matrix", model_id=None, overrides=None,
) -> dict

run_vertex_comparison_row(
    matrix, row_index, prompt_bytes, response_schema_bytes, *,
    adc_path, evidence_dir, budget_path, approval_path,
    cancel_event=None,
) -> dict

run_vertex_comparison_batch(
    matrix, prompt_bytes, response_schema_bytes, *,
    adc_path, evidence_dir, budget_path, approval_path,
    cancel_event=None,
) -> dict
```

입력은 plain native dict/list/scalar, prompt/schema는 정확한 bytes다. snapshot은 호출자와 행 사이에 mutable alias를 남기지 않으며 깊이32·노드200000·int64·유한 수·유효 Unicode·canonical JSON 크기를 검사한다. C1은 UTF-8, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False의 JSON이다.

행은 항상 Argon LOW/MEDIUM/HIGH, Flash LOW/MEDIUM/HIGH의 6개 slot이다.

| selection | 실행 대상 | override |
|---|---|---|
| matrix | 6개 slot | max_output_tokens, timeout_seconds. model_id는 None이며 thinking_level을 넣으면 거절 |
| selected | 저장 selected_model 또는 명시 model_id와 해결된 level의 1개 slot | thinking_level, max_output_tokens, timeout_seconds |

selected의 다른 5개 slot은 settings=null, reason_code=not_selected다. matrix는 모델별 저장 output/timeout을 그대로 쓰고 level만 3축으로 해결한다. D1 resolve_run_settings의 원 exact16·profile revision·canonical profile/settings SHA를 검증한다. profile 저장은 이 모듈이 수행하지 않는다. max_output_tokens>512 또는 timeout_seconds>60인 유효 저장값은 budget_rejected/not_run으로 보존한다. 조용히 512/60으로 바꾸지 않는다.

```python
matrix = build_vertex_comparison_matrix(
    profile, prompt_bytes, response_schema_bytes,
    batch_id="connection-run-001",
    scenario_id="DGM-AI-CONNECTION-001",
    evaluator_id="connection-json-v1",
    selection="selected",
    model_id="gemini-4-argon",
    overrides={"thinking_level": "HIGH", "max_output_tokens": 128},
)
```

위 코드는 행 계획만 만든다. 실행 API는 labflow.ai_connection_profiles 및 labflow.vertex_response의 concrete API를 지연 로드한다. 의존성이 없으면 명시적으로 거절하며 callback·다른 공급자·Codex CLI·가짜 응답으로 대체하지 않는다.

## 등록 입력과 판정 범위

등록된 연결 scope는 DGM-AI-CONNECTION-001/version1, connection-json-v1이다. 접수 scope intake-synthetic-s01/s02/s03도 아래 명시 wire와 intake-understanding-v1로 고정 등록한다. 각 scenario/evaluator version은 정수1이며 pack revision 문자열 c57-v1과 구별한다.

| 원 bytes | 길이 | SHA-256 |
|---|---:|---|
| prompt | 639 | bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230 |
| literal schema | 321 | a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9 |

원 pair를 다른 요약이나 재직렬화 bytes로 바꿀 수 없다. connection의 strict decoder는 단일 UTF-8 JSON object exact4의 schema_version을 native int 1, status를 문자열 ok, synthetic을 true, equipment_authorized를 false로 검사한다. 중복키·비유한 수·잘못된 UTF-8·Markdown·추가 텍스트/키·bool/float 버전은 거절하고 수선하지 않는다.

연결 성공은 업무 품질 평가가 아니다. connection assessment는 not_assessed/verdict=null/connection_only이고 batch.business_assessment도 not_assessed다. 기존 접수→의뢰 이해→계획→가상시험→설명, Codex 실제 응답과 독립 기대, Fleet/Store/장비 DB를 변경하지 않는다. 등록 접수3도 실제 호출에는 해당 입력/evaluator의 별도 유계 승인이 필요하다. 논리 18셀은 18회 호출 권한이 아니다.

## 접수 등록 입력과 genuine 해석

[접수 비교 공통 설계](../superpowers/specs/2026-10-25-vertex-intake-comparison-design.md)에 따라 기존 runner의 private 상수와 명시 분기만 확장했다. public API3·모든 DTO 키·D2 receipt18을 유지하며 신규 wrapper/module·callback·임의 registry 설치를 받지 않는다.

| scenario_id | C1 wire bytes | C1 wire SHA-256 |
|---|---:|---|
| intake-synthetic-s01 | 4280 | 33d8aae6d0a19b6d884666d3937453dca1c88bb254a5552183858f0fd870eb4d |
| intake-synthetic-s02 | 4380 | a357cd1443371cef1aefec6dd3c93877733a7bc21db4ba0f809c1685ef8d2bbe |
| intake-synthetic-s03 | 4342 | b9874f59e1bf3d7c2520fb1fe3553f2db7da796daf6c860b0ced310121f5c5d4 |

세 입력은 동일 literal schema1410 bytes/SHA ade0333e65ad87f0028e0f4f1fab6872b162664dc3accdf63b39d6a9721e984c와 고정 neutral producer SYN-PENDING-MODEL-RUN을 사용한다. 원 raw prompt artifact4423/4523/4485와 명시 C1 wire의 SHA를 구별한다. caller의 pretty JSON이나 줄끝을 조용히 변환하지 않는다. 위 C1 bytes는 root가 과거 Codex의 실제 입력 metadata와 대조해 명시 선택한 값이며 원 모델 응답·독립 기대는 들어 있지 않다.

private descriptor exact11은 scenario_id/scenario_version/evaluator_id/evaluator_version/pack_revision/input_bundle_sha256/registration_sha256/context_sha256/producer_name/prompt/response_schema다. 원 inputpack004의 bundle/registration provenance와 inputpack005의 명시 C1 wire를 연결한다. context_sha256은 C1 context SHA이며 raw export 파일 SHA와 다르다. prompt/schema descriptor는 bytes/sha256 exact2다. 이 metadata는 실행 권한이나 새 공개 DTO가 아니다.

고정 prompt의 user message를 bounded strict JSON으로 읽어 context synthetic=True·schema1·C1 context SHA를 확인한다. 기존 build_analysis_prompt(context, *, producer_name)를 직접 호출해 전체 prompt DTO의 C1 값동일을 대조한다. system policy·binding·producer·원 DOCX text=null/unsupported/requires_parser를 수선하지 않는다. 등록 ID/evaluator·schema·wire/context가 맞지 않거나 genuine builder가 달라지면 인증/생성 전에 거절한다.

D2의 유효 complete receipt와 원 artifact readback을 통과한 final bytes만 기존 decode_analysis_response(response, context, *, producer_name)에 전달한다. 인용/producer/불확실성 validation은 기존 코드가 수행한다. 실패·취소·incomplete·unknown transport에서는 접수 decoder를 호출하지 않는다.

접수 strict 통과의 reason_code는 intake_response_verified, 거절은 intake_response_invalid다. assessment는 항상 not_assessed/verdict=null/reason_code=semantic_evaluator_not_connected이고 batch.business_assessment도 not_assessed다. neutral producer 선언은 실제 모델 신원이나 의미 정확도 증거가 아니다. requested/reported model은 원 settings/receipt에서 구별한다. 실제 의미평가는 root가 별도 고정한 독립 평가에서만 수행한다.

새 decoded artifact·Store admission·제공-input 계약 평가 승격·숨은 다음 모델 호출·가상 동작은 추가하지 않는다. 원 final bytes와 context로 후속 genuine 해석을 재현할 수 있다. 기존 I1 known0/부재 bytes0과 I2 최초 transport 오류·원 receipt/partial 보존을 접수 분기에도 적용한다.

## Intent 등록과 원 origin 미검증

[고정 intent 설계](../superpowers/specs/2026-10-25-vertex-intent-registry-design.md)·[기계 계약](vertex_intent_registry_contract.json)의 세 descriptor11을 기존 core의 명시 분기에 추가했다. 신규 제품 함수·helper·wrapper·registry API·callback은 없다. 공개 API3와 matrix/row/batch/receipt의 키를 유지한다.

| scenario_id | C1 wire bytes / SHA-256 | literal schema bytes / SHA-256 |
|---|---|---|
| intent-synthetic-i01 | 4822 / a710b9573af8bd433e654da06a20269b9a312c233a0c29448e5cc694aad03238 | 2694 / 937b3b9fa423bbfea40116495dd7cbed3937a3839e17445f08f7a37e48faf83d |
| intent-synthetic-i02 | 6178 / d32141932ea3b06d5d7b1ed39166072ebabbc4228e35768c2d438e73c46271be | 2694 / 47bfac67fde55165684381d3c624a07566b2790916f148e7d3534e593ef1f75b |
| intent-synthetic-i03 | 4783 / 369f4bc2d816e821428c4acaacfe560bb885e42a15ce4b2a52884e12b65b5e7e | 2694 / 75e492477ac8d7bb8949143b46941aec089359522c1741d70f969a135434f806 |

producer는 SYN-PENDING-INTENT-MODEL-RUN, evaluator는 intake-test-intent-semantic-v1, numeric scenario/evaluator version은1, pack revision은 intent-input-v1이다. schema 크기는 같지만 case별 request SHA enum 때문에 서로 다른 bytes/SHA를 쓴다. rule/method literal에는 정답 enum/const가 없으며 프로그램에 정답이나 빈 배열 fallback을 삽입하지 않는다.

intent descriptor의 context_sha256은 공개 payload3(intake_evidence/sources/scope)의 C1 SHA다. input_bundle_sha256은 공개 caller packet4(intake_view/source_views/scope/producer_name)의 C1 SHA, registration_sha256은 input006 index의 원 SHA다. 기존 analysis context 정의·원004005를 바꾸지 않는다. 공개 view/payload의 지문 일치는 원 full intake/analysis/projection/source의 preimage 확인이 아니다.

기존 검증 함수의 명시 분기에서 prompt7·user exact2·request exact5·payload exact3를 읽고 component SHA3·payload/caller packet/request·producer를 대조한다. 원 view/source/scope로 기존 build_intake_test_intent_prompt(intake_view,source_views,*,scope,producer_name)를 직접 호출하여 전체 C1 wire와 같은지 확인한다. 원 scope null/as_of·fact_index/evidence_index·page/text 주소와 unsupported DOCX를 수선하지 않는다.

D2 complete/STOP·원 artifact/settings/input·회수 검증 뒤에만 원 final bytes를 decode_intake_test_intent_response(response,intake_view,source_views,*,scope,producer_name)에 그대로 전달한다. genuine decoder의 response cap65536/decoded cap131072·depth32/nodes200000/int64를 유지한다. D2 cap2MiB 안이어도 65537 응답은 strict 거절하며 원 artifact를 절단하거나 수리하지 않는다. failed/auth/incomplete/unknown transport에서는 intent decoder를 호출하지 않는다.

input006의 origin_binding4는 정확한 zero SHA 선언이다. origin_binding_verified/grounding_verified/source_authenticity_verified/source_currentness_verified/rights_verified/model_execution_verified/model_quality_verified/external_transmission_authorized/execution_authorized의 원 false를 유지한다. 주소 membership이나 request/producer checked는 원본·현행성·권리·모델 품질/권한 증거가 아니다. genuine decoded7·binding6·proposal·verification을 재작성하거나 새 decoded artifact에 저장하지 않는다.

strict 성공/거절 reason은 intent_response_verified/intent_response_invalid다. evaluator 이름에 semantic이 있어도 assessment는 not_assessed/verdict=null/semantic_evaluator_not_connected, batch.business_assessment도 not_assessed다. 원 full preimage를 갖지 않은 input006을 기존 Store에 입수하거나 제공-input 계약 평가를 실제 의미평가로 바꾸지 않는다.

intent3은 독립된 등록 입력이다. 기존 접수 strict 성공 후 자동으로 intent/다음 모델·가상 동작·Store 작업을 실행하지 않는다. connection/analysis 승인으로 intent를 호출할 수 없고 같은 누적6/3072·소진/active·I1/I2를 유지한다. 추가 실제 실행/승인/예산 회수는 root의 별도 범위다. 신규10은 가상 전송과 genuine builder/decoder의 parser/주소 검증이며 실제 모델 규칙/방법 품질 점수는 아니다.

## 호스트 승인과 누적 예산

adc_path, evidence_dir, budget_path, approval_path는 보호된 호스트가 정한 absolute native Path여야 한다. UI body의 임의 경로를 전달하지 않는다. reparse/symlink, Windows 짧은 이름·ADS·device/UNC 경로, regular file의 hardlink를 거절한다. evidence_dir는 새 폴더 또는 빈 폴더이며 부모가 이미 있어야 한다. 원 자료를 덮어쓰지 않는다. cancel_event는 정확한 threading.Event 또는 None이고 미리 set됐으면 metadata 검사·worker·인증·생성·예약 모두 0이다.

승인은 root가 seed한 private exact17이다. UI bool이나 기존 prepared.json으로 열 수 없다. 키는 schema_version, kind, approval_id, scope_id, budget_id, project_id, quota_project_id, auth_profile_id, scenario_id, evaluator_id, prompt_sha256, response_schema_sha256, execution_mode, trial, limits, issued_at, expires_at이다. kind는 vertex_comparison_approval이다.

scope는 선택한 고정 등록 pair·scenario/evaluator, project/quota project-a6310591-f8cc-487c-9e3, auth profile, root_console의 confirmed 무료 체험 관측에 결합한다. 양의 KRW 크레딧 문자열·잔여1~90일·관측시각·최대24시간 유효기간을 검증한다. 새 profile revision·model/level/override·selected/matrix·batch도 같은 scope에서 쓸 수 있다. 각 실행의 원 profile/settings/matrix/pair SHA는 별도로 다시 검증한다. 승인은 실시간 잔액 조회나 과금0의 보증이 아니다.

고정 limits exact7은 generation_posts=6, max_output_tokens=512, reserved_output_tokens=3072, timeout_seconds=60, wall_seconds=300, retries=0, continuations=0이다. 프로필은 공식 global/us/eu·허용 model2/level3만 받는다. 요청과 quota project가 다르거나 알 수 없는 설정은 거절한다. 모델 접근 권한은 metadata 검사로 입증되지 않는다. D2 inspect의 model_access_verified=false를 실제 생성 성공으로 처리하거나 그 자체만으로 생성 전 거절하지 않는다.

budget_path는 증거 폴더와 별도의 단일 호스트 누적 파일이다. 신규 batch·프로필·프로세스·UI·복제본·추가 승인으로 초기화하지 않는다. 누락/손상 파일을 0으로 만들지 않는다. root만 처음 exact11을 seed하고 필요한 회수를 수행한다.

```text
schema_version, kind, budget_id, project_id, revision,
call_limit, output_token_limit, reserved_calls, reserved_output_tokens,
active_run_id, entries
```

kind=vertex_comparison_budget, 최초 한도6/3072, revision0, 예약0, active_run_id=null, entries=[]다. entries의 exact10은 reservation_id, batch_id, run_id, row_index, matrix_sha256, settings_sha256, output_tokens, state, record_ref, receipt_ref다. 누적 합계·revision·중복 run/reservation·active 상태를 재검증한다.

짧은 nonblocking OS 파일 잠금 아래 현재 파일과 revision을 확인하고 call1/실제 output cap을 fsync·atomic replace로 예약한다. RPC 동안 파일 잠금을 잡지 않으며 active_run_id가 동시 in-flight를 막는다. 같은 batch/index의 결정적 run_id는 다시 예약하지 않는다. 실패·취소·응답 불명 후 예약을 refund하지 않는다. 제어 예외나 프로세스 중단 때 active 예약이 남으면 root 대조 전 다음 생성이 막힌다. 다른 PC의 ledger가 Git으로 자동 동기화됐다고 가정하지 않는다.

각 실행의 monotonic wall300은 입력 검증부터 센다. 다음 요청의 원 timeout+D2 cleanup6초가 잔여 시간에 들어가지 않으면 wall_limit/not_run이다. 예약 전후와 호출 직전에 취소·승인/만료·시간을 다시 검사한다. 이미 예약한 뒤 중단되어도 예약은 남으며 generation_post_attempts=0과 구별된다. D2 timeout을 줄이거나 retry/continuation/repair/fallback하지 않는다. batch는 첫 실패·불명·선택 행의 거절 뒤 나머지 선택 행을 batch_stopped/not_run으로 남긴다.

## 응답, 보존 파일과 상태

D2 성공 tuple2만 strict decoder에 전달한다. receipt18의 settings/bindings·request host/model/quota·시도 횟수·STOP·worker 회수·의존성·usage/cost·취소/검증 상태와 artifact6를 검사한다. 원 request/schema/settings/provider request는 원 bytes와 대조하고, provider response/final text는 파일 크기·SHA·완결성으로 읽기 대조한다. 반환 final bytes도 파일과 같아야 한다. raw/thought 내용을 UI나 로그에 복사하지 않는다.

D2의 부재 artifact는 present=false, bytes=정확한 native int 0, sha256=null, complete=false, overflow=false, extent=absent로 받는다. bytes의 null/bool/float/다른 정수는 보정하지 않고 거절한다.

자연 완료에서는 genuine D2가 cancellation.requested=false/local_worker_stopped=null을 반환한다. local_worker_stopped는 취소를 요청했을 때만 회수 관측값을 기입하므로 null을 완료 실패로 해석하지 않는다. cleanup.worker_reaped=true/worker_exit_code=0/두 handle 종료, HTTP200/STOP, 원 artifact/verification 등 모든 기존 성공 조건은 그대로 필요하다. 원 nullable 값은 보정하지 않고 보존한다. 기존 명시 True 영수증과 fixture도 호환 유지하며 False·bool이 아닌 위조값·미회수/다른 성공 조건 미충족은 거절한다. 자연 회수는 원격 취소나 비용0의 증거가 아니다.

known VertexResponseError의 고정 code를 첫 실패로 보존한다. 유효 failed receipt는 값 그대로 남기며 strict decode를 하지 않는다. 뒤따르는 행 파일/ledger 기록에 일반 I/O 오류가 나면 원 D2 오류 객체·args/code/receipt를 변경하지 않고 clean chain으로 재전파한다. 부차 문제는 고정 note model_comparison_persistence_failed만 추가하며 원 I/O/path를 노출하지 않는다. 이때 예약/active는 자동 회수하지 않는다. 선행 D2 오류가 없는 기록 실패는 기존 state_error로 남는다. receipt가 없거나 유효하지 않아 실제 생성 횟수를 알 수 없으면 unknown/null이다. KI/SystemExit/GeneratorExit/MemoryError 및 예상하지 못한 adapter 예외는 원 객체를 전파하며 예약은 남는다. 로컬 중단을 원격 취소나 과금0 증거로 승격하지 않는다.

| DTO | 정확 키 수 | 핵심 |
|---|---:|---|
| matrix | 11 | profile/binding/limits/rows/selection와 나머지10키의 matrix_sha256 |
| selection | 4 | mode, model_id, overrides, row_indexes |
| row | 15 | binding/settings/mode/status/reason/receipt/strict_decode/assessment/budget/timing |
| batch | 8 | six rows, summary, business_assessment |
| summary | 11 | 상태별 수, 누적 예약, known 시도 부분합/unknown 행 수 |

row status는 success/failed/not_run/unknown이다. 최초 호출 전 거절은 attempts0이며, receipt의 누락된 사용량·비용은 null/unknown으로 보존한다. provider reported_model_version과 요청 model_id를 구별한다. unknown 시도가 하나라도 있으면 batch 전체 시도 합은 null이고 알려진 부분합과 unknown 행 수를 별도로 남긴다. usage/cost를 추정 합산하지 않는다.

실행 폴더에는 row-0~row-5의 D2 폴더, row-N.record.json, batch.json이 남는다. run 단일 API는 해당 행 기록만 만든다. 행 기록의 SHA와 exchange_ref를 ledger에 연결한다. 행 파일을 저장한 뒤 ledger 종료 기록을 원자 갱신하므로 중간 실패 때 행 파일이 있어도 예약 완료/해제를 뜻하지 않는다. budget active 상태와 원 receipt를 함께 대조한다. 완료 파일 덮어쓰기·자동 복구·자동 재전송은 없다.

matrix128KiB, budget64KiB, row/batch 각1MiB를 상한으로 둔다. receipt/artifact/ref를 포함한 전체 반환값은 private 결과이며 보호 UI에 그대로 제공하지 않는다. 개발4 호스트는 허용 필드만 투영하고 인증 경로·원 응답·thought·artifact 경로를 제외한다.

이 API는 actual 전송 경로를 위한 호스트 승인만 받는다. 모의와 replay를 actual 승인으로 변환하는 production 분기는 없다. 단위 검사에서 actual 경로 DTO를 testpatch로 시뮬레이션한 결과의 증거 모드는 mock이며 실제 생성/요금/인증 증거가 아니다. 기존 provided-result replay나 실제 모델 결과와 별도 분모를 사용한다.

## 가상 작업자 고정 후보 비교

[가상 작업자 설계](../superpowers/specs/2026-10-25-virtual-operator-model-comparison-design.md)의 첫 정보 부족 case만 runner에서 추가 수용한다. scenario는 operator-synthetic-o01/version1, evaluator는 virtual-operator-wire-v1/version1, pack은 operator-input-v1, producer는 dgm-virtual-operator-v1이다. [고정 합성 자료](virtual_operator_comparison_inputs.json)는 context/delegation/ids/producer_name/prompt_literal_utf8/response_schema_literal_utf8 exact6의 C1이다.

| 대상 | 원 bytes | SHA-256 |
|---|---:|---|
| context C1 | 318 | 7db07a21ecae1ef0221452516a71f9bb09ba235ec55b70e556fc3c5ac4d3d5b1 |
| logical request core C1 | 887 | 18438b686208d6c55f3c539e6d1e3e96f91601bd6c69577234bc6cf015a4d8c3 |
| prompt C1 | 2131 | 55e618165ab033b48c03589b02a10d5651c952f9b2c5334cc56afc0b4687d85b |
| schema 원문 UTF-8 | 3052 | aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb |
| input pack C1 | 6607 | 0dfe3bae594b0db6646d3c8882059b364c1b34cc7bdfbccdc3c2024e970c6e5a |

schema는 공개 first-decision 계약의 literal3052/끝 LF를 그대로 사용한다. C1으로 재작성한 schema1435는 다른 pair이므로 거부한다. case ID/evaluator/전체 prompt/schema가 고정 bytes와 다르면 transport 전에 거부한다. 내부 helper는 공개 genuine build_operator_prompt로 context/delegation/ID/producer를 재구축해 full C1 prompt를 대조한다. case/scenario/정답/seed/truth를 context 안에 추가하지 않는다.

순수 입력 준비 예시는 다음과 같다. C1 설정은 앞 절과 같으며 실제 모델을 호출하지 않는다.

```python
from pathlib import Path
import json
from labflow.virtual_fleet.model_operator_boundary import (
    build_operator_prompt, decode_operator_response,
)

pack = json.loads(Path("docs/fcc/virtual_operator_comparison_inputs.json").read_bytes())
prompt_bytes = pack["prompt_literal_utf8"].encode("utf-8")
schema_bytes = pack["response_schema_literal_utf8"].encode("utf-8")
prompt = build_operator_prompt(
    pack["context"], **pack["ids"],
    producer_name=pack["producer_name"], delegation=pack["delegation"],
)
```

Vertex는 앞 절의 기존 API3를 그대로 사용하며 matrix 생성 때 scenario_id="operator-synthetic-o01", evaluator_id="virtual-operator-wire-v1"을 전달한다. 별도 공용 등록이 이뤄질 경우 input_kind는 registered_synthetic을 유지한다. 현재 backend/frontend UI의 closed7·공용4 파일·root tuple은 변경하지 않았고 8번째 UI admission을 완료한 것이 아니다. model catalog를 scenario registry로 바꾸지 않는다.

strict_decode는 원본 bytes와 재구축 prompt를 genuine decode_operator_response에 직접 넘긴다. wire exact5는 schema_version/kind/request_sha256/producer/proposal이다. proposal은 dut/start 또는 sensor/acquire|read의 빈 parameters, advance ticks=1, stop의 completed|blocked|unsupported|failed 및 bounded nonblank reason만 허용한다. 새로운 refused/needs_information wire kind나 claim은 만들지 않는다.

성공 row는 success/operator_response_verified/strict_decode.checked, 거부 row는 failed/operator_response_invalid/strict_decode.rejected다. 두 경우 assessment는 not_assessed/verdict=null/semantic_evaluator_not_connected이고 batch.business_assessment도 not_assessed다. 반환 row15/batch8과 public 함수3개는 유지하며 score나 실행 권한을 새 키·기본값으로 만들지 않는다. completed라는 stop claim도 실제 task 완료·정답·행동 적용·효과 평가를 뜻하지 않는다.

genuine 경계의 response cap65536, depth32/nodes200000/native int64, duplicate/UTF-8/비유한 수/타입·키·binding·producer 검증과 control3/최초 오류 보존을 따른다. 65536은 상한 안이라는 뜻이며 임의 bytes의 유효성을 보장하지 않는다. 65537은 limit_exceeded다. fence 제거·strip·repair·producer/hash 보충·부분 결합·재시도 없이 원문 artifact를 보존한다. 상세 bounds와 최초 오류 본문 규범도 기계 JSON 밖에서 계속 적용된다.

### Codex direct composition

Codex는 기존 labflow.codex_cli_response.produce_codex_cli_response와 위 genuine decoder를 직접 조합한다. 새로운 provider·runner API·Codex UI·first-decision/one-action host 변경은 없다. 아래 호출은 향후 별도 실제 실행 위임을 받은 host의 순서를 설명하며 이번 구현 검증에서는 실제 CLI·모델을 호출하지 않았다.

```python
from labflow.codex_cli_response import produce_codex_cli_response
import hashlib

# executable/evidence_dir는 host가 명시한 절대 Path이며,
# requested_model과 호출 예산도 별도로 위임돼 있어야 한다.
raw, receipt = produce_codex_cli_response(
    prompt_bytes, schema_bytes,
    executable=executable, requested_model=requested_model,
    evidence_dir=evidence_dir, timeout_seconds=60.0,
)
# genuine 반환 tuple만 사용하며, receipt는 변경하지 않는다.
cleanup = receipt["cleanup"]
bindings = receipt["bindings"]
if not (
    receipt["status"] == "complete" and receipt["failure"] is None
    and receipt["verification"]["wire_complete"] is True
    and all(cleanup[k] is True for k in (
        "version_child_reaped", "model_child_reaped", "readers_joined",
        "pipes_closed", "artifacts_closed",
    ))
    and bindings["prompt_sha256"] == hashlib.sha256(prompt_bytes).hexdigest()
    and bindings["schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
):
    raise ValueError("incomplete or mismatched Codex record")
final = receipt["artifacts"]["final_text"]
if not (
    final["path"] == "final-text.bin" and final["present"] is True
    and final["complete"] is True and final["overflow"] is False
    and final["extent"] == "whole_file" and type(final["bytes"]) is int
    and final["bytes"] == len(raw)
    and final["sha256"] == hashlib.sha256(raw).hexdigest()
):
    raise ValueError("incomplete or mismatched final artifact")
with (evidence_dir / "final-text.bin").open("rb") as handle:
    original = handle.read(65537)
if original != raw:
    raise ValueError("final artifact readback mismatch")
candidate = decode_operator_response(raw, prompt)
```

direct host는 genuine producer에서 받은 tuple만 사용한다. complete/failure=null/wire_complete=true 및 version/model child 회수·reader join·pipe/artifact 종료를 확인하고, receipt의 prompt_sha256/schema_sha256를 같은 원 bytes와 대조한다. final_text descriptor는 fixed final-text.bin의 whole_file/complete/overflow=false·native bytes·SHA와 반환 raw에 맞아야 한다. 원 파일을 bounded read로 재대조한 뒤 raw를 decoder에 그대로 전달한다. 외부에서 제공한 receipt나 fixture를 실제 모델 생성으로 인정하는 경로가 아니다.

Codex receipt는 codex_cli_response_receipt, Vertex receipt는 vertex_response_receipt의 원 형상을 유지한다. logical request hash·full prompt hash·schema 원문 hash·transport invocation/provider payload hash는 각각 다르다. producer 이름·요청 model·reported model 문자열·일치 hash만으로 원격 identity/저장 진위/업무 의미/행동 권한을 증명하지 않는다. complete transport여도 candidate strict는 거부될 수 있으며, incomplete/timeout/cancel/cleanup 실패·unknown은 원형을 보존한다.

Codex public API에는 output-token cap 인자가 없으므로 Vertex512 제한을 Codex에도 적용했다고 쓰지 않는다. 모든 실제 새 호출은 현재0이다. Vertex 동일6/3072 소진·free credits only를 유지하고, case 등록이나 delegation의 가상8/8/4/30/retries2·outer60/model_calls8을 새 호출 허가로 해석하지 않는다. 기존 승인서를 새 pair에 전용하거나 실제 ledger를 seed/reset/refund하지 않는다.

이 단위의 가상 비교 검사는 기존64+operator 신규14=담당78이다. genuine builder/decoder와 bounded fake producer를 사용했고 Codex native pipe fixture는 실제 executable을 실행하지 않는다. fake 생성·credential metadata·approval·budget 파일은 각 테스트의 격리 자료다. 실제 Codex/Vertex/API/auth/ADC/live ledger/Store/고객/현장 접근은0이며 actual-shaped 행도 검증 증거의 출처는 mock이다. 독립12논리 봉인·후속 공용 admission 및 실제 모델·의미·행동·effect/task/closed_loop 검증은 이 담당78에 합산하지 않는다.

## 검증과 남은 범위

기존64 검사는 가상 프로필/전송만 쓴다. 고정행/선택/override 불변, scope와 만료, 누적 재시작·중복·동시 in-flight, 원 설정 한도 거절, 예약 후 취소/시간, strict wire, receipt/artifact 변조, known 실패·unknown·제어 예외를 포함한다. 접수 신규10은 genuine decoder·등록3·교차입력/producer/schema·dependency·transport decoder0·누적 소진·최초 오류 보존을 가상 전송으로 검사했다. 원41과 접수 신규10의 기존51에 자연 완료 호환 신규3과 intent 신규10을 모두 보존한 총괄 가상 검사 합계64다. 담당54·61과 독립 분모는 합산하지 않는다. OS 잠금은 이 Windows 호스트에서 검사했다. 다른 OS의 파일시스템·프로세스 강제 종료·실제 D1/D2 결합·원격 API·실제 모델은 별도 검증 대상이다.

고정 오류는 ModelComparisonError(ValueError)이며 code/str/args가 동일하고 cause/context가 없는 model_comparison_invalid_input, model_comparison_limit_exceeded, model_comparison_state_error, model_comparison_dependency_unavailable이다. operational 거절은 고정 reason_code와 not_run/unknown 기록으로 구별한다. 원 인증 오류 내용이나 파일 경로를 오류 메시지로 만들지 않는다.

문서 무결성 검사는 기능·계측 정확도·실장비/현장·규범 적합성·전체 업무 무인화의 증거가 아니다. 실제 생성6·등록 S01~S03의 실제 모델 비교/의미평가·물리 시험소 검증은 이 담당 단위에서 미실행이다.
