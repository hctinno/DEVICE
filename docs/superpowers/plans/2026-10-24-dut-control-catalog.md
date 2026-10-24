# DUT 출처·경로 조회 실행 계획

2026-10-24 · Asia/Seoul. [고정 설계](../specs/2026-10-24-dut-control-catalog-design.md)의 입력/조회 범위를 개발3 신규3파일에서 실행한다.

1. 총괄 입력 커밋을 exact fetch하고 전용 branch를 만든다. 이전 PSD/METER 완료 branch·증거를 보존하며 두 입력의 LF SHA를 확인한다.
2. usage에 최소 API/정확 DTO·고정 오류를 동결하고 의미 있는 source/경로·출처/지원 분리·실패/불변/무I/O RED를 만든다.
3. stdlib 고정파일 snapshot 조회만 구현한다. 실제 현재 입력→API 결과와 source/DB/프로필 전후불변을 기록한다.
4. 자기/장비catalog 관련 검사·문서검사·소유 커밋/푸시→독립 리뷰·소유수정→총괄 통합/검증/게시로 이어간다.
