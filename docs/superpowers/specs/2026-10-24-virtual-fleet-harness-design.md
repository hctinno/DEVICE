# 전체 장비 관측 기반 하네스 — 첫 구현 계약

2026-10-24, Asia/Seoul. 사용자 위임에 따라 전체 가상환경 다음 단위를 진행한다. 기준은 `890ae269e10a108e93d8e09daa8f209a270c7bc6`의 [전체 장비 가상환경](../../fcc/virtual_fleet_usage.md)이며 개발1~4의 읽기 전용 계약 검토를 반영했다. 이 문서는 총괄이 고정한 **첫 구현 범위**다. 실제 모델 공급자, 원시데이터, 실장비를 선행조건으로 추가하지 않는다.

## 선택과 경계

기존 VirtualSession에 다른 backend를 억지로 넣는 안, 별도 관측 기반 실행기를 먼저 만드는 안, 영속 재생·상시 실행·실시간 화면 제어까지 한 번에 만드는 안을 비교했다. 별도 실행기를 선택한다. 새 Fleet의 초기화·요청 캐시·전역 revision을 기존 세션이 이미 저장한다고 가정하지 않으며, 실행과 증거 보존을 먼저 검증한다.

이 단위는 신뢰한 Python fixture policy를 제한된 JSON 문맥으로 호출한다. 실제 LLM/AI 학습·모델 평가를 실행했다고 표시하지 않는다. 첫 UI는 **완료된 실행 기록 조회**다. 실행 중 start/stop/resume HTTP 제어, 자동 재시작/재개, 전체 초기화부터의 결정적 replay, hard timeout/강제 취소는 후속 단위다. CLI를 재실행해 새 시험을 만드는 것과 중단된 시험 재개를 구별한다.

모든 출력은 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`를 유지한다. 현재 catalog는 Un-licensed 64프로필/24역할이며 제조사 전체 기능이나 64실물 자산을 뜻하지 않는다. 기존 접수·가상 세션·기존 장비 역할과 core의 계약은 변경하지 않는다.

## 실행기 — 개발2 소유

새 모듈 `labflow/virtual_fleet/harness.py`의 고정 진입점:

```python
FleetHarness(runtime, policy, *, goal, catalog, topology, role_actions,
             budgets=None, event_sink=None, run_id=None,
             runtime_instance_id=None, clock=None)
