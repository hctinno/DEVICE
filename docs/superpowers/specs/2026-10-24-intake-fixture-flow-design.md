# FLOW-003 — 접수와 단일 가상 실행의 연결 계약

2026-10-24, Asia/Seoul. [연결 검토](../../../handoff/development/FLOW-003-CONTRACT.md)의 개발1~4/P01 결과를 반영한 총괄의 첫 구현 계약이다. 사용자가 검토에서 멈추지 말고 구현·검증·통합·후속 배정까지 계속하도록 위임했다. 기능 기준은 `35dc0f59e2d9368e79e76fa552c35271e695509f`이며 이후 `64600dc`는 배정 문서만 추가했다.

## 선택과 범위

기존 분석 job에 가상 실행을 넣는 안, 별도 가상 요청/attempt와 연결하는 안, 실제 case/plan/run에 바로 넣는 안을 대조했다. 별도 요청/attempt를 선택한다. 기존 분석의 만료 후 재인수와 provider 임시 폴더를 live runtime의 재개로 오인하지 않고, 실제 case에 가상 raw를 실제 자료처럼 등록하지 않기 위해서다.

이번 결과는 접수의 정확한 revision/준비 상태에서 명시적으로 고른 **단일 합성 센서 recipe**를 실행하고 같은 접수 화면에서 결과를 읽는 흐름이다. FCC 적용성/전체 전도출력 방법 승인이나 실제 AI 호출·실장비를 포함하지 않는다. 기존 `run_fixture_suite()`의 세 조건을 한 의뢰의 측정 세 번으로 전용하지 않는다. case/plan은 아직 자동 생성하지 않으며 연결 DTO의 `case_id`/`plan_id`는 null이다.

PDF 페이지 입력/인용 연결은 개발1의 독립 작업이다. TXT V1을 유지하고 PDF V2를 명시한다. 실제 일반 문서의 의미/역할 이해를 합성 fixture provider의 성능으로 표시하지 않는다.

## PDF 입력과 인용 — 개발1

소유: 신규 `labflow/intake_documents.py`, 전용 tests/usage와 기존 `intake_analysis.py`, `intake_jobs.py`, `intake_worker.py`의 연결 부분. 기존 queue/원본/revision/답변/알림 동작은 보존한다. `schema.sql`, `store.py`, 가상 queue는 수정하지 않는다.

`prepare_analysis_documents(store, files, *, source_id, intake_id, revision, revision_fingerprint)`는 보존 blob을 검증하고 `{context_id, extraction_profile_id, documents}`를 반환한다. text 문서는 기존 `text`/줄 좌표를 유지한다. PDF는 `text=null`과 typed 추출 상태, `extraction_id`, pages의 `page_number/status/text/text_sha256/line_spans`를 전달한다. 추출물/식별자는 원본 hash·parser/version·정규화한 extractor 코드·limits·페이지 내용을 결합해 고정한다. 공개 문맥에 blob 절대 경로를 넣지 않는다.

텍스트 한도는 문서당 UTF-8 256 KiB/묶음 2 MiB이며 PDF에도 합산 적용한다. extractor의 기본 16 MiB 입력/200페이지/1,000,000문자/페이지 content 8 MiB 한도를 함께 유지한다. UTF-8 출력 한도를 넘으면 typed 실패/partial을 남기며 조용히 정상 문서로 자르지 않는다. 문맥 직렬화는 4 MiB 이내다. parser unavailable·encrypted·malformed·image/no_text·empty·partial·limit 상태와 원본/실패를 보존한다. 암호/Office/OCR/매크로/사용자 원본 실행을 추가하지 않는다.

분석 schema1은 기존 exact fields/6개 citation 필드 그대로다. schema2는 top-level `context_id`를 추가하고 evidence를 다음 두 변형으로 제한한다. `validate_analysis(..., *, context_id=None)`는 V1 세 인수 호출을 유지하며 V2는 서버가 만든 context_id와 현재 보존 추출물을 대조한다.

- text: `{kind:'text_line',path,sha256,line_start,line_end,quote,role}`.
- PDF: `{kind:'pdf_page',path,sha256,extraction_id,page_number,text_sha256,line_start,line_end,quote,role}`.

