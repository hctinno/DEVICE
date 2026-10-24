# REFERENCE-ACTIONS-UI-COMPOSITION-052 C2 고정 설계

2026-10-25 Asia/Seoul. 독립 정적 Yes/C0I0인 C2 최소 계약을 공개 경로로 정리한 준비본이다. 기존 수용20개와 API를 유지하며 R1의 guard 해제 시점만 명시한다. C1과049는 통합029에서 인수됐다. 050 F2는 root031 `1f17e0a764f9cc2e4b41f17869ede04a992802d7`에서 독립 최종 Yes/C0I0 뒤 최종 인수·게시됐고 새 Node230·관련 HTTP Python58·DOM12가 통과했다. 053 후보 `5eee86b4f1baf029bf99bb73fd59f0278bbda836`는 독립 최종 Yes/C0I0 뒤 root032 기능 `b29237126d119ed18db85ae4654f6caae9f96b47`에 인수했고 새 전체Python2242/skip0·기존화면 실제HTTP/DOM12가 통과했다. 이번은 문서/정적 대조뿐이며 C2 제품·fixture·브라우저 실행0이다.

[공개052 설계](2026-10-24-intake-reference-actions-ui-design.md)·[계획](../plans/2026-10-24-intake-reference-actions-ui.md), [050 계약](2026-10-24-intake-reference-frontend-design.md), [A1 공개 API](../../fcc/intake_reference_ui_usage.md)를 소비한다. 053은 정확 게시 `ed6b50e0be3d7526946d0d4bc02c480492988a44`의 `docs/superpowers/specs/2026-10-25-intake-reference-actions-host-design.md` 12019B/SHA256 `57668de3edaed4b6436e6bfaee2af9c0d41bd30ddddbef9b2e06a9d8b09c8c82`, 같은 plans의 `2026-10-25-intake-reference-actions-host.md` 7465B/`7f3be4037fa7301701c45e9cfe594907f629d53bb5fea313162c9161d133629f`다. [053 공개 설계](2026-10-25-intake-reference-actions-host-design.md)·[계획](../plans/2026-10-25-intake-reference-actions-host.md)을 소비하며 공개 계약의 게시와 제품 인수는 구별한다.

## A안과 착수 조건

리드가 권고한 A안은 기존 app에서 A1 reader·050 transport·C1 view를 각각 1개 만들고 공개 setter와 등록 이벤트만 연결하는 것이다. 별도 facade/controller 중복 생성은 슬롯·세션 경계를 늘리고, 050 private CSRF 재사용은 공개 API 밖이므로 채택하지 않는다. 새 화면 구조나 상태 framework는 만들지 않는다.

구현은 리드가 **accepted050 F2 + accepted053의 같은 host·실제 static1**을 포함한 정확 root base와 미래 소유5를 별도로 실제 배정한 뒤다. C1/049의 통합029 인수만으로 C2를 시작하지 않는다. 상태 확인용 게시점 `160732c896322cc79755d7d91ad6e6f1e43c6db9`는054가 포함된 기존 게시점이며055 또는 미래 C2 실행 base를 뜻하지 않는다. C2 실행 base는 아직 미정이다. 그 전 제품·새 branch·cherry-pick·공개 파일 변경0이며 선행 blob 차이는 임의 결합·수리 없이 리드에게 보고한다.

| 미래 소유 — 별도 실제 배정 후 정확5 | 책임 |
|---|---|
| `frontend/app.js` | C1 view1·문맥/pending·event→A1 이력·수명 연결 |
| `frontend/index.html` | A1 뒤·알림 앞의 sibling `#intake-reference-actions-panel`; detail replace 밖 |
| `frontend/styles.css` | `.reference-actions-review` 아래 제품 스타일·390/1440·초점·줄바꿈 |
| `frontend/intake_reference_actions/browser_check.cjs` | 기존 component 보존, 별도 genuine integrated 검증 |
| `docs/fcc/intake_reference_actions_usage.md` | 실제 실행/미실행·증거·한계 갱신 |

C1 actions.mjs/test, A1 model/view/test, 050 transport/test/기존 checker/usage, backend/core/Store/schema·부모·공유 대장·CSP는 보호한다. 이 밖의 수정이 필요하면 소유 밖 변경으로 보고하며 다섯 파일에 억지로 우회 코드를 넣지 않는다. 독립 F2 지적이 도착하면 기존050 소유 수정을 우선 처리한다.

