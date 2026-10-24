# 접수 참고검토 host046 코어

2026-10-24 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-intake-reference-review-host-design.md)·[계획](../superpowers/plans/2026-10-24-intake-reference-review-host.md)과 [부모042](intake_reference_review_usage.md)를 따른다. 실제 backend049의 auth/session/CSRF/source gate/HTTP·DOM·configured host 종료는 별도 통합 단계다. 이 코어는 이미 위임된 trusted binding3/실제 RLock과 정식043 Store·genuine catalog·025 검토 입력을 받는다.

## 정식 표면

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

factory는 borrowed Store를 생성/close하지 않는다. exact Store/catalog와 같은044/049 runtime RLock을 인수하고, None/미구성은 capability를 닫는다. 코어 단위 호출의 RLock/binding은 trusted 직접 입력이며 실제 세션 인증을 증명하지 않는다. backend가 검증한 내부 binding3은 `{host_epoch,session_id,scope_epoch}`의 hex64 strings다. HTTP에서 이 값을 입력받지 않는다.

caller는 정식 `Store.open_existing`으로 연 Store를 전달한다. 코어는 공개 `Store.__enter__`를 비소유 생존 검사로만 호출하고 DB의 경로/device/inode 결합을 확인한다. `__exit__`·043 private binding 접근·Store close를 호출하지 않는다. None 구성은 빈 검토 입력과 함께 허용하며, 입력을 제공하면서 Store/catalog가 빠진 불일치는400이다. 부모043의 알려진 StoreOpenError9도 exact class/code로 보존한다.

read_scope/append_scope는 정확 `"workspace"` 또는 중복 없는 ASCII150 tuple≤100, 기본 빈tuple이다. 입력은 정확 tuple≤100의 exact4 `{intake_id,case_context,validated_response,producer_name}`다. scope/입력은 시작에 고정되고 평문 사본/byte 한도를 확인한다. startup에042 호출·retained 원문/DB 쓰기·Store 생성/연결0이다. 구성된 경우만 정식042 함수를 capture하고 클라이언트가 callback을 고를 수 없다.

review_input_id는 canonical5 `{schema_version:1,intake_id,case_context_sha256,validated_response_sha256,producer_name}`의 SHA다. canonical은 UTF8/ensure_ascii=false/allow_nan=false/sorted dict keys/compact separators이며 배열을 정렬하지 않는다. 입력의 의미/선택 결합은 prepare의 공개042→032가 검증한다. 모델 실행이나 새로운 권한이 생기는 것이 아니다.

## 요청·반환과 수명

| 구조 | 정확 키 |
|---|---|
| capabilities3 | prepare_allowed,append_allowed,review_input_id |
| prepare request3 | schema_version,review_input_id,replace_handle_id |
| prepare envelope6 | schema_version,kind,handle_id,append_request_id,expires_in_seconds,preview |
| append request7 | schema_version,handle_id,intake_id,request_id,preparation_id,expected_snapshot_id,expected_head_record_id |

capabilities의 bool은 현재 trusted scope·구성 입력의 가능 여부이며 준비 readiness나 업무 권한과 합치지 않는다. input ID는 SHA|null, 나머지 ID는 root 부모의 ASCII150/fullmatch 규칙을 따른다. handle은 server random32bytes hex64이며 source권한 토큰이나 preparation SHA로 대체하지 않는다. envelope kind=intake_reference_preparation_handle, expires_in_seconds는 monotonic 양수 남은시간의ceil1..900이고 preview는042 exact11이다. append는042 registration10/append7/verification8 그대로다.

prepare는 예약 후 전역 RLock을 놓고 부모042를1회 호출한다. 부모 C1→032→C2 paired 관측과 reason9/부족/false authority를 그대로 보존한다. 결과를 공개하기 전 deadline/retire/closing을 다시 확인한다. append는 세션·intake·원래 고정 request/expected·Store/catalog 결합을 대조하고 원래 private prepared를042에1회 전달한다. 실제038의 CAS/멱등 등록을 다른 cache나 임의 replayed=true 값으로 대체하지 않는다.

| 상태/사건 | 결과 |
|---|---|
| preparing→정상 | ready/public handle.900초 절대기한을 갱신하지 않음 |
| ready/recorded 명시교체 | old slot credit·미공개candidate, 성공 뒤 원자 publish·실패 때 유효old만 복구 |
| appending/uncertain 교체 | 409·부모0 |
| ready/recorded/uncertain exact append | appending→정상recorded 또는 dispatch뒤오류uncertain |
| 같은 항목 진행 중 | 429/queue0·부모 재진입0 |
| 만료/세션 retire | 비활성 해제/410.진행 값은finally까지 retire_pending |
| close | admission 차단·진행 중503/참조보존→종료후재시도None·반복None |

recorded는 부모가 정상 DTO를 반환한 상태다. 전송 실패의 delivery-unknown은 backend/UI가 별도로 표현하며 미저장으로 단정하지 않는다. uncertain의 원래 handle/request는 명시 재송신으로만042/038에 다시 전달한다. 자동 새ID·재준비·재등록0이다. `discard_session`과 `close`는 준비 메모리만 retire하며 borrowed Store/native pins·세션/cookie를 종료하지 않는다.

