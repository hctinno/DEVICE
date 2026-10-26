# Conducted workflow의 수동 operator 준비

## 명시 선택 정책의 등록 binding v2 — 2026-10-26

DEV2-WORKFLOW-SELECTION-REGISTRATION-001은 정확87e343e3662fc186c420b4460063a0151c03c921의 새 독립 clone에서 registration core/test/usage3만 수정한다. 의존 [host87](codex_registered_conducted_workflow_host_usage.md)의 core26916B/SHA787620eb660dedc8f2b2cfe69da65aa567913385b7aa4336d4ccc73d304b2aa8을 바인딩했으며 독립 검수는 아직 pending이다. host/selector/finalizer/issuer/native helper를 수정하지 않는다. 이 등록 후보의 독립 검수도 별도 대기다.

preflight_conducted_workflow_inputs는 기존 required keyword measurement_ref를 유지하고 optional measurement_selection_policy=None만 추가했다. None이면 원6입력 snapshot·ref string1~200 검증·exact7 반환·pins exact5·execution_authority=false가 그대로다. 명시 policy일 때만 원 snapshot에 정책을 추가하여 ref=None과 native exact2 `{schema_version: 1, kind: "unique_same_run_sensor_acquisition"}`를 검증한다. bool/float 버전·subclass·추가/누락 키·다른 정책·ref 동시값을 거절한다. None ref와 None policy를 선택의 기본값으로 해석하지 않는다. 반환·pin에 새 권한이나 선택 결과를 추가하지 않는다.

고정 prepared-inputs-v1.json의 파일명과 trusted root-delegation-v1.json exact8은 유지한다. metadata의 원 bytes SHA를 기존 prepared_manifest_sha256으로 결합하며, 다음 두 schema만 명시 분기한다.

| metadata | 생성 workflow |
| --- | --- |
| schema1 exact14 | 기존 ref string을 가진 workflow schema1 exact12. policy 키가 있으면 거절, preflight 새 keyword0 |
| schema2 exact15 | 기존14키+measurement_selection_policy. ref=null과 위 native exact2 정책을 검증한 뒤 workflow schema2 exact13에 원값을 그대로 작성 |

schema1 정책 추가/schema2 정책 누락·None·추가 키·ref 동시값·metadata version bool/float/미지원값은 staging 전에 거절한다. policy는 유일 취득 기록을 고르는 데이터 계약이며 위임·실행 권한·추가 workflow/모델 한도를 발급하지 않는다. 기존 profile 이동·v1 자동변환·원 ref17 수정·권한 infer/fallback은 없다. root record/권위 scope/_LIMITS·원17 baseline·만료·model/quantity/tools·G3/current C1/source6/basis·SQL/marker/knownclose/fsync/NX 게시·최초primary 우선·반환 exact11을 바꾸지 않는다.

- [x] exactbase/의존 pin·독립 pending·소유3/비소유 raw/native baseline 확인
- [x] optional policy 부재 RED2와 metadata v2 거절 RED1 보존
- [x] 명시 schema2 metadata→pure preflight→동일 원 policy/ref의 workflow2 연결
- [x] 작은 pure2/native publish1/boundary4의 분리7논리 검증

preflight RED2는0.261s에2FAIL/error0, publish RED1은0.148s에1FAIL/error0이었다. 최초 pure2(0.237s)/publish1(0.543s)/boundary4(1.906s) 통과 뒤 별도 metadata 결합 입력의 누락을 발견했다. schema2/ref string/policy=None은 pureAPI의 기존 None 경로를 거쳐 staging까지 진행해0.514s의 추가 RED1 FAIL로 재현했다. 원 실패SQL/prefix는 보존하고 metadata v2에서 ref=None/policy non-None을 먼저 강제하는 guard를 보완했다. 이 guard는 pureAPI의 optional None/legacy 경로를 바꾸지 않는다.

최종 pure2는 기존0.237s PASS(해당 함수 후행 변경0), 후행 native publish1은0.595s PASS, 별도 boundary4는1.997s PASS이며 각 failure/error/skip0이다. 서로 다른7논리/분리3cohort이며 중간 통과나 기존8/9·host7을 더하지 않는다. 기본 discovery의 기존8/--boundary9와 최초오류 수정의 원 opt-in은 그대로 두고 이번 selection_ 검사만 명시 선택한다.

