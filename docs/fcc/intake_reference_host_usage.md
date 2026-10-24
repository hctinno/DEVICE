# 접수 참고이력 HTTP host049

2026-10-24 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-intake-reference-http-host-design.md)·[계획](../superpowers/plans/2026-10-24-intake-reference-http-host.md)의 backend다. 전체 시험소·현장 운전·규범 적합성 완료를 뜻하지 않는다.

```python
from labflow.store import Store
from labflow.ui_server import create_server

with Store.open_existing(workspace_absolute_string) as store:
    server = create_server(store.root, port=0, intake_reference_store=store,
                           intake_reference_read_scope="workspace")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
```

Store는 caller가 소유한다. host는043 공식 existing exact Store와 같은 workspace만 받으며 생성자/DDL/추가 Store를 호출하지 않는다. None은 reference 미구성으로 기존 UI/040을 유지하고042 import/call0이다. scope 기본 `()`는 retained read를 거절한다. 기존 위임의 exact `"workspace"` 또는 중복 없는 ASCII1..150 ID tuple1..100을 명시할 수 있다. HTTP가 위임을 만들거나 scope를 바꾸지 못하며 새 동의창/업로드/모델 실행은 없다.

`/api/intake-references/{id}/history` GET/HEAD는042 history7의 metadata다. query는 limit1..100(기본20)·before_seq63bit(기본null)뿐이다. HEAD는 body·새 session·idle 갱신0이다. 정상 GET은 port별 HttpOnly/SameSite=Strict cookie와 read-allowed header를 돌려주며 허용된 세션에만 CSRF header를 준다. cookie/token은 고정 host/Store/scope에 묶이고128 session/idle900초이며 정상 후속 GET에 token을 회전시키지 않는다.

`/api/intake-references/{id}/current` POST는 정확 `{"schema_version":1,"action":"current"}`만 받는다. 별도 명시 호출에서만 보존 PDF/context/extraction의 무결성을 읽고 새 파싱/OCR/render는 하지 않는다. 정상 none/stale/unavailable도 current10의200 응답이며 과거 등록과 새 현재 관측을 합치지 않는다. strict loopback/Host·필수 Origin=http://Host·present Fetch-Site=same-origin·session cookie/CSRF·scope를 확인한다. 자동 source 재송신0이다.

wire16KiB/depth8/nodes256·응답2MiB/depth20/nodes200000·socket I/O5초를 적용한다. ID/cursor/0/false/null을 바꾸지 않으며 unsafe JS 정수를 몰래 반올림하지 않는다. client abort/timeout은 이미 시작된 부모를 취소하지 않는다. host source gate는 동시1/queue0이며 busy429다. 부모 I/O 중 runtime RLock을 잡지 않고 finally에서 active/source를 반환한다. history와 source 실행·fixture 준비의 DDL/분석/기록을 구별한다.

내부 hook `_reference_action_binding(session_id)`와 `_reference_parent_call(*,source=False)`는 미래046의 같은 RLock/epoch·세션/source gate 연결용이다. binding3/epoch/secret은 wire/DOM/로그에 내보내지 않는다.049는046 prepare/append/registry나 새 producer를 구현하지 않는다.

configured `server_close()`는 admission 차단→모든 부모 finally/active0→worker/socket/session 회수 뒤 반환한다. borrowed Store.close는0이며 caller가 그 뒤 닫는다. 실행 중인 다른 thread의 loop만 shutdown하고 미시작/중단 loop의 deadlock을 피한다. 자기 worker/lease/실행 loop 안의 close는 고정 거절이므로 완료로 해석하지 않는다. 반복 close는 멱등이고 반복 interrupt가 drain을 생략하지 않는다. 부모 I/O의 총 deadline/강제 취소·강제 process kill의 graceful 완료는 보장하지 않는다. None/040의 전역 thread 설정은 유지한다.

정적 `/intake-references/{model,view,transport}.mjs`는 고정3 allowlist·JS UTF8 MIME·기존 CSP self만 사용한다. None에서도 존재 파일을 제공하며 없는 파일은404, 다른 I/O 오류는503이다. 승인 A1 model/view의 실제bytes 제공과 미래 D4 transport404/후속 제공·DOM을 구별한다. 빈 대체 asset/범용 path/CSP 완화0이다.

