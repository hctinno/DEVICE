# CONTROL-PACKET-002 — P01 제어자료 동결 패킷의 읽기 검증

2026-10-24 · Asia/Seoul. CTRL-CATALOG-001 게시 뒤 개발1의 다음 실제 구현이다. 기존 API·UI/자료 JSON을 바꾸지 않고 총괄의 반복 SHA/bytes/JSON 인수 검증을 작은 공용 도구로 옮긴다. 현재 catalog의 독립 리뷰 소유 수정이 생기면 먼저 처리한다.

개발1 소유 신규3파일: `labflow/control_packet_audit.py`, `tests/test_control_packet_audit.py`, `docs/fcc/control_packet_audit_usage.md`. Store/DB·복사/수입/공유 폴더·네트워크·SDK 실행은0이다.

```python
audit_control_packet(packet_dir, *, expected_index_sha256) -> dict
```

packet_dir는 신뢰된 host가 지정한 로컬 디렉터리이며 HTTP/문서 속 경로를 자동 실행하지 않는다. 고정 `intake-v1.json`의 실제 bytes SHA-256을 expected와 먼저 대조한다. 예상 hash는 소문자64hex다. index는 최대1MiB, strict UTF-8/유한 JSON/중복키 없음, request_id는 DEV-CONTROL-SOURCES-008, revision은 ASCII ID, files는1..128행의 path/bytes/sha256이다. bool을 정수로 받지 않는다. index의 source_code_executed/runtime_or_hardware_support_confirmed/public_export_allowed는 모두 정확한 false여야 한다. 기존 추가 관찰 metadata는 입력에서 보존하되 실행 권한·지원 판정으로 사용하지 않는다.

파일 경로는 packet 안의 상대 POSIX 경로만 허용한다. 절대경로/drive/ADS/역슬래시/빈 segment/`.`·`..`/중복경로와 Windows 예약 DOS device명을 거절하고 모든 payload가 regular file임을 open 전에 확인한다. 루트와 각 파일 조상의 symlink/junction/reparse를 확인해 밖으로 따라 읽지 않는다. 새 소프트웨어·HTML·압축 내부 명령을 실행하거나 추출하지 않는다. 파일당64MiB·총128MiB, JSON 파일당8MiB 이하다. 실제 stream bytes·크기·SHA를 대조하고 JSON은 strict UTF-8/유한/중복키 없는지 확인한다. 실패·원본을 수정하지 않는다. ZIP은 CRC를 검사하되 entry2000개/총해제크기128MiB/단일64MiB의 사전 한도로 무제한 해제를 피한다. TAR.GZ는 v1에서 SHA/bytes만 검사하고 ZIP CRC와 혼동하지 않는다. 압축 안의 symlink/경로도 추출하지 않으며 실제 source import0이다.

모든 파일 검증 뒤 index bytes/SHA를 다시 확인한다. 성공은 해당 읽기 시점의 대조이며 전체 파일시스템 원자 snapshot이나 미래 무변조 보증으로 표시하지 않는다. source 검수/권리·SDK 동작·장비 지원도 이 검사로 승인하지 않는다. 예외는 `ControlPacketAuditError(ValueError)`와 `.code`의 고정 오류만 반환하고 root/경로/본문/원시 예외를 공개하지 않는다.

정확한 성공 DTO·오류 코드는 개발1이 사용법에 고정해 총괄에게 전달한다. 최소 schema_version/kind/request_id/revision/index_sha256/payload_file_count/payload_bytes/json_file_count/ZIP CRC 검사수·상태/읽기검사범위/public_export_allowed=false/source_code_executed=false/hardware_verified=false/state_mutations=0을 담는다. 원문 본문/파일 경로·이름 목록/secret/serial은 반환하지 않는다. 반환 사본은 호출자 변경과 격리한다.

TDD로 정상 혼합 JSON/HTML/ZIP/TAR bytes·index와payload 변조·불완전/중복/비유한 JSON·cap·음수/bool크기·중복/탈출/reparse·CRC 실패·읽기 중 index 변경·에러정제를 RED→GREEN 확인한다. 총괄이 인수한 `.local/a176u/collection/DEV-CONTROL-SOURCES-008/` S04-B0009-v1/S06-B0005-v1/S07-B0006-v1은 private 실제 corpus로 읽기 검증하되 테스트 fixture에 원본을 복사하거나 게시하지 않는다. 각 패킷의 expected hash/bytes는 [인수 기록](../../material-intake/2026-10-24-control-sources-receipts.md)과 총괄 메시지를 따른다.

전용/기존 catalog 회귀·새 private corpus 결과·소스/공유 무변경을 확인한 뒤 자기3파일만 커밋·푸시한다. 독립 리뷰/소유수정·총괄 CLI/인수 접점 통합은 다음 작은 단위로 이어간다. 새로운 사용자 준비물0이다.
