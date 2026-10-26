# 등록 합성 conducted workflow의 native host

## 정식 등록 v3와 실제 host 준비면의 호환 — 2026-10-26

DEV2-CURRENT-REGISTRATION-PREPARE-COMPAT-001은 원 host 후보7b04f32의 새 독립 clone/branch에서 이 usage와 기존 host test2만 소유한다. 개발1 후보 b7230c54edf421ece4a169c563e28b5e83eb8e1c의 registration3은 892ee055로 dependency 정상 cherry-pick했으며 원 bytes를 그대로 유지한다. host core32893B/SHA93f410f4와 원 ERS·H+tail·v1/v2·summary12/finalization5·sole genuine1도 변경하지 않는다. 원 host 후보와 이 최소 회귀의 독립/통합 수용은 별개다.

공개 등록 ABI는 prepare_registered_conducted_workflow(*,scenario_id,requested_model)다. 제공 prepared-data schema3 exact16/context_scope completed_current_provided/ref null/명시 policy를 실제 검증하고 native stage를 작성한 뒤, 원 실제 _prepare(root,config,scenario,owned)의 5tuple/current3·원 native Store를 대조해 배타 게시한다. 새 회귀는 공개된 RegistrationTests의 disposable TXT 준비 경계만 재사용한다. operator-parent 위치를 AUTHORED 폴더로 치환하고 실제 권위/data 함수·native SQL/fsync/publish·실제 host 준비면을 실행한다. 이는 운영 계정·실제 승인·KnownFolder profile의 진위를 검증한 것이 아니다.

의미있는 RED는 공개 git의 parent7b 등록 source 원bytes26816B/SHAce86c8cb를 private 제어명으로 읽기 전용 로드해 같은 metadata16을 거절시키는 의존성 기준선이다. RED1/0.269초는 target/stage/host 진입 전 not_prepared이며 원 prefix를 보존한다. b723 파일을 고치거나 실제 host를 정답 callback으로 교체한 결과가 아니다.

동일한 TXT 내용의 새 AUTHORED disposable 경계에서 실제 b723+7b 연결2가1.033초/exit0 PASS했다. 양성은 metadata16→workflow3 exact14→native publish→staging 실제 _prepare1+게시 후 실제 _prepare1을 실행해 원5tuple/context/analysis/plan/schema와 owned.current_facts_plan exact3/completed_scope를 대조했다. 정확 등록 Store root와 각 known owned close1, 원5SHA·current/원queued C1 구별, 원 Store/source bytes·SHA/dev/inode/nlink/size/mtime/ctime/attributes 불변을 확인했다. control SQL은 baseline/permit2로 미소비이고 runs 폴더는 비어 있다. 음성은 제공 analysis만 달리하면 actual current/data gate가 staging/target/host 준비 전에 거절한다. 이2개를 원 등록13의 typed-host 양성/구형 host 거절 모집단에 합산하지 않는다.

```powershell
python -B -X utf8 tests/test_codex_registered_conducted_workflow_host.py --registration-compat -v
```

원 host test74개 메서드 AST·core·registration3·다른 소유를 보존하고 새 클래스2검사는 표준 discovery에도 선택된다. 실제 loop/가상 RF runtime/CLI/모델·추가 genuine·운영17/profile/permit/새 승인·공유/peer/agent는0이다. product 준비 동안 Store 초기화·실행·finalizer·CLI 진입도 거절하는 경계를 둔다. private `.local/CRPC-001/`에 source/ABI·parent 의존성 RED·actual GREEN·native 원형을 보존한다. 기존 WCH 원 seed/genuine/profile/로그를 복제해 수선하거나 다시 실행하지 않는다.

미실행 기대 부채도 구별한다. b723의 test_completed_unfinished_real_host_remains_dependency_pending은 당시 구형 host 거절을 기대한 원 검사이며 이 새 host3 조합에서는 그 가정이 바뀐다. registrar test는 개발1 소유라 원형을 유지하고 실행하지 않았다. 해당 기대의 버전별 제어/후속 정리는 개발1·총괄이 담당하며, 이 연결2 PASS를 등록 전체 suite PASS로 표시하지 않는다. actual readonly current 독립 검수·D3 readback/export·PDF·실제AI/실측/규범/현장·전체 업무는 각각 별도 수용이다.

