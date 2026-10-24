# CONTROL-PACKET-PREPARE-004 — 검증된 패킷의 private 보존 복제

2026-10-24 · Asia/Seoul. 개발1 audit002/CLI003의 완료 branch와 RED·fix를 보존한다. 신규3파일은 `labflow/control_packet_prepare.py`, `tests/test_control_packet_prepare.py`, `docs/fcc/control_packet_prepare_usage.md`다. 기존 audit/CLI/Store·DB·공통 접수 흐름은 수정하지 않는다. CLI003 독립 지적 수정이 우선이다.

```python
prepare_control_packet(source_dir, *, expected_index_sha256, workspace_root, packet_id) -> dict
```

host는 허가된 **독립 개발 workspace_root**와 로컬 source_dir·별도 신뢰한 expected index SHA를 명시한다. API의 유일한 쓰기 범위는 workspace의 `.local/control-packets/{packet_id}/`다. packet_id는80자 이하 ASCII ID이며 drive/ADS/예약device·`.`/`..`·끝점/공백을 허용하지 않는다. UNC/장치 namespace·reparse/symlink/파일형식·source와 쓰기 범위의 조상/자손 겹침은 거절한다. 외부PC 절대경로를 하드코딩하지 않으며 공유 수집 루트는 host가 목적지로 지정하지 않는다.

audit API의 고정 CTRL008 계약/한도를 그대로 먼저 적용한다. 원래index를 strict 해석하고 listed payload와 index bytes만 새 목적지에 읽기 검증/stream hash로 복제한다. unlisted development receipt·원시 소스 import/설치·압축 추출/추가 다운로드/권리 승인·DB/네트워크·장비 연결은 없다. private 원문의 공개 export를 허용하지 않는다. 원본에 쓰거나 mtime·권한·이름을 변경하지 않는다.

목적지는 exclusive mkdir로 새로 소유하고 기존 목적지는 항상 고정 오류로 거절한다. 개별 파일도 exclusive 생성이며 overwrite/merge/삭제/자동 cleanup은 없다. 파일 open 전/후 정규파일·ancestor reparse/identity·실제 stream 크기/hash를 대조하고 마지막 source 재audit와 destination audit의 고정 summary가 같아야 완료 영수증을 게시한다. 동시 변경은 실패로 남기며 파일시스템 원자 snapshot을 주장하지 않는다.

초기 배정의 'atomic 게시'는 portable한 완료 경계로 구체화한다. 목적지 생성/복사만으로 완료가 아니며 **최종 `prepared-receipt.json`의 유효한 complete 상태**가 완료 표지다. 이 이름과 충돌하는 manifest는 복사 전에 거절한다. 완료 표지는 자기 임시파일에 UTF-8 JSON을 완성/flush한 뒤 자기 새 디렉터리 안에서 게시한다. 부분 사본·실패 stage는 private에 보존하고 완료 표지를 만들지 않는다. 다른 프로세스/사용자 파일을 지우거나 빈 기존 디렉터리를 rename으로 덮지 않는다. 준비 실패를 source·SDK·제품 비지원으로 바꾸지 않는다.

성공 DTO는 packet ID·private상대목적지·예상indexSHA·audit summary·complete/지원미평가·실물false/실행false만 허용한다. 원시 source절대경로·파일본문·serial·예외를 넣지 않는다. 정확 DTO와 `ControlPacketPrepareError(ValueError).code`의 고정 오류(인자/경로/기존목적지/검증실패/복사실패/원본변경/완료게시실패)는 owner usage에 먼저 동결한다. audit 오류를 원시 context로 노출하지 않는다. 사용자 권한/현장제어를 승인하는 함수가 아니다.

RED→GREEN으로 정상복제/index정확bytes·unlisted미수입·source bytes/크기/mtime불변·기존목적지/겹침/예약device/reparse거절·open중변조·짧은읽기/쓰기/중간실패·최종재검증실패·완료표지의게시실패/부분사본보존·고정오류비노출을 검증한다. 실제 private CTRL008 작은 패킷1개는 **별도 새 자기 clone `.local` 목적지**에 실행하고 원본/게시물 hash·실패/실행 범위를 기록한다. 자기/기존audit·CLI 회귀와 문서검사→소유3파일 커밋푸시→독립리뷰/소유수정→총괄통합/검증게시를 이어간다. 새 사용자 준비0이다.