## 공개 연결 경계

| 소비 표면 | C2 사용 | 넘기지 않는 값 |
|---|---|---|
| A1 `validateIntakeReferenceContext(value)` | 선택 fallback 후 `{intake_id,revision,snapshotGeneration}` 또는 null 검증 | DOM에서 읽은 ID·추측 revision |
| 050 `createIntakeReferenceTransport()` / 반환5 | reader2를 A1 options의 정확2키로 전달, 공개 setter/destroy 호출 | transport spread·private CSRF/cache |
| A1 `createIntakeReferenceReview(container,{readHistory,readCurrent})` / 반환5 | 기존 문맥/pending/명시 current 유지, 등록 후 `refreshHistory()` | current 자동 실행·준비 DTO 주입 |
| C1 `createIntakeReferenceActionsReview(container)` / 반환5 | view1 생성; root/setContext/setPending/destroy 사용. capability는 기존 명시 버튼 사용 | 별도 controller·fetch/origin/session 주입 |
| C1 공개 state8 | 기존 C1 view만 표시. app에 getter/callback option을 추가하지 않음 | handle·원 request7·request_id·private 응답 |
| `intake-reference-history-refresh` detail3 | 실제 C1 root에서 현재 문맥의 A1 metadata만 1회 갱신 | registration/preview/CSRF·새 권한 |

state8은 `context,phase,pending,prepare_allowed,append_allowed,preview,registration,error_code` 그대로다. 공개 preview11/registration9·사유9/분류5·0/false/null·원 UTC/KST·오래된 관측·결과불명 안내는 C1 렌더링을 그대로 사용한다. app이 DOM을 다시 파싱하거나 bool로 실행 권한을 만들지 않는다. capability는 C1의 명시 조회 및 준비/재전송 내부 bootstrap이 담당한다. app의 자동 capability/current/prepare/append/replay/retry는 0이다. production025 입력 미제공 시 false/false·입력 없음과 ‘검토 입력이 없습니다’를 그대로 표시하며 producer를 만들지 않는다.

## 문맥·pending·등록 이벤트·수명

1. app의 기존 `prepareView`가 fallback 선택과 검증된 context3를 만들고 DOM/state를 게시한다. 짧은 동기 게시 guard 안에서 C1→050 transport→A1에 같은 context를 전달한다. 같은 유효 context는 no-op이며 검색/필터 렌더마다 재생성·capability 재조회하지 않는다. 비밀 대신 기존 main 문맥·pending·alive/suspended와 동기 guard만 사용한다.
2. main refresh 시작 시 app pending을 먼저 닫고 C1 pending true→050 transport true→A1 true 순으로 전달한다. C1이 전송 중 등록을 불명으로 기록한 뒤 자기 abort를 수행하는 의미를 보존한다. 새 main request 이전 응답/finally는 세대를 검사해 모두 무시한다. 최신·살아있음·비suspended인 finally만 050 false→C1 false→A1 false로 풀고 app guard를 마지막에 연다. 목록 실패로 context/generation을 새로 만들지 않는다. A1의 새 문맥 metadata 최대1회 규칙을 바꾸지 않는다.
3. 이벤트 listener는 C1 root에 1개만 둔다. alive·root 연결/정확 target·비pending·비suspended·guard 밖을 먼저 확인한 뒤 A1 검증기로 detail exact3와 현재 main context3의 세 값 전체를 비교한다. 통과한 이벤트에 guard를 닫고 A1.refreshHistory만1회 호출한다. C1 notifying은 onRegistered와 전체 DOM bubbling이 끝날 때까지 true다. 따라서 guard는 자기 root listener 반환 때 열지 않고 뒤쪽 bubbling listener 동안에도 유지하며, end-of-stack microtask에서만 해제한다. microtask는 살아있는 guard 해제만 수행하고 이벤트 queue/replay/source 작업은0이다. 잘못된/옛/추가키/getter 문맥은 raw 값 없이 무시한다. CustomEvent를 쓰기 권한 증거로 취급하지 않는다.
   R1 routine 결정: guard 중 selection/main refresh/pending 진입은 앱의 main state·request·DOM 게시 또는 C1 setter 호출 **이전**에 return한다. 일부 main 문맥만 바꾼 뒤 C1의 재진입 오류를 받는 split context/pending을 허용하지 않는다. terminal destroy는 예외로 alive와 listener를 먼저 닫고 C1 destroy를 호출할 수 있다. terminal 뒤 microtask는 guard나 UI를 되살리지 않는다. 새 getter/callback/tokenstore/provider/framework는 없다.