## 최초 오류 보존 보완 — 2026-10-26

DEV2-WORKFLOW-HOST-FIRST-FAILURE-FIX-001은 정확226 base의 별도 clone/branch에서 host/test/usage3만 수정한다. completed-current WIP는 다른 clone에 그대로 동결하며 이 수정에 포함하지 않는다. 기존 _run.error는 최초 ordinary 오류가 있어도 후행 CONTROL을 마지막에 전파해 이미 만든 최초 실패 DTO를 가리는 문제가 있다. ordinary/CONTROL 여부와 관계없이 첫 오류 원객체 하나를 보존하고, 그 객체가 CONTROL인 경우에만 마지막에 그대로 전파하는 최소 수정이다. receipt 필드·정상 v1/v2 dispatch/permit/anchor/원 실행 경로는 바꾸지 않는다.

사전 고정 검사는 새 --first-failure의 다섯 논리다: v1 ordinary→후행 Store close CONTROL4종, v2 ordinary→후행 ledger close CONTROL, 최초 CONTROL→후행 ordinary, 서로 다른 CONTROL2개의 첫 객체, 선행 오류 없는 owned Store close ordinary/CONTROL. 원 ordinary의 오류 DTO·그 뒤 cleanup 오류 기록·known Store/ledger close 각각1회·미소비 baseline/permit2와 원 Store raw/native를 확인한다. 부모14/9·host7 등의 넓은 반복과 실제 loop/모델·프로필/permit 발급·원 운영17 변경은0이다. authored synthetic fixture의 setup과 제품의 미소비 경로를 구분한다.

- [x] 최소 RED 원본 보존
- [x] first-primary 최소 수정과 같은 좁은 다섯 논리 GREEN
- [x] 원50 test method AST·범위 밖1989 파일 raw/native 보존
- [ ] 정상 commit/push·원격 exact 뒤 root 독립 delta·회귀 수용

실제 관측은 서로 구분한다. 첫 RED는5논리/1.075초/6 failure이며 실제 ordinary→후행 CONTROL 재현5와 관측 Proxy가 G3 exact Store 타입 검사에 걸린 준비/기대 오류1을 포함한다. 원 prefix를 보존하고 실제 Store 객체의 close만 관측하도록 고친 proper RED는5논리/1.388초/5 failure다. 첫 GREEN은 같은5논리/1.459초/exit0 PASS이며 같은 정상 검사를 다시 반복하지 않았다. 4개 CONTROL subtest를 별도5개 논리로 부풀리지 않는다.

core는 초기 control→primary, nonlocal, 첫 객체 무조건 보존, 마지막 isinstance(primary, CONTROL)의 네 군데만 바꿨다. 새 테스트 메서드5+관측 helper2를 추가하고 원50개 메서드 AST는 동일하다. 세 raw namespace의 파일301/보존4,719,717바이트와 호출 관측32개는 재실행·준비 오류를 포함한 보존량이며 고유 통과 논리의 합계가 아니다. 각 호출에서 Store raw/native·업무 행·baseline/permit2 불변, known Store/ledger close 각1회, producer argv0을 관측했다. 최대 namespace는104파일/1,579,239바이트이며 OS 물리적 peak는 null이다. 실제 runtime/모델·OS KnownFolder 프로필/실제 permit·운영17 변경은0이다. private `.local/FHF-001/`에 첫 실패·proper RED·첫 GREEN·관측 원형과 source 보존 목록을 보존한다. 독립 검수·총괄 회귀·completed-current 구현은 이 통과 주장에 포함하지 않는다.

## completed current 명시 경로 — 구현 계약

