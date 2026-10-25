# Codex 가상 첫 판단 실행 설계

2026-10-25, Asia/Seoul. DEV2-CODEX-OPERATOR-HOST-CONTRACT-004의 독립 정적 검토 Yes 뒤 고정한 구현 계약이다. [계획](../plans/2026-10-25-codex-first-decision.md)·[기계 판독 계약](../../fcc/codex_first_decision_contract.json)과 함께 root pin 뒤 실제 배정을 받는다. 현재 제품 구현·CLI·모델·가상 runtime 추가 실행은0이다. 기존 b9df 후보와 002/003·원 실패를 수정하지 않는다.

## 1. 단위 선택과 정확 소유

이번 단위는 fresh fullbench의 **첫 판단에 대한 producer trace와 strict wire5**다. 모델 proposal을 가상 runtime에 파견하거나 업무 완료를 평가하지 않는다. 기존 공개 callback이 문맥을 주므로 2노드 요약·역사적 snapshot 재사용·새 context getter는 필요하지 않다.

검토한 연결은 두 가지다. callback 안에서 실제 producer를 호출하고 반환 proposal을 바로 실행하면 legacy report/journal의 fixture·ai_model_called=false와 실제 호출의 provenance를 함께 바꿔야 한다. 이번에는 callback이 문맥을 포착하고 고정 stop으로 끝난 **후** producer를 호출한다. legacy 기록의 false가 그 capture fixture에 대해 사실로 유지되며 실제 trace는 별도 caller receipt에 결합된다. 모델 주도 폐루프·새 actual provenance·거절 task grader는 후속 공통 단위다. 이 선택을 총괄이 첫 구현 단위로 고정했다. 실제 모델 실행은 별도 위임과 누적 예산을 따른다.

제품 소유 제안은 정확 신규3이다.

- labflow/virtual_fleet/codex_first_decision.py
- tests/test_virtual_fleet_codex_first_decision.py
- docs/fcc/virtual_fleet_codex_first_decision_usage.md

공개 API와 __all__은 아래 함수1과 CodexFirstDecisionError 정확2다. registry·provider/capture/evaluator callback·새 SDK·CLI wrapper·상시 실행기·자동 batch 생성은 없다. 기존 harness.py/journal.py/producer/builder/decoder/fixture/evaluator는 수정하지 않는다. root가 공개 spec/plan/typed contract를 먼저 고정하고 이 정확 new3의 구현 base·branch를 배정한다.

```python
def run_codex_first_decisions(
    *, catalog_path: Path, catalog_sha256: str,
    response_schema_bytes: bytes, executable: Path,
    requested_models: list[str], scenarios: list[str],
    evidence_dir: Path, cancel_event: threading.Event | None = None,
) -> dict:
    ...
```

Path는 해당 Windows OS의 정확 type(Path())·absolute·부모를 포함해 no symlink/reparse다. catalog/executable은 regular file, evidence_dir은 기존 부모 아래 아직 없는 새 디렉터리다. bytes/list/str/Event도 정확 native type만 받는다. requested_models는 중복 없는 길이1..2이며 gpt-6.1-sol/gpt-6-astra뿐이다. scenarios는 중복 없는 길이1..2이며 normal/restored_disconnect뿐이다. 전달 순서의 scenario-major/model-minor Cartesian product가 최대4 slot인 유한 계획이다. 기본 모델/시나리오·모델 이름에 따른 prompt label 변경은 없다.

catalog bytes는 최대1MiB, catalog_sha256은 lowerhex64와 실제 bytes 일치가 필수다. 공개 loader의 원 catalog를 보존하고 factory 전후 다시 확인한다. response_schema_bytes는003의 caller literal3052B/SHA aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb와 정확히 같아야 한다. host가 schema를 새로 생성·수선하지 않는다. producer_name은 모든 slot에서 dgm-virtual-operator-v1이다. 지원 client/version·argv18·usage5·오류/한도는 정식 Codex producer 계약 그대로다.

## 2. 한 slot의 정확 순서

