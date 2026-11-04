# 제조사별 남은 연결 정보

**모든 장비 제어가 완성됐다는 의미로 읽지 않습니다.** [지원표](EQUIPMENT_COVERAGE.md)의 `implemented_uncommissioned`는 명시된 API만 구현한 상태입니다. `conditional`은 하위 컨트롤러·앱·설치 조건이 추가로 필요합니다. `pending_protocol`/`vendor_required`에는 실행 드라이버가 없으며 SCPI를 추측해 전송하지 않습니다.

| 제조사·모델 | 확보·분석한 내용 | 연결을 완성하는 데 필요한 구체적 항목 |
| --- | --- | --- |
| Keysight/Agilent 분석기·RF source·power meter·E3640A | 모델별 공식 매뉴얼, A/B/PSA 문법 분리, VISA/TCP API | 실제 IDN/firmware/options, VISA 주소, 입력 최대치·RF 경로, 교정 및 cable-loss 파일, 센서 채널·영점 |
| R&S FSW/ESU/ESCI/ESW/ESR·NRP·SMB/SMW·ZNLE | 공식 매뉴얼과 remote command, 모델 식별·측정·종료 API | 설치 대역/앱/펌웨어·VISA 런타임, RF path1 이외 구성, 보정 상태, 과부하·필터/검파기 설정의 현장 비교 |
| R&S CMW500 | LTE FDD RMC 시작/상태 대기/종료 executor | LTE signaling license, RF route/감쇠, test SIM/PLMN/auth, band/EARFCN/RB 조합, DUT 접속 설정, 독립 RF OFF 계측 |
| R&S CMX500 | 공식 [5G F2L 문서](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/dl_application/application_notes/1sl369/1SL369_0e_5G_F2L.pdf)에 XLAPI 설치·네트워크 설정 명시. `from xlapi import settings`, `settings.system.set_instrument_address(...)` 인터페이스 확인 | 설치 XLAPI 버전·패키지, 생성된 검증 시험 스크립트와 network configuration, NR cell/connection/stop API, 라이선스. 주소 지정 코드만으로 NR TX 실행 가능으로 표시하지 않음 |
| Keysight E7515B UXM | [공식 제품 자료](https://www.keysight.com/in/en/product/E7515B/uxm-5g-wireless-test-platform.html)의 NR/LTE signaling 및 옵션 확인 | 실제 설치된 test application 이름/버전·프로그램 가이드·SCPI endpoint, RF port/role mapping, SIM/connection/stop 예제. E7515A 매뉴얼을 B에 전용하지 않음 |
| R&S EMC32, SCU-18, SCU-40A | 성적서 모델/역할 목록 보존 | EMC32 버전·라이선스·automation interface, SCU 포트/필터 맵·controller 문서·readback·default route. 잘못된 경로를 결과로 승인하지 않음 |
| Boonton RTP5008 | 공식 RTP API 문서 URL 확보. 현재 다운로드 `403 Forbidden`; 일부 검색 인덱스의 함수명만으로 드라이버를 만들지 않음 | 설치 SDK·DLL/헤더·bitness·세션 open/close·callback 및 오류 ABI, SCPI 송수신 예제. `PwrSnsr_SendSCPICommand` 이름만으로 SessionID 형식·초기화를 추측하지 않음 |
| Copper Mountain Planar R140 | RVNA 21.3.1 SCPI, BUS trigger와 데이터 API | 설치 RVNA/RNVNA 버전, 앱의 TCP server address/port, 정확한 IDN 문자열, 교정 파일·reference plane |
| Kikusui PWR2001ML | PWR-01 공식 interface guide, 전압/전류/출력/계측 구현 | 통신 주소·옵션과 시료/배선 기준 V/A 상한, protection/interlock, 전압 실측 비교 |
| HP 437B·8481A | 스캔된 공식 매뉴얼 육안 대조. 고유 TR/FR/SE/SM 언어 구현 | GPIB 주소·VISA, 실제 8481A 교정표 번호 0..9·교정 주파수 범위, 영점/교정 기록 |
| ESPEC SH-642 | 제조사 [ChamberConnectLibrary](https://github.com/EspecNorthAmerica/ChamberConnectLibrary)의 P300/SCP220 wire protocol 구현 | 장착 controller명, 실제 ROM? 결과, socket/serial 설정·termination, 온도 단위/범위·습도 사용 여부·interlock. SH-642에서 해당 controller라는 증거 필요 |
| Thermotron SM-16C | 8800 공식 generic protocol 구현 | 실제 8800 장착 확인, 장비별 운전 매뉴얼, ACK on/off·채널·단위, 시작 전 기존 manual setpoint, door/airflow/interlock |
| Cincinnati Sub Zero / Sorensen XT15-4, XT20-3 | 성적서 모델 추출. 본체 모델만으로 통신옵션 확정 불가 | CSZ controller 모델/프로토콜; Sorensen 설치 MRA/MGA 등 옵션명과 해당 interface manual·pinout·terminator. 다른 Sorensen SCPI 문법 자동 적용 금지 |
| TESCOM MTP300A/TC3000C, TA Engineering TA018S16 | 성적서 모델/설명 보존 | 실제 controller·SDK·명령표·축 이름/단위·원점·limit·home/move/position/stop 응답, 연결 port 및 interlock. 이동 API는 아직 없음 |
| SPEAG DASY/cSAR/DAK, DAE, EX3, EUmmW | 공개 DASY8 R&D 문서·custom scan 구조 확인 | 설치 제품·버전·licensed SDK, robot/DAE/probe 통합 API, scan start/stop/position/results, probe calibration 및 tissue/system-check. R&D API를 SAR 적합성 자동화 API로 간주하지 않음 |
| UL / UL-FR1 자체 RF switch·filterbox·시험 소프트웨어 | 자산/모델 원문과 해당 PDF 페이지 보존 | 설치실의 내부 프로토콜/SDK·port map·relay readback·filter selection·busy/error/stop/reset 규칙. 제조사 일반 매뉴얼로 대체 불가 |
| Samsung SM-F971U / Apple A3447 | FCC 조건·기술 목록, 기존 Samsung source-scoped bridge | 정확한 시험용 빌드, OEM test app/SDK와 사용 권한, 각 radio/antenna/chain/RU/BW/power/duty 숫자표, TX ON/OFF·readback·실측. 최신 단말 직접 제어는 아직 차단 |

수동 안테나·케이블·필터·attenuator·LISN·지그는 전부 독립 원격 제어 장비가 아닙니다. 필요한 것은 asset ID, 교정계수, 연결 방향/포트, 주파수별 손실, 배치입니다. 전원이 있는 프리앰프도 원격 API가 확인되지 않으면 제어 가능 장비로 승격하지 않습니다. PC/충전기/헤드셋 등 지원 장비는 별도 OS·앱 설정 대상입니다.

## 현장 자료 입력 형식

| 항목 | 최소 제공값 | 검수에서 사용하는 방식 |
| --- | --- | --- |
| 장비 | 제조사·모델·serial·IDN 원문·firmware·options | 잘못된 장비/명령 dialect 연결 차단 |
| 통신 | VISA resource 또는 IP/port; serial은 baud/parity/bits/stop/termination | 프로파일에 명시, 네트워크 자동 검색 없음 |
| 연결 | DUT port→switch→attenuator→analyzer 도면, 최대입력, path-loss/antenna factor | 측정값 보정·보호·올바른 RF 경로 확인 |
| 시험 | 원본 보고서 항목/페이지, channel/BW/MCS/RB/antenna/fold/duty, 장비 recipe | 요청 조건과 실제 설정/결과 비교 |
| 실행 증거 | IDN·설정 재조회·오류큐·ON/OFF 실제 파형·정상/실패/취소 로그 | `hardware_validated`를 증거 있는 조합만 승격 |

프로파일·교정·시리얼·현장 주소는 별도 `site-*.json`에 보관하고 실제값을 공용 예제에 커밋하지 않습니다. 자료가 추가되면 미구현 항목을 같은 드라이버 registry와 실패 harness에 편입합니다.
