# 실행된 conducted 결과의 finalizer

## 명시적 불확도 검토 입력 전달 — 2026-10-26

최종화 API에 keyword-only `uncertainty_inputs=None`을 추가했다. 생략 또는 None이면 writer에 이 키를 전달하지 않고 기존 인자·반환 exact11/선택 모드 exact12·result JSON·DRAFT·manifest bytes와 budget 호출0을 유지한다. 값이 있을 때만 기존 native snapshot 한도(UTF-8 262144 bytes, depth32)를 적용한 후 원 result 객체를 [기존 artifact writer](conducted_result_artifact_usage.md)에 전달한다. 외부 객체/subclass hook, 순환, 비유한 수, 초과 입력은 evidence open 전에 input_invalid로 거절한다.

입력 형상은 native exact dict `{"components": components, "policy": policy}`다. [805 budget의 현재 지원](conducted_uncertainty_budget_usage.md)은 호출자가 명시한 성분·uncorrelated 가정·양의 coverage_factor와 그 근거다. 행렬·상관 추정·기본 k 또는 근거를 만들어 주지 않는다. 구성요소가 없거나 지원되지 않는 상관 가정이면 기존 budget의 not_assessed/null/reasons를 그대로 DRAFT 부록에 싣는다. 계산값을 정식 결과에 적용하지 않으므로 `result.calculation.conformity.uncertainty_db is None`과 `budget.verification.applied_to_result is False`는 유지한다.

```python
finalized = finalize_conducted_execution_result(
    execution,
    expected_execution_sha256=pin(execution),
    evidence_dir=explicit_retained_evidence_dir,
    measurement_ref=explicit_same_run_measurement_ref,
    workspace_root=workspace_root,
    artifact_name=unique_artifact_name,
    uncertainty_inputs={"components": declared_components, "policy": declared_policy},
)
```

새 실행 없이 이미 결합된 원 source/ref를 사용한다. 기존 `measurement_selection_policy`도 그대로 사용할 수 있으며 이때 measurement_ref=None 규칙을 유지한다. 불확도 옵션으로 selector·quantity·원 source·최초 오류를 수선하지 않는다. 저장 파일은 기존 result.json/draft.md/manifest.json 최종3개와 기존 pending3개이며, 추가 정보는 DRAFT 부록에만 있다. result JSON과 canonical input SHA는 원값을 유지하고 manifest는 실제 payload bytes/SHA를 결합한다.

좁은 opt-in 검증은 `DGM_FINALIZER_UNCERTAINTY_REPLAY_ROOT`에 명시된 retained fixture만 사용한다. `python tests/test_conducted_execution_result_finalizer.py --uncertainty-forward`는 새7개만 선택하며 원20·writer21·부록10·기존 selector cohort나 새 실행을 자동 호출하지 않는다. fixture에는 원 실행 receipt, evidence5, 기존 None 결과/파일, 명시 입력과 제공-current 자료가 있어야 한다. 준비·수치 가정을 검사하기 전에 원 context/setup/report/events/raw를 저장해야 한다.

이번 검증은 API 미지원 RED1 FAIL(준비 오류와 구별) 후 새7 PASS를 얻었다. 공개 legacy 부모 fixture 준비2회는 첫 ref17 가정 오류와 후속 report.status 키 가정 오류를 각각 실패로 보존했다. 둘째의 원 반환 자료를 먼저 동결했으므로 추가 RF0으로 복구했다. 이 fixture가 정식 반환한 명시 ref21을 사용했고 transport의 ref17/29 또는 새 latest 선택을 전용하지 않았다. adapter/loop envelope는 제공된 typed 자료이며 실제 CodexLoop 실행이 아니다. 테스트의 .3/.4 dB, 명시 uncorrelated/k2 기대 .5/1.0은 구현 전에 봉인한 산술 기대다.

원 생략/None kwargs와 receipt·최종3/pending3 bytes 동일, 명시 budget1/원 result 동일, 부족/미지원 null, current selector exact12, 입력 조기 거절, 제어 예외 identity, 최초 오류와 native 19-byte partial 보존을 확인했다. 이후 검증 중 새 RF/모델/SQL/subprocess/실장비0이며 기존 전체 검사는 재실행하지 않았다. 17cf writer 후보를 의존성으로 재사용했으며 총괄 독립 수용은 별도 pending이다.

같은 새 optional artifact를 [기존 native reader](conducted_result_artifact_read_usage.md)가 원 manifest와 payload3 검증으로 읽었다. 이어 기존 current readback 함수의 current 공급 경계 두 곳에 명시 자료를 제공하고 실제 native artifact reader를 사용한 연결 시험에서 matched였다. 실제 Store current/SQLite 검증이 아니며 reader·허용 조건은 수정하지 않았다. reader의 `draft_content=not_interpreted`와 current 미평가·영구 승인 false, DRAFT·물리/규범 미검증은 그대로다.



