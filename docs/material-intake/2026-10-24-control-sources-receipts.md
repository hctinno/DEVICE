# CTRL008 준비 자료의 개발 인수

2026-10-24 · Asia/Seoul. [실제 수집 요청](2026-10-24-control-sources-requests.md)에 따라 P01이 검수·동결한 자료를 독립 개발 clone에 비공개 인수한다. 원문·소스/권리·재사용 실행·장비 지원은 따로 기록하며 기존 [고정 카탈로그](../../control_sources/README.md)의 출처 속성을 덮어쓰지 않는다.

| 패킷 | 색인 SHA-256 / bytes | 독립 인수 검증 |
|---|---|---|
| S04-B0009-v1 / CTRL001 | `9280086206ee62863d8132a7673030a8529d2e95787a14e47060573c91eb58d6` /3815 |16payload/744792B, JSON12개 UTF-8·SHA·bytes PASS |
| S06-B0005-v1 / CTRL005 | `4119966f2be60a476a5d892acc09cfbdaf3a0fb8a058e54808eba7879c72a844` /3789 |16payload/661080B, JSON14개 UTF-8·SHA·bytes PASS |
| S07-B0006-v1 / CTRL003 | `b6f3575d2a50b99abf73a351daed2c4662ace102df265eaef8c7d152cb1c4798` /4213 |18payload/885113B, JSON16개·ZIP2개 CRC/완전 MIT 허가문·31member/66line hash PASS |
| S02-B0005-v1 / CTRL002 | `fc4b047d5b08d16e94bf9cc67c0ea4bdab6c16e665227cb6255733bafb4db422` /3142 |12payload/1243358B, JSON9개·전 파일 SHA/bytes PASS |
| S08-B0009-v1 / CTRL003 | `7881ebf76b12d0697c09a07a8ffb8090868590ffe4b049e1cad57cc57e259e00` /2791 |10payload/104980B, JSON9개·전 파일 SHA/bytes PASS |
| S01-B0010-v1 / CTRL006 | `ec0a52b5dd07c216c158facd1c82d1dcbea8965c0131c8734a61597d5f9ec6e0` /3097 |12payload/290073B, JSON12개·전 파일 SHA/bytes PASS |
| S03-B0003-v1 / CTRL004 | `185d3f79f3069b163664b2a011cc55a0f7cdbb38801ed75b9e3d4206678c39b2` /5006 |23payload/268123B, JSON16개·전 파일 SHA/bytes PASS |
| S05-B0003-v1 / CTRL004 | `45d686441bdb072e462730e271bddcad0061a65dbd46e1f588885b86fc980e80` /4944 |21payload/246112B, JSON16개·전 파일 SHA/bytes PASS |

첫 두 패킷32payload/1405872B를 `.local/a176u/collection/DEV-CONTROL-SOURCES-008/`의 새 디렉터리에 사본화했다. 권리 검수 조건의 비공개 자료이며 공개 원본/코드 재배포·import/실행·실물·공유 폴더 쓰기0이다. DB 전후 SHA는 `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`로 같다. P01에 실제 ACK했고 개발3에 CTRL001의 읽기 경로·검수 한계와 구현 반영을 전달했다.

전력계는 N1911A P-Series/N1914A EPM의7영역씩14영역·45근거다. 기존5가이드와41개 근거 위치는 재사용했으며 새 원문1개는 IVI1.2.3.0 소개 HTML이다. 실제 IVI Readme/package/EULA/NOTICE는 확보하지 않았다. measurement window와 물리 input, FETCh/READ/MEASure·relative/ratio 단위, 센서/보정·OPC 완료와 CAL 성공/새 유효 데이터/추적 교정을 나눈다. CAL:ALL?가 절차를 시작한다는 이유로 현재 조회 subset에 추가하지 않는다. N1921A 호스트·교정 관계를 보존하고 N1914A 호환·독립 endpoint를 승인하지 않는다.

시설 자료는8의존 범위·17근거·16기존프로필을 보존했다. 2090 April2006 RevG의 공개 미러 HTML1..100/178쪽만 확보했고 실제 설치주소·축·한계/정지·FW를 확정하지 않았다. RsOsp2.10.17.75는 OSP2xx/3xx용 정적 소스이며 OSP120 적용·완전 권리문 확보로 세지 않는다. 경로 손상 질문은 P01의 원본 SHA/UTF-8/codepoint 대조에서 오탐으로 처분됐다. 동결 질문을 그대로 보존하고 검수 정정을 함께 인수했다.

이 인수는 문서 근거와 bytes 대조이며 실제 SDK/제품 Simulation 실행이나 장비 기능 검증이 아니다. 개발1 catalog API/개발4 화면과 개발3 기존 N1914A subset 연결을 계속한다. 준비된 고정 SDK 소스는 아래 후속 인수처럼 SDK-SIM-006에 연결하며 현재 새 사용자 준비 요청0이다.

