# 접수 참고이력 메인화면050 설계

2026-10-24 Asia/Seoul. 총괄은044 A2 frontend 후속을 **050**으로 식별한다. 기존044 A1 model/view/test·원설계31775B/계획3594B를 보존하며 개발4는 아래 정확7파일만 맡는다. root025 기능43b04ae41945550723f5ca0e83698a7de3001953에 A1을 인수했다. [049 서버 설계](2026-10-24-intake-reference-http-host-design.md)·[계획](../plans/2026-10-24-intake-reference-http-host.md)와 이 공개 계약/계획을 포함한 정확 root025 게시 SHA로 F1을 실제 배정한다.

F1은 frontend core/wire-fixture DOM 구현·독립 소유 게시부터 진행한다. 실제049 제품 완료를 코어 착수 게이트로 요구하지 않는다. **제품 root app 통합은049 인수·정적3의 실제 제공 후** 하며 먼저 통합해 기존 접수 화면을404로 깨뜨리지 않는다. F2는 인수된049+F1 exactbase의 genuine043/042→HTTP→DOM을 별도 실제 배정/실행한다. 빈 integrated 성공 모드는 만들지 않는다. 준비/등록046 화면은 다음 단위다.

아래의049 private v1 관측/미배정/A1 인수예정 문장은 원계획 작성시점 이력이다. 현재 고정 인터페이스는 위049 공개 최종 v3이며 accepted A1은root025에 포함된다. 내부binding/lock/secret은서버소유다. transport 자체의 local invalid input은 기존 `intake_reference_ui_invalid_request`, 잘못된 wire/UTF8/timeout/unknown은 `intake_reference_ui_unavailable`로 정제하고 서버응답은049 고정 exact code만 허용한다. raw 예외/body/secret은표시하지않는다. 이 최소코드선택은A1의고정unrepresentable 구분/다른오류일반표시를바꾸지않는다.

현재 모든050 구현/수용은 미실행이다. [구현 계획](../plans/2026-10-24-intake-reference-frontend.md)의F1부터 진행하고 고객원문/실제모델/장비·현장 실행이나 추가동의창을 만들지 않는다.

> 실행 담당은 고정 계약 인수 후 `superpowers:executing-plans`로 진행한다. 지금은 private 계획이며 제품 변경·새 branch·API/DB/HTTP 실행0이다. A1 독립 지적이 오면 먼저 같은 소유5에서 수정한다.

2026-10-24 Asia/Seoul. **Goal:** 인수된 A1을 기존 접수 화면에 연결하여 동일049 서버의 history/current를 실제 HTTP→정식043/042/038/034→DOM으로 확인한다. **Architecture:** frontend는049를 소비하며 세션/Store/provider를 만들지 않는다. 같은 서버의046 최소hook은 backend 내부에 남고 prepare/append 화면은 후속으로 분리한다. **Tech stack:** 기존 ESM/native fetch·AbortController·Node test·Playwright, 기존 Python genuine 합성 fixture와 정식049 server. 외부 모델/실고객/장비0이다.

**Spec/source:**044 공개 고정 설계·계획/A1 `38e0e1b4f8073a52891db31341064cceb6f0e4ec`, root의046 공개 host 설계/계획, D1의049 private v1 `9331B/78b66232b8b5c2f47707fbf4c04d216d3b8f500c44063824f9f24f854be7f2ad`를 읽었다.049 v1은 아직 인수된 제품 계약/구현이 아니다. 리드는 A1 독립 최종Yes C0/I0(보고 SHA `1028bb0ef8d27c5b69dadb70232242dace5961c99fe3aebd8f9dce424fff0569`)를 확인했고 다음 cut 인수 예정이라고 전달했다.현재 A1 branch/원본/실패/핀을 재작성하지 않는다.

