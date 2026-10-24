# 접수 참고검토 host046 설계

2026-10-24 Asia/Seoul. A 동일 접수 host 재사용·A1 trusted startup exact4 입력·코어 우선 구현을 확정한다. v3 정적 독립 Yes C0/I0 뒤 공개한 계약이며 아래 수용 조건은 미실행이다. root023의043/042 정확 의존을 포함한 게시 SHA와 이 설계/계획을 총괄이 실제 배정 메시지로 고정하면 개발2는 신규3 코어를 구현한다. 실제 backend provider 인수는 동일세션 HTTP/DOM 통합 완료의 선행조건이다.

## 현재 소유권과 단계

| 담당 | 정확 범위 |
|---|---|
| 개발2 |신규 `labflow/intake_reference_review_host.py`, `tests/test_intake_reference_review_host.py`, `docs/fcc/intake_reference_review_host_usage.md` 3파일의046 코어 |
| 개발1 |후속049 backend: 기존 `labflow/ui_server.py`, `tests/test_ui_server.py`, 신규 `docs/fcc/intake_reference_host_usage.md`.044 history/current·같은 세션/RLock·아래 최소hook·configured 종료/정제오류 |
| 개발4 |현재044 A1 신규5 유지. 이후 frontend app/index/styles·transport·browser checker/DOM 접점은 총괄이 별도 배정 |
| 총괄 |정확 base·의존·소유권·공개 계약 고정, 독립 리뷰/소유 수정·통합 회귀·게시·후속 배정 |

이는 아직 착수하지 않은044 A2의 backend와 frontend 소유를 나눈 최신 배정이며 현재044 A1 파일/계약/API를 바꾸지 않는다. 아래의 ‘044 host/A2/provider’는 동일 접수 host의 서버 책임을 뜻하고 backend 담당은 개발1/049다. A1은046 trusted startup 입력 선택 또는044 frontend 구성요소 단계라는 각 문맥을 유지한다. 두 번째 listener/session/secret·가짜 provider를 만들지 않는다.

최소hook `_reference_action_binding(session_id)`는 같은 실제 세션의 내부 exact binding3을 제공하고, `_reference_parent_call(*, source=False)` context manager는 같은 RLock으로 admission/active와 source 동시1/queue0을 감독한다. 부모 I/O 동안 전역 RLock을 잡지 않고 finally에서 회수한다. 실제049 configured `server_close`는 admission 차단→진입한 모든 부모 finally/active0→worker/socket·세션 회수 뒤 반환해야 caller가 borrowed043 Store를 닫을 수 있다. stdlib ThreadingHTTPServer의 daemon worker 또는 기본 server_close만으로 이 보장을 주장하지 않는다. configured 오류 경로는 원문 traceback/secret/path를 stderr/HTTP에 출력하지 않는다. 미구성(None)·기존040 경로의 동작은 그대로 검증한다.

046 core는 trusted binding3/실제 RLock과 genuine043/042를 직접 호출해 구현·검증할 수 있다. 실제 세션 auth/CSRF·current 교차 source gate·HTTP 전송·DOM·configured host 종료는049 provider 인수 후 별도 phase로 검증한다. 코어 검사를 이 통합 결과로 합산하지 않는다.

기존 부모 합성 feasibility는 public025 외부 build1/decode1·public042 prepare2이며046/043/HTTP/registry 실행0이다. 중첩 호출과 fixture 생성/파싱/분석·원문 read는 별도 계수하고 read byte 수 미측정·원래 run-01 계측 실패를 보존한다. 새 실제 모델/고객 자료/실장비 실행이나 전체 무인시험소 완료의 증거가 아니다.

## 1. 읽은 기존 접점과 재사용 판단

root021 이후 관측한 제품 ui_server.create_server에는 fcc_case_catalog와 읽기 model이 있고, intake-reference session/CSRF/prepared registry는 없다. 실제 기존 registry는 VirtualFleetServer의 session_id/csrf_token/RLock/receipts4096과 virtual_session의 파일 기반 replay session이다. 전자는 synthetic runtime actions/advance 결과를 보존하고, 후자는 JSON replay/OS lock·파일 저장을 소유한다.042 PreparedReferenceReview나 접수 권한·catalog·Store 수명에 맞춘 registry가 아니다. 이 객체나 secret을 참고등록 host에 연결하지 않는다.

총괄이 A를 선택한044 계약/v2에는 **같은 intake-reference host**의 session128/idle900초, cookie·CSRF, read scope, active 부모 호출 감독과 current 동시1/queue0이 예정돼 있다. 현재 실행된 제품 registry로 부르지 않는다.046은 최종 인수된044 host/session/lock/admission을 확장하는 **A**를 총괄이 선택했다. 두 번째 cookie/세션/전역 registry/043 Store를 만들지 않는다.