1. callback/공급자 객체를 받지 않는다. genuine load_catalog/get_role_actions/prepare_sensor_trial만 사용한다. seed=0·power_dbm=12.5·해당 고정 condition으로 slot마다 fresh trial을 준비한다. 작성자 record/정답·기존 actual 응답을 읽거나 모델에 주지 않는다. trusted virtual 준비의 configure/advance/조건 주입은 source recipe의 작업이며 모델 명령이 아니다.
2. 새 run_id는 operator-first-run:+uuid4 hex32, runtime_instance_id는 fresh trial의 공개 속성 그대로다. decision_id와 model_request_id는 각각 operator-first-decision:/operator-first-request:+uuid4 hex32다. 이전 slot·003 IDs를 재사용하지 않는다.
3. 기존 FleetHarness에 원 catalog/topology/goal/role_actions와 고정 예산을 주고 **step() 한 번**만 호출한다. 고정 private capture policy는 공개 context8을 분리 복사한다. 이때 trial.runtime.observations()·goal·topology·role_actions·모든 profile ID를 대조한다. 실패를 외부 latch에 처음 고정한 뒤 rethrow한다. harness가 callback BaseException을 삼켜도 producer로 넘어가지 않는다.
4. capture policy가 반환하는 값은 정확 {kind:stop, claim:blocked, reason:host_first_decision_capture}다. 모델 출력이 아니다. 정상 capture는 원 observation→고정 policy_decision→termination 3 event, policy_stop/blocked, 미결[]여야 하며 intent/receipt/advance/execute 파견은0이다. legacy result의 fixture/ai_model_called=false·not_assessed를 원형 저장한다. OperatorJournal에 실제 trace를 끼워 넣지 않는다.
5. context8 원본을 보존한다. 별도 copy에서 remaining_budget **한 필드만** 빼 context7을 만들고 remaining은 binding.json에 별도 보존한다. 고정 full delegation은 scope=rf_sensor_proposal_v1, harness_budgets={decisions:64,logical_requests:64,ticks:32,wall_seconds:30,transport_retries:2}, outer_limits={wall_seconds:60,model_calls:8}이다. 잔량을 full 선언으로 대체하거나 반대로 덮지 않는다.
6. genuine build_operator_prompt로 새 IDs/context7/delegation/중립 producer를 결합한다. canonical은 ensure_ascii=False/sort_keys=True/allow_nan=False/compact separators, LF없음이다. context·request·완성 prompt·literal schema hash를 구별해 고정한다. 같은 condition의 두 모델 slot은 context7 hash가 같아야 하며 다르면 capture_failed로 producer0이다. 새 IDs 때문에 raw prompt/request hash는 다를 수 있다. source/catalog와 현재 runtime 관측을 다시 대조하고 clock/cancel을 검사한다.
7. batch의 model slot을 **produce 진입 전** 예약한다. 한 slot당 produce_codex_cli_response 한 번, version metadata/model process는 그 함수 소유다. host가 별도 --version/login/명령을 실행하지 않는다. 반환 tuple2와 정식 receipt18을 받는다.
8. 성공 producer receipt와 producer/receipt.json이 canonical 값·exchange_ref로 같고 artifact9 literal/complete/bytes/hash가 맞아야 한다. final-text/last-message/반환 bytes가 정확히 같아야 한다. bounded exact-file 읽기만 사용하며 prefix·실패·미완료·저장 불확실성이면 decode0이다. 원 producer receipt를 수정하지 않는다.
9. cancel/deadline과 동일 runtime/context tick/revision을 다시 확인한 뒤 genuine decode_operator_response(response_bytes,prompt)를 **한 번** 호출한다. wire5를 분리 저장한다. fence/JSON/producer·binding 보충이나 repair는 없다. wire 안의 stop/completed도 업무 완료를 뜻하지 않는다.
10. 모델 proposal의 execute/advance/stop을 runtime/harness로 돌려보내지 않는다. evaluate_sensor_run도 호출하지 않는다. 실제 모델 업무 평가·score는 not_executed/null이다. 다음 slot만 같은 batch 예산 안에서 새 trial/IDs로 진행한다.

소스 안에서 이미 삼켜진 내부 예외의 원 객체를 복원했다고 주장하지 않는다. 원 객체 전파는 host/capture latch/producer 경계에서 실제 관측한 KI/SE/GE/MemoryError에 적용한다. 부모 API가 fixed failure를 반환하면 그 공개 code/원 receipt를 보존한다.

## 3. 예산·큰 입력·취소

한 함수 invocation이 외부 model reservation cap8/monotonic wall60초를 소유한다. 타입/경로/고정 입력의 preflight 뒤, 새 증거 폴더 생성 전 시작한 하나의 clock을 모든 준비/slot/import/producer/retention/decode/finalize에 사용한다. 최대 계획4는 cap8을 늘리지 않는다. 첫 오류·취소·deadline 뒤 남은 slot은 not_executed이며 새 함수/Event/process로 자동 이어가지 않는다. 이후 명시 batch는 root가 이전 ledger를 검토해 따로 위임해야 한다. 이 함수는 root의 계정 전체 잔량·기존 실제 batch 권한을 인증하지 않는다.

