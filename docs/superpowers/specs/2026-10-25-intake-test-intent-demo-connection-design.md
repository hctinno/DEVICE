# 057 합성 데모의 제공 대조 화면 연결 설계안

2026-10-25 Asia/Seoul. DEV4-INTENT-DEMO-CONTRACT-20261025-001. private v1 No/C0I1M0와 원 실패를 보존하고, 수정 v2의 독립 정적 Yes/C0I0M0 뒤 공개한 구현 계약이다. 총괄은 명시 `--intent-view` 접근과 아래 기존3개 소유를 승인한다. 정확 게시 base·전용 branch·실제 배정 뒤 개발4가 구현한다. 현재 이 후속 기능의 제품 실행은0이다. 조사 기준088의 데모·jobs·034 접점은 통합038 기능 `23fbf981420518a36fa7d09c243a272875acfbe4`에서도 같고, 기존 화면088과 공통 Store290의 제품 인수는 별도다. [구현 계획](../plans/2026-10-25-intake-test-intent-demo-connection.md)을 따른다.

v2 정정: v1 정적 리뷰의 No/Important1을 보존한다. 현034는 expected revision/result SHA를 함께 받도록 검사하므로 revision만 지정한 호출은 invalid_argument다. 이번 fresh 합성 P0는 두 expected 인자를 모두 생략해 원 capture를 보존한다. 새 result SHA 생산·원 context/full projection 재구성·atomic/currentness 보증은 추가하지 않는다. 기존088 제품 Yes와 이 후속 정적 계약의 리뷰 결과는 별개다.

## 목적과 현재 공백

사용자가 정식 057 합성 데모를 시작해 접수 상세의 **제공된 규정·방법 대조** 구역을 실제로 확인하게 한다. 기존 준비·등록·재전송을 같은 화면에서 별도의 명시 조작으로 유지한다. 합성 literal 대조를 실제 의뢰 이해·모델 실행·규범 적용·시험 착수로 표시하지 않는다.

현재 `labflow/intake_reference_demo.py`의 `_prepare_demo`는 PDF/TXT 새 원본→public scan→`run_worker`→`respond(proceed)`를 수행하고 P0 Store를 닫은 뒤 C2용 빈 catalog·수동 025 no_candidate 입력을 만든다. 반환은 정확4개이며 `_execute`가 기존 host에 참고 입력만 공급한다. `labflow/intake_serve.py:147`도 기존 Store/read scope만 공급한다. 두 CLI 모두 `intake_test_intent_inputs`를 넘기지 않는다. `run_worker`의 반환에는 상태 요약만 있고 원 context/submission은 없다. 034 capture의 최소 snapshot을 full projection으로 대신 쓰거나 현재 UI facts에서 원 제출을 복원해서는 안 된다. 비공개 소스 지도 `source-map.json`의 raw/GitLF·AST 위치를 기준으로 이 공백을 다시 확인한다.

이번 단위는 057의 명시 합성 경로 한 가지다. 047 운영 CLI의 외부 입력·provider·loader를 함께 만들지 않는다. 현재 공급 경로가 없는 것을 화면 완성이나 실제 모델 검증으로 보고하지 않는다.

## 접근과 제안한 선택

| 접근 | 달라지는 범위와 비용 | 선택 상태 |
|---|---|---|
| 057 `--intent-view` 명시 옵션 | 기존 CLI 안에서 새 합성 원입력만 보존·공급한다. 기본 worker·기존 오류 회귀를 유지한다. | 개발4 제안 |
| 057 기본 실행에 항상 공급 | 옵션은 줄지만 기존 bounded worker 경로와 기본 관측을 바꾼다. | 이번 제안에서 제외 |
| 047에 파일/공급자 입력 추가 | 운영 입력·권리·계보·로더 계약까지 필요하다. | 이번 한 단위보다 큼 |

총괄은 첫 접근과 기존3개 소유를 승인한다. 정확 base·전용 branch는 게시 SHA를 확인한 별도 실제 배정으로 고정한다. 새 기준 화면/버튼은 만들지 않으며 인수 대기 중인 기존 화면을 그대로 쓴다.

