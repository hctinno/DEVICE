# Conducted twin의 제공 대조값 비교

2026-10-26 Asia/Seoul. DEV3-CONDUCTED-TWIN-COMPARISON-001은 한 개의 on-average 전도 전력 결과를 같은 조건의 제공 값과 비교하는 순수 함수다. 공개86b0c55359d295ec5d37d4a903ddcf20cc1907db와 자기 RF3ba·writer e3의 정상 cherry 위에서 신규 source/test/이 사용법3개만 소유한다. 기존 결과·보정·그룹 분할 코드는 바꾸지 않는다. 아래 계약을 먼저 기록한 뒤 구현·합성 검증했다.

```python
compare_conducted_twin_result(
    twin_result, reference=None, *, comparator_policy=None, lineage=None,
) -> dict
```

새 실행, 파일 읽기·쓰기, 원본/PDF·Store·모델·장비 호출은 없다. 제공 데이터가 부족하면 not_assessed와 null 및 이유를 반환한다. KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit는 원 객체로 전파한다.

## 수치와 같은 조건

twin_result는 [기존 결과 DTO](conducted_twin_result_usage.md)의 recorded/full_bound 결과여야 한다. 기존 순수 snapshot/C1/hash/binding 검증과 native plan 검증을 재사용한다. 저장 writer를 실행하지 않는다. 첫 지원은 method_id=conducted_synthetic / method_version=1, plan과 원 journal quantity의 명시 metric=on, 보정된 calculation.corrected의 dBm, 명시 source_output 기준면이다. 실제 native sensor packet에는 quantity 키가 미생성일 수 있으며 키를 만들지 않는다. packet에 quantity가 명시돼 있으면 on_average와 같아야 한다. raw sensor_input 값을 DUT 출력 값처럼 비교하지 않는다. 권위false·conformity not_assessed/null 및 원 method 조건도 유지해야 한다.

reference는 exact10이다.

| 필드 | 계약 |
|---|---|
| schema_version / kind | native int1 / provided_conducted_reference |
| case_id | 기존 group primitive가 받는 opaque case ID |
| revision / split_id | 제공 제품·자료 개정 문자열 / 명시 split ID |
| data_origin | provided_synthetic, provided_measured, provided_replay, unknown 중 원 주장 |
| method | exact2: method_id, method_version |
| source_settings | 기존 D1 native source6 |
| measurement | exact4: value, unit, metric, reference_plane |
| evidence_refs | 비어 있지 않은 bounded 문자열 배열. 참조를 따라 읽지 않음 |

source6은 frequency_hz, power_dbm, bandwidth_hz, duty_cycle, crest_factor_db, modulation이다. 기존 integration._source_configuration으로 검증하고 같은 유한 숫자 값·같은 modulation을 요구한다. bool이나 파생 숫자 타입을 숫자로 승격하지 않는다. reference.method와 source6, measurement.metric=on / unit=dBm / reference_plane=source_output이 결과의 원 방법·조건과 같아야 한다. 다른 방법·판본·metric·기준면·단위·입력조건이나 unknown 출처는 비교를 보류한다. 원 type/값을 수정하거나 단위를 추측해서 변환하지 않는다.

comparator_policy는 exact4: policy_id(명시 문자열), policy_version(양의 native int), purpose=independent_validation, tolerance_db(finite nonnegative native int/float)다. tolerance의 기본 숫자·규격 한계·불확도 값은 없다. policy가 없거나 tolerance가 없거나 잘못됐으면 보류한다. policy ID는 caller 선언이며 기관/물리 승인이 아니다.

signed difference는 twin−reference, absolute difference는 그 절댓값이다. native 숫자를 JSON의 십진 표기대로 Fraction(str(value))로 해석해 차이와 inclusive `absolute <= tolerance`를 비교한다. float 출력은 그 유한 투영이다. 0.1 같은 경계의 이진 반올림으로 허용오차 결과가 뒤집히지 않도록 decision은 exact rational에서 정한다. 출력 범위 초과·0으로 소실되는 투영은 numeric_range로 보류한다. 수치 비교에 맞지 않는 W 변환·새 보정·가상 RF 재실행은 하지 않는다.

## 제공 계보와 독립 검증 분할

lineage는 exact7: schema_version=1, kind=conducted_comparison_lineage, split_id, revisions, cases, calibration_case_ids, independent_case_ids다. cases는 기존 [순수 분할 primitive](../../labflow/fcc_case_evaluation.py)의 native exact8 metadata를 그대로 제공한다: case_id, product_family_group_id, fcc_ids, report_group_id, original_sha256s, reuse_group_ids, group_review_status, unresolved_relations. 최대128개이며 metadata는 원본 사실의 인증이 아니다.

calibration_case_ids는 caller가 제공한 보정용 모집단 선택이다. 명시 빈 배열은 ‘제공된 보정용 case 없음’이라는 caller 주장만 뜻하며 완전성은 검증하지 않는다. independent_case_ids는 정확히 reference.case_id 한 개다. revisions는 모든 제공 case ID에 대한 비어 있지 않은 개정 문자열 map이며 reference.revision과 해당 값이 같아야 한다. lineage.split_id와 reference.split_id도 같아야 한다.

build_case_evaluation_split(cases, development_case_ids=calibration_case_ids, independent_case_ids=independent_case_ids)를 직접 호출한다. family/FCC ID/report group/original SHA/reuse relation의 연결 성분이 split을 가로지르거나, 중복·누락·불완전 성분·미검토/미해결 관계면 보류한다. 제공된 모든 case를 먼저 묶으므로 중간 관계를 거치는 leakage도 막는다. 개정·split 이름을 바꿔 기존 같은 자료 관계를 우회하지 않는다. 서로 관련 없는 제품의 개정 이름이 우연히 같은 것만으로 같은 자료라고 추정하지 않는다. 개정 간 동일 자료 관계는 원 SHA·report/reuse 관계로 명시해야 하고 미확정 관계는 unresolved_relations로 남긴다.

