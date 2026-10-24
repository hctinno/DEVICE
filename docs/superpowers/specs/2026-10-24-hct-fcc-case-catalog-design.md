# HCT FCC 사례 조회 021 / 읽기 화면 024 설계

2026-10-24, Asia/Seoul. 사용자 신규 corpus 지시를 작은 실행 단위로 연결한다. 범위·실제 수집 요청은 [요청012](../../material-intake/2026-10-24-hct-fcc-corpus-request.md), 기존 목표·구조는 [PLAN](../../../PLAN.md), [IMPLEMENTATION](../../../IMPLEMENTATION.md), [DESIGN](../../../DESIGN.md)를 따른다. 기존 개발/수집을 취소하지 않고 각 소유 단위 뒤 새 전용 branch에서 작업한다.

## 첫 단위와 소유권

개발1 `FCC-CASE-CATALOG-021`: 새 `labflow/fcc_report_cases.py`, `tests/test_fcc_report_cases.py`, `docs/fcc/fcc_report_cases_usage.md` 3파일. 기존 `document_extract.extract_document/page_citation`를 재사용하는 private 검수 packet의 읽기 전용 메모리 인덱스, 원본·페이지 근거 조회, 정확 조건 사례 검색, 기존 접수 projection의 사례 연결을 구현한다. Store/schema/원본/기존 추출기 변경은 없다. 첫 준비된 P01 배치를 private에서 실제 입력해 검증하고 전체 수집 완료를 기다리지 않는다.

개발4 `FCC-CASE-VIEW-024`: 새 `frontend/fcc_cases/model.mjs`, `view.mjs`, `model.test.mjs`, `browser_check.cjs`, `docs/fcc/fcc_case_view_usage.md` 5파일. 021의 `summary/case` 공개 DTO를 검증하는 읽기 구성요소와 실제 producer JSON→자기 loopback GET→DOM 검증 도구를 구현한다. 기존 HTTP 서버/장비·DUT/접수 화면은 이 단위에서 수정하지 않는다. 실제 자료 연결 전의 fixture 검사는 contract-only로 구분한다. 실제 021 준비 후 같은 도구로 private 실제 DTO를 연결한다. 물리 PDF 경로·원본 파일은 브라우저에 제공하지 않는다.

총괄은 공통 계약·private P01 패킷 인수/변환·독립 리뷰·통합/회귀·게시를 맡는다. 원본/추출 본문/실측값은 private에 두며 공개 Git의 테스트는 명시적 합성 PDF/사례만 사용한다. 개발1/4 usage의 완전한 키·유형·예산·오류 계약을 총괄이 대조한 뒤 RED→GREEN을 진행한다. 아래 의미를 약화하는 DTO 변경은 총괄과 먼저 조율한다.

## 입력과 출처 경계

`FccReportCaseCatalog(packet, pdf_sources)`를 기본 API로 한다. 입력은 순수 JSON 호환 검수 packet과 `{원본SHA: bytes}`다. 이 API는 파일 경로/네트워크/SDK/OCR/외부 모델/데이터베이스 writer/콜백을 받지 않는다. caller가 private 원본과 packet을 보존한다. 객체는 입력/출력 모두 detached이고 생성 후 질의는 I/O를 하지 않는다. JSON은 중복 키·NaN/Infinity·bool 정수·사용자 객체·깊이/총량 초과를 거절한다. JSON text helper가 있으면 같은 strict decoder를 사용한다. 원본은 bytes만 받으며 합계/개별 크기·문서/사례/claim 수·추출 페이지/내용 예산을 usage에 고정한다. 파서 작업 예산은 기존 추출기의 cooperative 한계이며 OS 격리/hard timeout으로 주장하지 않는다.

packet의 정확 top-level은 `schema_version`, `corpus_id`, `scope`, `searches`, `documents`, `cases` 6개다. schema_version은 정수1이다. scope는 시작 발행일/실제 +09:00 마감/Asia-Seoul/모집단 미확인·검색 범위의 불확실성을 담는다. 공식 검색 실패를 공식 확인으로 승격하지 않는다.

documents는 물리 고유 SHA와 파일 메타데이터, 공개 경로/열람 시각/source_kind(official/mirror/existing_user), official 대응 상태, 권리 상태를 담는다. URL은 HTTP(S) 문헌 링크일 뿐 자동 열람하지 않는다. 같은 SHA의 여러 등재 관계는 별도 exhibit 관계로 보존하며 고유 PDF 수와 등재 수를 분리한다. 원본 bytes의 SHA/크기/PDF signature/strict 파싱 가능 상태/물리 페이지 수를 실제 검사한다. HTML·깨진 PDF는 확보 완료로 받아들이지 않는다. 기존 추출기가 partial/이미지 페이지를 보고하면 상태를 보존하고 해당 페이지 근거를 성공으로 만들지 않는다.

cases는 `case_id`, `report_group_id`, `document_ids`, `claims`, `relations`, `reuse_group_ids` 6키다. report_group_id는 검수자가 확인한 보고서 계열이며 개정/부분번호를 제거하는 추측 regex로 생성하지 않는다. 미확인이면 null이고 독립 평가 적격이 아니다. relations는 개정/분할/부록/등재 관계 및 unresolved 외부 대상을 보존한다.

