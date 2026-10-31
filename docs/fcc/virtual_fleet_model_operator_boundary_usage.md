# 순수 가상 운전자 모델 경계

2026-10-25, Asia/Seoul. [공개 설계](../superpowers/specs/2026-10-25-virtual-fleet-model-operator-boundary-design.md)와 [계획](../superpowers/plans/2026-10-25-virtual-fleet-model-operator-boundary.md)에 따른 [순수 코어](../../labflow/virtual_fleet/model_operator_boundary.py), [검사](../../tests/test_virtual_fleet_model_operator_boundary.py)다. 구현 기준은 764ca91b03fa96d788dc653b20b8959e08d4304b다.

공개 문맥을 요청 해시·실제 user 메시지에 결합하고 응답을 제한된 JSON proposal로 읽는다. 모델·CLI·파일·환경·시계·DB·가상 runtime·장비를 호출하지 않는다. 수용된 proposal도 실제 실행 권한·장비 지원·모델 실행 진위·측정 유효성·평가 통과를 뜻하지 않는다. 기존 fixture result의 ai_model_called=false와 journal/evaluator는 변경하지 않았다.

## API와 입력

```python
build_operator_prompt(public_context, *, run_id, runtime_instance_id,
                      decision_id, model_request_id, producer_name, delegation) -> dict
decode_operator_response(response: bytes, prompt: dict) -> dict
ModelOperatorBoundaryError
```

__all__은 위 함수2와 오류 class 정확3이다. callback, provider registry, producer/launcher, 범용 run 함수는 없다.

public_context는 schema_version/goal/catalog/topology/role_actions/observations/last_receipt 정확7이다. 이미 공개 투영한 native JSON을 공급한다. 예약 private 필드는 삭제하지 않고 거절한다. goal은 acquire_fresh_rf_sensor와 dut_id/sensor_id/minimum_acquisition_tick 정확4, observations는 tick/setup_revision/synthetic/devices/hardware_verified 정확5다. detailed metadata·allowlist는 설계 §3을 따른다. 빈 capability metadata의 수용은 실제 harness admission을 보장하지 않는다.

delegation은 scope/harness_budgets/outer_limits 정확3이다. scope는 rf_sensor_proposal_v1, harness_budgets는 decisions/logical_requests/ticks/wall_seconds/transport_retries 정확5, outer_limits는 wall_seconds/model_calls 정확2다. caller의 전체 선언이며 예산 잔량이나 실제 타이머가 아니다. 기본 모델·기본 예산을 추가하지 않는다.

dict/list/str/int/float/bool/None의 정확 builtin만 허용하고 subclass·사용자 객체·cycle을 거절한다. dict key는 native str이다. finite float와 UTF-8 scalar만 허용하며 signed64 int를 float로 바꾸지 않는다. bool은 정수 필드에 쓰지 않는다. 비순환 alias는 독립 tree로 복사한다.

ID4는 ASCII [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}이다. producer_name은 비어 있지 않은 native str 1..200자다. 이 label은 지원되는 공식 모델 ID나 실제 호출의 증거가 아니다.

## 최소 사용 예

아래 예는 wire 결합만 확인한다. 원 응답을 만드는 실제 producer는 포함하지 않는다.

```python
import json
from labflow.virtual_fleet.model_operator_boundary import (
    build_operator_prompt, decode_operator_response,
)

context = {
    "schema_version": 1,
    "goal": {"kind": "acquire_fresh_rf_sensor", "dut_id": "dut",
             "sensor_id": "sensor", "minimum_acquisition_tick": 1},
    "catalog": {"profiles": []},
    "topology": {"devices": []},
    "role_actions": {},
    "observations": {"tick": 0, "setup_revision": 0, "synthetic": True,
                     "hardware_verified": False, "devices": {}},
    "last_receipt": None,
}
declared = {
    "scope": "rf_sensor_proposal_v1",
    "harness_budgets": {"decisions": 8, "logical_requests": 8, "ticks": 4,
                        "wall_seconds": 30, "transport_retries": 2},
    "outer_limits": {"wall_seconds": 60, "model_calls": 8},
}
prompt = build_operator_prompt(
    context, run_id="run-r0", runtime_instance_id="runtime-i0",
    decision_id="decision-d0", model_request_id="request-q0",
    producer_name="codex-synthetic-sample", delegation=declared,
)
# Supplied synthetic response, not a model call.
supplied = {
    "schema_version": 1, "kind": "virtual_operator_response",
    "request_sha256": prompt["binding"]["request_sha256"],
    "producer": {"kind": "model", "name": "codex-synthetic-sample"},
    "proposal": {"kind": "advance", "ticks": 1},
}
wire = decode_operator_response(json.dumps(supplied).encode("utf-8"), prompt)
proposal = wire["proposal"]
```