PDF의 줄 번호는 해당 page-local이며 다른 페이지의 같은 quote로 대체하지 않는다. `claim_job()` 반환에는 `analysis_context_id`를 추가할 수 있고 worker는 이를 provider에 전달한다. PDF page 문맥이면 schema2를 광고/생성하며 TXT V1 결과는 유지한다. claim/complete에서 느린 parsing은 `BEGIN IMMEDIATE` 밖에서 준비하고 안에서는 current revision/lease/context fence와 제출·질문·알림의 원자성을 확인한다. completed 재전송에서도 V2 context/추출물·원본을 검증한다.

partial의 유효 페이지 인용은 보존하되 미독해/추출 경고 질문이 남아 `prepare_plan`으로 승격되지 않게 한다. schema1 분석만 받은 PDF도 읽힌 것으로 가장하지 않는다. parser/limits만 바뀌었을 때 같은 revision의 새 분석 job을 자동 생성하는 generation migration은 이번에 넣지 않는다. V2의 오래된 context는 거절하고 원래 완료 기록은 보존한다. generation 재분석은 다음 작은 배정으로 이어간다.

## 준비 snapshot과 가상 작업 — 총괄

신규 `labflow/intake_fixture_jobs.py`, `schema.sql`의 별도 table과 전용 tests는 총괄 소유다. 기존 `intake_jobs`를 재사용하거나 변경하지 않는다. 아래 함수를 고정한다.

```python
fixture_readiness(store, intake_id) -> dict
request_fixture_job(store, request_id, intake_id, *, expected_revision,
                    expected_readiness_fingerprint, recipe_id, settings) -> dict
claim_fixture_job(store, worker_id, *, lease_seconds=120, now=None) -> dict | None
fixture_lease_current(store, request_id, token, *, now=None) -> bool
complete_fixture_job(store, request_id, token, report, artifacts, *, now=None) -> dict
fail_fixture_job(store, request_id, token, code, *, dispatched=False, now=None) -> dict
```

readiness에는 intake_id/revision/revision_fingerprint/readiness_fingerprint/source_synthetic/기존 delegation_event_id와 ready/reason_codes, 확인된 product model을 반환한다. fingerprint는 현재 `analysis_json`, 정렬한 답변과 basis, delegated/deferred/status, 원본 revision fingerprint와 실제 기록된 proceed event를 포함한다. 같은 revision의 답변·보류 변경도 fingerprint를 바꾼다. ready에는 analyzed·질문/미독해 없음·prepare_plan·delegated·미보류와 실제 trusted proceed 기록이 필요하다. 전부를 스마트폰/FCC로 분류하지 않는다.

request는 명시적인 recipe/settings와 예상 revision/fingerprint를 원자 비교한다. 같은 request ID/같은 body는 멱등이고 다른 body는 거절한다. 현재 revision/readiness/위임이 달라진 queued는 실행하지 않고 `superseded`로 남긴다. 상태는 `queued|running|completed|failed|uncertain|superseded`다. running의 run_id/runtime_instance_id·token·lease를 dispatch 전에 예약하며 만료 running을 다시 claim하지 않고 uncertain으로 동결한다. 파견 이후의 실패·lease 소실·불완전 증거는 자동 재실행하지 않는다. 명시적 새 요청은 새 합성 시도이며 기존 runtime 재개가 아니다.

complete는 같은 token/lease/instance/report hash·검증한 공개 artifact 목록으로 CAS한다. 준비 상태가 달라졌으면 현재 성공으로 게시하지 않는다. 과거 결과/파일을 보존한다. read GET은 Store 초기화·migration·evaluate·case_status·harness 호출을 하지 않는다.

table 이름은 `intake_fixture_jobs`다. 공통 열은 `request_id,intake_id,revision,request_fingerprint,readiness_fingerprint,revision_fingerprint,delegation_event_id,recipe_id,settings_json,model,source_synthetic,state,worker_id,token,lease_until,run_id,runtime_instance_id,result_json,error_code,created_at,updated_at`다. claim 반환은 이 중 JSON settings와 source_synthetic bool을 복원한 host-only dict이며 token/lease를 포함한다. model은 현재 분석 facts의 model 값이다. 새 request_id로 명시적 새 시도는 허용하며 같은 ID의 자동 중복은 허용하지 않는다.

