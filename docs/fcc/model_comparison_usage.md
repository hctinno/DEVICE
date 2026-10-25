# Vertex 연결 비교 실행

2026-10-25, Asia/Seoul. [공통 설계](../superpowers/specs/2026-10-25-vertex-ai-connection-design.md)와 [공식 모델 카탈로그](vertex_ai_connection_catalog.json)를 따르는 작은 연결 실행 경계다. [구현](../../labflow/model_comparison.py)은 프로필/설정 담당 모듈과 REST 응답 담당 모듈을 직접 연결한다. 현재 소유 단위의 검증은 [가상 단위 검사](../../tests/test_model_comparison.py) 41개이며 실제 ADC 읽기·인증 갱신·네트워크·Vertex 생성은 모두 0이다. 실제 의존성 결합·처음 6회 생성과 독립 제품 검수는 총괄이 수행한다.

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

현재 등록 범위는 DGM-AI-CONNECTION-001/version1, connection-json-v1뿐이다.

| 원 bytes | 길이 | SHA-256 |
|---|---:|---|
| prompt | 639 | bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230 |
| literal schema | 321 | a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9 |

원 pair를 다른 요약이나 재직렬화 bytes로 바꿀 수 없다. strict decoder는 단일 UTF-8 JSON object exact4의 schema_version을 native int 1, status를 문자열 ok, synthetic을 true, equipment_authorized를 false로 검사한다. 중복키·비유한 수·잘못된 UTF-8·Markdown·추가 텍스트/키·bool/float 버전은 거절하고 수선하지 않는다.

연결 성공은 업무 품질 평가가 아니다. assessment는 항상 not_assessed/verdict=null/connection_only이고 batch.business_assessment도 not_assessed다. 기존 접수→의뢰 이해→계획→가상시험→설명, Codex 실제 응답과 독립 기대, Fleet/Store/장비 DB를 변경하지 않는다. S01~S03의 추가 비교는 별도 등록 입력·평가자와 추가 유계 승인이 필요하다. 논리 18셀은 18회 호출 권한이 아니다.

## 호스트 승인과 누적 예산

adc_path, evidence_dir, budget_path, approval_path는 보호된 호스트가 정한 absolute native Path여야 한다. UI body의 임의 경로를 전달하지 않는다. reparse/symlink, Windows 짧은 이름·ADS·device/UNC 경로, regular file의 hardlink를 거절한다. evidence_dir는 새 폴더 또는 빈 폴더이며 부모가 이미 있어야 한다. 원 자료를 덮어쓰지 않는다. cancel_event는 정확한 threading.Event 또는 None이고 미리 set됐으면 metadata 검사·worker·인증·생성·예약 모두 0이다.

승인은 root가 seed한 private exact17이다. UI bool이나 기존 prepared.json으로 열 수 없다. 키는 schema_version, kind, approval_id, scope_id, budget_id, project_id, quota_project_id, auth_profile_id, scenario_id, evaluator_id, prompt_sha256, response_schema_sha256, execution_mode, trial, limits, issued_at, expires_at이다. kind는 vertex_comparison_approval이다.

scope는 위 고정 등록 pair·scenario/evaluator, project/quota project-a6310591-f8cc-487c-9e3, auth profile, root_console의 confirmed 무료 체험 관측에 결합한다. 양의 KRW 크레딧 문자열·잔여1~90일·관측시각·최대24시간 유효기간을 검증한다. 새 profile revision·model/level/override·selected/matrix·batch도 같은 scope에서 쓸 수 있다. 각 실행의 원 profile/settings/matrix/pair SHA는 별도로 다시 검증한다. 승인은 실시간 잔액 조회나 과금0의 보증이 아니다.

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

## 검증과 남은 범위

신규41 검사는 가상 프로필/전송만 쓴다. 고정행/선택/override 불변, scope와 만료, 누적 재시작·중복·동시 in-flight, 원 설정 한도 거절, 예약 후 취소/시간, strict wire, receipt/artifact 변조, known 실패·unknown·제어 예외를 포함한다. OS 잠금은 이 Windows 호스트에서 검사했다. 다른 OS의 파일시스템·프로세스 강제 종료·실제 D1/D2 결합·원격 API·실제 모델은 별도 검증 대상이다.

고정 오류는 ModelComparisonError(ValueError)이며 code/str/args가 동일하고 cause/context가 없는 model_comparison_invalid_input, model_comparison_limit_exceeded, model_comparison_state_error, model_comparison_dependency_unavailable이다. operational 거절은 고정 reason_code와 not_run/unknown 기록으로 구별한다. 원 인증 오류 내용이나 파일 경로를 오류 메시지로 만들지 않는다.

문서 무결성 검사는 기능·계측 정확도·실장비/현장·규범 적합성·전체 업무 무인화의 증거가 아니다. 실제 생성6/기존 S01~S03 업무 비교·물리 시험소 검증은 이 담당 단위에서 미실행이다.
