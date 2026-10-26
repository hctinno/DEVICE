# 등록 합성 conducted workflow의 native host

## completed current 명시 경로 — 구현 전 고정안

2026-10-26 Asia/Seoul. DEV2-WORKFLOW-CURRENT-HANDOFF-001은 정확226a5182fbc4f88d1321eea6a6cee0e668ac598d의 별도 clone/branch에서 host/test/usage3만 소유한다. 등록3·native-intake3·현재 reader·Store·D1/D3/D4 코드는 수정하지 않는다. 아래는 root가 승인한 최소 범위를 구체화한 사전 계약이며 독립 preseal 확인과 구현/검증은 아직 대기다. 원87/226과 과거 실패·proof는 동결 유지한다.

새 workflow는 native schema_version=3 exact14, 즉 v2 exact13+context_scope="completed_current_provided"다. ref=None/명시 policy exact2·원 workflow SHA/config/finite permit/모델/시간·파일 한도는 유지한다. v1/v2는 기존 queued/G3 경로를 그대로 사용하고 schema3만 completed readonly current/facts-plan API로 분기한다. instructions나 C1을 고쳐 원 provider 문맥을 현재처럼 만들지 않는다. current context/analysis/facts-plan의 원 입력을 사용하며 원 queued plan/result는 과거 원형이다.

completed 전용 범위 검사는 단순한 _dedicated 생략이 아니다. 새 분기에만 같은 Store의 SELECT snapshot으로 다음을 전부 확인한다.

1. registered_intake exact6의 source_id/intake_id/job_id/positive revision/fingerprint/files를 원 manifest·actual source/revision/job과 대조한다. 대상 job은 정확1개이고 그 intake/revision의 실제 completed job이어야 한다.
2. 원 source와 revision의 synthetic=1, intake의 현재 revision 일치·upload_incomplete 아님, source의 실제 root/bundle이 원 registered_input_root와 일치, revision files_json/fingerprint가 선택 원형과 canonical 일치해야 한다. 다른 source·파일 목록·원문 bytes를 허용하는 범위 확대가 없다.
3. 같은 Store 전체의 queued/running job은0이어야 한다. 다른 active job이 있거나 대상만 queued/running이면 차단한다. 기존 과거 completed 이력 자체를 삭제·수정하거나 대상으로 선택하지 않는다.
4. scope snapshot 전후로 current readonly API를 한 번 호출한다. 원 context의 job/intake/revision와 원 analysis·current plan 전체 canonical SHA를 profile의 사전 명시 context/analysis/plan-input SHA 및 catalog/schema SHA에 대조하고 current plan은 ready여야 한다. scope/원 submission·현재 revision/files가 달라지면 소비 전 차단한다.
5. 제품은 claim/complete/respond/행 UPDATE·DML/새 parser/Store 초기화·원 권한 발급을 호출하지 않는다. queued 자료만 있으면 진짜 public claim→strict 분석→complete_job이 별도 선행되어야 하며 새 scope가 그 절차를 위장하지 않는다.

TXT만 첫 지원한다. 기존 native _registration의 PDF suffix unsupported_schema를 유지한다. D1 G3 schema2/PDF 지원과 formal native PDF 등록 지원은 별도이며 후자는 이번 소유 밖 인계 공백이다. 새 scope를 이유로 기존 helper 거절을 우회하지 않는다.

실행은 위에서 확인한 동일 current context/analysis/plan으로 원 adapter→selector/finalizer를 사용한다. D3의 독립 current3 readback/export에 줄 공급 원형과 기존 execution/finalizer/artifact pin을 연결해 보존해야 한다. caller-request.json은 plan binding/source 설정만 담으므로 그것만으로 current context/analysis 전체를 보존했다고 주장하지 않는다. 추가 handoff 파일의 정확 형상/상한과 저장 순서는 root preseal에서 먼저 확정한다. 기존 DRAFT·actual model/physical/method 미평가를 바꾸지 않는다.

