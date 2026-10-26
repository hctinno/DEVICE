# 가상 운전자 공개 문맥 투영

2026-10-27, Asia/Seoul. 폐쇄 loop는 원 `context8`을 기존 64장비 전체 상태로 검증·보존한다. `remaining_budget`을 별도 기존 binding 기록으로 분리한 뒤 공개 context7 전체를 기존 `build_operator_prompt`로 먼저 검사한다. 원 프롬프트의 canonical UTF-8 길이에도 기존 host artifact cap 262,144 bytes를 적용한다. 이 사전 프롬프트는 메모리에서 폐기하며 파일로 기록하거나 producer에 전송하지 않는다. 기존 입력 type·private/reserved 필드·크기·binding·delegation 오류는 투영에 앞서 같은 경계에서 거절된다. 따라서 제거 대상 장비의 금지 정보나 원 host cap 초과가 투영으로 숨겨져 수락되지 않는다.

`project_operator_context(public_context)`는 추가로 동일 경계의 native snapshot/context 검사를 재사용하는 순수 함수다. 원 context7과 반환값은 분리된다. goal의 DUT·sensor와 장비 receipt의 `device_id`에서 시작해 topology의 모든 명시 연결을 방향·kind와 무관하게 닫는다. 정상 `advance` receipt에는 device ID가 없으며 정확한 6키/`advanced_ticks` 형상일 때 원형을 보존하고 별도 장비 seed 없이 처리한다. 연결 kind에는 RF뿐 아니라 power, environment, control, measurement 및 향후 명시 ground/source/path도 포함된다. 선택 관측·프로필·역할 동작·마지막 receipt의 알려진 장비 ID 참조를 함께 닫는다. 선택한 topology node, connection, catalog profile, observation device, role_actions row는 원형을 보존하며 각 묶음의 바깥 metadata와 goal·last_receipt도 원형이다. 동작 권한이나 runtime 상태를 새로 만들지 않는다.

Topology에 미지 key, 중복 node/profile, dangling 연결, 포트·kind 불일치, 다중 source가 같은 입력에 연결된 경우, cycle 또는 필수 profile/observation/role/receipt 참조가 불분명한 경우 투영하지 않고 검증된 context7 전체의 분리된 복사본을 반환한다. 이는 의미 보존 fallback이며 invalid 입력을 정상화하지 않는다. 원래 경계가 거절할 형상과 private 필드는 그대로 오류로 남는다. loop는 투영 결과를 기존 `public-context7.json`에 기록하고 정확히 그 객체로 실제 프롬프트를 생성한다. 따라서 prompt의 `context_sha256`은 compact context7과 결합한다. 원 전체 `context8.json`, 기존 `binding.json`의 분리 예산, 원 source pin, 원 runtime 관측·평가·journal은 유지한다.

허용된 과거 실제 7번째 요청의 공개 문맥을 읽기 전후 파일 pin을 유지하며 로컬 순수 계산한 결과는 다음과 같다. 원 topology 64 node/13 connection에서 goal 연결 component 11 node/13 connection, profile 11, role 10이 선택됐다. 동일한 현재 SYSTEM 프로필과 동일 ID·delegation으로 비교한 canonical UTF-8 context는 116,409→28,784 bytes(87,625 감소), 완성 prompt는 134,090→35,525 bytes(98,565 감소)다. 이 계산은 실제 모델 호출·토큰 청구량 또는 비용 상한의 증거가 아니다. 이전 실제 request 파일의 133,458 bytes는 당시 legacy SYSTEM을 포함하므로 동일 프로필 비교치와 구별한다.

검증에는 작성한 topology 및 private 필드 단위 검사와 가상 MOCK loop 회귀를 사용한다. 실제 모델 재호출, OS/ADB, 실장비, 현장, 기관 적합성 검증은 포함하지 않는다.
