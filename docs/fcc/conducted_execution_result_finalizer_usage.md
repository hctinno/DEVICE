# 실행된 conducted 결과의 finalizer

2026-10-26 Asia/Seoul. 제품 함수는 이미 실행된 [D2 adapter](intake_plan_virtual_execution_usage.md)의 원 receipt와 명시 evidence_dir만 받는다. 새 실행·모델·Store·장비 호출은 없다. 독립 수용 전인 후보 의존성을 포함해 시작한 개발 후보이며, 후행 인수 상태와 이 후보의 독립 검토는 구별한다. 전체 시험소 업무·규범 승인·물리 정확도 검증은 별도다.

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

expected_execution_sha256은 LF 없는 원 adapter canonical JSON의 lowercase SHA256이다. 이는 제공 snapshot의 일관성 pin이며 실제 AI·발급자 인증이 아니다. measurement_ref=None은 D3의 원 missing-reference 이유와 null을 보존한다. 마지막 값·PASS·유리한 측정을 고르지 않는다.

고정 파일5개만 열어 원 adapter의 artifact descriptor와 bytes/SHA를 대조한다: caller-request.json(256KiB), setup-snapshot.json(1MiB), operator-journal.jsonl(9MiB), legacy-harness-report.json(256KiB), legacy-harness-events.json(8MiB). 경로를 descriptor나 nested raw ref에서 만들지 않는다. 다른 run·전체 디렉터리·wildcard 검색은 없다. native adapter≤256KiB/depth32/nodes1M, 읽기 합계≤32MiB, 입력5와 writer 최대7 경로는512개 미만이다. Windows 공통 handle-relative reader의 reparse·identity·stamp·읽기 pin을 사용하며 다른 플랫폼 fallback은 없다. 읽기 pin 해제까지 확인한 detached snapshot으로 다음 단계에 들어간다.

원 D1 binding6/plan pin·source6, caller request·loop 선언, 실제 setup hash, journal header의 run/runtime·topology·catalog·host source pin fingerprint, host_evidence와 원 events/report를 같은 파일에서 대조한다. source pin 경로의 실제 소스나 고객 원문을 다시 열지 않는다. post-run journal은 실시간 durable journal로 승격하지 않는다. prefix·누락·오류를 원 receipt에서 지우지 않는다.

genuine read_operator_journal → [D3 순수 builder](conducted_twin_result_usage.md) → [D3 native writer](conducted_result_artifact_usage.md) 순서다. 수학·기준면·quantity 정책은 D3를 그대로 사용한다. 잘못된 quantity/sign/bool·이미 보정됨·누락·stale·invalid의 결과와 원 DTO를 수정하지 않는다. writer에는 원 run/runtime와 실제 D3 결과 canonical SHA만 전달한다. 별도 계산·기준·PASS 합성은 없다.

## 반환·실패

반환 exact11은 schema_version, kind, status, execution_receipt, input_files, result, artifact, failure, secondary_errors, verification, execution_authority다. kind=conducted_execution_result_finalizer, status=held/stored는 저장 상태만 뜻한다. execution_receipt는 detached 원형, input_files는 고정 파일의 검증 bytes/SHA, result와 artifact는 각각 원 D3 DTO다. 미도달 값은 null이며 다른 run ID나 성공 값을 채우지 않는다.

원 producer/adapter failure가 있으면 최초 failure로 보존한다. 이후 입력·builder·writer·close 오류는 secondary_errors에 남기며 원인을 덮지 않는다. D3 failure도 원형으로 보존한다. ConductedExecutionResultFinalizerError는 정제 code, stage, receipt를 제공하며 실패 receipt.status=held다. D3 writer 오류의 code/phase/publication_attempted는 보존한다. 원 예외 문자열·객체 repr는 저장하지 않는다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파한다.

verification은 evidence_snapshot_verified, recording_mode, origin_authenticated=false, ai_model_called=null, execution_rerun=false, source_bytes_reopened=false, hardware_verified=false, physical_verified=false, full_task_verified=false, method_approval=not_assessed다. execution_authority=false. storage complete는 원 result.status recorded/incomplete/invalid와 별도이며 정식 적합 판정은 not_assessed/null이다.

자체 오류 prefix는 conducted_execution_result_finalizer_이며 suffix는 input_invalid, execution_hash_mismatch, unbound_execution, binding_mismatch, artifact_descriptor_invalid, evidence_missing, artifact_incomplete, artifact_hash_mismatch, evidence_changed, unsupported_platform, evidence_json_invalid, evidence_read_failed, evidence_close_failed, builder_failed, storage_failed다. writer의 publication_uncertain도 storage_failed receipt의 원 writer code/phase/publication_attempted로 구별한다. 실패 목적지·prefix를 지우거나 자동 재시도하지 않는다.

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
