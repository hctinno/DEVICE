# 접수 참고 검토 준비·등록052 C1/C2

2026-10-25 C2는 [화면 조립 설계](../superpowers/specs/2026-10-25-intake-reference-actions-ui-composition-design.md)·[계획](../superpowers/plans/2026-10-25-intake-reference-actions-ui-composition.md)에 따라 기존 접수 화면에 C1을 연결한다. 아래 C1 기록은 당시 구성요소 범위이며, C2는 accepted050 F2와053을 포함한 별도 배정 base에서 수행한다. 전체 시험소 업무·실장비 검증을 완료한 것은 아니다.

## C2 실제 화면과 명시 작업

참고이력 A1 뒤, 알림 화면 앞에 C1 패널을 한 번만 생성한다. 메인 화면은 검증된 `intake_id,revision,snapshotGeneration`과 pending만 전달한다. 서버 세션·원래 요청·준비 번호는 기존 구성요소의 비공개 수명을 따른다. 알림 탭에서는 패널 표시만 숨긴다.

‘검토 준비’는 metadata bootstrap 뒤 보존자료를 확인하고, ‘참고 이력 등록’은 명시한 준비를 등록한다. ‘원래 요청 재전송’은 같은 접수·revision에서 원래7 필드를 그대로 전송한다. 자동 준비·등록·재전송·현재 조회는 없다. production025 입력을 제공하지 않은 서버는 미구성 상태이며 이 화면이 모델이나 입력 공급자를 만들지 않는다. 실제 입력과 읽기 범위가 있어도 등록 범위는 별도로 허용해야 한다.

등록 이벤트는 현재 패널·문맥의 metadata 이력만 한 번 새로 읽는다. 이벤트 처리부터 전체 bubbling이 끝나는 microtask까지 동기 선택·메인 새로고침·pending 재진입을 차단한다. 일반 페이지 폐기는 즉시 terminal destroy하며, BFcache 복귀는 기존 메인 조회만 수행한다. 늦은 finally가 더 최신 pending을 열지 않는다.

응답 유실은 미저장 증거가 아니다. 등록 불명은 원래 요청을 유지하고, 준비 교체 불명은 이전 준비가 유효하다고 복구하지 않는다. 별도 ‘새로 준비’만 replace=null로 요청한다. 서버의 남은 예약·503·410·만료와 세션 변경을 그대로 처리한다. 선택이 없으면 마지막 공개 결과를 이전 관측으로 남기고 쓰기 버튼을 닫는다. 다른 접수·revision에서는 그 결과를 숨긴다. retired 뒤에도 이전 등록 결과불명 안내를 보존한다.

## C2 검증 실행

```powershell
node frontend/intake_reference_actions/browser_check.cjs --mode integrated
node frontend/intake_references/browser_check.cjs --mode frontend
node frontend/intake_references/browser_check.cjs --mode integrated
python scripts/check_artifacts.py
```

C2 integrated는 자기 `.local`의 새 합성 PDF·기존 public025 검증 입력과 정식043 Store를 준비한 뒤 실제049/053 같은 loopback port0의 앱·HTTP를 검사한다. 각 P0 준비 batch와 P1 HTTP의 SQL·보존 읽기·행 변화를 구별한다. 정상 부모를 가짜 성공 DTO·별도 proxy·ASSETS adapter로 대신하지 않는다. 전송 지연·유실·헤더 모순·시계 변경은 별도 fault phase로 기록한다. 고객 PDF·실제 모델·시험장 네트워크·장비·출력·포털은 실행하지 않는다.

각 실행은 새 result/source-pin/PNG와 원 실패를 보존한다. 390/1440 화면, 키보드·외부 초점, 등록 분류5, 원래7 동일성 bool, source 동시1/queue0, abort 뒤 부모 수명과 drain, borrowed Store·native handle·sidecar·자기 port 회수를 구분한다. 보존자료 총 읽기 bytes는 unknown이며 실제 bounded `_blob` 부분집합만 계수한다. 비공개 token·cookie·handle·원래7 값/해시·HAR·원문은 영수증에 저장하지 않는다. A1의 승인 공개 이력 DTO에 포함된 request_id는 기존 공개 표시 범위다.

아래 C1 단위·합성 wire 검사는 실제 backend 연결 수와 합산하지 않는다. 기존050 호환 수정은 별도 checker/usage2에서 static1 누락과 옛 배치 전제만 갱신하며, transport/API·wire/source/부모 계수·CSP를 바꾸지 않는다. 통합/독립 제품 인수는 소유 검증과 별도다.

