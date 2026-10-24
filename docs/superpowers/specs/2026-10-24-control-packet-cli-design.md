# CONTROL-PACKET-CHECK-003 — 명시 패킷의 읽기 검증 CLI

2026-10-24 · Asia/Seoul. 개발1의 audit002 후보와 실패 기록을 보존하고 신규3파일 `labflow/control_packet_check.py`, `tests/test_control_packet_check.py`, `docs/fcc/control_packet_check_usage.md`에서 구현한다. audit002 독립 리뷰 수정이 우선이며 공통 `__main__`/Store/HTTP/카탈로그는 수정하지 않는다.

`python -B -m labflow.control_packet_check --packet-dir LOCAL_DIR --index-sha256 LOWERCASE_SHA256`를 고정한다. 두 옵션은 필수이며 각각 한 번만 허용한다. 약어·positionals·unknown·중복·빈 값은 거절한다. `--help`만 표준 사용법을 stdout에 출력하고 exit0이다. 공개 help에는 실제 사용자 경로를 넣지 않는다. caller가 인자로 준 문자열을 오류/usage/traceback에 되비추지 않는다.

성공은 기존 `audit_control_packet`의 검증된 summary19키만 한 줄 UTF-8 JSON으로 stdout에 출력하고 exit0/stderr공백이다. audit 고정 오류는 stdout공백/stderr 한 줄 `{"error":"<고정 audit code>"}`·exit1이다. 인자 오류는 stdout공백/stderr `{"error":"packet_cli_invalid_argument"}`·exit2, 예상 밖 Exception은 같은 형식의 `packet_cli_internal_error`·exit1이다. 원시 경로·명령 인자·예외·context·본문을 출력하지 않는다. `KeyboardInterrupt`는 `packet_cli_interrupted`·exit130으로 정제하고 성공 summary를 내지 않는다. `main(argv=None)->int`와 모듈 실행 경계를 제공한다.

입력 경로/예상 SHA를 audit에 명시 전달하고 예상값을 대상 index에서 자동 계산하지 않는다. 자동 선택/검색/복사/쓰기·압축 추출·SDK 설치/import·장비/네트워크·원문 출력·실행 권한 승격은 없다. `-B`로 자기 bytecode 생성을 억제한다. CLI는 원자 파일시스템 snapshot/권리·지원·계측·실물 검증이 아니다.

RED→GREEN으로 모듈 실제 subprocess 성공/각 실패 exit·stdout/stderr·중복/약어/미지정/한글·secret marker 비노출·입력파일 bytes/크기/mtime 불변을 확인한다. 합성 fixture를 공개 테스트에 쓰며 실제 private 패킷 검증은 별도 기록한다. 기존 audit33/catalog20 회귀와 문서 검사 후 자기3파일 커밋·푸시→독립 리뷰·소유수정→총괄 통합/검증·게시를 이어간다. 새 사용자 준비0이다.
