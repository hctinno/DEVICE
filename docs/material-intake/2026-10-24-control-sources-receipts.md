# CTRL008 준비 자료의 개발 인수

2026-10-24 · Asia/Seoul. [실제 수집 요청](2026-10-24-control-sources-requests.md)에 따라 P01이 검수·동결한 자료를 독립 개발 clone에 비공개 인수한다. 원문·소스/권리·재사용 실행·장비 지원은 따로 기록하며 기존 [고정 카탈로그](../../control_sources/README.md)의 출처 속성을 덮어쓰지 않는다.

| 패킷 | 색인 SHA-256 / bytes | 독립 인수 검증 |
|---|---|---|
| S04-B0009-v1 / CTRL001 | `9280086206ee62863d8132a7673030a8529d2e95787a14e47060573c91eb58d6` /3815 |16payload/744792B, JSON12개 UTF-8·SHA·bytes PASS |
| S06-B0005-v1 / CTRL005 | `4119966f2be60a476a5d892acc09cfbdaf3a0fb8a058e54808eba7879c72a844` /3789 |16payload/661080B, JSON14개 UTF-8·SHA·bytes PASS |
| S07-B0006-v1 / CTRL003 | `b6f3575d2a50b99abf73a351daed2c4662ace102df265eaef8c7d152cb1c4798` /4213 |18payload/885113B, JSON16개·ZIP2개 CRC/완전 MIT 허가문·31member/66line hash PASS |

첫 두 패킷32payload/1405872B를 `.local/a176u/collection/DEV-CONTROL-SOURCES-008/`의 새 디렉터리에 사본화했다. 권리 검수 조건의 비공개 자료이며 공개 원본/코드 재배포·import/실행·실물·공유 폴더 쓰기0이다. DB 전후 SHA는 `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`로 같다. P01에 실제 ACK했고 개발3에 CTRL001의 읽기 경로·검수 한계와 구현 반영을 전달했다.

전력계는 N1911A P-Series/N1914A EPM의7영역씩14영역·45근거다. 기존5가이드와41개 근거 위치는 재사용했으며 새 원문1개는 IVI1.2.3.0 소개 HTML이다. 실제 IVI Readme/package/EULA/NOTICE는 확보하지 않았다. measurement window와 물리 input, FETCh/READ/MEASure·relative/ratio 단위, 센서/보정·OPC 완료와 CAL 성공/새 유효 데이터/추적 교정을 나눈다. CAL:ALL?가 절차를 시작한다는 이유로 현재 조회 subset에 추가하지 않는다. N1921A 호스트·교정 관계를 보존하고 N1914A 호환·독립 endpoint를 승인하지 않는다.

시설 자료는8의존 범위·17근거·16기존프로필을 보존했다. 2090 April2006 RevG의 공개 미러 HTML1..100/178쪽만 확보했고 실제 설치주소·축·한계/정지·FW를 확정하지 않았다. RsOsp2.10.17.75는 OSP2xx/3xx용 정적 소스이며 OSP120 적용·완전 권리문 확보로 세지 않는다. 경로 손상 질문은 P01의 원본 SHA/UTF-8/codepoint 대조에서 오탐으로 처분됐다. 동결 질문을 그대로 보존하고 검수 정정을 함께 인수했다.

이 인수는 문서 근거와 bytes 대조이며 실제 SDK/제품 Simulation 실행이나 장비 기능 검증이 아니다. 개발1 catalog API/개발4 화면과 개발3 기존 N1914A subset 연결을 계속한다. 준비된 고정 SDK 소스는 아래 후속 인수처럼 SDK-SIM-006에 연결하며 현재 새 사용자 준비 요청0이다.

후속 S07까지 합계50payload/2290985B·JSON42개를 비공개 인수했다. RsInstrument 고정 commit `b600fd6cf693dbcfa3cbfba0f638dfa14ff2c0aa`의 ZIP SHA는 `01eaa9b33bf047ae420ee49280fe74addecd98ad4e04456919c08ca0dd100649`, PyVISA-sim0.7.0 commit `f7af67e299ccdc95ccfccbe9edcb7490aa189d6f`은 `7fc2bc8cd2392fa33295da94253b86e9119ef9ab2140693ac2f9aa83302cfc51`이다. 두 ZIP CRC·루트 MIT 허가/고지문과 실제31개 member SHA/66개 line-range SHA를 직접 대조했다. 70개 표기는 동결자료를 바꾸지 않고 P01 정정으로 인수했다.

자료·소스 정적 대조 후 개발2에 실제 SDK-SIM-006 구현 입력을 전달했다. Python package1.131.0과 README build1.131.0.128을 구별한다. 의존성 선언은 설치된 lock이 아니며 private 환경에서 개별 배포·권리/해시를 고정한 후 실행한다. PyVISA-sim의 동적 SCM version/생성 version.py 부재는 빌드 미검증으로 남기고 이번 R&S 결과로 대체하지 않는다. 캐시·기본 OPC/error·같은 backend close/open은 실제 RF 유효성·프로세스 재시작 복구가 아니다. 총괄 인수 단계의 설치·archive 추출·source import/실행은0이다.