2026-10-26 Asia/Seoul. DEV2-WORKFLOW-CURRENT-HANDOFF-001은 정확226a5182fbc4f88d1321eea6a6cee0e668ac598d에서 시작한 별도 clone/branch의 host/test/usage3만 소유한다. 원 WIP bytes29272/SHA0663a1b3는 정상 c19f21e에 보존하고 수용 d318 최초 오류 수정을 e741663으로 정상 cherry-pick했다. 문서 충돌은 두 계약을 모두 보존해 해소하고 core/test d318 exact에서 구현했다. 공동 예산의 post-hoc 합산만으로는 사전 보장이 안 된다는 root 지적을 보존하고, 별도 ERS d0fa의 수용 seam6을 7ce4bcb로 정상 cherry-pick한 뒤 host3를 재개했다. ERS 독립14/64 scopedYes·root 새8+signature2+genuine trial1=11 PASS와 이 후보의 통과는 별개다. ERS alias851은 이 후보에서 미반영이며 source6은 수용 d0fa exact다. native-intake3·schema3 등록3은 개발1 단독 소유이고 현재 reader·Store·D1/D3/D4 코드는 이번 수정 밖이다. 원87/226·원 No/실패·proof는 동결 유지한다.

새 workflow는 native schema_version=3 exact14, 즉 v2 exact13+context_scope="completed_current_provided"다. ref=None/명시 policy exact2·원 workflow SHA/config/finite permit/모델/시간·파일 한도는 유지한다. v1/v2는 기존 queued/G3 경로를 그대로 사용하고 schema3만 completed readonly current/facts-plan API로 분기한다. instructions나 C1을 고쳐 원 provider 문맥을 현재처럼 만들지 않는다. current context/analysis/facts-plan의 원 입력을 사용하며 원 queued plan/result는 과거 원형이다.

completed 전용 범위 검사는 단순한 _dedicated 생략이 아니다. 새 분기에만 같은 Store의 SELECT snapshot으로 다음을 전부 확인한다.

1. registered_intake exact6의 source_id/intake_id/job_id/positive revision/fingerprint/files를 원 manifest·actual source/revision/job과 대조한다. 대상 job은 정확1개이고 그 intake/revision의 실제 completed job이어야 한다.
2. 원 source와 revision의 synthetic=1, intake의 현재 revision 일치·upload_incomplete 아님, source의 실제 root/bundle이 원 registered_input_root와 일치, revision files_json/fingerprint가 선택 원형과 canonical 일치해야 한다. 다른 source·파일 목록·원문 bytes를 허용하는 범위 확대가 없다.
3. 같은 Store 전체의 queued/running job은0이어야 한다. 다른 active job이 있거나 대상만 queued/running이면 차단한다. 기존 과거 completed 이력 자체를 삭제·수정하거나 대상으로 선택하지 않는다.
4. scope snapshot 전후로 current readonly API를 한 번 호출한다. 원 context의 job/intake/revision와 원 analysis·current plan 전체 canonical SHA를 profile의 사전 명시 context/analysis/plan-input SHA 및 catalog/schema SHA에 대조하고 current plan은 ready여야 한다. scope/원 submission·현재 revision/files가 달라지면 소비 전 차단한다. 원 files를 다시 확인하는 마지막 native 등록 검사 뒤 completed SELECT snapshot도 소비 전에 다시 대조한다.
5. 제품은 claim/complete/respond/행 UPDATE·DML/새 parser/Store 초기화·원 권한 발급을 호출하지 않는다. queued 자료만 있으면 진짜 public claim→strict 분석→complete_job이 별도 선행되어야 하며 새 scope가 그 절차를 위장하지 않는다.

이번 실증은 TXT1이다. owner base의 native _registration PDF suffix unsupported_schema는 변경하지 않았다. D1 G3 schema2/PDF·native PDF 입구·등록3은 개발1의 별도 변경/수용과 구별한다. 이 host의 TXT 모의 종단1을 PDF 정식 종단 지원의 검증으로 환산하지 않는다. 새 scope를 이유로 기존 helper 거절을 우회하지 않는다.

