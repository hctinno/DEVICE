# 사례021의 선택 페이지 읽기030 설계

2026-10-24, Asia/Seoul. [기존021 계약](2026-10-24-hct-fcc-case-catalog-design.md)과 [028 discovery](2026-10-24-fcc-case-discovery-design.md)를 유지한다. 총괄은 개발1 설계안15559B/SHA `f6ce278b66752c3c627f9ec2a398e2834cf0f5bcda7b94221444444da4280b59` 전체를 읽고 권장 A를 고정했다. private 원바이트 사본은 개발 배정 대장에 보존한다.

개발1은 완료028 `1fae206e9fcda717d2d06eb74e45cdcf6d37da63`에서 전용 `codex/dev1-page-scope030-20261024`를 만들고 기존 소유3파일 `labflow/fcc_report_cases.py`, `tests/test_fcc_report_cases.py`, `docs/fcc/fcc_report_cases_usage.md`만 변경한다. shared extractor·023/024·Store·DB·수집 원본은 변경하지 않는다.

## 입력과 읽기 범위

`FccReportCaseCatalog(packet, pdf_sources, *, page_scope=None)`와 `from_json(packet_json, pdf_sources, *, page_scope=None)`를 쓴다. None은 기존 경로/동작/producer 원바이트와 같아야 한다. 별도 factory·reader callback·주입된 retained 결과는 추가하지 않는다. 명시 policy는 정확 plain JSON이며 top2키 `schema_version=1`, `sources`다. sources는 원본 SHA key집합과 정확 대응하며 누락 source의 전체 추출 fallback을 금지한다. 빈 corpus만 sources={}를 허용한다.

source entry의 정확4키는 `pages`, `mode`, `basis_id`, `basis_sha256`다. pages는 고유한 양의 정수/1기반·source당1..200개·원래 physical_pages 이내이며 bool/중복/빈 배열을 거절하고 입력을 바꾸지 않은 오름차순 사본을 사용한다. mode는 `native_text|accessibility`, basis ID는 기존 ASCII ID 문법128자 이내, basis SHA는 소문자64hex다. basis는 이미 검토된 범위의 추적 참조이며 API가 외부 권한/라이선스를 인증·발급하지 않는다.

policy64KiB/depth6/node4096, source16/선택페이지총800, 기존 PDF source16MiB/총64MiB·retained문자 source100만/총400만·선택 content8MiB 한도를 지킨다. 모든 policy·source/range·합계 예산을 native content 처리 전에 검사한다. 전체 파일 SHA/크기/strict 구조 및 내용에 접근하지 않는 page-tree leaf 수와 packet·Count의 일치는 검증한다. 암호화 PDF의 `/Count`만 물리쪽 수의 증거로 삼지 않는다. 필요한 pinned reader 구조가 없거나 모호하면 실패로 남긴다. 협력적 예산을 OS 격리/강제 timeout으로 표시하지 않는다.

선택하지 않은 페이지에는 content stream/text/image decode/OCR/render를 실행하지 않는다. 전체 추출 뒤 필터하는 구현도 금지한다. 기존 공개출처 gate/빈 USER 암호 단1회/결과 USER1만 유지하며 secret/owner/private-only PDF 경로로 넓히지 않는다. 암호화 source는 permission integrity가 명시 True여야 하며 native_text는 EXTRACT16, accessibility는 EXTRACT_TEXT_AND_GRAPHICS512를 확인한다. print만으로 native 읽기를 허용하지 않고 copy=false·private/unknown 권리를 보존한다. 권리 플래그 수정·decrypted PDF 저장·본문 일괄 export·OCR 우회는 없다.

## 기존 출력과 실패 의미

새 DTO키/상태 enum/오류를 만들지 않는다. 선택하지 않은 페이지는 retained/page_index에서 생략하고 empty/error/hash 행을 꾸미지 않는다. total_pages는 전체 물리쪽 수, processed_pages는 실제 선택 페이지 시도 수이며 원래 비연속 file_page를 유지한다. 부분 선택이면 partial/complete=false, 실제 선택 페이지의 ok/image_only/no_text/truncated/error·파서/폼 리소스 누락과 citable 조건을 그대로 적용한다. index에 없는 근거는 invalid_evidence다.

고정 진단은 `page_scope_applied`, `page_scope_native_text` 또는 `page_scope_accessibility`, 요청 페이지마다 `page_scope_requested`, 부분 선택에만 `page_scope_outside_unprocessed`다. scope 진단은 실제 parser warning과 구별하고 그 자체로 정상 선택 페이지의 인용을 막지 않는다. parser 식별자는 설계안의 선택 읽기3종을 사용한다. basis private 경로/hash를 진단 문자열에 숨기거나 DTO키를 추가하지 않는다. 기존 summary12/case9/matches12/discovery11·document8/extraction6/page_index5·claim7/evidence13을 유지한다.

오류는 잘못된 policy→invalid_packet, 한도→limit_exceeded, SHA/크기→invalid_sources, strict 구조/물리쪽/암호 읽기 실패→pdf_invalid, mode/permission integrity/가용성 부족→extraction_unavailable, 미선택/미인용 근거→invalid_evidence로 기존 고정 오류를 사용한다. raw private 예외·암호·본문을 오류 문자열로 반환하지 않는다.

## 실제 수용과 추적

실제 preflight에서 최초 제안의 basis SHA와 인수 파일이 불일치해 native0으로 정지한 실패를 보존했다. 총괄이 고정 S04-B0011 index와 실제21823B `P01-independent-review-S04.json`·같은16쪽 검수 범위를 대조해 basis를 `c337cd7bb64f7c38e4368a248b07f7670d8b6ec1edc55018df256b6e68569f93`로 정정했다. 원래 제안/실패와 별도 정정 receipt를 보존하며 source·페이지 집합·mode·권리 범위를 넓히지 않는다. 실제 reader의 permission integrity/mode 검사는 여전히 필수다.

S04 EMC40쪽은 기존 P01 범위16쪽(2,3,5,6,8,9,11,14,15,16,17,18,19,22,23,40)만 accessibility로 검증한다. 실제 시도/retained/citable·원본 권리/변경 없음·범위 basis/정규 policy SHA는 caller private receipt에 남긴다. 남은24쪽 본문 미처리, 전체 의미 검토/기관·방법 승인0을 유지한다. actual reader가 범위를 수행할 수 없으면 실패/미실행으로 보고하고 성공을 만들지 않는다. 본문 일괄 JSON/복호 PDF는 쓰지 않는다.

S06 America는 기존 visual/display-list 검수와 text/OCR0을 유지한다. native scope를 새로 발급하거나 None/빈 pages/허구 hash로021에 넣지 않고 metadata+미실행 gap으로 보존한다. S03/S05 기존 producer의 원바이트 재생,023/024의 변경 없는 DTO 수용·미선택 근거 거절과 default126 회귀를 확인한다.

새 owner branch에서 RED→구현→전용/관련·실제 검증→독립 리뷰/수정→총괄015 이후 통합·회귀·개발 branch 게시 순서다. 실제 모델·학습·RF/기계·현장망·외부 제출/발송은 실행하지 않는다.