pure2는 v1 호출·explicit policy=None·명시 v2의 원 DTO/pins 일치와 원 input 불변·false 권위, 잘못된 policy8/ref 조합2 및 최초 MemoryError 객체 전파를 확인했다. boundary4는 metadata 형상17개, 원 manifestSHA 무결성과 권위 scope9 확대 거절, v2 ordinary SQL fsync→후행 MemoryError와 v2 최초 SQL close MemoryError→후행 directory ordinary 오류를 검사했다. 최초오류의 SQL/prefix·failure marker는 남기며 durable 준비 성공으로 고치지 않는다.

native publish1은 genuine source 등록/Store/G3/D1과 native 쓰기/fsync/SQL2/NX sibling 게시 뒤, 같은 complete marker의 prepared manifest pin/원10파일·workflow policy·config/permit SHA/원17 baseline을 대조했다. published profile의 원 파일을 보존한 채 pending host의 _prepare까지 다시 확인했고 그 전후 원 파일/SQL bytes가 같다. 빈 runs/permit은 소비하지 않았고 같은 target 재호출은 not_prepared다. host main/producer/새 runtime·모델은0이다. 테스트의 AUTHORED_TEST_ONLY 위임 record·일회용 OS parent를 실제 위임/운영profile로 해석하지 않는다.

```python
preflight = preflight_conducted_workflow_inputs(
    context, analysis, plan_input, quantity=quantity, allowed_tools=allowed_tools,
    measurement_ref=None,
    measurement_selection_policy={"schema_version": 1,
                                  "kind": "unique_same_run_sensor_acquisition"},
)
```

```powershell
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py --selection-preflight -v
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py --selection-publish -v
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py --selection-boundary -v
```

새 정책 검증은 원 snapshot 상한 안에서 수행하고 원 files/cap/IO32파일·8MiB·proof512파일·32MiB를 유지한다. 실제 KnownFolder·기존 profile·원17 장부·새 실 permit·추가 승인 record 자동 생성·실제 모델·ADC·Vertex·실장비와 peer/하위 agent는0이다. 원1 v1 기본8/경계9·host7의 일괄 실행은0이며 SQL 원장·물리/규범 정확도·실제 AI 종단 검증으로 이 준비 결과를 승격하지 않는다. 아래 d2e/921 기록은 각 당시 이력으로 보존한다.

## 최초 실패 보존 수정 — 2026-10-26

DEV2-WORKFLOW-REGISTRATION-FIRST-FAILURE-FIX-001은 정확921bdca27249fb785c1cea12f9a177cfe9a3e256에서 시작한 별도 clone/branch의 core/test/usage3 수정이다. 기존921·7226·cc72와 원 증거는 동결 유지한다. root의 등록 원 dynamic12/12 통과 통지와 후행 Important1을 구별하며 원12를 재실행하거나 이번 분모에 더하지 않는다. 이 수정의 독립 검수는 아직 대기다.

원 구현은 최초 ordinary 실패를 primary에 저장한 뒤에도 후행 cleanup control을 control에 저장하고 마지막에 던졌다. outward 전파 조건 한 줄만 `isinstance(primary, _CONTROL)`로 바꿨다. 최초가 control이면 같은 객체를 던지고, 최초가 ordinary이면 기존 실패 DTO를 반환한다. 오류 수집·first code/phase·후행 errors와 SQL/marker/native close·publish 상태 계산은 바꾸지 않는다. 새 DTO·OS 진입·정책/권한/위임값·ref 변경은 없다.

- [x] genuine authored source/Store/G3/D1 입력과 일회용 OS boundary에서 ordinary SQL fsync 실패→후행 directory-close KI/MemoryError의 원 동작 RED2 보존
- [x] 최종 outward 선택 한 줄 수정
- [x] 새 영향 경계2와 필요한 기존 최초control2만 분리 검증

