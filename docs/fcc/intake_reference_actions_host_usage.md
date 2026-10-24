# 같은 host의 접수 참고 준비·등록 HTTP — 053

이 기능은 기존049 서버에 승인046 준비 코어를 연결한다. trusted caller가 미리 구성한 검토 입력으로 **명시 준비→참고 등록→원래 요청 재전송**을 수행한다. 참고 등록은 시험 착수·인증 승인·기관 권한 부여가 아니다. 실제025 producer가 제공되지 않은 운영 입력은 미구성으로 두고 capability=false로 표시한다.

[053 설계](../superpowers/specs/2026-10-25-intake-reference-actions-host-design.md)·[구현 계획](../superpowers/plans/2026-10-25-intake-reference-actions-host.md), [049 host 사용법](intake_reference_host_usage.md), [046 코어 사용법](intake_reference_review_host_usage.md)을 함께 따른다. 기존 history/current body·040 CLI·frontend는 바꾸지 않는다.

## trusted 구성과 기본 거절

`create_server`의 새 keyword는 다음2개다.

```python
intake_reference_append_scope=()
intake_reference_review_inputs=()
```

기존 `intake_reference_store`, `fcc_case_catalog`, `intake_reference_read_scope`와 같은 Store/catalog/RLock/epochs/session/source1을 사용한다. Store는 공식 `Store.open_existing(str(workspace))`로 연 기존 exact Store이며 서버는 이를 빌린다. startup에 DB·Store를 새로 만들거나 보존 PDF를 재파싱하지 않는다.

- 새 옵션이 모두 exact 빈 tuple이면 기존 None/040/049 동작을 유지하고046을 import하거나 생성하지 않는다.
- configured Store에서 입력이 exact 빈 tuple이면 append scope만 검증하고046 import/factory0·cap=false/false다. append scope 기본값은 등록 거절이다.
- Store=None인데 새 옵션이 비기본/잘못된 값이면 bind 전에 `intake_reference_ui_invalid_request`로 거절한다.
- 비어 있지 않은 입력은 같은 RLock과 epoch로 정식046 factory1개에 전달한다. filesystem/native 관측은 mutex 밖이며, setup 실패는 고정 오류로 보고한다.

read/append scope는 각각 exact `()`·`"workspace"` 또는 중복 없는 ASCII150 접수 ID tuple≤100이다. append 가능 범위는 둘의 교집합이며 HTTP body/버튼/클라이언트 bool이 이를 넓힐 수 없다. 이미 위임된 접수 ID만 trusted caller가 전달한다.

review_inputs는 exact tuple≤100, 각 항목은 다음 exact4다. HTTP 요청에 이 private 입력을 보내지 않는다.

```text
{intake_id, case_context, validated_response, producer_name}
```

case_context/validated_response는 공개025가 구성·검증한 값이며046이 detached canonical copy로 보관한다. 입력 ID는046 canonical5의 SHA64다. 별도 loader·가짜025 응답·037 재해석·새 모델/producer·권한을 만들지 않는다. 합성 검증에서는 승인된 fixture의025 build/decode와 기존043/042/038을 사용한다.

| 경계 | bytes/depth/nodes 또는 개수 |
|---|---|
| context | 8MiB/24/200000 |
| validated response | 320KiB/16/60000 |
| startup 입력 전체 | 32MiB, 항목≤100 |
| 작은 POST | 16KiB/8/256 |
| 준비 envelope / preview | 64KiB/16/10000 / 32KiB/12/4096 |
| 등록 결과 | 2MiB/20/200000 |
| 준비 예약 | host3/session2, 각21MiB/합63MiB, 절대900초 |

## metadata bootstrap와 같은 세션

`GET /api/intake-references/{id}/history?limit=1`은 기존 history7 body를 유지한다. 보존 원문 읽기 없이 같은 세션의 read/CSRF header와 새 capability header를 제공한다.

| header | 의미 |
|---|---|
| `X-Intake-Reference-Prepare-Allowed` | exact true/false |
| `X-Intake-Reference-Append-Allowed` | exact true/false, true이면 prepare도true |
| `X-Intake-Reference-Review-Input` | prepare=true일 때의 입력 SHA64; disabled 때 생략 |

