# Conducted workflow의 수동 operator 준비

2026-10-26 Asia/Seoul. DEV2-CONDUCTED-WORKFLOW-REGISTRATION-001. 게시 ab45019e411fbd9ebde1ec091acb6e054d83af1b에 자기735만 정상 cherry한 bb7412d가 시작점이다. [735 host](codex_registered_conducted_workflow_host_usage.md)는 이 단위 시작 때 미수용 의존이었다. 후행 root 통지로 독립 qualified Yes와 root4c7c7c49e185f659683b5855cbd3a774618bc0c1 수용을 확인했다. 원 normal positive incomplete1과 별도 genuine normal1을 구별하며 이 준비 API의 검수 결과로 합산하지 않는다. 기존 host/intake permit/운영17/Store/D1/D3/UI를 수정하지 않는다.

## 실제 trust source 공백과 최소 계약

현재 공통 API에는 trusted 사용자 위임 기록과 root의 실제 수동 게시를 읽는 범용 issuer가 없다. 이 helper가 caller dict/bool/SHA에서 권한을 만드는 방법으로 이를 대체하지 않는다. 현재 OS token KnownFolder의 고정 `DGMAutoLab/codex-conducted-workflow-operator/`를 root가 기존 직접 사용자 위임과 이번 수동 준비 지시로 먼저 게시하는 좁은 operator 계약을 사용한다. 동일 계정 임의 코드에 대한 인증·방어는 주장하지 않는다.

그곳의 root-delegation-v1.json은 root가 실제로 보유한 기존 위임의 curated 기록이어야 한다. 이 API는 그 파일·operator 디렉터리·사용자 위임·새 전역 예산을 생성하지 않는다. root의 수동 준비 reference와 prepared manifest의 C1을 그 신뢰 경로에서 대조한다. 입력 자료의 문구·일반 prepared metadata·hash 일치만으로 승인하지 않는다. 없거나 범위가 다르면 not_prepared이며 다른 파일을 찾지 않는다.

```python
preflight_conducted_workflow_inputs(
    context, analysis, plan_input, *, quantity, allowed_tools, measurement_ref,
) -> dict

prepare_registered_conducted_workflow(*, scenario_id, requested_model) -> dict
```

첫 API는 독립 가능한 native/canonical/D1 검증만 수행한다. 반환에는 실행·profile 준비 권한이 없다. 두 번째 API는 위 고정 operator source를 읽는 명시 수동 준비 entry다. argv/env/승인 dict/경로/provider hook을 받지 않는다. module CLI는 `--scenario-id ID --model gpt-6.1-sol|gpt-6-astra`만 수용한다.

## 고정 입력 형상

root-delegation-v1.json exact8은 schema_version=1, kind=codex_root_conducted_workflow_manual_preparation, authority_source, manual_preparation_reference, action=prepare_one_registered_synthetic_conducted_workflow_profile, scope, prepared_manifest_sha256, inherited_history다.

authority_source는 기존 kind=direct_human_instructions_to_this_root_thread, instruction_reference:string, authority_is_not_inferred_from_uploaded_documents_or_model_output=true exact3다. manual_preparation_reference는 root가 실제 게시한 이번 수동 준비 지시의 reference이며 새로운 사용자 승인값을 helper가 발급한 것이 아니다. 두 reference는 nonblank UTF-8≤2048자다. 실제 인간 지시 내용의 재해석·원격 principal 검증·문서에서 권한 추론은 하지 않는다.

scope exact12는 allowed_models=[gpt-6.1-sol,gpt-6-astra], maximum_workflows=1, maximum_model_processes=8, loop_seconds=180, producer_seconds=60, automatic_retries=0, output_bytes=262144, evidence_files=192, evidence_bytes=33554432, synthetic_only=true, hardware_network_output_motion_submission=false, scope_is_existing_delegation_not_new_global_budget=true다. bool을 숫자로 받지 않으며 부족·다른 범위를 채우지 않는다.

inherited_history는735가 요구하는 원17 exact8 metadata다. actual_codex_model_processes/known_total_before_this_host=17, usage_complete=false, unknown_usage_components/cost=null, provenance_level=previous_verified_root_rollup_not_fresh_original_receipt_reaudit 및 원 source_rollup/published_source를 그대로 보존한다. 이 경로를 따라 운영17의 원 SQL/receipt를 열지 않는다. 0 seed·새 예산으로 바꾸지 않는다.

prepared-inputs-v1.json exact14는 schema_version=1, kind=codex_conducted_workflow_prepared_data, scenario_id, requested_model, journal_id, permit_id, registered_input_root, store_root, executable, expires_at, quantity, allowed_tools, measurement_ref, files다. 이 파일의 원 bytes SHA가 위 trusted record의 prepared_manifest_sha256과 같아야 한다. 이것은 준비 데이터의 binding이며 이 metadata 자체가 권위 source는 아니다.

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
