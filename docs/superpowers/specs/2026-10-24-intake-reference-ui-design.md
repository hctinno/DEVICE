# 접수 참고 이력·명시 현재 조회044 — A1/A2 고정 설계

2026-10-24 Asia/Seoul. 총괄은 A(정제 history7·명시 fresh current10 형제 패널)를 선택하고 A1 신규5 구성요소→A2 기존5 host/app 연결로 나눈다. 준비/등록 버튼·registry·모델 실행은 다음046의 별도 계약이다. [구현 계획](../plans/2026-10-24-intake-reference-ui.md)을 따른다. 사용자 준비/반복 승인 질문0이다.

아래 원제안의 선택대기·제안·미구현 문구는 작성 당시 기록이다. 이 설계는 v3(view/transport/context/A1 분할)→v2(ID literal/borrowed 수명/U18)→v1(정식 HTTP·권한/상한/표시 의미) 순으로 고정한다. 독립 v1 Yes dad9569dd85a61eb9f2b7b730f5be6c1f64dbf442598267cc82410cadf40194b, v2 Yes251e4edc9082fd3c063d93bc49344bab454941bb2d5c3fe54d438ccd300721cc와 v3/공개 builder의 최종 검토를 별도로 보존한다.

A1은 실제 Store/API를 호출하지 않는 합성 trusted transport DOM이다. A1에서 Store/042/043가 구현됐다고 가장하지 않는다. 공개 model 상수1/함수4·view export1/반환5·transport2·context3과 예산은 v3 그대로다. `setPending`은 primitive boolean만 받는다. model은 고정 Error를 던지고 view setter의 잘못된 입력은 두 ticket/허용을 닫아 고정 화면 오류·transport0·lastgood 보존으로 처리한다. A1 raw string은 유효 Unicode/JSON·UTF8 인코딩 예산을 검증한다. A2는 실제 wire를 fatal UTF8 decode한 뒤 raw string을 전달해야 하며 JS string만 보고 원래 wire bytes를 검증했다고 주장하지 않는다.

A1 소유는 신규 `frontend/intake_references/model.mjs`, `view.mjs`, `model.test.mjs`, `browser_check.cjs`, `docs/fcc/intake_reference_ui_usage.md` 정확5다. 기존 host/app/styles·부모·039/024/033 변경0이다. 기존 stylesheet를 읽기 참조하고 A1 수용 CSS/정적 harness와 최종 제품 style/CSP를 구별한다. 여섯 번째 제품 파일이나 CSP 완화를 임의 추가하지 않는다. A2는 기존5 파일과 필요한 A1 checker 확장의 정확 소유권을 별도 고정한 뒤 구현하며, A1 완료를 A2/전체접수 완료로 올리지 않는다.

잘못된 context는 active/queued context를 모두 null로 닫고 pending 중 새-context 표식도 지운다. 이후 `setPending(false)`가 옛 context의 자동 metadata 조회를 되살리지 않는다. 원래 lastgood는 그 context의 과거 결과로만 보존하며 새 선택의 성공으로 표시하지 않는다. 이 fail-closed 전이는 v3의 원래 invalid context/transport0 의미를 구체화한 최종 선택이다.

A2의 정식043 exact Store factory·borrowed 수명과 인수042 API·038/034를 사용한다. 기존 loose calculation Origin 처리를 source POST에 그대로 재사용하지 않는다. trusted scope/엄격 Origin·Host/loopback/세션128·idle900초/CSRF·동시current1/queue0·고정 wire/의미 예산을 지킨다. 이력은 metadata이고 현재는 retained PDF/context/extraction을 실제 읽는다. 페이지 진입·선택·이력 갱신의 current0과 명시 버튼만의 source read를 구별한다. 첫 제품 수용은 genuine 합성 접수→정식043/042→HTTP→DOM이며 production DB/PDF를 새 착수 준비물로 요구하지 않는다. 실제 고객/모델/장비/현장·현재규범 검증은 미실행이다.

## 승인 원제안 v1 — HTTP와 표시 의미

2026-10-24 Asia/Seoul. 개발4의 **리드 선택용 계약**이다.044 구현·새 branch·HTTP/Store/공유 파일 변경·DB 연결·보존 원문 읽기·모델/장비 실행은0이다.039 I1 수정은 별도 `8e804c32936371de7ce1f7f90bdfe1fd0a309aea`로 게시했고 독립 재검토가 우선이다. root020에039가 포함됐다고 가정하지 않는다.