계획은 사전 규범/독립 preseal→작은 RED→schema3/current scope 구현→typed 준비/차단·최초 오류→genuine MOCK≤1→source/Store 무쓰기/native 검증→정상게시·동결 순서다. 기존14/9·host7·registration7/parent 회귀를 반복하지 않는다. 새 TXT disposable Store 1건을 genuine public claim/strict/complete로 준비하고, product 호출과 setup의 DML·모델0을 분리한다. typed 실패는 보존 snapshot/새 test-only 복사본에서 수행한다. genuine loop는≤1이며 producer60초/loop180초/retry0/기존 disk cap을 유지한다. 실제 원Store/운영17·authority/profile/실permit·실제AI/ADC/Vertex/실장비·peer/하위 agent는0이다.

- [ ] root 독립 preseal 및 handoff/최초 오류 범위 확정
- [ ] 기존 v1/v2 보존·schema3/current binding의 작은 RED
- [ ] completed1·미완료/다른분석/범위/드리프트·control/최초 실패의 typed 검사
- [ ] 한 completed current snapshot의 genuine MOCK≤1·재소비 거절·원 current 공급/출력 보존
- [ ] 문서·raw/native 무쓰기·실패 보존·정상 commit/push·pin 인계

## 명시 측정 선택 workflow v2 — 2026-10-26

DEV2-REGISTERED-WORKFLOW-SELECTION-HOST-001은 정확 공개 base30cd27bc47e70e93713d984b8ac545e801217b9c의 독립 clone에서 host/test/usage3만 수정한다. 불필요한 의존 cherry는 없다. 수용 [selector](conducted_measurement_selector_usage.md) e258과 [선택 finalizer](conducted_execution_result_finalizer_usage.md) 7226+15b의 원 API를 사용한다. 등록921+d2e·원 운영profile/ref17·원 proof는 변경하지 않는다. 이 host 후보의 독립 검수는 아직 대기다.

공개 main(argv=None)->int와 CLI/scenario/model·고정 profile 위치·operator-control·anchor/permit 형상은 그대로다. registered-workflow.json만 두 형상을 명시 분기한다. schema_version은 native int이며 bool/float는 받지 않는다.

| workflow 형상 | 측정 선택 계약 |
| --- | --- |
| v1 exact12 | 원 nonempty measurement_ref string1~200자. measurement_selection_policy 키가 있으면 거절. 원 finalizer에 ref만 전달하며 새 keyword0 |
| v2 exact13 | 원12키+measurement_selection_policy. measurement_ref는 반드시 null, policy는 exact2 schema_version:int1/kind:unique_same_run_sensor_acquisition |

v2의 policy 누락/None/추가 키/다른 종류, non-null ref, v1에 policy 추가, 버전 bool/float/미지원값은 소비 전 원 profile_invalid/scope_mismatch/binding_mismatch 경계로 거절한다. 암묵적 None/default·v1→v2/profile 변환·last/PASS/ref 보정·fallback은 없다. 예를 들어 기존 ref17을 null로 바꾸기만 한 v1은 유효한 선택 정책이 아니다. v2의 전체 원 bytes SHA는 기존 config/permit의 workflow_sha256에 그대로 결합되며 policy 자체가 승인·추가 예산을 발급하지 않는다.

native 등록/G3/current C1·analysis/plan/source6/basis·quantity/tools와 원 schema를 모두 통과한 v2에만 measurement_ref=None과 원 policy를 기존 finalizer에 전달한다. finalizer가 원 native5파일을 재검증하고 selector1/내부 builder1을 사용하며 host는 선택·수치를 재계산하지 않는다. 선택 DTO exact9는 원 finalizer-receipt.json의 measurement_selection에 그대로 보존하고, host receipt exact12·finalization exact5와 원 파일/ledger pin을 유지한다. v2의 finalizer receipt exact12와 v1의 exact11을 구별한다.