수정 전 RED2는0.646s에 각각 후행 KeyboardInterrupt/MemoryError가 밖으로 전파되어 기대대로 FAIL했다. 수정 후 새2는0.728s PASS, 별도 legacy2는0.640s PASS이며 각 failure/error/skip0이다. legacy는 원 SQL-close 최초 MemoryError와 최초 write KeyboardInterrupt→후행 ordinary close 오류의 같은 객체 전파를 확인한 기존 두 검사다. 기본8/전체boundary9/독립원12의 일괄 반복은0이다.

fault seam은 실제 SQL 생성·commit/close 뒤 Python fsync에 첫 OSError를 주고, 실제 directory knownclose를 끝낸 뒤 후행 control을 주는 경계다. SQL fsync fault와 directory close 호출은 각1회, publish0이다. 원 failure marker와 failed/phase=sql·first native_or_data_rejected·후행 directory_close/interrupted가 유지됐다. 새 staging/SQL baseline·permit2행은 실패 원형으로 보존했으며 fsync 실패를 durable 준비 성공으로 표시하지 않는다. 기존 target은 없고 result.profile=null/files={}·dispatch=not_invoked다. 기존 산출물을 덮거나 삭제·이동/재시도하지 않는다.

재현과 영향 검사는 다음 opt-in 두 경로로만 고른다. 부모의 기존 테스트·일반 source 검증은 정적 AST/raw 대조로 보존하고, 원 최초 예외 선택 외 구현을 바꾸지 않는다.

```powershell
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py --first-failure -v
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py --first-control-legacy -v
```

실제 운영 OS profile/새 실 permit/host/모델/원17/ADC/Vertex/실장비와 다른 세션·하위 agent 실행은0이다. 실제 비동기 신호의 모든 시점이나 현장 검증을 이 fault-seam 결과로 주장하지 않는다. 문서 무결성·소유3 raw/index/commit·원격 exact와 보존 proof pin은 최종 인계 기록에 남긴다. 아래는 원921의 공개 계약·검증 이력이며 이 수정의 통과 수와 합산하지 않는다.

2026-10-26 Asia/Seoul. DEV2-CONDUCTED-WORKFLOW-REGISTRATION-001. 게시 ab45019e411fbd9ebde1ec091acb6e054d83af1b에 자기735만 정상 cherry한 bb7412d가 시작점이다. [735 host](codex_registered_conducted_workflow_host_usage.md)는 이 단위 시작 때 미수용 의존이었다. 후행 root 통지로 독립 qualified Yes와 root4c7c7c49e185f659683b5855cbd3a774618bc0c1 수용을 확인했다. 원 normal positive incomplete1과 별도 genuine normal1을 구별하며 이 준비 API의 검수 결과로 합산하지 않는다. 기존 host/intake permit/운영17/Store/D1/D3/UI를 수정하지 않는다.

## 실제 trust source 공백과 최소 계약

현재 공통 API에는 trusted 사용자 위임 기록과 root의 실제 수동 게시를 읽는 범용 issuer가 없다. 이 helper가 caller dict/bool/SHA에서 권한을 만드는 방법으로 이를 대체하지 않는다. 현재 OS token KnownFolder의 고정 `DGMAutoLab/codex-conducted-workflow-operator/`를 root가 기존 직접 사용자 위임과 이번 수동 준비 지시로 먼저 게시하는 좁은 operator 계약을 사용한다. 동일 계정 임의 코드에 대한 인증·방어는 주장하지 않는다.

그곳의 root-delegation-v1.json은 root가 실제로 보유한 기존 위임의 curated 기록이어야 한다. 이 API는 그 파일·operator 디렉터리·사용자 위임·새 전역 예산을 생성하지 않는다. root의 수동 준비 reference와 prepared manifest의 C1을 그 신뢰 경로에서 대조한다. 입력 자료의 문구·일반 prepared metadata·hash 일치만으로 승인하지 않는다. 없거나 범위가 다르면 not_prepared이며 다른 파일을 찾지 않는다.

```python
preflight_conducted_workflow_inputs(
    context, analysis, plan_input, *, quantity, allowed_tools, measurement_ref,
    measurement_selection_policy=None,
) -> dict

prepare_registered_conducted_workflow(*, scenario_id, requested_model) -> dict
```