```

- runtime에는 기존 `execute(request_id, device_id, action, parameters)`, `advance(request_id, ticks)`, `observations()`만 사용한다. 신뢰한 작성자 wrapper를 주입할 수 있지만 policy에 객체를 전달하지 않는다.
- `policy(context) -> proposal`은 호출마다 분리된 JSON 사본을 받는다. context의 키는 `schema_version`, `goal`, `catalog`, `topology`, `role_actions`, `observations`, `last_receipt`, `remaining_budget`다. 공개 catalog는 기존 HTTP와 같은 필드 투영을 사용하며 `simulation_parameters`를 포함하지 않는다.
- goal은 공개 시험 목표다. 사용자에게서 받은 공개 한계/기준은 허용하지만 숨은 fault/정답/평가 허용차/시나리오 라벨·일정/seed/경로/평가 결과는 policy 문맥에 넣지 않는다. callable Python의 보안 sandbox를 제공한다는 주장은 하지 않는다.
- proposal은 정확히 `{"kind":"execute","device_id":str,"action":str,"parameters":dict}`, `{"kind":"advance","ticks":1}`, 또는 `{"kind":"stop","claim":"completed|blocked|unsupported|failed","reason":str}` 중 하나다. 인수·장비·동작을 현재 선언과 대조하며 알 수 없는 키/비유한 수/과도한 JSON은 거절한다. policy가 request ID를 지정할 수 없다.
- `run()`은 종료까지 반복해 공개 result를 반환한다. `step()`은 최대 한 번의 policy 판단을 진행하고 분리된 상태 dict를 반환한다. `stop()`은 판단 경계에서 감독 중단을 요청한다. 실행 중 함수를 강제 중단한다고 표시하지 않는다. `events()`는 분리된 운영 이벤트 목록, `result()`는 종료된 공개 result를 반환한다.

기본 예산은 `decisions=64`, `logical_requests=64`, `ticks=32`, `wall_seconds=30`, `transport_retries=2`다. transport retry는 요청별이 아닌 run 전체 누계 예산이다. 모두 유한한 양수이며 transport retries는 0을 허용한다. wall clock은 monotonic 주입 가능 함수이며 호출 전/후를 확인하는 협력식 deadline이다. 잘못된 proposal도 decision 1회를 차감한다. 이 첫 단위는 자동 cleanup을 수행하지 않으며 result의 cleanup은 `not_assessed`다. 종료를 RF/이동/전원 정지 완료로 해석하지 않는다.

실행 의도와 예산을 먼저 예약·기록하고 dispatch한다. 새 acquire는 새 논리 요청 ID를 사용한다. `RetryableTransportError`만 **같은 살아있는 runtime instance·같은 ID·같은 body**로 최대 2회 재전송한다. advance는 1 tick만 허용하고 재전송 때 예산/tick을 다시 예약하지 않는다. 알려진 invalid/unsupported/error는 transport 재시도가 아니다. 다른 호출 예외, dispatch 이후 증거 저장 실패, 원 instance 소실은 불확실 종료하며 다른 instance/새 ID에 재실행하지 않는다.

`termination.reason`은 `policy_stop`, `supervisor_stop`, `decision_budget`, `request_budget`, `tick_budget`, `wall_deadline`, `policy_error`, `invalid_proposal`, `runtime_error`, `runtime_mutation_uncertain`, `evidence_error` 중 하나다. policy의 완료 주장은 독립 평가와 구별한다. 원시 예외 문자열·traceback을 공개 context/결과/로그에 넣지 않는다. 미결 요청 ID를 보존한다.

## 운영 이벤트와 저장 — 개발3 소유

실행기는 각 이벤트에 다음 고정 외피를 사용한다:

```json
{"schema_version":1,"kind":"operator_event","event_id":"event:1","run_id":"opaque","runtime_instance_id":"opaque","sequence":1,"type":"observation","payload":{"observation":{}}}
```

sequence는 1부터 연속이며 작성자 이벤트 순번과 무관하다. type은 `policy_decision`, `intent`, `receipt`, `observation`, `transport_retry`, `error`, `termination`이다. intent payload는 `request_id`, `operation`(`execute|advance`), `body`, `logical_request`를 가진다. execute body는 `device_id/action/parameters`, advance body는 `ticks`다. receipt payload는 `request_id/result`, observation payload는 `observation`과 선택적 `cause_request_id`, retry payload는 `request_id/retry`다. 나머지는 최소한의 proposal 또는 공개 코드만 담는다.

`event_sink(event: dict) -> None`은 실행기가 dispatch 전에 호출하며, 실패하면 진행하지 않는다. event 사본을 전달하고 성공한 이벤트는 실행기 메모리에도 보존한다. sink 없이도 메모리 증거로 단위 검사할 수 있다.

종료 이벤트 payload는 `{"code":"run_terminated","unresolved_request_ids":[]}` marker다. sink와 협력식 deadline을 확인한 뒤 공개 result의 최종 종료 사유와 policy claim을 확정한다. 이미 저장된 종료 이벤트를 나중 사유로 고쳐 쓰지 않는다. dispatch 후 receipt의 대상·profile·role·tick과 새 관측의 구조·예상 tick을 모두 검증한 뒤 receipt/observation을 확정한다. 검증 실패는 해당 미결 intent를 유지하고 불확실 종료한다.

새 모듈 `labflow/virtual_fleet/journal.py`:

```python
OperatorJournal(path, *, run_id, runtime_instance_id, provenance)
journal(event)  # event_sink callback
journal.close()
read_operator_journal(path) -> dict
```

새 파일만 생성하고 기존 파일을 덮거나 이어 쓰지 않는다. header에 schema/run/instance/provenance와 합성 표시를 고정하고 UTF-8/LF canonical JSONL로 append·flush·fsync한다. 운영 이벤트의 연속 sequence/외피/JSON 유효성·중복키·크기를 검증하고 hash chain을 유지한다. 기본 한도는 한 줄 512 KiB, 파일 32 MiB, 이벤트 4096개다. private author/fault/seed/truth/expected/password/경로 필드를 중첩해 넣으면 거절한다. 공개 `source_id`와 관측 증상 reason은 보존한다.

provenance의 필수 키는 `runtime_origin="preinitialized"`, `catalog_sha256`, `topology_sha256`, `engine_sha256`다. SHA는 64자리 소문자 hex다. 추가 공개 JSON은 허용하며 reader가 자동 실행/복구하거나 현재 engine과 비교해 재개를 시도하지 않는다. header/events·무결성·complete 여부·미결 intent ID를 반환하고 `resumable=false`를 명시한다. 저장만으로 runtime 복구를 지원한다고 표시하지 않는다. 부분 마지막 줄·불일치 hash·sequence/ID/instance 오류는 원본을 보존해 거절한다. hash chain은 서명/접근 통제의 대체물이 아니다.

현재 초기화 23요청 이전부터 기록하는 재생 wrapper는 아직 없다. 이 단위의 provenance는 `runtime_origin=preinitialized`, catalog/topology/code fingerprint를 명시한다. 작성자 seed/고장/정답/일정은 총괄이 별도 private artifact로 저장하고 운영 journal header·순번·context와 섞지 않는다.

## 첫 policy — 개발1 소유

새 모듈 `labflow/virtual_fleet/policies.py`의 `RFSensorFixturePolicy`는 `policy(context)` callable이며 `policy_id="rf_sensor_v1"`을 선언한다. 시나리오 이름이나 정답을 생성자 인수로 받지 않는다. 공개 goal은 다음과 같다:

```json
{"kind":"acquire_fresh_rf_sensor","dut_id":"dut","sensor_id":"sensor","minimum_acquisition_tick":15}
```

minimum tick은 시험 시작 관측 tick 다음 값이며 정답 수치가 아니다. policy는 실제 observation에서 disconnected/invalid/pending/idle·RF 상태를 읽어 DUT start, sensor acquire/read, 1 tick advance 또는 stop을 선택한다. 실제 fault 해제/재배선/reset으로 숨은 원인을 제거하지 않는다. 지속 장애는 유한 예산으로 종료한다.

측정 완료 주장은 sensor의 valid measurement, source_id=sensor 노드, unit=dBm, finite value, 새 acquisition tick, 같은 관측 snapshot의 현재 setup revision을 모두 확인한다. profile_id는 envelope로 별도 대조한다. ON평균에 duty/crest 보정을 중복 적용하지 않는다. 과거 acquire receipt를 새 취득으로 사용하지 않는다.

## 독립 평가와 통합 — 총괄 소유

`evaluation.py`와 `harness_check.py`가 기존 전도 예제를 초기화하고 sensor를 triggered·명시적 합성 calibration valid로 바꾼 뒤 DUT stop 상태에서 trial을 시작한다. 모든 trial의 공개 goal/정책은 같다. 작성자만 아는 세 경우는 정상, 지속 DUT 통신 단절, 시작 후 상대 tick 4에 원인 해제다. 작성자 wrapper는 advance 후 별도 author namespace로 원인을 해제하며 policy에 일정/분류/seed/객체를 제공하지 않는다.

평가자는 운영 observation 이벤트를 읽고 정상 산술·단위/출처·새 취득/revision, 실패 시 허위 완료 금지, 복구 후 새 취득을 확인한다. 특정 action 순서만을 정답으로 강제하지 않는다. 정상의 수치를 바꾼 별도 합성 조건에서도 계산을 확인한다. 취득 이후 정리/설정 변경이 있더라도 취득 당시 snapshot에 맞는 역사적 측정은 보존한다.

공개 result의 schema는 다음과 같다. result에 작성자 정답 수치/허용차/시나리오 라벨/seed/경로를 추가하지 않는다.

```json
{"schema_version":1,"kind":"virtual_fleet_harness_result","run_id":"opaque","runtime_instance_id":"opaque","synthetic":true,"hardware_verified":false,"ai_model_called":false,"policy":{"kind":"fixture","id":"rf_sensor_v1"},"termination":{"reason":"policy_stop","policy_claim":"completed"},"task_outcome":"not_assessed","cleanup":{"status":"not_assessed","evidence_refs":[]},"usage":{"decisions":1,"logical_requests":0,"transport_retries":0,"tick_delta":0,"reserved_ticks":0,"elapsed_ms":0},"evidence":{"measurement_refs":[],"operator_transcript_ref":"artifact:operator_events"},"unresolved_request_ids":[],"assessment":{"status":"not_assessed","verdict":null,"evaluator_id":null,"evidence_refs":[],"summary_code":null}}
```

assessment.status는 `not_assessed|completed|failed`다. not_assessed/failed의 verdict는 null, completed는 pass/fail/inconclusive다. policy가 stop하지 않은 종료의 policy_claim은 null이다. v1 task_outcome/cleanup.status는 not_assessed로 고정한다. 모든 evidence ref 배열의 원소는 opaque 문자열이며 object를 넣지 않는다. elapsed_ms는 유한한 비음수 number, 나머지 usage counter는 비음수 정수다. 평가기 오류 failed, 평가 완료 fail, 미평가를 분리한다. 평가 결과는 policy로 피드백하지 않는다. runtime coverage의 `scenario_validation=not_assessed`는 바꾸지 않는다.

CLI는 새 출력 폴더에 opaque run별 공개 result·operator JSONL·별도 private author 파일·hash manifest를 남긴다. 기존 출력은 덮지 않는다. 실제 모델 호출·학습·현장 정확도·완전한 디지털 트윈 완료로 표현하지 않는다.

## 완료 기록 화면 — 개발4 소유

기존 `create_server(..., harness_report=None)`에 선택적 공개 완료 result를 주입한다. report는 런타임을 실행하지 않는 읽기 전용 자료다. `GET /api/harness-result`는 `{"schema_version":1,"report":null|result}`를 반환한다. existing `/api/state`, action/advance와 보안/CSRF/멱등성은 유지한다. 파일 경로·seed·fault·작성자 artifact 입력은 받지 않는다.

기존 화면에 완료 기록 패널을 추가해 로딩/조회 오류/실행 없음·fixture 표시·termination/policy claim·별도 평가·예산 사용·관측 참조를 보여준다. result의 미평가를 PASS로 바꾸지 않는다. 현재 장비 관측이 바뀌어도 결과는 과거 실행 기록으로 표시한다. 활성 실행/재개/중단 버튼은 이 단위에 만들지 않는다. 다른 run/instance의 응답이나 유효하지 않은 스키마/렌더 오류가 마지막 성공 기록을 덮지 않게 한다.

서버 주입 report는 엄격한 공개 필드/JSON/256 KiB UTF-8 크기 검증과 분리된 사본을 사용한다. `harness_model.mjs`에 검증/표시 계약을 분리하고 Node·HTTP·브라우저에서 정상/미평가/평가실패/전송 실패/악성 문자열/모바일을 확인한다. 기존 64프로필 실제 브라우저 수용은 유지한다.
