# Vertex AI 연결·추론 선택·합성 비교

2026-10-25, Asia/Seoul. 사용자 추가 지시 `DEV-VERTEX-GEMINI-20261025-001`이다. 기존 Codex CLI producer, 합성 의뢰와 가상시험, 담당별 후보와 실패 기록을 보존한다. 이 문서는 구현 계약이며 실호출 또는 시험소 전체 완료 증거가 아니다.

## 1. 공급자와 확인 범위

서비스는 `aiplatform.googleapis.com`, 대상 프로젝트와 quota project는 모두 `project-a6310591-f8cc-487c-9e3`이다. 콘솔의 Agent Platform 표기를 별도 공급자로 취급하지 않는다. Gemini Developer API·AI Studio·express mode·API key·파트너 모델로 우회하지 않는다.

| 선택 모델 | API ID | 추론 선택 | 기본 | 공식 제공 위치 |
|---|---|---|---|---|
| Gemini 4 Argon | `gemini-4-argon` | LOW, MEDIUM, HIGH | MEDIUM | global, us, eu |
| Gemini 3.8 Flash | `gemini-3.8-flash` | LOW, MEDIUM, HIGH | MEDIUM | global, us, eu |

MINIMAL·OFF·thinking_budget은 이 연결에서 지원하지 않는다. 유효하지 않은 값, 미지 키, 다른 모델·위치와 bool을 숫자로 사용한 값은 명시적으로 거절한다. SDK/서버 거절을 다른 설정으로 재전송하지 않는다.

공식 모델·thinking·지역·REST·무료 체험 원문은 [카탈로그](../../fcc/vertex_ai_connection_catalog.json)에 확인일과 링크를 기록한다. 모델 문서의 제공과 대상 계정 접근, 연결 성공과 업무 품질을 별도 판정한다. 계정의 크레딧 잔액·만료는 공개 문서에서 확인할 수 없다.

## 2. 기존 작업과 소유권

| 담당 | 새 제품 소유 | 첫 구현 |
|---|---|---|
| 개발1 | ai_connection_profiles.py, 전용 test, usage | 비밀 없는 프로필 저장·revision·모델별 설정·실행 snapshot |
| 개발2 | Codex new3의 첫 검증 경계/WIP 보존 후 vertex_response.py, 전용 test, usage | 최신 요청의 분리 ADC·단일 REST 호출을 우선, 보존한 CLI 구현은 후속 재개 |
| 개발3 | 기존 pure operator 후보 보존 후 model_comparison.py, 전용 test, usage | 고정 합성 입력·6조합·예산·취소·기록·기존 평가 접점 |
| 개발4 | 기존 DOCX UI 후보 보존 후 별도 정확 배정한 server/frontend/test | 보호된 설정 저장·테스트 실행·취소·6조합 이력 |
| 총괄 | 공통 계약/카탈로그/선택 의존성·인증 점검·독립 리뷰/통합 | 인증·무료 체험 조건 확인, 원격 대조와 고정 실호출 묶음 |
| P01 | 플랫폼 자료 별도 수집 요청 | 기존 수집4 한 역할의 공식 원문 공백 검증 |

새 소유 범위 밖의 Store/schema/worker/FleetHarness/journal·registry·공유 폴더를 수정하지 않는다. 개발1~4는 각각 새 독립 clone/전용 branch를 사용하고 완료된 기존 후보는 보존한다. 총괄이 정확 base와 함수/DTO를 전달한 뒤 후속 소유자가 구현한다. 사용자에게 다시 설계 승인이나 동일 권한을 요청하지 않는다.

## 3. 프로필과 실행 설정

프로필의 정확 키는 `schema_version`, `profile_id`, `provider`, `project_id`, `location`, `quota_project_id`, `auth_profile_id`, `selected_model`, `models`, `revision`이다. schema_version=1, provider=vertex_ai. 최초 profile_id/auth_profile_id는 vertex-trial, location=global, selected_model=gemini-3.8-flash, revision=0이다. models는 위 두 모델을 모두 가지며 각 값의 정확 키는 `thinking_level`, `max_output_tokens`, `timeout_seconds`다. 기본 MEDIUM/512/60이다. 출력 한도는 정수64..8192, timeout은 유한 숫자1..120초다. 저장 선택과 실행 override는 구별한다.

개발1의 공개 API는 다음 세 함수다. 반환값은 caller가 변경해도 저장 상태를 바꾸지 않는 분리 dict다.

```python
load_profile(path) -> dict
save_profile(path, profile, *, expected_revision) -> dict
resolve_run_settings(profile, *, model_id=None, overrides=None) -> dict
```

