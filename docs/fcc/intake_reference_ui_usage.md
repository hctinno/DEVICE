# 접수 참고 이력·현재 조회044 A1 / 프런트엔드050 F1·F2

인수된044 A1 구성요소를 기존 접수 화면의 별도 형제 패널에 연결했다.050 F1은 native fetch 전송 모듈과 제품 app/index/styles를 명시 wire fixture로 검증하며, F2는 정식049 서버·043/042→HTTP→DOM을 별도로 검증한다. [044 설계](../superpowers/specs/2026-10-24-intake-reference-ui-design.md)·[계획](../superpowers/plans/2026-10-24-intake-reference-ui.md)의 A1 API를 보존하며, [050 설계](../superpowers/specs/2026-10-24-intake-reference-frontend-design.md)·[계획](../superpowers/plans/2026-10-24-intake-reference-frontend.md)의 소유7 범위만 변경한다. 실제 고객 DB/PDF·모델·현장 장비는 실행하지 않는다.

`model.mjs`는 상수 `INTAKE_REFERENCE_VIEW_MAX_BYTES=2097152`와 `validateIntakeReferenceContext`, `parseIntakeReferenceHistoryJson`, `parseIntakeReferenceCurrentJson`, `createIntakeReferenceGate`를 공개한다. parser는 exact history7/current10과2MiB/depth20/key+value nodes200000을 검사해 detached DTO를 반환한다. 잘못된 입력은 `invalid_intake_reference_view`, Number로 정확하게 표현할 수 없는 정수는 `intake_reference_view_unrepresentable`의 고정 Error다. 부모 SQLite63bit를 반올림·잘라내기·빈 성공으로 바꾸지 않는다. A1 raw string의 Unicode/JSON·UTF8 크기를 검사하며 실제 wire의 fatal UTF8 decode는 A2 transport 소유다.

`createIntakeReferenceReview(container,{readHistory,readCurrent})`는 정확 `{root,setContext,setPending,refreshHistory,destroy}`를 반환한다. context는 null 또는 정확 `{intake_id,revision,snapshotGeneration}`이며 ASCII intake ID1..150/양의 safe revision/0이상의 safe generation이다. setter 오류는 기존 결과를 보존하면서 active/queued context·pending 새context 표식과두ticket/허용을닫고 추가호출을 막는다. destroy는 멱등·종료상태이며 자기root를분리한다.

trusted `readHistory(intake_id,{limit:20,before_seq:null|safeint},signal)`은 정확 `{raw_json:string,read_allowed:boolean}`, `readCurrent(intake_id,signal)`은 raw current JSON을 반환한다. secret·CSRF·cookie·세션·HTTP 경로는 이 구성요소에 전달하지 않는다. 새 context의 자동 이력은 metadata만 읽고, 현재 조회는 정상 history가 허용을 표시한 후 사용자의 명시 버튼 한 번만 실행한다. pending 중 새 context는 한 개만 보관하고 해제 후 이력 최대1회, invalid context 뒤에는 옛 조회가 되살아나지 않는다.

이력/현재는 독립 ticket·AbortController·lastgood를 갖는다. 문맥·판본·generation 변경 뒤 늦은 성공/실패는 파싱·게시·초점 변경 전에 거절한다. 마지막 정상값·0/false/null·source_modes를 보존하고 기존 등록 당시 일치와 새 관측 시각을 구별한다. 현재 unavailable/none/current/stale는 원래의 업무 상태다. 자동 이력은 초점 이동0, 사용자가 옮긴 초점을 결과가 빼앗지 않는다. 잘못된 응답/표현 한계는 고정 오류와 이전 결과로 남는다. 원문 값·quote·private receipt·JSON 다운로드는 추가하지 않는다.

검증 명령:

```powershell
node --test frontend/intake_references/model.test.mjs
node --test frontend/intake_references/transport.test.mjs
node frontend/intake_references/browser_check.cjs
node frontend/intake_references/browser_check.cjs --mode frontend
node frontend/intake_references/browser_check.cjs --mode integrated
python scripts/check_artifacts.py
```

무인자 checker는 기존 A1의 전체 합성 DTO·trusted callback 경로18검사를 유지한다. `--mode frontend`는 자기127.0.0.1 port0의 정적 allowlist와 실제 제품 app/index/styles·A1·transport를 사용한다. API 응답은 브라우저 native fetch 경계에서 제공하는 명시 wire fixture이며, 서버의 session/cookie/Store/provider를 구현하거나 대신하지 않는다. `--mode integrated`는 아래 실제049 경로다. 각 모드의 새 ignored `.local` 증거·소스 전후 SHA·390/1440 PNG·종료 결과를 따로 보존한다. 제품 CSS와 CSP를 유지하며 임의 URL·secret 입력과 알 수 없는 mode는 선행 거절한다. 빈 성공 모드는 제공하지 않는다.