| 안 | 접점 | 판단 |
|---|---|---|
| **A 권고:044 host 세션 확장** | 동일 Store/catalog·session/CSRF/scope와 active/busy를 재사용하고 private 준비 handle만 유한하게 보관 | history/current 소유와 경계를 유지하고 prepare/append 두 POST를 추가할 수 있음 |
| B 독립 참고등록 서버/세션 | 새 listener·cookie·secret·Store 수명/중복 요청 cache를 별도 구현 | 같은 접수의 권한/종료/상한을 두 곳에서 조정해야 함. 필요 근거 없음 |
| C stateless 서명 token | 준비본 전체를 브라우저에 보내거나 append 때 재준비해야 함 | private 객체 비노출·원래 준비 입력/시점·재전송 계약과 맞지 않음 |

기존038 request_id/record/event가 **영속 등록의 멱등 근거**다. host가 이를 새 DB/파일 cache나 임의 `replayed=true` 값으로 대체하지 않는다. host registry는 준비 객체의 메모리 수명과 세션 결합만 맡는다.

## 2. 실제 검토 입력의 인수 공백과 최소 선택

현재 제품 UI/HTTP를 읽은 범위에는025 build_case_review_context/decode_case_review_response의 context+validated_response를 host에 보존/게시하는 경로가 없다. 기존 FCC 사례·claim 선택은042가 요구하는 검증 응답 그 자체가 아니다. 브라우저 선택에서 model producer 응답을 꾸미거나 새 모델을 호출해 이 공백을 감추지 않는다.

**선택된 A1**은 trusted host가 이미 가진025 context/validated_response/producer를 startup의 private 입력 목록으로 인수하는 것이다. 원래 검토 절차·위임을 재사용하며 새로운 고객 파일 업로드를 시작 조건으로 요구하지 않는다. 코어 수용은 genuine public025 입력·정식043/042와 trusted binding3/RLock 직접 호출 경계에서 수행한다. 실제044 A2 인수 뒤 동일세션의 HTTP→042 준비/등록→제품버튼으로 통합 수용한다. 실제 검토 응답 producer와의 동적 연결은 후속 trusted publisher 접점이며 현재 존재한다고 주장하지 않는다.

각 입력은 exact4 `{intake_id,case_context,validated_response,producer_name}`다. startup에서 plain detached 사본/부모 예산·ID만 확인하며042·retained PDF 읽기/DB쓰기0이다. 정상 재결합/선택 검증은 준비 시042→032가 판정한다. catalog는 host의 기존 genuine fcc_case_catalog 객체 하나다. 동일 intake 입력은1개, 목록은 최대100/사본합32MiB다. 개별 context8MiB/response320KiB·부모 depth/nodes를 유지한다. raw body·query·파일 경로·임의 callback으로 입력을 등록하는 새 HTTP 경로는 없다.

review_input_id는 canonical5 `{schema_version:1,intake_id,case_context_sha256,validated_response_sha256,producer_name}`의 SHA다. private 항목은 host instance·catalog 객체·고정 scope epoch에도 결합한다. 이 SHA는 권한 secret/검토자 인증/모델 실행 증거가 아니다. 입력 없음은 고정 미구성 상태로 드러내며 빈 선택/가짜응답/모델 호출로 성공시키지 않는다.

A2 대안인 trusted runtime publisher는 기존 source가 구현될 때만 고려한다. 입력 교체와 generation/준비본 무효화·예산 원자성을 추가로 고정해야 한다. 브라우저가 private context/response를 그대로 전송하는 대안은 더 큰 wire/개인자료 노출·중복 검증 경계가 생긴다. 이번046은 A1으로 고정하며 실제 동적 producer publisher는 후속이다. 이 구분을 새 사용자 승인 질문으로 돌리지 않는다.

## 3. host 옵션·재사용 범위

044의 intake_reference_store/read_scope/session을 그대로 사용한다.046 추가 제안은 **`intake_reference_append_scope=(), intake_reference_review_inputs=()`** 두 keyword다. write scope는044 read scope와 같은 trusted exact `"workspace"` 또는 중복 없는 ASCII150 tuple≤100이고, 기본 빈 tuple이다. append는 read와append scope가 모두 해당 intake를 허용할 때만 가능하다. HTTP 입력은 이 scope를 만들거나 변경할 수 없다. 이미 위임된 host 범위를 재사용하며 동작마다 같은 승인창을 요구하는 계약이 아니다.

None Store/None catalog/입력 없음/빈 scope를 기존 읽기 UI의 실패로 바꾸지 않는다. 구성된 단계의 버튼만 활성화하고 실제 부족 이유를 고정 코드로 표시한다.046 설정은 server 시작에 고정한다. Store/catalog/scope 교체는 새 host/session epoch로 준비본을 폐기한 별도 정상 재시작이며 live 속성 조작이나 자동 reload로 처리하지 않는다.

구성된 host는 승인된042 모듈의 정식 prepare_reference_review/append_reference_review 함수를 startup에 capture한다. body나 임의 instance callback을 실행 대상으로 삼지 않는다. 미구성 경로는 새042 import/retained read 없이 닫는다.044 history/current 함수와 route를 prepare/append로 덮어쓰지 않는다.