**단계:** F1 frontend core는 리드가 인수한 A1의 exact base·고정049 interface·공개 A2 spec/plan/소유권으로 먼저 구현할 수 있다.049 실제 제품 완료를 새 착수 조건으로 요구하지 않는다. F1은 단위 wire fixture/명시 frontend harness이며 genuine049 완료가 아니다. F2 실제 HTTP 통합은 인수049+043/042와F1을 합친 exact base에서 별도 배정한다.새 app을 제품 root cut에 조립할 때는 static3이 실제 제공돼야 하며 F1 harness 통과로 그 공백을 숨기지 않는다.

## 정확 소유 후보7

| 경로 | 변경/책임 |
|---|---|
| `frontend/app.js` | A1 mount·검증된 context3·main pending/세대와 transport lifecycle 조립 |
| `frontend/index.html` | 기존 intake-view 뒤/notification-view 앞에 `div#intake-reference-panel` mount 하나 |
| `frontend/styles.css` | `.intake-reference-review` 아래만 제품 스타일·390/1440·stale/초점·기존 화면 회귀 |
| **신규** `frontend/intake_references/transport.mjs` | same-origin 실제 history/current·bounded fatal UTF8·private CSRF·고정 오류 |
| **신규** `frontend/intake_references/transport.test.mjs` | wire/상태/취소·secret 세대의 독립 단위 검사; fake wire는 제품HTTP 수용과 분리 |
| `frontend/intake_references/browser_check.cjs` | 무인자 A1 trusted 경로 유지, F1 `--mode frontend` wire-fixture DOM과 F2 `--mode integrated` 실제049/DOM 분리 |
| `docs/fcc/intake_reference_ui_usage.md` | A1/A2 실행법·실행/미실행·새 증거/한계와 CSS/실제HTTP 차이 |

A1 model/view/model.test 및 backend049 exact3·043/042/038/034·039/024/033은 변경하지 않는 안이다. A1 지적 수정은 별도 우선 delta다. 후보7은 배정 전 제안이며 여덟 번째 파일·백엔드 수정·CSP 완화/Node reverse proxy를 추가하지 않는다.

## 공유 연결 선행조건 — 리드/D1 소유

관측 당시 `ui_server._ASSETS`의 연결 공백을 리드가 수용해 다음3 GET/HEAD·JS MIME·경로 allowlist를049 동일 backend 소유3 안에 추가하도록 실제 지시했다.**None에서도 존재하는 정적 파일은 제공**하며042 import/Store 생성0이다.미존재는404이며 빈 module/가짜 성공으로 대체하지 않는다. model/view는 accepted A1 cut 뒤, transport는 F1 구현 뒤 각각 genuine asset 제공을 검증한다.이 실제 제공 phase는 backend core의 선행조건이 아니다.

| HTTP asset | 고정 파일 |
|---|---|
| `/intake-references/model.mjs` | `frontend/intake_references/model.mjs` |
| `/intake-references/view.mjs` | `frontend/intake_references/view.mjs` |
| `/intake-references/transport.mjs` | `frontend/intake_references/transport.mjs` |

기존 CSP의 script/style/connect self로 충분하다.049 v1의 keyword2 `intake_reference_store=None,intake_reference_read_scope=()`·GET/HEAD history/POST current·header/session128/idle900·scope/Origin·source1/queue0·정제오류·configured drain을 프런트엔드가 대체하지 않는다.최종049 공개 계약의 원바이트/경로/header/오류를 인수해 아래 명칭과 대조한다.

046의 `_reference_action_binding(session_id)`와 `_reference_parent_call(*,source=False)`는 **호출하지 않는다**. binding3/host·scope epoch/RLock/active/registry는 backend 내부다.현재 POST는 서버의 동일 source lease를 통과하고 future prepare/append/replay도 같은 lease를 사용한다.브라우저 abort를 parent 종료로 해석하지 않는다.실제 `server_close()`의 admission 차단→active0/worker·socket 회수→반환 뒤 caller043 close를 사용한다.

## Global constraints / 정확 frontend 표면