builder 반환은 schema_version/kind/binding/expected_producer/messages 정확5다. binding은 opaque ID4/context_sha256/request_sha256 정확6, expected_producer는 kind=model/name 정확2다. system/user 메시지는 정확2다. decoder가 재구성한 prompt와 supplied prompt를 비교하므로 system·메시지 순서·user 내용·binding을 바꾼 응답 결합은 거절한다. user.content의 비정규 JSON 표현도 거절한다. dict 삽입 순서는 무관하다.

2026-10-27 가상 pilot 실패에서 모델은 fresh sensor read 관측 후에도 불필요한 tick advance를 제안했고, 지정된 결정 한도에서 실행이 미완료로 끝났다. 새 builder의 고정 SYSTEM 프로필은 공개 goal·observations·last_receipt에 드러난 필수 센서, 최소 획득 tick, 현재 setup revision, 측정 유효성을 살펴 목표 충족이 관측되면 `stop/completed`를 제안하도록 설명한다. 유효한 read 후 예산 소진용 advance를 피하고, pending일 때만 정당한 advance를 제안하도록 안내한다. stale·invalid·sensor/setup 불일치·근거 부족이면 완료를 주장하지 않고 허용된 복구 제안 또는 `stop/blocked|failed`를 제안한다. 이는 모델에 주는 설명이며 host가 proposal을 교체하거나 목표 충족을 자동 판정하는 로직이 아니다. 예상 측정값, 정답 단계 수, private oracle은 프롬프트에 포함하지 않는다.

새 builder는 현재 고정 SYSTEM만 생성한다. decoder는 현재 SYSTEM과 2026-10-25 원래의 정확한 SYSTEM literal만 known profile로 받아, 해당 프로필로 전체 prompt를 재구성해 결합을 검사한다. 이전에 보존한 prompt·response의 typed decode/readback을 유지하기 위한 것이며 임의의 SYSTEM 수정이나 결합 우회를 허용하지 않는다. logical request SHA-256은 SYSTEM이 아닌 공개 core5의 C1 해시이므로 동일 core에서는 이 변경 전후에 같다. 완성 prompt 해시와 길이는 변경된다. 기존 테스트의 구 프롬프트 literal·byte 경계 기대값은 새 builder에 그대로 적용할 수 없다.

C1은 UTF-8의 json.dumps(ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))다. logical request hash는 공개 core5의 C1 SHA-256이다. 실제 user 메시지에도 해당 core와 해시가 들어간다. 완성 prompt의 해시나 실제 CLI/API 전송 bytes 해시와 구별한다. 후자의 요청은 이 API가 만들거나 전송하지 않는다.

decoder 반환은 원 wire의 schema_version/kind/request_sha256/producer/proposal 정확5다. proposal은 독립 native 사본이다. 반환 객체의 수정은 prompt·원 bytes·다음 호출에 영향을 주지 않는다. 실행/authority/assessment flags를 추가하지 않는다.

## 제안 수용과 한도

고정 wire allowlist는 goal.dut_id의 start, goal.sensor_id의 acquire/read와 빈 parameters, advance(ticks=1), stop(claim=completed/blocked/unsupported/failed, 비어 있지 않은 reason≤4096자)다. configure·DUT stop·meter·request_id·raw SCPI/shell/tool 확장을 허용하지 않는다. 실제 실행 위임과 harness의 metadata admission은 후행 별도 검사다.

| 대상 | 한도 |
|---|---:|
| C1(context) | 1048576 bytes |
| C1(prompt), user.content UTF-8 | 각각 2097152 bytes |
| 원 response | 65536 bytes |
| 독립 tree 깊이(root=0) | 32 |
| 독립 tree nodes(키 포함) | 200000 |
| plain integer | -9223372036854775808..9223372036854775807 |

response는 정확 bytes만 받는다. UTF-8 BOM·duplicate key·fence·trailing JSON·NaN/Infinity·surrogate·비유한 float를 거절한다. 정상 JSON 바깥 whitespace는 허용한다. 원 raw cap을 canonical 크기로 대체하거나 파싱 후 동일 raw cap을 다시 적용하지 않는다.

각 tree 한도는 독립적이다. context가 한도 안이어도 U2 envelope의 깊이/nodes 또는 prompt 인용 비용 때문에 거절될 수 있다. 정수 범위·정수 토큰 자릿수 초과는 prompt 재구성을 포함해 limit_exceeded다. native type·JSON 문법·Unicode·비유한 수 위반은 해당 stage 오류다.

decoder는 raw type/길이 → prompt 전체 재구성 → strict raw 파싱 → wire5 형식 → request binding → producer binding → proposal 순서로 검사한다. oversized raw와 invalid prompt가 함께 있으면 limit_exceeded, 작은 malformed raw와 invalid prompt이면 invalid_prompt다.