이 검사는 제공 metadata의 분리만 확인한다. lineage가 완전한지, ‘실측’ label이 진짜인지, 원본 권리·사용 허가·물리 정확도·불확도 범위를 인증하지 않는다. 실제 대조 자료가 없는 첫 검증은 합성 known-pair 및 결함·누락·경계로 수행한다.

## 반환과 한계

반환 exact11은 schema_version, kind, status, bindings, scope, comparison, independence, reference, reasons, conformity, verification이다. kind=conducted_twin_comparison, status=compared/not_assessed다. bindings는 제공 result/reference/policy/lineage canonical SHA를 보존하며 원본 진위의 증명이 아니다. scope는 비교에 확인된 method/source6/metric/plane/unit이며 보류 때 null일 수 있다.

comparison exact8은 twin_value_dbm, reference_value_dbm, signed_difference_db, absolute_difference_db, tolerance_db, within_tolerance 및 signed_difference_rational_db, absolute_difference_rational_db의 exact 유리수 문자열2개다. 필요한 조건 하나라도 부족하면 이8개는 모두 null이다. independence는 제공 metadata 분리 상태·split fingerprint·case 수·대조 case ID만 보여준다. reference는 원 data_origin 주장과 authenticity_verified=false, rights_verified=false, uncertainty_db=null을 구별한다. reasons는 고정 code/field/detail이며 원 예외·경로·본문을 복사하지 않는다.

conformity는 항상 status=not_assessed, verdict=null이다. verification의 hardware_verified, physical_verified, uncertainty_assessed, model_execution_verified, execution_authority는 항상 false이고 method_approval=not_assessed, source_bytes=not_reopened, trust_scope=provided_values_and_group_metadata_only다. 허용오차 만족은 이 비교의 수치 결과이며 FCC PASS·물리 정확도 승인·실행 허가가 아니다. 부모의 61/23/38/284 결과를 이 단위 검사로 합산하거나 반복하지 않는다. 전역 Codex 실제17회 수신과 이 단위 새 호출0, 원16 기록 보존을 구별한다.

입력은 plain native JSON만 받는다. 전체 canonical≤2MiB, result≤1MiB, 기존 snapshot depth32/nodes1M을 넘으면 보류한다. source6·숫자·case 수와 문자열도 각각 검사한다. 출력≤256KiB를 유지하며 원본은 수정하지 않는다. 실장비·실측·불확도·현장·기관 적합성은 미검증이다.

지원되는 명시 data_origin label은 보류하더라도 유지한다. unknown은 unknown으로 남고 비교 숫자는 null이다. 사유 code는 input_invalid, input_limit, twin_result_missing, twin_result_invalid, twin_result_incomplete, twin_binding_invalid, twin_measurement_invalid, reference_missing, reference_invalid, measurement_invalid, method_mismatch, metric_mismatch, unit_mismatch, reference_plane_mismatch, source_settings_invalid, source_settings_mismatch, origin_unknown, policy_missing, policy_invalid, tolerance_missing, tolerance_invalid, lineage_missing, lineage_invalid, lineage_limit, lineage_overlap, lineage_unconfirmed, revision_mismatch, split_mismatch, numeric_range, output_limit이다. lineage detail은 기존 분할기의 known 고정 코드만 포함한다.

## 이번 단위의 검증

recorded label이 있어도 raw packet에 명시된 invalid/status 실패·다른 source ID·상충한 power/frequency/duty/crest가 있으면 보류한다. 미생성 quantity 키는 만들지 않으며 같은 journal의 명시 metric과 현재 packet의 모순을 검사한다. 이는 제공 값의 명시적 모순 검사이며 원 RF 실행·보정 계산의 재실행이 아니다.

최종 owner26개가 failure/error/skip0으로 통과했다. 하나의 genuine D1·가상 Trial/setup/journal/report에서 만든 native 결과를 사용하되 수치 기대는 독립 Decimal로 계산했다. 조건6·metric/방법/기준면/단위 불일치, unknown·누락·native bool/비유한/파생 타입, 허용오차0과 십진 경계, 수치 범위 초과, 그룹의 각 namespace·전이 leakage·개정/split label 우회·부분/미확정 관계를 확인했다. 제어 예외 원 객체, 입력 불변/반환 분리와 no-I/O 경계도 검사했다.

별도 숫자12벡터·보류5벡터는 Decimal precision1000으로 대조해 일치했다. float 투영 값이 허용오차와 같아 보여도 exact 차이가 더 크면 outside이며 유리수 trace로 대조할 수 있다. 마지막 직렬화 실패 뒤 이미 계산된 숫자를 반환하지 않는 것과 unknown label 보존도 실제 fault test로 확인했다. 숫자 표본은 제공 합성 입력 재사용이며 실제 대조 측정0이다. owner26과 표본12/5를 독립 사례 수로 합산하지 않는다.

수정 전 실패·테스트 준비 오류·처음 잘못 요구한 meter quantity 키와 잘못 선택한 두 source 조건값은 원 로그/스냅샷에 보존했다. 기존 61/23/38/284를 다시 실행하지 않았다. 이 검증은 실제 비교 수학과 제공 metadata 분리 계약의 검증이며 실물 트윈 정확도·정식 허용오차·기관 적합성의 검증은 아니다.