044 history GET의 no-store 메타 header에 `X-Intake-Reference-Prepare-Allowed: true|false`, `X-Intake-Reference-Append-Allowed: true|false`, 구성된 경우의 `X-Intake-Reference-Review-Input: <SHA64>`를 확장하는 최소안을 제안한다. 원래 history7 body/HEAD body0·HEAD 새세션0·CSRF cookie/header 정책을 유지한다. header는 UI 안내이고 권한의 원천은 host 고정 설정이다. review input의 raw 값/producer/quote를 싣지 않는다.

## 4. opaque 준비 handle과 예산

준비 성공 때 session 안에 정확 PreparedReferenceReview 객체와 preview11을 보관한다. handle_id는 server가 만든 random32bytes의 hex64이며 preparation_id SHA나 request_id와 구별한다. catalog/Store는 기존 host가 소유/빌린 같은 객체다. private 항목은 아래 결합을 가진다.

- host instance epoch·세션·044의 고정 scope epoch
- borrowed Store 객체와043 수명/DB identity·genuine catalog 객체 동일성
- intake_id·review_input_id·042 preparation_id·expected snapshot/head
- server가 만든 하나의 append_request_id와 원래042 exact6 요청
- monotonic 생성/만료 시각·ready/appending/recorded/uncertain 상태·활성 여부

클라이언트의 다른 Store/catalog/session/scope/intake/expected 값을 채택하지 않는다. publication 전에042가 자기 DB identity/catalog 결합을 다시 검증한다. 별도 parent private attribute/직렬화/해시 복구 API를 만들지 않는다. handle은 cookie+CSRF+scope 확인 없이 사용할 수 없다. URL/query/DOM text/로그/stdout/영속 브라우저 저장·보고서에는 넣지 않고, 요청/응답의 필요한 필드와 메모리 안에서만 사용한다.

**최소 보수 상한 제안:** host의 retained handle3개, session당2개, handle당 private 입력 최대20MiB+관리여유1MiB를 예약해 총63MiB를 넘지 않는다.042 객체의 private bytes를 들여다보는 새 accessor를 요구하지 않는다. 이 값은 retained 준비값의 보수 예약이며 Python 전체 RSS·부모 계산 중 임시 메모리 한도가 아니다. parent의 정상20MiB/각DTO 예산을 축소하지 않는다. context/response 입력 목록32MiB·세션128 메타는 별도 한도이며 source 작업은 동시1이다.

handle은 monotonic 절대900초,044 session idle900초 중 먼저 끝나는 admission을 따른다. 호출/replay/history가 준비의 절대 만료를 연장하지 않는다. 만료/재시작/해제 후는 고정410/부모0이며 원래 private 입력을 history로부터 복구하지 않는다. live·불명 결과의 준비본을 포화 때문에 몰래 LRU eviction하지 않는다. cap은503, 진행 중은429/queue0이다. 이 작은 상한의 비용은 동시 보존 수이며 총괄이 수치를 늘리면 별도 메모리/수용 조건으로 고정한다.

새 명시 prepare의 replace_handle_id가 같은 세션의 ready 또는 recorded 항목이면 교체를 요청할 수 있다. appending/uncertain은409로 닫는다. 교체 중 기존 항목을 잠그고 새 준비가 성공한 뒤 원자 publish/기존값 release, 실패면 원래 항목/lastgood를 보존한다. 교체는 old slot의 용량을 예약하고 부모 임시 값과 retained 용량을 구별한다. 다른 세션 값 교체·자동 만료 연장·새 request로 재등록은 없다. 교체된 옛 handle의 재송신은410이며 원래038 영속 이력은 보존한다.

## 5. 두 POST와 정확 DTO 제안

044의 `/api/intake-references/{intake_id}/history|current`는 변경하지 않는다.046 경로는 같은 prefix의 **`prepare`와 `append`**다. exact ASCII150 ID/fullmatch, query0·alias/percent slash/중복 slash·absolute target/fragment 거절, GET/HEAD405·Allow POST·body0·부모0이다.

prepare body 정확3키:

```text
schema_version, review_input_id, replace_handle_id
```

schema_version은 bool 아닌1, review_input_id는 같은 intake의 구성된 SHA64, replace_handle_id는 null 또는 hex64다. origin/session/scope/입력·교체 상태·용량/busy를 먼저 검증하고 기존044 active/busy를 취득한 뒤042 prepare를1회 호출한다. C1→032→C2 paired 관측을 host가 원자/지속 현재성으로 바꾸지 않는다. source/관측 변경은 부모 고정 오류이며 자동 재준비0이다.

prepare 성공 body 정확6키는 `schema_version,kind,handle_id,append_request_id,expires_in_seconds,preview`다. kind=intake_reference_preparation_handle, expires_in_seconds는 서버가 계산한1..900 정수, preview는042 exact11 그대로다. raw prepared/context/response/receipt/source는 없다. append_request_id는 server가 만든 ASCII150 이내의 고유 ID이며 해당 handle 동안 고정한다. prepared/deferred/부족을 현재성·업무/모델/실물 승인으로 바꾸지 않는다.

append body 정확7키:

```text
schema_version, handle_id, intake_id, request_id, preparation_id,
expected_snapshot_id, expected_head_record_id
```