## 오류와 검증 범위

ModelOperatorBoundaryError의 code/str/args에는 model_operator_boundary_ 접두사와 고정 suffix만 남는다. suffix는 invalid_input, invalid_prompt, response_invalid, response_binding_mismatch, response_producer_mismatch, proposal_invalid, limit_exceeded, internal_error 정확8이다. 새 오류의 cause/context는 None이며 활성 caller except 안에서도 원 입력·예외 문자열을 chain에 넣지 않는다. KeyboardInterrupt/SystemExit/GeneratorExit는 원 객체를 그대로 전파한다. 이는 Python frame 전체를 격리하는 sandbox가 아니다.

구현 전 사전 literal과 API 부재 RED를 보존했다. 신규 검사27은 고정 hash·native 사본·활성 caller/control·실제 raw/context/prompt/depth/node 경계를 확인한다. 원 response의 유효 wire는 고정된 얕은 구조이므로 raw byte cap 안에서 nodes200000의 유효 wire 성공 경계에 도달했다고 주장하지 않는다. U2의 실제 nodes200000/200001 및 depth32/33 경계와 구별한다. 관련 부모 회귀는 신규 검사와 별도 분모로 보고한다.

2026-10-27 goal guidance 검사는 두 known SYSTEM의 typed decode, 새 builder의 안내와 불변 request binding, 미등록 SYSTEM·binding drift 거절, private budget 필드 거절을 확인한다. 이 검사는 작성된 wire에 대한 단위 검사다. 위 pilot의 실제 모델을 재호출하거나 가상 목표 종료가 개선됐음을 입증하지 않는다.

기존 회귀 실행 환경에 설치된 tests 패키지가 저장소 namespace를 가릴 수 있다. 이때 원 import 실패를 보존하고 전용 검사 프로세스에서 로컬 tests namespace를 먼저 지정한다. 기존 tests/__init__.py나 부모 source를 수정하지 않는다.

D2 concrete producer 입력·성공/실패 DTO·고정 오류·artifact refs를 빌리는 실제 private host driver는 후행 OPEN이다. 원문/ACK/readback·첫 callback 오류·case/input/expected/run/runtime 연결·deadline/감독 중단/미결 dispatch·독립 과제 평가·실제 CLI 가상 pilot을 이번 pure 단위의 완료에 합산하지 않는다. 실제 모델·품질 점수·실장비·현장·기관 적합성 검증은 미실행이다.

## 2026-10-31 선택형 공개 관측 복구 계약

기본 `rf_sensor_proposal_v1` delegation의 exact3 키, legacy/current SYSTEM 바이트, context7, wire schema1은 유지한다. `build_operator_prompt`의 인자도 그대로다. host가 명시적으로 `rf_sensor_observed_recovery_v1`을 선택할 때만 해당 scope의 별도 SYSTEM과 exact4 delegation을 사용한다. 추가 키 `recovery_budget`은 `max_wait_advances`, `wait_advances_used`, `wait_advances_remaining`, `reobservations_confirmed` 정확4 키다. 모두 native int이며 한도1..2, 사용·잔여 합=한도, 확인 재관측≤사용을 요구한다. scope와 counter는 기존 request SHA에 들어간다. decode는 scope에 맞는 정확한 SYSTEM까지 다시 검증하므로 다른 프로필을 붙이거나 counter/hash만 바꾸면 거절한다. 이 결속은 모델 실행·권한 인증이 아니다.

추가 대기는 현재 goal DUT의 `disconnected/unavailable/device_unavailable/empty outputs`와 goal sensor의 `invalid/unavailable/invalid_rf_input/empty outputs`가 함께 관측될 때만 허용한다. 두 장치의 identity/profile/role/tick/setup_revision과 synthetic=true, hardware_verified=false, configured=true가 맞아야 한다. 일반 invalid 전체를 복구 대상으로 확장하지 않는다. 정상 idle/settling/transmitting/acquiring/complete 흐름은 별도로 검증하며, 누락·NaN·다른 source·오래된 acquisition/revision·모호한 상태는 중단한다.

모델 안내와 별개로 [공개 loop](../../labflow/virtual_fleet/codex_virtual_loop.py)가 dispatch 전에 한도를 강제한다. 대기나 상태 변화만으로 completed를 허용하지 않으며, 같은 goal sensor의 valid packet, minimum acquisition tick, 현재 setup revision이 필요하다. 최종 계산·저장 성공은 후행 selector/finalizer 증거로 따로 확인한다. 이번 typed/public DTO와 fake native producer 검증은 실제 모델의 복구 능력을 입증하지 않는다.
