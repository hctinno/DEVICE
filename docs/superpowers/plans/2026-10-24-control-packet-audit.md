# P01 제어자료 패킷 audit 실행 계획

2026-10-24 · Asia/Seoul. [고정 설계](../specs/2026-10-24-control-packet-audit-design.md)를 개발1 신규3파일에서 실제 구현한다.

1. catalog a65c09e의 독립 리뷰 수정이 있으면 우선한다. 완료 branch/미커밋을 보존한 새 전용 branch에서 audit의 정상/변조 RED를 만든다.
2. 고정 index SHA·strict JSON·상대 경로/읽기 한도·파일 stream hash·bounded ZIP CRC를 구현하고 오류/원문 보존 GREEN을 확인한다. 외부 코드 import·쓰기/자동복사는 없다.
3. S04/S06/S07 실제 private 동결 패킷을 읽기 검증하고 synthetic fixture 검사 수와 corpus 수를 구분해 기록한다.
4. usage의 정확 DTO/고정 오류와 private 증거/제한을 전달하고 자기3파일을 커밋·푸시한다. 독립 리뷰 수정·총괄 접점 통합/게시 후 다음 실제 구현을 이어간다.