경로 ID와body ID·handle의 ID가 같아야 한다.042 exact6 요청과 server가 고정한 ID/기대값이 모두 같아야 하며 head=null은 wildcard가 아니다. 세션/현재 scope·유효기간·Store/catalog/scope epoch를 다시 검사한다. 부모042 append를 **1회** 호출하며 원래 준비 객체와 exact6을 그대로 전달한다. head/답변이 달라져도 expected를 재작성하거나 새 request ID를 만들지 않는다.

성공은042 registration10 그대로다. stored/replayed·binding_status5종·append_observation7/verification8과 최초 시각을 보존한다. historical_provided/head_conflict/preparation_unverified/reference_unbound도 저장된 이력의 서로 다른 정상 결과이고 current_at_append로 바꾸지 않는다. ready=false도 참고결합/기록의 의미와 시험 착수 권한을 구별한다.

transport는044의 cookie/CSRF/loopback peer·정확Host/필수Origin·same-origin Fetch 조건을 재사용한다. header 중복/동명cookie 중복·Content-Length1·JSON UTF8·TE/CE/Expect/BOM/중복키/비유한 수/surrogate/trailing data를 닫는다. 작은 요청16KiB/depth8/nodes256·body read5초, prepare envelope64KiB/depth16/nodes10000, registration2MiB/depth20/nodes200000 제안이다. preview32KiB/부모 private예산은 유지한다. JS는044의 SQLite63bit/Number safe lexeme 정책을 재사용한다.

## 6. 재전송·경합·오류·수명

동시1/queue0 source gate를 current/prepare/append/replay가 공유한다. history metadata도 active 호출 수에는 들어가되 source gate를 소비하지 않는다. 같은 handle의 append가 진행 중이면 중복 요청은429이고 부모 재진입0이다. 부모가 끝난 뒤 동일 handle/request로 명시 재송신하면042/038이 원래 append를 검증·replay하며 host가 cache 값에 replayed=true를 덧붙이지 않는다.

timeout/응답 단절/부모 dispatch 뒤 오류는 미저장이라고 단정하지 않는다. appending 상태/자원은 부모 finally가 끝날 때까지 보존하고 결과 불명은 uncertain으로 남긴다. 자동 새ID·재준비·재등록0이다. 동일 원래 handle/request의 명시 재송신과 기존044 metadata history 확인을 제공한다. metadata history만으로 private payload 전체를 재검증했다고 표시하지 않는다. 원래 준비가 만료되면 자동 복구/재제출하지 않고 과거 이력과 명시적인 새 검토 절차를 구별한다.

오류는 기존 `{error:{code}}`다.044 session/access 오류와042/034/032/025/038의 exact class+열거 code를 유지하고 unknown/raw exception/path/SQL/값은 정제한다.046 host prefix `intake_reference_review_host_`의 suffix8 제안은 `unconfigured,invalid_request,input_limit,access_denied,review_input_unavailable,prepared_unavailable,request_conflict,unavailable`다. wire400/413·권한403·binding409·만료410·busy429·미구성/자원/unknown503을 구분한다. prepare/current의 정상 부족/상태와 error를 혼합하지 않는다.

borrowed Store close는046이 소유하지 않는다.044 active 감독을 **history/current/prepare/append/replay 모두**에 적용한다. shutdown은 새 admission 차단→진입한 부모 전부 종료/active0→registry/secret 폐기→host 종료→caller의043 Store.close 순서다. 브라우저 abort/만료/전송 실패가 active0 확인이나 parent finally를 생략하는 근거가 아니다.043 Store.connection의 카운터가034/038 자체 SQLite 연결을 자동 추적한다고 보장하지 않는다. 최초 append의038 전용 DDL8과 기본 업무 schema/DB·폴더 생성0도 구별한다.

## 7. 소유 경계와 실제 버튼까지의 후속

총괄이 공개 최소hook 계약/소유권/exactbase를 고정하면 신규 labflow/intake_reference_review_host.py, tests/test_intake_reference_review_host.py, docs/fcc/intake_reference_review_host_usage.md 정확3파일의 코어 구현·자체검증을 먼저 시작한다. 실제044 A2 host/session 인수는 통합 완료의 선행조건이다. 기존044 create_server keyword 조립·정식함수 capture·exact dispatcher 두 경로·header 확장은 총괄이 공용 소유자에게 명시 배정해야 한다. frontend의 새 prepare/append 형제 패널과 `setContext({intake_id,revision,snapshotGeneration})`, 검토입력ID·허용header 전달도 별도 소유 hook이다. 동시에 같은 ui_server/app/style을 수정하지 않는다.

실제 버튼은 준비preview11·reason9→명시등록→registration10/옛관측 결과를 보여야 한다. 입력/선택/generation 변경·늦은 성공/부족/오류·사용자 취소가 새 선택·초점/lastgood를 덮지 못하게 한다. 등록 뒤 자동 fresh current/모델 호출0이며 필요한 이력 metadata 갱신만044 소유 hook으로 합의한다. host API만 통과한 것을 실제 HTTP/DOM 완료로 세지 않는다.

