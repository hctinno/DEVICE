# FCC 사례 평가 그룹 분리 022

2026-10-24, Asia/Seoul. [신규 corpus 요청012](../../material-intake/2026-10-24-hct-fcc-corpus-request.md)와 [사례 조회021 설계](2026-10-24-hct-fcc-case-catalog-design.md)의 독립 평가 유출 방지를 실행 코드로 만든다. 개발2의 HARNESS016 소유 게시 `7d8968a7ea3df838890d9b34eb71b7825a8a5b66`와 독립 최종 검토를 보존한 뒤 별도 작은 단위로 진행한다. 실제 모델 평가·학습·점수 산출은 이번 단위에 없다.

## 소유 파일·API

개발2는 새 `codex/dev2-fcc-case-evaluation022-20261024`에서 `labflow/fcc_case_evaluation.py`, `tests/test_fcc_case_evaluation.py`, `docs/fcc/fcc_case_evaluation_usage.md` 3파일만 소유한다. 기존 harness/013/Store/core·021·PDF/수집자 파일은 바꾸지 않는다.

`build_case_evaluation_split(cases, *, development_case_ids, independent_case_ids) -> dict`를 순수 JSON 입력/출력 함수로 구현한다. I/O/콜백/시간/랜덤/전역 writer·실제 모델 호출은 없다. caller는 검수된021/P01 메타데이터를 비공개로 아래 행에 projection한다. 행을 제공했다고 사실·분류 진위를 인증하지 않으며, 실제 그룹 검토의 상태를 보존한다. 정확 DTO/예산/고정 오류·keys는 소유 usage에서 먼저 고정해 총괄이 확인한다.

case 행의 exact 8키: `case_id`, `product_family_group_id`, `fcc_ids`, `report_group_id`, `original_sha256s`, `reuse_group_ids`, `group_review_status`, `unresolved_relations`. ID는 제한 길이의 명시 문자열, SHA는 lowercase64, list는 중복 없는 제한 배열이다. product_family_group_id/report_group_id는 unknown이면 null이다. product family group은 검수한 canonical 그룹키이며 보고서의 표시 문자열을 자동 분류하지 않는다. fcc_ids의 비교는 trim/upper, 다른 명시 group ID는 trim/casefold 수준으로 고정한다. 판본/부분/개정 문자열을 regex로 삭제하거나 관계를 추측하지 않는다. group_review_status는 reviewed/pending, unresolved_relations는 미확인 관계 ID 목록이다. reused group이 없다는 검토가 끝났으면 reviewed+빈 배열이고, 미확인이면 pending/unresolved로 구분한다.

전체 입력의 **제품군 그룹/FCC ID/보고서 계열/원본SHA/재사용 그룹** 중 하나라도 공유하면 같은 연결 성분이다. 종류별 namespace를 분리하고 동일 문자열의 서로 다른 종류를 충돌시키지 않는다. 선택된 case만 먼저 골라 그룹을 만드는 오류를 금지한다. 동일 PDF의 여러 관계는 각 case를 유지하되 한 물리 SHA 그룹으로 연결한다. sort된 ID·명시 key와 연결 성분에서 deterministic 그룹 ID/hash를 만들며 입력 순서를 바꿔도 동일해야 한다.

family/report group/FCC ID/source SHA 중 필수 키가 없거나 검토 pending/관계 unresolved이면 해당 case는 ineligible다. 이미 알려진 관계로 연결된 전체 성분에도 그 부적격이 전파된다. 부족한 키를 case_id로 대체해 독립 그룹으로 만드는 것을 금지한다. 포함하지 않은 외부 원문/후속 버전까지 전수 leakage 없음으로 주장하지 않는다.

development_case_ids와 independent_case_ids는 중복 없는 실제 case ID 배열이다. unknown/중복/양쪽동일case를 거절한다. 같은 연결 성분을 양쪽으로 나누거나 성분 일부만 선택하면 고정 오류로 거절하며 암묵적으로 다른 case를 추가 배정하지 않는다. ineligible 성분 선택도 거절한다. 어느 쪽에도 배정되지 않은 case는 unassigned에 보존한다. 독립 평가가 비어 있으면 구성 상태만 나타내며 평가 완료/score를 만들지 않는다.

반환에는 실제 연결 성분/각 case·key·적격 사유·개발/독립/미배정 분리와 입력 fingerprint/분모를 담는다. `model_execution_verified=false`, `training_executed=false`, `evaluation_executed=false`, `hardware_verified=false`를 명시한다. 보고서 사실·계산 재검증·합성 시뮬레이션·실제 AI 평가·실장비 검증을 하나의 성능 점수로 합치지 않는다. bounded JSON의 exact 타입/깊이/총량·숫자·detached 복사를 검사하고 불명 응답을 성공으로 올리지 않는다.

## 수용 조건

가족/FCC/report/SHA/reuse 각각과 A→B→C의 전이 연결, 종류 namespace 충돌 없음, 개정·분할·동일PDF case 관계 보존, 누락/미검토의 성분 전체 부적격, 양쪽 분할·부분 선택·unknown/중복·입력 순서·nonfinite/타입/예산 경계를 검사한다. 테스트 입력은 합성이며 실제 P01 그룹 대장은 준비되는 작은 검수 묶음부터 private로 실행한다. 이것은 grouping 계약 검증이며 실제 모델의 독립 평가 점수가 아니다. 원본·수집/기존 source의 전후 SHA 불변과 실패/수정·owner 커밋/푸시·원격 대조를 보고한다.
