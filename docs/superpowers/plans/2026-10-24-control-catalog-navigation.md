# 카탈로그 링크·이력 구현 계획

2026-10-24 · Asia/Seoul. [고정 범위](../specs/2026-10-24-control-catalog-navigation-design.md)를 개발4가 실행한다.

1. UI001의 독립 리뷰 수정/소유 게시를 우선한다. 완료 branch/미커밋을 보존한 새 전용 branch에서 URL상태 parser/encoding·불량링크 RED를 만든다.
2. 기존 DOM/DTO/세대 guard를 보존해 fragment와 history·새로고침 복원을 구현한다. 기존HTTP는 바꾸지 않는다.
3. 실제API→GET→선택·reload/back/forward·늦은응답·모바일/keyboard 회귀를 새증거로 확인한다. Node와 actual 검사 수를 구별한다.
4. 소유파일만 커밋/푸시→독립 리뷰 수정→root 통합/검증·게시와 다음 실제 UI 구현을 이어간다.