실행 settings의 정확16 키는 `schema_version`, `kind`, `profile_id`, `profile_revision`, `provider`, `service`, `project_id`, `location`, `quota_project_id`, `auth_profile_id`, `model_id`, `thinking_level`, `max_output_tokens`, `timeout_seconds`, `profile_sha256`, `settings_sha256`다. kind=ai_run_settings, service=aiplatform.googleapis.com이다. profile의 revision은 profile_revision으로, 선택된 모델의 설정은 세 run 값으로 복사한다. override는 그 세 값만 허용하며 원 profile과 다른 모델의 저장값을 변경하지 않는다. credential path·키·토큰·계정 email·billing account는 포함하지 않는다. profile_sha256은 전체 profile의 canonical JSON, settings_sha256은 나머지15 키의 canonical JSON을 결합한다. canonical은 UTF-8/ensure_ascii=False/sort_keys=True/separators comma·colon/allow_nan=False다. 반환은 별도 plain dict이며, 실행 시 한 번 검증·복사해 고정한 값과 hash를 요청/기록에 사용한다. dict subclass를 불변 보안 경계로 만들지 않는다.

없는 파일의 load는 revision0 기본값을 반환하고 profile을 쓰지 않는다. 생성 save는 expected_revision=0 및 입력 revision0에서만 허용한다. 기존 파일 save는 입력 revision과 expected_revision과 저장 revision이 같아야 하며 성공 결과의 revision은 1 증가한다. 동시 CAS·원자 교체로 충돌/손상/중복 JSON 키를 거절하고 원본을 보존한다. caller 지정 private 경로만 사용한다. load/save의 협조적 OS lock sidecar 생성은 허용하며 자동 삭제하지 않는다. 손상된 기존 파일을 기본값으로 덮어쓰지 않는다.

## 4. REST·ADC 경계

단일 nonstreaming REST v1 generateContent를 사용한다. 자동 retry/continuation/stream/tool/grounding/cache 호출은 0이다. 공식 호스트는 global=`https://aiplatform.googleapis.com`, us=`https://aiplatform.us.rep.googleapis.com`, eu=`https://aiplatform.eu.rep.googleapis.com`이다. 공통 path는 `/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_id}:generateContent`다. us-aiplatform 형식으로 추측하지 않는다.

generationConfig에는 `maxOutputTokens`와 `thinkingConfig: {thinkingLevel: 요청값}`을 정확히 넣는다. 불필요한 temperature·topP·topK·candidateCount·thinkingBudget을 보내지 않는다. 반환 continuation을 따라가지 않으며 미완료로 기록한다. SDK의 자동 long decode는 사용하지 않는다. REST API 버전·google-auth/requests 실제 설치 버전과 SDK 선택 여부를 receipt에 남긴다.

프로필의 auth_profile_id를 host가 별도 ADC 경로로 해석한다. UI 요청으로 credential path를 지정하거나 파일을 업로드하지 못한다. 기존 default ADC, GOOGLE_APPLICATION_CREDENTIALS, metadata server나 다른 gcloud 계정으로 자동 탐색하지 않는다. 최초 범위는 명시 경로의 authorized_user ADC다. metadata를 읽어 quota_project_id가 settings와 같음을 확인한 뒤 credential을 만든다. 다른 quota를 with_quota_project로 조용히 바꾸지 않는다. token endpoint는 Google OAuth로 한정하고 인증 응답·credential 내용을 기록하지 않는다. 실제 REST에는 OAuth bearer와 정확한 `x-goog-user-project`를 붙이며 로그에는 bearer/header 전체를 넣지 않는다. 인증 refresh와 생성 호출 수는 별도 기록한다.

개발2 API의 첫 형태는 아래와 같다. 세부 receipt/error 키는 담당 mini contract를 독립 검수한 뒤 고정한다. 전송 오류는 정해진 코드와 비밀 없는 partial receipt만 반환한다.

```python
inspect_vertex_credentials(adc_path, *, settings) -> dict
produce_vertex_response(prompt_bytes, response_schema_bytes, *, settings,
                        adc_path, evidence_dir, cancel_event=None) -> tuple[bytes, dict]
```

canonical prompt bytes와 literal JSON schema bytes를 그대로 pin한다. Vertex wire의 provider envelope는 별도로 SHA를 기록한다. prompt와 schema를 명시한 합성 입력만 수송하고 기존 strict decoder로 응답을 검증한다. provider의 응답을 JSON 수선·fence 제거·기본 사실 삽입으로 통과시키지 않는다. schema를 provider 내부에 다른 형식으로 강제 변환하지 않는다. 논리 prompt/schema가 같은 비교와 provider wire bytes가 같은 비교를 구별한다.

