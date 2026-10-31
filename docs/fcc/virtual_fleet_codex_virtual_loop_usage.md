# Codex의 동일 가상 runtime 판단 루프

2026-10-26 schema 호환/하향 한도: [현재·역사 프로필과 검증 범위](codex_operator_schema_compat_usage.md)를 따른다. 새 실행에는 current_response_schema_bytes()의 exact 3052B만 허용하며 역사 oneOf 프로필은 producer 전에 invalid_input으로 거절한다. 선택 keyword model_process_limit=8, wall_seconds_limit=180은 각각 native 정수1..8, 유한 native 숫자0<wall<=180의 더 작은 상한만 허용한다. 선언·하네스 decision/wall·remaining delegation·예약/admission·최종 elapsed 대조는 같은 값을 사용한다. 기존 기본 8/180, producer≤60/retry0과 원 소비 기록을 보존하며 권한을 발급하지 않는다.

## caller의 외부 증거 예약 — 2026-10-26

공개 run_codex_virtual_loop는 optional evidence_reservation=None을 지원한다. None은 원 경로/한도/DTO와 추가 keyword0을 유지한다. explicit native dict exact2 files/bytes의 strict native int를 각각0~192/0~33554432에서 검증하고 새 복사본의 immutable tuple로 분리한다. 유효성 검사는 파일/런타임/producer 이전이며 bool·subclass·추가/누락·음수/초과는 invalid_input이다. caller alias 변경으로 이미 고정한 예약을 줄일 수 없다.

loop known 안의 실제 파일과 known 밖의 caller 예약은 중복하지 않는다. 모든 write·producer 선예약·final=True receipt도 기존 space 한 곳에서 실제 known+이번 예약+caller 예약을 동일192파일/32MiB에 더해 거절한다. global _LIMITS·8decision/180초/producer60초/retry0·원 DTO의 closed shape는 바꾸지 않는다. 예산을 발급·초기화·환불하거나 권위를 부여하지 않는다. 기존 producer9 cap14159872B/decision 선예약16257024B·13파일/8회 독립합113278976B는 host 상계 증명으로 쓸 수 없어 원 근거와 한계를 보존한다.

journal은 직접 writer 경로도 같은 admission을 지킨다. 기존 Journal의 순수 _header/_record를 읽기 전용으로 재사용해 실제 인메모리 provenance·header·retained event마다 canonical envelope·hash64·개행을 포함한 완전한 line bytes를 계산해 합산하고, 생성 전에 space(total,1)을 통과시킨 뒤 원 Journal을 한 번 생성한다. 실제 chain의 이전 hash와0*64는 모두64 hex 문자라 직렬화 길이가 같다. 원 writer·행·hash·검증/원천 Journal 모듈은 바꾸지 않는다. 9MiB 후행 읽기 cap이나 사후 파일 크기는 선예약의 근거가 아니다.

독립 정적 원 No/C0I1M0의 journal header/framing closure 부재는 별도 보존했다. 새 동적 경계는 진짜 public Journal의 긴 provenance header+유효 termination1 참조 bytes를 기준으로 딱 맞는 잔여 bytes/파일1을 허용하고1byte 부족이면 생성 전에 차단한다. 실제 loop.run/producer는 실행하지 않는다. 새8논리 proper GREEN/0.140초와 별도 signature2/0.130초, API 미지원/별도 framing RED·첫 GREEN 준비 오류의 분모와 기록은 [adapter 문서](intake_plan_virtual_execution_usage.md)에 구별한다. 원wall257초>180 한계와 actual 모델/물리/완전 종단 미검증은 그대로이며 이 seam을 host 공동예산 수용으로 승격하지 않는다.

2026-10-25, Asia/Seoul. DEV2-CODEX-PERSISTENT-VIRTUAL-LOOP-001.

한 fresh SensorTrial을 만들고 관측→Codex 응답→strict wire→허용 가상 도구1회→같은 runtime의 다음 관측을 반복한다. 첫 지원 goal은 acquire_fresh_rf_sensor다. configure·RF 수치 판정·스마트폰 전체 FCC 업무·실물 운전의 완료를 뜻하지 않는다.