claim은 `claim_id`, `field`, `value`, `unit`, `status`, `basis`, `evidence` 7키다. field는 report/issuer/product/method/setting/equipment/correction/result/normative 네임스페이스를 구분한다. status는 reviewed/extracted/not_reported/extraction_failed/ambiguous/conflicting, basis는 report_fact/government_rule/guidance/standard_reference_only/developer_inference/synthetic_policy다. 공백 value는 null이며 미기재·실패를 0/빈 문자열 기본값으로 채우지 않는다. reviewed는 제공 검수의 상태이며 API의 literal 검증이 과학/법률/기관 진위를 새로 인증하는 것은 아니다. 결과값과 표 구조·조건은 분리된 claim과 위치/단위로 보존한다.

evidence는 원본 document_id/SHA, 1-based 파일 페이지, 인쇄 페이지(unknown 허용), 표/행/열/각주 위치, retained text hash·line_start/end·quote를 담는다. `page_citation`으로 실제 같은 SHA·페이지의 retained literal을 확인한다. 다른 페이지/개정의 값·변조된 hash·범위를 거절한다. 구조화 값은 인용과 검수자의 해석을 구분하며 단위 환산·판정·법령 요구를 API가 추측하지 않는다. 추출 이미지·곡선은 native raw가 아니다.

## 조회와 접수 연결

API는 `summary()`, `case(case_id)`, `search(query)`, `match_intake(projected_summary, query)`로 고정한다. 완전한 DTO 키/유형/오류를 개발1 usage에서 먼저 명시하고 개발4와 공유한다. summary/case/matches kind는 각각 `fcc_report_case_summary`, `fcc_report_case`, `fcc_report_case_matches`다. 모든 wrapper에 검증 범위를 담고 실행모드는 report_derived, hardware/physical/model execution verified는 false다. 요약은 원본 확보/추출/검토/규정대조/개발반영/평가를 혼합 완료율로 표시하지 않는다.

case preview는 case_id/보고서번호/개정/기관분류/발행일·범위상태/FCC IDs/제품군·제조사·모델/규정·방법 참조/검토상태/문서IDs를 반환한다. 국내 HCT와 America, 기관 불명을 분리한다. 기관 분류에는 검토된 법인명·주소의 페이지 근거가 필요하며 본문 HCT 문자열 출현만으로 포함하지 않는다. 보고서 필드의 충돌·추출만 된 상태·발행일 미확인은 unknown/pending으로 보존한다. 미래/기간 밖 발행은 조회 목록에서 제외 여부를 별도 상태로 나타낸다.

search query의 정확 키는 `product_family`, `rule`, `method`, `model`이며 각 string 또는 null이다. 관련성 판정에 제품군·rule·정확 방법/판본 3개가 필요하며 부족하면 insufficient_evidence다. 비교는 trim/casefold 수준의 literal 일치이며 판본 대체·모든 제품의 스마트폰/FCC 분류는 하지 않는다. model이 있으면 정확 모델 후보와 같은 제품군 사례를 구분하며 다른 모델을 일치 제품 증거로 반환하지 않는다. 반환은 검토할 사례 후보이지 실행 권한·현재 모델 지원·보편 시험조건이 아니다.

match_intake는 이미 기존 접수에서 만들어진 projection을 읽기만 한다. product_type/market/model의 명시 또는 user_confirmed 사실만 사용하고, caller query의 제품군/모델과 불일치하면 insufficient_evidence다. market이 명시적 미국/FCC 범위가 아니면 FCC를 가정하지 않는다. 접수 질문·승인·current generation·Store를 수정하지 않는다. fixture 입력과 실제 접수 연결 검증은 분리한다.

case별 평가 유출 방지 키는 제품군, FCC IDs, report_group_id, 원본SHA, reuse_group_ids에서 만든다. 미기재/미확인 그룹을 새 독립 그룹으로 꾸미지 않는다. 다음 개발2 단위는 관계의 연결 성분 전체를 train/development와 independent evaluation 중 한쪽에만 배정하고 duplicate/group overlap을 거절한다. 이 단계에는 모델 호출·학습·평가 점수 생성이 없다.

## 읽기 화면과 수용 검사

개발4는 기관/제품군/방법·판본/장비·페이지·규정 대조 상태를 원문 hash/파일 페이지와 함께 탐색하게 한다. 후보/다운로드/파싱/추출/검토/규정대조/개발연결·미확보를 구분하고 모집단 미확인·공식 접근 실패·rights를 보인다. 결과·과거 교정을 현재 측정/교정으로 올리지 않는다. unknown/null/ambiguous/conflicting은 명시하고 미지원/실패를 녹색 성공으로 표시하지 않는다. private quote는 textContent로만 표시하고 HTML/unsafe URL/원본 경로/비허용 필드는 삽입하지 않는다. last good DOM/선택·늦은 응답/키보드 초점/390px을 검사한다.

개발1은 합성 PDF의 정상/개정/분할/같은SHA다중등재/잘못된페이지/단위·날짜충돌/HTML·malformed·image/partial/입력변조/깊이·용량/접수부족·다른제품·다른판본을 검사한다. 실제 P01 B001에는 SHA/크기·물리 페이지·대표 페이지 literal·조회/검색·접수 일치/거절과 원본 불변을 별도 실행한다. 024 실제 producer→GET→DOM은 contract-only와 분리한다. 기존 장비 DB/64프로필·DUT pin·Store는 불변이다. 전체 기능·규정 적합·RF 물리·실제 AI 검증 완료를 주장하지 않는다.
