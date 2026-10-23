# 관측 기반 fixture 하네스

2026-10-24, Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-harness-design.md), [구현 계획](../superpowers/plans/2026-10-24-virtual-fleet-harness.md), [배정](../../handoff/development/VLAB-HARNESS-002.md)에 따른 개발2의 [실행기](../../labflow/virtual_fleet/harness.py)와 [검사](../../tests/test_virtual_fleet_harness.py)다. 기준 commit은 `45fafe20033da2a78752dec99a07673870fef36c`다.

신뢰한 Python fixture의 JSON 판단을 기존 가상 runtime에 연결한다. 실제 모델·장비·현장망·SDK/API·사용자 raw·매크로를 호출하지 않는다. 모든 결과에 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`를 고정한다. fixture 실행을 실제 AI 운전·학습·모델 성능 평가로 표시하지 않는다.

## API

```python
FleetHarness(runtime, policy, *, goal, catalog, topology, role_actions,
             budgets=None, event_sink=None, run_id=None,
             runtime_instance_id=None, clock=None)
```

runtime에는 execute(request_id, device_id, action, parameters), advance(request_id, ticks), observations()만 호출한다. catalog/topology/role_actions는 호출자가 제공하며 분리된 사본으로 보존한다. policy에는 runtime 객체·작성자 API·내부 상태를 전달하지 않는다. 선택적 policy.policy_id가 유효한 ASCII 식별자이면 결과에 사용하고 그 밖에는 fixture로 표시한다.

| 메서드 | 의미 |
|---|---|
| run() | 종료까지 반복하고 분리된 공개 result 반환 |
| step() | 최대 한 번 판단. state/run_id/runtime_instance_id/usage/termination/result의 분리된 dict 반환 |
| stop() | 다음 호출·판단 경계의 감독 중단 요청. 반환 None. 장비 정지는 실행하지 않음 |
| events() | 성공한 운영 이벤트들의 분리된 사본 |
| result() | 종료 전 None, 종료 뒤 분리된 공개 result |

step의 state는 running/terminated다. 종료된 객체를 다시 run/step해도 runtime에 재파견하지 않는다. 한 객체의 동시 step/run은 지원하지 않는다. stop은 실행 중 함수를 강제 취소하지 않는다. 자동 cleanup·새 runtime으로 재시작·세션 재생은 제공하지 않는다.

## 문맥과 proposal

문맥 키는 정확히 schema_version, goal, catalog, topology, role_actions, observations, last_receipt, remaining_budget이다. 매 호출에 분리된 JSON 사본을 준다. catalog는 기존 가상 HTTP의 공개 profile 필드 목록을 사용하며 simulation_parameters와 예약 private 필드를 제거한다. seed·author/fault/truth·숨은 시나리오/일정·비공개 경로·암호 등을 문맥/이벤트에 복사하지 않는다. 공개 목표와 문자열의 적절성은 신뢰한 호출자도 책임진다. 이는 임의 Python을 격리하는 보안 sandbox가 아니다.

proposal은 아래 세 형태 중 하나이며 키를 추가할 수 없다.

```json
{"kind":"execute","device_id":"sensor","action":"acquire","parameters":{}}
```

```json
{"kind":"advance","ticks":1}
```

```json
{"kind":"stop","claim":"completed","reason":"observed_evidence"}
```

stop claim은 completed/blocked/unsupported/failed다. 요청 ID는 하네스가 생성한다. 장비·action·필수 인수·타입·선언된 enum/최소·최대 범위를 파견 전에 확인한다. boolean을 수치로 받지 않는다. 비유한 수·비 JSON 객체·잘못된 Unicode·추가 키·미지원 동작·과도한 입력은 invalid_proposal로 종료하며 decision 한 번을 차감한다. 미지원 raw SCPI나 외부 명령으로 fallback하지 않는다.

초기 관측과 파견 뒤 최신 관측을 기록한다. last_receipt는 최초 확정 응답이며 재전송 응답의 tick/revision은 과거일 수 있다. 최신 상태는 observations를 사용한다. coverage는 호출하지 않고 주입된 role_actions를 사용하며 available/counter를 시나리오 성공으로 해석하지 않는다.

## 예산과 시간

| budgets 키 | 기본값 | 범위와 차감 |
|---|---|---|
| decisions | 64 | 양의 정수. 잘못된 판단과 stop도 1회 |
| logical_requests | 64 | 양의 정수. 성공적으로 기록한 intent마다 1회 |
| ticks | 32 | 양의 정수. advance 1 tick을 intent 후 예약하고 확정 시 실제 tick delta로 전환 |
| wall_seconds | 30 | 유한한 양수. 첫 step/run 경계부터 monotonic 시간 |
| transport_retries | 2 | 0 이상 정수. **실행 전체 누계** 재전송 예산 |

위 키의 일부만 지정할 수 있다. 알 수 없는 키·잘못된 타입/범위는 생성 시 거절한다. remaining_budget은 현재 decision을 예약한 뒤의 잔량이다. request/tick 잔량이 0이어도 decision 예산 안에서 stop을 판단할 수 있다. 새로운 변경 요청만 request/tick 한도를 검사한다.

clock에는 monotonic 초를 반환하는 함수를 주입할 수 있다. 호출 전/후·증거 저장 경계에서 확인하는 협력식 deadline이다. 가상 tick을 초로 환산하지 않으며 hard cancellation을 보장하지 않는다. 늦은 policy/관측 반환은 wall_deadline, 확정하지 못한 변경 호출의 늦은 반환은 runtime_mutation_uncertain이다. 파견 중 감독 중단도 응답 미확정이면 uncertain으로 남긴다. 원시 예외 문자열과 traceback은 공개 결과에 넣지 않는다.

JSON 복사는 1 MiB, proposal은 64 KiB, 중첩은 32단계로 제한한다. 운영 이벤트는 512 KiB/개, 4,096개/32 MiB의 메모리 한도를 가진다. 공개 result는 256 KiB 이하다. journal의 hash/header/줄바꿈 오버헤드 한도는 주입된 sink가 추가 검사한다. 저장 거절을 성공으로 숨기지 않는다.

## intent·재전송·미결 요청

event_sink는 callable(event)→None이다. event 사본을 전달하고 callback이 성공한 이벤트만 메모리에 추가한다. intent가 성공하기 전에 execute/advance를 호출하지 않는다. 실패한 이벤트를 callback에 반복 기록하거나 실패한 journal에 자동으로 이어 쓰지 않는다.

intent는 request_id/operation/body/logical_request를 담는다. 요청 ID는 run/instance에서 유도한 opaque ASCII 접두사와 증가 번호이며 128자 이하다. retry마다 같은 body의 새 사본을 전달하므로 runtime이나 sink의 사본 변조가 다음 재전송에 영향을 주지 않는다. runtime은 단일 소유자가 사용하며 run_id/runtime_instance_id 쌍을 다른 실행에 재사용하지 않는다.

RetryableTransportError만 제한 재전송한다. 이 예외를 올리는 wrapper는 **같은 살아있는 runtime과 같은 요청 ledger에 다시 도달함을 보장해야 한다.** 하네스는 새 instance나 다른 ID로 복구하지 않는다. run-wide retry 예산을 차감하며 논리 요청/tick은 다시 예약하지 않는다. 알려진 invalid/unsupported/error/disconnected 응답은 재전송 사유가 아니며 다음 판단에 전달한다. 수정 뒤 새 acquire는 새 논리 ID다.

일반 파견 예외·잘못된 응답·재전송 소진·파견 후 증거 실패는 runtime_mutation_uncertain이다. receipt를 성공적으로 기록하지 못한 intent의 ID와 advance 예약은 보존한다. intent 기록 뒤 파견 직전 deadline/중단을 만난 요청도 receipt가 없는 미결 ID로 남긴다. runtime을 복원했다고 표시하지 않는다.

receipt와 최신 observation을 둘 다 검증한 뒤 receipt→observation 순서로 기록한다. execute receipt의 device_id/profile_id/role은 요청 대상과 일치해야 하며, execute는 tick을 바꾸지 않고 advance는 정확히 1 tick만 진행해야 한다. receipt와 최신 관측의 tick·전체 tick 예산을 함께 검사한다. 관측 outputs는 port별 객체의 dict여야 한다. 형식·대상·tick 위반이면 해당 ID/예약을 미결로 보존하고 추가 파견을 막는다. receipt 확정 전 관측 읽기/검증 실패도 같은 처리다. 유효한 receipt를 저장한 뒤 observation 이벤트 저장만 실패하면 receipt를 보존하고 불확실 종료하며 그 요청 ID를 미결로 다시 만들지 않는다. 작성자 제어로 최신 revision이 증가하는 것은 허용하지만 역행은 거절한다.

## 이벤트와 결과

각 이벤트는 schema_version=1, kind=operator_event, event_id=event:N, run_id, runtime_instance_id, sequence=N, type, payload를 갖는다. N은 작성자 이벤트와 무관하게 1부터 연속이다. type은 policy_decision/intent/receipt/observation/transport_retry/error/termination이다. retry 순번은 해당 request에서 1부터 시작하며 usage의 재전송은 실행 전체 누계다.

observation payload는 observation과 선택 cause_request_id, receipt는 request_id/result, retry는 request_id/retry다. 오류에는 공개 code만 쓴다. termination payload는 code=run_terminated와 unresolved_request_ids의 종료 마커다. 마커 저장 뒤에도 deadline을 확인하므로 **최종 reason/claim은 공개 result.termination을 따른다.** 이미 저장한 이벤트를 사후 수정하지 않는다. sink 실패 시 남은 이벤트가 journal에 기록됐다고 가정하지 않는다.

종료 reason은 policy_stop, supervisor_stop, decision_budget, request_budget, tick_budget, wall_deadline, policy_error, invalid_proposal, runtime_error, runtime_mutation_uncertain, evidence_error다. policy 호출 실패와 잘못된 제안, 초기 runtime 계약 오류와 파견 결과 불확실성, 미파견 증거 실패를 구분한다.

result 필드는 고정 설계를 따른다. task_outcome과 cleanup.status는 not_assessed다. assessment는 status=not_assessed, verdict/evaluator_id/summary_code=null, evidence_refs=[]로 시작하며 총괄 평가기가 별도로 붙인다. completed 주장을 PASS로 바꾸지 않는다.

measurement_refs는 source ID·유한 scalar value·비어 있지 않은 unit·valid/status·획득 tick·해당 snapshot의 setup revision이 맞는 measurement 출력을 가진 observation 이벤트 ID다. 목표 장비·dBm·새 취득 최소 tick·독립 산술·허용차는 policy/평가기의 추가 검증 대상이다. 일반 증거 참조만으로 목표 달성이나 계측 적합성을 인정하지 않는다. 나중에 setup revision이 바뀌어도 취득 당시 snapshot의 역사적 증거를 보존한다.

## 메모리 증거 실행 예

기존 전도 예제를 초기화한 뒤 blocked로 종료하는 API 예다. 실제 목표를 수행하는 fixture와 독립 평가는 총괄이 연결한다.

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example
from labflow.virtual_fleet.harness import FleetHarness

catalog = load_catalog('virtual_profiles/sm_a176u_unlicensed.json')
fleet, topology, receipts = create_conducted_example(catalog, seed=7)

def fixture(context):
    return {'kind': 'stop', 'claim': 'blocked', 'reason': 'example_requires_task_policy'}

fixture.policy_id = 'example_stop'
harness = FleetHarness(fleet, fixture, goal={'kind': 'inspect_preinitialized_bench'},
                       catalog=catalog, topology=topology, role_actions=fleet.role_actions)
assert harness.result() is None
report = harness.run()
assert report['termination']['policy_claim'] == 'blocked'
assert report['task_outcome'] == 'not_assessed'
assert report['cleanup']['status'] == 'not_assessed'
assert harness.events()[-1]['type'] == 'termination'
```