## 수용 selector 수정의 의존 경계 검증 — 2026-10-26

정확7226ff857995be8e3a8788f7cd13cf353a633bfb의 별도 clone에서 수용 selector e2587e374794f902285301b01df4121ef4101fa2의 published 변경3만 정상 cherry했다. 부모는69db6f2b6477160ef054ac8ac4588f58966d732e다. root 통지의 수용 통합6de5ece1cce27a13c269a189475c0a9766a4a7cd/게시64d4391236fb2aca9bf096593cd3c5fb36a5fe54/source326을 연결하며, 이 의존 cohort의 검수·통과 수와 root의 새8/15를 합산하지 않는다.

사전 검증과 cherry를 별도 단계로 실행했다. 변경3/원 parent/지정 core pin·disjoint·staged0·own3 raw/native/index가 모두 PASS한 뒤에만 cherry했고 전후 own3 불변을 다시 대조했다. 사전 실패 때 후속 cherry를 실행하는 경로는 없다. frozen7226/cc72/d2e와 기존 proof를 수정하지 않는다.

최종 selected core는7226 원 bytes 그대로다. 새 opt-in `--selection-dependency` 한 검사는 보존된 recorded native6파일을 복사하고, selector 첫 import 전에 public 부모 builder에 명시 ValueError 한 종류를 주입한다. 실제 selector가 같은 최초 객체를 전파하는지 관측하고, finalizer의 기존 selection_failed/held·처음 failure/빈 secondary_errors·result/artifact/selection null·writer0을 확인했다. 실제 selector1/parent fault1/추가 builder0/parent 실제 계산0이며 native5파일과 원 receipt도 그대로다. 새 RF/runtime·모델·운영profile·운영SQL은 없다.

새1은0.167s PASS(failure/error/skip0)다. 원8/legacy3/20이나 부모 테스트는 반복 실행하지 않았다. defaultNone/ref·원 DTO·marker-last는 core bytes 불변으로 유지하며 정상 selected/blocked 알고리즘·수치의 추가 검증으로 이 오류 주입을 보고하지 않는다. 새 fixture root에는 원 recorded 고정 입력6만 필요하며 `DGM_FINALIZER_REPLAY_ROOT`를 지정한 뒤 다음 명령을 실행한다.

```powershell
python -B -X utf8 tests/test_conducted_execution_result_finalizer.py --selection-dependency -v
```

별도 문서 Minor로 원 suffix 열거 한 문장에 measurement_selection_invalid/measurement_selection_blocked/measurement_selection_failed 세 항목만 보완했다. 이 변경은 UTF-8/문서·diff로 확인하며 동적 검사 분모에 추가하지 않는다. root의 원 SF08 writer0 기대 불일치와 후행 공개norm 판독은 각각 보존한다. selectorblocked만 writer0이며, valid selected의 저장은 원 producer failure와 DRAFT/task 미평가를 함께 보존할 수 있다. 그 stored 상태를 업무 성공·규범 승인으로 승격하지 않는다. 이 판독 정정에 맞추어 원 기대/코드/proof를 다시 쓰지 않는다. 아래는7226의 당시 계약·검증 이력이다.

2026-10-26 Asia/Seoul. 제품 함수는 이미 실행된 [D2 adapter](intake_plan_virtual_execution_usage.md)의 원 receipt와 명시 evidence_dir만 받는다. 새 실행·모델·Store·장비 호출은 없다. 독립 수용 전인 후보 의존성을 포함해 시작한 개발 후보이며, 후행 인수 상태와 이 후보의 독립 검토는 구별한다. 전체 시험소 업무·규범 승인·물리 정확도 검증은 별도다.

## 명시 측정 선택 연결

DEV2-MEASUREMENT-SELECTED-FINALIZER-001은 root가 지정한 base4c7c7c49e185f659683b5855cbd3a774618bc0c1의 독립 clone에서 이 finalizer/core/test/usage3만 변경한다. 기존 등록921·host735·고정 ref17 profile·운영17은 수정하지 않는다. 후행 [D3 selector](conducted_measurement_selector_usage.md) cc72d9ba55eb36f6f67bb3cda650b2d5086651ff의 신규3만 정상 cherry한 f1cae01ee8de778b5d3ed913fbbeeb74c7f18f9f가 구현 부모다. root 제공 bytes/SHA와 원 source commit=cherry commit=working bytes를 대조했다. D3의 독립 수용은 아직 pending 의존이며 이 연결의 독립 검수와도 별도다.