## 정식 entry와 위임

공개 export는 run_codex_virtual_loop와 CodexVirtualLoopError(RuntimeError) 정확2다.

```python
def run_codex_virtual_loop(
    *, catalog_path: Path, catalog_sha256: str, response_schema_bytes: bytes,
    executable: Path, requested_model: str, scenario: str,
    evidence_dir: Path, execution_origin: str, cancel_event=None,
    source_settings=None,
    plan_binding=None, quantity=None, evidence_reservation=None,
    model_process_limit=8, wall_seconds_limit=180,
) -> dict:
    ...
```

이 함수가 합성 가상 실행의 정식 entry다. 기존 사용자의 합성 가상 실행 위임 범위에서 직접 호출하며, noauth intake CLI·issuer·account·reservation을 만들어 사용하지 않는다. 실제 접수 issuer 연결은 OPEN이다. 이 함수는 새 승인 bool이나 원격 실행 권한을 발급하지 않는다. 실제 Codex 호출은 총괄의 독립 수용 뒤 기존 Codex 시험 위임 안에서 별도 수행하며 owner 검증은 mock subprocess만 사용한다.

2026-10-26 연결 확장: 선택 keyword source_settings=None 하나를 추가한다. None은 기존 factory 호출의 condition/scenario·seed0·power_dbm12.5와 원 파일 종류·DTO 형상을 유지한다. 제공값은 native dict exact6 frequency_hz/power_dbm/bandwidth_hz/duty_cycle/modulation/crest_factor_db다. bool·숫자 subclass·문자열 숫자·NaN/Inf·float 범위 밖 정수·누락/추가 키를 거절하고, 주파수/BW 양수·RF interval 유한/하한0·duty (0,1]·crest≥0·modulation의 native 1..200자 nonblank를 증거 생성·factory·producer 전에 검사한다. 값의 보충·변환·clamp는 없다.

제공 source는 한 번 분리 복사하고 prepare_sensor_trial에 power_dbm=그 원 power 및 source_settings=그 원 exact6으로 전달한다. trial/runtime/harness는 계속 run당1개다. 제공 시에만 caller-request.json의 execution.source_settings에 같은 선언을 보존한다. None에는 이 키를 추가하지 않는다. 원 source pin·run ID·시각처럼 실제 실행마다 달라지는 근거를 이전 파일 bytes로 위장하지 않는다. 실제 장치/profile의 후행 거절은 기존 factory 책임이며 전역 rollback이나 모든 부정 입력의 무부작용을 새로 보장하지 않는다.

첫 source6 확장과 별도로, 2026-10-26 DEV2-CONDUCTED-EXECUTION-PROVENANCE-001은 plan_binding/quantity 선택 경계를 추가한다. plan_binding=None·quantity=None에는 기존 factory keyword·파일·top14/step12·AI flag를 유지하며 setup/journal을 생성하지 않는다. bound mode는 원 D1 binding6이 명시될 때만 열고 source_settings exact6도 필수다. quantity만 있거나 source 없는 binding은 증거/factory/producer 전에 거절한다. binding은 native exact6 intake_id/revision/analysis_context_id/context_sha256/analysis_sha256/plan_sha256이며 positive native revision·ID·SHA를 검증한다. caller snapshot 결합일 뿐 실행권한이 아니다.

bound mode에서는 prepare 전에 fresh 빈 collector를 만들고 같은 SensorTrial factory에 setup_records로 한 번 전달한다. 반환된 trial의 setup_snapshot()을 첫 harness event 전에 한 번 읽어 실제 collector와 대조하고 원 exact8 record list를 setup-snapshot.json에 보존한다. factory 예외의 원 collector/null receipt·시점도 partial로 보존한다. None getter의 빈 목록은 미기록이며 setup 무실행이 아니다. 별도 trial을 만들거나 원 record에 run/runtime을 삽입하지 않는다.