## 1. 첫 범위와 의존

접수 운영 화면에 **참고 이력 / 현재 조회 결과** 형제 패널을 연결한다.042의 정제 history7과 current10만 사용한다. preview는 준비 reason9종을 포함한 정확11이며 준비/등록 화면은 다음 단위로 미룬다. 첫044에는 prepared registry·prepare/append 경로·request ID 생성·모델 실행·새 catalog 생성이 없다. 사용자 화면까지 연결한 실제 HTTP→042→038/034→DOM 검증이 완료 기준이며 Python 호출만으로 대체하지 않는다.

선행은 최종 인수된038·042와043, 총괄이 게시한044 spec/plan·정확 base다.042 소유 작업 파일의 존재는 독립 최종Yes가 아니다.043의 현재 D1 제안은 `Store.open_existing(root)`/명시 close·수명 pin·인식 schema profile이며 **미확정**이다.043의 최종 API·지원 DB profile/WAL·오류·수명 계약에 맞춘 뒤 시작한다. 기존 Store 생성자·ro proxy·subclass·호출자 `__new__`/속성 조립으로 대체하지 않는다.043 자체의 정식 객체 생성 방법은 D1 소유다.

## 2. 화면과 부모 의미

- 목록의 검증된 선택을 받으면 정제 이력을 읽는다. 새 현재 조회는 **‘현재 상태 조회’ 버튼 한 번**에만 실행한다. 페이지 진입·목록 검색·접수 선택·주기 갱신·이력 페이지 이동에서 fresh current/retained source read/prepare/append는0이다.
- 버튼은 ‘접수 보존자료의 무결성을 새로 확인합니다’라고 설명한다. 이미 위임된 workspace/접수 읽기 범위를 재사용한다. 같은 허용을 재확인하는 동의창은 없고 실제 미구성·범위 밖·만료·자료 오류만 표시한다.
- history의 `binding_status=current_at_append`는 **‘등록 당시 일치’**다. `created_at`, `append_observation.observed_at`과 fresh `current_observation.observed_at`을 별도 표기한다. ‘현재’는 해당 관측 시점의 결과이며 지속 현재성/원자 head+snapshot을 약속하지 않는다.
- history `available=false`는 등록 이력 미가용이다. source 상태/현재 조회의 가용성과 합치지 않는다. current의 `unavailable/none/current/stale`는 정상200 DTO의 서로 다른 상태이며 stale/unavailable의 검증된 old head는 ‘이전 등록’으로만 남긴다.
- ID·revision·등록/관측 시각·binding 상태·정제 reference_summary의 case IDs/개수·reason·source_modes·검증 flags만 표시한다.0/false/null, nullable catalog와 합성/실자료 출처를 보존한다. 원문 값·quote·private receipt·모델 응답·파일 경로·raw JSON 다운로드는 없다. authority/model/evaluation false를 true로 승격하지 않으며 기존 업무 위임 취소로도 해석하지 않는다.

## 3. 최소 HTTP 선택 — 두 경로 권고

| 안 | 접점 | 대가 |
|---|---|---|
| **A 권고** | history GET + current POST. history 응답 header로 읽기 가능 여부·세션 CSRF 전달 | 원래 history7/current10을 그대로 유지하고 별도 session JSON/세 번째 경로가 필요 없다 |
| B | 별도 GET session + history GET + current POST | session DTO·경로·만료 상태 관리가 하나 더 생긴다. 준비/등록을 같은 단위에 넣을 때 재검토할 수 있다 |

제안 경로는 `/api/intake-references/{intake_id}/history`와 `/api/intake-references/{intake_id}/current`다. 기존 `/api/intakes/{id}`·039 계산 POST·040 S0를 건드리지 않는다. exact ASCII150 ID만 받으며 인코딩 alias·중복 slash·absolute target·fragment는 거절한다.

- history는 GET/HEAD만 허용한다. query는 `limit` 기본20/1..100, `before_seq` 기본null/정규 양의 십진수 SQLite63bit만 각1개다. 서버가 정확4키 `{schema_version:1,action:"history",limit,before_seq}`를 구성한다. HEAD는 body0이고 새 세션을 만들지 않는다.
- current는 POST만 허용한다. query0, JSON body는 정확2키 `{schema_version:1,action:"current"}`다. GET/HEAD는405·Allow POST·HEAD body0, 부모/원문 읽기0이다. 경로/flag/token/SQL/callback을 body에 추가하지 않는다.
- 성공 body는042 history7/current10 원형이다. `available=false`, none/stale/unavailable을 transport 실패나 빈 성공으로 재분류하지 않는다. history의 record11/append_observation7, current의 record11/reference_summary5/current_observation4/verification6을 정확 검증한다. preview11·registration·전체 receipt를 이 경로에 섞지 않는다.