selectorblocked이면 held/별도 result/artifact null/write0 및 원 선택 candidate/reasons/result·최초 producer 실패가 원 nested DTO에 남는다. valid selected 저장은 원 producer 실패와 DRAFT/task 미평가가 함께 남을 수 있으며, stored를 업무 성공·규범 승인으로 승격하지 않는다. host의 completed 판정식과 unknown/실제 local process 관측은 원형 그대로다. 실제 AI·물리/규범 검증을 성공값으로 채우지 않는다.

원 한도는 workflow64KiB·execution256KiB·finalizer2MiB/후행 reserve8파일·3MiB, loop8회/180s/producer60s/retry0·192파일/32MiB다. 입력·원장·취소·모델·claim/소비/finish·최초 오류와 cleanup을 변경하지 않는다. source의 변경은 _prepare의 두 형상/측정 계약 분기와 _run의 v2 전용 keyword 전달뿐이다.

- [x] 정확base/소유3 실파일명·finalizer18328/58d8·selector9241/4361 pin 확인, 비소유 raw/native baseline 보존
- [x] v2 미지원 준비 RED·policy 전달 부재의 실제 MOCK5 RED 보존
- [x] v2 exact13 준비·원 finalizer 정책 연결과 v1 keyword0 유지
- [x] 새 selection_ opt-in 작은 cohort와 닿는 legacy/최초control 경계 분리 검증

기존 기본14/별도9와 parent 전체 테스트는 반복하지 않았다. 최종 새 boundary4는1.587s, v2 blocked1은1.091s, legacy v1 한 건은1.131s, v2 genuine MOCK5와 같은 profile 재진입 차단 한 건은7.475s에 각각 PASS했으며 failure/error/skip0이다. 서로 다른7논리/분리4cohort다. 준비1과 genuine1의 중간 반복 통과를 이 분모에 더하지 않는다. default discovery는 원 test_14, 기존 --boundary는9이며 새 검사는 selection_ opt-in으로만 선택한다.

genuine v2는 실제 같은 Trial/runtime의 원 plan→MOCK 도구5→첫 acquire 완료 선택→raw -19.5 dBm/원 보정11 dBm→원 JSON/DRAFT·완료 marker를 확인했다. selector9/원 result·파일 bytes/SHA·같은 run/runtime chain과 원 ledger baseline/permit/reserved/consumed/finished5를 보존했다. 같은 profile 재진입은 not_run이고 새 dispatch0·SQL/claim/workflow 원 bytes 불변이다. 이 한 runtime의 Python mock model process는5이고 실제 모델은0이다. version 거절의 v2 blocked와 legacy v1은 각각 mock version child1/model0이며, 원 failure·소비·finish와 null/원 DRAFT 상태를 구별한다.

boundary4는 양성 v2 준비, 잘못된 형상16개 소비 전 거절, 원 quantity bool/source6/current context/tools/hash 검증 유지, 최초 G3 MemoryError→후행 owned Store close 오류의 같은 객체 전파를 확인했다. 상위 cap·ledger·취소·firsterror/cleanup helper와 원14/9 method는 정적 AST/원 bytes로 대조한다. 검증 fixture는 일회용 native OS 경계와 authored synthetic17 metadata·disposable Store/SQL이며 실제 운영17·권한 record가 아니다.

원 준비 RED의 profile_invalid ERROR1(0.138s)과 기대 실패로 정리한 RED FAIL1(0.152s), 준비 GREEN1(0.227s), policy 전달 전 MOCK5의 failed RED1(4.424s), 첫 전달 GREEN1(4.697s)을 별도 보존한다. 실제 실패/원 SQL·prefix·producer 영수증을 삭제·이동/수리·재시도하지 않는다. 최종 재진입 검사는 자동 retry 기능이 아니라 같은 consumed profile의 명시 재호출 거절 검사다.

```powershell
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py --selection-boundary -v
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py --selection-genuine -v
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py --selection-blocked -v
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py --selection-legacy -v
```

