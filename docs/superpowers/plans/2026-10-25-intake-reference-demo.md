# INTAKE-REFERENCE-DEMO-057 구현 계획

> **For agentic workers:** 실제 구현 배정 뒤 `superpowers:executing-plans`로 직접 수행한다. 하위 agent0. 조립 계약과 공개 투영은 독립 정적 Yes/C0I0M0이며 정확base/신규3의 실제 별도 배정 전 제품·fixture·runtime 실행0이다.

**Goal:** 새 합성 접수에서 기존 main/C2를 열어 사용자가 준비·참고 등록·원7 재전송을 직접 수행하게 한다.

**Architecture:** 새 CLI1 안에 fixed synthetic setup과 기존 public 부모 조립만 둔다. 생성용 P0 Store와 공식043 borrowed P1 수명을 나누고, genuine empty catalog/선언 no_candidate wire를025 build/decode한 exact4로053에 전달한다. frontend/backend/API/helper module은 확장하지 않는다.

**Tech Stack:** 기존 Python/SQLite·Store/worker·025/053·C2, pypdf와 기존 합성 demo의 ReportLab. native HTTP/Playwright는 검증 전용이다.

**Spec:** [고정 설계](../specs/2026-10-25-intake-reference-demo-design.md)·[공개 재사용 접점](../specs/2026-10-25-intake-reference-demo-design.md#공개-재사용-접점).

## Global Constraints

- C2 인수된 최종 게시점 포함 정확 base/신규3·계약의 실제 배정 전 제품·새 branch/commit·fixture/서버/runtime0. 통합033의 C2 기능914d9de0/게시d18fbb는 기준 기능의 인수 핀이며057 실제 배정base가 아니다.
- 신규3만: labflow/intake_reference_demo.py, tests/test_intake_reference_demo.py, docs/fcc/intake_reference_demo_usage.md. 부모·기존CLI·frontend/ASSETS/CSP/schema·운영DB·공유문서 변경0.
- 127.0.0.1:0 고정, 8765/8766 service0. 새 output exclusive·기존 입력/실패/원7 보존. 새 input schema/provider/loader/helper module·모델/실물/실제 사례·자동 RF/등록0.
- P0 PDF1/TXT1와 선언manual_fixture025, P1 genuine HTTP, lifecycle double/fault/강제kill·정상회수·문서 integrity의 분모를 나눈다. empty catalog는 부모가 허용한 실제 객체이며 가짜 성공 DTO가 아니다.

## Review Focus

1. 기존 폴더/부모 reparse나 에러 뒤 재시작이 원본을 덮음 → D057-01/02 exclusive·실패 보존.
2. test helper/실제 사례 literal·fake 응답을 제품에 들이거나 model kind를 actual AI로 오독 → D057-02/04 import/025/pure no_candidate·선언·false 검증.
3. 준비/등록을 startup에 수행하거나 scope를 운영DB에 넓힘 → D057-03/04 P0 reference0·freshID scope1·None/emptycapfalse.
4. 원7/세션이 바뀐 재전송 또는 저장 응답 유실을 rollback/새 등록으로 처리 → D057-04/05 original bool·행/SQL·불명/retire.
5. 출력 실패/반복 중단·active close가 Store를 먼저 닫거나 회수 성공으로 꾸며짐 → D057-06/07 ready0/serve0·부모finally/네이티브/port.

## Task 1 — explicit synthetic CLI와 정식 부모 연결

**Files:** Create `labflow/intake_reference_demo.py`, `tests/test_intake_reference_demo.py`, `docs/fcc/intake_reference_demo_usage.md`.

**Interfaces:** sole public `main(argv: list[str]|None=None) -> int`. 옵션은 `--help` 또는 선택 `--output NEW_ABS_DIR`만 허용한다. 내부 `_prepare_demo(output: Path)`는 이 module에서만 생성한 state path/intake ID/genuine catalog/review_inputs tuple을 반환한다. 외부 provider·raw input·callback을 받지 않는다. actual host는 계약의 기존 create_server keyword 이름/exact4를 그대로 사용한다.

- [ ] 배정 base/branch/원 refs·dirty/stash/C2·056 원고를 고정한다. 계약과 실제 public 함수/empty packet/source·025 producer blob을 대조하고 차이는 총괄에게 반환한다. 구현 전 현재 v1을 임의 적용하지 않는다.
- [ ] D057-01~08 전용 테스트를 작성하고 missing module/CLI 행위 RED를 실제 얻어 보존한다. 라이브러리 parent/test double과 실제 child/HTTP·브라우저의 결과를 구별한다. 제품에 test hook·env adapter를 추가하지 않는다.
- [ ] CLI의 strict argument/path/dependency 선검사와 exclusive output을 구현한다. --help 이외 unknown/중복/기존leaf/UNC/reparse/비절대 custom output을 쓰기·bind 전에 거절한다. default 새 UUID 폴더만 생성한다. 기존선택PDF환경을implementer가확인하고usage에명시한다. 새requirements파일·실행기자동설치/fallback0이다.
- [ ] 실제 새 PDF/TXT 원본을 쓰고 공개 register/scan/run_worker/fixture provider/respond만으로 단일 synthetic V2 완료·모의 proceed를 만든다. P0 Store를 닫는다. 자동RF, 기존 fixture flow의 run/평가, 가짜 analysis·원문 text 대체0이다.
- [ ] public genuine empty catalog를 기존6키 packet/빈 source map으로 만든다. fixture exact4 query와 case_ids=[]→025 context, 선언된 no_candidate/no_reviewed_case의 기존7키 wire→decode를 수행한다. 입력 artifact/선언을 새 private output에 exclusive 저장한다. producer.kind는 부모 model 고정/실제 AI0, JSON/type/원 입력을 임의 수리하지 않는다.
- [ ] 공식043 open_existing1→기존053 create_server1에 같은 Store/catalog/exact4·read/append=(새ID,)를 전달한다. C1 actions static1을 포함한 기존 main asset4/route를 그대로 제공한다. reference prepare/append/current는 startup0, ready JSON1/LF flush 성공 뒤 caller serve_forever다.
- [ ] 계약의 고정 오류/exit와 output delivery unknown을 구현한다. ready 전 중단130/뒤 정상중단0을 구별하고 최초 오류를 보존한다. admission/parentfinally/actions.close/worker·socket·session→callerStore 순서와 제한 retry를 지키며 확인되지 않은 close/강제kill을 정상 회수로 세지 않는다.
- [ ] 아래 테스트와 정상 사용자 순서를 실제 실행한다. Node browser observer는 test 파일/owner private 검증에만 두고 제품 import0이다. 실제 request/원7 값·token/header/HAR는 보존하지 않고 RAM equality bool·고정 계수/DTO public 부분만 영수증으로 남긴다.

## 미래 검증 수용

| ID | 필요한 실제 확인 |
|---|---|
| D057-01 | help/unknown/중복/output 기존·빈·file/경로오류·부모 reparse/의존성 부재→지정exit, 선점·Store/bind0. 사용자 환경·기존파일/실패 불변. |
| D057-02 | 새 단일 P0 workspace/PDF1/TXT1의 bytes/정식 V2 page·line 인용/fixture producer/모의위임·완료1. reference rows/DDL0·RF/workflow case/plan/run/evaluation0. parent calls/SQL 생성은P0로 별도 기록. test/private harness import0. |
| D057-03 | real CLI child/정식0431/0531/read·appendID1. 범위 밖 거절, None/emptyinputs는 기존capfalse/등록0. existing static4 GET/HEAD raw·정규화GitLF/MIME/no-store/CSP·alias404 유지. |
| D057-04 | CLI ready URL의 real main/C2에서 prepare1/append1/original replay1, 초기 H5/current0. 선택 no_candidate·accepted0·requested[]·false 권한을 실제 확인. 원7 동일 bool, native current_at_append 정상기대·rows1/1/1/replay DDL/datawrite0·전체SQLdump 동일. 실패는 원결과로 보존한다. |
| D057-05 | genuine commit 뒤 전송 유실/세션·410 경계의uncertain·retired·원7/replay/불명메모, 자동 재준비/ID교체0. source1/queue0·metadata 허용/부모finally 전취소선반환0. C2/053 기존검사를 재사용하고새CLI 조립의native 관측을별도로고정. |
| D057-06 | ready 출력 실패/깨진 stdout·stderr→serve0·고정exit/중복frame0·생성원본/실패보존·자기자원회수. wrapper UTF8/LF/flush 실패에raw traceback/exit120 성공0. |
| D057-07 | actual native parent active 중 caller KeyboardInterrupt·반복중단→종료대기·parentfinally→coreclose1/None/active0→workers/clients/loop/socket→callerStoreclose. SQLite C-close 일치·native4 차단/해제·sidecar/port회수. 정리실패/kill은 exit·실제회수범위를 분리. test observer는기존047 pattern의정식부모pass-through를참고하되제품hook0. |
| D057-08 | usage의한명령→URL→main합성제목/목적의manual_fixture·schema model/실제호출0 구별→명시준비→후보0확인→등록→원7replay→Ctrl+C를실제브라우저/키보드390·1440에서검증. 자동focus/source·external/storage/download/secret노출0. UI/parent 회귀와전용unit/native수를 구별. |

미래 명령: `python -X utf8 -B -m unittest tests.test_intake_reference_demo -v`, `python -X utf8 -B -m labflow.intake_reference_demo --help`, `python -X utf8 -B -m labflow.intake_reference_demo`. 실제 API/브라우저 조작은 새 private output·127.0.0.1:0만 쓴다. 라이브 서버 중단/출력 fault는 자기 child만 대상으로 한다. 같은 실제 product module과 공개 부모 source pin을 앞뒤 대조한다.

- [ ] 관련 CLI/HTTP/Node/C2 회귀를 변화에 맞게 실행하고 새 전체 Python은 새 runtime 모듈과전용테스트가통과한뒤총괄지정범위로고정한다. 이전2242/230·C2 warm/cold16을새run으로더하지않는다. native PDF/worker spawn/실제HTTP를 fake 성공으로 대체하거나 미실행을 skip PASS로 올리지 않는다.
- [ ] usage의명시합성/후보0·schema model 대실제AI 구분·원본/기한/재전송/None/재개미지원·오류/종료순서를작성한다. UTF8·링크·JS/Python정적검사·`python scripts/check_artifacts.py`,정확3 cached diff/원본·refs 보존,commit/push/remoteexact·cold evidence→총괄독립리뷰로반환한다.

자체검토: 기존 demo와의 차이·공개 API 재사용·최소 input·CLI/자료 경계·실제 사용자 순서·P0/P1/None·원7·출력/중단/회수는D057-01~08에모두연결했다. 현재 수용은전부미실행이며문서정적검사만한다. 제품 인수는미래genuine전체경로가실행된뒤다.