원 events가 모인 뒤 genuine OperatorJournal로 operator-journal.jsonl을 구성한다. timing은 post_run_from_retained_events이며 live/durable 취득으로 표시하지 않는다. 원 report/events와 같은 run/runtime, 원 plan_binding6, 실제 setup canonical SHA·topology와 SHA, 실제 source pin manifest의 canonical SHA(engine_fingerprint_kind=sha256_canonical_host_source_pins_v1)를 provenance에 결합한다. quantity는 caller의 유계 native 제공값만 보존하고 None이면 key를 생략한다. on/sensor_input/false/+1이나 손실값에서 양·기준면·부호를 추정하지 않는다. genuine journal이 거절하는 제공 형상은 원 caller request와 실패로 보존하며 정규화해 통과시키지 않는다.

bound mode에만 artifacts.setup_snapshot/operator_journal 원 파일 metadata와 execution.host_evidence를 추가한다. host_evidence는 원 binding/setup/topology SHA·quantity·post-run timing·journal complete/원 file/head SHA를 담으며 partial/unknown은 null 또는 명시 상태다. journal의 native 형상·해시/완료는 public read_operator_journal로 재대조한다. legacy journal/report의 ai_model_called=false는 그대로이며 실제 producer lifecycle·origin_authenticated=false/ai_model_called=null을 대체하지 않는다. 원 256KiB 출력·192파일/32MiB 관측 evidence·8/180/60/retry0 한도를 올리지 않는다. 새 계산·결과 builder·measurement_ref 선택·Store·G4 권위는 추가하지 않는다.

execution_origin은 actual_cli 또는 mock_subprocess의 명시적인 **caller 출처 선언**이다. native producer receipt에는 실제/mock을 인증하는 필드가 없으므로 origin_authenticated=false, ai_model_called=null로 표시하고 그 선언을 인증·권한으로 사용하지 않는다. 테스트는 genuine producer의 subprocess만 알려진 Python test child로 치환하고 원 producer lifecycle·raw 파일·receipt를 검증한다. mock 선언 자체가 subprocess를 치환하거나 실제 실행을 차단하는 기능은 아니다. 실제 실행 권한은 이 값으로 획득되지 않는다.

## 연결과 한도

[공개 producer](../../labflow/codex_cli_response.py), [공개 prompt builder/strict decoder](../../labflow/virtual_fleet/model_operator_boundary.py), [genuine SensorTrial와 공개 evaluator](../../labflow/virtual_fleet/evaluation.py), [기존 FleetHarness](../../labflow/virtual_fleet/harness.py)를 사용한다. trial/runtime은 run당 정확1개다. 각 step에 새 decision/model request binding을 만들되 run/runtime ID는 유지한다. 다음 prompt의 관측과 last_receipt는 직전 도구의 실제 후행 관측·receipt다.

원 runtime의 execute/advance/observations 경계와 호환 하네스의 clock 관측에서 BaseException이 가려지기 전에 최초 오류·control을 보존한다. 세 runtime 경계는 종료·정리 오류에도 원형 복원하며 별도 runtime이나 일반 도구 framework를 만들지 않는다. 관측 오류·invalid 관측을 정상 budget 종료로 취급하지 않고 후행 관측이 없으면 after/effect를 보충하지 않는다.

모델 logical call≤8, 가상 도구 intent≤8, tick delta≤8, outer wall≤180초, producer timeout≤60초 및 남은 outer deadline, transport/application retry0다. 모델 진입 전 예약은 오류·취소에도 소비하며 refund/reset/new budget이 없다. 각 prompt에는 기존 전체 한도 내 남은 예산을 선언하고 매 턴 새8회를 할당하지 않는다. 비용·usage 미관측은 null이다. 원 producer의 per-call usage/cost를 보존하며 추정 합계를 만들지 않는다. 기존 Vertex ledger6/3072는 읽거나 초기화하지 않는다.

허용 도구는 wire의 DUT.start {}, sensor.acquire/read {}, advance1, bounded stop뿐이다. 일반 shell·임의 도구·실물 연결0이다. known invalid/disconnected/error receipt는 원 status와 diagnostic을 다음 관측에 보존한다. 모델이 같은 남은 예산으로 다음 허용 행동을 선택할 수 있지만 host가 명령을 자동 재전송하지 않는다. producer/decoder/저장/불명 실행의 fatal error에서는 종료하고 자동 재개하지 않는다.