소유 test의 쓰기는 실행별512파일/32MiB O(1) admission을 유지하며 알려진 native 쓰기는 먼저 예약한다. 원14/9 전체 실행이나 실제 installed CLI·모델·운영profile·새 실 permit·root 위임 record 자동 생성·원17·ADC·Vertex·시험소 네트워크/장비는 이번 범위에서0이다. 다음 등록 metadata/preflight의 명시 v2 binding은 이 host 수용 뒤 별도 registration3 단위다. 아래는 원735의 v1 공개 계약과 당시 검증 이력이며 이번 분모와 합산하지 않는다.

2026-10-26 Asia/Seoul. DEV2-REGISTERED-CONDUCTED-WORKFLOW-HOST-001. base9fe7e5a41c6f427a77f9592a690e9c027073b9c4에 자기 finalizer576만 정상 cherry한 3b06e8b 위의 신규3이다. [finalizer](conducted_execution_result_finalizer_usage.md)의 새 실행0과 이 opt-in host의 유계 가상 실행을 구별한다.

## 실제 공백과 진입점

기존 [native intake host](codex_registered_intake_host_usage.md)의 permit/SQL은 one_registered_synthetic_intake_run·model process1에 고정됐다. conducted workflow용 정식 공통 issuer/예약 API는 없다. 그 permit·완료 run·운영 continuation을 재사용하지 않는다. 이 구현은 별도 고정 profile에서 root가 실제 준비할 한 bounded permit을 소비하는 좁은 host이며 issuer·DDL·baseline/permit 발급 기능이 아니다. profile이 없으면 not_run이다.

```text
python -B -X utf8 -m labflow.codex_registered_conducted_workflow_host --scenario-id ID --model gpt-6.1-sol
```

공개 main(argv=None)->int는 scenario/model 두 선택자만 받는다. 모델은 기존 지원 SOL/ASTRA 두 값이다. 승인 dict·경로·provider hook·stdin 승인·env profile 선택자는 없다. 현재 token의 KnownFolder LocalAppData 아래 고정 `DGMAutoLab/codex-conducted-workflow-host`만 사용한다. KnownFolder와 등록 원문 검증의 기존 native helper를 재사용하되 기존 intake issuer/history/once는 호출하지 않는다. 동일 계정 임의 코드 공격까지 인증한다고 주장하지 않는다.

현재 실제 profile/permit은 root가 검수 후 별도로 준비할 항목이다. 이 개발 작업에서 실제 OS profile·인증·운영 SQL·설치 CLI·실제 모델을 열지 않는다. root가 준비할 17회 계보는 원 bytes/hash metadata의 읽기 전용 continuation이며 host가 원 경로를 따라 재감사하거나 기존 원장을 변경하지 않는다. 0 seed·예산 reset/refund·retry·Vertex fallback은 없다.

## 고정 profile 계약

root는 아래 파일·native 경로·새 빈 runs/permit_id를 실제 등록 자료에 결합해 준비한다. host는 기존 파일만 읽고 기존 workflow ledger를 mode=rw로 연다. 고객 문서와 caller JSON은 이 profile을 선택하거나 승인할 수 없다.