새 keyword-only 인자는 measurement_selection_policy=None이다. 기본 None이면 기존 measurement_ref 문자열/None과 원 exact11 receipt·원 DTO·권한·marker-last·partial/first-error 경계를 그대로 사용하며 selector 호출0이다. 명시 정책은 native exact dict `{schema_version: 1, kind: "unique_same_run_sensor_acquisition"}`만 허용한다. bool-as-int/subclass/추가 키를 거절하며 measurement_ref와 policy가 둘 다 non-None이면 입력 오류다. profile의 원 ref를 사후에 교체하는 기능이 아니다.

명시 정책 경로만 receipt에 measurement_selection을 추가한 exact12다. 처음 null에서 원 native5파일의 pin/knownclose·binding 대조 뒤 pure selector를 한 번 호출해 반환한 detached 원 선택 DTO를 보존한다. 최종 root 계약은 exact9 schema_version/kind/status/candidate/measurement_ref/request_id/reasons/result/verification이다. 앞 exact8 초안은 이력이며 후행 exact9가 우선한다. candidate는 null 또는 request_id/intent_ref/receipt_ref/measurement_ref/sequence exact5의 원 추적 근거다. selected만 top ref/request를 제공하며 blocked는 둘 다 null이고 candidate와 원 invalid/incomplete result를 nested 선택 DTO에 보존한다. D3가 내부 builder를 한 번 호출하고 돌려준 원 result를 기존 writer에 전달하며 finalizer에서 수치를 다시 계산하지 않는다. 유일한 양의 sensor.acquire 요청의 최초 native 완료 관측을 구조·clock·setup·report로 대조한다. 값/PASS/마지막 측정 선택, 최초 완료가 invalid인 경우 fallback, 자동 retry, 새 runtime은 없다.

선택 blocked면 기존 FinalizerError의 stage=selection·held receipt, result/artifact=null·writer0이다. 원 producer 실패가 있으면 최초 failure로 남기고 뒤의 선택 사유를 secondary_errors에 보존한다. 원 선택 증거를 보존하며 승인이나 실측 성공으로 승격하지 않는다. native5파일/close/binding에서 실패하면 selector도 실행하지 않는다. 선택 결과를 저장하는 marker를 별도로 만들지 않는다.

전달 방식 대안 중 selector ref만 받아 finalizer가 다시 계산하는 경로 대신, root가 D3 내부 builder1/원 result 반환을 고정했다. 공개 API를 임의로 추측해 import하거나 새 실행으로 fixture를 만들지 않는다. 기존 20개 전체 replay는 이번 기본 실행 범위가 아니다. 변경이 닿는 legacy 문자열·None·early error를 이름 붙인 작은 cohort로, 새 연결 접점8개 안팎을 별도 cohort로 검증하고 새로운 결함이 남을 때만 범위를 넓힌다.

- [x] 지정 base·소유3·비소유1964 raw baseline 및 기존 retained fixture locator 확인
- [x] root의 정책/반환/blocked/builder1/검증 범위 고정
- [x] 선택 policy keyword의 작은 계약 RED와 기존 분기 seam 준비
- [x] root가 전달한 D3 공개 API/source pin binding 후 selector1→원 result→writer 연결
- [x] 닿는 기존 분기·새 접점을 분리 검증하고 AST/원 DTO/first-error 경계 확인

Git 게시와 원격 exact 대조·보존 proof pin은 최종 인계 기록에서 확인한다. 이 후보의 독립 검수는 아직 대기다.

실제 installed profile·새 실 permit·실제 모델·ADC·Vertex·실장비와 새 runtime은0이다. 보존 입력의 genuine 선택·저장과 새 runtime/모델 실행을 구별한다. 아래 576의 원 사용법·20개/별도 fresh 시연 이력은 이 후속 실행 수와 합산하지 않는다.

소스 binding 전 준비 검사는 계약1(0.000s), 입력2(0.057s), 명시 authored-protocol 접점3(0.543s), 원 byte legacy3(0.407s)가 각 별도 실행으로 통과했다. protocol은 실제 D3 선택을 대체한 경계 검사이며 genuine selector 검증이 아니다. legacy3은 문자열 한 건·None 미선택/null·early execution pin error만 재생했다. 원20 전체와 새 runtime을 실행하지 않았다. 첫 legacy3의2PASS/None 기대 오류1FAIL은 원 D3의 invalid/null을 incomplete로 좁힌 테스트 기대 오류이며, 원 결과를 바꾸지 않고 기대만 기존 invalid/incomplete 범위로 정정했다. 초기 protocol 준비의 중복 def/IndentationError(API0), 후행 keyword 부재의 RED3도 별도로 보존한다.