오류는 고정 `intake_reference_ui_`6코드와 exact 부모 class/code27만 내보낸다. auth403·busy429·wire400/411/413/415/417/408·미구성/unknown503을 구별한다. raw exception/SQL/path·traceback·secret을 자동 출력하지 않는다. metadata 관측을 전체 DB/원문 진위·권리·지속 현재성·쓰기/운전 권한으로 승격하지 않는다.

초기 `20e26ed` 후보의 2026-10-24 검증은 기준 `0d7ee630b87bf2e2221c00ebcb3c106822dcfd15`의 합성 fixture로 실행했다. Python 3.12.4/SQLite 3.45.3에서 전용38·관련285·전체2053이 각각 실패/오류/건너뜀0으로 통과했다. 전체 실행은420.078초이며 검사 전후 제품/test 소스 hash가 같았다. Node v24.16.0의 기존186개도 모두 통과했다. 서로 겹치는 검사 묶음이므로 숫자를 합산하지 않는다.

별도 실제 HTTP 계측은 정식043→042 history GET/HEAD/current POST 각1회였다. history/HEAD의 원문 open0, current의 합성 context7857B/PDF4437B 읽기를 관측했고 재파싱0·쓰기 SQL 요청0·read-only SQLite 연결4개 회수를 확인했다. 준비 단계의 fixture 생성/분석/038 기록은 API 실행과 분리했다. 실행 전후 DB/파일의 identity·mode·mtime·bytes/hash와 SQL dump/row counts가 같았다. host 종료의 borrowed Store.close0·부모 finally 대기·client/worker 회수, caller 종료 전후 native 보호 대상4곳의 이동 차단/해제와 같은 포트 재사용도 확인했다. client abort의 응답 전달 여부는 unknown으로 보존했다.

승인 A1의 model/view는 실제200·MIME·HEAD를 검증했다. 이 Windows checkout의 HTTP raw는 model12473B/view14851B이며 CRLF를 그대로 제공한다. Git LF 기준은 model12335B·SHA256 `93a6a2f2e45c9ed75e23fbc01399ae7ec3817c1a3ff2c97651198c97802a10d2`, view14712B·SHA256 `c3e38b254cc346d0bd64dc12b5f1ebae6e426ce17662c6d8f533f3da457b7417`와 같았다. HTTP raw hash와 Git LF hash를 따로 기록했으며 전송 때 줄바꿈을 바꾸지 않았다. 미구현 transport는 실제404였다.

실패한 RED와 계측기 분류 실패도 보존했다. 최초 계측기는 SQLite 내부 `-- ...` trace를 별도 SQL 명령으로 오인했다. 실행을 바꾸지 않고 실제 쓰기 요청 여부를 기록하는 authorizer를 더한 계측에서 통과했으며 제품을 바꾸거나 실패를 성공 수에 넣지 않았다. `scripts/check_artifacts.py`는 UTF8·필수 문서·링크 검사이며 기능·계측 정확도·기관 적합성 증거가 아니다.

이후 독립 검토는 Critical0/Important3의 No였다. 이력의 세션 확인과 lease 등록 사이 만료, 종료된 worker 참조 누적, runtime RLock 안의043 native identity I/O를 재현했다. 원래 후보·검사·No 원문을 보존하고 같은 소유3에서 별도 수정했다. 초기 인증과 lease 예약을 같은 critical section에서 수행하고 모든 runtime lock depth를 놓은 뒤 native 검증을 한다. 그동안 active/source lease를 보유하며 native 뒤 인증/idle/closing/binding을 다시 확인해 formal 부모에 진입한다. native 실패/중단도 finally로 lease를 반환한다. worker 참조는 실행 중 회수하되 표준 non-daemon join이 실제 thread 반환까지 기다리는 보장은 유지한다.

2026-10-25 수정본은 전용50·관련297·전체2065가 각각 실패/오류/건너뜀0으로 통과했다. 전체 실행은428.687초이며 제품/test hash가 실행 전후 같았다. 새 경계12개는 GET/HEAD 만료403의 부모/SQL0, closing/binding 변경503의 부모/SQL0, native 중 mutex 접근과 active/source 소유, 빠른 두 번째 source429, native 오류 뒤 회수,21요청의 종료 참조0, runtime finally 뒤 실제 thread 종료까지 close 대기를 확인했다. 제품 factory/main/기존 handler/hook signature와 원래38개 검사 본문은 같다.