## 4. trusted startup·세션·CSRF

044가 추가할 keyword **제안**은 기존 인자를 보존한 `intake_reference_store=None, intake_reference_read_scope=()`다. Store는043으로 정식 연 기존 exact Store를 caller가 주입한다. 주입 Store와 조회 workspace의 root/db가 일치해야 한다. `None`은 reference 미구성이며042/034/038의 새 import/call·Store 생성0, 기존 UI는 그대로 시작한다. configured 때만 정식042 `read_reference_review`를 capture한다. 이 첫 범위에는 genuine catalog 주입이 필요 없다.

scope는 trusted Python 값만 받는다: 기본 빈 tuple은 retained-read 불가, 정확 문자열 `"workspace"`는 그 workspace 전체에 대한 기존 위임, 비어 있지 않은 정확 tuple은 중복 없는 ASCII150 접수 IDs(제안 상한100)다. workspace 전체 위임을 접수마다 다시 입력하게 하지 않는다. HTTP body/header/URL이 이 값을 설정하지 못한다. current 때마다 membership을 확인해 exact bool `allow_retained_reads`로042에 전달한다. metadata history는 그 flag 없이 가능하다. appendix/write/운전·모델 권한은 만들지 않는다.

history GET은 no-store header `X-Intake-Reference-Read-Allowed: true|false`를 보낸다. 허용된 세션에서는 `X-Intake-Reference-CSRF`도 보낸다. 이 header는 UI 표시/CSRF 전달이며 read 권한의 원천이 아니다. 첫 정상 history GET에서만 runtime session을 만들고, 정상 후속 GET마다 token을 회전시키지 않는다. 브라우저의 쿠키 차단/세션 만료는 고정 실패이며 source POST 자동 재시도0이다.

제안 세션은 host 메모리 최대128개/idle900초, server 생성 session ID와 CSRF 각각32 random bytes의 opaque hex다. cookie 이름은 `dgm_intake_reference_<실제port>`, 속성은 `HttpOnly; SameSite=Strict; Path=/api/intake-references/; Max-Age=900`이며 HTTP loopback 조건에 맞춘다. 세션은 host instance·Store identity·고정 grant scope에 묶인다. 만료된 항목만 정리하고 포화는 고정 미가용으로 닫는다. 브라우저 영속 저장·URL/history·로그/stdout·receipt에 secret을 남기지 않는다. 세션은 사용자 신원 인증이나 새 위임 증거가 아니다.

source POST는 **127.0.0.1 bind + loopback peer + 정확 Host + 필수 `Origin=http://Host` + present Sec-Fetch-Site=same-origin + 유효 session cookie + 해당 token의 custom header**를 모두 확인한 뒤 부모를 호출한다. missing/null/다른 Origin, 범위 밖·CSRF 누락/불일치는403/부모0/원문0이다. 필수 header와 동명 session cookie의 중복도 거절한다. GET의 Origin은 있으면 동일 origin을 요구하고 cross-site fetch를 거절한다. CORS/simple form/query token 예외는 없다. caller는 server shutdown·활성 요청 종료 후 주입 Store를 close한다.044가 빌린 Store의 수명을 임의 종료하지 않는다.

## 5. 한도·오류·표현

current wire16KiB/strict UTF8·BOM/중복 key/비유한 수/surrogate/trailing data 거절, 의미 depth8/nodes256을 제안한다. Content-Length 하나·JSON charset=utf-8만 허용하고 TE/CE/중복 length/Expect를 닫는다. body read5초·새 경로 target1024B, response raw/의미2MiB/depth20/nodes200000이다. 부모의 private snapshot/context/response/receipt 예산은 줄이지 않는다.

fresh current는 host당 동시1개/queue0을 제안한다. busy는429, client timeout35초·사용자 취소/화면 세대 변경 뒤 자동 재전송0이다. 브라우저 abort가 이미 시작된 부모 retained read를 즉시 멈춘다고 주장하지 않는다. 진행 중 부모가 끝날 때까지 busy 상태와 자원을 보존하고 종료한다.

