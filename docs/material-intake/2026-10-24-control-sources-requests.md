# DEV-CONTROL-SOURCES-008 실제 수집 요청

2026-10-24 · Asia/Seoul. 사용자 지정 인계 MAIN-PROMPT를 읽고 기존 P01 한 창구에 **실제 전달**했다. [제어자료 카탈로그](../../control_sources/README.md)와 [어댑터 계획](../fcc/control_adapter_roadmap.md)을 개발 기준으로 사용한다. 이 문서는 보조대화의 미발송 초안과 구별되는 총괄 발송 기록이다. 수집1~8 배정·검수·게시와 공유 Git은 P01이 유지한다.

| 하위 ID | 우선 | 실제 요청·완료 조건 |
|---|---|---|
| CTRL-001 | P0 | N1911A/N1914A 각각 공식 Programming Guide·IVI 배포/지원표·센서 조합·권리/고정 버전·해시. 명령·단위·보정·완료/오류에 판본/페이지 연결 |
| CTRL-002 | P0 | N9030A X-Series IVI·모드/FW/옵션과 FSV40 정확 모델 드라이버/SCPI. 기존 TRACE007 두 패킷12행 재사용, N9030B/FSW 자동 대체 금지 |
| CTRL-003 | P0 | RsInstrument/필요 모델 드라이버, Keysight MCP1.1/Mock/IDF/IOLS, PyVISA-sim의 고정 배포·권리·의존성. OS/버스/승인·unchecked·오류·재시작/Simulation 범위 |
| CTRL-004 | P1 | E3632A python-ivi exact/계열·LICENSE/deps/공식 IVI. KEITHLEY DMM6500 tm_devices/PyMeasure/조건부 샘플의 경로·권리·기능 분리 |
| CTRL-005 | P1 | CO3000/2090 controller·축/정지/한계, SU-642 설치controller/공개통신option, 맞춤 RF스위치 port/기존SW. 공개 근거와 현장 unknown 구별 |
| CTRL-006 | 대응 공백 | 프로필의 다른제조사 같은모델9/직접후보없음18을 기존 성적서·장비master·보유자료부터 검토. 별칭/다중후보/파생프로필 보존 |

008 범위의 공개 자료 조사·다운로드를 요청했으며 설치·바이너리 실행·장비 discovery/실물 운전·외부 계정/구매는 요청하지 않았다. TRACE007 자체의 신규 원문/네트워크/실물 예산0과 동결본은 그대로 유지한다. 모델별 `kind/authority/match_level/access/license/evidence/notes`와 버전/커밋·해시를 보존한 작은 패킷을 P0부터 받는다. 공개 미발견502항목 전체를 첫 실증의 차단조건으로 만들지 않는다. 현재 사용자 추가 준비/결정0이다.

## TRACE007 실제 인수와 ACK

준비된 두 패킷을 독립 clone의 `.local/a176u/collection/DEV-ANALYZER-TRACE-007-EVIDENCE/`에 비공개 복사했다. 첫 색인 2747B SHA-256 `38a4a7075dc42d0613bd3a53a6cebda4b5a115c5b4f77875219582111378bd1d`, S02 후속 3216B `30e10c6fe5193d2d90267193f8fd6e251f22fc2fe4a10952d2cc4549b83e1bb6`이다. 총21metadata/183498B의 SHA·bytes·UTF-8 JSON과 합계 등록부12행/4프로필을 확인하고 P01에 실제 ACK했다. 원문 payload·신규 원본·실물/OEM 실행·총괄 공유 쓰기0이다.

N9030A 고정 매뉴얼의 Sample bucket 중심과 FSV의 point 내 마지막값 정의를 합치지 않는다. FSV Spectrum point 범위101..32001/reset691과 표시 설명691을 구별한다. HP호환·VB버퍼·파일 export·I/Q 예제를 일반 amplitude trace의 포맷·길이·순서 근거로 쓰지 않는다. 선형grid/revision/stale/cancel은 별도 선언 합성 정책이며 현재 FW/옵션·실제 축/끝점·정규화·취소 후 값·native byte order는 미확인으로 남긴다. 이 근거 검수는 제품 Mock나 실장비 검증이 아니다.