| 파일 | 원형·상한 |
| --- | --- |
| root-continuation-anchor.json | schema_version/kind/inherited_history exact3; kind=codex_conducted_workflow_root_anchor; 64KiB |
| operator-control.json | schema_version/kind/anchor_sha256/journal_id/permit_id/registration_sha256/workflow_sha256/registered_input_root/store_root/executable exact10; kind=codex_registered_conducted_workflow_control; 16KiB |
| registered-intake-v1.json | 기존 native 등록 manifest exact5와 실제 원 폴더 전체 bytes/SHA; 256KiB |
| registered-workflow.json | v1은 schema_version/kind/scenario_id/context_sha256/analysis_sha256/plan_input_sha256/source_settings/quantity/allowed_tools/measurement_ref/catalog_sha256/schema_sha256 exact12. v2는 위 명시 measurement_selection_policy를 추가한 exact13; kind=codex_registered_conducted_workflow; 64KiB |
| analysis.json / plan-input.json | root가 보존한 원 native 분석·D1 exact8 plan; 각각256KiB |
| catalog.json / response-schema.json | 원 catalog≤1MiB, 승인 원 literal schema≤64KiB; SHA 검증, 재직렬화0 |
| cancel-request.json | exact1 requested:bool; 1KiB, 단계 사이 읽음. missing/invalid는 실행 차단 또는 진입 뒤 unknown |
| workflow-continuation.sqlite3 | 기존 새 scope 전용 ledger≤32MiB; 생성/DDL/seed0 |
| runs/permit_id/ | root가 준비한 빈 run directory. loop/와 DRAFT artifact, 원 receipt를 보존 |

inherited_history는 기존 actual_codex_model_processes/known_total_before_this_host/unknown_usage_components/usage_complete/cost/provenance_level/source_rollup/published_source exact8이다. actual/known은 native17, unknown/cost=null, usage_complete=false, provenance_level=previous_verified_root_rollup_not_fresh_original_receipt_reaudit다. source_rollup과 published_source의 path/bytes/SHA는 계보 metadata이며 원 파일·실제17의 원 응답을 열지 않는다.

root/input/Store는 서로 중첩되지 않는다. Store.open_existing와 genuine registered context를 사용하고 실제 source 등록·current public8 C1·원 analysis/plan C1·source6를 대조한다. 원 plan은 ready_for_simulation 및 conducted_synthetic/version1/on/source_output 개발 계약이어야 한다. 원 basis를 조립·복구하지 않는다. quantity는 명시 on/sensor_input/false/+1 exact4이며 bool을 숫자1로 취급하지 않는다. allowed_tools는 기존 loop의 dut.start/sensor.acquire/sensor.read/advance1/stop exact5다.

analysis.json/plan-input.json은 LF 없는 canonical native JSON이며 각 hash는 그 원 bytes와 같다. v1 workflow.measurement_ref는 root가 명시한 observation ID string1~200자다. source6와 같은 raw 값·숫자 타입을 유지하며 다른 event·마지막 값·PASS를 자동 선택하지 않는다. 명시 ID가 실제 report/journal에 없으면 D3의 원 incomplete/null 이유를 보존한다. v2는 앞의 ref=null/명시 정책 계약으로만 원 selector에 전달한다. scenario_id는 등록 건 선택자이며 이 host의 가상 실행 scenario는 normal이다.

승인 schema는 기존 public literal3052B/SHA256 aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb다. root가 다른 schema와 hash를 함께 주어도 소비 전에 unsupported_schema다. 새 client/schema 지원은 별도 검증 대상이다.

## 새 scope ledger와 한 permit

root가 준비할 SQL은 `CREATE TABLE codex_conducted_workflow_history(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, permit_id TEXT, payload TEXT NOT NULL, UNIQUE(kind,permit_id))`다. seq1부터 canonical payload만 수용한다. 이 단위는 한 root-issued permit만 지원하며 다른/추가 permit을 선택하거나 발급하지 않는다. 모델 시작 전 reserved와 consumed를 별도 durable commit한다.

baseline exact5: schema_version=1, kind=codex_conducted_workflow_continuation_baseline, journal_id, anchor_sha256, inherited_history. permit exact9: schema_version=1, kind=codex_conducted_workflow_single_use_permit, journal_id, permit_id, anchor_sha256, workflow_sha256, registration_sha256, requested_model, expires_at. expires_at은 UTC 초 단위의 미래 시각이다. permit은 operator control의 실제 ID/hash/model과 모두 일치해야 한다.

고정 한도는 model process≤8, outer≤180s, producer≤60s, tool intent/tick≤8, output256KiB·loop files192/32MiB, transport/application retry0이다. 소비는 이 bounded workflow 하나를 위한 것이며 unused 호출도 환불하지 않는다. host가 추가 모델 호출을 하거나 한도를 늘리지 않는다. cancellation은 단계 사이만 지원하고 remote hard cancel/과금 중단은 미검증이다.