non2xx는 기존 `{error:{code}}` 형식이다. 새 code 제안은 `intake_reference_ui_` + `unconfigured/invalid_request/input_limit/access_denied/session_unavailable/unavailable`의6개다. wire400/411/413/415/417/408, grant/session403, busy429, 미구성/예외503을 구별한다. 부모0428종 및 고정034/038 오류는 spec의 **열거 허용집합만** 원 code로 보존하고, intake_not_found404/input_limit413/가용성·무결성503으로 고정 매핑한다. 모르는 예외·path/SQL/값·traceback은 고정 unavailable로 닫는다. service의 정상 current unavailable은200으로 유지한다.

SQLite seq/cursor의 부모 최대 `2**63-1`을 축소하지 않는다. 브라우저는 raw JSON 정수 lexeme와 Number 안전 범위를 검증하고, 표현할 수 없는 seq/cursor는 명시적인 표시 한계 오류로 남겨 lastgood를 보존한다. 반올림·문자열로 몰래 변환·잘라내기·기본0/null·가짜 빈 이력은 없다. UTC timezone 시각 원형을 검증하고 표시만 KST로 바꾼다.

## 6. 선택 세대와 소유 접점

기존 `prepareView/publishView`가 검증·동시 게시한 `{intake_id,revision,snapshotGeneration}`을 새 패널의 `setContext`에 명시 전달한다. DOM 스크랩·기존 fixture gate 공유는 없다. main refresh 시작은 별도 pending 접점으로 이전 ticket을 즉시 무효화한다. 선택/판본/게시 세대가 바뀌면 history/current의 독립 gate와 AbortController를 무효화한다. 늦은 성공·부족·거절·transport 오류 모두 새 선택/초점/lastgood를 덮지 못한다. 오류 때 같은 선택의 lastgood는 관측 시각과 stale 표시로 남기고 다른 접수의 결과를 현재 선택의 것으로 보여주지 않는다. 목록 revision과 새 current 관측이 원자적으로 같다고 표시하지 않는다.

추후 소유 **10파일 제안**: 기존 `labflow/ui_server.py`, `tests/test_ui_server.py`, `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`; 신규 `frontend/intake_references/{model.mjs,view.mjs,model.test.mjs,browser_check.cjs}`, `docs/fcc/intake_reference_ui_usage.md`. 실제 정적 파일 allowlist·기존 options/route 회귀와 독립 typed parser·DOM을 포함한다.043 Store·042·038/034·039·024/033 파일은 수정하지 않는다. 공유 dispatcher/top frontend 변경은 총괄의044 소유권 확정 뒤만 가능하다.

## 7. 미실행 수용 조건18

| ID | 실제로 유발할 조건 | 기대 관측 |
|---|---|---|
| U01 | None·부재/다른 Store·미지원043 profile | 고정 disabled/오류, 생성/DDL/provenance 변경/새 부모 import0, 기존 화면 정상 |
| U02 | 정식043 existing Store + genuine 합성 SQLite/038 이력 | 실제 history GET→042→038→DOM, source read0/private payload SQL 선택0 |
| U03 | 페이지 진입/검색/접수 선택/이력 pagination | fresh current·retained source read·prepare·append0 |
| U04 | scope 없음/다른 ID, Origin missing/null/타사이트, cookie/CSRF 불일치 | beforeparent403·원문0; 기존 위임 범위에서는 추가 동의창0 |
| U05 | 정상 명시 current 버튼 | 실제 POST→042→038/034→DOM; retained PDF/context/extraction read 실제 계수, parser/OCR/render/새 catalog/모델0 |
| U06 | source/상태 변경으로 current/stale/none/unavailable | 관측 시각·원 reason/old head 보존, 과거 append와 새 현재성 혼동0 |
| U07 | available=false인 ledger + 지원되는 접수 현재 상태 | history 부재와 새 current 관측 독립, 임의 available=true/빈 성공0 |
| U08 | body/권한 flag/query token/alias·TE/CE/dup CL/Expect·잘못된 JSON | 고정 status/code, 부모0/secret·원문 echo0 |
| U09 | source I/O/무결성/SQLite 실패·모르는 부모 code | 고정 실패·lastgood 보존, 성공/부족으로 삼킴0 |
| U10 | seq/cursor 2**53−1·2**53·2**63−1/0/false/null | 안전 범위 정확 보존, 나머지 명시 한계/입력 거절·반올림0 |
| U11 | 새 선택/refresh 뒤 늦은 성공·부족·거절·transport error | stale parse/publish0·새 선택/초점/lastgood 불변 |
| U12 | 만료/재시작/세션128포화·다른 cookie token | session 고정 거절, source 자동 재시도·전역 token 공유0 |
| U13 | current 이중 클릭·동시 요청·35초 timeout | 동시1/queue0, 결과 불명 표시·자동 source 재송신0·자원 종료 |
| U14 | 정제 DTO 변조·extra/누락 key·verification true·0/false/null | strict typed 거절/원형 보존, raw quote/경로/JSON export0 |
| U15 | explicit 현재 조회 전후 실제 합성 DB·blob·source 비교 | SQL row/schema/provenance 쓰기0, SQLite WAL/SHM 관측은 별도이며 전체 filesystem writes0 주장0 |
| U16 | history 현재/과거 표시·KST·키보드/초점·390/1440px | 실제 DOM/접근성·스크린샷 확인, current_at_append를 최신으로 표시0 |
| U17 | 039 POST·040 S0·024/033·기존 접수/fixture 화면 | exact route/옵션/기능 계약 보존; 옛 actual 증거를 새 source 실행으로 재계수0 |
| U18 | 정식 실제 경계 수용 | owner 합성 E2E와 독립 리뷰 후, 리드가 정한 실제 접수/Store·권한·원문 범위에서 새phase만 실행. 지금 customer/LG DB·원문 사용0 |