`createIntakeReferenceTransport()`만 export하고 정확 `{readHistory,readCurrent,setContext,setPending,destroy}`를 반환한다. 생성 I/O·주입 옵션은 없다. app은 view에 reader 두 개만 전달한다. 같은 유효 non-null context3는 no-op이며 토큰과 진행 중 요청을 보존한다. 문맥 변경·null/invalid·pending true는 private 요청 세대와 CSRF를 먼저 무효화하고 요청을 취소한다. 잘못된 입력은 `intake_reference_ui_invalid_request`, 잘못된 wire/UTF8·시간 초과·알 수 없는 실패는 `intake_reference_ui_unavailable`이며 알려진 서버 오류는049의 열거33개만 보존한다. raw 응답·예외·주소·secret을 오류 메시지에 포함하지 않는다.

history GET은 `limit=1..100`과 null이면 생략하는 safe 양의 `before_seq`만 전송한다. 현재 POST body는 정확 `{schema_version:1,action:"current"}`다. 상대 same-origin URL·credentials same-origin·cache no-store·redirect error를 사용한다. Origin/Host/Cookie/Fetch header는 수동 설정하지 않는다. strict read-allowed/CSRF header의 최신 이력만 private 토큰을 게시하고, 이전 current의403은 새 토큰을 지우지 못한다. 응답 header와 stream의2MiB 상한, wire BOM 거절 후 fatal UTF8 decode,35초 제한·caller/context 취소를 적용한다. DTO의 strict JSON/정수 검증은 원래 A1 model이 맡는다.

메인 목록은 fallback 선택 뒤 context3까지 검증한 후 DOM/state와 함께 게시한다. 새 목록 요청 전에 transport→panel pending true를 전달하고 최신 finally만 해제한다. 실패한 목록으로 새 문맥을 만들지 않는다. 표시 필터가 같은 접수를 유지하면 이력을 중복 조회하지 않는다. 새 선택·목록 세대에서 metadata 이력만1회이며 현재 조회는 명시 버튼으로만 실행한다. 연결 만료 시 고정 안내에 따라 이력을 새로 조회한 뒤 현재를 명시 조회한다. BFcache에 들어가면 pending/토큰을 닫고 복귀 시 목록부터 새로 읽는다. 숨겨진 동안 끝난 메인 요청도 참고 패널을 재개하지 못하며, non-persisted pagehide는 두 구성요소를 종료한다. 브라우저 취소는 서버 부모 I/O 종료를 뜻하지 않는다.

2026-10-24 F1 소유 검증은 새 전체 Node206(기존186+transport20, fail/skip0), A1 trusted DOM18, 명시 frontend wire-fixture DOM19다. 기존 합성 사례 reader13·route17·lookup21·calculation21도 별도 통과했다. 전송 모듈 부재와 실제 behavior/잘못된 접수 ID의 fail-closed RED, 화면 mount RED 및 보완 중 실패 원본은 private 증거에 보존했다. 제품049 HTTP·043/042·참고 현재 조회의 보존 원문 읽기·backend 전체 Python은 이번 F1에서 미실행이다. Python2015는 root024의 이전 실행이다.

F1 당시 배정 base `0d7ee630b87bf2e2221c00ebcb3c106822dcfd15`의 기존 서버는 [049 정적 계약](../superpowers/specs/2026-10-24-intake-reference-http-host-design.md)의 `/intake-references/{model,view,transport}.mjs`를 제공하지 않았다. 이 base의 원형 intake-fixture 회귀1회 ESM 실패와 별도 exact static3 어댑터 phase의 text/PDF10 PASS를 보존했다. 이 adapter 결과를 제품049/session/auth/source gate/F2 통과로 합산하지 않는다. 후속 F2는 인수049를 포함한 정확 base에서 adapter 없이 새로 실행한다.

## 050 F2 — 실제049·제품 화면 검증

2026-10-25 Asia/Seoul. 별도 배정 base `2c5ba9ee043fd2559635bfe4d4725b34f6b45cd4`에서 원 F1 `3aa2c7d`와 cold 수정 `50a9aa3`를 순서대로 적용했다. 추가 제품 변경은 같은 checker와 이 usage뿐이다. A1·050 transport/app·052 C1 core와 backend/Store/schema/CSP는 바꾸지 않는다. 최종 소유 게시·독립 인수는 영수증으로 구별한다.

