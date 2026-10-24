> 보관용 조사 기록입니다. 당시 조사 역할·클라우드 경로를 설명하며 현재 총괄에게 새 역할을 부여하지 않습니다. 이번 공개 게시본의 로그는 검색어·URL·원본 해시 중심의 메타데이터이며, 아래 설명의 원시 웹 응답이나 코드 사본은 게시본에 포함하지 않습니다. 현재 인수 지시는 저장소 루트의 EQUIPMENT-CONTROL-RESEARCH-START.md를 따릅니다.

# 위치제어·스위치·인터페이스·시험 소프트웨어 조사

236개 입력 모델을 모두 개별 검색했다. 검색 실행 316건, 미검색 0건이다. 결과에는 123개 항목의 출처 199건(고유 URL 119개)을 연결했다. 출처가 있다는 것은 완전한 명령서 확보나 현장 장비와의 호환 검증을 뜻하지 않는다.

## 최종 집계

| 구분 | 수 |
|---|---:|
| 입력 / 결과 | 236 / 236 |
| 포함 | 152 |
| 식별 미해결 | 62 |
| 범위 확인 필요: 일반 PC·서버·모니터 등 | 18 |
| 수동 부품 제외 | 4 |
| 정확 모델 자료 | 41 |
| 계열 자료 / 계열 후보 | 37 |
| 제조사 제품·지원 자료만 | 16 |
| 검색했으나 공개 제어 자료 미확보 | 58 |
| 공개 코드 또는 SDK 후보 링크가 있는 항목 | 29 |
| 미검색 | 0 |

등급은 결과 JSON의 research_status를 따른다. 식별 미해결 62개와 범위 확인 필요 18개도 검색은 수행했다. 동일 계열 또는 맞춤 접미사의 적용 가능성은 sources.match_level에 별도로 기록했다.

## 확인한 제어 경로

