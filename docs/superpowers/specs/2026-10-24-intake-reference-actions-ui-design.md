# REFERENCE-ACTIONS-UI-052 고정 설계

2026-10-24 Asia/Seoul. 총괄이 C1 신규4→C2 실제 backend/static/F2 뒤 app3 조립을 선택했다. private v1과 I1/I2/I3 보완 v2의 독립 정적 최종 Yes/C0I0 뒤, 대체된 옛 callback/실패·slot 문장을 제거해 하나의 계약으로 접었다. 아래는 구현·제품 검증 완료가 아니다. 정확 공개 게시base/소유4의 실제 배정 뒤 구현하며 현재049 소유 지적 수정은 별도 담당이 계속한다. C1은 backend 완료를 기다리지 않는다.

## 목적·분리

trusted exact4/동일host A의 명시 **준비→참고 등록→원래 요청 재전송**이다. 새 loader/가짜025·모델·Store·권한·공통registry/session0. 입력 없음은 미구성이며 준비/등록을 시험 착수·규범 승인으로 올리지 않는다.

A1 reader2/context3·050 반환5/private CSRF는 불변이다.052는 **같은 서버 history GET**으로 자기 capability/CSRF만 bootstrap한다. 서버 cookie/session/source1을 공유하고 등록 뒤 A1 metadata만 갱신한다. current 자동0이다.

## 권고 소유·선행

1. C1 신규 `frontend/intake_reference_actions/{actions.mjs,actions.test.mjs,browser_check.cjs}`·`docs/fcc/intake_reference_actions_usage.md` 정확4. 한 feature에 typed/native-fetch/controller/DOM을 두고 고정 계약·A1 의존으로 Node/wire/component DOM부터 게시한다. 실제 backend 완료가 C1 착수 조건은 아니다.
2. C2는 backend 인수/static 제공 뒤 별도 base/배정으로 기존 `frontend/app.js,index.html,styles.css`3과 같은 checker/usage를 연결한다. sibling `#intake-reference-actions-panel`은 A1 뒤/알림 앞·detail replace 밖이다. D1은 자기 host에 keyword2·POST2·cap header·asset1을 추가한다. 현재049/050 공유7은 변경0이다.
3. static `/intake-reference-actions/actions.mjs`→실제 module1/JS UTF8·CSP self. 범용서빙/빈module0.

## 제안 export·상태 노출

export2: `createIntakeReferenceActionsController({onChange,onRegistered})`, `createIntakeReferenceActionsReview(container)`. options는 고정 callback2만, URL/fetch/host/session 주입0이다. controller 반환7 `setContext,setPending,refreshCapabilities,prepare,append,replay,destroy`; action Promise<void>, setter/destroy void다.

view 반환5 `{root,setContext,setPending,refreshCapabilities,destroy}`, controller1/ctor I/O0.

## I1. exact 표시 DTO와 callback

`onChange(state)`는 own enumerable data **정확8**이며 extra/상속/accessor/undefined0이다.

```text
context: null | {intake_id, revision, snapshotGeneration}
phase: 아래 고정 enum 하나
pending: boolean
prepare_allowed: boolean
append_allowed: boolean
preview: null | 042 exact preview11
registration: null | exact registration9
error_code: null | 고정 허용 error enum
```

context는 현재 선택3, pending은 외부 메인pending, 자체busy는phase다. capability bool2는 유효cache 값이며 readiness/위임이 아니다. preview11=`schema_version,kind,intake_id,preparation_id,observation,preparation_ready,reason_codes,review_status,selection,source_modes,verification`. registration9=검증된registration10에서request_id만 제거한 `schema_version,kind,record_id,seq,stored,replayed,binding_status,append_observation,verification`. 불명을 빈 정상DTO로 채우지 않는다.

phase는 `idle,capabilities_pending,unconfigured,preparing,ready,appending,recorded,uncertain,replacement_unknown,prepare_unknown,retired,error`만이다. error_code는 local `intake_reference_ui_invalid_request|intake_reference_ui_unavailable|intake_reference_view_unrepresentable`와 공개backend **exact class/code allowlist**만 허용한다. 미고정/unknown은unavailable, 정상null·prefix일반허용/raw예외0이다.