credential 점검은 파일 metadata와 quota 상태를 표시하며 자동 refresh/생성하지 않는다. 파일 존재만으로 로그인 검증/모델 접근 가능을 표시하지 않는다. 실제 access preflight와 모델 실행의 확인 시점을 따로 보존한다. ADC 파일·상위 경로의 reparse/임의 endpoint/부족한 metadata는 실패로 닫는다.

## 5. 무료 체험·예산·취소

최초 실제 생성은 사용자의 Google Cloud 무료 체험 크레딧에 한정한다. paid 전환, 결제수단 변경, IAM 확대, 파트너 가입, API enablement, quota 증액을 실행하지 않는다. API ENABLED는 크레딧 조건이나 모델 접근 성공 증거가 아니다.

host 전용 private 승인 기록은 대상 프로젝트, 무료 체험 상태와 확인 시각, 잔액·만료 확인, 승인된 고정 묶음 ID를 결합한다. UI POST의 boolean이나 프로필 편집으로 이 gate를 열 수 없다. 미확인·만료·다른 프로젝트는 실제 호출을 시작하지 않고 원인을 보존한다. 일반 Cloud Billing API의 billingEnabled/open 값만으로 무료 체험/잔액을 확정하지 않는다. 사용자 확인은 그 출처를 명시하고 API로 독립 검증한 것으로 표현하지 않는다.

첫 묶음은 같은 작은 합성 입력의 모델2×추론3, 최대 생성 POST6, 각 출력512·누적 예약 출력3072, 각 timeout≤60초·전체 wall budget300초다. 실패한 POST도 사용한 호출로 남기고 재시도하지 않는다. 전송 전 예산을 예약하며 partial/timeout/cancel 뒤 사용량이 없더라도 예약을 0으로 돌려 새 호출을 허용하지 않는다. token count와 실제 비용 정보가 없으면 null/unknown이다. 출력 토큰 예약은 실제 청구 금액 증거가 아니다. 계정의 누적 테스트 예산은 프로세스 재시작/새 화면/새 batch ID로 초기화하지 않는다. 최초6 완료 후 업무 평가의 추가 실제 호출은 남은 크레딧·예산을 확인해 별도 유계 묶음으로 배정한다.

cancel은 진행 중 로컬 호출의 종료 시도와 다음 호출 금지를 뜻한다. 이미 서버에 전달한 요청의 원격 중단·무과금은 보장하지 않는다. local cancellation, provider completion unknown과 사용량 unknown을 구별한다. parent wall deadline과 bounded child cleanup을 지키고 응답 body/read/수집 queue·로그·artifact도 한정한다. 무제한 읽기·retry·join이나 종료를 막는 lock을 허용하지 않는다.

## 6. 실행 이력과 업무 평가

한 실행의 기록에는 run/batch/scenario ID·input/schema/evaluator 버전과 SHA, execution_mode(actual/mock/replay), profile ID/revision와 settings snapshot, request URL의 비밀 없는 project/location/model, 실제 thinkingLevel, wire SHA, 호출/예약 수, 시작/종료/지연, HTTP/finish/error, provider modelVersion/responseId, usage(없으면 null), cost(없으면 null), 원격 완료/취소의 한계, strict decode와 업무 평가를 각각 남긴다. 요청한 model ID와 응답이 보고한 modelVersion을 합치지 않는다. provider가 실제로 어느 모델을 처리했는지의 보고와 독립적 진위 보증을 구별한다.

응답 metadata·오류는 whitelist로 투영하고 원 credential·token·header나 사용자 원문을 실수로 포함하지 않는다. 원 synthetic 요청/응답은 private artifact로만 보존하며 public Git에는 합성 제품 fixture와 코드/비밀 없는 문서만 올린다. 실제 모델의 thought text를 화면이나 일반 로그에 복사하지 않는다.

기존 build_analysis_prompt/decode_analysis_response와 독립 봉인된 S01~S03 기대를 재사용한다. 접수/의뢰 이해·계획·가상시험·결과 설명은 작업별 prompt/schema/evaluator를 결합한 후 그 범위만 평가한다. 기존 pure operator와 FleetHarness의 권한·proposal allowlist를 보존한다. 호출 성공/JSON 통과를 시험계획 적합성·계산 정확도·물리 실행 성공으로 승격하지 않는다. 최초 연결6에서 업무5단계를 검증했다고 표시하지 않는다. 학습은 harness/prompt/평가 개선이며 모델 가중치 학습·전체 무인화 완료를 주장하지 않는다.

## 7. 화면과 검증 순서

기존 접수 화면에 새 연결 설정 영역을 추가한다. 프로필/프로젝트/지역/인증·quota 상태·선택 모델/LOW MEDIUM HIGH/출력/timeout을 보여준다. 각 모델별 저장값과 이번 실행 override를 구별하고 실행 record의 실제 snapshot을 확인할 수 있게 한다. 기존48b DOCX 화면에는 Codex provider 선택 UI가 없으므로 존재하지 않는 UI를 보존했다고 주장하지 않는다. CLI와 기존 평가 경로는 그대로 유지하며 새 영역이 중복 selector를 만들지 않는지 최신 base에서 확인한다.