첫 API는 독립 가능한 native/canonical/D1 검증만 수행한다. 반환에는 실행·profile 준비 권한이 없다. 두 번째 API는 위 고정 operator source를 읽는 명시 수동 준비 entry다. argv/env/승인 dict/경로/provider hook을 받지 않는다. module CLI는 `--scenario-id ID --model gpt-6.1-sol|gpt-6-astra`만 수용한다.

## 고정 입력 형상

root-delegation-v1.json exact8은 schema_version=1, kind=codex_root_conducted_workflow_manual_preparation, authority_source, manual_preparation_reference, action=prepare_one_registered_synthetic_conducted_workflow_profile, scope, prepared_manifest_sha256, inherited_history다.

authority_source는 기존 kind=direct_human_instructions_to_this_root_thread, instruction_reference:string, authority_is_not_inferred_from_uploaded_documents_or_model_output=true exact3다. manual_preparation_reference는 root가 실제 게시한 이번 수동 준비 지시의 reference이며 새로운 사용자 승인값을 helper가 발급한 것이 아니다. 두 reference는 nonblank UTF-8≤2048자다. 실제 인간 지시 내용의 재해석·원격 principal 검증·문서에서 권한 추론은 하지 않는다.

scope exact12는 allowed_models=[gpt-6.1-sol,gpt-6-astra], maximum_workflows=1, maximum_model_processes=8, loop_seconds=180, producer_seconds=60, automatic_retries=0, output_bytes=262144, evidence_files=192, evidence_bytes=33554432, synthetic_only=true, hardware_network_output_motion_submission=false, scope_is_existing_delegation_not_new_global_budget=true다. bool을 숫자로 받지 않으며 부족·다른 범위를 채우지 않는다.

inherited_history는735가 요구하는 원17 exact8 metadata다. actual_codex_model_processes/known_total_before_this_host=17, usage_complete=false, unknown_usage_components/cost=null, provenance_level=previous_verified_root_rollup_not_fresh_original_receipt_reaudit 및 원 source_rollup/published_source를 그대로 보존한다. 이 경로를 따라 운영17의 원 SQL/receipt를 열지 않는다. 0 seed·새 예산으로 바꾸지 않는다.

prepared-inputs-v1.json의 schema1 exact14는 schema_version=1, kind=codex_conducted_workflow_prepared_data, scenario_id, requested_model, journal_id, permit_id, registered_input_root, store_root, executable, expires_at, quantity, allowed_tools, measurement_ref, files다. schema2 exact15는 위 명시 measurement_selection_policy를 추가하고 ref=null을 요구한다. 이 파일의 원 bytes SHA가 위 trusted record의 prepared_manifest_sha256과 같아야 한다. 이것은 준비 데이터의 binding이며 이 metadata 자체가 권위 source는 아니다.

files exact5는 registered-intake-v1.json/analysis.json/plan-input.json/catalog.json/response-schema.json을 key로 가진 Pin{bytes,sha256}다. 실제 파일은 operator/prepared-data/의 같은 고정 leaf에서만 읽는다. arbitrary/nested raw ref 경로를 따라가지 않는다. manifest256KiB/analysis256KiB/plan256KiB/catalog1MiB/schema64KiB, metadata64KiB/위임64KiB를 상한으로 둔다. analysis/plan은 원 canonical JSON, schema는 승인 literal3052B/aa321 원 bytes다.

원 등록 manifest5·genuine 원 폴더 전체·existing Store/current public8·원 analysis/plan·source6/basis·명시 quantity/tools/ref를 대조한다. source6/basis·단위·기준면·null·count를 채우거나 바꾸지 않는다. source는192파일/32MiB 이내 합성만 지원한다. G3는 context/blob metadata를 retain할 수 있으므로 working Store 전체 bytes 불변을 주장하지 않는다. 업무 claim/attempt/완료나 intake permit은 소비하지 않는다.

## 준비·실패·게시