evidence_dir는 caller가 명시한 새로운 absolute native 디렉터리다. 기존 폴더·링크/reparse·알 수 없는 모델/schema는 실행 전에 거절한다. 승인 response schema literal3052B를 그대로 보존하고 canonical로 재직렬화하지 않는다. call별 context8/context7/binding/prompt/before/after/wire/dispatch-receipt 및 원 producer artifact9/receipt18을 보존한다. raw 크기/hash·native 파일·producer original response/last-message 결합을 검사한 뒤에만 strict decoder와 도구를 연다. 실패·prefix 파일을 삭제하거나 고쳐 성공으로 만들지 않는다.

bounded 데이터 한도는 output256KiB, step≤8, event≤64/총8MiB, context/관측 각1MiB, prompt/원 receipt 각256KiB, response/wire/dispatch 각64KiB, 알려진 evidence≤192파일/관측32MiB다. 다음 producer의 최대 retained 크기와 host 정리 여유가 남을 때만 새 호출을 시작한다. CLI의 순간 disk quota나 blocking OS IO의 강제 realtime 중단은 제공하지 않는다. cap 초과 원본은 보존하고 추가 호출을 중단한다.

## 새 outer receipt

schema_version=1, kind=codex_virtual_loop_result. top exact14는 schema_version/kind/run_id/status/failure/declaration/budget/steps/termination/evidence_assessment/execution/cleanup/artifacts/verification이다.

- declaration: 원 catalog/schema hash, 요청 모델·scenario·중립 producer·가상 goal/scope와 출처 선언.
- budget: 고정 한도와 소비한 producer 예약/진입·관측 process attempts·elapsed·원 harness usage. 원 attempt를 모르면 null이다.
- steps: 최대8. index/binding/before/after/producer/wire/dispatch/stage/status/failure/artifacts/verification exact12다. before/after는 원 full64 파일 metadata, producer는 출처 선언·원 receipt18·raw hash를 보존한다. dispatch는 원 request ID·intent·receipt status·실행 불명/null·changed/unchanged/unknown을 구별한다.
- termination: 원 stop claim과 실제 종료 이유·unresolved request IDs. AI의 completed 발언을 측정 성공으로 치환하지 않는다.
- evidence_assessment: scope=acquire_fresh_rf_sensor_public_evidence, evaluator_called, genuine 공개 evaluator result 또는 null, goal_observed, score=null. pass인 bounded noncompletion과 observed_goal_satisfied를 구별한다.
- execution: 같은 runtime ID·synthetic mode·caller origin declaration·origin_authenticated=false·ai_model_called=null. cancellation은 scope=between_stages_only와 관측 requested를 담고 producer_inflight_cancelled/remote_hard_cancelled는 null이다. 실제/mock의 선언과 per-call 원 lifecycle을 실제 모델 진위 인증으로 올리지 않는다.
- cleanup: supervisor terminal 관측·host 파일 닫힘·runtime 참조 해제와 후행 정리 오류. virtual_outputs_disabled=null/remote_cancel_verified=false이며 물리 정리가 아니다.
- verification: 원 byte/binding·관측 연결 확인과 별도로 root 권위/remote identity/실제 wall 강제/모델 품질/하드웨어/물리 정리/전체 업무 검증은 false다.

FleetHarness의 원 report는 fixture/ai_model_called=false로 고정되어 있다. 원 report/events는 **legacy compatibility evidence only** 파일로만 보존하고 실제 AI 실행 record로 반환하지 않는다. 원 DTO를 수정하거나 실제 origin으로 변환하지 않는다. 공개 evaluate_sensor_run에는 같은 원 trial과 genuine legacy report/events를 원형 전달해 합성 sensor evidence만 평가한다. 실제 모델 호출·출처는 새 outer receipt의 producer lifecycle에만 연결하며 legacy false flag를 그 의미로 재사용하지 않는다.

## 실패·취소·검증