설정 저장/실행/취소는 기존 session/CSRF·권한 경계를 따른다. 서버 host가 등록한 private profile와 credential 연결만 사용한다. URL/POST로 임의 파일·credential·endpoint를 주입하지 못한다. 동시에 한 actual run만 허용하고 6조합별 success/failure/not_run 및 사유를 보여준다. 설정 저장 성공, 연결 성공, strict decode, 업무 평가를 각기 표시한다. pending/unknown을 초록 성공으로 렌더하지 않는다.

수용 증거는 프로필 CAS/모델별 저장/override, 6개 REST wire thinkingLevel·model·project·quota의 정확 전달, auth/403/invalid/timeout/429/budget/cancel/partial의 독립 검사, 보호 HTTP→저장→backend→모의 transport→record→DOM, 기존 Codex CLI/가상시험 관련 회귀다. 실제6은 인증·무료 체험 gate 뒤 별도 실행한다. blocked면 구현 검증과 실제 미실행 원인을 구분한다. 각 담당은 검증·정상 commit/push/remote exact를 제출하고 root의 독립 리뷰/수정·통합/관련 회귀·정상 push 뒤 다음 작업을 이어간다.

## 8. 보호 facade의 첫 경계

개발4 소유는 신규 `labflow/ai_connection_ui.py`, `tests/test_ai_connection_ui.py`, `frontend/ai_connections/panel.mjs`, `panel.test.mjs`, `browser_check.cjs`와 기존 `labflow/ui_server.py`, `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`, `tests/test_ui_server.py`, `docs/fcc/frontend_usage.md`의 정확11이다. 제품 구현은 기존 DOCX 후보가 포함된 root 정확 base를 별도로 배정받는다.

create_server의 optional ai_connections host 설정이 private profile_path/adc_path/approval_path/budget_path/evidence_root 및 등록한 synthetic scenario를 연결한다. 이 인수는 브라우저가 제공하는 설정이 아니다. 기존 runtime의 cookie Path·scope를 확장하지 않고 별도 HttpOnly/SameSite=Strict/900초 cookie를 `/api/ai-connections/`에 발급한다. CSRF는 `X-AI-Connection-CSRF` header로만 주고 UI memory에서만 사용한다. ADC/OAuth 토큰과 이 nonce를 혼동하지 않는다. 허용 capability는 profile 읽기/편집, 등록 합성 실행, 자기 실행 취소다.

| 경로 | 용도·입력 |
|---|---|
| GET /api/ai-connections/session | loopback Host·same-origin/Fetch-Metadata 확인 후 해당 session/CSRF 발급 |
| GET /api/ai-connections/state | 같은 session/CSRF에서 catalog/profile·비밀 없는 auth/trial/budget 상태 |
| GET /api/ai-connections/runs/{id} | 자기 session의 실행 snapshot/이력. 다른 session은404 |
| POST /api/ai-connections/profile | 정확 profile, expected_revision. target/project/quota/auth ID를 host 범위로 재검증 |
| POST /api/ai-connections/run | 정확 expected_revision, scenario_id, model_id, overrides, matrix. 새 run ID와202 |
| POST /api/ai-connections/cancel | 정확 run_id. 자기 실행만 취소 요청 |

변경 POST는 Host/Origin·session/CSRF·bounded strict JSON을 모두 검사한다. client가 mode/gate/usage/cost/credential/path/endpoint를 추가하면 거절한다. 상태 GET와 poll·상세 펼침은 생성 호출0이다. 실행은 async start/status/cancel로 기존 보존 조회 transport의35초와 분리한다. 동시에 actual run1, runtime lock 밖에서 RPC를 수행한다. close는 새 작업을 막고 cancel/유계 join하며 원격 완료 unknown을 보존한다. post 전 수명·성공/실패 DTO와 D3 concrete runner 접점은 담당 mini contract와 제품 검사에서 정확히 닫고, 임시 callback/빈 성공 wrapper를 제품으로 넣지 않는다.

첫 모델 접근 상태가 미확인인 것은 테스트 자체의 차단 이유가 아니다. trial·명시 인증 파일/quota/target·등록 합성 입력·누적 예산 준비가 테스트 gate다. 모델403은 실제 접근 실패로 기록한다. `credential_file_ready`를 이미 접근 검증된 상태로 표시하지 않는다. 저장된 모델별 값과 명시 run override의 model·thinking이 실제 wire/receipt와 일치하는지 확인한다.