4. 같은 id/revision의 새 generation에서 원래 replay는 C1의 명시 버튼과 원7이 담당한다. 다른 id/revision·pending·late 성공은 다른 선택의 이력을 갱신하지 않는다. 등록 불명·교체 불명·retired 뒤 과거 결과불명 메모를 app이 지우거나 미저장으로 바꾸지 않는다. 알림 화면에서는 두 패널의 표시만 숨기고 재생성/슬롯 폐기/초점 이동하지 않는다.
5. persisted pagehide는 app suspended/pending을 먼저 닫고 위 true 순서를 적용한다. pageshow는 기존 main refresh만 수행한다. 일반 pagehide는 alive를 먼저 닫고 listener 제거→C1 destroy→050 transport/A1 destroy다. main late finally/이벤트의 후속 호출은 0이다. destroy 뒤 슬롯 복구나 서버 미저장을 보장하지 않는다.

## 실제 연결 검증 경계

[아래 수용표](#c2-acceptance)와 [구현 계획](../plans/2026-10-25-intake-reference-actions-ui-composition.md)을 따른다. 준비 P0의 기존 public025 `build_case_review_context/decode_case_review_response` 합성 context/validated response, genuine043 Store와 catalog를 쓰고, 053이 공개 exact4를 받도록 한다. 새 provider/loader나 고객 원문을 만들지 않는다. HTTP 실행은 실제049/053 같은 loopback port0이며 Node proxy·ASSETS adapter·가짜 부모 성공·이전 result 재생은 0이다. 실제 원문/모델·실장비·기관 적합성·전체 시험소 완료는 전부 미실행이다.

## C2 acceptance

기존 수용20개는 모두 미래 미실행이다. D는 실제 앱 DOM, G는 genuine049/053 HTTP+DOM, F는 명시 fault, R은 회귀다. D/F와 정상 G, P0 준비와 P1 HTTP, 이전 PASS와 새 실행을 합산하지 않는다. 현재 제품 시험0이다.

| ID / 종류 | 입력·사건 | 미래 수용 결과·보존 증거 |
|---|---|---|
| C2-01 / 착수 | C1/049·F2(root031 1f17e0a)와053(root032 기능b2923712) 독립 최종Yes/인수·새Python2242/DOM12 완료 | accepted053/static1·정확 최종root base/소유5 별도 배정 전 제품/branch0. 현재1f17e0a와 기존160732c를 미래C2 base로 승격0. 원 branch·No/RED/cold 보존 |
| C2-02 / D | 실제 `/`·static4·mount | 실제 C1 root1/controller1, A1 뒤·알림 앞/detail replace 밖. C1 constructor API I/O0·재렌더 재생성0. 기존 main/A1 metadata는 별도 계수 |
| C2-03 / D | 선택 fallback·같은 context·새 generation·다른 revision/null | 검증 exact3만 동일 전달. 같은 valid no-op, 다른 선택의 결과 숨김·옛 이벤트 metadata0. DOM scrape0 |
| C2-04 / D | main1 지연/finally 뒤 main2 pending·목록 실패 | 최신 request만 해제. 실패로 generation/context 생성0, A1 queued metadata 최대1·source0, C1 불명 보존 |
| C2-05 / D | 현재 event3·다른 root/옛세대/추가키/getter | 현재 root·alive·비pending·exact3만 history+1. 나머지0; current/prepare/append+0·raw 오류/secret0 |
| C2-06 / D | root listener 뒤의 bubbling listener가 다른 접수 선택 버튼.click()과 #refresh.click()·pending 진입을 동기 실행; terminal destroy 별도 | guard가 microtask까지 닫혀 main state/request/DOM·문맥/pending 분리0·C1 setter/action0. 현재 이벤트 자체의 metadata1과 재진입 delta0을 구별. microtask는 해제만/queue·replay·source0. terminal은 alive/listener를 닫고 C1 destroy 허용·이후 metadata/parse/emit/focus0. callback 예외로 등록 rollback0 |
| C2-07 / D | persisted pagehide/pageshow·일반 폐기·늦은 main finally | BFcache는 pending→기존 main refresh만. 일반은 alive닫기/listener제거/destroy, 이후 호출0·자동 source0 |
| C2-08 / D | 0/false/null·사유9/분류5·옛시각/긴ID·unresolved retired | 원문 literal·raw UTC+KST·‘이전 관측’/불명 메모 유지. readiness/등록을 업무·시험 권한으로 표시하지 않음 |
| C2-09 / D | 390/1440·키보드·외부초점·알림 탭 | 가로 overflow0, controls wrap·focus visible·실제 버튼 조작. 자동 focus0, 탭 전환 시 패널 숨김만·슬롯 재생성0. 화면 PNG |
| C2-10 / G | None·inputs=()·append 기본거절·production025 미제공 | None/입력 없음은 capfalse/false·input 없음·고정 미구성·prepare/append POST0. 별도 genuine 합성 입력+read 허용/append 기본()는 true/false·명시 prepare만 가능/append0. 자동 current0·앱/provider/Store 임의 생성0 |
| C2-11 / G | genuine025 합성 exact4·043·같은 browser cookie | history bootstrap→명시 prepare1/append1/replay1. body3/7·envelope6/registration10→공개11/9. 원7 동일 bool·이력 row1/replay 추가쓰기0·fresh current0 |
| C2-12 / G+F 분리 | append 뒤 같은 id/revision 새generation·다른 id/revision | 새 dispatch context3 이벤트만. 원7 기대값 불변·원래 replay≤1; 다른 origin old append/replay0·옛 결과 숨김 |
| C2-13 / F | 실제 append/commit 뒤 응답 유실·늦은 성공·세션 만료 | uncertain-beforeabort, 미저장 단정/새ID/자동등록0. 유효 동일session이면 원래 replay로 durable 이력 대조, 변경/만료면 이력 확인만. retired 뒤 과거 불명 메모 유지 |
| C2-14 / F | 실제 prepare 교체 뒤 응답 유실·old 없음 | replacement_unknown/prepare_unknown 구별. old 유효 복구0·별도 새로 준비 replace=null만. 남은 예약/cap503 숨김0 |
| C2-15 / G+F 분리 | 동일 token·다른 valid token·absent/모순·만료/410 | 원 slot과 workingcache 구별은 C1 그대로. valid 변경/410은retired, absent만으로 세션변경 단정0·기한 연장0. token 값/hash 기록0 |
| C2-16 / G | 정상 binding5·준비 부족·동시 head 변경 | 정상분류5 모두 typed 정상, readinessfalse/0/null과 false authority 보존. head_conflict를 미저장 오류/새자동등록으로 바꾸지 않음 |
| C2-17 / G | current/prepare/append/replay source 동시 진입·취소 | 공용source1/queue0·고정busy, 부모 finally 전 선반환0. metadata는 source0. pass-through 실제부모 trace와 bytes/read·parse0 분리 |
| C2-18 / G | active 중 close·abort·정리 실패 | admission닫기→parentfinally/active0→actions.close1/None→worker/socket/session→caller043close. native handle/port/sidecar 회수, 실패 보존 |
| C2-19 / R | 배정 base의 Node·A1·050 F1/F2·원형intake/기존조회·계산 | 새 phase/정확 소스핀으로 실행. C1 210/23/18·root2092 같은 이전 수를 새 검사수에 합산하지 않음 |
| C2-20 / R | 정적경로/MIME/CSP·악성wire·비노출·문서/핀 | 실제asset4와 alias/미존재404·securityself. DTO 외 handle/원7/CSRF/cookie/private 원문은 DOM/storage/URL/log/download/영수증0. 소유5외 원본/DB/provenance 불변·UTF8/링크·회수 영수증 |

P0 준비와 P1 HTTP의 SQL/DDL·보존 자료 읽기·파싱 분모를 분리한다. metadata source0는 기존 metadata SQL0이라는 뜻이 아니다. 정상 G는 실제 부모를 통과하고, F는 전송만 명시적으로 유실/지연시키며 가짜 응답·provider·ASSETS/독립 proxy로 성공을 만들지 않는다. 전체 Python/정상 분류별 실제 재현·회수는 실행한 것만 세고 나머지는 미실행으로 남긴다.