총괄이 선택된 A/A1·정식 표면·최소hook 계약/소유권·정확043/042 의존과 root023 이후 exactbase/spec/plan을 공개 고정하면 신규3 코어 구현→genuine043/042 직접 API 검증·독립리뷰로 잇는다. 실제044 A2 provider를 인수한 뒤 동일세션/CSRF·active/source 동시1·genuine HTTP→제품버튼/재전송·종료를 통합 검증한다. 사용자 추가 결정/자료 준비를 현재 요구하지 않는다. 실제 고객·모델/실물·원문 권리 검증은 별도 범위이며 전체 시험소 목표를 이 host 단위로 축소하지 않는다.


## 8. 신규3 소유와 정식 Python 표면

아래는 앞으로 구현할 정식 표면이다. 현재 해당046 제품 파일/함수를 만들거나 실행하지 않았다. module/test/usage는 위 정확3이며 Store/042/043/044/공유 host/frontend 변경0이다. arbitrary callback·범용 registry·세션 생성자를 public option으로 추가하지 않는다.

```python
def create_reference_review_actions(
    store, catalog, *, host_epoch, scope_epoch, runtime_lock,
    read_scope=(), append_scope=(), review_inputs=(),
) -> ReferenceReviewActions: ...

class ReferenceReviewActions:
    def capabilities(self, session_binding, intake_id) -> dict: ...
    def prepare(self, session_binding, intake_id, request) -> dict: ...
    def append(self, session_binding, intake_id, request) -> dict: ...
    def discard_session(self, session_binding) -> None: ...
    def close(self) -> None: ...
```

새 fixed 오류 class는 IntakeReferenceReviewHostError(ValueError)다. code/str/args는 `intake_reference_review_host_`+고정8 suffix의 같은 code이며 cause/context=None이다. status는 고정400/403/409/410/413/429/503 중 실제 분류값만 가진다. busy는 unavailable code/status429, 그 밖의 unknown/closed는 unavailable503이다. 부모 고정 class/code는 원 code로 유지하고 HTTP status는 별도 고정표를 적용한다. 원문 오류·SQL/path/값을 반환하지 않는다.

factory는 borrowed exact Store와 genuine catalog,044 host가 이미 만든 host_epoch/scope_epoch와 **같은 runtime RLock 객체**를 받는다. epoch는 내부용 hex64이고 새 세션/권한 token이 아니다. None Store 또는 None catalog·빈 review_inputs는 정상 미구성으로 capabilities를 닫고 부모042 import/call0이다. 명시된 잘못된 설정·중복 intake/잘못된 scope/불일치는 고정오류이며 creating fallback/빈 성공은 없다. read_scope/append_scope는 원래044 의미를 유지하고 review_inputs는 정확 tuple≤100의 exact4 dict다.

startup 사본은 strict plain JSON·Unicode·각 부모 bytes/depth/nodes를 검사한다. 개별 context8MiB/depth24/nodes200000, validated_response320KiB/depth16/nodes60000, canonical 전체 입력 목록32MiB를 유지한다. version/type/ID/기본 shape 검사는 성공 의미를 부풀리지 않고 catalog 재결합은 부모042→032 prepare에서 한다. caller의 입력 원본을 바꾸지 않고 canonical private bytes로 보관한다. canonical은 UTF8/ensure_ascii=false/allow_nan=false/sorted dict keys/compact separators이며 목록 순서/값·case 순서를 보정하지 않는다. review_input_id의 정확5키와 정상 부정/부족 상태는 v1대로다.

session_binding은 **HTTP body가 아닌044 내부 전달값**이며 정확3 `{host_epoch,session_id,scope_epoch}`의 hex64 strings다.044가 자기 table에서 cookie/CSRF·만료·Store/scope 결합을 검증한 세션만 이 값을 생성한다.046은 같은 host/scope epoch와 own-data shape를 대조한다. 이는 같은 process의 악의적 Python을 격리하는 인증 체계가 아니다. 공용 요청에서 session_binding·lock·epoch·부모 callback을 받지 않는다. 코어 단위 검사는 trusted binding3와 실제 RLock을 직접 전달하는 호출 경계다. 정식043/042로 코어 API를 검증하되 실제044 auth/session/source gate/HTTP/DOM을 실행했다고 주장하지 않으며 대체 host/session/가짜provider를 구현하지 않는다.

capabilities의 반환은 정확3 `prepare_allowed,append_allowed,review_input_id`다. 앞2개는 exact bool, input ID는 SHA64|null이다. session_binding=None/미구성/closing이면 false,false,null이며 객체 생성·retained read·042 import0이다. 유효 세션의 prepare는 read scope+구성 입력, append는 read와append scope 교집합으로 판단한다. 준비 상태 ready와 업무 권한을 합치지 않는다. 이 값은044 header adapter만 쓰며 CSRF/세션값은 포함하지 않는다.

prepare는 exact3 요청→envelope6/preview11, append는 exact7 요청→registration10으로 v1의 HTTP DTO와 동일하다. method 반환은 detached plain DTO뿐이다. prepare는 자기 startup copy를 부모042에 넘겨 원래 PreparedReferenceReview를 보관하고 append는 원래 객체/ID/기대값을1회 전달한다. parent 함수를 body나 injected callback으로 바꾸지 않고 구성된 factory가 정식 모듈 함수만 capture한다.