emit마다 plain DTO를 detached copy/deep-freeze한다(중첩 포함). options/callback·handle/CSRF/request7/append_request_id·비교값/epoch·private context/response/receipt0이다. payload의 원context를 바꾸지 않고 현재context3와 다르면 preview/registration=null. view의 이전 공개 lastgood/context/시각만 stale로 보존하고 다른id/revision은 숨긴다.

constructor I/O/emit0. commit뒤onChange1, 같은valid non-null은no-op·late/destroy뒤parse/emit0. async실패는phase/error_code·Promise<void>종료다. callback throw격리·recorded rollback/retry/rawlog0.

재진입setter는fixed invalid_request throw/action은reject·state/emit/I/O/queue0. destroy만 허용하고 뒤onRegistered를 생략한다. factory invalid options도같은Error다.

## I1. 등록 성공 hook와 C2 event

`onRegistered(capturedContext)`는 **명시append/replay dispatch의 exact context3** detached/deep-frozen 사본만 받는다. 정상registration10/원request 일치 뒤 alive/action ticket·epoch/현재context3 일치/비pending에서 최대1회다. onChange 뒤 재검사하며 throw재호출·secret/handle/request/registration 추가0이다.

view는 `CustomEvent('intake-reference-history-refresh',{detail:capturedContext,bubbles:true})`로 그3만 보낸다. C2의 살아있는패널/main세대·비pending·현재id/revision/snapshotGeneration 일치 때 A1.refreshHistory1만 실행한다. controller ticket검사·다른선택갱신/current/prepare/append자동0.

## HTTP와 bootstrap

후속 backend의 고정 keyword `intake_reference_append_scope=(),intake_reference_review_inputs=()`는046/049 같은Store/catalog/RLock·auth/sourcelease를 쓴다. binding3/epoch는 browser에 노출0이다.

명시 prepare 때 `GET /api/intake-references/{id}/history?limit=1`1회로 bootstrap한다. A1 history7 parser/header를 검증하되 A1 결과를 대신 게시하지 않는다. 추가 header 후보:

- `X-Intake-Reference-Prepare-Allowed`, `X-Intake-Reference-Append-Allowed`: exact true/false.
- `X-Intake-Reference-Review-Input`:046 capabilities3의 ID만 SHA64로 제공. prepare=true는 input/read/CSRF 필수, append=true는prepare=true, false,false,null은input header없음이다. 모순은 unavailable이며 권한 발급0이다.

이후 명시 source 호출은 같은 prefix의 POST뿐이다.

| 동작 | exact body → 결과 |
|---|---|
| prepare | `{schema_version:1,review_input_id,replace_handle_id}`3 → envelope6 `schema_version,kind,handle_id,append_request_id,expires_in_seconds,preview`/preview11 |
| append/replay | `{schema_version:1,handle_id,intake_id,request_id,preparation_id,expected_snapshot_id,expected_head_record_id}`7 → registration10 |

request/expected/head=null은 private 원본 그대로다. revision/generation·UI bool·새ID로 고치지 않는다. replay도 원래7/metadata bootstrap 뒤 POST 최대1·자동 retry0이다. session 비교·기한·결과불명의 전이는 아래 고정 slot/session 규칙을 따른다.

050의 native same-origin/credentials/no-store/redirect error·자기 AbortController/35초를 따른다. bounded stream/BOM/fatalUTF8·중복키/비유한수/surrogate/unsafe lexeme를 검증한다. 요청16KiB/8/256, envelope64KiB/16/10000·preview32KiB, 등록2MiB/20/200000이다(bytes/depth/nodes). reason9/분류5·0/false/null·UTC/KST·false authority를 보존한다. 승인 exact 오류만 전달하고 unknown은 fixed unavailable이다.

## 원래 요청과 마지막 공개 관측

closure의 **원래 준비/요청 slot1개**만 유지한다. 공통 registry/host3·session2 예약을 복제하지 않는다. 같은 접수 ready/recorded의 명시 준비만 replace한다. 다른 접수는replace=null이며 옛 server 예약 해제를 주장하지 않고 cap503을 표시한다. appending/uncertain의 교체·새ID·자동재준비0이다. readiness=false도 원래 정상 분류로 명시 등록하며 capability와 구별한다.

