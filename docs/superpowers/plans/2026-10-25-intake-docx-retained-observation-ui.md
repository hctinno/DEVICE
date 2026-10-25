# 보호 source POST DOCX 보존 관측 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 총괄의 정확 base·전용 branch 실제 배정 뒤 담당이 직접 구현하며 하위 agent를 만들지 않는다. 공개 설계와 기존10 소유는 고정했고 readonly API 독립 제품 인수와 실행 배정이 남아 있다.

**Goal:** 명시 단일 retained DOCX를 기존 보호 current POST로 새로 admission하고 원 exact6을 현재 접수의 읽기 전용 관측 구역에 표시한다.

**Architecture:** host가 actual artifact ID/exact5 binding을 고정한다. 기존 history의 선택 안내 헤더→기존 token closure→tagged current POST→`_request_call(source=True)`→D1 API1→UI 표시 한도→원 exact6 bytes→tagged client parser→현재 파일 결합/DOM 순서다. metadata GET body·042 current·reference view·D1 envelope는 그대로다.

**Tech Stack:** 기존 Python HTTP/official borrowed Store/stdlib canonical JSON, 기존 JS transport/model/app·bounded stream/AbortSignal, 기존 tests/browser checker와 CSS. 새 module/framework/provider/endpoint/CLI0.

**Spec:** [보호된 current POST DOCX 관측 설계](../specs/2026-10-25-intake-docx-retained-observation-ui-design.md), [D1 readonly admission 설계](../specs/2026-10-25-intake-docx-retained-observation-design.md). 원 정적 제안·독립 검토·실패 증거는 private에 보존한다.

## Global Constraints

- 실제 배정 전 제품/test/fixture/API/DB/HTTP/browser/branch/Git 변경0이다. 아래 checkbox는 실행 결과가 아니다.
- 기존7에 추가3 transport/model/transport.test를 포함한 아래 기존10 소유를 고정한다. 기존 reference view/model.test·C1/C2·CSS/CSP/ASSETS/Store/D1 core는 임의 수정하지 않는다.
- full exact6/native text는 일반 metadata GET·history body에 들어가지 않는다. 보호 POST의 source 인증과 lease를 각각 지킨다.
- request exact2 action current는 원042로, 새 action docx_retained는 D1 원6으로 별도 분기한다. source 선택 ID/path/body/limits는 browser 입력0이다.
- 고정 선택 None의 추가 import/API/SQL/native/헤더·키/구역/버튼/source 요청0이다. source 요청은 버튼으로만 실행하고 parent admission은1회다.
- D1 artifact9MiB/receipt10MiB 유지, UI canonical2MiB/depth64/value nodes200000/native 구조2000/issues128 별도다. native 재파싱·retention/register/DB 쓰기·절단/빈 성공0이다.
- 원 a6a0/4059/No·74/cold/grammar/gap/UIv1과 큰 proof payload는 보존한다. 기존10053 조사·무관 전체검사·재시도/sleep/drain 변경을 끌어오지 않는다.

## Review Focus

1. source HTTP auth는 Origin/Host/Sec-Fetch/session/CSRF/read scope이고 프로그램 lease·선택 헤더·metadata GET이 대체하지 않는다.
2. 기존042 closed body와 default transport/view의 exact 형상·동작을 지키며 DOCX 요청과 응답을 자동 추측하지 않는다.
3. request 동안 새 admission한 물리 관측·현재 metadata·native 선언/분석/인용을 구별하고 이전 결과를 새 현재성으로 만들지 않는다.
4. canonical byte·value-node/depth·native 구조/issue count를 정확 경계/+1과 unknown/unmappable로 검증한다. 기존 depth20/key-node는 그대로다.
5. source lease 밖에서 caller Store를 닫지 않으며 source 동시429·close/drain·실패/지연/BFCache/C2 pending·last-good을 실제 관측한다.

## Task 1: 공통 배선과 정확 소유 확정

- [ ] **U0:** wire action/선택 헤더/constructor/오류와 기존10 소유는 공개 설계로 고정했다. 고정 공개 D1 spec/plan을 확인하고 실제 readonly API의 독립 최종 제품 인수·정확 최신 base/전용 branch 실행 배정을 받는다. 담당의 이전 branch를 임의로 base로 선택하지 않는다. finding과 원 실패를 먼저 처리하고 과거 정적 제안·검토 기록을 보존한다.

**확정한 제품 소유 기존10:** 기존7 `labflow/ui_server.py`, `frontend/model.mjs`, `frontend/app.js`, `tests/test_ui_server.py`, `frontend/model.test.mjs`, `frontend/intake_references/browser_check.cjs`, `docs/fcc/frontend_usage.md`; 추가3 `frontend/intake_references/transport.mjs`, `frontend/intake_references/model.mjs`, `frontend/intake_references/transport.test.mjs`. 세부 변경은 공개 설계와 아래 task를 따른다. 소유 확대가 필요하면 구현 전 총괄이 정확한 차이를 고정한다.

## Task 2: actual admission을 호출하는 최소 host