discard_session은 해당 binding의 준비값을 retire하고 None을 반환한다. 비활성 값은 즉시 해제, 진행 값은 finally 뒤 해제하도록 표시한다.044의 session table/cookie/CSRF 자체를 생성/교체/삭제하지 않는다. close는 이 actions 객체의 새 admission을 닫고 활동 중이면 unavailable503으로 알려 자원을 보존한다. active가 끝난 다음 재호출로 input/handle 메모리만 해제하고 None, 반복 close도 None이다. borrowed Store/native pin·기존044 session을 close하지 않는다.

## 9. 044 A2가 제공할 최소 hook — 아직 미구현

044 A1 구성요소/transport2/context3/export는 변경하지 않는다.046이044 세션 대체물을 구현해 A2 완료로 가장하지 않는다. 아래 내부 hook 이름/역할은 개발1/049 backend에 고정하는 최소 계약이며 현재 제품 함수가 아니다.

1. startup 조립:044가 같은 borrowed Store/catalog·read_scope·host/scope epoch·runtime RLock을 factory에 전달한다. 새 append_scope/review_inputs 두 option의 parsing/설정 소유는044 공용 host다.046은 standalone listener/세션/global worker를 만들지 않는다.
2. `_reference_action_binding(session_id) -> binding3`:044가 자기 session/cookie/CSRF/idle/epoch를 검증한 뒤만 내부 사본을 만든다. 외부 body로부터 binding을 구성하지 않고 HEAD는 새 session을 만들지 않는다.
3. `_reference_parent_call(*, source=False) -> contextmanager[None]`:같은044 lock에서 admission/active를 등록하고 source=True면 기존 동시1/queue0 gate를 취득한다. history는 source=False, current/prepare/append/replay는True다. lock은 짧은 metadata 변경 동안만 유지하고 parent I/O 동안 전체 mutex를 잡지 않는다. finally에서 active/source 자원을 반드시 반환한다.
4. auth/wire/header/dispatcher:044가 exact route·loopback/Host/Origin/Fetch·cookie/CSRF·strict body를 먼저 검사하고 binding+lease 안에서046 method를 호출한다. history7/current10 body와 A1 raw_json/read_allowed wrapper를 바꾸지 않는다. 추가 capability header는 app private closure에서만 읽고 prepare envelope의 handle/request도 그 closure에 보관한다. 새 버튼 view에는 preview/만료 안내/등록 결과만 넘긴다.
5. expiry/shutdown:044가 session retire 때 discard_session을 호출하고 종료 admission을 닫아 active0을 확인한 뒤 actions.close→host 종료→caller043 Store.close 순서를 지킨다.034/038의 자체 연결을043 카운터가 추적한다고 가정하지 않는다.

역할은 개발2=신규0463파일/부모 정상 호출·private 준비 상태, 개발1=043 공식 factory/수명 및 별도049 backend의044 A2 서버·session/CSRF/상기 hook, 개발4=현재044 A1 및 후속 frontend/prepare·append 형제 패널, 총괄=정확 의존/base·공유 소유권·통합/회귀다. 직접 다른 담당에게 지시/메시지하지 않고 총괄 한 창구를 유지한다. 공개 최소hook 계약/소유권/exactbase 고정은 신규3 코어 착수 조건이고, 실제049 backend provider 인수는 HTTP/DOM 통합 완료 선행조건이다. root023 게시와 공개046 spec/plan을 포함한 정확 배정 뒤 새046 제품 branch를 시작한다.

## 10. 상태·만료·교체의 정확 전이

입력/handle은 host instance만 소유한다. session은044가 소유한다. 내부 상태는 준비 전 `preparing`, 공개된 `ready`, 부모 등록 중 `appending`, 부모 정상 결과를 받은 `recorded`, dispatch 뒤 결과 불명 `uncertain`, 종료된 `retired`다. 교체는 이전 항목의 `replacing` 표시와 private candidate이며 새 세션/cache가 아니다.

| 진입/사건 | 전이·결과 |
|---|---|
| prepare admission/예약 성공 | preparing, 해당 session/host slot과source gate 예약. 실패 시 새 항목 미공개/예약 반환 |
| 부모prepare 정상 | session/host 유효와 남은기간을 다시 확인한 뒤 ready로 공개. 절대 deadline=예약 생성 monotonic+900, envelope의 양수 남은초는 ceil로1..900 |
| parentprepare가 끝날 때 이미 만료/종료 | candidate retire/예약 반환·만료410/종료503, 준비를 공개하거나 deadline을 새로 늘리지 않음. 유효한 replacement old만 복구 |
| ready/recorded에 명시 replacement | old=replacing·old slot credit, 새 candidate 미공개. 부모 성공 후 원자 publish/drop old, 실패면 유효한 old state 복구 |
| replacement 중 세션/old deadline 종료 | parent를 강제 취소하지 않고 retire_pending. 실패했다고 expired old를 다시 활성화하지 않음; lastgood는 과거 표시만 유지 |
| appending/uncertain 또는 다른 session 교체 | 고정409/403·parent0. cap을 맞추려고 이 값을 evict하지 않음 |
| 유효 ready/recorded/uncertain의 exact append | appending. 원래 준비+request/expected만 부모에1회 전달 |
| 부모append 정상 | recorded. 정상 분류5종/최초 관측/실제 replayed를 그대로 반환, 절대 deadline 연장0 |
| dispatch 뒤 오류/결과 불명 | uncertain. 원래 handle/request 유지·새ID/자동 재준비0, 이후 동일 요청의 명시 재송신만 허용 |
| 같은 handle가 preparing/appending/replacing 중 | 429/queue0·parent 재진입0 |
| 만료/세션 retire/close 중 비활성 값 | retired·메모리 해제, 옛 handle410·parent0 |
| 만료/종료 시 이미 진입한 parent | 참조/예약을 finally까지 보존. admission 만료는 이미 시작한 SQL을 취소/미저장으로 바꾸지 않음 |

