# 접수 참고이력 HTTP host049 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 새 하위 에이전트0.

**Goal:** borrowed043 Store의 history/current HTTP·같은 session/source gate·정상 종료와 정적3 예약을 기존 server에 연결한다.

**Architecture:** None을 보존하고 configured runtime/수명만 분기한다. parent I/O는 mutex 밖, 후속 단위는 별도 인수다.

**Tech Stack:** 기존 Python http.server/threading·043/042/038/034.

**Spec:** [고정 설계](../specs/2026-10-24-intake-reference-http-host-design.md), 그 안의044/공개046 참조와 [부모27/asset3](../specs/2026-10-24-intake-reference-http-host-design.md#고정-부모-오류27). 아래는 미실행 계획이며 정확 root025 게시 base의 실제 배정 뒤 구현한다. 승인 A1 model/view는 그 base에 포함되고 future transport는 미구현이다.

## Global Constraints

- 공개049 spec/plan·hook·소유/exact base 전달 후 신규 `codex/dev1-intake-reference-host049-20261024` 제안 branch를 만든다. 현재043 HEAD/clean·Yes·실패·초안을 보존한다.
- 소유는 ui_server.py/test_ui_server.py/신규 host usage 정확3. D4 frontend·부모/040/공통 CLI 수정0이다. 새 keyword2/None import0·기존 위임/source 기본거절·044 cap/6 host code+27 부모 allowlist를 보존한다.
- 정적3은 URL dash→고정 frontend/intake_references 파일/MIME JS UTF8다. placeholder0. 승인 A1 candidate38e0e1b의 accepted base/static2와 미래 transport404/후속 제공을 분리한다.
-049 HTTP/코어가 D4 asset/DOM이나046 실제 provider를 기다리는 게이트0. runtime RLock/epoch·hook2만 고정하고 prepare/append/registry·추가 동의/모델/실물0이다.

## Review Focus

1. None이 새 import/생성/daemon 변경을 받는 경우 → T1/H01과 T3의040 회귀.
2. auth→lease 사이 expiry/closing·다른 epoch/RLock → T2/H06~H08.
3. parent I/O 중 mutex 점유·abort 후 source 선반환 → T2의 block/finally 검사.
4. daemon/자기 worker close·미시작/same-thread shutdown deadlock → T3/H09.
5. 느린 client/uncaught write traceback·정적 alias/빈 transport 대체 → T1/H13·T3/H10.

---

### T1: 주입·typed HTTP·정적3

**Files:** Modify `labflow/ui_server.py`; Test `tests/test_ui_server.py`; Create `docs/fcc/intake_reference_host_usage.md`.

**Interfaces:** 기존 create_server에 `intake_reference_store=None,intake_reference_read_scope=()`만 추가. configured는 official exact Store를 빌려 `read_reference_review(store,intake_id,request,*,allow_retained_reads=False)`를 capture한다. None은 runtime/042 import0이다. static URL3/고정 파일/MIME는 spec을 따른다.

- [ ] **1. usage·RED:** `test_reference_none_without_import_or_create`, `test_reference_Store_binding_and_workspace_before_bind`, `test_reference_history_HEAD_and_explicit_current`, `test_reference_strict_wire_scope_and_typed_result`로 H01~H05를 작성한다. keyword 부재 RED와 setup 실패를 구별한다. ASCII150/151·scope100/101·rawalias/정상UTF8·current405/HEAD body0·normal unavailable200·부모27/unknown을 고정한다.
- [ ] **2. static RED:** `test_reference_assets_exact3_None_MIME_HEAD_alias_and_missing`로 H13을 작성한다. exact mapping3/MIME, GET/HEAD·다른method405, query/percent/slash/absolute alias404·부모0을 확인한다. 현재 미구현 transport는 실제404이고 fake/빈 파일을 만들지 않는다. 승인 A1 static2의 실제200/bytes는 accepted base의 고정 blob과 대조하는 별도 phase다.
- [ ] **3. RED 실행:** `python -X utf8 -B -m unittest discover -s tests -p test_ui_server.py -v`를 기존 tests import 규칙으로 실행한다. 실패·baseline pins를 private 보존하고 환경 오류는 private runner에서 해결한다. 부모/tests/__init__를 바꾸지 않는다.
- [ ] **4. 최소 구현:** None을 분리하고 configured 입력/공식 binding·sameworkspace를 bind 전에 검증한다.044 route/auth/예산·typed DTO/오류를 그대로 적용하고 formal 부모만 호출한다. static3은 raw exact lookup, FileNotFound404·다른IO503·기존보안header/CSP/MIME이며 generic path를 열지 않는다. 정적 None 요청에 runtime을 만들지 않는다.
- [ ] **5. genuine GREEN:** public API로 준비한 합성 접수/PDF/context/extraction/038 fixture의 문맥을 닫고043→port0 HTTP history GET/HEAD/허용current·기본거절을 실행한다. fixture 생성/DDL/분석/기록과 API phase를 구분한다. source read·재파싱0·SQL row/schema/provenance/input과 자원을 기록한다. 전달 base에 accepted A1이 있으면 static2를 실제 검증하고 없으면 그 실행만 후속으로 남긴다. 코어를 fakeStore/DTO/asset으로 통과시키지 않는다.

### T2: session·같은 RLock·source lease/hook

**Files:** 동일 소유3.

**Interfaces:** server `_reference_action_binding(session_id) -> binding3|None`, `_reference_parent_call(*,source=False) -> contextmanager[None]`. binding3 exact host_epoch/session_id/scope_epoch hex64, future046에 전달할 runtime lock/epochs는 같은 객체/값이다.046 import/attach0이다.

- [ ] **1. RED:** `test_reference_session_capacity_idle_HEAD_no_rotation`, `test_reference_binding_atomic_epoch_admission`, `test_reference_parent_IO_releases_runtime_mutex`, `test_reference_source_busy_abort_and_finally`로 H06~H08을 고정한다.128/129session·idle899/900·expired-only 회수·HEAD 신규/갱신0·32randomB형식·중복cookie/header·stale binding·exact bool source·current 두 번째429/부모0을 검사한다. 시간은 private fault clock으로 제어하며 새 public callback option0이다.
- [ ] **2. RED 뒤 구현:** 성공 history GET만 session을 만들고 stable token·scope/Store/host 결합을 유지한다. auth·binding·lease를 같은 RLock 아래 등록한 뒤 parent 전에 완전히 놓는다. active/source1·queue0과 finally/notify를 구현한다. 만료/closing binding은None이고 새 session/권한을 만들지 않는다.
- [ ] **3. GREEN:** 실제 cookie/CSRF HTTP의 허용/거절과 parent를 막은 상태의 metadata/lock·current429를 관측한다. disconnect/timeout 뒤에도 원래 parent finally까지 source/active가 유지돼야 한다. secret/binding/epoch/raw path·quote를 HTTP/stdout/stderr에 내보내지 않는다. hook/double 검사를046 registry·제품 통합 PASS로 세지 않는다.

### T3: drain·quiet worker·회귀/인수

**Files:** 동일 소유3.

**Interfaces:** configured `server_close()`는 admission→모든 부모 active0→worker/socket/session 종료, borrowed Store close0. supervisor caller가 host 후 Store를 닫는다. None/040 server/daemon은 그대로다.

- [ ] **1. RED:** `test_reference_close_waits_for_all_parent_finally`, `test_reference_own_worker_and_lease_close_rejected`, `test_reference_loop_not_started_running_and_stopped_close`, `test_reference_repeat_interrupt_first_error_and_partial_cleanup`, `test_reference_slow_client_quiet_handler_and_native_release`로 H09~H12를 작성한다. bind 부분실패와 외부 활성예외 문맥도 포함한다.
- [ ] **2. 구현:** configured 전용 non-daemon/block_on_close·실행 loop/thread 상태를 둔다. close가 admission을 먼저 닫고 다른 thread의 실행 중 loop만 shutdown, 미시작/종료 loop에는 호출0이다. drain/join 중 RLock 점유0·부모 active0 전 반환0이다. 자기 worker/lease close는 고정 거절하고 caller가 quiescent 완료로 해석하지 못하게 한다. socket I/O5초·quiet handle_error/log와 first error/나머지 cleanup을 보존한다.
- [ ] **3. genuine GREEN:** history/current 각각 block·abort·close·반복 interrupt/응답실패를 실제 HTTP/043에서 유발한다. host borrowed close0→caller close 후 자기 port 재bind·DB/blobs/root rename 해제를 확인한다. raw stderr/traceback0과 worker/SQL 종료, row/schema/provenance/source 불변·SQLite sidecar 관측을 분리한다. 타 process/현장망 제어0이다.
- [ ] **4. 회귀·문서:** 전용→043/042/034/038·ui_server/040·기존 route→전체 Python을 실행한다. `python scripts/check_artifacts.py`, 새 usage 링크/UTF8·소유밖 diff/부모 pins·실패/known자원을 확인한다. asset phase는 예약/미존재404·accepted A1 static2·D4 transport actual로 구별하며 DOM/Node의 실행·미실행을 따로 보고한다.
- [ ] **5. 게시:** 정확3 commit/push·remoteSHA·GitLF pins/새 QA로 총괄에 인계한다. 독립 지적은 같은3 수정/회귀 뒤 재검토하고 총괄 통합/게시까지 잇는다. D4 DOM·046 attach·047 CLI 완료를049 단위 수로 합산하지 않는다.

## 2026-10-25 후행 만료 보완 검사 — 미실행

고정 설계의 완료 후 만료 명확화를 같은049 소유3으로 구현한다. 기존 c24e806·원No/RED·owner/독립 post-parent 관측은 보존한다. 입장과 native 뒤 최종 인증에서 이미 만료한 cookie의403/부모0 검사는 유지한다. 실제 formal042 history가 반환한 직후 private clock을900으로 진행하는 GET/HEAD 경계를 먼저 RED로 고정하고,200/history7·Read-Allowed:false·CSRF/Set-Cookie/새세션/idle갱신0·HEAD body0·부모1/ROSQLite1·자원회수를 검증한다. 이미 허용된 current200/current10은 완료 뒤 새 인증/idle갱신 없이 유지되는 별도 검사다. closing/binding/native 실패와 혼동하지 않고 기존50·관련297·genuine043/042·수명·필요전체회귀를 새 phase로 확인해 같은branch 수정commit/push→독립재검토→총괄인수로 잇는다.047/053 제품 착수나 소유권 이관을 뜻하지 않는다.

## 자체 검토·미실행 상태

H01~H13과 keyword2/hook2·None/정적3·lock/close를 spec과 대조했다. 구현/검사0,실제 구현 base는 이 설계/계획과 accepted A1을 포함한 총괄의 정확 root025 게시 SHA로 배정한다. public spec/plan·소유/hook/base 고정 뒤 구현을 별도 배정하며 새 고객자료/사용자 준비·승인0이다.