후속 S07까지 합계50payload/2290985B·JSON42개를 비공개 인수했다. RsInstrument 고정 commit `b600fd6cf693dbcfa3cbfba0f638dfa14ff2c0aa`의 ZIP SHA는 `01eaa9b33bf047ae420ee49280fe74addecd98ad4e04456919c08ca0dd100649`, PyVISA-sim0.7.0 commit `f7af67e299ccdc95ccfccbe9edcb7490aa189d6f`은 `7fc2bc8cd2392fa33295da94253b86e9119ef9ab2140693ac2f9aa83302cfc51`이다. 두 ZIP CRC·루트 MIT 허가/고지문과 실제31개 member SHA/66개 line-range SHA를 직접 대조했다. 70개 표기는 동결자료를 바꾸지 않고 P01 정정으로 인수했다.

자료·소스 정적 대조 후 개발2에 실제 SDK-SIM-006 구현 입력을 전달했다. Python package1.131.0과 README build1.131.0.128을 구별한다. 의존성 선언은 설치된 lock이 아니며 private 환경에서 개별 배포·권리/해시를 고정한 후 실행한다. PyVISA-sim의 동적 SCM version/생성 version.py 부재는 빌드 미검증으로 남기고 이번 R&S 결과로 대체하지 않는다. 캐시·기본 OPC/error·같은 backend close/open은 실제 RF 유효성·프로세스 재시작 복구가 아니다. 총괄 인수 단계의 설치·archive 추출·source import/실행은0이다.

## 후속 네 패킷 인수와 적용

총괄이 새57payload/1906534B·JSON46개를 위 index의 독립 예상 SHA로 대조해 새 private 디렉터리에 인수했다. 현재 누적은 **107payload/4197519B·JSON88개**다. 공유 파일의 bytes·크기·mtime 불변과 공유쓰기0을 확인하고 P01에 실제 ACK했다. 원문·원시 소스는 공개하지 않았다.

S02는 N9030A 두 제조사와 FSV40/FSV 40 표기 네 등록 레코드를 세 기존 가상 후보로 보존했다. XSAn IVI.NET/IVI-C1.2.1.0 공식 등재와 AgXSAn3.12.0.0 계열, 1MA17114e의2021년 rsspecan3.8.0 예제는 서로 다른 판본이다. 로그인/privacy HTML은 package/Readme/EULA가 아니다. 정확 FSV40 현재 driver/FW/옵션은 미확인이며 TRACE007의12행·37인용과 family조건을 바꾸지 않는다.

S08의14근거는 v1.1/build1.1.20·46쪽 PDF·17도구와 구형 온라인0.1/18도구를 구별한다. 공식 게시 checksum은 미확보 installer의 실제 파일 SHA가 아니다. MCP/Mock/IDF/IOLS 본체·완전 EULA는 확보되지 않았다. Linux Mock 표와 socket-only 문구의 불일치, annotation과 승인 강제의 차이, 오류 큐 소비와 메모리 재시작 소실을 그대로 남겼다.

S01은27프로필의15후보 관계/14유일 model ID와 DB18모델·12별칭을 읽기 대조했다. FMZB 제조사·T&M/TNM·HP 오기/별칭·MA4640 EP/ET를 합치지 않으며64프로필·DUT·CO3000 역할/PXI기능/FMSR경로·N1921A 호스트/교정을 보존한다. 새 원문·네트워크0이며 실제 설치 binding이나 지원 승인이 아니다.

S03은 공식 tm_devices의 TSP/Apache-2.0, community PyMeasure SCPI/MIT, Tek socket sample의 제품 한정 조건을 분리한다.14정적 근거와3소스의 AST 색인에서 return-only24개를 기능으로 세지 않는다. PyMeasure 생성자의 `*LANG` 쓰기 후보·측정 설정과 반환값 차이·오류 큐 변경을 어댑터 검토 항목에 반영한다. tm_devices22선언 의존성은 설치 lock/전이 권리 검증이 아니며 Keysight DMM6500 식별 보류를 유지한다. 구체 구현 전 해당 mixin/NOTICE/adapter/release/제품 범위만 후속 검토한다.

SDK-SIM006은 개발2의 private 고정소스/의존성 환경에서 진행 중이다. 첫 실제 Simulation 관측은 부모 PID 결합 검증에서 실패해 성공 집계0으로 보존했다. 통합된 합성 probe 성공이나 이 인수 영수증으로 제조사 SDK 실행 검증을 대체하지 않는다. 현재 추가 사용자 준비물0이다.

후속 S05까지8패킷의 누적은 **128payload/4443631B·JSON104개**다. 마지막21파일도 지정 index SHA/bytes와 모두 대조했고 공유 원본 bytes·크기·mtime은 같다. E3632A의 고정 python-ivi commit `cfa45ceade0758debe4bc24ba4c8195222cad1e2`는 정확 class의 초기화/range와 E3600A/SCPI 계열 기능을 구별한다. 단일 출력·P15V/P30V의 프로그래밍 최대값을 정격/DUT 한계로 쓰지 않는다. abort/disable/lock의 pass-only·simulation 측정0·tracking getter 위험과 출력 OFF 미보장을 보존한다. 설정/cache/실측/출력 readback·오류/완료는 별개다. setup의 legacy requires/extras는 pin·설치 검증이 아니며 버전 exec·core/transport와 의존 권리는 미검토다.6신규 원문은 private이며 실제 SDK/실장비 지원으로 승인하지 않는다.
