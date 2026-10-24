# DUT-CATALOG-DELTA-015 실행 계획

[고정 설계](../specs/2026-10-24-dut-manufacturer-delta-design.md)를 따른다. 개발3 MAX014의 독립 Yes·기존 source/PSD/DUT/branch/실패 증거를 보존한다.

1. 총괄의 새 입력/정확 pin·기존 두 pin·reference map을 읽고 전용 branch와 신규3파일 소유권을 ACK한다. usage/10키 두 DTO·오류3개를 먼저 고정한다.
2. 누락 모듈 RED 후 기존 catalog composition·고정 metadata read·snapshot/delta 분리·관계/형식·오류/무I/O·detached 조회를 구현한다.
3. 정상6/22·원래9/new6/null3 및 손상/드리프트·부모 관계·권리/지원 flags·optional file 변형/경계의 의미 있는 검사, 관련 회귀/문서 무결성을 확인한다.
4. 실제 고정 metadata API 결과와 fixture를 구분해 증거/전후 SHA를 보존하고 소유3파일 commit/push/원격 SHA를 전달한다. 독립 지적은 owner fix 후 재검증하고 총괄 통합/다음 배정으로 이어간다.
