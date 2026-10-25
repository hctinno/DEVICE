# 순수 가상 운전자 경계 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 공개 신규3 소유를 고정하며 총괄의 정확 base/전용 branch 실제 배정 뒤 담당이 직접 구현한다. 다른 세션의 소유와 원 proof를 보존한다.

**Goal:** 순수 operator prompt builder와 strict response decoder만 공개 신규3으로 닫고 실제 호출·보존·host 운전 검증은 후행 OPEN으로 분리한다.

**Architecture:** native JSON을 유계 검증한 뒤 문맥7/선언3/opaque IDs를 logical request hash와 실제 메시지에 결합한다. decoder는 prompt 재구성 후 원 response를 strict 파싱해 exact5 wire와 분리된 proposal tree만 반환한다. 함수2에는 callback·transport·runtime·시계·파일·환경 의존성이 없다.

**Tech Stack:** Python 표준 json/hashlib/math/re 등과 unittest. 다른 labflow 모듈을 수정·호출하지 않는다.

**Spec:** [순수 가상 운전자 경계 설계](../specs/2026-10-25-virtual-fleet-model-operator-boundary-design.md). 사전 owner literal은 설계 §8이며 소스 pin·원 제안·No·실패는 private에 보존한다.

## Global Constraints

- 구현 base는 이 공통 계약을 게시한 정확 커밋으로 총괄이 배정한다. 원 aperture clone/69f41e5·branch·58proof를 보존하고 별도 독립 clone/전용 codex/ branch에서 신규3만 작성한다.
- 원 정적 제안 v1/v2·원 No·오류와 aperture 후보·58proof를 보존한다. 실제 구현은 아래 신규3만 변경하며 공유 원본을 수정하지 않는다.
- 확정 public 소유는 model_operator_boundary.py, test_virtual_fleet_model_operator_boundary.py, model_operator_boundary_usage.md 정확3이며 디렉터리는 아래 Task에 고정한다.
- 함수2와 ModelOperatorBoundaryError만 공개한다. 범용 run_operator_trial, producer/evidence_sink/event_sink/clock callback·launcher/provider registry/새 서비스·host DTO는 제외한다.
- 기존 harness/engine/journal/evaluator/source4/closure20 및 meter/aperture·fixture report/평가 의미를 고치지 않는다. D2 WIP·root oracle·동결 proof를 열람하지 않는다.
- 순수 wire 수용은 실행 권한·장비 지원·모델 실행 진위·보존·판정의 인증이 아니다. 검증 flags를 만들지 않는다.
- C1/context/request/prompt/raw-wire hash를 구별하며 int64/native ID/ns를 JavaScript Number로 바꾸지 않는다. 관측 mtime_ns는 decimal 문자열이다.
- 기존 v1 No/C0I1M0와 정밀도·출력 관측 실패를 private 기록에 남긴다. 수정이 원 실패를 삭제하거나 원 No를 Yes로 재표시하지 않는다.
- 제품 구현은 root v2 Yes→public 계약→정확 base/branch/new3 소유 배정 뒤 시작한다. 실제 모델/CLI/API/현장/Office·외부 메시지는 그 단계의 명시 위임을 따른다.

## Review Focus

1. 사용자 객체/subclass 또는 int>2^53이 type 검사나 정규화 과정에서 hook 실행·수치 변형을 일으키지 않아야 한다.
2. 원 response raw 한도, context cap, U2 depth/nodes, prompt escaping cap의 경계와 검증 순서를 혼동하지 않아야 한다.
3. caller가 prompt/messages/core/hash를 바꿨는데 decoder가 response의 echo만 보고 받아들이지 않아야 한다.
4. API가 활성 caller except 안에서 실패해도 새 고정 오류에 caller/원 secret 예외 chain이 붙지 않아야 하며 원 control은 동일 객체로 전파돼야 한다.
5. decoder accepted를 실제 execute 권한·CLI 실행 증거·fresh measurement·독립 pass로 표시하거나 부모 계약을 바꾸지 않아야 한다.

## Task 0: 공통 계약과 실행 배정