complete 입력 artifacts는 `{kind:'result'|'operator_journal',artifact_id:'blob:'+sha256,sha256,bytes}` 두 항목이다. bridge가 `Store.import_artifact(..., synthetic=True)`로 등록한 보존 blob이며 root도 크기/hash/합성 표지·결과 identity/내용을 재검증한다. result_json은 정확히 `{report,artifacts}`이고 공개 report에는 연결 필드를 추가하지 않는다. run_id/runtime_instance_id는 claim에서 UUID 기반 opaque 문자열로 예약한다. 모든 terminal 상태는 자동 재claim하지 않는다.

## 단일 가상 방법 — 개발3

신규 `labflow/virtual_fleet/method_adapter.py`, 전용 tests/usage를 소유한다. 기존 core/역할/하네스/평가기/세 조건 CLI는 변경하지 않는다.

```python
describe_fixture_method(recipe_id, *, model, settings) -> dict
run_fixture_method(request, output_dir, *, run_id, runtime_instance_id,
                   can_continue=None) -> dict
```

request는 서버가 보존한 request_id/intake_id/revision/readiness_fingerprint/recipe_id/settings/model/source_synthetic의 분리된 dict다. recipe ID는 `conducted_sensor_fixture_v1`, model은 `SM-A176U`, settings는 정확히 `{power_dbm: finite number}`다. 첫 합성 recipe 입력 범위는 -30~20 dBm이며 제조사 실제 capability를 뜻하지 않는다. 나머지는 unsupported로 거절하고 대체 recipe를 추측하지 않는다.

기존 정상 `prepare_sensor_trial(..., condition='normal', seed=0, power_dbm=...)` 한 건을 새 policy/harness/journal로 실행하고 별도 evaluator를 적용한다. 주파수 2.45 GHz/20 MHz/OFDM/duty .25/crest3와 실제 반환한 전체 topology·노드/profile 결합을 기록한다. 측정량은 센서 입력 기준면의 ON 평균 dBm이며 DUT 출력/전력계 시간평균과 구별한다. 합성 결합 20 dB를 자료의 실물 결합계수로 표시하지 않는다.

새 출력 폴더에 `public-result.json`, `operator/events.jsonl`, `private/author.json`과 private 해시 목록을 보존한다. 결과는 `{report, artifacts}`이며 report는 기존 v1 exact contract를 유지한다. artifacts는 host-only `{kind:'result'|'operator_journal',path,sha256,bytes}` 목록이다. private 작성자 파일은 공개 artifact 목록에 넣지 않는다. provenance는 preinitialized/catalog/topology/engine fingerprint와 `resumable=false`다.

can_continue는 trusted host callback으로 준비 상태/lease를 확인한다. 초기화 전과 각 policy 판단/파견 경계에서 확인하고 false·예외면 추가 파견을 중단한다. cooperative 경계이며 강제 취소를 가장하지 않는다. 실패/미결 journal을 보존한다.

## 실행 bridge — 개발2

신규 `labflow/intake_fixture_bridge.py`, 전용 tests/usage를 소유한다. 총괄 queue와 개발3 adapter는 고정 API의 대역으로 먼저 검사한다.

```python
run_fixture_worker(store, *, worker_id, output_root, max_jobs=1,
                   lease_seconds=120, executor=None) -> dict
```

executor 기본값은 개발3 `run_fixture_method`이며 한 claim은 한 새 runtime이다. 위임/recipe/예상 snapshot은 queue가 고정한다. 실행 직전·실행 중 callback·게시 직전에 fence를 확인한다. output은 새 request/run 전용 폴더이며 기존/실패 폴더는 덮거나 이어 쓰지 않는다. private 경로·token·원시 예외를 공개 결과에 넣지 않는다.