실행은 위에서 확인한 동일 current context/analysis/plan으로 원 adapter→selector/finalizer를 사용한다. D3의 독립 current3 readback/export에 줄 공급 원형을 고정 `current-handoff.json`으로 보존한다. exact6은 schema_version:int1, kind:codex_conducted_workflow_current_handoff, workflow_sha256, current_facts_plan:원exact3, execution_receipt:원pin2|null, finalizer_receipt:원pin2|null이다. caller-request.json은 plan binding/source 설정만 담으므로 그 파일에서 current를 역산하지 않는다. summary12/finalization5·원 receipt/DTO에는 새 필드0이다. 원 current 지시/C1과 원 queued 지시/C1을 따로 보존한다. 이 파일은 입력 공급 기록이며 원 AI·권위·실측 진위 인증이 아니다.

staticYes M1의 timing/용량은 다음과 같다. 전체 입력/현재 binding·output-ready 검증 전 파일0이다. v3만 소비 전 기존 _OutputBudget에서 H1파일을 먼저 예약한다. H는 고정 exact6의 원 current3/workflowSHA와 최대 execution pin(256KiB/64hex), finalizer pin(2MiB/64hex)을 직렬화한 길이이며 UTF-8 canonical 최대8MiB·기존 native JSON depth24/node50000/유한 수·int64를 통과해야 한다. 실제 pin 또는 null은 그 상계를 넘지 않는다. 최종 finally write는 이미 예약한 H 안에서 xb 최대1회이고 이 파일을 다시 reserve하지 않는다.

같은 소비 전에 loop known 밖의 tail10파일/5505024B도 상계한다. execution-receipt1/262144B+writer reserve8/3145728B+finalizer-receipt1/2097152B다. 기존 native writer의 pending3+final3(하드링크의 각 논리 이름도 전체 bytes로 계산)+failure1은 최대7파일/2641920B = 2×(1MiB+256KiB+8KiB)+4KiB라 원8/3MiB 안이다. directory·loop known 산출물은 이 tail에 중복하지 않으며 원 profile/claim/SQL은 evidence-root 밖의 기존 별도 control cap을 유지한다. 이 source와 cap·include/exclude 목록을 private 사전 증명에 고정한다.

host는 H+tail exact2 {files,bytes}를 수용 ERS의 evidence_reservation으로 실제 adapter→loop에 전달한다. loop의 매 write·producer·journal·final receipt admission이 같은192/32MiB에서 이를 미리 제외하므로 실행 종료 뒤 초과를 발견하는 방식으로 준수를 소급하지 않는다. 후행 host는 같은 H 예약에 실제 loop prefix를 합산하고 원 execution save·writer reserve·finalizer save를 O(1)로 admission한다. 원 execution/finalizer pin 또는 null 확정 뒤 finally에서 고정 파일을 기록한다. partial/존재 충돌이면 원 prefix와 최초 오류를 보존하고 repair/retry/overwrite0이다. 선행 ordinary를 후행 CONTROL로 뒤집지 않고 최초 CONTROL만 원객체로 전파한다. handoff 실패를 성공으로 가리지 않으며 summary12/finalization5에는 필드를 추가하지 않는다.

계획은 사전 규범/독립 preseal→작은 RED→schema3/current scope 구현→typed 준비/차단·최초 오류→genuine MOCK≤1→source/Store 무쓰기/native 검증→정상게시·동결 순서다. 기존14/9·host7·registration7/parent 회귀를 반복하지 않는다. 새 TXT disposable Store 1건을 genuine public claim/strict/complete로 준비하고, product 호출과 setup의 DML·모델0을 분리한다. typed 실패는 보존 snapshot/새 test-only 복사본에서 수행한다. genuine loop는≤1이며 producer60초/loop180초/retry0/기존 disk cap을 유지한다. 실제 원Store/운영17·authority/profile/실permit·실제AI/ADC/Vertex/실장비·peer/하위 agent는0이다.