추가 준비 authored-protocol5는1.036s PASS이며 앞3과 중복 합산하지 않는다. source binding 후 단독 genuine1은0.250s PASS, 최종 새 cohort는 입력2+protocol5+genuine1=8개가1.298s PASS, 별도 legacy3은0.391s PASS이며 각각 failure/error/skip0이다. 반복 통과를 독립 분모에 더하지 않는다. genuine 선택은 원 intent event:11/receipt event:12/최초 완료 event:17을 보존하며 raw -19.5 dBm과 원 보정11 dBm/result 전체가 기존 legacy의 저장 DTO bytes와 일치했다. selector1·그 내부 builder_calls1·추가 finalizer builder0이고 native writer payload/완료 marker pin도 확인했다. 새 runtime·부모 D3 tests 실행0이며 원20을 확대 실행할 새 제품 결함은 남지 않았다.

새 검사는 selection_ 접두어와 명시 --selection-contract/--selection-legacy/--selection-input/--selection-protocol/--selection-genuine/--selection-boundary opt-in으로만 고른다. 기본 discovery의 기존20에 새 fixture 의존이나 genuine selector 실행을 섞지 않는다. 원20은 열거만 했으며 공개 signature 기대에 새 keyword만 추가한 기존 한 검사 외의 원 method AST는 같다. 새 cohort에는 보존된 recorded/producer_failure 고정 입력12파일과 이전 legacy의 원 result2파일을 명시 fixture root로 공급했다. authored-protocol은 완전한 native DTO의 경계 double이며 실제 선택·수치 검증으로 보고하지 않는다.

explicit 경로에서만 고정 D3 모듈을 lazy import한다. root source pin 전 실제 import/selector0을 유지한 뒤, 후행 source binding 후 위 genuine 접점을 실행했다. policy 검사는1KiB, 선택 DTO의 native snapshot은2MiB 이내다. D3의 제공 입력16MiB/4096 events/32 setup·부모 result1MiB 제한을 finalizer가 완화하거나 재계산으로 우회하지 않는다. selection stage의 자체 code는 measurement_selection_blocked/measurement_selection_invalid/measurement_selection_failed를 기존 prefix 뒤에 붙인다.

의존 추가 전 WIP3 raw/native/index 사본과 staged0을 보존했다. 사전 verifier가 D3 test 경로를 잘못 추정해 실패했는데 뒤 cherry가 계속 실행된 순서 오류도 기록했다. 실제 added-only3·원 parent/세 source pin·전후 WIP3 raw/native/index 불변을 사후 대조했으며 stash/reset/덮기/정리0이다. 잘못된 복원 patch의 거절도 파일 변경0으로 보존했다. `_snapshot/_note/_adapter/_read_inputs/_bind`·원 error class·기존 receipt 생성식과 CONTROL handler AST는 동일하다.

```python
receipt = finalize_conducted_execution_result(
    execution_receipt, expected_execution_sha256=execution_sha256,
    evidence_dir=evidence_dir, measurement_ref=None,
    measurement_selection_policy={"schema_version": 1,
                                  "kind": "unique_same_run_sensor_acquisition"},
    workspace_root=workspace_root, artifact_name="explicit-selected-result",
)
```

검증용 명시 fixture root를 공급한 상태에서 `python -B -X utf8 tests/test_conducted_execution_result_finalizer.py --selection-boundary -v`와 `--selection-legacy -v`를 별도 실행한다. 이 명령은 보존 byte 재생이며 --fresh 경로와 합치지 않는다. proof는 실행별512파일/32MiB admission을 쓰고 native writer용32파일/8MiB를 먼저 예약한 뒤 한 번 관측한다. 기존 산출물·실패 prefix를 삭제하거나 이동해 재시도하지 않는다.

## 공개 계약과 순서

```python
from labflow.conducted_execution_result_finalizer import finalize_conducted_execution_result

receipt = finalize_conducted_execution_result(
    execution_receipt,
    expected_execution_sha256=sha256(canonical(execution_receipt).encode("utf-8")).hexdigest(),
    evidence_dir=evidence_dir,
    measurement_ref="event:17",  # 호출자가 명시한 같은 journal observation ID
    workspace_root=workspace_root,
    artifact_name="caller-selected-unique-name",
)
```

expected_execution_sha256은 LF 없는 원 adapter canonical JSON의 lowercase SHA256이다. 이는 제공 snapshot의 일관성 pin이며 실제 AI·발급자 인증이 아니다. measurement_selection_policy=None 경로에서 measurement_ref=None은 D3의 원 missing-reference 이유와 null을 보존한다. 마지막 값·PASS·유리한 측정을 고르지 않는다.