- [x] v1 callback 오류를 확인하고 generic runner를 제거한 pure2 계약의 독립 정적 Yes를 인수했다. 제품 검증은0이다.
- [x] exact API·형상·한도·오류·검증 순서·사전 owner literal과 신규3 소유를 공개한다.
- [ ] 정확 게시 base/새 독립 clone/전용 branch와 구현 전 별도 독립 기대를 총괄 배정으로 확인한 뒤 Task 1~3을 진행한다.

## Task 1: 유계 native 입력과 순수 prompt builder

**Files:**

- Create labflow/virtual_fleet/model_operator_boundary.py
- Create tests/test_virtual_fleet_model_operator_boundary.py
- Task 3에서 같은 new3의 docs/fcc/virtual_fleet_model_operator_boundary_usage.md 작성
- Existing Modify0. D2 producer/intake 경계·부모 오류 helper를 공통화하려고 손대지 않는다.

**Interfaces:**

- Consumes: spec §2~4의 public_context7, delegation3, opaque ID4와 producer_name.
- Produces: build_operator_prompt(public_context, *, run_id, runtime_instance_id, decision_id, model_request_id, producer_name, delegation) -> native dict5.
- Produces: ModelOperatorBoundaryError(ValueError). prefix/suffix8·code/args·정제 chain은 spec §7 고정.
- Private helpers만으로 native snapshot/C1/hash/기본형상/고정 오류를 구현한다. caller callback과 labflow import를 추가하지 않는다.

- [ ] Step 1 — 정확 base/branch/new3 소유와 부모 guard를 root 배정으로 확인한다. 다른 worker의 진행 중 구현을 읽지 않는다. root는 제품 구현 전 별도 독립 literal/실패 기대를 봉인한다. 이 owner literal을 독립 oracle로 사칭하지 않는다.
- [ ] Step 2 — test_builder_literal_and_copy를 먼저 작성한다. spec §8의 고정 입력으로 context/request/prompt hashes와 2129-byte prompt, 982-byte user.content, exact5/binding6/messages2/producer2를 확인한다. expected는 제품 함수를 호출해 생성하지 않고 사전 literal을 사용한다. 입력/반환 후행 mutation과 alias 분리를 검사한다.
- [ ] Step 3 — Review Focus 1의 test_native_types_and_int64를 작성한다. dict/list/str/int subclasses, UserDict, tuple/set/Path/Decimal/사용자 객체를 거절하고 hook 호출0인지 확인한다. cycle 거절·비순환 alias 분리, True schema/tick 거절, 9007199254740993/INT64_MAX 유지, INT64_MAX+1 거절, finite float/-0.0/UTF-8 scalar를 검사한다.
- [ ] Step 4 — test_context_and_delegation_shape를 작성한다. exact7/goal4/observation5/delegation3/budgets5/outer2, ID regex·length·생산자200자, catalog/profile 허용 key set, reserved SeEd/remaining_budget 거절을 확인한다. 지원 action/관측 진위·실제 권한 판정이 없음을 빈 capability literal로 고정한다.
- [ ] Step 5 — Review Focus 2의 test_context_message_prompt_limits를 작성한다. spec의 ASCII x1048247/1048248, quote523752(+a)/524123, pad nodes199907/199908, list26/27 recipe를 각각 native로 만든다. context1048576, prompt2097152, U2 nodes200000/depth32를 inclusive로 확인하고 초과의 고정 limit_exceeded를 확인한다. 예산을 임의 낮춘 mock으로 실제 byte 경계를 대신하지 않는다.
- [ ] Step 6 — 새 검사 명령 python -B -X utf8 -m unittest discover -s tests -p test_virtual_fleet_model_operator_boundary.py -v 를 실행해 제품 부재의 RED를 보존한다. 아직 결과를 PASS로 보고하지 않는다.
- [ ] Step 7 — core 하나에 유계 snapshot/고정 오류 class·helper와 builder를 최소 구현한다. type→키→bounds→copy/serialize 순서를 지키고 큰 int의 str 변환 전에 signed64를 확인한다. 컨텍스트 예약 필드를 삭제하지 않는다. hash는 C1(core)이며 실제 user 메시지에 그 hash/producer/ID를 넣는다.
- [ ] Step 8 — 같은 명령으로 builder 관련 실제 PASS를 확인한다. 아직 decoder/host/모델/런타임/보존/평가가 구현·검증됐다고 보고하지 않는다.