이 표는 PASS 수가 아니다. 합성 fixture 준비의 생성/분석과 API 내 I/O를 나누고 실패/전후 상태/자원/수정 전 증거를 보존한다. 현재 사용자 준비·추가 승인 질문은0건이며 선택·고정은 리드가 진행 중인042/043 인수와 함께 한다.


## 승인 보완 v2 — ID·수명·genuine 최초 수용

2026-10-24 Asia/Seoul. 리드가 선택한 사항을 v1의 후속 고정 후보로 정리한다. 정적 검토 중인 `contract-proposal-v1.md` 14232B/SHA `80c6e486d7d5093660337680f720b4c56723a5322e42c670eb9d746c89d5e1e2`와 v1 receipt를 수정하지 않는다. 아래 항목이 해당 v1 문장을 보완하며 나머지 제한·한도·미실행 조건은 유지한다.044 제품/공유 HTTP/Store/새 branch 변경0,039 재검토 우선이다.

## 1. 선택된 첫 범위

리드는 A를 선택했다. 정제 history7의 GET/HEAD와 사용자 명시 fresh current10의 POST만 첫044에 연결한다. preview11·reason9 계약을 보존하며 prepare/append는 후속이다. 추가 세션 경로/JSON DTO를 만드는 B는 선택하지 않았다. v1의 header·세션 한도·오류와 기존 auth의 재사용 가능성은042 최종·043 v2 및044 정적 검토 뒤 리드가 공통 spec에 고정한다. 이 보완으로 제품 구현을 시작하지 않는다.

## 2. ASCII150의 정확 의미

034/038/042의 intake ID는 같은 Python literal **`r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z'` + `re.ASCII`**, exact str/fullmatch와 **길이1..150**이다. 첫 문자는 ASCII 영문/숫자이고 이후는 ASCII 영문/숫자/underscore/dot/hyphen이다. NFC·strip·casefold·percent alias 보정은 없다. 경로 ID를 다른 reference case ID의 최대128 규칙으로 좁히지 않는다.

JS는 primitive string/길이1..150과 완전 일치를 확인한다. 예를 들어 `/^[A-Za-z0-9][A-Za-z0-9_.-]{0,149}$/.exec(id)?.[0] === id`로 끝까지 같은지 확인한다. `$`의 줄바꿈 전 일치를 성공으로 삼키는 `.test()` 단독 검사는 쓰지 않는다. 정상 `A`와 ASCII150, 실패151·빈 문자열·`_A`·한글·공백·slash·percent·마지막 LF/CRLF를 미실행 수용 조건에 추가한다. wire/path/query와 parent DTO에서 같은 intake ID 의미를 유지한다.

## 3. 043에 맞춘 borrowed Store 수명