- [x] root 독립 preseal 및 M1 handoff 형상/시점·d318 최초 오류 범위 확정
- [x] 기존 v1/v2 보존·schema3/current binding의 작은 RED
- [x] completed1·미완료/다른분석/범위/드리프트·control/최초 실패의 typed 검사
- [x] H+tail 소비 전 상계/수용 seam 전달·exact6/원pin|null·partial/존재 충돌 보존
- [x] 한 completed current snapshot의 genuine MOCK1·재소비 거절·원 current 공급/출력 보존
- [ ] 정상 commit/push·pin 인계 뒤 root 독립/통합 수용

정식 _prepare(root,config,scenario,owned)의 반환은 원5tuple(workflow,context,analysis,plan_input,schema_bytes)이다. owned.store는 caller가 정확히 닫아야 하는 native lease이고 schema3 성공 때 current_facts_plan 원exact3와 completed_scope SELECT snapshot을 함께 보존한다. 원 _prepare 호출만으로 claim/complete/permit 소비/runtime/handoff 파일이 생기지 않는다. 개발1의 후속 registrar는 이 실제 검증면과 제공 원자료/현재 대조를 재사용할 수 있으며 정답 callback으로 생략하지 않는다.

실제 기록: seed 준비 import 위치 실패1(생성 전), Store.open_existing의 str 요구 실패1(queued 준비 후 claim 전)을 보존한 뒤 새 TXT seed1을 public proceed/claim/strict/complete로 완료했다. 원 seed/profile의 finite fixture permit이 기다리는 동안 만료되어 그 bytes를 보존했고, 매 case의 별도 AUTHORED 복사본에만 setup 중 now+1h의 test-only expiry를 써서 workflow SHA에 묶었다. 실제 OS profile/permit/새 승인·기존 운영17·실모델은0이다. 같은 완료 Store/원 queued/current 문맥은 보존했다.

RED preflight2/0.464초는 유효schema3 거절1/legacy PASS1이고 GREEN2/0.464초다. handoff RED3/0.807초는2failure/2error(subtest 포함), 첫 GREEN3/0.757초다. 최종 typed12는 preflight2/0.475초·closed shapes1/0.767초·binding1/1.691초·scope2/1.715초·handoff6/1.584초의 별도 cohort이며 모두 통과했다. 5SHA·selection4·다른 분석·원 파일·active/미완료/current drift·reader 최초 오류/known close1·8MiB/depth24/node50000·null pin·partial/존재 충돌을 포함한다. 원57 테스트 메서드 AST는 동일하다. typed12는 동일 함수 객체의 test_current_* alias로 표준 discovery에도 각1회 선택되며, 각 typed method의 test proof namespace만 별도512파일/32MiB로 제한한다. 제품 예산은 reset하지 않는다. genuine은 --current-genuine opt-in이고 같은 seed의 one-shot guard로 최대1회다.

단 한 번의 genuine MOCK1은4.512초/exit0, 같은 원 APIs와 한 runtime·mock model child5·selector/finalizer stored/DRAFT를 실제 실행했다. H 최대8663B+tail5505024B = external11파일/5513687B, loop 잔여181파일/28040745B를 소비 전에 전달했다. 실제 handoff8661B, evidence106파일/3415971B다. Store raw/native·업무 행은 동일하고 새 AUTHORED workflow ledger만2→5, 같은 current 입력/plan·원 receipt pins·summary12/finalization5·재소비 거절·child reaped를 확인했다. current C1 6b8d8052와 원 queued C1 7ab5ecd3를 서로 바꾸지 않았다. actual AI/물리/규범 적합성·전체 업무 완료를 입증하지 않으며 원wall257초>180 관측 한계도 별도 보존한다. private `.local/WCH-001/`의 원 prefix·proof와 각 분모를 합산해 고유 통과를 부풀리지 않는다. final cohort exit 로그의 literal backslash-n 행끝은 원형 보존하고 도구 returncode0와 정식 집계에 구별해 기록한다.

후속 공백은 개발1 schema3 정식 등록과 최종 host pin 결합, D3 readback/export 소비의 독립 current 재검증, PDF 정식 host의 별도 종단 검증이다. 이 TXT 모의1을 실제 AI·실장비·현장/규범·전체 무인화 수용으로 승격하지 않는다.

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