180초는 재사용하는 genuine loop의 outer deadline이다. 등록·SQLite·native 파일 I/O 전체의 hard realtime 상한을 새로 주장하지 않는다. 고정 cancel 파일을20ms 간격으로 읽는 bounded watcher가 실제 threading.Event를 설정한다. caller callback이나 Event subclass를 loop에 넣지 않는다. 취소는 실행 중 producer를 원격 취소하지 않으며 producer의 기존60초/남은 loop deadline·유계 회수를 유지한다. watcher 종료 join은2초, 최초 종료 시도 실패를 재시도해 성공으로 숨기지 않는다.

loop 뒤 run 폴더를 한 번 유계 관측해 남은 수용량을 계산하고, 추가 host snapshot과 D3 writer 최대8경로/3MiB를 O(1)로 먼저 예약한다. loop+후행 run evidence도192파일/32MiB를 넘겨 저장하지 않는다. 부족하면 원 loop/prefix를 남기고 후행 저장을 거절한다. 이 관측은 hot write마다 전체 경로를 검색하는 기능이나 OS disk hard quota가 아니다. profile/등록 원문/working Store와 별도 workflow ledger는 위 개별 상한과 원 genuine API의 한도를 따른다.

reserved는 permit_id/context_sha256/workflow_sha256/plan_input_sha256/requested_model/maximum_model_processes=8 exact6, consumed는 permit_id/reservation_sha256 exact2다. finished는 원 실행 영수증 pin·actual local model process0..8/null·cleanup·storage 상태와 정제 오류를 기록한다. 원 scope의 17회와 새 scope의 예약8·실제 관측 수·unknown을 구별한다. 최초 실패·원 receipt/prefix·소비를 삭제하거나 성공으로 고치지 않는다.

이 초기 wrapper는 소비 뒤 같은 fixed profile로 재진입하지 않는다. 영속 workflow-claimed.json은 예약 bytes를 보존한 crash/late-close 차단이며 정상 완료에도 삭제하지 않는다. 새 permit 발급·후속 issuer·복구는 이 단위의 공통 API 공백으로 남는다. 임의 새 branch/폴더/0 ledger로 차단을 우회하지 않는다.

## 구현·검증 순서

신규 소유는 [host](../../labflow/codex_registered_conducted_workflow_host.py), [검사](../../tests/test_codex_registered_conducted_workflow_host.py), 이 usage3개다. 계획은 (1) fixed-profile 미제공·scope/hash/permit/계보 거절 RED, (2) genuine 등록/context와 원 plan gate, (3) durable reserve/consume→공개 adapter→공개 finalizer, (4) 실제 producer 원 receipt로 count/cleanup/finish, (5) mock native 실행·예산/취소/unknown·동일 runtime 검증과 정상 게시 순서다. 별도 policy 문서·범용 provider platform·다른 owner 수정은 없다.

개발 검사는 별도 authored synthetic17 계보·disposable Store/SQL/profile와 알려진 Python mock child만 사용한다. 이것을 실제 원장17 또는 실제 모델 사용으로 가산하지 않는다. source/native profile 경로는 test-only OS 경계에서만 대체하고 실제 producer/strict decoder/Trial/runtime/journal/builder/writer는 그대로 실행한다. proof 쓰기와 native child의 예상 쓰기는 O(1) counter로 먼저 예약하며 proof를 삭제하지 않는다. 원 실패와 미실행은 별도로 보존한다. 실제 검증·return 계약은 구현 후 아래에 기록한다.

## 반환과 원 영수증