043은 리드가 고른 **분리된 `Store.open_existing(root: str)` → exact Store**, native READ|WRITE 공유/denyDELETE 수명 pin, 명시 close/context, clean rollback only·WAL/sidecar 거절, core+GEN+038의 인식된 정확 schema를 따른다. startup은 header/known schema metadata 범위다. 전체 data page/무결성·원문 검증 성공을 선언하거나 추가하지 않는다. 기존 생성형 `Store(root)` 기본은 보존한다. 구체 API/오류/예산은043의 최종 공통 계약을 인수한다.

044 caller는 정식043으로 열린 Store를 **빌려 준다**.044가 기본 생성자를 호출하거나 borrowed Store의 `close`/context exit를 소유하지 않는다.044 host는 history와 current 양쪽의 부모 호출 진입/종료를 자기 lock·활성 호출 수로 감독한다. close 순서는 **새 호출 admission 차단 → 이미 진입한 모든 부모 호출의 finally 종료·활성0 확인 → host 종료 확인 → caller의 Store.close**다. timeout/브라우저 abort/응답 실패도 활성0 확인을 생략하는 근거가 아니다. 호출 중 Store close와 close 뒤 재사용은 caller 계약 위반이다.

034/038은 `store.db`에서 자체 connection을 연다.043의 Store.connection 활성 카운터·closed/mode/schema guard가 이들 connection을 추적/취소하거나 소급 적용한다고 주장하지 않는다. hostile 같은 process나 임의 caller의 조기 close를043이 막는다고 보장하지도 않는다.044는 host 자신의 호출 경로와 정상 종료에서 이 수명 규칙을 검증한다. quiescent 종료 전 강제 close·타 process 종료·가짜 connection·creating fallback은 없다.

## 4. U18 대체 — 첫 제품 수용은 실제 HTTP와 합성 접수

v1 U18의 ‘정식 실제 경계 수용’은 아래 **첫 제품 수용**으로 바꾼다. 아직 제공되지 않은 production DB/PDF를 구현·검증 착수나 소프트웨어 인수의 선행조건으로 요구하지 않는다.

1. 승인된 새 private 합성 workspace에서 public API로 genuine 합성 접수·retained PDF/context/extraction·038 이력을 준비한다. 준비 단계의 Store 생성·DDL·분석·catalog/038 기록을044 read 단계와 따로 계수한다. fixture의 모든 SQLite 문맥을 종료해 clean rollback admission을 만족시킨다.
2. **실제 정식043 `Store.open_existing`**로 그 workspace를 열어 exact Store를 얻는다. fakeStore/proxy/`__new__`·속성 조립·041/042 결과 JSON 재생으로 대체하지 않는다. startup 원문 PDF 읽기/파싱·전체 DB integrity 검사는0이며 header/metadata 읽기는 별도 기록한다.
3. borrowed Store를 주입한 실제 HTTP 서버와 제품 화면에서 이력 GET/HEAD→042→038→DOM, 명시 current POST→042→038/034→DOM을 실행한다. history의 retained source read0과 current의 실제 retained PDF/context/extraction read를 계수하고 원문 재파싱/OCR/render·새 모델·실장비0을 구분한다.
4. history7/current10·old append 대 fresh 시각·reason/source_modes/false authority·JS seq/null·late response/lastgood/초점과 기존 route를 실제 브라우저에서 확인한다. API 전후 SQL row/schema/provenance·원본 상태, SQLite sidecar 관측, 종료 자원과 실패를 보존한다.
5. host의 모든 API 호출 종료를 확인한 뒤 caller가 Store를 close한다. 소유 검증과 독립 리뷰를 마친 범위만 인수한다. **실고객 DB/PDF와 현장 검증은 별도 후속**이며 이 합성 E2E를 실고객·실측·전체 무인 시험소 완료로 표시하지 않는다.

이 다섯 단계와 ID/수명 조건은 전부 미실행이다. 현재 작업은 계약·소스 읽기와 문서 무결성 확인뿐이다. 실제 읽기 범위/권리·미지원·모호성이 생기는 후속 단계에서 해당 사실만 드러내며 사용자에게 같은 위임이나 고객 DB 준비를 반복 요구하지 않는다. root020 `ed71f985b40b20da222ba90f46b4a1041492a023`의1857Python/114Node·source206은 리드의 기존 실행 기록이며044의 새 실행 수에 합산하지 않는다.


## 정확 A1/A2 보완 v3 — 최종 구성요소 표면