## 제안 소유권과 경계

총괄이 승인한 소유권은 기존3개 최소 변경이다.

1. `labflow/intake_reference_demo.py`: 옵션 파싱, 합성 P0 원입력 보존, 기존 host 명시 tuple1 공급.
2. `tests/test_intake_reference_demo.py`: 기존 assertion 보존, 추가 경로·원입력·실제 HTTP/DOM·실패/종료 관측.
3. `docs/fcc/intake_reference_demo_usage.md`: 같은 실행기의 새 옵션과 실제 확인 순서·한계.

새 제품 파일·provider·범용 loader·선택 framework·endpoint·worker·schema·UI/CSS/CSP/ASSETS·새 버튼·query/case 승격은 없다. `ui_server`/intent API/worker/jobs/034/Store/프런트 모듈과 기존 공개 설계·계획·공유 문서는 소유하지 않는다. 제품에서 test fixture/helper를 import하지 않는다.

## CLI와 미공급 기본값

`main(argv=None) -> int`와 ready JSON의 기존8키·flags4·고정4오류/종료 코드·127.0.0.1/port0·8765/8766 금지는 유지한다. `--help`는 단독으로만 허용하며 준비/Store/host 없이 도움말만 출력한다.

제안 문법은 무인자, `--output NEW_ABS_DIR`, `--intent-view`, 그리고 `--intent-view --output NEW_ABS_DIR` 또는 `--output NEW_ABS_DIR --intent-view`다. 옵션은 native list/tuple의 native str로만 받고 `--intent-view`는 값 없는 단일 flag다. 중복·값·별칭·다른 옵션·`--help` 조합은 기존 invalid_argument/2, stdout0, 의존성/예약/준비/host0이다. 기존 새 절대 경로·링크/reparse·UNC·동일 경로 재사용 거절은 유지한다.

기본 실행은 기존 `run_worker(... max_jobs=1)`을 그대로 쓰고 intent tuple은 `()`다. 추가 intent API import/call0, intent 원입력 파일0, GET 키/화면 구역0이다. 047과 직접 `create_server`의 미공급 동작도 바꾸지 않는다. opted-in 도움말은 실제 모델 호출0과 미제공 근거를 설명한다. 브라우저 자동 실행·고정 port·기존 workspace 재개를 추가하지 않는다.

## 옵션을 켰을 때의 합성 P0

현재 057은 intent 원입력을 가지고 있지 않다. 원 context를 worker 반환에서 만들어 냈다고 하지 않고, 명시 옵션의 작은 합성 준비 분기에서 **동일한 기존 public API**로 원입력을 직접 보존한다. 실제 공급자를 새로 만들거나 기존 worker의 반환·상태 계약을 늘리지 않는다.

1. 기존 exclusive 새 output·declaration·합성 PDF1/TXT1·등록/안정화 scan을 유지한다. `_PURPOSE`, `_LINES`, 기존 수동 025 query와 원문을 바꾸지 않는다.
2. 옵션 분기만 `claim_job(store, 'demo-reference-analysis', synthetic_only=True)`를 한 번 호출한다. 반환의 intake ID가 방금 accepted ID이고 synthetic이 true인지 확인한다. 없음/다른 ID/비합성은 고정 unavailable이며 원본을 남긴다.
3. 원 claim에서 `job_id,intake_id,revision,synthetic,documents,analysis_contract,instructions`와 존재하는 `analysis_context_id`만 같은 값으로 보존한다. token/lease_until/attempt는 공급 context·파일·stdout에 넣지 않는다. 합성 concrete `SyntheticTextProvider().analyze(context)`의 원 submission을 받아 public `complete_job`에 원 job ID/token과 함께 한 번 제출한다. 새 provider·프로세스·worker API는 없다. 이 명시 경로는 bounded worker 실행 증거가 아니며 이미 제한된 내부 합성 literal의 동기 분석이다.
4. 기존 `respond(proceed)` 성공 후 `intake_status(store, intake_id)['analysis']`의 **현재 full projection**과 `read_intake_reference_snapshot(store, intake_id)`의 원 034 capture를 같은 P0에서 받는다. unavailable/null/불완전은 부모 원상태로 보존하며 가짜 hash·snapshot·submitted를 채우지 않는다. 예외는 빈 성공으로 바꾸지 않는다.
5. 기존 P0 `except BaseException`/finally와 `_close_owned(... remember_interrupt=True)`를 유지한다. 원 분석 완료 직후 또는 P0 close의 최초 KI가 있으면 P1 opener/factory0, ready0, 130이며 후행 close·출력 오류가 덮지 않는다. P0가 확실히 닫힌 뒤에만 P1을 연다.

