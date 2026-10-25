# 첫 접수 운영 화면 — DEV4-UI-001

2026-10-23 (Asia/Seoul). [작업 배정](../../handoff/development/DEV4-UI-001.md), [전용 설계](../superpowers/specs/2026-10-23-dev4-intake-ui-design.md), [실행 계획](../superpowers/plans/2026-10-23-dev4-intake-ui.md).

## 제공하는 기능

기존 접수 서비스의 목록 → 상세 → 사실/출처 → 누락·충돌 → 분석 작업/로컬 알림을 브라우저에서 조회한다. 검색과 상태 필터, 수동 새로고침, 키보드 상세 이동, 작은 화면을 지원한다. 합성 자료와 제공 자료를 구분하고 제공 자료도 실측으로 간주하지 않는다.

빈 저장소, 조회 중, 접속/저장소 오류, 자료 미완성, 분석 대기·분석 중, 실패, 사용자 보류, 임대 만료, 미지원 상태를 구분한다. `prepare_plan`은 계획 연결 대기이며 시험 준비 완료가 아니다. `completed`는 분석 작업 완료다. 알림은 생성 당시 로컬 기록이며 읽음/외부 발송 상태가 없다.

사용자 답변은 응답 event ID로 표시한다. 그 외 사실은 일치하는 제출 후보의 원문 인용·행·파일명·SHA-256을 연결하며 출처가 없으면 근거 없음을 표시한다. 시장·목적은 서비스와 같이 `explicit`이면서 모든 출처 역할이 `request`인 후보만 확정 근거로 연결한다. 제외된 참고/추론 후보는 제출 후보에서 보존한다. 충돌/불확실 후보도 펼쳐 볼 수 있다. 원본 파일은 메타데이터만 조회하며 현재 원본 바이트의 무결성을 새로 검증하는 화면은 아니다.

## 실행

저장소 루트에서 Python 3.12를 사용한다. UI 자체는 Python 표준 라이브러리와 정적 파일만 사용하며 Node 빌드/외부 CDN이 필요 없다. 전체 저장소 검사는 `requirements.txt`와 PDF 추출용 `requirements-extract.txt`를 설치한 가상환경을 사용한다.

새 합성 데이터로 시작하려면 다음과 같이 실행한다. 생성 대상 디렉터리가 이미 있으면 덮어쓰지 않고 실패하므로 새 이름을 사용한다.

```powershell
python -m frontend.demo_fixture .local/ui-demo
python -m labflow.ui_server --workspace .local/ui-demo/state --port 8765
```