2026-10-24 Asia/Seoul. 승인된 v1/v2를 보존한 별도 보완안이다. 리드가 선택한 A를 A1 신규5/독립 화면, A2 기존 host/app 연결로 나눈다. **이번 작성은 계약뿐**이며039 branch `8e804c32936371de7ce1f7f90bdfe1fd0a309aea`·증거를 유지한다.044 spec/plan·A1 exact base/소유권 게시 후 새 branch에서 구현한다.

## 1. A1 공개 표면 제안

`frontend/intake_references/model.mjs` exports는 상수1/함수4만 제안한다.

```text
INTAKE_REFERENCE_VIEW_MAX_BYTES = 2097152
validateIntakeReferenceContext(context) -> detached context3 | null
parseIntakeReferenceHistoryJson(raw_json, intake_id, query2) -> detached history7
parseIntakeReferenceCurrentJson(raw_json, intake_id) -> detached current10
createIntakeReferenceGate() -> {begin(), clear(), current(ticket)}
```

gate는 begin마다 새 opaque ticket, clear는 이전 ticket 무효화, current는 동일 ticket인지 bool만 반환한다. history/current는 별도 gate 인스턴스다. parser는042의 exact DTO·status/관측/verification·배열 순서·0/false/null을 보존한다. raw/의미2MiB·depth20/nodes200000(key+value)·strict UTF8/JSON과 기존 ID/시간 한도를 적용한다. 부모 SQLite63bit를 축소하지 않고 JS 정수 lexeme/안전 범위 밖은 `intake_reference_view_unrepresentable`, 다른 입력/DTO 위반은 `invalid_intake_reference_view`의 고정 Error만 낸다. 반올림·잘라내기·정렬 보정·빈 성공은 없다.

`view.mjs`의 유일 export와 반환은 다음이다.

```text
createIntakeReferenceReview(container, {readHistory, readCurrent})
  -> {root, setContext(context), setPending(boolean), refreshHistory(), destroy()}
```

root는 자신이 생성한 HTMLElement다. options도 정확2키/함수만 받는다. setters/destroy는 void, refreshHistory는 Promise<void>이며 정상 조회 실패는 화면 상태로 처리한다. view에는 fetch/HTTP 경로·cookie·CSRF·세션 ID·Store·권한 설정을 넣지 않는다. transport가 보낸 secret key도 허용하지 않는다. destroy는 terminal/멱등이며 gate/AbortController/listener를 해제하고 자기 root만 분리한다. 이후 새 호출·늦은 응답 처리0이고 목록/fixture 상태는 변경하지 않는다.

## 2. trusted transport 정확 계약

```text
readHistory(intake_id, query2, signal)
  -> Promise<{raw_json: string, read_allowed: boolean}>
readCurrent(intake_id, signal)
  -> Promise<string>  // current10 raw JSON
query2 = {limit: 20, before_seq: null | positive safe integer}
```

history 반환은 정확2 own data keys이고 primitive string/bool이다. query2는 정확2키이며 첫 페이지/새로고침은20/null, ‘이전 이력’만 검증된 next_before_seq를 쓴다. parser는 limit1..100/정확 cursor를 검사하고 순서·페이지 경계를 대조한다. cursor를 URL 문자열로 만드는 일은 A2 app transport가 맡는다. query/인자에 context/secret/권한 flag를 섞지 않는다.

read_allowed는 **해당 현재 문맥의 정상 history 응답에서만 얻는 UI 가능 여부**다. 서버 권한의 원천이나 새 위임이 아니다. 초기/문맥 변경/pending/이력 재조회 시작·실패에서는 false로 닫는다. 정상 typed history7과 wrapper가 함께 유효해야 갱신한다. history 실패·read_allowed=false에서도 lastgood history/current DTO의 원래 표시값을 false/빈 목록으로 덮지 않는다.

A2 app transport가 session/CSRF를 private closure에서 보유하고 header·same-origin·cookie·HTTP status/code를 처리한다. view에는 raw_json/read_allowed 또는 raw current만 전달한다. transport 오류는 정제된 고정 오류로 reject하며 view가 raw exception/본문/주소를 DOM에 출력하지 않는다. secret은 view return/DOM/브라우저 영속 저장·URL/history/로그·수용 receipt로 보내지 않는다. 현재 요청 body는 A2가 정확 `{schema_version:1,action:"current"}`로 구성한다.

## 3. context·pending·두 독립 gate