예약은 감소·환급하지 않는다. reserved_slots와 producer 호출 횟수, producer가 보고한 version/model process 시도 수를 구별한다. receipt가 없어 실제 시도가 불명확하면 합계는 null이다. 원격 network/retry/과금·resolved identity는 계속 unknown/null이다.

produce 전에 remaining_wall>6초가 필요하다. timeout_seconds=min(60,remaining_wall-6)을 정식 producer에 준다. 그 producer의 terminate2+kill2+reader/close2초 여유를 남기는 계산이며 새 retry/fallback은0이다. host close join은 max(0,min(2,remaining_wall))초 안이며, 회수를 확인하지 못하면 cleanup flag=false/실패다. 이2초를 전체 clock 밖에 새로 붙이지 않는다. 준비·IO 자체가 clock을 넘으면 실패로 보존하고 성공을 반환하지 않는다. 유한 OS metadata/파일 IO의 hard realtime이나 원격 강제 취소 보장은 아니다.

cancel_event는 None 또는 native threading.Event다. caller는 batch 중 clear/reset하지 않는다. **stage 사이 협조 취소**만 지원한다. 정식 producer는 cancel 인수가 없으므로 in-flight Event는 producer가 반환/timeout한 뒤 관측한다. 이미 수신한 complete trace는 보존하되 decoder·다음 slot은0이다. 최초 관측 producer 오류가 있으면 후행 cancel이 primary를 바꾸지 않는다. active Python control은 정식 producer의 bounded cleanup 뒤 동일 객체로 전파한다. 신속한 programmatic in-flight stop이 필수라면 producer API 소유의 별도 공통 변경이 선행되어야 하며 이 new3에 숨겨 구현하지 않는다.

003의 fullbench prompt는 normal131305B/recovery131356B였다. 이는 측정한 bytes이며 token 수가 아니다. 새 IDs·source로 매번 다시 봉인한다. 131KB context의 토큰·서비스 지연·출력 한도는 미검증이다. 2노드 요약을 같은 context라고 부르지 않는다. 원 fixture의 전체 운전은 normal6/recovery10 decisions, 합16이었다. 회복10은 매판단 모델 호출 시 cap8을 넘으므로 이번 첫 판단 trace의 성공을 전체 복구 완료로 올리지 않는다. 모델 출력 token cap/가격을 caller가 임의 추정하거나 새 CLI flag로 넣지 않는다.

## 4. Receipt·파일의 닫힌 형상

성공은 detached native dict 하나이며 top exact12다: schema_version, kind, batch_id, status, failure, declaration, budget, slots, cancellation, cleanup, execution, verification. kind=codex_operator_first_decision_batch, batch_id=operator-first-batch:+uuid4 hex32, status=complete/failed다. 성공은 계획 slot 모두 complete이면서 wire 검증만 완료했다는 뜻이다. failure는 null 또는 exact3 code/stage/slot_index(null 또는1..4)다. source-map의 exact nested key가 규범이다.

- declaration exact5: producer_name/scenarios/requested_models/catalog_sha256/schema_sha256.
- budget exact8: limits/reserved_slots/producer_calls_started/version_process_attempts/model_process_attempts/elapsed_seconds/reset_used/application_retries. counts는 0..8 또는 관측 불가 null, reset_used=false/application_retries=0이다. limits exact4는 model_calls8/wall_seconds60.0/producer_cleanup_allowance_seconds6.0/harness_budgets exact5다.
- slots는 선언 순서 길이1..4. slot exact11: slot_index/scenario/requested_model/status/stage/binding/capture/transport/wire/failure/artifacts. status는 complete/failed/not_executed, untouched slot은 stage=not_started와 나머지 자료 null/absent다.
- binding은 null 또는 exact6 run_id/runtime_instance_id/decision_id/model_request_id/context_sha256/request_sha256이다. capture는 null 또는 exact8 tick/setup_revision/profile_count/device_count/context8_sha256/context7_sha256/legacy_ai_model_called/model_proposal_dispatches이며 마지막 두 값은 false/0이다.
- transport는 null 또는 exact3 exchange_ref/receipt/receipt_sha256이다. receipt는 원 producer dict18 또는 아직 없음 null, disk 저장·값 일치를 증명 못한 receipt_sha는 null이다. wire는 null 또는 원 decoder wire5다. slot.failure는 null 또는 exact2 code/stage다.
- cancellation exact4: requested/scope/observed_stage/remote_cancel_verified. scope=between_stages_only, remote_cancel_verified=false다.
- cleanup exact3: host_artifacts_closed/secondary_errors/remote_cancel_verified. close flag는 bool 또는 null, secondary는 artifact_close_failed/receipt_write_failed/secondary_overflow의 고유 관측 순 배열 최대8, remote flag=false다. producer cleanup/descendants는 원 receipt를 그대로 읽는다.
- execution exact4: mode=native_cli_first_decision/model_proposal_dispatches=0/task_assessment_status=not_executed/task_score=null이다. 실제 CLI 호출 여부는 별도 count로 판단하고 선언 mode만으로 원격 진위를 인증하지 않는다.
- verification exact5: wire_complete/source_inputs_unchanged/remote_identity_verified/semantic_quality_verified/hardware_verified. 처음 둘은 bool, 뒤3은 false다.