prepare=true에는 입력/read/CSRF가 필요하다. capability는 준비 readiness나 업무 권한을 대신하지 않는다.046 registry·세션·CSRF·epoch를 별도로 복제하지 않는다. HEAD는 body0·새 세션/idle 갱신0이며 기존 유효 binding/CSRF 조건이 없으면 새 cap=false/false다.

같은 session의 CSRF는 회전하지 않는다. 입장/부모 직전에 세션이 만료되면403·부모0이다. 이미 허용된 history 부모가 끝난 뒤 만료된 경우는 공개049 정책대로200 metadata/readfalse·새 capfalse/false·input/CSRF/새 cookie/새 session/idle 갱신0이다. closing/native/binding 오류는 이 만료 관측으로 덮지 않는다. 이미 허용된 current/정상 append의 결과는 이후 만료로 미실행·미저장으로 바꾸지 않는다.

## 명시 POST와 원래 요청

두 URL만 사용하며 ASCII150 ID·strict target을 적용한다. query/percent alias/중복slash/absolute target은 허용하지 않는다. GET/HEAD/기타 method는405·Allow POST·body0이다. 같은 loopback origin/cookie/CSRF와 기존049 Host/Origin/Fetch 검증이 필요하다. Content-Type은 application/json(UTF8)이며 중복키/BOM/NaN/surrogate·잘못된 정수/필드/크기·깊이를 거절한다.

| POST | exact 요청 / 응답 |
|---|---|
| `/api/intake-references/{id}/prepare` | request3 →envelope6/preview11 |
| `/api/intake-references/{id}/append` | 원래 request7 →registration10 |

```text
prepare request3:
{schema_version:1, review_input_id, replace_handle_id}

envelope6:
{schema_version, kind, handle_id, append_request_id, expires_in_seconds, preview}

append/replay request7:
{schema_version:1, handle_id, intake_id, request_id,
 preparation_id, expected_snapshot_id, expected_head_record_id}
```

handle/request ID는 server가 만들며 envelope kind는 `intake_reference_preparation_handle`이다. replace_handle_id는 null 또는 같은 세션 ready/recorded의 handle이다. appending/uncertain 교체는 거절한다. expires_in_seconds는 server 절대 기한의 ceil1..900이며 history/append/replay가 준비 기한을 연장하지 않는다.

append는 preview의 preparation/snapshot/head와 envelope의 request ID를 **원래대로** 사용한다. expected_head_record_id=null은 wildcard가 아니다. 재전송도 같은 URL에 같은 원래7 전체를 보내며 새 ID·새 snapshot·자동 재준비/재등록으로 치환하지 않는다. fresh current는 별도 명시 조회다.

정상 `current_at_append,historical_provided,preparation_unverified,head_conflict,reference_unbound`는 모두200이며 stored/replayed와 옛 append observation·false authority를 보존한다. head_conflict는 저장된 참고 이력이고 head를 전진시키지 않는다.038 request_conflict의409 오류와 구별한다.

부모 dispatch 뒤 오류·timeout·응답 유실은 결과불명일 수 있다. 정상 commit을 rollback/미저장으로 표시하지 않는다. 이미 알려진 원래7의 명시 replay로 기존 기록을 확인한다. prepare 응답을 받지 못한 경우 새 handle을 추측하지 않으며,052의 prepare_unknown/replacement_unknown과 별도 명시 새 준비 정책을 따른다. 서버가 보존 중인 예약을 자동으로 회수했다고 표시하지 않는다.

## 같은 source lease와 종료

body/socket·filesystem/native·SQL·부모 I/O는 runtime RLock 밖이다. 최종 auth/CSRF·session/idle/epoch·scope·binding과 기존 source lease를 같은 critical section에서 확인/예약한다. current/prepare/append/replay는 공용 source1·queue0이고 포화는429다. history는 metadata lease다. browser abort/소켓 timeout은 부모 취소나 미저장 증거가 아니며 부모 finally와 wrapper 정리 전에 lease를 반환하지 않는다.

