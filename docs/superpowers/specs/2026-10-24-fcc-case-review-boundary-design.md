# FCC 사례 AI 문맥·응답 경계025 설계

2026-10-24, Asia/Seoul. [021 사례 계약](2026-10-24-hct-fcc-case-catalog-design.md)과 [022 평가 그룹](2026-10-24-fcc-case-evaluation-groups-design.md), [요청012](../../material-intake/2026-10-24-hct-fcc-corpus-request.md)을 잇는 작은 단위다. 사용자 상시 위임에 따라 총괄이 기존 prompt/strict-response 방식을 선택했다. 새 범용 에이전트 프레임워크나 모델 클라이언트를 만들지 않는다.

## 소유권과 목적

개발2 신규 `labflow/fcc_case_review.py`, `tests/test_fcc_case_review.py`, `docs/fcc/fcc_case_review_usage.md` 3파일, 전용 `codex/dev2-fcc-case-review025-20261024`다. 기존022 branch/원격 커밋/실제 metadata 실패와 성공을 보존한다. 다른 개발자의021/023/024 및 기존 Store/추출기/장비/하네스의 소스는 수정하지 않는다.

021 검수 catalog와 caller의 명시 query/사례 선택으로 AI가 참조할 bounded private 문맥을 만들고, 응답에서 선택한 사례/claim/원본 SHA/페이지가 그 문맥의 검토된 근거와 정확히 같은지 검사한다. 실제 AI 호출·외부 송신·모델 평가·학습·장비 실행 권한을 이 경계가 생성하지 않는다. 접수 제품·시장·판본을 기본값으로 채우지 않는다.

## 계약 고정

021 `FccReportCaseCatalog`의 summary/search/case 읽기 결과를 사용한다. API는 파일 경로·PDF bytes·Store·SDK·네트워크·사용자 callback을 받지 않는다. 생성 뒤 검수 PDF 재열람 없이 조회한 자료만 쓴다. 모델용 문맥과 모델 응답 decoder를 분리하고 기존 `intake_model_boundary`의 단순한 JSON/prompt/response 패턴을 참고한다.

개발2는 구현 전 usage에 API signature·정확 키/enum/오류·context identity 계산·JSON 크기/깊이/노드·선택/claim/인용 수·반환 예산을 완전하게 제시한다. 총괄은 작은 계약의 일관성만 빠르게 고정한 뒤 즉시 RED→GREEN을 진행시킨다. 선행021이 준비되면 exact 소유 커밋을 명시 인수하며 작성 중 파일을 완료 기준으로 사용하지 않는다.

query의 제품군·규정·방법/판본·모델은021의 문자 그대로 비교한다. 선택 사례는 명시 query의 실제 후보에 포함되어야 하고 문맥 상한보다 많으면 좁히도록 반환한다. 검색 후보가 없거나 근거가 partial/conflicting이면 이를 유지한다. 0/false는 원값이며 null/unknown/미검토를 사실로 승격하지 않는다. 인용은 case/claim/document/SHA/파일페이지/text hash/line과 결합하며 다른 사례·문서·판본의 출처를 혼합하지 않는다.

reviewed 상태라도 basis·literal 검증·citable 여부와 parser 한계를 보존한다. 원문 사실·규정/가이드·표준 번호 참조·개발자 추론을 별도로 표시하며 structured value의 의미·기관 진위·규정 충족·현재 제품 지원은 새로 인증하지 않는다. 제공된 문맥과 응답의 참조 일치만 검사하고 모델 문장의 과학적 정확도/성능을 검증했다고 주장하지 않는다.

응답은 strict JSON의 고정 선택/판정·근거 참조만 허용한다. 없는 ID, 다른 context identity, 허용하지 않은 claim·SHA·페이지, 과도한 JSON/중복 키/nonfinite/타입 오류는 고정 오류로 거절하고 원문·private 주소를 오류에 넣지 않는다. 입력/결과는 detached다. 외부 모델을 실행하지 않은 합성 응답은 fixture 검증이며 실제 모델 추론으로 세지 않는다.

022의 성분/평가 적격·fold/score를025가 추측하거나 자동 배정하지 않는다. 실제 S03의 같은 FCC 성분·canonical family/reuse 미확인/전체 미배정 상태는 유지한다. SAR/HAC를 §15.247 사례로 강제하지 않는다.

## 수용 조건

계약 고정 보완: 정확021 class/type와 공식 읽기 API·DTO 검증만 사용하며 하위 helper/code 교체 방어 프레임워크를 추가하지 않는다. 실제 검증은 caller가 private packet/원문 bytes로 정식021 객체를 먼저 구성하고 그 준비단계의 PDF 읽기와025 API 자체 I/O0을 별도 계상한다. private state/method를 만들어 실제 catalog로 가장하지 않는다. `selected`는 근거 참조 선택 상태이며 사례 전체 승인·규범/모델 품질 승인이 아니다.

합성 문맥/정상 응답·후보 없음·판본/제품 불일치·미검토/partial·출처 혼합·잘못된 문맥/참조·JSON/예산·사본 불변을 RED→GREEN으로 검증한다. 실제021 B001은 private에서 두 사례·페이지 한계가 유지되는 문맥 생성/합성 응답 decoding만 별도 실행한다. 원본과 source fingerprints가 불변이고 외부 송신·모델·학습·평가/실물0이어야 한다. 소유 커밋/푸시·원격 대조 후 독립 리뷰/수정, 총괄 실제 통합/회귀/게시와 다음 배정으로 이어간다.