slot.artifacts exact7은 context8/context7/binding/prompt/capture_report/capture_events/wire다. descriptor exact7 path/present/bytes/sha256/complete/overflow/extent는 기존 prefix/absent/whole_file 의미를 따른다. 성공 complete에는 overflow=false가 필요하다. 각 path는 slot-0001 등 slot 디렉터리 기준의 고정 literal이다. context8.json/public-context7.json 각1MiB, binding.json64KiB, prompt.json256KiB, capture-report.json256KiB, capture-events.json2MiB, wire.json64KiB다. 반환 bytes 원본은 producer/final-text.bin에 있고 wire.json은 decoder의 별도 canonical dict다.

각 slot/producer/는 정식 producer의 artifact9/receipt.json/work 그대로다. binding.json은 binding/delegation/remaining_budget/catalog_sha256/schema_sha256 정확5키다. 공통 literal은 response-schema.json, private 절대 경로는 caller-request.json, 최종은 batch-receipt.json이다. caller-request.json은 schema_version=1/kind=codex_operator_first_decision_request/batch_id/execution/declaration/source_pins/limits 정확7키이며 execution은 catalog_path/executable 정확2다. 원 argv는 producer의 invocation.json 소유다. receipt 자기 hash는 없다. caller-request·host receipt≤256KiB·schema64KiB 및 host 작성 파일 각각 위 cap을 적용하고 producer 수집 cap은 바꾸지 않는다. native CLI의 순간 disk 사용량·알려지지 않은 work 파일을 hard quota로 제한했다고 주장하지 않는다. 원/실패/partial·unknown 파일을 지우거나 잘라 성공으로 바꾸지 않는다.

## 5. 첫 오류와 소유 공통 변경

CodexFirstDecisionError(RuntimeError)의 .code/str/args는 고정 code만, cause/context=None, .receipt는 증거 생성 전 null/이후 가능한 failed batch 사본이다. 새 prefix operator_first_decision_ 뒤 suffix는 invalid_input/unsupported_source/capture_failed/budget_exhausted/cancelled/retention_failed/timeout/cleanup_failed/internal_error다. 정식 producer의11개 code와 순수 boundary의8개 code는 **그 원 full code 그대로** 허용해 primary를 보존한다. 원 producer phase는 transport.receipt.failure에 보존하고 caller stage는 별도다.

첫 운영 code/stage를 latch한다. 후행 close·receipt 실패는 secondary이고 다음 slot/decoder/dispatch를 열지 않는다. 저장 실패 시 in-memory partial만 남을 수 있으며 기존 파일을 overwrite하지 않는다. MemoryError로 receipt조차 불가능하면 원 control을 전파한다. 계정·header·stderr·원 예외/절대 경로를 public 오류에 넣지 않는다.

선택 단위에 필요한 legacy 공통 source 변경은0이다. root 소유 공개 norm3(spec/plan/typed contract)와 구현 base pin만 선행한다. 이후 모델 주도 실행을 하려면 harness result와 journal의 false/provenance 정책을 어떻게 공존시킬지, 별도 actual trace/평가 귀속·취소 seam을 누가 소유할지 새 공통 단위로 닫는다. owner가 legacy false를 true로 바꾸거나 capture report/003 fixture PASS를 actual 모델 품질로 승격하지 않는다.