만료/세션 제거는046 `discard_session`으로 알린다. outer lease 입장 뒤 core candidate 예약 전에 만료되는 간격도 finally에서 다시 정리한다. prepare envelope를 게시하기 전 같은 session/epoch/closing을 재확인해 만료/종료된 handle을 성공으로 내보내지 않는다. private046 entries/prepared를 읽어 재구성하지 않는다.

configured `server_close()`는 다음 순서를 지킨다.

1. 새 admission 차단·session retire 통지.
2. history/current/prepare/append/replay의 부모 finally와 active0 대기.
3. mutex 밖 `actions.close()`1회 호출·반환값 None 확인.
4. 기존 worker/socket/session 회수 뒤 반환.
5. caller가 borrowed Store를 닫음.

active 동안046 close를 반복 호출하거나 busy/unknown을 성공으로 삼지 않는다. 비None/정리 예외는 고정 unavailable이며 남은 자원 회수를 시도한다.046 close가 확인되지 않았다면 host를 closed로 표시하지 않는다. 자기 worker/활성 lease/같은 serving loop에서의 close 거절과 non-daemon·느린 client·미시작 loop·반복 close 정책은049 그대로다. Store는 정상 host 종료를 확인한 caller가 닫는다.

## 오류·정적 module·검증 범위

오류 body는 `{error:{code}}`뿐이다. 새 POST는 UI6+046 Host8+부모54의 exact class/code68쌍만 전달한다. prefix/클래스 이름만으로 허용하지 않는다. 기본 wire400·권한403·notfound404·충돌409·준비 만료410·한도413·busy429·미구성/unknown503이며 기존049의411/415/417/408 구분도 유지한다. Python 고정 오류의 code/str/args는 같고 cause/context=None이다. raw path/SQL/값/traceback을 노출하지 않는다. 기존 history/current 부모27 mapping은 바꾸지 않는다.

`GET/HEAD /intake-reference-actions/actions.mjs`는 실제 `frontend/intake_reference_actions/actions.mjs` 하나를 JS UTF8로 제공한다. None에서도 실제 파일만 제공하며 미존재404·기타 asset I/O503이다. 별도 listener·범용 파일서빙·placeholder/CSP 완화는 없다. 실제 C1 module 제공과 이를 메인 화면에 연결하는052 C2/F2 DOM 검증은 구별한다.

이번 개발의 전용/회귀·실제 HTTP·SQL/원문·드레인/자원 회수 결과는 후보 인계 영수증에 별도로 기록한다. 문서 무결성 검사는 UTF8/로컬 링크 확인이며 계측 정확도·규범 적합성·현장 자동화를 검증하지 않는다. 합성 fixture 결과를 고객 원문·실제 모델·실장비·전체 시험소 업무 검증으로 올리지 않는다.

2026-10-25 새 검증은 전용18개·전체 Python2193개(skip0)·Node210개(fail/skip0)다. 같은 두 합성 작업공간의 실제 HTTP에서 정식025/043/046/042/038을 사용해 정상 등록·원래 replay·head_conflict·commit 응답 유실 뒤 원래 replay를 확인했다. source 경합3개는429, 부모 실행 중 metadata는200이며 active parent drain·history 반환 후 만료의 capfalse/재발급0·옛 cookie403을 확인했다. 최초 등록의 DDL8/INSERT3, 충돌 INSERT2/head쓰기0과 replay의 추가쓰기/보존 원문 읽기0을 분리했다. native/SQL I/O 중 runtime mutex 점유0, active0 뒤 mutex 밖 actions.close()→None, 소유 스레드의 실제 SQLite close 반환36개와 caller 종료 뒤 DB rename/포트 회수를 확인했다.

실행기 이름 충돌과 관측기 cross-thread 정리 실패의 원본도 보존했다. 후자는 HTTP 두 시나리오 완료 뒤 영수증 정리에서 발생했으며, 완료 DB를 불변 복사하고 같은 합성 fixture의 참고 namespace만 검사 준비 단계에서 복원해 관측을 보완했다. 이는 제품의 commit/결과불명 처리나 자동 rollback 동작이 아니다. 기존 원본·이력·응답과 fixture 준비 SQL을 제품 SQL과 구별해 보존했다.052 C2/F2 DOM·고객/수집 원문·실제 모델·실장비·현장 검증은 미실행이다.
