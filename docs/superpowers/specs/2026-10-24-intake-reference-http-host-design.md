# 접수 참고이력 HTTP host049 설계

2026-10-24 Asia/Seoul. 개발1의049 backend 정확3파일을 고정한다.044 원래 model/view 계약·046 코어 최소hook을 재사용하고 history/current HTTP·borrowed Store 수명·exact static3만 구현한다. root025 기능43b04ae41945550723f5ca0e83698a7de3001953에는 승인044 A1 source가 포함된다. 이 설계/계획을 포함한 root025 정확 게시 SHA를 총괄이 실제 배정하면 개발1은 별도 전용 branch에서 구현한다. 기존043 branch/원본·실패·초안은 보존한다.

049는 실제 frontend/046 제품 완료를 기다리지 않고 구현한다. 정상043/042→HTTP·수명과 accepted A1 static2를 실제 검증하고, 미래 transport의 미존재404·후속 실제제공/DOM은 나눈다. frontend050 F1은 고정049 interface로 먼저 구현하되 root 제품 app 통합은 실제static3 제공/049 인수 후 수행한다. 두 담당이 같은 파일을 수정하지 않는다. 아래 H01~H13과 구현계획은 미실행이며 새 실제모델·고객원문·실장비 실행/동의창을 추가하지 않는다.

## 참조·정확 소유

[044 설계](2026-10-24-intake-reference-ui-design.md)의 history7/current10·wire/권한/표시·borrowed 수명은 그대로다. [공개046](2026-10-24-intake-reference-review-host-design.md)의 코어 선행·hook 계약을 참조한다.049 소유는 `labflow/ui_server.py`, `tests/test_ui_server.py`, 신규 `docs/fcc/intake_reference_host_usage.md` 정확3이다. D4의 A1과 후속 app/index/styles/transport·DOM은 별도다. 부모/040/공통 CLI·frontend 파일은 수정하지 않는다.

049 첫 범위는 history GET/HEAD·current POST·정적3 예약과 host 수명이다.046 준비/등록/registry/options·추가 동의·새 catalog/producer/Store·모델/실물0이다.046 코어는049 구현을 기다리지 않는다.047 thin CLI는049 인수 뒤 별도3으로 잇는다.

## 주입과 None

```python
create_server(workspace, host='127.0.0.1', port=8765, *, fcc_case_catalog=None,
              intake_reference_store=None, intake_reference_read_scope=())
```

새 keyword는2개다. None이면 reference runtime/042 import/call·Store 생성0이고 scope를 사용하지 않는다. 기존 server/daemon/옵션/040을 보존하며 새 reference API만503/unconfigured다. 아래 정적3은 None에서도 제공한다. configured 때만 정식042 `read_reference_review`/고정 오류 class를 capture하며 callback을 받지 않는다.

configured는043 공식 opener의 exact Store만 받는다. legacy creating Store/subclass/fake·닫힘/바뀐 binding·다른 workspace는 bind 전에 거절한다. exact private binding type/open·root/db/native identity를 읽기 검증하고 `Store.__enter__`를 사용한다. borrowed exit/close·새 connection/DDL은0이다. workspace는 exact str/기본 Path이며 문자열 raw alias를 정규화 전에043 규칙으로 거절하고 canonical root/고정 DB를 대조한다. 같은 process의 악의적 Python 격리/객체 출생 인증은 아니다.

scope는044의 `()`/exact `"workspace"`/중복 없는 ASCII150 ID exact tuple1..100이다. 기본 source 거절이며 기존 위임을 current retained-read에 적용한다. HTTP가 scope를 만들거나 넓히지 못한다. 잘못된 구성은 fixed invalid_request, 닫힘/identity 관측 실패는 unavailable로 bind 전에 실패한다. startup history/current·보존 PDF/재파싱/전체DB integrity0, creating/빈 성공 fallback0이다.

## 정적 allowlist delta — 정확3

| GET/HEAD URL | 고정 파일 |
|---|---|
| `/intake-references/model.mjs` | `frontend/intake_references/model.mjs` |
| `/intake-references/view.mjs` | `frontend/intake_references/view.mjs` |
| `/intake-references/transport.mjs` | `frontend/intake_references/transport.mjs` |

MIME는 모두 `text/javascript; charset=utf-8`. 같은 origin/CSP self·기존 no-store/보안 header를 유지한다. raw target exact3만 허용하며 query/fragment/percent alias·중복slash/역slash·absolute target은404다. 다른 method405·Allow GET,HEAD/HEAD body0이다. 범용 path 서빙/별도 listener0이다. 없는 파일은404/route_not_found, 다른 파일 I/O 오류는 기존503/asset_unavailable이며 기존 asset 오류 처리는 바꾸지 않는다. None에서도042 import/call·Store 생성0이다.