고정 파일5개만 열어 원 adapter의 artifact descriptor와 bytes/SHA를 대조한다: caller-request.json(256KiB), setup-snapshot.json(1MiB), operator-journal.jsonl(9MiB), legacy-harness-report.json(256KiB), legacy-harness-events.json(8MiB). 경로를 descriptor나 nested raw ref에서 만들지 않는다. 다른 run·전체 디렉터리·wildcard 검색은 없다. native adapter≤256KiB/depth32/nodes1M, 읽기 합계≤32MiB, 입력5와 writer 최대7 경로는512개 미만이다. Windows 공통 handle-relative reader의 reparse·identity·stamp·읽기 pin을 사용하며 다른 플랫폼 fallback은 없다. 읽기 pin 해제까지 확인한 detached snapshot으로 다음 단계에 들어간다.

원 D1 binding6/plan pin·source6, caller request·loop 선언, 실제 setup hash, journal header의 run/runtime·topology·catalog·host source pin fingerprint, host_evidence와 원 events/report를 같은 파일에서 대조한다. source pin 경로의 실제 소스나 고객 원문을 다시 열지 않는다. post-run journal은 실시간 durable journal로 승격하지 않는다. prefix·누락·오류를 원 receipt에서 지우지 않는다.

genuine read_operator_journal → [D3 순수 builder](conducted_twin_result_usage.md) → [D3 native writer](conducted_result_artifact_usage.md) 순서다. 수학·기준면·quantity 정책은 D3를 그대로 사용한다. 잘못된 quantity/sign/bool·이미 보정됨·누락·stale·invalid의 결과와 원 DTO를 수정하지 않는다. writer에는 원 run/runtime와 실제 D3 결과 canonical SHA만 전달한다. 별도 계산·기준·PASS 합성은 없다.

## 반환·실패

기존 경로의 반환 exact11은 schema_version, kind, status, execution_receipt, input_files, result, artifact, failure, secondary_errors, verification, execution_authority다. 명시 선택 경로는 위 measurement_selection 한 필드만 추가한 exact12다. kind=conducted_execution_result_finalizer, status=held/stored는 저장 상태만 뜻한다. execution_receipt는 detached 원형, input_files는 고정 파일의 검증 bytes/SHA, result와 artifact는 각각 원 D3 DTO다. 미도달 값은 null이며 다른 run ID나 성공 값을 채우지 않는다.

원 producer/adapter failure가 있으면 최초 failure로 보존한다. 이후 입력·builder·writer·close 오류는 secondary_errors에 남기며 원인을 덮지 않는다. D3 failure도 원형으로 보존한다. ConductedExecutionResultFinalizerError는 정제 code, stage, receipt를 제공하며 실패 receipt.status=held다. D3 writer 오류의 code/phase/publication_attempted는 보존한다. 원 예외 문자열·객체 repr는 저장하지 않는다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파한다.

verification은 evidence_snapshot_verified, recording_mode, origin_authenticated=false, ai_model_called=null, execution_rerun=false, source_bytes_reopened=false, hardware_verified=false, physical_verified=false, full_task_verified=false, method_approval=not_assessed다. execution_authority=false. storage complete는 원 result.status recorded/incomplete/invalid와 별도이며 정식 적합 판정은 not_assessed/null이다.

자체 오류 prefix는 conducted_execution_result_finalizer_이며 suffix는 input_invalid, execution_hash_mismatch, unbound_execution, binding_mismatch, artifact_descriptor_invalid, evidence_missing, artifact_incomplete, artifact_hash_mismatch, evidence_changed, unsupported_platform, evidence_json_invalid, evidence_read_failed, evidence_close_failed, measurement_selection_invalid, measurement_selection_blocked, measurement_selection_failed, builder_failed, storage_failed다. writer의 publication_uncertain도 storage_failed receipt의 원 writer code/phase/publication_attempted로 구별한다. 실패 목적지·prefix를 지우거나 자동 재시도하지 않는다.

## 구현 source map·검증 계획

base53cc55b461a76ae15053b9c567bc166e074595cd에 D2 4e3→11d→dd2→743과 D3 e8e→412c→e3를 정상 cherry했다. 구현 전 HEAD는2fcdbadf585faef44d57cf77d6df358df8d0899b다. 후행 총괄 수용한 [D1 facts adapter](intake_facts_to_conducted_plan_usage.md) 7d4acd45915e83f79bbff5f98d1dc66f090d5923을 추가 정상 cherry한 부모는70fc8446879b0b74914bb2a8483ff37188aaf593이다. 새 소유는 [finalizer](../../labflow/conducted_execution_result_finalizer.py), [검사·명시 mock 시연](../../tests/test_conducted_execution_result_finalizer.py), 이 usage3개뿐이다. 공통 reader는 control_packet_prepare, journal은 virtual_fleet.journal의 기존 API, 수치와 저장은 공개 D3 API를 사용한다. D3 핵심·테스트·독립 기대와 새 D1 facts 핵심·테스트를 읽거나 수정하지 않고 공개 usage API만 재사용했다.

