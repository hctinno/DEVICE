# Operator 응답 schema 호환 프로필

2026-10-26, Asia/Seoul. DEV2-GOAL-OPERATOR-SCHEMA-001.

최초 실제 CLI 0.164/SOL 실행은 `proposal.oneOf is not permitted when strict is true`인 HTTP 400 `invalid_json_schema`로 실패했다. 이는 총괄이 보존한 실제 관측이며 아래 문서 해석이나 새 가상 검증 결과와 구별한다. 원 실패를 성공·재생으로 바꾸지 않는다. 누적 실제 18회/잔여 7회이며 이 구현 담당의 추가 실제 모델/API 호출은 0회다.

[OpenAI Structured Outputs 공식 문서](https://developers.openai.com/api/docs/guides/structured-outputs)를 같은 날짜에 재확인했다. 지원 schema 부분집합, 모든 필드의 required 지정, 객체의 additionalProperties=false, 중첩 anyOf 지원을 확인했다. 이 수정 뒤의 실제 provider 수용 여부는 미재검증이다.

## 고정 프로필

[공통 helper](../../labflow/virtual_fleet/operator_response_schema.py)는 파일·권한·provider·fallback을 다루지 않는다. SCHEMA_BYTES는 정수 길이 3052다. CURRENT_SCHEMA_SHA256은 `e045c19a6fa5041780091f7a459e2b9f5a909d634cd6a7ccb6d82f16fafccf05`, LEGACY_SCHEMA_SHA256은 `aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb`다.

current_response_schema_bytes()는 현재 고정 native bytes를 반환한다. is_current_response_schema_bytes(value)는 exact native bytes/길이/hash가 현재 프로필과 일치할 때만 true다. is_known_response_schema_bytes(value)는 읽기용으로 현재·역사 프로필을 인식한다. bool·bytes subclass·bytearray·문자열·재직렬화·추가 개행·변형은 현재 실행 프로필이 아니다. known을 실행 승인에 사용하지 않는다.

[계약](codex_first_decision_contract.json)의 response_schema는 현재 literal, legacy_response_schema는 기존 literal과 hash를 보존한다. schema_version=1, wire keys/kind/strict decoder·허용 도구·권한은 유지한다. 변경은 proposal의 고정 union 한 곳의 oneOf→anyOf다. execute 두 branch는 서로 다른 device_id const를 가지며, advance/stop은 서로 다른 kind const를 가진다. 모든 branch가 pairwise 배타적이므로 이 고정 schema에서는 두 union의 허용 응답 집합이 같다. 임의 schema나 겹치는 branch의 자동 변환 기능은 없다.

first-decision·one-action·persistent-loop는 파일/가상 runtime/producer 진입 전에 현재 프로필만 수용한다. 옛 프로필은 각 공개 entry의 기존 invalid_input으로 거절하며 provider를 다시 호출하지 않는다. 합성 접수 fixture도 helper의 현재 bytes를 사용한다. model_comparison의 matrix 구성·검증은 역사 프로필 읽기를 유지하지만, 두 실행 entry는 현재 프로필만 producer 이전에 허용한다. 역사 matrix·승인·소비 대장·원 응답을 수정하거나 새 프로필로 소급 변환하지 않는다. 기존 역사 literal을 실행하던 비교 테스트는 이제 역사 읽기 또는 명시적인 현재 프로필 double로 구별해서 검증해야 한다.

## 더 작은 실행 한도

run_codex_virtual_loop와 run_intake_plan_virtual_execution의 선택 keyword는 model_process_limit=8, wall_seconds_limit=180이다. 생략 시 기존 8회/180초다. 모델 상한은 native int 1..8, wall은 native int/float의 유한 값 0<wall<=180만 받는다. bool·subclass·문자열·NaN/Inf·초과값은 파일/runtime 전에 거절한다. adapter는 blocked/invalid_input을 반환하고 loop는 기존 invalid_input 예외를 낸다.

낮춘 값은 선언·하네스 decision/wall·remaining delegation·모든 producer 예약/admission·외부 deadline·elapsed 최종 대조에 사용한다. tool/tick/file/harness 최대 한도는 기존 범위 안이다. producer 한 번은 min(60, remaining_wall-6), retry=0이며, 남은 시간이 6초 이하면 producer 예약/진입 없이 기존 budget/deadline 실패로 멈춘다. 이미 예약·소비한 시도는 환불하거나 초기화하지 않는다. 이 인자는 권한 발급·계정 잔여 횟수의 인증 API가 아니다.

## 검증 범위

`python -m unittest discover -s tests -p test_codex_operator_schema_compat.py -v`는 기존 benign fixture child와 공개 transport double로 프로필·branch 배타/동일집합·소비자·하향 한도를 확인한다. 기존 interpreter의 jsonschema를 독립 대조에 사용하며 제품 dependency는 추가하지 않는다. 새 helper source가 pin manifest에 포함되어 source hash가 이전 실행과 달라지는 것은 정상적인 변경이다. 원 실패의 source mismatch를 수정하거나 과거 응답을 새 성공으로 해석하지 않는다. 실제 모델/API 재검증, 실장비·현장·전체 업무 완료는 미실행이다.