브라우저에서 [로컬 접수 화면](http://127.0.0.1:8765)을 연다. 이 명령은 합성 8건을 기존 접수 함수로 등록하고 fixture 분석을 저장한다. 실제 모델 호출·장비 제어·외부 전송을 수행하지 않는다. 서버는 Ctrl+C로 종료한다.

빈 상태도 별도로 재현할 수 있다.

```powershell
python -m frontend.demo_fixture .local/ui-empty --empty
python -m labflow.ui_server --workspace .local/ui-empty/state --port 8766
```

기존 접수 저장소를 읽으려면 `--workspace`에 `lab.sqlite3`가 있는 디렉터리를 지정한다. 없는 저장소를 자동 생성하지 않는다. `127.0.0.1`에만 바인딩하며 타 PC 공개 서버로 배포하는 기능은 없다. 로컬 사용자 인증을 구현한 서비스가 아니므로 서버 호스트의 계정·파일 접근 관리는 기존 로컬 환경의 책임이다.

## 조회 연결

| 경로 | 반환 |
|---|---|
| `GET /api/intakes` | `schema_version: 1`, `generated_at`, `intakes`, `notifications` |
| `GET /api/intakes/{intake_id}` | `schema_version: 1`, `generated_at`, `intake`, 해당 접수 `notifications` |

기존 `active_intake.intake_status`와 `intake_jobs.notifications`를 같은 SQLite 읽기 스냅샷에서 호출한다. `Store`를 생성해 마이그레이션하지 않고 `mode=ro` 및 `query_only`를 사용한다. 변경 메서드·외부 Host/Origin·임의 파일 경로·쿼리를 거절한다. 응답에는 lease token을 추가하지 않는다. 정적 자산은 allowlist만 제공하고 원문은 DOM `textContent`로 표시한다.

미지원/손상 상태는 `503`과 `store_missing/store_unavailable/state_invalid`, 없는 접수는 `404`와 `intake_not_found`로 반환한다. 화면은 HTTP 200이어도 중첩 사실/후보/질문/출처/작업/파일/알림의 자료형과 필수 필드를 검사한다. 구조가 잘못되면 해당 필드 경로를 표시하고 적용하지 않는다. 출처 없음과 새로운 상태 코드는 잘못된 객체/배열 구조와 구분한다.

모든 패널과 조회 시각을 화면 밖에서 구성한 뒤 상태와 함께 반영한다. 검사 또는 화면 구성 실패 시 마지막 성공 스냅샷의 목록·상세·집계·알림·시각을 함께 보존한다. 정상 조회를 한 적이 없으면 검색/필터 조작으로 오류·로딩을 빈 저장소로 바꾸지 않는다. 시각은 KST로 표시하고 API 시각은 ISO UTC다.

## 검증 재현

```powershell
python -m unittest discover -s tests -p "test_ui_*.py" -v
node --test frontend/model.test.mjs frontend/snapshot.test.mjs
python -m unittest discover -s tests -v
python scripts/check_artifacts.py
```

선택적 브라우저 검사는 설치된 `playwright`와 Chromium을 사용한다. 위 합성 서버를 8765, 빈 서버를 8766에서 실행한 뒤 다음을 실행한다. 패키지를 별도 디렉터리에 설치했다면 `NODE_PATH`로 해당 `node_modules`를 지정한다. 다른 포트는 `UI_DEMO_URL`, `UI_EMPTY_URL` 환경변수로 바꿀 수 있다.

```powershell
node frontend/browser_check.cjs
node --test frontend/review_check.cjs
```

스크린샷과 검사 결과는 `.local/dev4/evidence/`에 저장한다. [고정 화면 증거](../../frontend/evidence/README.md)는 이 작업의 합성 자료만 포함한다. Node는 상태 검사와 선택적 브라우저 검사에만 필요하다.

초기 검증은 Python 118개·Node 상태 6개·브라우저 9개였다. 총괄 통합 리뷰의 3개 결함을 재현한 후 확정 출처 필터, 중첩 응답 검사·일괄 화면 반영, 초기 로딩/오류 보존을 수정했다. 후속 검증은 Python 전체 118개(신규 UI 11개 포함), Node 상태·계약 20개, 기존 브라우저 9개와 리뷰 회귀 10개다. 리뷰 회귀는 잘못된 중첩 자료 및 실제 렌더 예외에서 이전 스냅샷 보존과 첫 오류/로딩 중 검색·필터를 확인한다. 별도 로그와 화면은 `.local/dev4/review-evidence/` 및 [고정 리뷰 증거](../../frontend/evidence/README.md)에 있다.

기존 브라우저 검사는 실제 합성 서비스 연결·빈 상태·HTML 안전 표시·검색/필터·키보드·알림 이동·390px 화면·미지원 상태/출처 누락·조회 실패/재시도·초기 오류·로딩을 확인했다. 이 검사의 페이지 JavaScript 오류와 외부 자산 요청은 0건이다. 리뷰 회귀의 렌더 예외는 테스트에서 의도적으로 주입한다. Python/JavaScript 정적 검사, 문서 UTF-8/링크와 diff 검사도 수행한다.

초기 환경에는 reportlab 등 일부 의존성이 없어 기존 검사 2실패/3오류가 발생했다. 자기 clone의 가상환경에 기존 requirements를 설치한 뒤 전체 검사가 통과했다. 제품 공통 의존성 파일은 변경하지 않았다.

## 통합과 다음 계약

공통 스키마·Store·접수/하네스/가상 모듈·CLI를 변경하지 않았다. 현재 계약으로 조회가 가능하여 차단된 공통 변경은 없다. 다음 단계의 답변/보류 변경 API는 기존 `respond`의 신뢰 경계·event ID·대상 확인을 유지해야 한다. 알림 전달 확인/발생 시각, 대량 조회의 페이지 구분, 원본 파일 뷰어, 실시간 작업 갱신은 총괄과 별도 계약이 필요하다.

업로드, AI 자동 대화·상시 모델 작업자, 가상 시험 실행 제어, 실장비/현장 운전, 공식 성적서 발행은 이 화면에 연결하지 않았다. 실측 비교·현장 검증·기관 적합성 검증은 미실행이다. 이번 통과는 접수 조회 기능과 합성 상태의 소프트웨어 검증이다.

## DOCX 보존 관측 읽기

신뢰된 로컬 호출자는 실제 DOCX 보존 receipt에서 받은 artifact ID와 `reference.binding` 한 개를 host에 고정할 수 있다. `workspace`, `intake_id`, `retained_receipt`는 이미 수행한 명시 보존 업무의 실제 값이다. browser가 파일 경로나 artifact ID를 선택하거나 원본을 다시 해석하지 않는다.

```python
from labflow.store import Store
from labflow.ui_server import create_server

store = Store.open_existing(str(workspace))
server = create_server(
    store.root, port=0,
    intake_reference_store=store,
    intake_reference_read_scope=(intake_id,),
    intake_docx_reference_selection=(
        retained_receipt['artifact_id'], retained_receipt['reference']['binding']),
)
```

서버 실행·종료는 [기존 reference host 수명](intake_reference_host_usage.md)을 따른다. Store는 호출자가 소유하며 server의 source 요청과 worker가 실제 drain된 뒤 닫는다. 생성 시에는 원본·artifact admission을 실행하지 않는다. 선택을 공급하지 않는 기존 CLI와 `create_server` 기본값에는 새 DOCX 구역·버튼·source 요청이 없다.

선택한 접수에서 기존 이력 조회가 성공하고 read scope/session이 허용되면 **DOCX 보존 관측 읽기** 버튼이 나타난다. 버튼은 기존 session·CSRF·Origin 검사가 적용되는 current POST의 `action=docx_retained` 분기를 명시 실행한다. 원본·등록·보존 bytes를 그 요청에서 확인한 원 관측을 읽으며 native 재파싱이나 retention 쓰기를 하지 않는다. 일반 `/api/intakes` GET과 history body에는 native 본문을 넣지 않는다. history의 선택 안내 헤더는 구성 안내이며 별도 source 권한이나 현재성 증명이 아니다.

화면은 실제 artifact ID/bytes·등록 synthetic·원 source/revision/fingerprint/document 결합, reader/profile/status/complete 선언, issues와 실제 part/element-child/physical-cell·merge 위치를 원 값대로 표시한다. 페이지는 `unavailable`이며 PDF page/text-line 인용이나 문단 본문·HTML·링크·다운로드로 바꾸지 않는다. `ok`, `empty`, `partial`, native 실패와 unknown 선언을 구별한다. 보존 관측은 현재 분석의 `requires_parser`/unread·열린 질문을 해소하거나 사실·인용·실행을 승인하지 않는다.

파일에 결합된 이전 관측과 현재 분석을 구별한다. 분석만 바뀌면 이전 명시 요청 관측을 유지할 수 있지만 새 확인 결과로 바꾸지 않는다. 다른 revision/fingerprint/문서 SHA·bytes로는 재결합하지 않는다. 실패 시 고정 오류와 이전 성공 관측을 함께 구별하고, **성공 history 응답에서 선택 헤더가 없을 때** 현재 구역을 제거한다. 일반 metadata GET에는 원래 이 선택 헤더가 없으므로 그 부재를 선택 소멸로 해석하지 않는다.

원본/보존 읽기 한도와 별도로 이 화면의 전체 관측 한도는 UTF-8 2MiB, 깊이64, JSON value200000, native 구조2000, issues128이다. 초과는 HTTP413 `intake_reference_ui_input_limit`이며 저장 실패나 native 실패를 뜻하지 않는다. D1의 원 admission 한도 오류는 별도 `intake_docx_reference_input_limit`다. 현재 결합 변경은409 `intake_docx_reference_revision_changed`, 무결성 확인 실패는503 `intake_docx_reference_source_integrity_invalid`로 반환하며 잘라낸 성공이나 빈 관측으로 수리하지 않는다. 전체 오류·형상은 [공개 설계](../superpowers/specs/2026-10-25-intake-docx-retained-observation-ui-design.md)를 따른다.

Tab/Enter로 버튼과 위치 details를 사용할 수 있다. details 펼침은 추가 읽기를 하지 않는다. 권한 오류 뒤에는 이력을 명시 새로 조회해야 하며, 다른 source 작업 중429·browser 취소·timeout·종료를 새 권한이나 실제 서버 취소 완료로 간주하지 않는다. 마지막 성공 관측은 반환 이후의 현재성을 보증하지 않는다.

관련 client 검사는 아래 범위다. `--mode docx`는 선언 wire/오류 mutation의 실제 브라우저 검사이며, 실제 retention→readonly admission→보호 HTTP→DOM 검증과 분모가 다르다.

```powershell
node --test frontend/model.test.mjs frontend/snapshot.test.mjs frontend/intake_references/model.test.mjs frontend/intake_references/transport.test.mjs
node frontend/intake_references/browser_check.cjs --mode docx
```
# Vertex 연결 설정과 등록 합성 테스트

이 영역은 `create_server(..., ai_connections=...)`를 명시한 host의 별도 기능이다. 기존 접수·보존자료 session/CSRF·35초 transport를 확장하지 않는다. 메뉴의 **모델 연결**을 선택할 때만 화면 모듈과 AI session을 조회한다. D1/D2/D3 정식 모듈이 없으면 명시 실패하며 모의 provider로 대체하지 않는다. 등록7 검증은 typed 경계, 정식 D1+D3/genuine decoder와 fake concrete D2만 둔 보호HTTP, 그 HTTP DTO의 DOM replay를 별도 분모로 기록한다. 이 합성 검증은 실제 인증·Vertex·업무 의미 검증이 아니다.

## Host의 정확 config6와 첫 연결 입력

host config는 정확 `profile_path`, `adc_path`, `approval_path`, `budget_path`, `evidence_root`, `scenarios`다. 앞5개는 절대 native `Path`이며 reparse/symlink를 거절한다. 실제 credential 경로·파일·토큰을 UI로 보내지 않는다. profile/approval/budget/evidence는 각각 다른 private 경로다. UI는 승인·누적 budget을 작성하거나 초기화하지 않는다.

`scenarios`는 tuple이며 각 등록값은 정확 `scenario_id`, `evaluator_id`, `prompt_bytes`, `response_schema_bytes`다. prompt/schema는 native bytes다. 브라우저가 원문·파일·endpoint·credential·mode·gate를 입력하거나 등록하는 API는 없다. version/family/assessment를 config에 추가하지 않는다. `scope_id`는 scenario에서 파생하지 않는 독립 ASCII ID이며 `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}` 문법을 따른다. 슬래시가 들어간 ID는 거절한다. 선택 case와 승인 ID/evaluator/prompt/schema·project/quota/auth/trial/누적 예산을 서버가 별도로 정확 결합한다.

지원 입력은 아래7개다. host가 원 pair를 기존 tuple에 제공하며 D3 public build가 등록 pair를 최종 검증한다. 알려지지 않은 ID/evaluator는 미지원으로 표시하고 실행을 막는다. 각 scenario/evaluator version은 native int1/1이다. 원 wire/schema 지문은 [등록7 공통 설계](../superpowers/specs/2026-10-25-vertex-registered-inputs-ui-design.md)와 [intent registry](vertex_intent_registry_contract.json)를 따른다.

| scenario_id | evaluator_id | schema |
|---|---|---|
| DGM-AI-CONNECTION-001 | connection-json-v1 | 321 bytes |
| intake-synthetic-s01 / s02 / s03 | intake-understanding-v1 | 공통1410 bytes |
| intent-synthetic-i01 | intake-test-intent-semantic-v1 | 2694 / 937b3b9fa423bbfea40116495dd7cbed3937a3839e17445f08f7a37e48faf83d |
| intent-synthetic-i02 | intake-test-intent-semantic-v1 | 2694 / 47bfac67fde55165684381d3c624a07566b2790916f148e7d3534e593ef1f75b |
| intent-synthetic-i03 | intake-test-intent-semantic-v1 | 2694 / 75e492477ac8d7bb8949143b46941aec089359522c1741d70f969a135434f806 |

intent schema3은 길이만 같고 request binding이 달라 SHA가 각각 다르다. 기존1410이나 하나의2694 schema로 대체하지 않는다. analysis의 genuine build_analysis_prompt/decode_analysis_response와 intent의 별도 build_intake_test_intent_prompt/decode_intake_test_intent_response를 D3가 직접 사용한다. UI는 raw context/응답을 해석하거나 private case dict를 import하지 않는다.

아래 변수들은 host가 이미 준비한 private 경로다. 명시한 원 pair를 읽어 그대로 등록하며 새 입력을 발명하지 않는다. `isolated_adc_path`, 승인 파일 및 누적 ledger는 총괄이 준비한 것을 사용한다.

```python
from hashlib import sha256
from labflow.ui_server import create_server

prompt_bytes = prompt_path.read_bytes()          # root가 제공한 고정 합성 pair
schema_bytes = response_schema_path.read_bytes()
assert len(prompt_bytes) == 639
assert sha256(prompt_bytes).hexdigest() == "bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230"
assert len(schema_bytes) == 321
assert sha256(schema_bytes).hexdigest() == "a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9"

ai_connections = {
    "profile_path": private_root / "vertex-profile.json",
    "adc_path": isolated_adc_path,
    "approval_path": approval_path,
    "budget_path": budget_path,
    "evidence_root": private_root / "vertex-ui-evidence",
    "scenarios": ({
        "scenario_id": "DGM-AI-CONNECTION-001",
        "evaluator_id": "connection-json-v1",
        "prompt_bytes": prompt_bytes,
        "response_schema_bytes": schema_bytes,
    },),
}
server = create_server(workspace, port=8765, ai_connections=ai_connections)
try:
    server.serve_forever()
finally:
    server.server_close()
```

기존 reference 기능도 사용하는 host는 원래의 `intake_reference_store/read_scope/append_scope/...` 인수를 위 호출에 그대로 전달한다. AI 기능 때문에 기존 scope를 workspace로 넓히지 않는다. 공식 조립은 [공통 설계](../superpowers/specs/2026-10-25-vertex-ai-connection-design.md)와 [catalog](vertex_ai_connection_catalog.json)를 따른다.

## 저장과 실행

기본 profile은 revision0이며 첫 실행을 명시 거절한다(`409 ai_connection_ui_profile_not_saved`). 화면에서 모델별 설정을 **프로필 저장**해 revision1 이상으로 만든 뒤 실행한다. profile ID/auth ID는 vertex-trial, target/quota는 project-a6310591-f8cc-487c-9e3로 host가 고정한다. location/selected_model/models와 CAS revision만 편집할 수 있다. LOW/MEDIUM/HIGH·기본 MEDIUM/512/60, token 정수64..8192, timeout 유한1..120초(소수 허용)다.

저장 설정과 이번 실행 override는 별개다. 선택1 테스트는 model과 세 설정 override를 정식 D1/D3에 전달하고 다른5행은 not_selected로 보존한다. matrix는 model_id=null이며 LOW/MEDIUM/HIGH 고정6행에 flat output/timeout override만 전달한다. matrix thinking override는 명시 거절하며 무시하지 않는다. 첫 실제6 조건은 저장 revision1 이상·global·각512/60·위 고정 pair·유효 trial/명시 ADC/quota/누적 예산이다. profile의 유효한 선택이 최초 승인 상한을 넘으면 budget_rejected/not_run이며512/60으로 조용히 바꾸지 않는다.

자동 재시도·continuation·대체모델·추가 generation preflight는0이다. 모델 접근 미확인은 첫 테스트 자체의 차단 이유가 아니다. 인증 파일 metadata-ready와 auth/model access verified를 구별하며 실제403은 row 실패로 기록한다. trial은 상태·확인 시각만 표시하고 계정·잔액·credential 경로를 투영하지 않는다.

상단은 인증 메타데이터 **사전 점검**이다. 실제 모델 접근·HTTP·완결·strict는 각 행의 관측으로 확인한다. 전역 gate가 준비됐어도 다른 선택 case의 승인을 뜻하지 않으며 선택 승인 불일치는 worker/예약/producer 전에409로 거절한다. case 변경·새 승인·새 profile/batch/clone은 같은 누적6/3072를 reset/refund하지 않는다. 소진/active면 모든 case의 추가 생성0이다. 등록7은 추가 실제 실행 권한이 아니다.

화면 selectors: 메뉴 `[data-view="ai-connections"]`, root `#ai-connections-panel`, 저장 `#ai-save`, 지역 `#ai-location`, 저장 기본 모델 `#ai-default-model`, Argon/Flash 설정 `#ai-level-0/1`, `#ai-output-0/1`, `#ai-timeout-0/1`; 등록 입력 `#ai-scenario`, 선택 모델 `#ai-run-model`, 이번 override `#ai-run-level`, `#ai-run-output`, `#ai-run-timeout`; 선택1 `#ai-run-selected`, **최초 matrix6 `#ai-run-matrix`**, 취소 `#ai-cancel`. 최초 matrix6에는 추론 override를 비운다. 사용자 추가 인증 질문이나 파일 경로 입력을 만들지 않는다.

## HTTP·투영·수명

별도 쿠키는 `dgm_ai_connection_<port>`, Path=/api/ai-connections/, HttpOnly/SameSiteStrict/Max-Age900·절대900초다. CSRF는 X-AI-Connection-CSRF header로만 반환해 JS closure에 보관한다. GET session에서 발급하고 GET state/runs 및 POST profile/run/cancel은 같은 session/CSRF와 loopback Host·same-origin을 검사한다. 다른 session의 run은404다. configured AI의 HEAD/OPTIONS는405, None은503 unconfigured다.

POST profile은 정확 `{profile,expected_revision}`, run은 `{expected_revision,scenario_id,model_id,overrides,matrix}`, cancel은 `{run_id}`다. async run202→status GET poll→cancel로 장시간 작업을 분리한다. GET·상세 펼침은 generation0이며 host 전체 AI run1·queue0이다. status/cancel은 actual slot을 재획득하지 않는다. body32KiB·5초 strict JSON(UTF8/중복키/깊이/미지 필드 제한), Session4KiB/State64KiB/Run256KiB 응답, 클라이언트 HTTP당10초·poll1초 한도다.

UI는 서버의 settings/profile hash를 opaque binding으로 비교하며 Python60.0을 JS60으로 재canonical하지 않는다. selected/matrix의 요청값·서버 snapshot·후속 record를 대조한다. 사용량은 원 nullable6키를 유지하되 signed64 정밀도를 잃지 않도록 decimal string/null로 투영한다. cost는null/미확인이다. actual/mock/replay와 입력 synthetic, HTTP/완결·strict decode·업무 품질을 구별하며 첫 연결의 업무 품질은 not_assessed다. D2 artifacts·raw/response/thought·credential·headers·파일 경로는 UI DTO에 넣지 않는다.

connection strict reason은 connection_verified/connection_response_invalid, analysis는 intake_response_verified/intake_response_invalid, intent는 intent_response_verified/intent_response_invalid다. native version·입력군·strict/status/reason/error를 정확 결합하고 미등록 code를 거절한다. 업무 두 입력군은 assessment not_assessed/null/semantic_evaluator_not_connected이며 quality=not_run을 유지한다. evaluator 이름에 semantic이 있어도 의미평가 연결을 뜻하지 않는다. 원 origin zero SHA·검증 false/권한 false를 actual 전송이나 형상/인용 검사로 true로 바꾸지 않는다. Store 입수·의뢰 확정·규칙/시험법 정답·시험계획·가상/실장비 동작·결과 설명은 미지원이며 analysis→intent를 자동 연쇄 실행하지 않는다.

수명 변경·늦은 응답·렌더 오류·요청 실패에는 이전 성공 관측과 draft를 보존하고 현재 권한/결과로 승격하지 않는다. POST 전달 불명은 자동 재전송하지 않고 명시 refresh로 자기 실행을 대조한다. 숨김·BFCache suspension은 poll/HTTP를 중단하고, destroy는 DOM/listener/nonce를 회수한다. 취소는 미전송 작업 중지·진행 중 로컬 종료 시도이며 원격 중단/무과금/예산 환불을 보장하지 않는다. close는 AI worker를 cancel하고 최대5초 join하며 살아 있으면 close_unconfirmed, 기존 HTTP cleanup은 finally에서 수행한다.

실패 body는 `{error:{code}}`의 `ai_connection_ui_` 고정 코드만이다. invalid_request400/access_denied403/not_found404/method_not_allowed405/request_timeout408/revision_conflict409/profile_not_saved409/gate_blocked409/length_required411/input_limit413/unsupported_media415/expectation_failed417/busy429/unconfigured·session_unavailable·unavailable503을 구별한다. producer403/429는 run row의 provider 관측이며 UI session403과 다른 상태다. 실제 호출과 최종 업무·실장비 검증은 이 UI의 typed double 통과로 대체하지 않는다.

D3 기록 I/O 실패 등으로 원 D2 예외가 올라오면 원 객체/receipt는 runtime의 private 실패 기록에 보존하고, run DTO에는 정식 D2/D3 whitelist의 고정 code만 넣는다. raw 예외·artifact 경로는 반환하지 않으며 aggregate 시도 수·실행 출처는 미확정/null로 둔다. 정상 failed row의 알려진 generation0/1과 absent artifact bytes0을 결측값으로 바꾸지 않는다. 새 세션이 발급되면 이전 세션 run의 controls/관측·history를 퇴역시키고 자동 재실행하지 않는다.

## 등록7의 합성 보호HTTP와 DOM replay 검사

기존 tests/test_ai_connection_ui.py 안의 RegisteredHTTPTests는 정식 D1 profile과 genuine D3 public builder/runner, 두 genuine 업무 decoder를 사용하고 D2 inspect/produce만 모의다. 원14 pair는 같은 테스트 파일의 literal이며 새 fixture 파일이나 `.local` 런타임 입력에 의존하지 않는다. 사전 metadata 횟수와 fake D2 생산/관측 시도를 별도로 기록한다. nullable 자연완료/legacy True·origin false/zero·intent65536/65537·cross-family·실패 decoder0·same budget·원 session/CSRF도 검사한다.

`VERTEX_UI_HTTP_CAPTURE`는 선택적인 **출력** 경로다. 설정하지 않아도 owned HTTP 검사는 동일하게 실행된다. 기록된 보호HTTP DTO를 `VERTEX_UI_HTTP_REPLAY`로 browser_check에 제공하면390/1440 replay를 추가한다. replay의 API/producer 실행은0이며 DTO 사본의 표시 횟수를 genuine API 성공 수에 더하지 않는다. 제공하지 않은 replay는 not_run으로 명시한다.

```powershell
New-Item -ItemType Directory -Path .local -Force | Out-Null
$env:VERTEX_UI_HTTP_CAPTURE = Join-Path (Resolve-Path .) '.local/registered-http.json'
python -B -X utf8 -m unittest discover -s tests -p test_ai_connection_ui.py -v
$env:VERTEX_UI_HTTP_REPLAY = $env:VERTEX_UI_HTTP_CAPTURE
node frontend/ai_connections/browser_check.cjs
```

이 검증은 실제 ADC/인증/모델·실 ledger·현장 장비를 사용하지 않는다. 원 실패/unknown·nullable usage/cost·no-reset/no-refund를 보존하며 실제 최초6과의 근거·분모를 구별한다.

# 제공 캠페인 기록 · 읽기 전용

이 영역은 [공개 UI 설계](../superpowers/specs/2026-10-25-vertex-campaign-readback-ui-design.md)와 [reader 사용법](vertex_campaign_readback_usage.md)의 제공 기록만 표시한다. 등록7 실행 화면과 다른 읽기 경로이며 의미 평가·현재 권한·원본 artifact 검증·실제 회계 반영을 새로 수행하지 않는다. 현재 registry는7개 그대로다.

호스트가 명시적으로 선택한 native tuple2 `(manifest, artifacts)`를 `create_server(..., ai_connection_campaign_readback=(selected_manifest, selected_artifacts))`로 주입한다. artifacts는 source ID→immutable bytes/None의 native dict다. 파일 경로·업로드·URL·자동 탐색·callback을 입력하지 않는다. genuine `build_vertex_connection_campaign_readback`을 listen 전에1회 호출한 뒤 분리된 C1 JSON bytes와 선택 지문만 보존한다. 같은 GET를 반복해도 reader·생성·예약을 다시 수행하지 않는다. caller가 반환 뒤 입력 dict를 바꿔도 cache는 바뀌지 않는다.

`ai_connections=None`과 이 tuple만 주면 readback-only host가 된다. 정상 session/guard/CSRF는 재사용하며 실행 state/auth/policy·D1/D2·worker/producer·Store/DB·승인/원장/ADC는 이 읽기 경로에서 사용하지 않는다. 해당 host는 제공 기록과 기존 정적 자산만 노출하고, 기본 앱의 `/api/intakes` 등 workspace/catalog 경로와 percent-encoded 별칭도503 unconfigured로 닫는다. 기존 실행 host/default host는 그대로다. 두 설정이 모두 None이면 종전 unconfigured, 기존 실행 설정만 있고 tuple이 없으면 캠페인 GET는503이다.

`제공 기록 조회`를 누르면 AI session bootstrap 후 `GET /api/ai-connections/campaign-readback`을 보낸다. body/query는 없으며 기존 loopback Host·same-origin·Fetch·cookie/CSRF·900초 범위를 검사한다. 응답 직전 만료/closing도 다시 확인한다. HTTP200 body는 D3 report9 그대로이고 `X-AI-Campaign-Selection`은 manifest C1의 opaque SHA-256이다. 새 wrapper DTO나 기존 State12/Run16/Cell17의 새 key는 없다. 정상 unknown/issues는 HTTP200이며 원본 누락을 미실행/성공으로 바꾸지 않는다. HEAD/다른 method405·Allow GET, 보호 위반403, 잘못된 GET framing400, 미구성503을 구별한다.

입력 cap은 reader source32/파일1MiB/전체8MiB다. 신규 응답만1MiB/depth32/node40000이고 기존 Session4KiB/State64KiB/Run256KiB 한도는 유지한다. browser10초·서버 socket5초를 사용한다. startup의 입력 형상/cap 실패는 고정 `vertex_campaign_readback_invalid_input` ValueError로 listen 전에 실패한다. 반환 projection 계약 위반/출력 cap도 listener 없이 실패하며 truncate/빈 성공으로 대체하지 않는다. readback-only의 유효 session에 들어온 미구성 POST는32KiB 이하의 명확한 body만 해석 없이 소비하고503으로 닫아 Windows의 unread-body reset을 피한다.

화면 접점은 `#ai-campaign-read/status/summary/cells/issues`, source 영역은 `#ai-campaign-sources`다. 모드를 선택하거나 모델을 실행하는 버튼은 없다. 여섯 축의 종합 상태와 원/effective 상태·해석 출처·선언 origin·원/재생 mode·원/effective generation을 전용 한국어 열로 나란히 표시한다. 나머지20필드의 관측·예약·사용량 근거는 키보드로 펼치는 details에 둔다. 원 연결 없는 replay6와 미실행/coverage5의 **없는 key**는 `제공 항목 없음`, 명시 null은 `미확인(null)`, native0은 `0`으로 구별한다.

history.source_ids는 원/재생/영수증의 통합 참조다. 원/replay별 ID나 개별 competing replay 이력을 복원하지 않는다. 반환 history·issue/source만 표시하며 원 success가 있어도 축 unknown을 덮지 않는다. source.status=valid는 raw/외형 처리 상태이며 모델 성공·권한 검증이 아니다. 선언 bytes/SHA를 현재 파일 검사 결과로 해석하지 않는다.

전체 totals12와 출처별 origin10, usage6의 metric3은 서로 구별한다. 알려진 부분합0/불명 exchange 수0이 전체 사용량0·완결을 뜻하지 않으며 total null을 유지한다. 출처별 참조가 겹칠 수 있어 합산하지 않고 누적 snapshot도 sum/max/latest로 현 잔액에 적용하지 않는다. origin에 없는 new_actual_calls/by_generation_origin을 채우지 않는다. 비용 kind=not_applicable도 금액0이 아니며 amount/currency/price_version·ledger_balance/remaining_capacity는 null이다. `provided_records_only`·권한/기초 자료 검증 false2·업무 품질 미평가는 항상 분리 표시한다.

새 readback parser만 BigInt로 원 int64 및 최대192×int64의 부분합을 보존한다. Number로 반올림하거나 기존 실행 parser/clone에 BigInt를 섞지 않는다. 요청 실패·timeout·잘못된 JSON/header/false 위조·렌더 실패는 같은 session/binding의 마지막 정상 관측을 이전 관측으로 보존한다. 같은 nonce의 선택 지문 변경은 거절한다. 새 nonce는 다음 GET 완료 전에도 옛 scope를 퇴역시키며 hide/BFCache/destroy는 HTTP/timer/늦은 응답을 회수한다. 자동 재조회·재실행·원장 reset/refund는 없다.

합성 검사는 `CampaignReadbackHTTPTests`와 공통 host 검사, Node typed parser, genuine reader→보호 loopback HTTP→production panel의390/1440 DOM으로 구별한다. fixture는 owned 테스트의 새 메모리 선택6종과 공개 shape primitive만 쓰며 실제 producer/decoder/모델 실행 증거가 아니다. 실패 전송/clock/DOM 주입과 기존 typed 실행 UI·선택적 DTO replay는 별도 분모다. `VERTEX_UI_PROOF_ROOT`는 `.local` 아래의 새 증거 namespace이며 모든 쓰기 전512파일/32MiB를 검사한다. 브라우저 helper·한정 화면·정제 report·자원 회수 기록만 남기고 원 temp workspace 전체를 복제하지 않는다.