recorded는 **부모가 정상 등록 DTO를 반환했다는 상태**다. HTTP 응답 전달 실패는 브라우저의 delivery-unknown이며 server가 이미 확인한 결과를 미저장으로 바꾸지 않는다. handler가 registry에 임의 replayed flag를 쓰지 않고 동일 원래 handle/request를 다시042에 넘긴다. parent 호출 뒤 예외와 전송 단절을 구분한 이 규칙은 응답 실패용 새 public method를 요구하지 않는다.

예약은 host3/session2/21MiB×3=66060288bytes(63MiB)다. replacement의 새 parent 값은 미공개 임시이며 old slot credit으로 retained 수를 늘리지 않는다. transient parent 자료는 각 부모의 고정 상한/source 동시1에서 따로 관측하고 총RSS63MiB를 약속하지 않는다. cap503·busy429·closed503·expired410은 body/code와 함께 고정하며 입력32MiB/session128 한도와 혼합하지 않는다.

## 11. 이번 A1 feasibility probe — 부모 재사용 검증

probe-v1/run-02는 기존 approved042 fixture recipe/025 public build+decode를 재사용하고 046 모듈/HTTP/registry/043/044 A2를 구현하지 않았다. fresh private synthetic Store/접수/PDF 생성·분석은 fixture phase다. public025 외부 build1/decode1 뒤 exact4를 canonical plain 사본으로 만들고 input SHA5를 계산했다. 사전순 dict key 재배치와 caller 원본만의 사후 변경에도 사본/ID가 유지됐다.

그 입력으로 genuine public042 prepare를 **2회** 호출해 preview11/observation4/선택 binding·권한false와 동일 preparation_id를 확인했다. 각 호출의 내부025/032/034/038는 nested counter이며 별도의 top-level046 호출 수로 더하지 않는다. parent API 구간 Store 생성/connection/event/blob 등록·PDF parser/provider/catalogctor0, 실제 retained PDF/context/extraction은 각각6open씩/호출 관측했다. 실제 read byte수는 측정하지 않았다. SQL row/schema/blob/입력과 확인한 physical files는 전후 같고 reference namespace 생성0이다.

run-01은 fixture Store 초기화 중 audit handle 이벤트에 SQL trace를 너무 일찍 설치한 계측 ProgrammingError로 중단됐다.042/025 입력 호출 전 실패이며 원래 script/fixture/trace/pins를 보존했다. parent monkeypatch나 source 수정 없이 초기화된 local connection을 Python trace로 관측하게 probe만 고쳐 run-02로 분리했다. 이 성공은046 제품/HTTP/session/expiry 수용 PASS가 아니며 실제 고객/원문/모델/실물 검증은0이다.

## 미실행 실패 수용 조건24