## Task 2: prompt 재구성과 strict decoder·정제 실패

**Files:** Task 1의 같은 core/test2. Existing Modify0.

**Interfaces:**

- Consumes: native bytes response≤65536, caller prompt dict5. subclass/str/raw artifact ref를 받지 않는다.
- Produces: decode_operator_response(response: bytes, prompt: dict) -> 분리된 native wire5. proposal은 그 wire 안의 독립 plain tree다.
- Return에는 verification/authority/실행 결과/새 metadata를 추가하지 않는다.

- [ ] Step 1 — test_decoder_literal_and_safe_proposal_copy를 작성한다. spec의 239-byte literal이 exact5/producer2/advance2로 돌아오고 decoded hash d6049a0e8a3e2328245d8fac06974787123965aed3e61da7eccc8cdba332496e인지 확인한다. 명시 execute sensor.read와 stop blocked literal도 확인한다. mutable 반환·prompt/원 bytes·다음 호출이 공유되지 않아야 한다.
- [ ] Step 2 — Review Focus 3의 test_prompt_rebuild_not_hash_echo를 작성한다. system/user 내용/순서/extra message/바깥 producer/ID/context/hash/embedded U2 key를 각각 바꾼 prompt를 거절한다. user.content의 의미 같은 whitespace/escape 변경도 invalid_prompt, native prompt dict의 삽입 순서 변경은 수용한다.
- [ ] Step 3 — test_strict_raw_response를 작성한다. duplicate key/BOM/fence/trailing object/NaN/Infinity/1e999/surrogate/invalid UTF-8와 bytearray/str/bytes subclass를 고정 오류로 거절한다. 원문239+65297 spaces=65536은 수용하고65537은 limit_exceeded인지 확인한다. 원 bytes를 잘라내거나 재작성하지 않는다.
- [ ] Step 4 — test_wire_and_proposal_allowlist를 작성한다. wrong hash/producer/schema/kind/extra key를 구분하고 execute4/advance2/stop3의 action/device/empty params/claim/reason 조건을 각각 검사한다. ticks=True/1.0, configure, DUT stop, meter, request_id/raw command는 수용하지 않는다. 소문자 hash64와 producer native exact2를 검사한다.
- [ ] Step 5 — Review Focus 2의 test_error_precedence를 작성한다. invalid prompt+oversized raw→limit_exceeded, invalid prompt+b"{"→invalid_prompt, wrong hash+wrong proposal→response_binding_mismatch를 고정한다. raw wire 구조가 먼저 잘못됐으면 response_invalid다.
- [ ] Step 6 — Review Focus 4의 test_error_class_and_active_caller를 두 public API 각각에 작성한다. malformed input 및 내부 ordinary secret sentinel 예외를 활성 caller except 안에서 발생시켜 code/str/args/cause/context/suppress_context를 확인한다. allowlist 밖 constructor code도 invalid_input 한 개로 정규화되는지 확인한다.
- [ ] Step 7 — test_original_controls_propagate를 두 API 각각에 작성한다. 실제 내부에서 도달하는 표준 직렬화/hash/parser seam에 KeyboardInterrupt/SystemExit/GeneratorExit의 고정 객체를 주입해 동일 객체가 나오는지 검사한다. 사용자 입력 hook을 호출시키는 방식으로 control 보존을 테스트하지 않는다.
- [ ] Step 8 — 새 검사의 decoder 미구현 RED를 실행·보존한 뒤 native prompt 재구성·strict raw parser/숫자 토큰/allowlist·분리 사본 반환을 core에 구현한다. callback이나 런타임 API를 추가하지 않는다.
- [ ] Step 9 — 같은 새 test 명령으로 전체 PASS를 확인한다. 예상 validation과 ordinary internal 오류는 spec의 고정 code, 원 control은 동일 identity임을 확인한다. 오류 정제는 from None만 쓰는 데 그치지 않고 활성 caller의 __context__까지 검사한다.

## Task 3: 부모 보존·문서·독립 리뷰 인계

**Files:** 같은 new3. 신규 usage만 추가. 기존 부모/공개 index/프로젝트 root docs Modify0.