이 분기는 공개 API의 원값을 확보하기 위한 합성 caller 조립이다. DB 내부 SQL·retained file 탐색·원 context 재구성·추가 scan/claim/retry·외부 모델/자료/장비 실행을 만들지 않는다. 실패한 claim/분석·기존 원본은 cleanup/rollback으로 삭제하지 않는다.

## 명시한 후보와 빈 근거

새 데모는 최소 **proposed 두 필드** 예제 하나다. linked/conflicting 등 전체 상태 행렬은 현재 화면/API의 별도 검증 범위이며 새 데모에 선택 모드를 추가하지 않는다.

`intake`는 `context,analysis,projection,observation` 정확4키이며 위 P0의 원 객체다. `proposal`은 정확4키이며 `as_of=None`, `institution_scope=None`, `workflow_scope_id=None`, `fields`의 rule/method 각각 후보1개다. 수동 후보 literal은 `DEMO-RULE-NONNORMATIVE`와 `DEMO-METHOD-NONNORMATIVE-v1`, origin은 `explicit_supplied`, 각 `intake_refs=[]`, `basis_refs=[]`다. `sources=[]`를 그대로 공급한다.

이는 기존 C2 수동 fixture와 같은 표시용 문자열을 **별도 입력으로 명시한 것**이다. 원 의뢰·규범에서 추출/추론했다거나 실제 basis를 제공했다고 하지 않는다. 기존 `_LINES`에는 이 literal이 없으므로 fact/evidence index·quote·basis extraction·기간·scope를 만들어 주지 않는다. 부모의 기대 결과는 각 `status=proposed`, `literal_linked=false`, `intake_ground_missing`/`basis_missing`, 전역 `applicability_not_assessed`다. 검사 수행2개도 false이며 권한/검증12개는 항상 false다. 후보가 없거나 틀린 원자료를 linked로 보이게 만드는 데모는 실패다.

P0 성공 후 새 `intent-input.json`을 기존 `_save`의 exclusive UTF-8 JSON으로 보존한다. 이 파일은 `authoring='manual_fixture'`, 기존 flags4와 `intake,proposal,sources`를 담는 private 원입력 증거이며 새 loader/제품 schema/API가 아니다. claim 전체·token·원래 C2 요청7값을 넣지 않는다. 기존 `review-input.json`과 C2 input 정확4키·빈 catalog·no_candidate를 유지한다. 새 원입력 저장 실패를 빈 tuple로 덮거나 재시도/덮어쓰기하지 않는다.

## P1 공급과 화면 확인

`_prepare_demo(output: Path, *, intent_view=False)`의 반환을 `(state, intake_id, catalog, reference_inputs, intent_inputs)`로 명시한다. 마지막은 기본 `()`, 명시 옵션은 `((intake, proposal, sources),)`인 native tuple0/1이다. 기존 `_execute`가 이를 현재 `create_server(..., intake_test_intent_inputs=intent_inputs)`에 전달한다. 부모 review는 host가 bind 전에 1회 만들며 demo에서 추가 호출하지 않는다.

