# INTAKE-REFERENCE-DEMO-057 — 새 합성 접수의 준비·등록 체험 CLI 설계

2026-10-25 Asia/Seoul. 조립 계약과 공개 투영은 **독립 정적 Yes/C0I0M0**를 받았으며 이 문서는 공개 구현 계약이다. 정적 판정은 공개 API 조립 설계의 검토이며 제품 수용·실제 실행이 아니다. C2는 통합033에서 최종 인수됐고 기능 `914d9de0`·게시 `d18fbb3e`를 기준 기능으로 참조한다. 이 결과를057 새 실행으로 합산하지 않는다. 정확 최종 게시base/신규3의 실제 별도 배정 전 제품·새 branch/commit·runtime/fixture/서버 기동0이다. [공개 재사용 접점](#공개-재사용-접점)과 [구현 계획](../plans/2026-10-25-intake-reference-demo.md)을 함께 사용한다.

## 공개 재사용 접점

- 기존 [접수 fixture 흐름](../../fcc/intake_fixture_check_usage.md)과 [기존 Store 실행 CLI](../../fcc/intake_serve_usage.md)는 아래의 시작 범위 차이를 유지한다.
- 새 접수는 [register_source/scan_source](../../../labflow/active_intake.py), [SyntheticTextProvider/run_worker](../../../labflow/intake_worker.py), [respond](../../../labflow/intake_jobs.py)의 기존 공개 API를 사용한다.
- catalog는 [FccReportCaseCatalog](../../../labflow/fcc_report_cases.py), 검토 입력은 [025 context/응답 검증](../../fcc/fcc_case_review_usage.md)을 사용한다.
- 공식 기존 Store 열기는 [Store.open_existing](../../../labflow/store.py), 같은 host 구성은 [053 준비·등록 계약](../../fcc/intake_reference_actions_host_usage.md)을 따른다.
- 사용자 화면은 기존 [C1/C2 준비·등록 화면](../../fcc/intake_reference_actions_usage.md)이며 새 화면·클라이언트 API를 만들지 않는다.

## 기존 기능과 필요한 작은 접점

`intake_fixture_check --document-kind pdf --port 0`은 새 접수→분석→자동 RF fixture→main UI까지 있지만 참고 Store/catalog/025 입력 없이 host를 만들므로 C2는 미구성이다. `intake_serve`는 기존043 열기/읽기 범위만 조립한다. 공통 `demo`/Virtual Fleet demo도 이 준비·등록 체험과 다른 흐름이다. 같은 사용 가능한 전체 진입점은 찾지 못했다.

**단일 추천:** 새 `labflow.intake_reference_demo` CLI1개가 자기 새 작업공간에 공개 API만 조립한다. legacy RF 데모/047/049·053/C2를 수정하지 않는다. 자동 가상 RF 실행·case/plan/run/evaluation 생성0이다.

실사용성의 최소 범위는 **후보 없는 검토 결과의 준비→명시 참고 등록→원래 재전송**이다. genuine `FccReportCaseCatalog`는 documents/cases/searches가 빈 합성 packet과 빈 PDF source map을 허용한다. 공개025 build/decode가 이 catalog의 실제 `no_candidate`/`no_reviewed_case` 입력을 검증한다. 받아들인 참고0/선택사례[]는 그대로 표시한다. 긍정 사례·HCT 기관·실제 보고서/규정·시험방법 값을 발명하지 않는다. positive reference 선택 데모가 필요하면 별도 승인 합성 사례자료 단위로 닫는다. 이번 준비·등록 체험을 전체 의도 이해·실측/규범 검증으로 대체하지 않는다.

## 명시 시작과 파일 경계

미래 명령안: `python -X utf8 -B -m labflow.intake_reference_demo [--output NEW_ABS_DIR]`. module 이름 자체가 합성 demo 선택이다. host는 항상 `127.0.0.1`, port는 항상0이며 host/port/기존workspace/외부입력/provider 선택 옵션은 추가하지 않는다. 8765/8766을 명시 사용할 경로가 없다. 실제 배정 포트도 금지값이면 ready/serve 전에 닫고 실패한다.

- 기본 output은 현재 작업 저장소의 `.local/intake-reference-demo/<새 UUID>`이다. custom은 절대 경로·존재하는 부모 아래의 새 leaf만 받는다. 기존 leaf는 빈 폴더라도 거절한다. 부모/leaf의 symlink·Windows reparse/UNC/비정규 경로를 거절하고 atomic mkdir(exist_ok=False)로 선점한다. default 전용 부모를 만들 때도 기존 경로·다른 DB를 재사용하지 않는다.
- 선점 전 CLI/경로/필수 dependency를 확인한다. pypdf는 기존 requirements-extract, PDF 작성은 기존 합성 도구가 쓰는 ReportLab을 재사용한다. 새 설치·네트워크·TXT fallback은 실행기에 없다. 누락은 고정 unavailable이며 미완성 PDF를 성공 처리하지 않는다.
- 새 폴더 안 inbox의 bundle명은 `057 합성 수동참고 데모(모델호출0)`이며 이것이 기존 main 상세 제목으로 표시된다. 그 안에 합성 PDF1와 TXT1을 만든다. 동일한 명시 literal product_type=sensor_node, market=FCC, model=DEMO-REFERENCE-ONLY를 사용한다. purpose는 `Synthetic manual/fixture 025 review; schema producer.kind=model; actual model calls=0; no hardware`다. 원문에 SYNTHETIC / NO REAL MODEL OR HARDWARE를 넣는다. 실제 사례/고객 값은 읽거나 복사하지 않는다. PDF의 ASCII 원문은 새로 작성된 bytes를 그대로 추출·보존하며 인용 text를 대체하지 않는다.
- `state/` DB·blobs, 새 원문, demo 선언/025 입력·실패/종료 기록은 이 새 폴더에만 둔다. JSON 출력은 exclusive UTF8 파일이다. 원래 입력·실패·등록 DB를 덮거나 지우지 않는다. 같은 output 재실행·재개/자동 rollback0이다.

## 실제 부모 조립과 범위

| 단계 | 공개 API/결합 | 하지 않는 것 |
|---|---|---|
| P0 새 접수 | `Store(new_state)`→`register_source(...synthetic=True,settle_seconds=0.001)`→`scan_source`2회→기존 `run_worker(...SyntheticTextProvider(),max_jobs=1)`→`respond(...,'proceed',intake_id=새ID)`→Store close | 기존 Store/고객 inbox 접근·새 provider·모델/외부 API·RF fixture 실행0 |
| P0 검토 입력 | `FccReportCaseCatalog(empty_synthetic_packet,{})`→`build_case_review_context(catalog,query=선언fixture exact4,case_ids=[])`→선언 wire를 `decode_case_review_response`로 검증 | private/test helper import·가짜 성공 DTO·추출기 대역·037 재해석0 |
| P1 실제 host | `Store.open_existing(str(new_state))`1→`create_server(...host='127.0.0.1',port=0,intake_reference_store=같은Store,fcc_case_catalog=같은catalog,read_scope=(새ID,),append_scope=(새ID,),review_inputs=(exact4,))`1→ready→caller `serve_forever()` | Node proxy/ASSETS adapter·새 HTTP API·기본 append 범위 확대0 |
| 브라우저 | 기존 `/` main/C2·native 같은 origin session→사용자 prepare/append/replay | CLI startup의042 prepare/append/current·자동 클릭/등록/재시도0 |

실제 kwargs 이름은 기존 `intake_reference_read_scope`, `intake_reference_append_scope`, `intake_reference_review_inputs`다. exact4 항목은 기존 `{intake_id,case_context,validated_response,producer_name}`만이다. P0 끝 reference rows/038 DDL0을 단언한다. P1 후에는 참고 ledger 변화만 허용하고 intake 원본·analysis/위임/기타 업무 행은 보존한다. 기존 Store=None/inputs=()는 그대로 미구성이고 이 CLI가 운영 서버에 기본 입력을 주입하지 않는다. demo 입력 구성·decode 실패는 bind 전에 중단하며 empty 성공으로 대체하지 않는다.

empty packet은 기존 schema1/corpus_id/scope/searches/documents/cases를 그대로 사용한다. scope는 부모의 `2025-01-01`/Asia/Seoul/population unconfirmed/synthetic=true, cutoff는 시작 시각이며 searches/documents/cases는[]이다. 새 입력 schema·loader/helper module0이다. query의 rule/method는 각각 `DEMO-RULE-NONNORMATIVE`, `DEMO-METHOD-NONNORMATIVE-v1`라는 **별도 선언 fixture 입력**이다. intake가 이를 자동 이해/확정한 결과가 아니다. case_ids=[]와 references=[]를 유지한다.

025 부모는 producer.kind=`model`로 고정한다. 이를 fixture/manual enum으로 바꾸지 않는다. producer_name=`DGM-SYNTHETIC-REFERENCE-DEMO-v1`, 작성 방식=`manual_fixture`는 private demo 선언에 기록하며 wire는 parent의 기존7키·no_candidate/no_reviewed_case만 사용한다. HTTP의 model_execution_verified/operational_authority_granted 등 false를 보존한다. schema의 model 표기가 실제 모델 호출 증거가 되는 것은 아니다.

## 사용자가 조작하는 순서

1. 명령을 시작하고 UTF8 ready JSON의 `url`을 브라우저에서 연다. 자동 browser launch·외부 로그인0이다. ready는 `/#[새 intake ID]`이며 URL/출력에 cookie/CSRF/handle/원7을 넣지 않는다.
2. main 상세의 합성 bundle 제목/fixture 분석 출처·목적의 manual/fixture 선언과 schema kind=model·실제 호출0, 시험/장비 미검증을 확인한다. 기존 ‘참고 검토 · 준비와 등록’ 패널에서 **검토 준비**를 누른다. 분석 출처의 fixture는 접수 분석자의 분류이며025 wire의고정 model kind와 구별한다.
3. 준비 응답의 선택상태 no_candidate, 받아들인 참고0, 선택사례[]·false 권한을 확인한다. 후보 없음 결과가 실제 parent로 검증된 체험이다.
4. **참고 이력 등록**을 한 번 누른다. 부모의 저장 응답과 A1 metadata 갱신을 본다. 정상 기대는 bound인 후보 없음 결과의 current_at_append다. 이는 등록 당시 관측의 일치이며 적용 규정 승인/긍정 참고 존재가 아니다.
5. **원래 요청 재전송**을 누른다. 같은 session/id/revision의 원7을 C1 closure 그대로 전송하고 replayed=true를 확인한다. row/seq/DB 추가쓰기0, rows1/1/1을 기대한다. CLI가 원요청을 새 ID로 고치거나 로그/파일로 꺼내지 않는다.
6. 현재 조회는 A1의 별도 명시 버튼을 누를 때만 수행한다. 기본 체험의 current0과 선택 추가 조회1은 별도 계수다. CLI `Ctrl+C`로 종료하고 새 원문·DB·실패/결과 기록을 보존한다. 재시작은 다른 새 output이며 기존 runtime 재개0이다.

## 출력·종료 계약

새 ready 출력은 stdout UTF8/LF JSON1개로 exact8: schema_version=1, kind=intake_reference_demo_ready, url, workspace, synthetic=true, ai_model_called=false, hardware_verified=false, operational_authority_granted=false. browser session/원7/검토 input 값·해시/원문/원시 예외는 출력·HAR·종료 영수증에0이다. demo의 선언025 원입력은 새 private 작업공간에만 보존하며 HTTP 파일 제공/다운로드를 추가하지 않는다.

help exit0·I/O 생성0, 인자/기존·잘못된 output exit2·선점0, 준비/host/출력/정리 실패 exit1, ready 전 KeyboardInterrupt exit130, ready 뒤 사용자 중단은 정상 drain을 확인한 경우에만 exit0이다. error는 stderr의 `{"error":{"code":"intake_reference_demo_invalid_argument|unavailable|output_failed|shutdown_failed"}}` 중 실제 고정 code1개다(파이프 구분자는 문서 표기이며 출력값 아님). stdout/stderr delivery unknown은 중복 frame 재전송0이다. raw traceback과 exit120을 정상 종료로 처리하지 않는다.

성공 정리는 admission 닫기→진행 부모 finally/active0→actions.close1/None→workers/socket/session 정리→caller043 Store.close 순서다. native4(workspace/state/blobs/DB)·sidecar·SQLite 연결·자기 port 회수를 별도로 관측한다. parent 종료 전 Store를 닫지 않는다. 반복 KeyboardInterrupt에도 같은 정리 순서를 끝내며 새 source 작업/재준비0이다. ordinary close 실패는 같은 소유 public close를 최대1회 추가 시도하고 최초 오류를 보존한다. host close가 확인되지 않으면 정상 회수를 주장하지 않고 exit1/실패 영수증으로 남긴다. 이 경우 OS 종료 회수와 정상 API drain은 구별한다. 강제 kill은 정상 cleanup proof가 아니다.

## 작은 소유안·수용·범위

후보3: 신규 `labflow/intake_reference_demo.py`, `tests/test_intake_reference_demo.py`, `docs/fcc/intake_reference_demo_usage.md`. 기존PDF demo와같은 pypdf/ReportLab의 선택 dependency와현재제공버전(pypdf6.21.2/ReportLab4.5.1)은usage에명시하고실행전검사한다. 새requirements파일·자동설치0이다. 실제배정뒤implementer가제공환경으로실행가능성을먼저닫으며사용자에게환경준비를요청하지않는다. 기존 부모·CLI·frontend/ASSETS/CSP/기본DB/schema/공유문서 수정0이다.

미래 수용은 [계획](../plans/2026-10-25-intake-reference-demo.md)의 D057-01~08이다. actual CLI child→기존 product HTTP/DOM과 정식025/043/046/042/038, 원7 동일 bool/ledger 행·SQL/원본 불변, None 미구성, 실패·중단/자원 회수·사용 순서를 실제 확인해야 제품 인수를 주장한다. mock lifecycle/wire와 genuine HTTP·P0 생성/025 구성/P1 native source·문서 검사를 분리한다. 현재는 선행 조립 계약의 정적 검토만 통과했으며 위 실행0이다. 새로운 원자료/사용자 준비 요청0, 실제 고객·모델·실물·규범·업무 전체 검증은 미완료다. 정확 공개 계약/base/신규3의 실제 배정 뒤에만 구현한다.