수정본의 별도 genuine HTTP도 다시 실행했다. history GET/HEAD/current POST 각1, 앞서 적은 source bytes·parser0·쓰기 요청0·DB/file/SQL 불변·native 대상4곳 차단/해제와 같은 포트 재사용을 다시 확인했다. 이번에는 SQLite.close의 실제 C-return4도 계측했다. Node186은 초기 후보의 검사이며 frontend 소스가 같아 이번 수정에서 재실행하지 않았다. 새 RED47의 실패8·native 소유 경계 RED49의 실패5와 중간 GREEN47/49도 최종 GREEN50과 구분해 보존했다.

그 `c24e806` 후보는 원래3건의 독립 확인 뒤, 허용된 history 부모 완료 직후 만료가 뒤늦은403으로 바뀌는 I4 한 건으로 Critical0/Important1·No를 받았다. 총괄의 [공개 명확화7cafcb4](https://github.com/hctinno/DEVICE/commit/7cafcb4c79d9d64695393386162ab72e41b00d31)의 spec/plan 핀과 별도 정적Yes를 읽고 같은3에서 I4만 수정했다. 공개 문서는 git show/privatecopy로 확인했으며 이 branch의 공유 spec/plan을 바꾸거나 root base로 재배치하지 않았다.

입장/native 뒤 최종 인증 이전의 invalid/expired cookie는 그대로403/부모·SQLite0이다. 그 인증을 통과한 history 부모와 typed history7이 완료된 뒤 같은 session이 만료된 GET/HEAD는 원래 metadata200·Read-Allowed:false만 반환하며 CSRF/Set-Cookie/새session/idle갱신0, HEAD body0이다. 만료 cookie를 anonymous 신규session 분기로 바꾸지 않는다. closing을 먼저 차단하고 해당 후행분기의 binding도 확인해 다른 실패를200으로 승격하지 않는다. anonymous GET/HEAD·live cookie·이미 허용된 current200과 source/native lease 코드는 그대로다. 만료 binding은 후속 내부 조회에서도None이며 권한을 복원하지 않는다.

2026-10-25 I4 수정본의 전용54·관련301·전체2069는 각각 실패/오류/건너뜀0으로 통과했다. 전체 실행은439.906초이며 제품/test hash가 실행 전후 같았다. 원c24e에서 GET/HEAD와 binding 동시변경의 RED54/실패3을 먼저 보존했다. 새4개 검사는 실제 부모 반환 직후 clock900에서 metadata 원형·HEAD body0·권한/쿠키/idle0, 옛cookie 재제출403/추가부모·SQL0, admitted current10/후행재인증·갱신0, closing/binding/native/typed/parent 실패의 비승격을 확인했다. 원래50개 검사 본문과 다른 제품 함수·public interface는 같다.

별도 genuine043→042 HTTP는 정상GET/HEAD/current3·후행만료GET/HEAD/current3·anonymous 재bootstrap2의 formal 부모8회다. 부모 함수는 바꾸지 않고 실제 반환 profile에서 private clock만 진행했다. 후행GET/HEAD200·metadata/권한false, current200과 만료bindingNone, 옛cookie403의 부모/SQLite0을 확인했다. 실제 SQLite.close C-return9·쓰기요청0·metadata 원문0·재파싱0, 두current 각각 context7857B/PDF4437B 읽기를 계측했다. 입력/SQL dump/row counts 불변·worker/socket/native 회수와 같은 포트 재사용도 다시 확인했다. 이8회나 과거50/297/2065·초기Node186을 새54/301/2069에 합산하지 않는다. frontend가 같아 이번에도 Node는 재실행하지 않았다. 기존 No·proof·RED·관측647B와 모든 원본은 보존했다.

현재 사용 예제의 별도 CLI는 후속047이다. 실제 고객 DB/PDF·모델·실장비/현장·D4 DOM/미래 transport·046 통합은 미실행이며 이 backend 검증과 별도다. 위 I4 결과는 자체 검증이며 새 독립 판정은 총괄 재검토 후 별도로 기록한다.
