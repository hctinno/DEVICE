# FCC 사례 평가 그룹 022 실행 계획

[설계](../specs/2026-10-24-fcc-case-evaluation-groups-design.md)에 따라 개발2가 신규3파일만 구현한다.

1. HARNESS016 완료 branch/7d8968a·실패·검증 증거를 보존하고 새 전용 branch를 만든다. 최종 독립 코드 리뷰는 총괄이 병행한다.
2. usage의 exact input/output·예산·고정 오류와 공개 그룹/미배정/부적격 의미를 먼저 고정한다. 총괄의 빠른 계약 검토 후 missing module과 실제 유출 경계를 RED로 남긴다.
3. 전체 입력의 namespace별 key를 union하고 deterministic connected components/eligibility를 계산한다. 분할 요청의 전체성/비중첩을 검증하고 detached DTO를 반환한다. I/O/모델·원본 body·기존 구현 변경은 없다.
4. 의미 있는 그룹/전이/미확인/중복·부분선택·타입/예산 검사와 실패·수정을 보존한다. P01 첫 준비된 group 대장은 private로 실제 실행하며 합성·실제 메타데이터 검증과 실제 AI 평가를 구분한다.
5. 자기 소유 커밋/푸시·원격 대조 후 총괄에 SHA/증거를 보낸다. 총괄 독립 리뷰/소유 수정→통합/회귀·문서/링크·원격 게시 후 다음 bounded 근거검색/하네스 연결을 배정한다.