integrated checker는 저장한 Python supervisor를 자기 `.local/ir-f2-*`에 만들고 별도 P0에서 기존 public 합성 접수 helper와 genuine025 context/validated response→정식042 prepare1/append1로 이력1행을 준비한다. 생성/분석/파싱·DDL/쓰기는 이후 HTTP와 분리한다. 새 provider·고객 원문·이전 run DB/응답 재생은 사용하지 않는다. 새 Python child의 actual049가 같은 checkout의 실제 static3를 제공하고 Chromium은 제품 `/`·app·native same-origin fetch를 사용한다. ASSETS shim·Node proxy·sitecustomize·가짜 Store/HTTP 성공 응답은 없다.

수용은 별도 세 host(None/default scope/허용 scope)와 None child의040 catalog-only 생성·종료를 구분한다. None/040는042 import·Store 생성/opener0, static3 GET/HEAD6은 HTTP raw bytes와 Git LF 정규화 bytes·MIME/CSP를 대조한다. 기본scope는 이력 metadata1/source0·현재 버튼 비활성·직접 current403/부모0이다. 허용 정상은 자동 history1/source0 후 키보드 명시 current1만 정식042→038/034를 통과한다. 공개 정제 요약·CASE-A·false/null/0·raw UTC/KST·이전 관측과390/1440·외부 초점을 확인한다.

retained PDF/context/extraction의 실제 open과 snapshot._blob의 bounded native 반환 bytes를 profile/audit로 관찰한다. 후자는 전체 read bytes의 부분 계측이며 총 bytes는 unknown이다. 문서 재파싱/OCR/render·subprocess/model 시작은 HTTP phase에서0이다. SQL dump/행 수·파일 hash/identity 불변은 관측 범위 보존 증거이며 전체 데이터 무결성 인증이 아니다. SQLite open/close 수에는 startup 검증도 포함하므로 startup과 정상·fault·수명 phase를 나눠 기록한다.

정상 current와 별개로 clock+901 fault의 세션403/부모0·lastgood 보존, 새 anonymous browser context의 실제 재bootstrap을 확인한다. lifecycle은 정식042 native 진입 profile에서 원 실행을 유지한 채 잠시 대기한다. 둘째 실제 탭은 metadata를 읽되 source current429/queue0이며, 첫 브라우저 abort가 부모를 끝내지 않는다. 브라우저 종료→configured host close의 parent finally 대기→worker/socket/loop 회수 뒤 caller만043 Store를 닫는다. host 종료 뒤 borrowed Store 가용성, caller close 전 native4 이동 차단/뒤 해제·자기 port 재bind·원본/sidecar 보존을 별도 확인한다. 이 profile gate·시계 fault를 실제 운영의 모든 지연/시간 흐름 검증으로 올리지 않는다.

관측에는 method/route 종류/status·header 존재/형식·정확body2 bool과 계수만 남긴다. 실제 cookie/CSRF·binding 값/해시·원 request 헤더/HAR·private 원문을 DOM/storage/로그/다운로드/영수증으로 내보내지 않는다. 최초 integrated 미구현 RED·P0 계측의 테이블명 오류·None supervisor 종료 실패도 보존했다. 고객 PDF·실제 모델/실장비·053 준비/등록 HTTP·052 C2 메인 조립·새 backend 전체 Python은 이번 F2에서 미실행이다.

소유 F2의 새 검증은 integrated12·원형 text/PDF10·A1 trusted18·F1 wire19·보호된 C1 component23·전체 Node230(인수base210+기존 transport20, fail/skip0)이다. 기존 합성 reader13/route17/lookup21/calculation21도 별도 통과했다. integrated의 reference 요청은 응답9개와 browser abort로 전달 불명인 lifecycle1개를 구별하며 정식042 부모는 metadata4/current2회다. 세 child의 SQLite 누적2/4/12는 startup 포함이며 모두 close를 관측했다. 정상 current의 bounded _blob 관측은 PDF2958/context3438/extraction1800 bytes와 각각 open3회이며 전체 read bytes로 합산하지 않는다. configured 수명 둘의 caller close 전 native4 차단/뒤4 해제·3개 실제 host port 회수와040 catalog-only port 회수, 입력/행/schema/소스 불변을 확인했다. 이전 F1/root029 검사 수는 이 새 실행 수에 더하지 않는다.