소유743의 이미 실행된 원 파일 재생 검사는 새 execution 증거와 분리한다. 별도 fresh 합성1은 genuine D1→현재 adapter→같은 runtime의 실제 configure/acquire·관측 read·policy stop·journal→명시 ref→finalizer→D3 builder/writer를 잇는다. DUT의 물리 정지 검증으로 해석하지 않는다. fake Python executable/concrete producer/strict decoder의 scripted mock이며 실제 AI·설치 CLI·인증·운영DB·외부망·실장비 호출0이다. 기존8회/180s/60s/retry0/파일 cap을 유지한다.

## 입력 문장에서 DRAFT까지 재현

저장소 루트에서 Python 3.12와 기존 의존성으로 다음을 실행한다. 현재 clone 안의 새 UUID namespace만 사용하며 기존 산출물을 덮지 않는다.

```powershell
python -B -X utf8 tests/test_conducted_execution_result_finalizer.py --fresh-from-intake-facts --measurement-ref event:17
```

공개 시연은 새 합성 request.txt에 smartphone/SM-A176U/US/Wi-Fi 2.4GHz engineering 목적 및 한 조건의 RF6 문장을 저장한다. frequency 2412 MHz, bandwidth 20 MHz, on_average_power 11 dBm, duty_cycle 50 %, modulation OFDM, crest_factor 4 dB는 하나의 literal physical quote에 있다. 고객 실값·실제 SM-A176U 지원 주장이나 코드 기본값이 아니다.

genuine register_source/scan_source와 새 disposable synthetic Store(`is/`) → prepare_registered_synthetic_context → build_analysis_prompt → 명시 scripted mock 원 분석 응답의 decode_analysis_response → genuine build_conducted_plan_from_intake_facts → 원 plan_input → adapter → finalizer 순서다. source_settings6/basis6는 facts adapter가 실제 인용에서 조립한다. source6를 수동 주입하거나 다른 run 결과를 끼우지 않는다. method만 conducted_synthetic/version1/on/source_output 개발 계약으로 명시한다. 현재 FCC 방법·규범·실물 운전 승인은 발급하지 않는다.

원문, 실제 scan 선택, context/prompt, scripted raw response/strict analysis, facts wrapper의 plan/gaps/questions, 원 execution/result/저장 manifest를 같은 증거 ZIP에 보존한다. 문법이나 근거가 부족하면 blocked/gaps 원형을 남기고 가상 runtime을 시작하지 않는다. 시연은 현재 닫힌 문법·같은 quote의 합성 한 조건이며 자유문장 해석·실제 AI 능력의 검증이 아니다. producer.kind=model도 mock 선언이지 인증이 아니다.

출력 JSON의 expected 상태는 source6_assembly=genuine_cited_intake_facts, result_status=recorded, storage_status=complete, conformity=not_assessed다. 명시 event:17이 그 새 report에 없으면 중단하며 다른 측정을 고르지 않는다. 기존 실제 모델 응답을 편집하거나 다시 호출하지 않는다. 원 proof_directory의 finalizer_fresh2_intake_facts_mock-*.zip에 원 파일과 `.local/conducted-result-artifacts/fresh-draft/` payload/manifest가 들어 있다. wildcard는 사용자가 결과 ZIP 이름을 찾는 설명이며 제품 입력 탐색에는 쓰지 않는다.

개발 선언 source6에서 시작한 앞선 별도 합성 경로도 보존한다. 이것은 입력→facts 연결의 대체 증거가 아니다.

```powershell
python -B -X utf8 tests/test_conducted_execution_result_finalizer.py --fresh --measurement-ref event:17
```

## 다른 consumer의 public API recipe

다른 consumer는 위 test 파일·private proof·D2/D3 핵심을 읽을 필요가 없다. 자체 opt-in 합성 orchestration에서 [등록·scan](active_intake_usage.md)의 새 synthetic source/accepted item과 원 revision.files/fingerprint를 [public context 준비](intake_preclaim_context_usage.md)의 registered_intake exact6에 전달한다. 이는 caller 소유의 새 disposable Store만 사용한다. 예제의 `now=100/101`은 합성 안정 관측용 고정 시각이며 운영 clock을 바꾸는 절차가 아니다.

원 입력 TXT의 형상은 다음과 같다. 마지막 RF 줄 전체가 features.value와 한 evidence.quote에 함께 결합된다. raw strict 분석은 schema1/producer{kind=model,name=명시MOCK명}/identity=single/facts/missing_fields=[]다. facts는 product_type=smartphone, model=SM-A176U, market=US, purpose=아래 목적, features=마지막 RF 줄 exact5개이며 각각 explicit과 원 path/sha256/line_start/line_end/quote/role=request를 제공한다. 이 분석을 만들어 주는 scripted fixture와 strict 검증을 구별한다.