- [ ] **U1 RED:** 실제 새 합성 OOXML→기존 retention→actual receipt ID/binding을 준비한다. 공식 borrowed Store로 D1 readonly API가 실제 인수된 상태임을 확인한 뒤, 기존 `tests/test_ui_server.py`에서 새 constructor 선택·선택 헤더·tagged POST 부재의 RED를 남긴다. 예상 hash/수동 native/receipt를 genuine 입력으로 만들지 않는다. no-input과 source auth 실패를 별도 원인으로 관측한다.

- [ ] **U2 GREEN:** `intake_docx_reference_selection=None`/exact tuple2를 생성자에 추가한다. None은 기존 경로에 추가 parent/import/I/O/응답을 만들지 않는다. explicit 선택만 exact5를 detach하고 official Store/root/readscope/intake와 public 함수/error class를 준비한다. D1은 생성자가 아니라 허가된 source 요청에서만 호출한다. before-bind 형상/root/scope/publicAPI 오류·caller Store 보존을 검사한다.

- [ ] **U3 GREEN:** 기존 history body와 metadata GET body를 보존하고 selected+read_allowed일 때만 `X-Intake-Reference-Docx-Selected: true`를 붙인다. session 생성/만료·HEAD·cookie Path·CSRF/readscopecap은 기존 그대로다. 헤더에 ID/path/native/시각을 넣지 않는다. 선택 안내를 위한 추가 SQL/D1/source0을 관측한다.

  `_reference_body`는 current exact2를 유지하며 `action='docx_retained'`만 명시 추가한다. `_reference_dispatch`는 공통 source guard/auth/wire 제한 뒤 request.action으로 분기한다. legacy current는 원 parent/원 exact10이다. DOCX는 선택 intake 일치 확인 후 `_request_call(...source=True,action=None)` 안에서 public `read_retained_intake_docx_reference(runtime.store, fixed_id, expected_binding=copy)`를1회 호출한다. `_reference_response`의042 validator에 원6을 통과시키거나 extra key를 붙이지 않는다.

  D1 exact error class/9code만 새 분기의 spec 표대로 매핑하고 기존 parent mappings를 넓히지 않는다. 다른 intake·미공급은 auth 이후503 unconfigured/parent0이다. serialized 원6은 위 lease 안에서 검사·준비해 bytes로 send하고 예외 때 lease를 반환한다. body 시작 이후 두 번째 frame0이다.

- [ ] **U4:** UI 형상/한도를 host에 추가하고 원9MiB/반환10MiB를 바꾸지 않는다. 기존 Store canonical 규칙·원6/node/depth·구조 paths/issues128을 검사해 cap은 UI413, unmappable/불가형상은 UI503으로 거절한다. 초과가 HTTP 전송/renderer 전에 실패함을 확인하고 raw 값/오류를 빈 성공으로 바꾸지 않는다. 기존042/context/history의 전역 한도를 변경하지 않는다.

  실행은 실제 배정 뒤 정한 DOCX host 관련 test selector 및 영향을 받는 기존 current/history/source-lease/close case로 한정한다. 모든 실패/skip·원 RED·관측기 오류를 결과와 구분한다.

## Task 3: 기존 transport/model과 앱 상세 연결

- [ ] **U5 RED→GREEN transport:** `transport.mjs`에 선택 헤더의 typed private flag와 `hasRetainedDocxSelection()`을 추가한다. closure 반환 집합6 변경은 `transport.test.mjs`의 원 factory exact5 단언만 의도된6으로 갱신하고, 기존 history 반환 exact2·생성 인자0·default current exact2는 그대로 검사한다. malformed/contradictory 선택 헤더, 다른 context/secret/403/session 만료/pending/destroy에 true가 남으면 실패다.

  `readCurrent(id,signal,kind='current')`의 새 literal만 같은 POST에 직렬화하고 token/CSRF는 기존 closure에 둔다. getter/선택 안내 없이 DOCX fetch0, 잘못된 literal/extra selectors 거절, source kind 양쪽의 secret clear, 35초·2MiB stream·중단/finally·Cookie/Origin 직접 설정0을 검사한다. 새 endpoint/토큰 저장소/자동 source 재조회는 없다.

- [ ] **U6 RED→GREEN model:** `intake_references/model.mjs`의 기존 export 집합과 default parser를 유지한다. `parseIntakeReferenceCurrentJson(raw,id,kind='current')`의 DOCX tagged branch에서만 원 exact6/4/11·full binding·native 구조·safe integer/Unicode·raw UTF8 2MiB/depth64/value nodes200000/구조2000/issues128을 검사한다. 기존 depth20/keys-counting parser를 전역 확대하지 않는다. numeric object keys·nonBMP·escape/-0·중복키를 검사하되 새 JS canonicalizer는 만들지 않는다. server의 canonical byte 생성은 별도 Python/HTTP oracle로 비교한다.

  기존 `frontend/model.test.mjs`에는 이 접수 기능의 DOCX tagged 원6 및 current record 결합 검사를 추가한다. 기존 reference model.test는 수정하지 않고 기존042 export/current/context 회귀로 선정 실행한다. host/server와 parser의 예산 경계 oracle는 서로의 생산 helper를 정답으로 재사용하지 않는다. native unknown 선언과 unknown/unmappable block 구조를 구분하고 오류를 native failure로 바꾸지 않는다.

