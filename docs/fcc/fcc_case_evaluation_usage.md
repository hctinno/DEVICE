# FCC 사례의 개발·독립 평가 그룹 분리

2026-10-24 · Asia/Seoul. FCC-CASE-EVALUATION-GROUPS022의 [구현](../../labflow/fcc_case_evaluation.py)과 [전용 검사](../../tests/test_fcc_case_evaluation.py)다. 전체 제공 메타데이터의 알려진 연결 성분을 먼저 만든 뒤 개발/독립/미배정을 분리한다. 실제 모델 호출·학습·평가 점수는 생성하지 않는다.

## 고정 API와 예산

```python
build_case_evaluation_split(cases, *, development_case_ids,
                           independent_case_ids) -> dict
```

입력은 정확한 JSON list/dict/str/null만 해당 필드 형식에 맞게 받는다. tuple·subclass·callback·경로/원문 본문 필드·비유한 숫자·깨진 Unicode를 거절한다. case는 최대 4,096개, 각 case의 배열은 최대 64개, 두 선택 배열은 각각 최대 4,096개다. ID 원문과 정규화된 값은 각각 1~128자/UTF-8 512바이트 안에 있어야 한다. 입력 전체와 정규화 입력은 각각 compact UTF-8 JSON 4 MiB/depth 8 이하다. 반환 전체는 16 MiB/depth 12 이하다. 초과는 고정 budget 오류이며 잘라내거나 일부만 성공 처리하지 않는다.

JSON 크기는 각 필드·배열 항목을 읽으며 누적해 제한을 넘는 지점에서 멈춘다. 한계를 넘는 전체 트리를 먼저 복사하거나 뒤의 자료를 계속 처리하지 않는다. 유효 입력의 최종 canonical byte 크기도 다시 확인한다.

case 행은 exact 8키 `case_id`, `product_family_group_id`, `fcc_ids`, `report_group_id`, `original_sha256s`, `reuse_group_ids`, `group_review_status`, `unresolved_relations`다. 누락/추가 키는 입력 오류다. family/report를 모르면 null, FCC ID/source SHA를 모르면 빈 배열로 명시하며 이 경우 적격으로 올리지 않는다.