**Interfaces:**

- Consumes: Task 1/2의 actual RED/PASS와 source guard.
- Produces: 순수 API/한도/오류/미실행 범위를 명시한 usage 및 exact3 후보 인계.
- 실제 host driver·producer·retention·runtime/evaluation 결과는 생성하지 않는다.

- [ ] Step 1 — Review Focus 5의 test_pure_boundary_has_no_execution_contract를 고정한다. 반환 exact5에는 flags/authority/assessment/receipt가 없고 선언을 주어도 어떤 장비/모델 동작도 호출하지 않는지 확인한다. 금지 import/외부 호출은 core 정적 검토와 제품 호출 경로를 함께 확인한다.
- [ ] Step 2 — 관련 부모 회귀는 기존 tests/test_intake_test_intent_model_boundary.py, test_virtual_fleet_harness.py, test_virtual_fleet_policies.py, test_virtual_fleet_journal.py, test_virtual_fleet_evaluation.py를 각각 unittest discover로 실행한다. 순수 신규 API 결과와 부모 회귀, root의 과거270 PASS를 분리한다. RF 수학·동결58·실장비를 재실행했다고 보고하지 않는다.
- [ ] Step 3 — 신규 core와 관련 부모 파일의 raw/LF/mtime 문자열, v1 exact3와 그 원 실패, HEAD/index/refs/stash/WIP 보존을 확인한다. 다른 작업자/D2 파일의 변경을 우리 소유로 덮어쓰지 않는다.
- [ ] Step 4 — usage에 함수2와 exact shapes, canonical hash/actual-message 차이, raw cap/depth/nodes/int64, 고정 오류/원 control, accepted가 실행 권한/진위가 아님을 적는다. v1 No의 범용 callback 경계는 이번 단위에서 제거됐음을 명시한다.
- [ ] Step 5 — python -B -X utf8 scripts/check_artifacts.py와 신규 usage/문서 UTF-8·링크 검사를 실행한다. 문서 검사를 계측 정확도/기관 적합성/AI 운전 입증으로 표시하지 않는다.
- [ ] Step 6 — 정확3 후보·부모 guard·실제 RED/PASS·owner literal을 root에 인계하고 독립 리뷰→최소 수정→재검증→통합 순서를 따른다. commit/push/branch 변경은 당시 root 배정 범위에서만 수행한다. 정확 실행 배정을 받은 담당은 관련 검증 뒤 정상 commit/push하고 총괄의 원격 대조·독립 검토로 인계한다.

## Future host OPEN — 이 계획의 완료 조건에 합산하지 않음

D2가 concrete 입력·성공/실패 DTO·고정 오류·artifact refs를 고정한 뒤 그 실제 계약을 직접 빌린다. 이 작업은 그 반환 구조나 ACK/readback 규약을 발명하지 않는다.

후행 private 유계 driver에서 실제 CLI 요청/원문/추출 text를 exact run/case/input/expected와 연결하고 기존 step/events/result와 trusted 준비 callable을 직접 조합한다. 최초 callback 오류 보존·raw 보존/ACK/readback·사전/사후 실패·미결 요청·시작 전/늦은 모델 시간·감독 중단·행동 admission·독립 assessment는 그때 별도 실패 literal과 독립 oracle로 검증한다. 기존 _record가 sink control을 밖으로 전달한다고 가정하지 않는다.

pure 구현 수용 뒤에도 실제 모델 호출·CLI 가상 pilot·그룹 비교·품질 점수는 OPEN이다. 구체 실행 위임·producer 설정·예산·독립 평가 인수가 준비되면 이어가며 모델명 재선택 대기나 provider registry로 이를 대신하지 않는다.

## 자기 검토

spec의 형상·hash/message·raw/크기·순서·오류/원 control·사본 요구는 Task 1/2에, 상대 소유/부모 보존·미실행은 Task 3에 대응한다. Review Focus 5항목 모두 검사 단계가 있다. 공개 시점의 실제 수행은 정적 계약 검토·문서 관측뿐이며 제품 API·모델 호출은0이다. 미래 제품 검사를 이미 통과한 것처럼 보고하지 않는다.
