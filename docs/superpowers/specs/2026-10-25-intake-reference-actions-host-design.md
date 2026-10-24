# REFERENCE-ACTIONS-HOST-053 고정 설계

2026-10-25 Asia/Seoul. A는 승인046의 trusted exact4를 **최종 인수된049의 같은 Store/catalog/RLock/epoch/session/source1**에 연결한다. 기존 HTTP host에 keyword2·POST2·capability header3·static1과046 수명 연결을 추가한다. 이 공개 설계는 제품 구현·049 인수·소유권 이관 완료를 뜻하지 않는다.

공개 [046 코어](2026-10-24-intake-reference-review-host-design.md), [049 HTTP host](2026-10-24-intake-reference-http-host-design.md), [050 frontend](2026-10-24-intake-reference-frontend-design.md), [052 UI](2026-10-24-intake-reference-actions-ui-design.md)와 [053 구현 계획](../plans/2026-10-25-intake-reference-actions-host.md)을 따른다. 새 서버·공통 registry·Store/loader/producer/모델을 추가하지 않는다.

## 정확 소유·착수 조건

| 파일 | 변경 책임 |
|---|---|
| `labflow/ui_server.py` | 기존049 runtime의046 연결·HTTP·정적1·수명 |
| `tests/test_ui_server.py` | 실제 HTTP·동시성·회수·기존 계약 회귀 |
| 신규 `docs/fcc/intake_reference_actions_host_usage.md` | trusted 주입·기본 거절·한계·실제 검증 영수증 |

소유는 정확3이다. D1의049 소유 수정·독립 최종 Yes·총괄 인수가 끝난 뒤 기존2의 소유권을 **D1→D2로 명시 이관**한다. 총괄이 accepted049를 포함한 정확 base와 소유3을 실제 전달한 뒤 개발2가 구현한다. D1은047 신규3으로 이어간다. 현재 branch/stash·원본·실패·검토 영수증은 보존한다.

046/042/043/Store/schema·기존049 usage·CLI·frontend·공유 문서는053 제품 소유 밖이다. 구현 branch 제안은 `codex/dev2-reference-actions-host053-20261024`이며 위 착수 조건 전에 만들지 않는다.052 C1의 제품 완료는053 착수 조건이 아니며 실제 C2/F2는 accepted049+053+050+052 static이 있는 별도 정확 base에서 검증한다.

## 주입·기본값

```python
create_server(workspace, host='127.0.0.1', port=8765, *,
              fcc_case_catalog=None,
              intake_reference_store=None,
              intake_reference_read_scope=(),
              intake_reference_append_scope=(),
              intake_reference_review_inputs=())
```

| 구성 | bind 전 처리 |
|---|---|
| 새 옵션 둘 다 exact 빈 tuple | 기존 None/040/049 경로 유지,046 import/factory0 |
| Store=None + 새 옵션 중 비기본/잘못된 값 | 고정 `intake_reference_ui_invalid_request`, Store/runtime 생성0 |
| configured Store + exact 빈 review_inputs | 기존 scope 검증을 append에도 재사용,046 import/factory0, cap=false/false |
| configured Store + 비어 있지 않은 review_inputs | 공식046 factory를 잠금 밖·bind 전에1회, 같은 Store/catalog/RLock/epoch·기존 read scope 전달 |

review_inputs는 exact tuple≤100이며 각 항목은 `intake_id,case_context,validated_response,producer_name` exact4다. 비tuple·중복 ID·잘못된 catalog/입력은 bind 전에 고정 오류로 거절한다.046의 detached canonical copy·context8MiB/depth24/nodes200000·response320KiB/16/60000·합계32MiB를 그대로 사용한다. 별도 입력 parser나 private prepared 복사는 만들지 않는다.

append_scope는 기존 read scope와 같은 exact `()`/`"workspace"`/중복 없는 ASCII150 ID tuple≤100이며, 등록 가능 범위는 read와 append의 교집합이다. read 없음/입력 없음은 준비 거절, append 기본값은 등록 거절이다. 빈 inputs의 default와 nondefault append_scope도 새로운 권한을 만들지 않는다. genuine 공개025가 만든 **합성** context/validated response만 검증 fixture로 사용한다. 실제 producer 미제공 상태에서는 입력을 만들지 않아 cap=false다.037/사례 선택 결과를025로 재해석하지 않는다.