- [ ] **U7 RED→GREEN DOM:** `app.js`의 기존 history 연결만 bridge하고 ref view options/DTO는 바꾸지 않는다. 선택 true일 때만 기존 history raw 검증 뒤 captured context에 DOCX 버튼/구역을 off-DOM 준비한다. false/default에서 추가 JSON parse·placeholder/구역·source0이다. `frontend/model.mjs`의 순수 source/intake/revision/full fingerprint/doc path-SHA-bytes 결합 helper로 새 source 원6과 현재 record를 비교한다. 전체 analysis hash를 요구하지 않는다.

  click→새 literal source request→tagged parser→원 값 보존→검증된 구역 원자 게시를 잇는다. native 본문을 quote/fact/HTML/링크로 만들지 않는다. reader/status/complete·artifact/provenance/locator/page unavailable·현재 jobs/unread를 구별한다. 새 timestamp나 authority DTO0이다. 원6과 details·last-good은 현재 app context/ticket에만 결합하고 성공한 선택 소멸·다른 revision·late/render 실패·C2 pending/BFCache/terminal/destroy에서 spec의 상태 표를 따른다. 분석만 바뀌면 이전 관측으로 유지할 수 있으나 새 현재성으로 바꾸지 않는다.

  browser checker에 새 선언 wire/mutation을 별도 mode/분모로 추가한다. 실제 source getter/header/token/wire와 ordinary GET source0을 확인하고 기존 F1·intent/C1/C2 요구를 유지한다. 기존 view.mjs/options/export/legacycurrent10은 변경0이다. keyboard/390/1440·focus/hash/storage·long Unicode/HTMLURI text를 검증한다.

## Task 4: genuine chain·자원·인계

- [ ] **U8:** 새 private evidence에서 실제 synthetic retention/blob/등록→D1 readonly API→실제 session/Origin/CSRF source POST→DOM1440/390을 관측한다. 원 artifact bytes/SHA/registry provenance·reference binding/native locators·HTTP canonical 원6을 독립 비교한다. ordinary metadata/history body에 원6/native text0, no-input extra0, DOCX request exact2·browser selector0, source API1/native parser0/write0을 실제 계측한다.

  정상/partial/empty/native 실패는 실제 retention이 생성한 저장 관측으로 검사한다. unknown 선언·unmappable 형상·정확 JSON 예산 경계의 선언 wire/memory mutation은 별도 분모이며 실제 retention 성공으로 세지 않는다. 실제 출력으로 만들 수 있는 byte/구조 cap 초과는 별도 genuine 거절로 관측한다. stale/current provenance 변화·source/artifact 무결성·session/CSRF/Origin/readscope 실패·다른 intake·source429·선택소멸·지연/last-good을 원인별로 검사한다. parent API와 실제 source I/O/SQL, metadata SQL, C2, observer를 분리한다. 큰 옛 payload/312 proof를 재실행하거나 native 재해석으로 읽기 성공을 만들지 않는다.

  실제 source lease 보유 중 close 진입·new source 거절·부모 완료/first error·active0 뒤 host drain/caller Store.close 순서를 확인한다. browser timeout/abort 뒤 실제 부모 수명과 전달 불명을 구별한다. close 자체 미수행·강제 kill을 정상 회수로 세지 않는다. actual callable/control/native 자원 경계는 기존 D1와 HTTP 계약 각각의 분모로 보고한다. 실제 OS Ctrl+C/고객/AI/현장/Word 검증으로 확대하지 않는다.

  합성 원6/native 본문·cookie/CSRF/token·원 request7·SQL문/params는 공개 Git/일반 보고에 복사하지 않는다. 새 private 관측의 실제 I/O와 인증 형상·카운터만 공개 인계하고 원 실패를 보존한다.

- [ ] **U9:** usage에 실제 constructor와 action/header/error·source 권한·원 관측/현재성/native 선언/unread 한계를 적는다. 새 전용 검사·관련 legacy 회귀·좁은 exact candidate cold genuine을 실행하고 raw/GitLF/원 RED/실패·실제 count·resource/문서 무결성을 구분한다. `python scripts/check_artifacts.py`·소유 diff/작은 pins·HEAD/clean/remote를 확인한다. root의 별도 commit/push/독립 제품 리뷰·finding 수정/통합 절차를 따른다. 이전 owner/root/독립 pass를 합산하지 않는다.

## 현재 상태

공통 설계와 기존10 소유는 고정했다. U0의 readonly API 독립 제품 인수·정확 실행 base/branch 배정과 U1~U9 제품 구현·검증은 아직 미실행이다. 원 정적 제안·독립 검토·실패는 보존한다. 사용자 준비나 모델 공급자 선택을 새 선행조건으로 두지 않는다.
