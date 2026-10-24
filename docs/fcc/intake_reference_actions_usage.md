# 접수 참고 검토 준비·등록052 C1

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

2026-10-25 소유 C1 검증은 단위24개와 전체 Node210개(기존186+신규24, fail/skip0), component wire/DOM22개·기존 A1 trusted DOM18개를 구분한다. module 부재·실제 behavior·시간 제한/불명 보존·동시 동작/자원 반환·view 부재 RED를 보존했다. 첫 `.local` 없는 별도 체크아웃·CLI 선행 거절·390/1440/keyboard/focus·late-beforeparse·브라우저/정적서버 종료와 source 핀은 소유 영수증에서 확인한다. 최종 독립 제품 인수는 별도다.

이 branch는 승인 A1 model/view만 의존하며 기존050 F1 app/transport를 합치지 않는다.050 F1의 기존 검증은 이전 별도 branch 결과이고 이번에 실제050/F2를 실행한 것으로 세지 않는다. 전체 backend Python·실제049/053/046 HTTP·025 입력 생산/모델·고객PDF·장비/현장은 미실행이다. root027 Python2092/Node186은 과거의 서로 다른 검증이다. component CSS는 수용 harness이며 제품 app/index/styles와 CSP는 변경하지 않았다.