정상 형상은 exact12 schema_version/kind/status/phase/scenario_id/requested_model/history/reservation/execution/finalization/errors/verification이다. kind는 codex_registered_conducted_workflow_host_receipt다. completed0/not_run3/failed4/unknown5이며 completed만 stdout, 나머지는 stderr에 UTF-8 JSON/LF로 출력한다. 인자 오류는 별도 exact5 schema_version/kind/status/phase/code와 exit2, help0이다. 출력 frame≤69632B다. main은 원 control 객체를 전파하고 module process는 KeyboardInterrupt130/그 밖의 control5로 종료한다. 출력 실패도 소비를 되돌리지 않는다.

| 경로 | 실제 형상·보존 범위 |
| --- | --- |
| history | 미검증/finish 불확실은 null. exact7 inherited_model_processes/local_model_processes/known_total_model_processes/actual_total_model_processes/usage_complete/unknown_usage_components/cost |
| history 수치 | inherited=원17, local=실제 native producer 관측0..8/null. known_total은17+관측 부분합이며 local null을0회 관측으로 바꾸지 않는다. actual_total은 unknown/후행 close 오류면null. 실제 계정 전체 원격 사용량 인증이 아님 |
| history 미확인 | usage_complete=false, unknown_usage_components/cost=null; 원 계보 범위를 유지 |
| reservation | 미예약 null. 이후 exact3 permit_id/state/reservation_sha256; state=reserved/consumed/finished |
| execution | 미도달/null 또는 exact6 run_id/runtime_instance_id/status/failure/receipt/producer_receipts. 원 adapter failure를 유지 |
| finalization | 미도달/null 또는 exact5 status/result_status/artifact/failure/receipt. artifact는 원 D3 writer summary10이며 raw/null/gaps는 원 finalizer snapshot과 result.json에 보존 |
| errors | phase/code exact2 최대8. 최초 오류를 앞에 두고 원 exception text·SQL·경로·본문을 노출하지 않음 |
| verification | exact6 operator_scope/execution_scope/origin_authenticated/remote_model_identity_verified/measurement/hardware_verified |

operator_scope는 검증 전 not_validated, 원 native profile/원장/원문을 대조한 뒤 native_operator_control이다. execution_scope=one_registered_synthetic_conducted_workflow, origin_authenticated=false, remote_model_identity_verified=false, measurement=not_assessed, hardware_verified=false다. 현재 OS 위치 해석·요청 argv·실제 local process 시작·원격 principal/server model identity를 구별한다. 원 adapter의 actual_cli 선언·ai_model_called=null·intake_native_host_connected=false를 고치지 않는다.

receipt Pin은 bytes/sha256 exact2다. runs/permit_id/execution-receipt.json(≤256KiB)은 원 adapter DTO, finalizer-receipt.json(≤2MiB)은 v1 exact11/v2 선택 evidence를 가진 exact12 원 finalizer DTO다. producer_receipts는 index/bytes/sha256 목록이고 index의 고정 경로는 loop/calls/0001/producer/receipt.json 형식이다. 원 failed step의 receipt_sha256이 null이어도 원 DTO와 실제 고정 receipt file·모델·prompt/schema를 대조해 별도 pin을 기록할 수 있다. 원 null pin을 채우거나 receipt status를 고치지는 않는다.

version 거절처럼 model attempt0/start=false가 원 receipt에 있으면 local0이다. attempt1인데 start=false인 모호한 spawn, 원 receipt 부재/불일치·unknown DTO는 local=null·unknown이며0으로 가정하지 않는다. model child가 아예 없던 metadata 실패의 model_child_reaped=null은 원형 그대로 두고 소유한 자원의 회수만 판단한다. cleanup_confirmed는 CLI child/pipe/artifact 및 runtime reference의 범위이며 DUT 출력 OFF·물리 안전·원격 취소의 증명이 아니다.

