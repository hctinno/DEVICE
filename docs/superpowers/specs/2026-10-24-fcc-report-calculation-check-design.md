# 성적서 근거와 기존 계산 연결 023

2026-10-24, Asia/Seoul. [요청012](../../material-intake/2026-10-24-hct-fcc-corpus-request.md)와 [사례021 계약](2026-10-24-hct-fcc-case-catalog-design.md)의 검토된 페이지 근거를 기존 `labflow.calculations.calculate`와 연결한다. 개발3은 완료019 `e3d5b69157694b3a6c0a80badfa319a4087d2ac1`의 branch/검증·실패를 보존하고 새 `codex/dev3-fcc-report-calculation023-20261024`에서 신규3파일 `labflow/fcc_report_calculation.py`, `tests/test_fcc_report_calculation.py`, `docs/fcc/fcc_report_calculation_usage.md`만 소유한다. 기존 계산/core/VirtualFleet/021/Store/프로필·수집 원본은 바꾸지 않는다.

API는 `check_report_calculation(case_detail, request) -> dict`인 순수 함수다. case_detail은 021의 정확9키 case DTO이며 실제 PDF bytes 검증/retained literal 검증은 그 producer에서 실행한다. 이 함수는 제공된 DTO/출처 정합성을 재검사하며 원본 bytes 진위·기관 진위·법적 요구를 새로 인증하지 않는다. 파일/네트워크/SDK/실장비/외부모델·콜백을 받거나 실행하지 않는다. 공개 테스트는 합성이며 실제 사례·값/추출본문은 private다.

021 usage는 개발1 clone `docs/fcc/fcc_report_cases_usage.md`의 명료화본19047B/SHA `4307e3b20bbee0217cb8bbce232ff43c6322ae48a7c58657807380ae7d68efa2`가 공통 정확키 기준이다. 운영 case/doc/claim/evidence의 타입·예산·원본SHA/파일페이지·page_index.citable/literal_verified 일치와 사용한 claim이 같은 case/document에 속함을 확인한다. wrapper 검증 flags false와 report_derived를 유지한다. 다른 판본/다른 source·페이지/이미지·truncated/미확인·추론값을 입력 계산 성공으로 올리지 않는다. 필요한 값은 reviewed report_fact의 유효한 숫자 또는 명시 bool이며 0/false를 누락으로 취급하지 않는다. 구조화 value는 검수자의 해석이고 quote 문자 대응과 구분한다.

request의 정확6키는 `calculator`, `rule`, `method`, `input_claim_ids`, `reported_result_claim_id`, `comparison_policy`다. rule/method는 reviewed preview와 trim/casefold literal로 정확히 맞아야 하며 edition/정오표를 자동 치환하지 않는다. in_scope/알려진HCT 기관·검토된 제품/방법 문맥이 부족하면 계산하지 않고 insufficient_evidence로 반환한다. case의 표기 모델이 현재 DUT/FW/계측기 지원을 뜻하지 않는다.

첫 calculator는 기존 `rf_power`와 `emc_field_strength` 두 개뿐이다. 새 수식/규범 limit은 만들지 않는다.

- rf_power: input_claim_ids는 정확 `reading` 한 키이며 해당 claim의 unit은 dBm이다. 기존 함수의 W 값을 재사용한다. 보고 결과가 mW이면 명시 1000배 단위 변환만 허용하고 변환 provenance를 표시한다. reported_result_claim_id가 null이면 기본 계산 단위는 W이며 비교는 미실행이다. dBm/mW/W·dBuV를 혼동하지 않는다.
- emc_field_strength: input_claim_ids는 정확 `reading`, `antenna_factor_db_per_m`, `cable_loss_db`, `preamp_gain_db`, `instrument_corrections_applied`다. reading의 명시 단위는 dBuV 또는 dBµV, 나머지 수치는 각각 dB/m·dB·dB이며 마지막 claim은 reviewed report_fact의 명시 false여야 한다. 이미 보정됐거나 미확인인 값에 보정을 재적용하지 않는다. 기존 함수의 dBuV/m 출력만 사용하고 같은 단위의 보고 결과와 비교한다.

reported_result_claim_id는 같은 case의 reviewed report_fact 숫자 claim 또는 null이다. 비교 대상이 있으면 comparison_policy는 정확 `absolute_tolerance`, `unit`이며 유한 비음수 tolerance와 해당 결과 단위를 caller가 명시한다. 비교 대상이 없으면 policy는 null이다. tolerance는 명시적인 개발 비교 정책이며 FCC limit·측정불확도·원래 보고서 decision rule이 아니다. 반올림해 일치를 만들지 않고 원래 숫자를 비교한다. 무한대/underflow·불가능한 표현은 고정 사유로 계산 미확정 처리하며 원래 입력 근거를 보존한다.

반환 exact keys/유형·깊이/총량·고정 오류와 상태는 owner usage에 먼저 명시한다. 상태는 계산만 실행/명시 tolerance 내 수치 일치/불일치/근거 부족을 구분하고 어느 것도 DUT 적합·부적합/실측으로 바꾸지 않는다. 계산 입력/원래 unit·sourceSHA/페이지·claim ID·원래 보고 결과와 재계산·비교 policy를 추적하고, private 파일 경로·원본 bytes·raw 예외는 노출하지 않는다. report_derived·synthetic 여부, normative/hardware/physical/model execution false를 유지하며 실제 계측/native raw·AI 평가·현장 완료로 세지 않는다.

수용 검사는 두 기존 계산의 정확 재사용, source/페이지/판본·단위/입력역할 불일치 거절, missing/모호/상충·false와0·이미보정/unknown/overflow·반올림 경계/선언tolerance·입력순서·사본/JSON예산을 포함한다. 실제 P01 첫 검수 사례와021이 준비되면 같은 API에 private projection으로 입력해 별도 실행한다. 해당 방법의 수치가 아직 미확보면 미실행/공백으로 남기고 합성 검사와 준비된 다른 사례를 계속한다. 후속 가상 연결은 검토된 셋업/기준면·명시 recipe와 기존 b/g/n 전도/BW6/PSD를 재사용하는 별도 작은 단위로 배정한다.

### 구현 전 계약 보완

같은 원문 페이지여도 서로 다른 표·행의 숫자를 섞지 않는다. 명시 table/row가 전부 같거나 불명 annotation에 대해 공통 line 범위가 있어야 하며 알려진 표/행의 상충은 line이 겹쳐도 거절한다. bool 보정 flag와 기관/방법 문맥은 같은 원문 문서의 별도 근거를 허용한다. 행 후보 작업은65,536회 이하로 제한한다.

rf_power의 W→mW 비교는 원래 native W의 Fraction을1000배하여 표시 float의 재반올림과 분리한다. unit_conversion은 from/to/factor/basis/exact_value_ratio의 정확5키이며 ratio는 numerator/denominator 십진 문자열·각4096bits 한도다. 명시 tolerance0의 binary 수치 비교와 인간/기관의 유효숫자 판정은 다르며 이 정책은 개발자 비교에만 적용한다. 기존 계산 함수·RF 수식/규범 limit은 바꾸지 않는다.