고정 target은 KnownFolder/DGMAutoLab/codex-conducted-workflow-host다. 새 sibling codex-conducted-workflow-host.preparing을 배타 생성하고735 파일 형상·baseline/단일 finite permit SQL·빈 runs/permit_id를 준비한다. host가 추가 marker를 검사하지 않으므로, 불완전 profile을 live 위치에 순차 노출하지 않고 검증·SQLite/fsync/close 뒤 native 배타 directory rename으로 한 번 게시한다. 이것은 신규 artifact 게시이며 기존·실패 원본의 정리/이동이 아니다.

기존 target·staging·claimed·SQL/원문은 덮거나 지우지 않는다. staging이 남으면 자동 재개/다른 임시 이름 우회0이다. SQL은 신규 파일에735 exact table+원17 baseline+이번 단일 permit2행만 준비하며 운영17은 열지 않는다. 원문·의미/단위·모델·scope를 repair하지 않는다. 모델/host 실행을 이 helper 안에서 호출하지 않는다.

새 marker는 profile에 넣지 않는다. operator 영역의 preparation-record-v1.json은 수동 준비 시작과 원 trusted record/metadata pin, preparation-complete-v1.json은 게시된 profile의 원 파일/SQL pin을 묶는 저장 기록이다. preparation-failure-v1.json은 best-effort 고정 실패 기록이다. 어느 marker도 추가 승인이나735가 검사하는 실행 권위가 아니다. final에는735 필수10파일과 빈 runs/permit_id만 게시한다.

실패는 stage/SQL/prefix/기록을 남기며 최초 예외·control을 close 오류가 덮지 않는다. native publish 시도 뒤 불확실하면 publication_uncertain이며 자동 rollback/repair/host 실행0이다. directory 게시에 필요한 source DELETE handle과 parent handle은 유지하지만 하위 directory와 모든 file/SQL은 먼저 knownclose한다. 게시 뒤 최종 directory close가 실패하면 완전한 final이 있더라도 성공으로 반환하지 않는다. root는 성공 반환·게시 원형을 별도 검수하기 전 실제 host를 시작하지 않는다.

실제 source Store의 synthetic 등록/G3를 먼저 확인하고 그 뒤 원 폴더 전체를 읽는다. 복사한10파일의 원 bytes/SHA·SQL2행·exactset·비어 있는 run directory 및 current G3/C1을 다시 대조한다. native input pin은 변경을 차단하며 파일·SQL fsync/close를 검증한 뒤 namespace만 배타 게시한다. current snapshot 검증을 영구 Store lease나 동일계정 공격 방어로 해석하지 않는다.

## 소유·구현 순서

신규 소유는 [preparation API](../../labflow/codex_conducted_workflow_registration.py), [검사](../../tests/test_codex_conducted_workflow_registration.py), 이 usage3개다. 계약→작은 RED→비권위 canonical/genuine native preflight→배타 staging/SQL/fsync/publish→genuine mock host 소비(model0)→실패/control/close/중복 검사→정상 commit/push 순서로 진행한다. proof 쓰기는 O(1)로 먼저 cap을 확인하고 원 실패/부분 파일을 삭제하지 않는다. 실제 installed OS profile/새 실 permit/운영17/ADC/실제 모델/장비/외부원본은 개발 검증에서0이다. 실제 준비·실행 성공으로 보고하지 않는다.

## 반환·검증 명령

preflight exact7은 schema_version/kind/status/pins/gaps/failure/execution_authority다. kind=conducted_workflow_input_preflight, status=validated/invalid, execution_authority=false다. pins는 성공 때 context_sha256/analysis_sha256/plan_input_sha256/source_settings_sha256/quantity_sha256 exact5이고 그 전에는null이다. gaps는 원 blocked plan의 부족 근거를 유지하고 failure는 고정 code 또는null이다. validated는 제공 snapshot의 데이터 일관성일 뿐 root 위임·원 bytes·실행 권위가 아니다.

prepare exact11은 schema_version/kind/status/phase/scenario_id/requested_model/operator_source/profile/files/errors/verification이다. kind=codex_conducted_workflow_registration이다. status는 prepared/not_prepared/failed/publication_uncertain, CLI exit는 각각0/3/4/5다. 인자 오류2, main의 control은 원 객체 전파, module process는 KeyboardInterrupt130/나머지 control5다. raw exception text·SQL·인간 지시 원문은 stdout에 노출하지 않는다.