CodexVirtualLoopError는 고정 code/str/args, cause/context=None와 가능한 detached .receipt를 가진다. 원 Codex producer11·boundary8 full error code를 보존하며 후행 close/finalize가 최초 code/stage를 덮지 않는다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 유계 best-effort 정리 뒤 동일 객체로 전파한다. cancel_event는 native threading.Event이며 stage 사이 협조 취소다. 원 producer에는 cancel_event 인수가 없어 실행중 producer의 즉시 중단이나 remote hard-cancel은 unknown이다. 엄격한 producer timeout과 남은 deadline으로 제한하고 이미 시작한 시도를 취소·오류 때문에 환불하지 않는다. 마지막 gate 이후 이미 가상 도구가 호출됐을 수 있으므로 intent/receipt/관측을 보존하고 rollback·재실행하지 않는다.

owner 단계는 실제 Codex·원격 모델·auth/ADC·운영 DB/Store·고객 원본·실장비0이다. 정상 fresh 관측 루프, 부족한 관측·known 거절/단선·복구 미완료, malformed binding·producer/auth 모의 실패, deadline/cancel/cap/cleanup을 genuine core와 mock subprocess로 검증한다. 공개 evidence evaluator의 합성 판정과 실제 RF 수치·모델 업무 품질·전체 시험소 완료는 별도다.

새 루프의 owner 회귀는 저장소 루트에서 `python -m unittest discover -s tests -p test_virtual_fleet_codex_virtual_loop.py -v`로 실행한다. 이 검사는 알려진 Python child와 합성 runtime을 사용하며 실제 Codex 호출을 실행하지 않는다.

## 2026-10-31 bounded observed recovery 선택 인자

마지막 keyword-only 인자 `recovery_policy=None`을 추가했다. 생략/None은 기존 scope/SYSTEM/DTO와 하위 호출 형태를 유지한다. 선택값은 다음 native dict이며 추가 키·bool 정수·다른 kind/version·한도 밖 값은 파일/runtime/producer 입장 전에 거절한다. `max_wait_advances`는1..2만 허용한다.

```python
recovery_policy={"schema_version": 1, "kind": "bounded_observed_wait", "max_wait_advances": 2}
```

상한2의 근거는 기존8 결정에서 정상 scripted 흐름5와 종료 결정1을 뺀 값이다. 숨은 복구 일정에 맞춘 값이 아니다. [별도 scope 계약](virtual_fleet_model_operator_boundary_usage.md)의 닫힌 현재 공개 관측 쌍에서만 nonpending advance1을 추가 허용한다. 알려진 정상 pending advance는 추가 대기 한도에 넣지 않지만 기존 결정·logical request·tick·시간 예산을 계속 사용한다. 추가 대기도 같은 기존 예산을 사용하고 다음 종료용 결정/model call이 남아야 한다. 세 번째 추가 대기는 기존 `operator_virtual_loop_budget_exhausted`로 proposal 반환 전에 막아 intent/dispatch를 만들지 않는다. 연결 끊긴 DUT.start를 reconnect로 대신하지 않는다.

선택 모드의 `execution.recovery`에는 원 policy, `wait_advances_used`, `reobservations_confirmed`, `outcome`을 보존한다. 사용량은 host gate 통과 시 예약하며 상태 변화·취소·예산 오류로 초기화하거나 환급하지 않는다. 확인 재관측은 같은 runtime의 실제 advance receipt와 원인 연결된 after observation이 확인된 경우만 센다. 기존 무결성 확인용 read와 구별한다. 공개 delegation에는 한도·사용·잔여·확인 수를 hash에 결속해 전달한다. source/관측 오류와 취소의 첫 오류는 기존 경로로 보존한다.

선택 모드 normal은5 결정/추가 대기0으로 fresh 측정과 DRAFT 저장을 확인했다. persistent_disconnect와 restored_disconnect는 같은 공개 정책으로 각각 대기2+blocked 종료1 후 selector가 held로 유지했다. 기대 일치3/3과 업무 목표 충족1/3을 구별하며 두 장애의 실제 복구 성공은 관측하지 못했다. 별도 typed public transition 검사는 상태 변화만으로 완료할 수 없음을 검증한다. 실제 AI/실장비 검증과 합산하지 않는다.