2026-10-24 Asia/Seoul. [본 설계](#현재-소유권과-단계)에 대한 **미실행** 조건이다. 공개 최소hook 계약/소유권/exactbase 고정 뒤 코어는 trusted binding3/실제 RLock 직접 호출과 genuine043/042로 먼저 검증한다. 실제044 A2 provider 인수는 동일세션 auth/CSRF·active/source gate·HTTP/DOM 통합 완료의 선행조건이다. 승인된 부모 합성 probe는 별도 feasibility이며046 제품/HTTP/registry/브라우저를 실행한 결과가 아니다. 이 표는 PASS 수가 아니다.

| ID | 입력/상태/실패 | 확인할 결과 |
|---|---|---|
| H01 | Store/catalog/검토입력/append scope 미구성 | 단계별고정미구성·기존history/current유지·새Store/catalog/모델/파일생성0 |
| H02 | 실제044 session/CSRF/context 재사용 | 별도listener/cookie/전역registry0·VirtualFleet secret/runtime/파일replay연결0 |
| H03 | trusted025입력사본·같은intake두입력/100초과/32MiB초과·부모한도 | 고정거절/사본불변·startupretained원문/042/DB쓰기0·없는응답꾸미기0 |
| H04 | scope body/header 위조·범위밖·다른세션/cookie/CSRF·Origin/Host/peer 실패 | beforeparent403·원문/SQL쓰기0·원래위임에추가동의창0 |
| H05 | 정상명시prepare | 실제034C1→032→038C2→privatehandle/preview11·reason9·paired표시·부모값보정0 |
| H06 | 준비중snapshot/readiness/원문 변경·부모부족/미지원 | 부모정제결과보존·자동재준비/선택/모델/새request0 |
| H07 | handle의Store/catalog/session/scopeepoch/intake/입력ID/expected불일치 | 부모append0·opaque handle다른세션재사용0·raw값echo0 |
| H08 | handle3/session2/63MiB예약 cap·입력32MiB·session128포화 | 고정503·live/uncertain 자동LRU폐기0·부모정상20MiB축소0 |
| H09 | monotonic900초·session만료/재시작·옛handle | 고정410/부모0·시간/secret회전으로무한연장0·history에서private복구0 |
| H10 | ready/recorded명시교체·교체실패·appending/uncertain/다른세션교체 | 성공후원자교체/실패oldhandle·lastgood유지·busy/불명은고정거절·retained/임시예산분리 |
| H11 | prepare/append GET/HEAD·alias/query/잘못된JSON/header/대형body | exactroute/405body0·한도/정제오류·부모0·원문/secret로그0 |
| H12 | 정상append와head/답변변경·defer/부족 | 042writer1회·CAS/분류5종·기대값/최초시각보존·실행권한승격0 |
| H13 | 동시current/prepare/append·같은handle재송신중 | shared동시1/queue0·중복429·active감독/finally회수·별도gate우회0 |
| H14 | commit뒤응답단절·부모dispatch뒤오류/timeout | 결과불명표시/원래handle+ID보존·자동새ID/재등록0·미저장단정0 |
| H15 | 같은handle/request의명시재전송·다른요청/기대값 | 실제042/038replay 또는고정conflict·host재생flag위조0·새head관측과분리 |
| H16 | 준비/등록중shutdown/만료/browserabort/예외 | 신규admission차단→부모finally/active0→registry폐기→host종료→callerclose·조기Storeclose0 |
| H17 | 정상/변조된envelope6·preview11/registration10·unknowncode/verifytrue | exacttyped검증·권한/모델/평가false·quote/값/producer/privateprepared/secret출력0 |
| H18 | 선택/generation/편집뒤늦은응답·lastgood/초점·seq안전정수밖 | 새로운선택덮기/반올림/implicitnull0·등록후자동freshcurrent0·실제DOM검증 |
| H19 | 최초명시append의DDL8·history/read/replay·SQLite보조파일 | 전용namespace만허용·기본schema/DB/폴더생성0·retainedread/sidecar분리관측 |
| H20 | 합성genuine025입력→043→실제HTTP→042prepare/append→제품버튼 | source/입력불변·이력/재전송·자원회수·독립리뷰까지확인; 실고객/새실제원문/모델/실물0 |

fixture의 생성/분석·025 응답 decode와046 API 내부 I/O를 분리한다. 042 owner37/394/API11·독립394/API22 및044/043의 과거/정적 결과를046 실행으로 합산하지 않는다. 원래실패/수정전source/계약버전·raw검증과 DB/원본전후 상태를 보존하고 아직 제공되지 않은 production DB를 첫 소프트웨어 인수의 선행조건으로 요구하지 않는다.


| ID | v2 정식 표면/상태 추가 조건 | 확인할 결과 |
|---|---|---|
| H21 | factory/정확class5 methods·capabilities3·오류8/status | callback/새세션주입0·정확반환/기본scope·입력사본/ID·고정오류 |
| H22 | 실제044 binding3/같은RLock·parent lease/sourcegate | 공용auth/admission/active가유일근거·prepared를fake044host로검증완료주장0 |
| H23 | replacement실패와동시에deadline/session종료·close | 유효old만복구·expired재활성화0·retire_pending과finally후해제·retained/임시예약분리 |
| H24 | 부모recorded뒤전송실패 대dispatch뒤예외 | server확인결과/클라이언트불명구분·원래handle/request재송신·새ID/가짜replayed0 |

이 추가4항목도 미실행이다. 이번 허용된 probe의025 외부2call/042prepare2call 및 nested counters는 parent feasibility로만 기록하고 H01~H24 제품 PASS 수에 넣지 않는다. 원래 run-01 계측 실패와 run-02의 SQL·source 전후핀·합성 입력/관측을 보존한다. 실제044 A2가 없다는 사실을 fake host/session으로 대체하지 않는다.


착수순서 I1 정정의 검증 분리: 위24조건의 코어 부분(factory/입력·ID·binding/handle·상한·절대expiry·교체·부모prepare/append/replay·코어close/정제DTO)은 직접 호출 단위로 먼저 실행할 수 있다. H02/H04/H11/H18/H20/H22와 H08의실제session128/H09의idle900/H13의current교차sourcegate/H14·H24의전송실패/H16의실제host종료 등044 의존 부분은 provider 인수 뒤 통합에서 실행한다. 혼합 항목은 관측한 부분만 계수하며 단위 검사의 trusted binding을 실제044 auth/session 검증으로 올리지 않는다. 대체host/session/가짜provider·공유파일 수정0과 현재 제품branch 미생성을 유지한다.