```text
Synthetic engineering request; no physical or FCC approval.
product_type: smartphone
model: SM-A176U
market: US
purpose: Wi-Fi 2.4 GHz conducted engineering simulation
Condition SYN-WIFI24-CH1; single authored synthetic operating condition.
frequency: 2412 MHz; bandwidth: 20 MHz; on_average_power: 11 dBm; duty_cycle: 50 %; modulation: OFDM; crest_factor: 4 dB
```

아래는 public API만 쓰는 최소 연결이다. `registered_intake`는 genuine scan accepted의 같은 intake/revision/job 및 실제 revision files/fingerprint에서 얻은 exact6이며 임의 승인 DTO가 아니다. `raw_scripted_analysis`는 위 형상의 원 UTF-8 JSON bytes다. `execution_options`는 아래 명시 입력을 가진 caller 제공 fixture 설정이다. 자동 설치 CLI 탐색·인증·새 provider 연결·기본 model 선택은 없다.

```python
from hashlib import sha256
from labflow.store import canonical
from labflow.intake_jobs import prepare_registered_synthetic_context
from labflow.intake_model_boundary import build_analysis_prompt, decode_analysis_response
from labflow.intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from labflow.intake_plan_virtual_execution import run_intake_plan_virtual_execution
from labflow.conducted_execution_result_finalizer import finalize_conducted_execution_result

def pin(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()

context = prepare_registered_synthetic_context(store, registered_intake, producer_name=mock_name)
prompt = build_analysis_prompt(context, producer_name=mock_name)
analysis = decode_analysis_response(raw_scripted_analysis, context, producer_name=mock_name)
assembled = build_conducted_plan_from_intake_facts(
    context, analysis, expected_revision=context["revision"],
    expected_context_sha256=pin(context),
    method=dict(method_id="conducted_synthetic", method_version=1,
                metric="on", reference_plane="source_output"),
)
# Caller retains context/prompt/raw analysis/assembled, including original gaps.
if assembled["status"] == "ready_for_simulation":
    plan = assembled["plan_input"]
    execution = run_intake_plan_virtual_execution(
        context, analysis, plan, expected_revision=context["revision"],
        expected_context_sha256=pin(context), expected_plan_input_sha256=pin(plan),
        quantity=dict(metric="on", reference_plane="sensor_input",
                      loss_compensation_applied=False, loss_compensation_sign=1),
        **execution_options,
    )
    finalized = finalize_conducted_execution_result(
        execution, expected_execution_sha256=pin(execution),
        evidence_dir=execution_options["evidence_dir"],
        measurement_ref=caller_measurement_ref,
        workspace_root=workspace_root, artifact_name=unique_artifact_name,
    )
```

execution_options의 required8은 catalog_path:Path, catalog_sha256:lowercase SHA64, response_schema_bytes:승인 원 literal bytes(3052B, 재직렬화 금지), executable:명시 fixture Path, requested_model:명시 string, scenario="normal", evidence_dir:새 absolute Path, execution_origin="mock_subprocess"다. cancel_event는 선택이다. source_settings/basis/plan_binding을 이 dict에서 새로 만들지 않는다. 원 plan을 adapter가 재검증해 전달한다. [기존 loop 공개 경계](virtual_fleet_codex_virtual_loop_usage.md)와 [concrete producer](codex_cli_response_usage.md)의 같은 모델·schema·상한을 적용한다.

executable은 consumer가 명시적으로 제공한 bounded fake executable 또는 scripted producer fixture 경계여야 한다. origin 문자열만으로 subprocess가 mock으로 바뀌지는 않는다. owner 시연은 기존 test-only Python child/producer 경계를 사용했으며 그 monkeypatch를 생산 경로에 옮기는 지침이 아니다. 실제 CLI 실행 파일을 넣어 이 합성 recipe를 실행하지 않는다. fixture 제공 기능이 없으면 opt-in 시연을 미지원/미실행으로 표시하고 실제 provider로 fallback하지 않는다.

blocked이면 원 assembled를 보존하고 runtime0이다. adapter 오류는 IntakePlanVirtualExecutionError.receipt의 원 loop/failure를 보존한다. binding·파일이 갖춰진 실패 receipt도 finalizer에 제공할 수 있으며 원 producer 최초 실패가 유지된다. finalizer 오류는 ConductedExecutionResultFinalizerError.receipt를 보존하고 성공 receipt로 바꾸지 않는다. 별도 source 복구·계산·결과 repair·다른 run fallback을 하지 않는다.

