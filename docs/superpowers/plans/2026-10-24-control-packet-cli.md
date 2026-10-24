# 패킷 검증 CLI 실행 계획

2026-10-24 · Asia/Seoul. [고정 설계](../specs/2026-10-24-control-packet-cli-design.md)를 개발1 신규3파일에서 실행한다.

1. audit002 완료 branch/원격 SHA와 미커밋을 보존한 새 branch를 사용한다. 독립 리뷰 지적이 있으면 먼저 owner fix한다.
2. 실제 모듈 subprocess의 성공 JSON·인자/고정 audit/예상 밖/interrupt 실패·출력 비노출 RED를 만든다.
3. strict 옵션 파싱과 audit 호출만 구현하고 원본 불변·동작 범위를 검증한다. API DTO나 공통 CLI는 확장하지 않는다.
4. 자기/관련 검사·문서 검증→소유 커밋·푸시→독립 리뷰·수정→총괄 인수·현재 공통본 검증·게시로 이어간다.