host의 ID/revision/**전체 analysis canonical hash** 결합을 재사용한다. 같은 revision에서 답변·질문이 바뀌면 이전 메타데이터와 구역이 사라져야 한다. 생략 상태를 잘못된 intent 없음 판정으로 표시하거나 GET에서 API·원자료·034를 다시 준비하지 않는다. 새 로더·serializer·캐시·refresh 동작·hash 비교 구현은 추가하지 않는다.

사용자는 기존 ready URL을 열어 같은 접수의 두 후보 literal, proposed와 근거 미제공 사유, 검사2 false/권한12 false를 읽는다. 인용 위치/quote가 새로 생기지 않는 것을 확인한다. 펼침은 네트워크·source 읽기·권한을 만들지 않는다. 기존 C2 준비→명시 등록→원 요청 재전송은 별도의 버튼 조작이다. intent review로 query/선택사례/등록 권한을 산출하지 않으며 기존 수동 025 no_candidate 입력으로만 동작한다. ready8키에 raw context·review·token·cookie·CSRF·handle을 추가하지 않는다.

## 오류·수명·원본 보존

기존 fixed invalid_argument/2, unavailable/1, output_failed/1, shutdown_failed/1과 ready 전 최초 KI/130, ready 후 정상 drain/0을 유지한다. intent 부모의 fixed3오류는 host에서 빈 성공으로 바뀌지 않으며 demo CLI는 기존 phase unavailable로 정제하고 bind/ready0·보존 failure 기록을 남긴다. 경로·예외 원문·candidate를 stderr로 복제하지 않는다.

057 `_close_owned`, `_cleanup`, 최초 오류·ready phase·`_process_main` final flush 처리의 구현을 재설계하지 않는다. 기존 core/actions close 완료→host 종료 확인→borrowed Store caller close 순서를 유지한다. host 종료 미확인 시 Store를 먼저 닫거나 closed 성공을 기록하지 않는다. 진행 중 부모·반복 KI·출력 실패·최초 1/2/130 우선순위를 기존 검사와 옵션 경로의 실제 결함 주입으로 함께 확인한다. 정상 종료, OS 강제 회수, 미실행 검사를 구분한다.

## 수용 조건과 증거

실제 구현 승인 후 새 output에서 public jobs/034→host API1→정식 GET→실제 DOM1440/390을 확인한다. 기본 경로는 API0/키·구역0이다. wire만으로 이 흐름을 통과했다고 하지 않는다. view 단계 원문 read0/추가 034·parent0/DB write0와 기존 metadata SQL을 구분한다. 별도 C2 조작의 예상 source 읽기·DDL/datawrite 및 replay의 원7 RAM 동일·rows1/1/1/쓰기0를 분리한다.

P0/P1 Store·SQLite 실제 open/close·source 단계·core close·host drain·native handle4·sidecar·자체 loopback port 재bind를 기록한다. 실제 값은 관측한 수로 보고하고 과거의 SQLite15/16 등 수를 정답으로 고정하지 않는다. source/cookie/token/HAR/SQL문·params/원7값을 외부 증거로 복사하지 않는다. 최초 오류·실패·합성 원본과 이전 No/Yes 증거를 보존한다. 새 후보의 모든 테스트 산출물은 `.local/INTENT-DEMO-CONNECTION-001/` 아래 새 UUID 경로에 두며, 기존057/088 증거 폴더에 새 실행을 섞지 않는다. 기존 테스트의 assertion은 유지하고 출력 경로 관측만 새 영역으로 옮길 수 있다.

fresh checkout의 exact candidate에서 새 output/명시 옵션을 실제 실행해 URL/DOM/종료를 재현한다. 변경에 직접 관련된 기존057 검사와 새 검사를 실행하고 기존 host/intent 화면의 필요한 경계만 회귀한다. 전체 Python/Node/browser를 관례적으로 반복하지 않는다. cold·owner·독립 리뷰·총괄 통합, 문서 무결성·합성 기능·실제 모델/장비/현행 규범 검증은 별개다.

이 후속 기능의 정적 준비 당시 제품 import/API/fixture/DB/HTTP/browser/model/hardware는 모두0이었다. private spec/plan/source-map exact3와 당시 tracked1782·refs/stash·기존 증거 보존 기록은 그대로 둔다. 공개 계약과 실제 제품 실행을 구별하며, 구현은 총괄의 정확 base·전용 branch 실제 배정 뒤 [계획](../plans/2026-10-25-intake-test-intent-demo-connection.md)을 따른다.
