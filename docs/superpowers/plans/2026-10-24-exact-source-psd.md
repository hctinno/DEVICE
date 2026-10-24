# 정확 ratio PSD 실행 계획

2026-10-24 · Asia/Seoul. [고정 설계](../specs/2026-10-24-exact-source-psd-design.md)를 개발3 신규3파일에서 실행한다.

1. METER006 독립 리뷰 수정 우선, 완료 branch/미커밋 보존 후 새 전용 branch를 만든다. 현재 source/math API를 읽고 ratio→조건부비교 RED를 만든다.
2. 기존 정확 적분을 재사용하고 정수power5 비교/독립 Decimal 표시·context 불변을 구현한다. 세부 DTO/고정 오류는 usage에 고정한다.
3. 독립 oracle·경계/표시 반올림·실제 source→새결과 합성 연결과 기존source/math 회귀를 확인한다. 최대 탐색·물리/OEM 지원으로 승격하지 않는다.
4. 자기3파일 커밋·푸시→독립 리뷰 수정·총괄 통합/문서·검사·게시로 이어간다.
