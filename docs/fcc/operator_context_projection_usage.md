# 가상 운전자 공개 문맥 투영

2026-10-27, Asia/Seoul. 폐쇄 loop는 원 `context8`을 기존 64장비 전체 상태로 검증·보존한다. `remaining_budget`을 별도 기존 binding 기록으로 분리한 뒤 공개 context7 전체를 기존 `build_operator_prompt`로 먼저 검사한다. 원 프롬프트의 canonical UTF-8 길이에도 기존 host artifact cap 262,144 bytes를 적용한다. 이 사전 프롬프트는 메모리에서 폐기하며 파일로 기록하거나 producer에 전송하지 않는다. 기존 입력 type·private/reserved 필드·크기·binding·delegation 오류는 투영에 앞서 같은 경계에서 거절된다. 따라서 제거 대상 장비의 금지 정보나 원 host cap 초과가 투영으로 숨겨져 수락되지 않는다.

`project_operator_context(public_context)`는 추가로 동일 경계의 native snapshot/context 검사를 재사용하는 순수 함수다. 원 context7과 반환값은 분리된다. goal의 DUT·sensor와 장비 receipt의 `device_id`에서 시작해 topology의 모든 명시 연결을 방향·kind와 무관하게 닫는다. 정상 `advance` receipt에는 device ID가 없으며 정확한 6키/`advanced_ticks` 형상일 때 원형을 보존하고 별도 장비 seed 없이 처리한다. 연결 kind에는 RF뿐 아니라 power, environment, control, measurement 및 향후 명시 ground/source/path도 포함된다. 선택 관측·프로필·역할 동작·마지막 receipt의 알려진 장비 ID 참조를 함께 닫는다. 선택한 topology node, connection, catalog profile, observation device, role_actions row는 원형을 보존하며 각 묶음의 바깥 metadata와 goal·last_receipt도 원형이다. 동작 권한이나 runtime 상태를 새로 만들지 않는다.

Topology에 미지 key, 중복 node/profile, dangling 연결, 포트·kind 불일치, 다중 source가 같은 입력에 연결된 경우, cycle 또는 필수 profile/observation/role/receipt 참조가 불분명한 경우 투영하지 않고 검증된 context7 전체의 분리된 복사본을 반환한다. 이는 의미 보존 fallback이며 invalid 입력을 정상화하지 않는다. 원래 경계가 거절할 형상과 private 필드는 그대로 오류로 남는다. loop는 투영 결과를 기존 `public-context7.json`에 기록하고 정확히 그 객체로 실제 프롬프트를 생성한다. 따라서 prompt의 `context_sha256`은 compact context7과 결합한다. 원 전체 `context8.json`, 기존 `binding.json`의 분리 예산, 원 source pin, 원 runtime 관측·평가·journal은 유지한다.

2026-10-31 수정은 원 독립 No의 `sensor.values.source_id = "missing-device"` 반례를 다룬다. 기존 전체 boundary 검사에 유효한 이 문맥은 오류로 거절하지 않고, 원 5개 node·profile·observation·role action과 metadata를 모두 담은 detached full-copy로 반환한다. 축소 가능성이 불분명하다는 뜻이며, 출처나 측정의 유효성을 새로 인정하지 않는다. 원 No와 수정 전 실패 기록은 보존하며, 후보 d7ba026의 독립 48개·동일 source MOCK 1건을 확인한 뒤 가상 범위로 수용했다.

새 fallback 검사는 마지막 receipt와 선택 closure에 속한 observation·profile·role action의 중첩 dict/list에 적용한다. 명시 장비참조 필드는 `device_id`, `source_id`, `input_source_id`, `reference_source_id`다. 이 값이 native 문자열 장비 ID로 확인되지 않거나 topology에 없으면 축소 전에 전체 복사본으로 돌아간다. 알려진 참조나 연결로 뒤늦게 선택된 장비도 다음 closure에서 검사한다. 미선택 spare의 unknown 참조만으로 새 fallback을 만들지는 않는다. 일반 설명·`source` 문구·`profile_id` 같은 다른 ID 영역을 장비참조로 추측하지 않는다. 전체 문맥에 대한 기존 private/type/크기·full-prompt 검사는 이 선택 검사보다 먼저 유지되므로 미선택 부분의 원래 경계 위반도 숨겨지지 않는다. 오류 enum·예산·도구 및 실장비 실행 제한은 바꾸지 않는다.

이 네 필드 제한은 **미확인 장비참조의 새 fallback 판정** 범위다. 기존 known-ID closure는 모든 값에서 이미 알려진 장비 ID와 같은 문자열을 보수적으로 선택하는 동작을 유지한다. 따라서 설명이나 `profile_id` 값이 `spare` 장비 ID와 같으면 그 장비가 추가 선택되고, 그 안의 미확인 참조로 full-copy가 될 수 있다. 이는 축소 효율의 한계이며 typed-only closure나 실제 모델 비용 절감을 보장하지 않는다.

허용된 과거 실제 7번째 요청의 공개 문맥을 읽기 전후 파일 pin을 유지하며 로컬 순수 계산한 결과는 다음과 같다. 원 topology 64 node/13 connection에서 goal 연결 component 11 node/13 connection, profile 11, role 10이 선택됐다. 동일한 현재 SYSTEM 프로필과 동일 ID·delegation으로 비교한 canonical UTF-8 context는 116,409→28,784 bytes(87,625 감소), 완성 prompt는 134,090→35,525 bytes(98,565 감소)다. 이 계산은 실제 모델 호출·토큰 청구량 또는 비용 상한의 증거가 아니다. 이전 실제 request 파일의 133,458 bytes는 당시 legacy SYSTEM을 포함하므로 동일 프로필 비교치와 구별한다.

검증에는 작성한 topology 및 private 필드 단위 검사와 가상 MOCK loop 회귀를 사용한다. 실제 모델 재호출, OS/ADB, 실장비, 현장, 기관 적합성 검증은 포함하지 않는다.