adapter 반환 후 report와 공개 artifact의 실제 bytes/hash/run/instance, `read_operator_journal`의 무결성/완료/미결을 검사하고 CAS 게시한다. 임의 경로/다른 run/private artifact를 받지 않는다. storage/publication 실패는 증거를 보존하고 파견 여부에 따라 failed 또는 uncertain이다. 사용자가 완성된 측정이라고 해석하지 않도록 작업 기술 상태·policy 주장·별도 평가·fresh measurement를 분리한다. persistent 장애의 평가 pass도 측정 성공으로 승격하지 않는다.

## 접수 화면 읽기 — 개발4

소유: 기존 `ui_read_model.py`/`ui_server.py`, `frontend/app.js`/관련 snapshot 검증과 새 `frontend/intake_flow_model.mjs`, 전용 tests/usage. 기존 별도 가상 장비 action 서버는 변경하지 않는다.

`GET /api/intakes/{intake_id}/fixture-runs`는 같은 origin의 순수 읽기다. 새 table이 없는 이전 DB도 쓰기/migration 없이 `storage_available=false`와 빈 records를 반환한다. 정확한 현재 intake/과거 revision을 결합하며 runtime/평가를 실행하지 않는다. JSON 외피는 `{schema_version:1,intake_id,current_revision,storage_available,records:[],more_available:false}`다. 최신 20개를 보여주고 초과 시 more_available로 표시한다.

read model 이름은 `IntakeReadModel.fixture_runs(intake_id)`다. 같은 read transaction의 `_SnapshotStore`를 `fixture_readiness()`에 전달해 현재 fingerprint를 계산할 수 있다. 이 helper는 DB 조회만 하며 Store 생성이나 blob 쓰기를 하지 않는다. queue가 아직 도착하지 않았으면 테스트 대역으로 계약을 고정하며 legacy DB의 준비 helper/table 부재는 storage_available=false로 구별한다.

각 record의 공개 필드는 `{request_id,intake_id,revision,readiness_fingerprint,recipe_id,run_id,runtime_instance_id,state,source_current,source_synthetic,synthetic:true,hardware_verified:false,ai_model_called:false,resumable:false,case_id:null,plan_id:null,error_code,report}`다. report는 공개 v1 또는 null이다. 절대 경로/token/author/seed/private manifest를 내보내지 않는다. source_current는 현재 revision뿐 아니라 readiness fingerprint도 비교한다. result_json의 report/identity/합성 표지/256 KiB와 중첩 비공개 키를 엄격히 검증한다.

기존 접수 상세에 가상 기록 카드/선택/빈 상태·이전 자료 버전 표시를 더한다. 활성 start/stop/resume 버튼을 만들지 않는다. 분석 완료·장비 available·평가 pass를 실제 측정/FCC 합격으로 표시하지 않는다. 선택 intake/revision/request의 identity와 요청 순번을 결합해 늦은 응답·렌더 실패가 다른 건의 기록/시각을 덮지 않게 한다. 페이지 V2 인용은 page/줄/extraction 표시를 보존하고 V1을 유지한다. 파일 원본/운영 event 다운로드 resolver는 이번 범위에 넣지 않고 opaque refs만 표시한다.

## 총괄 통합과 자료

총괄은 readiness/queue/schema·전용 CLI `labflow/intake_fixture_check.py`, 가상 접수/위임/분석→한 recipe→동일 접수 UI의 실제 통합 검사를 소유한다. 준비 부족·다른 제품·보류·R1/R2·답변 변경·중복·lease 소실/파일 실패·잘못된 공개 결과도 검사한다. 담당 결과는 각 독립 clone/전용 브랜치에서 commit/push하고 총괄이 인수·리뷰·회귀를 수행한다.

P01의 첫 근거 묶음은 최대 전도 평균의 ON 구간·duty 중복 방지·기준면·포트 선형 합산과 판본 공백을 확인했다. 이는 자료 인수/방법 설계 근거이며 현행 규범적 방법 승인이나 실장비 검증이 아니다. 특히 KDB의 C63.10-2013 절과 보유 법령 snapshot의 2020 채택은 구분한다. 추가 사용자 자료·암호·계정·raw 없이 합성 개발을 계속한다.
