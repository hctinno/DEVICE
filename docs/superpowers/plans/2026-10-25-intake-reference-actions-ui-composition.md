# REFERENCE-ACTIONS-UI-COMPOSITION-052 C2 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 개발4 직접 수행, 새 하위 에이전트0. 현재는 공개 준비 문서이며 실제 구현 배정이 아니다.

**Goal:** 기존 app에서 명시 준비·참고 등록·원래 재전송과 현재 문맥의 metadata 이력 갱신을 공개 API로 연결한다.

**Architecture:** 기존 A1/050에 C1 view1만 sibling으로 추가한다. 서버 세션·source gate·비밀과 C1 slot은 각 소유 closure/runtime에 두고 app은 검증된 context3/pending/event3만 전달한다.

**Tech Stack:** 기존 ESM/DOM/CSS, Node test, Playwright Chromium, genuine Python049/053·043/025/046/042. 새 dependency0.

**Spec:** [고정 설계와 수용20개](../specs/2026-10-25-intake-reference-actions-ui-composition-design.md). 공개052/050 및053을 소비하며 수용 검사는 모두 미래 미실행이다.

## Global Constraints

- C1/049는 통합029, F2는 root031 `1f17e0a764f9cc2e4b41f17869ede04a992802d7`에서 최종 인수·게시(새 Node230·관련 HTTP Python58·DOM12)됐다. 053 후보 `5eee86b4f1baf029bf99bb73fd59f0278bbda836`는 독립 최종 Yes/C0I0 뒤 root032 기능 `b29237126d119ed18db85ae4654f6caae9f96b47`에 인수됐고 새 전체Python2242/skip0·기존화면 실제HTTP/DOM12가 통과했다. accepted053/static1·정확 최종root base/소유5의 실제 별도 배정 전 제품/branch/cherry-pick/공개 파일/fixture/브라우저 실행0. 현재1f17e0a와 기존160732c는 미래 C2 실행 base가 아니다. 원 branch·No/RED/cold·원계획을 보존한다.
- 기본 소유는 app.js/index.html/styles.css와 C1 browser_check.cjs/usage 정확5. 고정 설계의 C2-COMPAT-050 별도예외2는 공개핀·총괄 실제 추가 배정 뒤에만 허용한다. 보호 부모·C1 core/API·050 transport/test/secret·backend·공유 문서·CSP 변경0.
- C1 공개 state8/view5·event3, A1 reader2/context3·050 반환5 유지. 자동 source/새 tokenstore/provider/current·권한 발급0; production025 미제공 capfalse 유지.
- 실제 검증 fixture는 기존 public API의 합성025·genuine043/부모, 같은 host port0만 사용한다. 고객 PDF·실제 모델·실장비·Hancom0. 정상 genuine phase와 명시 전송 fault phase를 구별한다.

## Review Focus

1. 같은 id/revision의 새 generation과 다른 revision을 혼동해 원 요청/이력이 바뀜 → T1의 C2-03/06, T2의 C2-12.
2. 옛 main finally·BFcache 복귀가 pending을 먼저 열거나 source를 자동 실행함 → T1 C2-04/07.
3. 성공 hook과 뒤쪽 bubbling의 동기 selection/main-refresh/pending이 main만 바꾸거나 C1 setter에 재진입함 → T1 C2-05/06. guard는 listener 반환이 아닌 end-of-stack microtask에서 해제한다.
4. 응답 유실·다른/없는 token·만료 후 미저장 또는 old-valid로 복구함 → T2 C2-13/14/15.
5. 입력 없음·false/0/null·retired 안내가 앱 스타일/권한 계산으로 사라짐 → T1 C2-08/09, T2 C2-10/16.

## T1 — 앱 연결·화면·문맥의 의미 있는 RED→GREEN

**Files:** Modify `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`; Test `frontend/intake_reference_actions/browser_check.cjs`; usage는 같은 task 설명만 작성.

**Interfaces:** 기존050 transport1+reader2/A1 view5에 C1 `createIntakeReferenceActionsReview(container)` view5·등록 event3를 연결한다. 새 공개 export/getter는 없다.