context는 null 또는 정확3키 `{intake_id,revision,snapshotGeneration}`다. intake ID는 승인된 ASCII regex/fullmatch·길이1..150, revision은 양의 safe integer, snapshotGeneration은0 이상의 safe integer다. primitive/plain own data 값만 받고 새 사본으로 보관한다. 잘못된 context는 두 ticket/source 허용을 닫고 고정 오류·새 transport0·lastgood 보존이다.

| 진입 | 동작 |
|---|---|
| 생성/`setContext(null)` | source·metadata 호출0, 두 ticket 무효화·current 비활성 |
| 동일 context3 재전달 | no-op; 목록 필터 재게시로 중복 조회0 |
| 다른 유효 context3 | 두 ticket 무효화/abort, 새 선택의 lastgood로 혼동0. pending이 아니면 첫 history1 자동 호출 |
| `setPending(true)` | 즉시 두 ticket 무효화/abort·read_allowed=false, 새 호출 차단·lastgood stale |
| pending 중 context 변경 | 최신 context 하나만 보관, history는 아직 호출0 |
| `setPending(false)` | pending 중 받은 새 유효 context의 history를 최대1회 시작. 새 context가 없으면 자동 재시도0 |
| 이력 새로고침/이전 페이지 | history gate만 교체, metadata만 조회. current 자동 호출/그 ticket 대체0 |
| 현재 조회 버튼 | context 유효·not pending·read_allowed=true·current 미진행일 때만1회. 중복 클릭/자동 retry0 |

각 async success/reject는 alive·자기 ticket·캡처한 context3을 **parse/표시 전에** 확인한다. 늦은 성공·부족·거절·transport error는 parse/publish/초점 변경0이다. history와 current의 lastgood는 별도이고 원래 context/관측 시각을 함께 보존한다. 다른 선택의 값을 새 선택의 결과로 보이지 않게 한다. raw unsafe seq/cursor 오류는 명시 표시 한계로 남기고 이전 정상 페이지/현재 결과를 보존하며 pagination을 차단한다.0/false/null로 대체하지 않는다.

자동 이력 조회는 초점을 옮기지 않는다. 명시 클릭의 결과도 사용자가 다른 곳으로 옮긴 초점을 빼앗지 않는다. history/current error가 다른 채널의 정상 결과를 지우지 않는다. current_at_append·이전 등록·fresh 관측의 의미와 KST 표시는 v1/v2를 따른다. secret·raw JSON 다운로드·원문 값/quote를 새 화면으로 추가하지 않는다.

## 4. A1/A2 소유·검증 경계

A1은 신규 `frontend/intake_references/{model.mjs,view.mjs,model.test.mjs,browser_check.cjs}`와 `docs/fcc/intake_reference_ui_usage.md` **정확5파일**이다. 기존 stylesheet는 읽기 전용으로 참조할 수 있으며 shared host/app/style·부모·039/024/033 변경0이다. 테스트는 DTO parser의 정상/변조/unsafe 정수, 독립 gate, 위 context/pending 전이, wrapper false, 지연된 success/error·lastgood·destroy·초점·모바일을 실제 브라우저의 **합성 trusted transport DOM**에서 RED→GREEN으로 확인한다. 전체 DTO fixture이며 가짜 Store/API 수용을 만들지 않는다. 수용 tool의 자체 static harness HTTP는042/043 제품 HTTP 완료가 아니다.

A2는 리드가 고정할 기존 `labflow/ui_server.py`, `tests/test_ui_server.py`, `frontend/app.js`, `frontend/index.html`, `frontend/styles.css` 연결이다. A1 checker의 A2 실제 API 수용 확장 소유는 A2 spec에서 함께 고정한다. 최종043 borrowed Store/042/038의 genuine 합성 접수로 **제품 HTTP→정식 API→DOM**을 새 phase에서 실행한다. 수명·권한·CSRF·원문 I/O 계수·기존 route·종료와 U18 보완을 실제 확인한 뒤에만 이 단계가 완료된다. 실제 고객 DB/PDF는 후속이며 A1/A2 착수의 새 준비물로 요구하지 않는다.

위 API·상태·수용 조건은 전부 제안/미실행이다. 현재042/043 host를 만들거나 backend 완료를 가장하지 않는다. 사용자 준비·반복 승인 질문0이며 리드의 정확 공통 spec/plan 게시 다음에 A1 제품 구현으로 바로 잇는다.