consumer는 반환 top11의 원 execution_receipt/result/artifact/failure/secondary_errors를 먼저 유지한다. outer finalizer receipt는 메모리 반환이며 파일에 자동 저장되지 않는다. result의 binding exact11에서 run_id/runtime_instance_id/measurement_ref와 plan_input_sha256/setup_sha256/journal_file_sha256/journal_head_sha256/report_sha256/topology_sha256를 읽는다. early incomplete/invalid binding exact2에는 이 ID/hash9가 없을 수 있으므로 원 execution.binding과 report ID만 명시 범위로 보여주고 full_bound로 채우지 않는다.

| consumer 표시 | 실제 반환 경로·형상 |
| --- | --- |
| 저장 상태 | status=stored/held와 artifact.storage.status=complete; artifact 미생성은 null |
| 결과 상태·보류 | result.status=recorded/incomplete/invalid, result.gaps/failure; result 미도달은 null |
| 원시값 | result.raw_measurement.packet 원 object 또는 null; 임의 scalar0으로 교체하지 않음 |
| 보정값 | result.calculation.corrected=null 또는 value/unit/power_w exact3 |
| 정식 판정 | result.calculation.conformity.status=not_assessed와 원 null verdict/limit/uncertainty |
| 저장 결합 | artifact.run_id/runtime_instance_id/result_status, verification.binding_scope=full_bound/report_ids_only |
| public 파일 | artifact.files의 result.json·draft.md 각 path/bytes/sha256/media_type; path는 workspace_root 상대 |
| 완료 marker | artifact.storage.commit_marker/bytes/sha256; manifest.files는 leaf 상대 payload2개 |

실제 반환 예의 값은 fresh2 run/runtime 위 기록과 같고 result=recorded, 저장=complete, raw packet power_dbm=−19.5, corrected={value:11.0,unit:dBm,power_w:약0.0125892541179417}다. 수치의 UI 반올림은 원 result.json을 바꾸지 않는다. consumer가 파일을 읽을 때는 명시 workspace_root와 반환된 bound path/bytes/SHA만 대조한다. 고정 저장 namespace는 `.local/conducted-result-artifacts/<artifact_name>/`이며 다른 run·마지막 manifest·nested raw ref 검색은 없다. 원 result.json은 D1 plan/report·setup/계산/gaps/미검증 범위를 담고 draft.md는 같은 결과의 escaped DRAFT다. 존재만으로 완료 표시하지 않고 marker와 두 payload를 대조한다.

## 실제 검증과 남은 범위

재생 기반 owner20/20이 통과했다(3.640s). 고정 파일·같은 run의 report/source/topology/hash 교환, missing/unlisted ref, missing/wrong quantity와 bool/already-applied 원형, genuine D3 invalid DTO의 저장, native 읽기 pin의 쓰기 차단, close 전파·최초 producer 실패·제어 객체 identity·경로 fallback 금지를 포함한다. 테스트용 raw fixture는 호출자가 명시한 DGM_FINALIZER_REPLAY_ROOT에 있어야 하며 자동 검색·새 실행 fallback은 없다.

별도 fresh1은 run operator-loop-run:2a91fc4c77594baaa80d988e410152ee/runtime5dc2799c97834f078fff1edba36dc395, 별도 fresh2는 run operator-loop-run:f00bb7402afb409180de7548965e5f54/runtime c2d23a67811b438eb664c8e8681e2551이다. 각 새 genuine 가상 runtime1·mock producer5회로 recorded/complete/DRAFT까지 통과했다. 두 경우 raw −19.5dBm + 실제 구성한 attenuator10/switch0.5/coupled20dB =11dBm이며 별도 Decimal 단위 변환 상대오차<1e−12를 대조했다. 고정 합성 전파 규칙의 계산 대조이며 물리 예측 성능이 아니다. 정식 수치 한계·불확도·판정은 원 null/not_assessed다.

원 RED14/API 부재, 첫 owner14 중13 PASS/순환 fixture pin 계산 준비 오류1, 경계6 중4 PASS/제품 non-synthetic 거절 누락1·검사측 binding_scope 가정 오류1을 보존했다. 제품 거절을 추가하고 검사 가정을 실제 D3 binding 형상에 맞춘 후 owner20이 통과했다. 같은 검사의 반복 수를 독립 통과 수로 더하지 않는다.

fresh2의 첫 준비는 기존 Store blob 경로269자에서 FileNotFound로 가상 runtime0/producer0에 중단됐다. 원 ZIP·로그와 별도 경로 진단(runtime0)을 보존하고 새 disposable Store 이름을 줄여 같은 공개 API로 fresh2를 통과했다. 이전101 전체·실제모델·설치 CLI·계정/인증·운영DB·실장비·현장은 이 작업에서 실행하지 않았다. 실제 모델 누적17/Vertex 소진 상태를 바꾸지 않는다. 이 후보의 총괄 독립 검토는 제출 후 별도다.