- [ ] 정확 배정 base/소유5·accepted blob/정적4·원래 refs·증거 보존을 확인하고 리드가 배정한 미래 branch에서만 시작한다. 근거는 별도 새 영수증으로 남긴다.
- [ ] checker의 component 경로를 보존하며 실제 app을 쓰는 integrated 경로에 C2-02~09 assertions를 먼저 추가한다. sibling mount 없음 또는 연결 동작 부재의 RED를 실제 실행하고 원본을 보존한다. C2-06은 뒤쪽 bubbling listener에서 다른 접수 선택 버튼.click()·#refresh.click()·pending 진입을 동기로 실행해 main/context/pending·C1 setter/action 변화0을 단언한다. 해제 microtask 자체는 source/queue/replay0이며 terminal destroy도 별도 확인한다. URL/secret CLI option을 추가하지 않는다.
- [ ] 고정 설계의 문맥 전달·latest pending·event guard·pagehide/pageshow를 app에 추가한다. R1은 root listener 뒤 bubbling 동안 guard 유지→end-of-stack microtask 해제만이다. selection/main refresh/pending은 state/request/DOM 또는 C1 setter 이전 return, terminal destroy만 alive/listener 닫기와 C1 destroy를 허용한다. index sibling과 scoped CSS만 추가한다. 예: stale generation event 뒤 history delta=0, 현재 event 한 번 뒤 history delta=1/current·prepare·append delta=0, main2가 pending이면 main1 finally 뒤 버튼은 닫힘을 단언한다.
- [ ] 같은 명령 `node frontend/intake_reference_actions/browser_check.cjs --mode integrated`의 새 app phase GREEN과 390/1440 화면·keyboard/외부 초점을 확인한다. C1 의미 지적이면 현재 C1 소유수정으로 별도 우선 보고하고 C2에서 우회하지 않는다.

## T1.5 — 기존050 검사의 최소 호환2

**Files:** 별도 실제 배정 뒤 `frontend/intake_references/browser_check.cjs`, `docs/fcc/intake_reference_ui_usage.md` 정확2. 기본 C2 소유5와 구분되는 작은 commit으로 보존한다. 기존 C2 base/branch·미커밋은 재작성하지 않는다.

- [ ] 공개 C2-COMPAT-050 핀과 추가2 소유의 실제 배정을 확인한다. F1 static 목록의 모듈 누락과 F2의 옛 panel0 전제를 원소스/실제 실패로 구분해 보존한다.
- [ ] F1 기존 static allowlist에 실제 C1 모듈 파일1만 추가한다. F2의 부재 전제만 새 sibling1/detail 밖으로 바꾸며 기존 수동조회·wire·부모/source 계수·CSP·오류/수명 검사를 보존한다. ASSETS adapter·조건부 skip·가짜 성공·새 API0이다.
- [ ] combined C2 후보에서 F1/F2 새 phase를 실행한다. C2 own checker의 static4·genuine 준비/등록 수용과 기존 F2 읽기 검증을 구별한다. 계수 변화는 원인 확인 전 기대값을 바꾸지 않는다. 사용법에 새 실행과 미실행만 갱신한다.

## T2 — 같은 host genuine HTTP·회수·인계

**Files:** 같은 C1 `browser_check.cjs`, `docs/fcc/intake_reference_actions_usage.md`; T1 소유3의 회귀만 수행한다.

**Interfaces:** 053 public create_server의 borrowed Store/catalog·read/append scope·review_inputs exact4, 실제 GET history/header3·prepare body3→6·append/replay 원7→10. backend private registry/hooks를 app에서 호출하지 않는다.

- [ ] [050 공개 계획](2026-10-24-intake-reference-frontend.md)의 P0와 public025 helper를 재사용해 새 ignored 합성 workspace를 준비한다. 생성/파싱/초기 DDL8·baseline row/schema/provenance/원본 pins와 P1 HTTP 실행을 분리한다. None/default-deny와 정상 허용은 별도 새 수명이다. Windows 자식 helper는 checker 내부 또는 ignored 저장 파일이며 main guard를 둔다.
- [ ] C2-10~18을 실제 port0 HTTP/DOM에서 RED→GREEN으로 확인한다. 정상 same-session 명시 prepare1→append1→원래 replay1, 등록 뒤 metadata만, 원7 동일성은 메모리 비교 bool/키 수만 기록한다. 정상 분류5·source1/queue0·retained read/parse0와 최초 row1/replay 추가쓰기0을 구분한다. 전송 유실은 실제 부모 완료 뒤의 명시 fault phase이며 합성 성공 응답으로 대체하지 않는다.
- [ ] browser 종료→host admission 차단→모든 parent finally/active0→actions.close1/None→worker/session/socket 회수→caller043 close·port/sidecar 회수를 확인한다. pass-through 계측으로 확인할 수 없는 항목은 미검증으로 남기고 추정 PASS를 만들지 않는다.
- [ ] C2-19/20의 새 회귀·문서·pins를 실행한다. `node --test`는 배정 base의 실제 test 파일 집합, A1/F1/F2는 기존 명령, C1 component/integrated는 각각 새 phase로 기록한다. `python -X utf8 -B scripts/check_artifacts.py`, 신규 usage 직접 UTF8/로컬 링크, `git diff --check`를 확인한다. 전체 Python은 별도 실제 실행 유무를 기록한다.
- [ ] 소유5만 commit/push, 원격exact·원래 실패/RED·입출력 pins·회수·실제/미실행 영수증을 리드에 전달한다. 독립 최종 Yes와 루트 실제 인수 전 완료로 승격하지 않는다.

현재 T1/T2 체크는 모두 미실행이다. 이번 문서 무결성 검사를 제품 DOM/HTTP·기능 PASS로 세지 않는다. 실행 방식은 개발4 직접 수행으로 유지하고 리드의 배정/검토를 따른다.
