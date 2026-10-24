# 선택 페이지030 구현 계획

2026-10-24, Asia/Seoul. [고정 설계](../specs/2026-10-24-fcc-case-page-scope-design.md)를 개발1에게 실제 배정한다. 기존028/030 설계와 다른 owner의 작업을 보존한다.

1. 완료028에서 전용030 branch를 만들고 소유3파일만 사용한다. usage에 정확 signature/policy/keyset·예산·기존 오류·선택/미선택 상태·actual 수용 범위를 먼저 적는다.
2. keyword-only policy, 잘못된/누락 source·page/aggregate 예산·비연속 선택·외부 evidence 거절을 RED로 기록한다. default producer/기존126 검사는 기준선을 유지한다.
3. native 내용 처리 전 전체 SHA/strict page-tree leaf 수/모순 Count·scope·mode/permission integrity를 확인하는 선택 경로를 구현한다. 외부 페이지 content/text 연산 spy는 실행 페이지를 분명히 기록하며 일반 구조·권한 상태 검증에 한정한다.
4. 선택된 정상/빈/폼누락/오류·partial/count·page hash/원문 line 인용과 detached 사본을 검증한다. 기존 parser/None 경로·search/intake/discovery 의미를 유지한다.
5. S04 실제16쪽 범위만 읽고 bounded case 근거·caller receipt를 private에 보존한다. S06 metadata gap과 S03/S05 default byteequal,023/024 원래 consumer를 확인한다. 실제 미실행/미인용은 그대로 기록한다.
6. 관련 검사·UTF8/문서/AST·소유 diff를 검증하고 정확 commit/push/remote SHA·usage/source/receipt SHA를 총괄에 반환한다. 독립 리뷰 No는 owner가 RED/수정/재검증하고 총괄이 인수·통합·후속 배정을 맡는다.

합성 policy/fixture 검사를 실제 원문 성공·권리 허가·규정/계측 정확도·AI/실물 검증으로 합산하지 않는다. 개발/수집 원본에는 쓰지 않는다.