operator_source는 원 root-delegation raw의 Pin{bytes,sha256} 또는null, profile은 성공/게시 불확실 때 relative_directory/permit_id/journal_id exact3 또는null, files는 원10파일의 leaf→Pin이다. errors는 phase/code exact2 최대8이다. verification exact4는 authority_scope(not_validated/fixed_native_root_manual_preparation), data_preflight(not_run/validated), dispatch=not_invoked, same_account_arbitrary_code_defense=false다. profile prepared와 실제 host/model 실행을 구별한다. 유효한 원 위임을 root가 게시하지 않았다면 native source가 없는 것이며 caller의 metadata로 보충하지 않는다.

```powershell
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py -v
python -B -X utf8 tests/test_codex_conducted_workflow_registration.py --boundary -v
python -B -X utf8 scripts/check_artifacts.py
```

기본8/8 PASS(2.571s), 별도 boundary9/9 PASS(3.467s), 각 failure/error/skip0이다. 두 UUID proof namespace의 서로 다른17논리이며 한 번의17개 실행이나 반복 통과 수의 합산이 아니다. O(1) write counter와 알려진 native 쓰기의 선예약은 실행별512파일/32MiB이고, 생성 profile 자체는32파일/8MiB 이내로 먼저 예약한다. cold file/namespace 관측은 검증 시점의 retained 값이며 native disk의 순간 최대를 주장하지 않는다.

기본 검사는 genuine source 등록/Store/G3/strict scripted 분석/facts→원D1 plan과 독립 pure preflight, 없는위임/모델·scope·8상한/기존final·partial/원17·bool·file pin 거절을 확인했다. 새 profile과 SQLite baseline/permit2행을 실제 Windows native write/fsync/NX directory rename으로 게시한 뒤735 genuine host로 소비했다. 그 자식은 명시 Python mock의 잘못된 버전만 반환해 version process1/model process0이며 원 소비·finish/claim을 남겼다. 초기2행 SQL bytes는 별도 보존하고 소비 뒤5행을 초기 pin과 혼동하지 않는다. 실제 installed CLI·실 profile·실 permit·실제 모델/운영17/ADC/Vertex/장비는0이다.

경계9는 partial write, fsync, SQL commit/control close, 최초 write control+후행close, native final collision, 게시 후close, current G3/C1, 기존 staging/Store-source 중첩을 검사했다. KI/SystemExit/GeneratorExit/MemoryError 원 객체도 pure preflight에서 확인했다. 원 RED8/API 부재, 첫8의7PASS/게시1실패(Windows AccessDenied5), 별도 진단과 하위 handle knownclose 후 단독 게시1 PASS, 중간8/9와 최종8/9를 구별해 보존했다. 같은 통과를 독립 분모에 다시 더하지 않았다.

resolved staging/final은 정확 sibling 이름과 fixed parent·native identity/reparse를 검사하고 NtSetInformationFile FileRenameInformation의 ReplaceIfExists=0을 사용한다. 기존 final·원 staging을 replace/삭제·이동하여 재시도하지 않는다. 신규 staging의 정상 게시만 namespace rename이다. 실제 root가 위임 기록을 수동 게시하거나 실제 profile/새 실 permit을 준비한 결과는 이 검증에 포함하지 않는다. 이 후보의 독립 검수는 아직 대기이며735의 후행 독립 수용과 별도다.

## 남은 연결 공백

735의 measurement_ref는 사전 명시 string이다. mock5의 event:17은 자유 AI의 다른 도구/관측 순서에서 같은 event를 뜻한다고 가정할 수 없다. 이 unit은 원 ref를 last/PASS/사후 값으로 바꾸지 않는다. 같은 plan/run/condition/quantity·실제 sensor request·완료 journal에 근거한 유일 후보 selector와 없음/복수/무효 hold는 별도 후속 계약·구현 대상이다. root가 실제 모델 실행 전에 이 범위를 검토한다.