소유 C2 실제 앱 검증은 16묶음이다. 초기 정상 등록 phase는 prepare1/append1/원래 replay1·metadata5/current0이고, replay의 reference 행은1/1/1로 유지됐다. 전체 실행의 P0는 새 workspace11·각 합성 PDF2(파일22개, 고유 실자료22개라는 뜻은 아님)이며 historical revision 변경1은 별도 fixture mutation이다. P1 host15의 정상·미구성·거절·fault/회수 분모를 구분한다. 실제 부모의 분류5 중 profile_changed는 선언한 합성 profile fault로 재현했다. 정적4는 GET 응답과 실제 raw 파일 bytes를 대조하고 Windows CRLF→LF 정규화 후 Git blob도 대조한다. 서버 정책과 보호 소스는 바꾸지 않았다. Node230, C1 wire23, A1 trusted18, F1 wire19, F2 genuine12, 원형 TXT/PDF10, 기존 reader13/route17/lookup21/calculation21은 별도 회귀이며 전체 backend Python2242는 root032의 이전 실행이다.

## C1 구성요소 구현 당시 기록

2026-10-25 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-intake-reference-actions-ui-design.md)·[계획](../superpowers/plans/2026-10-24-intake-reference-actions-ui.md)의 신규4 구성요소를 구현한다. 같은 host의 기존 trusted 입력을 명시 준비→등록→원래 요청 재전송으로 연결하는 경계이며, C1의 합성 wire/DOM은 실제049/053/F2·고객 자료·모델·현장 검증과 구별한다.

공개 ESM factory2는 `createIntakeReferenceActionsController({onChange,onRegistered})`, `createIntakeReferenceActionsReview(container)`다. controller 반환7은 `setContext,setPending,refreshCapabilities,prepare,append,replay,destroy`, view 반환5는 `root,setContext,setPending,refreshCapabilities,destroy`다. 생성 I/O/emit0이며 A1/050의 API·private 값은 확장하지 않는다.

onChange는 exact8 `context,phase,pending,prepare_allowed,append_allowed,preview,registration,error_code`의 detached/deep-frozen 사본이다. preview11/null, 검증된 registration10에서request_id만 뺀 exact9/null을 받는다. onRegistered와 `intake-reference-history-refresh` event detail은 현재 명시 dispatch context3만 받는다. 모든 callback은 최신 세대·문맥·비pending에서만 호출하며 secret/handle/원래request는 공개하지 않는다.

준비는 명시 history bootstrap 후 exact3 POST, 등록/원래 재전송은 private 원래7을 전송한다. working CSRF cache 삭제와 occupied slot의 원 session 비교값을 구별한다. 같은 id/revision의 새 표시 세대에서도 원 요청을 바꾸지 않고 명시 재전송하며, 다른 접수·revision에는 전송하지 않는다. 현재 조회·새 모델·자동 준비/등록/재시도는 실행하지 않는다.

등록 dispatch 뒤 정상 응답을 확인하지 못하면 미저장으로 단정하지 않고 `uncertain`과 원래 요청을 보존한다. 준비 교체 응답 유실은 `replacement_unknown`이며 old가 유효하다고 복구하지 않는다. 별도 새 준비만 replace=null로 요청할 수 있고, 남은 서버 예약이나 cap503을 숨기지 않는다. 만료/session 변경과 단순 cache clear는 다르며 destroy는 terminal/private 폐기다. 브라우저 취소는 서버 부모 종료나 미저장 증거가 아니다.

검증 명령:

```powershell
node --test frontend/intake_reference_actions/actions.test.mjs
node frontend/intake_reference_actions/browser_check.cjs --mode component
python scripts/check_artifacts.py
```

checker는 고정 synthetic wire와 실제 browser 구성요소만 사용하며 port0/소유 ignored `.local` 증거를 만든다. 실제 backend mode/임의 URL은 미구현 상태에서 거절한다. parent/실제HTTP·업무 원문/모델/장비 실행은 C1 수로 올리지 않는다. C2의 실제 static1/app3/동일 session·source gate·genuine API·종료 검증은 accepted backend와050 F2의 별도 정확base/배정 뒤 수행한다.

2026-10-25 소유 C1 검증은 단위24개와 전체 Node210개(기존186+신규24, fail/skip0), component wire/DOM23개·기존 A1 trusted DOM18개를 구분한다. module 부재·실제 behavior·시간 제한/불명 보존·동시 동작/자원 반환·view 부재·retired 뒤의 공개 결과불명 표시 RED를 보존했다. 첫 `.local` 없는 별도 체크아웃·CLI 선행 거절·390/1440/keyboard/focus·late-beforeparse·브라우저/정적서버 종료와 source 핀은 소유 영수증에서 확인한다. 최종 독립 제품 인수는 별도다. 원 준비가 폐기돼도 공개 결과불명 안내를 미저장으로 바꾸지 않는다.

이 branch는 승인 A1 model/view만 의존하며 기존050 F1 app/transport를 합치지 않는다.050 F1의 기존 검증은 이전 별도 branch 결과이고 이번에 실제050/F2를 실행한 것으로 세지 않는다. 전체 backend Python·실제049/053/046 HTTP·025 입력 생산/모델·고객PDF·장비/현장은 미실행이다. root027 Python2092/Node186은 과거의 서로 다른 검증이다. component CSS는 수용 harness이며 제품 app/index/styles와 CSP는 변경하지 않았다.