- A1의 model 상수1/함수4·view1/반환5·context3·transport2를 유지한다.새 transport의 공개 제안은 **`createIntakeReferenceTransport()` 한 함수**, 반환은 `{readHistory,readCurrent,setContext,setPending,destroy}`다.생성 시 I/O0이며 임의 origin/fetch/host/session 주입 option은 없다.
- app이 view에 넘기는 options는 **`{readHistory:transport.readHistory,readCurrent:transport.readCurrent}` 두 키만**이다. transport 객체 전체를 spread하지 않는다. readHistory는 raw_json/read_allowed, readCurrent는 raw current JSON만 반환하며 secret/epoch/handle을 추가하지 않는다.
- context는 null 또는 검증된 `{intake_id,revision,snapshotGeneration}`. A1 검증 함수를 재사용한다. 같은 유효 non-null context3를 전달한 `setContext`는 no-op으로 private token/요청 세대를 보존한다. 실제 context 변경·null/invalid 또는 `setPending(true)`는 private 요청 epoch·secret을 먼저 무효화한다.잘못된 입력은 active/queued/secret을 닫고 고정오류·fetch0이다. destroy는 terminal/멱등·자기 요청 취소/참조 해제만 수행한다.
- 실제 fetch는 동일 origin의 상대 경로·credentials same-origin/cache no-store/redirect error다. Origin/Host/Cookie/Fetch header를 수동 위조하지 않는다. 다른 origin·localhost alias·독립 listener로 우회하지 않는다.세션 cookie는049만 설정하며 HttpOnly 값을 JS로 복사하지 않는다.
- CSRF는 private closure 하나다. history response의 `X-Intake-Reference-Read-Allowed`는 정확 true/false, true 때 `X-Intake-Reference-CSRF`는 최종049의 exact token 형식이 있어야 한다. false면 token을 지운다.누락/모순 header를 true/빈 값으로 고치지 않는다.
- history header 저장은 signal not aborted·현재 context/epoch·해당 최신 history ticket일 때만 한다. current 오류는 자신이 사용한 token 세대가 아직 같을 때만 cache를 지운다.늦은 header/403이 새 선택의 token을 덮거나 지우지 않는다.권한은 서버 scope가 최종 판정하며 UI bool/기존 위임을 새로 발급하지 않는다.
- query는 검증된 limit1..100·before_seq null|positive safeint. null cursor는 URL에서 생략한다. current body는 정확 `{schema_version:1,action:"current"}`다. main revision/generation·permission·세션/binding을 body에 넣지 않는다.
- response는 headers+stream으로2MiB를 넘기기 전에 중단하고 wire BOM을 먼저 거절한 뒤 **fatal UTF8 decode**한다. `.text()` replacement decode/`.json()` Number 반올림을 쓰지 않는다. DTO typed parse는 A1 소유다. non2xx는 exact 오류 envelope/열거 code만 정제하고 raw body/exception/statusText/path를 출력하지 않는다. timeout35초·context 취소·만료 뒤 source POST 자동 재전송0이다.
- secret은 view/DOM·URL/hash/history·storage·console/receipt로 내보내지 않는다. 세션 재조회 안내는 app/index의 고정문구로 제공하며 A1의 오류·lastgood·표시를 바꾸지 않는다. 연결이 만료되면 이력을 새로 조회한 뒤 현재 상태를 명시 조회하도록 안내하고 자동 current retry/새 권한 요청은 하지 않는다.

## Review focus5

1. 이전 history 응답/이전 current의403이 새 context의 private CSRF 상태를 훼손하지 않아야 한다.
2. 늦은 main refresh finally와 invalid/queued context가 새 pending을 풀거나 옛 metadata를 부활시키지 않아야 한다.
3. UTF8/BOM·2MiB 초과·unsafe seq와 unknown error가 lastgood를 버리거나 비공개 문자열을 표시하지 않아야 한다.
4. None·정적파일3·권한false에서 기존 접수/fixture 화면은 사용 가능하고 source current는0이어야 한다.
5. page 폐기·BFcache·취소·host 종료가 parent 성공/실패를 꾸미거나 borrowed Store를 조기 close하지 않아야 한다.