A1 `38e0e1b4f8073a52891db31341064cceb6f0e4ec`는 독립 Yes를 받은 정식 model/view 의존 후보다. root 인수 base/blob에서 실제200/MIME/bytes를 새 phase로 검증한다. transport는 D4 미래 소유·미구현이며 빈 대체/가짜 asset0이다. private 작성 관측 fdd40c1에는3파일 모두 없었다. root025는 승인 A1 model/view를 인수했고 transport는 여전히 미래 frontend 소유다. 소스 존재·실제049 정적200·미존재404를 구별한다. 실제 frontend 완료를049 코어/wire 구현의 선행조건으로 삼지 않는다.

## wire·오류 delta

044 §3~5의 route/ID/query/current exact2·strict UTF8/JSON·session128/idle900·CSRF/엄격 Host/Origin/loopback을 재사용한다. current16KiB/depth8/nodes256·응답2MiB/depth20/nodes200000·body5초를 보존한다. typed history7/current10/nested record11/summary5·63bit/0/false/null을 검증하고 정상 none/stale/unavailable은200이다. 기존039의 loose Origin과 섞지 않는다.

| 단계 | 고정 결과 |
|---|---|
| route/method/query/wire | 400/404/405·Allow 및044의411/413/415/417/408, 부모0. current GET/HEAD405 |
| peer/Host/Origin/Fetch·scope/session/CSRF | 403/access_denied·부모/source0. lease 예약 직전 재확인 |
| source 포화 | 429/unavailable, queue0/추가 부모0 |
| 부모 | 아래 고정 부모 오류27의 exact class+code(0428/03810/0349)만 원 code 보존. invalid_argument400/access_denied403/intake_not_found404/input_limit413, 나머지503 |
| unknown/typed응답·closing/cleanup | unavailable, HTTP503 또는 고정 ValueError. raw 예외/SQL/path/traceback0 |

host suffix는044의6개(unconfigured/invalid_request/input_limit/access_denied/session_unavailable/unavailable), prefix `intake_reference_ui_`다. prefix만으로 부모를 허용하지 않는다. JSON `{error:{code}}`, Python code/str/args 동일·cause/contextNone이다. write 실패에 빈 성공/오류 응답 재귀 전송0이다.

## 같은 runtime·hook2

host별 RLock1/Condition1·host_epoch/scope_epoch hex64·session table1을 둔다.044 cookie/32randomB ID·CSRF/idle·중복 검사/expired-only 회수·포화503을 그대로 사용한다. 성공 history GET만 session 생성, token 회전0, HEAD 신규/갱신0이다. Store identity/scope/host에 묶고 secret/epoch/binding을 HTTP/DOM/로그에 내보내지 않는다.

```text
_reference_action_binding(session_id) -> detached binding3 | None
binding3 = {host_epoch, session_id, scope_epoch}  # exact hex64 strings
_reference_parent_call(*, source=False) -> contextmanager[None]
```

binding은 HTTP auth 뒤 같은 lock에서 session/idle/epoch를 재확인한 사본이다. 없는/만료/closing은 None, 생성/갱신·부모0이다. ID만으로 CSRF/Origin을 검증했다고 주장하지 않는다. auth·binding·lease는 같은 critical section에서 등록하고 ExitStack 등으로 parent I/O 전에 mutex를 완전히 놓는다. source는 exact bool; False=history, True=current/미래 prepare·append·replay의 공용1/queue0이다. finally에서 active/source 반환·notify, abort/timeout에도 원래 parent finally 전 lease 해제0이다. 같은 lock/epoch를 future046 startup에 전달한다. 오늘046 attach/registry/capability header/expiry callback을 만들지 않는다.

2026-10-25 완료 후 세션 만료 명확화: 위 403/access_denied·부모/source0은 요청 입장과 부모 직전 최종 인증에서 거절한 경우다. 그 인증·lease를 통과해 이미 허용된 history 부모가 완료된 뒤 응답 header를 만들기 전에 같은 세션만 만료되면, GET/HEAD는 원래 history7 metadata를200으로 전달하되 Read-Allowed:false, CSRF/Set-Cookie/새 세션/idle 갱신0으로 반환한다. HEAD body0·신규/갱신0은 유지한다. 만료된 권한을 복원하거나 anonymous 신규세션으로 바꾸지 않으며, 만료 사실을 뒤늦은403으로 바꿔 이미 수행한 부모를0으로 보고하지 않는다. 이미 허용된 current의 결과200도 완료 뒤 재인증을 추가하지 않고 유지한다. 입장/부모 직전의 invalid·expired cookie는 여전히403/부모0이며, closing/binding 실패·native 오류·finally/close 수명은 이 세션 만료 예외로 덮지 않는다. 후속 capability도 만료된 binding을 유효한 것으로 사용하지 않는다. 이는 독립 재검토의 GET/HEAD 후행만료 관측에 따른 계약 명확화이며 제품 수정/검증 완료가 아니다.