## 상한과 오류

입력 context8MiB/depth24/nodes200000, validated response320KiB/depth16/nodes60000·목록 canonical32MiB·항목100을 유지한다. 요청16KiB/depth8/nodes256, preview32KiB·envelope64KiB/depth16/nodes10000, 등록2MiB/depth20/nodes200000이다. host3/session binding당2·각21MiB예약 총63MiB·절대900초를 적용한다. 이는 retained 준비값의 예약이며 RSS나 부모 임시 자료 전체의 한도가 아니다. 부모20MiB 정상 입력을 줄이지 않는다.

새 IntakeReferenceReviewHostError는 prefix `intake_reference_review_host_`와 suffix8 `unconfigured,invalid_request,input_limit,access_denied,review_input_unavailable,prepared_unavailable,request_conflict,unavailable`만 사용한다. status는400/403/409/410/413/429/503의 고정 분류다. cap/unknown/closed는503, busy는unavailable429, expired/missing handle은prepared_unavailable410이다. code/str/args는 같은 고정 code, cause/context=None이다. 허용 부모 고정 class/code만 원형으로 전달하고 raw OS/SQL/path/값은 반환하지 않는다.

## backend 통합과 검증 상태

049가 실제 세션/CSRF 검사와 `_reference_action_binding`·`_reference_parent_call(source=...)`을 소유한다. 같은 source 동시1/queue0·history/current/prepare/append/replay active 감독은 backend에서 적용한다. 종료는 admission 차단→실제 부모finally/active0→actions.close·worker/socket/session회수→host종료 확인→caller043 Store.close 순서다. 코어의 상태 검사를 이 실제 통합 보증으로 올리지 않는다.

신규 코어 전용34개와 전체 Python2014개가 실패/skip0으로 통과했다. Node156개도 실패/skip0이다. 전체2014에는 기존1980과 신규34가 포함되며 별도 합산하지 않는다. source215개는 지정base와 LF 정규화 내용이 같다. 문서 검사는 루트9문서·로컬링크298개, 신규 usage의 UTF8/로컬링크3개를 별도로 확인했다. 이 수는046 코어 자체 검사이며 총괄 독립 인수와 실제049 통합 완료를 뜻하지 않는다.

전용 검사는 genuine043/025/042로 정상 분류5종·038 replay·호스트3/세션결합2·절대900초·32MiB/개별입력 상한·교체/만료/세션 retire 경합을 확인했다. 실제 부모 진입 지점에서 표준 Python profile로 일시정지해 RLock 해제와 active close/finally를 관측했다. SQLite authorizer가 실제 INSERT를 거절한 뒤 uncertain의 같은 handle/request만 재시도·재전송하여 record/event/head가 각1개임을 확인했다. 부모 제품 메서드 교체0이며 시간 제어는046 자체 clock에만 적용했다. 준비 중 genuine 답변 변경은 원래 paired 관측 오류를 보존했다. 16개 사례·256참조·150자 producer도 genuine025 입력으로 준비/등록했다.

새 별도 코어 API 실행은 factory1/capabilities1/prepare1/append3(최초등록1·재전송1·기대값 불일치 거절1)/close2다. 외부025 build1/decode1·043 open_existing1·fixture 생성/파싱/합성 분석은 별도 phase다. prepare는0421→034 C1/0321/038 C2, 최초 append와 replay는 각각0421/0381이며 중첩 호출 수를 top-level 수에 더하지 않는다. startup/capabilities/거절/코어 close에서 DB 연결·SQL·retained 원문 읽기는0이었다.

API의 실제 Python 보존 자료 읽기는 prepare에서 PDF6회/8874B·context6회/10290B·extraction6회/5400B, 최초 append에서 각각8회/11832B·10회/17150B·8회/7200B였다. 원래 bounded read 반환 bytes와 raw locals를 관측했으며 OS/native SQLite I/O 수치는 아니다. metadata 읽기는 별도 기록했고 replay의 원문 읽기는0이었다. 최초 append는038 명시 DDL8개와 SQLite 자동 index5개·record/event/head 각1개를 만들었다. 기본 업무 행/schema·보존 blob은 같고 replay 전후 행/schema/blob·확인한 DB/보조파일은 같았다. 전체 파일시스템 쓰기0을 주장하지 않는다. 코어 close 뒤 borrowed Store가 열려 있고 caller043 close 뒤 실제 DB rename/원복이 가능한 것까지 확인했다.

module 부재 RED·API shell RED와 전체검사 discovery/계측 도구의 원래 실패·수정 전 source·SQL 로그·합성 원본을 private 증거로 보존했다. 원래 parent feasibility의025 외부2/042 prepare2·root0231980/156/7call은 이번 실행으로 재사용하지 않았다. 실제049 auth/session/CSRF·current 교차 source gate·HTTP 전송실패/DOM·configured host shutdown은 미실행이다. 실제 고객/새 원문·모델·장비/현장 검증도 미실행이다.