## F1 Task 1 — 실제 frontend transport core (신규2)

**Consumes:**최종049 두 경로/header/오류·A1 validate context/gate. **Produces:** 위 factory와 raw2 경계. 제품 header·session 대체물/재생 API는 없다.

- [ ] 먼저 `transport.test.mjs`에 native fetch 경계의 `same_origin_exact_paths_and_body`, `strict_header_false_and_missing_csrf`, `fatal_utf8_bom_stream_cap`, `late_history_cannot_publish_secret`, `old403_cannot_clear_new_token`, `context_pending_destroy_abort_without_retry`를 작성한다. 실패 응답은 전체 wire fixture이며 mocked wire 검사를 genuine049 수용으로 세지 않는다.
- [ ] `node --test frontend/intake_references/transport.test.mjs`에서 모듈 부재/실제 behavior RED와 입력·실패를 보존한다.
- [ ] factory를 구현한다. 임의 callback option 없이 native fetch를 쓰고 자기 AbortController/35초 deadline을 caller signal과 결합한다. context epoch/history ticket/token version은 private이며 위 갱신 조건을 적용한다.단위 검사는 테스트 환경의 native fetch 경계만 관찰/대체하고 production API에 test-only 주입구를 추가하지 않는다.
- [ ] 같은 명령의 GREEN·무관련 Node186 기준선을 새 실행과 구분하고 소유 delta를 커밋한다.단위 통과를 HTTP/Store 성공으로 부르지 않는다.

## F1 Task 2 — app 조립·정식 제품 CSS (기존3)

**Consumes:** 인수 A1 view/model + Task1 transport. **Produces:** 기존 intake 화면의 별도 형제 패널과 정확 선택/pending 전달.

- [ ] 실제 product-page 검사에 `none_assets_keep_intake_UI`, `main_refresh_before_fetch_cancels_both`, `latest_finally_only`, `prepare_before_publish_context`, `filter_same_context_no_extra_history`, `context_change_history1_current0`, `invalid_context_no_resume`, `outside_focus_and390_layout`를 RED로 고정한다.
- [ ] F1은 제품 app/index/styles를 읽는 static harness와 명시 wire fixture로 이 브라우저 사례를 구현한다. 실제049 session/cookie/Store/provider를 흉내내는 host는 만들지 않는다.단위/fixture 응답을 실제backend HTTP·source read로 계수하지 않는다.정적경로의 실제049 제공은F2에서다시확인한다.
- [ ] index에 mount div 하나를 intake-view 뒤/notification-view 앞에 둔다. detail-panel replaceChildren에 mount를 포함하지 않는다. `changeView`는 mount 표시만 기존 intakes/notifications와 맞추고 현재 조회를 실행하지 않는다.
- [ ] app module에서 transport/view 각1개를 만든다. `prepareView`가 선택 fallback 뒤 referenceContext를 검증해 준비 값으로 만들고 DOM/state 동시 게시 전에 실패를 확인한다. `publishView`의 기존 fixture hook은 보존하며 `transport.setContext(ctx)`→`panel.setContext(ctx)`로 전달한다. DOM 스크랩/CSRF 전달0이다.
- [ ] `refresh()`의 새 request 시작/기존 fetch 전 `transport.setPending(true)`→`panel.setPending(true)`를 호출한다. 최신 `request===state.request`인 finally에서만 transport false→panel false로 해제한다.실패한 목록 응답으로 새 context를 만들지 않는다. pending 중 검증된 새 선택은 A1 규칙대로 metadata만 최대1회다.
- [ ] non-persisted pagehide는 둘을 destroy한다. persisted pagehide는 pending true/secret 무효화만 하고 pageshow 복귀 시 기존 main refresh로 metadata를 새로 읽는다. source current 자동 실행은0이며 기존 fixture/알림 기능을 바꾸지 않는다.
- [ ] CSS는 root selector 아래 기본 light tokens·controls wrap·긴 ID/시각 줄바꿈·stale text/색·2열/모바일1열만 추가한다. harness CSS나 inline style/CSP 완화로 제품 스타일을 대신하지 않는다. GREEN/390·1440 screenshot·원래 화면/초점 회귀 뒤 소유 delta를 커밋한다.