## configured server_close

configured 전용 non-daemon/block_on_close server만 사용한다. admission 차단→진입한 모든 부모 finally/active0→worker/socket/session 회수 뒤 반환하며 borrowed Store.close0이다. caller가 그 뒤 Store를 닫는다. 반복 close는 멱등이고 반복 interrupt/abort로 drain을 건너뛰지 않는다. 자기 worker/활성 lease·동일 실행 loop 안의 close는 unavailable 거절이며 완료로 간주하지 않는다. 정상 supervisor의 ordinary cleanup 오류는 active0 뒤 전달하며 첫 오류와 나머지 회수 시도를 보존한다.

configured serve_forever의 실행 상태/thread를 추적한다. admission을 닫은 뒤 다른 thread에서 loop가 실행 중일 때만 shutdown한다. 미시작/이미 끝난 loop에 무조건 shutdown하지 않는다. lock을 잡은 채 shutdown/join/부모 I/O를 기다리지 않는다. configured socket header/body/response I/O5초는 느린 client의 worker 종료를 위한 것이며 parent 취소/deadline이 아니다. configured handle_error/log의 raw 자동출력0과 worker finally를 보장한다. 전역 server/None·040 설정 변경·stderr redirect·타 process 종료0이다.

## 미실행 수용·인계

| ID | 앞으로 검증할 경계 |
|---|---|
| H01~H04 | None/import0·정식Store/sameworkspace·genuine history GET/HEAD source0·명시 current/권한거절/정상200 |
| H05~H08 | wire/typed정수·session128/idle900/HEAD·same-lock/epoch·parent중 mutex 해제·source1/abort/queue0 |
| H09~H12 | active/loop/interrupt/자기close·quiet write/firsterror·caller/native 회수·원본/row/sidecar·None/040 회귀 |
| H13 | 정적3 raw path/MIME/HEAD/None·미존재404와 accepted A1 static2/미래transport 실제 제공의 분리 |

전부 미실행이며049 PASS0이다. 첫 인수는 합성 fixture 준비와 분리한 정식043/042→실제 HTTP·수명이다. accepted A1 static2는 전달된 정확 base에서 확인하고 transport genuine/DOM은 D4 후속이다.046 통합/047 CLI도 별도 phase다. 고객DB/PDF·모델·장비/현장·새 사용자 준비/승인0이다. root023+공개049 spec/plan·hook/소유/exact base 고정 후 제품 구현을 별도 배정한다.

## 고정 부모 오류27

아래 exact class와 exact code의 결합만 허용하며 prefix 일반 허용·임의 exception 문자열 노출은0이다.

| 부모 module / exact class | 허용 code |
|---|---|
|`labflow/intake_reference_review.py` / `IntakeReferenceReviewError`|`intake_reference_review_access_denied`<br>`intake_reference_review_input_limit`<br>`intake_reference_review_invalid_argument`<br>`intake_reference_review_parent_invalid`<br>`intake_reference_review_prepared_invalid`<br>`intake_reference_review_review_state_changed`<br>`intake_reference_review_store_invalid`<br>`intake_reference_review_unavailable`|
|`labflow/intake_reference_ledger.py` / `IntakeReferenceLedgerError`|`intake_reference_ledger_input_limit`<br>`intake_reference_ledger_intake_not_found`<br>`intake_reference_ledger_integrity_invalid`<br>`intake_reference_ledger_invalid_argument`<br>`intake_reference_ledger_origin_invalid`<br>`intake_reference_ledger_parent_invalid`<br>`intake_reference_ledger_request_conflict`<br>`intake_reference_ledger_schema_mismatch`<br>`intake_reference_ledger_storage_error`<br>`intake_reference_ledger_store_invalid`|
|`labflow/intake_reference_snapshot.py` / `IntakeReferenceStateError`|`intake_reference_state_delegation_invalid`<br>`intake_reference_state_input_limit`<br>`intake_reference_state_intake_not_found`<br>`intake_reference_state_invalid_argument`<br>`intake_reference_state_projection_inconsistent`<br>`intake_reference_state_source_integrity_invalid`<br>`intake_reference_state_storage_error`<br>`intake_reference_state_store_invalid`<br>`intake_reference_state_transaction_required`|