startup은 기존 Store의 비소유 liveness/identity 확인만 허용하고 filesystem/native 관측은 모두 mutex 밖이다. 보존 PDF 읽기·재파싱·부모 prepare/append·새 DB/connection/DDL0, borrowed Store.close0이다.

## HTTP·capability·정적1

성공 history의 기존 body7·read header·CSRF/cookie 계약은 유지한다. 같은 유효 binding에 대한046 `capabilities` exact3를 metadata로만 읽어 다음 header를 붙인다. read/입력/CSRF 조건 없는 prepare=true 또는 append=true/prepare=false 같은 모순은503이며, cap 관측으로 보존 원문·새 SQL·부모를 호출하지 않는다.

- `X-Intake-Reference-Prepare-Allowed`: exact `true`/`false`.
- `X-Intake-Reference-Append-Allowed`: exact `true`/`false`.
- `X-Intake-Reference-Review-Input`: prepare=true인 해당 입력의 lowercase SHA64만. false/false 때 생략한다.

disabled046 경로는 import 없이 false/false와 입력 header 생략으로 처리한다. HEAD는 기존 body0·세션 생성/idle 갱신0을 지키며 기존 유효 binding/CSRF 조건을 충족할 때만 capability를 제공한다. 조건이 없으면 false/false다. 새 세션/CSRF 발급은 기존 성공 history GET의049 정책을 따르고 token 회전은 추가하지 않는다.

**history 부모 완료 뒤 세션 만료의 응답·기존 header 정책은 공개049를 그대로 따른다.** binding이 유효하지 않으면 새 cap은 false/false·review-input 생략이며, CSRF·새 cookie·새 session 발급과 idle 갱신은0이다. closing/native/binding 실패는 기존049 오류로 처리한다. 공개049 정책의 게시와049 제품 인수는 별개다.

| POST URL | exact 요청 → 응답 |
|---|---|
| `/api/intake-references/{id}/prepare` | `{schema_version,review_input_id,replace_handle_id}`3 → envelope6/preview11 |
| `/api/intake-references/{id}/append` | `{schema_version,handle_id,intake_id,request_id,preparation_id,expected_snapshot_id,expected_head_record_id}`7 → registration10 |

schema_version=1, ID와 null의 의미·envelope kind·server 생성 handle/request ID·preview11/이유9·registration10/정상분류5는046 그대로다. replay는 같은 append URL에 **원래7 전체**를 전달한다. expected_head_record_id=null을 wildcard로 바꾸거나 새 ID/현재 snapshot으로 고치지 않는다. 정상분류 `current_at_append,historical_provided,preparation_unverified,head_conflict,reference_unbound`는 모두200이며 stored/replayed/false authority를 보존한다. fresh current 자동 호출0이다.

기존049 strict target/ASCII150/Host·Origin·Fetch·loopback·cookie·CSRF·scope 검증과 body5초를 재사용한다. POST2는 query/alias0, GET/HEAD는405·Allow POST/body0이다. 요청16KiB/depth8/nodes256, strict UTF8/JSON(중복키/BOM/NaN/surrogate/unsafe 정수 거절), envelope64KiB/16/10000·preview32KiB/12/4096·registration2MiB/20/200000을 유지한다. private context/response/prepared/epoch/binding은 HTTP·DOM·로그에 내보내지 않는다.

정적 allowlist는 `/intake-reference-actions/actions.mjs` → `frontend/intake_reference_actions/actions.mjs` 정확1을 추가한다. GET/HEAD·`text/javascript; charset=utf-8`·기존 CSP self/no-store/보안 header를 유지한다. 실제 파일 없음404, 기타 asset I/O503, 다른 method405·Allow GET,HEAD다. query/percent/중복slash 등 alias는404다. None에서도 실제 파일만 제공하며 placeholder0이다.052 C1 asset의 실제 존재/200과 미존재404를 분리하고, 제품 완성을 기다리지 않는다.

## 같은 admission·세션 회수·close