## F1/F2 Task 3 — checker/usage와 genuine049→제품 DOM (기존2)

**Consumes:** 인수049·043/042/038/034와 Task1/2. **Produces:** A1과 분리한 실제 제품 HTTP phase의 새 영수증.

- [ ] 기존 무인자 checker의 A1 trusted 경로를 그대로 유지한다. F1의 `--mode frontend`는 명시 wire-fixture DOM, F2의 `--mode integrated`는 아래 genuine049 경로다. unknown/override URL·callback·PDF·secret CLI 입력은 거절한다.새 client/source 입력은 요구하지 않는다.
- [ ] integrated 경로는 새 private 합성 workspace를 준비하고 생성/분석/GEN·025/038 namespace 단계와 API read 단계를 분리한다. 정식043 exact Store→049 create_server를 사용한다. Node static proxy/가짜 Store/가짜 provider·원래 result JSON 재생은 제품 수용에 쓰지 않는다.
- [ ] 실제 제품 `/`가 static3+app을 로드한다. 첫 history GET→042→038→A1 DOM·source0, 명시 current POST1→042→038/034→A1 DOM·retained PDF/context/extraction read>0·재파싱/OCR/render0을 관찰한다. prepare/append/모델/장비0이다.
- [ ] 별도 negative-wire 단위/명시 fault-injection은 genuine HTTP 정상 phase와 계수/입력을 분리한다. None/권한false·잘못된응답·세대/취소·old lastgood·session 만료/재시작 안내·unsafe 정수·KST·키보드/390·1440을 확인한다.현재 body2/actual header는 전송하지만 기록에는 token/cookie value/hash를 남기지 않는다.
- [ ] browser 종료 뒤049의 configured drain/worker 종료를 기다려 server_close가 반환한 다음 caller가043 Store를 닫는다. row/schema/provenance/retained 원본·SQLite sidecar·자원·실패를 보존하며 parent I/O를 강제 중단했다고 주장하지 않는다.
- [ ] 전용 transport/전체Node·A1 trusted/기존 intake-fixture 및 조회·계산 회귀·정적/UTF8/링크/문서 검사를 실행한다. backend 전체 회귀 실행/미실행은 리드의 통합과 분리한다. 정확 소유7 commit/push/remote·새 입력/phase/핀으로 독립 리뷰에 인계한다.사용법에 A1/A2 실제 수와 미실행을 구분한다.

F1의 구현/독립 소유 게시와F2의genuine 통합 수용을 서로 기다리게 하지 않는다.F1 게시 때 integrated mode는미실행이며빈성공모드로추가하지않는다.F2 배정 때 같은checker의구현을확장하고accepted backend/asset cut으로새실행한다.

## 046 준비·등록은 별도 후속

첫 A2는046 입력/registry를 요구하지 않는다.046 core/provider와049 동일세션 attach를 인수한 뒤만 별도 spec/base/파일 소유를 정한다. capability header는 app private closure에만 읽고 binding3/CSRF/handle/request는 view로 내보내지 않는다. 준비 preview11/reason9와 명시 append registration10의 별도 sibling view/새 API를 이후에 정한다.A1 history/current raw2/context3/export를 확장하거나 준비/등록을 자동 실행하지 않는다. append 뒤에도 metadata 이력만 갱신하고 fresh current는 명시 동작으로 남긴다.

현재 이 계획의 모든 검사/구현은 미실행이다.A1 `38e0e1b`/Node186·typed30·trustedDOM18과독립검사(리드보고 typed추가12/DOM추가5)는이전의서로다른실행으로보존한다.production DB/PDF·반복위임을새착수준비물로요구하지않는다.049 exactstatic3/내부세션소유와공개interface·accepted A1base를리드가고정하면F1부터시작하고실제HTTP수용은F2로분리한다.