case_id와 선택 ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`이며 공백·대소문자를 바꾸지 않는다. 나머지 명시 group/relation ID는 trim/casefold, FCC ID는 trim/upper만 적용한다. 내부 문자·판본·개정·분할 표기는 삭제하거나 추론하지 않는다. 정규화 후 빈 ID·제어 문자·배열 내 중복도 거절한다. original_sha256s는 정규화하지 않는 정확한 lowercase hex 64자리다. 모든 배열은 출력에서 정렬한다. 공식 FCC ID 문법이나 보고서 사실의 진위를 인증하지 않는다.

group_review_status는 정확히 reviewed/pending이다. 재사용 그룹이 없다는 검토가 끝났으면 reviewed+reuse_group_ids=[]이며, 미검토는 pending 또는 unresolved_relations에 명시한다. unresolved relation ID는 미확인 사유로 보존하며 알려진 연결 key로 승격하지 않는다.

## 연결과 적격

전체 입력의 family/FCC ID/report 계열/source SHA/reuse 중 하나라도 공유하면 같은 연결 성분이다. 다섯 종류는 서로 다른 namespace다. 같은 문자열이 다른 종류에 나타나도 연결하지 않는다. 선택된 case만 먼저 필터링하지 않는다. 같은 PDF의 여러 case 관계, 보고서 계열의 개정·부분 파일, A→B→C 전이 관계를 그대로 유지한다.

각 case의 직접 부적격 사유는 `missing_product_family_group`, `missing_report_group`, `missing_fcc_id`, `missing_source_sha256`, `group_review_pending`, `unresolved_relations`다. 알려진 관계로 연결된 성분의 어느 case에라도 사유가 있으면 성분 전체가 부적격이다. 부족한 key를 case_id로 대신 채우지 않는다.

group hash는 schema_version=1, 정렬한 case_ids, namespace별 정렬 key map의 canonical compact UTF-8 JSON SHA-256이다. group_id는 `case-group:`+hash다. 검토 상태만 바뀌어 연결 성분/key가 같으면 group ID는 유지된다. 입력 fingerprint는 algorithm/schema_version과 정규화·정렬한 전체 cases/두 선택 배열을 hash하며 원래 PDF의 SHA와 구별한다. 입력 순서와 표기 정규화 차이는 결과를 바꾸지 않는다.

두 선택 배열은 중복 없는 실제 case ID 배열이다. 같은 case의 양쪽 선택, 성분의 양쪽 분할, 성분 일부 선택, 부적격 성분 선택을 거절한다. 암묵적으로 나머지 case를 추가 배정하지 않는다. 두 배열이 모두 비어 있어도 전체 성분과 부적격을 계산하며 전부 unassigned에 보존한다.

## 정확한 반환 DTO

반환 exact 22키는 `schema_version=1`, `kind=fcc_case_evaluation_split`, `algorithm=namespaced_connected_components_v1`, `status=configured`, `input_fingerprint`, `scope=provided_metadata_only`, `fact_review_verified=false`, `model_execution_verified=false`, `training_executed=false`, `evaluation_executed=false`, `hardware_verified=false`, `independent_assignment_status`, `case_count`, `component_count`, `eligible_component_count`, `ineligible_component_count`, `denominators`, `cases`, `components`, `development`, `independent`, `unassigned`다.

independent_assignment_status는 독립 배정이 없으면 not_assigned, 있으면 assigned다. 어느 값도 평가 실행·독립 성능·점수를 뜻하지 않는다. group_review_status의 caller 검토 선언은 보존하지만 fact_review_verified로 승격하지 않는다.

| 필드 | 정확한 내용 |
|---|---|
| cases | case_id 순 정렬. 입력 canonical 8키와 group_id/eligible/case_ineligibility_reasons/component_ineligibility_reasons의 exact 12키. eligible은 성분 전체의 적격 |
| components | group_id 순 정렬. exact 7키 group_id/group_sha256/case_ids/keys/eligible/ineligibility_reasons/ineligible_case_ids. 마지막 배열은 직접 사유가 있는 원래 case ID |
| component.keys | exact 5키 product_family_group_ids/fcc_ids/report_group_ids/original_sha256s/reuse_group_ids, 각 값은 정렬된 고유 key 배열 |
| development / independent / unassigned | 각각 exact 2키 case_ids/group_ids의 정렬 배열. 미배정에 부적격도 보존 |
| denominators | exact 9키 provided_cases/provided_components/eligible_cases/ineligible_cases/eligible_components/ineligible_components/development_cases/independent_cases/unassigned_cases의 비음수 int |

반환은 입력과 사본을 공유하지 않는 detached JSON이다. 분모는 제공된 메타데이터에 한정되며 corpus 전체 모집단이나 포함하지 않은 외부 원문·후속 개정까지 leakage가 없음을 뜻하지 않는다. PDF 원문·페이지 추출·021 조회·Store·기존 하네스는 변경하지 않는다.

## 고정 오류와 검증

원시 값·경로·예외를 붙이지 않는 ValueError 코드만 반환한다: `fcc_case_evaluation_input_invalid`, `fcc_case_evaluation_budget_exceeded`, `fcc_case_evaluation_duplicate_case_id`, `fcc_case_evaluation_selection_invalid`, `fcc_case_evaluation_duplicate_selection`, `fcc_case_evaluation_unknown_case_id`, `fcc_case_evaluation_overlapping_selection`, `fcc_case_evaluation_cross_split_component`, `fcc_case_evaluation_partial_component`, `fcc_case_evaluation_ineligible_component`.

입력/선택의 형식·중복·unknown을 먼저 검사하고, 양쪽 동일 case → 성분 양쪽 분할 → 부분 선택 → 부적격 선택 순서로 거절한다. malformed 행/정규화 중복은 input_invalid다. deep/총량/배열 개수 초과는 budget_exceeded다. 오류 때문에 입력이나 배정을 바꾸지 않는다.

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_fcc_case_evaluation.py -q
python scripts/check_artifacts.py
```

전용 검사는 합성 metadata의 연결·누락·분할 거절·결정성·예산 계약을 검증한다. 준비된 P01 검수 group 대장의 실제 실행은 비공개 별도 증거로 보존하며, 미제공이면 미실행으로 기록한다. 공개 열람/검수 metadata의 인수는 원본 재배포·모델 학습 권한이나 실제 AI 평가 완료를 뜻하지 않는다. 함수는 파일·네트워크·시간·랜덤·전역 writer·외부 모델 I/O를 사용하지 않는다.
