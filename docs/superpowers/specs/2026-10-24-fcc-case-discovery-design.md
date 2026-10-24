# FCC 검토 사례 발견028 설계

2026-10-24, Asia/Seoul. [021 계약](2026-10-24-hct-fcc-case-catalog-design.md)의 `.search/.match_intake`는 시험 진행 후보의 보수적인 근거 조건을 유지한다. 실제 S05의 올바른 제품/15.255/판본도 조건 상충 때문에 후보0인 한계를 감추지 않는다. 총괄은 같은 메모리 인덱스에 별도 `.discover(query)` 읽기 API/kind를 추가하는 방식을 채택했다. 별도 원문 parser/reader를 만들지 않는다.

개발1 전용 `codex/dev1-fcc-case-discovery028-20261024`, 고정0213c599fe 부모와 기존 실패/실제 producer를 보존한다. 소유는 기존 `labflow/fcc_report_cases.py`, `tests/test_fcc_report_cases.py`, `docs/fcc/fcc_report_cases_usage.md` 3파일이다. 기존 search/접수 연결·권리·평가 적격·Store·출력/실행 권한은 변경하지 않는다.

query는 기존 product_family/rule/method/model 정확4키를 쓰고 부분 질의를 허용한다. trim/casefold literal만 비교하며 판본/모델 alias·제품·규정 분류를 추측하지 않는다. 검토된 제품/규정/방법 값이 명백히 다른 경우만 해당 조건의 불일치로 제외한다. 상충 값 안에 질의와 같은 값이 있거나 미확인이면 검토 대상으로 남기고 상태를 명시한다. 모델만 다른 사례는 related_model로 남길 수 있으나 exact 모델로 바꾸지 않는다. 조건 없음/자료 없음은 확인된 일치로 표시하지 않는다.

결과의 각 제공 조건은 matched/conflicting/unconfirmed/mismatched/not_requested를 구분하고, 검토된 원값·claim/문서/SHA/page/line 참조와 기존 search의 진행 후보 부적격 사유를 별도로 담는다. out_of_scope/pending/partial/conflicting 사례도 검토 조회로 보존하되 적격·규정/기관 승인·현재 제품 지원을 부여하지 않는다. source status/basis·0/false/null·누락/미검토와 권리를 유지한다.

kind는 `fcc_report_case_discovery`로 분리한다. 정확 DTO/정렬·중복·개수/JSON/출력 예산·고정 오류는 owner usage에 완전하게 제시하고 총괄 고정 뒤 RED→GREEN을 진행한다. 생성 완료 인덱스만 사용하고 새 파일/네트워크/PDF/SDK/모델 호출은0이다. 원본 body·수치·비공개 경로를 공개 fixture/Git에 넣지 않는다.

수용은 기존021 회귀·동등 literal/판본차이·부분질의·상충/미확인·related 모델·결과 사본/예산, 실제 S03두 사례와S05상충1 사례를 포함한다. S05는 discovery에서 검토 근거가 보이고 기존 search는 계속후보0이어야 한다. source fingerprints/실패/부모 producer가 불변이어야 하며022 분할/025 응답의 권한을 자동 확대하지 않는다.023 재검토 지적이 오면 그 독립 재검토를 우선한다.