lastgood는 원 context/시각·stale를 유지하고 다른 접수 결과는 숨긴다. countdown은 안내이며 server 절대900초가 최종판정이다. history/append/replay의 연장0, prepare 응답 유실로 모르는 handle의 추측0이다.

## I3. 작업 cache와 occupied slot의 session 비교값

working CSRF/cap cache는 context/pending/실패 때 지워도 occupied slot의 **원CSRF 비교값**·원request7/id/revision/기한은 따로 유지한다.050 cache읽기·새token발급·값/해시/log/storage/DOM0이다.

049 token은 같은session에서 회전0. 유효 bootstrap body/header·최신ticket/context에서만 비교한다.

| bootstrap 관측 | 처리 |
|---|---|
| 원 slot token과 같음 | working cache/cap만 복구; 원 slot/deadline/request7 불변 |
| 유효 token이 다름 | binding 교체로 retired; 원 handle을 새session으로 옮기지 않음; 해당 action의 source 전송0 |
| token 없음·모순 header·조회 실패/403 | 실제session 변경 증거 아님; working cache/cap/source만 닫고 원 slot/unknown 요청 보존 |

cache clear/null/invalid/pending/capability=false만으로 retired/원request삭제0이다. valid bootstrap은 metadata만 복구/source재시도0. 다른valid token/410/서버확정retire/local expiry는 retired로 닫되 공개lastgood/결과불명은 유지한다. 시계안내가 서버절대900초를 연장/대체하지 않는다.

## I2. 준비 교체와 응답 유실

046은 publish/old삭제 뒤 응답한다. **prepare dispatch 뒤** timeout/abort/단절/badwire/late로 정상envelope 미확인이면old-valid복구0.

| 사건 | controller/view 처리 |
|---|---|
| 아직 dispatch 전 local 실패 | 원래 유효 old를 유지; 새 server 작업을 주장하지 않음 |
| 정상 최신 envelope6/preview11 | 새 slot 원자게시, old local 참조 해제; 기한은 새 준비에만 설정 |
| 교체 dispatch 뒤 정상 미확인 | `replacement_unknown`; old private slot은 보존하되 append/replay/replace 모두 닫음; old preview는 공개 lastgood만 |
| old 없는 prepare 응답 미확인 | `prepare_unknown`; unknown newhandle/ID/preview를 추측하지 않음 |
| 검증된 server 오류가 미publish 보장 | 그 고정 allowlist에서만 아직 유효한 old 복구; expired old 복구0 |

미publish 복구 allowlist는 초안에서 **빈 집합**이다. backend exact code/단계보장 공개고정 전 임의400/403/503으로 복구0.410/검증된session변경의 retired가 우선이다.

준비unknown의 자동재준비/retry/예약해제주장0. ‘준비 교체 응답을 확인하지 못했습니다. 이전 준비의 유효성은 미확인입니다’로 표시한다. **별도 ‘새로 준비’**만replace=null로 허용하며 멱등replay가 아니다. 옛/유실예약이 남아 cap503이면 실제expiry를 기다린다. LRU/강제해제·새정상envelope 전old-valid append0이며 append uncertain과 구별한다.

## I3. dispatch·선택/pending·destroy

원slot의 **origin=(id,revision)**과 명시action의 **dispatch context3**를 나눈다. 같은id/revision의 새generation에서 원request7 그대로 replay, 다른id/revision의 원요청append/replay0이다. 새준비는v1/I2 정책만 따른다. callback/event는 새dispatch context3의 최신 일치 조건이다.

| 사건 | 필수 전이 |
|---|---|
| append/replay dispatch 전 실패 | server 등록을 단정하지 않고 원 slot 유지 |
| dispatch 뒤 정상 registration 미확인 | `uncertain`, 원 request7/slot·기한 보존; 자동 새ID/재등록0 |
| dispatch 중 context/null/invalid/pending 전환 | **uncertain 기록→ticket/cache 무효화→abort** 순서; old 원 request 보존, late parse/callback0 |
| 같은 id/revision의 새generation·명시 replay | valid 동일session bootstrap 후 원 request7 POST 최대1; 새generation으로 기대값 재작성0 |
| 다른 id/revision | old내용 숨김/원요청 보존; old append/replay0 |
| destroy | alive/admission/ticket 먼저 terminal→abort→**모든 private slot/token/비교값/참조 폐기**; late parse/callback/event0 |