finished payload exact8은 permit_id/status/local_model_processes/cleanup_confirmed/execution_receipt/finalizer_receipt/producer_receipts/errors다. finished는 당시 관측을 durable 기록한 것이며 후행 Store/SQL/guard close 오류가 있으면 최종 반환은 unknown이다. 그 뒤에도 workflow-claimed.json과 원 finished/consumed를 보존하고 새 호출을 막는다. 실패한 rollback을 반복하지 않고 알려진 owned connection close는 별도로 한 번 시도한다. 준비의 최초 control이 Store close 오류에 가려지지 않는다.

completed는 원 adapter에 실패가 없고 D3 결과 recorded·저장 stored인 로컬 workflow 연결 상태다. 정식 task/conformity PASS·모델의 일반 능력·실측 예측력·전체 시험소 완료로 확대하지 않는다. DRAFT와 result.json은 원 artifact의 files/manifest path·bytes·SHA로 읽고, 다른 run이나 nested raw ref를 탐색하지 않는다.

## 실행한 검증과 미실행

기본14와 별도 boundary9를 각각 다른 UUID proof namespace/512파일·32MiB 한도 안에서 실행한다. default unittest discovery는 기본 test_14를, --boundary는 명시 boundary_9를 실행한다. 이는 한 검사의 반복을 분모에 더하거나 기존 증거를 삭제해 수용량을 만드는 절차가 아니다.

```powershell
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py -v
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py --boundary -v
python -B -X utf8 scripts/check_artifacts.py
```

기본14는 genuine 등록/context/facts 원 plan·실제 같은 Trial/runtime·genuine producer/strict decoder/journal/finalizer/builder/writer와 test-only Python executable으로 ASTRA mock5회→DRAFT를 확인한다. SOL nonzero1/원 producer 실패·version metadata 뒤 model0·취소 뒤 관측1·재사용 금지·0 seed/다른 intake SQL 거절·원문/quantity/C1/만료/모델 불일치를 구별한다. 원 actual CLI·계정·인증·운영SQL·실제 모델·Vertex·시험장 네트워크/실장비는 미실행이다. 실제17/Vertex6·3072 소진을 변경하지 않았다.

최종 기본14/14 PASS(11.533s), 별도 boundary9/9 PASS(4.532s)이며 failure/error/skip0이다. 두 실행의 서로 다른23개 논리를 뜻하며 한 번에23개를 실행했다거나 중간 반복을 독립 증거로 더한 값은 아니다.

boundary9는 missing cancel/미지원 schema의 소비 전 거절, partial claim, KI/SystemExit/GeneratorExit 원 객체, consumed commit/finish 실패, 후행 evidence cap, ambiguous spawn=null, 최초 G3 control+Store close와 rollback 실패+owned close를 검사한다. 기본 MemoryError는 소비 뒤 unknown과 같은 객체를 확인한다. SQLite와 child의 알려진 native 쓰기는 먼저 예약하고 각 proof write는 O(1) 누적 counter로 검사한다. cold namespace 관측은 완료 후 한 번의 검증이다.

원 RED14/API 부재, 첫14의10 PASS/4 FAIL(Event 형상), target4의2 PASS/2 FAIL(실패 receipt null pin의 관측), 미지원 schema RED1, ambiguous spawn RED1, Store/rollback 최초 예외 RED2와 후속 PASS를 보존한다. 중간에 통과한 같은 기본14/경계6·7을 최종 분모에 더하지 않는다. 원본·prefix·DB·guard·log를 삭제하지 않는다. 전송 ZIP은 원 raw의 byte/SHA·CRC를 대조한 별도 사본이다. 관측한 retained 크기와 논리 admission 한도를 구별하고 관측하지 않은 native disk 순간 최대를 소급 합격으로 표시하지 않는다.

부모 finalizer576은 후행 root 독립 qualified Yes/C·I·M0와 root 재생20 PASS를 인수했다. 그 frozen clone/proof/partial raw/ZIP은 수정·재검사하지 않았다. 요청받은 작은 replay locator metadata만 새 private 작업 공간에 보존했다. 현재 host 후보의 독립 검수·실제 root profile/새 bounded permit 발급·실제 모델 실행은 제출 후 별도다.