sink가 없으면 메모리 증거만 유지한다. OperatorJournal을 쓰면 총괄이 callback과 runtime_origin=preinitialized 등의 header provenance를 제공한다. 하네스는 header를 쓰지 않고 초기화23요청 이전부터의 결정적 재생도 제공하지 않는다. 기존 VirtualSession/core/접수/장비 역할은 변경하지 않았다.

## 검증과 인수

전용 검사는 `python -m unittest discover -s tests -p test_virtual_fleet_harness.py -v`다. 39개 검사가 문맥/증거/응답 격리, 예산/늦은 응답, 전송 유실과 run-wide retry, 저장 실패/미결 intent, 정지와 불확실, 공개 코드/JSON/Unicode, 출처/revision·저장한 이벤트의 깊이 경계 조회를 확인한다. 최초 모듈 부재 RED 뒤 경계 회귀의 실패를 확인하고 구현했다. 독립 리뷰의 outputs 형식 3종, receipt 식별자 누락/불일치 6종, 예상 tick/전체 tick 예산 6종도 RED→GREEN으로 검증했다. 공통 VirtualFleet와 합성 발생기→센서, 장비 계약 오류 격리도 순수 Python 가상 모델로 실행했다.

이 개발 복제본의 최종 전체 unittest는 454개/52.453초 통과했다. 루트 문서 8개/로컬 링크155개, 소유 텍스트3개 UTF-8/Python AST2개/사용법 링크5개/완전한 실행 예1개와 의존성 검사를 통과했다. 처음에는 기존 PDF 검사 의존성이 없어 저장소의 requirements-extract.txt에 고정된 pypdf를 현재 가상환경에 설치했다. 회귀 중 기존 HTTP 검사의 Windows10053 연결 중단 1회는 단독 재검사와 최종 전체 재검사에서 통과했으며 실패 이력은 비공개로 보존한다. 서버 담당의 별도 보강과 통합 최종 검증은 총괄이 수행한다.

전용 브랜치의 최종 SHA는 총괄 인수 보고에 남긴다. 개발1 policy·개발3 journal·총괄 평가/CLI·개발4 완료 조회는 총괄이 결합한다. 실장비/현장 정확도·실제 모델/자율 운전·자동 cleanup·hard cancellation·durable resume/replay 검증은 미실행이다.