1. socket/body·filesystem/native/SQL·부모 I/O는 전부 RLock 밖이다. body 검증 뒤 cookie/CSRF·idle/epoch·read/append scope·closing을 **binding 사본과 기존 parent lease/source1 예약의 같은 critical section**에서 다시 확인한다. 잠금을 완전히 놓은 뒤046 public prepare/append를 호출한다. metadata history는 source=False, current/prepare/append/replay는 공용 source=True·1개/queue0다.
2. 기존 `_reference_action_binding(session_id)`와 `_reference_parent_call(*,source=False)`를 사용한다. 별도 lock/session/admission counter/handle registry는 만들지 않는다.046의 host3/session2·각21MiB/합63MiB·절대900초 예약을 그대로 사용하고 원래 요청 재송신은 기한을 연장하지 않는다.
3. idle expiry/세션 제거는 같은 RLock에서 `actions.discard_session(binding)`으로 먼저 알려 active handle의 private 참조를 보호한다. **outer lease 입장 후046 candidate 예약 전에 만료되는 간격**도 처리한다. prepare 응답을 게시하기 전 같은 session/epoch/closing을 다시 확인하고, 이미 사라졌거나 closing이면 handle을 retire하고 성공 envelope를 내보내지 않는다. outer finally도 retired/missing/closing binding을 재확인해 discard한 뒤 lease를 반환한다. core private `_entries`/prepared를 읽지 않는다.
4. 이미 입장한 append의 정상 registration은 이후 세션 만료/응답 유실로 미저장이나 rollback으로 바꾸지 않는다. abort/timeout에도 source는 원래 부모 finally와 wrapper 정리 전 반환하지 않는다. write 실패 뒤 재귀 오류전송·자동 retry/새 ID0이다.
5. close는 기존049 admission을 닫고 session retire를 알린 뒤 **모든 history/current/prepare/append/replay lease의 finally/active0**를 기다린다. 046이 연결된 경우 그 다음 **`actions.close()`를1회 호출하고 반환값이 `None`인지 확인**한 뒤 기존 worker/socket/session을 회수해 반환한다. caller만 그 뒤 Store를 닫는다. 예외/비None는 기존049 cleanup 오류 정책으로 고정 실패를 보존하고 나머지 회수를 시도한다. active 동안046 close를 반복 시도하거나 busy/unknown을 성공으로 삼지 않는다. mutex를 잡은 shutdown/join/I/O 대기0, 기존 non-daemon/block_on_close·자기 worker/lease/같은 loop close 거절·미시작 loop·quiet error/반복 close 처리는049 그대로다.

## 오류 경계

기존 history/current의049 host6+부모27 mapping은 변경하지 않는다. 새 POST2는 **UI6 + 046 Host8 + 승인 부모54 = exact class/code 68쌍**만 고정 allowlist로 처리한다. runtime에서046 private error 상수를 조회하지 않고 승인 계약의 literal set을 둔다. prefix 일치/클래스 이름 문자열만으로는 허용하지 않는다.

046 Host8의 status는 고정400/403/409/410/413/503이며 `intake_reference_review_host_unavailable` exact class/code와 status429일 때만 core busy429다. 공용 source 포화는 기존 UI unavailable429다. 부모54는 StoreOpen9·042 Review8·038 Ledger10·034 State9·032 CaseReferences7·025 Review11이며 목록은 [승인046 API](../../../labflow/intake_reference_review_host.py)의 승인 exact 코드다. 새 POST에서 invalid_argument400/access_denied403/intake_not_found404/input_limit 또는 limit_exceeded413/038 request_conflict409, 나머지503이다. **정상 binding_status=head_conflict는200**과 구별한다.

전달은 `{error:{code}}`뿐이며 Python code/str/args 동일·cause/context=None을 유지한다. unknown/응답 형식 오류/정리 실패는 fixed unavailable503으로 닫고 raw path/SQL/value/traceback을 내보내지 않는다.

## 수용·검증 경계

[구현 계획](../plans/2026-10-25-intake-reference-actions-host.md)의 T1~T3는 전부 미실행이다. genuine043/025/046/042와 실제 loopback port0 HTTP, 원래 replay·정상분류5·고정68쌍·같은 RLock/source1·만료 간격/후행 만료·abort/결과불명·active0/close/caller native 회수·None/040/049/A1/050 회귀를 확인한다. 실제 C1 static 제공과 이후 C2/F2 DOM은 별도 phase다.

052의 controller/slot/session/결과불명 전이는 공개052를 그대로 소비하고 backend가 UI의 마지막 관측이나 서버 미도달을 추정하지 않는다. 원본·실패·입력/출력 pin·새 검증/미실행을 구별해 보존한다. 고객 PDF·실제 모델·실장비/현장 실행0이며 이 설계로 공식 권한·계측 정확도·전체 시험소 완료를 주장하지 않는다.