- **INNCO**: [CO3000 제조사 명령서 재게시](https://www.ramayes.com/Data%20Files/Innco%20Systems/CO3000-en.pdf)의 GPIB/LAN 경로와 기구별 명령 절. [CO2000 커뮤니티 Python 코드](https://github.com/eardali/turntable)는 MIT이며 turntable 전용이다. 실제 table.py·README·LICENSE를 읽었고 마스트 지원으로 확대하지 않았다. CT0800은 root가 별도 조사한 항목으로 이 입력 목록에는 없다.
- **TDK**: [SI-300 공식 자료](https://www.tdkrfsolutions.tdk.com/products/loop-/system-interface-si-300)의 GPIB/광 제어와 RSM-02 연계를 확인했다. SI-300-2/SI30002 표기의 세부 구성은 확정하지 않았다.
- **ETS-Lindgren**: [2090 명령서](https://manualmachine.com/etslindgren/2090/1422741-user-manual/)와 [2110/2115 MAPS 공동 매뉴얼](https://www.mdltechnologies.co.uk/technical-docs/2115-multi-axis-positioning-systems-maps.pdf)이 제어 경로다. 2110/2115는 공동 계열 근거에 맞춰 family_source로 기록했다. 2092는 2090과 동일 명령 체계라고 확정하지 않았다.
- **Stäubli / SPEAG**: [ROS-Industrial VAL3 드라이버](https://github.com/ros-industrial/staubli_val3_driver)는 커뮤니티 Apache-2.0 코드이며 CS8/CS9 및 VAL3 조건이 있다. [SPEAG 수명·호환 자료](https://speag.swiss/products/dasy8/m-sar-apd/product-lifetime)로 DASY·로봇·컨트롤러 세대를 대조했다. CS7MB는 별도의 V+ 계열로 구분했다. SP1/SP2 및 D211 부품번호는 티칭 펜던트 자료로 남겼으며 독립 HID/API 지원을 추정하지 않았다.
- **UR5e**: [Universal Robots 공식 ROS2 드라이버](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver)의 명시적 UR5e 지원과 BSD-3-Clause를 확인했다.
- **RF/시험 스위치**: [HIOKI SW2001 공식 통신 설명](https://manual.hioki.com/en/SW2001/manual/7-3), [Keithley S46 QCoDeS 코드](https://github.com/microsoft/Qcodes/blob/main/src/qcodes/instrument_drivers/Keithley/Keithley_s46.py)를 찾았다. S46의 대장 접미사는 별도 포트맵 확인이 필요하다. HIOKI Sample Application은 소스 코드가 아닌 독점 실행형 유틸리티로 수정했다. R&S OSP220/230 자료는 대장 제조사와 충돌하므로 식별 후보로 유지했다.
- **EM TEST**: BS200N100과 BSM200N40은 [제조사 데이터시트](https://en.excen-tech.com/uploadfiles/281/Products/Emtest/Automotive-EMC-Test-Solutions/transient-emission-set-en.pdf)에 외부 BNC 트리거가 명시된다. BSM의 기계식 릴레이도 외부 제어가 있어 포함했다.
- **통신 인터페이스**: NI GPIB 연장기·PEAK/MK/TESEO 광 변환기는 독립 명령 API와 상위 호스트 드라이버를 구분했다. Vector·Kvaser는 해당 CAN 장치/API 자료를 연결했다. 일반 Ethernet TAP과 USB 절연기를 소프트웨어 제어기로 간주하지 않았다.
- **소프트웨어·PC**: Burp는 [공식 Montoya API](https://github.com/PortSwigger/burp-extensions-montoya-api), PTS는 공식 Control API와 커뮤니티 자동화 후보를 연결했다. Sparrow Enterprise와 On-Demand API 제품은 구분했다. 일반 PC의 OS/BIOS 자료와 SAR·시험 소프트웨어 API는 별개로 남겼다. Dell 서버의 Redfish는 서버 관리 후보이며 시험장비 API를 대체하지 않는다.

## 남은 자료

HCT의 경로명만 있는 INPUT/HPF/LNA 항목, T&M/TNM/인스조이의 TMX·FBSM·FBSR·FMSR, SCM 스위치박스는 정확한 본체/컨트롤러 모델, RF·릴레이 포트맵, 통신 방식과 명령 구문, 동시접속 조건이 필요하다. 검색된 시험 보고서의 장비 목록은 제어 명령서로 취급하지 않았다. 고정 감쇠기와 이름이 비슷한 전환 경로도 스위치 시스템 일부라 유지했다.

식별 미해결에는 모델 없는 턴테이블·마스트·조이스틱·전원 스위치, ADLINK로 기록된 Aeroflex 3025C/3035C 후보, 제조사가 다른 OSP220/230, 세대 없는 PTS 동글 등이 포함된다. 일반 PC 18개는 설치된 시험 SW와 인터페이스 식별이 필요하다.

수동 제외는 Schwarzbeck AM9144, TDK TRI150R, ETS108279 mount, B&K 대장상 Antenna Cable이다. AM9144는 공식 제품 설명의 수동 나사/텔레스코프 조절 근거로 제외했다. B&K Type3590C는 케이블이라는 대장 용도에 한정하며 동일 표기의 다른 장비까지 제외하지 않는다.

## 검증 및 파일

[results.json](results.json)은 입력 item_id와 1:1로 대응한다. [statistics.json](statistics.json)에 집계가 있으며 [unprocessed.json](unprocessed.json)은 빈 배열이다. 개별 검색과 추가 검색의 원문은 logs/batch_*.json과 logs/follow_*.json, 직접 연 페이지는 logs/open_*.json, 읽은 공개 코드/라이선스는 logs/raw/에 있다.

중복 ID·누락 ID·검색 기록 누락·축약 URL·exact_source의 exact_model 근거 여부를 확인했다. 원본 저장소·DB는 변경하지 않았고 Git 작업과 현장 네트워크 탐색도 하지 않았다. 드라이버 설치, 내려받은 장비 제어 코드 실행, 장비 연결 및 명령 송신은 수행하지 않았다.