invalid context/nonbool pending은 context=null/pending=true·cap/cache/ticket닫음·invalid_request emit1. append dispatch는uncertain, prepare dispatch는I2unknown을 먼저 기록/기존unknown유지 후abort하며 그밖에는error다.

destroy멱등·뒤setter/destroy는no-op/action전송0이다. 서버active/commit·미저장을단정하거나 이미전달된본문 삭제를 주장하지 않는다. 폐기뒤handle복원/replay보장0·secret영속저장0이며 새UI는 실제metadata로 durable이력을 확인한다.

고정 한국어: 미구성 ‘검토 입력이 없습니다’; preparing ‘보존자료와 참고 결합 확인 중’; ready ‘검토 준비를 확인했습니다’; 부족 ‘준비 조건 미충족: {열거 사유}’; appending ‘참고 등록 응답 대기’; recorded ‘참고 이력에 등록했습니다’; uncertain ‘등록 결과를 확인하지 못했습니다. 이력 확인 또는 원래 요청 재전송이 필요합니다’; retired ‘준비 만료 또는 연결 변경입니다. 이력을 확인한 뒤 필요하면 새로 준비하세요’.429는진행중/queue0,403은이력재조회다. 분류5/옛시각·textContent/키보드/외부초점을 보존하며 반복동의·secret/다운로드0이다.

## 최소 검증·구현 순서

1. 고정 계약/base/소유 뒤 controller RED→GREEN: I/O0·3/7→6/10·header/budget/UTF8/unsafe·slot/교체·원래replay·uncertain/retired·late beforeparse·35초/abort/destroy.
2. C1 wire DOM의 reason9/분류5·false/KST·키보드390/1440·lastgood/invalid·source자동0·metadata event1·secret/storage/log0. `--mode component`만 제공하고 실제mode는 미구현 때 거절한다. 신규4 게시/독립리뷰.
3. 인수backend+046+050/F2 exactbase의 C2 별도배정 후 genuine025/043 준비와 API를 분리한다. 같은session bootstrap→명시prepare1→append1→원래replay1→DOM, parent042/038/034/032·source bytes/parse0·최초DDL8·row/schema/provenance·replay row1·source1/queue0·expiry/전송불명을 계측한다.
4. browser→host admission 차단→parent finally/active0→actions/worker/session/socket→caller043 close/port/sidecar를 검증한다. A1/050F2·원형intake/Node/문서/핀 회귀 뒤 exact 소유게시/독립리뷰한다. 가짜049·빈실제mode·기존PASS재계수0.

## 고정 의존과 미실행 수용

root027 `985f46bb0e06b43d4e0f4b080de942e84c2f8ea8`의 승인046 source GitLF28642B/SHA `9987684b6e9880409dbe10e390e63188f89d11a9568299fc1b44517025a0e6cb`·usage10080B/SHA `59a1ce515bd554b5382d5a29c79f601f04c98b9e70249f1bcbbce31b9a7a5a9d`를 참조한다. [046 설계](2026-10-24-intake-reference-review-host-design.md), [049 설계](2026-10-24-intake-reference-http-host-design.md), [050 설계](2026-10-24-intake-reference-frontend-design.md), [구현 계획](../plans/2026-10-24-intake-reference-actions-ui.md)을 따른다. backend keyword/header/POST·정적1은 후속 같은host 연결의 계약값이며 이번 C1이 실제049/046 연결 완료를 주장하지 않는다. 미고정 backend 오류는 fixed unavailable로 닫고 prefix 일반허용이나 가짜성공을 만들지 않는다. 원래 비공개v1/v2·No/erratum/최종Yes·F1/F2/실패는 보존했다.

## 추가 수용 (전부 미실행)

- I1: exact8/11/9·unsafe/extra/getter·복사/freeze·throw/재진입/destroy·emit횟수·event3/다른context갱신0.
- I2: publish뒤응답유실과미publish분리·old작업0/unknown복원0·명시null준비/cap/expiry.
- I3: 동일/다른valid/absent/모순token·원slot유지·uncertain-beforeabort·새generation replay원7/다른revision0·destroy폐기/late0/미저장단정0.
